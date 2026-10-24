# -*- coding: utf-8 -*-
"""researchTriple15y 獨立重算（對帳）——回測線計算子代理。⛔ 不 import researchTriple15y、不用本線合併面板。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTriple15y_check

另一條路：
 台股 ＝ 最新 origin/main 的 data/stocks/<代號>.csv（valid_bar＝1、price_basis≠無成交、close＞0）原始收盤 ×
        data/adj/<代號>.csv 後向累乘 factor（d 之後的事件 factor 全乘上 ⇒ 判斷日尺度）；日曆 ＝ 11 檔 data/stocks 列日期聯集。
        ⚠ data/stocks 從 2015-01-05 起 ⇒ 只能重算 t ≥ 2015-01-05 的部分：
          ① 主檔最大倍數的 t ≥ 2015-01-05 ⇒ 本檔最大倍數須與主檔一致（倍數差 ≤ 0.5%、t 與高點日相同）；
          ② 主檔最大倍數 ≥ 本檔（主檔多看 2011-10～2014-12）；③ 過／未過一致（主檔 t ＜ 2015 的檔只核 ②）。
        未還原欄同法用原始收盤（須一致：t、高點日相同、倍數差 ≤ 6e-4＝主檔表格四捨五入到小數 3 位）。
        「(t, t＋750] 最高」用 pandas 反向 rolling max（主檔用逐 t 迴圈）。壞根 ＝ 有效 K 棒間隔 ≥ 5 交易日（本檔自算，只報、不截）。
 ETN ＝ us-stock-data origin/main prices_yahoo/ETN.csv 的 adjclose／close，日曆 ＝ 該檔自己的列（主檔用 ^GSPC 日曆，列須一致）。
"""
from __future__ import annotations

import io
import os
import subprocess

import numpy as np
import pandas as pd

OUT = "backtest/resultsTriple15y"
J = pd.Timestamp("2026-10-22")
H = 750
CODES = ["1503", "1513", "1305", "1312", "4510", "6609", "8936", "3376", "2014", "1101", "2002"]


def gshow(path, repo=None):
    t = subprocess.run(["git"] + (["-C", repo] if repo else []) + ["show", f"origin/main:{path}"], capture_output=True)
    return t.stdout if t.returncode == 0 else None


def fwdmax(C, h=H):
    """fm[t] ＝ max C[t+1 .. t+h]（NaN 略過）。"""
    n = len(C)
    rm = pd.Series(C[::-1]).rolling(h, min_periods=1).max().values
    fm = np.full(n, np.nan)
    for t in range(n - 1):
        fm[t] = rm[n - 1 - (t + 1)]
    return fm


def best(D, C, t_lo, je):
    fm = fwdmax(C)
    ts = np.arange(t_lo, je - H + 1)
    m = fm[ts] / C[ts]
    m[~np.isfinite(m)] = -np.inf
    k = int(np.argmax(m)); t = int(ts[k])
    seg = C[t + 1:t + H + 1]
    hp = t + 1 + int(np.nanargmax(seg))
    return float(m[k]), str(D[t].date()), str(D[hp].date())


def main():
    T = pd.read_csv(os.path.join(OUT, "table.csv"), dtype=str).set_index("代號")
    S = {}
    for s in CODES:
        x = pd.read_csv(io.BytesIO(gshow(f"data/stocks/{s}.csv")), dtype={"date": str})
        x["date"] = pd.to_datetime(x["date"]); S[s] = x
    D = pd.DatetimeIndex(sorted(set().union(*[set(x["date"]) for x in S.values()])))
    D = D[D <= J]; je = len(D) - 1; pos = {d: q for q, d in enumerate(D)}
    assert D[-1] == J
    out = []; bad_all = []
    for s in CODES:
        x = S[s]
        c = pd.to_numeric(x["close"], errors="coerce")
        ok = (c > 0) & (pd.to_numeric(x["valid_bar"], errors="coerce").fillna(1) == 1) & (x["price_basis"].fillna("").astype(str) != "無成交")
        x = x[ok & (x["date"] <= J)]
        R = np.full(len(D), np.nan)
        for d, v in zip(x["date"], pd.to_numeric(x["close"])):
            R[pos[d]] = v
        A = gshow(f"data/adj/{s}.csv")
        F = np.ones(len(D))
        if A:
            ev = pd.read_csv(io.BytesIO(A), dtype={"date": str}); ev["date"] = pd.to_datetime(ev["date"])
            for e in ev.itertuples():
                if e.date <= J:
                    F[D < e.date] *= float(e.factor)       # 事件日之前的價 × factor
        C = R * F
        v = np.flatnonzero(np.isfinite(C))
        gaps = [str(D[b].date()) for a_, b in zip(v[:-1], v[1:]) if b - a_ - 1 >= 5]
        mA, tA, hA = best(D, C, 0, je)
        mU, tU, hU = best(D, R, 0, je)
        r = T.loc[s]
        mM = float(r["主_截斷_倍數"]); tM = r["主_截斷_起點t"]; hM = r["主_截斷_高點日"]
        mMU = float(r["未還原_倍數"]); tMU = r["未還原_起點t"]; hMU = r["未還原_高點日"]
        items = []
        if pd.Timestamp(tM) >= D[0]:
            ok1 = abs(mA / mM - 1) <= 0.005 and tA == tM and hA == hM
            items.append(("①還原一致", ok1))
        ok2 = mM >= mA * (1 - 0.005); items.append(("②主≥本", ok2))
        if pd.Timestamp(tM) >= D[0]:
            items.append(("③過否一致", (mA >= 3) == (mM >= 3)))
        if pd.Timestamp(tMU) >= D[0]:
            items.append(("未還原一致", abs(mU - mMU) <= 6e-4 and tU == tMU and hU == hMU))
        else:
            items.append(("未還原主≥本", mMU >= mU - 1e-9))
        allok = all(b for _, b in items)
        out.append({"代號": s, "本檔還原倍數": round(mA, 4), "t": tA, "高點": hA, "主檔": f"{mM}／{tM}／{hM}",
                    "本檔未還原": f"{mU:.4f}／{tU}／{hU}", "主檔未還原": f"{mMU}／{tMU}／{hMU}",
                    "項目": " ".join(f"{k}{'✓' if b else '✗'}" for k, b in items), "結果": "OK" if allok else "✗不符",
                    "2015起缺口≥5日": "；".join(gaps)})
        if s == "1312":
            t0 = pos[pd.Timestamp(tA)]; h0 = pos[pd.Timestamp(hA)]
            print(f"[1312 明細] t {tA} 原始收 {R[t0]} 還原 {C[t0]:.4f}｜高 {hA} 原始收 {R[h0]} 還原 {C[h0]:.4f}｜還原比 {C[h0] / C[t0]:.4f}｜"
                  f"原始比 {R[h0] / R[t0]:.4f}｜3 倍需高點原始收 ≥ {3 * R[t0] * F[t0] / F[h0]:.3f}")
        bad_all += gaps
    # ETN
    P = pd.read_csv(io.BytesIO(gshow("data/prices_yahoo/ETN.csv", os.path.expanduser("~/us-stock-data"))), dtype={"date": str})
    P["date"] = pd.to_datetime(P["date"]); P = P[P["date"] <= J].reset_index(drop=True)
    UD = pd.DatetimeIndex(P["date"])
    mA, tA, hA = best(UD, P["adjclose"].values.astype(float), 0, len(UD) - 1)
    mU, tU, hU = best(UD, P["close"].values.astype(float), 0, len(UD) - 1)
    r = T.loc["ETN"]
    okE = abs(mA - float(r["主_截斷_倍數"])) <= 6e-4 and tA == r["主_截斷_起點t"] and hA == r["主_截斷_高點日"]
    okU = abs(mU - float(r["未還原_倍數"])) <= 6e-4 and tU == r["未還原_起點t"] and hU == r["未還原_高點日"]
    out.append({"代號": "ETN", "本檔還原倍數": round(mA, 4), "t": tA, "高點": hA, "主檔": f"{r['主_截斷_倍數']}／{r['主_截斷_起點t']}／{r['主_截斷_高點日']}",
                "本檔未還原": f"{mU:.4f}／{tU}／{hU}", "主檔未還原": f"{r['未還原_倍數']}／{r['未還原_起點t']}／{r['未還原_高點日']}",
                "項目": f"還原一致{'✓' if okE else '✗'} 未還原一致{'✓' if okU else '✗'}", "結果": "OK" if (okE and okU) else "✗不符", "2015起缺口≥5日": ""})
    O = pd.DataFrame(out)
    O.to_csv(os.path.join(OUT, "check.csv"), index=False, encoding="utf-8-sig")
    print(O.to_string())
    n_ok = int((O["結果"] == "OK").sum())
    print(f"[check] {n_ok}/{len(O)} OK")


if __name__ == "__main__":
    main()
