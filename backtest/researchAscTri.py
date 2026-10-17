# -*- coding: utf-8 -*-
"""PREREG上升三角組合層 seq3（台股策略線 登錄 sha 3be823297d0b36d5，2026-10-17 09:38，定版；裁定 seq358 發號 N_組合 ＋1、
seq360 §一 主判改「空格放 0050」、seq361）——回測線計算子代理。
⛔ 只計算：不 commit、不改既有程式與結果夾、引擎 research11.simulate_mtm ⛔ 不改；用語「假訊號」；⛔ 不給買賣建議。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchAscTri [--procs 2]
    獨立查核：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchAscTri_check

⭐ 讀法寫死：2026-10-17 09:55～10:30（台北）之間寫檔；寫死前 ⛔ 沒算任何本件報酬（看過的只有 seq2 頻率表：訊號數、持股檔數、持有天數，⛔ 無報酬）

═══ 讀法（A 標；登錄沒寫清楚、執行者補的都在這裡）═══
 A0 型態與訊號（登錄 §一）：⛔ 不另寫——偵測 ＝ patterns_all.detect_lines 原樣 S06，上下線 ＝ researchAscTri_freq._lines_replica
    （逐檔斷言兩者 (T, first) 逐筆相同）、去重 ＝ researchAscTri_freq._dedup；世界、母體、壞根 ＝ researchAscTri_freq.load_world
    （Q1／Q2，＝ researchDumb Z1／Z3／Z4；早年 reduce_v2 ＋ R8）；剔除順序、可買、出場時點 ＝ 頻率表 Q3／Q4 同式，
    ⭐ 每一筆訊號的（剔除、買進日、賣出日、出場種類）都與已提交的 resultsAscTri/freq/signals_{主,早年}.csv.gz 逐筆比對，任一筆不同 ⇒ 中止。
    ⚠ 本支要求「偵測有效 K 棒 ＝ load_bars 有效 K 棒」（頻率表兩世界 0 檔不同）⇒ 下線第 j 根的值 ＝ la ＋ lb × j；不同 ⇒ 中止。
 A1 出場價（登錄 §二）：買價 ＝ e 的還原開盤；a／b 觸發 ⇒ 觸發根之後第一根可賣開盤（有成交 ∧ 開盤有效 ∧ 非開盤跌停鎖死）的還原開盤；
    壞根前強制 ⇒ kb−1 收盤（記在次一日曆日）；下市／停止交易 ⇒ 最後收盤（記次一日曆日）；資料尾仍持有 ⇒ 資料尾收盤（xpos ＝ n0，窗尾照實報）。
    gross ＝ 賣價 ÷ 買價 − 1（還原）；引擎 ep ＝ 快取還原開盤（與 load_bars 開盤相對差 ≤ 1e−9 閘）。
 A2 組合（登錄 §二）：正式引擎 research11.simulate_mtm（⛔ 不改）：10 槽、新部位 min(前一日權益 ÷ 10, 可提現金)、抽籤 default_rng(1000)、
    同檔同時一筆、賣後可再進、同日先出後進；sig 依 (entry_pos, 代號) 排序；stop_force 傳入當保險（應 0 次）。
    ⭐ 主判「空格放 0050」＝ cash_mode="bench"、bench ＝ 0050 還原收盤（rerun17.load_bench，ffill）：沒用到的格子全部以 0050 單位數持有；
       訊號來時賣 0050 撥出、賣出拿回的錢買回 0050。⚠ 引擎 bench_cost 是對稱單邊 ⇒ 取 0.385% ÷ 2 ＝ 0.1925%（來回合計 ＝ 登錄 0.1425%×2＋0.1%；
       登錄字面買 0.1425%、賣 0.2425% 不對稱 ⇒ 引擎沒有不對稱開關，⛔ 不改引擎，照報）；0050 部分 ⛔ 不每日再平衡回「每格 1/10」（＝ 引擎 bench 慣例：
       閒置資金整包抱 0050）；窗首建倉 0050 ⛔ 不扣成本（引擎慣例）。
       引擎在第一筆進場前權益固定 1、最後一筆出場＋2 之後凍結 ⇒ bench 臂在段內若碰到這兩端，以 0050 價格比例延伸（全部是 0050，延伸是精確的；
       延伸天數照報，段內為 0 才不必延伸）。
    描述「空格留現金」＝ cash_mode="zero"（seq2 原主規則；⛔ 不判、不觸退化）。
 A3 描述出場（⛔ 不判）：固定 20 日、60 日 ＝ research11 口徑「持有 H 根（進場根算第 1 根）收盤賣」（D.exit_pos；＝ researchDumb F6）；
    途中壞根、下市、資料尾照 A1；與主判同樣空格放 0050。
 A4 描述臂 營收年增 ＞ 0（⛔ 不判）：月營收 ＝ researchExit5.load_revenue（mops/revenue_hist；年增 ＝ 當月 ÷ 去年當月 − 1、去年當月 ＞ 0 才可判）；
    可得日 ＝ researchExit5.avail_pos（期別次月 10 日（≤ 2025-12）／15 日（≥ 2026-01）之後第一個交易日）；T 當天可得 ＝ 可得日 ≤ T；
    「最近一期」＝ 可得日 ≤ T 的期別中、該股有營收值的最新一期；年增 ＞ 0 才買、不可判 ⇒ 不買；其餘同主判（空格放 0050）。
 A5 滑價（登錄 §二 另報、⛔ 不判）：個股買價 ×1.005、每筆賣價 ×0.995（含強制、資料尾）；0050 不加滑價；主判設定其餘同。
 A6 段（登錄 §三）：探索 2017-03-02～2021-12-30｜確認 2022-01-03～資料尾 2026-09-24｜早年 2005 第一個交易日～2014-12-31；
    年化、回落 ＝ rerun17.win_metrics；0050 ＝ 同窗 rerun17.bench_row；判準（使用者）：合格 ＝ 年化 ＞ 0050 且 年化÷|回落| ≥ 0050；另列 ＝ 只贏年化；其餘不合格。
    整件：探索、確認都合格 ⇒ 合格（早年不合格 ⇒ 最多暫定）；兩段都「合格或另列」⇒ 另列；其餘 ⇒ 不合格。
 A7 退化（seq325；登錄 §三）：探索段平均持股 ＜ 3 ⇒ 標退化、不判；⭐ 主判空格放 0050 ⇒「現金 ＞ 30%」一條不適用（seq360 §一）⇒ ⛔ 不用；
    先寫 degeneracy.json（附台北時間）再算任何報酬。平均持股 ＝ 段內逐日收盤持股檔數平均（買進日算、賣出日不算）。
 A8 必報定義（＝ researchDumb Z16 同式）：換手 ＝ 段內買進金額 ÷ 段內平均權益 ÷ 年（年 ＝ 交易日 ÷ 245）；成本／年 ＝ 換手 × 0.585%；
    另報 0050 成本／年 ＝ 段內 0050 進出付的單邊成本合計 ÷ 平均權益 ÷ 年；
    現金比例：bench 臂沒有真現金（＝ 0），另報「0050 占淨值」＝ 1 − 持股市值÷權益、「型態股占淨值」＝ 持股市值÷權益（段內平均）；現金臂 ＝ 1 − 持股市值÷權益；
    平均持有天數 ＝ 賣出日曆位置 − 買進日曆位置（窗尾仍持有不計、另報筆數）；等效獨立檔數 ＝ researchDumb.eff_n；
    每年：訊號數（S06 事件、剔除前，依 T 年）、可買數、筆數（依買進年）、勝率（g − 0.585% ＞ 0）、平均賺賠比（賺筆平均 ÷ |賠筆平均|）；
    出場種類比例（a／b／a＆b 同日／強制／窗尾）；賣出點（只算 a／b 觸發後開盤賣的筆）：賣價 ÷ 賣出根起 60 根有效 K 棒最高收盤 − 1、
    賣後 60 根最高收盤 ＞ 持有期（ke～觸發根）最高收盤的比例；窗不滿 60 根或遇壞根截斷 ⇒ 不計（⚠ 比 researchDumb 程式嚴：它截斷仍計）；
    對使用者措辭照 seq343「真頂訊號（多半在最高點之前）」，⛔ 不稱最高點、頂部。
 A9 隨機對照（登錄 §三 ②）：主判（空格放 0050）實際買進的每一個進場日 e 買了 k 檔 ⇒ 從 T ＝ e−1 的同日母體（500 張閘 ∧ pit_valid ∧ [k−20, k＋1] 無壞根
    ∧ ATR20 可算 ∧ e 可買（有成交、開盤有效、非開盤鎖漲停），⛔ 不看型態）不重複抽 k 檔（default_rng([20261017, 世界, i])，母體依代號排序）；
    ⭐ 出場「同出場規則」：隨機股沒有三角形 ⇒ 出場 a 用「移植下線」——當天第 j 檔隨機股（抽出順序）配當天第 j 筆實際買進（依代號排序）的下線，
       以訊號日收盤為基準的相對位置與相對斜率移植：隨機股第 k_s＋m 根的線 ＝ c_s[k_s] × (la ＋ lb×(k＋m)) ÷ c[k]；
       出場 b ＝ 隨機股自己的 ATR20（T 那根）與自己的最高收盤；壞根、下市、資料尾照 A1；同引擎同參數（空格放 0050、default_rng(1000)）；200 次；
    p ＝ 隨機版 年化÷|回落| ≥ 主判 的比例（另報 年化 ≥ 主判 的比例）；各段各報。
 A10 結果句必附：seq185 原句；「單筆層通過 ≠ 組合會贏 0050」；早年另附「早年含減資假飆股約 0.3%（剩 22 筆未解釋）」＋ 上櫃版面註。
輸出 backtest/resultsAscTri/：degeneracy.json（先寫）、AscTri.json、AscTri_main.csv、rows_{世界}.csv.gz、eq_{世界}.npz、random_{世界}.csv.gz、run.log
"""
from __future__ import annotations

import argparse
import glob
import gzip
import hashlib
import json
import os
import pickle
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D                              # noqa: E402
from backtest import research11 as R                        # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402
from backtest import patterns as P                          # noqa: E402
from backtest import patterns_all as PA                     # noqa: E402
from backtest import universe_gate as UG                    # noqa: E402
from backtest import researchAddOn as RA                    # noqa: E402
from backtest import researchAscTri_freq as AF              # noqa: E402
from backtest import researchDumb as RD                     # noqa: E402
from backtest import researchExit5 as RX5                   # noqa: E402

UG.set_gate_v2(True)

TIME = "2026-10-17 09:55～10:30（台北）"
REG_SHA = "3be823297d0b36d5"
MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
OUT = "backtest/resultsAscTri"
FREQ = "backtest/resultsAscTri/freq"
NRAND = 200
if os.environ.get("ASC_QUICK"):                                  # 煙霧測試（不是交件）
    NRAND, OUT = 3, "/tmp/asc_quick"
COST = R.COST
ETF_RT = 0.001425 * 2 + 0.001
BC = ETF_RT / 2
SLIP = 0.005
NS = 10
SEED_ENG = 1000
RSEED = 20261017
WID = {"主": 0, "早年": 1}
ATR_X = 3.0
DEG_HOLD = 3.0
SEGS = AF.SEGS
ARMS = {"M0050": {"名": "主判：條件出場 a／b、空格放 0050", "x": "M", "bench": True, "slip": False, "rev": False},
        "Mcash": {"名": "描述：空格留現金（seq2 原主規則）", "x": "M", "bench": False, "slip": False, "rev": False},
        "H20": {"名": "描述：固定 20 日（空格放 0050）", "x": "H20", "bench": True, "slip": False, "rev": False},
        "H60": {"名": "描述：固定 60 日（空格放 0050）", "x": "H60", "bench": True, "slip": False, "rev": False},
        "REV": {"名": "描述臂：營收年增 ＞ 0 才買（空格放 0050）", "x": "M", "bench": True, "slip": False, "rev": True},
        "M0050slip": {"名": "描述：主判＋滑價每邊 0.5%", "x": "M", "bench": True, "slip": True, "rev": False}}
SENT = ["裁定 seq185：「任何一格都不可以說照這個型態交易會贏 0050……要不要組合進策略要進組合層另外評估」",
        "單筆層通過 ≠ 組合會贏 0050"]
NOTE_EARLY = ["早年含減資假飆股約 0.3%（剩 22 筆未解釋）",
              "上櫃 2007-07～12 除權息未還原；上櫃減資 2007～2012 為偵測、非官方；2005-01～2007-06 只有上市"]
TRUETOP = "真頂訊號（多半在最高點之前）"
_G: dict = {}


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


def reg_check():
    fs = [f for f in glob.glob(os.path.join(MAILBOX, "*.md")) if f"sha{REG_SHA}" in os.path.basename(f)]
    if len(fs) != 1:
        raise SystemExit(f"⛔ 信箱找不到唯一一封登錄全文 sha{REG_SHA}：{fs}")
    b = open(fs[0], "rb").read()
    h = hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]
    if h != REG_SHA:
        raise SystemExit(f"⛔ 登錄 sha {h} ≠ {REG_SHA}")
    return os.path.basename(fs[0])


# ═════════════ 世界 ═════════════
def load_world(wn, log):
    W = AF.load_world(wn)                                         # ⭐ 頻率表同一支（母體、壞根、早年 reduce_v2）
    cal = W["cal"]; n0 = W["n0"]; D.DATA = W["data"]
    Z = pickle.load(open(os.path.expanduser(f"~/rluwork/world_{AF.WORLDS[wn]['part']}.pkl"), "rb"))
    if list(Z["sids"]) != W["sids"]:
        raise SystemExit("⛔ 快取名單與 load_world 不同")
    W["C"] = np.asarray(Z["c"], float); BAR = np.asarray(Z["bar"], bool)
    SF = {}
    for s, i in W["ix"].items():
        b = np.flatnonzero(BAR[i])
        if len(b) and b[-1] < n0 - 1:
            SF[s] = int(b[-1])
    W["SF"] = SF; W["NP"] = n0 + 1
    bench = np.asarray(RR.load_bench(cal), float)
    if not (np.all(np.isfinite(bench)) and np.all(bench > 0)):
        raise SystemExit(f"⛔ {wn} 0050 序列有缺值（首個有效 {np.flatnonzero(np.isfinite(bench))[:1]}）")
    W["bench"] = bench; W["benchP"] = np.r_[bench, bench[-1]]
    W["names"] = dict(zip(pd.read_csv(os.path.join(W["data"], "meta", "stocks.csv"), dtype=str)["stock_id"],
                          pd.read_csv(os.path.join(W["data"], "meta", "stocks.csv"), dtype=str)["name"]))
    log(f"[世界 {wn}] {cal[0].date()}～{cal[-1].date()}｜股 {len(W['sids'])}｜0050 {bench[0]:.4f}～{bench[-1]:.4f}｜下市／停止交易股 {len(SF)}")
    return W


# ═════════════ 出場 ═════════════
def exit_path(pk, k, mode, A=None, linefn=None, n0=None):
    """訊號根 k（進場根 ke ＝ k＋1）⇒ dict：xpos、px（還原賣價）、fk、trig（觸發根，無 ⇒ -1）、S（賣出根，無 ⇒ -1）。
    mode ＝ "M"（a／b 條件出場，頻率表 Q4 同式）或整數 H（持有 H 根收盤賣）。"""
    idx, c, nxs, bb = pk["idx"], pk["c"], pk["nxs"], pk["badb"]; o = pk["o"]
    nb = len(idx); ke = k + 1
    j_ = int(np.searchsorted(bb, ke + 1)); kb = int(bb[j_]) if j_ < len(bb) else None
    lim = kb if kb is not None else nb
    d = None; typ = ""; S = None
    if mode == "M":
        hmax = -np.inf
        for j in range(ke, lim):
            hmax = max(hmax, c[j])
            ca = bool(c[j] < linefn(j))
            cb_ = bool(c[j] <= hmax - ATR_X * A)
            if ca or cb_:
                d = j; typ = "a＆b同日" if (ca and cb_) else ("a 型態失敗" if ca else "b 回落3ATR"); break
        if d is not None:
            s_ = int(nxs[d + 1]) if d + 1 <= nb else nb
            S = s_ if s_ < lim else None
        if S is not None:
            return {"xpos": int(idx[S]), "px": float(o[S]), "fk": typ, "trig": int(d), "S": int(S), "kb": -1 if kb is None else kb, "skind": "open"}
    else:
        q = D.exit_pos(ke, int(mode))
        if q < lim and q < nb:
            return {"xpos": int(idx[q]), "px": float(c[q]), "fk": f"第{int(mode)}根收盤", "trig": int(q), "S": int(q), "kb": -1 if kb is None else kb, "skind": "close"}
    tg = int(d) if d is not None else -1
    if kb is not None:
        q = kb - 1
        return {"xpos": int(idx[q]) + 1, "px": float(c[q]), "fk": "壞根前收盤強制", "trig": tg, "S": -1, "kb": kb, "skind": "close"}
    if pk["end_ok"]:
        return {"xpos": int(n0), "px": float(c[nb - 1]), "fk": "資料尾仍持有", "trig": tg, "S": -1, "kb": -1, "skind": "end"}
    return {"xpos": int(idx[nb - 1]) + 1, "px": float(c[nb - 1]), "fk": "下市／停止交易（最後收盤）", "trig": tg, "S": -1, "kb": -1, "skind": "close"}


def gross(px, bp):
    return px / bp - 1.0, px * (1 - SLIP) / (bp * (1 + SLIP)) - 1.0


# ═════════════ 逐股 ═════════════
def stock_job(a):
    wn, sid = a
    W = _G[wn]; D.DATA = W["data"]; cal = W["cal"]; n0 = W["n0"]; i = W["ix"][sid]
    B = R.load_bars(sid, W["mk"].get(sid, "twse"), cal)
    if B is None:
        return sid, None
    df = B["df"]; idx = B["idx"].astype(np.int64); nb = len(idx)
    o, h, l, c = (np.asarray(B[k], float) for k in ("o", "h", "l", "c"))
    cf = df["close"].to_numpy(float)
    bars = np.flatnonzero(np.isfinite(cf))
    if not (len(bars) == nb and (bars == idx).all()):
        raise SystemExit(f"⛔ {wn} {sid}：偵測有效 K 棒 ≠ load_bars 有效 K 棒（A0）")
    hd, ld, cd = df["high"].to_numpy(float)[bars], df["low"].to_numpy(float)[bars], cf[bars]
    r60 = PA._rN(cd, PA.R60)
    ref = AF._dedup(PA.detect_lines(hd, ld, cd, r60)[AF.VID])
    rep = AF._lines_replica(hd, ld, cd, r60)
    rep_d = AF._dedup([(e[0], e[1]) for e in rep])
    if [(int(x), int(y)) for x, y in ref] != [(int(x), int(y)) for x, y in rep_d]:
        raise SystemExit(f"⛔ {wn} {sid}：replica S06 ≠ PA.detect_lines")
    line_of = {}
    for e in rep:
        if e[0] not in line_of:
            line_of[e[0]] = e
    f = P.Frame(df, set())
    gate_b = np.asarray(f.gate, bool)[idx]
    bad = np.asarray(B["next_bad"][:nb] == np.arange(nb), bool)
    for p in W["BADPOS"].get(sid, ()):
        k = int(np.searchsorted(idx, p, "left"))
        if k < nb:
            bad[k] = True
    CB = np.r_[0, np.cumsum(bad)]

    def nbad(a_, b_):
        a_ = max(a_, 0); b_ = min(b_, nb - 1)
        return int(CB[b_ + 1] - CB[a_]) if b_ >= a_ else 0
    tr = np.full(nb, np.nan); tr[1:] = np.maximum(h[1:], c[:-1]) - np.minimum(l[1:], c[:-1])
    atr = pd.Series(tr).rolling(20, min_periods=20).mean().to_numpy()
    pv_b = W["PV"][i, idx]
    TRD = W["TRD"][i]; O = W["O"][i]; UPL = W["UPL"][i]; DNL = W["DNL"][i]
    sell_ok = TRD[idx] & np.isfinite(O[idx]) & (O[idx] > 0) & ~DNL[idx]
    nxs = np.full(nb + 1, nb, np.int64)
    for k in range(nb - 1, -1, -1):
        nxs[k] = k if sell_ok[k] else nxs[k + 1]
    pk = {"idx": idx, "o": o, "c": c, "atr": atr, "badb": np.flatnonzero(bad), "nxs": nxs, "end_ok": bool(idx[-1] == n0 - 1)}
    # ── 隨機對照母體（A9）：每根 k 是否可當隨機股
    K = np.arange(nb)
    CBk = CB
    win_ok = (K >= 20) & (K + 1 < nb)
    lo = np.maximum(K - 20, 0); hi = np.minimum(K + 1, nb - 1)
    win_ok &= (CBk[hi + 1] - CBk[lo]) == 0
    e_ = idx + 1
    nxt = np.zeros(nb, bool); nxt[:-1] = idx[1:] == e_[:-1]
    ec = np.minimum(e_, n0 - 1)
    buy_ok = nxt & (e_ < n0) & TRD[ec] & np.isfinite(O[ec]) & (O[ec] > 0) & ~UPL[ec]
    with np.errstate(invalid="ignore"):
        pool = gate_b & pv_b & win_ok & np.isfinite(atr) & (atr > 0) & buy_ok
    pk["pool"] = np.flatnonzero(pool)
    # ── 價格閘：快取 vs load_bars
    cc = W["C"][i, idx]; oo = O[idx]
    okc = np.isfinite(cc) & np.isfinite(c); oko = np.isfinite(oo) & np.isfinite(o)
    gd = {"收盤差": float(np.max(np.abs(cc[okc] / c[okc] - 1.0))) if okc.any() else 0.0,
          "開盤差": float(np.max(np.abs(oo[oko] / o[oko] - 1.0))) if oko.any() else 0.0}
    rows = []
    for (Tb, fb) in ref:
        k, kf = int(Tb), int(fb)
        pos = int(idx[k]); e = pos + 1
        rec = {"sid": sid, "T": pos, "first": int(idx[kf]), "k": k, "why": ""}
        if not (gate_b[k] and pv_b[k]):
            rec["why"] = AF.REASONS[0]
        elif nbad(min(kf, k - 20), k + 1) > 0:
            rec["why"] = AF.REASONS[1]
        elif k < 20 or not np.isfinite(atr[k]) or not atr[k] > 0:
            rec["why"] = AF.REASONS[2]
        elif not (k + 1 < nb and idx[k + 1] == e and e < n0 and TRD[e] and np.isfinite(O[e]) and O[e] > 0):
            rec["why"] = AF.REASONS[3]
        elif UPL[e]:
            rec["why"] = AF.REASONS[4]
        if rec["why"]:
            rows.append(rec); continue
        A = float(atr[k]); la, lb = float(line_of[Tb][2]), float(line_of[Tb][3])
        bp = float(o[k + 1])
        rec.update({"entry_pos": e, "bp": bp, "atr": A, "la": la, "lb": lb, "ck": float(c[k])})
        xm = exit_path(pk, k, "M", A, lambda j, la=la, lb=lb: la + lb * j, n0)
        g, gs = gross(xm["px"], bp)
        rec.update({"xpos_M": xm["xpos"], "px_M": xm["px"], "g_M": g, "gs_M": gs, "fk_M": xm["fk"], "trig_M": xm["trig"], "S_M": xm["S"],
                    "kb": xm["kb"], "skind_M": xm["skind"]})
        for H in (20, 60):
            xh = exit_path(pk, k, H, n0=n0)
            g, _ = gross(xh["px"], bp)
            rec.update({f"xpos_H{H}": xh["xpos"], f"px_H{H}": xh["px"], f"g_H{H}": g, f"fk_H{H}": xh["fk"], f"skind_H{H}": xh["skind"]})
        rows.append(rec)
    return sid, {"pk": pk, "rows": rows, "gate": gd}


# ═════════════ 營收（A4） ═════════════
def rev_flags(W, rows, log):
    rev, rly, info = RX5.load_revenue(W["data"])
    AV = RX5.avail_pos(list(rev.index), W["cal"])
    per = list(rev.index); avp = np.array([AV[p] for p in per], int)
    if not (np.diff(avp) >= 0).all():
        raise SystemExit("⛔ 營收可得日不是單調")
    RV = rev.to_numpy(float); RL = rly.to_numpy(float); col = {s: j for j, s in enumerate(rev.columns)}
    n_ok = n_pos = n_na = 0
    for r in rows:
        if r["why"]:
            continue
        j = col.get(r["sid"], -1); r["rev_per"] = ""; r["rev_yoy"] = np.nan; r["rev_ok"] = False
        if j >= 0:
            m = int(np.searchsorted(avp, r["T"], side="right"))           # 可得日 ≤ T 的期別：per[:m]
            vv = np.flatnonzero(np.isfinite(RV[:m, j]))
            if len(vv):
                q = int(vv[-1]); r["rev_per"] = per[q]
                if np.isfinite(RL[q, j]) and RL[q, j] > 0:
                    r["rev_yoy"] = float(RV[q, j] / RL[q, j] - 1.0)
        if np.isfinite(r["rev_yoy"]):
            n_ok += 1; r["rev_ok"] = bool(r["rev_yoy"] > 0); n_pos += int(r["rev_ok"])
        else:
            n_na += 1
    out = {"營收檔": info, "可買訊號": n_ok + n_na, "年增可判": n_ok, "年增>0": n_pos, "不可判（不買）": n_na}
    log(f"[營收 {W['name']}] {out}")
    return out


# ═════════════ 引擎 ═════════════
def run_eng(W, rows, arm, opens_cache=None):
    cfg = ARMS[arm]; x = cfg["x"]
    rows = [r for r in rows if (not cfg["rev"] or r.get("rev_ok"))]
    if not rows:
        return None
    rows = sorted(rows, key=lambda r: (r["entry_pos"], r["sid"]))
    gk = "gs_M" if cfg["slip"] else f"g_{x}"
    sig = pd.DataFrame({"sid": [r["sid"] for r in rows], "entry_pos": [r["entry_pos"] for r in rows],
                        "xpos_D": [r[f"xpos_{x}"] for r in rows], "g_D": [r[gk] for r in rows]})
    closes = {}; opens = {}; SFk = {}
    for s in set(sig["sid"]):
        i = W["ix"][s]; c = W["C"][i]; closes[s] = np.r_[c, c[-1]]
        op = np.r_[W["O"][i], np.nan]; opens[s] = op * (1 + SLIP) if cfg["slip"] else op
        if s in W["SF"]:
            SFk[s] = W["SF"][s]
    au = []
    kw = dict(cash_mode="bench", bench=W["benchP"], bench_cost=BC) if cfg["bench"] else {}
    o = R.simulate_mtm(sig, "D", NS, np.random.default_rng(SEED_ENG), closes, opens, W["NP"], return_equity=True,
                       stop_force=SFk, audit=au, **kw)
    eq = np.asarray(o["equity"], float).copy(); hv = np.asarray(o["hold_val"], float).copy()
    first, end = int(o["first"]), int(o["end"]); ext = {"前": 0, "後": 0}
    if cfg["bench"]:
        bP = W["benchP"]
        if end < W["NP"]:
            eq[end:] = eq[end - 1] * bP[end:] / bP[end - 1]; ext["後"] = W["NP"] - end
        if first > 1:
            eq[:first - 1] = bP[:first - 1] / bP[first - 1]; ext["前"] = first - 1
    hv[:first] = 0.0; hv[end:] = 0.0
    info = {(r["sid"], r["entry_pos"]): r for r in rows}
    return {"eq": eq, "hv": hv, "first": first, "end": end, "ext": ext, "trades": int(o["trades"]), "sf_n": int(o.get("x_stop_force_n", 0)),
            "audit": au, "info": info, "arm": arm}


def eng_job(a):
    wn, arm = a
    return wn, arm, run_eng(_G[wn], _G["ROWS"][wn], arm)


def trades_of(E):
    buys = {}; out = []
    for x in E["audit"]:
        if x["side"] == "buy":
            buys[x["sid"]] = (int(x["t"]), float(x["amt"]))
        else:
            tb, amt = buys.pop(x["sid"])
            out.append({"sid": x["sid"], "tb": tb, "amt": amt, "ts": int(x["t"]), "proc": float(x["amt"]) - float(x["cost"]),
                        "r": E["info"][(x["sid"], tb)]})
    for s, (tb, amt) in buys.items():
        out.append({"sid": s, "tb": tb, "amt": amt, "ts": None, "proc": np.nan, "r": E["info"][(s, tb)]})
    out.sort(key=lambda z: (z["tb"], z["sid"]))
    return out


def pre_stats(W, E):
    """⛔ 不含任何報酬：持股數、型態股占淨值、換手、持有天數。"""
    eq, hv = E["eq"], E["hv"]; n = len(eq)
    TR = trades_of(E)
    cnt = np.zeros(n + 1)
    for z in TR:
        cnt[z["tb"]] += 1; cnt[min(z["ts"] if z["ts"] is not None else n, n)] -= 1
    hold = np.cumsum(cnt)[:n]
    bench = ARMS[E["arm"]]["bench"]
    out = {}
    for sg, (x, y) in W["segp"].items():
        yrs = (y - x + 1) / 245.0
        bs = [z for z in TR if x <= z["tb"] <= y]
        ss = [z for z in TR if z["ts"] is not None and x <= z["ts"] <= y]
        hd = [z["ts"] - z["tb"] for z in bs if z["ts"] is not None]
        pat = float(np.mean(hv[x:y + 1] / eq[x:y + 1]))
        meq = float(np.mean(eq[x:y + 1]))
        d = {"平均持股": float(np.mean(hold[x:y + 1])), "型態股占淨值": pat,
             "0050占淨值": (1.0 - pat) if bench else 0.0, "真現金比例": 0.0 if bench else 1.0 - pat,
             "買進筆": len(bs), "買進每年": len(bs) / yrs, "換手每年": float(sum(z["amt"] for z in bs) / meq / yrs),
             "平均持有天數": float(np.mean(hd)) if hd else float("nan"), "持有天數中位": float(np.median(hd)) if hd else float("nan"),
             "窗尾仍持有筆": int(sum(z["ts"] is None or z["r"][f"fk_{ARMS[E['arm']]['x']}"] == "資料尾仍持有" for z in bs))}
        d["成本每年"] = d["換手每年"] * COST
        if bench:
            c50 = sum(z["amt"] / (1 - BC) * BC for z in bs) + sum(z["proc"] * BC for z in ss)
            d["0050成本每年"] = float(c50 / meq / yrs)
        else:
            d["0050成本每年"] = 0.0
        out[sg] = d
    return out, TR, hold


def label(c, m, b):
    if not (np.isfinite(c) and np.isfinite(m)) or m == 0:
        return "—"
    return "合格" if (c > b["cagr"] and c / abs(m) >= b["cagr"] / abs(b["mdd"])) else ("另列" if c > b["cagr"] else "不合格")


def ratio(c, m):
    return float(c / abs(m)) if (np.isfinite(c) and np.isfinite(m) and m < 0) else float("nan")


def seg_metrics(E, x, y):
    c, m, _ = RR.win_metrics(E["eq"], E["first"], E["end"], x, y)
    return float(c), float(m)


def post60(pk, S, d, ke, px):
    idx, c = pk["idx"], pk["c"]; nb = len(idx)
    if S < 0 or S + 59 > nb - 1:
        return np.nan, np.nan
    bb = pk["badb"]; j_ = int(np.searchsorted(bb, S + 1))
    if j_ < len(bb) and bb[j_] <= S + 59:
        return np.nan, np.nan
    mx = float(np.max(c[S:S + 60])); hold_mx = float(np.max(c[ke:d + 1]))
    return px / mx - 1.0, float(mx > hold_mx)


# ═════════════ 主程式 ═════════════
def run(a, log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    if abs(COST - 0.00585) > 1e-15:
        raise SystemExit(f"⛔ R.COST {COST} ≠ 0.585%")
    regf = reg_check(); log(f"[登錄] sha {REG_SHA} ✓ {regf}")
    S = {"讀法寫死": TIME, "登錄": f"PREREG上升三角組合層 seq3 sha {REG_SHA}（定版；裁定 seq358 N_組合 ＋1、seq360 §一 主判空格放 0050、seq361）",
         "登錄檔": regf, "結果句必附": SENT, "早年標註": NOTE_EARLY, "臂": {k: v["名"] for k, v in ARMS.items()},
         "成本": {"個股來回": COST, "0050來回": ETF_RT, "引擎0050單邊(對稱)": BC, "滑價每邊(描述)": SLIP}, "閘": {}}
    WS = {}; PKS = {}; ROWS = {}
    for wn in ("主", "早年"):
        W = load_world(wn, log); WS[wn] = W; _G[wn] = W
        t0 = time.time(); res = {}
        sids = W["sids"][::10] if os.environ.get("ASC_QUICK") else W["sids"]
        with Pool(a.procs) as pool:
            for j, (s, r) in enumerate(pool.imap_unordered(stock_job, [(wn, s) for s in sids], chunksize=8)):
                res[s] = r
                if j % 400 == 0:
                    log(f"[逐股 {wn}] {j}/{len(sids)}｜{time.time() - t0:.0f}s")
        PKS[wn] = {s: v["pk"] for s, v in res.items() if v is not None}
        ROWS[wn] = sorted([x for v in res.values() if v is not None for x in v["rows"]], key=lambda r: (r["T"], r["sid"]))
        g = {"load_bars 不足260根檔數": sum(v is None for v in res.values()),
             "快取收盤 vs load_bars 最大相對差": max(v["gate"]["收盤差"] for v in res.values() if v),
             "快取開盤 vs load_bars 最大相對差": max(v["gate"]["開盤差"] for v in res.values() if v),
             "S06 事件": len(ROWS[wn]), "可買": sum(1 for r in ROWS[wn] if not r["why"]),
             "load_world 閘": W["gate"], "壞根": W["bad_info"]}
        if g["快取收盤 vs load_bars 最大相對差"] > 1e-9 or g["快取開盤 vs load_bars 最大相對差"] > 1e-9:
            raise SystemExit(f"⛔ {wn} 價格閘不過 {g}")
        # ── A0：與已提交頻率表逐筆比對
        if not os.environ.get("ASC_QUICK"):
            fq = pd.read_csv(os.path.join(FREQ, f"signals_{wn}.csv.gz"), dtype=str, keep_default_na=False)
            cal = W["cal"]; n0 = W["n0"]
            mine = [(r["sid"], str(cal[r["T"]].date()), str(cal[r["first"]].date()), r["why"],
                     str(cal[r["entry_pos"]].date()) if not r["why"] else "",
                     ((str(cal[r["xpos_M"]].date()) if r["xpos_M"] < n0 else "窗尾") if not r["why"] else ""),
                     r.get("fk_M", "")) for r in ROWS[wn]]
            theirs = list(zip(fq["sid"], fq["T"], fq["first"], fq["剔除"], fq["買進日"], fq["賣出日"], fq["出場"]))
            nd = sum(1 for x_, y_ in zip(sorted(mine), sorted(theirs)) if x_ != y_) + abs(len(mine) - len(theirs))
            g["與頻率表 signals 逐筆比對（剔除、買進日、賣出日、出場）"] = {"本支": len(mine), "頻率表": len(theirs), "不同": nd}
            if nd:
                ex = [(x_, y_) for x_, y_ in zip(sorted(mine), sorted(theirs)) if x_ != y_][:5]
                raise SystemExit(f"⛔ {wn} 與頻率表不同 {nd} 筆：{ex}")
            W["freq_buy"] = {(s, d) for s, d, b in zip(fq["sid"], fq["買進日"], fq["實際買進"]) if b == "True"}
        S["閘"][wn] = g
        log(f"[逐股 {wn}] {len(PKS[wn])} 檔｜{g}｜{time.time() - t0:.0f}s")
        S["閘"][wn]["營收"] = rev_flags(W, ROWS[wn], log)
    _G["ROWS"] = {wn: [r for r in ROWS[wn] if not r["why"]] for wn in WS}
    _G["PK"] = PKS
    # ── 引擎 ──
    jobs = [(wn, arm) for wn in WS for arm in ARMS]
    with Pool(min(a.procs, len(jobs))) as pool:
        RES = pool.map(eng_job, jobs, chunksize=1)
    ENG = {(wn, arm): E for wn, arm, E in RES}
    for (wn, arm), E in ENG.items():
        S["閘"][wn][f"{arm} 引擎"] = {"買進筆": E["trades"], "stop_force 觸發": E["sf_n"], "first": str(WS[wn]["cal"][min(E["first"], WS[wn]["n0"] - 1)].date()),
                                     "end": E["end"], "bench 延伸天數": E["ext"]}
        if E["sf_n"]:
            raise SystemExit(f"⛔ stop_force 應 0：{wn} {arm}")
    for wn, W in WS.items():
        if "freq_buy" in W:
            cal = W["cal"]; TRm = trades_of(ENG[(wn, "M0050")])
            mine = {(z["sid"], str(cal[z["tb"]].date())) for z in TRm}
            S["閘"][wn]["主判實際買進 vs 頻率表槽模擬"] = {"引擎": len(mine), "頻率表": len(W["freq_buy"]), "只在引擎": len(mine - W["freq_buy"]),
                                                "只在頻率表": len(W["freq_buy"] - mine)}
            log(f"[對頻率表 {wn}] {S['閘'][wn]['主判實際買進 vs 頻率表槽模擬']}")
    # ── 退化（先寫，⛔ 未算報酬）──
    PRE_ = {}
    DEG = {"寫入時間（台北）": None, "規則": "seq325：探索段平均持股 ＜ 3 ⇒ 退化、不判；⭐ 主判空格放 0050 ⇒「現金 ＞ 30%」一條不適用（seq360 §一、登錄 §三）",
           "格": {}}
    for (wn, arm), E in ENG.items():
        ps, TR, hold = pre_stats(WS[wn], E); PRE_[(wn, arm)] = (ps, TR, hold)
        for sg, v in ps.items():
            DEG["格"][f"{wn}|{arm}|{sg}"] = {"平均持股": v["平均持股"], "型態股占淨值": v["型態股占淨值"], "買進筆": v["買進筆"],
                                            "退化（只看平均持股）": bool(v["平均持股"] < DEG_HOLD)}
    DEG["主判探索段退化"] = DEG["格"]["主|M0050|探索"]["退化（只看平均持股）"]
    DEG["寫入時間（台北）"] = now_tpe()
    json.dump(DEG, open(os.path.join(OUT, "degeneracy.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[退化] 已寫 degeneracy.json（{DEG['寫入時間（台北）']}）｜主判探索 {DEG['格']['主|M0050|探索']}")
    S["退化"] = DEG
    # ── 報酬 ──
    TAB = []
    for (wn, arm), E in ENG.items():
        W = WS[wn]; ps, TR, hold = PRE_[(wn, arm)]
        for sg, (x, y) in W["segp"].items():
            c_, m_ = seg_metrics(E, x, y); b = RR.bench_row(W["cal"], W["bench"], x, y + 1)
            row = {"世界": wn, "臂": arm, "臂名": ARMS[arm]["名"], "段": sg, "窗": f"{W['cal'][x].date()}～{W['cal'][y].date()}",
                   "年化": c_, "回落": m_, "比值": ratio(c_, m_), "0050年化": b["cagr"], "0050回落": b["mdd"], "0050比值": ratio(b["cagr"], b["mdd"]),
                   "標籤": label(c_, m_, b), **ps[sg]}
            if arm in ("M0050", "Mcash"):
                days = sorted({z["tb"] for z in TR if x <= z["tb"] <= y})
                en = RD.eff_n(W, [{"r": {"sid": z["sid"]}, "tb": z["tb"], "ts": z["ts"]} for z in TR], days)
                row["等效獨立檔數"] = float(np.nanmean([z[3] for z in en])) if en else np.nan
                row["平均ρ"] = float(np.nanmean([z[2] for z in en])) if en else np.nan
            TAB.append(row)
    TB = pd.DataFrame(TAB)
    S["主表"] = TAB
    TB.to_csv(os.path.join(OUT, "AscTri_main.csv"), index=False, float_format="%.6g", encoding="utf-8-sig")
    for wn in WS:
        np.savez_compressed(os.path.join(OUT, f"eq_{wn}.npz"), **{arm: ENG[(wn, arm)]["eq"] for arm in ARMS}, bench=WS[wn]["benchP"])
        R_ = pd.DataFrame(ROWS[wn])
        R_.insert(1, "T日", [str(WS[wn]["cal"][t].date()) for t in R_["T"]])
        with gzip.open(os.path.join(OUT, f"rows_{wn}.csv.gz"), "wt", encoding="utf-8") as fh:
            R_.to_csv(fh, index=False, float_format="%.17g")
    log("[主表]\n" + TB[["世界", "臂", "段", "年化", "回落", "比值", "0050年化", "0050回落", "0050比值", "標籤", "平均持股", "型態股占淨值", "買進筆"]].to_string())

    def lab(wn, arm, sg):
        return TB[(TB["世界"] == wn) & (TB["臂"] == arm) & (TB["段"] == sg)].iloc[0]["標籤"]

    def verdict(arm):
        le, lc, lo = lab("主", arm, "探索"), lab("主", arm, "確認"), lab("早年", arm, "早年")
        if le == "合格" and lc == "合格":
            v = "暫定（早年不合格 ⇒ 最多暫定）" if lo == "不合格" else "合格"
        elif le in ("合格", "另列") and lc in ("合格", "另列"):
            v = "另列" + ("（早年不合格）" if lo == "不合格" else "")
        else:
            v = "不合格"
        return {"探索": le, "確認": lc, "早年": lo, "整件": v}
    S["判語"] = {"主判 M0050": verdict("M0050")}
    for arm in ARMS:
        if arm != "M0050":
            S["判語"][f"{arm}（描述、⛔ 不判）"] = verdict(arm)
    if DEG["主判探索段退化"]:
        S["判語"]["主判 M0050"]["整件"] = "退化、照 seq325 不判（標籤照報：" + S["判語"]["主判 M0050"]["整件"] + "）"
    log(f"[判語] {S['判語']}")
    S["必報"] = must(WS, PKS, ENG, PRE_, ROWS, log)
    S["隨機進場"] = random_arm(WS, PKS, ENG, TB, a, log)
    # ── 先驗 ──
    mm = S["必報"]
    bsh = {}
    for wn, sgs in (("主", ("探索", "確認")), ("早年", ("早年",))):
        fk = {}
        for sg in sgs:
            for k_, v_ in mm[f"{wn}|M0050"]["各段"][sg]["出場種類"].items():
                fk[k_] = fk.get(k_, 0) + v_
        n_ = sum(fk.values())
        bsh[wn] = {"出場種類": fk, "b 單獨比例": fk.get("b 回落3ATR", 0) / n_ if n_ else np.nan,
                   "b 含 a＆b 同日比例": (fk.get("b 回落3ATR", 0) + fk.get("a＆b同日", 0)) / n_ if n_ else np.nan}
    S["先驗對照"] = {
        "① 探索段因訊號太少標退化（約五成）": {"探索段平均持股": DEG["格"]["主|M0050|探索"]["平均持股"], "成立": DEG["主判探索段退化"]},
        "② 不退化的話，確認段不合格（約七成）": {"確認段標籤": lab("主", "M0050", "確認"), "成立": (not DEG["主判探索段退化"]) and lab("主", "M0050", "確認") == "不合格"},
        "③ 出場 b 占出場七成以上（約六成）": {**bsh, "成立（主世界、b 單獨）": bool(bsh["主"]["b 單獨比例"] >= 0.7),
                                      "成立（主世界、b 含同日）": bool(bsh["主"]["b 含 a＆b 同日比例"] >= 0.7)}}
    log(f"[先驗] {json.dumps(S['先驗對照'], ensure_ascii=False, default=str)}")
    S["耗時秒"] = round(time.time() - T0); S["完成時間（台北）"] = now_tpe()
    S["讀法"] = __doc__.split("═══ 讀法")[1]
    json.dump(S, open(os.path.join(OUT, "AscTri.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] {S['耗時秒']}s")


def must(WS, PKS, ENG, PRE_, ROWS, log):
    out = {}
    for wn, W in WS.items():
        cal = W["cal"]
        sig_y = {}
        for r in ROWS[wn]:
            y = int(cal[r["T"]].year); sig_y.setdefault(y, [0, 0]); sig_y[y][0] += 1; sig_y[y][1] += int(not r["why"])
        for arm in ARMS:
            ps, TR, hold = PRE_[(wn, arm)]; x_ = ARMS[arm]["x"]
            gk = "gs_M" if ARMS[arm]["slip"] else f"g_{x_}"
            yrs = {}
            for z in TR:
                yrs.setdefault(int(cal[z["tb"]].year), []).append(z["r"][gk] - COST)
            peryr = {}
            for y in sorted(set(sig_y) | set(yrs)):
                v = np.array(yrs.get(y, []), float); w_ = v[v > 0]; l_ = v[v <= 0]
                peryr[y] = {"訊號": sig_y.get(y, [0, 0])[0], "可買": sig_y.get(y, [0, 0])[1], "筆數": int(len(v)),
                            "勝率": float((v > 0).mean()) if len(v) else np.nan,
                            "平均賺賠比": float(w_.mean() / abs(l_.mean())) if (len(w_) and len(l_) and l_.mean() != 0) else np.nan,
                            "平均淨報酬": float(v.mean()) if len(v) else np.nan}
            seg = {}
            for sg, (x, y) in W["segp"].items():
                rz = [z["r"] for z in TR if x <= z["tb"] <= y]; nn = len(rz)
                v = np.array([r[gk] - COST for r in rz], float); w_ = v[v > 0]; l_ = v[v <= 0]
                fk = pd.Series([r[f"fk_{x_}"] for r in rz]).value_counts().to_dict() if nn else {}
                d = {"筆數": nn, "勝率": float((v > 0).mean()) if nn else np.nan,
                     "平均賺賠比": float(w_.mean() / abs(l_.mean())) if (len(w_) and len(l_) and l_.mean() != 0) else np.nan,
                     "平均淨報酬": float(v.mean()) if nn else np.nan, "出場種類": {k: int(v_) for k, v_ in fk.items()},
                     "出場種類比例": {k: v_ / nn for k, v_ in fk.items()} if nn else {}}
                if x_ == "M":
                    dist = []; nh = []
                    for r in rz:
                        if r["S_M"] < 0:
                            continue
                        a_, b_ = post60(PKS[wn][r["sid"]], r["S_M"], r["trig_M"], r["k"] + 1, r["px_M"])
                        if np.isfinite(a_):
                            dist.append(a_); nh.append(b_)
                    d["賣出點：賣價距賣後60根最高收盤（中位）"] = float(np.median(dist)) if dist else np.nan
                    d["賣出點：p25／p75"] = [float(np.quantile(dist, .25)), float(np.quantile(dist, .75))] if dist else []
                    d["賣後60根又創新高比例"] = float(np.mean(nh)) if nh else np.nan
                    d["賣出點可算筆數"] = len(dist)
                    d["措辭"] = f"a／b 賣出屬「{TRUETOP}」式描述；⛔ 不稱最高點"
                seg[sg] = d
            out[f"{wn}|{arm}"] = {"逐年": peryr, "各段": seg, "全部筆數": len(TR)}
        log(f"[必報 {wn}] M0050 " + json.dumps(out[f'{wn}|M0050']['各段'], ensure_ascii=False, default=str)[:1200])
    return out


# ═════════════ 隨機對照（A9） ═════════════
def rand_rows_job(a):
    wn, sid, reqs = a
    W = _G[wn]; pk = _G["PK"][wn][sid]; n0 = W["n0"]; O = W["O"][W["ix"][sid]]
    res = {}
    for kk, (la, lb, k0, ck) in reqs:
        cs = float(pk["c"][kk]); A = float(pk["atr"][kk])
        fn = (lambda j, la=la, lb=lb, k0=k0, ck=ck, cs=cs, kk=kk: cs * (la + lb * (k0 + (j - kk))) / ck)
        x = exit_path(pk, kk, "M", A, fn, n0)
        e = int(pk["idx"][kk]) + 1; bp = float(pk["o"][kk + 1])
        if abs(bp / O[e] - 1) > 1e-9:
            raise SystemExit(f"⛔ 隨機股開盤不一致 {sid}")
        g, _ = gross(x["px"], bp)
        res[(kk, la, lb, k0, ck)] = {"sid": sid, "entry_pos": e, "xpos_M": x["xpos"], "g_M": g, "fk_M": x["fk"]}
    return sid, res


def rand_job(a):
    wn, i = a
    W = _G[wn]; RB = _G["RANDROWS"][wn]; DAYS = _G["RDAYS"][wn]; POOL = _G["RPOOL"][wn]; SPEC = _G["RSPEC"][wn]
    rng = np.random.default_rng([RSEED, WID[wn], i])
    rows = []
    for e, k in DAYS:
        pool = POOL.get(e - 1, [])
        if not pool:
            continue
        pick = rng.choice(len(pool), size=min(k, len(pool)), replace=False)
        for jj, j in enumerate(pick):
            s, kk = pool[j]; sp = SPEC[e][jj]
            rows.append(RB[s][(kk, *sp)])
    E = run_eng(W, rows, "M0050")
    row = {"世界": wn, "i": i, "列": len(rows), "買進筆": E["trades"] if E else 0}
    for sg, (x, y) in W["segp"].items():
        c_, m_ = seg_metrics(E, x, y) if E else (np.nan, np.nan)
        row[f"{sg}_年化"] = c_; row[f"{sg}_回落"] = m_
    return row


def random_arm(WS, PKS, ENG, TB, a, log):
    _G["RANDROWS"] = {}; _G["RDAYS"] = {}; _G["RPOOL"] = {}; _G["RSPEC"] = {}
    out = {}
    for wn, W in WS.items():
        E = ENG[(wn, "M0050")]
        byday = {}
        for x in E["audit"]:
            if x["side"] == "buy":
                byday.setdefault(int(x["t"]), []).append(x["sid"])
        DAYS = sorted((t, len(v)) for t, v in byday.items())
        SPEC = {}
        for t, v in byday.items():
            SPEC[t] = []
            for s in sorted(v):
                r = E["info"][(s, t)]
                SPEC[t].append((r["la"], r["lb"], r["k"], r["ck"]))
        need = {e - 1 for e, _ in DAYS}
        POOL = {}
        for s in sorted(PKS[wn]):
            pk = PKS[wn][s]
            for k in pk["pool"]:
                t = int(pk["idx"][k])
                if t in need:
                    POOL.setdefault(t, []).append((s, int(k)))
        for t in POOL:
            POOL[t].sort()
        req = {}
        for i in range(NRAND):
            rng = np.random.default_rng([RSEED, WID[wn], i])
            for e, k in DAYS:
                pool = POOL.get(e - 1, [])
                if not pool:
                    continue
                for jj, j in enumerate(rng.choice(len(pool), size=min(k, len(pool)), replace=False)):
                    s, kk = pool[j]; req.setdefault(s, set()).add((kk, *SPEC[e][jj]))
        RB = {}; _G["RANDROWS"][wn] = RB
        _G["RDAYS"][wn] = DAYS; _G["RPOOL"][wn] = POOL; _G["RSPEC"][wn] = SPEC
        jobs = [(wn, s, sorted(((z[0], z[1:]) for z in v), key=lambda q: (q[0], q[1]))) for s, v in sorted(req.items())]
        with Pool(a.procs) as pool:
            for s, res in pool.imap_unordered(rand_rows_job, jobs, chunksize=8):
                RB[s] = res
        log(f"[隨機 {wn}] 進場日 {len(DAYS)}｜主判買進 {sum(k for _, k in DAYS)}｜母體日中位 {np.median([len(v) for v in POOL.values()]):.0f}｜"
            f"母體空日 {sum(1 for e, _ in DAYS if not POOL.get(e - 1))}｜需算列 {sum(len(v) for v in req.values())}")
        with Pool(a.procs) as pool:
            RES = pool.map(rand_job, [(wn, i) for i in range(NRAND)], chunksize=4)
        RDF = pd.DataFrame(RES)
        RDF.to_csv(os.path.join(OUT, f"random_{wn}.csv.gz"), index=False, float_format="%.10g")
        o = {}
        for sg in W["segp"]:
            z = TB[(TB["世界"] == wn) & (TB["臂"] == "M0050") & (TB["段"] == sg)].iloc[0]
            rr = RDF[f"{sg}_年化"] / RDF[f"{sg}_回落"].abs()
            o[sg] = {"主判 年化": float(z["年化"]), "主判 比值": float(z["比值"]), "隨機 年化中位": float(RDF[f"{sg}_年化"].median()),
                     "隨機 回落中位": float(RDF[f"{sg}_回落"].median()), "隨機 比值中位": float(rr.median()),
                     "p（隨機比值 ≥ 主判）": float((rr >= z["比值"]).mean()), "p（隨機年化 ≥ 主判）": float((RDF[f"{sg}_年化"] >= z["年化"]).mean()),
                     "隨機 買進筆中位": float(RDF["買進筆"].median()), "次數": int(len(RDF))}
        out[wn] = o
        log(f"[隨機 {wn}] {o}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=2)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    log = RA.log_to(os.path.join(OUT, "run.log"))
    run(a, log)


if __name__ == "__main__":
    main()
