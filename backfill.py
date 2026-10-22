"""
Pulls past occupancy from the TfNSW Car Park API history endpoint
(/carpark/history) for the last N days (default 60), keeps one reading per
car park per 5 minutes across the whole day, and writes data/history.csv.

Usage:  python backfill.py [days]
Needs the TFNSW_API_KEY environment variable.
"""

import csv
import json
import os
import sys
from datetime import datetime, timedelta

from tracker import FACILITIES, BASE, SYDNEY, HEADER, API_KEY, get, parse_record

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "history.csv")
SAMPLES = os.path.join(HERE, "data", "history_samples")
BUCKET = 5  # minutes


def records_from(payload):
    """The history response shape isn't documented, so accept a list of
    records, a dict that wraps a list, or a single record."""
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for v in payload.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
        return [payload]
    return []


def parse_time(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s[:26], fmt)
        except ValueError:
            continue
    try:  # ISO with an offset, e.g. ...+11:00 or Z
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(SYDNEY).replace(tzinfo=None)
    except Exception:
        return None


def main():
    if not API_KEY:
        sys.exit("TFNSW_API_KEY secret is missing.")
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    today = datetime.now(SYDNEY).date()
    os.makedirs(SAMPLES, exist_ok=True)

    rows, sampled, empty_days = [], set(), 0
    for back in range(days, 0, -1):  # oldest first
        d = today - timedelta(days=back)
        for fid, name in FACILITIES.items():
            try:
                payload = get(f"{BASE}/history?facility={fid}&eventdate={d.isoformat()}")
            except Exception as e:
                print(f"{d} {name}: error {e}")
                continue

            if fid not in sampled:  # keep one raw response per car park for reference
                with open(os.path.join(SAMPLES, f"facility_{fid}.json"), "w") as f:
                    json.dump(payload, f, indent=1)
                sampled.add(fid)

            buckets = {}  # 5-minute slot -> latest reading in that slot
            for rec in records_from(payload):
                total, used, msg = parse_record(rec)
                t = parse_time(msg)
                if t is None or total is None or used is None or t.date() != d:
                    continue
                slot = t.replace(minute=t.minute - t.minute % BUCKET, second=0, microsecond=0)
                if slot not in buckets or t >= buckets[slot][0]:
                    buckets[slot] = (t, total, used)

            if not buckets:
                empty_days += 1
            for slot in sorted(buckets):
                _, total, used = buckets[slot]
                rows.append([slot.strftime("%Y-%m-%d %H:%M"), fid, total, used])
            print(f"{d} {name}: {len(buckets)} readings")

    rows.sort(key=lambda r: (r[0], r[1]))
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUT} ({empty_days} car-park-days had no data)")


if __name__ == "__main__":
    main()
