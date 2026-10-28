# -*- coding: utf-8 -*-
"""美股合理價機械版——頻率表（⛔ 不算任何報酬）。

登錄：產業 seq63（pw1 sha ab44c6850399ff57）「長期投資追蹤看板合理價算法」美股機械版，規則照第二節寫死。
發號：裁定 seq480 §一（N_單筆 +1：可買−偏貴 1 年；N_組合 +1：對大盤兩格；3 年只描述）。
       ⇒ 先交【頻率表＋全部描述欄乾跑】、⛔ 不附報酬；核後正式跑。
資料：私有庫 us-stock-data commit 89d9f8550（資料庫 fundamentals 第二輪缺口修補，2026-10-27 19:02；裁定 seq481 §二換版）。
       讀 ~/usdata/89d9f8550（`git archive 89d9f8550` 出來的唯讀快照，.commit 記完整 sha；開跑先驗）。
       〔沿革：seq480 頻率表原用 b7572463c（2026-10-27 01:04）；舊版輸出留在 resultsUSFairValue/freq_b7572463/（可重現：
         US_FV_DATA_ROOT=~/usdata/b7572463c 並把 DATA_COMMIT 改回）；兩版差異見 resultsUSFairValue/freq/freq_diff_b7572463.json〕
私有：repo 的 resultsUSFairValue/freq/ 只放判定、彙總、筆數；逐檔明細只寫 ~/us_work/fairvalue/（repo 外）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSFairValue_freq

══════════ 裁定 seq480 §一 三個空白（看數字前寫死）══════════
 ①（EPS 補值）單季稀釋 EPS「只有累計」＝ 資料庫 derived=2（全年−9 個月近似）的列、或「留空」＝ 沒有列
    ⇒ 改用「單季淨利 ÷ 該季加權稀釋股數」（兩者都要 first_filed < 評估日）；derived=0/1（公司自報單季）照用。
    ★15 淨利÷股數補不出、但有 derived=2 列 ⇒ 用 derived=2 值（「只有累計」本身有值，不算「兩者都缺」）；
        真的兩者都缺 ⇒ 該季不可算 ⇒ 用到該季的評估日該檔不可算（照報）。
        〔另一讀法（字面）：derived=2 一律不用，補不出即不可算；兩讀法的分組差異筆數照報（literal 重算，只報筆數）〕。
 ②（同股數基礎）採【把歷史每股值依之後的分割調成同基礎】：
    每股值（EPS、每股股利）÷ Π（分割日 > 該值基礎日 的分割比）；股數 × 同一乘積；
    基礎日：EPS／股利／加權股數 ＝ first_filed（SEC 申報會把申報前生效的分割追溯重編）；封面流通股數 ＝ as_of_date。
    價格：Yahoo close 已調到檔尾（＝同一基礎）直接用；Tiingo close 是原始價 ⇒ ÷ Π（分割日 > 當日 的 splitFactor）。
    分割事件：該評估日 panel src 那個價格檔的事件（Yahoo：data/events_yahoo/<檔>.csv 的 split；Tiingo：data/prices/<檔>.csv
    的 splitFactor≠1）。⛔ 不直接相除。市值（封面股數 × 收盤）同理。
 ③ shares_outstanding 用 filed < 評估日 的最新一份申報（PIT）：核。

══════════ ★ 執行者定（另一讀法寫在〔〕；看任何數字前寫死）══════════
 ★1 評估日＝每季末日曆日（3/31、6/30、9/30、12/31）【之前】最後一個交易日（字面「前一個交易日」，嚴格早於季末日）。
     〔另一讀法：≤ 季末日的最後一個交易日〕。本益比歷史的「季末收盤」點用同一個日期規則。
 ★2「本益比歷史滿 3 年的第一個季末」：價格檔最早 2015-12-01 ⇒ 第一個本益比點 2015-12-30；
     第一個評估日 ＝ 第一個與 2015-12-30 相距 ≥ 3 個日曆年的評估日（＝2019-03-28）；到 2025-09-30 為止（最後 2025-09-29）。
     〔另一讀法：滿 12 個季點即可 ⇒ 2018-12-28 起〕。
 ★3 個股「最少 3 年」：評估日前 10 年內（含評估日當天的點）正本益比點，最早一點距評估日 ≥ 3 個日曆年；不滿 ⇒ pe_T 不可算。
     本益比點的價格用【評估日 panel src 那個價格檔】的整段歷史（含入指數前），⛔ 不只用 panel 暖身段。
 ★4 財年：淨利（net_income）列中 first_form 為 10-K* 的季 ＝ 第四季；財年 ＝ 第四季＋往前 3 個相連的季
     （相鄰季 period_start ≈ 前季 period_end＋1 日，±7 日；四季合計跨 ≈1 年，±14 日）。
     「最近 5 個完整財年」＝ 評估日前四季淨利都已申報的最新財年 e*，與 e* 往前 1～4 年（第四季 period_end 在 e*−k 年 ±20 日）。
     年度值 ＝ 4 個單季相加（每股值先各自調同基礎再相加）；權益 ＝ 第四季 period_end（±5 日）那天的時點值。
 ★5 門檻有缺值時：結果與缺值怎麼填都一樣才判（過／不過），否則記「不可算」；不可算 ⇒ 不算過門檻（不進任何組），照報筆數。
     ①ROE：已知 ≥15% 年數 ≥4 ⇒ 過；已知 ≥15% ＋缺 < 4 ⇒ 不過；權益 ≤ 0 的年算「未達 15%」。
     ②虧損：年度淨利 < 0 且年度營業利益 ≤ 0（或營業利益缺）⇒ 虧損年；淨利<0 而營業利益缺 ⇒ 該年不可判 ⇒ ②不可算（除非另有已知虧損年）。
     ③EPS 4 段年複合：起點（e*−4 年）與終點（e*）年度 EPS 都要有；起點 ≤ 0 ⇒ 不過；終點 ≤ 0 ⇒ 不過；(終/起)^(1/4)−1 ≥ 12%。
     ④營業現金流 5 年合計 ÷ 淨利 5 年合計 ≥ 0.8：20 季現金流與淨利都要有；淨利合計 ≤ 0 ⇒ 不過。
 ★6 淨利口徑：用資料庫 net_income 主序列（NetIncomeLoss，缺季時 ProfitLoss），⛔ 不另篩；ProfitLoss 季用到幾筆照報。
     〔另一讀法：只收 tag==NetIncomeLoss〕。
 ★7 E0：評估日前已申報的最新一季（淨利或 EPS 有列者）往前共 4 個相連季的單季稀釋 EPS（照 ① 補）相加；任一季不可算 ⇒ E0 不可算。
     歷史本益比點的「當時可得近四季 EPS」同一函式、以該點日期為準。
 ★8 配息率：與 E0 同 4 季的每股股利（調同基礎）相加 ÷ E0，夾 0～1；4 季都沒有股利列 ⇒ 記 0（照報）；部分季缺 ⇒ 缺的季記 0（照報）。
 ★16 權益：該年末 equity（StockholdersEquity）沒有列 ⇒ 用 equity_incl_nci（含非控制權益）補（照報年數）；
     JNJ、PG、CAT、UNH、V 等只申報含非控制權益的總額標籤。〔另一讀法：只用 equity，缺即不可算；差異筆數照報〕
 ★17 資料過舊：最新可用財年 e* 早於評估日 456 日以上（＝至少一整個財年的資料缺）⇒ 四條都不可算；
     E0 的最新一季早於評估日（或本益比點日）200 日以上 ⇒ 不可算／該點略過。
 ★18 同一季兩列（period_end 差幾天、較晚那份是重申報）⇒ 取評估日前最早申報的那列；財年串季時多列取最接近者。
     ★4 的季對季比對一律 ±5 日。
 ★9 市值：封面股數取最新一份申報（filed < 評估日）；同一份申報多個 as_of_date 取最晚；沒有類別維度的列優先，
     沒有就把該份申報各普通股類別（share_class 含 Common／Capital，排除優先股、存託、債券、子公司等法人維度）相加 × 本檔收盤。
     沒有股數 ⇒ 市值不可算 ⇒ 不進母體（照報）。
 ★10 分割事件早於價格檔起點（2015-12-01）的：資料庫事件檔沒有 ⇒ 由 SEC 加權稀釋股數的重編推得
     （相鄰兩份申報的股數跳 j 倍、且較早申報的季之後被重編成 ≈ j 倍〔latest_value／value，只用來偵測分割、⛔ 不當數值用〕；
     比值吸附到 a/b（a,b ≤ 20，或 1:N、N:1 至 100，誤差 ≤ 2%），分割日記為新基礎第一份申報的 first_filed）；只收「跳點前一份申報早於價格檔起點」的。
     跳點只看 derived=0 的單季股數；重編比與跳點差 ≤ 15%；兩份申報之間若有已在新基礎的申報（含 derived=2），分割日取它。
     驗證：同一偵測法套在 2016 起，對事件檔的召回率與精確率照報（check 檔）。
 ★11 單位明顯錯的加權股數（< 1,000,000 股）當缺值（例 A 2008-11 季報 352）；照報筆數。
 ★12 IR 2020-03-02 前在指數的是 Ingersoll-Rand plc（今 TT），但 IR 的財報是新 Ingersoll Rand（原 Gardner Denver）的 CIK
     ⇒ 那段財報對不上公司 ⇒ 不可算（照報）。一般化：renames_manual 有 until 的 old 代號在 until 之前一律如此。
     〔沿革 2026-10-28 裁定 seq481：資料 89d9f8550 的 cik_map 加了分段（seg_from／seg_to）⇒ 有分段的代號改走 ★19（依評估日挑 CIK），
       ★12 只剩「renames_manual 有 until、但 cik_map 沒有分段」的代號才適用（89d9f8550 上 0 檔；IR 改由 ★19 處理）〕
 ★13 母體「in_index=1」＝ panel 那天有列且 in_index=1；名冊在指數但 panel 那天沒有列（整段缺價 35 檔、部分缺段）⇒
     沒有收盤、市值與倍數都不可算 ⇒ 進不了任何組；照報每評估日筆數（⇒ −100% 規則實際觸發 0 筆，照報）。
 ★14 「過門檻全部」＝ 四條全過且合理價可算（含 E0 ≤ 0 歸偏貴者）；全過但合理價不可算（E0 或 pe_T 不可算）另報。

══════════ 裁定 seq481（2026-10-28）換資料 89d9f8550 後新增（看任何報酬前寫死）══════════
 ★15、★16 照寫採用（裁定 seq481 §一）；兩讀法差異筆數照報不變。
 ★19 依評估日挑 CIK：cik_map.csv 同代號多列（seg_from／seg_to，迄＝第一個不適用的日子）的代號（IR、DD、BHGE、FTI），
     評估日 d 落在哪一段（seg_from ≤ d < seg_to，空白＝不設限）就只用該段 CIK（＋cik_predecessor.csv 中 cik_now＝該 CIK、
     verdict＝ok 的前身 CIK）的列：季財報（全部欄位）、封面股數（★9）、★10 分割偵測都照這個 CIK 篩；
     本益比歷史點也用評估日那一段的 CIK（＝評估日那家公司的財報，配評估日 panel src 那個價格檔）。
     例：IR 評估日 < 2020-03-02 ⇒ 0001466258（Ingersoll-Rand plc，今 TT；panel src＝yahoo:TT）；≥ 2020-03-02 ⇒ 0001699150。
     DD（< 2017-09-01 舊杜邦 0000030554）、BHGE（< 2017-07-03 Baker Hughes Inc 0000808362）、FTI（< 2017-01-17 FMC Technologies
     0001135152）的評估日全在切換日之後 ⇒ 只用新 CIK（舊版是兩個 CIK 的列混在一起讀）。
     評估日不落在任何一段 ⇒ 財報對不上公司 ⇒ 不可算（保守；89d9f8550 上 0 筆）。沒有分段的代號照舊（不篩 CIK）。
 ★20 多類股 EPS／加權稀釋股數（quarterly_eps_diluted_class.csv／quarterly_diluted_shares_class.csv）：只用裁定 seq481 指定類別的 6 檔：
     V、STZ、GOOGL ⇒ CommonClassAMember；GOOG ⇒ CapitalClassCMember；
     HSY ⇒ CommonStockMember 與 HersheyCommonStockMember（2014–2019 的名稱；兩者同列一級；⛔ 永不用 Class B）；
     BRK.B ⇒ period_end ≥ 2017-01-01 用 EquivalentClassBMember；之前只有 Class A ⇒ 用 CommonClassAMember：EPS ÷ 1500、股數 × 1500
     （BRK 只申報基本 EPS〔tag＝EarningsPerShareBasic〕⇒ 照用、照報筆數）。
     讀法：同一季（±5 日）優先用指定類別的列；指定類別沒有該季 ⇒ 用主檔（沒有類別維度）的列；PIT 照舊（first_filed < 評估日，
     同級多列取最早申報）。⛔ 別的類別（GOOG 的 CommonClassCMember、V 的 Class B／C 等）一律不用。
     同一級兩個標籤同季都有值且相差 > 2%（HSY 2015-10-04 一季）⇒ 兩列都不用（當作沒有 EPS 列，照 ① 走淨利÷股數或不可算；照報）。
     類別檔裡其他檔（ADT、KKR、TSS、XOM、CVNA、BKR／BHGE、ERIE、GDDY 及 S&P 400 的）沒有裁定類別 ⇒ ⛔ 不讀類別檔（照舊用主檔）。
     ★10 分割偵測對這 6 檔改用同一套合併後的加權稀釋股數（指定類別優先，主檔只補指定類別沒有的季）。
 ★21 多類股的「淨利÷加權稀釋股數」補值（裁定①）：只有該檔「淨利 ÷ 指定類別股數」與公司自報指定類別 derived=0 EPS 同季比值的中位數
     與 1 相差 ≤ 2% 才做（＝該類股數就是 EPS 的分母）；否則該檔不做淨利÷股數補值（直接走 ★15：有 derived=2 列用之，否則不可算）。
     （89d9f8550：GOOGL、GOOG 比值中位 ≈ 2（A＋B 與 C 分開算股數）⇒ 不補；V、STZ、HSY、BRK.B 過）。只用財報、⛔ 不看報酬。
 ★22 淨利新備援標籤 NetIncomeLossAvailableToCommonStockholdersBasic、EPS 主檔的繼續營業部門備援標籤：照資料庫主序列直接用（★6 不另篩），
     用到的季數照報。A（Agilent）2017–2019 第四季 3 季留白 ⇒ 照既有不可算規則。DE 重複季已由資料庫去除，★18 照舊。
"""
from __future__ import annotations

import functools
import io
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

# ── 版本與路徑 ──────────────────────────────────────────────
DATA_COMMIT = "89d9f8550"             # 裁定 seq481 §二（舊：b7572463c／b7572463cd253596b1e64c419053c48cb4cda9fe）
DATA_COMMIT_FULL = "89d9f8550f6ea39b392087c22998cd298164a26c"
REG_SHA = "ab44c6850399ff57"        # 產業 seq63 pw1
RULING = "seq480"
RULING_DATA = "seq481"
ROOT = os.environ.get("US_FV_DATA_ROOT", os.path.expanduser("~/usdata/%s" % DATA_COMMIT))
HERE = os.path.dirname(os.path.abspath(__file__))
OUTD = os.path.join(HERE, "resultsUSFairValue", "freq")
PRIVD = os.path.expanduser("~/us_work/fairvalue")

# ── 登錄常數（seq63 §二）──────────────────────────────────────
MCAP_MIN = 10e9
ROE_MIN, ROE_YEARS_NEED = 0.15, 4
EPS_CAGR_MIN = 0.12
CFO_NI_MIN = 0.8
G_MULT, G_CAP = 0.8, 0.15
PE_CAP = 25.0
PE_LOOKBACK_YEARS, PE_MIN_YEARS = 10, 3
DISC = 0.10
CHEAP_MAX, NEAR_MAX = 1.00, 1.15
END_EVAL = pd.Timestamp("2025-09-30")
PRICE_START = pd.Timestamp("2015-12-01")
SHARES_MIN_SANE = 1_000_000          # ★11
GROUPS = ("可買", "接近", "偏貴")
ALT = {"eps_literal": False, "equity_strict": False}   # ★15／★16 另一讀法開關（只拿來報差異筆數）
STALE_FY_DAYS = 456                  # ★17
STALE_Q_DAYS = 200                   # ★17
_TTM = {}
# ★20 指定類別：ticker ⇒ [(share_class, period_end 起, period_end 迄（不含）, EPS 乘數)]；同一 list 內無日期限的列為同一級
CLASS_PICK = {
    "V": [("CommonClassAMember", None, None, 1.0)],
    "STZ": [("CommonClassAMember", None, None, 1.0)],
    "GOOGL": [("CommonClassAMember", None, None, 1.0)],
    "GOOG": [("CapitalClassCMember", None, None, 1.0)],
    "HSY": [("CommonStockMember", None, None, 1.0), ("HersheyCommonStockMember", None, None, 1.0)],
    "BRK.B": [("EquivalentClassBMember", pd.Timestamp("2017-01-01"), None, 1.0),
              ("CommonClassAMember", None, pd.Timestamp("2017-01-01"), 1.0 / 1500)],
}
CLASS_CONFLICT_TOL = 0.02            # ★20 同級兩標籤同季相差 > 2% ⇒ 兩列都不用
CLASS_FILL_TOL = 0.02                # ★21
PRIO_MAIN = 9                        # 主檔列在類別檔 6 檔裡的優先序（數字小者優先）
CLASS_FIELDS = {"eps_diluted": "quarterly_eps_diluted_class.csv", "diluted_shares": "quarterly_diluted_shares_class.csv"}
_CLASS_LOG = Counter()


def _p(*a):
    return os.path.join(ROOT, "data", *a)


def data_commit():
    return io.open(os.path.join(ROOT, ".commit"), encoding="utf-8").read().strip()


def assert_pinned():
    c = data_commit()
    if c != DATA_COMMIT_FULL:
        raise RuntimeError("資料 commit %s ≠ 寫死的 %s" % (c, DATA_COMMIT_FULL))
    return c


def jdump(obj, p):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, default=lambda x: x.item() if hasattr(x, "item") else str(x))


# ═════════════ 日曆與評估日 ═════════════
@functools.lru_cache(maxsize=None)
def calendar():
    d = pd.read_csv(_p("macro", "yahoo_GSPC.csv"), usecols=["date"], dtype=str)
    return pd.DatetimeIndex(pd.to_datetime(d["date"])).sort_values()


def qend_trading_day(qe):
    """★1：季末日曆日 qe 之前（嚴格早於）的最後一個交易日。"""
    cal = calendar()
    i = cal.searchsorted(pd.Timestamp(qe), side="left") - 1
    return cal[i] if i >= 0 else pd.NaT


@functools.lru_cache(maxsize=None)
def quarter_points():
    """價格檔起點之後的全部季末點（★1 規則）：2015-12-30 起到資料尾。"""
    out = []
    for y in range(2015, 2027):
        for m, dd in ((3, 31), (6, 30), (9, 30), (12, 31)):
            qe = pd.Timestamp(y, m, dd)
            t = qend_trading_day(qe)
            if pd.isna(t) or t < PRICE_START or qe > calendar()[-1]:
                continue
            out.append(t)
    return tuple(out)


@functools.lru_cache(maxsize=None)
def eval_dates():
    """★2：第一個與首個本益比點相距 ≥ 3 個日曆年的季末點起，到 2025-09-30 的季末點止。"""
    qp = quarter_points()
    first = qp[0]
    return tuple(t for t in qp if t >= first + pd.DateOffset(years=PE_MIN_YEARS) and t <= END_EVAL)


# ═════════════ 名冊、panel、價格 ═════════════
@functools.lru_cache(maxsize=None)
def universe_table():
    return pd.read_csv(_p("membership", "universe.csv"), dtype=str, keep_default_na=False)


def spans(ticker):
    row = universe_table().set_index("ticker").loc[ticker]
    out = []
    for sp in row["spans"].split(";"):
        a, b = sp.split("~")
        out.append((pd.Timestamp(a), pd.Timestamp(b) if b else None))
    return out


def member_by_spans(ticker, d):
    return any(a <= d and (b is None or d < b) for a, b in spans(ticker))


@functools.lru_cache(maxsize=None)
def panel(ticker):
    p = _p("panel", ticker + ".csv")
    if not os.path.exists(p):
        return None
    d = pd.read_csv(p, dtype={"date": str, "src": str})
    d["date"] = pd.to_datetime(d["date"])
    d["src"] = d["src"].str.rstrip("*")
    return d.set_index("date")


@functools.lru_cache(maxsize=None)
def renames_until():
    """★12：renames_manual 有 until 的 old 代號 ⇒ {old: until}。"""
    r = pd.read_csv(_p("membership", "renames_manual.csv"), dtype=str, keep_default_na=False)
    r = r[r["until"] != ""]
    return {o: pd.Timestamp(u) for o, u in zip(r["old"], r["until"])}


@functools.lru_cache(maxsize=None)
def cik_segments():
    """★19：cik_map.csv 同代號多列且有 seg_from／seg_to 的代號 ⇒ {ticker: [(cik, from|None, to|None)]}。"""
    c = pd.read_csv(_p("fundamentals", "cik_map.csv"), dtype=str, keep_default_na=False)
    if "seg_from" not in c.columns:
        return {}
    out = {}
    for t, g in c.groupby("ticker"):
        if len(g) < 2 or not ((g["seg_from"] != "") | (g["seg_to"] != "")).any():
            continue
        out[t] = [(ck, pd.Timestamp(a) if a else None, pd.Timestamp(b) if b else None)
                  for ck, a, b in zip(g["cik"], g["seg_from"], g["seg_to"])]
    return out


@functools.lru_cache(maxsize=None)
def cik_predecessors():
    """cik_now ⇒ set(pred_cik)（verdict＝ok）。"""
    p = _p("fundamentals", "cik_predecessor.csv")
    if not os.path.exists(p):
        return {}
    c = pd.read_csv(p, dtype=str, keep_default_na=False)
    c = c[(c["verdict"] == "ok") & (c["pred_cik"] != "")]
    out = defaultdict(set)
    for a, b in zip(c["cik_now"], c["pred_cik"]):
        out[a].add(b)
    return dict(out)


def cik_for(t, d):
    """★19：→ (cik 或 None［不分段＝不篩］, ok)。分段代號但 d 不落在任何一段 ⇒ (None, False)。"""
    segs = cik_segments().get(t)
    if not segs:
        return None, True
    d = pd.Timestamp(d)
    for ck, a, b in segs:
        if (a is None or a <= d) and (b is None or d < b):
            return ck, True
    return None, False


def cik_allowed(cik):
    return None if cik is None else frozenset({cik} | cik_predecessors().get(cik, set()))


@functools.lru_cache(maxsize=None)
def price_file(src):
    """src＝'yahoo:F'／'tiingo:F' ⇒ (close Series［同基礎＝檔尾股數］, 分割事件 list[(date, k)])。
    Yahoo：close 已調分割 ⇒ 直接用；事件 ＝ events_yahoo/F.csv 的 split（'a/b' ⇒ a/b）。
    Tiingo：close 原始 ⇒ ÷ Π（splitFactor，日期 > 當日）；事件 ＝ splitFactor≠1 的列。"""
    kind, f = src.split(":", 1)
    if kind == "yahoo":
        d = pd.read_csv(_p("prices_yahoo", f + ".csv"), usecols=["date", "close"], dtype={"date": str})
        s = pd.Series(d["close"].values, index=pd.to_datetime(d["date"])).astype(float)
        ev = []
        pe = _p("events_yahoo", f + ".csv")
        if os.path.exists(pe):
            e = pd.read_csv(pe, dtype=str)
            for dt, v in zip(e.loc[e["type"] == "split", "date"], e.loc[e["type"] == "split", "value"]):
                a, b = v.split("/")
                ev.append((pd.Timestamp(dt), float(a) / float(b)))
    elif kind == "tiingo":
        d = pd.read_csv(_p("prices", f + ".csv"), usecols=["date", "close", "splitFactor"], dtype={"date": str})
        idx = pd.to_datetime(d["date"])
        sf = d["splitFactor"].astype(float).values
        ev = [(t, k) for t, k in zip(idx, sf) if k != 1.0]
        # 收盤調到檔尾基礎：÷ Π（日期 > t 的 splitFactor）
        cum_after = np.ones(len(sf))
        acc = 1.0
        for i in range(len(sf) - 1, -1, -1):
            cum_after[i] = acc
            acc *= sf[i]
        s = pd.Series(d["close"].astype(float).values / cum_after, index=idx)
    else:
        raise ValueError(src)
    s = s[s.notna() & (s > 0)]
    return s.sort_index(), sorted(ev)


# ═════════════ 財報 ═════════════
FIELDS = ("net_income", "eps_diluted", "diluted_shares", "dps", "equity", "equity_incl_nci", "operating_income", "cfo")
BASE_COLS = ["ticker", "cik", "period_start", "period_end", "value", "first_filed", "first_form", "tag", "derived", "index"]


def _class_rows(name, extra_cols=()):
    """★20：類別檔中指定類別的列（已乘 EPS 乘數／股數除以乘數），加 prio 欄；同級衝突季兩列都丟。→ DataFrame。"""
    fn = CLASS_FIELDS[name]
    c = pd.read_csv(_p("fundamentals", fn), dtype={"ticker": str, "cik": str, "first_form": str, "tag": str,
                                                   "index": str, "share_class": str}, keep_default_na=False)
    keep = []
    for t, rules in CLASS_PICK.items():
        g = c[c["ticker"] == t]
        for prio, (cl, a, b, mult) in enumerate(rules):
            x = g[g["share_class"] == cl].copy()
            pe = pd.to_datetime(x["period_end"])
            m = pd.Series(True, index=x.index)
            if a is not None:
                m &= pe >= a
            if b is not None:
                m &= pe < b
            x = x[m]
            k = mult if name == "eps_diluted" else 1.0 / mult
            for col in ("value", "latest_value"):
                if col in x.columns:
                    x[col] = pd.to_numeric(x[col], errors="coerce") * k
            x["prio"] = 0 if (a is None and b is None) else prio     # 無日期限的同級（HSY 兩名稱）同 prio
            x["cls"] = cl if mult == 1.0 else cl + "/1500"
            keep.append(x)
    x = pd.concat(keep, ignore_index=True)
    for col in ("period_start", "period_end", "first_filed") + tuple(extra_cols):
        if col in x.columns:
            x[col] = pd.to_datetime(x[col], errors="coerce")
    x["derived"] = x["derived"].astype(int)
    # 同級衝突：同一檔、同 prio、不同 share_class、period_end ±5 日、值相差 > 2% ⇒ 兩邊該季的列都丟
    drop = set()
    for (t, pr), g in x.groupby(["ticker", "prio"]):
        if g["share_class"].nunique() < 2:
            continue
        cls = g["share_class"].unique()
        for i, ca in enumerate(cls):
            for cb in cls[i + 1:]:
                A, B = g[g["share_class"] == ca], g[g["share_class"] == cb]
                for ia, ra in A.iterrows():
                    nb = B[(B["period_end"] - ra["period_end"]).abs() <= pd.Timedelta(days=5)]
                    for ib, rb in nb.iterrows():
                        if rb["value"] != 0:
                            bad = abs(ra["value"] / rb["value"] - 1) > CLASS_CONFLICT_TOL
                        else:
                            bad = ra["value"] != 0
                        if bad:
                            drop |= {ia, ib}
                            _CLASS_LOG["conflict_%s_%s_%s" % (name, t, ra["period_end"].date())] = 1
    return x.drop(index=sorted(drop)).reset_index(drop=True)


def _merge_class(q, name, cols):
    """主檔 q（已篩 sp500）＋ ★20 指定類別列：6 檔的主檔列 prio＝PRIO_MAIN，類別列 prio 0/1；其餘檔 prio 0。"""
    q = q.copy()
    q["prio"] = np.where(q["ticker"].isin(list(CLASS_PICK)), PRIO_MAIN, 0)
    q["cls"] = ""
    if name not in CLASS_FIELDS:
        return q
    c = _class_rows(name, extra_cols=tuple(x for x in ("latest_filed",) if x in cols))
    c = c[[x for x in q.columns if x in c.columns]]
    return pd.concat([q, c], ignore_index=True)


@functools.lru_cache(maxsize=None)
def field(name):
    """→ {ticker: DataFrame（依 period_end 排序）}；只讀 value／first_filed（⛔ 不讀 latest_*）；只取 S&P 500（index≠sp400）。
    含 cik（★19 篩）、prio（★20：數字小者優先）、cls（用到的類別）欄。"""
    q = pd.read_csv(_p("fundamentals", "quarterly_%s.csv" % name), usecols=BASE_COLS,
                    dtype={"ticker": str, "cik": str, "first_form": str, "tag": str, "index": str})
    q = q[q["index"] != "sp400"].copy()
    for c in ("period_start", "period_end", "first_filed"):
        q[c] = pd.to_datetime(q[c])
    q["value"] = q["value"].astype(float)
    q["derived"] = q["derived"].astype(int)
    q = _merge_class(q, name, BASE_COLS)
    return {t: g.sort_values(["period_end", "prio"], kind="stable").reset_index(drop=True) for t, g in q.groupby("ticker")}


@functools.lru_cache(maxsize=None)
def split_detect_rows():
    """★10 專用：加權稀釋股數含 latest_value／latest_filed（只拿來偵測分割，⛔ 不當數值用）。
    ★20 的 6 檔：指定類別列＋主檔只補指定類別沒有的季（±5 日）。"""
    cols = ["ticker", "cik", "period_end", "value", "first_filed", "latest_value", "latest_filed", "derived", "index"]
    q = pd.read_csv(_p("fundamentals", "quarterly_diluted_shares.csv"), usecols=cols,
                    dtype={"ticker": str, "cik": str, "index": str})
    q = q[q["index"] != "sp400"].copy()
    for c in ("period_end", "first_filed", "latest_filed"):
        q[c] = pd.to_datetime(q[c])
    q = _merge_class(q, "diluted_shares", cols)
    out = {}
    for t, g in q.groupby("ticker"):
        if t in CLASS_PICK:
            cl = g[g["prio"] < PRIO_MAIN]
            mn = g[g["prio"] == PRIO_MAIN]
            if len(cl):
                pes = cl["period_end"].values.astype("datetime64[ns]").astype("int64")
                ok = [not (np.abs(pes - p.value) <= 5 * 86400 * 10 ** 9).any() for p in mn["period_end"]]
                mn = mn[np.array(ok, dtype=bool)]
            g = pd.concat([cl, mn])
        out[t] = g.sort_values(["first_filed", "period_end"]).reset_index(drop=True)
    return out


@functools.lru_cache(maxsize=None)
def class_fill_ok(t):
    """★21：→ (ok, 中位比值, 對數)。非 6 檔 ⇒ (True, None, 0)。比值 ＝ 淨利 ÷ 指定類別股數 ÷ 指定類別 derived=0 EPS（同季，各取 prio 最優、最早申報）。"""
    if t not in CLASS_PICK:
        return True, None, 0
    E, S, N = field("eps_diluted").get(t), field("diluted_shares").get(t), field("net_income").get(t)
    if E is None or S is None or N is None:
        return False, None, 0
    E = E[(E["prio"] < PRIO_MAIN)].sort_values(["prio", "first_filed"]).drop_duplicates("period_end")
    E = E[E["derived"] == 0]
    S = S[(S["prio"] < PRIO_MAIN)].sort_values(["prio", "first_filed"]).drop_duplicates("period_end")
    N = N.sort_values("first_filed").drop_duplicates("period_end")
    r = []
    for pe, ev in zip(E["period_end"], E["value"]):
        s = S[(S["period_end"] - pe).abs() <= pd.Timedelta(days=5)]
        n = N[(N["period_end"] - pe).abs() <= pd.Timedelta(days=5)]
        if len(s) and len(n) and ev and s["value"].iloc[0] > 0:
            r.append(n["value"].iloc[0] / s["value"].iloc[0] / ev)
    if not r:
        return False, None, 0
    med = float(np.median(r))
    return bool(abs(med - 1) <= CLASS_FILL_TOL), med, len(r)


@functools.lru_cache(maxsize=1)
def _snap_set():
    s = set()
    for a in range(1, 21):
        for b in range(1, 21):
            if a != b:
                s.add(a / b)
    for a in range(21, 101):                 # 大比值整數分割（例 CMG 50:1）
        s.add(float(a)); s.add(1.0 / a)
    return np.array(sorted(s))


def snap_ratio(k):
    c = _snap_set()
    i = int(np.argmin(np.abs(np.log(c / k))))
    return float(c[i]) if abs(math.log(c[i] / k)) <= 0.02 else None


@functools.lru_cache(maxsize=None)
def detect_splits(ticker, cik=None):
    """★10：→ list[(date＝新基礎第一份申報日, k, prev_filed)]（全期；呼叫端再依價格檔起點篩）。★19：cik≠None ⇒ 只用該 CIK（＋前身）的列。"""
    G = split_detect_rows().get(ticker)
    if G is not None and cik is not None:
        G = G[G["cik"].isin(cik_allowed(cik))].reset_index(drop=True)
    if G is None or len(G) < 2:
        return []
    # 跳點只看公司自報單季股數（derived=0）；derived=2 是推算值（例 NOW 2025Q4）會假跳
    g = G[G["derived"] == 0].reset_index(drop=True)
    v = g["value"].values.astype(float)
    ff = g["first_filed"].values
    Gv = G["value"].values.astype(float)
    Glv = G["latest_value"].values.astype(float)
    Gff = G["first_filed"].values
    Glf = G["latest_filed"].values
    out = []
    for i in range(1, len(g)):
        if ff[i] == ff[i - 1] or v[i] < SHARES_MIN_SANE or v[i - 1] < SHARES_MIN_SANE:
            continue
        j = v[i] / v[i - 1]
        if 0.7 <= j <= 1.4:
            continue
        # 早於跳點申報、之後（latest_filed ≥ ff[i]）被重編的列，重編比 q 與 j 相差 ≤ 15%（j 含兩季間股數增減；比值取 q）
        m = (Gff <= ff[i - 1]) & (Glf >= ff[i]) & (Gv >= SHARES_MIN_SANE)
        q = Glv[m] / Gv[m]
        q = q[np.isfinite(q) & (np.abs(np.log(q / j)) <= math.log(1.15))]
        if len(q) == 0:
            continue
        k = snap_ratio(float(np.median(q)))
        if k is None:
            continue
        # 分割日：(ff[i-1], ff[i]] 之間任何一份申報（含 derived=2）股數已在新基礎（對 v[i-1] 的比 ≈ k，±15%）⇒ 取最早者
        dte = ff[i]
        mid = (Gff > ff[i - 1]) & (Gff < ff[i]) & (Gv >= SHARES_MIN_SANE)
        for fv, vv in sorted(zip(Gff[mid], Gv[mid])):
            if abs(math.log(vv / v[i - 1] / k)) <= math.log(1.15):
                dte = fv
                break
        out.append((pd.Timestamp(dte), k, pd.Timestamp(ff[i - 1])))
    # 去重：同一跳點只記一次
    ded = []
    for e in out:
        if not ded or ded[-1][0] != e[0]:
            ded.append(e)
    return ded


@functools.lru_cache(maxsize=None)
def split_list(ticker, src, cik=None):
    """→ (每股值用的分割 list［事件檔＋★10 推得、早於價格檔起點的］, 推得的那幾筆)。"""
    s, ev = price_file(src)
    p0 = s.index[0] if len(s) else PRICE_START
    inf = [(d, k) for d, k, prev in detect_splits(ticker, cik) if prev < p0]
    # 與事件檔重複（±200 日內同比值）的不加
    inf2 = []
    for d, k in inf:
        dup = any(abs((d - de).days) <= 200 and abs(math.log(k / ke)) <= 0.03 for de, ke in ev)
        if not dup:
            inf2.append((d, k))
    return tuple(sorted(ev + inf2)), tuple(inf2)


def factor_after(splits, basis_date):
    """Π k（分割日 > basis_date）。"""
    f = 1.0
    for d, k in splits:
        if d > basis_date:
            f *= k
    return f


# ═════════════ 每檔財報結構 ═════════════
class Fund:
    """一檔的財報（全部 PIT 讀取都經 asof 過濾 first_filed < asof）。"""

    def __init__(self, t, cik=None):
        self.t = t
        self.cik = cik
        self.fill_ok = class_fill_ok(t)[0]          # ★21
        self.F = {}
        for f in FIELDS:
            g = field(f).get(t)
            if g is not None and cik is not None:   # ★19
                g = g[g["cik"].isin(cik_allowed(cik))].reset_index(drop=True)
                if not len(g):
                    g = None
            self.F[f] = g
        ni = self.F["net_income"]
        eps = self.F["eps_diluted"]
        pes = []
        for g in (ni, eps):
            if g is not None:
                pes.extend(g["period_end"].tolist())
        pes = sorted(set(pes))
        grid = []
        for pe in pes:                          # 同一季 ±5 日視為同一點
            if grid and (pe - grid[-1]).days <= 5:
                continue
            grid.append(pe)
        self.grid = grid
        self._pe = {f: (None if g is None else g["period_end"].values.astype("datetime64[ns]").astype("int64")) for f, g in self.F.items()}
        self._ff = {f: (None if g is None else g["first_filed"].values.astype("datetime64[ns]").astype("int64")) for f, g in self.F.items()}
        self._pr = {f: (None if g is None else g["prio"].values.astype(int)) for f, g in self.F.items()}

    def row(self, f, pe, asof, tol=5):
        """field f 在 period_end≈pe（±tol 日）、first_filed < asof 的列（Series）或 None。
        ★18 同一季有兩列（period_end 差幾天，例 DE 2016-10-30／10-31，較晚那份是重申報）⇒ 取 asof 前最早申報的那列。
        ★20 先比 prio（指定類別 0/1 ＜ 主檔 9），同 prio 再取最早申報；非 6 檔全是 0 ⇒ 與舊版相同。"""
        g = self.F[f]
        if g is None:
            return None
        m = (np.abs(self._pe[f] - pd.Timestamp(pe).value) <= tol * 86400 * 10 ** 9) & (self._ff[f] < pd.Timestamp(asof).value)
        k = np.flatnonzero(m)
        if len(k) == 0:
            return None
        o = np.lexsort((self._ff[f][k], self._pr[f][k]))
        i = int(k[o[0]])
        return g.iloc[i]

    # ── 單季 EPS（裁定①）──
    def eps_q(self, pe, asof, splits, literal=False):
        """→ (EPS 同基礎, kind) 或 (None, kind)。順序（裁定①＋★15）：
        direct（derived 0/1）→ 淨利÷加權稀釋股數（d2_fill：原列 derived=2；miss_fill：沒有列）
        → d2_keep（淨利÷股數補不出、但有 derived=2 列 ⇒ 用資料庫的全年−9 個月值）→ na（不可算）。
        literal=True（裁定①字面另一讀法）：沒有 d2_keep 這一步（補不出即不可算；只拿來報差異筆數）。
        單位錯的股數（< 1,000,000）當缺（★11）。"""
        r = self.row("eps_diluted", pe, asof)
        sfx = "" if r is None or not r["cls"] else ("_clsA1500" if r["cls"].endswith("/1500") else "_cls")   # ★20 用到類別列
        if r is not None and r["derived"] in (0, 1):
            return r["value"] / factor_after(splits, r["first_filed"]), "direct" + sfx
        ni = self.row("net_income", pe, asof)
        sh = self.row("diluted_shares", pe, asof) if self.fill_ok else None        # ★21
        if ni is not None and sh is not None and sh["value"] >= SHARES_MIN_SANE:
            basis = max(ni["first_filed"], sh["first_filed"])
            v = ni["value"] / sh["value"] / factor_after(splits, basis)
            return v, ("d2_fill" if r is not None else "miss_fill") + ("_cls" if sh["cls"] else "")
        if r is not None and not (literal or ALT["eps_literal"]):
            return r["value"] / factor_after(splits, r["first_filed"]), "d2_keep" + sfx
        return None, ("na_d2" if r is not None else "na")

    def latest_q(self, asof):
        """★7：asof 前已申報（淨利或 EPS 有列）的最新一季 period_end。"""
        best = None
        for f in ("net_income", "eps_diluted"):
            g = self.F[f]
            if g is None:
                continue
            m = g[g["first_filed"] < asof]
            if len(m):
                pe = m["period_end"].max()
                best = pe if best is None or pe > best else best
        if best is None or (asof - best).days > STALE_Q_DAYS:      # ★17
            return None
        # 對到 grid 上的點
        for pe in self.grid:
            if abs((pe - best).days) <= 5:
                return pe
        return None

    def prev_q(self, pe):
        """grid 上 period_end 在 [pe−105, pe−75] 日的季。"""
        for x in reversed(self.grid):
            dd = (pe - x).days
            if 75 <= dd <= 105:
                return x
            if dd > 105:
                break
        return None

    def last4(self, pe0):
        out = [pe0]
        while len(out) < 4:
            p = self.prev_q(out[-1])
            if p is None:
                return None
            out.append(p)
        return out

    def ttm_eps(self, asof, splits, kinds=None):
        if kinds is None:
            key = (self.t, self.cik, asof, splits, ALT["eps_literal"])
            if key not in _TTM:
                _TTM[key] = self._ttm_eps(asof, splits, None)
            return _TTM[key]
        return self._ttm_eps(asof, splits, kinds)

    def _ttm_eps(self, asof, splits, kinds=None):
        pe0 = self.latest_q(asof)
        if pe0 is None:
            return None, None
        qs = self.last4(pe0)
        if qs is None:
            return None, None
        tot = 0.0
        for pe in qs:
            v, k = self.eps_q(pe, asof, splits)
            if kinds is not None:
                kinds.append((pe, k))
            if v is None:
                return None, qs
            tot += v
        return tot, qs

    # ── 財年（★4）──
    def fy_quarters(self, q4_pe):
        """第四季 period_end ⇒ 4 季 period_end（新→舊）或 None（不相連）。"""
        ni = self.F["net_income"]
        if ni is None:
            return None
        if not hasattr(self, "_nirows"):
            self._nirows = ni.set_index("period_end")
        rows = self._nirows
        if q4_pe not in rows.index:
            return None
        qs = [q4_pe]
        cur = rows.loc[q4_pe]
        for _ in range(3):
            ps = cur["period_start"]
            if pd.isna(ps):
                return None
            cand = rows[(rows.index >= ps - pd.Timedelta(days=8)) & (rows.index <= ps + pd.Timedelta(days=6))]
            cand = cand[cand.index < qs[-1]]
            if len(cand) == 0:
                return None
            # ★18 多列時取 period_end 最接近 period_start−1 日者（同距取較早）
            dist = np.abs((cand.index - (ps - pd.Timedelta(days=1))).days)
            k = int(np.argmin(dist))
            qs.append(cand.index[k])
            cur = cand.iloc[k]
        span = (q4_pe - rows.loc[qs[-1], "period_start"]).days
        if not (351 <= span <= 380):
            return None
        return qs

    def fy_window(self, asof):
        """★4：→ list of 5 個 (財年末, 4 季 period_end 或 None)，新→舊；e* 找不到 ⇒ None。"""
        ni = self.F["net_income"]
        if ni is None:
            return None
        k10 = ni[ni["first_form"].fillna("").str.startswith("10-K") & (ni["first_filed"] < asof)]
        estar = None
        for pe in sorted(k10["period_end"], reverse=True):
            qs = self.fy_quarters(pe)
            if qs is not None and all(self.row("net_income", x, asof) is not None for x in qs):
                estar = pe
                break
        if estar is None:
            return None
        out = [(estar, self.fy_quarters(estar))]
        pes = ni["period_end"]
        for k in range(1, 5):
            tgt = estar - pd.DateOffset(years=k)
            c = pes[(pes - tgt).abs() <= pd.Timedelta(days=20)]
            qs = None
            e = None
            for pe in c:
                qq = self.fy_quarters(pe)
                if qq is not None:
                    qs, e = qq, pe
                    break
            out.append((e if e is not None else tgt, qs))
        return out

    def annual_sum(self, f, qs, asof):
        if qs is None:
            return None
        tot = 0.0
        for pe in qs:
            r = self.row(f, pe, asof)
            if r is None:
                return None
            tot += r["value"]
        return tot


@functools.lru_cache(maxsize=None)
def fund(t, cik=None):
    return Fund(t, cik)


# ═════════════ 封面股數（③、★9）═════════════
CLASS_OK = re.compile(r"(?:Common|Capital)", re.I)
CLASS_BAD = re.compile(r"(?:Preferred|Deposit|Note|Due|Subsidiar|Corporation|Company|Units|LLC|Partnership|Trust|Exchangeable)", re.I)


@functools.lru_cache(maxsize=None)
def shares_table():
    s = pd.read_csv(_p("fundamentals", "shares_outstanding.csv"), dtype=str, keep_default_na=False)
    s = s[s["index"] != "sp400"].copy()
    s["as_of_date"] = pd.to_datetime(s["as_of_date"])
    s["filed"] = pd.to_datetime(s["filed"])
    s["shares"] = s["shares"].astype(float)
    return {t: g.sort_values(["filed", "as_of_date"]) for t, g in s.groupby("ticker")}


def shares_asof(t, asof, cik=None):
    """→ (股數, as_of_date, kind) 或 (None, None, 'na')。kind：plain／class_sum。★19：cik≠None ⇒ 只用該 CIK（＋前身）的申報。"""
    g = shares_table().get(t)
    if g is None:
        return None, None, "na"
    if cik is not None:
        g = g[g["cik"].isin(cik_allowed(cik))]
    g = g[g["filed"] < asof]
    if not len(g):
        return None, None, "na"
    last = g[g["filed"] == g["filed"].max()]
    last = last[last["as_of_date"] == last["as_of_date"].max()]
    plain = last[last["share_class"] == ""]
    if len(plain):
        return float(plain["shares"].iloc[0]), last["as_of_date"].iloc[0], "plain"
    cl = last[last["share_class"].str.contains(CLASS_OK) & ~last["share_class"].str.contains(CLASS_BAD)]
    if len(cl):
        return float(cl["shares"].sum()), last["as_of_date"].iloc[0], "class_sum"
    return None, None, "na"


# ═════════════ 估值公式（seq63 §二逐字）═════════════
def fair_value(E0, g, pe_T, payout):
    e = E0
    pv = 0.0
    for t in range(1, 11):
        e *= (1 + g) if t <= 5 else (1 + g / 2)
        pv += e * payout / (1 + DISC) ** t
    return pv + e * pe_T / (1 + DISC) ** 10


def group_of(m):
    if not np.isfinite(m):
        return "偏貴"
    if m <= CHEAP_MAX:
        return "可買"
    if m <= NEAR_MAX:
        return "接近"
    return "偏貴"


# ═════════════ 單一（評估日, 代號）══════════════
def gates(F, d, splits, stat):
    """四條門檻 ⇒ dict(r1..r4 ∈ {pass, fail, na}, g_hist)。stat：計數器。"""
    W = F.fy_window(d)
    res = {"r1": "na", "r2": "na", "r3": "na", "r4": "na", "g_hist": None, "fy_end": None}
    if W is None:
        res["why"] = "no_fy"
        stat["fy_none"] += 1
        return res
    if (d - W[0][0]).days > STALE_FY_DAYS:               # ★17
        res["why"] = "stale_fy"
        res["fy_end"] = str(W[0][0].date())
        stat["fy_stale"] += 1
        return res
    res["fy_end"] = str(W[0][0].date())
    ni = [F.annual_sum("net_income", qs, d) for _, qs in W]
    # ★6 計 ProfitLoss 季
    for _, qs in W:
        for pe in (qs or []):
            r = F.row("net_income", pe, d)
            if r is not None and r["tag"] == "ProfitLoss":
                stat["ni_profitloss_q"] += 1
            if r is not None and "AvailableToCommonStockholders" in str(r["tag"]):     # ★22
                stat["ni_availcommon_q"] += 1
    # ① ROE
    hit = miss = 0
    for (e, qs), n in zip(W, ni):
        eq = F.row("equity", e, d) if qs is not None else None
        if eq is None and qs is not None and not ALT["equity_strict"]:      # ★16
            eq = F.row("equity_incl_nci", e, d)
            if eq is not None:
                stat["equity_incl_nci_year"] += 1
        if n is None or eq is None:
            miss += 1
            continue
        if eq["value"] <= 0:
            stat["roe_neg_equity"] += 1
            continue
        if n / eq["value"] >= ROE_MIN:
            hit += 1
    res["r1"] = "pass" if hit >= ROE_YEARS_NEED else ("fail" if hit + miss < ROE_YEARS_NEED else "na")
    # ② 虧損
    loss = unk = 0
    for (e, qs), n in zip(W, ni):
        if n is None:
            unk += 1
            continue
        if n < 0:
            oi = F.annual_sum("operating_income", qs, d)
            if oi is None:
                unk += 1
            elif oi <= 0:
                loss += 1
            else:
                stat["loss_year_oi_exempt"] += 1
    res["r2"] = "fail" if loss > 0 else ("pass" if unk == 0 else "na")
    # ③ EPS 4 段年複合
    def annual_eps(qs):
        if qs is None:
            return None
        tot = 0.0
        for pe in qs:
            v, k = F.eps_q(pe, d, splits)
            stat["eps_kind_annual_" + k] += 1
            if k.startswith(("direct", "d2_keep")):
                tg = str(F.row("eps_diluted", pe, d)["tag"])
                if "ContinuingOperations" in tg:                                 # ★22
                    stat["eps_contops_annual_q"] += 1
                if tg == "EarningsPerShareBasic":                                  # ★20 BRK 基本 EPS
                    stat["eps_basic_annual_q"] += 1
            if v is None:
                return None
            tot += v
        return tot
    e_end, e_start = annual_eps(W[0][1]), annual_eps(W[4][1])
    if e_start is None or e_end is None:
        res["r3"] = "na"
    elif e_start <= 0 or e_end <= 0:
        res["r3"] = "fail"
    else:
        gh = (e_end / e_start) ** 0.25 - 1
        res["g_hist"] = gh
        res["r3"] = "pass" if gh >= EPS_CAGR_MIN else "fail"
    # ④ 現金流／淨利
    cfo = [F.annual_sum("cfo", qs, d) for _, qs in W]
    if any(x is None for x in cfo) or any(x is None for x in ni):
        res["r4"] = "na"
    else:
        sn = sum(ni)
        res["r4"] = "fail" if sn <= 0 else ("pass" if sum(cfo) / sn >= CFO_NI_MIN else "fail")
    return res


def pe_target(F, d, src, splits, close):
    """★3：→ (pe_T, n_pos, first_pos_date) 或 (None, n_pos, first)。"""
    vals, dates = [], []
    for q in quarter_points():
        if q > d or q < d - pd.DateOffset(years=PE_LOOKBACK_YEARS):
            continue
        if q not in close.index:
            continue
        ttm, _ = F.ttm_eps(q, splits)
        if ttm is None or ttm <= 0:
            continue
        pe = close.loc[q] / ttm
        if pe > 0:
            vals.append(pe)
            dates.append(q)
    if not dates or dates[0] > d - pd.DateOffset(years=PE_MIN_YEARS):
        return None, len(vals), (dates[0] if dates else None)
    return min(float(np.median(vals)), PE_CAP), len(vals), dates[0]


def classify(t, d, stat):
    """→ dict（逐檔明細，私有）。"""
    rec = {"eval": str(d.date()), "ticker": t}
    pn = panel(t)
    if pn is None or d not in pn.index:
        rec["stage"] = "member_noprice" if member_by_spans(t, d) else "not_member"
        return rec
    row = pn.loc[d]
    if int(row["in_index"]) != 1:
        rec["stage"] = "not_member"
        return rec
    src = row["src"]
    rec["src"] = src
    cik, cik_ok = cik_for(t, d)                 # ★19
    if not cik_ok:
        rec["stage"] = "fund_mismatch"
        rec["why"] = "no_cik_segment"
        return rec
    if cik is not None:
        rec["cik"] = cik
        stat["cik_segment_used"] += 1
        stat["cikseg_%s_%s" % (t, cik)] += 1
        if any(ck == cik and b is not None for ck, _, b in cik_segments()[t]):    # 用到「有迄日」的舊段
            stat["cik_segment_old"] += 1
    elif t in renames_until() and d <= renames_until()[t]:
        rec["stage"] = "fund_mismatch"          # ★12（沿革：只剩沒有 cik 分段的代號）
        return rec
    close, _ = price_file(src)
    if d not in close.index:
        rec["stage"] = "no_close"
        return rec
    splits, inferred = split_list(t, src, cik)
    c = float(close.loc[d])
    sh, asof_sh, skind = shares_asof(t, d, cik)
    if sh is None:
        rec["stage"] = "mcap_na"
        return rec
    f_sh = factor_after(splits, asof_sh)
    if f_sh != 1.0:
        stat["split_adj_shares"] += 1
    mcap = sh * f_sh * c
    rec.update(close=c, shares=sh * f_sh, shares_kind=skind, mcap=mcap)
    if skind == "class_sum":
        stat["shares_class_sum"] += 1
    if mcap < MCAP_MIN:
        rec["stage"] = "mcap_small"
        return rec
    rec["stage"] = "pop"
    F = fund(t, cik)
    if t in CLASS_PICK:
        stat["class_ticker_pop"] += 1
    G = gates(F, d, splits, stat)
    rec.update({k: G.get(k) for k in ("r1", "r2", "r3", "r4", "g_hist", "fy_end", "why")})
    allp = all(G[k] == "pass" for k in ("r1", "r2", "r3", "r4"))
    rec["all_pass"] = allp
    # 分割調整筆數（本檔本日用到的每股值是否有被調）：
    rec["n_split_events"] = len(splits)
    rec["n_inferred_splits"] = len(inferred)
    if not allp:
        return rec
    kinds = []
    E0, qs = F.ttm_eps(d, splits, kinds)
    for pe, k in kinds:
        stat["eps_kind_E0_" + k] += 1
        if k.startswith(("direct", "d2_keep")):
            tg = str(F.row("eps_diluted", pe, d)["tag"])
            if "ContinuingOperations" in tg:                                     # ★22
                stat["eps_contops_E0_q"] += 1
            if tg == "EarningsPerShareBasic":
                stat["eps_basic_E0_q"] += 1
    rec["E0_kinds"] = ",".join(k for _, k in kinds)
    if E0 is None:
        rec["val"] = "E0_na"
        return rec
    peT, npos, fpos = pe_target(F, d, src, splits, close)
    rec.update(E0=E0, pe_T=peT, pe_npos=npos, pe_first=str(fpos.date()) if fpos is not None else None)
    if peT is None:
        rec["val"] = "peT_na"
        return rec
    g = min(G_MULT * G["g_hist"], G_CAP)
    # 配息率（★8）
    nd = 0
    dsum = 0.0
    for pe in qs:
        r = F.row("dps", pe, d)
        if r is not None:
            nd += 1
            dsum += r["value"] / factor_after(splits, r["first_filed"])
    rec["dps_quarters"] = nd
    if E0 <= 0:
        rec.update(val="ok", g=g, payout=None, fv=None, multiple=float("inf"), group="偏貴", E0_le0=True)
        return rec
    payout = min(max(dsum / E0, 0.0), 1.0)
    fv = fair_value(E0, g, peT, payout)
    m = c / fv if fv > 0 else float("inf")
    rec.update(val="ok", g=g, payout=payout, fv=fv, multiple=m, group=group_of(m), E0_le0=False)
    # 這一檔本日用到的每股值是否有分割調整（E0 四季、年度 EPS、股利）
    adj = any(factor_after(splits, F.row("eps_diluted", pe, d)["first_filed"]) != 1.0
              for pe in qs if F.row("eps_diluted", pe, d) is not None)
    rec["split_adjusted_E0"] = bool(adj)
    return rec


# ═════════════ 主程式：頻率表 ═════════════
def run(eval_list=None, tickers=None, write=True):
    assert_pinned()
    ev = list(eval_list or eval_dates())
    univ = list(tickers or universe_table()["ticker"])
    recs = []
    stat_by = {}
    for d in ev:
        st = Counter()
        for t in univ:
            r = classify(t, d, st)
            if r.get("stage") == "not_member":
                continue
            recs.append(r)
        stat_by[str(d.date())] = st
    R = pd.DataFrame(recs)
    if write:
        os.makedirs(PRIVD, exist_ok=True)
        R.to_csv(os.path.join(PRIVD, "classify_by_eval_ticker.csv"), index=False)
    return R, stat_by


def freq_table(R, stat_by):
    rows = []
    for d, g in R.groupby("eval", sort=True):
        pop = g[g["stage"] == "pop"]
        r = {"eval": d,
             "名冊在指數": int(len(g)),
             "在指數無價格": int((g["stage"] == "member_noprice").sum()),
             "財報對不上公司": int((g["stage"] == "fund_mismatch").sum()),
             "市值不可算": int((g["stage"] == "mcap_na").sum()),
             "市值<100億": int((g["stage"] == "mcap_small").sum()),
             "母體": int(len(pop))}
        for k, nm in (("r1", "①ROE"), ("r2", "②無虧損"), ("r3", "③EPS成長"), ("r4", "④現金流")):
            r[nm + "_過"] = int((pop[k] == "pass").sum())
            r[nm + "_不過"] = int((pop[k] == "fail").sum())
            r[nm + "_不可算"] = int((pop[k] == "na").sum())
            r[nm + "_通過率"] = round(float((pop[k] == "pass").mean()), 4) if len(pop) else None
        ap = pop[pop["all_pass"] == True]  # noqa: E712
        r["全過"] = int(len(ap))
        r["全過_E0不可算"] = int((ap.get("val") == "E0_na").sum()) if len(ap) else 0
        r["全過_peT不可算"] = int((ap.get("val") == "peT_na").sum()) if len(ap) else 0
        ok = ap[ap.get("val") == "ok"] if len(ap) else ap
        r["過門檻全部"] = int(len(ok))
        for G in GROUPS:
            r[G] = int((ok["group"] == G).sum()) if len(ok) else 0
        r["E0≤0歸偏貴"] = int(ok["E0_le0"].sum()) if len(ok) else 0
        r["無股利記0"] = int((ok["dps_quarters"] == 0).sum()) if len(ok) else 0
        r["股利部分季缺記0"] = int(((ok["dps_quarters"] > 0) & (ok["dps_quarters"] < 4)).sum()) if len(ok) else 0
        st = stat_by.get(d, Counter())
        for k in sorted(st):
            r["n_" + k] = int(st[k])
        rows.append(r)
    return pd.DataFrame(rows)


def main():
    import time
    t0 = time.time()
    R, stat_by = run()
    T = freq_table(R, stat_by)
    os.makedirs(OUTD, exist_ok=True)
    T.to_csv(os.path.join(OUTD, "freq_by_eval.csv"), index=False, encoding="utf-8-sig")
    S = summarize(R, T)
    # ★15 另一讀法（字面）：只報分組差異筆數
    for k in ALT:
        ALT[k] = True
    try:
        R2, _ = run(write=False)
    finally:
        for k in ALT:
            ALT[k] = False
    S["★15★16另一讀法（EPS 字面＋權益只用 equity）_分組差異"] = alt_diff(R, R2)
    jdump(S, os.path.join(OUTD, "freq_summary.json"))
    print(json.dumps(S, ensure_ascii=False, indent=1, default=str)[:6000])
    print("用時 %.0f 秒" % (time.time() - t0))


def _grp(R):
    g = R.get("group")
    lab = pd.Series("—", index=R.index) if g is None else g.fillna("—")
    lab = lab.where(R.get("val", pd.Series(None, index=R.index)) == "ok", "不在組")
    return dict(zip(zip(R["eval"], R["ticker"]), lab))


def alt_diff(R, R2):
    a, b = _grp(R), _grp(R2)
    keys = set(a) | set(b)
    ch = Counter()
    for k in keys:
        x, y = a.get(k, "不在組"), b.get(k, "不在組")
        if x != y:
            ch["%s→%s" % (x, y)] += 1
    per = {}
    for G in GROUPS:
        n1 = Counter(k[0] for k, v in a.items() if v == G)
        n2 = Counter(k[0] for k, v in b.items() if v == G)
        per[G] = {"本讀法_中位": float(np.median([n1.get(d, 0) for d in sorted({k[0] for k in a})])),
                  "字面讀法_中位": float(np.median([n2.get(d, 0) for d in sorted({k[0] for k in a})]))}
    return {"變動筆數(評估日,檔)": int(sum(ch.values())), "變動種類": dict(ch), "每評估日檔數": per}


def summarize(R, T):
    ne = len(T)
    small = {G: int((T[G] < 3).sum()) for G in ("可買", "偏貴")}
    trig = any(v > ne / 2 for v in small.values())
    ok = R[(R.get("stage") == "pop") & (R.get("all_pass") == True) & (R.get("val") == "ok")]  # noqa: E712
    # EPS 單季種類（E0 與年度 EPS 用到的）
    kinds = {}
    for c in T.columns:
        if c.startswith("n_eps_kind_"):
            kinds[c[len("n_eps_kind_"):]] = int(T[c].sum())
    yrs = sorted({d[:4] for d in T.loc[(T["可買"] > 0) & (T["偏貴"] > 0), "eval"]})
    # 分割調整：用到的推得分割（★10）與事件檔分割
    inf_used = set()
    ev_used = set()
    pop = R.loc[R.get("stage") == "pop"].copy()
    pop["cik"] = pop["cik"].where(pop["cik"].notna(), None) if "cik" in pop else None
    for t, src, ck in pop[["ticker", "src", "cik"]].drop_duplicates().itertuples(index=False):
        sp, inf = split_list(t, src, ck if isinstance(ck, str) else None)
        for x in inf:
            inf_used.add((t,) + tuple(map(str, x)))
        for x in sp:
            if x not in inf:
                ev_used.add((t,) + tuple(map(str, x)))
    S = {
        "登錄": "產業 seq63 pw1 %s" % REG_SHA, "發號": "裁定 %s §一" % RULING,
        "資料commit": data_commit(), "評估日數": ne,
        "評估日": [T["eval"].iloc[0], T["eval"].iloc[-1]],
        "每評估日檔數_中位_最少_最多": {c: [float(T[c].median()), int(T[c].min()), int(T[c].max())]
                                for c in ("名冊在指數", "母體", "全過", "過門檻全部", "可買", "接近", "偏貴")},
        "各門檻通過率_中位": {c: float(T[c].median()) for c in T.columns if c.endswith("_通過率")},
        "樣本不足": {"可買<3檔的評估日數": small["可買"], "偏貴<3檔的評估日數": small["偏貴"],
                 "門檻": "任一組 > %d／2 評估日" % ne, "觸發": bool(trig)},
        "EPS單季種類筆數": kinds,
        "EPS補值_說明": "direct＝公司自報單季（derived 0/1）；d2_fill＝derived=2 改用淨利÷股數（裁定①）；"
                     "miss_fill＝沒有列、用淨利÷股數；na_d2／na＝補不出（不可算）。筆數＝(評估日,代號,季) 計，母體內。",
        "全過但E0不可算": int(T["全過_E0不可算"].sum()), "全過但peT不可算": int(T["全過_peT不可算"].sum()),
        "分割調整": {"事件檔分割（母體用到的檔）": len(ev_used), "★10推得分割（母體用到的檔）": len(inf_used),
                  "推得清單": sorted(x[0] + " " + x[1][:10] + " ×" + x[2] for x in inf_used),
                  "封面股數被調的(評估日,檔)": int(T["n_split_adj_shares"].sum()) if "n_split_adj_shares" in T else 0,
                  "過門檻且E0四季有調的(評估日,檔)": int(ok["split_adjusted_E0"].sum()) if len(ok) else 0},
        "無股利記0_(評估日,檔)": int(T["無股利記0"].sum()), "股利部分季缺記0": int(T["股利部分季缺記0"].sum()),
        "E0≤0歸偏貴": int(T["E0≤0歸偏貴"].sum()),
        "在指數無價格_(評估日,檔)": int(T["在指數無價格"].sum()),
        "整段無價格進組(−100%)": 0,
        "整段無價格進組_說明": "★13：無收盤 ⇒ 市值與倍數不可算 ⇒ 進不了組；−100% 規則程式已寫（researchUSFairValue.py），實際 0 筆",
        "財報對不上公司_(評估日,檔)": int(T["財報對不上公司"].sum()),
        "市值不可算_(評估日,檔)": int(T["市值不可算"].sum()),
        "淨利ProfitLoss季_筆": int(T.get("n_ni_profitloss_q", pd.Series([0])).sum()) if "n_ni_profitloss_q" in T else 0,
        "權益≤0年_筆": int(T["n_roe_neg_equity"].sum()) if "n_roe_neg_equity" in T else 0,
        "虧損年因營業利益>0豁免_筆": int(T["n_loss_year_oi_exempt"].sum()) if "n_loss_year_oi_exempt" in T else 0,
        "封面股數類別相加_(評估日,檔)": int(T["n_shares_class_sum"].sum()) if "n_shares_class_sum" in T else 0,
        "進場年分群（可買與偏貴都非空的評估日之年）": yrs, "進場年分群數": len(yrs),
        "財年資料過舊★17_(評估日,檔)": int(T["n_fy_stale"].sum()) if "n_fy_stale" in T else 0,
        "財年資料過舊_檔": R.loc[R.get("why") == "stale_fy", "ticker"].value_counts().to_dict() if "why" in R else {},
        "找不到財年_(評估日,檔)": int(T["n_fy_none"].sum()) if "n_fy_none" in T else 0,
        "找不到財年_檔": R.loc[R.get("why") == "no_fy", "ticker"].value_counts().to_dict() if "why" in R else {},
        "權益用equity_incl_nci補★16_年": int(T["n_equity_incl_nci_year"].sum()) if "n_equity_incl_nci_year" in T else 0,
        "門檻不可算最多的檔": {k: R.loc[(R.get("stage") == "pop") & (R[k] == "na"), "ticker"].value_counts().head(15).to_dict()
                       for k in ("r1", "r2", "r3", "r4")},
    }
    # ── 裁定 seq481 新增（★19～★22）──
    ncol = lambda c: int(T[c].sum()) if c in T else 0     # noqa: E731
    S["★19_依評估日挑CIK"] = {
        "分段代號": {t: [[ck, str(a.date()) if a is not None else "", str(b.date()) if b is not None else ""] for ck, a, b in v]
                 for t, v in cik_segments().items()},
        "用到分段的(評估日,檔)": ncol("n_cik_segment_used"), "其中用舊段CIK": ncol("n_cik_segment_old"),
        "逐代號CIK_(評估日,檔)": {c[len("n_cikseg_"):]: int(T[c].sum()) for c in T.columns if c.startswith("n_cikseg_")},
        "評估日不落在任何段_(評估日,檔)": int((R.get("why") == "no_cik_segment").sum()) if "why" in R else 0,
        "★12殘留(renames_until且無分段)_(評估日,檔)": int(((R.get("stage") == "fund_mismatch") & (R.get("why") != "no_cik_segment")).sum()),
    }
    six = R[(R.get("stage") == "pop") & R["ticker"].isin(list(CLASS_PICK))]
    S["★20★21_多類股"] = {
        "指定類別": {t: [r[0] + ("" if r[3] == 1.0 else "÷1500") + ("" if r[1] is None else " pe≥" + str(r[1].date()))
                     + ("" if r[2] is None else " pe<" + str(r[2].date())) for r in v] for t, v in CLASS_PICK.items()},
        "淨利÷股數補值_可用": {t: {"ok": class_fill_ok(t)[0], "比值中位": None if class_fill_ok(t)[1] is None else round(class_fill_ok(t)[1], 4),
                           "對數": class_fill_ok(t)[2]} for t in CLASS_PICK},
        "同級衝突丟列": {k: v for k, v in _CLASS_LOG.items()},
        "6檔在母體_(評估日,檔)": int(len(six)),
        "6檔四條_各狀態": {k: six[k].value_counts().to_dict() for k in ("r1", "r2", "r3", "r4")} if len(six) else {},
        "6檔進組_(評估日,檔)": six.loc[six.get("val") == "ok", "group"].value_counts().to_dict() if len(six) and "val" in six else {},
        "6檔進組_逐代號評估日數": six.loc[six.get("val") == "ok"].groupby("ticker").size().to_dict() if len(six) and "val" in six else {},
        "EPS單季用到類別列_筆": {k: v for k, v in kinds.items() if "_cls" in k},
        "BRK基本EPS_季筆(年度/E0)": [ncol("n_eps_basic_annual_q"), ncol("n_eps_basic_E0_q")],
    }
    S["★22_新備援標籤"] = {"淨利AvailableToCommon季_筆": ncol("n_ni_availcommon_q"),
                       "EPS繼續營業部門標籤季_筆(年度/E0)": [ncol("n_eps_contops_annual_q"), ncol("n_eps_contops_E0_q")]}
    S["★15★16_筆數"] = {"權益用equity_incl_nci補_年": ncol("n_equity_incl_nci_year"),
                      "derived2改用淨利÷股數(d2_fill)_季筆": sum(v for k, v in kinds.items() if "d2_fill" in k),
                      "derived2照用(d2_keep)_季筆": sum(v for k, v in kinds.items() if "d2_keep" in k),
                      "沒有列用淨利÷股數(miss_fill)_季筆": sum(v for k, v in kinds.items() if "miss_fill" in k)}
    return S


if __name__ == "__main__":
    main()
