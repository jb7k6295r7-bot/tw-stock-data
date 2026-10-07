# -*- coding: utf-8 -*-
"""USREG-A3 計算分工 g4（四件：A3-3 N字底／N型、A3-10 爆量突破＋跌破 EMA、A3-11 外部長線三件、A3-12 動能改良四件）——回測線計算子代理 g4。

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSA3_g4 --run   [--item A3-10] [--procs 2] [--limit 60]
    ...                                                                                    --check [--item A3-10] [--limit 60]

判準：美股策略線 登錄 USREG-A3A4 seq1（sha 0dc16d3267725d7c）＋seq2（sha bc0927fed5996fd4）；裁定 seq318（發號、四件主臂改條件出場）、
      seq319（Q1 早年段、Q4 A3-3 停損兩版當格軸 N 6、Q5 臺灣50 代理、Q14 季版附註）、seq316（只 S&P 400 與合併兩者都過才合格）。
開跑前清單（⛔ 照它、不改）：backtest/researchUSA34_prep.py（P1～P20）、resultsUSA34/prep/PREP_REPORT.md、清單_29件.csv。
共同讀法：backtest/researchUSA3_core.py C1～C10（照用；本檔只 import core、一行不改）。
台股原登錄（信箱）與原程式（只 import 偵測器、⛔ 未改）：
  A3-3  N字底與N型走法 seq1 sha 4df1f473b005da3c ｜ researchNpattern（ndb_candidates／ndb_scan／ndb_table／red_flags／nwave_scan／members／chains_dedup／cstat／dstat）
  A3-10 爆量突破進場與跌破EMA出場 seq2 sha 0c44c9e73bba2397 ｜ researchVolBreak（規則照它的 docstring 重寫成美股陣列）
  A3-11 外部長線戰法三件 seq2 sha 04f9758bb33bc345 ｜ researchLongT／researchLongD（box_machine）／researchLongI（ichimoku、wilder_atr、atr_exit）
  A3-12 動能改良版四件 seq1 sha f9b6932850aa4ea7 ｜ researchMomX（規則照它的 docstring R1～R9 重寫）

⛔⛔ 私有資料：resultsUSA34/A3/ 只放彙總；逐筆事件、訊號表、逐種子結果、累加器一律在 ~/us_work/a3/g4/（repo 外），彙總 json 列 sha。

═══ g4 補讀法（執行者寫死於 2026-10-07 12:15（台北）；寫死前 ⛔ 沒看任何 A3 報酬；只看過事件數、引擎耗時）═══
【共通】
 G1 判定段：四件台股原登錄都有早年段 ⇒ seq319 Q1：判定 ＝ 確認段（2022-01-03～2026-09-30）＋ 兩母體（合併、只 S&P 400 都過才合格）；
    原文另要「探索段也過」者（A3-3 兩問、A3-10 整套）改報描述「原文雙段版」（⛔ 不判）；挑格件（A3-11 T、A3-12）照「探索段挑、確認段判」；
    A3-11 件 I 照 P12 全窗判。結果句標「缺早年段」。
 G2 組合層（A3-10、A3-11、A3-12）照 C5：8 槽等權、抽籤種子 102000＋r、成本 0.05%、T＋1 開盤、tradable＋delist、^SP500TR 同段。台股原件引擎設定不同處（列入偏離）：
    ・A3-11 T、A3-12：N ∈ {10, 20} 讀成「符合」名單長度（換股日依分數取前 N ＝ 符合；仍在名單 ＝ 續抱；落選 ⇒ 下一個同頻率換股日開盤賣）；
      名單新進者多於空槽 ⇒ 引擎抽籤（台股：換股簿名單全買、等權 1/N、依名次）。
    ・A3-11 D：N ∈ {10, 20} 是持股上限 ⇒ 8 槽下兩格相同 ⇒ 只剩 1 格（N 仍計 1；不挑格）；RS 高者先 ⇒ 抽籤。
    ・A3-11 I：最多 20 檔 ⇒ 8 槽；轉換÷基準大者先 ⇒ 抽籤。A3-10：最多 10 檔 ⇒ 8 槽；各段獨立起跑、段首全現金（照台股原程式）。
 G3 不再符合才換的訊號表（W1b 同式）：換股日 e ＝ 當月第一個交易日（＝ prep MSTART）；條件只用 e−1 收盤以前的資料、名單成員以 e 當天在該欄指數為準；
    名單內每檔一列：e 開盤進、出場 ＝ 之後第一個「不在名單」的同頻率換股日開盤（開盤無效改收盤）；一直在名單 ⇒ 窗尾收盤結算；已持有 ⇒ 引擎不重買。
 G4 三欄 ＝ 三組各自的組合：A3-11 T、A3-12 的排名（RS 前 30%、R(F) 名次、剔極端 3%、前 30%）都在該欄母體內排。
 G5 斷點：組合層訊號列的特徵回看窗或持有期跨轉接層 hard_break ⇒ 剔除（W1b W5；回看 A3-10 ＝ max(B, 20) 根、T ＝ 252 根、A3-12 ＝ 形成期＋2 個月）；
    A3-11 D、I 照台股原程式「持有中碰到壞根 ⇒ 壞根前一根收盤出」。A3-3 單筆層見 A4。
 G6 |ret|＞50% 敏感度（C8）：S&P 400 未確認 23 列落在特徵窗或持有期 ⇒ 剔除該列／事件後重判（合併、只 400）；基準、同十分位對照不動。
 G7 種子（判定用 200 顆；描述臂顆數因耗時減少、⛔ 不影響判定）：
    A3-10 確認段合併、只 400 各 200｜探索段合併、只 400 各 50｜只 500 確認段 50｜S 臂（確認、探索；合併）50｜ret50（確認；合併、只 400）20｜
          成本 0.02%、0.10%（確認；合併）10｜固定 20／60／120／240（確認；合併）10｜隨機出場假訊號（確認；合併）每格 30 次
    A3-11、A3-12 挑格與判定格 合併、只 400 各 200｜只 500 50｜非判定格描述 50｜固定天數 20｜成本 20｜ret50 50｜假訊號 100 次
    出場敏感度（seq242 合格／另列者）＝ 固定 20／60／120／240 描述臂（不另加）。
 G8 退化（事前排除，A3-11 T、A3-12）：探索段（自 G9 起點）平均持股 ＜ 4（8 槽的一半）或現金比例 ＞ 30%（逐種子中位）⇒ 不參與挑格；M4 用其底層 M0 判。
    A3-10 退化只標（探索段合併 平均持有 ＜ 2 日，仍計分母）。
 G9 探索段起點：資料面板 2015-12 起，回看長的條件（樣板 271 根、R(12)、M3 24 個月）前段依構造空倉 ⇒ 挑格件的探索段起點 ＝
    該件所有格在合併欄都有名單之後的第一個季換股日（1／4／7／10 月；只看名單、⛔ 不看報酬）；確認段不動。A3-10、件 D、件 I 照 C1 窗。
 G10 假訊號臂（各台股原登錄 K4；描述；p ＝ 假年化 ≥ 本格年化中位 的比例）：A3-10 隨機出場（持有天數從本格確認段合併欄訊號表的持有天數池放回抽）；
    T、A3-12 同池隨機（每個換股日從該欄排名母體不放回抽與真名單同數；M4 照同一套縮放）；D 同股隨機週進場、同持有根數、收盤出；
    I 同曆月、同母體（當月市值前 50）隨機一檔隨機一日、隔日開盤進、同 ATR 出場。引擎種子 102000＋i、抽樣 default_rng([20261007, 件序, …, i])。
 G11（資料修正，2026-10-07 14:45（台北）補；⚠ 寫在第一次 A3-11 全量之後，照實記）：回測線協調訊息（A4 子代理發現、回測線驗證）——prep 的 rc（raw_close_aligned）
    在 yahoo 來源實為「日後拆股調整」收盤 ⇒ 市值低估；件 I 甲的「S&P 500 市值前 50」改用 mcap × Π(拆股比 a/b，拆股日 ＞ 收盤日)（events_yahoo type＝split），
    tiingo 來源不改；A3-11 全部重跑（T、D 不用市值、結果不變）。其餘三件不用市值或原始價。
【A3-3】
 N1 單筆層（事件研究）照原文；主臂 ＝ 作者停損或目標價先到先出（收盤判、次一有效 K 棒開盤出；開盤無效改收盤）、⛔ 無時間上限、窗尾 2026-09-30 收盤結算；
    資料結束（下市）⇒ 最後一根收盤。停損兩版（ver0 回測低點、ver1 前低）當格軸（seq319 Q4）；N型 停損 ＝ 長紅最低點、無目標價。
 N2 偵測照台股原程式（只 import）；量 ＝ Yahoo 拆股調整量；掃描起點 ＝ prep（窗首前 120 日、第 40 根起）；型態窗內有壞根 ⇒ 實例不定義（壞根 ＝ 該根轉接層 hard_break 或與前一根間有缺 K 棒的交易日；ndb_table 原式）。
 N3 事件：訊號日 t ∈ [窗首, 窗尾−1]、t 在母體且有效、t＋1 是有效 K 棒且開盤有效（＝ prep）；事件欄 ＝ t 當天歸屬；事件段 ＝ t 的曆月。
 N4 持有路徑碰到壞根 ⇒ 壞根前一根收盤結算（台股原文「該 H 不定義」；主臂沒有 H ⇒ 改此讀法，件數照報）。
 N5 基準②：同日 t、合併母體中「t 有效、t＋1 開盤有效、(t, t＋5] 無轉接層硬斷點、r20 可算（收盤日曆 20 日報酬）」者依 r20 分十分位（researchVolBreak 同式）；
    同十分位其他股票「t＋1 開盤買、在事件的出場日以同一價別（開盤；無效改前收｜收盤）賣」報酬平均；(t＋1, 出場日] 內有硬斷點者不收（MB.ew_us 同式）。
    X2 ＝ R − 該平均；判定扣成本 0.05%（基準不付）；事件本身不在十分位母體 ⇒ X2 不定義。
 N6 去重（台股 R13 照用）：同一檔、同一格（臂 × 形狀 × 量能 × 停損版本），訊號日晚於上一筆出場才算新事件；同格同訊號日多個 L 實例（長紅）取最晚。
 N7 判（台股 R15、判定段 G1）：「站得住」＝ 確認段可判格（事件 ≥ 30）中 X2 月分群 95% CI 下緣 − 0.05% ＞ 0 的格嚴格過半；
    「量能有加分」＝ M − S（同形狀、同停損版本）差的 CI 下緣 ＞ 0 的格過半（兩臂都 ≥ 30）；N 6 ＝（甲1、甲2、N型）× 兩問，各自照 C4 給標籤；
    合併可判格 0 ⇒ 不可判定；只 400 可判格 0 ⇒ 依構造最多事後擴母體。
 N8 描述：原文時間出口 H{5,10,20,60}（停損／目標先到或 t＋H 收盤；基準 ＝ 同十分位固定持有 H；路徑內有壞根 ⇒ 該 H 不定義）只在合併欄報兩問；
    探索段、原文雙段版、Bonferroni（N＝6）、只 500。放棄組 A、「目標價碰到 vs 隨機同距離」⛔ 未做（描述臂、不影響判定）⇒ 改報主臂出場方式比例。
【A3-10】
 V1 規則照 researchVolBreak：突破 ＝ 收盤 ＞ 前 B 根有效 K 棒最高價最大值（不含當根）且 收盤 ＞ 開盤（還原，同日係數相同）；爆量 ＝ 量 ＞ k × 前 20 根均量（均量 ＞ 0）；
    EMA(L) ＝ ewm(span＝L, adjust＝False)；暖機 ＝ 有效 K 棒序號 ≥ 3L；訊號日自己收盤 ＜ EMA ⇒ 不進；候選 ＝ 訊號日在該欄指數；進場 e ＝ t＋1 ∈ 段內、開盤有效。
    出場 ＝ 進場日起第一個收盤 ＜ EMA(L) 的 d ⇒ d＋1 開盤；d＋1 超過段尾 ⇒ 段尾收盤結算。同檔可再進（引擎已持有不重買）。
 V2 整套判：確認段每欄 ≥ 31／60 格合格 ⇒ 該欄合格；≥ 31 格「合格或另列」⇒ 另列；否則不合格；兩欄照 C4（core.label_pf）。
 V3 描述：S 臂（拿掉爆量，B × L ＝ 20 格）M − S 年化差；EMA 出場 − 固定 20／60／120／240 年化差；按 B／k／L 分組合格格數；探索段合格格數；原文雙段版。
【A3-11】
 T1 件 T 用 prep 每月快照（~/us_work/a34/month.pkl；tmpl17 ＝ ①～⑦、rs ＝ 2r63＋r126＋r189＋r252、rev_hi8 ＝ P6 季營收創 8 季新高；kb ＝ e−1 以前最後一根）；
    ⑧ ＝ 該欄 rs 可算者依 rs 名次 ≤ ⌈0.3n⌉（同值依代號）；名單 ＝ 樣板內（乙另要 rev_hi8）依 rs 前 N（同值依代號）；頻率 月／季（1、4、7、10 月）。
 T2 挑格：探索段（G9）合併欄去退化，先合格、再比值（同分：年化高、甲先、月先、N 小）；判：確認段兩欄。溫斯坦描述臂、與營量重疊率 ⛔ 未做（美股無營量 v1）。
 D1 件 D 週 K ＝ researchWeekly.weekly_bars；箱型 ＝ researchLongD.box_machine（52 週；壞根週與前後 1 週不產生買訊，同 prep）；
    買 ＝ 突破週的下一個日曆週第一根有效 K 棒開盤（該週無 K 棒或開盤無效 ⇒ 放棄）；賣 ＝ 週收 ＜ 箱底那週之後第一根有效 K 棒開盤；
    候選 ＝ 突破週最後一根在該欄指數；日線版描述臂 ⛔ 未做。
 I1 件 I 訊號與出場照 researchLongI（ichimoku、wilder_atr、atr_exit；第 77 根起、條件由不成立轉成立、壞根與前後 1 根不產生訊號、下一個交易日為有效 K 棒且開盤有效）；
    甲 ＝ 訊號日所在月 S&P 500 成分中市值前 50（prep 快照 mcap ＝ P8；代理，seq319 Q5）；乙 ＝ 該欄全體。
 I2 判定格 ＝ 甲 × k3、全窗（P12）；甲只含 S&P 500 ⇒ 合併 ＝ 只 500，只 400 欄依構造無股 ⇒ 標籤最多「事後擴母體」；其餘 3 格描述。
【A3-12】
 M1 R(F) ＝ 月底收盤(m−2) ÷ 月底收盤(m−2−F) − 1（m ＝ 換股日所在月；ffill 還原收盤；兩端 ＞ 0）；排名母體 ＝ e 在該欄指數 ∩ e 前 5 日內有 K 棒 ∩ R(F) 可算；同值依代號。
    M1 剔 ⌊0.03n⌋ 高與低；M2 上一個同頻率換股日前 30%（⌈0.3n⌉）∩ 本期前 30%；M3 對 ^SP500TR 月報酬 OLS（m−37～m−2 的月報酬，≥ 24 個月，含截距；
    殘差標準差 ddof＝1；分數 ＝ 最近 F 個月殘差和 ÷ 殘差標準差）。
 M2 M4 ＝ M0 同格引擎權益的覆蓋層：每個換股日把股票部位調到 w × 權益（w ＝ min(1, 20% ÷ M0 名單 [e−60, e−1] 等權日報酬標準差 × √252)；不可算 ⇒ 1），
    調整金額 × 0.05%；兩次換股間部位隨 M0 權益漂移、其餘現金 0 息（台股 R6 覆蓋層同式）。
 M3 挑：每件探索段（G9）合併欄 12 格去退化：過判準者取比值最高，都沒過取比值最高（同分：年化高、F 小、月先、N 小）；判：確認段兩欄；並列同格 M0。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pickle
import sys
import time
from collections import Counter
from multiprocessing import Pool, Process
from statistics import NormalDist

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
from backtest import researchUSA3_core as C
from backtest import researchNpattern as NP          # ⚠ import 時 chdir ~/tw-p17（無害）
from backtest import researchLongD as LD
from backtest import researchLongI as LI
from backtest import researchWeekly as RW

R11, W = C.R11, C.W
READ_TS = "2026-10-07 12:15（台北）"
WK = os.path.join(C.WORK, "g4")
COST = C.COST
Z95 = 1.959963984540054
ZB6 = NormalDist().inv_cdf(1 - 0.025 / 6)
MONTH_PKL = os.path.expanduser("~/us_work/a34/month.pkl")
TWREG = {
    "A3-3": ("登錄全文-N字底與N型走法_照作者原文含量能_登錄_台股策略線_seq1_sha4df1f473b005da3c-6376B-20261004-0200.md", "4df1f473b005da3c"),
    "A3-10": ("登錄全文-爆量突破進場與跌破EMA出場_Threads作者指標常見值網格_登錄_台股策略線_seq2_sha0c44c9e73bba2397-7319B-20261004-2120.md", "0c44c9e73bba2397"),
    "A3-11": ("登錄全文-外部長線戰法三件_趨勢樣板與週線達華斯與一目三役_登錄_台股策略線_seq2_sha04f9758bb33bc345-7448B-20260928-2353.md（封存）", "04f9758bb33bc345"),
    "A3-12": ("登錄全文-動能改良版四件_剔極端持續殘差波動縮放_登錄_台股策略線_seq1_shaf9b6932850aa4ea7-4366B-20260927-2052.md（封存）", "f9b6932850aa4ea7"),
}
NAME = {"A3-3": "N字底與 N型走法（照作者原文含量能）", "A3-10": "爆量突破進場、跌破 EMA 出場（網格 60 格，seq2）",
        "A3-11": "外部長線三件（趨勢樣板 T、週線達華斯 D、一目三役 I）", "A3-12": "動能改良版四件（剔極端、持續、殘差、波動縮放）"}
SEEDS = {"judge": 200, "desc": 50, "fixed": 20, "cost": 20, "ret50": 50, "fake": 100,
         "a10_exp": 50, "a10_500": 50, "a10_S": 50, "a10_ret50": 20, "a10_cost": 10, "a10_fixed": 10, "a10_fake": 30}
if os.environ.get("G4_SMOKE"):                         # 只給冒煙測試（程式能不能跑完）；正式交件不用
    SEEDS = {k: 2 for k in SEEDS}
COLS = C.COLS
G: dict = {}


def log(m):
    print("[%s] %s" % (time.strftime("%H:%M:%S", time.gmtime(time.time() + 8 * 3600)), m), flush=True)


# ═════════════ 共用：資料、段、基準 ═════════════
def setup(lim=None):
    if G.get("ok") and G.get("lim") == lim:
        return G
    meta, ST = C.load_cache(lim)
    cal = meta["cal"]; w0, w1, sp, c0 = meta["w0"], meta["w1"], meta["sp"], meta["c0"]
    sids = sorted(ST)
    C.pf_setup(ST, sids, cal, w0, w1)
    per = cal.to_period("M")
    ms = np.flatnonzero(np.r_[True, per[1:] != per[:-1]])
    mst = ms[(ms >= w0) & (ms <= w1)]
    ym = np.asarray(cal.year * 12 + cal.month)
    me = {}
    for i, m in enumerate(ym):
        me[int(m)] = i
    mon = np.array([(d.year - 2016) * 12 + d.month - 1 for d in cal])
    pbc = {s: np.cumsum(ST[s]["pb"]) for s in sids}
    f5c = {s: np.cumsum(ST[s]["f50"]) for s in sids}
    G.update(ok=True, lim=lim, meta=meta, ST=ST, cal=cal, n=len(cal), w0=w0, w1=w1, sp=sp, c0=c0, sids=sids, bench=C.bench_tr(cal),
             mst=mst, ym=ym, me=me, mon=mon, pbc=pbc, f5c=f5c, ym0=int(ym[mst[0]]))
    os.makedirs(WK, exist_ok=True)
    return G


def cnt(cs, a, b):
    """cs ＝ cumsum ⇒ [a, b] 內旗標數（a ≤ 0 ⇒ 從頭）。"""
    b = min(int(b), len(cs) - 1)
    if b < a:
        return 0
    return int(cs[b] - (cs[a - 1] if a > 0 else 0))


def cntv(cs, a, b):
    """cnt 的向量版：[a, b] 內旗標數。"""
    a = np.asarray(a, int); b = np.minimum(np.asarray(b, int), len(cs) - 1)
    lo = np.where(a > 0, cs[np.maximum(a - 1, 0)], 0)
    return np.where(b >= a, cs[b] - lo, 0)


_BR = {}


def bref(s0, s1):
    k = (int(s0), int(s1))
    if k not in _BR:
        _BR[k] = C.bench_row(G["cal"], s0, s1, arr=G["bench"])
    return _BR[k]


def colflag(d, col):
    return d["member"] if col == "合併" else (d["m4"] if col == "只400" else d["m5"])


def dstr(p):
    return str(G["cal"][int(p)].date())


# ═════════════ 組合引擎（設定 ＝ core C5／W1b；多段量測＋C6 必報＋M4 覆蓋層）═════════════
_A: dict = {}
_B: dict = {}
LAZY: dict = {}


def m4_overlay(eq, wmap, n):
    E = np.ones(n); S = 0.0; K = 1.0; ws = np.zeros(n)
    for t in range(1, n):
        w = wmap.get(t)
        if w is not None:
            tot = S + K; St = w * tot; cst = abs(St - S) * COST
            S = St; K = tot - St - cst
        if eq[t - 1] > 0:
            S *= eq[t] / eq[t - 1]
        E[t] = S + K; ws[t] = S / E[t] if E[t] > 0 else 0.0
    return E, ws


def _run1(job):
    key, seed = job
    a = _A[key]
    if "sig" not in a:
        a = dict(a); a["sig"], a["endh"], extra = LAZY[a["lazy"][0]](*a["lazy"][1:])
        a.update(extra)
    S_ = C._S
    R11.COST = a.get("cost", COST)
    aud = []
    try:
        out = R11.simulate_mtm(a["sig"], C.RULE, C.N_SLOTS, np.random.default_rng(seed), S_["closes"], S_["opens"], S_["ncal"],
                               return_equity=True, pick=None, d_max=None, queue_days=0, cash_mode="zero",
                               tradable=S_["trad"], delist=S_["dl"], audit=aud)
    finally:
        R11.COST = COST
    eq = np.asarray(out["equity"], float); hv = np.asarray(out["hold_val"], float); n = len(eq)
    r = {"key": key, "seed": seed, "trades": int(out["trades"]), "slot_use": float(out["slot_use"])}
    for nm, (s0, s1) in a["segs"].items():
        c_, m_ = W.window_metrics(eq, s0, s1); r["c_" + nm] = c_; r["m_" + nm] = m_
    endh = a["endh"]; cl = S_["closes"]; s1j = a["jseg"][1]
    buy = {}; hold = []; nend = 0; peak = []; dpos = np.zeros(n + 1)
    for x in aud:
        t = int(x["t"])
        if x["side"] == "buy":
            buy[x["sid"]] = t; dpos[t] += 1
        elif x["side"] == "sell" and x["sid"] in buy:
            b = buy.pop(x["sid"]); hold.append(t - b); dpos[t] -= 1
            if (x["sid"], b) in endh and t >= s1j:
                nend += 1
            seg = cl[x["sid"]][b:t + 1]
            pk = np.nanmax(seg) if len(seg) else np.nan
            if np.isfinite(pk) and pk > 0 and np.isfinite(x["px"]):
                peak.append(float(x["px"]) / pk - 1.0)
    hold = np.asarray(hold, float); peak = np.asarray(peak, float)
    r.update({"hold_mean": float(hold.mean()) if len(hold) else np.nan, "hold_med": float(np.median(hold)) if len(hold) else np.nan,
              "hold_p10": float(np.percentile(hold, 10)) if len(hold) else np.nan, "hold_p90": float(np.percentile(hold, 90)) if len(hold) else np.nan,
              "hold_max": float(hold.max()) if len(hold) else np.nan, "n_sells": int(len(hold)), "n_end_hold": int(nend + len(buy)),
              "peak_gap_med": float(np.median(peak)) if len(peak) else np.nan})
    if a.get("dseg"):
        s0, s1 = a["dseg"]; npos = np.cumsum(dpos)[:n]
        r["avg_pos"] = float(npos[s0:s1 + 1].mean())
        r["cash"] = float(np.mean(1.0 - hv[s0:s1 + 1] / eq[s0:s1 + 1]))
    if a.get("m4w") is not None:
        e4, ws = m4_overlay(eq, a["m4w"], n)
        for nm, (s0, s1) in a["segs"].items():
            c_, m_ = W.window_metrics(e4, s0, s1); r["c4_" + nm] = c_; r["m4_" + nm] = m_
        s0, s1 = a["jseg"]; r["w4"] = float(ws[s0:s1 + 1].mean())
    return r


def run_arms(arms, procs):
    _A.clear(); _A.update(arms)
    jobs = [(k, s) for k, a in arms.items() for s in a["seeds"]]
    out = {k: [] for k in arms}
    t0 = time.time()
    if procs <= 1 or len(jobs) < 8:
        for j in jobs:
            x = _run1(j); out[x["key"]].append(x)
    else:
        with Pool(procs) as pool:
            for x in pool.imap_unordered(_run1, jobs, chunksize=2):
                out[x["key"]].append(x)
    for k in out:
        out[k].sort(key=lambda x: x["seed"])
    _A.clear()
    log("  引擎 %d 臂 %d 次 %.0fs" % (len(arms), len(jobs), time.time() - t0))
    return out


def seeds(k):
    return [C.SEED0 + r for r in range(k)]


def sig_of(sid, e, x, g, eh):
    sid = np.asarray(sid); e = np.asarray(e, int); x = np.asarray(x, int); g = np.asarray(g, float); eh = np.asarray(eh, bool)
    ok = np.isfinite(g)
    sid, e, x, g, eh = sid[ok], e[ok], x[ok], g[ok], eh[ok]
    d = pd.DataFrame({"sid": sid, "entry_pos": e, f"xpos_{C.RULE}": x, f"g_{C.RULE}": g})
    d = d.sort_values(["entry_pos", "sid"], kind="mergesort").reset_index(drop=True)
    endh = set(zip(sid[eh].tolist(), e[eh].tolist()))
    return d, endh


def agg(rows, seg, br, m4=False):
    if not rows:
        return {"標籤": "不可判定", "註": "無訊號"}
    pc, pm = ("c4_", "m4_") if m4 else ("c_", "m_")
    rr = [dict(x, cagr=x[pc + seg], mdd=x[pm + seg]) for x in rows]
    a = C.pf_agg(rr, br)
    for k, nm in (("avg_pos", "平均持股（逐種子中位）"), ("cash", "現金比例（逐種子中位）"), ("w4", "M4 平均股票部位（逐種子中位）")):
        v = [x[k] for x in rows if k in x and np.isfinite(x[k])]
        if v:
            a[nm] = float(np.median(v))
    return a


def slim(a):
    """彙總 dict ⇒ 給 json 的精簡版。"""
    keep = ("年化中位", "回落中位", "比值", "基準年化", "基準回落", "基準比值", "標籤", "年化p10", "年化p90", "逐種子標籤比例", "交易數中位", "槽位使用率中位",
            "持有天數_平均（逐種子中位）", "持有天數_中位（逐種子中位）", "持有天數_p10", "持有天數_p90", "最長持有（200 顆最大）",
            "窗尾仍持有件數（逐種子中位）", "窗尾仍持有件數（範圍）", "離頂距離中位（出場價÷持有期最高收盤−1）", "種子數",
            "平均持股（逐種子中位）", "現金比例（逐種子中位）", "M4 平均股票部位（逐種子中位）", "註")
    return {k: (round(v, 6) if isinstance(v, float) else v) for k, v in a.items() if k in keep}


def c6(a):
    if not a or "持有天數_平均（逐種子中位）" not in a:
        return None
    return {"持有天數平均": a["持有天數_平均（逐種子中位）"], "持有天數中位": a["持有天數_中位（逐種子中位）"], "p10": a["持有天數_p10"], "p90": a["持有天數_p90"],
            "最長": a["最長持有（200 顆最大）"], "窗尾仍持有件數（逐種子中位）": a["窗尾仍持有件數（逐種子中位）"], "窗尾仍持有件數範圍": a["窗尾仍持有件數（範圍）"],
            "離頂距離中位": a["離頂距離中位（出場價÷持有期最高收盤−1）"], "口徑": "引擎逐筆成交配對（逐種子量再取中位）"}


def save_seeds(res, name):
    rows = []
    for k, L in res.items():
        for x in L:
            rows.append({"key": "|".join(map(str, k)) if isinstance(k, tuple) else str(k), **{q: v for q, v in x.items() if q != "key"}})
    p = os.path.join(WK, name)
    pd.DataFrame(rows).to_csv(p, index=False, compression="gzip")
    return p


def pct(x):
    return "—" if x is None or not np.isfinite(x) else "%+.2f%%" % (100 * x)


def fixed_arrays(sid, e, s1, H):
    ST = G["ST"]
    x = np.minimum(e + H - 1, s1); eh = (e + H - 1) > s1
    g = np.array([ST[s]["closes"][xx] / ST[s]["opens"][ee] - 1.0 for s, ee, xx in zip(sid, e, x)])
    return x, g, eh


def pb_hold(sid, a, x, f50=False):
    cs = G["f5c"] if f50 else G["pbc"]
    return np.array([cnt(cs[s], aa, xx) > 0 for s, aa, xx in zip(sid, a, x)], bool)


def gross_at(sid, e, x, eh):
    ST = G["ST"]; out = np.empty(len(sid))
    for i, (s, ee, xx, h) in enumerate(zip(sid, e, x, eh)):
        d = ST[s]; o = d["opens"][ee]
        if h:
            out[i] = d["closes"][xx] / o - 1.0
        else:
            ox = d["opens"][xx]
            out[i] = (ox if (np.isfinite(ox) and ox > 0) else d["closes"][xx]) / o - 1.0
    return out


def lazy_fixed(bkey, H, s1):
    R = _B[bkey]
    x, g, eh = fixed_arrays(R["sid"], R["e"], s1, H)
    bad = pb_hold(R["sid"], R["a"], x)
    sig, endh = sig_of(R["sid"][~bad], R["e"][~bad], x[~bad], g[~bad], eh[~bad])
    return sig, endh, {"m4w": R.get("m4w")} if R.get("m4w") is not None else {}


LAZY["fixed"] = lazy_fixed


# ═════════════ A3-10 爆量突破＋跌破 EMA ═════════════
BS10, KS10, LS10 = (5, 10, 20, 60, 120), (1.5, 2.0, 3.0), (5, 10, 20, 60)


def a10_rows():
    """→ {(B, k 或 None, L, 段): dict 陣列}；k None ＝ S 臂（不看量）。"""
    g = G; ST = g["ST"]
    segs = {"探索": (g["w0"], g["sp"]), "確認": (g["c0"], g["w1"])}
    acc = {}
    drop = Counter()
    for sid in g["sids"]:
        d = ST[sid]; b = d["bars"]; nb = len(b)
        if nb < 25:
            continue
        cb, hb, ob, vb = d["C"][b], d["H"][b], d["O"][b], d["V"][b]
        red = cb > ob
        va = pd.Series(vb).rolling(20, min_periods=20).mean().shift(1).to_numpy()
        opens, closes, mem, m4, m5 = d["opens"], d["closes"], d["member"], d["m4"], d["m5"]
        pbc, f5c = g["pbc"][sid], g["f5c"][sid]
        ar = np.arange(nb)
        EM = {}
        for L in LS10:
            ema = pd.Series(cb).ewm(span=L, adjust=False).mean().to_numpy()
            bel = cb < ema
            EM[L] = (bel, b[bel])
        for B in BS10:
            hh = pd.Series(hb).rolling(B, min_periods=B).max().shift(1).to_numpy()
            with np.errstate(invalid="ignore"):
                brk = (cb > hh) & red & np.isfinite(hh)
            lbk = max(B, 20)
            for k in (None,) + KS10:
                with np.errstate(invalid="ignore"):
                    sg = brk if k is None else (brk & np.isfinite(va) & (va > 0) & (vb > k * va))
                for L in LS10:
                    bel, belc = EM[L]
                    ii = np.flatnonzero(sg & (ar >= 3 * L) & ~bel)
                    if not len(ii):
                        continue
                    t = b[ii]; e = t + 1
                    for sn, (s0, s1) in segs.items():
                        m = (e >= s0) & (e <= s1) & mem[t]
                        if not m.any():
                            continue
                        i2, t2, e2 = ii[m], t[m], e[m]
                        oe = opens[e2]; okb = np.isfinite(oe) & (oe > 0)
                        drop[("開盤不可用", sn, k is None)] += int((~okb).sum())
                        i2, t2, e2 = i2[okb], t2[okb], e2[okb]
                        if not len(i2):
                            continue
                        j = np.searchsorted(belc, e2)
                        dX = np.where(j < len(belc), belc[np.minimum(j, max(len(belc) - 1, 0))] if len(belc) else 10 ** 9, 10 ** 9)
                        x = np.where(dX + 1 <= s1, dX + 1, s1); eh = ~(dX + 1 <= s1)
                        gg = gross_at(np.full(len(e2), sid), e2, x, eh)
                        a0 = b[np.maximum(i2 - lbk, 0)]
                        pbf = np.array([cnt(pbc, aa, xx) > 0 for aa, xx in zip(a0, x)], bool)
                        f5f = np.array([cnt(f5c, aa, xx) > 0 for aa, xx in zip(a0, x)], bool)
                        acc.setdefault((B, k, L, sn), []).append((np.full(len(e2), sid, dtype=object), t2, e2, x, gg, eh, m4[t2], m5[t2], pbf, f5f, a0))
    out = {}
    for key, parts in acc.items():
        cols = list(zip(*parts))
        R = {nm: np.concatenate(v) for nm, v in zip(("sid", "t", "e", "x", "g", "endh", "m4", "m5", "pbf", "f5f", "a"), cols)}
        R["sid"] = R["sid"].astype(str)
        out[key] = R
    return out, drop


def colmask(R, col):
    return np.ones(len(R["e"]), bool) if col == "合併" else (R["m4"] if col == "只400" else R["m5"])


def lazy_fake10(bkey, ci, i, s1):
    R = _B[bkey]
    pool = R["x"] - R["e"]
    rng = np.random.default_rng([20261007, 10, ci, i])
    h = rng.choice(pool, size=len(pool), replace=True) if len(pool) else np.zeros(0, int)
    x = R["e"] + h; eh = x > s1; x = np.where(eh, s1, x)
    gg = gross_at(R["sid"], R["e"], x, eh)
    return (*sig_of(R["sid"], R["e"], x, gg, eh), {})


LAZY["fake10"] = lazy_fake10


def set10(labs):
    q = sum(1 for v in labs if v == "合格"); ql = sum(1 for v in labs if v in ("合格", "另列"))
    return ("合格" if q >= 31 else ("另列" if ql >= 31 else "不合格")), q, ql


def run_a10(procs):
    g = G; w0, w1, sp, c0 = g["w0"], g["w1"], g["sp"], g["c0"]
    t0 = time.time()
    base, drop = a10_rows()
    log("A3-10 訊號表 %d 鍵 %.0fs" % (len(base), time.time() - t0))
    SEG = {"探索": (w0, sp), "確認": (c0, w1)}
    cells = [(B, k, L) for B in BS10 for k in KS10 for L in LS10]
    scells = [(B, None, L) for B in BS10 for L in LS10]

    def arm(key, col, sn, nseed, f50=False, cost=None):
        R = base.get(key + (sn,))
        if R is None:
            return None
        m = colmask(R, col) & ~R["pbf"]
        if f50:
            m &= ~R["f5f"]
        sig, endh = sig_of(R["sid"][m], R["e"][m], R["x"][m], R["g"][m], R["endh"][m])
        if len(sig) == 0:
            return None
        a = {"sig": sig, "endh": endh, "segs": {sn: SEG[sn]}, "jseg": SEG[sn], "seeds": seeds(nseed), "dseg": SEG[sn]}
        if cost is not None:
            a["cost"] = cost
        return a
    RES = {}
    # 批 1：判定（確認段 合併／只 400，200 顆）
    arms = {}
    for cl in cells:
        for col in ("合併", "只400"):
            a = arm(cl, col, "確認", SEEDS["judge"])
            if a:
                arms[("J", col) + cl] = a
    RES.update(run_arms(arms, procs)); del arms
    # 批 2：描述（探索段、只 500、S 臂、ret50、成本）
    arms = {}
    for cl in cells:
        for col in ("合併", "只400"):
            a = arm(cl, col, "探索", SEEDS["a10_exp"])
            if a:
                arms[("E", col) + cl] = a
            a = arm(cl, col, "確認", SEEDS["a10_ret50"], f50=True)
            if a:
                arms[("R50", col) + cl] = a
        a = arm(cl, "只500", "確認", SEEDS["a10_500"])
        if a:
            arms[("J", "只500") + cl] = a
        for cs_ in C.COST_SENS:
            a = arm(cl, "合併", "確認", SEEDS["a10_cost"], cost=cs_)
            if a:
                arms[("COST%.4f" % cs_, "合併") + cl] = a
    for cl in scells:
        for sn in ("確認", "探索"):
            a = arm(cl, "合併", sn, SEEDS["a10_S"])
            if a:
                arms[("S" + sn, "合併") + cl] = a
    RES.update(run_arms(arms, procs)); del arms
    # 批 3：固定天數與隨機出場（lazy）
    _B.clear()
    arms = {}
    for ci, cl in enumerate(cells):
        R = base.get(cl + ("確認",))
        if R is None:
            continue
        m = ~R["pbf"]
        bk = ("B10",) + cl
        _B[bk] = {q: R[q][m] for q in ("sid", "e", "x", "a")}
        for H in C.FIXH:
            arms[("F%d" % H, "合併") + cl] = {"lazy": ("fixed", bk, H, w1), "segs": {"確認": SEG["確認"]}, "jseg": SEG["確認"], "seeds": seeds(SEEDS["a10_fixed"])}
        for i in range(SEEDS["a10_fake"]):
            arms[("FAKE", "合併") + cl + (i,)] = {"lazy": ("fake10", bk, ci, i, w1), "segs": {"確認": SEG["確認"]}, "jseg": SEG["確認"], "seeds": [C.SEED0 + i]}
    RES.update(run_arms(arms, procs)); del arms
    _B.clear()
    p_seeds = save_seeds(RES, "A3-10_seeds.csv.gz")
    # ── 彙總
    BR = {sn: bref(*SEG[sn]) for sn in SEG}
    cellrows = []; lab = {"合併": {}, "只400": {}, "只500": {}}; labE = {"合併": {}, "只400": {}}
    for cl in cells:
        B, k, L = cl; nm = "B%d_k%s_L%d" % cl
        row = {"格": nm}
        for col in COLS:
            a = agg(RES.get(("J", col) + cl, []), "確認", BR["確認"])
            row["確認_" + col] = slim(a); lab[col][nm] = a.get("標籤")
        for col in ("合併", "只400"):
            a = agg(RES.get(("E", col) + cl, []), "探索", BR["探索"])
            row["探索_" + col] = slim(a); labE[col][nm] = a.get("標籤")
            a = agg(RES.get(("R50", col) + cl, []), "確認", BR["確認"])
            row["ret50_確認_" + col] = {"年化中位": a.get("年化中位"), "標籤": a.get("標籤")}
        for cs_ in C.COST_SENS:
            a = agg(RES.get(("COST%.4f" % cs_, "合併") + cl, []), "確認", BR["確認"])
            row["成本%.2f%%_確認_合併" % (100 * cs_)] = {"年化中位": a.get("年化中位"), "標籤": a.get("標籤")}
        mainc = row["確認_合併"].get("年化中位")
        fx = {}
        for H in C.FIXH:
            a = agg(RES.get(("F%d" % H, "合併") + cl, []), "確認", BR["確認"])
            fx[H] = a.get("年化中位")
        row["EMA−固定H_年化差（確認、合併）"] = {H: (mainc - v if (mainc is not None and v is not None) else None) for H, v in fx.items()}
        fk = [x["c_確認"] for i in range(SEEDS["a10_fake"]) for x in RES.get(("FAKE", "合併") + cl + (i,), [])]
        row["隨機出場_p（確認、合併）"] = float(np.mean([v >= mainc for v in fk])) if (fk and mainc is not None) else None
        row["隨機出場_次數"] = len(fk)
        S_c = agg(RES.get(("S確認", "合併", B, None, L), []), "確認", BR["確認"]).get("年化中位")
        S_e = agg(RES.get(("S探索", "合併", B, None, L), []), "探索", BR["探索"]).get("年化中位")
        row["M−S_年化差"] = {"確認": (mainc - S_c) if (mainc is not None and S_c is not None) else None,
                           "探索": (row["探索_合併"].get("年化中位") - S_e) if (row["探索_合併"].get("年化中位") is not None and S_e is not None) else None}
        hm = row["探索_合併"].get("持有天數_平均（逐種子中位）")
        row["退化標記（探索段平均持有＜2日）"] = bool(hm is not None and np.isfinite(hm) and hm < 2)
        cellrows.append(row)
    setl = {}
    for col in COLS:
        sl, q, ql = set10(list(lab[col].values()))
        setl[col] = {"整套": sl, "合格格": q, "合格或另列格": ql, "格數": len(lab[col])}
    for col in ("合併", "只400"):
        sl, q, ql = set10(list(labE[col].values()))
        setl["探索_" + col] = {"整套": sl, "合格格": q, "合格或另列格": ql}
    final = C.label_pf(setl["合併"]["整套"], setl["只400"]["整套"])
    two = {col: (setl[col]["合格格"] >= 31 and setl["探索_" + col]["合格格"] >= 31) for col in ("合併", "只400")}
    r50 = {}
    for col in ("合併", "只400"):
        r50[col] = set10([r["ret50_確認_" + col]["標籤"] for r in cellrows])
    r50lab = C.label_pf(r50["合併"][0], r50["只400"][0])
    grp = {}
    for nm_, idx in (("B", 0), ("k", 1), ("L", 2)):
        for v in sorted(set(c[idx] for c in cells)):
            sub = ["B%d_k%s_L%d" % c for c in cells if c[idx] == v]
            grp["%s=%s" % (nm_, v)] = {col: sum(1 for s in sub if lab[col][s] == "合格") for col in ("合併", "只400")}
    ms_pos = sum(1 for r in cellrows if (r["M−S_年化差"]["確認"] or 0) > 0 and (r["M−S_年化差"]["探索"] or 0) > 0)
    ema60 = sum(1 for r in cellrows if (r["EMA−固定H_年化差（確認、合併）"].get(60) or -1) > 0)
    p05 = sum(1 for r in cellrows if r["隨機出場_p（確認、合併）"] is not None and r["隨機出場_p（確認、合併）"] < 0.05)
    # C6（判定欄合併、確認段：60 格各自的必報量取中位）
    def cmed(k):
        v = [r["確認_合併"].get(k) for r in cellrows if r["確認_合併"].get(k) is not None and np.isfinite(r["確認_合併"].get(k))]
        return float(np.median(v)) if v else None
    c6x = {"持有天數平均（60 格中位）": cmed("持有天數_平均（逐種子中位）"), "持有天數中位（60 格中位）": cmed("持有天數_中位（逐種子中位）"),
           "p10（60 格中位）": cmed("持有天數_p10"), "p90（60 格中位）": cmed("持有天數_p90"),
           "最長（60 格最大）": max([r["確認_合併"].get("最長持有（200 顆最大）") or 0 for r in cellrows]),
           "窗尾仍持有件數（60 格中位、逐種子中位）": cmed("窗尾仍持有件數（逐種子中位）"),
           "離頂距離中位（60 格中位）": cmed("離頂距離中位（出場價÷持有期最高收盤−1）"), "口徑": "確認段、合併欄、每格引擎逐筆成交配對（段尾收盤結算＝窗尾仍持有）"}
    yrs_c = (w1 - c0 + 1) / 252.0
    nsig = {("B%d_k%s_L%d" % cl): int((~base[cl + ("確認",)]["pbf"]).sum()) if cl + ("確認",) in base else 0 for cl in cells}
    pbdrop = int(sum(base[k]["pbf"].sum() for k in base))
    sent = ("爆量突破進、跌破 EMA 出：60 種設定在 2022～2026 合併 %d 種、只 S&P 400 %d 種合格（門檻 31）⇒ %s。" % (setl["合併"]["合格格"], setl["只400"]["合格格"],
            {"不合格": "不構成可用規則", "另列": "多數設定報酬贏 ^SP500TR 但回落比例上不划算", "合格": "兩母體都過"}.get(setl["合併"]["整套"], setl["合併"]["整套"])))
    sent += " 爆量條件 M−S 兩段同為正的格 %d／60；EMA 出場年化贏固定抱 60 天的格 %d／60；隨機出場 p＜0.05 的格 %d／60。作者原參數不明、用常見值網格。" % (ms_pos, ema60, p05)
    sent += "%s；%s；%s。" % (C.IDEA, C.NO_EARLY, C.SURV)
    card = {"件": "A3-10", "名稱": NAME["A3-10"], "台股原登錄": "%s（%s）" % TWREG["A3-10"], "出場型": "① 條件（收盤 ＜ EMA(L) ⇒ 次日開盤賣；⛔ 無時間出口；段尾收盤結算）",
            "N": 1, "標籤": final, "判定格": "60 格整套一判（確認段 ≥ 31／60 合格；兩欄）",
            "三欄": {"合併": "確認段 %d／60 格合格、%d 格合格或另列 ⇒ %s" % (setl["合併"]["合格格"], setl["合併"]["合格或另列格"], setl["合併"]["整套"]),
                   "只400": "確認段 %d／60 格合格、%d 格合格或另列 ⇒ %s" % (setl["只400"]["合格格"], setl["只400"]["合格或另列格"], setl["只400"]["整套"]),
                   "只500": "（描述、⛔ 不判）確認段 %d／60 格合格、%d 格合格或另列" % (setl["只500"]["合格格"], setl["只500"]["合格或另列格"])},
            "條件出場必報": c6x, "結果句": sent,
            "敏感度_ret50": "剔除 S&P 400 未確認 |ret|>50%% 列後：合併 %d／60、只 400 %d／60 格合格 ⇒ %s（原 %s）" % (r50["合併"][1], r50["只400"][1], r50lab, final),
            "偏離": ["台股 10 檔 1/10 ⇒ 8 槽等權抽籤（C5）", "成本 0.585% ⇒ 0.05%（美股）", "開盤鎖漲停／鎖跌停、處置、gate_v2 美股無 ⇒ 拿掉（P4）",
                   "早年段拿掉 ⇒ 只看確認段＋兩母體（seq319 Q1）；原文雙段版另報", "量 ＝ Yahoo 拆股調整量（原文原始股數）",
                   "隨機出場假訊號 1,000 次 ⇒ 每格 30 次、持有天數池 ＝ 訊號表（事件）持有天數（台股原程式用 50 顆引擎實際持有）",
                   "固定抱天數加 240（C6）", "訊號列特徵窗或持有期跨轉接層 hard_break ⇒ 剔除（W1b W5）：%d 列" % pbdrop,
                   "單筆層描述（訊號後 5／10／20／60 日 vs 基準②）⛔ 未做（描述、不計 N）"],
            "補讀法": ["G1", "G2", "G5", "G6", "G7", "G8", "G10", "V1", "V2", "V3"],
            "先驗紀錄": "台股原登錄先驗：①整套合格：否（七成五）⇒ 美股 %s；②爆量加分（M−S＞0 過半、兩段同向）：否或測不出（六成）⇒ 兩段同正 %d／60 格；③EMA 出場比固定抱 60 天好（過半格）：否（六成）⇒ %d／60；④隨機出場 p＜0.05 過半：否（七成）⇒ %d／60" % (final, ms_pos, ema60, p05)}
    out = {"卡片": card, "讀法寫死": READ_TS, "登錄": C.REG, "資料commit": g["meta"]["data_commit"],
           "段": {sn: [dstr(a), dstr(b)] for sn, (a, b) in SEG.items()}, "基準": BR, "整套": setl, "原文雙段版（描述）": two,
           "按B_k_L分組合格格數": grp, "每格訊號列數（確認段、合併）": nsig, "每年訊號列（確認段合併，60 格中位）": float(np.median(list(nsig.values()))) / yrs_c,
           "剔除帳": {"|".join(map(str, k)): v for k, v in drop.items()}, "格": cellrows,
           "逐種子檔（repo 外）": {"path": p_seeds, "sha256": C.sha256f(p_seeds)}, "覆蓋_存活者偏差": C.coverage_cached(g["cal"], w0, w1)}
    return out


# ═════════════ A3-11 外部長線三件 ═════════════
def month_tab():
    M = pd.read_pickle(MONTH_PKL)
    M = M[M["t"].isin(set(G["sids"]))].copy()
    assert (G["mst"][M["mi"].to_numpy()] == M["e"].to_numpy()).all()
    return M


def mis_of(freq):
    nm = len(G["mst"])
    return list(range(nm)) if freq == "月" else [mi for mi in range(nm) if (G["ym0"] + mi - 1) % 12 in (0, 3, 6, 9)]


def book_rows(L, mis, lb_bars=0, extra_lb=None):
    """L：{mi: [代號…]}（已排序截 N）；mis：同頻率換股月序。⇒ 列陣列（G3、G5）。"""
    g = G; ST = g["ST"]; mst = g["mst"]; w1 = g["w1"]
    sets = {mi: set(L.get(mi, [])) for mi in mis}
    rows = []; ndrop = Counter()
    for j, mi in enumerate(mis):
        e = int(mst[mi])
        for s in L.get(mi, []):
            x = None
            for mi2 in mis[j + 1:]:
                if s not in sets[mi2]:
                    x = int(mst[mi2]); break
            d = ST[s]; oe = d["opens"][e]
            if not (np.isfinite(oe) and oe > 0):
                ndrop["開盤不可用"] += 1; continue
            if x is None:
                x = w1; eh = True; gg = d["closes"][w1] / oe - 1.0
            else:
                eh = False; ox = d["opens"][x]; gg = (ox if (np.isfinite(ox) and ox > 0) else d["closes"][x]) / oe - 1.0
            b = d["bars"]; kb = int(np.searchsorted(b, e)) - 1
            a0 = int(b[max(kb - lb_bars, 0)]) if kb >= 0 else e
            rows.append((s, e, x, gg, eh, a0))
    if not rows:
        return {"sid": np.zeros(0, str), "e": np.zeros(0, int), "x": np.zeros(0, int), "g": np.zeros(0), "endh": np.zeros(0, bool), "a": np.zeros(0, int),
                "pbf": np.zeros(0, bool), "f5f": np.zeros(0, bool)}, ndrop
    s, e, x, gg, eh, a0 = (np.array(v) for v in zip(*rows))
    R = {"sid": s.astype(str), "e": e.astype(int), "x": x.astype(int), "g": gg.astype(float), "endh": eh.astype(bool), "a": a0.astype(int)}
    R["pbf"] = pb_hold(R["sid"], R["a"], R["x"]); R["f5f"] = pb_hold(R["sid"], R["a"], R["x"], f50=True)
    ndrop["斷點剔除"] += int(R["pbf"].sum())
    return R, ndrop


def arm_book(R, segs, jseg, dseg, nseed, f50=False, cost=None, m4w=None, seedlist=None):
    m = ~R["pbf"]
    if f50:
        m &= ~R["f5f"]
    sig, endh = sig_of(R["sid"][m], R["e"][m], R["x"][m], R["g"][m], R["endh"][m])
    if len(sig) == 0:
        return None
    a = {"sig": sig, "endh": endh, "segs": segs, "jseg": jseg, "dseg": dseg, "seeds": seedlist if seedlist is not None else seeds(nseed)}
    if cost is not None:
        a["cost"] = cost
    if m4w is not None:
        a["m4w"] = m4w
    return a


def first_q_start(lists_by_cell):
    """G9：所有格（合併欄）都有名單之後的第一個季換股日 mi。"""
    firsts = []
    for L in lists_by_cell:
        ne = [mi for mi, v in L.items() if v]
        if not ne:
            return None
        firsts.append(min(ne))
    m0 = max(firsts)
    for mi in range(m0, len(G["mst"])):
        if (G["ym0"] + mi - 1) % 12 in (0, 3, 6, 9):
            return mi
    return None


def pick_cell(stats, order_key):
    """stats：{cell: (agg_exp, degenerate)} ⇒ 挑格（先合格、再比值；同分 order_key）。"""
    ok = {c: a for c, (a, dg) in stats.items() if not dg and a.get("年化中位") is not None}
    if not ok:
        return None, "全部退化"
    passed = [c for c, a in ok.items() if a["標籤"] == "合格"]
    pool = passed if passed else list(ok)
    best = sorted(pool, key=lambda c: (-ok[c]["比值"], -ok[c]["年化中位"]) + order_key(c))[0]
    return best, ("過判準者取比值最高" if passed else "都沒過、取比值最高")


def t_lists(M, col):
    out = {}
    for mi, g in M.groupby("mi"):
        cm = g["m5"] | g["m4"] if col == "合併" else (g["m4"] if col == "只400" else g["m5"])
        gg = g[cm.astype(bool) & g["rs"].notna()].sort_values(["rs", "t"], ascending=[False, True], kind="mergesort")
        cut = int(math.ceil(0.3 * len(gg)))
        top = set(gg["t"].iloc[:cut])
        tm = gg[(gg["tmpl17"] == True) & gg["t"].isin(top)]   # noqa: E712
        out[mi] = {"pool": list(gg["t"]), "甲": list(tm["t"]), "乙": list(tm[tm["rev_hi8"] == True]["t"])}   # noqa: E712
    return out


def lazy_fakebook(bkey, item_no, i, segs, jseg, m4mode):
    P = _B[bkey]
    rng = np.random.default_rng([20261007, item_no, i])
    L = {}
    for mi in P["mis"]:
        pool = P["pool"].get(mi, []); k = len(P["L"].get(mi, []))
        L[mi] = sorted(rng.choice(pool, size=min(k, len(pool)), replace=False).tolist()) if (k and pool) else []
    R, _ = book_rows(L, P["mis"], P["lb"])
    m = ~R["pbf"]
    sig, endh = sig_of(R["sid"][m], R["e"][m], R["x"][m], R["g"][m], R["endh"][m])
    ex = {}
    if m4mode:
        ex["m4w"] = m4_weights(L, P["mis"])
    return sig, endh, ex


LAZY["fakebook"] = lazy_fakebook


def d_trades():
    g = G; ST = g["ST"]; cal = g["cal"]; w0, w1 = g["w0"], g["w1"]
    wk, wf, wl = RW.weeks_of(cal)
    rows = []; acc = Counter()
    for sid in g["sids"]:
        d = ST[sid]; valid = d["valid"]
        wks, WO, WH, WL, WC, WV = RW.weekly_bars(valid, d["O"], d["H"], d["L"], d["C"], np.nan_to_num(d["V"]), wk)
        if len(wks) <= 60:
            continue
        badw = np.zeros(int(wk.max()) + 3, bool); badw[wk[d["pb"]]] = True
        near = badw[wks] | badw[np.maximum(wks - 1, 0)] | badw[wks + 1]
        ix = np.flatnonzero(valid); w_ = wk[ix]; st = np.r_[0, np.flatnonzero(np.diff(w_)) + 1]; en = np.r_[st[1:], len(ix)] - 1
        wfirst = ix[st]; wlast = ix[en]
        widx = {int(w): k for k, w in enumerate(wks)}
        pbd = np.flatnonzero(d["pb"])
        for bb, s_, top, bot, B_ in LD.box_machine(WH, WL, WC, near, 52):
            ds = int(wlast[bb])
            if not (w0 <= ds <= w1) or not d["member"][ds]:
                continue
            acc["買訊（窗內在母體）"] += 1
            nk = widx.get(int(wks[bb]) + 1)
            if nk is None:
                acc["放棄_下週無K棒"] += 1; continue
            e = int(wfirst[nk]); oe = d["opens"][e]
            if e > w1 or not (np.isfinite(oe) and oe > 0):
                acc["放棄_開盤不可用或超窗"] += 1; continue
            kind = "週收破箱底"
            if s_ is None:
                x = w1; eh = True; kind = "窗尾"
            else:
                dsl = int(wlast[s_]); j = int(np.searchsorted(ix, dsl, side="right"))
                if j < len(ix) and ix[j] <= w1:
                    x = int(ix[j]); eh = False
                else:
                    x = w1; eh = True; kind = "窗尾"
            pp = pbd[(pbd > e) & (pbd <= x)]
            byclose = False
            if len(pp):
                xb = int(ix[np.searchsorted(ix, pp[0]) - 1]); x = xb; eh = False; byclose = True; kind = "壞根前收盤出"
            if eh or byclose:
                gg = d["closes"][x] / oe - 1.0
            else:
                ox = d["opens"][x]; gg = (ox if (np.isfinite(ox) and ox > 0) else d["closes"][x]) / oe - 1.0
            a0 = int(wfirst[max(bb - 52, 0)])
            acc[kind] += 1
            rows.append((sid, ds, e, x, gg, eh, bool(d["m4"][ds]), bool(d["m5"][ds]), cnt(g["f5c"][sid], a0, x) > 0, int(np.searchsorted(ix, x) - np.searchsorted(ix, e))))
    s, t, e, x, gg, eh, m4, m5, f5, nbar = (np.array(v) for v in zip(*rows))
    R = {"sid": s.astype(str), "t": t.astype(int), "e": e.astype(int), "x": x.astype(int), "g": gg.astype(float), "endh": eh.astype(bool), "m4": m4.astype(bool),
         "m5": m5.astype(bool), "f5f": f5.astype(bool), "pbf": np.zeros(len(s), bool), "nbar": nbar.astype(int), "a": e.astype(int)}
    return R, acc


def lazy_faked(bkey, i):
    """D 假訊號：同股、窗內隨機一週（突破週最後一根在該欄母體、下週第一根可買）進場，持有同根數，收盤出。"""
    P = _B[bkey]; R = P["R"]; g = G; ST = g["ST"]; w0, w1 = g["w0"], g["w1"]
    rng = np.random.default_rng([20261007, 4, i])
    sid_o, e_o, x_o, g_o, eh_o = [], [], [], [], []
    for s, nbar in zip(R["sid"], R["nbar"]):
        cands = P["wk_ok"].get(s)
        if cands is None or not len(cands):
            continue
        e = int(cands[rng.integers(len(cands))]); d = ST[s]; ix = P["ix"][s]
        k = int(np.searchsorted(ix, e)) + int(nbar)
        if k < len(ix) and ix[k] <= w1:
            x = int(ix[k]); eh = False
        else:
            x = w1; eh = True
        sid_o.append(s); e_o.append(e); x_o.append(x); g_o.append(d["closes"][x] / d["opens"][e] - 1.0); eh_o.append(eh)
    return (*sig_of(sid_o, e_o, x_o, g_o, eh_o), {})


LAZY["faked"] = lazy_faked


def d_week_cands(col):
    """D 假訊號用：每檔可當隨機進場的日子（某週最後一根在該欄母體 ⇒ 下週第一根有效且開盤有效、≤ 窗尾）。"""
    g = G; ST = g["ST"]; cal = g["cal"]; w0, w1 = g["w0"], g["w1"]
    wk, wf, wl = RW.weeks_of(cal)
    out = {}; IX = {}
    for sid in g["sids"]:
        d = ST[sid]; ix = np.flatnonzero(d["valid"]); IX[sid] = ix
        if len(ix) < 10:
            continue
        w_ = wk[ix]; st = np.r_[0, np.flatnonzero(np.diff(w_)) + 1]; en = np.r_[st[1:], len(ix)] - 1
        wfirst = ix[st]; wlast = ix[en]; ww = w_[st]
        cf = colflag(d, col)
        ok = []
        for k in range(len(ww) - 1):
            if ww[k + 1] != ww[k] + 1:
                continue
            ds, e = int(wlast[k]), int(wfirst[k + 1])
            if w0 <= ds <= w1 and e <= w1 and cf[ds] and np.isfinite(d["opens"][e]) and d["opens"][e] > 0:
                ok.append(e)
        out[sid] = np.array(ok, int)
    return out, IX


def mcap_fix(M5):
    """G11：prep 的 rc（raw_close_aligned）在 yahoo 來源實為「日後拆股調整」收盤 ⇒ 市值 × Π(拆股比 a/b，拆股日 ＞ 該收盤日)；
    tiingo（prices）來源 close 為原始、不改。收盤日 ＝ prep 的 kb（e−1 以前最後一根有效 K 棒 ＝ bars[nbar−1]）。"""
    g = G; ST = g["ST"]; cal = g["cal"]
    fac = np.ones(len(M5)); spl = {}; srcs = {}; st = Counter()
    for i, (t, nbar) in enumerate(zip(M5["t"].to_numpy(), M5["nbar"].to_numpy())):
        if t not in ST or not np.isfinite(nbar):
            continue
        b = ST[t]["bars"]; kb = int(nbar) - 1
        if kb < 0 or kb >= len(b):
            continue
        dl = cal[b[kb]]
        if t not in srcs:
            srcs[t] = C.U.panel(t)["src"]
        s = srcs[t].get(dl)
        if s is None or not str(s).startswith("yahoo:"):
            st["tiingo 或無來源（不改）"] += 1; continue
        nm = str(s).split(":", 1)[1]
        if nm not in spl:
            p = C.U._p("events_yahoo", nm + ".csv")
            if os.path.exists(p):
                d = pd.read_csv(p, dtype=str); d = d[d["type"] == "split"]
                r = d["value"].str.split("/", expand=True).astype(float) if len(d) else None
                spl[nm] = (pd.to_datetime(d["date"]).to_numpy(), (r[0] / r[1]).to_numpy()) if len(d) else (np.zeros(0, "datetime64[ns]"), np.zeros(0))
            else:
                spl[nm] = (np.zeros(0, "datetime64[ns]"), np.zeros(0))
        sd, rr = spl[nm]
        sel = sd > np.datetime64(dl)
        f = float(np.prod(rr[sel])) if sel.any() else 1.0
        fac[i] = f; st["yahoo 來源"] += 1; st["yahoo 且日後有拆股（市值被修正）"] += int(f != 1.0)
    M5["mcap_fix"] = M5["mcap"].to_numpy() * fac
    return M5, {"G11 市值修正帳（S&P 500 股-月）": dict(st), "受影響比例": st["yahoo 且日後有拆股（市值被修正）"] / max(len(M5), 1)}


def i_trades(top50):
    g = G; ST = g["ST"]; n = g["n"]; w0, w1 = g["w0"], g["w1"]; mon = g["mon"]
    rows = []; acc = Counter()
    for sid in g["sids"]:
        d = ST[sid]; b = d["bars"]; nb = len(b)
        if nb < 80:
            continue
        cb, hb, lb, ob = d["C"][b], d["H"][b], d["L"][b], d["O"][b]
        cond, ok, tk, kj, sa, sbb = LI.ichimoku(hb, lb, cb)
        badk = d["pb"][b]
        near = badk | np.r_[False, badk[:-1]] | np.r_[badk[1:], False]
        sigI = np.flatnonzero(cond[1:] & ok[:-1] & ~cond[:-1]) + 1
        if not len(sigI):
            continue
        atr = LI.wilder_atr(hb, lb, cb)
        for k in sigI:
            if k < 77 or near[k]:
                continue
            t = int(b[k])
            if not (w0 <= t <= w1 - 1) or not d["member"][t]:
                continue
            if k + 1 >= nb or int(b[k + 1]) != t + 1 or not (np.isfinite(ob[k + 1]) and ob[k + 1] > 0):
                acc["隔日無K棒或開盤無效"] += 1; continue
            jia = (int(mon[t]), sid) in top50
            for km in (2, 3):
                xc, gg, kind = LI.atr_exit(km, k + 1, cb, ob, atr, badk, b, n)
                if xc > w1:
                    x = w1; eh = True; gg = d["closes"][w1] / ob[k + 1] - 1.0; kind = "窗尾"
                else:
                    x = int(xc); eh = False
                acc[("k%d" % km, kind)] += 1
                rows.append((sid, km, jia, t, t + 1, x, float(gg), eh, bool(d["m4"][t]), bool(d["m5"][t]), cnt(g["f5c"][sid], int(b[max(k - 77, 0)]), x) > 0))
    s, km, jia, t, e, x, gg, eh, m4, m5, f5 = (np.array(v) for v in zip(*rows))
    R = {"sid": s.astype(str), "km": km.astype(int), "jia": jia.astype(bool), "t": t.astype(int), "e": e.astype(int), "x": x.astype(int), "g": gg.astype(float),
         "endh": eh.astype(bool), "m4": m4.astype(bool), "m5": m5.astype(bool), "f5f": f5.astype(bool), "pbf": np.zeros(len(s), bool), "a": e.astype(int)}
    return R, acc


def lazy_fakei(bkey, i):
    """I 假訊號：主格每筆 ⇒ 同曆月、同母體（當月市值前 50）隨機一檔、隨機一日（該檔當日有效且隔日開盤有效）、同 ATR(k3) 出場。"""
    P = _B[bkey]; g = G; ST = g["ST"]; n = g["n"]; w1 = g["w1"]
    rng = np.random.default_rng([20261007, 9, i])
    so, eo, xo, go, ho = [], [], [], [], []
    for t in P["t"]:
        mi = int(g["mon"][t]); cands = P["top50"].get(mi, [])
        days = P["mdays"].get(mi)
        if not cands or days is None:
            continue
        for _ in range(50):
            s = cands[rng.integers(len(cands))]; tt = int(days[rng.integers(len(days))])
            A = P["arr"].get(s)
            if A is None:
                continue
            b, cb, ob, atr, badk = A
            k = int(np.searchsorted(b, tt))
            if k + 1 >= len(b) or b[k] != tt or b[k + 1] != tt + 1 or not (np.isfinite(ob[k + 1]) and ob[k + 1] > 0) or tt > w1 - 1:
                continue
            xc, gg, kind = LI.atr_exit(3, k + 1, cb, ob, atr, badk, b, n)
            if xc > w1:
                x = w1; eh = True; gg = ST[s]["closes"][w1] / ob[k + 1] - 1.0
            else:
                x = int(xc); eh = False
            so.append(s); eo.append(tt + 1); xo.append(x); go.append(float(gg)); ho.append(eh)
            break
    return (*sig_of(so, eo, xo, go, ho), {})


LAZY["fakei"] = lazy_fakei


def run_a11(procs):
    g = G; w0, w1, sp, c0 = g["w0"], g["w1"], g["sp"], g["c0"]
    M = month_tab()
    out = {"讀法寫死": READ_TS, "登錄": C.REG, "資料commit": g["meta"]["data_commit"]}
    # ── 件 T
    TL = {col: t_lists(M, col) for col in COLS}
    cellsT = [(fam, fq, N) for fam in ("甲", "乙") for fq in ("月", "季") for N in (10, 20)]

    def T_L(col, fam, fq, N):
        return {mi: TL[col][mi][fam][:N] for mi in mis_of(fq) if mi in TL[col]}
    q0 = first_q_start([T_L("合併", *c) for c in cellsT])
    startT = int(g["mst"][q0])
    segT = {"探索": (startT, sp), "確認": (c0, w1), "全窗": (w0, w1)}
    rowsT = {}; dropT = Counter()
    for col in COLS:
        for c in cellsT:
            R, dd = book_rows(T_L(col, *c), mis_of(c[1]), lb_bars=252); rowsT[(col,) + c] = R; dropT.update(dd)
    arms = {}
    for c in cellsT:
        a = arm_book(rowsT[("合併",) + c], segT, (w0, w1), segT["探索"], SEEDS["judge"])
        if a:
            arms[("T", "合併") + c] = a
    RT = run_arms(arms, procs); del arms
    stats = {}
    for c in cellsT:
        a = agg(RT.get(("T", "合併") + c, []), "探索", bref(*segT["探索"]))
        dg = bool(a.get("平均持股（逐種子中位）", 0) < 4 or a.get("現金比例（逐種子中位）", 1) > 0.30)
        stats[c] = (a, dg)
    pick, why = pick_cell(stats, lambda c: (0 if c[0] == "甲" else 1, 0 if c[1] == "月" else 1, c[2]))
    # 判定與描述臂
    arms = {}
    if pick is not None:
        arms[("T", "只400") + pick] = arm_book(rowsT[("只400",) + pick], segT, (w0, w1), segT["探索"], SEEDS["judge"])
        arms[("T", "只500") + pick] = arm_book(rowsT[("只500",) + pick], segT, (w0, w1), segT["探索"], SEEDS["desc"])
        for col in ("合併", "只400"):
            arms[("TR50", col) + pick] = arm_book(rowsT[(col,) + pick], segT, (w0, w1), segT["探索"], SEEDS["ret50"], f50=True)
        for cs_ in C.COST_SENS:
            arms[("TCOST%.4f" % cs_, "合併") + pick] = arm_book(rowsT[("合併",) + pick], segT, (w0, w1), segT["探索"], SEEDS["cost"], cost=cs_)
        _B.clear()
        Rp = rowsT[("合併",) + pick]; mk = ~Rp["pbf"]
        _B[("TB",)] = {q: Rp[q][mk] for q in ("sid", "e", "x", "a")}
        for H in C.FIXH:
            arms[("TF%d" % H, "合併") + pick] = {"lazy": ("fixed", ("TB",), H, w1), "segs": segT, "jseg": (w0, w1), "seeds": seeds(SEEDS["fixed"])}
        for col in ("合併", "只400"):
            _B[("TFK", col)] = {"mis": mis_of(pick[1]), "L": T_L(col, *pick), "pool": {mi: TL[col][mi]["pool"] for mi in TL[col]}, "lb": 252}
            for i in range(SEEDS["fake"]):
                arms[("TFAKE", col) + pick + (i,)] = {"lazy": ("fakebook", ("TFK", col), 11, i, segT, (w0, w1), False), "segs": segT, "jseg": (w0, w1), "seeds": [C.SEED0 + i]}
    arms = {k: v for k, v in arms.items() if v}
    RT.update(run_arms(arms, procs)); del arms
    _B.clear()
    p1 = save_seeds(RT, "A3-11_T_seeds.csv.gz")
    T = {"起點（G9）": dstr(startT), "挑格": "%s_%s_N%d" % pick if pick else None, "挑法": why, "剔除帳": dict(dropT),
         "探索段（合併）各格": {"%s_%s_N%d" % c: {**slim(stats[c][0]), "退化": stats[c][1]} for c in cellsT}}
    if pick is not None:
        J = {}
        for col in COLS:
            rr = RT.get(("T", col) + pick, [])
            J[col] = {sn: slim(agg(rr, sn, bref(*segT[sn]))) for sn in ("確認", "探索", "全窗")}
        T["挑中格"] = J
        T["ret50（確認）"] = {col: slim(agg(RT.get(("TR50", col) + pick, []), "確認", bref(c0, w1))) for col in ("合併", "只400")}
        T["成本敏感度（確認、合併）"] = {"%.2f%%" % (100 * cs_): slim(agg(RT.get(("TCOST%.4f" % cs_, "合併") + pick, []), "確認", bref(c0, w1))) for cs_ in C.COST_SENS}
        T["固定天數（確認、合併，描述）"] = {H: slim(agg(RT.get(("TF%d" % H, "合併") + pick, []), "確認", bref(c0, w1))) for H in C.FIXH}
        fk = {}
        for col in ("合併", "只400"):
            v = [x["c_確認"] for i in range(SEEDS["fake"]) for x in RT.get(("TFAKE", col) + pick + (i,), [])]
            fk[col] = {"次數": len(v), "p": float(np.mean([z >= J[col]["確認"]["年化中位"] for z in v])) if v else None, "假年化中位": float(np.median(v)) if v else None}
        T["假訊號_同池隨機（確認）"] = fk
        T["標籤"] = C.label_pf(J["合併"]["確認"]["標籤"], J["只400"]["確認"]["標籤"])
        T["ret50標籤"] = C.label_pf(T["ret50（確認）"]["合併"]["標籤"], T["ret50（確認）"]["只400"]["標籤"])
    else:
        T["標籤"] = "不可判定（全部格退化）"
    T["逐種子檔（repo 外）"] = {"path": p1, "sha256": C.sha256f(p1)}
    out["T"] = T
    log("A3-11 T 完成：%s %s" % (T.get("挑格"), T["標籤"]))
    # ── 件 D
    RD, accD = d_trades()
    pD = os.path.join(WK, "A3-11_D_trades.csv.gz")
    pd.DataFrame({"sid": RD["sid"], "e": RD["e"], "x": RD["x"], "g": RD["g"]}).to_csv(pD, index=False, compression="gzip")
    segF ={"探索": (w0, sp), "確認": (c0, w1), "全窗": (w0, w1)}
    arms = {}
    for col, ns in (("合併", SEEDS["judge"]), ("只400", SEEDS["judge"]), ("只500", SEEDS["desc"])):
        m = colmask(RD, col)
        a = arm_book({q: RD[q][m] for q in RD}, segF, (w0, w1), segF["探索"], ns)
        if a:
            arms[("D", col)] = a
        if col != "只500":
            a = arm_book({q: RD[q][m] for q in RD}, segF, (w0, w1), segF["探索"], SEEDS["ret50"], f50=True)
            if a:
                arms[("DR50", col)] = a
    for cs_ in C.COST_SENS:
        arms[("DCOST%.4f" % cs_, "合併")] = arm_book(RD, segF, (w0, w1), segF["探索"], SEEDS["cost"], cost=cs_)
    _B.clear()
    _B[("DB",)] = {q: RD[q] for q in ("sid", "e", "x", "a")}
    for H in C.FIXH:
        arms[("DF%d" % H, "合併")] = {"lazy": ("fixed", ("DB",), H, w1), "segs": segF, "jseg": (w0, w1), "seeds": seeds(SEEDS["fixed"])}
    for col in ("合併", "只400"):
        m = colmask(RD, col)
        wc, IX = d_week_cands(col)
        _B[("DFK", col)] = {"R": {q: RD[q][m] for q in RD}, "wk_ok": wc, "ix": IX}
        for i in range(SEEDS["fake"]):
            arms[("DFAKE", col, i)] = {"lazy": ("faked", ("DFK", col), i), "segs": segF, "jseg": (w0, w1), "seeds": [C.SEED0 + i]}
    arms = {k: v for k, v in arms.items() if v}
    RDr = run_arms(arms, procs); del arms
    _B.clear()
    p2 = save_seeds(RDr, "A3-11_D_seeds.csv.gz")
    Dd = {"事件帳": dict(accD), "8 槽下 N 10／20 兩格相同 ⇒ 1 格": True}
    J = {col: {sn: slim(agg(RDr.get(("D", col), []), sn, bref(*segF[sn]))) for sn in ("確認", "探索", "全窗")} for col in COLS}
    Dd["判定格"] = J
    Dd["ret50（確認）"] = {col: slim(agg(RDr.get(("DR50", col), []), "確認", bref(c0, w1))) for col in ("合併", "只400")}
    Dd["成本敏感度（確認、合併）"] = {"%.2f%%" % (100 * cs_): slim(agg(RDr.get(("DCOST%.4f" % cs_, "合併"), []), "確認", bref(c0, w1))) for cs_ in C.COST_SENS}
    Dd["固定天數（確認、合併，描述）"] = {H: slim(agg(RDr.get(("DF%d" % H, "合併"), []), "確認", bref(c0, w1))) for H in C.FIXH}
    fk = {}
    for col in ("合併", "只400"):
        v = [x["c_確認"] for i in range(SEEDS["fake"]) for x in RDr.get(("DFAKE", col, i), [])]
        fk[col] = {"次數": len(v), "p": float(np.mean([z >= J[col]["確認"]["年化中位"] for z in v])) if v else None, "假年化中位": float(np.median(v)) if v else None}
    Dd["假訊號_同股隨機週（確認）"] = fk
    net = RD["g"] - COST
    Dd["逐筆（全部訊號、合併）"] = {"筆數": int(len(net)), "平均淨報酬": float(net.mean()), "勝率": float((net > 0).mean()), "平均持有根數": float(RD["nbar"].mean()),
                          "對照（台股原登錄引）": "布考斯基 美股 2001～2010 週線 +6.9%／筆、日線 0.0%"}
    Dd["標籤"] = C.label_pf(J["合併"]["確認"]["標籤"], J["只400"]["確認"]["標籤"])
    Dd["ret50標籤"] = C.label_pf(Dd["ret50（確認）"]["合併"]["標籤"], Dd["ret50（確認）"]["只400"]["標籤"])
    Dd["逐種子檔（repo 外）"] = {"path": p2, "sha256": C.sha256f(p2)}
    out["D"] = Dd
    log("A3-11 D 完成：%s" % Dd["標籤"])
    # ── 件 I
    M5, mfix = mcap_fix(M[M["m5"].astype(bool)].copy())
    top50 = set(); top50m = {}; old50 = set()
    for mi, gm in M5.groupby("mi"):
        tt = list(gm.nlargest(50, "mcap_fix")["t"]); top50m[int(mi)] = tt
        top50 |= {(int(mi), t) for t in tt}
        old50 |= {(int(mi), t) for t in gm.nlargest(50, "mcap")["t"]}
    mfix["甲母體（股-月）與 prep 原 mcap 版不同的筆數"] = len(top50 ^ old50) // 2
    mfix["甲母體股-月總數"] = len(top50)
    RI, accI = i_trades(top50)
    k3 = RI["km"] == 3
    pI = os.path.join(WK, "A3-11_I_trades_k3.csv.gz")
    pd.DataFrame({"sid": RI["sid"][k3], "e": RI["e"][k3], "x": RI["x"][k3], "jia": RI["jia"][k3]}).to_csv(pI, index=False, compression="gzip")
    arms = {}
    for jia in (True, False):
        for km in (3, 2):
            for col in COLS:
                if jia and col != "合併":
                    continue
                m = (RI["jia"] == jia) & (RI["km"] == km) & colmask(RI, col)
                ns = SEEDS["judge"] if (jia and km == 3) else SEEDS["desc"]
                a = arm_book({q: RI[q][m] for q in RI}, segF, (w0, w1), segF["全窗"], ns)
                if a:
                    arms[("I", "甲" if jia else "乙", km, col)] = a
    mmain = RI["jia"] & (RI["km"] == 3)
    for cs_ in C.COST_SENS:
        arms[("ICOST%.4f" % cs_,)] = arm_book({q: RI[q][mmain] for q in RI}, segF, (w0, w1), segF["全窗"], SEEDS["cost"], cost=cs_)
    _B.clear()
    _B[("IB",)] = {q: RI[q][mmain] for q in ("sid", "e", "x", "a")}
    for H in C.FIXH:
        arms[("IF%d" % H,)] = {"lazy": ("fixed", ("IB",), H, w1), "segs": segF, "jseg": (w0, w1), "seeds": seeds(SEEDS["fixed"])}
    arrs = {}
    for s in set(t for v in top50m.values() for t in v):
        d = g["ST"][s]; b = d["bars"]
        if len(b) < 80:
            continue
        arrs[s] = (b, d["C"][b], d["O"][b], LI.wilder_atr(d["H"][b], d["L"][b], d["C"][b]), d["pb"][b])
    mdays = {}
    for mi in range(len(g["mst"])):
        a_ = int(g["mst"][mi]); b_ = int(g["mst"][mi + 1]) - 1 if mi + 1 < len(g["mst"]) else w1
        mdays[mi] = np.arange(a_, min(b_, w1 - 1) + 1)
    _B[("IFK",)] = {"t": RI["t"][mmain], "top50": top50m, "mdays": mdays, "arr": arrs}
    for i in range(SEEDS["fake"]):
        arms[("IFAKE", i)] = {"lazy": ("fakei", ("IFK",), i), "segs": segF, "jseg": (w0, w1), "seeds": [C.SEED0 + i]}
    arms = {k: v for k, v in arms.items() if v}
    RIr = run_arms(arms, procs); del arms
    _B.clear()
    p3 = save_seeds(RIr, "A3-11_I_seeds.csv.gz")
    I = {"事件帳": {"|".join(map(str, k)) if isinstance(k, tuple) else k: v for k, v in accI.items()},
         "甲進場訊號（k3）": int(mmain.sum()), "乙進場訊號（k3、合併）": int(((~RI["jia"]) & (RI["km"] == 3)).sum())}
    cellsI = {}
    for jia in ("甲", "乙"):
        for km in (3, 2):
            for col in COLS:
                rr = RIr.get(("I", jia, km, col))
                if rr is None:
                    continue
                cellsI["%s_k%d_%s" % (jia, km, col)] = {sn: slim(agg(rr, sn, bref(*segF[sn]))) for sn in ("全窗", "探索", "確認")}
    I["格"] = cellsI
    mainI = cellsI.get("甲_k3_合併", {}).get("全窗", {})
    I["成本敏感度（全窗）"] = {"%.2f%%" % (100 * cs_): slim(agg(RIr.get(("ICOST%.4f" % cs_,), []), "全窗", bref(w0, w1))) for cs_ in C.COST_SENS}
    I["固定天數（全窗，描述）"] = {H: slim(agg(RIr.get(("IF%d" % H,), []), "全窗", bref(w0, w1))) for H in C.FIXH}
    v = [x["c_全窗"] for i in range(SEEDS["fake"]) for x in RIr.get(("IFAKE", i), [])]
    I["假訊號_同月同母體隨機（全窗）"] = {"次數": len(v), "p": float(np.mean([z >= mainI.get("年化中位", np.inf) for z in v])) if v else None,
                                "假年化中位": float(np.median(v)) if v else None}
    labI = mainI.get("標籤", "不可判定")
    I["標籤"] = ("事後擴母體" if labI == "合格" else ("事後擴母體（另列）" if labI == "另列" else "不合格")) if labI in ("合格", "另列", "不合格") else "不可判定"
    I["市值修正（G11）"] = mfix
    I["標籤註"] = "甲 ＝ S&P 500 市值前 50（代理）⇒ 只 400 欄依構造無股 ⇒ 最多事後擴母體（I2）；合併 ＝ 只 500"
    I["ret50"] = "甲母體只含 S&P 500 ⇒ S&P 400 未確認列不在母體、判語不變"
    I["逐種子檔（repo 外）"] = {"path": p3, "sha256": C.sha256f(p3)}
    out["I"] = I
    log("A3-11 I 完成：%s" % I["標籤"])
    # ── 卡片
    labs = {"T": T["標籤"], "D": Dd["標籤"], "I": I["標籤"]}
    order = ["合格", "事後擴母體", "另列", "事後擴母體（另列）", "不合格"]
    best = min(labs.values(), key=lambda s: order.index(s) if s in order else 99)
    fl = "合格（%s）" % "、".join(k for k, v in labs.items() if v == "合格") if best == "合格" else (
        "%s（%s）" % (best, "、".join(k for k, v in labs.items() if v == best)) if best != "不合格" else "不合格")
    jT = T.get("挑中格", {}); jD = Dd["判定格"]
    def one(j, col, sn="確認"):
        x = j.get(col, {}).get(sn, {})
        return "%s／%s（基準 %s／%s）⇒ %s" % (pct(x.get("年化中位")), pct(x.get("回落中位")), pct(x.get("基準年化")), pct(x.get("基準回落")), x.get("標籤"))
    three = {"合併": "T 挑中 %s：%s｜D：%s｜I 甲k3 全窗：%s" % (T.get("挑格"), one(jT, "合併"), one(jD, "合併"), one({"合併": cellsI.get("甲_k3_合併", {})}, "合併", "全窗")),
             "只400": "T：%s｜D：%s｜I：依構造無股（甲 ＝ S&P 500 市值前 50）" % (one(jT, "只400"), one(jD, "只400")),
             "只500": "（描述、⛔ 不判）T：%s｜D：%s" % (one(jT, "只500"), one(jD, "只500"))}
    c6x = {"T 挑中格（確認段判；全窗引擎）": c6(agg(RT.get(("T", "合併") + pick, []), "確認", bref(c0, w1))) if pick else None,
           "D": c6(agg(RDr.get(("D", "合併"), []), "確認", bref(c0, w1))), "I 甲k3": c6(agg(RIr.get(("I", "甲", 3, "合併"), []), "全窗", bref(w0, w1)))}
    sent = ("外部長線三件：T（趨勢樣板，挑中 %s）%s；D（週線達華斯）%s；I（一目三役，甲＝S&P 500 市值前 50 代理、k3）%s。" % (T.get("挑格"), T["標籤"], Dd["標籤"], I["標籤"]))
    sent += " 季版條件比月版寬：創 8 季新高觸發 34%%（T 乙族）。%s；%s；%s。" % (C.IDEA, C.NO_EARLY, C.SURV)
    card = {"件": "A3-11", "名稱": NAME["A3-11"], "台股原登錄": "%s（%s）" % TWREG["A3-11"], "出場型": "① 條件（T 換股簿續抱＝不再符合才換；D 週收破箱底；I ATR 移動停損）",
            "N": 3, "標籤": fl, "格標籤": labs, "判定格": {"T": T.get("挑格"), "D": "N 軸退化後唯一格", "I": "甲 × k3（全窗）"}, "三欄": three,
            "條件出場必報": c6x, "結果句": sent,
            "敏感度_ret50": "T：%s；D：%s；I：%s" % (T.get("ret50標籤"), Dd.get("ret50標籤"), I["ret50"]),
            "偏離": ["換股簿（名單全買 1/N、依名次）⇒ 8 槽等權抽籤；N 讀成名單長度（G2）", "D 的 N 10／20 在 8 槽下相同 ⇒ 1 格；RS 高者先 ⇒ 抽籤",
                   "I 最多 20 檔 ⇒ 8 槽；轉換÷基準大者先 ⇒ 抽籤", "T 乙 月營收創 24 月新高 ⇒ 季營收創 8 季新高（P6）",
                   "I 甲 臺灣50 ⇒ 當月 S&P 500 市值前 50（代理，seq319 Q5）；I 判定段 ⇒ 美股全窗（P12）", "早年段拿掉；-KY創 閘、溫斯坦描述臂、日線達華斯描述臂、營量重疊率 ⛔ 未做",
                   "成本 0.585% ⇒ 0.05%", "假訊號 1,000／200 次 ⇒ 100 次",
                   "prep 的原始收盤實為日後拆股調整價，已改 close×日後拆股比；A4 同法（回測線協調訊息、14:4x 收到；第一次 A3-11 全量用了未修正市值、I 已看過，修正後 A3-11 全部重跑；受影響 %d 股-月、甲母體變動 %d 股-月）" % (
                       mfix["G11 市值修正帳（S&P 500 股-月）"].get("yahoo 且日後有拆股（市值被修正）", 0), mfix["甲母體（股-月）與 prep 原 mcap 版不同的筆數"])],
            "補讀法": ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9", "G10", "G11", "T1", "T2", "D1", "I1", "I2"],
            "先驗紀錄": "台股原登錄先驗：①T 挑中格確認段合格、早年不合格（五成）⇒ 美股確認段 %s（早年無）；②D 週線兩段皆不合格（六成五）⇒ 確認 %s、探索 %s；③I 4 格沒有一格兩段都合格（六成）⇒ 主格全窗 %s" % (
                jT.get("合併", {}).get("確認", {}).get("標籤"), jD["合併"]["確認"]["標籤"], jD["合併"]["探索"]["標籤"], labI)}
    out["卡片"] = card
    out["覆蓋_存活者偏差"] = C.coverage_cached(g["cal"], w0, w1)
    return out


# ═════════════ A3-12 動能改良四件 ═════════════
FS12, FQ12, NS12 = (3, 6, 12), ("月", "季"), (10, 20)


def mom_tables(col):
    """每個換股月 mi ⇒ {"R": {F: dict}, "M3": {F: dict}}（該欄排名母體）。"""
    g = G; ST = g["ST"]; sids = g["sids"]; me = g["me"]; mst = g["mst"]; ym = g["ym"]; bench = g["bench"]
    CF = np.column_stack([ST[s]["closes"] for s in sids])
    V = np.column_stack([ST[s]["valid"] for s in sids])
    MEM = np.column_stack([colflag(ST[s], col) for s in sids])
    pos = np.where(V, np.arange(len(V))[:, None], -1)
    LV = np.maximum.accumulate(pos, axis=0)
    out = {}
    for mi, e in enumerate(mst):
        e = int(e); m = int(ym[e])
        pop = MEM[e] & (LV[e - 1] >= 0) & ((e - LV[e - 1]) <= 5)
        Rd = {}; M3d = {}
        bpos = me.get(m - 2)
        for F in FS12:
            apos = me.get(m - 2 - F)
            if apos is None or bpos is None:
                Rd[F] = {}; continue
            ca, cb = CF[apos], CF[bpos]
            ok = pop & np.isfinite(ca) & np.isfinite(cb) & (ca > 0) & (cb > 0)
            Rd[F] = {sids[j]: float(cb[j] / ca[j] - 1.0) for j in np.flatnonzero(ok)}
        ks = [k for k in range(m - 2 - 36, m - 2 + 1) if k in me]
        if len(ks) >= 25:
            pp = [me[k] for k in ks]
            bm = bench[pp]; xr = bm[1:] / bm[:-1] - 1.0
            cols = np.flatnonzero(pop)
            CM = CF[np.ix_(pp, cols)]
            with np.errstate(invalid="ignore", divide="ignore"):
                Y = CM[1:] / CM[:-1] - 1.0
            msk = np.isfinite(Y) & np.isfinite(xr)[:, None]
            nn = msk.sum(0)
            X = np.where(msk, xr[:, None], 0.0); Yz = np.where(msk, Y, 0.0)
            with np.errstate(invalid="ignore", divide="ignore"):
                xm = X.sum(0) / nn; ymn = Yz.sum(0) / nn
                sxy = (np.where(msk, (X - xm) * (Yz - ymn), 0.0)).sum(0); sxx = (np.where(msk, (X - xm) ** 2, 0.0)).sum(0)
                beta = sxy / sxx; alpha = ymn - beta * xm
                res = np.where(msk, Yz - alpha - beta * X, np.nan)
                sd = np.nanstd(res, axis=0, ddof=1)
            for F in FS12:
                last = res[-F:]
                okF = (nn >= 24) & np.isfinite(last).all(0) & (sd > 0) & np.isfinite(sd)
                M3d[F] = {sids[cols[j]]: float(last[:, j].sum() / sd[j]) for j in np.flatnonzero(okF)}
        else:
            M3d = {F: {} for F in FS12}
        out[mi] = {"R": Rd, "M3": M3d}
    return out


def topn(d, N, excl=None):
    items = sorted(((v, s) for s, v in d.items() if excl is None or s not in excl), key=lambda t: (-t[0], t[1]))
    return [s for _, s in items[:N]]


def mom_lists(TB, Mk, F, fq, N):
    mis = mis_of(fq); L = {}; keep = []; prev = None
    for mi in mis:
        R = TB[mi]["R"][F]
        if Mk in ("M0", "M4"):
            L[mi] = topn(R, N)
        elif Mk == "M1":
            n = len(R); k = int(math.floor(0.03 * n))
            order = sorted(R, key=lambda s: (-R[s], s))
            drop = set(order[:k]) | set(order[n - k:]) if k > 0 else set()
            L[mi] = topn(R, N, excl=drop)
        elif Mk == "M2":
            order = sorted(R, key=lambda s: (-R[s], s)); cut = int(math.ceil(0.3 * len(order)))
            cur = set(order[:cut])
            if prev is None:
                L[mi] = []
            else:
                both = {s: R[s] for s in cur & prev}
                L[mi] = topn(both, N)
                if cur:
                    keep.append(len(cur & prev) / len(cur))
            prev = cur if R else None
        elif Mk == "M3":
            L[mi] = topn(TB[mi]["M3"][F], N)
    return L, (float(np.mean(keep)) if keep else None)


def m4_weights(L, mis):
    g = G; ST = g["ST"]; mst = g["mst"]; w = {}
    for mi in mis:
        e = int(mst[mi]); lst = L.get(mi, [])
        if not lst or e < 61:
            w[e] = 1.0; continue
        CFm = np.column_stack([ST[s]["closes"][e - 61:e] for s in lst])
        with np.errstate(invalid="ignore", divide="ignore"):
            r = CFm[1:] / CFm[:-1] - 1.0
        ok = np.isfinite(r).any(1)
        ew = np.nanmean(np.where(np.isfinite(r), r, np.nan)[ok], axis=1) if ok.any() else np.zeros(0)
        vol = float(np.std(ew, ddof=1) * math.sqrt(252)) if len(ew) > 2 else np.nan
        w[e] = min(1.0, 0.20 / vol) if (np.isfinite(vol) and vol > 0) else 1.0
    return w


def run_a12(procs):
    g = G; w0, w1, sp, c0 = g["w0"], g["w1"], g["sp"], g["c0"]
    t0 = time.time()
    TBc = {col: mom_tables(col) for col in COLS}
    log("A3-12 排名表 %.0fs" % (time.time() - t0))
    cells = [(F, fq, N) for F in FS12 for fq in FQ12 for N in NS12]
    groups = {"M0": "M0", "M1": "M1", "M2": "M2", "M3": "M3"}           # M4 ＝ M0 覆蓋層
    LST = {}; KEEP = {}
    for col in COLS:
        for Mk in groups:
            for c in cells:
                L, kp = mom_lists(TBc[col], Mk, *c); LST[(col, Mk) + c] = L; KEEP[(col, Mk) + c] = kp
    starts = {}
    for Mk in ("M1", "M2", "M3", "M4"):
        base = "M0" if Mk == "M4" else Mk
        q0 = first_q_start([LST[("合併", base) + c] for c in cells])
        starts[Mk] = int(g["mst"][q0])
    starts["M0"] = starts["M4"]
    lbF = {F: (F + 2) * 21 for F in FS12}
    ROWS = {}; drop = Counter()
    W4 = {}
    for col in COLS:
        for Mk in groups:
            for c in cells:
                R, dd = book_rows(LST[(col, Mk) + c], mis_of(c[1]), lb_bars=lbF[c[0]] if Mk != "M3" else 38 * 21)
                ROWS[(col, Mk) + c] = R; drop.update(dd)
                if Mk == "M0":
                    W4[(col,) + c] = m4_weights(LST[(col, "M0") + c], mis_of(c[1]))

    def segs_for(Mk):
        st = starts[Mk]
        return {"探索": (st, sp), "確認": (c0, w1), "全窗": (w0, w1)}
    arms = {}
    for Mk in groups:
        sg = segs_for("M4" if Mk == "M0" else Mk)
        for c in cells:
            a = arm_book(ROWS[("合併", Mk) + c], sg, (w0, w1), sg["探索"], SEEDS["judge"], m4w=W4[("合併",) + c] if Mk == "M0" else None)
            if a:
                arms[(Mk, "合併") + c] = a
    RES = run_arms(arms, procs); del arms
    picks = {}; PST = {}
    for Mk in ("M1", "M2", "M3", "M4"):
        src = "M0" if Mk == "M4" else Mk; sg = segs_for(Mk); br = bref(*sg["探索"])
        stats = {}
        for c in cells:
            rr = RES.get((src, "合併") + c, [])
            a = agg(rr, "探索", br, m4=(Mk == "M4"))
            a0 = agg(rr, "探索", br) if Mk == "M4" else a
            dg = bool(a0.get("平均持股（逐種子中位）", 0) < 4 or a0.get("現金比例（逐種子中位）", 1) > 0.30)
            stats[c] = (a, dg)
        pk, why = pick_cell(stats, lambda c: (c[0], 0 if c[1] == "月" else 1, c[2]))
        picks[Mk] = (pk, why); PST[Mk] = stats
    log("A3-12 挑格：%s" % {k: v[0] for k, v in picks.items()})
    arms = {}; _B.clear()
    for Mk, (pk, why) in picks.items():
        if pk is None:
            continue
        src = "M0" if Mk == "M4" else Mk; sg = segs_for(Mk)
        w4 = (lambda col: W4[(col,) + pk]) if Mk == "M4" else (lambda col: None)
        arms[(src, "只400") + pk] = arm_book(ROWS[("只400", src) + pk], sg, (w0, w1), sg["探索"], SEEDS["judge"], m4w=w4("只400"))
        arms[(src, "只500") + pk] = arm_book(ROWS[("只500", src) + pk], sg, (w0, w1), sg["探索"], SEEDS["desc"], m4w=w4("只500"))
        if Mk != "M4":
            arms[("M0", "只400") + pk] = arms.get(("M0", "只400") + pk) or arm_book(ROWS[("只400", "M0") + pk], sg, (w0, w1), sg["探索"], SEEDS["desc"], m4w=W4[("只400",) + pk])
        for col in ("合併", "只400"):
            arms[("R50", Mk, col) + pk] = arm_book(ROWS[(col, src) + pk], sg, (w0, w1), sg["探索"], SEEDS["ret50"], f50=True, m4w=w4(col))
        for cs_ in C.COST_SENS:
            arms[("COST%.4f" % cs_, Mk) + pk] = arm_book(ROWS[("合併", src) + pk], sg, (w0, w1), sg["探索"], SEEDS["cost"], cost=cs_, m4w=w4("合併"))
        Rp = ROWS[("合併", src) + pk]; mk = ~Rp["pbf"]
        _B[("FB", Mk)] = {q: Rp[q][mk] for q in ("sid", "e", "x", "a")}
        if Mk == "M4":
            _B[("FB", Mk)]["m4w"] = W4[("合併",) + pk]
        for H in C.FIXH:
            arms[("F%d" % H, Mk) + pk] = {"lazy": ("fixed", ("FB", Mk), H, w1), "segs": sg, "jseg": (w0, w1), "seeds": seeds(SEEDS["fixed"])}
        for col in ("合併", "只400"):
            _B[("FK", Mk, col)] = {"mis": mis_of(pk[1]), "L": LST[(col, src) + pk],
                                   "pool": {mi: list((TBc[col][mi]["M3"] if src == "M3" else TBc[col][mi]["R"])[pk[0]].keys()) for mi in TBc[col]}, "lb": lbF[pk[0]]}
            for i in range(SEEDS["fake"]):
                arms[("FAKE", Mk, col) + pk + (i,)] = {"lazy": ("fakebook", ("FK", Mk, col), 12, i, sg, (w0, w1), Mk == "M4"), "segs": sg, "jseg": (w0, w1), "seeds": [C.SEED0 + i]}
    arms = {k: v for k, v in arms.items() if v}
    RES.update(run_arms(arms, procs)); del arms
    _B.clear()
    p_seeds = save_seeds(RES, "A3-12_seeds.csv.gz")
    out = {"讀法寫死": READ_TS, "登錄": C.REG, "資料commit": g["meta"]["data_commit"], "探索段起點（G9）": {k: dstr(v) for k, v in starts.items()}, "剔除帳": dict(drop)}
    items = {}
    for Mk in ("M1", "M2", "M3", "M4"):
        pk, why = picks[Mk]; src = "M0" if Mk == "M4" else Mk; sg = segs_for(Mk); m4 = Mk == "M4"
        it = {"名": {"M1": "剔除極端 3%", "M2": "持續型", "M3": "殘差動能（對 ^SP500TR、36 月）", "M4": "波動縮放（目標 20%）"}[Mk],
              "探索段（合併）各格": {"F%d_%s_N%d" % c: {**slim(PST[Mk][c][0]), "退化": PST[Mk][c][1]} for c in cells}, "挑法": why}
        if pk is None:
            it["標籤"] = "不可判定（全部格退化）"; items[Mk] = it; continue
        it["挑格"] = "F%d_%s_N%d" % pk
        J = {}
        for col in COLS:
            rr = RES.get((src, col) + pk, [])
            J[col] = {sn: slim(agg(rr, sn, bref(*sg[sn]), m4=m4)) for sn in ("確認", "探索", "全窗")}
        it["挑中格"] = J
        it["同格 M0（對照）"] = {col: {sn: slim(agg(RES.get(("M0", col) + pk, []), sn, bref(*sg[sn]))) for sn in ("確認",)} for col in ("合併", "只400")}
        mc = J["合併"]["確認"].get("年化中位"); m0c = it["同格 M0（對照）"]["合併"]["確認"].get("年化中位")
        it["比單純動能多（確認、合併，年化點）"] = (mc - m0c) if (mc is not None and m0c is not None) else None
        it["ret50（確認）"] = {col: slim(agg(RES.get(("R50", Mk, col) + pk, []), "確認", bref(c0, w1), m4=m4)) for col in ("合併", "只400")}
        it["成本敏感度（確認、合併）"] = {"%.2f%%" % (100 * cs_): slim(agg(RES.get(("COST%.4f" % cs_, Mk) + pk, []), "確認", bref(c0, w1), m4=m4)) for cs_ in C.COST_SENS}
        it["固定天數（確認、合併，描述）"] = {H: slim(agg(RES.get(("F%d" % H, Mk) + pk, []), "確認", bref(c0, w1), m4=m4)) for H in C.FIXH}
        fk = {}
        for col in ("合併", "只400"):
            v = [x[("c4_" if m4 else "c_") + "確認"] for i in range(SEEDS["fake"]) for x in RES.get(("FAKE", Mk, col) + pk + (i,), [])]
            fk[col] = {"次數": len(v), "p": float(np.mean([z >= J[col]["確認"]["年化中位"] for z in v])) if v else None, "假年化中位": float(np.median(v)) if v else None}
        it["假訊號_同池隨機（確認）"] = fk
        if Mk == "M2":
            it["持續判定後留下比例（合併、挑中格）"] = KEEP[("合併", "M2") + pk]
        it["標籤"] = C.label_pf(J["合併"]["確認"]["標籤"], J["只400"]["確認"]["標籤"])
        it["ret50標籤"] = C.label_pf(it["ret50（確認）"]["合併"]["標籤"], it["ret50（確認）"]["只400"]["標籤"])
        it["條件出場必報"] = c6(agg(RES.get((src, "合併") + pk, []), "確認", bref(c0, w1), m4=m4))
        items[Mk] = it
    out["四件"] = items
    # M0 確認段（對照，12 格合併）
    out["M0 單純動能（對照、⛔ 不判；合併欄 12 格）"] = {"F%d_%s_N%d" % c: slim(agg(RES.get(("M0", "合併") + c, []), "確認", bref(c0, w1))) for c in cells}
    labs = {k: v["標籤"] for k, v in items.items()}
    order = ["合格", "事後擴母體", "另列", "事後擴母體（另列）", "不合格"]
    best = min(labs.values(), key=lambda s: order.index(s) if s in order else 99)
    fl = "合格（%s）" % "、".join(k for k, v in labs.items() if v == "合格") if best == "合格" else (
        "%s（%s）" % (best, "、".join(k for k, v in labs.items() if v == best)) if best != "不合格" else "不合格")

    def one(Mk, col):
        it = items[Mk]
        if "挑中格" not in it:
            return "%s：%s" % (Mk, it["標籤"])
        x = it["挑中格"][col]["確認"]
        return "%s %s %s／%s ⇒ %s" % (Mk, it["挑格"], pct(x.get("年化中位")), pct(x.get("回落中位")), x.get("標籤"))
    br = bref(c0, w1)
    three = {"合併": "；".join(one(k, "合併") for k in items) + "（^SP500TR %s／%s）" % (pct(br["年化"]), pct(br["回落"])),
             "只400": "；".join(one(k, "只400") for k in items), "只500": "（描述、⛔ 不判）" + "；".join(one(k, "只500") for k in items)}
    sent = "動能改良四件（美股 S&P 500＋400、8 槽）：" + "；".join("%s %s" % (items[k]["名"], labs[k]) for k in items) + "。"
    sent += " 比單純動能多（確認、合併）：" + "、".join("%s %s" % (k, pct(items[k].get("比單純動能多（確認、合併，年化點）"))) for k in items) + "。"
    sent += " 台股 PREREGF（W1 池剔極端 +26.14%／−40.27% 另列）、PREREGC（W1 池殘差動能 +24.62%／−41.51% 另列）方向已見（原登錄必附）。"
    sent += "%s；%s；%s。" % (C.IDEA, C.NO_EARLY, C.SURV)
    m0c = {k: (items[k]["挑中格"]["合併"]["確認"].get("年化中位") if "挑中格" in items[k] else None) for k in items}
    card = {"件": "A3-12", "名稱": NAME["A3-12"], "台股原登錄": "%s（%s）" % TWREG["A3-12"], "出場型": "② 不再符合才換（仍入選續抱、落選下一換股日開盤賣）",
            "N": 4, "標籤": fl, "格標籤": labs, "判定格": {k: items[k].get("挑格") for k in items}, "三欄": three,
            "條件出場必報": {k: items[k].get("條件出場必報") for k in items}, "結果句": sent,
            "敏感度_ret50": "；".join("%s %s" % (k, items[k].get("ret50標籤")) for k in items),
            "偏離": ["換股簿（名單全買 1/N）⇒ 8 槽等權抽籤；N 讀成名單長度（G2）", "M3 對 0050 月報酬 ⇒ 對 ^SP500TR 月報酬", "M4 年化因子 √245 ⇒ √252；覆蓋層疊在 8 槽引擎權益上",
                   "營量 v1 並列（美股無）、早年段 ⛔ 未做；成本 0.585% ⇒ 0.05%", "探索段起點 ＝ 各件所有格都有名單的第一個季換股日（G9）", "假訊號 1,000 次 ⇒ 100 次"],
            "補讀法": ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9", "G10", "M1", "M2", "M3"],
            "先驗紀錄": "台股原登錄先驗：①M0 確認段不合格（七成）⇒ 美股 M0 挑中格對照見各件；②至少一件確認段比 M0 年化高、但合格 ≤ 1 件（六成五）⇒ 比 M0 高的件 %d、合格（兩欄）%d；③M4 回落最淺、年化最低（七成／六成）⇒ 見三欄；④早年 n/a" % (
                sum(1 for k in items if (items[k].get("比單純動能多（確認、合併，年化點）") or -1) > 0), sum(1 for v in labs.values() if v == "合格"))}
    out["卡片"] = card
    out["逐種子檔（repo 外）"] = {"path": p_seeds, "sha256": C.sha256f(p_seeds)}
    out["覆蓋_存活者偏差"] = C.coverage_cached(g["cal"], w0, w1)
    return out


# ═════════════ A3-3 N字底／N型（單筆層）═════════════
NSH, NSC = NP.NSH, NP.NSC
HS3 = (5, 10, 20, 60)
ARMS3 = {"N1M": NSH * 12 * 2, "N1S": NSH * 2, "N2M": NSH * 36 * 2, "N2S": NSH * 2, "TM": 21, "TS": 21}
NM3 = 129


def a3_bad(d):
    b = d["bars"]
    return d["pb"][b] | np.r_[False, np.diff(b) > 1]


class RMQ:
    def __init__(self, x):
        self.t = [np.asarray(x, float)]
        k = 1
        while 2 * k <= len(x):
            p = self.t[-1]; self.t.append(np.fmax(p[:-k], p[k:])); k *= 2

    def q(self, l, r):
        ln = r - l + 1; k = np.floor(np.log2(np.maximum(ln, 1))).astype(int)
        out = np.empty(len(l))
        for kk in np.unique(k):
            m = k == kk; tb = self.t[kk]
            out[m] = np.fmax(tb[l[m]], tb[r[m] - (1 << kk) + 1])
        return out


def first_pass(cb, ev, stop, tgt, lim):
    N = len(ev); out = np.full(N, -1); ist = np.zeros(N, bool)
    todo = np.flatnonzero(ev <= lim); start = ev.astype(int).copy(); Wd = 32
    while len(todo):
        rows = start[todo][:, None] + np.arange(Wd)[None, :]
        inb = rows <= lim[todo][:, None]
        Cw = cb[np.minimum(rows, len(cb) - 1)]
        hs = inb & (Cw < stop[todo][:, None]); ht = inb & (Cw >= tgt[todo][:, None])
        trig = hs | ht
        has = trig.any(1); f = trig.argmax(1)
        idx = todo[has]; out[idx] = start[idx] + f[has]; ist[idx] = ht[has, f[has]]
        rem = (~has) & (start[todo] + Wd <= lim[todo])
        nxt = todo[rem]; start[nxt] += Wd; todo = nxt
        Wd = min(Wd * 2, 4096)
    return out, ist


def a3_exits(d, b, cb, ob, bad, ev, stop, tgt, rmq):
    """主臂（無時間上限）＋原文 H 版。ev：進場根序號。"""
    g = G; w1 = g["w1"]; nb = len(cb)
    kE = int(np.searchsorted(b, w1, side="right")) - 1
    bp = np.flatnonzero(bad)
    j = np.searchsorted(bp, ev, side="right")
    kb = np.where(j < len(bp), bp[np.minimum(j, max(len(bp) - 1, 0))] if len(bp) else nb, nb)
    lim = np.minimum(kb - 1, kE)
    jt, ist = first_pass(cb, ev, stop, tgt, lim)
    hit = jt >= 0; nx = hit & (jt + 1 <= lim)
    xb = np.where(nx, jt + 1, np.where(hit, jt, lim)); pt = np.where(nx, 0, 1)
    kind = np.where(hit, np.where(ist, 1, 0), np.where((lim == kb - 1) & (kb < nb) & (lim < kE), 3, 2))
    po = ob[xb]; po = np.where(np.isfinite(po) & (po > 0), po, cb[xb])
    price = np.where(pt == 0, po, cb[xb])
    R = price / ob[ev] - 1.0
    ET = np.where(pt == 0, b[xb] - 0.5, b[xb].astype(float))
    hold = b[xb] - b[ev]
    peak = price / rmq.q(ev, xb) - 1.0
    main = {"x": b[xb].astype(np.int32), "pt": pt.astype(np.int8), "R": R, "ET": ET, "hold": hold.astype(np.int32), "peak": peak.astype(np.float32), "kind": kind.astype(np.int8)}
    t = b[ev] - 1
    Hv = {}
    for H in HS3:
        kH = ev + H - 1
        okH = (kH < nb) & (t + H <= w1)
        kHc = np.minimum(kH, nb - 1)
        okH &= (b[kHc] == t + H)
        # (ev, kH] 內無壞根：kb ＞ kH
        okH &= kb > kH
        early = (jt >= 0) & (jt <= kH - 1)
        xh = np.minimum(np.where(early, jt + 1, kHc), nb - 1)        # 不定義的 H（okH 假）只防越界、值不用
        poh = ob[xh]; poh = np.where(np.isfinite(poh) & (poh > 0), poh, cb[xh])
        Rh = np.where(early, poh, cb[kHc]) / ob[ev] - 1.0
        ETh = np.where(early, b[xh] - 0.5, (t + H).astype(float))
        Hv[H] = {"ok": okH, "R": np.where(okH, Rh, np.nan), "ET": ETh}
    return main, Hv


def _a3_stage1(sid):
    g = G; d = g["ST"][sid]; b = d["bars"]; nb = len(b); w0, w1 = g["w0"], g["w1"]; n = g["n"]
    if nb < 81:
        return sid, None
    ob, hb, lb, cb = d["O"][b], d["H"][b], d["L"][b], d["C"][b]
    vb0 = np.nan_to_num(d["V"][b])
    bad = a3_bad(d)
    i0 = int(np.searchsorted(b, max(w0 - 120, 0)))
    mem, valid, opens = d["member"], d["valid"], d["opens"]
    rmq = RMQ(cb)
    f5c = g["f5c"][sid]
    out = {}
    keys = []
    infos = []

    def evfilter(t):
        t = np.asarray(t, int)
        ok = (t >= w0) & (t <= w1 - 1)
        tc = np.clip(t, 0, n - 2)
        ok &= mem[tc] & valid[tc] & valid[tc + 1] & np.isfinite(opens[tc + 1]) & (np.nan_to_num(opens[tc + 1]) > 0)
        return ok
    # ── N字底
    cands = NP.ndb_candidates(hb, lb, max(i0, 40))
    ND = NP.ndb_scan(cb, hb, lb, cands)
    if len(ND):
        X = np.array(ND, dtype=np.float64).reshape(-1, 11)
        Z = {"nd": X, "v": vb0, "bad": bad, "shchg": np.zeros(nb, bool), "l": lb, "idx": b}
        T = NP.ndb_table(Z)
        hpos = X[:, 2].astype(int)
        tgt = T["B"] + (T["B"] - T["L"])
        for typ, tcol, okc, stops in (("1", "t1", "ok1", ("plo1", "L")), ("2", "t2", "ok2", ("plo2", "L"))):
            tt = T[tcol]
            m = (tt >= 0) & T[okc]
            m[m] = evfilter(tt[m])
            p = np.flatnonzero(m)
            if not len(p):
                continue
            t = tt[p].astype(int); ev = np.searchsorted(b, t + 1)
            rec = {"sc": T["sc"][p].astype(np.int16), "i": T["i"][p].astype(np.int32), "d1": T["d1"][p], "r1": T["r1"][p], "r2": T["r2"][p], "r3": T["r3"][p],
                   "r4": T["r4"][p], "t": t.astype(np.int32), "m4": d["m4"][t], "m5": d["m5"][t]}
            a0 = b[np.maximum(hpos[p] - NP.PRE, 0)]
            for v, sk in enumerate(stops):
                st = T[sk][p] if sk != "L" else T["L"][p]
                mn, Hv = a3_exits(d, b, cb, ob, bad, ev, st, tgt[p], rmq)
                rec["v%d_stop" % v] = st; rec["tgt"] = tgt[p]
                for q, val in mn.items():
                    rec["v%d_%s" % (v, q)] = val
                rec["v%d_f50" % v] = cntv(f5c, a0, mn["x"]) > 0
                for H in HS3:
                    rec["v%d_H%d_ok" % (v, H)] = Hv[H]["ok"]; rec["v%d_H%d_R" % (v, H)] = Hv[H]["R"]; rec["v%d_H%d_ET" % (v, H)] = Hv[H]["ET"]
                keys.append((t.astype(np.int64) * n + mn["x"]) * 2 + mn["pt"])
                infos.append(np.column_stack([np.full(len(t), int(typ)), np.full(len(t), v), t, mn["hold"], mn["kind"], mn["peak"], d["m4"][t], d["m5"][t]]))
            out["N" + typ] = rec
    # ── N型
    F = NP.red_flags(cb, ob, hb, lb)
    NW = NP.nwave_scan(cb, hb, lb, vb0, F, max(i0, 1))
    if len(NW):
        Xw = np.array(NW, dtype=np.float64).reshape(-1, 5)
        r, wi, res, kf = (Xw[:, q].astype(int) for q in range(4)); viol = Xw[:, 4].astype(bool)
        cbb = np.r_[0, np.cumsum(bad)]
        ok = ~NP.win_flag(cbb, r - 2, kf) & (res == 1)
        t = b[kf]
        ok &= evfilter(t)
        p = np.flatnonzero(ok)
        if len(p):
            t = t[p].astype(int); ev = np.searchsorted(b, t + 1)
            st = lb[r[p]]
            mn, Hv = a3_exits(d, b, cb, ob, bad, ev, st, np.full(len(p), np.inf), rmq)
            rec = {"r": r[p].astype(np.int32), "wi": wi[p].astype(np.int8), "viol": viol[p], "F": F[r[p]], "t": t.astype(np.int32), "m4": d["m4"][t], "m5": d["m5"][t],
                   "v0_stop": st, "tgt": np.full(len(p), np.inf)}
            for q, val in mn.items():
                rec["v0_" + q] = val
            a0 = b[np.maximum(r[p] - 1, 0)]
            rec["v0_f50"] = cntv(f5c, a0, mn["x"]) > 0
            for H in HS3:
                rec["v0_H%d_ok" % H] = Hv[H]["ok"]; rec["v0_H%d_R" % H] = Hv[H]["R"]; rec["v0_H%d_ET" % H] = Hv[H]["ET"]
            keys.append((t.astype(np.int64) * n + mn["x"]) * 2 + mn["pt"])
            infos.append(np.column_stack([np.full(len(t), 3), np.zeros(len(t)), t, mn["hold"], mn["kind"], mn["peak"], d["m4"][t], d["m5"][t]]))
            out["NT"] = rec
    if not out:
        return sid, None
    flat = {}
    for grp, rec in out.items():
        for q, val in rec.items():
            flat[grp + "__" + q] = val
    np.savez(os.path.join(WK, "a3ev", sid + ".npz"), **flat)
    ky = np.unique(np.concatenate(keys)) if keys else np.zeros(0, np.int64)
    info = np.concatenate(infos) if infos else np.zeros((0, 8))
    return sid, (ky, info)


def _a3_init(lim):
    setup(lim)


def a3_peers(allkeys):
    """N5：基準② 同十分位加總（主臂 (t, x, 價別) ＋ H 版 (t, t＋H, 收盤)）。"""
    g = G; ST = g["ST"]; sids = g["sids"]; n = g["n"]; w0, w1 = g["w0"], g["w1"]
    O = np.column_stack([ST[s]["O"] for s in sids]); V = np.column_stack([ST[s]["valid"] for s in sids])
    okO = V & (np.nan_to_num(O) > 0)
    CF = np.column_stack([ST[s]["closes"] for s in sids])
    PXo = np.where(okO, O, CF)
    PB = np.column_stack([ST[s]["pb"] for s in sids]); CS = np.cumsum(PB.astype(np.int64), axis=0)
    MEM = np.column_stack([ST[s]["member"] for s in sids])
    with np.errstate(invalid="ignore", divide="ignore"):
        r20 = np.full_like(CF, np.nan); r20[20:] = CF[20:] / CF[:-20] - 1.0
    r20[~V] = np.nan
    DEC = np.full((n, len(sids)), -1, np.int8)
    for t in range(w0, w1):
        pop = MEM[t] & V[t] & okO[t + 1] & np.isfinite(r20[t]) & ((CS[min(t + 5, n - 1)] - CS[t]) == 0)
        if pop.sum() < 10:
            continue
        x = r20[t, pop]; rk = pd.Series(x).rank(method="first").to_numpy(); mm = len(x)
        dec = ((10 * (rk - 1))[:, None] > (np.arange(1, 10) * (mm - 1))[None, :]).sum(axis=1)
        DEC[t, np.flatnonzero(pop)] = dec.astype(np.int8)
    K = np.unique(allkeys)
    tt = (K // 2) // n; xx = (K // 2) % n; pt = K % 2
    S2 = np.zeros((len(K), 10)); C2 = np.zeros((len(K), 10), np.int32); SA = np.zeros(len(K)); CA = np.zeros(len(K), np.int32)
    bounds = np.r_[0, np.flatnonzero(np.diff(tt)) + 1, len(K)]
    for a_, b_ in zip(bounds[:-1], bounds[1:]):
        t = int(tt[a_]); dec = DEC[t]; pop = dec >= 0
        if not pop.any():
            continue
        e = t + 1; xs = xx[a_:b_]; ps = pt[a_:b_]
        P = np.where(ps[:, None] == 0, PXo[xs], CF[xs])
        with np.errstate(invalid="ignore", divide="ignore"):
            r = P / O[e][None, :] - 1.0
        msk = pop[None, :] & ((CS[xs] - CS[e][None, :]) == 0) & np.isfinite(r)
        oh = np.zeros((len(sids), 10)); oh[np.flatnonzero(pop), dec[pop]] = 1.0
        rz = np.where(msk, r, 0.0)
        S2[a_:b_] = rz @ oh; C2[a_:b_] = (msk.astype(float) @ oh).astype(np.int32)
        SA[a_:b_] = rz.sum(1); CA[a_:b_] = msk.sum(1)
    return K, S2, C2, SA, CA, DEC


def _x2(sid, si, t, x, pt, R, PT):
    """事件 ⇒ X2（N5；扣自己）。"""
    K, S2, C2 = PT["K"], PT["S2"], PT["C2"]
    g = G; n = g["n"]; d = g["ST"][sid]
    key = (t.astype(np.int64) * n + x) * 2 + pt
    pos = np.searchsorted(K, key)
    pos = np.minimum(pos, len(K) - 1)
    found = K[pos] == key
    dq = PT["DEC"][t, si].astype(int)
    e = t + 1
    O = d["O"]; okO = d["valid"] & (np.nan_to_num(O) > 0)
    PXo = np.where(okO, O, d["closes"])
    Pself = np.where(pt == 0, PXo[x], d["closes"][x])
    with np.errstate(invalid="ignore", divide="ignore"):
        rs = Pself / O[e] - 1.0
    pbc = G["pbc"][sid]
    selfin = (dq >= 0) & ((pbc[x] - pbc[e]) == 0) & np.isfinite(rs)
    dd = np.maximum(dq, 0)
    s2 = S2[pos, dd] - np.where(selfin, rs, 0.0); c2 = C2[pos, dd] - selfin
    with np.errstate(invalid="ignore", divide="ignore"):
        X2 = np.where(found & (dq >= 0) & (c2 >= 1), R - s2 / np.maximum(c2, 1), np.nan)
    return X2


def _acc_put(A, arm, cf, col, mon, X2, R, ncols, nval):
    g = np.isfinite(X2) & (mon >= 0)
    if not g.any():
        return
    base = (cf[g].astype(np.int64) * ncols + col) * NM3 + mon[g]
    np.add.at(A[arm], (base, 0), 1.0); np.add.at(A[arm], (base, 1), X2[g])
    if nval > 2:
        np.add.at(A[arm], (base, 2), R[g])


def _dedup_put(A, arm, cf, ev, t, key_i, ET, X2, R, m4, m5, mon, layers):
    """同格同訊號日取 key 最大 ⇒ 依格去重（台股 R13）⇒ 累加。layers：主（3 欄）／r50／H。"""
    if not len(cf):
        return
    o = np.lexsort((key_i[ev], t[ev], cf))
    cf, ev = cf[o], ev[o]; tt = t[ev]
    last = np.r_[(cf[1:] != cf[:-1]) | (tt[1:] != tt[:-1]), True]
    cf, ev, tt = cf[last], ev[last], tt[last]
    ok = np.flatnonzero(np.isfinite(R[ev]))
    if not len(ok):
        return
    kept = ok[NP.chains_dedup(cf[ok], tt[ok], ET[ev[ok]])]
    e2 = ev[kept]; c2 = cf[kept]; mm = mon[tt[kept]]
    if layers == "main":
        _acc_put(A, arm, c2, 0, mm, X2[e2], R[e2], 3, 3)
        s4 = m4[e2]; s5 = m5[e2]
        _acc_put(A, arm, c2[s4], 1, mm[s4], X2[e2][s4], R[e2][s4], 3, 3)
        _acc_put(A, arm, c2[s5], 2, mm[s5], X2[e2][s5], R[e2][s5], 3, 3)
    elif layers == "r50":
        _acc_put(A, arm, c2, 0, mm, X2[e2], R[e2], 2, 2)
        s4 = m4[e2]
        _acc_put(A, arm, c2[s4], 1, mm[s4], X2[e2][s4], R[e2][s4], 2, 2)
    else:                         # ("H", q)
        _acc_put(A, arm, c2, layers[1], mm, X2[e2], R[e2], 4, 2)


def _a3_stage3(sub, k, lim):
    setup(lim)
    g = G; sids = g["sids"]; six = {s: i for i, s in enumerate(sids)}; n = g["n"]
    z = np.load(os.path.join(WK, "a3_peers.npz"))
    PT = {q: z[q] for q in ("K", "S2", "C2", "SA", "CA", "DEC")}
    mon = g["mon"].copy(); mon[: g["w0"]] = -1; mon[g["w1"] + 1:] = -1
    A = {}
    for a, nc in ARMS3.items():
        A[a] = np.zeros((nc * 3 * NM3, 3)); A[a + "_r50"] = np.zeros((nc * 2 * NM3, 2)); A[a + "_H"] = np.zeros((nc * 4 * NM3, 2))
    D1S = np.array(NP.D1S); V1 = np.array(NP.V1); V2 = np.array(NP.V2); V3 = np.array(NP.V3); V4 = np.array(NP.V4)
    for c_, sid in enumerate(sub):
        fp = os.path.join(WK, "a3ev", sid + ".npz")
        if not os.path.exists(fp):
            continue
        zz = np.load(fp); si = six[sid]
        grps = sorted(set(q.split("__")[0] for q in zz.files))
        for grp in grps:
            E = {q.split("__", 1)[1]: zz[q] for q in zz.files if q.startswith(grp + "__")}
            t = E["t"].astype(int); m4 = E["m4"].astype(bool); m5 = E["m5"].astype(bool)
            nv = 2 if grp != "NT" else 1
            for v in range(nv):
                x = E["v%d_x" % v].astype(int); pt = E["v%d_pt" % v].astype(int); R = E["v%d_R" % v]; ET = E["v%d_ET" % v]
                X2 = _x2(sid, si, t, x, pt, R, PT)
                f50 = E["v%d_f50" % v]
                XH = {}
                for q, H in enumerate(HS3):
                    okH = E["v%d_H%d_ok" % (v, H)]
                    RH = E["v%d_H%d_R" % (v, H)]
                    th = np.where(okH, t, 0); xh = np.where(okH, t + H, 0)
                    X2H = np.where(okH, _x2(sid, si, th, xh, np.ones(len(t), int), RH, PT), np.nan)
                    XH[q] = (RH, E["v%d_H%d_ET" % (v, H)], X2H)
                if grp in ("N1", "N2"):
                    keyi = E["i"]; sc = E["sc"].astype(int)
                    D1m = E["d1"][:, None] >= D1S[None, :]
                    A1 = E["r1"][:, None] < V1[None, :]; A2_ = E["r2"][:, None] > V2[None, :]; A3_ = E["r3"][:, None] < V3[None, :]
                    with np.errstate(invalid="ignore"):
                        A4_ = E["r4"][:, None] > V4[None, :]
                    sel = [("S", NP.members(D1m), lambda ix: ix[1] * NSC + sc[ix[0]])]
                    if grp == "N1":
                        sel.append(("M", NP.members(D1m, A1, A2_, A3_), lambda ix: (ix[1] * NSC + sc[ix[0]]) * 12 + (ix[2] * 3 + ix[3]) * 2 + ix[4]))
                    else:
                        sel.append(("M", NP.members(D1m, A1, A2_, A3_, A4_), lambda ix: (ix[1] * NSC + sc[ix[0]]) * 36 + ((ix[2] * 3 + ix[3]) * 2 + ix[4]) * 3 + ix[5]))
                    for arm_s, ix, fcell in sel:
                        ev = ix[0]
                        if not len(ev):
                            continue
                        cf = fcell(ix).astype(np.int64) * 2 + v
                        arm = grp + arm_s
                        _dedup_put(A, arm, cf, ev, t, keyi, ET, X2, R, m4, m5, mon, "main")
                        nf = ~f50[ev]
                        _dedup_put(A, arm + "_r50", cf[nf], ev[nf], t, keyi, ET, X2, R, m4, m5, mon, "r50")
                        for q in range(len(HS3)):
                            RH, ETH, X2H = XH[q]
                            _dedup_put(A, arm + "_H", cf, ev, t, keyi, ETH, X2H, RH, m4, m5, mon, ("H", q))
                else:
                    keyi = E["r"]; Fr = E["F"]; wi = E["wi"].astype(int); viol = E["viol"].astype(bool)
                    ev, rd = np.nonzero(Fr)
                    cf = (rd * 3 + wi[ev]).astype(np.int64)
                    for arm, mm_ in (("TS", np.ones(len(ev), bool)), ("TM", ~viol[ev])):
                        e_, c_2 = ev[mm_], cf[mm_]
                        _dedup_put(A, arm, c_2, e_, t, keyi, ET, X2, R, m4, m5, mon, "main")
                        nf = ~f50[e_]
                        _dedup_put(A, arm + "_r50", c_2[nf], e_[nf], t, keyi, ET, X2, R, m4, m5, mon, "r50")
                        for q in range(len(HS3)):
                            RH, ETH, X2H = XH[q]
                            _dedup_put(A, arm + "_H", c_2, e_, t, keyi, ETH, X2H, RH, m4, m5, mon, ("H", q))
        if c_ % 100 == 0:
            print("[A3-3 stage3 #%d] %d／%d" % (k, c_, len(sub)), flush=True)
    np.savez(os.path.join(WK, "a3_acc_%d.npz" % k), **A)


def judge3(Nm, mu, se, dd, sed, Ns, z=Z95):
    Nm, mu, se, dd, sed, Ns = (np.asarray(a).ravel() for a in (Nm, mu, se, dd, sed, Ns))
    el = Nm >= 30; elD = el & (Ns >= 30)
    with np.errstate(invalid="ignore"):
        lo = mu - z * se - COST; dlo = dd - z * sed
    pas = el & (lo > 0); dpas = elD & (dlo > 0)
    return {"格": int(len(Nm)), "可判格": int(el.sum()), "站_過": int(pas.sum()), "站_過半": bool(el.sum() > 0 and pas.sum() * 2 > el.sum()),
            "站_點估計正": int((el & (mu - COST > 0)).sum()), "量_可判格": int(elD.sum()), "量_過": int(dpas.sum()),
            "量_過半": bool(elD.sum() > 0 and dpas.sum() * 2 > elD.sum()), "量_點估計正": int((elD & (dd > 0)).sum()),
            "站_全部格版_過半": bool(((Nm >= 2) & (lo > 0)).sum() * 2 > len(Nm)),
            "事件中位": float(np.median(Nm[el])) if el.any() else 0.0, "X2中位": float(np.nanmedian(mu[el])) if el.any() else None,
            "M−S中位": float(np.nanmedian(dd[elD])) if elD.any() else None}


def a3_stats(A):
    exp_m = np.zeros(NM3, bool); exp_m[:72] = True; conf_m = ~exp_m
    J = {}
    groups = (("甲1", "N1M", "N1S", 12), ("甲2", "N2M", "N2S", 36), ("N型", "TM", "TS", None))
    for gname, am, as_, nv in groups:
        for layer, ncols, colnames in (("", 3, COLS), ("_r50", 2, COLS[:2])):
            for cI, col in enumerate(colnames):
                for sn, sm in (("探索", exp_m), ("確認", conf_m)):
                    if layer == "_r50" and sn == "探索":
                        continue
                    nval = 3 if layer == "" else 2
                    M = A[am + layer].reshape(-1, ncols, NM3, nval)[:, cI][:, sm]
                    S = A[as_ + layer].reshape(-1, ncols, NM3, nval)[:, cI][:, sm]
                    for zn, z in (("", Z95), ("_Bonf", ZB6)):
                        if zn and layer:
                            continue
                        J[(gname, col + layer, sn + zn)] = _jg(M, S, nv, z)
        # H 版（合併）
        for q, H in enumerate(HS3):
            for sn, sm in (("探索", exp_m), ("確認", conf_m)):
                M = A[am + "_H"].reshape(-1, 4, NM3, 2)[:, q][:, sm]
                S = A[as_ + "_H"].reshape(-1, 4, NM3, 2)[:, q][:, sm]
                J[(gname, "合併_H%d" % H, sn)] = _jg(M, S, nv, Z95)
    return J


def _jg(M, S, nv, z):
    nM, sM = M[..., 0], M[..., 1]; nS, sS = S[..., 0], S[..., 1]
    if nv is not None:                          # N字底：M (216, nv, 2, months)；S (216, 2, months)
        nM = nM.reshape(NSH, nv, 2, -1); sM = sM.reshape(NSH, nv, 2, -1)
        nS = nS.reshape(NSH, 1, 2, -1); sS = sS.reshape(NSH, 1, 2, -1)
        nSb = np.broadcast_to(nS, nM.shape); sSb = np.broadcast_to(sS, sM.shape)
    else:
        nSb, sSb = nS, sS
    Nm, mu, se = NP.cstat(nM, sM); Ns, muS, seS = NP.cstat(nSb, sSb)
    _, _, dd, sed = NP.dstat(nM, sM, nSb, sSb)
    return judge3(Nm, mu, se, dd, sed, Ns, z)


def run_a3(procs):
    g = G; lim = g["lim"]
    os.makedirs(os.path.join(WK, "a3ev"), exist_ok=True)
    for f in os.listdir(os.path.join(WK, "a3ev")):
        os.remove(os.path.join(WK, "a3ev", f))
    t0 = time.time()
    keys = []; infos = []; nst = 0
    with Pool(procs, initializer=_a3_init, initargs=(lim,)) as pool:
        for i, (sid, r) in enumerate(pool.imap_unordered(_a3_stage1, g["sids"], chunksize=4)):
            if r is not None:
                keys.append(r[0]); infos.append(r[1]); nst += 1
            if (i + 1) % 100 == 0:
                log("A3-3 stage1 %d／%d %.0fs" % (i + 1, len(g["sids"]), time.time() - t0))
    allk = np.unique(np.concatenate(keys)) if keys else np.zeros(0, np.int64)
    # H 版的基準鍵
    hk = []
    for t in range(g["w0"], g["w1"]):
        for H in HS3:
            if t + H <= g["w1"]:
                hk.append((t * g["n"] + t + H) * 2 + 1)
    allk = np.unique(np.r_[allk, np.array(hk, np.int64)])
    log("A3-3 stage1 完成 %d 檔有事件、基準鍵 %d %.0fs" % (nst, len(allk), time.time() - t0))
    K, S2, C2, SA, CA, DEC = a3_peers(allk)
    np.savez(os.path.join(WK, "a3_peers.npz"), K=K, S2=S2, C2=C2, SA=SA, CA=CA, DEC=DEC)
    log("A3-3 基準② 完成 %.0fs" % (time.time() - t0))
    INFO = np.concatenate(infos) if infos else np.zeros((0, 8))
    subs = [g["sids"][k::procs] for k in range(procs)]
    ps = [Process(target=_a3_stage3, args=(sb, k, lim)) for k, sb in enumerate(subs)]
    for p in ps:
        p.start()
    for p in ps:
        p.join()
    assert all(p.exitcode == 0 for p in ps), [p.exitcode for p in ps]
    A = None
    for k in range(procs):
        z = dict(np.load(os.path.join(WK, "a3_acc_%d.npz" % k)))
        A = z if A is None else {a: A[a] + z[a] for a in A}
        os.remove(os.path.join(WK, "a3_acc_%d.npz" % k))
    pa = os.path.join(WK, "a3_acc.npz"); np.savez(pa, **A)
    log("A3-3 累加完成 %.0fs" % (time.time() - t0))
    J = a3_stats(A)
    return a3_report(J, INFO, pa)


def a3_report(J, INFO, pa):
    g = G
    Q = {}
    for gname in ("甲1", "甲2", "N型"):
        for qn, qk in (("站得住", "站_過半"), ("量能有加分", "量_過半")):
            jc, j4 = J[(gname, "合併", "確認")], J[(gname, "只400", "確認")]
            elk = "可判格" if qk == "站_過半" else "量_可判格"
            if jc[elk] == 0:
                lab = "不可判定（合併可判格 0）"
            elif j4[elk] == 0:
                lab = "事後擴母體" if jc[qk] else "不合格"
                lab += "（只 400 依構造不可判；最多事後擴母體）"
            else:
                lab = C.label_ev("結果②" if jc[qk] else "x", "結果②" if j4[qk] else "x")
            r50c, r504 = J[(gname, "合併_r50", "確認")], J[(gname, "只400_r50", "確認")]
            lab50 = C.label_ev("結果②" if r50c[qk] else "x", "結果②" if r504[qk] else "x")
            Q["%s｜%s" % (gname, qn)] = {"標籤": lab, "合併": jc[qk], "只400": j4[qk], "ret50標籤": lab50,
                                       "原文雙段版（描述）": {col: bool(J[(gname, col, "確認")][qk] and J[(gname, col, "探索")][qk]) for col in ("合併", "只400")},
                                       "Bonferroni（N＝6）": {col: J[(gname, col, "確認_Bonf")][qk] for col in ("合併", "只400")}}
    # 結果句的「量能有差但型態測不出」
    for gname in ("甲1", "甲2", "N型"):
        s, v = Q["%s｜站得住" % gname], Q["%s｜量能有加分" % gname]
        if s["標籤"].startswith("不合格") and not v["標籤"].startswith("不合格") and not v["標籤"].startswith("不可判定"):
            v["註"] = "量能條件有差，但型態本身測不出"
    labs = {k: v["標籤"] for k, v in Q.items()}
    order = ["合格", "事後擴母體", "不合格"]
    best = min(labs.values(), key=lambda s: next((i for i, o in enumerate(order) if s.startswith(o)), 9))
    if best.startswith("合格"):
        fl = "合格（%s）" % "、".join(k for k, v in labs.items() if v.startswith("合格"))
    elif best.startswith("事後擴母體"):
        fl = "事後擴母體（%s）" % "、".join(k for k, v in labs.items() if v.startswith("事後擴母體"))
    elif all(v.startswith("不可判定") for v in labs.values()):
        fl = "不可判定"
    else:
        fl = "不合格"
    # C6（事件為單位，不分格、不去重；同一檔同 (t, 出場) 只算一次）
    c6x = {}
    if len(INFO):
        df = pd.DataFrame(INFO, columns=["typ", "v", "t", "hold", "kind", "peak", "m4", "m5"])
        df = df.drop_duplicates(["typ", "v", "t", "hold", "kind", "peak"])
        for typ, nm in ((1, "甲1"), (2, "甲2"), (3, "N型")):
            for v in ((0, 1) if typ != 3 else (0,)):
                sub = df[(df["typ"] == typ) & (df["v"] == v) & (df["t"] >= g["c0"])]
                if not len(sub):
                    continue
                h = sub["hold"].to_numpy(float); kd = sub["kind"].to_numpy(int)
                c6x["%s_%s（確認段事件）" % (nm, ("回測低點停損", "前低停損")[v] if typ != 3 else "長紅低點停損")] = {
                    "事件": int(len(sub)), "持有天數平均": float(h.mean()), "中位": float(np.median(h)), "p10": float(np.percentile(h, 10)), "p90": float(np.percentile(h, 90)),
                    "最長": float(h.max()), "窗尾仍持有件數": int((kd == 2).sum()), "離頂距離中位": float(np.median(sub["peak"])),
                    "出場方式比例": {"停損": float((kd == 0).mean()), "目標價": float((kd == 1).mean()), "窗尾／資料結束": float((kd == 2).mean()), "斷點前結算": float((kd == 3).mean())}}
    three = {}
    for col in COLS:
        parts = []
        for gname in ("甲1", "甲2", "N型"):
            j = J[(gname, col, "確認")]
            parts.append("%s 站 %d／%d 格過（X2 中位 %s）、量 %d／%d" % (gname, j["站_過"], j["可判格"], pct(j["X2中位"]), j["量_過"], j["量_可判格"]))
        three[col] = ("（描述、⛔ 不判）" if col == "只500" else "") + "確認段：" + "；".join(parts)
    sent = "N字底與 N型走法（照作者原文含量能；停損或目標價先到先出、無時間上限）：" + "；".join("%s %s" % (k, v) for k, v in labs.items()) + "。"
    for gname in ("甲1", "甲2", "N型"):
        if Q["%s｜量能有加分" % gname].get("註"):
            sent += " %s：量能條件有差，但型態本身測不出。" % gname
    sent += " %s；%s；%s。" % (C.IDEA, C.NO_EARLY, C.SURV)
    pri = {"①N字底主臂站得住：否（七成）": "甲1 %s、甲2 %s" % (labs["甲1｜站得住"], labs["甲2｜站得住"]),
           "②N字底量能有加分：否（六成五）": "甲1 %s、甲2 %s" % (labs["甲1｜量能有加分"], labs["甲2｜量能有加分"]),
           "③放棄組 ≥ 主臂（六成）": "放棄組未做（描述臂）", "④N型主臂站得住：否（六成五）": labs["N型｜站得住"], "⑤N型代理臂：P 臂拿掉（退化）": "n/a"}
    card = {"件": "A3-3", "名稱": NAME["A3-3"], "台股原登錄": "%s（%s）" % TWREG["A3-3"],
            "出場型": "① 條件（seq2：停損或目標價先到先出、⛔ 無時間上限、窗尾結算；原文 H{5,10,20,60} 降描述）", "N": 6, "標籤": fl, "格標籤": labs,
            "判定格": "確認段 ×（甲1 216×12×2、甲2 216×36×2、N型 21）格全報、過半判（停損兩版當格軸）", "三欄": three, "條件出場必報": c6x, "結果句": sent,
            "敏感度_ret50": "；".join("%s %s" % (k, v["ret50標籤"]) for k, v in Q.items()),
            "偏離": ["單筆層（事件研究）照原文；主臂無 H（seq2）", "成本 0.585% ⇒ 0.05%；基準不付成本", "母體 W1 eligible ⇒ 合併母體；量 原始股數 ⇒ Yahoo 拆股調整量",
                   "P 代理臂（法人）拿掉 ⇒ 退化（N 28 ⇒ 6）；隔天鎖漲停、處置 美股無", "早年段拿掉 ⇒ 只看確認段＋兩母體；原文雙段版另報",
                   "持有路徑碰到壞根 ⇒ 斷點前一根收盤結算（N4）", "放棄組 A、目標價碰到 vs 隨機同距離、現實版滑價 ⛔ 未做（描述臂）"],
            "補讀法": ["G1", "G6", "N1", "N2", "N3", "N4", "N5", "N6", "N7", "N8"], "先驗紀錄": pri}
    out = {"卡片": card, "讀法寫死": READ_TS, "登錄": C.REG, "資料commit": g["meta"]["data_commit"], "兩問": Q,
           "判定明細": {"|".join(k): v for k, v in J.items()}, "成本": COST, "Bonferroni_z": ZB6,
           "累加器（repo 外）": {"path": pa, "sha256": C.sha256f(pa)}, "覆蓋_存活者偏差": C.coverage_cached(g["cal"], g["w0"], g["w1"])}
    return out


# ═════════════ run／check ═════════════
RUNNERS = {"A3-3": run_a3, "A3-10": run_a10, "A3-11": run_a11, "A3-12": run_a12}


def run(procs=2, lim=None, items=None):
    setup(lim)
    outd = C.OUT if lim is None else os.path.join(WK, "lim%d" % lim)
    os.makedirs(outd, exist_ok=True)
    res = {}
    for it in (items or list(RUNNERS)):
        t0 = time.time(); log("===== %s 開始（procs %d、limit %s）=====" % (it, procs, lim))
        out = RUNNERS[it](procs)
        out["耗時秒"] = round(time.time() - t0, 1)
        C.jdump(out, os.path.join(outd, "%s.json" % it))
        log("===== %s 完成：%s（%.0fs）=====" % (it, out["卡片"]["標籤"], time.time() - t0))
        res[it] = out["卡片"]["標籤"]
    return res


# ── check：獨立寫法（不呼叫上面算報酬／建訊號的函式；只共用讀檔快取與引擎）──
def _ind_ema(c, L):
    a = 2.0 / (L + 1); out = np.empty(len(c)); out[0] = c[0]
    for i in range(1, len(c)):
        out[i] = a * c[i] + (1 - a) * out[i - 1]
    return out


def _ind_a10_cell(B, k, L, col, s0, s1):
    g = G; ST = g["ST"]; rows = []
    for sid in g["sids"]:
        d = ST[sid]; v = d["valid"]; b = [i for i in range(len(v)) if v[i]]
        if len(b) < 25:
            continue
        c = [d["C"][i] for i in b]; h = [d["H"][i] for i in b]; o = [d["O"][i] for i in b]; vv = [d["V"][i] for i in b]
        ema = _ind_ema(np.array(c), L)
        for i in range(max(B, 20), len(b)):
            if i < 3 * L or not (c[i] > max(h[i - B:i]) and c[i] > o[i]) or not (c[i] >= ema[i]):
                continue
            va = sum(vv[i - 20:i]) / 20.0
            if not (va > 0 and vv[i] > k * va):
                continue
            t = b[i]; e = t + 1
            fl = d["member"] if col == "合併" else d["m4"]
            if not (s0 <= e <= s1) or not fl[t]:
                continue
            oe = d["opens"][e]
            if not (np.isfinite(oe) and oe > 0):
                continue
            x = None
            for j in range(i + 1, len(b)):
                if b[j] >= e and c[j] < ema[j]:
                    x = b[j] + 1; break
            if x is None or x > s1:
                x = s1; gg = d["closes"][s1] / oe - 1.0; eh = True
            else:
                ox = d["opens"][x]; gg = (ox if (np.isfinite(ox) and ox > 0) else d["closes"][x]) / oe - 1.0; eh = False
            st_ = b[i - max(B, 20)]
            if any(d["pb"][st_:x + 1]):
                continue
            rows.append((sid, e, x, gg, eh))
    return rows


def _ind_engine(rows, s0, s1, seed):
    d = pd.DataFrame(rows, columns=["sid", "entry_pos", "xpos_A3", "g_A3", "eh"]).sort_values(["entry_pos", "sid"], kind="mergesort")
    S_ = C._S
    R11.COST = 0.0005                                     # 美股成本（登錄 seq242：0.05% 來回）
    try:
        out = R11.simulate_mtm(d[["sid", "entry_pos", "xpos_A3", "g_A3"]].reset_index(drop=True), "A3", 8, np.random.default_rng(seed), S_["closes"], S_["opens"], S_["ncal"],
                               return_equity=True, pick=None, d_max=None, queue_days=0, cash_mode="zero", tradable=S_["trad"], delist=S_["dl"])
    finally:
        R11.COST = C.COST
    eq = np.asarray(out["equity"], float); seg = eq[s0:s1 + 1]
    return (seg[-1] / seg[0]) ** (252.0 / len(seg)) - 1


def _seedcsv(name):
    return pd.read_csv(os.path.join(WK, name))


def check_a10():
    g = G; diff = 0; nchk = 0; msg = []
    S = _seedcsv("A3-10_seeds.csv.gz")
    for (B, k, L) in ((20, 2.0, 20), (60, 1.5, 10)):
        for col in ("合併", "只400"):
            rows = _ind_a10_cell(B, k, L, col, g["c0"], g["w1"])
            cag = _ind_engine(rows, g["c0"], g["w1"], C.SEED0)
            key = "|".join(map(str, ("J", col, B, k, L)))
            ref = S[(S["key"] == key) & (S["seed"] == C.SEED0)]["c_確認"]
            nchk += 1
            if not len(ref) or abs(float(ref.iloc[0]) - cag) > 1e-9:
                diff += 1; msg.append("%s 不同：%s vs %s" % (key, cag, ref.tolist()))
    return {"件": "A3-10", "抽樣": nchk, "不同": diff, "說明": "獨立逐根迴圈重建 2 格 × 2 欄的訊號表（EMA 自算遞迴、前 B 根最高、爆量、出場、斷點剔除）、直接呼叫引擎 seed 102000，與主程式逐種子年化比（容差 1e−9）" + ("；" + "；".join(msg) if msg else "")}


def _ind_book(L, mis, s1):
    g = G; ST = g["ST"]; mst = g["mst"]; rows = []
    for j, mi in enumerate(mis):
        for s in L.get(mi, []):
            e = int(mst[mi]); x = None
            for mi2 in mis[j + 1:]:
                if s not in L.get(mi2, []):
                    x = int(mst[mi2]); break
            d = ST[s]; oe = d["opens"][e]
            if not (np.isfinite(oe) and oe > 0):
                continue
            if x is None:
                rows.append((s, e, s1, d["closes"][s1] / oe - 1.0, True)); x = s1
            else:
                ox = d["opens"][x]; rows.append((s, e, x, (ox if (np.isfinite(ox) and ox > 0) else d["closes"][x]) / oe - 1.0, False))
    return rows


def check_a11():
    g = G; diff = 0; nchk = 0; msg = []
    js = json.load(open(os.path.join(C.OUT if g["lim"] is None else os.path.join(WK, "lim%d" % g["lim"]), "A3-11.json"), encoding="utf-8"))
    M = pd.read_pickle(MONTH_PKL); M = M[M["t"].isin(set(g["sids"]))]
    pick = js["T"]["挑格"]
    if pick:
        fam, fq, N = pick.split("_"); N = int(N[1:])
        mis = list(range(len(g["mst"]))) if fq == "月" else [mi for mi in range(len(g["mst"])) if g["cal"][g["mst"][mi]].month in (1, 4, 7, 10)]
        L = {}
        for mi in mis:
            sub = M[(M["mi"] == mi) & (M["m5"] | M["m4"]) & M["rs"].notna()]
            ranked = sorted(zip(sub["rs"], sub["t"], sub["tmpl17"], sub["rev_hi8"]), key=lambda z: (-z[0], z[1]))
            top = set(z[1] for z in ranked[:int(math.ceil(0.3 * len(ranked)))])
            L[mi] = [z[1] for z in ranked if z[1] in top and z[2] == True and (fam == "甲" or z[3] == True)][:N]   # noqa: E712
        rows = [r for r in _ind_book(L, mis, g["w1"]) if not any(g["ST"][r[0]]["pb"][g["ST"][r[0]]["bars"][max(int(np.searchsorted(g["ST"][r[0]]["bars"], r[1])) - 1 - 252, 0)]:r[2] + 1])]
        cag = _ind_engine(rows, g["c0"], g["w1"], C.SEED0)
        S = _seedcsv("A3-11_T_seeds.csv.gz")
        ref = S[(S["key"] == "|".join(map(str, ("T", "合併", fam, fq, N)))) & (S["seed"] == C.SEED0)]["c_確認"]
        nchk += 1
        if not len(ref) or abs(float(ref.iloc[0]) - cag) > 1e-9:
            diff += 1; msg.append("T 不同 %s vs %s" % (cag, ref.tolist()))
    # I：獨立一目＋ATR（逐根迴圈），抽 30 檔與主程式事件比
    rng = np.random.default_rng(7); smp = rng.choice(g["sids"], size=min(30, len(g["sids"])), replace=False)
    mine = []; ref = []
    for sid in smp:
        d = g["ST"][sid]; b = d["bars"]; nb = len(b)
        if nb < 80:
            continue
        c, h, l, o = d["C"][b], d["H"][b], d["L"][b], d["O"][b]
        def mid(i, w):
            return (max(h[i - w + 1:i + 1]) + min(l[i - w + 1:i + 1])) / 2 if i >= w - 1 else np.nan
        cond = np.zeros(nb, bool); okv = np.zeros(nb, bool)
        for i in range(nb):
            if i >= 77:
                tk, kj = mid(i, 9), mid(i, 26); sa = (mid(i - 26, 9) + mid(i - 26, 26)) / 2; sbb = mid(i - 26, 52)
                okv[i] = all(np.isfinite([tk, kj, sa, sbb])); cond[i] = okv[i] and tk > kj * 1.01 and c[i] > c[i - 26] and c[i] > max(sa, sbb)
        tr = [h[0] - l[0]] + [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(1, nb)]
        atr = [np.nan] * nb; atr[13] = float(np.mean(tr[:14]))
        for i in range(14, nb):
            atr[i] = (atr[i - 1] * 13 + tr[i]) / 14
        bad = d["pb"][b]
        for k in range(78, nb - 1):
            if not (cond[k] and okv[k - 1] and not cond[k - 1]) or bad[k] or bad[k - 1] or (k + 1 < nb and bad[k + 1]):
                continue
            t = b[k]
            if not (g["w0"] <= t <= g["w1"] - 1) or not d["member"][t] or b[k + 1] != t + 1:
                continue
            mx = c[k + 1]; x = None
            for j in range(k + 2, nb):
                if bad[j]:
                    x = b[j - 1]; break
                if np.isfinite(atr[j - 1]) and c[j] < mx - 3 * atr[j - 1]:
                    x = b[j + 1] if (j + 1 < nb and not bad[j + 1]) else b[j]; break
                mx = max(mx, c[j])
            x = g["w1"] if (x is None or x > g["w1"]) else int(x)
            mine.append((sid, int(t + 1), x))
    S = _seedcsv("A3-11_I_seeds.csv.gz")
    p = os.path.join(WK, "A3-11_I_trades_k3.csv.gz")
    if os.path.exists(p):
        T_ = pd.read_csv(p)
        T_ = T_[T_["sid"].isin(set(smp))]
        ref = set(zip(T_["sid"], T_["e"], T_["x"]))
        mm = set(mine)
        nchk += len(mm | ref); d_ = len(mm ^ ref); diff += d_
        if d_:
            msg.append("I 事件不同 %d：%s" % (d_, sorted(mm ^ ref)[:5]))
    # D：獨立週 K（pandas groupby）＋ box_machine（台股偵測器）＋ 獨立日線對應（進場／出場日、價別、毛報酬），抽 40 檔與主程式比
    pD = os.path.join(WK, "A3-11_D_trades.csv.gz")
    if os.path.exists(pD):
        TD = pd.read_csv(pD)
        smpD = rng.choice(g["sids"], size=min(40, len(g["sids"])), replace=False)
        cal = g["cal"]; mondays = (cal - pd.to_timedelta(cal.weekday, unit="D")).normalize()
        wid = pd.Series(pd.factorize(mondays)[0])
        for sid in smpD:
            d = g["ST"][sid]; ix = np.flatnonzero(d["valid"])
            if len(ix) < 10:
                continue
            df = pd.DataFrame({"w": wid.to_numpy()[ix], "pos": ix, "h": d["H"][ix], "l": d["L"][ix], "c": d["C"][ix]})
            agg_ = df.groupby("w", sort=True).agg(h=("h", "max"), l=("l", "min"), c=("c", "last"), first=("pos", "first"), last=("pos", "last"))
            if len(agg_) <= 60:
                continue
            wks = agg_.index.to_numpy()
            pbw = set(wid.to_numpy()[np.flatnonzero(d["pb"])].tolist())
            near = np.array([(w in pbw) or (w - 1 in pbw) or (w + 1 in pbw) for w in wks])
            mine = set()
            for bb, s_, top, bot, B_ in LD.box_machine(agg_["h"].to_numpy(), agg_["l"].to_numpy(), agg_["c"].to_numpy(), near, 52):
                ds = int(agg_["last"].iloc[bb])
                if not (g["w0"] <= ds <= g["w1"]) or not d["member"][ds]:
                    continue
                nxt = agg_.index.get_indexer([wks[bb] + 1])[0]
                if nxt < 0:
                    continue
                e = int(agg_["first"].iloc[nxt])
                if e > g["w1"]:
                    continue
                if s_ is None:
                    x = g["w1"]; byc = True
                else:
                    later = ix[ix > int(agg_["last"].iloc[s_])]
                    x, byc = (int(later[0]), False) if (len(later) and later[0] <= g["w1"]) else (g["w1"], True)
                pbs = [p for p in np.flatnonzero(d["pb"]) if e < p <= x]
                if pbs:
                    x = int(ix[ix < pbs[0]][-1]); byc = True
                gg = (d["closes"][x] if byc else d["opens"][x]) / d["opens"][e] - 1
                mine.add((sid, e, x, round(float(gg), 10)))
            ref = set((r.sid, int(r.e), int(r.x), round(float(r.g), 10)) for r in TD[TD["sid"] == sid].itertuples())
            nchk += len(mine | ref); dd_ = len(mine ^ ref); diff += dd_
            if dd_:
                msg.append("D %s 不同 %d" % (sid, dd_))
    return {"件": "A3-11", "抽樣": nchk, "不同": diff, "說明": "T：自 month.pkl 獨立排序重建挑中格名單與訊號列、直接呼叫引擎 seed 102000 比年化；I：30 檔獨立逐根一目三役＋Wilder ATR 移動停損（k3）重算事件（進場、出場日）與主程式事件比；D：40 檔獨立週 K（pandas）＋獨立日線對應（下週首根進、破底週後首根出、壞根前收盤）比進出場日與毛報酬" + ("；" + "；".join(msg[:6]) if msg else "")}


def check_a12():
    g = G; diff = 0; nchk = 0; msg = []
    js = json.load(open(os.path.join(C.OUT if g["lim"] is None else os.path.join(WK, "lim%d" % g["lim"]), "A3-12.json"), encoding="utf-8"))
    S = _seedcsv("A3-12_seeds.csv.gz")
    ST = g["ST"]; sids = g["sids"]; me = g["me"]; ym = g["ym"]; mst = g["mst"]
    for Mk in ("M1", "M3"):
        it = js["四件"][Mk]
        if "挑格" not in it:
            continue
        F, fq, N = it["挑格"].split("_"); F = int(F[1:]); N = int(N[1:])
        mis = list(range(len(mst))) if fq == "月" else [mi for mi in range(len(mst)) if g["cal"][mst[mi]].month in (1, 4, 7, 10)]
        L = {}
        for mi in mis:
            e = int(mst[mi]); m = int(ym[e]); sc = {}
            for s in sids:
                d = ST[s]
                if not d["member"][e]:
                    continue
                vb = np.flatnonzero(d["valid"][:e])
                if not len(vb) or e - vb[-1] > 5:
                    continue
                if Mk == "M1":
                    if (m - 2 - F) not in me or (m - 2) not in me:
                        continue
                    a, b_ = d["closes"][me[m - 2 - F]], d["closes"][me[m - 2]]
                    if np.isfinite(a) and np.isfinite(b_) and a > 0 and b_ > 0:
                        sc[s] = b_ / a - 1
                else:
                    ks = [q for q in range(m - 38, m - 1) if q in me]
                    if len(ks) < 25:
                        continue
                    cs = np.array([d["closes"][me[q]] for q in ks]); bs = np.array([g["bench"][me[q]] for q in ks])
                    y = cs[1:] / cs[:-1] - 1; x = bs[1:] / bs[:-1] - 1; ok = np.isfinite(y) & np.isfinite(x)
                    if ok.sum() < 24 or not np.isfinite(y[-F:]).all():
                        continue
                    Xm = np.column_stack([np.ones(ok.sum()), x[ok]]); bb, *_ = np.linalg.lstsq(Xm, y[ok], rcond=None)
                    res = np.full(len(y), np.nan); res[ok] = y[ok] - Xm @ bb; sd = np.nanstd(res[ok], ddof=1)
                    if sd > 0:
                        sc[s] = float(np.sum(res[-F:]) / sd)
            order = sorted(sc, key=lambda s: (-sc[s], s))
            if Mk == "M1":
                kk = int(math.floor(0.03 * len(order))); order = order[kk:len(order) - kk] if kk > 0 else order
            L[mi] = order[:N]
        lb = (F + 2) * 21 if Mk == "M1" else 38 * 21
        rows = [r for r in _ind_book(L, mis, g["w1"]) if not any(ST[r[0]]["pb"][ST[r[0]]["bars"][max(int(np.searchsorted(ST[r[0]]["bars"], r[1])) - 1 - lb, 0)]:r[2] + 1])]
        cag = _ind_engine(rows, g["c0"], g["w1"], C.SEED0)
        ref = S[(S["key"] == "|".join(map(str, (Mk, "合併", F, fq, N)))) & (S["seed"] == C.SEED0)]["c_確認"]
        nchk += 1
        if not len(ref) or abs(float(ref.iloc[0]) - cag) > 1e-6:
            diff += 1; msg.append("%s 不同 %s vs %s" % (Mk, cag, ref.tolist()))
    # M4：獨立重算 M0 名單（R(F) 前 N）、權重（pandas 60 日等權日報酬標準差）與覆蓋層（逐日現金／股票帳），seed 102000
    it = js["四件"]["M4"]
    if "挑格" in it:
        F, fq, N = it["挑格"].split("_"); F = int(F[1:]); N = int(N[1:])
        mis = list(range(len(mst))) if fq == "月" else [mi for mi in range(len(mst)) if g["cal"][mst[mi]].month in (1, 4, 7, 10)]
        L = {}
        for mi in mis:
            e = int(mst[mi]); m = int(ym[e]); sc = {}
            if (m - 2 - F) in me and (m - 2) in me:
                for s in sids:
                    d = ST[s]; vb = np.flatnonzero(d["valid"][:e])
                    if not d["member"][e] or not len(vb) or e - vb[-1] > 5:
                        continue
                    a, b_ = d["closes"][me[m - 2 - F]], d["closes"][me[m - 2]]
                    if np.isfinite(a) and np.isfinite(b_) and a > 0 and b_ > 0:
                        sc[s] = b_ / a - 1
            L[mi] = sorted(sc, key=lambda s: (-sc[s], s))[:N]
        lb = (F + 2) * 21
        rows = [r for r in _ind_book(L, mis, g["w1"]) if not any(ST[r[0]]["pb"][ST[r[0]]["bars"][max(int(np.searchsorted(ST[r[0]]["bars"], r[1])) - 1 - lb, 0)]:r[2] + 1])]
        dfr = pd.DataFrame(rows, columns=["sid", "entry_pos", "xpos_A3", "g_A3", "eh"]).sort_values(["entry_pos", "sid"], kind="mergesort")
        S_ = C._S; R11.COST = 0.0005
        try:
            o = R11.simulate_mtm(dfr[["sid", "entry_pos", "xpos_A3", "g_A3"]].reset_index(drop=True), "A3", 8, np.random.default_rng(C.SEED0), S_["closes"], S_["opens"], S_["ncal"],
                                 return_equity=True, pick=None, d_max=None, queue_days=0, cash_mode="zero", tradable=S_["trad"], delist=S_["dl"])
        finally:
            R11.COST = C.COST
        eq = np.asarray(o["equity"], float)
        wts = {}
        for mi in mis:
            e = int(mst[mi]); lst = L.get(mi, [])
            if not lst or e < 61:
                wts[e] = 1.0; continue
            px = pd.DataFrame({s: ST[s]["closes"][e - 61:e] for s in lst})
            ew = (px / px.shift(1) - 1.0).iloc[1:].mean(axis=1, skipna=True).dropna()
            vol = ew.std(ddof=1) * math.sqrt(252) if len(ew) > 2 else np.nan
            wts[e] = min(1.0, 0.2 / vol) if (np.isfinite(vol) and vol > 0) else 1.0
        cash, stock = 1.0, 0.0; E = [1.0]
        for t in range(1, len(eq)):
            if t in wts:
                tot = cash + stock; tgt = wts[t] * tot
                cash = tot - tgt - abs(tgt - stock) * 0.0005; stock = tgt
            stock = stock * (eq[t] / eq[t - 1]) if eq[t - 1] > 0 else stock
            E.append(cash + stock)
        E = np.array(E); seg = E[g["c0"]:g["w1"] + 1]; c4 = (seg[-1] / seg[0]) ** (252.0 / len(seg)) - 1
        ref = S[(S["key"] == "|".join(map(str, ("M0", "合併", F, fq, N)))) & (S["seed"] == C.SEED0)]["c4_確認"]
        nchk += 1
        if not len(ref) or abs(float(ref.iloc[0]) - c4) > 1e-6:
            diff += 1; msg.append("M4 不同 %s vs %s" % (c4, ref.tolist()))
    return {"件": "A3-12", "抽樣": nchk, "不同": diff, "說明": "M4 挑中格：獨立重算 M0 名單、波動權重（pandas）與覆蓋層帳；M1、M3 挑中格：逐檔獨立重算 R(F)／OLS 殘差分數（np.linalg.lstsq）、剔極端、排名、換股列，直接呼叫引擎 seed 102000 與主程式比確認段年化（容差 1e−6：OLS 寫法不同）" + ("；" + "；".join(msg) if msg else "")}


def check_a3():
    g = G; ST = g["ST"]; sids = g["sids"]; n = g["n"]; diff = 0; nchk = 0; msg = []
    fs = sorted(os.listdir(os.path.join(WK, "a3ev")))
    rng = np.random.default_rng(11)
    pick = rng.choice(fs, size=min(12, len(fs)), replace=False)
    # 獨立基準②：逐檔迴圈
    def peer(t, x, pt):
        pop = []
        for s in sids:
            d = ST[s]
            if not (d["member"][t] and d["valid"][t] and d["valid"][t + 1] and d["O"][t + 1] > 0 and t >= 20):
                continue
            if any(d["pb"][t + 1:min(t + 5, n - 1) + 1]):
                continue
            c0_, c20 = d["closes"][t], d["closes"][t - 20]
            if not (np.isfinite(c0_) and np.isfinite(c20)):
                continue
            pop.append((s, c0_ / c20 - 1))
        if len(pop) < 10:
            return None
        rs = pd.Series([p[1] for p in pop]).rank(method="first").to_numpy(); m = len(pop)
        dec = {p[0]: int(sum(10 * (r - 1) > q * (m - 1) for q in range(1, 10))) for p, r in zip(pop, rs)}
        return dec
    def ret(s, t, x, pt):
        d = ST[s]; e = t + 1
        if any(d["pb"][e + 1:x + 1]):
            return None
        px = (d["O"][x] if (d["valid"][x] and d["O"][x] > 0) else d["closes"][x]) if pt == 0 else d["closes"][x]
        return px / d["O"][e] - 1
    z = np.load(os.path.join(WK, "a3_peers.npz")); PT = {q: z[q] for q in ("K", "S2", "C2", "SA", "CA", "DEC")}
    for f in pick:
        sid = f[:-4]; zz = np.load(os.path.join(WK, "a3ev", f)); d = ST[sid]; b = d["bars"]
        for grp in ("N1", "N2", "NT"):
            if grp + "__t" not in zz.files:
                continue
            t = zz[grp + "__t"]; j = int(rng.integers(len(t))); tt = int(t[j])
            v = int(rng.integers(2)) if grp != "NT" else 0
            x = int(zz[grp + "__v%d_x" % v][j]); pt = int(zz[grp + "__v%d_pt" % v][j]); R = float(zz[grp + "__v%d_R" % v][j])
            stop = float(zz[grp + "__v%d_stop" % v][j]); tgt = float(zz[grp + "__tgt"][j])
            if grp == "NT":                                      # 長紅最低點（獨立從原陣列取）
                stop2 = float(d["L"][b[int(zz["NT__r"][j])]])
                nchk += 1
                if stop2 != stop:
                    diff += 1; msg.append("%s NT 停損價不同" % sid)
            # 獨立出場：逐根（停損／目標先到、次一根開盤、壞根前收盤、窗尾收盤）
            k0 = int(np.searchsorted(b, tt + 1)); xx = None; ptt = 1
            bad = d["pb"][b] | np.r_[False, np.diff(b) > 1]
            kE = int(np.searchsorted(b, g["w1"], side="right")) - 1
            for k in range(k0, len(b)):
                if k > k0 and bad[k]:
                    xx = b[k - 1]; ptt = 1; break
                if k > kE:
                    xx = b[kE]; ptt = 1; break
                cc = d["C"][b[k]]
                if cc < stop or cc >= tgt:
                    if k + 1 <= kE and not bad[k + 1]:
                        xx = b[k + 1]; ptt = 0
                    else:
                        xx = b[k]; ptt = 1
                    break
            if xx is None:
                xx = b[min(kE, len(b) - 1)]
            px = (d["O"][xx] if ptt == 0 else d["C"][xx]) / d["O"][tt + 1] - 1
            nchk += 1
            if xx != x or ptt != pt or abs(px - R) > 1e-12:
                diff += 1; msg.append("%s %s 出場不同 %s/%s vs %s/%s" % (sid, grp, xx, ptt, x, pt))
            # 獨立 X2
            dec = peer(tt, x, pt)
            if dec is None or sid not in dec:
                continue
            q = dec[sid]; vals = [ret(s, tt, x, pt) for s, dq in dec.items() if dq == q and s != sid]
            vals = [v for v in vals if v is not None and np.isfinite(v)]
            if not vals:
                continue
            x2_ind = R - float(np.mean(vals))
            si = sids.index(sid)
            x2_main = float(_x2(sid, si, np.array([tt]), np.array([x]), np.array([pt]), np.array([R]), PT)[0])
            nchk += 1
            if not (np.isfinite(x2_main) and abs(x2_main - x2_ind) < 1e-9):
                diff += 1; msg.append("%s %s X2 不同 %s vs %s" % (sid, grp, x2_ind, x2_main))
    # 累加器：N型 M 臂事件最多的一格（確認段、合併）——逐檔獨立去重（訊號日 ＞ 上一筆出場）＋獨立月分群平均與 SE（台股 R14 式）
    A = np.load(os.path.join(WK, "a3_acc.npz"))
    acc = A["TM"].reshape(21, 3, NM3, 3); conf = np.arange(NM3) >= 72
    cell = int(np.argmax(acc[:, 0][:, conf, 0].sum(1))); rd, wi = cell // 3, cell % 3
    vals = []
    for f in fs:
        zz = np.load(os.path.join(WK, "a3ev", f))
        if "NT__t" not in zz.files:
            continue
        sid = f[:-4]; t = zz["NT__t"].astype(int); sel = np.flatnonzero(zz["NT__F"][:, rd] & (zz["NT__wi"] == wi) & ~zz["NT__viol"])
        best = {}
        for j in sel:
            tt = int(t[j])
            if tt not in best or zz["NT__r"][j] > zz["NT__r"][best[tt]]:
                best[tt] = j
        last = -10 ** 18
        keep = []
        for tt in sorted(best):
            j = best[tt]
            if not np.isfinite(zz["NT__v0_R"][j]) or tt <= math.floor(last):
                continue
            keep.append(j); last = float(zz["NT__v0_ET"][j])
        if not keep:
            continue
        kk = np.array(keep)
        x2 = _x2(sid, sids.index(sid), t[kk], zz["NT__v0_x"][kk].astype(int), zz["NT__v0_pt"][kk].astype(int), zz["NT__v0_R"][kk], PT)
        for tt, xv in zip(t[kk], x2):
            mo = int(g["mon"][tt])
            if mo >= 72 and np.isfinite(xv):
                vals.append((mo, float(xv)))
    if vals:
        dfv = pd.DataFrame(vals, columns=["m", "x"]); Nn = len(dfv); mu = dfv["x"].mean()
        gm = dfv.groupby("m")["x"].agg(["sum", "count"]); se = math.sqrt(((gm["sum"] - mu * gm["count"]) ** 2).sum()) / Nn
        Nm, muA, seA = NP.cstat(acc[cell, 0][conf, 0], acc[cell, 0][conf, 1])
        nchk += 1
        if int(Nm) != Nn or abs(float(muA) - mu) > 1e-12 or abs(float(seA) - se) > 1e-12:
            diff += 1; msg.append("累加器不同 N %s/%s mu %s/%s se %s/%s" % (Nn, Nm, mu, muA, se, seA))
    return {"件": "A3-3", "抽樣": nchk, "不同": diff, "說明": "N型事件最多的一格（確認、合併）逐檔獨立去重＋月分群平均／SE 與累加器比；抽 12 檔各型態 1 事件：N型 逐根獨立重算停損出場日與價別；所有抽中事件逐檔迴圈獨立重算基準②（自分十分位、扣自己、硬斷點剔除）的 X2，與主程式比（容差 1e−9）" + ("；" + "；".join(msg[:6]) if msg else "")}


CHECKS = {"A3-3": check_a3, "A3-10": check_a10, "A3-11": check_a11, "A3-12": check_a12}


def check(lim=None, items=None):
    setup(lim)
    out = []
    for it in (items or list(CHECKS)):
        r = CHECKS[it](); out.append(r); log("check %s：%s" % (it, r))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true"); ap.add_argument("--check", action="store_true")
    ap.add_argument("--procs", type=int, default=2); ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--item", action="append", default=None)
    a = ap.parse_args()
    if a.run:
        print(run(a.procs, a.limit, a.item))
    if a.check:
        r = check(a.limit, a.item)
        p = os.path.join(WK, "check%s.json" % ("" if a.limit is None else "_lim%d" % a.limit))
        prev = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else []
        keep = [x for x in prev if x["件"] not in {y["件"] for y in r}]
        json.dump(keep + r, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
