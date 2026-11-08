#!/usr/bin/env python3
"""Create a Brevo email-campaign DRAFT from the daily digest. Never sends."""
import argparse
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIGEST = ROOT / "newsletter" / "pending-digest.json"
API = "https://api.brevo.com/v3/emailCampaigns"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--create-draft", action="store_true", help="Create a draft in Brevo; never send")
    parser.add_argument("--skip-existing", action="store_true", help="Avoid duplicate daily drafts")
    args = parser.parse_args()
    if not DIGEST.exists():
        sys.exit("No prepared digest. Run prepare_daily_newsletter.py first.")
    digest = json.loads(DIGEST.read_text(encoding="utf-8"))
    if not digest.get("slugs") or not digest.get("html"):
        sys.exit("Digest has no content; refusing to create an empty campaign.")
    sender = os.environ.get("BREVO_SENDER_EMAIL", "no-reply@deepdocumentary.com")
    list_id = int(os.environ.get("BREVO_LIST_ID", "3"))
    payload = {
        "name": "Deep Documentary Daily " + digest["date"],
        "subject": digest["subject"],
        "sender": {"name": "Deep Documentary", "email": sender},
        "type": "classic",
        "htmlContent": digest["html"],
        "recipients": {"listIds": [list_id]},
    }
    if not args.create_draft:
        print(json.dumps({"mode": "dry-run", "date": digest["date"], "kind": digest["kind"],
                          "articles": digest["slugs"], "recipient_list": list_id,
                          "sender": sender, "note": "No API call; no email sent."},
                         ensure_ascii=False, indent=2))
        return
    key = os.environ.get("BREVO_API_KEY", "")
    if not key:
        sys.exit("BREVO_API_KEY is missing; no campaign created.")
    if args.skip_existing:
        check = urllib.request.Request(API + "?type=classic&status=draft&limit=100&offset=0", headers={"api-key": key, "accept": "application/json"})
        try:
            with urllib.request.urlopen(check, timeout=20) as response:
                existing = json.load(response)
            if any(c.get("name") == payload["name"] for c in existing.get("campaigns", [])):
                print(json.dumps({"status": "existing_draft_skipped", "date": digest["date"], "sent": False}))
                return
        except (urllib.error.URLError, ValueError) as exc:
            sys.exit("Unable to verify existing Brevo drafts; refusing duplicate creation.")
    req = urllib.request.Request(
        API,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"api-key": key, "Content-Type": "application/json", "accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        # Show Brevo's structured error only; never log API keys or request headers.
        raw = exc.read(4096).decode("utf-8", errors="replace")
        try:
            details = json.loads(raw)
        except ValueError:
            details = {}
        safe = {}
        for field in ("code", "message"):
            value = details.get(field)
            if isinstance(value, str):
                safe[field] = value[:300] if "key" not in value.lower() else "[redacted]"
        print(json.dumps({"error": "brevo_draft_creation_failed", "http_status": exc.code,
                          "brevo_response": safe}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError:
        print("Brevo connection failed; no draft created.", file=sys.stderr)
        sys.exit(1)
    campaign_id = result.get("id")
    if not campaign_id:
        sys.exit("Brevo did not return a campaign ID.")
    print(json.dumps({"status": "draft_created", "campaign_id": campaign_id,
                      "date": digest["date"], "sent": False}, ensure_ascii=False))
    # No delivery-state updates here: drafts are NOT sent.

if __name__ == "__main__":
    main()
