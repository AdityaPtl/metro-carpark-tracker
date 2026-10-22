"""
Takes one snapshot of live occupancy for the Sydney Metro Northwest Park&Ride
car parks (Tallawong P1–P3, Kellyville north/south, Bella Vista) from the
Transport for NSW Car Park API and appends it to data/live.csv.

The workflow fires every 5 minutes. This script keeps a reading every
5 minutes during weekday peaks (5–10am and 3–7pm Sydney time) and every
10 minutes at all other times, skipping runs that come too soon.

Needs the TFNSW_API_KEY environment variable (a GitHub Actions secret).
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
    "26": "Tallawong P1", "27": "Tallawong P2", "28": "Tallawong P3",
    "29": "Kellyville north", "30": "Kellyville south",
    "31": "Bella Vista",
}

PEAKS = [(5 * 60, 10 * 60), (15 * 60, 19 * 60)]   # minutes of day, Mon–Fri
PEAK_GAP, OFFPEAK_GAP = 5, 10                      # minutes between readings

BASE = "https://api.transport.nsw.gov.au/v1/carpark"
HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = os.path.join(HERE, "data", "live.csv")
HEADER = ["time", "facility_id", "spots", "occupied"]
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
    """Return (total_spaces, occupied, message_date) from one feed record."""
    total = to_int(d.get("spots"))
    used = to_int((d.get("occupancy") or {}).get("total"))
    if used is None:  # fall back to summing zones
        vals = [to_int((z.get("occupancy") or {}).get("total")) for z in d.get("zones") or []]
        vals = [v for v in vals if v is not None]
        used = sum(vals) if vals else None
    return total, used, d.get("MessageDate", "")


def is_peak(t):
    m = t.hour * 60 + t.minute
    return t.weekday() < 5 and any(a <= m < b for a, b in PEAKS)


def last_logged():
    """Time of the most recent reading in live.csv, or None."""
    try:
        with open(LIVE, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 200))
            last = f.read().decode("utf-8").strip().splitlines()[-1]
        return datetime.strptime(last.split(",")[0], "%Y-%m-%d %H:%M").replace(tzinfo=SYDNEY)
    except Exception:
        return None


def main():
    now = datetime.now(SYDNEY)
    force = "--force" in sys.argv  # manual runs always take a reading

    gap = PEAK_GAP if is_peak(now) else OFFPEAK_GAP
    prev = last_logged()
    if not force and prev and (now - prev).total_seconds() < (gap - 2) * 60:
        print(f"{now:%a %H:%M}: last reading {prev:%H:%M}, next due in a {gap}-minute gap — skipping.")
        return

    if not API_KEY:
        sys.exit("TFNSW_API_KEY secret is missing.")

    stamp = now.strftime("%Y-%m-%d %H:%M")
    rows = []
    for fid, name in FACILITIES.items():
        try:
            total, used, msg = parse_record(get(f"{BASE}?facility={fid}"))
        except Exception as e:
            print(f"{name}: error {e}")
            continue
        if total is None or used is None:
            print(f"{name}: no occupancy in response")
            continue
        rows.append([stamp, fid, total, used])
        print(f"{name}: {used}/{total}  [feed time {msg}]")

    if not rows:
        sys.exit("No car park data returned — check the TFNSW_API_KEY secret.")

    os.makedirs(os.path.dirname(LIVE), exist_ok=True)
    new = not os.path.exists(LIVE)
    with open(LIVE, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(HEADER)
        w.writerows(rows)


if __name__ == "__main__":
    main()
