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

def api(method, path, payload=None):
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(base + path, data=body, headers=headers, method=method)
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
# Campaign listings can omit recipient details; verify the full campaign before sending.
detail = api("GET", "/emailCampaigns/" + str(campaign["id"]))
recipients = detail.get("recipients") or {}
raw_ids = recipients.get("listIds") or []
try:
    recipient_ids = {int(value) for value in raw_ids}
except (TypeError, ValueError):
    sys.exit("Invalid recipient list IDs in Brevo campaign; no email sent.")
if list_id not in recipient_ids:
    # Repair a draft with missing recipients, then independently verify the saved settings.
    # Never overwrite a draft that already targets another list.
    if recipient_ids or recipients.get("exclusionListIds") or recipients.get("segmentIds"):
        sys.exit("Draft has unexpected recipient targeting; refusing to modify or send.")
    api("PUT", "/emailCampaigns/" + str(campaign["id"]), {"recipients": {"listIds": [list_id]}})
    detail = api("GET", "/emailCampaigns/" + str(campaign["id"]))
    recipients = detail.get("recipients") or {}
    try:
        recipient_ids = {int(value) for value in (recipients.get("listIds") or [])}
    except (TypeError, ValueError):
        sys.exit("Invalid recipient list IDs after draft update; no email sent.")
    if recipient_ids != {list_id} or detail.get("status") != "draft":
        sys.exit("Unable to verify updated draft recipient list and status; no email sent.")
    print("Draft recipient list repaired and verified:", list_id)
# Check actual active recipient count; never send to an unverified/empty list.
contacts = api("GET", "/contacts/lists/" + str(list_id))
if int(contacts.get("totalSubscribers", 0)) < 1:
    sys.exit("No confirmed active subscribers; no email sent.")
api("POST", "/emailCampaigns/" + str(campaign["id"]) + "/sendNow")
print(json.dumps({"status": "send_requested", "date": today, "campaign_id": campaign["id"], "recipient_count": contacts.get("totalSubscribers")}))
