# Conversion Notes

Generated from `source/FEBio_Theory_Manual.lyx` (the complete manual; `CHAPTERS_TO_CONVERT` in
`tools/lyx2md.py` currently limits actual output to Chapters 1–3) using `tools/lyx2md.py`. Totals reconciled
below; per-section detail follows. This file originally covered only Chapter 2 (Continuum Mechanics) as a
single-chapter pilot; Chapters 1 (Introduction) and 3 (The Nonlinear FE Method) have since been added.

## Reconciliation summary

| Check | Result |
|---|---|
| Chapters converted | 3 (Introduction; Continuum Mechanics; The Nonlinear FE Method) |
| Sections converted | 28 |
| Inline `$...$` emitted | 2442 |
| Display `\[...\]` emitted | 868 |
| Citations | 83 |
| Figures | 4 |
| Leftover LyX artifacts (`\begin_`, `\end_inset`, `\begin_inset`, `SpecialChar`, `\lang `) | **0** |
| Unhandled/unrecognized inset kinds | **0** |
| `mkdocs build --strict` | exit code 0 (`INFO`-level anchor notices only, for chapters not yet converted; 0 `WARNING`) |

Chapter 2 alone reconciles exactly against its source range, as established during the original
single-chapter pilot: 1455 inline + 368 display = 1823, matching `grep -c "begin_inset Formula"` over
`source/ch2.lyx` (now retired in favor of the single vendored `source/FEBio_Theory_Manual.lyx`) exactly.
Chapter 3 has one formula-inset-count discrepancy against a raw source scan (1487 rendered vs. 1488 raw
`\begin_inset Formula` occurrences) not yet root-caused; given zero unhandled insets and zero leftover
artifacts otherwise, this is presumed to be a benign edge case (e.g. two adjacent insets on the same source
line) rather than lost content, but is flagged here for anyone revisiting this.

## Per-section breakdown

### Chapter 1 — Introduction

| Section | Title | Inline formulas | Display formulas | Citations | Figures | Converted cleanly? | Needs manual review |
|---|---|---|---|---|---|---|---|
| 1.1 | Overview of FEBio | 0 | 0 | 0 | 0 | Yes | None |
| 1.2 | About this Document | 0 | 0 | 0 | 0 | Mostly | 3 unresolved refs (`chap:Element-Library`, `chap:Constitutive-Models`, `chap:Contact-and-Coupling`) — those chapters aren't in `CHAPTERS_TO_CONVERT` yet; expected |

### Chapter 2 — Continuum Mechanics

| Section | Title | Inline formulas | Display formulas | Citations | Figures | Converted cleanly? | Needs manual review |
|---|---|---|---|---|---|---|---|
| 2.1 | Vectors and Tensors | 42 | 26 | 1 | 0 | Yes | None |
| 2.2 | The Directional Derivative | 10 | 6 | 1 | 0 | Yes | None |
| 2.3 | Cauchy Stress | 21 | 1 | 0 | 0 | Yes | None |
| 2.4 | Axioms of Conservation | 30 | 11 | 0 | 0 | Yes | None |
| 2.5 | Kinematics of the Continuum | 210 | 57 | 1 | 3 | Mostly | 3 figures (`FigKinematicsContinuum.png`, `FigShearStrain.png`, `FigReferentialVolume.png` — not in the pilot's original inputs, fetched from upstream by `build.py` at build time, see README); 1 unresolved `\ref{subsubsec:determinant}` (real label, but lives in the Tensor Calculus appendix, not yet converted) |
| 2.6 | Hyperelasticity | 144 | 79 | 11 | 0 | Mostly | 1 unresolved ref: `\ref{chap:Constitutive-Models}` (real label, Chapter 5, not yet converted); several cross-section `\eqref{}`s into section 2.5 (including `eq87`, referenced via a plain `\ref{}` rather than `\eqref{}`) now resolve to static links (e.g. `(2.5-35)`) instead of showing "???"; uses `\obslash` (see README) and `\mbox{\thinspace and\thinspace}` (eq. 11, renders correctly via MathJax macro fix) |
| 2.7 | Biphasic Material | 26 | 6 | 3 | 0 | Yes | None |
| 2.8 | Biphasic-Solute Material | 109 | 13 | 14 | 0 | Yes | None |
| 2.9 | Triphasic and Multiphasic Materials | 66 | 15 | 0 | 0 | Yes | None |
| 2.10 | Constrained Reactive Mixture of Solids | 201 | 29 | 6 | 0 | Yes | Cross-section `\ref{subsec:Nearly-Incompressible-Hyperelast}` (into 2.6.8) now correctly resolves to `2.6-hyperelasticity.md#subsec:Nearly-Incompressible-Hyperelast` — this was previously a real converter bug (a redundant label re-registration during rendering, without a filename, silently overwrote the correct pre-scanned entry), not a checker limitation as earlier notes here claimed; fixed by removing the redundant re-registration |
| 2.11 | Equilibrium Swelling | 56 | 9 | 0 | 0 | Yes | None |
| 2.12 | Chemical Reactions | 105 | 41 | 0 | 0 | Yes | None |
| 2.13 | Fluid Mechanics | 127 | 24 | 0 | 0 | Mostly | 1 unresolved `\ref{sec:Viscous-Fluids}` (real label, Chapter 5, not yet converted); cross-*chapter* `\eqref{eq:virtual work}` into section 3.5 now resolves to a static link (`eq:viscous-stress` is also a real label, but lives in Chapter 5, not yet converted) |
| 2.14 | Fluid-Structure Interactions | 27 | 15 | 1 | 0 | Yes | None |
| 2.15 | Hybrid Biphasic Material | 137 | 17 | 8 | 0 | Mostly | 1 unresolved `\ref{sec:Hydraulic-Permeability}` (real label, Chapter 5, not yet converted) |
| 2.16 | Fluid-Solutes Analyses | 144 | 19 | 12 | 0 | Yes | None |

### Chapter 3 — The Nonlinear FE Method

| Section | Title | Inline formulas | Display formulas | Citations | Figures | Converted cleanly? | Needs manual review |
|---|---|---|---|---|---|---|---|
| 3.1 | Weak formulation for Solid Materials | 27 | 22 | 1 | 1 | Yes | Figure `FigCentrifugalBodyForce.png` (bare `Graphics` inset decorated with `Box`/`VSpace`, no `Float`/`Caption` — a different pattern than Chapter 2's figures; fetched from upstream by `build.py`) |
| 3.2 | Weak formulation for biphasic materials | 115 | 35 | 5 | 0 | Yes | None |
| 3.3 | Weak Formulation for Biphasic-Solute Materials | 156 | 62 | 3 | 0 | Yes | None |
| 3.4 | Weak Formulation for Multiphasic Materials | 150 | 87 | 2 | 0 | Yes | None |
| 3.5 | Computational Fluid Dynamics | 184 | 38 | 7 | 0 | Yes | None |
| 3.6 | Weak Formulation for FSI | 81 | 131 | 1 | 0 | Yes | None |
| 3.7 | Weak Formulation for BFSI | 154 | 49 | 3 | 0 | Yes | None |
| 3.8 | Weak Formulation for Fluid-Solutes Analyses | 57 | 39 | 1 | 0 | Yes | None |
| 3.9 | Newton-Raphson Method | 37 | 30 | 1 | 0 | Yes | None |
| 3.10 | Generalized α-Method | 26 | 7 | 1 | 0 | Yes | Section title contains inline math (`$\alpha-$Method`); verified via headless browser that MathJax correctly typesets it both in the page heading and the nav sidebar, since nav labels are plain YAML text that MathJax happens to also scan as part of the page DOM |

Section 3.4 also contains the one `Tabular` inset in the currently-converted chapters (a 7×3 grid, no
merged cells) and is the first real exercise of table conversion — see the "Specific insets flagged" table
below.

## Specific equations/insets flagged for human review

| Section | Item | Issue | Resolution taken |
|---|---|---|---|
| 2.1 | eq. (11) `\mbox{\thinspace and\thinspace}` | `\mbox` and `\thinspace` are not in MathJax's default macro set | Added `mbox` and `thinspace` macros to `docs/js/mathjax_config.js`; verified render (see `screenshot_section_2.1.png`) |
| 2.1, 2.6, 2.9–2.16, 3.x (throughout) | `\tr`, `\dev`, `\grad`, `\divg`, etc. | Custom operators defined in the *full manual's* LyX preamble (`\newcommand`), not standard LaTeX/MathJax | Added equivalent `macros` entries to `docs/js/mathjax_config.js` |
| 2.1, 2.6 (eq. 19, 22, 25, 26) | `\obslash` | **No macro definition exists anywhere in the source LyX file for this symbol** — appears to be a gap in the original document, not something this converter introduced | Renders as `⦸` (U+29B8 CIRCLED REVERSE SOLIDUS, `\mathbin{\unicode{x29B8}}` in `mathjax_config.js`), confirmed against the published manual as the correct glyph (backslash-in-a-circle, mirroring `\oslash`'s forward-slash-in-a-circle); previously approximated as an overlined `\oslash`, which was visually wrong |
| 2.5 | Figure captions/images (3×) | Original image binaries not present in the pilot's original input directory | `build.py` fetches the real artwork from `febiosoftware/FEBio` on GitHub at build time; original LyX caption text preserved verbatim |
| Chapter-spanning | Cross-section/cross-chapter `\eqref{}`/`\ref{}` to equations, e.g. `\eqref{eq88}` (defined in 2.5, referenced from 2.6), `\eqref{eq:virtual work}` (defined in 3.5, referenced from 2.13) | Each Section is a separate page; MathJax's per-page auto-numbering can't resolve a `\label{}` defined on a different page, so these previously rendered as unclickable "???" | `EQ_LABEL_REGISTRY` in `tools/lyx2md.py` resolves these to a static link with the target's own page-local equation number, e.g. `(2.5-35)`, linking to MathJax's `#mjx-eqn:<label>` anchor (with spaces in the label sanitized to underscores, matching MathJax's own id-generation); verified via a real browser that the displayed number exactly matches what MathJax itself shows on the target page, and that the link both navigates to the right page and scrolls to the right equation |
| 2.10, 2.9 | `\ref{subsec:Nearly-Incompressible-Hyperelast}`, `\ref{subsec:BS-continuous-variables}` | Cross-section reference | **Was a real converter bug**, not a checker limitation as earlier notes here claimed: `render_section_body()` redundantly re-registered every Subsection/Subsubsection label a second time during rendering, without a filename, silently overwriting the correct pre-scanned registry entry the moment that section was rendered and breaking any *later*-rendered section's link to it. Fixed by removing the redundant re-registration; the pre-scan pass already handles it correctly |
| 3.1 | `FigCentrifugalBodyForce.png` | Bare `Graphics` inset decorated with `Box Frameless`/`VSpace` insets (for a print border and spacing), not wrapped in `Float`/`Caption` like Chapter 2's figures | Added `Box` (renders its content transparently — the frame/border is print-only styling with no Markdown equivalent) and `VSpace` (renders as nothing, same treatment as `Newpage`) to the inset dispatch table; the `Graphics` inset itself already rendered correctly regardless of its wrapper |
| 3.4 | `Tabular` inset (7×3 grid) | `render_tabular()` was previously a stub that always emitted `<!-- TABLE: manual review needed -->`, untested since Chapter 2 has zero tables | Implemented for real: LyX's tabular format is an embedded pseudo-XML dialect (`<lyxtabular>`, `<row>`, `<cell>`) that the line-based parser doesn't understand structurally, so those tags are used purely as delimiters to group the `Text` insets (which *are* correctly parsed) holding each cell's content, rendered as a plain Markdown table (first row as header). Also surfaced two general renderer bugs, not table-specific: (1) a cell's `\series bold` with no explicit `\series default` before `\end_layout` (which LyX allows — formatting is implicitly scoped to the paragraph) left an unclosed `**` that then mis-paired with a later cell's marker, corrupting everything in between — fixed by auto-closing any open bold/emph/tt state at the end of every `render_items_inline()` call; (2) a Markdown table needs a single real newline between every row, which collided with a separate normalization pass that collapses stray single newlines to spaces — fixed by having `render_tabular()` protect its row breaks with a sentinel character, restored to real newlines only after that pass runs |
| 1.1, 1.2 | `\href{https://febio.org/knowledgebase/}{\emph{FEBio User's/Developer's Manual}}` (ERT) | ERT ("evil red text", raw LaTeX LyX has no native inset for) was previously always flagged for manual review and dropped, regardless of content | `render_ert()` reconstructs the raw LaTeX from LyX's per-line `\backslash`-token encoding and renders the one pattern that occurs in this document, `\href{}{}`, as a real Markdown link (unwrapping the nested `\emph{}` to Markdown emphasis) |
| — | `eq87`, `eq:viscous-stress`, `eq:virtual work` | Earlier notes here described these as broken references in FEBio's own source (no matching `\label{}` anywhere) | **Correction:** all three are real, resolvable labels — missed by an incomplete search at the time (only `CommandInset label` was checked, not raw `\label{}` embedded in formula bodies, which is how equation labels are actually written). `eq87` and `eq:virtual work` are within currently-converted chapters and now resolve correctly; `eq:viscous-stress` is in Chapter 5 (Constitutive Models), not yet converted |

## Fidelity spot-checks against published HTML

- **Section 2.1** (`docs/theory/chapter2/2.1-vectors-and-tensors.md` vs.
  [help.febio.org TM40-Section-2.1](https://help.febio.org/docs/FEBioTheory-4-0/TM40-Section-2.1.html)):
  matches on all definitions (dot/scalar product, cross product, vector
  outer product, double contraction/tensor inner product, trace, tensor
  invariants \(I_1, I_2, I_3\), symmetric/anti-symmetric decomposition,
  Voigt notation, permutation tensor, fourth-order tensor operators
  \(\otimes, \oslash, \obslash, \odot\) and their Cartesian component
  forms, fourth-order identity tensors) and the single footnote citing Lai,
  Rubin & Krempl's *Introduction to Continuum Mechanics*. Equation numbering
  (1)–(26) is sequential and matches the source structure.
- **Section 2.6** (`docs/theory/chapter2/2.6-hyperelasticity.md` vs. the
  [published TOC for 2.6](https://help.febio.org/docs/FEBioTheory-4-0/TM40-Section-2.6.html)):
  all 9 subsections match exactly, in order — 2.6.1 Constitutive
  Restrictions, 2.6.2 Other Stress Tensors, 2.6.3 Directional Derivative of
  the Stress, 2.6.4 Isotropic Hyperelasticity, 2.6.5 Isotropic Elasticity in
  Principal Directions, 2.6.6 Transversely Isotropic Hyperelasticity, 2.6.7
  Incompressibility, 2.6.8 Nearly-Incompressible Hyperelasticity, 2.6.9
  Tension-Bearing Fiber Materials — confirmed via
  `grep -n "^## " docs/theory/chapter2/2.6-hyperelasticity.md`.

## Visual verification

`mkdocs serve` was run locally and section 2.1 and 2.6 were screenshotted
with a headless-Chromium Playwright script
(`tools/screenshot_section.py`) after waiting for MathJax's
`mjx-container` elements to appear:

- `screenshot_section_2.1.png` — confirms all 26 numbered display equations
  render as typeset math (matrices, tensors, fractions), the sidebar nav
  lists all 16 sections, and the footnote renders at the bottom of the page.
- `screenshot_section_2.6.png` — confirms the denser, citation-heavy section
  (11 citations, 79 display equations) also renders cleanly end-to-end with
  no raw LaTeX visible.

Real rendering bugs that were only caught by actually looking at the rendered page, not by static
grep-based checks, across the life of this project so far: the `\tr`/`\obslash` custom-macro gap, the
`\mbox`/`\thinspace` nesting issue, the table-cell unclosed-bold-marker bug, the table-row newline collapse,
and the `mjx-eqn:` anchor space-to-underscore sanitization needed for a working cross-chapter equation link
— see `docs/js/mathjax_config.js`, `tools/lyx2md.py`, and the tables above.
