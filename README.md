# Does Mercury retrograde predict tech outages?

The code and data behind two pages on lancedobson.com:

- **The plan, published before any data was pulled:** https://lancedobson.com/essays/mercury-retrograde-outages-pre-registration/
- **The results:** https://lancedobson.com/essays/mercury-retrograde-outages-results/

**Verdict:** not supported. No window showed a difference beyond what randomly placed calendars produce, and the retrograde calendar did not help forecast outages in held-out years.

## Reproduce it

Requires Python 3.13 with `numpy`, `pandas` and `skyfield`.

```
python scripts/pull_statuspage.py www.githubstatus.com raw/statuspage   # repeat for each host below
python scripts/pull_gcp_wayback.py raw/gcp_wayback
python scripts/ephemeris.py          # downloads JPL DE440s on first run (~32 MB, not committed)
python scripts/parse_statuspage.py
python scripts/parse_gcp.py
python scripts/analyze.py            # pre-registered tests -> out/results.json
python scripts/explore_signs.py      # exploratory, NOT pre-registered -> out/exploratory_by_sign.csv
PYTHONPATH=scripts python scripts/selftest.py   # method check on simulated data
```

Status-page hosts: `www.githubstatus.com`, `status.digitalocean.com`, `www.redditstatus.com`, `discordstatus.com`, `status.dropbox.com`.

## What's here

- **`raw/statuspage/`** — every page of each provider's public `history.json`, saved untouched (pulled 2026-10-26).
- **`raw/gcp_wayback/`** — Internet Archive snapshots of `status.cloud.google.com/incidents.json`.
- **`out/mercury_calendar.csv`** — one row per day with the retrograde, shadow, station and element flags.
- **`out/mercury_cycles.csv`** — one row per retrograde.
- **`out/statuspage_incidents.csv`, `out/gcp_incidents.csv`** — one row per incident.
- **`out/gcp_coverage.csv`** — the days the Google Cloud snapshots cover.
- **`out/results.json`** — every pre-registered number.

## Known gaps

- **Google Cloud coverage** — the archive rate-limited downloads, so these months are missing and those days are excluded for Google Cloud only:
  - 2015-11 → 2015-12
  - 2017-02 → 2017-05
  - 2022-12 → 2024-04
- **The forecast baseline** — not specified in the plan. It is each provider's mean daily incidents over the previous 365 days.
- **Re-running the pulls today** gives slightly different raw files, because status pages keep adding incidents. The committed `raw/` files are the ones used.
