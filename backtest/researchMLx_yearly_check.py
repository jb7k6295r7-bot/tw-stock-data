# -*- coding: utf-8 -*-
"""researchMLx_yearly 的獨立查核（回測線，2026-09-28）：只讀權益序列，用 pandas 另寫一套重算，和 yearly/summary.json 比對。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMLx_yearly_check

查：① series.csv.gz 的 ML 欄 ＝ resultsMLx/eq_pick.npy（逐位元，靠日曆位置對齊）
    ② 逐年（groupby 年取年底）③ 月相關（resample 月底）、0050 跌的月、0050 最大回落期間同期
    ④ 兩段年化／回落（自寫：(末÷首)^(245÷日數)−1、cummax）⑤ 混合（自寫：按年分塊累乘、年初扣成本再切半）
容差 1e-12（相對）；輸出 yearly/check.json
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
Y = os.path.join(HERE, "resultsMLx", "yearly")
SEGS = {"探索": ("2019-01-01", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}
TOL = 1e-12


def close(a, b):
    return bool(abs(a - b) <= TOL * max(1.0, abs(a), abs(b)))


def stats(s):
    c = (s.iloc[-1] / s.iloc[0]) ** (245 / len(s)) - 1
    return c, (s / s.cummax() - 1).min()


def mix(ml, b, ce=0.00385, cs=0.00585):
    """ml、b：段內日序列（段首日起）。按年分塊：塊內各自累乘，每塊（首塊除外）首日收盤後再平衡。"""
    yrs = ml.index.year
    val = []; E = M = 0.5; prev = None
    for i, (dt, m, x) in enumerate(zip(ml.index, ml.to_numpy(), b.to_numpy())):
        if prev is not None:
            E *= x / prev[1]; M *= m / prev[0]
            if dt.year != yrs[i - 1]:
                T = E + M; d = abs(E - T / 2); T -= d * (ce + cs); E = M = T / 2
        val.append(E + M); prev = (m, x)
    return pd.Series(val, ml.index)


def main():
    S = json.load(open(os.path.join(Y, "summary.json"), encoding="utf-8"))
    s = pd.read_csv(os.path.join(Y, "series.csv.gz"), parse_dates=["date"], float_precision="round_trip").set_index("date")
    eq = np.load(os.path.join(HERE, "resultsMLx", "eq_pick.npy"))
    ok = {}
    # ① ML 欄 ＝ eq_pick 的尾巴片段（段尾 2026-08-24 之後 eq_pick 還有幾天）
    k = len(s); hit = [i for i in range(len(eq) - k + 1) if np.array_equal(eq[i:i + k], s["ML"].to_numpy())]
    ok["① ML 欄 ＝ eq_pick.npy 連續片段（逐位元）"] = len(hit) >= 1
    # ② 逐年
    ye = s.groupby(s.index.year).tail(1)
    base = pd.concat([s.iloc[:1], ye]).iloc[:-1]
    yr = pd.DataFrame(ye.to_numpy() / base.to_numpy() - 1, index=ye.index.year, columns=s.columns).loc[2019:]
    mx = 0.0
    for r in S["逐年"]:
        y = int(r["年"][:4])
        for c in ("ML", "0050", "營量v1_T1"):
            mx = max(mx, abs(yr.loc[y, c] - r[c]))
    ok["② 逐年三欄（最大差）"] = mx
    ok["② 逐年 0050 下跌年"] = [int(y) for y in yr.index[yr["0050"] < 0]]
    ok["② 逐年 0050 落後 ML 年"] = [int(y) for y in yr.index[yr["0050"] < yr["ML"]]]
    # ③ 月
    mo = s.groupby(s.index.to_period("M")).last()
    mr = mo.pct_change().dropna()
    for nm, (a, b) in SEGS.items():
        m = mr[(mr.index >= pd.Period(a, "M")) & (mr.index <= pd.Period(b, "M"))]
        rho = np.corrcoef(m["ML"], m["0050"])[0, 1]; dn = m["0050"] < 0
        ref = S["月相關"][nm]
        ok[f"③ {nm} 月數"] = bool(len(m) == ref["月數"])
        ok[f"③ {nm} 相關"] = close(rho, ref["相關"])
        ok[f"③ {nm} 0050 跌的月 ML 平均"] = close(m.loc[dn, "ML"].mean(), ref["0050 跌的月 ML 平均"])
        seg = s.loc[a:b]; dd = seg["0050"] / seg["0050"].cummax() - 1
        lo = dd.idxmin(); hi = seg.loc[:lo, "0050"].idxmax()
        rd = S["0050 最大回落期間"][nm]
        ok[f"③ {nm} 0050 回落期間"] = (str(hi.date()), str(lo.date())) == (rd["高點日"], rd["低點日"])
        ok[f"③ {nm} ML 同期"] = close(seg.loc[lo, "ML"] / seg.loc[hi, "ML"] - 1, rd["ML 同期"])
        ok[f"③ {nm} 營量同期"] = close(seg.loc[lo, "營量v1_T1"] / seg.loc[hi, "營量v1_T1"] - 1, rd["營量v1_T1 同期"])
        # ④ 段
        for col, key in (("0050", "純 0050"), ("ML", "純 ML"), ("營量v1_T1", "營量 v1（T1）")):
            c, d = stats(seg[col]); rf = S["混合"][nm][key]
            ok[f"④ {nm} {key}"] = close(c, rf["年化"]) and close(d, rf["回落"])
        # ⑤ 混合
        mp = mix(seg["ML"], seg["0050"]); c, d = stats(mp); rf = S["混合"][nm]["混合 50／50（扣再平衡成本）"]
        ok[f"⑤ {nm} 混合 年化"] = close(c, rf["年化"]); ok[f"⑤ {nm} 混合 回落"] = close(d, rf["回落"])
        ok[f"⑤ {nm} 混合 路徑 ＝ mix npy"] = bool(np.allclose(mp.to_numpy(), np.load(os.path.join(Y, f"mix_{nm}.npy")), rtol=TOL, atol=0))
    allok = all((v is True) or (isinstance(v, float) and v <= 1e-12) or isinstance(v, list) for v in ok.values())
    ok["② 旗標一致"] = ok["② 逐年 0050 下跌年"] == [int(r["年"][:4]) for r in S["逐年"] if r["0050 下跌"]] and \
        ok["② 逐年 0050 落後 ML 年"] == [int(r["年"][:4]) for r in S["逐年"] if r["0050 落後 ML"]]
    ok["全過"] = bool(allok and ok["② 旗標一致"])
    json.dump(ok, open(os.path.join(Y, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print(json.dumps(ok, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()
