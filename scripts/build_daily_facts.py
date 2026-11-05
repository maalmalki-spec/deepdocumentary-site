#!/usr/bin/env python3
"""Build daily facts from article metadata. Never invent or infer a source."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlparse
import json
ROOT=Path(__file__).resolve().parents[1]
class Meta(HTMLParser):
 def __init__(self):super().__init__();self.data={}
 def handle_starttag(self,tag,attrs):
  if tag!='meta':return
  a=dict(attrs);key=a.get('name') or a.get('property')
  if key:self.data[key.lower()]=a.get('content','').strip()
def valid_url(url):
 p=urlparse(url)
 return p.scheme=='https' and bool(p.netloc) and p.netloc.lower() not in ('deepdocumentary.com','www.deepdocumentary.com')
out=[]
seen=set()
for path in sorted((ROOT/'articles').glob('*.html')):
 m=Meta();m.feed(path.read_text(encoding='utf-8'))
 d=m.data
 if 'noindex' in d.get('robots','').lower():continue
 ar=d.get('dd:fact:ar','');en=d.get('dd:fact:en','')
 url=d.get('dd:fact:source:url','');source=d.get('dd:fact:source:name','')
 if not all((ar,en,url,source)) or not valid_url(url):continue
 key=(ar.strip(),url)
 if key in seen:continue
 seen.add(key)
 out.append({'ar':ar,'en':en,'article':path.stem,'source':source,'url':url})
target=ROOT/'assets/daily-facts-generated.json'
target.write_text(json.dumps({'facts':out},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Generated',len(out),'sourced daily facts from article metadata')
