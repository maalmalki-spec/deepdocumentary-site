#!/usr/bin/env python3
"""Editorial release gate for new Deep Documentary articles.

Checks new article pages before publication. This is a structural gate,
not a substitute for factual, image-license or visual review.
"""
import re
import sys
from pathlib import Path
from html.parser import HTMLParser

class Article(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []
        self.captions = 0
        self.sources = 0
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "img" and "dd-footer-logo" not in a.get("class", ""):
            self.images.append(a)
        if tag == "figcaption":
            self.captions += 1
        if tag == "a" and a.get("href", "").startswith("https://") and "commons.wikimedia.org/wiki/File:" in a.get("href", ""):
            self.sources += 1

errors = []
for name in sys.argv[1:]:
    path = Path(name)
    if not path.is_file() or not str(path).startswith("articles/") or path.suffix != ".html":
        continue
    s = path.read_text(encoding="utf-8")
    doc = Article()
    doc.feed(s)
    missing = []
    if len(doc.images) < 6: missing.append(f"at least 6 editorial images (found {len(doc.images)})")
    if doc.captions < 6: missing.append("captions for at least 6 images")
    if not re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](?![^"\']*logo)', s, re.I):
        missing.append("dedicated og:image, not a logo")
    if not re.search(r'background[^;}]*url\(', s, re.I) and not re.search(r'<(?:img|picture)[^>]+class=["\'][^"\']*hero', s, re.I):
        missing.append("cover/hero image")
    if "data-ar=" not in s or "data-en=" not in s:
        missing.append("Arabic and English versions")
    if "application/ld+json" not in s: missing.append("structured metadata")
    if "canonical" not in s: missing.append("canonical URL")
    if "dd-story-explore" not in s and "documentary-series.js" not in s:
        missing.append("related articles")
    if "sources" not in s.lower() and "المصادر" not in s:
        missing.append("references")
    if missing: errors.append(f"{name}: " + "; ".join(missing))
if errors:
    print("EDITORIAL RELEASE GATE FAILED\n" + "\n".join(errors))
    sys.exit(1)
print("Editorial structural release gate passed.")
