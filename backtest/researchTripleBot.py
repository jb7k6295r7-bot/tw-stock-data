# -*- coding: utf-8 -*-
"""PREREG三重底 seq1【事件層正式跑】（台股策略線 單筆層登錄 sha 806f2cd9554b213d，2026-10-20 18:47；裁定 seq394 第 1 題、seq398 發號
（主形狀沿用型態全量 S2 ⇒ 屬事後重切、標籤最多暫定）、seq399 核准開跑；N_前段 ＋1）——回測線計算子代理。
⛔ 不 commit、不改既有程式與結果夾（resultsTripleBot/freq/ ⛔ 不碰）；researchTripleBot_freq（事件偵測、剔除）、researchWR_freq（世界、base、段）、
   researchKDJ3（共用小工具：stock_arrays、cell_stats、desc_ci、clkey、trade_stats、freq_text、check_events、fixture_common）、
   researchPatC（decile_int、dec_matrix、excl_past、verdict、agg_eval、diff_stats）、researchAscTri_freq（load_world）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTripleBot [--procs 2] [--dry [--limit N]]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTripleBot_check
    --dry ＝ 不含報酬的乾跑（R 一律寫 0）；--limit 只准與 --dry 同用
輸出 backtest/resultsTripleBot/（⛔ 不碰 freq/）：TripleBot.json、TripleBot_main.csv（判定表＋分報＋描述格）、TripleBot_diff.csv（J−M、量縮兩組差）、
    by_year.csv、fake_reps.csv、fake_acc.npz、events/trades_<世界>_<段>_<格>_H<H>.csv.gz、run.log

格（頻率表同名）：J ＝ 判定格（S2 ∧ 放量 vr20≥1.5 收紅 ∧ 距 250 日高 ≤ −20%；H20 判，H60、H120 描述）；描述（⛔ 不判、不計 N）：
    M（主錨 ＝ S2 重跑）、較嚴 J_放量2倍／3倍／前5日均量／跌30%／跌40%／120日線下>3月、單條 M+放量／M+長期下跌、量縮兩組（J、M 各有／沒）。

═══ 讀法（B 標；頻率表 T1～T10 原樣沿用（世界、母體、偵測、剔除、合併、放量、長期下跌、量縮、段）；方法 ＝「型態 C 組框架」
     （登錄 §三）＝ researchPatC P1～P10（PREREG型態全量 seq3 §五 價格結構對照 C1～C8 的 AT 世界版）；以下只寫與 PatC 不同或新增者；
     ⛔ 在讀任何本件報酬之前寫死；★＝執行者定，〔 〕內為另一讀法、⛔ 不另跑）═══
 B1 事件 ＝ 逐股呼叫 researchTripleBot_freq.stock_job 原樣；⭐ 依 run_freq 寫法排成 events_<世界>.csv.gz 全文，與已提交檔【逐字】比，任一不同 ⇒
    中止、⛔ 不算報酬。判定母體 ＝ 狀態「保留」者（每格各自 20 日合併 ⇒ H20 持有不重疊）。
 B2 R ＝ ffill 還原收盤(T＋H) ÷ 還原開盤(T＋1) − 1（H ∈ {20, 60, 120}）；X ＝ R − 對照平均（⛔ 不扣成本；另報 X̄ − 0.585%、每筆淨報酬）。
 B3 對照（登錄 §三「同一天 T、r60 同一十分位、當天沒出現三重底的股票等權」＋「同型態 C 組框架」⇒ PatC P3 價格結構版）：
    配對量 r60 ＝ c[first−1] ÷ c[first−61] − 1（＝ S2 主要條件「r60 ＜ 0」的同一個量，patterns_all._rN；first ＝ 第一底 L1）；
    ★ (first−61, first−1] 內有壞 K 棒 ⇒ 不可算（seq335 硬斷點；事件剔除並計數「錨點r60不可算」）〔另一讀法：PatC 原樣不查壞根〕；
    十分位橫斷面 ＝ first 當天 pit_valid ∧ 有效 K 棒 ∧ r60 可算（PatC P3 ★ 原樣；＜10 檔 ⇒ 無十分位）。
    對照股 ＝ first 當天同十分位 ∧ ★ T 當天母體（Frame.gate ∧ pit_valid ＝ 事件同一道 500 張閘；PatC 只看 pit_valid）∧ T＋1 可買（頻率表 T3 同旗標，
    ⛔ 不另剔開盤跌停，與事件同；researchWR V3 同）∧ ★ (first, T＋H] 無硬斷點（壞 K 棒或 T＋H 落在 ≥ 5 日缺口；事件自身同一窗）
    ∧ R 可算 ∧ T 當天【原始】偵測沒有「該格」（任何狀態；PatC P3）∧ 不是自己 ⇒ 等權平均；配對格無對照股 ⇒ 剔除並計數。
 B4 事件自身硬斷點 ＝ (first, T＋H] 有壞 K 棒或 T＋H 落在 ≥ 5 日缺口（(first, T] 頻率表已剔）⇒ 剔除並計數「持有期壞根」；T＋H 超出資料尾 ⇒ 剔除。
 B5 判定量 X̄；CI：H20 曆月分群；★ H60 ＝ (T−段起點)//60、H120 ＝ //120（只描述）；n_eff、出口、結果 ①②③ ＝ PatC P6／WR V6 同式。
    Bonferroni 族 ＝ 本登錄判定格 N ＝ 1 ⇒ z ＝ 1.96。
 B6 ★ 段（登錄 §三「探索｜確認｜早年描述；兩段分報」）：判定 ＝【探索】【確認】各自照 B5 判（researchWR V7 同）；主全窗並報【參考】
    〔另一讀法：PatC 的主全窗單一判定窗〕；早年只描述（reduce_v2 註）。
 B7 假訊號臂（PatC P7 ＋ WR V8；只跑判定格 J、H20）：r ＝ 0…29；每檔每段 n ＝ 該檔 J 保留真事件數；可抽日 ＝ 該檔有效 K 棒 ∧ T 當天母體
    （WR V8 ★ 改當可抽條件）、T ∈ [段起點, min(段尾, 資料尾 − 20)]；新預設排除「存在 J 保留真事件 T_r ∈ [T−20, T]」的日子，不排除版並列；
    不放回抽 n 天；假事件 first ＝ 把該檔真事件（依 T 排序）的「first 到 T 的有效 K 棒根數」依序配給抽到的日子（PatC P7）；
    之後同一套剔除（錨點 r60 不可算／無十分位 → (first, T＋H] 斷點、T＋1 不可買、R 不可算 → 配對格無對照股；計數、⛔ 不補抽）、同一套對照（B3）。
    種子 default_rng([20261020＋r, crc32(sid), 1, 段序號, 版本])。x／30 ＝ 落結果② 次數；結果② 且 x ≥ 2 ⇒ 句首「⚠ 隨機挑日子也有 x／30 次同樣過關。」
 B8 seq322 門檻（WR V9 同式）＝ 該段結果② ∧ Bonferroni 下界 ＞ 0 ∧ 假訊號 x ≤ 1 ∧ X̄ − 0.585% ＞ 0 ∧ 逐月 X 平均之中位數與 X̄ 同號；
    兩段皆過才另起組合層；⭐ 標籤上限「最多暫定」（seq398：主形狀來自已看過結果的家族 ⇒ 事後重切，要靠前瞻紀錄確認）。
 B9 差（描述、⛔ 不判）：J − M（先驗③）、J_有量縮 − J_沒量縮、M_有量縮 − M_沒量縮 ＝ PatC P8 曆月分群線性化 SE（H60／H120 用 B5 分群）。
    ★ 先驗③「加次要條件的 X 不高於主錨」中 ＝ 兩判定段 J − M 差的 95% CI 下界 ≤ 0（沒有顯著較高）〔另報點估計 ≤ 0 版〕。
 B10 結果句必附：「放量、長期下跌取最寬一檔（使用者：次要條件不用太嚴苛）」「主要條件同型態全量 S2」「原文樣本為美股」
    「最多暫定」「主形狀已在型態全量測過（S2 原標籤 H20①／H60①），本件只多了放量與長期下跌條件」「單筆層通過 ≠ 組合會贏 0050」；
    早年另附 reduce_v2 與上櫃版面註。本件無賣出訊號（固定 H 天）；措辭照 seq343，⛔ 不稱最高點、頂部。先驗 ①②③ 照登錄逐字對照。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import zlib
from collections import Counter
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchTripleBot_freq as TF           # noqa: E402  事件偵測＋剔除（⛔ 只 import）
from backtest import researchWR_freq as WF                  # noqa: E402  base、SEGS、reg_check、_G（⛔ 只 import）
from backtest import researchKDJ3 as KJ                     # noqa: E402  共用小工具（⛔ 只 import）
from backtest import researchAscTri_freq as AT              # noqa: E402  load_world 原樣
from backtest import researchWeekly as RW                   # noqa: E402  weeks_of
from backtest import researchPatC as PC                     # noqa: E402  PatAll 同式小工具（⛔ 只 import）
from backtest import evaluate as E                          # noqa: E402  COST
from backtest import universe_gate as UG                    # noqa: E402

UG.set_gate_v2(True)

REG_SHA = TF.REG_SHA
OUT = "backtest/resultsTripleBot"
FREQ = TF.OUT
DRY_OUT = "/mnt/c/Users/ChemTim/AppData/Local/Temp/claude/C--SynologyDrive---------/f4c14e25-a422-4a37-ab64-e11f2ead97b5/scratchpad/triplebot_dry"
HS = (20, 60, 120)
RN = 60
REPS, EXCL, SEED_FAKE = 30, 20, 20261020
NCL = KJ.NCL
Z95 = 1.96
N_FAM = 1
COST = E.COST
CELLS = list(TF.CELLS)
SEGNUM = {"探索": 0, "確認": 1, "主全窗": 2, "早年": 3}
JUDGE_SEGS = ("探索", "確認")
NAME = {"J": "三重底（三個等低的底、收盤突破較高的反彈高點、突破當天量 ≥ 1.5 倍且收紅、距一年高點已跌 ≥ 20%）",
        "M": "主錨：只有主要條件（＝ 型態全量 S2 三重底）", "J_放量2倍": "較嚴：放量改 2 倍", "J_放量3倍": "較嚴：放量改 3 倍",
        "J_前5日均量": "較嚴：放量改前 5 日均量 1.5 倍", "J_跌30%": "較嚴：距一年高點 ≤ −30%", "J_跌40%": "較嚴：距一年高點 ≤ −40%",
        "J_120日線下>3月": "較嚴：第一底前收盤連續在 120 日線下 ＞ 3 個月", "M+放量": "單條：S2 ＋ 放量", "M+長期下跌": "單條：S2 ＋ 長期下跌",
        "J_有量縮": "量縮組：判定格 ∧ 第三底量 ＜ 第一底量", "J_沒量縮": "量縮組：判定格 ∧ 第三底量 ≥ 第一底量",
        "M_有量縮": "量縮組：S2 ∧ 第三底量 ＜ 第一底量", "M_沒量縮": "量縮組：S2 ∧ 第三底量 ≥ 第一底量"}
SENT_SELF = ["放量、長期下跌取最寬一檔（使用者：次要條件不用太嚴苛）", "主要條件同型態全量 S2", "原文樣本為美股", "最多暫定",
             "主形狀已在型態全量測過（S2 原標籤 H20①／H60①），本件只多了放量與長期下跌條件"]
SENT_ALL = "單筆層通過 ≠ 組合會贏 0050"
NOTE_EARLY = KJ.NOTE_EARLY
EXC = ["T+H超出資料尾", "錨點r60不可算", "無十分位(橫斷面<10)", "持有期壞根", "R不可算", "配對格無對照股"]
LOG: list = []
DRY = False


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


pct = KJ.pct
now_tpe = KJ.now_tpe


# ═════════════ 對照（單一事件；真／假共用；PatC s_one 改 B3）═════════════
def s_one(X, base_row, H, i, T, f):
    """⇒ (對照平均, 對照數)；對照數 −1 ＝ 錨點不可算或無十分位。base_row ＝ BASE[cell,H][T]（母體 ∧ T＋1 可買 ∧ R 可算 ∧ 當天無原始偵測）。"""
    d = X["DEC"][f, i]
    if d < 0:
        return np.nan, -1
    b = T + H
    m = base_row & (X["DEC"][f] == d) & ((X["CSB"][b] - X["CSB"][f]) == 0) & ~X["GAP"][b]
    m[i] = False
    cnt = int(m.sum())
    return (float(X["G"][H][T][m].mean()) if cnt else np.nan), cnt


def own_brk(X, i, f, b):
    return bool((X["CSB"][b, i] - X["CSB"][f, i]) > 0 or X["GAP"][b, i])


def selftest():
    msgs = KJ.fixture_common()
    rng = np.random.default_rng(7)
    n, S = 300, 40
    X = {"G": {H: rng.normal(0, 0.1, (n, S)) for H in HS}, "CSB": np.cumsum(rng.random((n, S)) < 0.01, axis=0).astype(np.int32),
         "GAP": rng.random((n, S)) < 0.02, "DEC": rng.integers(-1, 3, (n, S)).astype(np.int8)}
    BASE = rng.random((n, S)) < 0.8
    worst = 0.0; nchk = 0
    for H in HS:
        for _ in range(300):
            t = int(rng.integers(70, n - H)); i = int(rng.integers(0, S)); f = int(t - rng.integers(0, 60))
            c1, n1 = s_one(X, BASE[t].copy(), H, i, t, f)
            if X["DEC"][f, i] < 0:
                assert n1 == -1; continue
            vals = []
            for q in range(S):
                if q == i or not BASE[t, q] or X["DEC"][f, q] != X["DEC"][f, i]:
                    continue
                if any(X["CSB"][p, q] != X["CSB"][p - 1, q] for p in range(f + 1, t + H + 1)) or X["GAP"][t + H, q]:
                    continue
                vals.append(X["G"][H][t, q])
            assert n1 == len(vals), (n1, len(vals))
            if vals:
                worst = max(worst, abs(c1 - float(np.mean(vals))))
            nchk += 1
    assert worst < 1e-12
    msgs.append(f"F8 價格結構對照（first 錨點、(first, T＋H] 逐日掃斷點）向量版 ＝ 逐檔迴圈（{nchk} 筆）最大差 {worst:.1e}")
    for m_ in msgs:
        log("✅ " + m_)
    return msgs


# ═════════════ 逐股 ═════════════
def stock_job(a):
    wn, sid = a
    sid_, res = TF.stock_job(a)                            # ⭐ 頻率表同一支：事件、狀態
    if res is None:
        return sid, None
    X = WF.base(wn, sid)
    B = X["B"]; idx = X["idx"]; n0 = X["n0"]
    o_b = np.asarray(B["o"], float); c_b = np.asarray(B["c"], float)
    assert np.array_equal(X["df"]["close"].to_numpy(float)[idx], c_b), f"{sid} B['c'] ≠ df close"
    A = KJ.stock_arrays(idx, o_b, c_b, X["bad"], n0, X["TRD"], X["O"], X["UPL"], X["gate"], X["PV"], hs=HS, rn=RN, anchor="pre", dry=DRY)
    A["CSB"] = A["CSB"].astype(np.int32)
    A["bars"] = idx.astype(np.int32)
    A.pop("BRK")
    return sid, {"ev": res["ev"], "A": A}


def fake_arm(X, H, ii, TT, LAG, p0, pend, moni_s, segnum, BASE):
    order = np.lexsort((TT, ii))
    ii_s, TT_s, lag_s = ii[order], TT[order], LAG[order]
    stocks, starts = np.unique(ii_s, return_index=True)
    ends = np.r_[starts[1:], len(ii_s)]
    acc = np.zeros((REPS, 2, NCL, 2)); cnt = np.zeros((REPS, 2, 6), np.int64)  # 抽出、錨點不可算/無十分位、斷點/T+1/R、無對照股、可抽日不足、(保留)
    G = X["G"][H]
    cands = {}
    for i in stocks:
        bars = X["BARS"][int(i)]
        bb = bars[(bars >= p0) & (bars <= pend)].astype(np.int64)
        cands[int(i)] = bb[X["POPT"][bb, int(i)]]
    for r in range(REPS):
        for ver in (0, 1):
            dX = []; TTs = []
            for i, a, b in zip(stocks, starts, ends):
                i = int(i); Tk = TT_s[a:b]
                cand = cands[i]
                if ver == 0:
                    cand = PC.excl_past(cand, Tk)
                m = min(len(Tk), len(cand)); cnt[r, ver, 4] += len(Tk) - m
                if m == 0:
                    continue
                rng = np.random.default_rng([SEED_FAKE + r, X["CRC"][i], 1, segnum, ver])
                pick = np.sort(rng.choice(cand, size=m, replace=False))
                bars = X["BARS"][i]
                for t, lg in zip(pick, lag_s[a:a + m]):
                    t = int(t); cnt[r, ver, 0] += 1
                    bi = int(np.searchsorted(bars, t))
                    if bi - lg < 0:
                        cnt[r, ver, 1] += 1; continue
                    f = int(bars[bi - lg])
                    if X["DEC"][f, i] < 0:
                        cnt[r, ver, 1] += 1; continue
                    if own_brk(X, i, f, t + H) or not (X["TR1"][t, i] and np.isfinite(G[t, i])):
                        cnt[r, ver, 2] += 1; continue
                    cm, c_ = s_one(X, BASE[t].copy(), H, i, t, f)
                    if c_ <= 0:
                        cnt[r, ver, 3] += 1; continue
                    dX.append(float(G[t, i] - cm)); TTs.append(t)
            if dX:
                cl = KJ.clkey(np.asarray(TTs), H, p0, moni_s)
                assert cl.max() < NCL
                np.add.at(acc[r, ver, :, 0], cl, 1.0)
                np.add.at(acc[r, ver, :, 1], cl, np.asarray(dX))
    return acc, cnt


def sentence(cell, st, sg, early=False):
    nm = NAME[cell]; H = int(st["H"])
    tail = SENT_SELF + [SENT_ALL] + (NOTE_EARLY if early else [])
    rs = st["結果"]
    head = f"{nm}之後 {H} 天，比同一天、型態前 60 日走勢同一級距、沒出現該型態的股票"
    if rs == "樣本不足以分辨":
        s = f"{head}：樣本不足以分辨（n_eff＝{int(st.get('n_eff', 0) or 0)}）"
    else:
        pre = "樣本中等（n_eff＝{}，介於 30 與 100 之間）：".format(int(st["n_eff"])) if st.get("出口") == "出口②" else ""
        if rs == "結果①":
            s = "{}{}：分不出（每筆平均 X̄ {}，95% CI {} ～ {}）".format(pre, head, pct(st["X̄"]), pct(st["lo"]), pct(st["hi"]))
        else:
            x2 = st.get("假訊號_新預設_x2", 0) or 0
            warn = "⚠ 隨機挑日子也有 {}／30 次同樣過關。".format(int(x2)) if (rs == "結果②" and x2 >= 2) else ""
            verb = "多" if rs == "結果②" else "少"
            s = "{}{}{}：{} {}（95% CI {} ～ {}；扣成本 0.585% 後 X̄ {}）".format(warn, pre, head, verb, pct(abs(st["X̄"]))[1:], pct(st["lo"]),
                                                                       pct(st["hi"]), pct(st["X̄扣成本"]))
    seg = {"探索": "〔探索段・判定〕", "確認": "〔確認段・判定〕", "主全窗": "〔主全窗・參考〕", "早年": "〔早年・描述〕"}[sg]
    if cell != "J" or H != 20:
        seg = seg.replace("・判定", "・描述").replace("・參考", "・描述")
    role = "" if cell == "J" else "〔描述格、⛔ 不判、不計 N〕"
    return seg + role + s + "｜" + "；".join(tail)


def main():
    global DRY
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); ap.add_argument("--dry", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    DRY = bool(a.dry)
    if a.limit and not DRY:
        raise SystemExit("⛔ --limit 只准與 --dry 同用（不准做含報酬的小樣本試跑）")
    t0 = time.time()
    out = DRY_OUT if DRY else OUT
    os.makedirs(os.path.join(out, "events"), exist_ok=True)
    reg = WF.reg_check(REG_SHA)
    log(f"[登錄] {reg}（sha {REG_SHA} 已驗）｜{'乾跑（R 全寫 0）' if DRY else '本體'}開跑 {now_tpe()}")
    fx = selftest()
    fq = json.load(open(os.path.join(FREQ, "freq.json"), encoding="utf-8"))
    J = {"性質": "三重底 seq1 事件層正式跑（單筆層；判定 J 一格 H20，探索、確認各自報；H60／H120 描述；標籤最多暫定）" + ("〔乾跑：R 全 0〕" if DRY else ""),
         "登錄": f"台股策略線 seq1 sha {REG_SHA}", "裁定": "seq394 第 1 題、seq398 發號（最多暫定）、seq399 核准開跑；N_前段 ＋1",
         "方法": "型態 C 組框架 ＝ researchPatC P1～P10（PREREG型態全量 seq3 §五 價格結構對照；配對量 r60 錨在第一底）",
         "Bonferroni": {"族N": N_FAM, "z": Z95}, "成本": COST, "fixture": fx, "S2型態全量原標籤": fq["S02型態全量原標籤"],
         "讀法": __doc__.split("═══ 讀法")[1], "世界": {}, "時點": {"本體開跑": now_tpe()}}
    MAIN = []; DIFF = []; BY = []; FK = []; FACC = {}
    for wn in ("主", "早年"):
        W = AT.load_world(wn); cal = W["cal"]; n0 = W["n0"]
        win = {}
        for sg, (x_, y_) in WF.SEGS[wn].items():
            p0 = int(cal.searchsorted(pd.Timestamp(x_)))
            p1 = n0 - 2 if y_ is None else min(n0 - 2, int(cal.searchsorted(pd.Timestamp(y_), side="right")) - 1)
            win[sg] = (p0, p1)
        W["win"] = win
        W["wk"], W["wf"], W["wl"] = RW.weeks_of(cal)
        WF._G[wn] = W
        log(f"[{wn}] 段 " + "｜".join(f"{k} {cal[p].date()}～{cal[q].date()}" for k, (p, q) in win.items()))
        sids = W["sids"]; S = len(sids); ix = W["ix"]
        run_sids = sids[:a.limit] if a.limit else sids
        VALID = np.zeros((n0, S), bool); RNm = np.full((n0, S), np.nan); TR1 = np.zeros((n0, S), bool); POPT = np.zeros((n0, S), bool)
        PVm = np.zeros((n0, S), bool); CSB = np.zeros((n0, S), np.int32); GAP = np.zeros((n0, S), bool)
        G = {H: np.full((n0, S), np.nan) for H in HS}
        BARS = [np.zeros(0, np.int32)] * S
        ok = {}
        with Pool(a.procs) as pool:
            for k_, (sid, r) in enumerate(pool.imap_unordered(stock_job, [(wn, s) for s in run_sids], chunksize=8)):
                if r is not None:
                    j = ix[sid]; A = r["A"]
                    VALID[:, j] = A["valid"]; RNm[:, j] = A["RN"]; TR1[:, j] = A["TR1"]; POPT[:, j] = A["POPT"]; PVm[:, j] = A["PV"]
                    CSB[:, j] = A["CSB"]; GAP[:, j] = A["GAP"]; BARS[j] = A["bars"]
                    for H in HS:
                        G[H][:, j] = A["G"][H]
                    ok[sid] = {"ev": r["ev"]}
                if (k_ + 1) % 400 == 0:
                    log(f"  {wn} … {k_ + 1}／{len(run_sids)}｜{time.time() - t0:.0f}s")
        log(f"[{wn}] 逐股完 {len(ok)} 檔｜{time.time() - t0:.0f}s")
        nl, how = KJ.check_events(KJ.freq_text(ok, cal, n0, CELLS), wn, FREQ, run_sids if a.limit else None)
        log(f"[查核1] {wn}：重新偵測與已提交頻率表 events_{wn}.csv.gz {how}相同（{nl:,} 列）")
        if "第一次讀報酬" not in J["時點"] and not DRY:
            J["時點"]["第一次讀報酬"] = now_tpe()
        dpos = {str(d.date()): p for p, d in enumerate(cal)}
        RAW = {c: np.zeros((n0, S), bool) for c in CELLS}
        KEPT = {c: [] for c in CELLS}
        for s_, r in ok.items():
            j = ix[s_]
            for c in CELLS:
                for e in r["ev"][c]:
                    RAW[c][e["T"], j] = True
                    if e["st"] == "保留":
                        KEPT[c].append((j, e["T"], dpos[e["first"]]))
        bad2 = Counter()
        for c in CELLS:
            for j, T, f in KEPT[c]:
                if not POPT[T, j]:
                    bad2[f"{c} 保留但本支判閘外"] += 1
                if not TR1[T, j]:
                    bad2[f"{c} 保留但本支判 T+1 不可買"] += 1
                if not VALID[f, j]:
                    bad2[f"{c} first 不是有效 K 棒"] += 1
                if (CSB[T, j] - CSB[f, j]) != 0:
                    bad2[f"{c} 保留但 (first, T] 有壞根"] += 1
        assert not bad2, bad2
        log("[查核2] 保留事件：本支矩陣判 T 當天母體、T＋1 可買、first 為有效 K 棒、(first, T] 無壞根（與頻率表 T3 一致）")
        DEC = PC.dec_matrix(RNm, PVm & VALID & np.isfinite(RNm))
        moni = np.asarray(cal.year * 12 + cal.month)
        years = np.asarray(cal.year); dates = np.array([str(d.date()) for d in cal])
        crc = [zlib.crc32(s.encode("utf-8")) for s in sids]
        mk_all = np.array([W["mk"].get(s, "twse") for s in sids])
        X = {"G": G, "CSB": CSB, "GAP": GAP, "DEC": DEC, "TR1": TR1, "POPT": POPT, "BARS": BARS, "CRC": crc}
        EW = {}
        for H in HS:
            em = POPT & TR1 & np.isfinite(G[H])
            cnt_ = em.sum(axis=1); sm = np.where(em, np.nan_to_num(G[H]), 0.0).sum(axis=1)
            EW[H] = np.where(cnt_ > 0, sm / np.maximum(cnt_, 1), np.nan)
        log(f"[十分位、EW] 完成｜{time.time() - t0:.0f}s")
        Wj = {"資料": W["data"], "日曆": [str(cal[0].date()), str(cal[-1].date())], "檔數": len(sids), "可用檔數": len(ok),
              "閘": W["gate"], "壞根": W["bad_info"], "段": {sg: {"期間": f"{cal[p].date()}～{cal[q].date()}", "年": round((cal[q] - cal[p]).days / 365.25, 3)}
                                                           for sg, (p, q) in win.items()}}
        EVF = {}
        for c in CELLS:
            for H in HS:
                BASE = POPT & TR1 & np.isfinite(G[H]) & ~RAW[c]
                for sg, (p0, p1) in win.items():
                    moni_s = moni - moni[p0]
                    yrs = (cal[p1] - cal[p0]).days / 365.25
                    kept = sorted([x for x in KEPT[c] if p0 <= x[1] <= p1], key=lambda z: (z[1], sids[z[0]]))
                    nk = len(kept)
                    ii = np.array([x[0] for x in kept], np.int64); TT = np.array([x[1] for x in kept], np.int64)
                    FF = np.array([x[2] for x in kept], np.int64)
                    LAG = np.array([int(np.searchsorted(BARS[i], t)) - int(np.searchsorted(BARS[i], f)) for i, t, f in zip(ii, TT, FF)], np.int64)
                    why = np.full(nk, "有", dtype=object)
                    g = np.full(nk, np.nan); cm = np.full(nk, np.nan); cc = np.zeros(nk, np.int64); rv = np.full(nk, np.nan)
                    dec_e = np.full(nk, -1, np.int64); ew = np.full(nk, np.nan)
                    for q in range(nk):
                        i, T, f = int(ii[q]), int(TT[q]), int(FF[q])
                        rv[q] = RNm[f, i]; dec_e[q] = DEC[f, i]
                        if T + H > n0 - 1:
                            why[q] = EXC[0]; continue
                        g[q] = G[H][T, i]; ew[q] = EW[H][T]
                        if not np.isfinite(rv[q]):
                            why[q] = EXC[1]
                        elif dec_e[q] < 0:
                            why[q] = EXC[2]
                        elif own_brk(X, i, f, T + H):
                            why[q] = EXC[3]
                        elif not np.isfinite(g[q]):
                            why[q] = EXC[4]
                        else:
                            cm[q], cc[q] = s_one(X, BASE[T].copy(), H, i, T, f)
                            if cc[q] <= 0:
                                why[q] = EXC[5]
                    okm = why == "有"
                    Xv = np.where(okm, g - cm, np.nan)
                    Xu = g - ew
                    st = KJ.cell_stats(Xv[okm], TT[okm], H, p0, moni_s)
                    st.update(KJ.trade_stats(g[okm], cm[okm]))
                    st.update({"保留": int(nk), "配對剔除": {k: int(v) for k, v in Counter(why[~okm].tolist()).items()},
                               "配對剔除數": int((~okm).sum()), "對照數_中位": float(np.median(cc[okm])) if okm.any() else None,
                               "對照數_最小": int(cc[okm].min()) if okm.any() else None,
                               "每年事件數(保留)": round(nk / yrs, 1), "每年事件數(配對後)": round(int(okm.sum()) / yrs, 1),
                               "相異檔數": int(len(set(ii[okm].tolist()))), "未配對_Xu": KJ.desc_ci(Xu[okm], TT[okm], H, p0, moni_s)})
                    mk = mk_all[ii] if nk else np.zeros(0, str)
                    st["上市"] = KJ.desc_ci(Xv[okm & (mk == "twse")], TT[okm & (mk == "twse")], H, p0, moni_s)
                    st["上櫃"] = KJ.desc_ci(Xv[okm & (mk == "tpex")], TT[okm & (mk == "tpex")], H, p0, moni_s)
                    yr = years[TT] if nk else np.zeros(0, int)
                    st["逐年"] = {str(y): {"保留": int((yr == y).sum()), "n": int((okm & (yr == y)).sum()),
                                         "X̄": float(Xv[okm & (yr == y)].mean()) if (okm & (yr == y)).any() else None}
                                for y in sorted(set(yr.tolist()))}
                    for y, qd in st["逐年"].items():
                        BY.append({"世界": wn, "段": sg, "格": c, "H": H, "年": y, **qd})
                    fr = pd.DataFrame({"sid": [sids[i] for i in ii], "market": mk, "T": dates[TT] if nk else [], "first": dates[FF] if nk else [],
                                       "lag": LAG, "進場日": [dates[t + 1] for t in TT], "出場日": [dates[t + H] if t + H <= n0 - 1 else "" for t in TT],
                                       "r60": rv, "十分位": dec_e, "R": g, "對照平均": cm, "對照數": cc, "X": Xv, "EW": ew, "X_未配對": Xu,
                                       "分群": KJ.clkey(TT, H, p0, moni_s) if nk else [], "配對": why})
                    EVF[(sg, c, H)] = {"T": TT, "ok": okm, "X": Xv}
                    if c == "J" and H == 20:
                        pend = min(p1, n0 - 1 - H)
                        acc, cntf = fake_arm(X, H, ii, TT, LAG, p0, pend, moni_s, SEGNUM[sg], BASE)
                        FACC[f"{wn}|{sg}|{c}|H{H}"] = (acc, cntf)
                        for ver, vn in ((0, "新預設"), (1, "不排除")):
                            res_ = [PC.agg_eval(acc[r_, ver]) for r_ in range(REPS)]
                            st[f"假訊號_{vn}_x2"] = sum(1 for q in res_ if q and q["結果"] == "結果②")
                            st[f"假訊號_{vn}_x3"] = sum(1 for q in res_ if q and q["結果"] == "結果③")
                            st[f"假訊號_{vn}_平均X"] = float(np.mean([q["平均"] for q in res_ if q])) if any(res_) else None
                            c2 = cntf[:, ver].sum(axis=0)
                            st[f"假訊號_{vn}_帳"] = {"抽出": int(c2[0]), "錨點不可算或無十分位": int(c2[1]), "斷點或T+1或R": int(c2[2]),
                                                  "配對格無對照股": int(c2[3]), "可抽日不足": int(c2[4])}
                            for r_, q in enumerate(res_):
                                FK.append({"世界": wn, "段": sg, "格": c, "H": H, "版本": vn, "r": r_,
                                           **({kk: q[kk] for kk in ("n", "平均", "lo", "hi", "n_eff", "出口", "結果")} if q else {"n": 0})})
                        st["過seq322門檻"] = bool(st["結果"] == "結果②" and st.get("bonf_lo", -1) > 0 and st.get("假訊號_新預設_x2", 99) <= 1
                                               and st.get("X̄扣成本", -1) > 0 and st.get("逐群中位與平均同號", False))
                    st["H"] = H
                    if c != "J":
                        st["身分"] = "主錨（描述、⛔ 不判）" if c == "M" else "描述格（⛔ 不判、不計 N）"
                    elif H != 20:
                        st["身分"] = f"H{H} 描述（⛔ 不判）"
                    else:
                        st["身分"] = {"探索": "判定格｜探索段判定", "確認": "判定格｜確認段判定", "主全窗": "判定格｜主全窗參考", "早年": "判定格｜早年描述"}[sg]
                    st["句子"] = sentence(c, st, sg, early=(wn == "早年"))
                    Wj["段"][sg][f"{c}_H{H}"] = st
                    fr.to_csv(os.path.join(out, "events", f"trades_{wn}_{sg}_{c}_H{H}.csv.gz"), index=False,
                              compression={"method": "gzip", "compresslevel": 6})
                    MAIN.append({"世界": wn, "段": sg, "格": c, "說明": NAME[c], "H": H, "身分": st["身分"], "期間": Wj["段"][sg]["期間"],
                                 **{k: v for k, v in st.items() if not isinstance(v, dict) and k not in ("H", "身分", "句子")}, "句子": st["句子"]})
                    if c in ("J", "M") or H == 20:
                        log(f"  [{wn}/{sg}] {c} H{H}：保留 {nk} 配對 {st['n']} n_eff={st.get('n_eff')} X̄={pct(st.get('X̄'))} "
                            f"CI {pct(st.get('lo'))}～{pct(st.get('hi'))} {st['結果']}" + (f" 假 x={st.get('假訊號_新預設_x2')}" if (c == "J" and H == 20) else "")
                            + f"｜{time.time() - t0:.0f}s")
                del BASE
        # ── 差（B9）
        for sg, (p0, p1) in win.items():
            moni_s = moni - moni[p0]
            for H in HS:
                for new, old in (("J", "M"), ("J_有量縮", "J_沒量縮"), ("M_有量縮", "M_沒量縮")):
                    A1 = EVF[(sg, new, H)]; A2 = EVF[(sg, old, H)]
                    k1 = KJ.clkey(A1["T"][A1["ok"]], H, p0, moni_s); k2 = KJ.clkey(A2["T"][A2["ok"]], H, p0, moni_s)
                    d = PC.diff_stats(A1["X"][A1["ok"]], k1, A2["X"][A2["ok"]], k2)
                    DIFF.append({"世界": wn, "段": sg, "H": H, "比較": f"{new} − {old}", **d})
        Wj["頻率表重疊(附加)"] = {sg: fq["世界"][wn]["段"][sg].get("附加") for sg in win}
        J["世界"][wn] = Wj
        del VALID, RNm, TR1, POPT, PVm, CSB, GAP, G, RAW, DEC, X, EW
    # ── 判定（J H20；探索、確認各自）
    jd = {}
    for sg in JUDGE_SEGS + ("主全窗",):
        st = J["世界"]["主"]["段"][sg]["J_H20"]
        jd[sg] = {"身分": "判定" if sg in JUDGE_SEGS else "參考", "結果": st["結果"], "出口": st.get("出口"), "n": st["n"], "n_eff": st.get("n_eff"),
                  "X̄": st.get("X̄"), "95%CI": [st.get("lo"), st.get("hi")], "假訊號x/30(新預設)": st.get("假訊號_新預設_x2"),
                  "X̄−成本": st.get("X̄扣成本"), "逐月中位同號": st.get("逐群中位與平均同號"), "過seq322門檻": st.get("過seq322門檻"), "句子": st["句子"]}
    J["判定"] = jd
    both322 = all(jd[sg]["過seq322門檻"] for sg in JUDGE_SEGS)
    J["整件"] = {"兩段皆過seq322": both322,
                 "結論": ("兩段皆過 seq322 ⇒ 標籤最多【暫定】（主形狀已在型態全量測過；要靠前瞻紀錄確認）；可另起組合層登錄（單筆層通過 ≠ 組合會贏 0050）"
                        if both322 else "未兩段皆過 seq322 ⇒ ⛔ 不另起組合層"), "標籤上限": "最多暫定（seq398）"}
    # ── 先驗（登錄 §六，⛔ 不改）
    dJM = {r["段"]: r for r in DIFF if r["世界"] == "主" and r["H"] == 20 and r["比較"] == "J − M"}
    ne_ok = {sg: bool((jd[sg]["n_eff"] or 0) >= 30) for sg in JUDGE_SEGS}
    J["先驗"] = {
        "① 兩段 n_eff ≥ 30（約四成）": {sg: {"n_eff(配對後)": jd[sg]["n_eff"], "中": ne_ok[sg]} for sg in JUDGE_SEGS} | {"中": all(ne_ok.values())},
        "② 若可判，兩段皆 ①（約七成）": {sg: {"結果": jd[sg]["結果"]} for sg in JUDGE_SEGS}
                                  | {"中": bool(all(ne_ok.values()) and all(jd[sg]["結果"] == "結果①" for sg in JUDGE_SEGS))},
        "③ 加次要條件的 X 不高於主錨（約六成）": {sg: {"差(J−M)": dJM[sg].get("差"), "CI": [dJM[sg].get("lo"), dJM[sg].get("hi")],
                                               "CI下界≤0": bool(dJM[sg].get("lo", 1) <= 0), "點估計≤0": bool(dJM[sg].get("差", 1) <= 0)}
                                          for sg in JUDGE_SEGS} | {"中": bool(all(dJM[sg].get("lo", 1) <= 0 for sg in JUDGE_SEGS)),
                                                                   "中(另一讀法：點估計)": bool(all(dJM[sg].get("差", 1) <= 0 for sg in JUDGE_SEGS))}}
    J["N"] = {"本件判定格": 1, "主錨、描述格、差、H60／H120": "不計 N"}
    J["時點"]["完成"] = now_tpe()
    pd.DataFrame(MAIN).to_csv(os.path.join(out, "TripleBot_main.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(DIFF).to_csv(os.path.join(out, "TripleBot_diff.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(BY).to_csv(os.path.join(out, "by_year.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(FK).to_csv(os.path.join(out, "fake_reps.csv"), index=False, encoding="utf-8-sig")
    keys = list(FACC)
    np.savez_compressed(os.path.join(out, "fake_acc.npz"), keys=np.array(keys), acc=np.stack([FACC[k][0] for k in keys]),
                        cnt=np.stack([FACC[k][1] for k in keys]))
    J["差"] = DIFF
    json.dump(J, open(os.path.join(out, "TripleBot.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[判定] {json.dumps({k: {kk: v[kk] for kk in ('結果', 'n_eff', 'X̄', '假訊號x/30(新預設)', '過seq322門檻')} for k, v in jd.items()}, ensure_ascii=False, default=float)}")
    log(f"[先驗] " + "｜".join(f"{k} 中={v['中']}" for k, v in J["先驗"].items()))
    log(f"完成 {time.time() - t0:.0f}s")
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
