# -*- coding: utf-8 -*-
"""財報公告後漂移 PEAD seq1【頻率表・乾跑】（台股策略線 登錄 sha af545cdcfa5bf94f，2026-10-20 11:38；裁定 seq388 發號 N_前段 ＋1；
Bernard & Thomas 1989：標準化盈餘意外 SUE 最高十分位，財報上傳後抱 60 個交易日）——回測線計算子代理。
⛔ 只數事件、剔除計數、n_eff、分組件數、重疊比例；⛔ 不讀、不算、不存任何進場後的價格、報酬、持有期結果（裁定 seq388：頻率表先交、裁定過目後才開跑）。
   本件訊號完全不用價格；進場日 e 只用「500 張閘、有沒有成交、開盤是否有效、是否開盤鎖漲停」旗標（Frame.gate、快取 pv／trd／o／upl）。
⛔ 不 commit、不改既有程式與結果夾；researchAscTri_freq／research11／patterns／researchExit5 ⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPEAD_freq [--procs 3]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPEAD_freq_check
輸出 backtest/resultsPEAD/freq/：freq.json、freq.csv、freq_by_year.csv、quarterly.csv、events.csv.gz、run.log

═══ 讀法（E 標；登錄沒寫清楚、執行者補的都在這裡；⛔ 在看任何本件數字之前寫死；★＝執行者定，〔 〕內為另一讀法）═══
 E1 財報資料 ＝ tw-stock-data main 006adbd009（2026-10-20 05:02 台北 data commit）git archive 到 ~/peadwork/006adbd009/（唯讀）：
    data/mops/fin_hist/<yyyy>Q<q>.csv（2013Q1～2026Q2，全產業）、data/meta/filing_dates.csv（t57sb01 上傳時戳）、data/mops/revenue_hist（月營收）。
 E2 單季 EPS（登錄 §一）：Q1 ＝ eps_ytd；Q2、Q3、Q4 ＝ eps_ytd(q) − eps_ytd(q−1)（Q4 ＝ 全年 − Q3 累計）；
    ★ 相減不可算（本季或前季累計空）⇒ 改用檔內 eps_q（researchMine X5 同式），用到的筆數照報〔另一讀法：一律當缺〕。
    ⚠ fin_hist 是回填版本：後來重編過的季（filing_dates 有 AI4～AI9 重編檔）檔內可能是重編後數字 ⇒ 不遮、事件中屬重編季的筆數照報。
 E3 SUE(q) ＝ d(q) ÷ std(d(q−1), …, d(q−8))，d(x) ＝ EPS(x) − EPS(x−4)；★ std 用樣本標準差（ddof＝1）〔另一讀法：母體 ddof＝0，只差常數倍、不改排序與十分位〕。
    剔除（每筆只記第一個原因）：EPS缺（EPS(q) 或 EPS(q−4) 空）→ 前8季不足（d(q−1..q−8) 任一空）→ 標準差0。⇒ SUE可算。
    母體 ＝ 主世界股票（researchAscTri_freq.load_world「主」sids：四碼普通股、含已下市、排 -DR／ETF／創新板；load_bars ≥ 260 根）∩ fin_hist 有該季列。
 E4 可用日（seq352 §四、seq368 §三「同期多檔取最早的 uploaded_at（中文主報表，AI1 優先、否則 AI2）」）：★ 該 (股, 年, 季) 有 AI1 ⇒ AI1 列中最早 uploaded_at；
    沒有 AI1 ⇒ AI2 列中最早；兩者皆無 ⇒ 剔除「無上傳時戳」〔另一讀法：法定期限後補〕。上傳日 u ＝ uploaded_at 的日期；
    進場日 e ＝ 日曆中第一個 ＞ u 的交易日（登錄「可用日下一交易日開盤進」；★ 不看上傳時刻，盤中上傳也是下一交易日）。
 E5 十分位（登錄 §一）：主 ＝ 上一季（q−1）全體 SUE可算（E3，⛔ 不看時戳與閘）的 90 百分位（np.quantile 線性內插）；同季並報 ＝ 第 q 季全體的 90 百分位。
    事件 ＝ SUE ≥ 切點 ∧ 有上傳時戳。★ 第一個可算 SUE 季沒有上一季分布 ⇒ 主臂 0 件（照報）。最低十分位（描述）同法 ≤ 10 百分位，只報件數。
    ⚠ 上一季分布用到該季全部公司（含晚交者）⇒ 另報「進場時 q−1 分布中還沒上傳的公司」件數與比例（門檻是否微前視）。
 E6 進場剔除（每筆只記第一個原因）：超出資料尾（e 不在日曆內）→ 閘外(500張/pit)（patterns.Frame.gate[e]：含 e 的 20 個交易日都有成交 ∧ e−20～e−1 日均量
    ≥ 500 張 ＝ 登錄「500 張閘在可用日判（T−20～T−1）」，★ T 取進場日 e，與 UO／海龜頻率表同；∧ UG.pit_valid[e]）→ e無成交（e 無成交或開盤無效）
    → e開盤鎖漲停（快取 upl）。保留 ＝ 事件數。★ e 那根是壞 K 棒（與前一根斷開）只報、不剔（訊號不用價格；持有從 e 開盤起算）。
 E7 段（登錄 §二）：依進場日 e：探索 [2017-03-02, 2021-12-30]｜確認 [2022-01-03, 資料尾 2026-09-24]｜段前 ＝ e ＜ 2017-03-02（只描述）｜早年段不做（登錄）。
    n_eff ＝ min(事件數, 有事件的進場月數)；另報有事件的財報季數；n_eff ＜ 30 ⇒ 標「依構造不可判定、不計 N」。
 E8 營收先揭露（登錄 §四）：該季三個月的月營收年增 ＝ 當月營收 ÷ 去年當月營收 − 1（去年當月 ＞ 0 才可算）；月份 p 已公布 ⇔ 可得日 ≤ e
    （可得日 ＝ researchExit5.avail_pos：次月 10 日〔2026-01 期起 15 日，seq 營收可用日規則〕之後第一個交易日）。
    「營收已先好」＝ 三個月都已公布且年增都 ＞ 0；「沒先好」再分「三個月都已公布但有月 ≤ 0」與「有月缺／未公布／去年當月 ≤ 0」。
 E9 與單季 EPS 季增（seq329）重疊：同股同季 EPS(q) ＞ EPS(q−1)（E2 同一條單季 EPS；兩者有值、相等不算）；另報一般業（industry＝ci）子集。
    ⚠ seq329 原件母體是 5,000 萬＋一般業 ci、用法定期限 ⇒ 這裡只比「同股同季是否也季增」。
 E10 seq377 乾跑等價檢查（上季切點 vs 同季切點）：每季事件集合 A（上季切點）、B（同季切點）（有時戳、閘前），報 |A∩B|÷|A|、Jaccard 季中位與合計；保留層同報。
 E11 早年可否：fin_hist 最早 2013Q1；repo 內 2013 前單季 EPS 有無照報（fs_hist 2015Q1 起；~/earlydata 各版面 mops 只有 revenue_hist）。
"""
from __future__ import annotations

import argparse
import glob
import gzip
import hashlib
import json
import os
import subprocess
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchAscTri_freq as AT              # noqa: E402  load_world 原樣（⛔ 只 import）
from backtest import research11 as R                        # noqa: E402  load_bars
from backtest import patterns as P                          # noqa: E402  Frame.gate（500 張閘）
from backtest import universe_gate as UG                    # noqa: E402
from backtest import researchExit5 as X5                    # noqa: E402  avail_pos（⛔ 只 import）

UG.set_gate_v2(True)

REG_SHA = "af545cdcfa5bf94f"
MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
ARCH = os.path.join(MAILBOX, "_封存-2026-10-19_附件與登錄全文-舊")
OUT = "backtest/resultsPEAD/freq"
MAIN_SHA = "006adbd009e7f6c461e1d904f0349f395e54a5f6"
WD = os.path.expanduser(f"~/peadwork/{MAIN_SHA[:10]}/data")
NPREV = 8
TOPQ = 0.90
BOTQ = 0.10
NEFF_MIN = 30
RESTATE = {"AI4", "AI5", "AI6", "AI7", "AI8", "AI9"}
SEGS = {"段前": ("2015-01-01", "2017-03-01"), "探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", None), "主全窗": ("2017-03-02", None)}
ARMS = ["上季切點", "同季切點"]
X_EPS, X_HIST, X_STD = "EPS缺", "前8季不足", "標準差0"
E_TAIL, E_GATE, E_NOTRD, E_UPL, E_KEEP = "日曆外(超出資料尾)", "閘外(500張/pit)", "e無成交", "e開盤鎖漲停", "保留"
_G: dict = {}
LOG: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def reg_check():
    fs = [f for d in (MAILBOX, ARCH) for f in glob.glob(os.path.join(d, "*.md")) if f"sha{REG_SHA}" in os.path.basename(f)]
    if len(fs) < 1:
        raise SystemExit(f"⛔ 信箱找不到登錄全文 sha{REG_SHA}")
    for f in fs:
        b = open(f, "rb").read()
        h = hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]
        if h != REG_SHA:
            raise SystemExit(f"⛔ 登錄 sha {h} ≠ {REG_SHA}（{f}）")
    return os.path.basename(fs[0])


def ensure_archive():
    if not os.path.isdir(os.path.join(WD, "mops", "fin_hist")):
        os.makedirs(os.path.dirname(WD), exist_ok=True)
        cmd = f"git -C ~/tw-p17 archive {MAIN_SHA} data/mops/fin_hist data/meta/filing_dates.csv data/mops/revenue_hist | tar -x -C {os.path.dirname(WD)}"
        subprocess.run(cmd, shell=True, check=True)


def qname(qi):
    return f"{qi // 4}Q{qi % 4 + 1}"


# ═════════════ E2 單季 EPS ═════════════
def load_eps(sids):
    fs = sorted(glob.glob(os.path.join(WD, "mops", "fin_hist", "*.csv")))
    h = hashlib.sha256()
    parts = []
    for f in fs:
        h.update(os.path.basename(f).encode()); h.update(open(f, "rb").read())
        parts.append(pd.read_csv(f, dtype={"stock_id": str, "period": str}, usecols=["stock_id", "period", "industry", "eps_q", "eps_ytd"]))
    F = pd.concat(parts, ignore_index=True)
    dup = int(F.duplicated(["stock_id", "period"]).sum())
    F = F.drop_duplicates(["stock_id", "period"], keep="last")
    F["y"] = F["period"].str[:4].astype(int); F["q"] = F["period"].str[-1].astype(int); F["qi"] = F["y"] * 4 + F["q"] - 1
    F["eps_ytd"] = pd.to_numeric(F["eps_ytd"], errors="coerce"); F["eps_q"] = pd.to_numeric(F["eps_q"], errors="coerce")
    K = {(s, qi): v for s, qi, v in zip(F["stock_id"], F["qi"], F["eps_ytd"])}
    sq, fb = [], []
    for s, qi, q, v, vq in zip(F["stock_id"], F["qi"], F["q"], F["eps_ytd"], F["eps_q"]):
        if q == 1:
            e = v
        else:
            pv = K.get((s, qi - 1), np.nan)
            e = v - pv if (np.isfinite(v) and np.isfinite(pv)) else np.nan
        f_ = False
        if not np.isfinite(e) and np.isfinite(vq):
            e = vq; f_ = True
        sq.append(e); fb.append(f_)
    F["eps"] = sq; F["fb"] = fb
    info = {"檔數": len(fs), "內容sha": h.hexdigest()[:16], "期別": [qname(int(F["qi"].min())), qname(int(F["qi"].max()))], "重複列": dup,
            "全體股季": int(len(F)), "改用eps_q股季": int(F["fb"].sum())}
    F = F[F["stock_id"].isin(set(sids))].reset_index(drop=True)
    info["主世界股季"] = int(len(F)); info["主世界改用eps_q股季"] = int(F["fb"].sum())
    return F, info


# ═════════════ E4 上傳時戳 ═════════════
def load_upload():
    fd = pd.read_csv(os.path.join(WD, "meta", "filing_dates.csv"), dtype=str)
    fd["ts"] = pd.to_datetime(fd["uploaded_at"], errors="coerce")
    fd["qi"] = fd["year"].astype(int) * 4 + fd["season"].astype(int) - 1
    out = {}; src = {}; anyd = {}
    for code in ("AI1", "AI2"):
        g = fd[fd["doc_code"] == code].groupby(["stock_id", "qi"])["ts"].min()
        for k, v in g.items():
            if k not in out and pd.notna(v):
                out[k] = v; src[k] = code
    g = fd.groupby(["stock_id", "qi"])["ts"].min()
    anyd = g.to_dict()
    rs = set(fd[fd["doc_code"].isin(RESTATE)][["stock_id", "qi"]].itertuples(index=False, name=None))
    info = {"列": int(len(fd)), "年份": [int(fd["year"].astype(int).min()), int(fd["year"].astype(int).max())],
            "股季有AI1": int(sum(1 for v in src.values() if v == "AI1")), "股季只有AI2": int(sum(1 for v in src.values() if v == "AI2")),
            "股季有任何檔": int(len(anyd)), "重編股季": len(rs),
            "AI1/AI2最早日晚於任何檔最早日的股季": int(sum(1 for k, v in out.items() if anyd.get(k) is not None and v.normalize() > anyd[k].normalize()))}
    return out, src, rs, info


# ═════════════ 逐股：閘 ═════════════
def stock_job(a):
    sid = a
    W = _G["主"]; cal = W["cal"]; n0 = W["n0"]; i = W["ix"][sid]
    import backtest.data as D
    D.DATA = W["data"]
    B = R.load_bars(sid, W["mk"].get(sid, "twse"), cal)
    if B is None:
        return sid, None
    df = B["df"]; idx = B["idx"].astype(np.int64); nb = len(idx)
    bad = np.asarray(B["next_bad"][:nb] == np.arange(nb), bool)
    for p_ in W["BADPOS"].get(sid, ()):
        k = int(np.searchsorted(idx, p_, "left"))
        if k < nb:
            bad[k] = True
    f = P.Frame(df, set())
    g = np.asarray(f.gate, bool)[:n0] & np.asarray(W["PV"][i][:n0], bool)
    badpos = np.zeros(n0, bool); badpos[idx[bad]] = True
    tr = np.zeros(n0, bool); tr[idx] = True
    return sid, {"gate": g, "badpos": badpos, "bar": tr}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    t0 = time.time()
    out_dir = OUT if a.limit is None else os.path.join(OUT, "_try")
    os.makedirs(out_dir, exist_ok=True)
    reg = reg_check()
    log(f"[登錄] {reg}（sha {REG_SHA} 已驗）")
    ensure_archive()
    W = AT.load_world("主"); cal = W["cal"]; n0 = W["n0"]
    _G["主"] = W
    sids = W["sids"][:a.limit] if a.limit else W["sids"]
    res = {}
    with Pool(a.procs) as pool:
        for k_, (sid, r) in enumerate(pool.imap_unordered(stock_job, sids, chunksize=8)):
            res[sid] = r
    ok = sorted(s for s, r in res.items() if r is not None)
    log(f"[主] 逐股閘完｜{len(ok)} 檔（load_bars 不足 260 根 {len(res) - len(ok)}）｜{time.time() - t0:.0f}s")
    F, finfo = load_eps(ok)
    log(f"[fin_hist] {finfo}")
    UP, USRC, RS, uinfo = load_upload()
    log(f"[filing_dates] {uinfo}")
    # 矩陣：sid × qi
    q0, q1 = int(F["qi"].min()), int(F["qi"].max()); nq = q1 - q0 + 1
    six = {s: k for k, s in enumerate(ok)}; S = len(ok)
    EPS = np.full((S, nq), np.nan); HAS = np.zeros((S, nq), bool); IND = np.full((S, nq), "", object); FBM = np.zeros((S, nq), bool)
    for s, qi, e, ind, fb in zip(F["stock_id"], F["qi"], F["eps"], F["industry"], F["fb"]):
        EPS[six[s], qi - q0] = e; HAS[six[s], qi - q0] = True; IND[six[s], qi - q0] = ind; FBM[six[s], qi - q0] = fb
    D4 = np.full((S, nq), np.nan); D4[:, 4:] = EPS[:, 4:] - EPS[:, :-4]
    SUE = np.full((S, nq), np.nan); XR = np.full((S, nq), "", object); SD = np.full((S, nq), np.nan)
    for j in range(nq):
        for i in np.flatnonzero(HAS[:, j]):
            if not np.isfinite(D4[i, j]):
                XR[i, j] = X_EPS; continue
            if j - NPREV < 4:
                XR[i, j] = X_HIST; continue
            h = D4[i, j - NPREV:j]
            if not np.isfinite(h).all():
                XR[i, j] = X_HIST; continue
            sd = float(np.std(h, ddof=1))
            if not sd > 0:
                XR[i, j] = X_STD; continue
            SD[i, j] = sd; SUE[i, j] = D4[i, j] / sd
    OKS = np.isfinite(SUE)
    # 上傳、進場
    UPD = np.full((S, nq), np.datetime64("NaT"), "datetime64[ns]"); EP = np.full((S, nq), -1, np.int64)
    for i, s in enumerate(ok):
        for j in range(nq):
            v = UP.get((s, q0 + j))
            if v is not None:
                UPD[i, j] = np.datetime64(v)
                if v.normalize() >= cal[0] - pd.Timedelta(days=7):
                    EP[i, j] = int(cal.searchsorted(v.normalize(), side="right"))     # 第一個 ＞ u 的交易日（日曆前上傳 ⇒ −1）
    HASTS = ~np.isnat(UPD)
    CUT = {"上季切點": np.full(nq, np.nan), "同季切點": np.full(nq, np.nan)}; CUTB = np.full(nq, np.nan)
    for j in range(nq):
        v = SUE[OKS[:, j], j]
        if len(v):
            CUT["同季切點"][j] = np.quantile(v, TOPQ); CUTB[j] = np.quantile(v, BOTQ)
        if j >= 1:
            v1 = SUE[OKS[:, j - 1], j - 1]
            if len(v1):
                CUT["上季切點"][j] = np.quantile(v1, TOPQ)
    with np.errstate(invalid="ignore"):
        TOP = {arm: OKS & HASTS & (SUE >= CUT[arm][None, :]) for arm in ARMS}
        BOT = OKS & HASTS & (SUE <= CUTB[None, :])
    # 進場狀態
    TRD = W["TRD"]; O = W["O"]; UPL = W["UPL"]; ixw = W["ix"]
    def est(i, j):
        e = int(EP[i, j]); s = ok[i]
        if e < 0 or e >= n0:
            return E_TAIL
        r = res[s]
        if not r["gate"][e]:
            return E_GATE
        w = ixw[s]
        if not (r["bar"][e] and TRD[w][e] and np.isfinite(O[w][e]) and O[w][e] > 0):
            return E_NOTRD
        if UPL[w][e]:
            return E_UPL
        return E_KEEP
    ANY = TOP["上季切點"] | TOP["同季切點"] | BOT
    ST = np.full((S, nq), "", object)
    for i, j in zip(*np.nonzero(ANY)):
        ST[i, j] = est(i, j)
    # 營收
    rev, rly, rinfo = X5.load_revenue(WD)
    AV = X5.avail_pos(list(rev.index), cal)
    def revgrp(s, qi, e):
        y, q = qi // 4, qi % 4 + 1
        ps = [f"{y}-{m:02d}" for m in (3 * q - 2, 3 * q - 1, 3 * q)]
        if s not in rev.columns:
            return "沒先好_資料不全"
        yo = []
        for p in ps:
            if p not in rev.index:
                return "沒先好_資料不全"
            rv, rl = rev.at[p, s], rly.at[p, s]
            if not (np.isfinite(rv) and np.isfinite(rl) and rl > 0) or AV[p] > e:
                return "沒先好_資料不全"
            yo.append(rv / rl - 1)
        return "營收已先好" if all(x > 0 for x in yo) else "沒先好_有月≤0"
    # 單季 EPS 季增（seq329）
    QOQ = np.zeros((S, nq), bool)
    with np.errstate(invalid="ignore"):
        QOQ[:, 1:] = EPS[:, 1:] > EPS[:, :-1]
    # q−1 分布在進場時還沒上傳；SUE 用到的前 12 季中有晚於本季上傳者
    def prev_unpub(i, j):
        if j < 1:
            return np.nan
        m = OKS[:, j - 1]
        u = UPD[m, j - 1]
        known = ~np.isnat(u)
        return float((u[known] >= UPD[i, j]).sum() / max(1, m.sum())), float((~known).sum() / max(1, m.sum()))
    def late_hist(i, j):
        u = UPD[i, max(0, j - 12):j]
        u = u[~np.isnat(u)]
        return bool((u > UPD[i, j]).any())
    # 事件列
    rows = []
    for i, j in zip(*np.nonzero(ANY)):
        e = int(EP[i, j]); s = ok[i]
        rows.append({"sid": s, "季": qname(q0 + j), "qi": q0 + j, "industry": IND[i, j], "EPS": EPS[i, j], "EPS_q-4": EPS[i, j - 4] if j >= 4 else np.nan,
                     "std8": SD[i, j], "SUE": SUE[i, j], "上傳時戳": str(pd.Timestamp(UPD[i, j])), "時戳來源": USRC.get((s, q0 + j), ""),
                     "e": str(cal[e].date()) if 0 <= e < n0 else "", "上季切點": CUT["上季切點"][j], "同季切點": CUT["同季切點"][j], "低十分位切點": CUTB[j],
                     "上季切點_入選": bool(TOP["上季切點"][i, j]), "同季切點_入選": bool(TOP["同季切點"][i, j]), "最低十分位": bool(BOT[i, j]),
                     "st": ST[i, j], "本季EPS改用eps_q": bool(FBM[i, j]), "SUE用到的13季有改用eps_q": bool(FBM[i, max(0, j - 12):j + 1].any()), "e壞K棒": bool(0 <= e < n0 and res[s]["badpos"][e]), "重編季": bool((s, q0 + j) in RS),
                     "營收分組": revgrp(s, q0 + j, e) if 0 <= e < n0 else "", "EPS季增(seq329式)": bool(QOQ[i, j]),
                     **dict(zip(("q-1分布中上傳晚於本件比例", "q-1分布中無時戳比例"), prev_unpub(i, j) if (TOP["上季切點"][i, j] and j >= 1) else (np.nan, np.nan))),
                     "前12季有晚於本季上傳": late_hist(i, j)})
    EV = pd.DataFrame(rows)
    EV["e_dt"] = pd.to_datetime(EV["e"], errors="coerce")
    with gzip.open(os.path.join(out_dir, "events.csv.gz"), "wt", encoding="utf-8") as fh:
        EV.drop(columns=["e_dt"]).to_csv(fh, index=False)
    # 每季表
    QT = []
    jfirst = int(np.flatnonzero(OKS.any(axis=0))[0]) if OKS.any() else None
    for j in range(nq):
        if not HAS[:, j].any():
            continue
        r = {"季": qname(q0 + j), "有財報列(主世界)": int(HAS[:, j].sum()),
             **{f"剔除_{x}": int((XR[:, j] == x).sum()) for x in (X_EPS, X_HIST, X_STD)},
             "SUE可算": int(OKS[:, j].sum()), "可算但無上傳時戳": int((OKS[:, j] & ~HASTS[:, j]).sum()),
             "上季切點": CUT["上季切點"][j], "同季切點": CUT["同季切點"][j]}
        for arm in ARMS:
            m = TOP[arm][:, j]
            r[f"{arm}_最高十分位"] = int(m.sum())
            for x in (E_TAIL, E_GATE, E_NOTRD, E_UPL, E_KEEP):
                r[f"{arm}_{x}"] = int((m & (ST[:, j] == x)).sum())
        r["上季切點_最高十分位占可算比例"] = round(int(TOP["上季切點"][:, j].sum()) / max(1, int(OKS[:, j].sum())), 4)
        r["最低十分位(描述)"] = int(BOT[:, j].sum()); r["最低十分位_保留"] = int((BOT[:, j] & (ST[:, j] == E_KEEP)).sum())
        A = set(np.flatnonzero(TOP["上季切點"][:, j])); Bs = set(np.flatnonzero(TOP["同季切點"][:, j]))
        r["等價_交集"] = len(A & Bs); r["等價_交集÷上季"] = round(len(A & Bs) / len(A), 4) if A else None
        r["等價_Jaccard"] = round(len(A & Bs) / len(A | Bs), 4) if (A | Bs) else None
        QT.append(r)
    QT = pd.DataFrame(QT)
    QT.to_csv(os.path.join(out_dir, "quarterly.csv"), index=False, encoding="utf-8-sig")
    # 段
    J = {"性質": "財報公告後漂移 PEAD seq1 頻率表乾跑（⛔ 未讀、未算任何進場後價格、報酬、持有期結果）",
         "登錄": f"台股策略線 seq1 sha {REG_SHA}", "裁定": "seq388 發號；N_前段 ＋1；頻率表先交、裁定過目後才開跑；n_eff ＜ 30 ⇒ 依構造不可判定、不計 N",
         "資料": {"main": MAIN_SHA, "fin_hist": finfo, "filing_dates": uinfo, "revenue_hist": rinfo, "主世界": W["data"],
                 "日曆": [str(cal[0].date()), str(cal[-1].date())], "股數": len(ok)},
         "第一個可算SUE季": qname(q0 + jfirst) if jfirst is not None else None,
         "早年可否": {"fin_hist最早": qname(q0), "第一個可算SUE季": qname(q0 + jfirst) if jfirst is not None else None,
                    "2013前單季EPS": "repo（main 006adbd009）內無：fin_hist 2013Q1 起、fs_hist 2015Q1 起；~/earlydata 各版面 mops 只有 revenue_hist ⇒ 照登錄早年段不做"},
         "段": {}}
    FREQ = []; YR = []
    for sg, (x, y) in SEGS.items():
        p0 = pd.Timestamp(x); p1 = cal[-1] if y is None else pd.Timestamp(y)
        segj = {"期間": f"{p0.date()}～{p1.date()}"}
        yrs = (p1 - p0).days / 365.25
        for arm in ARMS:
            col = f"{arm}_入選"
            sub = EV[EV[col] & EV["e_dt"].between(p0, p1)]
            kept = sub[sub["st"] == E_KEEP]
            months = kept["e_dt"].dt.strftime("%Y-%m").nunique(); ne = min(len(kept), months)
            jarm = {"最高十分位(進場日在段內)": int(len(sub)), **{f"剔除_{s_}": int((sub["st"] == s_).sum()) for s_ in (E_GATE, E_NOTRD, E_UPL)},
                    "事件數(保留)": int(len(kept)), "相異檔數": int(kept["sid"].nunique()), "有事件進場月": int(months), "有事件財報季": int(kept["季"].nunique()),
                    "n_eff": int(ne), "n_eff<30": bool(ne < NEFF_MIN), "判斷": "依構造不可判定、不計 N" if ne < NEFF_MIN else "可判（n_eff ≥ 30）",
                    "每年事件數": round(len(kept) / yrs, 1) if yrs > 0 else None,
                    "每季事件(季中位)": float(kept.groupby("季").size().median()) if len(kept) else None,
                    "營收分組": {k: int(v) for k, v in kept["營收分組"].value_counts().items()},
                    "營收已先好比例": round(float((kept["營收分組"] == "營收已先好").mean()), 4) if len(kept) else None,
                    "與EPS季增(seq329式)同股同季": int(kept["EPS季增(seq329式)"].sum()),
                    "比例_與EPS季增重疊": round(float(kept["EPS季增(seq329式)"].mean()), 4) if len(kept) else None,
                    "一般業ci件數": int((kept["industry"] == "ci").sum()),
                    "一般業ci中與EPS季增重疊比例": round(float(kept.loc[kept["industry"] == "ci", "EPS季增(seq329式)"].mean()), 4) if (kept["industry"] == "ci").any() else None,
                    "重編季件數": int(kept["重編季"].sum()), "e壞K棒件數(只報)": int(kept["e壞K棒"].sum()),
                    "本季EPS改用eps_q件數": int(kept["本季EPS改用eps_q"].sum()), "SUE用到的13季有改用eps_q件數": int(kept["SUE用到的13季有改用eps_q"].sum()),
                    "前12季有晚於本季上傳件數": int(kept["前12季有晚於本季上傳"].sum()),
                    "逐年保留": {int(k): int(v) for k, v in kept["e_dt"].dt.year.value_counts().sort_index().items()},
                    "進場月分布(月→件)": {k: int(v) for k, v in kept["e_dt"].dt.month.value_counts().sort_index().items()}}
            if arm == "上季切點" and len(kept):
                u = kept["q-1分布中上傳晚於本件比例"].to_numpy(float); z = kept["q-1分布中無時戳比例"].to_numpy(float)
                jarm["門檻微前視_q-1分布有公司上傳晚於本件_件數"] = int((u > 0).sum())
                jarm["門檻微前視_晚於本件比例_中位"] = round(float(np.median(u)), 4)
                jarm["門檻微前視_晚於本件比例_max"] = round(float(np.max(u)), 4)
                jarm["門檻微前視_q-1分布含無時戳公司比例_中位"] = round(float(np.median(z)), 4)
            segj[arm] = jarm
            FREQ.append({"段": sg, "臂": arm, "期間": segj["期間"], **{k: v for k, v in jarm.items() if not isinstance(v, (dict, list)) and v is not None}})
            for yy, v in jarm["逐年保留"].items():
                YR.append({"段": sg, "臂": arm, "年": yy, "保留": v})
        bsub = EV[EV["最低十分位"] & EV["e_dt"].between(p0, p1)]
        segj["最低十分位(描述)"] = {"件數": int(len(bsub)), "保留": int((bsub["st"] == E_KEEP).sum())}
        # seq377
        qs = sorted(EV.loc[EV["e_dt"].between(p0, p1), "季"].unique())
        A_ = EV[EV["上季切點_入選"] & EV["季"].isin(qs)]; B_ = EV[EV["同季切點_入選"] & EV["季"].isin(qs)]
        def eqv(A_, B_):
            ka = set(zip(A_["sid"], A_["季"])); kb = set(zip(B_["sid"], B_["季"]))
            perq = []
            for q in qs:
                a_ = {x for x in ka if x[1] == q}; b_ = {x for x in kb if x[1] == q}
                if a_:
                    perq.append((len(a_ & b_) / len(a_), len(a_ & b_) / len(a_ | b_)))
            return {"季數": len(perq), "交集÷上季_季中位": round(float(np.median([p[0] for p in perq])), 4) if perq else None,
                    "Jaccard_季中位": round(float(np.median([p[1] for p in perq])), 4) if perq else None,
                    "合計交集÷上季": round(len(ka & kb) / len(ka), 4) if ka else None, "合計Jaccard": round(len(ka & kb) / len(ka | kb), 4) if (ka | kb) else None,
                    "上季集合": len(ka), "同季集合": len(kb)}
        segj["seq377等價_上季vs同季切點"] = {"入選層(有時戳、閘前)": eqv(A_, B_),
                                       "保留層": eqv(A_[A_["st"] == E_KEEP], B_[B_["st"] == E_KEEP])}
        J["段"][sg] = segj
        log(f"[{sg}] " + "｜".join(f"{arm} n={segj[arm]['事件數(保留)']} n_eff={segj[arm]['n_eff']} 季={segj[arm]['有事件財報季']}" for arm in ARMS) +
            f"｜等價 {segj['seq377等價_上季vs同季切點']['入選層(有時戳、閘前)']['合計交集÷上季']}")
    J["每季SUE可算公司數"] = {"中位": float(QT.loc[QT["SUE可算"] > 0, "SUE可算"].median()) if len(QT) else None,
                       "最少": int(QT.loc[QT["SUE可算"] > 0, "SUE可算"].min()) if len(QT) else None,
                       "最多": int(QT["SUE可算"].max()) if len(QT) else None,
                       "≥1000的季數／可算季數": f"{int((QT['SUE可算'] >= 1000).sum())}／{int((QT['SUE可算'] > 0).sum())}"}
    _sh = QT.loc[QT["上季切點"].notna(), "上季切點_最高十分位占可算比例"]
    J["上季切點_最高十分位占可算比例(每季)"] = {"中位": float(_sh.median()), "最小": float(_sh.min()), "最大": float(_sh.max()),
                                     "≥20%季數": int((_sh >= 0.2).sum()), "≤5%季數": int((_sh <= 0.05).sum()), "季數": int(len(_sh))}
    J["剔除合計(全部季)"] = {x: int((XR == x).sum()) for x in (X_EPS, X_HIST, X_STD)}
    J["剔除合計(全部季)"]["可算但無上傳時戳"] = int((OKS & ~HASTS).sum())
    J["讀法"] = __doc__.split("═══ 讀法")[1]
    J["時間"] = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")
    pd.DataFrame(FREQ).to_csv(os.path.join(out_dir, "freq.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(YR).to_csv(os.path.join(out_dir, "freq_by_year.csv"), index=False, encoding="utf-8-sig")
    json.dump(J, open(os.path.join(out_dir, "freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] {time.time() - t0:.0f}s")
    open(os.path.join(out_dir, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
