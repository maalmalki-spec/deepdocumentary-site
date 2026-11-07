#!/usr/bin/env python3
"""Check publicly deployed article and catalogue images, not just repository files."""
import json
import os
import sys
import time
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

BASE = os.environ.get("SITE_BASE_URL", "https://deepdocumentary.com/").rstrip("/") + "/"
TIMEOUT = 18
RETRIES = 4

class RateLimited(RuntimeError):
    pass

class Images(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []
    def handle_starttag(self, tag, attrs):
        if tag.lower() != "img":
            return
        a = dict(attrs)
        src = a.get("src") or a.get("data-src")
        if src and not src.startswith(("data:", "blob:")):
            self.images.append(src)

def fetch(url, binary=False):
    last = None
    for attempt in range(RETRIES):
        try:
            req = Request(url, headers={"User-Agent": "DeepDocumentaryImageAudit/1.0", "Accept": "image/*,text/html,application/json"})
            with urlopen(req, timeout=TIMEOUT) as response:
                body = response.read(1024 if binary else 3_000_000)
                return response.status, response.headers.get("Content-Type", ""), body
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            last = str(exc)
            if isinstance(exc, HTTPError) and exc.code == 429:
                if attempt + 1 < RETRIES:
                    retry_after = exc.headers.get("Retry-After", "")
                    delay = int(retry_after) if retry_after.isdigit() else 3 * (2 ** attempt)
                    time.sleep(min(delay, 30))
                else:
                    raise RateLimited(f"HTTP 429: remote host rate-limited audit for {url}") from exc
            elif attempt + 1 < RETRIES:
                time.sleep(2)
    raise RuntimeError(last)

def check_image(url):
    status, ctype, body = fetch(url, binary=True)
    if status != 200:
        raise RuntimeError(f"HTTP {status}")
    if not ctype.lower().startswith("image/"):
        raise RuntimeError(f"unexpected Content-Type {ctype!r}")
    if not body:
        raise RuntimeError("empty image response")

def main():
    errors = []
    throttled = []
    try:
        _, _, raw = fetch(urljoin(BASE, "assets/documentary-catalogue.json"))
        stories = json.loads(raw).get("stories", [])
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: Cannot load deployed catalogue: {exc}", file=sys.stderr)
        return 1
    urls = {}
    for story in stories:
        slug = story.get("slug", "")
        article_url = urljoin(BASE, "articles/" + slug + ".html")
        image = story.get("image")
        if image:
            urls.setdefault(urljoin(BASE, image), set()).add(f"catalogue:{slug}")
        try:
            _, ctype, html = fetch(article_url)
            if "html" not in ctype.lower():
                raise RuntimeError(f"unexpected article Content-Type {ctype!r}")
            parser = Images()
            parser.feed(html.decode("utf-8", errors="replace"))
            for src in parser.images:
                urls.setdefault(urljoin(article_url, src), set()).add(f"article:{slug}")
        except RuntimeError as exc:
            errors.append(f"{article_url}: {exc}")
    for index, (url, origins) in enumerate(urls.items(), 1):
        try:
            check_image(url)
            print(f"OK {index}/{len(urls)} {url}")
        except RateLimited as exc:
            throttled.append(f"{url} ({origins}): {exc}")
            print(f"UNVERIFIED (429) {url}", file=sys.stderr)
        except RuntimeError as exc:
            errors.append(f"{url} ({', '.join(sorted(origins))}): {exc}")
            print(f"FAIL {url}: {exc}", file=sys.stderr)
    print(f"Checked {len(stories)} deployed articles and {len(urls)} unique image URLs; {len(errors)} failures, {len(throttled)} throttled/unverified")
    if throttled:
        with open("image-check-rate-limited.txt", "w", encoding="utf-8") as output:
            output.write("\n".join(throttled) + "\n")
    if errors:
        with open("image-check-failures.txt", "w", encoding="utf-8") as output:
            output.write("\n".join(errors) + "\n")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
