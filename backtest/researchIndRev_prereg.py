# -*- coding: utf-8 -*-
"""PREREG產業營收加速 seq3（台股策略線登錄 sha 42339de513c98702；裁定 seq281 發號、N_組合 ＋1；seq282 §二 開跑）乙＋丙——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchIndRev_prereg [--procs 3] [--reps 1000] | --check | --page

═══ 讀法（寫死於 2026-10-03 23:42（台北），在算任何乙、丙數字之前；「★」＝ 登錄沒寫清楚、執行者補）═══
 P0 資料
    月營收 ＝ tw-stock-data origin/main（執行時取 sha；git archive 到 ~/h2data/indrevpr_<sha12>，唯讀）的 data/early/revenue（2003-01～2014-12，上市＋上櫃）
      ＋ data/mops/revenue_hist（2015-01～）；欄「當月營收」「去年當月營收」（千元）。同 (代號, 期別) 重複（2007～2008 上櫃彙總表同一公司列兩次：舊母類與新子類）
      ⇒ 數值取最後一列（同 snapshot load_rev）；類別（P1 fallback 用）取非「電子工業／化學生技醫療」那列
    產業別 ＝ 同 sha 的 data/meta/industry_hist/industry_pit.csv（主表）、data/meta/industry.csv（現值版）
    價格、成交、漲跌停、下市、W1 eligible（researchScore 同一套）：
      主段 ＝ rerun17 快照 H2D（edc6f8002f）＋ resultsp9_engine/panel_ext.csv.gz；
      早年段 ＝ ~/earlydata/3edc0e2206/main/data（只上市）＋ sig_main/panel.csv.gz；母體 ＝ eligible ∩ gate3（早年只上市）、含已下市
    市值 ＝ 原始收盤 × shares，取 e−1 以前最後一筆兩者皆有限的列：主段 H2D stocks/<代號>.csv；早年 ~/earlydata/eotc_f65bb03e11/daily_all.pkl
      （main data/early/daily 原樣；3edc0e2206 上市列 shares 空白 ⇒ ★ 改用這份）
 P1 產業別 point-in-time：ind_at(代號, 日 d)
    ① industry_pit 有該檔：start ≤ d ≤ end 的段（start 空 ＝ 無下限、end 空 ＝ 至今）；d 晚於最後一段 ⇒ 最後一段（最後已知類別）；
       d 早於第一段 ⇒ 第一段；兩段之間的空隙 ⇒ 前一段（★）
    ② industry_pit 沒有該檔（多為 2015 前已下市；⛔ 不剔除）⇒ ★ 月營收彙總表該檔「d 時已公告的最近一期」的「產業別」欄（公告當時的類別）；
       名稱對齊：金融業／證券 → 金融保險、建材營建 → 建材營造、生物科技 → 生技醫療業、農業科技 → 農業科技業、通訊網路 → 通信網路業、軟體 → 資訊服務業；
       管理股票、之合計數、電子(二)、塑化紡織(二)、水泥窯製營造 ⇒ 無類別（不進任何產業；計數照報）
    名稱相同合併（上市、上櫃同名一類）；排除 金融保險、其他、存託憑證、ETF；股票 ＝ 四碼、首碼 1～9、非 91xx（early_data R2 同式），且 main stocks.csv 有該檔時 kind ＝ stock
    版本：主表 pit｜現值（industry.csv 現值；名稱空白代碼 32／33 ⇒ 文化創意業／農業科技業（同 pit README）；industry.csv 沒有的檔 ⇒ 照主表）｜
          剔除 2023 新增（主表，但 綠能環保、數位雲端、運動休閒、居家生活 四類不排名、不可挑）
    ⚠ 存活者偏差：industry_pit 對已下市公司只有公告段；② 補的是公告當時的彙總表類別（並報各來源股-月占比）
    ③ 改讀法（2026-10-03 23:48（台北）；⚠ 改之前只跑過冒煙測試、看過 3 個月的 A 表，⛔ 沒看過任何乙、丙輸出）：
       原因：冒煙測試發現月營收檔含「當時還沒上市櫃」的公司（2010-06 上市檔 49 檔、上櫃檔 71 檔當月沒有日 K；2020-06 上市檔 54 檔 first_seen 在之後，
       例 1563 巧新 2024 才上市卻在 2020-06 上市檔、類別也是現值名稱）⇒ 登錄「上市、上櫃官方產業別」⇒ ★ P2 的產業營收成員加「d 當時已上市櫃」：
       d ≥ 2015-01-05 ⇒ main stocks.csv first_seen ≤ d ≤ last_seen；d 更早 ⇒ main data/early/daily（eotc daily_all）在 d 當月或前一月有有效收盤；
       沒有日 K 可查的時段（上市 2004-03 前、上櫃 2007-07 前）⇒ 月營收檔有就當作已上市櫃（照實標、計數）。挑股本來就要 W1 eligible，不受影響
 P2 產業營收與 A（⭐ 沿用 researchIndRev_snapshot.compute_ind 同一支函式，mode "new"）
    每個營收月 M：成員 ＝ 月營收檔裡所有合格代號，依 ind_at(代號, M 的可用日前一交易日) 分產業 ⇒ compute_ind(rev, rev_ly, 成員, M, "new")
      （同一個月檔「當月 ÷ 去年當月」、每月各自的同公司集合、多月分子分母分別加總；A1 近 3 月、A2 ＝ A1 − 近 12 月、A3 ＝ A1 − 三個月前的 A1；公司數 ＜ 5 不排名）
    可用日 ＝ research34.rebalance_dates(pub_day 10)：M＋1 月 10 日之後第一個交易日（日曆 ＝ 早年版面 ≤ 2014-12-31 接 H2D）
    剔除 2013 版（描述，只影響早年段）：期別 2013-01～2013-12 的當月、去年當月都設空後重算；★ 某換股日沒有可排名產業 ⇒ 該次不換股（持股照舊）
 P3 換股日：季 ＝ 營收月 12、3、6、9 的可用日（1、4、7、10 月）；半年 ＝ 12、6；年 ＝ 12；★ 窗首即建倉（同 researchScore）：窗首日用「可用日 ≤ 窗首」的最新月
    換股日 e 用的月 M ＝ 可用日 ≤ e 的最新月；續抱仍入選
 P4 挑產業：A 由大到小（同值依名稱）前 K（公司數 ≥ 5、A 有限）；反向臂 ＝ 由小到大；E1～E3 被賣出、出場條件仍成立的產業 ⇒ ★ 跳過、由下一名遞補
 P5 挑股：該產業成員 ＝ e 同月量測日 W1 eligible（researchScore.eligible_by_reb）∩ gate3 ∩ ind_at(代號, e 前一交易日) ∩ 有價格 ∩ 市值有限 ＞ 0；依市值大到小（同值依代號）
    S1 前 20、S2 前 3、S3 最新月（M）營收創 24 月新高（當月營收 ≥ 前 24 期最高、25 期皆有值；snapshot S4 同式）者前 10
    每檔目標金額：S1／S2 ＝ 前一日權益 ÷（K × n_i）（n_i ＝ 該產業實際入選檔數：★「不足 20 全買」＝ 產業那份由實際檔數平分）；S3 ＝ 前一日權益 ÷（K × 10）（不足剩現金）
    產業入選 0 檔 ⇒ 那份現金；新入選買進順序 ＝ 產業名次、再市值
 P6 換股簿（sim_ind ＝ researchScore.sim_book 同一套成交與成本：落選開盤賣、開盤跌停／停牌延後、下市了結、續抱不再平衡、買進 min(目標, 現金)、
    開盤漲停／停牌買不到不遞補、賣出時扣進場金額 × 0.585%、停止交易強制出場開；本檔只多「每檔目標金額」與「產業整批出場」）
    閘 G1：每檔目標 ＝ 前一日權益 ÷ N、不開出場臂、名額上限 N ⇒ sim_ind 與 researchScore.sim_book 權益逐位元相同（抽 3 組選股表）
 P7 出場 E（產業層，整個產業一起賣）
    E0 定期；E1：每個營收可用日 t（含換股日），持有中產業 A2(M_t) ＜ 0 且 A2(M_t 前一月) ＞ 0 ⇒ t 開盤賣（NaN 不觸發）
    E2／E3：產業持股等權指數 ＝ 該產業目前持股的等權日報酬連乘（續抱用 c[t]/c[t−1]、當天買進用 c[t]/買價）；本次持有期間（入選起、連續入選不斷）最高收盤；
      收盤 ≤ (1−X) × 最高 ⇒ 次一交易日開盤賣（X ＝ 20%／30%）
    出場後該份現金到下一換股日；★「出場條件已不成立」：E1 ＝ 最新可用月 A2 ≥ 0；E2／E3 ＝ 出場那批股票的等權指數延續計算，前一日收盤 ＞ (1−X) × 出場時的持有期間最高；
      仍成立 ⇒ 該換股日跳過，下一個換股日再判，直到再被挑中
    同一天順序：停止交易強制出場 → E 出場 → 換股日選股 → 賣 → 買
 P8 段與判定
    主段一條連續權益 2017-03-02～2026-08-24：探索 2017-03-02～2021-12-30（挑）、確認 2022-01-03～2026-08-24（判）（R13.window_stats、245 日／年）
    早年段 ＝ 2012-06-01～2014-12-30（只上市；W1 eligible 自 2012-06 起才有：個股法人 inst_ok 早年缺）；2005-01～2012-05 W1 母體依構造做不出 ⇒ 標「不可判定」
    退化（探索段，事前排除）：平均持股 ＜ 3 或 平均現金比例 ＞ 30%
    挑格：非退化中過使用者判準者取比值最高；都沒過 ⇒ 非退化中比值最高；平手 ⇒ 年化高、A、K、S、R、E 順
    判定：確認段、早年段各自標籤（合格 ＞ 另列 ＞ 不合格）取較嚴；★ 兩段都合格時因 2005-01～2012-05 不可判定 ⇒ 寫「暫定合格」
    早年覆蓋率：2005～2014 每月「月營收檔中當月與去年當月皆 ＞ 0 的合格代號 ÷ 當月有日 K 的合格代號」（main data/early/daily；上市、上櫃分開；上櫃日 K 2007-07 起）
      年平均 ＜ 90%（上市）⇒ 該年標不可判定（★ 門檻）
 P9 0050 ＝ RR.load_bench（各段資料自己的 0050 還原收盤）同窗；主窗錨逐位元（同 researchScore）
 P10 對照（挑中格同 K、S、R、E）：隨機挑產業 1,000 次（default_rng([20261003, r])；每換股日把可排名產業依名稱排好後 permutation，跳過仍被禁的取前 K）；
    反向臂；全產業等權（★ K ＝ 當日全部可排名產業，挑股與出場同挑中格）；營量 v1（T1：同 researchScore 丁，逐位元對 resultsT1fix c13）；
    早年 營量 v1 引 resultsYLretest/b2_early_seeds.csv main|開|N20|H60 r0（窗 2012-06-04～2014-12-31，略不同窗，照標）；0050
 P11 現實版（挑中格；researchSlip 定義落到換股簿）：C1 每邊 ＋0.3%；C2 資金 50 萬：每筆 Q ＝ 50 萬 × 該筆金額 ÷ 前一日權益，單邊衝擊 ＝ σ20 × √(Q ÷ ADV20)
    （researchSlip.stock_extra 同式），買價 ×(1＋i)、賣價 ×(1−min(i, 0.99))；C3 一字漲跌停 ⇒ ★ 本簿基準已是「開盤漲停買不到、開盤跌停賣不掉」（比一字嚴）⇒ 不另加；
    C4 成交價 ＝ 當日 (開＋高＋低＋收)÷4（強制出場、下市了結仍用收盤）；另報 ＋C5 低消 20 元：每筆 A ＝ 50 萬 × 金額 ÷ 前一日權益，單邊另加 max(20÷A − 0.1425%, 0)
 P12 必報：挑中產業清單與次數；★ 持股與 0050 重疊率（0050 代理 ＝ 已載入上市普通股市值前 50、市值權重；換股日收盤後持股權重 Σmin，同 d4_overlap 口徑）；
    各年報酬；換手（年買進金額 ÷ 平均權益）與成本／年；216 格全表；同 A×K×S×R 下 E1～E3 對 E0 的年化差、回落差、平均持有天數（產業每段持有交易日數）、現金比例
    另報（描述）：現值版、剔除 2023 新增版、剔除 2013 版（早年）、早年母體放寬版（2005-02-01～2014-12-30，母體 ＝ early 面板 liq_ok ∧ bars_ok，去掉 inst_ok）
 P13 丙（描述）
    產業指數 ＝ 當月量測日成員（主段 W1 eligible；★ 早年用 liq_ok ∧ bars_ok，因 2012-06 前沒有 W1）∩ 該產業（量測日 PIT）的等權日報酬（ffill 還原收盤，兩日皆有限）連乘
    「產業×換股日」＝ 挑中格的 A、K、R 在 E0 下每次換股的前 K 名（S 不影響）：I_s ＝ I[e−1]（訊號當下）；訊號前已漲 ＝ I_s ÷ min(I[e−250..e−1]) − 1（另 60、120）；
      頂 ＝ max(I[e..e+499])；起漲到頂 ＝ ln(頂 ÷ 低)；吃到幾成 ＝ ln(頂 ÷ I_s) ÷ ln(頂 ÷ 低)；吃到 ≤ 0 ＝ 之後沒再超過 I_s；
      實際持有吃到幾成 ＝ ln(I[下一換股日−1] ÷ I_s) ÷ ln(頂 ÷ 低)（照 R 一期）；之後回落 ≥ 20／30% ＝ I[e−1..e+499] 從滾動最高的最大回落
      500 日不足（資料尾）⇒ 照算、標「未滿 500 日」並另報剔除後；ln(頂 ÷ 低) ≤ 0 ⇒ 吃到幾成為空
      分組：探索段「訊號前已漲（250 日）」中位數切兩半（≥ 中位 ＝ 已漲多）；同一門檻套到確認段、早年段
    出場面（挑中格 A×K×S×R 下 E0～E3 各自；每段產業持有：進場日 s → 出場日 x）：吃到 ＝ ln(I[x−1] ÷ I[s−1]) ÷ ln(頂 ÷ 低)（頂、低以 s 為準）；
      躲掉多少 ＝ min(I[x−1..x+249]) ÷ I[x−1] − 1；賣早了 ＝ 出場後 250 日內 I 超過持有期間最高收盤（錯過的漲幅 ＝ max(I[x..x+249]) ÷ I[x−1] − 1）；
      賣在頂點附近 ＝ I[x−1] ≥ 0.9 × 頂；窗尾仍持有 ⇒ 不列（筆數照報）
    股價先見頂？：上面 E0 的每段持有（進場 s）：股價頂日 ＝ argmax I[s..s+499]；營收頂 ＝ 可用日落在 [s, s+499] 的月份中 A1 最大者（同值取早）；
      時間差（月）＝（營收頂可用日 − 股價頂日）交易日 ÷ 21（正 ＝ 股價先見頂）；另報以營收月月底為準的日曆月差
 P14 查核（--check）：① 挑中格＋另抽 1 格（default_rng(20261003) 從 216 格抽），從原始 csv 獨立重建（industry_pit 逐列、月營收 csv 逐列、面板 eligible、
    原始收盤 × shares、24 月新高逐期比），獨立寫的逐日迴圈重算選股、持股、交易與權益 ⇒ 換股日持股集合、每筆買賣（日、檔、價）0 不同，權益相對差 ≤ 1e−9；
    ①′ 2026-10-04 00:12（台北）加（主程式結果已出、看過；只加查核、⛔ 讀法不變）：另從 E1～E3 的 162 格抽 1 格（default_rng([20261003, 1])）一併逐筆重算；
       查核一律用主程式同一個 main sha（第一次查核時 origin/main 已前進到 0f5ef73ee8，A 值抽查與逐筆重算仍 0 不同）
    ② 抽 2 個產業×月（default_rng(20261003)），從原始 csv 逐公司重算 A1、A2、A3、公司數 ⇒ 差 ≤ 1e−12；③ 閘 G1 重跑 ⇒ 全部 0 不同才算過
輸出 backtest/resultsIndRev/prereg/：cells_main.csv、cells_early.csv、chosen_picks.csv、industry_counts.csv、years.csv、controls.json、random.csv.gz、variants.csv、
    c_pairs.csv、c_exit.csv、c_gap.csv、coverage_early.csv、A_table.csv.gz、eq.npz、meta.json、check.json、產業營收加速回測.html
"""
from __future__ import annotations

import argparse
import bisect
import glob
import hashlib
import html
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
from backtest import data as D
from backtest import rerun17 as RR
from backtest import research11 as R
from backtest import research13 as R13
from backtest import research34 as R34
from backtest import researchScore as SC
from backtest import researchIndRev_snapshot as SNAP
from backtest import tradability as TR
from backtest import universe_gate as UG
from backtest import p4_features as P4F

TIME = "2026-10-03 23:42（台北）"
OUT = "backtest/resultsIndRev/prereg"
PARTS_GIT = ["data/meta/industry_hist", "data/meta/industry.csv", "data/meta/stocks.csv", "data/mops/revenue_hist", "data/early/revenue"]
EOTC_DAILY = os.path.expanduser("~/earlydata/eotc_f65bb03e11/daily_all.pkl")
MAIN_W = ("2017-03-02", "2026-08-24")
SEG = {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}
EARLY_A = ("2012-06-01", "2014-12-30")
EARLY_X = ("2005-02-01", "2014-12-30")
AS = ("A1", "A2", "A3"); KS = (1, 3); SS = ("S1", "S2", "S3"); RS = ("季", "半年", "年"); ES = ("E0", "E1", "E2", "E3")
RMON = {"季": (12, 3, 6, 9), "半年": (12, 6), "年": (12,)}
SN = {"S1": 20, "S2": 3, "S3": 10}
EXX = {"E2": 0.20, "E3": 0.30}
EXCL = {"金融保險", "其他", "存託憑證", "ETF"}
NEW2023 = {"綠能環保", "數位雲端", "運動休閒", "居家生活"}
FB_MAP = {"金融業": "金融保險", "證券": "金融保險", "金融保險業": "金融保險", "建材營建": "建材營造", "生物科技": "生技醫療業", "農業科技": "農業科技業",
          "通訊網路": "通信網路業", "軟體": "資訊服務業"}
FB_NONE = {"管理股票", "之合計數", "電子(二)", "塑化紡織(二)", "水泥窯製營造", ""}
OLDNAMES = {"電子工業", "化學生技醫療"}
COST = SC.COST
SEED_R = 20261003
CAP = 500_000
ANCHOR = (0.24020209886370614, -0.3395700527611012)
RANKL = {"合格": 2, "另列": 1, "不合格": 0}
_C: dict = {}
LOGF = None


def log(x):
    x = f"[{time.strftime('%H:%M:%S')}] {x}"
    print(x, flush=True)
    if LOGF:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(x + "\n")


def mshift(m, k):
    y, mm = int(m[:4]), int(m[5:]); t = y * 12 + mm - 1 + k
    return f"{t // 12:04d}-{t % 12 + 1:02d}"


def okcode(s):
    return isinstance(s, str) and len(s) == 4 and s.isdigit() and s[0] in "123456789" and not s.startswith("91")


def fin(x):
    return x is not None and isinstance(x, (float, int, np.floating, np.integer)) and np.isfinite(x)


# ═════════════ 資料 ═════════════
def ensure_data(sha=None):
    sha = sha or subprocess.run(["git", "rev-parse", "origin/main"], capture_output=True, text=True, check=True).stdout.strip()
    root = os.path.expanduser(f"~/h2data/indrevpr_{sha[:12]}")
    if not os.path.isdir(os.path.join(root, "data", "early", "revenue")):
        os.makedirs(root, exist_ok=True)
        p = subprocess.run(["git", "archive", "--format=tar", sha] + PARTS_GIT, capture_output=True, check=True)
        subprocess.run(["tar", "-x", "-C", root], input=p.stdout, check=True)
        log(f"[資料] git archive {sha[:10]} ⇒ {root}")
    return sha, os.path.join(root, "data")


def rev_files(DATA):
    return sorted(glob.glob(os.path.join(DATA, "early", "revenue", "*.csv"))) + sorted(glob.glob(os.path.join(DATA, "mops", "revenue_hist", "*.csv")))


def load_rev(DATA):
    fs = rev_files(DATA)
    df = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "market", "產業別", "當月營收", "去年當月營收"]) for f in fs], ignore_index=True)
    df["rev"] = pd.to_numeric(df["當月營收"], errors="coerce"); df["rev_ly"] = pd.to_numeric(df["去年當月營收"], errors="coerce")
    df["產業別"] = df["產業別"].fillna("")
    df["_old"] = df["產業別"].isin(OLDNAMES)
    cat = df.sort_values(["stock_id", "period", "_old"], kind="stable").drop_duplicates(["stock_id", "period"], keep="first")[["stock_id", "period", "market", "產業別"]]
    val = df.drop_duplicates(["stock_id", "period"], keep="last")
    pers = sorted(val["period"].unique()); full = [pers[0]]
    while full[-1] < pers[-1]:
        full.append(mshift(full[-1], 1))
    rev = val.pivot(index="period", columns="stock_id", values="rev").reindex(full).sort_index()
    rev_ly = val.pivot(index="period", columns="stock_id", values="rev_ly").reindex(full).sort_index()
    mk = val.sort_values("period").drop_duplicates("stock_id", keep="last").set_index("stock_id")["market"].to_dict()
    return rev, rev_ly, cat, mk, len(fs), int(len(df))


class PIT:
    """industry_pit ＋ fallback ＋ 現值（P1）。"""

    def __init__(self, DATA, cat):
        p = pd.read_csv(os.path.join(DATA, "meta", "industry_hist", "industry_pit.csv"), dtype=str)
        self.seg = defaultdict(list)
        for sid, ind, a, b in zip(p["stock_id"], p["industry"], p["start"], p["end"]):
            a_ = pd.Timestamp(a) if isinstance(a, str) and a else pd.Timestamp.min
            b_ = pd.Timestamp(b) if isinstance(b, str) and b else pd.Timestamp.max
            self.seg[sid].append((a_, b_, ind))
        for k in self.seg:
            self.seg[k].sort(key=lambda z: z[0])
        cur = pd.read_csv(os.path.join(DATA, "meta", "industry.csv"), dtype=str).fillna("")
        self.cur = {}
        for sid, nm, code in zip(cur["stock_id"], cur["industry_name"], cur["industry_code"]):
            if not nm:
                nm = {"32": "文化創意業", "33": "農業科技業", "91": "存託憑證"}.get(code, "")
            if nm:
                self.cur[sid] = nm
        self.fb = {}
        for sid, g in cat.groupby("stock_id"):
            self.fb[sid] = (g["period"].tolist(), [None if c in FB_NONE else FB_MAP.get(c, c) for c in g["產業別"]])
        self.memo = {}

    def at(self, sid, d, ver="pit"):
        key = (sid, d, ver == "現值")
        if key in self.memo:
            return self.memo[key]
        r = self._at(sid, d, ver)
        self.memo[key] = r
        return r

    def _at(self, sid, d, ver):
        if ver == "現值" and sid in self.cur:
            return self.cur[sid], "現值"
        if sid in self.seg:
            sg = self.seg[sid]
            for a, b, ind in sg:
                if a <= d <= b:
                    return ind, "pit"
            if d > sg[-1][1]:
                return sg[-1][2], "pit最後已知"
            if d < sg[0][0]:
                return sg[0][2], "pit首段前"
            prev = [z for z in sg if z[1] < d]
            return prev[-1][2], "pit空隙"
        if sid in self.fb:
            pers, cats = self.fb[sid]
            lim = mshift(f"{d.year:04d}-{d.month:02d}", -1 if d.day > 10 else -2)
            k = bisect.bisect_right(pers, lim) - 1
            if k >= 0:
                return cats[k], "營收彙總表"
        return None, "無"


T2015 = pd.Timestamp("2015-01-05")


def listed(sid, d, M):
    """P1 ③：d 當時已上市櫃？⇒ (bool, 依據)。"""
    if d >= T2015:
        r = _C["strange"].get(sid); ds = str(d.date())
        return (r is not None and r[0] <= ds <= r[1]), "stocks.csv"
    ym = f"{d.year:04d}-{d.month:02d}"
    if (sid, ym) in _C["dk"] or (sid, mshift(ym, -1)) in _C["dk"]:
        return True, "早年日K"
    if d < pd.Timestamp("2004-03-01"):
        return True, "無日K可查（上市 2004-03 前）"
    if d < pd.Timestamp("2007-07-01") and _C["revmk"].get((sid, M)) == "tpex":
        return True, "無日K可查（上櫃 2007-07 前）"
    return False, "早年日K"


def member_frame(sids, d, ver, mk_rev, kind, M=None):
    rows = []; src = Counter()
    for s in sids:
        if not okcode(s) or kind.get(s, "stock") != "stock":
            continue
        if M is not None:
            ok, lb = listed(s, d, M)
            has = bool(np.isfinite(_C["rev"].at[M, s]))
            if not ok:
                if has:
                    src["當月有營收但未上市櫃（剔）"] += 1
                continue
            if has:
                src[f"當月有營收、上市櫃依據：{lb}"] += 1
        ind, b = _C["PIT"]._at(s, d, ver)
        src[b] += 1
        if ind is None or ind in EXCL:
            continue
        rows.append((s, ind, mk_rev.get(s, "twse")))
    return pd.DataFrame(rows, columns=["stock_id", "產業", "market"]), src


def _a_month(args):
    M, ver = args
    rev, rev_ly = (_C["rev13"], _C["revly13"]) if ver == "剔除2013" else (_C["rev"], _C["rev_ly"])
    d = _C["pitday"][M]
    mem, src = member_frame(_C["revsids"], d, "現值" if ver == "現值" else "pit", _C["mk_rev"], _C["kind"], M)
    T, _ = SNAP.compute_ind(rev, rev_ly, mem, M, "new")
    T = T[["產業", "公司數", "近3月年增", "近12月年增", "A1", "A2", "A3"]].copy()
    T["M"] = M; T["ver"] = ver
    return T, dict(src)


# ═════════════ 段（part）準備 ═════════════
def part_ctx(name, procs):
    """快取包裝（只快取資料層：價格、母體、市值；內容由 _part_ctx 決定）。"""
    cp = os.path.expanduser(f"~/h2data/indrevpr_cache_{name}.pkl")
    if os.path.exists(cp):
        C = pickle.load(open(cp, "rb"))
        D.DATA = C["data"]
        log(f"[{name}] 讀快取 {cp}")
        return C
    C = _part_ctx(name, procs)
    pickle.dump(C, open(cp, "wb"), protocol=5)
    return C


def _part_ctx(name, procs):
    """name ∈ {main, early}：日曆、價格、母體、市值、可用日 ⇒ dict。"""
    t0_ = time.time()
    if name == "main":
        RR.use_snapshot(); panel = SC.PANEL_EXT
    else:
        D.DATA = SC.EARLY_DATA; panel = os.path.join(SC.EARLY_SIG, "panel.csv.gz")
    cal = D.load_calendar(); ncal = len(cal)
    U = UG.gate3(pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str))
    if name == "early":
        U = U[U["market"] == "twse"]
    mk = U.set_index("stock_id")["market"].to_dict(); keep = set(mk)
    pn = P4F.read_panel(panel)
    pn = pn[pn["stock_id"].isin(keep)]
    el = pn["eligible"].astype(str).eq("True"); lb = pn["liq_ok"].astype(str).eq("True") & pn["bars_ok"].astype(str).eq("True")
    memW = {d: sorted(g) for d, g in pn.loc[el].groupby("measure_date")["stock_id"]}
    memX = {d: sorted(g) for d, g in pn.loc[lb].groupby("measure_date")["stock_id"]}
    meas = sorted(set(pn["measure_date"]))
    lo = pd.Timestamp("2016-01-01") if name == "main" else pd.Timestamp("2004-01-01")
    sids = sorted({s for d, v in (memW if name == "main" else memX).items() if d >= lo for s in v} | {s for v in memW.values() for s in v})
    SC._G.update(cal=cal)
    with Pool(procs) as pool:
        P = dict(pool.map(SC.load_px, [(s, mk.get(s, "twse")) for s in sids], chunksize=16))
    P = {s: v for s, v in P.items() if v is not None}
    try:
        off = TR.load_official()
    except Exception:
        off = {}
    dl = TR.delist_status({s: {"trd": v["trd"]} for s, v in P.items()}, cal, official=off)
    bench = RR.load_bench(cal)
    # 市值（原始收盤 × shares，ffill）
    MC = {}
    if name == "main":
        for s in P:
            raw = pd.read_csv(os.path.join(D.DATA, "stocks", f"{s}.csv"), dtype={"date": str}, usecols=["date", "close", "shares"])
            raw["date"] = pd.to_datetime(raw["date"]); raw = raw.drop_duplicates("date").set_index("date")
            v = (pd.to_numeric(raw["close"], errors="coerce") * pd.to_numeric(raw["shares"], errors="coerce"))
            v = v.where(v > 0)
            MC[s] = v.reindex(cal).ffill().to_numpy(float) if v.notna().any() else np.full(ncal, np.nan)
            # reindex 之後的 ffill 只往後帶 ⇒ 位置 t 的值 ＝ t 以前最後一筆
    else:
        da = pickle.load(open(EOTC_DAILY, "rb"))
        da = da[da["stock_id"].isin(set(P))][["date", "stock_id", "close", "shares"]].copy()
        da["v"] = pd.to_numeric(da["close"], errors="coerce") * pd.to_numeric(da["shares"], errors="coerce")
        da = da[da["v"] > 0].drop_duplicates(["stock_id", "date"], keep="last")
        da["date"] = pd.to_datetime(da["date"])
        pv = da.pivot(index="date", columns="stock_id", values="v").reindex(cal).ffill()
        for s in P:
            MC[s] = pv[s].to_numpy(float) if s in pv.columns else np.full(ncal, np.nan)
    log(f"[{name}] 日曆 {cal[0].date()}～{cal[-1].date()}（{ncal}）｜gate3 {len(keep)}｜載入 {len(P)} 檔｜量測日 {len(meas)}｜{time.time() - t0_:.0f}s")
    return {"name": name, "cal": cal, "ncal": ncal, "P": P, "dl": dl, "bench": bench, "MC": MC, "mk": mk, "memW": memW, "memX": memX, "meas": meas,
            "data": D.DATA, "panel": panel, "SF": {}}


def attach_months(C):
    """可用日、每日最新月、換股日。"""
    cal = C["cal"]; gav = _C["avail_date"]
    av = {}
    for M, dd in gav.items():
        p = int(cal.searchsorted(dd))
        if p < len(cal) and cal[p] == dd:
            av[p] = M
    C["availday"] = av
    ps = sorted(av); Ms = [av[p] for p in ps]
    Ml = [None] * C["ncal"]; j = -1
    for t in range(C["ncal"]):
        while j + 1 < len(ps) and ps[j + 1] <= t:
            j += 1
        Ml[t] = Ms[j] if j >= 0 else None
    C["Mlast"] = Ml
    C["reb"] = {}


def reb_days(C, R_, t0, t1):
    k = (R_, t0, t1)
    if k not in C["reb"]:
        mons = RMON[R_]
        C["reb"][k] = sorted({t0} | {p for p, M in C["availday"].items() if t0 < p <= t1 and int(M[5:]) in mons})
    return C["reb"][k]


def elig_at(C, t, mode):
    """researchScore.eligible_by_reb 同式：t 同月的最後一個量測日。"""
    d = C["cal"][t]; mem = C["memW"] if mode == "W1" else C["memX"]
    mm = [m for m in C["meas"] if m.year == d.year and m.month == d.month]
    return mem.get(max(mm), []) if mm else []


def picks_at(C, ver, mode, t):
    """⇒ {產業: {S: [代號...]}}（P5）。"""
    key = (ver, mode, t)
    cache = C.setdefault("pk", {})
    if key in cache:
        return cache[key]
    d = C["cal"][t - 1]; M = C["Mlast"][t]
    grp = defaultdict(list); nomc = 0
    for s in elig_at(C, t, mode):
        if s not in C["P"]:
            continue
        ind, _ = _C["PIT"].at(s, d, "現值" if ver == "現值" else "pit")
        if ind is None or ind in EXCL:
            continue
        mc = C["MC"][s][t - 1]
        if not (np.isfinite(mc) and mc > 0):
            nomc += 1; continue
        grp[ind].append((-mc, s))
    out = {}
    hi = _C["hi24"]
    for ind, lst in grp.items():
        lst.sort()
        o = [s for _, s in lst]
        h = [s for s in o if (s in hi.columns and M in hi.index and bool(hi.at[M, s]))]
        out[ind] = {"S1": o[:20], "S2": o[:3], "S3": h[:10]}
    cache[key] = out
    C.setdefault("nomc", Counter())[key] = nomc
    return out


def ranked(ver, A, M, order):
    T = _C["RANK"].get((ver, A, M))
    if T is None:
        return []
    return T[order]


def build_rank(AT):
    out = {}
    for (ver, M), g in AT.groupby(["ver", "M"]):
        g = g[(g["公司數"] >= 5)]
        for A in AS:
            h = g[np.isfinite(g[A].to_numpy(float))]
            if ver == "剔除2023":
                h = h[~h["產業"].isin(NEW2023)]
            top = h.sort_values([A, "產業"], ascending=[False, True])["產業"].tolist()
            bot = h.sort_values([A, "產業"], ascending=[True, True])["產業"].tolist()
            out[(ver, A, M)] = {"top": top, "bottom": bot, "names": sorted(h["產業"].tolist())}
    return out


def a_val(ver, M, ind, A):
    v = _C["AV"].get((("pit" if ver == "剔除2023" else ver), M, ind))
    return v[A] if v is not None else np.nan


# ═════════════ 換股簿模擬 ═════════════
def sim_ind(C, t0, t1, cfg, rng=None, fixed=None, gate_N=None, real=None):
    """P6／P7。cfg：A K S R E ver order(top|bottom|random|all) elig(W1|X)。fixed ＝ {t: [(代號, 產業)]}（閘 G1 用；除數 gate_N）。"""
    P, dl, ncal = C["P"], C["dl"], C["ncal"]
    if t1 not in C["SF"]:
        C["SF"][t1] = R.stop_force_days({s: v["valid"] for s, v in P.items()}, t1)
    SF = C["SF"][t1]
    ver = cfg.get("ver", "pit"); A = cfg.get("A"); K = cfg.get("K"); S = cfg.get("S"); E = cfg.get("E", "E0")
    order = cfg.get("order", "top"); mode = cfg.get("elig", "W1")
    reb = sorted(fixed) if fixed is not None else reb_days(C, cfg["R"], t0, t1)
    rebset = set(reb)
    eq = np.ones(ncal); cash = 1.0
    pos = {}; pend = set(); pind = {}; pbuy = {}; prate = {}
    npos = np.zeros(ncal, np.int16); cashf = np.zeros(ncal); costd = np.zeros(ncal); buyd = np.zeros(ncal)
    cnt = {"buy": 0, "sell": 0, "buy_blocked_limit_up": 0, "buy_blocked_halt": 0, "sell_delayed_days": 0, "delist_settled": 0,
           "delist_ambig_days": 0, "stop_force": 0, "cost_paid": 0.0, "ban_skip": 0, "ind_empty": 0, "reb_skip_norank": 0, "exits": 0}
    held = {}; ban = {}; exit_next = set(); episodes = []; picks = {}; snaps = {}; trades = []
    X_ = EXX.get(E)
    rx = real or {}
    for t in range(t0, t1 + 1):
        # ── 停止交易強制出場
        for s in [s for s in pos if SF.get(s) is not None and t == SF[s] + 1]:
            u, amt = pos.pop(s)
            px = P[s]["c"][t]; cr = prate.pop(s, COST)
            cash += u * px - amt * cr; costd[t] += amt * cr; cnt["cost_paid"] += amt * cr; cnt["stop_force"] += 1
            pend.discard(s); pind.pop(s, None); pbuy.pop(s, None); trades.append((t, s, "sf", px))
        # ── E 出場
        ex = []
        if E in EXX:
            ex = sorted(i for i in exit_next if i in held)
        elif E == "E1" and t in C["availday"]:
            M_ = C["availday"][t]
            for i in sorted(held):
                a2, a2p = a_val(ver, M_, i, "A2"), a_val(ver, mshift(M_, -1), i, "A2")
                if np.isfinite(a2) and np.isfinite(a2p) and a2 < 0 and a2p > 0:
                    ex.append(i)
        exit_next = set()
        for i in ex:
            h = held.pop(i)
            basket = sorted(s for s in pos if pind.get(s) == i)
            pend |= set(basket)
            episodes.append({"ind": i, "start": h["start"], "end": t, "why": E})
            ban[i] = {"E": E, "I": h["I"], "peak": h["peak"], "basket": basket}
            cnt["exits"] += 1
        # ── 換股日選股
        sel = None
        if t in rebset:
            if fixed is not None:
                sel = [s for s, _ in fixed[t]]; div = {s: gate_N for s in sel}; sind = dict(fixed[t]); chosen = sorted(set(sind.values()))
            else:
                M = C["Mlast"][t]
                if order == "random":
                    nm = ranked(ver, A, M, "names"); rk = [nm[k] for k in rng.permutation(len(nm))] if nm else []
                else:
                    rk = ranked(ver, A, M, "bottom" if order == "bottom" else "top")
                if not rk:
                    cnt["reb_skip_norank"] += 1
                else:
                    chosen = []
                    for i in rk:
                        if i in ban:
                            b = ban[i]
                            hold_ = (lambda a2: np.isfinite(a2) and a2 < 0)(a_val(ver, M, i, "A2")) if b["E"] == "E1" else (b["I"] <= (1 - EXX[b["E"]]) * b["peak"])
                            if hold_:
                                cnt["ban_skip"] += 1; continue
                            del ban[i]
                        chosen.append(i)
                        if order != "all" and len(chosen) == K:
                            break
                    Kd = len(chosen) if order == "all" else K
                    PK = picks_at(C, ver, mode, t)
                    sel = []; div = {}; sind = {}
                    for i in chosen:
                        lst = PK.get(i, {}).get(S, [])
                        if not lst:
                            cnt["ind_empty"] += 1
                        n_i = SN["S3"] if S == "S3" else len(lst)
                        for s in lst:
                            sel.append(s); div[s] = Kd * n_i; sind[s] = i
            if sel is not None:
                pend = (pend | (set(pos) - set(sel))) - set(sel)
                for i in list(held):
                    if i not in chosen:
                        h = held.pop(i); episodes.append({"ind": i, "start": h["start"], "end": t, "why": "換股"})
                for i in chosen:
                    if i not in held:
                        held[i] = {"start": t, "I": 1.0, "peak": -np.inf}
                for s in sel:
                    if s in pos:
                        pind[s] = sind[s]
                picks[t] = list(chosen)
        # ── 賣
        for s in sorted(pend):
            x = P[s]; o_t = (rx["X"][s]["avg"][t] if rx.get("c4") else x["o"][t])
            if x["trd"][t] and not x["dn_o"][t] and np.isfinite(o_t) and o_t > 0:
                px = o_t; kd = "open"
            elif (not x["trd"][t]) and s in dl and t > dl[s]["last"] and dl[s]["status"].startswith("delisted"):
                px = x["c"][t]; kd = "delist"; cnt["delist_settled"] += 1
            else:
                cnt["sell_delayed_days"] += 1
                if (not x["trd"][t]) and s in dl and t > dl[s]["last"]:
                    cnt["delist_ambig_days"] += 1
                continue
            u, amt = pos.pop(s)
            pxe = px
            if rx.get("cap") and kd == "open":
                xs = rx["X"][s]; Q = rx["cap"] * (u * px) / eq[t - 1]
                ix = xs["sig20"][t] * np.sqrt(Q / xs["adv20"][t]) if (np.isfinite(xs["adv20"][t]) and xs["adv20"][t] > 0 and np.isfinite(xs["sig20"][t])) else 0.0
                pxe = px * (1 - min(ix, 0.99))
            cr = prate.pop(s, COST)
            cash += u * pxe - amt * cr; costd[t] += amt * cr; cnt["cost_paid"] += amt * cr; cnt["sell"] += 1
            pend.discard(s); pind.pop(s, None); pbuy.pop(s, None); trades.append((t, s, kd, px))
        # ── 買
        if sel is not None:
            if gate_N is not None:
                new = [s for s in sel if s not in pos][:max(gate_N - len(pos), 0)]
            else:
                new = [s for s in sel if s not in pos]
            for s in new:
                x = P[s]; o_t = (rx["X"][s]["avg"][t] if rx.get("c4") else x["o"][t])
                if not x["trd"][t] or not (np.isfinite(o_t) and o_t > 0):
                    cnt["buy_blocked_halt"] += 1; continue
                if x["up_o"][t]:
                    cnt["buy_blocked_limit_up"] += 1; continue
                amt = min(eq[t - 1] / div[s], cash)
                if amt <= 1e-12:
                    break
                cash -= amt
                if real:
                    xs = rx["X"][s]; Q = rx["cap"] * amt / eq[t - 1]
                    ie = xs["sig20"][t] * np.sqrt(Q / xs["adv20"][t]) if (np.isfinite(xs["adv20"][t]) and xs["adv20"][t] > 0 and np.isfinite(xs["sig20"][t])) else 0.0
                    pos[s] = [amt / (o_t * (1 + ie)), amt]
                    prate[s] = COST + 2 * rx.get("s", 0.0) + (2 * max(rx["m5"] / Q - 0.001425, 0.0) if rx.get("m5") else 0.0)
                else:
                    pos[s] = [amt / o_t, amt]
                pind[s] = sind[s]; pbuy[s] = (t, o_t); cnt["buy"] += 1; buyd[t] += amt; trades.append((t, s, "buy", o_t))
        # ── 計值
        hv = 0.0
        for s, (u, _) in pos.items():
            hv += u * P[s]["c"][t]
        eq[t] = cash + hv
        npos[t] = len(pos); cashf[t] = cash / eq[t] if eq[t] > 0 else np.nan
        if sel is not None:
            snaps[t] = {s: (u * P[s]["c"][t] / eq[t], pind.get(s)) for s, (u, _) in pos.items()}
        # ── 產業持股等權指數（E2／E3）
        if X_ is not None:
            grp = defaultdict(list)
            for s in pos:
                if s in pind:
                    grp[pind[s]].append(s)
            for i, h in held.items():
                rs = []
                for s in grp.get(i, []):
                    bt, bp = pbuy[s]; ref = bp if bt == t else P[s]["c"][t - 1]; ct = P[s]["c"][t]
                    if np.isfinite(ct) and np.isfinite(ref) and ref > 0:
                        rs.append(ct / ref - 1)
                if rs:
                    h["I"] *= 1 + float(np.mean(rs)); h["peak"] = max(h["peak"], h["I"])
                    if h["I"] <= (1 - X_) * h["peak"]:
                        exit_next.add(i)
            for i, b in ban.items():
                rs = [P[s]["c"][t] / P[s]["c"][t - 1] - 1 for s in b["basket"] if np.isfinite(P[s]["c"][t]) and np.isfinite(P[s]["c"][t - 1]) and P[s]["c"][t - 1] > 0]
                if rs:
                    b["I"] *= 1 + float(np.mean(rs))
    eq[t1 + 1:] = eq[t1]
    for i, h in held.items():
        episodes.append({"ind": i, "start": h["start"], "end": None, "why": "窗尾"})
    return {"eq": eq, "npos": npos, "cashf": cashf, "costd": costd, "buyd": buyd, "cnt": cnt, "episodes": episodes, "picks": picks, "snaps": snaps,
            "trades": trades, "reb": reb}


# ═════════════ 指標 ═════════════
def stats(res, a, b, t1):
    c, m, ratio = SC.seg_metrics(res["eq"], a, b)
    yrs = (b + 1 - a) / 245; meq = float(res["eq"][a:b + 1].mean())
    ep = [e for e in res["episodes"] if a <= e["start"] <= b]
    hd = [((e["end"] if e["end"] is not None else t1 + 1) - e["start"]) for e in ep]
    return {"年化": c, "回落": m, "比值": ratio, "年化波動": RR.ann_vol(res["eq"][a:b + 1]),
            "平均持股": float(res["npos"][a:b + 1].mean()), "現金比例": float(np.nanmean(res["cashf"][a:b + 1])),
            "每年換手": float(res["buyd"][a:b + 1].sum()) / meq / yrs, "成本／年": float(res["costd"][a:b + 1].sum()) / meq / yrs,
            "產業持有段數": len(ep), "平均持有天數": float(np.mean(hd)) if hd else np.nan,
            "E出場次數": sum(1 for e in ep if e["why"] in ES and e["why"] != "E0")}


def segpos(C, segs):
    return {k: (SC.pos_of(C["cal"], x), SC.pos_of(C["cal"], y)) for k, (x, y) in segs.items()}


def lab(c, m, c0, m0):
    if not (np.isfinite(c) and np.isfinite(m)) or m >= 0:
        return "—"
    return SC.label(c, m, c0, m0)


def cells():
    return [dict(A=a, K=k, S=s, R=r, E=e) for a in AS for k in KS for s in SS for r in RS for e in ES]


def ckey(c):
    return f"{c['A']}|K{c['K']}|{c['S']}|{c['R']}|{c['E']}"


def _cell_job(args):
    part, cfg = args
    C = _C[part]; t0, t1 = C["win"]
    res = sim_ind(C, t0, t1, dict(cfg, ver="pit", order="top", elig="W1"))
    out = {"key": ckey(cfg), **cfg}
    for nm, (a, b) in C["segp"].items():
        st = stats(res, a, b, t1)
        out.update({f"{nm}_{k}": v for k, v in st.items()})
    out["計數"] = json.dumps({k: (round(v, 6) if isinstance(v, float) else v) for k, v in res["cnt"].items()}, ensure_ascii=False)
    out["picks"] = json.dumps({str(C["cal"][t].date()): v for t, v in res["picks"].items()}, ensure_ascii=False)
    return out, res["eq"].astype(np.float64)


def _rand_job(args):
    part, cfg, r = args
    C = _C[part]; t0, t1 = C["win"]
    res = sim_ind(C, t0, t1, dict(cfg, ver="pit", order="random", elig="W1"), rng=np.random.default_rng([SEED_R, r]))
    out = {"part": part, "r": r}
    for nm, (a, b) in C["segp"].items():
        c, m, ratio = SC.seg_metrics(res["eq"], a, b)
        out.update({f"{nm}_年化": c, f"{nm}_回落": m, f"{nm}_比值": ratio})
    return out


def year_rets(eq, cal, a, b):
    out = {}; prev = a
    for y in sorted(set(cal[a:b + 1].year)):
        e = int(np.flatnonzero((cal.year == y) & (np.arange(len(cal)) <= b))[-1])
        out[str(y)] = float(eq[e] / eq[prev] - 1); prev = e
    return out


def overlap50(C, res, a, b):
    """P12：換股日收盤後持股權重 vs 上市普通股市值前 50（市值權重）Σmin。"""
    vals = []
    tw = [s for s in C["P"] if C["mk"].get(s) == "twse"]
    for t, w in res["snaps"].items():
        if not (a <= t <= b) or not w:
            continue
        mc = sorted(((C["MC"][s][t - 1], s) for s in tw if np.isfinite(C["MC"][s][t - 1])), reverse=True)[:50]
        tot = sum(v for v, _ in mc); px = {s: v / tot for v, s in mc}
        vals.append(sum(min(wv[0], px.get(s, 0.0)) for s, wv in w.items()))
    return float(np.mean(vals)) if vals else np.nan, len(vals)


# ═════════════ 丙 ═════════════
def ind_index(C, mode):
    """P13 產業指數：{產業: I（日曆長，起點前 NaN）}。"""
    cal = C["cal"]; n = C["ncal"]
    sids = sorted(C["P"]); ix = {s: k for k, s in enumerate(sids)}
    Cm = np.vstack([C["P"][s]["c"] for s in sids])
    with np.errstate(invalid="ignore", divide="ignore"):
        Rm = np.full_like(Cm, np.nan); Rm[:, 1:] = Cm[:, 1:] / Cm[:, :-1] - 1
    mem = C["memW"] if mode == "W1" else C["memX"]
    meas = sorted(mem)
    rr = defaultdict(lambda: np.full(n, np.nan))
    for j, md in enumerate(meas):
        a = int(cal.searchsorted(md)); b = int(cal.searchsorted(meas[j + 1])) if j + 1 < len(meas) else n
        grp = defaultdict(list)
        for s in mem[md]:
            if s not in ix:
                continue
            ind, _ = _C["PIT"].at(s, md, "pit")
            if ind is None or ind in EXCL:
                continue
            grp[ind].append(ix[s])
        for ind, rows in grp.items():
            blk = Rm[rows, a:b]
            with np.errstate(invalid="ignore"):
                cntf = np.isfinite(blk).sum(0); sm = np.nansum(blk, 0)
            v = np.where(cntf > 0, sm / np.maximum(cntf, 1), np.nan)
            rr[ind][a:b] = v
    I = {}
    for ind, r in rr.items():
        f = np.flatnonzero(np.isfinite(r))
        if not len(f):
            continue
        x = np.full(n, np.nan); g = np.nan_to_num(r[f[0]:], nan=0.0)
        x[f[0] - 1 if f[0] > 0 else 0] = 1.0
        x[f[0]:] = np.cumprod(1 + g)
        I[ind] = x
    return I


def pair_rows(C, I, pk, reb, t1, segp):
    rows = []; n = C["ncal"]
    for j, e in enumerate(reb):
        e2 = reb[j + 1] if j + 1 < len(reb) else t1 + 1
        for rank, ind in enumerate(pk.get(e, [])):
            x = I.get(ind)
            if x is None or e < 1 or not np.isfinite(x[e - 1]):
                rows.append({"日": str(C["cal"][e].date()), "e": e, "產業": ind, "名次": rank + 1, "缺": 1}); continue
            Is = x[e - 1]
            r = {"日": str(C["cal"][e].date()), "e": e, "產業": ind, "名次": rank + 1, "缺": 0, "段": next((k for k, (a, b) in segp.items() if a <= e <= b), "")}
            for L in (250, 120, 60):
                w = x[max(0, e - L):e]
                r[f"已漲{L}"] = Is / np.nanmin(w) - 1 if np.isfinite(w).any() else np.nan
            low = np.nanmin(x[max(0, e - 250):e]); post = x[e:min(n, e + 500)]
            top = np.nanmax(post) if np.isfinite(post).any() else np.nan
            r["未滿500日"] = int(e + 500 > n)
            den = math.log(top / low) if (np.isfinite(top) and top > low) else np.nan
            r["起漲到頂"] = den
            r["吃到幾成"] = math.log(top / Is) / den if np.isfinite(den) else np.nan
            r["之後沒再創高"] = int(np.isfinite(top) and top <= Is)
            Ie = x[e2 - 1] if e2 - 1 < n else np.nan
            r["持有報酬"] = Ie / Is - 1
            r["實際持有吃到幾成"] = math.log(Ie / Is) / den if (np.isfinite(den) and np.isfinite(Ie)) else np.nan
            path = x[e - 1:min(n, e + 500)]; path = path[np.isfinite(path)]
            dd = float((path / np.maximum.accumulate(path) - 1).min()) if len(path) else np.nan
            r["之後最大回落"] = dd; r["回落20"] = int(dd <= -0.2); r["回落30"] = int(dd <= -0.3)
            rows.append(r)
    return rows


def exit_rows(C, I, episodes, E):
    rows = []; n = C["ncal"]
    for ep in episodes:
        x = I.get(ep["ind"]); s = ep["start"]
        if ep["end"] is None:
            rows.append({"E": E, "產業": ep["ind"], "進場": str(C["cal"][s].date()), "未出場": 1}); continue
        xe = ep["end"]
        if x is None or not np.isfinite(x[s - 1]) or not np.isfinite(x[xe - 1]):
            continue
        Is, Ix = x[s - 1], x[xe - 1]
        low = np.nanmin(x[max(0, s - 250):s]); post = x[s:min(n, s + 500)]; top = np.nanmax(post)
        den = math.log(top / low) if top > low else np.nan
        hh = np.nanmax(x[s:xe]) if xe > s else Is
        aft = x[xe:min(n, xe + 250)]
        r = {"E": E, "產業": ep["ind"], "進場": str(C["cal"][s].date()), "出場": str(C["cal"][xe].date()), "原因": ep["why"], "未出場": 0,
             "持有天數": xe - s, "持有報酬": Ix / Is - 1, "吃到幾成": math.log(Ix / Is) / den if np.isfinite(den) else np.nan,
             "躲掉多少": float(np.nanmin(x[xe - 1:min(n, xe + 250)]) / Ix - 1),
             "賣早了": int(np.isfinite(aft).any() and np.nanmax(aft) > hh), "錯過的漲幅": float(np.nanmax(aft) / Ix - 1) if np.isfinite(aft).any() else np.nan,
             "賣在頂點附近": int(Ix >= 0.9 * top), "出場後未滿250日": int(xe + 250 > n)}
        rows.append(r)
    return rows


def gap_rows(C, I, episodes, A_ver="pit"):
    rows = []; n = C["ncal"]; cal = C["cal"]
    av = sorted(C["availday"].items())
    for ep in episodes:
        x = I.get(ep["ind"]); s = ep["start"]
        if x is None:
            continue
        w = x[s:min(n, s + 500)]
        if not np.isfinite(w).any():
            continue
        tp = s + int(np.nanargmax(w))
        ms = [(p, M) for p, M in av if s <= p < s + 500 and p < n]
        vals = [(a_val(A_ver, M, ep["ind"], "A1"), p, M) for p, M in ms]
        vals = [v for v in vals if np.isfinite(v[0])]
        if not vals:
            continue
        best = max(v[0] for v in vals); vp, pp, Mp = next(v for v in vals if v[0] == best)
        me = pd.Timestamp(Mp + "-01") + pd.offsets.MonthEnd(0)
        rows.append({"產業": ep["ind"], "進場": str(cal[s].date()), "股價頂日": str(cal[tp].date()), "營收A1頂月": Mp, "營收頂可用日": str(cal[pp].date()),
                     "時間差_月（可用日）": (pp - tp) / 21, "時間差_月（營收月底）": (me - cal[tp]).days / 30.4375, "未滿500日": int(s + 500 > n)})
    return rows


# ═════════════ 早年覆蓋率 ═════════════
def coverage(rev, rev_ly):
    da = pickle.load(open(EOTC_DAILY, "rb"))[["date", "stock_id", "market", "close"]]
    da = da[da["stock_id"].map(okcode) & pd.to_numeric(da["close"], errors="coerce").gt(0)]
    da["M"] = da["date"].str[:7]
    lst = da.drop_duplicates(["M", "stock_id", "market"])
    rows = []
    for (M, mkt), g in lst.groupby(["M", "market"]):
        if not ("2005-01" <= M <= "2014-12") or M not in rev.index:
            continue
        a = rev.loc[M]; b = rev_ly.loc[M]
        okset = set(a.index[(a > 0) & (b > 0)])
        ls = set(g["stock_id"])
        rows.append({"月": M, "年": M[:4], "市場": mkt, "有日K家數": len(ls), "有營收年增家數": len(ls & okset), "覆蓋率": len(ls & okset) / len(ls) if ls else np.nan})
    T = pd.DataFrame(rows)
    Y = T.groupby(["年", "市場"]).agg(月數=("月", "size"), 有日K家數=("有日K家數", "mean"), 有營收年增家數=("有營收年增家數", "mean"),
                                    覆蓋率=("覆蓋率", "mean"), 最低月覆蓋率=("覆蓋率", "min")).reset_index()
    return T, Y


# ═════════════ 主程式 ═════════════
def setup(a, sha=None):
    sha, DATA = ensure_data(sha)
    rev, rev_ly, cat, mk_rev, nfiles, nrows = load_rev(DATA)
    stocks_main = pd.read_csv(os.path.join(DATA, "meta", "stocks.csv"), dtype=str)
    kind = stocks_main.drop_duplicates("stock_id", keep="last").set_index("stock_id")["kind"].to_dict()
    _C.update(rev=rev, rev_ly=rev_ly, mk_rev=mk_rev, kind=kind, PIT=PIT(DATA, cat), sha=sha, DATA=DATA,
              revsids=sorted(s for s in rev.columns if okcode(s)))
    _C["strange"] = {s: (f, l) for s, f, l in zip(stocks_main["stock_id"], stocks_main["first_seen"], stocks_main["last_seen"])}
    _C["revmk"] = {(s, p): m for s, p, m in zip(cat["stock_id"], cat["period"], cat["market"])}
    da = pickle.load(open(EOTC_DAILY, "rb"))[["date", "stock_id", "close"]]
    da = da[pd.to_numeric(da["close"], errors="coerce") > 0]
    _C["dk"] = set(zip(da["stock_id"], da["date"].str[:7]))
    del da
    r13, l13 = rev.copy(), rev_ly.copy()
    m13 = [p for p in rev.index if p.startswith("2013-")]
    r13.loc[m13] = np.nan; l13.loc[m13] = np.nan
    _C.update(rev13=r13, revly13=l13)
    prev24 = rev.shift(1).rolling(24, min_periods=24).max()
    _C["hi24"] = (rev >= prev24) & rev.notna() & prev24.notna()
    # 全域日曆（早年版面 ≤ 2014-12-31 接 H2D）與可用日
    D.DATA = SC.EARLY_DATA; ce = D.load_calendar()
    RR.use_snapshot(); cm = D.load_calendar()
    gcal = ce[ce <= pd.Timestamp("2014-12-31")].append(cm[cm > pd.Timestamp("2014-12-31")])
    rd = R34.rebalance_dates(list(rev.index), gcal, 10)
    _C["avail_date"] = {M: gcal[e] for M, (_, e) in rd.items()}
    _C["pitday"] = {M: gcal[e - 1] for M, (_, e) in rd.items()}
    log(f"[營收] main {sha[:10]}｜{nfiles} 檔 {nrows} 列｜期別 {rev.index[0]}～{rev.index[-1]}｜代號 {len(_C['revsids'])}｜可用日到 {max(_C['avail_date'])}")
    return sha


def build_A(a):
    Ms = [M for M in _C["rev"].index if "2003-12" <= M and M in _C["pitday"]]
    jobs = [(M, "pit") for M in Ms] + [(M, "現值") for M in Ms] + [(M, "剔除2013") for M in Ms if "2011-01" <= M <= "2015-12"]
    t0 = time.time()
    with Pool(a.procs) as pool:
        res = pool.map(_a_month, jobs, chunksize=4)
    AT = pd.concat([r[0] for r in res], ignore_index=True)
    src = Counter()
    for (M, v), r in zip(jobs, res):
        if v == "pit":
            src.update(r[1])
    log(f"[A 表] {len(jobs)} 月×版｜{time.time() - t0:.0f}s｜PIT 來源（pit 版、所有代號×月）{dict(src)}")
    return AT, dict(src)


def gate_g1(C):
    """閘 G1：sim_ind（每檔 ＝ 前一日權益 ÷ N、無出場、名額 N）＝ researchScore.sim_book 逐位元。"""
    G1 = []
    t0, t1 = C["win"]
    if t1 not in C["SF"]:
        C["SF"][t1] = R.stop_force_days({s: v["valid"] for s, v in C["P"].items()}, t1)
    for (A_, K_, S_, R_) in (("A1", 3, "S2", "季"), ("A2", 1, "S1", "半年"), ("A3", 3, "S3", "年")):
        N = K_ * SN[S_]
        fx = {}
        for t in reb_days(C, R_, t0, t1):
            rk = ranked("pit", A_, C["Mlast"][t], "top")[:K_]
            PK = picks_at(C, "pit", "W1", t)
            fx[t] = [(s, i) for i in rk for s in PK.get(i, {}).get(S_, [])][:N]
        mine = sim_ind(C, t0, t1, {"E": "E0"}, fixed=fx, gate_N=N)
        ref = SC.sim_book({t: [s for s, _ in v] for t, v in fx.items()}, C["P"], C["dl"], C["SF"][t1], t0, t1, "hold", N)
        same = bool(np.array_equal(mine["eq"], ref["eq"]))
        G1.append({"格": f"{A_}|K{K_}|{S_}|{R_}", "N": N, "權益逐位元相同": same, "買": mine["cnt"]["buy"], "ref買": ref["cnt"]["buy"]})
    return G1


def run(a):
    T00 = time.time()
    sha = setup(a)
    ap_ = os.path.join(OUT, "A_table.csv.gz")
    if a.reuse_a and os.path.exists(ap_):
        AT = pd.read_csv(ap_, float_precision="round_trip"); src = json.load(open(ap_ + ".src.json", encoding="utf-8"))
        log("[A 表] 讀既有檔")
    else:
        AT, src = build_A(a)
        AT.to_csv(ap_, index=False, float_format="%.17g")
        json.dump(src, open(ap_ + ".src.json", "w", encoding="utf-8"), ensure_ascii=False)
        AT = pd.read_csv(ap_, float_precision="round_trip")
    _C["RANK"] = build_rank(pd.concat([AT, AT[AT["ver"] == "pit"].assign(ver="剔除2023")], ignore_index=True))
    _C["AV"] = {(v, M, i): {"A1": a1, "A2": a2, "A3": a3} for v, M, i, a1, a2, a3 in zip(AT["ver"], AT["M"], AT["產業"], AT["A1"], AT["A2"], AT["A3"])}
    META = {"讀法寫死": TIME, "main": sha, "PIT 來源計數（代號×月）": src, "成本": COST}
    # ── 早年覆蓋率
    CT, CY = coverage(_C["rev"], _C["rev_ly"])
    CY["判讀"] = np.where((CY["市場"] == "twse") & (CY["覆蓋率"] < 0.90), "不可判定", "")
    CY.to_csv(os.path.join(OUT, "coverage_early.csv"), index=False)
    META["早年覆蓋率"] = CY.to_dict("records")
    log("[覆蓋率] " + "；".join(f"{r['年']}{r['市場']} {r['覆蓋率']:.3f}" for r in META["早年覆蓋率"]))
    # ── 兩段
    for part, win, segs in (("main", MAIN_W, SEG), ("early", EARLY_A, {"早年": EARLY_A})):
        C = part_ctx(part, a.procs); attach_months(C)
        C["win"] = (SC.pos_of(C["cal"], win[0]), SC.pos_of(C["cal"], win[1])); C["segp"] = segpos(C, segs)
        _C[part] = C
    Cm, Ce = _C["main"], _C["early"]
    # 0050
    RR.use_snapshot()
    t0m, t1m = Cm["win"]
    cf, mf = R13.window_stats(Cm["bench"], 0, Cm["ncal"], t0m, t1m + 1)
    anchor = repr(float(cf)) == repr(ANCHOR[0]) and repr(float(mf)) == repr(ANCHOR[1])
    Z = {nm: SC.seg_metrics(Cm["bench"], x, y) for nm, (x, y) in Cm["segp"].items()}
    Z["早年"] = SC.seg_metrics(Ce["bench"], *Ce["segp"]["早年"])
    log(f"[0050] 主窗錨逐位元 {anchor}｜" + "｜".join(f"{k} {v[0]:.2%}／{v[1]:.2%}／{v[2]:.3f}" for k, v in Z.items()))
    if not anchor:
        raise SystemExit("⛔ 0050 錨不過")
    META["0050"] = {k: dict(zip(("年化", "回落", "比值"), v)) for k, v in Z.items()}
    # 預先算挑股（pit、W1；所有換股日）
    for C in (Cm, Ce):
        t0, t1 = C["win"]
        for R_ in RS:
            for t in reb_days(C, R_, t0, t1):
                picks_at(C, "pit", "W1", t)
    G1 = gate_g1(Cm)
    META["閘G1"] = G1
    log(f"[閘 G1] {G1}")
    if not all(g["權益逐位元相同"] for g in G1):
        raise SystemExit("⛔ 閘 G1 不過")
    # ── 216 格 × 兩段
    t0_ = time.time(); EQ = {}
    for part in ("main", "early"):
        with Pool(a.procs) as pool:
            res = pool.map(_cell_job, [(part, c) for c in cells()], chunksize=2)
        T = pd.DataFrame([r[0] for r in res])
        T.to_csv(os.path.join(OUT, f"cells_{part}.csv"), index=False, float_format="%.10g")
        EQ[part] = {r[0]["key"]: r[1] for r in res}
        log(f"[216 格 {part}] {time.time() - t0_:.0f}s")
    TM = pd.read_csv(os.path.join(OUT, "cells_main.csv")); TE = pd.read_csv(os.path.join(OUT, "cells_early.csv"))
    c0, m0, r0 = Z["探索"]
    TM["退化"] = (TM["探索_平均持股"] < 3) | (TM["探索_現金比例"] > 0.30)
    TM["探索_標籤"] = [lab(c, m, c0, m0) for c, m in zip(TM["探索_年化"], TM["探索_回落"])]
    TM["確認_標籤"] = [lab(c, m, Z["確認"][0], Z["確認"][1]) for c, m in zip(TM["確認_年化"], TM["確認_回落"])]
    TE["早年_標籤"] = [lab(c, m, Z["早年"][0], Z["早年"][1]) for c, m in zip(TE["早年_年化"], TE["早年_回落"])]
    TM = TM.merge(TE[["key", "早年_年化", "早年_回落", "早年_比值", "早年_平均持股", "早年_現金比例", "早年_標籤"]], on="key", how="left")
    cand = TM[~TM["退化"]].copy()
    cand["過"] = cand["探索_標籤"] == "合格"
    pool_ = cand[cand["過"]] if cand["過"].any() else cand
    oi = lambda col, seq: pool_[col].map({v: i for i, v in enumerate(seq)})
    pool_ = pool_.assign(_a=oi("A", AS), _k=oi("K", KS), _s=oi("S", SS), _r=oi("R", RS), _e=oi("E", ES))
    best = pool_.sort_values(["探索_比值", "探索_年化", "_a", "_k", "_s", "_r", "_e"], ascending=[False, False, True, True, True, True, True]).iloc[0]
    ck = best["key"]; CH = {k: (int(best[k]) if k == "K" else best[k]) for k in ("A", "K", "S", "R", "E")}
    lc, le = best["確認_標籤"], best["早年_標籤"]
    fin_ = min((lc, le), key=lambda z: RANKL.get(z, -1))
    final = "暫定合格" if fin_ == "合格" else fin_
    TM.to_csv(os.path.join(OUT, "cells_main.csv"), index=False, float_format="%.10g")
    META["挑格"] = {"退化格數": int(TM["退化"].sum()), "非退化": int((~TM["退化"]).sum()), "探索過判準格數": int(cand["過"].sum()), "挑中": ck, "挑中參數": CH,
                  "探索": {k: float(best[f"探索_{k}"]) for k in ("年化", "回落", "比值")}, "確認": {k: float(best[f"確認_{k}"]) for k in ("年化", "回落", "比值")},
                  "早年": {k: float(best[f"早年_{k}"]) for k in ("年化", "回落", "比值")}, "確認標籤": lc, "早年標籤": le, "判定": final,
                  "兩段都合格格數（全 216）": int(((TM["確認_標籤"] == "合格") & (TM["早年_標籤"] == "合格")).sum()),
                  "兩段都合格格數（非退化）": int(((TM["確認_標籤"] == "合格") & (TM["早年_標籤"] == "合格") & ~TM["退化"]).sum()),
                  "確認段合格格數": int((TM["確認_標籤"] == "合格").sum()), "早年段合格格數": int((TM["早年_標籤"] == "合格").sum())}
    log(f"[挑格] {json.dumps(META['挑格'], ensure_ascii=False)}")
    np.savez_compressed(os.path.join(OUT, "eq.npz"), main=EQ["main"][ck], early=EQ["early"][ck], bench_main=Cm["bench"], bench_early=Ce["bench"])
    json.dump(META, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    # ── 挑中格細項
    CHR = {}
    for part in ("main", "early"):
        C = _C[part]; t0, t1 = C["win"]
        res = sim_ind(C, t0, t1, dict(CH, ver="pit", order="top", elig="W1"))
        CHR[part] = res
        assert np.array_equal(res["eq"], EQ[part][ck])
    rows = []
    for part in ("main", "early"):
        C = _C[part]; res = CHR[part]
        for t, inds in sorted(res["picks"].items()):
            seg = next((k for k, (x, y) in C["segp"].items() if x <= t <= y), "")
            for rk_, i in enumerate(inds):
                rows.append({"段": seg, "換股日": str(C["cal"][t].date()), "營收月": C["Mlast"][t], "名次": rk_ + 1, "產業": i,
                             "A": a_val("pit", C["Mlast"][t], i, CH["A"]),
                             "持股": "、".join(s for s, (w_, i_) in sorted(res["snaps"].get(t, {}).items(), key=lambda z: -z[1][0]) if i_ == i)})
    PKS = pd.DataFrame(rows); PKS.to_csv(os.path.join(OUT, "chosen_picks.csv"), index=False)
    IC = PKS.groupby(["段", "產業"]).size().rename("次數").reset_index().sort_values(["段", "次數"], ascending=[True, False])
    IC.to_csv(os.path.join(OUT, "industry_counts.csv"), index=False)
    DET = {}
    for part in ("main", "early"):
        C = _C[part]; res = CHR[part]; t0, t1 = C["win"]
        for nm, (x, y) in C["segp"].items():
            st = stats(res, x, y, t1); ov, nov = overlap50(C, res, x, y)
            DET[nm] = {**st, "0050重疊率": ov, "重疊率換股日數": nov}
        DET[f"{part}_計數"] = res["cnt"]
    YR = []
    for part in ("main", "early"):
        C = _C[part]; t0, t1 = C["win"]
        yr = year_rets(CHR[part]["eq"], C["cal"], t0, t1); yb = year_rets(C["bench"] / C["bench"][t0], C["cal"], t0, t1)
        for y in yr:
            YR.append({"段": part, "年": y, "挑中格": yr[y], "0050": yb[y]})
    pd.DataFrame(YR).to_csv(os.path.join(OUT, "years.csv"), index=False)
    META["挑中格細項"] = DET
    # ── 對照
    CTRL = {}
    for part in ("main", "early"):
        C = _C[part]; t0, t1 = C["win"]
        for nm_, od in (("反向臂", "bottom"), ("全產業等權", "all")):
            res = sim_ind(C, t0, t1, dict(CH, ver="pit", order=od, elig="W1"))
            for sg, (x, y) in C["segp"].items():
                CTRL.setdefault(nm_, {})[sg] = stats(res, x, y, t1)
    t0_ = time.time()
    jobs = [(part, CH, r) for part in ("main", "early") for r in range(a.reps)]
    with Pool(a.procs) as pool:
        RD = pd.DataFrame(pool.map(_rand_job, jobs, chunksize=10))
    RD.to_csv(os.path.join(OUT, "random.csv.gz"), index=False)
    log(f"[隨機] {len(jobs)} 次｜{time.time() - t0_:.0f}s")
    RAND = {}
    for part in ("main", "early"):
        C = _C[part]
        for sg in C["segp"]:
            xx = RD.loc[RD["part"] == part, f"{sg}_年化"].to_numpy(float); rr_ = RD.loc[RD["part"] == part, f"{sg}_比值"].to_numpy(float)
            mine = DET[sg]["年化"]; mr = DET[sg]["比值"]
            RAND[sg] = {"中位": float(np.nanmedian(xx)), "p10": float(np.nanquantile(xx, .1)), "p90": float(np.nanquantile(xx, .9)),
                        "回落中位": float(RD.loc[RD["part"] == part, f"{sg}_回落"].median()), "p_年化": float(np.nanmean(xx >= mine)),
                        "p_比值": float(np.nanmean(rr_ >= mr)), "贏0050比例": float(np.nanmean(xx > Z[sg][0]))}
    CTRL["隨機"] = RAND
    # 營量 v1（T1）
    RR.use_snapshot()
    cal = Cm["cal"]
    RR.setup_and(cal, os.path.join(RR.OUT, "sig_edc6f", "and_signals.csv.gz"), "branch", lambda x: None, t1=True)
    G = RR._G; AND = G["AND"]; e_ = AND["entry_pos"].to_numpy()
    sig13 = AND[(e_ >= G["w0"]) & (e_ <= G["w1"])]
    SF13 = R.stop_force_days(R.valid_from_data(sorted(G["closes"]), Cm["mk"], cal), G["w1"])
    o13 = R.simulate_mtm(sig13, "H60", 20, np.random.default_rng(RR.P1_SEED0), G["closes"], G["opens"], G["ncal"], log=[], d_max=None,
                         pick="relvol", queue_days=0, return_equity=True, stop_force=SF13)
    eq13 = np.asarray(o13["equity"], float)
    c13, m13, _ = RR.win_metrics(eq13, o13["first"], o13["end"], G["w0"], G["w1"])
    Y13 = {}
    for nm, (x, y) in Cm["segp"].items():
        cc, mm = R13.window_stats(eq13, min(o13["first"], x), max(o13["end"], y + 1), x, y + 1)
        Y13[nm] = {"年化": float(cc), "回落": float(mm), "比值": float(cc) / abs(float(mm))}
    t1ok = SC._t1ref(c13, m13)
    b2 = pd.read_csv("backtest/resultsYLretest/b2_early_seeds.csv", float_precision="round_trip")
    b2 = b2[(b2["key"] == "main|開|N20|H60") & (b2["r"] == 0)].iloc[0]
    Y13["早年"] = {"年化": float(b2["cagr"]), "回落": float(b2["mdd"]), "比值": float(b2["cagr"]) / abs(float(b2["mdd"])), "窗": "2012-06-04～2014-12-31（b2e）"}
    CTRL["營量v1_T1"] = {"主窗": {"年化": float(c13), "回落": float(m13)}, **Y13, "＝ resultsT1fix c13 t1（逐位元）": t1ok}
    if not t1ok:
        raise SystemExit("⛔ 營量 v1 T1 與 resultsT1fix 不同")
    META["對照"] = CTRL
    log(f"[對照] {json.dumps({k: (v if k != '隨機' else v) for k, v in CTRL.items()}, ensure_ascii=False, default=float)[:3000]}")
    # ── 變體（描述）
    VAR = []

    def addv(name, part, cfg, win=None, segs=None, real=None):
        C = _C[part]
        if win is None:
            t0, t1 = C["win"]; sp = C["segp"]
        else:
            t0, t1 = SC.pos_of(C["cal"], win[0]), SC.pos_of(C["cal"], win[1]); sp = segpos(C, segs)
        if real is not None:
            from backtest import researchSlip as SL
            need = sorted({s for t in reb_days(C, cfg["R"], t0, t1) for i, d_ in picks_at(C, cfg.get("ver", "pit"), cfg.get("elig", "W1"), t).items() for s in d_.get(cfg["S"], [])})
            X = C.setdefault("Xreal", {})
            for s in need:
                if s not in X:
                    X[s] = SL.stock_extra(s, C["mk"].get(s, "twse"), C["cal"], C["ncal"])
            real = dict(real, X=X)
        res = sim_ind(C, t0, t1, cfg, real=real)
        for sg, (x, y) in sp.items():
            st = stats(res, x, y, t1)
            b = SC.seg_metrics(C["bench"], x, y)
            VAR.append({"版本": name, "段": sg, **st, "0050年化": b[0], "0050回落": b[1], "標籤": lab(st["年化"], st["回落"], b[0], b[1])})
        return res
    base = dict(CH, order="top", elig="W1")
    for part in ("main", "early"):
        D.DATA = _C[part]["data"]
        addv("主表（industry_pit）", part, dict(base, ver="pit"))
        addv("現值（industry.csv）", part, dict(base, ver="現值"))
        addv("剔除 2023 新增類別", part, dict(base, ver="剔除2023"))
        addv("現實版（C1 0.3%＋C2 50 萬＋C4）", part, dict(base, ver="pit"), real=dict(s=0.003, cap=CAP, c4=True))
        addv("現實版＋C5 低消 20 元", part, dict(base, ver="pit"), real=dict(s=0.003, cap=CAP, c4=True, m5=20))
    D.DATA = Ce["data"]
    addv("剔除 2013（早年）", "early", dict(base, ver="剔除2013"))
    addv("早年母體放寬（liq∧bars，去掉法人）", "early", dict(base, ver="pit", elig="X"), win=EARLY_X,
         segs={"2005-02～2008-06": ("2005-02-01", "2008-06-30"), "2008-07～2012-05": ("2008-07-01", "2012-05-31"), "2012-06～2014-12": ("2012-06-01", "2014-12-30"),
               "2005-02～2014-12": EARLY_X})
    # S3 跨 2013-01 的訊號數（早年）
    n13 = 0; nS3 = 0
    for t, inds in CHR["early"]["picks"].items():
        M = Ce["Mlast"][t]
        for i in inds:
            k_ = len(picks_at(Ce, "pit", "W1", t).get(i, {}).get("S3", []))
            nS3 += k_
            if "2013-01" <= M <= "2014-12":
                n13 += k_
    META["S3跨2013-01訊號（早年挑中格的挑中產業、S3 名單）"] = {"S3 名單檔次": nS3, "其中回看期跨 2013-01": n13}
    pd.DataFrame(VAR).to_csv(os.path.join(OUT, "variants.csv"), index=False, float_format="%.10g")
    # ── E 臂比較（同 A×K×S×R）
    EC = []
    for part in ("main", "early"):
        T_ = TM if part == "main" else TE
        for (A_, K_, S_, R_), g in T_.groupby(["A", "K", "S", "R"]):
            g = g.set_index("E")
            for sg in _C[part]["segp"]:
                for E_ in ("E1", "E2", "E3"):
                    EC.append({"段": sg, "A": A_, "K": K_, "S": S_, "R": R_, "E": E_, "年化差": g.at[E_, f"{sg}_年化"] - g.at["E0", f"{sg}_年化"],
                               "回落差": g.at[E_, f"{sg}_回落"] - g.at["E0", f"{sg}_回落"], "平均持有天數": g.at[E_, f"{sg}_平均持有天數"],
                               "E0平均持有天數": g.at["E0", f"{sg}_平均持有天數"], "現金比例": g.at[E_, f"{sg}_現金比例"], "E0現金比例": g.at["E0", f"{sg}_現金比例"]})
    ECD = pd.DataFrame(EC); ECD.to_csv(os.path.join(OUT, "e_compare.csv"), index=False, float_format="%.10g")
    META["E臂比較摘要"] = {f"{sg}|{E_}": {"年化差中位": float(g["年化差"].median()), "年化差>0比例": float((g["年化差"] > 0).mean()),
                                         "回落差中位": float(g["回落差"].median()), "格數": int(len(g))}
                         for (sg, E_), g in ECD.groupby(["段", "E"])}
    # ── 丙
    CP, CX, CG = [], [], []
    for part in ("main", "early"):
        C = _C[part]; t0, t1 = C["win"]
        I = ind_index(C, "W1" if part == "main" else "X")
        C["I"] = I
        res0 = sim_ind(C, t0, t1, dict(CH, E="E0", ver="pit", order="top", elig="W1"))
        rows = pair_rows(C, I, res0["picks"], res0["reb"], t1, C["segp"])
        for r in rows:
            r["part"] = part
        CP += rows
        for E_ in ES:
            rE = res0 if E_ == "E0" else sim_ind(C, t0, t1, dict(CH, E=E_, ver="pit", order="top", elig="W1"))
            xr = exit_rows(C, I, rE["episodes"], E_)
            for r in xr:
                r["part"] = part
            CX += xr
        g = gap_rows(C, I, res0["episodes"])
        for r in g:
            r["part"] = part
        CG += g
    CPD, CXD, CGD = pd.DataFrame(CP), pd.DataFrame(CX), pd.DataFrame(CG)
    med = float(CPD.loc[(CPD["part"] == "main") & (CPD["段"] == "探索") & (CPD["缺"] == 0), "已漲250"].median())
    CPD["半"] = np.where(CPD["已漲250"] >= med, "已漲多", "已漲少"); CPD.loc[CPD["缺"] == 1, "半"] = ""
    CPD.to_csv(os.path.join(OUT, "c_pairs.csv"), index=False, float_format="%.8g"); CXD.to_csv(os.path.join(OUT, "c_exit.csv"), index=False, float_format="%.8g")
    CGD.to_csv(os.path.join(OUT, "c_gap.csv"), index=False, float_format="%.6g")
    # 丙 18 組 A×K×R（E0 前 K 名）描述
    ALLP = []
    for part in ("main",):
        C = _C[part]; t0, t1 = C["win"]
        for A_ in AS:
            for K_ in KS:
                for R_ in RS:
                    reb = reb_days(C, R_, t0, t1)
                    pk = {t: ranked("pit", A_, C["Mlast"][t], "top")[:K_] for t in reb}
                    rr_ = pd.DataFrame(pair_rows(C, C["I"], pk, reb, t1, C["segp"]))
                    rr_ = rr_[rr_["缺"] == 0]
                    ALLP.append({"A": A_, "K": K_, "R": R_, "筆數": len(rr_), "已漲250平均": rr_["已漲250"].mean(), "已漲250中位": rr_["已漲250"].median(),
                                 "吃到幾成中位": rr_["吃到幾成"].median(), "持有報酬平均": rr_["持有報酬"].mean(),
                                 "已漲多持有報酬平均": rr_.loc[rr_["已漲250"] >= med, "持有報酬"].mean(), "已漲少持有報酬平均": rr_.loc[rr_["已漲250"] < med, "持有報酬"].mean()})
    pd.DataFrame(ALLP).to_csv(os.path.join(OUT, "c_allAKR.csv"), index=False, float_format="%.6g")
    META["丙"] = c_summary(CPD, CXD, CGD, med)
    META["耗時秒"] = round(time.time() - T00)
    json.dump(META, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] {time.time() - T00:.0f}s")


def c_summary(CPD, CXD, CGD, med):
    S = {"已漲多門檻（探索段已漲250中位）": med}
    ok = CPD[CPD["缺"] == 0]
    for (part, sg), g in ok.groupby(["part", "段"]):
        k = f"{part}|{sg}"
        S[k] = {"筆數": int(len(g)), "未滿500日": int(g["未滿500日"].sum()), "已漲250平均": float(g["已漲250"].mean()), "已漲250中位": float(g["已漲250"].median()),
                "已漲120中位": float(g["已漲120"].median()), "已漲60中位": float(g["已漲60"].median()),
                "吃到幾成中位": float(g["吃到幾成"].median()), "吃到≤0比例": float((g["吃到幾成"] <= 0).mean()), "之後沒再創高比例": float(g["之後沒再創高"].mean()),
                "實際持有吃到幾成中位": float(g["實際持有吃到幾成"].median()), "持有報酬平均": float(g["持有報酬"].mean()),
                "吃到幾成中位（剔未滿500日）": float(g.loc[g["未滿500日"] == 0, "吃到幾成"].median())}
        for h, gg in g.groupby("半"):
            S[k][h] = {"筆數": int(len(gg)), "持有報酬平均": float(gg["持有報酬"].mean()), "持有報酬中位": float(gg["持有報酬"].median()),
                       "吃到幾成中位": float(gg["吃到幾成"].median()), "回落20比例": float(gg["回落20"].mean()), "回落30比例": float(gg["回落30"].mean())}
    ex = CXD[CXD["未出場"] == 0] if len(CXD) else CXD
    for (part, E_), g in ex.groupby(["part", "E"]):
        S[f"出場|{part}|{E_}"] = {"筆數": int(len(g)), "未出場": int((CXD[(CXD["part"] == part) & (CXD["E"] == E_)]["未出場"] == 1).sum()),
                                 "吃到幾成中位": float(g["吃到幾成"].median()), "躲掉多少中位": float(g["躲掉多少"].median()),
                                 "賣早了比例": float(g["賣早了"].mean()), "錯過的漲幅中位（賣早了者）": float(g.loc[g["賣早了"] == 1, "錯過的漲幅"].median()) if (g["賣早了"] == 1).any() else None,
                                 "賣在頂點附近比例": float(g["賣在頂點附近"].mean()), "平均持有天數": float(g["持有天數"].mean())}
    for part, g in CGD.groupby("part"):
        S[f"見頂|{part}"] = {"筆數": int(len(g)), "時間差中位_月（可用日）": float(g["時間差_月（可用日）"].median()),
                             "時間差中位_月（營收月底）": float(g["時間差_月（營收月底）"].median()), "股價先見頂比例": float((g["時間差_月（可用日）"] > 0).mean()),
                             "領先≥2月比例": float((g["時間差_月（可用日）"] >= 2).mean()),
                             "時間差中位_月（可用日；剔未滿500日）": float(g.loc[g["未滿500日"] == 0, "時間差_月（可用日）"].median()) if (g["未滿500日"] == 0).any() else None}
    return S


# ═════════════ 查核（P14；獨立重建，⛔ 不呼叫上面的 PIT／compute_ind／picks_at／sim_ind）═════════════
def ck_load(DATA):
    import csv
    pitseg = defaultdict(list)
    with open(os.path.join(DATA, "meta", "industry_hist", "industry_pit.csv"), encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pitseg[row["stock_id"]].append((row["start"] or "0000-00-00", row["end"] or "9999-12-31", row["industry"]))
    revd = {}; catd = defaultdict(dict); mkt = {}
    for fn in rev_files(DATA):
        with open(fn, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                k = (row["stock_id"], row["period"])

                def fl(v):
                    try:
                        return float(v)
                    except (TypeError, ValueError):
                        return float("nan")
                revd[k] = (fl(row["當月營收"]), fl(row["去年當月營收"]))
                c = row["產業別"] or ""
                old = catd[row["stock_id"]].get(row["period"])
                if old is None or (old in OLDNAMES and c not in OLDNAMES):
                    catd[row["stock_id"]][row["period"]] = c
    rmk = {}
    for fn in rev_files(DATA):
        mk_ = "tpex" if fn.endswith("_tpex.csv") else "twse"
        with open(fn, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rmk[(row["stock_id"], row["period"])] = row.get("market") or mk_
    kind = {}; rng_ = {}
    with open(os.path.join(DATA, "meta", "stocks.csv"), encoding="utf-8") as f:
        for row in csv.DictReader(f):
            kind[row["stock_id"]] = row["kind"]; rng_[row["stock_id"]] = (row["first_seen"], row["last_seen"])
    da = pickle.load(open(EOTC_DAILY, "rb"))
    dk = defaultdict(set)
    for s, d_, c_ in zip(da["stock_id"], da["date"], da["close"]):
        try:
            if float(c_) > 0:
                dk[s].add(d_[:7])
        except (TypeError, ValueError):
            pass
    return pitseg, revd, catd, kind, rng_, dk, rmk


def ck_listed(K_, s, dstr, M):
    _, _, _, _, rng_, dk, rmk = K_
    if dstr >= "2015-01-05":
        return s in rng_ and rng_[s][0] <= dstr <= rng_[s][1]
    ym = dstr[:7]; y, m = int(ym[:4]), int(ym[5:]); pm = f"{y - (m == 1):04d}-{(m - 2) % 12 + 1:02d}"
    if ym in dk.get(s, ()) or pm in dk.get(s, ()):
        return True
    if dstr < "2004-03-01":
        return True
    return dstr < "2007-07-01" and rmk.get((s, M)) == "tpex"


def ck_ind(K_, sid, dstr):
    pitseg, revd, catd = K_[:3]
    if sid in pitseg:
        sg = sorted(pitseg[sid])
        hit = [i for a, b, i in sg if a <= dstr <= b]
        if hit:
            return hit[0]
        if dstr > sg[-1][1]:
            return sg[-1][2]
        if dstr < sg[0][0]:
            return sg[0][2]
        return [i for a, b, i in sg if b < dstr][-1]
    if sid in catd:
        y, m, dd = int(dstr[:4]), int(dstr[5:7]), int(dstr[8:10])
        k = y * 12 + m - 1 - (1 if dd > 10 else 2)
        lim = f"{k // 12:04d}-{k % 12 + 1:02d}"
        ps = sorted(p for p in catd[sid] if p <= lim)
        if ps:
            c = catd[sid][ps[-1]]
            if c in FB_NONE:
                return None
            return FB_MAP.get(c, c)
    return None


def ck_A(K_, M, dstr, ver="pit"):
    """原始 csv 逐公司重算 ⇒ {產業: (A1, A2, A3, 公司數)}。"""
    pitseg, revd, catd, kind = K_[:4]
    sids = sorted({s for s, _ in revd if len(s) == 4 and s.isdigit() and s[0] != "0" and not s.startswith("91") and kind.get(s, "stock") == "stock"})
    mem = defaultdict(list)
    for s in sids:
        if not ck_listed(K_, s, dstr, M):
            continue
        i = ck_ind(K_, s, dstr)
        if i is not None and i not in EXCL:
            mem[i].append(s)

    def sh(m, k):
        t = int(m[:4]) * 12 + int(m[5:]) - 1 + k
        return f"{t // 12:04d}-{t % 12 + 1:02d}"

    def yy(ss, months):
        num = den = 0.0; c = 0
        for m in months:
            c = 0
            for s in ss:
                a, b = revd.get((s, m), (float("nan"), float("nan")))
                if a == a and b == b and a > 0 and b > 0:
                    num += a; den += b; c += 1
        return (num / den - 1 if den > 0 else float("nan")), c
    out = {}
    for i, ss in mem.items():
        a1, c = yy(ss, [sh(M, -2), sh(M, -1), M]); y12, _ = yy(ss, [sh(M, -k) for k in range(11, -1, -1)]); p3, _ = yy(ss, [sh(M, -5), sh(M, -4), sh(M, -3)])
        out[i] = (a1, a1 - y12, a1 - p3, c)
    return out


def ck_sim(C, K_, cfg, avail, pitday, t0, t1, mcap, eligf):
    """獨立逐日迴圈：選股（原始 csv 重建）、持股、交易、權益。"""
    P, dl = C["P"], C["dl"]; cal = C["cal"]; n = C["ncal"]
    SF = {}
    for s, v in P.items():
        b = np.flatnonzero(v["valid"])
        if len(b) and b[-1] < t1:
            SF[s] = int(b[-1])
    Acache = {}

    def AT(M):
        if M not in Acache:
            Acache[M] = ck_A(K_, M, pitday[M])
        return Acache[M]
    revd = K_[1]
    pos_list = sorted(avail)
    Mlast = lambda t: max((M for M, p in avail.items() if p <= t), key=lambda M: avail[M])
    mons = RMON[cfg["R"]]
    reb = sorted({t0} | {p for M, p in avail.items() if t0 < p <= t1 and int(M[5:]) in mons})
    E = cfg["E"]; X = EXX.get(E)
    eq = np.ones(n); cash = 1.0
    book = {}   # s -> dict(u, amt, ind, bt, bp)
    sellq = set(); held = {}; ban = {}; flag = set(); trades = []; hold_sets = {}
    av_rev = {p: M for M, p in avail.items()}
    for t in range(t0, t1 + 1):
        for s in list(book):
            if s in SF and t == SF[s] + 1:
                p_ = book.pop(s); cash += p_["u"] * P[s]["c"][t] - p_["amt"] * COST; sellq.discard(s); trades.append((t, s, "sf", P[s]["c"][t]))
        out_ = []
        if X is not None:
            out_ = sorted(i for i in flag if i in held)
        elif E == "E1" and t in av_rev:
            M = av_rev[t]; Mp = f"{(int(M[:4]) * 12 + int(M[5:]) - 2) // 12:04d}-{(int(M[:4]) * 12 + int(M[5:]) - 2) % 12 + 1:02d}"
            for i in sorted(held):
                r1, r0 = AT(M).get(i), AT(Mp).get(i)
                if r1 and r0 and r1[3] >= 0 and np.isfinite(r1[1]) and np.isfinite(r0[1]) and r1[1] < 0 and r0[1] > 0:
                    out_.append(i)
        flag = set()
        for i in out_:
            h = held.pop(i); bk = sorted(s for s, p_ in book.items() if p_["ind"] == i)
            sellq.update(bk); ban[i] = (E, h["I"], h["pk"], bk)
        newsel = None
        rk = []
        if t in reb:
            M = Mlast(t); TA = AT(M); A = cfg["A"]; ai = {"A1": 0, "A2": 1, "A3": 2}[A]
            rk = sorted([i for i, v in TA.items() if v[3] >= 5 and np.isfinite(v[ai])], key=lambda i: (-TA[i][ai], i))
        if t in reb and rk:
            ch = []
            for i in rk:
                if i in ban:
                    bE, bI, bpk, _ = ban[i]
                    still = (np.isfinite(TA[i][1]) and TA[i][1] < 0) if bE == "E1" else (bI <= (1 - EXX[bE]) * bpk)
                    if still:
                        continue
                    del ban[i]
                ch.append(i)
                if len(ch) == cfg["K"]:
                    break
            dstr = str(cal[t - 1].date())
            grp = defaultdict(list)
            for s in eligf(t):
                if s not in P:
                    continue
                i = ck_ind(K_, s, dstr)
                if i in ch:
                    v = mcap(s, t - 1)
                    if v is not None and v > 0:
                        grp[i].append((-v, s))
            newsel = []; dv = {}; si = {}
            for i in ch:
                o = [s for _, s in sorted(grp[i])]
                if cfg["S"] == "S3":
                    def hi(s):
                        cur = revd.get((s, M), (float("nan"),))[0]
                        pv = [revd.get((s, mshift(M, -k)), (float("nan"),))[0] for k in range(1, 25)]
                        return cur == cur and all(x == x for x in pv) and cur >= max(pv)
                    o = [s for s in o if hi(s)][:10]; nn = 10
                else:
                    o = o[:SN[cfg["S"]]]; nn = len(o)
                for s in o:
                    newsel.append(s); dv[s] = cfg["K"] * nn; si[s] = i
            sellq = (sellq | (set(book) - set(newsel))) - set(newsel)
            for i in list(held):
                if i not in ch:
                    held.pop(i)
            for i in ch:
                held.setdefault(i, {"I": 1.0, "pk": -np.inf})
            for s in newsel:
                if s in book:
                    book[s]["ind"] = si[s]
        for s in sorted(sellq):
            x = P[s]
            if x["trd"][t] and not x["dn_o"][t] and np.isfinite(x["o"][t]) and x["o"][t] > 0:
                px = x["o"][t]; kd = "open"
            elif (not x["trd"][t]) and s in dl and t > dl[s]["last"] and dl[s]["status"].startswith("delisted"):
                px = x["c"][t]; kd = "delist"
            else:
                continue
            p_ = book.pop(s); cash += p_["u"] * px - p_["amt"] * COST; sellq.discard(s); trades.append((t, s, kd, px))
        if newsel is not None:
            for s in [s for s in newsel if s not in book]:
                x = P[s]; o = x["o"][t]
                if not x["trd"][t] or not (np.isfinite(o) and o > 0) or x["up_o"][t]:
                    continue
                amt = min(eq[t - 1] / dv[s], cash)
                if amt <= 1e-12:
                    break
                cash -= amt; book[s] = {"u": amt / o, "amt": amt, "ind": si[s], "bt": t, "bp": o}; trades.append((t, s, "buy", o))
        eq[t] = cash + sum(p_["u"] * P[s]["c"][t] for s, p_ in book.items())
        if newsel is not None:
            hold_sets[t] = sorted(book)
        if X is not None:
            for i, h in held.items():
                rs = []
                for s, p_ in book.items():
                    if p_["ind"] != i:
                        continue
                    ref = p_["bp"] if p_["bt"] == t else P[s]["c"][t - 1]; ct = P[s]["c"][t]
                    if np.isfinite(ct) and np.isfinite(ref) and ref > 0:
                        rs.append(ct / ref - 1)
                if rs:
                    h["I"] *= 1 + float(np.mean(rs)); h["pk"] = max(h["pk"], h["I"])
                    if h["I"] <= (1 - X) * h["pk"]:
                        flag.add(i)
            for i in list(ban):
                bE, bI, bpk, bk = ban[i]
                rs = [P[s]["c"][t] / P[s]["c"][t - 1] - 1 for s in bk if np.isfinite(P[s]["c"][t]) and np.isfinite(P[s]["c"][t - 1]) and P[s]["c"][t - 1] > 0]
                if rs:
                    ban[i] = (bE, bI * (1 + float(np.mean(rs))), bpk, bk)
    return eq, trades, hold_sets


def check(a):
    T00 = time.time()
    META = json.load(open(os.path.join(OUT, "meta.json"), encoding="utf-8"))
    sha = setup(a, META["main"])                     # 查核用主程式同一個 main sha
    AT = pd.read_csv(os.path.join(OUT, "A_table.csv.gz"), float_precision="round_trip")
    _C["RANK"] = build_rank(pd.concat([AT, AT[AT["ver"] == "pit"].assign(ver="剔除2023")], ignore_index=True))
    _C["AV"] = {(v, M, i): {"A1": a1, "A2": a2, "A3": a3} for v, M, i, a1, a2, a3 in zip(AT["ver"], AT["M"], AT["產業"], AT["A1"], AT["A2"], AT["A3"])}
    K_ = ck_load(_C["DATA"])
    RES = {"讀法寫死": TIME, "main": sha}
    # ② 抽 2 個產業×月
    rng = np.random.default_rng(SEED_R)
    pool_ = AT[(AT["ver"] == "pit") & (AT["公司數"] >= 5) & (AT["M"] >= "2005-01")].reset_index(drop=True)
    pick = pool_.iloc[sorted(rng.choice(len(pool_), 2, replace=False))]
    out2 = []; nd2 = 0
    for _, r in pick.iterrows():
        mine = ck_A(K_, r["M"], str(_C["pitday"][r["M"]].date())).get(r["產業"])
        diff = {k: (mine[j] if mine else None, float(r[k])) for j, k in enumerate(("A1", "A2", "A3", "公司數"))}
        bad = [k for k, (x, y) in diff.items() if x is None or not (abs(x - y) <= 1e-12 * max(1, abs(y)))]
        nd2 += len(bad); out2.append({"月": r["M"], "產業": r["產業"], "獨立重算／主程式": diff, "不同": bad})
    RES["② A 值抽查"] = out2
    log(f"[查核 ②] {out2}")
    # ① 挑中格＋抽 1 格：獨立重建
    ck = META["挑格"]["挑中"]; CL = cells()
    other = CL[int(np.random.default_rng(SEED_R).integers(len(CL)))]
    if ckey(other) == ck:
        other = CL[(CL.index(other) + 1) % len(CL)]
    otherE = [c for c in CL if c["E"] != "E0"]
    otherE = otherE[int(np.random.default_rng([SEED_R, 1]).integers(len(otherE)))]
    targets = [dict(META["挑格"]["挑中參數"]), other, otherE]   # 第三格 2026-10-04 00:12 加：第一次查核抽到的另一格是 E0，出場臂沒驗到
    out1 = []; nd1 = 0
    for part, win, segs in (("main", MAIN_W, SEG), ("early", EARLY_A, {"早年": EARLY_A})):
        C = part_ctx(part, a.procs); attach_months(C)
        C["win"] = (SC.pos_of(C["cal"], win[0]), SC.pos_of(C["cal"], win[1])); C["segp"] = segpos(C, segs)
        _C[part] = C
        cal = C["cal"]; t0, t1 = C["win"]
        if part == "main":
            G1 = gate_g1(C); RES["③ 閘 G1"] = G1; nd1 += sum(not g["權益逐位元相同"] for g in G1)
        # 獨立可用日（第一個日期 ＞ 次月 10 日的交易日）與 PIT 日
        avail = {}; pitday = {}
        for M in _C["rev"].index:
            y, m = int(M[:4]), int(M[5:]); y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
            p = int(np.searchsorted(cal.values, np.datetime64(f"{y2:04d}-{m2:02d}-10"), side="right"))
            if 0 < p < len(cal) and cal[p].month == m2 and cal[p].year == y2:
                avail[M] = p; pitday[M] = str(cal[p - 1].date())
        # 獨立市值與面板
        if part == "main":
            import csv
            mcd = {}

            def mcap(s, t):
                if s not in mcd:
                    arr = np.full(len(cal), np.nan)
                    with open(os.path.join(C["data"], "stocks", f"{s}.csv"), encoding="utf-8") as f:
                        for row in csv.DictReader(f):
                            try:
                                v = float(row["close"]) * float(row["shares"])
                            except (TypeError, ValueError):
                                continue
                            p = cal.searchsorted(pd.Timestamp(row["date"]))
                            if p < len(cal) and cal[p] == pd.Timestamp(row["date"]) and v > 0:
                                arr[p] = v
                    last = np.nan
                    for k in range(len(arr)):
                        if np.isfinite(arr[k]):
                            last = arr[k]
                        arr[k] = last
                    mcd[s] = arr
                v = mcd[s][t]
                return float(v) if np.isfinite(v) else None
        else:
            da = pickle.load(open(EOTC_DAILY, "rb"))
            da = da[da["stock_id"].isin(set(C["P"]))]
            mcd = defaultdict(dict)
            for s, d_, c_, h_ in zip(da["stock_id"], da["date"], da["close"], da["shares"]):
                try:
                    v = float(c_) * float(h_)
                except (TypeError, ValueError):
                    continue
                if v > 0:
                    mcd[s][d_] = v

            def mcap(s, t):
                ds = str(cal[t].date()); best = None; bd = ""
                for d_, v in mcd.get(s, {}).items():
                    if d_ <= ds and d_ >= bd:
                        bd, best = d_, v
                return best
        pn = pd.read_csv(C["panel"], dtype=str, usecols=["measure_date", "stock_id", "eligible"])
        pn = pn[(pn["eligible"] == "True") & pn["stock_id"].isin(set(C["mk"]))]
        el = defaultdict(set)
        for d_, s in zip(pn["measure_date"], pn["stock_id"]):
            el[d_[:10]].add(s)

        def eligf(t):
            ym = str(cal[t].date())[:7]
            ds = sorted(d_ for d_ in el if d_[:7] == ym)
            return sorted(el[ds[-1]]) if ds else []
        for cfg in targets:
            res = sim_ind(C, t0, t1, dict(cfg, ver="pit", order="top", elig="W1"))
            eq2, tr2, hs2 = ck_sim(C, K_, cfg, avail, pitday, t0, t1, mcap, eligf)
            hs1 = {t: sorted(w) for t, w in res["snaps"].items()}
            tr1 = [(t, s, k, float(p)) for t, s, k, p in res["trades"]]; tr2 = [(t, s, k, float(p)) for t, s, k, p in tr2]
            rel = float(np.nanmax(np.abs(res["eq"][t0:t1 + 1] / eq2[t0:t1 + 1] - 1)))
            bad_h = [str(cal[t].date()) for t in sorted(set(hs1) | set(hs2)) if hs1.get(t) != hs2.get(t)]
            bad_t = len(set(tr1) ^ set(tr2))
            ok = (rel <= 1e-9) and not bad_h and bad_t == 0
            nd1 += (0 if ok else 1)
            out1.append({"段": part, "格": ckey(cfg), "換股日數": len(hs1), "交易筆數": len(tr1), "權益最大相對差": rel, "持股集合不同的換股日": bad_h[:10],
                         "交易不同筆數": bad_t, "通過": ok})
            log(f"[查核 ①] {out1[-1]}")
    RES["① 逐筆重算"] = out1
    RES["不同項數"] = nd1 + nd2; RES["通過"] = (nd1 + nd2) == 0; RES["秒"] = round(time.time() - T00)
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[查核] 不同 {RES['不同項數']}｜通過 {RES['通過']}")


def main():
    global LOGF
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=3); ap.add_argument("--reps", type=int, default=1000)
    ap.add_argument("--check", action="store_true"); ap.add_argument("--page", action="store_true"); ap.add_argument("--reuse-a", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    LOGF = os.path.join(OUT, "run_check.log" if a.check else ("run_page.log" if a.page else "run.log"))
    open(LOGF, "w").close()
    log(f"===== researchIndRev_prereg {'check' if a.check else ('page' if a.page else 'run')}｜讀法寫死 {TIME}｜停止交易強制出場：開 =====")
    if a.check:
        check(a)
    elif a.page:
        page()
    else:
        run(a)
        page()


def priors(META, TM, TE, CPD):
    """先驗 ①～⑧ 逐條對答（只讀已算好的檔）。"""
    CH = META["挑格"]["挑中參數"]; S = META["丙"]; out = []
    n2 = META["挑格"]["兩段都合格格數（全 216）"]
    out.append(("①", "兩段（確認＋早年）都合格的格 0 個", f"全 216 格中兩段都合格 {n2} 格（非退化 {META['挑格']['兩段都合格格數（非退化）']} 格）", "對" if n2 == 0 else "錯"))
    ok = CPD[(CPD["part"] == "main") & (CPD["缺"] == 0)]
    m2 = float(ok["已漲250"].mean())
    out.append(("②", "被挑中時產業指數距 250 日低點平均已漲 ＞ 30%", f"主段 {len(ok)} 筆平均 {m2:+.1%}（中位 {ok['已漲250'].median():+.1%}）", "對" if m2 > 0.30 else "錯"))
    m3 = float(ok["吃到幾成"].median())
    out.append(("③", "「吃到幾成」中位落在 30～60%", f"主段中位 {m3:.0%}", "對" if 0.30 <= m3 <= 0.60 else "錯"))
    hi = ok[ok["半"] == "已漲多"]["持有報酬"].mean(); lo = ok[ok["半"] == "已漲少"]["持有報酬"].mean()
    out.append(("④", "「已漲多」那半的持有報酬不比「已漲少」差", f"主段每期持有報酬平均：已漲多 {hi:+.1%}、已漲少 {lo:+.1%}", "對" if hi >= lo else "錯"))
    g = TM[(TM["A"] == CH["A"]) & (TM["K"] == CH["K"]) & (TM["R"] == CH["R"]) & (TM["E"] == CH["E"])].set_index("S")
    txt = []; ok5 = True
    for sg in ("探索", "確認"):
        v = g[f"{sg}_年化波動"]; d = g[f"{sg}_回落"]; c = g[f"{sg}_年化"]
        a_ = (v.idxmin() == "S2") and (d.idxmax() == "S2") and (c.idxmax() != "S2")
        ok5 &= a_
        txt.append(f"{sg}：波動最小 {v.idxmin()}、回落最淺 {d.idxmax()}、年化最高 {c.idxmax()}")
    out.append(("⑤", "S2 龍頭波動與回落最小，但年化不是三種挑股裡最高", "；".join(txt) + f"（同 {CH['A']}、K{CH['K']}、{CH['R']}、{CH['E']}）", "對" if ok5 else "錯"))
    gp = S.get("見頂|main", {})
    v6 = gp.get("時間差中位_月（可用日）")
    out.append(("⑥", "產業指數最高點早於營收 A1 最高點，中位領先 ≥ 2 個月", f"主段 {gp.get('筆數', 0)} 段持有：中位 {v6:+.1f} 月（正 ＝ 股價先見頂）" if v6 is not None else "—",
                "對" if (v6 is not None and v6 >= 2) else "錯"))
    e = {E_: S.get(f"出場|main|{E_}", {}) for E_ in ES}
    eat = {E_: e[E_].get("吃到幾成中位", np.nan) for E_ in ES}
    gk = TM[(TM["A"] == CH["A"]) & (TM["K"] == CH["K"]) & (TM["S"] == CH["S"]) & (TM["R"] == CH["R"])].set_index("E")
    cg = {E_: (gk.at[E_, "探索_年化"], gk.at[E_, "確認_年化"]) for E_ in ES}
    c7 = all(eat[E_] > eat["E0"] for E_ in ("E2", "E3")) and all(cg[E_][j] <= cg["E0"][j] for E_ in ("E2", "E3") for j in (0, 1))
    out.append(("⑦", "E2／E3「吃到幾成」中位高於 E0，但年化不贏 E0",
                "吃到幾成中位 " + "、".join(f"{E_} {eat[E_]:.0%}" for E_ in ES) + "；年化（探索／確認）" + "、".join(f"{E_} {cg[E_][0]:+.1%}／{cg[E_][1]:+.1%}" for E_ in ES), "對" if c7 else "錯"))
    se = {E_: e[E_].get("賣早了比例", np.nan) for E_ in ES}; dg = {E_: e[E_].get("躲掉多少中位", np.nan) for E_ in ES}
    c8 = all(se["E1"] <= se[x] for x in ES if x != "E1") and all(abs(dg["E1"]) <= abs(dg[x]) for x in ES if x != "E1")
    out.append(("⑧", "E1 的「賣早了」比例最低、「躲掉多少」最小",
                "賣早了 " + "、".join(f"{E_} {se[E_]:.0%}" for E_ in ES) + "；躲掉（出場後 250 日內最大跌幅中位）" + "、".join(f"{E_} {dg[E_]:+.0%}" for E_ in ES), "對" if c8 else "錯"))
    return out


def page():
    e = html.escape
    META = json.load(open(os.path.join(OUT, "meta.json"), encoding="utf-8"))
    TM = pd.read_csv(os.path.join(OUT, "cells_main.csv")); TE = pd.read_csv(os.path.join(OUT, "cells_early.csv"))
    CPD = pd.read_csv(os.path.join(OUT, "c_pairs.csv")); VAR = pd.read_csv(os.path.join(OUT, "variants.csv"))
    YR = pd.read_csv(os.path.join(OUT, "years.csv")); IC = pd.read_csv(os.path.join(OUT, "industry_counts.csv"))
    CY = pd.read_csv(os.path.join(OUT, "coverage_early.csv"), dtype={"年": str})
    CKp = os.path.join(OUT, "check.json"); CK = json.load(open(CKp, encoding="utf-8")) if os.path.exists(CKp) else None
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0]
    CSS += ("\ntd.l,th.l{text-align:left;white-space:normal}small{color:#666}.warn{border-left:4px solid #d64045;padding:6px 10px;background:#fff4f4}"
            ".ok{border-left:4px solid #2b6cb0;padding:8px 12px;background:#eef4fb}.big{font-size:1.05rem}li{margin:.35em 0}"
            "details{margin:.6em 0}summary{font-weight:600;cursor:pointer;padding:4px 0}")
    P1 = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:+.1f}%"
    PC = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:.0f}%"
    F2 = lambda v: "—" if v is None or not np.isfinite(v) else f"{v:.2f}"
    G = META["挑格"]; CH = G["挑中參數"]; Z = META["0050"]; DET = META["挑中格細項"]; CT = META["對照"]; S = META["丙"]
    RN = {"季": "每季", "半年": "每半年", "年": "每年"}
    SNm = {"S1": "產業內市值前 20 大", "S2": "產業內市值前 3 大（龍頭）", "S3": "產業內營收創 24 月新高者取市值前 10"}
    ANm = {"A1": "近 3 月營收年增最高", "A2": "近 3 月年增減近 12 月年增最大（短長差）", "A3": "近 3 月年增比三個月前升最多（動能）"}
    ENm = {"E0": "照換股日換", "E1": "營收轉減速就賣", "E2": "產業持股從高點回落 20% 就賣", "E3": "產業持股從高點回落 30% 就賣"}
    desc = f"{RN[CH['R']]}挑{ANm[CH['A']]}的 {CH['K']} 個產業，買{SNm[CH['S']]}，{ENm[CH['E']]}"
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>產業營收加速回測</title>", f"<style>{CSS}</style></head><body><main>", "<h1>產業營收加速回測（乙＋丙）</h1>"]
    fin_ = G["判定"]
    ex = G["探索"]; cf = G["確認"]; ea = G["早年"]
    rnd = CT["隨機"]
    H.append(f"<div class='ok big'><b>結論：判定【{e(fin_)}】。</b>216 格在 2017～2021 挑出最好的一格是「{e(desc)}」。"
             f"2022～2026-08 年化 {P1(cf['年化'])}、最大回落 {P1(cf['回落'])}（0050 {P1(Z['確認']['年化'])}／{P1(Z['確認']['回落'])}）⇒ {e(G['確認標籤'])}；"
             f"早年 2012-06～2014 年化 {P1(ea['年化'])}／{P1(ea['回落'])}（0050 {P1(Z['早年']['年化'])}／{P1(Z['早年']['回落'])}）⇒ {e(G['早年標籤'])}。"
             f"隨機挑同數目產業 1,000 次，確認段年化中位 {P1(rnd['確認']['中位'])}，比挑中格好的比例 {rnd['確認']['p_年化']:.0%}。</div>")
    mp = S.get("main|探索", {}); mc = S.get("main|確認", {})
    H.append("<div class='ok'><b>使用者問「是不是買到漲到一半」：</b>"
             f"被挑中時，產業指數距 250 日低點中位已漲 {P1(mp.get('已漲250中位'))}（探索段）、{P1(mc.get('已漲250中位'))}（確認段）；"
             f"之後還吃得到「起漲到頂」的中位 {PC(mp.get('吃到幾成中位'))}（探索）、{PC(mc.get('吃到幾成中位'))}（確認）；"
             f"照換股期實際抱的那段，吃到中位 {PC(mp.get('實際持有吃到幾成中位'))}（探索）、{PC(mc.get('實際持有吃到幾成中位'))}（確認）。"
             f"已漲多那半 vs 已漲少那半的每期持有報酬平均：探索 {P1(mp.get('已漲多', {}).get('持有報酬平均'))} vs {P1(mp.get('已漲少', {}).get('持有報酬平均'))}；"
             f"確認 {P1(mc.get('已漲多', {}).get('持有報酬平均'))} vs {P1(mc.get('已漲少', {}).get('持有報酬平均'))}。（描述，不計檢定數）</div>")
    if CK:
        H.append(f"<p class='note'>查核：{'通過' if CK['通過'] else '⛔ 不通過'}（不同 {CK['不同項數']} 項；抽格逐筆重算、抽 2 個產業×月重算 A、引擎閘）。讀法寫死 {e(META['讀法寫死'])}。</p>")
    # 一、判定表
    H.append("<h2>一、判定</h2><div class='wrap'><table><tr><th class='l'>項</th><th>探索<br><small>2017-03～2021</small></th><th>確認<br><small>2022～2026-08</small></th><th>早年<br><small>2012-06～2014</small></th></tr>")
    row = lambda nm, a_, b_, c_: H.append(f"<tr><td class='l'>{nm}</td><td>{a_}</td><td>{b_}</td><td>{c_}</td></tr>")
    fm = lambda d: f"{P1(d['年化'])}<br><small>回落 {P1(d['回落'])}・比值 {F2(d['比值'])}</small>"
    row("<b>挑中格</b>", fm(ex), fm(cf) + f"<br><b>{e(G['確認標籤'])}</b>", fm(ea) + f"<br><b>{e(G['早年標籤'])}</b>")
    row("0050", fm(Z["探索"]), fm(Z["確認"]), fm(Z["早年"]))
    row("隨機挑產業 1,000 次（中位）", f"{P1(rnd['探索']['中位'])}<br><small>p10～p90 {P1(rnd['探索']['p10'])}～{P1(rnd['探索']['p90'])}</small>",
        f"{P1(rnd['確認']['中位'])}<br><small>p10～p90 {P1(rnd['確認']['p10'])}～{P1(rnd['確認']['p90'])}</small>",
        f"{P1(rnd['早年']['中位'])}<br><small>p10～p90 {P1(rnd['早年']['p10'])}～{P1(rnd['早年']['p90'])}</small>")
    row("隨機 ≥ 挑中格的比例（年化）", PC(rnd["探索"]["p_年化"]), PC(rnd["確認"]["p_年化"]), PC(rnd["早年"]["p_年化"]))
    for nm in ("反向臂", "全產業等權"):
        row(nm + ("（A 最低）" if nm == "反向臂" else ""), fm(CT[nm]["探索"]), fm(CT[nm]["確認"]), fm(CT[nm]["早年"]))
    y = CT["營量v1_T1"]
    row("營量 v1（T1）", fm(y["探索"]), fm(y["確認"]), fm(y["早年"]) + "<br><small>窗 2012-06-04～2014-12-31</small>")
    H.append("</table></div>")
    H.append(f"<p class='note'>挑法：探索段先排除退化格（平均持股 ＜ 3 或現金 ＞ 30%，{G['退化格數']} 格），剩 {G['非退化']} 格；過判準（年化 ＞ 0050 且 年化÷|回落| ≥ 0050）的有 {G['探索過判準格數']} 格"
             f"{'，取比值最高' if G['探索過判準格數'] else '，都沒過 ⇒ 取比值最高'}。判定取確認段與早年段較嚴者。"
             f"全 216 格：確認段合格 {G['確認段合格格數']} 格、早年段合格 {G['早年段合格格數']} 格、兩段都合格 {G['兩段都合格格數（全 216）']} 格。</p>")
    H.append("<p class='warn'>⚠ 早年段：W1 母體要個股法人資料，2012-06 以前沒有 ⇒ 2005-01～2012-05 <b>不可判定</b>，早年只用 2012-06～2014-12（只上市）判。"
             "⚠ 存活者偏差：歷史產業別對已下市公司只有公告段，其餘用當時月營收彙總表的類別補（見第六節）。</p>")
    # 二、先驗
    H.append("<h2>二、先驗對答</h2><div class='wrap'><table><tr><th>#</th><th class='l'>先驗</th><th class='l'>結果</th><th>對錯</th></tr>")
    for k, pr, rs, ok in priors(META, TM, TE, CPD):
        H.append(f"<tr><td>{k}</td><td class='l'>{e(pr)}</td><td class='l'>{e(rs)}</td><td><b>{ok}</b></td></tr>")
    H.append("</table></div>")
    # 三、必報
    H.append("<h2>三、挑中格必報</h2><div class='wrap'><table><tr><th class='l'>段</th><th>平均持股</th><th>現金</th><th>每年換手</th><th>成本／年</th><th>0050 重疊率</th><th>年化波動</th></tr>")
    for sg in ("探索", "確認", "早年"):
        d = DET[sg]
        H.append(f"<tr><td class='l'>{sg}</td><td>{d['平均持股']:.1f}</td><td>{PC(d['現金比例'])}</td><td>{d['每年換手']:.2f} 倍</td><td>{d['成本／年'] * 100:.2f}%</td>"
                 f"<td>{PC(d['0050重疊率'])}</td><td>{PC(d['年化波動'])}</td></tr>")
    H.append("</table></div><p class='note'>換手 ＝ 一年買進金額 ÷ 平均資產；0050 重疊率用「上市普通股市值前 50、市值權重」當 0050 代理（不是官方成分），換股日收盤後算。</p>")
    H.append("<h3>各年報酬</h3><div class='wrap'><table><tr><th>年</th><th>挑中格</th><th>0050</th></tr>")
    for _, r in YR.iterrows():
        H.append(f"<tr><td>{r['年']}{'<small>（早年段）</small>' if r['段'] == 'early' else ''}</td><td>{P1(r['挑中格'])}</td><td>{P1(r['0050'])}</td></tr>")
    H.append("</table></div><p class='note'>首年、末年是不滿一年的窗內報酬。</p>")
    H.append("<h3>挑中產業與次數（看是不是一直挑同一個）</h3><div class='wrap'><table><tr><th class='l'>段</th><th class='l'>產業（次數）</th></tr>")
    for sg, g in IC.groupby("段", sort=False):
        H.append(f"<tr><td class='l'>{e(sg)}</td><td class='l'>{'、'.join(f'{e(x)}（{n}）' for x, n in zip(g['產業'], g['次數']))}</td></tr>")
    H.append("</table></div><p class='note'>逐次名單與持股見 chosen_picks.csv。</p>")
    H.append("<h3>現實版與其他版本（描述）</h3><div class='wrap'><table><tr><th class='l'>版本</th><th class='l'>段</th><th>年化</th><th>回落</th><th>0050</th><th>標籤</th></tr>")
    for _, r in VAR.iterrows():
        H.append(f"<tr><td class='l'>{e(r['版本'])}</td><td class='l'>{e(r['段'])}</td><td>{P1(r['年化'])}</td><td>{P1(r['回落'])}</td>"
                 f"<td>{P1(r['0050年化'])}／{P1(r['0050回落'])}</td><td>{e(str(r['標籤']))}</td></tr>")
    H.append("</table></div><p class='note'>現實版 ＝ 每邊多 0.3% 成本＋50 萬資金的衝擊成本＋用當日均價成交（開盤漲停買不到、跌停賣不掉本來就有）。"
             "早年母體放寬 ＝ 2012-06 以前沒有 W1，改用流動性＋K 棒數兩條（去掉法人），只描述、不判。</p>")
    # 四、丙
    H.append("<h2>四、吃到起漲到頂幾成（丙，描述）</h2><div class='wrap'><table><tr><th class='l'>段</th><th>筆數</th><th>已漲<br><small>250 日中位</small></th><th>吃到幾成<br><small>中位</small></th>"
             "<th>之後沒再創高</th><th>實際持有<br><small>吃到幾成中位</small></th><th>已漲多<br><small>每期報酬</small></th><th>已漲少<br><small>每期報酬</small></th></tr>")
    for k in ("main|探索", "main|確認", "early|早年"):
        d = S.get(k)
        if not d:
            continue
        H.append(f"<tr><td class='l'>{k.split('|')[1]}</td><td>{d['筆數']}</td><td>{P1(d['已漲250中位'])}</td><td>{PC(d['吃到幾成中位'])}</td><td>{PC(d['之後沒再創高比例'])}</td>"
                 f"<td>{PC(d['實際持有吃到幾成中位'])}</td><td>{P1(d.get('已漲多', {}).get('持有報酬平均'))}<br><small>回落 30% {PC(d.get('已漲多', {}).get('回落30比例'))}</small></td>"
                 f"<td>{P1(d.get('已漲少', {}).get('持有報酬平均'))}<br><small>回落 30% {PC(d.get('已漲少', {}).get('回落30比例'))}</small></td></tr>")
    H.append(f"</table></div><p class='note'>產業指數 ＝ 產業內 W1 成員等權（早年用流動性＋K 棒數）。吃到幾成 ＝（訊號 → 之後 500 日最高）÷（前 250 日最低 → 那個最高），對數報酬；"
             f"已漲多／少以探索段中位 {P1(S['已漲多門檻（探索段已漲250中位）'])} 切。早年段資料只到 2014-12，「之後 500 日」多半不滿。</p>")
    H.append("<h3>何時抽身（出場面）</h3><div class='wrap'><table><tr><th class='l'>出場</th><th>筆數</th><th>吃到幾成<br><small>中位</small></th><th>躲掉多少<br><small>中位</small></th>"
             "<th>賣早了</th><th>賣在頂點附近</th><th>平均持有<br><small>交易日</small></th></tr>")
    for E_ in ES:
        d = S.get(f"出場|main|{E_}")
        if d:
            H.append(f"<tr><td class='l'>{E_} {ENm[E_]}</td><td>{d['筆數']}</td><td>{PC(d['吃到幾成中位'])}</td><td>{P1(d['躲掉多少中位'])}</td><td>{PC(d['賣早了比例'])}</td>"
                     f"<td>{PC(d['賣在頂點附近比例'])}</td><td>{d['平均持有天數']:.0f}</td></tr>")
    gk = TM[(TM["A"] == CH["A"]) & (TM["K"] == CH["K"]) & (TM["S"] == CH["S"]) & (TM["R"] == CH["R"])].set_index("E")
    nx = "、".join(f"{E_} {int(gk.at[E_, '探索_E出場次數'] + gk.at[E_, '確認_E出場次數'])} 次" for E_ in ("E1", "E2", "E3"))
    H.append(f"</table></div><p class='note'>同挑中格的 A、K、S、R 下，主段真正提前賣出的次數：{nx}。觸發少的臂與 E0 幾乎相同。出場臂整體比較見第五節。</p>")
    gp = S.get("見頂|main", {})
    if gp:
        v_ = gp['時間差中位_月（可用日）']
        H.append(f"<p class='lead'><b>股價先見頂？</b>主段 {gp['筆數']} 段持有：營收 A1 最高點（可用日）減產業指數最高點，中位 {v_:+.1f} 個月"
                 f"（以營收月月底算 {gp['時間差中位_月（營收月底）']:+.1f}；正 ＝ 股價先見頂）⇒ {'股價多半先見頂' if v_ > 0 else '多半是營收先到頂、股價後到頂'}；"
                 f"股價先見頂的比例 {PC(gp['股價先見頂比例'])}，股價領先 ≥ 2 個月 {PC(gp['領先≥2月比例'])}。</p>")
    # 五、E 臂
    H.append("<h2>五、出場臂對 E0（同 A×K×S×R，216 格裡 54 組）</h2><div class='wrap'><table><tr><th class='l'>段｜臂</th><th>年化差中位</th><th>年化贏 E0 的組</th><th>回落差中位</th></tr>")
    for k, d in META["E臂比較摘要"].items():
        H.append(f"<tr><td class='l'>{e(k)}</td><td>{P1(d['年化差中位'])}</td><td>{PC(d['年化差>0比例'])}</td><td>{P1(d['回落差中位'])}</td></tr>")
    H.append("</table></div><p class='note'>回落差 ＞ 0 ＝ 回落比 E0 淺。逐組見 e_compare.csv。</p>")
    # 六、216 格
    H.append("<h2>六、216 格（探索段比值前 30）</h2><details><summary>展開</summary><div class='wrap'><table><tr><th class='l'>格</th><th>探索</th><th>確認</th><th>早年</th><th>持股／現金</th></tr>")
    for _, r in TM.sort_values("探索_比值", ascending=False).head(30).iterrows():
        H.append(f"<tr><td class='l'>{e(r['key'])}{' ⭐' if r['key'] == G['挑中'] else ''}{'<br><small>退化</small>' if r['退化'] else ''}</td>"
                 f"<td>{P1(r['探索_年化'])}<br><small>{P1(r['探索_回落'])}・{F2(r['探索_比值'])}</small></td><td>{P1(r['確認_年化'])}<br><small>{P1(r['確認_回落'])}・{e(str(r['確認_標籤']))}</small></td>"
                 f"<td>{P1(r['早年_年化'])}<br><small>{P1(r['早年_回落'])}・{e(str(r['早年_標籤']))}</small></td><td>{r['探索_平均持股']:.1f}<br><small>{PC(r['探索_現金比例'])}</small></td></tr>")
    H.append("</table></div></details><p class='note'>全表 cells_main.csv、cells_early.csv。</p>")
    # 七、資料與讀法
    H.append("<h2>七、資料與執行者補的讀法</h2>")
    H.append("<h3>早年月營收覆蓋率</h3><div class='wrap'><table><tr><th>年</th><th>上市</th><th>上櫃</th></tr>")
    for yv, g in CY.groupby("年"):
        d = {r["市場"]: r for _, r in g.iterrows()}
        cell = lambda m: (f"{PC(d[m]['覆蓋率'])}<br><small>{d[m]['有營收年增家數']:.0f}／{d[m]['有日K家數']:.0f}{'・不可判定' if d[m]['判讀'] == '不可判定' else ''}</small>" if m in d else "—<br><small>無日 K</small>")
        H.append(f"<tr><td>{yv}</td><td>{cell('twse')}</td><td>{cell('tpex')}</td></tr>")
    H.append("</table></div>")
    src = META.get("PIT 來源計數（代號×月）", {})
    H.append("<ul class='note'>"
             f"<li>產業別來源（主表，所有代號×月）：{e(json.dumps(src, ensure_ascii=False))}</li>"
             "<li>★ 已下市、歷史產業別沒有的公司 ⇒ 用當時月營收彙總表的類別（名稱對齊），⛔ 不剔除。</li>"
             "<li>★ 產業營收只算「當時已上市櫃」的公司（月營收檔裡有當時還沒上市的公司，2026-10-03 23:48 開跑前改）。</li>"
             "<li>★ 窗首即建倉；E1～E3 出場條件仍成立的產業跳過、由下一名遞補；E2／E3「已不成立」＝ 出場那批股票的指數回到出場時高點的 (1−X) 以上。</li>"
             "<li>★ S1「不足 20 全買」＝ 產業那份由實際檔數平分；S3 不足剩現金。</li>"
             "<li>★ 現實版 C3 不另加（本簿本來就開盤漲停買不到、跌停賣不掉）。</li>"
             "<li>★ 0050 重疊率用市值前 50 代理；★ 早年覆蓋率門檻 90%。</li>"
             f"<li>{e(json.dumps(META.get('S3跨2013-01訊號（早年挑中格的挑中產業、S3 名單）', {}), ensure_ascii=False))}（S3 創 24 月新高跨 IFRS 換軌，照實標）</li>"
             "<li>引擎：換股簿（researchScore.sim_book 同一套成交與成本，閘 G1 逐位元）、停止交易強制出場開、成本來回 0.585%。</li></ul>")
    H.append("</main></body></html>")
    open(os.path.join(OUT, "產業營收加速回測.html"), "w", encoding="utf-8").write("\n".join(H))
    log("[網頁] 完成")


if __name__ == "__main__":
    main()
