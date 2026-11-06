#!/usr/bin/env python3
"""Build bilingual, attributed news ticker data from established news publishers."""
import datetime as dt, email.utils, json, pathlib, re, urllib.request, xml.etree.ElementTree as ET
from urllib.parse import urlparse
UA={"User-Agent":"DeepDocumentaryNewsTicker/1.0 (+https://deepdocumentary.com)"}
FEEDS=[
 ("ar","world","https://aawsat.com/feed/news","الشرق الأوسط","aawsat.com"),
 ("ar","economy","https://aawsat.com/feed/economy","الشرق الأوسط","aawsat.com"),
 ("ar","sports","https://aawsat.com/feed/sport","الشرق الأوسط","aawsat.com"),
 ("en","world","https://feeds.bbci.co.uk/news/world/rss.xml","BBC News","bbc.co.uk"),
 ("en","economy","https://feeds.bbci.co.uk/news/business/rss.xml","BBC News","bbc.co.uk"),
 ("en","sports","https://feeds.bbci.co.uk/sport/rss.xml","BBC Sport","bbc.co.uk"),
]
BREAKING=re.compile(r"^(عاجل|breaking)(?:\s*[:：|\-])",re.I)
def get(url):
 req=urllib.request.Request(url,headers=UA)
 with urllib.request.urlopen(req,timeout=16) as f:return ET.fromstring(f.read(1500000))
def val(node,tag):return (node.findtext(tag) or "").strip()
def parse_date(raw):
 try:return email.utils.parsedate_to_datetime(raw).astimezone(dt.timezone.utc)
 except Exception:return None
def main():
 now=dt.datetime.now(dt.timezone.utc);items=[];errors=[];seen=set()
 for lang,category,url,source,domain in FEEDS:
  try:
   root=get(url)
   for node in root.findall(".//item")[:35]:
    title=re.sub(r"\s+"," ",re.sub("<[^>]*>","",val(node,"title"))).strip()
    link=val(node,"link");date=parse_date(val(node,"pubDate"))
    if not title or not link or not date or not (now-dt.timedelta(hours=36)<=date<=now+dt.timedelta(minutes=10)):continue
    host=urlparse(link).hostname or ""
    if host!=domain and not host.endswith("."+domain):continue
    key=re.sub(r"\W+","",title.casefold())[:110]
    if key in seen:continue
    seen.add(key)
    items.append({"lang":lang,"category":category,"title":title[:220],"source":source,"publishedAt":date.isoformat(),"breaking":bool(BREAKING.match(title))})
  except Exception as e:errors.append(f"{lang}/{category}: {type(e).__name__}: {str(e)[:120]}")
 # Never fabricate headlines; retain source attribution.
 items.sort(key=lambda x:x["publishedAt"],reverse=True)
 out={"updatedAt":now.isoformat(),"items":items[:90],"errors":errors}
 dest=pathlib.Path("assets/data/news-ticker.json");dest.parent.mkdir(parents=True,exist_ok=True)
 if not items:raise SystemExit("No verified fresh headlines; keeping existing ticker data. "+repr(errors))
 dest.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("News ticker:",len(out["items"]),"errors:",errors)
if __name__=="__main__":main()
