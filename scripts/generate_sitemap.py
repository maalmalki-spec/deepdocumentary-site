from pathlib import Path
from xml.etree import ElementTree as ET

root = Path(__file__).resolve().parent.parent
base = 'https://deepdocumentary.com/'
namespace = 'http://www.sitemaps.org/schemas/sitemap/0.9'
ET.register_namespace('', namespace)
urlset = ET.Element(f'{{{namespace}}}urlset')
paths = ['index.html', 'about.html', 'games.html', 'contact.html', 'privacy.html', 'terms.html']
paths += sorted(p.relative_to(root).as_posix() for p in (root / 'articles').glob('*.html'))
for relative in paths:
    if not (root / relative).is_file():
        continue
    entry = ET.SubElement(urlset, f'{{{namespace}}}url')
    ET.SubElement(entry, f'{{{namespace}}}loc').text = base if relative == 'index.html' else base + relative
ET.indent(urlset, space='  ')
(root / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(urlset, encoding='unicode') + '\n', encoding='utf-8')
