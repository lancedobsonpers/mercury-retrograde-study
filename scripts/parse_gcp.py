"""Union all Wayback snapshots of Google Cloud incidents.json into one incident table plus coverage intervals.
A snapshot only lists a rolling window, so GCP counts are only used on days that some snapshot covers:
from the earliest incident begin in that snapshot to the snapshot's capture date."""
import json, pathlib, pandas as pd
inc, cov = {}, []
for f in sorted(pathlib.Path("raw/gcp_wayback").glob("*.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    if not d: continue
    cap = pd.Timestamp(f.stem.split("_")[1][:8]).date()
    begins = [pd.Timestamp(x["begin"]).tz_convert("UTC").date() if pd.Timestamp(x["begin"]).tzinfo else pd.Timestamp(x["begin"]).date() for x in d]
    lo = min(begins); hi = max(cap, max(begins))
    cov.append((lo, hi))
    for x, b in zip(d, begins):
        key = x.get("id") or x.get("number")
        inc[key] = {"provider": "status.cloud.google.com", "code": key, "date": b, "severity": x.get("severity"), "name": x.get("external_desc", "")[:120]}
df = pd.DataFrame(inc.values()); df.to_csv("out/gcp_incidents.csv", index=False)
c = pd.DataFrame(cov, columns=["start", "end"]).sort_values("start"); c.to_csv("out/gcp_coverage.csv", index=False)
days = set()
for r in c.itertuples(): days.update(pd.date_range(r.start, r.end).date)
print(len(df), "incidents", df.date.min(), df.date.max(), "| covered days", len(days))
allm = pd.period_range("2015-10", "2026-09", freq="M"); covm = {pd.Period(x, "M") for x in days}
print("months with no coverage:", [str(m) for m in allm if m not in covm])
print(df.severity.value_counts().to_dict())
