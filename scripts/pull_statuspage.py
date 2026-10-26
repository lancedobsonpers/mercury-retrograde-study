"""Pull every page of a Statuspage history.json and save it raw, untouched.
Usage: python pull_statuspage.py <host> <outdir>"""
import json, sys, time, urllib.request, pathlib
host, out = sys.argv[1], pathlib.Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
page = 1
while True:
    req = urllib.request.Request(f"https://{host}/history.json?page={page}", headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(5):
        try:
            d = json.load(urllib.request.urlopen(req, timeout=60)); break
        except Exception as e:
            print(host, page, "retry", e); time.sleep(5 * (attempt + 1))
    else:
        sys.exit(f"{host}: gave up on page {page}")
    months = d.get("months", [])
    if not months or all(not m["incidents"] for m in months):
        break
    (out / f"{host}_p{page:03d}.json").write_text(json.dumps(d))
    page += 1
    time.sleep(0.5)
print(host, "pages", page - 1)
