#!/usr/bin/env python3
"""Archive licensed Commons photographs; publish AlUla/Khaybar only after validation."""
import json, re, shutil, hashlib, html, time
from pathlib import Path
from urllib.parse import urlencode
import requests
from PIL import Image
from io import BytesIO
from install_analytics import add_analytics

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'assets/images/alula-khaybar-archaeology'
DEST.mkdir(parents=True,exist_ok=True)
FILES=[
 ('alula-landscape','Landscape at al-Ula, Saudi Arabia (1).jpg','مناظر طبيعية من العُلا','Landscape in AlUla'),
 ('dadan-ruins','Ancient site of Dadan at al-Ula, 1st millenium BCE, Saudi Arabia 13.jpg','آثار دادان في العُلا','Archaeological remains at Dadan'),
 ('dadan-lion','Lion Tomb Site, Al Ula - panoramio.jpg','موقع مقابر الأسود في دادان','Lion Tomb site at Dadan'),
 ('khaybar-fortress','Khaybar - fortress Qamus (1).jpg','قلعة القموص في خيبر؛ موقع تاريخي وليس بلدة النطاة البرونزية','Qamus fortress at Khaybar; not the Bronze Age al-Natah settlement'),
 ('khaybar-valley','Panorama - Khaybar valley with two jewish fortresses.jpg','مشهد عام لوادي خيبر وحصونه','Khaybar valley and fortresses'),
 ('hegra-inscriptions','Ancient inscriptions at Jabal Ithlib, Hegra (MAdain Salih), Saudi Arabia.jpg','نقوش قديمة في جبل إثلب بالحِجر','Ancient inscriptions at Jabal Ithlib, Hegra'),
 ('alula-rock-art','Rock art site at al-Ula, Saudi Arabia.jpg','رسوم صخرية في العُلا','Rock art in AlUla'),
 ('alula-oasis','Al-\'Ula oasis (1).jpg','واحة العُلا','AlUla oasis'),
 ('khaybar-houses','Khaybar - deserted houses.jpg','منازل خيبر المهجورة؛ ليست دليلًا مباشرًا على العصر البرونزي','Deserted Khaybar houses; not direct Bronze Age evidence'),
]
session=requests.Session()
session.headers.update({'User-Agent':'DeepDocumentaryEditorial/1.0 (photo provenance; contact via deepdocumentary.com)'})
results=[]
for stem,name,ar,en in FILES:
 try:
  api='https://commons.wikimedia.org/w/api.php'
  params={'action':'query','format':'json','titles':'File:'+name,'prop':'imageinfo','iiprop':'url|extmetadata|size','iiurlwidth':'1200'}
  response=session.get(api,params=params,timeout=35);response.raise_for_status()
  page=next(iter(response.json()['query']['pages'].values()))
  info=page['imageinfo'][0]
  meta=info.get('extmetadata',{})
  license_code=html.unescape(re.sub('<[^>]+>','',meta.get('LicenseShortName',{}).get('value',''))).strip()
  license_url=meta.get('LicenseUrl',{}).get('value','')
  if not (license_code.startswith(('CC BY','CC0')) or 'Public domain' in license_code or license_code=='PD'):
   print('SKIP license',name,license_code);continue
  if 'NC' in license_code or 'ND' in license_code:continue
  src=info.get('thumburl') or info['url']
  raw=session.get(src,timeout=65);raw.raise_for_status()
  im=Image.open(BytesIO(raw.content));im.load()
  if im.width<600 or im.height<350:raise ValueError('insufficient dimensions')
  out=DEST/(stem+'.webp')
  im.convert('RGB').save(out,'WEBP',quality=84,method=5)
  check=Image.open(out);check.verify()
  if out.stat().st_size<15000:raise ValueError('suspiciously small')
  results.append({'file':out.name,'title':name,'source':'https://commons.wikimedia.org/wiki/File:'+name.replace(' ','_'),'creator':meta.get('Artist',{}).get('value',''),'license':license_code,'license_url':license_url,'credit':meta.get('Credit',{}).get('value',''),'caption_ar':ar,'caption_en':en,'width':im.width,'height':im.height,'sha256':hashlib.sha256(out.read_bytes()).hexdigest()})
  print('OK',out.name,license_code,im.size)
 except Exception as e:print('FAILED',name,repr(e))
 time.sleep(.4)
(DEST/'SOURCES.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
if len(results)<5:
 raise SystemExit('Publication blocked: fewer than five licensed verified images: '+str(len(results)))
draft=ROOT/'drafts/alula-khaybar-archaeology.html'
article=ROOT/'articles/alula-khaybar-archaeology.html'
s=draft.read_text(encoding='utf-8')
s=re.sub(r'<p class="notice"[\s\S]*?</p>','',s,count=1)
s=s.replace('<meta name="robots" content="noindex,nofollow">','<meta name="robots" content="index,follow,max-image-preview:large"><link rel="canonical" href="https://deepdocumentary.com/articles/alula-khaybar-archaeology.html">')
s=s.replace('— مسودة | Deep Documentary','| Deep Documentary')
gallery=[(0,0),(2,1),(3,2),(4,3),(6,4),(7,5),(8,6),(9,7),(10,8)]
sections=list(re.finditer(r'<section>',s))
for section_idx,img_idx in reversed(gallery):
 if section_idx>=len(sections) or img_idx>=len(results):continue
 item=results[img_idx]
 caption=html.escape(item['caption_ar'],quote=True)
 en=html.escape(item['caption_en'],quote=True)
 url=html.escape(item['source'],quote=True)
 figure=f'<figure style="margin:30px 0"><img loading="lazy" decoding="async" src="../assets/images/alula-khaybar-archaeology/{item["file"]}" alt="{caption}" style="display:block;width:100%;height:auto;max-height:550px;object-fit:cover;border-radius:12px"><figcaption style="color:#bfa875;font-size:12px;line-height:1.7" data-ar="{caption}" data-en="{en}">{caption}</figcaption><small><a href="{url}" rel="noopener noreferrer">Wikimedia Commons · {html.escape(item["license"])}</a></small></figure>'
 at=sections[section_idx].start()
 s=s[:at]+figure+s[at:]
article.write_bytes(add_analytics(s.encode("utf-8")))
home=ROOT/'index.html'
h=home.read_text(encoding='utf-8')
if "articles/alula-khaybar-archaeology.html" not in h:
 row="{category:'history',url:'articles/alula-khaybar-archaeology.html',ar:'أسرار العُلا وخيبر: حضارات عمرها آلاف السنين',en:'AlUla and Khaybar: Ancient Civilizations Revealing Their Secrets',summaryAr:'من مستطيلات ما قبل التاريخ إلى أسوار خيبر وممالك دادان: رحلة أثرية موثقة.',summaryEn:'From prehistoric stone monuments to Khaybar’s fortifications and Dadan’s kingdoms: an evidence-led journey.',image:'assets/images/alula-khaybar-archaeology/"+results[0]['file']+"'},\n"
 h=h.replace('const samples=[','const samples=[\n'+row,1)
 home.write_text(h,encoding='utf-8')
sitemap=ROOT/'sitemap.xml'
m=sitemap.read_text(encoding='utf-8')
if 'articles/alula-khaybar-archaeology.html' not in m:
 m=m.replace('</urlset>','  <url><loc>https://deepdocumentary.com/articles/alula-khaybar-archaeology.html</loc><changefreq>monthly</changefreq><priority>0.9</priority></url>\n</urlset>')
 sitemap.write_text(m,encoding='utf-8')
print('PUBLISHED after verified image gate:',len(results))
