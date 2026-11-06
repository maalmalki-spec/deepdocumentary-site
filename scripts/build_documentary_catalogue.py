#!/usr/bin/env python3
"""Generate documentary series catalogue from published article HTML metadata."""
from pathlib import Path
from html.parser import HTMLParser
import json, re
from urllib.parse import urlparse, unquote

ROOT=Path(__file__).resolve().parents[1]
ARTICLE_DIR=ROOT/'articles'
CATEGORIES={
'space':('space','science','astronomy','apollo','moon','mars','nasa','black hole','فضاء','قمر','ثقوب','كواكب'),
'mysteries':('mystery','chernobyl','celeste','disaster','لغز','كارثة','غموض','سفينة'),
'history':('history','archaeology','civilization','alula','khaybar','تاريخ','حضارة','آثار','العلا','خيبر'),
'technology':('technology','tutorial','canva','passkey','ai','تقنية','ذكاء','مفاتيح','فيديو')
}
class Metadata(HTMLParser):
 def __init__(self):
  super().__init__();self.meta={};self.title='';self.in_title=False;self.cover=None;self.first_image=None
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='meta':
   key=a.get('name') or a.get('property')
   if key:self.meta[key.lower()]=a.get('content','')
  if tag=='img':
   src=a.get('src','').strip()
   if src and not src.startswith(('data:','javascript:')):
    if a.get('id')=='dd-editorial-cover':self.cover=src
    elif not self.first_image and 'logo' not in src.lower() and 'icon' not in src.lower():self.first_image=src
  if tag=='title':self.in_title=True
 def handle_endtag(self,tag):
  if tag=='title':self.in_title=False
 def handle_data(self,data):
  if self.in_title:self.title+=data
def category(path,meta):
 text=' '.join([path.stem,meta.meta.get('article:section',''),meta.meta.get('keywords',''),meta.title,meta.meta.get('description','')]).lower()
 for key,words in CATEGORIES.items():
  if any(re.search(r'(?<![a-z])'+re.escape(w)+r'(?![a-z])',text) for w in words):return key
 return 'general'
def normalize_image(src, path):
 if not src:return None
 src=src.strip()
 parsed=urlparse(src)
 if parsed.scheme in ('http','https'):
  if parsed.netloc.lower() not in ('deepdocumentary.com','www.deepdocumentary.com'):return src
  src=unquote(parsed.path)
 else:
  src=unquote(parsed.path)
 # Relative URLs inside articles resolve relative to the article itself.
 if src.startswith('/'):candidate=ROOT/src.lstrip('/')
 elif src.startswith(('assets/','articles/')):candidate=ROOT/src
 else:candidate=path.parent/src
 try:
  resolved=candidate.resolve()
  resolved.relative_to(ROOT.resolve())
  if resolved.is_file():return resolved.relative_to(ROOT).as_posix()
 except (ValueError,OSError):pass
 return None

def extract(path):
 content=path.read_text(encoding='utf-8')
 if re.search(r'<meta[^>]+name=["\']robots["\'][^>]+content=["\'][^"\']*noindex',content,re.I):return None
 m=Metadata();m.feed(content)
 title=re.sub(r'\s*\|\s*Deep Documentary.*$','',m.title,flags=re.I).strip()
 if not title:return None
 en=m.meta.get('og:title','').strip() or title
 ar=title
 # Prefer explicitly authored bilingual metadata when available.
 ar=m.meta.get('dd:title:ar',ar)
 en=m.meta.get('dd:title:en',en)
 if not ar or not en:return None
 image=next((v for v in (normalize_image(m.cover,path),normalize_image(m.first_image,path),normalize_image(m.meta.get('og:image'),path)) if v),None)
 item=dict(slug=path.stem,series=m.meta.get('dd:series') or category(path,m),ar=ar,en=en,image=image)
 year=m.meta.get('dd:event-year','').strip()
 if year.lstrip('-').isdigit() and -5000 <= int(year) <= 2100: item['eventYear']=int(year)
 era=m.meta.get('dd:event-era','').strip()
 if era in ('ancient','medieval','modern','space'): item['era']=era
 if m.meta.get('dd:event-approximate')=='true': item['approximateYear']=True
 return item
# Covers are derived from article HTML; curated event years are preserved.
previous={}
out=ROOT/'assets/documentary-catalogue.json'
if out.exists():
 try: previous={x['slug']:x for x in json.loads(out.read_text(encoding='utf-8')).get('stories',[])}
 except (ValueError,KeyError,TypeError): pass
stories=[]
for path in sorted(ARTICLE_DIR.glob('*.html')):
 item=extract(path)
 if item:
  existing=previous.get(item['slug'],{})
  # The published article is the single source of truth for its cover.
  # Never let an old manually edited catalogue entry override it.
  # Preserve curated event chronology across automatic catalogue rebuilds.
  for field in ('eventYear','era','approximateYear'):
   if field not in item and field in existing:item[field]=existing[field]
  stories.append(item)
out=ROOT/'assets/documentary-catalogue.json'
out.write_text(json.dumps({'stories':stories},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Generated',len(stories),'articles:',out)
