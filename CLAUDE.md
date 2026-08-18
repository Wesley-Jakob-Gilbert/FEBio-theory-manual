# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A MkDocs site that converts FEBio's LyX-authored manuals to Markdown, mirroring the conventions of the
sibling `febio-feature-manual` repo (Material for MkDocs theme, indigo palette, `pymdownx.arithmatex` +
MathJax for equations, footnote-based citations). The site has two `navigation.tabs`, each a separately
converted manual, orchestrated by `build.py`'s `MANUALS` list:

- **Theory** (`source/FEBio_Theory_Manual.lyx` → `docs/theory/`) — all 9 chapters (1–8 plus Appendix A)
  are converted.
- **Studio** (`source/FEBioStudio_User_Manual.lyx` → `docs/studio/`) — all 22 chapters (1–20 plus
  Appendices A and B) are converted.

`source/` is vendored/checked-in for both manuals, so the repo builds standalone from a bare clone.

**`docs/theory/` and `docs/studio/` (except their `index.md` files) are generated output, not
hand-authored content.** They're regenerated from each manual's `.lyx` source by `tools/lyx2md.py` on
every build. Do not hand-edit generated chapter/section files expecting them to persist — fix the
converter (`tools/lyx2md.py`) instead, or edit the relevant `source/*.lyx` file if the manual content
itself is wrong. `docs/index.md` (site-root landing page, not in `nav:`), `docs/theory/index.md` and
`docs/studio/index.md` (each manual's Preface), and `docs/js/mathjax_config.js` are hand-authored
exceptions.

## Commands

```
pip install mkdocs mkdocs-material   # prerequisites

python3 build.py                     # runs tools/lyx2md.py once per manual, (re)writes docs/**/*.md and mkdocs.yml
python3 build.py -v                  # verbose (streams lyx2md.py's own stdout instead of buffering it)
mkdocs serve                         # preview at http://127.0.0.1:8000
mkdocs build --strict                # validate the full build; must exit 0 with zero WARNINGs
mkdocs gh-deploy --force             # manually publish site/ to the gh-pages branch (needs push access)

# tools/lyx2md.py is generic across manuals via CLI flags (build.py passes these per MANUALS entry):
python3 tools/lyx2md.py --lyx PATH --bib PATH --docs-root DIR --nav-root PREFIX --stats-out PATH --chapters "1,2|all"
```

There is no test suite. Validation is: `python3 build.py && mkdocs build --strict` exits 0 with no
`WARNING`-level output (`INFO`-level messages about cross-page equation anchors are expected — see
below), plus a leftover-artifact grep across both manuals' output:

```
grep -rn '\begin_\|\end_inset\|\begin_inset\|SpecialChar\|\lang ' docs/   # must be zero matches
```

Each manual's stats sidecar (`tools/_stats.json` for Theory, `tools/_stats_studio.json` for Studio,
written by `lyx2md.py`) reports per-chapter/per-section formula, citation, and figure counts —
reconcile these against the source when validating a chapter (see `CONVERSION_NOTES.md` /
`CONVERSION_NOTES_STUDIO.md` for the established methodology and known small discrepancies).

CI (`.github/workflows/deploy.yml`) runs `python3 build.py` then `mkdocs build --strict` on every push
to `main`, then `mkdocs gh-deploy --force`. **The live site is served from the `gh-pages` branch, not
from `docs/` on `main`** — pushing to `main` alone does not update the live site by itself; it only
triggers the workflow that does.

## Architecture

### Pipeline

For each manual in `build.py`'s `MANUALS` list: `source/<manual>.lyx` → `tools/lyx2md.py` (invoked as a
separate subprocess per manual, with `--lyx`/`--bib`/`--docs-root`/`--nav-root`/`--stats-out`/`--chapters`)
→ `docs/<nav_root>/chapter<N>/<N>.M-slug.md` + that manual's stats JSON → `build.py` reads all manuals'
stats files and writes one `mkdocs.yml` whose `nav:` has one top-level tab per manual → `mkdocs build`.
Running each manual as a separate subprocess means `lyx2md.py`'s module-level globals/label-registries
never cross-contaminate between manuals — no in-process reset logic is needed.

`tools/lyx2md.py` is a **stdlib-only, deterministic** parser for LyX's plain-text format — no LyX,
Pandoc, or other external tool involved, and the parsing/rendering logic itself is identical regardless
of which manual is being converted. `--chapters` (a comma list or `"all"`) controls which chapters
produce output pages for that run; chapters outside that set are still scanned for titles/label
positions so numbering and cross-references stay correct regardless of conversion order. Both manuals
pass `"all"` (Theory: `{1..9}`, chapter 9 = Appendix A; Studio: `{1..22}`, chapters 21–22 = Appendices A
and B). A chapter with zero `Section` boundaries (Studio's Appendix B) is treated as a single synthetic
section rather than producing an empty nav entry, since `mkdocs build --strict` rejects that outright.

Key stages inside `lyx2md.py` (all in one file — read the module docstring first):

1. `parse_flat()` tokenizes the file into a tree of `('text', ...)` / `('inset', spec, subitems)` /
   `('layout', spec, subitems)` tuples.
2. Chapter/section boundaries are located by scanning for `Chapter`/`Section` layouts; a chapter
   marked with LyX's native `\start_of_appendix` (and everything after it) is numbered with a letter
   instead of a digit.
3. **Two-pass label resolution**: a pre-scan registers every `\label` into `LABEL_REGISTRY` (sections/
   figures), `EQ_LABEL_REGISTRY` (equations), and `CHAPTER_LABEL_REGISTRY` (chapter-level, for every
   chapter regardless of conversion status) before rendering, so `\ref{}`/`\eqref{}` resolve correctly
   even across chapter files, and a reference into an *unconverted* chapter degrades gracefully
   (renders the chapter number as plain text, flagged in `needs_review`) instead of crashing.
4. Character formatting, math, citations (from `source/FEBio3.bib` via a hand-written `parse_bib()`),
   figures, tables, and "ERT" (raw LaTeX LyX has no inset for) each have dedicated rendering logic —
   see the corresponding numbered sections in README.md for the specific conventions/quirks of each
   (e.g. why `\obslash` renders as U+29B8, why `\mbox{}` stays in math mode, how merged table cells are
   flagged rather than silently mis-rendered).
5. Anything unrecognized renders as `<!-- UNHANDLED INSET ... -->` and is logged to `needs_review`
   rather than silently dropped — this is what makes the leftover-artifact grep a completeness check.

### Cross-reference resolution across pages

Each Section is a separate MkDocs page, and MathJax's `tags: 'ams'` equation auto-numbering is
per-page — it can't resolve a `\eqref{}` to a `\label{}` defined on a different page. `lyx2md.py`
resolves same-chapter/cross-chapter equation references to static links (e.g. `(2.5-35)`) at build
time using `EQ_LABEL_REGISTRY`'s recorded 1-indexed position of each label among its own page's
equations; MathJax injects the actual `#mjx-eqn:<label>` anchor client-side after typesetting, which
is *after* the browser's initial fragment-scroll already ran — `docs/js/mathjax_config.js` re-attempts
the scroll via MathJax's `startup.pageReady` hook. This is also why `mkdocs build --strict` reports
`INFO`-level "does not contain an anchor" messages for these links even though they work in a real
browser: the anchors don't exist until MathJax runs client-side.

### Figures

Figure PNGs are not part of either manual's LyX/BibTeX source. `build.py`'s step 4 loops over
`MANUALS`, scanning each manual's converted chapters' generated Markdown for `figs/<name>` references
and fetching any missing ones from that manual's own `fig_base` upstream repo (`febiosoftware/FEBio`'s
`Documentation/Figures/` for Theory, `febiosoftware/FEBioStudio`'s for Studio) into that chapter's
`figs/` directory (skipping any file already present and >2KB, to avoid re-fetching real vendored
copies).

## Notes for future edits

- `mkdocs.yml` is generated by `build.py` — don't hand-edit it; change the write logic in `build.py`
  instead (theme config and the `MANUALS` list live inline as `f.write(...)` calls / a module-level
  list at the top of the file).
- Merged table cells (colspan/rowspan) can't be represented in plain Markdown tables; `render_tabular()`
  flags these for manual review rather than guessing — check `CONVERSION_NOTES.md`/`needs_review` before
  assuming a table rendered correctly (occurs in Section 4.1's element-property tables).
- `CONVERSION_NOTES.md` (Theory) / `CONVERSION_NOTES_STUDIO.md` (Studio) have the full per-section
  conversion breakdown and every item flagged for manual review — check the relevant one before assuming
  a discrepancy between the manual and the rendered output is a new bug.
- Converting the Studio Manual surfaced many real converter gaps not present in the Theory Manual's
  source — see `CONVERSION_NOTES_STUDIO.md` for the full list. Worth knowing if extending `lyx2md.py`
  further: `Wrap`-figure insets alias to the existing `Float figure` handling; `Description`/`LyX-Code`
  layouts have dedicated renderers; a `Float table` (vs. `Float figure`) needed `render_float()` to also
  check for a `Tabular` inset — previously a silent content-loss bug with no `needs_review` flag, the most
  serious gap found; LaTeX accent commands in BibTeX fields (`decode_latex_accents()`) and `\backslash`
  tokens in ordinary prose (not just inside ERT) both needed decoding. The open-marker-stack rewrite of
  character-formatting state (`close_marker()` in `render_items_inline()`) also fixed a **pre-existing**
  Theory Manual bug: LyX doesn't always close formatting markers in reverse-of-open order, which the old
  four-independent-booleans state couldn't express correctly.
