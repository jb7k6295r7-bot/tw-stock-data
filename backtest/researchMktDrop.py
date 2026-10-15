# -*- coding: utf-8 -*-
"""大盤單日大跌之後買什麼（描述性初測、⛔ 不計 N、⛔ 不判定）——回測線計算子代理，2026-10-15。
使用者原話：「今天大跌，如果碰到買甚麼比較好？」「你測測看吧不用限定一定要買甚麼，不要每次都要有天數限制」。
⛔ 只計算：不 commit、不 push、不寫跨線信箱、不改既有檔；用語「假訊號」；⛔ 不給買賣建議。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMktDrop [--procs 4]

═══ 讀法（執行者補的都在這裡；寫死於第一次跑之前）═══
 M0 事件：加權指數 ＝ 公開庫 data/history/market_index.csv（git show 釘 origin/main sha，跑時記下）；日報酬 ＝ 收盤 ÷ 前一列收盤 − 1（檔內 change_pct 不帶正負號 ⇒ 不用）
    擴張視窗門檻 q(t) ＝ t 之前全部日報酬（1990 起、⛔ 不含 t）的 2％／1％分位（線性內插；前面少於 250 筆不算）；事件 ＝ r(t) ≤ q(t)
    另報固定門檻 r ≤ −2％、r ≤ −3％（描述）；去重 ＝ 前 20 個指數交易日（列）內已有同定義的事件 ⇒ 不是波段第一天、剔掉；另報不去重
 M1 世界（⛔ 不另寫資料層，同 researchDumb.load_world）：2015～ ＝ rerun17 快照 H2D（edc6f8002f，2015-01-05～2026-09-24）；
    2005～2014 ＝ ~/earlydata/eotc_f65bb03e11（上市＋上櫃）＋ reduce_v2／R8 早年壞根（researchAddOn.early_extra_bad）；
    逐股矩陣 ＝ ~/rluwork/world_{main,early}.pkl（GATE_V2 開 ∩ 四碼普通股，含已下市）；段 ＝ 2005～2014（早年世界）、2015～2021、2022～資料尾（主世界）
    ⚠ 指數資料到 2026-10-14、個股快照到 2026-09-24 ⇒ 09-24 之後的事件只列、不算；早年世界尾 2014-12-31 ⇒ 還沒出場的部位在該日收盤計值、標「窗尾未出場」
 M2 母體（C、D、E 用；＝ R1／營量營飆同一流動性閘）：快取股 ∧ pv[t]（UG.pit_valid）∧ patterns.Frame.gate[t]（含 t 的 20 日都有成交 ∧ 前 20 日均量 ≥ 500 張）
    ∧ t 是有效 K 棒 ∧ 第 20 根起 ∧ [k−20, k] 無壞 K 棒（seq335 缺口 ≥ 5 日即壞根；壞 K 棒同 researchDumb Z3）；當天報酬 ＝ 還原收盤[k] ÷ 收盤[k−1] − 1
    可買 ＝ 下一根有效 K 棒就是 t＋1 ∧ 有成交 ∧ 開盤有效 ∧ 非開盤漲停鎖死 ∧ k＋1 不是壞 K 棒；名單先在母體裡排、再剔買不到的（比例照報）
 M3 候選（t 收盤決定、t＋1 開盤買、等權）：A 0050（還原）；B 00631L（有資料期間；2014-10-31 上市）；
    C 母體當天報酬最低 ceil(10％) 檔；D 最高 ceil(10％) 檔；E 產業大類（industry_pit pit 版＋營收彙總表後備，PRE.PIT，t 當天）母體成員 ≥ 5 檔的產業中
    等權當天報酬最低者的全部母體成員（排「其他」「存託憑證」「ETF」與無產業；金融保險保留）；
    F 營量 v1 候選池 ＝ t 當天「已達成」（research11 主格 5 取 3 ∧ 去重 20 根 ∧ research13.and_flags 營收 24 月新高）∪「即將達成」（list_yl13_watch B 區
    基本條件：eligible ∧ 分數 ＝ 2 ∧ 營收條件今天、明天都成立；⛔ 不加「兩天內可能」排序）；營收面板 主 ＝ resultsN17/sig_edc6f/panel_rev.csv.gz（edc6f 快照、與正式營量 AND 同源）、
    早年 ＝ eotc sig_otc/panel_rev.csv.gz；平均每事件 ＜ 2 檔或有檔事件 ＜ 10 ⇒ 標退化
 M4 出場（條件出場、⛔ 不設最長天數）：
    主 ＝ 加權指數收盤 ≥ 大跌前一日（t−1）收盤的第一天 d（d ＞ t）⇒ d 之後第一根可賣開盤賣（整籃同一天決定）
    副1 ＝ 持有標的收盤 ≥ 自身 MA20（從進場根起）之後，第一根收盤 ＜ MA20 ⇒ 下一根可賣開盤賣（MA20 ＝ 20 根有效 K 棒還原收盤平均，窗內無壞 K 棒）
    副2 ＝ 自進場根起最高收盤 − 收盤 ≥ 3 × ATR20（當根；TR 簡單平均 20 根、窗內無壞 K 棒）⇒ 下一根可賣開盤賣
    可賣開盤 ＝ 有成交 ∧ 開盤有效 ∧ 非開盤跌停鎖死（鎖跌停 ⇒ 順延）；持有中碰到壞 K 棒 ⇒ 前一根收盤強制賣；之後沒再成交 ⇒ 最後收盤（下市）；
    到世界尾仍持有 ⇒ 世界尾收盤計值、記「窗尾未出場」
 M5 報酬：每筆（事件×候選）＝ 等權籃子 (1 ＋ 平均毛報酬) × (1 − 成本) − 1；成本 股票 0.585％、ETF 0.385％（來回）；
    同期 0050 ＝ 每一檔換成 0050（同一天開盤買、同一時點賣：開盤賣用開盤、收盤賣用收盤，⛔ 不扣成本）後的平均
    等效獨立事件數 ＝ n² ÷ (n ＋ 2·P·ρ)，P ＝ 持有區間重疊的事件對數、ρ ＝ 重疊對報酬（去平均）乘積和 ÷ (P × 變異數)，夾在 [0, 1]
    年化：資金曲線 ＝ 有部位的日子取「當天在場各筆」的日報酬等權平均，沒部位 ＝ 現金 0％；段的曲線從段首到 max(段尾, 最後出場)；
      全期年化 ＝ 曲線終值^(245 ÷ 天數) − 1；⭐ 在場年化（以事件期間資金加權）＝ 只連乘在場日 ^(245 ÷ 在場日數) − 1；最大回落 ＝ 曲線最大回落
    一直抱 0050 ＝ 段首到段尾還原收盤（rerun17.bench_row）
 M6 隨機日（200 次）：同定義、同去重版、同段、同候選的事件，每年幾筆 ⇒ 該年非事件日（該定義的原始事件日都排除）且該候選當天籃子非空的日子裡不重複抽同樣筆數，
    同候選、同出場規則；統計 ＝ 每筆平均報酬；差 ＝ 實際 − 隨機平均；p ＝ 隨機平均 ≥ 實際 的比例（單尾）；default_rng([20261015, 定義, 去重, 段, 候選, i])
 M7 必附：⚠ 個股急跌錯殺五刀已封存（裁定 seq340）；本件 C 是以「大盤事件日」為準的不同事件，不是重開該件；早年含減資假飆股約 0.3％（剩 22 筆未解釋）；
    描述性初測、不計 N、不判定
輸出 backtest/resultsMktDrop/：MktDrop.json、MktDrop_main.csv、events.csv、event_rows.csv.gz、random.csv.gz、run.log；大檔 ~/mktdropwork/
── 事後註（照實記）──
 ① 18:40 煙霧測試（MKT_QUICK：每 10 檔一檔、隨機 3 次，輸出 /tmp；數字不是本件結果）；之前另跑出場邏輯對暴力解的單元測試（全過）
 ② 18:45 第一次全跑：主世界營收面板誤用 results3/panel.csv.gz（舊面板）⇒ 營量 AND 對帳 addonwork 窗內 2309 筆只對到 2172（137 筆營收條件不同）；
    改成正式營量同源的 resultsN17/sig_edc6f/panel_rev.csv.gz 重跑（只影響 F；其他候選與出場 ⛔ 沒改）
"""
from __future__ import annotations

import argparse
import bisect
import io
import json
import os
import pickle
import subprocess
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
QUICK = bool(os.environ.get("MKT_QUICK"))
if QUICK:                                                          # 煙霧測試（每 10 檔一檔；數字不是本件結果）
    os.environ["DUMB_QUICK"] = "1"
from backtest import data as D                              # noqa: E402
from backtest import research11 as R                        # noqa: E402
from backtest import research13 as R13                      # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402
from backtest import patterns as P                          # noqa: E402
from backtest import universe_gate as UG                    # noqa: E402
from backtest import researchAddOn as RA                    # noqa: E402
from backtest import researchIndRev_prereg as PRE           # noqa: E402
from backtest import researchDumb as DB                     # noqa: E402

UG.set_gate_v2(True)

OUT = "backtest/resultsMktDrop"
WORK = os.path.expanduser("~/mktdropwork")
ANN = 245
NRAND = 200
RSEED = 20261015
if QUICK:
    OUT, WORK, NRAND = "/tmp/mktdrop_quick", "/tmp/mktdrop_quick/work", 3
TIME = "2026-10-15 18:40（台北；讀法寫死、第一次跑之前）"
DEDUP_WIN = 20
COST_STK, COST_ETF = R.COST, 0.00385
CANDS = ["A", "B", "C", "D", "E", "F"]
CN = {"A": "0050（還原）", "B": "00631L 正2", "C": "當天跌最多一成", "D": "當天最抗跌一成", "E": "跌最多產業", "F": "營量v1 候選池（已達成＋即將達成）"}
EXITS = ["主", "副1", "副2"]
EN = {"主": "加權收復大跌前一日收盤 ⇒ 隔天開盤賣", "副1": "站回 MA20 後再跌破 ⇒ 隔天開盤賣", "副2": "買進後最高收盤回落 3×ATR20 ⇒ 隔天開盤賣"}
DEFS = ["q2", "q1", "f2", "f3"]
DN = {"q2": "擴張視窗最低 2%（主）", "q1": "擴張視窗最低 1%", "f2": "固定 ≤ −2%", "f3": "固定 ≤ −3%"}
SEGS = {"早年": {"2005～2014": ("2005-01-01", "2014-12-31")}, "主": {"2015～2021": ("2015-01-01", "2021-12-31"), "2022～": ("2022-01-01", None)}}
IND_DATA = os.path.expanduser("~/crashwork/tw_283eec12b2bc/data")
IND_EXCL = {"其他", "存託憑證", "ETF"}
PANEL = {"主": "backtest/resultsN17/sig_edc6f/panel_rev.csv.gz", "早年": os.path.expanduser("~/earlydata/eotc_f65bb03e11/sig_otc/panel_rev.csv.gz")}
ETFS = ["0050", "00631L"]
KIND = {0: "規則賣（開盤）", 1: "壞根前收盤強制", 2: "之後沒成交（最後收盤）", 3: "窗尾未出場"}
NOTES = ["⚠ 個股急跌錯殺五刀已封存（裁定 seq340）；本件 C 是以「大盤事件日」為準的不同事件（全市場同日大跌），不是重開該件",
         "早年（2005～2014）含減資假飆股約 0.3%（剩 22 筆未解釋）；上櫃 2007-07～12 除權息未還原；上櫃減資 2007～2012 為偵測、非官方；2005-01～2007-06 只有上市",
         "描述性初測：不計 N、不判定、⛔ 不是買賣建議",
         "指數資料到 2026-10-14、個股快照到 2026-09-24 ⇒ 09-24 之後的事件只列不算；今天（10-15）的大跌不在資料內"]
_G: dict = {}


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


# ═════════════ 工具 ═════════════
def build_sparse(a):
    st = [np.asarray(a, float)]
    w = 1
    while 2 * w <= len(a):
        p = st[-1]; st.append(np.maximum(p[:-w], p[w:])); w *= 2
    return st


def last_ge(st, pos, T):
    """最大 i ≤ pos 使 a[i] ≥ T；沒有 ⇒ −1（向量化二進位跳躍）。"""
    pos = np.asarray(pos, np.int64).copy(); T = np.asarray(T, float)
    if len(st[0]) == 0:
        return np.full(len(pos), -1, np.int64)
    for lev in range(len(st) - 1, -1, -1):
        w = 1 << lev; a0 = pos - w + 1; ok = (a0 >= 0) & (pos >= 0)
        if not ok.any():
            continue
        m = np.full(len(pos), np.inf); m[ok] = st[lev][a0[ok]]
        sk = ok & (m < T)
        pos[sk] -= w
    good = pos >= 0
    gi = np.flatnonzero(good)
    good[gi] = st[0][pos[gi]] >= T[gi]
    return np.where(good, pos, -1)


def first_ge_after(a, start, T):
    """最小 d ≥ start 使 a[d] ≥ T；沒有 ⇒ −1。"""
    a = np.asarray(a, float); n = len(a)
    st = build_sparse(a[::-1])
    r = last_ge(st, n - 1 - np.asarray(start, np.int64), T)
    return np.where(r >= 0, n - 1 - r, -1)


def nxt_true(m):
    """長度 n＋2：res[k] ＝ 第一個 j ≥ k 使 m[j]；沒有 ⇒ n。"""
    n = len(m)
    p = np.where(m, np.arange(n), n)
    r = np.minimum.accumulate(p[::-1])[::-1] if n else p
    return np.r_[r, n, n].astype(np.int64)


def qtl(srt, p):
    m = len(srt); x = p * (m - 1); lo = int(np.floor(x)); hi = min(lo + 1, m - 1)
    return srt[lo] + (x - lo) * (srt[hi] - srt[lo])


# ═════════════ 指數與事件 ═════════════
def load_index(log):
    sha = subprocess.run(["git", "rev-parse", "origin/main"], capture_output=True, text=True, check=True).stdout.strip()
    raw = subprocess.run(["git", "show", f"{sha}:data/history/market_index.csv"], capture_output=True, check=True).stdout
    df = pd.read_csv(io.BytesIO(raw), dtype={"date": str})
    df["date"] = pd.to_datetime(df["date"]); df["close"] = pd.to_numeric(df["close"], errors="coerce")
    n_raw = len(df)
    df = df.dropna(subset=["close"]).sort_values("date").drop_duplicates("date").reset_index(drop=True)
    cl = df["close"].to_numpy(float); n = len(cl)
    r = np.r_[np.nan, cl[1:] / cl[:-1] - 1.0]
    q2 = np.full(n, np.nan); q1 = np.full(n, np.nan); srt = []
    for i in range(n):
        if len(srt) >= 250:
            q2[i] = qtl(srt, 0.02); q1[i] = qtl(srt, 0.01)
        if np.isfinite(r[i]):
            bisect.insort(srt, r[i])
    with np.errstate(invalid="ignore"):
        RAW = {"q2": r <= q2, "q1": r <= q1, "f2": r <= -0.02, "f3": r <= -0.03}
    FIRST = {}
    for k, m in RAW.items():
        cs = np.r_[0, np.cumsum(m)]
        lo = np.maximum(np.arange(n) - DEDUP_WIN, 0)
        prior = cs[np.arange(n)] - cs[lo]
        FIRST[k] = m & (prior == 0)
    pre = np.r_[np.nan, cl[:-1]]
    rec = first_ge_after(cl, np.arange(n) + 1, pre)
    rec[0] = -1
    idx = {"sha": sha, "df": df, "cl": cl, "r": r, "q2": q2, "q1": q1, "RAW": RAW, "FIRST": FIRST, "rec": rec, "n": n}
    log(f"[指數] origin/main {sha[:10]}｜{df['date'].iloc[0].date()}～{df['date'].iloc[-1].date()}｜{n} 列（原 {n_raw}）｜"
        f"最新門檻 q2 {q2[-1]:.4%}、q1 {q1[-1]:.4%}（以 {df['date'].iloc[-1].date()} 之前全部日報酬；下一日適用值另算）")
    return idx


# ═════════════ 世界 ═════════════
def load_world(wn, IX, log):
    DB.SEGS = SEGS
    W = DB.load_world(wn, log)
    cal = W["cal"]; n0 = W["n0"]
    # 指數對到世界日曆
    pos_of = {d: j for j, d in enumerate(IX["df"]["date"])}
    rows = np.array([pos_of.get(d, -1) for d in cal], np.int64)
    W["idx_rows"] = rows
    W["gate"]["世界日曆對不到指數列"] = int((rows < 0).sum())
    first_row = int(rows[0]); last_row = int(rows[-1])
    W["gate"]["世界期間指數多出的列（世界日曆沒有）"] = int((last_row - first_row + 1) - (rows >= 0).sum())
    Darr = np.full(n0, n0, np.int64)
    calpos = {d: j for j, d in enumerate(cal)}
    for t in range(n0):
        rr = rows[t]
        if rr < 1:
            continue
        rc = IX["rec"][rr]
        if rc < 0:
            continue
        d = IX["df"]["date"].iloc[rc]
        Darr[t] = calpos.get(d, n0)
    W["Darr"] = Darr
    # 0050／00631L
    D.DATA = W["data"]
    for s in ETFS:
        st = D.load_stock(s, "twse", cal)
        W[f"etf_{s}"] = None if st is None else st.df
    W["BO"] = W[f"etf_0050"]["open"].to_numpy(float)
    W["BC"] = pd.Series(W[f"etf_0050"]["close"].to_numpy(float)).ffill().to_numpy(float)
    return W


# ═════════════ 逐股 ═════════════
def exits_core(idx, o, h, l, c, bad, sell_ok, end_ok, Darr, n0):
    """⇒ 每根訊號 K 棒 k（進場 ke ＝ k＋1）三種出場的 (賣出日曆位置, 價, 種類)。"""
    nb = len(idx); K = np.arange(nb)
    CB = np.r_[0, np.cumsum(bad)]

    def nbad(a_, b_):
        a_ = np.clip(a_, 0, nb - 1); b_ = np.clip(b_, 0, nb - 1)
        return CB[b_ + 1] - CB[a_]
    ma20 = pd.Series(c).rolling(20, min_periods=20).mean().to_numpy().copy()
    ma20[(K < 19) | (nbad(K - 18, K) > 0)] = np.nan
    tr = np.full(nb, np.nan); tr[1:] = np.maximum(h[1:], c[:-1]) - np.minimum(l[1:], c[:-1])
    atr = pd.Series(tr).rolling(20, min_periods=20).mean().to_numpy().copy()
    atr[(K < 20) | (nbad(K - 19, K) > 0)] = np.nan
    nxs = nxt_true(sell_ok)                    # 長度 nb＋2
    NBAD = nxt_true(bad)
    ke = np.minimum(K + 1, nb)                 # 進場根
    kb = NBAD[np.minimum(ke + 1, nb + 1)]       # 進場後第一個壞 K 棒
    # 主
    Dk = Darr[idx]
    kk = np.searchsorted(idx, Dk, "right")
    kk = np.where(Dk >= n0, nb, kk)
    S_main = nxs[np.minimum(kk, nb + 1)]
    # 副1
    with np.errstate(invalid="ignore"):
        above = np.isfinite(ma20) & (c >= ma20); below = np.isfinite(ma20) & (c < ma20)
    NA = nxt_true(above); NB_ = nxt_true(below)
    a1 = NA[np.minimum(ke, nb + 1)]
    d1 = NB_[np.minimum(a1 + 1, nb + 1)]
    S_1 = nxs[np.minimum(d1 + 1, nb + 1)]
    # 副2
    with np.errstate(invalid="ignore"):
        T = np.where(atr > 0, c + 3.0 * atr, np.nan)
    g = last_ge(build_sparse(c), K, T)
    M = np.full(nb + 2, nb, np.int64)
    ok = g >= 0
    np.minimum.at(M, g[ok], K[ok])
    sufm = np.minimum.accumulate(M[::-1])[::-1]
    d2 = sufm[np.minimum(ke, nb + 1)]
    S_2 = nxs[np.minimum(d2 + 1, nb + 1)]
    out = {}
    for nm, S in (("主", S_main), ("副1", S_1), ("副2", S_2)):
        spos = np.full(nb, -1, np.int64); spx = np.full(nb, np.nan); kd = np.full(nb, -1, np.int8)
        valid = K + 1 < nb
        rule = valid & (S < nb) & (S < kb)
        Si = np.minimum(S, nb - 1)
        spos[rule] = idx[Si[rule]]; spx[rule] = o[Si[rule]]; kd[rule] = 0
        frc = valid & ~rule & (kb < nb)
        q = np.maximum(kb - 1, 0)
        spos[frc] = idx[q[frc]]; spx[frc] = c[q[frc]]; kd[frc] = 1
        rest = valid & ~rule & ~frc
        if end_ok:
            spos[rest] = n0 - 1; spx[rest] = c[nb - 1]; kd[rest] = 3
        else:
            spos[rest] = idx[nb - 1]; spx[rest] = c[nb - 1]; kd[rest] = 2
        out[nm] = (spos, spx, kd)
    return out, ma20, atr


def stock_job(a):
    wn, sid = a
    W = _G[wn]; D.DATA = W["data"]; cal = W["cal"]; n0 = W["n0"]; i = W["ix"][sid]
    B = R.load_bars(sid, W["mk"].get(sid, "twse"), cal)
    if B is None:
        return sid, None
    df = B["df"]; idx = B["idx"].astype(np.int64); nb = len(idx)
    o, h, l, c = (np.asarray(B[k], float) for k in ("o", "h", "l", "c"))
    amt = np.asarray(B["amt"], float); up = np.asarray(B["up"], bool); skip = np.asarray(B["skip"], bool); next_bad = np.asarray(B["next_bad"])
    gate_b = np.asarray(P.Frame(df, set()).gate, bool)[idx]
    bad = np.asarray(next_bad[:nb] == np.arange(nb), bool)
    for p in W["BADPOS"].get(sid, ()):
        k = int(np.searchsorted(idx, p, "left"))
        if k < nb:
            bad[k] = True
    K = np.arange(nb)
    CB = np.r_[0, np.cumsum(bad)]

    def nbad(a_, b_):
        a_ = np.clip(a_, 0, nb - 1); b_ = np.clip(b_, 0, nb - 1)
        return CB[b_ + 1] - CB[a_]
    TRD = W["TRD"][i]; O = W["O"][i]; UPL = W["UPL"][i]; DNL = W["DNL"][i]
    sell_ok = TRD[idx] & np.isfinite(O[idx]) & (O[idx] > 0) & ~DNL[idx]
    end_ok = bool(idx[-1] == n0 - 1)
    ex, ma20, atr = exits_core(idx, o, h, l, c, bad, sell_ok, end_ok, W["Darr"], n0)
    pv_b = W["PV"][i, idx]
    mem = gate_b & pv_b & (K >= 20) & (nbad(K - 20, K) == 0)
    ret1 = np.full(nb, np.nan); ret1[1:] = c[1:] / c[:-1] - 1.0
    e = idx + 1
    nxt_is_e = np.zeros(nb, bool); nxt_is_e[:-1] = idx[1:] == e[:-1]
    ec = np.minimum(e, n0 - 1)
    nbk1 = np.zeros(nb, bool); nbk1[:-1] = bad[1:]
    buy = nxt_is_e & (e < n0) & TRD[ec] & np.isfinite(O[ec]) & (O[ec] > 0) & ~UPL[ec] & ~nbk1
    bp = np.full(nb, np.nan); bp[:-1] = o[1:]
    # 產業（只算母體根）
    PIT = _G["PIT"]; ind = np.full(nb, None, object)
    for k in np.flatnonzero(mem):
        ind[k] = PIT._at(sid, cal[idx[k]], "pit")[0]
    # 營量 5 取 3（research11 主格）
    ret20 = np.array(c / np.roll(c, 20) - 1, dtype=float); ret20[:20] = np.nan
    nup20 = pd.Series(up.astype(int)).rolling(20, min_periods=20).sum().to_numpy(float)
    amt_prev20 = np.array(R._roll_mean(np.roll(amt, 1), 20), dtype=float); amt_prev20[:21] = np.nan
    with np.errstate(invalid="ignore", divide="ignore"):
        amt_ratio = amt / amt_prev20
    ma100 = R._roll_mean(c, 100); hi250 = R._roll_max(c, 250)
    nb_sig = np.array([next_bad[max(0, k - 20)] for k in range(nb)])
    elig = (K >= 249) & ~skip & ~np.isnan(ma100) & ~np.isnan(amt_ratio) & (nb_sig > K)
    with np.errstate(invalid="ignore"):
        score = ((ret20 >= 0.30).astype(int) + (nup20 >= 3).astype(int) + (amt_ratio >= 3.0).astype(int) + (c > ma100).astype(int) + (c >= hi250).astype(int))
    cand = np.flatnonzero(elig & (score >= 3))
    last = -10 ** 9; picks = []
    for k in cand:
        if k - last > 20:
            picks.append(int(k)); last = k
    near = np.flatnonzero(elig & (score == 2))
    cc = W["C"][i, idx]; okc = np.isfinite(cc) & np.isfinite(c)
    dc = float(np.max(np.abs(cc[okc] / c[okc] - 1.0))) if okc.any() else 0.0
    pk = {"idx": idx, "mem": mem, "ret1": ret1, "buy": buy, "bp": bp, "ind": ind, "ex": ex,
          "picks": picks, "near": near, "gate_c": dc}
    return sid, pk


def etf_pack(W, s):
    df = W[f"etf_{s}"]; n0 = W["n0"]
    if df is None:
        return None
    tr = df["traded"].to_numpy(bool)
    idx = np.flatnonzero(tr).astype(np.int64)
    if len(idx) < 25:
        return None
    o = df["open"].to_numpy(float)[idx]; h = df["high"].to_numpy(float)[idx]; l = df["low"].to_numpy(float)[idx]; c = df["close"].to_numpy(float)[idx]
    nb = len(idx); bad = np.zeros(nb, bool)
    sell_ok = np.isfinite(o) & (o > 0)
    end_ok = bool(idx[-1] == n0 - 1)
    ex, _, _ = exits_core(idx, o, h, l, c, bad, sell_ok, end_ok, W["Darr"], n0)
    e = idx + 1
    buy = np.zeros(nb, bool); buy[:-1] = (idx[1:] == e[:-1]) & np.isfinite(o[1:]) & (o[1:] > 0)
    bp = np.full(nb, np.nan); bp[:-1] = o[1:]
    cff = pd.Series(df["close"].to_numpy(float)).ffill().to_numpy(float)
    return {"idx": idx, "buy": buy, "bp": bp, "ex": ex, "cff": cff}


# ═════════════ 組矩陣 ═════════════
def assemble(W, PK, EP, log):
    n0 = W["n0"]; sids = sorted(PK); S = len(sids); NR = S + len(ETFS)
    MEM = np.zeros((S, n0), bool); RET = np.full((S, n0), np.nan); BUY = np.zeros((NR, n0), bool); BP = np.full((NR, n0), np.nan)
    SP = {x: np.full((NR, n0), -1, np.int32) for x in EXITS}; SX = {x: np.full((NR, n0), np.nan) for x in EXITS}; SK = {x: np.full((NR, n0), -1, np.int8) for x in EXITS}
    IND = np.full((S, n0), -1, np.int16); inds = {}
    C = np.zeros((NR, n0))
    for r, s in enumerate(sids):
        pk = PK[s]; idx = pk["idx"]
        MEM[r, idx] = pk["mem"]; RET[r, idx] = pk["ret1"]; BUY[r, idx] = pk["buy"]; BP[r, idx] = pk["bp"]
        for x in EXITS:
            sp, sx, kd = pk["ex"][x]; SP[x][r, idx] = sp; SX[x][r, idx] = sx; SK[x][r, idx] = kd
        for k in np.flatnonzero(pk["mem"]):
            v = pk["ind"][k]
            if v is None or v in IND_EXCL:
                continue
            IND[r, idx[k]] = inds.setdefault(v, len(inds))
        C[r] = W["C"][W["ix"][s]]
    for j, s in enumerate(ETFS):
        r = S + j; ep = EP.get(s)
        if ep is None:
            C[r] = np.nan; continue
        idx = ep["idx"]; BUY[r, idx] = ep["buy"]; BP[r, idx] = ep["bp"]
        for x in EXITS:
            sp, sx, kd = ep["ex"][x]; SP[x][r, idx] = sp; SX[x][r, idx] = sx; SK[x][r, idx] = kd
        C[r] = ep["cff"]
    # C 矩陣：快取已 ffill；起始前 NaN 保持
    M = {"sids": sids, "S": S, "NR": NR, "MEM": MEM, "RET": RET, "BUY": BUY, "BP": BP, "SP": SP, "SX": SX, "SK": SK, "IND": IND,
         "inds": {v: k for k, v in inds.items()}, "C": C}
    log(f"[矩陣 {W['name']}] 股 {S}｜產業 {len(inds)}｜母體股日 {int(MEM.sum())}")
    return M


def f_flags(W, PK, M, log):
    """營量 v1：已達成（AND）、即將達成（分數 2 ∧ 營收今天明天成立）。"""
    cal = W["cal"]; n0 = W["n0"]
    pn = pd.read_csv(PANEL[W["name"]], dtype={"stock_id": str}, usecols=["stock_id", "signal_pos", "signal_date", "rev_hi24"])
    calpos = {str(d.date()): j for j, d in enumerate(cal)}
    newpos = pn["signal_date"].map(calpos)
    gate = {"面板列": int(len(pn)), "signal_date 對不到世界日曆": int(newpos.isna().sum()),
            "signal_pos 與日期位置不同": int(((newpos.notna()) & (newpos != pn["signal_pos"])).sum())}
    pn = pn[newpos.notna()].copy(); pn["signal_pos"] = newpos[newpos.notna()].astype(int)
    pn["rev_hi24"] = pn["rev_hi24"].fillna(False).astype(bool)
    Sx = pd.DataFrame([(s, k, int(PK[s]["idx"][k])) for s in M["sids"] for k in PK[s]["picks"]], columns=["sid", "k", "pos"])
    flags, _ = R13.and_flags(Sx, pn)
    AND = Sx[flags]
    ACH = np.zeros((M["S"], n0), bool); NEAR = np.zeros((M["S"], n0), bool)
    rix = {s: r for r, s in enumerate(M["sids"])}
    for s, p in zip(AND["sid"], AND["pos"]):
        ACH[rix[s], p] = True
    by = {sid: (g["signal_pos"].to_numpy(), g["rev_hi24"].to_numpy(bool)) for sid, g in pn.sort_values(["stock_id", "signal_pos"]).groupby("stock_id")}
    for s in M["sids"]:
        nr = PK[s]["near"]
        if not len(nr) or s not in by:
            continue
        t = PK[s]["idx"][nr]; sp, hi = by[s]
        j = np.searchsorted(sp, t, "right") - 1
        okj = j >= 0; jj = np.maximum(j, 0)
        ok = okj & hi[jj] & (t - sp[jj] <= R13.STALE_MAX) & (t + 1 - sp[jj] <= R13.STALE_MAX)
        NEAR[rix[s], t[ok]] = True
    # 對帳：addonwork 世界 SIG[False]（營量 AND，窗內）
    Wa = pickle.load(open(os.path.join(RA.WORK, f"world_{W['name']}.pkl"), "rb"))
    ref = Wa["SIG"][False]; w0, w1 = Wa["w0"], Wa["w1"]
    if len(Wa["cal"]) == n0 and (Wa["cal"] == cal).all():
        A_ = set(zip(ref["sid"], ref["pos"].astype(int)))
        mine = AND[(AND["pos"] + 1 >= w0) & (AND["pos"] + 1 <= w1)]
        B_ = set(zip(mine["sid"], mine["pos"].astype(int)))
        gate["AND 對帳 addonwork SIG[False]（窗內）"] = {"既有": len(A_), "本程式": len(B_), "交集": len(A_ & B_), "只在既有": len(A_ - B_), "只在本程式": len(B_ - A_)}
    else:
        gate["AND 對帳"] = "日曆不同、略過"
    log(f"[營量 {W['name']}] AND {len(AND)}｜即將達成股日 {int(NEAR.sum())}｜{gate}")
    M["ACH"] = ACH; M["NEAR"] = NEAR
    return gate


# ═════════════ 每日籃子 ═════════════
def basket(M, t, cd):
    S = M["S"]
    if cd in ("A", "B"):
        r = S + (0 if cd == "A" else 1)
        sel = np.array([r]) if np.isfinite(M["BP"][r, t]) or M["BUY"][r, t] else np.array([], int)
        return (np.array([r]) if M["BUY"][r, t] else np.array([], int)), len(sel), None
    if cd == "F":
        sel = np.flatnonzero(M["ACH"][:, t] | M["NEAR"][:, t])
        return sel[M["BUY"][sel, t]], len(sel), None
    m = M["MEM"][:, t] & np.isfinite(M["RET"][:, t])
    rows = np.flatnonzero(m)
    if len(rows) < 20:
        return np.array([], int), 0, None
    v = M["RET"][rows, t]
    if cd in ("C", "D"):
        ns = int(np.ceil(0.10 * len(rows)))
        o = np.argsort(v, kind="stable")
        sel = rows[o[:ns]] if cd == "C" else rows[o[::-1][:ns]]
        return sel[M["BUY"][sel, t]], len(sel), None
    ic = M["IND"][rows, t]; ok = ic >= 0
    if not ok.any():
        return np.array([], int), 0, None
    df = pd.DataFrame({"i": ic[ok], "v": v[ok], "r": rows[ok]})
    g = df.groupby("i")["v"].agg(["mean", "count"]); g = g[g["count"] >= 5]
    if not len(g):
        return np.array([], int), 0, None
    worst = int(g["mean"].idxmin())
    sel = df.loc[df["i"] == worst, "r"].to_numpy()
    return sel[M["BUY"][sel, t]], len(sel), M["inds"][worst]


def day_stats(W, M, log):
    """每個日子 t（t＋1 在世界內）每候選每出場的籃子結果（隨機日與事件共用）。"""
    n0 = W["n0"]; BO, BC = W["BO"], W["BC"]
    out = {cd: {"n": np.zeros(n0, int), "nsel": np.zeros(n0, int), "ind": np.full(n0, None, object),
                **{x: {k: np.full(n0, np.nan) for k in ("net", "gross", "hold", "unex", "b50", "maxhold")} for x in EXITS}} for cd in CANDS}
    MEMB = {}
    for t in range(n0 - 1):
        for cd in CANDS:
            I, nsel, ind = basket(M, t, cd)
            o = out[cd]; o["n"][t] = len(I); o["nsel"][t] = nsel; o["ind"][t] = ind
            if not len(I):
                continue
            MEMB[(cd, t)] = I
            cost = COST_ETF if cd in ("A", "B") else COST_STK
            bp = M["BP"][I, t]; e = t + 1
            for x in EXITS:
                sp = M["SP"][x][I, t].astype(np.int64); sx = M["SX"][x][I, t]; kd = M["SK"][x][I, t]
                g = sx / bp - 1.0
                gm = float(np.mean(g))
                o[x]["gross"][t] = gm; o[x]["net"][t] = (1 + gm) * (1 - cost) - 1
                o[x]["hold"][t] = float(np.mean(sp - e)); o[x]["maxhold"][t] = float(np.max(sp - e)); o[x]["unex"][t] = float(np.mean(kd == 3))
                bb = np.where(kd == 0, BO[np.minimum(sp, n0 - 1)], BC[np.minimum(sp, n0 - 1)])
                b0 = BO[e] if e < n0 else np.nan
                o[x]["b50"][t] = float(np.nanmean(bb / b0 - 1.0)) if np.isfinite(b0) else np.nan
    log(f"[每日籃子 {W['name']}] " + "｜".join(f"{cd} 有籃日 {int((out[cd]['n'] > 0).sum())}、平均檔數 {out[cd]['n'][out[cd]['n'] > 0].mean() if (out[cd]['n'] > 0).any() else 0:.1f}" for cd in CANDS))
    return out, MEMB


def trade_path(W, M, I, t, x, cost):
    n0 = W["n0"]; e = t + 1
    sp = M["SP"][x][I, t].astype(np.int64); sx = M["SX"][x][I, t]; bp = M["BP"][I, t]
    end = int(min(max(sp.max(), e), n0 - 1))
    P_ = M["C"][I, e:end + 1] / bp[:, None]
    tt = np.arange(e, end + 1)[None, :]
    P_ = np.where(tt >= sp[:, None], (sx / bp)[:, None], P_)
    V = np.nanmean(P_, axis=0) * (1 - cost)
    r = V / np.r_[1.0, V[:-1]] - 1.0
    return e, end, r


# ═════════════ 彙總 ═════════════
def eff_n(vals, iv):
    n = len(vals)
    if n < 2:
        return float(n), np.nan, 0
    v = np.asarray(vals, float); d = v - v.mean(); var = float(np.mean(d ** 2))
    pairs = 0; acc = 0.0
    for a in range(n):
        for b in range(a + 1, n):
            if iv[a][0] <= iv[b][1] and iv[b][0] <= iv[a][1]:
                pairs += 1; acc += d[a] * d[b]
    if pairs == 0 or var == 0:
        return float(n), (np.nan if pairs == 0 else 0.0), pairs
    rho = float(np.clip(acc / (pairs * var), 0.0, 1.0))
    return float(n * n / (n + 2 * pairs * rho)), rho, pairs


def seg_curve(W, paths, x0, y0):
    n0 = W["n0"]
    y = max([y0] + [p[1] for p in paths]); y = min(y, n0 - 1)
    L = y - x0 + 1
    sm = np.zeros(L); ct = np.zeros(L)
    for e, end, r in paths:
        a = e - x0; b = end - x0 + 1
        rr = np.nan_to_num(r[:b - a] if b - a <= len(r) else r, nan=0.0)
        sm[a:a + len(rr)] += rr; ct[a:a + len(rr)] += 1
    R_ = np.where(ct > 0, sm / np.maximum(ct, 1), 0.0)
    eq = np.cumprod(1 + R_)
    full = float(eq[-1] ** (ANN / L) - 1) if L > 0 else np.nan
    inm = ct > 0; ni = int(inm.sum())
    inm_ann = float(np.prod(1 + R_[inm]) ** (ANN / ni) - 1) if ni else np.nan
    mdd = float(np.min(np.r_[1.0, eq] / np.maximum.accumulate(np.r_[1.0, eq]) - 1))
    return {"全期年化（閒置現金0%）": full, "在場年化（事件期間資金加權）": inm_ann, "最大回落": mdd, "在場日比例": ni / L if L else np.nan,
            "曲線天數": L, "曲線尾": str(W["cal"][y].date())}


def run(a, log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    S = {"讀法寫死": TIME, "開跑（台北）": now_tpe(), "讀法":"見程式檔頭 M0～M7（第一次跑之前寫死）", "必附": NOTES, "候選": CN, "出場": EN, "事件定義": DN, "閘": {}}
    IX = load_index(log)
    S["指數"] = {"origin/main sha": IX["sha"], "期間": f"{IX['df']['date'].iloc[0].date()}～{IX['df']['date'].iloc[-1].date()}",
                 "最新 q2 門檻（以資料尾之前）": float(IX["q2"][-1]), "最新 q1 門檻": float(IX["q1"][-1])}
    # 資料尾之後（下一日）適用門檻：含資料尾那天
    srt = np.sort(IX["r"][np.isfinite(IX["r"])])
    S["指數"]["下一交易日適用門檻 q2（含 2026-10-14）"] = float(qtl(list(srt), 0.02))
    S["指數"]["下一交易日適用門檻 q1"] = float(qtl(list(srt), 0.01))
    log(f"[門檻] 下一交易日適用 q2 {S['指數']['下一交易日適用門檻 q2（含 2026-10-14）']:.4%}｜q1 {S['指數']['下一交易日適用門檻 q1']:.4%}")
    PRE_rev = PRE.load_rev(IND_DATA)
    _G["PIT"] = PRE.PIT(IND_DATA, PRE_rev[2])
    # 事件表（全部，含世界外）
    df = IX["df"]; ev_rows = []
    for k in DEFS:
        for i in np.flatnonzero(IX["RAW"][k]):
            if df["date"].iloc[i] < pd.Timestamp("2005-01-01"):
                continue
            rc = IX["rec"][i]
            ev_rows.append({"定義": k, "日期": str(df["date"].iloc[i].date()), "指數報酬": float(IX["r"][i]), "門檻": float(IX[k][i]) if k in ("q2", "q1") else (-0.02 if k == "f2" else -0.03),
                            "波段第一天": bool(IX["FIRST"][k][i]), "收復日": (str(df["date"].iloc[rc].date()) if rc >= 0 else None),
                            "等待（指數交易日）": int(rc - i) if rc >= 0 else int(IX["n"] - 1 - i), "未收復（到指數尾）": bool(rc < 0)})
    EV = pd.DataFrame(ev_rows)
    EV.to_csv(os.path.join(OUT, "events.csv"), index=False, encoding="utf-8")
    log("[事件數 2005～指數尾] " + "｜".join(f"{k} 原始 {int((EV['定義'] == k).sum())}、去重 {int(((EV['定義'] == k) & EV['波段第一天']).sum())}" for k in DEFS))
    TAB = []; RND = []; EVR = []
    for wn in ("早年", "主"):
        W = load_world(wn, IX, log); _G[wn] = W
        S["閘"][wn] = {"世界": W["gate"], "壞根": W["bad_info"]}
        cp = os.path.join(WORK, f"packs_{wn}.pkl")
        if os.path.exists(cp):
            PK = pickle.load(open(cp, "rb")); log(f"[逐股 {wn}] 讀快取 {cp}")
        else:
            t0 = time.time(); PK = {}
            with Pool(a.procs) as pool:
                for j, (s, pk) in enumerate(pool.imap_unordered(stock_job, [(wn, s) for s in W["run_sids"]], chunksize=8)):
                    if pk is not None:
                        PK[s] = pk
                    if j % 400 == 0:
                        log(f"[逐股 {wn}] {j}/{len(W['run_sids'])}｜{time.time() - t0:.0f}s")
            pickle.dump(PK, open(cp, "wb"), protocol=5)
        gc = max(v["gate_c"] for v in PK.values())
        S["閘"][wn]["快取收盤 vs load_bars 最大相對差"] = gc
        if gc > 1e-9:
            raise SystemExit(f"⛔ {wn} 價格閘不過 {gc}")
        EP = {s: etf_pack(W, s) for s in ETFS}
        S["閘"][wn]["ETF 有資料"] = {s: (None if EP[s] is None else f"{W['cal'][EP[s]['idx'][0]].date()}～{W['cal'][EP[s]['idx'][-1]].date()}") for s in ETFS}
        M = assemble(W, PK, EP, log)
        S["閘"][wn]["營量"] = f_flags(W, PK, M, log)
        DAY, MEMB = day_stats(W, M, log)
        cal = W["cal"]; n0 = W["n0"]
        datepos = {d: j for j, d in enumerate(cal)}
        for sg, (x0, y0) in W["segp"].items():
            b = RR.bench_row(cal, W["bench"], x0, y0 + 1)
            S.setdefault("0050 一直抱", {})[sg] = {"窗": f"{cal[x0].date()}～{cal[y0].date()}", "年化": b["cagr"], "回落": b["mdd"]}
        for k in DEFS:
            rawpos = set()
            for i in np.flatnonzero(IX["RAW"][k]):
                p = datepos.get(df["date"].iloc[i])
                if p is not None:
                    rawpos.add(p)
            for dd in (True, False):
                evs = []
                for i in np.flatnonzero(IX["FIRST"][k] if dd else IX["RAW"][k]):
                    p = datepos.get(df["date"].iloc[i])
                    if p is not None and p + 1 < n0:
                        evs.append((p, i))
                for sg, (x0, y0) in W["segp"].items():
                    es = [(p, i) for p, i in evs if x0 <= p <= y0]
                    idxw = [IX["rec"][i] for _, i in es]
                    unrec = float(np.mean([r_ < 0 for r_ in idxw])) if es else np.nan
                    waits = [(int(IX["rec"][i] - i) if IX["rec"][i] >= 0 else int(IX["n"] - 1 - i)) for _, i in es]
                    for cd in CANDS:
                        cost = COST_ETF if cd in ("A", "B") else COST_STK
                        ec = [(p, i) for p, i in es if DAY[cd]["n"][p] > 0]
                        nsel = np.array([DAY[cd]["nsel"][p] for p, _ in ec]); nb_ = np.array([DAY[cd]["n"][p] for p, _ in ec])
                        # 隨機日池
                        yrs = pd.Series([cal[p].year for p, _ in ec]).value_counts().to_dict()
                        pool = {}
                        for y_ in yrs:
                            ds = [t for t in range(x0, min(y0, n0 - 2) + 1) if cal[t].year == y_ and t not in rawpos and DAY[cd]["n"][t] > 0]
                            pool[y_] = np.array(ds, int)
                        draws = []
                        for rep in range(NRAND):
                            rng = np.random.default_rng([RSEED, DEFS.index(k), int(dd), list(W["segp"]).index(sg) + (0 if wn == "早年" else 1), CANDS.index(cd), rep])
                            dl = []
                            for y_, c_ in sorted(yrs.items()):
                                pl = pool[y_]
                                if len(pl):
                                    dl.append(rng.choice(pl, size=min(c_, len(pl)), replace=False))
                            draws.append(np.concatenate(dl) if dl else np.array([], int))
                        for x in EXITS:
                            D_ = DAY[cd][x]
                            vals = np.array([D_["net"][p] for p, _ in ec]); holds = np.array([D_["hold"][p] for p, _ in ec])
                            mh = np.array([D_["maxhold"][p] for p, _ in ec]); unex = np.array([D_["unex"][p] for p, _ in ec]); b50 = np.array([D_["b50"][p] for p, _ in ec])
                            row = {"世界": wn, "段": sg, "定義": k, "去重": dd, "候選": cd, "出場": x, "指數事件數（段內）": len(es), "事件數（籃子非空）": len(ec)}
                            if len(ec):
                                paths = []
                                for p, _ in ec:
                                    e_, end_, r_ = trade_path(W, M, MEMB[(cd, p)], p, x, cost)
                                    paths.append((e_, end_, r_))
                                iv = [(e_, end_) for e_, end_, _ in paths]
                                ne, rho, prs = eff_n(vals, iv)
                                rm = np.array([np.mean(DAY[cd][x]["net"][dr]) if len(dr) else np.nan for dr in draws])
                                row.update({"等效獨立事件數": ne, "ρ（重疊對）": rho, "重疊對數": prs,
                                            "平均報酬": float(np.mean(vals)), "中位報酬": float(np.median(vals)), "勝率": float(np.mean(vals > 0)),
                                            "平均持有天數": float(np.mean(holds)), "最長持有天數": float(np.max(mh)),
                                            "未出場比例（籃內檔數平均）": float(np.mean(unex)), "有未出場的事件數": int(np.sum(unex > 0)),
                                            "同期0050平均": float(np.nanmean(b50)), "減同期0050": float(np.mean(vals) - np.nanmean(b50)),
                                            "平均籃子檔數": float(np.mean(nb_)), "買不到比例": float(1 - nb_.sum() / nsel.sum()) if nsel.sum() else np.nan,
                                            **seg_curve(W, paths, x0, y0),
                                            "隨機平均": float(np.nanmean(rm)), "實際減隨機": float(np.mean(vals) - np.nanmean(rm)),
                                            "p（隨機 ≥ 實際）": float(np.nanmean(rm >= np.mean(vals))), "隨機筆數": int(np.median([len(dr) for dr in draws]))})
                                if x == "主":
                                    row["指數未收復比例（到指數尾）"] = unrec; row["指數最長等待（交易日）"] = int(max(waits)) if waits else np.nan
                                    row["指數等待中位"] = float(np.median(waits)) if waits else np.nan
                                for rep, v in enumerate(rm):
                                    RND.append({"世界": wn, "段": sg, "定義": k, "去重": dd, "候選": cd, "出場": x, "i": rep, "隨機平均": v})
                                if k == "q2":
                                    for (p, i), v, hd, u, b5 in zip(ec, vals, holds, unex, b50):
                                        EVR.append({"段": sg, "去重": dd, "日期": str(cal[p].date()), "指數報酬": float(IX["r"][i]), "候選": cd, "出場": x,
                                                    "檔數": int(DAY[cd]["n"][p]), "產業": DAY[cd]["ind"][p], "報酬": v, "持有天數": hd, "未出場比例": u, "同期0050": b5})
                            TAB.append(row)
                log(f"[{wn}] {k} 去重={dd} 完｜{time.time() - T0:.0f}s")
        del M, DAY, MEMB, PK
    TB = pd.DataFrame(TAB)
    TB.to_csv(os.path.join(OUT, "MktDrop_main.csv"), index=False, float_format="%.6g", encoding="utf-8")
    pd.DataFrame(EVR).to_csv(os.path.join(OUT, "event_rows.csv.gz"), index=False, float_format="%.6g")
    pd.DataFrame(RND).to_csv(os.path.join(OUT, "random.csv.gz"), index=False, float_format="%.6g")
    # F 退化
    deg = {}
    for (wn, sg), g in TB[(TB["定義"] == "q2") & TB["去重"] & (TB["候選"] == "F") & (TB["出場"] == "主")].groupby(["世界", "段"]):
        r_ = g.iloc[0]
        deg[sg] = {"有檔事件": int(r_["事件數（籃子非空）"]), "指數事件": int(r_["指數事件數（段內）"]), "平均檔數": float(r_.get("平均籃子檔數", np.nan)),
                   "退化": bool(r_["事件數（籃子非空）"] < 10 or not (r_.get("平均籃子檔數", 0) >= 2))}
    S["F 退化"] = deg
    S["結束（台北）"] = now_tpe(); S["耗時秒"] = round(time.time() - T0)
    json.dump(S, open(os.path.join(OUT, "MktDrop.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    show = TB[(TB["定義"] == "q2") & TB["去重"]][["段", "候選", "出場", "事件數（籃子非空）", "等效獨立事件數", "平均報酬", "中位報酬", "勝率", "平均持有天數",
                                                 "未出場比例（籃內檔數平均）", "同期0050平均", "在場年化（事件期間資金加權）", "最大回落", "實際減隨機", "p（隨機 ≥ 實際）"]]
    log("[主表 q2 去重]\n" + show.to_string())
    log(f"[完] {S['耗時秒']}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    log = RA.log_to(os.path.join(OUT, "run.log"))
    run(a, log)


if __name__ == "__main__":
    main()
