# -*- coding: utf-8 -*-
"""USREG-C 批（C3～C8）獨立查核：用另寫的程式（⛔ 不呼叫 book／rank_tables／period_ret／wealth／plans／W_vt）重算抽樣值，對各件產出；結果寫 resultsUSC/check.json。

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSC_check

 X8 C8：原格 s40_L20 QLD 國庫券，每個月初的 w ＝ min(1, 0.40 ÷ σ̂)（σ̂ 用 pandas 自算：t−1 以前 20 個有效日報酬 sd×√252；2007-04-02 前用合成）對 W_vt 結果。
 X7 C7：每個標的抽 25 個起點，L、D、B 三法的 36 個月期末財富用逐日迴圈另算（現金按 DTB3 逐日計息、買進扣 0.05%）對 c7_starts_*.pkl。
 X3 C3：抽 12 個換股日，MOM 用逐股迴圈另算（錨點、5 根有效、⛔ 跨斷點）⇒ 前 10% 集合對 rank_tables 的進場名單。
 X5 C5：抽 12 個換股日，SEAS 逐股另算 ⇒ 前 10% 集合對進場名單。
 X6 C6：抽 40 個（股, 月），CBOP 直接讀 b33bde6 CSV 另算（filed ＜ 換股日、同期取最早 filed、近 4 季間隔 60～120 天、最新季距換股日 ≤ 200 天）對 scores()（代號重用分段股不抽）。
 X4 C4：抽 20 個事件，252 日超額另算（個股 開盤→收盤、^SP500TR 開→收）對 c4_events.pkl。
"""
from __future__ import annotations

import os
import time

import numpy as np
import pandas as pd

from backtest import researchUSC as K


def x8():
    from backtest import researchUSC_c8 as C8
    from backtest import researchUSA1_data as A
    M = C8.setup(); cal = M["cal"]; N = len(cal); P = M["pos"]
    G, I, SGM, lev_of = C8.sigmas(M)
    ms = np.zeros(N, bool); ms[1:] = I["me"][:-1]
    W, wv = C8.W_vt(ms, SGM[("QLD", 20)], 40, "b")
    e0 = P["2007-04-02"]
    diff = 0; tot = 0
    for name, lo, hi in (("SYN_QLD", 0, e0), ("QLD", e0, N)):
        c = pd.Series(M["C"][name]); v = c.notna().to_numpy()
        idx = np.flatnonzero(v); rr = pd.Series(c.to_numpy()[idx][1:] / c.to_numpy()[idx][:-1] - 1, index=idx[1:])
        sd = rr.rolling(20).std(ddof=1) * np.sqrt(252)
        for t in np.flatnonzero(ms):
            if not (lo <= t < hi):
                continue
            s_ = sd[sd.index <= t - 1]
            if not len(s_) or not np.isfinite(s_.iloc[-1]):
                continue
            w = min(1.0, 0.40 / s_.iloc[-1]); tot += 1
            diff += int(abs(w - wv[t]) > 1e-12)
    return {"件": "C8", "項": "原格每月初 w", "抽樣": tot, "不同": diff}


def x7(nper=25, seed=20261011):
    from backtest import researchUSC_c7 as C7
    from backtest import researchUSA1_data as A
    M = C7.setup(); cal = M["cal"]; g = M["cash_g"]
    rng = np.random.default_rng(seed); tot = diff = 0; worst = 0.0
    d = pd.to_datetime(pd.Series(cal)); ymv = (d.dt.year * 12 + d.dt.month - 1).to_numpy()
    for k in C7.TGT:
        df = pd.read_pickle(os.path.join(K.WORK, f"c7_starts_{k}.pkl")); df = df[df["h"] == 36].reset_index(drop=True)
        key = {"TR": "TR", "QQQ": "QQQ", "SSO": "SSO_SP", "QLD": "QLD"}[k]
        o = M["O"][key]; c = M["C"][key]
        ok = np.isfinite(o) & np.isfinite(c) & (o > 0) & (c > 0)
        cf = pd.Series(np.where(ok, c, np.nan)).ffill().to_numpy()
        for i in rng.choice(len(df), size=min(nper, len(df)), replace=False):
            r = df.iloc[int(i)]
            mk = int(r["起點"][:4]) * 12 + int(r["起點"][5:7]) - 1
            s = int(np.flatnonzero(ymv == mk)[0]); e = int(np.flatnonzero(ymv == mk + 35)[-1])
            # L
            WL = (1 - 0.0005) / o[s] * cf[e]
            # D（逐日迴圈：現金在每天收盤乘 1＋g[t]）
            cash = 1.0; sh = 0.0; tranche = 0
            months = [int(np.flatnonzero(ymv == mk + q)[0]) for q in range(12)]
            for t in range(s, e + 1):
                if tranche < 12 and t >= months[tranche] and ok[t]:
                    amt = cash / (12 - tranche); sh += amt * (1 - 0.0005) / o[t]; cash -= amt; tranche += 1
                cash *= 1 + g[t]
            WD = sh * cf[e] + cash
            # B（10%、12 個月上限）
            hi_ = -np.inf; b = None
            dl = int(np.flatnonzero(ymv == mk + 11)[-1])
            for t in range(s, dl + 1):
                if ok[t]:
                    hi_ = max(hi_, cf[t])
                    if cf[t] < 0.9 * hi_:
                        b = t + 1; break
            if b is None:
                b = int(np.flatnonzero(ymv == mk + 12)[0])
            while not ok[b]:
                b += 1
            cashb = 1.0
            for t in range(s, b):
                cashb *= 1 + g[t]
            WB = cashb * (1 - 0.0005) / o[b] * cf[e]
            for nm, mine in (("W_L", WL), ("W_D", WD), ("W_B", WB)):
                tot += 1; dd = abs(mine / r[nm] - 1); worst = max(worst, dd); diff += int(dd > 1e-9)
    return {"件": "C7", "項": "抽樣起點 L／D／B 36 個月期末財富", "抽樣": tot, "不同": diff, "最大相對差": worst}


def _top10(sc, mem):
    el = [j for j in range(len(sc)) if mem[j] and np.isfinite(sc[j])]
    el.sort(key=lambda j: (-sc[j], j))
    return set(el[:int(np.ceil(0.10 * len(el)))])


def x3(nm=12, seed=20261012):
    from backtest import researchUSC_c3 as C3
    R = K.rworld(); W = R["Wd"]; cal = R["cal"]; M_ = R["memb"]["合併"]
    S = C3.mom_scores(); BUY, _, _ = K.rank_tables(S, M_)
    ym = np.asarray(cal.year * 12 + cal.month - 1)
    rng = np.random.default_rng(seed); tot = diff = 0
    for e in rng.choice(sorted(S), size=nm, replace=False):
        e = int(e); k = ym[e]
        a12 = int(np.flatnonzero(ym == k - 13)[-1]); a1 = int(np.flatnonzero(ym == k - 2)[-1])
        sc = np.full(W["C"].shape[1], np.nan)
        for j in range(len(sc)):
            v = W["valid"][:, j]
            if not (v[a12 - 4:a12 + 1].any() and v[a1 - 4:a1 + 1].any()) or W["pb"][a12 + 1:e, j].any():
                continue
            sc[j] = W["CF"][a1, j] / W["CF"][a12, j] - 1
        tot += 1; diff += int(_top10(sc, M_[e - 1]) != set(BUY[e]))
    return {"件": "C3", "項": "抽樣換股日 MOM 前 10% 名單", "抽樣": tot, "不同": diff}


def x5(nm=12, seed=20261013):
    from backtest import researchUSC_c5 as C5
    R = K.rworld(); W = R["Wd"]; cal = R["cal"]; M_ = R["memb"]["合併"]
    S = C5.seas(C5.monthly_returns()); BUY, _, _ = K.rank_tables(S, M_, 0.10, 0.10)
    ym = np.asarray(cal.year * 12 + cal.month - 1)
    lastd = {int(k): int(np.flatnonzero(ym == k)[-1]) for k in np.unique(ym)}
    rng = np.random.default_rng(seed); tot = diff = 0
    for e in rng.choice(sorted(S), size=nm, replace=False):
        e = int(e); X = int(ym[e]); Sn = W["C"].shape[1]
        sc = np.full(Sn, np.nan)
        for j in range(Sn):
            vals = []
            for y in range(1, 11):
                m = X - 12 * y
                if m not in lastd or (m - 1) not in lastd or lastd[m] > R["w1"]:
                    continue
                a, b = lastd[m - 1], lastd[m]
                if not W["valid"][max(a - 4, 0):a + 1, j].any() or W["pb"][a + 1:b + 1, j].any():
                    continue
                r = W["CF"][b, j] / W["CF"][a, j] - 1
                if np.isfinite(r):
                    vals.append(r)
            if vals:
                sc[j] = float(np.mean(vals))
        tot += 1; diff += int(_top10(sc, M_[e - 1]) != set(BUY[e]))
    return {"件": "C5", "項": "抽樣換股日 SEAS 前 10% 名單", "抽樣": tot, "不同": diff}


def x6(ns=40, seed=20261014):
    from backtest import researchUSC_c6 as C6
    R = K.rworld(); W = R["Wd"]; cal = R["cal"]
    F = C6.load_F(); CB, _, _, _, _ = C6.scores(F)
    seg = set(F["SEG"])
    q = {}
    for f in ("cfo", "assets"):
        d = pd.read_csv(K.p_new("fundamentals", f"quarterly_{f}.csv"), dtype={"ticker": str})
        d["period_end"] = pd.to_datetime(d["period_end"]); d["first_filed"] = pd.to_datetime(d["first_filed"])
        q[f] = {t: g for t, g in d.groupby("ticker")}
    pairs = [(e, j) for e, v in CB.items() for j in np.flatnonzero(np.isfinite(v)) if str(W["tick"][j]) not in seg]
    rng = np.random.default_rng(seed); tot = diff = 0; det = []
    for i in rng.choice(len(pairs), size=min(ns, len(pairs)), replace=False):
        e, j = pairs[int(i)]; t = str(W["tick"][j]); day = cal[e]
        def lastk(f, k):
            g = q[f].get(t)
            if g is None:
                return None
            g = g[g["first_filed"] < day].sort_values(["period_end", "first_filed"]).drop_duplicates("period_end", keep="first")
            if len(g) < k:
                return None
            g = g.iloc[-k:]
            if (day - g["period_end"].iloc[-1]).days > 200:
                return None
            if k > 1:
                dd = g["period_end"].diff().dt.days.iloc[1:]
                if not ((dd >= 60) & (dd <= 120)).all():
                    return None
            return g["value"].to_numpy(float)
        c4 = lastk("cfo", 4); a1 = lastk("assets", 1)
        mine = c4.sum() / a1[0] if (c4 is not None and a1 is not None and a1[0] > 0) else np.nan
        tot += 1; bad = not (np.isfinite(mine) and abs(mine - CB[e][j]) < 1e-12 * max(1, abs(mine)))
        diff += int(bad)
        if bad:
            det.append((t, str(day.date()), mine, float(CB[e][j])))
    return {"件": "C6", "項": "抽樣（股, 月）CBOP 由 CSV 另算", "抽樣": tot, "不同": diff, "不同明細": det}


def x4(ns=20, seed=20261015):
    from backtest import researchUSA3_core as C
    from backtest import researchUSA1_data as A
    E = pd.read_pickle(os.path.join(K.WORK, "c4_events.pkl"))
    E = E[(E["狀態"] == "ok") & E["ex252"].notna()].reset_index(drop=True)
    meta, ST = C.load_cache(); cal = meta["cal"]
    M = A.load_market(); cs = pd.to_datetime(pd.Series(M["cal"]))
    trc = pd.Series(M["C"]["TR"], index=cs); tro = pd.Series(M["O"]["TR"], index=cs)
    rng = np.random.default_rng(seed); tot = diff = 0
    for i in rng.choice(len(E), size=min(ns, len(E)), replace=False):
        r = E.iloc[int(i)]; b = int(r["b"]); x = b + 251; d = ST[r["ticker"]]
        cl = pd.Series(d["C"]).ffill().to_numpy()
        mine = (cl[x] / d["O"][b] - 1) - (trc[cal[x]] / tro[cal[b]] - 1)
        tot += 1; diff += int(abs(mine - r["ex252"]) > 1e-12)
    return {"件": "C4", "項": "抽樣事件 252 日超額", "抽樣": tot, "不同": diff}


def main():
    T0 = time.time(); out = []
    for f in (x8, x7, x3, x5, x6, x4):
        r = f(); out.append(r); print(r, flush=True)
    tot = sum(r["抽樣"] for r in out); dif = sum(r["不同"] for r in out)
    K.jdump({"總抽樣": tot, "總不同": dif, "明細": out, "算於": K.now_tpe(), "秒": round(time.time() - T0)}, "check.json")
    print("合計 抽樣 %d 不同 %d" % (tot, dif))


if __name__ == "__main__":
    main()
