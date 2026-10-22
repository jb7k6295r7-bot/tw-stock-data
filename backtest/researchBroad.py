# -*- coding: utf-8 -*-
"""廣撒長抱 seq1【正式跑】（台股策略線 組合層登錄 sha 4f73227473ff654a；裁定 seq454 §一 發號（6 格挑 1、N_組合 ＋1、最多暫定）、
seq455 §二 核開跑：不做 36 月去重、不加 500 張閘（加閘版只描述）；早年退化格標「依構造不可判定」（處理同 seq455 §一.2）；早年價格 reduce_v2（seq335）；
結果句必附「實際照做不可行（同時持有約 170～890 檔），只回答訊號有沒有加分」；顧廣平 (2010) 本線未讀原文）——回測線計算子代理。
⛔ 不 commit、不改既有檔；researchBroad_freq（頻率表：step_prep、step_freq、sim、BT／LX 快取、NSL、SEGS、SEED）、researchRevTurn_freq（ensure_data、prices）、
   researchShortageExit（seam_open）、researchIndMom_freq（reg_check）、rerun17（load_bench）⛔ 只 import。

    cd ~/tw-p17
    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBroad --sha <頻率表同一版> --step rebuild
    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBroad --sha <同上> --step rand --g G1|G2 [--dry0] [--nrep N]
    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBroad --sha <同上> --step main [--dry0]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBroad_check [--dry0]
輸出 backtest/resultsBroad/main/（乾跑 ~/brdwork/dry0）：main.json、cells.csv、vs_broad.csv、random.csv、batches.csv.gz、yearly.csv、m25_36.csv、gated.csv、
     nav.csv.gz、run.log

═══ 讀法（N 標；頻率表讀法 B0～B12 原樣沿用；以下為正式跑新增；⛔ 在讀任何本件報酬之前寫死於 2026-10-23（台北）；★＝執行者定）═══
 N1 頻率表重建：researchBroad_freq.step_prep＋step_freq 原樣（同一 --sha）重建到 ~/brdwork/rebuild，cells、batches、overlap、random_frame 與已 commit 的
    resultsBroad/freq 逐字比，任一不同 ⇒ 中止。另以乾跑（R 全 0）帳逐日比對頻率表 sim 的持股金額（每格 max 差 ＜ 1e−9）⇒ 帳相同。
 N2 帳（R ≠ 0）：每批金額 ★ ＝ min(前一日收盤權益 ÷ n_H, 可用現金)（R 全 0 時 ＝ 頻率表 min(1 ÷ n_H, 1 − 占用)）；可用現金 ＝ 權益 − 未回收各批的現值
    （含該批買不到、提前出場留下的現金；登錄「停止交易強制出場、該部分放現金到該批到期」）。各筆：進場 ＝ b 還原開盤（主世界乘接縫倍數，seam_open），
    市值 ＝ 金額 × 還原收盤（★ 無成交日沿用前一有效收盤）÷ 進場價；出場日收盤賣成現金（留在該批到回收日）；回收日（＝ 到期或順延後最後賣出日）收盤後
    整批現值回到可用現金。走不完的筆持有到資料尾、按市值計。
 N3 成本：★ 0.585%／來回在買進時一次扣（持有到尾的筆也扣）；現實版 ★ 每邊再加 0.3%（＝ researchSlip「現實版」的每邊 ＋0.3%；衝擊 σ20×√(5 萬÷ADV20)、
    均價成交、一字跌停賣不掉未做：本面板無 ADV 欄，照註）。
 N4 指標（登錄 §三）：段窗 ＝ 頻率表 B7（早年 2012-06-01～2016-12-31、探索 2017-03-01～2021-12-31、確認 2022-01-01～資料尾 2026-09-24）；
    基準點 ＝ 段首前一交易日收盤；年化 ＝ (末 ÷ 基)^(365.25 ÷ 日曆天) − 1；MDD ＝ 窗內（含基準點）最大回落；比值 ＝ 年化 ÷ |MDD|。
    大盤報酬指數 ＝ origin/main data/history/market_tri.csv（★ 合併日曆 ffill）；0050 只當一列（rerun17.load_bench：主段 H2D、早年 eotc，接縫以收盤比接）。
    合格 ＝ 年化 ＞ 大盤 ∧ 比值 ≥ 大盤；另列 ＝ 只贏報酬；其餘不合格。
 N5 挑格與判定：探索段 6 格（G1、G2 × H）依「合格 ＞ 另列 ＞ 不合格」再依比值挑 1（★ 同級比值高者）；判定 ＝ 確認段與早年段取較嚴；
    早年依頻率表 cells.csv「退化」為真者標「依構造不可判定」⇒ 只看確認段、結果句寫「早年不可判、只看確認段」；一律最多「暫定」。
 N6 訊號有沒有加分（裁定 seq454 必答、主比較）：各格 對 同 H「純廣撒」的年化差、比值差（三段）；隨機 1,000 次（頻率表 B11 同一抽法：default_rng([20261022, r])、
    每批從 W1∩面板依代號排序 permutation 取與訊號同數）⇒ 報 隨機年化 ≥ 訊號格 的比例、隨機比值 ≥ 訊號格 的比例、隨機年化中位。
    ★ 「訊號加分」＝ 確認段 年化差（對純廣撒）＞ 0 且 隨機 ≥ 訊號 的比例 ＜ 5%；兩條都不成立 ⇒「沒有加分」；其餘 ⇒「分不出」（描述語，判定仍以 N5 為準）。
 N7 必報（登錄 §四）：平均持股、現金（頻率表）；各批 H 天報酬（＝ 回收時整批現值 ÷ 投入 − 1，已扣成本；平均、中位，依段）；各批前 5／後 5 筆對整批損益的貢獻
    （★ Σ前5 損益 ÷ Σ整批損益（全部回收批加總）與批中位）；各年報酬（日曆年，含大盤、0050、純廣撒）；換手（頻率表）與成本拖累（★ 年扣成本 ÷ 平均權益）；
    H＝750 批的第 25～36 個月 ★ ＝ 第 501～750 交易日（整批現值 b＋749 ÷ b＋499 − 1），附大盤同窗。
 N8 加閘版（只描述，seq455）：批成員再限 500 張閘 G[A−1]（＝ G[b−2]，營收轉強驗證 V3 同式）；只報三段年化、MDD、比值。
 N7′ 投入 ＝ 0 的批（份數被現金卡住、可用現金為 0）不入批報酬、第 25～36 月統計（★）。
 N10 ⚠ 看結果後修的錯（照報）：第一次正式跑 sim_nav 算「前一日權益」時，回收日恰為 b−1 的批被重複計入（已回到可用現金、又仍在 contrib[b−1]）；
    只影響 H500、H750（權益曲線最大相對差約 0.1%）。修正後依 seq366 先乾跑（R 全 0）再整份重跑；第一次結果存 ~/brdwork/first_run_buggy/ 備查。
 N9 先驗（登錄 §六，寫死不改）：① 挑中格兩段都合格（早年不可判 ⇒ 只看確認段，照註）；② 挑中格 ★ 確認段年化 − 純廣撒 ≤ 2 點；
    ③ H＝750 第 25～36 個月報酬（訊號兩格批平均）為負；④ ★ 挑中格 Σ前5 損益 ÷ Σ整批損益 ≥ 0.5。
"""
from __future__ import annotations

import argparse
import heapq
import io
import json
import os
import pickle
import shutil
import subprocess
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchBroad_freq as BF               # noqa: E402  頻率表（⛔ 只 import）
from backtest import researchRevTurn_freq as RT             # noqa: E402
from backtest import researchShortageExit as SM             # noqa: E402
from backtest import researchIndMom_freq as IMF             # noqa: E402

OUT = "backtest/resultsBroad/main"
FREQ = BF.OUT
REB = os.path.join(BF.WK, "rebuild")
RUL = ("seq454", "seq455")
COST = 0.00585
SLIP_SIDE = 0.003
SIGC = [(G, H) for G in ("G1", "G2") for H in BF.HS]
FILES = ["cells.csv", "batches.csv.gz", "overlap.csv", "random_frame.csv"]
SENT_FIXED = ["實際照做不可行（同時持有約 170～890 檔），只回答訊號有沒有加分",
              "顧廣平 (2010)：登錄引為 H＝750 反轉依據，本線未讀原文",
              "看過 3 倍命中率與營收轉強結果才提 ⇒ 結論最多暫定",
              "早年 W1 只有上市、2015-01～07 沒有 W1（不成批）；早年價格 eotc＋reduce_v2 壞根（seq335，約 0.3% 註）",
              "現實版只加每邊 0.3%，衝擊與均價成交未做"]
log = BF.log
LOG = BF.LOG
_S: dict = {}


# ═════════════ N1 重建 ═════════════
def step_rebuild(a):
    if os.path.isdir(REB):
        shutil.rmtree(REB)
    os.makedirs(REB)
    BF.OUT = REB
    try:
        BF.step_prep(a); BF.step_freq(a)
    finally:
        BF.OUT = FREQ
    res = {}
    for f in FILES:
        x = pd.read_csv(os.path.join(REB, f), dtype=str, keep_default_na=False); y = pd.read_csv(os.path.join(FREQ, f), dtype=str, keep_default_na=False)
        res[f] = bool(x.shape == y.shape and list(x.columns) == list(y.columns) and (x.values == y.values).all())
    J = {"sha": a.sha, "相同": res, "全同": all(res.values()), "時間": str(pd.Timestamp.now(tz="Asia/Taipei"))}
    json.dump(J, open(os.path.join(BF.WK, "rebuild.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[N1 重建] {J}")
    if not J["全同"]:
        raise SystemExit("⛔ 頻率表重建不同")


# ═════════════ 共用：載入 ═════════════
def load(a):
    RB = json.load(open(os.path.join(BF.WK, "rebuild.json"), encoding="utf-8"))
    if not (RB["全同"] and RB["sha"] == a.sha):
        raise SystemExit(f"⛔ 重建未全同或 sha 不符 {RB}")
    PR = pickle.load(open(os.path.join(BF.WK, f"prep_{a.sha[:12]}.pkl"), "rb"))
    sha, DN, MD = RT.ensure_data(a.sha)
    PX = RT.prices(sha, DN, a.procs)
    O, nseam = SM.seam_open(PX)
    Cf = np.ascontiguousarray(pd.DataFrame(PX["C"].T).ffill().to_numpy().T)   # ★ 無成交日沿用前一有效收盤（只在持有區間內用）
    return RB, PR, PX, O, Cf, nseam, (sha, DN, MD)


# ═════════════ N2 帳 ═════════════
def sim_nav(members, H, zero, cextra=0.0, want=False):
    """⇒ dict：nav、held（持股市值）、批資訊（want ＝ True 才存逐筆）。全域 _S：BT、LX、Cf、O、ix、CEND。"""
    BT, LX, Cf, O, ix, CEND = _S["BT"], _S["LX"], _S["Cf"], _S["O"], _S["ix"], _S["CEND"]
    n = CEND + 1; nH = BF.NSL[H]
    c = 0.0 if zero else COST + cextra
    contrib = np.zeros(n); held = np.zeros(n); fdelta = np.zeros(n + 2)
    free = 1.0; pend = []; binfo = []; costpaid = np.zeros(n)
    for j, x in enumerate(BT):
        b = x["b"]; mat = b + H - 1
        dbl = 0.0
        while pend and pend[0][0] < b:
            r, v = heapq.heappop(pend); free += v
            if r == b - 1:
                dbl += v            # 修正（看結果後，照報）：回收日 ＝ b−1 的批，其值已在 contrib[b−1]，又已回到 free ⇒ 扣掉重複
        eq_prev = free + contrib[b - 1] - dbl
        Aj = min(eq_prev / nH, max(free, 0.0)) if not zero else min(1.0 / nH, max(free, 0.0))
        free -= Aj; fdelta[b] -= Aj
        lst = members[j]
        r = mat if mat <= CEND else 10 ** 9
        lots = []
        for s in lst:
            i = ix[s]; q, why = LX[(i, b, H)]
            lots.append((i, q))
            if q is not None and q > mat:
                r = 10 ** 9 if q > CEND else max(r, q)
        rr = min(r, CEND); L = rr - b + 1
        path = np.zeros(L)
        per = Aj / len(lst) if lst else 0.0
        unspent = Aj if not lst else 0.0
        lotrec = []
        for i, q in lots:
            if q is None:
                unspent += per; continue
            qq = min(q, CEND)
            if zero:
                v = np.full(qq - b + 1, per)
            else:
                v = per * (1 - c) * Cf[i, b:qq + 1] / O[i, b]
                costpaid[b] += per * c
            path[:qq - b + 1] += v
            if q <= CEND:
                path[qq - b + 1:] += v[-1]
                held[b:qq] += v[:-1]
            else:
                held[b:CEND + 1] += v
            if want:
                lotrec.append((i, float(v[-1]) - per, float(v[min(499, len(v) - 1)]) if H == 750 else np.nan))
        path += unspent
        contrib[b:rr + 1] += path
        if r != 10 ** 9:
            heapq.heappush(pend, (r, float(path[-1])))
            fdelta[r + 1] += path[-1]
        bi = {"j": j, "b": b, "Aj": Aj, "r": r, "完": r != 10 ** 9 and mat <= CEND, "末值": float(path[-1])}
        if H == 750 and mat <= CEND and L >= 750:
            bi["v499"] = float(path[499]); bi["v749"] = float(path[749])
        if want:
            bi["lots"] = lotrec
        binfo.append(bi)
    nav = 1.0 + np.cumsum(fdelta)[:n] + contrib
    return {"nav": nav, "held": held, "binfo": binfo, "cost": costpaid}


def seg_bounds(CAL, CEND, first_b):
    out = {}
    for nm, x_, y_ in BF.SEGS:
        a_ = max(int(CAL.searchsorted(pd.Timestamp(x_))), first_b); z_ = min(int(CAL.searchsorted(pd.Timestamp(y_), "right")) - 1, CEND)
        out[nm] = (a_ - 1, z_)
    return out


def metr(nav, CAL, a0, z):
    w = np.asarray(nav[a0:z + 1], float)
    if not (len(w) > 1 and np.isfinite(w).all() and w[0] > 0):
        return {"年化": np.nan, "MDD": np.nan, "比值": np.nan}
    yrs = (CAL[z] - CAL[a0]).days / 365.25
    cg = (w[-1] / w[0]) ** (1 / yrs) - 1
    mdd = float((w / np.maximum.accumulate(w) - 1).min())
    return {"年化": float(cg), "MDD": mdd, "比值": float(cg / abs(mdd)) if mdd < 0 else np.nan}


def grade(m, mk):
    if not np.isfinite(m["年化"]):
        return "不可算"
    if m["年化"] > mk["年化"] and m["比值"] >= mk["比值"]:
        return "合格"
    if m["年化"] > mk["年化"]:
        return "另列"
    return "不合格"


GR = {"合格": 2, "另列": 1, "不合格": 0, "不可算": -1}


# ═════════════ 隨機 ═════════════
def _rand_job(args):
    G, r, zero = args
    BT = _S["BT"]
    rng = np.random.default_rng([BF.SEED, r])
    draw = []
    for x in BT:
        pool = sorted(x["W1"]); nb = len(x[G])
        draw.append([pool[k] for k in rng.permutation(len(pool))[:nb]] if nb else [])
    out = []
    for H in BF.HS:
        nav = sim_nav(draw, H, zero)["nav"]
        for nm, (a0, z) in _S["SB"].items():
            out.append((G, r, H, nm, *[metr(nav, _S["CAL"], a0, z)[k] for k in ("年化", "MDD", "比值")]))
    return out


def step_rand(a):
    t0 = time.time()
    RB, PR, PX, O, Cf, nseam, _ = load(a)
    CAL = PX["CAL"]; CEND = len(CAL) - 1
    _S.update(BT=PR["BT"], LX=PR["LX"], Cf=Cf, O=O, ix=PX["ix"], CEND=CEND, CAL=CAL, SB=seg_bounds(CAL, CEND, PR["BT"][0]["b"]))
    nrep = a.nrep or BF.NRAND
    r0, r1 = (a.r0 or 0), (a.r1 if a.r1 is not None else nrep)
    tag = "dry0" if a.dry0 else "real"
    rows = []
    with Pool(a.procs) as pool:
        for k, res in enumerate(pool.imap_unordered(_rand_job, [(a.g, r, a.dry0) for r in range(r0, r1)], chunksize=4)):
            rows.extend(res)
            if (k + 1) % 100 == 0:
                log(f"  隨機 {a.g} {k + 1}／{r1 - r0}｜{time.time() - t0:.0f}s")
    df = pd.DataFrame(rows, columns=["G", "r", "H", "段", "年化", "MDD", "比值"])
    df.to_pickle(os.path.join(BF.WK, f"randpart_{a.g}_{tag}_{r0}_{r1}.pkl"))
    # 各段接起來：r 覆蓋 0..nrep−1 不重不漏才寫總檔
    import glob as _g
    parts = [pd.read_pickle(f) for f in sorted(_g.glob(os.path.join(BF.WK, f"randpart_{a.g}_{tag}_*.pkl")))]
    al = pd.concat(parts).drop_duplicates(["G", "r", "H", "段"])
    if sorted(al["r"].unique()) == list(range(nrep)):
        al.sort_values(["G", "H", "段", "r"]).to_pickle(os.path.join(BF.WK, f"rand_{a.g}_{tag}.pkl"))
        log(f"[隨機] {a.g} 全部 {nrep} 次接齊 ⇒ rand_{a.g}_{tag}.pkl")
    log(f"[隨機] {a.g} r {r0}～{r1 - 1} ⇒ {len(df)} 列｜{time.time() - t0:.0f}s")


# ═════════════ 主 ═════════════
def step_main(a):
    t0 = time.time()
    out = os.path.join(BF.WK, "dry0") if a.dry0 else OUT
    os.makedirs(out, exist_ok=True)
    reg = IMF.reg_check(BF.REG_SHA)
    dirs = [IMF.MAILBOX] + sorted(__import__("glob").glob(os.path.join(IMF.MAILBOX, "_封存-*")))
    ruls = {q: [os.path.basename(f) for d in dirs for f in __import__("glob").glob(os.path.join(d, "*.md")) if q in os.path.basename(f) and "裁定線-" in os.path.basename(f)] for q in RUL}
    if not all(ruls.values()):
        raise SystemExit(f"⛔ 裁定信缺 {ruls}")
    log(f"[登錄] {reg}｜裁定 {ruls}")
    RB, PR, PX, O, Cf, nseam, (sha, DN, MD) = load(a)
    CAL, ix = PX["CAL"], PX["ix"]; CEND = len(CAL) - 1; BT = PR["BT"]
    _S.update(BT=BT, LX=PR["LX"], Cf=Cf, O=O, ix=ix, CEND=CEND, CAL=CAL)
    SB = seg_bounds(CAL, CEND, BT[0]["b"]); _S["SB"] = SB
    Z = a.dry0
    MEM = {"G1": [x["G1"] for x in BT], "G2": [x["G2"] for x in BT], "純廣撒": [x["W1"] for x in BT]}
    G_ = PX["G"]
    MEMG = {G: [[s for s in x[G] if G_[ix[s], x["b"] - 2]] for x in BT] for G in ("G1", "G2")}
    # ── 乾跑帳 ＝ 頻率表帳（N1 後半）
    eqchk = {}
    for G in ("G1", "G2", "純廣撒"):
        for H in BF.HS:
            d0 = sim_nav(MEM[G], H, True)
            f0 = BF.sim(PR, MEM[G], H)
            eqchk[f"{G} H{H}"] = float(np.max(np.abs(d0["held"] - f0["inv"])))
    log(f"[N1 帳相同] max|持股差| {eqchk}")
    if max(eqchk.values()) > 1e-9:
        raise SystemExit("⛔ 乾跑帳 ≠ 頻率表帳")
    # ── 基準
    tri = pd.read_csv(io.BytesIO(subprocess.run(["git", "show", f"{sha}:data/history/market_tri.csv"], capture_output=True, check=True).stdout))
    tri["date"] = pd.to_datetime(tri["date"]); tri = tri.drop_duplicates("date").set_index("date")["close"].astype(float)
    TRI = tri.reindex(tri.index.union(CAL)).ffill().reindex(CAL).to_numpy(float)
    from backtest import rerun17 as RR
    import backtest.data as D
    NE = PX["NE"]
    D.DATA = PX["early_data"]; be = RR.load_bench(CAL[:NE])
    D.DATA = RR.H2D; bm = RR.load_bench(CAL[NE:])
    b50 = np.concatenate([be, bm * (be[-1] / bm[0])]) if (np.isfinite(be[-1]) and np.isfinite(bm[0])) else np.concatenate([be, bm])
    if Z:
        TRI = np.ones(len(CAL)); b50 = np.ones(len(CAL))
    BM_ = {"大盤報酬指數": TRI, "0050": b50}
    # ── 各格
    RES = {}
    for G in ("G1", "G2", "純廣撒"):
        for H in BF.HS:
            RES[(G, H, "b")] = sim_nav(MEM[G], H, Z, 0.0, want=True)
            RES[(G, H, "r")] = sim_nav(MEM[G], H, Z, 2 * SLIP_SIDE)
    for G in ("G1", "G2"):
        for H in BF.HS:
            RES[(G + "加閘", H, "b")] = sim_nav(MEMG[G], H, Z)
    log(f"[帳] {len(RES)} 條｜{time.time() - t0:.0f}s")
    FC = pd.read_csv(os.path.join(FREQ, "cells.csv"), encoding="utf-8-sig")
    deg = {(r["格"], int(r["H"])): bool(r["退化(平均持股<10或現金>30%)"]) for r in FC[FC["段"] == "早年"].to_dict("records")}
    CE = []
    MK = {nm: {k: metr(v, CAL, a0, z) for k, v in BM_.items()} for nm, (a0, z) in SB.items()}
    for (G, H, v), R_ in RES.items():
        for nm, (a0, z) in SB.items():
            m = metr(R_["nav"], CAL, a0, z)
            row = {"格": G, "H": H, "版本": {"b": "0.585%", "r": "現實版"}[v], "段": nm, **m, "大盤年化": MK[nm]["大盤報酬指數"]["年化"], "大盤MDD": MK[nm]["大盤報酬指數"]["MDD"],
                   "大盤比值": MK[nm]["大盤報酬指數"]["比值"], "標籤": grade(m, MK[nm]["大盤報酬指數"]),
                   "早年退化(依構造不可判定)": (deg.get((G, H)) if nm == "早年" else None)}
            fr = FC[(FC["格"] == G) & (FC["H"] == H) & (FC["段"] == nm)]
            if len(fr):
                row["同時持有平均(頻率表)"] = float(fr["同時持有不同代號平均"].iloc[0]); row["平均現金(頻率表)"] = float(fr["平均現金比例"].iloc[0])
            yrs = (CAL[z] - CAL[a0]).days / 365.25
            row["成本拖累(年扣÷平均權益)"] = float(R_["cost"][a0 + 1:z + 1].sum() / yrs / np.mean(R_["nav"][a0:z + 1]))
            CE.append(row)
    for nm, (a0, z) in SB.items():
        for k in BM_:
            CE.append({"格": k, "H": None, "版本": "基準", "段": nm, **MK[nm][k], "大盤年化": MK[nm]["大盤報酬指數"]["年化"], "大盤MDD": MK[nm]["大盤報酬指數"]["MDD"],
                       "大盤比值": MK[nm]["大盤報酬指數"]["比值"], "標籤": ("基準" if k == "大盤報酬指數" else grade(MK[nm][k], MK[nm]["大盤報酬指數"]))})
    CE = pd.DataFrame(CE)

    def cm(G, H, nm, v="0.585%"):
        return CE[(CE["格"] == G) & (CE["H"] == H) & (CE["段"] == nm) & (CE["版本"] == v)].iloc[0]
    # ── N5 挑格與判定
    ex = sorted(SIGC, key=lambda gh: (GR[cm(*gh, "探索")["標籤"]], cm(*gh, "探索")["比值"] if np.isfinite(cm(*gh, "探索")["比值"]) else -9), reverse=True)
    pick = ex[0]
    lc = cm(*pick, "確認")["標籤"]; le = cm(*pick, "早年")["標籤"]; edeg = bool(deg.get(pick))
    labs = [lc] if edeg else [lc, le]
    fin = min(labs, key=lambda s: GR[s])
    verdict = {"合格": "合格（暫定）", "另列": "另列：只贏報酬（暫定）", "不合格": "不合格", "不可算": "不可算"}[fin] + ("；早年不可判、只看確認段" if edeg else "")
    log(f"[N5] 挑中 {pick}（探索 {cm(*pick, '探索')['標籤']}）｜確認 {lc}｜早年 {'依構造不可判定' if edeg else le}｜判定 {verdict}")
    # ── N6 對純廣撒、隨機
    VS = []
    RD = {}
    for G in ("G1", "G2"):
        fp = os.path.join(BF.WK, f"rand_{G}_{'dry0' if Z else 'real'}.pkl")
        RD[G] = pd.read_pickle(fp) if os.path.exists(fp) else None
    for G, H in SIGC:
        for nm in ("早年", "探索", "確認"):
            s, b_ = cm(G, H, nm), cm("純廣撒", H, nm)
            row = {"格": G, "H": H, "段": nm, "訊號年化": s["年化"], "純廣撒年化": b_["年化"], "年化差(點)": (s["年化"] - b_["年化"]) * 100,
                   "訊號比值": s["比值"], "純廣撒比值": b_["比值"], "比值差": s["比值"] - b_["比值"]}
            rd = RD[G]
            if rd is not None:
                d = rd[(rd["H"] == H) & (rd["段"] == nm)]
                row.update({"隨機次數": len(d), "隨機年化中位": float(d["年化"].median()), "隨機年化≥訊號比例": float((d["年化"] >= s["年化"]).mean()),
                            "隨機比值中位": float(d["比值"].median()), "隨機比值≥訊號比例": float((d["比值"] >= s["比值"]).mean())})
            VS.append(row)
    VS = pd.DataFrame(VS)
    vp = VS[(VS["格"] == pick[0]) & (VS["H"] == pick[1]) & (VS["段"] == "確認")].iloc[0]
    if "隨機年化≥訊號比例" in VS.columns:
        if vp["年化差(點)"] > 0 and vp["隨機年化≥訊號比例"] < 0.05:
            plus = "訊號有加分（描述）"
        elif vp["年化差(點)"] <= 0 and vp["隨機年化≥訊號比例"] >= 0.05:
            plus = "訊號沒有加分（描述）"
        else:
            plus = "訊號加不加分分不出（描述）"
    else:
        plus = "隨機未跑"
    # ── N7 批、貢獻、各年、第 25～36 月
    BA = []; CT = []; M25 = []
    for G in ("G1", "G2", "純廣撒"):
        for H in BF.HS:
            R_ = RES[(G, H, "b")]
            t5 = b5 = tot = 0.0; shares = []
            for bi in R_["binfo"]:
                sg = BF.segof(CAL[bi["b"]])
                ret = (bi["末值"] / bi["Aj"] - 1) if (bi["完"] and bi["Aj"] > 0) else np.nan
                BA.append({"格": G, "H": H, "批日": str(CAL[bi["b"]].date()), "段": sg, "投入": bi["Aj"], "完": bi["完"], "批報酬": ret,
                           "第25-36月": ((bi["v749"] / bi["v499"] - 1) if "v499" in bi and bi["v499"] > 0 else np.nan),
                           "大盤第25-36月": ((TRI[bi["b"] + 749] / TRI[bi["b"] + 499] - 1) if "v499" in bi else np.nan)})
                if bi["完"] and bi["lots"]:
                    pn = sorted(x[1] for x in bi["lots"]); bp = bi["末值"] - bi["Aj"]
                    t5 += sum(pn[-5:]); b5 += sum(pn[:5]); tot += bp
                    if bp > 0:
                        shares.append(sum(pn[-5:]) / bp)
            CT.append({"格": G, "H": H, "回收批": int(sum(1 for bi in R_["binfo"] if bi["完"])), "Σ前5損益÷Σ整批損益": (t5 / tot if tot else np.nan),
                       "Σ後5損益÷Σ整批損益": (b5 / tot if tot else np.nan), "前5占比批中位(整批賺錢者)": (float(np.median(shares)) if shares else np.nan)})
    BA = pd.DataFrame(BA); CT = pd.DataFrame(CT)
    BS = BA.groupby(["格", "H", "段"]).agg(批數=("批報酬", "size"), 回收批=("批報酬", "count"), 批報酬平均=("批報酬", "mean"), 批報酬中位=("批報酬", "median")).reset_index()
    for G in ("G1", "G2", "純廣撒"):
        d = BA[(BA["格"] == G) & (BA["H"] == 750)].dropna(subset=["第25-36月"])
        M25.append({"格": G, "H": 750, "批數": len(d), "第25-36月平均": float(d["第25-36月"].mean()) if len(d) else np.nan,
                    "第25-36月中位": float(d["第25-36月"].median()) if len(d) else np.nan, "大盤同窗平均": float(d["大盤第25-36月"].mean()) if len(d) else np.nan,
                    "＜0批比例": float((d["第25-36月"] < 0).mean()) if len(d) else np.nan})
    M25 = pd.DataFrame(M25)
    YR = []
    yrs_ = sorted(set(CAL[BT[0]["b"]:].year))
    series = {f"{G} H{H}": RES[(G, H, "b")]["nav"] for G in ("G1", "G2", "純廣撒") for H in BF.HS}
    series.update({"大盤報酬指數": TRI, "0050": b50})
    for y in yrs_:
        pos = np.flatnonzero(CAL.year == y); p0 = pos[0] - 1; p1 = pos[-1]
        if p0 < BT[0]["b"] - 1:
            p0 = BT[0]["b"] - 1
        YR.append({"年": int(y), **{k: float(v[p1] / v[p0] - 1) for k, v in series.items()}})
    YR = pd.DataFrame(YR)
    GT = CE[CE["格"].str.endswith("加閘", na=False)].copy()
    # ── 先驗
    pc = cm(*pick, "確認"); bc = cm("純廣撒", pick[1], "確認")
    sm25 = M25[M25["格"].isin(["G1", "G2"])]["第25-36月平均"]
    ctp = CT[(CT["格"] == pick[0]) & (CT["H"] == pick[1])].iloc[0]
    PRI = [{"先驗": "① 挑中格兩段都合格（約四成）", "實際": f"確認 {lc}｜早年 {'依構造不可判定' if edeg else le}", "中": bool(lc == "合格" and (edeg or le == "合格")),
            "註": "早年不可判 ⇒ 只看確認段" if edeg else ""},
           {"先驗": "② 挑中格不比純廣撒好超過 2 點年化（約六成；★ 確認段）", "實際": f"{(pc['年化'] - bc['年化']) * 100:+.2f} 點", "中": bool((pc["年化"] - bc["年化"]) * 100 <= 2)},
           {"先驗": "③ H＝750 第 25～36 個月報酬為負（約五成；★ G1、G2 批平均皆 ＜ 0）", "實際": " ／ ".join(f"{v:+.4f}" for v in sm25), "中": bool((sm25 < 0).all())},
           {"先驗": "④ 組合報酬靠各批前 5 檔撐一半以上（約六成五；★ 挑中格 Σ前5÷Σ整批）", "實際": f"{ctp['Σ前5損益÷Σ整批損益']:.3f}", "中": bool(ctp["Σ前5損益÷Σ整批損益"] >= 0.5)}]
    sent = [f"廣撒長抱（每月營收訊號股全買、抱 H 天）：探索段挑中 {pick[0]} H{pick[1]}，判定 {verdict}；確認段年化 {pc['年化'] * 100:+.2f}%、MDD {pc['MDD'] * 100:.1f}%"
            f"（大盤 {pc['大盤年化'] * 100:+.2f}%／{pc['大盤MDD'] * 100:.1f}%）；對同 H 純廣撒年化差 {vp['年化差(點)']:+.2f} 點"
            + (f"、隨機 1,000 次年化 ≥ 訊號 {vp['隨機年化≥訊號比例'] * 100:.1f}%" if "隨機年化≥訊號比例" in VS.columns else "") + f" ⇒ {plus}"] + SENT_FIXED
    # ── 輸出
    CE.to_csv(os.path.join(out, "cells.csv"), index=False, encoding="utf-8-sig")
    VS.to_csv(os.path.join(out, "vs_broad.csv"), index=False, encoding="utf-8-sig")
    BA.to_csv(os.path.join(out, "batches.csv.gz"), index=False, encoding="utf-8-sig", compression="gzip")
    BS.to_csv(os.path.join(out, "batch_stats.csv"), index=False, encoding="utf-8-sig")
    CT.to_csv(os.path.join(out, "top5.csv"), index=False, encoding="utf-8-sig")
    M25.to_csv(os.path.join(out, "m25_36.csv"), index=False, encoding="utf-8-sig")
    YR.to_csv(os.path.join(out, "yearly.csv"), index=False, encoding="utf-8-sig")
    GT.to_csv(os.path.join(out, "gated.csv"), index=False, encoding="utf-8-sig")
    rr = []
    for G in ("G1", "G2"):
        if RD[G] is not None:
            rr.append(RD[G].groupby(["G", "H", "段"]).agg(次數=("r", "size"), 年化中位=("年化", "median"), 年化p5=("年化", lambda x: x.quantile(.05)),
                                                        年化p95=("年化", lambda x: x.quantile(.95)), 比值中位=("比值", "median")).reset_index())
    if rr:
        pd.concat(rr).to_csv(os.path.join(out, "random.csv"), index=False, encoding="utf-8-sig")
    NV = pd.DataFrame({"date": CAL.strftime("%Y-%m-%d"), **{k: v for k, v in series.items()}})
    NV.iloc[BT[0]["b"] - 1:].to_csv(os.path.join(out, "nav.csv.gz"), index=False, encoding="utf-8-sig", compression="gzip")
    shutil.copy(os.path.join(BF.WK, "rebuild.json"), os.path.join(out, "rebuild.json"))
    MJ = {"性質": "廣撒長抱 seq1 正式跑（組合層 6 格挑 1，N_組合 ＋1）" + ("【乾跑：R 全 0】" if Z else ""), "登錄": f"sha {BF.REG_SHA}（{reg}）", "裁定": ruls,
          "origin/main": sha, "頻率表重建": RB, "乾跑帳＝頻率表帳": eqchk, "接縫開盤倍數檔數": nseam, "挑中": list(pick), "探索段排序": [list(x) for x in ex],
          "判定": verdict, "訊號加分": plus, "早年退化格": {f"{k[0]} H{k[1]}": v for k, v in deg.items()}, "先驗": PRI, "結果句": sent,
          "乾跑0": bool(Z), "讀法": __doc__.split("═══ 讀法")[1], "秒": round(time.time() - t0)}
    json.dump(MJ, open(os.path.join(out, "main.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=RT.jdef)
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    log(f"[完成] {out}｜{time.time() - t0:.0f}s")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=4); ap.add_argument("--sha", required=True)
    ap.add_argument("--step", choices=["rebuild", "rand", "main"], required=True); ap.add_argument("--dry0", action="store_true")
    ap.add_argument("--g", choices=["G1", "G2"]); ap.add_argument("--nrep", type=int, default=None)
    ap.add_argument("--r0", type=int, default=None); ap.add_argument("--r1", type=int, default=None)
    a = ap.parse_args()
    if a.step == "rebuild":
        step_rebuild(a)
    elif a.step == "rand":
        step_rand(a)
    else:
        step_main(a)


if __name__ == "__main__":
    main()
