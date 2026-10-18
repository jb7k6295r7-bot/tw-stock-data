# -*- coding: utf-8 -*-
"""Mass Index 反轉凸起 seq1【事件層正式跑】（台股策略線 單筆層登錄 sha 356f3ccfda10a90f，2026-10-18 13:28；裁定 seq374、375 發號；
N_前段 ＋1）——回測線計算子代理。
⛔ 不 commit、不改既有程式與結果夾；researchMI_freq（MI、EMA9、凸起、方向、剔除；讀法 G1～G7 寫死、沿用）、researchBB（sim 收盤判模式 'm'）、
   researchWR_freq（base、段、reg_check）、researchUO（Sampler、x_stats（族 N＝1）、agg_eval、diff_stats）、researchTurtle（NOTE_EARLY）、
   researchAscTri_freq、research11 ⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMI [--procs 3]
    乾跑（⛔ 不算任何出場、報酬；只驗事件重現與對照池）：... -m backtest.researchMI --dry [--limit 200]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMI_check
輸出 backtest/resultsMI/（⛔ 不碰 freq/）：MI.json、MI_main.csv（判定表＋描述）、MI_desc.csv（固定天數描述）、by_year.csv、fake_reps.csv、
    events/trades_<世界>_<格>.csv.gz（逐筆進出、對照、X）、run.log

格：A ＝ 判定格；描述（⛔ 不判、不計 N）：D1_26（完成門檻 26.0）、D2_無方向（不加方向條件）、D3（A 同進場、固定抱 20／60 日）、假訊號臂（30 次隨機日當 T）。
    ⛔ 出場無固定天數（登錄 §二；seq308）。

═══ 讀法（Q 標；頻率表 G1～G7 原樣沿用（世界、母體、壞根、EMA 起始、MI、凸起、方向、剔除、段），以下為正式跑新增；
     ⛔ 在讀任何本件報酬之前寫死；★＝執行者定，〔 〕內為另一讀法）═══
 Q1 事件 ＝ 逐股呼叫 researchMI_freq.stock_job 原樣；⭐ 依頻率表寫法排成表、與已提交的 resultsMI/freq/events_<世界>.csv.gz 逐列逐欄比
    （A、D1_26、D2_無方向），任一不同 ⇒ 中止、⛔ 不算報酬。進場候選 ＝ 狀態「保留」者；進場 ＝ T＋1 開盤（還原開盤 o[k＋1]，登錄 §二）。
 Q2 出場（登錄 §二，⭐ 本線定；條件出場、⛔ 無固定天數）：持有中第 j 根收盤 ＜ EMA9c[j] ∧ EMA9c[j] ＜ EMA9c[j−1]（價格與均線同時轉弱；兩者嚴格）
    ⇒ 第 j＋1 根（下一根有效 K 棒）開盤賣（開盤缺 ⇒ 該根收盤並計數）。★「進場後第 1 根起就判」＝ j ≥ 進場根 s（含進場當天收盤；
    開盤買在當日收盤之前；researchUO E2、researchBB H5 同）〔另一讀法 j ≥ s＋1——不採〕。EMA9c ＝ 頻率表 G2 同一支（同段、SMA 起始）。
    實作 ＝ researchBB.sim 收盤判模式 'm'（c[j] ＜ LV[j] ⇒ 下一根開盤）原樣呼叫（⛔ 不 patch、不複製），LV[j] ＝ EMA9c[j] 若 EMA9c[j] ＜ EMA9c[j−1]、
    否則 −1e300（永不觸發）⇒ c[j] ＜ LV[j] ⇔ Q2 兩條同時成立（fixture F1 對本檔逐根迴圈驗）。
    ⚠ 代數：EMA9c[j] ＝ EMA9c[j−1] ＋ 0.2（c[j] − EMA9c[j−1]）⇒ c[j] ＜ EMA9c[j] ⇔ EMA9c[j] ＜ EMA9c[j−1]（段內 SMA 起始那根除外）⇒ 兩條實際上是
    同一件事（fixture F2b 驗）；照登錄兩條都寫進程式，結果等同「收盤跌破 EMA9」。頻率表 G4 方向條件同理 ⇔ c[T] ＜ EMA9c[T]（在讀報酬前發現、照記，⛔ 不改登錄）。
    「出場訊號」措辭照 seq343：「均線轉弱出場訊號」；⛔ 不稱最高點、頂部。
 Q3 鎖死跌停順延、壞根、下市、資料尾 ＝ researchBB H6、H7 原樣（sim 內建）：賣出根開盤鎖死跌停（W.DNL）⇒ 順延到其後第一根非鎖死有效 K 棒開盤
    （開盤缺 ⇒ 收盤）；持有中下一根是壞 K 棒 ⇒ 前一根還原收盤強制（訊號在第 j 根、第 j＋1 根就是壞 K 棒 ⇒ 第 j 根收盤強制）；之後再無成交且
    最後一根距資料尾 ≥ 5 交易日 ⇒ 末根收盤（下市）；否則「資料尾未出場」：照實報件數與帳面報酬，⛔ 不進 X。
    seq373「同根兩出場價都碰到取較低」：本件出場只有一個收盤判條件 ⇒ 不涉及（計數恆 0，照記）。
 Q4 R ＝ 出場價 ÷ 進場還原開盤 − 1；淨 ＝ R − 0.585%；X ＝ R − 對照平均 R（兩邊同扣成本）。持有天數 ＝ 出場日 − 進場日（日曆位置差）。
 Q5 持有中不重複進場（登錄 §二）：同檔保留事件依 T 排序，前筆賣出日 S（日曆位置）；★ 新事件需 T ≥ S（T＋1 開盤買在賣出日之後；researchUO E5 同）
    〔另一讀法 T ＞ S〕；前筆資料尾未出場 ⇒ 之後全略。整個世界時序上套；各格用自己的事件各自套。
 Q6 對照（登錄 §三）：同一天 T、同母體隨機 20 檔、T＋1 開盤進場、同出場規則（各用自己的 EMA9c）。池 ＝ Frame.gate[T] ∧ pit_valid[T] ∧ T 非壞 K 棒
    ∧ T＋1 可買（下一根 ＝ 日曆 T＋1、非壞、有成交、開盤有值 ＞ 0、非開盤鎖漲停 ＝ G5 同旗標）∧ EMA9c[T] 有值（出場要用）∧ R 可算。
    ★ 扣事件股自己與 T 當天同格【原始】偵測到的股票（任何狀態；researchUO E6、researchDMI Q10 同）；不放回抽 20 檔（不足 ⇒ 全取、計數）；
    等權；⛔ 對照不套持有限制。種子 default_rng([20261018, 格標, T, crc32(sid)])；格標 A＝1、D1_26＝2、D2_無方向＝3、D3_H20＝20、D3_H60＝60。
 Q7 判定量 X̄；CI ＝ T 所在曆月分群（research11.cl_stats）、1.96；n_eff ＝ min(可算筆數, 有事件曆月數)；n_eff ＜ 30 ⇒ 依構造不可判定、
    30～99 ⇒ 句首「樣本中等」；結果② ＝ CI 不含 0 且 X̄ ＞ 0、③ ＝ X̄ ＜ 0 且 CI 不含 0、① ＝ 含 0。判定段：探索、確認【各自報】為準（登錄 §三）；
    主全窗參考；早年 2005～2014 描述（附 reduce_v2 約 0.3% 註）。Bonferroni 族 N＝1 ⇒ z ＝ 1.96（researchUO.x_stats 同式）。
 Q8 seq322（researchUO E9 同式）＝ 結果② ∧ Bonferroni 下界 ＞ 0 ∧ 假訊號 x ≤ 1 ∧ X̄ − 0.585% ＞ 0 ∧ 逐月 X 平均之中位數與 X̄ 同號；各段各報（只 A）。
 Q9 假訊號臂（researchUO E10 同式）：只做 A；r ＝ 0…29；每檔每段 n ＝ 該檔 A 可算筆數；可抽日 ＝ 該檔在段內且在 Q6 對照池；排除「存在該檔 A 保留事件
    T_r ∈ [T−20, T]」；不放回抽 n 天（不足 ⇒ 全取、計數）；假事件 R ＝ 對照式 R（T＋1 開盤進場、同出場）；對照照 Q6（扣自己與 T 當天 A 原始偵測）；
    種子 default_rng([20261019＋r, crc32(sid), 段序號])，假事件的對照 [20261018, 5100＋r, T, crc32(sid)]；x／30 ＝ 落結果② 的次數。⛔ 不套持有限制。
 Q10 描述（⛔ 不判、不計 N）：D1_26、D2_無方向 同 Q2～Q7 全套；另報 X̄(D2) − X̄(A)、X̄(D1) − X̄(A)（researchUO.diff_stats，曆月分群線性化）。
     D3 ＝ A 的同一批進場（Q5 後），R_H ＝ ffill 還原收盤(T＋H) ÷ 還原開盤(T＋1) − 1；(T＋1, T＋H] 有壞 K 棒或 T＋H 落在 ≥ 5 日缺口 ⇒ 不可算
     （researchUO D3／researchBB 同式）；對照 ＝ Q6 母體 ∧ R_H 可算、同法抽 20 檔。⛔ 只描述，不當出場比較基準（seq308）。
 Q11 必報：凸起數、方向保留比例（頻率表口徑，引自 freq.json）、每年事件數（可算筆 ÷ 段長；另附頻率表上限）、n_eff、平均／中位／p90 持有天數、
     出場種類占比（分母 ＝ 可算筆，另報含資料尾）、勝率（淨報酬 ＞ 0）、平均賺賠比（賺錢筆平均淨報酬 ÷ |賠錢筆平均淨報酬|）、假訊號 x／30、seq322。
 Q12 結果句必附：「原作為 1992 轉錄、非逐字」「方向條件來自二手網站範例，非原作」「出場由本線定」「單筆層通過 ≠ 組合會贏 0050」；
     早年另附 reduce_v2 與上櫃版面註（researchTurtle NOTE_EARLY）。
 Q13 先驗（登錄 §五，寫下不改）：① 判定格兩段都落結果①；② 方向條件保留 40～60% 的凸起（頻率表口徑，各段各報）；③ 平均持有 ＜ 10 天（A 各段各報）。
"""
from __future__ import annotations

import argparse
import io
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
from backtest import researchMI_freq as MF                  # noqa: E402  事件偵測、MI、EMA9c（⛔ 只 import）
from backtest import researchBB as BB                       # noqa: E402  sim（收盤判模式 'm'）（⛔ 只 import）
from backtest import researchWR_freq as WF                  # noqa: E402  base、SEGS、reg_check（⛔ 只 import）
from backtest import researchUO as UO                       # noqa: E402  Sampler、x_stats、agg_eval、diff_stats（⛔ 只 import）
from backtest import researchTurtle as TU                   # noqa: E402  NOTE_EARLY
from backtest import researchAscTri_freq as AT              # noqa: E402  load_world 原樣
from backtest import research11 as R                        # noqa: E402  cl_stats
from backtest import evaluate as E                          # noqa: E402  COST
from backtest import universe_gate as UG                    # noqa: E402

UG.set_gate_v2(True)

REG_SHA = MF.REG_SHA
OUT = "backtest/resultsMI"
FREQ = MF.OUT
NO_BAND = -1e300
SEED_CTRL, SEED_FAKE = 20261018, 20261019
REPS, EXCL = 30, 20
HD3 = (20, 60)
N_FAM = 1
assert UO.N_FAM == N_FAM and UO.NCTRL == 20 and UO.Z95 == 1.96
COST = E.COST
TAIL = BB.TAIL
GAP_END = BB.GAP_END
assert TAIL == 6 and GAP_END == 5
TYP = {3: "均線轉弱出場訊號(收盤<EMA9且EMA9下彎)", 4: "壞根前一根收盤強制", 5: "末根收盤(下市/之後無成交)", 6: "資料尾未出場"}
assert all(BB.TYP[k] == v for k, v in TYP.items() if k != 3) and BB.TYP[3] == "跌破中軌出場訊號"
CELLS = ("A", "D1_26", "D2_無方向")
TAG = {"A": 1, "D1_26": 2, "D2_無方向": 3, "D3_H20": 20, "D3_H60": 60}
SEGNUM = {"探索": 0, "確認": 1, "主全窗": 2, "早年": 3}
JUDGE = ("A",)
NAME = {"A": "Mass Index 反轉凸起（升破 27 後跌回 26.5、當日 9 日均線向下；隔天開盤買、收盤跌破且均線下彎隔天開盤賣）",
        "D1_26": "D1 描述：凸起完成門檻改 26.0", "D2_無方向": "D2 描述：不加方向條件（凸起完成就做多）"}
SENT_SRC = "原作為 1992 轉錄、非逐字"
SENT_DIR = "方向條件來自二手網站範例，非原作"
SENT_EXIT = "出場由本線定"
SENT_ALL = "單筆層通過 ≠ 組合會贏 0050"
NOTE_EARLY = TU.NOTE_EARLY
LOG: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M:%S")


def pct(x, d=2):
    return "—" if x is None or not np.isfinite(x) else "{:+.{}f}%".format(x * 100, d)


# ═════════════ Q2 出場 ═════════════
def exit_band(EC):
    """LV[j] ＝ EMA9c[j]（當 EMA9c[j] ＜ EMA9c[j−1]）否則 −1e300 ⇒ researchBB.sim 'm'：c[j] ＜ LV[j] ⇔ 收盤 ＜ EMA9 ∧ EMA9 下彎。"""
    LV = np.full(len(EC), NO_BAND)
    with np.errstate(invalid="ignore"):
        dn = np.zeros(len(EC), bool); dn[1:] = np.isfinite(EC[1:]) & np.isfinite(EC[:-1]) & (EC[1:] < EC[:-1])
    LV[dn] = EC[dn]
    return LV


def sim_mi(o, h, l, c, bad, dnlb, idx, n0, S, EC):
    S = np.asarray(S, np.int64)
    return BB.sim(o, h, l, c, bad, dnlb, idx, n0, S, np.zeros(len(S)), exit_band(EC), "m")


def exit_ref(o, c, EC, bad, dnlb, idx, n0, s):
    """逐根迴圈（fixture／對帳用，⛔ 不呼叫 researchBB）：回 (eb, px, typ, post, obad)。"""
    nb = len(c); delisted = (n0 - 1 - idx[-1]) >= GAP_END

    def endp():
        return (nb - 1, c[nb - 1], 5) if delisted else (-1, np.nan, TAIL)

    def opx(y):
        ok = np.isfinite(o[y]) and o[y] > 0
        return (o[y] if ok else c[y]), (not ok)
    j = s
    while True:
        if j >= nb:
            e = endp(); return e[0], e[1], e[2], False, False
        if j > s and bad[j]:
            return j - 1, c[j - 1], 4, False, False
        sig = np.isfinite(EC[j]) and np.isfinite(EC[j - 1]) and EC[j] < EC[j - 1] and c[j] < EC[j]
        if sig:
            if j + 1 >= nb:
                e = (j, c[j], 5) if delisted else (-1, np.nan, TAIL)
                return e[0], e[1], e[2], False, False
            if bad[j + 1]:
                return j, c[j], 4, False, False
            y = j + 1
            if dnlb[y]:
                while y < nb:
                    if bad[y]:
                        return y - 1, c[y - 1], 4, True, False
                    if not dnlb[y]:
                        p, ob = opx(y); return y, p, 3, True, ob
                    y += 1
                e = endp(); return e[0], e[1], e[2], True, False
            p, ob = opx(y)
            return y, p, 3, False, ob
        j += 1


# ═════════════ fixture ═════════════
def selftest():
    msgs = []
    rng = np.random.default_rng(13)
    nchk = 0; nsig = 0; npost = 0
    for rep in range(300):
        nb = int(rng.integers(60, 260)); n0 = nb + int(rng.integers(0, 12))
        c = 50 * np.exp(np.cumsum(rng.normal(0.0, 0.025, nb)))
        h = c * (1 + rng.uniform(0, 0.04, nb)); l = c * (1 - rng.uniform(0, 0.04, nb))
        o = l + (h - l) * rng.uniform(0, 1, nb)
        o[rng.random(nb) < 0.03] = np.nan
        bad = rng.random(nb) < 0.02; bad[0] = True
        dnlb = rng.random(nb) < 0.06
        idx = np.sort(rng.choice(np.arange(n0), nb, replace=False))
        _, EC, *_ = MF.indicators(h, l, c, bad)
        cand = np.array([k + 1 for k in range(nb - 1) if np.isfinite(EC[k]) and not bad[k + 1]], np.int64)
        if not len(cand):
            continue
        r = sim_mi(o, h, l, c, bad, dnlb, idx, n0, cand, EC)
        for q, s in enumerate(cand):
            e2 = exit_ref(o, c, EC, bad, dnlb, idx, n0, int(s))
            assert (r["eb"][q], r["typ"][q], r["post"][q], r["obad"][q]) == (e2[0], e2[2], e2[3], e2[4]), (rep, s, r["eb"][q], r["typ"][q], e2)
            assert (np.isnan(r["px"][q]) and np.isnan(e2[1])) or abs(r["px"][q] - e2[1]) < 1e-12
            assert not r["both"][q]
            nchk += 1; nsig += int(e2[2] == 3); npost += int(e2[3])
    msgs.append(f"F1 researchBB.sim('m') 配 LV ＝ 下彎時的 EMA9c ＝ 本檔逐根迴圈（收盤＜EMA9 ∧ EMA9 下彎、含進場當天收盤、鎖死跌停順延、壞根、"
                f"缺開盤、下市／資料尾；{nchk} 筆，其中訊號出場 {nsig}、順延 {npost}；同根皆觸恆 0）")
    # F2 手算小例：EMA9c 平、收盤一路上 ⇒ 不出；第 j 根收盤跌破且 EMA 下彎 ⇒ j＋1 開盤；收盤跌破但 EMA 仍上彎 ⇒ 不出
    n = 40
    c = np.r_[np.linspace(10, 14, 30), [13.0, 12.0, 11.0, 10.0, 9.0, 9.0, 9.0, 9.0, 9.0, 9.0]]
    h = c + 0.1; l = c - 0.1; o = c.copy(); bad = np.zeros(n, bool); bad[0] = True; dn = np.zeros(n, bool); idx = np.arange(n)
    _, EC, *_ = MF.indicators(h, l, c, bad)
    j_exp = next(j for j in range(21, n) if c[j] < EC[j] and EC[j] < EC[j - 1])
    r = sim_mi(o, h, l, c, bad, dn, idx, n + 10, np.array([21]), EC)
    assert r["eb"][0] == j_exp + 1 and r["px"][0] == o[j_exp + 1] and r["typ"][0] == 3, (r, j_exp)
    assert j_exp == 30 and all(not (c[j] < EC[j]) for j in range(21, 30)), (j_exp, c[21:31], EC[21:31])
    msgs.append(f"F2 手算小例：上升段不出；第 {j_exp} 根收盤 13 跌破 EMA9（{EC[j_exp]:.4f}）且 EMA9 下彎 ⇒ 第 {j_exp + 1} 根開盤賣")
    # F2b 代數：EMA[j] ＝ EMA[j−1] ＋ 0.2（c[j] − EMA[j−1]）⇒ 收盤 ＜ EMA[j] ⇔ 收盤 ＜ EMA[j−1] ⇔ EMA[j] ＜ EMA[j−1]（SMA 起始那根除外）
    neq = 0; ntot = 0
    for rep in range(200):
        nb = 300; c = 50 * np.exp(np.cumsum(rng.normal(0, 0.02, nb))); bad = rng.random(nb) < 0.01; bad[0] = True
        _, EC, POS, *_ = MF.indicators(c * 1.01, c * 0.99, c, bad)
        q = np.flatnonzero((POS >= 9) & np.isfinite(EC))
        a1 = c[q] < EC[q]; a2 = EC[q] < EC[q - 1]
        neq += int((a1 != a2).sum()); ntot += len(q)
    assert neq == 0, neq
    msgs.append(f"F2b 代數檢查：段內位置 ≥ 9 時「收盤 ＜ EMA9」與「EMA9 下彎」逐根同真假（{ntot} 根、0 根不同）⇒ 出場第二條與方向條件在 EMA 定義下等價於收盤在 EMA9 之下")
    x = rng.normal(0, 1, 500); key = rng.integers(0, 40, 500)
    acc = np.zeros((300, 2)); np.add.at(acc[:, 0], key, 1.0); np.add.at(acc[:, 1], key, x)
    a_ = UO.agg_eval(acc); b_ = R.cl_stats(x, key)
    assert abs(a_["平均"] - b_["mean"]) < 1e-12 and abs(a_["lo"] - b_["lo"]) < 1e-12
    msgs.append("F3 假訊號分群彙總式 ＝ research11.cl_stats")
    for m in msgs:
        log("✅ " + m)
    return msgs


# ═════════════ 逐股 ═════════════
def stock_job(a):
    wn, sid, dry = a
    sid_, res = MF.stock_job((wn, sid))                     # ⭐ 頻率表同一支：事件、剔除狀態
    if res is None:
        return sid, None
    X = WF.base(wn, sid)
    W = X["W"]; n0 = X["n0"]; i = W["ix"][sid]
    o, h, l, c, bad, idx, nb, df = X["o"], X["h"], X["l"], X["c"], X["bad"], X["idx"], X["nb"], X["df"]
    _, EC, *_ = MF.indicators(h, l, c, bad)
    gate = X["gate"]; PV = np.asarray(X["PV"][:n0], bool); TRD = X["TRD"]; O = X["O"]; UPL = X["UPL"]
    dnlb = np.asarray(W["DNL"][i][idx], bool)
    pop = gate & PV
    kk = np.arange(nb - 1); s = kk + 1; T = idx[kk]; e = T + 1
    e_ = np.minimum(e, n0 - 1)
    with np.errstate(invalid="ignore"):
        ok = pop[T] & ~bad[kk] & (idx[s] == e) & ~bad[s] & (e < n0)
        ok &= TRD[e_] & np.isfinite(O[e_]) & (np.nan_to_num(O[e_]) > 0) & ~UPL[e_] & np.isfinite(o[s]) & (o[s] > 0) & np.isfinite(EC[kk])
    ent = np.zeros(n0, bool); ent[T[ok]] = True
    ev = res["ev"]
    okk = np.zeros(nb, bool); okk[kk[ok]] = True
    nex = {cell: int(sum(1 for x in ev[cell] if x["st"] == "保留" and not okk[x["k"]])) for cell in CELLS}
    out = {"ent": ent, "pop": pop, "ev": ev, "nex": nex, "nb": nb}
    if dry:
        return sid, out
    sk = kk[ok]; S = sk + 1; Tq = idx[sk]; Pq = o[S]
    r = sim_mi(o, h, l, c, bad, dnlb, idx, n0, S, EC)
    okr = r["eb"] >= 0
    Rr = np.full(n0, np.nan); Ty = np.zeros(n0, np.int8); Hh = np.full(n0, -1, np.int16); Sd = np.full(n0, -1, np.int32)
    Mt = np.full(n0, np.nan); Bo = np.zeros(n0, bool); Po = np.zeros(n0, bool)
    with np.errstate(invalid="ignore", divide="ignore"):
        rr = r["px"] / Pq - 1.0
    Rr[Tq[okr]] = rr[okr]; Ty[Tq] = r["typ"]
    Hh[Tq[okr]] = (idx[r["eb"][okr]] - idx[S[okr]]).astype(np.int16)
    Sd[Tq[okr]] = idx[r["eb"][okr]]
    Mt[Tq[r["typ"] == TAIL]] = c[nb - 1] / Pq[r["typ"] == TAIL] - 1.0
    Bo[Tq] = r["obad"]; Po[Tq] = r["post"]
    out.update({"R": Rr, "T_": Ty, "H": Hh, "S": Sd, "M": Mt, "B": Bo, "P": Po, "both": int(r["both"].sum())})
    # D3：固定抱 H（researchUO D3／researchBB 同式；T＋1 開盤進場）
    cf = df["close"].to_numpy(float); of = df["open"].to_numpy(float)
    cff = pd.Series(cf).ffill().to_numpy()
    badcal = np.zeros(n0, bool); badcal[idx[bad]] = True
    csb = np.cumsum(badcal).astype(np.int64)
    kH = np.searchsorted(idx, np.arange(n0), "right") - 1
    gap = np.zeros(n0, bool)
    okh = (kH >= 0) & (kH < nb - 1)
    pp = np.arange(n0)[okh]; kq = kH[okh]
    gap[pp] = (idx[kq + 1] - idx[kq] - 1 >= 5) & (pp - idx[kq] >= 5)
    for H in HD3:
        g = np.full(n0, np.nan)
        t = np.arange(n0 - H)
        with np.errstate(invalid="ignore", divide="ignore"):
            g[t] = cff[t + H] / of[t + 1] - 1.0
        brk = np.ones(n0, bool)
        brk[t] = (csb[t + H] - csb[t + 1] > 0) | gap[t + H]
        g[brk] = np.nan
        g[~ent] = np.nan
        out[f"G{H}"] = g
    return sid, out


# ═════════════ 統計 ═════════════
def trade_stats(Rn, hold, typ):
    Rn = np.asarray(Rn, float)
    o = {}
    if len(Rn):
        w = Rn[Rn > 0]; l_ = Rn[Rn <= 0]
        o.update({"淨報酬平均": float(Rn.mean()), "淨報酬中位": float(np.median(Rn)), "勝率": float((Rn > 0).mean()),
                  "平均賺": float(w.mean()) if len(w) else None, "平均賠": float(l_.mean()) if len(l_) else None,
                  "平均賺賠比": float(w.mean() / abs(l_.mean())) if len(w) and len(l_) and l_.mean() != 0 else None,
                  "平均持有天數": float(np.mean(hold)), "持有天數中位": float(np.median(hold)), "持有天數p90": float(np.percentile(hold, 90))})
        cnt = Counter(np.asarray(typ).tolist())
        for k_, nm in TYP.items():
            if k_ == TAIL:
                continue
            o[f"出場占比_{nm}"] = float(cnt.get(k_, 0) / len(Rn))
    return o


def sentence(cell, st, early=False):
    tail = [SENT_SRC, SENT_DIR, SENT_EXIT, SENT_ALL] + (NOTE_EARLY if early else [])
    rs = st["結果"]
    nm = NAME.get(cell, cell)
    if rs == "樣本不足以分辨":
        return f"{nm}：樣本不足以分辨（n_eff＝{st.get('n_eff', 0)}）｜" + "；".join(tail)
    pre = "樣本中等（n_eff＝{}，介於 30 與 100 之間）：".format(st["n_eff"]) if st.get("出口") == "出口②" else ""
    if rs == "結果①":
        s = "{}{}比同一天同母體隨機買、照同樣規則賣：測不出（X̄ {}，95% CI {} ～ {}）".format(pre, nm, pct(st["X̄"]), pct(st["lo"]), pct(st["hi"]))
    else:
        x2 = st.get("假訊號_x2", 0) or 0
        warn = "⚠ 隨機挑日子也有 {}／30 次同樣過關。".format(int(x2)) if (rs == "結果②" and x2 >= 2) else ""
        verb = "多賺" if rs == "結果②" else "少賺"
        s = "{}{}{}比同一天同母體隨機買、照同樣規則賣，每筆{} {}".format(warn, pre, nm, verb, pct(abs(st["X̄"]))[1:])
        s += "（95% CI {} ～ {}）".format(pct(st["lo"]), pct(st["hi"]))
    return s + "｜" + "；".join(tail)


def freq_frame(EVS, cal, n0):
    """researchWR_freq.run_freq 的事件檔寫法原樣（ev_cells ＝ A、D1_26、D2_無方向），寫成 CSV 再讀回字串。"""
    allrows = []
    for cell in CELLS:
        rows = sorted([e for ev in EVS for e in ev.get(cell, [])], key=lambda x: (x["T"], x["sid"]))
        if not rows:
            continue
        dfo = pd.DataFrame(rows)
        for col in ("T", "c日", "進場日位置"):
            if col in dfo:
                dfo[col] = [str(cal[x].date()) if 0 <= x < n0 else "" for x in dfo[col]]
        dfo.insert(0, "格", cell)
        allrows.append(dfo)
    buf = io.StringIO()
    pd.concat(allrows, ignore_index=True).to_csv(buf, index=False)
    buf.seek(0)
    return pd.read_csv(buf, dtype=str, keep_default_na=False)


# ═════════════ 主程式 ═════════════
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--dry", action="store_true", help="乾跑：只驗事件重現、對照池；⛔ 不算任何出場與報酬")
    a = ap.parse_args()
    if a.limit and not a.dry:
        raise SystemExit("⛔ 不准含報酬的小樣本試跑；--limit 只能配 --dry")
    t0 = time.time()
    out = OUT
    os.makedirs(os.path.join(out, "events"), exist_ok=True)
    reg = WF.reg_check(REG_SHA)
    log(f"[登錄] {reg}（sha {REG_SHA} 已驗）｜{'乾跑' if a.dry else '本體'}開跑 {now_tpe()}")
    fx = selftest()
    FJ = json.load(open(os.path.join(FREQ, "freq.json"), encoding="utf-8"))
    J = {"性質": "Mass Index 反轉凸起 seq1 事件層正式跑（單筆層；判定格 A；探索、確認各自報、主全窗參考、早年描述）",
         "登錄": f"台股策略線 seq1 sha {REG_SHA}", "裁定": "seq374 起草、seq375 發號；N_前段 ＋1",
         "成本": COST, "種子": {"對照": SEED_CTRL, "假訊號": SEED_FAKE}, "Bonferroni": {"族N": N_FAM, "z": UO.Z95},
         "出場": "收盤 < EMA9(收盤) 且 EMA9 當日 < 前一日 ⇒ 隔天開盤賣（⭐ 本線定；researchBB.sim 'm' 配 LV）",
         "fixture": fx, "讀法_頻率表": MF.__doc__.split("═══ 讀法")[1], "讀法": __doc__.split("═══ 讀法")[1], "世界": {}, "時點": {"本體開跑": now_tpe()}}
    MAIN = []; DESC = []; BY = []; FK = []
    for wn in ("主", "早年"):
        W = AT.load_world(wn); cal = W["cal"]; n0 = W["n0"]
        win = {}
        for sg, (x_, y_) in WF.SEGS[wn].items():
            p0 = int(cal.searchsorted(pd.Timestamp(x_)))
            p1 = n0 - 2 if y_ is None else min(n0 - 2, int(cal.searchsorted(pd.Timestamp(y_), side="right")) - 1)
            win[sg] = (p0, p1)
        W["win"] = win
        WF._G[wn] = W
        sids = W["sids"][:a.limit] if a.limit else W["sids"]
        S = len(W["sids"]); ix = W["ix"]
        ENT = np.zeros((n0, S), bool); POP = np.zeros((n0, S), bool)
        M = {k: np.full((n0, S), np.nan) for k in ("R", "M", "G20", "G60")}
        Mi = {"H": np.full((n0, S), -1, np.int16), "S": np.full((n0, S), -1, np.int32)}
        Ty = np.zeros((n0, S), np.int8); Mb = {k: np.zeros((n0, S), bool) for k in ("B", "P")}
        EVS = {}; NEX = Counter(); NBOTH = 0
        with Pool(a.procs) as pool:
            for k_, (sid, r) in enumerate(pool.imap_unordered(stock_job, [(wn, s_, a.dry) for s_ in sids], chunksize=8)):
                if r is not None:
                    j = ix[sid]
                    ENT[:, j] = r["ent"]; POP[:, j] = r["pop"]; EVS[sid] = r["ev"]; NEX.update(r["nex"])
                    if not a.dry:
                        for kk in M:
                            M[kk][:, j] = r[kk]
                        Mi["H"][:, j] = r["H"]; Mi["S"][:, j] = r["S"]; Ty[:, j] = r["T_"]
                        Mb["B"][:, j] = r["B"]; Mb["P"][:, j] = r["P"]; NBOTH += r["both"]
                if (k_ + 1) % 400 == 0:
                    log(f"  {wn} … {k_ + 1}／{len(sids)}｜{time.time() - t0:.0f}s")
        log(f"[{wn}] 逐股完 {len(EVS)} 檔｜{time.time() - t0:.0f}s")
        # ── 查核 1：事件 ＝ 已提交頻率表事件檔（逐列逐欄）
        mine = freq_frame(list(EVS.values()), cal, n0)
        ref = pd.read_csv(os.path.join(FREQ, f"events_{wn}.csv.gz"), dtype=str, keep_default_na=False)
        if a.limit:
            ref = ref[ref["sid"].isin(set(sids))].reset_index(drop=True)
        same = list(ref.columns) == list(mine.columns) and ref.shape == mine.shape and (ref.values == mine.values).all()
        if not same:
            raise SystemExit(f"⛔ {wn} 重新偵測 ≠ 已提交頻率表事件檔（{mine.shape} vs {ref.shape}）⇒ 中止（未讀任何報酬）")
        log(f"[查核1] {wn}：重新偵測與已提交頻率表事件檔逐列逐欄相同（{len(ref):,} 列）")
        # ── 查核 2：保留事件都在母體且可進場
        bad_st = Counter()
        for s_, ev in EVS.items():
            j = ix[s_]
            for cell in CELLS:
                for e in ev[cell]:
                    if e["st"] == "保留" and not (POP[e["T"], j] and ENT[e["T"], j]):
                        bad_st[cell] += 1
        assert not bad_st, f"⛔ 保留事件但本支判不可進場：{bad_st}"
        log(f"[查核2] 保留事件全在母體且 T＋1 可買、EMA9c[T] 有值；本支另剔（應為 0）：{dict(NEX)}")
        RAW = {}
        for cell in CELLS:
            Mx = np.zeros((n0, S), bool)
            for s_, ev in EVS.items():
                for e in ev[cell]:
                    Mx[e["T"], ix[s_]] = True
            RAW[cell] = Mx
        BASE = POP & ENT
        moni = np.asarray(cal.year * 12 + cal.month); years = np.asarray(cal.year); dates = np.array([str(d.date()) for d in cal])
        Wj = {"資料": W["data"], "日曆": [str(cal[0].date()), str(cal[-1].date())], "檔數": len(sids), "可用檔數": len(EVS),
              "段": {sg: f"{cal[p].date()}～{cal[q].date()}" for sg, (p, q) in win.items()}, "格": {}}
        if a.dry:
            for sg, (p0, p1) in win.items():
                pb_ = BASE[p0:p1 + 1].sum(axis=1)
                kept = {c_: sum(1 for ev in EVS.values() for e in ev[c_] if e["st"] == "保留" and p0 <= e["T"] <= p1) for c_ in CELLS}
                log(f"[乾跑 {wn}/{sg}] 對照基池每日中位 {int(np.median(pb_[pb_ > 0])) if (pb_ > 0).any() else 0}｜保留事件 {kept}")
            J["世界"][wn] = Wj
            continue
        if "第一次讀報酬" not in J["時點"]:
            J["時點"]["第一次讀報酬"] = now_tpe()
        POOL = BASE & np.isfinite(M["R"])
        pm = POOL.sum(axis=1)
        log(f"[對照池] 第一次讀報酬 {J['時點']['第一次讀報酬']}｜每日對照池中位 {int(np.median(pm[pm > 0]))} 檔｜同根皆觸 {NBOTH}（應為 0）｜{time.time() - t0:.0f}s")
        Wj["同根皆觸(seq373)"] = int(NBOTH)
        crc = {s_: zlib.crc32(s_.encode("utf-8")) for s_ in W["sids"]}
        TR = {}
        for cname in CELLS:
            smp = UO.Sampler(POOL, RAW[cname])
            rows = []; skip = Counter()
            for s_, ev in EVS.items():
                j = ix[s_]; last_sell = -10 ** 9; open_end = False
                for e in sorted([x for x in ev[cname] if x["st"] == "保留"], key=lambda x: x["T"]):
                    T = e["T"]
                    if open_end:
                        skip["前筆資料尾未出場"] += 1; continue
                    if T < last_sell:
                        skip["持有中略過"] += 1; continue
                    rows.append((j, T, e))
                    if int(Ty[T, j]) == TAIL:
                        open_end = True
                    else:
                        last_sell = int(Mi["S"][T, j])
            rows.sort(key=lambda z: (z[1], W["sids"][z[0]]))
            n = len(rows)
            ii = np.array([z[0] for z in rows], np.int64); TT = np.array([z[1] for z in rows], np.int64)
            Rr = M["R"][TT, ii]; ty = Ty[TT, ii]; Hk = Mi["H"][TT, ii].astype(np.int64)
            cm = np.full(n, np.nan); cn = np.zeros(n, np.int64); cids = []; cty = []; chd = []
            for q, (j, T, e) in enumerate(rows):
                sid = W["sids"][j]
                cs = smp.draw(T, j, [SEED_CTRL, TAG[cname], T, crc[sid]])
                cn[q] = len(cs)
                if len(cs):
                    cm[q] = float(M["R"][T, cs].mean()); cty.append(Ty[T, cs]); chd.append(Mi["H"][T, cs])
                cids.append(";".join(W["sids"][x] for x in cs))
            Xv = Rr - cm
            fr = pd.DataFrame({"sid": [W["sids"][x] for x in ii], "market": [W["mk"].get(W["sids"][x], "twse") for x in ii],
                               "T": dates[TT] if n else [], "進場日": dates[np.minimum(TT + 1, n0 - 1)] if n else [],
                               "凸起開始日": [z[2]["凸起開始日"] for z in rows], "MI[T]": [z[2]["MI[T]"] for z in rows],
                               "MI峰值": [z[2]["MI峰值"] for z in rows], "EMA9下彎": [z[2]["EMA9下彎"] for z in rows],
                               "出場日": [dates[x] if x >= 0 else "" for x in Mi["S"][TT, ii]], "出場種類": [TYP[int(x)] for x in ty],
                               "持有天數": Hk, "R": Rr, "R淨": Rr - COST, "帳面R(資料尾)": M["M"][TT, ii],
                               "順延(鎖死跌停)": Mb["P"][TT, ii], "賣出開盤缺用收盤": Mb["B"][TT, ii],
                               "對照數": cn, "對照平均R": cm, "X": Xv, "種子格標": TAG[cname], "對照代號": cids})
            TR[cname] = {"fr": fr, "i": ii, "T": TT, "X": Xv, "R": Rr, "ty": ty, "H": Hk, "cm": cm, "skip": dict(skip),
                         "cty": np.concatenate(cty) if cty else np.zeros(0), "chd": np.concatenate(chd) if chd else np.zeros(0)}
            log(f"  [{wn}] {cname}：進場 {n} 筆（{dict(skip)}）｜資料尾未出場 {int((ty == TAIL).sum())}｜無對照 {int((cn == 0).sum())}｜{time.time() - t0:.0f}s")
        # D3：同 A 進場、固定抱 H
        A0 = TR["A"]
        SMP3 = {H: UO.Sampler(BASE & np.isfinite(M[f"G{H}"]), RAW["A"]) for H in HD3}
        for H in HD3:
            g = M[f"G{H}"][A0["T"], A0["i"]]; cm = np.full(len(g), np.nan); cn = np.zeros(len(g), np.int64)
            for q, (j, T) in enumerate(zip(A0["i"], A0["T"])):
                cs = SMP3[H].draw(int(T), int(j), [SEED_CTRL, TAG[f"D3_H{H}"], int(T), crc[W["sids"][j]]])
                cn[q] = len(cs)
                if len(cs):
                    cm[q] = float(M[f"G{H}"][T, cs].mean())
            A0["fr"][f"D3_R{H}"] = g; A0["fr"][f"D3_對照{H}"] = cm; A0["fr"][f"D3_X{H}"] = g - cm; A0["fr"][f"D3_對照數{H}"] = cn
            A0[f"X{H}"] = g - cm; A0[f"G{H}"] = g
        for cname, d_ in TR.items():
            d_["fr"].to_csv(os.path.join(out, "events", f"trades_{wn}_{cname}.csv.gz"), index=False, compression={"method": "gzip", "compresslevel": 6})
        keptA = {ix[s_]: np.array(sorted(e["T"] for e in ev["A"] if e["st"] == "保留"), np.int64) for s_, ev in EVS.items()}
        for sg, (p0, p1) in win.items():
            yrs = (cal[p1] - cal[p0]).days / 365.25
            segj = {}
            fsg = FJ["世界"][wn]["段"][sg]
            for cname, d_ in TR.items():
                inseg = (d_["T"] >= p0) & (d_["T"] <= p1)
                okx = inseg & np.isfinite(d_["X"])
                st = UO.x_stats(d_["X"][okx], moni[d_["T"][okx]])
                fin = inseg & np.isfinite(d_["R"])
                ty_all = d_["ty"][inseg]
                st.update({"進場筆數(含未出場)": int(inseg.sum()), "資料尾未出場": int((inseg & (d_["ty"] == TAIL)).sum()),
                           "資料尾未出場_帳面R平均": float(np.nanmean(d_["fr"]["帳面R(資料尾)"].to_numpy(float)[inseg & (d_["ty"] == TAIL)])) if (inseg & (d_["ty"] == TAIL)).any() else None,
                           "無對照剔除": int((fin & ~np.isfinite(d_["X"])).sum()), "相異檔數": int(len(set(d_["i"][okx].tolist()))),
                           "每年事件數": round(int(okx.sum()) / yrs, 2), "頻率表上限每年事件數": fsg.get(cname, {}).get("每年事件數"),
                           "R̄": float(d_["R"][okx].mean()) if okx.any() else None,
                           "對照R̄": float(d_["cm"][okx].mean()) if okx.any() else None,
                           "對照淨報酬平均": float(d_["cm"][okx].mean() - COST) if okx.any() else None})
                for k_, nm in TYP.items():
                    st[f"出場占比含資料尾_{nm}"] = float((ty_all == k_).mean()) if len(ty_all) else None
                st.update(trade_stats(d_["R"][okx] - COST, d_["H"][okx], d_["ty"][okx]))
                frs = d_["fr"]
                if okx.any():
                    st["順延筆數"] = int(frs["順延(鎖死跌停)"].to_numpy(bool)[okx].sum())
                    st["賣出開盤缺用收盤筆數"] = int(frs["賣出開盤缺用收盤"].to_numpy(bool)[okx].sum())
                yr = years[d_["T"][okx]]
                st["逐年"] = {str(y): {"n": int((yr == y).sum()), "X̄": float(d_["X"][okx][yr == y].mean()),
                                      "持有均": float(d_["H"][okx][yr == y].mean()),
                                      "勝率": float(((d_["R"][okx][yr == y] - COST) > 0).mean())} for y in sorted(set(yr.tolist()))}
                for y, q in st["逐年"].items():
                    BY.append({"世界": wn, "段": sg, "格": cname, "年": y, **q})
                if cname == "A":
                    st["凸起與方向(頻率表口徑)"] = fsg.get("附加")
                    for H in HD3:
                        xh = d_[f"X{H}"]; okh = inseg & np.isfinite(xh)
                        q = UO.x_stats(xh[okh], moni[d_["T"][okh]])
                        q.update({"R̄": float(d_[f"G{H}"][okh].mean()) if okh.any() else None,
                                  "淨報酬平均": float(d_[f"G{H}"][okh].mean() - COST) if okh.any() else None,
                                  "勝率": float(((d_[f"G{H}"][okh] - COST) > 0).mean()) if okh.any() else None})
                        DESC.append({"世界": wn, "段": sg, "格": f"D3_固定抱{H}日", **{k: v for k, v in q.items() if not isinstance(v, dict)}, "身分": "描述（⛔ 不判、⛔ 不當出場比較基準）"})
                        st[f"D3_H{H}"] = q
                    # 假訊號臂
                    acc = np.zeros((REPS, 300, 2)); cntf = np.zeros((REPS, 3), np.int64)
                    mo0 = moni[p0]
                    isel = d_["i"][okx]
                    nper = Counter(isel.tolist())
                    candc = {}
                    for jj in nper:
                        cand = np.flatnonzero(POOL[p0:p1 + 1, jj]).astype(np.int64) + p0
                        Tk = keptA.get(jj, np.zeros(0, np.int64))
                        if len(Tk) and len(cand):
                            kq = np.searchsorted(Tk, cand, side="right") - 1
                            prv = np.where(kq >= 0, Tk[np.clip(kq, 0, len(Tk) - 1)], -10 ** 9)
                            cand = cand[~((kq >= 0) & (cand - prv <= EXCL))]
                        candc[jj] = cand
                    smpf = UO.Sampler(POOL, RAW["A"])
                    for r_ in range(REPS):
                        for jj, nn in nper.items():
                            cand = candc[jj]; mq = min(nn, len(cand)); cntf[r_, 2] += nn - mq
                            if mq == 0:
                                continue
                            sid = W["sids"][jj]
                            rng = np.random.default_rng([SEED_FAKE + r_, crc[sid], SEGNUM[sg]])
                            pick = np.sort(rng.choice(cand, size=mq, replace=False))
                            for T in pick:
                                T = int(T)
                                cs = smpf.draw(T, jj, [SEED_CTRL, 5100 + r_, T, crc[sid]])
                                cntf[r_, 0] += 1
                                if len(cs) == 0:
                                    cntf[r_, 1] += 1; continue
                                xv = M["R"][T, jj] - M["R"][T, cs].mean()
                                cl = moni[T] - mo0
                                acc[r_, cl, 0] += 1.0; acc[r_, cl, 1] += xv
                    res_ = [UO.agg_eval(acc[r_]) for r_ in range(REPS)]
                    st["假訊號_x2"] = sum(1 for q in res_ if q and q["結果"] == "結果②")
                    st["假訊號_x3"] = sum(1 for q in res_ if q and q["結果"] == "結果③")
                    st["假訊號_平均X"] = float(np.mean([q["平均"] for q in res_ if q])) if any(res_) else None
                    c2 = cntf.sum(axis=0)
                    st["假訊號_帳"] = {"抽出": int(c2[0]), "無對照": int(c2[1]), "可抽日不足": int(c2[2])}
                    for r_, q in enumerate(res_):
                        FK.append({"世界": wn, "段": sg, "格": cname, "r": r_, **({kk: q[kk] for kk in ("n", "平均", "lo", "hi", "n_eff", "出口", "結果")} if q else {"n": 0})})
                    st["過seq322門檻"] = bool(st["結果"] == "結果②" and st.get("bonf_lo", -1) > 0 and st["假訊號_x2"] <= 1 and st.get("X̄−成本", -1) > 0
                                          and st.get("逐月中位與平均同號", False))
                segj[cname] = st
            A_ = TR["A"]; okA = (A_["T"] >= p0) & (A_["T"] <= p1) & np.isfinite(A_["X"])
            for other in ("D1_26", "D2_無方向"):
                B_ = TR[other]; okB = (B_["T"] >= p0) & (B_["T"] <= p1) & np.isfinite(B_["X"])
                segj[other]["對A差"] = UO.diff_stats(A_["X"][okA], moni[A_["T"][okA]], B_["X"][okB], moni[B_["T"][okB]])
            for cname, st in segj.items():
                if cname in JUDGE:
                    role = "判定格｜" + {"探索": "判定段（各自報）", "確認": "判定段（各自報）", "主全窗": "參考", "早年": "早年描述"}[sg]
                else:
                    role = "描述（⛔ 不判、不計 N）"
                st["身分"] = role
                st["句子"] = sentence(cname, st, early=(wn == "早年"))
                MAIN.append({"世界": wn, "段": sg, "格": cname, "說明": NAME[cname], "身分": role, "期間": f"{cal[p0].date()}～{cal[p1].date()}",
                             **{k: v for k, v in st.items() if not isinstance(v, dict) and k not in ("身分", "句子")},
                             **({"對A差": st["對A差"].get("差(D2−A)"), "對A差_lo": st["對A差"].get("lo"), "對A差_hi": st["對A差"].get("hi")} if "對A差" in st else {}),
                             "句子": st["句子"]})
                log(f"  [{wn}/{sg}] {cname}：n={st['n']} n_eff={st.get('n_eff')} X̄={pct(st.get('X̄'))} CI {pct(st.get('lo'))}～{pct(st.get('hi'))} {st['結果']}"
                    f" 持有均 {st.get('平均持有天數')}" + (f" 假 x={st.get('假訊號_x2')} seq322={st.get('過seq322門檻')}" if cname in JUDGE else "")
                    + f"｜{time.time() - t0:.0f}s")
            Wj["格"][sg] = segj
        Wj["對照側"] = {c_: {"筆數": int(len(TR[c_]["cty"])), **{f"占比_{TYP[k]}": float((TR[c_]["cty"] == k).mean()) if len(TR[c_]["cty"]) else None for k in TYP},
                             "平均持有": float(TR[c_]["chd"][TR[c_]["chd"] >= 0].mean()) if (TR[c_]["chd"] >= 0).any() else None}
                        for c_ in CELLS}
        Wj["持有限制略過"] = {c_: d_["skip"] for c_, d_ in TR.items()}
        J["世界"][wn] = Wj
        del ENT, POP, M, Mi, Ty, Mb, RAW, BASE, POOL, TR
    if a.dry:
        log(f"[乾跑完] ⛔ 未算任何出場與報酬｜{time.time() - t0:.0f}s")
        open(os.path.join(out, "dry.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
        return
    # ── 判定表與先驗
    jd = {}
    keys = ("身分", "結果", "出口", "n", "n_eff", "X̄", "lo", "hi", "bonf_lo", "中位", "X̄−成本", "逐月平均之中位", "假訊號_x2", "過seq322門檻",
            "勝率", "平均賺賠比", "平均持有天數", "持有天數中位", "持有天數p90", "每年事件數", "頻率表上限每年事件數",
            "出場占比_" + TYP[3], "出場占比_" + TYP[4], "出場占比_" + TYP[5], "資料尾未出場", "句子")
    for cell in CELLS:
        for w, sgs in (("主", ("探索", "確認", "主全窗")), ("早年", ("早年",))):
            for sg in sgs:
                st = J["世界"][w]["格"][sg][cell]
                jd[f"{cell}｜{sg}"] = {k: st.get(k) for k in keys}
    J["判定"] = jd
    pri = {}
    ex, cf = J["世界"]["主"]["格"]["探索"]["A"], J["世界"]["主"]["格"]["確認"]["A"]
    pri["①判定格兩段都落結果①"] = {"探索": ex["結果"], "確認": cf["結果"], "中": ex["結果"] == "結果①" and cf["結果"] == "結果①"}
    pri["②方向保留40～60%"] = {}
    pri["③平均持有<10天"] = {}
    for w, sgs in (("主", ("探索", "確認", "主全窗")), ("早年", ("早年",))):
        for sg in sgs:
            fx_ = FJ["世界"][w]["段"][sg]["附加"]; r_ = fx_["方向保留比例(偵測)"]
            pri["②方向保留40～60%"][sg] = {"比例(偵測)": r_, "比例(保留)": fx_["方向保留比例(保留)"], "中": bool(r_ is not None and 0.4 <= r_ <= 0.6)}
            hm = J["世界"][w]["格"][sg]["A"].get("平均持有天數")
            pri["③平均持有<10天"][sg] = {"平均持有天數": hm, "中": bool(hm is not None and hm < 10)}
    J["先驗"] = pri
    J["N"] = {"本件判定格": 1, "描述格": "不計 N"}
    J["時點"]["完成"] = now_tpe()
    pd.DataFrame(MAIN).to_csv(os.path.join(out, "MI_main.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(DESC).to_csv(os.path.join(out, "MI_desc.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(BY).to_csv(os.path.join(out, "by_year.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(FK).to_csv(os.path.join(out, "fake_reps.csv"), index=False, encoding="utf-8-sig")
    json.dump(J, open(os.path.join(out, "MI.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[判定] {json.dumps({k: {kk: v.get(kk) for kk in ('結果', 'n_eff', 'X̄', '假訊號_x2', '過seq322門檻', '平均持有天數')} for k, v in jd.items()}, ensure_ascii=False, default=float)}")
    log("[先驗] " + json.dumps(pri, ensure_ascii=False, default=float))
    log(f"完成 {time.time() - t0:.0f}s")
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
