#!/usr/bin/env python3
"""Staged bilingual documentary draft generator. Manual review only; never publishes."""
import json, os, pathlib, re, sys, urllib.request, urllib.error
ROOT=pathlib.Path(__file__).resolve().parents[1]
QUEUE=ROOT/"editorial/production-queue.json"
OUT=ROOT/"editorial/generated"
MODEL=os.getenv("OPENAI_MODEL","gpt-4.1-mini")
MAX_CALLS=int(os.getenv("MAX_API_CALLS_PER_RUN","7"))
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

def ask_lead_from_sections(sections,lang):
    # Extract an opening passage from the first section without an additional paid request.
    first=sections[0]["body"].strip()
    return first[:350].rsplit(" ",1)[0]+"…" if len(first)>350 else first

def produce(item):
    title=item["title_en"]+" / "+item["title_ar"]
    research=ask(
        "You are a careful documentary research planner. No web access. Never claim to have verified a source, link, quotation, image or fact. Output JSON.",
        f"""Build a rigorous research and narrative plan for {title}. JSON fields: timeline (array of dated event descriptions), evidence (array of facts with confidence and verification_needed), disputed_claims (array), source_research (array of institution/publication search targets, not invented URLs), suggested_visuals (array of archival image/map/document search instructions with rights_to_verify=true), sections (array of 10-12 paired heading_ar/heading_en and evidence notes). Do not invent citations. Label uncertain facts VERIFY.""",
        3500)
    # Three separately bounded parts per language prevent short single-response drafts.
    outlines=research.get("sections",[])
    if len(outlines)<10: raise RuntimeError("Research outline has fewer than ten sections")
    groups=[outlines[i:i+4] for i in range(0,len(outlines),4)]
    if len(groups)!=3: raise RuntimeError("Expected 10-12 outline sections")
    language_results={}
    for lang in ("ar","en"):
        chunks=[]
        for i,group in enumerate(groups):
            prompt=f"""Topic: {title}. Language: {lang}. Part {i+1} of 3.
Write ONLY the following {len(group)} sections in the same order:
{json.dumps(group,ensure_ascii=False)}
Research notes are unverified, not proof: {json.dumps(research.get('evidence',[]),ensure_ascii=False)[:4500]}
Return JSON with sections array of exactly the requested count, each object having heading and body strings, and claims_to_verify array. No nested wrapper.
Each section must have 160-230 meaningful words in the requested language. Target 650-850 words for this part, so the complete article exceeds 1500 words. Do not add a lead or conclusion outside these sections. Every article must integrate at least two verifiable real-world micro-stories and two concrete explanatory examples across its sections. Never invent dialogue, scenes, people, quotes, links, citations, or image rights. Mark disputed or unsupported details VERIFY. Maintain narrative continuity, no filler."""
            chunk=ask("You are a meticulous documentary storyteller. Write original, fluent Arabic for ar and idiomatic English for en. Each section must be substantive, evidence-aware and vivid without fabricated details. JSON only.",prompt,4100)
            part=chunk.get("sections",[])
            if isinstance(part,dict): part=list(part.values())
            normalized=[]
            if isinstance(part,list):
                for k,x in enumerate(part):
                    if isinstance(x,str): x={"body":x}
                    if not isinstance(x,dict): continue
                    body=x.get("body") or x.get("text") or x.get("content")
                    if isinstance(body,list): body="\n\n".join(str(v) for v in body)
                    heading=x.get("heading") or x.get("title") or group[min(k,len(group)-1)].get("heading_"+lang)
                    if isinstance(body,str) and body.strip() and isinstance(heading,str) and heading.strip():
                        normalized.append({"heading":heading,"body":body})
            if len(normalized)!=len(group):
                raise RuntimeError(f"Malformed {lang} part {i+1}: expected {len(group)} sections, got {len(normalized)}; keys={list(chunk.keys())}")
            chunks.append({"sections":normalized,"claims_to_verify":chunk.get("claims_to_verify",[])})
        sections=[section for chunk in chunks for section in chunk["sections"]]
        lead=ask_lead_from_sections(sections,lang)
        language_results[lang]={"sections":sections,"lead":lead,"claims_to_verify":[claim for chunk in chunks for claim in chunk.get("claims_to_verify",[])]}
    ar=language_results["ar"];en=language_results["en"]
    if not valid_language(ar,"ar") or not valid_language(en,"en"):
        print(f"REJECTED {item['slug']}: ar={words(ar['lead'])+sum(words(x['body']) for x in ar['sections'])}; en={words(en['lead'])+sum(words(x['body']) for x in en['sections'])}",file=sys.stderr)
        return False
    sections=[{"heading_ar":a["heading"],"body_ar":a["body"],"heading_en":b["heading"],"body_en":b["body"]} for a,b in zip(ar["sections"],en["sections"])]
    data={"slug":item["slug"],"title_ar":item["title_ar"],"title_en":item["title_en"],"lead_ar":ar["lead"],"lead_en":en["lead"],"sections":sections,"claims_to_verify":research.get("disputed_claims",[])+ar["claims_to_verify"]+en["claims_to_verify"],"suggested_visuals":research.get("suggested_visuals",[]),"source_research":research.get("source_research",[]),"research_timeline":research.get("timeline",[]),"research_evidence":research.get("evidence",[]),"status":"needs-human-review","verified_sources":[],"licensed_images":[]}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/(item["slug"]+".json")).write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return True

def main():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Missing API key; no charges incurred")
    if MAX_CALLS<7: raise RuntimeError("Seven calls required: research plan and three parts per language")
    completed=0
    for item in json.loads(QUEUE.read_text(encoding="utf-8")):
        slug=item["slug"]
        if (OUT/(slug+".json")).exists() or (ROOT/"articles"/(slug+".html")).exists(): continue
        if calls+7>MAX_CALLS: break
        try:
            if produce(item): completed+=1
        except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError,ValueError,RuntimeError,KeyError,TypeError) as e:
            print(f"Generation stopped for {slug}: {e}",file=sys.stderr);break
        if completed>=MAX_DRAFTS:break
    print(f"API calls: {calls}; drafts saved: {completed}; published: 0")
    if completed==0: raise RuntimeError("No draft passed validation; workflow failed")
if __name__=="__main__": main()
