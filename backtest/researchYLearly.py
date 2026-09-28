# -*- coding: utf-8 -*-
"""營量 v1 提早一天、T 日中午買（使用者提議；描述臂：不計 N、不改任何判定）。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLearly [--procs 2]
    簡短查核：~/tw-p16/.venv/bin/python backtest/researchYLearly_check.py

使用者原話（逐字）：「如果前兩天準備好即將達成的個股，在達成前一天中午左右買進！（或許有可能是差一點點，然後算61天！？）」
⭐ 先驗提醒：本專案 回測 研究十二「早鳥不優於追高」。
⚠ 逐字標：「中午價以當日均價近似」（只有日線）；完美預知臂逐字標「含前視、不可執行」。
═══ 規則（協調者轉述）＋ 本線讀法（S 標；看數字前寫死）═══
 三臂（營量 T1＋stop_force、20 檔、relvol 排序、H60 同一出場根）：
   原版     營量 v1（T 收盤成立 ⇒ T＋1 開盤買、第 T＋60 根收盤出）
   完美預知 同一批訊號（T 收盤真的成立的），改在 T 日以均價買；出場根同原版（＝ 從 T 算第 61 根）【含前視、不可執行】
   可執行   T−1 收盤後：營收已成立（AND 營收條件，讀 T−1 當下）＋ 5 取 3 恰 2 分 ＋「最容易補的那條未達條件」所需隔日收盤漲幅 ≤ x
            ⇒ T 日均價買，不管 T 收盤有沒有成立；第 T＋60 根收盤出（抱 61 根）；x ∈ {3, 5, 10%}
 S1 中午價 ＝ 當日成交額 ÷ 成交量 × 還原因子（還原收盤 ÷ 未還原收盤），夾到當日還原 [最低, 最高]（大宗／盤後讓均價落在區間外的根數另報）
    敏感度：researchSlip C4 的 (開＋高＋低＋收)÷4 另跑一組（協調者寫「同 researchSlip C4」，而 C4 實際是四價平均 ⇒ 兩種都報、主表用成交額÷成交量）
 S2 「5 取 3 恰 2 分」＝ research11.stock_features 主格同一套條件、在 T−1 那根算；T−1 那根要是 stock_features 的合格根（eligible）
 S3 所需隔日漲幅（T 收盤 ÷ T−1 收盤 − 1），只對 T−1 沒達的條件算：
      c1 20 日漲幅 ≥ 30%   ⇒ 1.3 × 收[T−20] ÷ 收[T−1] − 1
      c2 20 日內漲停 ≥ 3 次 ⇒ 前 19 根已有 2 次 ⇒ T 要收漲停：漲停價(未還原收[T−1]) ÷ 未還原收[T−1] − 1；不到 2 次 ⇒ 補不到（∞）
      c3 成交額 ≥ 前 20 日均 3 倍 ⇒ 不是價格條件 ⇒ ∞（⛔ 不算「差一點點」；讀法）
      c4 收 ＞ 100 日均   ⇒ (收[T−99..T−1] 合計 ÷ 99) ÷ 收[T−1] − 1
      c5 收 ≥ 250 日最高 ⇒ max(收[T−249..T−1]) ÷ 收[T−1] − 1
    「最容易」＝ 所需漲幅最小的那條；可以 ≤ 0（視窗移動後不用漲就達）
 S4 可執行臂同檔去重 ＝ 營量 v1 的 20 根（選入根 − 上次選入根 ＞ 20）；relvol ＝ T−1 成交額 ÷ 前 60 根中位數（T−1 收盤後可得 ⇒ 不需退到 amt_ratio）
 S5 出場 ＝ 第 T＋60 根收盤（fixed_exit 同一套壞根規則＋T1 資料尾補＋早年 R8 截）；g ＝ 出場收盤 ÷ T 日中午價 − 1
    完美預知臂 g ＝ (1＋原 g_H60) × 原進場開盤 ÷ T 日中午價 − 1（出場根、截尾一字不改）
 S6 引擎一字不動：只換 sig 的 entry_pos／g 與 opens（進場價）字典；同日順序照引擎（先出場、後進場）
 S7 「當天收盤真的成立」＝ T 那根 eligible ＋ 5 取 3 ≥ 3 ＋ AND 營收（讀 T 當下）；另報「在營量 AND 訊號表裡」（含 20 根去重）
 閘：原版 ＝ resultsT1fix c13 t1（主）／resultsYLexit3 營量v1 種子 0（主、早年）；原版換成擴充字典後 eq_sha 不變；
     本支重算的 AND 訊號 (sid, k) ＝ 營量訊號表（主窗逐筆相同）；營量不抽籤 ⇒ 1 顆
輸出 backtest/resultsYLearly/
"""
from __future__ import annotations

import argparse
import html
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import rerun17 as RR
from backtest import research11 as R11
from backtest import research13 as R13
from backtest import researchYLexit as YX
from backtest import researchYLexit3_b as YB
from backtest import universe_gate as UG
from backtest import chart_svg as CS

OUT = "backtest/resultsYLearly"
F_HTML = "營量提早一天中午買_20260928.html"
COST = R11.COST
RAW = "如果前兩天準備好即將達成的個股，在達成前一天中午左右買進！（或許有可能是差一點點，然後算61天！？）"
TAG_PX = "中午價以當日均價近似"
TAG_PF = "含前視、不可執行"
PRIOR = "本專案 回測 研究十二「早鳥不優於追高」"
XS = (0.03, 0.05, 0.10)
C1, C3, DD = R11.MAIN_CELL
STALE = R13.STALE_MAX
CN = ("c1", "c2", "c3", "c4", "c5")
CNAME = {"c1": "20 日漲 30%", "c2": "漲停 3 次", "c3": "量 3 倍", "c4": "站上百日線", "c5": "創 250 日高"}
_G: dict = {}
_W: dict = {}


def xname(x):
    return f"x{int(round(x * 100))}"


# ═════════════ 每檔掃描（T−1 名單、T 成立與否、均價） ═════════════
def feats(B):
    idx, c, amt, up, skip, next_bad = (B[k] for k in ("idx", "c", "amt", "up", "skip", "next_bad"))
    n = len(idx); ar = np.arange(n)
    ret20 = np.array(c / np.roll(c, 20) - 1, dtype=float); ret20[:20] = np.nan
    nup20 = pd.Series(up.astype(int)).rolling(20, min_periods=20).sum().to_numpy(float)
    amt_prev20 = np.array(R11._roll_mean(np.roll(amt, 1), 20), dtype=float); amt_prev20[:21] = np.nan
    amt_ratio = amt / amt_prev20
    ma100 = R11._roll_mean(c, 100); hi250 = R11._roll_max(c, 250)
    cond = np.vstack([ret20 >= C1, nup20 >= 3, amt_ratio >= C3, c > ma100, c >= hi250])
    score = cond.sum(0)
    nb_sig = np.array([next_bad[max(0, k - 20)] for k in range(n)])
    eligible = (ar >= 249) & ~skip & ~np.isnan(ma100) & ~np.isnan(amt_ratio)
    eligible &= nb_sig > ar
    return cond, score, eligible, nb_sig, amt_ratio


def scan(args):
    sid, mk = args
    cal = _G["cal"]; n0 = len(cal); w0, w1 = _G["w0"], _G["w1"]
    B = R11.load_bars(sid, mk, cal)
    if B is None:
        return None
    idx, o, c, h, l, amt, rc, df = (B[k] for k in ("idx", "o", "c", "h", "l", "amt", "rc", "df"))
    n = len(idx)
    vol = pd.to_numeric(df["volume"], errors="coerce").to_numpy(float)[idx]
    with np.errstate(invalid="ignore", divide="ignore"):
        vw0 = np.where(vol > 0, amt / vol * c / rc, np.nan)
    out_rng = int(np.nansum((vw0 < l * (1 - 1e-9)) | (vw0 > h * (1 + 1e-9))))
    vw = np.clip(vw0, l, h)
    o4 = (o + h + l + c) / 4.0
    cond, score, eligible, nb_sig, amt_ratio = feats(B)
    sp, hi = _G["PAN"].get(sid, (np.zeros(0, int), np.zeros(0, bool)))

    def andf(pos):
        j = int(np.searchsorted(sp, pos, side="right")) - 1
        return bool(j >= 0 and pos - sp[j] <= STALE and hi[j])
    # 營量 3/5 主格（去重 20）＋ AND ⇒ 與訊號表對帳
    last = -10 ** 9; and_ks = []
    for k in np.flatnonzero(eligible & (score >= 3)):
        if k - last > DD:
            last = k
            if k + 1 < n and andf(int(idx[k])):
                and_ks.append(int(k))
    and_set = set(and_ks)
    cf_ = pd.Series(df["close"].to_numpy(float)).ffill().to_numpy()
    evd = _G["EVD"].get(sid, [])
    up = B["up"]; dates = B["dates"]
    rows = []
    for j in np.flatnonzero(eligible[:n - 1] & (score[:n - 1] == 2)):
        pj = int(idx[j])
        if not andf(pj):
            continue
        k = j + 1; T = int(idx[k])
        rq = {}
        if not cond[0, j]:
            rq["c1"] = (1 + C1) * c[j - 19] / c[j] - 1
        if not cond[1, j]:
            cnt = int(up[j - 18:j + 1].sum())
            lim = 0.07 if dates[k] < pd.Timestamp("2015-06-01") else 0.10
            rq["c2"] = (R11.limit_price(rc[j], True, lim) / rc[j] - 1) if cnt == 2 else np.inf
        if not cond[2, j]:
            rq["c3"] = np.inf
        if not cond[3, j]:
            rq["c4"] = c[j - 98:j + 1].sum() / 99.0 / c[j] - 1
        if not cond[4, j]:
            rq["c5"] = c[j - 248:j + 1].max() / c[j] - 1
        ez = min(rq, key=lambda z: (rq[z], z)); mreq = float(rq[ez])
        med = float(np.nanmedian(amt[j - 60:j])) if j >= 60 else np.nan
        relv = float(amt[j]) / med if (j >= 60 and med > 0 and np.isfinite(amt[j])) else np.nan
        e = k + 60; nbk = int(nb_sig[k]); xpos = -1; xb = -1
        if e < n and e < nbk:
            xpos = int(idx[e]); xb = e
        elif e >= n and nbk > n - 1 and int(idx[n - 1]) == n0 - 1:
            xpos = n0; xb = n - 1
        r8 = False
        g = g4 = np.nan
        if xpos >= 0:
            cx = c[xb]
            for pe, pL in evd:
                if T <= pL and xpos >= pe:
                    xpos = pL; cx = cf_[pL]; r8 = True
            g = cx / vw[k] - 1.0 if np.isfinite(vw[k]) else np.nan
            g4 = cx / o4[k] - 1.0
        rows.append({"sid": sid, "j": int(j), "k": int(k), "pos_j": pj, "T": T, "score_j": int(score[j]), "未達": "+".join(z for z in CN if z in rq),
                     "最容易": ez, "所需漲幅": mreq, **{f"rq_{z}": float(rq.get(z, np.nan)) for z in CN},
                     "relvol_j": relv, "amt_ratio_j": float(amt_ratio[j]), "vw_T": float(vw[k]), "vw_T_原": float(vw0[k]), "o4_T": float(o4[k]),
                     "開_T1": float(o[k + 1]) if k + 1 < n else np.nan, "收_Tm1": float(c[j]), "收_T": float(c[k]), "T漲幅": float(c[k] / c[j] - 1),
                     "xpos": int(xpos), "R8截": r8, "g": float(g), "g4": float(g4),
                     "T成立": bool(eligible[k] and score[k] >= 3 and andf(T)), "T分數": int(score[k]), "T營收": andf(T), "在訊號表": int(k) in and_set})
    for x in XS:
        last = -10 ** 9
        for r in rows:
            ok = r["所需漲幅"] <= x + 1e-12 and r["j"] - last > DD
            r[f"sel_{xname(x)}"] = bool(ok)
            if ok:
                last = r["j"]
    rows = [r for r in rows if w0 - 5 <= r["T"] <= w1 + 1]
    keep = bool(rows) or any(w0 - 5 <= int(idx[k + 1]) <= w1 + 1 for k in and_ks)
    arr = None
    if keep:
        vwc = np.full(n0, np.nan); vwc[idx] = vw
        o4c = np.full(n0, np.nan); o4c[idx] = o4
        opc = np.full(n0, np.nan); opc[idx] = o
        arr = {"vw": vwc, "o4": o4c, "op": opc, "close32": pd.Series(df["close"].to_numpy()).ffill().to_numpy(np.float32),
               "valid": np.isfinite(df["close"].to_numpy(float))}
    return {"sid": sid, "rows": rows, "and_ks": [(k, int(idx[k]), int(idx[k + 1])) for k in and_ks], "arr": arr, "out_rng": out_rng,
            "n_vw_nan": int(np.isnan(vw0).sum())}


def load_panel(p):
    P = pd.read_csv(p, dtype={"stock_id": str}, usecols=["stock_id", "signal_pos", "rev_hi24"]).sort_values(["stock_id", "signal_pos"])
    return {s: (g["signal_pos"].to_numpy(), g["rev_hi24"].astype("boolean").fillna(False).to_numpy(bool)) for s, g in P.groupby("stock_id")}


def universe():
    stocks = pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(stocks)
    uni = D.load_universe().merge(U[["stock_id"]], on="stock_id")
    return list(zip(uni["stock_id"], uni["market"]))


# ═════════════ 引擎 ═════════════
def pad(a, NP, fill):
    a = np.asarray(a)
    return a if len(a) >= NP else np.r_[a, np.full(NP - len(a), a[-1] if fill == "last" else np.nan, dtype=a.dtype)].astype(a.dtype)


def run_arm(job):
    wk, nm = job
    W = _W[wk]; sig, cl, op, sf = W["ARMS"][nm]
    o, aud = YX._eng(W, "營量", sig, "H60", 7000, closes=cl, opens=op, SF=sf)
    row, eq, _ = YX._stats(W, o, aud, W["SEGP"], 20)
    row.update({"世界": wk, "臂": nm, "eq_sha": YX.sha(eq), "強制出場": int(o.get("x_stop_force_n", -1))})
    diffs = {}
    V1 = W["V1EQ"]
    for sg, (x, y) in W["SEGP"].items():
        diffs[sg] = (eq[x + 1:y + 1] / eq[x:y] - 1.0) - (V1[x + 1:y + 1] / V1[x:y] - 1.0)
    return row, diffs, aud


def trades(aud):
    op = {}; rows = []
    for a in sorted(aud, key=lambda z: (z["t"], z["side"] != "sell")):
        if a["side"] == "buy":
            op[a["sid"]] = a
        else:
            b = op.pop(a["sid"])
            rows.append({"sid": a["sid"], "t_in": b["t"], "t_out": a["t"], "px_in": b["px"], "淨": a["amt"] / b["amt"] - 1 - a["cost"] / b["amt"]})
    return pd.DataFrame(rows)


def dist(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    q = np.percentile(x, [5, 10, 25, 50, 75, 90, 95])
    return {"筆數": int(len(x)), "平均": float(x.mean()), "中位": float(q[3]), "p5": float(q[0]), "p10": float(q[1]), "p25": float(q[2]), "p75": float(q[4]),
            "p90": float(q[5]), "p95": float(q[6]), "比較便宜比例": float((x < 0).mean())}


BINS = [-np.inf, -0.06, -0.04, -0.02, -0.01, 0.0, 0.01, 0.02, 0.04, 0.06, np.inf]
BLAB = ["≤−6%", "−6～−4%", "−4～−2%", "−2～−1%", "−1～0%", "0～1%", "1～2%", "2～4%", "4～6%", "≥6%"]


def prep_world(wk, W, uni_jobs, panel_path, procs, log, S):
    PAN = load_panel(panel_path)
    _G.clear(); _G.update(cal=W["cal"], w0=W["w0"], w1=W["w1"], PAN=PAN, EVD=W["EVD"])
    t0 = time.time()
    with Pool(procs) as pool:
        res = [r for r in pool.imap_unordered(scan, uni_jobs, chunksize=8) if r is not None]
    log(f"[{wk}] 掃描 {len(uni_jobs)} 檔（有資料 {len(res)}）｜{time.time() - t0:.0f}s")
    ARR = {r["sid"]: r["arr"] for r in res if r["arr"] is not None}
    ROWS = pd.DataFrame([x for r in res for x in r["rows"]])
    ROWS = ROWS.sort_values(["T", "sid"]).reset_index(drop=True)
    w0, w1 = W["w0"], W["w1"]; NP = W["NP"]; n0 = len(W["cal"])
    st = {"均價落在當日區間外（夾回）根數": int(sum(r["out_rng"] for r in res)), "均價算不出（量 0）根數": int(sum(r["n_vw_nan"] for r in res))}
    # 閘：本支重算的 AND 訊號 ＝ 訊號表（窗內）
    mine = {(r["sid"], k) for r in res for k, p_, e_ in r["and_ks"] if w0 <= e_ <= w1}
    base = W["SIGH"][("營量", 60)]
    tab = set(zip(base["sid"], base["k"].astype(int)))
    st["重算 AND 訊號 vs 訊號表：只在重算"] = len(mine - tab); st["重算 AND 訊號 vs 訊號表：只在訊號表"] = len(tab - mine); st["訊號表筆數"] = len(tab)
    st["只在重算（例）"] = sorted(mine - tab)[:5]; st["只在訊號表（例）"] = sorted(tab - mine)[:5]
    # 價格字典
    CL = dict(W["closes"]); dmax = 0.0; new = []
    for s, a in ARR.items():
        c32 = a["close32"]
        if s in CL:
            ref = CL[s][:n0]; m = np.isfinite(ref) | np.isfinite(c32)
            d_ = np.nanmax(np.abs(ref[m].astype(float) - c32[m].astype(float))) if m.any() else 0.0
            dmax = max(dmax, float(d_) if np.isfinite(d_) else 9e9)
        else:
            CL[s] = pad(c32, NP, "last"); new.append(s)
    st["既有收盤字典 vs 本支（最大差）"] = dmax; st["補進收盤字典檔數"] = len(new)
    SFx = {**W["SF"], **R11.stop_force_days({s: ARR[s]["valid"] for s in new}, w1)}
    OPV = dict(W["opens"]); OP4 = dict(W["opens"])
    for s, a in ARR.items():
        OPV[s] = pad(a["vw"].astype(np.float32), NP, "nan"); OP4[s] = pad(a["o4"].astype(np.float32), NP, "nan")
    # 完美預知臂
    PF = base[base["xpos_H60"] >= 0].copy()
    pos = PF["pos"].to_numpy(int); ent = PF["entry_pos"].to_numpy(int); g0 = PF["g_H60"].to_numpy(float)
    vwT = np.array([ARR[s]["vw"][p] if s in ARR else np.nan for s, p in zip(PF["sid"], pos)])
    o4T = np.array([ARR[s]["o4"][p] if s in ARR else np.nan for s, p in zip(PF["sid"], pos)])
    opE = np.array([ARR[s]["op"][e] if s in ARR else np.nan for s, e in zip(PF["sid"], ent)])
    opW = np.array([float(W["opens"][s][e]) for s, e in zip(PF["sid"], ent)])
    st["完美預知：原進場開盤 本支 vs 引擎字典（最大相對差）"] = float(np.nanmax(np.abs(opE / opW - 1)))
    disc = pd.DataFrame({"sid": PF["sid"].to_numpy(), "k": PF["k"].to_numpy(int), "T": pos, "T1": ent, "均價": vwT, "四價均": o4T, "T1開盤": opE,
                         "便宜_均價": vwT / opE - 1, "便宜_四價均": o4T / opE - 1})
    ARMS = {}
    for tag, px in (("", vwT), ("_四價均", o4T)):
        P2 = PF.copy(); ok = np.isfinite(px)
        P2["entry_pos"] = pos; P2["g_H60"] = (1 + g0) * opE / px - 1
        P2 = P2[ok]
        st[f"完美預知{tag}：中午價算不出剔除"] = int((~ok).sum())
        ARMS["完美預知" + tag] = (P2.sort_values(["entry_pos", "sid"], kind="stable"), CL, OPV if tag == "" else OP4, SFx)
    # 可執行臂
    for x in XS:
        for tag, gc, pc in (("", "g", "vw_T"), ("_四價均", "g4", "o4_T")):
            R_ = ROWS[ROWS[f"sel_{xname(x)}"] & (ROWS["T"] >= w0) & (ROWS["T"] <= w1) & (ROWS["xpos"] >= 0) & np.isfinite(ROWS[gc])]
            sg = pd.DataFrame({"sid": R_["sid"].to_numpy(), "k": R_["k"].to_numpy(int), "pos": R_["T"].to_numpy(int), "entry_pos": R_["T"].to_numpy(int),
                               "xpos_H60": R_["xpos"].to_numpy(np.int64), "g_H60": R_[gc].to_numpy(float), "relvol": R_["relvol_j"].to_numpy(float)})
            ARMS[f"可執行_{xname(x)}{tag}"] = (sg, CL, OPV if tag == "" else OP4, SFx)
    ARMS["原版"] = (base, None, None, None)
    ARMS["原版_擴充字典"] = (base, CL, dict(W["opens"]), SFx)
    W["ARMS"] = ARMS; W["ROWS"] = ROWS; W["DISC"] = disc; W["ARR"] = ARR
    S["資料"][wk] = st
    log(f"[{wk}] {st}")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    log(f"===== researchYLearly {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜提早一天中午買（描述臂、不計 N、不改判定） =====")
    S = {"身分": "描述臂、不計 N、不改任何判定", "使用者原話": RAW, "逐字標": [TAG_PX, TAG_PF], "先驗提醒": PRIOR, "閘": {}, "資料": {}}
    Wm, We, ctx = YB.worlds(log)
    _W["主"] = Wm; _W["早年"] = We
    from backtest import researchV as V
    RR.use_snapshot()
    prep_world("主", Wm, universe(), os.path.join(RR.OUT, "sig_edc6f", "panel_rev.csv.gz"), a.procs, log, S)
    D.DATA = V.body_paths("main")[0]
    prep_world("早年", We, universe(), os.path.join(V.body_paths("main")[1], "panel_rev.csv.gz"), a.procs, log, S)
    RR.use_snapshot()
    # 原版與閘
    ref = pd.read_csv("backtest/resultsT1fix/seeds.csv.gz", dtype={"eq_sha": str})
    rf = ref[(ref["key"] == "c13") & (ref["var"] == "t1")].set_index("r")["eq_sha"]
    ref3 = pd.read_csv("backtest/resultsYLexit3/seeds.csv.gz", dtype={"eq_sha": str}, low_memory=False)
    ROWS = []; DIFF = {}; AUD = {}
    for wk, W in (("主", Wm), ("早年", We)):
        o, aud = YX._eng(W, "營量", W["SIGH"][("營量", 60)], "H60", 7000); W["V1EQ"] = np.asarray(o["equity"], float)
        sh = YX.sha(W["V1EQ"])
        r3 = ref3[(ref3["世界"] == wk) & (ref3["格"] == "營量v1") & (ref3["r"] == 0)]["eq_sha"].iloc[0]
        S["閘"][f"{wk}｜原版 ＝ resultsYLexit3 營量v1 種子 0"] = bool(sh == r3)
        if wk == "主":
            S["閘"]["主｜原版 ＝ resultsT1fix c13 t1 種子 0"] = bool(sh == rf[0])
        names = list(W["ARMS"])
        with Pool(a.procs) as pool:
            res = pool.map(run_arm, [(wk, nm) for nm in names])
        for nm, (row, diffs, aud_) in zip(names, res):
            ROWS.append(row)
            for sg, d in diffs.items():
                DIFF[(wk, nm, sg)] = d
            AUD[(wk, nm)] = aud_
        shas = {r["臂"]: r["eq_sha"] for r in ROWS if r["世界"] == wk}
        S["閘"][f"{wk}｜原版（引擎池內重跑）＝ 原版"] = bool(shas["原版"] == sh)
        S["閘"][f"{wk}｜原版換擴充字典 eq_sha 不變"] = bool(shas["原版_擴充字典"] == sh)
        S["閘"][f"{wk}｜重算 AND 訊號 ＝ 訊號表（差筆數）"] = S["資料"][wk]["重算 AND 訊號 vs 訊號表：只在重算"] + S["資料"][wk]["重算 AND 訊號 vs 訊號表：只在訊號表"]
        log(f"[{wk}] 引擎完成｜{S['閘']}")
    SEED = pd.DataFrame(ROWS); SEED.to_csv(os.path.join(OUT, "arms.csv"), index=False, float_format="%.17g")
    Z = json.load(open("backtest/resultsYLexit3/summary.json", encoding="utf-8"))["0050"]
    S["0050"] = Z
    cal, ecal = Wm["cal"], We["cal"]
    months = {sg: np.array([str(d)[:7] for d in cal[x + 1:y + 1]]) for sg, (x, y) in Wm["SEGP"].items()}
    months["早年"] = np.array([str(d)[:7] for d in ecal[We["w0"] + 1:We["w1"] + 1]])
    SEGW = (("探索", "主"), ("確認", "主"), ("早年", "早年"))
    ARMN = ["原版", "完美預知"] + [f"可執行_{xname(x)}" for x in XS] + ["完美預知_四價均"] + [f"可執行_{xname(x)}_四價均" for x in XS]
    TB = []
    for nm in ARMN:
        row = {"臂": nm}
        for sg, wk in SEGW:
            g = SEED[(SEED["世界"] == wk) & (SEED["臂"] == nm)].iloc[0]
            cc, mm = float(g[f"{sg}_年化"]), float(g[f"{sg}_回落"])
            row.update({f"{sg}_年化": cc, f"{sg}_回落": mm, f"{sg}_標籤": YX.label(cc, mm, Z[sg]), f"{sg}_持股": float(g.get(f"{sg}_持股", np.nan)),
                        f"{sg}_買進每年": float(g.get(f"{sg}_買進每年", np.nan))})
            if nm != "原版":
                m_, se_ = YX.cr0(DIFF[(wk, nm, sg)], months[sg])
                row[f"{sg}_差"] = m_ * 245; row[f"{sg}_差lo"] = (m_ - 1.96 * se_) * 245; row[f"{sg}_差hi"] = (m_ + 1.96 * se_) * 245
        TB.append(row)
    TB = pd.DataFrame(TB); TB.to_csv(os.path.join(OUT, "table.csv"), index=False, float_format="%.17g")
    # 均價 vs T+1 開盤
    DS = {}
    for wk, W in (("主", Wm), ("早年", We)):
        d_ = W["DISC"]; d_ = d_[(d_["T1"] >= W["w0"]) & (d_["T1"] <= W["w1"])]
        d_.to_csv(os.path.join(OUT, f"discount_{wk}.csv.gz"), index=False, float_format="%.9g")
        for col in ("便宜_均價", "便宜_四價均"):
            DS[f"{wk}｜{col}"] = dist(d_[col]); DS[f"{wk}｜{col}"]["分佈"] = dict(zip(BLAB, pd.cut(d_[col], BINS, labels=BLAB).value_counts(sort=False).astype(int).tolist()))
        if wk == "主":
            for sg in ("探索", "確認"):
                x_, y_ = Wm["SEGP"][sg]; dd = d_[(d_["T1"] > x_) & (d_["T1"] <= y_)]
                DS[f"主{sg}｜便宜_均價"] = dist(dd["便宜_均價"])
    S["均價vsT1開盤"] = DS
    # 可執行臂另報
    EXS = {}
    for wk, W in (("主", Wm), ("早年", We)):
        R_ = W["ROWS"]; R_.to_csv(os.path.join(OUT, f"rows_{wk}.csv.gz"), index=False, float_format="%.9g")
        base = W["SIGH"][("營量", 60)]; bw = base[(base["entry_pos"] >= W["w0"]) & (base["entry_pos"] <= W["w1"])]
        prev = {(s, int(j)): r for s, j, r in zip(R_["sid"], R_["j"], R_["所需漲幅"])}
        for x in XS:
            xn = xname(x); sel = R_[R_[f"sel_{xn}"] & (R_["T"] >= W["w0"]) & (R_["T"] <= W["w1"])]
            ok = sel[(sel["xpos"] >= 0) & np.isfinite(sel["g"])]
            e = {"選入筆數": int(len(sel)), "可算報酬": int(len(ok)), "每年筆數": float(len(sel) / ((W["w1"] - W["w0"] + 1) / 245.0)),
                 "T 收盤真的成立比例": float(sel["T成立"].mean()), "在營量訊號表比例": float(sel["在訊號表"].mean()),
                 "最容易那條": sel["最容易"].value_counts().to_dict(),
                 "訊號層 成立那批 平均淨": float((ok[ok["T成立"]]["g"] - COST).mean()), "訊號層 沒成立那批 平均淨": float((ok[~ok["T成立"]]["g"] - COST).mean()),
                 "訊號層 沒成立那批 勝率": float(((ok[~ok["T成立"]]["g"] - COST) > 0).mean()),
                 "營量訊號被前一天名單抓到的比例（去重後）": float(np.mean([bool(((sel["sid"] == s) & (sel["k"] == k)).any()) for s, k in zip(bw["sid"], bw["k"].astype(int))])) if len(bw) < 5000 else np.nan,
                 "營量訊號前一天在名單條件內的比例（去重前）": float(np.mean([prev.get((s, int(k) - 1), np.inf) <= x + 1e-12 for s, k in zip(bw["sid"], bw["k"])]))}
            aud = AUD[(wk, f"可執行_{xn}")]; TRd = trades(aud)
            info = {(s, int(t)): (cf, tb) for s, t, cf, tb in zip(ok["sid"], ok["T"], ok["T成立"], ok["在訊號表"])}
            cf = np.array([info.get((r.sid, int(r.t_in)), (None, None))[0] for r in TRd.itertuples()], dtype=object)
            e["組合成交筆數"] = int(len(TRd)); e["組合 成立比例"] = float(np.mean(cf == True))
            e["組合 成立那批 平均淨"] = float(TRd["淨"][cf == True].mean()); e["組合 沒成立那批 平均淨"] = float(TRd["淨"][cf == False].mean())
            e["組合 沒成立那批 勝率"] = float((TRd["淨"][cf == False] > 0).mean())
            EXS[f"{wk}｜{xn}"] = e
    S["可執行臂另報"] = EXS
    log("[結果] " + "；".join(f"{r.臂} 確認 {r.確認_年化:+.2%}／{r.確認_回落:+.2%} {r.確認_標籤}" for r in TB.itertuples()))
    # ── 例子（主、可執行 x5、確認段、組合實際成交）
    W = Wm; XN = "可執行_x5"
    TRd = trades(AUD[("主", XN)])
    t0c, t1c = Wm["SEGP"]["確認"]
    R_ = W["ROWS"]; sel = R_[R_["sel_x5"]]
    info = {(s, int(t)): r for s, t, r in zip(sel["sid"], sel["T"], sel.to_dict("records"))}
    base = W["SIGH"][("營量", 60)]
    orig = {(s, int(k)): (int(e), int(x), float(g)) for s, k, e, x, g in zip(base["sid"], base["k"], base["entry_pos"], base["xpos_H60"], base["g_H60"])}
    TRd = TRd[(TRd["t_in"] > t0c) & (TRd["t_in"] <= t1c)].copy()
    TRd["info"] = [info.get((r.sid, int(r.t_in))) for r in TRd.itertuples()]
    TRd = TRd[TRd["info"].notna()].copy()
    TRd["成立"] = [bool(i["T成立"]) for i in TRd["info"]]
    TRd["原版淨"] = [(orig[(r.sid, int(r.info["k"]))][2] - COST) if (r.sid, int(r.info["k"])) in orig else np.nan for r in TRd.itertuples()]
    TRd["差"] = TRd["淨"] - TRd["原版淨"]
    A_ = TRd[TRd["成立"] & (TRd["差"] > 0) & (TRd["淨"] > 0)].sort_values(["差", "t_in"])
    Bl = TRd[~TRd["成立"] & (TRd["淨"] <= 0)].sort_values(["淨", "t_in"]); Bw = TRd[~TRd["成立"] & (TRd["淨"] > 0)].sort_values(["淨", "t_in"])
    mid = lambda g, off=0: g.index[min(max((len(g) - 1) // 2 + off, 0), len(g) - 1)] if len(g) else None
    EX = [("提早買賺到的（當天真的成立、比隔天開盤買多賺）", mid(A_, -1) if len(A_) > 1 else mid(A_), len(A_)),
          ("提早買賺到的（當天真的成立、比隔天開盤買多賺）", mid(A_, 1) if len(A_) > 1 else None, len(A_)),
          ("提早買但沒成立（賠錢那種）", mid(Bl), len(Bl)), ("提早買但沒成立（賺錢那種）", mid(Bw), len(Bw))]
    S["例子類別筆數"] = {"確認段組合成交": int(len(TRd)), "成立且比原版多賺且賺錢": int(len(A_)), "沒成立且賠": int(len(Bl)), "沒成立且賺": int(len(Bw)),
                   "成立": int(TRd["成立"].sum()), "成立那批 比原版多賺比例": float((TRd[TRd["成立"]]["差"] > 0).mean())}
    uni = D.load_universe().set_index("stock_id")["name"]
    dt = lambda t: str(cal[int(t)].date()) if int(t) < len(cal) else "資料尾"
    P = lambda x: "—" if x is None or not np.isfinite(x) else f"{x * 100:+.2f}%"
    Pn = lambda x: "—" if x is None or not np.isfinite(x) else f"{x * 100:.2f}%"
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0] + "\n.pick{background:#fff4cc}td.l,th.l{text-align:left}"
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>營量 提早一天中午買</title>", f"<style>{CSS}</style></head><body><main>", "<h1>營量 v1：提早一天、中午就買</h1>",
         f"<p class='lead'>使用者原話：「{html.escape(RAW)}」<br>⛔ 描述臂：不計 N、不改任何判定。⚠ 先驗提醒：{html.escape(PRIOR)}。<br>⚠ {TAG_PX}（只有日線，中午價用當天成交額÷成交量）。</p>",
         "<p class='note'>原版：訊號日（T）收盤成立 ⇒ 隔天（T＋1）開盤買、抱 60 天。<br>"
         f"<b>完美預知</b>：同一批訊號改在 T 當天中午買、同一天賣（等於抱 61 天）——⚠ {TAG_PF}（中午不可能知道收盤會不會成立），只用來看提早一天最多多賺多少。<br>"
         "<b>可執行</b>：T 的前一天收盤後，挑「營收已成立、5 取 3 已有 2 條、差的那條只要隔天漲 ≤ x% 就達到」的股票，T 當天中午買、不管收盤成不成立，抱 61 天。"
         "量的條件（成交額 3 倍）不是漲幅算得出來的，⛔ 不算「差一點點」。名額與挑法（relvol）照營量 v1；都扣成本。</p>"]
    v1 = TB.set_index("臂").loc["原版"]
    H.append("<h2>對照表</h2><div class='wrap'><table><tr><th class='l'>臂</th><th>探索 2017–21</th><th>確認 2022–26</th><th>標籤</th><th>早年 2012–14</th><th>標籤</th><th>確認：對原版〔95% CI〕</th><th>早年：對原版〔CI〕</th></tr>")
    lab = {"原版": "原版（營量 v1）", "完美預知": f"完美預知（{TAG_PF}）", "可執行_x3": "可執行 x＝3%", "可執行_x5": "可執行 x＝5%", "可執行_x10": "可執行 x＝10%"}
    for r in TB.to_dict("records"):
        if r["臂"].endswith("四價均"):
            continue
        c_ = "pick" if r["臂"] == "可執行_x5" else ""
        dd = (lambda sg: "—" if r["臂"] == "原版" else f"{P(r[sg + '_差'])}〔{P(r[sg + '_差lo'])}, {P(r[sg + '_差hi'])}〕")
        H.append(f"<tr class='{c_}'><td class='l'>{lab[r['臂']]}</td><td>{P(r['探索_年化'])}／{P(r['探索_回落'])}</td><td>{P(r['確認_年化'])}／{P(r['確認_回落'])}</td><td>{r['確認_標籤']}</td>"
                 f"<td>{P(r['早年_年化'])}／{P(r['早年_回落'])}</td><td>{r['早年_標籤']}</td><td>{dd('確認')}</td><td>{dd('早年')}</td></tr>")
    H.append("</table></div>")
    H.append(f"<p class='note'>年化／最大回落。0050 確認 {P(Z['確認']['cagr'])}／{P(Z['確認']['mdd'])}、早年 {P(Z['早年']['cagr'])}。"
             "四價平均（開高低收÷4）當中午價的敏感度見 REPORT。</p>")
    H.append("<h2>可執行臂：買進那批當天收盤真的成立嗎？</h2><div class='wrap'><table><tr><th class='l'>x</th><th>每年選入</th><th>當天真的成立</th><th>成立那批 平均淨</th><th>沒成立那批 平均淨</th><th>沒成立 勝率</th><th>營量訊號前一天就在名單</th></tr>")
    for x in XS:
        e = EXS[f"主｜{xname(x)}"]
        H.append(f"<tr><td class='l'>{int(round(x * 100))}%</td><td>{e['每年筆數']:.0f}</td><td>{e['T 收盤真的成立比例']:.0%}</td><td>{P(e['訊號層 成立那批 平均淨'])}</td>"
                 f"<td>{P(e['訊號層 沒成立那批 平均淨'])}</td><td>{e['訊號層 沒成立那批 勝率']:.0%}</td><td>{e['營量訊號前一天在名單條件內的比例（去重前）']:.0%}</td></tr>")
    H.append("</table></div><p class='note'>主窗 2017–2026、訊號層（每筆選入各抱 61 天、扣成本）。</p>")
    dm = DS["主｜便宜_均價"]
    H.append("<h2>T 日均價比 T＋1 開盤便宜多少？</h2>"
             f"<p class='note'>主窗營量訊號 {dm['筆數']} 筆：均價 ÷ 隔天開盤 − 1 平均 {P(dm['平均'])}、中位 {P(dm['中位'])}；均價比較便宜的比例 {dm['比較便宜比例']:.0%}"
             f"（負 ＝ 中午買比較便宜）。早年 平均 {P(DS['早年｜便宜_均價']['平均'])}、中位 {P(DS['早年｜便宜_均價']['中位'])}。</p><div class='wrap'><table><tr><th class='l'>區間</th><th>筆數</th></tr>")
    for b_, n_ in dm["分佈"].items():
        H.append(f"<tr><td class='l'>{b_}</td><td>{n_}</td></tr>")
    H.append("</table></div>")
    H.append("<h2>可執行 x＝5% 的例子（確認段、組合實際成交）</h2>" + CS.legend_html())
    for cat, i, n_ in EX:
        if i is None:
            H.append(f"<p class='note'>{cat}：沒有例子。</p>"); continue
        r = TRd.loc[i]; s = r["sid"]; inf_ = r["info"]; T = int(r["t_in"]); t_out = min(int(r["t_out"]), len(cal) - 1)
        df = D.load_stock(s, Wm["mk"].get(s, "twse"), cal).df; cf = pd.Series(df["close"].to_numpy(float)).ffill().to_numpy()
        i0 = max(0, T - 40); i1 = min(len(cal) - 1, t_out + 8); sl = slice(i0, i1 + 1)
        marks = [{"i": T - i0, "px": float(inf_["vw_T"]), "kind": "entry", "label": f"中午買 {inf_['vw_T']:.2f}"},
                 {"i": t_out - i0, "px": float(cf[t_out]), "kind": "exit", "label": f"出 {cf[t_out]:.2f}"}]
        if r["成立"] and (s, int(inf_["k"])) in orig:
            e1 = orig[(s, int(inf_["k"]))][0]
            marks.append({"i": e1 - i0, "px": float(df["open"].to_numpy(float)[e1]), "kind": "entry", "label": f"原版隔天開盤 {df['open'].to_numpy(float)[e1]:.2f}", "color": "#888888", "row": 1})
            sub = f"前一天差：{CNAME[inf_['最容易']]}（要漲 {Pn(inf_['所需漲幅'])}）｜T 當天漲 {P(inf_['T漲幅'])}、收盤成立｜提早買 {P(r['淨'])}；原版隔天開盤買 {P(r['原版淨'])}"
        else:
            sub = f"前一天差：{CNAME[inf_['最容易']]}（要漲 {Pn(inf_['所需漲幅'])}）｜T 當天漲 {P(inf_['T漲幅'])}、收盤沒成立（T 分數 {inf_['T分數']}）｜這筆 {P(r['淨'])}"
        ma = {kk: CS.moving_avg(cf, kk)[sl] for kk in (5, 20, 60)}
        svg = CS.kline_svg([str(z.date()) for z in cal[sl]], df["open"].to_numpy(float)[sl], df["high"].to_numpy(float)[sl], df["low"].to_numpy(float)[sl], df["close"].to_numpy(float)[sl],
                           df["volume"].to_numpy(float)[sl] / 1000.0, ma=ma, marks=marks, shade=(T - i0, t_out - i0), title=cat, show_title=False)
        H.append(f"<details class='card' open><summary><b>{html.escape(cat)}</b>｜{s} {html.escape(str(uni.get(s, '')))}｜中午買 {dt(T)}</summary>"
                 f"<div class='meta'>這一類在確認段 {n_} 筆；取中位附近｜{html.escape(sub)}</div>{svg}</details>")
    H.append(f"<p class='note'>⚠ {TAG_PX}；價格為還原價。</p></main></body></html>")
    open(os.path.join(OUT, F_HTML), "w", encoding="utf-8").write("\n".join(H))
    S["例子"] = [{"類": cat, "sid": (TRd.at[i, "sid"] if i is not None else None), "T": (dt(TRd.at[i, "t_in"]) if i is not None else None),
                "淨": (float(TRd.at[i, "淨"]) if i is not None else None), "原版淨": (float(TRd.at[i, "原版淨"]) if i is not None else None), "類筆數": n_} for cat, i, n_ in EX]
    # 例子查核：成交價 ＝ 中午價
    S["例子查核：組合進場價 ＝ T 日中午價（最大相對差）"] = float(max([abs(float(r.px_in) / float(r.info["vw_T"]) - 1) for r in TRd.itertuples()] + [0.0]))
    NL = chr(10)
    R_ = ["# 營量 v1 提早一天、T 日中午買（描述臂）" + NL, "使用者原話（逐字）：「" + RAW + "」" + NL,
          f"> ⛔ 描述臂：不計 N、不改任何判定。⚠ 先驗提醒：{PRIOR}。⚠ {TAG_PX}。完美預知臂：{TAG_PF}。本線讀法 S1～S7 見程式開頭。" + NL,
          "| 臂 | 探索 | 確認 | 確認標籤 | 早年 | 早年標籤 | 探索 對原版〔CI〕 | 確認 對原版〔CI〕 | 早年 對原版〔CI〕 |", "|---|---|---|---|---|---|---|---|---|"]
    for r in TB.to_dict("records"):
        dd = (lambda sg: "—" if r["臂"] == "原版" else f"{P(r[sg + '_差'])}〔{P(r[sg + '_差lo'])}, {P(r[sg + '_差hi'])}〕")
        R_.append(f"| {r['臂']} | {P(r['探索_年化'])}／{P(r['探索_回落'])} | {P(r['確認_年化'])}／{P(r['確認_回落'])} | {r['確認_標籤']} | {P(r['早年_年化'])}／{P(r['早年_回落'])} | {r['早年_標籤']} | {dd('探索')} | {dd('確認')} | {dd('早年')} |")
    R_.append(NL + "## T 日均價 ÷ T＋1 開盤 − 1（負 ＝ 中午買比較便宜）" + NL)
    R_.append("| 範圍 | 筆數 | 平均 | 中位 | p10 | p25 | p75 | p90 | 比較便宜比例 |"); R_.append("|---|---|---|---|---|---|---|---|---|")
    for k_, d_ in DS.items():
        R_.append(f"| {k_} | {d_['筆數']} | {P(d_['平均'])} | {P(d_['中位'])} | {P(d_['p10'])} | {P(d_['p25'])} | {P(d_['p75'])} | {P(d_['p90'])} | {d_['比較便宜比例']:.1%} |")
    R_.append(NL + "分佈（主、均價）：" + "、".join(f"{b_} {n_}" for b_, n_ in DS["主｜便宜_均價"]["分佈"].items()) + NL)
    R_.append("## 可執行臂另報" + NL)
    R_.append("| 世界｜x | 每年選入 | T 真的成立 | 在訊號表 | 訊號層 成立／沒成立 平均淨 | 沒成立勝率 | 組合成交 | 組合 成立比例 | 組合 成立／沒成立 平均淨 | 營量訊號前一天在名單（去重前） |")
    R_.append("|---|---|---|---|---|---|---|---|---|---|")
    for k_, e in EXS.items():
        R_.append(f"| {k_} | {e['每年筆數']:.0f} | {e['T 收盤真的成立比例']:.1%} | {e['在營量訊號表比例']:.1%} | {P(e['訊號層 成立那批 平均淨'])}／{P(e['訊號層 沒成立那批 平均淨'])} | {e['訊號層 沒成立那批 勝率']:.0%} | "
                  f"{e['組合成交筆數']} | {e['組合 成立比例']:.1%} | {P(e['組合 成立那批 平均淨'])}／{P(e['組合 沒成立那批 平均淨'])} | {e['營量訊號前一天在名單條件內的比例（去重前）']:.1%} |")
    R_.append(NL + f"閘：{S['閘']}" + NL + NL + f"資料：{json.dumps(S['資料'], ensure_ascii=False, default=str)}" + NL + NL + f"例子：{S['例子']}｜類別筆數 {S['例子類別筆數']}｜網頁：{F_HTML}")
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write(NL.join(R_) + NL)
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=lambda z: z.item() if hasattr(z, "item") else str(z))
    log(f"[完] 網頁 {os.path.getsize(os.path.join(OUT, F_HTML))} bytes｜閘 {S['閘']}｜{time.time() - T0:.0f}s")


if __name__ == "__main__":
    main()
