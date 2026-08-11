#!/usr/bin/env python3
"""
lyx2md.py -- Deterministic LyX -> Markdown converter for the FEBio Theory
Manual. Started as a Chapter 2 (Continuum Mechanics) single-chapter pilot;
now handles the complete manual, though CHAPTERS_TO_CONVERT below limits
which chapters actually produce output pages at any given time.

No external dependencies (stdlib only).

Usage:
    python3 tools/lyx2md.py

Reads (checked in this order so the repo is self-contained for CI/GitHub
Actions, but still picks up live edits from the original workspace input
directory during local development):
    source/FEBio_Theory_Manual.lyx   (vendored copy, checked into this repo)
    source/FEBio3.bib
    ../febio-docs/FEBio_Theory_Manual.lyx   (fallback: sibling workspace dir, if present)
    ../febio-docs/FEBio3.bib

Writes:
    docs/theory/chapter<N>/<N>.M-slug.md   (one file per converted Section)
    tools/_stats.json                      (conversion statistics consumed by build.py / CONVERSION_NOTES)

Design
------
LyX files are a fairly simple line-oriented, brace/keyword-delimited format.
We do NOT attempt a full LyX grammar. Instead we:

  1. Split the document into a flat list of "lines".
  2. Walk the lines with an explicit stack-based inset/layout parser that
     builds a small tree of Block/Inset nodes.
  3. Render that tree to Markdown text, tracking:
       - open citation keys -> footnotes appended per page
       - equation \\label{...} anchors for \\eqref{...} cross refs
       - figure/table label anchors for \ref{...} cross links
  4. Post-process: join LyX's hard-wrapped paragraph continuation lines
     (LyX 2.4 writes a leading space on wrapped continuation lines) into
     single logical paragraphs before emitting markdown text runs.

The converter is intentionally conservative: anything it does not
recognize is logged to the "needs review" list (see tools/_stats.json)
rather than silently dropped, and unhandled inset content is rendered
as an HTML comment marker `<!-- UNHANDLED: ... -->` so a `grep` for
leftover LyX bookkeeping tokens (\\begin_, \\end_inset, etc.) will catch
any gaps.
"""
import json
import os
import re
import string
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _first_existing(*candidates):
    for c in candidates:
        if os.path.isfile(c):
            return c
    # Nothing found -- return the first candidate anyway so the resulting
    # FileNotFoundError points at the preferred (vendored) location.
    return candidates[0]


# Prefer the vendored copy under source/ (checked into this repo, so
# `python3 build.py` works standalone in CI/GitHub Actions with just a
# checkout of this repo -- no sibling febio-docs/ directory required).
# Fall back to the sibling workspace directory this pilot was originally
# developed against, for convenience during local iteration.
LYX_PATH = _first_existing(
    os.path.join(ROOT, "source", "FEBio_Theory_Manual.lyx"),
    os.path.join(ROOT, "..", "febio-docs", "FEBio_Theory_Manual.lyx"),
)
BIB_PATH = _first_existing(
    os.path.join(ROOT, "source", "FEBio3.bib"),
    os.path.join(ROOT, "..", "febio-docs", "FEBio3.bib"),
)
DOCS_THEORY_ROOT = os.path.join(ROOT, "docs", "theory")

# Which chapters to actually convert this run, by their 1-indexed position
# among \begin_layout Chapter entries in the full manual (Introduction=1,
# Continuum Mechanics=2, The Nonlinear FE Method=3, ...). Chapters not
# listed here are still scanned for their titles/boundaries (so section
# numbering and cross-chapter \ref{}/\eqref{} resolution stays correct
# regardless of conversion order) but produce no output files -- a
# reference into an unconverted chapter degrades the same way an
# out-of-scope reference already does (left unresolved, flagged in
# needs_review), not a crash.
CHAPTERS_TO_CONVERT = {1, 2, 3, 4, 5, 6, 7, 8, 9}

STATS = {
    "sections": [],
    "totals": {
        "inline_formulas": 0,
        "display_formulas": 0,
        "citations": 0,
        "labels": 0,
        "refs": 0,
        "figures": 0,
        "unhandled": 0,
    },
    "needs_review": [],
}

# -----------------------------------------------------------------------
# Section 1: Bibliography parsing (very small bibtex subset -- enough for
# author/title/journal/year fields used by FEBio3.bib)
# -----------------------------------------------------------------------

def parse_bib(path):
    """Parse a .bib file into {key: {field: value}}."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    entries = {}
    # Match @type{key, field = {...} or "...", ... }
    # We scan manually because values can themselves contain braces.
    i = 0
    n = len(text)
    while i < n:
        at = text.find("@", i)
        if at == -1:
            break
        # skip @comment{...}
        m = re.match(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", text[at:])
        if not m:
            i = at + 1
            continue
        entry_type = m.group(1).lower()
        key = m.group(2)
        body_start = at + m.end()
        if entry_type == "comment":
            # find matching close brace and skip
            depth = 1
            j = body_start
            while j < n and depth > 0:
                if text[j] == "{":
                    depth += 1
                elif text[j] == "}":
                    depth -= 1
                j += 1
            i = j
            continue

        # walk forward tracking brace depth (started at 1 for the entry's outer brace)
        depth = 1
        j = body_start
        while j < n and depth > 0:
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
            j += 1
        body = text[body_start:j - 1]  # exclude final closing brace
        fields = parse_bib_fields(body)
        entries[key] = fields
        i = j
    return entries


def parse_bib_fields(body):
    fields = {}
    i = 0
    n = len(body)
    while i < n:
        m = re.match(r"\s*,?\s*(\w[\w\-]*)\s*=\s*", body[i:])
        if not m:
            i += 1
            continue
        field_name = m.group(1).lower()
        i += m.end()
        if i >= n:
            break
        if body[i] == "{":
            depth = 1
            j = i + 1
            while j < n and depth > 0:
                if body[j] == "{":
                    depth += 1
                elif body[j] == "}":
                    depth -= 1
                j += 1
            value = body[i + 1:j - 1]
            i = j
        elif body[i] == '"':
            j = i + 1
            while j < n and body[j] != '"':
                j += 1
            value = body[i + 1:j]
            i = j + 1
        else:
            j = i
            while j < n and body[j] not in ",\n":
                j += 1
            value = body[i:j].strip()
            i = j
        fields[field_name] = re.sub(r"\s+", " ", value).strip()
    return fields


def format_citation(key, fields):
    """Render a footnote text for a bib entry: author, title, journal, year."""
    if not fields:
        return f"{key} (reference not found in FEBio3.bib)"
    author = fields.get("author", "")
    # bibtex authors are "Last, First and Last2, First2" -> keep as-is but tidy 'and'
    author = author.replace(" and ", "; ")
    title = fields.get("title", "")
    journal = fields.get("journal") or fields.get("booktitle") or fields.get("publisher", "")
    year = fields.get("year", "")
    volume = fields.get("volume", "")
    pages = fields.get("pages", "")
    parts = []
    if author:
        parts.append(author)
        pass
    piece = ""
    if author:
        piece += f"{author}. "
    if title:
        piece += f'"{title}." '
    if journal:
        piece += f"*{journal}*"
        if volume:
            piece += f", vol. {volume}"
        if pages:
            piece += f", pp. {pages}"
        piece += " "
    if year:
        piece += f"({year})."
    return piece.strip() or f"{key}"


# -----------------------------------------------------------------------
# Section 2: Tokenizing / tree building
# -----------------------------------------------------------------------

class Node:
    __slots__ = ("kind", "attrs", "children", "text_lines")

    def __init__(self, kind, attrs=None):
        self.kind = kind          # 'layout:Section', 'inset:Formula', 'text', 'root', ...
        self.attrs = attrs or {}
        self.children = []
        self.text_lines = []      # raw text lines directly inside (for text/plain nodes)

    def __repr__(self):
        return f"Node({self.kind}, attrs={self.attrs}, nchild={len(self.children)})"


LAYOUT_RE = re.compile(r"^\\begin_layout\s+(.+)$")
END_LAYOUT_RE = re.compile(r"^\\end_layout\s*$")
INSET_RE = re.compile(r"^\\begin_inset\s+(.+)$")
END_INSET_RE = re.compile(r"^\\end_inset\s*$")


def build_tree(lines):
    """Parse the flat list of LyX lines into a tree of Node objects.

    We use an explicit stack. Each stack frame is a Node. Layouts and
    insets both push/pop. Anything else is accumulated as a raw text
    line attached to the node at top-of-stack.
    """
    root = Node("root")
    stack = [root]

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]

        m_lay = LAYOUT_RE.match(line)
        m_endlay = END_LAYOUT_RE.match(line)
        m_ins = INSET_RE.match(line)
        m_endins = END_INSET_RE.match(line)

        if m_lay:
            node = Node("layout:" + m_lay.group(1).strip())
            stack[-1].children.append(node)
            stack.append(node)
        elif m_endlay:
            # pop until we pop a layout node (defensive against imbalance)
            while len(stack) > 1 and not stack[-1].kind.startswith("layout:"):
                stack.pop()
            if len(stack) > 1:
                stack.pop()
        elif m_ins:
            spec = m_ins.group(1).strip()
            node = Node("inset:" + spec)
            stack[-1].children.append(node)
            stack.append(node)
        elif m_endins:
            while len(stack) > 1 and not stack[-1].kind.startswith("inset:"):
                stack.pop()
            if len(stack) > 1:
                stack.pop()
        else:
            stack[-1].text_lines.append(line)

        i += 1

    return root


# -----------------------------------------------------------------------
# Section 3: Rendering helpers
# -----------------------------------------------------------------------

CHAR_STATE_LINES = {
    r"\series bold", r"\series default", r"\series medium",
    r"\emph on", r"\emph default",
    r"\shape italic", r"\shape default", r"\shape up", r"\shape slanted", r"\shape smallcaps",
    r"\bar under", r"\bar default",
    r"\family typewriter", r"\family default", r"\family roman", r"\family sans",
    r"\noun on", r"\noun default",
    r"\color inherit", r"\color none",
}

ALIGN_RE = re.compile(r"^\\align\s+(\w+)\s*$")
LANG_RE = re.compile(r"^\\lang\s+\w+\s*$")


def render_text_lines(raw_lines):
    """Convert LyX 'Standard'-layout raw text lines (with inline char-format
    bookkeeping lines mixed in) to a single joined markdown text run.

    LyX 2.4 hard-wraps paragraph source across multiple lines; continuation
    lines start with a single leading space which is the real word-separating
    space. A line that has no trailing content (blank) signals a paragraph
    break within the same layout (rare inside Standard, but handled).
    """
    out_words = []  # we'll just concatenate, honoring the leading-space rule
    buf = ""
    state = {"bold": False, "emph": False, "tt": False, "italic_shape": False}

    def flush_state_marker(kind, turn_on):
        nonlocal buf
        if kind == "bold":
            buf += "**"
        elif kind == "emph":
            buf += "_"
        elif kind == "tt":
            buf += "`"

    for raw in raw_lines:
        if raw in CHAR_STATE_LINES or ALIGN_RE.match(raw) or LANG_RE.match(raw):
            if raw in ("\\series bold",):
                buf += "**"
                state["bold"] = True
            elif raw in ("\\series default", "\\series medium"):
                if state["bold"]:
                    buf += "**"
                    state["bold"] = False
            elif raw == "\\emph on":
                buf += "_"
                state["emph"] = True
            elif raw == "\\emph default":
                if state["emph"]:
                    buf += "_"
                    state["emph"] = False
            elif raw == "\\shape italic":
                buf += "_"
                state["italic_shape"] = True
            elif raw == "\\shape default":
                if state["italic_shape"]:
                    buf += "_"
                    state["italic_shape"] = False
            elif raw == "\\family typewriter":
                buf += "`"
                state["tt"] = True
            elif raw == "\\family default" or raw == "\\family roman":
                if state["tt"]:
                    buf += "`"
                    state["tt"] = False
            # \align, \lang, \bar, \noun, \color, \shape up/slanted -> ignored bookkeeping
            continue
        else:
            buf += raw
    # close any unterminated markers defensively
    if state["bold"]:
        buf += "**"
    if state["emph"] or state["italic_shape"]:
        buf += "_"
    if state["tt"]:
        buf += "`"
    return buf


def strip_lyx_text_bookkeeping(raw_lines):
    """Return raw_lines with pure-bookkeeping lines removed but content kept."""
    return raw_lines


LABEL_ANCHORS = {}      # lyx label name -> (kind, number-or-slug, section_slug)
EQ_LABEL_TO_NUM = {}     # label -> equation number string, e.g. "2.1-4"
SEC_LABEL_TO_TITLE = {}  # label -> (section_number, title, filename)
FIG_LABEL_TO_NUM = {}


def slugify(title):
    s = title.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s


# -----------------------------------------------------------------------
# Section 4: Inset renderers
# -----------------------------------------------------------------------

class RenderCtx:
    def __init__(self, bib, section_num, section_file=None, chapter_dir=None):
        self.bib = bib
        self.section_num = section_num       # e.g. "2.1"
        self.section_file = section_file     # e.g. "2.1-vectors-and-tensors.md"
        self.chapter_dir = chapter_dir       # e.g. "chapter2" -- which chapter's
                                              # output directory this page lives in,
                                              # needed to build correct relative
                                              # links for cross-chapter references
                                              # (docs/theory/chapter1/ vs chapter2/
                                              # are sibling directories)
        self.citations_used = []             # ordered list of (key, footnote_index)
        self.citation_index = {}             # key -> footnote number within this page
        self.eq_counter = 0                  # per-section equation counter
        self.fig_counter = 0
        self.example_counter = 0             # per-section Example environment counter
        self.inline_footnotes = []           # rendered text of each Foot inset, in order
        self.needs_review = []
        self.inline_formula_count = 0
        self.display_formula_count = 0
        self.unhandled_count = 0

    def cite_footnote_num(self, key):
        if key not in self.citation_index:
            self.citation_index[key] = len(self.citation_index) + 1
            self.citations_used.append(key)
        return self.citation_index[key]


def render_inset_formula(node, ctx):
    """Render \\begin_inset Formula ... contents (math)."""
    raw = "\n".join(node.text_lines)
    raw = raw.strip("\n")
    # Determine inline vs display: LyX writes inline math as "$...$" possibly
    # on one line right after 'Formula'; display math uses \begin{equation}
    # or \[ ... \] or align/eqnarray/array blocks, usually preceded by a
    # blank line ("\begin_inset Formula \n\n\begin{equation}").
    stripped = raw.strip()
    if stripped.startswith("$") and stripped.endswith("$") and stripped.count("$") == 2:
        inner = stripped[1:-1]
        ctx.inline_formula_count += 1
        return "$" + inner.strip() + "$"

    # display math: contains \begin{equation}, \begin{align}, \begin{eqnarray}, \[..\], etc.
    ctx.display_formula_count += 1
    body = stripped
    # LyX sometimes wraps bare align/eqnarray/array w/o outer \[ \]; the
    # feature-manual convention wants the whole thing wrapped in \[ ... \].
    if body.startswith("\\[") and body.endswith("\\]"):
        inner = body[2:-2].strip()
    else:
        inner = body
    return "\\[\n" + inner + "\n\\]"


def render_inset_quotes(spec):
    if spec.endswith("eld"):
        return '\u201c'
    if spec.endswith("erd"):
        return '\u201d'
    return '"'


def render_inset_space(spec):
    spec = spec.strip()
    if spec == "" or spec.startswith("\\quad") or spec.startswith("\\qquad"):
        return " "
    if spec == "~":
        return "\u00a0"
    return " "


def render_citation(node, ctx):
    key = node.attrs.get("key", "")
    keys = [k.strip() for k in key.split(",") if k.strip()]
    refs = []
    for k in keys:
        num = ctx.cite_footnote_num(k)
        refs.append(f"[^{ctx.section_num}-{num}]")
    return "".join(refs)


def render_ref(node, ctx):
    cmd = node.attrs.get("_cmd", "")
    reference = node.attrs.get("reference", "")
    if cmd == "eqref":
        return f"\\eqref{{{reference}}}"
    elif cmd == "ref":
        # section / figure / table cross-reference -> markdown link where resolvable
        return f"[{reference}](#{reference})"
    return f"\\ref{{{reference}}}"


def parse_inset_attrs(node):
    """Parse the leading attribute lines of an inset (e.g. CommandInset ref
    has LatexCommand eqref / reference "x" / plural "false" ...).
    Returns attrs dict and remaining text_lines with the attribute lines removed.
    """
    attrs = {}
    remaining = []
    consumed_prefix = True
    for line in node.text_lines:
        m = re.match(r'^(\w[\w]*)\s+"?([^"]*)"?\s*$', line)
        if consumed_prefix and re.match(r'^LatexCommand\s+(\S+)', line):
            attrs["_cmd"] = re.match(r'^LatexCommand\s+(\S+)', line).group(1)
            continue
        if consumed_prefix and re.match(r'^(reference|name|key|literal|plural|caps|noprefix|nolink)\s+', line):
            mm = re.match(r'^(\w+)\s+"?([^"]*)"?\s*$', line)
            if mm:
                attrs[mm.group(1)] = mm.group(2)
            continue
        consumed_prefix = False
        remaining.append(line)
    node.attrs.update(attrs)
    return attrs


# -----------------------------------------------------------------------
# Section 5: Main recursive markdown renderer
# -----------------------------------------------------------------------

class InlineRunBuilder:
    """Accumulates plain text + rendered inline insets, honoring LyX's
    leading-space-on-continuation-line convention, then exposes joined text.
    """
    def __init__(self):
        self.parts = []

    def add_raw_text_lines(self, lines):
        for raw in lines:
            self.parts.append(("text", raw))

    def add_rendered(self, text):
        self.parts.append(("rendered", text))

    def build(self):
        out = ""
        for kind, val in self.parts:
            out += val
        # Collapse LyX's explicit paragraph-internal comma+space breaks
        out = re.sub(r"[ \t]+", " ", out)
        out = out.replace(" ,", ",")
        out = re.sub(r"\s+([.,;:])", r"\1", out)
        out = re.sub(r"\.\s*\.", ".", out)
        return out.strip()


def render_inline_content(node, ctx):
    """Render the children + text_lines of a paragraph-like node (Standard,
    Plain Layout, Enumerate item, table cell, caption, etc.) to an inline
    markdown text run, recursing into child insets that are inline
    (Formula, citation, ref, label, quotes, space)."""
    builder = InlineRunBuilder()
    # children carries both text (via text_lines at this level, interleaved
    # positionally is NOT preserved by our simple tree -- we need positional
    # interleaving). To preserve order we re-walk using an index-based
    # approach instead. See render_layout_or_container for the real logic.
    raise NotImplementedError


# Because Node doesn't preserve interleaving between text_lines and children
# (a limitation of the simple tree builder above), we instead do a second,
# order-preserving pass directly over the flat line list for paragraph
# containers. This is implemented via `build_tree` variant below.

# ---- Order preserving flat-parse approach -----------------------------

def parse_flat(lines, i, end_predicate):
    """Generic recursive-descent: parse lines[i:] until a line matches
    end_predicate (exclusive), returning (list_of_items, next_index).
    Each item is either ('text', line) or ('inset', kind, spec, sub_items)
    or ('layout', kind, sub_items).

    Special case: LyX writes *inline* Formula insets entirely on one line,
    e.g. "\\begin_inset Formula $v_{i}$" immediately followed by
    "\\end_inset" on the next line -- there is no separate math content
    line. We detect this by checking whether the text after "Formula "
    already contains a balanced, self-contained "$...$" (i.e. the whole
    inline formula is inline with the begin_inset keyword itself).
    """
    items = []
    n = len(lines)
    while i < n:
        line = lines[i]
        if end_predicate(line):
            return items, i
        m_ins = INSET_RE.match(line)
        m_lay = LAYOUT_RE.match(line)
        if m_ins:
            spec = m_ins.group(1).strip()
            if spec.startswith("Formula ") and spec.count("$") >= 2:
                # inline formula fully on the begin_inset line itself
                math_part = spec[len("Formula "):].strip()
                sub_items = [("text", math_part)]
                # advance past this line; next line should be blank then end_inset,
                # or end_inset directly -- consume up to end_predicate for the inset
                i += 1
                inner_items, i = parse_flat(lines, i, lambda l: END_INSET_RE.match(l))
                i += 1
                items.append(("inset", "Formula", sub_items))
            elif spec.startswith("Formula ") and spec != "Formula":
                # A multi-line formula whose first line of math content sits
                # on the \begin_inset line itself (e.g.
                # "\begin_inset Formula $\begin{array}{l}", closed by
                # "\end{array}$" several lines later) rather than starting
                # on its own line. Not caught by the single-line case above
                # since it doesn't close here (count("$") == 1). Without this
                # branch, that leading "$\begin{array}{l}" text is silently
                # dropped -- it lives in `spec`, which nothing downstream
                # reads except its first token ("Formula") -- corrupting the
                # rendered formula (confirmed against Section 5.1's
                # Lame-parameter conversion table, the only place this
                # pattern occurs in the document).
                math_part_prefix = spec[len("Formula "):]
                inner_items, i = parse_flat(lines, i + 1, lambda l: END_INSET_RE.match(l))
                i += 1
                sub_items = [("text", math_part_prefix)] + inner_items
                items.append(("inset", "Formula", sub_items))
            else:
                sub_items, i = parse_flat(lines, i + 1, lambda l: END_INSET_RE.match(l))
                i += 1  # skip the end_inset line
                items.append(("inset", spec, sub_items))
        elif m_lay:
            spec = m_lay.group(1).strip()
            sub_items, i = parse_flat(lines, i + 1, lambda l: END_LAYOUT_RE.match(l))
            i += 1  # skip end_layout
            items.append(("layout", spec, sub_items))
        else:
            items.append(("text", line))
            i += 1
    return items, i


def top_level_parse(lines):
    items, _ = parse_flat(lines, 0, lambda l: False)
    return items


# ------------------------------------------------------------------
# Render an ordered item list (as produced by parse_flat) to markdown
# ------------------------------------------------------------------

EMPHASIS_SPAN_RE = re.compile(r"(\*\*|`|_)([^\n]*?)\1")
INLINE_MATH_RE = re.compile(r"\$[^$\n]*\$")
MATH_UNDERSCORE_PLACEHOLDER = "\x00"


def fix_emphasis_whitespace(text):
    """Markdown emphasis/bold/code markers (`_..._`, `**...**`, `` `...` ``)
    must not have whitespace immediately inside the delimiters, or most
    Markdown parsers (Python-Markdown included) will fail to recognize
    them and render the literal delimiter characters instead. LyX's
    character-formatting bookkeeping (\\series bold / \\emph on ... default)
    sometimes brackets leading/trailing spaces that belong, semantically,
    outside the run (e.g. "_dot _or" from "_dot_ or" with the space typed
    before toggling emphasis off in LyX). This normalizes such runs by
    hoisting interior leading/trailing whitespace to outside the marker
    pair. Applied repeatedly (non-overlapping, left-to-right) since marker
    pairs do not nest in this document.
    """
    def repl(m):
        marker, inner = m.group(1), m.group(2)
        stripped = inner.strip(" ")
        if stripped == "":
            # an emphasis run containing only whitespace (or nothing) --
            # drop the markers entirely, keep the whitespace.
            return inner
        lead = inner[: len(inner) - len(inner.lstrip(" "))]
        trail = inner[len(inner.rstrip(" ")):]
        return lead + marker + stripped + marker + trail

    # Inline math ($...$) commonly contains a literal LaTeX subscript/
    # superscript underscore (e.g. "$t_{0}$"), which is indistinguishable
    # from a real emphasis delimiter to a naive regex. Left as-is, one
    # such "fake" underscore between two genuine \emph on/off toggles
    # shifts the marker pairing for the rest of the paragraph, swallowing
    # large unrelated spans of text (including further math and other
    # \emph runs) into bogus "emphasis" matches. Neutralize underscores
    # inside math spans in place (restored at the end) rather than
    # splitting the string around them, so markers that legitimately wrap
    # a whole math span (e.g. "**$\\mathbf{x}$**") still pair correctly.
    def mask_math(m):
        return m.group(0).replace("_", MATH_UNDERSCORE_PLACEHOLDER)

    masked = INLINE_MATH_RE.sub(mask_math, text)

    prev = None
    out = masked
    # iterate a few times in case adjacent fixes reveal new fixable spans
    for _ in range(3):
        out = EMPHASIS_SPAN_RE.sub(repl, out)
        if out == prev:
            break
        prev = out

    return out.replace(MATH_UNDERSCORE_PLACEHOLDER, "_")


def render_items_inline(items, ctx):
    """Render a list of (kind, spec, subitems)/('text', line) tuples that
    represent the *inline* content of a paragraph, honoring char-formatting
    state and LyX's leading-space continuation convention."""
    out = ""
    state = {"bold": False, "emph": False, "tt": False, "shape_italic": False}
    for kind, *rest in items:
        if kind == "text":
            raw = rest[0]
            if raw in ("\\series bold",):
                out += "**"; state["bold"] = True
            elif raw in ("\\series default", "\\series medium"):
                if state["bold"]:
                    out += "**"; state["bold"] = False
            elif raw == "\\emph on":
                out += "_"; state["emph"] = True
            elif raw == "\\emph default":
                if state["emph"]:
                    out += "_"; state["emph"] = False
            elif raw == "\\shape italic":
                out += "_"; state["shape_italic"] = True
            elif raw == "\\shape default":
                if state["shape_italic"]:
                    out += "_"; state["shape_italic"] = False
            elif raw in ("\\shape up", "\\shape slanted", "\\shape smallcaps"):
                pass
            elif raw == "\\family typewriter":
                out += "`"; state["tt"] = True
            elif raw in ("\\family default", "\\family roman", "\\family sans"):
                if state["tt"]:
                    out += "`"; state["tt"] = False
            elif ALIGN_RE.match(raw) or LANG_RE.match(raw):
                pass
            elif raw.startswith("\\bar ") or raw.startswith("\\noun ") or raw.startswith("\\color "):
                pass
            elif raw == "\\start_of_appendix":
                # LyX's native marker for "this Chapter and all following
                # ones are lettered appendices, not numbered chapters"
                # (equivalent to LaTeX's \appendix) -- embedded directly
                # in the Chapter heading's own content (right before the
                # title text), so it must be stripped here or it becomes
                # literal text glued onto the title. main()'s chapter
                # boundary detection separately checks for this same
                # marker to decide the display numbering; this is just
                # about not corrupting the rendered title string.
                pass
            elif raw == "":
                # A truly empty line (zero-length) is LyX bookkeeping
                # filler, e.g. the blank line right after \end_inset or
                # before \begin_inset -- NOT a paragraph break (real
                # breaks are \end_layout/\begin_layout). Skip it.
                pass
            elif raw.strip() == "" and raw != "":
                # A line containing only whitespace (typically a single
                # leading space) is a genuine word-separating space that
                # LyX emitted on its own line, e.g. right before a
                # \series bold / \emph on block. Preserve it verbatim.
                out += raw
            else:
                out += raw
        elif kind == "inset":
            spec, sub_items = rest
            out += render_inset(spec, sub_items, ctx)
        elif kind == "layout":
            spec, sub_items = rest
            # Nested layout inside inline content (rare: Plain Layout inside Float/Tabular)
            out += render_items_inline(sub_items, ctx)
    # LyX scopes character formatting (\series/\emph/\shape/\family) to a
    # single paragraph/layout -- it implicitly resets at \end_layout and
    # does not require an explicit "...default" toggle first (confirmed:
    # table cells in Chapter 3 end with e.g. "\series bold\nI/J\n\end_layout"
    # and no closing \series default at all). Auto-close any marker left
    # open at the end of this call so it can never bleed into whatever the
    # *caller* appends next -- without this, an unclosed "**" from one
    # table cell would pair against the next available "**" anywhere later
    # in the surrounding text (e.g. a different cell's opening marker),
    # producing a bogus bold span across everything in between.
    if state["bold"]:
        out += "**"
    if state["emph"] or state["shape_italic"]:
        out += "_"
    if state["tt"]:
        out += "`"
    # normalize whitespace introduced by line joins; LyX continuation lines
    # begin with a single leading space which already provides the needed
    # word-separating space, so a straight concatenation is correct. Any
    # stray single "\n" left over (e.g. from raw LaTeX line breaks inside
    # a formula that leaked, or from list item boundaries) is collapsed to
    # a space, but the double "\n\n" markers that intentionally separate
    # display-math blocks from surrounding prose are preserved.
    out = re.sub(r"(?<!\n)\n(?!\n)", " ", out)
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r" +([,.;:])", r"\1", out)
    out = re.sub(r"\n[ \t]+", "\n", out)
    out = re.sub(r"[ \t]+\n", "\n", out)
    out = fix_emphasis_whitespace(out)
    # A Markdown table needs a *single* real newline between every row (no
    # blank lines allowed inside it, unlike the \n\n used elsewhere to
    # separate blocks) -- exactly the "stray single newline" shape the
    # substitution above collapses to a space. render_tabular() protects
    # its row breaks with TABLE_ROW_BREAK so they survive that pass
    # unchanged; restore them to real newlines now that it's done.
    out = out.replace(TABLE_ROW_BREAK, "\n")
    return out


INSET_HEAD_RE = re.compile(r"^(\S+)(?:\s+(.*))?$")

ERT_HREF_RE = re.compile(r"\\href\{([^}]*)\}\{(.*)\}\s*$", re.DOTALL)
ERT_URL_RE = re.compile(r"\\url\{([^}]*)\}\s*$")
ERT_EMPH_RE = re.compile(r"\\emph\{([^}]*)\}")


def render_ert(sub_items, ctx):
    """ERT ("evil red text") holds raw LaTeX source, not normal LyX
    character-formatted prose -- e.g. \\href{url}{\\emph{link text}} for a
    hyperlink LyX has no native inset for. It can't be rendered through
    render_items_inline()'s normal text handling for two reasons: (1) that
    would also pick up the inset's own "status open" attribute line as if
    it were content (mirroring the Box/Float attribute-lines pattern, so
    only the nested Plain Layout is real content), and (2) LyX encodes
    each literal backslash in the LaTeX source as a standalone
    "\\backslash" token line followed immediately by the rest of that
    command with *no* inserted whitespace, which render_items_inline's
    prose-joining rules (that assume a leading space means a real
    word-separating space) would corrupt into something like
    "\\backslashhref{...}".

    \\href{url}{text} and bare \\url{url} are the two patterns that occur
    anywhere in this document as of this writing (confirmed by scanning
    every ERT inset): both render as real Markdown links, \\href unwrapping
    a nested \\emph{} in its link text to Markdown emphasis rather than
    dropping it. Anything else is flagged for manual review instead of
    silently guessed at.
    """
    raw_parts = []
    for item in sub_items:
        if item[0] == "layout" and item[1] == "Plain Layout":
            for it in item[2]:
                if it[0] == "text":
                    raw_parts.append("\\" if it[1] == "\\backslash" else it[1])
    raw = "".join(raw_parts).strip()
    if raw in ("", "\\-"):
        return ""
    m = ERT_HREF_RE.search(raw)
    if m:
        url, link_text = m.group(1), m.group(2)
        link_text = ERT_EMPH_RE.sub(r"_\1_", link_text).strip()
        return f"[{link_text}]({url})"
    m = ERT_URL_RE.search(raw)
    if m:
        return f"<{m.group(1)}>"
    ctx.needs_review.append(f"ERT inset with content: {raw!r}")
    return f"<!-- ERT: {raw} -->"


def render_inset(spec, sub_items, ctx):
    kind = spec.split()[0]
    if kind == "Formula":
        return render_formula_inset(sub_items, ctx)
    if kind == "CommandInset":
        return render_command_inset(spec, sub_items, ctx)
    if kind == "Quotes":
        variant = spec.split()[1] if len(spec.split()) > 1 else ""
        return render_inset_quotes(variant)
    if kind == "space":
        variant = spec[len("space"):].strip()
        return render_inset_space(variant)
    if kind == "Newpage":
        return ""
    if kind == "ERT":
        return render_ert(sub_items, ctx)
    if kind == "Float":
        return render_float(spec, sub_items, ctx)
    if kind == "Caption":
        return render_items_inline(sub_items, ctx)
    if kind == "Graphics":
        return render_graphics(sub_items, ctx)
    if kind == "Tabular":
        return render_tabular(sub_items, ctx)
    if kind == "Box":
        # Purely decorative in print (border/background/frame styling around
        # its content, e.g. a figure); Markdown has no equivalent, so just
        # render the content transparently. sub_items' leading lines are
        # box attributes (position, width, thickness, ...), which -- like
        # Float's attribute lines -- are plain 'text' items and get skipped
        # naturally by only processing 'layout' items. A \align command
        # inside the Plain Layout (e.g. "\align center" wrapping a
        # Graphics inset) is otherwise silently dropped by
        # render_items_inline (it's plain inline character-formatting
        # state there, with no way to emit a block-level wrapper) --
        # re-detect it here at the layout level and center the image via
        # CSS. (Wrapping in a raw <div align="center"> block does *not*
        # work: nested Markdown image syntax inside a raw HTML block is
        # left unprocessed -- literal "![...](...)" text -- without the
        # md_in_html extension, which isn't enabled.)
        parts = []
        for item in sub_items:
            if item[0] != "layout":
                continue
            align = None
            for it in item[2]:
                if it[0] == "text":
                    m = ALIGN_RE.match(it[1])
                    if m:
                        align = m.group(1)
                        break
            content = render_items_inline(item[2], ctx)
            if align == "center":
                content = center_images(content)
            parts.append(content)
        return "".join(parts)
    if kind == "VSpace":
        # Decorative vertical whitespace (\vspace-equivalent); Markdown/CSS
        # already handles paragraph spacing, so there's nothing meaningful
        # to emit -- same treatment as Newpage above.
        return ""
    if kind == "FormulaMacro":
        # A LyX Math Macro definition (\newcommand{\X}{...}), not visible
        # content -- the expansion needs to be usable by any *later*
        # formula in the document that invokes \X, which MathJax can only
        # do via its own global `macros` config (docs/js/mathjax_config.js),
        # not anything embedded in the page itself. Every FormulaMacro in
        # this document has been transcribed there by hand; this just
        # suppresses the definition inset from rendering as literal text.
        return ""
    if kind == "Foot":
        # A real footnote (distinct from citations, which get their own
        # [^sec-n] numbering via cite_footnote_num()) -- collect the
        # rendered text and emit a reference marker; main() appends the
        # matching [^...]: definition at the bottom of the page alongside
        # the citation footnotes. "fn" in the marker keeps it from ever
        # colliding with a citation's plain numeric suffix on the same
        # page. sub_items' first lines are inset attributes (status
        # collapsed/open), which -- like Box/Float -- are skipped
        # naturally by only processing 'layout' items.
        text = "".join(
            render_items_inline(item[2], ctx) for item in sub_items if item[0] == "layout"
        ).strip()
        ctx.inline_footnotes.append(text)
        return f"[^{ctx.section_num}-fn{len(ctx.inline_footnotes)}]"
    # Unhandled inset kind
    ctx.unhandled_count += 1
    ctx.needs_review.append(f"Unhandled inset type: {spec!r}")
    inner = render_items_inline(sub_items, ctx)
    return f"<!-- UNHANDLED INSET {kind}: {inner[:80]} -->"


def render_formula_inset(sub_items, ctx):
    # sub_items are 'text' lines forming the raw LaTeX (Formula insets have
    # no nested layouts/insets in this document).
    raw_lines = [it[1] for it in sub_items if it[0] == "text"]
    raw = "\n".join(raw_lines).strip("\n")
    stripped = raw.strip()
    if stripped.startswith("$") and stripped.endswith("$") and stripped.count("$") == 2:
        inner = stripped[1:-1].strip()
        ctx.inline_formula_count += 1
        return "$" + inner + "$"
    ctx.display_formula_count += 1
    body = stripped
    if body.startswith("\\[") and body.endswith("\\]"):
        inner = body[2:-2].strip()
    else:
        inner = body
    return "\n\n\\[\n" + inner + "\n\\]\n\n"


def mathjax_eqn_id(label):
    """MathJax builds an equation's DOM id as "mjx-eqn:<label>", but first
    sanitizes the label -- confirmed empirically (only one label in this
    document contains a space, "eq:virtual work") that it replaces spaces
    with underscores, giving "mjx-eqn:eq:virtual_work", not a literal
    space. A link built from the raw label would point at a nonexistent
    id and silently fail to navigate to the right anchor.
    """
    return f"mjx-eqn:{label.replace(' ', '_')}"


def build_relative_link(target_dir, target_file, ctx, anchor=None):
    """Build a relative href from the current page (ctx.chapter_dir /
    ctx.section_file) to another page's #anchor, handling same-page,
    same-chapter-different-page, and cross-chapter cases. Every chapter
    lives in a sibling directory under docs/theory/ (chapter1/, chapter2/,
    ...), so a cross-chapter link is always exactly
    "../<target_dir>/<file>#anchor" -- no general-purpose path
    relativization is needed. `anchor=None` (e.g. linking to a chapter's
    first section, where there's no actual anchor id for the chapter's
    own label on that page) links to the bare page instead.
    """
    frag = f"#{anchor}" if anchor else ""
    same_page = target_file == ctx.section_file and target_dir == ctx.chapter_dir
    if same_page:
        return frag or "#"
    if target_dir == ctx.chapter_dir:
        return f"{target_file}{frag}"
    return f"../{target_dir}/{target_file}{frag}"


def render_command_inset(spec, sub_items, ctx):
    # spec like "CommandInset label" / "CommandInset ref" / "CommandInset citation"
    parts = spec.split(None, 1)
    subtype = parts[1] if len(parts) > 1 else ""
    attrs = {}
    cmd = None
    remaining_text = []
    for it in sub_items:
        if it[0] != "text":
            continue
        line = it[1]
        m = re.match(r'^LatexCommand\s+(\S+)\s*$', line)
        if m:
            cmd = m.group(1)
            continue
        m2 = re.match(r'^(\w+)\s+"([^"]*)"\s*$', line)
        if m2:
            attrs[m2.group(1)] = m2.group(2)
            continue
        if line.strip() == "":
            continue
        remaining_text.append(line)

    if subtype == "label":
        name = attrs.get("name", "")
        ctx.needs_review_label = name
        return f'<a id="{name}"></a>'
    if subtype == "ref":
        reference = attrs.get("reference", "")
        if cmd == "eqref":
            eq_entry = EQ_LABEL_REGISTRY.get(reference)
            if eq_entry and eq_entry["file"] and (eq_entry["file"] != ctx.section_file or eq_entry["dir"] != ctx.chapter_dir):
                # Cross-section (possibly cross-chapter): MathJax can't
                # resolve this (separate page, separate auto-numbering), so
                # resolve it statically instead of emitting \eqref{} (which
                # would just render as "???").
                label_text = f"({eq_entry['section']}-{eq_entry['number']})"
                link = build_relative_link(eq_entry["dir"], eq_entry["file"], ctx, mathjax_eqn_id(reference))
                return f"[{label_text}]({link})"
            return f"\\eqref{{{reference}}}"
        else:
            # A \ref{} to a Chapter's own label (e.g. "chap:dynamics") --
            # the published manual's own convention is "Chapter 3" with
            # just the number hyperlinked, not the chapter's title
            # repeated after the word "Chapter" already in the prose.
            # Checked ahead of LABEL_REGISTRY since it's a distinct
            # registry with different rendering rules (a chapter that
            # exists in the source but isn't converted yet still has a
            # correct *number* to show, just not a page to link to).
            chap_entry = CHAPTER_LABEL_REGISTRY.get(reference)
            if chap_entry:
                if chap_entry["file"]:
                    link = build_relative_link(chap_entry["dir"], chap_entry["file"], ctx)
                    return f"[{chap_entry['number']}]({link})"
                return str(chap_entry["number"])
            entry = LABEL_REGISTRY.get(reference)
            if entry and entry["file"]:
                if entry["title"] == "Figure":
                    # The source prose always writes the word "Figure"
                    # (optionally with a non-breaking space) immediately
                    # before this \ref{}, e.g. "(Figure \ref{fig17})" or
                    # "Figure~\ref{...}a-c." -- so the ref itself should
                    # resolve to just the figure's number, not repeat
                    # "Figure" again. Numbered per-page (matching the
                    # pymdownx.blocks.caption auto-numbering actually shown
                    # next to each figure), with a "<section>." prefix only
                    # when the reference points at a figure defined on a
                    # *different* page -- same convention as eqref's
                    # "(2.5-35)", per the user's explicit figure-numbering
                    # request.
                    if entry["section"] == ctx.section_num:
                        label_text = str(entry["fig_number"])
                    else:
                        label_text = f"{entry['section']}.{entry['fig_number']}"
                else:
                    label_text = entry["title"]
                link = build_relative_link(entry["dir"], entry["file"], ctx, reference)
                return f"[{label_text}]({link})"
            # A plain \ref{} (LatexCommand "ref", not "eqref") can still
            # target an equation label -- unusual (normally \eqref{} is
            # used for that, to get the auto-parenthesized number), but it
            # happens at least once in this document (eq87, referenced via
            # plain \ref from section 2.6) and is a real, resolvable label,
            # not a broken reference -- LABEL_REGISTRY only ever holds
            # subsection/figure labels, so it alone can't find it.
            eq_entry = EQ_LABEL_REGISTRY.get(reference)
            if eq_entry and eq_entry["file"]:
                label_text = f"({eq_entry['section']}-{eq_entry['number']})"
                link = build_relative_link(eq_entry["dir"], eq_entry["file"], ctx, mathjax_eqn_id(reference))
                return f"[{label_text}]({link})"
            ctx.needs_review.append(f"Unresolved \\ref target: {reference!r}")
            return f"[{reference}](#{slugify_ref(reference)})"
    if subtype == "citation":
        key = attrs.get("key", "")
        keys = [k.strip() for k in key.split(",") if k.strip()]
        out = ""
        for k in keys:
            num = ctx.cite_footnote_num(k)
            out += f"[^{ctx.section_num}-{num}]"
        return out
    if subtype == "bibtex":
        # LaTeX's "generate a consolidated bibliography here" marker.
        # Irrelevant to this converter: citations already render as
        # per-page Markdown footnotes (via cite_footnote_num() above),
        # not a single end-of-document bibliography list.
        return ""
    ctx.unhandled_count += 1
    ctx.needs_review.append(f"Unhandled CommandInset subtype: {subtype!r}")
    return f"<!-- UNHANDLED CommandInset {subtype} -->"


def slugify_ref(reference):
    return slugify(reference)


def render_float(spec, sub_items, ctx):
    # spec = "Float figure" or "Float table"
    float_kind = spec.split(None, 1)[1] if len(spec.split()) > 1 else "figure"
    # sub_items contain layout 'Plain Layout' blocks: one with the Graphics
    # inset (image), and one with a Caption inset.
    image_md = ""
    caption_md = ""
    fig_anchor = ""
    for item in sub_items:
        if item[0] != "layout":
            continue
        kind, layout_spec, layout_items = item
        # scan this Plain Layout's items for Graphics / Caption insets
        for it in layout_items:
            if it[0] == "inset" and it[1].startswith("Graphics"):
                image_md = render_graphics(it[2], ctx)
            elif it[0] == "inset" and it[1].startswith("Caption"):
                caption_raw = render_items_inline(it[2], ctx).strip()
                # Extract any figure \label anchor emitted inline (LyX puts
                # the CommandInset label for a figure inside its caption)
                # and hoist it before the caption instead of inline in the
                # caption prose.
                anchor_match = LABEL_ANCHOR_RE.search(caption_raw)
                fig_anchor = anchor_match.group(0) if anchor_match else ""
                caption_md = LABEL_ANCHOR_RE.sub("", caption_raw).strip()
                caption_md = re.sub(r"\s+", " ", caption_md)
            elif it[0] == "inset" and it[1] == "CommandInset label" and not fig_anchor:
                # At least one figure in this document has its label as a
                # sibling of Caption within the same Plain Layout, not
                # embedded inside the caption text like every other one --
                # same anchor-hoisting outcome, just found a different way.
                for sub in it[2]:
                    if sub[0] == "text":
                        m = re.match(r'name\s+"([^"]+)"', sub[1].strip())
                        if m:
                            fig_anchor = f'<a id="{m.group(1)}"></a>'
    out = "\n\n"
    out += (fig_anchor + "\n\n" if fig_anchor else "") + image_md
    if caption_md:
        out += "\n\n/// figure-caption\n\n    " + caption_md + "\n\n///\n"
    return out + "\n"


IMG_ATTR_RE = re.compile(r'(!\[[^\]]*\]\([^)]*\))(?:\{: style="([^"]*)" \})?')


def center_images(content):
    """Inject centering CSS into every Markdown image's attr_list style in
    `content`, merging with any style already there (e.g. a LyX "scale"
    width from render_graphics). Used for a LyX \\align center wrapping a
    figure, since Markdown has no native image-centering syntax.
    """
    def repl(m):
        img_md, existing_style = m.group(1), m.group(2)
        center_css = "display:block; margin-left:auto; margin-right:auto;"
        style = f"{existing_style.rstrip().rstrip(';')}; {center_css}" if existing_style else center_css
        return f'{img_md}{{: style="{style}" }}'
    return IMG_ATTR_RE.sub(repl, content)


def render_graphics(sub_items, ctx):
    filename = None
    scale = None
    for it in sub_items:
        if it[0] == "text":
            m = re.match(r"^\s*filename\s+(.+)$", it[1])
            if m:
                filename = m.group(1).strip()
            m2 = re.match(r"^\s*scale\s+(\d+(?:\.\d+)?)\s*$", it[1])
            if m2:
                scale = m2.group(1)
    if not filename:
        ctx.needs_review.append("Graphics inset with no filename")
        return "<!-- MISSING GRAPHICS FILENAME -->"
    ctx.fig_counter += 1
    base = os.path.basename(filename)
    name_no_ext = os.path.splitext(base)[0]
    ctx.needs_review.append(
        f"Figure image '{base}' referenced (source path '{filename}') -- "
        f"placeholder written to figs/{base}, original binary not available in inputs."
    )
    # LyX's "scale NN" is the percentage of the image's natural size it
    # should be displayed at (all three Chapter 2 figures specify 50, but
    # the converter previously dropped this attribute entirely, embedding
    # each image at full native pixel size with no width constraint --
    # e.g. FigKinematicsContinuum.png is 951x992px, requiring the reader
    # to scroll to see it in full). attr_list (already enabled in
    # mkdocs.yml) lets us carry the scale through as inline CSS.
    # Note: unlike heading attr_list syntax (which needs a leading space
    # before "{:"), attr_list requires the block glued directly onto an
    # inline image with no space, or it's left as literal trailing text.
    attr = f'{{: style="width:{scale}%" }}' if scale else ""
    return f"![{name_no_ext}](figs/{base}){attr}"


TABLE_CELL_SPAN_RE = re.compile(r'multicolumn="[12]"|multirow="[1-9]')
TABLE_ROW_BREAK = "\x01"


def render_tabular(sub_items, ctx):
    """LyX's tabular format is *not* the usual \\begin_layout/\\begin_inset
    keyword syntax -- inside a Tabular inset it switches to an embedded
    pseudo-XML dialect (<lyxtabular>, <column>, <row>, <cell>). parse_flat
    doesn't understand that dialect, so these lines just come through as
    plain ('text', line) items; the only *real* structure inside them that
    parse_flat *does* recognize is each cell's content, wrapped in an
    ordinary \\begin_inset Text ... \\end_inset (which is correctly
    balanced/parsed already). So: use the <row>/<cell> text markers purely
    as delimiters to group the Text insets we do get, and render each
    cell's content the normal way.

    Basic Markdown tables can't represent merged cells (colspan/rowspan);
    none occur anywhere in this document as of this writing, so this
    covers every real table, but a merged cell is flagged for manual
    review rather than silently producing a misaligned table if one ever
    shows up.
    """
    rows = []
    current_row = None
    has_spanning = False
    for item in sub_items:
        if item[0] == "text":
            line = item[1].strip()
            if line.startswith("<row"):
                current_row = []
            elif line == "</row>":
                if current_row is not None:
                    rows.append(current_row)
                current_row = None
            elif line.startswith("<cell") and TABLE_CELL_SPAN_RE.search(line):
                has_spanning = True
        elif item[0] == "inset" and item[1] == "Text" and current_row is not None:
            cell_parts = [
                render_items_inline(sub[2], ctx) for sub in item[2] if sub[0] == "layout"
            ]
            cell_text = re.sub(r"\s+", " ", " ".join(cell_parts)).strip()
            cell_text = cell_text.replace("|", "\\|")
            current_row.append(cell_text)

    if has_spanning:
        ctx.needs_review.append(
            "Tabular inset has merged cells (multicolumn/multirow) -- not "
            "representable in plain Markdown tables; rendered best-effort."
        )
    if not rows:
        ctx.needs_review.append("Tabular inset had no parsable rows")
        return "\n\n<!-- TABLE: could not parse -->\n\n"

    ncols = max(len(r) for r in rows)
    pad = lambda r: r + [""] * (ncols - len(r))  # noqa: E731

    header, *body = rows
    lines = ["| " + " | ".join(pad(header)) + " |", "|" + "|".join(["---"] * ncols) + "|"]
    lines += ["| " + " | ".join(pad(r)) + " |" for r in body]
    table_md = TABLE_ROW_BREAK.join(lines)

    # A Markdown table has no native alignment syntax, and attr_list
    # doesn't attach to one (confirmed: appending "{: ... }" right after a
    # table gets swallowed as a bogus extra table row instead). The only
    # way to center it is a raw HTML wrapper -- which needs the
    # md_in_html extension (see build.py) and a markdown="1" attribute, or
    # the nested table syntax is left as unprocessed literal text instead
    # of being parsed as a real <table>.
    return (
        '\n\n<div markdown="1" style="display: flex; justify-content: center;">\n\n'
        + table_md
        + "\n\n</div>\n\n"
    )


# -----------------------------------------------------------------------
# Section 6: Paragraph-level rendering (Standard / Itemize / Enumerate / Quote)
# -----------------------------------------------------------------------

def render_paragraph(layout_kind, items, ctx):
    text = render_items_inline(items, ctx)
    text = text.strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def format_list_item(marker, body):
    """Render a single Markdown list item, indenting any continuation
    lines (e.g. a display-equation block LyX nests inside an Enumerate/
    Itemize paragraph) so they stay part of the same list item -- and the
    same list -- instead of breaking out into their own top-level
    paragraph. An un-indented line after a blank line ends a Markdown
    list, which would make every subsequent item start a brand-new
    <ol> that restarts numbering at 1."""
    lines = body.split("\n")
    out = [f"{marker} {lines[0]}"]
    for line in lines[1:]:
        out.append("    " + line if line.strip() else "")
    return "\n".join(out)


def render_section_body(items, ctx, section_num, section_title, level_base=2):
    """items: list of top-level ('layout', kind, subitems) for everything
    following the Section header line, up to (not including) the next
    top-level Section."""
    md_parts = []
    heading_counters = [0, 0, 0]  # subsection, subsubsection depth trackers (informational)
    prev_spec = None  # previous top-level layout's spec, for Example/Theorem* continuation (see below)

    for item in items:
        if item[0] != "layout":
            # A blank text line is just LyX's between-layout formatting noise
            # and doesn't break an Example/Theorem* continuation run below.
            # Anything else non-blank at this level -- concretely,
            # \begin_deeper/\end_deeper, which LyX emits around an
            # indented-but-still-top-level paragraph and doesn't match
            # INSET_RE/LAYOUT_RE -- is structurally significant (confirmed
            # against Appendix A.1's two Theorem* environments: the second
            # one is wrapped in \begin_deeper/\end_deeper and states an
            # unrelated fact, not a continuation of the first), so it does
            # break the run.
            if item[0] == "text" and item[1].strip() == "":
                continue
            prev_spec = None
            continue
        kind, spec, sub_items = item
        if spec == "Subsection":
            raw_title = render_items_inline(sub_items, ctx).strip()
            title, anchor = extract_heading_label(raw_title)
            attr = f" {{: #{anchor} }}" if anchor else ""
            md_parts.append(f"\n\n## {title}{attr}\n")
            # NOTE: do not re-register this label here. The prescan pass in
            # main() already registered it (correctly, with its real
            # filename) before rendering began; re-registering here with no
            # filename argument used to silently overwrite that entry with
            # file=None the moment *this* section got rendered, breaking
            # any *later*-rendered section's cross-page link to it (it
            # would resolve to a same-page "#anchor" instead) -- confirmed
            # this was live: 2.10's reference to 2.6.8 was broken.
        elif spec == "Subsubsection":
            raw_title = render_items_inline(sub_items, ctx).strip()
            title, anchor = extract_heading_label(raw_title)
            attr = f" {{: #{anchor} }}" if anchor else ""
            md_parts.append(f"\n\n### {title}{attr}\n")
            # see NOTE above -- same fix, same reason.
        elif spec == "Standard":
            body = render_paragraph(spec, sub_items, ctx)
            if body:
                md_parts.append("\n\n" + body + "\n")
        elif spec in ("Quote", "Quotation"):
            body = render_paragraph(spec, sub_items, ctx)
            quoted = "\n".join("> " + l for l in body.splitlines())
            md_parts.append("\n\n" + quoted + "\n")
        elif spec == "Enumerate":
            body = render_paragraph(spec, sub_items, ctx)
            md_parts.append("\n\n" + format_list_item("1.", body) + "\n")
        elif spec == "Itemize":
            body = render_paragraph(spec, sub_items, ctx)
            md_parts.append("\n\n" + format_list_item("-", body) + "\n")
        elif spec == "Plain" or spec.startswith("Plain "):
            body = render_paragraph(spec, sub_items, ctx)
            if body:
                md_parts.append("\n\n" + body + "\n")
        elif spec == "Paragraph":
            # LaTeX's \paragraph{} heading level -- one level deeper than
            # Subsubsection in the Chapter > Section > Subsection >
            # Subsubsection > Paragraph sectioning hierarchy.
            raw_title = render_items_inline(sub_items, ctx).strip()
            title, anchor = extract_heading_label(raw_title)
            attr = f" {{: #{anchor} }}" if anchor else ""
            md_parts.append(f"\n\n#### {title}{attr}\n")
        elif spec == "Example":
            # Numbered environment from the theorems-ams LyX module (no
            # title of its own in the source -- LaTeX auto-numbers it).
            # In LyX/LaTeX, consecutive same-style paragraphs continue the
            # *same* environment instance rather than each starting a new
            # one -- a run of several adjacent "Example" layouts (e.g. a
            # problem statement, then "Solution.", then the derivation) is
            # one logical example with several paragraphs, not one example
            # per layout. So the counter only advances -- and a fresh bold
            # label is only emitted -- when the *previous* top-level item
            # wasn't also "Example"; a continuation paragraph is appended
            # to the current example's body instead (confirmed against
            # Appendix A.1, where several examples span 2-4 consecutive
            # Example layouts in the source). Label registration for
            # \ref{} already happened in the pre-scan pass (same reason
            # Subsection/Subsubsection don't re-register here); the
            # pre-scan's own counter must apply this identical continuation
            # rule so the *displayed* number matches what \ref{} resolved
            # to. Rendered as a bold run-in label followed by the body in
            # the normal text flow -- matching the published manual's
            # plain LaTeX theorem-style numbering -- not a Material
            # admonition callout box (which the original document doesn't
            # use).
            raw_body = render_paragraph(spec, sub_items, ctx)
            body, _ = extract_heading_label(raw_body)
            if prev_spec == "Example":
                md_parts.append(f"\n\n{body}\n")
            else:
                ctx.example_counter += 1
                md_parts.append(f"\n\n**Example {ctx.example_counter}.** {body}\n")
        elif spec == "Theorem*":
            # Unnumbered ("starred") environment from theorems-ams; same
            # plain run-in treatment, and the same consecutive-paragraph
            # continuation rule, as Example above.
            raw_body = render_paragraph(spec, sub_items, ctx)
            body, _ = extract_heading_label(raw_body)
            if prev_spec == "Theorem*":
                md_parts.append(f"\n\n{body}\n")
            else:
                md_parts.append(f"\n\n**Theorem.** {body}\n")
        else:
            ctx.needs_review.append(f"Unhandled top-level layout kind in section body: {spec!r}")
            body = render_paragraph(spec, sub_items, ctx)
            if body:
                md_parts.append("\n\n" + body + "\n")
        prev_spec = spec

    text = "".join(md_parts)
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
    return text


LABEL_ANCHOR_RE = re.compile(r'<a id="([^"]+)"></a>')

# Global registry mapping a LyX \label name -> (section_number, file, title)
# populated as sections are rendered, and used to resolve
# \begin_inset CommandInset ref / LatexCommand ref (non-eqref) cross
# references to markdown links. Since sections are rendered in document
# order and \ref targets in this chapter always point to *earlier or
# same-chapter* sections/figures, a single forward pass is sufficient;
# any reference that cannot be resolved is left as a best-effort anchor
# link and flagged in needs_review.
LABEL_REGISTRY = {}

# Global registry mapping a Chapter's own \label{} (e.g.
# "chap:continuum-mechanics") -> {"number": N, "file": ..., "dir": ...}.
# Populated for *every* chapter in the source (not just converted ones) so
# a \ref{} to a chapter can always show the correct chapter number, even
# if that chapter isn't converted yet -- matching the published manual's
# own convention of "Chapter 3" (just the number, hyperlinked) rather than
# repeating the chapter's title after the word "Chapter". "file"/"dir" stay
# None for a chapter that hasn't been converted, which render_command_inset
# uses to decide whether the number should be a link or plain text.
CHAPTER_LABEL_REGISTRY = {}

# Global registry mapping an equation \label{} name -> {"section": sec_num,
# "file": fname, "number": N}, where N is that equation's 1-indexed
# position among AMS-numbered (\begin{equation}-wrapped) display equations
# on its own page. Populated by prescan_equation_labels() before rendering.
#
# Why this exists: each Section becomes a separately-loaded HTML page, and
# MathJax's tags:'ams' auto-numbering is per-page -- it has no way to know
# about a \label{} defined on a *different* page, so a same-chapter
# \eqref{} to another section's equation renders as "???" with no way to
# resolve it client-side. The published FEBio Theory Manual hits the same
# problem (it paginates even more granularly, at the subsection level) and
# solves it by replacing such cross-page \eqref{}s with static resolved
# text (e.g. "eq.(2.5.4-2)") linked directly to the target page's anchor,
# rather than relying on live cross-page numbering. render_command_inset's
# eqref branch does the same thing here, adapted to this pilot's coarser
# per-*section* (not per-subsection) pagination -- e.g. "(2.5-4)" -- and
# linking to MathJax's own auto-generated "mjx-eqn:<label>" anchor id
# (verified empirically against the rendered DOM; stable as long as the
# MathJax CDN stays on v3.x). Same-page \eqref{}s are left untouched since
# MathJax already resolves those correctly on its own.
EQ_LABEL_REGISTRY = {}


def prescan_equation_labels(items, sec_num, fname, counter, chapter_dir=None):
    """Walk a section's body items (pre-render) to find display-equation
    \\label{} occurrences and register each one's 1-indexed position among
    that page's AMS-numbered equations into EQ_LABEL_REGISTRY. `counter`
    is a mutable single-element list so the running count can be threaded
    through recursive calls; pass a fresh [0] per section.

    Only bodies starting with "\\begin{equation}" are counted, since that's
    the only outer-wrapper pattern MathJax's tags:'ams' actually assigns a
    visible number to in this document -- confirmed empirically against
    the whole corpus: every one of the 29 bare "\\[...\\]" (no environment)
    and 2 standalone "\\begin{aligned}...\\end{aligned}" display formulas in
    Chapter 2 is unlabeled, i.e. nothing here ever needs to reference them.
    """
    for item in items:
        if item[0] == "inset" and item[1] == "Formula":
            raw = "\n".join(it[1] for it in item[2] if it[0] == "text").strip()
            if raw.startswith("\\begin{equation}"):
                counter[0] += 1
                for lbl in re.findall(r"\\label\{([^}]+)\}", raw):
                    EQ_LABEL_REGISTRY[lbl] = {
                        "section": sec_num,
                        "file": fname,
                        "dir": chapter_dir,
                        "number": counter[0],
                    }
        elif item[0] in ("inset", "layout"):
            prescan_equation_labels(item[2], sec_num, fname, counter, chapter_dir)


def strip_label_markup(title):
    return LABEL_ANCHOR_RE.sub("", title).strip()


def extract_heading_label(raw_title):
    """Given a rendered heading title that may contain an inline
    <a id="..."></a> anchor marker (from a LyX CommandInset label attached
    to the Section/Subsection layout), return (clean_title, anchor_or_None).
    """
    m = LABEL_ANCHOR_RE.search(raw_title)
    anchor = m.group(1) if m else None
    clean = LABEL_ANCHOR_RE.sub("", raw_title).strip()
    return clean, anchor


def register_label(anchor, section_num, title, filename=None, chapter_dir=None, fig_number=None):
    LABEL_REGISTRY[anchor] = {
        "section": section_num,
        "title": title,
        "file": filename,
        "dir": chapter_dir,
        "fig_number": fig_number,
    }


# -----------------------------------------------------------------------
# Section 7: Top-level document walk: split into Chapter/Section units
# -----------------------------------------------------------------------

def read_lyx_lines(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return [line.rstrip("\n") for line in f.readlines()]


def main():
    os.makedirs(DOCS_THEORY_ROOT, exist_ok=True)

    bib = parse_bib(BIB_PATH)
    lines = read_lyx_lines(LYX_PATH)
    top_items = top_level_parse(lines)
    n = len(top_items)

    # Find every Chapter and Section layout (siblings, since LyX layouts of
    # different "depth" are all flat \begin_layout entries at the same
    # nesting level -- LyX does not nest Section inside Chapter in the
    # token stream).
    boundaries = []  # (index_in_top_items, kind, spec_items)
    for idx, item in enumerate(top_items):
        if item[0] == "layout" and item[1] in ("Chapter", "Section"):
            boundaries.append((idx, item[1], item[2]))

    if not boundaries:
        print("ERROR: no Chapter/Section layouts found", file=sys.stderr)
        sys.exit(1)

    chapter_boundaries = [b for b in boundaries if b[1] == "Chapter"]
    if not chapter_boundaries:
        print("ERROR: no Chapter layouts found", file=sys.stderr)
        sys.exit(1)

    # ---- Pass 1: walk every Chapter in the *whole* manual to compute each
    # one's absolute chapter number (1-indexed position in the source) and
    # which Section boundaries fall under it. This runs regardless of
    # CHAPTERS_TO_CONVERT so numbering ("3.1", not "1.1", for the third
    # chapter's first section) and cross-chapter \ref{}/\eqref{} targets
    # stay correct even when we're only converting a subset. ----
    chapters_meta = []
    in_appendix = False   # LyX's \start_of_appendix marker switches numbering
    appendix_index = 0    # from numeric chapters to lettered appendices (A, B,
                           # ...) from that chapter onward, mirroring LaTeX's
                           # \appendix command -- see the "Tensor Calculus"
                           # chapter, whose heading contains this exact marker.
    for c_idx, (c_bidx, _, c_sub_items) in enumerate(chapter_boundaries):
        chap_num = c_idx + 1
        if any(it[0] == "text" and it[1].strip() == "\\start_of_appendix" for it in c_sub_items):
            in_appendix = True
        if in_appendix:
            appendix_index += 1
            chap_display = string.ascii_uppercase[appendix_index - 1]
        else:
            chap_display = str(chap_num)
        raw_chap_title = render_items_inline(c_sub_items, RenderCtxDummy()).strip()
        # A Chapter's own \label{} (e.g. "chap:continuum-mechanics") is
        # embedded directly in its heading layout, the same way Section
        # titles carry theirs -- confirmed for both Chapter 2 and Chapter 3
        # ("\begin_layout Chapter\nContinuum Mechanics\n\begin_inset
        # CommandInset label..."), so it must be captured the same way,
        # via extract_heading_label(), not just stripped and discarded.
        chap_title, chap_label = extract_heading_label(raw_chap_title)
        chap_end_idx = chapter_boundaries[c_idx + 1][0] if c_idx + 1 < len(chapter_boundaries) else n
        sec_boundaries = [b for b in boundaries if b[1] == "Section" and c_bidx < b[0] < chap_end_idx]
        # Chapter 1 instead carries its label in a separate Standard
        # paragraph right after the heading rather than embedded in it --
        # scan the chapter's intro (before its first Section) for that
        # pattern too, so both are covered.
        if not chap_label:
            intro_end = sec_boundaries[0][0] if sec_boundaries else chap_end_idx
            for item in top_items[c_bidx + 1: intro_end]:
                if item[0] == "inset" and item[1] == "CommandInset label":
                    for it in item[2]:
                        if it[0] == "text":
                            m = re.match(r'name\s+"([^"]+)"', it[1].strip())
                            if m:
                                chap_label = m.group(1)
                                break
        if chap_label:
            CHAPTER_LABEL_REGISTRY[chap_label] = {"number": chap_display, "file": None, "dir": None}
        chapters_meta.append({
            "chap_num": chap_num,
            "chap_display": chap_display,
            "is_appendix": in_appendix,
            "title": chap_title,
            "label": chap_label,
            "start_idx": c_bidx,
            "end_idx": chap_end_idx,
            "section_boundaries": sec_boundaries,
        })

    # ---- Pass 2: for chapters actually being converted this run, split
    # each into per-Section pages and register every Section's own label
    # (if any) up front, exactly as before. ----
    all_sections_data = []
    chapters_output = []  # [{"chap_num", "title", "dir", "sections": [sec_data, ...]}]
    for chap in chapters_meta:
        chap_num = chap["chap_num"]
        if chap_num not in CHAPTERS_TO_CONVERT:
            continue
        chap_dir = f"chapter{chap['chap_display']}"
        out_dir = os.path.join(DOCS_THEORY_ROOT, chap_dir)
        os.makedirs(out_dir, exist_ok=True)
        os.makedirs(os.path.join(out_dir, "figs"), exist_ok=True)

        sec_boundaries = chap["section_boundaries"]
        chap_sections = []
        # A Chapter can carry real content of its own -- not just a label
        # -- in Standard paragraph(s) between the Chapter heading and its
        # first Section (e.g. Chapter 6 "Dynamics" opens with 4 equations
        # before section 6.1 even starts). There's no separate
        # chapter-landing page in this site's structure, and until this
        # fix that content had nowhere to go at all -- silently dropped
        # entirely, not just its label (confirmed: exactly explains a
        # formula-count reconciliation gap against source). Prepend it to
        # the first section's own body instead.
        intro_body_items = top_items[chap["start_idx"] + 1: sec_boundaries[0][0]] if sec_boundaries else []
        for k, (bidx, spec, sub_items) in enumerate(sec_boundaries):
            title = render_items_inline(sub_items, RenderCtxDummy()).strip()
            label_name = None
            lm = re.search(r'<a id="([^"]+)"></a>', title)
            if lm:
                label_name = lm.group(1)
            title = strip_label_markup(title)
            end_idx = sec_boundaries[k + 1][0] if k + 1 < len(sec_boundaries) else chap["end_idx"]
            body_items = top_items[bidx + 1: end_idx]
            if k == 0 and intro_body_items:
                body_items = intro_body_items + body_items
            sec_num = f"{chap['chap_display']}.{k + 1}"
            slug = slugify(title)
            fname = f"{sec_num}-{slug}.md"
            sec_data = {
                "chap_num": chap_num,
                "chapter_dir": chap_dir,
                "number": k + 1,
                "sec_num": sec_num,
                "title": title,
                "label": label_name,
                "items": body_items,
                "file": fname,
                "out_dir": out_dir,
            }
            all_sections_data.append(sec_data)
            chap_sections.append(sec_data)
            if label_name:
                register_label(label_name, sec_num, title, fname, chap_dir)

        # A Chapter's own \label{} (already found in Pass 1 and registered
        # into CHAPTER_LABEL_REGISTRY with file/dir still None) now has a
        # real target: there's no dedicated chapter-landing page in this
        # site's structure, so point it at the chapter's first section.
        if chap_sections and chap["label"]:
            CHAPTER_LABEL_REGISTRY[chap["label"]]["file"] = chap_sections[0]["file"]
            CHAPTER_LABEL_REGISTRY[chap["label"]]["dir"] = chap_dir

        chapters_output.append({
            "chap_num": chap_num,
            "chap_display": chap["chap_display"],
            "is_appendix": chap["is_appendix"],
            "title": chap["title"],
            "dir": chap_dir,
            "sections": chap_sections,
        })

    if not all_sections_data:
        print(f"ERROR: none of the chapters in CHAPTERS_TO_CONVERT {CHAPTERS_TO_CONVERT} were found", file=sys.stderr)
        sys.exit(1)

    # ---- Pre-scan pass: walk every section's body items (without full
    # rendering) purely to discover \label anchors on Subsection /
    # Subsubsection headings and Figure captions, so that \ref{} cross
    # references anywhere in the converted chapters (including *forward*
    # references, and references *across* chapters) can be resolved to the
    # correct page + anchor before we do the real rendering pass below. ----
    def prescan(items, sec_num, fname, chapter_dir):
        example_counter = [0]  # per-section, mirrors ctx.example_counter in the render pass
        fig_counter = [0]  # per-section, mirrors ctx.fig_counter in the render pass
        prev_spec = [None]  # mirrors render_section_body's Example/Theorem* continuation rule
        for item in items:
            if item[0] != "layout":
                # see the matching case in render_section_body(): a blank
                # text line doesn't break a same-kind run, but anything
                # else (e.g. \begin_deeper) does.
                if item[0] == "text" and item[1].strip() == "":
                    continue
                prev_spec[0] = None
                continue
            _, spec, sub_items = item
            if spec in ("Subsection", "Subsubsection"):
                raw_title = render_items_inline(sub_items, RenderCtxDummy()).strip()
                clean, anchor = extract_heading_label(raw_title)
                if anchor:
                    register_label(anchor, sec_num, clean, fname, chapter_dir)
            elif spec == "Example":
                # Numbered (from the theorems-ams LyX module), so a \ref{}
                # to one needs a resolved title like "Example 3" -- counted
                # per-page here to exactly mirror ctx.example_counter in
                # render_section_body() below (same items, same order,
                # same continuation rule: consecutive "Example" layouts are
                # one example's paragraphs, not one example each -- see the
                # comment there).
                if prev_spec[0] != "Example":
                    example_counter[0] += 1
                raw_body = render_items_inline(sub_items, RenderCtxDummy()).strip()
                _, anchor = extract_heading_label(raw_body)
                if anchor:
                    register_label(anchor, sec_num, f"Example {example_counter[0]}", fname, chapter_dir)
            # descend into floats/nested layouts to find figure/table labels
            prescan_nested(sub_items, sec_num, fname, chapter_dir, fig_counter)
            prev_spec[0] = spec

    def prescan_nested(items, sec_num, fname, chapter_dir, fig_counter):
        for item in items:
            if item[0] == "inset" and item[1].startswith("Graphics"):
                # Mirrors render_graphics()'s ctx.fig_counter increment: counts
                # every image (Float-wrapped or bare) in document order, so a
                # figure \ref{}'s per-page number matches what
                # pymdownx.blocks.caption actually displays next to it.
                fig_counter[0] += 1
            if item[0] == "inset" and item[1].startswith("Float"):
                for sub in item[2]:
                    if sub[0] == "layout":
                        anchor = None
                        for it in sub[2]:
                            if it[0] == "inset" and it[1].startswith("Graphics"):
                                fig_counter[0] += 1
                            elif it[0] == "inset" and it[1].startswith("Caption"):
                                raw = render_items_inline(it[2], RenderCtxDummy()).strip()
                                _, anchor_in_caption = extract_heading_label(raw)
                                anchor = anchor or anchor_in_caption
                            elif it[0] == "inset" and it[1] == "CommandInset label" and not anchor:
                                # See the matching case in render_float():
                                # at least one figure has its label as a
                                # sibling of Caption, not embedded in it.
                                for it2 in it[2]:
                                    if it2[0] == "text":
                                        m = re.match(r'name\s+"([^"]+)"', it2[1].strip())
                                        if m:
                                            anchor = m.group(1)
                        if anchor:
                            register_label(anchor, sec_num, "Figure", fname, chapter_dir, fig_number=fig_counter[0])
            elif item[0] in ("inset", "layout"):
                prescan_nested(item[2], sec_num, fname, chapter_dir, fig_counter)

    for sec in all_sections_data:
        prescan(sec["items"], sec["sec_num"], sec["file"], sec["chapter_dir"])
        prescan_equation_labels(sec["items"], sec["sec_num"], sec["file"], [0], sec["chapter_dir"])

    # ---- Render pass ----
    section_stats = []

    for sec in all_sections_data:
        sec_num = sec["sec_num"]
        fname = sec["file"]
        ctx = RenderCtx(bib, sec_num, fname, sec["chapter_dir"])
        body_md = render_section_body(sec["items"], ctx, sec_num, sec["title"])

        # Build footnotes block
        footnote_lines = []
        for key in ctx.citations_used:
            num = ctx.citation_index[key]
            fields = bib.get(key)
            text = format_citation(key, fields)
            footnote_lines.append(f"[^{sec_num}-{num}]: {text}")
            if not fields:
                ctx.needs_review.append(f"Citation key '{key}' not found in FEBio3.bib")
        for i, foot_text in enumerate(ctx.inline_footnotes, 1):
            footnote_lines.append(f"[^{sec_num}-fn{i}]: {foot_text}")

        page_attr = f" {{: #{sec['label']} }}" if sec.get("label") else ""
        page = f"# {sec_num} {sec['title']}{page_attr}\n\n"
        page += body_md.strip() + "\n"
        if footnote_lines:
            page += "\n\n" + "\n".join(footnote_lines) + "\n"

        out_path = os.path.join(sec["out_dir"], fname)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(page)

        section_stats.append({
            "section": sec_num,
            "title": sec["title"],
            "file": fname,
            "chapter": sec["chap_num"],
            "inline_formulas": ctx.inline_formula_count,
            "display_formulas": ctx.display_formula_count,
            "citations": len(ctx.citations_used),
            "figures": ctx.fig_counter,
            "unhandled": ctx.unhandled_count,
            "needs_review": ctx.needs_review,
        })

        STATS["totals"]["inline_formulas"] += ctx.inline_formula_count
        STATS["totals"]["display_formulas"] += ctx.display_formula_count
        STATS["totals"]["citations"] += len(ctx.citations_used)
        STATS["totals"]["figures"] += ctx.fig_counter
        STATS["totals"]["unhandled"] += ctx.unhandled_count

    STATS["sections"] = section_stats
    STATS["chapters"] = [
        {
            "chap_num": c["chap_num"],
            "chap_display": c["chap_display"],
            "is_appendix": c["is_appendix"],
            "title": c["title"],
            "dir": c["dir"],
            "nav": [
                [f"{s['sec_num']} {s['title']}", f"theory/{c['dir']}/{s['file']}"]
                for s in c["sections"]
            ],
        }
        for c in chapters_output
    ]

    with open(os.path.join(ROOT, "tools", "_stats.json"), "w", encoding="utf-8") as f:
        json.dump(STATS, f, indent=2)

    print(f"Converted {len(all_sections_data)} sections across {len(chapters_output)} chapters.")
    print(f"Totals: {STATS['totals']}")


class RenderCtxDummy(RenderCtx):
    """Used only for lightweight title extraction where citation/formula
    bookkeeping is irrelevant."""
    def __init__(self):
        super().__init__({}, "x")


if __name__ == "__main__":
    main()
