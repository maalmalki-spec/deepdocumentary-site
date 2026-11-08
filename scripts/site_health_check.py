#!/usr/bin/env python3
"""Public-site health check. No secrets or member data are collected."""
import json, os, re, time
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urldefrag
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from xml.etree import ElementTree as ET

BASE = "https://deepdocumentary.com"
MAX_PAGES = 150
MAX_ASSETS = 450
TIMEOUT = 12
class Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.assets = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and a.get("href"): self.links.append(a["href"])
        if tag in ("img", "script", "source") and a.get("src"): self.assets.append(a["src"])
        if tag == "link" and a.get("rel", "").lower() == "stylesheet" and a.get("href"): self.assets.append(a["href"])

def local(url):
    url = urldefrag(url)[0]
    p = urlsplit(url)
    return url if p.scheme in ("http", "https") and p.netloc.lower() == "deepdocumentary.com" else None

def get(url):
    try:
        req = Request(url, headers={"User-Agent": "DeepDocumentaryHealthMonitor/1.0", "Accept": "text/html,application/xml,*/*"})
        with urlopen(req, timeout=TIMEOUT) as response:
            data = response.read(850_000)
            return response.status, data, response.headers.get("Content-Type", "")
    except HTTPError as e:
        return e.code, b"", ""
    except (URLError, TimeoutError, OSError, ValueError) as e:
        return 0, str(e).encode()[:160], ""

def main():
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    pages = {BASE + "/", BASE + "/games.html", BASE + "/login.html"}
    issues = []
    status, xml, _ = get(BASE + "/sitemap.xml")
    if status == 200:
        try:
            root = ET.fromstring(xml)
            for node in root.iter():
                if node.tag.endswith("loc") and node.text:
                    u = local(node.text.strip())
                    if u: pages.add(u)
        except ET.ParseError:
            issues.append({"kind":"sitemap","url":BASE+"/sitemap.xml","status":"invalid_xml"})
    else:
        issues.append({"kind":"sitemap","url":BASE+"/sitemap.xml","status":status})
    page_list = sorted(pages)[:MAX_PAGES]
    assets = set()
    links = set()
    checked = 0
    for page in page_list:
        code, data, mime = get(page)
        checked += 1
        if code != 200:
            issues.append({"kind":"page","url":page,"status":code})
            continue
        if "html" not in mime.lower() and not page.endswith(".html") and page != BASE + "/":
            continue
        parser = Parser()
        parser.feed(data.decode("utf-8", "replace"))
        for item in parser.assets:
            u = local(urljoin(page, item))
            if u: assets.add(u)
        for item in parser.links:
            if item.startswith(("#", "mailto:", "tel:", "javascript:")): continue
            u = local(urljoin(page, item))
            if u and (urlsplit(u).path.endswith((".html", ".pdf")) or urlsplit(u).path == "/"): links.add(u)
    checked_assets = 0
    for u in sorted(assets)[:MAX_ASSETS]:
        code, _, _ = get(u)
        checked_assets += 1
        if code != 200: issues.append({"kind":"asset","url":u,"status":code})
    checked_links = 0
    for u in sorted(links - set(page_list))[:MAX_PAGES]:
        code, _, _ = get(u)
        checked_links += 1
        if code in (404, 410) or code == 0: issues.append({"kind":"link","url":u,"status":code})
    # An HTTP 200 for a public page cannot verify private login, newsletter or game interactions.
    result = {"generatedAt":started,"site":BASE,"status":"healthy" if not issues else "issues",
              "checked":{"pages":checked,"assets":checked_assets,"links":checked_links},
              "issues":issues[:100],"issueCount":len(issues),
              "limitations":"Public URLs only; authentication, newsletter delivery, and gameplay are not tested."}
    os.makedirs("health", exist_ok=True)
    with open("health/latest.json","w",encoding="utf-8") as f: json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps({"status":result["status"],"checked":result["checked"],"issues":len(issues)}))
if __name__ == "__main__": main()
