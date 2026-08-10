# febio-theory-manual

A MkDocs site converting the FEBio Theory Manual from LyX to Markdown, built to mirror the conventions of
the sibling [`febio-feature-manual`](https://github.com/febiosoftware/febio-feature-manual) repository
(Material for MkDocs theme, indigo palette, `pymdownx.arithmatex` +
MathJax for equations, footnote-based citations). Started as a single-chapter pilot (Chapter 2, Continuum
Mechanics); now also covers Chapter 1 (Introduction) and Chapter 3 (The Nonlinear FE Method), with more
chapters to follow.

## Table of Contents
- [Repository layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Building the manual](#building-the-manual)
- [Deployment](#deployment)
- [How the converter works](#how-the-converter-works)
- [Conversion statistics](#conversion-statistics)
- [Known limitations / needs manual review](#known-limitations--needs-manual-review)
- [Validation performed](#validation-performed)

## Repository layout

```
source/                   vendored copies of the LyX manual + BibTeX bibliography
  FEBio_Theory_Manual.lyx (the complete manual; from febiosoftware/FEBio's Documentation/ dir)
  FEBio3.bib
tools/lyx2md.py            the converter (stdlib-only)
build.py                   runs the converter, generates mkdocs.yml
docs/                      generated Markdown SOURCE for mkdocs (+ index.md, js/mathjax_config.js) --
                           this is mkdocs's input, not the deployed site; see "Deployment" below
.github/workflows/deploy.yml   GitHub Actions workflow that builds and deploys to the gh-pages branch
```

`source/FEBio_Theory_Manual.lyx` and `source/FEBio3.bib` are vendored (checked-in) copies of the upstream
files, so this repository builds standalone from a bare `git clone` — the converter does not depend on any
sibling directory outside this repo. (`tools/lyx2md.py` will also pick up a sibling `../febio-docs/`
directory instead, if present, which is how it was used during local development against the original
workspace layout — see the module docstring.)

Only a subset of the manual's chapters are actually converted into pages at any given time, controlled by
`CHAPTERS_TO_CONVERT` in `tools/lyx2md.py` (currently `{1, 2, 3}`) — chapters not in that set are still
scanned for their titles and label positions (so numbering and cross-references stay correct regardless of
conversion order), they just don't produce output files yet.

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
`tools/_stats.json` sidecar file it writes (per-chapter, per-section formula/citation/
figure counts and nav ordering), and uses that to generate `mkdocs.yml` with the correct navigation
automatically — the nav never needs to be hand-maintained. Navigation is a single unified sidebar tree (no
`navigation.tabs`): a Preface entry, then one top-level nav group per converted chapter, each expanding to
that chapter's sections.

## Deployment

The live site (<https://wesley-jakob-gilbert.github.io/FEBio-theory-manual/>)
is served by GitHub Pages **from the `gh-pages` branch**, not from the
`docs/` folder on `main`. `docs/` on `main` is mkdocs's *source* input
(Markdown); the `gh-pages` branch holds the fully rendered, compiled HTML
output that `mkdocs build` produces into a local, gitignored `site/`
directory. These are two different branches with two different kinds of
content — pushing to `main` alone does not, by itself, change what's live.

Two ways the `gh-pages` branch gets updated:

- **Automatically:** `.github/workflows/deploy.yml` runs on every push to
  `main`. It re-generates `docs/`/`mkdocs.yml` from `source/FEBio_Theory_Manual.lyx` (so the
  deploy can never drift from what's actually committed), validates with
  `mkdocs build --strict`, then runs `mkdocs gh-deploy --force`, which
  builds the site and pushes the result to `gh-pages`. GitHub's own internal
  "pages build and deployment" step then republishes that branch to the live
  CDN — this second step happens outside our workflow and isn't always
  instant.
- **Manually**, e.g. to deploy local changes right away:
  ```
  mkdocs gh-deploy --force
  ```
  (requires push access to this repository).

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

2. **Chapter/section boundary detection.** `main()` locates every `Chapter` layout in the source (not just
   the ones being converted) to compute each one's absolute chapter number by position, then splits each
   converted chapter into its `Section` boundaries and numbers them `<chapter>.<n>`.

3. **Two-pass label resolution.** Before rendering, a pre-scan pass walks
   every converted section and registers all `\begin_inset CommandInset label` targets
   (chapters, subsections, subsubsections, figures) into a global `LABEL_REGISTRY`, plus a parallel
   `EQ_LABEL_REGISTRY` for equation `\label{}`s (see the cross-section equation references bullet below), so
   `\ref{}`/`\eqref{}` cross-references — including ones that point to a *different*
   section's or *chapter's* file — can be resolved to the correct relative link, regardless of processing
   order. Every chapter lives in its own sibling directory under `docs/theory/` (`chapter1/`, `chapter2/`,
   ...), so `build_relative_link()` computes same-page / same-chapter / cross-chapter links accordingly.

4. **Character formatting** (`\series bold` → `**`, `\emph on` → `_`,
   `\shape italic` → `_`, `\family typewriter` → `` ` ``) is applied via a
   small state machine in `render_items_inline()`. LyX scopes this formatting to a single paragraph/layout
   and doesn't require an explicit closing toggle before `\end_layout` (confirmed: table cells routinely
   end with formatting left open), so any marker still open at the end of a call is auto-closed rather than
   leaking into whatever the caller appends next. A separate `fix_emphasis_whitespace()` post-pass hoists
   any whitespace LyX left *inside* emphasis/bold/code delimiters back *outside* them — Markdown (unlike
   LyX) requires no whitespace adjacent to the marker or it won't recognize the emphasis run at all. That
   pass masks underscores inside inline math (`$t_{0}$`-style LaTeX subscripts) before pairing markers,
   since otherwise they're indistinguishable from a real `_..._` delimiter and can shift the pairing across
   an entire paragraph.

5. **Math.** Inline `\begin_inset Formula $...$` becomes inline `$...$`;
   display insets (`\begin{equation}`, `align`, `aligned`, `eqnarray`,
   `array`) become `\[ ... \]` blocks with the LyX `\label{}` preserved
   inside, so MathJax's `tags: 'ams'` + `\eqref{}` numbering works exactly
   like in the Feature Manual. A same-page `\eqref{}`/`\ref{}` to an equation passes through as literal
   LaTeX for MathJax to resolve; a reference to an equation defined on a *different* page is resolved at
   build time instead (MathJax's per-page auto-numbering can't do this itself) — see the "Known
   limitations" bullet below. `ref` to a subsection/figure becomes a Markdown link.

6. **Citations** (`\begin_inset CommandInset citation`) become
   `[^section-n]` footnote references, deduplicated per page (the same
   BibTeX key cited twice on one page reuses one footnote number), with
   definitions resolved from `source/FEBio3.bib` via a small hand-written
   BibTeX field parser (`parse_bib()`), and appended at the bottom of each
   page as `Author. "Title." *Journal* (Year).`.

7. **Figures** (`\begin_inset Float figure` + `\begin_inset Graphics`)
   become `![name](figs/name.png)` followed by a
   `pymdownx.blocks.caption`-style `/// figure-caption` block, with the
   figure's own `\label` hoisted to an `<a id="...">` anchor placed before
   the image (rather than left inline in the caption prose, which is where
   LyX actually stores it). A LyX `scale NN` attribute is carried through as inline CSS
   (`{: style="width:NN%" }` via `attr_list`) so the figure isn't embedded at full native pixel size. A bare
   `Graphics` inset not wrapped in a `Float` (decorated instead with LyX `Box`/`VSpace` insets, which are
   otherwise purely presentational and rendered as their content passed through transparently) is also
   handled.

8. **Tables** (`\begin_inset Tabular`) become plain Markdown tables (first row as header). LyX's tabular
   format is an embedded pseudo-XML dialect (`<lyxtabular>`, `<row>`, `<cell>`) that `parse_flat()` doesn't
   parse structurally; `render_tabular()` uses those tags purely as delimiters to group the `Text` insets
   (which *are* ordinary, correctly-parsed insets) holding each cell's real content. Merged cells
   (colspan/rowspan) aren't representable in plain Markdown and are flagged for manual review rather than
   silently producing a misaligned table, though none occur anywhere in the document as of this writing.

9. **ERT** ("evil red text", raw LaTeX LyX has no native inset for) is reconstructed from its per-line
   `\backslash`-token encoding and currently handles the one pattern that occurs in this document,
   `\href{url}{text}`, rendering a real Markdown link (unwrapping a nested `\emph{}` in the link text to
   Markdown emphasis). Anything else is flagged for manual review instead of guessed at.

10. **Unhandled inset kinds** render as `<!-- UNHANDLED INSET ... -->` HTML
    comments and are logged to `needs_review` — this makes the required
    zero-leftover-artifact grep double as a completeness check: any real
    parser gap shows up as a `grep`-able marker instead of silently
    dropping content.

11. **Headings** get explicit anchor IDs via `attr_list` syntax
    (`## Title {: #label }`), which is why `attr_list` was added to
    `mkdocs.yml`'s `markdown_extensions` beyond the Feature Manual's
    baseline set — it's required for the cross-section `\ref{}` links in
    step 3 to have a target to land on.

Output: one Markdown file per converted Section in
`docs/theory/chapter<N>/`, named e.g. `2.1-vectors-and-tensors.md`.

## Conversion statistics

Current totals for the converted chapters (1, 2, 3); see `CONVERSION_NOTES.md` for the full per-section
breakdown.

| Metric | Count |
|---|---|
| Chapters converted | 3 (Introduction; Continuum Mechanics; The Nonlinear FE Method) |
| Sections converted | 28 |
| Inline `$...$` formulas emitted | 2442 |
| Display `\[...\]` formulas emitted | 868 |
| Citations | 83 |
| Figures | 4 (artwork fetched at build time — see below) |
| Unhandled/unknown inset kinds | 0 |
| Leftover LyX bookkeeping artifacts in output | 0 |

See [`CONVERSION_NOTES.md`](CONVERSION_NOTES.md) for the full per-section
breakdown and every item flagged for manual review.

## Known limitations / needs manual review

- **Figure artwork is fetched automatically at build time.** Figures aren't part of the pilot's original
  LyX/BibTeX inputs, so `build.py` scans every converted chapter's generated Markdown for figure
  references and fetches any missing ones from the upstream
  [`febiosoftware/FEBio`](https://github.com/febiosoftware/FEBio)
  repository's `Documentation/Figures/` directory into that chapter's `figs/` directory (skipping the fetch
  if a real copy is already present). The original LyX-authored captions are preserved intact either way.
- **Cross-section (and cross-chapter) `\eqref{}`/`\ref{}` references to equations are resolved to static
  links, not left as `\eqref{}`.** Each Section is a separately-loaded page, and
  MathJax's `tags: 'ams'` auto-numbering is per-page -- it has no way to
  resolve a reference to a `\label{}` defined on a *different* page, which
  renders as a bare "???" with nothing to click. `EQ_LABEL_REGISTRY` in
  `tools/lyx2md.py` tracks every labeled equation's 1-indexed position
  among its own page's AMS-numbered equations (verified to exactly match
  what MathJax itself displays, and cross-checked via a real browser that the link both navigates to the
  right page and lands on the right equation); such a reference is
  then replaced with a real link like `(2.5-35)` to the target page's
  MathJax-generated `#mjx-eqn:<label>` anchor, mirroring how the published
  manual itself handles the identical problem at its finer per-subsection
  pagination (there it reads `(2.5.4-2)`). MathJax sanitizes spaces in the label to underscores when
  building that anchor id (confirmed against the one label in this document that contains a space,
  `eq:virtual work` → `mjx-eqn:eq:virtual_work`) — `mathjax_eqn_id()` replicates that. Because the anchor is
  injected by MathJax *after* the browser's initial page-load fragment-scroll
  already ran (and thus failed to find it), `docs/js/mathjax_config.js`
  also re-attempts the scroll once typesetting finishes, via MathJax's
  `startup.pageReady` hook. Same-page references are untouched since
  MathJax already resolves those correctly on its own.
- **A handful of cross-references point outside the currently-converted chapters** (into chapters not yet
  in `CHAPTERS_TO_CONVERT`, e.g. Element Library, Constitutive Models, Contact and Coupling, or the Tensor
  Calculus appendix). These render as literal `#anchor-not-found` links (or, for equation references, a
  passthrough `\eqref{}` that MathJax can't resolve) and are flagged by `mkdocs build --strict` as
  `INFO`-level messages (not warnings/errors, so `--strict` still exits 0) — expected, and will resolve
  automatically as more chapters are converted. (Earlier notes in this file mis-described three of these —
  `eq87`, `eq:viscous-stress`, `eq:virtual work` — as broken references in FEBio's own source; they're
  real, resolvable labels, just missed by an incomplete search at the time. Corrected here.)
- **`\obslash` has no LaTeX macro definition anywhere in the LyX source.**
  The document's preamble defines `\tr`, `\dev`, `\grad`, `\divg`, etc. as
  `\newcommand`s (and `docs/js/mathjax_config.js` reproduces them as MathJax
  `macros` so they render instead of leaving raw command names on the page),
  but `\obslash` — used 8 times in Chapter 2 for a tensor "conjugate"
  transpose-product operator — is never defined, even in the full manual.
  It was initially approximated as an overlined `\oslash`; visual comparison
  against the published manual showed the actual glyph is a
  backslash-in-a-circle rather than an overlined forward-slash-in-a-circle,
  so it now renders as U+29B8 CIRCLED REVERSE SOLIDUS (`⦸`), the mirror
  image of `\oslash`'s U+2298 CIRCLED DIVISION SLASH. This depends on the
  MathJax web font covering that codepoint — reconfirm visually if the
  MathJax CDN version ever changes.
- **`\mbox{...}` is aliased to keep its argument in math mode** rather than
  switching to true text mode, because the LyX source nests math macros
  (`\dot{}`, `\thinspace`) inside `\mbox{}` in a few places, and MathJax's
  `\text{}` does not expand macros in its argument. It's aliased to
  `\mathrm{#1}` rather than a no-op group, so plain-word arguments (`and`,
  `grad`, `div`, `M`) render in upright text font while nested macros like
  `\dot{}` and `\thinspace` still expand correctly.
- **`mkdocs build --strict` succeeds (exit code 0).** The only diagnostics
  emitted are the `INFO`-level anchor messages described above —
  there are zero `WARNING`-level messages.

## Validation performed

1. `python3 build.py && mkdocs build --strict` — exit code 0.
2. `grep -rn '\begin_\|\end_inset\|\begin_inset\|SpecialChar\|\lang ' docs/theory/` —
   **zero matches** across all converted pages.
3. Zero unhandled/unknown inset kinds logged across all converted chapters.
4. Formula counts reported by the converter's own render-pass counters (not a post-hoc regex scan) were
   checked chapter-by-chapter against the source; Chapter 2 alone reconciles exactly (1455 inline + 368
   display = 1823, matching `grep -c "begin_inset Formula"` over its source range exactly, as in the
   original single-chapter pilot).
5. A real browser (headless Chromium via Playwright) was used throughout development to verify things a
   static grep can't catch: MathJax equation/table/figure rendering, the removal of `navigation.tabs` in
   favor of a single unified sidebar, a chapter title containing inline math (`$\alpha-$Method`) rendering
   correctly in both the page heading and the nav sidebar, and that a cross-chapter equation reference link
   both navigates to the right page *and* scrolls to the right equation.
6. Sections 2.1 and 2.6 were read in full and spot-checked against the
   published manual at
   [help.febio.org TM40-Section-2.1](https://help.febio.org/docs/FEBioTheory-4-0/TM40-Section-2.1.html)
   and the [Chapter 2 table of contents](https://help.febio.org/docs/FEBioTheory-4-5/TM45-Chapter-2.html) — see `CONVERSION_NOTES.md` for the detailed comparison. Every equation, definition, and the section 2.6 subsection ordering (2.6.1 through 2.6.9) match the published manual exactly.
7. The site was served locally with `mkdocs serve` and screenshotted with a
   headless Chromium (Playwright) during the original single-chapter pilot — see `screenshot_section_2.1.png` and
   `screenshot_section_2.6.png` in the repo root. Equations render as
   properly typeset math (fractions, matrices, tensor operators, numbered
   equations with working anchors) with no raw LaTeX source visible on the
   page.
