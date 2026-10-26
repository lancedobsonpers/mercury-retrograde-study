"""Mercury retrograde calendar from JPL DE440s, daily at 12:00 UTC.
Writes out/mercury_calendar.csv (one row per day) and out/mercury_cycles.csv (one row per retrograde)."""
import numpy as np, pandas as pd
from skyfield.api import Loader
from skyfield.framelib import ecliptic_frame
load = Loader("raw/ephemeris")
eph = load("de440s.bsp"); ts = load.timescale()
earth, mercury = eph["earth"], eph["mercury"]
days = pd.date_range("2009-01-01", "2026-12-31", freq="D")
t = ts.utc(days.year.to_numpy(), days.month.to_numpy(), days.day.to_numpy(), 12)
lat, lon, _ = earth.at(t).observe(mercury).apparent().frame_latlon(ecliptic_frame)
L = np.unwrap(np.radians(lon.degrees)); L = np.degrees(L)          # continuous longitude
retro = np.r_[False, np.diff(L) < 0]
cal = pd.DataFrame({"date": days.date, "lon": lon.degrees, "L": L, "retro": retro})
SIGNS = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]
ELEM = {"Aries":"fire","Leo":"fire","Sagittarius":"fire","Taurus":"earth","Virgo":"earth","Capricorn":"earth",
        "Gemini":"air","Libra":"air","Aquarius":"air","Cancer":"water","Scorpio":"water","Pisces":"water"}
r = cal["retro"].to_numpy()
starts = np.where(r & ~np.r_[False, r[:-1]])[0]           # first retrograde day = station retrograde
ends = np.where(~r & np.r_[False, r[:-1]])[0]              # first direct day   = station direct
cycles = []
for s in starts:
    e = ends[ends > s]
    if not len(e): continue
    e = e[0]
    L_sr, L_sd = L[s - 1], L[e - 1]                          # longitude at the two turning points
    pre = s - 1
    while pre > 0 and L[pre - 1] >= L_sd: pre -= 1             # walk back to where Mercury first reached the SD degree
    post = e
    while post < len(L) - 1 and L[post] < L_sr: post += 1      # walk forward until it passes the SR degree
    sign = SIGNS[int((cal.lon[s - 1] % 360) // 30)]
    cycles.append({"station_retro": days[s].date(), "station_direct": days[e].date(),
                   "pre_shadow_start": days[pre].date(), "post_shadow_end": days[post].date(),
                   "sign_at_station_retro": sign, "element": ELEM[sign]})
cyc = pd.DataFrame(cycles)
cal["shadow"] = False; cal["pre_shadow"] = False; cal["post_shadow"] = False; cal["station"] = False; cal["element"] = ""
d = pd.to_datetime(cal.date)
for c in cyc.itertuples():
    sr, sd = pd.Timestamp(c.station_retro), pd.Timestamp(c.station_direct)
    ps, pe = pd.Timestamp(c.pre_shadow_start), pd.Timestamp(c.post_shadow_end)
    cal.loc[(d >= ps) & (d <= pe), "shadow"] = True
    cal.loc[(d >= ps) & (d < sr), "pre_shadow"] = True
    cal.loc[(d >= sd) & (d <= pe), "post_shadow"] = True
    for st in (sr, sd):
        cal.loc[(d >= st - pd.Timedelta(days=3)) & (d <= st + pd.Timedelta(days=3)), "station"] = True
    cal.loc[(d >= sr) & (d < sd), "element"] = c.element
cal.to_csv("out/mercury_calendar.csv", index=False); cyc.to_csv("out/mercury_cycles.csv", index=False)
print(len(cyc), "cycles"); print(cyc.tail(6).to_string())
print("share retro", cal.retro.mean().round(3), "share shadow", cal.shadow.mean().round(3))
