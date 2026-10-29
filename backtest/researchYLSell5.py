# -*- coding: utf-8 -*-
"""營量 v1、營飆 v1 出場改用「賣 5」（收盤跌破 200 日線且 200 日線下彎才賣）　台股 seq1【頻率表＋全部描述欄乾跑／正式程式】——回測線計算子代理。

登錄：登錄全文-營量營飆改用賣5出場_收盤跌破200日線且線下彎才賣_組合層加單筆層登錄_台股策略線_seq1_shaf1421f918e63c990-5887B-20261030-0218.md
      （pw1 sha f1421f918e63c990 ＝ 去掉末行 pw1 戳記後全文 sha256 前 16 碼；整檔 5887 B；整檔 sha256 6f92ee5d… ≠ ⇒ 照 pw1 慣例；回測線子代理 2026-10-30 已驗）
發號：裁定 seq492 §二（判定 4 格：組合層 2 格 N_組合 ＋2、單筆層 2 格 N_單筆 ＋2；單筆層確認段 CI 97.5%（Bonferroni 2），95% 只描述並列；
      「買進時已符合賣 5、隔天就賣」≥ 10% ⇒ 頻率表照報後先回信；單筆層原版 ＝ 正式程式實際成交清單；組合層補位多出、少掉的筆數照報）；§三 先交頻率表（⛔ 不附報酬）＋描述欄乾跑。
⛔ 乾跑（--dry）：只數筆數、觸發比例、持有天數分布、n_eff、滿倉日、名額不足沒進、補位多出／少掉；⛔ 不讀、不算、不存任何本件報酬／超額／勝率（seq366／458／459）；
   價格用來判「賣 5 條件」本身（收盤 vs MA200、MA200 斜率），⛔ 不算報酬；描述欄一律以價格 1、成本 0 佔位跑完整流程（報酬全為 0），輸出只寫 filled／EMPTY 與件數。
   原版正式權益只拿來比 eq_sha（閘：＝ resultsYL_integrate），⛔ 不印、不存數值。
⛔ 不 commit、不改既有檔；營量 v1／營飆 v1 在策略鎖內（strategy_lock.json 25 支）⇒ 本檔只 import：researchYL_integrate（世界、eng、YL／YF）、researchAddOn（worlds、market、log_to）、
   researchGranville（stock_features、load_tri 不用）、research11（load_bars、simulate_mtm、cl_stats）、rerun17（win_metrics、bench_row）、benchmark_rejudge（read_series、bstat）、
   researchAscTri（label、ratio）、researchSlip／researchT1fix（現實版）、strategy_lock（check）。開跑前、跑完各驗一次策略鎖 ⇒ 不同即中止。

用法（cd ~/tw-p17）：
    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLSell5 --dry [--procs 3]          ⇒ backtest/resultsYLSell5/freq/
    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLSell5 --formal --ruling seq492    ⇒ backtest/resultsYLSell5/formal/（⛔ 兩旗標都要、ruling 必須 seq492）
    自測：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLSell5_check [--procs 3]

══════════ 登錄寫死的（照抄，不改）══════════
 問：營量 v1、營飆 v1 買進規則一字不動，只把「第 60／120 個交易日收盤賣」換成「收盤 < MA200 且 MA200 下彎（賣 5）⇒ 隔天開盤賣」。
 進場、母體、檔數、挑法、部位、成本：全照正式程式（營量 v1：20 檔、relvol 優先；營飆 v1：10 檔、0050 在 200 日線上、抽籤）。
 賣 5：MA200 ＝ 200 日還原收盤均線；下彎 ＝ MA200(t) < MA200(t−20)；持有中第 t 日收盤 < MA200(t) 且下彎 ⇒ t+1 開盤賣；從買進日起判（買進日收盤即可判）；
   上限 250 個交易日收盤；持有中遇壞根 ⇒ 壞根前一根收盤強制賣（seq335）。空出名額照正式程式補下一個訊號；⛔ 不補 0050、不加碼。
 母體門檻 R1（seq321 §五）、引擎閘 UG.set_gate_v2(True)（seq296）。段：探索 2017-03～2021-12｜確認 2022-01～資料尾｜早年 2005～2014 描述（reduce_v2，seq341 §六）。
 判定 4 格：組合層（營量、營飆各 1）：改版年化較高且 年化÷|回落| 不低於原版，探索、確認兩段都要；另報使用者判準標籤（對大盤報酬指數；0050 只當一欄）。
   單筆層（營量、營飆各 1）：原版實際成交的同一批買進只換出場；每筆差 ＝ 改出場每筆年化 − 原出場每筆年化；每筆年化 ＝ (1＋R)^(250 ÷ max(H, 60)) − 1；
   按月分群 CI（裁定 seq492：確認段 97.5%，95% 描述）；通過 ＝ 兩段點估計 > 0 且確認段 CI 下緣 > 0；〈四十九〉n_eff < 24 ⇒ 還沒測；方向為負只寫測不出。

══════════ ★ 執行者讀法（⛔ 在跑任何本件程式之前寫死於 2026-10-30 02:51（台北，WSL TZ=Asia/Taipei date）；〔 〕內為另一讀法）══════════
 寫死前看過：登錄全文 seq1、裁定 seq491、seq492、既有程式 researchExit5（整筆出場走引擎的寫法）、researchAddOn（世界、壞根、R1）、researchYL_integrate（世界、eng）、
   researchGranville（seg_features／stock_features／exit_sim 的賣 5 與上限寫法）、researchShortageExit2（U9 每筆年化、cl_stats）、research11.simulate_mtm、researchSlip；
   ⚠ 回測線看過營量 v1／營飆 v1 全部正式結果與出場五法、葛蘭碧 seq2 拆件結果；⛔ 沒看過「營量、營飆持股改用賣 5」任何數字（本件第一次算）。
 ★1 原版 ＝ 正式引擎：營量 v1 ＝ IG.eng(W, "H60·S20·無·relvol", 0)；營飆 v1 ＝ IG.eng(W, "H120·S10·閘·抽籤", r)，r ＝ 0～199；世界 ＝ researchAddOn.worlds 快取
     （＝ researchYL_integrate.main_world／early_world，主世界 rerun17 H2D edc6f、日曆 2015-01-05～2026-09-24；早年 eotc_f65bb03e11 上市＋上櫃 2004-02-11～2014-12-31）。
     閘：每條原版權益 eq_sha ＝ backtest/resultsYL_integrate/seeds.csv.gz 同世界、同格、同 r（只比 sha）。原版「實際成交清單」＝ 該次引擎 audit 的買進（t, sid）與賣出（t, sid）。
 ★2 單筆層「同一批買進」：營量 ＝ r0 實際買進；營飆 ＝ 200 顆實際買進的聯集，以（代號, 進場位置）去重、每筆算 1 次
     〔另一讀法：200 顆各自成交清單合併、按出現顆數加權——只描述並報觸發比例〕。單筆層的賣 5 出場與原版出場都以「該筆自己」算（不受名額影響）。
 ★3 段：依【進場日】e 落段（＝ 正式窗「訊號進場日在窗內」的同一口徑；依訊號日會把 2017-03-01 訊號、03-02 進場的第一批丟到段外）〔另一讀法：依訊號日〕；
     月分群與 n_eff 依【訊號月】（SIG pos 的年月，登錄「n_eff（訊號月）」）。段界 ＝ 正式 SEG_M（探索 2017-03-02～2021-12-30、確認 2022-01-03～2026-08-24 ＝
     正式窗尾 w1；正式訊號表本來就只收進場 ≤ w1 的訊號 ⇒ 「確認～資料尾」在進場上等於到 w1）〔另一讀法：組合層確認段延到資料尾 2026-09-24（原版也要同延）〕。
     早年 2005-02-01～2014-12-31 ＝ 描述。
 ★4 單筆層判定樣本 ＝「走得完」：e ＋ 250 ≤ 資料尾（各世界日曆最後一根）——不論實際何時賣（用實際出場決定入不入樣本是前視；同葛蘭碧 ★9）
     〔另一讀法：全收，資料尾仍持有者以資料尾收盤計（T1 同式）〕；兩種筆數都報。原版臂同一批、照原版自己的出場。
 ★5 MA200 與下彎：researchGranville.stock_features 原式（該股自己的有效 K 棒 ＝ research11.load_bars idx；還原收盤；壞根切段、壞根當根是新段第一根，MA200 與 t−20
     都不跨壞根）；壞根集合 ＝ researchAddOn.market 的持股壞根（主：~/crashwork/bad_main.pkl ＝ load_bars 壞根（含缺口 ≥ 5 日）∪ adj 減資／面額；
     早年：bad_early ∪ R8 事件恢復日 ∪ reduce_v2 上市／上櫃偵測 ∪ 未解釋 22 筆）；壞根落在非有效 K 棒日 ⇒ 其後第一根有效 K 棒當新段起點。
     賣 5 狀態 X5 ＝ 收盤 < MA200 且 MA200(t) < MA200(t−20)（嚴格，同葛蘭碧 ★6「照字面」）；MA200 或 t−20 不可得 ⇒ 當天不成立（不可判日照報）。
     各世界各自算（主世界 2015-01 起 ⇒ 2017-03 起的買進都有 ≥ 400 根；早年 2004-02 起 ⇒ 2005 年初前的買進要等到 MA200／斜率可得）〔另一讀法：早年＋主合併日曆連續算——
     主窗不受影響（2015 起已滿 220 根），只差主世界剛上市的股，兩讀法相同〕。
 ★6 出場（葛蘭碧 seq1 ★8 改寫成持股版）：cap ＝ e ＋ 250（日曆位置，e ＝ 進場根）〔另一讀法：該股自己第 250 根有效 K 棒（進場根算第 1 根，同正式 fixed_exit）〕；
     判斷日 d ∈ [e, min(cap, kb) − 1] 的有效 K 棒（kb ＝ e 之後第一個壞根），第一個 X5 成立日 d ⇒ X ＝ d 之後第一根有效 K 棒且開盤有限 > 0：
       X ＝ cap ⇒ 同根有開盤（觸發）、收盤（上限）兩個出場價 ⇒ 取較低 min(開, 收)（seq373）；X > cap（停牌跨上限）⇒ 仍在 X 開盤賣（照報件數）；
       X 不存在且 d ＝ 資料尾 ⇒ 資料尾仍持有；X 不存在（之後再也沒有成交）或 X ≥ kb（下一根已跨壞根）⇒ d 收盤賣（照報件數）。
     沒觸發：kb ≤ cap ⇒ kb 前最後一根有效收盤強制賣（seq335）；cap ≤ 資料尾 ⇒ cap 當天（或之前最後一根有效）收盤賣（上限 250）；cap ＞ 資料尾 ⇒ 資料尾仍持有。
     停止交易（W["SF"] 的 L）⇒ 照正式引擎 stop_force：排程出場 ＞ L＋1 ⇒ L＋1 以 L 收盤結清（引擎自己做；本檔另記經濟口徑）。
     引擎編碼（決定名額何時釋出）：開盤賣 X ⇒ xpos ＝ X；上限收盤（事先已知的排程出場）⇒ xpos ＝ cap（＝ 正式引擎「第 H 根收盤賣」的同一慣例：當天開盤釋出名額）；
     條件式收盤賣（壞根前強制、觸發後無下一開盤）⇒ xpos ＝ 賣出根 ＋ 1（收盤才知道 ⇒ 次一交易日才釋出名額，⛔ 不前視）〔另一讀法：xpos ＝ 賣出根，同 researchExit5〕；
     資料尾仍持有 ⇒ xpos ＝ 資料尾後墊根（T1 同式）。g ＝ 賣價 ÷ 進場價 − 1（進場價 ＝ 世界開盤[e]，無效改收盤，同引擎）。
     正式訊號表裡 xpos_H ＜ 0 的列（原版 H 窗跨壞根等，正式就不收）⇒ 本件也不收（進場一字不動）〔另一讀法：重收——會改變進場集合，不採〕。
 ★7 持有天數 H ＝ 賣出根 − e ＋ 1（進場根算第 1 天；開盤賣 X ⇒ X − e ＋ 1，收盤賣 x ⇒ x − e ＋ 1；同 researchShortageExit2 U9）；原版 ＝ xf − e ＋ 1；
     停止交易經濟口徑 ⇒ L − e ＋ 1；資料尾仍持有 ⇒ 資料尾 − e ＋ 1（標「截尾」）。
 ★8 「買進時已符合賣 5、隔天就賣」（裁定 seq492 旗標）主讀法 ＝ 第一個觸發日 d ＝ e（買進日收盤已在線下且線下彎 ⇒ e 之後第一個開盤賣）；
     另報〔另一讀法〕訊號日（pos）收盤 X5 已成立的比例。任一 ≥ 10% ⇒ 旗標（主讀法 ≥ 10% ⇒ 先回信）。
 ★9 組合層：同一引擎、同參數、同種子；sig ＝ 正式訊號表同一批列，只把 xpos_H／g_H 換成 ★6（relvol、進場位置不動）。stop_force 開（正式同）。
     乾跑 ＝ 引擎價格全換成 1、g ＝ 0、成本 0（執行時暫換 research11.COST，⛔ 不改檔）⇒ 只取成交清單（哪幾筆被買、何時賣）；
     閘：原出場走同一條乾跑路徑 ⇒ 成交清單（t, 買／賣, 代號）與 ★1 正式（真實價格）比對。
     ⚠ 事後註（寫死後第一次自測約 03:02（台北）發現，讀法照補、⛔ 當時未看任何本件頻率數字）：正式引擎有「現金不足」這一步——同一天空出多槽、但現金（出場拿回的錢）只夠買其中幾檔時，
       後面的候選被擋（log 'a'），這一步依價格；乾跑（價格 1）量不到 ⇒ 原出場乾跑與正式成交清單在極少數路徑上差幾筆（自測 C4c 逐條驗證：每條差異的第一個分歧日
       都是正式引擎「有空槽、現金不夠」擋掉的）。因此：組合層「補位多出／少掉」主讀法 ＝ 改版乾跑 vs 原版乾跑（同一個無價格引擎，只差出場）；
       〔另一讀法〕改版乾跑 vs 正式真實成交；原版乾跑 vs 正式的差（無價格近似誤差：條數、筆數）照報；正式跑一律用真實價格引擎重報（改版 vs 原版正式）。
     補位多出／少掉 ＝ 改版成交（代號, 進場位置）對原版：多出 ＝ 改版有、原版沒有；少掉 ＝ 原版有、改版沒有（依進場日落段；營飆 200 顆中位與合計）。
     滿倉日比例 ＝ 段內交易日收盤後持股數 ＝ N 的比例；平均占槽 ＝ 平均持股數 ÷ N；名額不足沒進 ＝ 段內候選訊號（xpos ≥ 0）沒被買、且當天開盤（出場之後）沒持有同一檔；
     已持有沒進另列；年換手 ★ ＝ 每年買進筆數 ÷ N（以筆數計，等權一槽 ＝ 1）〔另一讀法：買進金額 ÷ 平均權益——要用權益數值 ⇒ 留正式跑〕。
 ★10 R1（seq321 §五）：賣 5 不需要母體門檻；R1 不改正式進場（改了就不是「進場一字不動」）⇒ 只描述「原版成交的訊號日在 R1 內」比例〔另一讀法：只收 R1 內進場——會改進場，不採〕。
 ★11 單筆層 CI：research11.cl_stats 同式（按訊號月分群、cluster SE）；95%（z 1.95996）描述、97.5%（Bonferroni 2 格，z ＝ Φ⁻¹(1 − 0.025/2) ＝ 2.24140）判定；
     n_eff ＝ 判定樣本的訊號月數；任一段 < 24 ⇒ 還沒測。R ＝ 賣價 ÷ 進場價 − 1 − 0.585%（兩臂同扣）；1 ＋ R ≤ 0 ⇒ 年化 −1。
 ★12 組合層判定 ＝ seq342 口徑：營飆 200 顆中位（年化中位、回落中位、比值 ＝ 年化中位 ÷ |回落中位|）；改版變好 ＝ 年化 > 原版 且 比值 ≥ 原版，探索、確認兩段都要。
     使用者判準標籤 ＝ researchAscTri.label 對大盤報酬指數（benchmark_rejudge.read_series("git:origin/main:data/history/market_tri.csv")，執行時記 sha；世界日曆 ffill）；
     0050 ＝ 世界 b50（只當一欄）。
 ★13 描述欄（登錄 §三「正式跑另報」）：早賣／晚賣 ＝ 改版賣出根 < ／> 原版賣出根（同根 ＝ 同）；報酬差 ＝ 改版 R − 原版 R（中位、前 10%、後 10%）；
     每筆超額 ＝ R − 大盤報酬指數同期（★ 訊號日收盤 → 賣出根收盤；指數只有收盤，同葛蘭碧 ★17）〔另一讀法：進場日收盤起算〕，報中位、平均；
     使用者口徑 ＝ 每筆淨報酬（扣 0.585%）平均、中位、賺錢比例；早年段同表；
     加真實成本 ＝ researchSlip「現實版（C1 0.3%＋C2 50 萬＋C3＋C4）」（IG.slip_real 同一條，改 sig 的 xpos／g；只主世界，同 IG.slip_real）。
     乾跑：價格、指數全換成 1、成本 0、C2 衝擊 0、C4 均價 1（C3 漲跌停旗標用真的 ⇒ 只產生筆數）。
     ⚠（事後註，乾跑開跑後補的說明文字，計算未改）C3 賣出端沿用引擎「排程收盤出場」口徑（出場日收盤鎖跌停／沒成交 ⇒ 延到下一個可賣開盤）；賣 5 是開盤賣 ⇒ 開盤鎖跌停那一天在本臂近似（照註，描述用）。
 ★14 早年世界尾 2014-12-31 ⇒ 2014 年進場的 250 日上限多半走不完（截尾，件數照報）；早年附「早年含減資假飆股約 0.3%（剩 22 筆未解釋）」與上櫃版面註。
 ★15 R8（早年減資截斷）：正式早年 H 出場遇 R8 事件改在 pL 收盤賣；本件 R8 事件恢復日已在壞根集合 ⇒ 走 ★6 壞根前強制（賣在 kb 前最後一根有效收盤），件數照報。
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import pickle
import subprocess
import sys
import time
from collections import Counter
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D                              # noqa: E402
from backtest import research11 as R                        # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402
from backtest import researchYL_integrate as IG             # noqa: E402
from backtest import universe_gate as UG                    # noqa: E402
from backtest import researchAddOn as AO                    # noqa: E402
from backtest import researchGranville as GV                # noqa: E402  stock_features（⛔ 只 import）
from backtest import strategy_lock as SLK                   # noqa: E402

TIME = "2026-10-30 02:51（台北）"
REG_SHA = "f1421f918e63c990"
REG_BYTES = 5887
RULING = "seq492"
MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
OUT = "backtest/resultsYLSell5"
WORK = os.path.expanduser("~/ylsell5work")
NSEED = 200
if os.environ.get("YLS5_QUICK"):                                 # 煙霧測試（不是交件）：輸出另一個夾
    NSEED, OUT, WORK = 3, "/tmp/ylsell5_quick", "/tmp/ylsell5_quick/work"
CAP = 250
COST = 0.00585
NEFF_MIN = 24
Z95, Z975 = 1.959963984540054, 2.241402727604947
FLAG_SHARE = 0.10
STR = {"營量": {"H": 60, "N": 20, "G": False, "key": IG.YL}, "營飆": {"H": 120, "N": 10, "G": True, "key": IG.YF}}
SEGS = {"主": ("探索", "確認", "主窗"), "早年": ("早年",)}
JSEG = ("探索", "確認")
SENT = ["想法來自葛蘭碧拆件結果，看過那批才提；那批是不同進場與母體", "營量、營飆本身已看過結果", "改版抱得較久、名額較常滿，補進的訊號變少"]
NOTE_EARLY = ["早年含減資假飆股約 0.3%（剩 22 筆未解釋）", "上櫃 2007-07～12 除權息未還原；上櫃減資 2007～2012 為偵測、非官方；2005-01～2007-06 只有上市"]
NOTES = ["乾跑：未讀、未算、未存任何本件報酬、超額、勝率（seq366／458／459）；描述欄以價格 1、成本 0 佔位，只報 filled／EMPTY",
         "原版正式權益只比 eq_sha（閘），不印不存數值",
         "高10 不納入（登錄、裁定 seq492）"]
SLIP_ARM = "現實版（C1 0.3%＋C2 50 萬＋C3＋C4）"
_G: dict = {}


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


# ═════════════ 登錄、裁定、策略鎖 ═════════════
def reg_verify():
    fs = [f for f in glob.glob(os.path.join(MAILBOX, "*.md")) if f"sha{REG_SHA}" in os.path.basename(f)]
    if len(fs) != 1:
        raise SystemExit(f"⛔ 信箱找不到唯一一封登錄全文 sha{REG_SHA}：{fs}")
    b = open(fs[0], "rb").read()
    h = hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]
    if h != REG_SHA:
        raise SystemExit(f"⛔ 登錄 pw1 sha {h} ≠ {REG_SHA}")
    if len(b) != REG_BYTES:
        raise SystemExit(f"⛔ 登錄大小 {len(b)} ≠ {REG_BYTES}")
    rul = [f for f in glob.glob(os.path.join(MAILBOX, "*.md")) if RULING in os.path.basename(f) and "裁定線" in os.path.basename(f)]
    if not rul:
        raise SystemExit(f"⛔ 信箱找不到裁定 {RULING}")
    return {"登錄": os.path.basename(fs[0]), "bytes": len(b), "整檔sha前16": hashlib.sha256(b).hexdigest()[:16], "pw1去戳記sha前16": h,
            "裁定": os.path.basename(rul[0])}


def lock_check(tag, log):
    diff = SLK.check()
    log(f"[策略鎖 {tag}] {'相符（' + str(len(SLK.digest())) + ' 支）' if not diff else diff}")
    if diff:
        raise SystemExit(f"⛔ 策略鎖不符：{diff}")
    return {"時點": tag, "相符": True, "支數": len(SLK.digest())}


def seeds_of(sn):
    return [0] if sn == "營量" else list(range(NSEED))


# ═════════════ 原版正式引擎（真實價格；只取成交清單與 eq_sha）═════════════
def trade_list(au):
    """audit ⇒ (買進 [(t, sid)], 賣出 [(t, sid)])，依記錄順序。"""
    b = [(int(a["t"]), str(a["sid"])) for a in au if a["side"] == "buy"]
    s = [(int(a["t"]), str(a["sid"])) for a in au if a["side"] == "sell"]
    return b, s


def job_official(a):
    wn, sn, r = a
    o, au = IG.eng(_G["WS"][wn], STR[sn]["key"], r, audit=True)
    return wn, sn, r, IG.sha(np.asarray(o["equity"], float)), trade_list(au)


# ═════════════ 逐股：有效 K 棒、壞根、賣 5 狀態 ═════════════
def bars_job(a):
    sid, mk = a
    D.DATA = _G["data"]
    B = R.load_bars(sid, mk, _G["cal"])
    if B is None:
        return sid, None
    return sid, (np.asarray(B["idx"], np.int64), np.asarray(B["h"], float), np.asarray(B["l"], float), np.asarray(B["c"], float))


def bad_on_bars(idx, bad_cal):
    """日曆壞根 ⇒ 有效 K 棒序列上的壞根旗標（落在非 K 棒日的壞根 ⇒ 其後第一根有效 K 棒；★5）。"""
    cb = np.cumsum(np.asarray(bad_cal, bool).astype(np.int64))
    v = np.zeros(len(idx), bool)
    if len(idx):
        v[0] = cb[idx[0]] > 0
        v[1:] = (cb[idx[1:]] - cb[idx[:-1]]) > 0
    return v


def x5_features(c, h, l, badv):
    """★5：GV.stock_features 原式 ⇒ (X5, 可判)；可判 ＝ MA200(t) 與 MA200(t−20) 同段都可得。"""
    F = GV.stock_features(c, h, l, badv)
    MA = F["MA"]; n = len(c)
    seg = np.cumsum(badv.astype(np.int64)) if n else np.zeros(0, np.int64)
    jud = np.zeros(n, bool)
    if n > GV.SLOPE:
        k = np.arange(GV.SLOPE, n)
        jud[k] = np.isfinite(MA[k]) & np.isfinite(MA[k - GV.SLOPE]) & (seg[k] == seg[k - GV.SLOPE])
    return np.asarray(F["X5"], bool), jud


def stock_pack(W, sid, LB, HB, n0, NP):
    idx, h, l, cb = LB
    idx_ok = idx < n0
    idx, h, l, cb = idx[idx_ok], h[idx_ok], l[idx_ok], cb[idx_ok]
    c = np.asarray(W["closes"][sid], float)[:n0]; o = np.asarray(W["opens"][sid], float)[:n0]
    bar = np.zeros(n0, bool); bar[idx] = True
    okop = bar & np.isfinite(o) & (o > 0)
    nxt = np.full(n0 + 2, -1, np.int64)
    for p in range(n0 - 1, -1, -1):
        nxt[p] = p if okop[p] else nxt[p + 1]
    lastbar = np.full(n0 + 1, -1, np.int64)                      # lastbar[p] ＝ ≤ p 的最後一根有效 K 棒
    run = -1
    for p in range(n0):
        if bar[p]:
            run = p
        lastbar[p] = run
    lastbar[n0] = run
    bad_cal = np.asarray(HB[sid][1], bool)[:NP]
    nbad = np.full(NP + 1, -1, np.int64)
    for p in range(NP - 1, -1, -1):
        nbad[p] = p if bad_cal[p] else nbad[p + 1]
    badv = bad_on_bars(idx, bad_cal[:n0])
    X5v, Jv = x5_features(cb, h, l, badv)
    x5 = np.zeros(n0, bool); x5[idx] = X5v
    jud = np.zeros(n0, bool); jud[idx] = Jv
    return {"c": c, "o": o, "bar": bar, "nxt": nxt, "lastbar": lastbar, "nbad": nbad, "x5": x5, "jud": jud, "idx": idx}


# ═════════════ ★6 出場（單筆；自測直接呼叫）═════════════
def sell5_exit(pk, e, n0, cap=CAP, x5=None):
    """單筆賣 5 出場 ⇒ dict：kind（open／minoc／close／cclose／end）、sale（賣出根）、xpos（引擎）、px（賣價）、d（觸發日或 −1）、reason、flags。
    ⛔ 只用 ≤ 判斷日的收盤判條件；px 只在正式跑拿去算報酬。"""
    x5 = pk["x5"] if x5 is None else x5
    c, o = pk["c"], pk["o"]
    capp = e + cap
    kb = int(pk["nbad"][e + 1]) if e + 1 < len(pk["nbad"]) else -1
    lim = capp if kb < 0 else min(capp, kb)
    hi = min(lim, n0)
    flags = []
    dd = np.flatnonzero(x5[e:hi]) if hi > e else np.zeros(0, np.int64)
    if len(dd):
        d = e + int(dd[0])
        X = int(pk["nxt"][d + 1]) if d + 1 <= n0 - 1 else -1
        if X < 0:
            if d >= n0 - 1 or pk["lastbar"][n0 - 1] > d:
                # 資料尾觸發（或其後只有無效開盤直到資料尾）⇒ 資料尾仍持有
                v = int(pk["lastbar"][n0 - 1])
                return {"kind": "end", "sale": v, "xpos": n0, "px": float(c[v]), "d": d, "reason": "賣5觸發但資料尾前無可賣開盤（仍持有）", "flags": flags}
            return {"kind": "cclose", "sale": d, "xpos": d + 1, "px": float(c[d]), "d": d, "reason": "賣5→之後無成交（觸發日收盤）", "flags": flags}
        if kb >= 0 and X >= kb:
            return {"kind": "cclose", "sale": d, "xpos": d + 1, "px": float(c[d]), "d": d, "reason": "賣5→下一根跨壞根（觸發日收盤）", "flags": flags}
        if X == capp:
            flags.append("同根取較低")
            return {"kind": "minoc", "sale": X, "xpos": X, "px": float(min(o[X], c[X])), "d": d, "reason": "賣5", "flags": flags}
        if X > capp:
            flags.append("停牌跨上限")
        return {"kind": "open", "sale": X, "xpos": X, "px": float(o[X]), "d": d, "reason": "賣5", "flags": flags}
    if kb >= 0 and kb <= capp and kb <= n0 - 1:
        db = int(pk["lastbar"][kb - 1])
        if db < e:
            db = e
        return {"kind": "cclose", "sale": db, "xpos": db + 1, "px": float(c[db]), "d": -1, "reason": "壞根前強制", "flags": flags}
    if capp <= n0 - 1:
        v = int(pk["lastbar"][capp])
        if v != capp:
            flags.append("上限根無成交")
        return {"kind": "close", "sale": v, "xpos": capp, "px": float(c[v]), "d": -1, "reason": "上限250", "flags": flags}
    v = int(pk["lastbar"][n0 - 1])
    return {"kind": "end", "sale": v, "xpos": n0, "px": float(c[v]), "d": -1, "reason": "資料尾仍持有", "flags": flags}


def econ(xpos, sale, px, L, c):
    """停止交易經濟口徑（引擎 stop_force：排程出場 ＞ L＋1 ⇒ L＋1 以 L 收盤）。⇒ (xpos_e, sale_e, px_e, sf)。"""
    if L is not None and xpos > L + 1:
        return L + 1, L, float(c[L]), 1
    return xpos, sale, px, 0


# ═════════════ 逐列（候選訊號）═════════════
def build_rows(wn, sn, W, PK, n0):
    S = STR[sn]; H = S["H"]; sig = W["SIG"][S["G"]]
    sig = sig[sig[f"xpos_H{H}"] >= 0]
    rows = []
    for r in sig.itertuples(index=False):
        sid = r.sid; e = int(r.entry_pos); pos = int(r.pos); xf = int(getattr(r, f"xpos_H{H}")); gf = float(getattr(r, f"g_H{H}"))
        pk = PK[sid]
        bp = float(W["opens"][sid][e])
        if not np.isfinite(bp) or bp <= 0:
            bp = float(W["closes"][sid][e])
        L = W["SF"].get(sid)
        X = sell5_exit(pk, e, n0)
        cfull = np.asarray(W["closes"][sid], float)
        xe, se, pe, sf = econ(X["xpos"], X["sale"], X["px"], L, cfull)
        # 原版（正式欄）：收盤賣在 xf；xf ＝ n0 ⇒ T1 補回（資料尾仍持有）
        if xf < n0:
            so, po = xf, bp * (1 + gf)
        else:
            so, po = int(pk["lastbar"][n0 - 1]), bp * (1 + gf)
        xoe, soe, poe, sfo = econ(xf, so, po, L, cfull)
        rows.append({"key": f"{sid}#{e}", "sid": sid, "e": e, "pos": pos, "k": int(r.k), "relvol": float(r.relvol), "bp": bp, "L": -1 if L is None else int(L),
                     "訊號日": str(W["cal"][pos].date()), "進場日": str(W["cal"][e].date()), "訊號月": str(W["cal"][pos])[:7],
                     "完成": bool(e + CAP <= n0 - 1),
                     "o_xpos": xf, "o_g": gf, "o_sale": soe, "o_xe": xoe, "o_px": poe, "o_sf": sfo, "o_尾": bool(xf >= n0),
                     "o_跨壞根": bool(0 <= int(pk["nbad"][e + 1]) <= min(xf, n0 - 1)),
                     "n_kind": X["kind"], "n_d": X["d"], "n_sale": se, "n_xpos": X["xpos"], "n_xe": xe, "n_px": pe, "n_sf": sf,
                     "n_reason": ("停止交易（引擎 L＋1）" if sf else X["reason"]), "n_flags": "|".join(X["flags"]),
                     "n_g": X["px"] / bp - 1.0,
                     "x5_訊號日": bool(pk["x5"][pos]), "可判_訊號日": bool(pk["jud"][pos]), "可判_進場日": bool(pk["jud"][e]),
                     "e日觸發": bool(X["d"] == e)})
    T = pd.DataFrame(rows)
    if not T["key"].is_unique:
        raise SystemExit(f"⛔ {wn}·{sn} 訊號列（代號, 進場位置）不唯一")
    T["o_H"] = T["o_sale"] - T["e"] + 1
    T["n_H"] = T["n_sale"] - T["e"] + 1
    T.insert(0, "策略", sn); T.insert(0, "世界", wn)
    return T


def seg_of_pos(W, pos):
    out = np.full(len(pos), "段外", dtype=object)
    for sg, (x, y) in W["segp"].items():
        if sg == "主窗":
            continue
        m = (pos >= x) & (pos <= y)
        out[m] = sg
    return out


# ═════════════ 組合層引擎（乾跑：價格 1、g 0、成本 0）═════════════
def sig_with(W, sn, T, arm, dry):
    """正式訊號表同一批列（含 xpos ＜ 0 的列，引擎自己丟），arm ＝ "o"（原出場）／"n"（賣 5）。"""
    S = STR[sn]; H = S["H"]
    sig = W["SIG"][S["G"]].copy()
    if arm == "n":
        Ti = T.set_index("key")
        k = [f"{s}#{int(e)}" for s, e in zip(sig["sid"], sig["entry_pos"])]
        m = sig[f"xpos_H{H}"].to_numpy() >= 0
        xp = sig[f"xpos_H{H}"].to_numpy(np.int64).copy(); g = sig[f"g_H{H}"].to_numpy(float).copy()
        kk = [k[i] for i in np.flatnonzero(m)]
        xp[m] = Ti.loc[kk, "n_xpos"].to_numpy(np.int64); g[m] = Ti.loc[kk, "n_g"].to_numpy(float)
        sig[f"xpos_H{H}"] = xp; sig[f"g_H{H}"] = g
    if dry:
        H_ = f"g_H{H}"
        g = sig[H_].to_numpy(float).copy(); g[np.isfinite(g)] = 0.0; sig[H_] = g
    return sig


def job_dry(a):
    wn, sn, arm, r = a
    C = _G["DRY"][(wn, sn, arm)]; S = STR[sn]; W = _G["WS"][wn]
    au = []
    R.COST = 0.0
    try:
        if sn == "營量":
            o = R.simulate_mtm(C["sig"], f"H{S['H']}", S["N"], np.random.default_rng(RR.P1_SEED0 + r), C["cl"], C["op"], W["NP"], return_equity=True,
                               log=[], d_max=None, pick="relvol", queue_days=0, stop_force=W["SF"], audit=au)
        else:
            o = R.simulate_mtm(C["sig"], f"H{S['H']}", S["N"], np.random.default_rng(RR.P10_SEED0 + r), C["cl"], C["op"], W["NP"], return_equity=True,
                               stop_force=W["SF"], audit=au)
    finally:
        R.COST = _G["COST0"]
    eq = np.asarray(o["equity"], float) if _G.get("KEEP_EQ") else None
    return wn, sn, arm, r, trade_list(au), eq, int(o["first"]), int(o["end"])


def ones_prices(W, sids):
    one = np.ones(W["NP"])
    return {s: one for s in sids}


# ═════════════ 組合層頻率（⛔ 無報酬）═════════════
def port_stats(W, sn, buys, sells, cand, H_of):
    """一條路徑 ⇒ 各段：買進筆、滿倉日比例、平均占槽、名額不足沒進、已持有沒進、年換手（筆數）、持有天數。"""
    N = STR[sn]["N"]; NPn = W["NP"]
    cnt = np.zeros(NPn + 1)
    for t, _ in buys:
        cnt[t] += 1
    for t, _ in sells:
        cnt[t] -= 1
    hold = np.cumsum(cnt)[:NPn]
    # 持有區間（已持有判定）：同一代號 [買, 賣)
    iv = {}
    sq = {}
    for t, s in sells:
        sq.setdefault(s, []).append(t)
    for s in sq:
        sq[s].sort()
    bys = sorted(buys)
    for t, s in bys:
        lst = sq.get(s, [])
        ts = next((x for x in lst if x >= t), None)
        if ts is not None:
            lst.remove(ts)
        iv.setdefault(s, []).append((t, ts if ts is not None else 10 ** 9))
    bought = set((s, t) for t, s in buys)
    out = {}
    for sg, (x, y) in W["segp"].items():
        yrs = (y - x + 1) / 245.0
        bs = [(t, s) for t, s in buys if x <= t <= y]
        cs = cand[(cand["entry_pos"] >= x) & (cand["entry_pos"] <= y)]
        nf, nh = 0, 0
        for s, e in zip(cs["sid"], cs["entry_pos"]):
            e = int(e)
            if (s, e) in bought:
                continue
            held = any(a < e < b for a, b in iv.get(s, []))
            nh += int(held); nf += int(not held)
        hd = [H_of.get((s, t)) for t, s in bs]
        hd = [h for h in hd if h is not None]
        out[sg] = {"買進筆": len(bs), "滿倉日比例": float(np.mean(hold[x:y + 1] >= N)), "平均占槽": float(np.mean(hold[x:y + 1]) / N),
                   "候選訊號": int(len(cs)), "名額不足沒進": nf, "已持有沒進": nh, "年換手（筆數÷N）": float(len(bs) / yrs / N),
                   "持有天數中位": float(np.median(hd)) if hd else None, "持有天數p10": float(np.quantile(hd, .1)) if hd else None,
                   "持有天數p90": float(np.quantile(hd, .9)) if hd else None, "買進鍵": [(s, t) for t, s in bs]}
    return out


def q3(v):
    v = np.asarray([x for x in v if x is not None and np.isfinite(x)], float)
    if not len(v):
        return {"n": 0, "中位": None, "p10": None, "p90": None, "平均": None}
    return {"n": int(len(v)), "中位": float(np.median(v)), "p10": float(np.quantile(v, .1)), "p90": float(np.quantile(v, .9)), "平均": float(v.mean())}


def single_freq(T, sn, segname, wtab=None):
    """單筆層頻率（⛔ 無報酬）。T 已限定該段；wtab ＝ 營飆顆數權重（另一讀法）。"""
    n = len(T); J = T[T["完成"]]
    rs = T["n_reason"]
    d = {"段": segname, "原版成交筆（去重）": int(n), "判定樣本（e＋250≤資料尾）": int(len(J)), "截尾不收": int(n - len(J)),
         "n_eff（訊號月，判定樣本）": int(J["訊號月"].nunique()), "n_eff（訊號月，全部）": int(T["訊號月"].nunique())}
    for nm, S_ in (("全部", T), ("判定樣本", J)):
        m = len(S_)
        if not m:
            d[nm] = {"n": 0}; continue
        r_ = S_["n_reason"]
        d[nm] = {"n": int(m),
                 "賣5觸發（上限前）比例": float(r_.str.startswith("賣5").mean()),
                 "到250上限比例": float((r_ == "上限250").mean()),
                 "壞根前強制比例": float((r_ == "壞根前強制").mean()),
                 "停止交易（引擎）比例": float(r_.str.startswith("停止交易").mean()),
                 "資料尾仍持有比例": float(r_.str.contains("仍持有").mean()),
                 "賣5觸發→觸發日收盤（跨壞根／之後無成交）筆": int(r_.str.startswith("賣5→").sum()),
                 "同根取較低筆": int(S_["n_flags"].str.contains("同根取較低").sum()), "停牌跨上限筆": int(S_["n_flags"].str.contains("停牌跨上限").sum()),
                 "上限根無成交筆": int(S_["n_flags"].str.contains("上限根無成交").sum()),
                 "★8 買進日收盤已符合賣5、隔天就賣 比例": float(S_["e日觸發"].mean()), "★8 筆": int(S_["e日觸發"].sum()),
                 "〔另一讀法〕訊號日收盤已符合賣5 比例": float(S_["x5_訊號日"].mean()),
                 "進場日 MA200／斜率不可判比例": float((~S_["可判_進場日"]).mean()),
                 "持有天數 改版（賣5）": q3(S_["n_H"]), "持有天數 原版": q3(S_["o_H"]),
                 "改版比原版早賣筆": int((S_["n_sale"] < S_["o_sale"]).sum()), "改版比原版晚賣筆": int((S_["n_sale"] > S_["o_sale"]).sum()),
                 "同一根賣筆": int((S_["n_sale"] == S_["o_sale"]).sum()),
                 "觸發距進場（交易日，觸發者）": q3((S_.loc[S_["n_d"] >= 0, "n_d"] - S_.loc[S_["n_d"] >= 0, "e"]).to_numpy(float)),
                 "原版截尾（T1 補回）筆": int(S_["o_尾"].sum()), "原版停止交易筆": int(S_["o_sf"].sum()),
                 "原版持有窗內有壞根筆（正式不截、改版在壞根前強制賣）": int(S_["o_跨壞根"].sum())}
        if "R1_訊號日" in S_.columns:
            d[nm]["★10 訊號日在 R1 內比例（描述）"] = float(S_["R1_訊號日"].mean())
    if wtab is not None and len(T):
        w = T["key"].map(wtab).fillna(0).to_numpy(float)
        r_ = T["n_reason"]
        d["〔★2 另一讀法〕按顆數加權（全部）"] = {"總筆（200 顆合計）": int(w.sum()),
                                         "賣5觸發比例": float((w * r_.str.startswith("賣5")).sum() / w.sum()),
                                         "到250上限比例": float((w * (r_ == "上限250")).sum() / w.sum()),
                                         "★8 隔天就賣比例": float((w * T["e日觸發"]).sum() / w.sum())}
    return d


# ═════════════ 描述欄（正式跑才有值；乾跑佔位）═════════════
def ann_of(R_, H):
    H = np.maximum(np.asarray(H, float), 60.0)
    R_ = np.asarray(R_, float)
    out = np.where(1 + R_ > 0, np.power(np.clip(1 + R_, 1e-300, None), 250.0 / H) - 1.0, -1.0)
    return out


def ci(x, m, z):
    s = R.cl_stats(np.asarray(x, float), np.asarray(m))
    if s.get("n", 0) == 0:
        return {"n": 0, "n_eff": 0, "平均": None, "下緣": None, "上緣": None}
    return {"n": s["n"], "n_eff": s["months"], "平均": s["mean"], "中位": s["median"], "se": s["se"], "下緣": s["mean"] - z * s["se"], "上緣": s["mean"] + z * s["se"]}


def single_desc(T, tri, dry):
    """單筆層判定與描述（formal）；dry ⇒ 價格 1、成本 0 佔位。T 已限定段、判定樣本。"""
    cost = 0.0 if dry else COST
    if dry:
        Rn = np.zeros(len(T)); Ro = np.zeros(len(T)); trn = np.zeros(len(T)); tro = np.zeros(len(T))
    else:
        Rn = T["n_px"].to_numpy(float) / T["bp"].to_numpy(float) - 1 - cost
        Ro = T["o_px"].to_numpy(float) / T["bp"].to_numpy(float) - 1 - cost
        pos = T["pos"].to_numpy(int)
        trn = tri[T["n_sale"].to_numpy(int)] / tri[pos] - 1; tro = tri[T["o_sale"].to_numpy(int)] / tri[pos] - 1
    An = ann_of(Rn, T["n_H"].to_numpy(float)); Ao = ann_of(Ro, T["o_H"].to_numpy(float))
    dd = An - Ao
    mo = T["訊號月"].to_numpy()
    early = (T["n_sale"] < T["o_sale"]).to_numpy(); late = (T["n_sale"] > T["o_sale"]).to_numpy()
    return {"每筆年化差（改−原）": {"95%": ci(dd, mo, Z95), "97.5%（Bonferroni 2，判定）": ci(dd, mo, Z975)},
            "改版每筆年化": q3(An), "原版每筆年化": q3(Ao),
            "早賣筆 報酬差（改−原）": q3(Rn[early] - Ro[early]), "晚賣筆 報酬差（改−原）": q3(Rn[late] - Ro[late]),
            "每筆超額（對大盤報酬指數）改版": q3(Rn - trn), "每筆超額（對大盤報酬指數）原版": q3(Ro - tro),
            "使用者口徑 每筆淨報酬 改版": {**q3(Rn), "賺錢比例": float(np.mean(Rn > 0)) if len(Rn) else None},
            "使用者口徑 每筆淨報酬 原版": {**q3(Ro), "賺錢比例": float(np.mean(Ro > 0)) if len(Ro) else None}}


def single_verdict(D2):
    ex, cf = D2["探索"]["每筆年化差（改−原）"]["97.5%（Bonferroni 2，判定）"], D2["確認"]["每筆年化差（改−原）"]["97.5%（Bonferroni 2，判定）"]
    if min(ex["n_eff"], cf["n_eff"]) < NEFF_MIN:
        return "還沒測（n_eff ＜ 24）"
    if ex["平均"] is None or cf["平均"] is None:
        return "還沒測（無樣本）"
    if ex["平均"] > 0 and cf["平均"] > 0 and cf["下緣"] > 0:
        return "通過（改賣 5 每筆年化較高）"
    return "測不出"


def port_metrics(W, eq, f_, e_, tri, dry):
    out = {}
    for sg, (x, y) in W["segp"].items():
        c, m, _ = RR.win_metrics(eq, f_, e_, x, y)
        out[sg] = (float(c), float(m))
    return out


def port_desc(W, MET, sn, tri, dry):
    """MET[(arm)] ＝ [每顆 {段: (年化, 回落)}] ⇒ 判定與標籤（seq342 口徑）。"""
    from backtest import benchmark_rejudge as BR
    from backtest import researchAscTri as AS
    rep = {}
    for sg, (x, y) in W["segp"].items():
        bt = BR.bstat(W["cal"], tri, x, y)
        b50 = {"cagr": 0.0, "mdd": 0.0} if dry else RR.bench_row(W["cal"], np.asarray(W["bench"], float), x, y + 1)
        z = {}
        for arm in ("o", "n"):
            cs = [v[sg][0] for v in MET[arm]]; ms = [v[sg][1] for v in MET[arm]]
            c, m = float(np.median(cs)), float(np.median(ms))
            z[arm] = {"年化中位": c, "回落中位": m, "比值": AS.ratio(c, m), "對大盤": AS.label(c, m, bt) if bt else "—", "對0050（只一欄）": AS.label(c, m, b50)}
        better = bool(z["n"]["年化中位"] > z["o"]["年化中位"] and (z["n"]["比值"] >= z["o"]["比值"]))
        per = [bool(a[sg][0] > b[sg][0] and AS.ratio(*a[sg]) >= AS.ratio(*b[sg])) for a, b in zip(MET["n"], MET["o"])]
        rep[sg] = {"原版": z["o"], "改版": z["n"], "變好": better, "逐顆變好比例": float(np.mean(per)) if per else None,
                   "大盤": {k: bt[k] for k in ("cagr", "mdd", "ratio")} if bt else None, "0050": {"cagr": b50["cagr"], "mdd": b50["mdd"]}}
    return rep


# ═════════════ 現實版（★13；主世界）═════════════
def slip_setup(W, procs, log):
    from backtest import researchSlip as SL
    from backtest import researchT1fix as T1
    from backtest import tradability as TR
    RR.use_snapshot(); D.DATA = W["data"]
    sids = sorted(set(W["SIG"][False]["sid"]) | set(W["SIG"][True]["sid"]))
    T1._G.update(cal=W["cal"], NPX=len(W["cal"]) + 1)
    with Pool(procs) as pool:
        X = dict(pool.map(T1._load_x, [(s, W["uni"].get(s, "twse")) for s in sids], chunksize=8))
    trad_full = {s: {"trd": v["trd"][:len(W["cal"])]} for s, v in X.items() if v is not None}
    try:
        off = TR.load_official()
    except Exception:
        off = {}
    dl = TR.delist_status(trad_full, W["cal"], official=off)
    SL._G.clear(); SL._G.update(dict(cal=W["cal"], NP=W["NP"], closes=W["closes"], opens=W["opens"], w0=W["w0"], w1=W["w1"], SF=W["SF"], dl=dl, X=X, ncal=len(W["cal"])))
    log(f"[現實版] 讀 {len(X)} 檔附加資料（tradability）")
    return SL, X


def slip_run(SL, X, W, sn, sig, dry, seeds):
    S = STR[sn]; cell = f"YLS5_{sn}"
    SL.CELLS[cell] = {"名": sn, "rule": f"H{S['H']}", "N": S["N"], "seed0": RR.P1_SEED0 if sn == "營量" else RR.P10_SEED0, "A": 250_000 / S["N"]}
    spec = dict(SL.ARMS)[SLIP_ARM]
    if dry:
        Xd = {s: ({**v, "avg": np.ones_like(np.asarray(v["avg"], float)), "sig20": np.zeros_like(np.asarray(v["sig20"], float)),
                   "adv20": np.ones_like(np.asarray(v["adv20"], float))} if v is not None else None) for s, v in X.items()}
        cl = ones_prices(W, set(X.keys()) | set(W["SF"])); op0 = cl
    else:
        Xd = X; cl = W["closes"]; op0 = W["opens"]
    sg_, op, cost, kw = SL.arm_inputs(cell, spec, sig, Xd, cl, op0)
    if dry:
        cost = 0.0
        g = sg_[f"g_H{S['H']}"].to_numpy(float).copy(); g[np.isfinite(g)] = 0.0; sg_[f"g_H{S['H']}"] = g
    res = []
    for r in seeds:
        R.COST = cost
        try:
            if sn == "營量":
                o = R.simulate_mtm(sg_, f"H{S['H']}", S["N"], np.random.default_rng(RR.P1_SEED0 + r), cl, op, W["NP"], log=[], d_max=None, pick="relvol",
                                   queue_days=0, return_equity=True, **kw)
            else:
                o = R.simulate_mtm(sg_, f"H{S['H']}", S["N"], np.random.default_rng(RR.P10_SEED0 + r), cl, op, W["NP"], return_equity=True, **kw)
        finally:
            R.COST = _G["COST0"]
        eq = np.asarray(o["equity"], float)
        res.append({"met": {sg: tuple(map(float, RR.win_metrics(eq, o["first"], o["end"], x, y)[:2])) for sg, (x, y) in W["segp"].items()},
                    "tr": {k: v for k, v in o.items() if k.startswith("tr_") or k in ("limit_up", "halt_in", "exit_delayed")}})
    return res


# ═════════════ 主流程 ═════════════
def run(mode, procs, log):
    T0 = time.time()
    dry = mode == "dry"
    od = os.path.join(OUT, "freq" if dry else "formal")
    os.makedirs(od, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    A = {"讀法寫死": TIME, "模式": mode, "開跑": now_tpe() + "（台北）", "附註": NOTES, "結果句必附": SENT, "早年必附": NOTE_EARLY}
    A["登錄"] = reg_verify(); log(f"[登錄] {A['登錄']}")
    A["策略鎖"] = [lock_check("開跑前", log)]
    _G["COST0"] = R.COST
    if abs(R.COST - COST) > 1e-15:
        raise SystemExit(f"⛔ 引擎成本 {R.COST} ≠ 0.585%")
    WS = AO.worlds(log, procs); _G["WS"] = WS
    gates = {}
    for wn, W in WS.items():
        gates.update(W["gate"])
    # ── ★1 原版正式（真實價格）：eq_sha 閘＋成交清單 ──
    jobs = [(wn, sn, r) for wn in ("主", "早年") for sn in STR for r in seeds_of(sn)]
    with Pool(procs) as pool:
        res = pool.map(job_official, jobs, chunksize=4)
    ref = pd.read_csv("backtest/resultsYL_integrate/seeds.csv.gz", dtype={"eq_sha": str}, usecols=["世界", "格", "r", "eq_sha"])
    REF = {(w, k, int(r)): s for w, k, r, s in zip(ref["世界"], ref["格"], ref["r"], ref["eq_sha"])}
    OFF = {}
    nbad = 0
    for wn, sn, r, sh, tl in res:
        nbad += int(sh != REF[(wn, STR[sn]["key"], r)])
        OFF[(wn, sn, r)] = tl
    gates["★1 原版 eq_sha ≠ resultsYL_integrate（條數）"] = nbad
    log(f"[★1 原版閘] {len(res)} 條｜eq_sha 不同 {nbad}｜{time.time() - T0:.0f}s")
    if nbad:
        raise SystemExit("⛔ 原版 eq_sha 閘不過")
    UG.set_gate_v2(True)
    # ── 逐股、逐列 ──
    ROWS = {}; X1 = None; MINFO = {}
    for wn in ("主", "早年"):
        W = WS[wn]; cal = W["cal"]; n0 = len(cal); NP = W["NP"]
        sids = sorted(set(W["SIG"][False]["sid"]) | set(W["SIG"][True]["sid"]))
        M, HB, X1, info = AO.market(wn, W, X1, log, sids)
        # ★10 R1 描述：訊號日 R1 成員（AddOn 同一份 R1；快取股序）
        part = "main" if wn == "主" else "early"
        zs = pickle.load(open(os.path.join(AO.RLU_WORK, f"world_{part}.pkl"), "rb"))["sids"]
        zix = {s: i for i, s in enumerate(zs)}
        R1m = M["R1"]
        del M
        MINFO[wn] = info
        _G["data"] = W["data"]; _G["cal"] = cal
        with Pool(procs) as pool:
            LBS = dict(pool.map(bars_job, [(s, W["uni"].get(s, "twse")) for s in sids], chunksize=8))
        miss = [s for s in sids if LBS.get(s) is None]
        if miss:
            raise SystemExit(f"⛔ load_bars 取不到 {miss[:5]}")
        PK = {}; md = 0.0
        for s in sids:
            PK[s] = stock_pack(W, s, LBS[s], HB, n0, NP)
            idx, h, l, cb = LBS[s]; ok = idx < n0
            cw = PK[s]["c"][idx[ok]]; m_ = np.isfinite(cw) & np.isfinite(cb[ok])
            if m_.any():
                md = max(md, float(np.max(np.abs(cb[ok][m_] / cw[m_] - 1.0))))
        gates[f"{wn} load_bars 收盤 vs 世界收盤 最大相對差"] = md
        if md > 1e-6:
            raise SystemExit(f"⛔ {wn} 收盤閘 {md}")
        for sn in STR:
            T = build_rows(wn, sn, W, PK, n0)
            T["段"] = seg_of_pos(W, T["e"].to_numpy(int))
            T["R1_訊號日"] = [bool(R1m[zix[s], p]) if s in zix else False for s, p in zip(T["sid"], T["pos"])]
            ROWS[(wn, sn)] = T
            log(f"[逐列 {wn}·{sn}] {len(T)} 列｜理由 {dict(Counter(T['n_reason']))}")
        _G[("PK", wn)] = PK
        del R1m
    # ── ★9 組合層：乾跑引擎（原出場＝閘、賣 5）──
    DRY = {}
    for wn in ("主", "早年"):
        W = WS[wn]
        for sn in STR:
            for arm in ("o", "n"):
                sg_ = sig_with(W, sn, ROWS[(wn, sn)], arm, dry=True)
                cl = ones_prices(W, set(sg_["sid"]) | set(W["SF"]))
                DRY[(wn, sn, arm)] = {"sig": sg_, "cl": cl, "op": cl}
    _G["DRY"] = DRY
    jobs = [(wn, sn, arm, r) for wn in ("主", "早年") for sn in STR for arm in ("o", "n") for r in seeds_of(sn)]
    with Pool(procs) as pool:
        dres = pool.map(job_dry, jobs, chunksize=4)
    DT = {(wn, sn, arm, r): tl for wn, sn, arm, r, tl, _, _, _ in dres}
    rep = 0
    for (wn, sn, arm, r), tl in DT.items():
        if arm == "o":
            rep += int(tl != OFF[(wn, sn, r)])
    nsd = 0; ntot = 0
    for (wn, sn, arm, r), tl in DT.items():
        if arm == "o":
            bo, bd = set(OFF[(wn, sn, r)][0]), set(tl[0])
            nsd += len(bo ^ bd); ntot += len(bo)
    gates["★9 原出場乾跑成交清單 ≠ 正式（條數；無價格近似誤差）"] = rep
    gates["★9 原出場乾跑 vs 正式 買進對稱差（筆）／正式買進（筆）"] = [nsd, ntot]
    log(f"[★9 重現] 原出場乾跑 vs 正式成交清單 不同 {rep} 條｜買進對稱差 {nsd}／{ntot}｜{time.time() - T0:.0f}s")
    if ntot and nsd / ntot > 0.01:
        raise SystemExit("⛔ 無價格近似誤差 ＞ 1%：原出場乾跑與正式成交清單差太多")
    # ── 單筆層：原版實際成交 ──
    SINGLE = {}; WT = {}
    for (wn, sn), T in ROWS.items():
        cnt = Counter()
        for r in seeds_of(sn):
            for t, s in OFF[(wn, sn, r)][0]:
                cnt[f"{s}#{t}"] += 1
        miss = [k for k in cnt if k not in set(T["key"])]
        gates[f"{wn}·{sn} 正式買進不在訊號列（筆）"] = len(miss)
        if miss:
            raise SystemExit(f"⛔ {wn}·{sn} 正式買進找不到訊號列：{miss[:3]}")
        T["正式買進顆數"] = T["key"].map(cnt).fillna(0).astype(int)
        SINGLE[(wn, sn)] = T[T["正式買進顆數"] > 0].copy()
        WT[(wn, sn)] = dict(cnt)
    # 頻率表（單筆）
    FS = []; FJ = {}
    for (wn, sn), U in SINGLE.items():
        for sg in SEGS[wn]:
            V = U if sg in ("主窗",) else U[U["段"] == sg]
            if sg == "主窗":
                V = U[U["段"].isin(JSEG)]
            fj = single_freq(V, sn, sg, WT[(wn, sn)] if sn == "營飆" else None)
            FJ[f"{sn}·{wn}·{sg}"] = fj
            for nm in ("全部", "判定樣本"):
                z = fj[nm]
                if not z.get("n"):
                    continue
                FS.append({"策略": sn, "世界": wn, "段": sg, "樣本": nm, "筆": z["n"], "n_eff": fj["n_eff（訊號月，判定樣本）" if nm == "判定樣本" else "n_eff（訊號月，全部）"],
                           "賣5觸發比例": z["賣5觸發（上限前）比例"], "到250上限比例": z["到250上限比例"], "壞根前強制比例": z["壞根前強制比例"],
                           "停止交易比例": z["停止交易（引擎）比例"], "資料尾仍持有比例": z["資料尾仍持有比例"],
                           "★8隔天就賣比例": z["★8 買進日收盤已符合賣5、隔天就賣 比例"], "★8筆": z["★8 筆"],
                           "訊號日已符合賣5比例": z["〔另一讀法〕訊號日收盤已符合賣5 比例"], "進場日不可判比例": z["進場日 MA200／斜率不可判比例"],
                           "改版持有中位": z["持有天數 改版（賣5）"]["中位"], "改版持有p10": z["持有天數 改版（賣5）"]["p10"], "改版持有p90": z["持有天數 改版（賣5）"]["p90"],
                           "原版持有中位": z["持有天數 原版"]["中位"], "原版持有p10": z["持有天數 原版"]["p10"], "原版持有p90": z["持有天數 原版"]["p90"],
                           "早賣筆": z["改版比原版早賣筆"], "晚賣筆": z["改版比原版晚賣筆"], "同根筆": z["同一根賣筆"],
                           "R1內比例": z.get("★10 訊號日在 R1 內比例（描述）")})
    FS = pd.DataFrame(FS)
    # 旗標（裁定 seq492）
    FLAGS = []
    for _, r_ in FS.iterrows():
        if r_["段"] in ("探索", "確認", "主窗") and r_["樣本"] == "判定樣本":
            if r_["★8隔天就賣比例"] >= FLAG_SHARE:
                FLAGS.append(f"⚠ {r_['策略']}·{r_['段']} 買進日已符合賣5、隔天就賣 {r_['★8隔天就賣比例']:.1%} ≥ 10%（裁定 seq492：先回信）")
            if r_["訊號日已符合賣5比例"] >= FLAG_SHARE:
                FLAGS.append(f"⚠〔另一讀法〕{r_['策略']}·{r_['段']} 訊號日已符合賣5 {r_['訊號日已符合賣5比例']:.1%} ≥ 10%")
            if r_["n_eff"] < NEFF_MIN and r_["段"] in JSEG:
                FLAGS.append(f"⚠ {r_['策略']}·{r_['段']} 單筆層判定樣本 n_eff {r_['n_eff']} ＜ 24 ⇒ 還沒測")
    # 組合層頻率（⛔ 無報酬）
    FP = []; PJ = {}
    for wn in ("主", "早年"):
        W = WS[wn]
        for sn in STR:
            T = ROWS[(wn, sn)]
            S = STR[sn]; sig = W["SIG"][S["G"]]; cand = sig[sig[f"xpos_H{S['H']}"] >= 0][["sid", "entry_pos"]]
            Hn = {(s, int(e)): int(h) for s, e, h in zip(T["sid"], T["e"], T["n_H"])}
            Ho = {(s, int(e)): int(h) for s, e, h in zip(T["sid"], T["e"], T["o_H"])}
            per = {sg: [] for sg in SEGS[wn]}
            for r in seeds_of(sn):
                sf = port_stats(W, sn, *OFF[(wn, sn, r)], cand, Ho)
                so = port_stats(W, sn, *DT[(wn, sn, "o", r)], cand, Ho)
                sn_ = port_stats(W, sn, *DT[(wn, sn, "n", r)], cand, Hn)
                for sg in SEGS[wn]:
                    ko, kn, kf = set(so[sg]["買進鍵"]), set(sn_[sg]["買進鍵"]), set(sf[sg]["買進鍵"])
                    per[sg].append({"r": r, **{f"原_{k}": v for k, v in so[sg].items() if k != "買進鍵"}, **{f"改_{k}": v for k, v in sn_[sg].items() if k != "買進鍵"},
                                    **{f"正式_{k}": v for k, v in sf[sg].items() if k in ("買進筆", "滿倉日比例", "平均占槽", "名額不足沒進", "已持有沒進")},
                                    "補位多出": len(kn - ko), "補位少掉": len(ko - kn), "兩版都有": len(kn & ko),
                                    "〔另一讀法〕對正式 多出": len(kn - kf), "〔另一讀法〕對正式 少掉": len(kf - kn),
                                    "無價格近似誤差（原乾跑 vs 正式 對稱差）": len(ko ^ kf)})
            for sg in SEGS[wn]:
                P = pd.DataFrame(per[sg])
                row = {"策略": sn, "世界": wn, "段": sg, "顆數": len(P)}
                for c_ in P.columns:
                    if c_ == "r":
                        continue
                    v = pd.to_numeric(P[c_], errors="coerce")
                    row[c_ + "（中位）"] = float(v.median()) if v.notna().any() else None
                    if sn == "營飆" and c_ in ("補位多出", "補位少掉", "兩版都有", "原_買進筆", "改_買進筆", "原_名額不足沒進", "改_名額不足沒進"):
                        row[c_ + "（p10）"] = float(v.quantile(.1)); row[c_ + "（p90）"] = float(v.quantile(.9))
                    if sn == "營飆" and c_ in ("補位多出", "補位少掉", "無價格近似誤差（原乾跑 vs 正式 對稱差）"):
                        row[c_ + "（200 顆合計）"] = int(v.sum())
                FP.append(row)
                PJ[f"{sn}·{wn}·{sg}"] = row
    FP = pd.DataFrame(FP)
    log(f"[頻率表] 單筆 {len(FS)} 列、組合 {len(FP)} 列｜旗標 {FLAGS}｜{time.time() - T0:.0f}s")
    # ── 描述欄（正式／乾跑佔位）──
    DESC, DST = describe_all(WS, ROWS, SINGLE, OFF, DT, dry, procs, log)
    A.update({"閘": gates, "母體": MINFO, "旗標": FLAGS, "頻率表_單筆": FJ, "頻率表_組合": PJ})
    if dry:
        A["描述欄乾跑"] = DST
    else:
        A["正式"] = DESC
    A["策略鎖"].append(lock_check("跑完", log))
    A["耗時秒"] = round(time.time() - T0)
    FS.to_csv(os.path.join(od, "freq_single.csv"), index=False, float_format="%.6g", encoding="utf-8-sig")
    FP.to_csv(os.path.join(od, "freq_portfolio.csv"), index=False, float_format="%.6g", encoding="utf-8-sig")
    # 逐筆（⛔ 乾跑不存任何價格）
    keep = ["世界", "策略", "key", "sid", "e", "pos", "訊號日", "進場日", "訊號月", "段", "完成", "正式買進顆數", "o_xpos", "o_sale", "o_H", "o_sf", "o_尾", "o_跨壞根",
            "n_kind", "n_d", "n_sale", "n_xpos", "n_xe", "n_H", "n_sf", "n_reason", "n_flags", "x5_訊號日", "可判_訊號日", "可判_進場日", "e日觸發", "R1_訊號日"]
    pd.concat([U[keep] for U in SINGLE.values()]).to_csv(os.path.join(od, "trades_single.csv.gz"), index=False)
    json.dump(A, open(os.path.join(od, "freq.json" if dry else "formal.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=lambda o: o.item() if hasattr(o, "item") else str(o))
    log(f"[完成] {time.time() - T0:.0f}s ⇒ {od}")
    return A


def describe_all(WS, ROWS, SINGLE, OFF, DT, dry, procs, log):
    """登錄 §二 判定欄＋§三「正式跑另報」全部欄。dry ⇒ 價格、指數 1、成本 0（報酬全為 0），回 (值, 填表狀態)。"""
    from backtest import benchmark_rejudge as BR
    TRI = {}
    tri_sha = None
    if not dry:
        tri_sha = subprocess.run(["git", "rev-parse", "origin/main"], capture_output=True, text=True).stdout.strip()
        s = BR.read_series("git:origin/main:data/history/market_tri.csv")
    for wn, W in WS.items():
        TRI[wn] = np.ones(W["NP"]) if dry else np.r_[s.reindex(W["cal"]).ffill().to_numpy(float), [np.nan] * (W["NP"] - len(W["cal"]))]
    DESC = {"大盤報酬指數": "乾跑佔位 1" if dry else f"origin/main {tri_sha}"}
    # 組合層：每顆權益（乾跑 ⇒ 價格 1 引擎；正式 ⇒ 真實價格引擎）
    _G["KEEP_EQ"] = True
    MET = {}
    for wn in ("主", "早年"):
        W = WS[wn]
        for sn in STR:
            for arm in ("o", "n"):
                if dry:
                    _G["DRY"][(wn, sn, arm)] = _G["DRY"][(wn, sn, arm)]
                else:
                    sg_ = sig_with(W, sn, ROWS[(wn, sn)], arm, dry=False)
                    _G["DRY"][(wn, sn, arm)] = {"sig": sg_, "cl": W["closes"], "op": W["opens"]}
    if not dry:
        _G["COST0"] = R.COST
    jobs = [(wn, sn, arm, r) for wn in ("主", "早年") for sn in STR for arm in ("o", "n") for r in seeds_of(sn)]
    if not dry:
        # 正式：真實成本（job_dry 會把 COST 換成 0 ⇒ 正式用 job_real）
        with Pool(procs) as pool:
            rr = pool.map(job_real, jobs, chunksize=4)
    else:
        with Pool(procs) as pool:
            rr = pool.map(job_dry, jobs, chunksize=4)
    for wn, sn, arm, r, tl, eq, f_, e_ in rr:
        W = WS[wn]
        MET.setdefault((wn, sn, arm), []).append(port_metrics(W, eq, f_, e_, TRI[wn], dry))
        if not dry and arm == "o":
            if tl != OFF[(wn, sn, r)]:
                raise SystemExit("⛔ 正式原出場成交清單 ≠ 原版")
    PD = {}
    for wn in ("主", "早年"):
        for sn in STR:
            PD[f"{sn}·{wn}"] = port_desc(WS[wn], {"o": MET[(wn, sn, "o")], "n": MET[(wn, sn, "n")]}, sn, TRI[wn], dry)
    VER_P = {sn: {"探索": PD[f"{sn}·主"]["探索"]["變好"], "確認": PD[f"{sn}·主"]["確認"]["變好"],
                  "結論": ("變好" if (PD[f"{sn}·主"]["探索"]["變好"] and PD[f"{sn}·主"]["確認"]["變好"]) else
                         ("沒有變好（探索段就沒變好）" if not PD[f"{sn}·主"]["探索"]["變好"] else "沒有變好（確認段沒變好）"))} for sn in STR}
    DESC["組合層"] = PD; DESC["組合層判定"] = VER_P
    # 單筆層
    SD = {}; VER_S = {}
    for (wn, sn), U in SINGLE.items():
        J = U[U["完成"]]
        dd = {}
        for sg in SEGS[wn]:
            V = J[J["段"].isin(JSEG)] if sg == "主窗" else J[J["段"] == sg]
            dd[sg] = single_desc(V, TRI[wn], dry)
            dd[sg]["〔★4 另一讀法〕全收（截尾以資料尾收盤）"] = single_desc(U[U["段"].isin(JSEG)] if sg == "主窗" else U[U["段"] == sg], TRI[wn], dry)["每筆年化差（改−原）"]
        SD[f"{sn}·{wn}"] = dd
        if wn == "主":
            VER_S[sn] = single_verdict(dd)
    DESC["單筆層"] = SD; DESC["單筆層判定"] = VER_S
    # 現實版（主世界）
    W = WS["主"]
    SL, X = slip_setup(W, procs, log)
    RC = {}
    for sn in STR:
        z = {}
        for arm in ("o", "n"):
            sg_ = sig_with(W, sn, ROWS[("主", sn)], arm, dry=False)
            res = slip_run(SL, X, W, sn, sg_, dry, seeds_of(sn))
            z[arm] = {sg: {"年化中位": float(np.median([q["met"][sg][0] for q in res])), "回落中位": float(np.median([q["met"][sg][1] for q in res]))}
                      for sg in W["segp"]}
            z[arm]["tradability（r0）"] = res[0]["tr"]
        RC[sn] = z
    DESC["現實版（主世界）"] = RC
    log(f"[描述欄] {'乾跑佔位' if dry else '正式'} 完成")
    return DESC, fill_status(DESC)


def job_real(a):
    wn, sn, arm, r = a
    C = _G["DRY"][(wn, sn, arm)]; S = STR[sn]; W = _G["WS"][wn]
    au = []
    if sn == "營量":
        o = R.simulate_mtm(C["sig"], f"H{S['H']}", S["N"], np.random.default_rng(RR.P1_SEED0 + r), C["cl"], C["op"], W["NP"], return_equity=True,
                           log=[], d_max=None, pick="relvol", queue_days=0, stop_force=W["SF"], audit=au)
    else:
        o = R.simulate_mtm(C["sig"], f"H{S['H']}", S["N"], np.random.default_rng(RR.P10_SEED0 + r), C["cl"], C["op"], W["NP"], return_equity=True,
                           stop_force=W["SF"], audit=au)
    return wn, sn, arm, r, trade_list(au), np.asarray(o["equity"], float), int(o["first"]), int(o["end"])


def fill_status(DESC):
    """描述欄填表狀態：葉值 None ⇒ EMPTY；有限數 ⇒ filled；NaN ⇒ filled（0 佔位⇒NaN，例：比值 0÷0）；字串 ⇒ filled。⛔ 不輸出值。"""
    st = Counter(); empty = []

    def walk(p, v):
        if isinstance(v, dict):
            if not v:
                st["EMPTY"] += 1; empty.append(p); return
            for k, x in v.items():
                walk(f"{p}/{k}", x)
        elif isinstance(v, (list, tuple)):
            for i, x in enumerate(v):
                walk(f"{p}[{i}]", x)
        elif v is None:
            st["EMPTY"] += 1; empty.append(p)
        elif isinstance(v, (float, np.floating)) and not np.isfinite(v):
            st["filled（NaN：0 佔位）"] += 1
        else:
            st["filled"] += 1
    walk("", DESC)
    return {"葉欄數": int(sum(st.values())), **dict(st), "EMPTY 欄（前 60）": empty[:60], "EMPTY 欄數": len(empty)}


def gate_args(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--formal", action="store_true")
    ap.add_argument("--ruling", default=None)
    ap.add_argument("--procs", type=int, default=3)
    a = ap.parse_args(argv)
    if a.dry == a.formal:
        raise SystemExit("⛔ 要給 --dry 或 --formal（擇一）")
    if a.formal and a.ruling != RULING:
        raise SystemExit(f"⛔ 正式跑要 --formal --ruling {RULING}（收到 {a.ruling!r}）")
    return a


def main(argv=None):
    a = gate_args(sys.argv[1:] if argv is None else argv)
    mode = "dry" if a.dry else "formal"
    od = os.path.join(OUT, "freq" if a.dry else "formal")
    os.makedirs(od, exist_ok=True)
    log = AO.log_to(os.path.join(od, "run.log"))
    log(f"[開跑] {now_tpe()}（台北）模式 {mode}｜NSEED {NSEED}")
    run(mode, a.procs, log)


if __name__ == "__main__":
    main()
