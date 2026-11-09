"""Regenerate the sitemap from published static pages and article files."""
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://deepdocumentary.com/"
NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
ET.register_namespace("", NS)
STATIC = ("index.html", "about.html", "games.html", "contact.html", "privacy.html", "terms.html")
ARTICLES = ROOT / "articles"

def published(path):
    if not path.is_file():
        return False
    # Draft files never belong in the public sitemap.
    if path.name.startswith("_") or path.name.endswith(".draft.html"):
        return False
    content = path.read_text(encoding="utf-8", errors="replace").lower()
    return '<meta name="robots" content="noindex' not in content and '<meta content="noindex' not in content

def build():
    paths = [ROOT / p for p in STATIC]
    if ARTICLES.exists():
        paths += sorted(ARTICLES.glob("*.html"))
    urlset = ET.Element(f"{{{NS}}}urlset")
    for path in paths:
        if not published(path):
            continue
        relative = path.relative_to(ROOT).as_posix()
        entry = ET.SubElement(urlset, f"{{{NS}}}url")
        loc = BASE if relative == "index.html" else BASE + quote(relative, safe="/-._~")
        ET.SubElement(entry, f"{{{NS}}}loc").text = loc
        # File mtime is deliberately omitted: checkout timestamps are not publication dates.
    ET.indent(urlset, space="  ")
    result = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(urlset, encoding="unicode") + "\n"
    output = ROOT / "sitemap.xml"
    if not output.exists() or output.read_text(encoding="utf-8") != result:
        output.write_text(result, encoding="utf-8")
    return len(urlset)

if __name__ == "__main__":
    print(f"Sitemap entries: {build()}")
