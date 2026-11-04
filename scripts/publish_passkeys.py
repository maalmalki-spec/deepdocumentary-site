#!/usr/bin/env python3
"""Publish passkeys article only with >=5 distinct verified local Wikimedia Commons images."""
import io,json,re,html,hashlib,os,sys,time
from pathlib import Path
from urllib.parse import quote
import requests
from PIL import Image,ImageOps
ROOT=Path(__file__).resolve().parents[1]
SLUG="passkeys-end-of-passwords-2026"
OUT=ROOT/"assets"/"images"/SLUG
API="https://commons.wikimedia.org/w/api.php"
HEAD={"User-Agent":"DeepDocumentaryEditorial/1.0 (documentary educational site; contact via deepdocumentary.com)"}
SEARCHES=["passkey authentication security key","FIDO2 security key","YubiKey USB security key","fingerprint reader laptop","biometric fingerprint scanner","hardware security key authentication","WebAuthn security key"]
EXCLUDE=("logo","icon","diagram","screenshot","qr code","stock","advertisement","banner","password manager")
def api(params):
    for i in range(3):
        try:
            r=requests.get(API,params={"format":"json",**params},headers=HEAD,timeout=35)
            r.raise_for_status();return r.json()
        except (requests.RequestException,ValueError):
            if i==2: raise
            time.sleep(2*(i+1))
def allowed(info):
    e=info.get("extmetadata") or {}
    lic=html.unescape(re.sub("<[^>]*>","",e.get("LicenseShortName",{}).get("value",""))).strip()
    norm=lic.upper()
    return (norm.startswith("CC BY") and "NC" not in norm and "ND" not in norm) or norm in ("CC0","PUBLIC DOMAIN","PD","PUBLIC DOMAIN MARK")
def clean(v):
    return html.unescape(re.sub("<[^>]*>"," ",v or "")).strip()[:250]
def run():
    OUT.mkdir(parents=True,exist_ok=True)
    results=[];seen=set();hashes=set()
    for term in SEARCHES:
        if len(results)>=9: break
        data=api({"action":"query","generator":"search","gsrsearch":term+" filetype:bitmap","gsrnamespace":6,"gsrlimit":35,"prop":"imageinfo","iiprop":"url|size|extmetadata","iiurlwidth":1400})
        pages=list(data.get("query",{}).get("pages",{}).values())
        for p in pages:
            if len(results)>=9: break
            title=p.get("title","")
            if title in seen:continue
            seen.add(title)
            if any(x in title.lower() for x in EXCLUDE):continue
            ii=(p.get("imageinfo") or [{}])[0]
            if not allowed(ii) or ii.get("width",0)<700 or ii.get("height",0)<400:continue
            src=ii.get("thumburl") or ii.get("url")
            if not src:continue
            try:
                raw=requests.get(src,headers=HEAD,timeout=40);raw.raise_for_status()
                im=Image.open(io.BytesIO(raw.content))
                if im.width<650 or im.height<380:continue
                im=ImageOps.exif_transpose(im).convert("RGB")
                im.thumbnail((1500,1100))
                buf=io.BytesIO();im.save(buf,format="WEBP",quality=84,method=5)
                blob=buf.getvalue();digest=hashlib.sha256(blob).hexdigest()
                if len(blob)<14000 or digest in hashes:continue
                hashes.add(digest)
                name=f"passkeys-{len(results)+1:02d}.webp"
                (OUT/name).write_bytes(blob)
                ext=ii.get("extmetadata") or {}
                results.append({"file":name,"commons_title":title,"source":"https://commons.wikimedia.org/wiki/"+quote(title.replace(" ","_"),safe=":/()"),"creator":clean(ext.get("Artist",{}).get("value","")),"license":clean(ext.get("LicenseShortName",{}).get("value","")),"license_url":ext.get("LicenseUrl",{}).get("value",""),"description":clean(ext.get("ImageDescription",{}).get("value","")),"subject":"Illustrative photograph of digital authentication equipment; not an image of a particular 2026 event.","sha256":digest,"width":im.width,"height":im.height})
                print(name,title,flush=True)
            except (requests.RequestException,OSError,ValueError) as exc:
                print("Skip",title,str(exc)[:100],flush=True)
    (OUT/"SOURCES.json").write_text(json.dumps(results,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if len(results)<5:sys.exit(f"BLOCKED: only {len(results)} validated photos; draft remains unpublished")
    draft=(ROOT/"drafts"/(SLUG+".html")).read_text(encoding="utf-8")
    article=draft.replace('content="noindex,nofollow"','content="index,follow,max-image-preview:large"').replace(" — مسودة | Deep Documentary"," | Deep Documentary")
    article=re.sub(r'<p class="notice".*?</p>',"",article,count=1,flags=re.S)
    article=article.replace("</head>",'<link rel="canonical" href="https://deepdocumentary.com/articles/'+SLUG+'.html"></head>',1)
    css='.dd-photo{margin:34px 0;background:#15130f;border:1px solid #5a492d;border-radius:12px;overflow:hidden}.dd-photo img{display:block;width:100%;height:auto;max-height:650px;object-fit:contain}.dd-photo figcaption{font-size:12px;line-height:1.7;color:#c8b78d;padding:10px 16px}.dd-photo a{color:#e6bd6c}'
    article=article.replace("</style>",css+"</style>",1)
    figures=[]
    for i,item in enumerate(results):
        caption_ar="صورة توضيحية لمعدات وتقنيات المصادقة الرقمية"
        caption_en="Illustrative photograph of digital authentication equipment"
        title=html.escape(item["commons_title"])
        credit=html.escape(item["creator"] or "Wikimedia Commons contributor")
        url=html.escape(item["source"],quote=True)
        lic=html.escape(item["license"])
        figures.append(f'<figure class="dd-photo"><img loading="lazy" decoding="async" src="../assets/images/{SLUG}/{item["file"]}" alt="{title}" width="{item["width"]}" height="{item["height"]}"><figcaption><span data-ar="{caption_ar}" data-en="{caption_en}">{caption_ar}</span> · {credit} · <a href="{url}" target="_blank" rel="noopener noreferrer">{lic} / Wikimedia Commons</a></figcaption></figure>')
    # Place pictures through the story rather than only at the end.
    parts=article.split("<section>")
    if len(parts)<6:sys.exit("Unexpected article layout")
    for i in range(len(figures)-1,-1,-1):
        idx=1+(i%min(7,len(parts)-1))
        parts[idx]=figures[i]+parts[idx]
    article="<section>".join(parts)
    target=ROOT/"articles"/(SLUG+".html")
    target.parent.mkdir(exist_ok=True)
    target.write_text(article,encoding="utf-8")
    index=ROOT/"index.html"
    text=index.read_text(encoding="utf-8")
    if "articles/"+SLUG+".html" not in text:
        entry="{category:'technology',url:'articles/"+SLUG+".html',ar:'مفاتيح المرور: هل بدأ عصر ما بعد كلمة السر؟',en:'Passkeys: Has the Post-Password Era Begun?',summaryAr:'كيف تتغير حماية الحسابات مع مفاتيح المرور؟ تحقيق موثق في تقنية 2026.',summaryEn:'How passkeys are reshaping account security: a sourced 2026 documentary.',image:'assets/images/"+SLUG+"/"+results[0]["file"]+"'},"
        if "const samples=[" not in text:sys.exit("Homepage insertion marker missing")
        text=text.replace("const samples=[","const samples=["+entry,1)
        index.write_text(text,encoding="utf-8")
    sitemap=ROOT/"sitemap.xml"
    xml=sitemap.read_text(encoding="utf-8")
    if SLUG+".html" not in xml:
        xml=xml.replace("</urlset>","  <url><loc>https://deepdocumentary.com/articles/"+SLUG+".html</loc></url>\n</urlset>")
        sitemap.write_text(xml,encoding="utf-8")
    print("PUBLISHED",len(results),"locally archived images",flush=True)
if __name__=="__main__":run()
