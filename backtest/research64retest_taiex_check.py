# -*- coding: utf-8 -*-
"""六四 v1 重測 ④ 獨立查核（⛔ 不 import research64retest_taiex；自讀指數與利率、自寫合成與固定配比引擎）⇒ ＝ stress_taiex.csv（六四、一直抱兩列）。

    cd ~/tw-p17 && ~/tw-p16/.venv/bin/python backtest/research64retest_taiex_check.py --src ~/msdata/us_macro/<sha>
"""
from __future__ import annotations
import argparse, json, os
import numpy as np
import pandas as pd

OUT = os.path.expanduser("~/tw-p17/backtest/results64retest")
CO = 0.00385


def eng(O, C, w, i0, i1, cal):
    k = len(O); u = np.zeros(k); cash = 1.0; eq = []; pend = True
    for j in range(i1 - i0 + 1):
        t = i0 + j
        if j > 0 and cal[t][:7] != cal[t - 1][:7] and cal[t][5:7] == "01":
            pend = True
        if pend:
            o = np.array([x[t] for x in O])
            need = (u > 0) | (np.array(w) > 0)
            if np.isfinite(o[need]).all():
                hold = np.array([u[i] * o[i] if u[i] > 0 else 0.0 for i in range(k)]); V = hold.sum() + cash
                tr = 0.5 * (sum(abs(w[i] * V - hold[i]) for i in range(k)) + abs((1 - sum(w)) * V - cash)); V -= tr * CO
                u = np.array([w[i] * V / o[i] if w[i] > 0 else 0.0 for i in range(k)]); cash = (1 - sum(w)) * V; pend = False
        eq.append(sum(u[i] * C[i][t] for i in range(k) if u[i] > 0) + cash)
    p = np.r_[1.0, np.array(eq)]
    return float(p.min() * 100), float(np.min(p / np.maximum.accumulate(p) - 1))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--src", required=True); a = ap.parse_args(); src = os.path.expanduser(a.src)
    tx = pd.read_csv(os.path.join(src, "twse_taiex.csv"), dtype={"date": str}).drop_duplicates("date").sort_values("date")
    cal = tx["date"].tolist(); c = pd.to_numeric(tx["close"]).to_numpy(float); n = len(cal)
    def lagd(dates, vals):                                      # t 用 < t 的最近一筆
        idx = np.searchsorted(np.array(dates), np.array(cal), side="left") - 1
        return np.where(idx >= 0, np.array(vals)[np.maximum(idx, 0)] / 100.0, np.nan)
    d = pd.read_csv("/mnt/c/SynologyDrive/跨線信箱/DTB3.csv"); d.columns = ["d", "v"]; d["v"] = pd.to_numeric(d["v"], errors="coerce"); d = d.dropna()
    m = pd.read_csv(os.path.join(src, "cbc_EG41M01_money_market_monthly.csv"), dtype={"month": str})
    cpm = dict(zip(m["month"], pd.to_numeric(m["商業本票-初級市場-1-30天"], errors="coerce")))
    cp = []
    for dd in cal:
        y, mo = int(dd[:4]), int(dd[5:7]); k = f"{y - 1}-12" if mo == 1 else f"{y}-{mo - 1:02d}"
        v = cpm.get(k, np.nan); cp.append(v / 100.0 if np.isfinite(v) else np.nan)
    ib = pd.read_csv(os.path.join(src, "cbc_EG37D01_interbank_daily.csv"), dtype={"date": str})
    ib["v"] = pd.to_numeric(ib["隔夜-加權平均"], errors="coerce"); ib = ib.dropna(subset=["v"])
    RT = {"不扣資金成本": np.zeros(n), "DTB3（美國 3 個月國庫券，代）": lagd(d["d"].tolist(), d["v"].tolist()),
          "台灣商業本票初級 1-30 天（上個月）": np.array(cp), "台灣拆款隔夜加權平均": lagd(ib["date"].tolist(), ib["v"].tolist()),
          "固定 1%": np.full(n, 0.01), "固定 2%": np.full(n, 0.02), "固定 3%": np.full(n, 0.03)}
    ST = pd.read_csv(os.path.join(OUT, "stress_taiex.csv"), encoding="utf-8")
    diffs = []; flagbad = 0; cnt = 0
    for divn, dv in (("價格指數（不含息）", 0.0), ("加年 3% 股息近似（描述）", 0.03)):
        r = np.r_[np.nan, c[1:] / c[:-1] - 1.0] + dv / 245
        C0 = np.r_[1.0, np.cumprod(1 + r[1:])]; O0 = np.r_[np.nan, C0[:-1]]
        for rn, rt in RT.items():
            rf = pd.Series(rt).ffill().to_numpy(); k0 = int(np.flatnonzero(np.isfinite(rf))[0])
            CL = np.full(n, np.nan); CL[k0] = 1.0
            for t in range(k0 + 1, n):
                CL[t] = CL[t - 1] * (1 + 2 * r[t] - 0.003 / 245 - rf[t] / 245)
            OL = np.r_[np.nan, CL[:-1]]
            for wn in ST["窗"].unique():
                sub = ST[(ST["股息"] == divn) & (ST["資金成本"] == rn) & (ST["窗"] == wn)]
                w = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))["④ 1990 起加權指數合成"]["窗（實際交易日）"][wn]
                i0, i1 = cal.index(w[0]), cal.index(w[1])
                for nm, O, C, ww in (("六四 v1", [O0, OL], [C0, CL], (0.6, 0.4)), ("一直抱合成正2", [OL], [CL], (1.0,)), ("一直抱 0050 代理", [O0], [C0], (1.0,))):
                    ref = sub[sub["對象"] == nm].iloc[0]
                    if isinstance(ref["狀態"], str) and ref["狀態"]:
                        ok = not (np.isfinite(OL[i0]) and np.isfinite(CL[i0:i1 + 1]).all())
                        flagbad += int(not ok); continue
                    lo, mdd = eng(O, C, ww, i0, i1, cal); cnt += 1
                    diffs.append(max(abs(lo - ref["窗內最慘剩（萬，100 萬起）"]), abs(mdd - ref["窗內最大回落"])))
                    flagbad += int(bool(mdd < -0.70) != bool(ref["超過−70%"]))
    RES = {"比對": cnt, "最大差": float(max(diffs)), "−70% 標記與不適用判定不同": flagbad, "過": bool(max(diffs) < 1e-9 and flagbad == 0)}
    CK = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else {}
    CK["④ 1990 起加權指數合成（六四、一直抱兩列）"] = RES
    CK["全部過"] = all(v["過"] is True for v in CK.values() if isinstance(v, dict))
    json.dump(CK, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(RES)


if __name__ == "__main__":
    main()
