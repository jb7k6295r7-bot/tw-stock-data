# -*- coding: utf-8 -*-
"""PREREG滑價 seq1（台股策略線登錄 sha 687410dfcc0fd76a「營量 v1／營飆 v1 滑價與流動性敏感度」；裁定 seq258 發號、敏感度、N 不加）。回測線，2026-09-27。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchSlip main|early [--procs 2] [--reps 200]
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchSlip_check.py

⭐ 策略本體一字不改（只加成本與成交限制）：
   營飆 v1 ＝ rerun17 #1 PREREG10 AND regime=True N10 H120、t−1 大盤閘（rerun17_regime_t1 同式：regime 遮罩右移一格）、種子 1000＋r、200 顆取中位
   營量 v1 ＝ rerun17 #13 P1 AND N20 d=inf relvol H60（無大盤閘）、種子 7000＋r；relvol 排序不抽籤 ⇒ 200 顆完全相同（researchYfMix13 已驗）⇒ 各臂只跑 r＝0（閘另驗 r＝0～2）
   主窗 2017-03-02～2026-08-24（rerun17 win 讀法：訊號進場日在窗內、窗首全現金），另切探索 2017-03-02～2021-12-30、確認 2022-01-03～2026-08-24 兩段（同一條權益）
   早年 2012-06-04～2014-12-31、只上市（researchV.body_setup("main") 的早年版面與訊號，PREREGV 同一條路徑）
⭐ 停止交易強制出場：開（research11.simulate_mtm stop_force ＝ research11.stop_force_days(valid, 窗尾)，裁定 seq255 §一 4）；另報「關」的原件版
═══ 臂（登錄 §二；⛔ 看數字前寫死；★ ＝ 本線落地讀法）═══
   C1 每筆單邊另加 s ∈ {0.1, 0.3, 0.5}% ⇒ 引擎成本 COST ＝ 0.585% ＋ 2s（★ 引擎在出場時以進場金額一次扣，照既有口徑）
   C2 平方根衝擊：單邊 ＝ 1.0 × σ20 × √(Q ÷ ADV20)；σ20 ＝ 前 20 根還原收盤日報酬標準差（ddof＝1，截至前一根）、ADV20 ＝ 前 20 根成交金額平均（元）；
      Q ＝ 資金 ÷ 檔數（營量 20、營飆 10）、資金 ∈ {50 萬, 250 萬, 1,000 萬}；進出各算一次 ⇒ 該筆報酬 g′ ＝ (1＋g)(1−i_出)／(1＋i_進) − 1（★ 持有期間市值照原價計、出場時一次反映）
      ⚠ 登錄的 50 萬是「資金 ÷ 檔數」＝ 每檔 25,000（營量）／50,000（營飆），比使用者實際（50 萬對半分兩套）大一倍 ⇒ 50 萬那列偏保守，照報不改
   C3 一字漲停買不到：進場日開盤 ＝ 漲停且全日最低 ＝ 開盤（鎖死）⇒ 買不到、名額當天持現金（引擎 tradable 規則、⛔ 不遞補）；
      一字跌停賣不掉：出場日開盤跌停且最高 ＝ 開盤、或排程出場日收盤跌停且最高 ＝ 收盤 ⇒ 延到第一個賣得掉的開盤（引擎 tradable＋delist）
      漲跌停旗標 ＝ tradability.one（原始價、跳動單位）× 原始最高／最低價（★ 一字 ＝ 開盤鎖死且全日沒離開那個價）
   C4 進出價改當日 (開＋高＋低＋收)÷4（還原價）：進場價與延後賣價 ＝ 均價、排程出場 ＝ 出場日均價
   C5（裁定 seq258 加）零股成本：手續費每筆 max(低消 M, 0.1425% × A)、M ∈ {1 元, 20 元}，A ＝ 每筆 12,500 元（營量）／25,000 元（營飆）；
      其餘照 0.1425%＋證交稅 0.3% ⇒ 低消多出的單邊 ＝ max(M／A − 0.1425%, 0) 加進成本；⚠ 逐字：「零股成交價以均價近似」（C5 一律疊在 C4 上）
   現實版 ＝ C1 0.3%＋C2（50 萬）＋C3＋C4；並列「現實版＋C5（低消 20 元）」
═══ 必報 ═══ 每臂年化、回落、比值、對 0050 標籤、比原回測少幾點；損益兩平額外單邊成本（① 比值掉到 0050 以下 ② 年化掉到 0050 以下；主窗、二分法）；
   參與率（Q ÷ 當日成交金額）＞ 1%、＞ 5% 的交易比例（三種資金；r＝0 的實際成交）；持股 ADV20 的 10／50／90 分位；
   進場日一字漲停比例與放棄組報酬；跌停延後次數；早年段同表
輸出 backtest/resultsSlip/
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import data as D
from . import rerun17 as RR
from . import research11 as R
from . import research13 as R13
from . import tradability as TR

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsSlip")
AND_PATH = os.path.join(RR.OUT, "sig_edc6f", "and_signals.csv.gz")
BASE_COST = R.COST
SEGS = {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}
CELLS = {1: {"名": "營飆 v1", "rule": "H120", "N": 10, "seed0": RR.P10_SEED0, "A": 25_000},
         13: {"名": "營量 v1", "rule": "H60", "N": 20, "seed0": RR.P1_SEED0, "A": 12_500}}
CAPS = (500_000, 2_500_000, 10_000_000)
SF_TAG = "停止交易強制出場：開"
C5_TAG = "零股成交價以均價近似"
ARMS = [("原件（stop_force 關）", dict(sf=False)), ("基準（stop_force 開）", dict()),
        ("C1 +0.1%", dict(s=0.001)), ("C1 +0.3%", dict(s=0.003)), ("C1 +0.5%", dict(s=0.005)),
        ("C2 50 萬", dict(cap=500_000)), ("C2 250 萬", dict(cap=2_500_000)), ("C2 1,000 萬", dict(cap=10_000_000)),
        ("C3 一字漲跌停", dict(c3=True)), ("C4 均價成交", dict(c4=True)),
        ("C5 低消 1 元（＋C4）", dict(c4=True, m5=1)), ("C5 低消 20 元（＋C4）", dict(c4=True, m5=20)),
        ("現實版（C1 0.3%＋C2 50 萬＋C3＋C4）", dict(s=0.003, cap=500_000, c3=True, c4=True)),
        ("現實版＋C5 低消 20 元", dict(s=0.003, cap=500_000, c3=True, c4=True, m5=20))]
_G: dict = {}
LOGF = None


def log(m):
    print(m, flush=True)
    if LOGF:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(m + "\n")


# ═════════════ 每檔資料（C2／C3／C4 用）═════════════
def stock_extra(sid, market, cal, npad):
    st = D.load_stock(sid, market, cal)
    if st is None:
        return None
    df = st.df; n = len(cal)
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    amt = pd.to_numeric(df["amount"], errors="coerce").to_numpy(float) if "amount" in df else np.full(n, np.nan)
    valid = np.isfinite(c); bars = np.flatnonzero(valid)
    avg = (o + h + l + c) / 4.0
    sig20 = np.full(n, np.nan); adv20 = np.full(n, np.nan)
    if len(bars) > 21:
        cb = c[bars]; r = cb[1:] / cb[:-1] - 1.0
        sd = pd.Series(r).rolling(20).std(ddof=1).to_numpy()          # sd[k] 用 r[k−19..k]（屬 bars[k+1]）
        ab = pd.Series(amt[bars]).rolling(20).mean().to_numpy()
        at = np.full(n, np.nan); at[bars[1:]] = sd; at = pd.Series(at).ffill().to_numpy()
        aa = np.full(n, np.nan); aa[bars] = ab; aa = pd.Series(aa).ffill().to_numpy()
        sig20[1:] = at[:-1]; adv20[1:] = aa[:-1]                         # t 用 t−1 以前
    tb = TR.one(sid, cal)
    p = os.path.join(D.DATA, "stocks", f"{sid}.csv")
    raw = pd.read_csv(p, dtype={"date": str}, usecols=["date", "open", "high", "low", "close"])
    raw["date"] = pd.to_datetime(raw["date"]); raw = raw.drop_duplicates("date").set_index("date").reindex(cal)
    ro, rh, rl, rc = (pd.to_numeric(raw[k], errors="coerce").to_numpy(float) for k in ("open", "high", "low", "close"))
    with np.errstate(invalid="ignore"):
        lk_up = tb["up_o"] & (rl == ro)
        lk_dn_o = tb["dn_o"] & (rh == ro)
        lk_dn_c = tb["dn_c"] & (rh == rc)
    pad = lambda x, v: np.r_[x, np.full(npad - n, v)] if npad > n else x
    return {"avg": pad(avg, np.nan), "amt": pad(amt, np.nan), "sig20": pad(sig20, np.nan), "adv20": pad(adv20, np.nan), "valid": valid,
            "trd": pad(tb["trd"], False), "up_o": pad(lk_up, False), "dn_o": pad(lk_dn_o, False), "dn_c": pad(lk_dn_c, False),
            "n_lock_up": int(lk_up.sum()), "n_up_o": int(tb["up_o"].sum())}


def _load(args):
    sid, mk = args
    return sid, stock_extra(sid, mk, _G["cal"], _G["NP"])


# ═════════════ 臂 ⇒ 訊號／價格／引擎參數 ═════════════
def arm_inputs(cell, spec, sig0, X, closes, opens):
    cf = CELLS[cell]; gcol, xcol = f"g_{cf['rule']}", f"xpos_{cf['rule']}"
    sig = sig0.copy(); op = opens
    e = sig["entry_pos"].to_numpy(int); x = sig[xcol].to_numpy(int)
    g = sig[gcol].to_numpy(float).copy()
    if spec.get("c4"):
        op = {s: (X[s]["avg"] if s in X and X[s] is not None else opens[s]) for s in opens}
        g = np.array([X[s]["avg"][xx] / X[s]["avg"][ee] - 1.0 if (np.isfinite(X[s]["avg"][ee]) and X[s]["avg"][ee] > 0 and np.isfinite(X[s]["avg"][xx])) else gg
                      for s, ee, xx, gg in zip(sig["sid"], e, x, g)])
    if spec.get("cap"):
        Q = spec["cap"] / cf["N"]
        ie = np.array([X[s]["sig20"][ee] * np.sqrt(Q / X[s]["adv20"][ee]) if (np.isfinite(X[s]["adv20"][ee]) and X[s]["adv20"][ee] > 0) else 0.0 for s, ee in zip(sig["sid"], e)])
        ix = np.array([X[s]["sig20"][xx] * np.sqrt(Q / X[s]["adv20"][xx]) if (np.isfinite(X[s]["adv20"][xx]) and X[s]["adv20"][xx] > 0) else 0.0 for s, xx in zip(sig["sid"], x)])
        ie = np.nan_to_num(ie); ix = np.nan_to_num(ix)
        g = (1 + g) * (1 - np.minimum(ix, 0.99)) / (1 + ie) - 1.0
    sig[gcol] = g
    cost = BASE_COST + 2 * spec.get("s", 0.0)
    if spec.get("m5"):
        cost += 2 * max(spec["m5"] / cf["A"] - 0.001425, 0.0)
    kw = {}
    if spec.get("c3"):
        kw["tradable"] = {s: {k: X[s][k] for k in ("trd", "up_o", "dn_o", "dn_c")} for s in set(sig["sid"])}
        kw["delist"] = {s: v for s, v in _G["dl"].items() if s in kw["tradable"]}
    if spec.get("sf", True):
        kw["stop_force"] = _G["SF"]
    return sig, op, cost, kw


def run_engine(cell, sig, op, cost, kw, r, audit=None):
    cf = CELLS[cell]; G = _G
    R.COST = cost
    try:
        if cell == 1:
            return R.simulate_mtm(sig, cf["rule"], cf["N"], np.random.default_rng(cf["seed0"] + r), G["closes"], op, G["NP"], return_equity=True, audit=audit, **kw)
        return R.simulate_mtm(sig, cf["rule"], cf["N"], np.random.default_rng(cf["seed0"] + r), G["closes"], op, G["NP"], log=[], d_max=None,
                              pick="relvol", queue_days=0, return_equity=True, audit=audit, **kw)
    finally:
        R.COST = BASE_COST


def metrics(o):
    G = _G; eq = np.asarray(o["equity"], float)
    c, m, v = RR.win_metrics(eq, o["first"], o["end"], G["w0"], G["w1"])
    out = {"cagr": float(c), "mdd": float(m), "eq_sha": hashlib.sha256(eq.tobytes()).hexdigest()[:16],
           "tr_limit_up": int(o.get("tr_limit_up", 0)), "tr_exit_delayed": int(o.get("tr_exit_delayed", 0)), "tr_close_locked": int(o.get("tr_close_locked", 0)),
           "sf_n": int(o.get("x_stop_force_n", 0))}
    for k, (a, b) in G["subsegs"].items():
        lo = min(o["first"], a)
        cc, mm = R13.window_stats(eq, lo, max(o["end"], b + 1), a, b + 1)
        out[f"{k}_cagr"] = float(cc); out[f"{k}_mdd"] = float(mm)
    return out


def job(args):
    cell, arm, r = args
    sig, op, cost, kw = _G["INP"][(cell, arm)]
    o = run_engine(cell, sig, op, cost, kw, r)
    return {"cell": cell, "arm": arm, "r": r, **metrics(o)}


def be_job(args):
    cell, s, r = args
    sig, op, cost, kw = _G["INP"][(cell, "基準（stop_force 開）")]
    o = run_engine(cell, sig, op, BASE_COST + 2 * s, kw, r)
    m = metrics(o); return m["cagr"], m["mdd"]


def label(c, m, c0, m0):
    return "合格" if (c > c0 and c / abs(m) >= c0 / abs(m0)) else ("另列" if c > c0 else "不合格")


# ═════════════ 設定 ═════════════
def setup(part, a):
    t0 = time.time()
    if part == "main":
        RR.use_snapshot()
        cal = D.load_calendar(); ncal = len(cal)
        w0, w1 = RR.win_bounds(cal)
        RR.setup_and(cal, AND_PATH, "branch", log)
        G = RR._G
        reg = G["regime"].copy(); reg_t1 = np.zeros_like(reg); reg_t1[1:] = reg[:-1]
        AND = G["AND"]; e = AND["entry_pos"].to_numpy()
        inwin = (e >= w0) & (e <= w1)
        SIG = {1: AND[reg_t1[e] & inwin], 13: AND[inwin]}
        closes, opens, NP = G["closes"], G["opens"], ncal
        bench = G["bench"]
        uni = D.load_universe().set_index("stock_id")["market"]
        subsegs = {k: (int(cal.searchsorted(pd.Timestamp(x))), int(cal.searchsorted(pd.Timestamp(y)))) for k, (x, y) in SEGS.items()}
    else:
        from . import researchV as V
        from . import researchYear1M as Y
        V.body_setup("main", log)
        cal = V._B["cal"]; ncal = len(cal); w0, w1 = V._B["w0"], V._B["w1"]
        SIG = {c: Y.sig_of(c, "mtm", w0, w1) for c in (1, 13)}
        closes, opens, NP = Y._G["closes"], Y._G["opens"], Y._G["NP"]
        bench = Y._G["bench"]
        uni = Y._G["uni"]
        subsegs = {}
    sids = sorted(set(SIG[1]["sid"]) | set(SIG[13]["sid"]))
    _G.update(cal=cal, NP=NP)
    with Pool(a.procs, initializer=_G.update, initargs=({"cal": cal, "NP": NP},)) as pool:
        X = dict(pool.map(_load, [(s, uni.get(s, "twse")) for s in sids], chunksize=8))
    valid = {s: v["valid"] for s, v in X.items() if v is not None}
    SF = R.stop_force_days(valid, w1)
    trad_full = {s: {"trd": v["trd"][:ncal]} for s, v in X.items() if v is not None}
    try:
        off = TR.load_official()
    except Exception:
        off = {}
    dl = TR.delist_status(trad_full, cal, official=off)
    _G.update(closes=closes, opens=opens, w0=w0, w1=w1, SF=SF, dl=dl, subsegs=subsegs, X=X, SIG=SIG, bench=bench, part=part, ncal=ncal)
    INP = {}
    for cell in (1, 13):
        for nm, spec in ARMS:
            INP[(cell, nm)] = arm_inputs(cell, spec, SIG[cell], X, closes, opens)
    _G["INP"] = INP
    b0 = RR.bench_row(cal, bench, w0, w1 + 1)
    Z = {"主窗": (b0["cagr"], b0["mdd"])}
    for k, (x, y) in subsegs.items():
        bb = RR.bench_row(cal, bench, x, y + 1); Z[k] = (bb["cagr"], bb["mdd"])
    _G["Z"] = Z
    log(f"[setup {part}] 日曆 {ncal}｜窗 {cal[w0].date()}～{cal[w1].date()}｜訊號 營飆 {len(SIG[1]):,}、營量 {len(SIG[13]):,}｜檔 {len(sids)}｜停止交易 {len(SF)}｜0050 {Z}｜{time.time() - t0:.0f}s")
    return cal


def liquidity(part):
    """r＝0、基準（stop_force 開）實際成交 ⇒ 參與率、ADV20 分佈；訊號層一字漲停比例與放棄組。"""
    G = _G; out = {}
    for cell in (1, 13):
        cf = CELLS[cell]; sig, op, cost, kw = G["INP"][(cell, "基準（stop_force 開）")]
        au = []
        run_engine(cell, sig, op, cost, kw, 0, audit=au)
        trades = [(a["t"], a["sid"], a["side"]) for a in au]
        amt = np.array([G["X"][s]["amt"][t] for t, s, _ in trades], float)
        adv = np.array([G["X"][s]["adv20"][t] for t, s, side in trades if side == "buy"], float)
        pr = {}
        for cap in CAPS:
            Q = cap / cf["N"]
            with np.errstate(divide="ignore", invalid="ignore"):
                q = Q / amt
            q = q[np.isfinite(q)]
            pr[f"{cap // 10000} 萬"] = {"每筆下單": Q, "參與率中位": float(np.median(q)) if len(q) else np.nan, "＞1%": float(np.mean(q > 0.01)) if len(q) else np.nan,
                                     "＞5%": float(np.mean(q > 0.05)) if len(q) else np.nan, "成交筆": int(len(q))}
        e = sig["entry_pos"].to_numpy(int); gcol = f"g_{cf['rule']}"
        lk = np.array([bool(G["X"][s]["up_o"][ee]) for s, ee in zip(sig["sid"], e)])
        g = sig[gcol].to_numpy(float)
        out[cf["名"]] = {"參與率": pr, "持股 ADV20（元）10／50／90 分位": [float(np.nanpercentile(adv, q_)) for q_ in (10, 50, 90)] if len(adv) else None,
                        "訊號進場日一字漲停": {"筆": int(lk.sum()), "占訊號": float(lk.mean()), "放棄組報酬平均（原 g、未扣成本）": float(np.nanmean(g[lk])) if lk.any() else np.nan,
                                         "其餘訊號報酬平均": float(np.nanmean(g[~lk]))}}
    return out


def breakeven(a, pool):
    """主窗、stop_force 開：額外單邊成本 s 使 ① 比值 ＜ 0050 ② 年化 ＜ 0050（二分法 12 次，區間 0～10%）。"""
    G = _G; c0, m0 = G["Z"]["主窗"]; out = {}
    cp = os.path.join(OUT, "be_cache.json")
    cache = json.load(open(cp, encoding="utf-8")) if os.path.exists(cp) else {}
    for cell in (1, 13):
        if CELLS[cell]["名"] in cache:                    # 續跑：已算完的策略照快取（run_main.log 有同一筆）
            out[CELLS[cell]["名"]] = cache[CELLS[cell]["名"]]; log(f"  [兩平 {CELLS[cell]['名']}] 讀快取 {out[CELLS[cell]['名']]}"); continue
        reps = a.reps if cell == 1 else 1

        def med(s):
            res = pool.map(be_job, [(cell, s, r) for r in range(reps)], chunksize=10)
            return float(np.median([x[0] for x in res])), float(np.median([x[1] for x in res]))
        rr = {}
        for crit in ("比值", "年化"):
            f = (lambda cm: cm[0] / abs(cm[1]) - c0 / abs(m0)) if crit == "比值" else (lambda cm: cm[0] - c0)
            lo, hi = 0.0, 0.10
            if f(med(lo)) < 0:
                rr[crit] = 0.0; continue
            if f(med(hi)) >= 0:
                rr[crit] = float("inf"); continue
            for _ in range(12):
                mid = (lo + hi) / 2
                if f(med(mid)) >= 0:
                    lo = mid
                else:
                    hi = mid
            rr[crit] = (lo + hi) / 2
        out[CELLS[cell]["名"]] = {"損益兩平額外單邊成本_比值跌到0050以下": rr["比值"], "損益兩平額外單邊成本_年化跌到0050以下": rr["年化"],
                                 "對成本很敏感（＜ 0.3% 單邊）": bool(min(rr.values()) < 0.003)}
        log(f"  [兩平 {CELLS[cell]['名']}] {out[CELLS[cell]['名']]}")
        cache[CELLS[cell]["名"]] = out[CELLS[cell]["名"]]
        json.dump(cache, open(cp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return out


def main():
    global LOGF
    ap = argparse.ArgumentParser()
    ap.add_argument("part", choices=["main", "early"])
    ap.add_argument("--procs", type=int, default=2)
    ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--resume", action="store_true", help="主 session 重啟後續跑：已有 seeds_<part>.csv.gz 就不重跑臂")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); LOGF = os.path.join(OUT, f"run_{a.part}.log")
    if not a.resume:
        open(LOGF, "w").close()
    log(f"===== researchSlip {a.part} {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜{SF_TAG}｜{C5_TAG} =====")
    t0 = time.time()
    cal = setup(a.part, a)
    jobs = []
    for cell in (1, 13):
        for nm, _ in ARMS:
            reps = a.reps if cell == 1 else (3 if nm.startswith("原件") or nm.startswith("基準") else 1)
            jobs += [(cell, nm, r) for r in range(reps)]
    with Pool(a.procs) as pool:
        sp = os.path.join(OUT, f"seeds_{a.part}.csv.gz")
        if a.resume and os.path.exists(sp):
            df = pd.read_csv(sp, float_precision="round_trip")
            if len(df) != len(jobs):
                raise SystemExit(f"⛔ 續跑：seeds 列數 {len(df)} ≠ 應有 {len(jobs)}")
            log(f"[續跑] 讀回 {sp}（{len(df):,} 列）")
        else:
            res = pool.map(job, jobs, chunksize=4)
            df = pd.DataFrame(res)
            df.to_csv(sp, index=False, float_format="%.17g")
            log(f"[臂] {len(jobs):,} 次引擎｜{time.time() - t0:.0f}s")
        BE = breakeven(a, pool) if a.part == "main" else None
    # 閘
    gate = {}
    if a.part == "main":
        ref1 = pd.read_csv(os.path.join(RR.OUT, "regime_t1", "seeds.csv"), float_precision="round_trip")
        ref1 = ref1[(ref1["stage"] == "t1") & (ref1["cell"] == 1)].set_index("r")
        ref13 = pd.read_csv(os.path.join(RR.OUT, "rerun17_seeds.csv"), float_precision="round_trip")
        ref13 = ref13[(ref13["stage"] == "main") & (ref13["cell"] == 13)].set_index("r")
    else:
        vs = pd.read_csv(os.path.join(HERE, "resultsV", "body_seeds.csv.gz"), float_precision="round_trip")
        vs = vs[vs["variant"] == "main"]
        ref1 = vs[vs["cell"] == 1].set_index("r"); ref13 = vs[vs["cell"] == 13].set_index("r")
    for cell, ref in ((1, ref1), (13, ref13)):
        g = df[(df["cell"] == cell) & (df["arm"] == "原件（stop_force 關）")].set_index("r")
        bad = sum(1 for r in g.index if repr(float(g.at[r, "cagr"])) != repr(float(ref.at[r, "cagr"])) or repr(float(g.at[r, "mdd"])) != repr(float(ref.at[r, "mdd"])))
        gate[CELLS[cell]["名"]] = {"比對顆數": int(len(g)), "不逐位元": int(bad), "逐位元": bad == 0}
    b13 = df[(df["cell"] == 13) & (df["arm"].isin(["原件（stop_force 關）", "基準（stop_force 開）"]))]
    gate["營量 r＝0～2 完全相同"] = bool(b13.groupby("arm")["eq_sha"].nunique().max() == 1)
    log(f"[閘] {gate}")
    # 彙總
    Z = _G["Z"]; T = []
    for cell in (1, 13):
        base = df[(df["cell"] == cell) & (df["arm"] == "原件（stop_force 關）")]
        bc = float(base["cagr"].median())
        for nm, _ in ARMS:
            x = df[(df["cell"] == cell) & (df["arm"] == nm)]
            row = {"策略": CELLS[cell]["名"], "臂": nm, "顆數": int(len(x))}
            for seg in ["主窗"] + list(_G["subsegs"]):
                pre = "" if seg == "主窗" else f"{seg}_"
                c, m = float(x[f"{pre}cagr"].median()), float(x[f"{pre}mdd"].median())
                row.update({f"{seg}_年化": c, f"{seg}_回落": m, f"{seg}_比值": c / abs(m) if m < 0 else np.nan, f"{seg}_標籤": label(c, m, *Z[seg])})
            row["比原回測少（點，主窗）"] = (bc - row["主窗_年化"]) * 100
            row.update({"一字漲停擋買（中位）": float(x["tr_limit_up"].median()), "跌停延後賣（中位）": float((x["tr_exit_delayed"] + x["tr_close_locked"]).median()),
                        "強制出場（中位）": float(x["sf_n"].median())})
            T.append(row)
    TT = pd.DataFrame(T); TT.to_csv(os.path.join(OUT, f"table_{a.part}.csv"), index=False, encoding="utf-8")
    LQ = liquidity(a.part)
    C5 = {CELLS[c]["名"]: {f"低消 {M} 元": {"每筆": CELLS[c]["A"], "低消換算單邊": M / CELLS[c]["A"], "比 0.1425% 多出的單邊": max(M / CELLS[c]["A"] - 0.001425, 0.0)} for M in (1, 20)} for c in (1, 13)}
    S = {"登錄": "PREREG滑價 seq1 sha 687410dfcc0fd76a；裁定 seq258（C5）；敏感度、N 不加", "標註": [SF_TAG, C5_TAG,
         "登錄的 50 萬列是「資金 ÷ 檔數」，比使用者實際大一倍 ⇒ 50 萬那列偏保守；照報不改"],
         "段": a.part, "0050": {k: list(v) for k, v in Z.items()}, "閘": gate, "流動性與漲停": LQ, "C5 低消換算": C5, "損益兩平": BE,
         "營量只跑 r＝0": "relvol 排序不抽籤 ⇒ 200 顆完全相同（YfMix13 已驗；本檔閘另驗 r＝0～2）"}
    json.dump(S, open(os.path.join(OUT, f"summary_{a.part}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    log(TT[["策略", "臂", "主窗_年化", "主窗_回落", "主窗_標籤", "比原回測少（點，主窗）"]].to_string())
    log(f"[完] {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
