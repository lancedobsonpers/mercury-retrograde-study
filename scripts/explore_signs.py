"""EXPLORATORY (not pre-registered): retrograde vs. outside, split by the sign Mercury turns retrograde in."""
import numpy as np, pandas as pd
import analyze as A
A.NPERM = 2000
A.load()
cyc = pd.read_csv("out/mercury_cycles.csv", parse_dates=["station_retro", "station_direct"])
rows = []
for pn in ["long", "broad"]:
    df, dates = A.panel_days(pn)
    retro = A.cal_arr(dates, "retro")
    for sign in ["Aries","Taurus","Gemini","Cancer","Leo","Virgo","Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"]:
        w = np.zeros(len(dates), bool)
        c = cyc[(cyc.sign_at_station_retro == sign) & (cyc.station_retro >= dates[0]) & (cyc.station_direct <= dates[-1])]
        for r in c.itertuples():
            w |= (dates >= r.station_retro) & (dates < r.station_direct)
        if not w.any(): continue
        res = A.run(df, dates, w, keep_full=~retro | w, label=f"{pn} | {sign}")
        res["retrogrades"] = len(c); rows.append(res)
out = pd.DataFrame(rows)
out["p_holm_within_panel"] = out.groupby(out.test.str.split(" | ").str[0]).p_perm.transform(lambda s: A.holm(s.to_numpy()))
out.to_csv("out/exploratory_by_sign.csv", index=False)
print(out[["test","retrogrades","pct_diff","ci95_low_pct","ci95_high_pct","p_perm","p_holm_within_panel"]].to_string(index=False))
