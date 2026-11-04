#!/usr/bin/env python3
"""Use vendored, verified images after download succeeds."""
from pathlib import Path
import re
root=Path(__file__).resolve().parents[1]
article=root/"articles/apollo-11.html"
home=root/"index.html"
images=["launch","earthrise","aldrin","lunar-module","footprint","mission-control"]
for name in images:
    path=root/"assets/images/apollo-11"/(name+".webp")
    if not path.is_file() or path.stat().st_size<10000:
        raise RuntimeError("Missing local image: "+str(path))
s=article.read_text(encoding="utf-8")
figures=list(re.finditer(r"<figure>[\s\S]*?</figure>",s))
if len(figures)!=6:
    raise RuntimeError("Expected six image figures, found "+str(len(figures)))
# Order in the article: launch, earthrise, aldrin, lunar-module, splashdown, footprint.
article_order=["launch","earthrise","aldrin","lunar-module","mission-control","footprint"]
for match,name in reversed(list(zip(figures,article_order))):
    fragment=match.group()
    fragment,n=re.subn(r'<img\b[^>]*>',lambda m:re.sub(r'src="[^"]+"', 'src="../assets/images/apollo-11/'+name+'.webp"',re.sub(r'\s+onerror="[^"]*"','',m.group())),fragment,count=1)
    if n!=1:raise RuntimeError("Missing img in figure "+name)
    s=s[:match.start()]+fragment+s[match.end():]
article.write_text(s,encoding="utf-8")
s=home.read_text(encoding="utf-8")
pattern=r"(url:'articles/apollo-11.html'[^\n]*?image:)'[^']+'"
s,n=re.subn(pattern,r"\1'assets/images/apollo-11/aldrin.webp'",s,count=1)
if n!=1:raise RuntimeError("Could not update Apollo 11 homepage image")
home.write_text(s,encoding="utf-8")
print("Updated article and homepage to use locally archived images")
