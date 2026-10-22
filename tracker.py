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
# Live Park&Ride facility IDs from the TfNSW Car Park API docs (v2.4).
# Norwest has no Park&Ride car park in the API. IDs 1-3 are retired
# "historical only" car parks and are deliberately left out.
FACILITIES = {
    "26": "Tallawong", "27": "Tallawong", "28": "Tallawong",
    "29": "Kellyville", "30": "Kellyville",
    "31": "Bella Vista",
}
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


def parse_record(d):
    """Return (facility_name, total_spaces, occupied, message_date) from one feed record."""
    total = to_int(d.get("spots"))
    used = to_int((d.get("occupancy") or {}).get("total"))
    if used is None:  # fall back to summing zones
        vals = [to_int((z.get("occupancy") or {}).get("total")) for z in d.get("zones") or []]
        vals = [v for v in vals if v is not None]
        used = sum(vals) if vals else None
    return d.get("facility_name", ""), total, used, d.get("MessageDate", "")


def percent(total, used):
    if not total or used is None:
        return ""
    return round(100 * min(used, total) / total, 1)


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

    rows = []
    for fid, station in FACILITIES.items():
        try:
            name, total, used, msg_date = parse_record(get(f"{BASE}?facility={fid}"))
        except Exception as e:
            print(f"Facility {fid}: error {e}")
            continue
        pct = percent(total, used)
        rows.append([now.strftime("%Y-%m-%d %H:%M"), now.strftime("%a"),
                     station, name, total, used, pct])
        print(f"{name}: {used}/{total} ({pct}%)  [feed time {msg_date}]")

    if not rows:
        sys.exit("No car park data returned — check the TFNSW_API_KEY secret.")

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
