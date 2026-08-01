# Conversion Notes — Chapter 2 (Continuum Mechanics)

Generated from `febio-docs/ch2.lyx` (1823 total `Formula` insets, 59
`CommandInset citation`, 62 `CommandInset label`, 223 `CommandInset ref`,
3 `Float figure` / `Graphics` / `Caption`, 0 `Tabular`) using
`tools/lyx2md.py`. Totals reconciled below; per-section detail follows.

## Reconciliation summary

| Check | Result |
|---|---|
| Formula insets in source | 1823 |
| Inline `$...$` emitted (all sections) | 1455 |
| Display `\[...\]` emitted (all sections) | 368 |
| Sum | **1823 — exact match, zero formulas lost** |
| Citation insets in source | 59 |
| Unique footnote definitions emitted | 58 (1 key reused twice on the same page) |
| Leftover LyX artifacts (`\begin_`, `\end_inset`, `\begin_inset`, `SpecialChar`, `\lang `) | **0** |
| Unhandled/unrecognized inset kinds | **0** |
| `mkdocs build --strict` | exit code 0 (7 `INFO`-level out-of-scope anchor notices, 0 `WARNING`) |

## Per-section breakdown

| Section | Title | Inline formulas | Display formulas | Citations | Figures | Converted cleanly? | Needs manual review |
|---|---|---|---|---|---|---|---|
| 2.1 | Vectors and Tensors | 42 | 26 | 1 | 0 | Yes | None |
| 2.2 | The Directional Derivative | 10 | 6 | 1 | 0 | Yes | None |
| 2.3 | Cauchy Stress | 21 | 1 | 0 | 0 | Yes | None |
| 2.4 | Axioms of Conservation | 30 | 11 | 0 | 0 | Yes | None |
| 2.5 | Kinematics of the Continuum | 210 | 57 | 1 | 3 | Mostly | 3 figure placeholders (`FigKinematicsContinuum.png`, `FigShearStrain.png`, `FigReferentialVolume.png` — real artwork not in inputs); 1 unresolved `\ref{subsubsec:determinant}` (target not in Chapter 2) |
| 2.6 | Hyperelasticity | 144 | 79 | 11 | 0 | Mostly | 2 unresolved refs: `\ref{chap:Constitutive-Models}` (Chapter 3, out of pilot scope) and `\ref{eq87}` (target label doesn't exist in source — likely a typo/broken ref in the original LyX document itself, not a converter bug); uses `\obslash` (approximated, see README) and `\mbox{\thinspace and\thinspace}` (eq. 11, now renders correctly via MathJax macro fix) |
| 2.7 | Biphasic Material | 26 | 6 | 3 | 0 | Yes | None |
| 2.8 | Biphasic-Solute Material | 109 | 13 | 14 | 0 | Yes | None |
| 2.9 | Triphasic and Multiphasic Materials | 66 | 15 | 0 | 0 | Yes | None |
| 2.10 | Constrained Reactive Mixture of Solids | 201 | 29 | 6 | 0 | Mostly | 1 unresolved `\ref{subsec:Nearly-Incompressible-Hyperelast}` — this label *does* exist (in section 2.6.8), but `mkdocs`'s same-page-relative anchor check flags it as an `INFO` notice since the ref doesn't include the cross-file path; the underlying Markdown link itself correctly points to `2.6-hyperelasticity.md#subsec:Nearly-Incompressible-Hyperelast` |
| 2.11 | Equilibrium Swelling | 56 | 9 | 0 | 0 | Yes | None |
| 2.12 | Chemical Reactions | 105 | 41 | 0 | 0 | Yes | None |
| 2.13 | Fluid Mechanics | 127 | 24 | 0 | 0 | Mostly | 1 unresolved `\ref{sec:Viscous-Fluids}` (target not present anywhere in Chapter 2 — likely a later chapter or a section removed in this manual revision) |
| 2.14 | Fluid-Structure Interactions | 27 | 15 | 1 | 0 | Yes | None |
| 2.15 | Hybrid Biphasic Material | 137 | 17 | 8 | 0 | Mostly | 1 unresolved `\ref{sec:Hydraulic-Permeability}` (target not present in Chapter 2) |
| 2.16 | Fluid-Solutes Analyses | 144 | 19 | 12 | 0 | Yes | None |
| **Total** | | **1455** | **368** | **58 unique / 59 insets** | **3** | | |

## Specific equations/insets flagged for human review

| Section | Item | Issue | Resolution taken |
|---|---|---|---|
| 2.1 | eq. (11) `\mbox{\thinspace and\thinspace}` | `\mbox` and `\thinspace` are not in MathJax's default macro set | Added `mbox` and `thinspace` macros to `docs/js/mathjax_config.js`; verified render (see `screenshot_section_2.1.png`) |
| 2.1, 2.6, 2.9–2.16 (throughout) | `\tr`, `\dev`, `\grad`, `\divg`, etc. | Custom operators defined in the *full manual's* LyX preamble (`\newcommand`), not standard LaTeX/MathJax | Added equivalent `macros` entries to `docs/js/mathjax_config.js` |
| 2.1, 2.6 (eq. 19, 22, 25, 26) | `\obslash` | **No macro definition exists anywhere in the source LyX file for this symbol** — appears to be a gap in the original document, not something this converter introduced | Approximated as `\overline{\oslash}` in `mathjax_config.js`; flagged for confirmation with FEBio maintainers |
| 2.5 | Figure captions/images (3×) | Original image binaries not present in any input directory | Generated placeholder PNGs; original LyX caption text preserved verbatim |
| 2.6 | `\ref{eq87}` | Label `eq87` does not exist anywhere in `ch2.lyx` — likely a stale/broken reference in FEBio's own source document | Rendered as a dead anchor link; not a converter defect |
| 2.6 | `\ref{chap:Constitutive-Models}` | Points to Chapter 3, outside this pilot's extract | Left as unresolved cross-chapter link; expected for a single-chapter pilot |
| 2.10 | `\ref{subsec:Nearly-Incompressible-Hyperelast}` | Cross-section reference into 2.6.8 | Resolves correctly to `2.6-hyperelasticity.md#...`; MkDocs' strict-mode anchor checker only warns because it checks anchors per-page, not cross-file — this is a checker limitation, not a broken link |
| 2.13 | `\ref{sec:Viscous-Fluids}` | Target label not present in Chapter 2 | Left as unresolved; likely lives in a chapter outside this pilot's scope |
| 2.15 | `\ref{sec:Hydraulic-Permeability}` | Target label not present in Chapter 2 | Left as unresolved; likely lives in a chapter outside this pilot's scope |

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

Two real MathJax rendering bugs were caught and fixed this way (not
visible from grep-based checks alone, only from actually rendering the
page): the `\tr`/`\obslash` custom-macro gap, and the `\mbox`/`\thinspace`
nesting issue — see `docs/js/mathjax_config.js` and the "Specific
equations/insets flagged" table above.
