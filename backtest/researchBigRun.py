# -*- coding: utf-8 -*-
"""長線「大漲是怎麼來的」第一步：大漲段清單＋當時樣貌（台股策略線 seq531，2026-10-21 12:09，件-回測會同裁定）——回測線計算子代理。
⛔ 描述件：不判、不計 N、不當選股規則；不做任何「之後報酬」檢定；不挑特徵、不做顯著性。
⛔ 不 commit、不改既有程式與結果夾；researchIndMom_freq（build_panel 快取、讀法 I1）、researchPTH_freq（month_ends）、researchIndRev_prereg（load_rev、PIT）、
   research11（load_bars）、researchLongPool（load_filing、load_fs、load_fin、single、qkey）⛔ 只 import。私有資料（us-stock-data、taifex_private）⛔ 不讀。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBigRun [--procs 2] [--limit N --out DIR（乾跑）]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBigRun_check
輸出 backtest/resultsBigRun/：freq_甲.csv、freq_乙.csv、甲_段.csv、甲_貢獻前5.csv、甲_窗.csv.gz、ind_index.csv.gz、乙_段_x3.csv.gz、乙_段_x5.csv.gz、
     乙_年.csv、乙_產業.csv、乙_重疊.csv、丙_乙彙總.csv、丙_缺欄.csv、bigrun.json、run.log

═══ 讀法（B 標；★＝執行者定，〔 〕內為另一讀法）═══
 B1 世界、價格 ＝ researchIndMom_freq.build_panel 快取（＝ researchAscTri_freq.load_world＋research11.load_bars，讀法 I1）：主 ＝ rerun17 快照 H2D
    （2015-01-05～2026-09-24）、早年 ＝ eotc_f65bb03e11（2004-02-11～2014-12-31，上市＋上櫃；上櫃 2007-07 前無價）；UG.gate3(GATE_V2) ∩ 四碼普通股、
    含已下市；load_bars ＜ 260 根不進（該世界）。還原收盤（除權息、減資、面額；含息）。壞根 ＝ load_bars next_bad（缺口 ≥ 5 日 seq335、斷點、幽靈還原）
    ∪ crashwork ∪ 早年 reduce_v2（seq335 新件早年用 reduce_v2，約 0.3% 註）。
    ★ 兩世界首尾相接成合併日曆；同代號兩段接起來，跨接縫價格比 ＝ 早年段還原比 × 接縫【原始】收盤比 × 主段還原比（researchLong3 L11 同式）；
      接縫前後最後／第一根相隔 ≥ 5 交易日或原始收盤缺 ⇒ 主段第一根當壞根（seq335）。
 B2 產業別 ＝ researchIndRev_prereg.PIT（industry_pit；無 ⇒ 月營收彙總表當時類別）；資料 ＝ tw-stock-data origin/main（SHA 常數）git archive 唯讀。
    ★ 每個曆月成員 ＝ 上月最後交易日 b 的 PIT 類別；排除「其他」「綜合」「存託憑證」「ETF」與無類別（researchIndMom I4 同）；金融保險納入；上市上櫃同名一類。
    ★ 成員條件：b 當天或之前 20 交易日內有有效 K 棒 ∧ b 的市值（原始收盤 × 股數，ffill）＞ 0；市值缺者兩版都不進（I5 同，兩版同一批成員）。
 B3 產業指數（甲）：★ 每月初重設權重、月內買進持有：成員日報酬 r ＝ 有效 K 棒還原收盤比（壞根那一根 r ＝ 0，即跳過斷點；無成交日 r ＝ 0）；
    市值加權 W0 ＝ b 的市值、等權 W0 ＝ 1；月內 V(t) ＝ Σ W0·g(t) ÷ Σ W0（g ＝ b 之後累乘 1＋r）；I(t) ＝ I(b)·V(t)。
    當月成員 ＜ 5 ⇒ 該月指數缺、鏈斷；之後重新以 1 起算（新鏈）；跨鏈的窗不算。下市股最後一根後 r ＝ 0（當現金，下市報酬不明）。
 B4 滾動 3 年（甲）：評估點 ＝ 合併日曆每個完整曆月最後交易日（researchPTH_freq.month_ends；資料尾 2026-09 不完整月不算 ⇒ 最後評估點 2026-08-31）；
    窗 ＝ (第 j−36 個月底, 第 j 個月底]；★ 窗起點 ≥ 2004-12-31（＝ 從 2005-01 起算）。R產業 ＝ I(t) ÷ I(a) − 1；R0050 ＝ 0050 還原收盤同窗（兩世界 load_bars
    跨接縫同 B1）。達標 ＝ R產業 ≥ 2 × R0050 ∧ R產業 ≥ +100%（R0050 ＜ 0 時第一條自動成立，照字面）。
    ★ 同產業兩個達標窗 j1 ＜ j2，j2 − 36 ≤ j1（區間相交或首尾相接）⇒ 併成一段。起點 S ＝ 首個達標窗起點；高點 H ＝ [S, 最後達標窗終點] 內 I 的最高日；
    漲幅 ＝ I(H) ÷ I(S) − 1；對 0050 ＝ 同期 0050 報酬，另報 差（漲幅 − R0050）與 倍數（(1＋漲幅) ÷ (1＋R0050)）；
    高點後 12 個月最大跌幅 ＝ (H, H＋12 曆月] 內同一鏈 I 最低 ÷ I(H) − 1（不足 12 個月照算並標「未滿12月」）。
    段內貢獻 ＝ Σ_月 I(b)/I(S) × W0_i(g_i(月末或 H) − 1)/ΣW0（各股貢獻加總 ＝ 漲幅，逐段驗）；報前 5 檔與占漲幅比。市值加權為主表、等權並報（各自成段）。
 B5 個股大漲段（乙）：★ 候選起點 ＝ 每個完整月底；起點那根 ＝ 該月最後一根有效 K 棒（該月沒有成交 ⇒ 不是候選）；P0 ＝ 其還原收盤。
    窗 ＝ 起點之後、日期 ≤ 起點日 ＋ 3 曆年（×5 版 5 年）的有效 K 棒；遇窗內第一個壞根 ⇒ 只看壞根之前（不跨斷點）；資料尾、下市 ⇒ 看到哪算到哪（標旗）。
    達標 ＝ 窗內最高收盤 ≥ 3 × P0（×5 版 5 × P0）。依時間序取最早達標的候選月底為一段；高點 ＝ 窗內最高收盤那天；
    「同一檔重疊只取第一段」★ ＝ 下一個候選起點必須在上一段高點之後。⭐ 起點只用「月底」這個事先固定的時點（不是事後挑的最低點），定義本身不看起點之後的
    價格以外資訊；但大漲段本來就是事後圈出來的（描述用）。起點 ≥ 2004-12-31 月底。
    與甲重疊 ★ ＝ 該股起點當時 PIT 產業有甲段（市值加權；等權並報）且兩區間 [起點, 高點] 相交；另報「起點落在甲段內」。
 B6 丙（當時樣貌）：三個時點 ＝ 起點前 12 個月（起點日 − 12 曆月，當天或之前最後交易日）、起點、高點；流量（外資＋投信）報兩段：前 12 月→起點、起點→高點。
    ⭐ 一律只用該時點 d「已公開」的資料：
    月營收年增 ＝ revenue_hist（早年 early/revenue）同一份公告的 當月營收 ÷ 去年當月營收 − 1（公告當時口徑）；可用 ＝ 期別次月 10 日之後（2026-01 期起 15 日之後，
      嚴格大於）＜ d 的最新期別；★ 該股最新期缺 ⇒ 往前最多 2 期；data/meta/revenue_delisted 只補 revenue_hist 沒有的股-期格（去年當月 ＝ 補檔 12 期前值）。
    財報（毛利率、存貨天數、資本支出）可用日 ＝ filing_dates（t57sb01）uploaded_at ★ 同 (代號, 年, 季) 有 AI1（合併財報）⇒ AI1 最早一筆，否則全部文件最早一筆
      （researchLongPool.load_filing；只取上傳日 ＜ d 的季，seq352）；沒有時戳的季 ⇒ 不用（⛔ 不補法定期限）。單季 ＝ 年初累計差分（Q1 不減）；
      營收、成本、毛利 ＝ fs_hist 一般業 ci（2015 起）★ 逐季缺才退 fin_hist（2013 起，rev_ytd、gp_ytd）；毛利率 ＝ 單季毛利 ÷ 單季營收；毛利率年變化 ＝ 本季 − 去年同季（百分點）；
      存貨天數 ＝ fs_xbrl inventories（期末，cr 合併優先）÷ 單季營業成本 × 91.25；資本支出 ＝ −fs_xbrl capex_ytd 差分成單季，近 4 季合計（TTM）的年增率、÷ 營收 TTM。
    本益比 5 年位置 ＝ 官方 per（主 stocks_per 2015 起；早年 early/per、early/otcper 2012 起）★ per ≤ 0 或缺 ⇒ 缺；含 d 最近 1250 個合併日曆交易日中有值 ≥ 750 天才算，
      位置 ＝ 有值日中 ≤ 當天值的比例（researchLongPool 同式）。
    股價距一年高點 ＝ d 當天或之前最後一根還原收盤 ÷ 最近 250 個交易日（含 d）最高還原收盤 − 1；★ 窗內有壞根 ⇒ 只看最後一個壞根（含）之後。
    外資＋投信持股變化 ＝ (d1, d2] 外資＋投信買賣超股數合計 ÷ d2 股數（stocks_inst；主 2015-01-05 起、早年上市 2012-05 起有檔者；★ 該日無列 ＝ 0）；涵蓋起點晚於 d1 ⇒ 缺。
    0050 在 200 日線上下 ＝ 0050 還原收盤 ÷ 最近 200 根有效 K 棒收盤平均 − 1（＞ 0 ＝ 上）；⚠ 我方 0050 資料 2004-02-11 起（非 2003）⇒ 2004-11-29 起才有值。
    ★「前12月」早於合併日曆首日（2004-02-11）⇒ 日期型欄（月營收、財報）照該日期算，位置型欄（本益比位置、距一年高點、0050、法人）記缺、標「前12月早於資料首日」。
    ⚠ industry_pit 的「電子工業」只到 2007-05-15（之後拆成半導體業等）⇒ 2005～2007 起點的電子類 3 年窗湊不滿、不會出現在甲（照字面，照實寫）。
    甲（產業層）每段：★ 加總口徑 ＝ Σ 分子 ÷ Σ 分母（營收 Σ當月 ÷ Σ去年當月、毛利 Σ毛利 ÷ Σ營收、存貨 Σ存貨 ÷ Σ成本、資本支出 ΣTTM），法人 ＝ 成員比例的 d2 市值加權平均；
      另報成員中位數；距一年高點用該段自己的產業指數；成員 ＝ d 所在月份的 B2 成員。乙 ＝ 逐段值，彙總報 n、涵蓋率、中位、p25、p75（全期、2005～2014 起點、2015 起起點）。
 B7 必附：「2015～2020 下市公司月營收約 80 家補不回」「上櫃 2007-07 前無價」「描述，不是選股規則」；早年 reduce_v2 約 0.3% 註（seq335）。
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
import os
import subprocess
import sys
import time
from collections import Counter, defaultdict
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchIndMom_freq as IMF             # noqa: E402  build_panel（快取）（⛔ 只 import）
from backtest import researchPTH_freq as PF                 # noqa: E402  month_ends
from backtest import researchIndRev_prereg as PRE           # noqa: E402  load_rev、PIT
from backtest import research11 as R                        # noqa: E402  load_bars
from backtest import researchLongPool as LP                 # noqa: E402  load_filing、load_fs、load_fin、single、qkey
import backtest.data as D                                   # noqa: E402

SHA = "dbfb96cb81a7d3032e07fe47d1aeb5f0230545fa"
WORK = os.path.expanduser("~/bgrwork")
ARCH = ["data/meta/industry_hist", "data/meta/industry.csv", "data/meta/stocks.csv", "data/mops/revenue_hist", "data/early/revenue",
        "data/meta/revenue_delisted", "data/meta/fs_xbrl", "data/meta/filing_dates.csv", "data/mops/fs_hist", "data/mops/fin_hist",
        "data/early/per", "data/early/otcper"]
OUT = "backtest/resultsBigRun"
EXCL_IND = {"其他", "綜合", "存託憑證", "ETF", ""}
MINMEM = 5
START = pd.Timestamp("2004-12-31")
WIN_M = 36
ALIVE = 20
DAYS_Q = 91.25
INST_EARLY = pd.Timestamp("2012-05-02")
NOTES = ["2015～2020 下市公司月營收約 80 家補不回", "上櫃 2007-07 前無價", "描述，不是選股規則",
         "早年壞根含 reduce_v2（約 0.3% 股日）（seq335）", "大漲段是事後圈出來的；丙只列數字、不做顯著性、不挑特徵"]
PTS = ("前12月", "起點", "高點")
LOG: list = []
_G: dict = {}


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def ensure_arch():
    root = os.path.join(WORK, f"main_{SHA[:12]}")
    if not os.path.isfile(os.path.join(root, ".done")):
        subprocess.run(["git", "cat-file", "-e", SHA], check=True)
        os.makedirs(root, exist_ok=True)
        p = subprocess.run(["git", "archive", "--format=tar", SHA] + ARCH, capture_output=True, check=True)
        subprocess.run(["tar", "-x", "-C", root], input=p.stdout, check=True)
        open(os.path.join(root, ".done"), "w").write(SHA)
    return os.path.join(root, "data")


def qd(a):
    a = np.asarray([x for x in a if x is not None and np.isfinite(x)], float)
    if len(a) == 0:
        return {"n": 0}
    return {"n": int(len(a)), "中位": float(np.median(a)), "p25": float(np.percentile(a, 25)), "p75": float(np.percentile(a, 75))}


# ═════════════ 逐股輔助（原始收盤、股數、per、法人）═════════════
def aux_job(sid):
    G = _G
    NC = G["NC"]
    out = {"sid": sid, "name": "", "rc_e": np.nan, "rc_m": np.nan, "sh": np.full(NC, np.nan, np.float32),
           "per": np.full(NC, np.nan, np.float32), "inst": np.zeros(NC, np.float32), "inst_cov": -1}
    pe, pm = G["SEAM"].get(sid, (-1, -1))
    for wn, data, off, cal in G["PARTS"]:
        f = os.path.join(data, "stocks", f"{sid}.csv")
        if not os.path.exists(f):
            continue
        x = pd.read_csv(f, dtype={"date": str}, usecols=["date", "name", "close", "shares"]).drop_duplicates("date", keep="last")
        dt = pd.to_datetime(x["date"]); ix = cal.get_indexer(dt); ok = ix >= 0
        pos = ix[ok] + off
        sh = pd.to_numeric(x["shares"], errors="coerce").to_numpy(float)[ok]
        out["sh"][pos] = sh
        if len(x):
            out["name"] = str(x["name"].iloc[-1])
        cl = pd.to_numeric(x["close"], errors="coerce").to_numpy(float)[ok]
        if wn == "早年" and pe >= 0:
            k = np.flatnonzero(pos == pe)
            out["rc_e"] = float(cl[k[0]]) if len(k) else np.nan
        if wn == "主" and pm >= 0:
            k = np.flatnonzero(pos == pm)
            out["rc_m"] = float(cl[k[0]]) if len(k) else np.nan
        fi = os.path.join(data, "stocks_inst", f"{sid}.csv")
        if os.path.exists(fi):
            y = pd.read_csv(fi, dtype={"date": str}, usecols=["date", "foreign", "trust"]).drop_duplicates("date", keep="last")
            iy = cal.get_indexer(pd.to_datetime(y["date"])); oky = iy >= 0
            v = (pd.to_numeric(y["foreign"], errors="coerce").fillna(0) + pd.to_numeric(y["trust"], errors="coerce").fillna(0)).to_numpy(float)
            out["inst"][iy[oky] + off] = v[oky]
            if wn == "早年" and G["MK_E"].get(sid) == "twse" and oky.any():
                out["inst_cov"] = int(max(iy[oky].min(), int(cal.searchsorted(INST_EARLY))) + off) if out["inst_cov"] < 0 else out["inst_cov"]
        if wn == "主":
            if out["inst_cov"] < 0:
                out["inst_cov"] = off
            fp = os.path.join(data, "stocks_per", f"{sid}.csv")
            if os.path.exists(fp):
                z = pd.read_csv(fp, dtype={"date": str}, usecols=["date", "per"]).drop_duplicates("date", keep="last")
                iz = cal.get_indexer(pd.to_datetime(z["date"])); okz = iz >= 0
                pv = pd.to_numeric(z["per"], errors="coerce").to_numpy(float)[okz]
                out["per"][iz[okz] + off] = np.where(pv > 0, pv, np.nan)
    out["sh"] = pd.Series(out["sh"]).ffill().to_numpy(np.float32)
    return out


# ═════════════ 財報 ═════════════
def load_xbrl_full(FD, ids):
    L = []
    for f in sorted(glob.glob(os.path.join(FD, "meta", "fs_xbrl", "fs_xbrl_*.csv"))):
        x = pd.read_csv(f, dtype={"stock_id": str}, usecols=["period", "stock_id", "report", "inventories", "capex_ytd"])
        x = x[x["stock_id"].isin(ids)].copy()
        x["_r"] = (x["report"] != "cr").astype(int)
        x = x.sort_values(["stock_id", "period", "_r"]).drop_duplicates(["stock_id", "period"], keep="first")
        x["qk"] = [LP.qkey(p[:4], p[-1]) for p in x["period"]]
        L.append(x)
    X = pd.concat(L)
    for c in ("inventories", "capex_ytd"):
        X[c] = pd.to_numeric(X[c], errors="coerce")
    return {s: g.set_index("qk").sort_index() for s, g in X.groupby("stock_id")}


def build_quarterly(FD, ids, QK0, QK1):
    fmin, fsrc = LP.load_filing(FD)
    FS = LP.load_fs(FD, set(ids), QK0, QK1); FN = LP.load_fin(FD, set(ids), QK0, QK1); XB = load_xbrl_full(FD, set(ids))
    KS = np.arange(QK0, QK1 + 1)
    Q = {}
    for s in ids:
        fs, fn, xb = FS.get(s), FN.get(s), XB.get(s)
        n = len(KS)
        rev = np.full(n, np.nan); gp = np.full(n, np.nan); cogs = np.full(n, np.nan); inv = np.full(n, np.nan); cap = np.full(n, np.nan)
        src = np.zeros(n, np.int8); av = np.full(n, np.datetime64("NaT"), "datetime64[ns]")
        for j, k in enumerate(KS):
            r1 = c1 = g1 = np.nan
            if fs is not None and k in fs.index:
                r1 = LP.single(fs["營業收入"], k); c1 = LP.single(fs["營業成本"], k)
                gpn = fs["營業毛利（毛損）淨額"] if fs["營業毛利（毛損）淨額"].notna().any() else fs["營業毛利（毛損）"]
                g1 = LP.single(gpn, k)
            if np.isfinite(r1) and np.isfinite(g1):
                rev[j], gp[j] = r1, g1; cogs[j] = c1 if np.isfinite(c1) else r1 - g1; src[j] = 1
            elif fn is not None and k in fn.index:
                r2 = LP.single(fn["rev_ytd"], k); g2 = LP.single(fn["gp_ytd"], k)
                if np.isfinite(r2):
                    rev[j] = r2; gp[j] = g2; cogs[j] = r2 - g2 if np.isfinite(g2) else np.nan; src[j] = 2
            if xb is not None and k in xb.index:
                inv[j] = xb["inventories"].get(k, np.nan)
                cy = LP.single(xb["capex_ytd"], k)
                cap[j] = -cy if np.isfinite(cy) else np.nan
            t = fmin.get((s, int(k)))
            if t is not None:
                av[j] = np.datetime64(pd.Timestamp(t).normalize())
        Q[s] = {"rev": rev, "gp": gp, "cogs": cogs, "inv": inv, "cap": cap, "src": src, "av": av}
    return Q, KS, fsrc


# ═════════════ 主程式 ═════════════
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    out_dir = a.out
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    DATA = ensure_arch()
    log(f"[資料] tw-stock-data origin/main {SHA[:12]} ⇒ {DATA}")
    Ze = IMF.build_panel("早年", a.procs, log); Zm = IMF.build_panel("主", a.procs, log)
    CAL = Ze["cal"].append(Zm["cal"]); NE = Ze["n0"]; NC = len(CAL); CEND = NC - 1
    cpos_le = lambda ts: int(CAL.searchsorted(pd.Timestamp(ts), side="right")) - 1
    log(f"[合併日曆] {CAL[0].date()}～{CAL[-1].date()}｜{NC} 日（早年 {NE}）")
    ie = {s: k for k, s in enumerate(Ze["sids"])}; im = {s: k for k, s in enumerate(Zm["sids"])}
    SIDS = sorted(set(ie) | set(im))
    if a.limit:
        rng = np.random.default_rng(531)
        SIDS = sorted(set(rng.choice(SIDS, a.limit, replace=False)) | {"2330", "2454", "2303", "3008", "2317", "2603", "2609", "3443", "1513", "6669"})
    N = len(SIDS); IX = {s: i for i, s in enumerate(SIDS)}
    C = np.full((N, NC), np.nan); BAD = np.zeros((N, NC), bool); MC = np.full((N, NC), np.nan)
    SEAM = {}
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
    # 逐股輔助
    _G.update({"NC": NC, "SEAM": SEAM, "MK_E": Ze["mk"],
               "PARTS": [("早年", Ze["data"], 0, Ze["cal"]), ("主", Zm["data"], NE, Zm["cal"])]})
    AUX = {}
    with Pool(a.procs) as pool:
        for k_, r in enumerate(pool.imap_unordered(aux_job, SIDS, chunksize=8)):
            AUX[r["sid"]] = r
            if (k_ + 1) % 500 == 0:
                log(f"  逐股輔助 {k_ + 1}／{N}｜{time.time() - t0:.0f}s")
    seam_info = Counter()
    for s, (pe, pm) in SEAM.items():
        i = IX[s]; seam_info["兩世界都有"] += 1
        re_, rm_ = AUX[s]["rc_e"], AUX[s]["rc_m"]
        Mf = C[i, pe] * rm_ / (re_ * C[i, pm]) if (np.isfinite(re_) and np.isfinite(rm_) and re_ > 0 and C[i, pm] > 0) else np.nan
        if np.isfinite(Mf) and Mf > 0:
            C[i, NE:] *= Mf
        gap = pm - pe - 1
        if not (np.isfinite(Mf) and Mf > 0):
            BAD[i, pm] = True; seam_info["接縫原始收盤缺⇒壞根"] += 1
        elif gap >= 5:
            BAD[i, pm] = True; seam_info["接縫相隔≥5交易日⇒壞根"] += 1
        else:
            BAD[i, pm] = False
    log(f"[接縫] {dict(seam_info)}")
    # 早年 per（上市＋上櫃日檔）
    PER = np.stack([AUX[s]["per"] for s in SIDS])
    L = []
    for sub in ("per", "otcper"):
        for f in sorted(glob.glob(os.path.join(DATA, "early", sub, "*.csv"))):
            L.append(pd.read_csv(f, dtype={"stock_id": str, "date": str}, usecols=["date", "stock_id", "per"]))
    ep = pd.concat(L, ignore_index=True)
    ep["per"] = pd.to_numeric(ep["per"], errors="coerce"); ep = ep[ep["per"] > 0]
    ep = ep[ep["stock_id"].isin(IX)].drop_duplicates(["date", "stock_id"], keep="last")
    pi = Ze["cal"].get_indexer(pd.to_datetime(ep["date"])); okp = pi >= 0
    PER[[IX[s] for s in ep["stock_id"][okp]], pi[okp]] = ep["per"].to_numpy(float)[okp]
    log(f"[per] 早年日檔 {len(L)} 個、{int(okp.sum())} 股日；主 stocks_per")
    SH = np.stack([AUX[s]["sh"] for s in SIDS]); INST = np.stack([AUX[s]["inst"] for s in SIDS])
    INSTCOV = np.array([AUX[s]["inst_cov"] for s in SIDS]); NAME = {s: AUX[s]["name"] for s in SIDS}
    del AUX
    # 有效 K 棒、日報酬
    VP, VC, VB, NB = [], [], [], []
    RR = np.zeros((N, NC))
    for i in range(N):
        vp = np.flatnonzero(np.isfinite(C[i])); vc = C[i, vp]; vb = BAD[i, vp].copy()
        if len(vp) > 1:
            r = vc[1:] / vc[:-1] - 1.0
            r[vb[1:]] = 0.0
            RR[i, vp[1:]] = r
        nb = np.full(len(vp) + 1, len(vp) + 10, np.int64)
        for k in range(len(vp) - 1, -1, -1):
            nb[k] = k if vb[k] else nb[k + 1]
        VP.append(vp); VC.append(vc); VB.append(vb); NB.append(nb)
    LASTV = np.full((N, NC), -1, np.int32)   # 日曆位置 p 當天或之前最後一根有效 K 棒的日曆位置
    for i in range(N):
        ar = np.full(NC, -1, np.int32); ar[VP[i]] = VP[i]
        LASTV[i] = np.maximum.accumulate(ar)
    log(f"[價格] {N} 檔｜{time.time() - t0:.0f}s")
    # 0050
    B50 = {}
    for wn, Z in (("早年", Ze), ("主", Zm)):
        D.DATA = Z["data"]
        B50[wn] = R.load_bars("0050", "twse", Z["cal"])
    idx50 = np.concatenate([B50["早年"]["idx"].astype(np.int64), B50["主"]["idx"].astype(np.int64) + NE])
    c50 = np.concatenate([B50["早年"]["c"], B50["主"]["c"]]).astype(float)
    rc50 = np.concatenate([B50["早年"]["rc"], B50["主"]["rc"]]).astype(float)
    j50 = len(B50["早年"]["idx"])
    M50 = c50[j50 - 1] * rc50[j50] / (rc50[j50 - 1] * c50[j50]); c50[j50:] *= M50
    dr50 = c50[1:] / c50[:-1] - 1
    if abs(dr50).max() > 0.2:
        raise SystemExit("⛔ 0050 還原序列有 > 20% 單日跳動")
    log(f"[0050] {CAL[idx50[0]].date()}～{CAL[idx50[-1]].date()}｜{len(idx50)} 根｜接縫 M {M50:.4f}")

    def v50(p):
        k = int(np.searchsorted(idx50, p, "right")) - 1
        return c50[k] if k >= 0 else np.nan

    def ma200_50(p):
        k = int(np.searchsorted(idx50, p, "right")) - 1
        if k < 199:
            return np.nan
        return c50[k] / c50[k - 199:k + 1].mean() - 1.0

    # 產業別、月營收
    rev, rev_ly, cat, mkr, nf, nr = PRE.load_rev(DATA)
    PIT = PRE.PIT(DATA, cat)
    log(f"[月營收] {nf} 檔 {nr} 列｜期別 {rev.index[0]}～{rev.index[-1]}")
    rd = pd.read_csv(os.path.join(DATA, "meta", "revenue_delisted", "revenue_delisted.csv"), dtype=str)
    rd["v"] = pd.to_numeric(rd["revenue_k"], errors="coerce")
    rdp = rd.pivot_table(index="period", columns="stock_id", values="v", aggfunc="last")
    nfill = 0
    for s in rdp.columns:
        if s not in rev.columns:
            rev[s] = np.nan; rev_ly[s] = np.nan
        for p, v in rdp[s].dropna().items():
            if p in rev.index and not np.isfinite(rev.at[p, s]):
                rev.at[p, s] = v; nfill += 1
                p12 = PRE.mshift(p, -12)
                if p12 in rdp.index and np.isfinite(rdp.at[p12, s]):
                    rev_ly.at[p, s] = rdp.at[p12, s]
                elif p12 in rev.index:
                    rev_ly.at[p, s] = rev.at[p12, s]
    log(f"[月營收] revenue_delisted 補 {nfill} 格（{rdp.shape[1]} 家）")
    PERIODS = list(rev.index)
    AVR = np.array([np.datetime64(LP.rev_avail(p)) for p in PERIODS], "datetime64[ns]")
    if not (np.diff(AVR.astype(np.int64)) > 0).all():
        raise SystemExit("⛔ 月營收可用日非遞增")
    REVA = {s: rev[s].to_numpy(float) for s in rev.columns}; LYA = {s: rev_ly[s].to_numpy(float) for s in rev.columns}

    def rev_at(s, d):
        """d ＝ Timestamp。回 (年增, 當月, 去年當月, 期別)。可用日 ＜ d（嚴格）。"""
        if s not in REVA:
            return np.nan, np.nan, np.nan, ""
        km = int(np.searchsorted(AVR, np.datetime64(d), "left")) - 1
        for k in range(km, max(km - 3, -1), -1):
            v, l = REVA[s][k], LYA[s][k]
            if np.isfinite(v):
                return (v / l - 1 if (np.isfinite(l) and l > 0) else np.nan), v, l, PERIODS[k]
        return np.nan, np.nan, np.nan, ""

    # 財報
    Q, KS, fsrc = build_quarterly(DATA, SIDS, LP.qkey(2012, 1), LP.qkey(2026, 4))
    log(f"[財報] {len(Q)} 檔｜季 {LP.qlabel(KS[0])}～{LP.qlabel(KS[-1])}｜{time.time() - t0:.0f}s")

    def fs_at(s, d):
        q = Q.get(s)
        res = {"毛利率": np.nan, "毛利率年變化": np.nan, "存貨天數": np.nan, "資本支出TTM年增": np.nan, "資本支出÷營收TTM": np.nan,
               "_財報季": "", "_財報可用": "", "_rev": np.nan, "_gp": np.nan, "_rev4": np.nan, "_gp4": np.nan, "_inv": np.nan, "_cogs": np.nan,
               "_cap": np.nan, "_cap4": np.nan, "_revttm": np.nan}
        if q is None:
            return res
        ok = np.flatnonzero(~np.isnat(q["av"]) & (q["av"] < np.datetime64(d)))
        if not len(ok):
            return res
        j = int(ok.max())
        res["_財報季"] = LP.qlabel(int(KS[j])); res["_財報可用"] = str(pd.Timestamp(q["av"][j]).date())
        r, g = q["rev"][j], q["gp"][j]
        if np.isfinite(r) and np.isfinite(g) and r > 0:
            res["毛利率"] = g / r; res["_rev"], res["_gp"] = r, g
            if j >= 4 and np.isfinite(q["rev"][j - 4]) and np.isfinite(q["gp"][j - 4]) and q["rev"][j - 4] > 0:
                res["毛利率年變化"] = g / r - q["gp"][j - 4] / q["rev"][j - 4]; res["_rev4"], res["_gp4"] = q["rev"][j - 4], q["gp"][j - 4]
        iv, cg = q["inv"][j], q["cogs"][j]
        if np.isfinite(iv) and np.isfinite(cg) and cg > 0:
            res["存貨天數"] = iv / cg * DAYS_Q; res["_inv"], res["_cogs"] = iv, cg
        if j >= 7:
            c4 = q["cap"][j - 3:j + 1]; c4o = q["cap"][j - 7:j - 3]; r4 = q["rev"][j - 3:j + 1]
            if np.isfinite(c4).all():
                res["_cap"] = c4.sum()
                if np.isfinite(c4o).all() and c4o.sum() > 0:
                    res["資本支出TTM年增"] = c4.sum() / c4o.sum() - 1; res["_cap4"] = c4o.sum()
                if np.isfinite(r4).all() and r4.sum() > 0:
                    res["資本支出÷營收TTM"] = c4.sum() / r4.sum(); res["_revttm"] = r4.sum()
        return res

    def pe_pos(i, p):
        v = PER[i, p]
        if not np.isfinite(v):
            return np.nan
        w = PER[i, max(0, p - 1249):p + 1]; w = w[np.isfinite(w)]
        return float((w <= v).mean()) if len(w) >= 750 else np.nan

    def dist_hi(i, p):
        vp = VP[i]
        k1 = int(np.searchsorted(vp, p, "right")) - 1
        if k1 < 0 or p - vp[k1] > ALIVE:
            return np.nan
        k0 = int(np.searchsorted(vp, p - 249, "left"))
        bb = np.flatnonzero(VB[i][k0 + 1:k1 + 1])
        if len(bb):
            k0 = k0 + 1 + int(bb[-1])
        return float(VC[i][k1] / VC[i][k0:k1 + 1].max() - 1.0)

    def inst_chg(i, p1, p2):
        if INSTCOV[i] < 0 or p1 < INSTCOV[i] or p2 <= p1:
            return np.nan
        sh = SH[i, p2]
        if not (np.isfinite(sh) and sh > 0):
            return np.nan
        return float(INST[i, p1 + 1:p2 + 1].sum() / sh)

    def stock_feats(i, s, pts):
        """pts ＝ {名: 日曆位置}。回 dict。"""
        o = {}
        for nm, (p, d) in pts.items():
            y, v, l, per = rev_at(s, d)
            o[f"營收年增@{nm}"] = y; o[f"營收期別@{nm}"] = per
            f = fs_at(s, d)
            for k in ("毛利率", "毛利率年變化", "存貨天數", "資本支出TTM年增", "資本支出÷營收TTM"):
                o[f"{k}@{nm}"] = f[k]
            o[f"財報季@{nm}"] = f["_財報季"]; o[f"財報可用@{nm}"] = f["_財報可用"]
            o[f"本益比5年位置@{nm}"] = pe_pos(i, p) if p >= 0 else np.nan
            o[f"距一年高點@{nm}"] = dist_hi(i, p) if p >= 0 else np.nan
            o[f"0050乖離200日@{nm}"] = ma200_50(p) if p >= 0 else np.nan
        o["外資投信持股變化@前12月→起點"] = inst_chg(i, pts["前12月"][0], pts["起點"][0]) if pts["前12月"][0] >= 0 else np.nan
        o["外資投信持股變化@起點→高點"] = inst_chg(i, pts["起點"][0], pts["高點"][0])
        return o

    # ═════════ 甲：每月成員、產業指數 ═════════
    ym = CAL.year * 12 + CAL.month
    mstart = np.flatnonzero(np.r_[True, ym[1:] != ym[:-1]])
    mend = np.r_[mstart[1:] - 1, NC - 1]
    MONTHS = []   # (b, e)
    for k in range(1, len(mstart)):
        MONTHS.append((int(mstart[k] - 1), int(mend[k])))
    MEMB = []     # 每月 {產業: idx array}
    for (b, e) in MONTHS:
        d = CAL[b]
        lv = LASTV[:, b]
        alive = (lv >= 0) & (b - lv <= ALIVE) & np.isfinite(MC[:, b]) & (MC[:, b] > 0)
        mm = defaultdict(list)
        for i in np.flatnonzero(alive):
            ind, src = PIT.at(SIDS[i], d)
            if ind is None or ind in EXCL_IND:
                continue
            mm[ind].append(i)
        MEMB.append({k: np.array(v, np.int64) for k, v in mm.items()})
    INDS = sorted({k for m in MEMB for k in m})
    log(f"[甲] 月份 {len(MONTHS)}｜產業 {len(INDS)}｜{time.time() - t0:.0f}s")
    IDX = {kd: {ind: np.full(NC, np.nan) for ind in INDS} for kd in ("vw", "ew")}
    CH = {kd: {ind: np.full(NC, -1, np.int64) for ind in INDS} for kd in ("vw", "ew")}
    NMEM = {ind: np.zeros(len(MONTHS), np.int64) for ind in INDS}
    chain_no = 0
    for mi, (b, e) in enumerate(MONTHS):
        Gm = np.cumprod(1.0 + RR[:, b + 1:e + 1], axis=1)
        for ind, idxs in MEMB[mi].items():
            NMEM[ind][mi] = len(idxs)
            if len(idxs) < MINMEM:
                continue
            for kd in ("vw", "ew"):
                W0 = MC[idxs, b] if kd == "vw" else np.ones(len(idxs))
                V = (W0[:, None] * Gm[idxs]).sum(0) / W0.sum()
                I_ = IDX[kd][ind]; H_ = CH[kd][ind]
                if not np.isfinite(I_[b]):
                    chain_no += 1; I_[b] = 1.0; H_[b] = chain_no
                I_[b + 1:e + 1] = I_[b] * V; H_[b + 1:e + 1] = H_[b]
    log(f"[甲] 指數完｜鏈 {chain_no}｜{time.time() - t0:.0f}s")
    ME, MK = PF.month_ends(CAL)
    jst = int(np.searchsorted(CAL[ME], START, "left"))
    WROWS = []
    HITS = {kd: defaultdict(list) for kd in ("vw", "ew")}
    for j in range(jst + WIN_M, len(ME)):
        pa, pt = int(ME[j - WIN_M]), int(ME[j])
        r50 = v50(pt) / v50(pa) - 1.0
        for ind in INDS:
            row = None
            for kd in ("vw", "ew"):
                I_, H_ = IDX[kd][ind], CH[kd][ind]
                if H_[pa] < 0 or H_[pa] != H_[pt]:
                    continue
                rr = I_[pt] / I_[pa] - 1.0
                hit = bool(rr >= 1.0 and rr >= 2.0 * r50)
                if row is None:
                    row = {"產業": ind, "窗起": str(CAL[pa].date()), "窗終": str(CAL[pt].date()), "R0050": r50}
                row[f"R_{kd}"] = rr; row[f"達標_{kd}"] = hit
                if hit:
                    HITS[kd][ind].append(j)
            if row is not None:
                WROWS.append(row)
    log(f"[甲] 窗 {len(WROWS)} 列｜達標窗 市值 {sum(len(v) for v in HITS['vw'].values())}、等權 {sum(len(v) for v in HITS['ew'].values())}")

    MB = np.array([b for b, e in MONTHS]); MEND = np.array([e for b, e in MONTHS])

    def mi_of(p):
        k = int(np.searchsorted(MEND, p, "left"))
        return k if k < len(MONTHS) and MB[k] < p <= MEND[k] else -1

    def contrib(kd, ind, S, H):
        I_ = IDX[kd][ind]
        acc = defaultdict(float)
        k0 = mi_of(S + 1)
        for mi in range(k0, len(MONTHS)):
            b, e = MONTHS[mi]
            if b >= H:
                break
            end = min(e, H)
            idxs = MEMB[mi][ind]
            W0 = MC[idxs, b] if kd == "vw" else np.ones(len(idxs))
            g = np.prod(1.0 + RR[idxs, b + 1:end + 1], axis=1)
            cc = I_[b] / I_[S] * W0 * (g - 1.0) / W0.sum()
            for i, v in zip(idxs, cc):
                acc[int(i)] += float(v)
        return acc

    def ind_feats(kd, ind, pts, S, H):
        o = {}
        I_, H_ = IDX[kd][ind], CH[kd][ind]
        for nm, (p, d) in pts.items():
            mi = mi_of(p) if p >= 0 else -1
            idxs = MEMB[mi].get(ind, np.array([], np.int64)) if mi >= 0 else np.array([], np.int64)
            o[f"成員數@{nm}"] = len(idxs)
            sv = sl = 0.0; gpa = rva = gpb = rvb = 0.0; iv = cg = 0.0; ca = ca4 = 0.0; cb = rt = 0.0
            mem = defaultdict(list); nrev = nfs = 0; pers = Counter(); fq = Counter()
            for i in idxs:
                s = SIDS[i]
                y, v, l, per = rev_at(s, d)
                if np.isfinite(v) and np.isfinite(l) and l > 0:
                    sv += v; sl += l; nrev += 1; pers[per] += 1
                if np.isfinite(y):
                    mem["營收年增"].append(y)
                f = fs_at(s, d)
                if f["_財報季"]:
                    fq[f["_財報季"]] += 1
                if np.isfinite(f["_rev"]):
                    gpa += f["_gp"]; rva += f["_rev"]; nfs += 1
                    if np.isfinite(f["_rev4"]):
                        gpb += f["_gp4"]; rvb += f["_rev4"]
                if np.isfinite(f["_inv"]):
                    iv += f["_inv"]; cg += f["_cogs"]
                if np.isfinite(f["_cap4"]):
                    ca += f["_cap"]; ca4 += f["_cap4"]
                if np.isfinite(f["_revttm"]):
                    cb += f["_cap"]; rt += f["_revttm"]
                for k in ("毛利率", "毛利率年變化", "存貨天數", "資本支出TTM年增", "資本支出÷營收TTM"):
                    if np.isfinite(f[k]):
                        mem[k].append(f[k])
                pp = pe_pos(i, p) if p >= 0 else np.nan
                if np.isfinite(pp):
                    mem["本益比5年位置"].append(pp)
                dh = dist_hi(i, p) if p >= 0 else np.nan
                if np.isfinite(dh):
                    mem["距一年高點"].append(dh)
            o[f"營收年增(加總)@{nm}"] = sv / sl - 1 if sl > 0 else np.nan
            o[f"營收年增(成員中位)@{nm}"] = float(np.median(mem["營收年增"])) if mem["營收年增"] else np.nan
            o[f"營收可算成員@{nm}"] = nrev; o[f"營收期別(最多)@{nm}"] = pers.most_common(1)[0][0] if pers else ""
            o[f"毛利率(加總)@{nm}"] = gpa / rva if rva > 0 else np.nan
            o[f"毛利率年變化(加總,百分點)@{nm}"] = (gpa / rva - gpb / rvb) if (rva > 0 and rvb > 0) else np.nan
            o[f"存貨天數(加總)@{nm}"] = iv / cg * DAYS_Q if cg > 0 else np.nan
            o[f"資本支出TTM年增(加總)@{nm}"] = ca / ca4 - 1 if ca4 > 0 else np.nan
            o[f"資本支出÷營收TTM(加總)@{nm}"] = cb / rt if rt > 0 else np.nan
            o[f"財報可算成員@{nm}"] = nfs; o[f"財報季(最多)@{nm}"] = fq.most_common(1)[0][0] if fq else ""
            for k in ("毛利率", "毛利率年變化", "存貨天數", "資本支出TTM年增", "資本支出÷營收TTM", "本益比5年位置", "距一年高點"):
                o[f"{k}(成員中位)@{nm}"] = float(np.median(mem[k])) if mem[k] else np.nan
            o[f"本益比5年位置可算成員@{nm}"] = len(mem["本益比5年位置"])
            # 產業指數距一年高點（同一鏈）
            if p >= 0 and H_[p] >= 0:
                lo = max(0, p - 249); w = I_[lo:p + 1]; hh = H_[lo:p + 1]
                w = w[hh == H_[p]]
                o[f"指數距一年高點@{nm}"] = float(I_[p] / w.max() - 1.0)
            else:
                o[f"指數距一年高點@{nm}"] = np.nan
            o[f"0050乖離200日@{nm}"] = ma200_50(p) if p >= 0 else np.nan
        for nm, (p1, p2) in (("前12月→起點", (pts["前12月"][0], pts["起點"][0])), ("起點→高點", (pts["起點"][0], pts["高點"][0]))):
            mi = mi_of(p2)
            idxs = MEMB[mi].get(ind, np.array([], np.int64)) if mi >= 0 else np.array([], np.int64)
            vs, ws, vv = [], [], []
            for i in (idxs if p1 >= 0 else []):
                x = inst_chg(i, p1, p2)
                if np.isfinite(x):
                    w = MC[i, p2]
                    vv.append(x)
                    if np.isfinite(w) and w > 0:
                        vs.append(x * w); ws.append(w)
            o[f"外資投信持股變化(市值加權)@{nm}"] = sum(vs) / sum(ws) if ws else np.nan
            o[f"外資投信持股變化(成員中位)@{nm}"] = float(np.median(vv)) if vv else np.nan
            o[f"外資投信可算成員@{nm}"] = len(vv)
        return o

    SEGS = []; CONT = []
    for kd in ("vw", "ew"):
        for ind in INDS:
            js = HITS[kd][ind]
            if not js:
                continue
            groups = [[js[0]]]
            for j in js[1:]:
                if j - WIN_M <= groups[-1][-1]:
                    groups[-1].append(j)
                else:
                    groups.append([j])
            I_, H_ = IDX[kd][ind], CH[kd][ind]
            for g in groups:
                S = int(ME[g[0] - WIN_M]); E = int(ME[g[-1]])
                seg = I_[S:E + 1]
                if not (H_[S:E + 1] == H_[S]).all():
                    raise SystemExit(f"⛔ {ind} 段內跨鏈")
                H = S + int(np.nanargmax(seg))
                gain = I_[H] / I_[S] - 1.0
                r50 = v50(H) / v50(S) - 1.0
                hend_t = CAL[H] + pd.DateOffset(months=12)
                he = cpos_le(hend_t)
                post = np.arange(H + 1, he + 1)
                post = post[H_[post] == H_[H]] if len(post) else post
                mdd = float(I_[post].min() / I_[H] - 1.0) if len(post) else np.nan
                full = bool(hend_t <= CAL[-1] and len(post) == he - H)
                acc = contrib(kd, ind, S, H)
                tot = sum(acc.values())
                if abs(tot - gain) > 1e-6 * max(1.0, abs(gain)):
                    raise SystemExit(f"⛔ {ind} 貢獻加總 {tot} ≠ 漲幅 {gain}")
                top = sorted(acc.items(), key=lambda z: -z[1])[:5]
                segid = f"{kd}-{ind}-{CAL[S].strftime('%Y%m')}"
                rec = {"段號": segid, "加權": "市值" if kd == "vw" else "等權", "產業": ind, "起點": str(CAL[S].date()), "高點": str(CAL[H].date()),
                       "最後達標窗終點": str(CAL[E].date()), "達標窗數": len(g), "起點左截斷": bool(g[0] - WIN_M == jst), "漲幅": gain, "0050同期": r50, "對0050差": gain - r50,
                       "對0050倍數": (1 + gain) / (1 + r50), "起點到高點交易日": H - S, "高點後12月最大跌幅": mdd, "高點後12月": "滿" if full else "未滿12月",
                       "首窗3年報酬": I_[int(ME[g[0]])] / I_[S] - 1.0,
                       "前5貢獻": "｜".join(f"{SIDS[i]}{NAME.get(SIDS[i], '')} {v / gain:.0%}" for i, v in top) if gain else ""}
                d12 = CAL[S] - pd.DateOffset(months=12); p12 = cpos_le(d12)
                rec["前12月早於資料首日"] = bool(p12 < 0)
                rec.update(ind_feats(kd, ind, {"前12月": (p12, d12 if p12 < 0 else CAL[p12]), "起點": (S, CAL[S]), "高點": (H, CAL[H])}, S, H))
                SEGS.append(rec)
                for rk, (i, v) in enumerate(top):
                    CONT.append({"段號": segid, "加權": rec["加權"], "產業": ind, "起點": rec["起點"], "高點": rec["高點"], "名次": rk + 1,
                                 "代號": SIDS[i], "名稱": NAME.get(SIDS[i], ""), "貢獻(漲幅點)": v, "占漲幅": v / gain if gain else np.nan})
    SEG = pd.DataFrame(SEGS)
    log(f"[甲] 段：市值 {int((SEG['加權'] == '市值').sum()) if len(SEG) else 0}、等權 {int((SEG['加權'] == '等權').sum()) if len(SEG) else 0}｜{time.time() - t0:.0f}s")

    # ═════════ 乙：個股大漲段 ═════════
    MEc = [int(p) for p in ME if CAL[p] >= START]
    MEprev = {int(ME[k]): (int(ME[k - 1]) if k > 0 else -1) for k in range(len(ME))}
    MK_ALL = {}
    for s in SIDS:
        MK_ALL[s] = Zm["mk"].get(s) or Ze["mk"].get(s, "")
    SEGI = defaultdict(list)
    for r_ in SEGS:
        SEGI[(r_["加權"], r_["產業"])].append((cpos_le(r_["起點"]), cpos_le(r_["高點"])))

    def scan(i, mult, yrs):
        vp, vc, nb = VP[i], VC[i], NB[i]
        out = []; nxt = -1
        if len(vp) < 2:
            return out
        for me in MEc:
            if me <= nxt:
                continue
            k = int(np.searchsorted(vp, me, "right")) - 1
            if k < 0 or vp[k] <= MEprev[me] or vp[k] <= nxt:
                continue
            endt = CAL[vp[k]] + pd.DateOffset(years=yrs)
            ep_ = cpos_le(endt)
            e = int(np.searchsorted(vp, ep_, "right")) - 1
            fb = int(nb[k + 1]) if k + 1 <= len(vp) else len(vp) + 10
            cut = min(e, fb - 1)
            if cut <= k:
                continue
            w = vc[k + 1:cut + 1]
            if w.max() >= mult * vc[k]:
                hk = k + 1 + int(np.argmax(w)); ak = k + 1 + int(np.argmax(w >= mult * vc[k]))
                out.append({"me": me, "k": k, "hk": hk, "ak": ak, "mult": float(w.max() / vc[k]), "trunc_bad": bool(fb <= e),
                            "trunc_tail": bool(endt > CAL[-1]), "delist": bool(vp[-1] < ep_ and vp[-1] < CEND - 5 and fb > e)})
                nxt = int(vp[hk])
        return out

    BROWS = {}
    for tag, mult, yrs in (("x3", 3.0, 3), ("x5", 5.0, 5)):
        rows = []
        for i, s in enumerate(SIDS):
            for z in scan(i, mult, yrs):
                ps, ph, pa_ = int(VP[i][z["k"]]), int(VP[i][z["hk"]]), int(VP[i][z["ak"]])
                ds = CAL[ps]
                ind, src = PIT.at(s, ds)
                rec = {"代號": s, "名稱": NAME.get(s, ""), "市場": MK_ALL[s], "起點月底": str(CAL[z["me"]].date()),
                       "起點": str(ds.date()), "起點收盤(還原)": float(VC[i][z["k"]]), "達標日": str(CAL[pa_].date()), "高點": str(CAL[ph].date()),
                       "高點收盤(還原)": float(VC[i][z["hk"]]), "倍數": z["mult"], "起點到高點交易日": ph - ps,
                       "產業(起點PIT)": ind if ind else "無類別", "產業來源": src, "窗遇壞根截斷": z["trunc_bad"], "窗超出資料尾": z["trunc_tail"],
                       "窗內下市": z["delist"], "起點左截斷": bool(z["me"] == MEc[0])}
                for kd, lab in (("市值", "vw"), ("等權", "ew")):
                    segs = SEGI.get((kd, ind), [])
                    rec[f"與甲相交_{kd}"] = any(S0 <= ph and ps <= H0 for S0, H0 in segs)
                    rec[f"起點在甲段內_{kd}"] = any(S0 <= ps <= H0 for S0, H0 in segs)
                d12 = ds - pd.DateOffset(months=12); p12 = cpos_le(d12)
                rec["前12月早於資料首日"] = bool(p12 < 0)
                rec.update(stock_feats(i, s, {"前12月": (p12, d12 if p12 < 0 else CAL[p12]), "起點": (ps, ds), "高點": (ph, CAL[ph])}))
                rows.append(rec)
        BROWS[tag] = pd.DataFrame(rows)
        log(f"[乙 {tag}] 段 {len(rows)}｜{time.time() - t0:.0f}s")

    # ═════════ 輸出 ═════════
    def year_of(sr):
        return pd.to_datetime(sr).dt.year

    YRS = list(range(2004, CAL[-1].year + 1))   # 2004 列 ＝ 起點 2004-12-31（最早可評估點、左截斷）
    F1 = []
    for y in YRS:
        r = {"起點年": y, "註": "起點 2004-12-31（從 2005-01 起算的第一個點，左截斷）" if y == 2004 else ""}
        for kd in ("市值", "等權"):
            sub = SEG[(SEG["加權"] == kd) & (year_of(SEG["起點"]) == y)] if len(SEG) else SEG
            r[f"甲段數_{kd}"] = len(sub); r[f"甲涉及產業數_{kd}"] = int(sub["產業"].nunique()) if len(sub) else 0
            r[f"甲產業_{kd}"] = "、".join(sorted(sub["產業"].unique())) if len(sub) else ""
        F1.append(r)
    F1 = pd.DataFrame(F1)
    F2 = []
    for y in YRS:
        r = {"起點年": y, "註": "起點 2004-12-31（從 2005-01 起算的第一個點，左截斷）" if y == 2004 else ""}
        for tag in ("x3", "x5"):
            B = BROWS[tag]
            sub = B[year_of(B["起點"]) == y] if len(B) else B
            r[f"乙段數_{tag}"] = len(sub)
            r[f"乙涉及產業數_{tag}"] = int(sub["產業(起點PIT)"].nunique()) if len(sub) else 0
            for kd in ("市值", "等權"):
                r[f"乙與甲相交比例_{tag}_{kd}"] = float(sub[f"與甲相交_{kd}"].mean()) if len(sub) else np.nan
        F2.append(r)
    F2 = pd.DataFrame(F2)
    IR = []
    for tag in ("x3", "x5"):
        B = BROWS[tag]
        if not len(B):
            continue
        era = np.where(year_of(B["起點"]) <= 2014, "2005～2014", "2015～")
        for (ind, er), g in B.groupby([B["產業(起點PIT)"], era]):
            IR.append({"版": tag, "產業": ind, "起點期": er, "段數": len(g), "與甲相交比例_市值": float(g["與甲相交_市值"].mean()),
                       "與甲相交比例_等權": float(g["與甲相交_等權"].mean())})
        for ind, g in B.groupby("產業(起點PIT)"):
            IR.append({"版": tag, "產業": ind, "起點期": "全期", "段數": len(g), "與甲相交比例_市值": float(g["與甲相交_市值"].mean()),
                       "與甲相交比例_等權": float(g["與甲相交_等權"].mean())})
    IR = pd.DataFrame(IR)
    OV = []
    for tag in ("x3", "x5"):
        B = BROWS[tag]
        era = np.where(year_of(B["起點"]) <= 2014, "2005～2014", "2015～") if len(B) else np.array([])
        for er in ("全期", "2005～2014", "2015～"):
            g = B if er == "全期" else B[era == er]
            OV.append({"版": tag, "起點期": er, "段數": len(g),
                       **{f"{c}_{kd}": (float(g[f"{c}_{kd}"].mean()) if len(g) else np.nan) for c in ("與甲相交", "起點在甲段內") for kd in ("市值", "等權")},
                       "產業無類別或排除": int(g["產業(起點PIT)"].isin(EXCL_IND | {"無類別"}).sum()) if len(g) else 0,
                       "窗遇壞根截斷": int(g["窗遇壞根截斷"].sum()) if len(g) else 0, "窗內下市": int(g["窗內下市"].sum()) if len(g) else 0,
                       "窗超出資料尾": int(g["窗超出資料尾"].sum()) if len(g) else 0,
                       "倍數中位": float(g["倍數"].median()) if len(g) else np.nan, "起點到高點交易日中位": float(g["起點到高點交易日"].median()) if len(g) else np.nan})
    OV = pd.DataFrame(OV)
    FEAT = ["營收年增", "毛利率", "毛利率年變化", "存貨天數", "資本支出TTM年增", "資本支出÷營收TTM", "本益比5年位置", "距一年高點", "0050乖離200日"]
    CS = []
    for tag in ("x3", "x5"):
        B = BROWS[tag]
        if not len(B):
            continue
        era = np.where(year_of(B["起點"]) <= 2014, "2005～2014", "2015～")
        for er in ("全期", "2005～2014", "2015～"):
            g = B if er == "全期" else B[era == er]
            cols = [f"{f}@{p}" for f in FEAT for p in PTS] + ["外資投信持股變化@前12月→起點", "外資投信持股變化@起點→高點"]
            for c in cols:
                v = g[c].to_numpy(float)
                q = qd(v)
                row = {"版": tag, "起點期": er, "欄": c, "段數": len(g), "有值": q["n"], "涵蓋率": q["n"] / len(g) if len(g) else np.nan,
                       "中位": q.get("中位"), "p25": q.get("p25"), "p75": q.get("p75")}
                if c.startswith("0050乖離200日"):
                    row["在200日線上比例"] = float(np.mean(v[np.isfinite(v)] > 0)) if np.isfinite(v).any() else np.nan
                CS.append(row)
    CS = pd.DataFrame(CS)
    MISS = pd.DataFrame([
        {"欄": "月營收年增", "來源": "early/revenue（2003-01～2014-12）＋ mops/revenue_hist（2015-01～）＋ meta/revenue_delisted（72 家只補缺格）",
         "缺口": "2015～2020 下市公司月營收約 80 家補不回（revenue_delisted 只補到 72 家，部分仍缺）；新上市前無；去年當月 ≤ 0 ⇒ 缺"},
        {"欄": "毛利率／毛利率年變化", "來源": "mops/fs_hist ci（2015Q1～）、mops/fin_hist（2013Q1～）；可用日 filing_dates（t57sb01，2013～）",
         "缺口": "2012 以前無季報與上傳時戳 ⇒ 起點在 2013 年中以前的『前12月』『起點』全缺；金融保險等無毛利科目 ⇒ 缺；fs_xbrl 無 GrossProfit 欄（不用）"},
        {"欄": "存貨天數", "來源": "meta/fs_xbrl inventories（2013～）÷ 單季營業成本",
         "缺口": "2013 以前缺；fs_xbrl 無該季或無存貨科目（空白 ≠ 0）⇒ 缺；成本 ≤ 0 ⇒ 缺"},
        {"欄": "資本支出 TTM 年增／÷營收", "來源": "meta/fs_xbrl capex_ytd（2013～）",
         "缺口": "需 8 季連續 ⇒ 最早 2014Q4 季報可用後（約 2015-03）才有值；Q4 單季靠年報差分"},
        {"欄": "本益比 5 年位置", "來源": "stocks_per（主 2015-01～）、early/per＋early/otcper（2012-01～2014-12）",
         "缺口": "2012 以前無官方 per；需 1250 日窗內有值 ≥ 750 天 ⇒ 約 2015-01 起才有值；虧損（per 空）⇒ 缺"},
        {"欄": "股價距一年高點", "來源": "還原收盤（B1）", "缺口": "幾乎不缺；窗內有壞根只看斷點之後；最近 20 交易日無成交（含尚未上市）⇒ 缺；『前12月』早於 2004-02-11 ⇒ 缺"},
        {"欄": "外資＋投信持股變化", "來源": "stocks_inst（主 2015-01-05～；早年上市 2012-05～）÷ 股數",
         "缺口": "2012-05 以前全缺；上櫃 2015 以前缺；『前12月→起點』需 d1 已有涵蓋 ⇒ 上市約 2013-05 起點後、上櫃 2016 起點後；投信持股『餘額』無歷史 ⇒ 用買賣超累計代替"},
        {"欄": "0050 在 200 日線上下", "來源": "0050 還原收盤（我方資料 2004-02-11 起；⚠ 2003 年那段我方沒有）",
         "缺口": "需 200 根 ⇒ 2004-11-29 起才有值；起點在 2005 年 11 月以前的『前12月』缺；位置型欄（本益比位置、距一年高點、0050、法人）在『前12月』早於 2004-02-11 時缺"},
    ])
    # 涵蓋率附到缺欄
    for tag in ("x3",):
        B = BROWS[tag]
        if len(B):
            era = np.where(year_of(B["起點"]) <= 2014, "2005～2014", "2015～")
            for k_, f in enumerate(["營收年增", "毛利率", "存貨天數", "資本支出TTM年增", "本益比5年位置", "距一年高點", None, "0050乖離200日"]):
                if f is None:
                    c = "外資投信持股變化@前12月→起點"
                else:
                    c = f"{f}@起點"
                for er in ("2005～2014", "2015～"):
                    v = B.loc[era == er, c].to_numpy(float)
                    MISS.loc[k_, f"乙x3起點涵蓋率_{er}"] = float(np.isfinite(v).mean()) if len(v) else np.nan
    # 存檔
    F1.to_csv(os.path.join(out_dir, "freq_甲.csv"), index=False, encoding="utf-8-sig")
    F2.to_csv(os.path.join(out_dir, "freq_乙.csv"), index=False, encoding="utf-8-sig")
    SEG.to_csv(os.path.join(out_dir, "甲_段.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(CONT).to_csv(os.path.join(out_dir, "甲_貢獻前5.csv"), index=False, encoding="utf-8-sig")
    with gzip.open(os.path.join(out_dir, "甲_窗.csv.gz"), "wt", encoding="utf-8") as fh:
        pd.DataFrame(WROWS).to_csv(fh, index=False)
    # 產業指數（月底）
    IXR = []
    for p in ME:
        for ind in INDS:
            a_, b_ = IDX["vw"][ind][p], IDX["ew"][ind][p]
            if np.isfinite(a_) or np.isfinite(b_):
                IXR.append({"日": str(CAL[p].date()), "產業": ind, "I_vw": a_, "鏈_vw": int(CH["vw"][ind][p]), "I_ew": b_, "鏈_ew": int(CH["ew"][ind][p]),
                            "成員數(當月)": int(NMEM[ind][mi_of(p)]) if mi_of(p) >= 0 else None, "0050": v50(p)})
    with gzip.open(os.path.join(out_dir, "ind_index.csv.gz"), "wt", encoding="utf-8") as fh:
        pd.DataFrame(IXR).to_csv(fh, index=False)
    for tag in ("x3", "x5"):
        with gzip.open(os.path.join(out_dir, f"乙_段_{tag}.csv.gz"), "wt", encoding="utf-8") as fh:
            BROWS[tag].to_csv(fh, index=False)
    IR.to_csv(os.path.join(out_dir, "乙_產業.csv"), index=False, encoding="utf-8-sig")
    OV.to_csv(os.path.join(out_dir, "乙_重疊.csv"), index=False, encoding="utf-8-sig")
    F2.to_csv(os.path.join(out_dir, "乙_年.csv"), index=False, encoding="utf-8-sig")
    CS.to_csv(os.path.join(out_dir, "丙_乙彙總.csv"), index=False, encoding="utf-8-sig")
    MISS.to_csv(os.path.join(out_dir, "丙_缺欄.csv"), index=False, encoding="utf-8-sig")
    J = {"性質": "描述（⛔ 不判、不計 N、不當選股規則、不做之後報酬檢定）", "來信": "台股策略線 seq531 2026-10-21 12:09（sha 0f8abb6e029d3c0e）",
         "資料": {"tw-stock-data origin/main": SHA, "主世界": Zm["data"], "早年世界": Ze["data"]},
         "合併日曆": [str(CAL[0].date()), str(CAL[-1].date()), NC], "檔數": N, "乾跑limit": a.limit, "乾跑代號": SIDS if a.limit else None, "接縫": dict(seam_info),
         "0050": {"首日": str(CAL[idx50[0]].date()), "接縫M": float(M50)}, "產業數": len(INDS), "產業": INDS, "鏈數": chain_no,
         "月營收": {"revenue_delisted補格": nfill}, "甲段數": {"市值": int((SEG["加權"] == "市值").sum()) if len(SEG) else 0,
                                                     "等權": int((SEG["加權"] == "等權").sum()) if len(SEG) else 0},
         "乙段數": {t: len(BROWS[t]) for t in BROWS}, "必附": NOTES, "讀法": __doc__.split("═══ 讀法")[1],
         "時間": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M"), "耗時秒": round(time.time() - t0)}
    json.dump(J, open(os.path.join(out_dir, "bigrun.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] {time.time() - t0:.0f}s ⇒ {out_dir}")
    open(os.path.join(out_dir, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
