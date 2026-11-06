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
        self.ar_text = []
        self.en_text = []
        self.language_stack = []
        self.skip_depth = 0
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.language_stack.append(a.get('lang', self.language_stack[-1] if self.language_stack else ''))
        if tag in ('script', 'style'): self.skip_depth += 1
        if a.get('data-ar'): self.ar_text.append(a['data-ar'])
        if a.get('data-en'): self.en_text.append(a['data-en'])
        if tag == "img" and "dd-footer-logo" not in a.get("class", ""):
            self.images.append(a)
        if tag == "figcaption":
            self.captions += 1
        if tag == "a" and a.get("href", "").startswith("https://") and "commons.wikimedia.org/wiki/File:" in a.get("href", ""):
            self.sources += 1

    def handle_endtag(self, tag):
        if tag in ('script', 'style'): self.skip_depth = max(0, self.skip_depth - 1)
        if self.language_stack: self.language_stack.pop()
    def handle_data(self, data):
        if self.skip_depth: return
        lang = self.language_stack[-1] if self.language_stack else ''
        if lang.startswith('ar'): self.ar_text.append(data)
        elif lang.startswith('en'): self.en_text.append(data)

errors = []
for name in sys.argv[1:]:
    path = Path(name)
    if not path.is_file() or not str(path).startswith("articles/") or path.suffix != ".html":
        continue
    s = path.read_text(encoding="utf-8")
    doc = Article()
    doc.feed(s)
    missing = []
    # Count editorial assets, not decorative footer images.
    if len(doc.images) < 6: missing.append(f"at least 6 editorial images (found {len(doc.images)})")
    for img in doc.images:
        src = img.get("src", "").strip()
        if not src or src.startswith(("http://", "https://", "//", "data:")):
            missing.append("editorial image must be a local file: " + src[:100])
        elif not (path.parent / src.split("?")[0]).is_file() and not (Path(src.lstrip("/"))).is_file():
            missing.append("editorial image file not found: " + src[:100])
        if not img.get("alt", "").strip():
            missing.append("editorial image missing alt text")
    if doc.captions < 6: missing.append("captions for at least 6 images")
    if not re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](?![^"\']*logo)', s, re.I):
        missing.append("dedicated og:image, not a logo")
    if not re.search(r'background[^;}]*url\(', s, re.I) and not re.search(r'<(?:img|picture)[^>]+class=["\'][^"\']*hero', s, re.I):
        missing.append("cover/hero image")
    # Both translations must contain substantial visible prose, not only UI labels.
    ar = re.findall(r'[\u0600-\u06FF]+', ' '.join(doc.ar_text))
    en = re.findall(r'\b[A-Za-z]{2,}\b', ' '.join(doc.en_text))
    if len(ar) < 1500: missing.append(f"Arabic content below 1500 words ({len(ar)})")
    if len(en) < 1500: missing.append(f"English content below 1500 words ({len(en)})")
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
