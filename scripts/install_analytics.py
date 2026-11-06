"""Install or validate the shared analytics loader on public pages."""
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TAG = b'<script defer src="/assets/analytics.js"></script>'


def add_analytics(html):
    if html.count(TAG) == 1 and html.find(TAG) < html.find(b"</head>"):
        return html
    if TAG in html or html.count(b"</head>") != 1:
        raise ValueError("Expected a single head and at most one analytics loader")
    return html.replace(b"</head>", TAG + b"</head>", 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    missing = []
    for path in sorted([*ROOT.glob("*.html"), *(ROOT / "articles").rglob("*.html")]):
        original = path.read_bytes()
        updated = add_analytics(original)
        if original != updated:
            if args.check:
                missing.append(str(path.relative_to(ROOT)))
            else:
                path.write_bytes(updated)
    if missing:
        parser.exit(1, "Missing analytics loader: " + ", ".join(missing) + "\n")


if __name__ == "__main__":
    main()
