# Preface

This is a MkDocs conversion of the [FEBio Studio Manual](https://help.febio.org/). The manual was originally authored in
[LyX](https://www.lyx.org/) (`FEBioStudio_User_Manual.lyx`) and has been converted to Markdown using the same
custom, deterministic converter (`tools/lyx2md.py`) used for the [Theory](../theory/index.md) tab, so it can be published as part of the
same searchable, versioned static site with [MkDocs](https://www.mkdocs.org/) and the [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) theme.
The complete manual is converted — all 20 chapters plus Appendices A (Mesh Import Formats) and B (Standard Data Fields).

Use the **Studio** tab above to browse by chapter and section.

## About this conversion

* **Source:** `source/FEBioStudio_User_Manual.lyx`, a vendored copy of the complete manual, checked into this repository so it builds
  standalone from a bare clone.
* **Converter:** the same `tools/lyx2md.py` used for the Theory Manual, run as a separate pass with this manual's own LyX/bib source
  and its own `docs/studio/` output tree (see `build.py`'s `MANUALS` list). Converting this manual surfaced several real converter
  gaps not present in the Theory Manual's source (e.g. `Wrap`-figure insets, `Description`/`LyX-Code` layouts, a content-loss bug in
  tables wrapped in a `Float table` inset) — see `CONVERSION_NOTES_STUDIO.md` for the full list of fixes.
* **Bibliography:** citations are resolved against `source/FEBioStudio.bib` and rendered as page-level Markdown footnotes, the same
  as the Theory Manual — though this manual has very few citations, being primarily UI/GUI documentation rather than a theoretical
  reference.
* **Math:** this manual is almost entirely prose and screenshots, not equations — MathJax/`\eqref` cross-page resolution logic exists
  in the converter but sees little to no use here.
* **Figures:** images that aren't part of this manual's LyX/BibTeX inputs are fetched by `build.py` from the upstream
  [`febiosoftware/FEBioStudio`](https://github.com/febiosoftware/FEBioStudio) repository at build time.

See `CONVERSION_NOTES_STUDIO.md` in the repository root for a per-chapter breakdown and every item flagged for manual review.
