"""Fetch visitor counts per country from GoatCounter and save them for the visitor map.

Runs in GitHub Actions before each build (and once a day). Needs the secret
GOATCOUNTER_TOKEN (a GoatCounter API key with only "Read statistics").
Writes static/data/visitors.json. If anything fails, the old file is kept.
"""
import json
import os
import sys
import urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

SITE = "https://ausmlab.goatcounter.com"
START = "2026-10-12T00:00:00Z"  # the day counting began
OUT = Path(__file__).resolve().parent.parent / "static" / "data" / "visitors.json"


def get(path, token):
    req = urllib.request.Request(SITE + path, headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    token = os.environ.get("GOATCOUNTER_TOKEN", "").strip()
    if not token:
        print("fetch_visitors: no GOATCOUNTER_TOKEN, keeping the old file")
        return
    end = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        loc = get(f"/api/v0/stats/locations?start={START}&end={end}&limit=250", token)
        tot = get(f"/api/v0/stats/total?start={START}&end={end}", token)
    except urllib.error.HTTPError as e:
        print("fetch_visitors: failed:", e, e.read()[:300])
        return
    except Exception as e:  # never break the site build
        print("fetch_visitors: failed:", e)
        return
    countries = [{"id": s.get("id", "").lower(), "name": s.get("name", ""), "count": s.get("count", 0)}
                 for s in loc.get("stats", []) if s.get("id")]
    data = {"since": START[:10], "updated": end[:10], "total": tot.get("total", sum(c["count"] for c in countries)),
            "countries": countries}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, separators=(",", ":")))
    print(f"fetch_visitors: {data['total']} visits from {len(countries)} countries")


if __name__ == "__main__":
    sys.exit(main())
