#!/usr/bin/env python3
"""Discover scholarly sources for the next unprocessed documentary topic.
No AI API calls. Candidate research only, NOT independent fact verification.
"""
import json, os, pathlib, re, sys, urllib.parse, urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
QUEUE=ROOT/"editorial/production-queue.json"
RESEARCH=ROOT/"editorial/research"
OUT=ROOT/"editorial/generated"
def fetch_json(url):
    req=urllib.request.Request(url,headers={"User-Agent":"DeepDocumentaryEditorial/1.0 (research discovery; contact via repository)"})
    with urllib.request.urlopen(req,timeout=25) as r:
        return json.load(r)
def abstract_text(inv):
    if not isinstance(inv,dict): return ""
    pairs=sorted((pos,word) for word,positions in inv.items() for pos in positions)
    return " ".join(word for _,word in pairs)[:2200]
def discover(item):
    query=urllib.parse.urlencode({"search":item["title_en"],"per-page":"25","filter":"has_doi:true"})
    data=fetch_json("https://api.openalex.org/works?"+query)
    tokens=set(re.findall(r"[a-z]{4,}",item["title_en"].lower()))-{"the","what","were","with","from","into","history","understanding"}
    works=[]
    for w in data.get("results",[]):
        title=w.get("title") or ""
        matched=tokens.intersection(re.findall(r"[a-z]{4,}",title.lower()))
        if len(matched)<min(2,len(tokens)): continue
        doi=w.get("doi")
        if not doi or not doi.startswith("https://doi.org/"): continue
        works.append({"title":title,"year":w.get("publication_year"),"doi":doi,
          "publisher":(w.get("primary_location") or {}).get("source",{}),
          "abstract":abstract_text(w.get("abstract_inverted_index"))})
        if len(works)==6: break
    if len(works)<3:
        raise RuntimeError("Fewer than three relevant DOI-indexed scholarly works; manual research required")
    lines=[f"# {item['title_en']} — AUTOMATIC RESEARCH CANDIDATES",
      "Status: AUTO-DISCOVERED / NOT VERIFIED / NOT PUBLICATION APPROVED.",
      "These are OpenAlex indexed scholarly records. DOI links identify publications, not confirmation that every claim is true.",
      "Editorial review MUST inspect each full publication, extract supported claims and find primary institutional sources.",
      "Do not infer eyewitness accounts, quotations, or image rights from metadata.",
      "", "## Candidate scholarly publications"]
    for i,w in enumerate(works,1):
        lines.extend([f"### {i}. {w['title']} ({w['year']})",f"Source: {w['doi']}",
          f"Abstract (index metadata, may be missing): {w['abstract'] or 'Unavailable; full text verification required.'}",""])
    lines.extend(["## Required human checks","- Confirm article-topic relevance and source accessibility.",
      "- Confirm dates, quotes, anecdotes, and disputed claims against primary evidence.",
      "- Acquire image permissions separately. No automated publishing.",""])
    return "\n".join(lines)
def main():
    for item in json.loads(QUEUE.read_text(encoding="utf-8")):
        slug=item["slug"]
        if (OUT/(slug+".json")).exists() or (ROOT/"articles"/(slug+".html")).exists():continue
        path=RESEARCH/(slug+"-sources.md")
        if path.exists():
            print(f"Research dossier exists: {path.relative_to(ROOT)}")
            return
        dossier=discover(item)
        RESEARCH.mkdir(parents=True,exist_ok=True)
        path.write_text(dossier,encoding="utf-8")
        print(f"Research candidates created: {path.relative_to(ROOT)}")
        return
    raise RuntimeError("No pending topic")
if __name__=="__main__":
    try:main()
    except Exception as exc:
        print(f"Research discovery stopped safely: {exc}",file=sys.stderr)
        sys.exit(1)
