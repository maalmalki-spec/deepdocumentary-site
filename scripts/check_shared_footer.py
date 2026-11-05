#!/usr/bin/env python3
"""Fail CI when a published page loses the shared Deep Documentary footer."""
from pathlib import Path
from html.parser import HTMLParser
import sys

ROOT = Path(__file__).resolve().parents[1]
SKIP = {".git", "node_modules", "dist", "build", ".next"}
REQUIRED_LINKS = ("about.html", "contact.html", "privacy.html", "terms.html")
class FooterParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_footer = 0
        self.found = False
        self.logo = False
        self.links = set()
        self.copy = False
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "footer" and "dd-unified-footer" in a.get("class", "").split():
            self.in_footer += 1
            self.found = True
        if not self.in_footer:
            return
        if tag == "img" and "dd-footer-logo" in a.get("class", "").split():
            self.logo = True
        if tag == "a":
            self.links.add(a.get("href", "").split("?")[0].split("/")[-1])
        if "dd-footer-copy" in a.get("class", "").split():
            self.copy = True
    def handle_endtag(self, tag):
        if tag == "footer" and self.in_footer:
            self.in_footer -= 1

errors = []
checked = 0
for path in sorted(ROOT.rglob("*.html")):
    if any(part in SKIP or part.startswith(".") for part in path.relative_to(ROOT).parts):
        continue
    text = path.read_text(encoding="utf-8")
    if "<html" not in text.lower():
        continue
    checked += 1
    p = FooterParser()
    p.feed(text)
    missing = []
    if not p.found: missing.append("unified footer")
    if not p.logo: missing.append("footer logo")
    if not p.copy: missing.append("copyright")
    for link in REQUIRED_LINKS:
        if link not in p.links: missing.append("link " + link)
    if "shared-footer.css" not in text: missing.append("shared-footer.css")
    if missing: errors.append(f"{path.relative_to(ROOT)}: {', '.join(missing)}")
print(f"Checked {checked} HTML pages.")
if errors:
    print("FOOTER AUDIT FAILED:")
    print("\n".join(errors))
    sys.exit(1)
print("All pages have the shared footer and required links.")
