#!/usr/bin/env python3
"""
lyx2md.py -- Deterministic LyX -> Markdown converter for the FEBio Theory
Manual, Chapter 2 (Continuum Mechanics).

No external dependencies (stdlib only).

Usage:
    python3 tools/lyx2md.py

Reads (checked in this order so the repo is self-contained for CI/GitHub
Actions, but still picks up live edits from the original workspace input
directory during local development):
    source/ch2.lyx           (vendored copy, checked into this repo)
    source/FEBio3.bib
    ../febio-docs/ch2.lyx    (fallback: sibling workspace dir, if present)
    ../febio-docs/FEBio3.bib

Writes:
    docs/theory/chapter2/2.N-slug.md   (one file per top-level \begin_layout Section)
    tools/_nav.json                    (nav entries consumed by build.py)
    tools/_stats.json                  (conversion statistics consumed by build.py / CONVERSION_NOTES)

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
    os.path.join(ROOT, "source", "ch2.lyx"),
    os.path.join(ROOT, "..", "febio-docs", "ch2.lyx"),
)
BIB_PATH = _first_existing(
    os.path.join(ROOT, "source", "FEBio3.bib"),
    os.path.join(ROOT, "..", "febio-docs", "FEBio3.bib"),
)
OUT_DIR = os.path.join(ROOT, "docs", "theory", "chapter2")
FIGS_DIR = os.path.join(OUT_DIR, "figs")

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

ALIGN_RE = re.compile(r"^\\align\s+\w+\s*$")
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
    def __init__(self, bib, section_num, section_file=None):
        self.bib = bib
        self.section_num = section_num       # e.g. "2.1"
        self.section_file = section_file     # e.g. "2.1-vectors-and-tensors.md"
        self.citations_used = []             # ordered list of (key, footnote_index)
        self.citation_index = {}             # key -> footnote number within this page
        self.eq_counter = 0                  # per-section equation counter
        self.fig_counter = 0
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

    prev = None
    out = text
    # iterate a few times in case adjacent fixes reveal new fixable spans
    for _ in range(3):
        out = EMPHASIS_SPAN_RE.sub(repl, out)
        if out == prev:
            break
        prev = out
    return out


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
    return out


INSET_HEAD_RE = re.compile(r"^(\S+)(?:\s+(.*))?$")


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
        # Evaluate: usually empty decorative ERT; render inline text if any
        text = render_items_inline(sub_items, ctx)
        text = text.strip()
        if text and text not in ("", "\\-"):
            ctx.needs_review.append(f"ERT inset with content: {text!r}")
            return f"<!-- ERT: {text} -->"
        return ""
    if kind == "Float":
        return render_float(spec, sub_items, ctx)
    if kind == "Caption":
        return render_items_inline(sub_items, ctx)
    if kind == "Graphics":
        return render_graphics(sub_items, ctx)
    if kind == "Tabular":
        return render_tabular(sub_items, ctx)
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
            return f"\\eqref{{{reference}}}"
        else:
            entry = LABEL_REGISTRY.get(reference)
            if entry:
                label_text = entry["title"] if entry["title"] != "Figure" else f"Figure ({entry['section']})"
                target_file = entry["file"] or ""
                link = f"{target_file}#{reference}" if target_file and target_file != ctx.section_file else f"#{reference}"
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
    ctx.fig_counter += 1
    out = "\n\n"
    out += (fig_anchor + "\n\n" if fig_anchor else "") + image_md
    if caption_md:
        out += "\n\n/// figure-caption\n\n    " + caption_md + "\n\n///\n"
    return out + "\n"


def render_graphics(sub_items, ctx):
    filename = None
    for it in sub_items:
        if it[0] == "text":
            m = re.match(r"^\s*filename\s+(.+)$", it[1])
            if m:
                filename = m.group(1).strip()
    if not filename:
        ctx.needs_review.append("Graphics inset with no filename")
        return "<!-- MISSING GRAPHICS FILENAME -->"
    base = os.path.basename(filename)
    name_no_ext = os.path.splitext(base)[0]
    ctx.needs_review.append(
        f"Figure image '{base}' referenced (source path '{filename}') -- "
        f"placeholder written to figs/{base}, original binary not available in inputs."
    )
    return f"![{name_no_ext}](figs/{base})"


def render_tabular(sub_items, ctx):
    # Not present in ch2.lyx (no Tabular insets), but implemented for completeness.
    rows = []
    for kind, spec, items in sub_items:
        if kind == "inset" and spec.startswith("Row") or spec == "Row":
            pass
    # Fallback generic renderer: look for nested 'Cell' insets grouped by 'Row'
    # LyX tabular format: features nested insets we won't fully model; if
    # encountered, flag for manual review.
    ctx.needs_review.append("Tabular inset encountered -- rendered best-effort; verify manually.")
    return "<!-- TABLE: manual review needed -->"


# -----------------------------------------------------------------------
# Section 6: Paragraph-level rendering (Standard / Itemize / Enumerate / Quote)
# -----------------------------------------------------------------------

def render_paragraph(layout_kind, items, ctx):
    text = render_items_inline(items, ctx)
    text = text.strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def render_section_body(items, ctx, section_num, section_title, level_base=2):
    """items: list of top-level ('layout', kind, subitems) for everything
    following the Section header line, up to (not including) the next
    top-level Section."""
    md_parts = []
    heading_counters = [0, 0, 0]  # subsection, subsubsection depth trackers (informational)

    for item in items:
        if item[0] != "layout":
            continue
        kind, spec, sub_items = item
        if spec == "Subsection":
            raw_title = render_items_inline(sub_items, ctx).strip()
            title, anchor = extract_heading_label(raw_title)
            attr = f" {{: #{anchor} }}" if anchor else ""
            md_parts.append(f"\n\n## {title}{attr}\n")
            if anchor:
                register_label(anchor, ctx.section_num, title)
        elif spec == "Subsubsection":
            raw_title = render_items_inline(sub_items, ctx).strip()
            title, anchor = extract_heading_label(raw_title)
            attr = f" {{: #{anchor} }}" if anchor else ""
            md_parts.append(f"\n\n### {title}{attr}\n")
            if anchor:
                register_label(anchor, ctx.section_num, title)
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
            md_parts.append(f"\n\n1. {body}\n")
        elif spec == "Itemize":
            body = render_paragraph(spec, sub_items, ctx)
            md_parts.append(f"\n\n- {body}\n")
        elif spec == "Plain" or spec.startswith("Plain "):
            body = render_paragraph(spec, sub_items, ctx)
            if body:
                md_parts.append("\n\n" + body + "\n")
        else:
            ctx.needs_review.append(f"Unhandled top-level layout kind in section body: {spec!r}")
            body = render_paragraph(spec, sub_items, ctx)
            if body:
                md_parts.append("\n\n" + body + "\n")

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


def register_label(anchor, section_num, title, filename=None):
    LABEL_REGISTRY[anchor] = {"section": section_num, "title": title, "file": filename}


# -----------------------------------------------------------------------
# Section 7: Top-level document walk: split into Chapter/Section units
# -----------------------------------------------------------------------

def read_lyx_lines(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return [line.rstrip("\n") for line in f.readlines()]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(FIGS_DIR, exist_ok=True)

    bib = parse_bib(BIB_PATH)
    lines = read_lyx_lines(LYX_PATH)
    top_items = top_level_parse(lines)

    # Find the Chapter layout and all top-level Section layouts (siblings,
    # since LyX layouts of different "depth" are all flat \begin_layout
    # entries at the same nesting level -- LyX does not nest Section inside
    # Chapter in the token stream).
    chapter_title = None
    sections = []  # list of (title, items_after_header_until_next_section)
    current_section_items = None
    pending_chapter_intro = []

    i = 0
    n = len(top_items)
    idx = 0
    # First pass: locate Chapter and Section boundaries
    boundaries = []  # (index_in_top_items, kind, spec)
    for idx, item in enumerate(top_items):
        if item[0] == "layout" and item[1] in ("Chapter", "Section"):
            boundaries.append((idx, item[1], item[2]))

    if not boundaries:
        print("ERROR: no Chapter/Section layouts found", file=sys.stderr)
        sys.exit(1)

    chapter_idx = boundaries[0][0]
    chapter_title = render_items_inline(boundaries[0][2], RenderCtxDummy()).strip()
    chapter_title = strip_label_markup(chapter_title)

    section_boundaries = [b for b in boundaries if b[1] == "Section"]

    sections_data = []
    for k, (bidx, spec, sub_items) in enumerate(section_boundaries):
        title = None
        # need ctx-less render for title extraction (labels are harmless placeholders)
        title = render_items_inline(sub_items, RenderCtxDummy()).strip()
        label_name = None
        lm = re.search(r'<a id="([^"]+)"></a>', title)
        if lm:
            label_name = lm.group(1)
        title = strip_label_markup(title)
        end_idx = section_boundaries[k + 1][0] if k + 1 < len(section_boundaries) else n
        body_items = top_items[bidx + 1: end_idx]
        sec_num = f"2.{k + 1}"
        slug = slugify(title)
        fname = f"{sec_num}-{slug}.md"
        sections_data.append({
            "number": k + 1,
            "sec_num": sec_num,
            "title": title,
            "label": label_name,
            "items": body_items,
            "file": fname,
        })
        if label_name:
            register_label(label_name, sec_num, title, fname)

    # ---- Pre-scan pass: walk every section's body items (without full
    # rendering) purely to discover \label anchors on Subsection /
    # Subsubsection headings and Figure captions, so that \ref{} cross
    # references anywhere in the chapter (including *forward* references)
    # can be resolved to the correct page + anchor before we do the real
    # rendering pass below. ----
    def prescan(items, sec_num, fname):
        for item in items:
            if item[0] != "layout":
                continue
            _, spec, sub_items = item
            if spec in ("Subsection", "Subsubsection"):
                raw_title = render_items_inline(sub_items, RenderCtxDummy()).strip()
                clean, anchor = extract_heading_label(raw_title)
                if anchor:
                    register_label(anchor, sec_num, clean, fname)
            # descend into floats/nested layouts to find figure/table labels
            prescan_nested(sub_items, sec_num, fname)

    def prescan_nested(items, sec_num, fname):
        for item in items:
            if item[0] == "inset" and item[1].startswith("Float"):
                for sub in item[2]:
                    if sub[0] == "layout":
                        for it in sub[2]:
                            if it[0] == "inset" and it[1].startswith("Caption"):
                                raw = render_items_inline(it[2], RenderCtxDummy()).strip()
                                _, anchor = extract_heading_label(raw)
                                if anchor:
                                    register_label(anchor, sec_num, "Figure", fname)
            elif item[0] in ("inset", "layout"):
                prescan_nested(item[2], sec_num, fname)

    for sec in sections_data:
        prescan(sec["items"], sec["sec_num"], sec["file"])

    nav_entries = []
    section_stats = []

    for sec in sections_data:
        sec_num = sec["sec_num"]
        fname = sec["file"]
        ctx = RenderCtx(bib, sec_num, fname)
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

        page_attr = f" {{: #{sec['label']} }}" if sec.get("label") else ""
        page = f"# {sec_num} {sec['title']}{page_attr}\n\n"
        page += body_md.strip() + "\n"
        if footnote_lines:
            page += "\n\n" + "\n".join(footnote_lines) + "\n"

        out_path = os.path.join(OUT_DIR, fname)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(page)

        nav_entries.append((f"{sec_num} {sec['title']}", f"theory/chapter2/{fname}"))

        section_stats.append({
            "section": sec_num,
            "title": sec["title"],
            "file": fname,
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
    STATS["chapter_title"] = chapter_title
    STATS["nav"] = nav_entries

    with open(os.path.join(ROOT, "tools", "_stats.json"), "w", encoding="utf-8") as f:
        json.dump(STATS, f, indent=2)

    print(f"Converted {len(sections_data)} sections.")
    print(f"Totals: {STATS['totals']}")


class RenderCtxDummy(RenderCtx):
    """Used only for lightweight title extraction where citation/formula
    bookkeeping is irrelevant."""
    def __init__(self):
        super().__init__({}, "x")


if __name__ == "__main__":
    main()
