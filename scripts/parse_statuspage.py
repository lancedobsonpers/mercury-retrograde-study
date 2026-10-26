"""Flatten raw Statuspage history pages into one row per incident with its UTC start date."""
import json, re, pathlib, collections, pandas as pd
MON = {m: i for i, m in enumerate(["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"], 1)}
MONTHNAME = {m: i for i, m in enumerate(["January","February","March","April","May","June","July","August","September","October","November","December"], 1)}
rx = re.compile(r"^\s*([A-Z][a-z]{2})\s*<var data-var='date'>\s*(\d+)\s*</var>")
rows, bad = [], collections.Counter()
for f in sorted(pathlib.Path("raw/statuspage").glob("*.json")):
    host = f.name.split("_p")[0]
    for m in json.loads(f.read_text())["months"]:
        for inc in m["incidents"]:
            mt = rx.match(inc.get("timestamp", ""))
            if not mt: bad[host] += 1; continue
            mon, day = MON[mt.group(1)], int(mt.group(2)); year = m["year"]
            if mon - MONTHNAME[m["name"]] > 6: year -= 1        # a December start listed under January
            elif MONTHNAME[m["name"]] - mon > 6: year += 1
            rows.append({"provider": host, "code": inc["code"], "date": pd.Timestamp(year, mon, day).date(),
                         "impact": inc.get("impact"), "name": inc.get("name")})
df = pd.DataFrame(rows).drop_duplicates(["provider", "code"])
df.to_csv("out/statuspage_incidents.csv", index=False)
print("unparsed timestamps:", dict(bad))
print(df.groupby("provider").agg(n=("code", "size"), first=("date", "min"), last=("date", "max")).to_string())
print(pd.crosstab(df.provider, df.impact).to_string())
