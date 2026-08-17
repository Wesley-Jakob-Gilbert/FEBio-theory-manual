# Preface

This is a pilot MkDocs conversion of the [FEBio Theory Manual](https://help.febio.org/). The manual was originally authored in
[LyX](https://www.lyx.org/) (`FEBio_Theory_Manual.lyx`) and has been converted to Markdown using a
custom, deterministic converter (`tools/lyx2md.py`) so that it can be published as a searchable, versioned static site with
[MkDocs](https://www.mkdocs.org/) and the [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) theme, following the
same conventions established by the [FEBio Feature Manual](https://github.com/febiosoftware/febio-feature-manual) build.

Use the **Theory** tab above (and the navigation menu on the left) to browse by chapter and section. The
[FEBio Studio Manual](../studio/index.md) is converted the same way and lives under the **Studio** tab.

## About this pilot

* **Source:** `source/FEBio_Theory_Manual.lyx`, a vendored copy of the complete manual, checked into this repository so it builds
  standalone from a bare clone. Which chapters actually get converted into pages is controlled by `CHAPTERS_TO_CONVERT` in
  `tools/lyx2md.py`.
* **Converter:** `tools/lyx2md.py` — a dependency-free, deterministic LyX → Markdown parser (see `README.md` for details).
* **Bibliography:** citations are resolved against `source/FEBio3.bib` and rendered as page-level Markdown footnotes.
* **Equations:** rendered with [MathJax](https://www.mathjax.org/) via `pymdownx.arithmatex` (`generic` mode), using the same
  `\( ... \)` / `\[ ... \]` delimiters and `ams` ▸ `\eqref` numbering convention as the Feature Manual. Since each section is a
  separate page, a same-page `\eqref{}` is left for MathJax to resolve on its own, but a reference to an equation defined in a
  *different* section or chapter is resolved at build time to a link with an explicit page-local number, e.g. `(2.5-35)`.
* **Figures:** images that aren't part of the pilot's LyX/BibTeX inputs are fetched by `build.py` from the upstream
  [`febiosoftware/FEBio`](https://github.com/febiosoftware/FEBio) repository at build time.

See `CONVERSION_NOTES.md` in the repository root for a per-section breakdown of what converted cleanly and what still needs a human
pass.
