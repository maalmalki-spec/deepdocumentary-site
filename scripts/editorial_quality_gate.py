#!/usr/bin/env python3
"""Editorial quality gate: conservative checks; never substitutes human fact-checking."""
import json, pathlib, re, sys
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
    if len(sections)<10: errors.append("Fewer than 10 sections")
    if not data.get("source_research"): errors.append("No source research")
    if not data.get("claims_to_verify"): errors.append("No claim verification list")
    if not data.get("suggested_visuals"): errors.append("No visual research plan")
    if data.get("status")!="needs-human-review": errors.append("Draft review status missing")
    print(f"{path.name}: Arabic={ar}, English={en}, sections={len(sections)}; "+("FAIL: "+"; ".join(errors) if errors else "STRUCTURAL PASS (human fact-check still required)"))
    failed|=bool(errors)
if not files: print("No drafts found",file=sys.stderr);sys.exit(1)
sys.exit(1 if failed else 0)
