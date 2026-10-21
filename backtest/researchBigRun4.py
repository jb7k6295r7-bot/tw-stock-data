# -*- coding: utf-8 -*-
"""長線大漲段 補件三件（描述、不判、不計 N；任何特徵另起草登錄 seq421）——回測線計算子代理。
 A 外資持股率欄改用全期月表重產＋營業利益率欄用新 fs_xbrl（含證券業 2013～2017 補）重產（資料庫 1849）
 B「現在在谷底」產業／族群描述清單（台股 seq536）
 C ① 起漲前後事件時間月路徑＋先後順序（台股 seq537 §一）② 個股自己漲段（seq537 §二）
⛔ 不 commit、不改既有檔（resultsBigRun*／researchBigRun* 只讀）；私有資料 ⛔ 不讀；不檢定、不打分、不排名。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBigRun4 [--procs 3] [--dry]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBigRun4_check [--dry]
輸出 backtest/resultsBigRun4/：A/（新舊對照、覆蓋率、並排、各單位新欄）、B/（谷底_產業.csv、谷底_族群.csv、歷史AC段_前12月.csv）、
     C/（路徑_乙.csv、路徑_甲.csv、先後_乙.csv、先後_甲.csv、先後_逐段_*.csv.gz、自己漲_彙總.csv、自己漲_年.csv、自己漲_產業.csv、自己漲_前60.csv）、
     bigrun4.json、run.log；（repo 外）~/bgrwork/bgr4_<full|dry>.pkl（新欄面板，供對帳）

═══ 讀法（F 標；★＝執行者定；未寫 ＝ researchBigRun3 D1～D9、researchBigRun3b E1～E6 原樣）═══
 F0 資料：新快照 ＝ tw-stock-data origin/main（SHA 常數）的 meta/foreign_holding、meta/fs_xbrl、meta/filing_dates.csv、mops/news；
    月營收、產業別 ＝ 快照 dbfb96cb81a7（同前，更正期間有輕微前視）；價格 ＝ 兩世界面板（主到 2026-09-24）；月底面板 ＝ researchBigRun3 的 bgr3_panel_full.pkl。
 ── A ──
 F1 外資持股率(月表) ＝ foreign_holding foreign_pct（上市 2004-02～、上櫃 2007-05～，2026-09 止）：月底當天或之前 5 個交易日內最近一筆（D3 同式）；12 月變化 ＝ 與 12 個月底前之差（百分點）。
    營業利益率 ＝ 新 fs_xbrl operating_income_ytd ÷ revenue_ytd（單季差分、cr 優先、選季沿用原面板，E2／E3 同式）；年變化、由降轉升同 D3。
    ⚠ fs_xbrl 證券業（bd 範本）revenue_ytd 空白 ⇒ 證券業營業利益補上了，但營業利益率仍算不出（照實，⛔ 不改用別的分母）。
    新舊並列：外資欄舊 ＝ resultsBigRun3（2004～2012 月表）；營業利益率欄舊 ＝ resultsBigRun3/xbrl（前一版 fs_xbrl）。
 ── B ──
 F2 現在 ＝ 資料尾 2026-09-24（價格最後一天）。★ 財報、月營收以「該日之前已公開」取：月營收 ＝ 可用日（次月 15 日，2025-12 期以前 10 日）＜ 當日的最新 3 期；
    財報季 ＝ 新快照 filing_dates 上傳日 ＜ 當日的最新季（AI1 優先、否則最早，同前）。
    產業 ＝ 當日 PIT 類別（排除類同 B2）、20 交易日內有成交、市值 ＞ 0；族群 ＝ resultsBigRun2 族群_段（切 0.7 ＝ 群間平均殘差相關 ≥ 0.3）中 ≥ 3 段的群，
    成員 ＝ 群內出現過的代號（去重），★ 當日在市（同上條件）≥ 3 檔才列。
    指數：產業 ＝ B3 同式（每月初重設、月內買進持有；等權為主、市值並報）；族群 ＝ 同式，成員固定為上述代號（當月在市 ≥ 3 檔，不足即斷鏈）。
    欄：前 3 年報酬（指數，當日 ÷ 3 曆年前當天或之前最後一日，同一鏈）、距 5 年高點（指數 ÷ 近 1,250 交易日同鏈最高 − 1）、
      近 4 季合計營業利益率（Σ 營業利益 ÷ Σ 營收，fs_xbrl 單季）與前一年同口徑之差（百分點）、近 3 月營收年增（Σ 3 期 ÷ Σ 去年同 3 期 − 1）、
      存貨天數年變化（期末存貨 ÷ 單季營業成本 × 91.25，本季 − 去年同季）、近 4 季資本支出年增（TTM ÷ 前一 TTM − 1）。
      財報類、營收類各報「加總」（成員分子分母各自加總，近似規模加權）與「成員中位」（近似等權）兩種。
    排列 ＝ 前 3 年報酬（等權）由低到高，只為閱讀，⛔ 不打分、不排名、不挑。
    歷史 A、C 型段 ＝ 台股 seq537 §一 列的段號（A 缺貨漲價、C 谷底翻身）；同欄在「起點前 12 個月」（起點月底往前 12 個月底當天）用同一支函數算，
      指數用該段自己的版（vw／ew）；報各型中位與段數，並逐段列出。
 ── C ──
 F3 事件時間月路徑：乙 ×3 3,316 段、甲四版（各自）；相對起點 −24～＋36 個月底、相對高點（高點當天或之前最後月底）−24～＋12 個月底。
    欄（個股月底面板）：月營收年增、毛利率年變化（fs_xbrl 版）、營業利益率年變化（A 新版）、合約負債年增、存貨天數年變化（★ fs_xbrl：本季 − 去年同季，天）、
      資本支出 TTM 年增、外資持股率（A 新月表）、外資持股率 12 月變化、法人累計買賣超 ÷ 股數（★ 自該段路徑起點月 −24 起累計，外資＋投信）、融資 ÷ 股數、
      本益比 5 年位置、距一年高點、60 日周轉率、注意次數（★ 當月次數，2011 起）。甲 ＝ 該月該產業成員中位數。
    每月報 n、中位、四分位；對照 A ＝ 同一曆月其餘個股（甲：其餘產業）中位的中位；對照 B ＝ resultsBigRun3 對照 B（乙：B 乙；甲：同版 B 甲），
      以其自己的起點／「高點」（窗內最高）同法對齊。甲另依台股 seq537 類別 A～F、未標 分開報（看過原因後標的，只當描述分組）。
 F4 先後順序（每段算，再報分布）：★ 搜尋窗 ＝ [起點月 − 24, 高點月]，取窗內「第一次」出現的月 − 起點月：
      ① 營收年增由負轉正（D3 旗標成立的月）② 毛利率由降轉升（fs_xbrl 版旗標由不成立變成立的月）
      ③ 外資持股率開始連 3 月增加（該月起連 3 個月底各比前一月底高，且前一月不是增加）④ 營收創 24 月新高（當月最新已公告期 ≥ 前 24 期最高，24 期齊全）首次。
    甲 ★ 用產業序列：① 營收年增(加總) 由 ≤ 0 轉 ＞ 0；② 成員中位毛利率年變化由 ≤ 0 轉 ＞ 0；③ 成員中位外資持股率連 3 月增加開始；④ 成員中「營收 24 月新高」比例首次 ≥ 50%。
    報 早（＜ 0）／同（＝ 0）／晚（＞ 0）／窗內無 的比例與（有事件者）中位月數；乙、B 乙並列；甲按版、按類。
 F5 個股自己漲 ★：乙 ×3 中，與該股起點 PIT 產業在四版任一甲段都不相交、且族群（切 0.7 ＝ 群間平均殘差相關 ≥ 0.3）不在 ≥ 3 段的群（＝ 段數 ≤ 2）。
    報總段數、每年、產業分布；清單 ＝ 起點 2013 起、倍數前 60 段：代號、名稱、起點、高點、倍數、產業、起點市值、上市年資（左截斷記缺）、
    起點前 12 月／後 12 月的月營收年增與毛利率年變化、起點→高點現增可轉債決議次數、起點→高點重大訊息則數（mops/news；⚠ 該表只有主旨、無類別欄 ⇒「類別前 3 名」記無）、
    高點後 12 月最大跌幅。
 F6 必附：描述，不是選股規則｜事後圈的段｜2015～2020 下市月營收約 80 家補不回｜上櫃 2007-07 前無價｜月營收為最新版、更正期間有輕微前視；
    族群是事後分群、只當描述、⛔ 不當母體；類別 A～F 是看過原因後標的、只當描述分組；景氣燈號修正後值。
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
from backtest import researchIndRev_prereg as PRE           # noqa: E402
from backtest import research11 as R                        # noqa: E402
from backtest import researchLongPool as LP                 # noqa: E402
import backtest.data as D                                   # noqa: E402

SHA = "c1db66ce973025613512c3a318411db17e842f2a"
WORK = os.path.expanduser("~/bgrwork")
DATA_A = os.path.join(WORK, "main_dbfb96cb81a7", "data")
OUT = "backtest/resultsBigRun4"
S3, S3X, S2, S1 = "backtest/resultsBigRun3", "backtest/resultsBigRun3/xbrl", "backtest/resultsBigRun2", "backtest/resultsBigRun"
EXCL_IND = {"其他", "綜合", "存託憑證", "ETF", ""}
ALIVE = 20
DAYS_Q = 91.25
QK0 = LP.qkey(2012, 1)
PTS = ("前12月", "起點", "高點前6月", "高點", "高點後6月")
TYPES = {
    "A 缺貨漲價": "vw-塑膠工業-200412 vw-玻璃陶瓷-201911 vw-航運業-201805 vw-造紙工業-202007 vw-鋼鐵工業-200504 vw-電器電纜-201904 vw-電子通路業-202009 ew-玻璃陶瓷-202002 ew-航運業-200502 ew-航運業-201805 ew-造紙工業-200505 ew-鋼鐵工業-200505 ew-鋼鐵工業-202001 ew-電器電纜-202002 ew-電子通路業-202002 補vw-玻璃陶瓷-202302 補ew-電子零組件業-202304",
    "B 新需求": "vw-其他電子業-202106 vw-半導體業-201112 vw-半導體業-201707 vw-橡膠工業-200412 vw-資訊服務業-202106 vw-電腦及週邊設備業-202007 vw-食品工業-200412 ew-其他電子業-202108 ew-半導體業-201507 ew-橡膠工業-200502 ew-資訊服務業-202004 ew-通信網路業-202106 ew-電腦及週邊設備業-202003 ew-食品工業-200502 補vw-其他電子業-202208 補vw-半導體業-202206 補vw-通信網路業-202304 補vw-電子零組件業-202208 補vw-電腦及週邊設備業-202103 補ew-半導體業-202304 補ew-電腦及週邊設備業-202111 補vw-食品工業-201005",
    "C 谷底翻身": "vw-化學工業-200810 vw-塑膠工業-200807 vw-水泥工業-200810 vw-汽車工業-200807 vw-油電燃氣業-201509 vw-紡織纖維-200810 vw-貿易百貨-200806 vw-電子通路業-200810 vw-電機機械-200810 ew-光電業-202003 ew-化學工業-200801 ew-汽車工業-200806 ew-貿易百貨-200810 ew-電子通路業-200809 ew-電機機械-200810 補vw-光電業-202308",
    "D 政策": "vw-建材營造-200502 vw-建材營造-202105 vw-觀光事業-200502 vw-貿易百貨-200502 ew-建材營造-200502 ew-建材營造-202105 ew-觀光事業-200502 ew-觀光事業-202002 ew-貿易百貨-200505 ew-電機機械-202108",
    "E 資金與資產": "vw-建材營造-200809 vw-水泥工業-200412 vw-紡織纖維-200502 ew-水泥工業-200502 補vw-金融保險-202306",
    "F 個別公司": "vw-文化創意業-202103 vw-電器電纜-201505 補vw-電子通路業-202104"}
SEG2TYPE = {sid: t for t, s in TYPES.items() for sid in s.split()}
NOTES = ["描述，不是選股規則", "事後圈的段", "2015～2020 下市月營收約 80 家補不回", "上櫃 2007-07 前無價", "月營收為最新版、更正期間有輕微前視",
         "族群是事後分群，只當描述，⛔ 不當回測母體", "甲類別 A～F 是台股線看過原因後標的，只當描述分組", "景氣燈號為修正後資料、非當時公布值",
         "任何特徵若要用，一律另起草登錄、用沒看過的期間或前瞻驗（seq421）"]
LOG: list = []
_G: dict = {}


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def ensure_arch():
    root = os.path.join(WORK, f"mainD_{SHA[:12]}")
    if not os.path.isfile(os.path.join(root, ".done")):
        subprocess.run(["git", "cat-file", "-e", SHA], check=True)
        os.makedirs(root, exist_ok=True)
        p = subprocess.run(["git", "archive", "--format=tar", SHA, "data/meta/foreign_holding", "data/meta/fs_xbrl", "data/meta/filing_dates.csv",
                            "data/mops/news"], capture_output=True, check=True)
        subprocess.run(["tar", "-x", "-C", root], input=p.stdout, check=True)
        open(os.path.join(root, ".done"), "w").write(SHA)
    return os.path.join(root, "data")


def qstat(v, flag=False):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    if not len(v):
        return {"n": 0, "中位": np.nan, "p25": np.nan, "p75": np.nan}
    if flag:
        return {"n": int(len(v)), "中位": float(v.mean()), "p25": np.nan, "p75": np.nan}
    return {"n": int(len(v)), "中位": float(np.median(v)), "p25": float(np.percentile(v, 25)), "p75": float(np.percentile(v, 75))}


def single(a, j):
    if j < 0 or j >= len(a) or not np.isfinite(a[j]):
        return np.nan
    if (QK0 + j) % 4 == 0:
        return a[j]
    return a[j] - a[j - 1] if j >= 1 and np.isfinite(a[j - 1]) else np.nan


def seam_job(sid):
    pe, pm = _G["SEAM"][sid]; out = {"sid": sid}
    for key, data, cal, p in (("rc_e", _G["ED"], _G["ECAL"], pe), ("rc_m", _G["MD"], _G["MCAL"], pm - _G["NE"])):
        x = pd.read_csv(os.path.join(data, "stocks", f"{sid}.csv"), dtype={"date": str}, usecols=["date", "close"]).drop_duplicates("date", keep="last")
        v = pd.to_numeric(x.loc[x["date"] == str(cal[p].date()), "close"], errors="coerce")
        out[key] = float(v.iloc[0]) if len(v) else np.nan
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); ap.add_argument("--dry", action="store_true"); a = ap.parse_args()
    t0 = time.time(); tag = "dry" if a.dry else "full"
    src3 = os.path.join(WORK, "dry3") if a.dry else S3
    out = os.path.join(WORK, "dry4") if a.dry else OUT
    for sub in ("A", "B", "C"):
        os.makedirs(os.path.join(out, sub), exist_ok=True)
    DN = ensure_arch()
    log(f"[資料] 新快照 origin/main {SHA[:12]}（外資持股月表、fs_xbrl、filing_dates、news）｜月營收、產業別 dbfb96cb81a7｜面板 bgr3_panel_{tag}")
    PN = pickle.load(open(os.path.join(WORK, f"bgr3_panel_{tag}.pkl"), "rb"))
    NP3 = pickle.load(open(os.path.join(WORK, f"bgr3b_np_{tag}.pkl"), "rb"))["NP"]
    SIDS = PN["SIDS"]; MEp = PN["MEp"]; K = len(MEp); N = len(SIDS); P = PN["P"]; CU = PN["CU"]; META = PN["META"]; INDM = PN["INDM"]; SHK = PN["SHK"]
    IX = {s: i for i, s in enumerate(SIDS)}; ids = set(SIDS)
    Ze = IMF.build_panel("早年", 2, log); Zm = IMF.build_panel("主", 2, log)
    CAL = Ze["cal"].append(Zm["cal"]); NE = Ze["n0"]; NC = len(CAL); CEND = NC - 1
    cpos_le = lambda ts: int(CAL.searchsorted(pd.Timestamp(ts), side="right")) - 1
    MEy = np.array([CAL[int(p)].year for p in MEp])
    # ═════════ 價格（B 指數用）═════════
    ie = {s: k for k, s in enumerate(Ze["sids"])}; im = {s: k for k, s in enumerate(Zm["sids"])}
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
    _G.update({"SEAM": SEAM, "ED": Ze["data"], "MD": Zm["data"], "ECAL": Ze["cal"], "MCAL": Zm["cal"], "NE": NE})
    with Pool(a.procs) as pool:
        SR = {r["sid"]: r for r in pool.imap_unordered(seam_job, sorted(SEAM), chunksize=16)}
    for s, (pe, pm) in SEAM.items():
        i = IX[s]; re_, rm_ = SR[s]["rc_e"], SR[s]["rc_m"]
        Mf = C[i, pe] * rm_ / (re_ * C[i, pm]) if (np.isfinite(re_) and np.isfinite(rm_) and re_ > 0 and C[i, pm] > 0) else np.nan
        if np.isfinite(Mf) and Mf > 0:
            C[i, NE:] *= Mf; BAD[i, pm] = (pm - pe - 1) >= 5
        else:
            BAD[i, pm] = True
    RR = np.zeros((N, NC)); LASTV = np.full((N, NC), -1, np.int32)
    for i in range(N):
        vp = np.flatnonzero(np.isfinite(C[i]))
        if len(vp) > 1:
            vc = C[i, vp]; r = vc[1:] / vc[:-1] - 1.0; r[BAD[i, vp[1:]]] = 0.0; RR[i, vp[1:]] = r
        ar = np.full(NC, -1, np.int32); ar[vp] = vp; LASTV[i] = np.maximum.accumulate(ar)
    ym = CAL.year * 12 + CAL.month
    mstart = np.flatnonzero(np.r_[True, ym[1:] != ym[:-1]]); mend = np.r_[mstart[1:] - 1, NC - 1]
    MONTHS = [(int(mstart[k] - 1), int(mend[k])) for k in range(1, len(mstart))]
    rev, rev_ly, cat, _, _, _ = PRE.load_rev(DATA_A)
    PIT = PRE.PIT(DATA_A, cat)
    log(f"[價格] {N} 檔｜{time.time() - t0:.0f}s")

    def alive_at(p):
        lv = LASTV[:, p]
        return (lv >= 0) & (p - lv <= ALIVE) & np.isfinite(MC[:, p]) & (MC[:, p] > 0)

    def build_index(member_fn, minm):
        """member_fn(b) ⇒ 成員 idx 陣列；回 {vw, ew: (I, CH)}。"""
        res = {kd: (np.full(NC, np.nan), np.full(NC, -1, np.int64)) for kd in ("vw", "ew")}; ch = 0
        for (b, e) in MONTHS:
            idxs = member_fn(b)
            if len(idxs) < minm:
                continue
            Gm = np.cumprod(1.0 + RR[idxs, b + 1:e + 1], axis=1)
            for kd in ("vw", "ew"):
                I_, H_ = res[kd]
                W0 = MC[idxs, b] if kd == "vw" else np.ones(len(idxs))
                if not np.isfinite(I_[b]):
                    ch += 1; I_[b] = 1.0; H_[b] = ch
                I_[b + 1:e + 1] = I_[b] * (W0[:, None] * Gm).sum(0) / W0.sum(); H_[b + 1:e + 1] = H_[b]
        return res
    MEMB = []
    for (b, e) in MONTHS:
        mm = defaultdict(list)
        for i in np.flatnonzero(alive_at(b)):
            ind, _ = PIT.at(SIDS[i], CAL[b])
            if ind is not None and ind not in EXCL_IND:
                mm[ind].append(i)
        MEMB.append({k: np.array(v, np.int64) for k, v in mm.items()})
    MB = {b: mi for mi, (b, e) in enumerate(MONTHS)}
    INDS = sorted({k for m in MEMB for k in m})
    IDXI = {ind: build_index(lambda b, ind=ind: MEMB[MB[b]].get(ind, np.array([], np.int64)), 5) for ind in INDS}
    log(f"[產業指數] {len(INDS)}｜{time.time() - t0:.0f}s")

    # ═════════ 新快照：外資持股、fs_xbrl ═════════
    FHd = np.full((N, NC), np.nan, np.float32)
    for f in sorted(glob.glob(os.path.join(DN, "meta", "foreign_holding", "foreign_holding_*.csv"))):
        x = pd.read_csv(f, dtype={"stock_id": str, "date": str}, usecols=["date", "stock_id", "foreign_pct"])
        x = x[x["stock_id"].isin(ids)]
        pi = CAL.get_indexer(pd.to_datetime(x["date"])); okp = pi >= 0
        FHd[np.array([IX[s] for s in x["stock_id"]], dtype=np.int64)[okp], pi[okp]] = pd.to_numeric(x["foreign_pct"], errors="coerce").to_numpy(float)[okp]
    FHn = np.full((N, K), np.nan, np.float32)
    for k, p in enumerate(MEp):
        w = FHd[:, max(0, int(p) - 5):int(p) + 1]
        last = np.full(N, np.nan, np.float32)
        for c in range(w.shape[1]):
            m_ = np.isfinite(w[:, c]); last[m_] = w[m_, c]
        FHn[:, k] = np.where(np.isfinite(P["市值(億)"][:, k]), last, np.nan)
    FHc = np.full((N, K), np.nan, np.float32); FHc[:, 12:] = FHn[:, 12:] - FHn[:, :-12]
    L = []
    for f in sorted(glob.glob(os.path.join(DN, "meta", "fs_xbrl", "fs_xbrl_*.csv"))):
        x = pd.read_csv(f, dtype={"stock_id": str}, usecols=["period", "stock_id", "report", "inventories", "revenue_ytd", "cost_of_sales_ytd",
                                                             "gross_profit_ytd", "operating_income_ytd", "capex_ytd"])
        x = x[x["stock_id"].isin(ids)].copy(); x["_r"] = (x["report"] != "cr").astype(int)
        x = x.sort_values(["stock_id", "period", "_r"]).drop_duplicates(["stock_id", "period"], keep="first")
        x["qk"] = [LP.qkey(p_[:4], p_[-1]) for p_ in x["period"]]; L.append(x)
    X = pd.concat(L)
    XC_ = ["inventories", "revenue_ytd", "cost_of_sales_ytd", "gross_profit_ytd", "operating_income_ytd", "capex_ytd"]
    for c in XC_:
        X[c] = pd.to_numeric(X[c], errors="coerce")
    nQ = LP.qkey(2026, 4) - QK0 + 1
    QA = {}
    for s, g in X.groupby("stock_id"):
        d = {c: np.full(nQ, np.nan) for c in XC_}
        jj = g["qk"].to_numpy(int) - QK0; ok = (jj >= 0) & (jj < nQ)
        for c in XC_:
            d[c][jj[ok]] = g[c].to_numpy(float)[ok]
        q = {"rev": np.array([single(d["revenue_ytd"], j) for j in range(nQ)]), "oi": np.array([single(d["operating_income_ytd"], j) for j in range(nQ)]),
             "cogs": np.array([single(d["cost_of_sales_ytd"], j) for j in range(nQ)]), "inv": d["inventories"],
             "cap": -np.array([single(d["capex_ytd"], j) for j in range(nQ)])}
        with np.errstate(invalid="ignore", divide="ignore"):
            q["om"] = np.where(q["rev"] > 0, q["oi"] / q["rev"], np.nan)
            q["ivd"] = np.where(q["cogs"] > 0, q["inv"] / q["cogs"] * DAYS_Q, np.nan)
        QA[s] = q
    at_ = lambda arr, j: arr[j] if 0 <= j < len(arr) else np.nan
    OPM = {k_: np.full((N, K), np.nan, np.float32) for k_ in ("營業利益率", "營業利益率年變化", "營業利益率由降轉升")}
    IVDC = np.full((N, K), np.nan, np.float32)
    for i, s in enumerate(SIDS):
        q = QA.get(s)
        if q is None:
            continue
        for k in np.flatnonzero(META["fs_qk"][i] >= 0):
            j = int(META["fs_qk"][i, k]) - QK0
            v0, v4, v1, v5 = at_(q["om"], j), at_(q["om"], j - 4), at_(q["om"], j - 1), at_(q["om"], j - 5)
            OPM["營業利益率"][i, k] = v0; OPM["營業利益率年變化"][i, k] = v0 - v4
            if np.isfinite(v0 - v4) and np.isfinite(v1 - v5):
                OPM["營業利益率由降轉升"][i, k] = float(v0 - v4 > 0 and v1 - v5 <= 0)
            IVDC[i, k] = at_(q["ivd"], j) - at_(q["ivd"], j - 4)
    log(f"[新欄] 外資持股率 {int(np.isfinite(FHn).sum())} 格、營業利益率 {int(np.isfinite(OPM['營業利益率']).sum())} 格｜{time.time() - t0:.0f}s")

    # ═════════ A：新舊並列 ═════════
    NEWA = {"外資持股率(月表)": FHn, "外資持股率12月變化": FHc, **OPM}
    OLDA = {"外資持股率(月表)": P["外資持股率(月表)"], "外資持股率12月變化": P["外資持股率12月變化"], **{k_: NP3[k_] for k_ in OPM}}
    FLAGS = {"營業利益率由降轉升"}
    YI = pd.read_csv(os.path.join(src3, "乙_全表.csv.gz"), dtype={"代號": str}); BI = pd.read_csv(os.path.join(src3, "對照B_乙.csv"), dtype={"代號": str})
    JA = pd.read_csv(os.path.join(src3, "甲_全表.csv")); JB = pd.read_csv(os.path.join(src3, "對照B_甲.csv")); JC = pd.read_csv(os.path.join(src3, "對照C.csv"))

    def ind_med(arr, ind, k, flag=False):
        if not (0 <= k < K):
            return np.nan
        mem = np.flatnonzero(INDM[:, k] == ind)
        v = arr[mem, k].astype(float); v = v[np.isfinite(v)]
        return (float(v.mean()) if flag else float(np.median(v))) if len(v) else np.nan

    def unit_vals(df, arrs, kind):
        o = {}
        for f, arr in arrs.items():
            for pt in PTS:
                ks = df[f"_k{pt}"].to_numpy(int)
                if kind == "stock":
                    ii = df["_i"].to_numpy(int); ok = (ks >= 0) & (ks < K); v = np.full(len(df), np.nan); v[ok] = arr[ii[ok], ks[ok]]
                else:
                    v = np.array([ind_med(arr, ind, int(k), f in FLAGS) for ind, k in zip(df["_ind"], ks)])
                o[f"{f}@{pt}"] = v
        return pd.DataFrame(o, index=df.index)
    UN = {}
    for nm, df, kind in (("乙", YI, "stock"), ("B乙", BI, "stock"), ("甲", JA, "ind"), ("B甲", JB, "ind"), ("C", JC, "ind")):
        base = df[[c for c in ("代號", "名稱", "版", "段號", "產業", "起點", "對照D", "_i", "_ind") if c in df.columns] + [f"_k{p}" for p in PTS]]
        UN[nm] = pd.concat([base, unit_vals(df, OLDA, kind).add_suffix("(舊)"), unit_vals(df, NEWA, kind).add_suffix("(新)")], axis=1)
    CMP = []
    for nm, d in UN.items():
        parts = [("全部", d)] if "版" not in d else [(v, d[d["版"] == v]) for v in d["版"].unique()]
        for pn, dd in parts:
            for f in NEWA:
                for pt in PTS:
                    o = dd[f"{f}@{pt}(舊)"].to_numpy(float); n = dd[f"{f}@{pt}(新)"].to_numpy(float); both = np.isfinite(o) & np.isfinite(n); dif = n[both] - o[both]
                    r = {"單位": nm, "分組": pn, "欄": f, "時點": pt, "列數": len(dd), "舊有值": int(np.isfinite(o).sum()), "新有值": int(np.isfinite(n).sum()),
                         "兩版都有": int(both.sum()), "只舊有": int((np.isfinite(o) & ~np.isfinite(n)).sum()), "只新有": int((~np.isfinite(o) & np.isfinite(n)).sum()),
                         "舊中位": qstat(o, f in FLAGS)["中位"], "新中位": qstat(n, f in FLAGS)["中位"]}
                    if f in FLAGS:
                        r["兩版都有_一致比例"] = float((o[both] == n[both]).mean()) if both.any() else np.nan
                    else:
                        r["|差|中位"] = float(np.median(np.abs(dif))) if len(dif) else np.nan
                        r["|差|≤容忍比例"] = float((np.abs(dif) <= (0.05 if f.startswith("外資") else 0.005)).mean()) if len(dif) else np.nan
                    CMP.append(r)
    CMP = pd.DataFrame(CMP)
    alive = np.isfinite(P["市值(億)"])
    COV = []
    for y in sorted(set(MEy)):
        ks = np.flatnonzero(MEy == y); al = alive[:, ks]
        r = {"年": int(y), "有成交格": int(al.sum())}
        for f in NEWA:
            r[f"{f}_舊有值率"] = float(np.isfinite(OLDA[f][:, ks])[al].mean()); r[f"{f}_新有值率"] = float(np.isfinite(NEWA[f][:, ks])[al].mean())
        COV.append(r)
    COV = pd.DataFrame(COV)
    # 並排（新欄；乙／B／D崩／乙非D ＋ A；甲／B／C ＋ A）
    XC = {}

    def cross(arr_name, k):
        if (arr_name, k) not in XC:
            v = NEWA[arr_name][:, k].astype(float); XC[(arr_name, k)] = np.sort(v[np.isfinite(v)])
        return XC[(arr_name, k)]

    def prc(x, arr):
        if not np.isfinite(x) or not len(arr):
            return np.nan
        lo = np.searchsorted(arr, x, "left"); hi = np.searchsorted(arr, x, "right")
        return float((lo + 0.5 * (hi - lo)) / len(arr))
    yr = lambda df: pd.to_datetime(df["起點"]).dt.year
    SIDE = []
    for er, (y0, y1) in {"全期": (2004, 2100), "2005～2014": (2004, 2014), "2015～": (2015, 2100)}.items():
        g1 = UN["乙"][(yr(UN["乙"]) >= y0) & (yr(UN["乙"]) <= y1)]; gb = UN["B乙"][(yr(UN["B乙"]) >= y0) & (yr(UN["B乙"]) <= y1)]
        for f in NEWA:
            for pt in PTS:
                col = f"{f}@{pt}(新)"; row = {"起點期": er, "欄": f, "時點": pt}
                for gn, df in (("乙", g1), ("B", gb), ("D崩", g1[g1["對照D"] == "崩"]), ("乙非D", g1[g1["對照D"] == "未崩"])):
                    st = qstat(df[col], f in FLAGS); row.update({f"{gn}_n": st["n"], f"{gn}_中位": st["中位"], f"{gn}_p25": st["p25"], f"{gn}_p75": st["p75"]})
                med = []; pr = []
                for k, x in zip(g1[f"_k{pt}"].to_numpy(int), g1[col].to_numpy(float)):
                    if 0 <= k < K:
                        arr = cross(f, int(k))
                        if len(arr):
                            med.append(float(arr.mean()) if f in FLAGS else float(np.median(arr)))
                            if f not in FLAGS:
                                pr.append(prc(x, arr))
                row["A_同月他股中位"] = float(np.median(med)) if med else np.nan
                row["乙在同月百分位中位"] = float(np.nanmedian(pr)) if pr and np.isfinite(pr).any() else np.nan
                SIDE.append(row)
    SIDE = pd.DataFrame(SIDE)
    INDS_P = sorted({x for x in np.unique(INDM) if x})
    IPC = {}

    def ipv(f, ind, k):
        key = (f, ind, k)
        if key not in IPC:
            IPC[key] = ind_med(NEWA[f], ind, k, f in FLAGS)
        return IPC[key]
    SIDEJ = []
    for vn in ("原版市值", "原版等權", "補充市值", "補充等權"):
        GA, GB, GC = (UN[x][UN[x]["版"] == vn] for x in ("甲", "B甲", "C"))
        for f in NEWA:
            for pt in PTS:
                col = f"{f}@{pt}(新)"; row = {"版": vn, "欄": f, "時點": pt}
                for gn, df in (("甲", GA), ("B", GB), ("C", GC)):
                    st = qstat(df[col], f in FLAGS); row.update({f"{gn}_n": st["n"], f"{gn}_中位": st["中位"], f"{gn}_p25": st["p25"], f"{gn}_p75": st["p75"]})
                med = []; pr = []
                for ind, k, x in zip(GA["_ind"], GA[f"_k{pt}"].to_numpy(int), GA[col].to_numpy(float)):
                    if 0 <= k < K:
                        arr = np.sort(np.array([ipv(f, o_, int(k)) for o_ in INDS_P if o_ != ind], float)); arr = arr[np.isfinite(arr)]
                        if len(arr):
                            med.append(float(arr.mean()) if f in FLAGS else float(np.median(arr)))
                            if f not in FLAGS:
                                pr.append(prc(x, arr))
                row["A_同月他產業中位"] = float(np.median(med)) if med else np.nan
                row["甲在同月百分位中位"] = float(np.nanmedian(pr)) if pr and np.isfinite(pr).any() else np.nan
                SIDEJ.append(row)
    SIDEJ = pd.DataFrame(SIDEJ)
    w = lambda df, sub, nm: df.to_csv(os.path.join(out, sub, nm), index=False, encoding="utf-8-sig")
    w(CMP, "A", "新舊對照.csv"); w(COV, "A", "覆蓋率_年.csv"); w(SIDE, "A", "並排_乙.csv"); w(SIDEJ, "A", "並排_甲.csv")
    for nm, d in UN.items():
        with gzip.open(os.path.join(out, "A", f"{nm}_新舊欄.csv.gz"), "wt", encoding="utf-8") as fh:
            d.to_csv(fh, index=False)
    log(f"[A] 完｜{time.time() - t0:.0f}s")

    # ═════════ 月營收面板（24 月新高、近 3 月）＝ 快照 A（同前，含 revenue_delisted 補格）═════════
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
    if PERIODS != list(PN["PERIODS"]):
        raise SystemExit("⛔ 月營收期別與面板不同")
    REVA = {s: rev[s].to_numpy(float) for s in rev.columns if s in ids}; LYA = {s: rev_ly[s].to_numpy(float) for s in rev.columns if s in ids}
    HI24 = np.zeros((N, K), bool)
    for i, s in enumerate(SIDS):
        rv = REVA.get(s)
        if rv is None:
            continue
        for k in np.flatnonzero(META["rev_per"][i] >= 0):
            rp = int(META["rev_per"][i, k])
            if rp >= 24 and np.isfinite(rv[rp]):
                h = rv[rp - 24:rp]
                HI24[i, k] = bool(np.isfinite(h).all() and rv[rp] >= h.max())

    # ═════════ C①：路徑 ═════════
    natt = np.full((N, K), np.nan); natt[:, 1:] = CU["注意次數"][:, 1:] - CU["注意次數"][:, :-1]
    PF = {"月營收年增": P["月營收年增"], "毛利率年變化(xbrl)": NP3["毛利率年變化"], "營業利益率年變化(xbrl新)": OPM["營業利益率年變化"],
          "合約負債年增": P["合約負債年增"], "存貨天數年變化(天)": IVDC, "資本支出TTM年增": P["資本支出TTM年增"],
          "外資持股率(新月表)": FHn, "外資持股率12月變化": FHc, "融資餘額÷股數": P["融資餘額÷股數"], "本益比5年位置": P["本益比5年位置"],
          "距一年高點": P["距一年高點"], "60日周轉率": P["60日周轉率"], "注意次數(當月)": natt}
    CUMF = "法人累計買賣超÷股數(自路徑起點)"
    OFFS = {"起點": range(-24, 37), "高點": range(-24, 13)}
    CM = {f: np.array([np.nanmedian(arr[:, k]) if np.isfinite(arr[:, k]).any() else np.nan for k in range(K)]) for f, arr in PF.items()}
    IPF = {f: {ind: np.full(K, np.nan) for ind in INDS_P} for f in PF}
    for k in range(K):
        byind = defaultdict(list)
        for i in np.flatnonzero(INDM[:, k] != ""):
            byind[INDM[i, k]].append(i)
        for ind, mem in byind.items():
            for f, arr in PF.items():
                v = arr[mem, k]; v = v[np.isfinite(v)]
                if len(v):
                    IPF[f][ind][k] = float(np.median(v))
    ICM = {f: np.array([np.nanmedian([IPF[f][ind][k] for ind in INDS_P]) if np.isfinite([IPF[f][ind][k] for ind in INDS_P]).any() else np.nan
                        for k in range(K)]) for f in PF}
    inst = CU["外資投信買賣超÷股數"]

    def cum_stock(i, k0, k):
        if not (0 <= k0 < K and 0 <= k < K) or k < k0:
            return np.nan
        a_, b_ = inst[i, k0], inst[i, k]; sh = SHK[i, k]
        return (b_ - a_) / sh if np.isfinite(a_) and np.isfinite(b_) and np.isfinite(sh) and sh > 0 else np.nan

    def path_rows(units, kind, label, ctrlB=None):
        rows = []
        for al, offs in OFFS.items():
            kcol = "_k起點" if al == "起點" else "_k高點"
            for off in offs:
                for f in list(PF) + [CUMF]:
                    r = {"單位": label, "對齊": al, "月": off, "欄": f}
                    for gn, df in (("段", units),) + ((("B", ctrlB),) if ctrlB is not None else ()):
                        k0 = df[kcol].to_numpy(int); kk = k0 + off; ok = (kk >= 0) & (kk < K)
                        if kind == "stock":
                            ii = df["_i"].to_numpy(int)
                            if f == CUMF:
                                v = np.array([cum_stock(i, kb - 24, k) for i, kb, k in zip(ii, k0, kk)])
                            else:
                                v = np.full(len(df), np.nan); v[ok] = PF[f][ii[ok], kk[ok]]
                        else:
                            if f == CUMF:
                                v = []
                                for ind, kb, k in zip(df["_ind"], k0, kk):
                                    if 0 <= kb - 24 and k < K:
                                        mem = np.flatnonzero(INDM[:, k] == ind)
                                        x = np.array([cum_stock(i, kb - 24, k) for i in mem]); x = x[np.isfinite(x)]
                                        v.append(float(np.median(x)) if len(x) else np.nan)
                                    else:
                                        v.append(np.nan)
                                v = np.array(v)
                            else:
                                v = np.array([IPF[f][ind][k] if (0 <= k < K and ind in IPF[f]) else np.nan for ind, k in zip(df["_ind"], kk)])
                        st = qstat(v); r.update({f"{gn}_n": st["n"], f"{gn}_中位": st["中位"], f"{gn}_p25": st["p25"], f"{gn}_p75": st["p75"]})
                    if f != CUMF:
                        k0 = units[kcol].to_numpy(int) + off; k0 = k0[(k0 >= 0) & (k0 < K)]
                        ref = CM[f] if kind == "stock" else ICM[f]
                        r["A_同月他者中位"] = float(np.nanmedian(ref[k0])) if len(k0) and np.isfinite(ref[k0]).any() else np.nan
                    rows.append(r)
        return rows
    PATHY = pd.DataFrame(path_rows(YI, "stock", "乙×3", BI))
    JA["類"] = [SEG2TYPE.get(s, "未標") for s in JA["段號"]]
    unk = sorted(set(SEG2TYPE) - set(JA["段號"]))
    if unk and not a.dry:
        raise SystemExit(f"⛔ seq537 段號在甲表找不到：{unk}")
    PJ = []
    for vn in ("原版市值", "原版等權", "補充市值", "補充等權"):
        PJ += path_rows(JA[JA["版"] == vn], "ind", f"甲{vn}", JB[JB["版"] == vn])
    for t in list(TYPES) + ["未標"]:
        sub = JA[JA["類"] == t]
        if len(sub):
            PJ += path_rows(sub, "ind", f"甲類 {t}（四版合併）")
    PATHJ = pd.DataFrame(PJ)
    log(f"[C① 路徑] 乙 {len(PATHY)} 列、甲 {len(PATHJ)} 列｜{time.time() - t0:.0f}s")

    # ═════════ C①：先後 ═════════
    GMF = NP3["毛利率由降轉升"]; RVF = P["月營收年增由負轉正"]

    def first_in(mask_row, k_lo, k_hi):
        k_lo = max(k_lo, 0); k_hi = min(k_hi, K - 1)
        if k_hi < k_lo:
            return None
        w = np.flatnonzero(mask_row[k_lo:k_hi + 1])
        return int(w[0]) + k_lo if len(w) else None

    def nearest_in(mask_row, k_lo, k_hi, ks):
        k_lo = max(k_lo, 0); k_hi = min(k_hi, K - 1)
        if k_hi < k_lo:
            return None
        w = np.flatnonzero(mask_row[k_lo:k_hi + 1]) + k_lo
        if not len(w):
            return None
        return int(w[np.lexsort((w, np.abs(w - ks)))[0]])          # 距起點最近，同距取較早

    def onset(arr_row):
        x = arr_row == 1
        prev = np.r_[False, x[:-1]]
        return x & ~prev

    def fh_run(row):
        inc = np.r_[False, row[1:] > row[:-1]]
        inc &= np.isfinite(row) & np.isfinite(np.r_[np.nan, row[:-1]])
        st = np.zeros(len(row), bool)
        for k in range(1, len(row) - 2):
            st[k] = inc[k] and inc[k + 1] and inc[k + 2] and not inc[k - 1]
        return st
    EVN = ["營收年增由負轉正", "毛利率由降轉升", "外資持股率開始連3月增加", "營收創24月新高首次"]
    STK_EV = {}

    def stock_events(i):
        if i not in STK_EV:
            STK_EV[i] = {EVN[0]: RVF[i] == 1, EVN[1]: onset(GMF[i]), EVN[2]: fh_run(FHn[i].astype(float)), EVN[3]: HI24[i]}
        return STK_EV[i]
    IREV = {ind: np.full(K, np.nan) for ind in INDS_P}
    for k in range(K):
        byind = defaultdict(list)
        for i in np.flatnonzero(INDM[:, k] != ""):
            byind[INDM[i, k]].append(i)
        for ind, mem in byind.items():
            sv = sl = 0.0
            for i in mem:
                rp = META["rev_per"][i, k]; s = SIDS[i]
                if rp >= 0 and s in REVA and np.isfinite(REVA[s][rp]) and np.isfinite(LYA[s][rp]) and LYA[s][rp] > 0:
                    sv += REVA[s][rp]; sl += LYA[s][rp]
            IREV[ind][k] = sv / sl - 1 if sl > 0 else np.nan
    IHI = {ind: np.full(K, np.nan) for ind in INDS_P}
    for k in range(K):
        for ind in INDS_P:
            mem = np.flatnonzero(INDM[:, k] == ind)
            if len(mem):
                IHI[ind][k] = HI24[mem, k].mean()
    IND_EV = {}

    def ind_events(ind):
        if ind not in IND_EV:
            nan_ = np.full(K, np.nan)
            rv = IREV.get(ind, nan_); gm = IPF["毛利率年變化(xbrl)"].get(ind, nan_); fh = IPF["外資持股率(新月表)"].get(ind, nan_)
            IHI.setdefault(ind, nan_)
            pos_onset = lambda x: np.r_[False, (x[1:] > 0) & (x[:-1] <= 0)]
            IND_EV[ind] = {EVN[0]: pos_onset(rv), EVN[1]: pos_onset(gm), EVN[2]: fh_run(fh), EVN[3]: np.nan_to_num(IHI[ind]) >= 0.5}
        return IND_EV[ind]

    def order_rows(df, kind, label):
        per = []
        for _, r in df.iterrows():
            ks, kh = int(r["_k起點"]), int(r["_k高點"])
            ev = stock_events(int(r["_i"])) if kind == "stock" else ind_events(r["_ind"])
            rec = {"單位": label, **{c: r[c] for c in ("代號", "名稱", "版", "段號", "產業", "類", "起點") if c in df.columns}}
            for e in EVN:
                kf = first_in(ev[e], ks - 24, kh); kn = nearest_in(ev[e], ks - 24, kh, ks)
                rec[f"{e}_月差(窗內第一次)"] = (kf - ks) if kf is not None else np.nan
                rec[f"{e}_月差(最接近起點)"] = (kn - ks) if kn is not None else np.nan
            per.append(rec)
        per = pd.DataFrame(per)
        summ = []
        for e in EVN:
          for dfn in ("最接近起點", "窗內第一次"):
            v = per[f"{e}_月差({dfn})"].to_numpy(float); n = len(v); has = np.isfinite(v)
            main_ = (dfn == "窗內第一次") if e == "營收創24月新高首次" else (dfn == "最接近起點")
            summ.append({"單位": label, "事件": e, "定義": dfn + ("（主）" if main_ else "（並報）"), "段數": n, "早(<0)": float((v[has] < 0).sum() / n) if n else np.nan,
                         "同(=0)": float((v[has] == 0).sum() / n) if n else np.nan, "晚(>0)": float((v[has] > 0).sum() / n) if n else np.nan,
                         "窗內無": float((~has).sum() / n) if n else np.nan, "有事件者中位月差": float(np.median(v[has])) if has.any() else np.nan,
                         "有事件者p25": float(np.percentile(v[has], 25)) if has.any() else np.nan, "有事件者p75": float(np.percentile(v[has], 75)) if has.any() else np.nan})
        return per, summ
    OY, sY = order_rows(YI, "stock", "乙×3"); OB, sB = order_rows(BI.rename(columns={"高點(窗內最高)": "高點"}), "stock", "B乙（自己的起點、窗內最高）")
    SUMY = pd.DataFrame(sY + sB)
    OJ = []; sJ = []
    for vn in ("原版市值", "原版等權", "補充市值", "補充等權"):
        o_, s_ = order_rows(JA[JA["版"] == vn], "ind", f"甲{vn}"); OJ.append(o_); sJ += s_
        o_, s_ = order_rows(JB[JB["版"] == vn], "ind", f"B甲{vn}"); OJ.append(o_); sJ += s_
    for t in list(TYPES) + ["未標"]:
        sub = JA[JA["類"] == t]
        if len(sub):
            _, s_ = order_rows(sub, "ind", f"甲類 {t}（四版合併）"); sJ += s_
    SUMJ = pd.DataFrame(sJ); OJ = pd.concat(OJ, ignore_index=True)
    log(f"[C① 先後] ｜{time.time() - t0:.0f}s")

    # ═════════ C②：個股自己漲 ═════════
    S1s = pd.read_csv(os.path.join(S1, "甲_段.csv")); S2s = pd.read_csv(os.path.join(S2, "甲補充_段.csv"))
    JSEG = defaultdict(list)
    for df in (S1s, S2s):
        for _, r in df.iterrows():
            JSEG[r["產業"]].append((pd.Timestamp(r["起點"]), pd.Timestamp(r["高點"])))
    Y = YI.copy()
    Y["與任一甲段相交"] = [any(a_ <= pd.Timestamp(h) and pd.Timestamp(s0) <= b_ for a_, b_ in JSEG.get(ind, []))
                       for ind, s0, h in zip(Y["產業(起點PIT)"], Y["起點"], Y["高點"])]
    Y["族群≥3段"] = Y["族群(切0.7)"] > 0
    SELF = Y[~Y["與任一甲段相交"] & ~Y["族群≥3段"]].copy()
    news = []
    for f in sorted(glob.glob(os.path.join(DN, "mops", "news", "*.csv"))):
        if int(os.path.basename(f)[:4]) >= 2004:
            x = pd.read_csv(f, dtype={"stock_id": str}, usecols=["date", "stock_id"]); news.append(x[x["stock_id"].isin(set(SELF["代號"]))])
    news = pd.concat(news); news["d"] = pd.to_datetime(news["date"], errors="coerce")
    NG = {s: np.sort(g["d"].dropna().values) for s, g in news.groupby("stock_id")}
    SELF["起點→高點重大訊息則數"] = [int(((NG.get(s, np.array([], "datetime64[ns]")) > np.datetime64(pd.Timestamp(a_))) &
                                     (NG.get(s, np.array([], "datetime64[ns]")) <= np.datetime64(pd.Timestamp(b_)))).sum()) if s in NG else 0
                                for s, a_, b_ in zip(SELF["代號"], SELF["起點"], SELF["高點"])]
    SELF["起點→高點重大訊息類別前3名"] = "無（mops/news 只有主旨、無類別欄）"
    ii = SELF["_i"].to_numpy(int); ks = SELF["_k起點"].to_numpy(int)
    for nm, arr in (("月營收年增", P["月營收年增"]), ("毛利率年變化(xbrl)", NP3["毛利率年變化"])):
        for off in (-12, 12):
            kk = ks + off; ok = (kk >= 0) & (kk < K); v = np.full(len(SELF), np.nan); v[ok] = arr[ii[ok], kk[ok]]
            SELF[f"{nm}@起點{'前' if off < 0 else '後'}12月"] = v
    SELF["起點市值(億)"] = SELF["市值(億)@起點"]; SELF["上市年資(左截斷記缺)"] = SELF["上市年資@起點"]
    SELF["起點→高點現增可轉債決議次數"] = SELF["現增可轉債決議次數@起點→高點"]; SELF["高點後12月最大跌幅"] = SELF["⑩高點後12月最大跌幅"]
    yrs_ = pd.to_datetime(SELF["起點"]).dt.year
    SSUM = pd.DataFrame([{"乙×3段數": len(Y), "與任一甲段相交": int(Y["與任一甲段相交"].sum()), "在族群≥3段": int(Y["族群≥3段"].sum()),
                          "個股自己漲段數": len(SELF), "占乙": len(SELF) / len(Y) if len(Y) else np.nan, "檔數": SELF["代號"].nunique()}])
    SYR = SELF.groupby(yrs_).size().rename("段數").reset_index().rename(columns={"起點": "起點年"})
    SIN = SELF["產業(起點PIT)"].value_counts().rename_axis("產業").reset_index(name="段數")
    SIN["占自己漲"] = SIN["段數"] / len(SELF) if len(SELF) else np.nan
    allin = Y["產業(起點PIT)"].value_counts(); SIN["該產業乙段數"] = [int(allin.get(x, 0)) for x in SIN["產業"]]
    TOP = SELF[yrs_ >= 2013].sort_values("倍數", ascending=False).head(60)
    TOPC = ["代號", "名稱", "起點", "高點", "倍數", "產業(起點PIT)", "起點市值(億)", "上市年資(左截斷記缺)", "月營收年增@起點前12月", "月營收年增@起點後12月",
            "毛利率年變化(xbrl)@起點前12月", "毛利率年變化(xbrl)@起點後12月", "起點→高點現增可轉債決議次數", "起點→高點重大訊息則數",
            "起點→高點重大訊息類別前3名", "高點後12月最大跌幅"]
    log(f"[C② 自己漲] {len(SELF)} 段｜{time.time() - t0:.0f}s")

    # ═════════ B：現在在谷底 ═════════
    fmin, _ = LP.load_filing(DN)
    FAV = defaultdict(list)
    for (s, qk), tts in fmin.items():
        if s in ids:
            FAV[s].append((pd.Timestamp(tts).normalize(), int(qk)))
    AVR = np.array([np.datetime64(LP.rev_avail(p_)) for p_ in PERIODS], "datetime64[ns]")

    def stock_fund(s, d):
        o = {}
        km = int(np.searchsorted(AVR, np.datetime64(d), "left")) - 1
        rv, ly = REVA.get(s), LYA.get(s)
        o["rev3"] = o["ly3"] = np.nan
        if rv is not None:
            for kr in range(km, max(km - 3, -1), -1):
                if np.isfinite(rv[kr]):
                    if kr >= 2 and np.isfinite(rv[kr - 2:kr + 1]).all() and np.isfinite(ly[kr - 2:kr + 1]).all() and ly[kr - 2:kr + 1].sum() > 0:
                        o["rev3"], o["ly3"] = rv[kr - 2:kr + 1].sum(), ly[kr - 2:kr + 1].sum()
                    break
        q = QA.get(s); cand = [qk for dd, qk in FAV.get(s, []) if dd < d]
        for k_ in ("oi4", "r4", "oi4p", "r4p", "inv", "cg", "invp", "cgp", "cap", "capp"):
            o[k_] = np.nan
        if q is not None and cand:
            j = max(cand) - QK0
            if j >= 7:
                s4 = lambda a, jj: a[jj - 3:jj + 1].sum() if np.isfinite(a[jj - 3:jj + 1]).all() else np.nan
                o["oi4"], o["r4"], o["oi4p"], o["r4p"] = s4(q["oi"], j), s4(q["rev"], j), s4(q["oi"], j - 4), s4(q["rev"], j - 4)
                o["cap"], o["capp"] = s4(q["cap"], j), s4(q["cap"], j - 4)
            if j >= 4:
                o["inv"], o["cg"], o["invp"], o["cgp"] = q["inv"][j], q["cogs"][j], q["inv"][j - 4], q["cogs"][j - 4]
        return o

    def stock_metrics(o):
        r = lambda a_, b_: a_ / b_ if np.isfinite(a_) and np.isfinite(b_) and b_ > 0 else np.nan
        m = {"近4季營業利益率": r(o["oi4"], o["r4"])}
        m["近4季營業利益率與前一年比"] = m["近4季營業利益率"] - r(o["oi4p"], o["r4p"])
        m["近3月營收年增"] = r(o["rev3"], o["ly3"]) - 1
        m["存貨天數年變化"] = r(o["inv"], o["cg"]) * DAYS_Q - r(o["invp"], o["cgp"]) * DAYS_Q
        m["近4季資本支出年增"] = r(o["cap"], o["capp"]) - 1
        return m

    def group_row(mem_idx, p, IDXd):
        d = CAL[p]; row = {"成員數(當日在市)": len(mem_idx)}
        for kd, lab in (("ew", "等權"), ("vw", "市值")):
            I_, H_ = IDXd[kd]
            p3 = cpos_le(d - pd.DateOffset(years=3))
            row[f"前3年報酬_{lab}"] = I_[p] / I_[p3] - 1 if (p3 >= 0 and H_[p] >= 0 and H_[p] == H_[p3]) else np.nan
            if H_[p] >= 0:
                lo = max(0, p - 1249); w_ = I_[lo:p + 1][H_[lo:p + 1] == H_[p]]
                row[f"距5年高點_{lab}"] = I_[p] / w_.max() - 1
            else:
                row[f"距5年高點_{lab}"] = np.nan
        F = [stock_fund(SIDS[i], d) for i in mem_idx]
        sm = lambda key, cond: np.nansum([f_[key] for f_ in F if cond(f_)])
        ok_o = lambda f_: all(np.isfinite([f_["oi4"], f_["r4"], f_["oi4p"], f_["r4p"]]))
        ok_r = lambda f_: np.isfinite(f_["rev3"]) and np.isfinite(f_["ly3"])
        ok_i = lambda f_: all(np.isfinite([f_["inv"], f_["cg"], f_["invp"], f_["cgp"]])) and f_["cg"] > 0 and f_["cgp"] > 0
        ok_c = lambda f_: np.isfinite(f_["cap"]) and np.isfinite(f_["capp"])
        R4, R4p = sm("r4", ok_o), sm("r4p", ok_o)
        row["近4季營業利益率(加總)"] = sm("oi4", ok_o) / R4 if R4 > 0 else np.nan
        row["近4季營業利益率與前一年比(加總,百分點)"] = (row["近4季營業利益率(加總)"] - sm("oi4p", ok_o) / R4p) if (R4 > 0 and R4p > 0) else np.nan
        L3 = sm("ly3", ok_r); row["近3月營收年增(加總)"] = sm("rev3", ok_r) / L3 - 1 if L3 > 0 else np.nan
        CG, CGp = sm("cg", ok_i), sm("cgp", ok_i)
        row["存貨天數年變化(加總,天)"] = (sm("inv", ok_i) / CG - sm("invp", ok_i) / CGp) * DAYS_Q if CG > 0 and CGp > 0 else np.nan
        CP = sm("capp", ok_c); row["近4季資本支出年增(加總)"] = sm("cap", ok_c) / CP - 1 if CP > 0 else np.nan
        M = [stock_metrics(f_) for f_ in F]
        for kk in ("近4季營業利益率與前一年比", "近3月營收年增", "存貨天數年變化", "近4季資本支出年增"):
            v = np.array([m_[kk] for m_ in M], float); v = v[np.isfinite(v)]
            row[f"{kk}(成員中位)"] = float(np.median(v)) if len(v) else np.nan
            row[f"{kk}(成員有值數)"] = int(len(v))
        return row
    pnow = CEND; dnow = CAL[pnow]
    aln = np.flatnonzero(alive_at(pnow))
    BI_rows = []
    byind_now = defaultdict(list)
    for i in aln:
        ind, _ = PIT.at(SIDS[i], dnow)
        if ind is not None and ind not in EXCL_IND:
            byind_now[ind].append(i)
    for ind, mem in sorted(byind_now.items()):
        if ind not in IDXI:
            continue
        BI_rows.append({"分法": "產業(PIT)", "名稱": ind, **group_row(np.array(mem), pnow, IDXI[ind])})
    BIND = pd.DataFrame(BI_rows).sort_values("前3年報酬_等權", na_position="last")
    GS = pd.read_csv(os.path.join(S2, "族群_段.csv"), dtype={"代號": str})
    GR = pd.read_csv(os.path.join(S2, "族群_群.csv"))
    GROWS = []
    alset = set(aln.tolist())
    for g, sub in GS[GS["群_切0.7"] > 0].groupby("群_切0.7"):
        mem_all = np.array(sorted({IX[s] for s in sub["代號"] if s in IX}), np.int64)
        mem_now = np.array([i for i in mem_all if i in alset], np.int64)
        if len(mem_now) < 3:
            continue
        IDXg = build_index(lambda b, m=mem_all: m[alive_at(b)[m]], 3)
        gi = GR[GR["群號"] == g].iloc[0]
        GROWS.append({"分法": "族群(切0.7)", "名稱": f"群{g}", "代表股": gi["代表股"], "群期間": gi["期間"], "官方產業分布": gi["官方產業分布"],
                      **group_row(mem_now, pnow, IDXg)})
    BGRP = pd.DataFrame(GROWS).sort_values("前3年報酬_等權", na_position="last") if GROWS else pd.DataFrame()
    log(f"[B 現在] 產業 {len(BIND)}、族群 {len(BGRP)}｜{time.time() - t0:.0f}s")
    HIST = []
    for t in ("A 缺貨漲價", "C 谷底翻身"):
        for sid in TYPES[t].split():
            r = JA[JA["段號"] == sid]
            if not len(r):
                continue
            r = r.iloc[0]; ks = int(r["_k起點"]) - 12
            if ks < 0:
                HIST.append({"類": t, "段號": sid, "產業": r["產業"], "起點": r["起點"], "時點": "前12月早於資料"}); continue
            p12 = int(MEp[ks]); kd = "vw" if "vw-" in sid else "ew"
            ind = r["產業"]
            mem = np.array([i for i in np.flatnonzero(alive_at(p12)) if PIT.at(SIDS[i], CAL[p12])[0] == ind], np.int64)
            gr = group_row(mem, p12, IDXI[ind])
            gr = {k_: v for k_, v in gr.items() if not k_.endswith("_等權" if kd == "vw" else "_市值")}
            gr = {k_.replace("_等權", "(該段的版)").replace("_市值", "(該段的版)"): v for k_, v in gr.items()}
            HIST.append({"類": t, "段號": sid, "產業": ind, "起點": r["起點"], "時點": str(CAL[p12].date()), **gr})
    HIST = pd.DataFrame(HIST)
    HM = []
    num = [c for c in HIST.columns if c not in ("類", "段號", "產業", "起點", "時點") and not c.endswith("有值數)")]
    for t, g in HIST.groupby("類"):
        HM.append({"分法": f"歷史 {t} 段起點前12月中位", "名稱": f"{t}（{len(g)} 段）", **{c: float(np.nanmedian(g[c].to_numpy(float))) if np.isfinite(g[c].to_numpy(float)).any() else np.nan for c in num}})
    HM = pd.DataFrame(HM)
    # 存檔
    for d_, nm in ((BIND, "谷底_產業.csv"), (BGRP, "谷底_族群.csv"), (HIST, "歷史AC段_前12月.csv"), (HM, "歷史AC型_前12月中位.csv")):
        w(d_, "B", nm)
    w(PATHY, "C", "路徑_乙.csv"); w(PATHJ, "C", "路徑_甲.csv"); w(SUMY, "C", "先後_乙.csv"); w(SUMJ, "C", "先後_甲.csv")
    with gzip.open(os.path.join(out, "C", "先後_逐段_乙.csv.gz"), "wt", encoding="utf-8") as fh:
        pd.concat([OY, OB]).to_csv(fh, index=False)
    with gzip.open(os.path.join(out, "C", "先後_逐段_甲.csv.gz"), "wt", encoding="utf-8") as fh:
        OJ.to_csv(fh, index=False)
    w(SSUM, "C", "自己漲_彙總.csv"); w(SYR, "C", "自己漲_年.csv"); w(SIN, "C", "自己漲_產業.csv"); w(TOP[TOPC], "C", "自己漲_前60.csv")
    with gzip.open(os.path.join(out, "C", "自己漲_全部.csv.gz"), "wt", encoding="utf-8") as fh:
        SELF[["代號", "名稱", "起點", "高點", "倍數", "產業(起點PIT)", "_i", "_k起點"] + TOPC[6:]].to_csv(fh, index=False)
    pickle.dump({"FHn": FHn, "FHc": FHc, "OPM": OPM, "IVDC": IVDC, "HI24": HI24, "SIDS": SIDS, "MEp": MEp}, open(os.path.join(WORK, f"bgr4_{tag}.pkl"), "wb"), protocol=5)
    J = {"性質": "描述（⛔ 不判、不計 N、不檢定、不打分、不排名）", "依據": "資料庫 1849；台股 seq536、seq537；裁定 seq421", "新快照": SHA,
         "月營收與產業別快照": "dbfb96cb81a7", "現在": str(dnow.date()), "乾跑": a.dry, "必附": NOTES, "讀法": __doc__.split("═══ 讀法")[1],
         "A": {"欄": list(NEWA)}, "B": {"產業": len(BIND), "族群": len(BGRP), "歷史A段": int((HIST["類"] == "A 缺貨漲價").sum()) if len(HIST) else 0,
                                     "歷史C段": int((HIST["類"] == "C 谷底翻身").sum()) if len(HIST) else 0},
         "C": {"自己漲段數": len(SELF), "甲類": dict(Counter(JA["類"]))}, "時間": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M"),
         "耗時秒": round(time.time() - t0)}
    json.dump(J, open(os.path.join(out, "bigrun4.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] {time.time() - t0:.0f}s ⇒ {out}")
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
