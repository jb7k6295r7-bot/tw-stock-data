# -*- coding: utf-8 -*-
"""PREREG訊號系統（台股策略線登錄 seq1 sha 8e8595d3ce5f3c51；裁定 seq243、244、245 發號、N_組合 ＋4；新規矩 seq241、242）。
築底起漲（E1）／底部反轉（E2）訊號進、高檔反轉訊號（X）出；可再進場；加停損停利 16 組；0050 層。回測線，2026-09-27。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchSig.py pre|body|report [--procs 2] [--reps 200] [--fake 1000]

═══ 沿用（登錄 §一；⭐ 逐條）═══
  引擎 ＝ research11.simulate_mtm（營飆 v1 骨架：N＝10、每檔買進投入當時淨值 1/10、同日多於空格 ⇒ rng.permutation 抽籤、種子 1000＋r、
         200 顆取中位；成本 0.585%；無 tradable（開盤無效 ⇒ 停損線出場延到第一個有效開盤；進場開盤無效改收盤＝引擎原式））
  價   ＝ rerun17.load_prices（快照 edc6f，還原、float32、收盤 ffill）；訊號偵測 ＝ D.load_stock 還原 OHLC（float64，同 researchRev）
  母體 ＝ W1 eligible（resultsp4/panel.csv.gz 當月面板）∩ gate3；訊號日 t 看它那個月的面板
  段   ＝ 探索 2017-03-02～2021-12-30｜確認 2022-01-03～2026-08-24；各段獨立起跑（期初全現金）；進場 e＝t＋1 ∈ 段內；
         ⛔ 無時間出口：排程出場設在段尾次一交易日 ⇒ 段尾收盤按市值計（段尾未出場筆數照報）
═══ 訊號（⛔ 既有定義原樣）═══
  E1：W 底、頭肩底（PREREGX／patterns_x.detect_turn）｜箱型突破（patterns_x.box_events＝研究二 box_breakout，事件日＝站穩第 3 日）｜
      杯柄（patterns_x.cup_events＝研究二 cup_handle buy='handle'，只驗杯；裁定 seq245 照既有定義）
  E2：TD 9 買、RSI 30 站回、低檔爆量長下影、晨星、多頭吞噬（researchRev 原版，訊號日＝T）｜KD 底背離、MACD 底背離（researchRev 確認版，訊號日＝確認日 C）
  X ：高檔爆量長上影（確認版，訊號日＝C）、TD 9 賣、KD 頂背離、MACD 頂背離、RSI 70 跌回、黃昏之星、空頭吞噬（researchRev 原版）、
      上升趨勢線跌破（researchRev.up_line_events＝上升趨勢線登錄主格）
  規則：已持有不加碼（引擎 held）；同日同檔有進場與（本格的）出場訊號 ⇒ 該進場訊號不進；出場＝持有期間（d ≥ e）第一個 X 日 d ⇒ d＋1 開盤賣
        （引擎 stop_line：只在 d 放必觸發線 BIG）；再進場不設冷卻（同檔多列，引擎自然處理）
═══ 停損停利（登錄 §五；與訊號出場並存、誰先到先出；觸發日取最早，次日開盤執行）═══
  SL10／SL20：收盤 ≤ 進場價 ×90/100、×80/100（引擎進場價 listexit_lines.engine_ep、引擎收盤）
  AT2：2×ATR 追蹤（listexit_lines.trail_levels 同式：Wilder 14（research11.load_bars）、起點甲＝進場日收盤、嚴格新高才上調）；收盤 ＜ 線
  TP30：收盤 ≥ 進場價 ×130/100 全賣｜TP50h：引擎 trim_rule {"kind":"gain","x":0.5,"frac":0.5}（剩半照原規則）｜
  TR20：收盤 ≤ 持有以來最高收盤 ×80/100（yfstop_lines.t20_levels 同式）
  16 組 ＝ {無, SL10, SL20, AT2} × {無, TP30, TP50h, TR20}
═══ 挑法與判定（登錄 §四、§五；⛔ 看數字前寫死）═══
  探索段：E1、E2 各在 9 種出場（ANY＋X 單一 8）挑：過判準（年化 ＞ 0050 同段 且 年化÷|MDD| ≥ 0050）的裡取比值最高；都沒過 ⇒ 比值最高（同分取年化高）
  確認段：各驗挑中那格 ⇒ 合格／另列／不合格（使用者判準）；對照：0050｜同進場固定抱 20／60／120｜假訊號 A（同進場＋隨機出場，持有天數抽自本格）｜
          假訊號 B（同月同筆數隨機進場＋同出場規則）各 1,000 次（種子：出場／進場抽樣 default_rng([20260927, i])、引擎 1000＋(i mod 200)）
  停損停利：E1、E2 各用挑中出場跑 16 組（探索段）⇒ 32 選 1（同挑法）⇒ 確認段驗；挑中「無」⇒ 與 §四 同格、N 不另加
  0050 層：0050 自己的 E1∪E2 ⇒ 次日開盤全倉買；X 任一 ⇒ 次日開盤全賣持現金；對一直抱 0050（年化高不高）
輸出 backtest/resultsSig/
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pickle
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchRev as RV                                  # ⭐ 既有落地定義（偵測、確認、上升線、0050 序列）；D.DATA ⇒ 快照
from backtest import listexit_lines as L
from backtest import patterns_x as PX
from backtest import rerun17 as RR
from backtest import research11 as R11
from backtest import yfstop_lines as Y

D = RV.D
HERE = os.path.expanduser("~/tw-p17/backtest")
OUT = os.path.join(HERE, "resultsSig")
COST = R11.COST
BIG = float(np.finfo(np.float64).max)
SEG = {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}
EARLY = ("2004-02-11", "2016-12-30")
E1 = ["W", "HS", "BOX", "CUP"]
E2 = ["TD", "RSI", "VS", "MOR", "ENG", "KDc", "MACDc"]
XS = ["VSc", "TD", "KD", "MACD", "RSI", "EVE", "ENG", "TL"]
EXITS = ["ANY"] + XS
SLS = ["無", "SL10", "SL20", "AT2"]
TPS = ["無", "TP30", "TP50h", "TR20"]
NAME = {"W": "W 底", "HS": "頭肩底", "BOX": "箱型突破", "CUP": "杯柄", "TD": "TD 9", "RSI": "RSI", "VS": "爆量長影", "MOR": "晨星", "ENG": "吞噬",
        "KDc": "KD 底背離（確認）", "MACDc": "MACD 底背離（確認）", "VSc": "高檔爆量長上影（確認）", "KD": "KD 頂背離", "MACD": "MACD 頂背離",
        "EVE": "黃昏之星", "TL": "上升趨勢線跌破", "ANY": "X 任一"}
XNAME = {"ANY": "X 任一", "VSc": "高檔爆量長上影（確認）", "TD": "TD 9 賣", "KD": "KD 頂背離", "MACD": "MACD 頂背離", "RSI": "RSI 70 跌回",
         "EVE": "黃昏之星", "ENG": "空頭吞噬", "TL": "上升趨勢線跌破"}
PANEL = os.path.join(HERE, "resultsp9_engine", "panel_ext.csv.gz")      # ⭐ 裁定：面板用 panel_ext（量測日到 2026-08-03）
EARLY_DATA = os.path.expanduser("~/earlydata/3edc0e2206/main/data")
EARLY_PANEL = os.path.expanduser("~/earlydata/3edc0e2206/sig_main/panel.csv.gz")
EARLY_A = ("2012-06-01", "2014-12-30")      # 早年個股 A 段（early 版面、只上市；面板 eligible 自 2012-06 起；段尾留一天給排程出場）
EARLY_B = ("2015-08-03", "2016-12-30")      # 早年個股 B 段（主快照、只上市；panel_ext eligible 自 2015-08 起）
_G: dict = {}


def stock_universe(cal, panel_path, stocks_csv, twse_only=False):
    """W1 eligible（當月面板）∩ gate3；回 (sids, {sid: 月份集合}, market)。"""
    from backtest import p4_features as P4F
    U = RV.UG.gate3(pd.read_csv(stocks_csv, dtype=str))
    if twse_only:
        U = U[U["market"] == "twse"]
    p = P4F.read_panel(panel_path)
    p = p[p["eligible"].astype(bool) & p["stock_id"].isin(set(U["stock_id"]))]
    elig = {sid: set(str(x)[:7] for x in g["measure_date"]) for sid, g in p.groupby("stock_id")}
    return sorted(elig), elig, U.set_index("stock_id")["market"]


def sha16(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]


# ═════════════════════════════ 訊號（每檔）
def sig_days(o, h, l, c, v, ro, rh, rl, rc, df, event_dates, ncal):
    """日曆對齊的陣列 ⇒ {code: 訊號日（日曆位置，已排序、唯一）}；E 族與 X 族分開鍵（E:…／X:…）。"""
    valid = np.isfinite(c); bars = np.flatnonzero(valid)
    out = {}
    if len(bars) < 30:
        return out, valid
    sel = lambda x: np.asarray(x, float)[bars]
    ev = RV.detect(sel(o), sel(h), sel(l), c[bars], sel(v), sel(ro), sel(rh), sel(rl), sel(rc))
    cal_ev = {k: np.array([int(bars[t]) for t, _ in v_], int) for k, v_ in ev.items()}
    f = PX.frame_open(df, event_dates)
    out["E:W"] = cal_ev["L_W"]; out["E:HS"] = cal_ev["L_HS"]
    out["E:BOX"] = np.array(sorted({int(e["T"]) for e in PX.box_events(f)}), int)
    out["E:CUP"] = np.array(sorted({int(e["T"]) for e in PX.cup_events(f)}), int)
    out["E:TD"] = cal_ev["L_TD"]; out["E:RSI"] = cal_ev["L_RSI"]; out["E:VS"] = cal_ev["L_VS"]; out["E:MOR"] = cal_ev["L_MOR"]; out["E:ENG"] = cal_ev["L_ENG"]
    for k, src, top in (("E:KDc", "L_KD", False), ("E:MACDc", "L_MACD", False), ("X:VSc", "H_VS", True)):
        cc = [RV.confirm_day(c, valid, h[T], l[T], int(T), top, ncal - 2) for T in cal_ev[src]]
        out[k] = np.array(sorted({x for x in cc if x >= 0}), int)
    for k, src in (("X:TD", "H_TD"), ("X:KD", "H_KD"), ("X:MACD", "H_MACD"), ("X:RSI", "H_RSI"), ("X:EVE", "H_EVE"), ("X:ENG", "H_ENG"), ("X:TL", "H_TL")):
        out[k] = cal_ev[src]
    return out, valid


def stock_sig(args):
    sid, market = args
    cal = _G["cal"]
    st = D.load_stock(sid, market, cal)
    if st is None:
        return None
    df = st.df
    o, h, l, c, v = (df[k].to_numpy(float) for k in ("open", "high", "low", "close", "volume"))
    ro, rh, rl, rc, _ = RV.load_raw(sid, cal)
    S, valid = sig_days(o, h, l, c, v, ro, rh, rl, rc, df, st.event_dates, len(cal))
    return {"sid": sid, "market": market, "S": S, "valid": np.packbits(valid)}


def _init(d):
    _G.update(d)


# ═════════════════════════════ 列（段 × E × 出場選項）
def x_days(S, xopt):
    if xopt == "ANY":
        arrs = [S.get("X:" + k, np.zeros(0, int)) for k in XS]
        return np.unique(np.concatenate(arrs)) if arrs else np.zeros(0, int)
    return S.get("X:" + xopt, np.zeros(0, int))


def x_which(S, d):
    return "+".join(k for k in XS if d in set(S.get("X:" + k, [])))


def build_rows(SIG, elig, mon, E, xopt, s0, s1):
    rows = []; drop_same = 0; by_code = {}
    for sid, S in SIG.items():
        em = elig.get(sid)
        if not em:
            continue
        codes = E1 if E == "E1" else E2
        parts = [(k, S.get("E:" + k, np.zeros(0, int))) for k in codes]
        psets = [(k, set(p_.tolist())) for k, p_ in parts]
        ent = np.unique(np.concatenate([p for _, p in parts])) if parts else np.zeros(0, int)
        ent = ent[(ent + 1 >= s0) & (ent + 1 <= s1)]
        if not len(ent):
            continue
        ent = ent[np.array([mon[t] in em for t in ent], bool)]
        Xd = x_days(S, xopt)
        same = np.isin(ent, Xd)
        drop_same += int(same.sum()); ent = ent[~same]
        for t in ent:
            e = int(t) + 1
            i = int(np.searchsorted(Xd, e))
            dX = int(Xd[i]) if i < len(Xd) and Xd[i] <= s1 else -1
            srcs = "+".join(k for k, ps in psets if int(t) in ps)
            rows.append((sid, int(t), e, dX, srcs))
            for k in srcs.split("+"):
                by_code[k] = by_code.get(k, 0) + 1
    R = pd.DataFrame(rows, columns=["sid", "t", "entry_pos", "dX", "src"])
    return R, drop_same, by_code


# ═════════════════════════════ 停損停利觸發日（每列；引擎價）
def stop_days(R, cz, oz, bars_of, s1, valid_of):
    """回 DataFrame：ep、SL10、SL20、AT2、TP30、TR20 各自的第一個觸發日（無 ⇒ −1）、AT2 無法起算旗標。"""
    out = {k: np.full(len(R), -1, int) for k in ("SL10", "SL20", "AT2", "TP30", "TR20")}
    ep_a = np.zeros(len(R)); at_na = np.zeros(len(R), bool)
    for sid, g in R.groupby("sid"):
        c = np.asarray(cz[sid], float)
        B = bars_of(sid)
        valid = valid_of(sid)
        if B is not None:
            atr = R11.wilder_atr(B["h"], B["l"], B["c"])
        for i, e in zip(g.index, g["entry_pos"].to_numpy(int)):
            ep = L.engine_ep(oz, cz, sid, e); ep_a[i] = ep
            seg = c[e:s1 + 1]
            if not len(seg):
                continue

            def first(m):
                w = np.flatnonzero(m)
                return int(e + w[0]) if len(w) else -1
            out["SL10"][i] = first(seg <= Y.pct_of(ep, 90))
            out["SL20"][i] = first(seg <= Y.pct_of(ep, 80))
            out["TP30"][i] = first(seg >= Y.pct_of(ep, 130))
            if valid[e]:
                sv = valid[e:s1 + 1]
                run = np.maximum.accumulate(np.where(sv, seg, -np.inf))
                out["TR20"][i] = first(seg <= Y.pct_of(run, 80))
            k = int(np.searchsorted(B["idx"], e)) - 1 if B is not None else -1
            if B is None or k < 0 or k + 1 >= len(B["idx"]) or int(B["idx"][k + 1]) != e or not np.isfinite(atr[k]):
                at_na[i] = True
                continue
            idx = B["idx"]; j1 = int(np.searchsorted(idx, s1, side="right"))
            ii = idx[k + 1:j1]                                     # e..s1 內的有效 K 棒
            cb = c[ii]; ab = atr[k + 1:j1]
            prev_hi = np.maximum.accumulate(np.r_[-np.inf, cb[:-1]])
            newhi = cb > prev_hi
            cand = np.where(newhi & np.isfinite(ab), cb - 2.0 * ab, -np.inf)
            lvb = np.maximum.accumulate(np.maximum(ep - 2.0 * float(atr[k]), cand))
            lv = np.full(s1 - e + 1, np.nan); lv[ii - e] = lvb
            lv = pd.Series(lv).ffill().to_numpy()
            with np.errstate(invalid="ignore"):
                out["AT2"][i] = first(np.isfinite(lv) & (seg < lv))
    D_ = pd.DataFrame(out); D_["ep"] = ep_a; D_["AT2_na"] = at_na
    return D_


def gate_stoplines(R, SD, cz, oz, bars_of, s1, valid_of, n=300, seed=5):
    """閘：AT2、TR20 的向量化觸發日 ＝ listexit_lines.trail_levels／yfstop_lines.t20_levels 建出的線（逐條）的第一個觸發日。"""
    rng = np.random.default_rng(seed); bad = 0; chk = 0
    for i in rng.choice(len(R), size=min(n, len(R)), replace=False):
        sid = R.at[i, "sid"]; e = int(R.at[i, "entry_pos"]); ep = SD.at[i, "ep"]
        c = np.asarray(cz[sid], float); B = bars_of(sid)
        valid = valid_of(sid)
        if valid[e]:
            lv = Y.t20_levels(c, valid, e, s1, 80)
            w = np.flatnonzero(c[e:s1 + 1] <= lv)
            ref = int(e + w[0]) if len(w) else -1
            chk += 1; bad += ref != SD.at[i, "TR20"]
        if B is not None and not SD.at[i, "AT2_na"]:
            atr = R11.wilder_atr(B["h"], B["l"], B["c"]); k = int(np.searchsorted(B["idx"], e)) - 1
            st, lv = L.trail_levels(B["idx"], atr, c, k, ep, s1, mult=2.0, high_start="entry_close")
            with np.errstate(invalid="ignore"):
                w = np.flatnonzero(c[st:s1 + 1] < lv)
            ref = int(st + w[0]) if len(w) else -1
            chk += 1; bad += ref != SD.at[i, "AT2"]
    return {"比對條數": chk, "不一致": int(bad)}


# ═════════════════════════════ 引擎一顆
def make_cell(R, SD, s1, sl, tp, cz, oz):
    """R（列）＋停損停利 ⇒ (sig, kw, reason 對照)。"""
    ep = SD["ep"].to_numpy(float)
    d = R["dX"].to_numpy(int).copy(); why = np.where(d >= 0, "X", "").astype(object)
    cands = []
    if sl != "無":
        cands.append((sl, SD[sl].to_numpy(int)))
    if tp in ("TP30", "TR20"):
        cands.append((tp, SD[tp].to_numpy(int)))
    for nm, dd in cands:
        m = (dd >= 0) & ((d < 0) | (dd < d))
        d = np.where(m, dd, d); why = np.where(m, nm, why)
    sig = pd.DataFrame({"sid": R["sid"].to_numpy(), "entry_pos": R["entry_pos"].to_numpy(int), "xpos_X": s1 + 1})
    sig["g_X"] = [float(cz[s][s1 + 1]) / e_ - 1.0 for s, e_ in zip(sig["sid"], ep)]
    stop_line = {(s, int(e)): (int(dd), np.array([BIG])) for s, e, dd in zip(sig["sid"], sig["entry_pos"], d) if 0 <= dd <= s1}
    kw = {"stop_line": stop_line}
    if tp == "TP50h":
        kw["trim_rule"] = {"kind": "gain", "x": 0.5, "frac": 0.5}
    reason = {(s, int(e)): (w_, int(dd)) for s, e, w_, dd in zip(sig["sid"], sig["entry_pos"], why, d)}
    return sig, kw, reason


def run_one(args):
    key, r, s0, s1 = args
    sig, kw, reason, cf = _G["CELLS"][key]
    cz, oz, ncal = _G["cz"], _G["oz"], _G["ncal"]
    au = []
    o = R11.simulate_mtm(sig, "X", 10, np.random.default_rng(1000 + r), cz, oz, ncal, return_equity=True, audit=au, **kw)
    eq = np.asarray(o["equity"], float); hv = np.asarray(o["hold_val"], float)
    c_, m_, v_ = RR.win_metrics(eq, o["first"], o["end"], s0, s1)
    return summarize(key, r, au, eq, hv, c_, m_, reason, cf, s0, s1)


def summarize(key, r, au, eq, hv, c_, m_, reason, cf, s0, s1):
    cal = _G["cal"]
    openb = {}; tr = []; prev_done = set(); ntrim = 0
    for a in au:
        s = a["sid"]; t = int(a["t"])
        if a["side"] == "buy":
            if a.get("kind") in ("add",):
                continue
            openb[s] = {"tb": t, "amt": float(a["amt"]), "px": float(a["px"]), "sell": 0.0, "cost": 0.0, "trim": False}
        else:
            b = openb.get(s)
            if b is None:
                continue
            b["sell"] += float(a["amt"]); b["cost"] += float(a.get("cost", 0.0))
            if a.get("kind") == "trim":
                b["trim"] = True; ntrim += 1; continue
            net = (b["sell"] - b["cost"]) / b["amt"] - 1.0
            w_, dd = reason.get((s, b["tb"]), ("", -1))
            tr.append({"sid": s, "tb": b["tb"], "ts": t, "net": net, "re": s in prev_done, "why": w_ if (t <= s1) else "段尾",
                       "trim": b["trim"], "cf": cf.get((s, b["tb"])) if cf is not None else None})
            prev_done.add(s); del openb[s]
    for s, b in openb.items():                 # 引擎在 ncal 前仍未結清（理論上不會）
        tr.append({"sid": s, "tb": b["tb"], "ts": 10 ** 9, "net": np.nan, "re": s in prev_done, "why": "段尾", "trim": b["trim"], "cf": None})
    T = pd.DataFrame(tr)
    seg = slice(s0, s1 + 1)
    with np.errstate(invalid="ignore", divide="ignore"):
        cashr = float(np.nanmean(1.0 - hv[seg] / eq[seg]))
    heldn = np.zeros(len(eq))
    for x in tr:
        heldn[x["tb"]:min(x["ts"], s1 + 1)] += 1
    closed = T[T["ts"] <= s1] if len(T) else T
    yrs = {}
    for tb in T["tb"] if len(T) else []:
        y = cal[tb].year; yrs[y] = yrs.get(y, 0) + 1
    res = {"key": key, "r": r, "cagr": float(c_), "mdd": float(m_), "n": int(len(T)), "closed": int(len(closed)),
           "endopen": int(len(T) - len(closed)), "win": int((closed["net"] > 0).sum()) if len(closed) else 0,
           "hold": (closed["ts"] - closed["tb"]).to_numpy(int) if len(closed) else np.zeros(0, int),
           "net": closed["net"].to_numpy(float) if len(closed) else np.zeros(0),
           "re": closed["re"].to_numpy(bool) if len(closed) else np.zeros(0, bool),
           "why": closed["why"].value_counts().to_dict() if len(closed) else {}, "ntrim": ntrim,
           "cash": cashr, "held": float(heldn[seg].mean()), "yrs": yrs}
    if len(closed) and cf is not None:
        m = closed["why"].isin(["SL10", "SL20", "AT2", "TP30", "TR20"]).to_numpy()
        cfv = closed["cf"].to_numpy(object)
        res["aband"] = [(float(a_), float(b_)) for a_, b_, mm in zip(closed["net"], cfv, m) if mm and b_ is not None]
    return res


def cf_signal_exit(R, SD, cz, oz, s1):
    """放棄組：若只照訊號出場（dX＋1 開盤賣；沒有 ⇒ 段尾收盤計值）的逐列淨報酬。"""
    out = {}
    for s, e, dX, ep in zip(R["sid"], R["entry_pos"].to_numpy(int), R["dX"].to_numpy(int), SD["ep"].to_numpy(float)):
        if dX >= 0:
            j = dX + 1
            while j <= s1 + 1 and not (np.isfinite(oz[s][j]) and oz[s][j] > 0):
                j += 1
            px = float(oz[s][j]) if j <= s1 + 1 else float(cz[s][s1])
        else:
            px = float(cz[s][s1])
        out[(s, int(e))] = px / ep - 1.0 - COST
    return out


def agg(rows, bench, extra=None):
    """200 顆 ⇒ 一格。"""
    cg = np.array([x["cagr"] for x in rows]); mg = np.array([x["mdd"] for x in rows])
    c_, m_ = float(np.median(cg)), float(np.median(mg)); ratio = c_ / abs(m_) if m_ != 0 else np.nan
    c50, m50 = bench["cagr"], bench["mdd"]; r50 = c50 / abs(m50)
    lab = "合格" if (c_ > c50 and ratio >= r50) else ("另列" if c_ > c50 else "不合格")
    hold = np.concatenate([x["hold"] for x in rows]); net = np.concatenate([x["net"] for x in rows]); re = np.concatenate([x["re"] for x in rows])
    why = {}
    for x in rows:
        for k, v in x["why"].items():
            why[k] = why.get(k, 0) + v
    yrs = {}
    for x in rows:
        for y, v in x["yrs"].items():
            yrs[y] = yrs.get(y, 0) + v / len(rows)
    closed = sum(x["closed"] for x in rows)
    out = {"cagr_med": c_, "mdd_med": m_, "ratio": ratio, "label": lab, "c50": c50, "m50": m50, "r50": r50,
           "cagr_p10": float(np.percentile(cg, 10)), "cagr_p90": float(np.percentile(cg, 90)),
           "交易筆_每顆平均": float(np.mean([x["n"] for x in rows])), "每年交易": {int(k): round(v, 2) for k, v in sorted(yrs.items())},
           "勝率": float((net > 0).mean()) if len(net) else np.nan, "平均淨報酬": float(net.mean()) if len(net) else np.nan,
           "持有天數_平均": float(hold.mean()) if len(hold) else np.nan, "持有天數_中位": float(np.median(hold)) if len(hold) else np.nan,
           "持有天數_p10": float(np.percentile(hold, 10)) if len(hold) else np.nan, "持有天數_p90": float(np.percentile(hold, 90)) if len(hold) else np.nan,
           "再進場_筆數每顆": float(re.sum() / len(rows)), "再進場_平均淨報酬": float(net[re].mean()) if re.any() else np.nan,
           "再進場_勝率": float((net[re] > 0).mean()) if re.any() else np.nan,
           "首次進場_平均淨報酬": float(net[~re].mean()) if (~re).any() else np.nan, "首次進場_勝率": float((net[~re] > 0).mean()) if (~re).any() else np.nan,
           "出場原因占比": {k: round(v / max(1, closed), 4) for k, v in sorted(why.items(), key=lambda z: -z[1])},
           "賣半次數每顆": float(np.mean([x["ntrim"] for x in rows])),
           "段尾未出場_每顆": float(np.mean([x["endopen"] for x in rows])), "現金比例": float(np.mean([x["cash"] for x in rows])),
           "平均持股檔數": float(np.mean([x["held"] for x in rows]))}
    ab = [z for x in rows for z in x.get("aband", [])]
    if ab:
        a_ = np.array(ab)
        out["放棄組"] = {"筆數每顆": len(ab) / len(rows), "實際平均": float(a_[:, 0].mean()), "若照訊號出場平均": float(a_[:, 1].mean()),
                      "照訊號出場較好比例": float((a_[:, 1] > a_[:, 0]).mean())}
    out["_hold_pool"] = hold
    if extra:
        out.update(extra)
    return out


def pick(cands):
    """cands：[(key, cell)] ⇒ 登錄 §四 挑法。"""
    ok = [(k, c) for k, c in cands if c["label"] == "合格"]
    pool = ok if ok else cands
    return sorted(pool, key=lambda kc: (-kc[1]["ratio"], -kc[1]["cagr_med"]))[0][0]


# ═════════════════════════════ 0050 層
def l0050_signals(X):
    b = X["bars"]
    ev = RV.detect(*(np.asarray(X[k], float)[b] for k in ("o", "h", "l", "c", "v", "ro", "rh", "rl", "rc")))
    ce = {k: np.array([int(b[t]) for t, _ in v_], int) for k, v_ in ev.items()}
    n = len(X["c"])
    df = pd.DataFrame({"open": X["o"], "high": X["h"], "low": X["l"], "close": X["c"], "volume": X["v"], "traded": X["valid"],
                       "amount": np.nan}, index=pd.to_datetime(X["dates"]))
    f = PX.frame_open(df, set())
    E = {"W": ce["L_W"], "HS": ce["L_HS"], "BOX": np.array(sorted({int(e["T"]) for e in PX.box_events(f)}), int),
         "CUP": np.array(sorted({int(e["T"]) for e in PX.cup_events(f)}), int),
         "TD": ce["L_TD"], "RSI": ce["L_RSI"], "VS": ce["L_VS"], "MOR": ce["L_MOR"], "ENG": ce["L_ENG"]}
    for k, src, top in (("KDc", "L_KD", False), ("MACDc", "L_MACD", False)):
        E[k] = np.array(sorted({x for x in (RV.confirm_day(X["c"], X["valid"], X["h"][T], X["l"][T], int(T), top, n - 2) for T in ce[src]) if x >= 0}), int)
    Xs = {"VSc": np.array(sorted({x for x in (RV.confirm_day(X["c"], X["valid"], X["h"][T], X["l"][T], int(T), True, n - 2) for T in ce["H_VS"]) if x >= 0}), int),
          "TD": ce["H_TD"], "KD": ce["H_KD"], "MACD": ce["H_MACD"], "RSI": ce["H_RSI"], "EVE": ce["H_EVE"], "ENG": ce["H_ENG"], "TL": ce["H_TL"]}
    return E, Xs


def l0050_run(X, E, Xs, s0, s1):
    ent = set(np.unique(np.concatenate([v for v in E.values()])).tolist())
    ex = set(np.unique(np.concatenate([v for v in Xs.values()])).tolist())
    o, c = X["o"], X["c"]
    eq = np.ones(len(c)); units = 0.0; cash = 1.0; amt = 0.0; ep = np.nan; hold = False
    pend = None; trades = []; tb = None; cff = pd.Series(c).ffill().to_numpy()
    if (s0 - 1) in ent and (s0 - 1) not in ex:
        pend = "buy"
    for t in range(s0, s1 + 1):
        if pend is not None and np.isfinite(o[t]) and o[t] > 0:
            if pend == "sell" and hold:
                g = o[t] / ep - 1.0
                cash = amt * (1 + g - COST); trades.append({"tb": tb, "ts": t, "net": g - COST}); hold = False
            elif pend == "buy" and not hold:
                amt = cash; ep = float(o[t]); cash = 0.0; hold = True; tb = t
            pend = None
        eq[t] = amt * cff[t] / ep if hold else cash
        if hold and t in ex:
            pend = "sell"
        elif (not hold) and t in ent and t not in ex and t + 1 <= s1:
            pend = "buy"
        elif pend == "sell" and not hold:
            pend = None
    c_, m_, v_ = RR.win_metrics(eq, s0, s1 + 1, s0, s1)
    bh = RR.bench_row(None, cff, s0, s1 + 1)
    T = pd.DataFrame(trades)
    return {"cagr": float(c_), "mdd": float(m_), "ratio": float(c_ / abs(m_)) if m_ else np.nan, "抱0050_cagr": bh["cagr"], "抱0050_mdd": bh["mdd"],
            "判定_年化高於一直抱": bool(c_ > bh["cagr"]), "交易筆": int(len(T)) + int(hold), "段尾未出場": int(hold),
            "勝率": float((T["net"] > 0).mean()) if len(T) else np.nan, "平均持有天數": float((T["ts"] - T["tb"]).mean()) if len(T) else np.nan,
            "持股時間比例": float(np.mean([1.0 if any(x["tb"] <= t < x["ts"] for x in trades) or (hold and t >= tb) else 0.0 for t in range(s0, s1 + 1)]))}


# ═════════════════════════════ 主程式
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["pre", "body", "early", "report"])
    ap.add_argument("--procs", type=int, default=2)
    ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--fake", type=int, default=1000)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    if a.mode == "report":
        report(a.out); return
    if a.mode == "early":
        early(a); return
    logf = open(os.path.join(a.out, "run.log"), "a", encoding="utf-8")

    def log(x):
        print(x, flush=True); logf.write(x + "\n"); logf.flush()
    t00 = time.time()
    log(f"===== researchSig {a.mode} procs={a.procs} reps={a.reps} fake={a.fake} limit={a.limit} {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）=====")
    src = {f: hashlib.sha256(open(os.path.join(HERE, f), "rb").read()).hexdigest()[:16]
           for f in ("researchSig.py", "researchRev.py", "research11.py", "patterns_x.py", "patterns.py", "listexit_lines.py", "yfstop_lines.py")}
    log(f"[程式 sha256] {src}")
    cal = D.load_calendar(); ncal = len(cal); mon = np.array([str(x)[:7] for x in cal])
    P = {k: (int(cal.searchsorted(pd.Timestamp(v[0]))), int(cal.searchsorted(pd.Timestamp(v[1])))) for k, v in SEG.items()}
    for k, (x0, x1) in P.items():
        assert str(cal[x0].date()) == SEG[k][0] and str(cal[x1].date()) == SEG[k][1]
    SP = os.path.join(a.out, "summary.json")
    S = json.load(open(SP, encoding="utf-8")) if os.path.exists(SP) else {}
    S.update({"登錄": "PREREG訊號系統 seq1 sha 8e8595d3ce5f3c51；裁定 seq243／244／245；新規矩 seq241／242", "程式": src})
    # ── 訊號（每檔；快取）
    sids, elig, mk = stock_universe(cal, PANEL, os.path.join(RV.H2.H2D, "meta", "stocks.csv"))
    S["面板"] = {"路徑": PANEL, "sha256": sha16(PANEL), "出處": "resultsp9_engine/PANEL_SHA.md（commit d2c9df7fe2；同一支 build_panel 延伸到 2026-08-03）"}
    if a.limit:
        sids = sids[:a.limit]
    cache = os.path.join(a.out, f"sig_cache{'_lim' + str(a.limit) if a.limit else ''}.pkl")
    if os.path.exists(cache):
        SIG, VAL = pickle.load(open(cache, "rb"))
        log(f"[訊號] 讀快取 {cache}")
    else:
        t0 = time.time(); SIG = {}; VAL = {}
        with Pool(a.procs, initializer=_init, initargs=({"cal": cal},)) as pool:
            for i, r in enumerate(pool.imap_unordered(stock_sig, [(s, mk.get(s, "twse")) for s in sids], chunksize=4)):
                if r is not None:
                    SIG[r["sid"]] = r["S"]; VAL[r["sid"]] = r["valid"]
                if (i + 1) % 400 == 0:
                    log(f"  [訊號] {i + 1}/{len(sids)}｜{time.time() - t0:.0f}s")
        pickle.dump((SIG, VAL), open(cache, "wb"))
        log(f"[訊號] {len(SIG)} 檔｜{time.time() - t0:.0f}s")
    # ── 0050 層訊號
    Mm, Ms, info = RV.market_series()
    Em, Xm = l0050_signals(Mm); Es, Xs_ = l0050_signals(Ms)
    S["0050資料"] = info
    if a.mode == "pre":
        pre = {"個股": [], "0050": {}}
        for seg, (s0, s1) in P.items():
            for E in ("E1", "E2"):
                for xopt in EXITS:
                    R, drop, byc = build_rows(SIG, elig, mon, E, xopt, s0, s1)
                    per_m = R.groupby(mon[R["t"].to_numpy(int)]).size() if len(R) else pd.Series(dtype=int)
                    months = [m_ for m_ in sorted(set(mon[s0:s1 + 1]))]
                    pre["個股"].append({"段": seg, "E": E, "出場": xopt, "進場列": int(len(R)), "同日有出場而不進": drop, "各訊號": byc,
                                      "有出場訊號的列": int((R["dX"] >= 0).sum()) if len(R) else 0,
                                      "沒有出場訊號（段尾計值）的列": int((R["dX"] < 0).sum()) if len(R) else 0,
                                      "月數": len(months), "零列月數": int(sum(1 for m_ in months if per_m.get(m_, 0) == 0)),
                                      "每月列數_中位": float(per_m.reindex(months, fill_value=0).median()), "檔數": int(R["sid"].nunique()) if len(R) else 0})
        xcnt = {}
        for seg, (s0, s1) in P.items():
            for k in XS:
                xcnt[f"{seg}_{k}"] = int(sum(int(((v.get("X:" + k, np.zeros(0)) >= s0) & (v.get("X:" + k, np.zeros(0)) <= s1)).sum()) for v in SIG.values()))
        pre["X 訊號數（全母體、不分資格）"] = xcnt
        for seg, (X, E_, X_, lo, hi) in {"探索": (Mm, Em, Xm) + P["探索"], "確認": (Mm, Em, Xm) + P["確認"]}.items():
            pre["0050"][seg] = {"E": {k: int(((v >= lo - 1) & (v <= hi - 1)).sum()) for k, v in E_.items()},
                                "X": {k: int(((v >= lo) & (v <= hi)).sum()) for k, v in X_.items()}}
        dS = list(Ms["dates"]); e0, e1 = dS.index(EARLY[0]), dS.index(EARLY[1])
        pre["0050"]["早年"] = {"E": {k: int(((v >= e0) & (v <= e1 - 1)).sum()) for k, v in Es.items()},
                              "X": {k: int(((v >= e0) & (v <= e1)).sum()) for k, v in Xs_.items()}}
        # 閘：停損線（探索段 E2 任一）
        RR.use_snapshot()
        R, _, _ = build_rows(SIG, elig, mon, "E2", "ANY", *P["探索"])
        cz, oz = RR.load_prices(sorted(R["sid"].unique()), cal, mk, "branch")
        BC = {}
        bars_of = lambda s: BC.setdefault(s, R11.load_bars(s, mk.get(s, "twse"), cal))
        R = R.reset_index(drop=True)
        valid_of = lambda s_: np.unpackbits(VAL[s_])[:ncal].astype(bool)
        SD = stop_days(R, cz, oz, bars_of, P["探索"][1], valid_of)
        g = gate_stoplines(R, SD, cz, oz, bars_of, P["探索"][1], valid_of)
        pre["閘_停損線（抽樣）"] = g; pre["AT2 無法起算的列（探索 E2 任一）"] = int(SD["AT2_na"].sum())
        log(f"[閘 停損線] {g}")
        json.dump(pre, open(os.path.join(a.out, "pre.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=int)
        S["pre完成"] = time.strftime("%F %T")
        json.dump(S, open(SP, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
        log(f"[pre] 完成｜{time.time() - t00:.0f}s")
        if g["不一致"]:
            raise SystemExit("⛔ 閘不過（停損線）")
        return
    # ═══ body
    RR.use_snapshot()
    allsid = sorted(SIG)
    cz, oz = RR.load_prices(allsid, cal, mk, "branch")
    BC = {}
    bars_of = lambda s: BC.setdefault(s, R11.load_bars(s, mk.get(s, "twse"), cal))
    bench = RR.load_bench(cal)
    valid_of = lambda s_: np.unpackbits(VAL[s_])[:ncal].astype(bool)
    B50 = {seg: RR.bench_row(cal, bench, s0, s1 + 1) for seg, (s0, s1) in P.items()}
    S["0050同段"] = B50
    CELLS = {}
    _G.update(cal=cal, cz=cz, oz=oz, ncal=ncal, CELLS=CELLS, VAL=VAL)
    CELLOUT = {}

    def run_cells(keys, seg, reps, tag):
        s0, s1 = P[seg]
        t0 = time.time()
        res = {k: [] for k in keys}
        with Pool(a.procs) as pool:
            for x in pool.imap_unordered(run_one, [(k, r, s0, s1) for k in keys for r in range(reps)], chunksize=2):
                res[x["key"]].append(x)
        log(f"  [{tag}] {len(keys)} 格 × {reps} 顆｜{time.time() - t0:.0f}s")
        return res

    ROWS = {}; SDS = {}
    for seg in ("探索",):
        s0, s1 = P[seg]
        for E in ("E1", "E2"):
            keys = []
            for xopt in EXITS:
                R, _, _ = build_rows(SIG, elig, mon, E, xopt, s0, s1); R = R.reset_index(drop=True)
                SD = pd.DataFrame({"ep": [L.engine_ep(oz, cz, s_, e_) for s_, e_ in zip(R["sid"], R["entry_pos"])]})
                sig, kw, reason = make_cell(R, SD, s1, "無", "無", cz, oz)
                k = (seg, E, xopt, "無", "無"); CELLS[k] = (sig, kw, reason, None); keys.append(k); ROWS[k] = R
            res = run_cells(keys, seg, a.reps, f"探索 {E} 9 出場")
            for k in keys:
                CELLOUT[k] = agg(res[k], B50[seg])
    # 挑出場
    chosen = {}
    for E in ("E1", "E2"):
        cands = [((k[2]), CELLOUT[k]) for k in CELLOUT if k[0] == "探索" and k[1] == E and k[3] == "無" and k[4] == "無"]
        chosen[E] = pick(cands)
    S["探索段挑出場"] = chosen; log(f"[挑出場] {chosen}")
    # 停損停利 16 組 × E（探索）
    for E in ("E1", "E2"):
        s0, s1 = P["探索"]; xopt = chosen[E]
        R = ROWS[("探索", E, xopt, "無", "無")]
        SD = stop_days(R, cz, oz, bars_of, s1, valid_of); SDS[("探索", E)] = SD
        cf = cf_signal_exit(R, SD, cz, oz, s1)
        keys = []
        for sl in SLS:
            for tp in TPS:
                if sl == "無" and tp == "無":
                    continue
                sig, kw, reason = make_cell(R, SD, s1, sl, tp, cz, oz)
                k = ("探索", E, xopt, sl, tp); CELLS[k] = (sig, kw, reason, cf); keys.append(k)
        res = run_cells(keys, "探索", a.reps, f"探索 {E} 停損停利 15 組")
        for k in keys:
            CELLOUT[k] = agg(res[k], B50["探索"])
    cands = [(k, CELLOUT[k]) for k in CELLOUT if k[0] == "探索" and k[2] == chosen.get(k[1]) and (k[1] in ("E1", "E2"))]
    chosen_st = pick(cands)
    S["探索段挑停損停利"] = list(chosen_st); log(f"[挑停損停利] {chosen_st}")
    S["探索段完成"] = time.strftime("%F %T")
    # ═══ 確認段（⛔ 上面挑完才算）
    s0, s1 = P["確認"]
    keys = []; CR = {}
    for E in ("E1", "E2"):
        R, drop, _ = build_rows(SIG, elig, mon, E, chosen[E], s0, s1); R = R.reset_index(drop=True); CR[E] = R
        SD = stop_days(R, cz, oz, bars_of, s1, valid_of); SDS[("確認", E)] = SD
        cf = cf_signal_exit(R, SD, cz, oz, s1)
        sig, kw, reason = make_cell(R, SD, s1, "無", "無", cz, oz)
        k = ("確認", E, chosen[E], "無", "無"); CELLS[k] = (sig, kw, reason, None); keys.append(k); ROWS[k] = R
        if chosen_st[1] == E and not (chosen_st[3] == "無" and chosen_st[4] == "無"):
            sig, kw, reason = make_cell(R, SD, s1, chosen_st[3], chosen_st[4], cz, oz)
            k2 = ("確認", E, chosen[E], chosen_st[3], chosen_st[4]); CELLS[k2] = (sig, kw, reason, cf); keys.append(k2)
    res = run_cells(keys, "確認", a.reps, "確認段 判定格")
    for E in ("E1", "E2"):
        CR[E].assign(**{c_: SDS[("確認", E)][c_].to_numpy() for c_ in ("ep", "SL10", "SL20", "AT2", "TP30", "TR20")}).to_csv(
            os.path.join(a.out, f"confirm_rows_{E}.csv.gz"), index=False, float_format="%.17g")
    aud = []
    for k in keys:
        sig_, kw_, _, _ = CELLS[k]
        for r in range(5):
            au = []
            o = R11.simulate_mtm(sig_, "X", 10, np.random.default_rng(1000 + r), cz, oz, ncal, return_equity=True, audit=au, **kw_)
            c_, m_, _ = RR.win_metrics(np.asarray(o["equity"], float), o["first"], o["end"], s0, s1)
            for x in au:
                aud.append({"cell": "|".join(k), "r": r, **{kk: x.get(kk) for kk in ("t", "sid", "side", "kind", "amt", "px", "cost")}})
            aud.append({"cell": "|".join(k), "r": r, "t": -1, "sid": "_metrics", "side": "", "kind": "", "amt": c_, "px": m_, "cost": np.nan})
    pd.DataFrame(aud).to_csv(os.path.join(a.out, "confirm_audit5.csv.gz"), index=False, float_format="%.17g")
    for k in keys:
        CELLOUT[k] = agg(res[k], B50["確認"])
    # 固定持有對照（兩段）
    for seg in ("探索", "確認"):
        s0_, s1_ = P[seg]; keys = []
        for E in ("E1", "E2"):
            R = ROWS.get((seg, E, chosen[E], "無", "無"))
            for H in (20, 60, 120):
                xp = np.minimum(R["entry_pos"].to_numpy(int) + H - 1, s1_ + 1)
                sig = pd.DataFrame({"sid": R["sid"].to_numpy(), "entry_pos": R["entry_pos"].to_numpy(int), "xpos_X": xp})
                sig["g_X"] = [float(cz[s_][x_]) / L.engine_ep(oz, cz, s_, e_) - 1.0 for s_, e_, x_ in zip(sig["sid"], sig["entry_pos"], xp)]
                reason = {(s_, int(e_)): (f"H{H}", -1) for s_, e_ in zip(sig["sid"], sig["entry_pos"])}
                k = (seg, E, f"H{H}", "無", "無"); CELLS[k] = (sig, {}, reason, None); keys.append(k)
        res = run_cells(keys, seg, a.reps, f"{seg} 固定持有對照")
        for k in keys:
            CELLOUT[k] = agg(res[k], B50[seg])
    # 假訊號臂（確認段判定格）
    FAKE = {}
    s0, s1 = P["確認"]
    for E in ("E1", "E2"):
        base = CELLOUT[("確認", E, chosen[E], "無", "無")]
        R = CR[E]; sig0, kw0, reason0, _ = CELLS[("確認", E, chosen[E], "無", "無")]
        FAKE[E] = fake_arms(E, R, SIG, elig, mon, chosen[E], s0, s1, cz, oz, base, a, log)
    S["假訊號"] = FAKE
    # 早年段 0050 層與 0050 層
    L50 = {}
    for seg, (s0_, s1_) in P.items():
        L50[seg] = l0050_run(Mm, Em, Xm, s0_, s1_)
    dS = list(Ms["dates"]); e0, e1 = dS.index(EARLY[0]), dS.index(EARLY[1])
    L50["早年"] = l0050_run(Ms, Es, Xs_, e0, e1)
    S["0050層"] = L50
    # ── 輸出
    rows = []
    for k, c in CELLOUT.items():
        rows.append({"段": k[0], "E": k[1], "出場": k[2], "停損": k[3], "停利": k[4],
                     **{kk: (json.dumps(v, ensure_ascii=False) if isinstance(v, dict) else v) for kk, v in c.items() if not kk.startswith("_")}})
    pd.DataFrame(rows).to_csv(os.path.join(a.out, "cells.csv"), index=False)
    S["body完成"] = time.strftime("%F %T"); S["秒_body"] = round(time.time() - t00)
    json.dump(S, open(SP, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[body 完成] {time.time() - t00:.0f}s")
    report(a.out)


def fake_arms(E, R, SIG, elig, mon, xopt, s0, s1, cz, oz, base, a, log):
    """A：同進場＋隨機出場（持有天數抽自本格 200 顆已結清交易）；B：同月同筆數隨機進場＋同出場規則。各 a.fake 次。
    抽樣 rng ＝ default_rng([20260927, i])（先 A 後 B）；引擎種子 1000＋(i mod 200)。"""
    t0 = time.time()
    cand = {}
    for sid, S in SIG.items():
        em = elig.get(sid)
        if not em:
            continue
        v = np.unpackbits(_G["VAL"][sid])[:len(mon)].astype(bool)
        Xd = set(x_days(S, xopt).tolist())
        for t in np.flatnonzero(v[s0 - 1:s1]) + s0 - 1:
            if mon[t] in em and int(t) not in Xd:
                cand.setdefault(mon[t], []).append((sid, int(t)))
    per_m = R.groupby(mon[R["t"].to_numpy(int)]).size().to_dict()
    _G["FAKEJOB"] = {"R": R, "SIG": SIG, "xopt": xopt, "s0": s0, "s1": s1, "hold": base["_hold_pool"], "cand": cand, "per_m": per_m}
    out = {"A": [], "B": []}
    with Pool(a.procs) as pool:
        for x in pool.imap_unordered(fake_one, range(a.fake), chunksize=4):
            out["A"].append(x[0]); out["B"].append(x[1])
    cA, cB = np.array(out["A"]), np.array(out["B"])
    m = base["cagr_med"]
    log(f"  [假訊號 {E}] {a.fake} 次｜{time.time() - t0:.0f}s")
    return {"A_隨機出場_中位年化": float(np.median(cA)), "A_本格年化贏過的比例": float((m > cA).mean()), "A_p（隨機 ≥ 本格）": float((cA >= m).mean()),
            "B_隨機進場_中位年化": float(np.median(cB)), "B_本格年化贏過的比例": float((m > cB).mean()), "B_p（隨機 ≥ 本格）": float((cB >= m).mean()),
            "次數": a.fake, "B_每次列數": int(sum(per_m.values())), "A_持有天數池": int(len(base["_hold_pool"]))}


def fake_one(i):
    J = _G["FAKEJOB"]
    R, SIG, xopt, s0, s1 = J["R"], J["SIG"], J["xopt"], J["s0"], J["s1"]
    cz, oz, ncal = _G["cz"], _G["oz"], _G["ncal"]
    rng = np.random.default_rng([20260927, i]); r = i % 200
    # A
    if len(J["hold"]) == 0:
        dA = np.full(len(R), 10 ** 9)
    else:
        h = rng.choice(J["hold"], size=len(R), replace=True)
        dA = R["entry_pos"].to_numpy(int) + h - 1
    sig = pd.DataFrame({"sid": R["sid"].to_numpy(), "entry_pos": R["entry_pos"].to_numpy(int), "xpos_X": s1 + 1})
    sig["g_X"] = [float(cz[s][s1 + 1]) / L.engine_ep(oz, cz, s, e) - 1.0 for s, e in zip(sig["sid"], sig["entry_pos"])]
    sl = {(s, int(e)): (int(d), np.array([BIG])) for s, e, d in zip(sig["sid"], sig["entry_pos"], dA) if d <= s1}
    oA = R11.simulate_mtm(sig, "X", 10, np.random.default_rng(1000 + r), cz, oz, ncal, return_equity=True, stop_line=sl)
    cA, _, _ = RR.win_metrics(np.asarray(oA["equity"], float), oA["first"], oA["end"], s0, s1)
    # B
    rows = []
    for m_ in sorted(J["per_m"]):
        n_ = J["per_m"][m_]; cm = J["cand"].get(m_, [])
        if not cm:
            continue
        for j in rng.choice(len(cm), size=min(n_, len(cm)), replace=False):
            sid, t = cm[j]
            Xd = x_days(SIG[sid], xopt); e = t + 1
            k = int(np.searchsorted(Xd, e)); dX = int(Xd[k]) if k < len(Xd) and Xd[k] <= s1 else -1
            rows.append((sid, e, dX))
    B = pd.DataFrame(rows, columns=["sid", "entry_pos", "dX"]).drop_duplicates(["sid", "entry_pos"])
    sigB = pd.DataFrame({"sid": B["sid"].to_numpy(), "entry_pos": B["entry_pos"].to_numpy(int), "xpos_X": s1 + 1})
    sigB["g_X"] = [float(cz[s][s1 + 1]) / L.engine_ep(oz, cz, s, e) - 1.0 for s, e in zip(sigB["sid"], sigB["entry_pos"])]
    slB = {(s, int(e)): (int(d), np.array([BIG])) for s, e, d in zip(B["sid"], B["entry_pos"], B["dX"]) if d >= 0}
    oB = R11.simulate_mtm(sigB, "X", 10, np.random.default_rng(1000 + r), cz, oz, ncal, return_equity=True, stop_line=slB)
    cB, _, _ = RR.win_metrics(np.asarray(oB["equity"], float), oB["first"], oB["end"], s0, s1)
    return float(cA), float(cB)


def run_cells_g(keys, s0, s1, reps, procs, tag, log):
    t0 = time.time(); res = {k: [] for k in keys}
    with Pool(procs) as pool:
        for x in pool.imap_unordered(run_one, [(k, r, s0, s1) for k in keys for r in range(reps)], chunksize=2):
            res[x["key"]].append(x)
    log(f"  [{tag}] {len(keys)} 格 × {reps} 顆｜{time.time() - t0:.0f}s")
    return res


def early(a):
    """早年段個股層（描述、⛔ 不判）：挑中的格照跑。⚠ 受個股法人資料限制：只跑 2012-06～2016（A 段 early 版面、B 段主快照），只上市。"""
    logf = open(os.path.join(a.out, "run.log"), "a", encoding="utf-8")

    def log(x):
        print(x, flush=True); logf.write(x + "\n"); logf.flush()
    SP = os.path.join(a.out, "summary.json"); S = json.load(open(SP, encoding="utf-8"))
    ch = S["探索段挑出場"]; st = S["探索段挑停損停利"]
    log(f"===== researchSig early reps={a.reps} {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜挑中：{ch}、{st} =====")
    OUTE = {}
    for part, (lo_d, hi_d) in (("A", EARLY_A), ("B", EARLY_B)):
        if part == "A":
            st_ = json.load(open(os.path.join(os.path.dirname(EARLY_DATA), "STATUS.json"), encoding="utf-8"))
            assert st_.get("complete"), "⛔ 早年版面不完整"
            D.DATA = EARLY_DATA; panel = EARLY_PANEL
        else:
            D.DATA = RV.H2.H2D; panel = PANEL
        cal = D.load_calendar(); ncal = len(cal); mon = np.array([str(x)[:7] for x in cal])
        s0, s1 = int(cal.searchsorted(pd.Timestamp(lo_d))), int(cal.searchsorted(pd.Timestamp(hi_d)))
        assert str(cal[s0].date()) == lo_d and str(cal[s1].date()) == hi_d and s1 + 1 < ncal
        sids, elig, mk = stock_universe(cal, panel, os.path.join(D.DATA, "meta", "stocks.csv"), twse_only=True)
        cache = os.path.join(a.out, f"sig_cache_early{part}.pkl")
        if part == "B":
            SIG_all, VAL_all = pickle.load(open(os.path.join(a.out, "sig_cache.pkl"), "rb"))
            SIG = {k: v for k, v in SIG_all.items() if k in set(sids)}; VAL = {k: VAL_all[k] for k in SIG}
        elif os.path.exists(cache):
            SIG, VAL = pickle.load(open(cache, "rb"))
        else:
            t0 = time.time(); SIG = {}; VAL = {}
            with Pool(a.procs, initializer=_init, initargs=({"cal": cal},)) as pool:
                for r in pool.imap_unordered(stock_sig, [(s_, mk.get(s_, "twse")) for s_ in sids], chunksize=4):
                    if r is not None:
                        SIG[r["sid"]] = r["S"]; VAL[r["sid"]] = r["valid"]
            pickle.dump((SIG, VAL), open(cache, "wb"))
            log(f"[早年 {part} 訊號] {len(SIG)} 檔｜{time.time() - t0:.0f}s")
        cz, oz = RR.load_prices(sorted(SIG), cal, mk, "branch")
        BC = {}
        bars_of = lambda s_: BC.setdefault(s_, R11.load_bars(s_, mk.get(s_, "twse"), cal))
        valid_of = lambda s_: np.unpackbits(VAL[s_])[:ncal].astype(bool)
        bench = RR.load_bench(cal); b50 = RR.bench_row(cal, bench, s0, s1 + 1)
        CELLS = {}
        _G.update(cal=cal, cz=cz, oz=oz, ncal=ncal, CELLS=CELLS, VAL=VAL)
        keys = []
        for E in ("E1", "E2"):
            R, drop, byc = build_rows(SIG, elig, mon, E, ch[E], s0, s1); R = R.reset_index(drop=True)
            SD = stop_days(R, cz, oz, bars_of, s1, valid_of)
            sig, kw, reason = make_cell(R, SD, s1, "無", "無", cz, oz)
            k = (f"早年{part}", E, ch[E], "無", "無"); CELLS[k] = (sig, kw, reason, None); keys.append(k)
            if st[1] == E and not (st[3] == "無" and st[4] == "無"):
                cf = cf_signal_exit(R, SD, cz, oz, s1)
                sig, kw, reason = make_cell(R, SD, s1, st[3], st[4], cz, oz)
                k2 = (f"早年{part}", E, ch[E], st[3], st[4]); CELLS[k2] = (sig, kw, reason, cf); keys.append(k2)
            log(f"[早年 {part} {E}] 進場列 {len(R)}（同日出場不進 {drop}）｜{byc}")
        res = run_cells_g(keys, s0, s1, a.reps, a.procs, f"早年 {part}", log)
        for k in keys:
            c = agg(res[k], b50)
            OUTE["|".join(k)] = {kk: v for kk, v in c.items() if not kk.startswith("_")}
        OUTE[f"早年{part}_窗"] = [lo_d, hi_d]; OUTE[f"早年{part}_0050"] = b50; OUTE[f"早年{part}_資料"] = D.DATA
    D.DATA = RV.H2.H2D
    S["早年個股"] = OUTE
    S["早年個股_註"] = ("受個股法人資料限制：W1 eligible 要個股三大法人，data/early 自 2012-05 起才有 ⇒ 只跑 2012-06～2016、只上市；"
                    "A 段 2012-06-01～2014-12-30（early 版面 3edc0e2206）、B 段 2015-08-03～2016-12-30（主快照；panel_ext 在 2015-01～07 因 K 棒數不足 120 根無人合格）；"
                    "兩段各自期初全現金；描述、⛔ 不判、⛔ 不計 N")
    json.dump(S, open(SP, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log("[早年個股 完成]")
    report(a.out)


def _p(x, d=2):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—"
    return "—" if not np.isfinite(x) else f"{x * 100:+.{d}f}%"


def report(OUT_):
    S = json.load(open(os.path.join(OUT_, "summary.json"), encoding="utf-8"))
    C = pd.read_csv(os.path.join(OUT_, "cells.csv"))
    ch = S["探索段挑出場"]; st = S["探索段挑停損停利"]; B = S["0050同段"]; L50 = S["0050層"]; F = S.get("假訊號", {})

    def cell(seg, E, x, sl="無", tp="無"):
        q = C[(C["段"] == seg) & (C["E"] == E) & (C["出場"] == x) & (C["停損"] == sl) & (C["停利"] == tp)]
        return q.iloc[0] if len(q) else None
    c1, c2 = cell("確認", "E1", ch["E1"]), cell("確認", "E2", ch["E2"])
    cst = cell("確認", st[1], st[2], st[3], st[4])
    Lc = L50["確認"]
    labs = [c1["label"], c2["label"]]
    L = ["# PREREG訊號系統：築底起漲／底部反轉進、高檔反轉出（可再進場）＋停損停利 16 組＋0050 層", "",
         f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。登錄 seq1（sha 8e8595d3ce5f3c51）；裁定 seq243／244／245；新規矩 seq241／242。回測線。", ""]
    if "合格" in labs or "另列" in labs:
        L.append(f"**結論：確認段（2022～2026）E1 {c1['label']}、E2 {c2['label']}；0050 層年化{'高於' if Lc['判定_年化高於一直抱'] else '沒有高於'}一直抱 0050。**")
    else:
        L.append(f"**結論：訊號進、訊號出沒有贏 0050（確認段 E1、E2 都不合格）；停損停利{'沒有加分' if st[3] == '無' and st[4] == '無' else '挑出的那組在確認段也' + ('合格' if cst is not None and cst['label'] == '合格' else '沒有贏 0050')}；"
                 f"0050 層年化{'高於' if Lc['判定_年化高於一直抱'] else '低於'}一直抱 0050。**")
    dp = os.path.join(OUT_, "desc_anyexit.json")
    if os.path.exists(dp):
        DA = json.load(open(dp, encoding="utf-8"))
        L += ["", "## 裁定 seq246（判定更正）", "",
              "- ⭐ E1、E2 確認段判定格改判【依構造不可判定】：探索段挑中的出場〔黃昏之星〕在確認段幾乎不觸發，判定格退化成「段初買進、抱到段尾」，"
              "測不到「訊號進、訊號出」⇒ ⛔ 不另挑判定格；下表「不合格」的原數字保留、⛔ 不改",
              "- 停損停利挑中組（E1＋SL10＋TP50h）與 0050 層的判定照原樣",
              f"- 描述補報「X 任一」出場版（⚠ {DA['性質']}；resultsSig/desc_anyexit.*）：", "",
              "| E（確認段、X 任一） | 年化中位 | 回落中位 | 每顆交易筆 | 段尾未出場（每顆） |", "|---|---|---|---|---|"]
        for E, d in DA["格"].items():
            L.append(f"| {E} | {_p(d['年化中位'])} | {_p(d['回落中位'])} | {d['每顆交易筆']:.1f} | {d['段尾未出場_每顆']:.1f} |")
        L += ["", f"  每年交易（每顆平均）：" + "；".join(f"{E} {d['每年交易']}" for E, d in DA["格"].items())]
    L += ["", f"確認段 0050：年化 {_p(B['確認']['cagr'])}、回落 {_p(B['確認']['mdd'])}（比值 {B['確認']['cagr'] / abs(B['確認']['mdd']):.3f}）", "",
          "| 格（確認段） | 進場 | 出場 | 停損／停利 | 年化中位 | 回落中位 | 比值 | 判定 |", "|---|---|---|---|---|---|---|---|"]
    for nm, q, E in (("E1 築底起漲", c1, "E1"), ("E2 底部反轉", c2, "E2")):
        L.append(f"| {nm} | {E} | {XNAME[q['出場']]}（探索段挑） | 無 | {_p(q['cagr_med'])} | {_p(q['mdd_med'])} | {q['ratio']:.3f} | **{q['label']}** |")
    if st[3] == "無" and st[4] == "無":
        L.append(f"| 停損停利 32 選 1 | {st[1]} | {XNAME[st[2]]} | 挑中「無」⇒ 與上列同格、N 不另加 | — | — | — | 停損停利沒有加分 |")
    else:
        L.append(f"| 停損停利 32 選 1 | {st[1]} | {XNAME[st[2]]} | {st[3]}／{st[4]} | {_p(cst['cagr_med'])} | {_p(cst['mdd_med'])} | {cst['ratio']:.3f} | **{cst['label']}** |")
    L.append(f"| 0050 層 | 0050 自己的 E1∪E2 | X 任一 | 無 | {_p(Lc['cagr'])} | {_p(Lc['mdd'])} | {Lc['ratio']:.3f} | 一直抱 {_p(Lc['抱0050_cagr'])}／{_p(Lc['抱0050_mdd'])} ⇒ "
             f"**{'高於' if Lc['判定_年化高於一直抱'] else '低於'}一直抱** |")
    # ⚠ 退化解（〈一百一十四〉）與假訊號臂 A 的可解讀性
    notes = []
    for E, q in (("E1", c1), ("E2", c2)):
        if q["段尾未出場_每顆"] >= 9 and q["交易筆_每顆平均"] <= 15:
            notes.append(f"{E}：挑中的出場〔{XNAME[q['出場']]}〕在確認段幾乎不觸發（每顆交易 {q['交易筆_每顆平均']:.1f} 筆、段尾未出場 {q['段尾未出場_每顆']:.1f} 檔、持有中位 "
                         f"{q['持有天數_中位'] if q['持有天數_中位'] == q['持有天數_中位'] else '—'} 天）⇒ 判定格實際上退化成「段初買進最先出現進場訊號的 10 檔、一路抱到段尾」，"
                         "⛔ 不是在測「訊號進、訊號出」；挑法照登錄 §四（比值最高）事前寫死，本件照挑")
        fk = F.get(E, {})
        if fk.get("A_持有天數池", 0) <= 200:
            notes.append(f"{E}：假訊號臂 A 的持有天數池只有 {fk.get('A_持有天數池', 0)} 筆已結清交易（200 顆合併）⇒ 隨機出場幾乎等於不出場，A 的 p 值 ⛔ 不可解讀")
    notes.append("新規矩 ③（seq242 ②）：確認段判定格都不合格 ⇒ 不跟進出場敏感度；早年段 B 段 E1 雖對 0050 為「合格」，但早年段只描述、不判 ⇒ 不跟進")
    L += ["", "⚠ 讀之前先看：", ""] + [f"- {x}" for x in notes]
    L += ["", "## 結果句（⛔ 照登錄 §四出口表）", ""]
    for E, q in (("E1", c1), ("E2", c2)):
        fk = F.get(E, {}); pA, pB = fk.get("A_p（隨機 ≥ 本格）", np.nan), fk.get("B_p（隨機 ≥ 本格）", np.nan)
        pre_ = "隨機也做得到：" if (np.isfinite(pA) and pA >= 0.05) or (np.isfinite(pB) and pB >= 0.05) else ""
        if q["label"] == "合格":
            s_ = f"{pre_}〔{E}〕進、〔{XNAME[q['出場']]}〕出，2022～2026 年化 {_p(q['cagr_med'])}／回落 {_p(q['mdd_med'])}，贏 0050（{_p(B['確認']['cagr'])}）且風險調整後不輸"
        elif q["label"] == "另列":
            s_ = f"{pre_}〔{E}〕進、〔{XNAME[q['出場']]}〕出：報酬贏 0050，但回落比例上不划算（年化 {_p(q['cagr_med'])}／回落 {_p(q['mdd_med'])}）"
        else:
            s_ = f"{pre_}〔{E}〕訊號進、訊號出沒有贏 0050（年化 {_p(q['cagr_med'])}／回落 {_p(q['mdd_med'])}）"
        h = {H: cell("確認", E, f"H{H}") for H in (20, 60, 120)}
        s_ += (f"。用訊號出場 vs 固定抱 60 天：年化差 {(q['cagr_med'] - h[60]['cagr_med']) * 100:+.2f} 點（抱 20 天 {(q['cagr_med'] - h[20]['cagr_med']) * 100:+.2f}、"
               f"抱 120 天 {(q['cagr_med'] - h[120]['cagr_med']) * 100:+.2f}）")
        s_ += f"；假訊號 A（同進場＋隨機出場）p＝{pA:.3f}、B（隨機進場＋同出場）p＝{pB:.3f}"
        L.append(f"- {s_}")
    L.append(f"- 0050 層：年化 {_p(Lc['cagr'])}（回落 {_p(Lc['mdd'])}）vs 一直抱 {_p(Lc['抱0050_cagr'])}（回落 {_p(Lc['抱0050_mdd'])}）⇒ {'有' if Lc['判定_年化高於一直抱'] else '沒有'}多賺")
    L += ["", "## 必報（確認段判定格；200 顆合併）", "",
          "| 格 | 每顆交易筆 | 勝率 | 平均淨報酬 | 持有天數 平均／中位（10／90 分位） | 再進場 每顆筆數／平均／勝率 | 首次進場 平均／勝率 | 段尾未出場 | 平均持股／現金比例 |",
          "|---|---|---|---|---|---|---|---|---|"]
    rows_ = [("E1", c1), ("E2", c2)] + ([("停損停利挑中", cst)] if cst is not None and not (st[3] == "無" and st[4] == "無") else [])
    for nm, q in rows_:
        L.append(f"| {nm} | {q['交易筆_每顆平均']:.1f} | {q['勝率']:.3f} | {_p(q['平均淨報酬'])} | {q['持有天數_平均']:.1f}／{q['持有天數_中位']:.0f}（{q['持有天數_p10']:.0f}／{q['持有天數_p90']:.0f}） | "
                 f"{q['再進場_筆數每顆']:.1f}／{_p(q['再進場_平均淨報酬'])}／{q['再進場_勝率']:.3f} | {_p(q['首次進場_平均淨報酬'])}／{q['首次進場_勝率']:.3f} | {q['段尾未出場_每顆']:.1f} | "
                 f"{q['平均持股檔數']:.2f}／{q['現金比例']:.3f} |")
    L += ["", "每年交易次數（每顆平均）與出場原因占比：", ""]
    for nm, q in rows_:
        L.append(f"- {nm}：每年 {q['每年交易']}；出場原因 {q['出場原因占比']}" + (f"；放棄組 {q['放棄組']}" if isinstance(q.get('放棄組'), str) else ""))
    L += ["", "## 對照：同進場、固定持有（天數軸，seq241）", "", "| 段 | E | 訊號出場 | 抱 20 | 抱 60 | 抱 120 |", "|---|---|---|---|---|---|"]
    for seg in ("探索", "確認"):
        for E in ("E1", "E2"):
            q = cell(seg, E, ch[E]); h = {H: cell(seg, E, f"H{H}") for H in (20, 60, 120)}
            L.append(f"| {seg} | {E} | {_p(q['cagr_med'])}／{_p(q['mdd_med'])} | " + " | ".join(f"{_p(h[H]['cagr_med'])}／{_p(h[H]['mdd_med'])}" for H in (20, 60, 120)) + " |")
    L += ["", "## 假訊號臂（確認段；各 1,000 次；描述、不計 N）", ""]
    for E in ("E1", "E2"):
        L.append(f"- {E}：{F.get(E)}")
    L += ["", "## 探索段：9 種出場（挑法：過判準的取比值最高；都沒過取比值最高）", "", "| E | 出場 | 年化中位 | 回落中位 | 比值 | 判定 | 每顆交易筆 | 持有中位 | 段尾未出場 |", "|---|---|---|---|---|---|---|---|---|"]
    for E in ("E1", "E2"):
        for x in EXITS:
            q = cell("探索", E, x)
            mark = "⭐ " if x == ch[E] else ""
            L.append(f"| {E} | {mark}{XNAME[x]} | {_p(q['cagr_med'])} | {_p(q['mdd_med'])} | {q['ratio']:.3f} | {q['label']} | {q['交易筆_每顆平均']:.1f} | {q['持有天數_中位']:.0f} | {q['段尾未出場_每顆']:.1f} |")
    L += ["", f"探索段 0050：年化 {_p(B['探索']['cagr'])}、回落 {_p(B['探索']['mdd'])}", "",
          "## 探索段：停損停利 16 組 × E（32 選 1；並列「無」）", "", "| E | 停損 | 停利 | 年化中位 | 回落中位 | 比值 | 判定 | 出場原因占比 | 賣半次數 | 放棄組 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for E in ("E1", "E2"):
        for sl in SLS:
            for tp in TPS:
                q = cell("探索", E, ch[E], sl, tp)
                if q is None:
                    continue
                mark = "⭐ " if (E, sl, tp) == (st[1], st[3], st[4]) else ""
                L.append(f"| {E} | {mark}{sl} | {tp} | {_p(q['cagr_med'])} | {_p(q['mdd_med'])} | {q['ratio']:.3f} | {q['label']} | {q['出場原因占比']} | {q['賣半次數每顆']:.1f} | {q.get('放棄組', '—') if isinstance(q.get('放棄組'), str) else '—'} |")
    L += ["", "## 0050 層（三段）", "", "| 段 | 年化 | 回落 | 一直抱 年化／回落 | 交易筆 | 勝率 | 平均持有天數 | 持股時間比例 |", "|---|---|---|---|---|---|---|---|"]
    for seg in ("探索", "確認", "早年"):
        q = L50[seg]
        L.append(f"| {seg} | {_p(q['cagr'])} | {_p(q['mdd'])} | {_p(q['抱0050_cagr'])}／{_p(q['抱0050_mdd'])} | {q['交易筆']} | {q['勝率'] if q['勝率'] == q['勝率'] else '—'} | "
                 f"{q['平均持有天數'] if q['平均持有天數'] == q['平均持有天數'] else '—'} | {q['持股時間比例']:.3f} |")
    if S.get("早年個股"):
        L += ["", "## 早年段個股層（描述、⛔ 不判；⚠ 受個股法人資料限制：只跑 2012-06～2016、只上市）", "", f"{S.get('早年個股_註')}", "",
              "| 段 | 格 | 年化中位 | 回落中位 | 比值 | 對 0050（描述） | 0050 同段 |", "|---|---|---|---|---|---|---|"]
        for k, v in S["早年個股"].items():
            if "|" not in k:
                continue
            part = k.split("|")[0]; b_ = S["早年個股"][f"{part}_0050"]
            L.append(f"| {part} | {k} | {_p(v['cagr_med'])} | {_p(v['mdd_med'])} | {v['ratio']:.3f} | {v['label']} | {_p(b_['cagr'])}／{_p(b_['mdd'])} |")
    L += ["", "## 讀法與沿用（逐條）", "",
          "- 沿用：營飆 v1 骨架（N＝10、淨值 1/10、抽籤、種子 1000＋r、200 顆取中位、成本 0.585%、引擎無 tradable）；訊號次日開盤進；⛔ 無時間出口，段尾收盤按市值計",
          "- 訊號定義全部沿用 researchRev（已 commit 502cf9761f）與 PREREGX／研究二（箱型、杯柄）原樣；E2 的 KD／MACD 底背離與 X 的高檔爆量長上影用確認版（訊號日＝確認日）",
          "- 母體：W1 eligible 當月面板 ∩ gate3；同日同檔有進場與出場訊號 ⇒ 不進；已持有不加碼；再進場不設冷卻",
          "- 停損停利：觸發日取最早、次日開盤執行；+50% 賣半用引擎 trim_rule（剩半照原規則）",
          f"- 面板：{S.get('面板')}（2026-03-02 以前與 resultsp4/panel.csv.gz 在重疊列的 eligible 逐列相同；resultsp4 多出的 1,061 列全不在 gate3）",
          "- 早年段：0050 層 2004-02-11～2016-12-30（data/early 接主快照）；個股層只跑 2012-06～2016（受個股法人資料限制，見上）",
          f"- 0050 資料：{S.get('0050資料')}", ""]
    open(os.path.join(OUT_, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
