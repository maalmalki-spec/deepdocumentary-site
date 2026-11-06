#!/usr/bin/env python3
"""Audit published pages for missing local image and stylesheet assets."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import sys

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {"drafts", "editorial", ".git", "node_modules", "dist", "build"}
class Assets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("img", "script", "source"):
            self.refs.append((tag, a.get("src", "")))
        if tag == "link" and a.get("rel", "").lower() in ("stylesheet", "icon"):
            self.refs.append((tag, a.get("href", "")))
        if tag == "img" and a.get("srcset"):
            for item in a["srcset"].split(","):
                self.refs.append(("srcset", item.strip().split(" ")[0]))

failures = []
pages = 0
references = 0
for page in sorted(ROOT.rglob("*.html")):
    if any(part in EXCLUDED or part.startswith(".") for part in page.relative_to(ROOT).parts):
        continue
    content = page.read_text(encoding="utf-8")
    if "<html" not in content.lower():
        continue
    pages += 1
    parser = Assets()
    parser.feed(content)
    for tag, raw in parser.refs:
        if not raw or raw.startswith(("http:", "https:", "//", "data:", "blob:", "#")):
            continue
        target = unquote(urlsplit(raw).path)
        if not target:
            continue
        references += 1
        base = ROOT if target.startswith('/') else page.parent
        resolved = (base / target.lstrip('/')).resolve()
        if not resolved.is_relative_to(ROOT) or not resolved.is_file():
            failures.append(f"{page.relative_to(ROOT)}: {tag} missing {raw}")
print(f"Checked {pages} published pages and {references} local asset references.")
if failures:
    print("Missing local assets:\n" + "\n".join(failures))
    sys.exit(1)
print("Local asset audit passed. Remote image URLs are not covered.")
