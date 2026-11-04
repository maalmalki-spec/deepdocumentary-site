#!/usr/bin/env python3
"""Staged bilingual documentary draft generator. Manual review only; never publishes."""
import json, os, pathlib, re, sys, urllib.request, urllib.error
from urllib.parse import urlparse
ROOT=pathlib.Path(__file__).resolve().parents[1]
QUEUE=ROOT/"editorial/production-queue.json"
OUT=ROOT/"editorial/generated"
RESEARCH=ROOT/"editorial/research"
MODEL=os.getenv("OPENAI_MODEL","gpt-4.1-mini")
MAX_CALLS=int(os.getenv("MAX_API_CALLS_PER_RUN","25"))
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
    usage=result.get("usage",{})
    print(f"Request {calls}: input_tokens={usage.get('prompt_tokens',0)} output_tokens={usage.get('completion_tokens',0)}",flush=True)
    message=result["choices"][0]["message"]
    if result["choices"][0].get("finish_reason")!="stop": raise RuntimeError("Truncated response; discarded")
    return json.loads(message["content"])

def words(s): return len((s or "").split())
def valid_language(obj,lang):
    sections=obj.get("sections")
    if not isinstance(sections,list) or len(sections)<10: return False
    return words(obj.get("lead"))+sum(words(x.get("body")) for x in sections)>=1500

def ask_lead_from_sections(sections,lang):
    # Extract an opening passage from the first section without an additional paid request.
    first=sections[0]["body"].strip()
    return first[:350].rsplit(" ",1)[0]+"…" if len(first)>350 else first

def load_verified_research(item):
    """Fail closed before paid calls: each topic needs curated, real source URLs."""
    path=RESEARCH/(item["slug"]+"-sources.md")
    if not path.exists():
        raise RuntimeError(f"Missing human-curated source dossier: {path.relative_to(ROOT)}; zero API calls")
    dossier=path.read_text(encoding="utf-8")
    urls=re.findall(r"https?://[^\\s)]+",dossier)
    valid=[u for u in urls if urlparse(u).hostname and "." in urlparse(u).hostname]
    if len(set(valid))<3:
        raise RuntimeError("Research dossier needs at least three distinct source URLs; zero API calls")
    if "AUTO-DISCOVERED / NOT VERIFIED" in dossier:\n        raise RuntimeError("Auto-discovered bibliography needs evidence review before paid writing; zero API calls")\n    return dossier, list(dict.fromkeys(valid))

def produce(item):
    dossier,source_urls=load_verified_research(item)
    title=item["title_en"]+" / "+item["title_ar"]
    research=ask(
        "You are a careful documentary research planner. No web access. Use only the supplied curated dossier; never invent sources, quotes, or facts. Output JSON.",
        f"""CURATED RESEARCH DOSSIER (not independently verified by the model):\\n{dossier[:18000]}\\n\\nBuild a rigorous research and narrative plan for {title}. JSON fields: timeline (array of dated event descriptions), evidence (array of facts with confidence and verification_needed), disputed_claims (array), source_research (array of institution/publication search targets, not invented URLs), suggested_visuals (array of archival image/map/document search instructions with rights_to_verify=true), sections (array of 10-12 paired heading_ar/heading_en and evidence notes). Do not invent citations. Label uncertain facts VERIFY.""",
        3500)
    # Fixed, independent sections eliminate multi-section JSON parsing failures.
    outline=research.get("sections",[])
    if not isinstance(outline,list) or len(outline)<10:
        raise RuntimeError("Research plan lacks ten sections")
    outline=outline[:12]
    # Always use 12 sections; research may supply only ten.
    while len(outline)<12:
        n=len(outline)+1
        outline.append({"heading_ar":f"الفصل {n} — تحليل الأدلة","heading_en":f"Chapter {n} — Examining the evidence"})
    language_results={}
    for lang in ("ar","en"):
        sections=[]
        for i,section in enumerate(outline):
            heading=section.get("heading_"+lang) or section.get("heading") or f"Section {i+1}"
            prompt=f"""Write one original documentary section in language {lang} for: {title}.
Section {i+1} of 12: {heading}.
Section research note: {json.dumps(section,ensure_ascii=False)[:1200]}
Curated source dossier: {dossier[:11500]}\nResearch context: {json.dumps(research.get('evidence',[]),ensure_ascii=False)[:1800]}
Return ONE JSON object with exactly two keys: heading (string) and body (string).
Write 180-230 substantial words in body. Never return a list or multiple sections.
Build a cinematic but factual narrative. Write with narrative continuity, without invented scenes. Include two documented real-life micro-stories where the dossier supports them, and clearly label any explanatory analogies. Cite relevant dossier source URLs inline in the body. No fabricated dialogue, quotations, URLs, eyewitnesses or verified claims. Explicitly flag disputed claims VERIFY. This is a draft for human fact-checking."""
            chunk=ask("Documentary editor. Original natural prose, no invented evidence. JSON object only.",prompt,1700)
            body=chunk.get("body") or chunk.get("text") or chunk.get("content")
            if not isinstance(body,str) or not body.strip():
                raise RuntimeError(f"Empty {lang} section {i+1}; response keys={list(chunk.keys())}")
            if words(body)<120:
                raise RuntimeError(f"Short {lang} section {i+1}: {words(body)} words")
            sections.append({"heading":str(chunk.get("heading") or heading),"body":body})
            print(f"Accepted {lang} section {i+1}: {words(body)} words",flush=True)
        language_results[lang]={"sections":sections,"lead":ask_lead_from_sections(sections,lang)}
    ar=language_results["ar"];en=language_results["en"]
    if not valid_language(ar,"ar") or not valid_language(en,"en"):
        raise RuntimeError(f"Underlength: Arabic={words(ar['lead'])+sum(words(x['body']) for x in ar['sections'])}, English={words(en['lead'])+sum(words(x['body']) for x in en['sections'])}")
    sections=[{"heading_ar":a["heading"],"body_ar":a["body"],"heading_en":b["heading"],"body_en":b["body"]} for a,b in zip(ar["sections"],en["sections"])]
    data={"slug":item["slug"],"title_ar":item["title_ar"],"title_en":item["title_en"],"lead_ar":ar["lead"],"lead_en":en["lead"],"sections":sections,"claims_to_verify":research.get("disputed_claims") or ["Verify factual claims, anecdotes, dates and primary sources before publishing"],"suggested_visuals":research.get("suggested_visuals") or ["Locate rights-cleared archival material"],"source_research":research.get("source_research") or ["Curated institutional sources"],"source_urls":source_urls,"research_dossier":str((RESEARCH/(item["slug"]+"-sources.md")).relative_to(ROOT)),"research_timeline":research.get("timeline",[]),"research_evidence":research.get("evidence",[]),"status":"needs-human-review","verified_sources":[],"licensed_images":[]}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/(item["slug"]+".json")).write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return True

def main():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Missing API key; no charges incurred")
    if MAX_CALLS<25: raise RuntimeError("25 calls required: research plus 12 sections per language")
    completed=0
    for item in json.loads(QUEUE.read_text(encoding="utf-8")):
        slug=item["slug"]
        if slug in set(filter(None,os.getenv("SKIP_SLUGS","").split(","))): continue
        if (OUT/(slug+".json")).exists() or (ROOT/"articles"/(slug+".html")).exists(): continue
        if calls+25>MAX_CALLS: break
        try:
            load_verified_research(item)  # validate before any paid request
            if produce(item): completed+=1
        except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError,ValueError,RuntimeError,KeyError,TypeError) as e:
            print(f"Generation stopped for {slug}: {e}",file=sys.stderr);break
        if completed>=MAX_DRAFTS:break
    print(f"API calls: {calls}; drafts saved: {completed}; published: 0")
    if completed==0: raise RuntimeError("No draft passed validation; workflow failed")
if __name__=="__main__": main()
