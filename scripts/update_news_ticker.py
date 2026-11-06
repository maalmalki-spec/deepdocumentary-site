#!/usr/bin/env python3
"""Collect recent bilingual headlines from named publishers via Google News RSS."""
import datetime as dt
import email.utils
import json
import pathlib
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

HEADERS={"User-Agent":"Mozilla/5.0 (compatible; DeepDocumentaryNews/1.0)"}
# Google News RSS provides publisher attribution and avoids scraping publishers.
SEARCHES=[
 ("ar","saudi","السعودية when:1d"),
 ("ar","gulf","الخليج الإمارات الكويت قطر البحرين عمان when:1d"),
 ("ar","world","أخبار العالم سياسة عاجل when:1d"),
 ("ar","economy","اقتصاد أسواق نفط when:1d"),
 ("ar","sports","كرة القدم رياضة when:1d"),
 ("en","saudi","Saudi Arabia when:1d"),
 ("en","world","world news politics when:1d"),
 ("en","economy","economy business markets when:1d"),
 ("en","sports","sports football when:1d"),
 ("en","science","science technology when:1d"),
]
# Explicit source allowlist, not a Saudi-specific restriction.
TRUSTED_AR=("العربية","الإخبارية","الشرق الأوسط","سكاي نيوز عربية","فرانس 24","بي بي سي عربي","الجزيرة نت","رويترز","وكالة الأنباء السعودية","واس")
TRUSTED_EN=("Reuters","BBC","Associated Press","AP News","France 24","Al Arabiya English","Arab News","Bloomberg","CNBC","Sky News","The Guardian","Al Jazeera English")
BREAKING=re.compile(r"^(?:عاجل|breaking)(?:\s*[:：|\-])",re.I)
def fetch(lang,query):
 params={"q":query,"hl":"ar","gl":"SA","ceid":"SA:ar"} if lang=="ar" else {"q":query,"hl":"en-US","gl":"US","ceid":"US:en"}
 url="https://news.google.com/rss/search?"+urllib.parse.urlencode(params)
 request=urllib.request.Request(url,headers=HEADERS)
 with urllib.request.urlopen(request,timeout=22) as response:
  return ET.fromstring(response.read(2_000_000))
def date_of(s):
 try:return email.utils.parsedate_to_datetime(s).astimezone(dt.timezone.utc)
 except (TypeError,ValueError,OverflowError):return None
def main():
 now=dt.datetime.now(dt.timezone.utc);items=[];errors=[];seen=set()
 for lang,category,query in SEARCHES:
  try:
   root=fetch(lang,query)
   for node in root.findall("./channel/item")[:45]:
    title=re.sub(r"\s+"," ",node.findtext("title","")).strip()
    source=re.sub(r"\s+"," ",node.findtext("source","")).strip()
    published=date_of(node.findtext("pubDate",""))
    allowed=TRUSTED_AR if lang=="ar" else TRUSTED_EN
    if not title or not source or not published:continue
    if not any(source.casefold()==name.casefold() for name in allowed):continue
    if published<now-dt.timedelta(hours=36) or published>now+dt.timedelta(minutes=10):continue
    suffix=" - "+source
    if title.endswith(suffix):title=title[:-len(suffix)]
    key=re.sub(r"\W+","",title.casefold())[:130]
    if key in seen:continue
    seen.add(key)
    items.append({"lang":lang,"category":category,"title":title[:220],"source":source,"publishedAt":published.isoformat(),"breaking":bool(BREAKING.match(title))})
  except Exception as exc:
   errors.append(f"{lang}/{category}: {type(exc).__name__}: {str(exc)[:140]}")
 items.sort(key=lambda x:x["publishedAt"],reverse=True)
 if not items:raise SystemExit("No fresh trusted-source headlines; preserving previous data: "+repr(errors))
 dest=pathlib.Path("assets/data/news-ticker.json")
 dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_text(json.dumps({"updatedAt":now.isoformat(),"items":items[:150],"errors":errors},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("Saved",len(items),"trusted headlines;",len(errors),"feed errors")
if __name__=="__main__":main()
