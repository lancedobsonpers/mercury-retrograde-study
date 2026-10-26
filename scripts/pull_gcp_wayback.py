"""Fetch every monthly Wayback snapshot of status.cloud.google.com/incidents.json (raw, id_ mode)."""
import json, time, urllib.request, pathlib, sys
out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
cdx = "https://web.archive.org/cdx/search/cdx?url=status.cloud.google.com/incidents.json&output=json&filter=statuscode:200&collapse=timestamp:6&fl=timestamp"
ts = [r[0] for r in json.load(urllib.request.urlopen(cdx, timeout=120))[1:]]
for t in ts:
    f = out / f"gcp_{t}.json"
    if f.exists(): continue
    for attempt in range(6):
        try:
            body = urllib.request.urlopen(urllib.request.Request(f"https://web.archive.org/web/{t}id_/https://status.cloud.google.com/incidents.json", headers={"User-Agent": "Mozilla/5.0"}), timeout=120).read()
            json.loads(body); f.write_bytes(body); break
        except Exception as e:
            print(t, "retry", e); time.sleep(10 * (attempt + 1))
    time.sleep(3)
print("snapshots", len(list(out.glob("*.json"))), "of", len(ts))
