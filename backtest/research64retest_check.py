# -*- coding: utf-8 -*-
"""六四 v1 重測 獨立查核（⛔ 不 import research64retest；只讀它的輸出對數）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/research64retest_check.py

 ① 自寫固定配比引擎（窗首開盤建倉付 0.385%、每年指定月份第一個交易日開盤調回付 0.385%、缺開盤延後、不留現金）⇒ 六四與一直抱各檔（窗 A、B、A0）＝ summary
 ② 自寫 132 組合 × 窗 A、B ⇒ 照 random_draws.csv 取 ⇒ 六四百分位、隨機合格比例 ＝ summary
 ③ 自寫合成（含資金成本、自讀 DTB3）⇒ 五種資金成本 × 兩窗的六四、一直抱合成正2、0050 ＝ stress.csv
共用：researchTri.load_all（0050 早年＋主快照、00631L）、data.load_stock（00685L）、0050 判準基準的算法（還原收盤、窗首為基）自寫
"""
from __future__ import annotations
import json, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchTri as T
from backtest import data as D

HERE = os.path.expanduser("~/tw-p17/backtest")
OUT = os.path.join(HERE, "results64retest")
CO = 0.00385


def eng(O, C, w, i0, i1, cal, month):
    k = len(O); u = np.zeros(k); cash = 1.0; eq = []; pend = True
    for j in range(i1 - i0 + 1):
        t = i0 + j
        if j > 0 and cal[t][:7] != cal[t - 1][:7] and int(cal[t][5:7]) == month:
            pend = True
        if pend:
            o = np.array([x[t] for x in O])
            need = (u > 0) | (np.array(w) > 0)
            if np.isfinite(o[need]).all():
                hold = np.array([u[i] * o[i] if u[i] > 0 else 0.0 for i in range(k)])
                V = hold.sum() + cash
                tr = 0.5 * (sum(abs(w[i] * V - hold[i]) for i in range(k)) + abs((1 - sum(w)) * V - cash))
                V -= tr * CO
                u = np.array([w[i] * V / o[i] if w[i] > 0 else 0.0 for i in range(k)]); cash = (1 - sum(w)) * V; pend = False
        eq.append(sum(u[i] * C[i][t] for i in range(k) if u[i] > 0) + cash)
    eq = np.array(eq); n = len(eq)
    p = np.r_[1.0, eq]
    return float(eq[-1] ** (245 / n) - 1), float(np.min(p / np.maximum.accumulate(p) - 1))


def lab(c, m, c0, m0):
    r, r0 = c / abs(m), c0 / abs(m0)
    return "合格" if (c > c0 and r >= r0) else ("另列" if c > c0 else "不合格")


def main():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    G = T.load_all(); cal = list(G["cal"]); pos = G["pos"]; N = len(cal)
    calm = D.load_calendar(); off = pos[str(calm[0].date())]
    st = D.load_stock("00685L", "twse", calm).df
    o85 = np.full(N, np.nan); c85 = np.full(N, np.nan); o85[off:off + len(calm)] = st["open"].to_numpy(float); c85[off:off + len(calm)] = st["close"].to_numpy(float)
    o50 = G["O"]["0050"]; c50 = pd.Series(G["C"]["0050"]).ffill().to_numpy()
    o31 = G["O"]["00631L"]; c31 = pd.Series(G["C"]["00631L"]).ffill().to_numpy(); c85f = pd.Series(c85).ffill().to_numpy()
    RES = {}; diffs = []
    W = {"A 2018-01-15～2026-08-24": ("2018-01-15", "2026-08-24"), "B 確認段 2022-01-03～2026-08-24": ("2022-01-03", "2026-08-24"),
         "A0 2017-03-30～2026-08-24（00685L 上市首日起；描述）": ("2017-03-30", "2026-08-24")}
    base = {}
    for wn, (a, b) in W.items():
        i0, i1 = pos[a], pos[b]
        seg = c50[i0:i1 + 1] / c50[i0]; n = len(seg)
        c0 = seg[-1] ** (245 / n) - 1; m0 = float(np.min(seg / np.maximum.accumulate(seg) - 1)); base[wn] = (c0, m0)
        R = S["① 同窗判定＋⑤ 並列"][wn]
        diffs.append(max(abs(c0 - R["0050（判準，還原、不含成本）"]["年化"]), abs(m0 - R["0050（判準，還原、不含成本）"]["最大回落"])))
        for nm, O_, C_, w in (("六四 v1（真 00685L）", [o50, o85], [c50, c85f], (0.6, 0.4)), ("六四（00631L 代，描述）", [o50, o31], [c50, c31], (0.6, 0.4)),
                              ("一直抱 00685L", [o85], [c85f], (1.0,)), ("一直抱 00631L", [o31], [c31], (1.0,))):
            c, m = eng(O_, C_, w, i0, i1, cal, 1)
            diffs.append(max(abs(c - R[nm]["年化"]), abs(m - R[nm]["最大回落"])))
            if lab(c, m, c0, m0) != R[nm]["判準"]:
                diffs.append(np.inf)
    RES["① 同窗判定"] = {"比對": len(diffs), "最大差": float(max(diffs)), "過": bool(max(diffs) < 1e-9)}
    print(RES["① 同窗判定"], flush=True)
    # ②
    DR = pd.read_csv(os.path.join(OUT, "random_draws.csv"))
    bad = []
    for wn in ("A 2018-01-15～2026-08-24", "B 確認段 2022-01-03～2026-08-24"):
        a, b = W[wn]; i0, i1 = pos[a], pos[b]; c0, m0 = base[wn]
        grid = {}
        for x in range(11):
            for mth in range(1, 13):
                c, m = eng([o50, o85], [c50, c85f], (1 - x / 10, x / 10), i0, i1, cal, mth)
                grid[(x, mth)] = (c, m, c / abs(m), lab(c, m, c0, m0))
        d = [grid[(int(x), int(mm))] for x, mm in zip(DR.iloc[:, 0], DR.iloc[:, 1])]
        me = grid[(4, 1)]
        mine = {"六四 年化百分位（隨機 ≤ 六四）": float(np.mean([v[0] <= me[0] for v in d])), "六四 比值百分位": float(np.mean([v[2] <= me[2] for v in d])),
                "隨機合格比例": float(np.mean([v[3] == "合格" for v in d]))}
        ref = S["② 隨機配比臂"][wn]
        for k, v in mine.items():
            if abs(v - ref[k]) > 1e-12:
                bad.append((wn, k, v, ref[k]))
    RES["② 隨機配比臂"] = {"不同": bad, "過": not bad}
    print(RES["② 隨機配比臂"], flush=True)
    # ③
    dt = pd.read_csv("/mnt/c/SynologyDrive/跨線信箱/DTB3.csv"); dt.columns = ["d", "v"]; dt["v"] = pd.to_numeric(dt["v"], errors="coerce"); dt = dt.dropna()
    dd = dt["d"].tolist(); vv = (dt["v"] / 100).tolist()
    rate = np.full(N, np.nan)
    for t, day in enumerate(cal):
        k = int(np.searchsorted(dd, day, side="left")) - 1
        rate[t] = vv[k] if k >= 0 else np.nan
    f0 = int(np.flatnonzero(np.isfinite(G["C"]["0050"]))[0])

    def syn(fee, r):
        Lc = np.full(N, np.nan); Lo = np.full(N, np.nan); Lc[f0] = 1.0
        for t in range(f0 + 1, N):
            Lo[t] = Lc[t - 1] * (1 + 2 * (o50[t] / c50[t - 1] - 1)) if np.isfinite(o50[t]) else np.nan
            rr = (r[t] if np.isfinite(r[t]) else 0.0) if np.ndim(r) else r
            Lc[t] = Lc[t - 1] * (1 + 2 * (c50[t] / c50[t - 1] - 1) - fee / 245 - rr / 245)
        return Lo, Lc
    ST = pd.read_csv(os.path.join(OUT, "stress.csv"), encoding="utf-8")
    VAR = {"不扣資金成本（researchMix70 原式）": 0.0, "DTB3（美國 3 個月國庫券，代）": rate, "固定 1%": 0.01, "固定 2%": 0.02, "固定 3%": 0.03}
    d3 = []
    for vn, r in VAR.items():
        so85, sc85 = syn(0.003, r); so31, sc31 = syn(0.010, r)
        for win, (a, b) in (("壓力窗 2006-09-12～2014-12-31", ("2006-09-12", "2014-12-31")), ("2008-01-02～2009-03-31", ("2008-01-02", "2009-03-31"))):
            i0, i1 = pos[a], pos[b]
            for nm, O_, C_, w in (("六四 v1（合成 00685L）", [o50, so85], [c50, sc85], (0.6, 0.4)), ("一直抱合成正2（00631L 式）", [so31], [sc31], (1.0,)),
                                  ("一直抱 0050", [o50], [c50], (1.0,))):
                c, m = eng(O_, C_, w, i0, i1, cal, 1)
                ref = ST[(ST["資金成本"] == vn) & (ST["窗"] == win) & (ST["對象"] == nm)].iloc[0]
                d3.append(max(abs(c - ref["年化"]), abs(m - ref["最大回落"])))
                if bool(m < -0.70) != bool(ref["超過−70%"]):
                    d3.append(np.inf)
    RES["③ 2008 合成＋資金成本"] = {"比對": len(d3), "最大差": float(max(d3)), "過": bool(max(d3) < 1e-9)}
    RES["全部過"] = all(v["過"] is True for v in RES.values() if isinstance(v, dict))
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(RES, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
