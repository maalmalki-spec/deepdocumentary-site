#!/usr/bin/env python3
"""Send exactly one approved-format daily Brevo campaign; fail closed on uncertainty."""
import datetime as dt
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parents[1]
digest = json.loads((ROOT / "newsletter/pending-digest.json").read_text(encoding="utf-8"))
today = dt.datetime.now(ZoneInfo("Asia/Riyadh")).date().isoformat()
if digest.get("date") != today or not digest.get("html") or not digest.get("slugs"):
    sys.exit("Refusing to send missing, stale, or empty digest.")
key = os.environ.get("BREVO_API_KEY")
if not key:
    sys.exit("BREVO_API_KEY is not configured.")
base = "https://api.brevo.com/v3"
headers = {"api-key": key, "accept": "application/json", "Content-Type": "application/json"}

def api(method, path):
    req = urllib.request.Request(base + path, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            data = response.read()
            return json.loads(data) if data else {}
    except urllib.error.HTTPError as exc:
        print("Brevo API returned HTTP", exc.code, "for", path.split("?")[0], file=sys.stderr)
        raise

name = "Deep Documentary Daily " + today
# Check all statuses, not only drafts: a previously sent campaign must block duplicates.
matches = []
offset = 0
while True:
    query = urllib.parse.urlencode({"type": "classic", "limit": 100, "offset": offset})
    data = api("GET", "/emailCampaigns?" + query)
    batch = data.get("campaigns", [])
    matches.extend(c for c in batch if c.get("name") == name)
    if len(batch) < 100:
        break
    offset += 100
    if offset > 10000:
        sys.exit("Campaign listing too large; refusing to send.")
if len(matches) != 1:
    sys.exit("Expected exactly one daily campaign; found " + str(len(matches)) + ". No email sent.")
campaign = matches[0]
if campaign.get("status") != "draft":
    print("Already processed today:", campaign.get("status"), "No email sent.")
    sys.exit(0)
if campaign.get("subject") != digest.get("subject"):
    sys.exit("Draft subject differs from today's prepared digest; refusing to send.")
list_id = int(os.environ.get("BREVO_LIST_ID", "3"))
recipients = campaign.get("recipients") or {}
if list_id not in recipients.get("listIds", []):
    sys.exit("Campaign recipients do not match configured newsletter list.")
# Check actual active recipient count; never send to an unverified/empty list.
contacts = api("GET", "/contacts/lists/" + str(list_id))
if int(contacts.get("totalSubscribers", 0)) < 1:
    sys.exit("No confirmed active subscribers; no email sent.")
api("POST", "/emailCampaigns/" + str(campaign["id"]) + "/sendNow")
print(json.dumps({"status": "send_requested", "date": today, "campaign_id": campaign["id"], "recipient_count": contacts.get("totalSubscribers")}))
