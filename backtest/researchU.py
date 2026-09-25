# -*- coding: utf-8 -*-
"""PREREGU 本體（費波那契回撤：38.2／61.8 的止跌反彈，有沒有比旁邊的位置多）——判定量 D、CI、n_eff、出口、結果、§五 必報、
§六 描述臂 a～d、§七 假訊號臂（登錄那一種，200 次）＋ 描述用假訊號臂（同檔全窗，裁定線 seq159 §六 新預設）。
判準＝台股策略線 PREREGU seq1（sha 4ff4c1731fdded12）§三～§七。

事件：researchU_core.py 重新偵測（讀法 V1～V5；偵測器 fib_u.py 讀法 U1～U6）⇒ ⭐ 開算前先與頻率交出的 resultsU/events_*.csv
   五檔逐列比（sid、market、pos、T、tL、tH、conf、狀態），任一列不同 ⇒ 中止（未算任何反彈判定或報酬）。

⭐ 登錄沒逐字寫、本支的落地讀法（⛔ 在看任何本體結果之前寫在這裡；交件逐條列出）：
 B1 判定量的事件層級迴歸：y（反彈＝1／沒止住＝0；不分勝負 ⛔ 不進）對「位置虛擬變數（每個位置一個、無截距）」OLS ⇒ 係數 ＝ b(x)；
    D ＝ a'β，a ＝ 38.2、61.8 各 +½，30、45、55、70 各 −¼。SE ＝ √(a'Va)，V ＝ CR0 分群三明治（無小樣本修正，同 H1 Q5／research11.cl_stats）；
    主欄以 T 所在曆月分群、第二欄以波段（同檔同 t_H）分群。50 的事件不進主格迴歸（虛擬變數飽和 ⇒ 放不放都不改 D 與其 SE）。
 B2 n_eff ＝ min over 六位置 { min(該位置【分勝負】事件數, 該位置有分勝負事件的 20 日區段數) }（區段同 V5）；
    < 30 出口①／30～99 出口②／≥ 100 出口③；六位置中任一位置分勝負事件 < 30 ⇒ 結果④（併入出口①）。
 B3 §五「觸及後 20 日扣成本報酬」：R ＝ close(T+20)／close(T) − 1 − 0.585%（close(T+20) 缺 ⇒ ≤ T+20 最後一根收盤：停牌前收盤、下市者最後成交價）；
    「對同段 gate3 等權的超額」X ＝ (close(T+20)／close(T) − 1) − EWc_20(T)，EWc_20(d) ＝ d 日有收盤的全部 gate3 股票（含日後下市者）
    同式 close(d+20)／close(d) − 1 的等權平均（成本兩邊相消，同 PREREGM B3）。⚠ 進場用 T 收盤是「讀法」：觸及是盤中、收盤才確定位置。
 B4 描述臂 d（交易版）：同 PREREGM B1～B3：R_d ＝ px(T+21)／open(T+1) − 1 − 0.585%、X_d ＝ R_d −（EW_20(T+1) − 0.585%），
    EW 用 researchM.ew_open；T+1 停牌／開盤缺值／開盤漲停 ⇒ 該筆不進 d（另報件數）；需 T+21 ≤ 窗尾（另報件數）。
    d 的彙總：七位置各自平均 X_d，以及同 D 形狀的線性組合 D_d（對位置虛擬變數迴歸、月分群 CI）。
 B5 §七 假訊號臂（登錄）：r ＝ 0…199，種子 20260925＋r；從 [0.25, 0.75] 連續均勻抽 (a, b)，|a − b| < 0.10 ⇒ 同一個 rng 重抽；
    鄰位 ＝ a ± 0.075、b ± 0.075；六個位置各自照主格同一套（U1～U6、V1～V3）找觸及、合併、斷點、判定 ⇒ D_fake。
    百分位 ＝ D_fake < 真 D 的比例；x ＝ D_fake ≥ 真 D 的次數；真 D ≤ D_fake 的 95 百分位 ⇒ 結果② 句前加警語（只在結果② 時加）。
 B6 ⭐ 描述用假訊號臂（同檔、全窗不限月、排除真事件前後各 20 個交易日；⛔ 不計 N、不進判定）：
    加臂時點 ＝ 2026-09-25 18:11:52（台北；寫進本支之時。此時頻率已完成、本體尚未執行、⛔ 尚未讀到任何本體報酬或反彈比例）。
    每檔、每個位置 x：該檔 x 的主格保留真事件有 n 筆 ⇒ 從該檔「窗內可落日（有效 K 棒、low 非缺、T+20 ≤ 窗尾）且距該檔【任一位置】任一保留真事件
    > 20 個交易日（交易日曆）」的日子中不放回抽 n 天（不足 ⇒ 全取、另報）；第 i 天的位置價 p′ ＝ ρ_i × low(T′)，ρ_i ＝ 該檔 x 第 i 筆真事件的
    p／low(T)（依 T 排序配對；保留「位置價在當日低點之上多少」的形狀）；之後照主格同一順序（合併 20 日 → [T′, T′+20] 硬斷點）與同一判定 ⇒
    b′(x) 與 D′（同 B1 月分群 CI）。r ＝ 0…29，種子 [20260925＋r, crc32(sid)]（逐檔獨立 ⇒ 與行程分工無關）。
 B7 回撤深度（§五）：每個 conf 在窗內的合格波段，深度 ＝ (H0 − [t_H, 結束根] 內最低還原 low)／(H0 − L0)；報中位、5 個百分點一格的眾數區間；
    另報「以收盤 > H0 結束（回到上漲）」的波段（與 Bulkowski「回撤後續漲」的口徑最接近）。⛔ 只作對照。
 B8 逐年、上市／上櫃：以 T 的年／該檔快照 market 欄分組，D 與其月分群 CI、七位置 b(x)。
 B9 §八 先驗的可否證句：七位置 b(x) 對位置（百分點）的未加權 OLS 斜率；b(61.8) − 鄰位平均（百分點）對 3 個百分點。⛔ 只報。
"""
from __future__ import annotations
import os, sys, time, json, zlib
from multiprocessing import Pool
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchU_core as UC
from backtest import fib_u as FU
from backtest import selftest_fib_u as SFU
import researchM as RM                              # 只 import ew_open（同一件事只准一份實作）

H2, D, TR, UG, R11 = UC.H2, UC.D, UC.TR, UC.UG, UC.H2.R
OUT = "backtest/resultsU"
COST = H2.COST_RT
SEED = 20260925
REPS_REG, REPS_NEW = 200, 30
POS = list(FU.POS)
WD = {"38.2": 0.5, "61.8": 0.5, "30": -0.25, "45": -0.25, "55": -0.25, "70": -0.25}
W50 = {"50": 1.0, "45": -0.5, "55": -0.5}
W38 = {"38.2": 1.0, "30": -0.5, "45": -0.5}
W62 = {"61.8": 1.0, "55": -0.5, "70": -0.5}
_G = {}


def fake_positions(reps=REPS_REG):
    """B5：回 (reps, 6) 的比率：[a−.075, a, a+.075, b−.075, b, b+.075]。"""
    out = np.zeros((reps, 6)); ab = []
    for r in range(reps):
        rng = np.random.default_rng(SEED + r)
        while True:
            a, b = rng.uniform(0.25, 0.75, 2)
            if abs(a - b) >= 0.10:
                break
        out[r] = [a - 0.075, a, a + 0.075, b - 0.075, b, b + 0.075]; ab.append((a, b))
    return out, ab


def _init(cal, w0, w1, off, fr, mon):
    _G.update(cal=cal, w0=w0, w1=w1, off=off, fr=fr, mon=mon)


def _merge_brk(S, T, p, H=20):
    """V2 同一順序（已依 T 排序）：回保留的 (T, p) 與 (合併數, 斷點數)。"""
    keep_T, keep_p = [], []; t_keep = -10 ** 9; nm = nb = 0
    for t, q in zip(T, p):
        if t_keep < t <= t_keep + UC.MERGE:
            nm += 1; continue
        if UC.brk(S, int(t), int(t) + H):
            nb += 1; continue
        keep_T.append(int(t)); keep_p.append(float(q)); t_keep = t
    return np.array(keep_T, np.int64), np.array(keep_p), nm, nb


def work(args):
    sid, market = args
    cal, w0, w1, off, fr, mon = _G["cal"], _G["w0"], _G["w1"], _G["off"], _G["fr"], _G["mon"]
    S = UC.load(sid, market, cal, off)
    if S is None:
        return None
    n = len(cal); wE = w1 - 20
    det, cf = UC.detect_all(S, cal, w0, w1)
    o, l, c = S["o"], S["l"], S["c"]
    cff = pd.Series(c).ffill().to_numpy()
    okO = S["valid"] & np.isfinite(o) & (o > 0)
    px = np.where(okO, o, cff)
    res = {"sid": sid, "market": market, "c": c, "cff": cff, "o": o, "okO": okO, "px": px, "cfg": {}}
    for (k, H), v in cf.items():
        rows = v["rows"]
        if not rows:
            res["cfg"][(k, H)] = pd.DataFrame(); continue
        E = pd.DataFrame(rows)
        E["y"] = -9
        kp = (E["狀態"] == "保留").to_numpy()
        T = E["T"].to_numpy(np.int64); p = E["p"].to_numpy(float)
        E.loc[kp, "y"] = FU.outcome_vec(c, T[kp], p[kp], H, FU.BAND)
        if (k, H) == (5, 20):
            for nm_, band in (("y_b3", 0.03), ("y_b8", 0.08)):
                E[nm_] = -9; E.loc[kp, nm_] = FU.outcome_vec(c, T[kp], p[kp], H, band)
            # 閉區間讀法的另一種（≥／≤ 出帶）⇒ 只數兩種讀法的差異件數
            Tk, pk = T[kp], p[kp]
            idx = Tk[:, None] + np.arange(H + 1)[None, :]; C = c[idx]
            up = C >= (pk * 1.05)[:, None]; dn = C <= (pk * 0.95)[:, None]; an = up | dn
            f_ = np.argmax(an, axis=1); has = an.any(axis=1); ya = np.full(len(Tk), -1)
            ya[has] = np.where(up[np.arange(len(Tk)), f_][has], 1, 0)
            E["y_alt"] = -9; E.loc[kp, "y_alt"] = ya
            g = np.full(len(E), np.nan); g[kp] = cff[Tk + 20] / c[Tk] - 1.0
            E["g20"] = g
            # 描述臂 d（交易版）
            okd = kp & (T + 21 <= w1)
            t1 = np.minimum(T + 1, n - 1)
            trd = S["trd"][t1] & np.isfinite(o[t1]) & (o[t1] > 0)
            E["d_窗尾"] = kp & ~(T + 21 <= w1)
            E["d_T1停牌"] = okd & ~trd
            E["d_T1漲停開"] = okd & trd & S["up_o"][t1]
            dd = okd & trd & ~S["up_o"][t1]
            gd = np.full(len(E), np.nan); gd[dd] = px[T[dd] + 21] / o[T[dd] + 1] - 1.0
            E["gd"] = gd; E["d_ok"] = dd
        res["cfg"][(k, H)] = E
    # 回撤深度（B7）
    dep = []
    for W in det[5]["waves"]:
        if w0 <= W["conf"] <= wE:
            seg = l[W["tH"]:W["end"] + 1]
            mn = float(np.nanmin(seg)) if np.isfinite(seg).any() else np.nan
            dep.append(((W["H0"] - mn) / (W["H0"] - W["L0"]), W["why_end"]))
    res["depth"] = dep
    # ── §七 假訊號臂（登錄，B5）
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
            if not w_.any():
                continue
            Tc, pc = Tc[w_], pc[w_]
            o_ = np.argsort(Tc, kind="stable"); Tc, pc = Tc[o_], pc[o_]
            Tk, pk, _, _ = _merge_brk(S, Tc, pc)
            if len(Tk) == 0:
                continue
            y = FU.outcome_vec(c, Tk, pk)
            d_ = y >= 0
            np.add.at(acc[j, :, 0], mon[Tk[d_]], 1); np.add.at(acc[j, :, 1], mon[Tk[d_]], y[d_].astype(np.int32))
    res["fake_reg"] = acc
    # ── 描述用假訊號臂（B6）
    E5 = res["cfg"][(5, 20)]
    acc2 = np.zeros((REPS_NEW, len(POS), NM, 2), np.int32); cnt2 = np.zeros((REPS_NEW, 4), np.int64)   # 抽出、合併、斷點、不足
    if len(E5):
        K = E5[E5["狀態"] == "保留"]
        realT = np.sort(K["T"].to_numpy(np.int64))
        cand = np.flatnonzero(S["valid"] & np.isfinite(l)); cand = cand[(cand >= w0) & (cand <= wE)]
        if len(realT):
            i = np.searchsorted(realT, cand)
            dl = np.abs(cand - realT[np.clip(i - 1, 0, len(realT) - 1)]); dr = np.abs(realT[np.clip(i, 0, len(realT) - 1)] - cand)
            cand = cand[np.minimum(dl, dr) > 20]
        seed2 = zlib.crc32(sid.encode("utf-8"))
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
                pp = rho * l[dr_]
                Tk, pk, nm_, nb_ = _merge_brk(S, dr_, pp)
                cnt2[r, 0] += m; cnt2[r, 1] += nm_; cnt2[r, 2] += nb_
                if len(Tk) == 0:
                    continue
                y = FU.outcome_vec(c, Tk, pk)
                d_ = y >= 0
                np.add.at(acc2[r, pi, :, 0], mon[Tk[d_]], 1); np.add.at(acc2[r, pi, :, 1], mon[Tk[d_]], y[d_].astype(np.int32))
    res["fake_new"] = acc2; res["fake_new_cnt"] = cnt2
    return res


# ═════════════ 統計 ═════════════
def dstat(E, wts, cl):
    """B1：E 需有 pos、y（只取 0/1）、cl 欄；wts：{pos: 權重}。回 D、SE、b、各位置 n。"""
    d = E[E["pos"].isin(list(wts)) & (E["y"] >= 0)]
    P = list(wts)
    X = np.column_stack([(d["pos"] == p).to_numpy(float) for p in P])
    y = d["y"].to_numpy(float)
    XtX = X.T @ X
    if np.any(np.diag(XtX) == 0):
        return {"D": np.nan, "se": np.nan, "lo": np.nan, "hi": np.nan, "n": {p: int(XtX[i, i]) for i, p in enumerate(P)}}
    Xi = np.linalg.inv(XtX); beta = Xi @ X.T @ y; u = y - X @ beta
    g = d[cl].to_numpy()
    sc = pd.DataFrame(X * u[:, None]).groupby(g).sum().to_numpy()
    V = Xi @ (sc.T @ sc) @ Xi
    a = np.array([wts[p] for p in P])
    Dv = float(a @ beta); se = float(np.sqrt(a @ V @ a))
    return {"D": Dv, "se": se, "lo": Dv - 1.96 * se, "hi": Dv + 1.96 * se, "群數": int(len(sc)),
            "b": {p: float(beta[i]) for i, p in enumerate(P)}, "n": {p: int(XtX[i, i]) for i, p in enumerate(P)}}


def dstat_agg(A, wts_idx):
    """假訊號臂：A (P, NM, 2) 逐位置逐月 (n, 反彈數) ⇒ D 與月分群 CR0 SE（與 dstat 同一公式的彙總版）。wts_idx：[(位置列, 權重)]。"""
    nx = np.array([A[i, :, 0].sum() for i, _ in wts_idx], float); sx = np.array([A[i, :, 1].sum() for i, _ in wts_idx], float)
    if np.any(nx == 0):
        return np.nan, np.nan, np.nan, nx
    b = sx / nx; a = np.array([w for _, w in wts_idx])
    Dv = float(a @ b)
    gsum = sum(a[j] * (A[i, :, 1] - A[i, :, 0] * b[j]) / nx[j] for j, (i, _) in enumerate(wts_idx))
    se = float(np.sqrt((gsum ** 2).sum()))
    return Dv, se, b, nx


def neff(E, w0, pos=FU.SIX):
    out = {}
    for p in pos:
        d = E[(E["pos"] == p) & (E["y"] >= 0)]
        nb = int(np.minimum((d["T"] - w0) // UC.BLOCK, UC.CAP - 1).nunique()) if len(d) else 0
        out[p] = {"分勝負事件": int(len(d)), "區段": nb, "min": int(min(len(d), nb))}
    return min(v["min"] for v in out.values()), min(v["分勝負事件"] for v in out.values()), out


def verdict(s, ne, nmin):
    if nmin < 30:
        return "出口①", "結果④（事件 < 30，併入出口①：樣本不足以分辨）"
    if ne < 30:
        return "出口①", "—（出口①：樣本不足以分辨）"
    ex = "出口②" if ne < 100 else "出口③"
    if s["lo"] <= 0 <= s["hi"]:
        return ex, "結果①（測不出）"
    return ex, ("結果②（測得出（＋））" if s["D"] > 0 else "結果③（測得出（−））")


def summ(x, T, cal, w0):
    x = np.asarray(x, float); T = np.asarray(T, int); ok = np.isfinite(x); x, T = x[ok], T[ok]
    if len(x) == 0:
        return {"n": 0}
    cs = R11.cl_stats(x, np.array([str(cal[t])[:7] for t in T]))
    return {"n": int(len(x)), "平均": cs["mean"], "中位": cs["median"], "lo": cs["lo"], "hi": cs["hi"], "勝率": cs["win"], "最差": cs["worst"], "曆月數": cs["months"]}


def ew_close(C, CFF, H):
    """EWc_H(d) ＝ d 日有收盤的股票：cff(d+H)／c(d) − 1 的等權平均（B3）。C、CFF：n×S。"""
    n = C.shape[0]; out = np.full(n, np.nan)
    r = CFF[H:] / C[:n - H] - 1.0
    with np.errstate(invalid="ignore"):
        cnt = np.isfinite(r).sum(axis=1); s = np.nansum(r, axis=1)
    out[:n - H] = np.where(cnt > 0, s / np.maximum(cnt, 1), np.nan)
    return out


def selftest():
    """G1 0 報酬輸入（全體價格恆等）⇒ g＝0、EWc＝0、X＝0、R＝−0.585%；交易版 X_d＝0｜G2 dstat（矩陣三明治）＝ 逐筆影響函數迴圈（D、SE）、
    ＝ dstat_agg（彙總版）｜G3 ew_close 向量＝逐檔迴圈（停牌、下市、上市前）｜G4 假訊號位置：|a−b| ≥ 0.10、落在 [0.25, 0.75]。"""
    n, S_ = 60, 5
    C = np.full((n, S_), 20.0); CF = C.copy()
    ew = ew_close(C, CF, 20); T = 10
    g = CF[T + 20, 1] / C[T, 1] - 1; X = g - ew[T]; R = g - COST
    Oc = np.full((n, S_), 20.0); e2 = RM.ew_open(Oc, np.ones((n, S_), bool), Oc, 20)
    Xd = (Oc[T + 21, 1] / Oc[T + 1, 1] - 1 - COST) - (e2[T + 1] - COST)
    assert g == 0 and ew[T] == 0 and X == 0 and abs(R + COST) < 1e-15 and Xd == 0, (g, ew[T], X, R, Xd)
    rng = np.random.default_rng(11)
    N = 3000
    E = pd.DataFrame({"pos": rng.choice(POS, N), "y": rng.integers(0, 2, N), "mon": rng.integers(0, 40, N)})
    E.loc[E["pos"] == "38.2", "y"] = (rng.random((E["pos"] == "38.2").sum()) < 0.7).astype(int)
    s = dstat(E, WD, "mon")
    bm = E.groupby("pos")["y"].mean()
    Dm = 0.5 * (bm["38.2"] - 0.5 * (bm["30"] + bm["45"])) + 0.5 * (bm["61.8"] - 0.5 * (bm["55"] + bm["70"]))
    infl = np.zeros(N)
    for i, (p, y) in enumerate(zip(E["pos"], E["y"])):
        if p in WD:
            infl[i] = WD[p] * (y - bm[p]) / (E["pos"] == p).sum()
    se_l = np.sqrt((pd.Series(infl).groupby(E["mon"]).sum() ** 2).sum())
    A = np.zeros((len(POS), 40, 2), np.int64)
    for p, y, m in zip(E["pos"], E["y"], E["mon"]):
        A[POS.index(p), m, 0] += 1; A[POS.index(p), m, 1] += y
    Da, sa, _, _ = dstat_agg(A, [(POS.index(p), w) for p, w in WD.items()])
    assert abs(s["D"] - Dm) < 1e-12 and abs(s["se"] - se_l) < 1e-12 and abs(Da - Dm) < 1e-12 and abs(sa - se_l) < 1e-12, (s, Dm, se_l, Da, sa)
    # G3
    C = 30 * np.exp(rng.normal(0, 0.02, (80, 6)).cumsum(axis=0)); C[10:13, 1] = np.nan; C[50:, 2] = np.nan; C[:30, 3] = np.nan
    CF = pd.DataFrame(C).ffill().to_numpy(); ew = ew_close(C, CF, 20); worst = 0
    for d in range(60):
        v = [CF[d + 20, j] / C[d, j] - 1 for j in range(6) if np.isfinite(C[d, j])]
        worst = max(worst, abs(ew[d] - sum(v) / len(v)))
    assert worst < 1e-14, worst
    fr, ab = fake_positions()
    assert all(abs(a - b) >= 0.10 and 0.25 <= a <= 0.75 and 0.25 <= b <= 0.75 for a, b in ab) and np.allclose(fr[:, 2] - fr[:, 0], 0.15)
    msg = ("G1 0 報酬輸入 ⇒ g＝0、EWc＝0、X＝0、R＝−0.585%、交易版 X_d＝0｜G2 D 與月分群 SE：矩陣三明治＝逐筆影響函數＝彙總版（差 < 1e-12）｜"
           "G3 EWc 向量＝逐檔迴圈（停牌／下市／上市前）差 {:.1e}｜G4 假訊號 200 組位置皆 |a−b| ≥ 0.10、落在 [0.25, 0.75]").format(worst)
    print("✅ 本體自測：" + msg, flush=True)
    return msg


def pp_(x, d=2):
    return "—" if x is None or not np.isfinite(x) else "{:+.{}f}pp".format(x * 100, d)


def main():
    t0 = time.time()
    print("[時點] 本體開跑 {}（描述用假訊號臂已於 18:11:52 寫進本支）".format(time.strftime("%F %T")), flush=True)
    fx = SFU.run_all(); fx2 = selftest()
    procs = int(sys.argv[sys.argv.index("--procs") + 1]) if "--procs" in sys.argv else 2
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    reps = int(sys.argv[sys.argv.index("--reps") + 1]) if "--reps" in sys.argv else REPS_REG
    cal = D.load_calendar(); n = len(cal)
    w0, w1 = UC.win_index(cal); wE = w1 - 20
    base = cal[w0].year * 12 + cal[w0].month
    mon = np.array([d.year * 12 + d.month - base for d in cal]); mon = np.clip(mon, 0, None)
    stocks = pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(stocks)
    if lim:
        U = U.head(lim)
    off = TR.load_official()
    fr, ab = fake_positions(reps)
    NM = int(mon.max() + 1)
    print("[資料] 快照 {}｜判定窗 [{}, {}]｜T 可落 [{}, {}]｜gate3 {:,} 檔｜假訊號 {} 次".format(
        UC.SHA[:10], UC.W0, UC.W1, cal[w0].date(), cal[wE].date(), len(U), reps), flush=True)
    ST = {}
    FR = np.zeros((reps * 6, NM, 2), np.int64); FN = np.zeros((REPS_NEW, len(POS), NM, 2), np.int64); FNc = np.zeros((REPS_NEW, 4), np.int64)
    with Pool(procs, initializer=_init, initargs=(cal, w0, w1, off, fr, mon)) as pool:
        for r in pool.imap_unordered(work, list(zip(U["stock_id"], U["market"])), chunksize=4):
            if r is None:
                continue
            FR += r.pop("fake_reg"); FN += r.pop("fake_new"); FNc += r.pop("fake_new_cnt")
            ST[r["sid"]] = r
    sids = sorted(ST)
    print("[讀檔＋偵測＋假訊號] 可用 {:,} 檔｜{:.0f}s".format(len(ST), time.time() - t0), flush=True)
    os.makedirs(OUT, exist_ok=True)
    CHK = {"fixture_偵測器": fx, "fixture_本體": fx2}

    # ── 查核 1：與頻率交出的事件檔逐列相同（⛔ 在任何反彈判定／報酬彙總之前）
    rows_eq = {}
    for k, H in UC.CFGS:
        nm = UC.cfg_name(k, H)
        parts = []
        for s in sids:
            E = ST[s]["cfg"][(k, H)]
            if len(E):
                parts.append(pd.DataFrame({"sid": s, "market": ST[s]["market"], "pos": E["pos"], "T": [str(cal[t].date()) for t in E["T"]],
                                           "tL": [str(cal[t].date()) for t in E["tL"]], "tH": [str(cal[t].date()) for t in E["tH"]],
                                           "conf": [str(cal[t].date()) for t in E["conf"]], "狀態": E["狀態"]}))
        mine = pd.concat(parts, ignore_index=True)
        ref = pd.read_csv(os.path.join(OUT, "events_{}.csv".format(nm)), dtype=str)
        if lim:
            ref = ref[ref["sid"].isin(sids)].reset_index(drop=True)
        same = mine.shape == ref.shape and bool((mine.astype(str).values == ref.astype(str).values).all())
        rows_eq[nm] = {"列數_本支": int(len(mine)), "列數_頻率": int(len(ref)), "逐列相同": same}
        print("[查核1 事件檔逐列] {}：{:,}／{:,} ⇒ {}".format(nm, len(mine), len(ref), "相同" if same else "⛔ 不同"), flush=True)
        if not same:
            json.dump(rows_eq, open(os.path.join(OUT, "ABORT_rows.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            raise SystemExit("⛔ 重新偵測與頻率事件檔不同：{} ⇒ 中止（未彙總任何反彈判定或報酬）".format(nm))
    CHK["事件檔逐列相同"] = rows_eq

    # ── 基準
    Cm = np.column_stack([ST[s]["c"] for s in sids]); CFm = np.column_stack([ST[s]["cff"] for s in sids])
    Om = np.column_stack([ST[s]["o"] for s in sids]); OKm = np.column_stack([ST[s]["okO"] for s in sids]); PXm = np.column_stack([ST[s]["px"] for s in sids])
    EWc = ew_close(Cm, CFm, 20); EWo = RM.ew_open(Om, OKm, PXm, 20)
    del Cm, CFm, Om, OKm, PXm

    def cat(key):
        parts = []
        for s in sids:
            E = ST[s]["cfg"][key]
            if len(E):
                parts.append(E.assign(sid=s, market=ST[s]["market"]))
        E = pd.concat(parts, ignore_index=True)
        E = E[E["狀態"] == "保留"].copy()
        E["mon"] = [str(cal[t])[:7] for t in E["T"]]; E["wave_id"] = E["sid"] + "|" + E["tH"].astype(str)
        return E

    E = cat((5, 20))
    E["EWc"] = EWc[E["T"].to_numpy()]; E["X"] = E["g20"] - E["EWc"]; E["R"] = E["g20"] - COST
    E["EWo"] = [EWo[t + 1] for t in E["T"]]; E["Xd"] = E["gd"] - E["EWo"]; E["Rd"] = E["gd"] - COST
    t_first = time.strftime("%F %T")
    print("[時點] 本體第一次彙總反彈判定／報酬 {}".format(t_first), flush=True)
    RES = {"快照": UC.SHA, "判定窗": [UC.W0, UC.W1], "gate3母體": int(len(U)), "可用檔數": len(ST), "成本": COST,
           "時點": {"描述用假訊號臂加入": "2026-09-25 18:11:52", "本體第一次彙總反彈判定／報酬（程式）": t_first}}

    # ── 判定格（§三、§四）
    sm = dstat(E, WD, "mon"); sw = dstat(E, WD, "wave_id")
    ne, nmin, ned = neff(E, w0)
    ex, rs = verdict(sm, ne, nmin)
    und = {p: {"保留": int((E["pos"] == p).sum()), "分勝負": int(((E["pos"] == p) & (E["y"] >= 0)).sum()),
               "反彈": int(((E["pos"] == p) & (E["y"] == 1)).sum()), "沒止住": int(((E["pos"] == p) & (E["y"] == 0)).sum()),
               "不分勝負": int(((E["pos"] == p) & (E["y"] == -1)).sum())} for p in POS}
    for p in POS:
        und[p]["b"] = und[p]["反彈"] / max(1, und[p]["分勝負"]); und[p]["不分勝負比例"] = und[p]["不分勝負"] / max(1, und[p]["保留"])
    J = {"D": sm["D"], "lo_月": sm["lo"], "hi_月": sm["hi"], "se_月": sm["se"], "曆月數": sm["群數"],
         "lo_波段": sw["lo"], "hi_波段": sw["hi"], "se_波段": sw["se"], "波段群數": sw["群數"],
         "n_eff": ne, "n_eff明細": ned, "出口": ex, "結果": rs, "各位置": und,
         "帶緣兩種讀法差異件數（閉區間 vs ≥／≤）": int((E["y"] != E["y_alt"]).sum())}
    print("[判定格] D {}（月 CI {} ～ {}；波段 CI {} ～ {}）｜n_eff {}｜{} {}".format(
        pp_(sm["D"]), pp_(sm["lo"]), pp_(sm["hi"]), pp_(sw["lo"]), pp_(sw["hi"]), ne, ex, rs), flush=True)
    print("   b(x)：" + "｜".join("{} {:.4f}（{:,}，不分 {:.1%}）".format(p, und[p]["b"], und[p]["分勝負"], und[p]["不分勝負比例"]) for p in POS), flush=True)

    # ── §七 假訊號臂（登錄）
    fk = []
    for r in range(reps):
        A = FR[r * 6:(r + 1) * 6]
        Dv, se, b, nx = dstat_agg(A, [(1, 0.5), (0, -0.25), (2, -0.25), (4, 0.5), (3, -0.25), (5, -0.25)])
        fk.append({"r": r, "種子": SEED + r, "a": ab[r][0], "b": ab[r][1], "D": Dv, "lo": Dv - 1.96 * se, "hi": Dv + 1.96 * se,
                   "n_min": int(nx.min()), "CI不含0": bool(not (Dv - 1.96 * se <= 0 <= Dv + 1.96 * se))})
    FK = pd.DataFrame(fk); FK.to_csv(os.path.join(OUT, "fake_arm_registered.csv"), index=False, encoding="utf-8")
    fD = FK["D"].to_numpy(); p95 = float(np.percentile(fD, 95))
    xge = int((fD >= sm["D"]).sum())
    fake = {"次數": reps, "真D百分位": float((fD < sm["D"]).mean() * 100), "D_fake≥真D的次數x": xge, "D_fake的95百分位": p95,
            "D_fake平均": float(fD.mean()), "D_fake範圍": [float(fD.min()), float(fD.max())], "D_fake的p5": float(np.percentile(fD, 5)),
            "CI不含0的次數（附帶）": int(FK["CI不含0"].sum()),
            "真D未超過95百分位": bool(sm["D"] <= p95)}
    fake["警語"] = ("⚠ 隨機兩個位置也有 {}／{} 同樣好".format(xge, reps) if fake["真D未超過95百分位"] else "（真 D 超過 95 百分位 ⇒ 不加警語）")
    J["假訊號臂_登錄"] = fake
    RES["判定格"] = J
    print("[§七 假訊號臂] 真 D 百分位 {:.1f}｜x＝{}／{}｜95 百分位 {}｜{}".format(fake["真D百分位"], xge, reps, pp_(p95), fake["警語"]), flush=True)

    # ── 描述用假訊號臂（B6）
    nw = []
    for r in range(REPS_NEW):
        A = FN[r]
        Dv, se, b, nx = dstat_agg(A, [(POS.index(p), w) for p, w in WD.items()])
        bb = {p: float(A[i, :, 1].sum() / max(1, A[i, :, 0].sum())) for i, p in enumerate(POS)}
        nw.append({"r": r, "D": Dv, "lo": Dv - 1.96 * se, "hi": Dv + 1.96 * se, "CI不含0": bool(not (Dv - 1.96 * se <= 0 <= Dv + 1.96 * se)),
                   **{"b_" + p: bb[p] for p in POS}, **{"n_" + p: int(A[i, :, 0].sum()) for i, p in enumerate(POS)}})
    NW = pd.DataFrame(nw); NW.to_csv(os.path.join(OUT, "fake_arm_samestock.csv"), index=False, encoding="utf-8")
    RES["描述用假訊號臂_同檔全窗"] = {"次數": REPS_NEW, "D平均": float(NW["D"].mean()), "D範圍": [float(NW["D"].min()), float(NW["D"].max())],
                               "CI不含0": int(NW["CI不含0"].sum()),
                               "b′平均（逐位置）": {p: float(NW["b_" + p].mean()) for p in POS},
                               "真b − b′平均（逐位置）": {p: float(und[p]["b"] - NW["b_" + p].mean()) for p in POS},
                               "帳（30 次合計）": {"抽出": int(FNc[:, 0].sum()), "合併掉": int(FNc[:, 1].sum()), "斷點剔除": int(FNc[:, 2].sum()), "可抽日不足": int(FNc[:, 3].sum())}}
    print("[描述用假訊號臂] D′ 平均 {}｜CI 不含 0：{}／{}｜b′(38.2) {:.4f} b′(61.8) {:.4f}".format(
        pp_(NW["D"].mean()), int(NW["CI不含0"].sum()), REPS_NEW, NW["b_38.2"].mean(), NW["b_61.8"].mean()), flush=True)

    # ── §五 必報
    five = {}
    pos_tab = {}
    for p in POS:
        e = E[E["pos"] == p]
        pos_tab[p] = {**und[p], "R20扣成本": summ(e["R"], e["T"], cal, w0), "X20對EWc": summ(e["X"], e["T"], cal, w0)}
    five["七位置"] = pos_tab
    s38 = dstat(E, W38, "mon"); s62 = dstat(E, W62, "mon")
    five["費氏位各自_b(F)−鄰位平均（只報）"] = {"38.2": {k: s38[k] for k in ("D", "lo", "hi")}, "61.8": {k: s62[k] for k in ("D", "lo", "hi")}}
    dep = pd.DataFrame([d for s in sids for d in ST[s]["depth"]], columns=["depth", "why"])
    def dist(x):
        x = x[np.isfinite(x)]
        bins = np.floor(x * 20) / 20
        vc = pd.Series(bins).value_counts()
        mo = float(vc.index[0])
        return {"n": int(len(x)), "中位": float(np.median(x)), "眾數區間": [mo, mo + 0.05], "p25": float(np.percentile(x, 25)), "p75": float(np.percentile(x, 75)),
                "≤100%的中位": float(np.median(x[x <= 1.0])) if (x <= 1).any() else None}
    five["回撤深度"] = {"全部合格波段": dist(dep["depth"].to_numpy(float)), "以收盤>H0結束者": dist(dep.loc[dep["why"] == "收盤>H0", "depth"].to_numpy(float)),
                    "Bulkowski美股中位（只作對照）": 0.59}
    grp = {}
    for mk, nm in (("twse", "上市"), ("tpex", "上櫃")):
        e = E[E["market"] == mk]; s_ = dstat(e, WD, "mon")
        grp[nm] = {"D": s_["D"], "lo": s_["lo"], "hi": s_["hi"], "b": {p: float(e.loc[(e["pos"] == p) & (e["y"] >= 0), "y"].mean()) for p in POS},
                   "分勝負": {p: int(((e["pos"] == p) & (e["y"] >= 0)).sum()) for p in POS}}
    yr = {}
    for y in sorted(E["mon"].str[:4].unique()):
        e = E[E["mon"].str[:4] == y]; s_ = dstat(e, WD, "mon")
        yr[y] = {"D": s_["D"], "lo": s_["lo"], "hi": s_["hi"], "b": {p: float(e.loc[(e["pos"] == p) & (e["y"] >= 0), "y"].mean()) for p in POS},
                 "分勝負_min六位置": int(min(((e["pos"] == p) & (e["y"] >= 0)).sum() for p in FU.SIX))}
    five["上市上櫃"] = grp; five["逐年"] = yr
    xs = np.array([FU.POS[p] * 100 for p in POS]); bs = np.array([und[p]["b"] for p in POS])
    slope = float(np.polyfit(xs, bs, 1)[0])
    five["§八先驗可否證句"] = {"七位置b對位置的OLS斜率（每百分點）": slope, "每10個百分點": slope * 10, "斜率為負": bool(slope < 0),
                         "b(61.8)−鄰位平均": s62["D"], "|差|<3個百分點": bool(abs(s62["D"]) < 0.03),
                         "b(38.2)−鄰位平均": s38["D"]}
    RES["§五必報"] = five
    print("[§五] 回撤深度中位 {:.3f}（收盤>H0 結束者 {:.3f}）｜斜率 {:+.5f}／百分點｜上市 D {} 上櫃 D {}".format(
        five["回撤深度"]["全部合格波段"]["中位"], five["回撤深度"]["以收盤>H0結束者"]["中位"], slope, pp_(grp["上市"]["D"]), pp_(grp["上櫃"]["D"])), flush=True)

    # ── §六 描述臂
    dsc = {}
    s50 = dstat(E, W50, "mon")
    dsc["a_50%"] = {"D50": s50["D"], "lo": s50["lo"], "hi": s50["hi"], "b": s50["b"]}
    b_ = {}
    for col, nm in (("y_b3", "±3%帶"), ("y_b8", "±8%帶")):
        e = E.assign(y=E[col]); s_ = dstat(e, WD, "mon"); ne_, nm_, _ = neff(e, w0)
        b_[nm] = {"D": s_["D"], "lo": s_["lo"], "hi": s_["hi"], "n_eff": ne_, "b": s_["b"],
                  "不分勝負比例": float((e["y"] == -1).mean())}
    for H in (10, 40):
        e = cat((5, H)); s_ = dstat(e, WD, "mon"); ne_, _, _ = neff(e, w0)
        b_["{}日窗".format(H)] = {"D": s_["D"], "lo": s_["lo"], "hi": s_["hi"], "n_eff": ne_, "b": s_["b"], "不分勝負比例": float((e["y"] == -1).mean()), "保留": int(len(e))}
    dsc["b_判定帶與窗"] = b_
    c_ = {}
    for k in (3, 10):
        e = cat((k, 20)); s_ = dstat(e, WD, "mon"); ne_, _, _ = neff(e, w0)
        c_["k{}".format(k)] = {"D": s_["D"], "lo": s_["lo"], "hi": s_["hi"], "n_eff": ne_, "b": s_["b"], "保留": int(len(e))}
    dsc["c_k"] = c_
    dd = E[E["d_ok"]]
    d_ = {"進場筆數": int(len(dd)), "剔除_T+21超過窗尾": int(E["d_窗尾"].sum()), "剔除_T+1停牌或開盤缺": int(E["d_T1停牌"].sum()),
          "剔除_T+1開盤漲停": int(E["d_T1漲停開"].sum()), "七位置": {}}
    for p in POS:
        e = dd[dd["pos"] == p]
        d_["七位置"][p] = {"X_d": summ(e["Xd"], e["T"], cal, w0), "平均R_d": float(e["Rd"].mean()), "n": int(len(e))}
    ed = dd.assign(y=0.0)
    # D_d：以 X_d 當 y 做同一個位置虛擬變數迴歸（dstat 只取 y ≥ 0 ⇒ 另寫一份不過濾的）
    def dlin(e, col, wts, cl):
        d = e[e["pos"].isin(list(wts))]; P = list(wts)
        X = np.column_stack([(d["pos"] == p).to_numpy(float) for p in P]); y = d[col].to_numpy(float)
        Xi = np.linalg.inv(X.T @ X); beta = Xi @ X.T @ y; u = y - X @ beta
        sc = pd.DataFrame(X * u[:, None]).groupby(d[cl].to_numpy()).sum().to_numpy(); V = Xi @ (sc.T @ sc) @ Xi
        a = np.array([wts[p] for p in P]); Dv = float(a @ beta); se = float(np.sqrt(a @ V @ a))
        return {"D": Dv, "lo": Dv - 1.96 * se, "hi": Dv + 1.96 * se}
    d_["D_d（X_d 的同形線性組合）"] = dlin(dd, "Xd", WD, "mon")
    d_["同形_X20（§五 收盤進場版）"] = dlin(E, "X", WD, "mon")
    dsc["d_交易版"] = d_
    dsc["e_1.618延伸"] = "未測（登錄 §六 e）"
    RES["§六描述臂"] = dsc
    print("[§六] 50%：D50 {}（{} ～ {}）｜k3 D {}／k10 D {}｜D_d {}".format(pp_(s50["D"]), pp_(s50["lo"]), pp_(s50["hi"]),
          pp_(c_["k3"]["D"]), pp_(c_["k10"]["D"]), pp_(d_["D_d（X_d 的同形線性組合）"]["D"])), flush=True)

    # ── 逐筆檔
    keep_cols = ["sid", "market", "pos", "T", "mon", "tL", "tH", "conf", "wave_id", "L0", "H0", "p", "y", "y_b3", "y_b8", "y_alt",
                 "g20", "EWc", "X", "R", "d_ok", "gd", "EWo", "Xd", "Rd"]
    Eo = E[keep_cols].copy()
    for cc in ("T", "tL", "tH", "conf"):
        Eo[cc + "_date"] = [str(cal[t].date()) for t in Eo[cc]]
    Eo.to_csv(os.path.join(OUT, "events_body_k5_H20.csv"), index=False, encoding="utf-8")
    for k, H in UC.CFGS[1:]:
        e = cat((k, H))[["sid", "market", "pos", "T", "mon", "wave_id", "y"]]
        e.to_csv(os.path.join(OUT, "events_body_{}.csv".format(UC.cfg_name(k, H))), index=False, encoding="utf-8")

    # ── 查核：獨立路（不 import 共用讀檔）
    import researchU_check as UCK
    rng = np.random.default_rng(SEED)
    ii = rng.choice(len(E), size=20, replace=False)
    pick = []
    for i in ii:
        r = E.iloc[int(i)]
        pick.append({"sid": r["sid"], "pos": r["pos"], "T": str(cal[int(r["T"])].date()), "tL": str(cal[int(r["tL"])].date()),
                     "tH": str(cal[int(r["tH"])].date()), "conf": str(cal[int(r["conf"])].date()), "p": float(r["p"]), "y": int(r["y"]),
                     "g20": float(r["g20"]), "EWc": float(r["EWc"]), "gd": (float(r["gd"]) if r["d_ok"] else None)})
    CHK["獨立路"] = UCK.run(pick, sids, n_days=5)
    print("[查核 獨立路] 20 筆：p 最大相對差 {:.1e}｜y 不同 {}｜g20 最大差 {:.1e}｜交易版 {:.1e}｜基準 {} 天最大差 {:.1e}｜判 {}".format(
        CHK["獨立路"]["p最大相對差"], CHK["獨立路"]["y不同"], CHK["獨立路"]["g20最大差"], CHK["獨立路"]["gd最大差"],
        CHK["獨立路"]["基準天數"], CHK["獨立路"]["基準最大差"], CHK["獨立路"]["判"]), flush=True)
    RES["查核"] = CHK
    RES["時點"]["本體完成"] = time.strftime("%F %T")
    json.dump(RES, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print("完成 {:.0f}s".format(time.time() - t0))


if __name__ == "__main__":
    main()
