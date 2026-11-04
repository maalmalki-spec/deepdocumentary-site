#!/usr/bin/env python3
"""Audit external article imagery; archive eligible verified sources to local WebP.

Runs in CI. Never silently substitutes another photo. Sources without confirmed
redistribution permission are reported for editorial review, not copied.
"""
from pathlib import Path
from urllib.parse import urlparse, unquote
from collections import Counter
import hashlib, io, json, re
import requests
from PIL import Image, ImageOps

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/"assets/images"
REPORT=ROOT/"assets/image-audit.json"
HTML=list((ROOT/"articles").glob("*.html"))+[ROOT/"index.html"]
SRC=re.compile(r'(?P<prefix>\b(?:src|image):?\s*=\s*["\']|\bimage:\s*["\'])(?P<url>https?[^"\']+)',re.I)
# Only these official government/archival sources are eligible for unattended copying.
NASA_HOSTS={"images-assets.nasa.gov","www.nasa.gov","science.nasa.gov","assets.science.nasa.gov"}
s=requests.Session();s.headers["User-Agent"]="DeepDocumentary/1.0 image preservation editorial site"
audit=[]
for file in HTML:
    content=file.read_text(encoding="utf-8")
    found=list(SRC.finditer(content))
    replacements={}
    for match in found:
        url=match.group("url").replace("&amp;","&")
        host=(urlparse(url).hostname or "").lower()
        if host not in NASA_HOSTS:
            audit.append({"page":str(file.relative_to(ROOT)),"url":url,"status":"manual_review_required","reason":"Source license and identity must be verified before archiving"})
            continue
        key=hashlib.sha256(url.encode()).hexdigest()[:12]
        slug=file.stem
        target=ASSETS/slug/(key+".webp")
        try:
            if not target.exists():
                response=s.get(url,timeout=25)
                response.raise_for_status()
                image=Image.open(io.BytesIO(response.content))
                image.verify()
                image=Image.open(io.BytesIO(response.content))
                image=ImageOps.exif_transpose(image).convert("RGB")
                if image.width<400 or image.height<250:
                    raise ValueError("Image too small")
                image.thumbnail((1600,1600))
                target.parent.mkdir(parents=True,exist_ok=True)
                image.save(target,"WEBP",quality=84,method=6)
            if target.stat().st_size<10000:raise ValueError("File unexpectedly small")
            local=("../" if file.parent.name=="articles" else "")+str(target.relative_to(ROOT))
            replacements[match.group("url")]=local
            audit.append({"page":str(file.relative_to(ROOT)),"url":url,"local":str(target.relative_to(ROOT)),"status":"archived","credit":"NASA"})
        except Exception as exc:
            audit.append({"page":str(file.relative_to(ROOT)),"url":url,"status":"download_failed","error":str(exc)[:180]})
    for old,new in replacements.items():
        content=content.replace(old,new)
    if replacements:file.write_text(content,encoding="utf-8")
ASSETS.mkdir(parents=True,exist_ok=True)
REPORT.write_text(json.dumps(audit,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("Audit:",dict(Counter(item["status"] for item in audit)))
