# -*- coding: utf-8 -*-
"""海龜交易法 Donchian 突破 seq2【事件層正式跑】（台股策略線 單筆層登錄 sha 87b39da0f38816e0，2026-10-17 22:33；裁定 seq366 發號、
seq367 發 seq2；N_前段 ＋2）——回測線計算子代理。
⛔ 不 commit、不改既有程式與結果夾；researchTurtle_freq（事件偵測、剔除、ADX、段）、researchAscTri_freq（世界）、research11、researchUO（統計小工具）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTurtle [--procs 3]
    乾跑（⛔ 不算任何出場、報酬；只驗事件重現與對照池）：... -m backtest.researchTurtle --dry [--limit 200]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTurtle_check
輸出 backtest/resultsTurtle/（⛔ 不碰 freq/）：Turtle.json、Turtle_main.csv（判定表＋分報）、Turtle_desc.csv（描述格）、by_year.csv、fake_reps.csv、
    events/trades_<世界>_<格>.csv.gz（逐筆進出、對照、X）、run.log

格：S1、S2 ＝ 判定格（登錄 §一）；另一讀法（只報）：S1_當根停損、S2_當根停損（G3）；
    描述（⛔ 不判、不計 N）：D1（跳過規則甲）、D2（跳過規則乙）、D3（ADX(14)＞25）、D4（收盤判、隔天開盤）、D3×D4、D5（營量／營飆池內）、
    固定抱 20／60 日、假訊號臂（30 次隨機日當 T）。

═══ 讀法（G 標；頻率表 T1～T9 原樣沿用（世界、母體、壞根、價格、前 N 日、偵測、剔除、ADX、D5 池、段），以下為正式跑新增；
     ⛔ 在讀任何本件報酬之前寫死；★＝執行者定，〔 〕內為另一讀法）═══
 G1 事件 ＝ 逐股呼叫 researchTurtle_freq.stock_job 原樣；⭐ 依頻率表寫法排成表、與已提交的 resultsTurtle/freq/events_<世界>.csv.gz 逐列逐欄比
    （S1、S2、D4_S1、D4_S2），任一不同 ⇒ 中止、⛔ 不算報酬。進場候選 ＝ 狀態「保留」者；★ 另需停損用的 N 有值（S：N[k−1]；D4：N[k]）
    與還原開盤有值且 ＞ 0（S：第 k 根；D4：第 k＋1 根），否則剔除為「N缺值」並計數（頻率表沒有這一關）。
 G2 N（登錄 §一；MQL5 逐字）：TR ＝ max(h−l, |h−c前|, |l−c前|)（還原價）；★ 段內起算（段首 s ＝ 第 0 根或壞 K 棒，同 ADX T6）：TR 從 s＋1 起，
    N[s＋20] ＝ TR[s＋1..s＋20] 簡單平均（種子），之後 N[j] ＝ (N[j−1]×19 ＋ TR[j]) ÷ 20。
    停損價 ＝ 買進價 − 2 × N（S：N[k−1]＝買進當日前一日值，登錄 §一；D4：N[k]＝收盤判定日、買進前一日）。⭐ 停損價買進後固定不動（不加碼 ⇒ 無加倉移停損）。
 G3 S1／S2 成交（登錄 §一，盤中觸價）：買價 P ＝ max(o[k], 前 N 日最高)，T 當日；通道 CL_M[j] ＝ min(l[j−M..j−1])（前 M 根有效 K 棒、不含當日；
    S1 M＝10、S2 M＝20）。出場逐根 j：通道 l[j] ＜ CL_M[j] ⇒ 價 min(o[j], CL_M[j])；停損 l[j] ≤ 停損價 ⇒ 價 min(o[j], 停損價)；
    同一根兩者都觸 ⇒ 兩價較低者（登錄）；種類記價較低者、相等記「2N 停損」，另計「同根皆觸」筆數。o[j] 缺值 ⇒ 用觸價價位並計數。
    ★ 出場從 T＋1（第 k＋1 根）起判：進場當根日 K 看不出最低點在買進之前或之後 ⇒ 主讀法不在進場當根出場
    〔另一讀法 S_當根停損：進場當根最低 ≤ 停損價 ⇒ 當根以停損價賣（通道當根不判），只報；對照同法〕。
 G4 跌停鎖死順延（登錄 §一）：觸發根（S：觸價那根；D4：賣出那根）是開盤跌停且全日鎖死（W.DNL ＝ 開盤＝跌停價 ∧ 原始最高＝原始開盤）
    ⇒ 順延到其後第一根非鎖死有效 K 棒開盤賣（開盤缺 ⇒ 收盤）；順延途中遇壞 K 棒 ⇒ 壞 K 棒前一根收盤強制；順延到資料外 ⇒ 照 G5。種類不變、另記「順延」。
 G5 壞根、下市、資料尾（researchUO E3 同）：持有中下一根是壞 K 棒 ⇒ 以壞 K 棒前一根還原收盤強制出場；之後再無成交且最後一根距資料尾 ≥ 5 交易日
    ⇒ 最後一根還原收盤出場（「末根」＝下市／長期停牌）；距資料尾 ＜ 5 日仍未出場 ⇒「資料尾未出場」：照實報件數與帳面報酬，⛔ 不進 X。
 G6 R ＝ 出場價 ÷ 買價 − 1；淨報酬 ＝ R − 0.585%（evaluate.COST）；X ＝ (R − 0.585%) − 對照平均(R − 0.585%) ＝ R − 對照平均 R。
    持有天數 ＝ 出場日 − 進場日（交易日曆位置差；S 進場日 ＝ T、D4 進場日 ＝ T＋1）。
 G7 持有中不重複進場（登錄 §一）：同檔保留事件依 T 排序；前筆賣出日 S。★ S 格：新事件需 T ＞ S（當日觸價買 ⇒ 賣出當日不再買）〔另一讀法 T ≥ S〕；
    D4 格：T ≥ S（T＋1 開盤買，同 researchUO E5）。前筆資料尾未出場 ⇒ 之後全部略過。整個世界時序上套（段外也擋段內）；各格各自套
    （D3、D5 先濾再套持有限制）。
 G8 對照（seq366）：同一天 T、同母體隨機抽 20 檔，各自照同樣出場規則（各自的 M 日低點、各自的 2N）：
    S 格 ⇒ 對照以 T 當日開盤 o 進場、停損 ＝ o − 2 × N[k−1]、出場從 T＋1 起（同 G3～G5；當根停損另一讀法同法）；
    池 ＝ Frame.gate[T] ∧ pit_valid[T] ∧ T 有成交 ∧ T 非壞 K 棒 ∧ T 開盤有值 ＞ 0 ∧ 非開盤鎖漲停（頻率表 T4 同旗標）∧ N[k−1] 有值 ∧ R 可算；
    D4 格 ⇒ 對照以 T＋1 開盤進場（同 D4 事件；池 ＝ 母體 ∧ T＋1 可買（頻率表 T5 同旗標）∧ N[k] 有值 ∧ R 可算）。
    ★ 扣掉事件股自己與 T 當天同系統【原始】偵測到的股票（任何狀態；researchUO E6 同）。不放回抽 20 檔（不足 ⇒ 全取、計數）；等權平均。
    種子 default_rng([20261017, 格標, T, crc32(sid)])；⛔ 對照不套持有限制。
 G9 判定量 X̄；CI ＝ T 所在曆月分群（research11.cl_stats 式）、1.96；n_eff ＝ min(可算筆數, 有事件曆月數)；n_eff ＜ 30 ⇒ 依構造不可判定、
    30～99 ⇒ 句首「樣本中等」；結果② ＝ CI 不含 0 且 X̄ ＞ 0、③ ＝ X̄ ＜ 0 且 CI 不含 0、① ＝ 含 0（登錄 §二）。
    判定段（seq366／367）：探索、確認【各自報】為準；主全窗參考；早年 2005～2014 描述（附 reduce_v2 約 0.3% 註）。
 G10 seq322（researchUO E9 同式）＝ 結果② ∧ Bonferroni 下界 ＞ 0（族 N＝2 ⇒ z ＝ NormalDist.inv_cdf(1 − 0.05/4) ＝ 2.2414）∧ 假訊號 x ≤ 1
    ∧ X̄ − 0.585% ＞ 0 ∧ 逐月 X 平均之中位數與 X̄ 同號；各段各報。
 G11 假訊號臂（researchUO E10 同式）：r ＝ 0…29；每檔每段 n ＝ 該檔該格可算筆數；可抽日 ＝ 該檔在段內且在 G8 S 格對照池；排除「存在該檔同格保留事件
    T_r ∈ [T−20, T]」的日子；不放回抽 n 天；假事件 R ＝ 對照式 R（T 開盤進場、同出場）；對照照 G8；種子 default_rng([20261018＋r, crc32(sid), 段序號])；
    x／30 ＝ 落結果② 的次數。⛔ 不套持有限制。
 G12 描述：
    D1 跳過規則甲 ＝ ★ 子集讀法：同格持有限制後的交易序列中，同檔「上一筆」淨報酬 ＞ 0 ⇒ 跳過這筆（上一筆的假想交易照樣追蹤，故不另放行其持有期間的突破）；
       無上一筆 ⇒ 做。S1、S2 各報（登錄寫 S1；S2 多報）。
    D2 跳過規則乙 ＝ ★ 上一筆「失敗」才做：失敗 ＝ 上一筆持有期間（進場根～出場根）任一根收盤 ＜ 其突破價位（前 N 日最高）＝ 回到突破前區間；
       無上一筆 ⇒ 做。
    D3 ＝ 頻率表 D3 事件（ADX(14)[T−1] ＞ 25；D4 用 ADX[T]）先濾再套持有限制，其餘同判定格。
    D4 ＝ 頻率表 D4 事件；T＋1 開盤進場；出場收盤判：收盤 ＜ CL_M[j]（★ 前 M 日【最低價】，與 D4 進場用最高價對稱）或收盤 ≤ 停損價
       （★ D4 停損也收盤判）⇒ 下一根開盤賣（下一根壞 K 棒 ⇒ 當根收盤強制；鎖死跌停 ⇒ G4）；持有中第 j 根含進場當天收盤。
       並報 D4 − S（X̄ 差，曆月分群線性化 SE，researchUO.diff_stats）＝「成交假設差多少」。
    D5 ＝ 頻率表 D5 旗標（同日、20 日內；營飆子集另欄）先濾再套持有限制；n_eff ＜ 30 依構造不可判定。
    固定抱 H（20／60）＝ 判定格同一批進場，R_H ＝ ffill 還原收盤(T＋H) ÷ 買價 − 1；(T, T＋H] 有壞 K 棒或 T＋H 落在 ≥ 5 日缺口 ⇒ 不可算；
       對照 ＝ S 格對照池 ∧ R_H 可算、T 開盤進場、同法抽 20 檔。⛔ 只描述，不當出場比較基準（seq308）。
 G13 必報：勝率 ＝ 淨報酬 ＞ 0 比例；平均賺賠比 ＝ 賺錢筆平均淨報酬 ÷ |賠錢筆平均淨報酬|；出場種類占比（分母 ＝ 可算筆，另報含資料尾）；
    停損後 20 日內又創新高 ＝ 2N 停損出場根之後 20 根有效 K 棒內又出現同系統原始偵測（盤中最高 ＞ 前 N 日最高）的比例。
    賣出點措辭照 seq343：「通道出場訊號（跌破 10／20 日低點）」「2N 停損」；⛔ 不稱最高點、頂部。
 G14 結果句必附：「進出場照海龜原規則、盤中觸價成交；部位與加碼留組合層」「單筆層通過 ≠ 組合會贏 0050」；早年另附 reduce_v2 與上櫃版面註。
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
from statistics import NormalDist

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchTurtle_freq as RT              # noqa: E402  事件偵測、剔除、ADX、段（⛔ 只 import）
from backtest import researchUO as UO                       # noqa: E402  Sampler、agg_eval、diff_stats、verdict（⛔ 只 import）
from backtest import researchAscTri_freq as AT              # noqa: E402  load_world 原樣
from backtest import researchUO_freq as RU                  # noqa: E402  load_sig 原樣
from backtest import research11 as R                        # noqa: E402  load_bars、cl_stats
from backtest import patterns as P                          # noqa: E402  Frame.gate
from backtest import evaluate as E                          # noqa: E402  COST
from backtest import universe_gate as UG                    # noqa: E402

UG.set_gate_v2(True)

REG_SHA = RT.REG_SHA
OUT = "backtest/resultsTurtle"
FREQ = RT.OUT
NS = {"S1": 20, "S2": 55}
MS = {"S1": 10, "S2": 20}
NATR = 20
NCTRL = 20
SEED_CTRL, SEED_FAKE = 20261017, 20261018
REPS, EXCL = 30, 20
HD = (20, 60)
Z95 = 1.96
N_FAM = 2
ZB = NormalDist().inv_cdf(1 - 0.05 / 2 / N_FAM)
COST = E.COST
GAP_END = 5
REHIGH = 20
TYP = {1: "通道出場訊號(跌破10/20日低點)", 2: "2N停損", 3: "壞根前一根收盤強制", 4: "末根收盤(下市/之後無成交)", 5: "資料尾未出場"}
# 格 ⇒ (系統, 模式, 版本, 事件來源格, 濾網鍵)
CELLDEF = {
    "S1": ("S1", "S", "m", "S1", None), "S2": ("S2", "S", "m", "S2", None),
    "S1_當根停損": ("S1", "S", "a", "S1", None), "S2_當根停損": ("S2", "S", "a", "S2", None),
    "D3_S1": ("S1", "S", "m", "D3_S1", None), "D3_S2": ("S2", "S", "m", "D3_S2", None),
    "D4_S1": ("S1", "D", "m", "D4_S1", None), "D4_S2": ("S2", "D", "m", "D4_S2", None),
    "D3_D4S1": ("S1", "D", "m", "D3_D4S1", None), "D3_D4S2": ("S2", "D", "m", "D3_D4S2", None),
    "D5_S1_同日": ("S1", "S", "m", "D5_S1_同日", None), "D5_S2_同日": ("S2", "S", "m", "D5_S2_同日", None),
    "D5_S1_20日內": ("S1", "S", "m", "D5_S1_20日內", None), "D5_S2_20日內": ("S2", "S", "m", "D5_S2_20日內", None),
}
TAG = {"S1": 1, "S2": 2, "S1_當根停損": 11, "S2_當根停損": 12, "D3_S1": 31, "D3_S2": 32, "D4_S1": 41, "D4_S2": 42, "D3_D4S1": 43, "D3_D4S2": 44,
       "D5_S1_同日": 51, "D5_S2_同日": 52, "D5_S1_20日內": 53, "D5_S2_20日內": 54,
       "S1_H20": 220, "S1_H60": 260, "S2_H20": 320, "S2_H60": 360}
SYSNUM = {"S1": 1, "S2": 2}
SEGNUM = {"探索": 0, "確認": 1, "主全窗": 2, "早年": 3}
NAME = {"S1": "海龜系統 1（創 20 日新高買、跌破 10 日低點或 2N 停損賣）",
        "S2": "海龜系統 2（創 55 日新高買、跌破 20 日低點或 2N 停損賣）",
        "S1_當根停損": "另一讀法：S1 進場當根也判停損（只報）", "S2_當根停損": "另一讀法：S2 進場當根也判停損（只報）",
        "D3_S1": "D3：S1 且 ADX(14)>25（描述）", "D3_S2": "D3：S2 且 ADX(14)>25（描述）",
        "D4_S1": "D4：S1 收盤判、隔天開盤（描述）", "D4_S2": "D4：S2 收盤判、隔天開盤（描述）",
        "D3_D4S1": "D3×D4：D4_S1 且 ADX>25（描述）", "D3_D4S2": "D3×D4：D4_S2 且 ADX>25（描述）",
        "D5_S1_同日": "D5：S1 且 T＝營量/營飆訊號日（描述）", "D5_S2_同日": "D5：S2 且 T＝營量/營飆訊號日（描述）",
        "D5_S1_20日內": "D5 另一讀法：S1 且訊號 20 日內（描述）", "D5_S2_20日內": "D5 另一讀法：S2 且訊號 20 日內（描述）"}
JUDGE = ("S1", "S2")
SENT_SELF = "進出場照海龜原規則、盤中觸價成交；部位與加碼留組合層"
SENT_ALL = "單筆層通過 ≠ 組合會贏 0050"
NOTE_EARLY = ["早年含減資假飆股約 0.3%（剩 22 筆未解釋）",
              "上櫃 2007-07～12 除權息未還原；上櫃減資 2007～2012 為偵測、非官方；2005-01～2007-06 只有上市"]
LOG: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M:%S")


def pct(x, d=2):
    return "—" if x is None or not np.isfinite(x) else "{:+.{}f}%".format(x * 100, d)


# ═════════════ G2 N（Wilder 20，段內起算）═════════════
def natr(h, l, c, bad, n=NATR):
    h = np.asarray(h, float); l = np.asarray(l, float); c = np.asarray(c, float); nb = len(c)
    out = np.full(nb, np.nan)
    brk = np.asarray(bad, bool).copy()
    if nb:
        brk[0] = True
    starts = np.flatnonzero(brk).tolist() + [nb]
    for s, e in zip(starts[:-1], starts[1:]):
        if e - s <= n:
            continue
        j = np.arange(s + 1, e)
        tr = np.maximum.reduce([h[j] - l[j], np.abs(h[j] - c[j - 1]), np.abs(l[j] - c[j - 1])])
        v = tr[:n].mean(); out[s + n] = v
        for q in range(n, len(tr)):
            v = (v * (n - 1) + tr[q]) / n
            out[s + 1 + q] = v
    return out


def chan_low(l, M):
    """CL[j] ＝ min(l[j−M..j−1])；j ＜ M ⇒ nan。"""
    return pd.Series(np.asarray(l, float)).rolling(M, min_periods=M).min().shift(1).to_numpy(float)


def _nxt(mask, nb, BIG):
    out = np.full(nb + 2, BIG, np.int64)
    pos = np.where(mask, np.arange(nb), BIG)
    if nb:
        out[:nb] = np.minimum.accumulate(pos[::-1])[::-1]
    return out


# ═════════════ G3～G5 出場（向量化；fixture 對逐根迴圈）═════════════
def _end(nb, delisted, c):
    if delisted:
        return nb - 1, c[nb - 1], 4
    return -1, np.nan, 5


def sim_intra(o, l, c, bad, dnlb, idx, n0, CL, S, STOP, alt=False):
    """盤中觸價模式。S ＝ 進場根陣列、STOP ＝ 各自停損價。回 dict(eb, px, typ, post, both, obad)。"""
    nb = len(c); BIG = nb + 10; m = len(S)
    S = np.asarray(S, np.int64); STOP = np.asarray(STOP, float)
    eb = np.full(m, -1, np.int64); px = np.full(m, np.nan); typ = np.zeros(m, np.int8)
    post = np.zeros(m, bool); both = np.zeros(m, bool); obad = np.zeros(m, bool)
    if m == 0:
        return {"eb": eb, "px": px, "typ": typ, "post": post, "both": both, "obad": obad}
    nok = _nxt(~np.asarray(dnlb, bool), nb, BIG); nbd = _nxt(np.asarray(bad, bool), nb, BIG)
    delisted = bool((n0 - 1 - idx[-1]) >= GAP_END)
    eA, pA, tA = _end(nb, delisted, c)
    act = np.arange(m)
    if alt:
        hit = l[S] <= STOP
        q = act[hit]
        eb[q] = S[q]; px[q] = STOP[q]; typ[q] = 2
        act = act[~hit]
    d = 1
    while len(act):
        j = S[act] + d
        fin = j >= nb
        if fin.any():
            q = act[fin]; eb[q] = eA; px[q] = pA; typ[q] = tA
            act = act[~fin]; j = j[~fin]
            if not len(act):
                break
        fb = bad[j]
        if fb.any():
            q = act[fb]; eb[q] = j[fb] - 1; px[q] = c[j[fb] - 1]; typ[q] = 3
            act = act[~fb]; j = j[~fb]
            if not len(act):
                break
        clj = CL[j]
        if not np.isfinite(clj).all():
            raise RuntimeError("⛔ 持有中通道值缺（不應發生：進場前 M 根相連、持有中不跨壞根）")
        with np.errstate(invalid="ignore"):
            tc = l[j] < clj; ts = l[j] <= STOP[act]
        trig = tc | ts
        if trig.any():
            dl = trig & np.asarray(dnlb, bool)[j]
            if dl.any():
                q = act[dl]; jj = j[dl]
                x = nok[jj + 1]; b = nbd[jj + 1]
                post[q] = True
                f1 = (b <= x) & (b < nb)
                eb[q[f1]] = b[f1] - 1; px[q[f1]] = c[b[f1] - 1]; typ[q[f1]] = 3
                f2 = ~f1 & (x >= nb)
                eb[q[f2]] = eA; px[q[f2]] = pA; typ[q[f2]] = tA
                f3 = ~f1 & ~f2
                xx = x[f3]
                ox = o[np.minimum(xx, nb - 1)]
                okx = np.isfinite(ox) & (ox > 0)
                eb[q[f3]] = xx; px[q[f3]] = np.where(okx, ox, c[np.minimum(xx, nb - 1)]); obad[q[f3]] = ~okx
                typ[q[f3]] = np.where(ts[dl][f3], 2, 1)
            nd = trig & ~np.asarray(dnlb, bool)[j]
            if nd.any():
                q = act[nd]; jj = j[nd]
                oj = o[jj]; okj = np.isfinite(oj) & (oj > 0)
                pc = np.where(okj, np.minimum(oj, clj[nd]), clj[nd])
                ps = np.where(okj, np.minimum(oj, STOP[q]), STOP[q])
                a_c = tc[nd]; a_s = ts[nd]
                pr = np.where(a_c & a_s, np.minimum(pc, ps), np.where(a_c, pc, ps))
                ty = np.where(a_c & a_s, np.where(ps <= pc, 2, 1), np.where(a_c, 1, 2))
                eb[q] = jj; px[q] = pr; typ[q] = ty; both[q] = a_c & a_s; obad[q] = ~okj
            act = act[~trig]
        d += 1
    return {"eb": eb, "px": px, "typ": typ, "post": post, "both": both, "obad": obad}


def sim_close(o, l, c, bad, dnlb, idx, n0, CL, S, STOP):
    """D4 收盤判模式：進場根 S（開盤買），持有中第 j 根（j ≥ S）收盤 ＜ CL[j] 或 ≤ 停損 ⇒ 第 j＋1 根開盤賣。"""
    nb = len(c); BIG = nb + 10; m = len(S)
    S = np.asarray(S, np.int64); STOP = np.asarray(STOP, float)
    eb = np.full(m, -1, np.int64); px = np.full(m, np.nan); typ = np.zeros(m, np.int8)
    post = np.zeros(m, bool); both = np.zeros(m, bool); obad = np.zeros(m, bool)
    if m == 0:
        return {"eb": eb, "px": px, "typ": typ, "post": post, "both": both, "obad": obad}
    dnlb = np.asarray(dnlb, bool)
    nok = _nxt(~dnlb, nb, BIG); nbd = _nxt(np.asarray(bad, bool), nb, BIG)
    delisted = bool((n0 - 1 - idx[-1]) >= GAP_END)
    act = np.arange(m); d = 0
    while len(act):
        j = S[act] + d
        clj = CL[j]
        if not np.isfinite(clj).all():
            raise RuntimeError("⛔ D4 持有中通道值缺")
        tc = c[j] < clj; ts = c[j] <= STOP[act]
        trig = tc | ts
        last = j + 1 >= nb
        nbad = np.zeros(len(j), bool); nbad[~last] = bad[j[~last] + 1]
        # 觸發
        if trig.any():
            q = act[trig]; jj = j[trig]; ty = np.where(ts[trig], 2, 1); bt = tc[trig] & ts[trig]
            both[q] = bt
            la = last[trig]; nbb = nbad[trig]
            # 最後一根訊號
            if la.any():
                if delisted:
                    eb[q[la]] = jj[la]; px[q[la]] = c[jj[la]]; typ[q[la]] = 4
                else:
                    typ[q[la]] = 5
            f = ~la & nbb
            eb[q[f]] = jj[f]; px[q[f]] = c[jj[f]]; typ[q[f]] = 3
            g = ~la & ~nbb
            x = jj[g] + 1
            dl = dnlb[np.minimum(x, nb - 1)]
            qg = q[g]; tyg = ty[g]
            # 下一根正常
            n_ = ~dl
            xo = x[n_]; ox = o[xo]; okx = np.isfinite(ox) & (ox > 0)
            eb[qg[n_]] = xo; px[qg[n_]] = np.where(okx, ox, c[xo]); typ[qg[n_]] = tyg[n_]; obad[qg[n_]] = ~okx
            # 下一根鎖死跌停 ⇒ 順延
            if dl.any():
                qd = qg[dl]; xd = x[dl]; y = nok[xd]; b = nbd[xd]
                post[qd] = True
                f1 = (b <= y) & (b < nb)
                eb[qd[f1]] = b[f1] - 1; px[qd[f1]] = c[b[f1] - 1]; typ[qd[f1]] = 3
                f2 = ~f1 & (y >= nb)
                if f2.any():
                    if delisted:
                        eb[qd[f2]] = nb - 1; px[qd[f2]] = c[nb - 1]; typ[qd[f2]] = 4
                    else:
                        typ[qd[f2]] = 5
                f3 = ~f1 & ~f2
                yy = y[f3]; oy = o[np.minimum(yy, nb - 1)]; oky = np.isfinite(oy) & (oy > 0)
                eb[qd[f3]] = yy; px[qd[f3]] = np.where(oky, oy, c[np.minimum(yy, nb - 1)]); typ[qd[f3]] = tyg[dl][f3]; obad[qd[f3]] = ~oky
        # 未觸發：下一根壞 ⇒ 強制；最後一根 ⇒ 末根／資料尾
        nt = ~trig
        f = nt & ~last & nbad
        eb[act[f]] = j[f]; px[act[f]] = c[j[f]]; typ[act[f]] = 3
        g = nt & last
        if g.any():
            if delisted:
                eb[act[g]] = nb - 1; px[act[g]] = c[nb - 1]; typ[act[g]] = 4
            else:
                typ[act[g]] = 5
        keep = nt & ~last & ~nbad
        act = act[keep]; d += 1
    return {"eb": eb, "px": px, "typ": typ, "post": post, "both": both, "obad": obad}


def sim_ref(o, l, c, bad, dnlb, idx, n0, CL, s, stop, mode, alt=False):
    """逐根迴圈版（fixture 用）：回 (eb, px, typ, post, both)。"""
    nb = len(c); delisted = (n0 - 1 - idx[-1]) >= GAP_END

    def endp():
        return (nb - 1, c[nb - 1], 4) if delisted else (-1, np.nan, 5)

    def defer(x, ty):          # 從第 x 根起找第一根非鎖死可賣
        y = x
        while y < nb:
            if bad[y]:
                return y - 1, c[y - 1], 3
            if not dnlb[y]:
                p = o[y] if (np.isfinite(o[y]) and o[y] > 0) else c[y]
                return y, p, ty
            y += 1
        e = endp()
        return e
    if mode == "S":
        if alt and l[s] <= stop:
            return s, stop, 2, False, False
        j = s + 1
        while True:
            if j >= nb:
                e = endp(); return e[0], e[1], e[2], False, False
            if bad[j]:
                return j - 1, c[j - 1], 3, False, False
            tc = l[j] < CL[j]; ts = l[j] <= stop
            if tc or ts:
                if dnlb[j]:
                    e = defer(j + 1, 2 if ts else 1)
                    return e[0], e[1], e[2], True, False
                oj = o[j]; ok = np.isfinite(oj) and oj > 0
                pc = min(oj, CL[j]) if ok else CL[j]; ps = min(oj, stop) if ok else stop
                if tc and ts:
                    return j, min(pc, ps), (2 if ps <= pc else 1), False, True
                return (j, pc, 1, False, False) if tc else (j, ps, 2, False, False)
            j += 1
    j = s
    while True:
        tc = c[j] < CL[j]; ts = c[j] <= stop
        if tc or ts:
            ty = 2 if ts else 1
            if j + 1 >= nb:
                return (j, c[j], 4, False, tc and ts) if delisted else (-1, np.nan, 5, False, tc and ts)
            if bad[j + 1]:
                return j, c[j], 3, False, tc and ts
            if dnlb[j + 1]:
                e = defer(j + 1, ty)
                return e[0], e[1], e[2], True, tc and ts
            p = o[j + 1] if (np.isfinite(o[j + 1]) and o[j + 1] > 0) else c[j + 1]
            return j + 1, p, ty, False, tc and ts
        if j + 1 >= nb:
            e = endp(); return e[0], e[1], e[2], False, False
        if bad[j + 1]:
            return j, c[j], 3, False, False
        j += 1


# ═════════════ fixture ═════════════
def selftest():
    msgs = []
    rng = np.random.default_rng(7)
    nchk = 0
    for rep in range(300):
        nb = int(rng.integers(40, 160)); n0 = nb + int(rng.integers(0, 12))
        c = 50 * np.exp(np.cumsum(rng.normal(0, 0.03, nb)))
        h = c * (1 + rng.uniform(0, 0.04, nb)); l = c * (1 - rng.uniform(0, 0.04, nb))
        o = l + (h - l) * rng.uniform(0, 1, nb)
        o[rng.random(nb) < 0.03] = np.nan
        bad = rng.random(nb) < 0.03; bad[0] = True
        dnlb = rng.random(nb) < 0.08
        idx = np.sort(rng.choice(np.arange(n0), nb, replace=False))
        M = int(rng.choice([3, 10])); CL = chan_low(l, M)
        # 通道值缺的根當作壞（保證持有中有值）
        for k in range(nb):
            if not np.isfinite(CL[k]):
                bad[k] = True if k > 0 else bad[k]
        Nv = natr(h, l, c, bad)
        cand = np.array([s for s in range(1, nb - 1) if not bad[s] and np.isfinite(Nv[s - 1]) and np.isfinite(CL[s]) and all(not bad[q] for q in range(max(1, s - M + 1), s + 1))], np.int64)
        if not len(cand):
            continue
        Pp = np.where(np.isfinite(o[cand]), o[cand], c[cand]) * rng.uniform(1.0, 1.03, len(cand))
        stop = Pp - 2 * Nv[cand - 1] * rng.uniform(0.2, 1.5, len(cand))
        for alt in (False, True):
            r = sim_intra(o, l, c, bad, dnlb, idx, n0, CL, cand, stop, alt=alt)
            for q, s in enumerate(cand):
                e2 = sim_ref(o, l, c, bad, dnlb, idx, n0, CL, int(s), float(stop[q]), "S", alt=alt)
                assert (r["eb"][q], r["typ"][q], r["post"][q], r["both"][q]) == (e2[0], e2[2], e2[3], e2[4]), (rep, alt, s, r["eb"][q], r["typ"][q], e2)
                assert (np.isnan(r["px"][q]) and np.isnan(e2[1])) or abs(r["px"][q] - e2[1]) < 1e-12
                nchk += 1
        r = sim_close(o, l, c, bad, dnlb, idx, n0, CL, cand, stop)
        for q, s in enumerate(cand):
            e2 = sim_ref(o, l, c, bad, dnlb, idx, n0, CL, int(s), float(stop[q]), "D")
            assert (r["eb"][q], r["typ"][q], r["post"][q], r["both"][q]) == (e2[0], e2[2], e2[3], e2[4]), (rep, "D", s, r["eb"][q], r["typ"][q], e2)
            assert (np.isnan(r["px"][q]) and np.isnan(e2[1])) or abs(r["px"][q] - e2[1]) < 1e-12
            nchk += 1
    msgs.append(f"F1 向量化出場（盤中觸價、當根停損、收盤判；鎖死跌停順延、壞根、缺開盤、下市／資料尾）＝ 逐根迴圈（{nchk} 筆）")
    # N：Wilder 遞迴 ＝ 逐根定義
    h = rng.uniform(10, 12, 80); l = h - rng.uniform(0, 1, 80); c = (h + l) / 2; bad = np.zeros(80, bool); bad[0] = True; bad[40] = True
    Nv = natr(h, l, c, bad)
    tr = lambda j: max(h[j] - l[j], abs(h[j] - c[j - 1]), abs(l[j] - c[j - 1]))  # noqa: E731
    v = np.mean([tr(j) for j in range(1, 21)]); assert abs(Nv[20] - v) < 1e-12 and np.isnan(Nv[19])
    for j in range(21, 40):
        v = (v * 19 + tr(j)) / 20; assert abs(Nv[j] - v) < 1e-12
    assert np.isnan(Nv[40:60]).all() and np.isfinite(Nv[60])
    msgs.append("F2 N ＝ 前 20 個 TR 平均為種子、(N×19＋TR)÷20 遞迴、壞根重起")
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
    sid_, res = RT.stock_job((wn, sid))                    # ⭐ 頻率表同一支：事件、剔除狀態、ADX、D5 旗標
    if res is None:
        return sid, None
    W = RT._G[wn]; cal = W["cal"]; n0 = W["n0"]; i = W["ix"][sid]
    import backtest.data as D
    D.DATA = W["data"]
    B = R.load_bars(sid, W["mk"].get(sid, "twse"), cal)
    df = B["df"]; idx = B["idx"].astype(np.int64); nb = len(idx)
    o, h, l, c = (np.asarray(B[k], float) for k in ("o", "h", "l", "c"))
    bad = np.asarray(B["next_bad"][:nb] == np.arange(nb), bool)
    for p_ in W["BADPOS"].get(sid, ()):
        k = int(np.searchsorted(idx, p_, "left"))
        if k < nb:
            bad[k] = True
    Nv = natr(h, l, c, bad)
    gate = np.asarray(P.Frame(df, set()).gate, bool)
    PV = np.asarray(W["PV"][i][:n0], bool); TRD = W["TRD"][i]; O = W["O"][i]; UPL = W["UPL"][i]; DNL = W["DNL"][i]
    dnlb = np.asarray(DNL[idx], bool)
    pop = gate & PV
    kk = np.arange(nb); T = idx
    Nprev = np.r_[np.nan, Nv[:-1]]
    with np.errstate(invalid="ignore"):
        okS = pop[T] & ~bad & np.isfinite(O[T]) & (np.nan_to_num(O[T]) > 0) & ~UPL[T] & np.isfinite(o) & (o > 0) & np.isfinite(Nprev) & (kk >= 1)
        okD = np.zeros(nb, bool)
        q = kk[:-1]; s1 = q + 1; e1 = T[q] + 1
        okD[q] = (pop[T[q]] & ~bad[q] & (idx[s1] == e1) & ~bad[s1] & (e1 < n0))
        e_ = np.minimum(e1, n0 - 1)
        okD[q] &= TRD[e_] & np.isfinite(O[e_]) & (np.nan_to_num(O[e_]) > 0) & ~UPL[e_] & np.isfinite(o[s1]) & (o[s1] > 0) & np.isfinite(Nv[q])
    entS = np.zeros(n0, bool); entS[T[okS]] = True
    entD = np.zeros(n0, bool); entD[T[okD]] = True
    ev = res["ev"]
    # N缺值剔除計數（保留事件中）
    nex = {}
    for cell in ("S1", "S2", "D4_S1", "D4_S2"):
        msk = okD if cell.startswith("D4") else okS
        nex[cell] = int(sum(1 for e in ev[cell] if e["st"] == "保留" and not msk[e["k"]]))
    out = {"entS": entS, "entD": entD, "pop": pop, "ev": ev, "nex": nex, "nb": nb}
    if dry:
        return sid, out
    # ── 對照式（全部可進場根）：S 模式、D4 模式
    CLs = {sy: chan_low(l, M) for sy, M in MS.items()}
    sS = kk[okS]; stopS = o[sS] - 2.0 * Nprev[sS]
    sD = kk[okD] + 1; stopD = o[sD] - 2.0 * Nv[kk[okD]]
    TS = T[sS]; TD = T[kk[okD]]
    C = {}
    for sy in MS:
        for ver, alt in (("m", False), ("a", True)):
            r = sim_intra(o, l, c, bad, dnlb, idx, n0, CLs[sy], sS, stopS, alt=alt)
            C[f"{sy}{ver}"] = (TS, sS, o[sS], r)
        r = sim_close(o, l, c, bad, dnlb, idx, n0, CLs[sy], sD, stopD)
        C[f"D4{sy}"] = (TD, sD, o[sD], r)
    for key, (Tq, sq, Pq, r) in C.items():
        Rr = np.full(n0, np.nan, np.float64); Ty = np.zeros(n0, np.int8); Hh = np.full(n0, -1, np.int16)
        ok = r["eb"] >= 0
        Rr[Tq[ok]] = r["px"][ok] / Pq[ok] - 1.0
        Ty[Tq] = r["typ"]
        Hh[Tq[ok]] = (idx[r["eb"][ok]] - idx[sq[ok]]).astype(np.int16)
        out[f"C_{key}"] = (Rr, Ty, Hh)
        out[f"Cn_{key}"] = {"順延": int(r["post"].sum()), "同根皆觸": int(r["both"].sum()), "開盤缺用替代": int(r["obad"].sum())}
    # ── 固定抱 H（S 對照：T 開盤進場）
    cf = df["close"].to_numpy(float)
    cff = pd.Series(cf).ffill().to_numpy()
    badcal = np.zeros(n0, bool); badcal[idx[bad]] = True
    csb = np.cumsum(badcal).astype(np.int64)
    kH = np.searchsorted(idx, np.arange(n0), "right") - 1
    gap = np.zeros(n0, bool)
    okk = (kH >= 0) & (kH < nb - 1)
    pp = np.arange(n0)[okk]; kq = kH[okk]
    gap[pp] = (idx[kq + 1] - idx[kq] - 1 >= 5) & (pp - idx[kq] >= 5)
    Ocal = np.full(n0, np.nan); Ocal[idx] = o
    GBRK = {}
    for H in HD:
        g = np.full(n0, np.nan)
        t = np.arange(n0 - H)
        brk = np.ones(n0, bool)
        brk[t] = (csb[t + H] - csb[t] > 0) | gap[t + H]
        GBRK[H] = brk
        with np.errstate(invalid="ignore", divide="ignore"):
            g[t] = cff[t + H] / Ocal[t] - 1.0
        g[brk] = np.nan; g[~entS] = np.nan
        out[f"G{H}"] = g
    # ── 事件式（S 格：買價 max(o, 前N日最高)）
    EVR = {}
    for sy, N in NS.items():
        ks = np.array(sorted({e["k"] for e in ev[sy] if e["st"] == "保留"} |
                             {e["k"] for c_ in (f"D3_{sy}", f"D5_{sy}_同日", f"D5_{sy}_20日內") for e in ev[c_] if e["st"] == "保留"}), np.int64)
        ks = ks[okS[ks]] if len(ks) else ks
        pm = RT.prev_high(h, N)
        Pk = np.maximum(o[ks], pm[ks]); stk = Pk - 2.0 * Nprev[ks]
        raw = np.zeros(nb + REHIGH + 2, bool); rk, _ = RT.detect(h, c, bad, N); raw[rk] = True
        for ver, alt in (("m", False), ("a", True)):
            r = sim_intra(o, l, c, bad, dnlb, idx, n0, CLs[sy], ks, stk, alt=alt)
            d_ = {}
            for q, k in enumerate(ks):
                e_b = int(r["eb"][q]); ty = int(r["typ"][q]); Tk = int(idx[k])
                hi_end = e_b if e_b >= 0 else nb - 1
                rec = {"k": int(k), "P": float(Pk[q]), "pm": float(pm[k]), "Nprev": float(Nprev[k]), "stop": float(stk[q]),
                       "eb": e_b, "typ": ty, "R": float(r["px"][q] / Pk[q] - 1.0) if e_b >= 0 else np.nan,
                       "sell": int(idx[e_b]) if e_b >= 0 else -1, "hold": int(idx[e_b] - Tk) if e_b >= 0 else -1,
                       "mtm": float(c[nb - 1] / Pk[q] - 1.0) if ty == 5 else np.nan,
                       "post": bool(r["post"][q]), "both": bool(r["both"][q]), "obad": bool(r["obad"][q]),
                       "fail": bool((c[k:hi_end + 1] < pm[k]).any()),
                       "rehigh": bool(ty == 2 and e_b >= 0 and raw[e_b + 1:e_b + 1 + REHIGH].any())}
                for H in HD:
                    tH = Tk + H
                    rec[f"G{H}"] = float(cff[tH] / Pk[q] - 1.0) if (tH < n0 and not GBRK[H][Tk]) else np.nan
                d_[Tk] = rec
            EVR[f"{sy}{ver}"] = d_
    # D4 事件 ＝ D4 對照式同一筆（進場同為 T＋1 開盤）
    for sy in MS:
        Tq, sq, Pq, r = C[f"D4{sy}"]
        d_ = {}
        pos = {int(t): q for q, t in enumerate(Tq)}
        for e in ev[f"D4_{sy}"] + ev[f"D3_D4{sy}"]:
            if e["st"] != "保留" or e["T"] not in pos:
                continue
            q = pos[e["T"]]; e_b = int(r["eb"][q]); ty = int(r["typ"][q])
            d_[int(e["T"])] = {"k": int(e["k"]), "P": float(Pq[q]), "pm": float(e["前N日最高"]), "Nprev": float(Nv[e["k"]]), "stop": float(stopD[q]),
                               "eb": e_b, "typ": ty, "R": float(r["px"][q] / Pq[q] - 1.0) if e_b >= 0 else np.nan,
                               "sell": int(idx[e_b]) if e_b >= 0 else -1, "hold": int(idx[e_b] - idx[sq[q]]) if e_b >= 0 else -1,
                               "mtm": float(c[nb - 1] / Pq[q] - 1.0) if ty == 5 else np.nan,
                               "post": bool(r["post"][q]), "both": bool(r["both"][q]), "obad": bool(r["obad"][q]), "fail": False, "rehigh": False}
        EVR[f"D4{sy}"] = d_
    out["EVR"] = EVR
    return sid, out


# ═════════════ 統計 ═════════════
def x_stats(x, key):
    x = np.asarray(x, float); key = np.asarray(key)
    n = len(x)
    if n == 0:
        return {"n": 0, "n_eff": 0, "出口": "出口①", "結果": "樣本不足以分辨"}
    cs = R.cl_stats(x, key)
    m = cs["mean"]; se = cs["se"]; ng = cs["months"]; ne = int(min(n, ng))
    ex, rs = UO.verdict(m, se, ne)
    mm = pd.Series(x).groupby(key).mean()
    return {"n": int(n), "X̄": float(m), "中位": float(np.median(x)), "X勝率": float((x > 0).mean()), "se": float(se),
            "lo": float(m - Z95 * se), "hi": float(m + Z95 * se), "群數": int(ng), "n_eff": ne, "出口": ex, "結果": rs,
            "逐月平均之中位": float(mm.median()), "逐月中位與平均同號": bool(np.sign(mm.median()) == np.sign(m)),
            "X̄−成本": float(m - COST), "bonf_z": ZB, "bonf_lo": float(m - ZB * se), "bonf_hi": float(m + ZB * se)}


def trade_stats(Rn, hold, typ, pre=""):
    Rn = np.asarray(Rn, float)
    o = {}
    if len(Rn):
        w = Rn[Rn > 0]; l_ = Rn[Rn <= 0]
        o.update({pre + "淨報酬平均": float(Rn.mean()), pre + "淨報酬中位": float(np.median(Rn)), pre + "勝率": float((Rn > 0).mean()),
                  pre + "平均賺": float(w.mean()) if len(w) else None, pre + "平均賠": float(l_.mean()) if len(l_) else None,
                  pre + "平均賺賠比": float(w.mean() / abs(l_.mean())) if len(w) and len(l_) and l_.mean() != 0 else None,
                  pre + "平均持有天數": float(np.mean(hold)), pre + "持有天數中位": float(np.median(hold)),
                  pre + "持有天數p90": float(np.percentile(hold, 90))})
        cnt = Counter(np.asarray(typ).tolist())
        for k_, nm in TYP.items():
            if k_ == 5:
                continue
            o[f"{pre}出場占比_{nm}"] = float(cnt.get(k_, 0) / len(Rn))
    return o


def sentence(cell, st, early=False):
    tail = [SENT_SELF, SENT_ALL] + (NOTE_EARLY if early else [])
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


def freq_frame(EVS, cal):
    allrows = []
    for cell in ("S1", "S2", "D4_S1", "D4_S2"):
        rows = sorted([e for ev in EVS for e in ev[cell]], key=lambda x: (x["T"], x["sid"]))
        if not rows:
            continue
        dfo = pd.DataFrame(rows)
        dfo["T"] = [str(cal[x].date()) for x in dfo["T"]]
        dfo.insert(0, "格", cell)
        allrows.append(dfo)
    buf = io.StringIO()
    pd.concat(allrows, ignore_index=True).to_csv(buf, index=False)
    buf.seek(0)
    return pd.read_csv(buf, dtype=str, keep_default_na=False)


# ═════════════ 主程式 ═════════════
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--dry", action="store_true", help="乾跑：只驗事件重現、對照池、N缺值；⛔ 不算任何出場與報酬")
    a = ap.parse_args()
    if a.limit and not a.dry:
        raise SystemExit("⛔ 裁定 seq366：不准含報酬的小樣本試跑；--limit 只能配 --dry")
    t0 = time.time()
    out = OUT
    os.makedirs(os.path.join(out, "events"), exist_ok=True)
    reg = RT.reg_check()
    log(f"[登錄] {reg}（sha {REG_SHA} 已驗）｜{'乾跑' if a.dry else '本體'}開跑 {now_tpe()}")
    fx = selftest()
    J = {"性質": "海龜 Donchian 突破 seq2 事件層正式跑（單筆層；判定格 S1、S2；探索、確認各自報、主全窗參考、早年描述）",
         "登錄": f"台股策略線 seq2 sha {REG_SHA}", "裁定": "seq366 發號、seq367 發 seq2；N_前段 ＋2",
         "成本": COST, "種子": {"對照": SEED_CTRL, "假訊號": SEED_FAKE}, "Bonferroni": {"族N": N_FAM, "z": ZB},
         "fixture": fx, "讀法_頻率表": RT.__doc__.split("═══ 讀法")[1], "讀法": __doc__.split("═══ 讀法")[1], "世界": {}, "時點": {"本體開跑": now_tpe()}}
    MAIN = []; DESC = []; BY = []; FK = []
    for wn in ("主", "早年"):
        W = AT.load_world(wn); cal = W["cal"]; n0 = W["n0"]
        win = {}
        for sg, (x_, y_) in RT.SEGS[wn].items():
            p0 = int(cal.searchsorted(pd.Timestamp(x_)))
            p1 = n0 - 2 if y_ is None else min(n0 - 2, int(cal.searchsorted(pd.Timestamp(y_), side="right")) - 1)
            win[sg] = (p0, p1)
        W["win"] = win
        W["SIGPOS"], W["SIGPOS_YF"], cover, nsig = RU.load_sig(wn, cal)
        RT._G[wn] = W
        sids = W["sids"][:a.limit] if a.limit else W["sids"]
        S = len(W["sids"]); ix = W["ix"]
        ENTS = np.zeros((n0, S), bool); ENTD = np.zeros((n0, S), bool); POP = np.zeros((n0, S), bool)
        CK = ["S1m", "S1a", "S2m", "S2a", "D4S1", "D4S2"]
        CR = {k: np.full((n0, S), np.nan) for k in CK}
        CT = {k: np.zeros((n0, S), np.int8) for k in CK}
        CH = {k: np.full((n0, S), -1, np.int16) for k in CK}
        G = {H: np.full((n0, S), np.nan) for H in HD}
        CN = {k: Counter() for k in CK}
        EVS = {}; EVR = {}; NEX = Counter()
        with Pool(a.procs) as pool:
            for k_, (sid, r) in enumerate(pool.imap_unordered(stock_job, [(wn, s_, a.dry) for s_ in sids], chunksize=8)):
                if r is not None:
                    j = ix[sid]
                    ENTS[:, j] = r["entS"]; ENTD[:, j] = r["entD"]; POP[:, j] = r["pop"]
                    EVS[sid] = r["ev"]; NEX.update(r["nex"])
                    if not a.dry:
                        for kk in CK:
                            CR[kk][:, j], CT[kk][:, j], CH[kk][:, j] = r[f"C_{kk}"]
                            CN[kk].update(r[f"Cn_{kk}"])
                        for H in HD:
                            G[H][:, j] = r[f"G{H}"]
                        EVR[sid] = r["EVR"]
                if (k_ + 1) % 400 == 0:
                    log(f"  {wn} … {k_ + 1}／{len(sids)}｜{time.time() - t0:.0f}s")
        log(f"[{wn}] 逐股完 {len(EVS)} 檔｜{time.time() - t0:.0f}s")
        # ── 查核 1：事件 ＝ 已提交頻率表事件檔（逐列逐欄）
        for s_, ev in EVS.items():
            for cell in ("S1", "S2", "D4_S1", "D4_S2"):
                for e in ev[cell]:
                    assert e["sid"] == s_
        mine = freq_frame(list(EVS.values()), cal)
        ref = pd.read_csv(os.path.join(FREQ, f"events_{wn}.csv.gz"), dtype=str, keep_default_na=False)
        if a.limit:
            ref = ref[ref["sid"].isin(set(sids))].reset_index(drop=True)
        same = list(ref.columns) == list(mine.columns) and ref.shape == mine.shape and (ref.values == mine.values).all()
        if not same:
            raise SystemExit(f"⛔ {wn} 重新偵測 ≠ 已提交頻率表事件檔（{mine.shape} vs {ref.shape}）⇒ 中止（未讀任何報酬）")
        log(f"[查核1] {wn}：重新偵測與已提交頻率表事件檔逐列逐欄相同（{len(ref):,} 列）")
        # ── 查核 2：保留事件（N 有值者）都在本支母體與可進場矩陣內
        bad_st = Counter()
        for s_, ev in EVS.items():
            j = ix[s_]
            for cell in ("S1", "S2", "D4_S1", "D4_S2"):
                for e in ev[cell]:
                    if e["st"] == "保留" and not POP[e["T"], j]:
                        bad_st[cell] += 1
        assert not bad_st, f"⛔ 保留事件但不在母體：{bad_st}"
        log(f"[查核2] 保留事件全在母體；N缺值／開盤缺 剔除（全世界時序、不分段）：{dict(NEX)}")
        RAW = {}
        for fam, cells in (("S1", ("S1",)), ("S2", ("S2",)), ("D4S1", ("D4_S1",)), ("D4S2", ("D4_S2",))):
            Mx = np.zeros((n0, S), bool)
            for s_, ev in EVS.items():
                for cell in cells:
                    for e in ev[cell]:
                        Mx[e["T"], ix[s_]] = True
            RAW[fam] = Mx
        BASES = POP & ENTS; BASED = POP & ENTD
        moni = np.asarray(cal.year * 12 + cal.month); years = np.asarray(cal.year); dates = np.array([str(d.date()) for d in cal])
        Wj = {"資料": W["data"], "日曆": [str(cal[0].date()), str(cal[-1].date())], "檔數": len(sids), "可用檔數": len(EVS),
              "段": {sg: f"{cal[p].date()}～{cal[q].date()}" for sg, (p, q) in win.items()}, "N缺值剔除(全時序)": dict(NEX), "格": {}}
        if a.dry:
            for sg, (p0, p1) in win.items():
                ps = BASES[p0:p1 + 1].sum(axis=1); pdd = BASED[p0:p1 + 1].sum(axis=1)
                kept = {c_: sum(1 for ev in EVS.values() for e in ev[c_] if e["st"] == "保留" and p0 <= e["T"] <= p1) for c_ in ("S1", "S2", "D4_S1", "D4_S2")}
                log(f"[乾跑 {wn}/{sg}] S 對照基池每日中位 {int(np.median(ps[ps > 0]))}、D4 {int(np.median(pdd[pdd > 0]))}｜保留事件 {kept}")
            J["世界"][wn] = Wj
            continue
        if "第一次讀報酬" not in J["時點"]:
            J["時點"]["第一次讀報酬"] = now_tpe()
        POOL = {"S1m": BASES & np.isfinite(CR["S1m"]), "S1a": BASES & np.isfinite(CR["S1a"]),
                "S2m": BASES & np.isfinite(CR["S2m"]), "S2a": BASES & np.isfinite(CR["S2a"]),
                "D4S1": BASED & np.isfinite(CR["D4S1"]), "D4S2": BASED & np.isfinite(CR["D4S2"])}
        log(f"[對照池] 第一次讀報酬 {J['時點']['第一次讀報酬']}｜S1 每日對照池中位 {int(np.median(POOL['S1m'].sum(axis=1)[POOL['S1m'].sum(axis=1) > 0]))} 檔｜{time.time() - t0:.0f}s")
        crc = {s_: zlib.crc32(s_.encode("utf-8")) for s_ in W["sids"]}
        TR = {}
        for cname, (sy, mode, ver, src, _) in CELLDEF.items():
            ck = f"{sy}{ver}" if mode == "S" else f"D4{sy}"
            ek = ck
            fam = sy if mode == "S" else f"D4{sy}"
            smp = UO.Sampler(POOL[ck], RAW[fam])
            rows = []; skip = Counter()
            for s_, ev in EVS.items():
                j = ix[s_]; last_sell = -10 ** 9; open_end = False
                er = EVR[s_][ek]
                for e in sorted([x for x in ev[src] if x["st"] == "保留"], key=lambda x: x["T"]):
                    T = e["T"]
                    rec = er.get(T)
                    if rec is None:
                        skip["N缺值"] += 1; continue
                    if open_end:
                        skip["前筆資料尾未出場"] += 1; continue
                    if (mode == "S" and T <= last_sell) or (mode == "D" and T < last_sell):
                        skip["持有中略過"] += 1; continue
                    rows.append((j, T, e, rec))
                    if rec["typ"] == 5:
                        open_end = True
                    else:
                        last_sell = rec["sell"]
            rows.sort(key=lambda z: (z[1], W["sids"][z[0]]))
            # D1／D2（子集讀法）旗標：同檔上一筆
            prev = {}
            d1 = []; d2 = []
            for z in sorted(rows, key=lambda z: (z[0], z[1])):
                p_ = prev.get(z[0])
                d1.append(((z[0], z[1]), p_ is None or not (np.isfinite(p_["R"]) and p_["R"] - COST > 0)))
                d2.append(((z[0], z[1]), p_ is None or p_["fail"]))
                prev[z[0]] = z[3]
            d1 = dict(d1); d2 = dict(d2)
            n = len(rows)
            ii = np.array([z[0] for z in rows], np.int64); TT = np.array([z[1] for z in rows], np.int64)
            Rr = np.array([z[3]["R"] for z in rows], float); ty = np.array([z[3]["typ"] for z in rows], np.int8)
            Hk = np.array([z[3]["hold"] for z in rows], np.int64)
            cm = np.full(n, np.nan); cn = np.zeros(n, np.int64); cids = []; cty = []; chd = []
            for q, (j, T, e, rec) in enumerate(rows):
                sid = W["sids"][j]
                cs = smp.draw(T, j, [SEED_CTRL, TAG[cname], T, crc[sid]])
                cn[q] = len(cs)
                if len(cs):
                    cm[q] = float(CR[ck][T, cs].mean()); cty.append(CT[ck][T, cs]); chd.append(CH[ck][T, cs])
                cids.append(";".join(W["sids"][x] for x in cs) if cname in JUDGE or cname.startswith("D4_") else "")
            Xv = Rr - cm
            fr = pd.DataFrame({"sid": [W["sids"][x] for x in ii], "market": [W["mk"].get(W["sids"][x], "twse") for x in ii],
                               "T": dates[TT] if n else [], "進場日": (dates[TT] if mode == "S" else dates[np.minimum(TT + 1, n0 - 1)]) if n else [],
                               "買價": [z[3]["P"] for z in rows], "前N日最高": [z[3]["pm"] for z in rows], "N": [z[3]["Nprev"] for z in rows],
                               "停損價": [z[3]["stop"] for z in rows],
                               "出場日": [dates[z[3]["sell"]] if z[3]["sell"] >= 0 else "" for z in rows], "出場種類": [TYP[int(x)] for x in ty],
                               "持有天數": Hk, "R": Rr, "R淨": Rr - COST, "帳面R(資料尾)": [z[3]["mtm"] for z in rows],
                               "順延(鎖死跌停)": [z[3]["post"] for z in rows], "同根皆觸": [z[3]["both"] for z in rows],
                               "開盤缺用替代": [z[3]["obad"] for z in rows], "停損後20日內再突破": [z[3]["rehigh"] for z in rows],
                               "回到突破前區間": [z[3]["fail"] for z in rows],
                               "D1做(上一筆沒賺)": [d1[(z[0], z[1])] for z in rows], "D2做(上一筆失敗)": [d2[(z[0], z[1])] for z in rows],
                               "ADX參考": [z[2]["ADX參考"] for z in rows], "ADX>25": [z[2]["ADX>25"] for z in rows],
                               "對照數": cn, "對照平均R": cm, "X": Xv, "種子格標": TAG[cname], "對照代號": cids})
            if mode == "S":
                for kf in ("D5_同日", "D5_20日內", "D5_同日_營飆", "D5_20日內_營飆"):
                    fr[kf] = [bool(z[2].get(kf, False)) for z in rows]
            TR[cname] = {"fr": fr, "i": ii, "T": TT, "X": Xv, "R": Rr, "ty": ty, "H": Hk, "cm": cm, "skip": dict(skip),
                         "cty": np.concatenate(cty) if cty else np.zeros(0), "chd": np.concatenate(chd) if chd else np.zeros(0),
                         "d1": fr["D1做(上一筆沒賺)"].to_numpy(bool) if n else np.zeros(0, bool),
                         "d2": fr["D2做(上一筆失敗)"].to_numpy(bool) if n else np.zeros(0, bool), "ck": ck, "mode": mode, "sy": sy}
            log(f"  [{wn}] {cname}：進場 {n} 筆（{dict(skip)}）｜資料尾未出場 {int((ty == 5).sum())}｜無對照 {int((cn == 0).sum())}｜{time.time() - t0:.0f}s")
        # 固定抱 H：判定格同一批進場
        for sy in JUDGE:
            A0 = TR[sy]
            smpH = {H: UO.Sampler(BASES & np.isfinite(G[H]), RAW[sy]) for H in HD}
            for H in HD:
                g = np.array([EVR[W["sids"][j]][f"{sy}m"][int(T)][f"G{H}"] for j, T in zip(A0["i"], A0["T"])], float)
                cm = np.full(len(g), np.nan); cn = np.zeros(len(g), np.int64)
                for q, (j, T) in enumerate(zip(A0["i"], A0["T"])):
                    cs = smpH[H].draw(int(T), int(j), [SEED_CTRL, TAG[f"{sy}_H{H}"], int(T), crc[W["sids"][j]]])
                    cn[q] = len(cs)
                    if len(cs):
                        cm[q] = float(G[H][T, cs].mean())
                A0["fr"][f"固定抱{H}_R"] = g; A0["fr"][f"固定抱{H}_對照"] = cm; A0["fr"][f"固定抱{H}_X"] = g - cm; A0["fr"][f"固定抱{H}_對照數"] = cn
                A0[f"X{H}"] = g - cm; A0[f"G{H}"] = g
        for cname, d_ in TR.items():
            d_["fr"].to_csv(os.path.join(out, "events", f"trades_{wn}_{cname}.csv.gz"), index=False, compression={"method": "gzip", "compresslevel": 6})
        # ── 各段統計
        keptS = {}
        for sy in JUDGE:
            keptS[sy] = {ix[s_]: np.array(sorted(e["T"] for e in ev[sy] if e["st"] == "保留"), np.int64) for s_, ev in EVS.items()}
        for sg, (p0, p1) in win.items():
            yrs = (cal[p1] - cal[p0]).days / 365.25
            segj = {}
            for cname, d_ in TR.items():
                inseg = (d_["T"] >= p0) & (d_["T"] <= p1)
                okx = inseg & np.isfinite(d_["X"])
                st = x_stats(d_["X"][okx], moni[d_["T"][okx]])
                fin = inseg & np.isfinite(d_["R"])
                ty_all = d_["ty"][inseg]
                st.update({"進場筆數(含未出場)": int(inseg.sum()), "資料尾未出場": int((inseg & (d_["ty"] == 5)).sum()),
                           "資料尾未出場_帳面R平均": float(np.nanmean(d_["fr"]["帳面R(資料尾)"].to_numpy(float)[inseg & (d_["ty"] == 5)])) if (inseg & (d_["ty"] == 5)).any() else None,
                           "無對照剔除": int((fin & ~np.isfinite(d_["X"])).sum()), "相異檔數": int(len(set(d_["i"][okx].tolist()))),
                           "每年事件數": round(int(okx.sum()) / yrs, 2), "R̄": float(d_["R"][okx].mean()) if okx.any() else None,
                           "對照R̄": float(d_["cm"][okx].mean()) if okx.any() else None,
                           "對照淨報酬平均": float(d_["cm"][okx].mean() - COST) if okx.any() else None})
                for k_, nm in TYP.items():
                    st[f"出場占比含資料尾_{nm}"] = float((ty_all == k_).mean()) if len(ty_all) else None
                st.update(trade_stats(d_["R"][okx] - COST, d_["H"][okx], d_["ty"][okx]))
                frs = d_["fr"]
                if okx.any():
                    st2 = okx & (d_["ty"] == 2)
                    st["停損筆數"] = int(st2.sum())
                    st["停損後20日內又創新高比例"] = float(frs["停損後20日內再突破"].to_numpy(bool)[st2].mean()) if st2.any() and d_["mode"] == "S" else None
                    st["順延筆數"] = int(frs["順延(鎖死跌停)"].to_numpy(bool)[okx].sum()); st["同根皆觸筆數"] = int(frs["同根皆觸"].to_numpy(bool)[okx].sum())
                    st["開盤缺用替代筆數"] = int(frs["開盤缺用替代"].to_numpy(bool)[okx].sum())
                yr = years[d_["T"][okx]]
                st["逐年"] = {str(y): {"n": int((yr == y).sum()), "X̄": float(d_["X"][okx][yr == y].mean()),
                                      "持有均": float(d_["H"][okx][yr == y].mean())} for y in sorted(set(yr.tolist()))}
                for y, q in st["逐年"].items():
                    BY.append({"世界": wn, "段": sg, "格": cname, "年": y, **q})
                if cname in JUDGE or cname.startswith("D4_"):
                    # 對照側出場描述（抽到的對照股；全進場、不分段近似 ⇒ 僅參考）
                    pass
                if cname in JUDGE:
                    sy = cname
                    # D1／D2
                    for dn, msk in (("D1", d_["d1"]), ("D2", d_["d2"])):
                        o_ = okx & msk
                        q = x_stats(d_["X"][o_], moni[d_["T"][o_]])
                        q.update(trade_stats(d_["R"][o_] - COST, d_["H"][o_], d_["ty"][o_]))
                        q["跳過筆數"] = int((okx & ~msk).sum())
                        q["與判定格差"] = UO.diff_stats(d_["X"][okx], moni[d_["T"][okx]], d_["X"][o_], moni[d_["T"][o_]])
                        st[f"{dn}"] = q
                        DESC.append({"世界": wn, "段": sg, "格": f"{dn}_{sy}", "說明": ("D1 跳過規則甲（上一筆賺就跳過；子集讀法）" if dn == "D1" else "D2 跳過規則乙（上一筆失敗才做）"),
                                     **{k: v for k, v in q.items() if not isinstance(v, dict)}, "差(子集−全部)": q["與判定格差"].get("差(D2−A)"),
                                     "差lo": q["與判定格差"].get("lo"), "差hi": q["與判定格差"].get("hi"), "身分": "描述（⛔ 不判）"})
                    # 固定抱 H
                    for H in HD:
                        xh = d_[f"X{H}"]; okh = inseg & np.isfinite(xh)
                        q = x_stats(xh[okh], moni[d_["T"][okh]])
                        q.update({"R̄": float(d_[f"G{H}"][okh].mean()) if okh.any() else None})
                        DESC.append({"世界": wn, "段": sg, "格": f"{sy}_固定抱{H}日", "說明": f"同 {sy} 進場、固定抱 {H} 日（描述，⛔ 不當出場比較基準）",
                                     **{k: v for k, v in q.items() if not isinstance(v, dict)}, "身分": "描述（⛔ 不判）"})
                        st[f"固定抱{H}"] = q
                    # 對照側（抽到的對照：交易描述）
                    # 假訊號臂
                    ck = d_["ck"]
                    acc = np.zeros((REPS, 300, 2)); cntf = np.zeros((REPS, 3), np.int64)
                    mo0 = moni[p0]
                    isel = d_["i"][okx]
                    nper = Counter(isel.tolist())
                    candc = {}
                    for jj in nper:
                        cand = np.flatnonzero(POOL[ck][p0:p1 + 1, jj]).astype(np.int64) + p0
                        Tk = keptS[sy].get(jj, np.zeros(0, np.int64))
                        if len(Tk) and len(cand):
                            kq = np.searchsorted(Tk, cand, side="right") - 1
                            prv = np.where(kq >= 0, Tk[np.clip(kq, 0, len(Tk) - 1)], -10 ** 9)
                            cand = cand[~((kq >= 0) & (cand - prv <= EXCL))]
                        candc[jj] = cand
                    smpf = UO.Sampler(POOL[ck], RAW[sy])
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
                                cs = smpf.draw(T, jj, [SEED_CTRL, 5000 + 100 * SYSNUM[sy] + r_, T, crc[sid]])
                                cntf[r_, 0] += 1
                                if len(cs) == 0:
                                    cntf[r_, 1] += 1; continue
                                xv = CR[ck][T, jj] - CR[ck][T, cs].mean()
                                cl = moni[T] - mo0
                                acc[r_, cl, 0] += 1.0; acc[r_, cl, 1] += xv
                    res_ = [UO.agg_eval(acc[r_]) for r_ in range(REPS)]
                    st["假訊號_x2"] = sum(1 for q in res_ if q and q["結果"] == "結果②")
                    st["假訊號_x3"] = sum(1 for q in res_ if q and q["結果"] == "結果③")
                    st["假訊號_平均X"] = float(np.mean([q["平均"] for q in res_ if q])) if any(res_) else None
                    c2 = cntf.sum(axis=0)
                    st["假訊號_帳"] = {"抽出": int(c2[0]), "無對照": int(c2[1]), "可抽日不足": int(c2[2])}
                    for r_, q in enumerate(res_):
                        FK.append({"世界": wn, "段": sg, "格": sy, "r": r_, **({kk: q[kk] for kk in ("n", "平均", "lo", "hi", "n_eff", "出口", "結果")} if q else {"n": 0})})
                    g322 = bool(st["結果"] == "結果②" and st.get("bonf_lo", -1) > 0 and st["假訊號_x2"] <= 1 and st.get("X̄−成本", -1) > 0
                                and st.get("逐月中位與平均同號", False))
                    st["過seq322門檻"] = g322
                    # 對照側交易描述（本段事件抽到的對照，整段）
                if cname.startswith("D4_"):
                    sy = d_["sy"]; A_ = TR[sy]; okA = (A_["T"] >= p0) & (A_["T"] <= p1) & np.isfinite(A_["X"])
                    st["D4−S"] = UO.diff_stats(A_["X"][okA], moni[A_["T"][okA]], d_["X"][okx], moni[d_["T"][okx]])
                    st["D4−S_R̄差"] = (float(d_["R"][okx].mean() - A_["R"][okA].mean()) if okx.any() and okA.any() else None)
                if cname in JUDGE:
                    role = "判定格｜" + {"探索": "判定段（各自報）", "確認": "判定段（各自報）", "主全窗": "參考", "早年": "早年描述"}[sg]
                elif cname.endswith("當根停損"):
                    role = "另一讀法（只報）"
                else:
                    role = "描述（⛔ 不判、不計 N）"
                st["身分"] = role
                st["句子"] = sentence(cname, st, early=(wn == "早年"))
                segj[cname] = st
                MAIN.append({"世界": wn, "段": sg, "格": cname, "說明": NAME[cname], "身分": role, "期間": f"{cal[p0].date()}～{cal[p1].date()}",
                             **{k: v for k, v in st.items() if not isinstance(v, dict) and k not in ("身分", "句子")}, "句子": st["句子"]})
                log(f"  [{wn}/{sg}] {cname}：n={st['n']} n_eff={st.get('n_eff')} X̄={pct(st.get('X̄'))} CI {pct(st.get('lo'))}～{pct(st.get('hi'))} {st['結果']}"
                    + (f" 假 x={st.get('假訊號_x2')} seq322={st.get('過seq322門檻')}" if cname in JUDGE else "")
                    + (f" D4−S {pct(st['D4−S'].get('差(D2−A)'))}（{pct(st['D4−S'].get('lo'))}～{pct(st['D4−S'].get('hi'))}）" if cname.startswith("D4_") else "")
                    + f"｜{time.time() - t0:.0f}s")
            Wj["格"][sg] = segj
        # 對照側出場與持有（全世界、判定格抽到的對照）
        Wj["對照側"] = {c_: {"筆數": int(len(TR[c_]["cty"])), **{f"占比_{TYP[k]}": float((TR[c_]["cty"] == k).mean()) if len(TR[c_]["cty"]) else None for k in TYP},
                             "平均持有": float(TR[c_]["chd"][TR[c_]["chd"] >= 0].mean()) if (TR[c_]["chd"] >= 0).any() else None}
                        for c_ in ("S1", "S2", "D4_S1", "D4_S2")}
        Wj["對照全體計數"] = {k: dict(v) for k, v in CN.items()}
        Wj["持有限制略過"] = {c_: d_["skip"] for c_, d_ in TR.items()}
        J["世界"][wn] = Wj
        del ENTS, ENTD, POP, CR, CT, CH, G, RAW, BASES, BASED, POOL, TR, EVR
    if a.dry:
        log(f"[乾跑完] ⛔ 未算任何出場與報酬｜{time.time() - t0:.0f}s")
        open(os.path.join(out, "dry.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
        return
    # ── 判定表與先驗
    jd = {}
    for cell in JUDGE:
        for sg in ("探索", "確認", "主全窗"):
            st = J["世界"]["主"]["格"][sg][cell]
            jd[f"{cell}｜{sg}"] = {k: st.get(k) for k in ("身分", "結果", "出口", "n", "n_eff", "X̄", "lo", "hi", "bonf_lo", "中位", "X̄−成本", "逐月平均之中位",
                                                       "假訊號_x2", "過seq322門檻", "勝率", "平均賺賠比", "平均持有天數", "句子")}
        st = J["世界"]["早年"]["格"]["早年"][cell]
        jd[f"{cell}｜早年"] = {k: st.get(k) for k in ("身分", "結果", "n", "n_eff", "X̄", "lo", "hi", "假訊號_x2", "過seq322門檻", "句子")}
    J["判定"] = jd
    pri = {}
    for w, sgs in (("主", ("探索", "確認", "主全窗")), ("早年", ("早年",))):
        for sg in sgs:
            G_ = J["世界"][w]["格"][sg]
            p1_ = all(G_[c_]["結果"] in ("結果①", "結果③") for c_ in JUDGE)
            p2_ = all((G_[c_].get("勝率") or 1) < 0.40 and (G_[c_].get("平均賺賠比") or 0) > 1.5 for c_ in JUDGE)
            ch1 = G_["S1"].get(f"出場占比_{TYP[1]}") or 0; s1 = G_["S1"].get(f"出場占比_{TYP[2]}") or 0; s2 = G_["S2"].get(f"出場占比_{TYP[2]}") or 0
            pri[sg] = {"①兩格都①或③": {"S1": G_["S1"]["結果"], "S2": G_["S2"]["結果"], "中": p1_},
                       "②勝率<40%且賺賠比>1.5": {c_: {"勝率": G_[c_].get("勝率"), "賺賠比": G_[c_].get("平均賺賠比")} for c_ in JUDGE} | {"中": p2_},
                       "③S1通道出場>60%且S2停損占比>S1": {"S1通道": ch1, "S1停損": s1, "S2停損": s2, "中": bool(ch1 > 0.60 and s2 > s1)}}
    J["先驗"] = pri
    J["N"] = {"本件判定格": 2, "描述格／另一讀法": "不計 N"}
    J["時點"]["完成"] = now_tpe()
    pd.DataFrame(MAIN).to_csv(os.path.join(out, "Turtle_main.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(DESC).to_csv(os.path.join(out, "Turtle_desc.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(BY).to_csv(os.path.join(out, "by_year.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(FK).to_csv(os.path.join(out, "fake_reps.csv"), index=False, encoding="utf-8-sig")
    json.dump(J, open(os.path.join(out, "Turtle.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[判定] {json.dumps({k: {kk: v.get(kk) for kk in ('結果', 'n_eff', 'X̄', '假訊號_x2', '過seq322門檻')} for k, v in jd.items()}, ensure_ascii=False, default=float)}")
    log(f"[先驗] " + json.dumps({sg: {k: v['中'] for k, v in d.items()} for sg, d in pri.items()}, ensure_ascii=False))
    log(f"完成 {time.time() - t0:.0f}s")
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
