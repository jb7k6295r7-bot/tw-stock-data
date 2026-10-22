# -*- coding: utf-8 -*-
"""存貨天數下降＋營收轉強 seq1【頻率表・乾跑】（台股策略線 登錄 sha 3b637980fe4de0c3，2026-10-22 23:33；裁定 seq454 §二 發號 N_單筆 ＋1、
判日每月（頻率表前寫死）、任一段 n_eff ＜ 24 ⇒ 還沒測、⛔ 不得事後改判日或門檻；先交頻率表）——回測線計算子代理。
⛔ 只數事件、配對、n_eff、可算比例、走得完比例、重疊；⛔ 不讀、不算、不存任何進場後報酬（seq366）。
   用到的價格只有 ≤ 判日前一交易日的還原收盤（前 12 月漲跌只用來分位配對、⛔ 不存數值）與市值（只存十分位）；進場後只用有效 K 棒／壞根／下市／鎖漲停旗標。
⛔ 不 commit、不改既有檔；researchRevTurn_freq（ensure_data、rev_table、prices、filing_pos、avail_pos、back_ret、ranks、轉強 up ＝ 大漲觀察月報 rev_metrics）、
   researchIndMom_freq（reg_check、entry_flag、load_pit）、researchLongPool（single、qkey、qlabel）、rerun17（load_bench、regime_mask）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchInvRev_freq [--procs 3] [--limit N（乾跑，輸出 ~/rtfwork/dry_ivr）]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchInvRev_freq_check [--dry]
輸出 backtest/resultsInvRev/freq/：freq.json、freq_段.csv、yearly.csv、coverage.csv（存貨／營業成本／總資產可算率）、dist.csv（D 分佈）、
     industry.csv（產業層件數）、sens.csv（門檻敏感度件數）、overlap.csv、group12.csv、events.csv.gz（逐事件旗標，⛔ 無報酬、無價格）、run.log

═══ 讀法（W 標；登錄沒寫清楚、執行者補的都在這裡；⛔ 在看任何本件數字之前寫死於 2026-10-22（台北）；★＝執行者定，〔 〕內為另一讀法）═══
 W0 資料：最新 origin/main（開跑時 fetch）；★ 本件用到的路徑（月營收三處、fs_xbrl、filing_dates、industry_hist、industry.csv、fin_hist、exright 三處、stocks.csv）
    與營收轉強驗證頻率表的版本 443ee8ce96ec 以 git diff 逐檔比，全部相同才沿用該版 archive 與月營收快取（不同 ⇒ 中止）。價格、exright、合併日曆 ＝ researchRevTurn_freq 讀法 V0、V1。
 W1 判日 ＝ 每月營收可用日 A（V3：次月 10 日後第一個交易日；2026-01 期起 15 日後）；500 張閘 G[A−1]；進場 e ＝ A 下一交易日開盤；母體 ＝ 面板四碼普通股、含已下市；
    排除金融保險 ★ ＝ A 當天 PRE.PIT industry_pit 為「金融保險」（fallback 對應後同名）。
 W2 營收轉強狀態 ＝ researchRevTurn_freq.rev_table 的 up（＝ bigrun_monthly.rev_metrics，甲 ∨ 乙；⛔ 不寫第二份）。
 W3 財報（seq352）：季 q ＝ 上傳日（AI1 優先、否則最早文件）＜ A 日期的最新一季；★「落後 2 季以上不可算」＝ q ≤ qref − 2，qref ＝ 法定期限（Q1 5/15、Q2 8/14、
    Q3 11/14、Q4 次年 3/31）早於 A 日期的最新一季。存貨、總資產、營業成本 ＝ fs_xbrl（合併 cr 優先，同 bigrun_monthly.load_xbrl 去重法）inventories、total_assets、
    cost_of_sales_ytd（年初累計 ⇒ researchLongPool.single 差分成單季）。
    近 4 季營業成本 ＝ q−3～q 單季和（四季都要有值、和 ＞ 0）；I(q) ＝ 存貨 ÷（近 4 季營業成本 ÷ 365）（★ 存貨 ≥ 0）；D ＝ I(q) ÷ I(q−4) − 1（I(q−4) ＞ 0）；
    有實體存貨 ＝ 存貨 ÷ 總資產 ≥ 5%（同季、總資產 ＞ 0）。
 W4 條件 cond(P) ＝ up ∧ 財報可算（不落後）∧ 有實體存貨 ∧ D ≤ −15%；事件 ＝ cond(P) ∧ ¬cond(P−1)（★ 上月該檔沒有營收列 ⇒ 視為不成立）；
    ∧ 面板 ∧ 過閘 ∧ 非金融；★ 同檔 12 個月內只取第一次（過閘事件依期別、與上一個取用期別相差 ＜ 12 個月不取）。進場剔除 ＝ researchIndMom_freq.entry_flag。
 W5 配對（researchRevTurn_freq V5 同式：同期、同產業 industry_pit、市值十分位同、前 12 月三分位同；分位母體 ＝ A−1 過閘股；種子 20261022；≥3 抽 3 否則全取）：
    主對照 ＝ up ∧ 財報可算 ∧ 有實體存貨（★ 同樣要有實體存貨）∧ D ＞ −15% ∧ 過閘 ∧ 非金融 ∧ e 可進場；〔另一讀法：不要求有實體存貨〕
    描述對照 ＝ 該期有營收列 ∧ ¬up ∧ 過閘 ∧ 非金融 ∧ e 可進場（不要求財報）。兩種對照各用一條 rng（同種子），事件依（A, 代號）序。
 W6 H ∈ {60, 120, 250}：x ＝ e ＋ H；走得完 ＝ x ≤ 資料尾；窗內遇壞根、窗內遇下市照 V6。主格事件 ＝ 主對照配到 ∧ H250 走得完。
 W7 段 ★ 依 A：探索 2015-04～2019-12｜確認 2020-01～2025-08｜其他不入段。n_eff ＝ 主格事件的可用月數；＜ 24 ⇒ 還沒測。第二欄 ＝ 段內月序 mod 12 分組件數。
 W8 可算率（coverage.csv）★ ＝ 每季 q（2013Q1 起）、面板中該季季末前後 ±0 有有效 K 棒的股（季末當月最後交易日有收盤）：存貨、營業成本（單季可差分）、總資產有值比例，
    分上市／上櫃（stocks.csv market）；含已下市。判日層：轉強判點中 財報可算、有實體存貨、D 可算 的比例（dist.csv 與 freq_段.csv）。
 W9 重疊（seq377）：事件中屬「轉強起點」（本期 up、上期無 up）的比例、與營收轉強驗證 freq/events（同代號同期別）的重疊、缺貨型八業占比、
    與營量／營飆同月重疊（researchRevTurn_freq V9② 同式）；產業層 ＝ 段內各產業 事件數 ÷ 判點（up ∧ 財報可算 ∧ 有實體存貨）數。
    D 門檻 −10%、−25% 只描述（同管線的事件數）。
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import pickle
import subprocess
import sys
import time
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchRevTurn_freq as RT             # noqa: E402
from backtest import researchIndMom_freq as IMF             # noqa: E402
from backtest import researchLongPool as LP                 # noqa: E402

REG_SHA = "3b637980fe4de0c3"
OUT = "backtest/resultsInvRev/freq"
WORK = RT.WORK
BASE_SHA = "443ee8ce96ec3cbdb8e33be883a0e40c9a904336"
SAME_PATHS = ["data/mops/revenue_hist", "data/mops/revenue", "data/mops/_changes.log", "data/early/revenue", "data/meta/fs_xbrl", "data/meta/filing_dates.csv",
              "data/meta/industry_hist", "data/meta/industry.csv", "data/mops/fin_hist", "data/universe/exright", "data/early/exright", "data/universe/otcexright",
              "data/meta/stocks.csv"]
D_THR = -0.15
SENS = (-0.10, -0.25)
INV_TA = 0.05
LAG_BAD = 2
DEDUP_M = 12
HS = (60, 120, 250)
HJ = 250
SEED = 20261022
NEFF_MIN = 24
FIN = "金融保險"
SEGS = [("探索", "2015-04-01", "2019-12-31"), ("確認", "2020-01-01", "2025-08-31")]
NOTES = ["頻率表、未算任何報酬（seq366）", "判日每月（頻率表前寫死）；任一段 n_eff ＜ 24 ⇒ 還沒測，⛔ 不改判日或門檻",
         "事件 ⊂ 營收轉強狀態（設計如此）", "存貨季資料 fs_xbrl 2013Q1 起 ⇒ D（年比）2014Q1 起才可能可算",
         "2015～2018 下市 58 家月營收補不回（存活者偏差）", "250 日重疊 ⇒ 結論最多暫定",
         "價格面板 ＝ rerun17 H2D（edc6f，資料尾 2026-09-24）"]
LOG = RT.LOG
log = RT.log


def segof(d):
    s = str(pd.Timestamp(d).date())
    for nm, a, b in SEGS:
        if a <= s <= b:
            return nm
    return "不入段"


def qref_of(d):
    """法定期限早於 d 的最新一季（qk）。"""
    y = d.year
    for k in range(y * 4 + 3, (y - 2) * 4, -1):
        yy, qq = k // 4, k % 4 + 1
        dl = {1: pd.Timestamp(yy, 5, 15), 2: pd.Timestamp(yy, 8, 14), 3: pd.Timestamp(yy, 11, 14), 4: pd.Timestamp(yy + 1, 3, 31)}[qq]
        if dl < d:
            return k
    return -1


def fin_table(DN):
    """W3：{sid: {qk: (存貨, 總資產, 單季營業成本)}}、I、D、有實體存貨。"""
    cols = ["period", "stock_id", "report", "inventories", "total_assets", "cost_of_sales_ytd"]
    L = []
    for f in sorted(glob.glob(os.path.join(DN, "meta", "fs_xbrl", "fs_xbrl_*.csv"))):
        x = pd.read_csv(f, dtype={"stock_id": str}, usecols=lambda c: c in cols)
        for c in cols:
            if c not in x.columns:
                x[c] = np.nan
        L.append(x)
    X = pd.concat(L)
    X["_r"] = (X["report"] != "cr").astype(int)
    X = X.sort_values(["stock_id", "period", "_r"]).drop_duplicates(["stock_id", "period"], keep="first")
    X["qk"] = [int(p[:4]) * 4 + int(p[-1]) - 1 for p in X["period"]]
    for c in cols[3:]:
        X[c] = pd.to_numeric(X[c], errors="coerce")
    F = {}
    for s, g in X.groupby("stock_id"):
        g = g.set_index("qk").sort_index()
        cy = g["cost_of_sales_ytd"]
        qs = range(int(g.index.min()), int(g.index.max()) + 1)
        cq = {q: LP.single(cy, q) for q in qs}
        d = {}
        for q in qs:
            inv = g["inventories"].get(q, np.nan); ta = g["total_assets"].get(q, np.nan)
            c4 = [cq.get(j, np.nan) for j in range(q - 3, q + 1)]
            c4s = float(sum(c4)) if np.isfinite(c4).all() else np.nan
            I = inv / (c4s / 365.0) if (np.isfinite(inv) and inv >= 0 and np.isfinite(c4s) and c4s > 0) else np.nan
            phys = (bool(inv / ta >= INV_TA) if (np.isfinite(inv) and np.isfinite(ta) and ta > 0) else None)
            d[q] = {"inv": inv, "ta": ta, "cq": cq.get(q, np.nan), "I": I, "phys": phys}
        for q in qs:
            a, b = d[q]["I"], d.get(q - 4, {}).get("I", np.nan)
            d[q]["D"] = (a / b - 1.0) if (np.isfinite(a) and np.isfinite(b) and b > 0) else np.nan
        F[s] = d
    return F, X


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    t0 = time.time()
    out = os.path.join(WORK, "dry_ivr") if a.limit else OUT
    os.makedirs(out, exist_ok=True)
    reg = IMF.reg_check(REG_SHA); log(f"[登錄] {reg}（sha {REG_SHA} 已驗）")
    subprocess.run(["git", "fetch", "-q", "origin"], check=False)
    latest = RT.git("rev-parse", "origin/main")
    same = {p: subprocess.run(["git", "diff", "--quiet", BASE_SHA, latest, "--", p]).returncode == 0 for p in SAME_PATHS}
    if not all(same.values()):
        raise SystemExit(f"⛔ 最新 main {latest[:12]} 與 {BASE_SHA[:12]} 本件路徑不同：{same}")
    sha, DN, MD = RT.ensure_data(BASE_SHA)
    log(f"[資料] 最新 origin/main {latest}；本件路徑與 {BASE_SHA[:12]} 逐檔相同 ⇒ 沿用其 archive（{DN}）")
    PX = RT.prices(sha, DN, a.procs)
    CAL, SIDS, ix = PX["CAL"], PX["SIDS"], PX["ix"]
    CEND = len(CAL) - 1
    G = PX["G"]
    RV, rdiag = RT.rev_table(MD, SIDS, a.procs, tag="all")
    if a.limit:
        keep = set(np.random.default_rng(SEED).choice(SIDS, a.limit, replace=False).tolist())
        RVall = RV
        RV = RV[RV["sid"].isin(keep)].copy()
    else:
        RVall = RV
    pit = IMF.load_pit(DN)
    F, X = fin_table(DN)
    FP, fsrc = RT.filing_pos(DN, CAL)
    FPD = {s: (np.array([d for d, q, p in v], dtype="datetime64[ns]"), np.maximum.accumulate(np.array([q for d, q, p in v]))) for s, v in FP.items()}
    log(f"[財報] fs_xbrl 列 {len(X)}｜檔 {len(F)}｜上傳時戳 {dict(fsrc)}｜{time.time() - t0:.0f}s")
    periods = sorted(RVall["period"].unique())
    APOS = RT.avail_pos(CAL, periods)
    QREF = {}

    def judge(df):
        """逐列：A、財報季、落後、D、有實體存貨、cond。"""
        A_ = df["period"].map(APOS).astype(int).to_numpy()
        i_ = df["sid"].map(ix).fillna(-1).astype(int).to_numpy()
        qv = np.full(len(df), -1); lag = np.full(len(df), 99); Dv = np.full(len(df), np.nan); ph = np.full(len(df), np.nan); hasI = np.zeros(len(df), bool)
        hasInv = np.zeros(len(df), bool); hasTA = np.zeros(len(df), bool); hasC = np.zeros(len(df), bool)
        for k, (s, A1) in enumerate(zip(df["sid"], A_)):
            if A1 > CEND:
                continue
            t = CAL[A1]
            z = FPD.get(s)
            if z is None:
                continue
            kk = int(np.searchsorted(z[0], np.datetime64(t), "left")) - 1
            if kk < 0:
                continue
            q = int(z[1][kk]); qv[k] = q
            if A1 not in QREF:
                QREF[A1] = qref_of(t)
            lag[k] = QREF[A1] - q
            rec = F.get(s, {}).get(q)
            if rec is None:
                continue
            hasInv[k] = np.isfinite(rec["inv"]); hasTA[k] = np.isfinite(rec["ta"]); hasC[k] = np.isfinite(rec["cq"])
            hasI[k] = np.isfinite(rec["I"])
            Dv[k] = rec["D"]
            ph[k] = np.nan if rec["phys"] is None else float(rec["phys"])
        df = df.copy()
        df["A"] = A_; df["i"] = i_; df["q"] = qv; df["落後季"] = lag; df["財報可算"] = (qv >= 0) & (lag < LAG_BAD)
        df["有存貨值"] = hasInv; df["有總資產"] = hasTA; df["有營業成本"] = hasC; df["I可算"] = hasI
        df["D"] = Dv; df["有實體存貨"] = ph == 1.0; df["實體存貨可判"] = np.isfinite(ph)
        return df
    JD = judge(RV)
    JD["過閘"] = [bool(i >= 0 and 1 <= A1 <= CEND and G[i, A1 - 1]) for i, A1 in zip(JD["i"], JD["A"])]
    JD["ind"] = [(pit.at(s, CAL[A1])[0] or "") if A1 <= CEND else "" for s, A1 in zip(JD["sid"], JD["A"])]
    JD["非金融"] = JD["ind"] != FIN
    JD["段"] = [segof(CAL[A1]) if A1 <= CEND else "不入段" for A1 in JD["A"]]
    base = JD["up"] & JD["財報可算"] & JD["有實體存貨"]
    log(f"[判點] 列 {len(JD)}｜up {int(JD['up'].sum())}｜up∧財報可算∧有實體存貨 {int(base.sum())}｜{time.time() - t0:.0f}s")

    def events_for(thr, tagrec=False):
        cond = base & (JD["D"] <= thr)
        ck = set(zip(JD.loc[cond, "sid"], JD.loc[cond, "period"]))
        reasons = Counter(); last = {}; ev = []
        sub = JD[cond].sort_values(["sid", "period"])
        for r in sub.itertuples(index=False):
            P = r.period; n = RT.mnum(P) - 1
            Pp = f"{n // 12:04d}-{n % 12 + 1:02d}"
            if (r.sid, Pp) in ck:
                reasons["上月也成立（非新成立）"] += 1; continue
            if r.i < 0:
                reasons["非面板"] += 1; continue
            if r.A > CEND or r.A < 1:
                reasons["可用日超出日曆"] += 1; continue
            if not r.過閘:
                reasons["閘外（A−1）"] += 1; continue
            if not r.非金融:
                reasons["金融保險"] += 1; continue
            lk = last.get(r.sid)
            if lk is not None and RT.mnum(P) - RT.mnum(lk) < DEDUP_M:
                reasons["12個月內非第一次"] += 1; continue
            last[r.sid] = P; ev.append(r)
        return pd.DataFrame(ev), reasons, int(cond.sum())
    EV, reasons, ncond = events_for(D_THR)
    log(f"[事件] cond 列 {ncond} ⇒ 事件 {len(EV)}｜{dict(reasons)}")
    # ── 分位（RT V5 同式）
    feat = {}
    for P in periods:
        A_ = APOS[P]
        if not (1 <= A_ <= CEND) or A_ < int(CAL.searchsorted(pd.Timestamp("2014-01-01"))):
            continue
        p1 = A_ - 1
        U = np.flatnonzero(G[:, p1])
        if not len(U):
            continue
        p12 = int(CAL.searchsorted(CAL[p1] - pd.DateOffset(months=12), side="right")) - 1
        mc = PX["MC"][U, p1]; mc = np.where(np.isfinite(mc) & (mc > 0), mc, np.nan)
        r12 = np.array([RT.back_ret(PX, int(i), p1, p12) if p12 >= 0 else np.nan for i in U])
        pm = np.full(len(U), np.nan); pr = np.full(len(U), np.nan)
        if np.isfinite(mc).any():
            pm[np.isfinite(mc)] = RT.ranks(mc[np.isfinite(mc)])
        if np.isfinite(r12).any():
            pr[np.isfinite(r12)] = RT.ranks(r12[np.isfinite(r12)])
        for k, i in enumerate(U):
            feat[(int(i), P)] = (int(math.ceil(pm[k] * 10)) if np.isfinite(pm[k]) else -1, int(math.ceil(pr[k] * 3)) if np.isfinite(pr[k]) else -1)
    memo = {}

    def eflag(i, A_):
        if (i, A_) not in memo:
            memo[(i, A_)] = IMF.entry_flag(PX, i, A_, A_ + 1) if A_ + 1 <= CEND else "e超出資料尾"
        return memo[(i, A_)]
    pool_m = defaultdict(list); pool_d = defaultdict(list)
    # 對照池用全母體（乾跑時也用全母體，避免池子縮小；乾跑只少事件）
    JDall = JD if not a.limit else None
    if a.limit:
        JDall = judge(RVall)
        JDall["過閘"] = [bool(i >= 0 and 1 <= A1 <= CEND and G[i, A1 - 1]) for i, A1 in zip(JDall["i"], JDall["A"])]
        JDall["ind"] = [(pit.at(s, CAL[A1])[0] or "") if A1 <= CEND else "" for s, A1 in zip(JDall["sid"], JDall["A"])]
        JDall["非金融"] = JDall["ind"] != FIN
    C1 = JDall[JDall["過閘"] & JDall["非金融"] & (JDall["i"] >= 0) & (JDall["ind"] != "")]
    evP = set(EV["period"]) if len(EV) else set()
    for r in C1[C1["period"].isin(evP)].itertuples(index=False):
        f = feat.get((r.i, r.period))
        if f is None or f[0] < 0 or f[1] < 0:
            continue
        isM = bool(r.up and r.財報可算 and r.有實體存貨 and np.isfinite(r.D) and r.D > D_THR)
        isD = bool(not r.up)
        if not (isM or isD):
            continue
        if eflag(r.i, r.A) != "保留":
            continue
        key = (r.period, r.ind, f[0], f[1])
        if isM:
            pool_m[key].append(r.sid)
        if isD:
            pool_d[key].append(r.sid)
    log(f"[配對池] 主 {len(pool_m)} 格｜描述 {len(pool_d)} 格｜{time.time() - t0:.0f}s")
    rng_m = np.random.default_rng(SEED); rng_d = np.random.default_rng(SEED)
    rows = []
    EVs = EV.sort_values(["A", "sid"]).reset_index(drop=True) if len(EV) else EV
    for r in EVs.itertuples(index=False):
        i, A_, P = int(r.i), int(r.A), r.period; e = A_ + 1
        fl = eflag(i, A_)
        f = feat.get((i, P), (-1, -1))
        key = (P, r.ind, f[0], f[1])
        cm = sorted(pool_m.get(key, [])) if (f[0] >= 0 and f[1] >= 0) else []
        cd = sorted(s for s in pool_d.get(key, []) if s != r.sid) if (f[0] >= 0 and f[1] >= 0) else []
        pm_ = (sorted(rng_m.choice(cm, 3, replace=False).tolist()) if len(cm) >= 3 else cm) if (fl == "保留" and cm) else []
        pd_ = (sorted(rng_d.choice(cd, 3, replace=False).tolist()) if len(cd) >= 3 else cd) if (fl == "保留" and cd) else []
        row = {"sid": r.sid, "期別": P, "A": str(CAL[A_].date()), "e": (str(CAL[e].date()) if e <= CEND else ""), "段": segof(CAL[A_]),
               "月": f"{CAL[A_].year}-{CAL[A_].month:02d}", "年": CAL[A_].year, "產業": r.ind, "原物料型": r.ind in RT.RAW8,
               "財報季": LP.qlabel(int(r.q)), "落後季": int(r.落後季), "D": float(r.D), "甲": bool(r.accel >= RT.ACC), "乙": bool(r.hi24 == 1.0 and r.hi24_prev != 1.0),
               "轉強起點": bool(r.up and not r.up_prev), "市值十分位": f[0], "前12月三分位(配對特徵)": f[1], "進場": fl,
               "主對照候選數": len(cm), "主對照": " ".join(pm_), "主對照配到": bool(pm_), "描述對照候選數": len(cd), "描述對照": " ".join(pd_), "描述對照配到": bool(pd_),
               "下市(資料尾前≥5日)": bool(PX["LASTV"][i] < CEND - 5)}
        for H in HS:
            x = e + H
            row[f"H{H}走得完"] = bool(x <= CEND)
            row[f"H{H}窗內遇壞根"] = bool(PX["CB"][i, x] - PX["CB"][i, e] > 0) if x <= CEND else None
            row[f"H{H}窗內遇下市"] = bool(PX["LASTV"][i] < x and CEND - PX["LASTV"][i] >= 5) if x <= CEND else None
        row["主格"] = bool(row["主對照配到"] and row[f"H{HJ}走得完"])
        rows.append(row)
    E = pd.DataFrame(rows)
    log(f"[配對] 事件 {len(E)}｜主對照配到 {int(E['主對照配到'].sum()) if len(E) else 0}｜主格 {int(E['主格'].sum()) if len(E) else 0}｜{time.time() - t0:.0f}s")
    # ── 段表
    FR = []; G12 = []
    for nm, x_, y_ in SEGS + [("不入段", "", "")]:
        d = E[E["段"] == nm]; m = d[d["主格"]]
        jd = JD[JD["段"] == nm]
        up_ = jd[jd["up"]]
        ne = int(m["月"].nunique())
        okk = d["進場"] == "保留"
        FR.append({"段": nm, "可用日區間": f"{x_}～{y_}", "判點(股期)": len(jd), "轉強判點": len(up_),
                   "轉強判點中財報可算": float(up_["財報可算"].mean()) if len(up_) else np.nan,
                   "轉強判點中有實體存貨(可算者)": float(up_.loc[up_["財報可算"], "有實體存貨"].mean()) if up_["財報可算"].any() else np.nan,
                   "轉強∧有實體存貨中D可算": float(np.isfinite(up_.loc[up_["財報可算"] & up_["有實體存貨"], "D"]).mean()) if (up_["財報可算"] & up_["有實體存貨"]).any() else np.nan,
                   "cond成立(股期)": int(((jd["up"] & jd["財報可算"] & jd["有實體存貨"]) & (jd["D"] <= D_THR)).sum()),
                   "事件(新成立∧過閘∧去重)": len(d), "e可進場": int(okk.sum()),
                   "主對照配到": int(d["主對照配到"].sum()), "主對照成功率": float(d.loc[okk, "主對照配到"].mean()) if okk.any() else np.nan,
                   "主對照候選數中位": float(d.loc[okk, "主對照候選數"].median()) if okk.any() else np.nan,
                   "描述對照配到": int(d["描述對照配到"].sum()), "描述對照成功率": float(d.loc[okk, "描述對照配到"].mean()) if okk.any() else np.nan,
                   "H60走得完": int(d["H60走得完"].sum()), "H120走得完": int(d["H120走得完"].sum()), "H250走得完": int(d["H250走得完"].sum()),
                   "H250走得完比例": float(d["H250走得完"].mean()) if len(d) else np.nan,
                   "主格事件": len(m), "主格月數=n_eff": ne, "n_eff≥24": ne >= NEFF_MIN, "判定": ("可判" if ne >= NEFF_MIN else "還沒測（n_eff ＜ 24）") if nm != "不入段" else "",
                   "主格窗內遇壞根": int((m["H250窗內遇壞根"] == True).sum()), "主格窗內遇下市": int((m["H250窗內遇下市"] == True).sum()),  # noqa: E712
                   "事件中轉強起點": float(d["轉強起點"].mean()) if len(d) else np.nan, "原物料型占比": float(d["原物料型"].mean()) if len(d) else np.nan,
                   "含下市股比例": float(d["下市(資料尾前≥5日)"].mean()) if len(d) else np.nan})
        if nm in ("探索", "確認") and len(m):
            m0 = RT.mnum(x_[:7])
            for g, dd in m.groupby(m["月"].map(lambda s: (RT.mnum(s) - m0) % 12)):
                G12.append({"段": nm, "組(月序mod12)": int(g), "件數": len(dd), "月數": int(dd["月"].nunique())})
    FR = pd.DataFrame(FR)
    YR = E.groupby("年").agg(事件=("sid", "size"), 主對照配到=("主對照配到", "sum"), 主格=("主格", "sum"), 原物料型=("原物料型", "sum"),
                            轉強起點=("轉強起點", "sum"), D中位=("D", "median")).reset_index() if len(E) else pd.DataFrame()
    # ── 可算率（W8）
    stk = pd.read_csv(os.path.join(DN, "meta", "stocks.csv"), dtype=str)
    mk = dict(zip(stk["stock_id"], stk["market"])) if "market" in stk.columns else {}
    CV = []
    X2 = X.set_index(["stock_id", "qk"])
    ME = {}
    for q in range(2013 * 4, (CAL[-1].year) * 4 + 4):
        y, qq = q // 4, q % 4 + 1
        end = pd.Timestamp(y, qq * 3, 1) + pd.offsets.MonthEnd(0)
        p = int(CAL.searchsorted(end, side="right")) - 1
        if p < 0 or CAL[p] < end - pd.Timedelta(days=10):
            continue
        alive = [s for s in SIDS if np.isfinite(PX["C"][ix[s], p])]
        for mkt in ("twse", "tpex", "全部"):
            al = [s for s in alive if (mkt == "全部" or mk.get(s, "") == mkt)]
            if not al:
                continue
            inv = sum(1 for s in al if np.isfinite(F.get(s, {}).get(q, {}).get("inv", np.nan)))
            ta = sum(1 for s in al if np.isfinite(F.get(s, {}).get(q, {}).get("ta", np.nan)))
            cq = sum(1 for s in al if np.isfinite(F.get(s, {}).get(q, {}).get("cq", np.nan)))
            II = sum(1 for s in al if np.isfinite(F.get(s, {}).get(q, {}).get("I", np.nan)))
            DD = sum(1 for s in al if np.isfinite(F.get(s, {}).get(q, {}).get("D", np.nan)))
            CV.append({"季": LP.qlabel(q), "市場": mkt, "季末有價股": len(al), "存貨有值": inv / len(al), "總資產有值": ta / len(al), "單季營業成本可算": cq / len(al),
                       "存貨天數I可算": II / len(al), "D可算": DD / len(al)})
    CV = pd.DataFrame(CV)
    # D 分佈
    DS = []
    for nm, _, _ in SEGS:
        jd = JD[JD["段"] == nm]
        b_ = jd[jd["up"] & jd["財報可算"] & jd["有實體存貨"]]["D"].dropna()
        a_ = jd[jd["財報可算"] & jd["有實體存貨"]]["D"].dropna()
        for lab, v in (("轉強∧有實體存貨", b_), ("全部有實體存貨（不論轉強）", a_)):
            if len(v):
                DS.append({"段": nm, "母體": lab, "n": len(v), "p10": v.quantile(.1), "p25": v.quantile(.25), "中位": v.median(), "p75": v.quantile(.75), "p90": v.quantile(.9),
                           "≤−10%": float((v <= -0.10).mean()), "≤−15%": float((v <= -0.15).mean()), "≤−25%": float((v <= -0.25).mean())})
    DS = pd.DataFrame(DS)
    # 產業層
    IND = []
    for nm, _, _ in SEGS:
        jd = JD[JD["段"] == nm]
        b_ = jd[jd["up"] & jd["財報可算"] & jd["有實體存貨"] & jd["過閘"] & jd["非金融"]]
        d = E[E["段"] == nm]
        for ind, g in b_.groupby("ind"):
            IND.append({"段": nm, "產業": ind, "判點": len(g), "D中位": float(g["D"].median()), "事件": int((d["產業"] == ind).sum()),
                        "事件÷判點": float((d["產業"] == ind).sum() / len(g)), "原物料型": ind in RT.RAW8})
    IND = pd.DataFrame(IND).sort_values(["段", "事件"], ascending=[True, False])
    # 敏感度
    SE = []
    for thr in (D_THR,) + SENS:
        ev2, rs2, nc2 = events_for(thr)
        for nm, _, _ in SEGS:
            k = int(sum(1 for A1 in ev2["A"] if A1 <= CEND and segof(CAL[A1]) == nm)) if len(ev2) else 0
            SE.append({"門檻": thr, "段": nm, "事件(配對前)": k, "身分": ("登錄" if thr == D_THR else "描述")})
    SE = pd.DataFrame(SE)
    # 重疊
    OV = []
    rte = pd.read_csv(os.path.join(RT.OUT, "events.csv.gz"), dtype={"sid": str, "期別": str})
    RK = set(zip(rte["sid"], rte["期別"]))
    for nm, _, _ in SEGS:
        d = E[E["段"] == nm]
        k = set(zip(d["sid"], d["期別"]))
        rk = {x for x in RK if x[1] in set(d["期別"])} if len(d) else set()
        OV.append({"比較": f"事件 vs 營收轉強驗證 freq 事件（{nm}）", "事件": len(k), "同代號同期別也是轉強驗證事件": (len(k & RK) / len(k) if k else np.nan),
                   "事件為轉強起點": float(d["轉強起點"].mean()) if len(d) else np.nan, "缺貨型八業占比": float(d["原物料型"].mean()) if len(d) else np.nan})
    from backtest import rerun17 as RR
    import backtest.data as D
    D.DATA = RR.H2D
    mcal = D.load_calendar()
    reg_ = RR.regime_mask(RR.load_bench(mcal))
    AN = pd.read_csv(RT.AND_CSV, dtype={"sid": str}, usecols=["sid", "pos", "entry_pos"])
    AN = AN[(AN["pos"] < len(mcal)) & (AN["entry_pos"] <= len(mcal))].copy()
    AN["m"] = [f"{d.year}-{d.month:02d}" for d in mcal[AN["pos"].to_numpy()]]; AN["飆"] = reg_[AN["entry_pos"].to_numpy() - 1]
    w0, w1 = "2017-03", "2026-08"
    AN = AN[(AN["m"] >= w0) & (AN["m"] <= w1)]
    evm = E[(E["月"] >= w0) & (E["月"] <= w1)]
    EK = set(zip(evm["sid"], evm["月"]))
    for lab, sub in (("營量 v1（AND）", AN), ("營飆 v1（AND ∧ 0050＞200MA）", AN[AN["飆"]])):
        SK = set(zip(sub["sid"], sub["m"]))
        OV.append({"比較": f"事件 vs {lab} 同月同檔（{w0}～{w1}）", "事件": len(EK), "事件中同月有訊號": (len(EK & SK) / len(EK) if EK else np.nan),
                   "訊號中同月為事件": (len(EK & SK) / len(SK) if SK else np.nan)})
    OV = pd.DataFrame(OV)
    # 輸出
    E.to_csv(os.path.join(out, "events.csv.gz"), index=False, encoding="utf-8-sig", compression="gzip")
    FR.to_csv(os.path.join(out, "freq_段.csv"), index=False, encoding="utf-8-sig")
    YR.to_csv(os.path.join(out, "yearly.csv"), index=False, encoding="utf-8-sig")
    CV.to_csv(os.path.join(out, "coverage.csv"), index=False, encoding="utf-8-sig")
    DS.to_csv(os.path.join(out, "dist.csv"), index=False, encoding="utf-8-sig")
    IND.to_csv(os.path.join(out, "industry.csv"), index=False, encoding="utf-8-sig")
    SE.to_csv(os.path.join(out, "sens.csv"), index=False, encoding="utf-8-sig")
    OV.to_csv(os.path.join(out, "overlap.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(G12).to_csv(os.path.join(out, "group12.csv"), index=False, encoding="utf-8-sig")
    J = {"性質": "存貨天數下降＋營收轉強 seq1 頻率表（⛔ 未算任何報酬）", "登錄": f"台股策略線 seq1 sha {REG_SHA}", "裁定": "seq454 §二",
         "origin/main（最新）": latest, "沿用 archive": BASE_SHA, "路徑相同": same, "乾跑": bool(a.limit), "乾跑股數": a.limit,
         "cond列": ncond, "事件剔除": dict(reasons), "段": FR.to_dict("records"), "重疊": OV.to_dict("records"), "必附": NOTES,
         "讀法": __doc__.split("═══ 讀法")[1], "秒": round(time.time() - t0)}
    json.dump(J, open(os.path.join(out, "freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=RT.jdef)
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    log(f"[完成] {out}｜{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
