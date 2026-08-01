# febio-theory-manual

A pilot MkDocs site converting **Chapter 2 (Continuum Mechanics)** of the
FEBio Theory Manual from LyX to Markdown, built to mirror the conventions of
the sibling [`febio-feature-manual`](../febio-feature-manual/) repository
(Material for MkDocs theme, indigo palette, `pymdownx.arithmatex` +
MathJax for equations, footnote-based citations).

## Table of Contents
- [Prerequisites](#prerequisites)
- [Building the manual](#building-the-manual)
- [How the converter works](#how-the-converter-works)
- [Conversion statistics](#conversion-statistics)
- [Known limitations / needs manual review](#known-limitations--needs-manual-review)
- [Validation performed](#validation-performed)

## Repository layout

```
source/                   vendored copies of the LyX chapter + BibTeX bibliography
  ch2.lyx                 (from febio-docs/ch2.lyx)
  FEBio3.bib               (from febio-docs/FEBio3.bib)
tools/lyx2md.py            the converter (stdlib-only)
build.py                   runs the converter, generates mkdocs.yml
docs/                      generated Markdown site source (+ index.md, js/mathjax_config.js)
.github/workflows/deploy.yml   GitHub Pages deploy action
```

`source/ch2.lyx` and `source/FEBio3.bib` are vendored (checked-in) copies of
the original pilot inputs, so this repository builds standalone from a bare
`git clone` — the converter does not depend on any sibling directory outside
this repo. (`tools/lyx2md.py` will also pick up a sibling `../febio-docs/`
directory instead, if present, which is how it was used during local
development against the original workspace layout — see the module
docstring.)

## Prerequisites

```
pip install mkdocs mkdocs-material
```

## Building the manual

```
python3 build.py       # runs tools/lyx2md.py, writes mkdocs.yml
mkdocs serve           # preview at http://127.0.0.1:8000
mkdocs build --strict  # build the static site into site/
```

`build.py` invokes `tools/lyx2md.py` as a subprocess, reads back the
`tools/_stats.json` sidecar file it writes (per-section formula/citation/
figure counts and the nav ordering), and uses that to generate `mkdocs.yml`
with the correct Chapter 2 navigation automatically — the nav never needs to
be hand-maintained.

## How the converter works

`tools/lyx2md.py` is a **stdlib-only, deterministic** Python 3 parser for
LyX's plain-text `.lyx` format. It does not shell out to LyX, Pandoc, or any
other external tool.

1. **Tokenize into a tree.** `parse_flat()` reads the file line-by-line and
   builds an order-preserving tree of `('text', line)`, `('inset', spec,
   subitems)`, and `('layout', spec, subitems)` tuples, tracking
   `\begin_layout`/`\end_layout` and `\begin_inset`/`\end_inset` nesting.
   Inline formula insets (`\begin_inset Formula $x$` fully on one line) are
   special-cased at parse time so they don't get treated as the multi-line
   display-equation form.

2. **Two-pass label resolution.** Before rendering, a pre-scan pass walks
   every section and registers all `\begin_inset CommandInset label` targets
   (subsections, subsubsections, figures) into a global `LABEL_REGISTRY`, so
   `\ref{}` cross-references — including ones that point to a *different*
   section's file — can be resolved to `filename.md#anchor` links with the
   target's heading text, regardless of processing order.

3. **Character formatting** (`\series bold` → `**`, `\emph on` → `_`,
   `\shape italic` → `_`, `\family typewriter` → `` ` ``) is applied via a
   small state machine in `render_items_inline()`, plus a
   `fix_emphasis_whitespace()` post-pass that hoists any whitespace
   LyX left *inside* emphasis/bold/code delimiters back *outside* them —
   Markdown (unlike LyX) requires no whitespace adjacent to the marker or
   it won't recognize the emphasis run at all.

4. **Math.** Inline `\begin_inset Formula $...$` becomes inline `$...$`;
   display insets (`\begin{equation}`, `align`, `aligned`, `eqnarray`,
   `array`) become `\[ ... \]` blocks with the LyX `\label{}` preserved
   inside, so MathJax's `tags: 'ams'` + `\eqref{}` numbering works exactly
   like in the Feature Manual. `\begin_inset CommandInset ref` with
   `LatexCommand eqref` passes through as literal `\eqref{...}`; `ref` to
   a subsection/figure becomes a Markdown link.

5. **Citations** (`\begin_inset CommandInset citation`) become
   `[^section-n]` footnote references, deduplicated per page (the same
   BibTeX key cited twice on one page reuses one footnote number), with
   definitions resolved from `febio-docs/FEBio3.bib` via a small hand-written
   BibTeX field parser (`parse_bib()`), and appended at the bottom of each
   page as `Author. "Title." *Journal* (Year).`.

6. **Figures** (`\begin_inset Float figure` + `\begin_inset Graphics`)
   become `![name](figs/name.png)` followed by a
   `pymdownx.blocks.caption`-style `/// figure-caption` block, with the
   figure's own `\label` hoisted to an `<a id="...">` anchor placed before
   the image (rather than left inline in the caption prose, which is where
   LyX actually stores it).

7. **Unhandled inset kinds** render as `<!-- UNHANDLED INSET ... -->` HTML
   comments and are logged to `needs_review` — this makes the required
   zero-leftover-artifact grep double as a completeness check: any real
   parser gap shows up as a `grep`-able marker instead of silently
   dropping content.

8. **Headings** get explicit anchor IDs via `attr_list` syntax
   (`## Title {: #label }`), which is why `attr_list` was added to
   `mkdocs.yml`'s `markdown_extensions` beyond the Feature Manual's
   baseline set — it's required for the cross-section `\ref{}` links in
   step 2 to have a target to land on.

Output: one Markdown file per Section (2.1–2.16) in
`docs/theory/chapter2/`, named e.g. `2.1-vectors-and-tensors.md`.

## Conversion statistics

| Metric | Count |
|---|---|
| Sections converted | 16 of 16 (2.1–2.16) |
| Formula insets in source (`ch2.lyx`) | 1823 |
| Inline `$...$` formulas emitted | 1455 |
| Display `\[...\]` formulas emitted | 368 |
| **Formula reconciliation** | **1455 + 368 = 1823 — exact match** |
| Citation insets in source | 59 |
| Unique footnote definitions emitted | 58 (one BibTeX key cited twice on the same page shares one footnote number) |
| Figures (Float + Graphics + Caption) | 3 of 3 converted (placeholders — see below) |
| Unhandled/unknown inset kinds | 0 |
| Leftover LyX bookkeeping artifacts in output | 0 |

See [`CONVERSION_NOTES.md`](CONVERSION_NOTES.md) for the full per-section
breakdown and every item flagged for manual review.

## Known limitations / needs manual review

- **Figure artwork is placeholder only.** The three figures referenced in
  section 2.5 (`FigKinematicsContinuum.png`, `FigShearStrain.png`,
  `FigReferentialVolume.png`) are not present anywhere in the workspace
  inputs (`febio-docs/`, `febio-feature-manual/`) — no `Figures/` directory
  or matching binaries were found. Simple gray-bordered 480×300 placeholder
  PNGs were generated in their place at `docs/theory/chapter2/figs/`, with
  the original LyX-authored captions preserved intact. **Action needed:**
  drop in the real artwork from the FEBio documentation source repo before
  publishing.
- **Seven cross-references point outside Chapter 2's scope** (into Chapter 3's
  constitutive-models appendix, or to a subsection/label that doesn't exist
  in this pilot's single-chapter extract). These render as literal
  `#anchor-not-found` links and are flagged by `mkdocs build --strict` as
  `INFO`-level messages (not warnings/errors, so `--strict` still exits 0).
  This is expected for a single-chapter pilot; a full-manual build would
  resolve all of them. See the table in `CONVERSION_NOTES.md` for the exact
  targets.
- **`\obslash` has no LaTeX macro definition anywhere in the LyX source.**
  The document's preamble defines `\tr`, `\dev`, `\grad`, `\divg`, etc. as
  `\newcommand`s (and `docs/js/mathjax_config.js` reproduces them as MathJax
  `macros` so they render instead of leaving raw command names on the page),
  but `\obslash` — used 8 times in Chapter 2 for a tensor "conjugate"
  transpose-product operator — is never defined, even in the full manual.
  It has been approximated as an overlined `\oslash` (⊘ with a bar over it),
  which is visually consistent with its usage alongside the already-defined
  `\oslash` operator. **Action needed:** confirm the intended glyph with the
  FEBio documentation maintainers.
- **`\mbox{...}` is aliased to keep its argument in math mode** rather than
  switching to true text mode, because the LyX source nests math macros
  (`\dot{}`, `\thinspace`) inside `\mbox{}` in a few places, and MathJax's
  `\text{}` does not expand macros in its argument. The tradeoff is that
  plain-word arguments to `\mbox` (`grad`, `div`, `M`) render in italic math
  font rather than upright text font — a minor, cosmetic-only difference.
- **No `Tabular` insets occur in Chapter 2**, so table conversion is
  implemented but untested against a real table; if a future chapter
  contains one, treat its first render with extra scrutiny.
- **`mkdocs build --strict` succeeds (exit code 0).** The only diagnostics
  emitted are the seven `INFO`-level out-of-scope anchor messages above —
  there are zero `WARNING`-level messages.

## Validation performed

1. `python3 build.py && mkdocs build --strict` — exit code 0.
2. `grep -rn '\begin_\|\end_inset\|\begin_inset\|SpecialChar\|\lang ' docs/` —
   **zero matches** across all 16 generated pages.
3. Formula reconciliation: counted `$...$` + `\[...\]` markers across all 16
   output files = 1823, matching `grep -c "begin_inset Formula" ch2.lyx` =
   1823 in the source exactly.
4. Sections 2.1 and 2.6 were read in full and spot-checked against the
   published manual at
   [help.febio.org TM40-Section-2.1](https://help.febio.org/docs/FEBioTheory-4-0/TM40-Section-2.1.html)
   and the [Chapter 2 table of contents](https://help.febio.org/docs/FEBioTheory-4-5/TM45-Chapter-2.html) — see `CONVERSION_NOTES.md` for the detailed comparison. Every equation, definition, and the section 2.6 subsection ordering (2.6.1 through 2.6.9) match the published manual exactly.
5. The site was served locally with `mkdocs serve` and screenshotted with a
   headless Chromium (Playwright) — see `screenshot_section_2.1.png` and
   `screenshot_section_2.6.png` in the repo root. Equations render as
   properly typeset math (fractions, matrices, tensor operators, numbered
   equations with working anchors) with no raw LaTeX source visible on the
   page.
