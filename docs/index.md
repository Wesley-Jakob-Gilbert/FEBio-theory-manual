# FEBio 4.12 — Theory Manual

This is a pilot MkDocs conversion of the [FEBio Theory Manual](https://help.febio.org/), covering **Chapter 2: Continuum Mechanics**.

The manual was originally authored in [LyX](https://www.lyx.org/) (`FEBio_Theory_Manual.lyx`) and has been converted to Markdown using a
custom, deterministic converter (`tools/lyx2md.py`) so that it can be published as a searchable, versioned static site with
[MkDocs](https://www.mkdocs.org/) and the [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) theme, following the
same conventions established by the [FEBio Feature Manual](https://github.com/febiosoftware) build.

## Chapter 2 — Continuum Mechanics

This chapter contains an overview of some of the important concepts from continuum mechanics and establishes some of the notation and
terminology used in the rest of the FEBio documentation: deformation, stress and strain, hyperelasticity, and virtual work — later used
to derive the nonlinear finite element equations.

Use the navigation menu (or the tabs above) to browse sections 2.1 through 2.16.

## About this pilot

* **Source:** `source/ch2.lyx`, a vendored copy of `ch2.lyx` (extracted from `FEBio_Theory_Manual.lyx`, lines 808–16401), checked into
  this repository so it builds standalone from a bare clone.
* **Converter:** `tools/lyx2md.py` — a dependency-free, deterministic LyX → Markdown parser (see `README.md` for details).
* **Bibliography:** citations are resolved against `source/FEBio3.bib` and rendered as page-level Markdown footnotes.
* **Equations:** rendered with [MathJax](https://www.mathjax.org/) via `pymdownx.arithmatex` (`generic` mode), using the same
  `\( ... \)` / `\[ ... \]` delimiters and `ams` ▸ `\eqref` numbering convention as the Feature Manual.
* **Figures:** the three images in section 2.5 aren't part of the pilot's LyX/BibTeX inputs, so `build.py` fetches them from the
  upstream [`febiosoftware/FEBio`](https://github.com/febiosoftware/FEBio) repository at build time.

See `CONVERSION_NOTES.md` in the repository root for a per-section breakdown of what converted cleanly and what still needs a human
pass.
