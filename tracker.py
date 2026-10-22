"""
Takes one snapshot of live car park occupancy for Sydney Metro Northwest
stations (Tallawong, Kellyville, Bella Vista, Norwest) from the Transport for
NSW Car Park API and appends it to data/carpark_log.csv.

Run on a schedule by .github/workflows/track.yml. Needs the TFNSW_API_KEY
environment variable (stored as a GitHub Actions secret).
"""

import csv
import json
import os
import sys
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

SYDNEY = ZoneInfo("Australia/Sydney")
STATIONS = ["Tallawong", "Kellyville", "Bella Vista", "Norwest"]
START_HOUR, END_HOUR = 5, 14             # 5:00am to 2:00pm Sydney time
TRACK_DAYS = {0, 1, 2, 3, 4, 5}          # Mon=0 ... Sat=5
STOP_AFTER = datetime(2026, 10, 31, 14, 0, tzinfo=SYDNEY)  # end of tracking week

BASE = "https://api.transport.nsw.gov.au/v1/carpark"
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "carpark_log.csv")
API_KEY = os.environ.get("TFNSW_API_KEY", "")


def get(url):
    req = urllib.request.Request(url, headers={
        "Authorization": f"apikey {API_KEY}",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def to_int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def read_facility(fid):
    d = get(f"{BASE}?facility={fid}")
    total = to_int(d.get("spots"))
    used = to_int((d.get("occupancy") or {}).get("total"))
    if used is None:  # some car parks only report per zone
        vals = [to_int((z.get("occupancy") or {}).get("total")) for z in d.get("zones") or []]
        vals = [v for v in vals if v is not None]
        used = sum(vals) if vals else None
    return total, used


def main():
    now = datetime.now(SYDNEY)
    force = "--force" in sys.argv  # manual test runs ignore the time window

    if not force:
        if now > STOP_AFTER:
            print("Tracking week is over — nothing to do.")
            return
        if now.weekday() not in TRACK_DAYS or not (START_HOUR <= now.hour < END_HOUR):
            print(f"{now:%a %H:%M} is outside the tracking window — skipping.")
            return

    if not API_KEY:
        sys.exit("TFNSW_API_KEY secret is missing.")

    listing = get(BASE)  # {"<id>": "<facility name>", ...}
    rows = []
    for fid, name in listing.items():
        station = next((s for s in STATIONS if s.lower() in str(name).lower()), None)
        if not station:
            continue
        try:
            total, used = read_facility(fid)
        except Exception as e:
            print(f"{name}: error {e}")
            continue
        pct = round(100 * used / total, 1) if total and used is not None else ""
        rows.append([now.strftime("%Y-%m-%d %H:%M"), now.strftime("%a"),
                     station, name, total, used, pct])
        print(f"{name}: {used}/{total} ({pct}%)")

    if not rows:
        sys.exit("No matching car parks returned — check the API key and car park names.")

    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    new = not os.path.exists(LOG)
    with open(LOG, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["timestamp", "weekday", "station", "facility",
                        "total_spaces", "occupied", "percent_full"])
        w.writerows(rows)


if __name__ == "__main__":
    main()
