# -*- coding: utf-8 -*-
"""稽核 ② 4（seq3 §二 第 3 列、§七之六；裁定 seq257 順 5）：型態全量「上升三角往上突破（S06）」樣本外＋補 5／10 日＋CI 下緣對成本。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchAudit2_4.py [--procs 2]
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchAudit2_4_check.py

原件：researchPatAll.py（b0e44526b8；可執行層 a216539810）。S06 H20 d×X̄ ＋1.19%〔+0.66%, +1.72%〕Bonferroni 也不含 0；H60 ＋1.51%（樣本中等）。
問題：K1 180 格挑出、無樣本外；K2 只 20／60；K3 只比點估計。
═══ 照原件、⛔ 不改 ═══
  偵測器 patterns_all（只呼叫 S06 那一段：detect_lines ＋ detect_all 同一條去重；主窗逐列驗 ＝ 原件事件檔）；
  分類 ＝ researchPatAll_freq.classify 同式（T ∈ [w0, w1−20]、20 日合併、[first, T＋H] 硬斷點、T＋1 停牌／開盤漲停／跌停剔除）；
  R ＝ ffill 還原收盤(T＋H) ÷ 還原開盤(T＋1) − 1；對照 ＝ 原件 C3（first 當天全 gate3 的 r60 十分位同格、T 有效、T＋1 可成交、T 當天無原始 S06、
  [first, T＋H] 無硬斷點、R 可算；自己不算）＝ researchPatAll.s_pool／s_one；判定量 dX ＝ X（d＝＋1）；統計 ＝ researchPatAll.cell_stats
═══ 本件新增（⭐ 開跑前寫死；本線讀法）═══
  H ∈ {5, 10, 20, 60}；H5／H10 的事件集合與 H20 同一批 T（T ≤ w1−20，原件分類同式），CI 以曆月分群（同 H20）
  三個資料段：
    主窗     main 快照 edc6f8002f，窗 2017-03-02～2026-08-24（原件）
    早年甲   早年版面 ~/earlydata/3edc0e2206/main（2004-02-11～2014-12-31，只上市；還原＝官方除權息；R1 母體＝當時上市）⇒ 窗 ＝ 版面全段
    早年乙   main 快照，窗 2015-01-05～2017-03-01（主窗之前；上市＋上櫃）
    ⇒ 「早年段 2004～2016」＝ 早年甲＋早年乙各自算、另報合併（兩段各自配對、各自分群；合併只把逐筆 dX 併在一起、分群用曆月）
  ⚠ 早年甲只上市（早年版面沒有上櫃）；早年段起點前 60 根無 r60 ⇒ 最早的事件配不到對照（件數必報）
  K3：可執行層原件的讀法 ＋ 本件加「95% CI 下緣 ＞ 0.585%」（稽核要求）；每格報是否成立
  「樣本外過」＝ 早年段合併 H20 結果②（照原件判法）；另報 H60、H5、H10（描述，⛔ 不增 N）
  假訊號臂：不跑（原件 S06 H20 為 1／30）
輸出 backtest/resultsAudit2/4/
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchPatAll as PAT                      # ⭐ 原件（s_pool、s_one、dec_matrix、cell_stats、verdict）；import 時 D.DATA ＝ main 快照
RPF, H2, D, TR, UG, PA = PAT.RPF, PAT.H2, PAT.D, PAT.TR, PAT.UG, PAT.PA
import multiprocessing as mp

OUT = "backtest/resultsAudit2/4"
VID = "S06"
HS = (5, 10, 20, 60)
MERGE = 20
COST = 0.00585
SNAP = H2.H2D
EARLY = os.path.expanduser("~/earlydata/3edc0e2206/main/data")
SOURCES = [("主窗", SNAP, "2017-03-02", "2026-08-24"), ("早年甲", EARLY, None, "2014-12-31"), ("早年乙", SNAP, "2015-01-05", "2017-03-01")]
_G: dict = {}


def s06(o, h, l, c, v):
    """detect_all 的 S06 那一段（同一條去重）＋ detect_calendar 的日曆換算。"""
    bars = np.flatnonzero(np.isfinite(c))
    cb = c[bars]; hb = np.asarray(h, float)[bars]; lb = np.asarray(l, float)[bars]
    r60 = PA._rN(cb, PA.R60)
    S = PA.detect_lines(hb, lb, cb, r60)
    ev, seen = [], set()
    for e in sorted(set(S[VID])):
        if e[0] not in seen:
            seen.add(e[0]); ev.append(e)
    T = np.array([e[0] for e in ev], np.int64); f = np.array([e[1] for e in ev], np.int64)
    return (bars[T] if len(T) else T), (bars[f] if len(f) else f), (r60[f] if len(f) else np.zeros(0))


def _init(cal, w0, w1, off, data):
    D.DATA = data
    _G.update(cal=cal, w0=w0, w1=w1, off=off)


def load_one(args):
    sid, market = args
    cal, w0, w1, off = _G["cal"], _G["w0"], _G["w1"], _G["off"]; n = len(cal)
    st = D.load_stock(sid, market, cal)
    if st is None:
        return None
    df = st.df
    o, h, l, c, v = (df[k].to_numpy(float) for k in ("open", "high", "low", "close", "volume"))
    valid = np.isfinite(c); bars = np.flatnonzero(valid)
    if len(bars) == 0:
        return None
    T, first, r60f = s06(o, h, l, c, v)
    pb = np.zeros(n, bool)
    for b_ in D.breakpoints(df, st.event_dates):
        if b_["rule"] in ("price", "price+gap"):
            pb[b_["pos"]] = True
    tb = TR.one(sid, cal)
    ds = TR.delist_status({sid: tb}, cal, official=off).get(sid)
    delisted = ds is not None and ds["status"].startswith("delisted")
    g5 = RPF.MF._g5(valid, upto=ds["last"]) if delisted else RPF.MF._g5(valid)
    S = {"cs_pb": np.cumsum(pb).astype(np.int32), "cs_g5": np.cumsum(g5).astype(np.int32)}
    # 分類（researchPatAll_freq.classify 同式；H 換成 HS）
    m = (T >= w0) & (T <= w1 - 20)
    Tm, fm, rm = T[m], first[m], r60f[m]
    merged = np.zeros(len(Tm), bool); t0 = -10 ** 9
    for i, t in enumerate(Tm):
        if t0 < t <= t0 + MERGE:
            merged[i] = True
        else:
            t0 = t
    kept = {}; acct = {}
    for H in HS:
        s = []
        for i, t in enumerate(Tm):
            if t + H > w1:
                s.append("窗外"); continue
            brk = H2.brk(S, int(fm[i]), int(t) + H)
            halt = (not bool(tb["trd"][t + 1])) or (not np.isfinite(o[t + 1]))
            why = "剔除_硬斷點" if brk else ("剔除_T+1停牌" if halt else ("剔除_T+1開盤漲停" if tb["up_o"][t + 1] else ("剔除_T+1開盤跌停" if tb["dn_o"][t + 1] else None)))
            s.append("合併掉" if merged[i] else (why or "保留"))
        s = np.array(s); acct[H] = dict(Counter(s.tolist()))
        kept[H] = (Tm[s == "保留"].astype(np.int32), fm[s == "保留"].astype(np.int32))
    cff = pd.Series(c).ffill().to_numpy()
    okO1 = np.zeros(n, bool); okO1[:-1] = valid[1:] & np.isfinite(o[1:]) & (np.nan_to_num(o[1:]) > 0)
    G = {}
    for H in HS:
        g = np.full(n, np.nan)
        with np.errstate(invalid="ignore", divide="ignore"):
            g[:n - H] = np.where(okO1[:n - H], cff[H:] / o[1:n - H + 1] - 1.0, np.nan)
        G[H] = g
    trd1 = np.zeros(n, bool)
    trd1[:-1] = tb["trd"][1:] & np.isfinite(o[1:]) & ~tb["up_o"][1:] & ~tb["dn_o"][1:]
    j = np.arange(len(bars)); cb = c[bars]; A60 = np.full(n, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        jj = j[j >= 61]; A60[bars[jj]] = cb[jj - 1] / cb[jj - 61] - 1.0
    mism = int(np.sum(~((A60[fm] == rm) | (np.isnan(A60[fm]) & np.isnan(rm)))))
    raw = T[(T >= w0) & (T <= w1)].astype(np.int32)
    ev_rows = [(sid, market, int(t), int(f_)) for t, f_ in zip(Tm, fm)]
    return {"sid": sid, "market": market, "valid": valid, "trd1": trd1, "G": G, "A60": A60, "cs_pb": S["cs_pb"], "cs_g5": S["cs_g5"],
            "raw": raw, "kept": kept, "acct": acct, "mism": mism, "ev": ev_rows}


def run_source(name, data, W0, W1, procs, log, lim=None):
    D.DATA = data
    cal = D.load_calendar(); n = len(cal)
    w0 = int(cal.searchsorted(pd.Timestamp(W0))) if W0 else 0
    w1 = int(cal.searchsorted(pd.Timestamp(W1)))
    if str(cal[w1].date()) != W1:
        w1 -= 1
    stocks = pd.read_csv(os.path.join(data, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(stocks)
    if lim:
        U = U.head(lim)
    off = TR.load_official()
    sids, mkts = list(U["stock_id"]), list(U["market"]); S_ = len(sids)
    VALID = np.zeros((n, S_), bool); TRD1 = np.zeros((n, S_), bool); A60 = np.full((n, S_), np.nan)
    G = {H: np.full((n, S_), np.nan) for H in HS}
    CSPB = np.zeros((n, S_), np.int32); CSG5 = np.zeros((n, S_), np.int32)
    rawI, rawT = [], []; KE = {H: [] for H in HS}; ACCT = {H: Counter() for H in HS}; mism = 0; EV = []
    t0 = time.time()
    with mp.get_context("fork").Pool(procs, initializer=_init, initargs=(cal, w0, w1, off, data)) as pool:
        for jx, r in enumerate(pool.imap(load_one, list(zip(sids, mkts)), chunksize=8)):
            if r is None:
                continue
            VALID[:, jx] = r["valid"]; TRD1[:, jx] = r["trd1"]; A60[:, jx] = r["A60"]; CSPB[:, jx] = r["cs_pb"]; CSG5[:, jx] = r["cs_g5"]
            for H in HS:
                G[H][:, jx] = r["G"][H]; ACCT[H].update(r["acct"].get(H, {}))
                T_, f_ = r["kept"][H]
                if len(T_):
                    KE[H].append((np.full(len(T_), jx), T_, f_))
            if len(r["raw"]):
                rawI.append(np.full(len(r["raw"]), jx)); rawT.append(r["raw"])
            mism += r["mism"]; EV += r["ev"]
    log(f"[{name}] 讀檔＋偵測 {S_:,} 檔｜窗 {cal[w0].date()}～{cal[w1].date()}｜{time.time() - t0:.0f}s｜錨點 r60 不一致 {mism}")
    DECA60 = PAT.dec_matrix(A60, VALID & np.isfinite(A60), range(0, w1 + 1))
    RAWD = np.zeros((n, S_), bool)
    if rawI:
        RAWD[np.concatenate(rawT), np.concatenate(rawI)] = True
    moni = np.asarray(cal.year * 12 + cal.month) - (cal[w0].year * 12 + cal[w0].month)
    Wd = {"w0": w0, "w1": w1, "VALID": VALID, "TRD1": TRD1, "G": G, "CSPB": CSPB, "CSG5": CSG5}
    out = {"窗": [str(cal[w0].date()), str(cal[w1].date())], "gate3 檔數": S_, "帳": {H: dict(ACCT[H]) for H in HS}, "錨點不一致": mism}
    rows = []
    for H in HS:
        if not KE[H]:
            out[f"H{H}"] = {"n": 0}; continue
        idx = np.concatenate([a for a, _, _ in KE[H]]); T = np.concatenate([b for _, b, _ in KE[H]]).astype(np.int64)
        fst = np.concatenate([c_ for _, _, c_ in KE[H]]).astype(np.int64)
        sp = PAT.s_pool(Wd, H, RAWD)
        g = sp["G"][T - sp["r0"], idx]
        ctrl = np.full(len(T), np.nan); cc = np.zeros(len(T), np.int64)
        for q in range(len(T)):
            ctrl[q], cc[q] = PAT.s_one(Wd, sp, DECA60, H, int(idx[q]), int(T[q]), int(fst[q]))
        X = g - ctrl; ok = np.isfinite(X)
        hh = 20 if H in (5, 10) else H                                   # H5／H10 分群同 H20（曆月）
        cs = PAT.cell_stats(X[ok], T[ok], hh, w0, moni)
        cs.update({"保留": int(len(T)), "配對剔除": dict(Counter(np.where(cc < 0, "錨點量不可算", "配對格無對照股")[~ok].tolist())),
                   "對照數中位": float(np.median(cc[ok])) if ok.any() else None})
        if "lo" in cs:
            cs["95%CI下緣 ＞ 0.585%"] = bool(cs["lo"] > COST); cs["點估計 ＞ 0.585%"] = bool(cs["dX̄"] > COST)
        out[f"H{H}"] = cs
        rows.append(pd.DataFrame({"段": name, "H": H, "sid": np.array(sids)[idx], "market": np.array(mkts)[idx], "T": [str(cal[t].date()) for t in T],
                                  "first": [str(cal[f].date()) for f in fst], "R": g, "對照平均": ctrl, "對照數": cc, "X": X,
                                  "月": [str(cal[t])[:7] for t in T]}))
        log(f"[{name} H{H}] n {cs.get('n')}｜dX̄ {cs.get('dX̄', float('nan')):+.3%} [{cs.get('lo', float('nan')):+.3%}, {cs.get('hi', float('nan')):+.3%}]｜"
            f"{cs.get('出口')} {cs.get('結果')}｜剔除 {cs['配對剔除']}")
    evdf = pd.DataFrame(EV, columns=["sid", "market", "T", "first"])
    evdf["T"] = [str(cal[t].date()) for t in evdf["T"]]; evdf["first"] = [str(cal[f].date()) for f in evdf["first"]]
    return out, (pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()), evdf


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); ap.add_argument("--limit", type=int, default=None); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    log(f"===== researchAudit2_4（上升三角往上突破 S06：樣本外＋5／10 日）{pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）=====")
    S = {"原件": "researchPatAll.py b0e44526b8／a216539810", "閘": {}}
    ALL = []; RAWS = []
    for name, data, W0, W1 in SOURCES:
        res, ev, raw_ev = run_source(name, data, W0, W1, a.procs, log, a.limit)
        S[name] = res; ALL.append(ev); RAWS.append(raw_ev.assign(段=name))
        if name == "主窗" and not a.limit:
            ref = pd.read_csv(os.path.join("backtest/resultsPatAll", "events_S06_上升三角_向上.csv.gz"), dtype={"sid": str})
            mine = raw_ev.sort_values(["sid", "T"]).reset_index(drop=True); rf = ref[["sid", "market", "T", "first"]].sort_values(["sid", "T"]).reset_index(drop=True)
            S["閘"]["主窗 S06 事件（sid、T、first）＝ 原件事件檔"] = {"本件": len(mine), "原件": len(rf), "相同": bool(mine.equals(rf))}
            be = pd.read_csv("backtest/resultsPatAll/body/events/events_S06.csv.gz", dtype={"sid": str}, float_precision="round_trip")
            for H in (20, 60):
                x = ev[ev["H"] == H].sort_values(["sid", "T"]).reset_index(drop=True)
                y = be[be["H"] == H].sort_values(["sid", "T"]).reset_index(drop=True)
                same = len(x) == len(y) and (x["sid"].values == y["sid"].values).all() and (x["T"].values == y["T"].values).all()
                nd = int(sum(repr(float(p)) != repr(float(q)) for p, q in zip(x["X"], y["X"]) if not (np.isnan(p) and np.isnan(q)))) if same else None
                S["閘"][f"主窗 H{H} 逐筆 X ＝ 原件 events_S06（逐位元）"] = {"筆數": [len(x), len(y)], "同一批": bool(same), "不逐位元": nd}
            log(f"[閘] {S['閘']}")
            if not all((v.get("相同", True) and v.get("不逐位元", 0) == 0) for v in S["閘"].values()):
                json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
                raise SystemExit("⛔ 閘不過")
    pd.concat(RAWS, ignore_index=True).to_csv(os.path.join(OUT, "raw_events.csv.gz"), index=False)   # 分類窗內全部原始偵測（任何狀態；查核的對照排除用）
    E = pd.concat(ALL, ignore_index=True)
    E.to_csv(os.path.join(OUT, "events.csv.gz"), index=False, float_format="%.17g")
    # 早年段合併（甲＋乙）：逐筆併、曆月分群
    comb = {}
    for H in HS:
        x = E[(E["段"].isin(["早年甲", "早年乙"])) & (E["H"] == H) & E["X"].notna()]
        mon = x["月"].to_numpy()
        cs = PAT.R11.cl_stats(x["X"].to_numpy(float), mon)
        ne = int(min(len(x), cs["months"]))
        ex, rs = PAT.verdict(cs["mean"], cs["se"], ne)
        comb[f"H{H}"] = {"n": int(len(x)), "dX̄": float(cs["mean"]), "lo": float(cs["lo"]), "hi": float(cs["hi"]), "n_eff": ne, "出口": ex, "結果": rs,
                         "95%CI下緣 ＞ 0.585%": bool(cs["lo"] > COST), "上市": int((x["market"] == "twse").sum()), "上櫃": int((x["market"] == "tpex").sum())}
        log(f"[早年合併 H{H}] n {len(x)}｜dX̄ {cs['mean']:+.3%} [{cs['lo']:+.3%}, {cs['hi']:+.3%}]｜{ex} {rs}")
    S["早年段合併（甲＋乙）"] = comb
    S["樣本外過（早年段合併 H20 結果②）"] = comb["H20"]["結果"] == "結果②"
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=lambda o_: o_.item() if hasattr(o_, "item") else str(o_))
    log(f"[完] {time.time() - T0:.0f}s")


if __name__ == "__main__":
    main()
