#!/usr/bin/env python3
"""Send exactly one approved-format daily Brevo campaign; fail closed on uncertainty."""
import argparse
import datetime as dt
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

parser = argparse.ArgumentParser()
parser.add_argument("--verify-only", action="store_true", help="Check existing Brevo campaign without changing or sending it")
args = parser.parse_args()
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
# Brevo's campaign-detail response represents recipient lists as
# recipients.lists = [{"id": 3, "name": "..."}], while campaign creation
# and updates use recipients.listIds = [3]. Accept both response shapes.
detail = api("GET", "/emailCampaigns/" + str(campaign["id"]))
recipients = detail.get("recipients") or {}

def recipient_list_ids(value):
    ids = set()
    if not isinstance(value, dict):
        return ids
    for entry in (value.get("listIds") or []) + (value.get("lists") or []):
        raw = entry.get("id") if isinstance(entry, dict) else entry
        try:
            ids.add(int(raw))
        except (TypeError, ValueError):
            sys.exit("Unrecognized recipient list ID; no email sent.")
    return ids

recipient_ids = recipient_list_ids(recipients)
if recipient_ids != {list_id}:
    # Only repair a draft if Brevo reports no recipient targeting at all.
    if recipient_ids or recipients.get("exclusionListIds") or recipients.get("segmentIds") or recipients.get("segments"):
        sys.exit("Draft has unexpected recipient targeting; refusing to modify or send.")
    if args.verify_only:
        print("VERIFY_ONLY: no recipient lists found; draft needs repair. No changes made.")
        sys.exit(1)
    api("PUT", "/emailCampaigns/" + str(campaign["id"]), {"recipients": {"listIds": [list_id]}})
    detail = api("GET", "/emailCampaigns/" + str(campaign["id"]))
    recipients = detail.get("recipients") or {}
    recipient_ids = recipient_list_ids(recipients)
    if recipient_ids != {list_id} or detail.get("status") != "draft":
        print("Brevo recipient verification:", {"recipient_keys": sorted(recipients.keys()), "list_ids": sorted(recipient_ids), "status": detail.get("status")}, file=sys.stderr)
        sys.exit("Unable to verify updated draft recipient list and status; no email sent.")
    print("Draft recipient list repaired and verified:", list_id)
else:
    print("Brevo recipient list verified:", list_id)
if detail.get("status") != "draft":
    sys.exit("Campaign no longer a draft; no email sent.")
# Check actual active recipient count; never send to an unverified/empty list.
contacts = api("GET", "/contacts/lists/" + str(list_id))
if int(contacts.get("totalSubscribers", 0)) < 1:
    sys.exit("No confirmed active subscribers; no email sent.")
if args.verify_only:
    print(json.dumps({"status": "verified_without_sending", "campaign_id": campaign["id"], "list_id": list_id, "recipient_count": contacts.get("totalSubscribers")}))
    sys.exit(0)
api("POST", "/emailCampaigns/" + str(campaign["id"]) + "/sendNow")
print(json.dumps({"status": "send_requested", "date": today, "campaign_id": campaign["id"], "recipient_count": contacts.get("totalSubscribers")}))
