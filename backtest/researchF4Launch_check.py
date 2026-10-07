# -*- coding: utf-8 -*-
"""researchF4Launch 抽樣查核（獨立寫法；⛔ 不呼叫 researchF4Launch 的函式，只讀它的輸出 ~/f4lwork、backtest/resultsF4Launch）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchF4Launch_check

 ① F4：抽 40 檔（旗表內；帶過 F4 的 30 ＋ 隨機 10，default_rng(20261011)），pandas 從 fin_hist／filing_dates CSV 自算單季 EPS、重編遮罩、公布日、月底判定
    ⇒ 不遮重編版逐月比 flags_main.npz（F4、F4_ok）；遮重編版用 merge_asof（嚴格早於 d）對到觸發日 ⇒ 比 signals_all.pkl 的 f4、f4ok
 ② 訊號：抽 60 檔（default_rng(20261012)），逐日迴圈自算 k（Q 表逐特徵）、2026 營收 15 日修正、dlo_60 觸發（60 根去重）、EL、pit
    ⇒ 比 signals_all.pkl 該檔全部列（(d, x) 集合、k、f4、f4ok、el、pit）
 ③ E1：抽 30 筆（無壞根、錨回看 250 根全有值；default_rng(20261013)），逐日 T 直接呼叫 surge_flow_daily.replay（W1／W2 由本檔逐根自算後換進 signals_for；
    stock_ctx 用 replay 原函式、price_dir ＝ 接合版面）⇒ 由 replay 每天的「階段／該做什麼」得出該賣到幾成 ⇒ 下單、執行（base：次一有效開盤；現實版：再避開停牌與一字跌停、均價、衝擊）
    ⇒ 比 exits.pkl 的 E1b、E1r（x30、x70、px30、px70、g）
 ④ E2 與壞根：抽 200 筆（default_rng(20261014)），逐日迴圈自算回落 30%、壞根截（幽靈還原、價格斷點自算）、base／現實版執行與 g ⇒ 比 exits.pkl 的 E2b、E2r
 ⑤ 組合：挑中格 2 顆種子（0、1；base、現實版），用實體陣列（numpy 合成收盤，⛔ 不用本體的 Syn）重跑引擎 ⇒ 年化、回落逐位元比 seeds.csv.gz；
    窗年化、回落用自寫公式從權益重算；逐筆賣出價 ÷ 買進價 − 1 ＝ 訊號 g（停止交易強制出場的筆除外）
輸出 backtest/resultsF4Launch/check.json、run_check.log
"""
from __future__ import annotations

import glob
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import universe_gate as UG
from backtest import research11 as R
from backtest import surge_flow_daily as SFL
from backtest import tradability as TR

UG.set_gate_v2(True)
ST = os.path.expanduser("~/evtdata/stitch_950ad26e12_b53f5540a8/data")
S5W = os.path.expanduser("~/s5work")
MAIN = os.path.expanduser("~/h2data/mine_796d94c9dafd/data")
S5MAIN = os.path.expanduser("~/h2data/surge_b53f5540a8ad/data")
FLAGS = os.path.expanduser("~/minework/flags_main.npz")
WORK = os.path.expanduser("~/f4lwork")
OUT = "backtest/resultsF4Launch"
FEATS = [("dlo_5", 1), ("dlo_10", 1), ("ma_5", 1), ("r_5", 1), ("turn_60", 5), ("r_120", 5), ("musage", 5), ("d_px", 1), ("d_bull", 2), ("d_att60", 3),
         ("d_R2a", 2), ("d_eps", 2), ("d_revhi", 2), ("d_lu20", 4)]
XS = (0.10, 0.20, 0.30, 0.50)
COST_B = 0.00585; COST_R = 0.00585 + 0.006; Q = 50_000
T0 = time.time(); LOGF = None


def log(m):
    m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True)
    with open(os.path.join(OUT, "run_check.log"), "a", encoding="utf-8") as f:
        f.write(m + "\n")


# ═════════════ ① F4 ═════════════
def own_f4(sids, calm, me, restated_mask):
    fs = sorted(glob.glob(os.path.join(MAIN, "mops", "fin_hist", "*.csv")))
    F = pd.concat([pd.read_csv(f, dtype={"stock_id": str, "period": str}, usecols=["stock_id", "period", "eps_q", "eps_ytd"]) for f in fs])
    F = F[F["stock_id"].isin(sids)].drop_duplicates(["stock_id", "period"], keep="last").copy()
    F["y"] = F["period"].str[:4].astype(int); F["q"] = F["period"].str[-1].astype(int)
    F["ytd"] = pd.to_numeric(F["eps_ytd"], errors="coerce"); F["eq"] = pd.to_numeric(F["eps_q"], errors="coerce")
    fd = pd.read_csv(os.path.join(MAIN, "meta", "filing_dates.csv"), dtype=str)
    if restated_mask:
        rs = fd[fd["doc_type"].str.contains("重編", na=False)][["stock_id", "year", "season"]].drop_duplicates()
        rs = set(zip(rs["stock_id"], rs["year"].astype(int), rs["season"].astype(int)))
        m = [(a, b, c) in rs for a, b, c in zip(F["stock_id"], F["y"], F["q"])]
        F.loc[m, ["ytd", "eq"]] = np.nan
    fd["dt"] = pd.to_datetime(fd["uploaded_at"].astype(str).str[:10], errors="coerce")
    fd = fd.dropna(subset=["dt"])
    first = fd.groupby(["stock_id", "year", "season"])["dt"].min()
    first.index = [(a, int(b), int(c)) for a, b, c in first.index]
    first = first.to_dict()
    mepos = calm.get_indexer(me)
    out = {}
    for sid in sids:
        g = F[F["stock_id"] == sid].sort_values(["y", "q"])
        ytd = {(y, q): v for y, q, v in zip(g["y"], g["q"], g["ytd"])}
        sing = {}; ap = {}
        for y, q, v, vq in zip(g["y"], g["q"], g["ytd"], g["eq"]):
            if q == 1:
                e = v
            else:
                pv = ytd.get((y, q - 1), np.nan)
                e = v - pv if (np.isfinite(v) and np.isfinite(pv)) else np.nan
            if not np.isfinite(e) and np.isfinite(vq):
                e = vq
            o = y * 4 + q - 1; sing[o] = e
            ts = first.get((sid, y, q))
            if ts is not None:
                ap[o] = int(calm.searchsorted(ts, side="right"))
            else:
                dl = pd.Timestamp(y + 1, 3, 31) if q == 4 else pd.Timestamp(y, *{1: (5, 15), 2: (8, 14), 3: (11, 14)}[q])
                ap[o] = int(calm.searchsorted(dl, side="right")) + 5
        F4 = np.zeros(len(me), bool); OK = np.zeros(len(me), bool)
        for i, m in enumerate(mepos):
            av = [o for o, a in ap.items() if a <= m]
            if not av:
                continue
            top = max(av)
            e8 = np.array([sing.get(top - j, np.nan) for j in range(8)], float)
            a_ok = bool(np.isfinite(e8[:4]).all()); b_ok = bool(np.isfinite(e8).all())
            OK[i] = a_ok or b_ok
            F4[i] = (a_ok and e8[:4].sum() < 0 and e8[0] < 0) or (b_ok and int((e8 < 0).sum()) >= 6)
        out[sid] = (F4, OK)
    return out


# ═════════════ 共用：每檔自算陣列 ═════════════
def own_stock(sid, mk, cal, Qm, Fm, FX, s):
    D.DATA = ST
    st = D.load_stock(sid, mk, cal); df = st.df; n = len(cal)
    c0 = df["close"].to_numpy(float); o = df["open"].to_numpy(float); h = df["high"].to_numpy(float); l = df["low"].to_numpy(float)
    bar = np.isfinite(c0); c = pd.Series(c0).ffill().to_numpy()
    idx = np.flatnonzero(bar)
    HI20 = np.zeros(n, bool); NEAR = np.zeros(n, bool)
    for j, b in enumerate(idx):
        if j >= 20:
            HI20[b] = c0[b] > max(c0[idx[j - 20:j]])
        if j >= 19:
            NEAR[b] = c0[b] >= 0.9 * max(c0[idx[j - 19:j + 1]])
    att = np.asarray(Qm[FX["att_10"], s]); lu5 = np.asarray(Qm[FX["lu_5"], s]); r5 = np.asarray(Qm[FX["r_5"], s]); d60 = np.asarray(Fm[FX["disp_60"], s])
    w1 = HI20 & (att == 5) & ((lu5 == 5) | (r5 == 5)) & (d60 == 0) & bar
    dp = pd.read_csv(os.path.join(S5MAIN, "meta", "disposal.csv"), dtype={"stock_id": str}, usecols=["stock_id", "start_date", "end_date"])
    dp = dp[dp["stock_id"] == sid]
    iv = [(int(cal.searchsorted(pd.Timestamp(a))), int(cal.searchsorted(pd.Timestamp(b), side="right")) - 1) for a, b in zip(dp["start_date"], dp["end_date"])]
    starts = [a for a, b in iv]
    w2a = np.zeros(n, bool); w2b = np.zeros(n, bool)
    for a, b in iv:
        if 0 <= a < n and any(0 < a - x <= 60 for x in starts if x != a) and NEAR[a] and bar[a]:
            w2a[a] = True
        if 0 <= b + 1 < n and NEAR[b + 1] and bar[b + 1]:
            w2b[b + 1] = True
    # 現實版：均價、一字跌停、衝擊
    avg = (o + h + l + c0) / 4
    raw = pd.read_csv(os.path.join(ST, "stocks", sid + ".csv"), dtype={"date": str}, usecols=["date", "open", "high", "close"]).drop_duplicates("date")
    raw.index = pd.to_datetime(raw["date"]); raw = raw.reindex(cal)
    ro = pd.to_numeric(raw["open"], errors="coerce").to_numpy(float); rh = pd.to_numeric(raw["high"], errors="coerce").to_numpy(float)
    rc = pd.to_numeric(raw["close"], errors="coerce").to_numpy(float)
    tb = TR.one(sid, cal)
    lockdn = tb["dn_o"] & (rh == ro)
    trd = np.isfinite(np.where(rc > 0, rc, np.nan))
    amt = pd.to_numeric(df["amount"], errors="coerce").to_numpy(float)
    sig20 = np.full(n, np.nan); adv20 = np.full(n, np.nan)
    sdj = np.full(len(idx), np.nan); adj_ = np.full(len(idx), np.nan)
    for j in range(len(idx)):
        if j >= 20:
            cs_ = c0[idx[j - 20:j + 1]]; r_ = cs_[1:] / cs_[:-1] - 1; sdj[j] = np.std(r_, ddof=1)
        if j >= 19:
            adj_[j] = np.mean(amt[idx[j - 19:j + 1]])
    for t in range(1, n):
        j = int(np.searchsorted(idx, t - 1, side="right")) - 1
        if j >= 0:
            sig20[t] = sdj[j]; adv20[t] = adj_[j]
    imp = sig20 * np.sqrt(Q / adv20)
    # 壞根（幽靈還原、價格斷點）
    bad = set()
    adj = D.load_adj(sid)
    if adj is not None:
        for d, f in zip(adj["date"], adj["factor"].astype(float)):
            k = int(np.searchsorted(cal[idx], d))
            if 0 < k < len(idx) and np.isfinite(rc[idx[k]]) and np.isfinite(rc[idx[k - 1]]) and f > 0:
                rr = rc[idx[k]] / (rc[idx[k - 1]] * f)
                if rr < 0.895 or rr > 1.105:
                    bad.add(int(idx[k]))
    for b in D.breakpoints(df, st.event_dates):
        if b["rule"] in ("price", "price+gap"):
            k = int(np.searchsorted(idx, b["pos"]))
            if k < len(idx):
                bad.add(int(idx[k]))
    okb = bar & np.isfinite(o) & (o > 0)
    okr = okb & trd & ~lockdn & np.isfinite(avg) & (avg > 0)
    return {"c": c, "o": o, "avg": avg, "bar": bar, "okb": okb, "okr": okr, "w1": w1, "w2a": w2a, "w2b": w2b, "imp": imp, "bad": sorted(bad), "n": n, "idx": idx}


def nxt(ok, T):
    w = np.flatnonzero(ok[T + 1:])
    return T + 1 + int(w[0]) if len(w) else None


def realize(X, orders, e, bad_after, real):
    """下單 [(T, 舊, 新)] ⇒ 兩個子部位 (xpos, px, kind)。"""
    n = X["n"]; ok = X["okr"] if real else X["okb"]; P = X["avg"] if real else X["o"]
    parts = {}
    for T, f0, f1 in orders:
        x = nxt(ok, T)
        ks = (["p30"] if f0 < 0.299 else []) + (["p70"] if f1 > 0.999 else [])
        for k in ks:
            parts[k] = (n, X["c"][n - 1], "end") if x is None else (x, P[x], "open")
    for k in ("p30", "p70"):
        parts.setdefault(k, (n, X["c"][n - 1], "end"))
    if bad_after is not None:
        for k in ("p30", "p70"):
            x, p, kd = parts[k]
            tk = 2 * x + (1 if kd == "close" else 0) if kd != "end" else 2 * n
            if tk > 2 * bad_after + 1:
                pb = bad_after
                parts[k] = (pb, (X["avg"][pb] if (real and np.isfinite(X["avg"][pb])) else X["c"][pb]), "close")
    return parts


def gross(X, parts, e, real):
    if real:
        bp = X["avg"][e]; ii = X["imp"][e] if np.isfinite(X["imp"][e]) else 0.0
        num = 0.0
        for w, k in ((0.3, "p30"), (0.7, "p70")):
            x, p, kd = parts[k]
            io = 0.0 if kd == "end" else (X["imp"][x] if np.isfinite(X["imp"][x]) else 0.0)
            num += w * p * (1 - min(io, 0.99))
        return num / (bp * (1 + ii)) - 1
    bp = X["o"][e] if (np.isfinite(X["o"][e]) and X["o"][e] > 0) else X["c"][e]
    return (0.3 * parts["p30"][1] + 0.7 * parts["p70"][1]) / bp - 1


def cmp(errs, tag, mine, body, tol=1e-9):
    if isinstance(mine, (int, np.integer)) or isinstance(body, (int, np.integer)):
        if int(mine) != int(body):
            errs.append(f"{tag}：自算 {mine} 本體 {body}")
    elif not np.isclose(float(mine), float(body), rtol=tol, atol=1e-12, equal_nan=True):
        errs.append(f"{tag}：自算 {mine} 本體 {body}")


def main():
    os.makedirs(OUT, exist_ok=True)
    log(f"===== check {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）=====")
    errs = []; items = []
    uni = pd.read_csv(os.path.join(S5W, "uni.csv"), dtype=str)
    D.DATA = ST; cal = D.load_calendar(); n = len(cal)
    SG = pd.read_pickle(os.path.join(WORK, "signals_all.pkl")); EX = pd.read_pickle(os.path.join(WORK, "exits.pkl"))
    z = np.load(FLAGS); me = pd.to_datetime(z["me"]); fsids = z["sids"].tolist()
    D.DATA = MAIN; calm = D.load_calendar(); D.DATA = ST
    # ── ①
    rng = np.random.default_rng(20261011)
    hasf = [s for j, s in enumerate(fsids) if z["F4"][:, j].any()]
    pick1 = sorted(set(rng.choice(hasf, 30, replace=False).tolist()) | set(rng.choice(fsids, 10, replace=False).tolist()))
    U = own_f4(pick1, calm, me, False); P = own_f4(pick1, calm, me, True)
    nd = 0
    for sid in pick1:
        j = fsids.index(sid)
        nd += int((U[sid][0] != z["F4"][:, j]).sum() + (U[sid][1] != z["F4_ok"][:, j]).sum())
    if nd:
        errs.append(f"① 不遮重編 F4 與 flags_main 不同 {nd} 格")
    ref = pd.DataFrame({"m": me, "j": np.arange(len(me))})
    nrow = 0
    for sid in pick1:
        g = SG[SG["sid"] == sid]
        if not len(g):
            continue
        dd = pd.DataFrame({"d": cal[g["d"].to_numpy()], "i": np.arange(len(g))}).sort_values("d")
        mm_ = pd.merge_asof(dd, ref, left_on="d", right_on="m", allow_exact_matches=False).sort_values("i")
        mj = mm_["j"].to_numpy()
        f4 = np.array([bool(P[sid][0][int(x)]) if np.isfinite(x) else False for x in mj]); ok = np.array([bool(P[sid][1][int(x)]) if np.isfinite(x) else False for x in mj])
        nrow += len(g)
        if (f4 != g["f4"].to_numpy()).any() or (ok != g["f4ok"].to_numpy()).any():
            errs.append(f"① {sid} 觸發日 F4 不同 {int((f4 != g['f4'].to_numpy()).sum())} 列、可判不同 {int((ok != g['f4ok'].to_numpy()).sum())} 列")
    items.append(f"① F4 {len(pick1)} 檔 × {len(me)} 月（不遮重編比 flags_main）；觸發列 {nrow}（遮重編比訊號表）")
    log(f"[①] {items[-1]}｜錯 {len(errs)}")
    # ── ②
    fcol = json.load(open(os.path.join(S5W, "build.json"), encoding="utf-8"))["特徵欄"]; FX = {c: i for i, c in enumerate(fcol)}
    Qm = np.load(os.path.join(S5W, "Q.npy"), mmap_mode="r"); Fm = np.load(os.path.join(S5W, "F.npy"), mmap_mode="r")
    bar5 = np.load(os.path.join(S5W, "bar.npy"), mmap_mode="r")
    rng = np.random.default_rng(20261012)
    cand2 = sorted(set(SG["s"].astype(int)))
    pick2 = sorted(rng.choice(cand2, 60, replace=False).tolist())
    Uf2 = own_f4([uni.loc[s, "stock_id"] for s in pick2 if uni.loc[s, "stock_id"] in fsids], calm, me, True)
    e10s = []
    for m in range(1, 13):
        y2, m2 = (2026, m + 1) if m < 12 else (2027, 1)
        a = int(np.searchsorted(cal.values, np.datetime64(pd.Timestamp(y2, m2, 10)), side="right")); b = int(np.searchsorted(cal.values, np.datetime64(pd.Timestamp(y2, m2, 15)), side="right"))
        if a < n:
            e10s.append((a, min(b, n)))
    nsig = 0
    for s in pick2:
        sid = uni.loc[s, "stock_id"]; bar = np.asarray(bar5[s])
        Qr = {col: np.array(Qm[FX[col], s]) for col, _ in FEATS}
        for a, b in e10s:
            pb = np.flatnonzero(bar[:a])
            for col in ("d_R2a", "d_revhi"):
                v = Qr[col][pb[-1]] if len(pb) else 0
                for t in range(a, b):
                    if bar[t]:
                        Qr[col][t] = v
        k = np.zeros(n, int)
        for col, code in FEATS:
            k += (Qr[col] == code)
        dlo = np.asarray(Fm[FX["dlo_60"], s])
        bars = np.flatnonzero(bar)
        mine = {}
        for xi, x in enumerate(XS):
            last = -10 ** 9
            for i, t in enumerate(bars):
                if np.isfinite(dlo[t]) and dlo[t] >= x and i - last > 60:
                    mine[(int(t), xi)] = True; last = i
        dd = pd.DataFrame({"d": cal[[t for t, _ in mine]]}) if mine else pd.DataFrame({"d": pd.DatetimeIndex([])})
        g = SG[SG["s"] == s].set_index(["d", "xi"])
        mk = {(t, xi) for t, xi in mine if t + 1 <= n - 1}
        if mk != set(g.index):
            errs.append(f"② {sid} 觸發集合不同：只自算 {len(mk - set(g.index))}、只本體 {len(set(g.index) - mk)}")
            continue
        pit = UG.pit_valid(sid, cal, data=S5MAIN)
        jj = fsids.index(sid) if sid in fsids else None
        for (t, xi), r in g.iterrows():
            nsig += 1
            m_ = int(np.searchsorted(me.values, np.datetime64(cal[t]), side="left")) - 1
            f4 = bool(Uf2[sid][0][m_]) if (jj is not None and m_ >= 0) else False
            ok = bool(Uf2[sid][1][m_]) if (jj is not None and m_ >= 0) else False
            el = bool(z["EL"][m_, jj]) if (jj is not None and m_ >= 0) else False
            for nm, a_, b_ in (("k", int(k[t]), int(r["k"])), ("f4", f4, bool(r["f4"])), ("f4ok", ok, bool(r["f4ok"])), ("el", el, bool(r["el"])), ("pit", bool(pit[t]), bool(r["pit"]))):
                if a_ != b_:
                    errs.append(f"② {sid} d{t} x{xi} {nm}：自算 {a_} 本體 {b_}")
    items.append(f"② 訊號 {len(pick2)} 檔、{nsig} 列")
    log(f"[②] {items[-1]}｜錯 {len(errs)}")
    # ── ③ E1 replay
    rng = np.random.default_rng(20261013)
    EXo = EX.copy()
    fv = {}
    for s in set(EXo["s"].astype(int)):
        b = np.flatnonzero(np.asarray(bar5[s])); fv[s] = int(b[0]) if len(b) else 0
    ok3 = (EXo["bad_after"] == -1) & (EXo["e"] - 249 >= EXo["s"].map(fv)) & (EXo["E1b_hold"] <= 700)
    pick3 = EXo[ok3].sample(30, random_state=np.random.RandomState(20261013))
    real_sig = SFL.signals_for; cache = {}; nT = 0
    try:
        for r in pick3.itertuples():
            s, e = int(r.s), int(r.e); sid = uni.loc[s, "stock_id"]; mk = uni.loc[s, "market"]
            X = cache.get(s) or own_stock(sid, mk, cal, Qm, Fm, FX, s); cache[s] = X
            SFL.signals_for = lambda R_, s_, X_, DISP_, sid_, X=X: (X["w1"][R_["d0"]:R_["d1"] + 1], X["w2a"][R_["d0"]:R_["d1"] + 1], X["w2b"][R_["d0"]:R_["d1"] + 1])
            ud = pd.DataFrame({"stock_id": [sid], "market": [mk], "name": [uni.loc[s, "name"]]})
            ordered = 0.0; orders = []
            for T in range(e, n):
                Rr = {"cal": cal, "W": {"DISP": {}}, "uni": ud, "d0": 0, "d1": T, "code": {}, "raw": {}}
                out = SFL.replay(Rr, sid, str(cal[e].date()), 1.0, ST, "/nonexistent_aux", names_bj=([], 0, {}))
                nT += 1
                if "錯誤" in out:
                    errs.append(f"③ {sid} e{e} T{T} replay 錯誤 {out['錯誤']}"); break
                stg, act = out["階段"], out["今天收盤後該做什麼"]
                if stg.startswith(("結束", "已出清", "第二段")):
                    tgt = 1.0
                elif stg.startswith("已賣 3 成"):
                    tgt = 1.0 if act.startswith("明天開盤賣剩 7 成") else 0.3
                else:
                    tgt = 1.0 if "明天開盤賣全部" in act else (0.3 if "明天開盤賣 3 成" in act else 0.0)
                if tgt > ordered + 1e-12:
                    orders.append((T, ordered, tgt)); ordered = tgt
                if ordered >= 1 - 1e-12:
                    break
            for v, real in (("b", False), ("r", True)):
                if real and not (np.isfinite(X["avg"][e]) and X["avg"][e] > 0):
                    continue
                parts = realize(X, orders, e, None, real)
                cmp(errs, f"③ {sid} e{e} E1{v} x30", parts["p30"][0], getattr(r, f"E1{v}_x30"))
                cmp(errs, f"③ {sid} e{e} E1{v} x70", parts["p70"][0], getattr(r, f"E1{v}_x70"))
                cmp(errs, f"③ {sid} e{e} E1{v} px30", parts["p30"][1], getattr(r, f"E1{v}_px30"))
                cmp(errs, f"③ {sid} e{e} E1{v} px70", parts["p70"][1], getattr(r, f"E1{v}_px70"))
                cmp(errs, f"③ {sid} e{e} E1{v} g", gross(X, parts, e, real), getattr(r, f"E1{v}_g"), 1e-7)
    finally:
        SFL.signals_for = real_sig
    items.append(f"③ E1 {len(pick3)} 筆、逐日呼叫 replay {nT} 次")
    log(f"[③] {items[-1]}｜錯 {len(errs)}")
    # ── ④ E2 與壞根
    pick4 = EXo.sample(200, random_state=np.random.RandomState(20261014))
    nb = 0
    for r in pick4.itertuples():
        s, e = int(r.s), int(r.e); sid = uni.loc[s, "stock_id"]; mk = uni.loc[s, "market"]
        X = cache.get(s) or own_stock(sid, mk, cal, Qm, Fm, FX, s); cache[s] = X
        bb = [b for b in X["bad"] if b > e]
        bad_after = None
        if bb:
            pbs = [t for t in np.flatnonzero(X["bar"][:bb[0]]) if t >= e]; bad_after = int(pbs[-1]) if pbs else e; nb += 1
        cmp(errs, f"④ {sid} e{e} 壞根前一根", -1 if bad_after is None else bad_after, int(r.bad_after))
        mx = -np.inf; dec = None
        for j in range(e, n):
            mx = max(mx, X["c"][j])
            if X["c"][j] <= mx * 0.7:
                dec = j; break
        orders = [(dec, 0.0, 1.0)] if dec is not None else []
        for v, real in (("b", False), ("r", True)):
            if real and not (np.isfinite(X["avg"][e]) and X["avg"][e] > 0):
                continue
            parts = realize(X, orders, e, bad_after, real)
            cmp(errs, f"④ {sid} e{e} E2{v} x", parts["p70"][0], getattr(r, f"E2{v}_x70"))
            cmp(errs, f"④ {sid} e{e} E2{v} px", parts["p70"][1], getattr(r, f"E2{v}_px70"))
            cmp(errs, f"④ {sid} e{e} E2{v} g", gross(X, parts, e, real), getattr(r, f"E2{v}_g"), 1e-7)
    items.append(f"④ E2 {len(pick4)} 筆（含壞根 {nb} 筆）")
    log(f"[④] {items[-1]}｜錯 {len(errs)}")
    # ── ⑤ 組合
    meta = json.load(open(os.path.join(OUT, "meta_run.json"), encoding="utf-8")); chosen = meta["挑中格"]
    SD = pd.read_csv(os.path.join(OUT, "seeds.csv.gz"))
    if chosen:
        k_, x_, E = int(chosen.split("_")[0][1:]), int(chosen.split("_")[1][1:]) / 100, chosen.split("_")[2]
        sg = SG[(np.isclose(SG["x"], x_)) & (SG["k"] >= k_) & SG["pit"] & SG["段"].isin(["探索", "確認"]) & SG["f4"]]
        EXi = EX.set_index(["s", "e"])
        w0, w1 = int(cal.searchsorted(pd.Timestamp("2017-03-02"))), int(cal.searchsorted(pd.Timestamp("2026-08-24")))
        xe, cs = int(cal.searchsorted(pd.Timestamp("2021-12-30"))), int(cal.searchsorted(pd.Timestamp("2022-01-03")))
        arrs = {}
        A = {k: np.load(os.path.join(WORK, f"arr_{k}.npy"), mmap_mode="r") for k in ("c", "o", "avg", "bar", "trd", "upl")}
        J = {s: j for j, s in enumerate(np.load(os.path.join(WORK, "arr_sids.npy")).tolist())}
        tt = np.arange(n + 1)
        for v in ("b", "r"):
            keys = []; ent = []; xp = []; gg = []; closes = {}; opens = {}; SFk = {}; trad = {}; dlk = {}
            valid = {}
            for s, e, sid in zip(sg["s"].astype(int), sg["e"].astype(int), sg["sid"]):
                rr = EXi.loc[(s, e)]
                if not np.isfinite(rr.get(f"{E}{v}_xpos", np.nan)):
                    continue
                j = J[s]; c = np.r_[np.asarray(A["c"][j]), A["c"][j][-1]]
                key = f"{sid}#{e}"
                Sc = 0.3 * np.where(tt <= rr[f"{E}{v}_dl30"], c, rr[f"{E}{v}_px30"]) + 0.7 * np.where(tt <= rr[f"{E}{v}_dl70"], c, rr[f"{E}{v}_px70"])
                keys.append(key); ent.append(e); xp.append(int(rr[f"{E}{v}_xpos"])); gg.append(float(rr[f"{E}{v}_g"]))
                closes[key] = Sc; opens[key] = np.r_[np.asarray(A["o" if v == "b" else "avg"][j]), np.nan]
                b_ = np.flatnonzero(np.asarray(A["bar"][j]))
                if len(b_) and b_[-1] < w1:
                    SFk[key] = int(b_[-1])
                if v == "r":
                    trad[key] = {"trd": np.r_[np.asarray(A["trd"][j]), False], "up_o": np.r_[np.asarray(A["upl"][j]), False], "dn_o": np.zeros(n + 1, bool), "dn_c": np.zeros(n + 1, bool)}
                    valid[key] = np.asarray(A["bar"][j])
            if v == "r":
                D.DATA = ST
                st_ = TR.delist_status({k: {"trd": valid[k]} for k in valid}, cal, official=TR.load_official())
                dlk = st_
            sig = pd.DataFrame({"sid": keys, "entry_pos": ent, "xpos_F": xp, "g_F": gg})
            for r_ in (0, 1):
                au = []
                R.COST = COST_R if v == "r" else COST_B
                try:
                    o = R.simulate_mtm(sig, "F", 10, np.random.default_rng(20261007 + r_), closes, opens, n + 1, return_equity=True, audit=au, stop_force=SFk,
                                       cap_fn=lambda si, t, hold: all(h.split("#")[0] != si.split("#")[0] for h in hold),
                                       **({"tradable": trad, "delist": dlk} if v == "r" else {}))
                finally:
                    R.COST = COST_B
                eq = np.asarray(o["equity"], float)
                row = SD[(SD["arm"] == f"all|F4|{chosen}|{v}") & (SD["r"] == r_)].iloc[0]
                for nm, (a_, b_) in {"主窗": (w0, w1), "探索": (w0, xe), "確認": (cs, w1)}.items():
                    lo = max(min(o["first"], a_), a_); hi = min(max(o["end"], b_ + 1), b_ + 1)
                    seg = eq[lo:hi]; cg = (seg[-1] / seg[0]) ** (245 / len(seg)) - 1; pk = np.maximum.accumulate(seg); md = float(((seg - pk) / pk).min())
                    if repr(float(cg)) != repr(float(row[f"{nm}_年化"])) and not np.isclose(cg, row[f"{nm}_年化"], rtol=1e-12):
                        errs.append(f"⑤ {v} r{r_} {nm} 年化 自算 {cg} 檔 {row[f'{nm}_年化']}")
                    if not np.isclose(md, row[f"{nm}_回落"], rtol=1e-12):
                        errs.append(f"⑤ {v} r{r_} {nm} 回落 自算 {md} 檔 {row[f'{nm}_回落']}")
                buys = {a["sid"]: a for a in au if a["side"] == "buy"}
                gmap = dict(zip(keys, gg))
                for a in au:
                    if a["side"] == "sell" and a["sid"] not in SFk:
                        gr = a["px"] / buys[a["sid"]]["px"] - 1
                        if not np.isclose(gr, gmap[a["sid"]], rtol=1e-9, atol=1e-12):
                            errs.append(f"⑤ {v} r{r_} {a['sid']} 實現 {gr} 訊號 g {gmap[a['sid']]}")
        items.append(f"⑤ 組合 {chosen} base／現實版 × 種子 0、1：實體陣列重跑、窗年化回落自寫、逐筆 g")
        log(f"[⑤] {items[-1]}｜錯 {len(errs)}")
    out = {"項目": items, "錯誤數": len(errs), "錯誤": errs[:80], "時間": f"{pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）"}
    json.dump(out, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[查核] 錯誤 {len(errs)}｜{items}")


if __name__ == "__main__":
    main()
