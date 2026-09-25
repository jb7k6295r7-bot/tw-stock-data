# -*- coding: utf-8 -*-
"""PREREGX（型態量幅目標達成率＋成形前讀法）——回測線落地。判準＝台股策略線 PREREGX seq2（sha 7de459d6a4578cf6）。

    ~/tw-p16/.venv/bin/python backtest/researchX.py --freq  [--procs 2]   # 第二步：只報頻率（⛔ 不算任何報酬／達成）
    ~/tw-p16/.venv/bin/python backtest/researchX.py --main  [--procs 2]   # 第三步：本體（甲 5 格 × H60／H120、乙 6 格）

資料、母體、讀檔、硬斷點、漲跌停：與 PREREGH1／H2／M 同一份快照與同一套函式（import researchH2：main edc6f8002f、gate3）。
偵測器：backtest/patterns_x.py（T1 fixture：backtest/selftest_patterns_x.py —— ⭐ 開跑前先全跑，任一型不過 ⇒ 該型不跑）。

⭐ 登錄沒逐字寫、本支的落地讀法（⛔ 在看任何頻率或結果之前寫在這裡；交件逐條列出；偵測器本身的讀法 X1～X11 見 patterns_x.py；★＝兩種讀法擇一）：
 Y1 判定窗：沿用 researchH2／H1／M 的 [2017-03-02, 2026-08-24]（同一份快照）。
    ★ 甲 的事件須 T ≤ 窗尾−120（H60 與 H120 用【同一批事件】；〔另一讀法：H60 放寬到 T ≤ 窗尾−60，兩個 H 事件不同〕）；
    乙 的 S 須 S ≤ 窗尾−40（成形 40 日、20 日超額都在窗內）。
 Y2 處理順序（同 H2 R5）：同檔同型依時間走 ⇒ 落在「上一個被保留事件 t0」的 (t0, t0+20]（交易日曆）⇒ 合併掉；
    否則依序判剔除：型態視窗硬斷點 → 未來窗硬斷點 → T+1 停牌 → T+1 開盤漲停 → T 日 20 日波動無法計算（無法配對照）；被剔除者不開合併窗。
 Y3 ★ 型態視窗硬斷點（① 逐字「處置、注意、停牌復牌、疑似公司行動」）：[第一轉折, T] 內有任一：
      價格斷點（data.breakpoints 價格規則）、連續 ≥ 5 個交易日無有效 K 棒（H2 R3 字面）、處置期間（disposal.csv 區間，⛔ 不加出關 5 日）、
      注意股公告日（attention.csv，普通股）。〔另一讀法：「同 gate3」＝只用價格＋停牌兩條（H2 R3）〕
    第一轉折：W＝L1、頭肩底＝L、旗形＝S0（旗桿起點）、箱型＝箱體起點（訊號日−20）、杯柄＝左杯口 L、趨勢線＝P1。
 Y4 未來窗硬斷點（資料完整性，同 H2 R3，⛔ 不含處置／注意）：甲 (T, T+120]、乙 (S, S+40]。事件與對照同一條。
 Y5 T+1（乙 S+1）停牌或開盤漲停 ⇒ 剔除（同 H2；tradability.one）。對照池同條件（見 Y7）。
 Y6 目標距離％ ＝ 目標價 ÷ c[T] − 1（T 日收盤；對照同法用對照股 c[T]）。杯柄的目標 ＝ 研究二進場開盤 o[T+1] ＋ 杯深 ⇒ 距離也除以 c[T]。
    達成 ＝ [T+1, T+H]（交易日曆）內任一日還原 high ≥ 目標（缺值日略過）；「開盤即達成」＝ o[T+1] ≥ 目標（另報比例）。
 Y7 對照池（⑧、§二）：T 日 gate3 母體中 20 日波動可算者依波動排序（平手依代號）等分十組（組號 ＝ ⌊名次×10／N⌋）；
    池 ＝ 同十分位 ∧ T 日沒有本件五型任何【原始】觸發（合併／剔除之前）∧ 不是事件股本身 ∧ 對照也通過 Y4（120 日）與 Y5；
    池空 ⇒ 事件剔除（計數）。每型一條亂數流 default_rng(20260925)，事件依 (T, 代號) 排序逐筆抽 1 檔；H60、H120 用同一檔對照。
 Y8 甲 判定（每 H 一次）：d_e ＝ 事件達成 − 對照達成；D_A ＝ 平均；主 CI ＝ 月分群 SE（T 曆月，research11.cl_stats）；
    n_eff ＝ min(事件數, 以窗起點切的 H 日區段數)；出口①：n_eff ＜ 30 或 事件達成數 ＜ 30 或 對照達成數 ＜ 30；出口② n_eff ＜ 100；否則出口③
    （同 researchH2.judge）；結果①＝CI 含 0、結果②＝測得出（＋）、結果③＝測得出（−）。
    ★ 格的結果：兩個 H 同一結果 ⇒ 下該結果；兩者不同 ⇒「結果隨持有期而變」；任一 H 落出口① ⇒ 該格照報出口①（保守）。
 Y9 乙 判定：X ＝ close(≤ S+20 最後一根)／open(S+1) − 1 − 0.585% − EW20(S+1)；EW20 ＝ researchH1.market_ew（gate3、20 日）；
    D ＝ 平均 X；CI、n_eff（20 日區段）、出口與結果同 Y8（出口① 只看 n_eff ＜ 30）。
    成形率／破壞率／都沒發生率：(S, S+40] 且不超過該組終點（X8）內，以收盤判先發生者；率的 CI 同用月分群。
 Y10 假訊號臂（§四）：同檔、同曆月、同筆數的隨機日（該月內通過 Y4／Y5、20 日波動可算的交易日），30 次（種子 20260925＋r）；
    甲 ：每個假日沿用配對真事件的目標距離％、同 Y7 抽對照 ⇒ D_A(60)、D_A(120)；乙：同 Y9 算 X ⇒ D。報「CI 不含 0 的次數」。
 Y11 頻率（§四「先報頻率」）：每檔每年 ＝ 保留事件數 ÷ 股票年；股票年 ＝ 該股在 [窗起點, 窗尾−120（乙 −40）] 內
    首個到最後一個有效 K 棒所跨的交易日數 ÷ 每年交易日數（同 researchM_freq Q6）。
"""
from __future__ import annotations
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchH2 as H2                                 # noqa: E402  ⭐ 同一份快照（D.DATA 已指到 main edc6f8002f）
import researchH1 as H1                                 # noqa: E402
D, TR, UG = H2.D, H2.TR, H2.UG
sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import patterns_x as PX                   # noqa: E402

OUT = "backtest/resultsX"
W0, W1, SHA = H2.W0, H2.W1, H2.SHA
HOR = (60, 120); HMAX = 120
FORM_N, EX_N, MERGE = 40, 20, 20
SEED = 20260925; COST = 0.00585; FAKE_R = 30
TA, TB = PX.TYPES_A, PX.TYPES_B
NAME = {"box": "箱型", "cup": "杯柄", "w": "W 底", "hs": "頭肩底", "flag": "旗形", "trend": "趨勢線"}
_G = {}


def _init(cal, disp, attn):
    _G.update(cal=cal, disp=disp, attn=attn)


def _g5(valid):
    n = len(valid); run = np.zeros(n, np.int32); r_ = 0
    for i in range(n):
        r_ = r_ + 1 if not valid[i] else 0
        run[i] = r_
    return run >= 5


def load_one(args):
    sid, market = args
    cal = _G["cal"]; n = len(cal)
    st = D.load_stock(sid, market, cal)
    if st is None:
        return None
    df = st.df
    o = df["open"].to_numpy(float); h = df["high"].to_numpy(float); l = df["low"].to_numpy(float); c = df["close"].to_numpy(float)
    valid = np.isfinite(c); bars = np.flatnonzero(valid)
    if len(bars) < 30:
        return None
    pb = np.zeros(n, bool)
    for b_ in D.breakpoints(df, st.event_dates):
        if b_["rule"] in ("price", "price+gap"):
            pb[b_["pos"]] = True
    g5 = _g5(valid)
    dm = D.disposal_mask(sid, cal, _G["disp"], after_days=0)
    am = np.zeros(n, bool)
    ad = _G["attn"].get(sid)
    if ad:
        am = np.isin(cal.values, np.array(sorted(ad), dtype="datetime64[ns]"))
    tb = TR.one(sid, cal)
    ret = np.full(n, np.nan); ret[1:] = c[1:] / c[:-1] - 1.0
    vol20 = pd.Series(ret).rolling(20, min_periods=20).std(ddof=1).to_numpy()
    cff = pd.Series(c).ffill().to_numpy()
    cb, ob, hb = c[bars], o[bars], h[bars]
    A, B = {}, {}
    for kind in ("w", "hs", "flag"):
        r = PX.detect_turn(kind, cb)
        A[kind] = [{"T": int(bars[e["T"]]), "first": int(bars[e["first"]]), "target": float(e["target"]), "level": float(e["level"]),
                    "low": float(e["low"]), "pts": {k_: str(cal[bars[x]].date()) for k_, x in e["pts"].items()}} for e in r["events"]]
        B[kind] = [{"S": int(bars[g["S"]]), "first": int(bars[g["first"]]), "id": tuple(int(bars[x]) for x in g["id"]),
                    "low": float(g["S_low"] if kind == "flag" else g["low"]),
                    "trig": int(bars[g["trig"]]) if g["trig"] is not None else None,
                    "end": int(bars[g["end"]]) if g["end"] is not None and g["end"] >= 0 else None}
                   for g in r["groups"] if g["S"] is not None]
    f = PX.frame_open(df, st.event_dates)
    A["box"] = [{"T": e["T"], "first": e["first"], "target": e["target"], "level": e["level"], "low": e["low"]} for e in PX.box_events(f)]
    bdays = np.array(sorted({e["T"] for e in A["box"]}), int)
    B["box"] = []
    for s in PX.box_forming(f):
        k = int(np.searchsorted(bdays, s["S"], side="right"))
        B["box"].append({"S": s["S"], "first": s["first"], "id": s["id"], "low": s["low"],
                         "trig": int(bdays[k]) if k < len(bdays) else None, "end": None})
    ce = PX.cup_events(f)
    sig2, cg = PX.cup_scan(f)
    assert [x["signal_pos"] for x in sig2] == [x["T"] for x in ce], (sid, "⛔ cup_scan 與 patterns.cup_handle 突破清單不同")
    A["cup"] = [{"T": e["T"], "first": e["first"], "depth": float(e["depth_px"]), "low": float(e["low"]),
                 "pts": {"L": str(cal[e["L"]].date()), "B": str(cal[e["B"]].date()), "R": str(cal[e["R"]].date())}} for e in ce]
    B["cup"] = [{"S": g["S"], "first": g["first"], "id": g["id"], "low": g["low"], "trig": g["trig"], "end": g["end"]}
                for g in cg if g["S"] is not None]
    rt = PX.trend_forming(ob, hb, cb)
    B["trend"] = [{"S": int(bars[g["S"]]), "first": int(bars[g["first"]]), "id": tuple(int(bars[x]) for x in g["id"]), "low": g["low"],
                   "trig": int(bars[g["trig"]]) if g["trig"] is not None else None, "end": int(bars[g["end"]])}
                  for g in rt["groups"] if g["S"] is not None]
    return {"sid": sid, "market": market, "o": o, "h": h, "l": l, "c": c, "cff": cff, "valid": valid,
            "first_bar": int(bars[0]), "last_bar": int(bars[-1]),
            "cs_pb": np.cumsum(pb).astype(np.int32), "cs_g5": np.cumsum(g5).astype(np.int32),
            "cs_d": np.cumsum(dm).astype(np.int32), "cs_a": np.cumsum(am).astype(np.int32),
            "trd": tb["trd"], "up_o": tb["up_o"], "vol": vol20.astype(np.float64), "A": A, "B": B}


def _cnt(cs, a, b):
    if b < a:
        return 0
    return int(cs[b] - (cs[a - 1] if a > 0 else 0))


def brk_pat(S, a, b):
    """Y3：回 None 或第一個成立的原因。"""
    if _cnt(S["cs_pb"], a, b) > 0 or _cnt(S["cs_g5"], a + 4, b) > 0:
        return "價格或停牌"
    if _cnt(S["cs_d"], a, b) > 0:
        return "處置"
    if _cnt(S["cs_a"], a, b) > 0:
        return "注意"
    return None


def brk_fwd(S, a, b):
    return H2.brk(S, a, b)


def tradable_next(S, t):
    n = len(S["c"])
    if t + 1 >= n or not S["trd"][t + 1] or not np.isfinite(S["o"][t + 1]):
        return "halt"
    if S["up_o"][t + 1]:
        return "limit"
    return None


def keep_A(S, typ, w0, wE, n):
    acc = {"原始_窗內": 0, "合併掉": 0, "剔除_型態視窗_價格或停牌": 0, "剔除_型態視窗_處置": 0, "剔除_型態視窗_注意": 0,
           "剔除_未來窗斷點": 0, "剔除_T+1停牌": 0, "剔除_T+1開盤漲停": 0, "剔除_20日波動不可算": 0}
    out = []; t_keep = -10 ** 9
    for e in sorted(S["A"][typ], key=lambda x: x["T"]):
        T = e["T"]
        if not (w0 <= T <= wE):
            continue
        acc["原始_窗內"] += 1
        if t_keep < T <= t_keep + MERGE:
            acc["合併掉"] += 1; continue
        why = brk_pat(S, e["first"], T)
        if why:
            acc["剔除_型態視窗_" + why] += 1; continue
        if T + HMAX >= n or brk_fwd(S, T + 1, T + HMAX):
            acc["剔除_未來窗斷點"] += 1; continue
        tn = tradable_next(S, T)
        if tn:
            acc["剔除_T+1停牌" if tn == "halt" else "剔除_T+1開盤漲停"] += 1; continue
        if not np.isfinite(S["vol"][T]):
            acc["剔除_20日波動不可算"] += 1; continue
        e2 = dict(e)
        if typ == "cup":
            e2["target"] = float(S["o"][T + 1] + e["depth"]); e2["target_half"] = float(S["o"][T + 1] + 0.5 * e["depth"])
        e2["dist"] = e2["target"] / S["c"][T] - 1.0
        out.append(e2); t_keep = T
    return out, acc


def keep_B(S, typ, w0, wB, n):
    acc = {"形成段數_有S": 0, "S_窗內": 0, "合併掉": 0, "剔除_型態視窗_價格或停牌": 0, "剔除_型態視窗_處置": 0, "剔除_型態視窗_注意": 0,
           "剔除_未來窗斷點": 0, "剔除_S+1停牌": 0, "剔除_S+1開盤漲停": 0}
    first = {}
    for g in sorted(S["B"][typ], key=lambda x: x["S"]):
        if g["id"] not in first:
            first[g["id"]] = g                           # 每組只取第一個 S
    acc["形成段數_有S"] = len(first)
    out = []; s_keep = -10 ** 9
    for g in sorted(first.values(), key=lambda x: x["S"]):
        s = g["S"]
        if not (w0 <= s <= wB):
            continue
        acc["S_窗內"] += 1
        if s_keep < s <= s_keep + MERGE:
            acc["合併掉"] += 1; continue
        why = brk_pat(S, g["first"], s)
        if why:
            acc["剔除_型態視窗_" + why] += 1; continue
        if s + FORM_N >= n or brk_fwd(S, s + 1, s + FORM_N):
            acc["剔除_未來窗斷點"] += 1; continue
        tn = tradable_next(S, s)
        if tn:
            acc["剔除_S+1停牌" if tn == "halt" else "剔除_S+1開盤漲停"] += 1; continue
        out.append(dict(g)); s_keep = s
    return out, acc


def load_all(procs, lim=None):
    t0 = time.time()
    cal = D.load_calendar(); n = len(cal)
    w0 = int(cal.searchsorted(pd.Timestamp(W0))); w1 = int(cal.searchsorted(pd.Timestamp(W1)))
    assert str(cal[w0].date()) == W0 and str(cal[w1].date()) == W1
    stocks = pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(stocks)
    if lim:
        U = U.head(lim)
    disp = D.load_disposal_intervals(); attn = D.load_attention_dates()
    with Pool(procs, initializer=_init, initargs=(cal, disp, attn)) as pool:
        res = pool.map(load_one, list(zip(U["stock_id"], U["market"])), chunksize=8)
    ST = {r["sid"]: r for r in res if r is not None}
    print("[資料] 快照 {}｜gate3 {:,} 檔、可用 {:,}｜判定窗 [{}, {}]｜{:.0f}s".format(SHA[:10], len(U), len(ST), W0, W1, time.time() - t0), flush=True)
    return cal, n, w0, w1, U, ST


def freq(ST, cal, w0, w1, n):
    wE, wB = w1 - HMAX, w1 - FORM_N
    out = {}
    for tag, types, end, fn in (("甲", TA, wE, keep_A), ("乙", TB, wB, keep_B)):
        DPY = (end - w0 + 1) / ((cal[end] - cal[w0]).days / 365.25)
        yrs = {s: max(0, min(S["last_bar"], end) - max(S["first_bar"], w0) + 1) / DPY for s, S in ST.items()}
        for typ in types:
            accs, ks, per = {}, [], []
            for s in sorted(ST):
                k, a = fn(ST[s], typ, w0, end, n)
                for k_, v_ in a.items():
                    accs[k_] = accs.get(k_, 0) + v_
                ks.append(len(k))
                if yrs[s] > 0:
                    per.append((yrs[s], len(k)))
            P_ = np.array(per)
            one = P_[P_[:, 0] >= 1.0]
            rate = one[:, 1] / one[:, 0]
            out[f"{tag}_{typ}"] = {"帳": accs, "保留": int(sum(ks)), "有事件檔數": int(sum(1 for x in ks if x)),
                                  "每檔每年_合併母體": round(float(P_[:, 1].sum() / P_[:, 0].sum()), 4),
                                  "每檔每年_中位_曝露≥1年": round(float(np.median(rate)), 4),
                                  "每檔每年_平均_曝露≥1年": round(float(rate.mean()), 4), "股票年": round(float(P_[:, 0].sum()), 1)}
            print("[頻率] {} {:6s} 保留 {:>7,}｜每檔每年 {:.3f}｜{}".format(tag, NAME[typ], out[f"{tag}_{typ}"]["保留"],
                                                                   out[f"{tag}_{typ}"]["每檔每年_合併母體"], accs), flush=True)
    return out


# ═════════════ 本體 ═════════════
class Mat:
    """橫斷面：十分位、原始觸發、對照可用（120 日）、池快取。"""

    def __init__(self, ST, n, w0, wE):
        self.sids = sorted(ST); self.ix = {s: i for i, s in enumerate(self.sids)}
        N = len(self.sids); self.N, self.n = N, n
        self.H = np.vstack([ST[s]["h"] for s in self.sids]); self.C = np.vstack([ST[s]["c"] for s in self.sids])
        self.L = np.vstack([ST[s]["l"] for s in self.sids]); self.O = np.vstack([ST[s]["o"] for s in self.sids])
        V = np.vstack([ST[s]["vol"] for s in self.sids])
        self.DEC = np.full((N, n), -1, np.int8)
        for t in range(w0, wE + 1):
            v = V[:, t]; ok = np.flatnonzero(np.isfinite(v))
            if len(ok) == 0:
                continue
            order = ok[np.lexsort((ok, v[ok]))]                  # 波動升冪、平手依代號序
            pos = np.empty(len(order), int); pos[np.arange(len(order))] = np.arange(len(order))
            self.DEC[order, t] = (np.arange(len(order)) * 10) // len(order)
        self.TRIG = np.zeros((N, n), bool)
        for s in self.sids:
            for typ in TA:
                for e in ST[s]["A"][typ]:
                    self.TRIG[self.ix[s], e["T"]] = True
        self.OK = np.zeros((N, n), bool)
        self.OK40 = np.zeros((N, n), bool)
        for s in self.sids:
            S = ST[s]; i = self.ix[s]
            for Hh, M in ((HMAX, self.OK), (FORM_N, self.OK40)):
                t = np.arange(0, n - Hh - 1)
                pb = S["cs_pb"][t + Hh] - S["cs_pb"][t] > 0
                g5 = S["cs_g5"][t + Hh] - S["cs_g5"][t + 4] > 0
                trd = S["trd"][t + 1] & np.isfinite(S["o"][t + 1]) & ~S["up_o"][t + 1]
                M[i, t] = np.isfinite(S["c"][t]) & trd & ~pb & ~g5
        self._pool = {}

    def pool(self, t, d):
        k = (t, d)
        if k not in self._pool:
            self._pool[k] = np.flatnonzero((self.DEC[:, t] == d) & ~self.TRIG[:, t] & self.OK[:, t])
        return self._pool[k]

    def hit(self, i, t, H, tgt):
        seg = self.H[i, t + 1:t + H + 1]
        return int(np.isfinite(seg).any() and np.nanmax(seg) >= tgt)


def draw_ctl(M, sid_i, t, rng):
    d = int(M.DEC[sid_i, t])
    if d < 0:
        return None, 0, -1
    pool = M.pool(t, d)
    pool = pool[pool != sid_i]
    if len(pool) == 0:
        return None, 0, -1
    k = int(rng.integers(len(pool)))
    return int(pool[k]), len(pool), k


def judge(X, cal, w0, H, col="d", hitcols=None):
    if len(X) == 0:
        return {"n": 0, "出口": "出口①", "結果": "—（出口①：樣本不足以分辨）"}
    cs = H2.R.cl_stats(X[col].to_numpy(float), X["month"].to_numpy())
    blk = int(((X["t"] - w0) // H).nunique())
    n_eff = min(len(X), blk)
    out = {"n": int(len(X)), "D": cs["mean"], "lo": cs["lo"], "hi": cs["hi"], "se_月": cs["se"], "months": cs["months"],
           "區段數": blk, "n_eff": n_eff}
    small = n_eff < 30
    if hitcols:
        a, b = int(X[hitcols[0]].sum()), int(X[hitcols[1]].sum())
        out.update({"事件達成數": a, "對照達成數": b, "事件達成率": float(X[hitcols[0]].mean()), "對照達成率": float(X[hitcols[1]].mean())})
        small = small or a < 30 or b < 30
    if small:
        out["出口"] = "出口①"; out["結果"] = "—（出口①：樣本不足以分辨）"
    else:
        out["出口"] = "出口②" if n_eff < 100 else "出口③"
        out["結果"] = "結果①（測不出）" if cs["lo"] <= 0 <= cs["hi"] else ("結果②（測得出（＋））" if cs["mean"] > 0 else "結果③（測得出（−））")
    return out


def cell_A(j60, j120):
    if j60["出口"] == "出口①" or j120["出口"] == "出口①":
        return "出口①（{}）".format("、".join(h for h, j in (("H60", j60), ("H120", j120)) if j["出口"] == "出口①"))
    if j60["結果"] == j120["結果"]:
        return j60["結果"]
    return "結果隨持有期而變（H60 {}／H120 {}）".format(j60["結果"], j120["結果"])


def first_day(arr_bool, off):
    k = np.flatnonzero(arr_bool)
    return int(k[0]) + off if len(k) else None


def run_A(ST, M, cal, w0, wE, n):
    res, rows_all = {}, {}
    for typ in TA:
        rng = np.random.default_rng(SEED)
        evs = []
        for s in sorted(ST):
            k, _ = keep_A(ST[s], typ, w0, wE, n)
            evs += [dict(e, sid=s) for e in k]
        evs.sort(key=lambda e: (e["T"], e["sid"]))
        rows, nodraw = [], 0
        for e in evs:
            i = M.ix[e["sid"]]; T = e["T"]
            j, psz, pk = draw_ctl(M, i, T, rng)
            if j is None:
                nodraw += 1; continue
            tgt_c = M.C[j, T] * (1.0 + e["dist"])
            r = {"sid": e["sid"], "t": T, "date": str(cal[T].date()), "month": cal[T].strftime("%Y-%m"), "dist": e["dist"],
                 "target": e["target"], "low": e["low"], "c_T": M.C[i, T], "o_T1": M.O[i, T + 1],
                 "ctl": M.sids[j], "ctl_c_T": M.C[j, T], "ctl_target": tgt_c, "pool_n": psz, "pool_k": pk,
                 "open_hit": int(M.O[i, T + 1] >= e["target"]), "pts": json.dumps(e.get("pts", {}), ensure_ascii=False)}
            if typ == "cup":
                r["target_half"] = e["target_half"]
            hs = M.H[i, T + 1:T + HMAX + 1]; ls_ = M.L[i, T + 1:T + HMAX + 1]
            with np.errstate(invalid="ignore"):
                dh = first_day(hs >= e["target"], 1); dl = first_day(ls_ <= e["low"], 1)
            for H in HOR:
                r[f"sig_{H}"] = M.hit(i, T, H, e["target"]); r[f"ctl_{H}"] = M.hit(j, T, H, tgt_c)
                r[f"d_{H}"] = r[f"sig_{H}"] - r[f"ctl_{H}"]
                r[f"low_first_{H}"] = int(dl is not None and dl <= H and (dh is None or dh > H or dl < dh))
                r[f"low_same_{H}"] = int(dl is not None and dh is not None and dl == dh and dl <= H)
                if typ == "cup":
                    r[f"sig_half_{H}"] = M.hit(i, T, H, e["target_half"])
            r["days_to_hit"] = dh
            rows.append(r)
        X = pd.DataFrame(rows)
        rows_all[typ] = X
        jj = {H: judge(X.assign(d=X[f"d_{H}"]), cal, w0, H, hitcols=(f"sig_{H}", f"ctl_{H}")) for H in HOR}
        dsc = {"事件數": int(len(X)), "池空而剔除": nodraw, "相異檔數": int(X["sid"].nunique()) if len(X) else 0,
               "目標距離％分佈": {q: float(np.percentile(X["dist"], p)) for q, p in (("p10", 10), ("p25", 25), ("中位", 50), ("p75", 75), ("p90", 90))} if len(X) else {},
               "開盤即達成比例": float(X["open_hit"].mean()) if len(X) else None}
        for H in HOR:
            hh = X[X[f"sig_{H}"] == 1]["days_to_hit"]
            dsc[f"H{H}"] = {"事件達成率": float(X[f"sig_{H}"].mean()), "對照達成率": float(X[f"ctl_{H}"].mean()),
                            "達成天數中位（事件）": float(hh.median()) if len(hh) else None,
                            "先碰型態低點比例": float(X[f"low_first_{H}"].mean()), "同日碰低點與目標": int(X[f"low_same_{H}"].sum())}
            if typ == "cup":
                dsc[f"H{H}"]["半杯深達成率（描述）"] = float(X[f"sig_half_{H}"].mean())
        res[typ] = {"H60": jj[60], "H120": jj[120], "格的結果": cell_A(jj[60], jj[120]), "描述": dsc}
        print("[甲] {:6s} n {:,}｜H60 D {:+.4f} [{:+.4f},{:+.4f}] {} {}｜H120 D {:+.4f} [{:+.4f},{:+.4f}] {} {}｜⇒ {}".format(
            NAME[typ], len(X), jj[60].get("D", np.nan), jj[60].get("lo", np.nan), jj[60].get("hi", np.nan), jj[60]["出口"], jj[60]["結果"],
            jj[120].get("D", np.nan), jj[120].get("lo", np.nan), jj[120].get("hi", np.nan), jj[120]["出口"], jj[120]["結果"], res[typ]["格的結果"]), flush=True)
    return res, rows_all


def outcome_B(S, g):
    s = g["S"]; lim = s + FORM_N
    if g["end"] is not None:
        lim = min(lim, g["end"])
    trig = g["trig"] if (g["trig"] is not None and s < g["trig"] <= lim) else None
    c = S["c"][s + 1:lim + 1] if lim > s else np.empty(0)
    with np.errstate(invalid="ignore"):
        k = np.flatnonzero(c < g["low"])
    dd = s + 1 + int(k[0]) if len(k) else None
    if trig is not None and (dd is None or trig < dd):
        return "成形", trig, dd
    if dd is not None:
        return "破壞", trig, dd
    return "都沒發生", trig, dd


def run_B(ST, cal, w0, wB, n, EW):
    res, rows_all = {}, {}
    for typ in TB:
        rows = []
        for s in sorted(ST):
            S = ST[s]
            k, _ = keep_B(S, typ, w0, wB, n)
            for g in k:
                t = g["S"]
                R_ = S["cff"][t + EX_N] / S["o"][t + 1] - 1.0
                oc, tg, dd = outcome_B(S, g)
                rows.append({"sid": s, "t": t, "date": str(cal[t].date()), "month": cal[t].strftime("%Y-%m"),
                             "R": R_, "EW": EW[t + 1], "X": R_ - COST - EW[t + 1], "結局": oc,
                             "成形日": str(cal[tg].date()) if tg is not None else "", "破壞日": str(cal[dd].date()) if dd is not None else "",
                             "low": g["low"], "first": str(cal[g["first"]].date()),
                             "end": str(cal[g["end"]].date()) if g["end"] is not None else ""})
        X = pd.DataFrame(rows).sort_values(["t", "sid"]).reset_index(drop=True)
        rows_all[typ] = X
        j = judge(X, cal, w0, EX_N, col="X")
        rate = {}
        for oc in ("成形", "破壞", "都沒發生"):
            ind = (X["結局"] == oc).astype(float).to_numpy()
            cs = H2.R.cl_stats(ind, X["month"].to_numpy())
            rate[oc] = {"率": cs["mean"], "lo": cs["lo"], "hi": cs["hi"], "筆數": int(ind.sum())}
            sub = X[X["結局"] == oc]
            rate[oc]["20日超額（描述）"] = float(sub["X"].mean()) if len(sub) else None
        res[typ] = {"判定": j, "率": rate, "平均R毛": float(X["R"].mean()), "平均EW": float(X["EW"].mean())}
        print("[乙] {:6s} n {:,}｜成形 {:.1%} 破壞 {:.1%}｜X {:+.4f} [{:+.4f},{:+.4f}] {} {}".format(
            NAME[typ], len(X), rate["成形"]["率"], rate["破壞"]["率"], j.get("D", np.nan), j.get("lo", np.nan), j.get("hi", np.nan), j["出口"], j["結果"]), flush=True)
    return res, rows_all


def fake_days(M, ST, sid, month_days, k, rng, okm, wlo, whi):
    i = M.ix[sid]
    c = [t for t in month_days if wlo <= t <= whi and okm[i, t] and M.DEC[i, t] >= 0] if okm is M.OK else \
        [t for t in month_days if wlo <= t <= whi and okm[i, t]]
    if not c:
        return []
    return sorted(int(x) for x in rng.choice(c, size=min(k, len(c)), replace=False))


def run_fake(ST, M, cal, w0, wE, wB, EW, rowsA, rowsB):
    mdays = {}
    for t in range(w0, max(wE, wB) + 1):
        mdays.setdefault(cal[t].strftime("%Y-%m"), []).append(t)
    out = []
    for r in range(1, FAKE_R + 1):
        for typ in TA:
            rng = np.random.default_rng(SEED + r)
            X = rowsA[typ]; rows = []
            for (sid, mon), g in X.groupby(["sid", "month"], sort=True):
                days = fake_days(M, ST, sid, mdays.get(mon, []), len(g), rng, M.OK, w0, wE)
                dists = g.sort_values("t")["dist"].to_numpy()
                i = M.ix[sid]
                for t, dist in zip(days, dists):
                    j, _, _ = draw_ctl(M, i, t, rng)
                    if j is None:
                        continue
                    tg = M.C[i, t] * (1 + dist); tc = M.C[j, t] * (1 + dist)
                    rr = {"t": t, "month": mon}
                    for H in HOR:
                        rr[f"sig_{H}"] = M.hit(i, t, H, tg); rr[f"ctl_{H}"] = M.hit(j, t, H, tc); rr[f"d_{H}"] = rr[f"sig_{H}"] - rr[f"ctl_{H}"]
                    rows.append(rr)
            F = pd.DataFrame(rows)
            for H in HOR:
                jf = judge(F.assign(d=F[f"d_{H}"]), cal, w0, H, hitcols=(f"sig_{H}", f"ctl_{H}")) if len(F) else {"n": 0}
                out.append({"r": r, "格": f"甲_{typ}_H{H}", "n": jf.get("n"), "D": jf.get("D"), "lo": jf.get("lo"), "hi": jf.get("hi"),
                            "判過": bool(jf.get("n", 0) and not (jf["lo"] <= 0 <= jf["hi"]))})
        for typ in TB:
            rng = np.random.default_rng(SEED + r)
            X = rowsB[typ]; rows = []
            for (sid, mon), g in X.groupby(["sid", "month"], sort=True):
                S = ST[sid]
                days = fake_days(M, ST, sid, mdays.get(mon, []), len(g), rng, M.OK40, w0, wB)
                for t in days:
                    R_ = S["cff"][t + EX_N] / S["o"][t + 1] - 1.0
                    rows.append({"t": t, "month": mon, "X": R_ - COST - EW[t + 1]})
            F = pd.DataFrame(rows)
            jf = judge(F, cal, w0, EX_N, col="X") if len(F) else {"n": 0}
            out.append({"r": r, "格": f"乙_{typ}", "n": jf.get("n"), "D": jf.get("D"), "lo": jf.get("lo"), "hi": jf.get("hi"),
                        "判過": bool(jf.get("n", 0) and not (jf["lo"] <= 0 <= jf["hi"]))})
        print("[假訊號臂] r＝{} 完成".format(r), flush=True)
    return pd.DataFrame(out)


def main():
    from backtest import selftest_patterns_x as STX
    t1, _ = STX.run_all()
    print("[T1] {}".format(t1), flush=True)
    bad = [k for k, v in t1.items() if not v]
    procs = int(sys.argv[sys.argv.index("--procs") + 1]) if "--procs" in sys.argv else 2
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    cal, n, w0, w1, U, ST = load_all(procs, lim)
    os.makedirs(OUT, exist_ok=True)
    wE, wB = w1 - HMAX, w1 - FORM_N
    if "--freq" in sys.argv:
        fr = freq(ST, cal, w0, w1, n)
        fr["_T1"] = t1; fr["_快照"] = SHA; fr["_gate3母體"] = len(U); fr["_可用檔數"] = len(ST)
        json.dump(fr, open(os.path.join(OUT, "freq.json" if not lim else "freq_limit.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
        return
    assert not bad, "⛔ T1 不過的型：{}（該型不跑）".format(bad)
    t0 = time.time()
    EW = H1.market_ew(ST, n, EX_N)
    M = Mat(ST, n, w0, wE)
    print("[橫斷面] 十分位／觸發／可用矩陣完成｜{:.0f}s".format(time.time() - t0), flush=True)
    resA, rowsA = run_A(ST, M, cal, w0, wE, n)
    resB, rowsB = run_B(ST, cal, w0, wB, n, EW)
    tag = "_limit" if lim else ""
    for typ, X in rowsA.items():
        X.to_csv(os.path.join(OUT, f"A_{typ}{tag}.csv.gz"), index=False)
    for typ, X in rowsB.items():
        X.to_csv(os.path.join(OUT, f"B_{typ}{tag}.csv.gz"), index=False)
    trig = [(s, typ, str(cal[e["T"]].date())) for s in sorted(ST) for typ in TA for e in ST[s]["A"][typ]]
    pd.DataFrame(trig, columns=["sid", "type", "T"]).to_csv(os.path.join(OUT, f"raw_triggers{tag}.csv.gz"), index=False)
    FK = run_fake(ST, M, cal, w0, wE, wB, EW, rowsA, rowsB) if "--nofake" not in sys.argv else pd.DataFrame()
    if len(FK):
        FK.to_csv(os.path.join(OUT, f"fake_arm{tag}.csv"), index=False)
    fk = {g: {"判過": int(x["判過"].sum()), "次數": int(len(x))} for g, x in FK.groupby("格")} if len(FK) else {}
    summ = {"快照": SHA, "gate3母體": len(U), "可用檔數": len(ST), "判定窗": [W0, W1], "T1": t1,
            "甲": resA, "乙": resB, "假訊號臂": fk, "耗時s": round(time.time() - t0)}
    json.dump(summ, open(os.path.join(OUT, f"summary{tag}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print("完成 {:.0f}s".format(time.time() - t0), flush=True)


if __name__ == "__main__":
    main()
