# -*- coding: utf-8 -*-
"""PREREGC5（資金費率套利：現貨多＋永續空，逐幣）v2（sha 32a21a483e10ad7b）——回測線執行端。批2。

資料：commit 22465b5bc2cc83a2c6dc1702280057a0bef80391（現貨日線＋資金費率＋清單；與 C2 同一份唯讀副本）
資金費讀取與逐月清單驗證：researchc2.fund_days（同一支；清單 status＝ok、列數相符，否則停）
CI 區塊長／bootstrap／cagr／mdd：researchc1

⭐ 落地讀法（⛔ 看任何結果前寫在這裡；交件逐條列出）：
 A1 價格：永續日 K 尚未落檔 ⇒ 兩腳都用【現貨】日線，強平檢查用【現貨】日高（登錄 §二、裁定 seq118 §四）⇒ 「基差恆 0」列為限制
 A2 窗：該幣第一筆資金費的 UTC 日（BTC／ETH 2020-01-01 為資料可得起點）當日收盤建倉 ～ 2026-08-31（C2 同一末日）；
    窗內每月都必須在清單 status＝ok（連續完整）；若有缺月 ⇒ 取最長連續區間並逐月列出被切掉的月（實測見交件）
 A3 資本：總權益 V（初始 1）＝ 現貨市值 ＋ 空單保證金；兩腳名目各 V／2；空單保證金 ＝ 名目（1 倍）⇒ 報酬是【對總權益】的報酬
 A4 每日（close(t) → close(t+1)）：① 先結算當日資金費：空方 ΔM ＝ ＋rate_i × close(t) × 空單數量（逐筆）
    ② 強平價（isolated 空單）L ＝ (M′ ＋ q·close(t)) ／ (q·(1＋MMR))；high(t+1) ≥ L ⇒ 強平（第 0 層否決）
    ③ 否則 M ＝ M′ − q·(close(t+1) − close(t))；現貨市值 ＝ q_spot × close(t+1)
    ④ close(t+1) 再平衡：先扣兩腳調整成本（現貨 |現貨市值 − V/2| × 0.1%、永續 |空單名目 − V/2| × 0.05%），再把兩腳調回扣後 V 的一半
 A5 建倉（窗首收盤）與平倉（窗尾收盤）各付一次兩腳單邊成本
 A6 強平後：該幣記「⛔ 發生強平，判不過」，報酬算到強平那天為止（之後不再模擬）
 A7 CI：單序列 stationary block bootstrap（L＝Politis–White 對日報酬），2,000 次、種子 20260923 ⇒ 年化的 95% CI；
    下界 > 0 ⇒ 出口②；含 0 ⇒ 出口①；上界 < 0 ⇒ 出口③；⭐ 2,000 個 bootstrap 年化存檔（批2 結算用）
 A8 敏感度：MMR {0.5%, 1%, 2%}（主格 2%）、成本 ×0.5／×1／×2／×4（判定只看 ×1）
 A9 必報：逐年報酬、去掉最好一年後的年化、最大回落、最長回落天數
"""
from __future__ import annotations
import os, sys, json, time
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchc1 as C
from backtest import researchc2 as C2
from backtest import funding as F

OUT = "backtest/resultsc5"
COINS = C2.COINS
END = "2026-08-31"
SPOT_SIDE, PERP_SIDE = 0.001, 0.0005
MMRS = (0.005, 0.01, 0.02)


def engine(close, high, fbd, mmr, cmult=1.0):
    """close／high 為窗內（索引 0 ＝ 建倉日）；fbd[k+1] ＝ 第 k 期的結算 rate。回 (逐期報酬, 強平期 or None, 資金費收入總和, 成本總和)。"""
    cs, cp = SPOT_SIDE * cmult, PERP_SIDE * cmult
    V = 1.0
    N = V / 2
    cost0 = N * cs + N * cp                                     # 建倉兩腳
    V -= cost0; N = V / 2
    qs = N / close[0]; qp = N / close[0]; M = N
    n = len(close) - 1
    r = np.zeros(n); prev = 1.0; liq = None; fund = 0.0; costs = cost0
    for k in range(n):
        c0, c1 = close[k], close[k + 1]
        rates = fbd[k + 1]
        dM = float((rates * c0 * qp).sum()) if len(rates) else 0.0
        fund += dM
        Mp = M + dM
        L = (Mp + qp * c0) / (qp * (1.0 + mmr))
        if high[k + 1] >= L:
            liq = k
            now = qs * c1 + 0.0                                  # 空單保證金歸零；現貨還在
            r[k] = now / prev - 1.0
            r = r[:k + 1]
            break
        M = Mp - qp * (c1 - c0)
        S = qs * c1
        V = S + M
        cst = abs(S - V / 2) * cs + abs(qp * c1 - V / 2) * cp
        if k == n - 1:
            cst = S * cs + qp * c1 * cp                          # 窗尾平倉兩腳
        costs += cst
        V -= cst
        N = V / 2; qs = N / c1; qp = N / c1; M = N
        r[k] = V / prev - 1.0
        prev = V
    return r, liq, fund, costs


def fixtures():
    """① 價格不動、費率 0、成本 0 ⇒ 報酬全 0｜② 正費率 ⇒ 空方收錢（對總權益的報酬 ＝ rate × 名目 ／ V ＝ rate／2）
    ③ 價格漲、費率 0、成本 0 ⇒ 兩腳相抵、報酬 0（對沖）｜④ 日高 ≥ 強平價 ⇒ 強平"""
    z = {k: np.array([]) for k in range(5)}
    global SPOT_SIDE, PERP_SIDE
    s0, p0 = SPOT_SIDE, PERP_SIDE
    SPOT_SIDE = PERP_SIDE = 0.0
    try:
        cl = np.array([100., 100, 100, 100]); r, lq, _, _ = engine(cl, cl, z, 0.02)
        assert lq is None and np.allclose(r, 0), r
        f = dict(z); f[1] = np.array([0.001])
        r, _, fund, _ = engine(cl, cl, f, 0.02)
        assert abs(r[0] - 0.0005) < 1e-12 and fund > 0, r
        cu = np.array([100., 110, 121, 133.1]); r, lq, _, _ = engine(cu, cu, z, 0.02)
        assert lq is None and np.allclose(r, 0, atol=1e-12), r
        hi = np.array([100., 100, 250, 100]); r, lq, _, _ = engine(cl, hi, z, 0.02)
        assert lq == 1, lq
    finally:
        SPOT_SIDE, PERP_SIDE = s0, p0
    print("✅ C5 fixture：①不動 ⇒ 0｜②正費率 0.1% ⇒ 對總權益 +0.05%（空方收錢）｜③價格漲、兩腳相抵 ⇒ 0｜④日高 250 ≥ 強平價 ⇒ 強平")


def continuous_window(sym, man, dates_all, full):
    """A2：從第一筆資金費的 UTC 日起，找清單 status＝ok 的最長連續月段。"""
    m = man[(man["sym"].str.upper().str.replace("USDT", "") == sym)].copy()
    m = m.sort_values("月份")
    ok = (m["status"] == "ok").to_numpy(); mon = m["月份"].to_numpy()
    best, cur, bs, s0 = 0, 0, None, None
    for i, o in enumerate(ok):
        if o:
            if cur == 0:
                s0 = i
            cur += 1
            if cur > best:
                best, bs = cur, (s0, i)
        else:
            cur = 0
    first_m, last_m = mon[bs[0]], mon[bs[1]]
    cut = [x for x, o in zip(mon, ok) if not o]
    first_day = full["ts"].dt.tz_convert("UTC").dt.strftime("%Y-%m-%d")
    first_day = first_day[first_day.str[:7] >= first_m].iloc[0]
    end = min(END, pd.Period(last_m, "M").end_time.strftime("%Y-%m-%d"))
    return first_day, end, cut, (first_m, last_m)


def boot_cagr(r, L, rng, B=C.N_BOOT):
    return np.array([C.cagr(r[C.stationary_idx(len(r), L, rng)]) for _ in range(B)])


def coin(sym, man):
    d = C2.load_px(sym)
    full = F.load_full(sym, path=os.path.join(C2.ROOT, "data", "crypto_funding", f"{sym}USDT.csv"))
    w0d, w1d, cut, mm = continuous_window(sym, man, d["date"].to_numpy(), full)
    da = d["date"].to_numpy()
    i0 = int(np.flatnonzero(da == w0d)[0]); i1 = int(np.flatnonzero(da == w1d)[0])
    close, high, dates = d["close"].to_numpy(float)[i0:i1 + 1], d["high"].to_numpy(float)[i0:i1 + 1], da[i0:i1 + 1]
    fbd, _ = C2.fund_days(sym, dates, man)
    res = {"coin": sym, "窗首（建倉日）": w0d, "窗尾": w1d, "連續月段": mm, "清單中非 ok 的月（被切掉）": cut, "期數": len(close) - 1}
    by_mmr = {}
    for mmr in MMRS:
        r, liq, fund, costs = engine(close, high, fbd, mmr)
        by_mmr[mmr] = {"強平": liq is not None, "強平日": dates[liq + 1] if liq is not None else None, "年化": C.cagr(r), "回落": C.mdd(r),
                       "資金費收入總和": fund, "成本總和": costs}
    res["MMR"] = {f"{k:.1%}": v for k, v in by_mmr.items()}
    r, liq, fund, costs = engine(close, high, fbd, 0.02)
    res["主格"] = by_mmr[0.02]
    samples = None
    if liq is None:
        L = C.politis_white_block(r)
        samples = boot_cagr(r, L, np.random.default_rng(C.SEED))
        lo, hi = float(np.percentile(samples, 2.5)), float(np.percentile(samples, 97.5))
        ex = "出口②" if lo > 0 else ("出口③" if hi < 0 else "出口①")
        res["主格"].update({"判定格": "過（淨年化 > 0）" if C.cagr(r) > 0 else "未過", "L": L, "CI年化": [lo, hi], "出口": ex})
    else:
        res["主格"].update({"判定格": "⛔ 發生強平，判不過（第 0 層）", "出口": "—"})
    res["成本敏感度"] = {f"×{m_}": (lambda o: {"年化": C.cagr(o[0]), "強平": o[1] is not None})(engine(close, high, fbd, 0.02, m_)) for m_ in (0.5, 1, 2, 4)}
    eq = np.cumprod(1 + r); s = pd.Series(eq, index=pd.to_datetime(dates[1:len(eq) + 1]))
    ye = s.groupby(s.index.year).last(); prev = ye.shift(1); prev.iloc[0] = 1.0; yr = (ye / prev - 1)
    res["逐年"] = {int(k): float(v) for k, v in yr.items()}
    best = int(yr.idxmax()); rest = s[s.index.year != best]
    rr = r[np.asarray(pd.to_datetime(dates[1:len(r) + 1]).year != best)]
    res["去掉最好一年"] = {"最好一年": best, "其餘年化": C.cagr(rr)}
    dd = eq / np.maximum.accumulate(eq) - 1; under = dd < 0; longest = cur = 0
    for u in under:
        cur = cur + 1 if u else 0; longest = max(longest, cur)
    res["最大回落"] = float(dd.min()); res["最長回落天數"] = int(longest)
    return res, samples


def main():
    t0 = time.time()
    fixtures()
    os.makedirs(OUT, exist_ok=True)
    man = F.load_manifest(path=os.path.join(C2.ROOT, "data", "meta", "crypto_funding_manifest.csv"))
    rows, samp = [], {}
    for s in COINS:
        res, sm = coin(s, man); rows.append(res)
        if sm is not None:
            samp[f"{s}_cagr"] = sm
        m = res["主格"]
        print("[{}] 窗 {}～{}｜{}｜年化 {:+.2%} 回落 {:.2%}｜{}｜{}｜去掉 {} 後 {:+.2%}｜{:.0f}s".format(
            s, res["窗首（建倉日）"], res["窗尾"], "強平 " + m["強平日"] if m["強平"] else "無強平", m["年化"], m["回落"], m["判定格"],
            m.get("出口"), res["去掉最好一年"]["最好一年"], res["去掉最好一年"]["其餘年化"], time.time() - t0), flush=True)
    json.dump(rows, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    if samp:
        np.savez_compressed(os.path.join(OUT, "bootstrap_cagr_samples.npz"), **samp)
    print("完成 {:.0f}s".format(time.time() - t0))


if __name__ == "__main__":
    main()
