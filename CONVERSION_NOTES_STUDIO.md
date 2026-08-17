# Conversion Notes — FEBio Studio Manual

Generated from `source/FEBioStudio_User_Manual.lyx` using the same `tools/lyx2md.py` converter as the
Theory Manual (see `CONVERSION_NOTES.md`), run as a separate pass via `build.py`'s `MANUALS` list with
this manual's own LyX/bib source and its own `docs/studio/` output tree.

**This is a pilot, not a complete conversion.** `build.py`'s `MANUALS` entry for `"studio"` has
`"chapters": "1,2"`, converting only Chapter 1 (Introduction) and Chapter 2 (Getting Started) — 8
sections total, out of a full manual of ~20 chapters / ~105 sections (per the live TOC at
https://help.febio.org/docs/FEBioStudio-3-1/FSM31.html). The goal of this pass was to validate that the
Theory-Manual-tuned converter, largely unmodified, produces clean output against a different manual's
LyX source — one that's almost entirely UI/GUI prose and screenshots rather than dense mathematics —
before committing to a full conversion. Widening `"chapters"` toward `"all"` is explicit follow-up work.

## Reconciliation summary

| Check | Result |
|---|---|
| Chapters converted | 2 of 20 (Introduction, Getting Started) — pilot scope |
| Sections converted | 8 |
| Inline `$...$` emitted | 1 (a keyboard-shortcut "+" rendered via inline math in the source, not a real equation) |
| Display `\[...\]` emitted | 0 |
| Citations | 0 |
| Figures | 5 |
| Leftover LyX artifacts (`\begin_`, `\end_inset`, `\begin_inset`, `SpecialChar`, `\lang `) | **0** |
| Unhandled/unrecognized inset kinds | **0** (after two converter fixes below) |
| `mkdocs build --strict` (both manuals together) | exit code 0, **zero** `WARNING`-level messages |

## Converter gaps found and fixed against this manual's real content

The Theory Manual's source never exercised these; both are now fixed in `tools/lyx2md.py` and covered by
the "Notes for future edits" section of `CLAUDE.md`:

1. **`\begin_inset Wrap figure`** (LaTeX's `wrapfig` — a text-wrapped figure) had no renderer and fell
   through to `<!-- UNHANDLED INSET ... -->`. Its substructure (a `Plain Layout` containing a `Graphics`
   inset and a `Caption`) is identical to `Float figure`'s, and Markdown has no text-wrap-around-image
   equivalent anyway, so it's now aliased to the existing `render_float()` path. The figure-numbering
   prescan (`prescan_nested()`) was also updated to count `Wrap`-wrapped figures the same way it already
   counted `Float`-wrapped ones, so `\ref{}` numbering stays consistent with what `pymdownx.blocks.caption`
   actually displays.
2. **A native `\begin_inset CommandInset href`** (LyX's own hyperlink inset, distinct from the ERT
   `\href{}{}`/`\url{}` reconstruction the Theory Manual relies on) was unhandled. Added the same
   rendering convention as the ERT case: an optional display `name` becomes a Markdown link, an unnamed
   one becomes a bare autolink.
3. **A whitespace-normalization regex** in `render_items_inline()` (intended to strip a spurious space
   before sentence-ending punctuation left over from LyX's line-continuation joining) was also stripping
   the *genuine* space before a literal file-extension token — `"the .xplt file extension"` was rendering
   as `"the.xplt file extension"`. Fixed with a negative lookahead so the space is only stripped when the
   punctuation isn't immediately followed by a word character.

None of these are content-loss bugs caught after the fact by a reconciliation mismatch (unlike, e.g., the
Theory Manual's Chapter 6 chapter-intro bug) — the first two were caught directly via
`unhandled`/`needs_review` during this pilot's first conversion attempt, and the third via manual spot-
reading of the rendered pages.

## Per-section breakdown

### Chapter 1 — Introduction

| Section | Title | Inline formulas | Figures | Converted cleanly? | Needs manual review |
|---|---|---|---|---|---|
| 1.1 | Overview of FEBioStudio | 0 | 0 | Yes | None |
| 1.2 | About this document | 0 | 0 | Yes | None — includes a native `href` link to the FEBio Knowledgebase (see fix #2 above) |

### Chapter 2 — Getting Started

| Section | Title | Inline formulas | Figures | Converted cleanly? | Needs manual review |
|---|---|---|---|---|---|
| 2.1 | Starting FEBio Studio | 0 | 1 | Yes | Figure `welcome.png` fetched at build time from `febiosoftware/FEBioStudio` |
| 2.2 | Creating a New Model | 0 | 1 | Yes | Figure `Figure_2_2.png` fetched at build time; forward-reference "Chapter 3" renders as plain text (Chapter 3 not yet converted — expected pilot-scope degradation, not a bug) |
| 2.3 | Opening a Model | 0 | 1 | Yes | Figure `Figure_2_3.png` fetched at build time |
| 2.4 | Exploring a Model | 1 | 0 | Yes | The one inline formula is a keyboard shortcut ("ctrl+z") written as inline math in the source, not real mathematics; contains an unresolved `\ref{subsubsec:navigating}` — target is in a later, unconverted chapter, so it renders as a same-page anchor link that doesn't resolve yet (expected pilot-scope degradation) |
| 2.5 | Solving the Model | 0 | 1 | Yes | Figure `run_febio.png` (a `Wrap figure` inset — see fix #1 above) fetched at build time; forward-reference "13" (Chapter 13, not yet converted) renders as plain text |
| 2.6 | Loading the Results | 0 | 1 | Yes | Figure `Figure_2_4.png` fetched at build time; contains an unresolved `\ref{subsec:postui}` — same expected pilot-scope degradation as 2.4 |

## What's left

Chapters 3–20 plus the appendix (~97 sections) are not yet converted. Widening scope should be done
incrementally rather than in one jump — e.g. a chapter or two at a time, watching `needs_review` and the
leftover-artifact grep after each step — the same way the Theory Manual itself grew from a single-chapter
pilot to the full manual. Expect further new LyX constructs to surface as later chapters (Materials,
Mesh Data, Post Processing, 3D Image Data, Python, Plugins) are reached, since this pilot only exercised
Chapters 1–2's relatively simple prose-and-screenshot content.
