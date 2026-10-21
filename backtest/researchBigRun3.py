# -*- coding: utf-8 -*-
"""長線大漲段 補件第二階段：十一類樣貌全表＋對照 A～D（台股 seq532 §一 §二、seq534 §一②；裁定 seq421：描述、不判、不計 N；
每組數字與對照 A、B 並排；族群只當描述欄、⛔ 不當母體）——回測線計算子代理。
⛔ 描述件：不做任何檢定、不挑特徵、不給門檻；對照 B 用到的「之後 3 年報酬」只用來【定義】對照組（登錄 seq532 §一字面），⛔ 不比較、不檢定。
⛔ 不 commit、不改既有檔；resultsBigRun／resultsBigRun2 只讀；私有資料（us-stock-data 含 data/macro、taifex_private）⛔ 不讀。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBigRun3 [--procs 3] [--limit N --out DIR（乾跑）]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBigRun3_check
輸出 backtest/resultsBigRun3/：並排_乙.csv、並排_甲.csv、乙_全表.csv.gz、甲_全表.csv、對照B_乙.csv、對照B_甲.csv、對照C.csv、對照D.csv、
     缺欄.csv、段數.csv、bigrun3.json、run.log；（repo 外）~/bgrwork/bgr3_panel_<full|dry>.pkl（月底面板，供對帳）

═══ 讀法（D 標；★＝執行者定；未寫者 ＝ researchBigRun B1～B7、researchBigRun2 C1～C4 原樣）═══
 D1 單位：甲 ＝ resultsBigRun/甲_段（原版：市值 32、等權 35）＋ resultsBigRun2/甲補充_段（補充版：市值 29、等權 20），四版各自成表；
    乙 ＝ resultsBigRun/乙_段_x3（3,316 段；×5 只報段數）；族群 ＝ resultsBigRun2/族群_段 主切點群號，只當描述欄（⛔ 不分組、不當母體）。
 D2 ★ 時點一律對到「月底面板」（每個完整曆月最後交易日；兩世界合併日曆）：起點 ＝ 起點月底（乙、甲的起點本來就是月底）；前12月 ＝ 起點月底往前 12 個月底；
    高點 ＝ 高點當天或之前最後一個月底（⛔ 不用高點之後的月底，免得看到高點後資料）；高點前6月、高點後6月 ＝ 高點月底 ∓ 6 個月底。
    區間（流量、次數）＝ 兩個月底之間 (k1, k2]：前12月→起點、起點→高點、高點前6月→高點、高點→高點後6月。
    ⇒ 段與對照 A 用同一張面板、同一個月底，可直接並排；代價：「高點」那格最多早於真正高點一個月（「距一年高點@高點」不等於 0）。
 D3 個股月底面板（每檔 × 每個月底；只用該月底 d 當天或之前已公開的資料）：
  ② 市值（原始收盤 × 股數；★ 股數缺 ⇒ 面板市值 ÷ 同日原始收盤補，早年多屬此類）、股數、原始股價、上市年資（自合併資料第一根有效 K 棒；★ 第一根 ＝ 該市場資料首日 2004-02-11／上櫃 2007-07-02 ⇒ 標「年資左截斷」）、
     新上市（年資 ＜ 2 年）、產業內市值排名百分位（當月 PIT 產業內，1 ＝ 最大）
  ③ 本益比、股價淨值比及各自 5 年位置（官方 per／pbr；主 stocks_per、早年 early/per＋otcper 2012 起；1250 日窗、有值 ≥ 750）、市值營收比（市值 ÷ 近 12 個已公告月營收合計）、
     營業現金流 TTM ÷ 市值（fs_xbrl operating_cash_flow_ytd 差分）
  ④ 月營收年增（公告當時口徑，B6 同）、前一個已公告月的年增、★「年增由負轉正」＝ 最新一期 ＞ 0 且前一期 ≤ 0、近 3 期年增平均；
     ★ EPS 由虧轉盈 ＝ 最新已上傳季單季 EPS ＞ 0 且前一季 ≤ 0（fin_hist eps_ytd 差分）；毛利率、毛利率年變化（百分點）、★ 毛利率由降轉升 ＝ 最新季年變化 ＞ 0 且前一季年變化 ≤ 0；
     營業利益率（fin_hist opi_ytd、rev_ytd 差分成單季後相除）、年變化、由降轉升（同式）；ROE（近 4 季 nip_ytd 差分單季合計 ÷ 最新季 equity_parent）與 4 季前之差
     ⚠ 資料庫 C（fs_xbrl 毛利、營業利益、營業成本三欄）尚未到 main ⇒ 標「待資料庫」；本件毛利、營業利益先用 fs_hist／fin_hist（＝ 第一件口徑），C 到後可替換。
  ⑤ 合約負債（fs_xbrl contract_liabilities_current＋noncurrent，2018 起）年增、合約負債 ÷ 單季營收、（存貨＋合約負債）年增
  ⑥ 總資產年增、資本支出 TTM 年增（fs_xbrl；固定資產 ⇒ fs_xbrl 無此欄，記缺）；現增／可轉債決議次數（seo_cb_events，排除 ipo＝1）在各區間
  ⑦ 前 3 年報酬（還原；窗內有壞根 ⇒ 缺）、距 5 年低點（1250 交易日、最後一個壞根之後）、距一年高點（B6 同）
  ⑧ 60 日周轉率（60 交易日平均成交股數 ÷ 股數；無成交日算 0）、成交金額變化（近 60 日平均成交金額 ÷ 一年前同長度 − 1）、
     融資餘額 ÷ 股數（主 stocks_margin 2015 起、早年上櫃 otcmargin 2007-07 起；早年上市無）與 12 個月變化（百分點）、借券賣出餘額 ÷ 股數（universe sbl、otcsbl 2015 起）、
     集保千張以上大戶持股比（tdcc_hist level 15，2017 起，★ 取月底前一天或更早的最近一週）與 12 個月變化、外資持股率（foreign_holding 月表 2004-02～2012-12，上櫃 2007-05 起）與 12 個月變化、
     區間：外資＋投信買賣超 ÷ 股數（B6 同）、注意次數、處置次數（attention／disposal，★ 2011-01 起才算，區間起點早於即缺）、內部人申報轉讓股數 ÷ 股數（insider_predeclare，申報日 ＝ 可用日；
     shares 空白 ⇒ plan_own＋plan_trust）
  ⑨ 市場層（各段同月同值，只並報、⛔ 無對照 A）：景氣對策信號分數（ndc_signal，⚠ 修正後資料、非當時公布值；★ 取月底所在月的前一個月）、
     大盤融資餘額（marginmkt 融資（交易單位），2005-01-03 起）與 12 個月變化、0050 200 日乖離、0050 與全市場等權 前 12 個月最大回落；
     SOX、美國同產業、匯率、美國利率 ⇒「無」（外部數列在私有庫，⛔ 不讀）
  ⑩ 段的形狀（日線）：起點→高點月數、段中最大回檔（起點到高點路徑）、★ 波數 ＝ 1 ＋ 段內「自前高回落 ≥ 20%」的次數（每次回落以再創新高結束）、
     高點後 12 個月最大跌幅、高點到其後 12 個月最低點的月數（遇壞根、下市截止）
  ⑪ 結束樣貌 ＝ 上列在 高點前6月、高點、高點後6月 三個時點（D2）
 D4 產業月底面板（甲）：成員 ＝ 該月底 PIT 產業、20 日內有成交、市值 ＞ 0、排除類別（B2 同）。★ 個股欄一律取成員中位數（旗標欄取比例）；
    另加總口徑 營收年增(加總)；價格位置三欄（前 3 年報酬、距一年高點、距 5 年低點）改用該版產業指數（市值或等權，鏈內）。
 D5 對照 A ★：同一月底、其餘個股（乙）／其餘產業（甲）的同一欄 ⇒ 報「A 中位」＝ 各段同月他者中位數的中位、「段在同月橫斷面的百分位中位」（0.5 ＝ 跟大家一樣）。
 D6 對照 B ★（起漲條件相似但沒漲）：
    乙：候選 ＝ 每檔每個月底（起點規則同 B5：該月最後一根有效 K 棒），條件全成立：
      (a) 起點前可得的 5 欄都落在乙 3,316 段起點值的 [p25, p75]：前 3 年報酬、距一年高點、月營收年增、log 市值、60 日周轉率；
      (b) 之後 3 曆年窗完整（不超出資料尾、不下市、無壞根），窗內最高收盤 ＜ 3 × 起點收盤（不是大漲段），且窗末收盤 ÷ 起點收盤 − 1 ＜ 0050 同窗；
      (c) 不落在該股任何乙段的 [起點, 高點]；同一檔取最早一筆、之後 36 個月內不再取。B 的「高點」＝ 窗內最高收盤日（時點同 D2）。
    甲：候選 ＝ 每產業每月底（該版指數鏈內、之後 36 個月窗在鏈內），條件：前 3 年指數報酬、指數距一年高點、營收年增(加總) 落在該版甲段起點值 [p25, p75]；
      之後 36 個月指數報酬 ＜ 0050（原版）／＜ 全市場等權（補充版）同窗；不落在該版同產業任何甲段 [起點, 高點]；同產業 36 個月內不重取。
 D7 對照 C ★（差一點）：該版產業指數 3 年窗 +50% ≤ R ＜ +100% 的窗，同 B4 併段；剔除與該版同產業任一甲段相交者；高點後 12 個月最大跌幅 ≤ −20%（「就回落」）才算；
    （不設 0050 條件；不剔高點後未滿 12 個月者，照標）。
 D8 對照 D（漲了又崩，飆股回推妖股的長線版）：乙段高點後 12 個曆月內（遇壞根止）最低收盤 ≤ 高點收盤 × 0.5；
    高點後窗未滿 12 個月且未崩 ⇒「未定」；窗內下市 ⇒「下市」（另列）。D 是乙的子集，並報 D 與「乙非 D」。
 D9 必附：「描述，不是選股規則」「族群分群是事後分群，只當描述，⛔ 不當回測母體」「2015～2020 下市公司月營收約 80 家補不回」「上櫃 2007-07 前無價」
    「月營收為最新版、更正期間有輕微前視（快照 dbfb96cb81a7）」「景氣燈號為修正後資料、非當時公布值」「本件找到的任何特徵若要用，一律另起草登錄（seq421）」。
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
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
from backtest import researchIndMom_freq as IMF             # noqa: E402
from backtest import researchPTH_freq as PF                 # noqa: E402
from backtest import researchIndRev_prereg as PRE           # noqa: E402
from backtest import research11 as R                        # noqa: E402
from backtest import researchLongPool as LP                 # noqa: E402  load_filing、load_fs、load_fin、single、qkey、rev_avail
import backtest.data as D                                   # noqa: E402

SHA_A = "dbfb96cb81a7d3032e07fe47d1aeb5f0230545fa"           # 月營收、財報、產業別、早年 per（同第一件）
SHA_B = "325a1ee753cfcb3b77a65fa270bb3120aad04fd2"           # 外資持股月表、景氣燈號、內部人、現增可轉債、注意處置、大盤融資、集保、早年上櫃融資、借券
WORK = os.path.expanduser("~/bgrwork")
DATA_A = os.path.join(WORK, f"main_{SHA_A[:12]}", "data")
ARCH_B = ["data/meta/foreign_holding", "data/meta/ndc_signal", "data/meta/insider_predeclare", "data/meta/seo_cb_events", "data/meta/attention.csv",
          "data/meta/disposal.csv", "data/early/marginmkt", "data/universe/marginmkt", "data/tdcc_hist", "data/early/otcmargin",
          "data/universe/sbl", "data/universe/otcsbl"]
SRC1, SRC2 = "backtest/resultsBigRun", "backtest/resultsBigRun2"
OUT = "backtest/resultsBigRun3"
EXCL_IND = {"其他", "綜合", "存託憑證", "ETF", ""}
ALIVE = 20
DAYS_Q = 91.25
ATT0 = pd.Timestamp("2011-01-01")
INST_EARLY = pd.Timestamp("2012-05-02")
NOTES = ["描述，不是選股規則", "族群分群是事後分群，只當描述，⛔ 不當回測母體", "2015～2020 下市公司月營收約 80 家補不回", "上櫃 2007-07 前無價",
         "月營收為最新版、更正期間有輕微前視（快照 dbfb96cb81a7）", "景氣燈號為修正後資料、非當時公布值（只描述）",
         "本件找到的任何特徵若要用，一律另起草登錄、用沒看過的期間或前瞻驗（seq421）", "毛利、營業利益：資料庫 C 未到 main ⇒ 待資料庫；本件先用 fs_hist／fin_hist（同第一件）"]
PTS = ("前12月", "起點", "高點前6月", "高點", "高點後6月")
PTOFF = {"前12月": ("s", -12), "起點": ("s", 0), "高點前6月": ("h", -6), "高點": ("h", 0), "高點後6月": ("h", 6)}
WINS = {"前12月→起點": ("前12月", "起點"), "起點→高點": ("起點", "高點"), "高點前6月→高點": ("高點前6月", "高點"), "高點→高點後6月": ("高點", "高點後6月")}
# 個股面板欄（名稱, 類別）
LV = [("市值(億)", "②"), ("股數(億股)", "②"), ("股價(原始)", "②"), ("上市年資", "②"), ("新上市(<2年)", "②"), ("產業內市值排名百分位", "②"),
      ("本益比", "③"), ("本益比5年位置", "③"), ("股價淨值比", "③"), ("股價淨值比5年位置", "③"), ("市值營收比", "③"), ("營業現金流TTM÷市值", "③"),
      ("月營收年增", "④"), ("月營收年增由負轉正", "④"), ("近3期營收年增平均", "④"), ("EPS由虧轉盈", "④"), ("毛利率", "④"), ("毛利率年變化", "④"),
      ("毛利率由降轉升", "④"), ("營業利益率", "④"), ("營業利益率年變化", "④"), ("營業利益率由降轉升", "④"), ("ROE", "④"), ("ROE年變化", "④"),
      ("合約負債年增", "⑤"), ("合約負債÷單季營收", "⑤"), ("存貨+合約負債年增", "⑤"), ("存貨天數", "⑤"),
      ("總資產年增", "⑥"), ("資本支出TTM年增", "⑥"),
      ("前3年報酬", "⑦"), ("距5年低點", "⑦"), ("距一年高點", "⑦"),
      ("60日周轉率", "⑧"), ("成交金額變化(對一年前)", "⑧"), ("融資餘額÷股數", "⑧"), ("融資餘額÷股數12月變化", "⑧"), ("借券賣出餘額÷股數", "⑧"),
      ("集保千張大戶比", "⑧"), ("集保千張大戶比12月變化", "⑧"), ("外資持股率(月表)", "⑧"), ("外資持股率12月變化", "⑧")]
FLAGS = {"新上市(<2年)", "月營收年增由負轉正", "EPS由虧轉盈", "毛利率由降轉升", "營業利益率由降轉升"}
CUMS = [("外資投信買賣超÷股數", "⑧"), ("注意次數", "⑧"), ("處置次數", "⑧"), ("內部人申報轉讓÷股數", "⑧"), ("現增可轉債決議次數", "⑥")]
MKT = ["景氣信號分數(修正後)", "大盤融資餘額(萬張)", "大盤融資12月變化", "0050乖離200日", "0050前12月最大回落", "全市場等權前12月最大回落"]
IDXF = ("前3年報酬", "距一年高點", "距5年低點")
LOG: list = []
_G: dict = {}


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def ensure_B():
    root = os.path.join(WORK, f"mainB_{SHA_B[:12]}")
    if not os.path.isfile(os.path.join(root, ".done")):
        subprocess.run(["git", "cat-file", "-e", SHA_B], check=True)
        os.makedirs(root, exist_ok=True)
        p = subprocess.run(["git", "archive", "--format=tar", SHA_B] + ARCH_B, capture_output=True, check=True)
        subprocess.run(["tar", "-x", "-C", root], input=p.stdout, check=True)
        open(os.path.join(root, ".done"), "w").write(SHA_B)
    return os.path.join(root, "data")


def fstat(f, v):
    """旗標欄報比例（中位欄放比例），其餘報中位、四分位。"""
    base = f.split("@")[0]
    if base in FLAGS:
        v = np.asarray(v, float); v = v[np.isfinite(v)]
        return {"n": int(len(v)), "中位": float(v.mean()) if len(v) else np.nan, "p25": np.nan, "p75": np.nan}
    return qstat(v)


def qstat(v):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    if not len(v):
        return {"n": 0, "中位": np.nan, "p25": np.nan, "p75": np.nan}
    return {"n": int(len(v)), "中位": float(np.median(v)), "p25": float(np.percentile(v, 25)), "p75": float(np.percentile(v, 75))}


# ═════════════ 逐股讀檔 ═════════════
def aux_job(sid):
    G = _G; NC = G["NC"]
    o = {"sid": sid, "name": "", "rc_e": np.nan, "rc_m": np.nan, "inst_cov": -1}
    for k in ("rc", "vol", "amt", "sh", "per", "pbr", "mbal", "inst"):
        o[k] = np.full(NC, np.nan, np.float32) if k != "inst" else np.zeros(NC, np.float32)
    pe, pm = G["SEAM"].get(sid, (-1, -1))
    for wn, data, off, cal in G["PARTS"]:
        f = os.path.join(data, "stocks", f"{sid}.csv")
        if not os.path.exists(f):
            continue
        x = pd.read_csv(f, dtype={"date": str}, usecols=["date", "name", "close", "volume", "amount", "shares"]).drop_duplicates("date", keep="last")
        ix = cal.get_indexer(pd.to_datetime(x["date"])); ok = ix >= 0; pos = ix[ok] + off
        for k, c in (("rc", "close"), ("vol", "volume"), ("amt", "amount"), ("sh", "shares")):
            o[k][pos] = pd.to_numeric(x[c], errors="coerce").to_numpy(float)[ok]
        if len(x):
            o["name"] = str(x["name"].iloc[-1])
        if wn == "早年" and pe >= 0:
            o["rc_e"] = float(o["rc"][pe])
        if wn == "主" and pm >= 0:
            o["rc_m"] = float(o["rc"][pm])
        fi = os.path.join(data, "stocks_inst", f"{sid}.csv")
        if os.path.exists(fi):
            y = pd.read_csv(fi, dtype={"date": str}, usecols=["date", "foreign", "trust"]).drop_duplicates("date", keep="last")
            iy = cal.get_indexer(pd.to_datetime(y["date"])); oky = iy >= 0
            v = (pd.to_numeric(y["foreign"], errors="coerce").fillna(0) + pd.to_numeric(y["trust"], errors="coerce").fillna(0)).to_numpy(float)
            o["inst"][iy[oky] + off] = v[oky]
            if wn == "早年" and G["MK_E"].get(sid) == "twse" and oky.any() and o["inst_cov"] < 0:
                o["inst_cov"] = int(max(iy[oky].min(), int(cal.searchsorted(INST_EARLY))) + off)
        if wn == "主":
            if o["inst_cov"] < 0:
                o["inst_cov"] = off
            fp = os.path.join(data, "stocks_per", f"{sid}.csv")
            if os.path.exists(fp):
                z = pd.read_csv(fp, dtype={"date": str}, usecols=["date", "per", "pbr"]).drop_duplicates("date", keep="last")
                iz = cal.get_indexer(pd.to_datetime(z["date"])); okz = iz >= 0
                for k in ("per", "pbr"):
                    v = pd.to_numeric(z[k], errors="coerce").to_numpy(float)[okz]
                    o[k][iz[okz] + off] = np.where(v > 0, v, np.nan)
            fm = os.path.join(data, "stocks_margin", f"{sid}.csv")
            if os.path.exists(fm):
                z = pd.read_csv(fm, dtype={"date": str}, usecols=["date", "m_balance"]).drop_duplicates("date", keep="last")
                iz = cal.get_indexer(pd.to_datetime(z["date"])); okz = iz >= 0
                o["mbal"][iz[okz] + off] = pd.to_numeric(z["m_balance"], errors="coerce").to_numpy(float)[okz]
    o["sh"] = pd.Series(o["sh"]).ffill().to_numpy(np.float32)
    return o


def load_daily_dir(paths, cols, ids, cal, off=0):
    """日檔夾（每檔一天）⇒ {欄: N×NC 由呼叫端填}；回 DataFrame(date, stock_id, cols)。"""
    L = []
    for f in paths:
        x = pd.read_csv(f, dtype={"stock_id": str, "date": str}, usecols=["date", "stock_id"] + cols)
        L.append(x[x["stock_id"].isin(ids)])
    if not L:
        return pd.DataFrame(columns=["date", "stock_id"] + cols)
    return pd.concat(L, ignore_index=True)


# ═════════════ 財報 ═════════════
def build_quarterly(FD, ids):
    QK0, QK1 = LP.qkey(2012, 1), LP.qkey(2026, 4)
    fmin, fsrc = LP.load_filing(FD)
    FS = LP.load_fs(FD, set(ids), QK0, QK1)
    L = []
    for f in sorted(glob.glob(os.path.join(FD, "mops", "fin_hist", "*.csv"))):
        per = os.path.basename(f)[:6]; k = LP.qkey(per[:4], per[5])
        x = pd.read_csv(f, dtype={"stock_id": str}, usecols=["stock_id", "rev_ytd", "gp_ytd", "opi_ytd", "nip_ytd", "eps_ytd", "equity_parent"])
        x = x[x["stock_id"].isin(ids)].copy(); x["qk"] = k; L.append(x)
    FN = pd.concat(L).drop_duplicates(["stock_id", "qk"], keep="last")
    for c in ("rev_ytd", "gp_ytd", "opi_ytd", "nip_ytd", "eps_ytd", "equity_parent"):
        FN[c] = pd.to_numeric(FN[c], errors="coerce")
    FN = {s: g.set_index("qk").sort_index() for s, g in FN.groupby("stock_id")}
    L = []
    for f in sorted(glob.glob(os.path.join(FD, "meta", "fs_xbrl", "fs_xbrl_*.csv"))):
        x = pd.read_csv(f, dtype={"stock_id": str}, usecols=["period", "stock_id", "report", "inventories", "contract_liabilities_current",
                                                             "contract_liabilities_noncurrent", "total_assets", "operating_cash_flow_ytd", "capex_ytd"])
        x = x[x["stock_id"].isin(ids)].copy()
        x["_r"] = (x["report"] != "cr").astype(int)
        x = x.sort_values(["stock_id", "period", "_r"]).drop_duplicates(["stock_id", "period"], keep="first")
        x["qk"] = [LP.qkey(p[:4], p[-1]) for p in x["period"]]; L.append(x)
    XB = pd.concat(L)
    for c in ("inventories", "contract_liabilities_current", "contract_liabilities_noncurrent", "total_assets", "operating_cash_flow_ytd", "capex_ytd"):
        XB[c] = pd.to_numeric(XB[c], errors="coerce")
    XB = {s: g.set_index("qk").sort_index() for s, g in XB.groupby("stock_id")}
    KS = np.arange(QK0, QK1 + 1); n = len(KS)
    Q = {}
    for s in ids:
        fs, fn, xb = FS.get(s), FN.get(s), XB.get(s)
        a = {k: np.full(n, np.nan) for k in ("rev", "gp", "cogs", "opi", "rq", "nip", "eps", "eqp", "inv", "cl", "ta", "ocf", "cap")}
        av = np.full(n, np.datetime64("NaT"), "datetime64[ns]")
        for j, k in enumerate(KS):
            r1 = g1 = c1 = np.nan
            if fs is not None and k in fs.index:
                r1 = LP.single(fs["營業收入"], k); c1 = LP.single(fs["營業成本"], k)
                gpn = fs["營業毛利（毛損）淨額"] if fs["營業毛利（毛損）淨額"].notna().any() else fs["營業毛利（毛損）"]
                g1 = LP.single(gpn, k)
            if np.isfinite(r1) and np.isfinite(g1):
                a["rev"][j], a["gp"][j] = r1, g1; a["cogs"][j] = c1 if np.isfinite(c1) else r1 - g1
            elif fn is not None and k in fn.index:
                r2 = LP.single(fn["rev_ytd"], k); g2 = LP.single(fn["gp_ytd"], k)
                if np.isfinite(r2):
                    a["rev"][j] = r2; a["gp"][j] = g2; a["cogs"][j] = r2 - g2 if np.isfinite(g2) else np.nan
            if fn is not None and k in fn.index:
                # ⚠ fin_hist 第 4 季的 *_q 欄空白 ⇒ 一律由年初累計差分成單季（Q1 不減）
                a["opi"][j] = LP.single(fn["opi_ytd"], k); a["rq"][j] = LP.single(fn["rev_ytd"], k)
                a["nip"][j] = LP.single(fn["nip_ytd"], k); a["eps"][j] = LP.single(fn["eps_ytd"], k); a["eqp"][j] = fn.at[k, "equity_parent"]
            if xb is not None and k in xb.index:
                row = xb.loc[k]
                a["inv"][j] = row["inventories"]
                c_ = [row["contract_liabilities_current"], row["contract_liabilities_noncurrent"]]
                a["cl"][j] = np.nansum(c_) if np.isfinite(c_).any() else np.nan
                a["ta"][j] = row["total_assets"]
                o_ = LP.single(xb["operating_cash_flow_ytd"], k); a["ocf"][j] = o_
                cy = LP.single(xb["capex_ytd"], k); a["cap"][j] = -cy if np.isfinite(cy) else np.nan
            t = fmin.get((s, int(k)))
            if t is not None:
                av[j] = np.datetime64(pd.Timestamp(t).normalize())
        a["av"] = av
        Q[s] = a
    return Q, KS


# ═════════════ 月底面板（逐股，子程序）═════════════
def panel_job(i):
    G = _G
    s = G["SIDS"][i]; MEp = G["MEp"]; K = len(MEp); CAL = G["CAL"]
    out = {k: np.full(K, np.nan, np.float32) for k, _ in LV}
    cum = {k: np.full(K, np.nan) for k, _ in CUMS}
    meta = {"rev_per": np.full(K, -1, np.int32), "fs_qk": np.full(K, -1, np.int32), "fs_av": np.full(K, -1, np.int64)}
    vp = G["VP"][i]; vc = G["VC"][i]; vb = G["VB"][i]
    if len(vp) == 0:
        return i, out, cum, meta
    cbad = np.r_[0, np.cumsum(vb)]
    rc = G["RC"][i]; vol = np.nan_to_num(G["VOL"][i]); amt = np.nan_to_num(G["AMT"][i]); sh = G["SH"][i]
    per, pbr, mb, sbl, tdc, fh = G["PER"][i], G["PBR"][i], G["MBAL"][i], G["SBL"][i], G["TDCC"][i], G["FH"][i]
    cvol = np.r_[0, np.cumsum(vol)]; camt = np.r_[0, np.cumsum(amt)]
    first = CAL[vp[0]]; cens = first in G["CENS"]
    q = G["Q"].get(s); rv = G["REVA"].get(s); ly = G["LYA"].get(s)
    for k in range(K):
        p = int(MEp[k]); d = CAL[p]
        kk = int(np.searchsorted(vp, p, "right")) - 1
        if kk < 0 or p - vp[kk] > ALIVE:
            continue
        c = vc[kk]; shp = sh[p] if np.isfinite(sh[p]) and sh[p] > 0 else np.nan
        rcp = rc[vp[kk]]
        mc = rcp * shp
        out["市值(億)"][k] = mc / 1e8; out["股數(億股)"][k] = shp / 1e8; out["股價(原始)"][k] = rcp
        age = (d - first).days / 365.25
        out["上市年資"][k] = age if not cens else np.nan
        out["新上市(<2年)"][k] = float(age < 2) if not (cens and age < 2) else np.nan
        # 價格位置
        k0 = int(np.searchsorted(vp, p - 249, "left")); bb = np.flatnonzero(vb[k0 + 1:kk + 1])
        k0 = k0 + 1 + int(bb[-1]) if len(bb) else k0
        out["距一年高點"][k] = c / vc[k0:kk + 1].max() - 1
        k5 = int(np.searchsorted(vp, p - 1249, "left")); bb = np.flatnonzero(vb[k5 + 1:kk + 1])
        k5 = k5 + 1 + int(bb[-1]) if len(bb) else k5
        out["距5年低點"][k] = c / vc[k5:kk + 1].min() - 1
        if k >= 36:
            p3 = int(MEp[k - 36]); k3 = int(np.searchsorted(vp, p3, "right")) - 1
            if k3 >= 0 and p3 - vp[k3] <= ALIVE and cbad[kk + 1] - cbad[k3 + 1] == 0:
                out["前3年報酬"][k] = c / vc[k3] - 1
        if p >= 59 and np.isfinite(shp):
            out["60日周轉率"][k] = (cvol[p + 1] - cvol[p - 59]) / 60 / shp
        if p >= 309:
            a1 = (camt[p + 1] - camt[p - 59]) / 60; a0 = (camt[p - 249] - camt[p - 309]) / 60
            out["成交金額變化(對一年前)"][k] = a1 / a0 - 1 if a0 > 0 else np.nan
        for nm, arr in (("本益比", per), ("股價淨值比", pbr)):
            v = arr[p]
            if np.isfinite(v):
                out[nm][k] = v
                w = arr[max(0, p - 1249):p + 1]; w = w[np.isfinite(w)]
                if len(w) >= 750:
                    out[f"{nm}5年位置"][k] = float((w <= v).mean())
        for nm, arr, lag in (("融資餘額÷股數", mb, ALIVE), ("借券賣出餘額÷股數", sbl, ALIVE)):
            j = G["LASTOK"](arr, p, lag)
            if j >= 0 and np.isfinite(shp):
                out[nm][k] = arr[j] * (1000.0 if nm.startswith("融資") else 1.0) / shp
        j = G["LASTOK"](tdc, p - 1, 14)
        if j >= 0:
            out["集保千張大戶比"][k] = tdc[j]
        j = G["LASTOK"](fh, p, 5)
        if j >= 0:
            out["外資持股率(月表)"][k] = fh[j]
        # 月營收
        if rv is not None:
            km = int(G["KM"][k]); got = []
            for kr in range(km, -1, -1):
                v, l = rv[kr], ly[kr]
                if np.isfinite(v):
                    got.append((kr, v / l - 1 if (np.isfinite(l) and l > 0) else np.nan))
                if len(got) >= 3 or kr <= km - 4:
                    break
            if got and got[0][0] >= km - 2:
                meta["rev_per"][k] = got[0][0]
                y0 = got[0][1]; out["月營收年增"][k] = y0
                if len(got) >= 2 and got[1][0] == got[0][0] - 1 and np.isfinite(y0) and np.isfinite(got[1][1]):
                    out["月營收年增由負轉正"][k] = float(y0 > 0 and got[1][1] <= 0)
                if len(got) == 3 and got[2][0] == got[0][0] - 2:
                    yy = [g[1] for g in got]
                    if np.isfinite(yy).all():
                        out["近3期營收年增平均"][k] = float(np.mean(yy))
                w12 = rv[got[0][0] - 11:got[0][0] + 1] if got[0][0] >= 11 else np.array([np.nan])
                if len(w12) == 12 and np.isfinite(w12).all() and w12.sum() > 0 and np.isfinite(mc):
                    out["市值營收比"][k] = mc / (w12.sum() * 1000)
        # 財報
        if q is not None:
            okq = np.flatnonzero(~np.isnat(q["av"]) & (q["av"] < np.datetime64(d)))
            if len(okq):
                j = int(okq.max()); meta["fs_qk"][k] = int(G["KS"][j]); meta["fs_av"][k] = int(q["av"][j].astype("datetime64[D]").astype(np.int64))

                def rat(a, b, jj):
                    return a[jj] / b[jj] if (jj >= 0 and np.isfinite(a[jj]) and np.isfinite(b[jj]) and b[jj] > 0) else np.nan
                gm = rat(q["gp"], q["rev"], j); gm4 = rat(q["gp"], q["rev"], j - 4); gm1 = rat(q["gp"], q["rev"], j - 1); gm5 = rat(q["gp"], q["rev"], j - 5)
                out["毛利率"][k] = gm; out["毛利率年變化"][k] = gm - gm4
                if np.isfinite(gm - gm4) and np.isfinite(gm1 - gm5):
                    out["毛利率由降轉升"][k] = float(gm - gm4 > 0 and gm1 - gm5 <= 0)
                om = rat(q["opi"], q["rq"], j); om4 = rat(q["opi"], q["rq"], j - 4); om1 = rat(q["opi"], q["rq"], j - 1); om5 = rat(q["opi"], q["rq"], j - 5)
                out["營業利益率"][k] = om; out["營業利益率年變化"][k] = om - om4
                if np.isfinite(om - om4) and np.isfinite(om1 - om5):
                    out["營業利益率由降轉升"][k] = float(om - om4 > 0 and om1 - om5 <= 0)
                if j >= 1 and np.isfinite(q["eps"][j]) and np.isfinite(q["eps"][j - 1]):
                    out["EPS由虧轉盈"][k] = float(q["eps"][j] > 0 and q["eps"][j - 1] <= 0)

                def roe(jj):
                    if jj < 3:
                        return np.nan
                    n4 = q["nip"][jj - 3:jj + 1]; e = q["eqp"][jj]
                    return n4.sum() / e if (np.isfinite(n4).all() and np.isfinite(e) and e > 0) else np.nan
                r0 = roe(j); out["ROE"][k] = r0; out["ROE年變化"][k] = r0 - roe(j - 4)

                def yoy(a, jj):
                    return a[jj] / a[jj - 4] - 1 if (jj >= 4 and np.isfinite(a[jj]) and np.isfinite(a[jj - 4]) and a[jj - 4] > 0) else np.nan
                out["合約負債年增"][k] = yoy(q["cl"], j)
                out["合約負債÷單季營收"][k] = rat(q["cl"], q["rev"], j)
                ic = q["inv"] + q["cl"]
                out["存貨+合約負債年增"][k] = yoy(ic, j)
                out["存貨天數"][k] = rat(q["inv"], q["cogs"], j) * DAYS_Q
                out["總資產年增"][k] = yoy(q["ta"], j)
                if j >= 7:
                    c4, c4o = q["cap"][j - 3:j + 1], q["cap"][j - 7:j - 3]
                    if np.isfinite(c4).all() and np.isfinite(c4o).all() and c4o.sum() > 0:
                        out["資本支出TTM年增"][k] = c4.sum() / c4o.sum() - 1
                if j >= 3:
                    o4 = q["ocf"][j - 3:j + 1]
                    if np.isfinite(o4).all() and np.isfinite(mc) and mc > 0:
                        out["營業現金流TTM÷市值"][k] = o4.sum() / mc
        # 累計（區間差分用）
        cum["外資投信買賣超÷股數"][k] = G["CINST"][i][p] if p >= G["INSTCOV"][i] >= 0 else np.nan
        for nm, arr in (("注意次數", G["CATT"]), ("處置次數", G["CDIS"]), ("內部人申報轉讓÷股數", G["CINS"]), ("現增可轉債決議次數", G["CSEO"])):
            cum[nm][k] = arr[i][p] if (nm not in ("注意次數", "處置次數") or d >= ATT0) else np.nan
    # 12 月變化
    for a_, b_ in (("融資餘額÷股數", "融資餘額÷股數12月變化"), ("集保千張大戶比", "集保千張大戶比12月變化"), ("外資持股率(月表)", "外資持股率12月變化")):
        x = out[a_]; out[b_][12:] = x[12:] - x[:-12]
    out["_shares"] = np.array([sh[int(p)] for p in MEp], np.float64)
    return i, out, cum, meta


def lastok(arr, p, lag):
    if p < 0:
        return -1
    lo = max(0, p - lag)
    w = np.flatnonzero(np.isfinite(arr[lo:p + 1]))
    return lo + int(w[-1]) if len(w) else -1


def shape_path(pos, val, bad, s_pos, h_pos, cal, cend, after=True):
    """日線路徑（有效 K 棒位置、值、壞根旗標）：回 ⑩ 形狀欄。"""
    o = {"起點→高點月數": (cal[h_pos] - cal[s_pos]).days / 30.44, "段中最大回檔": np.nan, "波數": np.nan,
         "高點後12月最大跌幅": np.nan, "高點後跌到低點月數": np.nan, "高點後窗": ""}
    a = int(np.searchsorted(pos, s_pos, "left")); b = int(np.searchsorted(pos, h_pos, "right")) - 1
    if b <= a:
        return o
    v = val[a:b + 1]
    rm = np.maximum.accumulate(v); ddp = v / rm - 1
    o["段中最大回檔"] = float(ddp.min())
    waves = 1; inside = False
    for x, r_ in zip(ddp, v / rm):
        if not inside and x <= -0.2:
            inside = True
        elif inside and x >= 0:
            waves += 1; inside = False
    o["波數"] = waves
    if after:
        hend = cal[h_pos] + pd.DateOffset(months=12)
        he = int(cal.searchsorted(hend, side="right")) - 1
        e = int(np.searchsorted(pos, he, "right")) - 1
        nb = np.flatnonzero(bad[b + 1:e + 1])
        cut = b + int(nb[0]) if len(nb) else e
        if cut > b:
            w = val[b + 1:cut + 1]; jm = int(np.argmin(w))
            o["高點後12月最大跌幅"] = float(w.min() / val[b] - 1)
            o["高點後跌到低點月數"] = (cal[pos[b + 1 + jm]] - cal[pos[b]]).days / 30.44
        full = hend <= cal[cend] and not len(nb) and (pos[e] >= he - ALIVE if e > b else False)
        o["高點後窗"] = "滿" if full else ("遇壞根截" if len(nb) else "未滿12月")
    return o


# ═════════════ 主程式 ═════════════
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    out_dir = a.out; os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    if not os.path.isfile(os.path.join(os.path.dirname(DATA_A), ".done")):
        raise SystemExit("⛔ 快照 A 不在")
    DATA_B = ensure_B()
    log(f"[資料] A {SHA_A[:12]}（月營收、財報、產業別、早年 per）｜B {SHA_B[:12]}（外資持股、燈號、內部人、現增、注意處置、大盤融資、集保、早年上櫃融資、借券）")
    Ze = IMF.build_panel("早年", 2, log); Zm = IMF.build_panel("主", 2, log)
    CAL = Ze["cal"].append(Zm["cal"]); NE = Ze["n0"]; NC = len(CAL); CEND = NC - 1
    cpos_le = lambda ts: int(CAL.searchsorted(pd.Timestamp(ts), side="right")) - 1
    ie = {s: k for k, s in enumerate(Ze["sids"])}; im = {s: k for k, s in enumerate(Zm["sids"])}
    SIDS = sorted(set(ie) | set(im))
    B1 = pd.read_csv(os.path.join(SRC1, "乙_段_x3.csv.gz"), dtype={"代號": str})
    B5n = len(pd.read_csv(os.path.join(SRC1, "乙_段_x5.csv.gz"), usecols=["代號"]))
    GRP = pd.read_csv(os.path.join(SRC2, "族群_段.csv"), dtype={"代號": str})
    if len(GRP) != len(B1) or not (GRP["代號"].values == B1["代號"].values).all() or not (GRP["起點"].values == B1["起點"].values).all():
        raise SystemExit("⛔ 族群_段 與 乙_段_x3 列不對齊")
    B1["族群(切0.7)"] = GRP["群_切0.7"].values
    if a.limit:
        rng = np.random.default_rng(533)
        SIDS = sorted(set(rng.choice(SIDS, a.limit, replace=False)) | {"2330", "2454", "2303", "2603", "2609", "2615", "1513", "1519", "6669", "3017", "2308", "2327"})
        B1 = B1[B1["代號"].isin(SIDS)].reset_index(drop=True)
    N = len(SIDS); IX = {s: i for i, s in enumerate(SIDS)}
    C = np.full((N, NC), np.nan); BAD = np.zeros((N, NC), bool); MC = np.full((N, NC), np.nan); SEAM = {}
    for i, s in enumerate(SIDS):
        if s in ie:
            C[i, :NE] = Ze["C"][ie[s]]; BAD[i, :NE] = Ze["BAD"][ie[s]]; MC[i, :NE] = Ze["MC"][ie[s]]
        if s in im:
            C[i, NE:] = Zm["C"][im[s]]; BAD[i, NE:] = Zm["BAD"][im[s]]; MC[i, NE:] = Zm["MC"][im[s]]
        if s in ie and s in im:
            ve = np.flatnonzero(np.isfinite(C[i, :NE])); vm = np.flatnonzero(np.isfinite(C[i, NE:]))
            if len(ve) and len(vm):
                SEAM[s] = (int(ve[-1]), int(vm[0]) + NE)
    for Z in (Ze, Zm):
        for k in ("C", "BAD", "G", "MC", "TRD", "O", "UPL"):
            Z.pop(k, None)
    _G.update({"NC": NC, "SEAM": SEAM, "MK_E": Ze["mk"], "PARTS": [("早年", Ze["data"], 0, Ze["cal"]), ("主", Zm["data"], NE, Zm["cal"])]})
    AUX = {}
    with Pool(a.procs) as pool:
        for k_, r in enumerate(pool.imap_unordered(aux_job, SIDS, chunksize=8)):
            AUX[r["sid"]] = r
            if (k_ + 1) % 500 == 0:
                log(f"  逐股讀檔 {k_ + 1}／{N}｜{time.time() - t0:.0f}s")
    seam_info = Counter()
    for s, (pe, pm) in SEAM.items():
        i = IX[s]; re_, rm_ = AUX[s]["rc_e"], AUX[s]["rc_m"]
        Mf = C[i, pe] * rm_ / (re_ * C[i, pm]) if (np.isfinite(re_) and np.isfinite(rm_) and re_ > 0 and C[i, pm] > 0) else np.nan
        if np.isfinite(Mf) and Mf > 0:
            C[i, NE:] *= Mf; BAD[i, pm] = (pm - pe - 1) >= 5
        else:
            BAD[i, pm] = True
        seam_info["兩世界都有"] += 1; seam_info["接縫壞根"] += int(BAD[i, pm])
    log(f"[接縫] {dict(seam_info)}")
    stack = lambda k, dt=np.float32: np.stack([AUX[s][k] for s in SIDS]).astype(dt)
    RC, VOL, AMT, SH, PER, PBR, MBAL, INST = (stack(k) for k in ("rc", "vol", "amt", "sh", "per", "pbr", "mbal", "inst"))
    INSTCOV = np.array([AUX[s]["inst_cov"] for s in SIDS]); NAME = {s: AUX[s]["name"] for s in SIDS}
    # ★ 股數缺（早年 stocks.csv 的 shares 常空白）⇒ 用面板市值 ÷ 同日原始收盤補（面板早年市值來自 daily_all 的 close × shares，同源），再往後延用
    with np.errstate(invalid="ignore", divide="ignore"):
        est = np.where(np.isfinite(MC) & np.isfinite(RC) & (RC > 0), MC / RC, np.nan)
    need = ~np.isfinite(SH) & np.isfinite(est)
    n_fill = int(need.sum())
    SH = pd.DataFrame(np.where(np.isfinite(SH), SH, est)).ffill(axis=1).to_numpy(np.float32)
    log(f"[股數] 由面板市值 ÷ 原始收盤補 {n_fill} 個股日")
    del AUX
    ids = set(SIDS)
    # 早年 per／pbr（上市＋上櫃日檔，快照 A）
    ep = load_daily_dir(sorted(glob.glob(os.path.join(DATA_A, "early", "per", "*.csv"))) + sorted(glob.glob(os.path.join(DATA_A, "early", "otcper", "*.csv"))),
                        ["per", "pbr"], ids, CAL)
    pi = Ze["cal"].get_indexer(pd.to_datetime(ep["date"])); okp = pi >= 0
    rows_ = np.array([IX[s] for s in ep["stock_id"]])
    for k, arr in (("per", PER), ("pbr", PBR)):
        v = pd.to_numeric(ep[k], errors="coerce").to_numpy(float); m_ = okp & (v > 0)
        arr[rows_[m_], pi[m_]] = v[m_]
    # 早年上櫃融資、借券（快照 B）
    em = load_daily_dir(sorted(glob.glob(os.path.join(DATA_B, "early", "otcmargin", "*.csv"))), ["m_balance"], ids, CAL)
    pi = Ze["cal"].get_indexer(pd.to_datetime(em["date"])); okp = pi >= 0
    MBAL[np.array([IX[s] for s in em["stock_id"]])[okp], pi[okp]] = pd.to_numeric(em["m_balance"], errors="coerce").to_numpy(float)[okp]
    SBL = np.full((N, NC), np.nan, np.float32)
    sb = load_daily_dir(sorted(glob.glob(os.path.join(DATA_B, "universe", "sbl", "*.csv"))) + sorted(glob.glob(os.path.join(DATA_B, "universe", "otcsbl", "*.csv"))),
                        ["sbl_balance"], ids, CAL)
    pi = Zm["cal"].get_indexer(pd.to_datetime(sb["date"])); okp = pi >= 0
    SBL[np.array([IX[s] for s in sb["stock_id"]])[okp], pi[okp] + NE] = pd.to_numeric(sb["sbl_balance"], errors="coerce").to_numpy(float)[okp]
    log(f"[讀檔] 早年 per {len(ep)}、早年上櫃融資 {len(em)}、借券 {len(sb)} 列｜{time.time() - t0:.0f}s")
    del ep, em, sb
    # 集保（千張以上，level 15）
    TDCC = np.full((N, NC), np.nan, np.float32)
    for f in sorted(glob.glob(os.path.join(DATA_B, "tdcc_hist", "*.parquet"))):
        x = pd.read_parquet(f, columns=["date", "stock_id", "level", "pct"])
        x = x[(x["level"] == 15)]; x["stock_id"] = x["stock_id"].astype(str); x = x[x["stock_id"].isin(ids)]
        pi = CAL.searchsorted(pd.to_datetime(x["date"].astype(str))); okp = pi < NC     # ★ 資料日非交易日 ⇒ 記在其後第一個交易日
        TDCC[np.array([IX[s] for s in x["stock_id"]], dtype=np.int64)[okp], pi[okp]] = x["pct"].to_numpy(float)[okp]
    # 外資持股月表
    FH = np.full((N, NC), np.nan, np.float32)
    for f in sorted(glob.glob(os.path.join(DATA_B, "meta", "foreign_holding", "foreign_holding_*.csv"))):
        x = pd.read_csv(f, dtype={"stock_id": str, "date": str}, usecols=["date", "stock_id", "foreign_pct"])
        x = x[x["stock_id"].isin(ids)]
        pi = CAL.get_indexer(pd.to_datetime(x["date"])); okp = pi >= 0
        FH[np.array([IX[s] for s in x["stock_id"]], dtype=np.int64)[okp], pi[okp]] = pd.to_numeric(x["foreign_pct"], errors="coerce").to_numpy(float)[okp]
    # 事件累計（注意、處置、內部人、現增可轉債）
    def cum_events(dates_by_sid, weights=None):
        out = np.zeros((N, NC), np.float32)
        for s, dl in dates_by_sid.items():
            if s not in IX:
                continue
            dt = pd.to_datetime(pd.Series(dl[0]), errors="coerce"); okd = dt.notna().to_numpy()
            pos = CAL.searchsorted(dt[okd])                          # 事件日當天或之後第一個交易日
            v = np.zeros(NC + 1)
            np.add.at(v, np.minimum(pos, NC), np.asarray(dl[1], float)[okd])
            out[IX[s]] = np.cumsum(v[:NC])
        return out
    at = pd.read_csv(os.path.join(DATA_B, "meta", "attention.csv"), dtype={"stock_id": str}, usecols=["stock_id", "date"])
    CATT = cum_events({s: (g["date"].values, np.ones(len(g))) for s, g in at.groupby("stock_id")})
    di = pd.read_csv(os.path.join(DATA_B, "meta", "disposal.csv"), dtype={"stock_id": str}, usecols=["stock_id", "announce_date"])
    CDIS = cum_events({s: (g["announce_date"].values, np.ones(len(g))) for s, g in di.groupby("stock_id")})
    L = []
    for f in sorted(glob.glob(os.path.join(DATA_B, "meta", "insider_predeclare", "insider_predeclare_*.csv"))):
        L.append(pd.read_csv(f, dtype={"stock_id": str}, usecols=["declare_date", "stock_id", "shares", "plan_own", "plan_trust"]))
    ins = pd.concat(L, ignore_index=True)
    sh_ = pd.to_numeric(ins["shares"], errors="coerce")
    alt = pd.to_numeric(ins["plan_own"], errors="coerce").fillna(0) + pd.to_numeric(ins["plan_trust"], errors="coerce").fillna(0)
    ins["w"] = sh_.where(sh_.notna(), alt).fillna(0)
    CINSr = cum_events({s: (g["declare_date"].values, g["w"].to_numpy(float)) for s, g in ins.groupby("stock_id")})
    se = pd.read_csv(os.path.join(DATA_B, "meta", "seo_cb_events", "seo_cb_events.csv"), dtype={"stock_id": str}, usecols=["date", "stock_id", "ipo"])
    se = se[pd.to_numeric(se["ipo"], errors="coerce").fillna(0) == 0]
    CSEO = cum_events({s: (g["date"].values, np.ones(len(g))) for s, g in se.groupby("stock_id")})
    CINST = np.cumsum(INST, axis=1, dtype=np.float64)
    log(f"[事件] 注意 {len(at)}、處置 {len(di)}、內部人 {len(ins)}、現增可轉債(非 ipo) {len(se)}｜{time.time() - t0:.0f}s")
    # 有效 K 棒、日報酬
    VP, VC, VB = [], [], []
    RR = np.zeros((N, NC)); LASTV = np.full((N, NC), -1, np.int32)
    for i in range(N):
        vp = np.flatnonzero(np.isfinite(C[i])); vc = C[i, vp]; vb = BAD[i, vp].copy()
        if len(vp) > 1:
            r = vc[1:] / vc[:-1] - 1.0; r[vb[1:]] = 0.0; RR[i, vp[1:]] = r
        ar = np.full(NC, -1, np.int32); ar[vp] = vp; LASTV[i] = np.maximum.accumulate(ar)
        VP.append(vp); VC.append(vc); VB.append(vb)
    # 0050、全市場等權
    B50 = {}
    for wn, Z in (("早年", Ze), ("主", Zm)):
        D.DATA = Z["data"]; B50[wn] = R.load_bars("0050", "twse", Z["cal"])
    idx50 = np.concatenate([B50["早年"]["idx"].astype(np.int64), B50["主"]["idx"].astype(np.int64) + NE])
    c50 = np.concatenate([B50["早年"]["c"], B50["主"]["c"]]).astype(float); rc50 = np.concatenate([B50["早年"]["rc"], B50["主"]["rc"]]).astype(float)
    j50 = len(B50["早年"]["idx"]); c50[j50:] *= c50[j50 - 1] * rc50[j50] / (rc50[j50 - 1] * c50[j50])
    v50 = lambda p: c50[int(np.searchsorted(idx50, p, "right")) - 1]
    ym = CAL.year * 12 + CAL.month
    mstart = np.flatnonzero(np.r_[True, ym[1:] != ym[:-1]]); mend = np.r_[mstart[1:] - 1, NC - 1]
    MONTHS = [(int(mstart[k] - 1), int(mend[k])) for k in range(1, len(mstart))]
    rev, rev_ly, cat, _, _, _ = PRE.load_rev(DATA_A)
    PIT = PRE.PIT(DATA_A, cat)
    MEMB = []; MKTM = []
    for (b, e) in MONTHS:
        lv = LASTV[:, b]; alive = (lv >= 0) & (b - lv <= ALIVE)
        MKTM.append(np.flatnonzero(alive))
        mm = defaultdict(list)
        for i in np.flatnonzero(alive & np.isfinite(MC[:, b]) & (MC[:, b] > 0)):
            ind, _ = PIT.at(SIDS[i], CAL[b])
            if ind is not None and ind not in EXCL_IND:
                mm[ind].append(i)
        MEMB.append({k: np.array(v, np.int64) for k, v in mm.items()})
    INDS = sorted({k for m in MEMB for k in m})
    IDX = {kd: {ind: np.full(NC, np.nan) for ind in INDS} for kd in ("vw", "ew")}
    CH = {kd: {ind: np.full(NC, -1, np.int64) for ind in INDS} for kd in ("vw", "ew")}
    IM = np.full(NC, np.nan); chain_no = 0
    for mi, (b, e) in enumerate(MONTHS):
        Gm = np.cumprod(1.0 + RR[:, b + 1:e + 1], axis=1)
        mk = MKTM[mi]
        if len(mk):
            if not np.isfinite(IM[b]):
                IM[b] = 1.0
            IM[b + 1:e + 1] = IM[b] * Gm[mk].mean(0)
        for ind, idxs in MEMB[mi].items():
            if len(idxs) < 5:
                continue
            for kd in ("vw", "ew"):
                W0 = MC[idxs, b] if kd == "vw" else np.ones(len(idxs))
                V = (W0[:, None] * Gm[idxs]).sum(0) / W0.sum()
                I_ = IDX[kd][ind]; H_ = CH[kd][ind]
                if not np.isfinite(I_[b]):
                    chain_no += 1; I_[b] = 1.0; H_[b] = chain_no
                I_[b + 1:e + 1] = I_[b] * V; H_[b + 1:e + 1] = H_[b]
    log(f"[指數] 產業 {len(INDS)}、鏈 {chain_no}｜{time.time() - t0:.0f}s")
    # 月營收
    rd = pd.read_csv(os.path.join(DATA_A, "meta", "revenue_delisted", "revenue_delisted.csv"), dtype=str)
    rd["v"] = pd.to_numeric(rd["revenue_k"], errors="coerce")
    rdp = rd.pivot_table(index="period", columns="stock_id", values="v", aggfunc="last")
    for s in rdp.columns:
        if s not in rev.columns:
            rev[s] = np.nan; rev_ly[s] = np.nan
        for p_, v in rdp[s].dropna().items():
            if p_ in rev.index and not np.isfinite(rev.at[p_, s]):
                rev.at[p_, s] = v; p12 = PRE.mshift(p_, -12)
                if p12 in rdp.index and np.isfinite(rdp.at[p12, s]):
                    rev_ly.at[p_, s] = rdp.at[p12, s]
                elif p12 in rev.index:
                    rev_ly.at[p_, s] = rev.at[p12, s]
    PERIODS = list(rev.index)
    AVR = np.array([np.datetime64(LP.rev_avail(p_)) for p_ in PERIODS], "datetime64[ns]")
    REVA = {s: rev[s].to_numpy(float) for s in rev.columns if s in ids}; LYA = {s: rev_ly[s].to_numpy(float) for s in rev.columns if s in ids}
    Q, KS = build_quarterly(DATA_A, SIDS)
    log(f"[財報] {len(Q)} 檔｜{time.time() - t0:.0f}s")
    ME, _ = PF.month_ends(CAL); MEp = np.asarray(ME, np.int64); K = len(MEp)
    KM = np.array([int(np.searchsorted(AVR, np.datetime64(CAL[p]), "left")) - 1 for p in MEp])
    CENS = {pd.Timestamp("2004-02-11"), pd.Timestamp("2007-07-02")}
    _G.update({"SIDS": SIDS, "MEp": MEp, "CAL": CAL, "VP": VP, "VC": VC, "VB": VB, "RC": RC, "VOL": VOL, "AMT": AMT, "SH": SH, "PER": PER, "PBR": PBR,
               "MBAL": MBAL, "SBL": SBL, "TDCC": TDCC, "FH": FH, "CENS": CENS, "Q": Q, "KS": KS, "REVA": REVA, "LYA": LYA, "KM": KM, "LASTOK": lastok,
               "CINST": CINST, "INSTCOV": INSTCOV, "CATT": CATT, "CDIS": CDIS, "CINS": CINSr, "CSEO": CSEO})
    P = {k: np.full((N, K), np.nan, np.float32) for k, _ in LV}
    CU = {k: np.full((N, K), np.nan) for k, _ in CUMS}
    META = {k: None for k in ("rev_per", "fs_qk", "fs_av")}
    META = {"rev_per": np.full((N, K), -1, np.int32), "fs_qk": np.full((N, K), -1, np.int32), "fs_av": np.full((N, K), -1, np.int64)}
    SHK = np.full((N, K), np.nan)
    with Pool(a.procs) as pool:
        for k_, (i, o, cu, me) in enumerate(pool.imap_unordered(panel_job, range(N), chunksize=4)):
            for k, _ in LV:
                P[k][i] = o[k]
            for k, _ in CUMS:
                CU[k][i] = cu[k]
            for k in META:
                META[k][i] = me[k]
            SHK[i] = o["_shares"]
            if (k_ + 1) % 500 == 0:
                log(f"  月底面板 {k_ + 1}／{N}｜{time.time() - t0:.0f}s")
    # 產業內市值排名、月底產業別
    INDM = np.full((N, K), "", dtype=object)
    ALV = np.isfinite(P["市值(億)"])
    for k in range(K):
        p = int(MEp[k]); d = CAL[p]
        byind = defaultdict(list)
        for i in np.flatnonzero(ALV[:, k]):
            ind, _ = PIT.at(SIDS[i], d)
            if ind is not None and ind not in EXCL_IND:
                INDM[i, k] = ind; byind[ind].append(i)
        for ind, mem in byind.items():
            mv = P["市值(億)"][mem, k]; order = np.argsort(-mv)
            rk = np.empty(len(mem)); rk[order] = np.arange(1, len(mem) + 1)
            P["產業內市值排名百分位"][mem, k] = rk / len(mem)
    # 市場層
    ndc = pd.read_csv(os.path.join(DATA_B, "meta", "ndc_signal", "ndc_signal.csv"), dtype={"period": str})
    ndcm = dict(zip(ndc["period"], pd.to_numeric(ndc["signal_score"], errors="coerce")))
    mm_ = []
    for sub in ("early", "universe"):
        for f in sorted(glob.glob(os.path.join(DATA_B, sub, "marginmkt", "*.csv"))):
            x = pd.read_csv(f, dtype=str)
            v = x.loc[x["item"].astype(str).str.startswith("融資(交易單位)"), "balance"]
            if len(v):
                mm_.append((x["date"].iloc[0], float(v.iloc[0])))
    mms = pd.Series({pd.Timestamp(d_): v for d_, v in mm_}).sort_index().reindex(CAL).ffill(limit=5)
    MK = {k: np.full(K, np.nan) for k in MKT}
    for k in range(K):
        p = int(MEp[k]); d = CAL[p]
        pm_ = f"{(d - pd.offsets.MonthBegin(1)).year:04d}-{(d - pd.offsets.MonthBegin(1)).month:02d}"
        MK["景氣信號分數(修正後)"][k] = ndcm.get(pm_, np.nan)
        MK["大盤融資餘額(萬張)"][k] = mms.iloc[p] / 1e4 if np.isfinite(mms.iloc[p]) else np.nan
        kk = int(np.searchsorted(idx50, p, "right")) - 1
        if kk >= 199:
            MK["0050乖離200日"][k] = c50[kk] / c50[kk - 199:kk + 1].mean() - 1
        lo = int(np.searchsorted(idx50, p - 249, "left")); w = c50[lo:kk + 1]
        MK["0050前12月最大回落"][k] = float((w / np.maximum.accumulate(w) - 1).min()) if len(w) and p - 249 >= idx50[0] else np.nan
        w = IM[max(p - 249, 0):p + 1]; w = w[np.isfinite(w)]
        MK["全市場等權前12月最大回落"][k] = float((w / np.maximum.accumulate(w) - 1).min()) if len(w) >= 200 else np.nan
    MK["大盤融資12月變化"][12:] = MK["大盤融資餘額(萬張)"][12:] / MK["大盤融資餘額(萬張)"][:-12] - 1
    log(f"[面板] 個股 {N}×{K}｜{time.time() - t0:.0f}s")
    kofp = lambda p: int(np.searchsorted(MEp, p, "right")) - 1     # 位置 p 當天或之前最後一個月底序

    # ═════════ 個股段的點、區間 ═════════
    def pts_of(ks, kh):
        return {nm: (ks if base == "s" else kh) + off for nm, (base, off) in PTOFF.items()}

    def winval(i, nm, k1, k2):
        if k1 < 0 or k2 >= K or k2 <= k1:
            return np.nan
        a_, b_ = CU[nm][i, k1], CU[nm][i, k2]
        if not (np.isfinite(a_) and np.isfinite(b_)):
            return np.nan
        v = b_ - a_
        if nm.endswith("÷股數"):
            shp = SHK[i, k2]
            return v / shp if np.isfinite(shp) and shp > 0 else np.nan
        return v

    def stock_unit_vals(i, P_):
        o = {}
        for nm, k in P_.items():
            ok = 0 <= k < K
            for f, _ in LV:
                o[f"{f}@{nm}"] = float(P[f][i, k]) if ok else np.nan
            for f in MKT:
                o[f"{f}@{nm}"] = float(MK[f][k]) if ok else np.nan
        for wn, (x, y) in WINS.items():
            for f, _ in CUMS:
                o[f"{f}@{wn}"] = winval(i, f, P_[x], P_[y])
        return o

    # 乙
    seg_rows = []; SEGPOS = defaultdict(list)
    for r_i, r in B1.iterrows():
        i = IX[r["代號"]]; ps = cpos_le(r["起點"]); ph = cpos_le(r["高點"])
        ks = kofp(cpos_le(r["起點月底"])); kh = kofp(ph)
        SEGPOS[i].append((ps, ph))
        P_ = pts_of(ks, kh)
        rec = {"代號": r["代號"], "名稱": r["名稱"], "起點": r["起點"], "高點": r["高點"], "倍數": r["倍數"], "產業(起點PIT)": r["產業(起點PIT)"],
               "族群(切0.7)": int(r["族群(切0.7)"]), "_i": i, **{f"_k{nm}": k for nm, k in P_.items()}}
        sh_ = shape_path(VP[i], VC[i], VB[i], ps, ph, CAL, CEND)
        # 對照 D
        b = int(np.searchsorted(VP[i], ph, "right")) - 1
        hend = CAL[ph] + pd.DateOffset(months=12); he = cpos_le(hend); e = int(np.searchsorted(VP[i], he, "right")) - 1
        nb = np.flatnonzero(VB[i][b + 1:e + 1]); cut = b + int(nb[0]) if len(nb) else e
        crashed = cut > b and VC[i][b + 1:cut + 1].min() <= 0.5 * VC[i][b]
        delisted = VP[i][-1] < he and VP[i][-1] < CEND - 5
        full = hend <= CAL[-1] and not len(nb) and not delisted
        rec["對照D"] = "崩" if crashed else ("下市" if delisted else ("未崩" if full else ("遇壞根截" if len(nb) else "未定")))
        rec.update({f"⑩{k}": v for k, v in sh_.items()})
        rec.update(stock_unit_vals(i, P_))
        seg_rows.append(rec)
    YI = pd.DataFrame(seg_rows)
    log(f"[乙] {len(YI)} 段｜D 崩 {int((YI['對照D'] == '崩').sum()) if len(YI) else 0}｜{time.time() - t0:.0f}s")

    # ═════════ 對照 B（乙）═════════
    BF = [("前3年報酬", "前3年報酬@起點"), ("距一年高點", "距一年高點@起點"), ("月營收年增", "月營收年增@起點"), ("log市值", None), ("60日周轉率", "60日周轉率@起點")]
    IQR = {}
    for f, col in BF:
        v = np.log(YI["市值(億)@起點"].to_numpy(float)) if f == "log市值" else YI[col].to_numpy(float)
        st = qstat(v); IQR[f] = (st["p25"], st["p75"])
    with np.errstate(divide="ignore", invalid="ignore"):
        LMC = np.log(P["市值(億)"])
    inb = np.ones((N, K), bool)
    for f, col in BF:
        x = LMC if f == "log市值" else P[f]
        lo, hi = IQR[f]
        inb &= np.isfinite(x) & (x >= lo) & (x <= hi)
    BROWS = []
    for i in range(N):
        vp, vc, vb = VP[i], VC[i], VB[i]
        nxt = -1
        for k in np.flatnonzero(inb[i]):
            if k < nxt:
                continue
            p = int(MEp[k]); kk = int(np.searchsorted(vp, p, "right")) - 1
            prev = int(MEp[k - 1]) if k > 0 else -1
            if kk < 0 or vp[kk] <= prev:
                continue
            ps = int(vp[kk])
            if any(a_ <= ps <= b_ for a_, b_ in SEGPOS.get(i, [])):
                continue
            endt = CAL[ps] + pd.DateOffset(years=3)
            if endt > CAL[-1]:
                continue
            ep_ = cpos_le(endt); e = int(np.searchsorted(vp, ep_, "right")) - 1
            if vp[-1] < ep_ - ALIVE or e <= kk or vb[kk + 1:e + 1].any():
                continue
            w = vc[kk + 1:e + 1]
            if w.max() >= 3 * vc[kk]:
                continue
            r3 = vc[e] / vc[kk] - 1; r50 = v50(ep_) / v50(ps) - 1
            if not r3 < r50:
                continue
            hk = kk + 1 + int(np.argmax(w)); ph = int(vp[hk])
            P_ = pts_of(k, kofp(ph))
            rec = {"代號": SIDS[i], "名稱": NAME.get(SIDS[i], ""), "起點": str(CAL[ps].date()), "高點(窗內最高)": str(CAL[ph].date()),
                   "窗內最高倍數": float(w.max() / vc[kk]), "3年報酬": float(r3), "0050同窗": float(r50), "產業(起點PIT)": PIT.at(SIDS[i], CAL[ps])[0] or "無類別",
                   "_i": i, **{f"_k{nm}": kk_ for nm, kk_ in P_.items()}}
            rec.update({f"⑩{k_}": v for k_, v in shape_path(vp, vc, vb, ps, ph, CAL, CEND).items()})
            rec.update(stock_unit_vals(i, P_))
            BROWS.append(rec); nxt = k + 36
    BI = pd.DataFrame(BROWS)
    log(f"[對照B 乙] {len(BI)} 筆、{BI['代號'].nunique() if len(BI) else 0} 檔｜IQR {IQR}｜{time.time() - t0:.0f}s")

    # ═════════ 產業面板（甲）═════════
    stockF = [f for f, _ in LV]
    IP = {ind: {f: np.full(K, np.nan) for f in stockF + ["營收年增(加總)", "成員數"]} for ind in INDS}
    for k in range(K):
        byind = defaultdict(list)
        for i in np.flatnonzero(INDM[:, k] != ""):
            byind[INDM[i, k]].append(i)
        km = int(KM[k])
        for ind, mem in byind.items():
            if ind not in IP:
                continue
            mem = np.array(mem); IP[ind]["成員數"][k] = len(mem)
            for f in stockF:
                v = P[f][mem, k]; v = v[np.isfinite(v)]
                if len(v):
                    IP[ind][f][k] = float(v.mean()) if f in FLAGS else float(np.median(v))
            sv = sl = 0.0
            for i in mem:
                rp = META["rev_per"][i, k]; s = SIDS[i]
                if rp >= 0 and s in REVA:
                    v, l = REVA[s][rp], LYA[s][rp]
                    if np.isfinite(v) and np.isfinite(l) and l > 0:
                        sv += v; sl += l
            IP[ind]["營收年增(加總)"][k] = sv / sl - 1 if sl > 0 else np.nan
    IPX = {kd: {ind: {f: np.full(K, np.nan) for f in IDXF} for ind in INDS} for kd in ("vw", "ew")}
    for kd in ("vw", "ew"):
        for ind in INDS:
            I_, H_ = IDX[kd][ind], CH[kd][ind]
            for k in range(K):
                p = int(MEp[k])
                if H_[p] < 0:
                    continue
                lo = max(0, p - 249); w = I_[lo:p + 1][H_[lo:p + 1] == H_[p]]
                IPX[kd][ind]["距一年高點"][k] = I_[p] / w.max() - 1
                lo = max(0, p - 1249); w = I_[lo:p + 1][H_[lo:p + 1] == H_[p]]
                IPX[kd][ind]["距5年低點"][k] = I_[p] / w.min() - 1
                if k >= 36:
                    p3 = int(MEp[k - 36])
                    if H_[p3] == H_[p]:
                        IPX[kd][ind]["前3年報酬"][k] = I_[p] / I_[p3] - 1
    log(f"[產業面板] {len(INDS)} 產業｜{time.time() - t0:.0f}s")

    def ind_val(kd, ind, f, k):
        if not (0 <= k < K):
            return np.nan
        if f in IDXF:
            return IPX[kd][ind][f][k]
        if f in MKT:
            return MK[f][k]
        return IP[ind][f][k] if ind in IP else np.nan

    def ind_win(ind, f, k1, k2):
        if k1 < 0 or k2 >= K or k2 <= k1:
            return np.nan
        mem = np.flatnonzero(INDM[:, k2] == ind)
        v = np.array([winval(i, f, k1, k2) for i in mem]); v = v[np.isfinite(v)]
        return float(np.median(v)) if len(v) else np.nan

    INDF = ["營收年增(加總)", "成員數"] + stockF
    def ind_unit_vals(kd, ind, P_):
        o = {}
        for nm, k in P_.items():
            for f in INDF + list(MKT):
                o[f"{f}@{nm}"] = ind_val(kd, ind, f, k)
            for f in IDXF:
                o[f"指數{f}@{nm}"] = ind_val(kd, ind, f, k)
        for wn, (x, y) in WINS.items():
            for f, _ in CUMS:
                o[f"{f}@{wn}"] = ind_win(ind, f, P_[x], P_[y])
        return o

    def ind_shape(kd, ind, S, H):
        I_, H_ = IDX[kd][ind], CH[kd][ind]
        lo = S; hi = min(CEND, cpos_le(CAL[H] + pd.DateOffset(months=12)))
        pos = np.arange(lo, hi + 1); pos = pos[H_[pos] == H_[S]]
        return shape_path(pos, I_[pos], np.zeros(len(pos), bool), S, H, CAL, CEND)

    S1 = pd.read_csv(os.path.join(SRC1, "甲_段.csv")); S2 = pd.read_csv(os.path.join(SRC2, "甲補充_段.csv"))
    VERS = {"原版市值": (S1[S1["加權"] == "市值"], "vw", "0050"), "原版等權": (S1[S1["加權"] == "等權"], "ew", "0050"),
            "補充市值": (S2[S2["加權"] == "市值"], "vw", "mkt"), "補充等權": (S2[S2["加權"] == "等權"], "ew", "mkt")}
    JROWS = []; JB = []; JC = []
    for vn, (SG, kd, bench) in VERS.items():
        segs_by = defaultdict(list)
        for _, r in SG.iterrows():
            if r["產業"] not in IDX[kd]:
                if not a.limit:
                    raise SystemExit(f"⛔ 甲段產業 {r['產業']} 不在本次產業清單")
                continue                                   # 乾跑子樣本才可能缺
            S = cpos_le(r["起點"]); H = cpos_le(r["高點"])
            segs_by[r["產業"]].append((S, H))
            P_ = pts_of(kofp(S), kofp(H))
            rec = {"版": vn, "段號": r["段號"], "產業": r["產業"], "起點": r["起點"], "高點": r["高點"], "漲幅": r["漲幅"], "_ind": r["產業"],
                   **{f"_k{nm}": k for nm, k in P_.items()}}
            rec.update({f"⑩{k}": v for k, v in ind_shape(kd, r["產業"], S, H).items()})
            rec.update(ind_unit_vals(kd, r["產業"], P_))
            JROWS.append(rec)
        # 對照 B（甲）
        JF = [("指數前3年報酬@起點", "前3年報酬"), ("指數距一年高點@起點", "距一年高點"), ("營收年增(加總)@起點", "營收年增(加總)")]
        mine = [x for x in JROWS if x["版"] == vn]
        iq = {c: (qstat([x[c] for x in mine])["p25"], qstat([x[c] for x in mine])["p75"]) for c, _ in JF}
        for ind in INDS:
            I_, H_ = IDX[kd][ind], CH[kd][ind]; nxt = -1
            for k in range(K - 36):
                if k < nxt:
                    continue
                p = int(MEp[k]); p36 = int(MEp[k + 36])
                if H_[p] < 0 or H_[p] != H_[p36]:
                    continue
                vals = [ind_val(kd, ind, f, k) for _, f in JF]
                if not all(np.isfinite(v) and iq[c][0] <= v <= iq[c][1] for (c, _), v in zip(JF, vals)):
                    continue
                if any(a_ <= p <= b_ for a_, b_ in segs_by.get(ind, [])):
                    continue
                r3 = I_[p36] / I_[p] - 1
                rb = (v50(p36) / v50(p) - 1) if bench == "0050" else (IM[p36] / IM[p] - 1)
                if not r3 < rb:
                    continue
                ph = p + int(np.argmax(I_[p:p36 + 1]))
                P_ = pts_of(k, kofp(ph))
                rec = {"版": vn, "產業": ind, "起點": str(CAL[p].date()), "高點(窗內最高)": str(CAL[ph].date()), "3年報酬": r3, "基準同窗": rb,
                       "_ind": ind, **{f"_k{nm}": kk_ for nm, kk_ in P_.items()}}
                rec.update({f"⑩{k_}": v for k_, v in ind_shape(kd, ind, p, ph).items()})
                rec.update(ind_unit_vals(kd, ind, P_))
                JB.append(rec); nxt = k + 36
        # 對照 C
        jst = int(np.searchsorted(CAL[MEp], pd.Timestamp("2004-12-31"), "left"))
        for ind in INDS:
            I_, H_ = IDX[kd][ind], CH[kd][ind]
            js = []
            for j in range(jst + 36, K):
                pa, pt = int(MEp[j - 36]), int(MEp[j])
                if H_[pa] >= 0 and H_[pa] == H_[pt] and 0.5 <= I_[pt] / I_[pa] - 1 < 1.0:
                    js.append(j)
            grp = []
            for j in js:
                if grp and j - 36 <= grp[-1][-1]:
                    grp[-1].append(j)
                else:
                    grp.append([j])
            for gg in grp:
                S = int(MEp[gg[0] - 36]); E = int(MEp[gg[-1]])
                if any(a_ <= E and S <= b_ for a_, b_ in segs_by.get(ind, [])):
                    continue
                H = S + int(np.nanargmax(I_[S:E + 1]))
                shp = ind_shape(kd, ind, S, H)
                if not (np.isfinite(shp["高點後12月最大跌幅"]) and shp["高點後12月最大跌幅"] <= -0.2):
                    continue
                P_ = pts_of(kofp(S), kofp(H))
                rec = {"版": vn, "產業": ind, "起點": str(CAL[S].date()), "高點": str(CAL[H].date()), "漲幅": I_[H] / I_[S] - 1, "窗數": len(gg), "_ind": ind,
                       **{f"_k{nm}": kk_ for nm, kk_ in P_.items()}}
                rec.update({f"⑩{k_}": v for k_, v in shp.items()})
                rec.update(ind_unit_vals(kd, ind, P_))
                JC.append(rec)
    JA = pd.DataFrame(JROWS); JBd = pd.DataFrame(JB); JCd = pd.DataFrame(JC)
    log(f"[甲] 段 {len(JA)}、對照B {len(JBd)}、對照C {len(JCd)}｜{time.time() - t0:.0f}s")

    # ═════════ 並排表 ═════════
    XC = {}

    def cross_stock(f, k, excl=None):
        """★ 同月全部個股（含該段自己；3 千段裡影響可忽略）已排序的有值陣列（快取）。"""
        if f in MKT:
            return None
        if (f, k) not in XC:
            v = P[f][:, k].astype(float); XC[(f, k)] = np.sort(v[np.isfinite(v)])
        return XC[(f, k)]
    WC = {}

    def cross_win(f, k1, k2):
        if (f, k1, k2) not in WC:
            v = CU[f][:, k2] - CU[f][:, k1]
            if f.endswith("÷股數"):
                v = v / SHK[:, k2]
            WC[(f, k1, k2)] = np.sort(v[np.isfinite(v)])
        return WC[(f, k1, k2)]

    def prc(x, arr):
        if arr is None or not np.isfinite(x) or not len(arr):
            return np.nan
        lo = np.searchsorted(arr, x, "left"); hi = np.searchsorted(arr, x, "right")
        return float((lo + 0.5 * (hi - lo)) / len(arr))

    def side_stock(G1, label_sets):
        rows = []
        feats = [(f, c) for f, c in LV] + [(f, "⑨") for f in MKT]
        for f, cat_ in feats:
            for nm in PTS:
                col = f"{f}@{nm}"
                row = {"類": cat_, "欄": f, "時點": nm}
                for gname, df in label_sets.items():
                    st = fstat(f, df[col]) if len(df) else qstat([])
                    row.update({f"{gname}_n": st["n"], f"{gname}_中位": st["中位"], f"{gname}_p25": st["p25"], f"{gname}_p75": st["p75"]})
                if f not in MKT and len(G1):
                    med = []; pr = []
                    for k, x in zip(G1[f"_k{nm}"].to_numpy(int), G1[col].to_numpy(float)):
                        if not 0 <= k < K:
                            continue
                        arr = cross_stock(f, int(k))
                        if arr is not None and len(arr):
                            med.append(float(arr.mean()) if f in FLAGS else float(np.median(arr)))
                            if f not in FLAGS:
                                pr.append(prc(x, arr))
                    row["A_同月他股中位"] = float(np.median(med)) if med else np.nan
                    row["乙在同月百分位中位"] = float(np.nanmedian(pr)) if pr and np.isfinite(pr).any() else np.nan
                rows.append(row)
        for f, cat_ in CUMS:
            for wn, (x, y) in WINS.items():
                col = f"{f}@{wn}"
                row = {"類": cat_, "欄": f, "時點": wn}
                for gname, df in label_sets.items():
                    st = qstat(df[col]) if len(df) else qstat([])
                    row.update({f"{gname}_n": st["n"], f"{gname}_中位": st["中位"], f"{gname}_p25": st["p25"], f"{gname}_p75": st["p75"]})
                med = []; pr = []
                for k1, k2, xv in zip(G1[f"_k{x}"].to_numpy(int), G1[f"_k{y}"].to_numpy(int), G1[col].to_numpy(float)):
                    if not (0 <= k1 < k2 < K):
                        continue
                    arr = cross_win(f, int(k1), int(k2))
                    if len(arr):
                        med.append(float(np.median(arr))); pr.append(prc(xv, arr))
                row["A_同月他股中位"] = float(np.median(med)) if med else np.nan
                row["乙在同月百分位中位"] = float(np.nanmedian(pr)) if np.isfinite(pr).any() else np.nan
                rows.append(row)
        for f in ("起點→高點月數", "段中最大回檔", "波數", "高點後12月最大跌幅", "高點後跌到低點月數"):
            row = {"類": "⑩", "欄": f, "時點": "段"}
            for gname, df in label_sets.items():
                st = qstat(df[f"⑩{f}"]) if len(df) else qstat([])
                row.update({f"{gname}_n": st["n"], f"{gname}_中位": st["中位"], f"{gname}_p25": st["p25"], f"{gname}_p75": st["p75"]})
            rows.append(row)
        return pd.DataFrame(rows)

    SIDE = []
    era = lambda df, col="起點": pd.to_datetime(df[col]).dt.year if len(df) else pd.Series([], dtype=int)
    for er, (y0, y1) in {"全期": (2004, 2100), "2005～2014": (2004, 2014), "2015～": (2015, 2100)}.items():
        g1 = YI[(era(YI) >= y0) & (era(YI) <= y1)] if len(YI) else YI
        gb = BI[(era(BI) >= y0) & (era(BI) <= y1)] if len(BI) else BI
        t_ = side_stock(g1, {"乙": g1, "B": gb, "D崩": g1[g1["對照D"] == "崩"] if len(g1) else g1,
                             "乙非D": g1[g1["對照D"] == "未崩"] if len(g1) else g1})
        t_.insert(0, "起點期", er); SIDE.append(t_)
    SIDE = pd.concat(SIDE, ignore_index=True)

    # 甲並排
    def side_ind(vn):
        GA = JA[JA["版"] == vn] if len(JA) else JA; GB = JBd[JBd["版"] == vn] if len(JBd) else JBd; GC = JCd[JCd["版"] == vn] if len(JCd) else JCd
        kd = VERS[vn][1]
        rows = []
        cols = [(f, "") for f in INDF] + [(f"指數{f}", "⑦") for f in IDXF] + [(f, "⑨") for f in MKT]
        for f, _ in cols:
            for nm in PTS:
                col = f"{f}@{nm}"; row = {"版": vn, "欄": f, "時點": nm}
                for gname, df in (("甲", GA), ("B", GB), ("C", GC)):
                    st = fstat(f, df[col]) if len(df) and col in df else qstat([])
                    row.update({f"{gname}_n": st["n"], f"{gname}_中位": st["中位"], f"{gname}_p25": st["p25"], f"{gname}_p75": st["p75"]})
                if f not in MKT and len(GA):
                    med = []; pr = []
                    for _, r in GA.iterrows():
                        k = int(r[f"_k{nm}"])
                        if not 0 <= k < K:
                            continue
                        base = f[2:] if f.startswith("指數") else f
                        arr = np.array([ind_val(kd, o_, base, k) for o_ in INDS if o_ != r["_ind"]], float); arr = np.sort(arr[np.isfinite(arr)])
                        if len(arr):
                            med.append(float(np.median(arr))); pr.append(prc(r[col], arr))
                    row["A_同月他產業中位"] = float(np.median(med)) if med else np.nan
                    row["甲在同月百分位中位"] = float(np.nanmedian(pr)) if np.isfinite(pr).any() else np.nan
                rows.append(row)
        for f, _ in CUMS:
            for wn in WINS:
                col = f"{f}@{wn}"; row = {"版": vn, "欄": f, "時點": wn}
                for gname, df in (("甲", GA), ("B", GB), ("C", GC)):
                    st = qstat(df[col]) if len(df) else qstat([])
                    row.update({f"{gname}_n": st["n"], f"{gname}_中位": st["中位"], f"{gname}_p25": st["p25"], f"{gname}_p75": st["p75"]})
                rows.append(row)
        for f in ("起點→高點月數", "段中最大回檔", "波數", "高點後12月最大跌幅", "高點後跌到低點月數"):
            row = {"版": vn, "欄": f, "時點": "段"}
            for gname, df in (("甲", GA), ("B", GB), ("C", GC)):
                st = qstat(df[f"⑩{f}"]) if len(df) else qstat([])
                row.update({f"{gname}_n": st["n"], f"{gname}_中位": st["中位"], f"{gname}_p25": st["p25"], f"{gname}_p75": st["p75"]})
            rows.append(row)
        return pd.DataFrame(rows)
    SIDEJ = pd.concat([side_ind(v) for v in VERS], ignore_index=True)
    log(f"[並排] 乙 {len(SIDE)} 列、甲 {len(SIDEJ)} 列｜{time.time() - t0:.0f}s")

    # 缺欄
    MISS = []
    srcs = {"②": "還原／原始收盤、股數（兩世界）；年資自合併資料首根（2004-02-11、上櫃 2007-07-02 起者左截斷）",
            "③": "官方 per／pbr（2012 起，5 年位置約 2015 起）；市值營收比需 12 期月營收；營業現金流 fs_xbrl 2013Q1 起",
            "④": "月營收 2003 起；財報 fs_hist 2015、fin_hist 2013 起、上傳時戳 t57sb01 2013 起；資料庫 C（fs_xbrl 毛利、營業利益）待資料庫",
            "⑤": "fs_xbrl contract_liabilities 2018 起；存貨 2013 起", "⑥": "fs_xbrl total_assets、capex 2013 起；固定資產 fs_xbrl 無欄 ⇒ 缺；seo_cb_events 1999 起",
            "⑦": "還原價", "⑧": "融資：主 2015 起、早年上櫃 2007-07 起、早年上市無；借券 2015 起；集保 2017 起；外資持股月表 2004-02～2012-12（上櫃 2007-05 起；2013 起待資料庫）；"
                                "法人買賣超 上市 2012-05、上櫃 2015 起；注意處置 2011 起（本件起算）；內部人 2003-05 起",
            "⑨": "景氣燈號 1984 起（修正後值）；大盤融資 2005-01-03 起；SOX、美國同產業、匯率、美國利率 ⇒ 無（私有庫不讀）"}
    for f, c in LV + [(x, "⑨") for x in MKT]:
        r_ = {"類": c, "欄": f, "來源與年限": srcs.get(c, "")}
        for er, (y0, y1) in {"2005～2014": (2004, 2014), "2015～": (2015, 2100)}.items():
            g = YI[(era(YI) >= y0) & (era(YI) <= y1)] if len(YI) else YI
            r_[f"乙起點有值率_{er}"] = float(np.isfinite(g[f"{f}@起點"].to_numpy(float)).mean()) if len(g) else np.nan
        MISS.append(r_)
    for f, c in CUMS:
        r_ = {"類": c, "欄": f, "來源與年限": srcs.get(c, "")}
        for er, (y0, y1) in {"2005～2014": (2004, 2014), "2015～": (2015, 2100)}.items():
            g = YI[(era(YI) >= y0) & (era(YI) <= y1)] if len(YI) else YI
            r_[f"乙起點有值率_{er}"] = float(np.isfinite(g[f"{f}@前12月→起點"].to_numpy(float)).mean()) if len(g) else np.nan
        MISS.append(r_)
    MISS.append({"類": "⑨", "欄": "SOX、美國同產業、新台幣匯率、美國利率", "來源與年限": "無（外部數列在私有庫 us-stock-data data/macro，⛔ 不讀）"})
    MISS.append({"類": "⑥", "欄": "固定資產成長", "來源與年限": "缺（fs_xbrl 無固定資產欄）"})
    MISS.append({"類": "④", "欄": "毛利、營業利益（資料庫 C 版）", "來源與年限": "待資料庫（fs_xbrl 三欄重建中）"})
    MISS = pd.DataFrame(MISS)
    CNT = pd.DataFrame([{"單位": "乙×3", "段數": len(YI)}, {"單位": "乙×5（只報段數）", "段數": B5n},
                        {"單位": "對照B 乙", "段數": len(BI)}, {"單位": "對照D 崩", "段數": int((YI["對照D"] == "崩").sum()) if len(YI) else 0},
                        {"單位": "對照D 下市", "段數": int((YI["對照D"] == "下市").sum()) if len(YI) else 0},
                        {"單位": "對照D 未定／遇壞根截", "段數": int(YI["對照D"].isin(["未定", "遇壞根截"]).sum()) if len(YI) else 0}] +
                       [{"單位": f"甲 {v}", "段數": int((JA["版"] == v).sum()) if len(JA) else 0} for v in VERS] +
                       [{"單位": f"對照B 甲 {v}", "段數": int((JBd["版"] == v).sum()) if len(JBd) else 0} for v in VERS] +
                       [{"單位": f"對照C {v}", "段數": int((JCd["版"] == v).sum()) if len(JCd) else 0} for v in VERS])
    # 存檔
    def drop_(df):
        return df[[c for c in df.columns if not c.startswith("_")]] if len(df) else df
    SIDE.to_csv(os.path.join(out_dir, "並排_乙.csv"), index=False, encoding="utf-8-sig")
    SIDEJ.to_csv(os.path.join(out_dir, "並排_甲.csv"), index=False, encoding="utf-8-sig")
    with gzip.open(os.path.join(out_dir, "乙_全表.csv.gz"), "wt", encoding="utf-8") as fh:
        YI.to_csv(fh, index=False)
    JA.to_csv(os.path.join(out_dir, "甲_全表.csv"), index=False, encoding="utf-8-sig")
    BI.to_csv(os.path.join(out_dir, "對照B_乙.csv"), index=False, encoding="utf-8-sig")
    JBd.to_csv(os.path.join(out_dir, "對照B_甲.csv"), index=False, encoding="utf-8-sig")
    JCd.to_csv(os.path.join(out_dir, "對照C.csv"), index=False, encoding="utf-8-sig")
    YI[YI["對照D"].isin(["崩", "下市"])][["代號", "名稱", "起點", "高點", "倍數", "產業(起點PIT)", "族群(切0.7)", "對照D", "⑩高點後12月最大跌幅"]].to_csv(
        os.path.join(out_dir, "對照D.csv"), index=False, encoding="utf-8-sig")
    MISS.to_csv(os.path.join(out_dir, "缺欄.csv"), index=False, encoding="utf-8-sig")
    CNT.to_csv(os.path.join(out_dir, "段數.csv"), index=False, encoding="utf-8-sig")
    pickle.dump({"SIDS": SIDS, "MEp": MEp, "P": P, "CU": CU, "META": META, "SHK": SHK, "MK": MK, "INDM": INDM, "PERIODS": PERIODS,
                 "IQR": IQR}, open(os.path.join(WORK, f"bgr3_panel_{'dry' if a.limit else 'full'}.pkl"), "wb"), protocol=5)
    J = {"性質": "描述（⛔ 不判、不計 N、不檢定、不挑特徵；族群不當母體）", "依據": "台股 seq532 §一 §二、seq534 §一②；裁定 seq421",
         "資料": {"快照A": SHA_A, "快照B": SHA_B, "主世界": Zm["data"], "早年世界": Ze["data"]}, "檔數": N, "月底數": K, "乾跑limit": a.limit,
         "乾跑代號": SIDS if a.limit else None, "接縫": dict(seam_info), "對照B乙_IQR": IQR, "段數": CNT.to_dict("records"), "必附": NOTES,
         "讀法": __doc__.split("═══ 讀法")[1], "時間": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M"), "耗時秒": round(time.time() - t0)}
    json.dump(J, open(os.path.join(out_dir, "bigrun3.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] {time.time() - t0:.0f}s ⇒ {out_dir}")
    open(os.path.join(out_dir, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
