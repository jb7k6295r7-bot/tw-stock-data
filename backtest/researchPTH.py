# -*- coding: utf-8 -*-
"""接近 52 週新高 PTH seq1【事件層正式跑】（台股策略線 登錄 sha e5d57b29ddb34ee7，2026-10-20 11:38；裁定 seq388 發號 N_前段 ＋1、
seq390 核准正式跑；George & Hwang 2004：月底收盤 ÷ 過去 12 個月最高收盤，前 30% 做多、抱 6 個月）——回測線計算子代理。
⛔ 不 commit、不改既有程式與結果夾；researchPTH_freq（世界、月底、PTH、排序、進場日、進場剔除；讀法 P1～P10 寫死、沿用）、researchUO（x_stats（族 N＝1）、
   agg_eval、diff_stats、Sampler）、researchTurtle（NOTE_EARLY）、research11、evaluate ⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTH [--procs 3]
    乾跑（⛔ 不算任何報酬；只驗頻率表重現、fixture）：... -m backtest.researchPTH --dry
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTH_check
輸出 backtest/resultsPTH/（⛔ 不碰 freq/）：PTH.json、PTH_main.csv（判定表＋並報＋描述）、block_ci.csv、by_year.csv、fake_reps.csv、
    events/trades_<世界>_<格>.csv.gz（逐筆進出、對照、X）、run.log

格：跳月 ＝ 判定格（登錄 §一「主臂：跳 1 個月」）；不跳 ＝ 並報（⛔ 不擇優，登錄 §一、裁定 seq388）；
    描述（⛔ 不判、不計 N）：跳月_3月、跳月_12月（天數軸 3／12 個月）、後30%（登錄 §一）、跳月_最高10檔（組合層描述格的事件層版，裁定 seq388）、
    6 個月不重疊區塊重抽 CI（裁定 seq390）；另一讀法（只報）：跳月_扣前30對照；假訊號臂（同月隨機 30%，30 次）。

═══ 讀法（R 標；頻率表 P1～P10 原樣沿用（世界、母體、壞根、月底、PTH、前 30%、進場日、進場剔除、段），以下為正式跑新增；
     ⛔ 在讀任何本件報酬之前寫死；★＝執行者定，〔 〕內為另一讀法）═══
 R1 事件 ＝ researchPTH_freq.main 原樣重跑到 /tmp/pth_freq_rerun（⛔ 不寫 freq/）⇒ events_<世界>.csv.gz 與已提交 backtest/resultsPTH/freq/ 逐位元組比，
    任一不同 ⇒ 中止、⛔ 不算報酬。事件 ＝ 入選 ∧ 該臂狀態「保留」（同檔連月入選各算一筆，登錄 §二；⛔ 無持有限制：原文重疊組合）。
    進場 ＝ 該臂進場日 e 的還原開盤（跳月：形成月 ＋2 個曆月第一個交易日；不跳：＋1）。
 R2 出場（登錄 §一「持有 6 個月」；★ 本線定）：進場月 M（e 所在曆月）起算第 H 個曆月（M＋H−1）的最後一個交易日 X 收盤賣〔另一讀法：M＋H 第一個交易日開盤〕；
    ＝ 持有整整 H 個曆月、與下一批（M＋H 月初開盤進場）銜接。H ＝ 6 判、3／12 描述（登錄 §四 天數軸）。
    X 當天無成交 ⇒ 用 X 當天或之前最後一根有效 K 棒還原收盤（停牌中；記「到期日無成交、用前一根收盤」）。
    ⛔ 不跨壞根（登錄 §四、seq335）：（進場那根, X 當天或之前最後一根］內有壞 K 棒 ⇒ 以第一個壞 K 棒前一根還原收盤強制出場。
    之後再無成交且最後一根距資料尾 ≥ 5 交易日（下市）⇒ 最後一根收盤（「末根」）；X 超出日曆（含資料尾不完整月）且未下市 ⇒「資料尾未出場」：
    照實報件數與帳面報酬，⛔ 不進 X（researchUO E3 同）。賣出日開盤跌停不另處理（收盤賣）。
 R3 R ＝ 出場價 ÷ 進場還原開盤 − 1；淨 ＝ R − 0.585%（evaluate.COST）；X ＝ (R − 0.585%) − 對照平均 (R − 0.585%) ＝ R − 對照平均 R。持有天數 ＝ 出場日 − e（日曆位置差）。
 R4 對照（登錄 §二「同日同母體隨機 20 檔同持有」）：池 ＝ 同一形成月 t 的排序母體（頻率表 P2∧P3：500 張閘、pit、PTH 可算）∧ 同臂狀態「保留」
    （同一 e 可買：無壞根(t,e]、e 有成交、開盤有效、非開盤鎖漲停）∧ 同 H 的 R 可算；不放回抽 20 檔（不足 ⇒ 全取、計數）；等權；各自照 R2 出場。
    ★ 只扣事件股自己〔另一讀法 跳月_扣前30對照：再扣同月全部 PTH 前 30% ⇒ 對照變成「其餘 70%」，只報〕——理由：本件事件占母體 30%，
    比照 researchUO E6 扣同日原始偵測會把「隨便買」換成「買其餘 70%」，與登錄「比同時隨便買」不同。
    種子 default_rng([20261020, 格標, 形成月序 j, crc32(sid)])；格標 跳月＝0、不跳＝1、跳月_3月＝3、跳月_12月＝12、跳月_扣前30對照＝5、後30%＝7；假訊號 ＝ 1000＋r。
 R5 判定量 X̄；CI ＝ 進場月分群（research11.cl_stats 式，researchUO.x_stats）、1.96；n_eff ＝ min(可算筆數, 有事件進場月數)；n_eff ＜ 30 ⇒ 依構造不可判定、
    30～99 ⇒ 句首「樣本中等」；結果② ＝ CI 不含 0 且 X̄ ＞ 0、③ ＝ X̄ ＜ 0 且 CI 不含 0、① ＝ 含 0（登錄 §二）。Bonferroni 族 N ＝ 1（本登錄 1 格）⇒ z ＝ 1.96。
    判定段：探索、確認【各自報】為準（seq366）；主全窗參考；早年 2005～2014 描述（附 reduce_v2 約 0.3% 註）。
 R6 seq322（researchUO E9 同式）＝ 結果② ∧ Bonferroni 下界 ＞ 0 ∧ 假訊號 x ≤ 1 ∧ X̄ − 0.585% ＞ 0 ∧ 逐月 X 平均之中位數與 X̄ 同號；只判定格（跳月）各段各報。
    seq329 §二（|t| ≥ N 帳 Bonferroni 臨界）：本登錄族 N＝1 ⇒ 臨界 1.96 ⇔ CI 不含 0，已含在結果② 內；|t| 照報。
 R7 假訊號臂（登錄 §二「同月隨機 30% 股票當假 PTH 組，30 次」）：只做跳月；r ＝ 0…29；每個進場日在段內的形成月 j：池 ＝ R4 跳月 6 個月池；
    ★ 抽 ⌈0.3 × 池大小⌉ 檔（不放回；種子 default_rng([20261021＋r, j, 段序號])）；每檔照 R4 抽對照（扣自己）、算 X；進場月分群 ⇒ 結果；x／30 ＝ 落結果② 的次數。
 R8 6 個月不重疊區塊重抽 CI（裁定 seq390 描述格）：段內進場月由第一個有事件月起每 6 個曆月一塊（最後不足 6 個月的一塊照留）；每塊 (ΣX, 筆數)；
    有放回重抽同樣塊數、X̄* ＝ ΣΣX ÷ Σ筆數，B ＝ 10,000，種子 default_rng([20261022, 段序號, 格標])；百分位 2.5／97.5 ⇒ ①②③。
    與判定格 ①②③ 不同 ⇒ 結果句必寫「區塊 CI 較寬、結論不穩」。跳月、不跳兩格都做。
 R9 描述：跳月_最高10檔 ＝ 跳月格可算筆中每個形成月 PTH 最高 10 檔（★ 同 PTH 以 default_rng([20261023, j]) 隨機排序打破；PTH ＝ 1 每月中位約 31 檔，
    實際＝「在一年高點上的股票隨機挑 10 檔」），用跳月格同一批對照；⛔ 組合層（登錄 §三）過 seq322 才另跑，本檔不跑。
    後30% ＝ 頻率表後 30% 旗標 ∧ 跳月狀態保留，對照同 R4（扣自己）。跳月_3月／12月 同 R2～R4。
    不跳 − 跳月：researchUO.diff_stats（進場月分群線性化）＝ 先驗③。
 R10 引自頻率表（⛔ 不重算）：PTH 與 12−1 每月 Spearman（先驗②）、營量／營飆重疊（結果句必附）、seq377 等價。
 R11 結果句必附：「原文用拆股調整價、本件用含息還原價」「跳 1 個月為本線定，不跳月並報」「單筆層通過 ≠ 組合會贏 0050」
     「營量入選股多半本來就在 PTH 前 30%」；區塊 CI 結論不同時「區塊 CI 較寬、結論不穩」；早年另附 reduce_v2 與上櫃版面註（researchTurtle NOTE_EARLY）。
     本件出場為固定持有期（登錄照文獻、seq363；裁定 seq388 已核），無賣出訊號措辭；⛔ 不稱最高點、頂部（seq343）。
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
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
from backtest import researchPTH_freq as PT                 # noqa: E402  頻率表（⛔ 只 import）
from backtest import researchUO as UO                       # noqa: E402  x_stats、agg_eval、diff_stats、Sampler（⛔ 只 import）
from backtest import researchTurtle as TU                   # noqa: E402  NOTE_EARLY
from backtest import research11 as R                        # noqa: E402  load_bars、cl_stats
from backtest import evaluate as E                          # noqa: E402  COST
from backtest import universe_gate as UG                    # noqa: E402

UG.set_gate_v2(True)
assert UO.N_FAM == 1 and UO.Z95 == 1.96 and UO.NCTRL == 20

REG_SHA = PT.REG_SHA
OUT = "backtest/resultsPTH"
FREQ = PT.OUT
RERUN = "/tmp/pth_freq_rerun"
COST = E.COST
NCTRL = 20
SEED_CTRL, SEED_FAKE, SEED_BLOCK, SEED_TOP = 20261020, 20261021, 20261022, 20261023
REPS = 30
BOOT = 10_000
GAP_END = 5
HS = (3, 6, 12)
TAG = {"跳月": 0, "不跳": 1, "跳月_3月": 3, "跳月_12月": 12, "跳月_扣前30對照": 5, "後30%": 7, "跳月_最高10檔": 0}
SEGNUM = {"探索": 0, "確認": 1, "主全窗": 2, "早年": 3}
TYP = {1: "到期收盤", 2: "到期日無成交、用前一根收盤", 3: "壞根前一根收盤強制", 4: "末根收盤(之後無成交)", 5: "資料尾未出場"}
CELLS = {  # 名: (臂 L, H, 事件來源, RAW, 身分)
    "跳月": (2, 6, "SEL", None, "判定格"),
    "不跳": (1, 6, "SEL", None, "並報（⛔ 不擇優）"),
    "跳月_3月": (2, 3, "SEL", None, "描述（⛔ 不判、不計 N）"),
    "跳月_12月": (2, 12, "SEL", None, "描述（⛔ 不判、不計 N）"),
    "跳月_扣前30對照": (2, 6, "SEL", "SEL", "另一讀法（只報）"),
    "後30%": (2, 6, "BOT", None, "描述（⛔ 不判、不計 N）"),
}
NAME = {"跳月": "PTH 前 30%、跳 1 個月進場、抱 6 個月（判定格）", "不跳": "PTH 前 30%、不跳月進場、抱 6 個月（並報）",
        "跳月_3月": "跳月、抱 3 個月（描述）", "跳月_12月": "跳月、抱 12 個月（描述）", "跳月_扣前30對照": "另一讀法：對照扣掉同月全部前 30%（＝對其餘 70%）",
        "後30%": "PTH 後 30%（描述）", "跳月_最高10檔": "PTH 最高 10 檔（同值隨機；描述）"}
SENT_ALL = ["原文用拆股調整價、本件用含息還原價", "跳 1 個月為本線定，不跳月並報", "單筆層通過 ≠ 組合會贏 0050", "營量入選股多半本來就在 PTH 前 30%"]
SENT_BLOCK = "區塊 CI 較寬、結論不穩"
LOG: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M:%S")


def pct(x, d=2):
    return "—" if x is None or not np.isfinite(x) else "{:+.{}f}%".format(x * 100, d)


# ═════════════ 出場（R2；向量化，fixture 對逐根迴圈）═════════════
def nxt_bad(bad):
    nb = len(bad); BIG = nb + 10
    out = np.full(nb + 2, BIG, np.int64)
    pos = np.where(np.asarray(bad, bool), np.arange(nb), BIG)
    if nb:
        out[:nb] = np.minimum.accumulate(pos[::-1])[::-1]
    return out


def fixed_exit(ke, X, idx, c, bad, n0, delisted):
    """進場第 ke 根、到期日曆位置 X（X ＞ n0−1 ＝ 超出日曆）⇒ (eb, px, typ)。ke、X 為等長陣列。"""
    ke = np.asarray(ke, np.int64); X = np.asarray(X, np.int64)
    nb = len(idx)
    nbd = nxt_bad(bad)
    kb = nbd[np.minimum(ke + 1, nb + 1)]
    beyond = X > n0 - 1
    Xc = np.minimum(X, n0 - 1)
    kx = np.searchsorted(idx, Xc, "right") - 1
    lim = np.where(beyond, nb - 1, kx)
    forced = kb <= lim
    eb = np.full(len(ke), -1, np.int64); typ = np.zeros(len(ke), np.int8)
    eb[forced] = kb[forced] - 1; typ[forced] = 3
    a = ~forced & ~beyond
    eb[a] = kx[a]
    hit = np.zeros(len(ke), bool); hit[a] = idx[kx[a]] == X[a]
    last = np.zeros(len(ke), bool); last[a] = (kx[a] == nb - 1) & delisted
    typ[a & hit] = 1; typ[a & ~hit & last] = 4; typ[a & ~hit & ~last] = 2
    b = ~forced & beyond
    if delisted:
        eb[b] = nb - 1; typ[b] = 4
    else:
        typ[b] = 5
    px = np.where(eb >= 0, c[np.maximum(eb, 0)], np.nan)
    return eb, px, typ


def fixed_exit_loop(ke, X, idx, c, bad, n0, delisted):
    """逐根迴圈版（fixture／對帳用）。"""
    nb = len(idx); k = int(ke); end = min(int(X), n0 - 1)
    while k + 1 < nb and idx[k + 1] <= end:
        if bad[k + 1]:
            return k, c[k], 3
        k += 1
    if X <= n0 - 1:
        if idx[k] == X:
            return k, c[k], 1
        if k == nb - 1 and delisted:
            return k, c[k], 4
        return k, c[k], 2
    if k == nb - 1 and delisted:
        return k, c[k], 4
    return -1, np.nan, 5


# ═════════════ 統計小工具 ═════════════
def block_ci(x, mon, seed, B=BOOT):
    """R8：6 個曆月不重疊區塊重抽。mon ＝ 年×12＋月。"""
    x = np.asarray(x, float); mon = np.asarray(mon, np.int64)
    if len(x) == 0:
        return None
    blk = (mon - mon.min()) // 6
    nbk = int(blk.max()) + 1
    S = np.bincount(blk, weights=x, minlength=nbk); N = np.bincount(blk, minlength=nbk).astype(float)
    rng = np.random.default_rng(seed)
    pick = rng.integers(0, nbk, size=(B, nbk))
    m = S[pick].sum(1) / np.maximum(N[pick].sum(1), 1e-300)
    lo, hi = float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))
    rs = "結果①" if lo <= 0 <= hi else ("結果②" if lo > 0 else "結果③")
    return {"塊數": nbk, "每塊筆數中位": float(np.median(N)), "X̄": float(x.mean()), "lo": lo, "hi": hi, "結果": rs, "B": B}


def trade_stats(Rn, hold, typ):
    Rn = np.asarray(Rn, float)
    o = {}
    if len(Rn):
        w = Rn[Rn > 0]; l_ = Rn[Rn <= 0]
        o.update(淨報酬平均=float(Rn.mean()), 淨報酬中位=float(np.median(Rn)), 勝率=float((Rn > 0).mean()),
                 平均賺=float(w.mean()) if len(w) else None, 平均賠=float(l_.mean()) if len(l_) else None,
                 平均賺賠比=float(w.mean() / abs(l_.mean())) if len(w) and len(l_) and l_.mean() != 0 else None,
                 平均持有天數=float(np.mean(hold)), 持有天數中位=float(np.median(hold)))
        cnt = Counter(np.asarray(typ).tolist())
        for k_, nm in TYP.items():
            if k_ != 5:
                o[f"出場占比_{nm}"] = float(cnt.get(k_, 0) / len(Rn))
    return o


# ═════════════ 逐股 ═════════════
def stock_job(a):
    wn, sid = a
    W = PT._G[wn]; cal = W["cal"]; n0 = W["n0"]
    import backtest.data as D
    D.DATA = W["data"]
    B = R.load_bars(sid, W["mk"].get(sid, "twse"), cal)
    if B is None:
        return sid, None
    idx = B["idx"].astype(np.int64); nb = len(idx)
    o = np.asarray(B["o"], float); c = np.asarray(B["c"], float)
    bad = np.asarray(B["next_bad"][:nb] == np.arange(nb), bool)
    for p_ in W["BADPOS"].get(sid, ()):
        k = int(np.searchsorted(idx, p_, "left"))
        if k < nb:
            bad[k] = True
    delisted = bool((n0 - 1 - idx[-1]) >= GAP_END)
    posk = np.full(n0, -1, np.int64); posk[idx] = np.arange(nb)
    nm = len(W["ME"])
    out = {}
    for L in (1, 2):
        EP = W["EP"][L]
        ke = np.where(EP >= 0, posk[np.maximum(EP, 0)], -1)
        ok = ke >= 0
        with np.errstate(invalid="ignore"):
            ok &= np.where(ok, np.isfinite(o[np.maximum(ke, 0)]) & (o[np.maximum(ke, 0)] > 0), False)
        for H in HS:
            Rr = np.full(nm, np.nan); Ty = np.zeros(nm, np.int8); Sd = np.full(nm, -1, np.int64); Mt = np.full(nm, np.nan)
            if ok.any():
                jj = np.flatnonzero(ok)
                eb, px, typ = fixed_exit(ke[jj], W["XP"][(L, H)][jj], idx, c, bad, n0, delisted)
                o0 = o[ke[jj]]
                Rr[jj] = px / o0 - 1.0; Ty[jj] = typ; Sd[jj] = np.where(eb >= 0, idx[np.maximum(eb, 0)], -1)
                Mt[jj] = np.where(typ == 5, c[nb - 1] / o0 - 1.0, np.nan)
            out[(L, H)] = {"R": Rr, "T": Ty, "S": Sd, "M": Mt}
    return sid, out


# ═════════════ fixture ═════════════
def selftest():
    msgs = []
    rng = np.random.default_rng(11)
    nchk = 0
    for rep in range(400):
        nb = int(rng.integers(30, 160)); n0 = nb + int(rng.integers(0, 40))
        idx = np.sort(rng.choice(np.arange(n0), nb, replace=False))
        c = rng.uniform(10, 20, nb); bad = rng.random(nb) < 0.03
        delisted = bool((n0 - 1 - idx[-1]) >= GAP_END)
        ke = np.arange(nb)
        X = idx + rng.integers(0, 80, nb)
        eb, px, typ = fixed_exit(ke, X, idx, c, bad, n0, delisted)
        for q in range(nb):
            e2, p2, t2 = fixed_exit_loop(ke[q], X[q], idx, c, bad, n0, delisted)
            assert (eb[q], typ[q]) == (e2, t2), (rep, q, eb[q], typ[q], e2, t2)
            assert (np.isnan(px[q]) and np.isnan(p2)) or px[q] == p2
            nchk += 1
    msgs.append(f"F1 向量化固定持有出場 ＝ 逐根迴圈（隨機壞根、停牌、下市、資料尾；{nchk} 筆）")
    x = rng.normal(0, 1, 600); mon = rng.integers(0, 60, 600)
    b1 = block_ci(x, mon, 1); b2 = block_ci(x, mon, 1)
    assert b1 == b2 and abs(b1["X̄"] - x.mean()) < 1e-12 and b1["lo"] < x.mean() < b1["hi"]
    xc = np.full(600, 0.01); bc = block_ci(xc, mon, 2)
    assert abs(bc["lo"] - 0.01) < 1e-12 and abs(bc["hi"] - 0.01) < 1e-12
    msgs.append("F2 區塊重抽：同種子重現、常數序列 CI 退化為該常數、X̄ ＝ 全體平均")
    acc = np.zeros((300, 2)); key = rng.integers(0, 40, 600)
    np.add.at(acc[:, 0], key, 1.0); np.add.at(acc[:, 1], key, x)
    a_ = UO.agg_eval(acc); b_ = R.cl_stats(x, key)
    assert abs(a_["平均"] - b_["mean"]) < 1e-12 and abs(a_["lo"] - b_["lo"]) < 1e-12
    msgs.append("F3 假訊號分群彙總式 ＝ research11.cl_stats")
    for m in msgs:
        log("✅ " + m)
    return msgs


# ═════════════ 頻率表重跑比對（R1）═════════════
def rerun_freq():
    PT.OUT = RERUN
    argv = sys.argv
    sys.argv = ["researchPTH_freq", "--procs", "3"]
    try:
        PT.main()
    finally:
        sys.argv = argv
    res = {}
    for wn in ("主", "早年"):
        a = gzip.open(os.path.join(RERUN, f"events_{wn}.csv.gz")).read()
        b = gzip.open(os.path.join(FREQ, f"events_{wn}.csv.gz")).read()
        res[wn] = {"位元組": len(b), "相同": a == b}
        if a != b:
            raise SystemExit(f"⛔ {wn} 頻率表重跑 ≠ 已提交 events（{len(a)} vs {len(b)} bytes）⇒ 中止（未算任何報酬）")
    return res


def exit_positions(W):
    """XP[(L, H)][j] ＝ 進場月 M 起第 H 個曆月最後交易日的日曆位置；不在完整月內 ⇒ n0＋1。"""
    cal = W["cal"]; n0 = W["n0"]; ME = W["ME"]
    mp = {(int(cal[p].year), int(cal[p].month)): int(p) for p in ME}
    XP = {}
    for L in (1, 2):
        EP = W["EP"][L]
        for H in HS:
            out = np.full(len(ME), n0 + 1, np.int64)
            for j, e in enumerate(EP):
                if e < 0:
                    continue
                y, m = int(cal[e].year), int(cal[e].month)
                k = y * 12 + (m - 1) + (H - 1)
                out[j] = mp.get((k // 12, k % 12 + 1), n0 + 1)
            XP[(L, H)] = out
    return XP


def sentence(cell, st, blk=None, early=False):
    tail = list(SENT_ALL) + (TU.NOTE_EARLY if early else [])
    nm = NAME.get(cell, cell)
    rs = st["結果"]
    if rs == "樣本不足以分辨":
        s = f"{nm}：樣本不足以分辨（n_eff＝{st.get('n_eff', 0)}）"
    else:
        pre = "樣本中等（n_eff＝{}，介於 30 與 100 之間）：".format(st["n_eff"]) if st.get("出口") == "出口②" else ""
        if rs == "結果①":
            s = "{}{}：比同時隨便買分不出（X̄ {}，95% CI {} ～ {}）".format(pre, nm, pct(st["X̄"]), pct(st["lo"]), pct(st["hi"]))
        else:
            x2 = st.get("假訊號_x2", 0) or 0
            warn = "⚠ 隨機挑股票也有 {}／30 次同樣過關。".format(int(x2)) if (rs == "結果②" and x2 >= 2) else ""
            s = "{}{}{}：比同時隨便買{} {}（95% CI {} ～ {}）".format(warn, pre, nm, "多" if rs == "結果②" else "少", pct(abs(st["X̄"]))[1:],
                                                             pct(st["lo"]), pct(st["hi"]))
    if blk is not None and blk.get("結果") != rs:
        s += f"；{SENT_BLOCK}（區塊 CI {pct(blk['lo'])} ～ {pct(blk['hi'])}，{blk['結果']}）"
    return s + "｜" + "；".join(tail)


# ═════════════ 主程式 ═════════════
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    os.makedirs(os.path.join(OUT, "events"), exist_ok=True)
    reg = PT.reg_check()
    log(f"[登錄] {reg}（sha {REG_SHA} 已驗）｜本體開跑 {now_tpe()}")
    fx = selftest()
    rr = rerun_freq()
    log(f"[查核1] 頻率表重跑 ⇒ events 與已提交逐位元組相同：{rr}")
    fj = json.load(open(os.path.join(FREQ, "freq.json"), encoding="utf-8"))
    if a.dry:
        log("[乾跑] 完（未算任何報酬）")
        return
    J = {"性質": "接近 52 週新高 PTH seq1 事件層正式跑（判定格 跳月；探索判定、確認確認、主全窗參考、早年描述）",
         "登錄": f"台股策略線 seq1 sha {REG_SHA}", "裁定": "seq388 發號 N_前段 ＋1；seq390 核准正式跑（加 6 個月不重疊區塊 CI 描述格）",
         "成本": COST, "種子": {"對照": SEED_CTRL, "假訊號": SEED_FAKE, "區塊": SEED_BLOCK, "最高10檔同值": SEED_TOP},
         "Bonferroni": {"族N": UO.N_FAM, "z": UO.Z95}, "fixture": fx, "查核1_頻率表重跑": rr,
         "讀法_頻率表": PT.__doc__.split("═══ 讀法")[1], "讀法": __doc__.split("═══ 讀法")[1], "世界": {}, "時點": {"本體開跑": now_tpe()}}
    MAIN = []; BY = []; FK = []; BLK = []
    for wn in ("主", "早年"):
        W = PT._G[wn]; cal = W["cal"]; n0 = W["n0"]; ME = W["ME"]; nm = len(ME)
        W["XP"] = exit_positions(W)
        sids = W["sids"]; ix = W["ix"]; S = len(sids)
        # 事件檔 ⇒ 矩陣
        ev = pd.read_csv(os.path.join(FREQ, f"events_{wn}.csv.gz"), dtype={"sid": str})
        jmap = {str(cal[p].date()): j for j, p in enumerate(ME)}
        ev["j"] = ev["形成月底"].map(jmap).astype(int); ev["i"] = ev["sid"].map(ix).astype(int)
        U = np.zeros((nm, S), bool); SEL = np.zeros((nm, S), bool); BOT = np.zeros((nm, S), bool)
        KEEP = {1: np.zeros((nm, S), bool), 2: np.zeros((nm, S), bool)}; PTHm = np.full((nm, S), np.nan)
        jj, ii = ev["j"].to_numpy(), ev["i"].to_numpy()
        U[jj, ii] = True; SEL[jj, ii] = ev["入選"].to_numpy(bool); BOT[jj, ii] = ev["後30%"].to_numpy(bool); PTHm[jj, ii] = ev["PTH"].to_numpy(float)
        KEEP[2][jj, ii] = (ev["跳月_st"] == "保留").to_numpy(); KEEP[1][jj, ii] = (ev["不跳_st"] == "保留").to_numpy()
        # 逐股報酬
        Rm = {(L, H): np.full((nm, S), np.nan) for L in (1, 2) for H in HS}
        Tm = {k: np.zeros((nm, S), np.int8) for k in Rm}; Sm = {k: np.full((nm, S), -1, np.int64) for k in Rm}
        Mm = {k: np.full((nm, S), np.nan) for k in Rm}
        nok = 0
        with Pool(a.procs) as pool:
            for k_, (sid, r) in enumerate(pool.imap_unordered(stock_job, [(wn, s_) for s_ in sids], chunksize=8)):
                if r is not None:
                    nok += 1; i = ix[sid]
                    for kk, d in r.items():
                        Rm[kk][:, i] = d["R"]; Tm[kk][:, i] = d["T"]; Sm[kk][:, i] = d["S"]; Mm[kk][:, i] = d["M"]
                if (k_ + 1) % 500 == 0:
                    log(f"  {wn} … {k_ + 1}／{S}｜{time.time() - t0:.0f}s")
        if "第一次讀報酬" not in J["時點"]:
            J["時點"]["第一次讀報酬"] = now_tpe()
        log(f"[{wn}] 逐股完 {nok} 檔｜第一次讀報酬 {J['時點']['第一次讀報酬']}｜{time.time() - t0:.0f}s")
        # 查核2：事件必有進場價（保留 ⇒ e 有效 K 棒、開盤 ＞ 0）
        for L in (1, 2):
            miss = int((SEL & KEEP[L] & (Tm[(L, 6)] == 0)).sum())
            assert miss == 0, f"⛔ {wn} 臂 L={L}：保留事件 {miss} 筆無進場價"
        log("[查核2] 入選 ∧ 保留事件全部有進場還原開盤、有出場種類")
        crc = {s_: zlib.crc32(s_.encode("utf-8")) for s_ in sids}
        EPd = {L: W["EP"][L] for L in (1, 2)}
        moni_j = {L: np.array([int(cal[e].year) * 12 + int(cal[e].month) if e >= 0 else -1 for e in EPd[L]]) for L in (1, 2)}
        dates = np.array([str(d.date()) for d in cal])
        POOLS = {(L, H): U & KEEP[L] & np.isfinite(Rm[(L, H)]) for L in (1, 2) for H in HS}
        TR = {}
        for cname, (L, H, src, raw, role) in CELLS.items():
            evm = (SEL if src == "SEL" else BOT) & KEEP[L]
            smp = UO.Sampler(POOLS[(L, H)], SEL if raw == "SEL" else None)
            jj, ii = np.nonzero(evm)
            o_ = np.lexsort((ii, jj)); jj, ii = jj[o_], ii[o_]
            Rr = Rm[(L, H)][jj, ii]; ty = Tm[(L, H)][jj, ii]; sd = Sm[(L, H)][jj, ii]
            cm = np.full(len(jj), np.nan); cn = np.zeros(len(jj), np.int64); cids = []
            for q in range(len(jj)):
                j, i = int(jj[q]), int(ii[q])
                cs = smp.draw(j, i, [SEED_CTRL, TAG[cname], j, crc[sids[i]]])
                cn[q] = len(cs)
                if len(cs):
                    cm[q] = float(Rm[(L, H)][j, cs].mean())
                cids.append(";".join(sids[x] for x in cs) if cname == "跳月" else "")
            Xv = Rr - cm
            e_ = EPd[L][jj]
            fr = pd.DataFrame({"sid": [sids[x] for x in ii], "形成月底": dates[ME[jj]], "PTH": PTHm[jj, ii], "進場日": dates[e_],
                               "出場日": [dates[x] if x >= 0 else "" for x in sd], "出場種類": [TYP[int(x)] for x in ty],
                               "持有天數": np.where(sd >= 0, sd - e_, -1), "R": Rr, "R淨": Rr - COST, "帳面R(資料尾)": Mm[(L, H)][jj, ii],
                               "對照數": cn, "對照平均R": cm, "X": Xv, "種子格標": TAG[cname], "對照代號": cids})
            TR[cname] = {"fr": fr, "j": jj, "i": ii, "e": e_, "mon": moni_j[L][jj], "X": Xv, "R": Rr, "ty": ty, "H": np.where(sd >= 0, sd - e_, -1),
                         "cm": cm, "L": L}
            log(f"  [{wn}] {cname}：事件 {len(jj)}｜資料尾未出場 {int((ty == 5).sum())}｜無對照 {int((cn == 0).sum())}｜{time.time() - t0:.0f}s")
        # 最高 10 檔（跳月格子集）
        A0 = TR["跳月"]; okA = np.isfinite(A0["X"])
        top = np.zeros(len(A0["X"]), bool)
        for j in np.unique(A0["j"]):
            q = np.flatnonzero((A0["j"] == j) & okA)
            if len(q) == 0:
                continue
            rk = np.random.default_rng([SEED_TOP, int(j)]).random(len(q))
            o_ = np.lexsort((rk, -PTHm[j, A0["i"][q]]))
            top[q[o_[:10]]] = True
        A0["fr"]["最高10檔"] = top
        TR["跳月_最高10檔"] = {**{k: (v[top] if isinstance(v, np.ndarray) else v) for k, v in A0.items() if k != "fr"}, "fr": A0["fr"][top]}
        for cname, d_ in TR.items():
            if cname != "跳月_最高10檔":
                d_["fr"].to_csv(os.path.join(OUT, "events", f"trades_{wn}_{cname}.csv.gz"), index=False, compression={"method": "gzip", "compresslevel": 6})
        Wj = {"資料": W["data"], "日曆": [str(cal[0].date()), str(cal[-1].date())], "檔數": S, "可用檔數": nok, "段": {}, "格": {}}
        for sg, (x_, y_) in PT.SEGS[wn].items():
            p0 = int(cal.searchsorted(pd.Timestamp(x_)))
            p1 = n0 - 1 if y_ is None else int(cal.searchsorted(pd.Timestamp(y_), side="right")) - 1
            Wj["段"][sg] = f"{cal[p0].date()}～{cal[p1].date()}"
            yrs = (cal[p1] - cal[p0]).days / 365.25
            segj = {}
            for cname, d_ in TR.items():
                inseg = (d_["e"] >= p0) & (d_["e"] <= p1)
                okx = inseg & np.isfinite(d_["X"])
                st = UO.x_stats(d_["X"][okx], d_["mon"][okx])
                st["t"] = float(st["X̄"] / st["se"]) if st.get("se") else None
                st.update({"進場筆數(含未出場)": int(inseg.sum()), "資料尾未出場": int((inseg & (d_["ty"] == 5)).sum()),
                           "無對照剔除": int((inseg & np.isfinite(d_["R"]) & ~np.isfinite(d_["X"])).sum()),
                           "相異檔數": int(len(set(d_["i"][okx].tolist()))), "每年事件數": round(int(okx.sum()) / yrs, 1),
                           "R̄": float(d_["R"][okx].mean()) if okx.any() else None, "對照R̄": float(d_["cm"][okx].mean()) if okx.any() else None,
                           "每月事件中位": float(np.median(np.bincount(d_["j"][okx])[np.bincount(d_["j"][okx]) > 0])) if okx.any() else None})
                st.update(trade_stats(d_["R"][okx] - COST, d_["H"][okx], d_["ty"][okx]))
                yr = np.array([int(cal[e].year) for e in d_["e"][okx]])
                st["逐年"] = {str(y): {"n": int((yr == y).sum()), "X̄": float(d_["X"][okx][yr == y].mean())} for y in sorted(set(yr.tolist()))}
                for y, q in st["逐年"].items():
                    BY.append({"世界": wn, "段": sg, "格": cname, "年": y, **q})
                blk = None
                if cname in ("跳月", "不跳") and okx.any():
                    blk = block_ci(d_["X"][okx], d_["mon"][okx], [SEED_BLOCK, SEGNUM[sg], TAG[cname]])
                    st["區塊CI"] = blk
                    st["區塊CI與判定格同結果"] = bool(blk["結果"] == st["結果"])
                    BLK.append({"世界": wn, "段": sg, "格": cname, **blk, "判定格結果": st["結果"], "同": st["區塊CI與判定格同結果"]})
                if cname == "跳月" and okx.any():
                    # 假訊號臂
                    POOL = POOLS[(2, 6)]
                    js = [j for j in range(nm) if EPd[2][j] >= 0 and p0 <= EPd[2][j] <= p1]
                    smpf = UO.Sampler(POOL, None)
                    m0 = int(min(moni_j[2][j] for j in js))
                    acc = np.zeros((REPS, 400, 2)); cntf = np.zeros(REPS, np.int64)
                    for r_ in range(REPS):
                        for j in js:
                            cand = np.flatnonzero(POOL[j])
                            if len(cand) == 0:
                                continue
                            k = int(math.ceil(0.3 * len(cand)))
                            pick = np.sort(np.random.default_rng([SEED_FAKE + r_, j, SEGNUM[sg]]).choice(cand, size=k, replace=False))
                            cl = moni_j[2][j] - m0
                            for i in pick:
                                i = int(i)
                                cs = smpf.draw(j, i, [SEED_CTRL, 1000 + r_, j, crc[sids[i]]])
                                if len(cs) == 0:
                                    cntf[r_] += 1; continue
                                acc[r_, cl, 0] += 1.0; acc[r_, cl, 1] += Rm[(2, 6)][j, i] - Rm[(2, 6)][j, cs].mean()
                    res_ = [UO.agg_eval(acc[r_]) for r_ in range(REPS)]
                    st["假訊號_x2"] = sum(1 for q in res_ if q and q["結果"] == "結果②")
                    st["假訊號_x3"] = sum(1 for q in res_ if q and q["結果"] == "結果③")
                    st["假訊號_平均X"] = float(np.mean([q["平均"] for q in res_ if q]))
                    st["假訊號_每次筆數中位"] = float(np.median([q["n"] for q in res_ if q]))
                    for r_, q in enumerate(res_):
                        FK.append({"世界": wn, "段": sg, "r": r_, **({kk: q[kk] for kk in ("n", "平均", "lo", "hi", "n_eff", "出口", "結果")} if q else {"n": 0})})
                    st["過seq322門檻"] = bool(st["結果"] == "結果②" and st.get("bonf_lo", -1) > 0 and st["假訊號_x2"] <= 1 and st.get("X̄−成本", -1) > 0
                                          and st.get("逐月中位與平均同號", False))
                    st["seq322各條"] = {"結果②": st["結果"] == "結果②", "Bonferroni下界>0": bool(st.get("bonf_lo", -1) > 0),
                                      "假訊號x≤1": bool(st["假訊號_x2"] <= 1), "X̄−0.585%>0": bool(st.get("X̄−成本", -1) > 0),
                                      "逐月中位與平均同號": bool(st.get("逐月中位與平均同號", False)),
                                      "seq329§二 |t|≥1.96(族N=1)": bool(st.get("t") is not None and abs(st["t"]) >= 1.96)}
                if cname == "不跳":
                    A_ = TR["跳月"]; okA_ = (A_["e"] >= p0) & (A_["e"] <= p1) & np.isfinite(A_["X"])
                    st["不跳−跳月"] = UO.diff_stats(A_["X"][okA_], A_["mon"][okA_], d_["X"][okx], d_["mon"][okx])
                CEL = dict(CELLS); CEL["跳月_最高10檔"] = (2, 6, "", None, "描述（⛔ 不判、不計 N；組合層描述格的事件層版）")
                role = CEL[cname][4]
                if cname == "跳月":
                    role = "判定格｜" + {"探索": "判定段", "確認": "確認段", "主全窗": "參考", "早年": "早年描述"}[sg]
                st["身分"] = role
                st["句子"] = sentence(cname, st, blk=blk, early=(wn == "早年"))
                segj[cname] = st
                MAIN.append({"世界": wn, "段": sg, "格": cname, "說明": NAME[cname], "身分": role, "期間": Wj["段"][sg],
                             **{k: v for k, v in st.items() if not isinstance(v, dict) and k not in ("身分", "句子")},
                             "區塊CI結果": blk["結果"] if blk else None, "區塊lo": blk["lo"] if blk else None, "區塊hi": blk["hi"] if blk else None,
                             "句子": st["句子"]})
                log(f"  [{wn}/{sg}] {cname}：n={st['n']} n_eff={st.get('n_eff')} X̄={pct(st.get('X̄'))} CI {pct(st.get('lo'))}～{pct(st.get('hi'))} {st['結果']}"
                    + (f"｜區塊 {pct(blk['lo'])}～{pct(blk['hi'])} {blk['結果']}" if blk else "")
                    + (f"｜假 x={st.get('假訊號_x2')} seq322={st.get('過seq322門檻')}" if cname == "跳月" else "")
                    + (f"｜不跳−跳月 {pct(st['不跳−跳月'].get('差(D2−A)'))}（{pct(st['不跳−跳月'].get('lo'))}～{pct(st['不跳−跳月'].get('hi'))}）" if cname == "不跳" else "")
                    + f"｜{time.time() - t0:.0f}s")
            Wj["格"][sg] = segj
        J["世界"][wn] = Wj
        del Rm, Tm, Sm, Mm, POOLS, TR
    # ── 判定表、先驗、引自頻率表
    jd = {}
    for w, sg in (("主", "探索"), ("主", "確認"), ("主", "主全窗"), ("早年", "早年")):
        for cname in ("跳月", "不跳"):
            st = J["世界"][w]["格"][sg][cname]
            jd[f"{sg}_{cname}"] = {k: st.get(k) for k in ("身分", "結果", "出口", "n", "n_eff", "X̄", "lo", "hi", "t", "中位", "X̄−成本", "逐月平均之中位",
                                                       "假訊號_x2", "過seq322門檻", "勝率", "平均賺賠比", "R̄", "對照R̄", "資料尾未出場", "句子")}
            jd[f"{sg}_{cname}"]["區塊CI"] = st.get("區塊CI")
    J["判定"] = jd
    fz = fj["世界"]
    J["引自頻率表"] = {"PTH與12−1每月Spearman": {f"{w}/{sg}": fz[w]["段"][sg]["PTH與12−1每月Spearman"] for w, sg in (("主", "探索"), ("主", "確認"), ("主", "主全窗"), ("早年", "早年"))},
                   "重疊_營量營飆在PTH前30%比例": {f"{w}/{sg}": {k: fz[w]["段"][sg]["重疊(同月同檔,依t)"][k]["比例_對方在PTH前30%"] for k in ("營量v1", "營飆v1")}
                                          for w, sg in (("主", "探索"), ("主", "確認"), ("早年", "早年"))},
                   "seq377等價": {f"{w}/{sg}": fz[w]["段"][sg]["seq377等價_跳月vs不跳"] for w, sg in (("主", "探索"), ("主", "確認"), ("早年", "早年"))}}
    G = J["世界"]
    r1 = {sg: G["主"]["格"][sg]["跳月"]["結果"] for sg in ("探索", "確認")}
    sp = J["引自頻率表"]["PTH與12−1每月Spearman"]
    p3 = {f"{w}/{sg}": {"跳月X̄": G[w]["格"][sg]["跳月"]["X̄"], "不跳X̄": G[w]["格"][sg]["不跳"]["X̄"],
                        "差(不跳−跳月)": G[w]["格"][sg]["不跳"]["不跳−跳月"].get("差(D2−A)"),
                        "差CI": [G[w]["格"][sg]["不跳"]["不跳−跳月"].get("lo"), G[w]["格"][sg]["不跳"]["不跳−跳月"].get("hi")],
                        "中": bool(G[w]["格"][sg]["不跳"]["X̄"] < G[w]["格"][sg]["跳月"]["X̄"])}
          for w, sg in (("主", "探索"), ("主", "確認"), ("早年", "早年"))}
    J["先驗"] = {"①事件層兩段至少一段②": {"探索/確認": r1, "中": any(v == "結果②" for v in r1.values())},
                "②PTH與12−1相關中位≥0.6": {"中位": {k: v["中位"] for k, v in sp.items()}, "中": all(sp[k]["中位"] >= 0.6 for k in ("主/探索", "主/確認"))},
                "③不跳月X低於跳月": p3,
                "④早年X>0": {"早年X̄": G["早年"]["格"]["早年"]["跳月"]["X̄"], "中": bool(G["早年"]["格"]["早年"]["跳月"]["X̄"] > 0)}}
    J["N"] = {"本件判定格": 1, "並報／描述／另一讀法": "不計 N"}
    J["時點"]["完成"] = now_tpe()
    pd.DataFrame(MAIN).to_csv(os.path.join(OUT, "PTH_main.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(BLK).to_csv(os.path.join(OUT, "block_ci.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(BY).to_csv(os.path.join(OUT, "by_year.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(FK).to_csv(os.path.join(OUT, "fake_reps.csv"), index=False, encoding="utf-8-sig")
    json.dump(J, open(os.path.join(OUT, "PTH.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[判定] {json.dumps({k: {kk: v[kk] for kk in ('結果', 'n_eff', 'X̄', '假訊號_x2', '過seq322門檻')} for k, v in jd.items()}, ensure_ascii=False, default=float)}")
    log(f"[先驗] ①{J['先驗']['①事件層兩段至少一段②']['中']} ②{J['先驗']['②PTH與12−1相關中位≥0.6']['中']} ③{ {k: v['中'] for k, v in p3.items()} } ④{J['先驗']['④早年X>0']['中']}")
    log(f"完成 {time.time() - t0:.0f}s")
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
