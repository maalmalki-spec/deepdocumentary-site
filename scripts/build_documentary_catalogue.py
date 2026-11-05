#!/usr/bin/env python3
"""Generate documentary series catalogue from published article HTML metadata."""
from pathlib import Path
from html.parser import HTMLParser
import json, re

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
  super().__init__();self.meta={};self.title='';self.in_title=False
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='meta':
   key=a.get('name') or a.get('property')
   if key:self.meta[key.lower()]=a.get('content','')
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
 return dict(slug=path.stem,series=m.meta.get('dd:series') or category(path,m),ar=ar,en=en,image=None)
stories=[]
for path in sorted(ARTICLE_DIR.glob('*.html')):
 item=extract(path)
 if item:stories.append(item)
out=ROOT/'assets/documentary-catalogue.json'
out.write_text(json.dumps({'stories':stories},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Generated',len(stories),'articles:',out)
