# Metro Northwest Parking

Tracks how full the commuter car parks at Sydney Metro Northwest stations get — **Tallawong (P1–P3), Kellyville (north and south) and Bella Vista** — and shows which one is most likely to have a space at the time you arrive. (Norwest has no Park&Ride car park in the API.)

**Dashboard:** `index.html`, served with GitHub Pages. Pick an arrival time, days and period; it ranks each station by how often it still had a space, shows the typical fill curve through the day, the time each day filled, and a weekday-by-time heatmap.

## How it works

- **Live tracking** — `.github/workflows/track.yml` fires every 5 minutes. `tracker.py` takes a reading every **5 minutes during weekday peaks (5–10am, 3–7pm Sydney time)** and every **10 minutes at all other times**, and appends it to `data/live.csv`. Sydney time is handled in the script, so daylight-saving changes need no edits.
- **History** — `.github/workflows/backfill.yml` (run by hand) pulls the last 60 days from the API's history endpoint into `data/history.csv`, one reading per car park per 5 minutes.
- Each run commits its new data back to this repo, so nothing needs to stay switched on.

## Data

Both CSVs share one schema:

| column | meaning |
|---|---|
| `time` | Sydney local time, `YYYY-MM-DD HH:MM` |
| `facility_id` | TfNSW facility ID: 26–28 Tallawong P1–P3, 29–30 Kellyville north/south, 31 Bella Vista |
| `spots` | total spaces reported by the feed |
| `occupied` | estimated cars parked (`occupancy.total`) |

## Setup

1. Get an API token from the [TfNSW Open Data Hub](https://opendata.transport.nsw.gov.au) (profile → API Tokens).
2. In this repo: **Settings → Secrets and variables → Actions → New repository secret**, name `TFNSW_API_KEY`, value = the token.
3. **Actions → Backfill past occupancy → Run workflow** to pull the last 60 days.
4. **Actions → Track car park occupancy → Run workflow** once to test live tracking; after that it runs on its own.
5. **Settings → Pages → Deploy from a branch → `main` / root** to publish the dashboard.

## Notes

- GitHub's scheduler is best-effort: runs can be late, and some get skipped at busy times.
- Occupancy is an estimate from the car park counters, so treat space counts as approximate.
- To stop tracking, disable the *Track car park occupancy* workflow in the Actions tab.
- The dashboard source is `dashboard/app.html`; run `./build_index.sh` after editing it to regenerate `index.html`.
