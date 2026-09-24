# -*- coding: utf-8 -*-
"""PREREGC2（SMA 趨勢濾網——永續合約槓桿版）v6 定版（sha 2d57657bc7264b0e）——回測線執行端。

資料：資料庫線 20260925-0306 交件 commit 22465b5bc2cc83a2c6dc1702280057a0bef80391
   ⇒ git archive 取 data/crypto、data/crypto_funding、data/meta/crypto_funding_manifest.csv 到 ~/c2data/<sha>/（唯讀）
訊號／段落重排／CI／判準／出口：沿用 researchc1（同一支，⛔ 不抄第二份）；報酬層＝本支新寫的路徑相依引擎（v2 §六④）

⭐ 引擎（登錄逐字）：
  在場段開始 ⇒ 全部權益當保證金（f＝1），曝險 E 倍（名目 ＝ E × 權益），isolated、只做多
  每日（持有 close(j) → close(j+1)）：
    ① 先結算當日資金費：逐筆 ΔM ＝ −rate_i × 前一交易日收盤 close(j) × 數量（funding.cashflow 同一條）
    ② 以扣完資金費的保證金 M′ 重算強平價 Lp ＝ (q·close(j) − M′) ／ (q·(1 − MMR))
    ③ low(j+1) ≤ Lp ⇒ 強平：該幣權益歸零、永久出局（第 0 層否決）
    ④ 否則 M ＝ M′ ＋ q·(close(j+1) − close(j))
  進出場：訊號 close(j) 決定；進場／出場各付單邊 0.05% × 名目（來回 0.1%，設計參數）

⭐ 落地讀法（⛔ 看任何結果前寫在這裡；交件逐條列出）：
 K1 價格＝ data/crypto/<SYM>.csv 的【現貨】日線（C1 同一份資料源）；永續日 K 尚未落檔（資料庫 0306 §四）⇒ 強平用現貨日低、名目用現貨前一日收盤
 K2 窗首＝登錄 §2-C③之二 表（寫死）；窗尾＝ 2026-08-31（資金費率只收到 2026-08 完結月；再往後 ⇒ FundingAbsent）
 K3 結算歸屬：calc_time 的 UTC 日期 ＝ d ⇒ 屬於「close(d−1) → close(d)」那一天的持有（00:00 那一筆也屬 d）
 K4 窗內每個月都必須在清單 status＝ok 且列數相符（funding.month_of）；否則停
 K5 強平後報酬：強平那一期 −100%，之後 0（權益 0，CAGR ＝ −100%）
 K6 對照：同窗現貨買進持有（不扣成本）；描述：C1 現貨規則（同窗、C1 的 0.2% 來回）、槓桿買進持有（同引擎、全程在場）
 K7 假訊號：窗內 held 的段落順序打亂 1,000 次（C1 placebo 同法、種子 20260923），每次跑同一個槓桿強平引擎
 K8 CI：配對 stationary block bootstrap（C1.paired_ci 同法），L＝Politis–White（抽配對差），回落腳另報 2L；
    ⭐ 每格的 2,000 個差值樣本存檔（批 1 結算：Bonferroni 捷徑不成立時要重抽，裁定線 seq97／台帳 §六）
 K9 MMR {0.5%, 1%, 2%} 三格各跑主格（N200、E3）；三格強平次數與出口一致 ⇒ 照報；不一致 ⇒ 以 2% 為主格（v3 補）
"""
from __future__ import annotations
import os, sys, json, time
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchc1 as C
from backtest import funding as F

SHA = "22465b5bc2cc83a2c6dc1702280057a0bef80391"
ROOT = os.path.expanduser(f"~/c2data/{SHA}")
OUT = "backtest/resultsc2"
COINS = ("BTC", "ETH", "BNB", "SOL", "XRP", "DOGE")
W_START = {"BTC": "2020-01-01", "ETH": "2020-01-01", "BNB": "2020-02-10", "XRP": "2020-01-06", "DOGE": "2020-07-10", "SOL": "2021-02-26"}
W_END = "2026-08-31"
E_MAIN, E_ROB, N_MAIN, N_ROB = 3.0, 2.0, 200, 50
COST_SIDE = 0.0005                     # 來回 0.1% ⇒ 單邊 0.05% × 名目（設計參數）
MMRS = (0.005, 0.01, 0.02)


def engine(held, close, low, fund_by_day, E, mmr, cost_side=COST_SIDE):
    """held[k] ＝ 第 k 期（close(k) → close(k+1)）是否在場；close／low 長度 ＝ len(held)+1（窗內，索引 0 ＝ 窗首）。
    fund_by_day[k+1] ＝ 屬於第 k 期的結算 rate 陣列（K3）。回 (逐期報酬, 強平期 or None, 資金費現金流總和／各期權益 list)。"""
    n = len(held)
    eq = 1.0; M = 0.0; q = 0.0; inpos = False; liq = None
    r = np.zeros(n); fcf = np.zeros(n)
    prev_total = 1.0
    for k in range(n):
        if liq is not None:
            r[k] = 0.0; continue
        c0 = close[k]
        # 收盤 k 的換手
        if held[k] and not inpos:
            notional = E * eq; q = notional / c0; M = eq - cost_side * notional; inpos = True
        elif (not held[k]) and inpos:
            eq = M - cost_side * q * c0; inpos = False; q = 0.0
        start_total = M if inpos else eq
        if inpos:
            rates = fund_by_day[k + 1]
            dM = float(-(rates * c0 * q).sum()) if len(rates) else 0.0
            fcf[k] = dM
            Mp = M + dM
            Lp = (q * c0 - Mp) / (q * (1.0 - mmr))
            if low[k + 1] <= Lp:
                liq = k; r[k] = -1.0 if prev_total > 0 else 0.0; eq = 0.0; M = 0.0; inpos = False
                continue
            M = Mp + q * (close[k + 1] - c0)
            end_total = M
        else:
            end_total = eq
        r[k] = end_total / prev_total - 1.0 if prev_total > 0 else 0.0
        prev_total = end_total
    return r, liq, fcf


def fixtures():
    """⭐ 先證明會響（⛔ 不綠就停）：
    ① E＝1、MMR＝0、成本 0、費率 0 ⇒ 與「held × 現貨報酬」逐期相同（引擎退化成 C1 毛報酬）
    ② 強平：E＝3、MMR＝1%，某日低點跌 35% ⇒ 那一天判強平、之後權益 0
    ③ 資金費符號：負費率 ⇒ 多方權益增加；正費率 ⇒ 減少（逐字：ΔEquity ＝ −rate × 名目）
    ④ 資金費會推近強平：同一條價格路徑，加大正費率 ⇒ 強平提早或出現"""
    close = np.array([100., 101, 99, 102, 104, 103, 105]); low = close * 0.995; n = len(close) - 1
    held = np.array([1, 1, 0, 1, 1, 1], bool); zero = {k: np.array([]) for k in range(n + 1)}
    r, liq, _ = engine(held, close, low, zero, 1.0, 0.0, 0.0)
    ref = held * (close[1:] / close[:-1] - 1)
    assert liq is None and np.allclose(r, ref, atol=1e-15), (r, ref)
    c2 = np.array([100., 100, 100, 100]); l2 = np.array([100., 99, 65, 100])
    r2, liq2, _ = engine(np.ones(3, bool), c2, l2, {k: np.array([]) for k in range(4)}, 3.0, 0.01, 0.0)
    assert liq2 == 1 and r2[1] == -1.0 and r2[2] == 0.0, (liq2, r2)
    c3 = np.array([100., 100, 100]); l3 = c3.copy()
    rp, _, fp = engine(np.ones(2, bool), c3, l3, {0: np.array([]), 1: np.array([0.001]), 2: np.array([])}, 3.0, 0.01, 0.0)
    rn, _, fn = engine(np.ones(2, bool), c3, l3, {0: np.array([]), 1: np.array([-0.001]), 2: np.array([])}, 3.0, 0.01, 0.0)
    assert fp[0] < 0 < fn[0] and abs(rp[0] + 0.003) < 1e-12 and abs(rn[0] - 0.003) < 1e-12, (rp, rn)
    c4 = np.array([100., 100, 80, 80]); l4 = np.array([100., 100, 76, 80])
    _, a, _ = engine(np.ones(3, bool), c4, l4, {k: np.array([]) for k in range(4)}, 3.0, 0.01, 0.0)
    _, b, _ = engine(np.ones(3, bool), c4, l4, {0: np.array([]), 1: np.array([0.2]), 2: np.array([]), 3: np.array([])}, 3.0, 0.01, 0.0)
    assert a is None and b == 1, (a, b)
    print("✅ C2 引擎 fixture：①退化成 C1 毛報酬逐期相同｜②日低跌 35% 在 E3 判強平、之後 0｜③費率符號（正費率 −0.30%、負費率 +0.30%）｜④正費率把強平提前到第 1 期")
    return True


def load_px(sym):
    d = pd.read_csv(os.path.join(ROOT, "data", "crypto", f"{sym}.csv"), dtype={"date": str})
    d = d.drop_duplicates("date").sort_values("date").reset_index(drop=True)
    gap = (pd.to_datetime(d["date"].iloc[-1]) - pd.to_datetime(d["date"].iloc[0])).days + 1
    assert gap == len(d), f"⛔ {sym} 日線有缺口"
    return d


def fund_days(sym, dates, man):
    """窗內每一天的結算 rate 陣列（K3）；逐月以清單驗（K4）。"""
    full = F.load_full(sym, path=os.path.join(ROOT, "data", "crypto_funding", f"{sym}USDT.csv"))
    months = sorted({(int(x[:4]), int(x[5:7])) for x in dates[1:]})
    for y, m in months:
        F.month_of(full, sym, y, m, man)                     # 清單沒有 ok 的月 ⇒ FundingAbsent；列數不符 ⇒ 炸
    day = full["ts"].dt.tz_convert("UTC").dt.strftime("%Y-%m-%d")
    g = {k: v.to_numpy(float) for k, v in full.groupby(day)["last_funding_rate"]}
    return {i: g.get(dt, np.array([])) for i, dt in enumerate(dates)}, full


def run_coin(sym, man, N, E, mmr, want_ci=False, want_plc=False):
    d = load_px(sym)
    c_all = d["close"].to_numpy(float); lo_all = d["low"].to_numpy(float); dates_all = d["date"].to_numpy()
    sig_all = (c_all > C.sma(c_all, N)).astype(bool)
    i0 = int(np.flatnonzero(dates_all == W_START[sym])[0]); i1 = int(np.flatnonzero(dates_all == W_END)[0])
    assert np.isfinite(C.sma(c_all, N)[i0]), f"⛔ {sym} 窗首 SMA{N} 無值"
    close, low, dates = c_all[i0:i1 + 1], lo_all[i0:i1 + 1], dates_all[i0:i1 + 1]
    held = sig_all[i0:i1]                                    # 第 k 期由 close(k) 的訊號決定
    fbd, full = fund_days(sym, dates, man)
    r, liq, fcf = engine(held, close, low, fbd, E, mmr)
    r_bh = close[1:] / close[:-1] - 1.0
    res = {"coin": sym, "N": N, "E": E, "MMR": mmr, "窗首": dates[0], "窗尾": dates[-1], "期數": len(r),
           "強平": liq is not None, "強平日": dates[liq + 1] if liq is not None else None,
           "年化": C.cagr(r), "回落": C.mdd(r), "BH年化": C.cagr(r_bh), "BH回落": C.mdd(r_bh),
           "曝險": float(held.mean()), "進出場": int(np.abs(np.diff(np.insert(held.astype(float), 0, 0.0))).sum()),
           "資金費現金流總和（相對初始 1）": float(fcf.sum()), "資金費結算筆數（在場期間）": int(sum(len(fbd[k + 1]) for k in range(len(held)) if held[k]))}
    ok, sc, sm = C.judge(res["年化"], res["回落"], res["BH年化"], res["BH回落"])
    res.update({"判定格": "⛔ 發生強平，判不過（第 0 層）" if liq is not None else ("過" if ok else "未過"), "嚴格優_年化": sc, "嚴格優_回落": sm})
    out = {"res": res}
    if want_ci and liq is None:
        Lb = C.politis_white_block(r - r_bh)
        samp = {}
        for tag, L in (("L", Lb), ("2L", 2 * Lb)):
            rng = np.random.default_rng(C.SEED); dc, dm = [], []
            for _ in range(C.N_BOOT):
                i = C.stationary_idx(len(r), L, rng); a, b = r[i], r_bh[i]
                dc.append(C.cagr(a) - C.cagr(b)); dm.append(abs(C.mdd(a)) - abs(C.mdd(b)))
            samp[tag] = (np.array(dc), np.array(dm))
        q = lambda v: (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5)))
        ci = {"cagr": q(samp["L"][0]), "mdd": q(samp["L"][1])}
        ex, why = C.exit_of(ok, sc, sm, ci, q(samp["2L"][1]))
        res.update({"L": Lb, "CI年化": ci["cagr"], "CI回落": ci["mdd"], "CI回落_2L": q(samp["2L"][1]), "出口": ex, "出口理由": why})
        out["boot"] = samp
    if want_plc:
        degen = []
        if res["曝險"] >= C.EXPO_DEGEN:
            degen.append("曝險 ≥ 90%")
        if res["進出場"] < C.MIN_TRADES:
            degen.append("進出場 < 5")
        res["假訊號狀態"] = "；".join(degen) if degen else "可得"
        if not degen:
            segs = C.segments(held.astype(float)); rng = np.random.default_rng(C.SEED); pc, pm, pl = [], [], 0
            for _ in range(C.N_PLACEBO):
                o = rng.permutation(len(segs))
                h = np.concatenate([np.full(segs[k][1], segs[k][0]) for k in o]).astype(bool)
                rr, lq, _ = engine(h, close, low, fbd, E, mmr)
                pc.append(C.cagr(rr)); pm.append(abs(C.mdd(rr))); pl += int(lq is not None)
            pc, pm = np.array(pc), np.array(pm)
            res.update({"假訊號_年化百分位": float((pc < res["年化"]).mean() * 100), "假訊號_回落百分位": float((pm > abs(res["回落"])).mean() * 100),
                        "假訊號_強平組數": pl})
            out["plc"] = (pc, pm)
    # 描述：C1 現貨規則（同窗）、槓桿買進持有
    if want_ci:
        gross = held * r_bh; prev = np.insert(held[:-1].astype(float), 0, 0.0)
        net1 = gross - np.abs(held - prev) * (C.COST_RT / 2.0)
        rL, lL, _ = engine(np.ones(len(held), bool), close, low, fbd, E, mmr)
        res.update({"描述_C1現貨規則": [C.cagr(net1), C.mdd(net1)], "描述_槓桿買進持有": [C.cagr(rL), C.mdd(rL), lL is not None]})
    return out


def main():
    t0 = time.time()
    fixtures()
    os.makedirs(OUT, exist_ok=True)
    man = F.load_manifest(path=os.path.join(ROOT, "data", "meta", "crypto_funding_manifest.csv"))
    rows, boots, plcs = [], {}, []
    for sym in COINS:
        mm = {}
        for mmr in MMRS:
            o = run_coin(sym, man, N_MAIN, E_MAIN, mmr, want_ci=True, want_plc=(mmr == 0.02))
            mm[mmr] = o
            rows.append(o["res"])
            if "boot" in o:
                for tag in ("L", "2L"):
                    boots[f"{sym}_MMR{mmr}_{tag}"] = o["boot"][tag]
            if "plc" in o:
                plcs += [{"coin": sym, "rep": i, "cagr": a, "mdd_abs": b} for i, (a, b) in enumerate(zip(*o["plc"]))]
        for N, E in ((N_ROB, E_MAIN), (N_MAIN, E_ROB)):
            rows.append(run_coin(sym, man, N, E, 0.02)["res"])
        r2 = mm[0.02]["res"]
        print("[{}] 窗 {}～{}｜強平 {}｜年化 {:+.2%} 回落 {:.2%}｜BH {:+.2%}/{:.2%}｜{}｜{}｜{:.0f}s".format(
            sym, r2["窗首"], r2["窗尾"], r2["強平日"] or "無", r2["年化"], r2["回落"], r2["BH年化"], r2["BH回落"], r2["判定格"], r2.get("出口", "—"), time.time() - t0), flush=True)
    T = pd.DataFrame(rows); T.to_csv(os.path.join(OUT, "per_coin.csv"), index=False)
    np.savez_compressed(os.path.join(OUT, "bootstrap_diff_samples.npz"), **{k + "_dcagr": v[0] for k, v in boots.items()}, **{k + "_dmdd": v[1] for k, v in boots.items()})
    if plcs:
        pd.DataFrame(plcs).to_csv(os.path.join(OUT, "placebo.csv.gz"), index=False)
    print(T.to_string())
    print("完成 {:.0f}s".format(time.time() - t0))


if __name__ == "__main__":
    main()
