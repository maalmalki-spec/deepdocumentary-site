#!/usr/bin/env python3
"""Keep documentary-series assets installed on every published HTML page.

Runs in CI on each site change; idempotent and safe for future articles.
"""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
CSS='documentary-series.css'
JS='documentary-series.js'
changed=[]
for path in [ROOT/'index.html',*sorted((ROOT/'articles').glob('*.html'))]:
    if not path.is_file():continue
    text=path.read_text(encoding='utf-8')
    if '<html' not in text.lower() or '</body>' not in text.lower():continue
    prefix='../' if path.parent.name=='articles' else ''
    # Replace old asset tags instead of stacking multiple copies.
    text=re.sub(r'<link[^>]*documentary-series[.]css[^>]*>', '', text, flags=re.I)
    text=re.sub(r'<script[^>]*documentary-series[.]js[^>]*>.*?</script>', '', text, flags=re.I|re.S)
    if path.name=='index.html' and 'id="documentary-series"' not in text:
        target='<section class="wrap" id="articles">'
        if target in text:text=text.replace(target,'<section id="documentary-series" aria-label="Documentary series"></section>'+target,1)
    text=text.replace('</head>',f'<link rel="stylesheet" href="{prefix}assets/{CSS}"></head>',1)
    text=text.replace('</body>',f'<script defer src="{prefix}assets/{JS}"></script></body>',1)
    old=path.read_text(encoding='utf-8')
    if text!=old:
        path.write_text(text,encoding='utf-8')
        changed.append(str(path.relative_to(ROOT)))
print('Updated',len(changed),'HTML files:',', '.join(changed))
