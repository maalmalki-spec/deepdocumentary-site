"""Normalize SEO metadata for existing and newly published article HTML files."""
from pathlib import Path
import html
import json
import re

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://deepdocumentary.com/"
SITE = "Deep Documentary"

def tag(content, pattern):
    found = re.search(pattern, content, re.I | re.S)
    return html.unescape(found.group(1).strip()) if found else ""

def add(content, markup):
    return re.sub(r"</head\s*>", markup + "</head>", content, count=1, flags=re.I)

def process(path):
    content = path.read_text(encoding="utf-8")
    if not re.search(r"</head\s*>", content, re.I):
        return False
    relative = path.relative_to(ROOT).as_posix()
    canonical = BASE + relative
    title = tag(content, r"<title[^>]*>(.*?)</title>") or path.stem.replace("-", " ")
    description = tag(content, r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']+)') or ""
    if not description:
        return False
    image = tag(content, r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)')
    if not image:
        image = tag(content, r'<img[^>]*\bsrc=["\']([^"\']+)')
    if image and not image.startswith(("https://", "http://")):
        image = BASE + str((Path(relative).parent / image).as_posix()).replace("../", "")
    changes = []
    if not re.search(r'<link\s+rel=["\']canonical["\']', content, re.I):
        changes.append(f'<link rel="canonical" href="{html.escape(canonical, quote=True)}">')
    meta = {
        "og:type": "article", "og:site_name": SITE,
        "og:title": title, "og:description": description,
        "og:url": canonical,
    }
    if image:
        meta["og:image"] = image
    for key, value in meta.items():
        if not re.search(r'<meta\s+property=["\']' + re.escape(key) + r'["\']', content, re.I):
            changes.append(f'<meta property="{key}" content="{html.escape(value, quote=True)}">')
    if not re.search(r'<meta\s+name=["\']twitter:card["\']', content, re.I):
        changes.append('<meta name="twitter:card" content="summary_large_image">')
    if not re.search(r'<script[^>]*type=["\']application/ld\+json["\']', content, re.I):
        schema = {"@context": "https://schema.org", "@type": "Article",
                  "headline": title, "description": description,
                  "mainEntityOfPage": canonical, "url": canonical,
                  "publisher": {"@type": "Organization", "name": SITE, "url": BASE}}
        if image:
            schema["image"] = image
        changes.append('<script type="application/ld+json">' + json.dumps(schema, ensure_ascii=False).replace("</", "<\\/") + '</script>')
    if not changes:
        return False
    updated = add(content, "".join(changes))
    path.write_text(updated, encoding="utf-8")
    return True

if __name__ == "__main__":
    changed = [p.name for p in sorted((ROOT / "articles").glob("*.html")) if process(p)]
    print(f"SEO metadata updated in {len(changed)} articles")
