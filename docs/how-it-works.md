# How it works

This page explains the design decisions behind the tracker and exactly how the dashboard calculates each figure.

## 1. Getting the data

The [TfNSW Car Park API](https://opendata.transport.nsw.gov.au) has three endpoints this project uses:

| Endpoint | Used for |
|---|---|
| `GET /v1/carpark?facility=<id>` | the current occupancy of one car park (`tracker.py`) |
| `GET /v1/carpark/history?facility=<id>&eventdate=YYYY-MM-DD` | every update for one car park on one past day (`backfill.py`) |
| `GET /v1/carpark` | lists facility names and IDs (used once, to find the IDs) |

Requests send the token as `Authorization: apikey <token>`.

From each response the tracker keeps `spots` (capacity) and `occupancy.total` (estimated cars parked). TfNSW's documentation recommends `total` as the most accurate occupancy figure and availability as `spots − total`, shown with "~" because it's an estimate. If a response has no top-level total, the script sums the zones instead.

### Why fixed facility IDs

The facility list contains older entries for the same stations (IDs 1–3, "Tallawong Station Car Park" and so on) that are marked *historical only*. Matching car parks by name would pick those up and mix stale data in, so the tracker uses the live Park&Ride IDs from the documentation: 26–28 Tallawong, 29–30 Kellyville, 31 Bella Vista.

## 2. Collecting it without a server

GitHub Actions can run a workflow on a schedule and push commits back to the repo, which makes it a free, always-on collector for a small project like this.

- `track.yml` fires every 5 minutes (GitHub's shortest schedule).
- `tracker.py` decides whether a reading is due. During weekday peaks (5–10am and 3–7pm Sydney time) it wants one every 5 minutes; otherwise every 10 minutes. It compares the current time with the last line of `data/live.csv` and skips the run if the previous reading is too recent.
- Doing the time logic in the script with `zoneinfo("Australia/Sydney")` instead of in UTC cron expressions means daylight-saving changes need no edits.
- Runs share a concurrency group, and each commit does `git pull --rebase` before pushing, so overlapping runs don't clash.

`backfill.yml` is run by hand. It asks the history endpoint for each car park for each of the last 60 days, keeps the latest update in every 5-minute slot, and writes `data/history.csv`. One raw response per car park is saved in `data/history_samples/` for reference, since the history response format isn't documented.

## 3. Turning readings into a grid

The dashboard loads both CSVs and builds, for each car park and date, an array of 288 five-minute slots holding the occupied count. A reading is carried forward into following empty slots for up to 30 minutes (so 10-minute off-peak readings fill the gap between them), but no further, so a long outage shows as missing data instead of a flat line.

**Station view** adds up a station's car parks slot by slot: Tallawong = P1 + P2 + P3. A slot only counts if every car park at that station has a value, so a missing car park can't make a station look emptier than it was.

## 4. The figures

With *full threshold* `F` (90% or 98%), *arrival time* `A` and the selected days:

| Figure | Calculation |
|---|---|
| **% of days with a space** | of the selected days with a reading at `A`, the share where occupancy at `A` was below `F` |
| **Spaces left (typical)** | median of `spots − occupied` at `A` across those days |
| **Usually full by** | for each day, the first slot from 4am where occupancy ≥ `F`; the median across days that filled. Shown as "Rarely" if fewer than half the days filled |
| **Arrive by (9 in 10 days)** | the latest slot from 4am such that every slot up to it had occupancy below `F` on at least 90% of days |
| **Best bet** | highest % of days with a space; ties broken by more typical spaces left |
| **Daily curve** | median occupancy % across the selected days, per slot |
| **Heatmap** | median occupancy % per weekday and 30-minute block, across the selected period (ignores the day filter, since each weekday is its own row) |

Medians are used throughout so one unusual day (a public holiday, a counter fault) doesn't drag the result around the way an average would.

The verdict colours: **Good** when a space was found on at least 90% of days, **Risky** at 50–90%, **Usually full** below 50%. Each comes with an icon and a label so it doesn't rely on colour alone.

Full is 98% rather than 100% by default because the counters are estimates and often plateau a few cars short of capacity when the car park is effectively full. The 90% option matches TfNSW's own "almost full" guidance.

## 5. The app

The dashboard is a single HTML file with no frameworks or build step: plain JavaScript and hand-drawn SVG charts. `build_index.sh` wraps it into `index.html` with a web-app manifest and a service worker, which makes the GitHub Pages site installable on a phone's home screen. The service worker fetches the newest page and data when online and falls back to the last copy it saved when offline.

Choices in the page itself: it follows the device's light or dark theme, works down to phone width, supports keyboard reading of the chart (arrow keys), and remembers your filters in the browser.
