#!/usr/bin/env python3
"""Review-only English-narrated reels with synchronized Arabic subtitles."""
import argparse, html, json, re, subprocess, wave
from html.parser import HTMLParser
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reels-review"
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

class Pairs(HTMLParser):
    def __init__(self):
        super().__init__(); self.items=[]; self.title=""; self.in_title=False
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=="title": self.in_title=True
        if tag in ("h1","h2","p") and attrs.get("data-en") and attrs.get("data-ar"):
            en=html.unescape(attrs["data-en"]).strip()
            ar=html.unescape(attrs["data-ar"]).strip()
            if len(en.split())>=5 and len(ar)>10:
                self.items.append((en,ar))
    def handle_endtag(self,tag):
        if tag=="title":self.in_title=False
    def handle_data(self,data):
        if self.in_title:self.title+=data

def command(args):
    subprocess.run(args,check=True,stdout=subprocess.DEVNULL)

def duration(path):
    with wave.open(str(path),"rb") as w:
        return w.getnframes()/w.getframerate()

def wrap(draw,text,font,maxwidth):
    words=text.split(); lines=[]; current=""
    for word in words:
        trial=(current+" "+word).strip()
        if draw.textbbox((0,0),trial,font=font)[2]>maxwidth and current:
            lines.append(current);current=word
        else:current=trial
    if current:lines.append(current)
    return lines

def frame(en,ar,index,total,path):
    image=Image.new("RGB",(1080,1920),"#080b15")
    d=ImageDraw.Draw(image)
    d.rounded_rectangle((72,110,1008,1810),radius=32,outline="#bb9146",width=5)
    d.text((115,165),"DEEP DOCUMENTARY",font=ImageFont.truetype(FONT,53),fill="#e8c477")
    d.line((115,265,965,265),fill="#bb9146",width=4)
    enfont=ImageFont.truetype(FONT,54)
    for j,line in enumerate(wrap(d,en,enfont,820)[:6]):
        d.text((125,510+j*87),line,font=enfont,fill="#f7f3ed")
    arfont=ImageFont.truetype(FONT,49)
    lines=wrap(d,ar,arfont,800)[:5]
    d.rounded_rectangle((105,1220,975,1590),radius=20,fill="#191d28")
    for j,line in enumerate(lines):
        # RAQM ensures contextual Arabic shaping and right-to-left ordering.
        d.text((935,1260+j*65),line,font=arfont,anchor="ra",direction="rtl",fill="#f9e5b6")
    d.text((115,1690),"deepdocumentary.com",font=ImageFont.truetype(FONT,40),fill="#e8c477")
    d.text((115,1750),f"{index}/{total}  •  REVIEW ONLY",font=ImageFont.truetype(FONT,28),fill="#aaa")
    image.save(path)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--article",required=True)
    args=ap.parse_args()
    path=(ROOT/args.article).resolve()
    if not path.is_relative_to(ROOT/"articles") or path.suffix!=".html" or not path.is_file():
        raise SystemExit("Expected an existing articles/*.html")
    parser=Pairs();parser.feed(path.read_text(encoding="utf-8"))
    if not parser.items:raise SystemExit("Article has no paired data-en/data-ar passages")
    # Prefer short narrative passages; do not claim machine-generated translations.
    passages=[(en[:280],ar[:320]) for en,ar in parser.items if len(en.split())>=9][:5]
    if not passages:raise SystemExit("No suitable bilingual passages")
    target=OUT/path.stem;target.mkdir(parents=True,exist_ok=True)
    segments=[];timeline=[];cursor=0.0
    for i,(en,ar) in enumerate(passages,1):
        png=target/f"slide-{i:03d}.png";wav=target/f"voice-{i:03d}.wav"
        frame(en,ar,i,len(passages),png)
        command(["espeak-ng","-v","en-us+m3","-s","138","-w",str(wav),en])
        seconds=duration(wav)+0.3
        clip=target/f"clip-{i:03d}.mp4"
        command(["ffmpeg","-y","-loglevel","error","-loop","1","-framerate","24","-i",str(png),"-i",str(wav),"-t",str(seconds),"-vf","format=yuv420p","-c:v","libx264","-preset","veryfast","-c:a","aac","-ar","44100","-ac","1","-shortest",str(clip)])
        segments.append(clip)
        timeline.append({"start":round(cursor,2),"end":round(cursor+seconds,2),"english":en,"arabic":ar})
        cursor+=seconds
    concat=target/"concat.txt"
    concat.write_text("".join("file '"+p.name+"'\n" for p in segments),encoding="utf-8")
    command(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",str(concat),"-c","copy",str(target/"review.mp4")])
    manifest={"article":args.article,"title":parser.title,"url":"https://deepdocumentary.com/"+args.article,"status":"REVIEW_REQUIRED","published":False,"voiceover":"English offline espeak-ng (synthetic placeholder voice)","subtitles":"Arabic hardcoded scene subtitles","duration_seconds":round(cursor,2),"cues":timeline,"note":"Requires editorial and audiovisual review. No Instagram publishing."}
    (target/"review.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"output":str(target/"review.mp4"),"duration":round(cursor,2),"segments":len(segments)},ensure_ascii=False))
if __name__=="__main__":main()
