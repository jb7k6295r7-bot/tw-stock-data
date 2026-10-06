# -*- coding: utf-8 -*-
"""PREREG產業營收加速但股價落後 seq1（台股策略線登錄 sha f54db09c944622e0；裁定 seq312 准甲先交）甲 現況快照
（描述、⛔ 不計 N、⛔ 不給買賣建議；乙、丙等 seq2，本檔不做）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchIndRevLag_snapshot [--procs 3] | --check | --page

═══ 讀法（寫死於 2026-10-07 01:30（台北），在算任何數字之前；「★」＝ 登錄沒寫清楚、執行者補讀法）═══
 L0 資料：tw-stock-data origin/main（執行時取 sha；git archive data/meta、mops/revenue_hist、stocks、adj、stocks_per、stocks_inst
    到 ~/h2data/indrevlag_<sha12>/data，唯讀；同前件 snapshot S0 的做法）。價格日 T ＝ main 日曆（meta/calendar_twse.csv）最後一天。
    月營收 ＝ researchIndRev_snapshot.load_rev（早年檔＋main，同 (代號, 期別) 取 main；本件只用 M−11～M）。
 L1 可用日（登錄 §一、裁定 seq312 §4）：M 月營收 ⇒ research34.rebalance_dates：M ≤ 2025-12 用 pub_day 10、M ≥ 2026-01 用 pub_day 15
    （＝ 次月 10／15 日「之後」第一個交易日，嚴格大於）；最新可用月 M ＝ 可用日 ≤ T 的最後一個月（10/7 當下預期 2026-08；9 月版 10/15 後另補）。
 L2 產業別、排除（⭐ 沿用前件 snapshot.universe，⛔ 不改它）：main meta/industry.csv 現值、名稱相同合併；排除 金融保險、其他、存託憑證、ETF；只留 kind＝stock。
    ★ snapshot 把名稱空白的上櫃代碼 32、33 標成「上櫃代碼 NN（名稱空白）」；本件照前件 prereg（industry_pit README）改名為 文化創意業、農業科技業
      （只是標籤，成員不變）。⚠ 只有現值 ⇒ 頁首標「產業別後見（現值套回）」。
    當時已上市櫃（登錄 §一「回測前件 23:48 口徑」＝ prereg P1 ③）：產業營收成員再限 main stocks.csv first_seen ≤ d ≤ last_seen，
      d ＝ M 可用日的前一交易日（＝ prereg pitday）；被剔的公司照列計數。
 L3 產業營收與 A（⭐ 直接呼叫 snapshot.compute_ind(rev, rev_ly, 成員, M, "new")，⛔ 不另寫）：S6 口徑（同月檔「當月 ÷ 去年當月」、每月各自同公司集合、
    多月分子分母分別加總）；A1 ＝ 近 3 月合計年增；A2 ＝ A1 − 近 12 月；A3 ＝ A1 − 三個月前的 A1；公司數 ＝ M 月同公司數，＜ 5 不排名。
 L4 產業指數（登錄 §一：產業內 W1 eligible 成員等權日報酬連乘，還原價）
    W1 eligible ＝ researchp4.panel_worker（P4 面板同一支逐檔工人，⛔ 不另寫）的 eligible ＝ liq_ok ∧ bars_ok ∧ inst_ok，在 main 最新資料上重算；
      量測日 ＝ p4_features.measurement_days（每月第一個交易日），取「涵蓋 T−249 那天的量測日」起到 T 為止；
      母體 ＝ data.load_universe() ∩ universe_gate.gate3（GATE_V2 開 ⇒ _gate3_v2）；GATE_V2 開 ⇒ 另剔量測日那天 UG.pit_valid 為 False 的列（創新板板期、興櫃列）
      ★ 不沿用 resultsp9_engine/panel_ext（只到 2026-08-03 量測日、且建在 edc6f8002f 舊快照上）；本件全部量測日都用同一份最新 main 重算
    成員所屬產業：現在仍在 industry.csv 者 ＝ L2 的現值類別（不在 L2 母體 ⇒ 屬排除類別、不進任何指數）；
      ★ 不在 industry.csv（已下市）⇒ prereg.PIT（industry_pit 逐段，量測日落在哪段；晚於最後一段 ⇒ 最後已知類別）；類別在排除名單或無 ⇒ 不進
    量測日 md 的成員管 [md, 下一量測日) 的每一天（同 prereg ind_index）；日報酬 ＝ c[t]/c[t−1] − 1（c ＝ data.load_stock 還原收盤 ffill；兩日皆有限才算）；
      產業日報酬 ＝ 當天有限的成員日報酬平均；指數 I[T−250] ＝ 1，往後連乘
    L 日報酬 ＝ I[T] ÷ I[T−L] − 1，L ∈ {60, 120, 250}（登錄寫「換股日前一交易日收盤」；甲是現況 ⇒ 用最近收盤 T）
    ★ L 窗內（T−L+1～T）只要有一天沒有任何成員日報酬 ⇒ 該 L 報酬記空、該產業不進排名（照列、標原因）
 L5 百分位與挑選（登錄 §二）
    ★ 可排名產業 ＝ 公司數 ≥ 5 ∧ A1、A2、A3 皆有限 ∧ 三個 L 報酬皆有限（一個集合，三種 A、三個 L 都在同一批產業上排）
    ★ 百分位 ＝（由低到高名次 − 1）÷（可排名產業數 − 1），同值取平均名次（pandas rank average）
    P1 名次差 ＝ A 百分位 − L 日報酬百分位；A ＞ 0 且 名次差 ＞ 0 的產業依名次差由大到小（同值依產業名稱）取前 5
    P2 ＝ A ＞ 0 且 A 百分位 ≥ 2/3（★ 浮點容差 1e−12）的產業依 L 日報酬由低到高（同值依名稱）取前 5
    18 張前 5 名單（P 2 × L 3 × A 3）合併、標出現次數
    ★「同時成立（加速＋落後）」＝ A ＞ 0 且 名次差 ＞ 0（＝ P1 的候選池）；每個 L 報三種 A 各幾個、三種 A 都成立的有哪些
 L6 成員股（登錄 §六；欄位照前件 snapshot：⭐ 直接呼叫 snapshot.stock_rows）：前 5 名單裡出現過的產業，
    從 L2 現值成員（★ 含 d 之後才上市的新股，現況描述用）依市值大到小取前 5；另加「W1（最新量測日）」「創新板」兩欄
    市值 ＝ 價格日未還原收盤 × shares；近 3 月營收年增（S6 口徑）；營收創 24 月新高；近 250 日報酬、距 250 日低點（還原、日曆位置）；本益比（附日期與財報期）
 L7 查核（--check；全部用獨立寫法從原始 csv 重算，0 不同才算過；抽樣 random_state 20261007）
    ① 抽 2 個可排名產業：逐公司迴圈重算 A1～A3、公司數（自己解析 industry.csv、stocks.csv、revenue_hist）⇒ 相對差 ≤ 1e−12
    ② 抽 40 個（股票 × 量測日）：自己由 stocks、stocks_inst csv 算 有成交、amt20、bars、法人 20 日、當日名稱／市場 ⇒ W1 是否相同
    ③ 同 ① 的 2 個產業 × 三個 L：自己由 stocks、adj csv 還原價、自己分產業（industry.csv／industry_pit 原始列）重算 L 日報酬 ⇒ 相對差 ≤ 1e−9
    ④ 用輸出表的 A 與 L 報酬，純 Python 重排百分位與 18 張前 5 名單 ⇒ 名單逐位相同、百分位差 ≤ 1e−12
    ⑤ 抽 1 個成員表產業：自己由 stocks csv 算全部成員市值、取前 5 ⇒ 代號與市值相同（相對差 ≤ 1e−9）
輸出 backtest/resultsIndRevLag/snapshot/：rank_industry.csv、picks.csv、members_top5.csv、w1_panel.csv.gz、ind_index.csv、ind_members.csv.gz、meta.json、check.json、
    產業營收加速但股價落後_現況.html
"""
from __future__ import annotations

import argparse
import glob
import html
import json
import math
import os
import random
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D                              # noqa: E402
from backtest import research34 as R34                      # noqa: E402
from backtest import researchIndRev_snapshot as SNAP        # noqa: E402
from backtest import researchIndRev_prereg as PRE           # noqa: E402
from backtest import researchp4 as RP4                      # noqa: E402
from backtest import p4_features as P4F                     # noqa: E402
from backtest import universe_gate as UG                    # noqa: E402

TIME = "2026-10-07 01:30（台北）"
OUT = "backtest/resultsIndRevLag/snapshot"
PARTS = ["data/meta", "data/mops/revenue_hist", "data/stocks", "data/adj", "data/stocks_per", "data/stocks_inst"]
AS = SNAP.AS
ANAME = SNAP.ANAME
LS = (60, 120, 250)
PS = ("P1", "P2")
PNAME = {"P1": "P1 名次差（加速百分位 − 股價百分位，大到小）", "P2": "P2 先篩後挑（加速前三分之一裡股價最落後）"}
TOPK = 5
NMEM = 5
BLANK = {"上櫃代碼 32（名稱空白）": "文化創意業", "上櫃代碼 33（名稱空白）": "農業科技業"}
EXCL = SNAP.EXCL
SEED = 20261007
BOARD = re.compile(r"-(?:KY)?創")
_W: dict = {}


# ═════════════ 資料 ═════════════
def ensure_data(log, sha=None):
    sha = sha or subprocess.run(["git", "rev-parse", "origin/main"], capture_output=True, text=True, check=True).stdout.strip()
    root = os.path.expanduser(f"~/h2data/indrevlag_{sha[:12]}")
    if not os.path.exists(os.path.join(root, ".done")):
        os.makedirs(root, exist_ok=True)
        p = subprocess.run(["git", "archive", "--format=tar", sha] + PARTS, capture_output=True, check=True)
        subprocess.run(["tar", "-x", "-C", root], input=p.stdout, check=True)
        open(os.path.join(root, ".done"), "w").write(sha + "\n")
        log(f"[資料] git archive {sha[:10]} ⇒ {root}")
    return sha, os.path.join(root, "data")


def avail_pos(periods, cal):
    """L1：M → 可用日位置（≤ 2025-12 pub_day 10；≥ 2026-01 pub_day 15）。"""
    a = R34.rebalance_dates([p for p in periods if p <= "2025-12"], cal, 10)
    b = R34.rebalance_dates([p for p in periods if p >= "2026-01"], cal, 15)
    return {p: e for p, (_, e) in {**a, **b}.items()}


def a_members(DATA, d):
    """L2：⇒ (現值成員全部, 當時已上市櫃成員, 母體計數, 被剔的公司)。"""
    mem, ucnt = SNAP.universe(DATA)
    mem = mem.copy(); mem["產業"] = mem["產業"].replace(BLANK)
    stk = pd.read_csv(os.path.join(DATA, "meta", "stocks.csv"), dtype=str).drop_duplicates("stock_id", keep="last").set_index("stock_id")
    ds = str(d.date())
    fs = mem["stock_id"].map(stk["first_seen"]); ls = mem["stock_id"].map(stk["last_seen"])
    ok = fs.notna() & ls.notna() & (fs <= ds) & (ls >= ds)
    return mem, mem[ok].reset_index(drop=True), ucnt, mem.loc[~ok, ["stock_id", "name", "產業"]].assign(first_seen=fs[~ok].to_numpy())


# ═════════════ W1 面板（L4） ═════════════
def _winit(cal, pos, data):
    RP4._init(cal, pd.DataFrame(), pos, False)
    D.DATA = data
    _W.update(cal=cal, data=data)


def _wjob(args):
    rows, _ = RP4.panel_worker(args)
    if not rows:
        return []
    cal = _W["cal"]
    pv = UG.pit_valid(args[0], cal, _W["data"])
    out = []
    for r in rows:
        p = int(cal.searchsorted(r["measure_date"]))
        out.append({"measure_date": str(pd.Timestamp(r["measure_date"]).date()), "stock_id": r["stock_id"], "market": r["market"],
                    "amt20": r["amt20"], "bars": r["bars"], "liq_ok": r["liq_ok"], "bars_ok": r["bars_ok"], "inst_ok": r["inst_ok"],
                    "eligible": r["eligible"], "pit_ok": bool(pv[p])})
    return out


def w1_positions(cal, T_pos):
    allp = P4F.measurement_days(cal, "2024-01-01", str(cal[T_pos].date()))
    s0 = T_pos - max(LS) + 1
    k0 = max(i for i, p in enumerate(allp) if p <= s0)
    return allp[k0:]


def w1_panel(DATA, cal, T_pos, procs, log):
    UG.set_gate_v2(True)
    stocks = pd.read_csv(os.path.join(DATA, "meta", "stocks.csv"), dtype=str)
    g = UG.gate3(stocks)
    U = D.load_universe().merge(g[["stock_id"]], on="stock_id")
    pos = w1_positions(cal, T_pos)
    U = U[U["last_seen"] >= cal[pos[0]]].reset_index(drop=True)
    jobs = [(r.stock_id, r.market, r.first_seen, r.last_seen) for r in U.itertuples()]
    t0 = time.time()
    rows = []
    with Pool(procs, initializer=_winit, initargs=(cal, pos, DATA)) as pool:
        for i, rs in enumerate(pool.imap_unordered(_wjob, jobs, chunksize=8)):
            rows.extend(rs)
            if (i + 1) % 500 == 0:
                log(f"  W1 {i + 1}/{len(jobs)} {time.time() - t0:.0f}s")
    PN = pd.DataFrame(rows).sort_values(["measure_date", "stock_id"]).reset_index(drop=True)
    PN["W1"] = PN["eligible"].astype(bool) & PN["pit_ok"].astype(bool)
    info = {"gate3（v2）∩ load_universe": int(len(U)), "量測日": [str(cal[p].date()) for p in pos], "面板列": int(len(PN)),
            "eligible 列": int(PN["eligible"].sum()), "pit_valid 剔": int((PN["eligible"] & ~PN["pit_ok"]).sum()), "W1 列": int(PN["W1"].sum()),
            "耗時秒": round(time.time() - t0)}
    return PN, dict(zip(U["stock_id"], U["market"])), info


class IndOf:
    """L4 成員所屬產業：industry.csv 有 ⇒ L2 現值類別（不在 L2 母體 ⇒ None）；沒有 ⇒ prereg.PIT（industry_pit）。"""

    def __init__(self, DATA, mem_all):
        cur = pd.read_csv(os.path.join(DATA, "meta", "industry.csv"), dtype=str)
        self.incur = set(cur["stock_id"])
        self.cur = dict(zip(mem_all["stock_id"], mem_all["產業"]))
        self.pit = PRE.PIT(DATA, pd.DataFrame(columns=["stock_id", "period", "market", "產業別"]))

    def __call__(self, sid, md):
        if sid in self.incur:
            return self.cur.get(sid), "現值"
        ind, b = self.pit._at(sid, pd.Timestamp(md), "pit")
        return (None if ind is None or ind in EXCL else ind), b


def ind_index(cal, T_pos, PN, mk, indf):
    """L4 ⇒ (I: {產業: 指數(長 T_pos+1)}, 無資料日數表, 成員表)。"""
    s0 = T_pos - max(LS)
    W = PN[PN["W1"]]
    mds = sorted(PN["measure_date"].unique())
    C = {}
    for s in sorted(W["stock_id"].unique()):
        st = D.load_stock(s, mk.get(s, "twse"), cal)
        C[s] = None if st is None else pd.Series(st.df["close"].to_numpy(float)).ffill().to_numpy(float)
    rr = defaultdict(lambda: np.full(T_pos + 1, np.nan))
    memb = []
    for j, md in enumerate(mds):
        a = int(cal.searchsorted(pd.Timestamp(md))); b = int(cal.searchsorted(pd.Timestamp(mds[j + 1]))) if j + 1 < len(mds) else T_pos + 1
        a = max(a, s0 + 1)
        grp = defaultdict(list)
        for s in W.loc[W["measure_date"] == md, "stock_id"]:
            ind, basis = indf(s, md)
            memb.append({"measure_date": md, "stock_id": s, "產業": ind if ind else "（排除／無類別）", "來源": basis})
            if ind is None or C.get(s) is None:
                continue
            grp[ind].append(s)
        if a >= b:
            continue
        for ind, ss in grp.items():
            M_ = np.vstack([C[s][a - 1:b] for s in ss])
            with np.errstate(invalid="ignore", divide="ignore"):
                R_ = M_[:, 1:] / M_[:, :-1] - 1
            fin = np.isfinite(R_); cnt = fin.sum(0); sm = np.where(fin, R_, 0.0).sum(0)
            rr[ind][a:b] = np.where(cnt > 0, sm / np.maximum(cnt, 1), np.nan)
    I = {}; miss = {}
    for ind, r in rr.items():
        x = np.full(T_pos + 1, np.nan); x[s0] = 1.0
        x[s0 + 1:] = np.cumprod(1 + np.nan_to_num(r[s0 + 1:], nan=0.0))
        I[ind] = x
        miss[ind] = {L: int((~np.isfinite(r[T_pos - L + 1:T_pos + 1])).sum()) for L in LS}
    return I, miss, pd.DataFrame(memb)


# ═════════════ 百分位與挑選（L5） ═════════════
def rank_pick(T):
    """T 要有 產業、可排名、A1～A3、ret60/120/250 ⇒ 加百分位、名次差欄；回 (T, picks rows)。"""
    R = T[T["可排名"]].copy(); n = len(R)
    for a in AS:
        R[f"{a}百分位"] = (R[a].rank(method="average") - 1) / (n - 1)
    for L in LS:
        R[f"ret{L}百分位"] = (R[f"ret{L}"].rank(method="average") - 1) / (n - 1)
        for a in AS:
            R[f"差_{a}_{L}"] = R[f"{a}百分位"] - R[f"ret{L}百分位"]
            R[f"同時_{a}_{L}"] = (R[a] > 0) & (R[f"差_{a}_{L}"] > 0)
    picks = []
    for a in AS:
        for L in LS:
            p1 = R[(R[a] > 0) & (R[f"差_{a}_{L}"] > 0)].sort_values([f"差_{a}_{L}", "產業"], ascending=[False, True]).head(TOPK)
            p2 = R[(R[a] > 0) & (R[f"{a}百分位"] >= 2 / 3 - 1e-12)].sort_values([f"ret{L}", "產業"], ascending=[True, True]).head(TOPK)
            for P_, sub in (("P1", p1), ("P2", p2)):
                for k, (_, r) in enumerate(sub.iterrows()):
                    picks.append({"P": P_, "A": a, "L": L, "名次": k + 1, "產業": r["產業"], "A值": r[a], "A百分位": r[f"{a}百分位"],
                                  "L報酬": r[f"ret{L}"], "L百分位": r[f"ret{L}百分位"], "名次差": r[f"差_{a}_{L}"]})
    cols = [c for c in R.columns if c not in T.columns]
    T = T.merge(R[["產業"] + cols], on="產業", how="left")
    return T, pd.DataFrame(picks)


# ═════════════ 主程式 ═════════════
def run(a, log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    sha, DATA = ensure_data(log)
    D.DATA = DATA; cal = D.load_calendar(); T_pos = len(cal) - 1; asof = str(cal[T_pos].date())
    rev, rev_ly = SNAP.load_rev(DATA)
    av = avail_pos(list(rev.index), cal)
    M = [p for p in rev.index if p in av and av[p] <= T_pos][-1]
    d = cal[av[M] - 1]
    log(f"[資料] main {sha[:10]}｜價格日 {asof}｜最新可用營收月 {M}（可用日 {cal[av[M]].date()}；上市櫃判定日 {d.date()}）｜營收期 {rev.index[0]}～{rev.index[-1]}")
    mem_all, mem, ucnt, rm = a_members(DATA, d)
    log(f"[母體] 現值成員 {len(mem_all)}｜當時已上市櫃 {len(mem)}｜剔 {len(rm)}：{rm.to_dict('records')}")
    T, _ = SNAP.compute_ind(rev, rev_ly, mem, M, "new")
    T = T[["產業", "成員檔數", "上市", "上櫃", "公司數", "近3月各月公司數", "最新月營收（億）", "近12月營收（億）", "近3月年增", "近12月年增",
           "三個月前的近3月年增", "A1", "A2", "A3"]].copy()
    # W1 與產業指數
    PN, mk, winfo = w1_panel(DATA, cal, T_pos, a.procs, log)
    log(f"[W1] {winfo}")
    PN.to_csv(os.path.join(OUT, "w1_panel.csv.gz"), index=False, compression={"method": "gzip", "mtime": 0})
    indf = IndOf(DATA, mem_all)
    I, miss, MEMB = ind_index(cal, T_pos, PN, mk, indf)
    lastmd = max(PN["measure_date"])
    nW = MEMB[MEMB["measure_date"] == lastmd]["產業"].value_counts().to_dict()
    for L in LS:
        T[f"ret{L}"] = [(I[i][T_pos] / I[i][T_pos - L] - 1) if (i in I and miss[i][L] == 0) else np.nan for i in T["產業"]]
        T[f"ret{L}無資料日"] = [miss[i][L] if i in I else np.nan for i in T["產業"]]
    T["指數成員數（最新量測日）"] = [nW.get(i, 0) for i in T["產業"]]
    fa = np.isfinite(T[list(AS)].to_numpy(float)).all(1); fl = np.isfinite(T[[f"ret{L}" for L in LS]].to_numpy(float)).all(1)
    T["可排名"] = (T["公司數"] >= 5) & fa & fl
    T["不排名原因"] = np.where(T["可排名"], "", np.where(T["公司數"] < 5, "公司數＜5", np.where(~fa, "A 缺值", "產業指數 L 窗內有缺日或無 W1 成員")))
    T, PK = rank_pick(T)
    T.to_csv(os.path.join(OUT, "rank_industry.csv"), index=False, float_format="%.17g")
    PK.to_csv(os.path.join(OUT, "picks.csv"), index=False, float_format="%.17g")
    # 指數（窗內）
    s0 = T_pos - max(LS)
    IX = pd.DataFrame({"date": [str(x.date()) for x in cal[s0:T_pos + 1]]})
    for i in sorted(I):
        IX[i] = I[i][s0:T_pos + 1]
    IX.to_csv(os.path.join(OUT, "ind_index.csv"), index=False, float_format="%.10g")
    MEMB.to_csv(os.path.join(OUT, "ind_members.csv.gz"), index=False, compression={"method": "gzip", "mtime": 0})
    # 成員股（L6）
    cnt = Counter(PK["產業"])
    W1last = set(PN.loc[(PN["measure_date"] == lastmd) & PN["W1"], "stock_id"])
    mkall = dict(zip(mem_all["stock_id"], mem_all["market"]))
    rows = []
    for ind in sorted(cnt):
        g = mem_all[mem_all["產業"] == ind]
        rs = SNAP.stock_rows(DATA, rev, rev_ly, cal, T_pos, g["stock_id"].tolist(), mkall, M)
        rs = sorted(rs, key=lambda r: (-(r.get("市值（億）") if np.isfinite(r.get("市值（億）", np.nan)) else -1e18), r["代號"]))[:NMEM]
        for k, r in enumerate(rs):
            r.update({"產業": ind, "市值名次": k + 1, "市場": "上市" if mkall[r["代號"]] == "twse" else "上櫃", "前5名單出現次數": cnt[ind],
                      "W1（最新量測日）": "是" if r["代號"] in W1last else "否", "創新板": "是" if BOARD.search(str(r.get("名稱", ""))) else ""})
            rows.append(r)
    MB = pd.DataFrame(rows)
    MB.to_csv(os.path.join(OUT, "members_top5.csv"), index=False, float_format="%.10g")
    R_ = T[T["可排名"]]
    both = {str(L): {a: int(R_[f"同時_{a}_{L}"].sum()) for a in AS} for L in LS}
    all3 = {str(L): sorted(R_[R_[[f"同時_{a}_{L}" for a in AS]].all(axis=1)]["產業"].tolist()) for L in LS}
    META = {"讀法寫死": TIME, "main": sha, "價格日": asof, "最新可用營收月": M, "其可用日": str(cal[av[M]].date()), "上市櫃判定日": str(d.date()),
            "9月營收可用日": "2026-10-15 之後第一個交易日（尚未到）", "母體": ucnt, "當時未上市櫃而剔": rm.to_dict("records"), "W1": winfo,
            "最新量測日": lastmd, "指數成員來源計數": MEMB["來源"].value_counts().to_dict(), "產業數": int(len(T)), "可排名產業數": int(T["可排名"].sum()),
            "不排名": T.loc[~T["可排名"], ["產業", "不排名原因"]].to_dict("records"), "同時成立家數": both, "三種A都同時成立": all3,
            "前5名單出現次數": dict(cnt.most_common()), "成員表列數": int(len(MB)), "耗時秒": round(time.time() - T0)}
    json.dump(META, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] {json.dumps(META, ensure_ascii=False, default=str)}")


# ═════════════ 查核（L7；獨立寫法） ═════════════
def _f(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else float("nan")
    except (TypeError, ValueError):
        return float("nan")


def _ms(m, k):
    y, mm = int(m[:4]), int(m[5:]); t = y * 12 + mm - 1 + k
    return f"{t // 12:04d}-{t % 12 + 1:02d}"


def _rel(x, y):
    if (x != x) and (y != y):
        return 0.0
    if (x != x) or (y != y):
        return float("inf")
    return abs(x - y) / max(1.0, abs(y))


def ck_industry(DATA):
    """自己解析 industry.csv ＋ stocks.csv（kind）⇒ {代號: 產業 或 None（排除）}。"""
    import csv
    kind = {}
    for r in csv.DictReader(open(os.path.join(DATA, "meta", "stocks.csv"), encoding="utf-8")):
        kind[r["stock_id"]] = r["kind"]
    out = {}
    for r in csv.DictReader(open(os.path.join(DATA, "meta", "industry.csv"), encoding="utf-8")):
        nm, code = r["industry_name"], r["industry_code"]
        if "-DR" in r["name"] or code == "91":
            lab = "存託憑證"
        elif nm:
            lab = nm
        elif code == "32":
            lab = "文化創意業"
        elif code == "33":
            lab = "農業科技業"
        else:
            lab = f"代碼{code}"
        out[r["stock_id"]] = None if (lab in {"金融保險", "其他", "存託憑證", "ETF"} or kind.get(r["stock_id"]) != "stock") else lab
    return out


def ck_pit(DATA):
    import csv
    seg = defaultdict(list)
    for r in csv.DictReader(open(os.path.join(DATA, "meta", "industry_hist", "industry_pit.csv"), encoding="utf-8")):
        seg[r["stock_id"]].append((r["start"] or "0000-00-00", r["end"] or "9999-99-99", r["industry"]))
    for k in seg:
        seg[k].sort()

    def at(sid, md):
        sg = seg.get(sid)
        if not sg:
            return None
        for a, b, ind in sg:
            if a <= md <= b:
                return ind
        if md > sg[-1][1]:
            return sg[-1][2]
        if md < sg[0][0]:
            return sg[0][2]
        return [z for z in sg if z[1] < md][-1][2]
    return at


def ck_adjclose(DATA, sid, cal_s):
    """自己還原：raw close（≤0 視為缺）× F(d)，F(d) ＝ 第一個事件日 ＞ d 的 cum_factor；對日曆 ffill。"""
    import csv
    p = os.path.join(DATA, "stocks", f"{sid}.csv")
    raw = {}
    for r in csv.DictReader(open(p, encoding="utf-8")):
        if r["date"] in raw:
            continue
        c = _f(r["close"])
        raw[r["date"]] = c if c > 0 else float("nan")
    ev = []
    pa = os.path.join(DATA, "adj", f"{sid}.csv")
    if os.path.exists(pa):
        ev = sorted((r["date"], float(r["cum_factor"])) for r in csv.DictReader(open(pa, encoding="utf-8")))
    out = []; last = float("nan")
    for dd in cal_s:
        c = raw.get(dd, float("nan"))
        if c == c:
            F = 1.0
            for e, cf in ev:
                if e > dd:
                    F = cf; break
            last = c * F
        out.append(last)
    return out


def check(log):
    import csv
    META = json.load(open(os.path.join(OUT, "meta.json"), encoding="utf-8"))
    sha, DATA = ensure_data(log, META["main"])
    T = pd.read_csv(os.path.join(OUT, "rank_industry.csv"), float_precision="round_trip")
    PK = pd.read_csv(os.path.join(OUT, "picks.csv"), float_precision="round_trip")
    PN = pd.read_csv(os.path.join(OUT, "w1_panel.csv.gz"), dtype={"stock_id": str})
    MB = pd.read_csv(os.path.join(OUT, "members_top5.csv"), dtype={"代號": str}, float_precision="round_trip")
    M = META["最新可用營收月"]; dstr = META["上市櫃判定日"]; asof = META["價格日"]
    cal_s = [r["date"] for r in csv.DictReader(open(os.path.join(DATA, "meta", "calendar_twse.csv"), encoding="utf-8"))]
    cal_s = sorted(cal_s); Tp = cal_s.index(asof)
    rng = random.Random(SEED)
    RES = {"讀法寫死": TIME, "main": sha}; nd = 0
    ranked = sorted(T.loc[T["可排名"], "產業"].tolist())
    pick = rng.sample(ranked, 2)
    # ① A
    ind = ck_industry(DATA)
    fl = {r["stock_id"]: (r["first_seen"], r["last_seen"]) for r in csv.DictReader(open(os.path.join(DATA, "meta", "stocks.csv"), encoding="utf-8"))}
    need = {_ms(M, -k) for k in range(12)}
    rv = {}
    for f in sorted(glob.glob(os.path.join(DATA, "mops", "revenue_hist", "*.csv"))):
        if os.path.basename(f)[:7] not in need:
            continue
        for r in csv.DictReader(open(f, encoding="utf-8")):
            rv[(r["stock_id"], r["period"])] = (_f(r["當月營收"]), _f(r["去年當月營收"]))

    def yoy(sids, months):
        num = den = 0.0; c = 0
        for m in months:
            c = 0
            for s in sids:
                x, y = rv.get((s, m), (float("nan"), float("nan")))
                if x == x and y == y and x > 0 and y > 0:
                    num += x; den += y; c += 1
        return num / den - 1, c
    o1 = {}
    for nm in pick:
        sids = [s for s, v in ind.items() if v == nm and s in fl and fl[s][0] <= dstr <= fl[s][1]]
        a1, c = yoy(sids, [_ms(M, -2), _ms(M, -1), M]); y12, _ = yoy(sids, [_ms(M, -k) for k in range(11, -1, -1)])
        p3, _ = yoy(sids, [_ms(M, -5), _ms(M, -4), _ms(M, -3)])
        mine = {"A1": a1, "A2": a1 - y12, "A3": a1 - p3, "公司數": float(c)}
        r = T[T["產業"] == nm].iloc[0]
        bad = [k for k in mine if _rel(mine[k], float(r[k])) > 1e-12]
        nd += len(bad); o1[nm] = {"獨立／主程式": {k: (mine[k], float(r[k])) for k in mine}, "不同": bad}
    RES["① A"] = o1
    # ② W1
    mds = sorted(PN["measure_date"].unique())
    U = sorted(set(PN["stock_id"]))
    pairs = [(rng.choice(U), rng.choice(mds)) for _ in range(30)]
    el = PN[PN["eligible"]]
    pairs += [tuple(x) for x in el.sample(10, random_state=SEED)[["stock_id", "measure_date"]].to_numpy()]
    o2 = []

    def w1_mine(sid, md):
        p = os.path.join(DATA, "stocks", f"{sid}.csv")
        rows = {}
        for r in csv.DictReader(open(p, encoding="utf-8")):
            if r["date"] not in rows:
                rows[r["date"]] = r
        k = cal_s.index(md)
        cl = [(_f(rows[d_]["close"]) if d_ in rows else float("nan")) for d_ in cal_s[:k + 1]]
        tr = [(x == x and x > 0) for x in cl]
        if not tr[k]:
            return False, "量測日無成交"
        i0 = tr.index(True)
        bars = sum(tr)
        amts = []
        for j in range(k - 19, k + 1):
            d_ = cal_s[j]
            if tr[j]:
                amts.append(_f(rows[d_]["amount"]))
            elif j >= i0:
                amts.append(0.0)
            else:
                amts.append(float("nan"))
        liq = all(x == x for x in amts) and sum(amts) / 20 >= 5e7
        sh = float("nan")
        for d_ in cal_s[:k + 1][::-1]:
            if d_ in rows and _f(rows[d_]["shares"]) == _f(rows[d_]["shares"]):
                sh = _f(rows[d_]["shares"]); break
        inst = {}
        pi = os.path.join(DATA, "stocks_inst", f"{sid}.csv")
        if os.path.exists(pi):
            for r in csv.DictReader(open(pi, encoding="utf-8")):
                if r["date"] not in inst:
                    inst[r["date"]] = (_f(r["foreign"]), _f(r["trust"]))
        win = [inst.get(cal_s[j], (float("nan"), float("nan"))) for j in range(k - 19, k + 1)]
        iok = all(a_ == a_ and b_ == b_ for a_, b_ in win) and sh == sh and sh > 0
        r = rows[md]
        pok = r["market"] in ("twse", "tpex") and not BOARD.search(r["name"] or "")
        return bool(liq and bars >= 120 and iok and pok), f"liq {liq} bars {bars} inst {iok} pit {pok}"
    for sid, md in pairs:
        x = PN[(PN["stock_id"] == sid) & (PN["measure_date"] == md)]
        main_ = bool(x["W1"].iloc[0]) if len(x) else False
        mine, why = w1_mine(sid, md)
        o2.append({"代號": sid, "量測日": md, "獨立": mine, "主程式": main_, "說明": why})
        nd += int(mine != main_)
    RES["② W1"] = {"筆數": len(o2), "W1 為真筆數": sum(r["主程式"] for r in o2), "不同": [r for r in o2 if r["獨立"] != r["主程式"]], "明細": o2}
    # ③ L 報酬
    pit = ck_pit(DATA)
    curset = {r["stock_id"] for r in csv.DictReader(open(os.path.join(DATA, "meta", "industry.csv"), encoding="utf-8"))}

    def ind_of(s, md):
        if s in curset:
            return ind.get(s)
        v = pit(s, md)
        return None if v in (None, "", "金融保險", "其他", "存託憑證", "ETF") else v
    W = PN[PN["eligible"] & PN["pit_ok"]]
    s0 = Tp - max(LS)
    o3 = {}; pxc = {}
    for nm in pick:
        r_day = {}
        for j, md in enumerate(mds):
            a = cal_s.index(md); b = cal_s.index(mds[j + 1]) if j + 1 < len(mds) else Tp + 1
            ss = [s for s in W.loc[W["measure_date"] == md, "stock_id"] if ind_of(s, md) == nm]
            for s in ss:
                if s not in pxc:
                    pxc[s] = ck_adjclose(DATA, s, cal_s)
            for t in range(max(a, s0 + 1), b):
                vals = []
                for s in ss:
                    c0, c1 = pxc[s][t - 1], pxc[s][t]
                    if c0 == c0 and c1 == c1:
                        vals.append(c1 / c0 - 1)
                r_day[t] = sum(vals) / len(vals) if vals else float("nan")
        mine = {}
        for L in LS:
            if any(r_day.get(t, float("nan")) != r_day.get(t, float("nan")) for t in range(Tp - L + 1, Tp + 1)):
                mine[L] = float("nan"); continue
            lev = 1.0; lev_L = None
            for t in range(s0 + 1, Tp + 1):
                if t == Tp - L + 1:
                    lev_L = lev
                v = r_day.get(t, float("nan"))
                lev *= 1 + (v if v == v else 0.0)
            if L == max(LS):
                lev_L = 1.0
            mine[L] = lev / lev_L - 1
        r = T[T["產業"] == nm].iloc[0]
        bad = [L for L in LS if _rel(mine[L], float(r[f"ret{L}"])) > 1e-9]
        nd += len(bad); o3[nm] = {"獨立／主程式": {str(L): (mine[L], float(r[f"ret{L}"])) for L in LS}, "不同": bad}
    RES["③ L 報酬"] = o3
    # ④ 百分位與名單
    R = [r for _, r in T.iterrows() if bool(r["可排名"])]
    n = len(R)

    def pct(col):
        vals = [(float(r[col]), r["產業"]) for r in R]
        out = {}
        for v, nm in vals:
            lo = sum(1 for w, _ in vals if w < v); eq = sum(1 for w, _ in vals if w == v)
            out[nm] = (lo + (eq + 1) / 2 - 1) / (n - 1)
        return out
    pa = {a: pct(a) for a in AS}; pl = {L: pct(f"ret{L}") for L in LS}
    o4 = {"百分位最大差": 0.0, "名單不同": []}
    for r in R:
        for a in AS:
            o4["百分位最大差"] = max(o4["百分位最大差"], abs(pa[a][r["產業"]] - float(r[f"{a}百分位"])))
        for L in LS:
            o4["百分位最大差"] = max(o4["百分位最大差"], abs(pl[L][r["產業"]] - float(r[f"ret{L}百分位"])))
    if o4["百分位最大差"] > 1e-12:
        nd += 1
    for a in AS:
        for L in LS:
            Av = {r["產業"]: float(r[a]) for r in R}; Lv = {r["產業"]: float(r[f"ret{L}"]) for r in R}
            c1 = [(-(pa[a][k] - pl[L][k]), k) for k in Av if Av[k] > 0 and pa[a][k] - pl[L][k] > 0]
            l1 = [k for _, k in sorted(c1)][:TOPK]
            c2 = [(Lv[k], k) for k in Av if Av[k] > 0 and pa[a][k] >= 2 / 3 - 1e-12]
            l2 = [k for _, k in sorted(c2)][:TOPK]
            for P_, mine in (("P1", l1), ("P2", l2)):
                main_ = PK[(PK["P"] == P_) & (PK["A"] == a) & (PK["L"] == L)].sort_values("名次")["產業"].tolist()
                if mine != main_:
                    nd += 1; o4["名單不同"].append({"P": P_, "A": a, "L": L, "獨立": mine, "主程式": main_})
    RES["④ 百分位與名單"] = o4
    # ⑤ 成員市值
    inds = sorted(MB["產業"].unique()); nm5 = rng.choice(inds)
    caps = []
    for s, v in ind.items():
        if v != nm5:
            continue
        p = os.path.join(DATA, "stocks", f"{s}.csv")
        if not os.path.exists(p):
            continue
        last = None
        for r in csv.DictReader(open(p, encoding="utf-8")):
            if r["date"] <= asof and _f(r["close"]) == _f(r["close"]):
                last = r
        if last is not None:
            v_ = _f(last["close"]) * _f(last["shares"]) / 1e8
            caps.append((-(v_ if v_ == v_ else -1e18), s, v_))
    caps.sort()
    mine = [(s, v_) for _, s, v_ in caps[:NMEM]]
    g = MB[MB["產業"] == nm5].sort_values("市值名次")
    main_ = list(zip(g["代號"], g["市值（億）"].astype(float)))
    bad5 = [i for i in range(max(len(mine), len(main_))) if i >= len(mine) or i >= len(main_) or mine[i][0] != main_[i][0] or _rel(mine[i][1], main_[i][1]) > 1e-9]
    nd += len(bad5)
    RES["⑤ 成員市值"] = {"產業": nm5, "獨立": mine, "主程式": main_, "不同位置": bad5}
    RES["抽樣"] = {"產業（①③）": pick, "成員表產業（⑤）": nm5, "W1 筆數（②）": len(pairs), "random": SEED}
    RES["不同項數"] = nd; RES["通過"] = nd == 0
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[查核] 抽樣 {RES['抽樣']}｜① {[(k, v['不同']) for k, v in o1.items()]}｜② 不同 {len(RES['② W1']['不同'])}／{len(o2)}｜"
        f"③ {[(k, v['不同']) for k, v in o3.items()]}｜④ {o4}｜⑤ {bad5}｜不同 {nd}｜通過 {nd == 0}")


# ═════════════ 網頁 ═════════════
def page(log):
    T = pd.read_csv(os.path.join(OUT, "rank_industry.csv"), float_precision="round_trip")
    PK = pd.read_csv(os.path.join(OUT, "picks.csv"), float_precision="round_trip")
    MB = pd.read_csv(os.path.join(OUT, "members_top5.csv"), dtype={"代號": str})
    META = json.load(open(os.path.join(OUT, "meta.json"), encoding="utf-8"))
    CKp = os.path.join(OUT, "check.json"); CK = json.load(open(CKp, encoding="utf-8")) if os.path.exists(CKp) else None
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0]
    CSS += ("\ntd.l,th.l{text-align:left;white-space:normal}small{color:#666}.warn{border-left:4px solid #d64045;padding:6px 10px;background:#fff4f4}"
            ".ok{border-left:4px solid #2b6cb0;padding:8px 12px;background:#eef4fb}.big{font-size:1.05rem}li{margin:.35em 0}"
            "details{margin:.6em 0}summary{font-weight:600;cursor:pointer;padding:4px 0}.pane{display:none}.pane.on{display:block}"
            ".sel{position:sticky;top:0;background:#f6f6f4;padding:6px 0;z-index:2}.sel select{font-size:16px;margin:2px 4px;padding:4px}"
            "td.y{background:#e8f3e8;font-weight:600}")
    P1 = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:+.1f}%"
    PT = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:+.1f} 點"
    PC = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:.0f}"
    N1 = lambda v: "—" if v is None or not np.isfinite(v) else f"{v:,.1f}"
    e = html.escape
    R = T[T["可排名"]]
    cnt = META["前5名單出現次數"]
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>產業營收加速但股價落後_現況</title>", f"<style>{CSS}</style></head><body><main>",
         f"<h1>產業營收加速但股價落後：現況（營收到 {META['最新可用營收月']}，股價 {META['價格日']}）</h1>",
         "<p class='warn'>⚠ <b>描述、不是買賣建議；產業別後見（現值套回）</b>：資料庫只有現在的產業別，過去改過類別的公司也用現在的歸類。"
         "這份沒有經過回測驗證（乙還沒跑），只給挑產業討論用；不計檢定數。"
         "⚠ 本件是看過前件「只看營收加速」的全部結果之後才加「股價落後」這條（裁定 seq312：事後重切），將來回測結果最多只算暫定。</p>"]
    # 結論
    top = sorted(cnt.items(), key=lambda x: (-x[1], x[0]))
    li = []
    for L in LS:
        b = META["同時成立家數"][str(L)]; a3 = META["三種A都同時成立"][str(L)]
        li.append(f"<li>看近 <b>{L}</b> 日股價：營收在加速、股價又比加速程度落後的產業，A1 {b['A1']} 個、A2 {b['A2']} 個、A3 {b['A3']} 個"
                  f"（共 {META['可排名產業數']} 個可排名產業）；三種加速都成立的：{'、'.join(e(x) for x in a3) or '無'}</li>")
    H.append("<div class='ok big'><b>先講結論</b><ul>"
             f"<li>18 張「前 5 名」名單（兩種挑法 × 三種股價天數 × 三種加速）裡出現最多次的產業："
             + "、".join(f"<b>{e(k)}</b> {v} 次" for k, v in top[:6]) + "（滿分 18 次）</li>" + "".join(li) +
             "<li>「落後」是跟其他產業比的相對位置（百分位），不是說股價跌了；加速也只是營收年增率比之前快，不代表之後一定續強。</li></ul></div>")
    ck = (f"查核：抽樣用另一套寫法從原始資料重算（加速、成分股資格、產業指數報酬、排名名單、市值），{CK['不同項數']} 項不同。" if CK else "")
    H.append(f"<p class='lead'>讀法寫死 {e(META['讀法寫死'])}。8 月營收的可用日是 {e(META['其可用日'])}（2026 年起次月 15 日之後第一個交易日）；"
             f"9 月營收要 10/15 之後才可用，屆時另補一版。股價看到 {e(META['價格日'])} 收盤。{ck}</p>")
    # 一、同時成立
    H.append("<h2>一、營收加速、股價又落後的產業（三個股價天數）</h2><p class='note'>打勾 ＝ 該種加速值大於 0，而且加速的排名百分位高於近 L 日股價的排名百分位"
             "（＝ 登錄 P1 的候選池）。打勾下方的小數字是「名次差」：加速百分位 − 股價百分位，越大代表營收排名越前面、股價排名越後面。</p>")
    H.append("<div class='wrap'><table><tr><th class='l'>產業</th>" + "".join(f"<th>{a}<br><small>近 {L} 日</small></th>" for L in LS for a in AS) + "<th>前5出現<br><small>次數</small></th></tr>")
    sub = R.copy(); sub["_n"] = sum(sub[f"同時_{a}_{L}"].astype(bool).astype(int) for a in AS for L in LS)
    sub = sub[sub["_n"] > 0].assign(_c=lambda x: x["產業"].map(lambda k: cnt.get(k, 0))).sort_values(["_n", "_c", "產業"], ascending=[False, False, True])
    for _, r in sub.iterrows():
        tds = "".join((f"<td class='y'>✓<br><small>{PC(r[f'差_{a}_{L}'])}</small></td>" if bool(r[f"同時_{a}_{L}"]) else "<td>·</td>") for L in LS for a in AS)
        H.append(f"<tr><td class='l'>{e(r['產業'])}</td>{tds}<td>{cnt.get(r['產業'], 0)}</td></tr>")
    H.append("</table></div><p class='note'>名次差以百分位點表示（0～100）。只列至少一格打勾的產業。</p>")
    # 二、前 5 名單
    H.append("<h2>二、登錄兩種挑法的前 5 名</h2><p class='note'>P1 ＝ 營收在加速的產業裡，名次差最大的 5 個；P2 ＝ 加速排在前三分之一（且大於 0）的產業裡，近 L 日股價漲最少的 5 個。"
             "每格：產業（近 L 日產業指數報酬）。</p>")
    for P_ in PS:
        H.append(f"<h3>{e(PNAME[P_])}</h3><div class='wrap'><table><tr><th class='l'>加速</th>" + "".join(f"<th class='l'>近 {L} 日</th>" for L in LS) + "</tr>")
        for a in AS:
            cells = []
            for L in LS:
                g = PK[(PK["P"] == P_) & (PK["A"] == a) & (PK["L"] == L)].sort_values("名次")
                cells.append("<td class='l'>" + ("<br>".join(f"{int(x['名次'])}. {e(x['產業'])} <small>{P1(x['L報酬'])}</small>" for _, x in g.iterrows()) or "（無）") + "</td>")
            H.append(f"<tr><td class='l'>{e(ANAME[a])}</td>{''.join(cells)}</tr>")
        H.append("</table></div>")
    # 三、全產業表
    H.append("<h2>三、全部產業：加速與股價</h2><div class='sel'>加速用 <select id='s1' onchange='sw()'>" + "".join(f"<option value='{a}'>{e(ANAME[a])}</option>" for a in AS) + "</select></div>")
    for a in AS:
        S = T.copy(); S["_k"] = S[a].where(S["可排名"], -1e9); S = S.sort_values(["_k", "產業"], ascending=[False, True])
        H.append(f"<div class='pane' id='p{a}'><div class='wrap'><table><tr><th class='l'>產業</th><th>{a}<br><small>百分位</small></th>"
                 + "".join(f"<th>近 {L} 日<br><small>報酬／百分位</small></th>" for L in LS) + "".join(f"<th>名次差<br><small>{L} 日</small></th>" for L in LS)
                 + "<th>公司數</th><th>指數<br><small>成員</small></th></tr>")
        for _, r in S.iterrows():
            ok = bool(r["可排名"])
            av = (PT(r[a]) if a != "A1" else P1(r[a])) + (f"<br><small>{PC(r[f'{a}百分位'])}</small>" if ok else "")
            rets = "".join(f"<td>{P1(r[f'ret{L}'])}" + (f"<br><small>{PC(r[f'ret{L}百分位'])}</small>" if ok else "") + "</td>" for L in LS)
            dif = "".join((f"<td class='y'>{PC(r[f'差_{a}_{L}'])}</td>" if ok and bool(r[f"同時_{a}_{L}"]) else f"<td>{PC(r[f'差_{a}_{L}']) if ok else '—'}</td>") for L in LS)
            nm = e(r["產業"]) + ("" if ok else f"<br><small>不排名：{e(str(r['不排名原因']))}</small>")
            H.append(f"<tr><td class='l'>{nm}</td><td><b>{av}</b></td>{rets}{dif}<td>{int(r['公司數'])}</td><td>{int(r['指數成員數（最新量測日）'])}</td></tr>")
        H.append("</table></div></div>")
    H.append("<p class='note'>百分位 0 ＝ 最低、100 ＝ 最高（在可排名產業之間比）。綠底 ＝ 加速 ＞ 0 且名次差 ＞ 0。指數成員 ＝ 最新量測日符合流動性、K 棒數、法人資料三條件（W1）的成分股數。</p>")
    # 四、成員股
    H.append("<h2>四、前 5 名單出現過的產業：市值前 5 大成員</h2><p class='note'>依市值大到小；點產業名稱展開。本益比日期與財報期（民國年／季）附在小字。"
             "W1 ＝ 最新量測日是否在產業指數成分裡。</p>")
    for ind in [k for k, _ in top]:
        g = MB[MB["產業"] == ind].sort_values("市值名次")
        H.append(f"<details><summary>{e(ind)}（前 5 名單出現 {cnt[ind]} 次）</summary><div class='wrap'><table><tr><th class='l'>代號 名稱</th><th>市值<br><small>億</small></th>"
                 "<th>近 3 月<br><small>營收年增</small></th><th>營收創<br><small>24 月新高</small></th><th>近 250 日<br><small>報酬</small></th><th>距 250 日<br><small>低點</small></th><th>本益比</th><th>W1</th></tr>")
        for _, r in g.iterrows():
            pe = "—" if not np.isfinite(r.get("本益比", np.nan)) else f"{r['本益比']:.1f}"
            sm = f"<br><small>{e(str(r.get('本益比日期', '')) if isinstance(r.get('本益比日期', ''), str) else '')} {e(str(r.get('財報期', '')) if isinstance(r.get('財報期', ''), str) else '')}</small>"
            tg = "<br><small>創新板</small>" if r.get("創新板") == "是" else ""
            H.append(f"<tr><td class='l'>{e(str(r['代號']))} {e(str(r.get('名稱', '')))}<br><small>{e(str(r['市場']))}</small>{tg}</td><td>{N1(r.get('市值（億）', np.nan))}</td>"
                     f"<td>{P1(r.get('近3月營收年增', np.nan))}</td><td>{e(str(r.get('營收創24月新高', '')))}</td><td>{P1(r.get('近250日報酬', np.nan))}</td>"
                     f"<td>{P1(r.get('距250日低點', np.nan))}</td><td>{pe}{sm}</td><td>{e(str(r['W1（最新量測日）']))}</td></tr>")
        H.append("</table></div></details>")
    # 名詞與讀法
    nr = META["不排名"]
    H.append("<h2>名詞與讀法</h2><ul class='note'>"
             "<li>A1 ＝ 近 3 個月合計營收年增率；A2 ＝ A1 − 近 12 個月合計年增率；A3 ＝ A1 − 三個月前的 A1。年增用同一份月營收檔的「去年當月營收」當分母、只加總兩邊都有數字的公司。</li>"
             "<li>產業指數 ＝ 產業內符合流動性（近 20 日均額 ≥ 5,000 萬）、K 棒數（≥ 120 根）、法人資料三條件的股票，每天等權平均報酬連乘（還原權息）；成分股每月第一個交易日更新。</li>"
             "<li>近 L 日報酬 ＝ 產業指數最近收盤 ÷ L 個交易日前 − 1。</li>"
             "<li>可排名 ＝ 公司數 ≥ 5、三種加速都有值、三個天數的指數報酬都有值。不排名的產業：" + ("、".join(f"{e(x['產業'])}（{e(x['不排名原因'])}）" for x in nr) or "無") + "。</li>"
             "<li>產業別：上市、上櫃官方產業別（現值），名稱相同合併；排除金融保險、其他、存託憑證、ETF；名稱空白的上櫃代碼 32、33 標為文化創意業、農業科技業。"
             "產業營收只算 8 月營收可用日前已上市櫃的公司。</li>"
             "<li>母體採新口徑（創新板只剔在板期間、興櫃日不算）。</li></ul>")
    H.append("<script>function sw(){var a=document.getElementById('s1').value;document.querySelectorAll('.pane').forEach(x=>x.classList.toggle('on',x.id=='p'+a))}sw()</script></main></body></html>")
    open(os.path.join(OUT, "產業營收加速但股價落後_現況.html"), "w", encoding="utf-8").write("\n".join(H))
    log("[網頁] 完成")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); ap.add_argument("--page", action="store_true")
    ap.add_argument("--procs", type=int, default=3); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); T0 = time.time()
    logf = open(os.path.join(OUT, "run_check.log" if a.check else ("run_page.log" if a.page else "run.log")), "w", encoding="utf-8")

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(str(m) + "\n"); logf.flush()
    if a.check:
        check(log)
    elif a.page:
        page(log)
    else:
        run(a, log)
        page(log)


if __name__ == "__main__":
    main()
