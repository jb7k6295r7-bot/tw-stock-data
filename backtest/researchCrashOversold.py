# -*- coding: utf-8 -*-
"""PREREG急跌錯殺 seq1（台股策略線登錄 sha db323ccbe775d244，2026-10-11 01:30；裁定 seq335 §四發號、N_組合 ＋1（F1／F2 × X1／X2 四格挑 1）；
標籤上限：最多暫定（台股看過 2026-07 那波急跌的反彈描述，屬確認段））——回測線計算子代理。
⛔ 只計算：不 commit、不改既有程式與結果夾；用語「假訊號」；⛔ 不給買賣建議。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchCrashOversold run [--procs 4] [--reps 200] [--fake 200] [--smoke]
    ...                                                                         -m backtest.researchCrashOversold page   # ⇒ resultsCrashOversold/急跌錯殺.html
    抽樣查核（獨立寫法）：... -m backtest.researchCrashOversold_check

⭐ 讀法寫死時間：TIME（台北，WSL TZ=Asia/Taipei date）；寫死前 ⛔ 沒算任何本件數字（只看過登錄全文 seq1、裁定 seq335、台股 1011-0130、回測 1011-0139、
   既有程式 researchRevLimitUp（組合層骨架、World 快取）、researchBARR（壞根 bad_part）、researchPRE5core、researchEPSqoq／researchYLmargin（季報）、
   researchNewsCat（13:30 規則）、research11.load_bars 與資料格式）。

═══ 讀法（K 標；登錄沒寫清楚、執行者補的都在這裡）═══
 K1 sha：登錄全文去掉含「pw1 line」那一行後 sha256 前 16 碼 ＝ db323ccbe775d244 才跑（信箱只讀）
 K2 版面 ＝ researchRevLimitUp.World（main ＝ rerun17 快照 H2D edc6f8002f，日曆 2015-01-05～2026-09-24；早年 ＝ ~/earlydata/eotc_f65bb03e11/otc/data，
    2004-02-11～2014-12-31，⚠ 上櫃日 K 2007-07 起；同一份快取 ~/rluwork/world_*.pkl，⛔ 不改）；股票 ＝ UG.gate3（GATE_V2 開）∩ 四碼、首碼 1～9、非 91xx；
    ⭐ 含已下市；價格 ＝ D.load_stock 還原價，收盤 ffill；月營收、產業、重大訊息、季報 ＝ tw-stock-data origin/main（執行時 sha）git archive 到 ~/crashwork（唯讀）
 K3 母體（seq321 §五 R1）：d 當天「有 K 棒 ∧ pit_valid ∧ amt20 有值 ∧ 產業不是金融保險」依 amt20（含 d 的最近 20 根有效 K 棒原始成交金額平均）由大到小前 X%；
    X ＝ 2016-01-04 上述母體中 amt20 ≥ 5,000 萬的檔數 ÷ 同日上述母體檔數（固定；早年段沿用同一個 X）；-DR、創新板由 gate3／pit_valid 剔；KY 不排
    產業 ＝ PRE.PIT（industry_pit pit 版＋營收彙總表後備），每月第一個交易日判一次、月內沿用（同 researchRevLimitUp fb_matrix）
 K4 硬斷點（⭐ 全線規則 seq335：research11.load_bars 壞根規則「缺口 ≥ 5 日即壞根」，不依流動性前提）：
    逐版面照抄 load_bars（＝ researchBARR.bad_part）：① 幽靈事件 ② 有效 K 棒間缺口 ≥ 5 個交易日 ③ data.breakpoints 且 applies()；
    再聯集 adj 的減資／面額變更事件日（event ∈ {reduce, parvalue}）⇒ 壞根矩陣 BAD
    事件窗：(t−10, t] 內有任一壞根 ⇒ 該股該日的 r10 不算（不進當天的排名、也不進同產業中位）⇒ 不會成為事件（⭐ 補讀法：剔在排名之前，否則假急跌會佔走最低 2% 名額；
      另報「若不剔、最低 2% 裡有幾筆壞根窗」）；進場日 e 本身是壞根 ⇒ 不進（筆數照報）
    持有期：e 之後第一個壞根 kb 早於（或等於）實際賣出那根 ⇒ 改在 kb 前最後一根有效 K 棒收盤強制出（原因「壞根前收盤強制出」，筆數照報）
      （⚠ 偏離：登錄寫「持有期跨停牌、減資 ⇒ 剔除」；進場當下不知道之後會停牌，事後剔除是前視 ⇒ 改成強制出，同 researchBARR R6）
 K5 急跌：r10(d) ＝ C(d) ÷ C(d−10) − 1（還原收盤、日曆交易日位置；d 與 d−10 都要有 K 棒）；
    ind10(d) ＝ 當天母體內同產業 r10 中位（含自己；同產業 ＜ 5 檔或產業不明 ⇒ 當天全母體中位）；ex ＝ r10 − ind10
    最低 2% ＝ 當天母體內（r10 可算者）ex 由小到大前 ⌈0.02 × 檔數⌉ 檔（同值依代號序）；事件候選 ＝ 最低 2% ∧ r10 ＜ 0
    同一檔 20 個交易日內只取第一筆：依日期，與上一筆「留下的」相距 ≤ 20 個交易日 ⇒ 不算（在候選層去重，公司事件、基本面之前）
 K6 公司事件排除：重大訊息（data/mops/news）主旨含登錄 18 個關鍵字任一（字串比對、原始主旨）且事件交易日落在 [t−10, t] ⇒ 不買
    事件交易日（照重大訊息類別反應件 13:30 規則，researchNewsCat）：發言日是交易日且時間（前 5 碼）≤ 13:30 ⇒ 當天；否則 ⇒ 次一交易日
 K7 基本面（決策日 t 收盤可用）：
    月營收可用日 ＝ research34.rebalance_dates（M ≤ 2025-12：M＋1 月 10 日之後第一個交易日；M ≥ 2026-01：15 日之後）；M* ＝ 可用日 ≤ t 的最新一期
    F1：年增(M*) ＝ 當月營收 ÷ 去年當月營收 − 1 ＞ 0，且近 3 期（M*−2～M*）當月營收合計 ÷ 去年當月營收合計 − 1 ＞ 0
        任一可算且不成立 ⇒ 不成立；兩者都可算且成立 ⇒ 成立；其餘（缺值、去年 ≤ 0）⇒ 不明 ⇒ 不買（筆數照報）
    季報：data/mops/fs_hist 一般業 ci 檔「基本每股盈餘（元）」「營業收入」「營業毛利（毛損）」年初累計 ⇒ 單季 ＝ 本期 − 同年前一季（Q1 不減；researchEPSqoq／researchYLmargin 同法）；
        可用日 ＝ 法定期限（Q1 5/15、Q2 8/14、Q3 11/14、Q4 隔年 3/31）之後第一個交易日；q* ＝ 可用日 ≤ t 的最新一季
    F2：F1 成立 ∧ 單季 EPS(q*) ＞ 0 ∧ 單季毛利率(q*) ≥ 單季毛利率(q*−4)；非 ci 格式（異業等）或缺值 ⇒ 不明 ⇒ 不買（筆數照報）
    早年段 F2 不可判定（fs_hist 2015Q1 起；登錄照寫）
 K8 進場 e ＝ t 的次一交易日（日曆）開盤；e 沒有有效開盤 ⇒ 不進（筆數照報）；10 槽、等權（前一日權益 ÷ 10）、候選多於空位 ⇒ 抽籤（default_rng(20261010＋r)）、
    200 顆報中位；空位才買、已持有不重買、⛔ 不遞補（引擎 research11.simulate_mtm rule "F"，經 researchRevLimitUp.sim／run_arms，⛔ 不改）；停止交易強制出場開
 K9 出場（seq308 §四：條件出場、⛔ 不設最長天數）：
    X1：① 修復 ＝ e 起（含 e）第一根有 K 棒且還原收盤 ≥ C(t−10) ⇒ 次一交易日起第一個有效開盤賣
        ② 轉壞（營收）＝ 可用日 ＞ t 的各期依序：第一期年增 ≤ 0（可算者；缺值不觸發）⇒ 觸發日 ＝ 該期可用日 ⇒ 次一交易日起第一個有效開盤賣
        ③ F2 格另加 轉壞（EPS）＝ 可用日 ＞ t 的各季依序：第一季單季 EPS ≤ 0 ⇒ 同上；①②③ 取最早
    X2：e 起（含 e 收盤）持有期最高收盤 × 0.8 ≥ 當日收盤 ⇒ 次一交易日起第一個有效開盤賣（＝ researchRevLimitUp E2）
    資料尾還沒出場 ⇒ 未完（以最後收盤計值、不賣；只影響窗外，窗尾持有照報）；早年版面出場落在 2015 之後 ⇒ 早年版面內視為未完
 K10 段：探索 2017-03-02～2021-12-30、確認 2022-01-03～2026-08-24、主窗 ＝ 兩段相接（同一條權益曲線切窗；rerun17 win_metrics；資料尾讀成 2026-08-24 ＝ 0050 錨）
     早年 2005-01-03～2014-12-30（只有 F1 格；月營收覆蓋：PRE.coverage 上市各年平均 ≥ 90% ⇒ 判定窗從「其後各年都 ≥ 90%」的第一年起，同 researchRevLimitUp M9）
     判準（使用者判準，對 0050 同段）：合格 ＝ 年化中位 ＞ 0050 且 年化中位 ÷ |回落中位| ≥ 0050；另列 ＝ 只過年化；其餘不合格
     挑格：探索段（0.585% 版）非退化格中合格者取比值最大；沒有合格 ⇒ 取比值最大（照報不合格）；平手 ⇒ 年化、格序 F1X1、F1X2、F2X1、F2X2
     判定 ＝ 確認段與早年段兩段取較嚴（F2 格早年不可判定 ⇒ 只看確認段，照報）；⭐ 標籤上限：合格 ⇒「暫定」（裁定 seq335 §四）；現實版同表並報標籤
 K11 退化：⭐ 先寫 degeneracy.json（附台北時戳）再彙總任何報酬；平均持股 ＜ 3 或平均現金 ＞ 30%（段內逐日平均、種子中位）⇒ 照登錄排除並列出；
     全部格都退化 ⇒ 在全部格裡照同規則挑、標「全退化」；確認或早年段退化 ⇒ 不判合格
     另報「候選不足月份占比」＝ r＝0 該月平均持股 ＜ 10 檔的月份比例
 K12 現實版 ＝ researchSlip「現實版」（researchRevLimitUp M8 同一套：每邊 ＋0.3%、衝擊 σ20 × √(5 萬 ÷ ADV20)、一字漲停買不到、停牌買不到、一字跌停賣不掉、均價成交）
 K13 對照：① 急跌但不看基本面（公司事件排除後全部事件、同挑中格的出場）200 顆（＋現實版 50 顆）
          ② 急跌而且基本面變差（F1 不成立者、同出場；描述）50 顆
          ③ 假訊號臂（挑中格）：每個進場日 e 的訊號數不變 ⇒ 改成 e−1 的母體裡「非急跌」（當天不在最低 2%）、e 有有效開盤的隨機同數量股；
             持有天數從挑中格（已完成）的「進場 → 出場」日曆位置差等機率抽，到期日起第一個有效開盤賣；default_rng([20261011, r])；200 抽；
             p ＝ 假訊號年化 ≥ 挑中格年化中位 的比例
          ④ 0050 同段、營量 v1、營飆 v1（backtest/resultsYLmargin/cells.csv 同窗；持股重疊用 researchRevLimitUp.yl_ref 的 r0 快取）
 K14 描述（⛔ 不判、不計 N；挑中格同進場、各 50 顆）：固定持有 {5, 20, 60} 根（進場那根算第 1 根，第 H 根收盤出）；t 後第 5 個交易日才買（e ＝ t＋5，
     (t, e] 有壞根 ⇒ 不進，出場規則同挑中格）；0050 在 200 日線上才買（e−1 的 0050 收盤 ＞ 200 日均）——「擋長空頭、不是急跌保護」；
     被公司事件排除的事件（同挑中格出場，逐筆與 50 顆組合）
 K15 必報：等效獨立檔數（r＝0，換股日持股 N、ρ ＝ 前 60 日日報酬兩兩相關平均、N_eff ＝ N ÷ (1＋(N−1)ρ)，researchRevLimitUp.eff_n）；最大產業占幾檔（K3 的產業）；
     現金比例與候選不足月份占比；持有天數分佈；X1 修復／轉壞／X2 各幾次；窗尾仍持有；一年內先跌 15%（researchRevLimitUp.trade_stats）；
     事件分組描述（逐筆、挑中格出場、主窗內）：大盤也急跌（0050 同期 r10 ≤ 該日以前（含）全部歷史 r10 的 5% 分位；歷史 ＝ 早年＋main 兩版面相接、
       至少 120 筆才判）vs 只有個股急跌；急跌前 60 日已大漲（r60 ＝ C(t−10) ÷ C(t−70) − 1 落在當天母體前 10%；窗內有壞根 ⇒ 不判）vs 沒有；
     每年事件數；與營量 v1、營飆 v1 持股重疊率
 K16 結果句必附（登錄 §三）：「本件只用公開的營收、財報、公告標題判斷『基本面沒變差』；文章裡的掉單、降規、延遲下單分級⛔ 無法機器化」
     「錯殺要事後才能確認；本件測的是『這樣挑，平均起來』，⛔ 不代表某一檔是錯殺」
輸出 backtest/resultsCrashOversold/：degeneracy.json（先寫）、summary.json、grid.csv、seeds.csv.gz、events.csv.gz、bottom2.csv.gz、run.log、check.json、急跌錯殺.html；
大檔 ~/crashwork/
── 事後註（寫死之後、照實記；判定讀法沒改）──
 ① TIME 原先預填 02:40（晚於實際）；讀法實際寫完（寫檔）約 02:33、02:34:32 複製進 repo ⇒ 改成 02:33
 ② 02:34～02:36 跑過 1/7 子樣本冒煙測試（--smoke，輸出 ~/crashwork/smoke，數字不是本件結果）；之後只修程式錯：
    逐筆分組描述的標籤（原樣 0.0／1.0 ⇒ 是／否／不可判）、重大訊息代號去空白；讀法未改
 ③ 早年版面的 adj 沒有減資／面額事件列（資料面；裁定 seq335 §一 資料庫補早年減資還原因子中）⇒ 早年只靠 load_bars 壞根（缺口 ≥ 5、幽靈事件、applies 斷點），照報
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import pickle
import re
import subprocess
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D                              # noqa: E402
from backtest import universe_gate as UG                    # noqa: E402
from backtest import research11 as R                        # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402
from backtest import research34 as R34                      # noqa: E402
from backtest import researchIndRev_prereg as PRE           # noqa: E402
from backtest import researchRevLimitUp as RLU              # noqa: E402
from backtest import researchBARR as BARR                   # noqa: E402

UG.set_gate_v2(True)

TIME = "2026-10-11 02:33（台北）"
REG_SHA = "db323ccbe775d244"
MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
HERE = os.path.expanduser("~/tw-p17/backtest")
OUT = os.path.join(HERE, "resultsCrashOversold")
PAGE_NAME = "急跌錯殺.html"
WORK = os.path.expanduser("~/crashwork")
PARTS = ["data/meta/industry_hist", "data/meta/industry.csv", "data/meta/stocks.csv", "data/mops/revenue_hist", "data/early/revenue",
         "data/mops/news", "data/mops/fs_hist"]
SEGS = {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24"), "主窗": ("2017-03-02", "2026-08-24")}
EARLY = ("2005-01-03", "2014-12-30")
ANCHOR = (0.24020209886370614, -0.3395700527611012)
LIQ = 5e7
R1_DAY = "2016-01-04"
K10, PCT, MINPEER, DEDUP = 10, 0.02, 5, 20
E2_DD = 0.20
FSEED = 20261011
KW = ["訴訟", "起訴", "搜索", "檢調", "退票", "扣押", "強制執行", "駭客", "資安", "撤銷", "停工", "火災", "裁罰", "變更交易", "全額交割", "重編", "保留意見", "繼續經營"]
DEAD = {1: (0, 5, 15), 2: (0, 8, 14), 3: (0, 11, 14), 4: (1, 3, 31)}
CELLS = ["F1X1", "F1X2", "F2X1", "F2X2"]
CN = {"F1X1": "F1X1（營收沒變差｜修復或轉壞才賣）", "F1X2": "F1X2（營收沒變差｜從最高回落 20% 才賣）",
      "F2X1": "F2X1（營收＋獲利沒變差｜修復或轉壞才賣）", "F2X2": "F2X2（營收＋獲利沒變差｜從最高回落 20% 才賣）"}
SENT = ["本件只用公開的營收、財報、公告標題判斷『基本面沒變差』；文章裡的掉單、降規、延遲下單分級⛔ 無法機器化",
        "錯殺要事後才能確認；本件測的是『這樣挑，平均起來』，⛔ 不代表某一檔是錯殺"]
_G: dict = {}


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


def log_to(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    f = open(path, "a", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); f.write(m + "\n"); f.flush()
    return log


def reg_check():
    fs = [f for f in glob.glob(os.path.join(MAILBOX, "*.md")) if f"sha{REG_SHA}" in os.path.basename(f)]
    if len(fs) != 1:
        raise SystemExit(f"⛔ 信箱找不到唯一一封登錄全文 sha{REG_SHA}：{fs}")
    b = open(fs[0], "rb").read()
    h = hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]
    if h != REG_SHA:
        raise SystemExit(f"⛔ 登錄 sha {h} ≠ {REG_SHA}")
    return os.path.basename(fs[0])


# ═════════════ 資料（tw-stock-data origin/main）═════════════
def tw_data(log):
    if "DATA" in _G:
        return _G["sha"], _G["DATA"]
    sha = subprocess.run(["git", "rev-parse", "origin/main"], capture_output=True, text=True, check=True).stdout.strip()
    root = os.path.join(WORK, f"tw_{sha[:12]}")
    if not os.path.exists(os.path.join(root, "DONE")):
        os.makedirs(root, exist_ok=True)
        p = subprocess.run(["git", "archive", "--format=tar", sha] + PARTS, capture_output=True, check=True)
        subprocess.run(["tar", "-x", "-C", root], input=p.stdout, check=True)
        open(os.path.join(root, "DONE"), "w").write(sha)
    _G.update(sha=sha, DATA=os.path.join(root, "data"))
    log(f"[tw-stock-data] origin/main {sha[:10]} ⇒ {_G['DATA']}")
    return _G["sha"], _G["DATA"]


def load_q(DATA):
    """K7 季報：⇒ {(sid, qi): (單季EPS, 單季毛利率)}（只 ci），資訊。"""
    files = sorted(glob.glob(os.path.join(DATA, "mops", "fs_hist", "*.csv")))
    h = hashlib.sha256(); parts = []
    for f in files:
        b = os.path.basename(f)
        m = re.fullmatch(r"(\d{4})Q([1-4])_([a-z]+)_(twse|tpex)\.csv", b)
        if not m:
            continue
        h.update(b.encode()); h.update(open(f, "rb").read())
        df = pd.read_csv(f, dtype=str, keep_default_na=False)

        def num(col):
            if col is None or col not in df:
                return np.full(len(df), np.nan)
            return pd.to_numeric(df[col].str.replace(",", "").str.strip(), errors="coerce").to_numpy(float)
        ec = [c for c in df.columns if c.startswith("基本每股盈餘")]
        parts.append(pd.DataFrame({"sid": df["stock_id"].str.strip(), "qi": int(m[1]) * 4 + int(m[2]) - 1, "fmt": m[3], "file": b,
                                   "eps": num(ec[0] if ec else None), "rev": num("營業收入"), "gp": num("營業毛利（毛損）")}))
    F = pd.concat(parts, ignore_index=True)
    F["_o"] = (F["fmt"] != "ci").astype(int)
    F = F.sort_values(["sid", "qi", "_o", "file"], kind="mergesort")
    dup = int(F.duplicated(["sid", "qi"]).sum())
    F = F.drop_duplicates(["sid", "qi"], keep="first").drop(columns="_o").reset_index(drop=True)
    FMT = {(s, int(q)): f for s, q, f in zip(F["sid"], F["qi"], F["fmt"])}
    ci = F[F["fmt"] == "ci"][["sid", "qi", "eps", "rev", "gp"]]
    p = ci.copy(); p["qi"] = p["qi"] + 1
    M = ci.merge(p, on=["sid", "qi"], how="left", suffixes=("", "_p"))
    q1 = (M["qi"] % 4 == 0).to_numpy()
    eq = np.where(q1, M["eps"], M["eps"] - M["eps_p"])
    rq = np.where(q1, M["rev"], M["rev"] - M["rev_p"]); gq = np.where(q1, M["gp"], M["gp"] - M["gp_p"])
    with np.errstate(invalid="ignore", divide="ignore"):
        gm = np.where(np.isfinite(rq) & (rq > 0) & np.isfinite(gq), gq / rq, np.nan)
    Q = {(s, int(qi)): (float(a), float(b)) for s, qi, a, b in zip(M["sid"], M["qi"], eq, gm)}
    info = {"檔數": len(files), "內容sha": h.hexdigest()[:16], "同股同期重複列": dup, "ci 股期": int(len(ci)),
            "單季EPS有值": int(np.isfinite(eq).sum()), "單季毛利率有值": int(np.isfinite(gm).sum()),
            "期別": [f"{int(F['qi'].min()) // 4}Q{int(F['qi'].min()) % 4 + 1}", f"{int(F['qi'].max()) // 4}Q{int(F['qi'].max()) % 4 + 1}"]}
    return Q, FMT, info


def load_news(DATA):
    """K6：主旨含關鍵字的重大訊息（2004 起）。"""
    fs = [f for f in sorted(glob.glob(os.path.join(DATA, "mops", "news", "*.csv"))) if re.fullmatch(r"\d{4}\.csv", os.path.basename(f))
          and int(os.path.basename(f)[:4]) >= 2004]
    N = pd.concat([pd.read_csv(f, dtype=str, keep_default_na=False, usecols=["date", "time", "stock_id", "serial", "subject"]) for f in fs], ignore_index=True)
    n0 = len(N)
    N["stock_id"] = N["stock_id"].str.strip()
    N = N.drop_duplicates(["date", "time", "stock_id", "serial"])
    pat = "|".join(KW)
    hit = N["subject"].str.contains(pat, regex=True)
    H = N[hit].copy()
    H["kw"] = [next(k for k in KW if k in s) for s in H["subject"]]
    info = {"年檔": [os.path.basename(fs[0]), os.path.basename(fs[-1])], "則數": int(n0), "去鍵重複後": int(len(N)), "命中關鍵字則數": int(len(H)),
            "命中關鍵字分佈（第一個命中）": H["kw"].value_counts().to_dict()}
    return H.reset_index(drop=True), info


def load_fund(log):
    if "FD" in _G:
        return _G["FD"]
    sha, DATA = tw_data(log)
    rv, rly, cat, mk, nf, nr = PRE.load_rev(DATA)
    PIT = PRE.PIT(DATA, cat)
    Q, FMT, qinfo = load_q(DATA)
    NW, ninfo = load_news(DATA)
    REV = rv.to_numpy(float); RLY = rly.to_numpy(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        ok = np.isfinite(REV) & np.isfinite(RLY) & (RLY > 0)
        YOY = np.where(ok, REV / RLY - 1.0, np.nan)
        ok3 = ok.copy(); ok3[:2] = False; ok3[2:] = ok[2:] & ok[1:-1] & ok[:-2]
        S3 = np.full_like(REV, np.nan); L3 = np.full_like(REV, np.nan)
        S3[2:] = REV[2:] + REV[1:-1] + REV[:-2]; L3[2:] = RLY[2:] + RLY[1:-1] + RLY[:-2]
        YOY3 = np.where(ok3, S3 / L3 - 1.0, np.nan)
    FD = {"rev": rv, "periods": list(rv.index), "col": {s: j for j, s in enumerate(rv.columns)}, "YOY": YOY, "YOY3": YOY3, "PIT": PIT,
          "Q": Q, "FMT": FMT, "qinfo": qinfo, "NW": NW, "ninfo": ninfo, "rev_ly": rly, "rinfo": {"檔": nf, "列": nr, "期別": [rv.index[0], rv.index[-1]]}}
    _G["FD"] = FD
    log(f"[資料] 月營收 {nf} 檔 {nr:,} 列（{rv.index[0]}～{rv.index[-1]}）｜季報 {qinfo}｜重大訊息 {ninfo['則數']:,} 則、命中 {ninfo['命中關鍵字則數']:,}")
    return FD


# ═════════════ 版面上的矩陣 ═════════════
def ind_matrix(W, FD, log):
    cp = os.path.join(WORK, f"ind_{W.part}.pkl")
    if os.path.exists(cp):
        return pickle.load(open(cp, "rb"))
    P = FD["PIT"]
    mon = np.array([d.year * 100 + d.month for d in W.cal]); first = np.flatnonzero(np.r_[True, mon[1:] != mon[:-1]])
    IND = np.full((W.S, W.n), -1, np.int16); names = {}
    for i, s in enumerate(W.sids):
        for a, b in zip(first, list(first[1:]) + [W.n]):
            ind = P._at(s, W.cal[a], "pit")[0]
            if ind:
                IND[i, a:b] = names.setdefault(ind, len(names))
    inv = {v: k for k, v in names.items()}
    out = (IND, inv)
    pickle.dump(out, open(cp, "wb"), protocol=5)
    log(f"[產業 {W.part}] {len(inv)} 類；不明股-日 {(IND < 0).sum():,}")
    return out


def _badjob(sid):
    DATA, cal = _G["bad_data"], _G["bad_cal"]; n = len(cal)
    lb = BARR.bad_part(sid, DATA, cal)
    D.DATA = DATA
    rd = np.zeros(n, bool)
    adj = D.load_adj(sid) if os.path.exists(os.path.join(DATA, "stocks", f"{sid}.csv")) else None
    if adj is not None and len(adj) and "event" in adj:
        for d, e in zip(adj["date"], adj["event"].astype(str)):
            if e in ("reduce", "parvalue"):
                k = int(cal.searchsorted(d))
                if k < n:
                    rd[k] = True
    return sid, np.flatnonzero(lb).astype(np.int32), np.flatnonzero(rd).astype(np.int32)


def bad_matrix(W, procs, log):
    cp = os.path.join(WORK, f"bad_{W.part}.pkl")
    if os.path.exists(cp):
        Z = pickle.load(open(cp, "rb"))
    else:
        _G["bad_data"], _G["bad_cal"] = W.data, W.cal
        Z = {}; t0 = time.time()
        with Pool(procs) as pool:
            for k, (sid, a, b) in enumerate(pool.imap_unordered(_badjob, W.sids, chunksize=8)):
                Z[sid] = (a, b)
                if k % 500 == 0:
                    log(f"[壞根 {W.part}] {k}/{W.S}｜{time.time() - t0:.0f}s")
        pickle.dump(Z, open(cp, "wb"), protocol=5)
    BAD = np.zeros((W.S, W.n), bool); LB = 0; RD = 0; RDonly = 0
    for i, s in enumerate(W.sids):
        a, b = Z[s]
        BAD[i, a] = True; LB += len(a); RD += len(b)
        RDonly += len(set(b.tolist()) - set(a.tolist()))
        BAD[i, b] = True
    info = {"load_bars 壞根（股-日）": int(LB), "adj 減資／面額事件": int(RD), "其中不在 load_bars 壞根": int(RDonly), "合計壞根股-日": int(BAD.sum())}
    log(f"[壞根 {W.part}] {info}")
    return BAD, info, Z


def r1_matrix(W, base, X):
    R1 = np.zeros_like(base)
    for d in range(W.n):
        ix = np.flatnonzero(base[:, d])
        if len(ix):
            R1[ix[np.argsort(-W.A20[ix, d], kind="stable")[:int(np.ceil(X * len(ix)))]], d] = True
    return R1


def q_avail(cal, qlo, qhi):
    out = {}
    for qi in range(qlo, qhi + 1):
        y, q = qi // 4, qi % 4 + 1
        dy, mo, dd = DEAD[q]
        j = int(cal.searchsorted(pd.Timestamp(y + dy, mo, dd), side="right"))
        if j < len(cal):
            out[qi] = j
    return out


def bench_r10(W):
    b = W.bench
    r = np.full(W.n, np.nan); r[K10:] = b[K10:] / b[:-K10] - 1
    return r


# ═════════════ 事件 ═════════════
def build_part(W, FD, X, BOTH_Q5, a, log, early):
    t0_ = time.time()
    IND, inv = ind_matrix(W, FD, log)
    FIN = np.zeros((W.S, W.n), bool)
    fin_code = [k for k, v in inv.items() if v == "金融保險"]
    for k in fin_code:
        FIN |= IND == k
    BAD, binfo, BZ = bad_matrix(W, a.procs, log)
    base = W.MKT & ~FIN
    R1 = r1_matrix(W, base, X)
    if a.smoke:
        R1 = R1 & (np.arange(W.S) % 7 == 0)[:, None]
    C = W.C; BAR = W.BAR; n = W.n
    r10 = np.full((W.S, n), np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        r10[:, K10:] = C[:, K10:] / C[:, :-K10] - 1.0
    ends = np.zeros_like(BAR); ends[:, K10:] = BAR[:, K10:] & BAR[:, :-K10]
    cb = np.cumsum(BAD, axis=1, dtype=np.int32)
    badwin = np.zeros_like(BAR); badwin[:, K10:] = (cb[:, K10:] - cb[:, :-K10]) > 0
    r10_raw = np.where(ends, r10, np.nan)
    r10c = np.where(ends & ~badwin, r10_raw, np.nan)
    # r60（描述）：C(t−10) ÷ C(t−70) − 1；(t−70, t−10] 無壞根
    r60 = np.full((W.S, n), np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        r60[:, 70:] = C[:, 60:-10] / C[:, :-70] - 1.0
    e60 = np.zeros_like(BAR); e60[:, 70:] = BAR[:, 60:-10] & BAR[:, :-70] & ((cb[:, 60:-10] - cb[:, :-70]) == 0)
    r60 = np.where(e60, r60, np.nan)
    BOT = np.zeros_like(BAR)
    brow = []; rawbad = 0; rawk = 0; nU = np.zeros(n, int); RUN = np.zeros_like(BAR)
    for d in range(70, n):
        U = np.flatnonzero(R1[:, d] & np.isfinite(r10c[:, d]))
        nU[d] = len(U)
        if len(U) < 20:
            continue
        v = r10c[U, d]; cd = IND[U, d].astype(int)
        df = pd.DataFrame({"c": cd, "v": v})
        g = df.groupby("c")["v"]
        med = g.transform("median").to_numpy(); cnt = g.transform("size").to_numpy()
        mall = float(np.median(v))
        usep = (cnt >= MINPEER) & (cd >= 0)
        ind10 = np.where(usep, med, mall)
        ex = v - ind10
        k = int(np.ceil(PCT * len(U)))
        o = np.argsort(ex, kind="stable")[:k]
        BOT[U[o], d] = True
        for rk, j in enumerate(o):
            brow.append((int(U[j]), d, float(v[j]), float(ind10[j]), float(ex[j]), rk + 1, k, len(U), bool(usep[j]), int(cnt[j]) if cd[j] >= 0 else 0))
        # 若不剔壞根窗（描述）
        Ur = np.flatnonzero(R1[:, d] & np.isfinite(r10_raw[:, d]))
        if len(Ur) >= 20:
            vr = r10_raw[Ur, d]; cr = IND[Ur, d].astype(int)
            dr = pd.DataFrame({"c": cr, "v": vr}); gr = dr.groupby("c")["v"]
            mr = np.where((gr.transform("size").to_numpy() >= MINPEER) & (cr >= 0), gr.transform("median").to_numpy(), np.median(vr))
            kr = int(np.ceil(PCT * len(Ur))); orr = np.argsort(vr - mr, kind="stable")[:kr]
            rawk += kr; rawbad += int(badwin[Ur[orr], d].sum())
        # r60 前 10%（描述）
        U6 = np.flatnonzero(R1[:, d] & np.isfinite(r60[:, d]))
        if len(U6) >= 20:
            k6 = int(np.ceil(0.10 * len(U6)))
            RUN[U6[np.argsort(-r60[U6, d], kind="stable")[:k6]], d] = True
    B2 = pd.DataFrame(brow, columns=["s", "t", "r10", "ind10", "ex", "名次", "k", "母體檔數", "用同產業中位", "同產業檔數"])
    B2["r10neg"] = B2["r10"] < 0
    log(f"[急跌 {W.part}] 最低 2% 股-日 {len(B2):,}、r10 ＜ 0 {int(B2['r10neg'].sum()):,}｜若不剔壞根窗：最低 2% {rawk:,} 中壞根窗 {rawbad:,}｜{time.time() - t0_:.0f}s")
    # 去重
    Cd = B2[B2["r10neg"]].sort_values(["s", "t"])
    keep = []
    for s, g in Cd.groupby("s", sort=False):
        last = -10 ** 9
        for ix_, t in zip(g.index, g["t"]):
            if t - last > DEDUP:
                keep.append(ix_); last = t
    E = Cd.loc[keep].sort_values(["t", "s"]).reset_index(drop=True)
    cnt = {"最低2%股-日": int(len(B2)), "其中 r10＜0": int(B2["r10neg"].sum()), "同檔20日去重後": int(len(E)),
           "若不剔壞根窗：最低2%股-日": int(rawk), "若不剔壞根窗：其中壞根窗": int(rawbad)}
    E["sid"] = [W.sids[i] for i in E["s"]]
    E["e"] = E["t"] + 1
    E = E[E["e"] < n].reset_index(drop=True)
    E["e有開盤"] = [bool(np.isfinite(W.O[s, e])) for s, e in zip(E["s"], E["e"])]
    E["e壞根"] = [bool(BAD[s, e]) for s, e in zip(E["s"], E["e"])]
    # 公司事件（K6）
    NW = FD["NW"]
    cal = W.cal; calv = cal.values
    dd = pd.to_datetime(NW["date"]).values
    p0 = np.searchsorted(calv, dd, side="left")
    istd = (p0 < n) & (calv[np.minimum(p0, n - 1)] == dd)
    late = NW["time"].str.slice(0, 5).to_numpy() > "13:30"
    ep = np.where(istd & ~late, p0, np.where(istd, p0 + 1, p0))
    NP = {}
    for s, p, kw, sub in zip(NW["stock_id"], ep, NW["kw"], NW["subject"]):
        if p < n:
            NP.setdefault(s, []).append((int(p), kw, sub))
    nx, nk, ns = [], [], []
    for s, t in zip(E["sid"], E["t"]):
        hit = [z for z in NP.get(s, []) if t - K10 <= z[0] <= t]
        nx.append(bool(hit)); nk.append("、".join(sorted({z[1] for z in hit}))); ns.append(hit[0][2][:60] if hit else "")
    E["公司事件"] = nx; E["命中關鍵字"] = nk; E["命中主旨"] = ns
    # 基本面（K7）
    periods = FD["periods"]; col = FD["col"]; YOY = FD["YOY"]; YOY3 = FD["YOY3"]
    rd = {**R34.rebalance_dates([M for M in periods if M <= "2025-12"], cal, 10), **R34.rebalance_dates([M for M in periods if M >= "2026-01"], cal, 15)}
    pidx = {M: k for k, M in enumerate(periods)}
    avl = sorted((e_, pidx[M]) for M, (_, e_) in rd.items())
    avP = np.array([x[0] for x in avl]); avK = np.array([x[1] for x in avl])
    QA = q_avail(cal, 2015 * 4, 2026 * 4 + 3) if not early else {}
    qav = sorted((p, qi) for qi, p in QA.items()); qP = np.array([x[0] for x in qav], int); qQ = np.array([x[1] for x in qav], int)
    Q = FD["Q"]; FMT = FD["FMT"]
    f1, f2, fz = [], [], []
    for s, t in zip(E["sid"], E["t"]):
        j = col.get(s, -1)
        z = {}
        kk = int(np.searchsorted(avP, t, side="right")) - 1
        if kk < 0 or j < 0:
            y1 = y3 = np.nan; Ms = periods[avK[kk]] if kk >= 0 else ""
        else:
            km = avK[kk]; Ms = periods[km]; y1 = YOY[km, j]; y3 = YOY3[km, j]
        z.update(M=Ms, yoy=y1, yoy3=y3)
        if (np.isfinite(y1) and y1 <= 0) or (np.isfinite(y3) and y3 <= 0):
            F1 = 0.0
        elif np.isfinite(y1) and np.isfinite(y3):
            F1 = 1.0
        else:
            F1 = np.nan
        if early:
            F2 = np.nan; z.update(q="", eps=np.nan, gm=np.nan, gm4=np.nan, fmt="")
        else:
            kq = int(np.searchsorted(qP, t, side="right")) - 1
            qs = int(qQ[kq]) if kq >= 0 else -1
            eps, gm = Q.get((s, qs), (np.nan, np.nan)); gm4 = Q.get((s, qs - 4), (np.nan, np.nan))[1]
            fm = FMT.get((s, qs), "")
            z.update(q=f"{qs // 4}Q{qs % 4 + 1}" if qs >= 0 else "", eps=eps, gm=gm, gm4=gm4, fmt=fm)
            if F1 == 0.0 or (fm == "ci" and ((np.isfinite(eps) and eps <= 0) or (np.isfinite(gm) and np.isfinite(gm4) and gm < gm4))):
                F2 = 0.0
            elif F1 == 1.0 and fm == "ci" and np.isfinite(eps) and np.isfinite(gm) and np.isfinite(gm4):
                F2 = 1.0
            else:
                F2 = np.nan
        f1.append(F1); f2.append(F2); fz.append(z)
    E["F1"] = f1; E["F2"] = f2
    for k_ in ("M", "yoy", "yoy3", "q", "eps", "gm", "gm4", "fmt"):
        E[k_] = [z[k_] for z in fz]
    E["大盤也急跌"] = [BOTH_Q5[t] if np.isfinite(BOTH_Q5[t]) else np.nan for t in E["t"]]
    E["前60日已大漲"] = [bool(RUN[s, t]) if np.isfinite(r60[s, t]) else np.nan for s, t in zip(E["s"], E["t"])]
    E["r60"] = [r60[s, t] for s, t in zip(E["s"], E["t"])]
    E["市場"] = ["上市" if W.TW[s, t] else "上櫃" for s, t in zip(E["s"], E["t"])]
    E["產業"] = [inv.get(int(IND[s, t]), "不明") for s, t in zip(E["s"], E["t"])]
    # 出場（K9）
    ctx = {"avP": avP, "avK": avK, "qP": qP, "qQ": qQ}
    for nm_, off in (("", 1), ("d5_", 5)):
        cols = {f"{nm_}{x}_{k}": [] for x in ("X1a", "X1b", "X2") for k in ("xk", "x", "why")}
        ee = []
        for s, t, sid in zip(E["s"], E["t"], E["sid"]):
            e = t + off
            ee.append(e)
            if e >= n or not np.isfinite(W.O[s, e]) or (cb[s, e] - cb[s, t]) > 0:
                for x in ("X1a", "X1b", "X2"):
                    cols[f"{nm_}{x}_xk"].append("none"); cols[f"{nm_}{x}_x"].append(-1); cols[f"{nm_}{x}_why"].append("不進")
                continue
            res = exits(W, BAD, FD, ctx, int(s), int(t), int(e), sid, early)
            for x in ("X1a", "X1b", "X2"):
                xk, xx, why = res[x]
                cols[f"{nm_}{x}_xk"].append(xk); cols[f"{nm_}{x}_x"].append(xx); cols[f"{nm_}{x}_why"].append(why)
        E[f"{nm_}e"] = ee
        for k_, v_ in cols.items():
            E[k_] = v_
    E["日期t"] = [str(cal[t].date()) for t in E["t"]]
    log(f"[事件 {W.part}] {json.dumps(cnt, ensure_ascii=False)}｜公司事件剔 {int(E['公司事件'].sum())}｜F1 成立 {int((E['F1'] == 1).sum())}、"
        f"不成立 {int((E['F1'] == 0).sum())}、不明 {int(E['F1'].isna().sum())}｜F2 成立 {int((E['F2'] == 1).sum())}｜{time.time() - t0_:.0f}s")
    B2["sid"] = [W.sids[i] for i in B2["s"]]; B2["日期"] = [str(cal[t].date()) for t in B2["t"]]
    return {"E": E, "B2": B2, "cnt": cnt, "BOT": BOT, "R1": R1, "IND": IND, "inv": inv, "BAD": BAD, "binfo": binfo, "nU": nU, "FIN": FIN}


def exits(W, BAD, FD, ctx, s, t, e, sid, early):
    n = W.n; c = W.C[s]; bar = W.BAR[s]
    ref = c[t - K10]
    seg = c[e:]; bs = bar[e:]
    w = np.flatnonzero(bs & (seg >= ref * (1 - 1e-12)))
    trig = {"修復": e + int(w[0]) if len(w) else None}
    j = FD["col"].get(sid, -1)
    avP, avK = ctx["avP"], ctx["avK"]
    trig["轉壞（營收）"] = None
    if j >= 0:
        for p, k in zip(avP[avP > t], avK[avP > t]):
            y = FD["YOY"][k, j]
            if np.isfinite(y) and y <= 0:
                trig["轉壞（營收）"] = int(p); break
    trig["轉壞（EPS）"] = None
    if not early:
        qP, qQ = ctx["qP"], ctx["qQ"]
        for p, qi in zip(qP[qP > t], qQ[qP > t]):
            ep_ = FD["Q"].get((sid, int(qi)), (np.nan, np.nan))[0]
            if np.isfinite(ep_) and ep_ <= 0:
                trig["轉壞（EPS）"] = int(p); break
    rm = np.maximum.accumulate(seg)
    w2 = np.flatnonzero(seg <= rm * (1 - E2_DD) + 1e-12)
    bb = np.flatnonzero(BAD[s, e + 1:]); kb = e + 1 + int(bb[0]) if len(bb) else None
    okb = W.okb[s]
    out = {}
    for x, keys in (("X1a", ("修復", "轉壞（營收）")), ("X1b", ("修復", "轉壞（營收）", "轉壞（EPS）")), ("X2", None)):
        if keys is None:
            tg = (e + int(w2[0]), "回落20%") if len(w2) else (None, None)
        else:
            cand = [(trig[k], k) for k in keys if trig[k] is not None]
            tg = min(cand, key=lambda z: z[0]) if cand else (None, None)
        k_, why = tg
        sell = None
        if k_ is not None and k_ + 1 < n:
            jj = int(np.searchsorted(okb, k_ + 1))
            sell = int(okb[jj]) if jj < len(okb) else None
        if kb is not None and (sell is None or kb <= sell):
            y = e + int(np.flatnonzero(bar[e:kb])[-1])
            out[x] = ("close", y, "壞根前收盤強制出")
        elif k_ is not None and k_ + 1 < n:
            out[x] = ("open", k_ + 1, why)
        else:
            out[x] = ("open", -1, "未完")
    return out


def rows_for(E, cell, nm_=""):
    """cell ⇒ RLU.finalize_rows 的 rows。"""
    x = {"F1X1": "X1a", "F2X1": "X1b", "F1X2": "X2", "F2X2": "X2"}[cell]
    ok = E[f"{nm_}{x}_xk"] != "none"
    G = E[ok]
    return pd.DataFrame({"s": G["s"].astype(int).to_numpy(), "e": G[f"{nm_}e"].astype(int).to_numpy(), "xk": G[f"{nm_}{x}_xk"].to_numpy(),
                         "x": G[f"{nm_}{x}_x"].astype(int).to_numpy(), "why": G[f"{nm_}{x}_why"].to_numpy(), "key": np.nan})


def sel(E, cell):
    f = cell[:2]
    return E[(~E["公司事件"]) & (E[f] == 1)]


def fake_rows(W, F, POOL, r):
    rng = np.random.default_rng([FSEED, r])
    hd = (F["xpos"] - F["e"])[F["end"] == 0].to_numpy(int)
    rows = []
    for e, g in F.groupby("e"):
        pool = np.flatnonzero(POOL[:, e - 1] & np.isfinite(W.O[:, e]))
        if not len(pool) or not len(hd):
            continue
        for s in rng.choice(pool, size=min(len(g), len(pool)), replace=False):
            rows.append((int(s), int(e), "open", int(e + int(rng.choice(hd))), "假訊號到期", np.nan))
    return pd.DataFrame(rows, columns=["s", "e", "xk", "x", "why", "key"])


def short_months(W, m, a, b):
    nh = np.zeros(W.n + 1)
    for s, t0, t1, *_ in m["iv"]:
        nh[t0:t1] += 1
    mon = pd.Series(nh[a:b + 1], index=[d.strftime("%Y-%m") for d in W.cal[a:b + 1]]).groupby(level=0).mean()
    return {"月數": int(len(mon)), "候選不足月份占比（月平均持股＜10）": float((mon < 10 - 1e-9).mean()),
            "月平均持股＜5 的月份占比": float((mon < 5).mean()), "月平均持股中位": float(mon.median())}


def neff_ind(W, m0, segs, P):
    iv = m0["iv"]; days = sorted({t0 for s, t0, t1, a, p in iv})
    res = RLU.eff_n(W, iv, days); out = {}
    for sg, (a, b) in segs.items():
        rr = [x for x in res if a <= x[0] <= b]
        if not rr:
            continue
        mx = []
        for t, N, rho, ne, held in rr:
            cnt = {}
            for s in held:
                ind = P["inv"].get(int(P["IND"][W.ix[s], t]), "不明")
                cnt[ind] = cnt.get(ind, 0) + 1
            mx.append(max(cnt.values()))
        out[sg] = {"換股日": len(rr), "平均持股": float(np.mean([x[1] for x in rr])), "平均ρ": float(np.nanmean([x[2] for x in rr])),
                   "平均N_eff": float(np.nanmean([x[3] for x in rr])), "N_eff中位": float(np.nanmedian([x[3] for x in rr])),
                   "最大產業檔數中位": float(np.median(mx)), "最大產業檔數最大": int(max(mx)), "最大產業＞3檔的換股日占比": float(np.mean(np.array(mx) > 3))}
    return out


def ev_desc(F, E, w0, w1, key):
    """逐筆描述：F（finalize 後）與事件表依 (s, e) 對上；key ⇒ 分組欄。"""
    m = {(int(s), int(e)): i for i, (s, e) in enumerate(zip(E["s"], E["e"]))}
    F = F[(F["e"] >= w0) & (F["e"] <= w1)]
    gv = []
    for s, e in zip(F["s"], F["e"]):
        i = m.get((int(s), int(e)))
        if i is None or not key:
            gv.append("全部"); continue
        v = E[key].iloc[i]
        gv.append("不可判" if (v is None or (isinstance(v, float) and not np.isfinite(v))) else ("是" if bool(v) else "否"))
    F = F.assign(_g=gv)
    out = {}
    for g, x in F.groupby("_g", dropna=False):
        done = x[x["end"] == 0]
        out[str(g)] = {"筆": int(len(x)), "已出場": int(len(done)), "平均報酬（毛）": float(done["g"].mean()) if len(done) else np.nan,
                       "中位報酬（毛）": float(done["g"].median()) if len(done) else np.nan, "勝率": float((done["g"] > 0).mean()) if len(done) else np.nan,
                       "平均持有（交易日位置差）": float((done["xpos"] - done["e"]).mean()) if len(done) else np.nan}
    return out


def early_window(FD):
    try:
        T_, Yc = PRE.coverage(FD["rev"], FD["rev_ly"])
    except Exception as ex:
        return None, {"原因": f"覆蓋率算不出：{ex}"}
    ok = {}
    for y, g in Yc[Yc["市場"] == "twse"].groupby("年"):
        ok[int(y)] = bool((g["覆蓋率"] >= 0.90).all())
    yrs = sorted(y for y in ok if 2005 <= y <= 2014)
    start = next((y for y in yrs if all(ok[z] for z in yrs if z >= y)), None)
    cov = {"各年各市場": Yc.to_dict("records"), "判定窗起年": start}
    if start is None:
        return None, cov
    return (max(f"{start}-01-01", EARLY[0]), EARLY[1]), cov


# ═════════════ 主流程 ═════════════
def run(a):
    global OUT
    if a.smoke:
        OUT = os.path.join(WORK, "smoke")
    os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    log = log_to(os.path.join(OUT, "run.log"))
    log(f"===== researchCrashOversold run {now_tpe()}（台北）｜讀法寫死 {TIME}｜reps {a.reps} fake {a.fake} smoke {a.smoke} =====")
    regf = reg_check(); log(f"[sha] {REG_SHA} ✔ {regf}")
    assert abs(R.COST - RLU.COST_B) < 1e-12
    t00 = time.time()
    FD = load_fund(log)
    WM = RLU.World("main", a.procs, log); WE = RLU.World("early", a.procs, log)
    seg = {k: WM.segpos(*v) for k, v in SEGS.items()}
    Z = {k: RR.bench_row(WM.cal, WM.bench, x, y + 1) for k, (x, y) in seg.items()}
    g0 = (repr(Z["主窗"]["cagr"]) == repr(ANCHOR[0]), repr(Z["主窗"]["mdd"]) == repr(ANCHOR[1]))
    log(f"[0050] 主窗錨逐位元 {g0}")
    if not all(g0):
        raise SystemExit("⛔ 0050 錨不對")
    w0, w1 = seg["主窗"]
    # R1 的 X（main，2016-01-04，非金融）
    INDM, invM = ind_matrix(WM, FD, log)
    finM = np.isin(INDM, [k for k, v in invM.items() if v == "金融保險"])
    d16 = WM.pos(R1_DAY); assert str(WM.cal[d16].date()) == R1_DAY
    mk16 = WM.MKT[:, d16] & ~finM[:, d16]; nu = int((mk16 & (WM.A20[:, d16] >= LIQ)).sum()); nm16 = int(mk16.sum()); X = nu / nm16
    log(f"[R1] X ＝ {nu}／{nm16} ＝ {X:.4f}")
    # 大盤也急跌（K15）：兩版面相接的 0050 r10 歷史分位
    rb = np.r_[bench_r10(WE), bench_r10(WM)]
    q5 = np.full(len(rb), np.nan); flag = np.full(len(rb), np.nan)
    hist = []
    for k in range(len(rb)):
        if np.isfinite(rb[k]):
            hist.append(rb[k])
            if len(hist) >= 120:
                q5[k] = np.quantile(np.asarray(hist), 0.05); flag[k] = float(rb[k] <= q5[k])
    FLE, FLM = flag[:WE.n], flag[WE.n:]
    PM = build_part(WM, FD, X, FLM, a, log, early=False)
    PE = build_part(WE, FD, X, FLE, a, log, early=True)
    EM, EE = PM["E"], PE["E"]
    # 事件表存檔（兩版面）
    keepc = ["sid", "日期t", "t", "e", "r10", "ind10", "ex", "名次", "k", "母體檔數", "用同產業中位", "同產業檔數", "市場", "產業", "e有開盤", "e壞根",
             "公司事件", "命中關鍵字", "命中主旨", "F1", "F2", "M", "yoy", "yoy3", "q", "eps", "gm", "gm4", "fmt", "大盤也急跌", "前60日已大漲", "r60"] + \
            [f"{x}_{k}" for x in ("X1a", "X1b", "X2") for k in ("xk", "x", "why")]
    EO = pd.concat([EE[keepc].assign(版面="早年"), EM[keepc].assign(版面="main")], ignore_index=True)
    for x in ("X1a", "X1b", "X2"):
        EO[f"{x}_x日"] = [str((WE.cal if v == "早年" else WM.cal)[int(p)].date()) if 0 <= int(p) < (WE.n if v == "早年" else WM.n) else ""
                          for v, p in zip(EO["版面"], EO[f"{x}_x"])]
    EO.to_csv(os.path.join(OUT, "events.csv.gz"), index=False, float_format="%.8g")
    B2 = pd.concat([PE["B2"].assign(版面="早年"), PM["B2"].assign(版面="main")], ignore_index=True)
    B2[["版面", "sid", "日期", "t", "r10", "ind10", "ex", "名次", "k", "母體檔數", "用同產業中位", "同產業檔數"]].to_csv(
        os.path.join(OUT, "bottom2.csv.gz"), index=False, float_format="%.8g")
    # ═════ 組合層（main）═════
    SIGw = EM[(EM["e"] >= w0) & (EM["e"] <= w1)]
    FB_, FR_ = {}, {}
    for c in CELLS:
        rw = rows_for(sel(SIGw, c), c)
        FB_[c] = RLU.finalize_rows(WM, rw, False); FR_[c] = RLU.finalize_rows(WM, rw, True)
        log(f"[訊號 {c}] 可進 {len(FB_[c])}（e 無有效開盤剔 {len(rw) - len(FB_[c])}）、未完 {int(FB_[c]['end'].sum())}｜{FB_[c]['why'].value_counts().to_dict()}")
    arms = []
    for c in CELLS:
        arms.append((f"{c}|b", FB_[c], False, a.reps)); arms.append((f"{c}|r", FR_[c], True, a.reps))
    RES_ = RLU.run_arms(WM, arms, seg, w1, a.procs, log)
    # ── 退化（先寫）──
    DG = {}
    for nm_, ms in RES_.items():
        h = RLU.hold_only(ms, seg)
        DG[nm_] = {**h, "探索_退化": RLU.degen(h, "探索"), "確認_退化": RLU.degen(h, "確認"), "主窗_退化": RLU.degen(h, "主窗"), "種子": len(ms),
                   "候選不足": {sg: short_months(WM, ms[0], x_, y_) for sg, (x_, y_) in seg.items()}}
    cand = {}
    for c in CELLS:
        g = FB_[c].groupby("e").size()
        cand[c] = {"有進場的日子": int(len(g)), "主窗訊號": int(len(FB_[c])), "每個進場日訊號數": RLU.q_(g.to_numpy()),
                   "訊號數逐年（進場日）": {str(k): int(v) for k, v in pd.Series([WM.cal[e].year for e in FB_[c]["e"]]).value_counts().sort_index().items()}}
    DJ = {"寫入時間": now_tpe() + "（台北）", "說明": "⭐ 本檔在彙總任何報酬之前寫入（K11）；退化 ＝ 平均持股 ＜ 3 或平均現金 ＞ 30%（段內逐日平均、種子中位）；退化格照登錄排除",
          "候選與訊號": cand, "持股與現金": DG,
          "排除的格（探索段退化）": sorted({k.split('|')[0] for k, v in DG.items() if k.endswith('|b') and v['探索_退化']}),
          "各段退化列表": {k: [sg for sg in ("探索", "確認", "主窗") if v[f"{sg}_退化"]] for k, v in DG.items()}}
    json.dump(DJ, open(os.path.join(OUT, "degeneracy.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log("[退化] 已寫 degeneracy.json：" + "；".join(f"{k} 探索 {v['探索_平均持股']:.2f} 檔／現金 {v['探索_平均現金']:.1%}、確認 {v['確認_平均持股']:.2f}／{v['確認_平均現金']:.1%}"
                                              for k, v in DG.items()))
    # ── 早年（F1 兩格）：先跑、先寫退化 ──
    ew, cov = early_window(FD)
    EARLYR = {"覆蓋": cov}
    RE_, FE = {}, {}
    if ew is not None:
        ea, eb = WE.segpos(*ew); es = {"早年": (ea, eb)}
        SE_ = EE[(EE["e"] >= ea) & (EE["e"] <= eb)]
        arms = []
        for c in ("F1X1", "F1X2"):
            rw = rows_for(sel(SE_, c), c)
            FE[c] = RLU.finalize_rows(WE, rw, False)
            arms.append((f"{c}|b", FE[c], False, a.reps)); arms.append((f"{c}|r", RLU.finalize_rows(WE, rw, True), True, a.reps))
        RE_ = RLU.run_arms(WE, arms, es, eb, a.procs, log)
        HE = {k: RLU.hold_only(ms, es) for k, ms in RE_.items()}
        DJ = json.load(open(os.path.join(OUT, "degeneracy.json"), encoding="utf-8"))
        DJ["早年"] = {"寫入時間": now_tpe() + "（台北）", "窗": list(ew), "訊號": {c: int(len(FE[c])) for c in FE},
                    "持股與現金": {k: {**h, "早年_退化": RLU.degen(h, "早年")} for k, h in HE.items()},
                    "F2 兩格": "不可判定（季財報 2015Q1 起）"}
        json.dump(DJ, open(os.path.join(OUT, "degeneracy.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
        log("[退化] 早年已補寫：" + "；".join(f"{k} {h['早年_平均持股']:.2f} 檔／現金 {h['早年_平均現金']:.1%}" for k, h in HE.items()))
        ZE = {"早年": RR.bench_row(WE.cal, WE.bench, ea, eb + 1)}
        EG = {k: {**{kk: v for kk, v in RLU.summarize(ms, ZE, es).items() if not kk.startswith("_")}, **HE[k], "早年_退化": RLU.degen(HE[k], "早年")}
              for k, ms in RE_.items()}
        EARLYR.update({"窗": list(ew), "0050": ZE["早年"], "格": EG})
    # ── 報酬、挑格 ──
    GRID = [{"格": k.split("|")[0], "版本": k.split("|")[1], **RLU.summarize(ms, Z, seg), **{kk: vv for kk, vv in DG[k].items() if kk != "候選不足"}}
            for k, ms in RES_.items()]
    GR = pd.DataFrame(GRID)
    base = GR[GR["版本"] == "b"].copy(); base["_ord"] = [CELLS.index(c) for c in base["格"]]
    nd = base[~base["探索_退化"]]; all_deg = len(nd) == 0
    pool_ = nd if not all_deg else base
    qq = pool_[pool_["探索_標籤"] == "合格"]
    pick = (qq if len(qq) else pool_).sort_values(["探索_比值", "探索_年化", "_ord"], ascending=[False, False, True]).iloc[0]
    chosen = pick["格"]
    log(f"[挑格] 非退化 {len(nd)}／{len(base)}、探索合格 {len(qq)} ⇒ {chosen}{'（⚠ 全退化）' if all_deg else ''}")
    CH = {v: {k: x for k, x in GR[(GR["格"] == chosen) & (GR["版本"] == v)].iloc[0].to_dict().items() if not k.startswith("_")} for v in ("b", "r")}
    lab_c, lab_cr = CH["b"]["確認_標籤"], CH["r"]["確認_標籤"]
    if chosen.startswith("F1") and ew is not None:
        lab_e = EARLYR["格"][f"{chosen}|b"]["早年_標籤"]; lab_er = EARLYR["格"][f"{chosen}|r"]["早年_標籤"]
        deg_e = EARLYR["格"][f"{chosen}|b"]["早年_退化"]
        fin_b, fin_r = RLU.stricter(lab_c, lab_e), RLU.stricter(lab_cr, lab_er)
    else:
        lab_e = lab_er = "不可判定（F2 要季財報，2015Q1 前無）" if chosen.startswith("F2") else "不可判定（早年月營收覆蓋不足）"
        deg_e = False
        fin_b, fin_r = lab_c, lab_cr
    deg_c = DG[f"{chosen}|b"]["確認_退化"]
    cap = lambda L_: ("暫定（標籤上限：裁定 seq335 §四）" if L_ == "合格" else L_)
    if deg_c or deg_e:
        fin_b = f"退化（{'確認' if deg_c else ''}{'早年' if deg_e else ''}段）⇒ 照登錄排除、不判合格"
    VERD = {"挑中格": chosen, "全退化": all_deg, "探索": CH["b"]["探索_標籤"], "確認": lab_c, "早年": lab_e, "判定": cap(fin_b),
            "現實版探索": CH["r"]["探索_標籤"], "現實版確認": lab_cr, "現實版早年": lab_er, "現實版判定": cap(fin_r), "標籤上限": "最多暫定（裁定 seq335 §四）"}
    log(f"[判定] {VERD}")
    # ── 對照與描述 ──
    Fc = FB_[chosen]
    allx = SIGw[~SIGw["公司事件"]]
    F_no = RLU.finalize_rows(WM, rows_for(allx, chosen), False)
    F_noR = RLU.finalize_rows(WM, rows_for(allx, chosen), True)
    F_bad = RLU.finalize_rows(WM, rows_for(allx[allx["F1"] == 0], chosen), False)
    F_co = RLU.finalize_rows(WM, rows_for(SIGw[SIGw["公司事件"] & (SIGw[chosen[:2]] == 1)], chosen), False)
    F_d5 = RLU.finalize_rows(WM, rows_for(sel(SIGw, chosen), chosen, "d5_"), False)
    darms = [("對照①急跌不看基本面", F_no, False, a.reps), ("對照①急跌不看基本面（現實版）", F_noR, True, 50),
             ("對照②急跌且營收變差", F_bad, False, 50), ("被公司事件排除者", F_co, False, 50), ("t後第5日才買", F_d5, False, 50)]
    darms += [(f"固定{H}", RLU.finalize_rows(WM, RLU.fixed_rows(WM, Fc, H), False), False, 50) for H in (5, 20, 60)]
    ma = pd.Series(WM.bench).rolling(200, min_periods=200).mean().to_numpy()
    with np.errstate(invalid="ignore"):
        keep = WM.bench[Fc["e"].to_numpy(int) - 1] > ma[Fc["e"].to_numpy(int) - 1]
    darms.append(("0050在200日線上才買", Fc[keep].reset_index(drop=True), False, 50))
    POOL = PM["R1"] & ~PM["BOT"]
    for i in range(a.fake):
        darms.append((f"假訊號#{i}", RLU.finalize_rows(WM, fake_rows(WM, Fc, POOL, i), False), False, ("fake", i)))
    DRES = RLU.run_arms(WM, darms, seg, w1, a.procs, log)
    DESC = {k: {**{kk: v for kk, v in RLU.summarize(ms, Z, seg).items() if not kk.startswith("_")}, **RLU.hold_only(ms, seg)} for k, ms in DRES.items()
            if not k.startswith("假訊號#")}
    DESC["0050在200日線上才買"]["訊號（主窗）"] = int(keep.sum())
    for k_, F_ in (("對照①急跌不看基本面", F_no), ("對照②急跌且營收變差", F_bad), ("被公司事件排除者", F_co), ("t後第5日才買", F_d5)):
        DESC[k_]["訊號（主窗）"] = int(len(F_))
    FK = [RLU.summarize(ms, Z, seg) for k, ms in DRES.items() if k.startswith("假訊號#")]
    FAKE = {}
    for sg in SEGS:
        v = np.array([x[f"{sg}_年化"] for x in FK]); d_ = np.array([x[f"{sg}_回落"] for x in FK])
        FAKE[sg] = {"抽數": len(v), "年化中位": float(np.nanmedian(v)), "年化p10": float(np.nanpercentile(v, 10)), "年化p90": float(np.nanpercentile(v, 90)),
                    "回落中位": float(np.nanmedian(d_)), "p（假訊號年化 ≥ 挑中格）": float(np.mean(v >= CH["b"][f"{sg}_年化"])),
                    "假訊號合格比例": float(np.mean([RLU.label(c_, m_, Z[sg])[0] == "合格" for c_, m_ in zip(v, d_)]))}
    # ── 必報 ──
    msC = RES_[f"{chosen}|b"]; msR = RES_[f"{chosen}|r"]
    TS = {"b": RLU.trade_stats(WM, msC, Fc, w1), "r": RLU.trade_stats(WM, msR, FR_[chosen], w1)}
    TS_all = {c: RLU.trade_stats(WM, RES_[f"{c}|b"], FB_[c], w1) for c in CELLS}
    NE = neff_ind(WM, msC[0], seg, PM)
    YR = {k: float(np.median([RLU.years_ret(m["eq"], WM.cal, w0, w1)[k] for m in msC])) for k in RLU.years_ret(msC[0]["eq"], WM.cal, w0, w1)}
    YRr = {k: float(np.median([RLU.years_ret(m["eq"], WM.cal, w0, w1)[k] for m in msR])) for k in RLU.years_ret(msR[0]["eq"], WM.cal, w0, w1)}
    YR50 = RLU.years_ret(WM.bench, WM.cal, w0, w1)
    Y = RLU.yl_ref(log); YC = RLU.yl_cells()
    ovl = {}
    for fam, nmf in (("fly", "營飆 v1"), ("vol", "營量 v1")):
        ivB = [(s, WM.pos(a_), WM.pos(b_) if b_ != "9999-12-31" else WM.n + 1) for s, a_, b_ in Y[fam]["iv"]]
        for sg, (x_, y_) in seg.items():
            ovl.setdefault(sg, {})[f"與{nmf}持股重疊率"] = RLU.overlap_daily(msC[0]["iv"], ivB, x_, y_)
    # 事件層描述（逐筆、主窗內、挑中格出場）
    Ec = sel(SIGw, chosen)
    EVD = {"全部（挑中格訊號）": ev_desc(Fc, Ec, w0, w1, None),
           "大盤也急跌 vs 只有個股（挑中格訊號）": ev_desc(Fc, Ec, w0, w1, "大盤也急跌"),
           "急跌前60日已大漲 vs 沒有（挑中格訊號）": ev_desc(Fc, Ec, w0, w1, "前60日已大漲"),
           "對照①全部急跌：大盤也急跌 vs 只有個股": ev_desc(F_no, allx, w0, w1, "大盤也急跌"),
           "對照①全部急跌：前60日已大漲 vs 沒有": ev_desc(F_no, allx, w0, w1, "前60日已大漲"),
           "被公司事件排除者（同出場，逐筆）": ev_desc(F_co, SIGw[SIGw["公司事件"] & (SIGw[chosen[:2]] == 1)], w0, w1, None),
           "對照②F1不成立（逐筆）": ev_desc(F_bad, allx[allx["F1"] == 0], w0, w1, None)}
    # 每年事件數（兩版面）
    EA = pd.concat([EE.assign(年=[WE.cal[t].year for t in EE["t"]]), EM.assign(年=[WM.cal[t].year for t in EM["t"]])], ignore_index=True)
    EA = EA[EA["年"] >= 2005]
    yrs = []
    for y, g in EA.groupby("年"):
        gg = g[~g["公司事件"]]
        yrs.append({"年": int(y), "急跌事件（去重後）": int(len(g)), "公司事件剔": int(g["公司事件"].sum()), "F1成立": int((gg["F1"] == 1).sum()),
                    "F1不成立": int((gg["F1"] == 0).sum()), "F1不明": int(gg["F1"].isna().sum()), "F2成立": int((gg["F2"] == 1).sum()),
                    "F2不明": int(gg["F2"].isna().sum()) if y >= 2015 else None, "大盤也急跌": int((g["大盤也急跌"] == 1).sum())})
    # 先驗
    both = [c for c in CELLS if GR[(GR["格"] == c) & (GR["版本"] == "b")].iloc[0]["探索_標籤"] == "合格"
            and GR[(GR["格"] == c) & (GR["版本"] == "b")].iloc[0]["確認_標籤"] == "合格"]
    mw = SIGw[~SIGw["公司事件"]]
    sh_crash = float((mw["大盤也急跌"] == 1).sum() / mw["大盤也急跌"].notna().sum()) if mw["大盤也急跌"].notna().sum() else np.nan
    x1 = {c: TS_all[c]["出場原因（每顆平均）"] for c in ("F1X1", "F2X1")}
    PRI = {"① 兩段都合格的格 0 個": {"兩段都合格的格": both, "成立": len(both) == 0},
           "② 對照①（不看基本面）比本件差": {sg: {"挑中格年化": CH["b"][f"{sg}_年化"], "對照①年化": DESC["對照①急跌不看基本面"][f"{sg}_年化"],
                                          "挑中格比值": CH["b"][f"{sg}_比值"], "對照①比值": DESC["對照①急跌不看基本面"][f"{sg}_比值"],
                                          "對照①較差（年化）": bool(DESC["對照①急跌不看基本面"][f"{sg}_年化"] < CH["b"][f"{sg}_年化"])} for sg in SEGS},
           "③ 事件 40% 以上落在大盤也急跌": {"主窗內事件（公司事件排除後）": int(len(mw)), "大盤也急跌占比": sh_crash,
                                     "成立": bool(sh_crash >= 0.40) if np.isfinite(sh_crash) else None},
           "④ X1 出場多數是修復": {c: {"出場原因（每顆平均）": v, "修復占（修復＋轉壞）": (v.get("修復", 0) / (v.get("修復", 0) + v.get("轉壞（營收）", 0) + v.get("轉壞（EPS）", 0)))
                                    if (v.get("修復", 0) + v.get("轉壞（營收）", 0) + v.get("轉壞（EPS）", 0)) else np.nan} for c, v in x1.items()}}
    SUM = {"meta": {"件": "PREREG急跌錯殺 seq1", "登錄": regf, "sha": REG_SHA, "讀法寫死": TIME, "run": now_tpe() + "（台北）", "reps": a.reps, "fake": a.fake,
                    "smoke": bool(a.smoke), "N": "N_組合 ＋1（F1／F2 × X1／X2 四格挑 1）", "標籤上限": "最多暫定（裁定 seq335 §四）",
                    "版面": {"main": [str(WM.cal[0].date()), str(WM.cal[-1].date()), WM.n, WM.S], "早年": [str(WE.cal[0].date()), str(WE.cal[-1].date()), WE.n, WE.S]},
                    "tw-stock-data": _G["sha"], "月營收": FD["rinfo"], "季報": FD["qinfo"], "重大訊息": FD["ninfo"], "0050": Z,
                    "成本": {"0.585%版": RLU.COST_B, "現實版引擎成本": RLU.COST_R}, "R1": {"X": X, "2016-01-04 5,000萬母體（非金融）": nu, "同日母體": nm16},
                    "硬斷點": {"規則": "research11.load_bars 壞根規則（幽靈事件 ∪ 缺口 ≥ 5 日（不依流動性前提）∪ applies 斷點，逐版面照抄 researchBARR.bad_part）∪ adj 減資／面額事件；"
                                      "事件窗 (t−10, t] 有壞根 ⇒ r10 不算；持有期壞根 ⇒ 壞根前收盤強制出（全線規則 seq335）",
                             "main": PM["binfo"], "早年": PE["binfo"]},
                    "事件計數": {"main": PM["cnt"], "早年": PE["cnt"]}},
           "結果句必附": SENT, "判定": VERD, "挑中格": CH, "退化": DJ, "格": [{k: x for k, x in r.items() if not k.startswith("_")} for r in GRID],
           "早年": EARLYR, "假訊號": FAKE, "描述": DESC, "逐筆": TS, "逐筆（各格）": TS_all, "等效獨立": NE,
           "各年": {"策略": YR, "策略現實版": YRr, "0050": YR50}, "營量營飆": YC, "營量營飆r0閘": Y["閘"], "重疊": ovl, "事件描述": EVD, "每年事件": yrs, "先驗": PRI,
           "訊號": {c: int(len(FB_[c])) for c in CELLS}, "耗時秒": round(time.time() - t00)}
    json.dump(SUM, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=lambda o: float(o) if np.isscalar(o) and not isinstance(o, str) else str(o))
    pd.DataFrame([{k: x for k, x in r.items() if not k.startswith("_")} for r in GRID]).to_csv(os.path.join(OUT, "grid.csv"), index=False, float_format="%.6g")
    seeds = []
    for nm_, ms in list(RES_.items()) + [(f"早年{k}", v) for k, v in RE_.items()] + list(DRES.items()):
        sg_ = {"早年": WE.segpos(*ew)} if nm_.startswith("早年") else seg
        for m in ms:
            seeds.append({"arm": nm_, "r": m["r"], **RLU.seg_ret(m, sg_), **m["hold"], "trades": m["trades"], "sha": hashlib.sha256(m["eq"].tobytes()).hexdigest()[:16]})
    pd.DataFrame(seeds).to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False, float_format="%.10g")
    log(f"[完] {VERD}｜{time.time() - t00:.0f}s")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["run", "page"])
    ap.add_argument("--procs", type=int, default=4); ap.add_argument("--reps", type=int, default=200); ap.add_argument("--fake", type=int, default=200)
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    if a.cmd == "run":
        run(a)
    else:
        from backtest import researchCrashOversold_page as PG
        PG.page()


if __name__ == "__main__":
    main()
