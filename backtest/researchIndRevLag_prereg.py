# -*- coding: utf-8 -*-
"""PREREG產業營收加速但股價落後 seq2（台股策略線登錄 seq1 sha f54db09c944622e0 ⇒ seq2 sha 4ea6c2df8fb36f89 為準；裁定 seq312、313 核准，N_組合 ＋1）
乙（組合層，72 格挑 1）＋丙（描述，不計 N）——回測線計算子代理。⚠ 事後重切（前件 PREREG產業營收加速 全部輸出已看過）⇒ 結果最多「暫定」、只進前瞻紀錄。
⛔ 不給買賣建議。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchIndRevLag_prereg [--procs 3] [--reps 1000] | --check | --page

═══ 讀法（寫死於 2026-10-07 02:15（台北），在算任何乙、丙數字之前；「★」＝ 登錄沒寫清楚、執行者補）═══
 Q0 沿用（⛔ 不改前件檔、⛔ 不改它們的輸出）
    前件 researchIndRev_prereg（PRE）：月營收、industry_pit（PIT 類）、「當時已上市櫃」、A 表（_a_month ＝ snapshot.compute_ind "new"）、挑股 picks_at（P5）、
      換股簿成交與成本（P6：開盤成交、開盤漲停買不到不遞補、開盤跌停／停牌延後賣、下市了結、停止交易強制出場、賣出扣進場金額 × 0.585%）、
      現實版 C1～C5（P11）、0050 重疊率（P12）、段與 0050（P8、P9）、丙公式（P13）
    甲 researchIndRevLag_snapshot（LAG）：L4 產業指數（W1 成員等權日報酬連乘、還原收盤 ffill、量測日成員管到下一量測日）、
      ★ L 窗內任一天沒有成員日報酬 ⇒ 該 L 報酬記空；L5 可排名集合（公司數 ≥ 5 ∧ A1～A3 皆有限 ∧ 三個 L 報酬皆有限，三種 A、三個 L 同一批）、
      百分位 ＝（由低到高名次 − 1）÷（n − 1）、同值取平均名次；P2 的 2/3 浮點容差 1e−12
 Q1 資料與母體（GATE_V2 開：程式開頭 UG.set_gate_v2(True)）
    月營收、產業別 ＝ tw-stock-data origin/main（執行時 sha；PRE.ensure_data）
    主段 ＝ 前件同一份價格快照 H2D（edc6f8002f）＋ resultsp9_engine/panel_ext（W1 eligible）；母體 ＝ gate3（v2）∩ 量測日 pit_valid 為真（★ 面板沿用、
      v2 的板期／興櫃列在量測日以 pit_valid 剔；panel_ext 是舊口徑建的、v2 才收回的股票若面板沒列就不會入選，照實標）
    早年段 ＝ ⭐ 上市＋上櫃版面 ~/earlydata/eotc_f65bb03e11/otc/data（登錄 §三；前件只用上市的偏離本件不再犯）：
      ★ W1 面板在此版面上重建（LAG._wjob ＝ researchp4.panel_worker ＋ pit_valid，量測日 2004-01～2014-12 每月第一個交易日；存 ~/indrevlagwork/panel_eotc.csv.gz）
      ⚠ 此版面上櫃沒有法人檔 ⇒ 上櫃 inst_ok 全假 ⇒ 早年 W1（挑股）實際只有上市；產業指數（Q4）用 liq_ok ∧ bars_ok（不需法人）⇒ 含上櫃；照實報
      市值 ＝ 原始收盤 × shares（主段 H2D stocks；早年 eotc daily_all.pkl），同 PRE
    段：探索 2017-03-02～2021-12-30（挑）、確認 2022-01-03～2026-08-24（判；＝ 前件同窗，panel_ext 最後量測日 2026-08 ⇒ 資料尾照實報 2026-08-24）、
      早年 2012-06-01～2014-12-30（判）；2005～2012-05 不可判定
 Q2 可用日（登錄 §一）：M ≤ 2025-12 ⇒ M＋1 月 10 日之後第一個交易日；M ≥ 2026-01 ⇒ 15 日之後（research34.rebalance_dates pub_day 10／15，嚴格大於）
    產業別與「當時已上市櫃」判定日 ＝ 可用日前一交易日（PRE pitday 同式，只換可用日）⇒ A 表全部重算（pit、現值兩版；剔除 2023 ＝ pit 版去掉四類）
 Q3 A ＝ PRE A 表的 A1／A2／A3（公司數 ＜ 5 不排名）；檢查日 t 用的營收月 M ＝ 可用日 ≤ t 的最新月（可用日當天即可用）
 Q4 產業指數（★ 逐段）：主段 ＝ W1（eligible ∧ pit_valid）成員；早年段 ＝ liq_ok ∧ bars_ok ∧ pit_valid 成員（★ W1 早年 2012-06 前沒有，同 PRE P13）；
      產業 ＝ PIT.at(代號, 量測日)（pit 版；現值變體用現值）；日報酬 ＝ c[t]/c[t−1] − 1（c ＝ SC.load_px 還原收盤 ffill，兩日皆有限）；
      產業日報酬 ＝ 有限者平均；第一個有值日前一天 ＝ 1，之後連乘（缺日 0）；L 日報酬 ＝ I[t] ÷ I[t−L] − 1，且 t−L ≥ 第一個有值日前一天、窗 (t−L, t] 每天都有成員報酬，否則空
 Q5 主臂（條件換股，登錄 §三 seq2）
    檢查日 ＝ 每個營收可用日 t（t0 ≤ t ≤ t1−1），收盤判（A 月 ＝ 最新可用月；L 報酬用 t 收盤 ＝ 執行日前一交易日收盤），次一交易日 t＋1 開盤執行；
      ★ 窗首即建倉：t0−1 視為檢查日（t0 開盤執行）
    出場（持有產業任一成立）：X1 ＝ 該產業 A ≤ 0（★ A 有限且公司數 ≥ 5 才判）；X2 ＝ A 百分位 − L 百分位 ≤ 0（★ 該產業在可排名集合內才判）；
      ★ 兩條都無法判（不在可排名集合且 A 無值）⇒ 不出場、計數；⛔ 無最長天數
    補位：同一檢查日，出場後的空位依位置序號由小到大，照 P 規則補「目前沒持有」的最佳候選：
      P1 ＝ A ＞ 0 ∧ 名次差 ＞ 0，依名次差大到小（同值依名稱）
      P2 ＝ A ＞ 0 ∧ A 百分位 ≥ 2/3，依 L 報酬小到大（同值依名稱）；★ 另要名次差 ＞ 0（否則當天就符合 X2、進場即該出場；P1 本來就要求）
      沒有候選 ⇒ 該位置現金（報酬 0）到下一檢查日
    位置（K ∈ {1, 3}）：★ 每個位置一個子帳戶：窗首各 1/K；產業出場的賣出款、停止交易強制出場款、下市了結款都回該位置；之後不再平衡
      新產業每檔目標 ＝ 該位置前一日收盤價值 ÷ n_i（n_i ＝ 該產業 S 名單實際檔數；S1 前 20 不足全買、S2 前 3），買 min(目標, 該位置現金)；
      延後賣出的款項晚到 ⇒ 留在該位置當現金，到該位置下次換產業才再投入（★）
      產業 S 名單 0 檔 ⇒ 該產業仍算持有、整個位置現金（同 PRE「產業入選 0 檔 ⇒ 那份現金」，計數）
      ★ 新名單裡的股票若正被同位置舊產業賣出 ⇒ 取消賣出、改掛新產業（計數）；被其他位置持有 ⇒ 跳過不買（計數）
    挑股 S ＝ PRE.picks_at(執行日)：S1 市值前 20、S2 前 3（同 PRE P5；進場時決定，持有期間不換）
    格 ＝ P 2 × L 3 × A 3 × K 2 × S 2 ＝ 72；探索段先排除退化（平均持股 ＜ 3 或平均現金比例 ＞ 30%），過使用者判準者取比值最高，都沒過取比值最高；
      平手 ⇒ 年化高、P、L、A、K、S 順；判定 ＝ 確認、早年各自標籤取較嚴；⚠ 事後重切 ⇒ 合格最多寫「暫定合格」、另列寫「另列（最多暫定）」
 Q6 描述對照（⛔ 不進挑選格）：挑中格改定期換股 R ∈ {季, 半年, 年}（＝ seq1 E0）：換股日 ＝ 營收可用日（季 1、4、7、10 月…，同 PRE P3），
      A 月 ＝ 換股日可用的最新月、L 報酬 ＝ 換股日前一交易日收盤（seq1 §二）、當日開盤執行；取 P 規則前 K（續抱仍入選；不足 K 缺額現金；
      ★ 可排名集合為空 ⇒ 該次不換股）；成交、成本、每檔目標 ＝ 前一日權益 ÷（K × n_i）同 PRE.sim_ind E0（閘 G1′：此引擎改用「只看 A」排名時與 PRE.sim_ind 權益逐位元相同）
      ⚠ 條件版是檢查日收盤判、隔日開盤做，定期版是可用日開盤做（各照 seq2／seq1 原文），兩者差一天，照標
 Q7 對照（挑中格同 P、L、A、K、S）
    ⭐ 主對照 ＝ 前件挑中格 A2｜K1｜S1｜季｜E0（PRE.sim_ind 原引擎）在本件設定（GATE_V2、早年上市＋上櫃版面、新 A 表與 15 日規則）同窗重跑；前件原數字並列
    隨機 1,000 次 ★ ＝ 同條件換股機制、同出場條件（用挑中格的 A、L），補位改成從「可排名且目前沒持有」的產業隨機抽（default_rng([20261007, r])）
    反向臂（描述）★ ＝ 定期季換：A ＞ 0 ∧ A 百分位 ≥ 2/3 的產業裡 L 報酬最高的 K 個（與挑中格的定期季換版同表比）
    全產業等權 ★ ＝ 定期季換：當日全部可排名產業、挑股同挑中格；營量 v1 ＝ 引前件 meta（resultsT1fix c13 逐位元那份；早年 b2e 窗略不同）；0050 ＝ RR.load_bench
 Q8 必報：挑中產業與次數、窗尾仍持有（產業、進場日、已持有交易日數）、持有天數分佈、X1／X2 次數、現金比例、0050 重疊率（PRE.overlap50；換倉日收盤後）、
    各年報酬、換手與成本、現實版（C1 每邊 ＋0.3%＋C2 50 萬衝擊＋C4 均價；＋C5 低消 20 元；PRE 同式落到位置簿）、產業別兩變體（① 現值 ② 剔除 2023 新增四類）
 Q9 丙（描述、不計 N；挑中格的每段產業持有 ＝ 一筆）
    ① 股價多久追上：從訊號日（檢查日 tc）起，★ 逐交易日收盤重算可排名集合與百分位（A 月 ＝ 當日最新可用月），第一個「該產業可排名且名次差 ≤ 0」的日 ⇒ 天數 ＝ 該日 − tc；
       看到資料尾（主段 2026-09-24、早年 2014-12-31）；250 日內追上比例 ＝ 250 日內追上 ÷（250 日內追上 ＋ 跟蹤滿 250 日仍未追上），其餘標「未滿 250 日」；
       追上前報酬 ＝ I[追上日] ÷ I[tc] − 1（產業指數）
    ② 落後的原因：訊號月 M 之後 3、6、9、12 個月（M＋3…）該產業同一種 A 是否仍 ＞ 0（有值者為分母）；前件挑中格（A2、季換每次前 1 名）同表
    ③ 吃到起漲到頂幾成：PRE P13 同式（Is ＝ I[進場−1]、低 ＝ 前 250 日最低、頂 ＝ 進場起 500 日最高；實際持有 ＝ I[出場−1]，窗尾仍持有用 I[窗尾]）
    ④ 窗尾仍持有數與持有天數分佈（同 Q8）
    ★ 非電子類（先驗 ③）：電子類 ＝ 半導體業、電腦及週邊設備業、光電業、通信網路業、電子零組件業、電子通路業、資訊服務業、其他電子業、電子工業、數位雲端；其餘為非電子
    ★ 先驗 ⑤ 以確認段判（三種 R 任一年化 ≥ 條件版 ⇒ 對），探索、早年並列
 Q10 查核（--check；獨立寫法，0 不同才算過；抽樣 default_rng(20261007)）
    ① A：抽 2 個（產業 × 月；其中 1 個在 2026 年，驗 15 日規則的判定日）用 PRE.ck_A 從原始 csv 逐公司重算 ⇒ 相對差 ≤ 1e−12
    ② 產業指數與 L 報酬：自己讀面板 csv（eligible／liq∧bars）、自己由逐日檔名稱與市場判板期、PRE.ck_ind 分產業、自己由 stocks＋adj csv 還原收盤 ⇒
       兩段全部檢查日 × 全部產業 × 三個 L ⇒ 相對差 ≤ 1e−9、有無值相同
    ③ 排名：用 ② 的 L 與 PRE.ck_A 的 A，純 Python 重排可排名集合與百分位 ⇒ 兩段全部檢查日：集合相同、百分位差 ≤ 1e−9；挑中格與抽中格的候選名單逐位相同
    ④ 逐筆重算：挑中格＋另抽 1 格，兩段：獨立位置簿迴圈（獨立市值、獨立 W1、PRE.ck_ind、③ 的排名）⇒ 權益相對差 ≤ 1e−9、換倉日持股集合與每筆交易 0 不同
    ⑤ 閘 G1′ 重跑（定期引擎 vs PRE.sim_ind 逐位元）
輸出 backtest/resultsIndRevLag/prereg/：cells.csv、chosen_episodes.csv、industry_counts.csv、years.csv、variants.csv、random.csv.gz、c_catch.csv、c_after.csv、
    c_eat.csv、A_table.csv.gz、eq.npz、meta.json、check.json、產業營收加速但股價落後_回測.html
"""
from __future__ import annotations

import argparse
import bisect
import csv
import html
import json
import math
import os
import pickle
import sys
import time
from collections import Counter, defaultdict
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D                              # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402
from backtest import research11 as R                        # noqa: E402
from backtest import research13 as R13                      # noqa: E402
from backtest import research34 as R34                      # noqa: E402
from backtest import researchScore as SC                    # noqa: E402
from backtest import researchIndRev_prereg as PRE           # noqa: E402
from backtest import researchIndRevLag_snapshot as LAG      # noqa: E402
from backtest import p4_features as P4F                     # noqa: E402
from backtest import tradability as TR                      # noqa: E402
from backtest import universe_gate as UG                    # noqa: E402

TIME = "2026-10-07 02:15（台北）"
OUT = "backtest/resultsIndRevLag/prereg"
WORK = os.path.expanduser("~/indrevlagwork")
EOTC = os.path.expanduser("~/earlydata/eotc_f65bb03e11/otc/data")
PANEL_EOTC = os.path.join(WORK, "panel_eotc.csv.gz")
MAIN_W, SEG, EARLY_A = PRE.MAIN_W, PRE.SEG, PRE.EARLY_A
PS = ("P1", "P2"); LS = (60, 120, 250); AS = PRE.AS; KS = (1, 3); SS = ("S1", "S2"); RS = PRE.RS
AI = {"A1": 1, "A2": 2, "A3": 3}
COST = PRE.COST
SEED = 20261007
CAP = PRE.CAP
EXCL = PRE.EXCL
NEW2023 = PRE.NEW2023
ELEC = {"半導體業", "電腦及週邊設備業", "光電業", "通信網路業", "電子零組件業", "電子通路業", "資訊服務業", "其他電子業", "電子工業", "數位雲端"}
RANKL = PRE.RANKL
PRE_CH = {"A": "A2", "K": 1, "S": "S1", "R": "季", "E": "E0"}
G: dict = {}
LOGF = None


def log(x):
    x = f"[{time.strftime('%H:%M:%S')}] {x}"
    print(x, flush=True)
    if LOGF:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(x + "\n")


def fin(x):
    return x is not None and isinstance(x, (float, int, np.floating, np.integer)) and np.isfinite(x)


# ═════════════ 設定（Q1、Q2） ═════════════
def setup(a, sha=None):
    UG.set_gate_v2(True)
    sha = PRE.setup(a, sha)
    D.DATA = SC.EARLY_DATA; ce = D.load_calendar()
    RR.use_snapshot(); cm = D.load_calendar()
    gcal = ce[ce <= pd.Timestamp("2014-12-31")].append(cm[cm > pd.Timestamp("2014-12-31")])
    rev = PRE._C["rev"]
    rd = {**R34.rebalance_dates([M for M in rev.index if M <= "2025-12"], gcal, 10),
          **R34.rebalance_dates([M for M in rev.index if M >= "2026-01"], gcal, 15)}
    PRE._C["avail_date"] = {M: gcal[e] for M, (_, e) in rd.items()}
    PRE._C["pitday"] = {M: gcal[e - 1] for M, (_, e) in rd.items()}
    G["sha"] = sha
    s26 = {M: str(PRE._C["avail_date"][M].date()) for M in sorted(PRE._C["avail_date"]) if M >= "2025-11"}
    log(f"[可用日] 2025-11 起：{s26}")
    return sha


def build_A(a):
    Ms = [M for M in PRE._C["rev"].index if "2003-12" <= M and M in PRE._C["pitday"]]
    jobs = [(M, "pit") for M in Ms] + [(M, "現值") for M in Ms]
    t0 = time.time()
    with Pool(a.procs) as pool:
        res = pool.map(PRE._a_month, jobs, chunksize=4)
    AT = pd.concat([r[0] for r in res], ignore_index=True)
    src = Counter()
    for (M, v), r in zip(jobs, res):
        if v == "pit":
            src.update(r[1])
    log(f"[A 表] {len(jobs)} 月×版｜{time.time() - t0:.0f}s")
    return AT, dict(src)


def install_A(AT):
    PRE._C["RANK"] = PRE.build_rank(pd.concat([AT, AT[AT["ver"] == "pit"].assign(ver="剔除2023")], ignore_index=True))
    PRE._C["AV"] = {(v, M, i): {"A1": a1, "A2": a2, "A3": a3} for v, M, i, a1, a2, a3 in zip(AT["ver"], AT["M"], AT["產業"], AT["A1"], AT["A2"], AT["A3"])}
    T = defaultdict(dict)
    for v, M, i, c, a1, a2, a3 in zip(AT["ver"], AT["M"], AT["產業"], AT["公司數"], AT["A1"], AT["A2"], AT["A3"]):
        T[(v, M)][i] = (float(c), float(a1), float(a2), float(a3))
    G["AT"] = dict(T)


# ═════════════ 早年 W1 面板（Q1） ═════════════
def build_panel_eotc(a):
    if os.path.exists(PANEL_EOTC):
        log(f"[早年面板] 讀既有 {PANEL_EOTC}")
        return json.load(open(PANEL_EOTC + ".info.json", encoding="utf-8"))
    D.DATA = EOTC; cal = D.load_calendar()
    g = UG.gate3(pd.read_csv(os.path.join(EOTC, "meta", "stocks.csv"), dtype=str))
    U = D.load_universe().merge(g[["stock_id"]], on="stock_id")
    pos = P4F.measurement_days(cal, "2004-01-01", "2014-12-31")
    jobs = [(r.stock_id, r.market, r.first_seen, r.last_seen) for r in U.itertuples()]
    t0 = time.time(); rows = []
    with Pool(a.procs, initializer=LAG._winit, initargs=(cal, pos, EOTC)) as pool:
        for rs in pool.imap_unordered(LAG._wjob, jobs, chunksize=8):
            rows.extend(rs)
    PN = pd.DataFrame(rows).sort_values(["measure_date", "stock_id"]).reset_index(drop=True)
    PN.to_csv(PANEL_EOTC, index=False, compression={"method": "gzip", "mtime": 0})
    info = {"gate3(v2)∩universe": int(len(U)), "上市": int((U["market"] == "twse").sum()), "上櫃": int((U["market"] == "tpex").sum()),
            "量測日": int(len(pos)), "面板列": int(len(PN)),
            "eligible 列（上市／上櫃）": [int((PN["eligible"] & (PN["market"] == "twse")).sum()), int((PN["eligible"] & (PN["market"] == "tpex")).sum())],
            "liq∧bars 列（上市／上櫃）": [int((PN["liq_ok"] & PN["bars_ok"] & (PN["market"] == "twse")).sum()), int((PN["liq_ok"] & PN["bars_ok"] & (PN["market"] == "tpex")).sum())],
            "pit_valid 剔": int((~PN["pit_ok"]).sum()), "秒": round(time.time() - t0)}
    json.dump(info, open(PANEL_EOTC + ".info.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[早年面板] {info}")
    return info


# ═════════════ 段 ═════════════
def part_ctx(name, a):
    cp = os.path.join(WORK, f"ctx_{name}.pkl")
    if os.path.exists(cp):
        C = pickle.load(open(cp, "rb")); D.DATA = C["data"]
        log(f"[{name}] 讀快取 {cp}")
        return C
    t0_ = time.time()
    if name == "main":
        RR.use_snapshot(); panel = SC.PANEL_EXT
    else:
        D.DATA = EOTC; panel = PANEL_EOTC
    cal = D.load_calendar(); ncal = len(cal)
    U = UG.gate3(pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str))
    mk = U.set_index("stock_id")["market"].to_dict(); keep = set(mk)
    pn = P4F.read_panel(panel)
    pn = pn[pn["stock_id"].isin(keep)].copy()
    if "pit_ok" in pn.columns:
        pn["pit_ok"] = pn["pit_ok"].astype(str).eq("True")
    else:
        pv = {s: UG.pit_valid(s, cal, D.DATA) for s in sorted(set(pn["stock_id"]))}
        pp = cal.searchsorted(pd.DatetimeIndex(pn["measure_date"]))
        pn["pit_ok"] = [bool(pv[s][p]) for s, p in zip(pn["stock_id"], pp)]
    el0 = pn["eligible"].astype(str).eq("True"); lb0 = pn["liq_ok"].astype(str).eq("True") & pn["bars_ok"].astype(str).eq("True")
    el = el0 & pn["pit_ok"]; lb = lb0 & pn["pit_ok"]
    memW = {d: sorted(g) for d, g in pn.loc[el].groupby("measure_date")["stock_id"]}
    memX = {d: sorted(g) for d, g in pn.loc[lb].groupby("measure_date")["stock_id"]}
    meas = sorted(set(pn["measure_date"]))
    lo = pd.Timestamp("2016-01-01") if name == "main" else pd.Timestamp("2004-01-01")
    sids = sorted({s for d, v in (memW if name == "main" else memX).items() if d >= lo for s in v} | {s for v in memW.values() for s in v})
    SC._G.update(cal=cal)
    with Pool(a.procs) as pool:
        P = dict(pool.map(SC.load_px, [(s, mk.get(s, "twse")) for s in sids], chunksize=16))
    P = {s: v for s, v in P.items() if v is not None}
    try:
        off = TR.load_official()
    except Exception:
        off = {}
    dl = TR.delist_status({s: {"trd": v["trd"]} for s, v in P.items()}, cal, official=off)
    bench = RR.load_bench(cal)
    MC = {}
    if name == "main":
        for s in P:
            raw = pd.read_csv(os.path.join(D.DATA, "stocks", f"{s}.csv"), dtype={"date": str}, usecols=["date", "close", "shares"])
            raw["date"] = pd.to_datetime(raw["date"]); raw = raw.drop_duplicates("date").set_index("date")
            v = (pd.to_numeric(raw["close"], errors="coerce") * pd.to_numeric(raw["shares"], errors="coerce"))
            v = v.where(v > 0)
            MC[s] = v.reindex(cal).ffill().to_numpy(float) if v.notna().any() else np.full(ncal, np.nan)
    else:
        da = pickle.load(open(PRE.EOTC_DAILY, "rb"))
        da = da[da["stock_id"].isin(set(P))][["date", "stock_id", "close", "shares"]].copy()
        da["v"] = pd.to_numeric(da["close"], errors="coerce") * pd.to_numeric(da["shares"], errors="coerce")
        da = da[da["v"] > 0].drop_duplicates(["stock_id", "date"], keep="last")
        da["date"] = pd.to_datetime(da["date"])
        pv_ = da.pivot(index="date", columns="stock_id", values="v").reindex(cal).ffill()
        for s in P:
            MC[s] = pv_[s].to_numpy(float) if s in pv_.columns else np.full(ncal, np.nan)
    info = {"日曆": [str(cal[0].date()), str(cal[-1].date()), ncal], "gate3(v2)": len(keep), "上市／上櫃": [sum(1 for v in mk.values() if v == "twse"), sum(1 for v in mk.values() if v == "tpex")],
            "載入": len(P), "量測日": len(meas), "W1 列（剔板期前→後）": [int(el0.sum()), int(el.sum())], "liq∧bars 列（剔前→後）": [int(lb0.sum()), int(lb.sum())],
            "W1 列 上櫃": int((el & pn["market"].eq("tpex")).sum()) if "market" in pn else None, "秒": round(time.time() - t0_)}
    log(f"[{name}] {info}")
    C = {"name": name, "cal": cal, "ncal": ncal, "P": P, "dl": dl, "bench": bench, "MC": MC, "mk": mk, "memW": memW, "memX": memX, "meas": meas,
         "data": D.DATA, "panel": panel, "SF": {}, "info": info}
    pickle.dump(C, open(cp, "wb"), protocol=5)
    return C


def prep_part(name, win, segs, a):
    C = part_ctx(name, a); PRE.attach_months(C)
    C["win"] = (SC.pos_of(C["cal"], win[0]), SC.pos_of(C["cal"], win[1])); C["segp"] = PRE.segpos(C, segs)
    t0, t1 = C["win"]
    C["checks"] = sorted({t0 - 1} | {p for p in C["availday"] if t0 <= p <= t1 - 1})
    mode = "W1" if name == "main" else "X"
    C["IX"] = {v: ind_index(C, mode, v) for v in ("pit", "現值")}
    C["RK"] = {}
    G[name] = C
    return C


def sfdays(C, t1):
    if t1 not in C["SF"]:
        C["SF"][t1] = R.stop_force_days({s: v["valid"] for s, v in C["P"].items()}, t1)
    return C["SF"][t1]


# ═════════════ 產業指數（Q4） ═════════════
def ind_index(C, mode, ver):
    cal = C["cal"]; n = C["ncal"]
    sids = sorted(C["P"]); ix = {s: k for k, s in enumerate(sids)}
    Cm = np.vstack([C["P"][s]["c"] for s in sids])
    with np.errstate(invalid="ignore", divide="ignore"):
        Rm = np.full_like(Cm, np.nan); Rm[:, 1:] = Cm[:, 1:] / Cm[:, :-1] - 1
    mem = C["memW"] if mode == "W1" else C["memX"]
    meas = sorted(mem)
    rr = defaultdict(lambda: np.full(n, np.nan))
    pv = "現值" if ver == "現值" else "pit"
    for j, md in enumerate(meas):
        a = int(cal.searchsorted(md)); b = int(cal.searchsorted(meas[j + 1])) if j + 1 < len(meas) else n
        grp = defaultdict(list)
        for s in mem[md]:
            if s not in ix:
                continue
            ind, _ = PRE._C["PIT"].at(s, md, pv)
            if ind is None or ind in EXCL:
                continue
            grp[ind].append(ix[s])
        for ind, rows in grp.items():
            blk = Rm[rows, a:b]
            fin_ = np.isfinite(blk); cnt = fin_.sum(0); sm = np.where(fin_, blk, 0.0).sum(0)
            rr[ind][a:b] = np.where(cnt > 0, sm / np.maximum(cnt, 1), np.nan)
    I = {}
    for ind, r in rr.items():
        f = np.flatnonzero(np.isfinite(r))
        if not len(f) or f[0] == 0:
            continue
        f0 = int(f[0])
        x = np.full(n, np.nan); x[f0 - 1] = 1.0
        x[f0:] = np.cumprod(1 + np.nan_to_num(r[f0:], nan=0.0))
        bad = ~np.isfinite(r); bad[:f0] = True
        I[ind] = (x, np.concatenate([[0], np.cumsum(bad)]), f0, r)
    return I


def lret(IX, ind, t, L):
    z = IX.get(ind)
    if z is None or t - L < 0:
        return np.nan
    x, nb, f0, _ = z
    if t - L < f0 - 1 or nb[t + 1] - nb[t - L + 1] > 0:
        return np.nan
    return float(x[t] / x[t - L] - 1)


# ═════════════ 排名（Q3、Q5） ═════════════
def rank_tab(C, ver, tA, tL):
    key = (ver, tA, tL)
    if key in C["RK"]:
        return C["RK"][key]
    M = C["Mlast"][tA]
    va = "現值" if ver == "現值" else "pit"
    T = G["AT"].get((va, M), {}) if M else {}
    IX = C["IX"][va]
    Aall = {}; rows = []
    for ind in sorted(T):
        if ver == "剔除2023" and ind in NEW2023:
            continue
        v = T[ind]; Aall[ind] = v
        if not (v[0] >= 5 and all(np.isfinite(v[1:]))):
            continue
        rets = [lret(IX, ind, tL, L) for L in LS]
        if not all(np.isfinite(rets)):
            continue
        rows.append((ind, v[1], v[2], v[3], *rets))
    n = len(rows); names = [r[0] for r in rows]
    Av = {a: np.array([r[1 + j] for r in rows], float) for j, a in enumerate(AS)}
    Lv = {L: np.array([r[4 + j] for r in rows], float) for j, L in enumerate(LS)}

    def pct(v):
        return (pd.Series(v).rank(method="average").to_numpy(float) - 1) / (n - 1) if n >= 2 else np.full(n, np.nan)
    out = {"M": M, "n": n, "names": names, "idx": {k: i for i, k in enumerate(names)}, "A": Av, "L": Lv,
           "pA": {a: pct(Av[a]) for a in AS}, "pL": {L: pct(Lv[L]) for L in LS}, "Aall": Aall}
    C["RK"][key] = out
    return out


def cands(RK, P_, A, L, held, order="rule", rng=None):
    """⇒ 候選產業（依序）；可排名集合 n ＜ 2 ⇒ None（無法排名）。"""
    if RK["n"] < 2:
        return None
    nm = RK["names"]
    if order == "random":
        return [nm[k] for k in rng.permutation(len(nm)) if nm[k] not in held]
    if order == "all":
        return [x for x in nm if x not in held]
    Av, pA, Lv, pL = RK["A"][A], RK["pA"][A], RK["L"][L], RK["pL"][L]
    d = pA - pL
    if order == "rule" and P_ == "P1":
        c = sorted(((-d[k], nm[k]) for k in range(len(nm)) if Av[k] > 0 and d[k] > 0))
    elif order == "rule":
        c = sorted(((Lv[k], nm[k]) for k in range(len(nm)) if Av[k] > 0 and pA[k] >= 2 / 3 - 1e-12 and d[k] > 0))
    elif order == "rev":
        c = sorted(((-Lv[k], nm[k]) for k in range(len(nm)) if Av[k] > 0 and pA[k] >= 2 / 3 - 1e-12))
    else:
        raise ValueError(order)
    return [x for _, x in c if x not in held]


def exit_test(RK, i, A, L):
    v = RK["Aall"].get(i); x1 = x2 = None
    if v is not None and v[0] >= 5 and np.isfinite(v[AI[A]]):
        x1 = bool(v[AI[A]] <= 0)
    k = RK["idx"].get(i)
    if k is not None and RK["n"] >= 2:
        x2 = bool(RK["pA"][A][k] - RK["pL"][L][k] <= 0)
    return x1, x2


def rk_info(RK, i, A, L):
    k = RK["idx"].get(i)
    if k is None:
        return {}
    return {"A值": float(RK["A"][A][k]), "A百分位": float(RK["pA"][A][k]), "L報酬": float(RK["L"][L][k]), "L百分位": float(RK["pL"][L][k]),
            "名次差": float(RK["pA"][A][k] - RK["pL"][L][k])}


# ═════════════ 主臂：條件換股位置簿（Q5） ═════════════
def sim_cond(C, t0, t1, cfg, rng=None, real=None):
    P, dl, ncal = C["P"], C["dl"], C["ncal"]
    SF = sfdays(C, t1)
    ver = cfg.get("ver", "pit"); P_, A, L, K, S = cfg["P"], cfg["A"], cfg["L"], cfg["K"], cfg["S"]
    order = cfg.get("order", "rule")
    checks = set(c for c in C["checks"] if t0 - 1 <= c <= t1 - 1)
    eq = np.ones(ncal); scash = [1.0 / K] * K; sval = [1.0 / K] * K; sind = [None] * K; sinfo = [None] * K
    pos = {}; pend = set(); prate = {}
    npos = np.zeros(ncal, np.int16); cashf = np.zeros(ncal); costd = np.zeros(ncal); buyd = np.zeros(ncal)
    cnt = Counter()
    episodes = []; snaps = {}; trades = []
    rx = real or {}
    for t in range(t0, t1 + 1):
        # ── 停止交易強制出場
        for s in [s for s in pos if SF.get(s) is not None and t == SF[s] + 1]:
            u, amt, k = pos.pop(s)
            px = P[s]["c"][t]; cr = prate.pop(s, COST)
            scash[k] += u * px - amt * cr; costd[t] += amt * cr; cnt["stop_force"] += 1
            pend.discard(s); trades.append((t, s, "sf", px))
        newbuy = {}
        dec = (t - 1) in checks
        if dec:
            tc = t - 1
            RK = rank_tab(C, ver, tc, tc)
            for k in range(K):
                i = sind[k]
                if i is None:
                    continue
                x1, x2 = exit_test(RK, i, A, L)
                if x1 or x2:
                    why = "X1+X2" if (x1 and x2) else ("X1" if x1 else "X2")
                    cnt[why] += 1
                    e_ = dict(sinfo[k]); e_.update(end=t, why=why, exit_sig=tc); episodes.append(e_)
                    pend |= {s for s, p_ in pos.items() if p_[2] == k}
                    sind[k] = None; sinfo[k] = None
                elif x1 is None and x2 is None:
                    cnt["無法判定"] += 1
            vac = [k for k in range(K) if sind[k] is None]
            if vac:
                held = {i for i in sind if i is not None}
                cl = cands(RK, P_, A, L, held, order, rng)
                if cl is None:
                    cnt["無法排名檢查日"] += 1; cl = []
                PK = PRE.picks_at(C, ver, "W1", t)
                for k in vac:
                    if not cl:
                        cnt["空位無候選"] += 1; continue
                    i = cl.pop(0)
                    lst = PK.get(i, {}).get(S, [])
                    if not lst:
                        cnt["ind_empty"] += 1
                    buy = []
                    for s in lst:
                        if s in pos:
                            if pos[s][2] == k and s in pend:
                                pend.discard(s); cnt["取消賣出改掛"] += 1
                            else:
                                cnt["他位置持有跳過"] += 1
                            continue
                        buy.append(s)
                    sind[k] = i
                    sinfo[k] = {"ind": i, "slot": k, "sig": tc, "start": t, "M": RK["M"], **rk_info(RK, i, A, L), "n_list": len(lst), "list": "、".join(lst)}
                    newbuy[k] = (buy, len(lst))
        # ── 賣
        for s in sorted(pend):
            x = P[s]; o_t = (rx["X"][s]["avg"][t] if rx.get("c4") else x["o"][t])
            if x["trd"][t] and not x["dn_o"][t] and np.isfinite(o_t) and o_t > 0:
                px = o_t; kd = "open"
            elif (not x["trd"][t]) and s in dl and t > dl[s]["last"] and dl[s]["status"].startswith("delisted"):
                px = x["c"][t]; kd = "delist"; cnt["delist_settled"] += 1
            else:
                cnt["sell_delayed_days"] += 1; continue
            u, amt, k = pos.pop(s)
            pxe = px
            if rx.get("cap") and kd == "open":
                xs = rx["X"][s]; Q = rx["cap"] * (u * px) / eq[t - 1]
                ix = xs["sig20"][t] * np.sqrt(Q / xs["adv20"][t]) if (np.isfinite(xs["adv20"][t]) and xs["adv20"][t] > 0 and np.isfinite(xs["sig20"][t])) else 0.0
                pxe = px * (1 - min(ix, 0.99))
            cr = prate.pop(s, COST)
            scash[k] += u * pxe - amt * cr; costd[t] += amt * cr; cnt["sell"] += 1
            pend.discard(s); trades.append((t, s, kd, px))
        # ── 買
        for k in sorted(newbuy):
            buy, n_i = newbuy[k]
            for s in buy:
                x = P[s]; o_t = (rx["X"][s]["avg"][t] if rx.get("c4") else x["o"][t])
                if not x["trd"][t] or not (np.isfinite(o_t) and o_t > 0):
                    cnt["buy_blocked_halt"] += 1; continue
                if x["up_o"][t]:
                    cnt["buy_blocked_limit_up"] += 1; continue
                amt = min(sval[k] / n_i, scash[k])
                if amt <= 1e-12:
                    break
                scash[k] -= amt
                if real:
                    xs = rx["X"][s]; Q = rx["cap"] * amt / eq[t - 1]
                    ie = xs["sig20"][t] * np.sqrt(Q / xs["adv20"][t]) if (np.isfinite(xs["adv20"][t]) and xs["adv20"][t] > 0 and np.isfinite(xs["sig20"][t])) else 0.0
                    pos[s] = [amt / (o_t * (1 + ie)), amt, k]
                    prate[s] = COST + 2 * rx.get("s", 0.0) + (2 * max(rx["m5"] / Q - 0.001425, 0.0) if rx.get("m5") else 0.0)
                else:
                    pos[s] = [amt / o_t, amt, k]
                cnt["buy"] += 1; buyd[t] += amt; trades.append((t, s, "buy", o_t))
        # ── 計值
        hv = [0.0] * K
        for s, (u, _, k) in pos.items():
            hv[k] += u * P[s]["c"][t]
        sval = [scash[k] + hv[k] for k in range(K)]
        eq[t] = sum(sval)
        npos[t] = len(pos); cashf[t] = sum(scash) / eq[t] if eq[t] > 0 else np.nan
        if dec:
            snaps[t] = {s: (u * P[s]["c"][t] / eq[t], sind[k]) for s, (u, _, k) in pos.items()}
    eq[t1 + 1:] = eq[t1]
    for k in range(K):
        if sind[k] is not None:
            e_ = dict(sinfo[k]); e_.update(end=None, why="窗尾"); episodes.append(e_)
    return {"eq": eq, "npos": npos, "cashf": cashf, "costd": costd, "buyd": buyd, "cnt": dict(cnt), "episodes": episodes, "snaps": snaps, "trades": trades}


# ═════════════ 描述對照：定期換股（Q6；PRE.sim_ind E0 的同一套，排名換成回呼） ═════════════
def sim_per(C, t0, t1, cfg, rkfun, real=None):
    P, dl, ncal = C["P"], C["dl"], C["ncal"]
    SF = sfdays(C, t1)
    ver = cfg.get("ver", "pit"); K = cfg["K"]; S = cfg["S"]; order = cfg.get("order", "top")
    reb = PRE.reb_days(C, cfg["R"], t0, t1); rebset = set(reb)
    eq = np.ones(ncal); cash = 1.0
    pos = {}; pend = set(); pind = {}; pbuy = {}; prate = {}
    npos = np.zeros(ncal, np.int16); cashf = np.zeros(ncal); costd = np.zeros(ncal); buyd = np.zeros(ncal)
    cnt = Counter(); held = {}; episodes = []; picks = {}; snaps = {}; trades = []
    rx = real or {}
    for t in range(t0, t1 + 1):
        for s in [s for s in pos if SF.get(s) is not None and t == SF[s] + 1]:
            u, amt = pos.pop(s)
            px = P[s]["c"][t]; cr = prate.pop(s, COST)
            cash += u * px - amt * cr; costd[t] += amt * cr; cnt["stop_force"] += 1
            pend.discard(s); pind.pop(s, None); pbuy.pop(s, None); trades.append((t, s, "sf", px))
        sel = None
        if t in rebset:
            rk = rkfun(t)
            if rk is None:
                cnt["reb_skip_norank"] += 1
            else:
                chosen = list(rk) if order == "all" else list(rk[:K])
                Kd = len(chosen) if order == "all" else K
                PK = PRE.picks_at(C, ver, "W1", t)
                sel = []; div = {}; sind = {}
                for i in chosen:
                    lst = PK.get(i, {}).get(S, [])
                    if not lst:
                        cnt["ind_empty"] += 1
                    n_i = len(lst)
                    for s in lst:
                        sel.append(s); div[s] = Kd * n_i; sind[s] = i
            if sel is not None:
                pend = (pend | (set(pos) - set(sel))) - set(sel)
                for i in list(held):
                    if i not in chosen:
                        h = held.pop(i); episodes.append({"ind": i, "start": h["start"], "end": t, "why": "換股"})
                for i in chosen:
                    if i not in held:
                        held[i] = {"start": t}
                for s in sel:
                    if s in pos:
                        pind[s] = sind[s]
                picks[t] = list(chosen)
        for s in sorted(pend):
            x = P[s]; o_t = (rx["X"][s]["avg"][t] if rx.get("c4") else x["o"][t])
            if x["trd"][t] and not x["dn_o"][t] and np.isfinite(o_t) and o_t > 0:
                px = o_t; kd = "open"
            elif (not x["trd"][t]) and s in dl and t > dl[s]["last"] and dl[s]["status"].startswith("delisted"):
                px = x["c"][t]; kd = "delist"; cnt["delist_settled"] += 1
            else:
                cnt["sell_delayed_days"] += 1; continue
            u, amt = pos.pop(s)
            pxe = px
            if rx.get("cap") and kd == "open":
                xs = rx["X"][s]; Q = rx["cap"] * (u * px) / eq[t - 1]
                ix = xs["sig20"][t] * np.sqrt(Q / xs["adv20"][t]) if (np.isfinite(xs["adv20"][t]) and xs["adv20"][t] > 0 and np.isfinite(xs["sig20"][t])) else 0.0
                pxe = px * (1 - min(ix, 0.99))
            cr = prate.pop(s, COST)
            cash += u * pxe - amt * cr; costd[t] += amt * cr; cnt["sell"] += 1
            pend.discard(s); pind.pop(s, None); pbuy.pop(s, None); trades.append((t, s, kd, px))
        if sel is not None:
            for s in [s for s in sel if s not in pos]:
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
        hv = 0.0
        for s, (u, _) in pos.items():
            hv += u * P[s]["c"][t]
        eq[t] = cash + hv
        npos[t] = len(pos); cashf[t] = cash / eq[t] if eq[t] > 0 else np.nan
        if sel is not None:
            snaps[t] = {s: (u * P[s]["c"][t] / eq[t], pind.get(s)) for s, (u, _) in pos.items()}
    eq[t1 + 1:] = eq[t1]
    for i, h in held.items():
        episodes.append({"ind": i, "start": h["start"], "end": None, "why": "窗尾"})
    return {"eq": eq, "npos": npos, "cashf": cashf, "costd": costd, "buyd": buyd, "cnt": dict(cnt), "episodes": episodes, "picks": picks, "snaps": snaps,
            "trades": trades, "reb": reb}


def rk_rule(C, cfg, order="rule"):
    """定期版排名回呼：A 月 ＝ 換股日可用最新月、L ＝ 換股日前一交易日收盤。"""
    ver = cfg.get("ver", "pit")

    def f(t):
        RK = rank_tab(C, ver, t, t - 1)
        return cands(RK, cfg.get("P"), cfg.get("A"), cfg.get("L"), set(), order)
    return f


def gate_g1p(C):
    """閘 G1′：sim_per 用「只看 A」排名 ⇒ 與 PRE.sim_ind（E0）權益逐位元相同。"""
    out = []
    t0, t1 = C["win"]
    for (A_, K_, S_, R_) in (("A2", 1, "S1", "季"), ("A1", 3, "S2", "半年"), ("A3", 3, "S1", "年")):
        cfg = {"A": A_, "K": K_, "S": S_, "R": R_, "E": "E0", "ver": "pit", "order": "top", "elig": "W1"}
        ref = PRE.sim_ind(C, t0, t1, cfg)
        mine = sim_per(C, t0, t1, cfg, lambda t, A_=A_: (PRE.ranked("pit", A_, C["Mlast"][t], "top") or None))
        out.append({"段": C["name"], "格": f"{A_}|K{K_}|{S_}|{R_}|E0", "權益逐位元相同": bool(np.array_equal(ref["eq"], mine["eq"])), "買": mine["cnt"].get("buy", 0),
                    "ref買": ref["cnt"]["buy"]})
    return out


# ═════════════ 指標 ═════════════
def stats_c(res, a, b, t1):
    c, m, ratio = SC.seg_metrics(res["eq"], a, b)
    yrs = (b + 1 - a) / 245; meq = float(res["eq"][a:b + 1].mean())
    ep = [e for e in res["episodes"] if a <= e["start"] <= b]
    hd = [((e["end"] if e["end"] is not None else t1 + 1) - e["start"]) for e in ep]
    return {"年化": c, "回落": m, "比值": ratio, "年化波動": RR.ann_vol(res["eq"][a:b + 1]),
            "平均持股": float(res["npos"][a:b + 1].mean()), "現金比例": float(np.nanmean(res["cashf"][a:b + 1])),
            "每年換手": float(res["buyd"][a:b + 1].sum()) / meq / yrs, "成本／年": float(res["costd"][a:b + 1].sum()) / meq / yrs,
            "產業持有段數": len(ep), "平均持有天數": float(np.mean(hd)) if hd else np.nan, "持有天數中位": float(np.median(hd)) if hd else np.nan,
            "X1": sum(1 for e in ep if e["why"] == "X1"), "X2": sum(1 for e in ep if e["why"] == "X2"), "X1+X2": sum(1 for e in ep if e["why"] == "X1+X2"),
            "窗尾仍持有": sum(1 for e in ep if e["end"] is None)}


def ckey(c):
    return f"{c['P']}|L{c['L']}|{c['A']}|K{c['K']}|{c['S']}"


def cells():
    return [dict(P=p, L=l, A=a_, K=k, S=s) for p in PS for l in LS for a_ in AS for k in KS for s in SS]


def _cell_job(args):
    part, cfg = args
    C = G[part]; t0, t1 = C["win"]
    res = sim_cond(C, t0, t1, dict(cfg, ver="pit", order="rule"))
    out = {"key": ckey(cfg), **cfg}
    for nm, (a, b) in C["segp"].items():
        out.update({f"{nm}_{k}": v for k, v in stats_c(res, a, b, t1).items()})
    out["計數"] = json.dumps(res["cnt"], ensure_ascii=False)
    return out, res["eq"].astype(np.float64)


def _rand_job(args):
    part, cfg, r = args
    C = G[part]; t0, t1 = C["win"]
    res = sim_cond(C, t0, t1, dict(cfg, ver="pit", order="random"), rng=np.random.default_rng([SEED, r]))
    out = {"part": part, "r": r}
    for nm, (a, b) in C["segp"].items():
        c, m, ratio = SC.seg_metrics(res["eq"], a, b)
        out.update({f"{nm}_年化": c, f"{nm}_回落": m, f"{nm}_比值": ratio})
    return out


def precompute(C, vers=("pit",)):
    t0, t1 = C["win"]
    for v in vers:
        for tc in C["checks"]:
            rank_tab(C, v, tc, tc)
            PRE.picks_at(C, v, "W1", tc + 1)
        for R_ in RS:
            for t in PRE.reb_days(C, R_, t0, t1):
                rank_tab(C, v, t, t - 1); PRE.picks_at(C, v, "W1", t)


# ═════════════ 丙 ═════════════
def daily_diff(C, A, L, ver="pit"):
    """Q9 ①：每個交易日收盤的 {產業: 名次差}（可排名者）。"""
    out = {}
    for t in range(C["win"][0] - 1, C["ncal"]):
        RK = rank_tab(C, ver, t, t)
        if RK["n"] < 2:
            out[t] = {}; continue
        d = RK["pA"][A] - RK["pL"][L]
        out[t] = {nm: float(d[k]) for k, nm in enumerate(RK["names"])}
    return out


def catch_rows(C, eps, dd, I):
    rows = []; n = C["ncal"]
    for e in eps:
        tc = e["sig"]; i = e["ind"]; hit = None
        for t in range(tc + 1, n):
            v = dd.get(t, {}).get(i)
            if v is not None and v <= 0:
                hit = t; break
        x = I.get(i)
        fol = n - 1 - tc
        r = {"段": e.get("段"), "產業": i, "訊號日": str(C["cal"][tc].date()), "追上日": str(C["cal"][hit].date()) if hit else "",
             "追上天數": (hit - tc) if hit else np.nan, "跟蹤天數": fol, "250日內追上": int(hit is not None and hit - tc <= 250),
             "未滿250日": int(hit is None and fol < 250),
             "追上前報酬": float(x[0][hit] / x[0][tc] - 1) if (hit and x is not None and np.isfinite(x[0][hit]) and np.isfinite(x[0][tc])) else np.nan}
        rows.append(r)
    return rows


def after_rows(eps, A, ver="pit", who=""):
    rows = []
    va = "現值" if ver == "現值" else "pit"
    for e in eps:
        M0 = e["M"]; r = {"誰": who, "段": e.get("段"), "產業": e["ind"], "訊號月": M0, "A": A}
        for h in (3, 6, 9, 12):
            v = G["AT"].get((va, PRE.mshift(M0, h)), {}).get(e["ind"])
            r[f"M+{h}"] = (float(v[AI[A]] > 0) if (v is not None and v[0] >= 5 and np.isfinite(v[AI[A]])) else np.nan)
        rows.append(r)
    return rows


def eat_rows(C, I, eps, t1, segp):
    rows = []; n = C["ncal"]
    for e in eps:
        z = I.get(e["ind"]); s = e["start"]
        if z is None or not np.isfinite(z[0][s - 1]):
            continue
        x = z[0]; Is = x[s - 1]
        low = np.nanmin(x[max(0, s - 250):s]); post = x[s:min(n, s + 500)]
        top = np.nanmax(post) if np.isfinite(post).any() else np.nan
        den = math.log(top / low) if (np.isfinite(top) and top > low) else np.nan
        xe = e["end"] if e["end"] is not None else t1 + 1
        Ie = x[xe - 1]
        rows.append({"段": next((k for k, (a, b) in segp.items() if a <= s <= b), ""), "產業": e["ind"], "進場": str(C["cal"][s].date()),
                     "已漲250": Is / np.nanmin(x[max(0, s - 250):s]) - 1, "起漲到頂": den, "吃到幾成": math.log(top / Is) / den if np.isfinite(den) else np.nan,
                     "之後沒再創高": int(np.isfinite(top) and top <= Is), "實際持有吃到幾成": math.log(Ie / Is) / den if (np.isfinite(den) and np.isfinite(Ie)) else np.nan,
                     "持有報酬": Ie / Is - 1, "窗尾仍持有": int(e["end"] is None), "未滿500日": int(s + 500 > n)})
    return rows


# ═════════════ 主程式 ═════════════
def run(a):
    T00 = time.time()
    os.makedirs(WORK, exist_ok=True)
    sha = setup(a)
    ap_ = os.path.join(OUT, "A_table.csv.gz")
    if a.reuse_a and os.path.exists(ap_) and os.path.exists(ap_ + ".src.json"):
        src = json.load(open(ap_ + ".src.json", encoding="utf-8")); log("[A 表] 讀既有檔（--reuse-a）")
    else:
        AT, src = build_A(a)
        AT.to_csv(ap_, index=False, float_format="%.17g", compression={"method": "gzip", "mtime": 0})
        json.dump(src, open(ap_ + ".src.json", "w", encoding="utf-8"), ensure_ascii=False)
    AT = pd.read_csv(ap_, float_precision="round_trip")
    install_A(AT)
    pinfo = build_panel_eotc(a)
    META = {"讀法寫死": TIME, "main": sha, "成本": COST, "GATE_V2": True, "PIT 來源計數（pit 版、代號×月）": src, "早年面板": pinfo}
    Cm = prep_part("main", MAIN_W, SEG, a); Ce = prep_part("early", EARLY_A, {"早年": EARLY_A}, a)
    META["段資訊"] = {"main": Cm["info"], "early": Ce["info"]}
    t0m, t1m = Cm["win"]
    RR.use_snapshot()
    cf, mf = R13.window_stats(Cm["bench"], 0, Cm["ncal"], t0m, t1m + 1)
    anchor = repr(float(cf)) == repr(PRE.ANCHOR[0]) and repr(float(mf)) == repr(PRE.ANCHOR[1])
    Z = {nm: SC.seg_metrics(Cm["bench"], x, y) for nm, (x, y) in Cm["segp"].items()}
    Z["早年"] = SC.seg_metrics(Ce["bench"], *Ce["segp"]["早年"])
    log(f"[0050] 主窗錨逐位元 {anchor}｜" + "｜".join(f"{k} {v[0]:.2%}／{v[1]:.2%}／{v[2]:.3f}" for k, v in Z.items()))
    if not anchor:
        raise SystemExit("⛔ 0050 錨不過")
    META["0050"] = {k: dict(zip(("年化", "回落", "比值"), v)) for k, v in Z.items()}
    for C in (Cm, Ce):
        precompute(C)
    G1 = gate_g1p(Cm) + gate_g1p(Ce)
    META["閘G1′"] = G1
    log(f"[閘 G1′] {G1}")
    if not all(g["權益逐位元相同"] for g in G1):
        raise SystemExit("⛔ 閘 G1′ 不過")
    # ── 72 格 × 兩段
    t0_ = time.time(); EQ = {}; TT = {}
    for part in ("main", "early"):
        with Pool(a.procs) as pool:
            res = pool.map(_cell_job, [(part, c) for c in cells()], chunksize=2)
        TT[part] = pd.DataFrame([r[0] for r in res]); EQ[part] = {r[0]["key"]: r[1] for r in res}
        log(f"[72 格 {part}] {time.time() - t0_:.0f}s")
    TM, TE = TT["main"], TT["early"]
    c0, m0, _ = Z["探索"]
    TM["退化"] = (TM["探索_平均持股"] < 3) | (TM["探索_現金比例"] > 0.30)
    TM["探索_標籤"] = [PRE.lab(c, m, c0, m0) for c, m in zip(TM["探索_年化"], TM["探索_回落"])]
    TM["確認_標籤"] = [PRE.lab(c, m, Z["確認"][0], Z["確認"][1]) for c, m in zip(TM["確認_年化"], TM["確認_回落"])]
    TE["早年_標籤"] = [PRE.lab(c, m, Z["早年"][0], Z["早年"][1]) for c, m in zip(TE["早年_年化"], TE["早年_回落"])]
    ecols = [c for c in TE.columns if c.startswith("早年_")]
    TM = TM.merge(TE[["key"] + ecols].rename(columns={}), on="key", how="left")
    TM = TM.merge(TE[["key", "計數"]].rename(columns={"計數": "早年計數"}), on="key", how="left")
    cand = TM[~TM["退化"]].copy(); cand["過"] = cand["探索_標籤"] == "合格"
    pool_ = cand[cand["過"]] if cand["過"].any() else cand
    oi = lambda col, seq: pool_[col].map({v: i for i, v in enumerate(seq)})
    pool_ = pool_.assign(_p=oi("P", PS), _l=oi("L", LS), _a=oi("A", AS), _k=oi("K", KS), _s=oi("S", SS))
    best = pool_.sort_values(["探索_比值", "探索_年化", "_p", "_l", "_a", "_k", "_s"], ascending=[False, False, True, True, True, True, True]).iloc[0]
    ck = best["key"]; CH = {"P": best["P"], "L": int(best["L"]), "A": best["A"], "K": int(best["K"]), "S": best["S"]}
    lc, le = best["確認_標籤"], best["早年_標籤"]
    fin_ = min((lc, le), key=lambda z: RANKL.get(z, -1))
    final = {"合格": "暫定合格（事後重切；只進前瞻紀錄）", "另列": "另列（事後重切，最多暫定；只進前瞻紀錄）"}.get(fin_, fin_)
    TM.to_csv(os.path.join(OUT, "cells.csv"), index=False, float_format="%.10g")
    nd = ~TM["退化"]
    META["挑格"] = {"格數": int(len(TM)), "退化格數": int(TM["退化"].sum()), "非退化": int(nd.sum()), "探索過判準格數": int(cand["過"].sum()), "挑中": ck, "挑中參數": CH,
                  **{sg: {k: float(best[f"{sg}_{k}"]) for k in ("年化", "回落", "比值")} for sg in ("探索", "確認", "早年")},
                  "確認標籤": lc, "早年標籤": le, "判定": final,
                  "兩段都合格格數（全 72）": int(((TM["確認_標籤"] == "合格") & (TM["早年_標籤"] == "合格")).sum()),
                  "兩段都合格格數（非退化）": int(((TM["確認_標籤"] == "合格") & (TM["早年_標籤"] == "合格") & nd).sum()),
                  "確認段合格格數": int((TM["確認_標籤"] == "合格").sum()), "早年段合格格數": int((TM["早年_標籤"] == "合格").sum()),
                  "確認段另列以上格數": int(TM["確認_標籤"].isin(["合格", "另列"]).sum())}
    log(f"[挑格] {json.dumps(META['挑格'], ensure_ascii=False)}")
    json.dump(META, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    # ── 挑中格細項
    CHR = {}; EPS = []
    for part in ("main", "early"):
        C = G[part]; t0, t1 = C["win"]
        res = sim_cond(C, t0, t1, dict(CH, ver="pit", order="rule"))
        assert np.array_equal(res["eq"], EQ[part][ck])
        CHR[part] = res
        for e in res["episodes"]:
            e["段"] = next((k for k, (x, y) in C["segp"].items() if x <= e["start"] <= y), "")
            e["part"] = part
            EPS.append({**e, "進場日": str(C["cal"][e["start"]].date()), "訊號日": str(C["cal"][e["sig"]].date()),
                        "出場日": str(C["cal"][e["end"]].date()) if e["end"] is not None else "", "持有天數": ((e["end"] if e["end"] is not None else t1 + 1) - e["start"])})
    ED = pd.DataFrame(EPS)
    ED.to_csv(os.path.join(OUT, "chosen_episodes.csv"), index=False, float_format="%.8g")
    IC = ED.groupby(["段", "ind"]).size().rename("次數").reset_index().sort_values(["段", "次數", "ind"], ascending=[True, False, True])
    IC.to_csv(os.path.join(OUT, "industry_counts.csv"), index=False)
    DET = {}
    for part in ("main", "early"):
        C = G[part]; res = CHR[part]; t0, t1 = C["win"]
        for nm, (x, y) in C["segp"].items():
            st = stats_c(res, x, y, t1); ov, nov = PRE.overlap50(C, res, x, y)
            DET[nm] = {**st, "0050重疊率": ov, "重疊率換倉日數": nov}
        DET[f"{part}_計數"] = res["cnt"]
        tail = [{"產業": e["ind"], "進場日": str(C["cal"][e["start"]].date()), "已持有交易日": t1 + 1 - e["start"]} for e in res["episodes"] if e["end"] is None]
        DET[f"{part}_窗尾仍持有"] = {"窗尾": str(C["cal"][t1].date()), "件數": len(tail), "明細": tail}
        hd = [((e["end"] if e["end"] is not None else t1 + 1) - e["start"]) for e in res["episodes"]]
        DET[f"{part}_持有天數分佈"] = {"筆數": len(hd), **({f"p{q}": float(np.percentile(hd, q)) for q in (10, 25, 50, 75, 90)} if hd else {}),
                                     "最長": int(max(hd)) if hd else None, "≤21": sum(h <= 21 for h in hd), "22～63": sum(21 < h <= 63 for h in hd),
                                     "64～250": sum(63 < h <= 250 for h in hd), "＞250": sum(h > 250 for h in hd)}
    META["挑中格細項"] = DET
    YR = []
    for part in ("main", "early"):
        C = G[part]; t0, t1 = C["win"]
        yr = PRE.year_rets(CHR[part]["eq"], C["cal"], t0, t1); yb = PRE.year_rets(C["bench"] / C["bench"][t0], C["cal"], t0, t1)
        for y in yr:
            YR.append({"段": part, "年": y, "挑中格": yr[y], "0050": yb[y]})
    # ── 對照
    CTRL = {}; PREV = {}
    for part in ("main", "early"):
        C = G[part]; t0, t1 = C["win"]
        rp = PRE.sim_ind(C, t0, t1, dict(PRE_CH, ver="pit", order="top", elig="W1"))
        PREV[part] = rp
        for sg, (x, y) in C["segp"].items():
            CTRL.setdefault("前件挑中格（本件設定重跑）", {})[sg] = PRE.stats(rp, x, y, t1)
        yp = PRE.year_rets(rp["eq"], C["cal"], t0, t1)
        for r_ in YR:
            if r_["段"] == part and r_["年"] in yp:
                r_["前件挑中格"] = yp[r_["年"]]
        for R_ in RS:
            rs_ = sim_per(C, t0, t1, dict(CH, R=R_, ver="pit"), rk_rule(C, CH))
            for sg, (x, y) in C["segp"].items():
                CTRL.setdefault(f"定期換股（{R_}）", {})[sg] = PRE.stats(rs_, x, y, t1)
        rv = sim_per(C, t0, t1, dict(CH, R="季", ver="pit"), rk_rule(C, CH, "rev"))
        al = sim_per(C, t0, t1, dict(CH, R="季", ver="pit", order="all"), rk_rule(C, CH, "all"))
        for sg, (x, y) in C["segp"].items():
            CTRL.setdefault("反向臂（季換、A 前三分之一裡已漲最多）", {})[sg] = PRE.stats(rv, x, y, t1)
            CTRL.setdefault("全產業等權（季換）", {})[sg] = PRE.stats(al, x, y, t1)
    pm = json.load(open("backtest/resultsIndRev/prereg/meta.json", encoding="utf-8"))
    CTRL["前件原數字（前件設定）"] = {sg: pm["挑格"][sg] for sg in ("探索", "確認", "早年")}
    CTRL["營量v1_T1"] = pm["對照"]["營量v1_T1"]
    pd.DataFrame(YR).to_csv(os.path.join(OUT, "years.csv"), index=False, float_format="%.8g")
    t0_ = time.time()
    jobs = [(part, CH, r) for part in ("main", "early") for r in range(a.reps)]
    with Pool(a.procs) as pool:
        RD = pd.DataFrame(pool.map(_rand_job, jobs, chunksize=10))
    RD.to_csv(os.path.join(OUT, "random.csv.gz"), index=False, compression={"method": "gzip", "mtime": 0})
    log(f"[隨機] {len(jobs)} 次｜{time.time() - t0_:.0f}s")
    RAND = {}
    for part in ("main", "early"):
        for sg in G[part]["segp"]:
            g = RD[RD["part"] == part]
            xx = g[f"{sg}_年化"].to_numpy(float); rr_ = g[f"{sg}_比值"].to_numpy(float)
            RAND[sg] = {"中位": float(np.nanmedian(xx)), "p10": float(np.nanquantile(xx, .1)), "p90": float(np.nanquantile(xx, .9)),
                        "回落中位": float(g[f"{sg}_回落"].median()), "p_年化": float(np.nanmean(xx >= DET[sg]["年化"])),
                        "p_比值": float(np.nanmean(rr_ >= DET[sg]["比值"])), "贏0050比例": float(np.nanmean(xx > Z[sg][0]))}
    CTRL["隨機"] = RAND
    META["對照"] = CTRL
    # ── 變體
    VAR = []

    def addv(name, part, cfg, real=None):
        C = G[part]; t0, t1 = C["win"]
        if real is not None:
            from backtest import researchSlip as SL
            need = sorted({s for _, s, k, _ in CHR[part]["trades"] if k == "buy"})
            X = C.setdefault("Xreal", {})
            for s in need:
                if s not in X:
                    X[s] = SL.stock_extra(s, C["mk"].get(s, "twse"), C["cal"], C["ncal"])
            real = dict(real, X=X)
        res = sim_cond(C, t0, t1, cfg, real=real)
        for sg, (x, y) in C["segp"].items():
            st = stats_c(res, x, y, t1); b = SC.seg_metrics(C["bench"], x, y)
            VAR.append({"版本": name, "段": sg, **st, "0050年化": b[0], "0050回落": b[1], "標籤": PRE.lab(st["年化"], st["回落"], b[0], b[1])})
        return res
    base = dict(CH, order="rule")
    for part in ("main", "early"):
        D.DATA = G[part]["data"]
        addv("主表（industry_pit）", part, dict(base, ver="pit"))
        addv("① 現值（industry.csv）", part, dict(base, ver="現值"))
        addv("② 剔除 2023 新增四類", part, dict(base, ver="剔除2023"))
        addv("現實版（C1 0.3%＋C2 50 萬＋C4）", part, dict(base, ver="pit"), real=dict(s=0.003, cap=CAP, c4=True))
        addv("現實版＋C5 低消 20 元", part, dict(base, ver="pit"), real=dict(s=0.003, cap=CAP, c4=True, m5=20))
    pd.DataFrame(VAR).to_csv(os.path.join(OUT, "variants.csv"), index=False, float_format="%.10g")
    # ── 丙
    CC, CA, CE = [], [], []
    for part in ("main", "early"):
        C = G[part]; t0, t1 = C["win"]
        I = C["IX"]["pit"]
        eps = [e for e in CHR[part]["episodes"]]
        dd = daily_diff(C, CH["A"], CH["L"])
        for r in catch_rows(C, eps, dd, I):
            r["part"] = part; CC.append(r)
        for r in after_rows(eps, CH["A"], who="本件挑中格"):
            r["part"] = part; CA.append(r)
        pe = []
        for t, inds in sorted(PREV[part]["picks"].items()):
            for i in inds:
                pe.append({"ind": i, "M": C["Mlast"][t], "段": next((k for k, (x, y) in C["segp"].items() if x <= t <= y), "")})
        for r in after_rows(pe, "A2", who="前件挑中格"):
            r["part"] = part; CA.append(r)
        for r in eat_rows(C, I, eps, t1, C["segp"]):
            r["part"] = part; r["誰"] = "本件挑中格"; CE.append(r)
        Ipre = {k: v[0] for k, v in I.items()}
        for r in PRE.pair_rows(C, Ipre, PREV[part]["picks"], PREV[part]["reb"], t1, C["segp"]):
            if r.get("缺") == 0:
                CE.append({"段": r["段"], "產業": r["產業"], "進場": r["日"], "已漲250": r["已漲250"], "起漲到頂": r["起漲到頂"], "吃到幾成": r["吃到幾成"],
                           "之後沒再創高": r["之後沒再創高"], "實際持有吃到幾成": r["實際持有吃到幾成"], "持有報酬": r["持有報酬"], "窗尾仍持有": 0,
                           "未滿500日": r["未滿500日"], "part": part, "誰": "前件挑中格（每季一期）"})
    CCD, CAD, CED = pd.DataFrame(CC), pd.DataFrame(CA), pd.DataFrame(CE)
    CCD.to_csv(os.path.join(OUT, "c_catch.csv"), index=False, float_format="%.8g")
    CAD.to_csv(os.path.join(OUT, "c_after.csv"), index=False, float_format="%.8g")
    CED.to_csv(os.path.join(OUT, "c_eat.csv"), index=False, float_format="%.8g")
    META["丙"] = c_summary(CCD, CAD, CED)
    np.savez_compressed(os.path.join(OUT, "eq.npz"), main=EQ["main"][ck], early=EQ["early"][ck], pre_main=PREV["main"]["eq"], pre_early=PREV["early"]["eq"],
                        bench_main=Cm["bench"], bench_early=Ce["bench"])
    META["先驗"] = priors(META, TM, ED, CCD)
    META["耗時秒"] = round(time.time() - T00)
    json.dump(META, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] {time.time() - T00:.0f}s")


def c_summary(CCD, CAD, CED):
    S = {}
    for part, g in CCD.groupby("part"):
        ok = g[(g["250日內追上"] == 1) | (g["未滿250日"] == 0)]
        h = g["追上天數"].dropna()
        S[f"追上|{part}"] = {"筆數": int(len(g)), "有追上": int(g["追上天數"].notna().sum()), "250日內追上": int(g["250日內追上"].sum()),
                            "分母（剔未滿250日）": int(len(ok)), "250日內追上比例": float(ok["250日內追上"].mean()) if len(ok) else None,
                            "未滿250日": int(g["未滿250日"].sum()), "追上天數中位": float(h.median()) if len(h) else None,
                            "追上天數p25": float(h.quantile(.25)) if len(h) else None, "追上天數p75": float(h.quantile(.75)) if len(h) else None,
                            "追上前報酬中位": float(g["追上前報酬"].median()) if g["追上前報酬"].notna().any() else None,
                            "追上前報酬平均": float(g["追上前報酬"].mean()) if g["追上前報酬"].notna().any() else None}
    for (who, part), g in CAD.groupby(["誰", "part"]):
        S[f"之後A|{who}|{part}"] = {"筆數": int(len(g)), **{f"M+{h}仍>0比例": (float(g[f"M+{h}"].mean()) if g[f"M+{h}"].notna().any() else None) for h in (3, 6, 9, 12)},
                                    **{f"M+{h}有值": int(g[f"M+{h}"].notna().sum()) for h in (3, 6, 9, 12)}}
    for (who, part), g in CED.groupby(["誰", "part"]):
        S[f"吃到|{who}|{part}"] = {"筆數": int(len(g)), "已漲250中位": float(g["已漲250"].median()), "吃到幾成中位": float(g["吃到幾成"].median()),
                                   "之後沒再創高比例": float(g["之後沒再創高"].mean()), "實際持有吃到幾成中位": float(g["實際持有吃到幾成"].median()),
                                   "持有報酬平均": float(g["持有報酬"].mean()), "持有報酬中位": float(g["持有報酬"].median()), "未滿500日": int(g["未滿500日"].sum())}
    return S


def priors(META, TM, ED, CCD):
    out = []
    n2 = META["挑格"]["兩段都合格格數（全 72）"]
    out.append(("①", "兩段都合格的格 0 個", f"全 72 格兩段都合格 {n2} 格（非退化 {META['挑格']['兩段都合格格數（非退化）']} 格）", "對" if n2 == 0 else "錯"))
    mine = META["挑格"]["確認"]["年化"]; pre = META["對照"]["前件挑中格（本件設定重跑）"]["確認"]["年化"]
    out.append(("②", "挑中格確認段年化不高於前件挑中格同窗", f"挑中格 {mine:+.1%} vs 前件挑中格（本件設定重跑）{pre:+.1%}", "對" if mine <= pre else "錯"))
    ne = int((~ED["ind"].isin(ELEC)).sum()); tot = int(len(ED))
    seg = "；".join(f"{sg} {int((~g['ind'].isin(ELEC)).sum())}/{len(g)}" for sg, g in ED.groupby("段"))
    out.append(("③", "挑中次數裡非電子類占一半以上", f"全部 {ne}/{tot}（{ne / tot:.0%}）；{seg}" if tot else "無挑中", "對" if tot and ne / tot > 0.5 else "錯"))
    g = CCD[(CCD["250日內追上"] == 1) | (CCD["未滿250日"] == 0)]
    p4 = float(g["250日內追上"].mean()) if len(g) else np.nan
    out.append(("④", "挑中後 250 日內股價追上的比例 ≥ 50%", f"{int(g['250日內追上'].sum())}/{len(g)}（{p4:.0%}；另 {int(CCD['未滿250日'].sum())} 筆未滿 250 日不計）" if len(g) else "—",
                "對" if np.isfinite(p4) and p4 >= 0.5 else "錯"))
    CT = META["對照"]; mc = META["挑格"]
    rr = {R_: CT[f"定期換股（{R_}）"] for R_ in RS}
    ok5 = any(rr[R_]["確認"]["年化"] >= mc["確認"]["年化"] for R_ in RS)
    txt = "；".join(f"{sg}：條件 {mc[sg]['年化']:+.1%}｜" + "、".join(f"{R_} {rr[R_][sg]['年化']:+.1%}" for R_ in RS) for sg in ("探索", "確認", "早年"))
    out.append(("⑤", "定期換股（三種 R 任一）年化不輸條件版（以確認段判）", txt, "對" if ok5 else "錯"))
    return out


# ═════════════ 查核（Q10；獨立寫法） ═════════════
def ck_adj(DATA, sid, cal_s):
    """自己還原：原始收盤（≤0 ⇒ 缺）× 第一個「事件日 ＞ d」的 cum_factor；對日曆 ffill。"""
    raw = {}
    p = os.path.join(DATA, "stocks", f"{sid}.csv")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["date"] in raw:
                continue
            try:
                c = float(r["close"])
            except (TypeError, ValueError):
                c = float("nan")
            bad = False
            for k in ("open", "high", "low"):
                try:
                    if float(r[k]) <= 0:
                        bad = True
                except (TypeError, ValueError):
                    pass
            raw[r["date"]] = c if (c == c and c > 0 and not bad) else float("nan")
    ev = []
    pa = os.path.join(DATA, "adj", f"{sid}.csv")
    if os.path.exists(pa):
        with open(pa, encoding="utf-8") as f:
            ev = sorted((r["date"], float(r["cum_factor"])) for r in csv.DictReader(f))
    out = []; last = float("nan"); j = 0
    for dd in cal_s:
        while j < len(ev) and ev[j][0] <= dd:
            j += 1
        c = raw.get(dd, float("nan"))
        if c == c:
            last = c * (ev[j][1] if j < len(ev) else 1.0)
        out.append(last)
    return out


def ck_rowok(DATA, sid):
    """自己判板期／興櫃列：逐日檔每列 market ∈ twse／tpex 且名稱不含「-創」「-KY創」。"""
    p = os.path.join(DATA, "stocks", f"{sid}.csv")
    if not os.path.exists(p):
        return [], []
    seen = {}
    with open(p, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            nm = r.get("name") or ""; mk_ = r.get("market", "twse") or ""
            seen[r["date"]] = (mk_ in ("twse", "tpex")) and ("-創" not in nm) and ("-KY創" not in nm)
    ds = sorted(seen)
    return ds, [seen[d] for d in ds]


def ck_pitok(rows, d):
    ds, oks = rows
    k = bisect.bisect_right(ds, d) - 1
    return True if k < 0 else oks[k]


def ck_panel(path, col):
    out = defaultdict(set)
    import gzip
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if col == "W1":
                ok = r["eligible"] == "True"
            else:
                ok = r["liq_ok"] == "True" and r["bars_ok"] == "True"
            if ok:
                out[r["measure_date"][:10]].add(r["stock_id"])
    return out


def ck_avg_rank(vals):
    n = len(vals); out = []
    for v in vals:
        lo = sum(1 for w in vals if w < v); eq_ = sum(1 for w in vals if w == v)
        out.append((lo + (eq_ + 1) / 2 - 1) / (n - 1))
    return out


def _ckA_job(args):
    M, dstr = args
    return M, PRE.ck_A(G["K_"], M, dstr)


def check(a):
    T00 = time.time()
    META = json.load(open(os.path.join(OUT, "meta.json"), encoding="utf-8"))
    sha = setup(a, META["main"])
    AT = pd.read_csv(os.path.join(OUT, "A_table.csv.gz"), float_precision="round_trip")
    install_A(AT)
    K_ = PRE.ck_load(PRE._C["DATA"]); G["K_"] = K_
    RES = {"讀法寫死": TIME, "main": sha}; nd = 0
    rng = np.random.default_rng(SEED)
    # ① A
    pool_ = AT[(AT["ver"] == "pit") & (AT["公司數"] >= 5) & (AT["M"] >= "2011-01")].reset_index(drop=True)
    p26 = pool_[pool_["M"] >= "2026-01"].reset_index(drop=True); pold = pool_[pool_["M"] < "2026-01"].reset_index(drop=True)
    pick = [pold.iloc[int(rng.integers(len(pold)))], p26.iloc[int(rng.integers(len(p26)))]]
    o1 = []
    for r in pick:
        mine = PRE.ck_A(K_, r["M"], str(PRE._C["pitday"][r["M"]].date())).get(r["產業"])
        diff = {k: (mine[j] if mine else None, float(r[k])) for j, k in enumerate(("A1", "A2", "A3", "公司數"))}
        bad = [k for k, (x, y) in diff.items() if x is None or not (abs(x - y) <= 1e-12 * max(1, abs(y)))]
        nd += len(bad); o1.append({"月": r["M"], "判定日": str(PRE._C["pitday"][r["M"]].date()), "產業": r["產業"], "獨立／主程式": diff, "不同": bad})
    RES["① A"] = o1; log(f"[查核 ①] {o1}")
    # 兩段
    out2, out3, out4 = [], [], []
    CL = cells(); chosen = META["挑格"]["挑中參數"]
    others = [c for c in CL if ckey(c) != META["挑格"]["挑中"]]
    other = others[int(rng.integers(len(others)))]
    targets = [dict(chosen), other]
    RES["抽中格"] = ckey(other)
    for part, win, segs in (("main", MAIN_W, SEG), ("early", EARLY_A, {"早年": EARLY_A})):
        C = prep_part(part, win, segs, a)
        cal = C["cal"]; cal_s = [str(x.date()) for x in cal]; t0, t1 = C["win"]; n = C["ncal"]
        if part == "main":
            g1 = gate_g1p(C)
        else:
            g1 = gate_g1p(C)
        RES.setdefault("⑤ 閘 G1′", []).extend(g1); nd += sum(not g["權益逐位元相同"] for g in g1)
        # 獨立面板、板期、產業、還原價
        pn = ck_panel(C["panel"], "W1" if part == "main" else "X")
        pnW = ck_panel(C["panel"], "W1")
        uni = set(C["mk"])
        mds = sorted(pn)
        allsid = sorted({s for v in pn.values() for s in v} | {s for v in pnW.values() for s in v})
        allsid = [s for s in allsid if s in uni]
        rok = {s: ck_rowok(C["data"], s) for s in allsid}
        px = {}
        for s in allsid:
            v = ck_adj(C["data"], s, cal_s)
            if v is not None:
                px[s] = v
        # 產業日報酬（pit）
        rd = defaultdict(lambda: [float("nan")] * n)
        for j, md in enumerate(mds):
            p0 = cal_s.index(md); p1 = cal_s.index(mds[j + 1]) if j + 1 < len(mds) else n
            grp = defaultdict(list)
            for s in pn[md]:
                if s not in uni or s not in px or not ck_pitok(rok[s], md):
                    continue
                i = PRE.ck_ind(K_, s, md)
                if i is None or i in EXCL:
                    continue
                grp[i].append(s)
            for i, ss in grp.items():
                arr = rd[i]
                for t in range(max(p0, 1), p1):
                    vs = [px[s][t] / px[s][t - 1] - 1 for s in ss if px[s][t] == px[s][t] and px[s][t - 1] == px[s][t - 1]]
                    arr[t] = sum(vs) / len(vs) if vs else float("nan")
        lev = {}
        for i, arr in rd.items():
            f0 = next((k for k in range(n) if arr[k] == arr[k]), None)
            if f0 is None or f0 == 0:
                continue
            x = [float("nan")] * n; x[f0 - 1] = 1.0; v = 1.0
            for k in range(f0, n):
                v *= 1 + (arr[k] if arr[k] == arr[k] else 0.0); x[k] = v
            lev[i] = (x, f0, arr)

        def Lr(i, t, L):
            z = lev.get(i)
            if z is None or t - L < 0:
                return float("nan")
            x, f0, arr = z
            if t - L < f0 - 1 or any(arr[k] != arr[k] for k in range(t - L + 1, t + 1)):
                return float("nan")
            return x[t] / x[t - L] - 1
        # A（獨立）
        Ms = sorted({C["Mlast"][tc] for tc in C["checks"] if C["Mlast"][tc]})
        with Pool(a.procs) as pool:
            ATk = dict(pool.map(_ckA_job, [(M, str(PRE._C["pitday"][M].date())) for M in Ms]))
        # ② ③ 全部檢查日
        bad2 = 0; bad3 = 0; ntest = 0; RKk = {}
        for tc in C["checks"]:
            M = C["Mlast"][tc]; TA = ATk.get(M, {})
            rows = []
            for i in sorted(TA):
                a1, a2, a3, c_ = TA[i]
                if not (c_ >= 5 and all(v_ == v_ for v_ in (a1, a2, a3))):
                    continue
                ls_ = [Lr(i, tc, L) for L in LS]
                if any(v_ != v_ for v_ in ls_):
                    continue
                rows.append((i, {"A1": a1, "A2": a2, "A3": a3}, dict(zip(LS, ls_)), c_))
            names = [r[0] for r in rows]
            pa = {A_: ck_avg_rank([r[1][A_] for r in rows]) if len(rows) >= 2 else [] for A_ in AS}
            pl = {L: ck_avg_rank([r[2][L] for r in rows]) if len(rows) >= 2 else [] for L in LS}
            RKk[tc] = {"names": names, "A": {A_: [r[1][A_] for r in rows] for A_ in AS}, "L": {L: [r[2][L] for r in rows] for L in LS}, "pA": pa, "pL": pl,
                       "Aall": {i: (TA[i][3], TA[i][0], TA[i][1], TA[i][2]) for i in TA}}
            RK = rank_tab(C, "pit", tc, tc)
            # ② L 報酬：全部產業（主程式指數有的 ∪ 獨立有的）
            for i in sorted(set(C["IX"]["pit"]) | set(lev)):
                for L in LS:
                    x1 = lret(C["IX"]["pit"], i, tc, L); x2 = Lr(i, tc, L); ntest += 1
                    if (x1 == x1) != (x2 == x2) or (x1 == x1 and abs(x1 - x2) > 1e-9 * max(1, abs(x2))):
                        bad2 += 1
                        if bad2 <= 5:
                            out2.append({"段": part, "日": cal_s[tc], "產業": i, "L": L, "主程式": x1, "獨立": x2})
            # ③ 集合與百分位
            if names != RK["names"]:
                bad3 += 1; out3.append({"段": part, "日": cal_s[tc], "集合不同": sorted(set(names) ^ set(RK["names"]))[:10]})
            else:
                for A_ in AS:
                    if len(names) >= 2 and max(abs(x - y) for x, y in zip(pa[A_], RK["pA"][A_])) > 1e-9:
                        bad3 += 1
                for L in LS:
                    if len(names) >= 2 and max(abs(x - y) for x, y in zip(pl[L], RK["pL"][L])) > 1e-9:
                        bad3 += 1
            for cfg in targets:
                l1 = ck_cands(RKk[tc], cfg, set())
                l2 = cands(RK, cfg["P"], cfg["A"], cfg["L"], set())
                if (l1 or []) != (l2 or []):
                    bad3 += 1; out3.append({"段": part, "日": cal_s[tc], "格": ckey(cfg), "獨立": l1, "主程式": l2})
        nd += bad2 + bad3
        RES.setdefault("② L 報酬", []).append({"段": part, "比對筆數": ntest, "不同": bad2, "例": out2[-5:]})
        RES.setdefault("③ 排名", []).append({"段": part, "檢查日": len(C["checks"]), "不同": bad3, "例": out3[-5:]})
        log(f"[查核 ②③ {part}] L 比對 {ntest} 不同 {bad2}｜排名不同 {bad3}")
        # ④ 獨立位置簿
        mcd = ck_mcap(C, cal_s)
        for cfg in targets:
            res = sim_cond(C, t0, t1, dict(cfg, ver="pit", order="rule"))
            eq2, tr2, hs2 = ck_sim(C, cfg, RKk, pnW, rok, mcd, K_, cal_s, t0, t1)
            hs1 = {t: sorted(w) for t, w in res["snaps"].items()}
            tr1 = [(t, s, k, float(p)) for t, s, k, p in res["trades"]]; tr2 = [(t, s, k, float(p)) for t, s, k, p in tr2]
            rel = float(np.nanmax(np.abs(res["eq"][t0:t1 + 1] / np.asarray(eq2[t0:t1 + 1]) - 1)))
            bad_h = [cal_s[t] for t in sorted(set(hs1) | set(hs2)) if hs1.get(t) != hs2.get(t)]
            bad_t = len(set(tr1) ^ set(tr2))
            ok = rel <= 1e-9 and not bad_h and bad_t == 0
            nd += 0 if ok else 1
            out4.append({"段": part, "格": ckey(cfg), "換倉日數": len(hs1), "交易筆數": len(tr1), "權益最大相對差": rel, "持股不同的換倉日": bad_h[:10], "交易不同筆數": bad_t, "通過": ok})
            log(f"[查核 ④] {out4[-1]}")
    RES["④ 逐筆重算"] = out4
    RES["不同項數"] = nd; RES["通過"] = nd == 0; RES["秒"] = round(time.time() - T00)
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[查核] 不同 {nd}｜通過 {nd == 0}")


def ck_cands(RKk, cfg, held):
    nm = RKk["names"]
    if len(nm) < 2:
        return None
    A_, L = cfg["A"], cfg["L"]
    out = []
    for k, i in enumerate(nm):
        av = RKk["A"][A_][k]; d = RKk["pA"][A_][k] - RKk["pL"][L][k]
        if av <= 0 or d <= 0:
            continue
        if cfg["P"] == "P1":
            out.append(((-d, i), i))
        elif RKk["pA"][A_][k] >= 2 / 3 - 1e-12:
            out.append(((RKk["L"][L][k], i), i))
    return [i for _, i in sorted(out) if i not in held]


def ck_mcap(C, cal_s):
    n = len(cal_s); out = {}
    if C["name"] == "main":
        for s in C["P"]:
            arr = [float("nan")] * n
            p = os.path.join(C["data"], "stocks", f"{s}.csv")
            day = {d: i for i, d in enumerate(cal_s)}
            with open(p, encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    try:
                        v = float(r["close"]) * float(r["shares"])
                    except (TypeError, ValueError):
                        continue
                    if r["date"] in day and v > 0 and arr[day[r["date"]]] != arr[day[r["date"]]]:
                        arr[day[r["date"]]] = v
            last = float("nan")
            for k in range(n):
                if arr[k] == arr[k]:
                    last = arr[k]
                arr[k] = last
            out[s] = arr
    else:
        da = pickle.load(open(PRE.EOTC_DAILY, "rb"))
        da = da[da["stock_id"].isin(set(C["P"]))]
        tmp = defaultdict(dict)
        for s, d_, c_, h_ in zip(da["stock_id"], da["date"], da["close"], da["shares"]):
            try:
                v = float(c_) * float(h_)
            except (TypeError, ValueError):
                continue
            if v > 0:
                tmp[s][d_] = v
        for s in C["P"]:
            dd = tmp.get(s, {}); arr = []; last = float("nan")
            for d in cal_s:
                if d in dd:
                    last = dd[d]
                arr.append(last)
            out[s] = arr
    return out


def ck_sim(C, cfg, RKk, pnW, rok, mcd, K_, cal_s, t0, t1):
    """獨立位置簿（Q5 照字面重寫；只共用價格陣列與成交旗標）。"""
    P, dl = C["P"], C["dl"]; n = len(cal_s)
    K = cfg["K"]; S = cfg["S"]; A_, L = cfg["A"], cfg["L"]; NS = {"S1": 20, "S2": 3}[S]
    SF = {}
    for s, v in P.items():
        b = np.flatnonzero(v["valid"])
        if len(b) and b[-1] < t1:
            SF[s] = int(b[-1])
    chk = set(t for t in RKk if t0 - 1 <= t <= t1 - 1)
    uni = set(C["mk"])
    mdl = sorted(pnW)
    slots = [{"cash": 1.0 / K, "val": 1.0 / K, "ind": None} for _ in range(K)]
    book = {}; sellq = set(); trades = []; hs = {}; eq = [1.0] * n

    def elig(t):
        ym = cal_s[t][:7]
        ds = [d for d in mdl if d[:7] == ym]
        if not ds:
            return []
        md = ds[-1]
        return sorted(s for s in pnW[md] if s in uni and ck_pitok(rok.get(s) or C_rok(C, s, rok), md))

    for t in range(t0, t1 + 1):
        for s in sorted(book):
            if s in SF and t == SF[s] + 1:
                b = book.pop(s); slots[b["k"]]["cash"] += b["u"] * P[s]["c"][t] - b["amt"] * COST; sellq.discard(s); trades.append((t, s, "sf", P[s]["c"][t]))
        buyplan = []
        dec = (t - 1) in chk
        if dec:
            Rk = RKk[t - 1]; nm = Rk["names"]
            for k in range(K):
                i = slots[k]["ind"]
                if i is None:
                    continue
                go = False
                av = Rk["Aall"].get(i)
                if av is not None and av[0] >= 5 and av[{"A1": 1, "A2": 2, "A3": 3}[A_]] == av[{"A1": 1, "A2": 2, "A3": 3}[A_]] and av[{"A1": 1, "A2": 2, "A3": 3}[A_]] <= 0:
                    go = True
                if i in nm and len(nm) >= 2:
                    j = nm.index(i)
                    if Rk["pA"][A_][j] - Rk["pL"][L][j] <= 0:
                        go = True
                if go:
                    for s, b in book.items():
                        if b["k"] == k:
                            sellq.add(s)
                    slots[k]["ind"] = None
            empty = [k for k in range(K) if slots[k]["ind"] is None]
            if empty:
                hold = {sl["ind"] for sl in slots if sl["ind"] is not None}
                lst = ck_cands(Rk, cfg, hold) or []
                dstr = cal_s[t - 1]
                grp = defaultdict(list)
                for s in elig(t):
                    if s not in P:
                        continue
                    ii = PRE.ck_ind(K_, s, dstr)
                    if ii is None or ii in EXCL:
                        continue
                    v = mcd[s][t - 1]
                    if v == v and v > 0:
                        grp[ii].append((-v, s))
                for k in empty:
                    if not lst:
                        continue
                    i = lst.pop(0); slots[k]["ind"] = i
                    names = [s for _, s in sorted(grp.get(i, []))][:NS]
                    tob = []
                    for s in names:
                        if s in book:
                            if book[s]["k"] == k and s in sellq:
                                sellq.discard(s)
                            continue
                        tob.append(s)
                    buyplan.append((k, tob, len(names)))
        for s in sorted(sellq):
            x = P[s]
            if x["trd"][t] and not x["dn_o"][t] and np.isfinite(x["o"][t]) and x["o"][t] > 0:
                px, kd = x["o"][t], "open"
            elif (not x["trd"][t]) and s in dl and t > dl[s]["last"] and dl[s]["status"].startswith("delisted"):
                px, kd = x["c"][t], "delist"
            else:
                continue
            b = book.pop(s); slots[b["k"]]["cash"] += b["u"] * px - b["amt"] * COST; sellq.discard(s); trades.append((t, s, kd, px))
        for k, tob, nn in sorted(buyplan):
            for s in tob:
                x = P[s]; o = x["o"][t]
                if not x["trd"][t] or not (np.isfinite(o) and o > 0) or x["up_o"][t]:
                    continue
                amt = min(slots[k]["val"] / nn, slots[k]["cash"])
                if amt <= 1e-12:
                    break
                slots[k]["cash"] -= amt; book[s] = {"u": amt / o, "amt": amt, "k": k}; trades.append((t, s, "buy", o))
        for k in range(K):
            slots[k]["val"] = slots[k]["cash"] + sum(b["u"] * P[s]["c"][t] for s, b in book.items() if b["k"] == k)
        eq[t] = sum(sl["val"] for sl in slots)
        if dec:
            hs[t] = sorted(book)
    return eq, trades, hs


def C_rok(C, s, rok):
    rok[s] = ck_rowok(C["data"], s)
    return rok[s]


# ═════════════ 網頁 ═════════════
def page():
    e = html.escape
    META = json.load(open(os.path.join(OUT, "meta.json"), encoding="utf-8"))
    TM = pd.read_csv(os.path.join(OUT, "cells.csv"))
    VAR = pd.read_csv(os.path.join(OUT, "variants.csv")); YR = pd.read_csv(os.path.join(OUT, "years.csv"))
    IC = pd.read_csv(os.path.join(OUT, "industry_counts.csv")); ED = pd.read_csv(os.path.join(OUT, "chosen_episodes.csv"))
    CKp = os.path.join(OUT, "check.json"); CK = json.load(open(CKp, encoding="utf-8")) if os.path.exists(CKp) else None
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0]
    CSS += ("\ntd.l,th.l{text-align:left;white-space:normal}small{color:#666}.warn{border-left:4px solid #d64045;padding:6px 10px;background:#fff4f4}"
            ".ok{border-left:4px solid #2b6cb0;padding:8px 12px;background:#eef4fb}.big{font-size:1.05rem}li{margin:.35em 0}"
            "details{margin:.6em 0}summary{font-weight:600;cursor:pointer;padding:4px 0}")
    P1 = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:+.1f}%"
    PC = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:.0f}%"
    F2 = lambda v: "—" if v is None or not np.isfinite(v) else f"{v:.2f}"
    G_ = META["挑格"]; CH = G_["挑中參數"]; Z = META["0050"]; DET = META["挑中格細項"]; CT = META["對照"]; S = META["丙"]
    ANm = {"A1": "近 3 月營收年增", "A2": "近 3 月年增減近 12 月年增（短長差）", "A3": "近 3 月年增比三個月前升多少（動能）"}
    PNm = {"P1": "「營收加速名次 − 股價名次」差最大", "P2": "營收加速前三分之一裡股價漲最少"}
    SNm = {"S1": "市值前 20 大", "S2": "市值前 3 大"}
    desc = (f"每月營收公布後，挑{PNm[CH['P']]}的 {CH['K']} 個產業（加速用 {ANm[CH['A']]}、股價看近 {CH['L']} 日），各買產業內{SNm[CH['S']]}；"
            f"直到該產業營收不再加速或股價已不落後才換")
    pre = CT["前件挑中格（本件設定重跑）"]; rnd = CT["隨機"]
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>產業營收加速但股價落後_回測</title>", f"<style>{CSS}</style></head><body><main>", "<h1>產業營收加速但股價落後：回測（乙＋丙）</h1>",
         "<p class='warn'>⚠ <b>事後重切</b>：「股價落後」這條是看過前件（只看營收加速）全部結果之後才加的，所以就算兩段都過，最多也只算「暫定」、只進前瞻紀錄。"
         "這是歷史回測的描述，<b>不是買賣建議</b>。</p>"]
    cf, ea, ex = G_["確認"], G_["早年"], G_["探索"]
    mt = DET["main_窗尾仍持有"]; et = DET["early_窗尾仍持有"]
    rr = {R_: CT[f"定期換股（{R_}）"] for R_ in RS}
    tail_txt = "、".join(f"{x['產業']}（{x['進場日']} 進、已 {x['已持有交易日']} 日）" for x in mt["明細"])
    H.append(f"<div class='ok big'><b>結論：判定【{e(G_['判定'])}】。</b><ul>"
             f"<li>72 格在 2017～2021 挑出的一格：{e(desc)}。</li>"
             f"<li>2022-01～2026-08：年化 {P1(cf['年化'])}、最大回落 {P1(cf['回落'])}；0050 {P1(Z['確認']['年化'])}／{P1(Z['確認']['回落'])} ⇒ <b>{e(G_['確認標籤'])}</b>。"
             f"早年 2012-06～2014：{P1(ea['年化'])}／{P1(ea['回落'])}；0050 {P1(Z['早年']['年化'])}／{P1(Z['早年']['回落'])} ⇒ <b>{e(G_['早年標籤'])}</b>。</li>"
             f"<li>跟前件「只看營收加速、不管股價」那一格（同窗、同設定重跑）比：確認段 {P1(cf['年化'])} vs {P1(pre['確認']['年化'])}，"
             f"早年 {P1(ea['年化'])} vs {P1(pre['早年']['年化'])} ⇒ 多加「股價落後」這條{'比較好' if cf['年化'] > pre['確認']['年化'] else '沒有比較好'}（確認段）。</li>"
             f"<li>同一格改成定期換股（確認段年化）：每季 {P1(rr['季']['確認']['年化'])}、每半年 {P1(rr['半年']['確認']['年化'])}、每年 {P1(rr['年']['確認']['年化'])}；條件換股 {P1(cf['年化'])}。</li>"
             f"<li>隨機挑產業（同機制）1,000 次，確認段年化中位 {P1(rnd['確認']['中位'])}，比挑中格好的比例 {PC(rnd['確認']['p_年化'])}。</li>"
             f"<li>窗尾仍持有：主段 {mt['件數']} 個產業（{e(tail_txt) or '無'}）；早年 {et['件數']} 個。</li>"
             "</ul></div>")
    if CK:
        H.append(f"<p class='note'>查核：{'通過' if CK['通過'] else '⛔ 不通過'}（不同 {CK['不同項數']} 項；另一套寫法重算 A、產業指數報酬、排名、整條權益與每筆交易、定期引擎閘）。讀法寫死 {e(META['讀法寫死'])}。</p>")
    # 一、判定
    H.append("<h2>一、判定</h2><div class='wrap'><table><tr><th class='l'>項</th><th>探索<br><small>2017-03～2021</small></th><th>確認<br><small>2022～2026-08</small></th><th>早年<br><small>2012-06～2014</small></th></tr>")
    fm = lambda d: f"{P1(d['年化'])}<br><small>回落 {P1(d['回落'])}・比值 {F2(d['比值'])}</small>" if d else "—"
    row = lambda nm, a_, b_, c_: H.append(f"<tr><td class='l'>{nm}</td><td>{a_}</td><td>{b_}</td><td>{c_}</td></tr>")
    row("<b>挑中格（條件換股）</b>", fm(ex), fm(cf) + f"<br><b>{e(G_['確認標籤'])}</b>", fm(ea) + f"<br><b>{e(G_['早年標籤'])}</b>")
    row("0050", fm(Z["探索"]), fm(Z["確認"]), fm(Z["早年"]))
    row("⭐ 前件挑中格（只看營收；本件設定重跑）", fm(pre["探索"]), fm(pre["確認"]), fm(pre["早年"]))
    po = CT["前件原數字（前件設定）"]
    row("<small>前件挑中格（前件原數字：舊母體口徑、早年只上市、全用 10 日）</small>", fm(po["探索"]), fm(po["確認"]), fm(po["早年"]))
    for R_ in RS:
        row(f"同一格改定期換股（{R_}）", fm(rr[R_]["探索"]), fm(rr[R_]["確認"]), fm(rr[R_]["早年"]))
    row("隨機挑產業 1,000 次（中位）", *[f"{P1(rnd[sg]['中位'])}<br><small>p10～p90 {P1(rnd[sg]['p10'])}～{P1(rnd[sg]['p90'])}・≥挑中格 {PC(rnd[sg]['p_年化'])}</small>" for sg in ("探索", "確認", "早年")])
    for nm in ("反向臂（季換、A 前三分之一裡已漲最多）", "全產業等權（季換）"):
        row(nm, fm(CT[nm]["探索"]), fm(CT[nm]["確認"]), fm(CT[nm]["早年"]))
    y = CT["營量v1_T1"]
    row("營量 v1（T1；引前件）", fm(y["探索"]), fm(y["確認"]), fm(y["早年"]) + "<br><small>窗 2012-06-04～2014-12-31</small>")
    H.append("</table></div>")
    H.append(f"<p class='note'>挑法：先排除退化格（平均持股 ＜ 3 或現金 ＞ 30%，{G_['退化格數']} 格），剩 {G_['非退化']} 格；探索段過判準（年化 ＞ 0050 且 年化÷|回落| ≥ 0050）的 {G_['探索過判準格數']} 格"
             f"{'，取比值最高' if G_['探索過判準格數'] else '，都沒過 ⇒ 取比值最高'}。判定取確認段與早年段較嚴者。全 72 格：確認段合格 {G_['確認段合格格數']}、早年段合格 {G_['早年段合格格數']}、兩段都合格 {G_['兩段都合格格數（全 72）']}。"
             "定期換股、反向臂、全產業等權只當描述對照，不進挑選。</p>")
    H.append("<p class='warn'>⚠ 早年段用上市＋上櫃版面，但這份資料上櫃沒有法人資料 ⇒ 挑股（要法人資料）實際只買得到上市股；產業指數（不要法人資料）有含上櫃。"
             "2005-01～2012-05 沒有法人資料 ⇒ 不可判定。</p>")
    # 二、先驗
    H.append("<h2>二、先驗對答</h2><div class='wrap'><table><tr><th>#</th><th class='l'>先驗</th><th class='l'>結果</th><th>對錯</th></tr>")
    for k, pr, rs, ok in META["先驗"]:
        H.append(f"<tr><td>{k}</td><td class='l'>{e(pr)}</td><td class='l'>{e(rs)}</td><td><b>{ok}</b></td></tr>")
    H.append("</table></div>")
    # 三、必報
    H.append("<h2>三、挑中格必報</h2><div class='wrap'><table><tr><th class='l'>段</th><th>平均持股</th><th>現金</th><th>每年換手</th><th>成本／年</th><th>0050 重疊率</th>"
             "<th>持有段數</th><th>持有天數<br><small>平均／中位</small></th><th>營收不再加速<br><small>X1</small></th><th>股價已不落後<br><small>X2</small></th><th>兩條同時</th><th>窗尾仍持有</th></tr>")
    for sg in ("探索", "確認", "早年"):
        d = DET[sg]
        H.append(f"<tr><td class='l'>{sg}</td><td>{d['平均持股']:.1f}</td><td>{PC(d['現金比例'])}</td><td>{d['每年換手']:.2f} 倍</td><td>{d['成本／年'] * 100:.2f}%</td>"
                 f"<td>{PC(d['0050重疊率'])}</td><td>{d['產業持有段數']}</td><td>{F2(d['平均持有天數'])}／{F2(d['持有天數中位'])}</td><td>{d['X1']}</td><td>{d['X2']}</td><td>{d['X1+X2']}</td><td>{d['窗尾仍持有']}</td></tr>")
    H.append("</table></div>")
    for part, nm in (("main", "主段"), ("early", "早年")):
        hd = DET[f"{part}_持有天數分佈"]
        if hd.get("筆數"):
            H.append(f"<p class='note'>{nm}持有天數（交易日）分佈：{hd['筆數']} 段；中位 {hd['p50']:.0f}、p25～p75 {hd['p25']:.0f}～{hd['p75']:.0f}、最長 {hd['最長']}；"
                     f"≤ 21 日 {hd['≤21']}、22～63 日 {hd['22～63']}、64～250 日 {hd['64～250']}、＞ 250 日 {hd['＞250']}。窗尾 {e(DET[f'{part}_窗尾仍持有']['窗尾'])} 仍持有 {DET[f'{part}_窗尾仍持有']['件數']} 個。</p>")
    H.append("<h3>各年報酬</h3><div class='wrap'><table><tr><th>年</th><th>挑中格</th><th>前件挑中格</th><th>0050</th></tr>")
    for _, r in YR.iterrows():
        H.append(f"<tr><td>{r['年']}{'<small>（早年段）</small>' if r['段'] == 'early' else ''}</td><td>{P1(r['挑中格'])}</td><td>{P1(r.get('前件挑中格', np.nan))}</td><td>{P1(r['0050'])}</td></tr>")
    H.append("</table></div><p class='note'>首年、末年是不滿一年的窗內報酬。</p>")
    H.append("<h3>挑中產業與次數</h3><div class='wrap'><table><tr><th class='l'>段</th><th class='l'>產業（次數）</th></tr>")
    for sg, g in IC.groupby("段", sort=False):
        H.append(f"<tr><td class='l'>{e(sg)}</td><td class='l'>{'、'.join(f'{e(x)}（{n}）' for x, n in zip(g['ind'], g['次數']))}</td></tr>")
    H.append("</table></div><p class='note'>每次進場一筆；逐筆（訊號日、加速與股價百分位、出場原因、持股）見 chosen_episodes.csv。</p>")
    H.append("<h3>產業別口徑與現實版（描述）</h3><div class='wrap'><table><tr><th class='l'>版本</th><th class='l'>段</th><th>年化</th><th>回落</th><th>0050</th><th>標籤</th></tr>")
    for _, r in VAR.iterrows():
        H.append(f"<tr><td class='l'>{e(r['版本'])}</td><td class='l'>{e(r['段'])}</td><td>{P1(r['年化'])}</td><td>{P1(r['回落'])}</td>"
                 f"<td>{P1(r['0050年化'])}／{P1(r['0050回落'])}</td><td>{e(str(r['標籤']))}</td></tr>")
    H.append("</table></div><p class='note'>① 現值 ＝ 用現在的產業別套回過去；② 剔除 2023-07 新增的綠能環保、數位雲端、運動休閒、居家生活四類不參加排名。"
             "現實版 ＝ 每邊多 0.3% 成本＋50 萬資金的衝擊成本＋用當日均價成交；＋C5 再加每筆低消 20 元。</p>")
    # 四、丙
    H.append("<h2>四、丙（描述，不計檢定數）</h2>")
    H.append("<h3>① 股價多久追上</h3><div class='wrap'><table><tr><th class='l'>段</th><th>筆數</th><th>250 日內追上</th><th>追上天數中位<br><small>p25～p75</small></th><th>追上前產業指數報酬<br><small>中位／平均</small></th><th>未滿 250 日</th></tr>")
    for part, nm in (("main", "主段"), ("early", "早年")):
        d = S.get(f"追上|{part}")
        if d:
            H.append(f"<tr><td class='l'>{nm}</td><td>{d['筆數']}</td><td>{d['250日內追上']}/{d['分母（剔未滿250日）']}（{PC(d['250日內追上比例'])}）</td>"
                     f"<td>{F2(d['追上天數中位'])}<br><small>{F2(d['追上天數p25'])}～{F2(d['追上天數p75'])}</small></td><td>{P1(d['追上前報酬中位'])}／{P1(d['追上前報酬平均'])}</td><td>{d['未滿250日']}</td></tr>")
    H.append("</table></div><p class='note'>追上 ＝ 從訊號日起逐日收盤重算，第一次「營收加速百分位 − 股價百分位 ≤ 0」。</p>")
    H.append("<h3>② 落後是不是因為加速只是一次性</h3><div class='wrap'><table><tr><th class='l'>誰｜段</th><th>筆數</th><th>3 個月後<br><small>A 仍 ＞ 0</small></th><th>6 個月後</th><th>9 個月後</th><th>12 個月後</th></tr>")
    for k, d in S.items():
        if k.startswith("之後A|"):
            _, who, part = k.split("|")
            H.append(f"<tr><td class='l'>{e(who)}｜{'主段' if part == 'main' else '早年'}</td><td>{d['筆數']}</td>" + "".join(f"<td>{PC(d[f'M+{h}仍>0比例'])}<br><small>{d[f'M+{h}有值']} 筆有值</small></td>" for h in (3, 6, 9, 12)) + "</tr>")
    H.append("</table></div>")
    H.append("<h3>③ 吃到起漲到頂幾成</h3><div class='wrap'><table><tr><th class='l'>誰｜段</th><th>筆數</th><th>訊號時已漲<br><small>距 250 日低點中位</small></th><th>還吃得到<br><small>中位</small></th><th>之後沒再創高</th><th>實際持有吃到<br><small>中位</small></th><th>每段持有報酬<br><small>平均／中位</small></th></tr>")
    for k, d in S.items():
        if k.startswith("吃到|"):
            _, who, part = k.split("|")
            H.append(f"<tr><td class='l'>{e(who)}｜{'主段' if part == 'main' else '早年'}</td><td>{d['筆數']}</td><td>{P1(d['已漲250中位'])}</td><td>{PC(d['吃到幾成中位'])}</td><td>{PC(d['之後沒再創高比例'])}</td>"
                     f"<td>{PC(d['實際持有吃到幾成中位'])}</td><td>{P1(d['持有報酬平均'])}／{P1(d['持有報酬中位'])}</td></tr>")
    H.append("</table></div><p class='note'>產業指數 ＝ 產業內合格成分股等權（主段 W1；早年流動性＋K 棒數）。吃到幾成 ＝（訊號 → 之後 500 日最高）÷（前 250 日最低 → 那個最高），對數；早年段資料只到 2014-12，「之後 500 日」多半不滿。</p>")
    # 五、72 格
    H.append("<h2>五、72 格（探索段比值前 30）</h2><details><summary>展開</summary><div class='wrap'><table><tr><th class='l'>格</th><th>探索</th><th>確認</th><th>早年</th><th>持股／現金</th></tr>")
    for _, r in TM.sort_values("探索_比值", ascending=False).head(30).iterrows():
        H.append(f"<tr><td class='l'>{e(r['key'])}{' ⭐' if r['key'] == G_['挑中'] else ''}{'<br><small>退化</small>' if r['退化'] else ''}</td>"
                 f"<td>{P1(r['探索_年化'])}<br><small>{P1(r['探索_回落'])}・{F2(r['探索_比值'])}</small></td><td>{P1(r['確認_年化'])}<br><small>{P1(r['確認_回落'])}・{e(str(r['確認_標籤']))}</small></td>"
                 f"<td>{P1(r['早年_年化'])}<br><small>{P1(r['早年_回落'])}・{e(str(r['早年_標籤']))}</small></td><td>{r['探索_平均持股']:.1f}<br><small>{PC(r['探索_現金比例'])}</small></td></tr>")
    H.append("</table></div></details><p class='note'>格名 ＝ 挑法｜股價天數｜加速種類｜產業數｜挑股。全表 cells.csv。</p>")
    # 六、讀法
    pi = META.get("早年面板", {})
    H.append("<h2>六、資料與執行者補的讀法</h2><ul class='note'>"
             "<li>主臂：每月營收可用日收盤判、隔天開盤做；持有產業「營收不再加速（A ≤ 0）」或「股價已不落後（加速百分位 − 股價百分位 ≤ 0）」才賣，沒有最長天數；空位補當期最佳候選。</li>"
             "<li>★ P2 的候選也要求名次差 ＞ 0（否則當天就符合「股價已不落後」）；★ 窗首前一天視為檢查日、窗首開盤建倉。</li>"
             "<li>★ 每個位置一個子帳戶：賣出款、強制出場款回該位置；延後賣出晚到的錢留在該位置，到下次換產業才再投入；之後不再平衡。</li>"
             "<li>★ 持有產業不在可排名集合時，X2 不判、只判 X1；兩條都判不了就續抱（計數見 cells.csv 計數欄）。</li>"
             "<li>★ 隨機對照 ＝ 同機制同出場、補位改隨機抽；反向臂、全產業等權用每季定期換股（描述）。</li>"
             "<li>★ 可用日：2025-12 以前次月 10 日之後第一個交易日；2026-01 起 15 日之後；產業別、當時已上市櫃判定日跟著改 ⇒ A 表全部重算。</li>"
             f"<li>母體新口徑（GATE_V2）：創新板只剔在板期間、興櫃列不算；主段沿用前件的 W1 面板、在量測日剔板期列。早年上市＋上櫃版面 W1 面板重建：{e(json.dumps(pi, ensure_ascii=False))}</li>"
             f"<li>段資訊：{e(json.dumps(META.get('段資訊', {}), ensure_ascii=False))}</li>"
             "<li>偏離：確認段資料尾沿用前件 2026-08-24（W1 面板最後量測日 2026-08），未延到最新收盤；營量 v1 引前件已算好的數字（舊母體口徑）。</li>"
             "<li>引擎：成交、成本、強制出場同前件換股簿；定期版與前件引擎逐位元對過（閘 G1′）。成本來回 0.585%。</li></ul>")
    H.append("</main></body></html>")
    open(os.path.join(OUT, "產業營收加速但股價落後_回測.html"), "w", encoding="utf-8").write("\n".join(H))
    log("[網頁] 完成")


def main():
    global LOGF
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=3); ap.add_argument("--reps", type=int, default=1000)
    ap.add_argument("--check", action="store_true"); ap.add_argument("--page", action="store_true")
    ap.add_argument("--reuse-a", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    LOGF = os.path.join(OUT, "run_check.log" if a.check else ("run_page.log" if a.page else "run.log"))
    open(LOGF, "w").close()
    log(f"===== researchIndRevLag_prereg {'check' if a.check else ('page' if a.page else 'run')}｜讀法寫死 {TIME}｜GATE_V2 開 =====")
    if a.check:
        check(a)
    elif a.page:
        page()
    else:
        run(a)
        page()


if __name__ == "__main__":
    main()
