# -*- coding: utf-8 -*-
"""PREREG台指期貨六題 seq2（台股策略線登錄 sha 8ea4f8b4010de81f，2026-10-06 10:48；裁定 seq304 §六 發號、seq305 §四 核准 seq2）。回測線。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTXF body
    抽樣查核：--check（⛔ 不呼叫本體的 load_fut／daily／run_path／run_starts，逐筆從原始列自己走契約）｜網頁：page

⭐ 讀法寫死時間：2026-10-06 11:50（台北）；寫死前 ⛔ 沒看任何期貨價格統計或本件輸出
   （只看過資料格式：欄位、到期月份列數、到期日的結算價欄有沒有值、星期分佈，見下 R0）。
排序（裁定 seq305 §四）：甲 → 乙 → 丙 → 丁 → 戊 → 己。
⛔ 期交所條款：私有庫原始數字不得重製散布 ⇒ repo 裡只放彙總（報酬、勝率、比例、CI、次數）；逐日／逐筆中間檔一律放 ~/txfwork/（不進 repo）。

═══ R0 共同讀法（執行者補；登錄沒寫清楚的）═══
  資料：私有庫 /home/chemtim/us-stock-data/data/taifex_private（F1 fut_daily、F2 inst_fut、F3 pc_ratio、F4 margin/history、F5 rates）；
        加權指數 us-stock-data data/macro/twse_taiex.csv（1990 起，只有收盤）；0050、00631L 還原價：tw-stock-data 快照 62eee83129（主，2015 起）
        ＋ 3edc0e2206 data/early（2015 以前，同 researchRev.market_series 接法：除息因子連乘、主快照首日比例接上）。
  單式近月：F1 篩 is_spread＝0、is_weekly＝0、dup_seq ∈ {空, 1}；一般盤列定交易日。
  到期日（最後交易日）＝ 該到期月份在一般盤出現的最後一天（含遇休市順延；資料尾端還在交易的契約不算到期）。
  ⭐ 結算價：F1 到期契約在最後交易日的 settle 欄 343 次中有 214 次是 0（官方欄未給最後結算價）⇒ 結算價 ＞ 0 用 settle，否則用該契約當日一般盤收盤代表（照實註；
     之後的「以結算價了結」都是這個代表值）。
  近月連續序列（丙丁戊己用）＝ 主版轉倉：到期日以結算價了結、同日以次月一般盤收盤買進；連續報酬 ＝ 持有那口契約的價格報酬（含正逆價差收斂，⭐ 台指不含息）。
  夜盤歸日照官方：交易日期 t 的盤後列 ＝ t−1 15:00～t 05:00；契約一律用「t 日一般盤的近月」那一口。
  成本（甲高案，判以高案）：每邊 ＝ 期交稅 0.002% × 契約價值 ＋ 滑價 1 點 ＋ 手續費（高 NT$50、低 NT$20／小台口 ⇒ 每點 NT$50 ⇒ 1 點、0.4 點）
     ⇒ 每邊成本占契約價值 ＝ 0.00002 ＋ (1 ＋ 手續費÷50) ÷ 價格（價格用成交當時的原始價）。來回 ＝ 兩邊相加。⛔ 期交稅不依歷史稅率（照登錄寫死）。
  契約規模：價格序列一律 TX；部位以「契約價值」連續量表示（可為小數口，⛔ 不做整數口）；保證金用 TX 每口金額 ÷ (200 × 價格) 換成占契約價值的比例。
     TMF 只有 2024-07 起 ⇒ 歷史以 TX／MTX 依契約規模換算代表（裁定 seq305 §四）；TMF×20＝TX 保證金 27／27 次全符（資料庫 README）。
  保證金（F4）：生效日 D（README：公告次一一般交易時段日）⇒ 日期 ≥ D 的收盤起用新值；2004-09-30 以前「無資料」，⛔ 不往前推。
  利率（F5）：臺銀一年期定存「固定」欄、以月為準；2025-12 起延用 2025-11 值（標明）；2001-01 以前無資料。
  年化 ＝ (期末淨值 ÷ 期初淨值)^(365.25 ÷ 日曆天數) − 1，期初 ＝ 窗起日前一個交易日收盤（同窗、同式套在期貨與 ETF；⚠ 與 0050 錨 24.02% 的年化式不同、窗也不同 ⇒ 不並列）。
  最大回落 ＝ 窗內（含期初點）淨值 ÷ 歷史高 − 1 的最小值。年化波動 ＝ 日對數報酬標準差 × √252。
  月分群 CI：CR0、1.96（research11.cl_stats 同式）。
  段：日期以台北交易日；「2026-09」＝ 到 2026-09-30。

═══ 甲 期貨代替 0050／正2（登錄 §二；N_組合 ＋1）═══
  起點：2005-01-31 收盤進場（早年段 2005-02 起）；連續跑到 2026-09-30；各段用同一條淨值曲線切窗（⛔ 各段不重新進場）。
  帳戶：權益 E、契約價值 V；每日 E ＋＝ V × 持有契約價格報酬；利息 ＝ max(E − 原始保證金 × 口數, 0) × F5 × 日曆天數 ÷ 365（以前一日收盤部位算）。
  轉倉（主版）：到期日以結算價了結、同日收盤買進次月（扣兩邊成本）；另報「結算前一日收盤轉倉」。
  調倉（主版）：每次轉倉後把 V 調回 L × E；另報「不調」＝ 口數不變（V 依新舊價格換算），只在追繳時補。
  追繳（照乙）：收盤 E ＜ 維持保證金 × 口數 ⇒ 計一次、補到原始保證金（補入金額當外部資金，報酬用時間加權）；賠光：前一日 E ＋ V ×（當日最低 ÷ 前一日收盤 − 1）≤ 0（最低含夜盤，2017-05 起）。
  比較：L1 vs 0050 還原；L2 vs 00631L 還原（2014-10-31 起）與「0050 每日 2 倍」合成（每日報酬 × 2、不計費用）；L2 vs 0050 一判。
  ⭐ 判定（執行者補：段怎麼合）：各段照使用者判準（條件一 年化 ＞ 0050；條件二 年化÷|回落| ≥ 0050）各給 合格／另列／不合格；
     探索、確認兩段都合格 ⇒ 合格｜兩段條件一都成立（至少另列）⇒ 另列｜否則 不合格；早年段照報、方向相反要寫出（⛔ 不進判定）。
  每年差額（期貨 − ETF，日曆年報酬）：平均與 CI（以年為群：平均 ± 1.96 × 標準差 ÷ √年數；2026 只到 9 月照報）。
  除息季（6～9 月）價差貢獻：每年 6～9 月 月對數報酬差（期貨 − ETF）加總，與其餘月份加總並列（年平均）。
  轉倉價差（描述）：每次主版轉倉 （次月收 − 近月結算）÷ 近月結算 的年加總平均、逆價差（＜0）占比。
  TMF／MTX 核對（2024-07 起；MTX 2001 起）：各自主版連續日報酬 vs TX 的相關、平均絕對差、年化差（只報彙總）。

═══ 乙 槓桿與追繳（登錄 §三；描述、N＝0）═══
  L ∈ {1, 2, 3, 5, 10, 14}；起點 ＝ 每個交易日收盤進場，持有 250 個交易日；每月轉倉後調回 L（主版轉倉）。
  ⭐ 「14（只放原始保證金）」讀法（執行者補）：主格用固定 14 倍；另報描述版「每次調倉都只放原始保證金」（倍數 ＝ 契約價值 ÷ 原始保證金，2004-09-30 起）。
  1990-01～1998-07-20：加權指數收盤同幅度「推算」，無成本、無保證金、無最低價（賠光以收盤判、標「推算」）；調倉日 ＝ 每月第 3 個星期三當天或之後第一個交易日。
  1998-07-21 起 TX 主版近月；1998-07-21 當天用加權指數報酬、收盤進 TX（扣進場成本）。乙 ⛔ 不計利息（登錄 §三 未列；照實註）、計轉倉成本（高案）。
  追繳：收盤 E ＜ 維持保證金 × 口數（F4 當時值）⇒「碰到追繳」；2004-09-30 以前 ⇒「無資料」、只報賠光。
  兩條路並報：補足路（追繳時補到原始保證金；只算起點 ≥ 2004-09-30）｜不補路（從不補錢；全期）。「一年內碰到追繳的起點比例」兩條路相同（第一次追繳之前兩路一樣）。
  賠光：當日最低（含夜盤）使 E ≤ 0 ⇒ 該起點出局（推算段以收盤）。最壞起點 ＝ 不補路一年後權益最低的起點（同為賠光取最早）。
  ⚠ 補足路的「補入金額」：補到原始保證金後，下次調倉照「當時權益（含補入的錢）× L」⇒ L 大於「契約價值÷原始保證金」時補入會越滾越大（實際上券商不會讓你這樣開倉）
     ⇒ 平均補入只當參考，另報中位；最低價照官方資料（含盤中瞬間急跌、收盤幾乎平盤的日子，照算）。（2026-10-06 12:20 台北補記：看過乙初版彙總後補的「呈現」欄，口徑未改）
  年份單列：起點落在 1990、2000、2008、2020、2022 年。

═══ 丙 夜盤 → 隔日日盤（登錄 §四、§十；N_單筆 6）═══
  n_t ＝ 盤後收(t) ÷ 一般收(t−1) − 1｜d_t ＝ 一般收(t) ÷ 一般開(t) − 1｜d2_t ＝ 一般收(t) ÷ 盤後收(t) − 1（同一口 t 日近月）。
  分位：n_t 在前 250 個有效 n（t−250..t−1，不含 t）中的位置 p ＝ 前 250 個中 ＜ n_t 的比例；組 ＝ min(9, ⌊10p⌋)；最高組＝9、最低組＝0。
  X ＝ d（或 d2）− 同段「有分組的全部日」平均；月分群 CI；延續 ＝ 最高組 X＞0／最低組 X＜0；反轉 ＝ 相反。
  「有延續／有反轉」＝ 探索、確認兩段 X 同號且 CI 不跨 0。交易版：最高組開盤買、最低組開盤賣，收盤平；扣來回成本（高案，開盤原始價）；「可交易」＝ 兩段平均 CI 下緣 ＞ 0。
  段：探索 2017-05-16～2021-12-31（實際有分組的日子要等 250 個前值）｜確認 2022-01-01～2026-09-30。

═══ 丁 TXO 賣買權比（登錄 §五、§十；N_單筆 6）═══
  x3 ＝ TXO 賣權買權未平倉比、x4 ＝ 成交量比；分位 p 同丙（前 250 個交易日、不含當日）；最高 10% ＝ p ≥ 0.9、最低 10% ＝ p ＜ 0.1。
  公布時點未實測 ⇒ 一律次一交易日一般盤開盤進（裁定 seq304）：R_H ＝ 近月連續 收(t＋H) ÷ 開(t＋1) − 1，H ∈ {1, 5, 20}（持有 H 根，進場那根算第 1 根）。
  差 ＝ 最高組平均 − 最低組平均；SE ＝ √(SE高² ＋ SE低²)（各自月分群，忽略兩組同月共變）。不扣成本（問的是預測力）。
  段（事件 t＋1 在段內且 t＋H ≤ 段尾）：早年 2002-起～2014-12-31｜探索 2015-01-01～2020-12-31｜確認 2021-01-01～2026-09-30。
  「有預測力」＝ 探索、確認同號且兩段 CI 都不跨 0；早年方向相反要寫出。
  x1（外資 TX＋MTX÷4 淨未平倉口數）、x2（x1 五日變化）：F2 只有 2023-10-05 起 ⇒ 只描述（分位要 250 個前值 ⇒ 約 2024-10 起），標「約 2 年、不可判定」，⛔ 不判。

═══ 戊 結算週（登錄 §六；N_單筆 3）═══
  結算日 e ＝ TX 到期日（上面定義；1998-08 起）。三個窗：①結算週一～三 ＝ e 往前 3 個交易日收盤 → e 收盤（3 日累積）｜②結算日當天 ＝ e−1 收 → e 收｜
  ③結算後第一個交易日 ＝ e 收 → e＋1 收。對照 ＝ 同段內、同長度、終點不是任何結算窗終點的全部交易日窗的平均；X ＝ 事件 − 對照；月分群 CI。
  ⭐ 判定以加權指數為準（N＝3 ＝ 三個窗；執行者補），TX 近月連續並報、方向不同要寫出。「有」＝ 探索、確認同號且 CI 不跨 0。
  段（以 e 所在日）：早年 1998-08～2014-12｜探索 2015～2020｜確認 2021～2026-09。

═══ 己 舊大盤訊號改期貨成本（登錄 §七；沿用原 N；⚠ 事後重算）═══
  反轉訊號（researchRev 大盤層主窗 2017-03-02～2026-08-24）：事件與基準日沿用 resultsRev/events_market.csv（⛔ 不重偵測）；
     R20_TX ＝ 近月連續 收(b＋20) ÷ 開(b＋1) − 1（TWSE 日曆位置；缺值取之前最後一根）；X ＝ R20_TX − 同窗所有基準日 R20_TX 平均（基準日集合同原件 base_days）；
     扣期貨來回成本（高案，b＋1 開盤原始價）：低點 X − 成本、高點 X ＋ 成本；CI 以 20 日區段分群、Bonferroni z 沿用原件（k＝28）；出口與結果照原件（exit_signal.exit_result）。
     0050 並報兩欄：原件（不扣成本，閘：逐格＝原 cells.csv）、0050 改扣期貨成本。
  驅動因素（researchY 主窗）：事件沿用 resultsY/body_events.csv ＋ repo 外 ~/us_work/prey/body_events_priv.csv（#2，sha 對 body_private_sha.txt）；原件出口①的 12 格照原件「只報筆數」（⛔ 不算報酬）；出口②的 4 格：
     R20_TX ＝ 近月連續 開(s＋20) ÷ 開(s) − 1；對照 ＝ 原件對照日集合上的 R20_TX 平均；D 扣成本往不利方向（加碼 D − 成本、減碼 D ＋ 成本）；Bonferroni z*＝2.9552、月分群。
  翻轉格數：原不過、現過；原過、現不過。⚠ 毛報酬早已看過 ⇒ 全部標「事後重算」；翻成合格最多「暫定」、只進前瞻紀錄（裁定 seq304）。

GATE_V2：本件無個股母體，不適用（照實寫）。
輸出 backtest/resultsTXF/（summary.json、*_cells.csv 彙總、check.json、台指期貨六題.html）；逐日中間檔 ~/txfwork/（⛔ 不進 repo）。
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import io
import json
import math
import os
import subprocess
import sys
import time
from statistics import NormalDist

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsTXF")
WORK = os.path.expanduser("~/txfwork")
PRIV = "/home/chemtim/us-stock-data/data/taifex_private"
TAIEX_CSV = "/home/chemtim/us-stock-data/data/macro/twse_taiex.csv"
SNAP_SHA = "62eee83129fd804fc92f3e97a96c1e04499dc921"
SNAP = os.path.expanduser(f"~/h2data/{SNAP_SHA}/data")
REV_SNAP = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
DB = os.path.expanduser("~/tw-stock-data")
EARLY_SHA = "3edc0e2206"
TAGT = "2026-10-06 11:50（台北）"

TAX, SLIP = 0.00002, 1.0
FEES = {"高": 50.0, "低": 20.0}
MULT = 200.0
END = "2026-09-30"
A_START = "2005-02-01"
A_SEG = {"早年": ("2005-02-01", "2014-12-31"), "探索": ("2015-01-01", "2020-12-31"), "確認": ("2021-01-01", END)}
C_SEG = {"探索": ("2017-05-16", "2021-12-31"), "確認": ("2022-01-01", END)}
D_SEG = {"早年": ("2001-12-24", "2014-12-31"), "探索": ("2015-01-01", "2020-12-31"), "確認": ("2021-01-01", END)}
E_SEG = {"早年": ("1998-07-21", "2014-12-31"), "探索": ("2015-01-01", "2020-12-31"), "確認": ("2021-01-01", END)}
B_LS = (1, 2, 3, 5, 10, 14)
B_W = 250
MARGIN0 = "2004-09-30"
TX0 = "1998-07-21"
NIGHT0 = "2017-05-16"
LOG: list = []


def log(s):
    LOG.append(s)
    print(s, flush=True)


def now_tpe():
    return f"{pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）"


def sha16(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]


def cf(P, fee):
    """每邊成本占契約價值比例。"""
    return TAX + (SLIP + fee / 50.0) / np.asarray(P, float)


def cl_stats(x, m):
    x = np.asarray(x, float); m = np.asarray(m)
    ok = np.isfinite(x); x = x[ok]; m = m[ok]
    n = len(x)
    if n == 0:
        return {"n": 0}
    mean = float(x.mean()); d = x - mean
    s = pd.Series(d).groupby(m).sum().to_numpy()
    se = float(np.sqrt((s ** 2).sum()) / n)
    return {"n": n, "mean": mean, "se": se, "lo": mean - 1.96 * se, "hi": mean + 1.96 * se, "months": int(len(s)),
            "win": float((x > 0).mean())}


# ═════════════ 資料 ═════════════
def load_fut(prod):
    fs = sorted(glob.glob(f"{PRIV}/fut_daily/{prod}/*.csv"))
    d = pd.concat([pd.read_csv(f, dtype=str, keep_default_na=False) for f in fs], ignore_index=True)
    d = d[(d["is_spread"] == "0") & (d["is_weekly"] == "0") & (d["dup_seq"].isin(["", "1"]))].copy()
    for k in ("open", "high", "low", "close", "settle"):
        d[k] = pd.to_numeric(d[k], errors="coerce")
    for k in ("open", "high", "low", "close"):
        d.loc[~(d[k] > 0), k] = np.nan
    g = d[d["session"] == "一般"]; ng = d[d["session"] == "盤後"]
    days = np.array(sorted(g["date"].unique()))
    exps = np.array(sorted(g["expiry"].unique()))
    di = {x: i for i, x in enumerate(days)}; ei = {x: j for j, x in enumerate(exps)}
    sh = (len(days), len(exps))
    F = {"prod": prod, "days": days, "exps": exps}
    r = g["date"].map(di).to_numpy(); c = g["expiry"].map(ei).to_numpy()
    for k, col in (("O", "open"), ("H", "high"), ("L", "low"), ("C", "close"), ("S", "settle")):
        a = np.full(sh, np.nan); a[r, c] = g[col].to_numpy(float); F[k] = a
    ng = ng[ng["date"].isin(di) & ng["expiry"].isin(ei)]
    r = ng["date"].map(di).to_numpy(); c = ng["expiry"].map(ei).to_numpy()
    for k, col in (("NO", "open"), ("NH", "high"), ("NL", "low"), ("NC", "close")):
        a = np.full(sh, np.nan); a[r, c] = ng[col].to_numpy(float); F[k] = a
    pres = np.zeros(sh, bool); pres[g["date"].map(di).to_numpy(), g["expiry"].map(ei).to_numpy()] = True
    n = len(days)
    ld = np.array([int(np.flatnonzero(pres[:, j]).max()) for j in range(len(exps))])
    live = ld == n - 1
    ld = np.where(live, n + np.arange(len(exps)), ld)
    assert np.all(np.diff(ld) > 0), "到期日須隨到期月份遞增"
    F["lastday"] = ld; F["live"] = live
    S = F["S"]
    F["SP"] = np.where(S > 0, S, F["C"])
    rows = np.arange(n)
    F["settle_src"] = {"到期次數": int((~live).sum()),
                       "結算價欄有值": int(sum(1 for j in np.flatnonzero(~live) if S[ld[j], j] > 0)),
                       "以收盤代表": int(sum(1 for j in np.flatnonzero(~live) if not (S[ld[j], j] > 0)))}
    return F


def load_margin(days):
    m = pd.read_csv(f"{PRIV}/margin/history_tx_mtx_tmf.csv", dtype=str)
    m = m[m["product"] == "TX"].sort_values("effective_date")
    eff = m["effective_date"].to_numpy(); im = m["initial_after"].astype(float).to_numpy(); mm = m["maintenance_after"].astype(float).to_numpy()
    k = np.searchsorted(eff, days, side="right") - 1
    IM = np.where(k >= 0, im[np.maximum(k, 0)], np.nan); MM = np.where(k >= 0, mm[np.maximum(k, 0)], np.nan)
    return IM, MM


def load_rate(days):
    r = pd.read_csv(f"{PRIV}/rates/bot_1y_deposit_monthly.csv", dtype=str)
    mp = dict(zip(r["ym"], r["fixed_1y_time_deposit"].astype(float)))
    last = max(mp)
    out = np.full(len(days), np.nan); ext = 0
    for i, d in enumerate(days):
        ym = d[:7]
        if ym in mp:
            out[i] = mp[ym]
        elif ym > last:
            out[i] = mp[last]; ext += 1
    return out / 100.0, {"最後月": last, "延用天數": ext}


def load_taiex():
    t = pd.read_csv(TAIEX_CSV, dtype={"date": str})
    t["close"] = pd.to_numeric(t["close"], errors="coerce")
    t = t[t["close"] > 0].drop_duplicates("date").sort_values("date")
    return t["date"].to_numpy(), t["close"].to_numpy(float)


def git(*a):
    return subprocess.run(["git", "-C", DB, *a], capture_output=True, text=True, check=True).stdout


def etf_close(sid, snap=SNAP):
    """還原收盤（日期字串 → 值）：主快照（data.load_stock）＋ 2015 以前 early（researchRev.market_series 同接法）。"""
    from backtest import data as D
    old = D.DATA; D.DATA = snap
    try:
        cal = D.load_calendar(); st = D.load_stock(sid, "twse", cal)
        raw = pd.read_csv(os.path.join(snap, "stocks", f"{sid}.csv"), dtype={"date": str}, usecols=["date", "close"]).drop_duplicates("date")
    finally:
        D.DATA = old
    c = st.df["close"]; c.index = [str(x.date()) for x in c.index]
    c = c.dropna()
    raw["close"] = pd.to_numeric(raw["close"], errors="coerce"); raw = raw.set_index("date")["close"]
    first = c.index[0]; s = float(c.iloc[0] / raw[first])
    rows = git("grep", "-h", f"_{sid},", EARLY_SHA, "--", "data/early/daily/")
    cols = ["key", "date", "stock_id", "name", "market", "open", "high", "low", "close", "volume", "amount", "change", "limit",
            "shares", "transactions", "price_basis", "last_price"]
    e = pd.read_csv(io.StringIO(rows), header=None, names=cols, dtype=str)
    e = e[e["stock_id"] == sid].copy(); e["close"] = pd.to_numeric(e["close"], errors="coerce")
    e = e[(e["close"] > 0) & (e["date"] < first)].sort_values("date").drop_duplicates("date")
    try:
        ex = git("grep", "-h", f",{sid},", EARLY_SHA, "--", "data/early/exright/")
    except subprocess.CalledProcessError:
        ex = ""
    if ex.strip():
        x = pd.read_csv(io.StringIO(ex), header=None, names=["date", "stock_id", "pre_close", "ref_price", "value", "kind", "open_base",
                                                            "limit_up", "limit_down", "ex_div_ref"], dtype={"date": str, "stock_id": str})
        x = x[x["stock_id"] == sid]
        f = x["ref_price"].astype(float).to_numpy() / x["pre_close"].astype(float).to_numpy(); evd = x["date"].to_numpy()
    else:
        f = np.zeros(0); evd = np.zeros(0, dtype=str)
    Fc = np.array([np.prod(f[evd > d]) for d in e["date"].to_numpy()]) if len(e) else np.zeros(0)
    early = pd.Series(e["close"].to_numpy(float) * Fc * s, index=e["date"].to_numpy())
    return pd.concat([early, c]).sort_index(), {"早年首日": str(early.index[0]) if len(early) else None, "主快照首日": first,
                                               "早年除息筆數": int(len(f)), "接點比例": s}


def daily(F, kroll=1, fee=50.0):
    """持有契約的逐日量（kroll＝1 主版：到期日收盤轉；2：到期前一日收盤轉）。"""
    n = len(F["days"]); ld = F["lastday"]; t = np.arange(n)
    h = np.searchsorted(ld, t + kroll)
    hp = np.r_[h[0], h[:-1]]
    at_ld = ld[hp] == t
    mark = np.where(at_ld, F["SP"][t, hp], F["C"][t, hp])
    entry = F["C"][t, h]
    roll = h != hp; roll[0] = False
    ref = np.where(roll, entry, mark); ref[0] = entry[0]
    refp = np.r_[np.nan, ref[:-1]]
    r = mark / refp - 1.0
    low = np.fmin(F["L"][t, hp], F["NL"][t, hp])
    lowr = low / refp - 1.0
    assert np.all(np.isfinite(r[1:])), "持有契約收盤有缺"
    assert np.all(np.isfinite(entry[roll])), "轉倉日次月收盤有缺"
    lowr = np.where(np.isfinite(lowr), np.minimum(lowr, r), r)
    cfx = np.where(roll, cf(mark, fee), 0.0); cfe = np.where(roll, cf(entry, fee), 0.0); cfe[0] = cf(entry[0], fee)
    adjC = np.cumprod(np.r_[1.0, 1.0 + r[1:]])
    adjCp = np.r_[np.nan, adjC[:-1]]
    O = F["O"][t, hp]; NC = F["NC"][t, hp]
    return {"days": F["days"], "h": h, "hp": hp, "mark": mark, "entry": entry, "roll": roll, "ref": ref, "r": r, "lowr": lowr,
            "cfx": cfx, "cfe": cfe, "adjC": adjC, "adjO": adjCp * O / refp, "adjNC": adjCp * NC / refp,
            "rawO": O, "rawC": F["C"][t, hp], "rawNC": NC, "at_ld": at_ld}


# ═════════════ 甲 ═════════════
def run_path(Dd, IM, MM, rate, t0, t1, L, rebal=True):
    days = Dd["days"]; r = Dd["r"]; lowr = Dd["lowr"]; roll = Dd["roll"]; mark = Dd["mark"]; ref = Dd["ref"]; entry = Dd["entry"]
    V = float(L); E = 1.0 - V * Dd["_cf0"]       # 起點 t0 收盤進場（_cf0 ＝ t0 收盤價的每邊成本）
    u = np.full(len(days), np.nan); u[t0] = 1.0
    calls = 0; wipes = 0; dep_tot = 0.0; costs = V * Dd["_cf0"]; intr = 0.0
    dts = pd.to_datetime(pd.Series(days))
    cd = np.r_[0, np.diff(dts.to_numpy()).astype("timedelta64[D]").astype(int)]
    Eprev = E
    for t in range(t0 + 1, t1 + 1):
        imf = IM[t - 1] / (MULT * ref[t - 1]) if np.isfinite(IM[t - 1]) else 0.0
        it = max(E - imf * V, 0.0) * (rate[t - 1] if np.isfinite(rate[t - 1]) else 0.0) * cd[t] / 365.0
        if E + V * lowr[t] <= 0:
            wipes += 1
        E = E + V * r[t] + it; V = V * (1.0 + r[t]); intr += it
        dep = 0.0
        if np.isfinite(MM[t]) and E < MM[t] / (MULT * mark[t]) * V:
            calls += 1
            dep = IM[t] / (MULT * mark[t]) * V - E
            E += dep; dep_tot += dep
        if roll[t]:
            c1 = V * Dd["cfx"][t]; E -= c1
            Vn = L * E if rebal else V * entry[t] / mark[t]
            c2 = Vn * Dd["cfe"][t]; E -= c2; V = Vn; costs += c1 + c2
        u[t] = u[t - 1] * (E - dep) / Eprev
        Eprev = E
    return u, {"追繳次數": calls, "賠光日數": wipes, "補入合計（×期初）": dep_tot, "成本合計（×期初）": costs, "利息合計（×期初）": intr}


def seg_metrics(days, u, a, b):
    i0 = int(np.searchsorted(days, a)) - 1; i1 = int(np.searchsorted(days, b, side="right")) - 1
    i0 = max(i0, int(np.flatnonzero(np.isfinite(u))[0]))
    w = u[i0:i1 + 1]
    cdays = (pd.Timestamp(str(days[i1])) - pd.Timestamp(str(days[i0]))).days
    cagr = (w[-1] / w[0]) ** (365.25 / cdays) - 1.0
    mdd = float(np.min(w / np.maximum.accumulate(w) - 1.0))
    lr = np.diff(np.log(w)); vol = float(np.std(lr, ddof=1) * math.sqrt(252))
    return {"起": str(days[i0 + 1]), "迄": str(days[i1]), "交易日": int(i1 - i0), "年化": float(cagr), "最大回落": mdd,
            "回落比": float(cagr / abs(mdd)) if mdd < 0 else float("inf"), "年化波動": vol, "年化÷波動": float(cagr / vol) if vol > 0 else float("nan")}


def judge_user(f, e):
    c1 = f["年化"] > e["年化"]; c2 = f["回落比"] >= e["回落比"]
    return "合格" if (c1 and c2) else ("另列" if c1 else "不合格")


def yearly(days, u, a, b):
    s = pd.Series(u, index=pd.to_datetime(days)).dropna()
    s = s[(s.index >= pd.Timestamp(a) - pd.Timedelta(days=15)) & (s.index <= pd.Timestamp(b))]
    ye = s.groupby(s.index.year).last()
    out = {}
    yrs = sorted(set(s.index.year))
    for y in yrs:
        if y < int(a[:4]):
            continue
        prev = s[s.index.year < y]
        if not len(prev):
            continue
        out[y] = float(ye[y] / prev.iloc[-1] - 1.0)
    return out


def monthly_log(days, u):
    s = pd.Series(u, index=pd.to_datetime(days)).dropna()
    me = s.groupby([s.index.year, s.index.month]).last()
    lr = np.log(me).diff().dropna()
    return lr


def part_A(F, IM, MM, rate, rinfo, etf):
    days = F["days"]
    t0 = int(np.searchsorted(days, A_START)) - 1; t1 = int(np.searchsorted(days, END, side="right")) - 1
    e50 = etf["0050"].reindex(days).ffill().to_numpy(float)
    e631 = etf["00631L"].reindex(days).ffill().to_numpy(float)
    miss50 = int(etf["0050"].reindex(days[t0:t1 + 1]).isna().sum())
    r50 = np.r_[np.nan, e50[1:] / e50[:-1] - 1.0]
    syn2 = np.full(len(days), np.nan); syn2[t0] = 1.0
    for t in range(t0 + 1, t1 + 1):
        syn2[t] = syn2[t - 1] * (1.0 + 2.0 * r50[t])
    bench = {"0050": e50, "00631L": e631, "0050×2合成": syn2}
    paths = {}; info = {}
    for rk, kroll in (("結算日轉倉", 1), ("結算前一日轉倉", 2)):
        for fk, fee in FEES.items():
            Dd = daily(F, kroll, fee); Dd["_cf0"] = float(cf(Dd["entry"][t0], fee))
            for rb in ("每月調回", "不調"):
                for L in (1, 2):
                    key = f"L{L}|{rk}|{rb}|手續費{fk}"
                    u, st = run_path(Dd, IM, MM, rate, t0, t1, L, rebal=(rb == "每月調回"))
                    paths[key] = u; info[key] = st
    np.savez_compressed(os.path.join(WORK, "A_paths.npz"), days=days, **{k.replace("|", "__"): v for k, v in paths.items()}, e50=e50, e631=e631, syn2=syn2)
    rows = []
    for key, u in paths.items():
        L = int(key[1])
        for seg, (a, b) in A_SEG.items():
            m = seg_metrics(days, u, a, b)
            for bn in (("0050",) if L == 1 else ("0050", "00631L", "0050×2合成")):
                bu = bench[bn]
                if seg == "早年" and bn == "00631L":
                    continue
                mb = seg_metrics(days, bu, a, b)
                yf = yearly(days, u, a, b); yb = yearly(days, bu, a, b)
                ys = sorted(set(yf) & set(yb)); dif = np.array([yf[y] - yb[y] for y in ys])
                lf = monthly_log(days, u); lb = monthly_log(days, bu)
                j = lf.index.intersection(lb.index)
                j = [k for k in j if pd.Timestamp(year=k[0], month=k[1], day=1) >= pd.Timestamp(a[:8] + "01") and pd.Timestamp(year=k[0], month=k[1], day=1) <= pd.Timestamp(b)]
                dm = pd.Series({k: lf[k] - lb[k] for k in j})
                byy = {}
                for (y, mo), v in dm.items():
                    byy.setdefault(y, [0.0, 0.0]); byy[y][0 if 6 <= mo <= 9 else 1] += v
                rows.append({"變體": key, "段": seg, "對照": bn, "期貨_年化": m["年化"], "期貨_回落": m["最大回落"], "期貨_回落比": m["回落比"],
                             "期貨_波動": m["年化波動"], "期貨_年化÷波動": m["年化÷波動"],
                             "ETF_年化": mb["年化"], "ETF_回落": mb["最大回落"], "ETF_回落比": mb["回落比"], "ETF_波動": mb["年化波動"], "ETF_年化÷波動": mb["年化÷波動"],
                             "年化差": m["年化"] - mb["年化"], "判準": judge_user(m, mb) if bn == "0050" else "（描述）",
                             "每年差_平均": float(dif.mean()) if len(dif) else np.nan,
                             "每年差_lo": float(dif.mean() - 1.96 * dif.std(ddof=1) / math.sqrt(len(dif))) if len(dif) > 1 else np.nan,
                             "每年差_hi": float(dif.mean() + 1.96 * dif.std(ddof=1) / math.sqrt(len(dif))) if len(dif) > 1 else np.nan,
                             "年數": len(dif), "6～9月差_年均": float(np.mean([v[0] for v in byy.values()])) if byy else np.nan,
                             "其餘月差_年均": float(np.mean([v[1] for v in byy.values()])) if byy else np.nan,
                             "窗": f"{m['起']}～{m['迄']}", "交易日": m["交易日"]})
    C = pd.DataFrame(rows); C.to_csv(os.path.join(OUT, "A_cells.csv"), index=False, float_format="%.10g")
    main = C[(C["變體"] == "L2|結算日轉倉|每月調回|手續費高") & (C["對照"] == "0050")].set_index("段")
    per = {s: main.loc[s, "判準"] for s in A_SEG}
    if per["探索"] == "合格" and per["確認"] == "合格":
        lab = "合格"
    elif per["探索"] in ("合格", "另列") and per["確認"] in ("合格", "另列"):
        lab = "另列"
    else:
        lab = "不合格"
    # 轉倉價差（描述）
    Dm = daily(F, 1, 50.0)
    rr = np.flatnonzero(Dm["roll"])
    gap = (Dm["entry"][rr] / Dm["mark"][rr] - 1.0)
    gy = pd.Series(gap, index=pd.to_datetime(days[rr]))
    gap_desc = {}
    for seg, (a, b) in A_SEG.items():
        g = gy[(gy.index >= a) & (gy.index <= b)]
        gap_desc[seg] = {"轉倉次數": int(len(g)), "每年加總平均（正＝正價差＝做多吃虧）": float(g.groupby(g.index.year).sum().mean()),
                         "逆價差占比": float((g < 0).mean()), "單次中位": float(g.median())}
    # 除息季的價差（描述）：6～9 月 vs 其餘
    for seg, (a, b) in A_SEG.items():
        g = gy[(gy.index >= a) & (gy.index <= b)]
        gap_desc[seg]["6～9 月轉倉 每年加總平均"] = float(g[(g.index.month >= 6) & (g.index.month <= 9)].groupby(g[(g.index.month >= 6) & (g.index.month <= 9)].index.year).sum().mean())
    S = {"判定": {"格": "L2｜結算日轉倉｜每月調回｜手續費高 vs 0050", "各段": per, "標籤": lab,
                "早年方向": main.loc["早年", "判準"]},
         "主表": {seg: main.loc[seg, ["期貨_年化", "期貨_回落", "期貨_回落比", "ETF_年化", "ETF_回落", "ETF_回落比", "期貨_波動", "ETF_波動", "期貨_年化÷波動", "ETF_年化÷波動", "窗"]].to_dict() for seg in A_SEG},
         "帳戶事件": info, "轉倉價差": gap_desc, "利率": rinfo, "0050 在 TX 交易日缺值天數": miss50,
         "先驗①": {"L1 與 0050 年化差在 ±1 點內（三段都要）": None, "L2 判 另列": lab == "另列"}}
    td, tc = load_taiex()
    ix = pd.Series(tc, index=td).reindex(days).ffill().to_numpy(float)
    S["加權指數（不含息，描述）"] = {seg: {k: v for k, v in seg_metrics(days, ix, a, b).items() if k in ("年化", "最大回落", "回落比")} for seg, (a, b) in A_SEG.items()}
    full = C[(C["變體"] == "L1|結算日轉倉|每月調回|手續費高") & (C["對照"] == "0050")]
    S["先驗①"]["L1 與 0050 年化差（各段）"] = dict(zip(full["段"], full["年化差"]))
    S["先驗①"]["L1 與 0050 年化差在 ±1 點內（三段都要）"] = bool(all(abs(x) <= 0.01 for x in full["年化差"]))
    return S, C


def consist(Fx, Ftx):
    """MTX／TMF 主版連續日報酬 vs TX（同日）。"""
    Da = daily(Fx, 1, 50.0); Db = daily(Ftx, 1, 50.0)
    a = pd.Series(Da["r"], index=Da["days"]).iloc[1:]; b = pd.Series(Db["r"], index=Db["days"]).iloc[1:]
    j = a.index.intersection(b.index); j = [d for d in j if d <= END]
    x = a[j].to_numpy(); y = b[j].to_numpy()
    yrs = (pd.Timestamp(j[-1]) - pd.Timestamp(j[0])).days / 365.25
    return {"起": j[0], "迄": j[-1], "共同日": len(j), "日報酬相關": float(np.corrcoef(x, y)[0, 1]), "平均絕對差（點數比例）": float(np.mean(np.abs(x - y))),
            "年化差（本商品 − TX）": float(np.prod(1 + x) ** (1 / yrs) - np.prod(1 + y) ** (1 / yrs))}


# ═════════════ 乙 ═════════════
def build_B(F, IM, MM):
    """合併時間軸：1990～1998-07-20 加權指數推算；1998-07-21 起 TX 主版。"""
    td, tc = load_taiex()
    Dd = daily(F, 1, 50.0)
    days = F["days"]
    pre = td < TX0
    d_idx = td[pre]; c_idx = tc[pre]
    n0 = len(d_idx)
    r0 = np.r_[np.nan, c_idx[1:] / c_idx[:-1] - 1.0]
    # 調倉日：每月第 3 個星期三當天或之後第一個交易日
    dd = pd.to_datetime(pd.Series(d_idx))
    roll0 = np.zeros(n0, bool)
    for (y, m), g in dd.groupby([dd.dt.year, dd.dt.month]):
        first = pd.Timestamp(year=y, month=m, day=1)
        w3 = first + pd.Timedelta(days=(2 - first.weekday()) % 7 + 14)
        k = g[g >= w3]
        if len(k):
            roll0[k.index[0]] = True
    # 接點日（TX 首日）：加權指數報酬、收盤進 TX
    ti = int(np.searchsorted(td, days[0]))
    assert td[ti] == days[0]
    rj = tc[ti] / tc[ti - 1] - 1.0
    B = {"days": np.r_[d_idx, days], "r": np.r_[r0, rj, Dd["r"][1:]], "lowr": np.r_[r0, rj, Dd["lowr"][1:]],
         "roll": np.r_[roll0, True, Dd["roll"][1:]], "cfx": np.r_[np.zeros(n0), 0.0, Dd["cfx"][1:]],
         "cfe": np.r_[np.zeros(n0), cf(Dd["entry"][0], 50.0), Dd["cfe"][1:]],
         "mmf": np.r_[np.full(n0, np.nan), MM / (MULT * Dd["mark"])], "imf": np.r_[np.full(n0, np.nan), IM / (MULT * Dd["mark"])],
         "imf_post": np.r_[np.full(n0, np.nan), IM / (MULT * Dd["ref"])], "era": np.r_[np.zeros(n0, int), np.ones(len(days), int)],
         "cf0": np.r_[np.zeros(n0), cf(Dd["ref"], 50.0)]}
    B["mmf"][n0] = np.nan; B["imf"][n0] = np.nan
    return B


def run_starts(B, L, topup, imonly=False, t_end=None):
    n = len(B["days"]); W = B_W
    if t_end is None:
        t_end = n - 1
    S = t_end - W + 1
    E = np.zeros(S); V = np.zeros(S); alive = np.zeros(S, bool)
    first_call = np.full(S, -1); ncall = np.zeros(S, int); dep = np.zeros(S); wiped = np.zeros(S, bool); final = np.full(S, np.nan)
    r, lowr, roll, cfx, cfe, mmf, imf, imfp, cf0 = (B[k] for k in ("r", "lowr", "roll", "cfx", "cfe", "mmf", "imf", "imf_post", "cf0"))
    for t in range(0, t_end + 1):
        a = max(0, t - W); b = min(t - 1, S - 1)
        if b >= a:
            sl = slice(a, b + 1)
            e = E[sl]; v = V[sl]; al = alive[sl]
            w = al & (e + v * lowr[t] <= 0)
            wiped[sl] |= w; al = al & ~w
            e = np.where(al, e + v * r[t], 0.0); v = np.where(al, v * (1.0 + r[t]), 0.0)
            if np.isfinite(mmf[t]):
                c = al & (e < mmf[t] * v)
                fc = first_call[sl]; fc[c & (fc < 0)] = t; first_call[sl] = fc
                ncall[sl] += c
                if topup:
                    d = np.where(c, imf[t] * v - e, 0.0); e = e + d; dep[sl] += d
            if roll[t]:
                e = e - v * cfx[t]
                if imonly:
                    vn = np.where(al, e / imfp[t], 0.0) if np.isfinite(imfp[t]) else np.where(al, L * e, 0.0)
                else:
                    vn = np.where(al, L * e, 0.0)
                e = e - vn * cfe[t]; v = vn
            E[sl] = e; V[sl] = v; alive[sl] = al
            s_fin = t - W
            if 0 <= s_fin < S:
                final[s_fin] = E[s_fin] if alive[s_fin] else 0.0
        if t < S:
            if imonly:
                if not np.isfinite(imfp[t]):
                    continue
                v0 = 1.0 / imfp[t]
            else:
                v0 = float(L)
            E[t] = 1.0 - v0 * cf0[t]; V[t] = v0; alive[t] = True
    return {"first_call": first_call, "ncall": ncall, "dep": dep, "wiped": wiped, "final": final, "S": S}


def part_B(F, IM, MM):
    B = build_B(F, IM, MM)
    days = B["days"]
    t_end = int(np.searchsorted(days, END, side="right")) - 1
    S = t_end - B_W + 1
    sd = days[:S]
    m_ok = np.array([d >= MARGIN0 for d in sd])
    groups = {"全期（1990 起，含推算）": np.ones(S, bool), "推算段起點（1990-01～1998-07-20）": sd < TX0,
              "期貨段起點（1998-07-21 起）": sd >= TX0, "保證金有資料（2004-09-30 起）": m_ok}
    for y in (1990, 2000, 2008, 2020, 2022):
        groups[f"{y} 年起點"] = np.array([d[:4] == str(y) for d in sd])
    rows = []; worst = {}
    np_save = {}
    for L in B_LS:
        R0 = run_starts(B, L, topup=False, t_end=t_end); R1 = run_starts(B, L, topup=True, t_end=t_end)
        np_save[f"L{L}_final"] = R0["final"]; np_save[f"L{L}_fc"] = R0["first_call"]
        for g, msk in groups.items():
            if not msk.any():
                continue
            fin = R0["final"][msk]
            row = {"L": L, "起點組": g, "起點數": int(msk.sum()), "起": str(sd[msk][0]), "迄": str(sd[msk][-1]),
                   "不補_一年內賠光比例": float(R0["wiped"][msk].mean()), "不補_一年後權益中位": float(np.median(fin)) - 1.0,
                   "不補_一年後權益最差": float(fin.min()) - 1.0, "不補_最差起點（同為賠光取最早）": str(sd[msk][int(np.argmin(fin))]), "不補_賠光起點數": int(R0["wiped"][msk].sum())}
            mm = msk & m_ok
            if mm.any():
                row.update({"追繳_有資料起點數": int(mm.sum()), "一年內碰到追繳比例": float((R0["first_call"][mm] >= 0).mean()),
                            "補足_平均追繳次數": float(R1["ncall"][mm].mean()), "補足_平均補入（×期初）": float(R1["dep"][mm].mean()), "補足_補入中位（×期初）": float(np.median(R1["dep"][mm])),
                            "補足_一年內賠光比例": float(R1["wiped"][mm].mean())})
            else:
                row.update({"追繳_有資料起點數": 0, "一年內碰到追繳比例": "無資料", "補足_平均追繳次數": "無資料", "補足_平均補入（×期初）": "無資料", "補足_補入中位（×期初）": "無資料",
                            "補足_一年內賠光比例": "無資料"})
            if g.startswith("推算"):
                row["註"] = "推算：加權指數收盤同幅度、無最低價、無保證金"
            rows.append(row)
    # 描述版：只放原始保證金
    R2 = run_starts(B, 0, topup=False, imonly=True, t_end=t_end); R3 = run_starts(B, 0, topup=True, imonly=True, t_end=t_end)
    lev = 1.0 / B["imf_post"][B["roll"] & np.isfinite(B["imf_post"])]
    msk = m_ok
    rows.append({"L": "只放原始保證金", "起點組": "保證金有資料（2004-09-30 起）", "起點數": int(msk.sum()), "起": str(sd[msk][0]), "迄": str(sd[msk][-1]),
                 "不補_一年內賠光比例": float(R2["wiped"][msk].mean()), "不補_一年後權益中位": float(np.median(R2["final"][msk])) - 1.0,
                 "不補_一年後權益最差": float(R2["final"][msk].min()) - 1.0, "不補_最差起點（同為賠光取最早）": str(sd[msk][int(np.argmin(R2["final"][msk]))]), "不補_賠光起點數": int(R2["wiped"][msk].sum()),
                 "追繳_有資料起點數": int(msk.sum()), "一年內碰到追繳比例": float((R2["first_call"][msk] >= 0).mean()),
                 "補足_平均追繳次數": float(R3["ncall"][msk].mean()), "補足_平均補入（×期初）": float(R3["dep"][msk].mean()), "補足_補入中位（×期初）": float(np.median(R3["dep"][msk])),
                 "補足_一年內賠光比例": float(R3["wiped"][msk].mean()),
                 "註": f"倍數＝契約價值÷原始保證金；調倉時中位 {np.median(lev):.1f} 倍（範圍 {lev.min():.1f}～{lev.max():.1f}）"})
    np.savez_compressed(os.path.join(WORK, "B_starts.npz"), days=sd, **np_save)
    C = pd.DataFrame(rows); C.to_csv(os.path.join(OUT, "B_cells.csv"), index=False, float_format="%.10g")
    g14 = C[(C["L"] == 14) & (C["起點組"] == "保證金有資料（2004-09-30 起）")].iloc[0]
    g3 = C[(C["L"] == 3)]
    S_ = {"先驗②": {"L14 一年內碰到追繳比例 ＞ 90%": bool(g14["一年內碰到追繳比例"] > 0.9),
                    "L3 遇 2008 型賠光（2008 年起點 不補路 賠光比例 ＞ 0）": bool(float(g3[g3["起點組"] == "2008 年起點"]["不補_一年內賠光比例"].iloc[0]) > 0)},
          "時間軸": {"推算段": [str(days[0]), "1998-07-20"], "TX 段": [TX0, str(days[t_end])], "起點數": int(S)}}
    return S_, C


# ═════════════ 丙 ═════════════
def pct_prior(x, W=250):
    """x 的每個有效值在它之前 W 個有效值中的位置（＜ 的比例）；不足 W 個 ⇒ NaN。回傳與 x 同長。"""
    out = np.full(len(x), np.nan)
    idx = np.flatnonzero(np.isfinite(x))
    v = x[idx]
    for k in range(W, len(idx)):
        out[idx[k]] = float(np.mean(v[k - W:k] < v[k]))
    return out


def part_C(F):
    Dd = daily(F, 1, 50.0)
    days = Dd["days"]; t = np.arange(len(days)); hp = Dd["hp"]
    Cp = np.r_[np.nan, F["C"][t[1:] - 1, hp[1:]]]
    NCt = F["NC"][t, hp]; Ot = F["O"][t, hp]; Ct = F["C"][t, hp]
    n = NCt / Cp - 1.0; d = Ct / Ot - 1.0; d2 = Ct / NCt - 1.0
    n[days < NIGHT0] = np.nan
    p = pct_prior(n)
    grp = np.where(np.isfinite(p), np.minimum(9, np.floor(p * 10)), np.nan)
    cost_hi = 2 * cf(Ot, FEES["高"]); cost_lo = 2 * cf(Ot, FEES["低"])
    ev = pd.DataFrame({"date": days, "n": n, "d": d, "d2": d2, "p": p, "grp": grp, "cost_hi": cost_hi, "cost_lo": cost_lo})
    ev = ev[np.isfinite(ev["grp"]) & np.isfinite(ev["d"]) & np.isfinite(ev["d2"])].copy()
    ev["月"] = ev["date"].str[:7]
    ev.to_csv(os.path.join(WORK, "C_days.csv.gz"), index=False)
    rows = []
    for seg, (a, b) in C_SEG.items():
        s = ev[(ev["date"] >= a) & (ev["date"] <= b)]
        for y in ("d", "d2"):
            base = float(s[y].mean())
            for gname, gv in (("最高組", 9), ("最低組", 0)):
                x = s[s["grp"] == gv]
                st = cl_stats(x[y] - base, x["月"])
                rows.append({"段": seg, "格": f"{y}｜{gname}", "n": st["n"], "全部日平均": base, "組平均": float(x[y].mean()), "X": st["mean"], "lo": st["lo"], "hi": st["hi"],
                             "月數": st["months"], "方向": ("延續" if (st["mean"] > 0) == (gv == 9) else "反轉"), "CI不跨0": bool(st["lo"] > 0 or st["hi"] < 0),
                             "起": str(s["date"].iloc[0]), "迄": str(s["date"].iloc[-1]), "有分組日數": int(len(s))})
        for ck, cc in (("高", "cost_hi"), ("低", "cost_lo")):
            for gname, gv, sign in (("最高組買", 9, 1), ("最低組賣", 0, -1)):
                x = s[s["grp"] == gv]
                st = cl_stats(sign * x["d"] - x[cc], x["月"])
                rows.append({"段": seg, "格": f"交易｜{gname}｜手續費{ck}", "n": st["n"], "X": st["mean"], "lo": st["lo"], "hi": st["hi"], "月數": st["months"],
                             "勝率": st["win"], "平均來回成本": float(x[cc].mean()), "CI不跨0": bool(st["lo"] > 0 or st["hi"] < 0)})
    C = pd.DataFrame(rows); C.to_csv(os.path.join(OUT, "C_cells.csv"), index=False, float_format="%.10g")
    J = {}
    for y in ("d", "d2"):
        for gname in ("最高組", "最低組"):
            k = f"{y}｜{gname}"
            a_ = C[(C["段"] == "探索") & (C["格"] == k)].iloc[0]; b_ = C[(C["段"] == "確認") & (C["格"] == k)].iloc[0]
            ok = bool(a_["CI不跨0"] and b_["CI不跨0"] and np.sign(a_["X"]) == np.sign(b_["X"]))
            J[k] = {"成立": ok, "方向": a_["方向"] if ok else f"探索{a_['方向']}／確認{b_['方向']}", "探索X": a_["X"], "確認X": b_["X"]}
    for gname in ("最高組買", "最低組賣"):
        k = f"交易｜{gname}｜手續費高"
        a_ = C[(C["段"] == "探索") & (C["格"] == k)].iloc[0]; b_ = C[(C["段"] == "確認") & (C["格"] == k)].iloc[0]
        J[k] = {"可交易": bool(a_["lo"] > 0 and b_["lo"] > 0), "探索平均": a_["X"], "確認平均": b_["X"], "探索lo": a_["lo"], "確認lo": b_["lo"]}
    nyes = sum(1 for k, v in J.items() if v.get("成立") or v.get("可交易"))
    S = {"判定": J, "N_單筆": 6, "成立格數": nyes,
         "先驗③": {"有延續或反轉": any(v.get("成立") for v in J.values()), "扣成本不可交易": not any(v.get("可交易") for v in J.values())},
         "描述": {"夜盤報酬標準差（全期有分組日）": float(ev["n"].std()), "日盤報酬標準差": float(ev["d"].std()),
                "n 與 d 相關": float(np.corrcoef(ev["n"], ev["d"])[0, 1]), "n 與 d2 相關": float(np.corrcoef(ev["n"], ev["d2"])[0, 1])}}
    return S, C


# ═════════════ 丁 ═════════════
def part_D(F, Fm):
    Dd = daily(F, 1, 50.0)
    days = Dd["days"]; nd = len(days)
    pc = pd.read_csv(f"{PRIV}/pc_ratio.csv", dtype=str).set_index("date")
    x3 = pd.to_numeric(pc["pc_oi_ratio_pct"], errors="coerce").reindex(days).to_numpy(float)
    x4 = pd.to_numeric(pc["pc_volume_ratio_pct"], errors="coerce").reindex(days).to_numpy(float)
    aC = Dd["adjC"]; aO = Dd["adjO"]
    HS = (1, 5, 20)
    R = {}
    for H in HS:
        r = np.full(nd, np.nan)
        for t in range(nd - H):
            r[t] = aC[t + H] / aO[t + 1] - 1.0
        R[H] = r
    def cells(xname, x, segs, label=""):
        p = pct_prior(x)
        rows = []; evs = []
        for seg, (a, b) in segs.items():
            for H in HS:
                ok = np.array([(t + H < nd) and days[min(t + 1, nd - 1)] >= a and days[min(t + H, nd - 1)] <= b and np.isfinite(p[t]) and np.isfinite(R[H][t])
                               for t in range(nd)])
                hi = ok & (p >= 0.9); lo = ok & (p < 0.1)
                mon = np.array([d[:7] for d in days])
                sh = cl_stats(R[H][hi], mon[hi]); sl = cl_stats(R[H][lo], mon[lo])
                if sh["n"] and sl["n"]:
                    dif = sh["mean"] - sl["mean"]; se = math.sqrt(sh["se"] ** 2 + sl["se"] ** 2)
                else:
                    dif = se = np.nan
                rows.append({"指標": xname, "段": seg, "H": H, "最高10%_n": sh["n"], "最低10%_n": sl["n"], "最高10%_平均": sh.get("mean"), "最低10%_平均": sl.get("mean"),
                             "差": dif, "lo": dif - 1.96 * se, "hi": dif + 1.96 * se, "CI不跨0": bool(np.isfinite(se) and (dif - 1.96 * se > 0 or dif + 1.96 * se < 0)),
                             "全部日平均": float(np.nanmean(R[H][ok])), "起": str(days[np.flatnonzero(ok)[0]]) if ok.any() else None,
                             "迄": str(days[np.flatnonzero(ok)[-1]]) if ok.any() else None, "註": label})
                evs.append(pd.DataFrame({"指標": xname, "段": seg, "H": H, "date": days[hi | lo], "組": np.where(hi[hi | lo], "高", "低"), "R": R[H][hi | lo]}))
        return rows, evs
    r3, e3 = cells("x3 賣買權未平倉比", x3, D_SEG); r4, e4 = cells("x4 賣買權成交量比", x4, D_SEG)
    # x1／x2 描述
    def fx(prodfile, div):
        f = pd.read_csv(f"{PRIV}/inst_fut/{prodfile}", dtype=str)
        f = f[f["investor"] == "外資及陸資"].set_index("date")
        return pd.to_numeric(f["net_oi_volume"], errors="coerce") / div
    x1s = (fx("TXF.csv", 1.0) + fx("MXF.csv", 4.0)).reindex(days)
    x1 = x1s.to_numpy(float)
    x2 = np.r_[np.full(5, np.nan), x1[5:] - x1[:-5]]
    dseg = {"描述（F2 2023-10-05 起）": ("2023-10-05", END)}
    r1, e1 = cells("x1 外資淨未平倉（不可判定）", x1, dseg, "約 2 年、不可判定"); r2, e2 = cells("x2 外資淨未平倉 5 日變化（不可判定）", x2, dseg, "約 2 年、不可判定")
    pd.concat(e3 + e4 + e1 + e2).to_csv(os.path.join(WORK, "D_events.csv.gz"), index=False)
    C = pd.DataFrame(r3 + r4 + r1 + r2); C.to_csv(os.path.join(OUT, "D_cells.csv"), index=False, float_format="%.10g")
    J = {}
    for xn in ("x3 賣買權未平倉比", "x4 賣買權成交量比"):
        for H in HS:
            q = C[(C["指標"] == xn) & (C["H"] == H)].set_index("段")
            a_, b_, e_ = q.loc["探索"], q.loc["確認"], q.loc["早年"]
            ok = bool(a_["CI不跨0"] and b_["CI不跨0"] and np.sign(a_["差"]) == np.sign(b_["差"]))
            J[f"{xn}｜H{H}"] = {"有預測力": ok, "探索差": a_["差"], "確認差": b_["差"], "早年差": e_["差"],
                               "早年方向相反": bool(ok and np.sign(e_["差"]) != np.sign(a_["差"]))}
    S = {"判定": J, "N_單筆": 6, "成立格數": sum(v["有預測力"] for v in J.values()),
         "先驗④": {"四個指標都沒有預測力（可判的 x3、x4）": not any(v["有預測力"] for v in J.values())},
         "x1x2": "F2 只有 2023-10-05 起 ⇒ 只描述、不可判定"}
    return S, C


# ═════════════ 戊 ═════════════
def part_E(F):
    Dd = daily(F, 1, 50.0)
    days = Dd["days"]
    ex = [F["lastday"][j] for j in range(len(F["exps"])) if not F["live"][j]]
    ex = np.array(sorted(ex)); ex = ex[ex >= 3]
    td, tc = load_taiex()
    tpos = {d: i for i, d in enumerate(td)}
    series = {"加權指數": (td, tc), "TX 近月": (days, Dd["adjC"])}
    WINS = {"①結算週一～三（3 日）": (3, 0), "②結算日當天": (1, 0), "③結算後第一個交易日": (1, 1)}
    rows = []; evrows = []; skip = {}
    for sname, (dd, cc) in series.items():
        pos = {d: i for i, d in enumerate(dd)}
        epos = []
        for i in ex:
            d = days[i]
            if d in pos:
                epos.append(pos[d])
            else:
                skip[sname] = skip.get(sname, 0) + 1
        epos = np.array(epos)
        for wn, (k, off) in WINS.items():
            ends = epos + off
            ends = ends[(ends < len(cc)) & (ends - k >= 0)]
            Rall = np.full(len(cc), np.nan); Rall[k:] = cc[k:] / cc[:-k] - 1.0
            isev = np.zeros(len(cc), bool); isev[ends] = True
            for seg, (a, b) in E_SEG.items():
                inseg = (dd >= a) & (dd <= b)
                other = inseg & ~isev & np.isfinite(Rall)
                base = float(np.mean(Rall[other]))
                e_ = ends[inseg[ends]]
                x = Rall[e_] - base
                st = cl_stats(x, np.array([dd[i - off][:7] for i in e_]))
                rows.append({"序列": sname, "窗": wn, "段": seg, "n": st["n"], "事件平均": float(np.mean(Rall[e_])), "對照平均": base, "X": st["mean"],
                             "lo": st["lo"], "hi": st["hi"], "勝率（事件 > 0）": float(np.mean(Rall[e_] > 0)), "CI不跨0": bool(st["lo"] > 0 or st["hi"] < 0),
                             "對照窗數": int(other.sum())})
                evrows.append(pd.DataFrame({"序列": sname, "窗": wn, "段": seg, "end": dd[e_], "R": Rall[e_]}))
    pd.concat(evrows).to_csv(os.path.join(WORK, "E_events.csv.gz"), index=False)
    C = pd.DataFrame(rows); C.to_csv(os.path.join(OUT, "E_cells.csv"), index=False, float_format="%.10g")
    J = {}
    for wn in WINS:
        q = C[(C["序列"] == "加權指數") & (C["窗"] == wn)].set_index("段"); qt = C[(C["序列"] == "TX 近月") & (C["窗"] == wn)].set_index("段")
        ok = bool(q.loc["探索", "CI不跨0"] and q.loc["確認", "CI不跨0"] and np.sign(q.loc["探索", "X"]) == np.sign(q.loc["確認", "X"]))
        okt = bool(qt.loc["探索", "CI不跨0"] and qt.loc["確認", "CI不跨0"] and np.sign(qt.loc["探索", "X"]) == np.sign(qt.loc["確認", "X"]))
        J[wn] = {"有（加權指數）": ok, "TX 並報：兩段同號且不跨 0": okt, "探索X": q.loc["探索", "X"], "確認X": q.loc["確認", "X"], "早年X": q.loc["早年", "X"],
                 "TX 探索X": qt.loc["探索", "X"], "TX 確認X": qt.loc["確認", "X"],
                 "TX 與指數方向不同（探索／確認）": [bool(np.sign(qt.loc[s, "X"]) != np.sign(q.loc[s, "X"])) for s in ("探索", "確認")]}
    S = {"判定": J, "N_單筆": 3, "成立格數": sum(v["有（加權指數）"] for v in J.values()), "結算日不在序列的次數": skip,
         "先驗⑤": {"測不出": not any(v["有（加權指數）"] for v in J.values())}}
    return S, C


# ═════════════ 己 ═════════════
def part_F(F):
    from backtest import exit_signal as XS
    from backtest import data as D
    Dd = daily(F, 1, 50.0)
    tdays = Dd["days"]
    old = D.DATA; D.DATA = REV_SNAP
    try:
        cal = D.load_calendar(); st = D.load_stock("0050", "twse", cal)
    finally:
        D.DATA = old
    cal_s = np.array([str(x.date()) for x in cal])
    o50 = st.df["open"].to_numpy(float); c50 = st.df["close"].to_numpy(float)
    valid = np.isfinite(c50)
    lv = XS.last_valid(valid)
    tx = pd.DataFrame({"aC": Dd["adjC"], "aO": Dd["adjO"], "rawO": Dd["rawO"]}, index=tdays).reindex(cal_s)
    tx_missing = [d for d in cal_s if d >= "2017-03-02" and d <= "2026-08-24" and not np.isfinite(tx.loc[d, "aC"])]
    aC = tx["aC"].to_numpy(float); aO = tx["aO"].to_numpy(float); rawO = tx["rawO"].to_numpy(float)
    tvalid = np.isfinite(aC); tlv = XS.last_valid(tvalid)
    pos = {d: i for i, d in enumerate(cal_s)}
    w0, w1 = pos["2017-03-02"], pos["2026-08-24"]
    H = 20

    def fwd50(b):
        if b + H > w1 or not np.isfinite(o50[b + 1]):
            return np.nan
        return c50[lv[b + H]] / o50[b + 1] - 1.0

    def fwdtx(b):
        if b + H > w1 or not np.isfinite(aO[b + 1]):
            return np.nan
        return aC[tlv[b + H]] / aO[b + 1] - 1.0

    bd = np.array([d for d in range(w0, w1 - H + 1) if valid[d] and np.isfinite(o50[d + 1])], int)
    b50 = float(np.mean([fwd50(d) for d in bd])); btx = float(np.nanmean([fwdtx(d) for d in bd]))
    SR = json.load(open(os.path.join(HERE, "resultsRev", "summary.json"), encoding="utf-8"))
    z = SR["Bonferroni_大盤"]["z"]
    EV = pd.read_csv(os.path.join(HERE, "resultsRev", "events_market.csv"), dtype={"基準日": str}, float_precision="round_trip")
    EV = EV[(EV["層"] == "大盤") & (EV["段"] == "主窗")]
    CE = pd.read_csv(os.path.join(HERE, "resultsRev", "cells.csv"), float_precision="round_trip")
    CE = CE[(CE["層"] == "大盤") & (CE["段"] == "主窗")]
    rows = []; gate_bad = 0; evout = []
    for _, c in CE.iterrows():
        code, ver = c["code"], c["版"]
        e = EV[(EV["code"] == code) & (EV["版"] == ver)]
        b = np.array([pos[d] for d in e["基準日"]], int)
        g = (b - w0) // 20
        side = c["邊"]                                   # ⛔ 不 import researchRev（它會改 D.DATA 與 chdir）；邊、名取自原 cells.csv
        r50 = np.array([fwd50(x) for x in b]); rtx = np.array([fwdtx(x) for x in b])
        cost = 2 * cf(rawO[b + 1], FEES["高"]) if len(b) else np.zeros(0)
        sgn = 1.0 if side == "低" else -1.0
        out = {"code": code, "名": c["名"], "邊": side, "版": ver, "事件": int(len(b)), "原_判定": c["判定"], "原_出口": c["出口"], "原_結果": c["結果"]}
        if len(b):
            gate_bad += int(not np.allclose(r50, e["R20"].to_numpy(float), rtol=0, atol=1e-12))
        ne = int(min(len(b), len(np.unique(g)))) if len(b) else 0
        out["n_eff"] = ne
        for lab, x in (("0050原（不扣）", r50 - b50), ("0050扣期貨成本", r50 - b50 - sgn * cost), ("TX扣期貨成本", rtx - btx - sgn * cost), ("TX不扣", rtx - btx)):
            if ne >= 10:
                m, se, ng = XS.cr0(x, g)
                lo, hi = m - z * se, m + z * se
                exr, rs = XS.exit_result(m, lo, hi, len(x), ne)
                ok = (rs == "結果③") if side == "高" else (rs == "結果②")
                out.update({f"{lab}_X": m, f"{lab}_lo": lo, f"{lab}_hi": hi, f"{lab}_出口": exr, f"{lab}_結果": rs, f"{lab}_判定": "通過" if ok else "不通過"})
            else:
                out.update({f"{lab}_X": float(np.mean(x)) if len(x) else np.nan, f"{lab}_判定": "不可判定"})
        if ne >= 10:
            gate_bad += int(not (abs(out["0050原（不扣）_X"] - c["mean"]) <= 1e-12)) + int(out["0050原（不扣）_判定"] != c["判定"])
        rows.append(out)
        if len(b):
            evout.append(pd.DataFrame({"code": code, "版": ver, "基準日": e["基準日"].to_numpy(), "R20_TX": rtx, "cost": cost}))
    CR = pd.DataFrame(rows); CR.to_csv(os.path.join(OUT, "F_rev_cells.csv"), index=False, float_format="%.10g")
    pd.concat(evout).to_csv(os.path.join(WORK, "F_rev_events.csv.gz"), index=False)
    flipR = {"原不過、現過": int(((CR["原_判定"] == "不通過") & (CR["TX扣期貨成本_判定"] == "通過")).sum()),
             "原過、現不過": int(((CR["原_判定"] == "通過") & (CR["TX扣期貨成本_判定"] != "通過")).sum()),
             "現過格數": int((CR["TX扣期貨成本_判定"] == "通過").sum()), "可判定格數": int((CR["n_eff"] >= 10).sum())}
    # ── 驅動因素（PREREGY）
    YE = pd.read_csv(os.path.join(HERE, "resultsY", "body_events.csv"), dtype={"起算日": str}, float_precision="round_trip")
    pp = os.path.expanduser("~/us_work/prey/body_events_priv.csv")      # #2（衍生自私有 us-stock-data）在 repo 外；sha 對 resultsY/body_private_sha.txt
    assert hashlib.sha256(open(pp, "rb").read()).hexdigest() == "7a07b691e7b19411526b3183a67d01919ea88bf2f1005c983813a58fb8458a6d"
    YE = pd.concat([YE, pd.read_csv(pp, dtype={"起算日": str}, float_precision="round_trip")], ignore_index=True)
    YC = pd.read_csv(os.path.join(HERE, "resultsY", "body_cells.csv"), dtype=str)
    zY = NormalDist().inv_cdf(1 - 0.05 / 16 / 2)
    R20o = np.full(len(cal_s), np.nan); R20o[:-H] = o50[H:] / o50[:-H] - 1.0
    R20t = np.full(len(cal_s), np.nan); R20t[:-H] = aO[H:] / aO[:-H] - 1.0
    eligY = np.arange(w0, w1 - H + 1); eligY = eligY[np.isfinite(R20o[eligY])]
    by50 = float(np.mean(R20o[eligY])); bytx = float(np.nanmean(R20t[eligY]))
    yrows = []; gY = 0
    for _, c in YC.iterrows():
        k, e_ = c["因素"], c["端"]
        out = {"因素": k, "名稱": c["名稱"], "端": e_, "原_出口": c["出口"], "原_結果": c["結果"], "原_候選": c["候選"], "n": c["n"], "n_eff": c["n_eff"]}
        if c["出口"] == "出口①":
            out.update({"TX扣期貨成本_候選": "都不是（原件出口①，照原件只報筆數）"}); yrows.append(out); continue
        ev = YE[(YE["因素"] == k) & (YE["端"] == e_)]
        s = np.array([pos[d] for d in ev["起算日"]], int)
        mon = np.array([cal_s[i][:7] for i in s])
        gY += int(len(s) != int(c["n"]) or not np.allclose(R20o[s], ev["R20"].to_numpy(float), rtol=0, atol=1e-12, equal_nan=False))
        cost = 2 * cf(rawO[s], FEES["高"])
        for lab, x, base in (("0050原（不扣）", R20o[s], by50), ("TX不扣", R20t[s], bytx), ("TX扣期貨成本", R20t[s], bytx), ("0050扣期貨成本", R20o[s], by50)):
            D_ = float(np.mean(x)) - base
            dd_ = x - x.mean(); sg = pd.Series(dd_).groupby(mon).sum().to_numpy(); se = float(np.sqrt((sg ** 2).sum()) / len(x))
            cm = float(np.mean(cost)) if "扣期貨" in lab else 0.0
            if (D_ - cm) - zY * se > 0:
                res = "結果②"
            elif (D_ + cm) + zY * se < 0:
                res = "結果③"
            else:
                res = "結果①"
            out.update({f"{lab}_D": D_, f"{lab}_平均成本": cm, f"{lab}_lo": D_ - zY * se, f"{lab}_hi": D_ + zY * se, f"{lab}_結果": res,
                        f"{lab}_加碼檢定下緣": D_ - cm - zY * se, f"{lab}_減碼檢定上緣": D_ + cm + zY * se,
                        f"{lab}_候選": {"結果①": "都不是", "結果②": "加碼候選", "結果③": "減碼候選"}[res]})
        gY += int(not (abs(out["0050原（不扣）_D"] - float(c["D"])) <= 1e-12)) + int(out["0050原（不扣）_結果"] != c["結果"])
        yrows.append(out)
    CY = pd.DataFrame(yrows); CY.to_csv(os.path.join(OUT, "F_y_cells.csv"), index=False, float_format="%.10g")
    flipY = {"原不過、現過": int(((CY["原_候選"] == "都不是") & CY.get("TX扣期貨成本_候選", pd.Series(dtype=str)).isin(["加碼候選", "減碼候選"])).sum()),
             "原過、現不過": int(((CY["原_候選"] != "都不是") & ~CY.get("TX扣期貨成本_候選", pd.Series(dtype=str)).isin(["加碼候選", "減碼候選"])).sum())}
    S = {"標籤": "事後重算（毛報酬早已看過；翻成合格最多「暫定」、只進前瞻紀錄）",
         "反轉訊號": {"翻轉": flipR, "Bonferroni z（沿用原件 k＝28）": z, "TX 基準 R20 平均": btx, "0050 基準 R20 平均": b50,
                   "閘：0050 原欄逐格＝原件（不同數）": gate_bad, "TX 在原窗缺值天數": len(tx_missing)},
         "驅動因素": {"翻轉": flipY, "z*": zY, "閘：0050 原欄＝原件（不同數）": gY, "TX 對照 R20 平均": bytx, "0050 對照 R20 平均": by50},
         "翻轉格數合計": flipR["原不過、現過"] + flipR["原過、現不過"] + flipY["原不過、現過"] + flipY["原過、現不過"]}
    S["先驗⑥"] = {"翻轉格數 0": S["翻轉格數合計"] == 0}
    return S, CR, CY


# ═════════════ 主流程 ═════════════
def body(a):
    T0 = time.time()
    os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    S = {"件": "PREREG台指期貨六題 seq2（sha 8ea4f8b4010de81f）", "讀法寫死": TAGT, "產出": now_tpe(), "GATE_V2": "本件無個股母體，不適用",
         "條款": "期交所原始數字只在私有庫與 ~/txfwork；本資料夾只放彙總"}
    F = load_fut("TX")
    S["資料"] = {"TX 一般盤交易日": [str(F["days"][0]), str(F["days"][-1]), int(len(F["days"]))], "結算價來源": F["settle_src"],
               "私有庫 commit": subprocess.run(["git", "-C", "/home/chemtim/us-stock-data", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
               "tw-stock-data 快照": SNAP_SHA, "early": EARLY_SHA}
    IM, MM = load_margin(F["days"]); rate, rinfo = load_rate(F["days"])
    log(f"[資料] TX {F['days'][0]}～{F['days'][-1]}｜到期 {F['settle_src']}")
    parts = a.parts.split(",")
    if "A" in parts:
        etf = {}; einfo = {}
        for sid in ("0050", "00631L"):
            etf[sid], einfo[sid] = etf_close(sid)
        S["甲"], _ = part_A(F, IM, MM, rate, rinfo, etf)
        S["甲"]["ETF 接法"] = einfo
        Fm = load_fut("MTX"); Ft = load_fut("TMF")
        S["甲"]["核對"] = {"MTX vs TX": consist(Fm, F), "TMF vs TX": consist(Ft, F)}
        log(f"[甲] {S['甲']['判定']}｜{time.time() - T0:.0f}s")
    if "B" in parts:
        S["乙"], _ = part_B(F, IM, MM); log(f"[乙] {S['乙']['先驗②']}｜{time.time() - T0:.0f}s")
    if "C" in parts:
        S["丙"], _ = part_C(F); log(f"[丙] 成立 {S['丙']['成立格數']}／6｜{time.time() - T0:.0f}s")
    if "D" in parts:
        S["丁"], _ = part_D(F, None); log(f"[丁] 成立 {S['丁']['成立格數']}／6｜{time.time() - T0:.0f}s")
    if "E" in parts:
        S["戊"], _ = part_E(F); log(f"[戊] 成立 {S['戊']['成立格數']}／3｜{time.time() - T0:.0f}s")
    if "F" in parts:
        S["己"], _, _ = part_F(F); log(f"[己] 翻轉 {S['己']['翻轉格數合計']}｜{time.time() - T0:.0f}s")
    S["耗時s"] = round(time.time() - T0)
    p = os.path.join(OUT, "summary.json")
    if os.path.exists(p) and a.parts != "A,B,C,D,E,F":
        old = json.load(open(p, encoding="utf-8")); old.update(S); S = old
    json.dump(S, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    log(f"[完] {time.time() - T0:.0f}s")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("mode", nargs="?", default="body", choices=["body", "page"])
    ap.add_argument("--parts", default="A,B,C,D,E,F"); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if a.check:
        from backtest import researchTXF_check as K
        return K.main()
    if a.mode == "page":
        from backtest import researchTXF_page as P
        return P.main()
    body(a)


if __name__ == "__main__":
    main()
