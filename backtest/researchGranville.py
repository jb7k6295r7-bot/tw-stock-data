# -*- coding: utf-8 -*-
"""葛蘭碧八大法則原版（200 日線＋前低停損）與乖離太遠會不會回來　台股 seq1【頻率表＋全部描述欄乾跑／正式程式】——回測線計算子代理。

登錄：登錄全文-葛蘭碧原版200日線加前低停損與乖離太遠會不會回來_單筆層登錄_台股策略線_seq1_sha50fcadb4c7caacd6-6775B-20261028-2252.md
      （pw1 sha 50fcadb4c7caacd6 ＝ 去掉末行 pw1 戳記後全文 sha256 前 16 碼；整檔 6775 B；整檔 sha256 4ea1a76a… ≠ ⇒ 照 pw1 慣例；回測線 2026-10-28 已驗）
發號：裁定 seq485 §一（判定 5 格 ⇒ N_單筆 ＋5；Bonferroni 5 格 ⇒ 確認段 99% CI）；§二 附註（乖離最早約 2009、買 3 停損先到比例照報、
      三組重疊率必報、≥ 80% 先回信 seq377）；§四 先交頻率表（⛔ 不附報酬）＋全部描述欄乾跑（seq459 §一）。
⛔ 乾跑（--dry）：只數事件、配對、n_eff、可判比例、出場原因（次數）、持有天數分布、重疊；⛔ 不讀、不算、不存任何報酬／超額／勝率（seq366／458／459）；
   描述欄的報酬一律填 0 當佔位（只驗「欄填得出來」，輸出只寫 filled／EMPTY 與件數，⛔ 不寫值）。
⛔ 不 commit、不改既有檔；researchRevTurn_freq（ensure_data、prices、back_ret、ranks）、researchIndMom_freq（reg_check、entry_flag、load_pit、build_panel、MAILBOX）、
   researchTriple_freq（pct_of、market_map）、researchShortageExit（seam_open、lastvalid_le）、research11（load_bars）⛔ 只 import、不寫第二份。

用法（cd ~/tw-p17）：
    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchGranville --dry [--procs 3] [--limit N（煙霧測：隨機 N 檔，輸出 ~/grvwork/dry）]
        ⇒ 頻率表＋全部描述欄乾跑 → backtest/resultsGranville/freq/
    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchGranville --formal --ruling seq485
        ⇒ 正式跑（⛔ 兩個旗標都要給、ruling 必須是 seq485，否則拒跑；⛔ 本次只准 --dry）→ backtest/resultsGranville/formal/
    自測：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchGranville_check

══════════ 登錄寫死的（照抄，不改）══════════
 母體：上市＋上櫃普通股（排除 DR、ETF、權證、創新板）；含已下市。流動性：20 日均量 ≥ 500 張（訊號日前一交易日）。
 價格：還原收盤；MA200＝200 日收盤均線；硬斷點缺口 ≥ 5 日壞根（seq335）；2015-01 接縫照回測新函式（回測 0128 §三）。
 均線方向：上揚＝MA200(t) > MA200(t−20)；下彎＝MA200(t) < MA200(t−20)；其餘＝走平。
 訊號日 t 收盤判，進場＝t+1 還原開盤；同檔同規則 60 個交易日內只取第一次。
 段：探索 2006-01～2015-12｜確認 2016-01～最後一個走得完的訊號日。成本 0.585% 來回。
 買1：MA200 上揚或走平；前 60 個交易日至少 40 日收盤 < MA200；t 收盤由 ≤ MA200 轉為 > MA200；S＝前 60 日最低收盤。
 買2：MA200 上揚；t−k 收盤跌破 MA200（1≤k≤10），跌破前 20 日收盤都 > MA200；t 收盤重新 > MA200（跌破後第一次站回）；S＝跌破期間最低收盤。
 買3：MA200 上揚；前 20 日收盤都 > MA200；t 最低 ≤ MA200×1.02 且收盤 > MA200；S＝t 日最低價。
 出場主臂（seq308）：收盤 < S ⇒ 次日開盤賣；或 收盤 < MA200 且 MA200 下彎（賣5）⇒ 次日開盤賣；兩者先到；上限 250 個交易日收盤。
 對照：同訊號日、同產業（industry_pit）、市值十分位同、前 60 日報酬三分位同、當天沒有該買點訊號；每事件 1～3 檔（種子 20261028）；同日進同日出。
 乖離 D(t)＝收盤÷MA200−1；只用 t 日以前、自己前 1,250 個交易日（不足 750 日不判）的 D 分布；
   超跌＝D ≤ 自己第 5 百分位且 D < −15%；超漲＝D ≥ 第 95 百分位且 D > +30%；觸發＝當天首次進入（前一日不在）；同檔同方向 60 日內取第一次。
   進場 t+1 開盤、持有 20 個交易日；對照同上但「非極端」；超漲回落以「對照 − 訊號」為正向量。
 判定：差＝訊號超額平均（超漲取負）；按訊號月分群 bootstrap 99%（Bonferroni 5 格）、10,000 次、種子 20261028；
   通過（暫定）＝兩段差皆 > 0 且確認段 CI 下緣 > 0；測不出＝其餘（負也寫測不出）；還沒測＝任一段月分群 n_eff < 24；買點格最多暫定。

══════════ ★ 執行者讀法（⛔ 在跑任何本件程式之前寫死於 2026-10-28 23:15（台北，WSL TZ=Asia/Taipei date）；〔 〕內為另一讀法；皆取保守）══════════
 寫死前看過：登錄全文、裁定 seq485、台股 580（葛蘭碧八條對照）、既有程式（researchRevTurn_freq／researchTriple_freq／researchIndMom_freq／
   researchShortageExit／researchTWCheapTrend／researchH1／researchKline／KDJ3／TripleBot／RoundBot 的定義與事件檔欄名）；⛔ 沒看過任何本件數字。
 ★1 資料：價格面板 ＝ researchRevTurn_freq.prices（3 倍命中率 §二 同一套：rerun17 H2D edc6f 2015-01-05～2026-09-24 ＋ 早年 eotc 2004-02-11～2014-12-31
     合併日曆；四碼普通股（gate3＋pit_valid 剔 DR／創新板）含已下市；壞根 ＝ 缺口 ≥5 日（seq335）∪ 價格斷點 ∪ 幽靈還原 ∪ crashwork ∪ 早年 reduce_v2；
     exright open_base（seq412，上市＋上櫃）判開盤鎖漲停）。產業、exright、大盤報酬指數 ＝ tw-stock-data 9b0e9882572c（＝ 3 倍命中率頻率表同一版，
     沿用登錄「§二 沿用 3 倍命中率」）〔另一讀法：最新 origin/main d1f4d2087397〕。早年上櫃日 K 2007-07 起（照註）。
 ★2 最高、最低價：面板沒有 ⇒ 各世界以 research11.load_bars（與面板收盤同一函式、同一還原）逐檔取 h／l，主世界部分乘接縫倍數
     （researchShortageExit.seam_open 原式，對 H、L 各呼叫一次）；開盤 ＝ seam_open(PX)。開盤以面板 O 為準；L ≤ O,C ≤ H 不符件數照報。
 ★3 均線、t−k、t−20、前 60／20 日、1,250／750 日 ⇒ 一律數【該股自己的有效 K 棒】〔另一讀法：數市場日曆〕；t+1、+250、+20、60 日去重 ⇒ 數合併日曆位置。
 ★4 硬斷點（seq335）：壞根切開序列，MA200、D 分布、前 60／20 日窗都不得跨壞根（壞根當根是新段第一根）⇒ 跨壞根的窗 ＝ 不可判。
     〔另一讀法：只剔「回看窗含壞根」的訊號日、壞根前的 D 仍進百分位〕。持有期 (e, 出場] 遇壞根 ⇒ 壞根前最後一根有效收盤強制出（researchCrashOversold K4／
     3 倍命中率 M2 同式；照報件數）。e 前 (t, e] 壞根 ⇒ entry_flag 剔除。
 ★5 流動性閘 ＝ 面板 G[t]（patterns.Frame.gate：含 t 的 20 日都有成交 ∧ t−20～t−1 均量 ≥ 500 張 ＝「訊號日前一交易日的 20 日均量」∧ pit_valid）
     〔另一讀法：G[t−1]〕。事件 ＝ 訊號 ∧ G[t]；★ 60 日去重在過閘之後做（3 倍命中率 T2 同序）：與上一個「取用」事件相距 ≤ 60 個交易日 ⇒ 不取
     〔另一讀法：< 60〕；去重不看進場剔除。
 ★6 線上 ＝ 收盤 > MA200；線下（含相等）＝ 收盤 ≤ MA200。買1「≤ 轉 >」照字面；買1「40 日收盤 < MA200」照字面嚴格 <；
     買2「跌破」＝ 收盤 ≤ MA200（＝ 不在線上；與「重新 > MA200」對稱）〔另一讀法：嚴格 <〕；賣5（出場）照字面「收盤 < MA200 且下彎」。
     上揚／下彎用嚴格 >／<；走平 ＝ 兩者相等（浮點下幾乎不出現，照字面）。買2、買3 的「上揚」只在 t 判〔另一讀法：跌破日也要上揚〕。
 ★7 買1「前 60 個交易日」＝ t−60～t−1（不含 t）、40 日數 t−60～t−1 中收盤 < MA200 者；S＝t−60～t−1 最低收盤〔另一讀法：含 t〕。
     買2：b ＝ t−k，b−20～b−1 全在線上、b～t−1 全線下、t 線上、1 ≤ t−b ≤ 10；S＝b～t−1 最低收盤。買3：t−20～t−1 全在線上；S＝t 的還原最低。
 ★8 出場：觸發看 [e, cap−1] 每根有效 K 棒收盤（cap ＝ e＋250 合併日曆位置〔另一讀法：e＋249〕）；觸發日 d ⇒ d 之後第一根有效 K 棒開盤賣；
     停損與賣5 同一根觸發 ⇒「同日兩者」（同一出場價）。賣出根恰為 cap ⇒ 那一根有「開盤（觸發）」「收盤（上限）」兩個出場價 ⇒ 取較低（seq373）。
     未觸發 ⇒ cap 當天或之前最後一根有效收盤（3 倍命中率 M2）。下市（最後有效 K 棒 < cap 且距資料尾 ≥ 5 日）⇒ 末根收盤。
     觸發後下一根已越過 cap（停牌跨 cap）⇒ 仍在下一根開盤賣（照報件數）。持有天數 ＝ 出場位置 − e（合併日曆）。
 ★9 走得完：買點格 e＋250 ≤ 資料尾（不論實際是否提前出場；用實際出場決定入不入樣本是前視）〔另一讀法：實際出場 ≤ 資料尾〕；
     乖離格 e＋20 ≤ 資料尾（判定）；描述 60／120 日各自要 e＋H ≤ 資料尾；賣5～7 描述 20／60 日同。確認段尾 ＝ 各格最後一個走得完的訊號日。
 ★10 段與月分群依訊號日 t（年月）〔另一讀法：依進場日〕；n_eff ＝ 該段主格事件的訊號月數；主格 ＝ 配到 ∧ e 可進場 ∧ 走得完。2004～2005 ＝ 段外（照報）。
 ★11 對照池（每個事件日 t）：G[t] 過閘、t 有有效 K 棒、非本股、t+1 可進場（entry_flag ＝ 保留）、同產業（IMF.load_pit 在 t；★「其他」也算一類、
     無類別 ⇒ 配不到）、市值十分位同、前 60 日報酬三分位同。分位母體 ＝ t 過閘且該值可算的面板股（rank pct average；十分位 ceil(pct×10)、三分位 ceil(pct×3)；
     3 倍命中率 T3 同法）。市值 ＝ 面板 MC[t]（原始收盤×股數）；前 60 日報酬 ＝ researchRevTurn_freq.back_ret(t, t−60) 同式（向量化，執行時抽樣對帳）。
     買點／賣點格：「當天沒有該訊號」＝ t 當天該格原始訊號（不論閘、去重）為假〔另一讀法：只排除過閘事件〕；不要求該股買點可判。
     乖離格「非極端」＝ t 當天 D 可判（≥ 750 日）且既不在超跌、也不在超漲狀態〔另一讀法：只排同方向極端；或含不可判〕。
     候選 ≥ 3 抽 3、否則全取（1～2）；np.random.default_rng(20261028) 每格各起一條，事件依（t, 代號）序逐一抽。配不到 ⇒ 不入主格。
 ★12 乖離 D 分布：t−1250～t−1（自己的有效 K 棒，同段內）有值的 D；需 ≥ 750 個 D 值才可判〔另一讀法：750 根價格〕；
     百分位 ＝ 線性內插（numpy percentile 預設 ＝ pandas rolling quantile linear；自測對帳）。D(t) 本身不進分布。
     「前一日不在極端」：前一根有效 K 棒（同段）可判且不在該極端；前一根不可判 ⇒ 不觸發〔另一讀法：當成不在極端 ⇒ 觸發〕。
 ★13 乖離持有：e 開盤 → e＋20 收盤（3 倍命中率／營收轉強 x ＝ e＋H 同式〔另一讀法：e＋19〕）；描述 60、120 日同式。對照同進同出。
     回到 MA200（描述）：(t, t+H] 內任一根有效收盤 ≥ MA200（超跌）／≤ MA200（超漲），MA200 用該根自己的值；回到前最大再跌／再漲 ＝ 回到那根之前
     （含進場到那根前一根；沒回到 ⇒ 整段）最低／最高收盤 ÷ t 收盤 − 1；訊號與對照各算。⛔ 乾跑不算（只填佔位、報分母）。
 ★14 賣5 描述事件 ＝ MA200 下彎 ∧ t−1 線上 ∧ t 線下（≤）；賣6 ＝ 下彎 ∧ t 最高 ≥ MA200×0.98 ∧ 收盤 < MA200；
     賣7 ＝ 下彎 ∧ t−20～t−1 收盤都 < MA200 ∧ t 最高 ≥ MA200（觸及）∧ 收盤 < MA200；60 日去重、配對、進場同買點；持有 20／60 日收盤（同 ★13）。
 ★15 對照報酬：同一出場位置與方式；對照在出場日沒成交 ⇒ 該位置以前最後一根有效收盤；對照持有期遇自己的壞根 ⇒ 壞根前收盤；對照下市 ⇒ 末根收盤
     （件數照報）。超額 ＝ 訊號筆（扣 0.585%）− 對照平均（各扣 0.585%）。
 ★16 bootstrap：月分群放回抽月、統計量 ＝ 抽中月份全部事件超額的平均（事件加權）〔另一讀法：月平均再平均〕；99% ＝ 第 0.5／99.5 百分位。
 ★17 對大盤報酬指數（seq425）：data/history/market_tri.csv（9b0e98 版）；訊號 t 收盤 → 出場日收盤（指數只有收盤；TWCheapTrend ★17 同式），不扣成本；
     訊號報酬 − 指數報酬（描述）。上市／上櫃 ＝ meta/stocks.csv∪delisted.csv 的 market（last_seen 值，陷阱 15 照註）。
 ★18 重疊（seq377，件數 ÷ 本格事件數；本格事件 ＝ 過閘去重事件、限在對方事件檔涵蓋的日期範圍內）：
     買2 vs H1 ＝ backtest/resultsH1/main_events.csv 站回組（站回日 ＝ t0＋s_first，主日曆位置 ⇒ 日期）；
     買3 vs 等拉回 ＝ backtest/resultsKline/events.csv.gz 研究十四 結局＝執行 的 X1 進場根；
     超跌 vs 抄底三型態 ＝ KDJ3 判定格 J（resultsKDJ3 主全窗＋早年 H20 交易檔的 T）、三重底 J（resultsTripleBot 同）、圓弧底 J（resultsRoundBot/freq 事件，不分 st）。
     主讀法 ＝「同日」（同檔、同一天）；另報 ±20 個交易日（RoundBot R7 慣例）與反向（對方事件中落在本格的比例）。
     任一讀法 ≥ 80% ⇒ 旗標（主讀法 ≥ 80% ⇒ seq377 先回信）〔另一讀法：只看同日〕。⛔ 只讀對方檔的代號與日期欄，⛔ 不讀報酬欄。
 ★19 可判比例（登錄 §八）：分母 ＝ 該段 G[t] 過閘的股日；分子 ＝ 其中該格條件可判（買點：所需 MA200／斜率／回看窗都有值且不跨壞根；乖離：D 分布 ≥ 750）。
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import io
import json
import math
import os
import pickle
import subprocess
import sys
import time
from collections import Counter, defaultdict
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchRevTurn_freq as RT             # noqa: E402  ensure_data、prices、back_ret、ranks（⛔ 只 import）
from backtest import researchIndMom_freq as IMF             # noqa: E402  reg_check、entry_flag、load_pit、build_panel
from backtest import researchTriple_freq as TP              # noqa: E402  pct_of、market_map
from backtest import researchShortageExit as SM             # noqa: E402  seam_open、lastvalid_le
from backtest import research11 as R                        # noqa: E402  load_bars

REG_SHA = "50fcadb4c7caacd6"
REG_BYTES = 6775
RULING = "seq485"
DATA_SHA = "9b0e9882572c438ec25771031658ddc701ca6171"
OUT = "backtest/resultsGranville"
WORK = os.path.expanduser("~/grvwork")
SEED = 20261028
DEDUP = 60
CAP = 250
HJ = 20
HDESC = (60, 120)
HSELL = (20, 60)
HFIX = 60
MAW = 200
SLOPE = 20
DWIN, DMIN = 1250, 750
COST = 0.00585
NEFF_MIN = 24
NBOOT = 10000
ALPHA = 0.01
SEGS = [("探索", "2006-01-01", "2015-12-31"), ("確認", "2016-01-01", "2099-12-31")]
BUY = ["買1", "買2", "買3"]
DEV = ["超跌回歸", "超漲回落"]
SELL = ["賣5", "賣6", "賣7"]
CELLS = BUY + DEV + SELL
JCELLS = BUY + DEV
NOTES = ["乾跑：未讀、未算、未存任何報酬、超額、勝率（seq366／458／459）；描述欄報酬以 0 佔位，只報 filled／EMPTY",
         "買點格持有期長短不一、月與月重疊 ⇒ 結論最多暫定（登錄 §五）",
         "乖離兩格要自己過去 ≥ 750 個 D 值才判 ⇒ 實際最早事件較晚（裁定 seq485 §二），各段可判比例照報",
         "買3 停損放在當天最低價（影片原版，裁定 seq485 §二 不改），停損先到比例照報",
         "早年上櫃日 K 2007-07 起；價格面板資料尾 2026-09-24（rerun17 H2D edc6f）",
         "上市／上櫃以 meta 名冊 market（last_seen 值）分，轉市場者歸最後市場（陷阱 15）"]
LOG: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


RT.log = log


# ═════════════ 登錄與裁定 ═════════════
def reg_verify():
    fs = [f for f in glob.glob(os.path.join(IMF.MAILBOX, "*.md")) if f"sha{REG_SHA}" in os.path.basename(f)]
    if not fs:
        raise SystemExit("⛔ 信箱找不到登錄全文")
    b = open(fs[0], "rb").read()
    whole = hashlib.sha256(b).hexdigest()[:16]
    name = IMF.reg_check(REG_SHA)                                       # 去 pw1 行重算（IMF 原式），不符即 SystemExit
    if len(b) != REG_BYTES:
        raise SystemExit(f"⛔ 登錄大小 {len(b)} ≠ {REG_BYTES}")
    rul = [f for f in glob.glob(os.path.join(IMF.MAILBOX, "*.md")) if RULING in os.path.basename(f)]
    if not rul:
        raise SystemExit(f"⛔ 信箱找不到裁定 {RULING}")
    return {"登錄": name, "bytes": len(b), "整檔sha前16": whole, "整檔相符": whole == REG_SHA, "pw1去戳記相符": True,
            "裁定": os.path.basename(rul[0])}


# ═════════════ ★2 最高、最低 ═════════════
_HL: dict = {}


def _hl_job(sid):
    Z = _HL["Z"]
    R.D.DATA = Z["data"]
    B = R.load_bars(sid, Z["mk"].get(sid, "twse"), Z["cal"])
    if B is None:
        return sid, None
    return sid, (np.asarray(B["idx"], np.int64), np.asarray(B["h"], float), np.asarray(B["l"], float), np.asarray(B["c"], float))


def hl_world(wn, procs):
    cp = os.path.join(WORK, f"hl_{wn}.pkl")
    if os.path.exists(cp):
        return pickle.load(open(cp, "rb"))
    Z = IMF.build_panel(wn, procs, log)
    _HL["Z"] = Z
    ix = {s: k for k, s in enumerate(Z["sids"])}
    H = np.full(Z["C"].shape, np.nan); L = np.full(Z["C"].shape, np.nan)
    cnt = Counter(); dmax = 0.0
    t0 = time.time()
    with Pool(procs) as pool:
        for k_, (sid, r) in enumerate(pool.imap_unordered(_hl_job, Z["sids"], chunksize=8)):
            j = ix[sid]
            if r is None:
                cnt["load_bars無"] += 1; continue
            idx, h, l, c = r
            H[j, idx] = h; L[j, idx] = l
            ref = Z["C"][j, idx]
            d = np.abs(c - ref) / np.where(ref > 0, ref, np.nan)
            if np.isfinite(d).any():
                dmax = max(dmax, float(np.nanmax(d)))
            cnt["檔"] += 1
            if (k_ + 1) % 500 == 0:
                log(f"  高低 {wn} … {k_ + 1}／{len(Z['sids'])}｜{time.time() - t0:.0f}s")
    out = {"sids": list(Z["sids"]), "H": H, "L": L, "info": {**dict(cnt), "收盤對面板最大相對差": dmax}}
    if dmax > 1e-12:
        raise SystemExit(f"⛔ {wn} load_bars 收盤 ≠ 面板收盤（{dmax}）")
    pickle.dump(out, open(cp, "wb"), protocol=5)
    log(f"[高低 {wn}] {out['info']}｜{time.time() - t0:.0f}s ⇒ {cp}")
    return out


def merged_hl(PX, procs):
    N, NC, NE = len(PX["SIDS"]), len(PX["CAL"]), PX["NE"]
    Hm = np.full((N, NC), np.nan); Lm = np.full((N, NC), np.nan)
    info = {}
    for wn, sl in (("早年", slice(0, NE)), ("主", slice(NE, NC))):
        X = hl_world(wn, procs)
        wix = {s: k for k, s in enumerate(X["sids"])}
        for i, s in enumerate(PX["SIDS"]):
            if s in wix:
                Hm[i, sl] = X["H"][wix[s]]; Lm[i, sl] = X["L"][wix[s]]
        info[wn] = X["info"]
    Hs, nh = SM.seam_open({**PX, "O": Hm})
    Ls, nl = SM.seam_open({**PX, "O": Lm})
    info["接縫乘倍數檔數(H,L)"] = [int(nh), int(nl)]
    return Hs, Ls, info


# ═════════════ 特徵（單一無壞根段；自測直接呼叫）═════════════
def shift(a, k, fill):
    out = np.empty_like(a)
    if k <= 0:
        return a.copy()
    out[:k] = fill; out[k:] = a[:-k]
    return out


def runlen(x):
    """x（bool）在每個位置「含當根往回連續 True」的長度。"""
    n = len(x); idx = np.arange(n)
    lastf = np.maximum.accumulate(np.where(~x, idx, -1))
    return np.where(x, idx - lastf, 0)


def seg_features(c, h, l):
    """c／h／l：同一無壞根段的有效 K 棒（還原）。回 dict（長度 m 的陣列）。只用 ≤ 當根的資料（D 分布只用 < 當根）。"""
    m = len(c); fin = np.isfinite
    s = pd.Series(c)
    MA = s.rolling(MAW, min_periods=MAW).mean().to_numpy(float)
    MA20 = shift(MA, SLOPE, np.nan)
    mok = fin(MA)
    slok = mok & fin(MA20)
    up = slok & (MA > MA20)
    down = slok & (MA < MA20)
    above = mok & (c > MA)
    under = mok & (c <= MA)                      # ★6 線下（含相等）
    below = mok & (c < MA)                       # 嚴格 <
    pmok = shift(mok, 1, False)
    # 買1（★7）
    lt = np.where(mok, below.astype(float), np.nan)
    cnt60 = pd.Series(lt).shift(1).rolling(60, min_periods=60).sum().to_numpy(float)
    J1 = slok & fin(cnt60) & pmok
    B1 = J1 & ~down & (cnt60 >= 40) & shift(under, 1, False) & above
    S1 = s.shift(1).rolling(60, min_periods=60).min().to_numpy(float)
    # 買2
    J2 = slok & shift(mok, 30, False)
    ra = runlen(above); ru = runlen(under)
    r = shift(ru, 1, 0)                          # t−1 往回連續線下根數 ＝ t−b
    bpos = np.arange(m) - r
    ra_bm1 = np.where(bpos >= 1, ra[np.clip(bpos - 1, 0, m - 1)], 0)
    B2 = J2 & up & above & (r >= 1) & (r <= 10) & (ra_bm1 >= 20)
    S2 = np.full(m, np.nan)
    for k in np.flatnonzero(B2):
        S2[k] = float(np.min(c[bpos[k]:k]))
    # 買3
    J3 = slok & shift(mok, 20, False)
    B3 = J3 & up & above & (shift(ra, 1, 0) >= 20) & fin(l) & (l <= MA * 1.02)
    S3 = np.where(B3, l, np.nan)
    # 賣5～7（描述）與出場賣5 狀態
    J5 = slok & pmok
    S5 = J5 & down & shift(above, 1, False) & under
    J6 = slok & fin(h)
    S6 = J6 & down & (h >= MA * 0.98) & below
    J7 = slok & shift(mok, 20, False) & fin(h)
    S7 = J7 & down & (shift(runlen(below), 1, 0) >= 20) & (h >= MA) & below
    X5 = below & down
    # 乖離（★12）
    D = c / MA - 1.0
    Ds = pd.Series(D).shift(1)
    P5 = Ds.rolling(DWIN, min_periods=DMIN).quantile(0.05, interpolation="linear").to_numpy(float)
    P95 = Ds.rolling(DWIN, min_periods=DMIN).quantile(0.95, interpolation="linear").to_numpy(float)
    JD = fin(D) & fin(P5) & fin(P95)
    OS = JD & (D <= P5) & (D < -0.15)
    OB = JD & (D >= P95) & (D > 0.30)
    pJD = shift(JD, 1, False)
    OSt = OS & pJD & ~shift(OS, 1, False)
    OBt = OB & pJD & ~shift(OB, 1, False)
    return {"MA": MA, "down": down, "X5": X5, "J1": J1, "B1": B1, "S1": S1, "J2": J2, "B2": B2, "S2": S2, "J3": J3, "B3": B3, "S3": S3,
            "J5": J5, "S5": S5, "J6": J6, "S6": S6, "J7": J7, "S7": S7, "JD": JD, "OS": OS, "OB": OB, "OSt": OSt, "OBt": OBt, "D": D, "P5": P5, "P95": P95}


FKEYS_B = ["down", "X5", "J1", "B1", "J2", "B2", "J3", "B3", "J5", "S5", "J6", "S6", "J7", "S7", "JD", "OS", "OB", "OSt", "OBt"]


def stock_features(c, h, l, bad):
    """有效 K 棒序列（含壞根旗標）⇒ 依壞根切段（壞根當根 ＝ 新段第一根，★4）逐段 seg_features 再接回。"""
    n = len(c)
    starts = sorted(set([0] + [int(k) for k in np.flatnonzero(bad) if k > 0]))
    ends = starts[1:] + [n]
    out = None
    for a, b in zip(starts, ends):
        F = seg_features(c[a:b], h[a:b], l[a:b])
        if out is None:
            out = {k: (np.zeros(n, bool) if v.dtype == bool else np.full(n, np.nan)) for k, v in F.items()}
        for k, v in F.items():
            out[k][a:b] = v
    return out


# ═════════════ 事件 ═════════════
def dedup(ts, gap=DEDUP):
    """同檔排序後的訊號位置 ⇒ 與上一個取用相距 ≤ gap ⇒ 不取（★5）。回 (kept, n_drop)。"""
    kept = []; last = None; nd = 0
    for t in sorted(ts):
        if last is not None and t - last <= gap:
            nd += 1; continue
        kept.append(t); last = t
    return kept, nd


def segof(d):
    s = str(pd.Timestamp(d).date())
    for nm, a, b in SEGS:
        if a <= s <= b:
            return nm
    return "段外"


def mkey(d):
    d = pd.Timestamp(d); return d.year * 12 + d.month - 1


# ═════════════ 出場（★8；自測直接呼叫）═════════════
def exit_sim(c, o, x5, bad, e, S, cap, cend, lastv):
    """單檔、日曆列：c、o（還原）、x5（賣5 狀態）、bad（壞根）。回 dict(x, kind, reason, flags)。
    kind：open（x 開盤）｜close（x 收盤或 x 以前最後有效收盤）｜minoc（x 根 min(開,收)，seq373）。只看日期與原因、⛔ 不算報酬。"""
    flags = []
    hi = min(cap, len(c) - 1)
    kb = None
    bb = np.flatnonzero(bad[e + 1:hi + 1])
    if len(bb):
        kb = e + 1 + int(bb[0])
    lim = cap if kb is None else min(cap, kb)                         # 觸發只看 [e, lim−1]
    seg = c[e:lim]
    v = np.isfinite(seg)
    st = v & (seg < S)
    xv = v & np.asarray(x5[e:lim], bool)
    tr = np.flatnonzero(st | xv)
    delist = bool(lastv < cap and (cend - lastv) >= 5)
    if len(tr):
        d = e + int(tr[0]); a_, b_ = bool(st[tr[0]]), bool(xv[tr[0]])
        reason = "同日兩者" if (a_ and b_) else ("停損先到" if a_ else "賣5先到")
        nxt = np.flatnonzero(np.isfinite(c[d + 1:]))
        if not len(nxt):
            return {"x": d, "kind": "close", "reason": reason + "→下市末根", "flags": flags, "d": d}
        sale = d + 1 + int(nxt[0])
        if np.asarray(bad[d + 1:sale + 1], bool).any():                # 下一根已跨壞根（含停牌 ≥5 日復牌、cap 之後的壞根）
            return {"x": d, "kind": "close", "reason": reason + "→壞根前強制出", "flags": flags, "d": d}
        if sale == cap:
            flags.append("同根取較低")
            return {"x": sale, "kind": "minoc", "reason": reason, "flags": flags, "d": d}
        if sale > cap:
            flags.append("停牌跨上限")
        return {"x": sale, "kind": "open", "reason": reason, "flags": flags, "d": d}
    if kb is not None:
        lv = np.flatnonzero(np.isfinite(c[e:kb]))
        return {"x": e + int(lv[-1]), "kind": "close", "reason": "壞根前強制出", "flags": flags, "d": None}
    if delist:
        return {"x": int(lastv), "kind": "close", "reason": "下市末根", "flags": flags, "d": None}
    lv = np.flatnonzero(np.isfinite(c[e:cap + 1]))
    return {"x": e + int(lv[-1]), "kind": "close", "reason": "上限250日", "flags": flags, "d": None}


def exit_price(c, o, bad, e, x, kind, cend, lastv):
    """（正式跑用）某檔在事件決定的 (x, kind) 出場價；自己的壞根 ⇒ 壞根前收盤；無成交 ⇒ x 以前最後有效收盤（★15）。回 (價, 狀態)。"""
    bb = np.flatnonzero(bad[e + 1:x + 1])
    if len(bb):
        kb = e + 1 + int(bb[0]); lv = np.flatnonzero(np.isfinite(c[e:kb]))
        return float(c[e + lv[-1]]), "壞根前收盤"
    if kind in ("open", "minoc") and np.isfinite(c[x]) and np.isfinite(o[x]) and o[x] > 0:
        return (float(o[x]) if kind == "open" else float(min(o[x], c[x]))), kind
    lv = np.flatnonzero(np.isfinite(c[e:x + 1]))
    if not len(lv):
        return np.nan, "無價"
    return float(c[e + lv[-1]]), ("收盤" if kind == "close" else "無成交改收盤")


# ═════════════ 配對（★11；自測直接呼叫）═════════════
def draw(rng, cands):
    cands = sorted(cands)
    if len(cands) >= 3:
        return sorted(int(cands[k]) for k in rng.choice(len(cands), 3, replace=False))
    return [int(x) for x in cands]


def match_day(rng, evs, U, dec, ter, excl, ind_of, entry_ok):
    """一個訊號日：evs（事件股 i 依代號序）、U（分位母體股）、dec／ter（對 U）、excl(j)（當天有該訊號／極端 ⇒ True）、ind_of(j)、entry_ok(j)。
    回 {i: (原因, [對照 j])}。"""
    pos = {int(j): k for k, j in enumerate(U)}
    out = {}
    for i in evs:
        k = pos.get(int(i))
        if k is None or dec[k] < 0 or ter[k] < 0:
            out[i] = ("分位不可算", []); continue
        ind = ind_of(i)
        if not ind:
            out[i] = ("無產業", []); continue
        same = [int(U[q]) for q in np.flatnonzero((dec == dec[k]) & (ter == ter[k])) if int(U[q]) != int(i)]
        cands = [j for j in same if not excl(j) and ind_of(j) == ind and entry_ok(j)]
        if not cands:
            out[i] = ("無候選", []); continue
        out[i] = ("配到", draw(rng, cands))
    return out


def deciles(vals):
    p = TP.pct_of(np.asarray(vals, float), np.ones(len(vals), bool))
    return p


# ═════════════ 統計（★16；自測直接呼叫）═════════════
def cluster_boot(x, months, nboot=NBOOT, seed=SEED, alpha=ALPHA):
    x = np.asarray(x, float); months = np.asarray(months)
    ok = np.isfinite(x); x = x[ok]; months = months[ok]
    if not len(x):
        return {"n": 0, "months": 0, "mean": np.nan, "lo": np.nan, "hi": np.nan}
    u, inv = np.unique(months, return_inverse=True)
    sm = np.bincount(inv, weights=x); cn = np.bincount(inv).astype(float)
    rng = np.random.default_rng(seed)
    st = np.empty(nboot)
    M = len(u)
    for b0 in range(0, nboot, 1000):
        k = min(1000, nboot - b0)
        idx = rng.integers(0, M, size=(k, M))
        st[b0:b0 + k] = sm[idx].sum(1) / cn[idx].sum(1)
    return {"n": int(len(x)), "months": int(M), "mean": float(x.mean()),
            "lo": float(np.percentile(st, 100 * alpha / 2)), "hi": float(np.percentile(st, 100 * (1 - alpha / 2)))}


def desc_stats(x, years=None, mkts=None):
    x = np.asarray(x, float); ok = np.isfinite(x)
    xs = x[ok]
    d = {"n": int(len(xs)), "mean": float(xs.mean()) if len(xs) else np.nan, "median": float(np.median(xs)) if len(xs) else np.nan,
         "mean_ex_max1": float(np.sort(xs)[:-1].mean()) if len(xs) >= 2 else np.nan, "win": float((xs > 0).mean()) if len(xs) else np.nan}
    if years is not None:
        yy = np.asarray(years)[ok]
        d["by_year"] = {str(y): {"n": int((yy == y).sum()), "mean": float(xs[yy == y].mean())} for y in sorted(set(yy.tolist()))}
    if mkts is not None:
        mm = np.asarray(mkts)[ok]
        d["by_market"] = {str(k): {"n": int((mm == k).sum()), "mean": (float(xs[mm == k].mean()) if (mm == k).any() else np.nan)} for k in ("twse", "tpex")}
    return d


def verdict(seg_stats):
    """seg_stats：{段: {mean, lo, months}}（超漲已取負）。"""
    if any(seg_stats[s]["months"] < NEFF_MIN for s in ("探索", "確認")):
        return "還沒測"
    if seg_stats["探索"]["mean"] > 0 and seg_stats["確認"]["mean"] > 0 and seg_stats["確認"]["lo"] > 0:
        return "通過（暫定）"
    return "測不出"


def dry_status(D):
    rows = []
    for key, v in D.items():
        sec, cell, stat = key
        if isinstance(v, dict) and "by_year" in v:
            for y, yy in v["by_year"].items():
                rows.append({"section": sec, "cell": cell, "stat": f"{stat}:by_year:{y}", "n": yy["n"],
                             "status": "filled" if yy["n"] > 0 and np.isfinite(yy["mean"]) else "EMPTY"})
        if isinstance(v, dict) and "by_market" in v:
            for k, yy in v["by_market"].items():
                rows.append({"section": sec, "cell": cell, "stat": f"{stat}:by_market:{k}", "n": yy["n"],
                             "status": "filled" if yy["n"] > 0 and np.isfinite(yy["mean"]) else "EMPTY"})
        fields = [f for f in ("mean", "median", "mean_ex_max1", "win", "lo", "hi", "share", "value") if isinstance(v, dict) and f in v]
        for f in fields:
            val = v[f]
            ok = isinstance(val, (int, float, np.floating, np.integer)) and np.isfinite(val) and v.get("n", 1) > 0
            rows.append({"section": sec, "cell": cell, "stat": f"{stat}:{f}", "n": v.get("n"), "status": "filled" if ok else "EMPTY"})
    return pd.DataFrame(rows)


# ═════════════ 主程式 ═════════════
def run(dry, procs, limit=None):
    t0 = time.time()
    od = (os.path.join(WORK, "dry") if limit else os.path.join(OUT, "freq")) if dry else os.path.join(OUT, "formal")
    os.makedirs(od, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    REG = reg_verify(); log(f"[登錄] {REG}")
    sha, DN, MD = RT.ensure_data(DATA_SHA); log(f"[資料] {sha}｜{DN}")
    PX = RT.prices(sha, DN, procs)
    CAL, SIDS, NE = PX["CAL"], PX["SIDS"], PX["NE"]
    N, NC = len(SIDS), len(CAL); CEND = NC - 1
    C, BAD, G, MC, CB, VP, LASTV = PX["C"], PX["BAD"], PX["G"], PX["MC"], PX["CB"], PX["VP"], PX["LASTV"]
    O, nseam = SM.seam_open(PX)
    PX["O"] = O                                                       # 開盤 ＝ 接縫版（entry_flag 只看有限 >0，不變）
    Hs, Ls, hlinfo = merged_hl(PX, procs)
    VALID = np.isfinite(C)
    tol = 1e-9
    chk = {"有效K棒": int(VALID.sum()), "高低缺": int((VALID & ~(np.isfinite(Hs) & np.isfinite(Ls))).sum()),
           "L>C或C>H": int((VALID & ((Ls > C * (1 + tol)) | (C > Hs * (1 + tol)))).sum()),
           "L>O或O>H": int((VALID & np.isfinite(O) & ((Ls > O * (1 + tol)) | (O > Hs * (1 + tol)))).sum())}
    log(f"[高低] {hlinfo}｜開盤接縫 {nseam}｜檢查 {chk}｜{time.time() - t0:.0f}s")
    SUB = np.ones(N, bool)
    if limit:
        rr = np.random.default_rng(SEED); pick = set(rr.choice(N, limit, replace=False).tolist())
        SUB = np.array([k in pick for k in range(N)])
    # ── 特徵 ⇒ 日曆陣列
    FL = {k: np.zeros((N, NC), bool) for k in FKEYS_B}
    MA = np.full((N, NC), np.nan)
    STOP = {"買1": {}, "買2": {}, "買3": {}}
    for i in range(N):
        if not SUB[i]:
            continue
        vp = VP[i]
        if len(vp) < MAW:
            continue
        F = stock_features(C[i, vp], Hs[i, vp], Ls[i, vp], BAD[i, vp])
        for k in FKEYS_B:
            FL[k][i, vp] = F[k]
        MA[i, vp] = F["MA"]
        for cell, bk, sk in (("買1", "B1", "S1"), ("買2", "B2", "S2"), ("買3", "B3", "S3")):
            for q in np.flatnonzero(F[bk]):
                STOP[cell][(i, int(vp[q]))] = float(F[sk][q])
    log(f"[特徵] {time.time() - t0:.0f}s")
    RAW = {"買1": FL["B1"], "買2": FL["B2"], "買3": FL["B3"], "超跌回歸": FL["OSt"], "超漲回落": FL["OBt"], "賣5": FL["S5"], "賣6": FL["S6"], "賣7": FL["S7"]}
    JUD = {"買1": FL["J1"], "買2": FL["J2"], "買3": FL["J3"], "超跌回歸": FL["JD"], "超漲回落": FL["JD"], "賣5": FL["J5"], "賣6": FL["J6"], "賣7": FL["J7"]}
    EXCL = {"買1": FL["B1"], "買2": FL["B2"], "買3": FL["B3"], "賣5": FL["S5"], "賣6": FL["S6"], "賣7": FL["S7"]}
    NONEXT = FL["JD"] & ~FL["OS"] & ~FL["OB"]                        # ★11 乖離對照 ＝ 可判且非極端
    GS = G & SUB[:, None]
    # ── 可判比例（★19）
    seg_pos = {}
    for nm, a, b in SEGS:
        pa = int(CAL.searchsorted(pd.Timestamp(a))); pb = int(CAL.searchsorted(pd.Timestamp(b), side="right"))
        seg_pos[nm] = (pa, pb)
    JUDG = []
    for cell in CELLS:
        for nm, (pa, pb) in seg_pos.items():
            den = int((GS[:, pa:pb] & VALID[:, pa:pb]).sum()); num = int((GS[:, pa:pb] & JUD[cell][:, pa:pb]).sum())
            JUDG.append({"格": cell, "段": nm, "過閘股日": den, "可判股日": num, "可判比例": num / den if den else None})
    # ── 事件
    EV = {}; EVR = {}
    eflag_memo = {}

    def eflag(i, t):
        k = (i, t)
        if k not in eflag_memo:
            eflag_memo[k] = IMF.entry_flag(PX, i, t, t + 1) if t + 1 <= CEND else "e超出資料尾"
        return eflag_memo[k]
    MKT = TP.market_map(DN)
    for cell in CELLS:
        ii, tt = np.nonzero(RAW[cell] & SUB[:, None])
        rs = Counter({"原始訊號": int(len(ii))})
        byi = defaultdict(list)
        for i, t in zip(ii.tolist(), tt.tolist()):
            if not G[i, t]:
                rs["閘外G[t]"] += 1; continue
            byi[i].append(t)
        rows = []
        for i in sorted(byi):
            kept, nd = dedup(byi[i]); rs["60日內非第一次"] += nd
            for t in kept:
                d = CAL[t]
                rows.append({"i": i, "sid": SIDS[i], "t": t, "date": str(d.date()), "段": segof(d), "月": mkey(d), "年": d.year,
                             "市場": MKT.get(SIDS[i], "?"), "進場": eflag(i, t)})
        E = pd.DataFrame(rows, columns=["i", "sid", "t", "date", "段", "月", "年", "市場", "進場"])
        E = E.sort_values(["t", "sid"]).reset_index(drop=True)
        E["e"] = E["t"] + 1
        for H in ([CAP] if cell in BUY else ([HJ] + list(HDESC) if cell in DEV else list(HSELL))) + ([HFIX] if cell in BUY else []):
            E[f"走得完{H}"] = (E["e"] + H) <= CEND
        E["走得完"] = E[f"走得完{CAP}"] if cell in BUY else (E[f"走得完{HJ}"] if cell in DEV else E[f"走得完{HSELL[0]}"])
        rs["事件"] = int(len(E))
        EV[cell] = E; EVR[cell] = dict(rs)
        log(f"[事件 {cell}] {dict(rs)}")
    # ── r60 向量化（★11）與對帳
    LVP = np.full((N, NC), -1, np.int32)
    for i in range(N):
        a = np.full(NC, -1, np.int64); a[VP[i]] = VP[i]; LVP[i] = np.maximum.accumulate(a)
    AR = np.arange(N)

    def r60_vec(t):
        p0 = t - 60
        if p0 < 0:
            return np.full(N, np.nan)
        a = LVP[:, p0].astype(np.int64)
        ok = VALID[:, t] & (a >= 0)
        a2 = np.where(ok, a, 0)
        ok &= (CB[:, t] - CB[AR, a2]) == 0
        with np.errstate(invalid="ignore", divide="ignore"):
            return np.where(ok, C[:, t] / C[AR, a2] - 1.0, np.nan)
    rr = np.random.default_rng(1)
    bad_n = 0; tested = 0
    for _ in range(3000):
        i = int(rr.integers(N)); t = int(rr.integers(61, NC))
        if not VALID[i, t]:
            continue
        x1 = RT.back_ret(PX, i, t, t - 60); x2 = r60_vec(t)[i]; tested += 1
        if not ((np.isnan(x1) and np.isnan(x2)) or (abs(x1 - x2) <= 1e-12 * max(1, abs(x1)))):
            bad_n += 1
    log(f"[r60 對帳 back_ret] 抽 {tested}｜不符 {bad_n}")
    if bad_n:
        raise SystemExit("⛔ r60 向量化 ≠ back_ret")
    pit = IMF.load_pit(DN)

    def ind_at(j, t):
        v, _ = pit.at(SIDS[j], CAL[t]); return v or ""
    # ── 配對
    MT = {}; MREASON = {}
    for cell in CELLS:
        E = EV[cell]; rng = np.random.default_rng(SEED)
        res = {}
        if len(E):
            need = E[(E["進場"] == "保留") & E["走得完"]]
            for t, g in need.groupby("t", sort=True):
                t = int(t)
                U = np.flatnonzero(GS[:, t] & VALID[:, t]) if not limit else np.flatnonzero(G[:, t] & VALID[:, t])
                mc = MC[U, t].astype(float); mc[~(mc > 0)] = np.nan
                r6 = r60_vec(t)[U]
                pm = deciles(mc); pr = deciles(r6)
                dec = np.where(np.isfinite(pm), np.ceil(pm * 10), -1).astype(int)
                ter = np.where(np.isfinite(pr), np.ceil(pr * 3), -1).astype(int)
                ex = (lambda j, t=t: bool(EXCL[cell][j, t])) if cell not in DEV else (lambda j, t=t: not bool(NONEXT[j, t]))
                out = match_day(rng, sorted(g["i"].astype(int).tolist(), key=lambda z: SIDS[z]), U, dec, ter, ex,
                                lambda j, t=t: ind_at(j, t), lambda j, t=t: eflag(j, t) == "保留")
                for i, v in out.items():
                    res[(i, t)] = v
        MT[cell] = res
        E["配對"] = [res.get((int(i), int(t)), ("未配(剔除或走不完)", []))[0] for i, t in zip(E["i"], E["t"])] if len(E) else []
        E["對照"] = [";".join(SIDS[j] for j in res.get((int(i), int(t)), ("", []))[1]) for i, t in zip(E["i"], E["t"])] if len(E) else []
        E["對照數"] = [len(res.get((int(i), int(t)), ("", []))[1]) for i, t in zip(E["i"], E["t"])] if len(E) else []
        E["主格"] = (E["配對"] == "配到") & (E["進場"] == "保留") & E["走得完"] if len(E) else []
        MREASON[cell] = dict(Counter(E["配對"])) if len(E) else {}
        log(f"[配對 {cell}] {MREASON[cell]}｜{time.time() - t0:.0f}s")
    # ── 出場（買點格；只日期與原因）
    for cell in BUY:
        E = EV[cell]
        xs, kinds, reas, fl, hold, cst = [], [], [], [], [], []
        for r in E.itertuples(index=False):
            if not (r.進場 == "保留" and r.走得完):
                xs.append(-1); kinds.append(""); reas.append(""); fl.append(""); hold.append(-1); cst.append(""); continue
            i, e = int(r.i), int(r.e)
            S = STOP[cell][(i, int(r.t))]
            X = exit_sim(C[i], O[i], FL["X5"][i], BAD[i], e, S, e + CAP, CEND, int(LASTV[i]))
            xs.append(X["x"]); kinds.append(X["kind"]); reas.append(X["reason"]); fl.append("|".join(X["flags"])); hold.append(X["x"] - e)
            cs = []
            for sj in (r.對照.split(";") if r.對照 else []):
                j = PX["ix"][sj]
                bb = np.flatnonzero(BAD[j, e + 1:X["x"] + 1])
                if len(bb):
                    cs.append("壞根")
                elif X["kind"] in ("open", "minoc") and not (VALID[j, X["x"]] and np.isfinite(O[j, X["x"]])):
                    cs.append("出場日無成交")
                elif X["kind"] == "close" and not VALID[j, X["x"]]:
                    cs.append("出場日無收盤")
                else:
                    cs.append("ok")
            cst.append(";".join(cs))
        E["出場位"] = xs; E["出場方式"] = kinds; E["出場原因"] = reas; E["旗標"] = fl; E["持有天數"] = hold; E["對照出場狀態"] = cst
        E["出場日"] = [str(CAL[x].date()) if x >= 0 else "" for x in xs]
    # 乖離／賣點：對照在 e＋H 的狀態（只次數）
    for cell in DEV + SELL:
        E = EV[cell]
        Hs_ = [HJ] + list(HDESC) if cell in DEV else list(HSELL)
        for H in Hs_:
            col = []
            for r in E.itertuples(index=False):
                if not (r.配對 == "配到" and r.進場 == "保留" and getattr(r, f"走得完{H}")):
                    col.append(""); continue
                e = int(r.e); x = e + H; cs = []
                for sj in ([SIDS[int(r.i)]] + (r.對照.split(";") if r.對照 else [])):
                    j = PX["ix"][sj]
                    cs.append("壞根" if len(np.flatnonzero(BAD[j, e + 1:x + 1])) else ("x無收盤" if not VALID[j, x] else "ok"))
                col.append(";".join(cs))
            E[f"H{H}狀態(訊號;對照)"] = col
    # ── 報酬（正式）或 0 佔位（乾跑）
    TRI = load_tri(CAL)

    def ret_pair(cell, r, H=None, x=None, kind=None):
        """回 (訊號報酬, 對照平均報酬, 對照報酬 list)。乾跑一律 0（⛔ 不碰進場後價格）。"""
        cj = [PX["ix"][s] for s in (r.對照.split(";") if r.對照 else [])]
        if dry:
            return 0.0, 0.0, [0.0] * len(cj)
        i, e = int(r.i), int(r.e)
        if x is None:
            x, kind = e + H, "close"
        vals = []
        for j in [i] + cj:
            p, _ = exit_price(C[j], O[j], BAD[j], e, x, kind, CEND, int(LASTV[j]))
            vals.append(p / O[j, e] - 1.0 - COST if np.isfinite(p) and O[j, e] > 0 else np.nan)
        cv = np.array(vals[1:], float)
        return vals[0], (float(np.nanmean(cv)) if np.isfinite(cv).any() else np.nan), vals[1:]

    DESC = {}; JSTAT = {}
    for cell in CELLS:
        E = EV[cell]
        if not len(E):
            continue
        M = E[E["主格"]]
        if cell in BUY:
            XS = []; XF = []; XT = []
            for r in M.itertuples(index=False):
                a, b, _ = ret_pair(cell, r, x=int(r.出場位), kind=r.出場方式); XS.append(a - b if np.isfinite(a) and np.isfinite(b) else np.nan)
                if getattr(r, f"走得完{HFIX}"):
                    a2, b2, _ = ret_pair(cell, r, H=HFIX); XF.append(a2 - b2 if np.isfinite(a2) and np.isfinite(b2) else np.nan)
                else:
                    XF.append(np.nan)
                XT.append(0.0 if dry else (a - (TRI[int(r.出場位)] / TRI[int(r.t)] - 1.0)))
            M = M.assign(X=XS, XF=XF, XT=XT)
            for nm, _, _ in SEGS:
                q = M[M["段"] == nm]
                JSTAT[(cell, nm)] = cluster_boot(q["X"].to_numpy(float), q["月"].to_numpy())
            DESC[("判定外描述", cell, "主臂超額(訊號−對照)")] = desc_stats(M["X"], M["年"], M["市場"])
            DESC[("判定外描述", cell, "固定抱60日無停損超額")] = desc_stats(M["XF"], M["年"], M["市場"])
            DESC[("判定外描述", cell, "對大盤報酬指數(訊號−指數)")] = desc_stats(M["XT"], M["年"], M["市場"])
            DESC[("判定外描述", cell, "停損觸發率")] = {"n": int(len(M)), "share": float(M["出場原因"].str.startswith(("停損先到", "同日兩者")).mean()) if len(M) else np.nan}
            DESC[("判定外描述", cell, "平均持有天數")] = {"n": int(len(M)), "value": float(M["持有天數"].mean()) if len(M) else np.nan}
            DESC[("判定外描述", cell, "出場原因分布")] = {"n": int(len(M)), "value": float(M["出場原因"].nunique()) if len(M) else np.nan}
        elif cell in DEV:
            sgn = -1.0 if cell == "超漲回落" else 1.0
            for H in [HJ] + list(HDESC):
                q = M[M[f"走得完{H}"]]
                XS = []; RET = []; RETC = []; MXS = []; MXC = []
                for r in q.itertuples(index=False):
                    a, b, cl = ret_pair(cell, r, H=H); XS.append(a - b if np.isfinite(a) and np.isfinite(b) else np.nan)
                    rs_, rc_, ms_, mc_ = back_to_ma(r, H, cell, dry, C, MA, PX)
                    RET.append(rs_); RETC.append(rc_); MXS.append(ms_); MXC.append(mc_)
                q = q.assign(X=XS)
                if H == HJ:
                    for nm, _, _ in SEGS:
                        z = q[q["段"] == nm]
                        JSTAT[(cell, nm)] = cluster_boot(sgn * z["X"].to_numpy(float), z["月"].to_numpy())
                DESC[("判定外描述", cell, f"{H}日超額(訊號−對照)")] = desc_stats(q["X"], q["年"], q["市場"])
                DESC[("判定外描述", cell, f"{H}日內收盤回到MA200比例｜訊號")] = {"n": int(len(q)), "share": float(np.nanmean(RET)) if len(RET) else np.nan}
                DESC[("判定外描述", cell, f"{H}日內收盤回到MA200比例｜對照")] = {"n": int(len(q)), "share": float(np.nanmean(RETC)) if len(RETC) else np.nan}
                lab = "最大再跌" if cell == "超跌回歸" else "最大再漲"
                DESC[("判定外描述", cell, f"{H}日回到前{lab}｜訊號")] = desc_stats(MXS)
                DESC[("判定外描述", cell, f"{H}日回到前{lab}｜對照")] = desc_stats(MXC)
        else:
            for H in HSELL:
                q = M[M[f"走得完{H}"]]
                XS = []
                for r in q.itertuples(index=False):
                    a, b, _ = ret_pair(cell, r, H=H); XS.append(a - b if np.isfinite(a) and np.isfinite(b) else np.nan)
                DESC[("賣點描述", cell, f"{H}日對照超額(訊號−對照)")] = desc_stats(XS, q["年"].to_numpy(), q["市場"].to_numpy())
    for (cell, nm), v in JSTAT.items():
        DESC[("判定", cell, f"{nm}｜差(超漲取負)與99%CI")] = {"n": v["n"], "mean": v["mean"], "lo": v["lo"], "hi": v["hi"]}
    # ── 重疊（★18）
    OVL = overlaps(EV, CAL, PX)
    for o_ in OVL:
        DESC[("等價自查", o_["本格"], f"vs {o_['對方']}｜{o_['讀法']}")] = {"n": o_["本格事件(涵蓋內)"], "share": o_["本格中重疊比例"] if o_["本格中重疊比例"] is not None else np.nan}
    # ── 彙整
    return dict(od=od, REG=REG, sha=sha, PX=PX, EV=EV, EVR=EVR, JUDG=JUDG, MREASON=MREASON, JSTAT=JSTAT, DESC=DESC, OVL=OVL,
                hlinfo=hlinfo, chk=chk, CAL=CAL, CEND=CEND, t0=t0, TRIcov=(int(np.isfinite(TRI).sum()), NC))


def load_tri(CAL):
    txt = subprocess.run(["git", "show", f"{DATA_SHA}:data/history/market_tri.csv"], capture_output=True, text=True, check=True).stdout
    x = pd.read_csv(io.StringIO(txt), dtype={"date": str})
    s = pd.Series(pd.to_numeric(x["close"], errors="coerce").to_numpy(float), index=pd.to_datetime(x["date"]))
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s.reindex(CAL).ffill().to_numpy(float)


def back_to_ma(r, H, cell, dry, C, MA, PX):
    """★13：回 (訊號回到 MA200 與否, 對照平均, 訊號回到前最大再跌/漲, 對照平均)。乾跑 ⇒ 0 佔位（⛔ 不碰 t 之後價格）。"""
    if dry:
        return 0.0, 0.0, 0.0, 0.0
    t = int(r.t); x = t + H
    res = []
    for s in [r.sid] + (r.對照.split(";") if r.對照 else []):
        j = PX["ix"][s]
        c = C[j, t + 1:x + 1]; m = MA[j, t + 1:x + 1]; v = np.isfinite(c) & np.isfinite(m)
        hit = np.flatnonzero(v & ((c >= m) if cell == "超跌回歸" else (c <= m)))
        stop = hit[0] if len(hit) else len(c)
        seg = c[:stop]; seg = seg[np.isfinite(seg)]
        base = C[j, t]
        mx = (np.nan if not len(seg) else (seg.min() / base - 1.0 if cell == "超跌回歸" else seg.max() / base - 1.0))
        res.append((float(len(hit) > 0), mx))
    a = np.array(res, float)
    return a[0, 0], (float(np.nanmean(a[1:, 0])) if len(a) > 1 else np.nan), a[0, 1], (float(np.nanmean(a[1:, 1])) if len(a) > 1 else np.nan)


# ═════════════ 重疊（★18）═════════════
def _dates_from_pos(main_cal, pos):
    pos = np.asarray(pos, np.int64)
    ok = (pos >= 0) & (pos < len(main_cal))
    out = np.array([""] * len(pos), dtype=object)
    out[ok] = [str(d.date()) for d in main_cal[pos[ok]]]
    return out


def other_sets(main_cal):
    """對方事件 ⇒ {名: DataFrame[sid, date]}（⛔ 只讀代號與日期欄）。"""
    S = {}
    h = pd.read_csv("backtest/resultsH1/main_events.csv", usecols=["sid", "t", "站回", "s_first"], dtype={"sid": str})
    h = h[h["站回"] == 1]
    S["H1月線3日站回"] = pd.DataFrame({"sid": h["sid"].str.strip(), "date": _dates_from_pos(main_cal, h["t"] + h["s_first"])})
    k = pd.read_csv("backtest/resultsKline/events.csv.gz", usecols=["研究", "sid", "X1", "結局"], dtype={"sid": str})
    k = k[(k["研究"].astype(str) == "十四") & (k["結局"] == "執行")]
    S["等拉回(K線研究十四執行)"] = pd.DataFrame({"sid": k["sid"].str.strip(), "date": _dates_from_pos(main_cal, k["X1"].astype(np.int64))})
    fr = []
    for f in ("backtest/resultsKDJ3/events/trades_主_主全窗_J_H20.csv.gz", "backtest/resultsKDJ3/events/trades_早年_早年_J_H20.csv.gz"):
        fr.append(pd.read_csv(f, usecols=["sid", "T"], dtype={"sid": str, "T": str}))
    x = pd.concat(fr); S["KDJ三週期共振J"] = pd.DataFrame({"sid": x["sid"].str.strip(), "date": x["T"].str[:10]})
    fr = []
    for f in ("backtest/resultsTripleBot/events/trades_主_主全窗_J_H20.csv.gz", "backtest/resultsTripleBot/events/trades_早年_早年_J_H20.csv.gz"):
        fr.append(pd.read_csv(f, usecols=["sid", "T"], dtype={"sid": str, "T": str}))
    x = pd.concat(fr); S["三重底J"] = pd.DataFrame({"sid": x["sid"].str.strip(), "date": x["T"].str[:10]})
    fr = []
    for f in ("backtest/resultsRoundBot/freq/events_主.csv.gz", "backtest/resultsRoundBot/freq/events_早年.csv.gz"):
        y = pd.read_csv(f, usecols=["格", "sid", "T"], dtype={"sid": str, "T": str}); fr.append(y[y["格"] == "J"])
    x = pd.concat(fr); S["圓弧底J"] = pd.DataFrame({"sid": x["sid"].str.strip(), "date": x["T"].str[:10]})
    return S


def overlap_rate(mine, other, CAL, win):
    """mine：DataFrame[sid, t（合併日曆位置）]；other：[sid, date]。回 (涵蓋內本格數, 重疊數, 對方涵蓋內數, 對方被涵蓋數)。"""
    if not len(other) or not len(mine):
        return 0, 0, 0, 0
    od = pd.to_datetime(other["date"]); lo, hi = od.min(), od.max()
    op = CAL.searchsorted(od)
    exact = (op < len(CAL)) & (CAL[np.clip(op, 0, len(CAL) - 1)] == od)
    byo = defaultdict(list)
    for s, p, ok in zip(other["sid"], op, exact):
        if ok:
            byo[s].append(int(p))
    for s in byo:
        byo[s] = np.array(sorted(byo[s]))
    md = CAL[mine["t"].to_numpy()]
    m = mine[(md >= lo) & (md <= hi)]
    n = len(m); hit = 0
    byme = defaultdict(list)
    for s, t in zip(m["sid"], m["t"]):
        byme[s].append(int(t))
        a = byo.get(s)
        if a is not None and len(a):
            k = np.searchsorted(a, t - win)
            if k < len(a) and a[k] <= t + win:
                hit += 1
    for s in byme:
        byme[s] = np.array(sorted(byme[s]))
    mlo, mhi = md.min(), md.max()
    no = 0; rh = 0
    for s, p, ok in zip(other["sid"], op, exact):
        if not ok or not (mlo <= CAL[p] <= mhi):
            continue
        no += 1
        a = byme.get(s)
        if a is not None and len(a):
            k = np.searchsorted(a, p - win)
            if k < len(a) and a[k] <= p + win:
                rh += 1
    return n, hit, no, rh


def overlaps(EV, CAL, PX):
    main_cal = PX["main_cal"]
    S = other_sets(main_cal)
    pairs = [("買2", ["H1月線3日站回"]), ("買3", ["等拉回(K線研究十四執行)"]), ("超跌回歸", ["KDJ三週期共振J", "三重底J", "圓弧底J", "抄底三型態聯集"])]
    S["抄底三型態聯集"] = pd.concat([S["KDJ三週期共振J"], S["三重底J"], S["圓弧底J"]]).drop_duplicates()
    out = []
    for cell, others in pairs:
        E = EV[cell]
        mine = E[["sid", "t"]] if len(E) else pd.DataFrame({"sid": [], "t": []})
        for on in others:
            for lab, win in (("同日", 0), ("±20日", 20)):
                n, hit, no, rh = overlap_rate(mine, S[on], CAL, win)
                out.append({"本格": cell, "對方": on, "讀法": lab, "本格事件(涵蓋內)": n, "重疊": hit, "本格中重疊比例": (hit / n) if n else None,
                            "對方事件(本格期間內)": no, "對方中落在本格": rh, "對方中重疊比例": (rh / no) if no else None,
                            "旗標≥80%": bool((n and hit / n >= 0.8) or (no and rh / no >= 0.8))})
    return out


# ═════════════ 輸出 ═════════════
def write_dry(A):
    od = A["od"]; EV = A["EV"]; CAL = A["CAL"]
    rows = []; reas = []; holds = []
    for cell in CELLS:
        E = EV[cell]
        for nm, _, _ in SEGS + [("段外", "", "")]:
            q = E[E["段"] == nm] if len(E) else E
            if not len(q):
                rows.append({"格": cell, "段": nm, "事件(過閘去重)": 0}); continue
            ent = q["進場"] == "保留"; wk = q["走得完"]; base = q[ent & wk]
            main = q[q["主格"]]
            months = int(main["月"].nunique())
            last_walk = q[wk]["date"].max() if wk.any() else ""
            row = {"格": cell, "段": nm, "事件(過閘去重)": int(len(q)), "進場剔除": dict(Counter(q.loc[~ent, "進場"])),
                   "可進場": int(ent.sum()), "可進場且走得完": int(len(base)), "配到": int((base["配對"] == "配到").sum()),
                   "配對成功率": float((base["配對"] == "配到").mean()) if len(base) else None,
                   "配不到原因": dict(Counter(base.loc[base["配對"] != "配到", "配對"])), "對照數分布": dict(Counter(base.loc[base["配對"] == "配到", "對照數"])),
                   "主格事件": int(len(main)), "主格訊號月數(n_eff)": months, "n_eff≥24": months >= NEFF_MIN,
                   "首個事件日": q["date"].min(), "末個事件日": q["date"].max(), "最後走得完訊號日": last_walk}
            if cell in DEV:
                for H in HDESC:
                    row[f"主格且{H}日走得完"] = int((main[f"走得完{H}"]).sum())
            if cell in SELL:
                row["主格且60日走得完"] = int((main["走得完60"]).sum())
            if cell in BUY:
                row["主格且固定60日走得完"] = int(main[f"走得完{HFIX}"].sum())
                rc = Counter(main["出場原因"])
                for k_, v_ in rc.items():
                    reas.append({"格": cell, "段": nm, "出場原因": k_, "件數": int(v_), "比例": v_ / len(main) if len(main) else None})
                row["停損先到(含同日)比例"] = float(main["出場原因"].str.startswith(("停損先到", "同日兩者")).mean()) if len(main) else None
                row["停損先到(不含同日)比例"] = float(main["出場原因"].str.startswith("停損先到").mean()) if len(main) else None
                row["同日兩者比例"] = float(main["出場原因"].str.startswith("同日兩者").mean()) if len(main) else None
                row["賣5先到比例"] = float(main["出場原因"].str.startswith("賣5先到").mean()) if len(main) else None
                row["上限250日比例"] = float((main["出場原因"] == "上限250日").mean()) if len(main) else None
                row["旗標"] = dict(Counter(f for x in main["旗標"] for f in x.split("|") if f))
                row["對照出場狀態"] = dict(Counter(f for x in main["對照出場狀態"] for f in x.split(";") if f))
                hd = main["持有天數"].to_numpy(float)
                if len(hd):
                    bins = [0, 1, 2, 3, 5, 10, 20, 60, 120, 250, 10 ** 6]
                    hc = np.histogram(hd, bins=bins)[0]
                    holds.append({"格": cell, "段": nm, "n": int(len(hd)), "平均": float(hd.mean()), "中位": float(np.median(hd)),
                                  "p10": float(np.percentile(hd, 10)), "p25": float(np.percentile(hd, 25)), "p75": float(np.percentile(hd, 75)),
                                  "p90": float(np.percentile(hd, 90)), "max": float(hd.max()),
                                  **{f"[{bins[k]},{bins[k + 1]})": int(hc[k]) for k in range(len(hc))}})
            if cell in DEV or cell in SELL:
                Hs_ = [HJ] + list(HDESC) if cell in DEV else list(HSELL)
                for H in Hs_:
                    col = f"H{H}狀態(訊號;對照)"
                    row[f"H{H}持有期狀態"] = dict(Counter(f for x in main[col] for f in x.split(";") if f))
            rows.append(row)
    # 年分布（只件數）
    yr = []
    for cell in CELLS:
        E = EV[cell]
        if len(E):
            for (y, nm), g in E.groupby(["年", "段"]):
                yr.append({"格": cell, "年": int(y), "段": nm, "事件": int(len(g)), "主格": int(g["主格"].sum())})
    pd.DataFrame(rows).to_csv(os.path.join(od, "freq_cells.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(reas).to_csv(os.path.join(od, "exit_reasons.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(holds).to_csv(os.path.join(od, "hold_dist.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(yr).to_csv(os.path.join(od, "yearly.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(A["JUDG"]).to_csv(os.path.join(od, "judgeable.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(A["OVL"]).to_csv(os.path.join(od, "overlap.csv"), index=False, encoding="utf-8-sig")
    ds = dry_status(A["DESC"]); ds.to_csv(os.path.join(od, "desc_dryrun_status.csv"), index=False, encoding="utf-8-sig")
    keep = ["sid", "date", "段", "市場", "進場", "走得完", "配對", "對照數", "對照", "主格"]
    for cell in CELLS:
        E = EV[cell]
        if not len(E):
            continue
        cols = keep + [c for c in E.columns if c.startswith("走得完") and c != "走得完"]
        if cell in BUY:
            cols += ["出場日", "出場方式", "出場原因", "旗標", "持有天數", "對照出場狀態"]
        else:
            cols += [c for c in E.columns if c.startswith("H") and "狀態" in c]
        E[cols].to_csv(os.path.join(od, f"events_{cell}.csv.gz"), index=False, encoding="utf-8-sig", compression="gzip")
    neff = {}
    for cell in JCELLS:
        E = EV[cell]
        ms = {nm: int(E[(E["段"] == nm) & E["主格"]]["月"].nunique()) if len(E) else 0 for nm, _, _ in SEGS}
        neff[cell] = {**ms, "狀態": ("依構造還沒測（任一段 n_eff < 24）" if min(ms.values()) < NEFF_MIN else "兩段 n_eff ≥ 24（可判，待正式跑）")}
    J = {"登錄": A["REG"], "裁定": RULING, "資料": A["sha"], "價格面板": "rerun17 H2D edc6f（2015-01-05～2026-09-24）＋ 早年 eotc（2004-02-11～2014-12-31）",
         "日曆": f"{A['CAL'][0].date()}～{A['CAL'][-1].date()}（{len(A['CAL'])}）", "高低價": A["hlinfo"], "價格檢查": A["chk"],
         "大盤報酬指數覆蓋(日曆位置有值/全部)": A["TRIcov"],
         "事件剔除": A["EVR"], "配對原因": A["MREASON"], "n_eff": neff,
         "重疊旗標(≥80%)": [o for o in A["OVL"] if o["旗標≥80%"]],
         "描述欄乾跑": {"欄數": int(len(ds)), "EMPTY": int((ds["status"] == "EMPTY").sum()) if len(ds) else 0},
         "NOTES": NOTES, "完成": str(pd.Timestamp.now(tz="Asia/Taipei")), "耗時秒": int(time.time() - A["t0"])}
    json.dump(J, open(os.path.join(od, "freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=_js)
    open(os.path.join(od, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    log(f"[完成] ⇒ {od}｜描述欄 {J['描述欄乾跑']}｜n_eff {neff}")


def _js(o):
    if isinstance(o, (np.integer, np.floating, np.bool_)):
        return o.item()
    return str(o)


def write_formal(A):
    od = A["od"]
    res = {}
    for cell in JCELLS:
        ss = {}
        for nm, _, _ in SEGS:
            v = A["JSTAT"].get((cell, nm), {"n": 0, "months": 0, "mean": np.nan, "lo": np.nan, "hi": np.nan})
            ss[nm] = v
        res[cell] = {"段": ss, "判定": verdict(ss), "上限": "最多暫定" if cell in BUY else ""}
    J = {"登錄": A["REG"], "裁定": RULING, "資料": A["sha"], "判定": res, "描述": {"|".join(k): v for k, v in A["DESC"].items()},
         "重疊": A["OVL"], "NOTES": NOTES, "完成": str(pd.Timestamp.now(tz="Asia/Taipei"))}
    json.dump(J, open(os.path.join(od, "formal.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=_js)
    open(os.path.join(od, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


def gate(argv):
    """→ ('dry', procs, limit) | ('formal', procs, None) | ('refuse', 訊息)。正式跑只認 --formal --ruling seq485。"""
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--dry", action="store_true"); ap.add_argument("--formal", action="store_true")
    ap.add_argument("--ruling", default=None); ap.add_argument("--procs", type=int, default=3); ap.add_argument("--limit", type=int, default=None)
    try:
        a, rest = ap.parse_known_args(argv)
    except SystemExit:
        return ("refuse", "⛔ 參數錯；拒跑")
    if rest:
        return ("refuse", f"⛔ 不認得的參數 {rest}；拒跑")
    if a.formal and a.dry:
        return ("refuse", "⛔ --formal 與 --dry 不可同時給；拒跑")
    if a.formal:
        if a.ruling != RULING:
            return ("refuse", f"⛔ 正式跑須 --formal --ruling {RULING}（裁定 seq485 §四：頻率表與描述欄乾跑核了才正式跑）；拒跑")
        if a.limit:
            return ("refuse", "⛔ 正式跑不可 --limit；拒跑")
        return ("formal", a.procs, None)
    if a.dry:
        return ("dry", a.procs, a.limit)
    return ("refuse", f"用法：--dry ｜ --formal --ruling {RULING}；拒跑")


def main():
    m = gate(sys.argv[1:])
    if m[0] == "refuse":
        sys.exit(m[1])
    A = run(dry=(m[0] == "dry"), procs=m[1], limit=m[2])
    (write_dry if m[0] == "dry" else write_formal)(A)


if __name__ == "__main__":
    main()
