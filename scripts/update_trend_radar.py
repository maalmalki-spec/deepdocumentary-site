#!/usr/bin/env python3
"""Build a sourced, cross-category editorial radar; no invented trend scores."""
import json, urllib.request, urllib.parse, xml.etree.ElementTree as ET, datetime, pathlib, re, email.utils
CATEGORIES={
"world":("العالم","World","world news latest"),
"history":("التاريخ والآثار","History & archaeology","archaeology discovery history"),
"science":("العلوم والصحة","Science & health","science medical discovery"),
"technology":("التقنية والذكاء الاصطناعي","Technology & AI","artificial intelligence technology"),
"economy":("الاقتصاد والأعمال","Economy & business","economy business"),
"environment":("الطبيعة والبيئة","Nature & environment","climate nature environment"),
"society":("الإنسان والمجتمع","Society","psychology society research"),
"culture":("الثقافة والفنون","Culture & arts","culture arts documentary"),
"mystery":("الغموض والتحقيقات","Mystery & investigations","historical mystery investigation"),
"space":("الفضاء","Space","space astronomy discovery")}
HEADERS={"User-Agent":"DeepDocumentaryEditorialRadar/1.0 (+https://deepdocumentary.com)"}
def fetch(query):
    url="https://news.google.com/rss/search?"+urllib.parse.urlencode({"q":query+" when:2d","hl":"en-US","gl":"US","ceid":"US:en"})
    req=urllib.request.Request(url,headers=HEADERS)
    with urllib.request.urlopen(req,timeout=18) as response:
        return ET.fromstring(response.read(800000))
def clean(s): return re.sub(r"\s+"," ",s or "").strip()
GENERIC = ("breaking headlines", "breaking news", "latest news", "news today", "top stories", "video reports", "watch live", "local angles", "news homepage", "news website")
def valid(title, publisher, date, now):
    if not 25 <= len(title) <= 190 or len(title.split()) < 5: return False
    if any(word in title.casefold() for word in GENERIC): return False
    if title.casefold().strip(" .-") == publisher.casefold().strip(" .-"): return False
    try:
        published = email.utils.parsedate_to_datetime(date)
        if published.tzinfo is None: published = published.replace(tzinfo=datetime.timezone.utc)
        age = (now-published.astimezone(datetime.timezone.utc)).total_seconds()
        return -3600 <= age <= 72*3600
    except (ValueError, TypeError, OverflowError): return False
def main():
    items=[];errors=[];seen=set();now=datetime.datetime.now(datetime.timezone.utc)
    for key,(ar,en,query) in CATEGORIES.items():
        try:
            root=fetch(query)
            count=0
            for node in root.findall(".//channel/item"):
                title=clean(node.findtext("title"))
                link=clean(node.findtext("link"))
                source=node.find("source")
                publisher=clean(source.text if source is not None else "")
                date=clean(node.findtext("pubDate"))
                if not title or not link or not publisher:continue
                if " - " in title and title.rsplit(" - ",1)[-1].casefold() == publisher.casefold():
                    title=title.rsplit(" - ",1)[0].strip()
                if not valid(title,publisher,date,now):continue
                signature=re.sub("[^a-z0-9]+","",title.casefold())
                if signature in seen:continue
                seen.add(signature)
                items.append({"category":key,"categoryAr":ar,"categoryEn":en,"title":title,"source":publisher,"url":link,"published":date,"suggestedTitleEn":"Behind the story: "+title,"suggestedTitleAr":"خلف الخبر: "+title})
                count+=1
                if count>=2:break
        except Exception as exc:errors.append(key+": "+str(exc)[:140])
    output={"updatedAt":now.isoformat(),"method":"Google News RSS editorial discovery; two recent headlines per category. Not search-volume rankings. Titles are unverified suggestions; verify original sources before publishing.","items":items[:20],"errors":errors}
    dest=pathlib.Path("assets/data/trend-radar.json");dest.parent.mkdir(parents=True,exist_ok=True)
    if len(items)<10:raise SystemExit("Insufficient valid headlines; preserving prior radar data")
    dest.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Radar items:",len(items),"errors:",len(errors))
    if not items:raise SystemExit("No feed items; keeping existing radar data via failed workflow")
if __name__=="__main__":main()
