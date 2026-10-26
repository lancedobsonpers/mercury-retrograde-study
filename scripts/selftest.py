"""Check the estimator on SIMULATED data with a known effect before touching the real counts.
Uses the real calendar but fake outage counts, so it says nothing about the real result."""
import time
import numpy as np
import pandas as pd
import analyze as A

rng = np.random.default_rng(1)
dates = pd.date_range("2010-02-01", "2026-09-30")
w = A.cal_arr(dates, "retro")
for true_pct in [0, 30]:
    rows = []
    for prov, base in [("p1", 0.4), ("p2", 1.2)]:
        trend = np.linspace(0.5, 2.0, len(dates))           # growth over time, which the estimator must not mistake for an effect
        mu = base * trend * np.where(w, 1 + true_pct / 100, 1.0)
        y = rng.negative_binomial(2, 2 / (2 + mu))           # overdispersed counts
        rows.append(pd.DataFrame({"provider": prov, "date": dates, "y": y}))
    df = pd.concat(rows, ignore_index=True)
    t0 = time.time()
    r = A.run(df, dates, w, label=f"simulated true effect {true_pct}%")
    print(r, f"{time.time() - t0:.1f}s")
