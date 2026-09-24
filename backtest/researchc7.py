# -*- coding: utf-8 -*-
"""PREREGC7（波動率管理曝險，對同平均曝險的固定部位）v2（sha 8cf7fec8cec5675f）——回測線執行端。批2。

資料：data/crypto/<SYM>.csv 釘 commit 22465b5bc2cc83a2c6dc1702280057a0bef80391（與 C2／C6 同一份唯讀副本）
CI／判準／出口／cagr／mdd：researchc1（同一支）

⭐ 落地讀法（⛔ 看任何結果前寫在這裡；交件逐條列出）：
 V1 月＝日曆月；RV_{m−1} ＝ 前一個日曆月所有日報酬的變異（ddof＝0，除以當月實際天數，照登錄「用當月實際天數」）
 V2 c_m ＝ 資料首月起至 m−1 各月 RV 的平均（擴張窗；「窗首」讀成資料首月 ⇒ 暖身月也計入，否則第一個調整日沒有 c）
 V3 暖身＝資料的前 12 個日曆月（首月若不完整也算一個月）；窗首＝第 13 個月的第一個交易日（調整日）
 V4 w_m ＝ min(c_m ／ RV_{m−1}, 1)；在第 m 月第一個交易日【收盤】調到 w_m，之後到下個月第一個交易日收盤前【不交易】
    ⇒ 月內部位數量不動、權重隨價格漂移；現金 0%；成本＝調整額 × 單邊 0.1%
 V5 主基準：k ＝ 判定窗內各月 w_m 的平均；每月第一個交易日收盤調回 k（同頻、同成本、同漂移）
 V6 判定窗：窗首 ～ 2026-09-19（C1 同一末日）；判定＝C1.judge（對主基準）；CI＝C1.paired_ci（L 與 2L）
 V7 假訊號：判定窗內的月權重序列 {w_m} 整段隨機重排 1,000 組（種子 20260923），同一套調整與成本 ⇒ 聯合判過比例（對主基準）
 V8 BTC 的 Bitstamp 段（≤ 2017-08-16）照 C6 主格比例還原（k＝Binance 首日開盤 ÷ Bitstamp 末日收盤）；其他五幣只有 Binance
 V9 描述：對 100% 買進持有（同窗）；逐年報酬；成本 0.1／0.2／0.4／0.8%（單邊）
"""
from __future__ import annotations
import os, sys, json, time
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchc1 as C

SHA = "22465b5bc2cc83a2c6dc1702280057a0bef80391"
ROOT = os.path.expanduser(f"~/c2data/{SHA}")
OUT = "backtest/resultsc7"
COINS = ("BTC", "ETH", "BNB", "SOL", "XRP", "DOGE")
END, WARM, COST1 = "2026-09-19", 12, 0.001


def load(sym):
    d = pd.read_csv(os.path.join(ROOT, "data", "crypto", f"{sym}.csv"), dtype={"date": str})
    d = d.drop_duplicates("date").sort_values("date").reset_index(drop=True)
    d = d[d["date"] <= END].reset_index(drop=True)
    gap = (pd.to_datetime(d["date"].iloc[-1]) - pd.to_datetime(d["date"].iloc[0])).days + 1
    assert gap == len(d), f"⛔ {sym} 日線有缺口"
    if sym == "BTC":
        bs = d["date"] <= "2017-08-16"
        k = float(d.loc[d["date"] == "2017-08-17", "open"].iloc[0]) / float(d.loc[d["date"] == "2017-08-16", "close"].iloc[0])
        d.loc[bs, "close"] = d.loc[bs, "close"].astype(float) * k
    return d


def run(close, adj_idx, weights, cost1=COST1):
    """adj_idx[j] ＝ 第 j 個調整日的日曆索引（收盤調整）；weights[j] ＝ 該次目標權重。
    回 逐期報酬（第 i 期 ＝ close(adj_idx[0]+i) → close(adj_idx[0]+i+1)），⛔ 月內不交易、權重漂移。"""
    i0 = adj_idx[0]; n = len(close) - 1 - i0
    hold = 0.0; cash = 1.0; prev = 1.0
    r = np.zeros(n); adj = set(adj_idx); wmap = dict(zip(adj_idx, weights))
    for t in range(i0, len(close) - 1):
        if t in adj:                                   # 收盤調整：先扣成本（按調整額），再依扣後權益設目標權重
            tot = hold + cash
            cst = abs(wmap[t] * tot - hold) * cost1
            tot2 = tot - cst
            hold = wmap[t] * tot2; cash = tot2 - hold
        hold *= close[t + 1] / close[t]
        now = hold + cash
        r[t - i0] = now / prev - 1.0                   # ⭐ 分母＝前一期總權益 ⇒ 成本算進當期報酬
        prev = now
    return r


def month_first_idx(dates):
    per = pd.PeriodIndex(pd.to_datetime(dates), freq="M")
    first = np.flatnonzero(np.r_[True, per[1:] != per[:-1]])
    return per, first


def coin(sym):
    d = load(sym); c = d["close"].to_numpy(float); dates = d["date"].to_numpy()
    per, first = month_first_idx(dates)
    rets = np.r_[np.nan, c[1:] / c[:-1] - 1.0]
    months = list(pd.unique(per))
    rv = {}
    for m in months:
        x = rets[(per == m)]; x = x[np.isfinite(x)]
        rv[m] = float(np.var(x)) if len(x) >= 2 else np.nan
    adj_idx, w = [], []
    for j, fi in enumerate(first):
        if j < WARM:
            continue
        m = per[fi]; prev = months[:months.index(m)]
        c_m = float(np.nanmean([rv[p] for p in prev]))
        rvp = rv[prev[-1]]
        w.append(min(c_m / rvp, 1.0)); adj_idx.append(int(fi))
    w = np.array(w)
    r_rule = run(c, adj_idx, w)
    k = float(w.mean())
    r_base = run(c, adj_idx, np.full(len(w), k))
    i0 = adj_idx[0]; r_bh = c[i0 + 1:] / c[i0:-1] - 1.0
    cg_r, md_r, cg_b, md_b = C.cagr(r_rule), C.mdd(r_rule), C.cagr(r_base), C.mdd(r_base)
    ok, sc, sm = C.judge(cg_r, md_r, cg_b, md_b)
    res = {"coin": sym, "資料首日": dates[0], "窗首（第一個調整日）": dates[i0], "窗尾": dates[-1], "期數": len(r_rule), "調整次數": len(w),
           "k（判定窗平均 w）": k, "w 取值": {"min": float(w.min()), "中位": float(np.median(w)), "上限 1 的月數": int((w >= 1).sum())},
           "規則": [cg_r, md_r], "主基準": [cg_b, md_b], "判定格": "過" if ok else "未過", "嚴格優": [sc, sm],
           "描述_100%買進持有": [C.cagr(r_bh), C.mdd(r_bh)]}
    Lb = C.politis_white_block(r_rule - r_base)
    ci1 = C.paired_ci(r_rule, r_base, Lb, np.random.default_rng(C.SEED))
    ci2 = C.paired_ci(r_rule, r_base, 2 * Lb, np.random.default_rng(C.SEED))
    ex, why = C.exit_of(ok, sc, sm, ci1, ci2["mdd"])
    res.update({"L": Lb, "CI年化差": ci1["cagr"], "CI回落深度差": ci1["mdd"], "CI回落深度差_2L": ci2["mdd"], "出口": ex, "出口理由": why})
    rng = np.random.default_rng(C.SEED); pc, pm, pj = [], [], 0
    for _ in range(C.N_PLACEBO):
        ww = rng.permutation(w); rr = run(c, adj_idx, ww)
        a, b = C.cagr(rr), C.mdd(rr); pc.append(a); pm.append(abs(b)); pj += int(C.judge(a, b, cg_b, md_b)[0])
    res.update({"假訊號_年化百分位": float((np.array(pc) < cg_r).mean() * 100), "假訊號_回落百分位": float((np.array(pm) > abs(md_r)).mean() * 100),
                "假訊號_聯合判過比例": pj / C.N_PLACEBO})
    cs = {}
    for c1 in (0.001, 0.002, 0.004, 0.008):
        a = run(c, adj_idx, w, c1); b = run(c, adj_idx, np.full(len(w), k), c1)
        cs[f"{c1:.1%}"] = {"規則": [C.cagr(a), C.mdd(a)], "主基準": [C.cagr(b), C.mdd(b)], "判定格形": "過" if C.judge(C.cagr(a), C.mdd(a), C.cagr(b), C.mdd(b))[0] else "未過"}
    res["成本敏感度（單邊）"] = cs
    ys = pd.Series(np.cumprod(1 + r_rule), index=pd.to_datetime(dates[i0 + 1:]))
    yb = pd.Series(np.cumprod(1 + r_base), index=pd.to_datetime(dates[i0 + 1:]))
    def yearly(s):
        ye = s.groupby(s.index.year).last(); prev = ye.shift(1); prev.iloc[0] = 1.0
        return {int(k_): float(v) for k_, v in (ye / prev - 1).items()}
    res["逐年_規則"] = yearly(ys); res["逐年_主基準"] = yearly(yb)
    return res, (r_rule, r_base, ci1, ci2)


def fixtures():
    """① w 全為 1、成本 0 ⇒ 與 100% 買進持有逐期相同｜② 權重漂移：月內不交易 ⇒ 持股價值隨價格走、現金不動（手算一例）
    ③ 成本：只在調整日收，額＝|目標 − 現有| × 單邊"""
    close = np.array([100., 110, 99, 120, 132]); adj = [0, 2]
    r = run(close, adj, np.array([1.0, 1.0]), 0.0)
    assert np.allclose(r, close[1:] / close[:-1] - 1), r
    r2 = run(close, adj, np.array([0.5, 0.5]), 0.0)
    # 第 0 期：0.5 持股 → 0.55，總 1.05 ⇒ +5%；第 1 期：0.55 → 0.495，總 0.995 ⇒ −5.238%；第 2 期起在第 2 日重調到 0.5
    assert abs(r2[0] - 0.05) < 1e-12 and abs(r2[1] - (0.995 / 1.05 - 1)) < 1e-12, r2
    r3 = run(np.array([100., 100, 100]), [0, 1], np.array([1.0, 0.5]), 0.001)
    tot0 = 1 - 0.001; exp1 = (tot0 - 0.5 * tot0 * 0.001) / tot0 - 1
    assert abs(r3[0] + 0.001) < 1e-12 and abs(r3[1] - exp1) < 1e-12, (r3, exp1)
    print("✅ C7 fixture：① w＝1、成本 0 ⇒ 等於買進持有｜② 月內漂移手算 +5.000%、−5.238%｜③ 成本只在調整日、按調整額計")


def main():
    t0 = time.time()
    fixtures()
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for s in COINS:
        res, _ = coin(s); rows.append(res)
        print("[{}] 窗 {}～{}｜k {:.3f}｜規則 {:+.2%}/{:.2%} vs 基準 {:+.2%}/{:.2%}｜{}｜{}｜假訊號聯合判過 {:.1%}｜{:.0f}s".format(
            s, res["窗首（第一個調整日）"], res["窗尾"], res["k（判定窗平均 w）"], *res["規則"], *res["主基準"], res["判定格"], res["出口"],
            res["假訊號_聯合判過比例"], time.time() - t0), flush=True)
    json.dump(rows, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print("完成 {:.0f}s".format(time.time() - t0))


if __name__ == "__main__":
    main()
