#!/usr/bin/env python3
"""Staged bilingual documentary draft generator. Manual review only; never publishes."""
import json, os, pathlib, re, sys, urllib.request, urllib.error
ROOT=pathlib.Path(__file__).resolve().parents[1]
QUEUE=ROOT/"editorial/production-queue.json"
OUT=ROOT/"editorial/generated"
MODEL=os.getenv("OPENAI_MODEL","gpt-4.1-mini")
MAX_CALLS=int(os.getenv("MAX_API_CALLS_PER_RUN","3"))
MAX_DRAFTS=int(os.getenv("MAX_DRAFTS_PER_RUN","1"))
calls=0

def ask(system,user,max_tokens):
    global calls
    if calls>=MAX_CALLS: raise RuntimeError("API request safety limit reached")
    key=os.getenv("OPENAI_API_KEY")
    if not key: raise RuntimeError("OPENAI_API_KEY not configured")
    payload=json.dumps({"model":MODEL,"messages":[{"role":"system","content":system},{"role":"user","content":user}],"response_format":{"type":"json_object"},"max_tokens":max_tokens,"temperature":0.35}).encode()
    calls+=1
    req=urllib.request.Request("https://api.openai.com/v1/chat/completions",data=payload,headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=180) as response:
        result=json.load(response)
    message=result["choices"][0]["message"]
    if result["choices"][0].get("finish_reason")!="stop": raise RuntimeError("Truncated response; discarded")
    return json.loads(message["content"])

def words(s): return len((s or "").split())
def valid_language(obj,lang):
    sections=obj.get("sections")
    if not isinstance(sections,list) or len(sections)<10: return False
    return words(obj.get("lead"))+sum(words(x.get("body")) for x in sections)>=1500

def produce(item):
    title=item["title_en"]+" / "+item["title_ar"]
    research=ask(
        "You are a careful documentary research planner. No web access. Never claim to have verified a source, link, quotation, image or fact. Output JSON.",
        f"""Build a rigorous research and narrative plan for {title}. JSON fields: timeline (array of dated event descriptions), evidence (array of facts with confidence and verification_needed), disputed_claims (array), source_research (array of institution/publication search targets, not invented URLs), suggested_visuals (array of archival image/map/document search instructions with rights_to_verify=true), sections (array of 10-12 paired heading_ar/heading_en and evidence notes). Do not invent citations. Label uncertain facts VERIFY.""",
        3500)
    common="""You write a compelling, accurate documentary narrative, not a generic encyclopedia entry. Start with an arresting *documented* moment, sustain narrative tension with evidence, reveal competing explanations fairly, and end with a meaningful resolution or open question. Never invent dialogue, feelings, quotations, source links or scenes. Mark uncertainty explicitly. In EVERY article weave in at least two vivid, verifiable real-world anecdotes or micro-stories involving documented people/events, plus two concrete explanatory examples that help readers grasp the stakes. Integrate them naturally into the narrative rather than as disconnected lists. Do not invent characters, conversations or anecdotal details; if a story cannot be supported by research, flag it VERIFY and do not assert it as fact. No filler, repetition, or exaggerated claims. Return JSON only with fields title, lead, sections (array of 10-12 objects each with heading, body), claims_to_verify (array). Each language must have 1500-2500 meaningful words TOTAL; each section must be substantial. Draft only, NOT fact-checked."""
    plan=json.dumps(research,ensure_ascii=False)
    ar=ask(common+" Write original idiomatic Modern Standard Arabic, not a translation.",f"Arabic article: {item['title_ar']}. Follow research plan (unverified; do not treat as verified): {plan}. 1500+ Arabic words. JSON only.",7600)
    en=ask(common+" Write natural original English, not a literal translation.",f"English article: {item['title_en']}. Follow same research plan (unverified): {plan}. 1500+ English words. JSON only.",7600)
    if not valid_language(ar,"ar") or not valid_language(en,"en"):
        print(f"REJECTED {item['slug']}: ar={words(ar.get('lead'))+sum(words(x.get('body')) for x in ar.get('sections',[]))}; en={words(en.get('lead'))+sum(words(x.get('body')) for x in en.get('sections',[]))}",file=sys.stderr)
        return False
    if len(ar["sections"])!=len(en["sections"]):
        print("REJECTED: language section counts differ",file=sys.stderr);return False
    sections=[{"heading_ar":a["heading"],"body_ar":a["body"],"heading_en":b["heading"],"body_en":b["body"]} for a,b in zip(ar["sections"],en["sections"])]
    data={"slug":item["slug"],"title_ar":ar.get("title") or item["title_ar"],"title_en":en.get("title") or item["title_en"],"lead_ar":ar["lead"],"lead_en":en["lead"],"sections":sections,"claims_to_verify":research.get("disputed_claims",[])+ar.get("claims_to_verify",[])+en.get("claims_to_verify",[]),"suggested_visuals":research.get("suggested_visuals",[]),"source_research":research.get("source_research",[]),"research_timeline":research.get("timeline",[]),"research_evidence":research.get("evidence",[]),"status":"needs-human-review","verified_sources":[],"licensed_images":[]}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/(item["slug"]+".json")).write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return True

def main():
    if not os.getenv("OPENAI_API_KEY"):
        print("Missing API key; no charges incurred.");return
    if MAX_CALLS<3: raise RuntimeError("Three calls required: plan, Arabic, English")
    completed=0
    for item in json.loads(QUEUE.read_text(encoding="utf-8")):
        slug=item["slug"]
        if (OUT/(slug+".json")).exists() or (ROOT/"articles"/(slug+".html")).exists(): continue
        if calls+3>MAX_CALLS: break
        try:
            if produce(item): completed+=1
        except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError,ValueError,RuntimeError,KeyError,TypeError) as e:
            print(f"Generation stopped for {slug}: {e}",file=sys.stderr);break
        if completed>=MAX_DRAFTS:break
    print(f"API calls: {calls}; drafts saved: {completed}; published: 0")
if __name__=="__main__": main()
