# febio-theory-manual

A MkDocs site converting the FEBio Theory Manual from LyX to Markdown, built to mirror the conventions of
the sibling [`febio-feature-manual`](https://github.com/febiosoftware/febio-feature-manual) repository
(Material for MkDocs theme, indigo palette, `pymdownx.arithmatex` +
MathJax for equations, footnote-based citations). Started as a single-chapter pilot (Chapter 2, Continuum
Mechanics); now covers the complete manual — Chapters 1 through 8 plus Appendix A (Tensor Calculus).

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
docs/                      generated Markdown SOURCE for mkdocs (+ index.md, js/mathjax_config.js,
                           febio.png -- the header logo, vendored from febio-feature-manual's docs/) --
                           this is mkdocs's input, not the deployed site; see "Deployment" below
.github/workflows/deploy.yml   GitHub Actions workflow that builds and deploys to the gh-pages branch
```

`source/FEBio_Theory_Manual.lyx` and `source/FEBio3.bib` are vendored (checked-in) copies of the upstream
files, so this repository builds standalone from a bare `git clone` — the converter does not depend on any
sibling directory outside this repo. (`tools/lyx2md.py` will also pick up a sibling `../febio-docs/`
directory instead, if present, which is how it was used during local development against the original
workspace layout — see the module docstring.)

Which chapters actually get converted into pages is controlled by `CHAPTERS_TO_CONVERT` in
`tools/lyx2md.py`, currently `{1, 2, 3, 4, 5, 6, 7, 8, 9}` — i.e. every chapter in the manual (chapter 9 is
the source's `\start_of_appendix`-marked chapter, rendered as "Appendix A"). Chapters not in that set are
still scanned for their titles and label positions (so numbering and cross-references stay correct
regardless of conversion order), they just don't produce output files yet — this is how the site grew from
a single-chapter pilot to the full manual without ever needing to rewrite the cross-reference machinery.

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
   converted chapter into its `Section` boundaries and numbers them `<chapter>.<n>`. Content that appears
   between the `Chapter` heading and the first `Section` boundary (chapter-level intro prose, and in one
   case — Chapter 6 — several numbered equations) is prepended to the first section's body rather than
   dropped; this was a real bug caught by reconciling formula counts chapter-by-chapter against the source
   (see `CONVERSION_NOTES.md`). A chapter whose source is marked with LyX's native `\start_of_appendix`
   layout (and every chapter after it) is numbered with a letter instead of a digit and labeled "Appendix"
   instead of "Chapter" in the nav — this is how Chapter 9 becomes "Appendix A" without hardcoding a chapter
   number.

3. **Two-pass label resolution.** Before rendering, a pre-scan pass walks
   every converted section and registers all `\begin_inset CommandInset label` targets
   (chapters, subsections, subsubsections, figures) into a global `LABEL_REGISTRY`, plus a parallel
   `EQ_LABEL_REGISTRY` for equation `\label{}`s (see the cross-section equation references bullet below), so
   `\ref{}`/`\eqref{}` cross-references — including ones that point to a *different*
   section's or *chapter's* file — can be resolved to the correct relative link, regardless of processing
   order. Every chapter lives in its own sibling directory under `docs/theory/` (`chapter1/`, `chapter2/`,
   ...), so `build_relative_link()` computes same-page / same-chapter / cross-chapter links accordingly. A
   third registry, `CHAPTER_LABEL_REGISTRY`, is populated for *every* chapter in the source regardless of
   whether it's actually converted, so a `\ref{}` to a chapter (e.g. "see Chapter 5") always renders the
   correct chapter *number* — hyperlinked if that chapter has been converted, plain text if not — instead of
   the chapter's full title.

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
   limitations" bullet below. `ref` to a subsection becomes a Markdown link showing the subsection's title;
   `ref` to a figure becomes a Markdown link showing just the figure's number — its 1-indexed position among
   `Graphics` insets on its own page (matching what `pymdownx.blocks.caption` displays next to it), with a
   `<section>.` prefix only when the figure is defined on a *different* page than the reference, mirroring
   the equation-reference convention above. No "Figure" text is added, since the source prose always writes
   that word itself immediately before the `\ref{}` (e.g. "(Figure `\ref{fig17}`)" or "Figure~`\ref{...}`a-c.").

6. **Citations** (`\begin_inset CommandInset citation`) become
   `[^section-n]` footnote references, deduplicated per page (the same
   BibTeX key cited twice on one page reuses one footnote number), with
   definitions resolved from `source/FEBio3.bib` via a small hand-written
   BibTeX field parser (`parse_bib()`), and appended at the bottom of each
   page as `Author. "Title." *Journal* (Year).`. `\begin_inset CommandInset bibtex`
   (LaTeX's `\bibliography{}` insertion marker, not an actual citation) is suppressed. Real footnotes
   (`\begin_inset Foot`, distinct from citations) are collected separately and appended as
   `[^section-fn1]`, `[^section-fn2]`, etc.

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

8. **Tables** (`\begin_inset Tabular`) become plain Markdown tables (first row as header), always wrapped in
   a centering `<div markdown="1" style="display: flex; justify-content: center;">` — a plain Markdown table
   has no native alignment syntax, and `attr_list` doesn't attach to a table at all (confirmed empirically:
   an appended `{: ... }` gets absorbed as a bogus extra table row instead), so `md_in_html` is required in
   `mkdocs.yml` to get the nested table syntax inside that wrapper `div` actually parsed rather than passed
   through as literal text. LyX's tabular format is an embedded pseudo-XML dialect (`<lyxtabular>`, `<row>`,
   `<cell>`) that `parse_flat()` doesn't parse structurally; `render_tabular()` uses those tags purely as
   delimiters to group the `Text` insets (which *are* ordinary, correctly-parsed insets) holding each cell's
   real content, protecting row-separator newlines with a sentinel character so they survive a later
   prose-whitespace-normalization pass that would otherwise collapse them onto one line. Merged cells
   (colspan/rowspan) aren't representable in plain Markdown and are flagged for manual review rather than
   silently producing a misaligned table (occurs in the element-property tables of Section 4.1).

9. **ERT** ("evil red text", raw LaTeX LyX has no native inset for) is reconstructed from its per-line
   `\backslash`-token encoding and handles the two patterns that occur in this document: `\href{url}{text}`
   (rendering a real Markdown link, unwrapping a nested `\emph{}` in the link text to Markdown emphasis) and
   a bare `\url{url}` (rendering as a Markdown autolink `<url>`). Anything else is flagged for manual review
   instead of guessed at.

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

12. **Theorem-style layouts.** LyX's `theorems-ams` module layouts `Example` (numbered, per-page counter)
    and `Theorem*` (unnumbered) render as a bold run-in label directly in the text flow — `**Example
    N.** <body>` / `**Theorem.** <body>` — matching the published manual's plain LaTeX theorem-style
    numbering, not a Material admonition callout box (which the original document doesn't use; an earlier
    version of this converter rendered these as `!!! example "Example N"` boxes, since corrected). Per
    LyX/LaTeX semantics, *consecutive* same-kind layouts (nothing but a blank line between them) are
    additional paragraphs of the **same** environment instance, not a new one each — `render_section_body()`
    tracks the previous top-level layout's kind and only advances the counter / starts a fresh bold label
    when it wasn't the same kind (a non-blank item in between, e.g. LyX's `\begin_deeper`, still breaks the
    run, since that does mark a genuinely separate instance — confirmed against Appendix A.1, which has
    both cases). `Paragraph` layouts (an unnumbered run-in sub-heading, one level below Subsubsection)
    render as a bold `####` heading. `FormulaMacro` insets (LyX Math Macro definitions, e.g. Chapter 7's 23
    local shorthand macros) render as nothing — they're definitions, not visible content; the equivalent
    MathJax `macros` entries live in `docs/js/mathjax_config.js` instead, since MathJax has no per-page
    macro scoping.

Output: one Markdown file per converted Section in
`docs/theory/chapter<N>/`, named e.g. `2.1-vectors-and-tensors.md`.

## Conversion statistics

Totals for the complete, now fully-converted manual; see `CONVERSION_NOTES.md` for the full per-section
breakdown.

| Metric | Count |
|---|---|
| Chapters converted | 9 (Chapters 1–8 plus Appendix A / Tensor Calculus) |
| Sections converted | 64 |
| Inline `$...$` formulas emitted | 5203 |
| Display `\[...\]` formulas emitted | 1919 |
| Citations | 203 |
| Figures | 21 (artwork fetched at build time — see below) |
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
- **Merged cells (colspan/rowspan) aren't representable in plain Markdown tables.** The element-property
  tables in Section 4.1 use them; `render_tabular()` flags each occurrence for manual review and renders a
  best-effort approximation rather than silently producing a misaligned table.
- **Every chapter is now converted, so cross-references no longer point outside the site.** (Earlier notes
  in this file mis-described three references — `eq87`, `eq:viscous-stress`, `eq:virtual work` — as broken
  references in FEBio's own source; they were always real, resolvable labels, just in chapters not yet
  converted at the time. All three, and every other cross-reference in the manual, now resolve.) `mkdocs
  build --strict` still emits `INFO`-level "does not contain an anchor" messages for cross-page equation
  links — this is a static-checker false positive, not a broken link: `#mjx-eqn:<label>` anchors are
  injected client-side by MathJax only after it typesets the target page, so mkdocs's link checker (which
  only inspects the built HTML/Markdown source) can't see them, even though they resolve correctly in a
  real browser. Zero `WARNING`-level messages.
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
   checked chapter-by-chapter against the source. Chapter 2 alone reconciles exactly (1455 inline + 368
   display = 1823, matching `grep -c "begin_inset Formula"` over its source range exactly, as in the
   original single-chapter pilot); Chapter 6 also reconciles exactly (400/400) after the chapter-intro
   content-loss fix described above. Chapter 3 has one long-standing, tiny (1 of 1096, ~0.1%) unreconciled
   formula not further pursued — see `CONVERSION_NOTES.md`. Chapter 7's apparent 23-formula "gap" is fully
   explained by its 23 `FormulaMacro` definitions, which correctly produce no visible output.
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
