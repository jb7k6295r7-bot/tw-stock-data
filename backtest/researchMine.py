# -*- coding: utf-8 -*-
"""PREREG地雷股濾網 seq3（台股策略線登錄 sha d38143d4aa992c6e，2026-10-07 01:49；裁定 seq310 發號 N_單筆 ＋3、seq311 丙呈現、seq313／314 核准 seq3）。回測線（子代理執行）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMine body [--procs 3]   # 旗、甲、乙、丙
    ...                                                                       ding [--procs 3] [--reps 200]   # 丁（營量 v1／營飆 v1 前面加濾網，描述）
    ...                                                                       page                            # 網頁
    抽樣查核：... -m backtest.researchMine --check（⛔ 不呼叫本體的旗、報酬、分類函式；從原始 CSV 自算）

⭐ 讀法寫死時間：2026-10-07 02:10（台北）；寫死前 ⛔ 沒看任何本件的旗、報酬、下市、飆股數字（只看過資料欄位、檔案格式、上櫃 note 字元種類、各年下市筆數）。
   使用者原話：「濾掉地雷股，長期股價下探的、很有可能會下市的公司…看看會有多少飆股被濾掉！？」

═══ 資料 ═══
  主快照：tw-stock-data origin/main 796d94c9da（git archive 到 ~/h2data/mine_796d94c9dafd/data，唯讀）：stocks、adj、meta（delisted、otc_delist_reason、par_timeline、
          filing_dates、disposal、stocks.csv、calendar）、mops/fin_hist、mops/bs_hist、universe/fulldelivery、chtm、marginratio、otcmargin；日曆 2015-01-05～2026-10-06
  早年：早年版面 ~/earlydata/3edc0e2206/main/data（只上市；2004-02-11～2014-12-31）
  W1 eligible：主 ＝ backtest/resultsp9_engine/panel_ext.csv.gz（edc6f 快照建的面板，量測月到 2026-08）的 eligible；
               早年 ＝ ~/earlydata/3edc0e2206/sig_main/panel.csv.gz 的 liq_ok ∧ bars_ok（2012-06 以前沒有個股法人 ⇒ 同 researchVolBreak／researchMomX R10）
  母體閘：UG.set_gate_v2(True)；gate3（含已下市，⛔ 不剔）∩ 該月 W1 eligible ∩ 判定日 pit_valid
  飆股名單：~/s5work/events.npz（飆股回推 seq5 build：早年 950ad26e12 接 main b53f5540a8，全日曆 2004-02-11～2026-09-24 連續鏈；seq6 演算法＝seq5 只改期間）
  丁：營量 v1（#13）、營飆 v1（#1）＝ researchT1fix 的 t1 版（T1 開、停止交易強制出場開；edc6f 快照，原件路徑）

═══ 讀法（X 標；⭐ 看數字前寫死；登錄沒寫清楚的執行者補讀法都在這裡）═══
 X1 判定日 m ＝ 各曆月最後一個交易日（主日曆最後一個月 2026-10 未完 ⇒ 不算）；旗只用 m 收盤（含）以前可得資料
 X2 有效 K 棒序列（收盤有值的日子）上算：F1 的「250 日前收盤」＝ m 當下最後一根有效 K 棒往前第 250 根；「250 日均線」＝ 最後 250 根有效 K 棒還原收盤平均；需 ≥ 251 根
    F1(d)：還原收盤 ≤ 250 根前還原收盤 ×（1 − d）且 還原收盤 ＜ 250 日均線；d ∈ {50%, 70%}
 X3 F2(p)：最後一根有效 K 棒的【原始】收盤 ＜ 面額 × p；面額 ＝ par_timeline（valid_from ≤ m ＜ valid_to，空白＝不限）；表上沒有或空白 ⇒ 假設 10 元並列清單（§七之三）
 X4 F3：最近已公布季報的官方「每股參考淨值」（bs_hist；2015Q1 起）＜ 面額／2（寬）或 ＜ 0（窄）；季報可用日（§一）＝ filing_dates 有時戳 ⇒ 上傳日之後第一個交易日；
    否則法定期限（Q1 5/15、Q2 8/14、Q3 11/14、Q4 次年 3/31）之後第一個交易日再往後 5 個交易日（researchQual B2 同式）；可用 ⇔ 可用日位置 ≤ m
    「最近已公布」＝ m 時已可用的季中期別最新者；該季淨值空白 ⇒ F3 不可判（當作沒旗）
 X5 F4：單季 EPS ＝ fin_hist eps_ytd 本期 − 前期（Q1 不減；eps_ytd 空 ⇒ 用 eps_q）；以 m 時已可用的最新一季為「最近一季」：
    F4a ＝ 最近連續 4 季都有值、合計 ＜ 0 且最近一季 ＜ 0｜F4b ＝ 最近連續 8 季都有值、≥ 6 季 ＜ 0｜F4 ＝ F4a ∨ F4b（「2 種」各報，G 用聯集）
 X6 F5a 全額交割／變更交易／管理股票：上市 fulldelivery 有列、上櫃 chtm changed＝1 或 managed＝1；F5b 懲罰型停資停券：上市 marginratio reason ∈
    {股價波動過度劇烈、成交量過度異常、股權過度集中、監視第二次處置}（⚠ 檔內另有「TDR兌回異常」「監視業務督導會報決議處置增加調整成數」⇒ 登錄沒列、⛔ 不算）；
    上櫃 otcmargin note 含 A、B、C 或 D 任一字元（⛔ O／X／@／*／! 不算）
    可用（§七之二、裁定 seq310）：快照日 d 的狀態在 d 的次一交易日起可用 ⇒ m 判定看「d ＜ m 的最後一份快照」（＝ m−1 那份）；F5c 停（b3 不做）
    F5 只主快照（2015-01-05 起）可判；早年 ⛔ 不判
 X7 組合旗（§一「各取較寬格」）：G1 ＝ F1(50%) ∨ F2(p＝1) ∨ F3(＜面額／2) ∨ F4 ∨ F5｜G2 ＝ 上列五項中 ≥ 2 項｜G3 ＝ F3(＜面額／2) ∨ F5（G3 也取較寬格；窄版 F3(＜0) ∨ F5 只描述）
    不可判的單旗當「沒旗」（濾網拿不到資料就濾不到；可判率逐年照報）
    早年（2005～2014）：F3 淨值 bs_hist 2015Q1 起 ⇒ 早年 0 季可判；F4 fin_hist 2013Q1 起 ⇒ 只有 2014-04 以後零星可判；F5 2015 起
    ⇒ 早年 G1／G2 只用 F1、F2（⭐ 執行者補：F4 早年只有末 9 個月可判，為了整段同一個定義不放；照實標）；早年 G3（只用 F3）⇒ 0 季可判 ⇒「早年 G3 不可判」
 X8 乙：事件 ＝ (股, m)：m 在段內、該股在 m 的母體內、帶 G 旗；報酬 R_H ＝ 還原收盤[m＋H] ÷ 還原開盤[m＋1] − 1（持有 H 根＝D.exit_pos(m＋1, H)＝m＋H；收盤 ffill ⇒
    下市後沿用最後有成交日收盤，含歸零那種收盤）；m＋1 開盤無效（停牌、已下市）⇒ 該列不進（筆數照報）；m＋H ≤ 段尾（同 researchVolBreak 單筆層）
    基準②：同一個 m、母體內（不論有沒有旗）r20（還原收盤[m] ÷ 還原收盤[m−20] − 1）同十分位者 R_H 的等權平均（researchPatAll decile_int 同式；同日 ＜ 20 檔 ⇒ 不算）
    X ＝ R_H − 基準②；月分群 95% CI：一個 m 就是一群（每月只有一個判定日）；群穩健 SE（CR1：G／(G−1)·Σ_g(Σ_i(x_i−x̄))²／n²）；點估計 ＝ 事件等權平均
    ⚠ H ≥ 60 時相鄰月持有期重疊 ⇒ 月分群 CI 偏窄（表頭標）
    「該躲」（登錄 §二乙）＝ 探索、確認兩段 CI 上緣都 ＜ 0；每個 G 4 個 H 中 ≥ 3 格該躲 ⇒ 該 G「該躲」成立（N_單筆 ＋1／G）
    另報（描述）：無旗母體的 X、帶旗 − 無旗；「含歸零」對照：事件 m 之後到 m＋H 之間財務性下市（主代理）者 R 代 −100%
 X9 甲：單位 ＝ 母體內股-月 (股, m)；結果 ＝ m 之後 12／24／36 個月內（(m, m＋k 月]）財務性下市；只用 m＋k 月 ≤ 2026-10-06（資料尾）的列
    下市清單 delisted.csv（上市 264、上櫃 240；轉上市不算）；原因（§七之一）：上櫃 otc_delist_reason：被合併、金控 ⇒ 非地雷（⭐ 金控＝股份轉換成金控子公司，執行者補）；
    拒絕往來、管理股票 ⇒ 財務性；其他、取消第二類股 ⇒ 代理（⭐「取消第二類股」登錄沒列，執行者補照代理）；上市 ⇒ 全部代理
    主代理（seq1 原文）：最後一根有效 K 棒還原收盤 ÷ 往前第 60 根有效 K 棒還原收盤 − 1 ＜ −50%（⭐「下市前 60 日」讀成下市前最後 60 根有效 K 棒，停牌很久才下市的也看得到停牌前那段跌幅）
             或 下市日時已可用的最新每股參考淨值 ＜ 0 ⇒ 財務性
    並報代理（資料庫建議）：下市日前 250 個交易日內（日曆位置 [D−250, D)）曾進 F5a、F5b 或處置（disposal 普通股、[start, end] 與窗重疊）⇒ 財務性
    ⚠ 早年下市（2015 以前）：淨值、F5 都沒有 ⇒ 主代理只看跌幅、並報代理只看處置（2010-12 起），照實標
    報：帶旗股-月 k 月內財務性下市比例（精準度）vs 無旗、倍數；召回 ＝ 段內財務性下市股中，下市前 12 個月內（月底判定日 ∈ [D−12 月, D)）至少一次帶旗的比例
       （⭐ 不要求那時在 W1 母體內：旗是股票的狀態；另報「下市前 12 個月內曾在母體」的檔數）；提前多久 ＝ 下市前 36 個月內第一次帶旗到下市的月數中位
       另報「有旗股之後 12 個月內被列處置的比例」vs 無旗（處置以 announce_date，普通股）
 X10 丙：飆股（§六）＝ s5 名單的網格事件（cell、起漲日 t）；⭐ seq6 U4b 右截斷：t＋H ≤ 2026-08-31 的事件才算；段依 t 的月份；鏈沿用 s5 全日曆連續鏈
    「起漲前一日帶旗」＝ t 之前（嚴格 ＜ t 的日期）最後一個月底判定日 m 的旗（＝ 起漲前一日當時正在生效的濾網狀態）；m ≤ 2014-12-31 用早年版面（只上市 ⇒ 早年上櫃事件無旗可查、不進分母，筆數照報）
    誤殺率（每格）＝ 該格事件中帶旗的比例；主表 ＝ s5 名單全部事件（飆股名單沿用，⛔ 不套 W1 閘）；另報「只算 m 時在 W1 母體內的事件」
    ⭐ 呈現（裁定 seq311）：第一個數 ＝ 探索＋確認（2017-03～2026-08）全網格各格誤殺率的中位（附 p10～p90；各格 ≥ 1 事件才算進去，另報 ≥ 30 事件的版本）；
       H120／g100% 那格並列、標「登錄主格」；⛔ 給使用者的文字不寫「N 天漲一倍」
    「帶旗股票之後變飆股的機率」⭐ 執行者補：單位 ＝ s5 名單內股-月 (股, m)（m 當天有 K 棒），結果 ＝ 到下一個判定日之間 (m, m_next] 有該格起漲日；
       定義域：s5 hdef[m＋1] ≥ H 且 m＋1＋H ≤ 2026-08-31；報帶旗 vs 無旗的比例與倍數（主格＋全網格倍數中位）
    「被濾掉的飆股之後的最大漲幅」＝ 事件 M250（s5：起漲後 250 日內最高收盤 ÷ t 收盤 − 1）帶旗 vs 無旗的分佈
 X11 必附一句（§二丙）：「這個濾網躲掉 x 檔下市、y% 的大跌，代價是誤殺 z% 的飆股」⭐ 執行者補：
     x ＝ 2017-03～2026-08 財務性下市（主代理）股中，下市前 12 個月內帶旗的檔數（附分母）；y ＝ 2017-03～2025-08 母體股-月中「之後 250 根報酬 ≤ −50%（含下市）」者帶旗的比例；
     z ＝ X10 的網格中位
 X12 丁（描述，⛔ 不判、不改正式規則）：researchT1fix t1 版 c13（營量 v1）、c1（營飆 v1），原件 kw ＋ stop_force；選股日 t ＝ entry_pos − 1，t 當時生效的旗 ＝ 最後一個 ≤ t 的判定日 m；
     帶 G1／G3 ⇒ 該筆用 weight_fn 回 0（引擎記 nocap、⛔ 不遞補，名額持現金）；其餘回 equity[t−1]／N（＝ 原件 slot）
     閘門：不濾版（weight_fn 全回 slot）必須與 resultsT1fix seeds.csv.gz 的 t1 列逐位元相同（cagr、mdd、eq_sha）
     200 顆（營量 7000＋r、營飆 1000＋r）；報主窗年化中位、回落中位、探索／確認年化中位、被濾掉的筆數（每顆平均）與那些筆的毛報酬 − 0.585%
 X13 sha：登錄全文去掉含「pw1 line」那一行後 sha256 前 16 碼 ＝ d38143d4aa992c6e 才跑
輸出 backtest/resultsMine/（summary.json、yi.csv、jia.csv、bing_cells.csv、bing_grid.csv、ding.csv、flag_rate.csv、check.json、地雷股濾網.html）；逐筆大檔 ~/minework/
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
import os
import re
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import universe_gate as UG

TAGT = "2026-10-07 02:10（台北）"
REG_SHA = "d38143d4aa992c6e"
MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
MAIN_SHA = "796d94c9dafd8f3860ef241b915a2df17de8c5be"
MAIN = os.path.expanduser("~/h2data/mine_796d94c9dafd/data")
EARLY = os.path.expanduser("~/earlydata/3edc0e2206/main/data")
PANEL = os.path.expanduser("~/tw-p17/backtest/resultsp9_engine/panel_ext.csv.gz")
EARLY_PANEL = os.path.expanduser("~/earlydata/3edc0e2206/sig_main/panel.csv.gz")
S5W = os.path.expanduser("~/s5work")
WORK = os.path.expanduser("~/minework")
OUT = os.path.expanduser("~/tw-p17/backtest/resultsMine")
SEG = {"早年": ("2005-02", "2014-12"), "探索": ("2017-03", "2021-12"), "確認": ("2022-01", "2026-08")}
POOL_SEG = ("2017-03", "2026-08")
HY = (20, 60, 120, 250)
COST = 0.00585
CUT = "2026-08-31"
F5B_REASONS = {"股價波動過度劇烈", "成交量過度異常", "股權過度集中", "監視第二次處置"}
FLAGS = ["F1_50", "F1_70", "F2_1", "F2_05", "F3_half", "F3_neg", "F4a", "F4b", "F4", "F5a", "F5b", "F5", "G1", "G2", "G3", "G3n"]
FNAME = {"F1_50": "F1 長期下探（跌 50%）", "F1_70": "F1 長期下探（跌 70%）", "F2_1": "F2 低於面額", "F2_05": "F2 低於半個面額", "F3_half": "F3 淨值 ＜ 面額／2",
         "F3_neg": "F3 淨值 ＜ 0", "F4a": "F4 近 4 季合計虧且最近一季虧", "F4b": "F4 近 8 季 ≥ 6 季虧", "F4": "F4 連續虧損（兩種任一）", "F5a": "F5 全額交割／變更交易／管理股票",
         "F5b": "F5 懲罰型停資停券", "F5": "F5 官方警示（任一）", "G1": "G1 任一旗", "G2": "G2 兩旗以上", "G3": "G3 淨值偏低或官方警示", "G3n": "G3 窄版（淨值 ＜ 0 或官方警示）"}
EARLY_NA = {"F3_half", "F3_neg", "F4a", "F4b", "F4", "F5a", "F5b", "F5", "G3", "G3n"}
HS5 = tuple(range(10, 251, 10))                                     # 飆股回推 seq5／seq6 網格（researchSurge5.HS、GS 同值；check 對）
GS5 = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.0, 10.0)
NC5 = len(HS5) * len(GS5)
_G: dict = {}


def cell_name(c):
    return f"H{HS5[c // len(GS5)]}_g{int(round(GS5[c % len(GS5)] * 100))}%"


def log_to(path):
    f = open(path, "a", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); f.write(m + "\n"); f.flush()
    return log


# ═════════════ sha 閘 ═════════════
def reg_sha(path):
    data = open(path, "rb").read()
    keep = [ln if ln.endswith(b"\n") else ln + b"\n" for ln in data.splitlines(keepends=True) if b"pw1 line" not in ln]
    return hashlib.sha256(b"".join(keep)).hexdigest()[:16]


def sha_gate():
    fs = [f for f in glob.glob(os.path.join(MAILBOX, "**", "*.md"), recursive=True)
          if os.path.basename(f).startswith("登錄全文-地雷股濾網") and "_seq3_" in os.path.basename(f)]
    hit = [(os.path.basename(f), reg_sha(f)) for f in fs]
    if not any(s == REG_SHA for _, s in hit):
        sys.exit(f"⛔ 找不到 sha＝{REG_SHA} 的 seq3 登錄全文：{hit}")
    return hit


# ═════════════ 小工具 ═════════════
def month_ends(cal, complete_last):
    m = np.array([c.year * 12 + c.month for c in cal])
    idx = list(np.flatnonzero(m[:-1] != m[1:]))
    if complete_last:
        idx.append(len(cal) - 1)
    return np.array(idx, int)


def decile_int(x):
    rk = pd.Series(x).rank(method="first").to_numpy(); mm = len(x)
    return ((10 * (rk - 1))[:, None] > (np.arange(1, 10) * (mm - 1))[None, :]).sum(axis=1)


def cr1(x, g):
    """事件等權平均與月分群 CR1 SE。"""
    x = np.asarray(x, float); n = len(x)
    if n == 0:
        return np.nan, np.nan, 0
    mu = float(x.mean())
    s = pd.Series(x - mu).groupby(np.asarray(g)).sum().to_numpy()
    G = len(s)
    if G < 2:
        return mu, np.nan, G
    v = G / (G - 1) * float((s ** 2).sum()) / n ** 2
    return mu, math.sqrt(v), G


def par_lookup(par_df):
    P = {}
    for r in par_df.itertuples():
        P.setdefault(r.stock_id, []).append((pd.Timestamp(r.valid_from) if isinstance(r.valid_from, str) else None,
                                             pd.Timestamp(r.valid_to) if isinstance(r.valid_to, str) else None,
                                             float(r.par) if isinstance(r.par, str) and r.par.strip() else np.nan))
    return P


def par_at(P, sid, dates):
    """回 (面額陣列, 是否假設 10 元)。"""
    rows = P.get(sid)
    out = np.full(len(dates), np.nan)
    if rows:
        for vf, vt, p in rows:
            m = np.ones(len(dates), bool)
            if vf is not None:
                m &= dates >= vf
            if vt is not None:
                m &= dates < vt
            out[m] = p
    assumed = ~np.isfinite(out)
    out[assumed] = 10.0
    return out, assumed


# ═════════════ 財報 ═════════════
def avail_positions(sids, ys, qs, fd, cal):
    dl = {1: (5, 15), 2: (8, 14), 3: (11, 14)}
    out = np.empty(len(sids), int); src = []
    for i, (s, y, q) in enumerate(zip(sids, ys, qs)):
        ts = fd.get((s, int(y), int(q)))
        if ts is not None:
            out[i] = int(cal.searchsorted(ts, side="right")); src.append("ts")
        else:
            d = pd.Timestamp(int(y) + 1, 3, 31) if q == 4 else pd.Timestamp(int(y), *dl[int(q)])
            out[i] = int(cal.searchsorted(d, side="right")) + 5; src.append("dl")
    return out, np.array(src)


def load_fin(cal, log):
    fd = pd.read_csv(os.path.join(MAIN, "meta", "filing_dates.csv"), dtype=str)
    fd["d"] = pd.to_datetime(fd["uploaded_at"].astype(str).str[:10], errors="coerce")
    fd = fd.dropna(subset=["d"]); fd["year"] = fd["year"].astype(int); fd["season"] = fd["season"].astype(int)
    fdd = fd.groupby(["stock_id", "year", "season"])["d"].min().to_dict()
    # 淨值
    bs = []
    for f in sorted(glob.glob(os.path.join(MAIN, "mops", "bs_hist", "*.csv"))):
        x = pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "每股參考淨值"])
        bs.append(x)
    B = pd.concat(bs, ignore_index=True)
    B["bv"] = pd.to_numeric(B["每股參考淨值"], errors="coerce")
    B = B.drop_duplicates(["stock_id", "period"], keep="last")
    B["y"] = B["period"].str[:4].astype(int); B["q"] = B["period"].str[-1].astype(int)
    B["ap"], B["src"] = avail_positions(B["stock_id"].tolist(), B["y"].tolist(), B["q"].tolist(), fdd, cal)
    # EPS
    fs = []
    for f in sorted(glob.glob(os.path.join(MAIN, "mops", "fin_hist", "*.csv"))):
        fs.append(pd.read_csv(f, dtype={"stock_id": str, "period": str}, usecols=["stock_id", "period", "eps_q", "eps_ytd"]))
    F = pd.concat(fs, ignore_index=True).drop_duplicates(["stock_id", "period"], keep="last")
    F["y"] = F["period"].str[:4].astype(int); F["q"] = F["period"].str[-1].astype(int)
    F["eps_ytd"] = pd.to_numeric(F["eps_ytd"], errors="coerce"); F["eps_q"] = pd.to_numeric(F["eps_q"], errors="coerce")
    K = {(s, y, q): v for s, y, q, v in zip(F["stock_id"], F["y"], F["q"], F["eps_ytd"])}
    single = []
    for s, y, q, v, vq in zip(F["stock_id"], F["y"], F["q"], F["eps_ytd"], F["eps_q"]):
        if q == 1:
            e = v
        else:
            pv = K.get((s, y, q - 1), np.nan)
            e = v - pv if (np.isfinite(v) and np.isfinite(pv)) else np.nan
        if not np.isfinite(e) and np.isfinite(vq):
            e = vq
        single.append(e)
    F["eps"] = single
    F["ap"], F["src"] = avail_positions(F["stock_id"].tolist(), F["y"].tolist(), F["q"].tolist(), fdd, cal)
    log(f"[財報] bs_hist {len(B):,} 季列（時戳 {(B['src'] == 'ts').mean():.1%}）｜fin_hist {len(F):,} 季列（時戳 {(F['src'] == 'ts').mean():.1%}）｜"
        f"filing_dates 年份 {sorted(fd['year'].unique().tolist())}")
    return B, F


def fin_flags_stock(sid, B_s, F_s, me, par_me):
    """回 F3_half、F3_neg、F3_ok、F4a、F4b、F4_ok（各長 len(me)）。"""
    nm = len(me)
    out = {k: np.zeros(nm, bool) for k in ("F3_half", "F3_neg", "F3_ok", "F4a", "F4b", "F4_ok")}
    out["bv"] = np.full(nm, np.nan)
    if B_s is not None and len(B_s):
        o = (B_s["y"] * 4 + B_s["q"] - 1).to_numpy(); ap = B_s["ap"].to_numpy(); bv = B_s["bv"].to_numpy(float)
        srt = np.argsort(ap, kind="stable"); ap_s = ap[srt]; o_s = o[srt]
        runmax = np.maximum.accumulate(o_s)
        k = np.searchsorted(ap_s, me, side="right") - 1
        val = {oo: v for oo, v in zip(o, bv)}
        for i in np.flatnonzero(k >= 0):
            v = val[int(runmax[k[i]])]
            if np.isfinite(v):
                out["F3_ok"][i] = True; out["bv"][i] = v
                out["F3_half"][i] = v < par_me[i] / 2; out["F3_neg"][i] = v < 0
    if F_s is not None and len(F_s):
        o = (F_s["y"] * 4 + F_s["q"] - 1).to_numpy(); ap = F_s["ap"].to_numpy(); ep = F_s["eps"].to_numpy(float)
        srt = np.argsort(ap, kind="stable"); ap_s = ap[srt]; o_s = o[srt]
        runmax = np.maximum.accumulate(o_s)
        k = np.searchsorted(ap_s, me, side="right") - 1
        val = {oo: v for oo, v in zip(o, ep)}
        for i in np.flatnonzero(k >= 0):
            top = int(runmax[k[i]])
            e8 = np.array([val.get(top - j, np.nan) for j in range(8)])
            a_ok = np.isfinite(e8[:4]).all(); b_ok = np.isfinite(e8).all()
            if a_ok or b_ok:
                out["F4_ok"][i] = True
            if a_ok:
                out["F4a"][i] = (e8[:4].sum() < 0) and (e8[0] < 0)
            if b_ok:
                out["F4b"][i] = int((e8 < 0).sum()) >= 6
    return out


# ═════════════ 官方警示快照 ═════════════
def load_warn(cal, log):
    """回 {kind: {日曆位置: set(sid)}}（kind＝a、b），以及快照日位置清單。"""
    pos = {d: i for i, d in enumerate(cal.strftime("%Y-%m-%d"))}
    A = {}; Bm = {}; days = set()
    for f in sorted(glob.glob(os.path.join(MAIN, "universe", "fulldelivery", "*.csv"))):
        d = os.path.basename(f)[:10]; p = pos.get(d)
        if p is None:
            continue
        x = pd.read_csv(f, dtype=str); A.setdefault(p, set()).update(x["stock_id"].str.strip()); days.add(p)
    for f in sorted(glob.glob(os.path.join(MAIN, "universe", "chtm", "*.csv"))):
        d = os.path.basename(f)[:10]; p = pos.get(d)
        if p is None:
            continue
        x = pd.read_csv(f, dtype=str)
        m = (x["changed"].fillna("").str.strip() == "1") | (x["managed"].fillna("").str.strip() == "1")
        A.setdefault(p, set()).update(x.loc[m, "stock_id"].str.strip()); days.add(p)
    for f in sorted(glob.glob(os.path.join(MAIN, "universe", "marginratio", "*.csv"))):
        d = os.path.basename(f)[:10]; p = pos.get(d)
        if p is None:
            continue
        x = pd.read_csv(f, dtype=str)
        Bm.setdefault(p, set()).update(x.loc[x["reason"].isin(F5B_REASONS), "stock_id"].str.strip()); days.add(p)
    rx = re.compile(r"[ABCD]")
    for f in sorted(glob.glob(os.path.join(MAIN, "universe", "otcmargin", "*.csv"))):
        d = os.path.basename(f)[:10]; p = pos.get(d)
        if p is None:
            continue
        x = pd.read_csv(f, dtype=str)
        m = x["note"].fillna("").map(lambda s: bool(rx.search(s)))
        Bm.setdefault(p, set()).update(x.loc[m, "stock_id"].str.strip()); days.add(p)
    days = np.array(sorted(days), int)
    log(f"[F5] 快照日 {len(days)}（{cal[days[0]].date()}～{cal[days[-1]].date()}）｜F5a 日均 {np.mean([len(A.get(p, ())) for p in days]):.1f} 檔｜F5b 日均 {np.mean([len(Bm.get(p, ())) for p in days]):.1f} 檔")
    return A, Bm, days


def load_disposal(data):
    d = pd.read_csv(os.path.join(data, "meta", "disposal.csv"), dtype=str)
    d = d[d["sec_kind"] == "普通股"]
    out = {}
    for s, a, b, an in zip(d["stock_id"], d["start_date"], d["end_date"], d["announce_date"]):
        out.setdefault(s.strip(), []).append((pd.Timestamp(a), pd.Timestamp(b), pd.Timestamp(an)))
    return out


# ═════════════ 世界（價格、母體）═════════════
def _init(data, cal, v2):
    D.DATA = data; _G["cal"] = cal; UG.set_gate_v2(v2)


def stock_one(args):
    sid, mk = args
    cal = _G["cal"]
    st = D.load_stock(sid, mk, cal)
    if st is None:
        return sid, None
    df = st.df
    p = os.path.join(D.DATA, "stocks", f"{sid}.csv")
    raw = pd.read_csv(p, dtype={"date": str}, usecols=["date", "close"])
    raw["date"] = pd.to_datetime(raw["date"]); raw = raw.drop_duplicates("date").set_index("date").sort_index()
    rc = pd.to_numeric(raw["close"], errors="coerce"); rc[rc <= 0] = np.nan
    rc = rc.reindex(cal).to_numpy(float)
    c = df["close"].to_numpy(float); o = df["open"].to_numpy(float)
    rc = np.where(np.isfinite(c), rc, np.nan)
    return sid, {"c": c, "o": o, "rc": rc, "pit": UG.pit_valid(sid, cal)}


def build_world(name, data, panel, early, procs, log):
    import pickle
    cp = os.path.join(WORK, f"world_{'early' if early else 'main'}.pkl")
    if os.path.exists(cp) and os.environ.get("MINE_REUSE"):
        W = pickle.load(open(cp, "rb")); log(f"[世界 {name}] 讀快取 {cp}（MINE_REUSE；同一支 build_world 產物）"); return W
    W = _build_world(name, data, panel, early, procs, log)
    pickle.dump(W, open(cp, "wb"), protocol=4)
    return W


def _build_world(name, data, panel, early, procs, log):
    UG.set_gate_v2(True)
    D.DATA = data
    cal = D.load_calendar(); n = len(cal)
    stocks = pd.read_csv(os.path.join(data, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(stocks)
    if early:
        U = U[U["market"] == "twse"]
    mk = U.set_index("stock_id")["market"].to_dict()
    with Pool(procs, initializer=_init, initargs=(data, cal, True)) as pool:
        R = dict(pool.map(stock_one, sorted(mk.items()), chunksize=16))
    sids = sorted(s for s, v in R.items() if v is not None)
    S = len(sids)
    C = np.column_stack([R[s]["c"] for s in sids]); O = np.column_stack([R[s]["o"] for s in sids])
    RC = np.column_stack([R[s]["rc"] for s in sids]); PIT = np.column_stack([R[s]["pit"] for s in sids])
    del R
    me = month_ends(cal, complete_last=early)
    pn = pd.read_csv(panel, dtype={"stock_id": str}, usecols=["measure_date", "stock_id", "liq_ok", "bars_ok", "eligible"])
    pn["el"] = (pn["liq_ok"].astype(bool) & pn["bars_ok"].astype(bool)) if early else pn["eligible"].astype(bool)
    pn = pn[pn["el"]]
    em = set(zip(pn["stock_id"], pn["measure_date"].str[:7]))
    mon = [str(cal[i])[:7] for i in me]
    mrow = {}
    for i, mo in enumerate(mon):
        mrow.setdefault(mo, []).append(i)
    ix = {s: j for j, s in enumerate(sids)}
    EL = np.zeros((len(me), S), bool)
    for s, mo in em:
        j = ix.get(s)
        if j is None:
            continue
        for i in mrow.get(mo, ()):
            EL[i, j] = True
    EL &= PIT[me]
    log(f"[世界 {name}] {data}｜日曆 {cal[0].date()}～{cal[-1].date()}（{n}）｜gate3 {len(mk)} 檔、有價 {S}｜判定日 {len(me)}（{cal[me[0]].date()}～{cal[me[-1]].date()}）｜"
        f"母體股-月 {int(EL.sum()):,}")
    return {"name": name, "data": data, "cal": cal, "n": n, "sids": sids, "ix": ix, "mk": mk, "C": C, "O": O, "RC": RC, "me": me, "EL": EL, "early": early,
            "Cf": pd.DataFrame(C).ffill().to_numpy()}


def price_flags(W, P, log):
    cal, me, C, RC = W["cal"], W["me"], W["C"], W["RC"]
    nm, S = len(me), len(W["sids"])
    out = {k: np.zeros((nm, S), bool) for k in ("F1_50", "F1_70", "F1_ok", "F2_1", "F2_05", "F2_ok", "par10")}
    PAR = np.full((nm, S), np.nan)
    dts = pd.DatetimeIndex(cal[me])
    for j, s in enumerate(W["sids"]):
        c = C[:, j]; b = np.flatnonzero(np.isfinite(c))
        if len(b) == 0:
            continue
        cb = c[b]; cs = np.r_[0.0, np.cumsum(cb)]
        k = np.searchsorted(b, me, side="right") - 1
        par, assumed = par_at(P, s, dts)
        PAR[:, j] = par; out["par10"][:, j] = assumed
        ok2 = k >= 0
        rcv = np.where(ok2, RC[b[np.maximum(k, 0)], j], np.nan)
        out["F2_ok"][:, j] = ok2 & np.isfinite(rcv)
        with np.errstate(invalid="ignore"):
            out["F2_1"][:, j] = out["F2_ok"][:, j] & (rcv < par * 1.0)
            out["F2_05"][:, j] = out["F2_ok"][:, j] & (rcv < par * 0.5)
        if len(cb) <= 250:
            continue
        ok1 = k >= 250
        kk = np.clip(k, 250, len(cb) - 1)
        now = cb[kk]; old = cb[kk - 250]; ma = (cs[kk + 1] - cs[kk + 1 - 250]) / 250.0
        out["F1_ok"][:, j] = ok1
        out["F1_50"][:, j] = ok1 & (now <= old * 0.5) & (now < ma)
        out["F1_70"][:, j] = ok1 & (now <= old * 0.3) & (now < ma)
    out["PAR"] = PAR
    return out


def warn_flags(W, A, Bm, days):
    me = W["me"]; nm, S = len(me), len(W["sids"]); ix = W["ix"]
    out = {k: np.zeros((nm, S), bool) for k in ("F5a", "F5b", "F5_ok")}
    k = np.searchsorted(days, me, side="left") - 1                # 快照日 d ＜ m 的最後一份
    for i in range(nm):
        if k[i] < 0:
            continue
        d = days[k[i]]; out["F5_ok"][i] = True
        for s in A.get(d, ()):
            j = ix.get(s)
            if j is not None:
                out["F5a"][i, j] = True
        for s in Bm.get(d, ()):
            j = ix.get(s)
            if j is not None:
                out["F5b"][i, j] = True
    return out


def combine(FL, early):
    f1, f2 = FL["F1_50"], FL["F2_1"]
    if early:
        z = np.zeros_like(f1)
        for k in ("F3_half", "F3_neg", "F4a", "F4b", "F5a", "F5b"):
            FL[k] = z.copy()
        FL["F4"] = z.copy(); FL["F5"] = z.copy()
    else:
        FL["F4"] = FL["F4a"] | FL["F4b"]; FL["F5"] = FL["F5a"] | FL["F5b"]
    cnt = f1.astype(int) + f2 + FL["F3_half"] + FL["F4"] + FL["F5"]
    FL["G1"] = cnt >= 1; FL["G2"] = cnt >= 2
    FL["G3"] = FL["F3_half"] | FL["F5"]; FL["G3n"] = FL["F3_neg"] | FL["F5"]
    return FL


# ═════════════ 下市分類 ═════════════
def delist_table(Wm, We, BS, WARN, DISP, log):
    dl = pd.read_csv(os.path.join(MAIN, "meta", "delisted.csv"), dtype=str)
    rs = pd.read_csv(os.path.join(MAIN, "meta", "otc_delist_reason", "otc_delist_reason.csv"), dtype=str)
    rs["stock_id"] = rs["stock_id"].str.strip()
    rmap = {(s, d): (c, l) for s, d, c, l in zip(rs["stock_id"], rs["delist_date"], rs["reason_code"], rs["reason_label"])}
    A, Bm, days = WARN
    inA = {}
    for p in days:
        for s in A.get(p, ()):
            inA.setdefault(s, []).append(p)
        for s in Bm.get(p, ()):
            inA.setdefault(s, []).append(p)
    inA = {s: np.array(sorted(set(v)), int) for s, v in inA.items()}
    rows = []
    for s, d, mkt in zip(dl["stock_id"].str.strip(), dl["delist_date"], dl["market"]):
        Dt = pd.Timestamp(d)
        W = We if Dt <= pd.Timestamp("2014-12-31") else Wm
        rec = {"sid": s, "delist_date": d, "market": mkt, "world": W["name"]}
        code, lab = rmap.get((s, d), (None, None)) if mkt == "tpex" else (None, None)
        rec["官方分類"] = lab if lab else ("（上市無原因欄）" if mkt == "twse" else "（查無）")
        if lab in ("被合併", "金控", "轉上市"):
            off = "非地雷"
        elif lab in ("拒絕往來", "管理股票"):
            off = "財務性"
        else:
            off = "代理"
        rec["官方判"] = off
        j = W["ix"].get(s)
        pD = int(W["cal"].searchsorted(Dt, side="left"))
        drop = np.nan; bvn = np.nan
        if j is not None:
            c = W["C"][:, j]; b = np.flatnonzero(np.isfinite(c[:pD]))
            if len(b) > 60:
                drop = c[b[-1]] / c[b[-61]] - 1.0
        if W is Wm and s in BS:
            x = BS[s]; x = x[x["ap"] <= pD]
            if len(x):
                o = (x["y"] * 4 + x["q"]).to_numpy(); bvn = float(x["bv"].to_numpy(float)[np.argmax(o)])
        rec["跌幅60"] = drop; rec["淨值"] = bvn
        main_px = bool((np.isfinite(drop) and drop < -0.5) or (np.isfinite(bvn) and bvn < 0))
        rec["主代理可判"] = bool(np.isfinite(drop) or np.isfinite(bvn))
        # 資料庫建議版
        db = False
        if W is Wm and s in inA:
            v = inA[s]; db |= bool(((v >= pD - 250) & (v < pD)).any())
        lo = W["cal"][max(pD - 250, 0)]; hi = W["cal"][min(pD, W["n"] - 1)] if pD < W["n"] else W["cal"][-1]
        for a_, b_, an in DISP.get(s, []):
            if a_ <= hi and b_ >= lo and a_ < Dt:
                db = True
        rec["主代理"] = main_px; rec["並報代理"] = db
        rec["在名冊"] = j is not None                         # 不在該世界 gate3 名冊（DR、早年上櫃等）⇒ 不進母體、不進召回分母；分類照算但不引用
        rec["財務性_主"] = (off == "財務性") or (off == "代理" and main_px)
        rec["財務性_並報"] = (off == "財務性") or (off == "代理" and db)
        rows.append(rec)
    T = pd.DataFrame(rows)
    T.loc[~T["在名冊"], ["主代理", "財務性_主"]] = False                # 名冊外沒有價格序列 ⇒ 主代理不可判（照實標 False）
    log(f"[下市] {len(T)} 筆（在名冊 {int(T['在名冊'].sum())}）｜官方判 {T['官方判'].value_counts().to_dict()}｜財務性 主 {int(T['財務性_主'].sum())}、並報 {int(T['財務性_並報'].sum())}、不一致 {int((T['財務性_主'] != T['財務性_並報']).sum())}")
    return T


# ═════════════ 乙 ═════════════
def yi_returns(W, H):
    """回 R（判定日 × 股）、基準②、X；R 用 m＋1 開盤、m＋H 收盤（ffill）。"""
    C, O, me, EL, n = W["C"], W["O"], W["me"], W["EL"], W["n"]
    Cf = W["Cf"]
    nm, S = len(me), C.shape[1]
    R = np.full((nm, S), np.nan); BASE = np.full((nm, S), np.nan)
    for i, m in enumerate(me):
        if D.exit_pos(m + 1, H) >= n:
            continue
        o1 = O[m + 1]; ok = np.isfinite(o1) & (o1 > 0)
        with np.errstate(invalid="ignore", divide="ignore"):
            R[i] = np.where(ok, Cf[D.exit_pos(m + 1, H)] / o1 - 1.0, np.nan)
            r20 = Cf[m] / Cf[m - 20] - 1.0 if m >= 20 else np.full(S, np.nan)
        msk = EL[i] & np.isfinite(r20) & np.isfinite(R[i])
        if msk.sum() < 20:
            continue
        dec = decile_int(r20[msk]); rr = R[i, msk]
        mu = np.array([rr[dec == q].mean() for q in range(10)])
        bt = np.full(S, np.nan); bt[np.flatnonzero(msk)] = mu[dec]; BASE[i] = bt
    return R, BASE


def seg_mask(W, seg, H):
    a, b = SEG[seg] if isinstance(seg, str) else seg
    cal, me = W["cal"], W["me"]
    mon = np.array([str(cal[m])[:7] for m in me])
    s1 = int(np.flatnonzero(np.array([str(x)[:7] for x in cal]) <= b)[-1])
    return (mon >= a) & (mon <= b) & (np.array([D.exit_pos(m + 1, H) for m in me]) <= s1)


def zero_delist(W, T, H):
    """事件 m 之後到 m＋H 收盤之間財務性下市（主代理）⇒ True。"""
    cal, me = W["cal"], W["me"]
    Z = np.zeros((len(me), len(W["sids"])), bool)
    for s, d, f in zip(T["sid"], T["delist_date"], T["財務性_主"]):
        j = W["ix"].get(s)
        if j is None or not f:
            continue
        Dt = pd.Timestamp(d)
        for i, m in enumerate(me):
            e = D.exit_pos(m + 1, H)
            if e < W["n"] and cal[m] < Dt <= cal[e]:
                Z[i, j] = True
            elif e >= W["n"] and cal[m] < Dt:
                Z[i, j] = True
    return Z


def run_yi(Wm, We, FLm, FLe, T, log):
    rows = []; keep = {}
    for W, FL, segs in ((Wm, FLm, ("探索", "確認")), (We, FLe, ("早年",))):
        for H in HY:
            R, BASE = yi_returns(W, H)
            X = R - BASE
            Z = zero_delist(W, T, H)
            R0 = np.where(Z, -1.0, R); X0 = R0 - BASE
            keep[(W["name"], H)] = (R, BASE)
            np.savez_compressed(os.path.join(WORK, f"yi_{'early' if W['early'] else 'main'}_H{H}.npz"), R=R, BASE=BASE)
            for seg in segs:
                sm = seg_mask(W, seg, H)[:, None]
                base_ok = W["EL"] & sm & np.isfinite(X)
                cand = W["EL"] & sm
                for f in FLAGS:
                    if W["early"] and f in EARLY_NA:
                        continue
                    ev = base_ok & FL[f]; nf = base_ok & ~FL[f]
                    ii, jj = np.nonzero(ev)
                    mu, se, G = cr1(X[ev], ii)
                    mu0, se0, _ = cr1(X0[ev], ii)
                    nmu, nse, _ = cr1(X[nf], np.nonzero(nf)[0])
                    no_open = int((cand & FL[f] & ~np.isfinite(R) & (np.array([D.exit_pos(m + 1, H) < W["n"] for m in W["me"]])[:, None])).sum())
                    rows.append({"段": seg, "旗": f, "H": H, "事件": int(ev.sum()), "月數": G, "R 平均": float(np.nanmean(R[ev])) if ev.any() else np.nan,
                                 "X 平均": mu, "lo": mu - 1.96 * se if np.isfinite(se) else np.nan, "hi": mu + 1.96 * se if np.isfinite(se) else np.nan,
                                 "X 中位": float(np.median(X[ev])) if ev.any() else np.nan, "X>0 比例": float((X[ev] > 0).mean()) if ev.any() else np.nan,
                                 "無旗 X 平均": nmu, "無旗 lo": nmu - 1.96 * nse if np.isfinite(nse) else np.nan, "無旗 hi": nmu + 1.96 * nse if np.isfinite(nse) else np.nan,
                                 "帶旗−無旗": mu - nmu, "含歸零 X 平均": mu0, "含歸零 hi": mu0 + 1.96 * se0 if np.isfinite(se0) else np.nan,
                                 "含歸零筆數": int((ev & Z).sum()), "m＋1 無開盤不進": no_open})
            log(f"[乙] {W['name']} H{H} 完成")
    Y = pd.DataFrame(rows)
    verdict = {}
    for g in ("G1", "G2", "G3"):
        hits = []
        for H in HY:
            e = Y[(Y["旗"] == g) & (Y["H"] == H) & (Y["段"] == "探索")]; c = Y[(Y["旗"] == g) & (Y["H"] == H) & (Y["段"] == "確認")]
            ok = bool(len(e) and len(c) and e["hi"].iloc[0] < 0 and c["hi"].iloc[0] < 0)
            hits.append({"H": H, "探索 hi": float(e["hi"].iloc[0]) if len(e) else None, "確認 hi": float(c["hi"].iloc[0]) if len(c) else None, "該躲": ok})
        n_ok = sum(h["該躲"] for h in hits)
        verdict[g] = {"格": hits, "該躲格數": n_ok, "判定": "該躲成立" if n_ok >= 3 else "該躲不成立"}
    return Y, verdict, keep


# ═════════════ 甲 ═════════════
def add_months(ts, k):
    return ts + pd.DateOffset(months=k)


def run_jia(Wm, We, FLm, FLe, T, DISP, log):
    END = Wm["cal"][-1]
    rows = []
    fin = {"主": T[T["財務性_主"]], "並報": T[T["財務性_並報"]]}
    for W, FL, segs in ((Wm, FLm, ("探索", "確認")), (We, FLe, ("早年",))):
        cal, me = W["cal"], W["me"]
        dts = pd.DatetimeIndex(cal[me])
        mon = np.array([str(x)[:7] for x in dts])
        for ver, TT in fin.items():
            dd = {}
            for s, d in zip(TT["sid"], TT["delist_date"]):
                dd.setdefault(s, []).append(pd.Timestamp(d))
            for k in (12, 24, 36):
                Y = np.zeros((len(me), len(W["sids"])), bool)
                endk = pd.DatetimeIndex([add_months(t, k) for t in dts])
                obs = np.asarray(endk <= END)
                for s, L in dd.items():
                    j = W["ix"].get(s)
                    if j is None:
                        continue
                    for Dt in L:
                        Y[:, j] |= np.asarray((dts < Dt) & (endk >= Dt))
                for seg in segs:
                    a, b = SEG[seg]
                    sm = ((mon >= a) & (mon <= b) & obs)[:, None]
                    base = W["EL"] & sm
                    for f in FLAGS:
                        if W["early"] and f in EARLY_NA:
                            continue
                        fl = base & FL[f]; nf = base & ~FL[f]
                        p1 = float(Y[fl].mean()) if fl.any() else np.nan; p0 = float(Y[nf].mean()) if nf.any() else np.nan
                        rows.append({"段": seg, "代理": ver, "k月": k, "旗": f, "帶旗股-月": int(fl.sum()), "帶旗下市": int(Y[fl].sum()), "精準度": p1,
                                     "無旗股-月": int(nf.sum()), "無旗下市": int(Y[nf].sum()), "無旗比例": p0, "倍數": p1 / p0 if p0 and np.isfinite(p0) and p0 > 0 else np.nan,
                                     "帶旗檔數": int(fl.any(axis=0).sum()), "可觀察最後判定日": str(dts[sm[:, 0]].max().date()) if sm.any() else None})
        log(f"[甲] {W['name']} 精準度完成")
    J = pd.DataFrame(rows)
    # 召回、提前多久
    rec = []
    for ver, TT in fin.items():
        for seg, (a, b) in SEG.items():
            sub = TT[(TT["delist_date"].str[:7] >= a) & (TT["delist_date"].str[:7] <= b)]
            for f in FLAGS:
                W, FL = (We, FLe) if seg == "早年" else (Wm, FLm)
                if W["early"] and f in EARLY_NA:
                    continue
                dts = pd.DatetimeIndex(W["cal"][W["me"]])
                hit = 0; inpop = 0; leads = []; tot = 0; miss = 0
                for s, d in zip(sub["sid"], sub["delist_date"]):
                    j = W["ix"].get(s); Dt = pd.Timestamp(d)
                    if j is None:                                   # 不在該世界 gate3 名冊（DR、早年上櫃等）⇒ 不進分母、另報
                        miss += 1; continue
                    tot += 1
                    w12 = (dts >= add_months(Dt, -12)) & (dts < Dt)
                    w36 = (dts >= add_months(Dt, -36)) & (dts < Dt)
                    inpop += int(W["EL"][w12, j].any())
                    if FL[f][w12, j].any():
                        hit += 1
                    q = np.flatnonzero(w36 & FL[f][:, j])
                    if len(q):
                        leads.append((Dt - dts[q[0]]).days / 30.4375)
                rec.append({"代理": ver, "段": seg, "旗": f, "財務性下市": tot, "下市前12月內帶旗": hit, "召回": hit / tot if tot else np.nan,
                            "下市前12月內曾在母體": inpop, "提前月數中位（36月內第一次帶旗）": float(np.median(leads)) if leads else np.nan, "36月內帶旗檔數": len(leads), "不在名冊不計（DR、早年上櫃等）": miss})
    RC = pd.DataFrame(rec)
    # 處置描述
    disp = []
    for W, FL, segs in ((Wm, FLm, ("探索", "確認")), (We, FLe, ("早年",))):
        dts = pd.DatetimeIndex(W["cal"][W["me"]]); mon = np.array([str(x)[:7] for x in dts])
        Y = np.zeros((len(dts), len(W["sids"])), bool)
        nxt = np.array([add_months(t, 12) for t in dts])
        for s, L in DISP.items():
            j = W["ix"].get(s)
            if j is None:
                continue
            for _, _, an in L:
                Y[:, j] |= (dts < an) & (nxt >= an)
        obs = np.array([add_months(t, 12) <= W["cal"][-1] for t in dts])
        for seg in segs:
            a, b = SEG[seg]
            base = W["EL"] & ((mon >= a) & (mon <= b) & obs)[:, None]
            for f in ("G1", "G2", "G3", "F1_50", "F2_1", "F3_half", "F4", "F5"):
                if W["early"] and f in ("F3_half", "F4", "F5", "G3"):
                    continue
                fl = base & FL[f]; nf = base & ~FL[f]
                disp.append({"段": seg, "旗": f, "帶旗 12 月內被列處置": float(Y[fl].mean()) if fl.any() else np.nan, "無旗": float(Y[nf].mean()) if nf.any() else np.nan})
    return J, RC, pd.DataFrame(disp)


# ═════════════ 丙 ═════════════
def s5_calendar():
    c1 = pd.read_csv(os.path.join(EARLY, "meta", "calendar_twse.csv"))["date"].tolist()
    c2 = pd.read_csv(os.path.join(MAIN, "meta", "calendar_twse.csv"))["date"].tolist()
    cal5 = pd.DatetimeIndex(c1 + [x for x in c2 if x <= "2026-09-24"])
    return cal5


def run_bing(Wm, We, FLm, FLe, log):
    E = np.load(os.path.join(S5W, "events.npz"))
    uni = pd.read_csv(os.path.join(S5W, "uni.csv"), dtype=str)
    cal5 = s5_calendar()
    hdef = np.load(os.path.join(S5W, "hdef.npy"), mmap_mode="r"); bar5 = np.load(os.path.join(S5W, "bar.npy"), mmap_mode="r")
    assert len(cal5) == hdef.shape[1] == 5571 and len(uni) == hdef.shape[0], "⛔ s5 日曆／母體對不上"
    icut = int(cal5.get_loc(pd.Timestamp(CUT)))
    cell = E["cell"]; d = E["d"]; s = E["s"]; M250 = E["M250"]
    Hc = np.array(HS5)[cell // len(GS5)]
    ok = d + Hc <= icut
    cell, d, s, M250, Hc = cell[ok], d[ok], s[ok], M250[ok], Hc[ok]
    tdates = cal5[d]
    # 判定日（兩個世界合併）
    meE = pd.DatetimeIndex(We["cal"][We["me"]]); meM = pd.DatetimeIndex(Wm["cal"][Wm["me"]])
    allme = meE.append(meM)
    k = np.searchsorted(allme.values, tdates.values, side="left") - 1          # 嚴格 ＜ t
    usid = uni["stock_id"].to_numpy()[s]
    nE = len(meE)
    fl = {f: np.zeros(len(d), bool) for f in FLAGS}; known = np.zeros(len(d), bool); elig = np.zeros(len(d), bool)
    for W, FL, sel, row in ((We, FLe, (k >= 0) & (k < nE), k), (Wm, FLm, k >= nE, k - nE)):
        col = np.array([W["ix"].get(x, -1) for x in usid])
        q = sel & (col >= 0)
        known[q] = True; elig[q] = W["EL"][row[q], col[q]]
        for f in FLAGS:
            fl[f][q] = FL[f][row[q], col[q]]
    mon = np.array([str(x)[:7] for x in tdates])
    np.savez_compressed(os.path.join(WORK, "bing_events.npz"), cell=cell, d=d, s=s, known=known, elig=elig, **{f: fl[f] for f in FLAGS})
    segs = dict(SEG); segs["探索＋確認"] = POOL_SEG
    rows = []
    for seg, (a, b) in segs.items():
        sm = (mon >= a) & (mon <= b)
        for c in range(NC5):
            mc = sm & (cell == c)
            for var, base in (("全部", mc & known), ("W1 母體內", mc & known & elig)):
                r = {"段": seg, "格": cell_name(c), "cell": c, "H": int(HS5[c // len(GS5)]), "g": float(GS5[c % len(GS5)]), "版本": var,
                     "事件": int(base.sum()), "查不到旗": int((mc & ~known).sum()) if var == "全部" else None}
                for f in FLAGS:
                    if seg == "早年" and f in EARLY_NA:
                        r[f] = np.nan; continue
                    r[f] = float(fl[f][base].mean()) if base.any() else np.nan
                    if f in ("G1", "G2", "G3") and base.any():
                        a1 = M250[base & fl[f]]; a0 = M250[base & ~fl[f]]
                        r[f"{f}_M250中位_帶旗"] = float(np.nanmedian(a1)) if len(a1) else np.nan
                        r[f"{f}_M250中位_無旗"] = float(np.nanmedian(a0)) if len(a0) else np.nan
                rows.append(r)
    BC = pd.DataFrame(rows)
    # 網格彙總
    grid = []
    for seg in segs:
        for var in ("全部", "W1 母體內"):
            x = BC[(BC["段"] == seg) & (BC["版本"] == var)]
            for f in FLAGS:
                if x[f].isna().all():
                    continue
                v1 = x.loc[x["事件"] >= 1, f].dropna(); v30 = x.loc[x["事件"] >= 30, f].dropna()
                main = x[(x["H"] == 120) & (np.isclose(x["g"], 1.0))]
                grid.append({"段": seg, "版本": var, "旗": f, "格數(≥1事件)": len(v1), "網格中位": float(v1.median()) if len(v1) else np.nan,
                             "p10": float(v1.quantile(0.1)) if len(v1) else np.nan, "p90": float(v1.quantile(0.9)) if len(v1) else np.nan,
                             "格數(≥30事件)": len(v30), "網格中位(≥30)": float(v30.median()) if len(v30) else np.nan,
                             "p10(≥30)": float(v30.quantile(0.1)) if len(v30) else np.nan, "p90(≥30)": float(v30.quantile(0.9)) if len(v30) else np.nan,
                             "登錄主格 H120 g100%": float(main[f].iloc[0]) if len(main) else np.nan, "主格事件": int(main["事件"].iloc[0]) if len(main) else 0})
    BG = pd.DataFrame(grid)
    # 帶旗股票之後變飆股的機率（股-月）
    pri = []
    s5ix = {sid: i for i, sid in enumerate(uni["stock_id"])}
    keyall = s.astype(np.int64) * 10000 + d
    for W, FL, segl in ((Wm, FLm, ("探索", "確認", "探索＋確認")), (We, FLe, ("早年",))):
        dts = pd.DatetimeIndex(W["cal"][W["me"]]); mon_m = np.array([str(x)[:7] for x in dts])
        d5 = np.array([cal5.get_loc(t) if t in cal5 else -1 for t in dts])
        d5n = np.r_[d5[1:], -1]
        cols = [(j, s5ix[sid]) for j, sid in enumerate(W["sids"]) if sid in s5ix]
        jj = np.array([c[0] for c in cols]); ss = np.array([c[1] for c in cols])
        for seg in segl:
            a, b = segs[seg]
            ii = np.flatnonzero((mon_m >= a) & (mon_m <= b) & (d5 >= 0) & (d5n > 0))
            I, Jc = np.meshgrid(ii, np.arange(len(jj)), indexing="ij"); I = I.ravel(); Jc = Jc.ravel()
            sI = ss[Jc]; dI = d5[I]; dN = d5n[I]
            hasbar = bar5[sI, dI]
            hd1 = hdef[sI, np.minimum(dI + 1, hdef.shape[1] - 1)]
            for f in ("G1", "G2", "G3"):
                if W["early"] and f == "G3":
                    continue
                fv = FL[f][I, jj[Jc]]
                ratios = []; mainr = None
                for c in range(NC5):
                    H = int(HS5[c // len(GS5)])
                    dom = hasbar & (hd1 >= H) & (dI + 1 + H <= icut)
                    kc = np.sort(keyall[cell == c])
                    lo = sI.astype(np.int64) * 10000 + dI + 1; hi = sI.astype(np.int64) * 10000 + dN
                    if len(kc):
                        p = np.searchsorted(kc, lo, side="left")
                        has = (p < len(kc)) & (kc[np.minimum(p, len(kc) - 1)] <= hi)
                    else:
                        has = np.zeros(len(lo), bool)
                    a1 = has[dom & fv]; a0 = has[dom & ~fv]
                    p1 = a1.mean() if len(a1) else np.nan; p0 = a0.mean() if len(a0) else np.nan
                    rr = p1 / p0 if (np.isfinite(p0) and p0 > 0) else np.nan
                    ratios.append(rr)
                    if H == 120 and np.isclose(GS5[c % len(GS5)], 1.0):
                        mainr = {"帶旗股-月": int(len(a1)), "帶旗起漲比例": float(p1), "無旗股-月": int(len(a0)), "無旗起漲比例": float(p0), "倍數": float(rr)}
                rv = np.array([x for x in ratios if np.isfinite(x)])
                pri.append({"段": seg, "旗": f, "主格": mainr, "全網格倍數中位": float(np.median(rv)) if len(rv) else np.nan,
                            "p10": float(np.quantile(rv, 0.1)) if len(rv) else np.nan, "p90": float(np.quantile(rv, 0.9)) if len(rv) else np.nan, "格數": int(len(rv))})
    log(f"[丙] 事件（截到 {CUT}）{len(d):,}｜查不到旗 {int((~known).sum()):,}（早年上櫃、或不在世界母體）")
    return BC, BG, pri, {"事件": int(len(d)), "查不到旗": int((~known).sum())}


# ═════════════ 主體 ═════════════
def body(a):
    os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    log = log_to(os.path.join(OUT, "run.log"))
    log(f"===== researchMine body {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜讀法寫死 {TAGT} =====")
    hit = sha_gate(); log(f"[sha] {hit}")
    Wm = build_world("主快照", MAIN, PANEL, False, a.procs, log)
    We = build_world("早年版面（只上市）", EARLY, EARLY_PANEL, True, a.procs, log)
    P = par_lookup(pd.read_csv(os.path.join(MAIN, "meta", "par_timeline.csv"), dtype=str))
    B, F = load_fin(Wm["cal"], log)
    BS = {s: g for s, g in B.groupby("stock_id")}; FS = {s: g for s, g in F.groupby("stock_id")}
    import pickle
    wp = os.path.join(WORK, "warn.pkl")
    if os.path.exists(wp) and os.environ.get("MINE_REUSE"):
        WARN = pickle.load(open(wp, "rb"))
    else:
        WARN = load_warn(Wm["cal"], log); pickle.dump(WARN, open(wp, "wb"))
    DISP = load_disposal(MAIN)
    FLs = {}
    for W in (Wm, We):
        FL = price_flags(W, P, log)
        nm, S = len(W["me"]), len(W["sids"])
        for k in ("F3_half", "F3_neg", "F3_ok", "F4a", "F4b", "F4_ok"):
            FL[k] = np.zeros((nm, S), bool)
        FL["BV"] = np.full((nm, S), np.nan)
        if not W["early"]:
            for j, s in enumerate(W["sids"]):
                o = fin_flags_stock(s, BS.get(s), FS.get(s), W["me"], FL["PAR"][:, j])
                for k in ("F3_half", "F3_neg", "F3_ok", "F4a", "F4b", "F4_ok"):
                    FL[k][:, j] = o[k]
                FL["BV"][:, j] = o["bv"]
            FL.update(warn_flags(W, *WARN))
        else:
            FL["F5a"] = np.zeros((nm, S), bool); FL["F5b"] = np.zeros((nm, S), bool); FL["F5_ok"] = np.zeros((nm, S), bool)
        FLs[W["name"]] = combine(FL, W["early"])
        np.savez_compressed(os.path.join(WORK, f"flags_{'early' if W['early'] else 'main'}.npz"), me=np.array([str(W["cal"][m].date()) for m in W["me"]]),
                            sids=np.array(W["sids"]), EL=W["EL"], **{k: v for k, v in FLs[W["name"]].items() if k not in ("PAR", "BV")}, PAR=FL["PAR"], BV=FL["BV"])
        log(f"[旗] {W['name']} 完成")
    FLm, FLe = FLs[Wm["name"]], FLs[We["name"]]
    # 旗的盛行率與可判率（母體股-月）
    fr = []
    for W, FL in ((Wm, FLm), (We, FLe)):
        yrs = np.array([W["cal"][m].year for m in W["me"]])
        for y in sorted(set(yrs)):
            base = W["EL"] & (yrs == y)[:, None]
            if not base.any():
                continue
            r = {"世界": W["name"], "年": int(y), "母體股-月": int(base.sum())}
            for f in FLAGS:
                r[f] = float(FL[f][base].mean())
            for k in ("F1_ok", "F2_ok", "F3_ok", "F4_ok", "F5_ok"):
                r[k + "（可判率）"] = float(FL[k][base].mean())
            r["面額假設10元（股-月比例）"] = float(FL["par10"][base].mean())
            fr.append(r)
    FR = pd.DataFrame(fr); FR.to_csv(os.path.join(OUT, "flag_rate.csv"), index=False)
    par10 = sorted({W["sids"][j] for W, FL in ((Wm, FLm), (We, FLe)) for j in np.flatnonzero((FL["par10"] & W["EL"]).any(axis=0))})
    # 下市
    T = delist_table(Wm, We, BS, WARN, DISP, log)
    T.to_csv(os.path.join(OUT, "delist.csv"), index=False)
    t15 = T[(T["delist_date"] >= "2015-07-01") & T["sid"].isin(Wm["ix"])]
    f3cov = {"2015-07 起下市且在主名冊": int(len(t15)), "其中 bs_hist（淨值）有任何一季": int(t15["sid"].isin(BS).sum()),
             "其中 fin_hist（EPS）有任何一季": int(t15["sid"].isin(FS).sum()),
             "說明": "淨值表只收現存公司 ⇒ 下市股的 F3 幾乎全部不可判（生存者偏誤）；EPS 表有收下市股"}
    log(f"[F3 覆蓋] {f3cov}")
    # 乙
    Y, verdict, keep = run_yi(Wm, We, FLm, FLe, T, log)
    Y.to_csv(os.path.join(OUT, "yi.csv"), index=False)
    # 甲
    J, RC, DP = run_jia(Wm, We, FLm, FLe, T, DISP, log)
    J.to_csv(os.path.join(OUT, "jia.csv"), index=False); RC.to_csv(os.path.join(OUT, "jia_recall.csv"), index=False); DP.to_csv(os.path.join(OUT, "jia_disposal.csv"), index=False)
    # 丙
    BC, BG, pri, binfo = run_bing(Wm, We, FLm, FLe, log)
    BC.to_csv(os.path.join(OUT, "bing_cells.csv"), index=False); BG.to_csv(os.path.join(OUT, "bing_grid.csv"), index=False)
    # 必附一句
    R250, BASE250 = keep[(Wm["name"], 250)]
    dts = pd.DatetimeIndex(Wm["cal"][Wm["me"]]); mon = np.array([str(x)[:7] for x in dts])
    sm = ((mon >= "2017-03") & (mon <= "2025-08"))[:, None] & Wm["EL"] & np.isfinite(R250)
    big = sm & (R250 <= -0.5)
    sent = {}
    for f in ("G1", "G2", "G3"):
        rc_ = RC[(RC["代理"] == "主") & (RC["旗"] == f) & (RC["段"].isin(["探索", "確認"]))]
        x = int(rc_["下市前12月內帶旗"].sum()); tot = int(rc_["財務性下市"].sum())
        y = float((big & FLm[f]).sum() / big.sum()) if big.any() else np.nan
        g = BG[(BG["段"] == "探索＋確認") & (BG["版本"] == "全部") & (BG["旗"] == f)].iloc[0]
        sent[f] = {"x 躲掉下市（檔）": x, "財務性下市總數": tot, "y 大跌中帶旗比例": y, "大跌股-月": int(big.sum()), "z 誤殺飆股（網格中位）": float(g["網格中位"]),
                   "z p10": float(g["p10"]), "z p90": float(g["p90"]), "登錄主格": float(g["登錄主格 H120 g100%"]),
                   "帶旗股-月占母體": float(FLm[f][sm].mean())}
    S = {"登錄": f"PREREG地雷股濾網 seq3 sha {REG_SHA}；裁定 seq310、311、313、314", "讀法寫死": TAGT, "資料": {"main": MAIN_SHA, "早年": "3edc0e2206", "s5": "950ad26e12＋b53f5540a8"},
         "GATE_V2": True, "F3 下市股覆蓋": f3cov, "乙判定": verdict, "N_單筆": 3, "必附一句": sent, "丙": binfo, "丙_變飆股": pri,
         "面額假設10元（母體內曾出現）": par10, "下市": {"總": int(len(T)), "在名冊": int(T["在名冊"].sum()), "官方判（在名冊）": T.loc[T["在名冊"], "官方判"].value_counts().to_dict(),
                                                 "財務性_主（在名冊）": int(T.loc[T["在名冊"], "財務性_主"].sum()), "財務性_並報（在名冊）": int(T.loc[T["在名冊"], "財務性_並報"].sum()),
                                                 "兩代理不一致（在名冊）": int((T.loc[T["在名冊"], "財務性_主"] != T.loc[T["在名冊"], "財務性_並報"]).sum())}}
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log("===== body 完成 =====")


# ═════════════ 丁 ═════════════
def _ding_one(args):
    key, var, r = args
    from backtest import listexit_lines as L
    from backtest import research11 as R
    from backtest import rerun17 as RR
    ctx = _G["ctx"]; N = 20 if key == "c13" else 10
    flagged = _G["FLG"].get(var, set())
    zeroed = []

    def wf(batch, t, eq_prev, cash):
        out = []
        for row in batch:
            if (row["sid"], int(row["entry_pos"])) in flagged:
                out.append(0.0); zeroed.append(float(row["gross"]))
            else:
                out.append(eq_prev / N)
        return out
    kw = {"stop_force": _G["SF"], "weight_fn": wf}
    if key == "c13":
        o = R.simulate_mtm(ctx["sig13"], "H60", 20, np.random.default_rng(RR.P1_SEED0 + r), ctx["closes"], ctx["opens"], ctx["ncal"],
                           log=[], d_max=None, pick="relvol", queue_days=0, return_equity=True, **kw)
    else:
        o = L.sim(ctx, kw, r)
    eq = np.asarray(o["equity"], float)
    w0, w1, e1, c0 = _G["w0"], _G["w1"], _G["e1"], _G["c0"]
    c, mm, _ = RR.win_metrics(eq, o["first"], o["end"], w0, w1)
    ce, me_, _ = RR.win_metrics(eq, o["first"], o["end"], w0, e1)
    cc, mc, _ = RR.win_metrics(eq, o["first"], o["end"], c0, w1)
    z = np.array(zeroed)
    return {"key": key, "var": var, "r": r, "cagr": float(c), "mdd": float(mm), "探索_cagr": float(ce), "探索_mdd": float(me_), "確認_cagr": float(cc), "確認_mdd": float(mc),
            "trades": int(o["trades"]), "eq_sha": hashlib.sha256(eq.tobytes()).hexdigest()[:16], "濾掉筆數": int(len(z)),
            "濾掉毛報酬和": float(z.sum()), "濾掉淨報酬和": float((z - COST).sum())}


def ding(a):
    os.makedirs(OUT, exist_ok=True)
    log = log_to(os.path.join(OUT, "run_ding.log"))
    log(f"===== researchMine ding {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜讀法寫死 {TAGT} =====")
    sha_gate()
    from backtest import listexit_lines as L
    from backtest import research11 as R
    ctx = L.setup_t1(log, t1=True)
    from backtest import rerun17 as RR
    G = RR._G; AND = G["AND"]; e = AND["entry_pos"].to_numpy()
    ctx["sig13"] = AND[(e >= G["w0"]) & (e <= G["w1"])]
    cal = ctx["cal"]; mk = ctx["mk"]
    SF = R.stop_force_days(R.valid_from_data(sorted(ctx["closes"]), mk, cal), ctx["w1"])
    z = np.load(os.path.join(WORK, "flags_main.npz"))
    me = pd.DatetimeIndex(z["me"]); sids = list(z["sids"]); ix = {s: j for j, s in enumerate(sids)}
    FLG = {"base": set()}; cnt = {}
    for var in ("G1", "G3"):
        M = z[var]; st = set(); n_all = {}
        for nm, sg, rl in (("c1", ctx["sig"], "H120"), ("c13", ctx["sig13"], "H60")):
            sg = sg[sg[f"xpos_{rl}"] >= 0].rename(columns={f"g_{rl}": "gross"})          # 引擎同一步（research11 680～685 行）
            k_ = 0; gs = []
            for sid, ep, gr in zip(sg["sid"], sg["entry_pos"], sg["gross"]):
                t = cal[int(ep) - 1]; i = int(me.searchsorted(t, side="right")) - 1; j = ix.get(sid)
                if i >= 0 and j is not None and M[i, j]:
                    st.add((sid, int(ep))); k_ += 1; gs.append(float(gr))
            n_all[nm] = {"窗內訊號": int(len(sg)), "帶旗訊號": k_, "帶旗訊號毛報酬−成本 平均": float(np.mean(gs) - COST) if gs else None,
                         "全部訊號毛報酬−成本 平均": float(sg["gross"].mean() - COST)}
        FLG[var] = st; cnt[var] = n_all
    log(f"[丁] 帶旗訊號 {json.dumps(cnt, ensure_ascii=False)}")
    e1 = int(cal.searchsorted(pd.Timestamp("2021-12-30"))); c0 = int(cal.searchsorted(pd.Timestamp("2022-01-03")))
    _G.update(ctx=ctx, SF=SF, FLG=FLG, w0=ctx["w0"], w1=ctx["w1"], e1=e1, c0=c0)
    jobs = [(k, v, r) for k in ("c13", "c1") for v in ("base", "G1", "G3") for r in range(a.reps)]
    t0 = time.time()
    with Pool(a.procs) as pool:
        res = pool.map(_ding_one, jobs, chunksize=4)
    log(f"[丁] {len(jobs)} 顆 {time.time() - t0:.0f}s")
    SD = pd.DataFrame(res); SD.to_csv(os.path.join(WORK, "ding_seeds.csv.gz"), index=False, float_format="%.17g")
    # 閘門：base ＝ resultsT1fix t1
    ref = pd.read_csv(os.path.expanduser("~/tw-p17/backtest/resultsT1fix/seeds.csv.gz"), float_precision="round_trip")   # ⛔ 預設快速解析不是 round-trip（p4_features.read_panel 註）
    ref = ref[(ref["var"] == "t1") & ref["key"].isin(["c1", "c13"])]
    mg = SD[SD["var"] == "base"].merge(ref, on=["key", "r"], suffixes=("", "_ref"))
    bad = int(((mg["cagr"].map(repr) != mg["cagr_ref"].map(repr)) | (mg["mdd"].map(repr) != mg["mdd_ref"].map(repr)) | (mg["eq_sha"] != mg["eq_sha_ref"])).sum())
    gate = {"比對顆數": int(len(mg)), "不同": bad}
    log(f"[丁 閘門] base vs resultsT1fix t1：{gate}")
    if bad or len(mg) != 2 * a.reps:
        raise SystemExit("⛔ 丁閘門不過")
    rows = []
    for (k, v), g in SD.groupby(["key", "var"]):
        rows.append({"策略": {"c13": "營量 v1", "c1": "營飆 v1"}[k], "濾網": {"base": "不濾（正式）", "G1": "濾 G1", "G3": "濾 G3"}[v], "顆": len(g),
                     "主窗年化中位": float(g["cagr"].median()), "主窗回落中位": float(g["mdd"].median()),
                     "探索年化中位": float(g["探索_cagr"].median()), "確認年化中位": float(g["確認_cagr"].median()),
                     "交易筆數平均": float(g["trades"].mean()), "濾掉筆數平均（每顆）": float(g["濾掉筆數"].mean()),
                     "濾掉那些筆 淨報酬平均（毛−0.585%）": float(g["濾掉淨報酬和"].sum() / g["濾掉筆數"].sum()) if g["濾掉筆數"].sum() else np.nan})
    DG = pd.DataFrame(rows); DG.to_csv(os.path.join(OUT, "ding.csv"), index=False)
    json.dump({"閘門": gate, "帶旗訊號": cnt, "顆數": a.reps, "主窗": [str(cal[ctx["w0"]].date()), str(cal[ctx["w1"]].date())]},
              open(os.path.join(OUT, "ding.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log("===== ding 完成 =====")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", nargs="?", default="body", choices=["body", "ding", "page"])
    ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        from backtest import researchMine_check as CK
        return CK.main()
    if a.stage == "body":
        body(a)
    elif a.stage == "ding":
        ding(a)
    else:
        from backtest import researchMine_page as PG
        PG.main()


if __name__ == "__main__":
    main()
