"""
Pulls past occupancy from the TfNSW Car Park API history endpoint
(/carpark/history) for the last N days, keeps Monday–Saturday 5:00am–2:00pm,
and writes one reading per car park per 10 minutes to data/history_log.csv.

Usage:  python backfill.py [days]     (default 28)
Needs the TFNSW_API_KEY environment variable.
"""

import csv
import json
import os
import sys
from datetime import date, datetime, timedelta

from tracker import (FACILITIES, BASE, SYDNEY, START_HOUR, END_HOUR,
                     TRACK_DAYS, API_KEY, get, parse_record, percent)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "history_log.csv")
SAMPLES = os.path.join(HERE, "data", "history_samples")


def records_from(payload):
    """The history feed's exact shape isn't documented, so accept a list of
    records, or a dict that wraps a list, or a single record."""
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        for v in payload.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
        return [payload]
    return []


def parse_time(s):
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s[:26], fmt)
        except (TypeError, ValueError):
            continue
    try:  # ISO with an offset, e.g. ...+11:00 or Z
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(SYDNEY).replace(tzinfo=None)
    except Exception:
        return None


def main():
    if not API_KEY:
        sys.exit("TFNSW_API_KEY secret is missing.")
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 28
    today = datetime.now(SYDNEY).date()
    os.makedirs(SAMPLES, exist_ok=True)

    rows, sampled = [], set()
    for back in range(1, days + 1):
        d = today - timedelta(days=back)
        if d.weekday() not in TRACK_DAYS:
            continue
        for fid, station in FACILITIES.items():
            try:
                payload = get(f"{BASE}/history?facility={fid}&eventdate={d.isoformat()}")
            except Exception as e:
                print(f"{d} facility {fid}: error {e}")
                continue

            if fid not in sampled:  # keep one raw response per car park for reference
                with open(os.path.join(SAMPLES, f"facility_{fid}_{d}.json"), "w") as f:
                    json.dump(payload, f, indent=1)
                sampled.add(fid)

            buckets = {}  # 10-minute slot -> latest reading in that slot
            for rec in records_from(payload):
                name, total, used, msg = parse_record(rec)
                t = parse_time(msg)
                if t is None or used is None or not (START_HOUR <= t.hour < END_HOUR):
                    continue
                slot = t.replace(minute=t.minute - t.minute % 10, second=0, microsecond=0)
                buckets[slot] = (t, name, total, used)

            for slot in sorted(buckets):
                _, name, total, used = buckets[slot]
                rows.append([slot.strftime("%Y-%m-%d %H:%M"), slot.strftime("%a"),
                             station, name, total, used, percent(total, used)])
            print(f"{d} {station} ({fid}): {len(buckets)} readings")

    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "weekday", "station", "facility",
                    "total_spaces", "occupied", "percent_full"])
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    main()
