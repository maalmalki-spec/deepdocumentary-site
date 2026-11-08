#!/usr/bin/env python3
"""Produce review-only vertical reels from locally published HTML articles."""
import argparse, html, json, re, subprocess
from html.parser import HTMLParser
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reels-review"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

class ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.in_title = False
        self.ignore = 0
        self.parts = []
        self.in_p = False
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "footer", "header"):
            self.ignore += 1
        if tag == "title": self.in_title = True
        if tag == "p" and not self.ignore: self.in_p = True
    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "footer", "header"):
            self.ignore = max(0, self.ignore - 1)
        if tag == "title": self.in_title = False
        if tag == "p": self.in_p = False
    def handle_data(self, data):
        value = html.unescape(data).strip()
        if self.in_title: self.title += value
        if self.in_p and not self.ignore and len(value) > 25: self.parts.append(value)

def font(size):
    return ImageFont.truetype(FONT, size)

def wrap(draw, text, max_width, f):
    words = text.split()
    lines, line = [], ""
    for word in words:
        candidate = (line + " " + word).strip()
        if draw.textbbox((0, 0), candidate, font=f)[2] > max_width and line:
            lines.append(line); line = word
        else: line = candidate
    if line: lines.append(line)
    return lines[:7]

def frame(text, index, count, path):
    im = Image.new("RGB", (1080, 1920), "#080b15")
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((75, 100, 1005, 1820), radius=35, outline="#bb9146", width=5)
    d.text((110, 165), "DEEP DOCUMENTARY", font=font(56), fill="#e8c477")
    d.rectangle((110, 260, 970, 265), fill="#bb9146")
    f = font(53)
    lines = wrap(d, text, 835, f)
    y = max(570, 930 - len(lines) * 43)
    for line in lines:
        d.text((125, y), line, font=f, fill="white", direction="rtl" if re.search(r"[\u0600-\u06ff]", line) else "ltr")
        y += 95
    d.text((110, 1680), "deepdocumentary.com", font=font(42), fill="#e8c477")
    d.text((110, 1750), f"{index}/{count}  •  PREVIEW", font=font(32), fill="#b2b2b2")
    im.save(path)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--article", required=True)
    args = ap.parse_args()
    article = (ROOT / args.article).resolve()
    if not article.is_relative_to(ROOT / "articles") or article.suffix != ".html":
        raise SystemExit("Only articles/*.html is supported")
    p = ArticleParser()
    p.feed(article.read_text(encoding="utf-8"))
    title = re.sub(r"\s+", " ", p.title).split("|")[0].strip() or article.stem.replace("-", " ")
    paragraphs = [re.sub(r"\s+", " ", x).strip() for x in p.parts]
    scenes = [title] + [x[:180] for x in paragraphs if len(x) > 45][:4]
    if len(scenes) < 2: raise SystemExit("Article lacks enough paragraph text")
    target = OUT / article.stem
    target.mkdir(parents=True, exist_ok=True)
    slides = target / "slides"
    slides.mkdir(exist_ok=True)
    for i, text in enumerate(scenes, 1):
        frame(text, i, len(scenes), slides / f"{i:03d}.png")
    concat = target / "slides.txt"
    concat.write_text("".join(f"file 'slides/{i:03d}.png'\nduration 5\n" for i in range(1,len(scenes)+1)) + f"file 'slides/{len(scenes):03d}.png'\n")
    subprocess.run(["ffmpeg","-y","-loglevel","error","-safe","0","-f","concat","-i",str(concat),"-vf","fps=24,format=yuv420p","-c:v","libx264","-preset","veryfast","-movflags","+faststart",str(target/"review.mp4")],check=True)
    manifest = {"article":args.article,"title":title,"url":"https://deepdocumentary.com/"+args.article,"status":"REVIEW_REQUIRED","published":False,"duration_seconds":len(scenes)*5,"voiceover":"not_generated","note":"Silent motion storyboard; requires human fact-check, rights review and approval before publishing."}
    (target/"review.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(manifest,ensure_ascii=False))
if __name__ == "__main__": main()
