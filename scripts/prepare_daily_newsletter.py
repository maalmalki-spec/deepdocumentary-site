#!/usr/bin/env python3
"""Prepare one bilingual daily digest; never sends email or fabricates facts."""
import datetime as dt, json, os, pathlib, re, html
from zoneinfo import ZoneInfo
ROOT=pathlib.Path(__file__).resolve().parents[1]
CAT=ROOT/"assets/documentary-catalogue.json"
STATE=ROOT/"newsletter/delivery-state.json"
OUT=ROOT/"newsletter/pending-digest.json"
TZ=ZoneInfo("Asia/Riyadh")
today=dt.datetime.now(TZ).date().isoformat()
catalog=json.loads(CAT.read_text(encoding="utf-8"))["stories"]
state=json.loads(STATE.read_text(encoding="utf-8"))
sent=set(state.get("sent_slugs",[]))
items=[s for s in catalog if s["slug"] not in sent]
def valid(s):
    return bool(s.get("slug") and s.get("ar") and s.get("en") and s.get("image"))
items=[s for s in items if valid(s)]
kind="new" if items else "archive"
if not items:
    archive=[s for s in catalog if valid(s)]
    if archive:
        used=state.get("archive_rotation",0)
        items=[archive[used % len(archive)]]
    else:
        items=[]
def clean(s):return html.escape(str(s),quote=True)
def url(s):return "https://deepdocumentary.com/articles/"+re.sub(r"[^a-z0-9-]","",s["slug"])+".html"
body=['<html><body style="background:#101014;color:#f3f0e7;font-family:Arial,sans-serif;padding:24px">','<div style="max-width:680px;margin:auto"><h1 style="color:#d5af58">Deep Documentary Daily</h1>']
body.append('<h2>أحدث المقالات | New articles</h2>' if kind=="new" else '<h2>من أرشيفنا | From our archive</h2>')
for s in items:
    body.append('<div style="border-bottom:1px solid #625535;padding:18px 0"><h3>'+clean(s["ar"])+'</h3><p>'+clean(s["en"])+'</p><a style="color:#d5af58" href="'+url(s)+'">اقرأ المقال | Read article</a></div>')
body.append('<p style="font-size:12px">Deep Documentary · <a style="color:#d5af58" href="{{ unsubscribe }}">إلغاء الاشتراك | Unsubscribe</a></p></div></body></html>')
payload={"date":today,"kind":kind,"slugs":[s["slug"] for s in items],"subject":"Deep Documentary Daily | نشرتك المعرفية اليومية","html":"".join(body)}
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("Prepared",kind,len(items),"article(s). No emails sent.")
