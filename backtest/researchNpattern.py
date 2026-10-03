# -*- coding: utf-8 -*-
"""PREREG N字底與N型走法 seq1（台股策略線 登錄 sha 4df1f473b005da3c；裁定 seq286 發號、N_單筆＝28）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchNpattern --stage build --world main|early [--procs 3]
    ... --stage stats        （兩個世界都 build 完）
    ... --stage page
    ... --check              （獨立查核：抽 ≥ 20 事件逐日重判型態與量能；抽 1 格逐筆重算基準② 與月分群 CI；0 不同才算過）

⭐ 讀法寫死：2026-10-04 02:30（台北），在算任何本件數字之前（含事件數）。執行者與交辦的回測線都沒看過任何 N字底、N型走法的輸出。
⭐ 定義出處：型態線〈N字底型態深入整理〉〈N型走法型態深入整理〉（2026-10-04，逐字照作者原文）；登錄 §一～§五。標「補」＝ 登錄沒寫清楚、執行者補的讀法。

═══ 資料與母體 ═══
 R1 主窗（探索 2017-03～2021-12、確認 2022-01～2026-08）：最新 main 0f5ef73ee8（2026-10-04 origin/main；日曆到 2026-10-02）
    stocks／adj／meta ＝ ~/h2data/0f5ef73ee8…/data 唯讀、stocks_inst ＝ 同 sha git archive ⇒ ~/npwork/main_0f5ef73ee8/data
    （補）接合版面（researchSurge5.stitch）只改 2014 以前的 adj 乘數；本件主窗最長回看 61 根 ⇒ 2016-11 以後，與接合版面同值 ⇒ 直接用 main。
    早年 2005-02～2014-12：上市＋上櫃版面 ~/earlydata/eotc_f65bb03e11/otc/data（researchYL_integrate.early_world 同一份）。
    ⚠ 引用必附（裁定 seq283）：上櫃 2007-07～12 除權息未還原；上櫃減資 2007～2012 為偵測、非官方；2005-01～2007-06 只有上市。
    （補）早年版面日曆止於 2014-12-31 ⇒ 持有窗跨出 2014-12-31 的事件該 H 不定義（只影響 2014 年底、H 越長越多），照報。
 R2 母體 ＝ gate3（上市櫃普通股、-DR 與創新板剔除、innov_ky 開），含已下市、注意、處置；⛔ 不套流動性閘。
    （補）登錄寫「W1 eligible」；照交辦用 gate3（W1 要個股法人，早年上櫃無資料，無法同口徑）。
 R3 價：還原價（data.load_stock）；型態一律在有效 K 棒序列上數。壞根 ＝ researchSurge5 S3（幽靈還原事件：事件日原始價比÷因子 ∉ [0.895,1.105]；
    價格斷點：相鄰有成交日收盤比 ≤ 0.55 或 ≥ 1.8 且其間無還原事件）；⛔ 純停牌不算壞根。
    型態用到的根（含量能回看窗）內有壞根 ⇒ 該型態實例不定義；報酬窗 (t, t＋H] 內有壞根 ⇒ 該 H 不定義。
 R4 量 ＝ 成交股數（原始 volume）。（補）量能比較窗內有「改變股數」的還原事件（kind 不是「息／除息」，含空白）⇒ 該型態實例四臂皆不定義（M、S、A、P 同母體）。
    窗：N字底 [h−20, 訊號日]；N型 [r, k]（長紅到再突破）。

═══ 甲 N字底（四段：下跌 → 反彈 → 回測不破前低 → 收盤突破頸線）═══
 R5 ① 下跌：L 根 i（有效 K 棒）；H0 根 h ＝ [i−20, i−1] 內最高價最大者（同值取最晚）；d1 ＝ (最高[h] − 最低[i]) ÷ 最高[h]；
       要 最低[i] ≤ [h, i−1] 每根最低（i 是這段下跌的最低點）、h ≥ 20（下跌前均量可算）。L ＝ 最低[i]。
       （補）H0 回看 20 根：登錄只給 d1 門檻沒給下跌段天數；20 根同突破量「近 20 日」，⛔ 不掃。
    ② 反彈：頸線 B 的認定窗 W_B ＝ L 之後 W_B 根內；B 取 {收盤, 最高}（P）。逐日（只用當日以前）：
       k ≤ i＋W_B 且 P[k] ≥ 目前 B ⇒ k 是新的反彈高點（B＝P[k]、j＝k；同值取最晚）；此時最低[k] ＜ L(1−ε) ⇒ L 不是底，實例作廢（不是放棄組）。
       （補）反彈要成立：B ＞ P[i]（反彈高點高於 L 那根自己的收盤／最高），否則作廢。
    ③ 回測：j 之後的根（不再創反彈高）＝ 回測段。逐日先後判：最低 ＜ L(1−ε) ⇒ 放棄組「回測破前低」；收盤 ＞ B（只可能在 i＋W_B 之後）⇒ 放棄組「沒出現像樣回測」；
       k − j ＝ W_R ⇒ 回測段結束、確認不破前低 ⇒ 甲1 訊號日 s ＝ k。（補）W_R 讀成回測段長度（回測段 ＝ (j, j＋W_R]），「像樣回測」＝ 撐滿 W_R 根沒突破也沒破底。
       容差 ε 用在 L 之後所有根（反彈段與回測段同一條「不破前低」線 L(1−ε)）。
    ④ 突破：s 之後第一根收盤 ＞ B ⇒ 甲2 訊號日 b；其間最低 ＜ L(1−ε) ⇒ 作廢；（補）最多等 20 根（s＋1～s＋20），等不到 ⇒ 沒有甲2。
       同一根先判破底、再判突破。
    形狀格 ＝ d1 {5,8,10,15}% × W_B {5,10,15} × B {收盤,最高} × W_R {3,5,10} × ε {0,1,2}% ＝ 216。
 R6 量能（作者四條；嚴格不等式）：
       ⓐ 下跌段均量 (h, i] ＜ 下跌前均量 [h−20, h−1] × {0.8,1.0}（補：下跌前 N ＝ 20 根）
       ⓑ 反彈段均量 (i, j] ＞ 下跌段均量 × {1.0,1.2,1.5}
       ⓒ 回測段均量 (j, s] ＜ 反彈段均量 × {0.8,1.0}（甲2 也用同一段 (j, s]）
       ⓓ 突破日量 v[b] ＞ 前 20 根均量 [b−20, b−1] × {1.2,1.5,2.0}（補：近 20 日不含突破日）
       甲1 在突破前進場 ⇒ ⓓ 不適用（補）：甲1 量能格 ＝ ⓐⓑⓒ 12 格；甲2 ＝ 36 格。
 R7 進場：甲1 ＝ s 次一交易日開盤；甲2 ＝ b 次一交易日開盤。同一檔、同一格、同一訊號日有多個 L 實例 ⇒ 取 L 最晚的那個（補）。
    停損（作者兩種並列）：ver0 回測低點 ＝ 回測段最低（甲1 (j, s]；甲2 (j, b)）；ver1 前低 ＝ L；收盤 ＜ 停損價 ⇒ 次一個有效 K 棒開盤出（本專案〈四十二〉主格收盤跌破）。
    目標價 ＝ B ＋ (B − L)：收盤 ≥ 目標價 ⇒ 次一個有效 K 棒開盤出（補：與停損同一口徑）。時間上限 H：t＋H 收盤出（停牌沿用前收、下市 ＝ 最後價）。
    （補）停損版本 ver0／ver1 當作格的一個軸（作者兩種並列 ⇒ 待定參數）：過半格的格 ＝ 形狀 × 量能 × 停損版本；另各版本分報。
    ver2 ＝ 固定持有 H、不設停損目標（描述，§二「另報」）。

═══ 乙 N型走法（長紅 → 回檔量縮不破 → 收盤突破長紅最高）═══
 R8 長紅 r：甲式 收盤÷前一有效收盤 − 1 ≥ {3,5,7}%；乙式 p ＝ (收−低)÷(高−低) ≥ {0.618,0.7} 且 (收−開)÷(高−低) ≥ {0.5,0.618}（高 ＝ 低 不算）⇒ 7 種。
    （補）作者「長紅突破」突破什麼沒定義 ⇒ 照型態線機器定義只判長紅本身。
    回檔窗 W ∈ {3,5,10}（補：讀成回檔段最長 W 根 ⇒ 再突破日 k ∈ [r＋2, r＋W＋1]）。逐日 k ＝ r＋1, …：
       收盤 ＞ 最高[r] ⇒ 若 k ＝ r＋1 或回檔段沒有任何一根收盤 ＜ 收盤[r] ⇒ 放棄組「沒出現回檔」；否則 ⇒ 訊號日 k（再突破）。
       否則（回檔日）：收盤 ＜ 最低[r] 且前一根也 ＜ 最低[r] ⇒ 放棄組「跌破超過一天」（⛔ 在第二根收盤後才判定，不回填）；
       到 k ＝ r＋W＋1 還沒突破 ⇒ 沒有事件。（補）「回檔」＝ 回檔段至少一根收盤 ＜ 長紅收盤。
    量（寫死、只 M）：回檔段每一天量 ＜ 長紅當日量。進場 k 次一交易日開盤；停損 ＝ 長紅最低點（收盤 ＜ 它 ⇒ 次一有效開盤出）；無目標價。
    （補）進場後停損不給「一天寬限」（寬限是型態成立條件，不是出場規則）。同一 k 有多根長紅 ⇒ 取最晚的 r。
    形狀格 ＝ 7 × 3 ＝ 21。

═══ 各臂 ═══
 R9 M ＝ 形狀＋量能＋作者停損／目標＋H；S ＝ 同形狀、拿掉全部量能（停損目標同 M）；M − S 同格配對（同形狀、同停損版本）。
    A 放棄組（描述）：N字底 ①② 成立（含 M 的 ⓐⓑ 量能）但 ③ 失敗；N型 ① 成立但回檔失敗。兩種失敗分報、合併為主。
    （補）「從本來會進場的同一時點」＝ 放棄那件事被確認的那根（直接突破日／破前低日／第二根跌破日）的次一交易日開盤；
    直接突破那批正好是「本來追突破會進場」的時點（研究十四「6 日內等不到」那批的對應）。A 固定持有 H、不設停損（補）。
    「等回測吃虧」＝ A − M（M 取 ver2 固定持有為主、ver0 另報；同形狀、A 取同 ⓐⓑ 量能格）的 CI 下緣 ＞ 0 的格過半（描述）。
 R10 P（只 N型）＝ M ＋ 訊號日（含）前 5 個交易日三大法人合計（total）加總 ＞ 0 ⇒ ⚠ 代理，不是作者原文的籌碼品質。
    缺列 ＝ 當日無法人買賣 ＝ 0（覆蓋期內）；覆蓋期：main 2015-01-05 起兩市；早年 上市 2012-05-02 起、⛔ 上櫃無 ⇒ 標「不可判定」、不補 0；
    （補）早年上市 2012-05 以前同樣無資料 ⇒ 也標不可判定（交辦說「上市照算」，上市只有 2012-05 起可算）。

═══ 報酬與判準 ═══
 R11 訊號日 t（收盤判定）、t＋1 開盤買：t＋1 要有成交、開盤有效、⛔ 非一字漲停鎖死（開＝高＝低＝漲停價，researchSurge5 S13）⇒ 否則「買不到」、不進報酬、照報比例；
     t＋1 處置中照報比例（仍算）。報酬 R ＝ 出場價 ÷ t＋1 開盤 − 1（還原）。
 R12 基準②（researchSurge5 S13 同式）：同日 t、前 20 根報酬（日曆長度 r20，avgdown.r20_cal）十分位（當日「t 有 K 棒、t＋1 可買、(t,t＋5] 無壞根、r20 可算」者分十分位），
     同十分位其他股票「t＋1 開盤買、固定持有 H、t＋H 收盤賣」報酬平均；X2 ＝ R − 該平均。對全體（隨機同日）X1 ＝ R − 同日其他股平均。
     扣成本：X2 的 CI 下緣 − 0.585% ＞ 0 才算「買了賺」（基準不付成本）；M − S、A − M、P − M 兩邊都付、成本相消。
 R13 去重：同一檔、同一格（臂 × 形狀 × 量能 × 停損版本 × H），依訊號日由早到晚，訊號日晚於上一筆出場（開盤出 ⇒ 出場日當天收盤後可再訊號；收盤出 ⇒ 次日起）才算新事件；
     買不到或報酬不定義的訊號不佔位。另報不去重版（M）。
 R14 月分群 CI：依 t 的曆月；μ ＝ Σx÷N、SE ＝ √Σ(s_m − μ n_m)² ÷ N；兩臂差 SE ＝ √Σ_m[(s_Am − μ_A n_Am)/N_A − (s_Bm − μ_B n_Bm)/N_B]²；95%（z＝1.96）。
     另報 Bonferroni（N＝28、z ＝ Φ⁻¹(1−0.025/28)）時判定變不變。
 R15 判（每個 型態 × 進場方式 × H）：
     「站得住」＝ 探索段與確認段都有【過半格】M 對基準② X2 的 CI 下緣 − 0.585% ＞ 0；
     「量能有加分」＝ 探索段與確認段都有【過半格】M − S（X2）CI 下緣 ＞ 0；
     過半 ＝ 嚴格多於一半；分母 ＝ 事件 ≥ 30 的格（M−S 兩臂都 ≥ 30）；另報分母含全部格版（不足 30 照判）。可判格 0 ⇒ 不可判定。
     早年：同式報過半格數；「方向」＝ 可判格中點估計（X2 − 成本；M−S 為差）＞ 0 的格是否過半；與主窗結論方向相反要寫出。
     結果句：主臂不成立但 M−S 有差 ⇒ 只能寫「量能條件有差，但型態本身測不出」。
     N_單筆 ＝ 28 ＝ 登錄 24（N字底 甲1／甲2 × H4 × 兩問 ＝ 16；N型 H4 × 兩問 ＝ 8）＋ P 臂「比主臂多」H4（補：裁定 28 的組成照此讀，P−M 判式同量能加分）。
     P 站得住（P 對基準②）另報描述。
 R16 另報（描述、不判）：固定持有 H 版本（ver2）；目標價被碰到的比例 vs 同日同十分位隨機 5 檔同距離（t＋1～t＋H 任一收盤 ≥ 進場開盤 ×(1＋δ)，δ ＝ 目標÷進場開盤−1）；
     現實版 ＝ 每邊再加 0.3% 滑價（補：只取 researchSlip C1 那一項，單筆層沒有資金規模）；不去重版；買不到、處置中比例；早年 P 不可判定筆數（依市場）。
 （2026-10-04 03:20 照實記錄：第一次跑完後查核 ② 抓到十分位用的 r20 與面板存成 float32、約 0.02% 的十分位歸屬因捨入不同 ⇒ 改存 float64 全部重跑；這是精度修正、不是讀法變更；第一次結果已看過（兩問皆否），重跑後照實報。查核容差改 1e−9。）
 R17 查核（--check）：① 抽 ≥ 20 個（股 × 格）的事件，用另寫的逐日迴圈從原始檔重判型態四段（三段）與量能條件、停損目標，與本程式事件清單逐筆比；
     ② 抽 1 格（N字底 甲2、d1 10%、W_B 10、收盤、W_R 5、ε 1%、量能 0.8/1.2/0.8/1.5、ver0、H20、確認段）從原始檔逐筆重算報酬、去重、基準②（自己分十分位）與月分群 CI；0 不同才算過。
輸出 backtest/resultsNpattern/；大檔在 ~/npwork/（不進 repo）
"""
from __future__ import annotations

import argparse
import html
import json
import os
import sys
import time
from multiprocessing import Pool, Process
from statistics import NormalDist

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import universe_gate as UG
UG.set_innov_ky(True)
from backtest import data as D
from backtest import research11 as R11
from backtest import avgdown as AV

TIME = "2026-10-04 02:30（台北）"
REG = "登錄 sha 4df1f473b005da3c（台股策略線 seq1）｜裁定 seq286（N_單筆＝28）"
MAIN_SHA = "0f5ef73ee8f5717c24a06229f383a1b5bee80acd"
EARLY_SHA = "f65bb03e114a5e10336d661218c63e6e68b08b85"
NOTE3 = "上櫃 2007-07～12 除權息未還原；上櫃減資 2007～2012 為偵測、非官方；2005-01～2007-06 只有上市"
WDIR = {"main": os.path.expanduser("~/npwork/main_0f5ef73ee8/data"), "early": os.path.expanduser("~/earlydata/eotc_f65bb03e11/otc/data")}
WORK = os.path.expanduser("~/npwork")
OUT = "backtest/resultsNpattern"
HS = (5, 10, 20, 60); HMAX = 60
COST = 0.00585; SLIP = 0.003
NFULL = 28
SEG = {"探索": ("2017-03", "2021-12"), "確認": ("2022-01", "2026-08"), "早年": ("2005-02", "2014-12")}
WSEG = {"main": ("探索", "確認"), "early": ("早年",)}
SCAN_FROM = {"main": "2016-11-01", "early": "2004-11-01"}
INST_COV = {"main": {"twse": "2015-01-05", "tpex": "2015-01-05"}, "early": {"twse": "2012-05-02", "tpex": None}}
D1S = (0.05, 0.08, 0.10, 0.15); WBS = (5, 10, 15); BTS = ("收盤", "最高"); WRS = (3, 5, 10); EPS = (0.0, 0.01, 0.02)
V1 = (0.8, 1.0); V2 = (1.0, 1.2, 1.5); V3 = (0.8, 1.0); V4 = (1.2, 1.5, 2.0)
LB_H0 = 20; PRE = 20; AVG_BRK = 20; CAP2 = 20
REDS = (("甲式≥3%", "a", 0.03, None), ("甲式≥5%", "a", 0.05, None), ("甲式≥7%", "a", 0.07, None),
        ("乙式p≥0.618實體≥0.5", "b", 0.618, 0.5), ("乙式p≥0.618實體≥0.618", "b", 0.618, 0.618),
        ("乙式p≥0.7實體≥0.5", "b", 0.7, 0.5), ("乙式p≥0.7實體≥0.618", "b", 0.7, 0.618))
NWS = (3, 5, 10)
NSC = 54; NSH = 216; NT = 21
ZB = NormalDist().inv_cdf(1 - 0.025 / NFULL); Z95 = 1.959963984540054
# 累加器：(格數, H, 月, 6)：[nR, sR, nX2, sX2, nX1, sX1]
ARMS = {"N1M": (NSH, 12, 3), "N2M": (NSH, 36, 3), "N1S": (NSH, 3), "N2S": (NSH, 3), "NA": (NSH, 6, 3),
        "TM": (NT, 2), "TS": (NT, 2), "TA": (NT, 3), "TP": (NT, 2)}
ND_ARMS = ("N1M", "N2M", "TM")                 # 不去重版
CNT_ARMS = ("N1M", "N2M", "TM", "TP")          # 去重前訊號、買不到、處置中、（TP：P 不可判定 上市／上櫃）
_G: dict = {}


def sc_of(wb, bt, wr, ep):
    return ((wb * 2 + bt) * 3 + wr) * 3 + ep


def sc_parts(sc):
    ep = sc % 3; wr = (sc // 3) % 3; bt = (sc // 9) % 2; wb = sc // 18
    return wb, bt, wr, ep


def shape_name(sh):
    d1i, sc = sh // NSC, sh % NSC
    wb, bt, wr, ep = sc_parts(sc)
    return f"d1≥{int(D1S[d1i] * 100)}%·W_B{WBS[wb]}·B{BTS[bt]}·W_R{WRS[wr]}·ε{int(EPS[ep] * 100)}%"


def vol_name(v, nv):
    if nv == 6:
        return f"ⓐ<{V1[v // 3]}·ⓑ>{V2[v % 3]}"
    a4 = None
    if nv == 36:
        a4, v = v % 3, v // 3
    a3 = v % 2; a2 = (v // 2) % 3; a1 = v // 6
    s = f"ⓐ<{V1[a1]}·ⓑ>{V2[a2]}·ⓒ<{V3[a3]}"
    return s + (f"·ⓓ>{V4[a4]}" if a4 is not None else "")


def cal_months(cal):
    return np.array([d.year * 12 + d.month - 1 for d in cal])


def seg_month_map(cal, world):
    """曆月 ⇒ 本世界段內月序（段外 −1）。"""
    mon = cal_months(cal)
    ms = []
    for sg in WSEG[world]:
        a, b = (pd.Period(x) for x in SEG[sg])
        ms += list(range(a.year * 12 + a.month - 1, b.year * 12 + b.month))
    ms = sorted(set(ms))
    mp = {m: k for k, m in enumerate(ms)}
    return np.array([mp.get(m, -1) for m in mon]), ms


# ═════════════ 每檔載入（build pass0）═════════════
def load_arrays(sid, mk, cal, world):
    """有效 K 棒序列與日曆陣列；壞根、改變股數事件、一字鎖死、處置、法人 5 日。"""
    n = len(cal)
    st = D.load_stock(sid, mk, cal)
    if st is None:
        return None
    df = st.df
    cA = df["close"].to_numpy(float); oA = df["open"].to_numpy(float); hA = df["high"].to_numpy(float); lA = df["low"].to_numpy(float)
    vA = pd.to_numeric(df["volume"], errors="coerce").to_numpy(float)
    idx = np.flatnonzero(np.isfinite(cA)); m = len(idx)
    if m < 70:
        return None
    raw = pd.read_csv(os.path.join(D.DATA, "stocks", sid + ".csv"), dtype={"date": str}, usecols=["date", "open", "high", "low", "close"]).drop_duplicates("date")
    raw.index = pd.to_datetime(raw["date"]); raw = raw.reindex(cal)
    rr = {k: np.array(pd.to_numeric(raw[k], errors="coerce"), dtype=float) for k in ("open", "high", "low", "close")}
    for k in rr:
        rr[k][~(rr[k] > 0)] = np.nan
    dates = cal[idx]; rc = rr["close"][idx]
    adj = D.load_adj(sid)
    ev_bar = np.zeros(m, bool); bad_k = np.zeros(m, bool); shchg = np.zeros(m, bool)
    if adj is not None and len(adj):
        kinds = adj["kind"].fillna("").astype(str).to_numpy() if "kind" in adj.columns else np.array([""] * len(adj))
        for d, f, kd in zip(adj["date"], adj["factor"].astype(float), kinds):
            k = int(np.searchsorted(dates, d))
            if k >= m:
                continue
            ev_bar[k] = True
            if kd not in ("息", "除息"):
                shchg[k] = True
            if k > 0 and np.isfinite(rc[k]) and np.isfinite(rc[k - 1]) and f > 0:
                r = rc[k] / (rc[k - 1] * f)
                if r < 0.895 or r > 1.105:
                    bad_k[k] = True
    for b in D.breakpoints(df, st.event_dates):
        if b["rule"] in ("price", "price+gap"):
            k = int(np.searchsorted(idx, b["pos"]))
            if k < m:
                bad_k[k] = True
    bad_day = np.zeros(n + 1, bool); bad_day[idx[bad_k]] = True
    nxt = np.full(n + 2, 10 ** 9)
    for p in range(n - 1, -1, -1):
        nxt[p] = p if bad_day[p] else nxt[p + 1]
    # 一字鎖死（researchSurge5 同式）
    skip = ev_bar.copy()
    if dates[0] > pd.Timestamp("2015-01-12") and world == "main":
        skip[:5] = True
    if world == "early" and dates[0] > pd.Timestamp("2004-02-18"):
        skip[:5] = True
    cut = pd.Timestamp("2015-06-01")
    locked = np.zeros(n, bool)
    for k in range(1, m):
        p = idx[k]
        if skip[k] or not (np.isfinite(rc[k - 1]) and np.isfinite(rr["open"][p]) and np.isfinite(rr["high"][p]) and np.isfinite(rr["low"][p])):
            continue
        lp = R11.limit_price(rc[k - 1], True, 0.07 if dates[k] < cut else 0.10)
        locked[p] = abs(rr["open"][p] - lp) < 1e-6 and abs(rr["high"][p] - lp) < 1e-6 and abs(rr["low"][p] - lp) < 1e-6
    bar = np.zeros(n, bool); bar[idx] = True
    buy_ok = bar & np.isfinite(oA) & (oA > 0) & ~locked
    cff = pd.Series(cA).ffill().to_numpy()
    hdef = np.zeros(n, np.int16)
    hd = np.minimum.reduce([np.full(m, HMAX), n - 1 - idx, nxt[np.minimum(idx + 1, n)] - 1 - idx])
    hdef[idx] = np.maximum(hd, 0)
    vpos = np.full(n + 1, -1, np.int64); vpos[idx] = np.arange(m)
    # 處置（t＋1 在處置期間）
    disp = np.zeros(n, bool)
    for a_, b_ in _G.get("DISP", {}).get(sid, []):
        i0 = cal.searchsorted(a_, side="left"); i1 = cal.searchsorted(b_, side="right")
        disp[i0:i1] = True
    # 法人 5 日合計（P 臂）
    inst5 = np.full(n, np.nan)
    cov = INST_COV[world].get(mk)
    if cov is not None:
        c0 = int(cal.searchsorted(pd.Timestamp(cov)))
        tot = np.zeros(n)
        p_ = os.path.join(D.DATA, "stocks_inst", sid + ".csv")
        if os.path.exists(p_):
            it = pd.read_csv(p_, dtype={"date": str}, usecols=["date", "total"]).drop_duplicates("date", keep="last")
            it.index = pd.to_datetime(it["date"])
            tot = pd.to_numeric(it["total"], errors="coerce").reindex(cal).fillna(0.0).to_numpy()
        cs = np.r_[0.0, np.cumsum(tot)]
        tt = np.arange(n)
        okc = tt - 4 >= c0
        inst5[okc] = cs[tt[okc] + 1] - cs[tt[okc] - 4]
    v = vA[idx]; v = np.where(np.isfinite(v), v, 0.0)
    return {"sid": sid, "mk": mk, "idx": idx, "m": m, "c": cA[idx], "o": oA[idx], "h": hA[idx], "l": lA[idx], "v": v,
            "bad": bad_k, "shchg": shchg, "cA": cA, "oA": oA, "cff": cff, "bar": bar, "buy_ok": buy_ok, "locked": locked,
            "hdef": hdef, "vpos": vpos, "disp": disp, "inst5": inst5}


# ═════════════ 型態掃描（純函式；--check 用另寫的逐日迴圈比）═════════════
def ndb_candidates(h_, l_, i0):
    """L 候選：回 (i, h, d1) 陣列。"""
    m = len(l_); out = []
    hl = h_.tolist(); ll = l_.tolist()
    for i in range(max(i0, LB_H0 + PRE), m):
        w = hl[i - LB_H0:i]
        mx = max(w)
        hpos = i - LB_H0 + (len(w) - 1 - w[::-1].index(mx))
        if hpos < PRE or not (mx > 0):
            continue
        Li = ll[i]
        if Li > min(ll[hpos:i]):
            continue
        d1 = (mx - Li) / mx
        if d1 >= D1S[0]:
            out.append((i, hpos, d1))
    return out


def ndb_scan(c_, h_, l_, cands):
    """N字底 逐日狀態機。回 list of (sc, i, h, d1, res, j, s_or_f, b, B, plo1, plo2)；
    res：1 ＝ 甲1 訊號（s）；2 ＝ 放棄組「沒出現像樣回測」（f）；3 ＝ 放棄組「回測破前低」（f）；作廢不回。"""
    cl = c_.tolist(); hl = h_.tolist(); ll = l_.tolist(); m = len(cl)
    out = []
    for i, hpos, d1 in cands:
        L = ll[i]
        for wb, WB in enumerate(WBS):
            for bt in (0, 1):
                P = cl if bt == 0 else hl
                Pi = P[i]
                for wr, WR in enumerate(WRS):
                    for ep, e_ in enumerate(EPS):
                        thr = L * (1 - e_)
                        B = -1e300; j = -1; k = i + 1; res = 0; sf = -1
                        while k < m:
                            if k <= i + WB and P[k] >= B:
                                if ll[k] < thr:
                                    break
                                B = P[k]; j = k; k += 1
                                continue
                            if ll[k] < thr:
                                res = 3; sf = k; break
                            if cl[k] > B:
                                res = 2; sf = k; break
                            if k - j == WR:
                                res = 1; sf = k; break
                            k += 1
                        if res == 0 or not (B > Pi):
                            continue
                        plo1 = min(ll[j + 1:sf + 1]) if sf > j else np.nan
                        b = -1; plo2 = np.nan
                        if res == 1:
                            mn = plo1
                            for k2 in range(sf + 1, min(sf + CAP2, m - 1) + 1):
                                if ll[k2] < thr:
                                    break
                                if cl[k2] > B:
                                    b = k2; break
                                mn = min(mn, ll[k2])
                            if b >= 0:
                                plo2 = mn
                        out.append((sc_of(wb, bt, wr, ep), i, hpos, d1, res, j, sf, b, B, plo1, plo2))
    return out


def red_flags(c_, o_, h_, l_):
    m = len(c_); F = np.zeros((m, len(REDS)), bool)
    g = np.r_[np.nan, c_[1:] / c_[:-1] - 1]
    rng = h_ - l_
    with np.errstate(invalid="ignore", divide="ignore"):
        p = np.where(rng > 0, (c_ - l_) / rng, np.nan); body = np.where(rng > 0, (c_ - o_) / rng, np.nan)
    for q, (_, kind, a, b) in enumerate(REDS):
        F[:, q] = (g >= a) if kind == "a" else ((p >= a) & (body >= b))
    F[0] = False
    return F


def nwave_scan(c_, h_, l_, v_, F, r0):
    """N型 逐日狀態機。回 list of (r, wi, res, k_or_f, volviol)；res：1 訊號（再突破日 k）；2 沒出現回檔；3 跌破超過一天。"""
    cl = c_.tolist(); hl = h_.tolist(); ll = l_.tolist(); vl = v_.tolist(); m = len(cl)
    rs = np.flatnonzero(F.any(1)); out = []
    for r in rs.tolist():
        if r < r0:
            continue
        for wi, W in enumerate(NWS):
            pull = False; below = False; viol = False; res = 0; kf = -1
            for k in range(r + 1, min(r + W + 1, m - 1) + 1):
                if cl[k] > hl[r]:
                    res = 1 if (k > r + 1 and pull) else 2; kf = k
                    break
                if cl[k] < cl[r]:
                    pull = True
                if vl[k] >= vl[r]:
                    viol = True
                if cl[k] < ll[r]:
                    if below:
                        res = 3; kf = k
                        break
                    below = True
                else:
                    below = False
            if res:
                out.append((r, wi, res, kf, viol))
    return out


# ═════════════ build ═════════════
def setup(world):
    D.DATA = WDIR[world]
    cal = D.load_calendar()
    stocks = pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str)
    uni = UG.gate3(stocks)
    have = {f[:-4] for f in os.listdir(os.path.join(D.DATA, "stocks"))}
    uni = uni[uni["stock_id"].isin(have)].sort_values("stock_id").reset_index(drop=True)
    return cal, uni


def _init(world):
    D.DATA = WDIR[world]
    _G["world"] = world; _G["cal"] = D.load_calendar()
    try:
        _G["DISP"] = D.load_disposal_intervals()
    except Exception:
        _G["DISP"] = {}


def pass0_one(args):
    si, sid, mk = args
    world = _G["world"]; cal = _G["cal"]; n = len(cal)
    A = load_arrays(sid, mk, cal, world)
    if A is None:
        return si, None
    wd = os.path.join(WORK, world)
    # 面板列
    bnext = np.r_[A["buy_ok"][1:], False]; onext = np.r_[A["oA"][1:], np.nan]
    Rf = np.full((len(HS), n), np.nan); MX = np.full((len(HS), n), np.nan)
    cff = A["cff"]
    for q, H in enumerate(HS):
        ok = np.flatnonzero(A["bar"] & bnext & (A["hdef"] >= H))
        Rf[q, ok] = cff[ok + H] / onext[ok] - 1
        rmx = pd.Series(cff[::-1]).rolling(H, min_periods=1).max().to_numpy()[::-1]
        fm = np.r_[rmx[1:], np.nan]
        MX[q, ok] = fm[ok] / onext[ok] - 1
    r20 = AV.r20_cal(A["cA"], A["idx"]).astype(np.float64)
    # 型態
    i0 = int(np.searchsorted(A["idx"], cal.searchsorted(pd.Timestamp(SCAN_FROM[world]))))
    cands = ndb_candidates(A["h"], A["l"], i0)
    ND = ndb_scan(A["c"], A["h"], A["l"], cands)
    F = red_flags(A["c"], A["o"], A["h"], A["l"])
    NW = nwave_scan(A["c"], A["h"], A["l"], A["v"], F, max(i0, 1))
    np.savez(os.path.join(wd, "st", sid + ".npz"),
             nd=np.array(ND, dtype=np.float64).reshape(-1, 11), nw=np.array(NW, dtype=np.float64).reshape(-1, 5), F=F,
             **{k: A[k] for k in ("idx", "c", "o", "h", "l", "v", "bad", "shchg", "cff", "oA", "buy_ok", "hdef", "vpos", "disp", "inst5")})
    return si, (Rf, MX, r20, len(ND), len(NW))


def build(world, procs, log):
    wd = os.path.join(WORK, world); os.makedirs(os.path.join(wd, "st"), exist_ok=True)
    cal, uni = setup(world); n = len(cal); S = len(uni)
    uni.to_csv(os.path.join(wd, "uni.csv"), index=False)
    log(f"[{world}] 日曆 {cal[0].date()}～{cal[-1].date()}（{n}）｜母體 gate3 {S} 檔")
    Rf = np.lib.format.open_memmap(os.path.join(wd, "Rf.npy"), "w+", np.float64, (len(HS), S, n))
    MX = np.lib.format.open_memmap(os.path.join(wd, "MX.npy"), "w+", np.float64, (len(HS), S, n))
    R20 = np.full((S, n), np.nan); have = np.zeros(S, bool)
    Rf[:] = np.nan; MX[:] = np.nan
    nnd = nnw = 0; done = 0
    with Pool(procs, initializer=_init, initargs=(world,)) as pool:
        for si, r in pool.imap_unordered(pass0_one, list(zip(range(S), uni["stock_id"], uni["market"])), chunksize=4):
            done += 1
            if r is not None:
                Rf[:, si, :] = r[0]; MX[:, si, :] = r[1]; R20[si] = r[2]; have[si] = True; nnd += r[3]; nnw += r[4]
            if done % 300 == 0:
                log(f"[{world} pass0] {done}/{S}")
    Rf.flush(); MX.flush(); np.save(os.path.join(wd, "R20.npy"), R20); np.save(os.path.join(wd, "have.npy"), have)
    log(f"[{world} pass0] 完成｜有資料 {int(have.sum())} 檔｜N字底實例列 {nnd:,}｜N型實例列 {nnw:,}")
    # 基準② 十分位與同十分位加總
    Rf = np.load(os.path.join(wd, "Rf.npy"), mmap_mode="r")
    R5 = np.asarray(Rf[0]); dec = np.full((S, n), -1, np.int8)
    for t in range(n):
        v = np.where(np.isfinite(R5[:, t]) & np.isfinite(R20[:, t]), R20[:, t], np.nan)
        if np.isfinite(v).any():
            dec[:, t] = AV.deciles(v)
    np.save(os.path.join(wd, "dec.npy"), dec)
    S2 = np.zeros((n, 10, len(HS))); C2 = np.zeros((n, 10, len(HS))); SA = np.zeros((n, len(HS))); CA = np.zeros((n, len(HS)))
    for q in range(len(HS)):
        R = np.asarray(Rf[q])
        for t in range(n):
            r = R[:, t]; ok = np.isfinite(r)
            SA[t, q] = r[ok].sum(dtype=np.float64); CA[t, q] = ok.sum()
            d = dec[:, t]; k2 = ok & (d >= 0)
            if k2.any():
                S2[t, :, q] = np.bincount(d[k2], r[k2].astype(np.float64), minlength=10); C2[t, :, q] = np.bincount(d[k2], minlength=10)
    np.savez(os.path.join(wd, "base.npz"), S2=S2, C2=C2, SA=SA, CA=CA)
    log(f"[{world}] 基準② 面板完成")
    # pass1：分格累加（每個行程一份累加器）
    sm, ms = seg_month_map(cal, world)
    chunks = [list(range(k, S, procs)) for k in range(procs)]
    ps = [Process(target=pass1_chunk, args=(world, ch, k)) for k, ch in enumerate(chunks)]
    for p in ps:
        p.start()
    for p in ps:
        p.join()
    assert all(p.exitcode == 0 for p in ps), [p.exitcode for p in ps]
    acc = None
    for k in range(procs):
        z = dict(np.load(os.path.join(wd, f"acc_{k}.npz")))
        acc = z if acc is None else {a: acc[a] + z[a] for a in acc}
        os.remove(os.path.join(wd, f"acc_{k}.npz"))
    np.savez(os.path.join(wd, "acc.npz"), **acc)
    pools = [pd.read_csv(os.path.join(wd, f"pool_{k}.csv.gz")) for k in range(procs)]
    pd.concat(pools).to_csv(os.path.join(wd, "pool.csv.gz"), index=False)
    for k in range(procs):
        os.remove(os.path.join(wd, f"pool_{k}.csv.gz"))
    json.dump({"世界": world, "日曆": [str(cal[0].date()), str(cal[-1].date()), n], "檔": S, "有資料": int(have.sum()), "N字底實例列": nnd, "N型實例列": nnw,
               "段內月": [int(x) for x in ms]}, open(os.path.join(wd, "build.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[{world}] pass1 完成")


# ═════════════ pass1：報酬、基準②、去重、累加 ═════════════
def new_acc(NM):
    A = {}
    for a, sh in ARMS.items():
        A[a] = np.zeros((int(np.prod(sh)) * len(HS) * NM, 6))
        if a in ND_ARMS:
            A[a + "_nd"] = np.zeros((int(np.prod(sh)) * len(HS) * NM, 6))
        if a in CNT_ARMS:
            A[a + "_cnt"] = np.zeros((int(np.prod(sh)) * NM, 5))
    return A


def exits(Z, t, stop, tgt, H):
    """valid-bar 空間求停損／目標出場。t：訊號日（日曆）；回 (R, 出場時點)。stop／tgt 不用 ⇒ −inf／＋inf。"""
    idx, cv, ov = Z["idx"], Z["c"], Z["o"]; m = len(idx)
    e = t + 1; ev = Z["vpos"][e]
    W = HMAX + 1
    rows = ev[:, None] + np.arange(W)[None, :]
    inb = rows < m; rc = np.minimum(rows, m - 1)
    Cw = cv[rc]; Iw = idx[rc]
    ok = inb & (Iw <= (t + H - 1)[:, None])
    trig = ok & ((Cw < stop[:, None]) | (Cw >= tgt[:, None]))
    has = trig.any(1); first = trig.argmax(1)
    xv = ev + first + 1; xc = np.minimum(xv, m - 1)
    use = has & (xv < m) & (idx[xc] <= t + H)
    po = np.where(np.isfinite(ov[xc]), ov[xc], cv[xc])
    price = np.where(use, po, Z["cff"][t + H])
    et = np.where(use, idx[xc] - 0.5, (t + H).astype(float))
    return price / Z["oA"][e] - 1, et


def entry_vals(Z, si, t, stops, tgt, P):
    """一批訊號（同一種進場）⇒ R、出場、X2、X1：(N, nver, H)。stops：list of 停損陣列（None ＝ 固定持有）。"""
    N = len(t); nv = len(stops)
    R = np.full((N, nv, len(HS)), np.nan); ET = np.full((N, nv, len(HS)), np.nan)
    X2 = np.full_like(R, np.nan); X1 = np.full_like(R, np.nan)
    if N == 0:
        return R, ET, X2, X1
    t = t.astype(np.int64)
    bok = Z["buy_ok"][t + 1]
    dq = P["dec"][si, t].astype(np.int64)
    for q, H in enumerate(HS):
        ok = bok & (Z["hdef"][t] >= H)
        if not ok.any():
            continue
        tt = t[ok]
        rself = P["Rf"][q][si, tt].astype(np.float64)
        sin = np.isfinite(rself)
        dd = dq[ok]
        s2 = P["S2"][tt, np.maximum(dd, 0), q] - np.where(sin & (dd >= 0), rself, 0)
        c2 = P["C2"][tt, np.maximum(dd, 0), q] - (sin & (dd >= 0))
        sa = P["SA"][tt, q] - np.where(sin, rself, 0); ca = P["CA"][tt, q] - sin
        for vi, st in enumerate(stops):
            if st is None:
                r = Z["cff"][tt + H] / Z["oA"][tt + 1] - 1; et = (tt + H).astype(float)
            else:
                r, et = exits(Z, tt, st[ok], tgt[ok] if tgt is not None else np.full(len(tt), np.inf), H)
            R[ok, vi, q] = r; ET[ok, vi, q] = et
            with np.errstate(invalid="ignore", divide="ignore"):
                X2[ok, vi, q] = np.where((dd >= 0) & (c2 >= 1), r - s2 / np.maximum(c2, 1), np.nan)
                X1[ok, vi, q] = np.where(ca >= 1, r - sa / np.maximum(ca, 1), np.nan)
    return R, ET, X2, X1


def uniq_latest(t, key):
    """同一訊號日取 key 最大（L／長紅最晚）者；回排序後的位置。"""
    if len(t) == 0:
        return np.zeros(0, np.int64)
    o = np.lexsort((key, t)); ts = t[o]
    last = np.r_[ts[1:] != ts[:-1], True]
    return o[last]


BIG = 10 ** 6


def chains_dedup(cell, t, et):
    """多條去重鏈一起做（R13）：(cell, t) 已排序且同格內 t 不重複；訊號日 ＞ 上一筆出場時點才收。回 kept。"""
    N = len(cell)
    kept = np.zeros(N, bool)
    if N == 0:
        return kept
    c64 = cell.astype(np.int64)
    key = c64 * BIG + t
    thr = c64 * BIG + np.floor(et).astype(np.int64) + 1
    nxt = np.searchsorted(key, thr, side="left")
    cur = np.flatnonzero(np.r_[True, c64[1:] != c64[:-1]])
    while len(cur):
        kept[cur] = True
        nx = nxt[cur]; ok = nx < N
        cc = c64[cur[ok]]; nx = nx[ok]
        cur = nx[c64[nx] == cc]
    return kept


class Acc:
    def __init__(self, NM, smon):
        self.NM = NM; self.smon = smon; self.rows = {}; self.vals = {}

    def _put(self, arm, cflat, q, mon, R, X2, X1):
        g = mon >= 0
        if not g.any():
            return
        rows = (cflat[g] * len(HS) + q) * self.NM + mon[g]
        r, x2, x1 = R[g], X2[g], X1[g]
        v = np.column_stack([np.isfinite(r), np.nan_to_num(r), np.isfinite(x2), np.nan_to_num(x2), np.isfinite(x1), np.nan_to_num(x1)]).astype(float)
        self.rows.setdefault(arm, []).append(rows); self.vals.setdefault(arm, []).append(v)

    def run(self, arm, pe, pc, t_ev, key_ev, V, nd=False, cnt=False, Z=None, extra=None, cnt_arm=None):
        """pe：成員的事件位置；pc：成員的格（不含停損版本）。同格同訊號日取 key 最大（R7、R8），再逐（版本 × H）去重、累加。"""
        if len(pe) == 0:
            return
        R, ET, X2, X1 = V; nver = R.shape[1]
        o = np.lexsort((key_ev[pe], t_ev[pe], pc))
        pe, pc = pe[o], pc[o]; tt = t_ev[pe]
        last = np.r_[(pc[1:] != pc[:-1]) | (tt[1:] != tt[:-1]), True]
        pe, pc, tt = pe[last], pc[last], tt[last]
        mm = self.smon[tt]
        if arm is not None:
            for vi in range(nver):
                cfl = pc.astype(np.int64) * nver + vi
                for q in range(len(HS)):
                    r = R[pe, vi, q]; ok = np.flatnonzero(np.isfinite(r))
                    if len(ok) == 0:
                        continue
                    kept = ok[chains_dedup(pc[ok], tt[ok], ET[pe[ok], vi, q])]
                    self._put(arm, cfl[kept], q, mm[kept], R[pe[kept], vi, q], X2[pe[kept], vi, q], X1[pe[kept], vi, q])
                    if nd:
                        self._put(arm + "_nd", cfl[ok], q, mm[ok], R[pe[ok], vi, q], X2[pe[ok], vi, q], X1[pe[ok], vi, q])
        if cnt:
            g = mm >= 0
            if g.any():
                t2 = tt[g]
                v = np.zeros((len(t2), 5)); v[:, 0] = 1; v[:, 1] = ~Z["buy_ok"][t2 + 1]; v[:, 2] = Z["disp"][t2 + 1]
                if extra is not None:
                    v[:, 3:5] = extra[pe[g]]
                rows = (pc[g].astype(np.int64) * nver) * self.NM + mm[g]
                ca = (cnt_arm or arm) + "_cnt"
                self.rows.setdefault(ca, []).append(rows); self.vals.setdefault(ca, []).append(v)

    def flush(self, A):
        for a in self.rows:
            np.add.at(A[a], np.concatenate(self.rows[a]), np.concatenate(self.vals[a]))
        self.rows = {}; self.vals = {}


def win_flag(cs, a, z):
    """(a, z] 內有旗標（cs ＝ r_[0, cumsum]）。"""
    return (cs[z + 1] - cs[a + 1]) > 0


def pass1_chunk(world, sis, k):
    _init(world)
    wd = os.path.join(WORK, world)
    cal = _G["cal"]
    uni = pd.read_csv(os.path.join(wd, "uni.csv"), dtype=str)
    smon, ms = seg_month_map(cal, world); NM = len(ms)
    P = {"Rf": np.load(os.path.join(wd, "Rf.npy"), mmap_mode="r"), "dec": np.load(os.path.join(wd, "dec.npy"), mmap_mode="r"), **dict(np.load(os.path.join(wd, "base.npz")))}
    A = new_acc(NM); pool = []
    for c_, si in enumerate(sis):
        sid = uni["stock_id"].iloc[si]; mk = uni["market"].iloc[si]
        fp = os.path.join(wd, "st", sid + ".npz")
        if not os.path.exists(fp):
            continue
        Z = dict(np.load(fp))
        ac = Acc(NM, smon)
        pool += stock_cells(Z, si, P, ac, world, mk)
        ac.flush(A)
        if c_ % 200 == 0:
            print(f"[{world} pass1 #{k}] {c_}/{len(sis)}", flush=True)
    np.savez(os.path.join(wd, f"acc_{k}.npz"), **A)
    pd.DataFrame(pool, columns=["si", "型", "t", "delta"]).to_csv(os.path.join(wd, f"pool_{k}.csv.gz"), index=False)


def ndb_table(Z):
    """N字底實例 ⇒ 欄位陣列（含量能比、壞根與改變股數過濾）。"""
    X = Z["nd"]
    if len(X) == 0:
        return None
    sc, i, h, d1, res, j, sf, b, B, plo1, plo2 = (X[:, q] for q in range(11))
    sc, i, h, res, j, sf, b = (a.astype(np.int64) for a in (sc, i, h, res, j, sf, b))
    v = Z["v"]; cv = np.r_[0.0, np.cumsum(v)]
    mean = lambda a, z: (cv[z + 1] - cv[a]) / np.maximum(z - a + 1, 1)          # [a, z]
    with np.errstate(invalid="ignore", divide="ignore"):
        pre = mean(h - PRE, h - 1); dec_ = mean(h + 1, i); reb = mean(i + 1, j); pb = np.where(res == 1, mean(j + 1, np.maximum(sf, j + 1)), np.nan)
        r1 = dec_ / pre; r2 = reb / dec_; r3 = pb / reb
        bb = np.maximum(b, AVG_BRK)
        r4 = np.where(b >= 0, v[np.maximum(b, 0)] / mean(bb - AVG_BRK, bb - 1), np.nan)
    end = np.where(b >= 0, b, sf)
    cb = np.r_[0, np.cumsum(Z["bad"])]; cs = np.r_[0, np.cumsum(Z["shchg"])]
    a0 = h - PRE - 1
    ok = ~win_flag(cb, a0, end) & ~win_flag(cs, a0, end)
    # 甲1 用到 s 為止；甲2 用到 b 為止 ⇒ 甲1 另判
    ok1 = ~win_flag(cb, a0, sf) & ~win_flag(cs, a0, sf)
    idx = Z["idx"]
    return {"sc": sc, "i": i, "d1": d1, "res": res, "r1": r1, "r2": r2, "r3": r3, "r4": r4, "B": B, "L": Z["l"][i],
            "plo1": plo1, "plo2": plo2, "t1": np.where(res == 1, idx[sf], -1), "t2": np.where(b >= 0, idx[np.maximum(b, 0)], -1),
            "tA": np.where(res >= 2, idx[sf], -1), "ok1": ok1, "ok2": ok}


def members(*ms):
    """多個布林成員矩陣（N, k_i）⇒ 外積後非零的 (事件, 各維索引…)。"""
    N = ms[0].shape[0]
    full = ms[0]
    for x in ms[1:]:
        full = full[..., None] & x.reshape((N,) + (1,) * (full.ndim - 1) + (x.shape[1],))
    return np.nonzero(full)


def stock_cells(Z, si, P, ac, world, mk):
    pool = []
    n = len(_G["cal"])
    T = ndb_table(Z)
    if T is not None:
        valid_t = lambda t: (t >= 0) & (t + 1 < n)
        tgt = T["B"] + (T["B"] - T["L"])
        e1 = (T["res"] == 1) & T["ok1"] & valid_t(T["t1"])
        e2 = (T["t2"] >= 0) & T["ok2"] & valid_t(T["t2"])
        eA = (T["res"] >= 2) & T["ok1"] & valid_t(T["tA"])
        p1 = np.flatnonzero(e1); p2 = np.flatnonzero(e2); pA = np.flatnonzero(eA)
        V1_ = entry_vals(Z, si, T["t1"][p1], [T["plo1"][p1], T["L"][p1], None], tgt[p1], P)
        V2_ = entry_vals(Z, si, T["t2"][p2], [T["plo2"][p2], T["L"][p2], None], tgt[p2], P)
        VA_ = entry_vals(Z, si, T["tA"][pA], [None], None, P)
        # 目標價碰到（描述）pool：M 最寬量能格可達者
        for p_, tcol, nm, extra in ((p1, "t1", "甲1", np.ones(len(p1), bool)), (p2, "t2", "甲2", T["r4"][p2] > V4[0])):
            mm = (T["r1"][p_] < V1[-1]) & (T["r2"][p_] > V2[0]) & (T["r3"][p_] < V3[-1]) & extra
            tt = T[tcol][p_][mm]; dl = tgt[p_][mm] / Z["oA"][np.minimum(tt + 1, n - 1)] - 1
            for a, b in set(zip(tt.tolist(), np.round(dl, 10).tolist())):
                if ac.smon[a] >= 0 and np.isfinite(b):
                    pool.append((si, nm, a, b))
        D1m = lambda p: T["d1"][p][:, None] >= np.array(D1S)[None, :]
        A1 = lambda p: T["r1"][p][:, None] < np.array(V1)[None, :]
        A2 = lambda p: T["r2"][p][:, None] > np.array(V2)[None, :]
        A3 = lambda p: T["r3"][p][:, None] < np.array(V3)[None, :]
        A4 = lambda p: T["r4"][p][:, None] > np.array(V4)[None, :]
        if len(p1):
            t1 = T["t1"][p1]; i1 = T["i"][p1]; sc1 = T["sc"][p1]
            ev, d1i = members(D1m(p1))
            ac.run("N1S", ev, d1i * NSC + sc1[ev], t1, i1, V1_)
            ev, d1i, x1, x2, x3 = members(D1m(p1), A1(p1), A2(p1), A3(p1))
            cell = (d1i * NSC + sc1[ev]) * 12 + (x1 * 3 + x2) * 2 + x3
            ac.run("N1M", ev, cell, t1, i1, V1_, nd=True, cnt=True, Z=Z)
        if len(p2):
            t2 = T["t2"][p2]; i2 = T["i"][p2]; sc2 = T["sc"][p2]
            ev, d1i = members(D1m(p2))
            ac.run("N2S", ev, d1i * NSC + sc2[ev], t2, i2, V2_)
            ev, d1i, x1, x2, x3, x4 = members(D1m(p2), A1(p2), A2(p2), A3(p2), A4(p2))
            cell = (d1i * NSC + sc2[ev]) * 36 + ((x1 * 3 + x2) * 2 + x3) * 3 + x4
            ac.run("N2M", ev, cell, t2, i2, V2_, nd=True, cnt=True, Z=Z)
        if len(pA):
            tA = T["tA"][pA]; iA = T["i"][pA]; scA = T["sc"][pA]; ty = T["res"][pA] - 1          # 1 沒回測、2 破前低
            ev, d1i, x1, x2 = members(D1m(pA), A1(pA), A2(pA))
            base = (d1i * NSC + scA[ev]) * 6 + x1 * 3 + x2
            ac.run("NA", np.r_[ev, ev], np.r_[base * 3, base * 3 + ty[ev]], tA, iA, VA_)
    # ── N型
    X = Z["nw"]
    if len(X):
        r, wi, res, kf, viol = (X[:, q] for q in range(5))
        r, wi, res, kf = (a.astype(np.int64) for a in (r, wi, res, kf)); viol = viol.astype(bool)
        idx = Z["idx"]; F = Z["F"]
        cb = np.r_[0, np.cumsum(Z["bad"])]; cs = np.r_[0, np.cumsum(Z["shchg"])]
        ok = ~win_flag(cb, r - 2, kf) & ~win_flag(cs, r - 1, kf)
        t = idx[kf]; ok &= t + 1 < n
        stop = Z["l"][r]
        pS = np.flatnonzero(ok & (res == 1)); pA = np.flatnonzero(ok & (res >= 2))
        if len(pS):
            VS = entry_vals(Z, si, t[pS], [stop[pS], None], None, P)
            tS = t[pS]; rS = r[pS]
            ins = Z["inst5"][tS]
            pfl = np.where(np.isfinite(ins), ins > 0, False); pnan = ~np.isfinite(ins)
            extra = np.column_stack([pnan & (mk == "twse"), pnan & (mk == "tpex")]).astype(float)
            ev, rd = np.nonzero(F[rS])
            cell = rd * 3 + wi[pS][ev]
            ac.run("TS", ev, cell, tS, rS, VS)
            m_ = ~viol[pS][ev]
            ac.run("TM", ev[m_], cell[m_], tS, rS, VS, nd=True, cnt=True, Z=Z)
            ac.run(None, ev[m_], cell[m_], tS, rS, VS, cnt=True, Z=Z, extra=extra, cnt_arm="TP")
            mp = m_ & pfl[ev]
            ac.run("TP", ev[mp], cell[mp], tS, rS, VS)
        if len(pA):
            VA = entry_vals(Z, si, t[pA], [None], None, P)
            tA = t[pA]; rA = r[pA]; ty = res[pA] - 1
            ev, rd = np.nonzero(F[rA])
            cell = rd * 3 + wi[pA][ev]
            ac.run("TA", np.r_[ev, ev], np.r_[cell * 3, cell * 3 + ty[ev]], tA, rA, VA)
    return pool


# ═════════════ stats ═════════════
def cstat(n_m, s_m, z=Z95):
    N = n_m.sum(-1)
    with np.errstate(invalid="ignore", divide="ignore"):
        mu = s_m.sum(-1) / N
        se = np.sqrt(((s_m - mu[..., None] * n_m) ** 2).sum(-1)) / N
    return N, mu, se


def dstat(nA, sA, nB, sB):
    NA, NB = nA.sum(-1), nB.sum(-1)
    with np.errstate(invalid="ignore", divide="ignore"):
        mA, mB = sA.sum(-1) / NA, sB.sum(-1) / NB
        psi = (sA - mA[..., None] * nA) / NA[..., None] - (sB - mB[..., None] * nB) / NB[..., None]
        se = np.sqrt((np.nan_to_num(psi) ** 2).sum(-1))
    return NA, NB, mA - mB, se


def load_acc(world):
    wd = os.path.join(WORK, world)
    A = dict(np.load(os.path.join(wd, "acc.npz")))
    ms = json.load(open(os.path.join(wd, "build.json"), encoding="utf-8"))["段內月"]
    NM = len(ms)
    out = {}
    for a, sh in ARMS.items():
        for suf in ("", "_nd"):
            if a + suf in A:
                out[a + suf] = A[a + suf].reshape(*sh, len(HS), NM, 6)
        if a + "_cnt" in A:
            out[a + "_cnt"] = A[a + "_cnt"].reshape(*sh, NM, 5)
    return out, np.array(ms)


def seg_mask(ms, sg):
    a, b = (pd.Period(x) for x in SEG[sg])
    return (ms >= a.year * 12 + a.month - 1) & (ms <= b.year * 12 + b.month - 1)


def stats(log):
    os.makedirs(OUT, exist_ok=True)
    W = {w: load_acc(w) for w in ("main", "early")}

    def seg_arr(arm, sg, col=(2, 3)):
        w = "early" if sg == "早年" else "main"
        A, ms = W[w]; X = A[arm][..., seg_mask(ms, sg), :]
        return X[..., col[0]], X[..., col[1]]
    rows = []; J = {}
    groups = [("N字底", "甲1", "N1M", "N1S", 12), ("N字底", "甲2", "N2M", "N2S", 36), ("N型", "再突破", "TM", "TS", None)]
    for pat, ent, am, as_, nv in groups:
        for q, H in enumerate(HS):
            key = f"{pat}|{ent}|H{H}"; J[key] = {}
            for sg in SEG:
                nM, sM = seg_arr(am, sg); nS, sS = seg_arr(as_, sg)
                nM, sM, nS, sS = nM[..., q, :], sM[..., q, :], nS[..., q, :], sS[..., q, :]
                if pat == "N字底":
                    # M (216, nv, 3, NM)；判定用 ver0、ver1
                    NMv, mu, se = cstat(nM, sM); NSv, muS, seS = cstat(nS, sS)
                    nSb = np.broadcast_to(nS[:, None], nM.shape); sSb = np.broadcast_to(sS[:, None], sM.shape)
                    _, _, dd, sed = dstat(nM, sM, nSb, sSb)
                    sel = (slice(None), slice(None), slice(0, 2))
                    NMj, muj, sej, ddj, sedj = NMv[sel], mu[sel], se[sel], dd[sel], sed[sel]
                    NSj = np.broadcast_to(NSv[:, None, :2], NMj.shape)
                else:
                    NMv, mu, se = cstat(nM, sM); NSv, muS, seS = cstat(nS, sS)
                    _, _, dd, sed = dstat(nM, sM, nS, sS)
                    NMj, muj, sej, ddj, sedj, NSj = NMv[:, :1], mu[:, :1], se[:, :1], dd[:, :1], sed[:, :1], NSv[:, :1]
                J[key][sg] = judge(NMj, muj, sej, ddj, sedj, NSj)
                # 逐格表
                it = np.ndindex(*NMv.shape)
                for ix in it:
                    if NMv[ix] == 0 and pat == "N字底":
                        continue
                    sh = ix[0]
                    if pat == "N字底":
                        sname = shape_name(sh); vname = vol_name(ix[1], nv); ver = ("回測低點停損", "前低停損", "固定持有")[ix[2]]
                        sidx = (sh, ix[2])
                    else:
                        sname = f"{REDS[sh // 3][0]}·回檔窗{NWS[sh % 3]}"; vname = "逐日量＜長紅量"; ver = ("長紅低點停損", "固定持有")[ix[1]]
                        sidx = (sh, ix[1])
                    rows.append({"型態": pat, "進場": ent, "形狀": sname, "量能": vname, "停損": ver, "H": H, "段": sg, "M_n": int(NMv[ix]), "M_X2": mu[ix],
                                 "M_下緣": mu[ix] - Z95 * se[ix], "M_上緣": mu[ix] + Z95 * se[ix], "S_n": int(NSv[sidx]), "S_X2": muS[sidx],
                                 "M−S": dd[ix], "M−S_下緣": dd[ix] - Z95 * sed[ix], "M−S_上緣": dd[ix] + Z95 * sed[ix]})
            log(f"[stats] {key}")
    CELLS = pd.DataFrame(rows)
    CELLS.to_csv(os.path.join(OUT, "cells.csv.gz"), index=False, float_format="%.12g")
    # 描述臂：M 淨報酬、X1、現實版、不去重、A−M、P
    DESC = describe(W, seg_arr, log)
    S = {"讀法寫死": TIME, "登錄": REG, "主窗資料": MAIN_SHA, "早年資料": EARLY_SHA, "早年標註": NOTE3, "N_單筆": NFULL, "Bonferroni_z": ZB,
         "判定": J, "描述": DESC}
    S["兩問"] = two_questions(J)
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log("[stats] 完成")


def judge(N, mu, se, dd, sed, NS):
    """過半格：M 對基準②（扣成本）與 M−S；可判格 ＝ n ≥ 30。另報全部格版、Bonferroni。"""
    N = N.ravel(); mu = mu.ravel(); se = se.ravel(); dd = dd.ravel(); sed = sed.ravel(); NS = NS.ravel()
    el = N >= 30; elD = el & (NS >= 30)
    lo = mu - Z95 * se - COST; loB = mu - ZB * se - COST
    dlo = dd - Z95 * sed; dloB = dd - ZB * sed
    pas = el & (lo > 0); pasB = el & (loB > 0); dpas = elD & (dlo > 0); dpasB = elD & (dloB > 0)
    anyN = N >= 2
    r = {"格": int(len(N)), "可判格": int(el.sum()), "站_過": int(pas.sum()), "站_過半": bool(el.sum() > 0 and pas.sum() * 2 > el.sum()),
         "站_點估計正": int((el & (mu - COST > 0)).sum()), "站_方向過半": bool(el.sum() > 0 and (el & (mu - COST > 0)).sum() * 2 > el.sum()),
         "站_全部格版_過": int((anyN & (lo > 0)).sum()), "站_全部格版_過半": bool((anyN & (lo > 0)).sum() * 2 > len(N)),
         "站_Bonf_過": int(pasB.sum()), "站_Bonf_過半": bool(el.sum() > 0 and pasB.sum() * 2 > el.sum()),
         "量_可判格": int(elD.sum()), "量_過": int(dpas.sum()), "量_過半": bool(elD.sum() > 0 and dpas.sum() * 2 > elD.sum()),
         "量_點估計正": int((elD & (dd > 0)).sum()), "量_方向過半": bool(elD.sum() > 0 and (elD & (dd > 0)).sum() * 2 > elD.sum()),
         "量_全部格版_過": int(((N >= 2) & (NS >= 2) & (dlo > 0)).sum()), "量_全部格版_過半": bool(((N >= 2) & (NS >= 2) & (dlo > 0)).sum() * 2 > len(N)),
         "量_Bonf_過": int(dpasB.sum()), "量_Bonf_過半": bool(elD.sum() > 0 and dpasB.sum() * 2 > elD.sum()),
         "事件中位": float(np.median(N[el])) if el.any() else 0.0, "事件總（格加總）": int(N.sum()),
         "X2中位": float(np.nanmedian(mu[el])) if el.any() else None, "M−S中位": float(np.nanmedian(dd[elD])) if elD.any() else None}
    return r


def two_questions(J):
    out = {}
    for key, d in J.items():
        ex, cf, ea = d["探索"], d["確認"], d["早年"]
        stand = ex["站_過半"] and cf["站_過半"]; vol = ex["量_過半"] and cf["量_過半"]
        nostand = ex["可判格"] == 0 or cf["可判格"] == 0
        if stand:
            s = "站得住" + ("（早年方向相反）" if (ea["可判格"] and not ea["站_方向過半"]) else "")
        else:
            s = "不可判定（可判格 0）" if nostand else "站不住（測不出）"
        if vol:
            v = "量能有加分" + ("（早年方向相反）" if (ea["量_可判格"] and not ea["量_方向過半"]) else "")
        else:
            v = "量能加分測不出"
        sent = s + "；" + v
        if not stand and vol:
            sent = "量能條件有差，但型態本身測不出"
        out[key] = {"站得住": stand, "量能有加分": vol, "句": sent,
                    "Bonferroni 下": {"站得住": ex["站_Bonf_過半"] and cf["站_Bonf_過半"], "量能有加分": ex["量_Bonf_過半"] and cf["量_Bonf_過半"]}}
    return out


def describe(W, seg_arr, log):
    R = {}
    def one(arm, sg, sel, q, col=(2, 3)):
        n, s = seg_arr(arm, sg, col)
        n, s = n[sel][..., q, :], s[sel][..., q, :]
        return cstat(n, s)
    # 1) M 主臂、固定持有、淨報酬、對全體、現實版、不去重：格中位
    for pat, ent, am, nv in (("N字底", "甲1", "N1M", 12), ("N字底", "甲2", "N2M", 36), ("N型", "再突破", "TM", None)):
        for q, H in enumerate(HS):
            for sg in SEG:
                key = f"{pat}|{ent}|H{H}|{sg}"; d = {}
                vers = (0, 1, 2) if pat == "N字底" else (0, 1)
                for ver in vers:
                    sel = (slice(None), slice(None), ver) if pat == "N字底" else (slice(None), ver)
                    N, mu, se = one(am, sg, sel, q)
                    Nr, mr, _ = one(am, sg, sel, q, (0, 1))
                    N1, m1, _ = one(am, sg, sel, q, (4, 5))
                    Nn, mn, _ = one(am + "_nd", sg, sel, q)
                    el = N >= 30
                    d[f"ver{ver}"] = {"可判格": int(el.sum()), "X2中位": med(mu[el]), "X2扣成本下緣>0格": int((el & (mu - Z95 * se - COST > 0)).sum()),
                                      "淨報酬中位": med(mr[el] - COST), "現實版淨報酬中位": med(mr[el] - COST - 2 * SLIP),
                                      "現實版X2下緣>0格": int((el & (mu - Z95 * se - COST - 2 * SLIP > 0)).sum()),
                                      "對全體X1中位": med(m1[el]), "不去重_X2中位": med(mn[(Nn >= 30)]), "不去重_事件中位": med(Nn[Nn >= 30]),
                                      "事件中位": med(N[el])}
                R[key] = d
        log(f"[描述] {pat}{ent}")
    # 2) 買不到、處置
    for w, A_ in W.items():
        A, ms = A_
        for arm in ("N1M", "N2M", "TM"):
            for sg in WSEG[w]:
                c = A[arm + "_cnt"][..., seg_mask(ms, sg), :].sum(-2)
                c = c.reshape(-1, 5).sum(0)
                R.setdefault("買不到處置", {})[f"{arm}|{sg}"] = {"去重前訊號（格加總）": float(c[0]), "買不到比例": float(c[1] / c[0]) if c[0] else None,
                                                             "處置中比例": float(c[2] / c[0]) if c[0] else None}
        c = A["TP_cnt"][..., seg_mask(ms, WSEG[w][0]) | (seg_mask(ms, WSEG[w][-1])), :].sum(-2).reshape(-1, 5)[0::2].sum(0)
        R.setdefault("P不可判定", {})[w] = {"M 訊號（格加總、去重前）": float(c[0]), "不可判定_上市": float(c[3]), "不可判定_上櫃": float(c[4])}
    # 3) A − M（等回測吃虧）與 A 本身、P
    AM = {}
    for pat, ent, am, nv in (("N字底", "甲1", "N1M", 12), ("N字底", "甲2", "N2M", 36), ("N型", "再突破", "TM", None)):
        for q, H in enumerate(HS):
            for sg in SEG:
                key = f"{pat}|{ent}|H{H}|{sg}"; d = {}
                for ver in ((2, 0) if pat == "N字底" else (1, 0)):
                    for ty, tn in ((0, "合併"), (1, "沒出現回測"), (2, "破前低／跌破超過一天")):
                        nA, sA = seg_arr("NA" if pat == "N字底" else "TA", sg)
                        nM, sM = seg_arr(am, sg)
                        if pat == "N字底":
                            nA_, sA_ = nA[:, :, ty, q], sA[:, :, ty, q]            # (216, 6, NM)
                            k = nv // 6 if nv == 12 else 6
                            nM_, sM_ = nM[:, :, ver, q], sM[:, :, ver, q]          # (216, nv, NM)
                            vi = np.arange(nv); aidx = (vi // 2) if nv == 12 else (vi // 6)
                            nAb, sAb = nA_[:, aidx], sA_[:, aidx]
                        else:
                            nAb, sAb = nA[:, ty, q], sA[:, ty, q]; nM_, sM_ = nM[:, ver, q], sM[:, ver, q]
                        NA_, NM_, df_, sed = dstat(nAb, sAb, nM_, sM_)
                        NAo, muA, seA = cstat(nAb, sAb)
                        el = (NA_ >= 30) & (NM_ >= 30)
                        d[f"ver{ver}|{tn}"] = {"可判格": int(el.sum()), "A−M中位": med(df_[el]), "A−M下緣>0格": int((el & (df_ - Z95 * sed > 0)).sum()),
                                               "A−M上緣<0格": int((el & (df_ + Z95 * sed < 0)).sum()),
                                               "過半（吃虧）": bool(el.sum() > 0 and (el & (df_ - Z95 * sed > 0)).sum() * 2 > el.sum()),
                                               "A_X2中位": med(muA[NAo >= 30]), "A_X2扣成本下緣>0格": int(((NAo >= 30) & (muA - Z95 * seA - COST > 0)).sum()),
                                               "A可判格": int((NAo >= 30).sum()), "A事件中位": med(NAo[NAo >= 30])}
                AM[key] = d
    R["A−M"] = AM
    PP = {}
    for q, H in enumerate(HS):
        for sg in SEG:
            nP, sP = seg_arr("TP", sg); nM, sM = seg_arr("TM", sg)
            nP, sP, nM, sM = nP[:, 0, q], sP[:, 0, q], nM[:, 0, q], sM[:, 0, q]
            NP_, NM_, df_, sed = dstat(nP, sP, nM, sM); NPo, muP, seP = cstat(nP, sP)
            el = (NP_ >= 30) & (NM_ >= 30); elP = NPo >= 30
            PP[f"H{H}|{sg}"] = {"P−M_可判格": int(el.sum()), "P−M_過": int((el & (df_ - Z95 * sed > 0)).sum()), "P−M_過半": bool(el.sum() > 0 and (el & (df_ - Z95 * sed > 0)).sum() * 2 > el.sum()),
                                "P−M_Bonf過": int((el & (df_ - ZB * sed > 0)).sum()), "P−M_點估計正": int((el & (df_ > 0)).sum()), "P−M中位": med(df_[el]),
                                "P_可判格": int(elP.sum()), "P站_過": int((elP & (muP - Z95 * seP - COST > 0)).sum()), "P_X2中位": med(muP[elP]),
                                "P_事件中位": med(NPo[elP])}
    R["P"] = PP
    R["P判定"] = {f"H{H}": {"P比主臂多": PP[f"H{H}|探索"]["P−M_過半"] and PP[f"H{H}|確認"]["P−M_過半"],
                           "Bonferroni 下": bool(PP[f"H{H}|探索"]["P−M_可判格"] and PP[f"H{H}|探索"]["P−M_Bonf過"] * 2 > PP[f"H{H}|探索"]["P−M_可判格"]
                                                and PP[f"H{H}|確認"]["P−M_Bonf過"] * 2 > PP[f"H{H}|確認"]["P−M_可判格"]),
                           "P站得住（描述）": bool(PP[f"H{H}|探索"]["P_可判格"] and PP[f"H{H}|探索"]["P站_過"] * 2 > PP[f"H{H}|探索"]["P_可判格"]
                                                 and PP[f"H{H}|確認"]["P站_過"] * 2 > max(PP[f"H{H}|確認"]["P_可判格"], 1))} for H in HS}
    # 4) 目標價碰到 vs 隨機同距離
    R["目標價"] = target_hits(log)
    return R


def med(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return float(np.median(x)) if len(x) else None


def target_hits(log):
    out = {}
    rng = np.random.default_rng(20261004)
    for w in ("main", "early"):
        wd = os.path.join(WORK, w)
        pool = pd.read_csv(os.path.join(wd, "pool.csv.gz"))
        MX = np.load(os.path.join(wd, "MX.npy"), mmap_mode="r"); dec = np.load(os.path.join(wd, "dec.npy"), mmap_mode="r")
        D.DATA = WDIR[w]; cal = D.load_calendar(); smon, ms = seg_month_map(cal, w); msa = np.array(ms)
        segof = {}
        for sg in WSEG[w]:
            mk = seg_mask(msa, sg)
            for k in np.flatnonzero(mk):
                segof[k] = sg
        pool["段"] = [segof.get(int(smon[t]), None) for t in pool["t"]]
        for q, H in enumerate(HS):
            M = np.asarray(MX[q])
            for (ty, sg), g in pool.groupby(["型", "段"]):
                si = g["si"].to_numpy(); t = g["t"].to_numpy(); dl = g["delta"].to_numpy()
                own = M[si, t]; okk = np.isfinite(own)
                hit = (own[okk] >= dl[okk] * (1 - 1e-12)).mean() if okk.any() else np.nan
                # 隨機：同日同十分位 5 檔
                hr = []
                gg = pd.DataFrame({"a": si[okk], "b": t[okk], "d": dl[okk]})
                for b, g2 in gg.groupby("b"):
                    dcol = np.asarray(dec[:, b]); mcol = M[:, b]
                    lists = {d: np.flatnonzero((dcol == d) & np.isfinite(mcol)) for d in range(10)}
                    for a, d_ in zip(g2["a"].to_numpy(), g2["d"].to_numpy()):
                        dq = int(dcol[a])
                        if dq < 0:
                            continue
                        cand = lists[dq]; cand = cand[cand != a]
                        if len(cand) == 0:
                            continue
                        pk = rng.choice(cand, size=min(5, len(cand)), replace=False)
                        hr.append(float((mcol[pk] >= d_).mean()))
                out[f"{ty}|H{H}|{sg}"] = {"樣本（不重複訊號）": int(okk.sum()), "碰到目標比例": float(hit), "隨機同距離比例": float(np.mean(hr)) if hr else None,
                                         "目標距離中位": float(np.median(dl[okk])) if okk.any() else None}
        log(f"[目標價] {w}")
    return out


# ═════════════ page ═════════════
def page(log):
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    J, Q, DS = S["判定"], S["兩問"], S["描述"]
    e = html.escape
    P = lambda x: "—" if x is None else f"{x * 100:+.2f}%"
    stand_any = [k for k, v in Q.items() if v["站得住"]]; vol_any = [k for k, v in Q.items() if v["量能有加分"]]
    pjud = DS["P判定"]
    p_more = [h for h, v in pjud.items() if v["P比主臂多"]]
    concl1 = ("沒有一個（型態 × 進場 × 持有天數）站得住" if not stand_any else "站得住的有：" + "、".join(stand_any))
    concl2 = ("量能條件在任何一組都沒有測出加分" if not vol_any else "量能有加分的有：" + "、".join(vol_any))
    H = ["<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
         "<title>N字底與N型走法回測</title><style>",
         ":root{--bg:#fff;--fg:#1d1d1f;--mut:#666;--bd:#ddd;--ok:#0a7a3d;--no:#b3261e;--hl:#fff6d6}",
         "@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#141414;--fg:#eee;--mut:#aaa;--bd:#333;--ok:#5fd18b;--no:#ff8a80;--hl:#3a3320}}",
         ":root[data-theme=dark]{--bg:#141414;--fg:#eee;--mut:#aaa;--bd:#333;--ok:#5fd18b;--no:#ff8a80;--hl:#3a3320}",
         "body{background:var(--bg);color:var(--fg);font:15px/1.6 -apple-system,'Noto Sans TC',sans-serif;margin:0;padding:16px;max-width:980px}",
         "h1{font-size:1.35em}h2{font-size:1.12em;margin-top:1.6em;border-bottom:1px solid var(--bd)}",
         ".wrap{overflow-x:auto}table{border-collapse:collapse;font-size:13px;min-width:100%}td,th{border:1px solid var(--bd);padding:4px 6px;text-align:right;white-space:nowrap}",
         "th.l,td.l{text-align:left}.ok{color:var(--ok);font-weight:600}.no{color:var(--no)}.box{background:var(--hl);padding:10px 12px;border-radius:8px}.mut{color:var(--mut);font-size:13px}</style></head><body>",
         "<h1>N字底與N型走法回測（照作者原文、含量能）</h1>",
         f"<p class='mut'>{e(REG)}｜讀法寫死 {e(S['讀法寫死'])}｜回測線計算子代理｜單筆事件研究（不是策略、不能說贏 0050）</p>",
         "<div class='box'><b>先講結論（兩問）</b><br>",
         f"① 型態本身站得住嗎？<b>{e(concl1)}</b>。<br>",
         f"② 作者的量能條件有加分嗎？<b>{e(concl2)}</b>。<br>",
         f"③ N型的法人代理臂（⚠ 代理，不是作者原文的籌碼品質）比主臂多：{'H' + '、'.join(p_more) if p_more else '各天數都沒有'}。</div>",
         "<p class='mut'>「站得住」＝ 探索段（2017-03～2021-12）與確認段（2022-01～2026-08）都有過半的格，扣 0.585% 成本後對「同日、前 20 日漲跌同十分位的股票」CI 下緣仍 ＞ 0。"
         "「量能有加分」＝ 兩段都有過半的格，作者全套（M）減同形狀不看量（S）的 CI 下緣 ＞ 0。待定參數全格報、不挑最好的一格；事件少於 30 的格不進分母。</p>",
         "<h2>逐組判定</h2><div class='wrap'><table><tr><th class='l'>型態｜進場｜H</th><th class='l'>結論句</th>"
         "<th>探索 過/可判</th><th>確認 過/可判</th><th>早年 過/可判</th><th>量能 探索</th><th>量能 確認</th><th>量能 早年</th><th>X2 中位（確認）</th><th>M−S 中位（確認）</th><th>事件中位（確認）</th></tr>"]
    for k, v in Q.items():
        d = J[k]
        cl = "ok" if (v["站得住"] or v["量能有加分"]) else "no"
        H.append(f"<tr><td class='l'>{e(k)}</td><td class='l {cl}'>{e(v['句'])}</td>"
                 + "".join(f"<td>{d[s]['站_過']}/{d[s]['可判格']}</td>" for s in ("探索", "確認", "早年"))
                 + "".join(f"<td>{d[s]['量_過']}/{d[s]['量_可判格']}</td>" for s in ("探索", "確認", "早年"))
                 + f"<td>{P(d['確認']['X2中位'])}</td><td>{P(d['確認']['M−S中位'])}</td><td>{d['確認']['事件中位']:.0f}</td></tr>")
    H.append("</table></div><p class='mut'>X2 ＝ 個股報酬 − 同日同十分位平均（未扣成本；判定時再扣 0.585%）。格 ＝ 形狀 × 量能 ×（N字底）停損兩種。"
             "⚠ 主臂有停損：被停掉的那筆只算到出場為止，對照組照抱滿 H 天，所以 H 越長、停損越近，X2 越負（固定持有版見下方「其他」）。"
             "Bonferroni（N＝28）下結論變不變：" + "；".join(f"{e(k)} {'變' if (v['Bonferroni 下']['站得住'] != v['站得住'] or v['Bonferroni 下']['量能有加分'] != v['量能有加分']) else '不變'}" for k, v in Q.items()) + "</p>")
    # 早年方向
    H.append("<h2>早年（2005-02～2014-12，上市＋上櫃）</h2><div class='wrap'><table><tr><th class='l'>型態｜進場｜H</th><th>可判格</th><th>扣成本過</th><th>點估計 ＞ 0 的格</th><th>M−S 點估計 ＞ 0</th></tr>")
    for k in Q:
        d = J[k]["早年"]
        H.append(f"<tr><td class='l'>{e(k)}</td><td>{d['可判格']}</td><td>{d['站_過']}</td><td>{d['站_點估計正']}</td><td>{d['量_點估計正']}/{d['量_可判格']}</td></tr>")
    H.append(f"</table></div><p class='mut'>⚠ 早年版面標註（裁定 seq283）：{e(NOTE3)}。早年日曆到 2014-12-31，持有窗跨年底的事件該天數不定義。</p>")
    # 放棄組
    H.append("<h2>放棄組（沒等到回測那批）的後續表現</h2><p class='mut'>放棄組 ＝ 前面成立、但沒出現像樣回測（直接突破）或回測破了前低（N型：跌破超過一天）。"
             "從放棄被確認那天的下一個開盤買、固定抱 H 天。A−M ＞ 0 ＝ 放棄掉的反而比較好（等回測吃虧）。M 取固定持有版、同形狀、同前兩條量能。</p>"
             "<div class='wrap'><table><tr><th class='l'>型態｜進場｜H｜段</th><th>A X2 中位</th><th>A−M 中位（合併）</th><th>A−M 下緣＞0 格/可判</th><th>A−M 上緣＜0 格</th>"
             "<th>沒回測那批 A−M 中位</th><th>破底那批 A−M 中位</th></tr>")
    for k, d in DS["A−M"].items():
        vv = "ver2" if k.startswith("N字底") else "ver1"
        a = d[f"{vv}|合併"]; b = d[f"{vv}|沒出現回測"]; c = d[f"{vv}|破前低／跌破超過一天"]
        H.append(f"<tr><td class='l'>{e(k)}</td><td>{P(a['A_X2中位'])}</td><td>{P(a['A−M中位'])}</td><td>{a['A−M下緣>0格']}/{a['可判格']}</td><td>{a['A−M上緣<0格']}</td>"
                 f"<td>{P(b['A−M中位'])}</td><td>{P(c['A−M中位'])}</td></tr>")
    H.append("</table></div>")
    # P
    H.append("<h2>N型 法人代理臂 P（⚠ 代理）</h2><div class='wrap'><table><tr><th class='l'>H｜段</th><th>P−M 過/可判</th><th>P−M 中位</th><th>P 扣成本過/可判</th><th>P X2 中位</th><th>P 事件中位</th></tr>")
    for k, d in DS["P"].items():
        H.append(f"<tr><td class='l'>{e(k)}</td><td>{d['P−M_過']}/{d['P−M_可判格']}</td><td>{P(d['P−M中位'])}</td><td>{d['P站_過']}/{d['P_可判格']}</td><td>{P(d['P_X2中位'])}</td><td>{d['P_事件中位'] or 0:.0f}</td></tr>")
    pn = DS["P不可判定"]
    H.append(f"</table></div><p class='mut'>早年上櫃沒有法人資料、上市只有 2012-05 起 ⇒ 標不可判定、不補 0：早年 M 訊號（格加總）{pn['early']['M 訊號（格加總、去重前）']:.0f} 筆中，不可判定 上市 {pn['early']['不可判定_上市']:.0f}、上櫃 {pn['early']['不可判定_上櫃']:.0f}。</p>")
    # 描述
    H.append("<h2>其他（描述，不判）</h2><div class='wrap'><table><tr><th class='l'>型態｜進場｜H｜段</th><th>停損版本</th><th>可判格</th><th>X2 中位</th><th>淨報酬中位</th><th>現實版淨報酬中位</th><th>對全體中位</th><th>不去重 X2 中位</th></tr>")
    for k, d in DS.items():
        if "|" not in k or k.count("|") != 3:
            continue
        for ver, x in d.items():
            vn = {"ver0": "回測低點／長紅低點停損", "ver1": "前低停損" if k.startswith("N字底") else "固定持有", "ver2": "固定持有"}[ver]
            H.append(f"<tr><td class='l'>{e(k)}</td><td class='l'>{vn}</td><td>{x['可判格']}</td><td>{P(x['X2中位'])}</td><td>{P(x['淨報酬中位'])}</td><td>{P(x['現實版淨報酬中位'])}</td><td>{P(x['對全體X1中位'])}</td><td>{P(x['不去重_X2中位'])}</td></tr>")
    H.append("</table></div>")
    H.append("<h3>目標價被碰到的比例 vs 隨機同距離</h3><div class='wrap'><table><tr><th class='l'>進場｜H｜段</th><th>樣本</th><th>碰到目標</th><th>隨機同距離</th><th>目標距離中位</th></tr>")
    for k, d in DS["目標價"].items():
        H.append(f"<tr><td class='l'>{e(k)}</td><td>{d['樣本（不重複訊號）']}</td><td>{d['碰到目標比例'] * 100:.1f}%</td><td>{(d['隨機同距離比例'] or 0) * 100:.1f}%</td><td>{P(d['目標距離中位'])}</td></tr>")
    H.append("</table></div><h3>買不買得到</h3><div class='wrap'><table><tr><th class='l'>臂｜段</th><th>去重前訊號（格加總）</th><th>隔天一字漲停買不到</th><th>處置中</th></tr>")
    for k, d in DS["買不到處置"].items():
        H.append(f"<tr><td class='l'>{e(k)}</td><td>{d['去重前訊號（格加總）']:.0f}</td><td>{(d['買不到比例'] or 0) * 100:.2f}%</td><td>{(d['處置中比例'] or 0) * 100:.2f}%</td></tr>")
    H.append("</table></div>")
    # 先驗對答
    H.append("<h2>先驗逐條對答（登錄 §五）</h2><div class='wrap'><table><tr><th class='l'>先驗</th><th class='l'>押</th><th class='l'>實測</th><th>對錯</th></tr>")
    for row in prior_rows(S):
        H.append("<tr>" + "".join(f"<td class='l'>{e(str(x))}</td>" for x in row) + "</tr>")
    H.append("</table></div>")
    H.append("<h2>讀法（摘要）</h2><p class='mut'>N字底：下跌（20 根內高點到低點跌幅 ≥ d1）→ 反彈（低點後 W_B 根內的最高收盤或最高價 ＝ 頸線）→ 回測 W_R 根不破前低（容差 ε）→ 甲1 回測段結束隔天開盤進、甲2 之後 20 根內收盤突破頸線隔天開盤進。"
             "量能四條照作者原文、門檻全格。停損：回測低點或前低（收盤跌破隔天開盤出）；目標價：頸線＋（頸線−低點）。"
             "N型：長紅 → W 根內回檔（每天量 ＜ 長紅量、收盤跌破長紅低點只能一天）→ 收盤突破長紅最高，隔天開盤進；停損長紅低點。"
             "同一檔前一筆出場前不算新事件。完整讀法與「執行者補」清單見程式 backtest/researchNpattern.py 開頭。</p>")
    H.append(f"<p class='mut'>查核：{e(json.dumps(S.get('查核', '見 check.json'), ensure_ascii=False))}</p></body></html>")
    open(os.path.join(OUT, "N字底與N型走法回測.html"), "w", encoding="utf-8").write("\n".join(H))
    log("[page] 完成")


def prior_rows(S):
    Q = S["兩問"]; PJ = S["描述"]["P判定"]; AM = S["描述"]["A−M"]
    nd_st = [k for k in Q if k.startswith("N字底") and Q[k]["站得住"]]
    nd_vol = [k for k in Q if k.startswith("N字底") and Q[k]["量能有加分"]]
    nw_st = [k for k in Q if k.startswith("N型") and Q[k]["站得住"]]
    p_more = [h for h, v in PJ.items() if v["P比主臂多"]]
    eat = []; tot = 0
    for k, d in AM.items():
        if k.endswith("|探索"):
            k2 = k[:-2] + "確認"; vv = "ver2" if k.startswith("N字底") else "ver1"
            tot += 1
            if d[f"{vv}|合併"]["過半（吃虧）"] and AM[k2][f"{vv}|合併"]["過半（吃虧）"]:
                eat.append(k[:-3])
    share = len(eat) / tot if tot else float("nan")
    return [("① N字底主臂站得住", "否（約七成）", "站得住：" + ("、".join(nd_st) if nd_st else "沒有"), "對" if not nd_st else "錯"),
            ("② N字底量能有加分", "否（約六成五）", "有加分：" + ("、".join(nd_vol) if nd_vol else "沒有"), "對" if not nd_vol else "錯"),
            ("③ 放棄組報酬 ≥ 主臂", "是（約六成）", f"「等回測吃虧」（A−M 下緣 ＞ 0 過半格、探索與確認都成立；固定持有版、合併）{len(eat)}/{tot} 組："
             + ("、".join(eat) if eat else "沒有"), "對" if share > 0.5 else "錯（多數組測不出放棄組較好）"),
            ("④ N型主臂站得住", "否（約六成五）", "站得住：" + ("、".join(nw_st) if nw_st else "沒有"), "對" if not nw_st else "錯"),
            ("⑤ P 比主臂多", "否或測不出（約六成）", "P 比主臂多：" + ("H" + "、".join(p_more) if p_more else "沒有"), "對" if not p_more else "錯")]


# ═════════════ check（獨立：另寫逐日迴圈、自己算十分位與 CI）═════════════
def chk_load(sid, mk, cal):
    """自己從原始檔讀（只借 data.load_stock 的還原價與 breakpoints）。"""
    st = D.load_stock(sid, mk, cal)
    df = st.df
    ok = df["close"].notna().to_numpy()
    pos = np.flatnonzero(ok)
    bars = [dict(pos=int(p), c=float(df["close"].iat[p]), o=float(df["open"].iat[p]), h=float(df["high"].iat[p]), l=float(df["low"].iat[p]),
                 v=float(df["volume"].iat[p]) if np.isfinite(df["volume"].iat[p]) else 0.0) for p in pos]
    return st, bars


def chk_ndb_events(bars, sc, d1thr, vcell, nv, entry, bad, sh):
    """逐日迴圈重判 N字底（另寫）：回 {訊號 valid 位置: (L 根, B, 停損0, 停損1, 目標)}（同訊號取 L 最晚）。"""
    wb, bt, wr, ep = sc_parts(sc); WB, WR, e_ = WBS[wb], WRS[wr], EPS[ep]
    a4 = None
    if nv == 36:
        a4 = vcell % 3; vcell //= 3
    a1, a2, a3 = vcell // 6, (vcell // 2) % 3, vcell % 2
    m = len(bars); ev = {}
    key = "c" if bt == 0 else "h"
    vol = [b["v"] for b in bars]
    avg = lambda a, z: sum(vol[a:z + 1]) / (z - a + 1)

    def rt(x, y):
        if y > 0:
            return x / y
        return float("inf") if x > 0 else float("nan")
    for i in range(LB_H0 + PRE, m):
        hs = [bars[k]["h"] for k in range(i - LB_H0, i)]
        top = max(hs); h0 = max(k for k in range(i - LB_H0, i) if bars[k]["h"] == top)
        if h0 < PRE or any(bars[k]["l"] < bars[i]["l"] for k in range(h0, i)):
            continue
        L = bars[i]["l"]; d1 = (top - L) / top
        if d1 < d1thr:
            continue
        thr = L * (1 - e_)
        B = None; j = None; out = None
        for k in range(i + 1, m):
            x = bars[k]
            if k <= i + WB and (B is None or x[key] >= B):          # 反彈窗內創新高 ⇒ 新頸線
                if x["l"] < thr:
                    out = "作廢"; break
                B = x[key]; j = k; continue
            if x["l"] < thr:
                out = ("A", k); break
            if x["c"] > B:
                out = ("A", k); break
            if k - j == WR:
                out = ("S", k); break
        if not isinstance(out, tuple) or out[0] != "S" or not (B > bars[i][key]):
            continue
        s = out[1]
        r1 = rt(avg(h0 + 1, i), avg(h0 - PRE, h0 - 1)); r2 = rt(avg(i + 1, j), avg(h0 + 1, i)); r3 = rt(avg(j + 1, s), avg(i + 1, j))
        if not (r1 < V1[a1] and r2 > V2[a2] and r3 < V3[a3]):
            continue
        sig = s; plo = min(bars[k]["l"] for k in range(j + 1, s + 1))
        if entry == 2:
            sig = None
            for k in range(s + 1, min(s + CAP2, m - 1) + 1):
                if bars[k]["l"] < thr:
                    break
                if bars[k]["c"] > B:
                    sig = k; break
                plo = min(plo, bars[k]["l"])
            if sig is None:
                continue
            r4 = rt(bars[sig]["v"], avg(sig - AVG_BRK, sig - 1))
            if not r4 > V4[a4]:
                continue
        # 壞根、改變股數（h0−20 到訊號日）
        if any(bad[k] for k in range(h0 - PRE, sig + 1)):
            continue
        ev[sig] = (i, B, plo, L, B + (B - L))
    return ev


def chk_nwave_events(bars, rd, w, arm, bad, Fflags):
    W = NWS[w]; m = len(bars); ev = {}
    for r in range(1, m):
        if not Fflags[r]:
            continue
        pull = False; below = 0; res = None
        for k in range(r + 1, min(r + W + 1, m - 1) + 1):
            if bars[k]["c"] > bars[r]["h"]:
                res = ("S", k) if (k > r + 1 and pull) else ("A", k)
                if arm == "M" and res[0] == "S" and any(bars[q]["v"] >= bars[r]["v"] for q in range(r + 1, k)):
                    res = ("X", k)
                break
            if bars[k]["c"] < bars[r]["c"]:
                pull = True
            below = below + 1 if bars[k]["c"] < bars[r]["l"] else 0
            if below >= 2:
                res = ("A", k); break
        if res and res[0] == "S" and not any(bad[0][q] for q in range(r - 1, res[1] + 1)) and not any(bad[1][q] for q in range(r, res[1] + 1)):
            ev[res[1]] = (r, bars[r]["l"])
    return ev


def check(log):
    """① 型態逐日重判；② 1 格基準② 與 CI 逐筆重算。"""
    rng = np.random.default_rng(7)
    res = {"①抽查（股×格）": 0, "①事件數": 0, "①不同": 0, "②不同": 0}
    world = "main"; _init(world); cal = _G["cal"]; n = len(cal)
    wd = os.path.join(WORK, world); uni = pd.read_csv(os.path.join(wd, "uni.csv"), dtype=str)
    det = []
    tried = 0
    while res["①事件數"] < 40 or res["①抽查（股×格）"] < 25:
        tried += 1
        if tried > 4000:
            break
        si = int(rng.integers(len(uni))); sid, mk = uni["stock_id"].iloc[si], uni["market"].iloc[si]
        fp = os.path.join(wd, "st", sid + ".npz")
        if not os.path.exists(fp):
            continue
        Z = dict(np.load(fp))
        st, bars = chk_load(sid, mk, cal)
        bad = (Z["bad"] | Z["shchg"]).tolist()
        typ = rng.integers(3)
        if typ < 2:
            T = ndb_table(Z)
            if T is None:
                continue
            entry = int(typ) + 1; nv = 12 if entry == 1 else 36
            sc = int(rng.integers(NSC)); d1i = int(rng.integers(4)); vc = int(rng.integers(nv))
            # 本程式：同 stock_cells 的篩選
            if entry == 1:
                base = (T["res"] == 1) & T["ok1"] & (T["t1"] >= 0); tcol = "t1"; plo = T["plo1"]
            else:
                base = (T["t2"] >= 0) & T["ok2"]; tcol = "t2"; plo = T["plo2"]
            v_ = vc
            a4 = None
            if nv == 36:
                a4 = v_ % 3; v_ //= 3
            a1, a2, a3 = v_ // 6, (v_ // 2) % 3, v_ % 2
            mk_ = base & (T["sc"] == sc) & (T["d1"] >= D1S[d1i]) & (T["r1"] < V1[a1]) & (T["r2"] > V2[a2]) & (T["r3"] < V3[a3])
            if a4 is not None:
                mk_ &= T["r4"] > V4[a4]
            sel = np.flatnonzero(mk_); u = sel[uniq_latest(T[tcol][sel], T["i"][sel])]
            mine = {int(Z["vpos"][T[tcol][k]]): (int(T["i"][k]), float(T["B"][k]), float(plo[k]), float(T["L"][k])) for k in u}
            i0 = int(np.searchsorted(Z["idx"], cal.searchsorted(pd.Timestamp(SCAN_FROM[world]))))
            ref = chk_ndb_events(bars, sc, D1S[d1i], vc, nv, entry, bad, None)
            ref = {k: v for k, v in ref.items() if v[0] >= max(i0, LB_H0 + PRE)}
            tag = f"N字底甲{entry} {sid} {shape_name(d1i * NSC + sc)} {vol_name(vc, nv)}"
        else:
            if len(Z["nw"]) == 0:
                continue
            rd = int(rng.integers(len(REDS))); w = int(rng.integers(3))
            X = Z["nw"]; r, wi, rs, kf, viol = (X[:, q] for q in range(5))
            r, wi, rs, kf = (a.astype(int) for a in (r, wi, rs, kf))
            cb = np.r_[0, np.cumsum(Z["bad"])]; cs = np.r_[0, np.cumsum(Z["shchg"])]
            okk = ~win_flag(cb, r - 2, kf) & ~win_flag(cs, r - 1, kf)
            mM = okk & (rs == 1) & (wi == w) & Z["F"][r, rd] & ~viol.astype(bool)
            sel = np.flatnonzero(mM); u = sel[uniq_latest(kf[sel], r[sel])]
            mine = {int(kf[k]): (int(r[k]), float(Z["l"][r[k]])) for k in u}
            # 長紅旗標另算
            Ff = []
            for q in range(len(bars)):
                b = bars[q]; ok = False
                if q > 0:
                    nm, kind, a, bb = REDS[rd]
                    if kind == "a":
                        ok = b["c"] / bars[q - 1]["c"] - 1 >= a
                    else:
                        rg = b["h"] - b["l"]
                        ok = rg > 0 and (b["c"] - b["l"]) / rg >= a and (b["c"] - b["o"]) / rg >= bb
                Ff.append(ok)
            i0 = int(np.searchsorted(Z["idx"], cal.searchsorted(pd.Timestamp(SCAN_FROM[world]))))
            badc = [bool(x) for x in Z["bad"]]; shc = [bool(x) for x in Z["shchg"]]
            ref = chk_nwave_events(bars, rd, w, "M", (badc, shc), [Ff[q] and q >= max(i0, 1) for q in range(len(bars))])
            tag = f"N型 {sid} {REDS[rd][0]} 窗{NWS[w]}"
        ks = set(mine) | set(ref)
        if not ks:
            continue
        res["①抽查（股×格）"] += 1; res["①事件數"] += len(ks)
        diff = 0
        for kx in ks:
            a = mine.get(kx); b = ref.get(kx)
            if a is None or b is None:
                diff += 1; continue
            if typ < 2:
                if a[0] != b[0] or abs(a[1] - b[1]) > 1e-9 or abs(a[2] - b[2]) > 1e-9 or abs(a[3] - b[3]) > 1e-9:
                    diff += 1
            elif a[0] != b[0] or abs(a[1] - b[1]) > 1e-9:
                diff += 1
        res["①不同"] += diff
        det.append({"抽": tag, "事件": len(ks), "不同": diff})
    log(f"[check ①] {res}")
    # ② 1 格：N字底甲2 d1 10%、W_B10、收盤、W_R5、ε1%、量能 ⓐ0.8 ⓑ1.2 ⓒ0.8 ⓓ1.5、ver0、H20、確認段
    sc = sc_of(1, 0, 1, 1); sh = 2 * NSC + sc; vc = ((0 * 3 + 1) * 2 + 0) * 3 + 1; q = HS.index(20)
    sgm = SEG["確認"]
    ev = []
    for si in range(len(uni)):
        sid = uni["stock_id"].iloc[si]
        fp = os.path.join(wd, "st", sid + ".npz")
        if not os.path.exists(fp):
            continue
        Z = dict(np.load(fp)); T = ndb_table(Z)
        if T is None:
            continue
        mk_ = (T["t2"] >= 0) & T["ok2"] & (T["sc"] == sc) & (T["d1"] >= 0.10) & (T["r1"] < 0.8) & (T["r2"] > 1.2) & (T["r3"] < 0.8) & (T["r4"] > 1.5)
        for k in np.flatnonzero(mk_):
            ev.append((si, int(T["t2"][k]), int(T["i"][k]), float(T["plo2"][k]), float(T["B"][k] + T["B"][k] - T["L"][k])))
    E = pd.DataFrame(ev, columns=["si", "t", "i", "stop", "tgt"]).sort_values(["si", "t", "i"]).drop_duplicates(["si", "t"], keep="last")
    # 自己建全體固定持有 H20 與 r20（逐檔重讀）
    S = len(uni); R20h = np.full((S, n), np.nan); r20 = np.full((S, n), np.nan); okb = np.zeros((S, n), bool)
    PX = {}
    for si in range(S):
        sid, mk = uni["stock_id"].iloc[si], uni["market"].iloc[si]
        fp = os.path.join(wd, "st", sid + ".npz")
        if not os.path.exists(fp):
            continue
        Z = dict(np.load(fp))
        idx = Z["idx"]; cff = Z["cff"]; oA = Z["oA"]; bo = Z["buy_ok"]; hd = Z["hdef"]
        cA = np.full(n, np.nan); cA[idx] = Z["c"]
        for kk in range(20, len(idx)):
            r20[si, idx[kk]] = Z["c"][kk] / Z["c"][kk - 20] - 1
        for t in idx:
            if t + 1 < n and bo[t + 1]:
                if hd[t] >= 20:
                    R20h[si, t] = cff[t + 20] / oA[t + 1] - 1
                if hd[t] >= 5:
                    okb[si, t] = True
        PX[si] = Z
    a, b = (pd.Period(x) for x in sgm)
    xs = []
    for si, g in E.groupby("si"):
        Z = PX[si]; idx = list(Z["idx"]); m = len(idx); last = -1e18
        for t, stop, tgt in zip(g["t"], g["stop"], g["tgt"]):
            t = int(t)
            if not (t + 1 < n and Z["buy_ok"][t + 1] and Z["hdef"][t] >= 20):
                continue
            e_ = t + 1; ev_ = idx.index(e_)
            price = None; et = None
            k = ev_
            while k < m and idx[k] <= t + 19:
                if Z["c"][k] < stop or Z["c"][k] >= tgt:
                    if k + 1 < m and idx[k + 1] <= t + 20:
                        price = Z["o"][k + 1] if np.isfinite(Z["o"][k + 1]) else Z["c"][k + 1]; et = idx[k + 1] - 0.5
                    break
                k += 1
            if price is None:
                price = Z["cff"][t + 20]; et = t + 20.0
            if not t > last:
                continue
            last = et
            Rr = price / Z["oA"][e_] - 1
            # 自己分十分位
            col = np.where(okb[:, t] & np.isfinite(r20[:, t]), r20[:, t], np.nan)
            okc = np.flatnonzero(np.isfinite(col))
            order = sorted(okc.tolist(), key=lambda z: (col[z], z))
            dq = {z: (rk * 10) // len(order) for rk, z in enumerate(order)}
            if si not in dq:
                continue
            peers = [z for z in order if dq[z] == dq[si] and z != si and np.isfinite(R20h[z, t])]
            if not peers:
                continue
            dt = cal[t]
            if not (a.start_time <= dt <= b.end_time):
                continue
            xs.append((dt.year * 12 + dt.month, Rr - float(np.mean(R20h[peers, t]))))
    X = pd.DataFrame(xs, columns=["m", "x"])
    N = len(X); mu = X["x"].mean()
    se = np.sqrt(sum((g["x"].sum() - mu * len(g)) ** 2 for _, g in X.groupby("m"))) / N
    C = pd.read_csv(os.path.join(OUT, "cells.csv.gz"))
    row = C[(C["型態"] == "N字底") & (C["進場"] == "甲2") & (C["形狀"] == shape_name(sh)) & (C["量能"] == vol_name(vc, 36)) & (C["停損"] == "回測低點停損") & (C["H"] == 20) & (C["段"] == "確認")]
    mine = row.iloc[0]
    d2 = {"n_本程式": int(mine["M_n"]), "n_重算": int(N), "X2_本程式": float(mine["M_X2"]), "X2_重算": float(mu), "下緣_本程式": float(mine["M_下緣"]), "下緣_重算": float(mu - Z95 * se)}
    res["②不同"] = int(d2["n_本程式"] != d2["n_重算"]) + int(abs(d2["X2_本程式"] - d2["X2_重算"]) > 1e-9) + int(abs(d2["下緣_本程式"] - d2["下緣_重算"]) > 1e-9)
    res["②"] = d2; res["①明細"] = det; res["過"] = res["①不同"] == 0 and res["②不同"] == 0
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[check] {json.dumps({k: v for k, v in res.items() if k != '①明細'}, ensure_ascii=False, default=float)}")
    S_ = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    S_["查核"] = {k: v for k, v in res.items() if k != "①明細"}
    json.dump(S_, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=("build", "stats", "page"))
    ap.add_argument("--world", choices=("main", "early"))
    ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    tag = "check" if a.check else (a.stage + (f"_{a.world}" if a.world else ""))
    logf = open(os.path.join(OUT, f"run_{tag}.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    log(f"===== researchNpattern {tag}｜讀法寫死 {TIME}｜{REG} =====")
    if a.check:
        check(log)
    elif a.stage == "build":
        build(a.world, a.procs, log)
    elif a.stage == "stats":
        stats(log)
    else:
        page(log)
    log(f"[完] {time.time() - T0:.0f}s")


if __name__ == "__main__":
    main()
