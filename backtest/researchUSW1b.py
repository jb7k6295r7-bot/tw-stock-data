# -*- coding: utf-8 -*-
"""USREG-W1b（美股新策略 W1(b)：季營收創近 8 季新高 ∧ ¬ma_stack ∧ ma60_up，組合層）——pre（候選盤點、讀法計數）＋本體。

    PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSW1b --pre  [--procs 2]   # ⛔ 不跑引擎、不讀任何持有期報酬
    PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSW1b --main [--procs 2]

判準：美股登錄 seq2 §五（正文）＋seq3 §四＋seq4 §二§三＋seq5 §一§二§三；裁定 seq168 §三、seq176 §二、seq182、seq214 §三。
台股原件：W1 ＝ P12 (S1, C1, T1)（researchp12／researchAFC）：月量測日（每月第一個交易日）、門檻B 訊號、n_slots 8、pick=None（候選池隨機挑）、
     d_max=None、queue_days=0、cash_mode="zero"、H120（進場 T+1 開盤、第 120 根收盤出）、tradable＋delist on（AFC W1）；
     引擎 backtest/research11.simulate_mtm（⛔ 只 import、未改）；種子 default_rng(102000＋r)，r＝0…199（P12 §九-8）。
判準（組合層；seq2 §五、台股 seq141 同形）：200 顆種子的 年化中位、回落中位 對 ^SP500TR 同窗（未捨入）：
     條件一 年化中位 ＞ 基準年化（嚴格）；條件二 年化中位 ÷ |回落中位| ≥ 基準比值 ⇒ 合格／另列（只條件一）／不合格。
     限制（seq2 §五）：窗 2016 起、無更早驗收段 ⇒ 合格只算候選，須以 2026-09 後資料前瞻再驗。

⛔⛔ 授權：權益曲線、逐月候選、逐筆交易 ＝ 美股資料衍生序列 ⇒ 只放 ~/us_work/usw1b/（repo 外）並列 sha；resultsUSW1b/ 只有彙總。

⭐ 讀法（登錄與裁定已寫 ⇒ 照寫；台股先例 ⇒ 照先例；★ 新讀法 ⇒ 兩邊都數、若改動候選集合就停下回報）：
 Z1 資料 us-stock-data 0043f97（窗到 2026-08-31 ≤ 09-22）；價格 scope＝panel（seq5 ④ 暖身可用入指數前）；NYSE 日曆；UA 無效 K 棒；成本 0.05% 來回。
 Z2 量測日 d ＝ 每月第一個交易日（台股 p4_features.measurement_days）；候選須 d 當天 in_index＝1 且有有效 K 棒（seq5 ④、adapter universe）。
 Z3 bars_ok ＝ d 以前（含）有效 K 棒數 ≥ 120（台股 MIN_BARS）；ma_stack／ma60_up ＝ 台股 p4_features 逐字（close 日曆 ffill、rolling min_periods＝w）。
 Z4 liq_ok（台股 amt20 ≥ 新台幣 5,000 萬）：美股沒有換算規定 ⇒ ★ 報「在指數 ∧ bars_ok 的股-月 amt20（美元，原始收盤 × 量）最小值」；
    最小值高於任何合理換算（25～35 TWD/USD ⇒ 1.4～2.0 百萬美元）⇒ 此閘對候選集合沒有作用、照「全過」；否則停下回報。
 Z5 季營收（seq3 §四、seq4 §三、seq5 §一）：讀 value（第一次公布）；可用日 ＝ first_filed 的下一個交易日（adapter avail_date）；d 當天可用的季依 period_end 排序取最後 8 個：
    不足 8 個、或相鄰 period_end 相距 ＞ 140 天、或任一 value ≤ 0 ⇒ 不列候選；新高 ＝ 最新一季 ≥ 前 7 季最大值 − |最大值|×1e-4（台股 rev_hi24 的對稱容差〈八十六〉）
    ★〔精確 ≥ 版的件數另報；有差 ⇒ 停〕。不適用 19 檔（沒有任何營收列）⇒ 不列候選、名單必報。
    描述臂（seq5 ①）：照 seq4「曆季逐字」（最後 8 季須是 8 個連續曆季、各有值）會被踢出的股-月數與檔數。
 Z6 訊號 ＝ 候選 ∧ ma_stack＝0 ∧ ma60_up＝100（台股 build_sig_gate_b "B" 同式，inst_ok 拿掉：seq2 §五）；entry ＝ d+1、xpos ＝ entry+119、g ＝ closes[xpos]／opens[entry] − 1；
    剔除 xpos ≥ 日曆長度／開盤非有限或 ≤ 0／收盤非有限（台股同）。
 Z7 ★ 轉接層硬斷點（IR seam、DHR／XRX split_div）：訊號的特徵回看窗 [d−120 根, d] 或持有期 [entry, xpos] 跨到斷點的件數必報；> 0 ⇒ 停下回報（⛔ 本支不自己選）。
 Z8 tradable ＝ {trd：該日有有效 K 棒；up_o／dn_o／dn_c：全 False（美股沒有漲跌停）}；delist ＝ 台股 tradability.delist_status 同式（gap 60、無官方下市表）。
    持有期內移出指數 ⇒ 照抱（seq214 R4 E0；scope＝panel 有移出後價格）。
 Z9 窗內年化／回落 ＝ 台股 rerun17.win_metrics 形狀（eq[w0]～eq[w1]，年數 ＝ 天數 ÷ ANN）；ANN ＝ 252（NYSE；台股 245）〔251.54 實際值、245 的標籤另報〕；
    ^SP500TR 同一條式子；SPY 還原價備援只描述。
 Z10 描述臂（⛔ 不改判）：成本 0.02%／0.10%；股息扣 30% 預扣稅版（seq3 §四；個股與基準同扣：淨報酬 ＝ 價格報酬 ＋ 0.7 ×（總報酬 − 價格報酬），
     基準 ＝ ^GSPC 價格報酬 ＋ 0.7 ×（^SP500TR − ^GSPC））；「從第一個可能進場日起算」的窗（面板最早 2015-12-01 ⇒ 期初 5 個月依構造無候選）。
"""
from __future__ import annotations
import os, sys, time, json, io, csv, hashlib
from multiprocessing import Pool
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
from backtest import us_data as U
from backtest import research11 as R
from backtest import researchUSM as RU
from backtest import researchUSM_body as MB
from backtest import tradability as TRD

OUT = os.path.expanduser("~/tw-p17/backtest/resultsUSW1b")
WORK = os.path.expanduser("~/us_work/usw1b")
COST = U.COST_ROUNDTRIP
COST_SENS = U.COST_SENSITIVITY
RULE, HOLD, N_SLOTS = "H120", 120, 8
SEED0, NSEED = 102000, 200
MIN_BARS, NQ, GAPMAX, TOL = 120, 8, 140, 1e-4
ANN = 252
NET_DIV = 0.7
_G = {}


def sha256f(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ═════════════ 每檔讀檔（worker）═════════════
def _src_raw(src):
    """src 檔 ⇒ DataFrame(index＝date)：raw_close（拆股調整、未含息）、vol、tr（總報酬比）、pr（價格報酬比）⇒ 給 amt20 與預扣稅版。"""
    kind, f = src.split(":", 1)
    if kind == "yahoo":
        d = pd.read_csv(U._p("prices_yahoo", f + ".csv"), dtype={"date": str})
        idx = pd.DatetimeIndex(pd.to_datetime(d["date"]))
        a = pd.Series(d["adjclose"].to_numpy(float), idx); c = pd.Series(d["close"].to_numpy(float), idx)
        out = pd.DataFrame({"raw_close": c, "vol": d["volume"].to_numpy(float), "tr": a / a.shift(1), "pr": c / c.shift(1)})
    else:
        d = pd.read_csv(U._p("prices", f + ".csv"), dtype={"date": str})
        idx = pd.DatetimeIndex(pd.to_datetime(d["date"]))
        a = pd.Series(d["adjClose"].to_numpy(float), idx); c = pd.Series(d["close"].to_numpy(float), idx)
        sf = pd.Series(d["splitFactor"].to_numpy(float), idx).fillna(1.0)
        out = pd.DataFrame({"raw_close": c, "vol": d["volume"].to_numpy(float), "tr": a / a.shift(1), "pr": c * sf / c.shift(1)})
    return out


def _init(cal, w0, w1, meas):
    _G.update(cal=cal, w0=w0, w1=w1, meas=meas)


def load_one(t):
    cal, meas = _G["cal"], _G["meas"]; n = len(cal)
    df = U.load_ohlc(t, scope="panel")
    if len(df) == 0:
        return None
    A = RU.prep(df, cal)
    if len(A["bars"]) == 0:
        return None
    valid = A["valid"]; C = A["C"]; O = A["O"]
    member = RU.member_array(t, cal)
    closes = pd.Series(C).ffill().to_numpy()
    opens = np.where(valid & (np.nan_to_num(O) > 0), O, np.nan)
    # 美元成交額、淨股息版：同一個 src 檔的同日列
    pn = U.panel(t)
    amt = np.full(n, np.nan); net = np.full(n, np.nan)
    for src, g in pn.groupby("src", sort=False):
        raw = _src_raw(src)
        idx = g.index[g.index.isin(cal)]
        r = raw.reindex(idx)
        pos = cal.get_indexer(idx)
        amt[pos] = (r["raw_close"] * r["vol"]).to_numpy(float)
        nr = (r["pr"] + NET_DIV * (r["tr"] - r["pr"])).to_numpy(float) / r["tr"].to_numpy(float)   # 淨／總 的當日比
        net[pos] = nr
    amt[~valid] = np.nan
    # 淨股息價：N_t ＝ A_t × Π(淨比)；在 hard_break 與 src 首日重設為 1（跨斷點不累積）
    f = np.ones(n); cum = 1.0
    pb = A["pb"]
    for i in np.flatnonzero(valid):
        x = net[i]
        if pb[i] or not np.isfinite(x):
            x = 1.0
        cum *= x; f[i] = cum
    f = pd.Series(np.where(valid, f, np.nan)).ffill().bfill().to_numpy()
    closes_net = pd.Series(np.where(valid, C * f, np.nan)).ffill().to_numpy()
    opens_net = np.where(np.isfinite(opens), opens * f, np.nan)
    c = pd.Series(closes)
    c = c.where(np.arange(n) >= A["bars"][0])                    # 首根之前無值
    ma20, ma60, ma120 = c.rolling(20, min_periods=20).mean(), c.rolling(60, min_periods=60).mean(), c.rolling(120, min_periods=120).mean()
    ma_stack = ((c > ma20) & (ma20 > ma60) & (ma60 > ma120)).astype(float) * 100
    ma60_up = (ma60 > ma60.shift(20)).astype(float) * 100
    ma_stack[ma120.isna()] = np.nan; ma60_up[ma60.shift(20).isna()] = np.nan
    bars = np.cumsum(valid)
    amt20 = pd.Series(amt).rolling(20, min_periods=20).mean().to_numpy()
    cs_pb = np.cumsum(pb)
    M = pd.DataFrame({"t": t, "d": meas, "member": member[meas] & valid[meas], "bars": bars[meas], "amt20": amt20[meas],
                      "ma_stack": ma_stack.to_numpy()[meas], "ma60_up": ma60_up.to_numpy()[meas]})
    # Z7：特徵回看窗（d 往回第 120 根有效 K 棒 ～ d）內的斷點
    vb = np.flatnonzero(valid)
    k = np.searchsorted(vb, meas, side="right")
    lo = np.where(k >= 120, vb[np.maximum(k - 120, 0)], 0)
    M["pb_feat"] = [(cs_pb[d] - (cs_pb[a - 1] if a > 0 else 0)) > 0 for a, d in zip(lo, meas)]
    trd = valid.copy()
    return {"t": t, "M": M, "closes": closes, "opens": opens, "closes_net": closes_net, "opens_net": opens_net,
            "trd": trd, "cs_pb": cs_pb, "valid": valid, "first_bar": int(A["bars"][0]),
            "n_invalid": len(A["bad_dates"])}


# ═════════════ 季營收旗標（Z5）═════════════
def rev_flags(q, cal, meas):
    """q：該檔 quarterly_revenue 列。回 DataFrame(d, rev_ok, rev_exact, why, cal_ok)。"""
    q = q.sort_values("period_end")
    av = q["avail_date"].to_numpy("datetime64[ns]"); pe = q["period_end"].to_numpy("datetime64[ns]")
    val = q["value"].to_numpy(float); cq = q["cal_q"].to_numpy()
    out = []
    for d in meas:
        dd = np.datetime64(cal[d])
        m = av <= dd
        if m.sum() < NQ:
            out.append((d, False, False, "不足8季", False)); continue
        idx = np.flatnonzero(m)
        idx = idx[np.argsort(pe[idx], kind="stable")][-NQ:]
        gaps = np.diff(pe[idx]).astype("timedelta64[D]").astype(int)
        v = val[idx]
        cal_ok = len(set(cq[idx])) == NQ and all((pd.Period(b) - pd.Period(a)).n == 1 for a, b in zip(cq[idx][:-1], cq[idx][1:])) and bool((v > 0).all())
        if (gaps > GAPMAX).any():
            out.append((d, False, False, "缺季（相距>140天）", cal_ok)); continue
        if (v <= 0).any():
            out.append((d, False, False, "value≤0當缺", cal_ok)); continue
        mx = v[:-1].max()
        ok = bool(v[-1] >= mx - abs(mx) * TOL); ex = bool(v[-1] >= mx)
        out.append((d, ok, ex, "新高" if ok else "非新高", cal_ok))
    return pd.DataFrame(out, columns=["d", "rev_ok", "rev_exact", "why", "cal_ok"])


def window_metrics(eq, a, b, ann=ANN):
    seg = np.asarray(eq[a:b + 1], float)
    years = len(seg) / ann
    cagr = (seg[-1] / seg[0]) ** (1 / years) - 1
    peak = np.maximum.accumulate(seg); mdd = float(((seg - peak) / peak).min())
    return float(cagr), mdd


def label(c, m, cb, mb):
    ratio = c / abs(m); rb = cb / abs(mb)
    k1 = c > cb; k2 = ratio >= rb
    return ("合格" if (k1 and k2) else ("另列" if k1 else "不合格")), ratio, rb




# ═════════════ fixture（開跑前全過）═════════════
def w1b_fixtures():
    out = []
    cal = pd.bdate_range("2014-01-01", "2018-12-31")
    pe0 = pd.Timestamp("2014-03-31")

    def mkq(vals, gaps=None, lag=30):
        pes = [pe0]
        for g in (gaps or [91] * (len(vals) - 1)):
            pes.append(pes[-1] + pd.Timedelta(days=g))
        q = pd.DataFrame({"period_end": pes, "value": vals})
        q["avail_date"] = q["period_end"] + pd.Timedelta(days=lag)
        q["cal_q"] = q["period_end"].dt.to_period("Q").astype(str)
        return q
    d_after = lambda q, k: int(cal.searchsorted(q["avail_date"].iloc[k]))
    q = mkq([10, 11, 12, 13, 14, 15, 16, 17.0])
    F = rev_flags(q, cal, np.array([d_after(q, 7), d_after(q, 7) - 1]))
    assert F["rev_ok"].tolist() == [True, False] and F["why"].tolist() == ["新高", "不足8季"], F
    for fr, want, wex in ((0.5e-4, True, False), (2e-4, False, False)):
        v = [10, 11, 12, 13, 14, 15, 16, 16 * (1 - fr)]; q = mkq(v)
        F = rev_flags(q, cal, np.array([d_after(q, 7)]))
        assert (F["rev_ok"].iloc[0], F["rev_exact"].iloc[0]) == (want, wex), (fr, F)
    q = mkq([10, 11, 12, 13, 14, 15, 16, 17.0], gaps=[91, 91, 91, 141, 91, 91, 91])
    assert rev_flags(q, cal, np.array([d_after(q, 7)]))["why"].iloc[0] == "缺季（相距>140天）"
    q = mkq([10, 11, 12, 13, 14, 15, 16, 17.0], gaps=[91, 91, 91, 140, 91, 91, 91])
    assert rev_flags(q, cal, np.array([d_after(q, 7)]))["rev_ok"].iloc[0]
    q = mkq([10, 11, 0, 13, 14, 15, 16, 17.0])
    assert rev_flags(q, cal, np.array([d_after(q, 7)]))["why"].iloc[0] == "value≤0當缺"
    # 52／53 週：兩季落同一曆季 ⇒ 會計季版過、曆季逐字版不過
    q = mkq([10, 11, 12, 13, 14, 15, 16, 17.0], gaps=[84, 91, 91, 98, 84, 91, 91])
    q["period_end"] = pd.to_datetime(["2014-01-04", "2014-03-29", "2014-06-28", "2014-09-27", "2015-01-03", "2015-03-28", "2015-06-27", "2015-09-26"])
    q["cal_q"] = q["period_end"].dt.to_period("Q").astype(str); q["avail_date"] = q["period_end"] + pd.Timedelta(days=30)
    F = rev_flags(q, cal, np.array([d_after(q, 7)]))
    assert F["rev_ok"].iloc[0] and not F["cal_ok"].iloc[0], F
    # 前視：d 之後才可用的一季不影響 d 的判定
    q = mkq([10, 11, 12, 13, 14, 15, 16, 17.0, 5.0]); d = d_after(q, 7)
    assert rev_flags(q, cal, np.array([d]))["rev_ok"].iloc[0]
    out.append("FW1 季營收旗標：8 季遞增新高／d 前一天只有 7 季⇒不足／容差 0.5e-4 過（精確不過）、2e-4 不過／相距 141 天⇒缺季、140 天過／value＝0⇒當缺／"
               "52-53 週兩季同曆季⇒會計季版過、曆季逐字版不過／d 之後才可用的一季不影響 d")
    eq = np.r_[1.0, 1.2, 0.9, 1.1]
    c, m = window_metrics(eq, 0, 3, ann=4)
    assert abs(c - 0.1) < 1e-12 and abs(m - (0.9 / 1.2 - 1)) < 1e-12, (c, m)
    assert label(0.2, -0.3, 0.1, -0.3)[0] == "合格" and label(0.2, -0.9, 0.1, -0.3)[0] == "另列" and label(0.1, -0.1, 0.1, -0.3)[0] == "不合格"
    out.append("FW2 窗內年化／回落手算相符；標籤三種（合格／另列／條件一等號不過＝不合格）")
    rng = np.random.default_rng(3)
    c = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.02, 300))))
    ma20, ma60, ma120 = c.rolling(20, min_periods=20).mean(), c.rolling(60, min_periods=60).mean(), c.rolling(120, min_periods=120).mean()
    ms = ((c > ma20) & (ma20 > ma60) & (ma60 > ma120)).astype(float) * 100
    for t in (150, 200, 299):
        m20, m60, m120 = c[t - 19:t + 1].mean(), c[t - 59:t + 1].mean(), c[t - 119:t + 1].mean()
        assert ms[t] == (100.0 if (c[t] > m20 > m60 > m120) else 0.0)
        assert ((ma60 > ma60.shift(20)).astype(float) * 100)[t] == (100.0 if m60 > c[t - 79:t - 19].mean() else 0.0)
    out.append("FW3 ma_stack／ma60_up 向量式＝逐點手算（台股 p4_features 同式）")
    for s in out:
        print("✅", s, flush=True)
    return out

# ═════════════ 引擎（fork 共用）═════════════
_S = {}


def _run(args):
    seed, arm = args
    s = _S["arms"][arm]
    R.COST = s["cost"]
    try:
        out = R.simulate_mtm(s["sig"], RULE, N_SLOTS, np.random.default_rng(seed), s["closes"], s["opens"], _S["ncal"],
                             return_equity=True, pick=None, d_max=None, queue_days=0, cash_mode="zero",
                             tradable=_S["trad"], delist=_S["dl"])
    finally:
        R.COST = U.COST_ROUNDTRIP
    eq = out["equity"]; w0, w1, fe = _S["w0"], _S["w1"], _S["first_entry"]
    c, m = window_metrics(eq, w0, w1)
    c245, m245 = window_metrics(eq, w0, w1, 245); c_emp, _ = window_metrics(eq, w0, w1, _S["ann_emp"])
    cf, mf = window_metrics(eq, fe, w1)
    hv = out.get("hold_val")
    r = {"arm": arm, "seed": seed, "cagr": c, "mdd": m, "cagr_245": c245, "cagr_emp": c_emp, "cagr_from_first": cf, "mdd_from_first": mf,
         "trades": out["trades"], "slot_use": out["slot_use"], "delist_settled": out.get("tr_delist_settled"), "delist_ambig": out.get("tr_delist_ambig"),
         "halt_in": out.get("tr_halt_in"), "exit_delayed": out.get("tr_exit_delayed")}
    if arm == "main" and seed < SEED0 + 3:
        r["equity"] = eq[w0:w1 + 1].astype(float)
    return r


def main():
    t0 = time.time()
    U.assert_pinned()
    mode = "pre" if "--pre" in sys.argv else "main"
    fx = w1b_fixtures()
    procs = int(sys.argv[sys.argv.index("--procs") + 1]) if "--procs" in sys.argv else 2
    nseed = int(sys.argv[sys.argv.index("--seeds") + 1]) if "--seeds" in sys.argv else NSEED
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    calF = U.load_calendar(); cal = calF[calF >= MB.CAL0]; n = len(cal)
    w0 = int(cal.searchsorted(U.WINDOW[0])); w1 = int(cal.searchsorted(U.WINDOW[1]))
    assert cal[w0] == U.WINDOW[0] and cal[w1] == U.WINDOW[1]
    per = cal.to_period("M")
    meas = np.flatnonzero(np.r_[True, per[1:] != per[:-1]])
    meas = meas[(meas + 1 + HOLD - 1) < n]                   # 台股同：xpos 必須在日曆內
    tick = [t for t in U.universe_table()["ticker"] if t not in set(U.no_ohlc_tickers())]
    if lim:
        tick = tick[:lim]
    os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    print("[資料] {}｜日曆 {}～{}｜窗 {}～{}｜量測日 {} 個（{}～{}）｜{} 檔｜{}".format(U.data_commit()[:10], cal[0].date(), cal[-1].date(),
          cal[w0].date(), cal[w1].date(), len(meas), cal[meas[0]].date(), cal[meas[-1]].date(), len(tick), mode), flush=True)
    with Pool(procs, initializer=_init, initargs=(cal, w0, w1, meas)) as pool:
        res = pool.map(load_one, tick, chunksize=4)
    ST = {r["t"]: r for r in res if r is not None}
    print("[讀檔] 可用 {} 檔｜{:.0f}s".format(len(ST), time.time() - t0), flush=True)
    q = U.quarterly_revenue()
    na = U.revenue_not_applicable()
    parts = []
    for t, r in ST.items():
        M = r["M"].copy()
        qt = q[q["ticker"] == t]
        if len(qt):
            F = rev_flags(qt, cal, meas); M = M.merge(F, on="d", how="left")
        else:
            M["rev_ok"] = False; M["rev_exact"] = False; M["why"] = "不適用（無營收列）"; M["cal_ok"] = False
        parts.append(M)
    P = pd.concat(parts, ignore_index=True)
    P["date"] = [str(cal[d].date()) for d in P["d"]]
    P["base"] = P["member"] & (P["bars"] >= MIN_BARS)
    P["tech"] = (P["ma_stack"] == 0) & (P["ma60_up"] == 100)
    P["cand"] = P["base"] & P["rev_ok"]
    P["sig"] = P["cand"] & P["tech"]
    P["sig_exact"] = P["base"] & P["rev_exact"] & P["tech"]
    P["sig_cal"] = P["base"] & P["cal_ok"] & P["rev_ok"] & P["tech"]
    # 訊號表（Z6）
    rows = []; drop = {"xpos≥日曆": 0, "開盤不可用": 0, "收盤不可用": 0}
    for r in P[P["sig"] | P["sig_exact"]].itertuples():
        S = ST[r.t]; e = int(r.d) + 1; x = e + HOLD - 1
        if x >= n:
            drop["xpos≥日曆"] += 1; continue
        o = S["opens"][e]; c = S["closes"][x]
        if not (np.isfinite(o) and o > 0):
            drop["開盤不可用"] += 1; continue
        if not np.isfinite(c):
            drop["收盤不可用"] += 1; continue
        cs = S["cs_pb"]
        rows.append({"sid": r.t, "entry_pos": e, "xpos_H120": x, "g_H120": c / o - 1.0, "month": cal[int(r.d)].strftime("%Y-%m"),
                     "pb_feat": bool(r.pb_feat), "pb_hold": bool((cs[x] - cs[e - 1]) > 0), "measure": int(r.d),
                     "tol": bool(r.sig), "exact": bool(r.sig_exact)})
    sigall = pd.DataFrame(rows).sort_values(["entry_pos", "sid"]).reset_index(drop=True)
    sigall["pb"] = sigall["pb_feat"] | sigall["pb_hold"]
    sig = sigall[sigall["tol"]].reset_index(drop=True)                       # 定案①：容差版（pre 盤點仍數全部容差訊號）
    SIGCOLS = ["sid", "entry_pos", "xpos_H120", "g_H120", "month"]
    SIG = {"main": sigall[sigall["tol"] & ~sigall["pb"]][SIGCOLS].reset_index(drop=True),          # 定案①(a)＋②(a)
           "exact": sigall[sigall["exact"] & ~sigall["pb"]][SIGCOLS].reset_index(drop=True),      # 敏感度①：精確 ≥
           "keep_pb": sigall[sigall["tol"]][SIGCOLS].reset_index(drop=True)}                      # 敏感度②：保留跨斷點
    # pre 彙總
    inb = P[P["base"]]
    liq_min = float(inb["amt20"].min()); liq_q = inb["amt20"].quantile([0.001, 0.01, 0.5]).to_dict()
    per_m = P.groupby("d")["sig"].sum()
    per_m = per_m[[d for d in per_m.index if d >= w0 - 25 and d <= w1]]
    first_sig = int(sig["entry_pos"].min()) if len(sig) else None
    why = inb["why"].value_counts().to_dict()
    kicked = inb[inb["rev_ok"] & ~inb["cal_ok"]]
    vneg = q[q["value"] <= 0]
    PRE = {"性質": "USREG-W1b pre：候選盤點與讀法計數（⛔ 未跑引擎、未讀任何持有期報酬）", "資料commit": U.data_commit(),
           "判定窗": [str(cal[w0].date()), str(cal[w1].date())], "量測日": {"個數": int(len(meas)), "首": str(cal[meas[0]].date()), "末": str(cal[meas[-1]].date())},
           "可用檔數": len(ST), "無效K棒": int(sum(r["n_invalid"] for r in ST.values())),
           "在指數且bars_ok的股月": int(len(inb)),
           "Z4_liq_amt20美元": {"最小": liq_min, "p0.1": float(liq_q[0.001]), "p1": float(liq_q[0.01]), "中位": float(liq_q[0.5]),
                              "台幣5000萬換算（25～35）": [50e6 / 35, 50e6 / 25], "最小值高於換算上限": bool(liq_min > 50e6 / 25)},
           "Z5_營收判定帳（在指數且bars_ok股月）": {k: int(v) for k, v in why.items()},
           "Z5_value≤0": {"列數": int(len(vneg)), "檔數": int(vneg["ticker"].nunique())},
           "Z5_不適用19檔": sorted(na.keys()), "Z5_不適用19檔_原因": na,
           "Z5_容差版與精確版訊號差（股月）": int((P["sig"] != P["sig_exact"]).sum()),
           "Z5_描述臂_曆季逐字會被踢出": {"在指數且bars_ok且營收新高的股月": int(len(kicked)), "檔數": int(kicked["t"].nunique()),
                                   "其中也過技術條件（訊號）": int((kicked["tech"]).sum()),
                                   "訊號數_會計季版": int(P["sig"].sum()), "訊號數_曆季逐字版": int(P["sig_cal"].sum())},
           "候選（在指數∧bars∧營收）股月": int(P["cand"].sum()), "訊號（再∧¬ma_stack∧ma60_up）股月": int(P["sig"].sum()),
           "訊號表（Z6 剔除後）": int(len(sig)), "Z6剔除": drop,
           "Z7_斷點": {"特徵回看窗跨斷點的訊號": int(sig["pb_feat"].sum()) if len(sig) else 0, "持有期跨斷點的訊號": int(sig["pb_hold"].sum()) if len(sig) else 0},
           "第一個進場日": str(cal[first_sig].date()) if first_sig is not None else None,
           "每月訊號數（窗內）": {"月數": int(len(per_m)), "零訊號月": int((per_m == 0).sum()), "中位": float(per_m.median()),
                          "p10": float(per_m.quantile(0.1)), "p90": float(per_m.quantile(0.9)), "≥8的月比例": float((per_m >= 8).mean())},
           "每年訊號數": {str(k): int(v) for k, v in sig.groupby(sig["month"].str[:4]).size().items()} if len(sig) else {},
           "倒閉銀行": "SIVB、FRC、SBNY 無 OHLC 且屬不適用 19 檔 ⇒ 依構造不可能被選到 ⇒ −100% 下界與最後成交價版皆不適用",
           "種子": "default_rng(102000＋r)，r＝0…{}".format(nseed - 1), "fixture": fx}
    p = os.path.join(WORK, "panel_monthly.csv.gz")
    P.drop(columns=[]).to_csv(p, index=False)
    p2 = os.path.join(WORK, "signals.csv.gz"); sigall.to_csv(p2, index=False)
    shas = [(os.path.basename(p), len(P), sha256f(p)), (os.path.basename(p2), len(sigall), sha256f(p2))]
    stop = []
    if not PRE["Z4_liq_amt20美元"]["最小值高於換算上限"]:
        stop.append("Z4 流動性閘有作用")
    if PRE["Z5_容差版與精確版訊號差（股月）"] > 0:
        pass                                          # 定案①（協調者轉達）：容差、精確版當敏感度
    if PRE["Z7_斷點"]["特徵回看窗跨斷點的訊號"] + PRE["Z7_斷點"]["持有期跨斷點的訊號"] > 0:
        pass                                          # 定案②：剔除、保留版當敏感度
    PRE["停下條件"] = stop or "無"
    PRE["逐筆檔sha（repo外）"] = {a: {"rows": b, "sha256": c} for a, b, c in shas}
    json.dump(PRE, open(os.path.join(OUT, "pre_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps({k: v for k, v in PRE.items() if k not in ("Z5_不適用19檔_原因",)}, ensure_ascii=False, indent=1, default=str), flush=True)
    if mode == "pre":
        with io.open(os.path.join(OUT, "pre_work_sha.csv"), "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n"); w.writerow(["file（~/us_work/usw1b/，repo 外）", "rows", "sha256"]); w.writerows(shas)
        return
    if stop:
        raise SystemExit("⛔ 停下條件成立：{} ⇒ 不跑本體".format(stop))

    # ═════════════ 本體 ═════════════
    sids = sorted(ST)
    closes = {s: ST[s]["closes"] for s in sids}; opens = {s: ST[s]["opens"] for s in sids}
    closes_n = {s: ST[s]["closes_net"] for s in sids}; opens_n = {s: ST[s]["opens_net"] for s in sids}
    # ⭐ 引擎的出場毛報酬取自 sig 的 g_H120 欄 ⇒ 預扣稅版要用淨股息價重算 g（⛔ 否則只有逐日市值是淨的）
    SIG["main_net"] = SIG["main"].copy()
    SIG["main_net"]["g_H120"] = [closes_n[s][x] / opens_n[s][e] - 1.0 for s, e, x in zip(SIG["main_net"]["sid"], SIG["main_net"]["entry_pos"], SIG["main_net"]["xpos_H120"])]
    assert np.isfinite(SIG["main_net"]["g_H120"]).all()
    z = np.zeros(n, bool)
    trad = {s: {"trd": ST[s]["trd"], "up_o": z, "dn_o": z, "dn_c": z} for s in sids}
    dl = TRD.delist_status(trad, cal)
    bench = U.benchmark_tr("SP500TR").reindex(cal).ffill().to_numpy(float)
    spy = U.benchmark_tr("SPY").reindex(cal).ffill().to_numpy(float)
    gspc = pd.read_csv(U._p("macro", "yahoo_GSPC.csv"), usecols=["date", "close"], dtype={"date": str})
    gspc = pd.Series(gspc["close"].to_numpy(float), pd.DatetimeIndex(pd.to_datetime(gspc["date"]))).reindex(cal).ffill().to_numpy()
    br = bench[1:] / bench[:-1]; gr = gspc[1:] / gspc[:-1]
    bench_net = np.r_[1.0, np.cumprod(gr + NET_DIV * (br - gr))] * bench[0]
    first_entry = int(SIG["main"]["entry_pos"].min())
    ann_emp = (w1 - w0 + 1) / ((cal[w1] - cal[w0]).days / 365.25)
    B = {}
    for nm, s_ in (("SP500TR", bench), ("SPY備援（描述）", spy), ("SP500TR_扣30%股息（描述）", bench_net)):
        c_, m_ = window_metrics(s_, w0, w1); cf_, mf_ = window_metrics(s_, first_entry, w1)
        B[nm] = {"年化": c_, "回落": m_, "比值": c_ / abs(m_), "年化_245": window_metrics(s_, w0, w1, 245)[0], "年化_實際": window_metrics(s_, w0, w1, ann_emp)[0],
                 "自第一個進場日_年化": cf_, "自第一個進場日_回落": mf_}
    _S.update(sig=SIG["main"], ncal=n, trad=trad, dl=dl, w0=w0, w1=w1, first_entry=first_entry, ann_emp=ann_emp,
              arms={"main": {"closes": closes, "opens": opens, "cost": COST, "sig": SIG["main"]},
                    "exact": {"closes": closes, "opens": opens, "cost": COST, "sig": SIG["exact"]},
                    "keep_pb": {"closes": closes, "opens": opens, "cost": COST, "sig": SIG["keep_pb"]},
                    "cost_0.02%": {"closes": closes, "opens": opens, "cost": COST_SENS[0], "sig": SIG["main"]},
                    "cost_0.10%": {"closes": closes, "opens": opens, "cost": COST_SENS[1], "sig": SIG["main"]},
                    "div_net30": {"closes": closes_n, "opens": opens_n, "cost": COST, "sig": SIG["main_net"]}})
    jobs = [(SEED0 + r, a) for a in ("main", "exact", "keep_pb", "cost_0.02%", "cost_0.10%", "div_net30") for r in range(nseed)]
    with Pool(procs) as pool:
        out = pool.map(_run, jobs, chunksize=4)
    print("[引擎] {} 次｜{:.0f}s".format(len(out), time.time() - t0), flush=True)
    EQ = {r["seed"]: r.pop("equity") for r in out if "equity" in r}
    # 給獨立查核：種子 102000 主臂的逐筆成交（audit）與整條權益（repo 外）
    aud = []
    R.COST = COST
    s0 = R.simulate_mtm(_S["sig"], RULE, N_SLOTS, np.random.default_rng(SEED0), closes, opens, n, return_equity=True, pick=None, d_max=None,
                        queue_days=0, cash_mode="zero", tradable=trad, delist=dl, audit=aud)
    A_ = pd.DataFrame(aud); A_["date"] = [str(cal[t].date()) for t in A_["t"]]
    p = os.path.join(WORK, "audit_seed102000.csv"); A_.to_csv(p, index=False); shas.append((os.path.basename(p), len(A_), sha256f(p)))
    p = os.path.join(WORK, "equity_seed102000_full.csv")
    pd.DataFrame({"date": [str(d.date()) for d in cal], "equity": s0["equity"]}).to_csv(p, index=False); shas.append((os.path.basename(p), n, sha256f(p)))
    assert abs(window_metrics(s0["equity"], w0, w1)[0] - float(pd.DataFrame(out).query("arm=='main' and seed==@SEED0")["cagr"].iloc[0])) < 1e-12
    D = pd.DataFrame(out)
    p = os.path.join(WORK, "seeds.csv"); D.to_csv(p, index=False); shas.append((os.path.basename(p), len(D), sha256f(p)))
    p = os.path.join(WORK, "equity_main_first3seeds.csv")
    pd.DataFrame({"date": [str(d.date()) for d in cal[w0:w1 + 1]], **{str(k): v for k, v in EQ.items()}}).to_csv(p, index=False)
    shas.append((os.path.basename(p), w1 - w0 + 1, sha256f(p)))
    RES = {"性質": "USREG-W1b 本體（組合層；判準 seq2 §五 ＝ 台股 seq141 同形，對 ^SP500TR 同窗）", "資料commit": U.data_commit(),
           "判定窗": [str(cal[w0].date()), str(cal[w1].date())], "ANN": ANN, "種子數": nseed, "訊號表筆數": {k: int(len(v)) for k, v in SIG.items()}, "讀法定案": "①容差（台股 rev_hi24 先例）②跨轉接層斷點剔除；敏感度 exact／keep_pb",
           "第一個進場日": str(cal[first_entry].date()), "基準": B, "臂": {}}
    for arm, g in D.groupby("arm"):
        bref = B["SP500TR_扣30%股息（描述）"] if arm == "div_net30" else B["SP500TR"]
        cm, mm = float(g["cagr"].median()), float(g["mdd"].median())
        lab, ratio, rb = label(cm, mm, bref["年化"], bref["回落"])
        l245 = label(float(g["cagr_245"].median()), mm, bref["年化_245"], bref["回落"])[0]
        lemp = label(float(g["cagr_emp"].median()), mm, bref["年化_實際"], bref["回落"])[0]
        cf, mf = float(g["cagr_from_first"].median()), float(g["mdd_from_first"].median())
        lff = label(cf, mf, bref["自第一個進場日_年化"], bref["自第一個進場日_回落"])[0]
        seedlab = [label(c_, m_, bref["年化"], bref["回落"])[0] for c_, m_ in zip(g["cagr"], g["mdd"])]
        RES["臂"][arm] = {"年化中位": cm, "回落中位": mm, "比值": ratio, "基準比值": rb, "標籤": lab,
                         "年化p10": float(g["cagr"].quantile(0.1)), "年化p90": float(g["cagr"].quantile(0.9)),
                         "回落p10": float(g["mdd"].quantile(0.1)), "回落p90": float(g["mdd"].quantile(0.9)),
                         "逐種子標籤比例": {k: float(np.mean([x == k for x in seedlab])) for k in ("合格", "另列", "不合格")},
                         "標籤_ANN245": l245, "標籤_ANN實際{:.2f}".format(ann_emp): lemp,
                         "自第一個進場日_年化中位": cf, "自第一個進場日_回落中位": mf, "自第一個進場日_標籤（描述）": lff,
                         "交易數中位": float(g["trades"].median()), "槽位使用率中位": float(g["slot_use"].median()),
                         "下市了結中位": float(g["delist_settled"].median()), "下市不明中位": float(g["delist_ambig"].median()),
                         "進場日無K棒（名額持現金）中位": float(g["halt_in"].median()), "出場延後中位": float(g["exit_delayed"].median())}
        print("[{}] 年化中位 {:+.2%} 回落中位 {:+.2%} 比值 {:.3f}（基準 {:+.2%}／{:+.2%}／{:.3f}）⇒ {}".format(
            arm, cm, mm, ratio, bref["年化"], bref["回落"], rb, lab), flush=True)
    RES["判定"] = RES["臂"]["main"]["標籤"]
    RES["逐筆檔sha（repo外）"] = {a: {"rows": b, "sha256": c} for a, b, c in shas}
    with io.open(os.path.join(OUT, "work_sha.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n"); w.writerow(["file（~/us_work/usw1b/，repo 外）", "rows", "sha256"]); w.writerows(shas)
    RES["耗時s"] = round(time.time() - t0)
    json.dump(RES, open(os.path.join(OUT, "body_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print("完成 {:.0f}s".format(time.time() - t0))


if __name__ == "__main__":
    main()
