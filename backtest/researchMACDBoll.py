# -*- coding: utf-8 -*-
"""MACD 柱翻正＋布林開口＋站上上揚 20 日線（Threads artur.rmm 原文）台股 seq1【頻率表＋全部描述欄乾跑／正式程式】——回測線計算子代理。

登錄：登錄全文-MACD柱翻正加布林開口加站上上揚20日線_Threads原文_單筆層加組合層登錄_台股策略線_seq1_shad2eadb7cad586731-5124B-20261029-1941.md
      （pw1 sha d2eadb7cad586731 ＝ 去掉末行 pw1 戳記後全文 sha256 前 16 碼；整檔 5124 B；整檔 sha256 d8d15190… ≠ ⇒ 照 pw1 慣例；回測線子代理 2026-10-29 19:5x 驗）
發號：裁定 seq487 §三（判定 2 格：單筆層 N_單筆 ＋1、組合層 N_組合 ＋1；單筆層照寫 95% CI）；發號附註：① 同檔可多次進出、不去重 ⇒ 必報每檔每月平均進出次數與 n_eff；
      ② ②「上下軌同時往外開」與 ③ 的 MA20 同一條中軌 ⇒ 照 §五 做等價自查；②③ 同日成立比例 ≥ 80% 先回信（seq377）；③ 加碼要 K < 50 ⇒ 照報觸發比例。
      先交頻率表（⛔ 不附報酬）＋描述欄乾跑（seq459 §一）。
⛔ 乾跑（--dry）：只數訊號、交易、配對、n_eff、出場原因（次數）、持有天數分布、加碼觸發、組合層名額（份數）；⛔ 不讀、不算、不存任何報酬／超額／勝率／權益／回落
   （seq366／458／459）；描述欄的報酬一律 0 佔位（只驗「欄填得出來」，輸出只寫 filled／EMPTY 與件數，⛔ 不寫值）。
⛔ 不 commit、不改既有檔；共用引擎一律 import（⛔ 不寫第二份）：researchGranville（merged_hl 高低價與其快取、match_day、deciles、cluster_boot、desc_stats、
   dry_status、segof、mkey、load_tri、overlap_rate）、researchRevTurn_freq（ensure_data、prices、back_ret）、researchIndMom_freq（reg_check、entry_flag、load_pit、build_panel、MAILBOX）、
   researchTriple_freq（market_map）、researchShortageExit（seam_open）、research11／data（load_stock 取成交量）、rerun17.H2D／researchAddOn.EOTC（最笨交易法世界日曆）。

用法（cd ~/tw-p17）：
    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMACDBoll --dry [--procs 3] [--limit N（煙霧測：隨機 N 檔，輸出 ~/macdwork/dry）]
        ⇒ 頻率表＋全部描述欄乾跑 → backtest/resultsMACDBoll/freq/
    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMACDBoll --formal --ruling seq487
        ⇒ 正式跑（⛔ 兩個旗標都要給、ruling 必須是 seq487，否則拒跑；⚠ 正式輸出尚未實作 ⇒ 目前一律拒跑，等頻率表核後再補）
    自測：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMACDBoll_check

══════════ 登錄寫死的（照抄，不改）══════════
 進場（三條件同一天）：① MACD 柱由負轉正 ② 布林開口放大 ③ 收盤站上 20 日線且 20 日線向上；訊號日 t 收盤判 ⇒ t+1 還原開盤買 1 份。
 指標（還原價）：MACD EMA12、EMA26、DIF＝EMA12−EMA26、DEA＝DIF 的 EMA9、柱＝DIF−DEA；翻正＝柱(t) > 0 且 柱(t−1) ≤ 0。
   布林：中軌 MA20、上下軌＝MA20 ± 2×20 日收盤標準差；開口放大＝上軌(t) > 上軌(t−1) 且 下軌(t) < 下軌(t−1)〔描述另一讀法：帶寬÷中軌 比 5 日前大 10% 以上〕。
   20 日線：收盤(t) > MA20(t) 且 MA20(t) > MA20(t−1)。KD：9 日 RSV、K、D 各 1/3 平滑；黃金交叉＝K(t) > D(t) 且 K(t−1) ≤ D(t−1)，且 K(t) < 50。
   量：成交量(t) > 前 5 日均量 × 1.5（續抱：只描述，不改出場）。
 母體：上市＋上櫃普通股（排除 DR、ETF、權證、創新板）；含已下市；流動性 20 日均量 ≥ 500 張（訊號日前一交易日）。處置股、全額交割股照母體閘。
 加碼：持有中出現 KD 條件 ⇒ 次日開盤加 1 份（每筆只加一次）。
 出場（先到者，次日開盤賣全部）：收盤 < MA20；MA20(t) < MA20(t−1)；收盤 ≤ 首次進場價 × 0.97。出場後隔一個交易日不得再進同檔（空手一天）；之後同檔可再進。
 成本 0.585% 來回；硬斷點 seq335；段：探索 2006-01～2015-12｜確認 2016-01 起。
 判定 1（單筆層）：每筆報酬（含加碼那份、以投入份數加權）− 對照平均；對照＝同訊號日、同產業（industry_pit）、市值十分位同、前 60 日報酬三分位同、當天沒訊號；
   每筆抽 1～3 檔（種子 20261029），同日進、同日出；通過（暫定）＝兩段平均差皆 > 0 且確認段月分群 95% CI 下緣 > 0；測不出＝其餘；還沒測＝任一段月分群 n_eff < 24。
 判定 2（組合層）：每筆 2 成、最多同時 5 筆；加碼也用 1 份、沒現金就不加；剩餘現金不計利息；同日訊號多於名額：抽籤（種子 20261029，200 次取中位）
   〔描述：成交量大者優先〕；合格＝兩段都 年化 > 大盤報酬指數（seq425），且 年化÷|最大回落| ≥ 大盤同一比值；0050 只當排名表一列。

══════════ ★ 執行者讀法（⛔ 在跑任何本件程式之前寫死於 2026-10-29 19:54～20:00（台北，WSL TZ=Asia/Taipei date；150 檔煙霧測 20:01 之前）；〔 〕內為另一讀法；皆取保守）══════════
 寫死前看過：登錄全文 seq1、裁定 seq487、researchGranville（★ 讀法、引擎）、researchDumb（讀法 Z1～Z5）、research11.load_bars、data.load_stock；⛔ 沒看過本件任何數字。
 ★1 資料：價格面板、壞根、閘 ＝ researchGranville ★1 同一套（researchRevTurn_freq.prices；rerun17 H2D 2015-01-05～2026-09-24 ＋ 早年 eotc 2004-02-11～2014-12-31 合併日曆；
     四碼普通股含已下市；壞根 ＝ 缺口 ≥5 日（seq335）∪ 價格斷點 ∪ 幽靈還原 ∪ crashwork ∪ 早年 reduce_v2；exright open_base（seq412）判開盤鎖漲停）。
     產業、exright、大盤報酬指數 data/history/market_tri.csv ＝ tw-stock-data 9b0e9882572c（＝ Granville 同一版）〔另一讀法：最新 origin/main〕。
     高、低價 ＝ researchGranville.merged_hl（research11.load_bars 同一還原、接縫倍數；快取 ~/grvwork/hl_*.pkl 唯讀沿用）；開盤 ＝ seam_open(PX)。
     成交量 ＝ data.load_stock 的原始成交股數（未還原；只用於 5 日均量比，量比在同一世界內算，跨世界接縫的窗不判）。
 ★2 指標一律數【該股自己的有效 K 棒】，並在壞根處切段重新起算（壞根當根 ＝ 新段第一根；Granville ★4 同式）〔另一讀法：數市場日曆、壞根只剔窗〕。
     EMA ＝ pandas ewm(span, adjust=False)，以段內第一根收盤起算；MACD 要段內第 61 根（索引 ≥ 60）起才可判（暖機 60 根）〔另一讀法：35 根（26＋9）〕。
     布林標準差 ＝ 母體標準差 ddof=0（Bollinger 原式）〔另一讀法：樣本 ddof=1〕；MA20、上下軌 min_periods＝20。
     三條件的可判 ＝ 段內索引 ≥ 60（含 t−1 的柱、MA20(t−1)、上下軌(t−1) 都有值）。
 ★3 不等式照字面：① 柱(t) > 0 且 柱(t−1) ≤ 0；② 嚴格 > 與 <；③ 嚴格 > 與 >；出場「收盤 < MA20」嚴格、「MA20(t) < MA20(t−1)」嚴格、停損「≤ 0.97×首次進場價」含等號；
     KD「K(t) < 50」嚴格；另一讀法開口：帶寬(t) ≥ 1.10 × 帶寬(t−5)（「大 10% 以上」含等號）。
 ★4 KD：RSV(t) ＝ (收盤 − 9 根最低) ÷ (9 根最高 − 9 根最低) × 100（含 t 的 9 根有效 K 棒，還原高低）；9 根最高 ＝ 最低（無區間）⇒ RSV ＝ 50〔另一讀法：沿用前一根 K〕；
     K、D 從段內第一個有 RSV 的根起算，前值 K＝D＝50；K(t) ＝ 2/3 K(t−1) ＋ 1/3 RSV(t)，D 同式；黃金交叉要 t−1 也有 K、D。
 ★5 閘 ＝ 面板 G[t]（Granville ★5 同一條：含 t 的 20 日都有成交 ∧ t−20～t−1 均量 ≥ 500 張 ∧ pit_valid）〔另一讀法：G[t−1]〕；訊號 ＝ ①∧②∧③∧G[t]。
     ⛔ 不去重（登錄：同檔可多次進出）；但同一檔同時只持一筆：持有中出現的新訊號不另進場（加碼只走 KD 條件）〔另一讀法：無（登錄只允許 KD 加碼）〕。
 ★6 進場：e ＝ t＋1（合併日曆）；IMF.entry_flag（壞根(t,e]、e 無成交、e 開盤鎖漲停 ⇒ 不進，次數照報）；被擋的訊號不佔「持有」，同檔之後的訊號照常判。
 ★7 出場：觸發看 [e, 第一個壞根−1] 每根有效 K 棒收盤（含進場當天 e 的收盤）；觸發日 d ⇒ d 之後第一根有效 K 棒開盤賣；同一根觸發多個條件 ⇒ 原因記成組合（如「跌破MA20+停損3%」），
     原因分布另報各條件的命中率（可重複計）。停損價 ＝ 0.97 × e 的還原開盤（首次進場價；加碼不改停損）。
     賣出根 s 已跨壞根（(d, s] 有壞根）⇒ d 收盤強制出；觸發後沒有下一根：已下市（末根距資料尾 ≥ 5 日）⇒ d 收盤；否則 ＝ 資料尾、d 收盤計值。
     未觸發：持有期遇壞根 ⇒ 壞根前最後一根有效收盤強制出；下市 ⇒ 末根收盤；到資料尾仍持有 ⇒ 資料尾收盤計值（記「資料尾未出」）。
     ★ seq373：賣出根 s 同時是強制收盤出場根（s 之後下一根有效 K 棒是壞根、或 s 是下市末根）⇒ 該根有「開盤（觸發）」「收盤（強制）」兩個出場價 ⇒ 取較低
     （Granville ★8 cap 根同式）〔另一讀法：只取開盤〕。⚠ 本件沒有最長持有天數 ⇒ 這種同根兩價只在壞根／下市前一根發生，件數照報。
     持有天數 ＝ 出場位置 − e（合併日曆）。
 ★8 空手一天：出場位置 x（開盤賣或收盤強制出那一根）⇒ x＋1 不得進同檔 ⇒ 同檔下一筆訊號日 t 要 ≥ x＋1（進場 ≥ x＋2）〔另一讀法：t ≥ x（只禁當天再買）〕；
     「交易日」數合併日曆。持有中（t < x）與空手日（t ＝ x）被擋的訊號分開計數。
 ★9 加碼：持有中（e ≤ k < d，觸發日當天不加——出場優先）第一個「K、D 黃金交叉且 K < 50」的根 k ⇒ k＋1 開盤加 1 份；k＋1 過不了 entry_flag（無成交、鎖漲停、壞根）
     ⇒ 這次不算、等下一個 KD 條件（每筆最多「實際加成」一次）〔另一讀法：第一個 KD 條件就用掉機會〕；含進場當天 e 的收盤〔另一讀法：k ≥ e＋1〕。
     加碼觸發比例（主讀法）＝ 有實際加碼的筆數 ÷ 交易筆數；另報「持有中出現過 KD 條件」比例與被擋次數。
 ★10 單筆層樣本：每一筆交易都算（含資料尾計值者，件數照報）〔另一讀法：剔除資料尾未出〕——用實際出場決定入不入樣本是前視（Granville ★9 同理）；
     段與月分群依訊號日 t（年月）〔另一讀法：依進場日〕；n_eff ＝ 該段主格交易的訊號月數；主格 ＝ 配到 ∧ 有進場；2004～2005 ＝ 段外（照報）。
     每檔每月平均進出次數（附註①）：主讀法 ＝ 主格交易數 ÷ 有交易的（代號、訊號月）組數；另報分布（1／2／3／4／5＋）與最大值、全部交易（不限配到）版本。
 ★11 對照池（每筆的訊號日 t）：G[t] 過閘、t 有有效 K 棒、非本股、entry_flag(j,t,t+1) ＝ 保留、同產業（IMF.load_pit 在 t；「其他」也算一類、無類別 ⇒ 配不到）、
     市值十分位同、前 60 日報酬三分位同（分位母體 ＝ t 過閘且有有效 K 棒的面板股；Granville ★11 同法、r60 向量化並對 back_ret 抽樣對帳）；
     「當天沒訊號」＝ 該股 t 當天原始 ①∧②∧③ 為假（不論閘）〔另一讀法：只排除過閘訊號〕；不要求對照「當時沒持有」。
     候選 ≥ 3 抽 3、否則全取；np.random.default_rng(20261029) 每個版本各起一條，事件依（t, 代號）序。對照同日進（e 開盤）同日出（同一出場位置與方式）；
     加碼那份：對照在同一加碼根開盤也加 1 份（份數加權同訊號）〔另一讀法：對照只 1 份〕。對照在出場根沒成交／遇自己的壞根 ⇒ 次數照報（正式跑才定價）。
 ★12 單筆統計：月分群放回抽月、統計量 ＝ 抽中月份全部交易差的平均（交易加權）、10,000 次、種子 20261029、95% ＝ 第 2.5／97.5 百分位（Granville cluster_boot，alpha＝0.05）。
 ★13 組合層：份數制——總資金 5 份、每次進場或加碼用 1 份（2 成）；同時最多 5 份在場（加碼佔份數，故實際最多 5 檔、加碼後可少於 5 檔）〔另一讀法：5 筆不含加碼份〕；
     ⛔ 乾跑不算權益 ⇒ 名額、閒置比例都以份數計（正式跑用 2 成 × 當時權益）。每段各自從全現金開跑，段尾仍持有者在段尾計值（次數照報）〔另一讀法：一條連續權益切段〕。
     每日順序：開盤先賣（開盤出場）→ 新進場（前一日訊號）→ 加碼；收盤強制出場在當天收盤釋出份數（次一日可用）。
     新進場候選 ＝ t ＝ p−1 過閘訊號 ∧ 該股未持有 ∧ 符合空手一天（組合自己的出場位置）∧ entry_flag 保留；候選多於空份數 ⇒ 抽籤（候選依代號排序後
     default_rng([20261029, r]).permutation，r ＝ 0～199）；200 次各統計量取中位〔另一讀法：單一 rng 連抽〕。
     加碼在新進場之後、有空份才加（「沒現金就不加」⇒ 加碼是剩餘現金用途）〔另一讀法：加碼優先〕；沒份數 ⇒ 這次不加、等下一個可加碼根（同 ★9）。
     成交量大者優先（描述）：同日候選依訊號日原始成交股數由大到小（同量依代號），1 次。
     「名額不足的日子」＝ 當天新進場候選數 > 當天開盤可用份數（分母 ＝ 段內交易日；另報分母 ＝ 有候選的日子）。「5 份全滿」＝ 當天進場後空份 ＝ 0；閒置比例 ＝ 空份 ÷ 5 的日平均。
 ★14 等價自查（§五＋附註②，seq377）：母體 ＝ 過閘且三條件皆可判的股日（各段）；報 P(③|②)、P(②|③)、Jaccard(②,③)、P(③|①∧②)、P(②|①∧③)；
     P(①|②∧③)、P(②|①∧③)、P(③|①∧②)（＝ 某一條是否被另兩條蘊含 ⇒ 100% 即等價、拿掉該條訊號逐位元相同）；①② 同日：P(②|①)、P(①|②)、Jaccard。
     主讀法（附註②「②③ 同日成立比例」）＝ P(③|②)；⚠ 任一讀法 ≥ 80% 即旗標（保守）；主讀法 ≥ 80% ⇒ seq377 先回信、不正式跑。
     另做拆件逐位元比對：拿掉 ①／②／③ 的訊號集合與主格是否逐位元相同（相同 ⇒ 該條等價、seq377 先回信）。
     與「最笨的交易法」重疊：backtest/resultsDumb/rows_{主,早年}_F1.csv.gz 的 sid、t（⛔ 只讀這兩欄）⇒ 該世界自己的日曆（rerun17.H2D／researchAddOn.EOTC 的 load_calendar）
     轉日期；同日（主讀法）與 ±20 個交易日，雙向（Granville overlap_rate 同式）。
 ★15 拆件（描述，⛔ 不判）：拿掉 ①、②、③ 各一條；拿掉加碼（交易同主格、只差份數）；改另一讀法開口放大 ⇒ 各自整套重跑（訊號、交易、配對），頻率照報。
 沿革：20:03 煙霧測（150 檔，數字非本件結果）後只改一處輸出結構：「拿掉加碼」版本的「加碼那份報酬」描述欄依構造不存在 ⇒ 不列（原本會被數成 EMPTY）；★ 讀法一字未改。
 ★16 對大盤報酬指數（seq425）：market_tri.csv（9b0e98 版）；單筆層描述：訊號 t 收盤 → 出場日收盤（指數只有收盤），不扣成本（Granville ★17 同式）；
     組合層判定基準 ＝ 同段指數年化與 年化÷|最大回落|。上市／上櫃 ＝ meta/stocks.csv∪delisted.csv 的 market（last_seen 值，陷阱 15 照註）。
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import pickle
import sys
import time
from collections import Counter, defaultdict
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchGranville as GV                # noqa: E402  merged_hl、match_day、deciles、cluster_boot、desc_stats、dry_status、segof、mkey、load_tri、overlap_rate
from backtest import researchRevTurn_freq as RT             # noqa: E402  ensure_data、prices、back_ret
from backtest import researchIndMom_freq as IMF             # noqa: E402  reg_check、entry_flag、load_pit、build_panel、MAILBOX
from backtest import researchTriple_freq as TP              # noqa: E402  market_map
from backtest import researchShortageExit as SM             # noqa: E402  seam_open
from backtest import research11 as R                        # noqa: E402  R.D（data.load_stock、load_calendar）

REG_SHA = "d2eadb7cad586731"
REG_BYTES = 5124
RULING = "seq487"
DATA_SHA = GV.DATA_SHA
OUT = "backtest/resultsMACDBoll"
WORK = os.path.expanduser("~/macdwork")
SEED = 20261029
COST = 0.00585
NEFF_MIN = 24
NBOOT = 10000
ALPHA = 0.05
SEGS = GV.SEGS
MACD_WARM = 60
STOP = 0.97
UNITS = 5
NDRAW = 200
FLAT = 1
VOLX = 1.5
BW_ALT = 1.10
VARIANTS = ["主", "拿掉①", "拿掉②", "拿掉③", "另一讀法②", "拿掉加碼"]
NOTES = ["乾跑：未讀、未算、未存任何報酬、超額、勝率、權益、回落（seq366／458／459）；描述欄報酬以 0 佔位，只報 filled／EMPTY",
         "同檔可多次進出、不去重（登錄 §〇、裁定 seq487 附註①）⇒ 每檔每月平均進出次數與 n_eff 必報",
         "②（上下軌同時往外開）與 ③（MA20 上揚）共用同一條中軌（附註②）⇒ 等價自查照 ★14 報、任一讀法 ≥ 80% 旗標",
         "加碼要 K < 50（附註③）⇒ 觸發比例照報",
         "組合層乾跑以份數計（每份 2 成、5 份），正式跑才以權益計",
         "早年上櫃日 K 2007-07 起；價格面板資料尾 2026-09-24（rerun17 H2D edc6f）",
         "上市／上櫃以 meta 名冊 market（last_seen 值）分，轉市場者歸最後市場（陷阱 15）",
         "原文宣稱（7 年 15 萬→500 萬、最大回撤 < 15%）不當先驗，只照規則測（登錄聲明、裁定 seq487）"]
BANNED = GV.BANNED
LOG: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


RT.log = log
GV.log = log


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
    rul = [f for f in glob.glob(os.path.join(IMF.MAILBOX, "*.md")) if RULING in os.path.basename(f) and "MACD" in os.path.basename(f)]
    if not rul:
        raise SystemExit(f"⛔ 信箱找不到裁定 {RULING}")
    return {"登錄": name, "bytes": len(b), "整檔sha前16": whole, "整檔相符": whole == REG_SHA, "pw1去戳記相符": True,
            "裁定": os.path.basename(rul[0])}


# ═════════════ 指標（單一無壞根段；自測直接呼叫）═════════════
def shift(a, k, fill):
    a = np.asarray(a)
    out = np.empty_like(a)
    if k <= 0:
        return a.copy()
    out[:k] = fill; out[k:] = a[:-k]
    return out


def ema(x, span):
    return pd.Series(np.asarray(x, float)).ewm(span=span, adjust=False).mean().to_numpy(float)


def macd_hist(c):
    dif = ema(c, 12) - ema(c, 26)
    dea = ema(dif, 9)
    return dif - dea


def turn_pos(h):
    """① 柱(t) > 0 且 柱(t−1) ≤ 0。"""
    h = np.asarray(h, float); p = shift(h, 1, np.nan)
    with np.errstate(invalid="ignore"):
        return np.isfinite(h) & np.isfinite(p) & (h > 0) & (p <= 0)


def boll(c, ddof=0):
    s = pd.Series(np.asarray(c, float))
    ma = s.rolling(20, min_periods=20).mean().to_numpy(float)
    sd = s.rolling(20, min_periods=20).std(ddof=ddof).to_numpy(float)
    return ma, ma + 2.0 * sd, ma - 2.0 * sd


def widen(ub, lb):
    """② 上軌(t) > 上軌(t−1) 且 下軌(t) < 下軌(t−1)。"""
    pu = shift(ub, 1, np.nan); pl = shift(lb, 1, np.nan)
    with np.errstate(invalid="ignore"):
        return np.isfinite(ub) & np.isfinite(pu) & np.isfinite(lb) & np.isfinite(pl) & (ub > pu) & (lb < pl)


def widen_alt(ub, lb, ma):
    """②（另一讀法）帶寬÷中軌 ≥ 1.10 × 5 根前。"""
    with np.errstate(invalid="ignore", divide="ignore"):
        bw = (ub - lb) / ma
        p = shift(bw, 5, np.nan)
        return np.isfinite(bw) & np.isfinite(p) & (bw >= BW_ALT * p)


def above_rising(c, ma):
    """③ 收盤 > MA20 且 MA20(t) > MA20(t−1)。"""
    pm = shift(ma, 1, np.nan)
    with np.errstate(invalid="ignore"):
        return np.isfinite(ma) & np.isfinite(pm) & (c > ma) & (ma > pm)


def kd(c, h, l):
    c = np.asarray(c, float); h = np.asarray(h, float); l = np.asarray(l, float)
    m = len(c)
    hh = pd.Series(h).rolling(9, min_periods=9).max().to_numpy(float)
    ll = pd.Series(l).rolling(9, min_periods=9).min().to_numpy(float)
    K = np.full(m, np.nan); D = np.full(m, np.nan)
    kp, dp = 50.0, 50.0
    for t in range(m):
        if not (np.isfinite(hh[t]) and np.isfinite(ll[t]) and np.isfinite(c[t])):
            continue
        rng_ = hh[t] - ll[t]
        rsv = 50.0 if rng_ <= 0 else (c[t] - ll[t]) / rng_ * 100.0
        kp = kp * 2.0 / 3.0 + rsv / 3.0
        dp = dp * 2.0 / 3.0 + kp / 3.0
        K[t] = kp; D[t] = dp
    return K, D


def kd_gc(K, D):
    """KD 黃金交叉且 K < 50：K(t) > D(t)、K(t−1) ≤ D(t−1)、K(t) < 50。"""
    pk = shift(K, 1, np.nan); pd_ = shift(D, 1, np.nan)
    with np.errstate(invalid="ignore"):
        return np.isfinite(K) & np.isfinite(D) & np.isfinite(pk) & np.isfinite(pd_) & (K > D) & (pk <= pd_) & (K < 50)


def vol_spike(v):
    """量(t) > 前 5 根均量 × 1.5（描述）。"""
    v = np.asarray(v, float)
    p5 = pd.Series(v).shift(1).rolling(5, min_periods=5).mean().to_numpy(float)
    with np.errstate(invalid="ignore"):
        return np.isfinite(v) & np.isfinite(p5) & (p5 > 0) & (v > VOLX * p5)


def seg_features(c, h, l, v=None):
    """c／h／l／v：同一無壞根段的有效 K 棒（還原價；v 原始股數）。只用 ≤ 當根的資料。"""
    c = np.asarray(c, float); m = len(c)
    hist = macd_hist(c)
    ma, ub, lb = boll(c)
    J = np.arange(m) >= MACD_WARM
    C1 = turn_pos(hist) & J
    C2 = widen(ub, lb) & J
    C2a = widen_alt(ub, lb, ma) & J
    C3 = above_rising(c, ma) & J
    pm = shift(ma, 1, np.nan)
    with np.errstate(invalid="ignore"):
        XB = np.isfinite(ma) & (c < ma)
        XD = np.isfinite(ma) & np.isfinite(pm) & (ma < pm)
    K, D = kd(c, h, l)
    GC = kd_gc(K, D)
    VS = vol_spike(v) if v is not None else np.zeros(m, bool)
    return {"J": J, "C1": C1, "C2": C2, "C2a": C2a, "C3": C3, "XB": XB, "XD": XD, "GC": GC, "VS": VS, "MA": ma, "H": hist, "K": K}


FKEYS = ["J", "C1", "C2", "C2a", "C3", "XB", "XD", "GC", "VS"]


def stock_features(c, h, l, v, bad, vseam=None):
    """有效 K 棒序列（含壞根旗標）⇒ 依壞根切段逐段 seg_features 再接回（Granville stock_features 同一切法）。
    vseam：布林，True 的根（跨世界接縫後 5 根）量比不判。"""
    n = len(c)
    starts = sorted(set([0] + [int(k) for k in np.flatnonzero(bad) if k > 0]))
    ends = starts[1:] + [n]
    out = {k: np.zeros(n, bool) for k in FKEYS}
    for a, b in zip(starts, ends):
        F = seg_features(c[a:b], h[a:b], l[a:b], None if v is None else v[a:b])
        for k in FKEYS:
            out[k][a:b] = F[k]
    if vseam is not None:
        out["VS"] &= ~np.asarray(vseam, bool)
    return out


# ═════════════ 出場與加碼（★7、★9；自測直接呼叫）═════════════
def exit_sim(c, o, xb, xd, gc, bad, e, cend, lastv, addon_ok, addon=True):
    """單檔、日曆列：c、o（還原）、xb（收盤<MA20）、xd（MA20 下彎）、gc（KD 條件）、bad（壞根）。
    addon_ok(k, a)：k 根 KD 條件 ⇒ a＝k+1 開盤能否加碼（entry_flag 保留）。
    回 dict：x（出場位置）、kind（open｜close｜minoc）、reason、trig（觸發條件集合）、A（實際加碼根或 None）、Alist（全部可加碼根）、
           kd_seen（持有中出現過 KD 條件）、kd_blocked（KD 條件但 a 過不了）、flags、done（False＝資料尾計值）、d（觸發日或 None）。只看位置與原因、⛔ 不算報酬。"""
    P0 = float(o[e]); stop = P0 * STOP
    flags = []
    bb = np.flatnonzero(np.asarray(bad[e + 1:cend + 1], bool))
    kb = e + 1 + int(bb[0]) if len(bb) else None
    lim = kb if kb is not None else cend + 1
    delist = bool(lastv < cend and (cend - lastv) >= 5)
    Alist = []; kd_seen = False; kd_blocked = 0
    d = None; trig = ()
    for k in range(e, lim):
        if not np.isfinite(c[k]):
            continue
        s_ = bool(c[k] <= stop); b_ = bool(xb[k]); m_ = bool(xd[k])
        if s_ or b_ or m_:
            d = k; trig = tuple(n for n, f in (("跌破MA20", b_), ("MA20下彎", m_), ("停損3%", s_)) if f)
            break
        if gc[k]:
            kd_seen = True
            if k + 1 <= cend and addon_ok(k, k + 1):
                Alist.append(k + 1)
            else:
                kd_blocked += 1
    A = (Alist[0] if (addon and Alist) else None)

    def res(x, kind, reason, done=True):
        return {"x": int(x), "kind": kind, "reason": reason, "trig": trig, "A": A, "Alist": (Alist if addon else []), "kd_seen": kd_seen,
                "kd_blocked": kd_blocked, "flags": flags, "done": done, "d": d}
    if d is not None:
        lab = "+".join(trig)
        nxt = np.flatnonzero(np.isfinite(c[d + 1:cend + 1]))
        if not len(nxt):
            if delist:
                return res(d, "close", lab + "→下市末根")
            return res(d, "close", lab + "→資料尾", done=False)
        s = d + 1 + int(nxt[0])
        if np.asarray(bad[d + 1:s + 1], bool).any():
            return res(d, "close", lab + "→壞根前強制出")
        nn = np.flatnonzero(np.isfinite(c[s + 1:cend + 1]))
        forced = (len(nn) and bool(np.asarray(bad[s + 1:s + 1 + int(nn[0]) + 1], bool).any())) or (s == lastv and delist)
        if forced:
            flags.append("同根取較低")
            return res(s, "minoc", lab)
        return res(s, "open", lab)
    if kb is not None:
        lv = np.flatnonzero(np.isfinite(c[e:kb]))
        return res(e + int(lv[-1]), "close", "壞根前強制出")
    if delist:
        return res(int(lastv), "close", "下市末根")
    lv = np.flatnonzero(np.isfinite(c[e:cend + 1]))
    return res(e + int(lv[-1]), "close", "資料尾未出", done=False)


def exit_price(c, o, x, kind):
    """（正式跑用）出場價：open ＝ x 開盤；close ＝ x 收盤；minoc ＝ min(開, 收)（seq373）。"""
    if kind == "open":
        return float(o[x])
    if kind == "minoc":
        return float(min(o[x], c[x]))
    return float(c[x])


def sim_stock(sigs, eflag, exit_fn, cend):
    """單筆層：同一檔依訊號日序列逐筆（★5、★6、★8）。sigs：過閘訊號日（遞增）；eflag(t) ⇒ 保留／原因；exit_fn(e) ⇒ exit_sim 結果。
    回 (trades, skips Counter)。trades：dict(t, e, X)。"""
    trades = []; sk = Counter()
    busy_until = -1; flat_until = -1                                    # t < busy_until ⇒ 持有中；t < flat_until ⇒ 空手日
    for t in sigs:
        if t < busy_until:
            sk["持有中"] += 1; continue
        if t < flat_until:
            sk["空手一天"] += 1; continue
        if t + 1 > cend:
            sk["e超出資料尾"] += 1; continue
        f = eflag(t)
        if f != "保留":
            sk[f] += 1; continue
        X = exit_fn(t + 1)
        trades.append({"t": t, "e": t + 1, "X": X})
        busy_until = X["x"]; flat_until = X["x"] + FLAT
    return trades, sk


# ═════════════ 組合層（★13；份數制；自測直接呼叫）═════════════
def portfolio(pa, pb, sig_by_t, get_trade, order, units=UNITS):
    """pa..pb：段內合併日曆位置（含）。sig_by_t：t ⇒ [股 i]（過閘訊號，依代號序）。get_trade(i, t) ⇒ exit_sim 結果或 None（entry_flag 不過）。
    order(cands, p) ⇒ 排序後的候選（抽籤或量大優先）。回統計 dict（只份數與次數；⛔ 無報酬）。"""
    held = {}                                                           # i ⇒ {X, u, added, ai}
    last_x = {}
    free = units
    days = 0; full = 0; idle = 0.0; short = 0; candd = 0; shortc = 0; hold_n = 0.0
    taken = 0; skipped_slots = 0; add_ok = 0; add_blocked = 0; flat_skip = 0; held_skip = 0
    by_year = Counter()
    for p in range(pa, pb + 1):
        # 開盤賣、前一日收盤強制出
        for i in list(held):
            X = held[i]["X"]
            if (X["kind"] in ("open", "minoc") and X["x"] == p) or (X["kind"] == "close" and X["x"] < p):
                free += held[i]["u"]; last_x[i] = X["x"]; del held[i]
        # 新進場（前一日訊號）
        cands = []
        if p - 1 >= pa:
            for i in sig_by_t.get(p - 1, ()):
                if i in held:
                    held_skip += 1; continue
                if i in last_x and (p - 1) < last_x[i] + FLAT:
                    flat_skip += 1; continue
                X = get_trade(i, p - 1)
                if X is None:
                    continue
                cands.append((i, X))
        if cands:
            candd += 1
            if len(cands) > free:
                short += 1; shortc += 1
        for i, X in order(cands, p):
            if free <= 0:
                skipped_slots += 1; continue
            held[i] = {"X": X, "u": 1, "added": False, "ai": 0}; free -= 1; taken += 1; by_year[p] += 1
        # 加碼
        for i in sorted(held):
            h = held[i]
            if h["added"]:
                continue
            AL = h["X"]["Alist"]
            while h["ai"] < len(AL) and AL[h["ai"]] < p:
                h["ai"] += 1
            if h["ai"] < len(AL) and AL[h["ai"]] == p:
                if free > 0:
                    h["u"] += 1; h["added"] = True; free -= 1; add_ok += 1
                else:
                    add_blocked += 1; h["ai"] += 1
        days += 1
        full += int(free == 0); idle += free / units; hold_n += len(held)
    return {"交易日": days, "5份全滿日比例": full / days if days else None, "閒置份數比例(日平均)": idle / days if days else None,
            "名額不足日比例(分母交易日)": short / days if days else None, "名額不足日比例(分母有候選日)": shortc / candd if candd else None,
            "有候選日": candd, "進場筆數": taken, "因名額未進筆數": skipped_slots, "加碼成功": add_ok, "加碼因無份數未加(次)": add_blocked,
            "平均持股檔數": hold_n / days if days else None, "段尾仍持有": len(held), "空手一天擋": flat_skip, "持有中訊號": held_skip,
            "進場位置": by_year}


def lottery_order(sids, r):
    rng = np.random.default_rng([SEED, r])

    def f(cands, p):
        if not cands:
            return cands
        cs = sorted(cands, key=lambda z: sids[z[0]])
        return [cs[k] for k in rng.permutation(len(cs))]
    return f


def volume_order(sids, V):
    def f(cands, p):
        return sorted(cands, key=lambda z: (-(V[z[0], p - 1] if np.isfinite(V[z[0], p - 1]) else -1.0), sids[z[0]]))
    return f


# ═════════════ 等價自查（★14；自測直接呼叫）═════════════
def cond_share(a, b):
    """P(b | a)：a 成立的股日中 b 也成立的比例；回 (分母, 分子, 比例)。"""
    a = np.asarray(a, bool); b = np.asarray(b, bool)
    n = int(a.sum()); k = int((a & b).sum())
    return n, k, (k / n if n else None)


def jaccard(a, b):
    a = np.asarray(a, bool); b = np.asarray(b, bool)
    u = int((a | b).sum()); i = int((a & b).sum())
    return u, i, (i / u if u else None)


def equiv_table(C1, C2, C3):
    rows = []
    for lab, (x, y) in {"P(③|②)【主讀法】": (C2, C3), "P(②|③)": (C3, C2), "P(③|①∧②)": (C1 & C2, C3), "P(②|①∧③)": (C1 & C3, C2),
                        "P(①|②∧③)": (C2 & C3, C1), "P(②|①)": (C1, C2), "P(①|②)": (C2, C1)}.items():
        n, k, s = cond_share(x, y)
        rows.append({"讀法": lab, "分母": n, "分子": k, "比例": s})
    for lab, (x, y) in {"Jaccard(②,③)": (C2, C3), "Jaccard(①,②)": (C1, C2)}.items():
        n, k, s = jaccard(x, y)
        rows.append({"讀法": lab, "分母": n, "分子": k, "比例": s})
    return rows


# ═════════════ 資料：成交量（★1）═════════════
_VJ: dict = {}


def _vol_job(sid):
    Z = _VJ["Z"]
    R.D.DATA = Z["data"]
    st = R.D.load_stock(sid, Z["mk"].get(sid, "twse"), Z["cal"])
    if st is None:
        return sid, None
    df = st.df
    idx = np.flatnonzero(df["traded"].to_numpy())
    return sid, (idx.astype(np.int64), df["volume"].to_numpy(float)[idx])


def vol_world(wn, procs):
    cp = os.path.join(WORK, f"vol_{wn}.pkl")
    if os.path.exists(cp):
        return pickle.load(open(cp, "rb"))
    Z = IMF.build_panel(wn, procs, log)
    _VJ["Z"] = Z
    ix = {s: k for k, s in enumerate(Z["sids"])}
    V = np.full(Z["C"].shape, np.nan); cnt = Counter()
    with Pool(procs) as pool:
        for sid, r in pool.imap_unordered(_vol_job, Z["sids"], chunksize=8):
            if r is None:
                cnt["無"] += 1; continue
            idx, v = r
            idx = idx[idx < V.shape[1]]
            V[ix[sid], idx] = v[:len(idx)]; cnt["檔"] += 1
    out = {"sids": list(Z["sids"]), "V": V, "info": dict(cnt)}
    pickle.dump(out, open(cp, "wb"), protocol=5)
    log(f"[量 {wn}] {out['info']} ⇒ {cp}")
    return out


def merged_vol(PX, procs):
    N, NC, NE = len(PX["SIDS"]), len(PX["CAL"]), PX["NE"]
    Vm = np.full((N, NC), np.nan); info = {}
    for wn, sl in (("早年", slice(0, NE)), ("主", slice(NE, NC))):
        X = vol_world(wn, procs)
        if X["V"].shape[1] != (sl.stop - sl.start):
            raise SystemExit(f"⛔ 量 {wn} 日曆長 {X['V'].shape[1]} ≠ 面板 {sl.stop - sl.start}")
        wix = {s: k for k, s in enumerate(X["sids"])}
        for i, s in enumerate(PX["SIDS"]):
            if s in wix:
                Vm[i, sl] = X["V"][wix[s]]
        info[wn] = X["info"]
    return Vm, info


# ═════════════ 最笨交易法訊號（★14）═════════════
def dumb_signals():
    from backtest import rerun17 as RR
    from backtest import researchAddOn as RA
    keep = R.D.DATA
    fr = []
    info = {}
    for wn, data in (("主", RR.H2D), ("早年", RA.EOTC)):
        R.D.DATA = data
        cal = R.D.load_calendar()
        f = f"backtest/resultsDumb/rows_{wn}_F1.csv.gz"
        x = pd.read_csv(f, usecols=["sid", "t"], dtype={"sid": str})
        t = x["t"].astype(np.int64).to_numpy()
        ok = (t >= 0) & (t < len(cal))
        fr.append(pd.DataFrame({"sid": x["sid"].str.strip()[ok], "date": [str(d.date()) for d in cal[t[ok]]]}))
        info[wn] = {"列": int(len(x)), "日曆外": int((~ok).sum()), "日曆": f"{cal[0].date()}～{cal[-1].date()}"}
    R.D.DATA = keep
    return pd.concat(fr).drop_duplicates().reset_index(drop=True), info


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
    PX["O"] = O
    Hs, Ls, hlinfo = GV.merged_hl(PX, procs)
    V, vinfo = merged_vol(PX, procs)
    VALID = np.isfinite(C)
    log(f"[高低量] {hlinfo}｜量 {vinfo}｜開盤接縫 {nseam}｜{time.time() - t0:.0f}s")
    SUB = np.ones(N, bool)
    if limit:
        rr = np.random.default_rng(SEED); pick = set(rr.choice(N, limit, replace=False).tolist())
        SUB = np.array([k in pick for k in range(N)])
    # ── 特徵 ⇒ 日曆陣列
    FL = {k: np.zeros((N, NC), bool) for k in FKEYS}
    for i in range(N):
        if not SUB[i]:
            continue
        vp = VP[i]
        if len(vp) < MACD_WARM + 1:
            continue
        vseam = np.zeros(len(vp), bool)                               # 跨世界接縫：主世界前 5 根有效 K 棒的前 5 根窗含早年量 ⇒ 不判
        if vp[0] < NE:
            q0 = int(np.searchsorted(vp, NE)); vseam[q0:q0 + 5] = True
        F = stock_features(C[i, vp], Hs[i, vp], Ls[i, vp], V[i, vp], BAD[i, vp], vseam)
        for k in FKEYS:
            FL[k][i, vp] = F[k]
    log(f"[特徵] {time.time() - t0:.0f}s")
    SIGRAW = {"主": FL["C1"] & FL["C2"] & FL["C3"], "拿掉①": FL["C2"] & FL["C3"] & FL["J"], "拿掉②": FL["C1"] & FL["C3"],
              "拿掉③": FL["C1"] & FL["C2"], "另一讀法②": FL["C1"] & FL["C2a"] & FL["C3"]}
    SIGRAW["拿掉加碼"] = SIGRAW["主"]
    GS = G & SUB[:, None]
    seg_pos = {}
    for nm, a, b in SEGS:
        pa = int(CAL.searchsorted(pd.Timestamp(a))); pb = int(CAL.searchsorted(pd.Timestamp(b), side="right")) - 1
        seg_pos[nm] = (pa, min(pb, CEND))
    # ── 等價自查（★14）
    EQ = []
    for nm, (pa, pb) in seg_pos.items():
        m = GS[:, pa:pb + 1] & FL["J"][:, pa:pb + 1]
        c1, c2, c3 = FL["C1"][:, pa:pb + 1][m], FL["C2"][:, pa:pb + 1][m], FL["C3"][:, pa:pb + 1][m]
        for r_ in equiv_table(c1, c2, c3):
            EQ.append({"段": nm, "母體(過閘且可判股日)": int(m.sum()), **r_, "≥80%旗標": bool(r_["比例"] is not None and r_["比例"] >= 0.8)})
        EQ.append({"段": nm, "母體(過閘且可判股日)": int(m.sum()), "讀法": "①、②、③ 各自成立股日", "分母": int(m.sum()),
                   "分子": f"{int(c1.sum())}/{int(c2.sum())}/{int(c3.sum())}", "比例": None, "≥80%旗標": False})
    for r_ in EQ:
        if r_["≥80%旗標"]:
            log(f"⚠ [等價旗標] {r_}")
    # ── 單筆層：各版本逐檔模擬
    eflag_memo = {}

    def eflag(i, t):
        k = (i, t)
        if k not in eflag_memo:
            eflag_memo[k] = IMF.entry_flag(PX, i, t, t + 1) if t + 1 <= CEND else "e超出資料尾"
        return eflag_memo[k]
    xmemo = {}

    def get_exit(i, e, addon=True):
        k = (i, e, addon)
        if k not in xmemo:
            xmemo[k] = exit_sim(C[i], O[i], FL["XB"][i], FL["XD"][i], FL["GC"][i], BAD[i], e, CEND, int(LASTV[i]),
                                lambda kk, a, i=i: eflag(i, kk) == "保留", addon=addon)
        return xmemo[k]
    MKT = TP.market_map(DN)
    TR = {}; SKIP = {}; SIGN = {}
    for vn in VARIANTS:
        S_ = SIGRAW[vn] & GS
        SIGN[vn] = {"原始訊號(不論閘)": int((SIGRAW[vn] & SUB[:, None]).sum()), "過閘訊號": int(S_.sum())}
        rows = []; sk = Counter()
        addon = vn != "拿掉加碼"
        for i in range(N):
            if not SUB[i]:
                continue
            sigs = np.flatnonzero(S_[i]).tolist()
            if not sigs:
                continue
            tr, s_ = sim_stock(sigs, lambda t, i=i: eflag(i, t), lambda e, i=i, ad=addon: get_exit(i, e, ad), CEND)
            sk.update(s_)
            for z in tr:
                X = z["X"]; d = CAL[z["t"]]
                rows.append({"i": i, "sid": SIDS[i], "t": z["t"], "e": z["e"], "date": str(d.date()), "段": GV.segof(d), "月": GV.mkey(d), "年": d.year,
                             "市場": MKT.get(SIDS[i], "?"), "x": X["x"], "出場方式": X["kind"], "出場原因": X["reason"], "觸發": "+".join(X["trig"]),
                             "加碼根": (-1 if X["A"] is None else X["A"]), "KD條件出現": X["kd_seen"], "KD被擋": X["kd_blocked"],
                             "旗標": "|".join(X["flags"]), "完成": X["done"], "持有天數": X["x"] - z["e"],
                             "觸發日量比>1.5": (bool(FL["VS"][i, X["d"]]) if X["d"] is not None else None)})
        E = pd.DataFrame(rows)
        if len(E):
            E = E.sort_values(["t", "sid"]).reset_index(drop=True)
        TR[vn] = E; SKIP[vn] = dict(sk)
        log(f"[交易 {vn}] 訊號 {SIGN[vn]}｜交易 {len(E)}｜擋 {dict(sk)}｜{time.time() - t0:.0f}s")
    # ── 拆件逐位元比對（★14）
    BITEQ = {vn: bool(np.array_equal(SIGRAW[vn] & GS, SIGRAW["主"] & GS)) for vn in ("拿掉①", "拿掉②", "拿掉③", "另一讀法②")}
    for vn, eq in BITEQ.items():
        if eq:
            log(f"⚠ [逐位元相同] {vn} 與主格訊號集合相同")
    # ── r60 向量化（Granville ★11 同式）與對帳
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
    indm = {}

    def ind_at(j, t):
        k = (j, t)
        if k not in indm:
            v, _ = pit.at(SIDS[j], CAL[t]); indm[k] = v or ""
        return indm[k]
    # ── 配對（★11）
    MREASON = {}; dcache = {}
    for vn in VARIANTS:
        E = TR[vn]
        if not len(E):
            MREASON[vn] = {}; continue
        rng = np.random.default_rng(SEED)
        res = {}
        ex_arr = SIGRAW[vn]
        for t, g in E.groupby("t", sort=True):
            t = int(t)
            if t not in dcache:
                U = np.flatnonzero(GS[:, t] & VALID[:, t]) if not limit else np.flatnonzero(G[:, t] & VALID[:, t])
                mc = MC[U, t].astype(float); mc[~(mc > 0)] = np.nan
                pm = GV.deciles(mc); pr = GV.deciles(r60_vec(t)[U])
                dcache[t] = (U, np.where(np.isfinite(pm), np.ceil(pm * 10), -1).astype(int), np.where(np.isfinite(pr), np.ceil(pr * 3), -1).astype(int))
            U, dec, ter = dcache[t]
            out = GV.match_day(rng, sorted(g["i"].astype(int).tolist(), key=lambda z: SIDS[z]), U, dec, ter,
                               lambda j, t=t: bool(ex_arr[j, t]), lambda j, t=t: ind_at(j, t), lambda j, t=t: eflag(j, t) == "保留")
            for i, v in out.items():
                res[(i, t)] = v
        E["配對"] = [res[(int(i), int(t))][0] for i, t in zip(E["i"], E["t"])]
        E["對照"] = [";".join(SIDS[j] for j in res[(int(i), int(t))][1]) for i, t in zip(E["i"], E["t"])]
        E["對照數"] = [len(res[(int(i), int(t))][1]) for i, t in zip(E["i"], E["t"])]
        E["主格"] = E["配對"] == "配到"
        cst = []
        for r in E.itertuples(index=False):
            cs = []
            for sj in (r.對照.split(";") if r.對照 else []):
                j = PX["ix"][sj]; e, x = int(r.e), int(r.x)
                if (CB[j, x] - CB[j, e]) > 0:
                    cs.append("壞根")
                elif r.出場方式 in ("open", "minoc") and not (VALID[j, x] and np.isfinite(O[j, x])):
                    cs.append("出場日無成交")
                elif r.出場方式 == "close" and not VALID[j, x]:
                    cs.append("出場日無收盤")
                elif r.加碼根 >= 0 and not (VALID[j, int(r.加碼根)] and np.isfinite(O[j, int(r.加碼根)])):
                    cs.append("加碼日無成交")
                else:
                    cs.append("ok")
            cst.append(";".join(cs))
        E["對照出場狀態"] = cst
        MREASON[vn] = dict(Counter(E["配對"]))
        log(f"[配對 {vn}] {MREASON[vn]}｜{time.time() - t0:.0f}s")
    # ── 組合層（★13；主格版本）
    sig_by_t = defaultdict(list)
    Smain = SIGRAW["主"] & GS
    ii, tt = np.nonzero(Smain)
    for i, t in sorted(zip(ii.tolist(), tt.tolist()), key=lambda z: (z[1], SIDS[z[0]])):
        sig_by_t[t].append(i)

    def get_trade(i, t):
        if t + 1 > CEND or eflag(i, t) != "保留":
            return None
        return get_exit(i, t + 1, True)
    PF = {}
    for nm, (pa, pb) in seg_pos.items():
        draws = []
        for r_ in range(NDRAW):
            st_ = portfolio(pa, pb, sig_by_t, get_trade, lottery_order(SIDS, r_))
            draws.append(st_)
        vol_ = portfolio(pa, pb, sig_by_t, get_trade, volume_order(SIDS, V))
        keys = [k for k in draws[0] if k != "進場位置"]
        med = {k: (float(np.median([d[k] for d in draws if d[k] is not None])) if any(d[k] is not None for d in draws) else None) for k in keys}
        rng_ = {k: [float(np.min([d[k] for d in draws if d[k] is not None])), float(np.max([d[k] for d in draws if d[k] is not None]))]
                for k in keys if any(d[k] is not None for d in draws)}
        yrs = sorted({CAL[p].year for d in draws for p in d["進場位置"]})
        per_year = {str(y): float(np.median([sum(v for p, v in d["進場位置"].items() if CAL[p].year == y) for d in draws])) for y in yrs}
        PF[nm] = {"抽籤200次中位": med, "抽籤200次範圍[min,max]": rng_, "每年進場筆數(中位)": per_year,
                  "成交量大者優先": {k: v for k, v in vol_.items() if k != "進場位置"}}
        log(f"[組合 {nm}] {med}｜{time.time() - t0:.0f}s")
    # ── 最笨交易法重疊（★14）
    DUMB, dinfo = dumb_signals()
    OVL = []
    E = TR["主"]
    mine = E[["sid", "t"]] if len(E) else pd.DataFrame({"sid": [], "t": []})
    SALL = pd.DataFrame({"sid": [SIDS[i] for i in ii], "t": tt}) if len(ii) else mine
    for lab_m, mm in (("主格交易", mine), ("過閘訊號", SALL)):
        for lab, win in (("同日", 0), ("±20日", 20)):
            n, hit, no, rh = GV.overlap_rate(mm, DUMB, CAL, win)
            OVL.append({"本件": lab_m, "對方": "最笨交易法F1訊號", "讀法": lab, "本件(涵蓋內)": n, "重疊": hit, "本件中重疊比例": (hit / n) if n else None,
                        "對方(本件期間內)": no, "對方中落在本件": rh, "對方中重疊比例": (rh / no) if no else None,
                        "旗標≥80%": bool((n and hit / n >= 0.8) or (no and rh / no >= 0.8))})
    TRI = GV.load_tri(CAL)
    return dict(od=od, REG=REG, sha=sha, PX=PX, CAL=CAL, CEND=CEND, t0=t0, TR=TR, SKIP=SKIP, SIGN=SIGN, MREASON=MREASON, EQ=EQ, BITEQ=BITEQ,
                PF=PF, OVL=OVL, dinfo=dinfo, hlinfo=hlinfo, vinfo=vinfo, TRIcov=(int(np.isfinite(TRI).sum()), NC), seg_pos=seg_pos,
                TRI=TRI, dry=dry)


# ═════════════ 描述欄（乾跑 0 佔位）═════════════
def build_desc(A):
    """全部描述欄（登錄 §三～§五＋附註）。乾跑：報酬類一律 0 佔位（只驗欄填得出來）；次數類（持有、原因、加碼、名額）用實際次數。"""
    D = {}
    dry = A["dry"]
    for vn in VARIANTS:
        E = A["TR"][vn]
        if not len(E):
            continue
        M = E[E["主格"]]
        z = np.zeros(len(M))                                            # ⛔ 乾跑佔位
        for nm, _, _ in SEGS:
            q = M[M["段"] == nm]
            cb = GV.cluster_boot(np.zeros(len(q)), q["月"].to_numpy(), nboot=200 if dry else NBOOT, seed=SEED, alpha=ALPHA)
            D[("判定1單筆", vn, f"{nm}｜差(份數加權)與95%CI")] = {"n": cb["n"], "mean": cb["mean"], "lo": cb["lo"], "hi": cb["hi"]}
        D[("每筆描述", vn, "超額(訊號−對照，份數加權)")] = GV.desc_stats(z, M["年"], M["市場"])
        D[("每筆描述", vn, "訊號筆報酬(份數加權，扣成本後)")] = GV.desc_stats(z, M["年"], M["市場"])
        D[("每筆描述", vn, "對照平均報酬(扣成本後)")] = GV.desc_stats(z)
        D[("每筆描述", vn, "勝率")] = {"n": int(len(M)), "share": 0.0 if len(M) else np.nan}
        D[("每筆描述", vn, "平均賺")] = {"n": int(len(M)), "value": 0.0 if len(M) else np.nan}
        D[("每筆描述", vn, "平均賠")] = {"n": int(len(M)), "value": 0.0 if len(M) else np.nan}
        D[("每筆描述", vn, "賺≥5%比例")] = {"n": int(len(M)), "share": 0.0 if len(M) else np.nan}
        D[("每筆描述", vn, "賺≥8%比例")] = {"n": int(len(M)), "share": 0.0 if len(M) else np.nan}
        D[("每筆描述", vn, "對大盤報酬指數(訊號−指數)")] = GV.desc_stats(z, M["年"], M["市場"])
        if vn != "拿掉加碼":                                            # 拿掉加碼：依構造沒有加碼那份（不適用，不列）
            D[("每筆描述", vn, "加碼那份報酬")] = GV.desc_stats(np.zeros(int((M["加碼根"] >= 0).sum())))
        hd = M["持有天數"].to_numpy(float)
        D[("每筆描述", vn, "持有天數")] = {"n": int(len(hd)), "mean": float(hd.mean()) if len(hd) else np.nan, "median": float(np.median(hd)) if len(hd) else np.nan}
        for lab in ("跌破MA20", "MA20下彎", "停損3%"):
            D[("每筆描述", vn, f"出場條件命中率｜{lab}")] = {"n": int(len(M)), "share": float(M["觸發"].str.contains(lab).mean()) if len(M) else np.nan}
        D[("每筆描述", vn, "加碼觸發比例")] = {"n": int(len(M)), "share": float((M["加碼根"] >= 0).mean()) if len(M) else np.nan}
        vs = M["觸發日量比>1.5"].dropna()
        D[("每筆描述", vn, "續抱量條件(觸發日量>前5日均量×1.5)比例")] = {"n": int(len(vs)), "share": float(vs.astype(bool).mean()) if len(vs) else np.nan}
    for nm, _, _ in SEGS:
        pf = A["PF"].get(nm, {})
        n = int(pf.get("抽籤200次中位", {}).get("交易日", 0) or 0)
        for st in ("年化", "最大回落", "年化÷|最大回落|", "大盤報酬指數年化", "大盤年化÷|最大回落|", "合格判定", "年化波動", "年化÷年化波動",
                   "成本吃掉(年化)", "最大回落對照原文宣稱<15%", "0050列年化", "0050列最大回落", "成交量大者優先｜年化", "成交量大者優先｜最大回落"):
            D[("判定2組合", "主", f"{nm}｜{st}")] = {"n": n, "value": 0.0 if n else np.nan}
        D[("組合描述", "主", f"{nm}｜每年交易筆數(中位)")] = {"n": n, "value": float(sum(pf.get("每年進場筆數(中位)", {}).values())) if n else np.nan}
    for r_ in A["EQ"]:
        if r_["比例"] is not None or r_["分母"] == 0:
            D[("等價自查", r_["段"], r_["讀法"])] = {"n": r_["分母"], "share": r_["比例"] if r_["比例"] is not None else np.nan}
    for o_ in A["OVL"]:
        D[("等價自查", o_["本件"], f"vs 最笨交易法｜{o_['讀法']}")] = {"n": o_["本件(涵蓋內)"], "share": o_["本件中重疊比例"] if o_["本件中重疊比例"] is not None else np.nan}
    return D


# ═════════════ 輸出 ═════════════
def write_dry(A):
    od = A["od"]; TR = A["TR"]
    rows = []; reas = []; holds = []; spm = []
    for vn in VARIANTS:
        E = TR[vn]
        for nm, _, _ in SEGS + [("段外", "", "")]:
            q = E[E["段"] == nm] if len(E) else E
            if not len(q):
                rows.append({"版本": vn, "段": nm, "交易": 0}); continue
            main = q[q["主格"]]
            months = int(main["月"].nunique())
            g = main.groupby(["sid", "月"]).size()
            ga = q.groupby(["sid", "月"]).size()
            row = {"版本": vn, "段": nm, "交易": int(len(q)), "配到": int(len(main)), "配對成功率": float(len(main) / len(q)),
                   "配不到原因": dict(Counter(q.loc[~q["主格"], "配對"])), "對照數分布": dict(Counter(main["對照數"])),
                   "主格訊號月數(n_eff)": months, "n_eff≥24": months >= NEFF_MIN,
                   "每檔每月平均進出(主格)": float(g.mean()) if len(g) else None, "每檔每月最大進出(主格)": int(g.max()) if len(g) else None,
                   "每檔每月進出分布(主格)": dict(Counter(np.minimum(g.to_numpy(), 5).tolist())) if len(g) else {},
                   "每檔每月平均進出(全部交易)": float(ga.mean()) if len(ga) else None,
                   "有交易股數": int(q["sid"].nunique()), "每檔平均交易數": float(len(q) / q["sid"].nunique()),
                   "首筆訊號日": q["date"].min(), "末筆訊號日": q["date"].max(),
                   "加碼觸發比例(實際加成)": float((main["加碼根"] >= 0).mean()) if len(main) else None,
                   "持有中出現KD條件比例": float(main["KD條件出現"].mean()) if len(main) else None,
                   "KD條件但加碼根不可進(次)": int(main["KD被擋"].sum()), "資料尾未出(計值)": int((~main["完成"]).sum()),
                   "同根取較低": int(main["旗標"].str.contains("同根取較低").sum()),
                   "對照出場狀態": dict(Counter(f for x in main["對照出場狀態"] for f in x.split(";") if f)),
                   "上市": int((main["市場"] == "twse").sum()), "上櫃": int((main["市場"] == "tpex").sum())}
            for lab in ("跌破MA20", "MA20下彎", "停損3%"):
                row[f"命中率｜{lab}"] = float(main["觸發"].str.contains(lab).mean()) if len(main) else None
            rows.append(row)
            for k_, v_ in Counter(main["出場原因"]).items():
                reas.append({"版本": vn, "段": nm, "出場原因": k_, "件數": int(v_), "比例": v_ / len(main) if len(main) else None})
            hd = main["持有天數"].to_numpy(float)
            if len(hd):
                bins = [0, 1, 2, 3, 5, 10, 20, 40, 60, 120, 250, 10 ** 6]
                hc = np.histogram(hd, bins=bins)[0]
                holds.append({"版本": vn, "段": nm, "n": int(len(hd)), "平均": float(hd.mean()), "中位": float(np.median(hd)),
                              "p10": float(np.percentile(hd, 10)), "p25": float(np.percentile(hd, 25)), "p75": float(np.percentile(hd, 75)),
                              "p90": float(np.percentile(hd, 90)), "max": float(hd.max()),
                              **{f"[{bins[k]},{bins[k + 1]})": int(hc[k]) for k in range(len(hc))}})
            spm.append({"版本": vn, "段": nm, **{f"每檔每月{k}次": int(v) for k, v in sorted(Counter(np.minimum(g.to_numpy(), 5).tolist()).items())}})
    yr = []
    for vn in VARIANTS:
        E = TR[vn]
        if len(E):
            for (y, nm), g in E.groupby(["年", "段"]):
                yr.append({"版本": vn, "年": int(y), "段": nm, "交易": int(len(g)), "主格": int(g["主格"].sum()),
                           "上市": int((g["主格"] & (g["市場"] == "twse")).sum()), "上櫃": int((g["主格"] & (g["市場"] == "tpex")).sum())})
    pd.DataFrame(rows).to_csv(os.path.join(od, "freq_cells.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(reas).to_csv(os.path.join(od, "exit_reasons.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(holds).to_csv(os.path.join(od, "hold_dist.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(spm).to_csv(os.path.join(od, "entries_per_stock_month.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(yr).to_csv(os.path.join(od, "yearly.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(A["EQ"]).to_csv(os.path.join(od, "equivalence.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(A["OVL"]).to_csv(os.path.join(od, "overlap_dumb.csv"), index=False, encoding="utf-8-sig")
    pfr = []
    for nm, v in A["PF"].items():
        for k, x in v["抽籤200次中位"].items():
            pfr.append({"段": nm, "統計": k, "抽籤200次中位": x, "min": v["抽籤200次範圍[min,max]"].get(k, [None, None])[0],
                        "max": v["抽籤200次範圍[min,max]"].get(k, [None, None])[1], "成交量大者優先": v["成交量大者優先"].get(k)})
    pd.DataFrame(pfr).to_csv(os.path.join(od, "portfolio_fill.csv"), index=False, encoding="utf-8-sig")
    keep = ["sid", "date", "段", "市場", "x", "出場方式", "出場原因", "觸發", "加碼根", "KD條件出現", "KD被擋", "旗標", "完成", "持有天數",
            "觸發日量比>1.5", "配對", "對照數", "對照", "主格", "對照出場狀態"]
    CAL = A["CAL"]
    for vn in VARIANTS:
        E = TR[vn]
        if not len(E):
            continue
        Z = E[[c for c in keep if c in E.columns]].copy()
        Z["出場日"] = [str(CAL[x].date()) for x in E["x"]]
        Z["加碼日"] = [str(CAL[a].date()) if a >= 0 else "" for a in E["加碼根"]]
        Z.drop(columns=["x", "加碼根"]).to_csv(os.path.join(od, f"trades_{vn}.csv.gz"), index=False, encoding="utf-8-sig", compression="gzip")
    DESC = build_desc(A)
    ds = GV.dry_status(DESC); ds.to_csv(os.path.join(od, "desc_dryrun_status.csv"), index=False, encoding="utf-8-sig")
    neff = {}
    for vn in VARIANTS:
        E = TR[vn]
        ms = {nm: int(E[(E["段"] == nm) & E["主格"]]["月"].nunique()) if len(E) else 0 for nm, _, _ in SEGS}
        neff[vn] = {**ms, "狀態": ("依構造還沒測（任一段 n_eff < 24）" if min(ms.values()) < NEFF_MIN else "兩段 n_eff ≥ 24")}
    eqmain = [r for r in A["EQ"] if r["讀法"].startswith("P(③|②)")]
    J = {"登錄": A["REG"], "裁定": RULING, "資料": A["sha"], "價格面板": "rerun17 H2D edc6f（2015-01-05～2026-09-24）＋ 早年 eotc（2004-02-11～2014-12-31）",
         "日曆": f"{A['CAL'][0].date()}～{A['CAL'][-1].date()}（{len(A['CAL'])}）", "高低價": A["hlinfo"], "成交量": A["vinfo"],
         "大盤報酬指數覆蓋(日曆位置有值/全部)": A["TRIcov"], "訊號": A["SIGN"], "單筆擋下": A["SKIP"], "配對原因": A["MREASON"], "n_eff": neff,
         "等價自查主讀法P(③|②)": eqmain, "等價旗標(任一讀法≥80%)": [r for r in A["EQ"] if r["≥80%旗標"]],
         "拆件訊號與主格逐位元相同": A["BITEQ"], "最笨交易法": {"讀檔": A["dinfo"], "重疊": A["OVL"]},
         "組合層(份數制)": A["PF"], "描述欄乾跑": {"欄數": int(len(ds)), "EMPTY": int((ds["status"] == "EMPTY").sum()) if len(ds) else 0,
                                          "EMPTY清單": [f"{r.section}｜{r.cell}｜{r.stat}" for r in ds[ds["status"] == "EMPTY"].itertuples(index=False)][:50]},
         "NOTES": NOTES, "完成": str(pd.Timestamp.now(tz="Asia/Taipei")), "耗時秒": int(time.time() - A["t0"])}
    json.dump(J, open(os.path.join(od, "freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=GV._js)
    open(os.path.join(od, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    log(f"[完成] ⇒ {od}｜描述欄 {J['描述欄乾跑']['欄數']} 欄、EMPTY {J['描述欄乾跑']['EMPTY']}｜n_eff {neff}")


def gate(argv):
    """→ ('dry', procs, limit) | ('formal', procs, None) | ('refuse', 訊息)。正式跑只認 --formal --ruling seq487。"""
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
            return ("refuse", f"⛔ 正式跑須 --formal --ruling {RULING}（裁定 seq487 §三：先交頻率表＋描述欄乾跑）；拒跑")
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
    if m[0] == "formal":
        sys.exit("⛔ 正式輸出（報酬、CI、判定、權益）尚未實作：頻率表與描述欄乾跑核可後才補（seq366／459）；拒跑")
    A = run(dry=True, procs=m[1], limit=m[2])
    write_dry(A)


if __name__ == "__main__":
    main()
