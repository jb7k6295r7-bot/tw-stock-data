# -*- coding: utf-8 -*-
"""PREREG飆股回推 seq5（台股策略線 登錄 sha 90ecf06e7f3d906a；裁定 seq276 拿掉舊參數、seq277 漲幅不設上限、seq278 核准＋g 網格照 seq277）——回測線。

    建表：   cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchSurge5 --stage build [--procs 2]
    橫斷面： ... --stage cross
    描述層： ... --stage desc          （第一批交件：網格計數、最大漲幅分佈、花幾天、高點後回落、結束時點、買不買得到）
    特徵層： ... --stage feat          （第二批：特徵 ①②③、挑選、確認、早年、妖股、結束特徵）
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchSurge5_check.py

⭐ 分析開始時間：2026-09-29 16:22（台北）｜所用登錄：seq5（sha 90ecf06e7f3d906a，去 pw1 行後驗）｜g 網格照裁定 seq277（seq278 §2）
⭐ 執行者未看過 seq4 結果（backtest/resultsSurge/_seq4_seen/ 與 /tmp 下舊 log 一律未開）；沿用的只有 surge_features.py 的函式（財報、借券、注意處置讀取、KD／RSI／EMA）
⭐ 結果句不附舊研究結論（seq5 §十之七）

═══ 資料 ═══
 價量：接合版面 ＝ 早年版面 950ad26e12（2004-02-11～2014-12-31，只上市）＋ tw-stock-data main b53f5540a8（2015-01-05～2026-09-24；git archive 唯讀 ~/h2data/surge_b53f5540a8ad）
       接法同 researchEvt.stitch（stocks 逐列相接；adj：早年事件 cum_factor × main 第一個事件 cum_factor）⇒ ~/evtdata/stitch_950ad26e12_b53f5540a8/data
 月營收：早年版面 950ad26e12 mops/revenue_hist ＋ main；財報 A2、法人、融資、借券、注意、處置、產業、集保：main b53f5540a8
 工作檔（大、不進 repo）：~/s5work/；結果：backtest/resultsSurge5/

═══ 本線自己補的讀法（S 標；⭐ 看任何本件數字前寫死）═══
 S1 列 ＝ 觀察日 t（該股 t 有有效 K 棒）× 股票；特徵只用 t 收盤（含）以前可得資料（月營收照公布日、財報照 A2 可用日、集保照資料日期 ＜ t 的最新一週）；
    飆股標籤以 t 收盤為基準：(t, t＋H] 內最高收盤（還原、停牌日沿用前一收盤）≥ t 收盤 ×（1＋g）；可交易 ＝ t＋1 開盤買
 S2 母體 ＝ 接合版面 kind＝stock、上市櫃、gate3（-DR、創新板含 -KY創 剔除；新件 innov_ky 開）＝「上市櫃普通股」，含已下市、注意、處置、停牌前後；
    ⛔ 不套 W1、流動性、處置閘；早年段（2005～2014）接合版面 2015 以前只有上市 ⇒ 自然只上市
 S3 壞根（seq5「含停牌前後」取代 seq4 的「≥5 日缺口」）：只剩兩種「價格序列接不起來」的點——① 幽靈還原事件（還原事件日原始價比 ÷ 因子 ∉ [0.895, 1.105]）
    ② 價格斷點（相鄰兩個有成交日收盤比 ≤ 0.55 或 ≥ 1.8、其間無還原事件；data.breakpoints 的 price／price＋gap）；⛔ 純停牌缺口（gap）不算壞根
    ⇒ 標籤窗、報酬窗 (t, t＋h] 內有壞根 ⇒ 該列該 h 不定義（不進分母）；有回看期的特徵，回看窗內有壞根 ⇒ 該特徵 NaN
 S4 標籤定義域：t＋H ≤ 日曆末日（2026-09-24）且窗內無壞根；下市後收盤沿用最後一價（＝ 強制出場價）
 S5 事件：同一檔、同一格，依 t 由早到晚，成立日與上一個事件相隔 ＞ H 才算新事件；被跳過的日子仍在分母、標籤 0（seq4 同讀法）
    「≥ g」一律以 收盤 ≥ t 收盤 ×（1＋g）×（1 − 1e−9）比（剛好漲 g 的不被浮點誤差判成沒到；查核 ② 抓到後補）
 S6 g 網格 ＝ 50,100,150,200,250,300,400,500,700,1000%（每格「至少漲 g」；1000% 那格即「≥ 1000%」）；H 10～250 每 10 ⇒ 250 格；
    分段版：落在 [g_i, g_(i+1)) 的事件（以該格 H 內最大漲幅判）；最大漲幅分佈（不分格）：所有格的事件取 (股, t) 聯集，報 250 日內最大漲幅與「不設 H」最大漲幅
 S7 高點 P ＝ 事件 (t, t＋H] 內最高收盤那天（同價取最早）；「不設 H」版 P* ＝ 從 P 起跟著創新高、直到第一次收盤 ≤ 當時最高 × 0.7 之前的最高點（P* ≥ P；到資料尾沒回落 ⇒ 標未完）
 S8 P 後回落 x%（x ∈ 10,20,30,50,70）：P 後任何時間（到下市、壞根或資料尾為止）第一次收盤 ≤ P 收盤 ×（1−x）；比例 ＝ 觸及事件 ÷ 全部事件（沒觸及含觀察期不足，照報觀察天數）；
    另報 60／120／250 日內觸及比例（分母 ＝ 觀察期夠長或已觸及）；妖股（描述分報用）＝ P 後回落 ≥ 50%
 S9 特徵清單：登錄 §二、§七、§八、§九之二 的底層量，凡有天數者 5／10／20／60／120／250 六個回看並列；門檻型改連續值；
    使用者原門檻版本（§二 二元、K1～K5、R1～R2、V1～V3、X1～X3、量縮 0.7）另列「描述」⛔ 不進挑選；狀態型二元（停止融資）進挑選
    回看期定義（寫死）：報酬 c/c[−L]−1｜距 L 日高／低｜收盤÷MA_L−1｜L 日區間寬度 max/min−1｜L 日帶寬（std/mean）÷自身 250 根中位｜L 日漲停天數｜
    L 日抗跌（0050 下跌日的個股−0050 平均日報酬）｜前 L 日 MA5/10/20 最大÷最小−1｜當日額÷前 L 日均額｜近 L 日均額÷再前 L 日均額｜L 日均額｜L 日平均周轉率｜
    外資／投信 L 日淨買÷股本｜融資、借券 L 日變化÷股本｜L 日注意次數、處置天數｜產業 L 日報酬排名（產業平均、產業間五等分）｜0050 收盤÷MA_L−1｜集保 400 張以上 L/5 週變化
 S10 五等分 ＝ 當日（有 K 棒的母體）橫斷面、同值同組（rank＝嚴格小於者個數；q＝rank×5÷k＋1）⇒ 大量同值（例漲停天數 0）會集中在低組、部分組可能空；
     大盤類（0050 收盤÷MA_L）全市場同值 ⇒ 改用時間序列：當日值在自身前 750 個交易日的分位五等分（⛔ 不看未來）
 S11 ① 提升倍數 ＝ 有特徵者（該格 H 定義域內）事件比例 ÷ 同段「該特徵有值」者事件比例；CI ＝ 有特徵者比例的曆月分群 CR0（依 t 的月份）÷ 全體比例；② 涵蓋率 ＝ 事件中有特徵的比例（特徵有值者）
 S12 挑：探索段（2017-01～2021-12）250 格中 ≥ 125 格「① 95% 下緣 ＞ 1 且 ② ≥ 5%」⇒ 進確認段；確認段（2022-01～2026-08）≥ 125 格「① Bonferroni（k＝進確認段數）下緣 ＞ 1」⇒ 站得住（② 照報）；
     早年（2005～2014）照驗（95%），報 ① ＞ 1 的格數與方向；早年無資料的類（法人、融資、借券、注意處置、集保、財報）標「無資料」
 S13 ③ 可交易曲線：t＋1 開盤買（t＋1 有成交、開盤有效、⛔ 非漲停鎖死〔開＝高＝低＝漲停價〕），持有 h ∈ 5～250（每 5）以收盤計：R_h ＝ c_ff[t＋h]÷o[t＋1]−1；
     對全體 X1 ＝ R − 同日其他股平均；對基準② X2 ＝ R − 同日同十分位其他股平均（十分位 ＝ 同日可買且前 20 日報酬可算者依前 20 日報酬分，不隨 h 變）；
     扣成本讀法 ＝ 成本帶：CI 下緣 − 0.585% ＞ 0 才算「買了賺」（對照不付成本）；淨報酬曲線 R − 0.585% 另報；確認段 CI 用 Bonferroni z；連續 ≥ 3 格才標區間
 S14 買不買得到：t＋1 無成交、t＋1 漲停鎖死、t＋1 處置中（main disposal 起訖）⇒ 報比例與「剔除這些列後」的網格與挑選特徵；近 20 日均額五等分只報分佈
 S15 妖股特徵：各格事件內，特徵（看 t）對「P 後回落 30／50／70%」的提升倍數＋涵蓋率（月分群依 t）；挑與驗同 S12（每個 x 各一族）
 S16 結束特徵：各格、各「結束套」x ∈ {10,20,30}（P 後曾回落 x% 的事件）× k ∈ {1,3,5,10,20}：陽性 ＝ P−k 那一天，對照 ＝ 同一事件漲勢中段 t＋(P−t)//2（須 P−中段 ＞ 20、中段 ＞ t）；
     y＝1 陽性、0 對照 ⇒ 提升倍數 ＝ 有特徵者陽性比例 ÷ 全部陽性比例、涵蓋率 ＝ 陽性中有特徵比例；挑與驗同 S12（每個 x×k 一族）
 S17 N_單筆 ＝ 確認段實際驗的特徵數（各族加總，照實）；Bonferroni 各族用自己的 k（另報用總 N 時結論變不變）
 S19 結束特徵可交易（seq5 §十之六；描述＋確認段標區間）：對象 ＝ 各段所有格事件的 (股, t) 聯集（＝ 手上抱著一檔真飆股，事後挑的，只描述）；
     t＋1 開盤買；規則 A ＝ 持有中該結束特徵（確認段站得住的級距）第一次出現於 d（t ＜ d ≤ t＋h−1）⇒ d 之後第一個有效開盤賣，否則抱到 t＋h 收盤；
     規則 B ＝ 抱到 t＋h 收盤（＝ R_h）；報 A−B 的平均（月分群 CI；確認段 Bonferroni k ＝ 站得住的不同級距數），連續 ≥ 3 格下緣 ＞ 0 ⇒ 標「一出現就賣較好」、上緣 ＜ 0 ⇒ 標「續抱較好」
     （⚠ S19 寫於看過「哪些結束特徵站得住」之後、看任何 A−B 數字之前）
 S18（⚠ 看過第一批「從起漲日算」天數後補，照實寫）：起漲日 ＝「H 日內會漲到的第一天」⇒ 從它算的天數天生貼近 H（構造使然）；
     另報「最短花幾天」＝ H＝250 的事件在 [t, P] 內任選起點 s、第一次收盤 ≥ s 收盤 ×（1＋g）的天數取最小；與網格累積（H 日內事件數 ÷ 250 日內）並列；只描述、不進任何判定
輸出 backtest/resultsSurge5/
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import universe_gate as UG
UG.set_innov_ky(True)                                               # ⭐ 新件
from backtest import data as D
from backtest import research11 as R11
from backtest import research34 as R34
from backtest import p4_features as P4F
from backtest import avgdown as AV
from backtest import surge_features as SF

START = "2026-09-29 16:22（台北）"
SEQ = "seq5（sha 90ecf06e7f3d906a）"
MAIN_SHA = "b53f5540a8add6927d72d57d010466631d4bfb08"
EARLY_SHA = "950ad26e1293592457ec28194f0c5eaebfd3e53b"
EARLY = os.path.expanduser("~/earlydata/950ad26e12/main/data")
MAIN = os.path.expanduser(f"~/h2data/surge_{MAIN_SHA[:12]}/data")
ST = os.path.expanduser("~/evtdata/stitch_950ad26e12_b53f5540a8/data")
WORK = os.environ.get("S5WORK", os.path.expanduser("~/s5work"))
OUT = "backtest/resultsSurge5"
COST = 0.00585
HS = tuple(range(10, 251, 10))                                      # 25
GS = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.0, 10.0)            # 10（裁定 seq277）
NC = len(HS) * len(GS)                                              # 250
LB = (5, 10, 20, 60, 120, 250)
HOLD = tuple(range(5, 251, 5))                                      # 50
DD = (0.10, 0.20, 0.30, 0.50, 0.70)
KEND = (1, 3, 5, 10, 20)
SEG = {"探索": ("2017-01", "2021-12"), "確認": ("2022-01", "2026-08"), "早年": ("2005-01", "2014-12")}
_G: dict = {}


def cell_of(hi, gi):
    return hi * len(GS) + gi


def cell_name(c):
    return f"H{HS[c // len(GS)]}_g{int(round(GS[c % len(GS)] * 100))}%"


# ═════════════ 特徵清單 ═════════════
def feature_specs():
    """(欄, 名稱, 類別, 型態, L, 早年可用)；型態：q（橫斷面五等分）｜qts（時間序列五等分，已是 1～5）｜bin（狀態二元，進挑選）｜dbin（原門檻二元，描述）｜dlvl（原門檻級距，描述）｜x（cross 階段填）"""
    F = []
    for L in LB:
        F += [(f"r_{L}", f"{L}日報酬", "價", "q", L, True), (f"dhi_{L}", f"距{L}日最高", "價", "q", L, True),
              (f"dlo_{L}", f"距{L}日最低", "價", "q", L, True), (f"ma_{L}", f"收盤÷MA{L}−1", "價", "q", L, True),
              (f"rng_{L}", f"{L}日區間寬度", "價", "q", L, True), (f"bbw_{L}", f"{L}日帶寬÷自身250根中位", "價", "q", L, True),
              (f"lu_{L}", f"{L}日漲停天數", "價", "q", L, True), (f"anti_{L}", f"{L}日抗跌", "價", "q", L, True),
              (f"tang_{L}", f"前{L}日均線5/10/20糾結度", "價", "q", L, True),
              (f"ar_{L}", f"當日額÷前{L}日均額", "量", "q", L, True), (f"achg_{L}", f"近{L}日均額÷再前{L}日均額", "量", "q", L, True),
              (f"amt_{L}", f"{L}日均額", "量", "q", L, True), (f"turn_{L}", f"{L}日平均周轉率", "量", "q", L, True),
              (f"fnet_{L}", f"外資{L}日淨買÷股本", "法人", "q", L, False), (f"tnet_{L}", f"投信{L}日淨買÷股本", "法人", "q", L, False),
              (f"mchg_{L}", f"融資{L}日變化÷股本", "融資", "q", L, False), (f"sbl_{L}", f"借券賣出餘額{L}日變化÷股本", "借券", "q", L, False),
              (f"att_{L}", f"{L}日注意次數", "注意處置", "q", L, False), (f"disp_{L}", f"{L}日處置天數", "注意處置", "q", L, False)]
    F += [("kdK", "KD的K值", "技術", "q", None, True), ("kdrun", "K＞80連續天數", "技術", "q", None, True),
          ("rsi14", "RSI14", "技術", "q", None, True), ("rsid", "RSI6−RSI12", "技術", "q", None, True),
          ("bbup", "收盤÷布林上軌(20,2)−1", "技術", "q", None, True), ("x3", "EMA5/10/20最大÷最小−1", "技術", "q", None, True),
          ("v2run", "EMA20＞SMA20連續天數", "技術", "q", None, True), ("v3box", "收盤÷修正箱上箱價−1", "技術", "q", None, True),
          ("maalign", "均線多頭排列段數(5/10/20/60/120/250)", "技術", "q", None, True),
          ("yoy", "營收年增率", "營收", "q", None, True), ("mom", "營收月增率", "營收", "q", None, True),
          ("streak", "營收連續年增月數", "營收", "q", None, True), ("d24", "距24月最高營收", "營收", "q", None, True),
          ("y3chg", "近3月年增率平均−前3月平均", "營收", "q", None, True),
          ("eps", "最近一季EPS", "財報A2", "q", None, False), ("gmd", "毛利率−上季", "財報A2", "q", None, False),
          ("opmd", "營益率−去年同季", "財報A2", "q", None, False), ("roe", "ROE", "財報A2", "q", None, False),
          ("musage", "融資使用率", "融資", "q", None, False), ("tstreak", "投信連買天數", "法人", "q", None, False),
          ("mcap", "市值", "規模", "q", None, True), ("shares", "股本", "規模", "q", None, True), ("price", "股價", "規模", "q", None, True),
          ("f_mstop", "停止融資中", "融資", "bin", None, False)]
    for L in LB:
        F += [(f"mkt_{L}", f"0050收盤÷MA{L}−1（時序）", "大盤", "qts", L, True)]
    for L in LB:
        F += [(f"indrk_{L}", f"產業{L}日報酬排名", "產業", "x", L, True), (f"tdcc_{L}", f"集保400張以上{max(1, L // 5)}週變化", "集保", "x", L, False)]
    # 使用者原門檻（描述；⛔ 不進挑選）
    F += [("d_revhi", "原：營收創24月新高", "營收", "dbin", None, True), ("d_R1", "原R1營收轉折", "營收", "dbin", None, True),
          ("d_R2a", "原R2營收年增≥50%", "營收", "dbin", None, True), ("d_R2b", "原R2營收年增≥100%", "營收", "dbin", None, True),
          ("d_eps", "原：EPS轉正", "財報A2", "dbin", None, False), ("d_gm", "原：毛利率比上季升", "財報A2", "dbin", None, False),
          ("d_opm", "原：營益率比去年同季升", "財報A2", "dbin", None, False),
          ("d_bull", "原：均線多頭排列5>20>60>100", "價", "dbin", None, True), ("d_ma100", "原：收盤站上MA100", "價", "dbin", None, True),
          ("d_mkt200", "原：0050在200日線上", "大盤", "dbin", None, True),
          ("d_px", "原：股價級距", "規模", "dlvl", None, True), ("d_lu20", "原：20日漲停天數級距", "價", "dlvl", None, True),
          ("d_tstreak", "原：投信連買天數級距", "法人", "dlvl", None, False), ("d_att60", "原：注意股60日次數級距", "注意處置", "dlvl", None, False),
          ("d_disp60", "原：60日內曾處置", "注意處置", "dbin", None, False),
          ("d_K1", "原K1 KD高檔鈍化(K>80連3日)", "技術", "dbin", None, True), ("d_K1l", "原K1 K>80連續天數級距", "技術", "dlvl", None, True),
          ("d_K2", "原K2 布林上軌帶量突破", "技術", "dbin", None, True), ("d_K3a", "原K3 RSI14>50", "技術", "dbin", None, True),
          ("d_K3b", "原K3 RSI6上穿RSI12", "技術", "dbin", None, True), ("d_K4", "原K4 均線糾結後發動", "技術", "dbin", None, True),
          ("d_K5a", "原K5 周轉率≥10%", "量", "dbin", None, True), ("d_K5b", "原K5 周轉率≥20%", "量", "dbin", None, True),
          ("d_V1", "原V1 量縮盤整後帶量突破", "技術", "dbin", None, True), ("d_V2l", "原V2 EMA20>SMA20連續天數級距", "技術", "dlvl", None, True),
          ("d_V3", "原V3 修正箱突破", "技術", "dbin", None, True), ("d_X1", "原X1 熊狗篩選", "技術", "x", None, True),
          ("d_X2", "原X2 區間突破後量縮", "技術", "dbin", None, True), ("d_X3", "原X3 EMA糾結向上", "技術", "dbin", None, True),
          ("d_shrink", "原：量縮狀態(20日均額≤前120日均額×0.7)", "量", "dbin", None, True)]
    return F


SPECS = feature_specs()
FCOL = [f[0] for f in SPECS]
FIX = {c: i for i, c in enumerate(FCOL)}
LVLN = {"d_px": {0: "＜20 元", 1: "20～50 元", 2: "50～100 元", 3: "≥100 元"}, "d_lu20": {0: "0 次", 1: "1 次", 2: "2 次", 3: "≥3 次"},
        "d_tstreak": {0: "0 天", 1: "1～2 天", 2: "3～5 天", 3: "≥6 天"}, "d_att60": {0: "0 次", 1: "1～2 次", 2: "≥3 次"},
        "d_K1l": {0: "0 天", 1: "1～2 天", 2: "3～5 天", 3: "≥6 天"}, "d_V2l": {0: "0 天", 1: "1～4 天", 2: "5～9 天", 3: "≥10 天"}}


# ═════════════ 接合版面 ═════════════
def stitch(log):
    done = os.path.join(ST, "STITCH.json")
    if os.path.exists(done):
        return json.load(open(done, encoding="utf-8"))
    for sub in ("stocks", "adj", "meta"):
        os.makedirs(os.path.join(ST, sub), exist_ok=True)
    ec = pd.read_csv(os.path.join(EARLY, "meta", "calendar_twse.csv"))["date"]; mc = pd.read_csv(os.path.join(MAIN, "meta", "calendar_twse.csv"))["date"]
    assert ec.max() <= "2014-12-31" < mc.min(), "⛔ 兩段日曆重疊"
    pd.DataFrame({"date": list(ec) + list(mc)}).to_csv(os.path.join(ST, "meta", "calendar_twse.csv"), index=False)
    es = pd.read_csv(os.path.join(EARLY, "meta", "stocks.csv"), dtype=str); ms = pd.read_csv(os.path.join(MAIN, "meta", "stocks.csv"), dtype=str)
    fs = es.set_index("stock_id")["first_seen"].to_dict()
    ms2 = ms.copy(); ms2["first_seen"] = [min(fs.get(s, f), f) for s, f in zip(ms2["stock_id"], ms2["first_seen"])]
    roster = pd.concat([ms2, es[~es["stock_id"].isin(set(ms["stock_id"]))]], ignore_index=True)
    roster.to_csv(os.path.join(ST, "meta", "stocks.csv"), index=False)
    ed = pd.read_csv(os.path.join(EARLY, "meta", "delisted.csv"), dtype=str); md = pd.read_csv(os.path.join(MAIN, "meta", "delisted.csv"), dtype=str)
    pd.concat([md, ed[~ed["stock_id"].isin(set(md["stock_id"]))]], ignore_index=True).to_csv(os.path.join(ST, "meta", "delisted.csv"), index=False)
    keep = sorted(set(roster.loc[roster["kind"] == "stock", "stock_id"]) | {"0050"})
    cnt = {"檔": 0, "兩段都有": 0, "只早年": 0, "只main": 0, "adj 乘數≠1": 0}
    for s in keep:
        pe, pm = os.path.join(EARLY, "stocks", s + ".csv"), os.path.join(MAIN, "stocks", s + ".csv")
        parts = []
        for p, lo, hi in ((pe, None, "2014-12-31"), (pm, "2015-01-05", None)):
            if os.path.exists(p):
                x = pd.read_csv(p, dtype=str, keep_default_na=False)
                x = x[x["date"] >= lo] if lo else x
                x = x[x["date"] <= hi] if hi else x
                parts.append(x)
        if not parts:
            continue
        if len(parts) == 2:
            assert list(parts[0].columns) == list(parts[1].columns), s
        pd.concat(parts, ignore_index=True).to_csv(os.path.join(ST, "stocks", s + ".csv"), index=False)
        cnt["檔"] += 1; cnt["兩段都有" if len(parts) == 2 and all(len(p_) for p_ in parts) else ("只早年" if os.path.exists(pe) and not os.path.exists(pm) else "只main")] += 1
        ae, am = os.path.join(EARLY, "adj", s + ".csv"), os.path.join(MAIN, "adj", s + ".csv")
        A = []; mult = 1.0; m = None
        if os.path.exists(am):
            m = pd.read_csv(am, dtype=str, keep_default_na=False); m = m[m["date"] > "2014-12-31"]
            if len(m):
                mult = float(m["cum_factor"].iloc[0])
        if os.path.exists(ae):
            e = pd.read_csv(ae, dtype=str, keep_default_na=False)
            assert (e["date"] <= "2014-12-31").all(), s
            cnt["adj 乘數≠1"] += int(mult != 1.0)
            e["cum_factor"] = [repr(float(v) * mult) for v in e["cum_factor"]]
            A.append(e)
        if m is not None and len(m):
            A.append(m)
        if A:
            pd.concat(A, ignore_index=True).to_csv(os.path.join(ST, "adj", s + ".csv"), index=False)
    info = {"早年": EARLY_SHA, "main": MAIN_SHA, "日曆": [str(ec.iloc[0]), str(mc.iloc[-1]), int(len(ec) + len(mc))], **cnt}
    json.dump(info, open(done, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[接合] {info}")
    return info


# ═════════════ 世界 ═════════════
def world(log, limit=0):
    D.DATA = ST
    cal = D.load_calendar(); n = len(cal)
    stocks = pd.read_csv(os.path.join(ST, "meta", "stocks.csv"), dtype=str)
    uni = UG.gate3(stocks)
    have = {f[:-4] for f in os.listdir(os.path.join(ST, "stocks"))}
    uni = uni[uni["stock_id"].isin(have)].sort_values("stock_id").reset_index(drop=True)
    if limit:
        uni = uni.iloc[::max(1, len(uni) // limit)].reset_index(drop=True)
    W = {"cal": cal, "sids": list(zip(range(len(uni)), uni["stock_id"], uni["market"]))}
    fs = sorted(glob.glob(os.path.join(EARLY, "mops", "revenue_hist", "*.csv"))) + sorted(glob.glob(os.path.join(MAIN, "mops", "revenue_hist", "*.csv")))
    df = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收"]) for f in fs])
    df["rev"] = pd.to_numeric(df["當月營收"], errors="coerce"); df = df.drop_duplicates(["stock_id", "period"], keep="last")
    rev = df.pivot(index="period", columns="stock_id", values="rev").sort_index()
    W["REV"] = rev; W["REVFLAG"] = P4F.rev_hi24_flags(rev, cal)
    rd = R34.rebalance_dates(list(rev.index), cal, 10)
    W["REV_EFF"] = np.array([rd[p][1] if p in rd else (n + 10 if pd.Period(p) > pd.Period(str(cal[-1])[:7]) else -1) for p in rev.index])
    b = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy(float)).ffill().to_numpy()
    W["M50"] = b
    MK = {}
    for L in LB:
        v = b / pd.Series(b).rolling(L, min_periods=L).mean().to_numpy() - 1
        q = np.full(n, np.nan)
        for t in range(n):
            if not np.isfinite(v[t]):
                continue
            h = v[max(0, t - 750):t]; h = h[np.isfinite(h)]
            if len(h) >= 250:
                q[t] = min(5, int((h < v[t]).sum() * 5 // len(h)) + 1)
        MK[L] = q
    W["MKTQ"] = MK
    W["MKT200"] = np.where(np.isfinite(b) & (np.arange(n) >= 199), (b > pd.Series(b).rolling(200).mean().to_numpy()).astype(float), np.nan)
    W.update(SF.fin_table(MAIN, cal)); W["SBL"] = SF.sbl_series(MAIN, cal); W["ATT"], W["DISP"] = SF.att_disp(MAIN, cal)
    W["ATT_FIRST"] = int(cal.searchsorted(pd.Timestamp("2011-01-03")))
    log(f"[世界] 日曆 {cal[0].date()}～{cal[-1].date()}（{n}）｜母體 {len(uni)} 檔｜營收期 {rev.index.min()}～{rev.index.max()}")
    return W, uni


def _init(W):
    D.DATA = ST; _G.clear(); _G.update(W)


def _roll(x, w, fn):
    return getattr(pd.Series(x).rolling(w, min_periods=w), fn)().to_numpy()


def _prev(x, k=1):
    return np.r_[np.full(k, np.nan), x[:-k]] if k < len(x) else np.full(len(x), np.nan)


# ═════════════ 每檔 ═════════════
def stock(args):
    si, sid, mk = args
    W = _G; cal = W["cal"]; n = len(cal)
    st = D.load_stock(sid, mk, cal)
    if st is None:
        return None
    df = st.df
    cA = df["close"].to_numpy(float); oA = df["open"].to_numpy(float); hA = df["high"].to_numpy(float); lA = df["low"].to_numpy(float)
    idx = np.flatnonzero(np.isfinite(cA))
    m = len(idx)
    if m < 2:
        return None
    raw = pd.read_csv(os.path.join(ST, "stocks", sid + ".csv"), dtype={"date": str}, usecols=["date", "open", "high", "low", "close", "shares"]).drop_duplicates("date")
    raw.index = pd.to_datetime(raw["date"]); raw = raw.reindex(cal)
    rr = {k: np.array(pd.to_numeric(raw[k], errors="coerce"), dtype=float) for k in ("open", "high", "low", "close")}
    for k in rr:
        rr[k][~(rr[k] > 0)] = np.nan
    shA = pd.to_numeric(raw["shares"], errors="coerce").ffill().to_numpy(float); shA = np.where(shA > 0, shA, np.nan)
    c, o, h, l = cA[idx], oA[idx], hA[idx], lA[idx]
    amt = pd.to_numeric(df["amount"], errors="coerce").to_numpy(float)[idx]
    vol = pd.to_numeric(df["volume"], errors="coerce").to_numpy(float)[idx]
    rc = rr["close"][idx]; sh = shA[idx]; dates = cal[idx]
    # ── 壞根（S3）
    adj = D.load_adj(sid)
    ev_bar = np.zeros(m, bool); bad_k = np.zeros(m, bool)
    if adj is not None and len(adj):
        for d, f in zip(adj["date"], adj["factor"].astype(float)):
            k = int(np.searchsorted(dates, d))
            if k >= m:
                continue
            ev_bar[k] = True
            if k > 0 and np.isfinite(rc[k]) and np.isfinite(rc[k - 1]) and f > 0:
                r = rc[k] / (rc[k - 1] * f)
                if r < 0.895 or r > 1.105:
                    bad_k[k] = True
    nbp = 0
    for b in D.breakpoints(df, st.event_dates):
        if b["rule"] in ("price", "price+gap"):
            k = int(np.searchsorted(idx, b["pos"]))
            if k < m:
                bad_k[k] = True; nbp += 1
    bad_day = np.zeros(n + 1, bool); bad_day[idx[bad_k]] = True
    nxt = np.full(n + 2, 10 ** 9)
    for p in range(n - 1, -1, -1):
        nxt[p] = p if bad_day[p] else nxt[p + 1]
    cbk = np.r_[0, np.cumsum(bad_k)]
    # ── 漲停、鎖死、可買
    skip = ev_bar.copy()
    if dates[0] > pd.Timestamp("2015-01-12"):
        skip[:5] = True
    up, _dn = R11.limit_flags(rc, dates, skip)
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
    last = int(idx[-1])
    # ── 特徵（有效 K 棒序列）
    NFW = len(FCOL)
    Fk = {}
    rS = lambda w_: np.r_[np.full(w_, np.nan), c[w_:] / c[:-w_] - 1] if w_ < m else np.full(m, np.nan)
    ma = {w_: _roll(c, w_, "mean") for w_ in (5, 10, 20, 60, 100, 120, 250)}
    m50 = W["M50"][idx]; rm = np.r_[np.nan, m50[1:] / m50[:-1] - 1]; rs = np.r_[np.nan, c[1:] / c[:-1] - 1]
    down = (rm < 0) & np.isfinite(rs)
    dd_ = np.where(down, rs - rm, 0.0); dn_ = down.astype(float)
    mas = np.vstack([ma[5], ma[10], ma[20]])
    okm = np.isfinite(mas).all(0)
    mxm = np.where(okm, np.where(okm, mas, -np.inf).max(0), np.nan); mnm = np.where(okm, np.where(okm, mas, np.inf).min(0), np.nan)
    turn = vol / sh
    span = {}
    for L in LB:
        Fk[f"r_{L}"] = rS(L); span[f"r_{L}"] = L + 1
        hi_, lo_ = _roll(c, L, "max"), _roll(c, L, "min")
        Fk[f"dhi_{L}"] = c / hi_ - 1; Fk[f"dlo_{L}"] = c / lo_ - 1; Fk[f"rng_{L}"] = hi_ / lo_ - 1
        mL = _roll(c, L, "mean"); Fk[f"ma_{L}"] = c / mL - 1
        bw = pd.Series(c).rolling(L, min_periods=L).std(ddof=0).to_numpy() / mL
        Fk[f"bbw_{L}"] = bw / pd.Series(bw).rolling(250, min_periods=250).median().to_numpy(); span[f"bbw_{L}"] = L + 250
        Fk[f"lu_{L}"] = _roll(up.astype(float), L, "sum")
        cnt = _roll(dn_, L, "sum"); Fk[f"anti_{L}"] = np.where(cnt > 0, _roll(dd_, L, "sum") / np.where(cnt > 0, cnt, 1), np.nan)
        Fk[f"tang_{L}"] = _prev(_roll(mxm, L, "max") / _roll(mnm, L, "min") - 1)      # 前 L 日（不含當日）三條均線最大÷最小−1（K4 的底層量）
        Fk[f"ar_{L}"] = amt / _prev(_roll(amt, L, "mean"))
        aL = _roll(amt, L, "mean"); Fk[f"amt_{L}"] = aL; Fk[f"achg_{L}"] = aL / _prev(aL, L) if L < m else np.full(m, np.nan)
        Fk[f"turn_{L}"] = _roll(turn, L, "mean")
        for k_ in ("dhi", "dlo", "rng", "ma", "lu", "anti", "turn", "amt"):
            span[f"{k_}_{L}"] = L + 1
        span[f"tang_{L}"] = L + 21; span[f"ar_{L}"] = L + 1; span[f"achg_{L}"] = 2 * L + 1
    # 技術（非回看型）
    K = SF.kd(c, h, l); Kr = SF.run_len(np.nan_to_num(K) > 80)
    R14, R6, R12 = SF.rsi(c, 14), SF.rsi(c, 6), SF.rsi(c, 12)
    sd20 = pd.Series(c).rolling(20, min_periods=20).std(ddof=0).to_numpy(); bu, bl = ma[20] + 2 * sd20, ma[20] - 2 * sd20
    e5, e10, e20 = SF.ema(c, 5), SF.ema(c, 10), SF.ema(c, 20)
    ex = np.vstack([e5, e10, e20]); x3 = ex.max(0) / ex.min(0) - 1; x3[:20] = np.nan
    v2 = SF.run_len(e20 > np.nan_to_num(ma[20], nan=np.inf))
    v3 = np.zeros(m, bool); v3box = np.full(m, np.nan); last_touch = -1; box = np.nan; low_since = False
    for i in range(m):
        if last_touch >= 0 and i - last_touch - 1 >= 20 and low_since:
            v3box[i] = c[i] / box - 1; v3[i] = c[i] > box
        if np.isfinite(bu[i]) and c[i] >= bu[i]:
            last_touch = i; box = h[i]; low_since = False
        elif np.isfinite(bl[i]) and c[i] <= bl[i]:
            low_since = True
    Fk["kdK"] = K; Fk["kdrun"] = np.where(np.isfinite(K), Kr, np.nan).astype(float)
    Fk["rsi14"] = R14; Fk["rsid"] = R6 - R12; Fk["bbup"] = c / bu - 1; Fk["x3"] = x3
    Fk["v2run"] = np.where(np.isfinite(ma[20]), v2, np.nan).astype(float); Fk["v3box"] = v3box
    mseq = [ma[5], ma[10], ma[20], ma[60], ma[120], ma[250]]
    al = np.zeros(m)
    for a_, b_ in zip(mseq[:-1], mseq[1:]):
        al += (a_ > b_)
    Fk["maalign"] = np.where(np.isfinite(ma[250]), al, np.nan)
    for k_ in ("kdK", "kdrun", "rsi14", "rsid", "bbup", "x3", "v2run", "v3box"):
        span[k_] = 30
    span["maalign"] = 251
    # 規模
    Fk["mcap"] = rc * sh; Fk["shares"] = sh; Fk["price"] = rc
    # 營收
    pos_d = idx
    for k_ in ("yoy", "mom", "streak", "d24", "y3chg", "d_R1", "d_R2a", "d_R2b", "d_revhi"):
        Fk[k_] = np.full(m, np.nan)
    V = W["REV"][sid].to_numpy(float) if sid in W["REV"].columns else None
    if V is not None:
        eff = W["REV_EFF"]
        yoy = np.full(len(V), np.nan); yoy[12:] = np.where((V[:-12] > 0) & np.isfinite(V[:-12]), V[12:] / V[:-12] - 1, np.nan)
        mom = np.full(len(V), np.nan); mom[1:] = np.where(V[:-1] > 0, V[1:] / V[:-1] - 1, np.nan)
        stk = np.zeros(len(V)); r0 = 0
        for j in range(len(V)):
            r0 = r0 + 1 if (np.isfinite(yoy[j]) and yoy[j] > 0) else 0; stk[j] = r0
        d24 = np.full(len(V), np.nan)
        for j in range(24, len(V)):
            hh = V[j - 24:j]; hh = hh[np.isfinite(hh)]
            if np.isfinite(V[j]) and len(hh) >= 18 and hh.max() > 0:
                d24[j] = V[j] / hh.max() - 1
        y3 = pd.Series(yoy).rolling(3, min_periods=3).mean().to_numpy()
        y3c = np.full(len(V), np.nan); y3c[3:] = y3[3:] - y3[:-3]
        r1 = np.full(len(V), np.nan); okr = np.zeros(len(V), bool); okr[3:] = np.isfinite(y3[3:]) & np.isfinite(y3[:-3])
        r1[3:] = ((y3[3:] > 0) & (y3[:-3] <= 0)).astype(float); r1[~okr] = np.nan
        order = np.argsort(eff, kind="stable"); effs = eff[order]
        for i in range(m):
            j = int(np.searchsorted(effs, pos_d[i], side="right")) - 1
            if j < 0:
                continue
            kx = order[j]
            while kx >= 0 and not np.isfinite(V[kx]):
                kx -= 1
            if kx < 0:
                continue
            Fk["yoy"][i] = yoy[kx]; Fk["mom"][i] = mom[kx]; Fk["streak"][i] = stk[kx]; Fk["d24"][i] = d24[kx]; Fk["y3chg"][i] = y3c[kx]
            Fk["d_R1"][i] = r1[kx]
            Fk["d_R2a"][i] = float(yoy[kx] >= 0.5) if np.isfinite(yoy[kx]) else np.nan; Fk["d_R2b"][i] = float(yoy[kx] >= 1.0) if np.isfinite(yoy[kx]) else np.nan
    if sid in W["REVFLAG"].columns:
        fv = W["REVFLAG"][sid].to_numpy(float)[pos_d]
        Fk["d_revhi"] = np.where(np.isfinite(fv), (fv == 100).astype(float), np.nan)
    # 財報 A2
    for k_ in ("eps", "gmd", "opmd", "roe", "d_eps", "d_gm", "d_opm"):
        Fk[k_] = np.full(m, np.nan)
    fr = W["FIN"].get(sid)
    if fr:
        fpos = np.array([x[0] for x in fr])
        for i in range(m):
            cj = np.flatnonzero(fpos <= pos_d[i])
            if len(cj) == 0:
                continue
            j = int(cj[-1]); _, y, q, eps, gm, opm, roe = fr[j]
            pv = fr[j - 1] if j >= 1 else None
            ly = next((x for x in fr[:j] if x[1] == y - 1 and x[2] == q), None)
            Fk["eps"][i] = eps; Fk["roe"][i] = roe
            if pv is not None and (pv[1], pv[2]) == ((y, q - 1) if q > 1 else (y - 1, 4)):
                if np.isfinite(eps) and np.isfinite(pv[3]):
                    Fk["d_eps"][i] = float(eps > 0 and pv[3] <= 0)
                if np.isfinite(gm) and np.isfinite(pv[4]):
                    Fk["gmd"][i] = gm - pv[4]; Fk["d_gm"][i] = float(gm > pv[4])
            if ly is not None and np.isfinite(opm) and np.isfinite(ly[5]):
                Fk["opmd"][i] = opm - ly[5]; Fk["d_opm"][i] = float(opm > ly[5])
    # 法人、融資、借券、注意、處置（日曆）
    for L in LB:
        for k_ in ("fnet", "tnet", "mchg", "sbl", "att", "disp"):
            Fk[f"{k_}_{L}"] = np.full(m, np.nan)
    for k_ in ("musage", "f_mstop", "tstreak", "d_tstreak"):
        Fk[k_] = np.full(m, np.nan)
    p_ = os.path.join(MAIN, "stocks_inst", sid + ".csv")
    if os.path.exists(p_):
        it = pd.read_csv(p_, dtype={"date": str}, usecols=["date", "foreign", "trust"]).drop_duplicates("date", keep="last")
        it.index = pd.to_datetime(it["date"]); first = int(cal.searchsorted(it.index.min()))
        fo = pd.to_numeric(it["foreign"], errors="coerce").reindex(cal).fillna(0.0).to_numpy()
        tr = pd.to_numeric(it["trust"], errors="coerce").reindex(cal).fillna(0.0).to_numpy()
        for L in LB:
            okd = pos_d - L + 1 >= first
            Fk[f"fnet_{L}"] = np.where(okd, pd.Series(fo).rolling(L).sum().to_numpy()[pos_d] / sh, np.nan)
            Fk[f"tnet_{L}"] = np.where(okd, pd.Series(tr).rolling(L).sum().to_numpy()[pos_d] / sh, np.nan)
        ts_ = SF.run_len(tr > 0)[pos_d]
        Fk["tstreak"] = np.where(pos_d >= first, ts_, np.nan).astype(float)
        Fk["d_tstreak"] = np.where(pos_d >= first, np.where(ts_ == 0, 0, np.where(ts_ <= 2, 1, np.where(ts_ <= 5, 2, 3))), np.nan).astype(float)
    p_ = os.path.join(MAIN, "stocks_margin", sid + ".csv")
    if os.path.exists(p_):
        mg = pd.read_csv(p_, dtype={"date": str}, usecols=["date", "m_balance", "m_limit", "note"]).drop_duplicates("date", keep="last")
        mg.index = pd.to_datetime(mg["date"]); first = int(cal.searchsorted(mg.index.min()))
        mb = pd.to_numeric(mg["m_balance"], errors="coerce").reindex(cal).ffill().to_numpy()
        ml = pd.to_numeric(mg["m_limit"], errors="coerce").reindex(cal).ffill().to_numpy()
        nt = mg["note"].reindex(cal).fillna("").astype(str).to_numpy()
        has = mg["m_balance"].reindex(cal).notna().to_numpy()
        for L in LB:
            ok_ = has[pos_d] & (pos_d - L >= first)
            Fk[f"mchg_{L}"] = np.where(ok_, (mb[pos_d] - mb[np.maximum(pos_d - L, 0)]) * 1000 / sh, np.nan)
        Fk["musage"] = np.where(has[pos_d] & (ml[pos_d] > 0), mb[pos_d] / np.where(ml[pos_d] > 0, ml[pos_d], 1), np.nan)
        Fk["f_mstop"] = np.where(has[pos_d], np.array(["O" in x for x in nt[pos_d]], float), np.nan)
    sb = W["SBL"]["S"].get(sid); f0 = W["SBL"]["first"]
    ser = np.full(n, np.nan)
    if sb:
        ks = np.fromiter(sb.keys(), int); ser[ks] = np.fromiter(sb.values(), float)
    ser = np.where(np.arange(n) >= f0, np.nan_to_num(ser, nan=0.0), np.nan)
    for L in LB:
        Fk[f"sbl_{L}"] = np.where(pos_d - L >= f0, (ser[pos_d] - ser[np.maximum(pos_d - L, 0)]) / sh, np.nan)
    af = W["ATT_FIRST"]
    ad = W["ATT"].get(sid, np.zeros(0, int))
    dday = np.zeros(n, bool)
    for a_, b_ in W["DISP"].get(sid, []):
        dday[max(a_, 0):min(b_, n - 1) + 1] = True
    cdd = np.r_[0, np.cumsum(dday)]
    for L in LB:
        cnt = np.searchsorted(ad, pos_d, side="right") - np.searchsorted(ad, pos_d - L + 1, side="left")
        okA = pos_d - L + 1 >= af
        Fk[f"att_{L}"] = np.where(okA, cnt, np.nan).astype(float)
        Fk[f"disp_{L}"] = np.where(okA, cdd[pos_d + 1] - cdd[np.maximum(pos_d - L + 1, 0)], np.nan).astype(float)
    cnt60 = np.searchsorted(ad, pos_d, side="right") - np.searchsorted(ad, pos_d - 59, side="left")
    ok60 = pos_d - 59 >= af
    Fk["d_att60"] = np.where(ok60, np.where(cnt60 == 0, 0, np.where(cnt60 <= 2, 1, 2)), np.nan).astype(float)
    Fk["d_disp60"] = np.where(ok60, (cdd[pos_d + 1] - cdd[np.maximum(pos_d - 59, 0)] > 0).astype(float), np.nan)
    # 大盤（時序五等分；S10）
    for L in LB:
        Fk[f"mkt_{L}"] = W["MKTQ"][L][pos_d]
    Fk["d_mkt200"] = W["MKT200"][pos_d]
    # 原門檻（描述；seq4 同式）
    amt20p = _prev(_roll(amt, 20, "mean")); amt20 = _roll(amt, 20, "mean")
    Fk["d_bull"] = np.where(np.isfinite(ma[100]), ((ma[5] > ma[20]) & (ma[20] > ma[60]) & (ma[60] > ma[100])).astype(float), np.nan)
    Fk["d_ma100"] = np.where(np.isfinite(ma[100]), (c > ma[100]).astype(float), np.nan)
    Fk["d_px"] = np.where(np.isfinite(rc), np.where(rc < 20, 0, np.where(rc < 50, 1, np.where(rc < 100, 2, 3))), np.nan).astype(float)
    lu20 = _roll(up.astype(float), 20, "sum"); Fk["d_lu20"] = np.minimum(lu20, 3)
    Fk["d_K1"] = np.where(np.isfinite(K), (Kr >= 3).astype(float), np.nan)
    Fk["d_K1l"] = np.where(np.isfinite(K), np.where(Kr == 0, 0, np.where(Kr <= 2, 1, np.where(Kr <= 5, 2, 3))), np.nan).astype(float)
    Fk["d_K2"] = np.where(np.isfinite(amt20p) & np.isfinite(bu), ((c > bu) & (amt >= 2 * amt20p)).astype(float), np.nan)
    Fk["d_K3a"] = np.where(np.isfinite(R14), (R14 > 50).astype(float), np.nan)
    Fk["d_K3b"] = np.r_[np.nan, np.where(np.isfinite(R6[1:]) & np.isfinite(R12[:-1]), ((R6[:-1] <= R12[:-1]) & (R6[1:] > R12[1:])).astype(float), np.nan)]
    tang20 = np.full(m, np.nan)
    for i in range(40, m):
        blk = mas[:, i - 20:i]
        tang20[i] = blk.max() / blk.min() - 1 if np.isfinite(blk).all() else np.nan
    Fk["d_K4"] = np.where(np.isfinite(tang20) & np.isfinite(ma[100]) & np.isfinite(amt20p),
                          ((tang20 <= 0.02) & (c / o - 1 >= 0.04) & (c > ma[20]) & (c > ma[100]) & (amt >= 2 * amt20p)).astype(float), np.nan)
    Fk["d_K5a"] = np.where(np.isfinite(turn), (turn >= 0.10).astype(float), np.nan); Fk["d_K5b"] = np.where(np.isfinite(turn), (turn >= 0.20).astype(float), np.nan)
    mx60p, mn60p = _prev(_roll(c, 60, "max")), _prev(_roll(c, 60, "min"))
    a120p = _prev(_roll(amt, 120, "mean"))
    Fk["d_V1"] = np.where(np.isfinite(mx60p) & np.isfinite(a120p) & np.isfinite(amt20p),
                          ((mx60p / mn60p - 1 <= 0.25) & (_prev(amt20) <= 0.7 * a120p) & (c > mx60p) & (amt >= 2 * amt20p)).astype(float), np.nan)
    Fk["d_V2l"] = np.where(np.isfinite(ma[20]), np.where(v2 == 0, 0, np.where(v2 <= 4, 1, np.where(v2 <= 9, 2, 3))), np.nan).astype(float)
    Fk["d_V3"] = np.where(np.isfinite(bu), v3.astype(float), np.nan)
    brk = c > _prev(_roll(c, 20, "max"))
    nxt10 = np.full(m, np.nan)
    if m > 11:
        cs = np.r_[0, np.cumsum(np.nan_to_num(amt))]
        j = np.arange(m - 10); nxt10[j] = (cs[j + 11] - cs[j + 1]) / 10
    okb = (brk & (nxt10 <= 0.4 * amt)).astype(float)
    x2 = np.zeros(m)
    for i in range(m):
        a_, b_ = i - 59, i - 10
        if b_ >= max(a_, 0):
            x2[i] = okb[max(a_, 0):b_ + 1].max()
    Fk["d_X2"] = np.where(np.arange(m) >= 80, x2, np.nan)
    e3 = [e5, e10, e20]
    Fk["d_X3"] = np.where(np.isfinite(x3), ((x3 <= 0.02) & np.all([e_ > _prev(e_, 3) for e_ in e3], axis=0)).astype(float), np.nan)
    a120pre = _prev(_roll(amt, 120, "mean"), 20)                                   # 20 日窗之前的 120 日均額
    Fk["d_shrink"] = np.where(np.isfinite(a120pre) & np.isfinite(amt20), (amt20 <= 0.7 * a120pre).astype(float), np.nan)
    span["d_shrink"] = 141
    # 回看窗內有壞根 ⇒ NaN（S3）
    for k_, sp in span.items():
        if k_ in Fk:
            kk = np.arange(m); nb_ = cbk[kk + 1] - cbk[np.maximum(kk + 1 - sp, 0)]
            Fk[k_] = np.where(nb_ > 0, np.nan, Fk[k_])
    Fout = np.full((NFW, n), np.nan, np.float32)
    for k_, v_ in Fk.items():
        Fout[FIX[k_], idx] = np.asarray(v_, float)
    # ── 標籤：定義域、網格事件（S4～S7）
    hdef = np.zeros(n, np.int16)
    pp = idx
    hd = np.minimum.reduce([np.full(m, 250), n - 1 - pp, nxt[np.minimum(pp + 1, n)] - 1 - pp])
    hdef[pp] = np.maximum(hd, 0)
    ev = []
    cP = {}
    ends = {}
    for hi, H in enumerate(HS):
        rmx = pd.Series(cff[::-1]).rolling(H, min_periods=1).max().to_numpy()[::-1]     # rmx[p] ＝ max(cff[p..p+H−1])
        fm = np.r_[rmx[1:], np.nan]                                                      # (p, p+H]
        okH = hdef[pp] >= H
        MH = np.where(okH, fm[pp] / c - 1, np.nan)
        for gi, g in enumerate(GS):
            q = pp[np.flatnonzero(okH & (fm[pp] >= c * (1 + g) * (1 - 1e-9)))]
            if len(q) == 0:
                continue
            lastE = -10 ** 9; j = 0
            while j < len(q):
                t = int(q[j])
                if t - lastE > H:
                    seg = cff[t + 1:t + H + 1]; P = t + 1 + int(np.argmax(seg)); ct = cff[t]
                    dg = int(np.argmax(seg >= ct * (1 + g) * (1 - 1e-9))) + 1
                    ev.append((cell_of(hi, gi), t, float(MH[np.searchsorted(pp, t)]), P, dg))
                    lastE = t
                    j = int(np.searchsorted(q, t + H + 1))
                else:
                    j += 1
    # 事件屬性
    E = {k_: [] for k_ in ("cell", "d", "M", "P", "dg", "M250", "obs", "maxdd", "rec", *[f"dd{int(x * 100)}" for x in DD], "ps_g", "ps_d", "ps_open")}
    for cc, t, M, P, dg in ev:
        if P not in cP:
            endobs = min(last, int(nxt[P + 1]) - 1 if P + 1 <= n else n - 1, n - 1)
            aft = cff[P + 1:endobs + 1]; pk = cff[P]
            hits = []
            for x in DD:
                w_ = np.flatnonzero(aft <= pk * (1 - x)); hits.append(int(w_[0]) + 1 if len(w_) else -1)
            rw = np.flatnonzero(aft > pk)
            seg = cff[P:endobs + 1]; rmax = np.maximum.accumulate(seg); w_ = np.flatnonzero(seg / rmax - 1 <= -0.3)
            stop = int(w_[0]) if len(w_) else len(seg); ps = int(np.argmax(seg[:stop]))
            cP[P] = (endobs - P, float(aft.min() / pk - 1) if len(aft) else np.nan, int(rw[0]) + 1 if len(rw) else -1, hits, float(seg[ps]), P + ps, int(len(w_) == 0))
        if t not in ends:
            m250 = cff[t + 1:t + 1 + min(250, int(hdef[t]))]
            ends[t] = float(m250.max() / cff[t] - 1) if len(m250) else np.nan
        ob, mdd, rec, hits, psv, psp, pso = cP[P]; m250 = ends[t]
        psg, psd = psv / cff[t] - 1, psp - t
        E["cell"].append(cc); E["d"].append(t); E["M"].append(M); E["P"].append(P); E["dg"].append(dg); E["M250"].append(m250)
        E["obs"].append(ob); E["maxdd"].append(mdd); E["rec"].append(rec)
        for x, hv in zip(DD, hits):
            E[f"dd{int(x * 100)}"].append(hv)
        E["ps_g"].append(psg); E["ps_d"].append(psd); E["ps_open"].append(pso)
    E = {k_: np.asarray(v_, dtype=np.float32 if k_ in ("M", "M250", "maxdd", "ps_g") else np.int32) for k_, v_ in E.items()}
    E["s"] = np.full(len(ev), si, np.int32)
    # ── 報酬（S13）
    Rout = np.full((len(HOLD), n), np.nan, np.float32)
    bnext = np.zeros(n, bool); bnext[:-1] = buy_ok[1:]
    onext = np.r_[oA[1:], np.nan]
    for j, hh in enumerate(HOLD):
        okr = bar & bnext & (hdef >= hh)
        pr = np.flatnonzero(okr)
        Rout[j, pr] = cff[pr + hh] / onext[pr] - 1
    r20c = AV.r20_cal(cA, idx).astype(np.float32)
    dnow = dday & bar
    return si, {"F": Fout, "R": Rout, "bar": bar, "hdef": hdef, "buy_ok": buy_ok, "locked": locked, "disp": dday, "r20c": r20c, "E": E,
                "nbad": int(bad_k.sum()), "nbp": nbp}


def mm(name, dtype, shape, mode="r"):
    return np.lib.format.open_memmap(os.path.join(WORK, name + ".npy"), mode=mode, dtype=dtype, shape=shape if mode == "w+" else None)


def build(a, log):
    os.makedirs(WORK, exist_ok=True)
    info = stitch(log)
    W, uni = world(log, a.limit)
    cal = W["cal"]; n = len(cal); S = len(uni)
    uni.to_csv(os.path.join(WORK, "uni.csv"), index=False)
    FE = mm("F", np.float32, (len(FCOL), S, n), "w+"); RE = mm("R", np.float32, (len(HOLD), S, n), "w+")
    AUX = {k: mm(k, dt, (S, n), "w+") for k, dt in (("bar", bool), ("hdef", np.int16), ("buy_ok", bool), ("locked", bool), ("disp", bool), ("r20c", np.float32))}
    EV = []; nb = 0; nbp = 0; done = 0
    with Pool(a.procs, initializer=_init, initargs=(W,)) as pool:
        for r in pool.imap_unordered(stock, W["sids"], chunksize=4):
            done += 1
            if r is None:
                continue
            si, o = r
            FE[:, si, :] = o["F"]; RE[:, si, :] = o["R"]
            for k in AUX:
                AUX[k][si, :] = o[k]
            EV.append(o["E"]); nb += o["nbad"]; nbp += o["nbp"]
            if done % 200 == 0:
                log(f"[建表] {done}/{S}")
    FE.flush(); RE.flush()
    for k in AUX:
        AUX[k].flush()
    E = {k: np.concatenate([e[k] for e in EV]) for k in EV[0]}
    np.savez(os.path.join(WORK, "events.npz"), **E)
    json.dump({"接合": info, "檔": S, "日曆": [str(cal[0].date()), str(cal[-1].date()), n], "壞根": nb, "價格斷點": nbp, "事件列": int(len(E["d"])),
               "特徵欄": FCOL}, open(os.path.join(WORK, "build.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[建表] 完成｜{S} 檔｜事件列 {len(E['d']):,}｜壞根 {nb}（價格斷點 {nbp}）")


# ═════════════ 橫斷面 ═════════════
def qtie(v):
    """同值同組五等分（S10）：v 有限者 rank ＝ 嚴格小於的個數；q ＝ rank×5÷k＋1；NaN ⇒ 0。"""
    out = np.zeros(len(v), np.int8); ok = np.flatnonzero(np.isfinite(v)); k = len(ok)
    if k == 0:
        return out
    x = v[ok]; srt = np.sort(x)
    out[ok] = (np.searchsorted(srt, x, side="left") * 5 // k + 1).astype(np.int8)
    return out


def cross(a, log):
    uni = pd.read_csv(os.path.join(WORK, "uni.csv"), dtype=str)
    D.DATA = ST; cal = D.load_calendar(); n = len(cal); S = len(uni)
    FE = mm("F", np.float32, None, "r+"); bar = mm("bar", bool, None)
    Q = mm("Q", np.int8, (len(FCOL), S, n), "w+")
    # 產業排名（cross）、集保（cross）、X1（cross）先填 F
    ind = pd.read_csv(os.path.join(MAIN, "meta", "industry.csv"), dtype=str)
    imap = dict(zip(ind["stock_id"], ind["industry_code"]))
    icode = np.array([int(imap[s]) if str(imap.get(s, "")).isdigit() else -1 for s in uni["stock_id"]])
    B = np.asarray(bar)
    for L in LB:
        r = np.asarray(FE[FIX[f"r_{L}"]]); out = np.full((S, n), np.nan, np.float32)
        for t in range(n):
            ok = B[:, t] & np.isfinite(r[:, t]) & (icode >= 0)
            if ok.sum() < 10:
                continue
            s_ = pd.Series(r[ok, t]).groupby(icode[ok]).agg(["mean", "size"])
            s_ = s_[s_["size"] >= 3]
            if len(s_) < 5:
                continue
            rk = qtie(s_["mean"].to_numpy()).astype(float)
            mp = dict(zip(s_.index, rk))
            out[B[:, t], t] = [mp.get(z, np.nan) for z in icode[B[:, t]]]
        FE[FIX[f"indrk_{L}"]] = out
        log(f"[橫斷面] 產業 {L}")
    tv = tdcc_panels(uni, cal, log)
    for L in LB:
        FE[FIX[f"tdcc_{L}"]] = np.where(B, tv[L], np.nan).astype(np.float32)
    r60 = np.asarray(FE[FIX["r_60"]]); r20 = np.asarray(FE[FIX["r_20"]]); a20 = np.asarray(FE[FIX["amt_20"]])
    med = np.array([np.nanmedian(np.where(B[:, t], a20[:, t], np.nan)) if B[:, t].any() else np.nan for t in range(n)])
    X1 = np.where(np.isfinite(r60) & np.isfinite(r20) & np.isfinite(a20), ((r60 >= 0.10) & (r60 <= 0.30) & (r20 <= 0.03) & (a20 >= med[None, :])).astype(float), np.nan)
    FE[FIX["d_X1"]] = np.where(B, X1, np.nan).astype(np.float32)
    FE.flush()
    # 五等分
    for f in SPECS:
        col, kind = f[0], f[3]
        X = np.asarray(FE[FIX[col]])
        if kind in ("q", "x") and col != "d_X1" and not col.startswith("indrk_"):
            qq = np.zeros((n, S), np.int8); Xt = np.ascontiguousarray(X.T); Bt = np.ascontiguousarray(B.T)
            for t in range(n):
                b_ = Bt[t]
                if b_.any():
                    qq[t, b_] = qtie(Xt[t, b_])
            Q[FIX[col]] = qq.T
        elif col.startswith("indrk_") or kind == "qts":
            Q[FIX[col]] = np.where(np.isfinite(X) & B, X, 0).astype(np.int8)
        else:                                                                       # 二元／級距：值＋1（0 ＝ NaN）
            Q[FIX[col]] = np.where(np.isfinite(X) & B, X + 1, 0).astype(np.int8)
    Q.flush()
    log("[橫斷面] 五等分完成")


def tdcc_panels(uni, cal, log):
    """集保 400 張以上（tdcc.level_of）持股比例 w 週變化（w ＝ L÷5，至少 1）；觀察日用「資料日期 ＜ t」的最新一週；2019 起（裁定 seq274）。"""
    import ast
    n = len(cal); S = len(uni); out = {L: np.full((S, n), np.nan, np.float32) for L in LB}
    src = open(os.path.join(os.path.dirname(MAIN), "tdcc.py"), encoding="utf-8").read()
    fn = next(nd for nd in ast.parse(src).body if isinstance(nd, ast.FunctionDef) and nd.name == "level_of")
    ns = {}; exec(compile(ast.Module(body=[fn], type_ignores=[]), "tdcc.py:level_of", "exec"), ns)
    lv = pd.read_csv(os.path.join(MAIN, "meta", "tdcc_levels.csv"))
    rows = [(int(r.level), int(r.lower_lo), int(r.lower_hi), int(r.upper_lo), int(r.upper_hi)) for r in lv.itertuples()]
    lo, hi = ns["level_of"](rows, 400_001); assert lo == hi, (lo, hi)
    parts = []
    for f in sorted(glob.glob(os.path.join(MAIN, "tdcc_hist", "*.parquet"))):
        x = pd.read_parquet(f, columns=["date", "stock_id", "level", "pct"]); x["stock_id"] = x["stock_id"].astype(str); x["date"] = x["date"].astype(str)
        parts.append(x[x["level"].astype(int).between(lo, 15)])
    for f in sorted(glob.glob(os.path.join(MAIN, "tdcc", "*.csv"))):
        x = pd.read_csv(f, dtype={"stock_id": str, "date": str}, usecols=["date", "stock_id", "level", "pct"])
        parts.append(x[x["level"].astype(int).between(lo, 15)])
    A = pd.concat(parts); A["date"] = pd.to_datetime(A["date"])
    A = A.drop_duplicates(["date", "stock_id", "level"], keep="last").groupby(["stock_id", "date"])["pct"].sum().reset_index().sort_values(["stock_id", "date"])
    A = A[A["date"] >= pd.Timestamp("2019-01-01")]
    si = {s: i for i, s in enumerate(uni["stock_id"])}
    cd = cal.to_numpy()
    for s, g in A.groupby("stock_id"):
        if s not in si:
            continue
        ds = g["date"].to_numpy(); pc = g["pct"].to_numpy(float)
        j = np.searchsorted(ds, cd, side="left") - 1
        for L in LB:
            w = max(1, L // 5)
            ch = np.full(len(pc), np.nan); ch[w:] = pc[w:] - pc[:-w]
            v = np.where(j >= 0, ch[np.maximum(j, 0)], np.nan)
            out[L][si[s]] = v
    log(f"[集保] 400 張以上 ＝ 第 {lo} 級起（tdcc.level_of）；2019 起")
    return out


# ═════════════ 共用 ═════════════
def load_all():
    uni = pd.read_csv(os.path.join(WORK, "uni.csv"), dtype=str)
    D.DATA = ST; cal = D.load_calendar()
    mon = np.array([d.year * 12 + d.month - 1 for d in cal])
    segd = {}
    for k, (x, y) in SEG.items():
        a_, b_ = pd.Period(x), pd.Period(y)
        segd[k] = (mon >= a_.year * 12 + a_.month - 1) & (mon <= b_.year * 12 + b_.month - 1)
    E = dict(np.load(os.path.join(WORK, "events.npz")))
    return uni, cal, mon, segd, E


def cr0_ratio(e_m, n_m):
    """曆月分群：p ＝ Σe÷Σn；se ＝ √Σ(e_m − p·n_m)² ÷ Σn。"""
    N = n_m.sum(-1)
    with np.errstate(invalid="ignore", divide="ignore"):
        p = e_m.sum(-1) / N
        se = np.sqrt(((e_m - p[..., None] * n_m) ** 2).sum(-1)) / N
    return p, se


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=("build", "cross", "desc", "feat", "endtrade"), required=True)
    ap.add_argument("--procs", type=int, default=2); ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, f"run_{a.stage}.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    log(f"===== researchSurge5 {a.stage}｜分析開始 {START}｜{SEQ}｜g 網格照裁定 seq277｜執行者未看過 seq4 結果 =====")
    if a.stage == "build":
        build(a, log)
    elif a.stage == "cross":
        cross(a, log)
    elif a.stage == "desc":
        from backtest import researchSurge5_desc as DS
        DS.run(log)
    elif a.stage == "feat":
        from backtest import researchSurge5_feat as FT
        FT.run(log)
    else:
        from backtest import researchSurge5_feat as FT
        FT.run_endtrade(log)
    log(f"[完] {time.time() - T0:.0f}s")


if __name__ == "__main__":
    main()
