# -*- coding: utf-8 -*-
"""PREREGV 早年段資料轉接層（回測線，2026-09-27）：把資料庫線 data/early/ 那一棵樹，轉成主窗管線讀得懂的 data/ 版面。

⛔ 本檔不算、不印任何報酬；只搬資料、改版面、驗結構。⛔ 不寫 ~/tw-stock-data（只用 git archive／git show 讀）。
⭐ 設計：主窗管線一律讀 D.DATA（data.py／research11／research34／p4_features／tradability／universe_gate）
   ⇒ 本檔在 ~/earlydata/<sha10>/<變體>/data 產出【同一版面】的目錄，之後只要把 D.DATA 指過去（use_early）即可，
      ⇒ 策略程式一字不動；要加格（例：營飆 v2 候選兩格）只要那一格的程式讀 D.DATA 就直接可用。

═══ 來源（逐項 commit 與讀法；⛔ 每一項都寫明出處）═══
  快照      tw-stock-data main e024f8a083（2026-09-26 23:23 資料庫線「上櫃 G1 重報」那封信的快照；上市列自 c7a1b4b9c8 起 0 變動）
  日曆      data/early/daily/<日期>.csv 的檔名 ∩「該日有 twse 列」（只上市；裁定 seq206 §三）
            ⇔ data/early/_structure.csv 的 twse 列（rows > 0）；本檔閘門逐日比對
  日 K      data/early/daily（17 欄，與 data/universe/daily 逐欄相同；資料庫線 1450）
            ⚠ 早年上櫃「量 0 且四價全 0」已由資料庫線改空白（notrade_blanked）；上市沒有這個形狀
            ⚠ shares 欄早年【全空】（2012-06-01 上市 859 列 0 列有值）⇒ 見 MISSING 的 M2
            ⚠ 除權息日 change ＝ 0.0（官方 MI_INDEX 寫 X、漲跌價差 0.00；資料庫線 0404 §二）⇒ ⛔ 不可用 close − change 反推參考價
  還原      官方除權息 TWT49U（上市）⇒ ⛔ data/early 沒有（M3）；只有 0050 的 2012～2014 三筆在 data/extra/0050_adj_2012_2014.csv
            （main 45c6fcbac1；欄位同 data/adj；factor ＝ 官方參考價 ÷ 除息前收盤）⇒ 本檔只為 0050 產 adj，cum_factor 在早年段內重算
            （＝ 事件日 ≥ 該列的 factor 連乘；與 data.cum_factor_series「事件日嚴格大於 d 的因子連乘」同一條鏈）
  減資      主版（判定用）只用官方 TWTAUU（登錄 seq5 §三）⇒ ⛔ data/early 沒有（M4）
            規則 A／B（描述段用）：資料庫線 1504 §一逐字；本檔 detect_rule_ab() 獨立重寫，閘門逐筆對資料庫線草稿
            early_checks.py 的輸出（C:\\SynologyDrive\\投資\\資料庫用\\草稿\\early_checks_out.json）
  0050      早年日 K 的 0050 列（MI_INDEX）＋ data/extra/0050_2012_2014.csv（STOCK_DAY）互驗；除息 ⇒ 上面那三筆
  月營收    data/early/revenue/<期別>_<twse|tpex>.csv（main 2026-09-25 18:27 信；欄位同 mops/revenue_hist）
            ⚠ 2006-06～2011-12 電子業列兩次 ⇒ 以 (stock_id, period) 去重、產業別取細類（⛔ 不取「電子工業」）；2012 起無重複
  本益比    data/early/per/<日期>.csv（上市，main fc9bbe01e7；2012-01-02～2014-12-31）⇒ stocks_per/<sid>.csv
            ⚠ close 欄早年空白（官方沒給）⇒ research34.load_per 只讀 yield_pct／per／pbr，不受影響
  三大法人  data/early/instamt 是【大盤】金額（date,investor,buy,sell,net；外資 2009-05-04 改名、自營商 2014-12-01 拆兩列）
            ⇒ ⛔ 不是個股；個股 T86（上市 2012-05-02 起）⛔ data/early 沒有（M1）
  名冊      data/meta/delisted.csv（b7a17bf624 起：上市 265｜上櫃 239）、data/meta/otc_to_twse.csv（342；代號＋日期在此表 ⇒ 轉上市、⛔ 不當下市）
            上市日名冊（資料庫線 1543）⛔ 只查不落地 ⇒ first_seen／last_seen 由早年日 K 自推（讀法 R13，待裁）
  處置／注意 data/meta/disposal.csv（最早 2010-12-14）、attention.csv（最早 2011-01-03）：只取 ≤ 2014-12-31 的列（⛔ 不讀 2015 以後）
  產業別    data/meta/industry.csv（TDR 名單 industry_code 91；p4_features.tdr_ids 用；今日值，與主窗同一份讀法）

═══ ⛔ 缺的資料（MISSING；fail closed：缺了就不產那一塊、use_early(strict=True) 拒絕）═══
  M1 上市個股三大法人日淨買超股數（T86，2012-05-02～2014-12-31）      ⇒ 門檻B 族 inst_ok（#5 #8 #18～#24）
  M2 上市個股發行股數 shares（2012～2014；early/daily 的 shares 欄全空）  ⇒ turn20、fore20／trust20 的分母 ⇒ 門檻B 族 inst_ok
  M3 上市全體個股除權息官方事件 TWT49U（至少 2011-06～2014-12；描述段要 2003-05 起） ⇒ 全部格的還原價
  M4 上市官方減資 TWTAUU（2011-01～2014-12）                              ⇒ 主版減資剔除／了結（全部格）
  M5 0050 2011 年除息（TWT49U）                                           ⇒ 大盤閘 MA200 回看（#1 #4 #7 #16 #17、營飆 v2 兩格）

═══ 讀法：登錄與信沒寫死的（⛔ 本檔不選；參數預設 None ⇒ 需要時拒跑）═══
  見 READINGS（researchV.py pre 段原樣抄進 PRE_REPORT.md）。
"""
from __future__ import annotations

import csv
import glob
import hashlib
import io
import json
import os
import pickle
import subprocess
import tarfile

import numpy as np
import pandas as pd

DB_REPO = os.path.expanduser("~/tw-stock-data")
EARLY_SHA = "e024f8a083644c2ccaa686f9704d830fbd0e8577"
ROOT = os.path.expanduser("~/earlydata")
EXTRACT = ["data/early", "data/extra", "data/meta/delisted.csv", "data/meta/otc_to_twse.csv", "data/meta/disposal.csv",
           "data/meta/attention.csv", "data/meta/industry.csv", "data/meta/stocks.csv", "data/meta/calendar_twse.csv"]
DAILY_COLS = ["key", "date", "stock_id", "name", "market", "open", "high", "low", "close", "volume", "amount", "change", "limit",
              "shares", "transactions", "price_basis", "last_price"]
STOCK_COLS = ["date", "stock_id", "name", "market", "open", "high", "low", "close", "volume", "amount", "change", "limit",
              "shares", "transactions", "price_basis", "last_price", "valid_bar"]
NUM = ["open", "high", "low", "close", "volume", "amount", "change", "transactions", "shares"]
WIN_FIRST_MONTH, WIN_END = "2012-06", "2014-12-31"
DESC_FIRST_MONTH, DESC_END = "2008-01", "2012-05-31"
T86_TWSE_START = "2012-05-02"          # 資料庫線 1423 ②④：官方回「小於101年05月02日」
MAIN_FIRST_DAY = "2015-01-05"
META_CUTOFF = "2014-12-31"             # 處置／注意只取到這天（⛔ 不讀 2015 以後）

MISSING = {
    "M1": {"項": "上市個股三大法人日淨買超股數（T86，2012-05-02～2014-12-31）", "版面": "stocks_inst/<sid>.csv（date,stock_id,foreign,trust,dealer,total,dealer_self,dealer_hedge）",
           "影響": "p4_features.fore20／trust20 ⇒ inst_ok ⇒ 門檻B 族（#5 #8 #18～#24）與 eligible", "data/early 現況": "只有大盤 instamt（非個股）"},
    "M2": {"項": "上市個股發行股數 shares（2012～2014，至少每日可 ffill）", "版面": "stocks/<sid>.csv 的 shares 欄",
           "影響": "p4_features.turn20、fore20／trust20 的分母 ⇒ inst_ok ⇒ 門檻B 族", "data/early 現況": "early/daily 的 shares 欄全空"},
    "M3": {"項": "上市全體個股除權息官方事件 TWT49U（至少 2011-06～2014-12；描述段要 2003-05 起）", "版面": "adj/<sid>.csv（date,factor,factor_official,cum_factor,pre_close,ref_price,kind,event）",
           "影響": "全部格：還原價（特徵回看 250 根＋窗內報酬）；research11.load_bars 幽靈事件判定", "data/early 現況": "只有 0050 2012～2014 三筆（data/extra）；⛔ 不可用 close − change 反推（除權息日 change＝0）"},
    "M4": {"項": "上市官方減資 TWTAUU（2011-01～2014-12）", "版面": "事件表（date,stock_id,pre_close,ref_price,reason）",
           "影響": "登錄 §三 主版：事件恢復交易日 e 之前 5／之後 60 根不可新進、持有中遇事件了結（全部格）", "data/early 現況": "沒有（資料庫線 G1 用的是草稿現打，未落地）"},
    "M5": {"項": "0050 2011 年除息（TWT49U）", "版面": "adj/0050.csv 多一列",
           "影響": "大盤閘 MA200（t−1）回看到 2011-08 ⇒ #1 #4 #7 #16 #17、營飆 v2 兩格在 2012-06～2012-08 的閘", "data/early 現況": "data/extra 只有 2012～2014"},
}

READINGS = {
    "R1": {"題": "「只上市」落在哪一層", "選項": {"a": "只收 twse 列（轉上市股的上櫃時期歷史不進；回看從轉上市日重算）",
                                               "b": "母體＝量測日在上市者；轉上市股的上櫃時期列當歷史（回看、營收 24 月、bars 照算）"},
           "影響": "轉上市股的 bars／MA／rev_hi24 暖身；上櫃 G1 未過 ⇒ b 會讀到上櫃期的價格與（未驗的）減資形狀"},
    "R2": {"題": "早年才有、今日 stocks.csv 沒有的代號，kind 怎麼定", "選項": {"a": "四碼、首碼 1～9、非 91xx ⇒ stock；其餘不進",
                                                                      "b": "照資料庫線落地名冊（上市日名冊，1543 只查未落地）"},
           "影響": "load_universe（kind＝stock）與 gate3 的母體"},
    "R3": {"題": "窗尾：早年日曆止於 2014-12-31（⛔ 不讀 2015 以後）", "選項": {"a": "引擎原樣（H 規則 xpos 超出日曆 ⇒ 整筆丟；門檻B x ≥ ncal 剔）＝ 主窗同一支程式",
                                                                          "b": "照 researchYear1M T1 主版：留下、窗尾照收盤計值、不賣不扣成本",
                                                                          "c": "延長日曆到 2015 取出場價（⛔ 與登錄「不讀主庫 2015 以後」衝突）"},
           "影響": "H120 格約最後 120 根（2014-07 起）的新訊號、H60 約最後 60 根；登錄 §二「窗尾仍持有的部位逐日市值計到窗尾」在 a 之下幾乎是空集合"},
    "R4": {"題": "各程式寫死的主窗常數要換成什麼早年值（登錄只說「只換窗與資料」）", "選項": {"表": "見 WINDOW_CONSTANTS；每一條給主窗值與建議的同義早年值"},
           "影響": "訊號與面板的建構範圍"},
    "R5": {"題": "#5 P17 R_eq 的 σ burn-in（窗內前 120 根 w＝0.50）", "選項": {"a": "照原件：起點 w0、前 120 根 w＝0.50（主窗也是）",
                                                                           "b": "起點延到 σ 算得出的第一個再平衡日"},
           "影響": "2.5 年窗有約 19% 的日子是固定 0.50"},
    "R6": {"題": "#1 的種子", "選項": {"a": "1000＋r（rerun17／regime_t1 原件；營飆 v2 登錄 §二 逐字）",
                                     "b": "99000＋r（PREREGV §四 別名段落後接的「8694b4f173 researchP9run」那句；排版上應屬 P9 六格）"},
           "影響": "#1 的 200 顆路徑"},
    "R7": {"題": "開跑前算術的口徑", "選項": {"α": "0.05／24（登錄字面）或 0.05／26（seq210 N_驗收 26）",
                                          "年化": "日差平均 × 245（算術）或 幾何",
                                          "30 個月": "主窗月份重抽 30 個（置中）或 主窗內每一段連續 30 個月",
                                          "月數": "30（登錄字面）或 31（2012-06～2014-12 實際曆月）"},
           "影響": "門檻值；本段三者都算、並列"},
    "R8": {"題": "主版減資：「持有中遇事件以消失前最後收盤了結（同下市處理）」怎麼接到引擎", "選項": {"a": "開 simulate_mtm 的 delist 機制（主窗 24 格都是關的 ⇒ 組態變動）",
                                                                                                "b": "在價格序列上把事件後截斷（該檔之後不可持有）",
                                                                                                "c": "兩者之外另寫（⛔ 需裁）"},
           "影響": "全部格；新候選的 −5／＋60 根剔除可以直接在訊號表上做（不動引擎）"},
    "R9": {"題": "寫死的「上市前 5 根」判準 2015-01-12（research11.load_bars 第 154 行、tradability.one 第 47 行）", "選項": {"a": "原樣（早年全部日期 < 2015 ⇒ 永不成立 ⇒ 2012～2014 新上市股前 5 根不跳過）",
                                                                                                                            "b": "換成早年日曆起點 +5 根（2004-02-18）＝ 同義常數"},
           "影響": "AND 族要 ≥ 249 根才可能成為訊號 ⇒ 預期對訊號 0 影響；tradability 在 24 格都是關的 ⇒ 0；仍列出"},
    "R10": {"題": "處置／注意的來源", "選項": {"a": "主庫 data/meta/disposal.csv、attention.csv 的 ≤ 2014-12-31 列（最早 2010-12-14／2011-01-03）"},
            "影響": "research34 的 disposal_mask；描述段 2008～2010 沒有處置資料"},
    "R11": {"題": "轉上市股在上櫃時期的月營收", "選項": {"a": "只讀 twse 營收檔（同 R1 a）", "b": "兩市營收檔合併（同 R1 b）"},
            "影響": "rev_hi24 的 24 期回看"},
    "R12": {"題": "開跑前算術用哪幾格", "選項": {"a": "PREREGV 24 格（登錄字面）", "b": "加營飆 v2 兩格（seq210；但 v2 登錄沒有 Bonferroni 那一條）"},
            "影響": "只影響表列"},
    "R13": {"題": "上市日／下市日", "選項": {"a": "first_seen／last_seen 由早年日 K 自推（上市前本來就沒有價，選不到）＋ delisted.csv 官方下市日",
                                          "b": "等資料庫線落地上市日名冊（1543）"},
            "影響": "in_life 閘；閘門先量兩者差"},
}

# 各程式寫死的主窗常數（R4）：(檔, 名稱, 主窗值, 同義的早年值建議, 意義)
WINDOW_CONSTANTS = [
    ("rerun17.py", "W0／W1／WIN_DAYS", "2017-03-02／2026-08-24／2313", "2012-06 第一個交易日／2014-12-31／（日曆算）", "主窗端點與天數"),
    ("rerun17.py", "ANCHOR", "0050 主窗 +24.02%／−33.96%", "早年 0050 自算還原同窗（⛔ 開跑前不算）", "0050 錨（逐位元閘）"),
    ("research34.py", "SIG_START／SIG_END", "2016-01-04／2026-07-31", "足以讓 w0 的 AND 找得到 45 根內面板列的起點／2014-12-31", "營收面板的訊號位置範圍"),
    ("research34.py／research11.py／research13.py", "SPLIT", "2021-01", "（只描述的 A／B 窗；早年段不用）", "A／B 窗切點"),
    ("researchp7.build_sig_gate_b", "start", "2017-01-01", "2012-01-01（同為窗首往前約兩個月）或 w0", "門檻B 訊號量測日下限"),
    ("researchAFC_panel.py／p9_panel_ext.py", "measurement_days 起訖", "2015-01-01～2026-03-31（ext 到 2026-08-24）", "早年日曆起點～2014-12-31", "門檻B 面板量測日"),
    ("researchP9run.py", "PERIODS", "2020-03／2022／2025-04", "（主窗描述區間；早年段改登錄 §五 的 2008、2011 兩段＝描述段）", "三段區間報酬"),
    ("researchAvg.py", "E_LO", "2017-03-01", "w0", "甲段事件起點（乙一只用 P9 setup）"),
    ("research11.py:154／tradability.py:47", "上市前 5 根判準", "2015-01-12", "見 R9", "新上市股前 5 根"),
    ("research11.py:51／tradability.CUT", "漲跌幅切點", "2015-06-01", "同（早年全在 7%）", "7%／10%"),
    ("researchp7.WANT_SIG_B", "驗收數", "2882 列…", "（主窗驗收常數；早年段不適用）", "訊號數閘"),
    ("rerun17_build.py", "import 時 RR.use_snapshot()＋assert D.DATA ＝ H2D；輸出 resultsN17/sig_edc6f", "主窗快照", "早年要另一支呼叫同四個函式（research34.process_stock／research11.stock_features／research13.and_flags／researchp1.attach_features）、輸出 resultsV/sig_early", "AND 訊號建構（⚠ 這四個函式會順手算前瞻報酬 g_H* ⇒ 只能在第二段跑）"),
    ("researchYfRank.build_keys／listexit_lines.setup_t1／researchYfV2", "sig_edc6f 路徑、resultsYfRank/pre_keys.csv", "主窗", "早年版 sig_early、pre_keys_early.csv（K4＝c[k]/c[k−20]−1 取 research11.load_bars 的還原收盤）", "營飆 v2 兩格的欄位"),
    ("researchP9run.py", "PANEL_SIG／PANEL_EXT（＋sha 閘）", "resultsAFC/panel.csv.gz／resultsp9_engine/panel_ext.csv.gz", "早年 build_panel 產的面板（新 sha）", "門檻B 族訊號與 ⓑ 旗標"),
]


# ═════════════ 取出（唯讀）═════════════
def snap_dir(sha: str = EARLY_SHA) -> str:
    return os.path.join(ROOT, sha[:10])


def raw_dir(sha: str = EARLY_SHA) -> str:
    return os.path.join(snap_dir(sha), "raw")


def extract(sha: str = EARLY_SHA, log=print) -> dict:
    """git archive <sha> 取出 EXTRACT 各路徑到 ~/earlydata/<sha10>/raw（⛔ 不寫 ~/tw-stock-data）。已取過 ⇒ 驗清單後直接回。"""
    rd = raw_dir(sha)
    man_p = os.path.join(snap_dir(sha), "raw_manifest.json")
    if os.path.exists(man_p):
        man = json.load(open(man_p, encoding="utf-8"))
        if man.get("sha") == sha and man.get("paths") == EXTRACT:
            return man
    full = subprocess.run(["git", "-C", DB_REPO, "rev-parse", sha], capture_output=True, text=True, check=True).stdout.strip()
    if full != sha:
        raise SystemExit(f"⛔ {sha} 解析成 {full}")
    os.makedirs(rd, exist_ok=True)
    p = subprocess.run(["git", "-C", DB_REPO, "archive", "--format=tar", sha] + EXTRACT, capture_output=True, check=True)
    with tarfile.open(fileobj=io.BytesIO(p.stdout)) as tf:
        tf.extractall(rd)
    man = {"sha": sha, "paths": EXTRACT, "tar_bytes": len(p.stdout), "tar_sha256": hashlib.sha256(p.stdout).hexdigest(),
           "counts": {d: len(glob.glob(os.path.join(rd, "data", "early", d, "*.csv"))) for d in ("daily", "per", "otcper", "instamt", "revenue")}}
    json.dump(man, open(man_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[取出] {sha[:10]} ⇒ {rd}｜{man['counts']}｜tar sha256 {man['tar_sha256'][:16]}")
    return man


# ═════════════ 讀 ═════════════
def read_daily(sha: str = EARLY_SHA, markets=("twse", "tpex")) -> pd.DataFrame:
    """早年日 K 全部列（快取成 pickle）。date 為 'YYYY-MM-DD' 字串；數值欄轉 float（空白 ⇒ NaN）。"""
    cache = os.path.join(snap_dir(sha), "daily_all.pkl")
    if os.path.exists(cache):
        df = pickle.load(open(cache, "rb"))
    else:
        fs = sorted(glob.glob(os.path.join(raw_dir(sha), "data", "early", "daily", "*.csv")))
        parts = []
        for f in fs:
            x = pd.read_csv(f, dtype=str, keep_default_na=False)
            if list(x.columns) != DAILY_COLS:
                raise SystemExit(f"⛔ {os.path.basename(f)} 表頭 {list(x.columns)} ≠ 17 欄")
            parts.append(x)
        df = pd.concat(parts, ignore_index=True)
        for c in NUM:
            df[c] = pd.to_numeric(df[c].str.replace(",", "", regex=False), errors="coerce")
        df["market"] = df["market"].astype("category")
        pickle.dump(df, open(cache, "wb"), protocol=4)
    return df[df["market"].isin(markets)].reset_index(drop=True)


def calendar(daily: pd.DataFrame, market: str = "twse") -> list[str]:
    """該市場有列的日子（⭐ 只上市 ⇒ market='twse'）。"""
    return sorted(daily.loc[daily["market"] == market, "date"].unique())


def structure(sha: str = EARLY_SHA) -> pd.DataFrame:
    return pd.read_csv(os.path.join(raw_dir(sha), "data", "early", "_structure.csv"), dtype={"date": str, "market": str})


def dedup_revenue(df: pd.DataFrame) -> pd.DataFrame:
    """資料庫線 1827：以 (stock_id, period) 去重；兩列只差產業別時取【細類】（⛔ 不取「電子工業」）。
    兩列除產業別外若不全同 ⇒ 拒收（fail closed）。"""
    key = ["stock_id", "period"]
    other = [c for c in df.columns if c not in key + ["產業別"]]
    dup = df.duplicated(key, keep=False)
    if not dup.any():
        return df.reset_index(drop=True)
    d = df[dup]
    chk = d.groupby(key)[other].nunique(dropna=False)
    if (chk > 1).any().any():
        bad = chk[(chk > 1).any(axis=1)].head(5)
        raise SystemExit(f"⛔ 營收重複列除產業別外不同：{bad.to_dict()}")
    keep = d[d["產業別"] != "電子工業"].drop_duplicates(key, keep="first")
    miss = set(map(tuple, d[key].drop_duplicates().to_numpy())) - set(map(tuple, keep[key].to_numpy()))
    if miss:                                   # 兩列都是「電子工業」或都不是：取第一列
        keep = pd.concat([keep, d[d[key].apply(tuple, axis=1).isin(miss)].drop_duplicates(key, keep="first")])
    return pd.concat([df[~dup], keep]).sort_values(key, kind="stable").reset_index(drop=True)


def read_revenue(sha: str = EARLY_SHA, markets=("twse",)) -> pd.DataFrame:
    fs = sorted(glob.glob(os.path.join(raw_dir(sha), "data", "early", "revenue", "*.csv")))
    parts = [pd.read_csv(f, dtype=str, keep_default_na=False) for f in fs if os.path.basename(f)[:-4].split("_")[1] in markets]
    return dedup_revenue(pd.concat(parts, ignore_index=True))


# ═════════════ 減資偵測（資料庫線 1504 §一逐字；描述段用）═════════════
def detect_rule_ab(daily: pd.DataFrame, cal: list[str], tol_abs: float = 0.01, tol_rel: float = 0.001,
                   absent_min: int = 4, b_jump: float = 0.05) -> list[tuple]:
    """每檔、每個「有成交」的交易日 d：ref(d) ＝ close(d) − change(d)；prev ＝ d 之前最後一個有成交日的收盤；
    absent ＝ prev 那天到 d 之間【該檔整列不在日檔】的交易日數。
    基準跳動：|ref − prev| > tol_abs 且 |ref ÷ prev − 1| > tol_rel。
    規則 A：基準跳動 ∧ absent ≥ 4；規則 B：基準跳動 ∧ 無成交（列不在或價空）連續 ≥ 4 日 ∧ |ref ÷ prev − 1| > 5%（A 優先）。
    回 [(sid, prev_date, d, rule, ref/prev)]。⚠ change 空白（算不出 ref）⇒ 該日只更新 prev。
    ⭐ cal ＝ 判「交易日數」用的日曆（資料庫線草稿用兩市合併日檔，兩市同曆）。"""
    pos = {d: i for i, d in enumerate(cal)}
    out = []
    for sid, g in daily.sort_values(["stock_id", "date"]).groupby("stock_id", sort=False):
        dates = g["date"].to_numpy(); close = g["close"].to_numpy(float); chg = g["change"].to_numpy(float)
        prev_d = None; prev_c = None; last_row = None
        for d, c, ch in zip(dates, close, chg):
            absent = (pos[d] - pos[last_row] - 1) if last_row is not None else 0
            last_row = d
            if not np.isfinite(c) or c == 0:
                continue
            if not np.isfinite(ch):
                prev_d, prev_c = d, c
                continue
            ref = c - ch
            if prev_c is not None and abs(ref - prev_c) > tol_abs + 1e-9 and abs(ref / prev_c - 1) > tol_rel:
                notrade = pos[d] - pos[prev_d] - 1
                rule = "A" if absent >= absent_min else ("B" if notrade >= absent_min and abs(ref / prev_c - 1) > b_jump else "")
                if rule:
                    out.append((sid, prev_d, d, rule, round(ref / prev_c, 6)))
            prev_d, prev_c = d, c
    return out


# ═════════════ 0050 ═════════════
def adj_0050(sha: str = EARLY_SHA) -> pd.DataFrame:
    """0050 的 adj（data/extra/0050_adj_2012_2014.csv 三筆），cum_factor 在早年段內重算：cum[i] ＝ ∏_{j ≥ i} factor[j]。"""
    a = pd.read_csv(os.path.join(raw_dir(sha), "data", "extra", "0050_adj_2012_2014.csv"), dtype={"date": str})
    a = a.sort_values("date").reset_index(drop=True)
    f = a["factor"].astype(float).to_numpy()
    a["cum_factor_main"] = a["cum_factor"]
    a["cum_factor"] = np.cumprod(f[::-1])[::-1]
    return a


def extra_0050_daily(sha: str = EARLY_SHA) -> pd.DataFrame:
    return pd.read_csv(os.path.join(raw_dir(sha), "data", "extra", "0050_2012_2014.csv"), dtype={"date": str, "stock_id": str})


# ═════════════ 名冊 ═════════════
def roster(daily_mkt: pd.DataFrame, sha: str = EARLY_SHA, kind_rule: str | None = None) -> pd.DataFrame:
    """meta/stocks.csv 版面（stock_id,name,market,kind,first_seen,last_seen）；first／last ＝ 該市場列的首末日（R13 a）。
    kind：今日 stocks.csv 有的照抄；沒有的 ⇒ kind_rule（R2；None ⇒ 標 '?'，⛔ 不進 load_universe）。"""
    g = daily_mkt.sort_values("date").groupby("stock_id")
    r = pd.DataFrame({"name": g["name"].last(), "market": g["market"].last().astype(str), "first_seen": g["date"].first(), "last_seen": g["date"].last()})
    st = pd.read_csv(os.path.join(raw_dir(sha), "data", "meta", "stocks.csv"), dtype=str).drop_duplicates("stock_id", keep="last").set_index("stock_id")
    r["kind"] = st["kind"].reindex(r.index)
    r["kind_src"] = np.where(r["kind"].notna(), "stocks.csv（今日）", "")
    miss = r["kind"].isna()
    if kind_rule == "a":
        sid = pd.Series(r.index, index=r.index)
        ok = sid.str.fullmatch(r"[1-9]\d{3}") & ~sid.str.startswith("91")
        r.loc[miss, "kind"] = np.where(ok[miss], "stock", "other")
        r.loc[miss, "kind_src"] = "R2a 規則"
    else:
        r.loc[miss, "kind"] = "?"
        r.loc[miss, "kind_src"] = "待裁 R2"
    return r.reset_index()[["stock_id", "name", "market", "kind", "first_seen", "last_seen", "kind_src"]]


# ═════════════ 產出主窗版面 ═════════════
def build(sha: str = EARLY_SHA, variant: str = "R1a", kind_rule: str | None = None, log=print) -> dict:
    """產出 ~/earlydata/<sha10>/<variant>/data（主窗版面）。缺的塊（MISSING）不產，寫進 STATUS.json。
    variant：'R1a'（只收 twse 列）；'R1b' 尚未實作（待裁定 R1）。"""
    if variant != "R1a":
        raise SystemExit(f"⛔ variant {variant}：R1 待裁，本段只產 R1a（結構閘門與 R1 無關）")
    extract(sha, log)
    out = os.path.join(snap_dir(sha), variant, "data")
    for d in ("meta", "stocks", "adj", "stocks_per", os.path.join("mops", "revenue_hist")):
        os.makedirs(os.path.join(out, d), exist_ok=True)
    rd = os.path.join(raw_dir(sha), "data")
    daily = read_daily(sha, markets=("twse",))
    cal = calendar(daily, "twse")
    pd.DataFrame({"date": cal}).to_csv(os.path.join(out, "meta", "calendar_twse.csv"), index=False)
    # 日 K ⇒ stocks/<sid>.csv（主窗 17 欄；valid_bar ＝ 收盤有值 ⇒ 1，否則 0；主窗讀者只讀 date／OHLC／volume／amount／shares）
    n_files = 0
    for sid, g in daily.sort_values(["stock_id", "date"]).groupby("stock_id", sort=False):
        x = g.drop(columns=["key"]).copy()
        x["market"] = x["market"].astype(str)
        x["valid_bar"] = np.where(x["close"].notna() & (x["close"] > 0), 1, 0)
        x[STOCK_COLS].to_csv(os.path.join(out, "stocks", f"{sid}.csv"), index=False)
        n_files += 1
    # 名冊
    R = roster(daily, sha, kind_rule)
    R.drop(columns=["kind_src"]).to_csv(os.path.join(out, "meta", "stocks.csv"), index=False)
    R.to_csv(os.path.join(snap_dir(sha), variant, "roster_with_src.csv"), index=False)
    # 0050 adj（其餘個股 ⛔ M3）
    a = adj_0050(sha)
    a[["date", "factor", "factor_official", "cum_factor", "pre_close", "ref_price", "kind", "event"]].to_csv(os.path.join(out, "adj", "0050.csv"), index=False)
    # 月營收（twse；R11 a）
    rv = read_revenue(sha, ("twse",))
    for (per,), g in rv.groupby(["period"]):
        g.to_csv(os.path.join(out, "mops", "revenue_hist", f"{per}_twse.csv"), index=False)
    # 本益比 ⇒ stocks_per/<sid>.csv
    fs = sorted(glob.glob(os.path.join(rd, "early", "per", "*.csv")))
    per = pd.concat([pd.read_csv(f, dtype=str, keep_default_na=False) for f in fs], ignore_index=True)
    for sid, g in per.groupby("stock_id"):
        g.to_csv(os.path.join(out, "stocks_per", f"{sid}.csv"), index=False)
    # meta：名冊與處置、注意（≤ 2014-12-31）、產業別
    for f in ("delisted.csv", "otc_to_twse.csv", "industry.csv"):
        with open(os.path.join(rd, "meta", f), "rb") as s, open(os.path.join(out, "meta", f), "wb") as t:
            t.write(s.read())
    dp = pd.read_csv(os.path.join(rd, "meta", "disposal.csv"), dtype=str, keep_default_na=False)
    dp[dp["start_date"] <= META_CUTOFF].to_csv(os.path.join(out, "meta", "disposal.csv"), index=False)
    at = pd.read_csv(os.path.join(rd, "meta", "attention.csv"), dtype=str, keep_default_na=False)
    at[(at["date"] != "") & (at["date"] <= META_CUTOFF)].to_csv(os.path.join(out, "meta", "attention.csv"), index=False)
    status = {"sha": sha, "variant": variant, "data": out, "calendar": [cal[0], cal[-1], len(cal)], "stocks_files": n_files,
              "roster": {"列": int(len(R)), "kind": R["kind"].value_counts().to_dict(), "kind_待裁": int((R["kind"] == "?").sum())},
              "adj": {"0050": int(len(a)), "其餘": "⛔ M3 缺"}, "stocks_inst": "⛔ M1 缺", "shares": "⛔ M2 缺（stocks/*.csv 的 shares 全空）",
              "revenue_periods": int(rv["period"].nunique()), "per_files": int(per["stock_id"].nunique()),
              "disposal_rows": int((dp["start_date"] <= META_CUTOFF).sum()), "complete": False, "missing": sorted(MISSING)}
    json.dump(status, open(os.path.join(snap_dir(sha), variant, "STATUS.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[產出] {out}｜{json.dumps({k: status[k] for k in ('calendar', 'stocks_files', 'roster', 'revenue_periods', 'per_files')}, ensure_ascii=False)}")
    return status


def use_early(sha: str = EARLY_SHA, variant: str = "R1a", strict: bool = True) -> str:
    """把 D.DATA 指到早年版面。strict ⇒ STATUS.complete 為假就拒絕（⛔ 缺 M1～M5 不可跑任何格）。"""
    from . import data as D
    st_p = os.path.join(snap_dir(sha), variant, "STATUS.json")
    if not os.path.exists(st_p):
        raise SystemExit(f"⛔ 沒有 {st_p}：先 build()")
    st = json.load(open(st_p, encoding="utf-8"))
    if strict and not st.get("complete"):
        raise SystemExit(f"⛔ 早年版面不完整（缺 {st.get('missing')}）⇒ strict 模式拒絕；結構閘門請用 strict=False")
    D.DATA = st["data"]
    return D.DATA
