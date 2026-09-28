# -*- coding: utf-8 -*-
"""PREREG長線戰法 seq1 件 T：米奈爾維尼趨勢樣板（台股策略線 登錄 sha dce9829bd0736d4f；裁定 seq272 §二 發號、全件 N ＋3）——回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLongT [--procs 2] [--reps 1000]
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchLongT_check.py

使用者原話（逐字，登錄 §依據）：「學習看看週線的戰法」「看看有沒有其他的」「還有嗎？」「好你看看排幾個來看看」⇒「試試看」
⭐ 新件 ⇒ 照裁定 seq271：程式開頭 universe_gate.set_innov_ky(True)（c131ded0a0；「-創」「-KY創」都剔）
═══ 登錄 §一（寫死）＋ 本線讀法（T 標，⭐ 看任何本件數字前寫死）═══
 八條（t−1 還原價）：① C＞MA150 且 C＞MA200 ② MA150＞MA200 ③ MA200＞21 個交易日前的 MA200 ④ MA50＞MA150 且 MA50＞MA200 ⑤ C＞MA50
   ⑥ C ≥ 250 日最低收盤×1.30 ⑦ C ≥ 250 日最高收盤×0.75 ⑧ RS 在當日 eligible 前 30%；RS ＝ 2×r63＋r126＋r189＋r252
 T1 世界與換股簿 ＝ researchMomX（PREREG動能改良）同一套：換股日 e ＝ 當月 W1 量測日（面板 measure_date）次一交易日、季 ＝ 1／4／7／10 月；
    eligible ＝ 量測日面板 eligible（主 panel_ext；早年 liq_ok∧bars_ok）；⚠ 面板是舊快取（panel_ext.csv.gz、早年 sig_main/panel.csv.gz），
    母體再經 gate3（innov_ky 開）交集 ⇒ 「-KY創」在換股簿裡剔除（寫明）
    換股簿 researchMomX.sim_book：續抱仍入選、落選開盤賣、新入選依名次開盤買（漲停／停牌 ⇒ 該名額持現金、不遞補）、等權 equity÷N、成本 0.585%、
    ⭐ 停止交易強制出場：開；窗尾照市值 ⇒ 依構造不截斷（t1_censor 不適用，照實寫）
 T2 量測日 m ＝ e − 1；每檔用「≤ m 的最後一根有效 K 棒」與它之前的有效 K 棒（MA、250 日高低、r_n 都以有效 K 棒計）；需 ≥ 253 根（r252）
 T3 ⑧ 前 30% ＝ 當期 eligible 中 RS 可算者依 RS 由高到低（同值依代號）名次 ≤ ceil(0.3 × 可算數)
 T4 乙族營收：最新可用月營收創 24 月新高 ＝ p4_features.rev_hi24_flags（researchMLlite 同一份月營收：早年版面 2003～2014 ＋ 主快照）在 m 日的值 ＝ 100；0／NaN ⇒ 不成立
 T5 選股：樣板內（乙另加營收）依 RS 由高到低取前 N（同值依代號）；不足 N ⇒ 剩現金
 T6 格：族 {甲, 乙} × 頻率 {月, 季} × N {10, 20} ＝ 8
 T7 段：主 ＝ main 快照 2017-03-02～2026-08-24（探索 2017-03-02～2021-12-30、確認 2022-01-03～2026-08-24）；
    早年 ＝ 早年版面（只上市）2005-03-01～2014-12-31（資料 2004-02-11 起、RS／MA200 要 253 根 ⇒ 第一個可算的換股月 2005-03）；0050 同窗各自由該世界 0050 算
 T8 退化（事前排除）：探索段 平均持股 ＜ N÷2 或 換股簿現金比例 ＞ 30%；挑：探索段先合格、再比值（同分 年化高、甲先、月先、N 小）；
    判：確認、早年各照使用者判準，件標籤取較嚴；「穩」（收緊讀法）＝ 挑中格的相鄰兩格（同族，只改頻率、只改 N）確認與早年標籤都不低於挑中格
 T9 假訊號（同池隨機）：挑中格頻率與 N；每個換股日從「eligible ∩ RS 可算」不放回抽「與該期真名單同數」；rng default_rng([20260928, 7, r])；p ＝ 隨機年化 ≥ 本格
 T10 新規矩 ③：挑中格確認或早年「合格／另列」⇒ 描述 (a) 全賣全買 (b) 持有期間收盤跌破 MA60 次日開盤賣（researchMomX R12 同式）
 T11 附帶（裁定 seq272 §二 2）：挑中格主窗逐日持股與 營量 v1（T1、種子 7000）、營量趨勢 乙_T3_H40（種子 7000）的重疊率
    ＝ 每日 |本格 ∩ 對方| ÷ |本格|（本格持股 ＝ 換股日持股、停止交易後剔除；對方 ＝ 引擎 audit 逐日重建）在本格持股 ≥ 1 的日子平均；另報 ÷ |對方|
    閘：營量 v1 ＝ resultsT1fix c13 t1 種子 0 eq_sha；乙_T3_H40 ＝ resultsYLtrend seeds_main 種子 0 eq_sha
    （對方兩件是已判件 ⇒ 重建時照它們當時設定 innov_ky 關，重建完開回來）
 T12 描述臂（不計 N）溫斯坦第二階段：週 K 同 PREREG週線（researchWeekly.weekly_bars，週加減以有交易日的週計）；訊號週 t：週 MA30[t] ＞ 週 MA30[t−4]、週收 ＞ 前 26 週最高週收、
    週量 ≥ 前 10 週平均 × 2、股價÷0050（週收比）＞ 其 52 週均線 ⇒ 下週第一根有效 K 棒開盤買；持有中（進場週起）週收 ＜ 週 MA30 ⇒ 下週第一根有效 K 棒開盤賣；
    資料尾未賣 ⇒ 日曆最後一日收盤計；20 檔、RS（訊號週最後一根的 IBD RS）高者先；引擎 research11.simulate_mtm（stop_force 開、pick＝RS、queue 0）
 ⚠ 現實版描述（登錄 §五）：換股簿沒有現實版接法 ⇒ 本件未做（寫明）
輸出 backtest/resultsLongT/
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import html
import json
import math
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchMomX as MX
from backtest import universe_gate as UG
UG.set_innov_ky(True)                                                        # ⭐ 裁定 seq271：新件開
from backtest import research11 as R11
from backtest import research13 as R13
from backtest import rerun17 as RR
from backtest import p4_features as P4F
from backtest import researchYLexit as YX
from backtest import researchWeekly as RW
from backtest import chart_svg as CS
D, TR, H2 = MX.D, MX.TR, MX.H2

OUT = "backtest/resultsLongT"
F_HTML = "趨勢樣板_20260928.html"
PREREG_SHA = "dce9829bd0736d4f"
PREREG_SHA2 = "04f9758bb33bc345"                                              # seq2（台股 23:53；補件 I 主格、件 T 重疊率一行；件 T 規則不動）
RAW = "「學習看看週線的戰法」「看看有沒有其他的」「還有嗎？」「好你看看排幾個來看看」⇒「試試看」"
COST = MX.COST
EARLY_REV = os.path.expanduser("~/earlydata/3edc0e2206/main/data/mops/revenue_hist")
MAIN = dict(MX.MAIN)
EARLY = dict(MX.EARLY, w=("2005-03-01", "2014-12-31"), segs={"早年": ("2005-03-01", "2014-12-31")})
FAMS, FREQS, NS = ("甲", "乙"), ("月", "季"), (10, 20)
FNAME = {"甲": "純樣板", "乙": "樣板＋營收創 24 月新高"}
LORD = MX.LORD
_G: dict = {}


# ═════════════ 特徵 ═════════════
def tables(Wd, flag):
    """每個換股日：pool（eligible ∩ RS 可算）、RS、七條（①～⑦）全過的集合、營收旗標集合。另回 每檔逐根 RS（給溫斯坦排序）。"""
    P, reb = Wd["P"], Wd["reb"]
    ess = sorted(reb)
    per = {e: {"RS": {}, "ok7": set(), "rev": set()} for e in ess}
    RSB = {}
    fl = flag.to_numpy(float) if flag is not None else None; fcol = {s: j for j, s in enumerate(flag.columns)} if flag is not None else {}
    elig = {e: set(reb[e]) for e in ess}
    for s in Wd["sids"]:
        v = P[s]["valid"]; idx = np.flatnonzero(v)
        if len(idx) < 253:
            continue
        cb = P[s]["c"][idx]
        m50 = pd.Series(cb).rolling(50).mean().to_numpy(); m150 = pd.Series(cb).rolling(150).mean().to_numpy(); m200 = pd.Series(cb).rolling(200).mean().to_numpy()
        lo = pd.Series(cb).rolling(250).min().to_numpy(); hi = pd.Series(cb).rolling(250).max().to_numpy()
        rs = np.full(len(cb), np.nan)
        rs[252:] = 2 * (cb[252:] / cb[252 - 63:-63] - 1) + (cb[252:] / cb[252 - 126:-126] - 1) + (cb[252:] / cb[252 - 189:-189] - 1) + (cb[252:] / cb[:-252] - 1)
        RSB[s] = (idx, rs)
        for e in ess:
            if s not in elig[e]:
                continue
            i = int(np.searchsorted(idx, e - 1, side="right")) - 1
            if i < 252 or not np.isfinite(rs[i]):
                continue
            C = cb[i]
            per[e]["RS"][s] = float(rs[i])
            ok = (C > m150[i] and C > m200[i] and m150[i] > m200[i] and m200[i] > m200[i - 21] and m50[i] > m150[i] and m50[i] > m200[i] and C > m50[i]
                  and C >= lo[i] * 1.30 and C >= hi[i] * 0.75)
            if ok:
                per[e]["ok7"].add(s)
            j = fcol.get(s)
            if fl is not None and j is not None and fl[e - 1, j] == 100:
                per[e]["rev"].add(s)
    for e in ess:
        R = per[e]["RS"]; order = sorted(R, key=lambda s: (-R[s], s)); cut = int(math.ceil(0.3 * len(order)))
        per[e]["top30"] = set(order[:cut]); per[e]["pool"] = sorted(R)
        per[e]["tmpl"] = per[e]["ok7"] & per[e]["top30"]
    return per, RSB


def rev_flags(cal, main):
    fs = sorted(glob.glob(os.path.join(EARLY_REV, "*.csv")))
    if main:
        fs += sorted(glob.glob(os.path.join(D.DATA, "mops", "revenue_hist", "*.csv")))
    df = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收"]) for f in fs])
    df["rev"] = pd.to_numeric(df["當月營收"], errors="coerce"); df = df.drop_duplicates(["stock_id", "period"], keep="last")
    rev = df.pivot(index="period", columns="stock_id", values="rev").sort_index()
    return P4F.rev_hi24_flags(rev, cal), (str(rev.index.min()), str(rev.index.max()))


def select(Wd, TT, fam, freq, N):
    sel = {}
    for e in Wd["rebs"]:
        if freq == "季" and Wd["cal"][e].month not in (1, 4, 7, 10):
            continue
        x = TT[e]; S_ = x["tmpl"] if fam == "甲" else (x["tmpl"] & x["rev"])
        sel[e] = sorted(S_, key=lambda s: (-x["RS"][s], s))[:N]
    return sel


def cname(fam, freq, N):
    return f"{fam}_{freq}_N{N}"


def run_world(Wd, TT, log, tag):
    cal = Wd["cal"]; segs = MAIN["segs"] if tag == "主" else EARLY["segs"]
    SEGP = {nm: (max(int(cal.searchsorted(pd.Timestamp(a))), Wd["w0"]), min(int(cal.searchsorted(pd.Timestamp(b), side="right") - 1), Wd["w1"])) for nm, (a, b) in segs.items()}
    Z = {nm: R13.window_stats(Wd["bench"], 0, Wd["n"], a, b + 1) for nm, (a, b) in SEGP.items()}
    rows = []; RES = {}; SEL = {}
    for fam in FAMS:
        for fq in FREQS:
            for N in NS:
                k = cname(fam, fq, N); sel = select(Wd, TT, fam, fq, N); res = MX.sim_book(sel, Wd, N)
                RES[k] = res; SEL[k] = sel
                for nm, (a, b) in SEGP.items():
                    rs = [e for e in sorted(sel) if a <= e <= b]
                    st = MX.seg_stats(Wd, res, a, b, N, rs)
                    st["標籤"] = MX.label(st["年化"], st["回落"], Z[nm][0], Z[nm][1])
                    st["入選平均檔數"] = float(np.mean([len(sel[e]) for e in rs])) if rs else float("nan")
                    rows.append({"世界": tag, "格": k, "族": fam, "頻率": fq, "N": N, "段": nm, **st, **{f"cnt_{c_}": v for c_, v in res["cnt"].items()}})
    log(f"[{tag}] 8 格完成")
    return pd.DataFrame(rows), RES, SEL, SEGP, Z


def _fake(args):
    tag, key, r = args
    Wd, TT, SEL, SEGP = _G[tag]["Wd"], _G[tag]["TT"], _G[tag]["SEL"], _G[tag]["SEGP"]
    fam, fq, N = key.split("_"); N = int(N[1:])
    rng = np.random.default_rng([20260928, 7, r])
    sel = {}
    for e, s_ in SEL[key].items():
        pool = TT[e]["pool"]; k = min(len(s_), len(pool))
        sel[e] = list(rng.choice(pool, size=k, replace=False)) if k else []
    res = MX.sim_book(sel, Wd, N)
    out = {"世界": tag, "r": r}
    for nm, (a, b) in SEGP.items():
        c, m = R13.window_stats(res["eq"], 0, len(res["eq"]), a, b + 1)
        out[f"{nm}_年化"] = float(c); out[f"{nm}_回落"] = float(m)
    return out


# ═════════════ 溫斯坦第二階段（描述臂） ═════════════
def _vol_init(cal, data):
    D.DATA = data; _G["cal"] = cal


def load_vol(args):
    sid, mk = args
    st = D.load_stock(sid, mk, _G["cal"])
    return sid, (None if st is None else pd.to_numeric(st.df["volume"], errors="coerce").to_numpy(np.float64))


def weinstein(Wd, VOL, RSB, tag, log):
    cal, n, P = Wd["cal"], Wd["n"], Wd["P"]
    wk, wf, wl = RW.weeks_of(cal); nw = len(wf)
    bench = Wd["bench"]
    rows = []
    for s in Wd["sids"]:
        v, o, c = P[s]["valid"], P[s]["o"], P[s]["c"]
        if s not in VOL or VOL[s] is None:
            continue
        wks, WO, WH, WL_, WC, WV = RW.weekly_bars(v, o, c, c, c, VOL[s], wk)
        m = len(wks)
        if m < 60:
            continue
        ma30 = pd.Series(WC).rolling(30).mean().to_numpy()
        hi26 = pd.Series(WC).shift(1).rolling(26).max().to_numpy(); v10 = pd.Series(WV).shift(1).rolling(10).mean().to_numpy()
        rsl = WC / bench[wl[wks]]; ma52 = pd.Series(rsl).rolling(52).mean().to_numpy()
        m4 = np.r_[np.full(4, np.nan), ma30[:-4]]
        with np.errstate(invalid="ignore"):
            cond = (ma30 > m4) & (WC > hi26) & (WV >= 2 * v10) & (rsl > ma52)
        vd = np.flatnonzero(v)
        for t in np.flatnonzero(cond):
            w = int(wks[t])
            if w + 1 >= nw:
                continue
            j = int(np.searchsorted(vd, wf[w + 1]))
            if j >= len(vd) or vd[j] > wl[w + 1]:
                continue
            ent = int(vd[j])
            if ent < Wd["w0"] or ent > Wd["w1"]:
                continue
            xs = None
            for t2 in range(t + 1, m):
                if wks[t2] < w + 1:
                    continue
                if np.isfinite(ma30[t2]) and WC[t2] < ma30[t2]:
                    xs = int(wks[t2]); break
            if xs is not None and xs + 1 < nw:
                jx = int(np.searchsorted(vd, wf[xs + 1]))
                if jx < len(vd):
                    xp = int(vd[jx]); g = o[xp] / o[ent] - 1.0
                else:
                    xp = n - 1; g = c[n - 1] / o[ent] - 1.0
            else:
                xp = n - 1; g = c[n - 1] / o[ent] - 1.0
            ib, rsv = RSB.get(s, (None, None))
            rs = np.nan
            if ib is not None:
                ii = int(np.searchsorted(ib, wl[w], side="right")) - 1
                rs = float(rsv[ii]) if ii >= 0 else np.nan
            rows.append({"sid": s, "k": int(t), "pos": int(wl[w]), "entry_pos": ent, "xpos_W": xp, "g_W": float(g), "RS": rs})
    sig = pd.DataFrame(rows).sort_values(["entry_pos", "sid"]).reset_index(drop=True)
    ss = sorted(set(sig["sid"]))
    closes = {s: P[s]["c"].astype(np.float32) for s in ss}; opens = {s: P[s]["o"].astype(np.float32) for s in ss}
    aud = []
    o_ = R11.simulate_mtm(sig, "W", 20, np.random.default_rng(7000), closes, opens, n, return_equity=True, log=[], d_max=None, pick="RS", queue_days=0,
                          stop_force=Wd["SF"], audit=aud)
    log(f"[{tag} 溫斯坦] 訊號 {len(sig)}｜成交 {sum(1 for a in aud if a['side'] == 'buy')}")
    return sig, np.asarray(o_["equity"], float), aud


# ═════════════ 重疊率（裁定 seq272 §二 2） ═════════════
def daily_from_audit(aud, n):
    H = [set() for _ in range(n)]; cur = set(); by = {}
    for a in aud:
        by.setdefault(a["t"], []).append(a)
    for t in range(n):
        for a in sorted(by.get(t, []), key=lambda z: z["side"] != "sell"):
            if a["side"] == "sell":
                cur.discard(a["sid"])
            else:
                cur.add(a["sid"])
        H[t] = set(cur)
    return H


def daily_from_book(res, Wd):
    H = [set() for _ in range(Wd["n"])]; cur = set()
    for t in range(Wd["w0"], Wd["w1"] + 1):
        if t in res["hold"]:
            cur = set(res["hold"][t])
        cur = {s for s in cur if not (s in Wd["SF"] and t > Wd["SF"][s])}
        H[t] = set(cur)
    return H


def overlap(log, S, HB, Wd):
    """對方兩件是已判件 ⇒ 照它們當時的設定重建（innov_ky 關），重建完再開回來。"""
    UG.set_innov_ky(False)
    try:
        return _overlap(log, S, HB, Wd)
    finally:
        UG.set_innov_ky(True)


def _overlap(log, S, HB, Wd):
    from backtest import researchT1fix as T1
    ctx = T1.build_ctx(True)
    cal, mk, w0, w1 = ctx["cal"], ctx["mk"], ctx["w0"], ctx["w1"]
    assert len(cal) == Wd["n"] and cal[0] == Wd["cal"][0] and cal[-1] == Wd["cal"][-1]
    SF = R11.stop_force_days(R11.valid_from_data(sorted(ctx["closes"]), mk, cal), w1)
    W = {"closes": ctx["closes"], "opens": ctx["opens"], "NP": ctx["ncal"], "SF": SF}
    o, aud = YX._eng(W, "營量", ctx["sig13"], "H60", 7000)
    ref = pd.read_csv("backtest/resultsT1fix/seeds.csv.gz", dtype={"eq_sha": str})
    rf = ref[(ref["key"] == "c13") & (ref["var"] == "t1") & (ref["r"] == 0)]["eq_sha"].iloc[0]
    S["閘"]["營量 v1 T1 種子 0 ＝ resultsT1fix c13 t1"] = bool(YX.sha(o["equity"]) == rf)
    H1 = daily_from_audit(aud, len(cal))
    sb = pd.read_csv("backtest/resultsYLtrend/sig_b_main.csv.gz", dtype={"sid": str}, float_precision="round_trip"); sb = sb[sb["Tk"] == "T3"].copy()
    stocks_ = pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str)          # 市場別照 researchYLtrend：load_universe ∩ gate3
    mk = D.load_universe().merge(UG.gate3(stocks_)[["stock_id"]], on="stock_id").set_index("stock_id")["market"]
    closes, opens = dict(ctx["closes"]), dict(ctx["opens"])
    extra = sorted(set(sb["sid"]) - set(closes))
    if extra:
        c2, o2 = RR.load_prices(extra, cal, mk, "branch"); c2, o2 = RR.pad_px_t1(c2, o2); closes.update(c2); opens.update(o2)
    SF2 = R11.stop_force_days(R11.valid_from_data(sorted(closes), mk, cal), w1)
    W2 = {"closes": closes, "opens": opens, "NP": ctx["ncal"], "SF": SF2}
    o2_, aud2 = YX._eng(W2, "營量", sb, "H40", 7000)
    y3 = pd.read_csv("backtest/resultsYLtrend/seeds_main.csv.gz", dtype={"eq_sha": str})
    r3 = y3[(y3["格"] == "乙_T3_H40") & (y3["r"] == 0)]["eq_sha"].iloc[0]
    S["閘"]["營量趨勢 乙_T3_H40 種子 0 ＝ resultsYLtrend seeds_main"] = bool(YX.sha(o2_["equity"]) == r3)
    H2_ = daily_from_audit(aud2, len(cal))
    out = {}
    for nm, HO in (("營量 v1（T1）", H1), ("營量趨勢 乙_T3_H40", H2_)):
        a_, b_ = [], []
        for t in range(Wd["w0"], Wd["w1"] + 1):
            if HB[t]:
                a_.append(len(HB[t] & HO[t]) / len(HB[t]))
            if HO[t] and HB[t]:
                b_.append(len(HB[t] & HO[t]) / len(HO[t]))
        out[nm] = {"本格持股中也被對方持有（平均）": float(np.mean(a_)), "對方持股中也被本格持有（平均）": float(np.mean(b_)) if b_ else float("nan"),
                   "有重疊的日子比例": float(np.mean([len(HB[t] & HO[t]) > 0 for t in range(Wd["w0"], Wd["w1"] + 1) if HB[t]]))}
    log(f"[重疊] {out}｜閘 {S['閘']}")
    return out


# ═════════════ 主程式 ═════════════
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); ap.add_argument("--reps", type=int, default=1000); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    log(f"===== researchLongT {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜PREREG長線戰法 seq1 件 T sha {PREREG_SHA} =====")
    S = {"登錄": f"PREREG長線戰法 seq1 sha {PREREG_SHA}（裁定 seq272 §二）件 T", "閘": {}, "共用閘": "innov_ky 開（-創、-KY創 都剔）；面板為舊快取、母體再經 gate3 交集"}
    reg = [os.path.join("/mnt/c/SynologyDrive/跨線信箱", f) for f in os.listdir("/mnt/c/SynologyDrive/跨線信箱") if f.startswith("登錄全文-外部長線戰法三件")]
    for p_ in reg:                                                          # 信箱現存 seq2（取代 seq1；件 T §一 不動，本線人工逐字比對過）
        txt = open(p_, "rb").read().decode("utf-8").splitlines(keepends=True)
        h_ = hashlib.sha256("".join(x for x in txt if "pw1" not in x).encode("utf-8")).hexdigest()[:16]
        S["閘"][f"登錄全文 sha（去 pw1 行）{os.path.basename(p_)[-60:]}"] = h_ in (PREREG_SHA, PREREG_SHA2)
    stk = pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str)
    S["閘"]["innov_ky 開：6854／6924／7823／7827 不在 gate3"] = not ({"6854", "6924", "7823", "7827"} & set(UG.gate3(stk)["stock_id"]))
    W_ = {}
    for tag, cfg in (("主", MAIN), ("早年", EARLY)):
        Wd = MX.load_world(cfg, a.procs, log)
        if tag == "主":
            c_, m_ = R13.window_stats(Wd["bench"], 0, Wd["n"], Wd["w0"], Wd["w1"] + 1)
            S["閘"]["0050 主窗錨逐位元"] = repr(float(c_)) == repr(MX.ANCHOR[0]) and repr(float(m_)) == repr(MX.ANCHOR[1])
        D.DATA = cfg["data"]
        flag, rng_ = rev_flags(Wd["cal"], tag == "主")
        TT, RSB = tables(Wd, flag)
        S.setdefault("資料", {})[tag] = {"月營收期別": rng_, "換股日": [str(Wd["cal"][Wd["rebs"][0]].date()), str(Wd["cal"][Wd["rebs"][-1]].date()), len(Wd["rebs"])],
                                      "樣板內（中位）": float(np.median([len(TT[e]["tmpl"]) for e in Wd["rebs"]])),
                                      "樣板＋營收（中位）": float(np.median([len(TT[e]["tmpl"] & TT[e]["rev"]) for e in Wd["rebs"]])),
                                      "RS 可算 eligible（中位）": float(np.median([len(TT[e]["pool"]) for e in Wd["rebs"]]))}
        T, RES, SEL, SEGP, Z = run_world(Wd, TT, log, tag)
        W_[tag] = {"Wd": Wd, "TT": TT, "RSB": RSB, "T": T, "RES": RES, "SEL": SEL, "SEGP": SEGP, "Z": Z, "cfg": cfg}
        log(f"[{tag}] 資料 {S['資料'][tag]}")
    D.DATA = H2.H2D
    T = pd.concat([W_["主"]["T"], W_["早年"]["T"]], ignore_index=True)
    T.to_csv(os.path.join(OUT, "cells.csv"), index=False, float_format="%.17g")
    Zm, Ze = W_["主"]["Z"], W_["早年"]["Z"]
    S["0050"] = {nm: [float(v[0]), float(v[1])] for nm, v in {**Zm, **Ze}.items()}
    # 挑格
    ex = T[(T["世界"] == "主") & (T["段"] == "探索")].copy()
    ex["退化"] = (ex["平均持股"] < ex["N"] / 2) | (ex["換股簿現金比例"] > 0.30)
    c0, m0 = Zm["探索"]; r0 = c0 / abs(m0)
    pool_ = ex[~ex["退化"]]
    S["退化格"] = ex[ex["退化"]]["格"].tolist()
    if not len(pool_):
        S["挑格"] = "8 格全退化 ⇒ 依構造不可判定"; pick = None
    else:
        pas = pool_[(pool_["年化"] > c0) & (pool_["比值"] >= r0)]
        pp = (pas if len(pas) else pool_).assign(_f=lambda d: d["頻率"].map({"月": 0, "季": 1}), _z=lambda d: d["族"].map({"甲": 0, "乙": 1}))
        pick = pp.sort_values(["比值", "年化", "_z", "_f", "N"], ascending=[False, False, True, True, True]).iloc[0]["格"]
    TB = []
    for k in [cname(f, q, N) for f in FAMS for q in FREQS for N in NS]:
        row = {"格": k}
        for sg, wk in (("探索", "主"), ("確認", "主"), ("早年", "早年")):
            g = T[(T["世界"] == wk) & (T["段"] == sg) & (T["格"] == k)].iloc[0]
            for c_ in ("年化", "回落", "比值", "標籤", "平均持股", "換股簿現金比例", "換手（每次換股買進檔數÷N）", "成本／年", "入選平均檔數"):
                row[f"{sg}_{c_}"] = g[c_]
        row["退化"] = bool(ex[ex["格"] == k]["退化"].iloc[0]); row["挑中"] = k == pick
        TB.append(row)
    TB = pd.DataFrame(TB); TB.to_csv(os.path.join(OUT, "table.csv"), index=False, float_format="%.9g")
    if pick is not None:
        pr = TB.set_index("格").loc[pick]
        final = max((pr["確認_標籤"], pr["早年_標籤"]), key=lambda l: LORD[l])
        fam, fq, N = pick.split("_"); N = int(N[1:])
        nb = [cname(fam, "季" if fq == "月" else "月", N), cname(fam, fq, 20 if N == 10 else 10)]
        nbl = {k: (TB.set_index("格").loc[k, "確認_標籤"], TB.set_index("格").loc[k, "早年_標籤"]) for k in nb}
        stable = ("不適用（件標籤不合格，沒有要撐的結論）" if final == "不合格" else
                  all(LORD[a_] <= LORD[pr["確認_標籤"]] and LORD[b_] <= LORD[pr["早年_標籤"]] for a_, b_ in nbl.values()))
        S["挑中"] = {"格": pick, "件標籤（確認、早年較嚴）": final, "穩（相鄰兩格標籤不低於挑中格）": stable, "相鄰格標籤（確認、早年）": nbl,
                   "探索": [pr["探索_年化"], pr["探索_回落"], pr["探索_標籤"]], "確認": [pr["確認_年化"], pr["確認_回落"], pr["確認_標籤"]],
                   "早年": [pr["早年_年化"], pr["早年_回落"], pr["早年_標籤"]]}
        log(f"[挑格] {pick}｜{S['挑中']}")
        # 假訊號
        for tag in ("主", "早年"):
            _G[tag] = W_[tag]
        with Pool(a.procs) as pool:
            FK = pd.DataFrame(pool.map(_fake, [(tag, pick, r) for tag in ("主", "早年") for r in range(a.reps)]))
        FK.to_csv(os.path.join(OUT, "fake.csv.gz"), index=False, float_format="%.6g")
        fk = {}
        for sg, wk in (("探索", "主"), ("確認", "主"), ("早年", "早年")):
            f_ = FK[FK["世界"] == wk]
            fk[sg] = {"隨機年化中位": float(f_[f"{sg}_年化"].median()), "p（隨機 ≥ 本格）": float((f_[f"{sg}_年化"] >= pr[f"{sg}_年化"]).mean())}
        S["假訊號（同池隨機、同數量）"] = fk
        # 新規矩 ③
        if pr["確認_標籤"] in ("合格", "另列") or pr["早年_標籤"] in ("合格", "另列"):
            sens = {}
            for tag in ("主", "早年"):
                Wd = W_[tag]["Wd"]; sel = W_[tag]["SEL"][pick]
                for vn, kw in (("(a) 全賣全買", {"mode": "all"}), ("(b) 跌破 MA60 次日賣", {"ma_stop": MX.ma_table(Wd, Wd["sids"], 60)})):
                    res = MX.sim_book(sel, Wd, N, **kw)
                    for nm, (a_, b_) in W_[tag]["SEGP"].items():
                        c_, m_ = R13.window_stats(res["eq"], 0, len(res["eq"]), a_, b_ + 1)
                        sens[f"{vn}｜{nm}"] = [float(c_), float(m_), MX.label(c_, m_, W_[tag]["Z"][nm][0], W_[tag]["Z"][nm][1])]
            S["新規矩③（描述）"] = sens
        else:
            S["新規矩③（描述）"] = "挑中格確認、早年都不合格／另列 ⇒ 不觸發"
        HB = daily_from_book(W_["主"]["RES"][pick], W_["主"]["Wd"])
        S["持股重疊（主窗、挑中格）"] = overlap(log, S, HB, W_["主"]["Wd"])
    # 溫斯坦描述臂
    WS = {}
    for tag in ("主", "早年"):
        Wd = W_[tag]["Wd"]; cfg = W_[tag]["cfg"]
        stocks = pd.read_csv(os.path.join(cfg["data"], "meta", "stocks.csv"), dtype=str); mkd = dict(zip(stocks["stock_id"], stocks["market"]))
        with Pool(a.procs, initializer=_vol_init, initargs=(Wd["cal"], cfg["data"])) as pool:
            VOL = dict(pool.map(load_vol, [(s, mkd.get(s, "twse")) for s in Wd["sids"]], chunksize=16))
        D.DATA = cfg["data"]
        sig, eq, aud = weinstein(Wd, VOL, W_[tag]["RSB"], tag, log)
        TRd = RW.YX_trades(aud)
        for nm, (a_, b_) in W_[tag]["SEGP"].items():
            c_, m_ = R13.window_stats(eq, 0, len(eq), a_, b_ + 1)
            tr = TRd[(TRd["t_in"] >= a_) & (TRd["t_in"] <= b_)]
            WS[nm] = {"年化": float(c_), "回落": float(m_), "標籤": MX.label(c_, m_, W_[tag]["Z"][nm][0], W_[tag]["Z"][nm][1]), "成交筆數": int(len(tr)),
                      "逐筆平均淨": float(tr["淨"].mean()) if len(tr) else float("nan"), "勝率": float((tr["淨"] > 0).mean()) if len(tr) else float("nan"),
                      "平均持有交易日": float((tr["t_out"] - tr["t_in"]).mean()) if len(tr) else float("nan")}
        W_[tag]["WS"] = (sig, eq, aud)
    D.DATA = H2.H2D
    S["溫斯坦第二階段（描述臂、不計 N）"] = WS
    log(f"[溫斯坦] {WS}")
    _G["W_"] = W_; _G["TB"] = TB; _G["pick"] = pick
    report(S); page(S)
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=lambda z: z.item() if hasattr(z, "item") else str(z))
    log(f"[完] 網頁 {os.path.getsize(os.path.join(OUT, F_HTML))} bytes｜{time.time() - T0:.0f}s")


def P_(x, d=1):
    return "—" if x is None or not isinstance(x, (int, float, np.floating)) or not np.isfinite(x) else f"{x * 100:+.{d}f}%"


def report(S):
    TB = _G["TB"]; NL = chr(10)
    L = ["# PREREG長線戰法 seq1 件 T：米奈爾維尼趨勢樣板" + NL, f"使用者原話（逐字）：{RAW}" + NL,
         f"> 登錄 sha {PREREG_SHA}（裁定 seq272 §二；全件 N ＋3，件 T 計 1）｜共用閘 innov_ky 開（新件，裁定 seq271）；面板為舊快取、母體再經 gate3 交集｜"
         "換股簿依構造不截斷（窗尾照市值）｜本線讀法 T1～T12 見程式開頭｜⚠ 現實版描述未做（換股簿無現實版接法）" + NL,
         "| 格 | 探索 | 確認 | 確認標籤 | 早年 | 早年標籤 | 平均持股（探索） | 現金（探索） | 入選平均檔數（確認） | 換手／成本每年（確認） | 退化 |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in TB.to_dict("records"):
        L.append(f"| {r['格']}{' ⭐挑中' if r['挑中'] else ''} | {P_(r['探索_年化'])}／{P_(r['探索_回落'])} | {P_(r['確認_年化'])}／{P_(r['確認_回落'])} | {r['確認_標籤']} | "
                 f"{P_(r['早年_年化'])}／{P_(r['早年_回落'])} | {r['早年_標籤']} | {r['探索_平均持股']:.1f} | {r['探索_換股簿現金比例']:.0%} | {r['確認_入選平均檔數']:.1f} | "
                 f"{r['確認_換手（每次換股買進檔數÷N）']:.2f}／{P_(r['確認_成本／年'])} | {'是' if r['退化'] else ''} |")
    L.append(NL + f"0050：{ {k: [P_(v[0]), P_(v[1])] for k, v in S['0050'].items()} }")
    L.append(NL + f"挑中：{S.get('挑中', S.get('挑格'))}")
    L.append(f"假訊號（同池隨機、同數量）：{S.get('假訊號（同池隨機、同數量）')}")
    L.append(f"新規矩 ③：{S.get('新規矩③（描述）')}")
    L.append(f"持股重疊（裁定 seq272 §二 2）：{S.get('持股重疊（主窗、挑中格）')}")
    L.append(f"溫斯坦第二階段（描述臂、不計 N）：{S['溫斯坦第二階段（描述臂、不計 N）']}")
    L.append(NL + f"資料：{S['資料']}｜退化格：{S['退化格']}｜閘：{S['閘']}")
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write(NL.join(L) + NL)


def page(S):
    W_ = _G["W_"]; TB = _G["TB"]; pick = _G["pick"]; Zm, Ze = W_["主"]["Z"], W_["早年"]["Z"]
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0] + "\n.pick{background:#fff4cc}td.l,th.l{text-align:left}"
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>趨勢樣板</title>", f"<style>{CSS}</style></head><body><main>", "<h1>米奈爾維尼趨勢樣板（長線戰法 件 T）</h1>",
         f"<p class='lead'>使用者原話：{html.escape(RAW)}<br>登錄 PREREG長線戰法 seq1（sha {PREREG_SHA}）件 T。</p>",
         "<p class='note'>規則：每月（或每季）第一個交易日後，挑「股價站上 50／150／200 日線且均線多頭排列、200 日線往上、離一年低點漲 30% 以上、離一年高點 25% 以內、"
         "相對強弱在前 30%」的股票（乙族再加「月營收創 24 個月新高」），相對強弱最高的前 10 或 20 檔等權買進；還在名單上就續抱。扣成本 0.585%。</p>"]
    H.append("<h2>對照表</h2><div class='wrap'><table><tr><th class='l'>格</th><th>探索 2017–21</th><th>確認 2022–26</th><th>標籤</th><th>早年 2005–14</th><th>標籤</th><th>平均持股</th></tr>")
    for r in TB.to_dict("records"):
        f_, q_, n_ = r["格"].split("_")
        nm = f"{FNAME[f_]}、{q_}換、{n_[1:]} 檔" + ("（退化）" if r["退化"] else "")
        H.append(f"<tr class='{'pick' if r['挑中'] else ''}'><td class='l'>{nm}</td><td>{P_(r['探索_年化'])}／{P_(r['探索_回落'])}</td><td>{P_(r['確認_年化'])}／{P_(r['確認_回落'])}</td>"
                 f"<td>{r['確認_標籤']}</td><td>{P_(r['早年_年化'])}／{P_(r['早年_回落'])}</td><td>{r['早年_標籤']}</td><td>{r['確認_平均持股']:.1f}</td></tr>")
    WS = S["溫斯坦第二階段（描述臂、不計 N）"]
    H.append(f"<tr><td class='l'>溫斯坦第二階段（描述）</td><td>{P_(WS['探索']['年化'])}／{P_(WS['探索']['回落'])}</td><td>{P_(WS['確認']['年化'])}／{P_(WS['確認']['回落'])}</td>"
             f"<td>{WS['確認']['標籤']}</td><td>{P_(WS['早年']['年化'])}／{P_(WS['早年']['回落'])}</td><td>{WS['早年']['標籤']}</td><td>—</td></tr>")
    H.append(f"<tr><td class='l'>0050</td><td>{P_(Zm['探索'][0])}／{P_(Zm['探索'][1])}</td><td>{P_(Zm['確認'][0])}／{P_(Zm['確認'][1])}</td><td></td><td>{P_(Ze['早年'][0])}／{P_(Ze['早年'][1])}</td><td></td><td></td></tr></table></div>")
    ch = S.get("挑中", {})
    ov = S.get("持股重疊（主窗、挑中格）", {})
    H.append(f"<p class='note'>黃底 ＝ 探索段挑中的格；件標籤 ＝ 確認、早年較嚴者：<b>{ch.get('件標籤（確認、早年較嚴）', '—')}</b>。"
             + ("持股重疊：" + "；".join(f"{k} {v['本格持股中也被對方持有（平均）']:.0%}" for k, v in ov.items()) + "（本格持股裡同時被對方持有的平均比例）。" if ov else "") + "</p>")
    # 例子：挑中格確認段，持有期間最賺、中位、最賠各一（以換股簿內每段持有的報酬）
    if pick is not None:
        Wd = W_["主"]["Wd"]; res = W_["主"]["RES"][pick]; cal = Wd["cal"]; a_, b_ = W_["主"]["SEGP"]["確認"]
        spans = []; cur = {}
        es = sorted(res["hold"])
        for i, e in enumerate(es):
            hs = set(res["hold"][e])
            for s in list(cur):
                if s not in hs:
                    spans.append((s, cur.pop(s), e))
            for s in hs:
                cur.setdefault(s, e)
        for s, e0 in cur.items():
            spans.append((s, e0, Wd["w1"]))
        spans = [(s, e0, e1, Wd["P"][s]["o"][e1] / Wd["P"][s]["o"][e0] - 1 if np.isfinite(Wd["P"][s]["o"][e1]) else Wd["P"][s]["c"][e1] / Wd["P"][s]["o"][e0] - 1)
                 for s, e0, e1 in spans if a_ <= e0 <= b_ and np.isfinite(Wd["P"][s]["o"][e0])]
        spans.sort(key=lambda z: z[3])
        H.append("<h2>挑中格的例子（確認段，一段持有＝入選到落選）</h2>" + CS.legend_html() + "<p class='note'>灰線 ＝ 200 日線。</p>")
        D.DATA = H2.H2D
        uni = D.load_universe().set_index("stock_id")["name"]
        mkd = dict(pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str)[["stock_id", "market"]].to_numpy())
        for lab_, i in (("賺最多的一段", len(spans) - 1), ("中位那段", len(spans) // 2), ("賠最多的一段", 0)):
            if not spans:
                break
            s, e0, e1, r_ = spans[i]
            c = Wd["P"][s]["c"]; o = Wd["P"][s]["o"]
            st = D.load_stock(s, mkd.get(s, "twse"), cal)
            df = st.df; i0 = max(0, e0 - 120); i1 = min(len(cal) - 1, e1 + 20); sl = slice(i0, i1 + 1)
            cf = pd.Series(df["close"].to_numpy(float)).ffill().to_numpy()
            ma = {20: CS.moving_avg(cf, 20)[sl], 60: CS.moving_avg(cf, 60)[sl], 200: CS.moving_avg(cf, 200)[sl]}
            marks = [{"i": e0 - i0, "px": float(o[e0]), "kind": "entry", "label": f"入選買 {o[e0]:.2f}"},
                     {"i": e1 - i0, "px": float(o[e1] if np.isfinite(o[e1]) else c[e1]), "kind": "exit", "label": f"落選賣 {(o[e1] if np.isfinite(o[e1]) else c[e1]):.2f}"}]
            svg = CS.kline_svg([str(z.date()) for z in cal[sl]], df["open"].to_numpy(float)[sl], df["high"].to_numpy(float)[sl], df["low"].to_numpy(float)[sl], df["close"].to_numpy(float)[sl],
                               df["volume"].to_numpy(float)[sl] / 1000.0, ma=ma, marks=marks, shade=(e0 - i0, e1 - i0), title=lab_, show_title=False)
            H.append(f"<details class='card' open><summary><b>{lab_}</b>｜{s} {html.escape(str(uni.get(s, '')))}｜{cal[e0].date()}～{cal[e1].date()}</summary>"
                     f"<div class='meta'>{pick}｜這段 {P_(r_)}（未扣成本）｜確認段共 {len(spans)} 段</div>{svg}</details>")
    H.append("<p class='note'>價格為還原價。溫斯坦第二階段只當描述、不計 N。</p></main></body></html>")
    open(os.path.join(OUT, F_HTML), "w", encoding="utf-8").write("\n".join(H))


if __name__ == "__main__":
    main()
