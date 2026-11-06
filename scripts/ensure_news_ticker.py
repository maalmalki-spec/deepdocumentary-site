#!/usr/bin/env python3
"""Ensure all public HTML pages, including future articles, load the shared news ticker."""
from pathlib import Path

TAG='<script defer src="/assets/news-ticker.js?v=1"></script>'
SKIP={"dashboard.html"}
def main():
 changed=[]
 for file in Path(".").rglob("*.html"):
  if ".git" in file.parts or "node_modules" in file.parts or file.name in SKIP:
   continue
  data=file.read_text(encoding="utf-8")
  if "assets/news-ticker.js" in data or "</body>" not in data.lower():
   continue
  index=data.lower().rfind("</body>")
  file.write_text(data[:index]+TAG+data[index:],encoding="utf-8")
  changed.append(str(file))
 print("News ticker injection:",len(changed),"pages updated",changed)
if __name__=="__main__":main()
