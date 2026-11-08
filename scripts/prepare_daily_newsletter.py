#!/usr/bin/env python3
"""Prepare one bilingual daily digest; never sends email or fabricates facts."""
import datetime as dt, json, os, pathlib, re, html, hashlib
from zoneinfo import ZoneInfo
ROOT=pathlib.Path(__file__).resolve().parents[1]
CAT=ROOT/"assets/documentary-catalogue.json"
STATE=ROOT/"newsletter/delivery-state.json"
OUT=ROOT/"newsletter/pending-digest.json"
TZ=ZoneInfo("Asia/Riyadh")
today=dt.datetime.now(TZ).date().isoformat()
catalog=json.loads(CAT.read_text(encoding="utf-8"))["stories"]
state=json.loads(STATE.read_text(encoding="utf-8"))
def valid(s):
    return bool(s.get("slug") and s.get("ar") and s.get("en") and s.get("image") and not re.search("[\\u0600-\\u06ff]", str(s["en"])))
catalog=[s for s in catalog if valid(s)]
import subprocess
try:
    added=subprocess.check_output(["git","log","--since=24 hours ago","--diff-filter=A","--name-only","--pretty=format:","--","articles/"],cwd=ROOT,text=True,timeout=15)
    new_slugs={pathlib.Path(p).stem for p in added.splitlines() if p.strip().endswith(".html")}
except (subprocess.SubprocessError,OSError):
    new_slugs=set()
new_items=sorted([s for s in catalog if s["slug"] in new_slugs],key=lambda s:hashlib.sha256((today+":new:"+s["slug"]).encode()).hexdigest())[:2]
remaining=[s for s in catalog if s["slug"] not in {x["slug"] for x in new_items}]
remaining=sorted(remaining,key=lambda s:hashlib.sha256((today+":archive:"+s["slug"]).encode()).hexdigest())
archive_items=remaining[:max(0,4-len(new_items))]
items=new_items+archive_items
kind="new" if new_items else "archive"
def clean(s):return html.escape(str(s),quote=True)
def url(s):return "https://deepdocumentary.com/articles/"+re.sub(r"[^a-z0-9-]","",s["slug"])+".html"
# Email-safe cinematic design: tables + inline styles; subtle CSS motion is optional.
base="https://deepdocumentary.com/"
def image_url(s):
    image=str(s["image"]).strip()
    if image.startswith("https://"): return image
    return base+image.lstrip("/")
def title_en(s):
    title=str(s["en"]).replace(" | Deep Documentary","").strip()
    # Titles must be English, not an Arabic duplicate.
    if re.search("[\\u0600-\\u06ff]", title):
        raise ValueError("Arabic characters found in English title: "+str(s["slug"]))
    return title
def card(s,index):
    link=clean(url(s))
    img=clean(image_url(s))
    ar=clean(s["ar"])
    en=clean(title_en(s))
    return f"""<tr><td style="padding:0 22px 24px">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #36312a;border-radius:14px;background:#19191e;overflow:hidden">
       <tr><td><a href="{link}" style="text-decoration:none"><img src="{img}" alt="{ar}" width="592" style="display:block;width:100%;height:auto;max-height:300px;object-fit:cover;border:0" /></a></td></tr>
       <tr><td style="padding:23px 24px 26px">
        <div style="color:#c9a75e;font:700 11px Arial,sans-serif;letter-spacing:3px">FIELD NOTE {index:02d} &nbsp; / &nbsp; DEEP DOCUMENTARY</div>
        <h2 dir="rtl" style="color:#f5f1e9;font:bold 25px/1.55 Tahoma,Arial,sans-serif;margin:13px 0 5px;text-align:right">{ar}</h2>
        <p style="color:#c5c0b5;font:16px/1.5 Arial,sans-serif;margin:0 0 24px">{en}</p>
        <a href="{link}" style="display:inline-block;padding:14px 24px;background:#c8a45a;color:#121216;font:bold 14px Arial,sans-serif;text-decoration:none;border-radius:5px">اقرأ القصة &nbsp; | &nbsp; EXPLORE THE STORY &nbsp; ↗</a>
       </td></tr>
      </table></td></tr>"""

# Verified evergreen editorial cards, independent from published articles.
FACTS=[
("غرائب الكون | Cosmic wonders","يوم الزهرة أطول من سنته","A Venus day is longer than its year","دوران الزهرة حول محوره أبطأ من دورانه حول الشمس.","Venus takes longer to rotate once than to orbit the Sun.","https://science.nasa.gov/venus/"),
("أسرار التاريخ | History","مدينة بومبي","Pompeii","دفن ثوران فيزوف عام 79 ميلادية مدينة بومبي وحفظ آثار الحياة الرومانية.","The AD 79 eruption of Vesuvius buried Pompeii and preserved Roman daily life.","https://pompeiisites.org/en/"),
("غموض الكون | Space mysteries","الانفجارات الراديوية السريعة","Fast radio bursts","ومضات راديوية شديدة وقصيرة؛ رُبط بعضها بنجوم مغناطيسية، وما زالت مصادر أخرى قيد الدراسة.","Brief, intense radio flashes: some have been linked to magnetars, while others remain under study.","https://science.nasa.gov/universe/"),
("حقيقة أم أسطورة؟ | Fact or myth","الجانب المظلم للقمر","The dark side of the Moon","الجانب البعيد من القمر ليس مظلمًا دائمًا؛ تصله أشعة الشمس.","The far side of the Moon is not permanently dark; it receives sunlight.","https://science.nasa.gov/moon/"),
("غرائب الكون | Cosmic wonders","البقعة الحمراء على المشتري","Jupiter's Great Red Spot","عاصفة هائلة على المشتري رُصدت عبر قرون ويتغير حجمها.","A giant storm on Jupiter observed for centuries, whose size changes over time.","https://science.nasa.gov/jupiter/"),
("أسرار التاريخ | History","آلة أنتيكيثيرا","The Antikythera mechanism","آلة يونانية قديمة معقدة استخدمت تروسًا لحساب دورات فلكية.","An ancient Greek geared device used to calculate astronomical cycles.","https://www.britishmuseum.org/")
]
day_number=(dt.date.fromisoformat(today)-dt.date(2026,1,1)).days
knowledge=[FACTS[(day_number+i)%len(FACTS)] for i in range(min(4,len(FACTS)))]
def knowledge_card(f):
    category,ar,en,ar_text,en_text,source=f
    return ('<tr><td style="padding:16px 25px;background:#1b1a1f;border-bottom:1px solid #443b2b">'
        '<div style="font:bold 12px Arial;color:#d7b56b">'+clean(category)+'</div>'
        '<h3 dir="rtl" style="color:#f5eddb;font:bold 22px Tahoma;text-align:right">'+clean(ar)+'</h3>'
        '<p dir="rtl" style="color:#d4d0c7;font:15px/1.9 Tahoma;text-align:right">'+clean(ar_text)+'</p>'
        '<h4 style="color:#d7b56b;font:bold 18px Arial">'+clean(en)+'</h4>'
        '<p style="color:#d4d0c7;font:14px/1.8 Arial">'+clean(en_text)+'</p>'
        '<a style="color:#d7b56b;font:13px Arial" href="'+clean(source)+'">المصدر | Read the source ↗</a></td></tr>')

heading_ar="اكتشف قصص اليوم" if kind=="new" else "رحلة جديدة من أرشيفنا"
heading_en="TODAY'S DISCOVERIES" if kind=="new" else "REDISCOVER THE EXTRAORDINARY"
body=[f"""<!doctype html><html lang="ar"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>@media only screen and (max-width:640px){{.shell{{width:100%!important}}.hero-title{{font-size:34px!important}}.pad{{padding:24px!important}}}}
@media (prefers-reduced-motion:no-preference){{.glow{{animation:pulse 4s ease-in-out infinite}}@keyframes pulse{{0%,100%{{opacity:.7}}50%{{opacity:1}}}}}}</style></head>
<body style="margin:0;padding:0;background:#0b0b0e;color:#f5f1e9;font-family:Arial,sans-serif">
<div style="display:none;max-height:0;overflow:hidden;opacity:0">قصص واكتشافات تستحق أن تُروى | Stories worth discovering</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#0b0b0e"><tr><td align="center" style="padding:24px 8px">
<table role="presentation" class="shell" width="640" cellpadding="0" cellspacing="0" style="max-width:640px;width:100%;background:#111115;border:1px solid #343029">
<tr><td style="padding:25px 26px;border-bottom:1px solid #423822;text-align:center">
<a href="{base}" style="text-decoration:none;color:#d7b56b;font:bold 20px Georgia,serif;letter-spacing:3px"><img src="{base}assets/logo-email.png" alt="Deep Documentary" width="104" height="104" style="display:block;width:104px;height:104px;object-fit:contain;border:0;margin:0 auto 13px" /><span style="display:block">DEEP DOCUMENTARY</span></a>
<div style="font:10px Arial,sans-serif;letter-spacing:4px;color:#8f8b84;margin-top:9px">BEYOND THE ORDINARY</div></td></tr>
<tr><td class="pad" style="padding:47px 35px 34px;text-align:center;background:#17151a;background-image:linear-gradient(135deg,#211c19 0%,#101015 70%)">
<div style="font:11px Arial,sans-serif;letter-spacing:4px;color:#c5a15c;margin-bottom:16px">✦ &nbsp; THE DAILY EDITION &nbsp; ✦</div><div style="height:6px;width:100%;max-width:330px;margin:0 auto 22px;background:linear-gradient(90deg,transparent,#cba75d,transparent);border-radius:10px"></div>
<h1 class="hero-title" style="font:normal 45px/1.14 Georgia,serif;color:#f7f0df;margin:22px 0 14px">Stories beyond<br><span style="color:#d7b56b">the surface.</span></h1>
<div style="height:2px;background:#cba75d;width:65px;margin:23px auto"></div>
<h2 dir="rtl" style="font:bold 23px/1.7 Tahoma,Arial,sans-serif;margin:12px 0 4px;color:#f2e9d7">{heading_ar}</h2>
<p style="font:12px Arial,sans-serif;letter-spacing:3px;color:#aaa59d;margin:0">{heading_en}</p>
<p style="font:13px Arial,sans-serif;color:#b3a995;margin:21px 0 0">{clean(today)} &nbsp; • &nbsp; AR / EN</p></td></tr>
<tr><td style="padding:28px 0 0"><table role="presentation" width="100%" cellpadding="0" cellspacing="0">"""]
if kind=="archive":
    body.append('<tr><td dir="rtl" style="padding:0 25px 25px;color:#d7b56b;font:16px Tahoma">لا توجد مقالات جديدة اليوم | No new articles today</td></tr>')
if new_items:
    body.append('<tr><td style="padding:8px 25px 20px;color:#d7b56b;font:bold 19px Tahoma">المقالات الجديدة | NEW ARTICLES</td></tr>')
for index,item in enumerate(items,1):
    if index == len(new_items)+1 and archive_items:
        body.append("<tr><td style='padding:8px 25px 20px;color:#d7b56b;font:bold 19px Tahoma'>مختارات اليوم | TODAY'S PICKS</td></tr>")
    body.append(card(item,index))
body.append('<tr><td style="padding:24px;color:#d7b56b;font:bold 23px Georgia">BEYOND THE HEADLINES | من عالم الغموض والمعرفة</td></tr>')
for fact in knowledge:
    body.append(knowledge_card(fact))
body.append('<tr><td style="padding:24px;color:#e7d5b5;background:#242027;text-align:center;font:16px/1.8 Tahoma">سؤال اليوم | TODAY\'S QUESTION<br>أي كوكب يومه أطول من سنته؟ | Which planet has a day longer than its year?<br><span style="color:#d7b56b">الإجابة | Answer: الزهرة — Venus</span></td></tr>')
body.append(f"""</table></td></tr>
<tr><td style="padding:34px 26px;text-align:center;background:#18171a;border-top:1px solid #3c3529">
<div style="font:normal 25px Georgia,serif;color:#d7b56b">Curiosity never ends.</div>
<p dir="rtl" style="font:14px/1.8 Tahoma,Arial,sans-serif;color:#bfb8aa;margin:14px 0">كل يوم، قصة تستحق الاكتشاف.</p>
<a href="{base}" style="display:inline-block;background:#cba75d;color:#111115;text-decoration:none;padding:15px 28px;border-radius:4px;font:bold 13px Arial,sans-serif;letter-spacing:1px">EXPLORE DEEP DOCUMENTARY ↗</a></td></tr>
<tr><td style="padding:22px 26px 28px;text-align:center;color:#8d8982;font:12px/1.9 Arial,sans-serif">
Deep Documentary Daily<br>
<a href="{{{{ unsubscribe }}}}" style="color:#d7b56b;text-decoration:underline">إلغاء الاشتراك | Unsubscribe</a>
</td></tr></table></td></tr></table></body></html>""")
payload={"date":today,"kind":kind,"new_slugs":[s["slug"] for s in new_items],"archive_slugs":[s["slug"] for s in archive_items],"knowledge_topics":[f[2] for f in knowledge],"slugs":[s["slug"] for s in items],"subject":"Deep Documentary Daily | نشرتك المعرفية اليومية","html":"".join(body)}
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(OUT.parent/"newsletter-preview.html").write_text(payload["html"],encoding="utf-8")
print("Prepared",kind,len(items),"article(s). No emails sent.")
