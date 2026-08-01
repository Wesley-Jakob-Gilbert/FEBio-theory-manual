#!/usr/bin/env python3
"""Capture a full-page screenshot of a locally-served MkDocs page using
Playwright, waiting for MathJax to finish typesetting before capturing."""
import sys
from playwright.sync_api import sync_playwright

url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/theory/chapter2/2.1-vectors-and-tensors/"
out_path = sys.argv[2] if len(sys.argv) > 2 else "/home/user/workspace/febio-theory-manual/screenshot_section_2.1.png"

with sync_playwright() as p:
    browser = p.chromium.launch(args=["--no-sandbox", "--disable-setuid-sandbox", "--no-proxy-server", "--proxy-bypass-list=*"])
    page = browser.new_page(viewport={"width": 1400, "height": 1000})
    # Block Google Fonts requests -- they can hang in this sandboxed network
    # and are not needed to verify math/layout rendering.
    page.route("**://fonts.gstatic.com/**", lambda route: route.abort())
    page.route("**://fonts.googleapis.com/**", lambda route: route.abort())
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    # Wait for MathJax to typeset (it injects <mjx-container> elements)
    try:
        page.wait_for_selector("mjx-container", timeout=15000)
        page.wait_for_timeout(1500)
    except Exception as e:
        print(f"WARNING: MathJax selector wait failed: {e}", file=sys.stderr)
    page.screenshot(path=out_path, full_page=True, timeout=60000)
    browser.close()

print(f"Saved screenshot to {out_path}")
