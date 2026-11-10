# -*- coding: utf-8 -*-
"""額外策略「營量 v1、營飆 v1 加『同族群營收也一起轉強』（只買版、優先版）」【頻率表・重疊度・等價檢查・乾跑】——回測線計算子代理，2026-11-10。
登錄：台股策略線 seq2（sha e72a759aefc7bfdc，6686 B；取代 seq1 8c0f6b403ebae89d）〈營量營飆加族群營收也轉強_只買版與優先版_組合層登錄〉
發號：裁定線 seq501 §三（N_組合 ＋4；最多「合格（暫定）」；優先版對原版買進重疊 ≥ 90% ⇒ 頻率表照報後先回信、正式標「等同原版」；
      優先版換掉的買進 ＜ 10% ⇒ 先回信；族群分群檔請產業提供，取不到照定義重建並報一致率；先交頻率表（含重疊度三項，⛔ 不附報酬））
族群定義：產業分析線 seq111（20261110-2008 件；定義全文在產業〈事前登錄_族群營收轉強能否讓營收新高訊號更準_20261110〉，本機取不到）

⛔ 乾跑：不讀、不算、不印任何報酬。引擎 research11.simulate_mtm 以「價格全為 1、毛報酬全為 0」跑（權益只隨成本下滑）⇒ 買進、持股、空槽是純構造量；
   ⛔ 日報酬相關係數需要報酬 ⇒ 本階段只報「算得出」。⛔ 不改策略鎖內任何檔（research11、rerun17、data… 只 import）；跑完 strategy_lock --check。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchGroupRevUp_freq --step world --world main|early [--procs 3]
    … --step groups --world main|early [--procs 3]｜--step sim --world main|early [--procs 3]｜--step report
    自測：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.selftest_researchGroupRevUp_freq

═══ 讀法（寫死於 2026-11-10（台北），在算任何本件數字之前；★ ＝ 登錄沒寫清楚、執行者定；〔 〕＝ 另一讀法並報）═══
 F0 登錄驗證：信箱登錄全文去掉末行 pw1 戳記後 sha256 前 16 碼 ＝ e72a759aefc7bfdc、整檔 6686 B 才跑（不符即停）
 F1 兩策略原版 ＝ researchYL_integrate.eng 原式（＝ researchYLvsYF V1）：
    營量 v1 ＝ simulate_mtm(SIG[無閘], "H60", 20, default_rng(7000＋0), log=[], d_max=None, pick="relvol", queue_days=0, stop_force=SF)，r＝0 一條
    營飆 v1 ＝ simulate_mtm(SIG[閘], "H120", 10, default_rng(1000＋r), stop_force=SF)，r ＝ 0～199（報中位、p10、p90 與 r0）
    世界 ＝ researchYL_integrate.main_world（T1 edc6f 快照；探索 2017-03-02～2021-12-30、確認 2022-01-03～2026-08-24）、
           early_world（上市＋上櫃 eotc_f65bb03e11、R8 截斷；早年 2005-02-01～2014-12-31，只描述）
    ★ 確認段尾 ＝ 該世界資料尾 2026-08-24（登錄「～資料尾」；正式跑若換新快照另報）
 F2 只買版 ＝ 候選表只留「族群營收轉強」列，其餘引擎參數同原版（不足額 ⇒ 空槽持現金；營飆照抽籤 200 顆、同種子）
    優先版 ＝ 候選照原表；名額不足時族群轉強者先進：
      營飆 ★ ＝ pick="prio"（族群轉強 1／否 0）＋ pick_tie="rng"：引擎每天照抽籤版抽同一次 permutation，依 prio 遞減穩定排序 ⇒ 同組內照抽籤先後
            （引擎註明「鍵全相同 ⇒ 與抽籤版逐位元相同」；本檔閘 G2 驗）
      營量 ★ ＝ pick 鍵 ＝ prio×10¹⁵ ＋ relvol（relvol 缺 ⇒ −10¹⁴，＝ 原版「NaN 排最後、同分照候選列序」）；閘 G2：prio 全 0 ⇒ 與原版逐筆相同
 F3 族群（產業 seq111，⛔ 不改定義）：每年初用前 250 日標準化日報酬 Ward 分群，群數 ＝ 母體檔數 ÷ 10
    ★ 分群檔：信箱、產業研究用、WSL、暫存夾都找不到產業 seq111 分群檔或逐筆名單 ⇒ 照定義重建（本檔），一致率只能對 seq111 件內的彙總數字
      （個股訊號 4,930、族群轉強 1,030、訊號月 113）以本檔同法重建近似訊號比對 ⇒ 報「彙總一致」，⛔ 不是逐檔一致率
    ★ 年 Y 的分群：參考日 ＝ 該世界日曆中 Y 年第一個交易日 ref；回看 [ref−250, ref−1] 共 250 個交易日
    ★ 母體（seq111 件內口徑）：data.load_universe（上市＋上櫃普通股，含之後下市；興櫃排除）中，回看 250 日內有效 K 棒（收盤有值）≥ 200，
      且 [ref−60, ref−1] 日均成交金額（無成交日記 0）≥ 1,000 萬元
    ★ 日報酬 ＝ 還原收盤相鄰兩個交易日都有值才算；|日報酬| ＞ 50% 視為斷點、當缺；每檔對自己有值的日報酬減平均、除標準差（ddof 0）、缺值補 0
    ★ Ward ＝ 平方歐氏距離 Lance–Williams 遞迴（同 scipy method="ward" 的合併順序；環境無 scipy、自寫，自測對窮舉 ΔSSE 驗），合併到剩
      K ＝ floor(母體檔數 ÷ 10 ＋ 0.5) 群為止；同距離取索引最小者
    ★補 F3b（分群步驟跑出「2005 回看只有 228 日」後、任何頻率數字之前補）：早年日曆首年回看不足 250 日 ⇒ 用可得回看（第 2 根起），
      有效 K 棒門檻按比例 ceil(200 × 可得日數 ÷ 250)；其餘不變
    族群營收轉強（第 m 月）：同群 ≥ 3 家，而且 ≥ 1/3 的成員第 m 月營收創 24 個月新高
    ★ 分母 ＝ 該群全部成員（無第 m 月營收者算「沒創新高」）
    ★ 創 24 月新高 ＝ 營量 v1 面板同式（research34：當月 ≥ 前 24 個月最大、前 24 個月全有值）〔另一讀法：含當月共 24 個月，即前 23 個月全有值且當月 ≥ 其最大；
      候選旗標兩讀法並報一致率〕；營收 ＝ 該世界資料夾 mops/revenue_hist（最新版，更正期間有輕微前視，照全線註）
    ★ 候選的 m ＝ 該候選自己的營收期別：同 research13.and_flags，取該世界 panel_rev 中 signal_pos ≤ 訊號日 pos、距離 ≤ 45 的最新一列的 period
      ⇒ 族群旗標與營量、營飆用同一期、同一個可用日（m＋1 月 10 日之後；2026-01 期起 15 日規則照該世界原建置，不另改）
    ★ 候選套用的分群 ＝ 訊號日 pos 所在年份 Y 的分群；候選不在 Y 年母體 ⇒ 「族群未轉強」並計入「不在產業母體」比例
 F4 頻率表（每 世界 × 策略 × 版本；營飆每顆種子各算，報中位〔p10～p90〕與 r0；段 ＝ 探索、確認、早年；以買進日 t 歸段）
    ① 每月：原版候選數（引擎看得到的列，以進場日歸月）、其中族群轉強數、原版買進、只買版買進、優先版買進、只買版平均持股與空格比例
       ★ 空格比例 ＝ 1 − 段內逐日持有檔數平均 ÷ 槽數（乾跑等權槽；＝ 現金比例的構造版）
    ② 優先版「換掉的買進」＝ 原版買進 (t, 代號) 不在優先版買進中的筆數 ÷ 原版買進筆數（對 10% 門檻）；
       買進重疊 ① ＝ 兩版同日同檔買進筆數 ÷ 該版買進筆數（另報 ÷ 原版買進筆數）（對 90% 門檻）；只買版、只買×優先同法
    ③ 持股重疊 ② ★ 乾跑無價格 ⇒ 報「等權槽持股重疊」＝ 逐日 |兩版共同持有代號| ÷ 槽數（每檔權重 1/N；一邊空槽 ＝ 0），平均、中位、逐年；
       ⚠ 金額權重需要價格（市值漂移）⇒ 留正式跑；③ 日報酬相關 ⇒ 只報「算得出」（兩版權益逐日都有、段內可配對）
       持有 ＝ [買進日, 賣出日)（researchYL_blend.holdings_w 同口徑；未賣持有到權益尾）
    ④ 只買版：逐日持有檔數分布（0、1～¼N、…、N）、空倉日比例、★ 空倉月 ＝ 整個月每個交易日都 0 檔的月份數；平均持股 ＜ N÷2 的月份數
       ★ 有效月數 ＝ 段內「有 ≥ 1 筆買進」的不同月份數（登錄沒定群；照方法論月分群 CI 的 24 群下限比）
    ⑤ 優先版「名額不足的日子」★ ＝ 當天（排程出場後）未持有的候選數 ＞ 空槽數的日子 ÷ 有未持有候選的日子；另報其中有族群轉強候選的日子
    ⑥ 候選中族群轉強比例、不在產業母體比例（逐年）
 F5 等價檢查（seq377）：只買版、優先版的買進序列是否與原版逐筆相同；族群旗標在候選中是否幾乎恆真（≥ 95%）或恆假（≤ 5%）；
    只買版買進是否 ＝ 「原版買進 ∩ 族群轉強」這個簡單條件（Jaccard）
 F6 閘：G0 乾跑原版營量買進 (t, 代號) 對 resultsYLlist/audit_seed0.csv.gz（只讀 t、sid、side 欄；正式版逐筆）一致率（現金不足差異照實報）；
    G1 世界閘照 IG 原樣印；G2 prio 全 0 的優先版 ＝ 原版（營量 r0；營飆 r0～2）逐筆相同；G3 逐日買進數 ＝ min(未持有候選, 空槽)（重建 vs 引擎）；
    G4 自算 24 月新高 vs 面板 rev_hi24（面板列）一致率；G5 strategy_lock --check 相符
 必附：「額外策略、與正式營量營飆分開；正式規則不動」「想法來自產業 seq111，看過同期結果才提」「營量、營飆本身已看過結果」；
       早年附 reduce_v2 約 0.3% 註與上櫃早年註（researchYL_integrate.NOTE3）
輸出 backtest/resultsGroupRevUp/freq/：monthly.csv、cand_yearly.csv、cells.csv、overlap_yearly.csv、holddist.csv、groups_yearly.csv、summary.json、結果.md
（中間檔 ~/grpwork/，不進 repo）
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import pickle
import subprocess
import sys
import time
from collections import Counter, defaultdict
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D                              # noqa: E402
from backtest import research11 as R                        # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402

TIME = "2026-11-10（台北）"
OUT = "backtest/resultsGroupRevUp/freq"
WORK = os.path.expanduser("~/grpwork")
MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
REG_SHA, REG_BYTES = "e72a759aefc7bfdc", 6686
NSEED = int(os.environ.get("GRU_NSEED", "200"))
STRATS = {"營量": dict(H=60, N=20, gate=False, seed0=RR.P1_SEED0),
          "營飆": dict(H=120, N=10, gate=True, seed0=RR.P10_SEED0)}
VERS = ("原版", "只買版", "優先版")
PAIRS = (("優先版", "原版"), ("只買版", "原版"), ("只買版", "優先版"))
SEGN = {"main": ("探索", "確認"), "early": ("早年",)}
YEARS = {"main": range(2017, 2027), "early": range(2005, 2015)}
PANEL = {"main": os.path.join(RR.OUT, "sig_edc6f", "panel_rev.csv.gz"),
         "early": os.path.expanduser("~/earlydata/eotc_f65bb03e11/sig_otc/panel_rev.csv.gz")}
STALE_MAX = 45
LOOK, MINBARS, AMTWIN, AMTMIN = 250, 200, 60, 1.0e7
JUMP = 0.5
BIGP, NANRV = 1.0e15, -1.0e14
LOGF = None


def log(x):
    s = f"[{time.strftime('%H:%M:%S')}] {x}"
    print(s, flush=True)
    if LOGF:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(s + "\n")


# ═════════════ F0 登錄 sha ═════════════
def check_reg():
    fs = [f for f in glob.glob(os.path.join(MAILBOX, "**", f"*sha{REG_SHA}*"), recursive=True)]
    if not fs:
        raise SystemExit(f"⛔ 信箱找不到 sha{REG_SHA} 登錄全文")
    b = open(fs[0], "rb").read()
    i = b.rfind(b"<!-- pw1")
    h = hashlib.sha256(b[:i]).hexdigest()[:16]
    ok = (h == REG_SHA and len(b) == REG_BYTES)
    if not ok:
        raise SystemExit(f"⛔ 登錄 sha／大小不符：{h}／{len(b)} B")
    return {"檔": os.path.basename(fs[0]), "sha16": h, "bytes": len(b)}


# ═════════════ Ward（平方歐氏 Lance–Williams）═════════════
def ward_cut(X, K):
    """X：n×d；合併到剩 K 群；回 labels（0..K−1，依群內最小列號排序編號）。"""
    n = X.shape[0]
    if K >= n:
        return np.arange(n)
    sq = (X * X).sum(1)
    Dm = sq[:, None] + sq[None, :] - 2.0 * (X @ X.T)
    np.maximum(Dm, 0.0, out=Dm)
    np.fill_diagonal(Dm, np.inf)
    size = np.ones(n)
    alive = np.ones(n, bool)
    lab = np.arange(n)
    nc = n
    while nc > K:
        k = int(np.argmin(Dm)); i, j = divmod(k, n)
        if i > j:
            i, j = j, i
        ni, nj = size[i], size[j]; dij = Dm[i, j]
        nk = size
        new = ((ni + nk) * Dm[i] + (nj + nk) * Dm[j] - nk * dij) / (ni + nj + nk)
        new[~alive] = np.inf; new[i] = np.inf; new[j] = np.inf
        Dm[i, :] = new; Dm[:, i] = new; Dm[i, i] = np.inf
        Dm[j, :] = np.inf; Dm[:, j] = np.inf
        alive[j] = False; size[i] = ni + nj
        lab[lab == j] = i
        nc -= 1
    roots = sorted(set(lab.tolist()), key=lambda r: int(np.flatnonzero(lab == r).min()))
    m = {r: q for q, r in enumerate(roots)}
    return np.array([m[x] for x in lab])


def zrets(C):
    """C：n×(L＋1) 還原收盤；回 n×L 標準化日報酬（缺 ⇒ 0）。"""
    with np.errstate(invalid="ignore", divide="ignore"):
        r = C[:, 1:] / C[:, :-1] - 1.0
    r[~np.isfinite(r)] = np.nan
    r[np.abs(r) > JUMP] = np.nan
    mu = np.nanmean(r, 1, keepdims=True); sd = np.nanstd(r, 1, keepdims=True)
    sd[~(sd > 0)] = 1.0
    z = (r - mu) / sd
    z[np.isnan(z)] = 0.0
    return z


def hi24_tables(rev):
    """rev：period × sid（完整月序）；回 (hi24 主讀法, hi24b 另一讀法) 兩個 bool 表。"""
    p1 = rev.shift(1)
    m24 = p1.rolling(24, min_periods=24).max()
    m23 = p1.rolling(23, min_periods=23).max()
    hi = rev.notna() & (rev >= m24)
    hib = rev.notna() & (rev >= m23)
    return hi, hib


def group_up(members_hi, size):
    """members_hi：該群第 m 月創高的成員數；size：群大小。"""
    return (size >= 3) and (members_hi * 3 >= size)


# ═════════════ step world ═════════════
def step_world(wn, procs):
    from backtest import researchYL_integrate as IG
    if wn == "main":
        W, gate = IG.main_world(log)
    else:
        W, gate = IG.early_world(log, procs)
    base = W["base"]
    keep = [c for c in ("sid", "k", "pos", "entry_pos", "month", "xpos_H60", "xpos_H120", "relvol") if c in base.columns]
    S = base[keep].copy().reset_index(drop=True)
    S["sid"] = S["sid"].astype(str)
    S["gated"] = np.asarray(W["reg"], bool)[S["entry_pos"].to_numpy(int) - 1]
    assert int(S["gated"].sum()) == len(W["SIG"][True]), "閘列數不符"
    P = dict(cal=W["cal"], w0=W["w0"], w1=W["w1"], NP=int(W["NP"]), SF=W["SF"], segp=W["segp"], S=S, data=D.DATA,
             sids=sorted(set(S["sid"])), gate=gate)
    os.makedirs(WORK, exist_ok=True)
    pickle.dump(P, open(os.path.join(WORK, f"world_{wn}.pkl"), "wb"), protocol=5)
    log(f"[world {wn}] 訊號 {len(S)}｜閘內 {int(S['gated'].sum())}｜NP {P['NP']}｜data {D.DATA}｜閘 {gate}")


# ═════════════ step groups ═════════════
def _load_px(args):
    sid, mk = args
    st = D.load_stock(sid, mk, _G["cal"])
    if st is None:
        return sid, None, None
    return sid, st.df["close"].to_numpy(np.float64), st.df["amount"].to_numpy(np.float64)


_G: dict = {}


def load_revenue():
    fs = sorted(glob.glob(os.path.join(D.DATA, "mops", "revenue_hist", "*.csv")))
    df = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收"]) for f in fs])
    df["rev"] = pd.to_numeric(df["當月營收"], errors="coerce")
    df = df.drop_duplicates(["stock_id", "period"], keep="last")
    rev = df.pivot(index="period", columns="stock_id", values="rev").sort_index()
    full = pd.period_range(rev.index.min(), rev.index.max(), freq="M").strftime("%Y-%m")
    return rev.reindex(full)


def cand_period(S, panel):
    """and_flags 同式：每列候選的營收期別（找不到 ⇒ None）。"""
    p = panel.sort_values(["stock_id", "signal_pos"])
    by = {sid: (g["signal_pos"].to_numpy(), g["period"].to_numpy(), g["rev_hi24"].to_numpy(bool)) for sid, g in p.groupby("stock_id")}
    out = []; nohi = 0
    for sid, pos in zip(S["sid"], S["pos"]):
        if sid not in by:
            out.append(None); continue
        sp, per, hi = by[sid]
        j = int(np.searchsorted(sp, pos, side="right")) - 1
        if j >= 0 and pos - sp[j] <= STALE_MAX:
            out.append(per[j]); nohi += int(not hi[j])
        else:
            out.append(None)
    return out, nohi


def step_groups(wn, procs):
    P = pickle.load(open(os.path.join(WORK, f"world_{wn}.pkl"), "rb"))
    D.DATA = P["data"]
    cal = D.load_calendar()
    if not (len(cal) == len(P["cal"]) and (cal == P["cal"]).all()):
        raise SystemExit("⛔ 日曆與世界不同")
    uni = D.load_universe()
    _G["cal"] = cal
    jobs = [(s, m) for s, m in zip(uni["stock_id"], uni["market"])]
    CL, AM = {}, {}
    with Pool(procs, initializer=_G.update, initargs=({"cal": cal},)) as pool:
        for sid, c, a in pool.imap_unordered(_load_px, jobs, chunksize=16):
            if c is not None:
                CL[sid] = c; AM[sid] = a
    log(f"[groups {wn}] 價格 {len(CL)} 檔／普通股 {len(uni)}")
    rev = load_revenue()
    hi, hib = hi24_tables(rev)
    mk = uni.set_index("stock_id")["market"]
    # 分群
    G = {}; GY = []
    for Y in YEARS[wn]:
        ref = int(cal.searchsorted(pd.Timestamp(year=Y, month=1, day=1)))
        lo = ref - LOOK; minb = MINBARS
        if ref >= len(cal):
            log(f"  {Y}：超出日曆 ⇒ 跳過"); continue
        if lo - 1 < 0:                                  # ★補（F3b）：早年日曆首年不足 250 日 ⇒ 用可得回看、有效 K 棒門檻按比例
            lo = 1; minb = int(np.ceil(MINBARS * (ref - lo) / LOOK))
            log(f"  {Y}：回看只有 {ref - lo} 日 ⇒ 用可得回看、門檻 {minb} 根（★）")
        elig = []
        for sid in sorted(CL):
            c = CL[sid]; a = AM[sid]
            nv = int(np.isfinite(c[lo:ref]).sum())
            if nv < minb:
                continue
            am = np.nan_to_num(a[ref - AMTWIN:ref], nan=0.0).mean()
            if am < AMTMIN:
                continue
            elig.append(sid)
        n = len(elig); K = int(np.floor(n / 10 + 0.5))
        C = np.vstack([CL[s][lo - 1:ref] for s in elig])
        Z = zrets(C)
        t0 = time.time(); lab = ward_cut(Z, K)
        sizes = np.bincount(lab)
        G[Y] = {"ref": ref, "sids": elig, "lab": lab, "sizes": sizes}
        GY.append({"世界": wn, "年": Y, "參考日": str(cal[ref].date()), "母體": n, "上市": int(sum(mk.get(s) == "twse" for s in elig)),
                   "上櫃": int(sum(mk.get(s) == "tpex" for s in elig)), "群數": K, "≥3 家群數": int((sizes >= 3).sum()),
                   "≥3 家群涵蓋檔數": int(sizes[sizes >= 3].sum()), "最大群": int(sizes.max()), "群大小中位": float(np.median(sizes)), "秒": round(time.time() - t0, 1)})
        log(f"  {Y}：母體 {n}｜K {K}｜≥3 家群 {(sizes >= 3).sum()}｜{time.time() - t0:.1f}s")
    # 群 × 期 的族群轉強
    GU = {}
    hiv = {"主": hi, "另": hib}
    for Y, g in G.items():
        periods = [p for p in rev.index if f"{Y - 1}-01" <= p <= f"{Y}-12"]
        cols = [s for s in g["sids"]]
        for nm, T in hiv.items():
            M = T.reindex(index=periods, columns=cols).fillna(False).to_numpy(bool)    # 期 × 成員
            for c in range(len(g["sizes"])):
                idx = np.flatnonzero(g["lab"] == c)
                cnt = M[:, idx].sum(1)
                for pi, p in enumerate(periods):
                    GU[(nm, Y, c, p)] = group_up(int(cnt[pi]), int(g["sizes"][c]))
    # 候選旗標
    S = P["S"].copy()
    panel = pd.read_csv(PANEL[wn], dtype={"stock_id": str, "period": str}, usecols=["stock_id", "period", "signal_pos", "rev_hi24"])
    panel["rev_hi24"] = panel["rev_hi24"].fillna(False).astype(bool)
    per, nohi = cand_period(S, panel)
    S["period"] = per
    S["year"] = [cal[int(p)].year for p in S["pos"]]
    lk = {Y: dict(zip(g["sids"], g["lab"])) for Y, g in G.items()}
    inu, f_main, f_alt = [], [], []
    for sid, Y, p in zip(S["sid"], S["year"], S["period"]):
        c = lk.get(Y, {}).get(sid)
        inu.append(c is not None)
        f_main.append(bool(c is not None and p is not None and GU.get(("主", Y, int(c), p), False)))
        f_alt.append(bool(c is not None and p is not None and GU.get(("另", Y, int(c), p), False)))
    S["in_univ"] = inu; S["grp"] = f_main; S["grp_alt"] = f_alt
    # G4：自算 24 月新高 vs 面板
    pr = panel[panel["period"].isin(hi.index)]
    pr = pr[pr["stock_id"].isin(hi.columns)]
    hv =np.array([bool(hi.at[p, s]) for p, s in zip(pr["period"], pr["stock_id"])])
    g4 = {"面板列": int(len(pr)), "一致": int((hv == pr["rev_hi24"].to_numpy(bool)).sum()),
          "面板真我假": int((~hv & pr["rev_hi24"].to_numpy(bool)).sum()), "面板假我真": int((hv & ~pr["rev_hi24"].to_numpy(bool)).sum()),
          "候選找不到期別": int(sum(p is None for p in per)), "候選期別列非創高（應 0）": int(nohi)}
    log(f"[G4 {wn}] {g4}")
    out = {"S": S, "GY": GY, "G4": g4, "G": {Y: {"sids": g["sids"], "lab": g["lab"].tolist()} for Y, g in G.items()}}
    if wn == "main":
        out["seq111"] = seq111_recon(cal, CL, G, GU, hi, hib)
        log(f"[seq111 近似重建] {out['seq111']}")
    pickle.dump(out, open(os.path.join(WORK, f"groups_{wn}.pkl"), "wb"), protocol=5)


def seq111_recon(cal, CL, G, GU, hi, hib):
    """seq111 件內口徑的個股訊號近似重建（彙總一致性）：訊號日 e ＝ m＋1 月 10 日之後第一個交易日；
    當月創 24 月新高 ＋ e 收盤 ＞ 60 日均 ＋ 近 20 日報酬 ＞ 加權指數（★ 庫無加權指數 ⇒ 0050 還原代）；母體 ＝ e 所在年分群母體。"""
    b = D.load_benchmark(cal)["close"].to_numpy(float)
    rows = []
    for Y, g in G.items():
        lab = dict(zip(g["sids"], g["lab"]))
        for p in hi.index:
            y, m = int(p[:4]), int(p[5:])
            y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
            if y2 != Y:
                continue
            e = int(cal.searchsorted(pd.Timestamp(year=y2, month=m2, day=10), side="right"))
            if e >= len(cal) or e < 60:
                continue
            for sid in g["sids"]:
                if not bool(hi.at[p, sid]) if sid in hi.columns else True:
                    continue
                c = CL[sid]
                w = c[e - 59:e + 1]
                if not (np.isfinite(w).all() and np.isfinite(c[e - 20])):
                    continue
                if not (c[e] > w.mean()):
                    continue
                if not (c[e] / c[e - 20] - 1.0 > b[e] / b[e - 20] - 1.0):
                    continue
                cc = int(lab[sid])
                rows.append((p, sid, bool(GU.get(("主", Y, cc, p), False))))
    if not rows:
        return {}
    X = pd.DataFrame(rows, columns=["period", "sid", "grp"])
    X = X[X["period"] >= "2016-12"]
    bm = X.groupby("period")["grp"].agg(["sum", "count"])
    return {"個股訊號": int(len(X)), "族群轉強": int(X["grp"].sum()), "族群轉強占比": float(X["grp"].mean()),
            "訊號月": int(X["period"].nunique()), "兩邊都有的月": int(((bm["sum"] > 0) & (bm["sum"] < bm["count"])).sum()),
            "期別範圍": [str(X["period"].min()), str(X["period"].max())],
            "seq111 件內": {"個股訊號": 4930, "族群轉強": 1030, "族群轉強占比": 1030 / 4930, "訊號月": 113, "兩邊都有的月": 80}}


# ═════════════ step sim（乾跑）═════════════
_W: dict = {}


def make_sig(S, st, ver, flag="grp", zero_prio=False):
    s = S[S["gated"]] if STRATS[st]["gate"] else S
    s = s.copy()
    s["g_H60"] = 0.0; s["g_H120"] = 0.0
    if ver == "只買版":
        s = s[s[flag].to_numpy(bool)]
    elif ver == "優先版":
        pr = np.zeros(len(s)) if zero_prio else s[flag].to_numpy(bool).astype(float)
        if st == "營量":
            rv = s["relvol"].to_numpy(float)
            s["prio_rv"] = pr * BIGP + np.where(np.isfinite(rv), rv, NANRV)
        else:
            s["prio"] = pr
    return s


def run_engine(sig, st, ver, r, ones, NP, SF):
    H, N, seed0 = STRATS[st]["H"], STRATS[st]["N"], STRATS[st]["seed0"]
    au = []
    rng = np.random.default_rng(seed0 + r)
    if st == "營量":
        pk = "prio_rv" if ver == "優先版" else "relvol"
        R.simulate_mtm(sig, f"H{H}", N, rng, ones, ones, NP, return_equity=True, log=[], d_max=None, pick=pk, queue_days=0,
                       stop_force=SF, audit=au)
    else:
        kw = dict(pick="prio", pick_tie="rng") if ver == "優先版" else {}
        R.simulate_mtm(sig, f"H{H}", N, rng, ones, ones, NP, return_equity=True, stop_force=SF, audit=au, **kw)
    buys = [(int(a["t"]), str(a["sid"])) for a in au if a["side"] == "buy"]
    sells = [(int(a["t"]), str(a["sid"])) for a in au if a["side"] != "buy"]
    return buys, sells


def intervals(buys, sells, NP):
    """(sid, tb, ts)；同檔不重複持有 ⇒ 依時間配對。"""
    sl = defaultdict(list)
    for t, s in sorted(sells):
        sl[s].append(t)
    out = []
    for t, s in sorted(buys):
        L = sl[s]
        j = next((i for i, x in enumerate(L) if x > t), None)
        ts = L.pop(j) if j is not None else NP
        out.append((s, t, ts))
    return out


def held_count(iv, NP):
    d = np.zeros(NP + 1)
    for _, a, b in iv:
        d[a] += 1; d[b] -= 1
    return np.cumsum(d)[:NP]


def overlap_count(iva, ivb, NP):
    by = defaultdict(list)
    for s, a, b in ivb:
        by[s].append((a, b))
    d = np.zeros(NP + 1)
    for s, a, b in iva:
        for a2, b2 in by.get(s, ()):
            lo, hi = max(a, a2), min(b, b2)
            if lo < hi:
                d[lo] += 1; d[hi] -= 1
    return np.cumsum(d)[:NP]


def shortage(sig, iv, N, NP):
    """逐日：未持有候選數、空槽數（排程出場後、買進前）。"""
    e = sig["entry_pos"].to_numpy(int); sids = sig["sid"].to_numpy(str); fl = sig["grp"].to_numpy(bool)
    byt = defaultdict(list)
    for t, s, f in zip(e, sids, fl):
        byt[int(t)].append((s, f))
    A = np.sort(np.array([a for _, a, _ in iv], int)); Bv = np.sort(np.array([b for _, _, b in iv], int))
    bys = defaultdict(list)
    for s, a, b in iv:
        bys[s].append((a, b))
    res = {}
    for t, L in byt.items():
        nheld = int(np.searchsorted(A, t, side="left")) - int(np.searchsorted(Bv, t, side="right"))   # #{a < t < b}
        nh = [(s, f) for s, f in L if not any(a < t < b for a, b in bys.get(s, ()))]
        res[t] = (len(nh), sum(f for _, f in nh), N - nheld)
    return res


def job(args):
    wn, st, r = args
    P = _W["P"]; S = _W["S"]; NP = P["NP"]; SF = P["SF"]; ones = _W["ones"]; N = STRATS[st]["N"]
    cal = P["cal"]
    res = {"st": st, "r": r, "ver": {}}
    IV = {}; B = {}
    for v in VERS:
        sig = make_sig(S, st, v)
        sig = sig[sig[f"xpos_H{STRATS[st]['H']}"].notna() & (sig[f"xpos_H{STRATS[st]['H']}"] >= 0)]
        buys, sells = run_engine(sig, st, v, r, ones, NP, SF)
        iv = intervals(buys, sells, NP)
        IV[v] = iv; B[v] = buys
        hc = held_count(iv, NP)
        sh = shortage(sig, iv, N, NP)
        # G3：逐日買進數 ＝ min(未持有候選, 空槽)
        bc = Counter(t for t, _ in buys)
        g3 = sum(1 for t, (nh, _, fr) in sh.items() if bc.get(t, 0) != max(0, min(nh, fr)))
        g3 += sum(1 for t in bc if t not in sh)
        res["ver"][v] = {"buys": buys, "hc": hc.astype(np.int16), "short": sh, "g3": g3, "ncand": len(sig)}
    for a, b in PAIRS:
        res[f"ov_{a}_{b}"] = overlap_count(IV[a], IV[b], NP).astype(np.int16)
    # G2：prio 全 0 ＝ 原版
    if (st == "營量" and r == 0) or (st == "營飆" and r < 3):
        sig = make_sig(S, st, "優先版", zero_prio=True)
        sig = sig[sig[f"xpos_H{STRATS[st]['H']}"].notna() & (sig[f"xpos_H{STRATS[st]['H']}"] >= 0)]
        bz, sz = run_engine(sig, st, "優先版", r, ones, NP, SF)
        res["G2"] = bool(bz == B["原版"])
    return res


def step_sim(wn, procs):
    P = pickle.load(open(os.path.join(WORK, f"world_{wn}.pkl"), "rb"))
    Gp = pickle.load(open(os.path.join(WORK, f"groups_{wn}.pkl"), "rb"))
    _W["P"] = P; _W["S"] = Gp["S"]
    _W["ones"] = {s: np.ones(P["NP"]) for s in P["sids"]}
    jobs = [(wn, "營量", 0)] + [(wn, "營飆", r) for r in range(NSEED)]
    t0 = time.time(); out = []
    with Pool(procs) as pool:
        for i, res in enumerate(pool.imap_unordered(job, jobs)):
            out.append(res)
            if (i + 1) % 20 == 0:
                log(f"  sim {wn} {i + 1}/{len(jobs)} {time.time() - t0:.0f}s")
    out.sort(key=lambda x: (x["st"], x["r"]))
    pickle.dump(out, open(os.path.join(WORK, f"sim_{wn}.pkl"), "wb"), protocol=5)
    log(f"[sim {wn}] {len(out)} 件｜{time.time() - t0:.0f}s")


# ═════════════ step report ═════════════
def seg_bounds(P, wn):
    return {sg: P["segp"][sg] for sg in SEGN[wn]}


def q(xs):
    xs = np.asarray([x for x in xs if x is not None and np.isfinite(x)], float)
    if not len(xs):
        return {"中位": None, "p10": None, "p90": None}
    return {"中位": float(np.median(xs)), "p10": float(np.percentile(xs, 10)), "p90": float(np.percentile(xs, 90))}


def per_seed_cell(res, P, x, y, N):
    cal = P["cal"]
    d = {}
    bset = {v: {(t, s) for t, s in res["ver"][v]["buys"] if x <= t <= y} for v in VERS}
    for v in VERS:
        hc = res["ver"][v]["hc"][x:y + 1].astype(float)
        d[f"{v}_買進"] = len(bset[v])
        d[f"{v}_平均持股"] = float(hc.mean())
        d[f"{v}_空格比例"] = float(1 - hc.mean() / N)
        d[f"{v}_空倉日比例"] = float((hc == 0).mean())
        mon = pd.Series(hc, index=cal[x:y + 1].strftime("%Y-%m"))
        g = mon.groupby(level=0)
        d[f"{v}_空倉月"] = int((g.max() == 0).sum())
        d[f"{v}_半滿以下月"] = int((g.mean() < N / 2).sum())
        d[f"{v}_月數"] = int(g.ngroups)
        d[f"{v}_有效月數"] = int(len({cal[t].strftime('%Y-%m') for t, _ in bset[v]}))
        sh = {t: z for t, z in res["ver"][v]["short"].items() if x <= t <= y}
        dc = [t for t, (nh, ng, fr) in sh.items() if nh > 0]
        ds = [t for t in dc if sh[t][0] > sh[t][2]]
        d[f"{v}_有候選日"] = len(dc)
        d[f"{v}_名額不足日比例"] = (len(ds) / len(dc)) if dc else None
        d[f"{v}_名額不足且有族群轉強候選日比例"] = (sum(1 for t in ds if sh[t][1] > 0) / len(dc)) if dc else None
    for a, b in PAIRS:
        A, Bb = bset[a], bset[b]
        inter = len(A & Bb)
        d[f"{a}vs{b}_買進重疊÷{a}"] = inter / len(A) if A else None
        d[f"{a}vs{b}_買進重疊÷{b}"] = inter / len(Bb) if Bb else None
        d[f"{a}vs{b}_{b}被換掉"] = (len(Bb - A) / len(Bb)) if Bb else None
        ov = res[f"ov_{a}_{b}"][x:y + 1].astype(float) / N
        d[f"{a}vs{b}_等權持股重疊_平均"] = float(ov.mean())
        d[f"{a}vs{b}_等權持股重疊_中位"] = float(np.median(ov))
        d[f"{a}vs{b}_逐筆相同"] = bool(A == Bb)
    return d


def step_report():
    os.makedirs(OUT, exist_ok=True)
    reg = check_reg()
    summ = {"時間": TIME, "登錄": reg, "發號": "裁定線 seq501 §三", "乾跑": "價格全 1、毛報酬 0；⛔ 無任何報酬數字", "世界": {}}
    cells, monthly, candy, ovy, hdist, gyear = [], [], [], [], [], []
    md = []
    for wn in ("main", "early"):
        P = pickle.load(open(os.path.join(WORK, f"world_{wn}.pkl"), "rb"))
        Gp = pickle.load(open(os.path.join(WORK, f"groups_{wn}.pkl"), "rb"))
        SIM = pickle.load(open(os.path.join(WORK, f"sim_{wn}.pkl"), "rb"))
        S = Gp["S"]; cal = P["cal"]
        gyear += Gp["GY"]
        W = {"G4": Gp["G4"], "IG閘": P["gate"], "seq111": Gp.get("seq111")}
        # 候選逐年
        for st in STRATS:
            s = S[S["gated"]] if STRATS[st]["gate"] else S
            H = STRATS[st]["H"]
            s = s[s[f"xpos_H{H}"].notna() & (s[f"xpos_H{H}"] >= 0)]
            yy = [cal[int(e)].year for e in s["entry_pos"]]
            for Y, g in s.groupby(yy):
                candy.append({"世界": wn, "策略": st, "年": Y, "候選": len(g), "族群轉強": int(g["grp"].sum()), "族群轉強比例": float(g["grp"].mean()),
                              "另一讀法族群轉強比例": float(g["grp_alt"].mean()), "不在產業母體比例": float((~g["in_univ"]).mean())})
            W[f"{st}_候選"] = {"候選": int(len(s)), "族群轉強比例": float(s["grp"].mean()), "不在產業母體比例": float((~s["in_univ"]).mean()),
                             "兩讀法旗標一致率": float((s["grp"] == s["grp_alt"]).mean()),
                             "seq377 恆真恆假": ("恆真" if s["grp"].mean() >= 0.95 else ("恆假" if s["grp"].mean() <= 0.05 else "否"))}
            # 每月表
            rs = [x for x in SIM if x["st"] == st]
            mo = pd.Series([cal[int(e)].strftime("%Y-%m") for e in s["entry_pos"]])
            cm = s.groupby(mo.to_numpy())["grp"].agg(["count", "sum"])
            months = sorted(set(cal[P["w0"]:P["w1"] + 1].strftime("%Y-%m")))
            N = STRATS[st]["N"]
            mpos = pd.Series(np.arange(len(cal)), index=cal.strftime("%Y-%m"))
            calm = np.asarray(cal.strftime("%Y-%m"))
            MC = {v: [Counter(calm[t] for t, _ in x["ver"][v]["buys"] if t < len(calm)) for x in rs] for v in VERS}
            for mth in months:
                ps = mpos.loc[[mth]].to_numpy() if mth in mpos.index else np.array([], int)
                ps = ps[(ps >= P["w0"]) & (ps <= P["w1"])]
                row = {"世界": wn, "策略": st, "月": mth, "原版候選": int(cm["count"].get(mth, 0)), "族群轉強候選": int(cm["sum"].get(mth, 0))}
                for v in VERS:
                    row[f"{v}買進"] = float(np.mean([c_.get(mth, 0) for c_ in MC[v]]))
                hv = [x["ver"]["只買版"]["hc"][ps].mean() for x in rs] if len(ps) else [np.nan]
                row["只買版平均持股"] = float(np.mean(hv)); row["只買版空格比例"] = float(1 - np.mean(hv) / N)
                monthly.append(row)
            # 段 cell
            for sg, (x, y) in seg_bounds(P, wn).items():
                per = [per_seed_cell(r_, P, x, y, N) for r_ in rs]
                keys = per[0].keys()
                row = {"世界": wn, "策略": st, "段": sg, "段起": str(cal[x].date()), "段尾": str(cal[y].date()), "種子數": len(per)}
                for k in keys:
                    vals = [p[k] for p in per]
                    if isinstance(vals[0], bool):
                        row[k] = f"{sum(vals)}/{len(vals)}"
                    elif st == "營量":
                        row[k] = vals[0]
                    else:
                        qq = q(vals); row[k] = qq["中位"]; row[k + "_p10"] = qq["p10"]; row[k + "_p90"] = qq["p90"]; row[k + "_r0"] = vals[0]
                cells.append(row)
                # 只買版持有檔數分布
                bins = [0, 1, N // 4 + 1, N // 2 + 1, 3 * N // 4 + 1, N, N + 1]
                labs = ["0", f"1～{N // 4}", f"{N // 4 + 1}～{N // 2}", f"{N // 2 + 1}～{3 * N // 4}", f"{3 * N // 4 + 1}～{N - 1}", f"{N}"]
                for v in VERS:
                    hcs = np.concatenate([r_["ver"][v]["hc"][x:y + 1] for r_ in rs])
                    h, _ = np.histogram(hcs, bins=bins)
                    hdist.append({"世界": wn, "策略": st, "段": sg, "版": v, **{f"持有{l}": float(c / len(hcs)) for l, c in zip(labs, h)}})
                # 只買 × 族群條件簡單集合（seq377）
                jac = []
                fl = dict(zip(zip(s["entry_pos"].astype(int), s["sid"]), s["grp"]))
                for r_ in rs:
                    A = {(t, s_) for t, s_ in r_["ver"]["只買版"]["buys"] if x <= t <= y}
                    Bb = {(t, s_) for t, s_ in r_["ver"]["原版"]["buys"] if x <= t <= y and fl.get((t, s_), False)}
                    jac.append(len(A & Bb) / len(A | Bb) if (A | Bb) else np.nan)
                row["只買版vs原版∩族群轉強_Jaccard"] = float(np.nanmedian(jac))
            # 逐年持股重疊
            yrs = cal.year.to_numpy()
            for Y in sorted(set(yrs[P["w0"]:P["w1"] + 1])):
                ps = np.flatnonzero((yrs == Y) & (np.arange(len(cal)) >= P["w0"]) & (np.arange(len(cal)) <= P["w1"]))
                row = {"世界": wn, "策略": st, "年": int(Y)}
                for a, b in PAIRS:
                    v_ = [x[f"ov_{a}_{b}"][ps].mean() / N for x in rs]
                    row[f"{a}vs{b}_等權持股重疊"] = float(np.median(v_))
                ovy.append(row)
            W[f"{st}_閘"] = {"G2 prio全0＝原版": [x.get("G2") for x in rs if "G2" in x],
                            "G3 逐日買進數不符（全部版本×種子合計）": int(sum(x["ver"][v]["g3"] for x in rs for v in VERS))}
        # G0：乾跑原版營量 vs 正式 audit_seed0
        if wn == "main":
            F0 = pd.read_csv("backtest/resultsYLlist/audit_seed0.csv.gz", dtype={"sid": str}, usecols=["t", "sid", "side"])
            fb = {(int(t), s) for t, s, sd in zip(F0["t"], F0["sid"], F0["side"]) if sd == "buy"}
            yl = [x for x in SIM if x["st"] == "營量"][0]
            db = set(yl["ver"]["原版"]["buys"])
            W["G0 乾跑原版營量 vs 正式 audit_seed0"] = {"正式買進": len(fb), "乾跑買進": len(db), "相同": len(fb & db),
                                                  "只在正式": len(fb - db), "只在乾跑": len(db - fb)}
        summ["世界"][wn] = W
    # G5 策略鎖
    pr = subprocess.run([sys.executable, "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True,
                        env={**os.environ, "PYTHONPATH": os.path.expanduser("~/tw-p17")})
    summ["G5 策略鎖"] = {"exit": pr.returncode, "out": (pr.stdout + pr.stderr).strip()[-500:]}
    summ["日報酬相關"] = "算得出（兩版權益逐日皆有、段內可配對；本階段乾跑不算，正式跑報）"
    summ["持股重疊口徑"] = "等權槽（每檔 1/N）；金額權重需價格，留正式跑"
    for nm, rows in (("cells", cells), ("monthly", monthly), ("cand_yearly", candy), ("overlap_yearly", ovy), ("holddist", hdist), ("groups_yearly", gyear)):
        pd.DataFrame(rows).to_csv(os.path.join(OUT, f"{nm}.csv"), index=False, encoding="utf-8-sig", float_format="%.6g")
    json.dump(summ, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    write_md(summ, cells, candy, gyear, hdist)
    log("[report] 完成")


def _f(x, pct=True, d=1):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "—"
    return f"{100 * x:.{d}f}%" if pct else (f"{x:.{d}f}" if isinstance(x, float) else str(x))


def write_md(summ, cells, candy, gyear, hdist):
    L = ["# 營量／營飆加族群營收也轉強（只買版、優先版）頻率表（乾跑、⛔ 無報酬）", "",
         f"登錄 台股 seq2 sha {summ['登錄']['sha16']}（{summ['登錄']['bytes']} B，相符）｜發號 裁定 seq501 §三｜回測線計算子代理 {TIME}", "",
         "額外策略、與正式營量營飆分開；正式規則不動｜想法來自產業 seq111，看過同期結果才提｜營量、營飆本身已看過結果", "",
         "營飆數字 ＝ 200 顆種子中位〔p10～p90〕；營量 ＝ r0 一條。持股重疊 ＝ 等權槽（金額權重留正式跑）；日報酬相關：算得出、本階段不算。", ""]
    for c in cells:
        st = c["策略"]; sp = st == "營飆"

        def g(k):
            v = c.get(k)
            s = _f(v)
            if sp and c.get(k + "_p10") is not None:
                s += f"〔{_f(c[k + '_p10'])}～{_f(c[k + '_p90'])}〕"
            return s
        L += [f"## {c['世界']}｜{st}｜{c['段']}（{c['段起']}～{c['段尾']}）", "",
              "| 項 | 原版 | 只買版 | 優先版 |", "|---|---|---|---|",
              f"| 買進筆數 | {_f(c['原版_買進'], False)} | {_f(c['只買版_買進'], False)} | {_f(c['優先版_買進'], False)} |",
              f"| 平均持股 | {_f(c['原版_平均持股'], False)} | {_f(c['只買版_平均持股'], False)} | {_f(c['優先版_平均持股'], False)} |",
              f"| 空格比例 | {g('原版_空格比例')} | {g('只買版_空格比例')} | {g('優先版_空格比例')} |",
              f"| 空倉月／月數 | {c['原版_空倉月']}/{c['原版_月數']} | {c['只買版_空倉月']}/{c['只買版_月數']} | {c['優先版_空倉月']}/{c['優先版_月數']} |",
              f"| 有效月數（對 24） | {c['原版_有效月數']} | {c['只買版_有效月數']} | {c['優先版_有效月數']} |",
              f"| 名額不足日比例 | {g('原版_名額不足日比例')} | {g('只買版_名額不足日比例')} | {g('優先版_名額不足日比例')} |", "",
              "| 配對 | 買進重疊÷前者 | 買進重疊÷後者 | 後者被換掉 | 等權持股重疊 平均 | 中位 | 逐筆相同 |", "|---|---|---|---|---|---|---|"]
        for a, b in PAIRS:
            k = f"{a}vs{b}"
            L.append(f"| {a} vs {b} | {g(k + '_買進重疊÷' + a)} | {g(k + '_買進重疊÷' + b)} | {g(k + '_' + b + '被換掉')} | "
                     f"{g(k + '_等權持股重疊_平均')} | {g(k + '_等權持股重疊_中位')} | {c[k + '_逐筆相同']} |")
        L += ["", f"只買版 vs「原版買進 ∩ 族群轉強」Jaccard：{_f(c.get('只買版vs原版∩族群轉強_Jaccard'))}", ""]
    L += ["## 候選與族群", ""]
    for wn, W in summ["世界"].items():
        for st in STRATS:
            cd = W[f"{st}_候選"]
            L.append(f"- {wn}｜{st}：候選 {cd['候選']}、族群轉強 {_f(cd['族群轉強比例'])}、不在產業母體 {_f(cd['不在產業母體比例'])}、"
                     f"兩讀法一致 {_f(cd['兩讀法旗標一致率'])}、恆真恆假：{cd['seq377 恆真恆假']}；閘 {W[f'{st}_閘']}")
        L.append(f"- {wn} G4（自算 24 月新高 vs 面板）：{W['G4']}")
        if W.get("seq111"):
            L.append(f"- seq111 彙總一致（近似重建，⛔ 非逐檔）：{W['seq111']}")
        if W.get("G0 乾跑原版營量 vs 正式 audit_seed0"):
            L.append(f"- G0：{W['G0 乾跑原版營量 vs 正式 audit_seed0']}")
    L += ["", f"G5 策略鎖：{summ['G5 策略鎖']}", "",
          "早年：只描述；含減資假飆股約 0.3%（reduce_v2；剩 22 筆未解釋）；上櫃 2007-07～12 除權息未還原；上櫃減資 2007～2012 為偵測、非官方；2005-01～2007-06 只有上市", "",
          "描述，不是買賣建議"]
    open(os.path.join(OUT, "結果.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


def main():
    global LOGF
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", required=True, choices=["world", "groups", "sim", "report", "reg"])
    ap.add_argument("--world", choices=["main", "early"])
    ap.add_argument("--procs", type=int, default=3)
    a = ap.parse_args()
    os.makedirs(WORK, exist_ok=True)
    LOGF = os.path.join(WORK, "run.log")
    log(f"===== {a.step} {a.world or ''}｜登錄 {check_reg()}")
    if a.step == "world":
        step_world(a.world, a.procs)
    elif a.step == "groups":
        step_groups(a.world, a.procs)
    elif a.step == "sim":
        step_sim(a.world, a.procs)
    elif a.step == "report":
        step_report()


if __name__ == "__main__":
    main()
