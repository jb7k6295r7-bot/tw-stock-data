# -*- coding: utf-8 -*-
"""PREREG洗盤還是出貨（圖卡四條合判）seq1（台股策略線登錄 sha bed6ad77174957ec，2026-10-04 21:59；裁定 seq300 §二 發號、N_單筆 ＋9）。回測線。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchWashDist body [--procs 4]
    抽樣查核：--check（⛔ 不呼叫本體的事件、條件、基準函式，逐日迴圈自算）｜網頁：page

⭐ 讀法寫死時間：2026-10-04 22:30（台北）；寫死前 ⛔ 沒看任何本件輸出。
⚠ 照實標（裁定 seq300 §二）：單條（量縮、放量滯漲、長上影、跌破支撐、等拉回）先前多已測過、多半不支持；本件只問「四條合判有沒有增量」，結果句不改寫單條的舊結論。
⚠ 圖卡「看後續」是事後標籤 ⛔ 不進條件，只報事後準確度。

═══ 時間線（登錄 §一；有效 K 棒序列上數，執行者補）═══
  前高 P ＝ 觸發日 j 往前 60 根（含 j）最高還原收盤那一根（平手取最早）
  觸發（回檔成立）j ＝ 第一個 c[j] ≤ c[P]×(1−D) 的日子，且起漲段成立：c[P] ÷ c[P−60] − 1 ≥ U（「前 60 日收盤漲幅」量在前高 P，執行者補）
  回檔低點 L ＝ P 之後到當下的最低收盤（平手取最早）；反彈確認 T ＝ j 之後第一根 c[T] ≥ c[L] ＋ (c[P] − c[L])／3（L 取到 T 前一根）
  30 日內沒反彈：T − j ＞ 30 ⇒ 不成事件（計數）；之後從 j＋31 起重找
  去重（主版）：事件 T 之後 60 根內不算新事件；不去重版：T 之後從 T＋1 起重找，但新觸發的前高 P 須在上一個 T 之後（免得同一段回檔重複觸發，執行者補）
  位置量要 250 根：前高 P 之前不足 250 根有效 K 棒 ⇒ 不成事件（計數，執行者補）
═══ 四條（登錄 §二 寫死；數字格 U、D、P、支撐）═══
  ① 位置：c[P] ÷ min(c[P−249..P]) − 1 ＜ P格 ⇒ 像洗盤；≥ ⇒ 像出貨
  ② 量能：像洗盤 ＝ 回檔段（P＋1..L）原始成交股數均量 ÷ 起漲段（P−59..P）均量 ＜ 0.8；
           像出貨 ＝ [P−10, min(P＋10, T)] 內有一根「量 ≥ 2 × 前 20 根均量 且 當日還原收盤漲幅 ≤ 0.5%」（兩者可同時成立或都不成立）
  ③ 走勢：支撐格 ∈ {MA60：T 日 60 根還原收盤簡單均線；回撤：c[P−60] ＋ 0.5 ×（c[P] − c[P−60]）}；c[L] ≥ 支撐 ⇒ 像洗盤，＜ ⇒ 像出貨
  ④ 反彈：像洗盤 ＝ 反彈段（L＋1..T）均量 ＞ 回檔段均量 且 L 之後沒有更低收盤（依 L 的定義到 T 恆成立）；像出貨 ＝ 反彈段均量 ＜ 回檔段均量
  分組：洗盤組 ＝ 四條都像洗盤｜出貨組 ＝ ≥ 3 條像出貨｜其餘 ＝ 混合（描述）
  格：U {20%, 40%} × D {8%, 15%} × P {50%, 100%} × 支撐 {MA60, 回撤50%} ＝ 16
═══ 報酬與基準（登錄 §三）═══
  進場 T＋1 開盤（還原）；T＋1 停牌或開盤漲停 ⇒ 買不到、剔除計數；R_H ＝ 還原收盤(T＋H，交易日曆、ffill) ÷ 還原開盤(T＋1) − 1，H ∈ {5, 20, 60}
  硬斷點（tw-stock-price-breaks：data.breakpoints 的價格斷點＋researchM_freq 連續缺 5 日）落在 [P−60, T＋H] ⇒ 剔除計數（執行者補：區段）
  基準② ＝ 同日 T、母體（eligible ∩ GATE_V2）中前 20 根報酬同十分位股票的同式 R 等權平均（十分位整數式 ＝ researchPatAll decile_int）；X ＝ R − 基準②
  另報：對全體（同日母體等權）、對 0050（同式）
  CI ＝ 月分群（T 所在曆月；research11.cl_stats CR0、1.96）
  Q1 ＝ 洗盤組 X − 0.585% 的 CI 下緣 ＞ 0｜Q3 ＝ 出貨組 X（不扣成本）CI 上緣 ＜ 0
  Q2 ＝ 洗盤組 − 出貨組：差 ＝ 兩組平均差，SE ＝ √(SE洗² ＋ SE出²)（兩組各自月分群；執行者補：忽略兩組同月共變），下緣 ＞ 0
  過半（各 H、各段）：主版分母 ＝ 該組事件 ≥ 30 的格（Q2 兩組都 ≥ 30），通過格數 ＞ 分母／2；另報「≥ 9／16」全格版；兩段都過才算成立；早年方向相反照寫
  事件 ＜ 30 的格標「樣本少」、⛔ 不併格
  段：探索 2017-03-02～2021-12-30｜確認 2022-01-03～2026-08-24（T＋1 在段內且 T＋H ≤ 段尾）｜早年 2005-02-01～2014-12-30（early 版面、只上市；2012-06 前無個股法人 ⇒ eligible_v，同 researchVolBreak）
  母體：W1 eligible（T 那個月面板）∩ gate3，⭐ UG.set_gate_v2(True) ⇒ 另要求 T 的 pit_valid；含已下市
═══ 描述（⛔ 不判）═══
  四條逐條（各條 像洗盤 − 像出貨 的 X 差，H20）｜各組事件數、每年分佈、混合組｜30 日內沒反彈比例｜事後標籤：T 後 20 根內收盤創前高 c[P] 的比例（洗盤 vs 出貨）
  現實版（描述）：進出改當日 (開＋高＋低＋收)÷4、每邊多 0.3%（researchSlip C1＋C4；C2 衝擊需資金規模，單筆層不加）
輸出 backtest/resultsWashDist/（summary.json、cells.csv、events.csv.gz、desc.json、check.json、洗盤還是出貨.html）
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchSig as RS
RV, D, RR, R11 = RS.RV, RS.D, RS.RR, RS.R11
from backtest import tradability as TR
from backtest import p4_features as P4F
import researchM_freq as RF

OUT = os.path.join(RS.HERE, "resultsWashDist")
US, DS, PS, SUPS = (0.20, 0.40), (0.08, 0.15), (0.50, 1.00), ("MA60", "回撤50%")
HS = (5, 20, 60)
SEG = {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}
EARLY = ("2005-02-01", "2014-12-30")
COST = 0.00585
TAGT = "2026-10-04 22:30（台北）"
_G: dict = {}


def set_v2(on):
    sys.modules["backtest.universe_gate"].set_gate_v2(on)


def UGm():
    return sys.modules["backtest.universe_gate"]


# ═════════════ 事件（每檔、每個 U×D）═════════════
def find_events(c, U, Dd, dedup=True):
    """c ＝ 有效 K 棒還原收盤。回 [(P, j, L, T)]（索引＝有效 K 棒序號）與 30 日沒反彈次數、不足 250 根次數。"""
    n = len(c); out = []; norb = 0; short = 0
    i = 60; lastT = -10 ** 9
    while i < n:
        if dedup and i <= lastT + 60:
            i = lastT + 61; continue
        lo = i - 59
        P = lo + int(np.argmax(c[lo:i + 1]))
        if not dedup and P <= lastT:
            i += 1; continue
        if P - 60 < 0 or not (c[P] / c[P - 60] - 1.0 >= U) or not (c[i] <= c[P] * (1.0 - Dd)):
            i += 1; continue
        j = i
        if P < 249:
            short += 1; i = j + 1; continue
        L = P + 1 + int(np.argmin(c[P + 1:j + 1])); T = -1
        k = j + 1
        while k < n and k - j <= 30:
            if c[k] >= c[L] + (c[P] - c[L]) / 3.0:
                T = k; break
            if c[k] < c[L]:
                L = k
            k += 1
        if T < 0:
            norb += 1; i = j + 31; continue
        out.append((P, j, L, T)); lastT = T
        i = T + 1
    return out, norb, short


def conds(c, v, P, L, T, Pthr, sup, ma60):
    """四條 ⇒ ({條: (像洗盤, 像出貨)})。c、v 有效 K 棒序列。"""
    r = {}
    pos = c[P] / np.min(c[P - 249:P + 1]) - 1.0
    r["位置"] = (pos < Pthr, pos >= Pthr)
    vr = np.mean(v[P - 59:P + 1]); vp = np.mean(v[P + 1:L + 1]); vb = np.mean(v[L + 1:T + 1])
    w2 = (vr > 0) and (vp / vr < 0.8)
    d2 = False
    for q in range(max(P - 10, 20), min(P + 10, T) + 1):
        a20 = np.mean(v[q - 20:q])
        if a20 > 0 and v[q] >= 2 * a20 and (c[q] / c[q - 1] - 1.0) <= 0.005:
            d2 = True; break
    r["量能"] = (bool(w2), bool(d2))
    lvl = ma60 if sup == "MA60" else c[P - 60] + 0.5 * (c[P] - c[P - 60])
    r["走勢"] = (bool(c[L] >= lvl), bool(c[L] < lvl))
    r["反彈"] = (bool(vb > vp), bool(vb < vp))
    return r


def events_one(args):
    sid, mk = args
    cal = _G["cal"]; n = len(cal)
    st = D.load_stock(sid, mk, cal)
    if st is None:
        return sid, None
    df = st.df
    c = df["close"].to_numpy(float); o = df["open"].to_numpy(float); h = df["high"].to_numpy(float); l = df["low"].to_numpy(float)
    ro, rh, rl, rc, rv = RV.load_raw(sid, cal)
    b = np.flatnonzero(np.isfinite(c) & np.isfinite(rv))
    if len(b) < 320:
        return sid, None
    cb, vb = c[b], np.nan_to_num(rv[b])
    ma60 = pd.Series(cb).rolling(60).mean().to_numpy()
    valid = np.isfinite(c)
    pb = np.zeros(n, bool)
    for x in D.breakpoints(df, st.event_dates):
        if x["rule"] in ("price", "price+gap"):
            pb[x["pos"]] = True
    g5 = RF._g5(valid)
    tb = TR.one(sid, cal)
    ev = []; acc = {}
    for U in US:
        for Dd in DS:
            for dedup in (True, False):
                E, norb, short = find_events(cb, U, Dd, dedup)
                acc[(U, Dd, dedup)] = (len(E), norb, short)
                for (P, j, L, T) in E:
                    tc = int(b[T])
                    for Pthr in PS:
                        for sup in SUPS:
                            cd = conds(cb, vb, P, L, T, Pthr, sup, ma60[T])
                            nw = sum(x[0] for x in cd.values()); nd = sum(x[1] for x in cd.values())
                            grp = "洗盤" if nw == 4 else ("出貨" if nd >= 3 else "混合")
                            newhi = bool(np.any(cb[T + 1:T + 21] > cb[P])) if T + 1 < len(cb) else False
                            ev.append((sid, U, Dd, dedup, Pthr, sup, int(b[P]), int(b[L]), tc, grp, *[int(cd[k][0]) - int(cd[k][1]) for k in ("位置", "量能", "走勢", "反彈")], newhi))
    cs_pb = np.cumsum(pb).astype(np.int32); cs_g5 = np.cumsum(g5).astype(np.int32)
    # 報酬（還原開 T＋1、收 T＋H）與現實版均價
    cz = pd.Series(c).ffill().to_numpy(float); avg = (o + h + l + c) / 4.0
    return sid, {"ev": ev, "acc": acc, "cs_pb": cs_pb, "cs_g5": cs_g5, "trd": tb["trd"], "up_o": tb["up_o"], "cz": cz.astype(np.float32), "o": o.astype(np.float32),
                 "avg": avg.astype(np.float32), "first": int(b[0]), "PIT": np.packbits(UGm().pit_valid(sid, cal))}


def world(name, data, panel, w, procs, log, elig_v=False, twse_only=False):
    D.DATA = data
    cal = D.load_calendar(); n = len(cal); mon = np.array([str(x)[:7] for x in cal])
    stocks = pd.read_csv(os.path.join(data, "meta", "stocks.csv"), dtype=str)
    U = UGm().gate3(stocks)
    if twse_only:
        U = U[U["market"] == "twse"]
    p = P4F.read_panel(panel)
    p["el"] = (p["liq_ok"].astype(bool) & p["bars_ok"].astype(bool)) if elig_v else p["eligible"].astype(bool)
    p = p[p["el"] & p["stock_id"].isin(set(U["stock_id"]))]
    elig = {sid: set(str(x)[:7] for x in g["measure_date"]) for sid, g in p.groupby("stock_id")}
    mk = U.set_index("stock_id")["market"].to_dict()
    sids = sorted(elig)
    if os.environ.get("WD_SMOKE"):
        sids = sids[:150]
    _G["cal"] = cal
    with Pool(procs) as pool:
        F = dict(pool.map(events_one, [(s, mk.get(s, "twse")) for s in sids], chunksize=8))
    F = {s: v for s, v in F.items() if v is not None}
    for s in F:
        F[s]["PIT"] = np.unpackbits(F[s]["PIT"])[:n].astype(bool)
    segs = {k: (int(cal.searchsorted(pd.Timestamp(a))), int(cal.searchsorted(pd.Timestamp(b_)))) for k, (a, b_) in w.items()}
    bench = RR.load_bench(cal)
    log(f"[世界 {name}] {data}｜母體 {len(F):,} 檔｜段 { {k: [str(cal[a].date()), str(cal[b_].date())] for k, (a, b_) in segs.items()} }")
    return {"name": name, "cal": cal, "n": n, "mon": mon, "elig": elig, "mk": mk, "F": F, "segs": segs, "bench": bench}


def baselines(Wd):
    """每個 H：R 矩陣、基準②（同日母體前 20 根報酬十分位等權）、全體等權。"""
    n = Wd["n"]; sids = sorted(Wd["F"]); ix = {s: i for i, s in enumerate(sids)}
    C = np.column_stack([Wd["F"][s]["cz"].astype(float) for s in sids]); O = np.column_stack([Wd["F"][s]["o"].astype(float) for s in sids])
    TRD = np.column_stack([Wd["F"][s]["trd"] for s in sids]); UPO = np.column_stack([Wd["F"][s]["up_o"] for s in sids])
    mon = Wd["mon"]
    EL = np.zeros((n, len(sids)), bool)
    for s in sids:
        em = Wd["elig"].get(s, set()); EL[:, ix[s]] = np.array([m in em for m in mon]) & Wd["F"][s]["PIT"]
    with np.errstate(invalid="ignore", divide="ignore"):
        r20 = np.full_like(C, np.nan); r20[20:] = C[20:] / C[:-20] - 1.0
    OK1 = np.zeros_like(TRD); OK1[:-1] = TRD[1:] & ~UPO[1:] & np.isfinite(O[1:]) & (O[1:] > 0)
    out = {}
    for H in HS:
        Rh = np.full_like(C, np.nan)
        with np.errstate(invalid="ignore", divide="ignore"):
            Rh[:n - H] = np.where(OK1[:n - H], C[H:n] / O[1:n - H + 1] - 1.0, np.nan)
        base = np.full_like(C, np.nan); ew = np.full(n, np.nan)
        for t in range(n - H):
            m = EL[t] & np.isfinite(r20[t]) & np.isfinite(Rh[t])
            if m.sum() < 20:
                continue
            x = r20[t, m]; rk = pd.Series(x).rank(method="first").to_numpy(); mm = len(x)
            dec = ((10 * (rk - 1))[:, None] > (np.arange(1, 10) * (mm - 1))[None, :]).sum(axis=1)
            rr = Rh[t, m]; mu = np.array([rr[dec == q].mean() for q in range(10)])
            bt = np.full(len(sids), np.nan); bt[np.flatnonzero(m)] = mu[dec]; base[t] = bt
            ew[t] = float(rr.mean())
        out[H] = (Rh, base, ew)
    return out, ix, EL


def body(a):
    global OUT
    if os.environ.get("WD_SMOKE"):
        OUT = os.path.expanduser("~/ugwork/wd_smoke")
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    log(f"===== researchWashDist body {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜讀法寫死 {TAGT} =====")
    set_v2(True)
    RR.use_snapshot()
    Wm = world("主快照", D.DATA, RS.PANEL, SEG, a.procs, log)
    We = world("早年版面（只上市）", RS.EARLY_DATA, RS.EARLY_PANEL, {"早年": EARLY}, a.procs, log, elig_v=True, twse_only=True)
    RR.use_snapshot()
    S = {"登錄": "PREREG洗盤還是出貨 seq1 sha bed6ad77174957ec；裁定 seq300 §二", "讀法寫死": TAGT, "GATE_V2": True}
    EVS = []; ACC = {}
    for Wd in (Wm, We):
        BL, ix, EL = baselines(Wd)
        bench = Wd["bench"]
        for seg, (s0, s1) in Wd["segs"].items():
            for s, f in Wd["F"].items():
                j = ix[s]
                for (sid, U, Dd, dedup, Pthr, sup, P, L, T, grp, c1, c2, c3, c4, newhi) in f["ev"]:
                    if not (s0 <= T + 1 <= s1) or T + 1 >= Wd["n"]:
                        continue
                    row = {"段": seg, "sid": sid, "U": U, "D": Dd, "去重": dedup, "P": Pthr, "支撐": sup, "T": T, "月": Wd["mon"][T], "組": grp,
                           "位置": c1, "量能": c2, "走勢": c3, "反彈": c4, "事後創前高": newhi}
                    if not EL[T, j]:
                        row["狀態"] = "母體外"
                    elif not (f["trd"][T + 1] and not f["up_o"][T + 1] and np.isfinite(f["o"][T + 1]) and f["o"][T + 1] > 0):
                        row["狀態"] = "T+1 停牌或開盤漲停"
                    else:
                        row["狀態"] = "保留"
                    for H in HS:
                        Rh, base, ew = BL[H]
                        if T + H > s1 or row["狀態"] != "保留":
                            row[f"X{H}"] = np.nan; continue
                        a_ = max(P - 60, 0)
                        if (f["cs_pb"][T + H] - (f["cs_pb"][a_ - 1] if a_ > 0 else 0)) > 0 or (f["cs_g5"][T + H] - f["cs_g5"][min(a_ + 3, T + H)]) > 0:
                            row[f"X{H}"] = np.nan; row[f"斷點{H}"] = True; continue
                        R = Rh[T, j]
                        row[f"R{H}"] = R; row[f"X{H}"] = R - base[T, j]; row[f"vsEW{H}"] = R - ew[T]
                        row[f"vs0050_{H}"] = R - (bench[T + H] / bench[T + 1] - 1.0)
                        av = f["avg"]
                        row[f"Xreal{H}"] = (float(av[T + H]) / float(av[T + 1]) - 1.0 - 2 * 0.003) - base[T, j] if np.isfinite(av[T + H]) and np.isfinite(av[T + 1]) and av[T + 1] > 0 else np.nan
                    EVS.append(row)
        for s, f in Wd["F"].items():
            for k, v in f["acc"].items():
                kk = f"{Wd['name']}|U{k[0]}|D{k[1]}|{'去重' if k[2] else '不去重'}"
                a0 = ACC.get(kk, [0, 0, 0]); ACC[kk] = [a0[0] + v[0], a0[1] + v[1], a0[2] + v[2]]
    E = pd.DataFrame(EVS)
    E.to_csv(os.path.join(OUT, "events.csv.gz"), index=False, float_format="%.6g")
    S["事件帳（全史、逐檔：成事件／30日沒反彈／不足250根）"] = {k: {"事件": v[0], "30日內沒反彈": v[1], "不足250根": v[2],
                                                       "沒反彈比例": v[1] / max(1, v[0] + v[1])} for k, v in ACC.items()}
    # ── 判定
    rows = []
    K = E[E["去重"] & (E["狀態"] == "保留")]
    for seg in ("探索", "確認", "早年"):
        for U in US:
            for Dd in DS:
                for Pthr in PS:
                    for sup in SUPS:
                        g = K[(K["段"] == seg) & (K["U"] == U) & (K["D"] == Dd) & (K["P"] == Pthr) & (K["支撐"] == sup)]
                        for H in HS:
                            w = g[g["組"] == "洗盤"]; d = g[g["組"] == "出貨"]; mx = g[g["組"] == "混合"]
                            sw = R11.cl_stats(w[f"X{H}"].to_numpy(float) - COST, w["月"].to_numpy()) if len(w) else {"n": 0}
                            sd = R11.cl_stats(d[f"X{H}"].to_numpy(float), d["月"].to_numpy()) if len(d) else {"n": 0}
                            sm = R11.cl_stats(mx[f"X{H}"].to_numpy(float), mx["月"].to_numpy()) if len(mx) else {"n": 0}
                            r = {"段": seg, "U": U, "D": Dd, "P": Pthr, "支撐": sup, "H": H,
                                 "洗盤_n": sw["n"], "洗盤_X−成本": sw.get("mean"), "洗盤_lo": sw.get("lo"), "洗盤_hi": sw.get("hi"),
                                 "出貨_n": sd["n"], "出貨_X": sd.get("mean"), "出貨_lo": sd.get("lo"), "出貨_hi": sd.get("hi"),
                                 "混合_n": sm["n"], "混合_X": sm.get("mean")}
                            r["Q1過"] = bool(sw["n"] and sw["lo"] > 0); r["Q3過"] = bool(sd["n"] and sd["hi"] < 0)
                            if sw["n"] and sd["n"]:
                                diff = (sw["mean"] + COST) - sd["mean"]; se = math.sqrt(sw["se"] ** 2 + sd["se"] ** 2)
                                r.update({"Q2_差": diff, "Q2_lo": diff - 1.96 * se, "Q2_hi": diff + 1.96 * se}); r["Q2過"] = bool(diff - 1.96 * se > 0)
                            else:
                                r["Q2過"] = False
                            r["樣本少"] = "、".join(nm for nm, nn in (("洗盤", sw["n"]), ("出貨", sd["n"])) if nn < 30)
                            for nm, sub in (("洗盤", w), ("出貨", d)):
                                for vv in (f"vsEW{H}", f"vs0050_{H}", f"Xreal{H}"):
                                    r[f"{nm}_{vv}"] = float(sub[vv].mean()) if len(sub) and vv in sub else np.nan
                            rows.append(r)
    C = pd.DataFrame(rows); C.to_csv(os.path.join(OUT, "cells.csv"), index=False, float_format="%.6g")
    J = {}
    for H in HS:
        for q, need in (("Q1", "洗盤"), ("Q2", "both"), ("Q3", "出貨")):
            per = {}
            for seg in ("探索", "確認", "早年"):
                x = C[(C["段"] == seg) & (C["H"] == H)]
                suff = (x["洗盤_n"] >= 30) & (x["出貨_n"] >= 30) if need == "both" else (x[f"{need}_n"] >= 30)
                npass = int(x[f"{q}過"].sum()); npass_s = int((x[f"{q}過"] & suff).sum()); nsuff = int(suff.sum())
                per[seg] = {"通過格（全）": npass, "足樣本格": nsuff, "足樣本中通過": npass_s, "主版過半": bool(nsuff > 0 and npass_s > nsuff / 2),
                            "全格版 ≥9／16": bool(npass >= 9)}
            main_ok = per["探索"]["主版過半"] and per["確認"]["主版過半"]
            alt_ok = per["探索"]["全格版 ≥9／16"] and per["確認"]["全格版 ≥9／16"]
            J[f"{q}_H{H}"] = {**per, "成立（主版）": main_ok, "成立（全格版）": alt_ok, "早年同向": per["早年"]["主版過半"]}
    S["判定"] = J
    # ── 描述
    dsc = {}
    for seg in ("探索", "確認", "早年"):
        k_ = K[K["段"] == seg]
        dsc[seg] = {"各組事件數（16 格合計）": k_["組"].value_counts().to_dict(),
                    "每年事件數（16 格合計）": k_.groupby(k_["月"].str[:4]).size().to_dict(),
                    "逐條 像洗盤−像出貨 X20 差（16 格合計）": {c_: float(k_.loc[k_[c_] == 1, "X20"].mean() - k_.loc[k_[c_] == -1, "X20"].mean()) for c_ in ("位置", "量能", "走勢", "反彈")},
                    "事後創前高比例": {gname: float(k_.loc[k_["組"] == gname, "事後創前高"].mean()) if (k_["組"] == gname).any() else None for gname in ("洗盤", "出貨", "混合")},
                    "剔除": E[(E["段"] == seg) & E["去重"]]["狀態"].value_counts().to_dict()}
        nd = E[(E["段"] == seg) & ~E["去重"] & (E["狀態"] == "保留")]
        dsc[seg]["不去重版 Q1 H20 洗盤 X−成本 平均"] = float(nd.loc[nd["組"] == "洗盤", "X20"].mean() - COST) if (nd["組"] == "洗盤").any() else None
    S["描述"] = dsc
    S["先驗（登錄 §五）"] = {"①Q1 洗盤組可買：否": not any(J[f"Q1_H{H}"]["成立（主版）"] for H in HS),
                         "②Q2 分得出：測不出": not any(J[f"Q2_H{H}"]["成立（主版）"] for H in HS),
                         "③Q3 出貨組該賣：否": not any(J[f"Q3_H{H}"]["成立（主版）"] for H in HS)}
    S["耗時s"] = round(time.time() - T0)
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    set_v2(False)
    log(f"[完] {time.time() - T0:.0f}s")


# ═════════════ 查核（⛔ 不呼叫 find_events／conds／events_one／baselines）═════════════
def check(a):
    out = {"時間": f"{pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）"}
    set_v2(True); RR.use_snapshot()
    E = pd.read_csv(os.path.join(OUT, "events.csv.gz"), dtype={"sid": str})
    cal = D.load_calendar(); n = len(cal)
    stocks = pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str); mk = stocks.set_index("stock_id")["market"].to_dict()
    rng = np.random.default_rng(5)
    sids = sorted(set(E[E["段"] != "早年"]["sid"])); pick = [sids[i] for i in rng.choice(len(sids), size=min(25, len(sids)), replace=False)]
    bad = 0; tot = 0; ex = []
    for s in pick:
        st = D.load_stock(s, mk.get(s, "twse"), cal); c = st.df["close"].to_numpy(float)
        raw = pd.read_csv(os.path.join(D.DATA, "stocks", s + ".csv"), dtype={"date": str}, usecols=["date", "volume"]).drop_duplicates("date")
        raw["date"] = pd.to_datetime(raw["date"]); v = pd.to_numeric(raw.set_index("date").reindex(cal)["volume"], errors="coerce").to_numpy(float)
        bars = [i for i in range(n) if np.isfinite(c[i]) and np.isfinite(v[i])]
        cb = [c[i] for i in bars]; vb = [v[i] for i in bars]
        for U in (0.20,):
            for Dd in (0.08, 0.15):
                # 逐日狀態機（另一種寫法）：去重主版
                evs = []; i = 60; last = -10 ** 9
                while i < len(cb):
                    if i <= last + 60:
                        i += 1; continue
                    win = cb[i - 59:i + 1]; P = i - 59 + win.index(max(win))
                    if P >= 60 and cb[P] / cb[P - 60] - 1 >= U and cb[i] <= cb[P] * (1 - Dd):
                        if P < 249:
                            i += 1; continue
                        L = min(range(P + 1, i + 1), key=lambda q: (cb[q], q)); T = None
                        for k in range(i + 1, min(i + 31, len(cb))):
                            if cb[k] >= cb[L] + (cb[P] - cb[L]) / 3:
                                T = k; break
                            if cb[k] < cb[L]:
                                L = k
                        if T is None:
                            i = i + 31; continue
                        evs.append((P, L, T)); last = T; i = T + 1; continue
                    i += 1
                for (P, L, T) in evs:
                    tc = bars[T]
                    for Pthr in (0.50, 1.00):
                        for sup in ("MA60", "回撤50%"):
                            pos = cb[P] / min(cb[P - 249:P + 1]) - 1
                            c1 = 1 if pos < Pthr else -1
                            vr = np.mean(vb[P - 59:P + 1]); vp = np.mean(vb[P + 1:L + 1]); vbb = np.mean(vb[L + 1:T + 1])
                            w2 = vr > 0 and vp / vr < 0.8
                            d2 = any(np.mean(vb[q - 20:q]) > 0 and vb[q] >= 2 * np.mean(vb[q - 20:q]) and cb[q] / cb[q - 1] - 1 <= 0.005 for q in range(max(P - 10, 20), min(P + 10, T) + 1))
                            c2 = int(w2) - int(d2)
                            lvl = np.mean(cb[T - 59:T + 1]) if sup == "MA60" else cb[P - 60] + 0.5 * (cb[P] - cb[P - 60])
                            c3 = 1 if cb[L] >= lvl else -1
                            c4 = int(vbb > vp) - int(vbb < vp)
                            ww = [c1 == 1, w2, c3 == 1, vbb > vp]; dd = [c1 == -1, d2, c3 == -1, vbb < vp]
                            grp = "洗盤" if all(ww) else ("出貨" if sum(dd) >= 3 else "混合")
                            hit = E[(E["段"] != "早年") & (E["sid"] == s) & (E["U"] == U) & (E["D"] == Dd) & (E["去重"]) & (E["P"] == Pthr) & (E["支撐"] == sup) & (E["T"] == tc)]
                            seg_ok = any(int(cal.searchsorted(pd.Timestamp(x0))) <= tc + 1 <= int(cal.searchsorted(pd.Timestamp(x1))) for x0, x1 in SEG.values())
                            if not seg_ok:
                                continue
                            tot += 1
                            if len(hit) != 1 or hit.iloc[0]["組"] != grp or [int(hit.iloc[0][k]) for k in ("位置", "量能", "走勢", "反彈")] != [c1, c2, c3, c4]:
                                bad += 1; ex.append((s, U, Dd, Pthr, sup, str(cal[tc].date())))
    out["① 事件與四條（抽 25 檔、U20%、D 兩值、主快照兩段）"] = {"比對": tot, "不同": bad, "例": ex[:5]}
    # ② 判定重算
    C = pd.read_csv(os.path.join(OUT, "cells.csv")); S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    mism = 0
    for H in HS:
        for q, need in (("Q1", "洗盤"), ("Q2", "both"), ("Q3", "出貨")):
            for seg in ("探索", "確認", "早年"):
                x = C[(C["段"] == seg) & (C["H"] == H)]
                suff = (x["洗盤_n"] >= 30) & (x["出貨_n"] >= 30) if need == "both" else (x[f"{need}_n"] >= 30)
                ns = int(suff.sum()); ps_ = int((x[f"{q}過"] & suff).sum())
                mism += int((ns > 0 and ps_ > ns / 2) != S["判定"][f"{q}_H{H}"][seg]["主版過半"])
    out["② 過半判定由 cells.csv 重算＝summary"] = {"不同": mism}
    ok = bad == 0 and tot > 0 and mism == 0
    out["結論"] = "✅ 全過（0 不同）" if ok else "⛔ 有不同"
    set_v2(False)
    json.dump(out, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("mode", nargs="?", default="body", choices=["body", "page"])
    ap.add_argument("--procs", type=int, default=4); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if a.check:
        return check(a)
    if a.mode == "page":
        from backtest import researchWashDist_page as P
        return P.main()
    body(a)


if __name__ == "__main__":
    main()
