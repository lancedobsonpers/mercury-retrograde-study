"""Runs exactly the pre-registered tests:
https://lancedobson.com/essays/mercury-retrograde-outages-pre-registration/

Estimator: within-cell (provider x calendar month) rate ratio, i.e. the Poisson fixed-effects MLE, solved directly.
Chance check: the whole calendar is circularly slid by a random offset, 10,000 times; two-sided.
Multiple comparisons: Holm within the primary family and within the secondary family.
"""
import json
import numpy as np
import pandas as pd

rng = np.random.default_rng(20261026)
NPERM = 10_000
END = pd.Timestamp("2026-09-30")

cal = pd.read_csv("out/mercury_calendar.csv", parse_dates=["date"]).set_index("date")
PANELS = {
    "long": {"start": "2010-02-01", "providers": ["www.githubstatus.com", "status.digitalocean.com"]},
    "broad": {"start": "2015-10-01", "providers": ["www.githubstatus.com", "status.digitalocean.com",
                                                   "www.redditstatus.com", "discordstatus.com",
                                                   "status.dropbox.com", "status.cloud.google.com"]},
}
def load():
    global inc, gdays, FIRST
    sp = pd.read_csv("out/statuspage_incidents.csv", parse_dates=["date"])
    sp = sp[sp.impact != "maintenance"].copy()
    sp["major"] = sp.impact.isin(["major", "critical"])
    gcp = pd.read_csv("out/gcp_incidents.csv", parse_dates=["date"])
    gcp["major"] = gcp.severity.eq("high")
    gcov = pd.read_csv("out/gcp_coverage.csv", parse_dates=["start", "end"])
    gdays = set()
    for r in gcov.itertuples():
        gdays.update(pd.date_range(r.start, r.end))
    inc = pd.concat([sp[["provider", "date", "major"]], gcp[["provider", "date", "major"]]])

    # Statuspage providers enter from the first month of their history.
    FIRST = inc.groupby("provider").date.min().dt.to_period("M").dt.start_time




def panel_days(name, major=False):
    p = PANELS[name]
    dates = pd.date_range(p["start"], END)
    frames = []
    for prov in p["providers"]:
        d = dates[dates >= FIRST[prov]]
        if prov == "status.cloud.google.com":
            d = d[d.isin(gdays)]
        sub = inc[inc.provider == prov]
        if major:
            sub = sub[sub.major]
        y = sub.groupby("date").size().reindex(d, fill_value=0)
        frames.append(pd.DataFrame({"provider": prov, "date": d, "y": y.to_numpy()}))
    return pd.concat(frames, ignore_index=True), dates


def solve_many(y_in, N, a, b):
    """Poisson FE MLE of log rate ratio, vectorised over rows (permutations) x cells.
    Solves sum_c y_in_c = sum_c N_c a_c t / (a_c t + b_c) by bisection."""
    y_in, N, a, b = map(np.atleast_2d, (y_in, N, a, b))
    k = (a > 0) & (b > 0) & (N > 0)
    lo = np.full(a.shape[0], -6.0)
    hi = np.full(a.shape[0], 6.0)
    target = np.where(k, y_in, 0).sum(1)
    for _ in range(50):
        mid = (lo + hi) / 2
        t = np.exp(mid)[:, None]
        f = np.where(k, N * a * t / (a * t + b), 0).sum(1) - target
        lo, hi = np.where(f < 0, mid, lo), np.where(f < 0, hi, mid)
    return (lo + hi) / 2


def run(df, dates, w_full, keep_full=None, label=""):
    """w_full / keep_full are boolean arrays over the panel calendar `dates`."""
    T = len(dates)
    pos = (df.date - dates[0]).dt.days.to_numpy()
    cell = pd.factorize(df.provider.astype(str) + "|" + df.date.dt.to_period("M").astype(str))[0]
    C = cell.max() + 1
    y = df.y.to_numpy().astype(float)
    keep_all = np.ones(T, bool) if keep_full is None else keep_full

    def agg(w, keep):
        ww, kk = w[pos], keep[pos]
        return (np.bincount(cell, y * ww * kk, C), np.bincount(cell, y * kk, C),
                np.bincount(cell, ww * kk, C), np.bincount(cell, (~ww) * kk, C))

    yin, N, a, b = agg(w_full, keep_all)
    lt = float(solve_many(yin, N, a, b)[0])
    t = np.exp(lt)
    # Wald interval on log rate ratio, inflated for overdispersion (Pearson)
    k = (a > 0) & (b > 0) & (N > 0)
    info = (N * a * b * t / (a * t + b) ** 2)[k].sum()
    ww, kk = w_full[pos], keep_all[pos]
    denom = a[cell] * t + b[cell]
    mu = np.where(ww, N[cell] * t, N[cell]) / np.where(denom > 0, denom, 1)
    m = kk & k[cell] & (mu > 0)
    phi = max(1.0, (((y - mu) ** 2 / np.where(mu > 0, mu, 1))[m]).sum() / max(1, m.sum() - k.sum() - 1))
    se = np.sqrt(phi / info)
    # Chance check: slide the whole calendar (and the keep-mask with it) by a random offset
    offs = rng.integers(1, T, NPERM)
    perm = np.empty(NPERM)
    for s in range(0, NPERM, 250):
        parts = [agg(np.roll(w_full, o), np.roll(keep_all, o)) for o in offs[s:s + 250]]
        perm[s:s + 250] = solve_many(*[np.array([p[i] for p in parts]) for i in range(4)])
    p = (np.sum(np.abs(perm) >= abs(lt)) + 1) / (NPERM + 1)
    return {"test": label, "rate_ratio": round(t, 4), "pct_diff": round(100 * (t - 1), 1),
            "ci95_low_pct": round(100 * (np.exp(lt - 1.96 * se) - 1), 1),
            "ci95_high_pct": round(100 * (np.exp(lt + 1.96 * se) - 1), 1),
            "p_perm": round(float(p), 4),
            "raw_per_day_in": round(float((y * ww * kk).sum() / max(1, (ww * kk).sum())), 4),
            "raw_per_day_out": round(float((y * (~ww) * kk).sum() / max(1, ((~ww) * kk).sum())), 4),
            "days_in_window": int((ww * kk).sum()), "incidents_used": int((y * kk).sum())}


def holm(ps):
    ps = np.asarray(ps)
    order = np.argsort(ps)
    m = len(ps)
    adj = np.empty(m)
    running = 0.0
    for i, j in enumerate(order):
        running = max(running, min(1.0, (m - i) * ps[j]))
        adj[j] = running
    return adj


def cal_arr(dates, col):
    return cal[col].reindex(dates).fillna(False).to_numpy().astype(bool)


if __name__ == "__main__":
    load()
    results = {"primary": [], "secondary": []}

    for pn in ["long", "broad"]:
        df, dates = panel_days(pn)
        for wn in ["retro", "shadow"]:
            results["primary"].append(run(df, dates, cal_arr(dates, wn), label=f"{pn} | {wn} | all incidents"))
            print("done", pn, wn, flush=True)

    for pn in ["long", "broad"]:
        df, dates = panel_days(pn)
        dfm, _ = panel_days(pn, major=True)
        anyday = (df.groupby("date").y.sum().gt(0).astype(int).reindex(dates, fill_value=0)
                  .rename("y").reset_index().rename(columns={"index": "date"}).assign(provider="any"))
        retro = cal_arr(dates, "retro")
        for wn in ["retro", "shadow"]:
            w = cal_arr(dates, wn)
            results["secondary"].append(run(dfm, dates, w, label=f"{pn} | {wn} | major+critical"))
            results["secondary"].append(run(anyday, dates, w, label=f"{pn} | {wn} | cascade: days with any incident"))
        results["secondary"].append(run(df, dates, cal_arr(dates, "station"), label=f"{pn} | station days ±3 | all incidents"))
        pre, post = cal_arr(dates, "pre_shadow"), cal_arr(dates, "post_shadow")
        results["secondary"].append(run(df, dates, pre, keep_full=~retro & ~post, label=f"{pn} | pre-shadow vs outside shadow | all incidents"))
        results["secondary"].append(run(df, dates, post, keep_full=~retro & ~pre, label=f"{pn} | post-shadow vs outside shadow | all incidents"))
        el = cal["element"].reindex(dates).fillna("").to_numpy()
        for e in ["fire", "earth", "air", "water"]:
            w = retro & (el == e)
            results["secondary"].append(run(df, dates, w, keep_full=~retro | w, label=f"{pn} | retro in {e} sign | all incidents"))
        print("done secondary", pn, flush=True)

    for fam in ["primary", "secondary"]:
        for r, a in zip(results[fam], holm([r["p_perm"] for r in results[fam]])):
            r["p_holm"] = round(float(a), 4)


    # Predictive test: long panel. Train 2010-2020, forecast each day of 2021-01-01..2026-09-30.
    # Baseline forecast = provider's mean daily incidents over the previous 365 days.
    # With-calendar forecast = baseline x (rate ratio learned on 2010-2020) inside the window, rescaled so the
    # overall level is unchanged. Score = mean Poisson log-likelihood gain per provider-day on the held-out years.
    def predictive(wn, nperm=NPERM):
        df, dates = panel_days("long")
        df = df.sort_values(["provider", "date"]).reset_index(drop=True)
        df["base"] = df.groupby("provider").y.transform(lambda s: s.shift(1).rolling(365, min_periods=180).mean())
        pos = (df.date - dates[0]).dt.days.to_numpy()
        tr = (df.date <= "2020-12-31").to_numpy()
        te = ((df.date >= "2021-01-01") & df.base.gt(0)).to_numpy()
        cell = pd.factorize(df.provider + "|" + df.date.dt.to_period("M").astype(str))[0]
        C = cell.max() + 1
        y = df.y.to_numpy().astype(float)
        mu0 = df.base.to_numpy()[te]
        yte = y[te]
        ll0 = yte * np.log(mu0) - mu0

        def gain(w):
            ww = w[pos]
            lt = solve_many(np.bincount(cell, y * ww * tr, C), np.bincount(cell, y * tr, C),
                            np.bincount(cell, ww * tr, C), np.bincount(cell, (~ww) * tr, C))[0]
            f = np.where(ww[te], np.exp(lt), 1.0)
            mu1 = mu0 * f / f.mean()
            return float(((yte * np.log(mu1) - mu1) - ll0).mean()), float(np.exp(lt))

        w0 = cal_arr(dates, wn)
        g, t = gain(w0)
        gp = np.array([gain(np.roll(w0, o))[0] for o in rng.integers(1, len(dates), nperm)])
        beaten = float((g > gp).mean())
        return {"window": wn, "train_rate_ratio_2010_2020": round(t, 4), "heldout_loglik_gain_per_day": round(g, 6),
                "share_of_slid_calendars_beaten": round(beaten, 4), "predictive_by_preregistered_rule": beaten >= 0.95}


    results["predictive"] = [predictive("retro"), predictive("shadow")]
    json.dump(results, open("out/results.json", "w"), indent=1, default=str)
    pd.set_option("display.width", 250)
    for fam in ["primary", "secondary"]:
        print(f"\n== {fam} ==")
        print(pd.DataFrame(results[fam]).to_string(index=False))
    print("\n== predictive ==")
    print(pd.DataFrame(results["predictive"]).to_string(index=False))
