# Conversion Notes — FEBio Studio Manual

Generated from `source/FEBioStudio_User_Manual.lyx` using the same `tools/lyx2md.py` converter as the
Theory Manual (see `CONVERSION_NOTES.md`), run as a separate pass via `build.py`'s `MANUALS` list with
this manual's own LyX/bib source and its own `docs/studio/` output tree.

This started as a 2-chapter pilot (Chapters 1–2, Introduction and Getting Started — 8 sections) to
validate that the Theory-Manual-tuned converter, largely unmodified, produces clean output against a
different manual's LyX source — one that's almost entirely UI/GUI prose and screenshots rather than
dense mathematics. It now covers the **complete manual**: all 20 chapters plus Appendix A (Mesh Import
Formats) and Appendix B (Standard Data Fields), 117 sections total.

## Reconciliation summary

| Check | Result |
|---|---|
| Chapters converted | 22 (Chapters 1–20 plus Appendices A and B) — the complete manual |
| Sections converted | 117 |
| Inline `$...$` emitted | 126 |
| Display `\[...\]` emitted | 18 |
| Citations | 2 |
| Figures | 194 |
| Leftover LyX artifacts (`\begin_`, `\end_inset`, `\begin_inset`, `SpecialChar`, `\lang `) | **0** |
| Unhandled/unrecognized inset kinds | **0** (after the converter fixes below) |
| `mkdocs build --strict` (both manuals together) | exit code 0, **zero** `WARNING`-level messages |

Appendix B ("Standard Data Fields") is a chapter with no `\begin_layout Section` boundaries at all —
just Standard paragraphs and tables directly under the chapter heading. `tools/lyx2md.py`'s section-
splitting logic previously assumed every chapter has at least one Section, producing an empty nav
entry for section-less chapters; `mkdocs build --strict` rejects an empty nav list outright ("Expected
nav to be a list, got None"). Fixed in `main()`: a chapter with zero Section boundaries is now treated
as a single synthetic section (numbered `<chapter>.1`, titled after the chapter itself), so it always
produces a real output page.

## Converter gaps found and fixed against this manual's real content

The Theory Manual's source never exercised any of these; all are now fixed in `tools/lyx2md.py`:

1. **`\begin_inset Wrap figure`** (LaTeX's `wrapfig` — a text-wrapped figure) had no renderer and fell
   through to `<!-- UNHANDLED INSET ... -->`. Aliased to the existing `render_float()` path (identical
   `Plain Layout` + `Graphics` + `Caption` substructure), including in the figure-numbering prescan.
2. **A native `\begin_inset CommandInset href`** (LyX's own hyperlink inset, distinct from the ERT
   `\href{}{}`/`\url{}` reconstruction the Theory Manual relies on) was unhandled. Added the same
   rendering convention as the ERT case: an optional display `name` becomes a Markdown link, an unnamed
   one becomes a bare autolink.
3. **A whitespace-normalization regex** in `render_items_inline()` (intended to strip a spurious space
   before sentence-ending punctuation left over from LyX's line-continuation joining) was also stripping
   the *genuine* space before a literal file-extension token — `"the .xplt file extension"` was rendering
   as `"the.xplt file extension"`. Fixed with a negative lookahead so the space is only stripped when the
   punctuation isn't immediately followed by a word character.
4. **`Description` layouts** (LaTeX's `description` list environment) had no renderer and fell through to
   generic paragraph handling with an "Unhandled top-level layout kind" flag. Added: the label (everything
   up to the first plain space; a non-breaking space from an author-inserted "protected space" does *not*
   end the label) is auto-bolded, matching LyX's own rendering — unless the body already starts with `**`
   (some items explicitly wrap their label in `\series bold` instead of relying on auto-bolding).
5. **`LyX-Code` layouts** (literal code/data listings — XML session-file snippets, CSV data rows) had no
   renderer. Added `render_code_line()`, which skips the prose-oriented character-formatting state machine
   and whitespace normalization entirely (both are wrong for literal listings), and groups consecutive
   `LyX-Code` layouts into a single fenced ` ``` ` block rather than one block per line.
6. **A bare ERT inset containing only `{` or `}`** (used to show a literal keyword-placeholder delimiter
   in prose, e.g. "keywords start with a percentage sign (`{%}`)") fell through `render_ert()`'s
   href/url pattern matching to "Unhandled ERT content". Neither character needs escaping in Markdown, so
   both now render verbatim.
7. **`\SpecialChar endofsentence`** (LyX's forced end-of-sentence-spacing marker, used e.g. right after a
   bolded term with no punctuation of its own) leaked as literal text. Renders as a plain `.`, matching
   the marker's visible effect.
8. **Malformed bold/italic nesting in Markdown output** — LyX source doesn't always close character-
   formatting markers in reverse-of-open (LIFO) order (e.g. closing `\series bold` while `\emph on`,
   opened after it, is still active). The converter's old formatting-state tracker (four independent
   booleans) couldn't express "close bold but keep emph open," producing invalid Markdown nesting like
   `**_word**_` that browsers render incorrectly. Replaced with an explicit open-marker stack and a
   `close_marker()` helper that closes everything opened after the target marker, then reopens it —
   correctly producing `**_word_**_..._`. This is a **pre-existing bug also present in some Theory Manual
   output** (not something newly introduced by the Studio Manual), fixed as a side effect of hardening
   the same code path against the Studio Manual's more varied nesting patterns.
9. **`\size <name>`** (LyX font-size commands: `footnotesize`, `normal`, `default`, etc.) leaked as
   literal text inside table cells and — pre-existing — one Theory Manual paragraph (Section 7.1). This
   site's CSS has no per-run font-size concept to preserve, so it's dropped like `\shape up`/`slanted`/
   `smallcaps` already was.
10. **`\emph off`** (an alternate spelling of `\emph default` LyX emits in some contexts) wasn't
    recognized, leaving an emphasis marker unclosed. Now treated identically to `\emph default`.
11. **`\noindent`** (LaTeX's "don't indent this paragraph" directive) leaked as literal text. This site's
    CSS doesn't indent paragraphs to begin with, so it's dropped with no effect on output.
12. **A bare `\backslash` token in ordinary prose** (not inside an ERT inset) leaked as the literal text
    `"\backslash"` — found in Windows file paths written directly in body text (e.g.
    `C:\backslashProgram Files\backslashFEBioStudio3\backslashsdk\backslashinclude`). `render_ert()`
    already decoded this token inside raw-LaTeX ERT insets; the same one-line fix (`\backslash` → literal
    `\`) is now applied in `render_items_inline()`'s normal text path too.
13. **`\begin_inset Float table`** (a table wrapped in a floating/captioned environment, analogous to
    `Float figure` but for a `Tabular` inset instead of `Graphics`) silently dropped its entire table —
    `render_float()` only ever looked for a `Graphics` inset inside the float, so a `Tabular` inset there
    produced an empty output block (caption and anchor still rendered, but the table itself vanished
    without any `needs_review` flag — the most serious of these gaps, a content-loss bug, not a cosmetic
    one). Fixed by also checking for a `Tabular` inset and rendering it via the existing `render_tabular()`
    function; the caption now uses `pymdownx.blocks.caption`'s `table-caption` type instead of
    `figure-caption` so it gets its own numbering sequence and doesn't perturb figure `\ref{}` numbering.
14. **Figure filenames containing literal spaces** (e.g. `Model Viewer.png`, `file viewer.png`,
    `Material Viewer.png`) broke `build.py`'s figure-fetch step — `urllib.request.urlretrieve` rejects a
    raw space in a URL ("URL can't contain control characters"). Fixed by percent-encoding just the
    filename portion (`urllib.parse.quote()`) before appending it to the upstream `fig_base` URL, leaving
    the local destination path (which has no such restriction) untouched.
15. **LaTeX accent commands in BibTeX author/title fields** (e.g. `{\"u}` or `\"u` for u-umlaut, found in
    `FEBioStudio.bib`-cited authors like "Gültekin" and "Dussèaux" — this pattern exists in the Theory
    Manual's `FEBio3.bib` too, but was never decoded, just silently rendered as garbled `{\"u}`-style
    text). Added `decode_latex_accents()`, translating the common LaTeX accent commands (umlaut, acute,
    grave, circumflex, tilde) to their real Unicode characters; anything not in the table is left
    untouched rather than guessed at. Also strips residual `{...}` capitalization-protection braces from
    BibTeX titles/journals (e.g. `{A {Nonparametric} Approach ... ({ODFs}) ...}`), which this site never
    needed to un-escape before since no case-transformation is applied to citation text.

None of these are silently-discovered-later bugs like the Theory Manual's Chapter 6 chapter-intro
content-loss issue — all were caught directly via `unhandled`/`needs_review` flags during conversion, or
via manual spot-reading of rendered pages against the source and the live HTML at
https://help.febio.org/docs/FEBioStudio-3-1/FSM31.html, *except* for #13 (the `Float table` content-loss
bug), which produced no `needs_review` flag at all and was only caught by spot-reading Appendix B's
rendered output and noticing its tables were entirely missing.

## Chapter breakdown

| Chapter | Title | Sections |
|---|---|---|
| 1 | Introduction | 2 |
| 2 | Getting Started | 6 |
| 3 | The FEBio Studio Environment | 15 |
| 4 | Creating, Loading, and Saving Models | 3 |
| 5 | Creating and Editing Geometry | 4 |
| 6 | Generating and Editing Mesh Data | 5 |
| 7 | Materials | 6 |
| 8 | Boundary Conditions and Loads | 4 |
| 9 | Contact and Constraints | 2 |
| 10 | Rigid Bodies | 5 |
| 11 | Defining Analysis Steps | 2 |
| 12 | Configuring Output | 2 |
| 13 | Running FEBio from FEBioStudio | 5 |
| 14 | The Post Environment | 4 |
| 15 | Saving Graphics | 5 |
| 16 | The Post Panel | 4 |
| 17 | Post Processing | 13 |
| 18 | Visualizing 3D Image Data | 5 |
| 19 | Using Python in FEBio Studio | 2 |
| 20 | Using and Creating FEBio Plugins | 2 |
| A | Mesh Import Formats | 20 |
| B | Standard Data Fields | 1 (synthetic — see Reconciliation summary above) |

Per-section `needs_review` entries are almost entirely one of two routine, expected categories, not
defects:

- **Figure image referenced, placeholder written** — informational; every referenced figure is fetched
  for real by `build.py`'s figure-fetch step at build time from `febiosoftware/FEBioStudio`'s
  `Documentation/Figures/` directory (see the Known Limitations section of `README.md`).
- **Unresolved `\ref` target** — none remain now that every chapter is converted; during the earlier
  2-chapter pilot, a handful of forward references into not-yet-converted chapters degraded gracefully
  (rendered as a same-page anchor link that didn't yet resolve) rather than crashing, the same way an
  out-of-scope Theory Manual reference does.

Full per-section detail (formula/citation/figure counts and any `needs_review` notes) is in
`tools/_stats_studio.json`, generated fresh on every `python3 build.py` run.
