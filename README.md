# Metro Car Park Tracker

Tracks how full the commuter car parks at Sydney Metro Northwest stations get each morning — **Tallawong (P1–P3), Kellyville (north and south) and Bella Vista** — to work out which station gives the best chance of a park before work. (Norwest has no Park&Ride car park in the API.)

## How it works

- A GitHub Actions workflow runs every 10 minutes, **5:00am–2:00pm, Monday to Saturday** (Sydney time).
- Each run calls the [Transport for NSW Car Park API](https://opendata.transport.nsw.gov.au) and appends a snapshot to [`data/carpark_log.csv`](data/carpark_log.csv).
- The new data is committed back to this repo automatically, so it runs with no computer switched on.
- Tracking stops automatically after Saturday 31 October 2026.
- **Backfill:** the *Backfill past occupancy* workflow pulls past weeks from the API's history endpoint into [`data/history_log.csv`](data/history_log.csv), so there's data to compare straight away.

## Data

| column | meaning |
|---|---|
| `timestamp` | Sydney local time of the snapshot |
| `weekday` | day of week |
| `station` | metro station |
| `facility` | car park name as reported by TfNSW |
| `total_spaces` | capacity |
| `occupied` | cars parked |
| `percent_full` | occupied ÷ capacity |

## Setup

1. Get a free API key from the TfNSW Open Data Hub and enable the **Car Park API** for it.
2. In this repo: **Settings → Secrets and variables → Actions → New repository secret**, name it `TFNSW_API_KEY`.
3. **Actions → Track car park occupancy → Run workflow** to test it straight away.
4. **Actions → Backfill past occupancy → Run workflow** to pull the last 4 weeks.

## Notes

- GitHub's scheduler is best-effort: runs can be a few minutes late, and occasionally one gets skipped at busy times.
- The cron times assume Sydney daylight saving (UTC+11). Shift each hour by +1 outside daylight saving.
- Facility IDs come from the TfNSW Car Park API docs v2.4: 26–28 Tallawong, 29–30 Kellyville, 31 Bella Vista.
