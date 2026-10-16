# -*- coding: utf-8 -*-
"""大盤大跌後「只能買 1～3 檔」——【只從該事件 C+ 名單內】依綜合分數挑最高 1／2／3 檔 vs C+ 隨機挑 vs 0050／00631L（描述性初測；⛔ 不計 N、⛔ 不判定、⛔ 不是買賣建議）
回測線計算子代理，2026-10-17。使用者：「基本面、營收獲利、未來性評比下去挑呢？」「或是籌碼或線型！」「我是指綜合分數高的會不會比較好！」
「我是從你跌最深的裡面挑的喔，不要往外延伸喔！」⇒ 所有分數的挑檔候選一律只限該事件 C+（大跌日跌最多一成 ∧ 營收年增 ＞ 0）；F7 百分位照情報規則在大母體算、挑檔仍只在 C+ 內

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMktDrop_fund [--procs 4]

═══ 讀法（寫死於第一次跑之前；⚠ F1～F6 分數規則是看過 pick 結果之後才設計的；F7 是情報線未看結果先寄、凍結）═══
 U0 ⛔ 不重跑引擎：逐筆報酬只讀 resultsMktDrop/deep/c_rows.csv（v1 C 全體、主出場「加權收盤收復事件前一日收盤 ⇒ 隔天開盤賣」、成本 0.585%、淨報酬）；
    C+ ＝ C 中 yoy ＞ 0（同 pick）；A 0050、B 00631L、C+ 全買 ＝ 同 pick（v1／yl event_rows；程式內對帳）；隨機 ＝ 同 pick（同種子、同列序 ⇒ 與 pick/random.csv 對帳）
 U1 F1～F6 子項（只用事件日 t 收盤以前可得；百分位 ＝ 該事件 C+ 名單內排名 pct（同值取平均）；方向一律「大 ＝ 好」）
    營收（3）：rv_yoy 最近一期年增（c_rows）；rv_yoy3 最近 3 個可得期年增平均（3 期都要有）；rv_hi24 創 24 月新高（c_rows）
       月營收可得日（researchExit5.avail_pos）：≤2025-12 期次月 10 日後、≥2026-01 期次月 15 日後第一個交易日
    獲利（4）：pf_eps4 近四季 EPS 合計 ＞ 0；pf_pbt 單季稅前淨利年增（÷|去年同季|）；pf_roe 近四季母公司淨利 ÷ 期末母公司權益；pf_gm 單季毛利率 − 去年同季
    未來性（3；⚠ 沒有分析師預估 ⇒ 只用財報代理）：ft_cl 合約負債年增（2018 起；兩欄都空 ⇒ 缺）；ft_capex 年初至今資本支出年增；ft_inv ＝ −（存貨年增 − 單季營收年增）
       財報：data/meta/fs_xbrl ＋ data/mops/fin_hist（年初至今差分成單季），origin/main f48d0851da 唯讀 git archive（~/mktdropwork/fund/f48d0851da）
       可得日（seq352）：filing_dates.csv（t57sb01）該季最早上傳日期 ⇒ 事件日 ＞ 上傳日才可用；F1～F6 找不到時戳 ⇒ 法定期限（Q1 5/15、Q2 8/14、Q3 11/14、年報次年 3/31）
    籌碼（6 欄）：ch_i1／i5／i20 事件日、近 5、近 20 根三大法人合計 ÷ 同窗成交股數；ch_t20 近 20 根投信 ÷ 成交股數；
       ch_big 集保 ＞1000 張（level 15）比例 4 週變化（照公布：資料日之後的下一個週一起可用）；ch_mu ＝ −融資使用率（不能融資 ⇒ 缺）；法人融資 2015 起
    線型（6）：tc_r60 前 60 日漲幅；tc_d52 距 52 週高；tc_ma60、tc_ma120 前一天在均線之上；tc_rs ⚠ 改用前 20 日漲幅（同事件內 60 日 RS 與 tc_r60 排序完全相同）；
       tc_drop ＝ −當天報酬（跌越深越高；方向事後設定）
 U2 F1～F6 分數 ＝ 子項百分位等權平均；缺值 0 分、分母照子項數；⭐ F6 ＝ 全部 22 欄等權（主答之一）
    附表：F1 營收＋獲利＋未來性；F2 營收＋獲利；F3 獲利；F4 籌碼；F5 線型；兩兩 ＝ (Fa＋Fb)÷2；F6f ＝ (F1＋F4＋F5)÷3
    某事件某分數全部子項全缺 ⇒ 該事件該分數「缺」、不進統計
 U2b ⭐ F7（情報線 1017-0250 信逐字；寄出即凍結）：百分位在【大母體】算 ＝ 事件日有效收盤、前 20 日均成交金額 ≥ 5,000 萬（前 20 根、不含當天，同 c_rows amt20）的四碼普通股
    （代號 [1-9]ddd、kind stock）；C+ 若不在大母體 ⇒ 用它的值在大母體分布中的位置（＜ 的比例＋同值一半）——所有人同一公式
    A 營收 30%：0.4 最新單月年增＋0.4 近 3 月累計年增＋0.2 創 24 月新高（100／0）；B 獲利 25%：0.3 單季 EPS＞0（100／0）＋0.4 單季毛利率 − 前一季＋0.3 單季營益率；
    C 財報品質 15%：0.6 (100 − 應收（帳款＋票據）年增 − 單季營收年增 的百分位)＋0.4 (100 − 存貨年增 − 營收年增 的百分位)；金融保險（basi／bd／fh／ins）C 不算、權重平分（÷0.85）；
    D 籌碼 15%：外資＋投信 5 日 ÷ 5 日量、100 − 融資餘額 5 日變化率、集保千張比例最近一週變化（公布日 ＝ 資料日後下一個週一）；有的等權；
    E 線型 15%：0.5 收盤÷MA60−1（上市未滿 60 根 ⇒ 缺）＋0.5 近 20 日報酬 − 大母體等權平均；（E 用事件日收盤，含大跌當天，照信「當天收盤」）
    缺值：細項缺 ⇒ 子項用其餘細項（權重按比例放大）；子項整個缺 ⇒ 50；年增分母 ≤ 0 ⇒ 細項缺
    季報可得日 ＝ filing_dates 第一次上傳日的下一個交易日；⚠ 該期沒有時戳（2016、2017 全部等）⇒ B、C 整個缺 ⇒ 50（協調者裁示）
    ⚠ fs_xbrl 沒有 EPS、毛利、營業利益 ⇒ B 用 fin_hist（同 MOPS；README 對帳 297,358/297,380 相符）；應收、存貨用 fs_xbrl
    同分 ⇒ A 高者；再同 ⇒ 代號
 U3 挑 N ＝ 只在該事件 C+ 內按分數降冪前 N 檔；報酬 ＝ 選中中買得到者淨報酬等權；全買不到 ⇒ 0（同 pick）
 U4 報：平均、中位、勝率、最差、虧 ＞10% 次數；隨機段平均分布中的位置（百分位 ＝ 隨機段平均 ＜ 分數段平均 的比例）
 U5 F6、F7 五分位：每事件 C+ 依分數排序切 5 組（Q5 高分）；組內買得到者等權；段內事件等權；事件群集 bootstrap 2000 次 CI；Q5−Q1；每事件 Spearman
 U6 10/15 前瞻：candidates_20261015.csv 的 C+ 75 檔（價量 ~/h2data/4b26f6…，同 pick；財報、籌碼 f48d0851da 只用 ≤ 10/15）；缺 ⇒「缺」
 U7 必附：28 事件；分數 18 種 × 3 N × 3 段多重比較；F1～F6 看過 pick 才設計 ⇒ 差異多半是運氣；描述性、不計 N、不判定
輸出 backtest/resultsMktDrop/fund/：MktDrop_fund.json、summary.csv、quintile.csv、features.csv、event_picks.csv、missing.csv、f7_universe.csv、forward_20261015.csv、forward_20261015_features.csv、run.log
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import time
from multiprocessing import Pool

import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)

REPO = os.path.expanduser("~/tw-p17")
OUT = os.path.join(REPO, "backtest/resultsMktDrop/fund")
CROWS = os.path.join(REPO, "backtest/resultsMktDrop/deep/c_rows.csv")
V1ER = os.path.join(REPO, "backtest/resultsMktDrop/v1/event_rows.csv")
YLER = os.path.join(REPO, "backtest/resultsMktDrop/yl/event_rows.csv.gz")
PICKRND = os.path.join(REPO, "backtest/resultsMktDrop/pick/random.csv")
FWD = os.path.join(REPO, "backtest/forward/mktdrop/candidates_20261015.csv")
FSHA = "4b26f6ad1efaf1369422f7e3b87c019a931d7d57"
FDATA = os.path.expanduser(f"~/h2data/{FSHA}/data")
MAINSHA = "f48d0851dda11d37d3ab14be025e46edfdfa1680"
XD = os.path.expanduser("~/mktdropwork/fund/f48d0851da/data")
F7LETTER = "件-回測會同裁定台股←市場情報分析線-20261017-0250-個股綜合評分規則F7（未看結果先寄）"
NR = 2000
SEED = 2026101602          # 同 pick
NBOOT = 2000
QSEED = 2026101701
SEGS = ["2006～2014", "2015～2021", "2022～", "全部"]
FINTPL = {"basi", "bd", "fh", "ins"}

FAM = {
    "營收": ["rv_yoy", "rv_yoy3", "rv_hi24"],
    "獲利": ["pf_eps4", "pf_pbt", "pf_roe", "pf_gm"],
    "未來性": ["ft_cl", "ft_capex", "ft_inv"],
    "籌碼": ["ch_i1", "ch_i5", "ch_i20", "ch_t20", "ch_big", "ch_mu"],
    "線型": ["tc_r60", "tc_d52", "tc_ma60", "tc_ma120", "tc_rs", "tc_drop"],
}
SUBNAME = {"rv_yoy": "最近一期營收年增", "rv_yoy3": "近3期營收年增平均", "rv_hi24": "營收創24月新高",
           "pf_eps4": "近四季EPS合計>0", "pf_pbt": "最近一季稅前淨利年增", "pf_roe": "ROE（近四季）", "pf_gm": "毛利率較去年同季",
           "ft_cl": "合約負債年增", "ft_capex": "資本支出年增", "ft_inv": "−(存貨年增−營收年增)",
           "ch_i1": "事件日三大法人÷成交量", "ch_i5": "5日三大法人÷成交量", "ch_i20": "20日三大法人÷成交量", "ch_t20": "20日投信÷成交量",
           "ch_big": "集保>1000張比例4週變化", "ch_mu": "−融資使用率",
           "tc_r60": "前60日漲幅", "tc_d52": "距52週高", "tc_ma60": "在MA60之上", "tc_ma120": "在MA120之上", "tc_rs": "前20日漲幅（RS代）", "tc_drop": "大跌日跌幅深"}
F7SUB = {"a1": "A①單月年增", "a2": "A②近3月累計年增", "a3": "A③創24月新高", "b1": "B①單季EPS>0", "b2": "B②毛利率−前季", "b3": "B③營益率",
         "c1": "C①應收年增−營收年增", "c2": "C②存貨年增−營收年增", "d1": "D①外資+投信5日÷量", "d2": "D②融資5日變化率", "d3": "D③集保千張週變化",
         "e1": "E①收盤÷MA60−1", "e2": "E②20日報酬−母體"}
SC = {"F1": FAM["營收"] + FAM["獲利"] + FAM["未來性"], "F2": FAM["營收"] + FAM["獲利"], "F3": FAM["獲利"], "F4": FAM["籌碼"], "F5": FAM["線型"]}
SC["F6"] = SC["F1"] + SC["F4"] + SC["F5"]
SCNAME = {"F7": "⭐情報F7（凍結規則、大母體百分位）", "F6": "⭐綜合F6（全部子項等權、C+內百分位）", "F1": "營收＋獲利＋未來性", "F2": "營收＋獲利", "F3": "獲利",
          "F4": "籌碼", "F5": "線型", "F6f": "三族等權（F1＋F4＋F5）÷3"}
PAIRS = [(a, b) for i, a in enumerate(["F1", "F2", "F3", "F4", "F5"]) for b in ["F1", "F2", "F3", "F4", "F5"][i + 1:]]
SCORES = ["F7", "F6", "F1", "F2", "F3", "F4", "F5", "F6f"] + [f"{a}+{b}" for a, b in PAIRS]
NOTES = ["⭐ 挑檔候選一律只限該事件 C+ 名單（大跌日跌最多一成 ∧ 營收年增 ＞ 0）；F7 百分位照情報規則在大母體算，但挑檔只在 C+ 內",
         "描述性初測：⛔ 不計 N、⛔ 不判定、⛔ 不是買賣建議",
         "只有 28 個事件（早年 10、2015～2021 7、2022～ 11）；分數 18 種 × 3 N × 3 段多重比較 ⇒ 分數越多、碰巧好看的越多；差異多半是運氣；百分位只是位置、不是檢定",
         "C+ 是看過 deep 拆解後切的；F1～F6 分數規則是看過 pick（7 條單一特徵都不穩定勝過隨機）之後才設計的；線型方向與「跌深＝好」是執行者設定 ⇒ 任何「看起來較好」只是待驗線索；F7 是情報線未看結果先寄（凍結）",
         "未來性只用財報代理（合約負債、資本支出、存貨相對營收）；沒有分析師預估資料",
         "財報 2013 起、法人與融資 2015 起、集保 2019-06 起連續 ⇒ 2006～2014 段（10 事件都在 2011-08 以前）只有營收＋線型：F3、F4 早年缺；F1＝F2＝營收；F6 早年＝營收＋線型；F7 早年 B、C、D ＝ 50 ⇒ 只剩 A、E",
         "財報可得日：t57sb01 上傳時戳（seq352）；F1～F6 缺時戳用法定期限（偏晚）；F7 缺時戳 ⇒ B、C 整個缺給 50（2016、2017 全部）",
         "RS 改用前 20 日漲幅：同事件內 60 日相對加權強度與前 60 日漲幅排序完全相同",
         "F1～F6 缺值 0 分 ⇒ 金融業（無存貨、毛利）等結構性缺值的股票分數偏低；缺值比例見 missing.csv",
         "B 00631L 2014-10 才上市 ⇒ 早年段沒有 B；主出場不設天數；成本 0.585% 來回；未含滑價"]
LOG = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


# ═════════════ 財報季表 ═════════════
def qkey(y, q):
    return int(y) * 4 + int(q) - 1


def load_fin():
    F = []
    for f in sorted(glob.glob(os.path.join(XD, "mops", "fin_hist", "*.csv"))):
        x = pd.read_csv(f, dtype={"stock_id": str})
        F.append(x[["stock_id", "period", "industry", "rev_ytd", "gp_ytd", "opi_ytd", "nip_ytd", "eps_ytd", "equity_parent"]])
    F = pd.concat(F).drop_duplicates(["stock_id", "period"], keep="last")
    X = []
    for f in sorted(glob.glob(os.path.join(XD, "meta", "fs_xbrl", "fs_xbrl_*.csv"))):
        x = pd.read_csv(f, dtype={"stock_id": str})
        x["_r"] = (x["report"] != "cr").astype(int)
        x = x.sort_values(["stock_id", "period", "_r"]).drop_duplicates(["stock_id", "period"], keep="first")
        X.append(x[["stock_id", "period", "industry_template", "inventories", "accounts_receivable", "notes_receivable", "contract_liabilities_current",
                    "contract_liabilities_noncurrent", "revenue_ytd", "profit_before_tax_ytd", "capex_ytd"]])
    X = pd.concat(X)
    M = F.merge(X, on=["stock_id", "period"], how="outer")
    M["y"] = M["period"].str[:4].astype(int); M["q"] = M["period"].str[-1].astype(int); M["qk"] = [qkey(a, b) for a, b in zip(M["y"], M["q"])]
    for c in ["rev_ytd", "gp_ytd", "opi_ytd", "nip_ytd", "eps_ytd", "equity_parent", "inventories", "accounts_receivable", "notes_receivable",
              "contract_liabilities_current", "contract_liabilities_noncurrent", "revenue_ytd", "profit_before_tax_ytd", "capex_ytd"]:
        M[c] = pd.to_numeric(M[c], errors="coerce")
    M["rev_ytd"] = M["rev_ytd"].where(M["rev_ytd"].notna(), M["revenue_ytd"])
    clc, cln = M["contract_liabilities_current"], M["contract_liabilities_noncurrent"]
    M["cl"] = np.where(clc.isna() & cln.isna(), np.nan, clc.fillna(0) + cln.fillna(0))
    ar, nr = M["accounts_receivable"], M["notes_receivable"]
    M["arn"] = np.where(ar.isna() & nr.isna(), np.nan, ar.fillna(0) + nr.fillna(0))
    tpl = M["industry_template"].where(M["industry_template"].notna(), M["industry"])
    M["fin_ind"] = tpl.isin(FINTPL)
    fd = pd.read_csv(os.path.join(XD, "meta", "filing_dates.csv"), dtype=str)
    fd["d"] = pd.to_datetime(fd["uploaded_at"].astype(str).str[:10], errors="coerce")
    fd = fd.dropna(subset=["d"])
    fd["qk"] = [qkey(a, b) for a, b in zip(fd["year"], fd["season"])]
    fmin = fd.groupby(["stock_id", "qk"])["d"].min()
    dl = {1: (5, 15), 2: (8, 14), 3: (11, 14)}

    def deadline(y, q):
        return pd.Timestamp(year=y + 1, month=3, day=31) if q == 4 else pd.Timestamp(year=y, month=dl[q][0], day=dl[q][1])
    av = []; src = []
    for s, k, y, q in zip(M["stock_id"], M["qk"], M["y"], M["q"]):
        t = fmin.get((s, k))
        if t is not None and pd.notna(t):
            av.append(t); src.append("t57sb01")
        else:
            av.append(deadline(y, q)); src.append("法定期限")
    M["avail"] = pd.to_datetime(av); M["avail_src"] = src
    out = {}
    for s, g in M.groupby("stock_id"):
        g = g.set_index("qk").sort_index()
        g = pd.DataFrame(index=np.arange(g.index.min(), g.index.max() + 1)).join(g)
        q = (g.index.to_numpy() % 4) + 1
        for c in ["rev_ytd", "gp_ytd", "opi_ytd", "nip_ytd", "eps_ytd", "profit_before_tax_ytd"]:
            v = g[c].to_numpy(float); pv = np.r_[np.nan, v[:-1]]
            g[c.replace("_ytd", "_q")] = np.where(q == 1, v, v - pv)
        out[s] = {"qk": g.index.to_numpy(), "avail": g["avail"].to_numpy("datetime64[ns]"), "src": g["avail_src"].to_numpy(object),
                  "has": (g["rev_ytd"].notna() | g["eps_ytd"].notna() | g["profit_before_tax_ytd"].notna()).to_numpy(),
                  **{c: g[c].to_numpy(float) for c in ["eps_q", "rev_q", "gp_q", "opi_q", "nip_q", "profit_before_tax_q", "equity_parent", "cl", "arn",
                                                       "inventories", "capex_ytd"]},
                  "fin_ind": g["fin_ind"].fillna(False).to_numpy(bool)}
    nts = int((M["avail_src"] == "t57sb01").sum())
    info = {"季列": int(len(M)), "有t57sb01時戳": nts, "無時戳": int(len(M) - nts),
            "無時戳占比（依年）": {int(k): round(float(v), 3) for k, v in M.groupby("y")["avail_src"].apply(lambda z: (z == "法定期限").mean()).items()}}
    return out, info


def fin_latest(g, t):
    """⇒ (位置 j, 來源) 或 (None, None)：可得日 ＜ t 的最新一季"""
    if g is None:
        return None, None
    ok = g["has"] & (~np.isnat(g["avail"])) & (g["avail"] < np.datetime64(t))
    if not ok.any():
        return None, None
    j = int(np.flatnonzero(ok).max())
    return j, g["src"][j]


def gv(g, c, j):
    return float(g[c][j]) if (j is not None and 0 <= j < len(g["qk"])) else np.nan


def fin_feats(g, t):
    f = {k: np.nan for k in FAM["獲利"] + FAM["未來性"]}
    f["fin_q"] = None; f["fin_src"] = None
    j, src = fin_latest(g, t)
    if j is None:
        return f
    k = int(g["qk"][j]); f["fin_q"] = f"{k // 4}Q{k % 4 + 1}"; f["fin_src"] = src
    j4 = j - 4 if j - 4 >= 0 else None
    e4 = [gv(g, "eps_q", jj) for jj in range(j - 3, j + 1)] if j >= 3 else [np.nan]
    if all(np.isfinite(e4)):
        f["pf_eps4"] = float(sum(e4) > 0)
    pb, pb4 = gv(g, "profit_before_tax_q", j), gv(g, "profit_before_tax_q", j4)
    if np.isfinite(pb) and np.isfinite(pb4) and pb4 != 0:
        f["pf_pbt"] = (pb - pb4) / abs(pb4)
    n4 = [gv(g, "nip_q", jj) for jj in range(j - 3, j + 1)] if j >= 3 else [np.nan]; eq = gv(g, "equity_parent", j)
    if all(np.isfinite(n4)) and np.isfinite(eq) and eq > 0:
        f["pf_roe"] = sum(n4) / eq
    rv, rv4, gp, gp4 = gv(g, "rev_q", j), gv(g, "rev_q", j4), gv(g, "gp_q", j), gv(g, "gp_q", j4)
    if np.isfinite(rv) and rv > 0 and np.isfinite(rv4) and rv4 > 0 and np.isfinite(gp) and np.isfinite(gp4):
        f["pf_gm"] = gp / rv - gp4 / rv4
    cl, cl4 = gv(g, "cl", j), gv(g, "cl", j4)
    if np.isfinite(cl) and np.isfinite(cl4) and cl4 > 0:
        f["ft_cl"] = cl / cl4 - 1
    cx, cx4 = gv(g, "capex_ytd", j), gv(g, "capex_ytd", j4)
    if np.isfinite(cx) and np.isfinite(cx4) and abs(cx4) > 0:
        f["ft_capex"] = abs(cx) / abs(cx4) - 1
    iv, iv4 = gv(g, "inventories", j), gv(g, "inventories", j4)
    if np.isfinite(iv) and np.isfinite(iv4) and iv4 > 0 and np.isfinite(rv) and np.isfinite(rv4) and rv4 > 0:
        f["ft_inv"] = -((iv / iv4 - 1) - (rv / rv4 - 1))
    return f


def fin7(g, t):
    """F7 B、C 細項原值；沒時戳 ⇒ 全缺（B、C ＝ 50）"""
    f = {"b1": np.nan, "b2": np.nan, "b3": np.nan, "c1": np.nan, "c2": np.nan, "fin_ind": False, "f7_fin_q": None}
    j, src = fin_latest(g, t)
    if j is None:
        return f
    f["fin_ind"] = bool(g["fin_ind"][j])
    if src != "t57sb01":
        f["f7_fin_q"] = "無時戳⇒50"; return f
    k = int(g["qk"][j]); f["f7_fin_q"] = f"{k // 4}Q{k % 4 + 1}"
    j1 = j - 1 if j >= 1 else None; j4 = j - 4 if j >= 4 else None
    e = gv(g, "eps_q", j)
    if np.isfinite(e):
        f["b1"] = 100.0 if e > 0 else 0.0
    rv, rv1, rv4 = gv(g, "rev_q", j), gv(g, "rev_q", j1), gv(g, "rev_q", j4)
    gp, gp1 = gv(g, "gp_q", j), gv(g, "gp_q", j1)
    if np.isfinite(rv) and rv > 0 and np.isfinite(rv1) and rv1 > 0 and np.isfinite(gp) and np.isfinite(gp1):
        f["b2"] = 100 * (gp / rv - gp1 / rv1)
    op = gv(g, "opi_q", j)
    if np.isfinite(rv) and rv > 0 and np.isfinite(op):
        f["b3"] = 100 * op / rv
    ry = (rv / rv4 - 1) if (np.isfinite(rv) and np.isfinite(rv4) and rv4 > 0) else np.nan
    a, a4 = gv(g, "arn", j), gv(g, "arn", j4)
    if np.isfinite(ry) and np.isfinite(a) and np.isfinite(a4) and a4 > 0:
        f["c1"] = 100 * ((a / a4 - 1) - ry)
    iv, iv4 = gv(g, "inventories", j), gv(g, "inventories", j4)
    if np.isfinite(ry) and np.isfinite(iv) and np.isfinite(iv4) and iv4 > 0:
        f["c2"] = 100 * ((iv / iv4 - 1) - ry)
    return f


# ═════════════ 月營收（F7 A）═════════════
def rev7(sid, rev, rly, AVarr, p):
    """F7 A 細項；AVarr ＝ 各期可得位置（同 rev.index 序）"""
    f = {"a1": np.nan, "a2": np.nan, "a3": np.nan}
    if sid not in rev.columns:
        return f
    rv = rev[sid].to_numpy(float); rl = rly[sid].to_numpy(float)
    ok = np.isfinite(rv) & (AVarr <= p)
    if not ok.any():
        return f
    k = int(np.flatnonzero(ok).max())
    if np.isfinite(rl[k]) and rl[k] > 0:
        f["a1"] = 100 * (rv[k] / rl[k] - 1)
    if k >= 2 and np.isfinite(rv[k - 2:k + 1]).all() and np.isfinite(rl[k - 2:k + 1]).all() and rl[k - 2:k + 1].sum() > 0:
        f["a2"] = 100 * (rv[k - 2:k + 1].sum() / rl[k - 2:k + 1].sum() - 1)
    hist = rv[max(0, k - 24):k]
    if len(hist) == 24 and np.isfinite(hist).all():
        f["a3"] = 100.0 if rv[k] >= hist.max() else 0.0
    return f


# ═════════════ 集保 ═════════════
def load_tdcc():
    P = []
    for f in sorted(glob.glob(os.path.join(XD, "tdcc_hist", "*.parquet"))):
        x = pd.read_parquet(f, columns=["date", "stock_id", "level", "pct"])
        P.append(x[x["level"].astype(int) == 15])
    for f in sorted(glob.glob(os.path.join(XD, "tdcc", "*.csv"))):
        x = pd.read_csv(f, dtype={"stock_id": str, "date": str}, usecols=["date", "stock_id", "level", "pct"])
        P.append(x[x["level"].astype(int) == 15])
    T = pd.concat(P)
    T["date"] = pd.to_datetime(T["date"].astype(str)); T["stock_id"] = T["stock_id"].astype(str); T["pct"] = pd.to_numeric(T["pct"], errors="coerce")
    T = T.drop_duplicates(["stock_id", "date"], keep="last").sort_values(["stock_id", "date"])
    # 公布 ⇒ 資料日之後的下一個週一起可用
    T["avail"] = T["date"] + pd.to_timedelta(7 - T["date"].dt.weekday, unit="D")
    return {s: (g["date"].to_numpy(), g["avail"].to_numpy(), g["pct"].to_numpy(float)) for s, g in T.groupby("stock_id")}, sorted(T["date"].unique())


def tdcc_chg(TD, sid, t, weeks):
    """可用（avail ≤ t）的最新一週 − 往前 weeks 週；⇒ (變化, 資料日)"""
    if sid not in TD:
        return np.nan, None
    d, av, v = TD[sid]
    j = int(np.searchsorted(av, np.datetime64(t), "right")) - 1
    if j < 0 or (np.datetime64(t) - av[j]) > np.timedelta64(10, "D"):
        return np.nan, None
    target = d[j] - np.timedelta64(7 * weeks, "D")
    j2 = int(np.searchsorted(d, target + np.timedelta64(3, "D"), "right")) - 1
    gap = d[j] - d[j2] if j2 >= 0 else None
    if j2 < 0 or j2 >= j or gap > np.timedelta64(7 * weeks + 7, "D") or gap < np.timedelta64(7 * weeks - 4, "D"):
        return np.nan, None
    if not (np.isfinite(v[j]) and np.isfinite(v[j2])):
        return np.nan, None
    return float(v[j] - v[j2]), str(pd.Timestamp(d[j]).date())


# ═════════════ 逐股：價量＋法人＋融資（Pool）═════════════
_G: dict = {}
BCOLS = ["tc_ma120", "ch_i1", "ch_i5", "ch_i20", "ch_t20", "ch_mu", "chk_r60", "chk_d52", "chk_ma60", "chk_r20", "chk_ret1",
         "valid", "amt20", "e1", "e2", "d1", "d2"]


def uni_job(a):
    wdata, sid, mkt, dates = a
    from backtest import data as D
    from backtest import research11 as R
    D.DATA = wdata
    cal = _G["cal"][wdata]
    out = {}
    B = R.load_bars(sid, mkt, cal)
    if B is not None:
        idx = B["idx"].astype(np.int64); c = np.asarray(B["c"], float); amt = np.asarray(B["amt"], float)
        vol = B["df"]["volume"].to_numpy(float)[idx]; nxb = np.asarray(B["next_bad"]); nb = len(idx)
        bad = np.asarray(nxb[:nb] == np.arange(nb), bool); src = "load_bars"
    else:
        st = D.load_stock(sid, mkt, cal)
        if st is None:
            return sid, {ds: {k: np.nan for k in BCOLS} | {"err": "no stock"} for ds in dates}
        df = st.df; idx = np.flatnonzero(df["traded"].to_numpy()); nb = len(idx)
        c = df["close"].to_numpy(float)[idx]; amt = df["amount"].to_numpy(float)[idx]; vol = df["volume"].to_numpy(float)[idx]
        bad = np.zeros(nb, bool); gap = np.diff(idx) - 1; bad[1:] |= gap >= 5; src = "load_stock（＜260根，只查缺口）"
    CB = np.r_[0, np.cumsum(bad)]

    def clean(a_, b_):
        return a_ >= 0 and b_ < nb and CB[b_ + 1] - CB[a_ + 1] == 0
    inst = None; marg = None
    if any(ds >= "2015-01-05" for ds in dates):
        fp = os.path.join(XD, "stocks_inst", f"{sid}.csv")
        if os.path.exists(fp):
            x = pd.read_csv(fp, dtype={"date": str}, usecols=["date", "foreign", "trust", "total"])
            inst = {dd: (float(tt), float(tr), float(fo)) for dd, tt, tr, fo in
                    zip(x["date"], pd.to_numeric(x["total"], errors="coerce"), pd.to_numeric(x["trust"], errors="coerce"), pd.to_numeric(x["foreign"], errors="coerce"))}
        fp = os.path.join(XD, "stocks_margin", f"{sid}.csv")
        if os.path.exists(fp):
            x = pd.read_csv(fp, dtype={"date": str}, usecols=["date", "m_balance", "m_limit"])
            marg = {dd: (float(b_), float(l_)) for dd, b_, l_ in zip(x["date"], pd.to_numeric(x["m_balance"], errors="coerce"), pd.to_numeric(x["m_limit"], errors="coerce"))}
    NA = (np.nan, np.nan, np.nan)
    for ds in dates:
        f = {k: np.nan for k in BCOLS}; f["src"] = src
        out[ds] = f
        p = int(cal.searchsorted(pd.Timestamp(ds)))
        if p >= len(cal) or str(cal[p].date()) != ds:
            f["err"] = "date not in cal"; continue
        k = int(np.searchsorted(idx, p))
        if k >= nb or idx[k] != p:
            f["valid"] = 0.0; continue
        f["valid"] = 1.0
        f["amt20"] = float(np.mean(amt[k - 20:k])) if k >= 20 else np.nan
        f["tc_ma120"] = float(c[k - 1] >= np.mean(c[k - 120:k])) if clean(k - 120, k - 1) else np.nan
        f["chk_ma60"] = float(c[k - 1] >= np.mean(c[k - 60:k])) if clean(k - 60, k - 1) else np.nan
        f["chk_r60"] = c[k - 1] / c[k - 61] - 1 if clean(k - 61, k - 1) else np.nan
        f["chk_r20"] = c[k - 1] / c[k - 21] - 1 if clean(k - 21, k - 1) else np.nan
        f["chk_d52"] = c[k - 1] / np.max(c[k - 250:k]) - 1 if clean(k - 250, k - 1) else np.nan
        f["chk_ret1"] = c[k] / c[k - 1] - 1 if k > 0 else np.nan
        f["e1"] = 100 * (c[k] / np.mean(c[k - 59:k + 1]) - 1) if clean(k - 59, k) else np.nan
        f["e2"] = 100 * (c[k] / c[k - 20] - 1) if clean(k - 20, k) else np.nan
        if ds < "2015-01-05":
            continue
        dts = [str(cal[i].date()) for i in idx[max(0, k - 19):k + 1]]
        vv = vol[max(0, k - 19):k + 1]
        if inst is not None and len(dts) == 20:
            tot = np.array([inst.get(d_, NA)[0] for d_ in dts]); tr = np.array([inst.get(d_, NA)[1] for d_ in dts]); fo = np.array([inst.get(d_, NA)[2] for d_ in dts])
            if ds in inst and np.isfinite(tot[-1]) and vv[-1] > 0:
                f["ch_i1"] = tot[-1] / vv[-1]
            for w, key in ((5, "ch_i5"), (20, "ch_i20")):
                tw = tot[-w:]; vw = vv[-w:]
                if np.isfinite(tw).sum() >= (w + 1) // 2 and vw.sum() > 0:
                    f[key] = np.nansum(tw) / vw.sum()
            if np.isfinite(tr).sum() >= 10 and vv.sum() > 0:
                f["ch_t20"] = np.nansum(tr) / vv.sum()
            ft = fo[-5:] + tr[-5:]
            if np.isfinite(ft).sum() >= 3 and vv[-5:].sum() > 0:
                f["d1"] = 100 * np.nansum(ft) / vv[-5:].sum()
        if marg is not None and ds in marg:
            b_, l_ = marg[ds]
            if np.isfinite(l_) and l_ > 0 and np.isfinite(b_):
                f["ch_mu"] = -(b_ / l_)
            if k >= 5:
                d5 = str(cal[idx[k - 5]].date())
                if d5 in marg and np.isfinite(b_) and np.isfinite(marg[d5][0]) and marg[d5][0] > 0:
                    f["d2"] = 100 * (b_ / marg[d5][0] - 1)
    return sid, out


def run_jobs(jobs, procs, tag):
    t0 = time.time(); BR = {}
    with Pool(procs) as pool:
        for j, (sid, out) in enumerate(pool.imap_unordered(uni_job, jobs, chunksize=8)):
            for ds, f in out.items():
                BR[(sid, ds)] = f
            if j % 500 == 0:
                log(f"[逐股 {tag}] {j}/{len(jobs)}｜{time.time() - t0:.0f}s")
    log(f"[逐股 {tag}] 完成 {len(jobs)}｜{time.time() - t0:.0f}s")
    return BR


# ═════════════ 分數 ═════════════
def add_scores(df, key):
    for s in SC["F6"]:
        df["p_" + s] = df.groupby(key)[s].rank(pct=True, method="average").fillna(0.0)
    for nm, subs in SC.items():
        df[nm] = df[["p_" + s for s in subs]].sum(axis=1) / len(subs)
        nn = df[subs].notna().any(axis=1)
        df["can_" + nm] = nn.groupby(df[key]).transform("any")
    df["F6f"] = (df["F1"] + df["F4"] + df["F5"]) / 3; df["can_F6f"] = df["can_F6"]
    for a, b in PAIRS:
        nm = f"{a}+{b}"; df[nm] = (df[a] + df[b]) / 2; df["can_" + nm] = df["can_" + a] | df["can_" + b]
    return df


def pos_in(univ_vals, x):
    """x 在大母體分布中的百分位 0～100：(＜ 的個數 ＋ 0.5×同值個數) ÷ n"""
    u = np.sort(univ_vals[np.isfinite(univ_vals)]); n = len(u)
    out = np.full(len(x), np.nan)
    if n == 0:
        return out
    ok = np.isfinite(x)
    lo = np.searchsorted(u, x[ok], "left"); hi = np.searchsorted(u, x[ok], "right")
    out[ok] = 100 * (lo + 0.5 * (hi - lo)) / n
    return out


def wavg(parts):
    """parts：[(值, 權重)]；缺值 ⇒ 其餘按比例放大；全缺 ⇒ 50"""
    v = np.array([p[0] for p in parts], float).T; w = np.array([p[1] for p in parts], float)
    ok = np.isfinite(v); ws = (ok * w).sum(axis=1)
    s = np.where(ok, v, 0.0) @ w
    return np.where(ws > 0, s / np.where(ws > 0, ws, 1), 50.0)


def f7_scores(T, uni_mask):
    """T：同一事件的大母體 ∪ C+ 列（含 a1..e2、fin_ind）；uni_mask：哪些是大母體 ⇒ 加 F7、F7A..F7E 與細項百分位"""
    T = T.copy()
    m = uni_mask
    T["e2"] = T["e2"] - np.nanmean(T.loc[m, "e2"])          # 近 20 日報酬 − 大母體等權平均（常數，不影響排序）
    P = {}
    for c in ["a1", "a2", "b2", "b3", "c1", "c2", "d1", "d2", "d3", "e1", "e2"]:
        P[c] = pos_in(T.loc[m, c].to_numpy(float), T[c].to_numpy(float))
    P["a3"] = T["a3"].to_numpy(float); P["b1"] = T["b1"].to_numpy(float)
    P["c1"] = 100 - P["c1"]; P["c2"] = 100 - P["c2"]; P["d2"] = 100 - P["d2"]
    for c, v in P.items():
        T["q7_" + c] = v
    A = wavg([(P["a1"], .4), (P["a2"], .4), (P["a3"], .2)])
    Bs = wavg([(P["b1"], .3), (P["b2"], .4), (P["b3"], .3)])
    Cs = wavg([(P["c1"], .6), (P["c2"], .4)])
    Ds = wavg([(P["d1"], 1), (P["d2"], 1), (P["d3"], 1)])
    E = wavg([(P["e1"], .5), (P["e2"], .5)])
    fi = T["fin_ind"].to_numpy(bool)
    tot = np.where(fi, (0.30 * A + 0.25 * Bs + 0.15 * Ds + 0.15 * E) / 0.85, 0.30 * A + 0.25 * Bs + 0.15 * Cs + 0.15 * Ds + 0.15 * E)
    T["F7A"] = A; T["F7B"] = Bs; T["F7C"] = np.where(fi, np.nan, Cs); T["F7D"] = Ds; T["F7E"] = E; T["F7"] = tot
    return T


def order(d, sc):
    d = d.sort_values("sid", kind="mergesort")
    if sc == "F7":
        return d.sort_values(["F7", "F7A"], ascending=[False, False], kind="mergesort")
    return d.sort_values(sc, ascending=False, kind="mergesort")


def stats(x):
    x = np.asarray(x, float)
    if len(x) == 0:
        return {"事件數": 0}
    return {"事件數": len(x), "平均": float(x.mean()), "中位": float(np.median(x)), "勝率": float((x > 0).mean()), "最差": float(x.min()),
            "最好": float(x.max()), "虧＞10%次數": int((x < -0.10).sum())}


def is4(s):
    return bool(re.fullmatch(r"[1-9]\d{3}", str(s)))


def universe_sids(wdata, d0, d1):
    m = pd.read_csv(os.path.join(wdata, "meta", "stocks.csv"), dtype=str).drop_duplicates("stock_id", keep="last")
    m = m[(m["kind"] == "stock") & m["market"].isin(["twse", "tpex"]) & m["stock_id"].map(is4)]
    m = m[(pd.to_datetime(m["first_seen"]) <= pd.Timestamp(d1)) & (pd.to_datetime(m["last_seen"]) >= pd.Timestamp(d0))]
    return dict(zip(m["stock_id"], m["market"]))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=4); a = ap.parse_args()
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    sys.path.insert(0, REPO)
    from backtest import data as D
    from backtest import researchExit5 as EX5
    from backtest import rerun17 as RR
    from backtest import researchAddOn as RA
    WD = {"早年": RA.EOTC, "主": RR.H2D}
    C = pd.read_csv(CROWS, dtype={"sid": str})
    C["dn"] = C["dn"].astype(str).str.lower().eq("true"); C["買得到"] = C["買得到"].astype(str).str.lower().eq("true")
    CP = C[C["yoy"] > 0].copy().reset_index(drop=True)
    evs = sorted(CP["事件日"].unique()); seg_of = CP.drop_duplicates("事件日").set_index("事件日")["段"].to_dict()
    assert len(evs) == 28
    CP["世界"] = ["早年" if seg_of[e] == "2006～2014" else "主" for e in CP["事件日"]]
    log(f"[讀檔] C+ {len(CP)} 列（買不到 {int((~CP['買得到']).sum())}）；事件 {len(evs)}；世界資料 早年 {WD['早年']}、主 {WD['主']}；財報籌碼 {XD}（origin/main {MAINSHA[:10]}）")
    # ── 對照 ──
    V = pd.read_csv(V1ER); V = V[(V["出場"] == "主") & (V["定義"] == "q2")]
    Y = pd.read_csv(YLER); Y = Y[Y["r"].isna() | (Y["r"].astype(str) == "") | (Y["r"].astype(str) == "nan")]
    ref = {}
    for ev in evs:
        wn = "早年" if seg_of[ev] == "2006～2014" else "主"; r = {}
        for cd in ("A", "B"):
            q = V[(V["世界"] == wn) & (V["候選"] == cd) & (V["日期"] == ev)]; q = q[q["進場"].astype(str).str.lower() == "true"]
            r[cd] = float(q["報酬"].iloc[0]) if len(q) else np.nan
        q = Y[(Y["世界"] == wn) & (Y["候選"] == "C+") & (Y["日期"] == ev)]; assert len(q) == 1
        r["C+全買"] = float(q["報酬"].iloc[0])
        mine = float(CP[(CP["事件日"] == ev) & CP["買得到"]]["淨報酬"].mean()); assert abs(mine - r["C+全買"]) < 1e-6
        ref[ev] = r
    log("[對帳] C+ 全買（c_rows 重算）＝ yl event_rows：28/28 差 ＜ 1e-6")
    # ── 營收 ──
    rev_e, rly_e, _ = EX5.load_revenue(WD["早年"]); rev_m, rly_m, _ = EX5.load_revenue(WD["主"])
    rev = rev_m.combine_first(rev_e).sort_index(); rly = rly_m.combine_first(rly_e).sort_index()
    cals = {}
    for wn, wd in WD.items():
        D.DATA = wd; cals[wd] = D.load_calendar()
    _G["cal"] = cals
    AVW = {wn: EX5.avail_pos(list(rev.index), cals[WD[wn]]) for wn in WD}
    AVA = {wn: np.array([AVW[wn][p] for p in rev.index], np.int64) for wn in WD}
    rv3 = []; rvchk = []
    for sid, ev, wn in zip(CP["sid"], CP["事件日"], CP["世界"]):
        cal = cals[WD[wn]]; p = int(cal.searchsorted(pd.Timestamp(ev)))
        E = [e for e in EX5.rev_events(sid, rev, rly, AVW[wn], len(cal)) if e[0] <= p]
        last3 = [e[1] for e in E[-3:]]
        rv3.append(float(np.mean(last3)) if len(last3) == 3 and np.isfinite(last3).all() else np.nan)
        rvchk.append(E[-1][1] if E else np.nan)
    CP["rv_yoy"] = CP["yoy"]; CP["rv_yoy3"] = rv3; CP["rv_hi24"] = CP["hi24"]
    d_ = np.abs(CP["yoy"].to_numpy(float) - np.asarray(rvchk, float)) / np.maximum(1.0, np.abs(CP["yoy"].to_numpy(float))); mxr = float(np.nanmax(d_))
    log(f"[營收] 最近一期年增 自算 vs c_rows（存 6 位有效數字）最大相對差 {mxr:.2e}（{int(np.isnan(d_).sum())} 筆缺）")
    if mxr > 1e-5:
        raise SystemExit("⛔ 營收年增對不上 c_rows")
    # ── 財報 ──
    FIN, finfo = load_fin(); log(f"[財報] {finfo}")
    FF = pd.DataFrame([fin_feats(FIN.get(s), pd.Timestamp(e)) for s, e in zip(CP["sid"], CP["事件日"])])
    for c in FF.columns:
        CP[c] = FF[c].to_numpy()
    # ── 逐股（大母體 ∪ C+）──
    jobs = []; UNIS = {}
    for wn, wd in WD.items():
        ew = [e for e in evs if (seg_of[e] == "2006～2014") == (wn == "早年")]
        us = universe_sids(wd, ew[0], ew[-1]); UNIS[wn] = us
        mk = pd.read_csv(os.path.join(wd, "meta", "stocks.csv"), dtype=str).drop_duplicates("stock_id", keep="last")
        mk = dict(zip(mk["stock_id"], mk["market"]))
        sids = sorted(set(us) | set(CP.loc[CP["世界"] == wn, "sid"]))
        jobs += [(wd, s, mk.get(s, "twse"), ew) for s in sids]
        log(f"[母體 {wn}] 四碼普通股候選 {len(us)}；連同 C+ 共 {len(sids)} 檔 × {len(ew)} 事件")
    BR = run_jobs(jobs, a.procs, "歷史")
    for c in BCOLS[:11]:
        CP[c] = [BR.get((s, e), {}).get(c, np.nan) for s, e in zip(CP["sid"], CP["事件日"])]
    CP["chk_amt20"] = [BR.get((s, e), {}).get("amt20", np.nan) for s, e in zip(CP["sid"], CP["事件日"])]
    chk = {}
    for a_, b_ in (("chk_r60", "ret60p"), ("chk_d52", "d52"), ("chk_ma60", "ma60"), ("chk_r20", "ret20p"), ("chk_ret1", "ret1"), ("chk_amt20", "amt20")):
        x = CP[a_].to_numpy(float); y = CP[b_].to_numpy(float)
        both = np.isfinite(x) & np.isfinite(y)
        rel = np.abs(x[both] - y[both]) / np.maximum(np.abs(y[both]), 1.0)
        chk[b_] = {"兩邊都有": int(both.sum()), "最大相對差": float(rel.max()) if both.any() else None, "相對差＞1e-5": int((rel > 1e-5).sum()),
                   "只有一邊": int((np.isfinite(x) ^ np.isfinite(y)).sum())}
    log(f"[逐股] C+ 線型自算 vs c_rows：{chk}")
    # ── 集保 ──
    TD, tdd = load_tdcc(); log(f"[集保] {len(TD)} 檔；週資料 {len(tdd)} 週（{pd.Timestamp(tdd[0]).date()}～{pd.Timestamp(tdd[-1]).date()}）")
    bg = [tdcc_chg(TD, s, pd.Timestamp(e), 4) for s, e in zip(CP["sid"], CP["事件日"])]
    CP["ch_big"] = [x[0] for x in bg]; CP["tdcc_date"] = [x[1] for x in bg]
    CP["tc_r60"] = CP["ret60p"]; CP["tc_d52"] = CP["d52"]; CP["tc_ma60"] = CP["ma60"]; CP["tc_rs"] = CP["ret20p"]; CP["tc_drop"] = -CP["ret1"]
    # ── F7（大母體）──
    F7ROWS = []; UNIINFO = []
    for ev in evs:
        wn = "早年" if seg_of[ev] == "2006～2014" else "主"; cal = cals[WD[wn]]; p = int(cal.searchsorted(pd.Timestamp(ev))); t = pd.Timestamp(ev)
        cps = set(CP.loc[CP["事件日"] == ev, "sid"])
        rows = []
        for s in sorted(set(UNIS[wn]) | cps):
            b = BR.get((s, ev))
            if b is None:
                continue
            inU = bool(s in UNIS[wn] and b.get("valid") == 1.0 and np.isfinite(b.get("amt20", np.nan)) and b["amt20"] >= 5e7)
            if not inU and s not in cps:
                continue
            r = {"事件日": ev, "sid": s, "inU": inU, "inC": s in cps, "e1": b["e1"], "e2": b["e2"], "d1": b["d1"], "d2": b["d2"]}
            r.update(rev7(s, rev, rly, AVA[wn], p)); r.update(fin7(FIN.get(s), t))
            r["d3"], _ = tdcc_chg(TD, s, t, 1)
            rows.append(r)
        T = pd.DataFrame(rows)
        T = f7_scores(T, T["inU"].to_numpy(bool))
        F7ROWS.append(T[T["inC"]])
        U = T[T["inU"]]
        UNIINFO.append({"事件日": ev, "大母體檔數": int(len(U)), "C+檔數": len(cps), "C+在大母體": int((T["inC"] & T["inU"]).sum()),
                        **{f"大母體缺_{F7SUB[c]}": float(U[c].isna().mean()) for c in F7SUB}})
    F7R = pd.concat(F7ROWS)[["事件日", "sid", "inU"] + list(F7SUB) + ["fin_ind", "f7_fin_q"] + [f"q7_{c}" for c in F7SUB] + ["F7A", "F7B", "F7C", "F7D", "F7E", "F7"]]
    CP = CP.merge(F7R, on=["事件日", "sid"], how="left")
    UI = pd.DataFrame(UNIINFO); UI.to_csv(os.path.join(OUT, "f7_universe.csv"), index=False, float_format="%.4g", encoding="utf-8")
    log("[F7 大母體]\n" + UI[["事件日", "大母體檔數", "C+檔數", "C+在大母體"]].to_string(index=False))
    # ── 缺值 ──
    MS = []
    for sg in SEGS[:3]:
        q = CP[CP["段"] == sg]
        for fam, subs in FAM.items():
            for s in subs:
                MS.append({"段": sg, "分數": "F1～F6", "族": fam, "子項": s, "名稱": SUBNAME[s], "C+列數": len(q), "缺值比例": float(q[s].isna().mean())})
        for c, nm in F7SUB.items():
            MS.append({"段": sg, "分數": "F7", "族": c[0].upper(), "子項": c, "名稱": nm, "C+列數": len(q), "缺值比例": float(q[c].isna().mean())})
        for c in ["F7B", "F7C", "F7D"]:
            MS.append({"段": sg, "分數": "F7", "族": c[-1], "子項": c, "名稱": f"{c} 整個缺給50（C 含金融不算）", "C+列數": len(q),
                       "缺值比例": float(((q[c] == 50.0) | q[c].isna()).mean())})
    MS = pd.DataFrame(MS); MS.to_csv(os.path.join(OUT, "missing.csv"), index=False, float_format="%.4g", encoding="utf-8")
    log("[缺值]\n" + MS.pivot_table(index=["分數", "族", "子項", "名稱"], columns="段", values="缺值比例", sort=False).to_string(float_format=lambda v: f"{v:.2f}"))
    # ── 分數 ──
    CP = add_scores(CP, "事件日"); CP["can_F7"] = True
    EP = []
    for ev in evs:
        d = CP[CP["事件日"] == ev]
        for sc in SCORES:
            can = bool(d["can_" + sc].iloc[0]); o = order(d, sc)
            for N in (1, 2, 3):
                pk = o.head(N); nb = pk[pk["買得到"]]
                ret = float(nb["淨報酬"].mean()) if len(nb) else 0.0
                EP.append({"段": seg_of[ev], "事件日": ev, "分數": sc, "N": N, "可算": can, "C+檔數": len(d), "選中": " ".join(pk["sid"]),
                           "選中分數": " ".join(f"{x:.3f}" for x in pk[sc]), "買到檔數": len(nb), "空手": len(nb) == 0, "報酬": ret,
                           "選中各檔報酬": " ".join(f"{x:.4f}" if b else "買不到" for x, b in zip(pk["淨報酬"], pk["買得到"]))})
    EP = pd.DataFrame(EP)
    # ── 隨機（同 pick）──
    RS = {}
    for i, ev in enumerate(evs):
        d = CP[CP["事件日"] == ev]
        net = np.where(d["買得到"].to_numpy(), d["淨報酬"].to_numpy(float), np.nan); m = len(net)
        for N in (1, 2, 3):
            rng = np.random.default_rng([SEED, i, N])
            ix = np.argsort(rng.random((NR, m)), axis=1)[:, :N]
            v = net[ix]; fin = np.isfinite(v); cnt = fin.sum(axis=1)
            RS[(ev, N)] = np.where(cnt > 0, np.where(fin, v, 0.0).sum(axis=1) / np.maximum(cnt, 1), 0.0)
    if os.path.exists(PICKRND):
        PR = pd.read_csv(PICKRND); mx = 0.0
        for sg in SEGS:
            es = [e for e in evs if sg == "全部" or seg_of[e] == sg]
            for N in (1, 2, 3):
                mx = max(mx, abs(float(np.stack([RS[(e, N)] for e in es]).mean()) - float(PR[(PR["段"] == sg) & (PR["N"] == N)]["平均"].iloc[0])))
        log(f"[對帳] 隨機平均 vs pick/random.csv 最大差 {mx:.2e}（pick 存 6 位有效數字）")
    # ── 彙總 ──
    SUM = []
    for sg in SEGS:
        es_all = [e for e in evs if sg == "全部" or seg_of[e] == sg]
        for cd, nm in (("A", "0050"), ("B", "00631L"), ("C+全買", "C+ 全部等權")):
            x = np.array([ref[e][cd] for e in es_all]); x = x[np.isfinite(x)]
            SUM.append({"段": sg, "方法": cd, "名稱": nm, "N": "", **stats(x)})
        for N in (1, 2, 3):
            M_ = np.stack([RS[(e, N)] for e in es_all]); flat = M_.ravel(); sa = M_.mean(axis=0)
            SUM.append({"段": sg, "方法": "隨機", "名稱": f"C+ 隨機挑 {N} 檔（{NR} 次）", "N": N, "事件數": len(es_all), "平均": float(flat.mean()),
                        "中位": float(np.median(flat)), "勝率": float((flat > 0).mean()), "最差": float(M_.min(axis=0).mean()),
                        "虧＞10%次數": float((M_ < -0.10).sum(axis=0).mean()),
                        "隨機段平均P10": float(np.quantile(sa, .1)), "隨機段平均P50": float(np.quantile(sa, .5)), "隨機段平均P90": float(np.quantile(sa, .9))})
            for sc in SCORES:
                q = EP[(EP["分數"] == sc) & (EP["N"] == N) & (EP["事件日"].isin(es_all)) & EP["可算"]].set_index("事件日")
                es = [e for e in es_all if e in q.index]
                if not es:
                    SUM.append({"段": sg, "方法": sc, "名稱": SCNAME.get(sc, sc), "N": N, "事件數": 0, "備註": "缺（該段沒有資料）"}); continue
                x = q.loc[es, "報酬"].to_numpy(float); s = stats(x)
                segavg = np.stack([RS[(e, N)] for e in es]).mean(axis=0)
                cpa = np.array([ref[e]["C+全買"] for e in es])
                SUM.append({"段": sg, "方法": sc, "名稱": SCNAME.get(sc, sc), "N": N, **s, "空手事件數": int(q.loc[es, "空手"].sum()),
                            "隨機段平均P10": float(np.quantile(segavg, .1)), "隨機段平均P50": float(np.quantile(segavg, .5)), "隨機段平均P90": float(np.quantile(segavg, .9)),
                            "隨機中位置（百分位）": float((segavg < s["平均"]).mean()), "p（隨機≥分數）": float((segavg >= s["平均"]).mean()),
                            "勝過C+全買事件數": int((x > cpa).sum()),
                            "勝過A事件數": int(sum(1 for e, v in zip(es, x) if np.isfinite(ref[e]["A"]) and v > ref[e]["A"])),
                            "備註": ("" if len(es) == len(es_all) else f"只有 {len(es)}/{len(es_all)} 事件可算")})
    SUM = pd.DataFrame(SUM)
    SUM.to_csv(os.path.join(OUT, "summary.csv"), index=False, float_format="%.6g", encoding="utf-8")
    EP.to_csv(os.path.join(OUT, "event_picks.csv"), index=False, float_format="%.6g", encoding="utf-8")
    pd.set_option("display.width", 260); pd.set_option("display.max_rows", 900); pd.set_option("display.max_columns", 40)
    cols = ["段", "方法", "N", "事件數", "平均", "中位", "勝率", "最差", "虧＞10%次數", "隨機中位置（百分位）", "空手事件數"]
    log("[彙總]\n" + SUM[cols].to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    # ── 五分位 ──
    QT = []; QX = []
    for sc in ("F7", "F6"):
        qt, qx = quintiles(CP, evs, seg_of, sc); QT.append(qt); QX += qx
    QT = pd.concat(QT); QT.to_csv(os.path.join(OUT, "quintile.csv"), index=False, float_format="%.6g", encoding="utf-8")
    log("[五分位]\n" + QT.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    log("[單調]\n" + pd.DataFrame(QX).to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    keep = ["段", "事件日", "sid", "買得到", "淨報酬", "fin_q", "fin_src", "tdcc_date", "f7_fin_q", "inU"] + SC["F6"] + list(F7SUB) + \
           ["F7A", "F7B", "F7C", "F7D", "F7E"] + SCORES
    CP[keep].to_csv(os.path.join(OUT, "features.csv"), index=False, float_format="%.6g", encoding="utf-8")
    FW = forward(FIN, TD, a.procs)
    S = {"程式": "backtest/researchMktDrop_fund.py", "時間（台北）": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M"), "讀法": __doc__, "註": NOTES,
         "F7 規則出處": F7LETTER, "F7 情報預期（寄出前寫下）": "F7 在「大跌後」這種情境未必贏隨機——大跌隔天反彈多半來自跌最深、波動大的股，而 F7 的 C、D、E 子項偏向品質與趨勢，可能挑到跌得少、彈得也少的股。",
         "分數": {k: {"名稱": SCNAME.get(k, k), "子項": v} for k, v in SC.items()}, "子項名": SUBNAME, "F7細項": F7SUB, "財報": finfo, "線型對帳": chk,
         "summary": SUM.replace({np.nan: None}).to_dict("records"), "quintile": QT.replace({np.nan: None}).to_dict("records"), "單調": QX,
         "missing": MS.to_dict("records"), "f7_universe": UI.to_dict("records"), "forward_20261015": FW, "耗時秒": round(time.time() - T0, 1)}
    with open(os.path.join(OUT, "MktDrop_fund.json"), "w", encoding="utf-8") as f:
        json.dump(S, f, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    with open(os.path.join(OUT, "run.log"), "w", encoding="utf-8") as f:
        f.write("\n".join(LOG) + "\n")


def quintiles(CP, evs, seg_of, sc):
    def spearmanr(x, y):
        rx = pd.Series(np.asarray(x, float)).rank().to_numpy(); ry = pd.Series(np.asarray(y, float)).rank().to_numpy()
        return type("R", (), {"correlation": float(np.corrcoef(rx, ry)[0, 1])})
    G = {}
    for ev in evs:
        d = order(CP[CP["事件日"] == ev], sc).reset_index(drop=True); n = len(d)
        d["Q"] = 5 - (np.arange(n) * 5 // n)
        b = d[d["買得到"]]
        qm = np.array([b[b["Q"] == q]["淨報酬"].mean() if (b["Q"] == q).any() else np.nan for q in range(1, 6)])
        rho = spearmanr(b[sc], b["淨報酬"]).correlation if len(b) >= 5 else np.nan
        G[ev] = (qm, rho, b.groupby("Q")["淨報酬"].agg(["sum", "count"]).reindex(range(1, 6)).fillna(0).to_numpy())
    rows = []; X = []
    for si, sg in enumerate(SEGS):
        es = [e for e in evs if sg == "全部" or seg_of[e] == sg]
        QM = np.stack([G[e][0] for e in es]); E = len(es)
        rng = np.random.default_rng([QSEED, si, 7 if sc == "F7" else 6]); ix = rng.integers(0, E, (NBOOT, E))
        SCt = np.stack([G[e][2] for e in es])
        for q in range(5):
            v = QM[:, q]; ok = np.isfinite(v)
            bm = np.array([np.nanmean(v[r]) for r in ix])
            rows.append({"分數": sc, "段": sg, "組": f"Q{q + 1}" + ("（高分）" if q == 4 else ("（低分）" if q == 0 else "")), "事件數": int(ok.sum()),
                         "檔次": int(SCt[:, q, 1].sum()), "事件等權平均": float(np.nanmean(v)), "CI95低": float(np.nanpercentile(bm, 2.5)),
                         "CI95高": float(np.nanpercentile(bm, 97.5)), "檔次合併平均": float(SCt[:, q, 0].sum() / max(SCt[:, q, 1].sum(), 1)),
                         "事件組平均＞0比例": float(np.mean(v[ok] > 0))})
        dq = QM[:, 4] - QM[:, 0]; okd = np.isfinite(dq)
        bd = np.array([np.nanmean(dq[r]) for r in ix]); rh = np.array([G[e][1] for e in es], float)
        mq = np.nanmean(QM, axis=0)
        X.append({"分數": sc, "段": sg, "事件數": E, "Q1": mq[0], "Q2": mq[1], "Q3": mq[2], "Q4": mq[3], "Q5": mq[4],
                  "Q5−Q1": float(np.nanmean(dq)), "Q5−Q1 CI95低": float(np.nanpercentile(bd, 2.5)), "Q5−Q1 CI95高": float(np.nanpercentile(bd, 97.5)),
                  "Q5＞Q1 事件比例": float(np.mean(dq[okd] > 0)), "Spearman 事件平均": float(np.nanmean(rh)),
                  "Spearman＞0 事件比例": float(np.mean(rh[np.isfinite(rh)] > 0)), "五組單調遞增": bool(np.all(np.diff(mq) > 0))})
    return pd.DataFrame(rows), X


def forward(FIN, TD, procs):
    from backtest import data as D
    from backtest import researchExit5 as EX5
    D.DATA = FDATA
    cal = D.load_calendar(); n0 = len(cal); TP = n0 - 1
    assert str(cal[-1].date()) == "2026-10-15", cal[-1]
    _G["cal"] = {FDATA: cal}
    F = pd.read_csv(FWD, dtype={"代號": str}, encoding="utf-8-sig"); F = F[F["候選"] == "C+"].reset_index(drop=True)
    mk = pd.read_csv(os.path.join(FDATA, "meta", "stocks.csv"), dtype=str).drop_duplicates("stock_id", keep="last").set_index("stock_id")["market"].to_dict()
    rev, rly, _ = EX5.load_revenue(FDATA); AV = EX5.avail_pos(list(rev.index), cal); AVA = np.array([AV[p] for p in rev.index], np.int64)
    t = pd.Timestamp("2026-10-15"); ds = "2026-10-15"
    us = universe_sids(FDATA, ds, ds)
    sids = sorted(set(us) | set(F["代號"]))
    BR = run_jobs([(FDATA, s, mk.get(s, "twse"), [ds]) for s in sids], procs, "10/15")
    rows = []
    for sid, nm, r1, yoy in zip(F["代號"], F["名稱"], F["當日報酬"], F["年增"]):
        f = {"sid": sid, "名稱": nm, "事件日": ds, "ret1": float(r1), "rv_yoy": float(yoy)}
        E = [e for e in EX5.rev_events(sid, rev, rly, AV, n0) if e[0] <= TP]
        last3 = [e[1] for e in E[-3:]]
        f["rv_yoy3"] = float(np.mean(last3)) if len(last3) == 3 and np.isfinite(last3).all() else np.nan
        f["rv_hi24"] = (np.nan if (not E or E[-1][2] is None) else float(E[-1][2])); f["yoy_chk"] = E[-1][1] if E else np.nan
        f.update(fin_feats(FIN.get(sid), t))
        b = BR[(sid, ds)]
        for k in ("tc_ma120", "ch_i1", "ch_i5", "ch_i20", "ch_t20", "ch_mu"):
            f[k] = b[k]
        f["tc_r60"] = b["chk_r60"]; f["tc_rs"] = b["chk_r20"]; f["tc_ma60"] = b["chk_ma60"]; f["tc_d52"] = b["chk_d52"]; f["tc_drop"] = -float(r1)
        f["ret1_chk"] = b["chk_ret1"]
        f["ch_big"], f["tdcc_date"] = tdcc_chg(TD, sid, t, 4)
        rows.append(f)
    d = pd.DataFrame(rows)
    log(f"[10/15] C+ {len(d)} 檔；年增對 csv 最大差 {float(np.nanmax(np.abs(d['rv_yoy'] - d['yoy_chk']))):.2e}；當日報酬對 csv 最大差 {float(np.nanmax(np.abs(d['ret1'] - d['ret1_chk']))):.2e}")
    log("[10/15 F6 缺值比例] " + ", ".join(f"{s} {d[s].isna().mean():.2f}" for s in SC["F6"]))
    d = add_scores(d, "事件日")
    # F7
    cps = set(d["sid"]); rr = []
    for s in sids:
        b = BR.get((s, ds))
        inU = bool(s in us and b.get("valid") == 1.0 and np.isfinite(b.get("amt20", np.nan)) and b["amt20"] >= 5e7)
        if not inU and s not in cps:
            continue
        r = {"事件日": ds, "sid": s, "inU": inU, "inC": s in cps, "e1": b["e1"], "e2": b["e2"], "d1": b["d1"], "d2": b["d2"]}
        r.update(rev7(s, rev, rly, AVA, TP)); r.update(fin7(FIN.get(s), t)); r["d3"], _ = tdcc_chg(TD, s, t, 1)
        rr.append(r)
    T = pd.DataFrame(rr); T = f7_scores(T, T["inU"].to_numpy(bool))
    log(f"[10/15 F7] 大母體 {int(T['inU'].sum())} 檔；C+ 在大母體 {int((T['inU'] & T['inC']).sum())}/{len(cps)}；大母體缺：" +
        ", ".join(f"{F7SUB[c]} {T.loc[T['inU'], c].isna().mean():.2f}" for c in F7SUB))
    d = d.merge(T[T["inC"]][["sid", "inU"] + list(F7SUB) + ["fin_ind", "f7_fin_q", "F7A", "F7B", "F7C", "F7D", "F7E", "F7"]], on="sid", how="left")
    d.to_csv(os.path.join(OUT, "forward_20261015_features.csv"), index=False, float_format="%.6g", encoding="utf-8")
    L = []
    for sc in SCORES:
        o = order(d, sc)
        for j, (_, r) in enumerate(o.head(3).iterrows()):
            row = {"分數": sc, "分數名": SCNAME.get(sc, sc), "名次": j + 1, "代號": r["sid"], "名稱": r["名稱"], "總分": r[sc], "F7": r["F7"], "F6": r["F6"],
                   "F7A營收": r["F7A"], "F7B獲利": r["F7B"], "F7C品質": r["F7C"], "F7D籌碼": r["F7D"], "F7E線型": r["F7E"],
                   "F1基本面": r["F1"], "F4籌碼": r["F4"], "F5線型": r["F5"], "當日報酬": r["ret1"], "財報季": r["fin_q"] or "缺", "在F7大母體": r["inU"]}
            for s in SC["F6"] + list(F7SUB):
                row[s] = r[s] if pd.notna(r[s]) else "缺"
            L.append(row)
    L = pd.DataFrame(L)
    L.to_csv(os.path.join(OUT, "forward_20261015.csv"), index=False, float_format="%.6g", encoding="utf-8")
    show = L[L["分數"].isin(["F7", "F6", "F1", "F2", "F3", "F4", "F5", "F6f"])][["分數", "名次", "代號", "名稱", "總分", "F7A營收", "F7B獲利", "F7C品質", "F7D籌碼", "F7E線型",
                                                                            "F1基本面", "F4籌碼", "F5線型", "當日報酬", "財報季", "在F7大母體"]]
    log("[10/15 前 3]\n" + show.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    for sc in ("F7", "F6"):
        t5 = order(d, sc).head(8)[["sid", "名稱", sc] + (["F7A", "F7B", "F7C", "F7D", "F7E"] + list(F7SUB) if sc == "F7" else SC["F6"])]
        log(f"[10/15 {sc} 前 8 子項]\n" + t5.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    return {"表": L.replace({np.nan: None}).to_dict("records"), "F6缺值比例": {s: float(d[s].isna().mean()) for s in SC["F6"]},
            "F7細項缺值比例（C+）": {F7SUB[c]: float(d[c].isna().mean()) for c in F7SUB}}


if __name__ == "__main__":
    main()
