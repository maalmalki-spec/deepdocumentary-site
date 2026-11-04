#!/usr/bin/env python3
"""Download, validate, optimize and locally vendor NASA Apollo 11 imagery.

Run: python scripts/vendor_apollo11_images.py
Requires: pip install requests Pillow beautifulsoup4
"""
from pathlib import Path
import io, json, re, sys
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageOps

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"assets/images/apollo-11"
GALLERY="https://www.nasa.gov/wp-content/uploads/static/history/ap11ann/kippsphotos/apollo.html"
# NASA's own gallery identifies each of these photographs.
PHOTOS=[
 ("S69-39525","launch","Saturn V lifting off, July 16, 1969"),
 ("AS11-44-6550","earthrise","Earth rising over the lunar horizon"),
 ("AS11-40-5903","aldrin","Buzz Aldrin on the lunar surface"),
 ("AS11-40-5924","lunar-module","Lunar Module ascent stage and Earth"),
 ("AS11-40-5880","footprint","Aldrin's boot and footprint in lunar soil"),
 ("S69-40023","mission-control","Mission Control celebrating after splashdown"),
]
session=requests.Session()
session.headers["User-Agent"]="DeepDocumentaryImageArchiver/1.0 (editorial archival project)"
def get(url):
    response=session.get(url,timeout=35)
    response.raise_for_status()
    return response

def resolve_from_nasa_gallery(code):
    soup=BeautifulSoup(get(GALLERY).text,"html.parser")
    # The gallery uses clickable image thumbnails linking to full-size originals.
    for node in soup.find_all(["a","img"]):
        parent=node.parent
        context=" ".join([node.get_text(" ",strip=True),node.get("alt",""),parent.get_text(" ",strip=True) if parent else ""])
        if code.lower() not in context.lower():
            continue
        anchor=node if node.name=="a" else node.find_parent("a")
        if anchor and anchor.get("href"):
            return urljoin(GALLERY,anchor["href"])
    return None

def resolve_from_nasa_api(code):
    data=get("https://images-api.nasa.gov/search").json() if False else get("https://images-api.nasa.gov/search?q="+code+"&media_type=image").json()
    items=data.get("collection",{}).get("items",[])
    for item in items:
        metadata=item.get("data",[{}])[0]
        if code.lower() not in (metadata.get("nasa_id","")+" "+metadata.get("title","")).lower():
            continue
        manifest=item.get("href")
        if manifest:
            candidates=get(manifest).json()
            for url in candidates:
                if re.search(r"\.(jpg|jpeg|png)(\?|$)",url,re.I) and ("~orig" in url or "~large" in url):
                    return url
            for url in candidates:
                if re.search(r"\.(jpg|jpeg|png)(\?|$)",url,re.I):
                    return url
    return None

OUT.mkdir(parents=True,exist_ok=True)
metadata=[]
for code,slug,description in PHOTOS:
    path=OUT/(slug+".webp")
    if path.exists() and path.stat().st_size>10000:
        print("Existing:",path)
        continue
    url=resolve_from_nasa_gallery(code) or resolve_from_nasa_api(code)
    if not url:
        raise RuntimeError("No NASA image located for "+code)
    raw=get(url).content
    try:
        image=Image.open(io.BytesIO(raw))
        image.verify()
        image=Image.open(io.BytesIO(raw))
        image=ImageOps.exif_transpose(image).convert("RGB")
    except Exception as exc:
        raise RuntimeError("Invalid image for "+code+": "+str(exc))
    if image.width<400 or image.height<300:
        raise RuntimeError("Unexpectedly small image for "+code)
    image.thumbnail((1600,1600))
    image.save(path,format="WEBP",quality=84,method=6)
    if path.stat().st_size<10000:
        raise RuntimeError("Optimized image unexpectedly small: "+str(path))
    metadata.append({"file":str(path.relative_to(ROOT)),"nasa_id":code,"description":description,"source":url,"credit":"NASA"})
    print("Saved:",path, image.size, path.stat().st_size)
(OUT/"SOURCES.json").write_text(json.dumps(metadata,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print("Archived",len(PHOTOS),"NASA photos locally.")
