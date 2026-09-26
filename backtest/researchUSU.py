# -*- coding: utf-8 -*-
"""USREG-U（美股移植 PREREGU：費波那契回撤 38.2／61.8 的止跌反彈，有沒有比旁邊的位置多）——pre（頻率、可判定性）＋本體。

    PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSU --pre  [--procs 2]   # ⛔ 不讀 T 以後的任何收盤
    PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSU --main [--procs 2]

判準：美股登錄 seq2（a3c98a07e882a574，正文）＋seq3（81bfc48eff6258f5，§三 先驗補「已看過台股 U 結果」）＋seq4＋seq5；
     移植來源 台股 PREREGU seq1（4ff4c1731fdded12）§一～§八。⚠ seq2 §二①／seq4 §一 的假訊號臂修正只寫 M、X ⇒ U 的判定用假訊號臂照台股登錄 §七（200 次隨機位置）。
讀法：裁定 seq214 §三（R1～R4、B1～B7、USREG-M 的 B1 斷點規則）＋ USREG-X 的 V1～V5；台股 fib_u U1～U6、researchU_core V1～V5、researchU B1～B9 照先例。
偵測器：backtest/fib_u.py（台股同一支，⛔ 未改）；fixture：selftest_fib_u.run_all()（台股 F1～F9）＋台股本體自測（researchU.selftest）＋本支 usu_fixtures()。

⛔⛔ 授權：resultsUSU/ 只寫彙總；逐筆、逐檔寫 ~/us_work/usu/（repo 外）並列 sha。

⭐ 讀法（美股新增；★＝台股先例兩種讀法照先例）：
 W1 價格、日曆、母體、暖身、無效 K 棒 ＝ USREG-M／X 同一套（scope＝panel）；波段偵測用全部歷史（只用到 T 以前）。
 W2 事件 ＝ 觸及日 T 當天 in_index＝1 且有有效 K 棒（R1：不在母體的觸及 ⇒ 不是事件、⛔ 不開合併窗）；T ∈ [窗首, 窗尾−H]。
 W3 處理順序 ＝ 台股 V2（同檔同位置跨波段合併 20 日 → [T, T+H] 硬斷點 ⇒ 剔除）；硬斷點 ＝ R2 P0＋R3 S1（轉接層 hard_break 或任一天沒有有效 K 棒；
    只數首末 K 棒之間）；台股的「T+1 停牌／開盤漲停」本來就不在主格（只在描述臂 d）。
 W4 §五 X ＝ (close(≤T+20)／close(T) − 1) − EWc_20(T)；EWc_20(d) ＝ d 日 in_index 且有收盤的股票 close(≤ d+20)／close(d) − 1 等權，
    (d, d+20] 有 hard_break 者不進（B1＋M 斷點規則）。R ＝ … − 0.05%。
 W5 描述臂 d（交易版）＝ USREG-M 同一套（px(T+21)／open(T+1)、EW_20(T+1) in_index 開盤版）；T+1 沒有有效 K 棒 ⇒ 不進 d。
 W6 20 日區段上限 ＝ ⌈(窗尾−20 − 窗首 + 1)／20⌉ ＝ 133（台股同式 115）。
 W7 §五「上市／上櫃」⇒ B3「期初已在指數／期中加入」（T 所在指數區間的起點 ≤ 窗首 ⇒ 期初已在）。
 W8 頻率與回撤深度的波段 ＝ 確認日 conf ∈ [窗首, 窗尾−20] 且 conf 當天在指數；每檔每年分母 ＝ 在指數且有 K 棒的日數（USREG-M U10）。
 W9 描述用假訊號臂（台股 B6 先例、改 seq175 新預設）：同檔、全窗、只排除「過去 20 個交易日內（[t−20, t]）有該檔【任一位置】保留真事件」的日子；
    可抽日 ＝ 窗內、in_index、有效 K 棒、low 非缺；每位置抽該檔該位置真事件數；位置價 p′ ＝ ρ × low(t)（台股 B6）；之後同 W3 合併與斷點。
    種子 [20260925＋r, crc32(代號)]，r＝0…29；⛔ 不計 N、不進判定。
"""
from __future__ import annotations
import os, sys, time, json, io, csv, zlib, hashlib
from multiprocessing import Pool
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
from backtest import us_data as U
from backtest import fib_u as FU
from backtest import selftest_fib_u as SFU
from backtest import researchUSM as RU
from backtest import researchUSM_body as MB
import researchU as TU                             # 台股本體：dstat、dstat_agg、verdict、summ、fake_positions、selftest（只 import）

OUT = os.path.expanduser("~/tw-p17/backtest/resultsUSU")
WORK = os.path.expanduser("~/us_work/usu")
COST = U.COST_ROUNDTRIP
SEED = 20260925
REPS_REG, REPS_NEW = 200, 30
MERGE, BLOCK = 20, 20
CFGS = [(5, 20), (3, 20), (10, 20), (5, 10), (5, 40)]
POS = list(FU.POS)
WD, W50, W38, W62 = TU.WD, TU.W50, TU.W38, TU.W62
_G = {}


def cfg_name(k, H):
    return "k{}_H{}".format(k, H)


def sha256f(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _init(cal, w0, w1, fr, mon, mode):
    _G.update(cal=cal, w0=w0, w1=w1, fr=fr, mon=mon, mode=mode)


def merge_brk(S, T, p, H=20):
    """W3 同一順序（已依 T 排序）：回保留 (T, p) 與 (合併數, 斷點數)。"""
    kT, kp = [], []; t_keep = -10 ** 9; nm = nb = 0
    for t, q in zip(T, p):
        if t_keep < t <= t_keep + MERGE:
            nm += 1; continue
        if S.brk(int(t), int(t) + H):
            nb += 1; continue
        kT.append(int(t)); kp.append(float(q)); t_keep = t
    return np.array(kT, np.int64), np.array(kp), nm, nb


def assign_us(S, r, w0, w1, H):
    """W2、W3：偵測結果 ⇒ 每個窗內、在母體的觸及的狀態列（⛔ 不讀 T 以後的價格）。"""
    W = r["waves"]; wLast = w1 - H
    tc = [t for t in r["touches"] if t["state"] == "觸及" and w0 <= t["T"] <= wLast]
    rows = []; nonmem = 0
    for pos in FU.POS:
        ev = sorted((t for t in tc if t["pos"] == pos), key=lambda t: t["T"])
        t_keep = -10 ** 9
        for t in ev:
            T = t["T"]; w = W[t["wave"]]
            if not (S.member[T] and S.valid[T]):
                nonmem += 1; continue
            f_brk = S.brk(T, T + H)
            if t_keep < T <= t_keep + MERGE:
                stt = "合併掉"
            elif f_brk:
                stt = "剔除_硬斷點"
            else:
                stt = "保留"; t_keep = T
            rows.append({"pos": pos, "T": int(T), "p": float(t["p"]), "wave": int(t["wave"]), "tL": int(w["tL"]), "tH": int(w["tH"]),
                         "conf": int(w["conf"]), "L0": float(w["L0"]), "H0": float(w["H0"]), "狀態": stt,
                         "f_dl_in": bool(S.last < T + H), "f_brk_wave": bool(S.brk(int(w["tL"]), T - 1))})
    rows.sort(key=lambda x: (x["T"], x["pos"]))
    return rows, nonmem


def work(t):
    cal, w0, w1, fr, mon, mode = _G["cal"], _G["w0"], _G["w1"], _G["fr"], _G["mon"], _G["mode"]
    n = len(cal); wE = w1 - 20
    df = U.load_ohlc(t, scope="panel")
    if len(df) == 0:
        return None
    A0 = RU.prep(df, cal)
    if len(A0["bars"]) == 0:
        return None
    S = MB.Stk(t, A0, MB.low_aligned(df, cal), RU.member_array(t, cal), RU.span_start_array(t, cal), w0, wE)
    h, l, c, o = S.h, S.l, S.c, S.o
    det, cf, nonmem = {}, {}, {}
    for k, H in CFGS:
        if k not in det:
            det[k] = FU.detect_calendar(h, l, c, k)
        cf[(k, H)], nonmem[(k, H)] = assign_us(S, det[k], w0, w1, H)
    res = {"t": t, "S": S, "cf": cf, "nonmem": nonmem, "wv": {}}
    for k in (5, 3, 10):
        r = det[k]; W = r["waves"]
        inwin = {i for i, x in enumerate(W) if w0 <= x["conf"] <= wE and S.member[x["conf"]]}
        st = {}
        for tt in r["touches"]:
            if tt["wave"] in inwin:
                st.setdefault(tt["pos"], {}).setdefault(tt["state"], 0)
                st[tt["pos"]][tt["state"]] += 1
        anypre = len({tt["wave"] for tt in r["touches"] if tt["wave"] in inwin and tt["state"] == "確認前已觸及"})
        raw = [tt for tt in r["touches"] if tt["state"] == "觸及" and w0 <= tt["T"] <= wE and S.member[tt["T"]]]
        key = {}
        for tt in raw:
            key.setdefault((tt["wave"], tt["T"]), []).append(tt["pos"])
        multi = {}
        for tt in raw:
            m_ = multi.setdefault(tt["pos"], [0, 0]); m_[0] += 1; m_[1] += int(len(key[(tt["wave"], tt["T"])]) > 1)
        res["wv"][k] = {"n_win": len(inwin), "n_all": len(W), "state": st, "anypre": anypre, "multi": multi}
    if mode == "pre":
        res.pop("S")
        res["expo"] = int(np.sum(S.member[w0:wE + 1] & S.valid[w0:wE + 1]))
        return res
    # ── 本體：反彈判定、報酬、假訊號臂
    cff = pd.Series(c).ffill().to_numpy()
    res.update({"cff": cff})
    for (k, H), rows in cf.items():
        if not rows:
            cf[(k, H)] = pd.DataFrame(); continue
        E = pd.DataFrame(rows); E["y"] = -9
        kp = (E["狀態"] == "保留").to_numpy(); T = E["T"].to_numpy(np.int64); p = E["p"].to_numpy(float)
        E.loc[kp, "y"] = FU.outcome_vec(c, T[kp], p[kp], H, FU.BAND)
        if (k, H) == (5, 20):
            for nm_, band in (("y_b3", 0.03), ("y_b8", 0.08)):
                E[nm_] = -9; E.loc[kp, nm_] = FU.outcome_vec(c, T[kp], p[kp], H, band)
            Tk, pk = T[kp], p[kp]
            idx = Tk[:, None] + np.arange(H + 1)[None, :]; C = c[idx]
            up = C >= (pk * 1.05)[:, None]; dn = C <= (pk * 0.95)[:, None]; an = up | dn
            f_ = np.argmax(an, axis=1); has = an.any(axis=1); ya = np.full(len(Tk), -1)
            ya[has] = np.where(up[np.arange(len(Tk)), f_][has], 1, 0)
            E["y_alt"] = -9; E.loc[kp, "y_alt"] = ya
            g = np.full(len(E), np.nan); g[kp] = cff[Tk + 20] / c[Tk] - 1.0; E["g20"] = g
            okd = kp & (T + 21 <= w1)
            t1 = np.minimum(T + 1, n - 1)
            trd = S.valid[t1] & (np.nan_to_num(o[t1]) > 0)
            E["d_窗尾"] = kp & ~(T + 21 <= w1); E["d_T1停牌"] = okd & ~trd
            dd = okd & trd
            gd = np.full(len(E), np.nan); gd[dd] = S.px[T[dd] + 21] / o[T[dd] + 1] - 1.0
            E["gd"] = gd; E["d_ok"] = dd
            E["grp"] = ["期初已在" if S.spanst[x] <= np.datetime64(cal[w0]) else "期中加入" for x in T]
        cf[(k, H)] = E
    dep = []
    for W in det[5]["waves"]:
        if w0 <= W["conf"] <= wE and S.member[W["conf"]]:
            seg = l[W["tH"]:W["end"] + 1]
            mn = float(np.nanmin(seg)) if np.isfinite(seg).any() else np.nan
            dep.append(((W["H0"] - mn) / (W["H0"] - W["L0"]), W["why_end"]))
    res["depth"] = dep
    # 登錄假訊號臂（台股 B5）
    r5 = det[5]; bars = r5["bars"]; lb = l[bars]
    wb = [{"conf": W["conf_bar"], "end": W["end_bar"], "H0": W["H0"], "L0": W["L0"], "pre_min": W["pre_min"]} for W in r5["waves"]]
    NM = mon.max() + 1
    acc = np.zeros((fr.shape[0] * fr.shape[1], NM, 2), np.int32)
    if wb:
        Tb, PP = FU.touches_many(wb, lb, fr.ravel())
        for j in range(Tb.shape[0]):
            ok = Tb[j] >= 0
            if not ok.any():
                continue
            Tc = bars[Tb[j][ok]]; pc = PP[j][ok]
            w_ = (Tc >= w0) & (Tc <= wE)
            w_ &= S.member[Tc] & S.valid[Tc]
            if not w_.any():
                continue
            Tc, pc = Tc[w_], pc[w_]
            o_ = np.argsort(Tc, kind="stable"); Tc, pc = Tc[o_], pc[o_]
            Tk, pk, _, _ = merge_brk(S, Tc, pc)
            if len(Tk) == 0:
                continue
            y = FU.outcome_vec(c, Tk, pk); d_ = y >= 0
            np.add.at(acc[j, :, 0], mon[Tk[d_]], 1); np.add.at(acc[j, :, 1], mon[Tk[d_]], y[d_].astype(np.int32))
    res["fake_reg"] = acc
    # 描述用假訊號臂（W9）
    E5 = cf[(5, 20)]
    acc2 = np.zeros((REPS_NEW, len(POS), NM, 2), np.int32); cnt2 = np.zeros((REPS_NEW, 4), np.int64)
    if len(E5):
        K = E5[E5["狀態"] == "保留"]
        realT = np.sort(K["T"].to_numpy(np.int64))
        cand = np.flatnonzero(S.valid & np.isfinite(l) & S.member); cand = cand[(cand >= w0) & (cand <= wE)]
        if len(realT):
            cand = cand[~MB.excl_mask(cand, realT)]
        seed2 = zlib.crc32(t.encode("utf-8"))
        for r in range(REPS_NEW):
            rng = np.random.default_rng([SEED + r, seed2])
            for pi, pos in enumerate(POS):
                kk = K[K["pos"] == pos].sort_values("T")
                if len(kk) == 0:
                    continue
                m = min(len(kk), len(cand)); cnt2[r, 3] += len(kk) - m
                if m == 0:
                    continue
                dr_ = np.sort(rng.choice(cand, size=m, replace=False))
                rho = (kk["p"].to_numpy(float) / l[kk["T"].to_numpy(np.int64)])[:m]
                Tk, pk, nm_, nb_ = merge_brk(S, dr_, rho * l[dr_])
                cnt2[r, 0] += m; cnt2[r, 1] += nm_; cnt2[r, 2] += nb_
                if len(Tk) == 0:
                    continue
                y = FU.outcome_vec(c, Tk, pk); d_ = y >= 0
                np.add.at(acc2[r, pi, :, 0], mon[Tk[d_]], 1); np.add.at(acc2[r, pi, :, 1], mon[Tk[d_]], y[d_].astype(np.int32))
    res["fake_new"] = acc2; res["fake_new_cnt"] = cnt2
    return res


# ═════════════ 基準（W4）與 fixture ═════════════
def ew_close_T(C, okM, CFF, CSPB, H):
    """EWc_H(d) ＝ okM[d] 的股票、(d, d+H] 無 hard_break：CFF(d+H)／C(d) − 1 等權。"""
    n = C.shape[0]; out = np.full(n, np.nan)
    Cd = np.where(okM[:n - H], C[:n - H], np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        r = CFF[H:] / Cd - 1.0
    r[(CSPB[H:] - CSPB[:n - H]) > 0] = np.nan
    cnt = np.isfinite(r).sum(axis=1); s = np.nansum(r, axis=1)
    out[:n - H] = np.where(cnt > 0, s / np.maximum(cnt, 1), np.nan)
    return out


def usu_fixtures():
    out = []
    rng = np.random.default_rng(5)
    n, S_ = 70, 6
    C = np.exp(rng.normal(0, 0.03, (n, S_)).cumsum(axis=0)) * 50
    C[10:13, 1] = np.nan; C[40:, 2] = np.nan; C[:25, 3] = np.nan
    MEM = np.ones((n, S_), bool); MEM[:30, 4] = False
    PB = np.zeros((n, S_), bool); PB[35, 5] = True
    okM = np.isfinite(C) & MEM; CFF = pd.DataFrame(C).ffill().to_numpy()
    worst = 0.0
    for H in (5, 20):
        e = ew_close_T(C, okM, CFF, np.cumsum(PB, axis=0), H)
        for d in range(n - H):
            v = [CFF[d + H, j] / C[d, j] - 1 for j in range(S_) if okM[d, j] and not PB[d + 1:d + H + 1, j].any()]
            b = sum(v) / len(v) if v else np.nan
            worst = max(worst, abs(e[d] - b) if np.isfinite(b) else (0 if np.isnan(e[d]) else 1))
    assert worst < 1e-12, worst
    out.append("UU1 EWc 向量法＝獨立迴圈法（在指數／停牌／下市／上市前／斷點排除）最大差 {:.1e}".format(worst))
    # UU2 assign_us：手造 Stk ＋ 假偵測結果
    m = 200
    c = np.linspace(100, 90, m); o = c + 0.1; h = c + 0.5
    A = {"O": o.copy(), "H": h.copy(), "C": c.copy(), "valid": np.ones(m, bool), "bars": np.arange(m), "pb": np.zeros(m, bool)}
    A["C"][100] = np.nan; A["O"][100] = np.nan; A["valid"][100] = False; A["bars"] = np.flatnonzero(A["valid"])
    mem = np.ones(m, bool); mem[50] = False
    Sx = MB.Stk("fx", A, c - 0.5, mem, np.full(m, np.datetime64("2010-01-01"), dtype="datetime64[ns]"), 0, m - 21)
    W = [{"tL": 0, "tH": 5, "conf": 10, "L0": 80.0, "H0": 100.0}]
    tc = [{"wave": 0, "pos": "38.2", "p": 92.36, "state": "觸及", "T": T} for T in (20, 30, 45, 50, 75, 97, 130)] + \
         [{"wave": 0, "pos": "30", "p": 94.0, "state": "確認前已觸及", "T": None}]
    rows, nm = assign_us(Sx, {"waves": W, "touches": tc}, 0, 180, 20)
    st = [(r_["T"], r_["狀態"]) for r_ in rows]
    # 20 保留｜30 合併｜45 保留｜50 不在母體（不開窗）｜75 保留｜97 [97,117] 含 100 ⇒ 斷點（不開窗）｜130 保留
    assert st == [(20, "保留"), (30, "合併掉"), (45, "保留"), (75, "保留"), (97, "剔除_硬斷點"), (130, "保留")] and nm == 1, (st, nm)
    out.append("UU2 事件狀態：觸及 [20,30,45,50,75,97,130] ⇒ 保留／合併／保留／不在母體（不開窗）／保留／[T,T+20] 缺日剔除／保留")
    for s in out:
        print("✅", s, flush=True)
    return out


def neff_us(E, w0, cap, pos=FU.SIX):
    o = {}
    for p in pos:
        d = E[(E["pos"] == p) & (E["y"] >= 0)]
        nb = int(np.minimum((d["T"] - w0) // BLOCK, cap - 1).nunique()) if len(d) else 0
        o[p] = {"分勝負事件": int(len(d)), "區段": nb, "min": int(min(len(d), nb))}
    return min(v["min"] for v in o.values()), min(v["分勝負事件"] for v in o.values()), o


def qd(x):
    x = np.asarray(x, float)
    return {"n": int(len(x)), "平均": round(float(x.mean()), 4), "中位": round(float(np.median(x)), 4),
            "p90": round(float(np.percentile(x, 90)), 4), "零事件佔比": round(float((x == 0).mean()), 4)} if len(x) else {"n": 0}


def pp_(x, d=2):
    return "—" if x is None or not np.isfinite(x) else "{:+.{}f}pp".format(x * 100, d)


def main():
    t0 = time.time()
    U.assert_pinned()
    mode = "pre" if "--pre" in sys.argv else "main"
    fx = {"台股F1_F9": SFU.run_all(), "台股本體自測G1_G4": TU.selftest(), "美股UU1_UU2": usu_fixtures()}
    procs = int(sys.argv[sys.argv.index("--procs") + 1]) if "--procs" in sys.argv else 2
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    reps = int(sys.argv[sys.argv.index("--reps") + 1]) if "--reps" in sys.argv else REPS_REG
    calF = U.load_calendar(); cal = calF[calF >= MB.CAL0]; n = len(cal)
    w0 = int(cal.searchsorted(U.WINDOW[0])); w1 = int(cal.searchsorted(U.WINDOW[1])); wE = w1 - 20
    assert cal[w0] == U.WINDOW[0] and cal[w1] == U.WINDOW[1]
    cap = -(-(wE - w0 + 1) // BLOCK)
    base = cal[w0].year * 12 + cal[w0].month
    mon = np.clip(np.array([d.year * 12 + d.month - base for d in cal]), 0, None)
    fr, ab = TU.fake_positions(reps)
    tick = [t for t in U.universe_table()["ticker"] if t not in set(U.no_ohlc_tickers())]
    if lim:
        tick = tick[:lim]
    os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    print("[資料] us-stock-data {}｜判定窗 {}～{}｜T 可落 ～{}｜區段上限 {}｜{} 檔｜模式 {}".format(
        U.data_commit()[:10], cal[w0].date(), cal[w1].date(), cal[wE].date(), cap, len(tick), mode), flush=True)
    ST = {}
    NM = int(mon.max() + 1)
    FR = np.zeros((reps * 6, NM, 2), np.int64); FN = np.zeros((REPS_NEW, len(POS), NM, 2), np.int64); FNc = np.zeros((REPS_NEW, 4), np.int64)
    with Pool(procs, initializer=_init, initargs=(cal, w0, w1, fr, mon, mode)) as pool:
        for r in pool.imap_unordered(work, tick, chunksize=4):
            if r is None:
                continue
            if mode == "main":
                FR += r.pop("fake_reg"); FN += r.pop("fake_new"); FNc += r.pop("fake_new_cnt")
            ST[r["t"]] = r
    sids = sorted(ST)
    print("[讀檔＋偵測] 可用 {} 檔｜{:.0f}s".format(len(ST), time.time() - t0), flush=True)

    if mode == "pre":
        DPY = (wE - w0 + 1) / ((cal[wE] - cal[w0]).days / 365.25)
        R_ = {"性質": "USREG-U pre：頻率＋可判定性算術（⛔ 未讀 T 以後任何收盤）", "資料commit": U.data_commit(),
              "判定窗": [str(cal[w0].date()), str(cal[w1].date())], "T可落": [str(cal[w0].date()), str(cal[wE].date())],
              "可用檔數": len(ST), "區段上限": int(cap), "fixture": fx, "波段": {}, "事件帳": {}}
        for k in (5, 3, 10):
            nwin = sum(ST[s]["wv"][k]["n_win"] for s in sids)
            per = [(ST[s]["expo"] / DPY, ST[s]["wv"][k]["n_win"]) for s in sids if ST[s]["expo"] > 0]
            P_ = np.array(per); one = P_[P_[:, 0] >= 1]
            state = {}; multi = {}
            for s in sids:
                for p, d in ST[s]["wv"][k]["state"].items():
                    for kk, v in d.items():
                        state.setdefault(p, {}).setdefault(kk, 0); state[p][kk] += v
                for p, v in ST[s]["wv"][k]["multi"].items():
                    m_ = multi.setdefault(p, [0, 0]); m_[0] += v[0]; m_[1] += v[1]
            anyp = sum(ST[s]["wv"][k]["anypre"] for s in sids)
            tot = [sum(v[0] for v in multi.values()), sum(v[1] for v in multi.values())]
            R_["波段"]["k{}".format(k)] = {"合格波段數_conf在窗內且在指數": nwin, "每檔每年": {**qd(one[:, 1] / one[:, 0]), "合併比率": round(float(P_[:, 1].sum() / P_[:, 0].sum()), 4)},
                                        "確認前已觸及（逐位置）": {p: {"n": state.get(p, {}).get("確認前已觸及", 0), "比例": round(state.get(p, {}).get("確認前已觸及", 0) / max(1, nwin), 4)} for p in POS},
                                        "至少一個位置確認前已觸及的波段比例": round(anyp / max(1, nwin), 4),
                                        "同日穿過多位置（七位置合計）": {"原始觸及": tot[0], "同日另有位置": tot[1], "比例": round(tot[1] / max(1, tot[0]), 4)}}
            print("[波段 k{}] 窗內合格 {:,}｜每股票年 {}｜同日多位置 {}".format(k, nwin, R_["波段"]["k{}".format(k)]["每檔每年"]["合併比率"],
                  R_["波段"]["k{}".format(k)]["同日穿過多位置（七位置合計）"]["比例"]), flush=True)
        shas = []
        for k, H in CFGS:
            nm = cfg_name(k, H); acc = {}; rows = []
            for s in sids:
                for r_ in ST[s]["cf"][(k, H)]:
                    acc.setdefault(r_["pos"], {}).setdefault(r_["狀態"], 0); acc[r_["pos"]][r_["狀態"]] += 1
                    rows.append({"ticker": s, "pos": r_["pos"], "T": str(cal[r_["T"]].date()), "tL": str(cal[r_["tL"]].date()),
                                 "tH": str(cal[r_["tH"]].date()), "conf": str(cal[r_["conf"]].date()), "狀態": r_["狀態"],
                                 "f_dl_in": int(r_["f_dl_in"]), "f_brk_wave": int(r_["f_brk_wave"])})
            dfr = pd.DataFrame(rows)
            p = os.path.join(WORK, "events_{}.csv".format(nm)); dfr.to_csv(p, index=False, encoding="utf-8")
            shas.append((os.path.basename(p), len(dfr), sha256f(p)))
            kept = dfr[dfr["狀態"] == "保留"]
            blk = {pp: int(((pd.to_datetime(kept.loc[kept["pos"] == pp, "T"]).map(lambda d: cal.get_loc(d)) - w0) // BLOCK).clip(upper=cap - 1).nunique())
                   if (kept["pos"] == pp).any() else 0 for pp in POS}
            R_["事件帳"][nm] = {"逐位置": acc, "不在母體的觸及（不開窗）": int(sum(ST[s]["nonmem"][(k, H)] for s in sids)),
                              "保留": {pp: int((kept["pos"] == pp).sum()) for pp in POS}, "有保留事件的區段": blk,
                              "n_eff上限（保留數與區段取小，六位置取最小）": int(min(min(int((kept["pos"] == pp).sum()), blk[pp]) for pp in FU.SIX)),
                              "保留中_波段內部有斷點（只報、未剔）": int(kept["f_brk_wave"].sum()), "保留中_持有窗內下市": int(kept["f_dl_in"].sum())}
            print("[事件 {}] 保留 {}｜區段 {}｜n_eff 上限 {}".format(nm, R_["事件帳"][nm]["保留"], blk, R_["事件帳"][nm]["n_eff上限（保留數與區段取小，六位置取最小）"]), flush=True)
        R_["開跑前算術"] = {"區段長": 20, "每位置最多區段": int(cap), "依構造最好": "出口③（①②③ 都可能）"}
        R_["逐筆檔sha（repo外）"] = {a: {"rows": b, "sha256": c} for a, b, c in shas}
        with io.open(os.path.join(OUT, "pre_work_sha.csv"), "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n"); w.writerow(["file（~/us_work/usu/，repo 外）", "rows", "sha256"]); w.writerows(shas)
        json.dump(R_, open(os.path.join(OUT, "pre_freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
        print("pre 完成 {:.0f}s".format(time.time() - t0))
        return

    # ═════════════ 本體 ═════════════
    CHK = {"fixture": fx}
    rows_eq = {}
    for k, H in CFGS:
        nm = cfg_name(k, H)
        ref = pd.read_csv(os.path.join(WORK, "events_{}.csv".format(nm)), dtype=str)
        if lim:
            ref = ref[ref["ticker"].isin(sids)]
        ref = ref.sort_values(["ticker", "T", "pos"], kind="stable").reset_index(drop=True)
        parts = []
        for s in sids:
            E = ST[s]["cf"][(k, H)]
            if len(E):
                parts.append(pd.DataFrame({"ticker": s, "pos": E["pos"], "T": [str(cal[t].date()) for t in E["T"]], "tL": [str(cal[t].date()) for t in E["tL"]],
                                           "tH": [str(cal[t].date()) for t in E["tH"]], "conf": [str(cal[t].date()) for t in E["conf"]], "狀態": E["狀態"]}))
        mine = pd.concat(parts, ignore_index=True).sort_values(["ticker", "T", "pos"], kind="stable").reset_index(drop=True)
        cols = ["ticker", "pos", "T", "tL", "tH", "conf", "狀態"]
        same = mine.shape[0] == ref.shape[0] and bool((mine[cols].astype(str).values == ref[cols].astype(str).values).all())
        rows_eq[nm] = {"列數_本體": int(len(mine)), "列數_pre": int(len(ref)), "逐列相同": same}
        print("[查核1] {}：{:,}／{:,} ⇒ {}".format(nm, len(mine), len(ref), "相同" if same else "⛔ 不同"), flush=True)
        if not same:
            raise SystemExit("⛔ 本體事件與 pre 段不一致：{} ⇒ 中止".format(nm))
    CHK["事件與pre逐列相同"] = rows_eq
    SS = [ST[s]["S"] for s in sids]
    Cm = np.column_stack([x.c for x in SS]); CFm = np.column_stack([ST[s]["cff"] for s in sids])
    MEMV = np.column_stack([x.member & x.valid for x in SS]); CSPB = np.column_stack([x.cs_pb for x in SS])
    EWc = ew_close_T(Cm, MEMV, CFm, CSPB, 20)
    Om = np.column_stack([x.o for x in SS]); okM = np.column_stack([x.okO & x.member for x in SS]); PXm = np.column_stack([x.px for x in SS])
    EWo = MB.ew_us(Om, okM, PXm, CSPB, 20)
    del Cm, CFm, Om, PXm
    p = os.path.join(WORK, "ewc20_ewo20.csv")
    pd.DataFrame({"date": [str(d.date()) for d in cal], "EWc20": EWc, "EWo20": EWo, "n_c": MEMV.sum(axis=1), "n_o": okM.sum(axis=1)}).to_csv(p, index=False)
    shas = [(os.path.basename(p), n, sha256f(p))]

    def cat(key):
        parts = [ST[s]["cf"][key].assign(sid=s) for s in sids if len(ST[s]["cf"][key])]
        E = pd.concat(parts, ignore_index=True); E = E[E["狀態"] == "保留"].copy()
        E["mon"] = [str(cal[t])[:7] for t in E["T"]]; E["wave_id"] = E["sid"] + "|" + E["tH"].astype(str)
        return E

    E = cat((5, 20))
    E["EWc"] = EWc[E["T"].to_numpy()]; E["X"] = E["g20"] - E["EWc"]; E["R"] = E["g20"] - COST
    E["EWo"] = [EWo[t + 1] for t in E["T"]]; E["Xd"] = E["gd"] - E["EWo"]; E["Rd"] = E["gd"] - COST
    RES = {"性質": "USREG-U 本體（單筆層；判定一格 ⇒ 美股 N_前段 +1）", "資料commit": U.data_commit(),
           "登錄": {"seq2": "a3c98a07e882a574", "seq3": "81bfc48eff6258f5", "seq4": "cbfc7610923b9e53", "seq5": "ffb22ecb1bd749ff",
                  "台股PREREGU_seq1": "4ff4c1731fdded12", "讀法": "seq214 §三＋USREG-X V1～V5＋台股 U1～U6、V1～V5、B1～B9；美股 W1～W9"},
           "判定窗": [str(cal[w0].date()), str(cal[w1].date())], "可用檔數": len(ST), "成本來回": COST, "區段上限": int(cap)}
    sm = TU.dstat(E, WD, "mon"); sw = TU.dstat(E, WD, "wave_id")
    ne, nmin, ned = neff_us(E, w0, cap)
    ex, rs = TU.verdict(sm, ne, nmin)
    und = {p: {"保留": int((E["pos"] == p).sum()), "分勝負": int(((E["pos"] == p) & (E["y"] >= 0)).sum()),
               "反彈": int(((E["pos"] == p) & (E["y"] == 1)).sum()), "沒止住": int(((E["pos"] == p) & (E["y"] == 0)).sum()),
               "不分勝負": int(((E["pos"] == p) & (E["y"] == -1)).sum())} for p in POS}
    for p in POS:
        und[p]["b"] = und[p]["反彈"] / max(1, und[p]["分勝負"]); und[p]["不分勝負比例"] = und[p]["不分勝負"] / max(1, und[p]["保留"])
    J = {"D": sm["D"], "lo_月": sm["lo"], "hi_月": sm["hi"], "se_月": sm["se"], "曆月數": sm["群數"],
         "lo_波段": sw["lo"], "hi_波段": sw["hi"], "se_波段": sw["se"], "波段群數": sw["群數"],
         "n_eff": ne, "n_eff明細": ned, "出口": ex, "結果": rs, "各位置": und,
         "帶緣兩種讀法差異件數": int((E["y"] != E["y_alt"]).sum())}
    print("[判定格] D {}（月 CI {} ～ {}；波段 {} ～ {}）｜n_eff {}｜{} {}".format(
        pp_(sm["D"]), pp_(sm["lo"]), pp_(sm["hi"]), pp_(sw["lo"]), pp_(sw["hi"]), ne, ex, rs), flush=True)
    print("   b(x)：" + "｜".join("{} {:.4f}（{:,}）".format(p, und[p]["b"], und[p]["分勝負"]) for p in POS), flush=True)
    fk = []
    for r in range(reps):
        A = FR[r * 6:(r + 1) * 6]
        Dv, se, b, nx = TU.dstat_agg(A, [(1, 0.5), (0, -0.25), (2, -0.25), (4, 0.5), (3, -0.25), (5, -0.25)])
        fk.append({"r": r, "a": ab[r][0], "b": ab[r][1], "D": Dv, "lo": Dv - 1.96 * se, "hi": Dv + 1.96 * se, "n_min": int(nx.min()),
                   "CI不含0": bool(not (Dv - 1.96 * se <= 0 <= Dv + 1.96 * se))})
    FK = pd.DataFrame(fk); FK.to_csv(os.path.join(OUT, "body_fake_registered.csv"), index=False, encoding="utf-8")
    fD = FK["D"].to_numpy(); p95 = float(np.percentile(fD, 95)); xge = int((fD >= sm["D"]).sum())
    fake = {"次數": reps, "真D百分位": float((fD < sm["D"]).mean() * 100), "D_fake≥真D的次數x": xge, "D_fake的95百分位": p95,
            "D_fake平均": float(fD.mean()), "D_fake範圍": [float(fD.min()), float(fD.max())], "CI不含0的次數（附帶）": int(FK["CI不含0"].sum()),
            "真D未超過95百分位": bool(sm["D"] <= p95)}
    fake["警語"] = ("⚠ 隨機兩個位置也有 {}／{} 同樣好".format(xge, reps) if (fake["真D未超過95百分位"] and rs.startswith("結果②")) else "（非結果② 或真 D 超過 95 百分位 ⇒ 不加警語）")
    J["假訊號臂_登錄"] = fake
    RES["判定格"] = J
    print("[§七] 真 D 百分位 {:.1f}｜x＝{}／{}｜{}".format(fake["真D百分位"], xge, reps, fake["警語"]), flush=True)
    nw = []
    for r in range(REPS_NEW):
        A = FN[r]
        Dv, se, b, nx = TU.dstat_agg(A, [(POS.index(p), w) for p, w in WD.items()])
        nw.append({"r": r, "D": Dv, "lo": Dv - 1.96 * se, "hi": Dv + 1.96 * se, "CI不含0": bool(not (Dv - 1.96 * se <= 0 <= Dv + 1.96 * se)),
                   **{"b_" + p: float(A[i, :, 1].sum() / max(1, A[i, :, 0].sum())) for i, p in enumerate(POS)}})
    NW = pd.DataFrame(nw); NW.to_csv(os.path.join(OUT, "body_fake_samestock_pastonly.csv"), index=False, encoding="utf-8")
    RES["描述用假訊號臂_同檔全窗只排除過去20日"] = {"次數": REPS_NEW, "D平均": float(NW["D"].mean()), "D範圍": [float(NW["D"].min()), float(NW["D"].max())],
                                         "CI不含0": int(NW["CI不含0"].sum()), "b′平均（逐位置）": {p: float(NW["b_" + p].mean()) for p in POS},
                                         "帳（30 次合計）": {"抽出": int(FNc[:, 0].sum()), "合併掉": int(FNc[:, 1].sum()), "斷點剔除": int(FNc[:, 2].sum()), "可抽日不足": int(FNc[:, 3].sum())}}
    print("[描述用假訊號臂] D′ 平均 {}｜CI 不含 0：{}／{}".format(pp_(NW["D"].mean()), int(NW["CI不含0"].sum()), REPS_NEW), flush=True)
    five = {"七位置": {}}
    for p in POS:
        e = E[E["pos"] == p]
        five["七位置"][p] = {**und[p], "R20扣成本": TU.summ(e["R"], e["T"], cal, w0), "X20對EWc": TU.summ(e["X"], e["T"], cal, w0)}
    s38 = TU.dstat(E, W38, "mon"); s62 = TU.dstat(E, W62, "mon")
    five["費氏位各自_b(F)−鄰位平均（只報）"] = {"38.2": {k: s38[k] for k in ("D", "lo", "hi")}, "61.8": {k: s62[k] for k in ("D", "lo", "hi")}}
    dep = pd.DataFrame([d for s in sids for d in ST[s]["depth"]], columns=["depth", "why"])

    def dist(x):
        x = x[np.isfinite(x)]; bins = np.floor(x * 20) / 20; mo = float(pd.Series(bins).value_counts().index[0])
        return {"n": int(len(x)), "中位": float(np.median(x)), "眾數區間": [mo, mo + 0.05], "p25": float(np.percentile(x, 25)), "p75": float(np.percentile(x, 75))}
    five["回撤深度"] = {"全部合格波段": dist(dep["depth"].to_numpy(float)), "以收盤>H0結束者": dist(dep.loc[dep["why"] == "收盤>H0", "depth"].to_numpy(float)),
                    "Bulkowski美股中位（只作對照）": 0.59}
    grp = {}
    for g_ in ("期初已在", "期中加入"):
        e = E[E["grp"] == g_]; s_ = TU.dstat(e, WD, "mon")
        grp[g_] = {"D": s_["D"], "lo": s_["lo"], "hi": s_["hi"], "分勝負": {p: int(((e["pos"] == p) & (e["y"] >= 0)).sum()) for p in POS}}
    yr = {}
    for y in sorted(E["mon"].str[:4].unique()):
        e = E[E["mon"].str[:4] == y]; s_ = TU.dstat(e, WD, "mon")
        yr[y] = {"D": s_["D"], "lo": s_["lo"], "hi": s_["hi"], "分勝負_min六位置": int(min(((e["pos"] == p) & (e["y"] >= 0)).sum() for p in FU.SIX))}
    five["期初已在／期中加入"] = grp; five["逐年"] = yr
    xs = np.array([FU.POS[p] * 100 for p in POS]); bs = np.array([und[p]["b"] for p in POS])
    slope = float(np.polyfit(xs, bs, 1)[0])
    five["§八先驗可否證句"] = {"七位置b對位置的OLS斜率（每10個百分點）": slope * 10, "斜率為負": bool(slope < 0),
                         "b(61.8)−鄰位平均": s62["D"], "|差|<3個百分點": bool(abs(s62["D"]) < 0.03), "b(38.2)−鄰位平均": s38["D"]}
    RES["§五必報"] = five
    dsc = {}
    s50 = TU.dstat(E, W50, "mon"); dsc["a_50%"] = {"D50": s50["D"], "lo": s50["lo"], "hi": s50["hi"]}
    b_ = {}
    for col, nm in (("y_b3", "±3%帶"), ("y_b8", "±8%帶")):
        e = E.assign(y=E[col]); s_ = TU.dstat(e, WD, "mon"); ne_, _, _ = neff_us(e, w0, cap)
        b_[nm] = {"D": s_["D"], "lo": s_["lo"], "hi": s_["hi"], "n_eff": ne_, "不分勝負比例": float((e["y"] == -1).mean())}
    for H in (10, 40):
        e = cat((5, H)); s_ = TU.dstat(e, WD, "mon"); ne_, _, _ = neff_us(e, w0, cap)
        b_["{}日窗".format(H)] = {"D": s_["D"], "lo": s_["lo"], "hi": s_["hi"], "n_eff": ne_, "不分勝負比例": float((e["y"] == -1).mean()), "保留": int(len(e))}
    dsc["b_判定帶與窗"] = b_
    c_ = {}
    for k in (3, 10):
        e = cat((k, 20)); s_ = TU.dstat(e, WD, "mon"); ne_, _, _ = neff_us(e, w0, cap)
        c_["k{}".format(k)] = {"D": s_["D"], "lo": s_["lo"], "hi": s_["hi"], "n_eff": ne_, "保留": int(len(e))}
    dsc["c_k"] = c_
    dd = E[E["d_ok"]]

    def dlin(e, col, wts, cl):
        d = e[e["pos"].isin(list(wts))]; P = list(wts)
        X = np.column_stack([(d["pos"] == p).to_numpy(float) for p in P]); y = d[col].to_numpy(float)
        Xi = np.linalg.inv(X.T @ X); beta = Xi @ X.T @ y; u = y - X @ beta
        sc = pd.DataFrame(X * u[:, None]).groupby(d[cl].to_numpy()).sum().to_numpy(); V = Xi @ (sc.T @ sc) @ Xi
        a = np.array([wts[p] for p in P]); Dv = float(a @ beta); se = float(np.sqrt(a @ V @ a))
        return {"D": Dv, "lo": Dv - 1.96 * se, "hi": Dv + 1.96 * se}
    dsc["d_交易版"] = {"進場筆數": int(len(dd)), "剔除_T+21超過窗尾": int(E["d_窗尾"].sum()), "剔除_T+1沒有K棒": int(E["d_T1停牌"].sum()),
                     "七位置X_d": {p: TU.summ(dd.loc[dd["pos"] == p, "Xd"], dd.loc[dd["pos"] == p, "T"], cal, w0) for p in POS},
                     "D_d": dlin(dd, "Xd", WD, "mon"), "同形_X20": dlin(E, "X", WD, "mon")}
    dsc["e_1.618延伸"] = "未測（登錄 §六 e）"
    RES["§六描述臂"] = dsc
    print("[§六] 50% {}（{}～{}）｜k3 {} k10 {}｜D_d {}".format(pp_(s50["D"]), pp_(s50["lo"]), pp_(s50["hi"]), pp_(c_["k3"]["D"]), pp_(c_["k10"]["D"]),
          pp_(dsc["d_交易版"]["D_d"]["D"])), flush=True)
    keep_cols = ["sid", "pos", "T", "mon", "tL", "tH", "conf", "wave_id", "L0", "H0", "p", "y", "y_b3", "y_b8", "y_alt", "g20", "EWc", "X", "R",
                 "d_ok", "gd", "EWo", "Xd", "Rd", "grp"]
    Eo = E[keep_cols].copy()
    for cc in ("T", "tL", "tH", "conf"):
        Eo[cc + "_date"] = [str(cal[t].date()) for t in Eo[cc]]
    p = os.path.join(WORK, "events_body_k5_H20.csv"); Eo.to_csv(p, index=False, encoding="utf-8"); shas.append((os.path.basename(p), len(Eo), sha256f(p)))
    RES["查核"] = CHK
    with io.open(os.path.join(OUT, "body_work_sha.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n"); w.writerow(["file（~/us_work/usu/，repo 外）", "rows", "sha256"]); w.writerows(shas)
    RES["逐筆檔sha（repo外）"] = {a: {"rows": b, "sha256": c} for a, b, c in shas}
    RES["耗時s"] = round(time.time() - t0)
    json.dump(RES, open(os.path.join(OUT, "body_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print("完成 {:.0f}s".format(time.time() - t0))


if __name__ == "__main__":
    main()
