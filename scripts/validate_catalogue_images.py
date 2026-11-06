#!/usr/bin/env python3
"""Fail CI when published catalogue cover paths are invalid or out of sync."""
import json
import sys
from pathlib import Path
from urllib.parse import urlparse
from build_documentary_catalogue import ARTICLE_DIR, ROOT, extract

catalogue=json.loads((ROOT/'assets/documentary-catalogue.json').read_text(encoding='utf-8'))
errors=[]
for item in catalogue.get('stories',[]):
 slug=item.get('slug','')
 article=ARTICLE_DIR/(slug+'.html')
 if not article.is_file():
  errors.append(f'{slug}: missing article')
  continue
 expected=extract(article)
 if not expected:
  errors.append(f'{slug}: article excluded from catalogue')
  continue
 image=item.get('image')
 if image!=expected.get('image'):
  errors.append(f'{slug}: catalogue cover differs from article cover ({image!r} vs {expected.get("image")!r})')
 if image:
  parsed=urlparse(image)
  if parsed.scheme in ('http','https'):
   if parsed.scheme!='https':errors.append(f'{slug}: insecure image URL')
  elif parsed.scheme or image.startswith('//'):
   errors.append(f'{slug}: unsupported image URL')
  else:
   file=ROOT/image.lstrip('/')
   if not file.is_file():errors.append(f'{slug}: missing local image {image}')
for error in errors:print('ERROR:',error,file=sys.stderr)
print(f'Validated {len(catalogue.get("stories",[]))} catalogue covers; {len(errors)} error(s)')
sys.exit(1 if errors else 0)
