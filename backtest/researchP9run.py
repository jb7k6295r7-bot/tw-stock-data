# -*- coding: utf-8 -*-
"""PREREGP9【分批進場與加減碼】12 格一次跑、一次交件（回測線計算助手，2026-09-25）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchP9run [--procs 2]

依據（逐字出處，⛔ 本檔不改任何規則）：
  登錄   台股策略線 PREREGP9 seq9（sha 868f99aeeba2fef3，13,568 B，2026-09-25 17:53）
  裁定   裁定線 seq162 §四（2-B 現金不足【不加、記次數】；出場＝第 120 根收盤；ⓑ 旗標建構器與 ē 對照先補；12 格一次跑；2-D 不跑）
         裁定線 seq167 §四（面板補 2026-04～08 量測日；加成中位 16／23／10.5 三格都不標；ē／m̄ 主版＝【逐種子配對】，中位、合計兩版描述；
                            讀法 1、2、4、5、6 收下）
  判準   裁定線 seq141（組合層新判準；主窗 2017-03-02～2026-08-24；0050 同窗 +24.0202%／−33.9570%，比值取未捨入值）
  引擎   research11.simulate_mtm（PREREGP9 seq8 §六 擴充，回測 1738 交件、seq162 收下）；旗標 p9_flags；對照 p9_controls；
         資料／窗／0050 錨 rerun17（edc6f8002f 快照＋主窗）；訊號 researchp7.build_sig_gate_b（resultsAFC 面板，S1 2,881 筆）
⛔ 本檔只 import，⛔ 不改 research11／p9_flags／p9_controls／p9_panel_ext／researchp9／researchp12／researchAFC／tradability／data。

═══ 臂（全部種子 default_rng(99000＋r)，r ∈ [0,200)，登錄 §一 寫死）═══
  基準臂  加減碼全關（登錄 §一：同引擎、edc6f8002f＋主窗重跑；⛔ 不沿用浮動窗 +27.69%）
  12 格   2-A k＝2／3｜2-B ⓐ +15%、ⓑ 120 日高點前三分位、ⓒ 滿 40 根仍為正｜2-C ⓐ −10% 賣半｜
          2-C ⓒ MA60 下新部位 1.5 slot、ⓓ MA20 下 0.5、ⓔ MA10 下 0.5｜2-C ⓕ／ⓖ／ⓗ MA60／20／10 跌破賣半、站回補回
  參照臂  ⓑ（0050＜MA60 ⇒ 新部位 0.5 slot）在主窗重跑（⛔ 不判、不計 N）
  對照臂  m̄（2-B 三格、ⓒⓓⓔ）、ē（ⓕⓖⓗ）：主版逐種子配對；中位、合計兩版描述；ē 另報 P17 兩向成本版（描述）
          同現金比例 × 0050（每一臂、每顆種子）：日報酬 ＝ 前一日持股比例 × 0050 日報酬（researchAFC 同式）
  假訊號臂（ⓒ～ⓗ，登錄 §四②）：線上／線下狀態以連續區段為單位打亂，30 次 × r ∈ [0,50)
  2-D     ⛔ 不跑（裁定 seq162 §四③：疊加規則沒訂）

═══ 引擎設定（＝ selftest_p9_builders.setup_real ＝ researchp9 基準臂 ＝ rerun17 main 格 0 的同一組；⭐ 開跑前閘三對 rerun17 驗）═══
  simulate_mtm(sig, "H120", 8, rng, closes, opens, ncal, return_equity=True, report_maxw=True[, audit])，其餘參數預設：
  pick=None、d_max=None、queue_days=0、cash_mode="zero"、tradable／delist 關（⛔ 與 AFC W1 不同：W1 開 tradable＋delist）
  價格 rerun17.load_prices(..., "branch")（快照、closes ffill float32）；0050 rerun17.load_bench；COST 0.585%（來回）
  sig 只留 entry_pos ∈ [w0, w1]（實測 2,881 筆全在窗內）；出場 H120 ＝ 進場後第 120 根收盤（xpos＝entry＋119）

═══ 判定（登錄 §三＋seq141；⛔ 看任何結果前寫死）═══
  判定值 ＝ 200 顆種子的【年化中位】、【回落中位】（＝ P9B_REPORT 取法）；比值 ＝ 年化中位 ÷ |回落中位|
  年化／回落／波動 ＝ rerun17.win_metrics（window_stats 以 eq[w0] 起算、2,313 日／245；波動 ＝ 窗內日報酬 sd(ddof=1)×√245）
  條件一 年化中位 ＞ 0050（嚴格）；條件二 比值 ≥ 0050 比值（0.24020209886370614 ÷ 0.3395700527611012，未捨入）
  ⇒ 合格／另列（只條件一）／不合格；合格但回落比 0050 深 ⇒ 附「深 x 點、多 y 點」
  年化÷波動 ＝ 年化中位 ÷ 波動中位（rerun17_table 同式；只描述）
  對照臂的甲'／乙'／丙'：格的（年化中位、比值）各與對照臂的同一量比，≥ 算不輸

═══ 讀法（登錄有兩種讀法、本檔選一種之處；⛔ 沒改規則；看結果前寫死）═══
  讀1  2-B ⓑ 旗標：flags ＝ p9_flags.build_flags(panel_ext)（resultsp9_engine/panel_ext.csv.gz，開跑前驗 sha256）；
       訊號仍由 resultsAFC/panel.csv.gz 建（panel_ext 只用來產 ⓑ 旗標，回測 1919）
  讀2  m̄ ＝ 實際成交倍數（p9_controls 讀法③ executed；seq167 §四 收下讀法 4）；m̄ ＞ 1 的對照走 ⓒ 的現金規則（只買 1 slot）
  讀3  ē ＝ 該格該顆種子在 [w0, w1] 的 hold_val ÷ equity 日平均；ē 對照成本＝引擎慣例（賣出付一次來回；seq167 收下讀法 5）
  讀4  「中位」版：該格 200 顆 m̄／ē 的中位，所有種子同一個數；「合計」版：m̄ ＝ Σ(m̄×新部位數)÷Σ新部位數、ē ＝ 200 顆平均
  讀5  假訊號臂打亂範圍 ＝ 狀態序列 below 的日曆位置 [w0−1, w1]（引擎在 t 開盤讀 below[t−1]，窗內交易日 t ∈ [w0, w1+…] 用到的就是這段；
       窗外不動）；線下段與線上段各自打亂順序、再照原本的交替與起始狀態接回 ⇒ 兩種段長分佈、段數、線下比例全保留；
       打亂的 rng ＝ default_rng(20260925＋j)，j ＝ 1..30（同 researchAFC 假訊號臂的種子起點）；同一 j 的 MA60 序列 ⓒ、ⓕ 共用
       判定值 ＝ 該次 50 顆（r ∈ [0,50)）的年化中位、回落中位，照同一判準 ⇒ x／30 合格；x／30 ≥ 5% ⇒ 結論句前加 ⚠
  讀6  同現金比例 × 0050：e[t] ＝ hold_val[t]／equity[t]（t ∈ [w0, w1]）；eqx[w0]＝1、eqx[t] ＝ eqx[t−1]×(1＋e[t−1]×r0050[t])；
       年化／回落用同一支 window_stats（2,313 日／245）⇒ ⚠ 與 researchAFC.path_desc 的 (w1−w0)/245 差一天的年數分母
  讀7  逐年報酬 ＝ 年末 ÷ 前一年末 − 1（首年 ÷ eq[w0]、2026 到 w1）；「去掉最好一年」＝ 其餘各年連乘，
       以其餘交易日數 ÷ 245 年化（⚠ 不是 researchAFC 那樣把首尾殘年當整年）；逐種子算、報中位
       三段區間報酬：2020-03（2020-02 月末 → 2020-03 月末）、2022（2021 年末 → 2022 年末）、2025-04（2025-03 月末 → 2025-04 月末）
  讀8  回落事件、分型、MA 跌破段：researchp9.dd_events／dd_type／window_mdd（seq5 §7-1 定義），MA20／MA10 的跌破段用與
       researchp9.ma_break_segments 同一式的通用版（MA60 時斷言逐段相同）；事件窗 ＝ 主窗 [w0, w1]
       「假警報」＝ 線下段長 ≤ 5 個交易日；「落後天數」＝ 事件高點 → 事件內 [高點, 回升] 第一個跌破段起日
       「訊號時 0050 已跌」：0050 自己的事件 ＝ 訊號日 ÷ 事件高點 − 1；組合事件 ＝ researchp9 同式（事件起點前 60 根內 0050 最高）
       §四⑤ 事件表 ＝ 基準臂中位種子（回落最接近 200 顆中位者，researchp9 同法）的 ≥20% 事件；各格用同一顆種子、同一個事件窗算「救到幾 pp」
       分型口徑 ＝ researchp9.dd_type 預設的 simple 報酬（＝ P9B_REPORT）；策略線 seq5 §7-2 的 ddtype.py 是 log 報酬 ⇒ 邊界附近會換型
       （⚠ 這一行是交件時補寫的：程式開跑時就是呼叫 dd_type 預設值，計算沒有改；報告 §八 另列 0050 事件的 log 口徑對照）
  讀9  ⓕⓖⓗ 每年多付成本 ＝ Σ（賣半當天付的成本 ＋ 補回金額 × COST（引擎於出場時才扣））÷ 前一日 equity，窗內合計 ÷ 窗年數 × 100（pp／年）
  讀10 A 窗／B 窗（seq5 §2-E②）＝ [w0, 2021-01 首日)／[2021-01 首日, w1]（research13.SPLIT）；只描述，⛔ 不判
  讀11 平均持股比例 ＝ 讀3 的 ē（每一臂都報）；平均持有天數：H120 固定出場、無停損、tradable 關 ⇒ 依構造每筆 120 根（不另算）
  讀12 2-B「實際加成次數」＝ 引擎 x_add_n；「現金不足」＝ x_add_short（登錄：不加、記次數）；中位 ≤ 2 ⇒ 標【結構上近乎不可得】
       結論句「現金不足次數是加成的 x 倍」的 x ＝ 各格 現金不足中位 ÷ 加成中位（三格取最小～最大）

═══ 開跑前閘（任何一道不過 ⇒ 停）═══
  閘一 0050 主窗年化、回落 repr 逐位元 ＝ 0.24020209886370614／−0.3395700527611012
  閘二 panel_ext.csv.gz sha256 ＝ d75bf50b…0788
  閘三 同一支引擎設定換 rerun17 的種子（102000＋r，r<200）⇒ 年化／回落／波動與 resultsN17/seeds_main.csv 格 0（P12 策略側 W1 描述）逐位元同
═══ 查核 ═══
  決定性：基準臂 200 顆重跑第二次 ⇒ equity sha256 與三數逐位元同
  獨立重算：backtest/researchP9run_check.py（⛔ 不 import 本檔）從逐種子檔重算每格中位、比值、標籤
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import rerun17 as RR
from . import research11 as R
from . import research13 as R13
from . import p9_flags as F
from . import p9_controls as C
from . import researchp9 as P9

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsP9run")
SEED0, REPS = 99000, 200
N_MAIN, RULE = 8, "H120"
ANCHOR = (0.24020209886370614, -0.3395700527611012)
PANEL_SIG = os.path.join(HERE, "resultsAFC", "panel.csv.gz")
PANEL_EXT = os.path.join(HERE, "resultsp9_engine", "panel_ext.csv.gz")
PANEL_EXT_SHA = "d75bf50baae15ed0445219a6f8003f166d65a6ce93b930d729a789fc364e0788"
RR17_SEED0 = 102000
FAKE_SEED0, N_FAKE, FAKE_REPS = 20260925, 30, 50
FALSE_ALARM = 5
PERIODS = {"2020-03": ("2020-02", "2020-03"), "2022": ("2021-12", "2022-12"), "2025-04": ("2025-03", "2025-04")}

# (鍵, 族, 名稱, 是否判定、計 N)
CELLS = [
    ("base", "基準", "基準臂（加減碼全關）", False),
    ("A2", "2-A", "分批進場 k＝2", True),
    ("A3", "2-A", "分批進場 k＝3", True),
    ("Ba", "2-B", "ⓐ 收盤 ≥ 進場 +15% ⇒ 加 0.5 slot", True),
    ("Bb", "2-B", "ⓑ 貼近 120 日高點三分位 ⇒ 加 0.5 slot", True),
    ("Bc", "2-B", "ⓒ 持有滿 40 根仍為正 ⇒ 加 0.5 slot", True),
    ("Ca", "2-C", "ⓐ 個股 −10% ⇒ 賣一半", True),
    ("Cc", "2-C", "ⓒ 0050＜MA60 ⇒ 新部位 1.5 slot（跌破加碼）", True),
    ("Cd", "2-C", "ⓓ 0050＜MA20 ⇒ 新部位 0.5 slot", True),
    ("Ce", "2-C", "ⓔ 0050＜MA10 ⇒ 新部位 0.5 slot", True),
    ("Cf", "2-C", "ⓕ 0050 跌破 MA60 ⇒ 手上各賣一半、站回補回", True),
    ("Cg", "2-C", "ⓖ 0050 跌破 MA20 ⇒ 手上各賣一半、站回補回", True),
    ("Ch", "2-C", "ⓗ 0050 跌破 MA10 ⇒ 手上各賣一半、站回補回", True),
    ("Cb_ref", "參照", "ⓑ 0050＜MA60 ⇒ 新部位 0.5 slot（主窗參照，⛔ 不判、不計 N）", False),
]
KEYS = [c[0] for c in CELLS]
NAME = {c[0]: c[2] for c in CELLS}
FAM = {c[0]: c[1] for c in CELLS}
JUDGED = [c[0] for c in CELLS if c[3]]
MA_OF = {"Cc": 60, "Cd": 20, "Ce": 10, "Cf": 60, "Cg": 20, "Ch": 10, "Cb_ref": 60}
MULT_OF = {"Cc": 1.5, "Cd": 0.5, "Ce": 0.5, "Cb_ref": 0.5}
MBAR_CELLS = ["Ba", "Bb", "Bc", "Cc", "Cd", "Ce"]
EBAR_CELLS = ["Cf", "Cg", "Ch"]
FAKE_CELLS = ["Cc", "Cd", "Ce", "Cf", "Cg", "Ch"]
_G: dict = {}


# ═════════════ 小工具 ═════════════
def sha(a) -> str:
    return hashlib.sha256(np.asarray(a, float).tobytes()).hexdigest()


def label(c, m):
    """seq141：回 (標籤, 比值, 附註)。"""
    c50, m50 = _G["c50"], _G["m50"]
    ratio = c / abs(m); r50 = c50 / abs(m50)
    k1 = c > c50; k2 = ratio >= r50
    lab = "合格" if (k1 and k2) else ("另列" if k1 else "不合格")
    extra = ""
    if lab == "合格" and m < m50:
        extra = f"回落比 0050 深 {(m50 - m) * 100:.2f} 點、報酬多 {(c - c50) * 100:.2f} 點"
    return lab, ratio, extra


def engine_kw(key, below=None):
    if key == "base":
        return {}
    if key in ("A2", "A3"):
        return {"entry_tranches": int(key[1])}
    if key == "Ba":
        return {"add_rule": {"kind": "gain", "x": 0.15}}
    if key == "Bb":
        return {"add_rule": {"kind": "flag", "flags": _G["flags"]}}
    if key == "Bc":
        return {"add_rule": {"kind": "hold", "days": 40}}
    if key == "Ca":
        return {"trim_rule": {"x": 0.10, "frac": 0.5}}
    bl = _G["below"][MA_OF[key]] if below is None else below
    if key in MULT_OF:
        return {"size_mult_by_regime": {"mult": MULT_OF[key], "below": bl}}
    return {"regime_trim": {"hold": 0.5, "below": bl}}


def sim(kw, seed, audit=None):
    return R.simulate_mtm(_G["sig"], RULE, N_MAIN, np.random.default_rng(seed), _G["closes"], _G["opens"], _G["ncal"],
                          return_equity=True, report_maxw=True, audit=audit, **kw)


def ma_segments(below_raw, lo, hi):
    """[lo, hi] 內 below_raw 為真的每一段：(起日, 段長)；起日 ＝ 前一日不在線下（researchp9.ma_break_segments 同一式）。"""
    segs = []; t = lo
    while t <= hi:
        if below_raw[t] and (t == 0 or not below_raw[t - 1]):
            u = t
            while u <= hi and below_raw[u]:
                u += 1
            segs.append((t, u - t)); t = u
        else:
            t += 1
    return segs


def shuffle_state(full, lo, hi, rng):
    """讀5：[lo, hi] 的線上／線下段各自打亂順序，照原交替與起始狀態接回。"""
    seg = np.asarray(full[lo:hi + 1], bool)
    runs = []; i = 0; n = len(seg)
    while i < n:
        j = i
        while j < n and seg[j] == seg[i]:
            j += 1
        runs.append((bool(seg[i]), j - i)); i = j
    s0 = runs[0][0]
    Lt = np.array([l for s, l in runs if s], int); Lf = np.array([l for s, l in runs if not s], int)
    Lt = Lt[rng.permutation(len(Lt))]; Lf = Lf[rng.permutation(len(Lf))]
    it, jf = 0, 0; st = s0; new = []
    for _ in range(len(runs)):
        if st:
            new += [True] * int(Lt[it]); it += 1
        else:
            new += [False] * int(Lf[jf]); jf += 1
        st = not st
    out = np.asarray(full, bool).copy(); out[lo:hi + 1] = np.array(new, bool)
    assert out[lo:hi + 1].sum() == seg.sum() and len(new) == len(seg)
    return out


# ═════════════ 單一路徑的量測 ═════════════
def measure(o):
    eq, hv, first, end = o["equity"], o["hold_val"], o["first"], o["end"]
    w0, w1, sp = _G["w0"], _G["w1"], _G["split"]
    c, m, v = RR.win_metrics(eq, first, end, w0, w1)
    lo, hi = min(first, w0), max(end, w1 + 1)
    ca, ma = R13.window_stats(eq, lo, hi, w0, sp)
    cb, mb = R13.window_stats(eq, lo, hi, sp, w1 + 1)
    e = hv[w0:w1 + 1] / eq[w0:w1 + 1]
    eqx = np.r_[1.0, np.cumprod(1.0 + e[:-1] * _G["r50"])]
    xc, xm = R13.window_stats(eqx, 0, len(eqx), 0, len(eqx))
    d = {"cagr": float(c), "mdd": float(m), "vol": float(v), "ca": float(ca), "ma": float(ma), "cb": float(cb), "mb": float(mb),
         "expo": C.ebar_of(eq, hv, w0, w1), "x50_cagr": float(xc), "x50_mdd": float(xm), "x50_vol": RR.ann_vol(eqx),
         "trades": int(o["trades"]), "slot": float(o["slot_use"]), "maxw": float(o["max_pos_frac"]),
         "first": int(first), "end": int(end), "eq_sha": sha(eq)}
    yr = {}
    for y, p0, p1 in _G["years"]:
        yr[y] = float(eq[p1] / eq[p0] - 1.0)
        d[f"y{y}"] = yr[y]
    best = max(yr, key=yr.get)
    days_best = [p1 - p0 for y, p0, p1 in _G["years"] if y == best][0]
    rest = np.prod([1.0 + r for y, r in yr.items() if y != best])
    d["drop_best_year"] = int(best)
    d["drop_best_geo"] = float(rest ** (245.0 / (w1 - w0 - days_best)) - 1.0)
    for k, (p0, p1) in _G["periods"].items():
        d[f"p{k}"] = float(eq[p1] / eq[p0] - 1.0)
    ev = P9.dd_events(eq, w0, w1 + 1)
    for kind in ("單日暴跌型", "延續下跌型", "混合型"):
        d[f"dd_{kind}"] = 0
    for e_ in ev:
        k, _, _ = P9.dd_type(eq, e_["peak"], e_["trough"])
        d[f"dd_{k}"] += 1
    d["dd_n"] = len(ev)
    for k_, v_ in o.items():
        if k_.startswith("x_") and k_ != "x_cost_days":
            d[k_] = float(v_)
    return d


def rt_costs(o, au):
    eq = o["equity"]; w0, w1 = _G["w0"], _G["w1"]
    yrs = (w1 + 1 - w0) / 245
    s_sell = sum(v / eq[t - 1] for t, v in o.get("x_cost_days", []) if w0 <= t <= w1)
    s_ref = 0.0
    for a in au:
        if a.get("kind") == "rt_refill" and w0 <= a["t"] <= w1:
            s_ref += a["amt"] * R.COST / eq[a["t"] - 1]
    return {"rt_cost_sell_pp_yr": s_sell / yrs * 100, "rt_cost_refill_pp_yr": s_ref / yrs * 100,
            "rt_cost_pp_yr": (s_sell + s_ref) / yrs * 100}


# ═════════════ workers ═════════════
def _arm(args):
    key, r = args
    seed = SEED0 + r
    au = [] if key in EBAR_CELLS else None
    o = sim(engine_kw(key), seed, audit=au)
    row = {"arm": key, "r": r, "seed": seed, **measure(o)}
    if key in EBAR_CELLS:
        row.update(rt_costs(o, au))
    if key in ("Ba", "Bb", "Bc"):
        row["mbar"] = C.mbar_of(o, "add")
        row["mbar_nominal"] = C.mbar_of(o, "add", reading="nominal")
    elif key in ("Cc", "Cd", "Ce", "Cb_ref"):
        row["mbar"] = C.mbar_of(o, "mult", mult=MULT_OF[key])
        row["mbar_nominal"] = C.mbar_of(o, "mult", mult=MULT_OF[key], reading="nominal")
    return row


def _rr17(r):
    o = sim({}, RR17_SEED0 + r)
    c, m, v = RR.win_metrics(o["equity"], o["first"], o["end"], _G["w0"], _G["w1"])
    return {"r": r, "seed": RR17_SEED0 + r, "cagr": float(c), "mdd": float(m), "vol": float(v)}


def _mbar_ctrl(args):
    key, version, r, mb = args
    o = sim(C.mbar_kwargs(mb, _G["ncal"]), SEED0 + r)
    c, m, v = RR.win_metrics(o["equity"], o["first"], o["end"], _G["w0"], _G["w1"])
    return {"cell": key, "kind": "mbar", "version": version, "r": r, "seed": SEED0 + r, "param": float(mb),
            "cagr": float(c), "mdd": float(m), "vol": float(v), "expo": C.ebar_of(o["equity"], o["hold_val"], _G["w0"], _G["w1"]),
            "x_mult_short": float(o.get("x_mult_short", 0))}


def _ebar_ctrl(args):
    """一顆種子：基準臂跑一次（audit），再合成 ⓕⓖⓗ 各版本的 ē 對照。jobs ＝ [(cell, version, ē, cost_mode)…]"""
    r, jobs = args
    au = []
    o = sim({}, SEED0 + r, audit=au)
    out = []
    for key, version, eb, cm in jobs:
        res = C.ebar_control(o["equity"], o["hold_val"], au, _G["cal"], _G["w0"], _G["w1"], eb, cost_mode=cm)
        c, m, v = RR.win_metrics(res["V"], o["first"], o["end"], _G["w0"], _G["w1"])
        out.append({"cell": key, "kind": "ebar", "version": version, "r": r, "seed": SEED0 + r, "param": float(eb),
                    "cagr": float(c), "mdd": float(m), "vol": float(v), "expo": float(res["ebar_realized"]),
                    "n_rebal": int(res["n_rebal"]), "ctrl_cost_total": float(res["cost"].sum())})
    return out


def _fake(args):
    key, j, r = args
    bl = _G["fake"][(MA_OF[key], j)]
    o = sim(engine_kw(key, below=bl), SEED0 + r)
    c, m, v = RR.win_metrics(o["equity"], o["first"], o["end"], _G["w0"], _G["w1"])
    return {"cell": key, "j": j, "r": r, "seed": SEED0 + r, "cagr": float(c), "mdd": float(m), "vol": float(v)}


# ═════════════ 設定 ═════════════
def setup(log):
    RR.use_snapshot()
    from . import data as D
    from . import p4_features as P4F
    from . import researchp7 as P7
    cal = D.load_calendar(); ncal = len(cal)
    w0, w1 = RR.win_bounds(cal)
    uni = D.load_universe().set_index("stock_id")["market"]
    panel = P4F.read_panel(PANEL_SIG)
    closes, opens = RR.load_prices(set(panel["stock_id"]), cal, uni, "branch")
    sig = P7.build_sig_gate_b(panel, cal, closes, opens, start="2017-01-01", signal="B")
    e = sig["entry_pos"].to_numpy()
    n_all = len(sig)
    sig = sig[(e >= w0) & (e <= w1)].reset_index(drop=True)
    bench = RR.load_bench(cal)
    split = int(cal.searchsorted(pd.Timestamp(R13.SPLIT + "-01")))
    ym = pd.DatetimeIndex(cal).strftime("%Y-%m"); yy = pd.DatetimeIndex(cal).year
    last_of_month = {}
    for i in range(w0 - 40, w1 + 1):
        last_of_month[ym[i]] = i
    years = []; prev = w0
    for y in range(int(yy[w0]), int(yy[w1]) + 1):
        idx = [i for i in range(w0, w1 + 1) if yy[i] == y]
        years.append((y, prev, idx[-1])); prev = idx[-1]
    periods = {k: (last_of_month[a], last_of_month[b]) for k, (a, b) in PERIODS.items()}
    below = {n: R.regime_below(bench, n) for n in (60, 20, 10)}
    info = {"data": D.DATA, "calendar": f"{ncal} 根 {cal[0].date()}～{cal[-1].date()}", "w0": [w0, str(cal[w0].date())],
            "w1": [w1, str(cal[w1].date())], "split": [split, str(cal[split].date())], "panel_sig": PANEL_SIG,
            "sig": {"建出": n_all, "窗內": len(sig), "檔": int(sig["sid"].nunique()), "月": int(sig["month"].nunique()),
                    "accept": P7.accept_sig_b(sig)}, "COST": R.COST}
    _G.update(cal=cal, ncal=ncal, w0=w0, w1=w1, split=split, uni=uni, panel=panel, closes=closes, opens=opens, sig=sig,
              bench=bench, below=below, years=years, periods=periods,
              r50=bench[w0 + 1:w1 + 1] / bench[w0:w1] - 1.0)
    log(f"[設定] {json.dumps(info, ensure_ascii=False, default=str)}")
    return info


# ═════════════ 主流程 ═════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=2)
    ap.add_argument("--smoke", action="store_true", help="只給試跑程式路徑用：4 顆種子、假訊號 2×2，輸出到 --out")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    global OUT, REPS, N_FAKE, FAKE_REPS
    if a.out:
        OUT = a.out
    if a.smoke:
        REPS, N_FAKE, FAKE_REPS = 4, 2, 2
        if not a.out:
            raise SystemExit("--smoke 要配 --out（不寫進 resultsP9run）")
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "a", encoding="utf-8")
    T0 = time.time()

    def log(x):
        x = f"[{time.time() - T0:6.0f}s] {x}"
        print(x, flush=True); logf.write(x + "\n"); logf.flush()

    log(f"===== researchP9run {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）=====")
    S = {"開跑": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M"), "閘": {}}
    if abs(R.COST - 0.00585) > 1e-15:
        raise SystemExit(f"⛔ COST {R.COST} ≠ 0.585%")
    S["設定"] = setup(log)
    cal, w0, w1, bench = _G["cal"], _G["w0"], _G["w1"], _G["bench"]

    # ── 閘一 0050 錨
    bw = RR.bench_row(cal, bench, w0, w1 + 1)
    ok1 = repr(bw["cagr"]) == repr(ANCHOR[0]) and repr(bw["mdd"]) == repr(ANCHOR[1])
    log(f"[閘一] 0050 主窗 年化 {bw['cagr']!r}／回落 {bw['mdd']!r}／波動 {bw['vol']!r} ⇒ 逐位元 {ok1}")
    S["閘"]["一_0050錨"] = {"年化": bw["cagr"], "回落": bw["mdd"], "波動": bw["vol"], "逐位元": ok1}
    if not ok1:
        raise SystemExit("⛔ 閘一不過")
    _G.update(c50=bw["cagr"], m50=bw["mdd"], v50=bw["vol"])
    b_a = RR.bench_row(cal, bench, w0, _G["split"]); b_b = RR.bench_row(cal, bench, _G["split"], w1 + 1)
    S["0050"] = {"主窗": bw, "比值": bw["cagr"] / abs(bw["mdd"]), "年化÷波動": bw["cagr"] / bw["vol"], "A窗": b_a, "B窗": b_b}
    beq = bench / bench[w0]
    S["0050"]["逐年"] = {int(y): float(beq[p1] / beq[p0] - 1) for y, p0, p1 in _G["years"]}
    S["0050"]["區間"] = {k: float(beq[p1] / beq[p0] - 1) for k, (p0, p1) in _G["periods"].items()}

    # ── 閘二 panel_ext sha
    h = hashlib.sha256(open(PANEL_EXT, "rb").read()).hexdigest()
    ok2 = h == PANEL_EXT_SHA
    log(f"[閘二] panel_ext sha256 {h} ⇒ {'✅ 相同' if ok2 else '⛔ 不同'}")
    S["閘"]["二_panel_ext"] = {"sha256": h, "位元組": os.path.getsize(PANEL_EXT), "相同": ok2}
    if not ok2:
        raise SystemExit("⛔ 閘二不過")
    from . import p4_features as P4F
    pext = P4F.read_panel(PANEL_EXT)
    _G["flags"] = F.build_flags(pext, cal, sids=set(_G["sig"]["sid"]))
    fs = F.flag_summary(_G["flags"], w0, w1 + 1)
    S["旗標"] = {**fs, "panel_ext 量測日": f"{pext['measure_date'].min().date()}～{pext['measure_date'].max().date()}"}
    log(f"[ⓑ 旗標] {S['旗標']}")
    del pext
    # 假訊號狀態序列
    fake = {}; fk_info = {}
    for n in (60, 20, 10):
        orig = _G["below"][n]
        for j in range(1, N_FAKE + 1):
            fake[(n, j)] = shuffle_state(orig, w0 - 1, w1, np.random.default_rng(FAKE_SEED0 + j))
        fk_info[n] = {"線下天數（[w0−1,w1]）": int(orig[w0 - 1:w1 + 1].sum()),
                      "打亂後都相同": all(int(fake[(n, j)][w0 - 1:w1 + 1].sum()) == int(orig[w0 - 1:w1 + 1].sum()) for j in range(1, N_FAKE + 1)),
                      "窗外不動": all((fake[(n, j)][:w0 - 1] == orig[:w0 - 1]).all() and (fake[(n, j)][w1 + 1:] == orig[w1 + 1:]).all() for j in range(1, N_FAKE + 1)),
                      "與原序列不同的次數": sum(int((fake[(n, j)] != orig).any()) for j in range(1, N_FAKE + 1))}
    _G["fake"] = fake
    S["假訊號序列"] = fk_info
    log(f"[假訊號序列] {fk_info}")

    with Pool(a.procs) as pool:
        # ── 閘三 rerun17 對照
        rr = pd.DataFrame(pool.map(_rr17, range(REPS), chunksize=10))
        ref = pd.read_csv(os.path.join(HERE, "resultsN17", "seeds_main.csv"), float_precision="round_trip")
        ref = ref[(ref["stage"] == "main") & (ref["cell"] == 0)].set_index("r").sort_index()
        mm = rr.set_index("r").sort_index()
        same = {k: bool(all(repr(x) == repr(y) for x, y in zip(mm[k], ref.loc[mm.index, k]))) for k in ("cagr", "mdd", "vol")}
        seeds_same = bool((mm["seed"].to_numpy() == ref.loc[mm.index, "seed"].to_numpy()).all())
        diff = {k: float((mm[k] - ref.loc[mm.index, k]).abs().max()) for k in ("cagr", "mdd", "vol")}
        ok3 = all(same.values()) and seeds_same and len(mm) == REPS and len(ref) == 200
        afc = json.load(open(os.path.join(HERE, "resultsAFC", "summary.json"), encoding="utf-8"))["W1"]
        S["閘"]["三_rerun17"] = {"對象": "resultsN17/seeds_main.csv 格 0（P12 策略側 W1 描述：H120、N8、pick None、cash zero、無 tradable／delist、種子 102000＋r）",
                               "顆數": REPS, "逐位元": same, "種子相同": seeds_same, "最大絕對差": diff, "過": ok3,
                               "本件年化中位": float(mm["cagr"].median()), "本件回落中位": float(mm["mdd"].median()),
                               "AFC_W1_200顆（開 tradable＋delist）": {"年化中位": afc["200顆年化中位"], "回落中位": afc["200顆回落中位"]},
                               "與AFC差": {"年化中位": float(mm["cagr"].median() - afc["200顆年化中位"]), "回落中位": float(mm["mdd"].median() - afc["200顆回落中位"])}}
        log(f"[閘三] {json.dumps(S['閘']['三_rerun17'], ensure_ascii=False)}")
        rr.to_csv(os.path.join(OUT, "gate3_rerun17_seeds.csv"), index=False)
        if not ok3:
            raise SystemExit("⛔ 閘三不過")

        # ── 主臂（基準＋12 格＋參照）
        jobs = [(k, r) for k in KEYS for r in range(REPS)]
        A = pd.DataFrame(pool.map(_arm, jobs, chunksize=10))
        A.to_csv(os.path.join(OUT, "seeds_arms.csv"), index=False)
        log(f"[主臂] {len(A):,} 列 ⇒ seeds_arms.csv")

        # ── 決定性：基準臂第二次
        B2 = pd.DataFrame(pool.map(_arm, [("base", r) for r in range(REPS)], chunksize=10))
        b1 = A[A["arm"] == "base"].set_index("r").sort_index(); b2 = B2.set_index("r").sort_index()
        det = {"equity_sha": bool((b1["eq_sha"] == b2["eq_sha"]).all()),
               **{k: bool(all(repr(x) == repr(y) for x, y in zip(b1[k], b2[k]))) for k in ("cagr", "mdd", "vol")}}
        S["查核_決定性"] = det
        log(f"[決定性] 基準臂 200 顆重跑 ⇒ {det}")

        # ── m̄ 對照
        mj = []
        mb_info = {}
        for k in MBAR_CELLS:
            g = A[A["arm"] == k].set_index("r").sort_index()
            med_ = C.cell_value(g["mbar"], "median")
            pooled = C.cell_value(g["mbar"], "pooled", weights=g["x_new_n"])
            mb_info[k] = {"逐種子中位": float(g["mbar"].median()), "p10": float(g["mbar"].quantile(.1)), "p90": float(g["mbar"].quantile(.9)),
                          "中位版": med_, "合計版": pooled}
            for r in range(REPS):
                mj.append((k, "paired", r, float(g.loc[r, "mbar"])))
                mj.append((k, "median", r, med_))
                mj.append((k, "pooled", r, pooled))
        M = pd.DataFrame(pool.map(_mbar_ctrl, mj, chunksize=10))
        log(f"[m̄ 對照] {len(M):,} 列")
        # ── ē 對照
        eb_info = {}; ejobs = {r: [] for r in range(REPS)}
        for k in EBAR_CELLS:
            g = A[A["arm"] == k].set_index("r").sort_index()
            med_ = float(np.median(g["expo"])); pooled = float(np.mean(g["expo"]))
            eb_info[k] = {"逐種子中位": med_, "p10": float(g["expo"].quantile(.1)), "p90": float(g["expo"].quantile(.9)),
                          "中位版": med_, "合計版": pooled}
            for r in range(REPS):
                ejobs[r] += [(k, "paired", float(g.loc[r, "expo"]), "engine"), (k, "median", med_, "engine"),
                             (k, "pooled", pooled, "engine"), (k, "paired_p17", float(g.loc[r, "expo"]), "p17")]
        E = pd.DataFrame([x for y in pool.map(_ebar_ctrl, [(r, ejobs[r]) for r in range(REPS)], chunksize=5) for x in y])
        CT = pd.concat([M, E], ignore_index=True)
        CT.to_csv(os.path.join(OUT, "seeds_controls.csv"), index=False)
        S["m̄"] = mb_info; S["ē"] = eb_info
        log(f"[ē 對照] {len(E):,} 列 ⇒ seeds_controls.csv")

        # ── 假訊號臂
        fj = [(k, j, r) for k in FAKE_CELLS for j in range(1, N_FAKE + 1) for r in range(FAKE_REPS)]
        FK = pd.DataFrame(pool.map(_fake, fj, chunksize=25))
        FK.to_csv(os.path.join(OUT, "seeds_fake.csv"), index=False)
        log(f"[假訊號臂] {len(FK):,} 列 ⇒ seeds_fake.csv")

    # ═════════ 彙總 ═════════
    base = A[A["arm"] == "base"].set_index("r").sort_index()
    rows = []
    for k in KEYS:
        g = A[A["arm"] == k].set_index("r").sort_index()
        c, m, v = float(g["cagr"].median()), float(g["mdd"].median()), float(g["vol"].median())
        lab, ratio, extra = label(c, m)
        row = {"arm": k, "族": FAM[k], "格": NAME[k], "判定": k in JUDGED, "cagr": c, "mdd": m, "ratio": ratio, "vol": v,
               "cagr_per_vol": c / v, "label": lab if k in JUDGED else "", "label_desc": lab, "deep_note": extra,
               "cagr_p10": float(g["cagr"].quantile(.1)), "cagr_p90": float(g["cagr"].quantile(.9)),
               "mdd_p10": float(g["mdd"].quantile(.1)), "mdd_p90": float(g["mdd"].quantile(.9)),
               "cond1": c > _G["c50"], "cond2": ratio >= _G["c50"] / abs(_G["m50"])}
        per = [label(x, y)[0] for x, y in zip(g["cagr"], g["mdd"])]
        row["seed_Q_share"] = float(np.mean([p == "合格" for p in per])); row["seed_R_share"] = float(np.mean([p == "另列" for p in per]))
        dc = g["cagr"] - base["cagr"]; dm = g["mdd"] - base["mdd"]
        row.update({"d_cagr_med": float(dc.median()), "d_cagr_p10": float(dc.quantile(.1)), "d_cagr_p90": float(dc.quantile(.9)),
                    "d_mdd_med": float(dm.median()), "d_mdd_p10": float(dm.quantile(.1)), "d_mdd_p90": float(dm.quantile(.9)),
                    "d_cagr_pos": float((dc > 0).mean()), "d_mdd_pos": float((dm > 0).mean())})
        for q in ("ca", "ma", "cb", "mb", "expo", "x50_cagr", "x50_mdd", "x50_vol", "trades", "slot", "maxw", "dd_n",
                  "dd_單日暴跌型", "dd_延續下跌型", "dd_混合型", "drop_best_geo", "p2020-03", "p2022", "p2025-04"):
            row[q] = float(g[q].median())
        row["maxw_worst"] = float(g["maxw"].max())
        row["x50_ratio"] = row["x50_cagr"] / abs(row["x50_mdd"])
        row["x50_label"] = label(row["x50_cagr"], row["x50_mdd"])[0]
        for y, _, _ in _G["years"]:
            row[f"y{y}"] = float(g[f"y{y}"].median())
        for q in [c_ for c_ in g.columns if c_.startswith("x_") or c_.startswith("rt_cost") or c_.startswith("mbar")]:
            x = g[q].astype(float)
            row[f"{q}_med"] = float(x.median()); row[f"{q}_p10"] = float(x.quantile(.1)); row[f"{q}_p90"] = float(x.quantile(.9))
            row[f"{q}_min"] = float(x.min()); row[f"{q}_max"] = float(x.max())
        rows.append(row)
    TB = pd.DataFrame(rows)

    # 對照臂比較
    ctrl_rows = []
    for k in MBAR_CELLS + EBAR_CELLS:
        cell = TB[TB["arm"] == k].iloc[0]
        g_cell = A[A["arm"] == k].set_index("r").sort_index()
        for ver in (["paired", "median", "pooled"] + (["paired_p17"] if k in EBAR_CELLS else [])):
            g = CT[(CT["cell"] == k) & (CT["version"] == ver)].set_index("r").sort_index()
            c, m, v = float(g["cagr"].median()), float(g["mdd"].median()), float(g["vol"].median())
            ratio = c / abs(m)
            w_c = cell["cagr"] >= c; w_r = cell["ratio"] >= ratio
            cls = "甲'" if (w_c and w_r) else ("乙'" if (w_c or w_r) else "丙'")
            dc = g_cell["cagr"] - g["cagr"]; dm = g_cell["mdd"] - g["mdd"]
            ctrl_rows.append({"cell": k, "kind": "m̄" if k in MBAR_CELLS else "ē", "version": ver,
                              "param_med": float(g["param"].median()), "cagr": c, "mdd": m, "ratio": ratio, "vol": v,
                              "label_desc": label(c, m)[0], "cell_cagr": cell["cagr"], "cell_ratio": cell["ratio"],
                              "cell_not_lose_cagr": bool(w_c), "cell_not_lose_ratio": bool(w_r), "class": cls,
                              "pair_d_cagr_med": float(dc.median()), "pair_d_mdd_med": float(dm.median()),
                              "expo_med": float(g["expo"].median())})
    CTB = pd.DataFrame(ctrl_rows)

    # 假訊號
    fk_rows = []
    for k in FAKE_CELLS:
        labs = []
        for j in range(1, N_FAKE + 1):
            g = FK[(FK["cell"] == k) & (FK["j"] == j)]
            c, m = float(g["cagr"].median()), float(g["mdd"].median())
            labs.append((j, c, m, label(c, m)[0]))
        g0 = A[(A["arm"] == k) & (A["r"] < FAKE_REPS)]
        c0, m0 = float(g0["cagr"].median()), float(g0["mdd"].median())
        nQ = sum(l == "合格" for *_, l in labs); nR = sum(l == "另列" for *_, l in labs)
        fk_rows.append({"cell": k, "x_Q": nQ, "x_R": nR, "n": N_FAKE, "warn": nQ / N_FAKE >= 0.05,
                        "fake_cagr_med": float(np.median([c for _, c, _, _ in labs])), "fake_mdd_med": float(np.median([m for _, _, m, _ in labs])),
                        "real50_cagr": c0, "real50_mdd": m0, "real50_label": label(c0, m0)[0],
                        "real_cagr_rank（≤它的次數）": int(sum(c <= c0 for _, c, _, _ in labs)),
                        "real_mdd_rank（≤它的次數）": int(sum(m <= m0 for _, _, m, _ in labs))})
    FKT = pd.DataFrame(fk_rows)

    # ── §四④ 各 MA 的狀態描述 ＋ 0050 自己的回落事件
    reg = {}
    bq = bench / bench[w0]
    ev50 = P9.dd_events(bq, w0, w1 + 1)
    for n in (60, 20, 10):
        raw = _G["below"][n]
        segs = ma_segments(raw, w0, w1)
        if n == 60:
            assert segs == P9.ma_break_segments(bench, w0, w1), "⛔ MA60 跌破段與 researchp9 不同"
        L = np.array([l for _, l in segs])
        ev_rows = []
        for e_ in ev50:
            k_, p2, p5 = P9.dd_type(bq, e_["peak"], e_["trough"])
            s_ = [s for s in ma_segments(raw, e_["peak"], e_["recover"])]
            sp_ = s_[0][0] if s_ else None
            ev_rows.append({"高點": str(cal[e_["peak"]].date()), "谷底": str(cal[e_["trough"]].date()), "跌幅": e_["dd"], "分型": k_,
                            "訊號": str(cal[sp_].date()) if sp_ is not None else "", "落後": (sp_ - e_["peak"]) if sp_ is not None else None,
                            "已跌": float(bq[sp_] / bq[e_["peak"]] - 1) if sp_ is not None else None,
                            "已跌占全段": float((bq[sp_] / bq[e_["peak"]] - 1) / e_["dd"]) if sp_ is not None else None})
        reg[n] = {"跌破段數": len(segs), "假警報（≤5日翻回）": int((L <= FALSE_ALARM).sum()),
                  "段長 p25/p50/p75/p90": [float(np.percentile(L, q)) for q in (25, 50, 75, 90)],
                  "線下天數": int(raw[w0:w1 + 1].sum()), "線下占比": float(raw[w0:w1 + 1].mean()), "0050事件": ev_rows}
    S["§四④"] = reg

    # ── §四⑤ 事件逐筆（基準臂中位種子）
    med_mdd = base["mdd"].median()
    bs = A[A["arm"] == "base"].sort_values("seed")
    med_seed = int(bs.iloc[(bs["mdd"] - med_mdd).abs().to_numpy().argsort(kind="stable")[0]]["seed"])
    eqs = {k: sim(engine_kw(k), med_seed)["equity"] for k in KEYS}
    eb = eqs["base"]
    ev_rows = []
    for e_ in P9.dd_events(eb, w0, w1 + 1):
        kind, p2, p5 = P9.dd_type(eb, e_["peak"], e_["trough"])
        lo, hi = e_["peak"], e_["recover"]
        bpk = float(np.max(bench[max(lo - 60, 0):lo + 1]))
        row = {"seed": med_seed, "高點": str(cal[lo].date()), "谷底": str(cal[e_["trough"]].date()), "回升": str(cal[hi].date()),
               "回升了": e_["recovered"], "日數": hi - lo, "基準回落": e_["dd"], "分型": kind, "最差2日占比": p2}
        for n in (60, 20, 10):
            s_ = ma_segments(_G["below"][n], lo, hi)
            sp_ = s_[0][0] if s_ else None
            row[f"MA{n}_首跌破"] = str(cal[sp_].date()) if sp_ is not None else ""
            row[f"MA{n}_落後"] = (sp_ - lo) if sp_ is not None else None
            row[f"MA{n}_0050已跌"] = float(bench[sp_] / bpk - 1) if sp_ is not None else None
            row[f"MA{n}_組合已跌"] = float(eb[sp_] / eb[lo] - 1) if sp_ is not None else None
            row[f"MA{n}_段數"] = len(s_); row[f"MA{n}_線下日"] = int(sum(l for _, l in s_))
        wb = P9.window_mdd(eb, lo, hi)
        row["窗內回落_基準"] = wb
        for k in KEYS:
            if k != "base":
                row[f"救到pp_{k}"] = (P9.window_mdd(eqs[k], lo, hi) - wb) * 100
        ev_rows.append(row)
    EV = pd.DataFrame(ev_rows)
    EV.to_csv(os.path.join(OUT, "events.csv"), index=False)
    S["§四⑤"] = {"中位種子": med_seed, "事件數": len(EV)}

    # ── §2-E⑤ 狀態月 vs 母體負報酬月（兩個方向）
    MU = P9.month_universe_returns(_G["panel"], cal, _G["closes"])
    mu = MU.set_index("ym")["ret"]
    sig = _G["sig"]
    ent = sig.groupby("month")["entry_pos"].agg(["min", "max"])
    one = bool((ent["min"] == ent["max"]).all())
    ov = {"每月只有一個進場日": one}
    for n in (60, 20, 10):
        wk = pd.Series({m: bool(_G["below"][n][int(p) - 1]) for m, p in ent["min"].items()})
        common = [m for m in wk.index if m in mu.index]
        w_ = wk.loc[common]; neg = mu.loc[common] < 0; inter = int((w_ & neg).sum())
        ov[f"MA{n}"] = {"共同月": len(common), "線下月": int(w_.sum()), "負報酬月": int(neg.sum()), "交集": inter,
                        "精確率": inter / int(w_.sum()) if w_.sum() else None, "涵蓋率": inter / int(neg.sum()) if neg.sum() else None}
    S["§2-E⑤"] = ov

    TB.to_csv(os.path.join(OUT, "cells.csv"), index=False)
    CTB.to_csv(os.path.join(OUT, "controls.csv"), index=False)
    FKT.to_csv(os.path.join(OUT, "fake.csv"), index=False)
    S["years"] = [[int(y), int(p0), int(p1), str(cal[p0].date()), str(cal[p1].date())] for y, p0, p1 in _G["years"]]
    S["periods"] = {k: [str(cal[p0].date()), str(cal[p1].date())] for k, (p0, p1) in _G["periods"].items()}
    S["N帳"] = {"N_組合": "+12（登錄 §八）", "不計": "基準臂、ⓑ 參照臂、m̄／ē 對照臂、同現金比例×0050、假訊號臂、2-D（未跑）"}
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log("[彙總] cells.csv／controls.csv／fake.csv／events.csv／summary.json")
    log("[完成] 報告另由 python -m backtest.researchP9run_report 產生（只讀本資料夾的檔）")


if __name__ == "__main__":
    sys.exit(main())
