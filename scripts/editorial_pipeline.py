#!/usr/bin/env python3
"""Generate up to 2 bilingual *drafts*, never auto-publish. Requires OPENAI_API_KEY."""
import json, os, pathlib, re, sys, urllib.request, urllib.error
ROOT=pathlib.Path(__file__).resolve().parents[1]
PLAN=ROOT/"editorial"/"production-queue.json"
OUT=ROOT/"editorial"/"generated"
def call(prompt):
    key=os.getenv("OPENAI_API_KEY")
    if not key:
        print("OPENAI_API_KEY is not configured. Skipping; no API charges.",file=sys.stderr)
        return None
    payload=json.dumps({"model":os.getenv("OPENAI_MODEL","gpt-4.1-mini"),"messages":[{"role":"system","content":"You are a meticulous documentary editor. Do not invent sources, quotes, dates, image URLs, or claims. When unsure, mark VERIFY. Return JSON only."},{"role":"user","content":prompt}],"response_format":{"type":"json_object"},"temperature":0.35}).encode()
    req=urllib.request.Request("https://api.openai.com/v1/chat/completions",data=payload,headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=110) as resp:
        return json.loads(json.load(resp)["choices"][0]["message"]["content"])
def main():
    queue=json.loads(PLAN.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True,exist_ok=True)
    count=0
    for item in queue:
        slug=item["slug"]
        if (OUT/(slug+".json")).exists() or (ROOT/"articles"/(slug+".html")).exists():
            continue
        prompt=f"""Prepare a substantive bilingual documentary feature draft about {item['title_ar']} / {item['title_en']}.
Return JSON keys: slug, title_ar, title_en, lead_ar, lead_en, sections (array of 10+ objects each with heading_ar,heading_en,body_ar,body_en), claims_to_verify (array), suggested_visuals (array of descriptive search instructions, NOT fabricated links), source_research (array of institution names and exact publications if confidently known, NO invented URLs), status (must be 'needs-human-review').
Target engaging coherent narrative with substantial factual depth; Arabic and English are independently readable. Mark contested facts clearly. Do not pretend you verified external sources; there is no web browsing here. JSON only."""
        try: data=call(prompt)
        except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError,ValueError) as e:
            print("Generation failed:",str(e),file=sys.stderr);break
        if data is None: break
        if not isinstance(data.get("sections"),list) or len(data["sections"])<8:
            print("Draft below minimum section threshold; skipping",slug,file=sys.stderr);continue
        data["slug"]=slug;data["status"]="needs-human-review"
        (OUT/(slug+".json")).write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        count+=1
        if count>=2:break
    print(f"Created {count} draft(s). No articles published.")
if __name__=="__main__":main()
