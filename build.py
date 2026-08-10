#!/usr/bin/env python3
"""
build.py -- Build script for the FEBio Theory Manual.

Mirrors the style of febio-feature-manual/build.py:
  1. Runs the LyX -> Markdown converter (tools/lyx2md.py) to (re)generate
     docs/theory/chapterN/*.md from source/FEBio_Theory_Manual.lyx, for
     whichever chapters tools/lyx2md.py's CHAPTERS_TO_CONVERT includes.
  2. Writes mkdocs.yml with the same Material theme / markdown_extensions
     conventions as febio-feature-manual (indigo palette, arithmatex
     generic + MathJax via docs/js/mathjax_config.js + jsdelivr
     tex-mml-chtml, admonition, footnotes, toc permalink,
     pymdownx.blocks.caption, superfences, details), plus attr_list
     (needed so that the converter's explicit heading anchors --
     `## Title {: #label }`, produced from LyX \\label insets -- work for
     cross-chapter/cross-section \\ref links).

Navigation is a single unified sidebar tree (no navigation.tabs): a
Preface entry, then one top-level nav group per converted chapter, each
expanding to that chapter's sections -- not one browser tab per chapter.

Usage:
    python3 build.py [-v|--verbose]
"""
import glob
import json
import re
import subprocess
import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))

args = sys.argv[1:]
verbose = "-v" in args or "--verbose" in args

print("Building FEBio 4.12 Theory Manual...")

# ---------------------------------------------------------------------
# Step 1: run the LyX -> Markdown converter
# ---------------------------------------------------------------------
if verbose:
    print("Running tools/lyx2md.py ...")

result = subprocess.run(
    [sys.executable, os.path.join(ROOT, "tools", "lyx2md.py")],
    cwd=ROOT,
    capture_output=not verbose,
    text=True,
)
if result.returncode != 0:
    print("ERROR: lyx2md.py failed")
    if not verbose:
        print(result.stdout)
        print(result.stderr)
    sys.exit(1)
elif not verbose:
    print(result.stdout.strip())

# ---------------------------------------------------------------------
# Step 2: load conversion stats (per-chapter nav entries)
# ---------------------------------------------------------------------
stats_path = os.path.join(ROOT, "tools", "_stats.json")
with open(stats_path, "r", encoding="utf-8") as f:
    stats = json.load(f)

chapters = stats["chapters"]  # [{"chap_num", "title", "dir", "nav": [[title, path], ...]}, ...]

# ---------------------------------------------------------------------
# Step 3: write mkdocs.yml
# ---------------------------------------------------------------------
if verbose:
    print("Writing mkdocs.yml...")

with open(os.path.join(ROOT, "mkdocs.yml"), mode="w", encoding="utf-8") as f:
    f.write('site_name: "FEBio 4.12 - Theory Manual"\n')
    f.write("site_description: This manual provides the theoretical background for FEBio.\n")
    f.write("site_author: FEBio Team\n")
    f.write("theme:\n")
    f.write("  name: material\n")
    f.write("  palette:\n")
    f.write("    primary: indigo\n")
    f.write("    accent: indigo\n")
    f.write("  font:\n")
    f.write("    text: 'Roboto'\n")
    f.write("    code: 'Roboto Mono'\n")
    f.write("  features:\n")
    f.write("    - navigation.top\n")
    f.write("    - navigation.footer\n")
    f.write("    - search.highlight\n")
    f.write("    - search.suggest\n")
    f.write("    - toc.integrate\n")
    f.write("    - content.external.links\n")
    f.write("markdown_extensions:\n")
    f.write("  - admonition\n")
    f.write("  - attr_list\n")
    f.write("  - codehilite\n")
    f.write("  - footnotes\n")
    f.write("  - toc:\n")
    f.write("      permalink: true\n")
    f.write("  - pymdownx.arithmatex:\n")
    f.write("      generic: true\n")
    f.write("  - pymdownx.superfences\n")
    f.write("  - pymdownx.blocks.caption\n")
    f.write("  - pymdownx.details\n")
    f.write("extra_javascript:\n")
    f.write("  - js/mathjax_config.js\n")
    f.write("  - https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js\n")
    f.write("nav:\n")
    f.write("  - Preface: index.md\n")
    for chap in chapters:
        f.write(f"  - Chapter {chap['chap_num']} - {chap['title']}:\n")
        for title, path in chap["nav"]:
            f.write(f"    - {title}: {path}\n")

total_sections = sum(len(c["nav"]) for c in chapters)
print(f"Wrote mkdocs.yml with {len(chapters)} chapters, {total_sections} section pages.")

# ---------------------------------------------------------------------
# Step 4: fetch any figure artwork that isn't already vendored in the
# repo. The originals live in the FEBio repo under Documentation/Figures/.
# Scans every converted chapter's generated Markdown for figure
# references (not hardcoded to a specific chapter's known figures), so
# this keeps working as more chapters get converted.
# ---------------------------------------------------------------------
import urllib.request as _url

_FIG_BASE = "https://raw.githubusercontent.com/febiosoftware/FEBio/master/Documentation/Figures/"
_FIG_RE = re.compile(r"!\[[^\]]*\]\(figs/([^)]+?)\)")

for _md_path in glob.glob(os.path.join(ROOT, "docs", "theory", "chapter*", "*.md")):
    _chapter_dir = os.path.dirname(_md_path)
    _figs_dir = os.path.join(_chapter_dir, "figs")
    with open(_md_path, "r", encoding="utf-8") as _f:
        _text = _f.read()
    for _fig in _FIG_RE.findall(_text):
        os.makedirs(_figs_dir, exist_ok=True)
        _dest = os.path.join(_figs_dir, _fig)
        if os.path.exists(_dest) and os.path.getsize(_dest) > 2048:
            continue
        try:
            _url.urlretrieve(_FIG_BASE + _fig, _dest)
            print(f"  fetched figure: {_fig}")
        except Exception as _e:
            print(f"  WARNING: could not fetch {_fig}: {_e}")

print("Build complete.")
print()
print("Next steps:")
print("  pip install mkdocs mkdocs-material")
print("  mkdocs serve      # preview at http://127.0.0.1:8000")
print("  mkdocs build --strict")
