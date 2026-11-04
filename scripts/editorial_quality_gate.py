#!/usr/bin/env python3
"""Editorial quality gate: conservative checks; never substitutes human fact-checking."""
import json, pathlib, re, sys
from urllib.parse import urlparse
root=pathlib.Path(__file__).resolve().parents[1]
files=[pathlib.Path(p) for p in sys.argv[1:]] or sorted((root/"editorial/generated").glob("*.json"))
def words(s): return len(re.findall(r"\S+",s or ""))
failed=False
for path in files:
    data=json.loads(path.read_text(encoding="utf-8"))
    sections=data.get("sections",[])
    ar=words(data.get("lead_ar"))+sum(words(s.get("body_ar")) for s in sections)
    en=words(data.get("lead_en"))+sum(words(s.get("body_en")) for s in sections)
    errors=[]
    if ar<1500: errors.append(f"Arabic {ar} words < 1500")
    if en<1500: errors.append(f"English {en} words < 1500")
    if ar>2500: errors.append(f"Arabic {ar} words > 2500")
    if en>2500: errors.append(f"English {en} words > 2500")
    if len(sections)<10: errors.append("Fewer than 10 sections")
    if not data.get("source_research"): errors.append("No source research")
    urls=data.get("source_urls",[])
    if not isinstance(urls,list) or len(set(urls))<3 or any(not urlparse(u).hostname for u in urls):
        errors.append("Fewer than three curated source URLs")
    dossier=data.get("research_dossier","")
    if not dossier or not (root/dossier).is_file():
        errors.append("Missing per-topic source dossier")
    bodies=" ".join(x.get("body_ar","")+" "+x.get("body_en","") for x in sections)
    cited=[u for u in urls if u in bodies]
    if len(cited)<3:
        errors.append(f"Only {len(cited)} of 3 required distinct sources cited in article text")
    for lang in ("ar","en"):
        uncited=[i+1 for i,x in enumerate(sections) if not any(u in x.get("body_"+lang,"") for u in urls)]
        if uncited:
            errors.append(f"{lang}: uncited sections {uncited}")
    if data.get("research_dossier") and (root/data["research_dossier"]).is_file():
        dossier_text=(root/data["research_dossier"]).read_text(encoding="utf-8")
        if "AUTO-DISCOVERED / NOT VERIFIED" in dossier_text:
            errors.append("Source dossier contains unverified automatic candidates")
    if data.get("verified_sources") or data.get("licensed_images"):
        errors.append("Generator must not assert sources or images were verified/licensed")
    if not data.get("claims_to_verify"): errors.append("No claim verification list")
    if not data.get("suggested_visuals"): errors.append("No visual research plan")
    if data.get("status")!="needs-human-review": errors.append("Draft review status missing")
    print(f"{path.name}: Arabic={ar}, English={en}, sections={len(sections)}; "+("FAIL: "+"; ".join(errors) if errors else "STRUCTURAL PASS (human fact-check still required)"))
    failed|=bool(errors)
if not files: print("No drafts found",file=sys.stderr);sys.exit(1)
sys.exit(1 if failed else 0)
