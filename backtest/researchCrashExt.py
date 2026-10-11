# -*- coding: utf-8 -*-
"""急跌延伸四件（裁定 seq336 §二發號，各 N_組合 ＋1；同一批急跌事件已看過 ⇒ 全部事後重切、標籤最多暫定）——回測線計算子代理。
⛔ 只計算：不 commit、不改既有程式與結果夾（researchCrashOversold 只 import、不改）；用語「假訊號」；⛔ 不給買賣建議。

  件（順序照裁定）                       登錄 sha            格                       同批急跌事件第 n 次切分
  rev    PREREG急跌後等營收證實 seq1     c552173c9ab53868    V1X1 V1X2 V2X1 V2X2      第 2 次
  stop   PREREG急跌後等止跌 seq1         93fe0f2cab25fd68    S1X1 S1X2 S2X1 S2X2      第 3 次
  inst   PREREG急跌中有人逆勢買 seq1     8f62f2eeaed7a5c7    I1X1 I1X2 I2X1 I2X2      第 4 次
  margin PREREG融資大減型錯殺 seq1       0b1a55534c26d6bb    M1X1 M1X2                第 5 次
  （急跌錯殺 seq1 是第 1 次）

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchCrashExt run --case rev [--procs 4] [--reps 200] [--fake 200]
    ...                                                                     -m backtest.researchCrashExt page --case rev
    抽樣查核（獨立寫法）：... -m backtest.researchCrashExt_check --case rev

⭐ 補讀法寫死時間：TIME（台北，WSL TZ=Asia/Taipei date）；寫死前 ⛔ 沒算任何本四件的數字（只看過四件登錄全文、裁定 seq336、台股 1011-1019 請發號信、
   急跌錯殺 seq1 的程式／結果（它的結果台股與本線都看過 ⇒ 本來就是事後重切）、researchRevLimitUp 引擎骨架、資料格式與起點）。

═══ 補讀法（K 標；登錄沒寫清楚、執行者補的都在這裡）═══
 K1 sha：登錄全文去掉含「pw1 line」那一行後 sha256 前 16 碼 ＝ 該件 sha 才跑（信箱只讀）
 K2 急跌事件 ＝ researchCrashOversold.build_part（⛔ 不改、只 import）原樣重建：版面 researchRevLimitUp.World（~/rluwork 快取）、產業／壞根快取 ~/crashwork/ind_*.pkl、
    bad_*.pkl（唯讀）、tw-stock-data 釘在急跌錯殺 seq1 執行時的 283eec12b2（~/crashwork/tw_283eec12b2bc，唯讀；⛔ 不另建 archive，以免急跌錯殺的 check 找到兩份）。
    重建後逐筆對 resultsCrashOversold/events.csv.gz（版面、代號、t、公司事件、X1a／X2 出場位置與原因）⇒ 有任何不同就停（同一事件集的硬保證）。
    法人、融資 ＝ 同一 sha 的 data/stocks_inst、data/stocks_margin，git archive 到 ~/crashextwork/tw_283eec12b2bc（本件自己的工作夾）。
 K3 進場共用檢查（每件每格、對照 B 都同一套；依序判、第一個不過的理由照報）：
    ① e ≥ 資料尾 ⇒ 不進 ② (t, e] 有壞根 ⇒ 不進 ③ 公司事件：重大訊息主旨含登錄 18 關鍵字、事件交易日（13:30 規則，同急跌錯殺 K6）落在 [t−10, e−1] ⇒ 不買
    ④ 已修復：C(e−1)（還原收盤、ffill）≥ C(t−10) ⇒ 不買 ⑤ e 沒有有效開盤 ⇒ 不進；e 要落在段內（探索／確認／主窗以 e 切）
    e ＝ t+1 時 ①～⑤ 與急跌錯殺 seq1 的對照① 完全相同（③ 的窗就是 [t−10, t]）
 K4 出場（seq308 §四：條件出場、⛔ 不設最長天數）：
    X1：修復 ＝ e 起（含 e 收盤）第一根有 K 棒且還原收盤 ≥ C(t−10)；轉壞 ＝ 可用日 ≥ e 的各期月營收依序第一期年增 ≤ 0（缺值不觸發；
        「之後新公布」＝ 進場當天或之後才可用的期別）；取較早者（同日修復優先）⇒ 次一交易日起第一個有效開盤賣
    X2：e 起持有期最高收盤 × 0.8 ≥ 當日收盤 ⇒ 次一交易日起第一個有效開盤賣
    持有中遇壞根（e 之後第一個壞根早於或等於賣出那根）⇒ 壞根前最後一根有效 K 棒收盤強制賣；資料尾還沒出場 ⇒ 未完（窗尾持有照報）
    e ＝ t+1 時與急跌錯殺 seq1 的 X1a／X2 逐筆相同（run 時全部事件逐筆比對，不同就停）
 K5 對照 A ＝ 急跌錯殺 seq1 對照① 原樣：公司事件（[t−10, t]）排除後全部急跌事件、t+1 開盤買、它的 X1a／X2 欄；同引擎、種子 0～199
    ⇒ X2 版應逐位元重現急跌錯殺 summary 的「對照①急跌不看基本面」（run 時比對、照報）；X1 版是它沒跑過的同口徑
 K6 對照 B 延後假訊號（每格各自）：底 ＝ 該版面全部急跌事件（同檔 20 日去重後，含急跌錯殺當時被公司事件剔掉的，照 K3 用自己的窗重判）；
    每抽 r：依事件順序每筆抽 d（等機率抽自該格「主窗內實際進場」的等待天數 e − (t+1)，含重複）⇒ e_B ＝ t+1+d，照 K3 檢查、K4 出場；
    default_rng([20261011, 件號, 格號, r])；200 抽；引擎抽籤種子 ＝ r；p ＝ 假訊號年化 ≥ 該格年化中位 的比例
    等待天數全是 0（I1、M1：t+1 就買）⇒ B 與 A 同一批列、同種子 ⇒ 不另跑，照報「B ＝ A」
 K7 「條件有用」＝ 挑中格確認段年化中位 ＞ 對照 A（同出場）年化中位 且 ＞ 對照 B 年化中位（200 抽的中位）；挑中格早年可判時早年段也要兩者都贏；
    比值（年化 ÷ |回落|）並列不判
 K8 營收證實：可用日 ＝ research34.rebalance_dates（≤ 2025-12 期次月 10 日後第一個交易日、≥ 2026-01 期 15 日後；同急跌錯殺 K7）；
    tr ＝ 第一個可用日 ＞ t 的期別 M 的可用日；tr − t ＞ 30 個交易日 ⇒ 不買；e ＝ tr（開盤買）
    V1 ＝ 當月營收(M) ＞ max(M−12～M−1)，13 期都要有值（否則不明 ⇒ 不買），比較用嚴格 ＞（正式程式比較號）
    V2 ＝ 年增(M) ≤ 0 ⇒ 不成立；年增(M)、年增(M−1) 都有值 ⇒ 年增(M) ＞ 0 且 年增(M) − 年增(M−1) ≥ 0；其餘不明
    年增 ＝ 當月營收 ÷ 去年當月營收 − 1（去年 ＞ 0；同急跌錯殺 F1 的算法）
    D（描述）＝ 當月營收(M) ＜ min(M−12～M−1)（13 期有值）或 年增(M) ≤ 0（「年增轉負」取 ≤ 0，與 X1 轉壞同口徑）；同 tr 進、同出場
    早年：急跌錯殺 seq1 的月營收覆蓋規則判定窗從 2005 起 ⇒ 早年 2005-01-03～2014-12-30 全段
 K9 止跌：位置都是日曆交易日、還原收盤（ffill）
    S1 ＝ k ∈ [t+1, t+20] 中第一個「k 有 K 棒且 C(k) ＞ MA20(k)」（MA20 ＝ C(k−19..k) 平均）⇒ e ＝ k+1
    S2 ＝ k ∈ [t+5, t+20] 中第一個「k 有 K 棒且 min C(k−4..k) ≥ L_k」，L_k ＝ min C(t..k−5)（自 t 起到這 5 天之前的最低收盤）⇒ e ＝ k+1
    20 日內沒出現 ⇒ 不成立；t+20 超出資料尾且還沒出現 ⇒ 不明；早年只用價量 ⇒ 2005-01-03～2014-12-30 全段可判
 K10 逆勢買：I1 ＝ t−9～t 十天 foreign＋trust 合計 ＞ 0（data/stocks_inst 原始單位是股，只看正負，張或股不影響）；某天沒列 ⇒ 當 0；十天都沒列 ⇒ 不明；
     e ＝ t+1；D（描述）＝ 合計 ＜ 0；資料起點 2015-01-05 ⇒ 早年不可判定
     I2 ＝ 重大訊息主旨含「董事會決議買回庫藏股」或「決議買回本公司股份」且不含「轉讓」「註銷」「執行情形」「期間屆滿」；事件交易日 ep（13:30 規則：
     交易日 ≤ 13:30 ⇒ 當天，否則次一交易日）落在 [t−9, t+20] 的第一則 ⇒ e ＝ max(ep+1, t+1)（照字面「13:30 後算隔天、公告後第一個交易日開盤買」；
     公告早於急跌成立時，最早只能 t+1 買，因為 t 收盤前不知道是急跌）；早年用同一份重大訊息 ⇒ 2005-01-03～2014-12-30 全段可判
 K11 融資大減：MB ＝ data/stocks_margin m_balance（張）；V20 ＝ 含 t−10 的最近 20 根有效 K 棒成交量平均（股 ÷ 1000 ＝ 張）；
     融資比重 ＝ MB(t−10) ÷ V20(t−10)；當日母體 ＝ 急跌錯殺的 R1（t 當天）裡比重算得出的；比重 ≥ 當日中位 才看
     降幅 ＝ (MB(t−10) − MB(t)) ÷ MB(t−10)（MB(t−10) ＞ 0 且 MB(t) 有值）；當日母體（R1 且降幅算得出）降幅由大到小前 ⌈10% × 檔數⌉（同值依股票序）
     M1 ＝ 比重 ≥ 中位 且 降幅在前 10%；比重或降幅算不出（含不能融資、沒有融資檔）⇒ 不明 ⇒ 不買；e ＝ t+1
     D（描述）＝ 可判定且 M1 不成立；stocks_margin 起點 2015-01-05 ⇒ 早年不可判定（只判探索、確認）
 K12 組合層：researchRevLimitUp.finalize_rows／run_arms（research11.simulate_mtm rule "F"、10 槽等權、抽籤 200 顆、空位才買、已持有不重買、停止交易強制出場）；
     現實版 ＝ researchSlip（同急跌錯殺 K12）200 顆；⭐ 先寫 degeneracy.json（附台北時戳）再彙總任何報酬；退化 ＝ 平均持股 ＜ 3 或平均現金 ＞ 30%（段內逐日、種子中位）
     ⇒ 照登錄排除；挑格、判定、標籤上限同急跌錯殺 K10（探索段非退化合格者比值最大，沒有合格取比值最大；判定 ＝ 確認與早年兩段取較嚴，早年不可判定只看確認；
     合格 ⇒「暫定」：同批事件事後重切）
 K13 描述（⛔ 不判、不計 N）：D（各件反面）50 顆；固定持有 {20, 60, 120} 根（挑中格同進場）50 顆；0050 在 200 日線上才買（e−1）50 顆——「擋長空頭、不是急跌保護」
 K14 必報：等效獨立檔數（急跌錯殺 neff_ind，換股日 N ÷ (1＋(N−1)ρ)）、最大產業、現金比例、候選不足月份、每年急跌事件數與本件成立數（兩版面）、
     等待天數（e − t）分佈、持有天數分佈、X1 修復／轉壞／X2 各幾次、窗尾仍持有、一年內先跌 15%、營量 v1／營飆 v1 持股重疊率
 K15 結果句必附：「同批急跌事件第 n 次切分」＋各件登錄的必附句
輸出 backtest/resultsCrashExt/<件名>/：degeneracy.json（先寫）、summary.json、grid.csv、entries.csv.gz、exits.csv.gz、seeds.csv.gz、run.log、check.json、<件名>.html；
大檔 ~/crashextwork/
── 事後註（寫死之後、照實記；補讀法沒改）──
 ① 10:41～10:44 跑過四件冒煙測試（--smoke --reps 2 --fake 2，輸出 ~/crashextwork/smoke，數字不是本件結果）；之後只改程式防呆（空臂不送引擎）與 --smoke 選項；讀法未改
 ② 正式 run 10:45～11:08（四件同一個程序依序）；之後才加 `exits` 子命令（只把主程式 exits_x 對每筆可進場列的出場寫成 exits.csv.gz 給 --check，不跑引擎、不動結果）
    與網頁的先驗排版；run_case 未改
 ③ --check 第一次 margin 有 1 萬多筆「不同」，全是查核程式自己的錯（entries.csv.gz 以 8 位有效數字存，查核用 1e-9 比；M1 拿截斷後的門檻比）；
    改成相對 1e-7、M1 改由查核程式自建每日 R1 重算後重跑 ⇒ 0；主程式未改
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import html
import json
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import research11 as R                        # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402
from backtest import research34 as R34                      # noqa: E402
from backtest import universe_gate as UG                    # noqa: E402
from backtest import researchRevLimitUp as RLU              # noqa: E402
from backtest import researchCrashOversold as CO            # noqa: E402

UG.set_gate_v2(True)

TIME = "2026-10-11 10:40（台北）"
MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
HERE = os.path.expanduser("~/tw-p17/backtest")
OUTROOT = os.path.join(HERE, "resultsCrashExt")
WORK = os.path.expanduser("~/crashextwork")
CO_SHA = "283eec12b2bc0eb17ffa756c5a0efe3a49d16d92"
CO_DATA = os.path.expanduser("~/crashwork/tw_283eec12b2bc/data")
EXT_DATA = os.path.join(WORK, "tw_283eec12b2bc", "data")
CO_OUT = os.path.join(HERE, "resultsCrashOversold")
SEGS = CO.SEGS
EARLY = CO.EARLY
K10 = CO.K10
FSEED = 20261011
BUY_IN = ["董事會決議買回庫藏股", "決議買回本公司股份"]
BUY_EX = ["轉讓", "註銷", "執行情形", "期間屆滿"]
COMMON_SENT = "錯殺要事後才能確認；本件測的是『這樣挑，平均起來』，⛔ 不代表某一檔是錯殺"
CASES = {
    "rev": {"no": 1, "name": "急跌後等營收證實", "reg": "PREREG急跌後等營收證實 seq1", "sha": "c552173c9ab53868", "types": ["V1", "V2"], "desc": "Dv",
            "early": ["V1", "V2"], "nth": 2,
            "title": "急跌後等營收證實：急跌後不馬上買，等下一期月營收創新高或沒變慢才買",
            "tn": {"V1": "下一期營收創 12 個月新高", "V2": "下一期營收年增為正且沒變慢", "Dv": "下一期營收創新低或年增 ≤ 0（反面，描述）"},
            "sent": [COMMON_SENT]},
    "stop": {"no": 2, "name": "急跌後等止跌", "reg": "PREREG急跌後等止跌 seq1", "sha": "93fe0f2cab25fd68", "types": ["S1", "S2"], "desc": None,
             "early": ["S1", "S2"], "nth": 3,
             "title": "急跌後等止跌：等收盤站回 20 日線、或連 5 天不再破低才買",
             "tn": {"S1": "站回 20 日線", "S2": "連 5 天不再破低"},
             "sent": [COMMON_SENT, "描述臂『t 後第 5 日才買』本線已看過，本件與它的差別只在用條件決定等多久"]},
    "inst": {"no": 3, "name": "急跌中有人逆勢買", "reg": "PREREG急跌中有人逆勢買 seq1", "sha": "8f62f2eeaed7a5c7", "types": ["I1", "I2"], "desc": "Di",
             "early": ["I2"], "nth": 4,
             "title": "急跌中有人逆勢買：急跌期間投信外資買超，或急跌後公司宣布買庫藏股才買",
             "tn": {"I1": "急跌十天投信＋外資買超", "I2": "公司宣布買回庫藏股", "Di": "急跌十天投信＋外資賣超（反面，描述）"},
             "sent": [COMMON_SENT, "法人買超與庫藏股都是公開資訊，⛔ 不代表內部人知道什麼"]},
    "margin": {"no": 4, "name": "融資大減型錯殺", "reg": "PREREG融資大減型錯殺 seq1", "sha": "0b1a55534c26d6bb", "types": ["M1"], "desc": "Dm",
               "early": [], "nth": 5,
               "title": "融資大減型錯殺：急跌期間融資大減的股票，隔天買",
               "tn": {"M1": "急跌十天融資大減", "Dm": "融資沒有大減（反面，描述）"},
               "sent": [COMMON_SENT, "融資大減是被迫賣出的代理，⛔ 不等於斷頭"]},
}
XN = {"X1": "修復或轉壞才賣", "X2": "從最高回落 20% 才賣"}
_G: dict = {}


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


def cells_of(ck):
    return [f"{t}{x}" for t in CASES[ck]["types"] for x in ("X1", "X2")]


def cname(ck, cell):
    return f"{cell}（{CASES[ck]['tn'][cell[:2]]}｜{XN[cell[2:]]}）"


def reg_check(sha):
    fs = [f for f in glob.glob(os.path.join(MAILBOX, "*.md")) if f"sha{sha}" in os.path.basename(f)]
    if len(fs) != 1:
        raise SystemExit(f"⛔ 信箱找不到唯一一封登錄全文 sha{sha}：{fs}")
    b = open(fs[0], "rb").read()
    h = hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]
    if h != sha:
        raise SystemExit(f"⛔ 登錄 sha {h} ≠ {sha}")
    return os.path.basename(fs[0])


def jdump(o, p):
    json.dump(o, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=lambda z: (None if (isinstance(z, float) and not np.isfinite(z)) else float(z)) if np.isscalar(z) and not isinstance(z, str) else str(z))


# ═════════════ 共用世界（急跌事件原樣重建）═════════════
def world(a, log):
    if "WM" in _G:
        return _G
    assert os.path.exists(os.path.join(CO_DATA, "..", "DONE")) and open(os.path.join(CO_DATA, "..", "DONE")).read().strip() == CO_SHA
    if not os.path.exists(os.path.join(EXT_DATA, "..", "DONE")):
        raise SystemExit("⛔ 缺 ~/crashextwork/tw_283eec12b2bc（stocks_inst／stocks_margin）")
    CO._G.update(sha=CO_SHA, DATA=CO_DATA)                    # 釘住，⛔ 不讓 CO.tw_data 另建 archive
    FD = CO.load_fund(log)
    WM = RLU.World("main", a.procs, log); WE = RLU.World("early", a.procs, log)
    seg = {k: WM.segpos(*v) for k, v in SEGS.items()}
    Z = {k: RR.bench_row(WM.cal, WM.bench, x, y + 1) for k, (x, y) in seg.items()}
    if not (repr(Z["主窗"]["cagr"]) == repr(CO.ANCHOR[0]) and repr(Z["主窗"]["mdd"]) == repr(CO.ANCHOR[1])):
        raise SystemExit("⛔ 0050 錨不對")
    INDM, invM = CO.ind_matrix(WM, FD, log)
    finM = np.isin(INDM, [k for k, v in invM.items() if v == "金融保險"])
    d16 = WM.pos(CO.R1_DAY)
    mk16 = WM.MKT[:, d16] & ~finM[:, d16]; X = int((mk16 & (WM.A20[:, d16] >= CO.LIQ)).sum()) / int(mk16.sum())
    rb = np.r_[CO.bench_r10(WE), CO.bench_r10(WM)]
    flag = np.full(len(rb), np.nan); hist = []
    for k in range(len(rb)):
        if np.isfinite(rb[k]):
            hist.append(rb[k])
            if len(hist) >= 120:
                flag[k] = float(rb[k] <= np.quantile(np.asarray(hist), 0.05))
    ns = argparse.Namespace(procs=a.procs, smoke=False)
    PM = CO.build_part(WM, FD, X, flag[WE.n:], ns, log, early=False)
    PE = CO.build_part(WE, FD, X, flag[:WE.n], ns, log, early=True)
    for P in (PM, PE):
        P["cb"] = np.cumsum(P["BAD"], axis=1, dtype=np.int32)
    _G.update(FD=FD, WM=WM, WE=WE, seg=seg, Z=Z, X=X, PM=PM, PE=PE)
    _G["av"] = {"main": avail(WM.cal, FD), "early": avail(WE.cal, FD)}
    _G["NP"] = {"main": news_pos(WM, FD["NW"]), "early": news_pos(WE, FD["NW"])}
    verify_events(log)
    return _G


def verify_events(log):
    """K2：重建的事件與急跌錯殺 events.csv.gz 逐筆相同；K4：e＝t+1 的出場逐筆相同。"""
    EO = pd.read_csv(os.path.join(CO_OUT, "events.csv.gz"), dtype={"sid": str}, low_memory=False)
    diff = {}
    for part, P, W in (("main", _G["PM"], _G["WM"]), ("早年", _G["PE"], _G["WE"])):
        E = P["E"]; O = EO[EO["版面"] == part].reset_index(drop=True)
        same_n = len(E) == len(O)
        d = 0 if same_n else abs(len(E) - len(O)) + 1
        if same_n:
            for c in ("sid", "日期t", "公司事件", "X1a_x", "X1a_why", "X2_x", "X2_why"):
                a_ = E[c].astype(str).to_numpy(); b_ = O[c].astype(str).to_numpy()
                if c == "公司事件":
                    a_ = E[c].astype(bool).astype(str).to_numpy(); b_ = O[c].astype(bool).astype(str).to_numpy()
                d += int((a_ != b_).sum())
        # 自己的出場函式在 e＝t+1 重現 CO 的 X1a／X2
        pk = "main" if part == "main" else "early"
        dx = 0
        for i, (s, t, sid) in enumerate(zip(E["s"], E["t"], E["sid"])):
            if E["X2_xk"].iloc[i] == "none":
                continue
            r = exits_x(pk, int(s), int(t), int(t) + 1, sid)
            for x, cx in (("X1", "X1a"), ("X2", "X2")):
                if (r[x][0], int(r[x][1]), r[x][2]) != (E[f"{cx}_xk"].iloc[i], int(E[f"{cx}_x"].iloc[i]), E[f"{cx}_why"].iloc[i]):
                    dx += 1
        diff[part] = {"事件筆數": int(len(E)), "急跌錯殺 events 筆數": int(len(O)), "事件欄不同": int(d), "出場函式（e＝t+1）對 X1a／X2 不同": int(dx)}
    _G["verify"] = diff
    log(f"[同一事件集] {diff}")
    if any(v["事件欄不同"] or v["出場函式（e＝t+1）對 X1a／X2 不同"] for v in diff.values()):
        raise SystemExit("⛔ 事件集或出場與急跌錯殺 seq1 不同")


def avail(cal, FD):
    periods = FD["periods"]
    rd = {**R34.rebalance_dates([M for M in periods if M <= "2025-12"], cal, 10), **R34.rebalance_dates([M for M in periods if M >= "2026-01"], cal, 15)}
    pidx = {M: k for k, M in enumerate(periods)}
    avl = sorted((e_, pidx[M]) for M, (_, e_) in rd.items())
    return np.array([x[0] for x in avl], int), np.array([x[1] for x in avl], int)


def ev_pos(W, df):
    cal = W.cal; calv = cal.values; n = W.n
    dd = pd.to_datetime(df["date"]).values
    p0 = np.searchsorted(calv, dd, side="left")
    istd = (p0 < n) & (calv[np.minimum(p0, n - 1)] == dd)
    late = df["time"].str.slice(0, 5).to_numpy() > "13:30"
    return np.where(istd & ~late, p0, np.where(istd, p0 + 1, p0))


def news_pos(W, NW):
    ep = ev_pos(W, NW); NP = {}
    for s, p in zip(NW["stock_id"], ep):
        if p < W.n:
            NP.setdefault(s, []).append(int(p))
    return {k: np.array(sorted(v), int) for k, v in NP.items()}


def P_(part):
    return (_G["WM"], _G["PM"]) if part == "main" else (_G["WE"], _G["PE"])


def hyg(part, s, t, e, sid):
    """K3：''＝可進；否則理由。"""
    W, P = P_(part)
    if e >= W.n:
        return "超出資料尾"
    if (P["cb"][s, e] - P["cb"][s, t]) > 0:
        return "(t,e] 有壞根"
    z = _G["NP"][part].get(sid)
    if z is not None and len(z):
        k = int(np.searchsorted(z, t - K10, side="left"))
        if k < len(z) and z[k] <= e - 1:
            return "公司事件"
    if W.C[s, e - 1] >= W.C[s, t - K10] * (1 - 1e-12):
        return "進場前已修復"
    if not np.isfinite(W.O[s, e]):
        return "e 無有效開盤"
    return ""


def exits_x(part, s, t, e, sid):
    """K4 ⇒ {'X1': (xk, x, why), 'X2': ...}（快取）。"""
    key = (part, s, t, e)
    C_ = _G.setdefault("EXC", {})
    if key in C_:
        return C_[key]
    W, P = P_(part); FD = _G["FD"]; BAD = P["BAD"]
    avP, avK = _G["av"][part]
    n = W.n; c = W.C[s]; bar = W.BAR[s]
    ref = c[t - K10]
    seg = c[e:]; bs = bar[e:]
    w = np.flatnonzero(bs & (seg >= ref * (1 - 1e-12)))
    rep = e + int(w[0]) if len(w) else None
    bad_r = None
    j = FD["col"].get(sid, -1)
    if j >= 0:
        m = avP >= e
        for p, k in zip(avP[m], avK[m]):
            y = FD["YOY"][k, j]
            if np.isfinite(y) and y <= 0:
                bad_r = int(p); break
    rm = np.maximum.accumulate(seg)
    w2 = np.flatnonzero(seg <= rm * (1 - CO.E2_DD) + 1e-12)
    bb = np.flatnonzero(BAD[s, e + 1:]); kb = e + 1 + int(bb[0]) if len(bb) else None
    okb = W.okb[s]
    out = {}
    for x in ("X1", "X2"):
        if x == "X1":
            cand = [(z, nm) for z, nm in ((rep, "修復"), (bad_r, "轉壞（營收）")) if z is not None]
            tg = min(cand, key=lambda z: z[0]) if cand else (None, None)
        else:
            tg = (e + int(w2[0]), "回落20%") if len(w2) else (None, None)
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
    C_[key] = out
    return out


# ═════════════ 各件的進場 ═════════════
def ent_rev(part, E):
    FD = _G["FD"]; avP, avK = _G["av"][part]; REV = FD["rev"].to_numpy(float); YOY = FD["YOY"]; col = FD["col"]; periods = FD["periods"]
    rows = []
    for s, t, sid in zip(E["s"], E["t"], E["sid"]):
        z = {"tr": -1, "M": "", "rev": np.nan, "max12": np.nan, "min12": np.nan, "yoy": np.nan, "yoy_prev": np.nan}
        kk = int(np.searchsorted(avP, t, side="right"))
        if kk >= len(avP):
            for ty in ("V1", "V2", "Dv"):
                z[f"{ty}_cond"] = np.nan; z[f"{ty}_e"] = -1; z[f"{ty}_why"] = "沒有下一期可用日"
            rows.append(z); continue
        tr = int(avP[kk]); km = int(avK[kk]); j = col.get(sid, -1)
        z.update(tr=tr, M=periods[km])
        v1 = v2 = dv = np.nan
        if j >= 0:
            v = REV[km, j]; pr = REV[km - 12:km, j] if km >= 12 else np.array([])
            y = YOY[km, j]; yp = YOY[km - 1, j] if km >= 1 else np.nan
            full = len(pr) == 12 and np.isfinite(pr).all() and np.isfinite(v)
            z.update(rev=v, yoy=y, yoy_prev=yp, max12=float(pr.max()) if full else np.nan, min12=float(pr.min()) if full else np.nan)
            if full:
                v1 = float(v > pr.max())
            if np.isfinite(y) and y <= 0:
                v2 = 0.0
            elif np.isfinite(y) and np.isfinite(yp):
                v2 = float(y > 0 and (y - yp) >= 0)
            lo = full and v < pr.min(); ng = np.isfinite(y) and y <= 0
            if lo or ng:
                dv = 1.0
            elif full and np.isfinite(y):
                dv = 0.0
        far = tr - t > 30
        for ty, cv in (("V1", v1), ("V2", v2), ("Dv", dv)):
            z[f"{ty}_cond"] = cv
            z[f"{ty}_e"] = tr if (cv == 1.0 and not far) else -1
            z[f"{ty}_why"] = "tr 距 t ＞ 30 日" if (cv == 1.0 and far) else ("" if cv == 1.0 else ("條件不成立" if cv == 0.0 else "不明"))
        rows.append(z)
    return pd.DataFrame(rows)


def ent_stop(part, E):
    W, P = P_(part); n = W.n
    rows = []
    for s, t in zip(E["s"], E["t"]):
        c = W.C[s]; bar = W.BAR[s]; z = {}
        k1 = None
        for k in range(t + 1, min(t + 20, n - 1) + 1):
            if bar[k] and c[k] > c[k - 19:k + 1].mean():
                k1 = k; break
        k2 = None; L2 = np.nan
        for k in range(t + 5, min(t + 20, n - 1) + 1):
            L = c[t:k - 4].min()
            if bar[k] and c[k - 4:k + 1].min() >= L:
                k2 = k; L2 = float(L); break
        trunc = t + 20 > n - 1
        for ty, k in (("S1", k1), ("S2", k2)):
            if k is not None:
                z[f"{ty}_cond"] = 1.0; z[f"{ty}_e"] = k + 1; z[f"{ty}_why"] = ""
            else:
                z[f"{ty}_cond"] = np.nan if trunc else 0.0; z[f"{ty}_e"] = -1; z[f"{ty}_why"] = "不明" if trunc else "條件不成立"
        z["S1_k"] = k1 if k1 is not None else -1; z["S2_k"] = k2 if k2 is not None else -1; z["S2_L"] = L2
        rows.append(z)
    return pd.DataFrame(rows)


def inst_mat(W, log):
    cp = os.path.join(WORK, f"inst_{W.part}.pkl")
    if os.path.exists(cp):
        return pickle.load(open(cp, "rb"))
    IN = np.full((W.S, W.n), np.nan); nf = 0
    for i, sid in enumerate(W.sids):
        p = os.path.join(EXT_DATA, "stocks_inst", f"{sid}.csv")
        if not os.path.exists(p):
            continue
        nf += 1
        df = pd.read_csv(p, dtype={"date": str, "stock_id": str}, usecols=["date", "foreign", "trust"]).drop_duplicates("date", keep="last")
        pos = W.cal.get_indexer(pd.to_datetime(df["date"])); ok = pos >= 0
        v = (pd.to_numeric(df["foreign"], errors="coerce").fillna(0) + pd.to_numeric(df["trust"], errors="coerce").fillna(0)).to_numpy(float)
        IN[i, pos[ok]] = v[ok]
    pickle.dump((IN, nf), open(cp, "wb"), protocol=5)
    log(f"[法人 {W.part}] 有檔 {nf}／{W.S}")
    return IN, nf


def buyback(log):
    if "BB" in _G:
        return _G["BB"]
    fs = [f for f in sorted(glob.glob(os.path.join(CO_DATA, "mops", "news", "*.csv"))) if os.path.basename(f)[:4].isdigit() and int(os.path.basename(f)[:4]) >= 2004]
    N = pd.concat([pd.read_csv(f, dtype=str, keep_default_na=False, usecols=["date", "time", "stock_id", "serial", "subject"]) for f in fs], ignore_index=True)
    N["stock_id"] = N["stock_id"].str.strip()
    N = N.drop_duplicates(["date", "time", "stock_id", "serial"])
    hit = N["subject"].str.contains("|".join(BUY_IN), regex=True) & ~N["subject"].str.contains("|".join(BUY_EX), regex=True)
    BB = N[hit].reset_index(drop=True)
    info = {"則數（去鍵重複後）": int(len(N)), "庫藏股買回命中": int(len(BB)), "年": [BB["date"].min(), BB["date"].max()]}
    log(f"[庫藏股] {info}")
    _G["BB"] = (BB, info)
    return _G["BB"]


def ent_inst(part, E, log):
    W, P = P_(part); n = W.n
    BB, _ = buyback(log)
    ep = ev_pos(W, BB); BP = {}
    for s, p, d, tm, sub in zip(BB["stock_id"], ep, BB["date"], BB["time"], BB["subject"]):
        if p < n:
            BP.setdefault(s, []).append((int(p), d, tm, sub))
    for k in BP:
        BP[k].sort()
    IN = inst_mat(W, log)[0] if part == "main" else None
    rows = []
    for s, t, sid in zip(E["s"], E["t"], E["sid"]):
        z = {}
        if IN is not None:
            v = IN[s, t - 9:t + 1]; nv = int(np.isfinite(v).sum()); sm = float(np.nansum(v)) if nv else np.nan
        else:
            nv, sm = 0, np.nan
        z.update(inst10=sm, inst_rows=nv)
        i1 = np.nan if not np.isfinite(sm) else float(sm > 0)
        di = np.nan if not np.isfinite(sm) else float(sm < 0)
        for ty, cv in (("I1", i1), ("Di", di)):
            z[f"{ty}_cond"] = cv; z[f"{ty}_e"] = t + 1 if cv == 1.0 else -1
            z[f"{ty}_why"] = "" if cv == 1.0 else ("條件不成立" if cv == 0.0 else ("不可判定（法人資料 2015 起）" if part == "early" else "不明"))
        hit = [x for x in BP.get(sid, []) if t - 9 <= x[0] <= t + 20]
        trunc = t + 20 > n - 1
        if hit:
            p, d, tm, sub = hit[0]
            z.update(I2_cond=1.0, I2_e=max(p + 1, t + 1), I2_why="", I2_ep=p, I2_date=f"{d} {tm}", I2_subject=sub[:60])
        else:
            z.update(I2_cond=np.nan if trunc else 0.0, I2_e=-1, I2_why="不明" if trunc else "條件不成立", I2_ep=-1, I2_date="", I2_subject="")
        rows.append(z)
    return pd.DataFrame(rows)


def margin_mat(W, log):
    cp = os.path.join(WORK, f"margin_{W.part}.pkl")
    if os.path.exists(cp):
        return pickle.load(open(cp, "rb"))
    MB = np.full((W.S, W.n), np.nan); V20 = np.full((W.S, W.n), np.nan); nf = 0
    for i, sid in enumerate(W.sids):
        p = os.path.join(EXT_DATA, "stocks_margin", f"{sid}.csv")
        if os.path.exists(p):
            nf += 1
            df = pd.read_csv(p, dtype={"date": str, "stock_id": str}, usecols=["date", "m_balance"]).drop_duplicates("date", keep="last")
            pos = W.cal.get_indexer(pd.to_datetime(df["date"])); ok = pos >= 0
            MB[i, pos[ok]] = pd.to_numeric(df["m_balance"], errors="coerce").to_numpy(float)[ok]
        q = os.path.join(W.data, "stocks", f"{sid}.csv")
        if os.path.exists(q):
            dv = pd.read_csv(q, dtype={"date": str}, usecols=["date", "volume"]).drop_duplicates("date")
            pos = W.cal.get_indexer(pd.to_datetime(dv["date"])); ok = pos >= 0
            v = np.full(W.n, np.nan); v[pos[ok]] = pd.to_numeric(dv["volume"], errors="coerce").to_numpy(float)[ok] / 1000.0
            bars = np.flatnonzero(W.BAR[i] & np.isfinite(v))
            if len(bars):
                V20[i, bars] = pd.Series(v[bars]).rolling(20, min_periods=20).mean().to_numpy()
    pickle.dump((MB, V20, nf), open(cp, "wb"), protocol=5)
    log(f"[融資 {W.part}] 有檔 {nf}／{W.S}")
    return MB, V20, nf


def ent_margin(part, E, log):
    W, P = P_(part)
    rows = []
    if part == "early":
        for _ in range(len(E)):
            rows.append({"M1_cond": np.nan, "M1_e": -1, "M1_why": "不可判定（stocks_margin 2015 起）", "Dm_cond": np.nan, "Dm_e": -1, "Dm_why": "不可判定（stocks_margin 2015 起）"})
        return pd.DataFrame(rows)
    MB, V20, _ = margin_mat(W, log)
    R1 = P["R1"]; day = {}
    for s, t in zip(E["s"], E["t"]):
        if t not in day:
            U = np.flatnonzero(R1[:, t])
            with np.errstate(invalid="ignore", divide="ignore"):
                ra = MB[U, t - K10] / V20[U, t - K10]
                ra = np.where(np.isfinite(V20[U, t - K10]) & (V20[U, t - K10] > 0), ra, np.nan)
                dc = np.where((MB[U, t - K10] > 0) & np.isfinite(MB[U, t]), (MB[U, t - K10] - MB[U, t]) / MB[U, t - K10], np.nan)
            okr = np.isfinite(ra); med = float(np.median(ra[okr])) if okr.any() else np.nan
            okd = np.flatnonzero(np.isfinite(dc))
            k = int(np.ceil(0.10 * len(okd)))
            top = set(U[okd[np.argsort(-dc[okd], kind="stable")[:k]]].tolist()) if k else set()
            thr = float(np.sort(dc[okd])[::-1][k - 1]) if k else np.nan
            day[t] = (med, top, thr, int(okr.sum()), int(len(okd)), k)
        med, top, thr, nr, nd, k = day[t]
        with np.errstate(invalid="ignore", divide="ignore"):
            ra = MB[s, t - K10] / V20[s, t - K10] if (np.isfinite(V20[s, t - K10]) and V20[s, t - K10] > 0) else np.nan
            dc = (MB[s, t - K10] - MB[s, t]) / MB[s, t - K10] if (MB[s, t - K10] > 0 and np.isfinite(MB[s, t])) else np.nan
        z = {"mb_t10": MB[s, t - K10], "mb_t": MB[s, t], "v20_t10": V20[s, t - K10], "比重": ra, "比重中位": med, "降幅": dc, "降幅前10%門檻": thr,
             "比重母體": nr, "降幅母體": nd, "前10%檔數": k}
        if np.isfinite(ra) and np.isfinite(dc) and np.isfinite(med):
            m1 = float(ra >= med and s in top)
        else:
            m1 = np.nan
        dm = np.nan if not np.isfinite(m1) else 1.0 - m1
        for ty, cv in (("M1", m1), ("Dm", dm)):
            z[f"{ty}_cond"] = cv; z[f"{ty}_e"] = t + 1 if cv == 1.0 else -1
            z[f"{ty}_why"] = "" if cv == 1.0 else ("條件不成立" if cv == 0.0 else "不明（比重或降幅算不出）")
        rows.append(z)
    return pd.DataFrame(rows)


def entries(ck, part, log):
    W, P = P_(part); E = P["E"]
    f = {"rev": lambda: ent_rev(part, E), "stop": lambda: ent_stop(part, E), "inst": lambda: ent_inst(part, E, log), "margin": lambda: ent_margin(part, E, log)}[ck]
    X = f()
    base = E[["s", "t", "sid", "日期t", "公司事件", "大盤也急跌", "市場", "產業", "r10", "ex"]].reset_index(drop=True)
    X = pd.concat([base, X.reset_index(drop=True)], axis=1)
    tys = CASES[ck]["types"] + ([CASES[ck]["desc"]] if CASES[ck]["desc"] else [])
    for ty in tys:
        hy = []
        for s, t, e, sid in zip(X["s"], X["t"], X[f"{ty}_e"], X["sid"]):
            hy.append(hyg(part, int(s), int(t), int(e), sid) if e >= 0 else "—")
        X[f"{ty}_hyg"] = hy
        X[f"{ty}_ok"] = X[f"{ty}_hyg"] == ""
    X["版面"] = part
    return X


def cell_rows(part, X, ty, x, a, b):
    G = X[X[f"{ty}_ok"] & (X[f"{ty}_e"] >= a) & (X[f"{ty}_e"] <= b)]
    rows = []
    for s, t, e, sid in zip(G["s"], G["t"], G[f"{ty}_e"], G["sid"]):
        xk, xx, why = exits_x(part, int(s), int(t), int(e), sid)[x]
        rows.append((int(s), int(e), xk, int(xx), why, np.nan))
    return pd.DataFrame(rows, columns=["s", "e", "xk", "x", "why", "key"])


def waits_of(X, ty, a, b):
    G = X[X[f"{ty}_ok"] & (X[f"{ty}_e"] >= a) & (X[f"{ty}_e"] <= b)]
    return (G[f"{ty}_e"] - G["t"] - 1).to_numpy(int)


def delay_rows(part, ck, ci, x, waits, r, a, b):
    """K6：同一批急跌事件隨機延後 d 天。"""
    W, P = P_(part); E = P["E"]
    rng = np.random.default_rng([FSEED, CASES[ck]["no"], ci, r])
    d = waits[rng.integers(0, len(waits), size=len(E))]
    rows = []
    for (s, t, sid), dd in zip(zip(E["s"].to_numpy(int), E["t"].to_numpy(int), E["sid"]), d):
        e = int(t + 1 + dd)
        if e < a or e > b:
            continue
        if hyg(part, s, t, e, sid):
            continue
        xk, xx, why = exits_x(part, s, t, e, sid)[x]
        rows.append((s, e, xk, int(xx), why, np.nan))
    return pd.DataFrame(rows, columns=["s", "e", "xk", "x", "why", "key"])


def a_rows(part, x, a, b):
    """K5：急跌錯殺 seq1 對照①（原樣）。"""
    W, P = P_(part); E = P["E"]
    S = E[(E["e"] >= a) & (E["e"] <= b) & (~E["公司事件"])]
    return CO.rows_for(S, "F1X1" if x == "X1" else "F1X2")


def fake_summary(FK, cellsum, Z, segs):
    out = {}
    for sg in segs:
        v = np.array([q[f"{sg}_年化"] for q in FK]); d_ = np.array([q[f"{sg}_回落"] for q in FK])
        out[sg] = {"抽數": len(v), "年化中位": float(np.nanmedian(v)), "年化p10": float(np.nanpercentile(v, 10)), "年化p90": float(np.nanpercentile(v, 90)),
                   "回落中位": float(np.nanmedian(d_)), "p（假訊號年化 ≥ 該格）": float(np.mean(v >= cellsum[f"{sg}_年化"])),
                   "假訊號合格比例": float(np.mean([RLU.label(c_, m_, Z[sg])[0] == "合格" for c_, m_ in zip(v, d_)]))}
    return out


# ═════════════ 主流程（一件）═════════════
def run_case(ck, a):
    C = CASES[ck]; OUT = os.path.join(OUTROOT, C["name"]); os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    log = CO.log_to(os.path.join(OUT, "run.log"))
    log(f"===== researchCrashExt run {ck}（{C['reg']}）{now_tpe()}（台北）｜補讀法寫死 {TIME}｜reps {a.reps} fake {a.fake} =====")
    regf = reg_check(C["sha"]); log(f"[sha] {C['sha']} ✔ {regf}")
    t00 = time.time()
    G = world(a, log)
    FD, WM, WE, seg, Z, PM, PE = G["FD"], G["WM"], G["WE"], G["seg"], G["Z"], G["PM"], G["PE"]
    w0, w1 = seg["主窗"]
    CELLS = cells_of(ck)
    XM = entries(ck, "main", log)
    XE = entries(ck, "early", log)
    ENT = pd.concat([XE, XM], ignore_index=True)
    ENT.to_csv(os.path.join(OUT, "entries.csv.gz"), index=False, float_format="%.8g")
    tys = C["types"] + ([C["desc"]] if C["desc"] else [])
    for part, X_ in (("main", XM), ("早年", XE)):
        log(f"[進場 {part}] 事件 {len(X_)}｜" + "；".join(f"{ty} 成立 {int((X_[f'{ty}_cond'] == 1).sum())}、不成立 {int((X_[f'{ty}_cond'] == 0).sum())}、"
                                                     f"不明 {int(X_[f'{ty}_cond'].isna().sum())}、可進 {int(X_[f'{ty}_ok'].sum())}｜檢查剔 "
                                                     f"{X_.loc[X_[f'{ty}_e'] >= 0, f'{ty}_hyg'].value_counts().to_dict()}" for ty in tys))
    # ── 格（main）──
    FB, FR, WT = {}, {}, {}
    for c in CELLS:
        rw = cell_rows("main", XM, c[:2], c[2:], w0, w1)
        FB[c] = RLU.finalize_rows(WM, rw, False); FR[c] = RLU.finalize_rows(WM, rw, True)
        WT[c] = waits_of(XM, c[:2], w0, w1)
        log(f"[訊號 {c}] 可進 {len(FB[c])}（列 {len(rw)}）、未完 {int(FB[c]['end'].sum())}｜{FB[c]['why'].value_counts().to_dict()}")
    arms = []
    for c in CELLS:
        arms += [(f"{c}|b", FB[c], False, a.reps), (f"{c}|r", FR[c], True, a.reps)]
    RES = RLU.run_arms(WM, arms, seg, w1, a.procs, log)
    DG = {}
    for k, ms in RES.items():
        h = RLU.hold_only(ms, seg)
        DG[k] = {**h, "探索_退化": RLU.degen(h, "探索"), "確認_退化": RLU.degen(h, "確認"), "主窗_退化": RLU.degen(h, "主窗"), "種子": len(ms),
                 "候選不足": {sg: CO.short_months(WM, ms[0], x_, y_) for sg, (x_, y_) in seg.items()}}
    cand = {}
    for c in CELLS:
        g = FB[c].groupby("e").size()
        cand[c] = {"有進場的日子": int(len(g)), "主窗訊號": int(len(FB[c])), "每個進場日訊號數": RLU.q_(g.to_numpy()),
                   "訊號數逐年（進場日）": {str(k): int(v) for k, v in pd.Series([WM.cal[e].year for e in FB[c]["e"]]).value_counts().sort_index().items()}}
    DJ = {"寫入時間": now_tpe() + "（台北）", "件": C["reg"], "說明": "⭐ 本檔在彙總任何報酬之前寫入（K12）；退化 ＝ 平均持股 ＜ 3 或平均現金 ＞ 30%（段內逐日平均、種子中位）；退化格照登錄排除",
          "候選與訊號": cand, "持股與現金": DG,
          "排除的格（探索段退化）": sorted({k.split('|')[0] for k, v in DG.items() if k.endswith('|b') and v['探索_退化']}),
          "各段退化列表": {k: [sg for sg in ("探索", "確認", "主窗") if v[f"{sg}_退化"]] for k, v in DG.items()}}
    jdump(DJ, os.path.join(OUT, "degeneracy.json"))
    log("[退化] 已寫 degeneracy.json：" + "；".join(f"{k} 探索 {v['探索_平均持股']:.2f} 檔／現金 {v['探索_平均現金']:.1%}、確認 {v['確認_平均持股']:.2f}／{v['確認_平均現金']:.1%}"
                                              for k, v in DG.items()))
    # ── 早年（可判的格）：先跑、先寫退化 ──
    ECELLS = [c for c in CELLS if c[:2] in C["early"]]
    EARLYR = {"可判的格": ECELLS, "不可判定": {c: ("法人資料 data/stocks_inst 2015-01-05 起" if c.startswith("I1") else "data/stocks_margin 2015-01-05 起")
                                          for c in CELLS if c not in ECELLS}}
    RE_, FE = {}, {}
    ea, eb = WE.segpos(*EARLY); es = {"早年": (ea, eb)}
    if ECELLS:
        arms = []
        for c in ECELLS:
            rw = cell_rows("early", XE, c[:2], c[2:], ea, eb)
            FE[c] = RLU.finalize_rows(WE, rw, False)
            arms += [(f"{c}|b", FE[c], False, a.reps), (f"{c}|r", RLU.finalize_rows(WE, rw, True), True, a.reps)]
        RE_ = RLU.run_arms(WE, arms, es, eb, a.procs, log)
        HE = {k: RLU.hold_only(ms, es) for k, ms in RE_.items()}
        DJ = json.load(open(os.path.join(OUT, "degeneracy.json"), encoding="utf-8"))
        DJ["早年"] = {"寫入時間": now_tpe() + "（台北）", "窗": list(EARLY), "訊號": {c: int(len(FE[c])) for c in FE},
                    "持股與現金": {k: {**h, "早年_退化": RLU.degen(h, "早年")} for k, h in HE.items()}, "不可判定": EARLYR["不可判定"]}
        jdump(DJ, os.path.join(OUT, "degeneracy.json"))
        log("[退化] 早年已補寫：" + "；".join(f"{k} {h['早年_平均持股']:.2f} 檔／現金 {h['早年_平均現金']:.1%}" for k, h in HE.items()))
        ZE = {"早年": RR.bench_row(WE.cal, WE.bench, ea, eb + 1)}
        EG = {k: {**{kk: v for kk, v in RLU.summarize(ms, ZE, es).items() if not kk.startswith("_")}, **HE[k], "早年_退化": RLU.degen(HE[k], "早年")}
              for k, ms in RE_.items()}
        EARLYR.update({"窗": list(EARLY), "0050": ZE["早年"], "格": EG})
    else:
        ZE = {"早年": RR.bench_row(WE.cal, WE.bench, ea, eb + 1)}
    # ── 報酬、挑格、判定 ──
    GRID = [{"格": k.split("|")[0], "版本": k.split("|")[1], **RLU.summarize(ms, Z, seg), **{kk: vv for kk, vv in DG[k].items() if kk != "候選不足"}}
            for k, ms in RES.items()]
    GR = pd.DataFrame(GRID)
    base = GR[GR["版本"] == "b"].copy(); base["_ord"] = [CELLS.index(c) for c in base["格"]]
    nd = base[~base["探索_退化"]]; all_deg = len(nd) == 0
    pool_ = nd if not all_deg else base
    qq = pool_[pool_["探索_標籤"] == "合格"]
    pick = (qq if len(qq) else pool_).sort_values(["探索_比值", "探索_年化", "_ord"], ascending=[False, False, True]).iloc[0]
    chosen = pick["格"]; cx = chosen[2:]
    log(f"[挑格] 非退化 {len(nd)}／{len(base)}、探索合格 {len(qq)} ⇒ {chosen}{'（⚠ 全退化）' if all_deg else ''}")
    CH = {v: {k: x for k, x in GR[(GR["格"] == chosen) & (GR["版本"] == v)].iloc[0].to_dict().items() if not k.startswith("_")} for v in ("b", "r")}
    lab_c, lab_cr = CH["b"]["確認_標籤"], CH["r"]["確認_標籤"]
    e_ok = chosen in ECELLS
    if e_ok:
        lab_e = EARLYR["格"][f"{chosen}|b"]["早年_標籤"]; lab_er = EARLYR["格"][f"{chosen}|r"]["早年_標籤"]
        deg_e = EARLYR["格"][f"{chosen}|b"]["早年_退化"]
        fin_b, fin_r = RLU.stricter(lab_c, lab_e), RLU.stricter(lab_cr, lab_er)
    else:
        lab_e = lab_er = f"不可判定（{EARLYR['不可判定'].get(chosen, '')}）"
        deg_e = False
        fin_b, fin_r = lab_c, lab_cr
    deg_c = DG[f"{chosen}|b"]["確認_退化"]
    cap = lambda L_: ("暫定（標籤上限：同批急跌事件事後重切，裁定 seq336 §二）" if L_ == "合格" else L_)
    if deg_c or deg_e:
        fin_b = f"退化（{'確認' if deg_c else ''}{'早年' if deg_e else ''}段）⇒ 照登錄排除、不判合格"
    VERD = {"挑中格": chosen, "全退化": all_deg, "探索": CH["b"]["探索_標籤"], "確認": lab_c, "早年": lab_e, "判定": cap(fin_b),
            "現實版探索": CH["r"]["探索_標籤"], "現實版確認": lab_cr, "現實版早年": lab_er, "現實版判定": cap(fin_r),
            "標籤上限": "最多暫定（同批急跌事件事後重切）", "同批急跌事件第n次切分": C["nth"]}
    log(f"[判定] {VERD}")
    # ── 對照 A、B、描述 ──
    Fc = FB[chosen]
    FA = {x: RLU.finalize_rows(WM, a_rows("main", x, w0, w1), False) for x in ("X1", "X2")}
    FAr = RLU.finalize_rows(WM, a_rows("main", cx, w0, w1), True)
    darms = [("A|X1", FA["X1"], False, a.reps), ("A|X2", FA["X2"], False, a.reps), (f"A|{cx}|r", FAr, True, 50)]
    BSAME = {}
    for ci, c in enumerate(CELLS):
        wt = WT[c]
        if len(wt) == 0:
            BSAME[c] = "該格主窗沒有進場 ⇒ B 不可算"; continue
        if (wt == 0).all():
            BSAME[c] = "等待天數全是 0 ⇒ B ＝ A（同一批列、同種子），不另跑"; continue
        for i in range(a.fake):
            darms.append((f"B|{c}#{i}", RLU.finalize_rows(WM, delay_rows("main", ck, ci, c[2:], wt, i, w0, w1), False), False, ("fake", i)))
    dsc = C["desc"]
    if dsc:
        rw = cell_rows("main", XM, dsc, cx, w0, w1)
        if len(rw):
            darms.append((f"D|{dsc}{cx}", RLU.finalize_rows(WM, rw, False), False, 50))
    for H in (20, 60, 120):
        darms.append((f"固定{H}", RLU.finalize_rows(WM, RLU.fixed_rows(WM, Fc, H), False), False, 50))
    ma = pd.Series(WM.bench).rolling(200, min_periods=200).mean().to_numpy()
    with np.errstate(invalid="ignore"):
        keep = WM.bench[Fc["e"].to_numpy(int) - 1] > ma[Fc["e"].to_numpy(int) - 1]
    darms.append(("0050在200日線上才買", Fc[keep].reset_index(drop=True), False, 50))
    darms = [z for z in darms if len(z[1])]
    t_d = time.time()
    DRES = RLU.run_arms(WM, darms, seg, w1, a.procs, log)
    log(f"[對照與描述] {len(darms)} 臂｜{time.time() - t_d:.0f}s")
    DESC = {k: {**{kk: v for kk, v in RLU.summarize(ms, Z, seg).items() if not kk.startswith("_")}, **RLU.hold_only(ms, seg)} for k, ms in DRES.items()
            if not k.startswith("B|")}
    DESC["0050在200日線上才買"]["訊號（主窗）"] = int(keep.sum())
    DESC["A|X1"]["訊號（主窗）"] = int(len(FA["X1"])); DESC["A|X2"]["訊號（主窗）"] = int(len(FA["X2"]))
    if dsc and f"D|{dsc}{cx}" in DESC:
        DESC[f"D|{dsc}{cx}"]["訊號（主窗）"] = int(len(rw))
    # A 對急跌錯殺 summary 的「對照①」（X2）
    COS = json.load(open(os.path.join(CO_OUT, "summary.json"), encoding="utf-8"))["描述"]["對照①急跌不看基本面"]
    A_rep = {sg: {"本件A|X2年化": DESC["A|X2"][f"{sg}_年化"], "急跌錯殺對照①年化": COS[f"{sg}_年化"],
                  "逐位元相同": repr(float(DESC["A|X2"][f"{sg}_年化"])) == repr(float(COS[f"{sg}_年化"])) and repr(float(DESC["A|X2"][f"{sg}_回落"])) == repr(float(COS[f"{sg}_回落"]))}
             for sg in SEGS}
    log(f"[A 重現急跌錯殺對照①] {A_rep}")
    GRb = {r["格"]: r for r in GRID if r["版本"] == "b"}
    FAKE = {}
    for c in CELLS:
        ks = [k for k in DRES if k.startswith(f"B|{c}#")]
        if ks:
            FK = [RLU.summarize(DRES[k], Z, seg) for k in ks]
            FAKE[c] = fake_summary(FK, GRb[c], Z, seg)
        elif "B ＝ A" in BSAME.get(c, ""):
            FAKE[c] = {sg: {"等同A": True, "年化中位": DESC[f"A|{c[2:]}"][f"{sg}_年化"], "回落中位": DESC[f"A|{c[2:]}"][f"{sg}_回落"],
                            "p（假訊號年化 ≥ 該格）": float(np.mean(RLU.summarize(DRES[f"A|{c[2:]}"], Z, seg)[f"_{sg}_all"] >= GRb[c][f"{sg}_年化"]))} for sg in SEGS}
    # 早年 A、B（挑中格可判時）
    EAB = {}
    if e_ok:
        FAe = RLU.finalize_rows(WE, a_rows("early", cx, ea, eb), False)
        earms = [(f"A|{cx}", FAe, False, a.reps)]
        wte = WT[chosen]
        ci = CELLS.index(chosen)
        if len(wte) and not (wte == 0).all():
            for i in range(a.fake):
                earms.append((f"B#{i}", RLU.finalize_rows(WE, delay_rows("early", ck, ci, cx, wte, i, ea, eb), False), False, ("fake", i)))
        ER = RLU.run_arms(WE, earms, es, eb, a.procs, log)
        sA = RLU.summarize(ER[f"A|{cx}"], ZE, es)
        EAB["A"] = {k: v for k, v in sA.items() if not k.startswith("_")}
        EAB["A"]["訊號"] = int(len(FAe))
        ks = [k for k in ER if k.startswith("B#")]
        cs = EARLYR["格"][f"{chosen}|b"]
        if ks:
            EAB["B"] = fake_summary([RLU.summarize(ER[k], ZE, es) for k in ks], cs, ZE, es)["早年"]
        else:
            EAB["B"] = {"等同A": True, "年化中位": EAB["A"]["早年_年化"], "p（假訊號年化 ≥ 該格）": float(np.mean(sA["_早年_all"] >= cs["早年_年化"]))}
        EAB["挑中格早年年化"] = cs["早年_年化"]
    # 條件有用（K7）
    CU = {}
    for c in CELLS:
        CU[c] = {}
        for sg in SEGS:
            cv = GRb[c][f"{sg}_年化"]; av = DESC[f"A|{c[2:]}"][f"{sg}_年化"]; bv = FAKE.get(c, {}).get(sg, {}).get("年化中位", np.nan)
            CU[c][sg] = {"該格年化": cv, "A年化": av, "B年化中位": bv, "B的p": FAKE.get(c, {}).get(sg, {}).get("p（假訊號年化 ≥ 該格）", np.nan),
                         "該格比值": GRb[c][f"{sg}_比值"], "A比值": DESC[f"A|{c[2:]}"][f"{sg}_比值"],
                         "贏A": bool(cv > av), "贏B": bool(np.isfinite(bv) and cv > bv)}
    cu_c = CU[chosen]["確認"]
    useful = cu_c["贏A"] and cu_c["贏B"]
    if e_ok:
        ce = EAB["挑中格早年年化"]
        e_wa, e_wb = bool(ce > EAB["A"]["早年_年化"]), bool(ce > EAB["B"]["年化中位"])
        useful = useful and e_wa and e_wb
        CU["挑中格早年"] = {"該格年化": ce, "A年化": EAB["A"]["早年_年化"], "B年化中位": EAB["B"]["年化中位"], "B的p": EAB["B"]["p（假訊號年化 ≥ 該格）"],
                         "贏A": e_wa, "贏B": e_wb}
    CUV = {"挑中格": chosen, "條件有用": bool(useful),
           "一句": ("條件有用（確認段" + ("與早年段" if e_ok else "") + "都贏對照 A 與延後假訊號；標籤最多暫定）") if useful else
           ("條件沒有比較好：挑中格" + ("、".join(x for x, ok_ in (("確認段沒贏對照 A", not cu_c["贏A"]), ("確認段沒贏延後假訊號", not cu_c["贏B"]),
                                                    ("早年段沒贏對照 A", e_ok and not CU["挑中格早年"]["贏A"]), ("早年段沒贏延後假訊號", e_ok and not CU["挑中格早年"]["贏B"])) if ok_)))}
    log(f"[條件有用] {CUV}")
    # ── 必報 ──
    msC = RES[f"{chosen}|b"]; msR = RES[f"{chosen}|r"]
    TS = {"b": RLU.trade_stats(WM, msC, Fc, w1), "r": RLU.trade_stats(WM, msR, FR[chosen], w1)}
    TS_all = {c: RLU.trade_stats(WM, RES[f"{c}|b"], FB[c], w1) for c in CELLS}
    TS_A = {x: RLU.trade_stats(WM, DRES[f"A|{x}"], FA[x], w1) for x in ("X1", "X2")}
    NE = CO.neff_ind(WM, msC[0], seg, PM)
    NE_all = {c: CO.neff_ind(WM, RES[f"{c}|b"][0], {"確認": seg["確認"]}, PM).get("確認", {}).get("平均N_eff") for c in CELLS}
    YR = {k: float(np.median([RLU.years_ret(m["eq"], WM.cal, w0, w1)[k] for m in msC])) for k in RLU.years_ret(msC[0]["eq"], WM.cal, w0, w1)}
    YRr = {k: float(np.median([RLU.years_ret(m["eq"], WM.cal, w0, w1)[k] for m in msR])) for k in RLU.years_ret(msR[0]["eq"], WM.cal, w0, w1)}
    YR50 = RLU.years_ret(WM.bench, WM.cal, w0, w1)
    Y = RLU.yl_ref(log); YC = RLU.yl_cells()
    ovl = {}
    for fam, nmf in (("fly", "營飆 v1"), ("vol", "營量 v1")):
        ivB = [(s, WM.pos(a_), WM.pos(b_) if b_ != "9999-12-31" else WM.n + 1) for s, a_, b_ in Y[fam]["iv"]]
        for sg, (x_, y_) in seg.items():
            ovl.setdefault(sg, {})[f"與{nmf}持股重疊率"] = RLU.overlap_daily(msC[0]["iv"], ivB, x_, y_)
    WAIT = {}
    for ty in tys:
        G_ = XM[XM[f"{ty}_ok"] & (XM[f"{ty}_e"] >= w0) & (XM[f"{ty}_e"] <= w1)]
        WAIT[ty] = {"e − t（交易日）": RLU.q_((G_[f"{ty}_e"] - G_["t"]).to_numpy()), "分佈": {str(k): int(v) for k, v in (G_[f"{ty}_e"] - G_["t"]).value_counts().sort_index().items()}}
        if len(ECELLS) and ty in C["early"]:
            Ge = XE[XE[f"{ty}_ok"] & (XE[f"{ty}_e"] >= ea) & (XE[f"{ty}_e"] <= eb)]
            WAIT[ty]["早年 e − t"] = RLU.q_((Ge[f"{ty}_e"] - Ge["t"]).to_numpy())
    EA = pd.concat([XE.assign(年=[WE.cal[t].year for t in XE["t"]]), XM.assign(年=[WM.cal[t].year for t in XM["t"]])], ignore_index=True)
    EA = EA[EA["年"] >= 2005]
    yrs = []
    for y, g in EA.groupby("年"):
        row = {"年": int(y), "急跌事件（去重後）": int(len(g)), "公司事件剔（急跌錯殺口徑 [t−10,t]）": int(g["公司事件"].sum())}
        for ty in tys:
            row[f"{ty}成立"] = int((g[f"{ty}_cond"] == 1).sum()); row[f"{ty}不明"] = int(g[f"{ty}_cond"].isna().sum()); row[f"{ty}可進"] = int(g[f"{ty}_ok"].sum())
        yrs.append(row)
    mwin = XM[(XM["t"] + 1 >= w0) & (XM["t"] + 1 <= w1)]
    rate = {ty: {"主窗事件": int(len(mwin)), "成立": int((mwin[f"{ty}_cond"] == 1).sum()), "不明": int(mwin[f"{ty}_cond"].isna().sum()),
                 "成立占事件": float((mwin[f"{ty}_cond"] == 1).mean()), "可進": int(mwin[f"{ty}_ok"].sum())} for ty in tys}
    EVD = {"挑中格：大盤也急跌 vs 只有個股": CO.ev_desc(Fc, PM["E"].assign(e=XM[f"{chosen[:2]}_e"].to_numpy()), w0, w1, "大盤也急跌")}
    # ── 先驗 ──
    both = [c for c in CELLS if GRb[c]["探索_標籤"] == "合格" and GRb[c]["確認_標籤"] == "合格"]
    PRI = {"① 兩段都合格的格 0 個": {"兩段都合格的格": both, "成立": len(both) == 0}}
    if ck in ("rev", "stop", "margin"):
        PRI["② 本件確認段 ＞ 對照 A"] = {"挑中格": chosen, "挑中格確認年化": GRb[chosen]["確認_年化"], "A確認年化": DESC[f"A|{cx}"]["確認_年化"],
                                    "成立": bool(GRb[chosen]["確認_年化"] > DESC[f"A|{cx}"]["確認_年化"])}
    else:
        PRI["② I1 確認段 ＞ 對照 A"] = {c: {"確認年化": GRb[c]["確認_年化"], "A確認年化": DESC[f"A|{c[2:]}"]["確認_年化"], "成立": bool(GRb[c]["確認_年化"] > DESC[f"A|{c[2:]}"]["確認_年化"])}
                                    for c in CELLS if c.startswith("I1")}
    if ck == "rev":
        PRI["③ 本件成立事件占急跌事件 ＜ 30%"] = {ty: {"成立占事件（主窗）": rate[ty]["成立占事件"], "成立": bool(rate[ty]["成立占事件"] < 0.30)} for ty in C["types"]}
    elif ck == "stop":
        nb = [c for c in CELLS if CU[c]["確認"]["贏B"]]
        PRI["③ 本件贏對照 B 的格 ≤ 1 個"] = {"確認段贏 B 的格": nb, "成立": len(nb) <= 1}
    elif ck == "inst":
        per = [r_["I2成立"] for r_ in yrs]
        PRI["③ I2 每年成立事件 ＜ 20 筆、退化"] = {"I2 每年成立": {str(r_["年"]): r_["I2成立"] for r_ in yrs}, "每年都 ＜ 20": bool(max(per) < 20),
                                             "I2 格探索退化": {c: DG[f"{c}|b"]["探索_退化"] for c in CELLS if c.startswith("I2")},
                                             "成立": bool(max(per) < 20 and all(DG[f"{c}|b"]["探索_退化"] for c in CELLS if c.startswith("I2")))}
    elif ck == "margin":
        mm = mwin[mwin["M1_cond"] == 1]
        sh = float((mm["大盤也急跌"] == 1).sum() / mm["大盤也急跌"].notna().sum()) if mm["大盤也急跌"].notna().sum() else np.nan
        PRI["③ 成立事件集中在大盤急跌期占 ＞ 30%"] = {"M1 成立（主窗）": int(len(mm)), "大盤也急跌占比": sh, "成立": bool(sh > 0.30) if np.isfinite(sh) else None,
                                                "對照：全部急跌事件的大盤也急跌占比": float((mwin["大盤也急跌"] == 1).sum() / max(mwin["大盤也急跌"].notna().sum(), 1))}
    extra = {}
    if ck == "inst":
        extra["庫藏股公告"] = buyback(log)[1]
        extra["法人檔數"] = inst_mat(WM, log)[1]
    if ck == "margin":
        extra["融資檔數"] = margin_mat(WM, log)[2]
    SUM = {"meta": {"件": C["reg"], "登錄": regf, "sha": C["sha"], "補讀法寫死": TIME, "run": now_tpe() + "（台北）", "reps": a.reps, "fake": a.fake,
                    "N": "N_組合 ＋1（裁定 seq336 §二）", "標籤上限": "最多暫定（同批急跌事件事後重切）", "同批急跌事件第n次切分": C["nth"],
                    "tw-stock-data": CO_SHA, "價量快照": "rerun17 H2D edc6f8002f（main）／eotc_f65bb03e11（早年）", "0050": Z, "早年0050": ZE["早年"],
                    "R1": {"X": G["X"]}, "同一事件集": G["verify"], "A重現急跌錯殺對照①": A_rep, "資料": extra,
                    "版面": {"main": [str(WM.cal[0].date()), str(WM.cal[-1].date()), WM.n, WM.S], "早年": [str(WE.cal[0].date()), str(WE.cal[-1].date()), WE.n, WE.S]}},
           "結果句必附": [f"同批急跌事件第 {C['nth']} 次切分（急跌錯殺 seq1 是第 1 次）"] + C["sent"],
           "判定": VERD, "條件有用": CUV, "條件有用明細": CU, "挑中格": CH, "退化": DJ, "格": [{k: x for k, x in r.items() if not k.startswith("_")} for r in GRID],
           "早年": EARLYR, "早年AB": EAB, "延後假訊號": FAKE, "B說明": BSAME, "描述": DESC, "逐筆": TS, "逐筆（各格）": TS_all, "逐筆（A）": TS_A,
           "等效獨立": NE, "等效獨立（各格確認段平均）": NE_all, "等待天數": WAIT, "成立率": rate,
           "各年": {"策略": YR, "策略現實版": YRr, "0050": YR50}, "營量營飆": YC, "營量營飆r0閘": Y["閘"], "重疊": ovl, "事件描述": EVD, "每年事件": yrs, "先驗": PRI,
           "訊號": {c: int(len(FB[c])) for c in CELLS}, "耗時秒": round(time.time() - t00)}
    jdump(SUM, os.path.join(OUT, "summary.json"))
    pd.DataFrame([{k: x for k, x in r.items() if not k.startswith("_")} for r in GRID]).to_csv(os.path.join(OUT, "grid.csv"), index=False, float_format="%.6g")
    seeds = []
    for nm_, ms in list(RES.items()) + [(f"早年{k}", v) for k, v in RE_.items()] + list(DRES.items()):
        sg_ = es if nm_.startswith("早年") else seg
        for m in ms:
            seeds.append({"arm": nm_, "r": m["r"], **RLU.seg_ret(m, sg_), **m["hold"], "trades": m["trades"], "sha": hashlib.sha256(m["eq"].tobytes()).hexdigest()[:16]})
    pd.DataFrame(seeds).to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False, float_format="%.10g")
    log(f"[完] {VERD}｜{CUV['一句']}｜{time.time() - t00:.0f}s")


def dump_exits(ck, a):
    """查核用：entries.csv.gz 裡每筆可進場列（各進場型態、兩版面）用主程式 exits_x 算的出場 ⇒ exits.csv.gz（不跑引擎、不改結果）。"""
    C = CASES[ck]; OUT = os.path.join(OUTROOT, C["name"])
    log = CO.log_to(os.path.join(OUT, "run.log"))
    log(f"===== researchCrashExt exits {ck} {now_tpe()}（台北）：只寫 exits.csv.gz 給 --check 用 =====")
    world(a, log)
    EN = pd.read_csv(os.path.join(OUT, "entries.csv.gz"), dtype={"sid": str}, low_memory=False)
    tys = C["types"] + ([C["desc"]] if C["desc"] else [])
    rows = []
    for part in ("main", "early"):
        E = EN[EN["版面"] == part]
        for ty in tys:
            G_ = E[E[f"{ty}_ok"].astype(bool)]
            for s, t, e, sid in zip(G_["s"].astype(int), G_["t"].astype(int), G_[f"{ty}_e"].astype(int), G_["sid"]):
                r = exits_x(part, s, t, e, sid)
                rows.append({"版面": part, "型態": ty, "sid": sid, "s": s, "t": t, "e": e, **{f"{x}_{k}": v for x in ("X1", "X2") for k, v in zip(("xk", "x", "why"), r[x])}})
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "exits.csv.gz"), index=False)
    log(f"[exits] {len(rows)} 列 ⇒ exits.csv.gz")


# ═════════════ 網頁 ═════════════
def _ok(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and x is not None and np.isfinite(x)


def _p(x, d=1):
    return f"{x * 100:+.{d}f}%" if _ok(x) else "—"


def _pp(x, d=1):
    return f"{x * 100:.{d}f}%" if _ok(x) else "—"


def _f(x, d=1):
    return f"{x:.{d}f}" if _ok(x) else "—"


CSS = """:root{--bg:#ffffff;--fg:#1d1d1b;--mut:#6b6a66;--line:#e2dfd8;--acc:#1f5f8b;--card:#ffffff;--hi:#fff4d6}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#161615;--fg:#ecebe6;--mut:#a3a19a;--line:#33322f;--acc:#7cb6de;--card:#1e1e1c;--hi:#3a3220}}
:root[data-theme="dark"]{--bg:#161615;--fg:#ecebe6;--mut:#a3a19a;--line:#33322f;--acc:#7cb6de;--card:#1e1e1c;--hi:#3a3220}
body{background:var(--bg);color:var(--fg);font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif;line-height:1.6;margin:0 auto;padding:24px 16px;max-width:980px}
h1{font-size:1.45rem;margin:.2em 0}h2{font-size:1.15rem;border-bottom:2px solid var(--acc);padding-bottom:.2em;margin-top:2em}
.lead{font-size:1.06rem}.m{color:var(--mut);font-size:.88rem}.box{background:var(--hi);padding:10px 14px;border-radius:6px}
table{border-collapse:collapse;width:100%;margin:.4em 0;font-size:.9rem;display:block;overflow-x:auto;background:var(--card)}
th,td{border:1px solid var(--line);padding:5px 8px;text-align:right;white-space:nowrap}th{text-align:left}thead th{background:var(--line)}"""


def page(ck):
    C = CASES[ck]; OUT = os.path.join(OUTROOT, C["name"])
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    ckj = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else {}
    e = html.escape; SEGN = ("探索", "確認", "主窗")
    V = S["判定"]; ch = V["挑中格"]; cx = ch[2:]; CU = S["條件有用"]; CUD = S["條件有用明細"]
    G = {(r["格"], r["版本"]): r for r in S["格"]}; Z = S["meta"]["0050"]; DS = S["描述"]; FK = S["延後假訊號"]
    EA = S["早年"]; EAB = S.get("早年AB") or {}
    CELLS = cells_of(ck)
    cb, cr = G[(ch, "b")], G[(ch, "r")]

    def cell(r, sg):
        return f"{_p(r.get(f'{sg}_年化'))}／{_p(r.get(f'{sg}_回落'))}" if r else "—"
    eline = ""
    if EA.get("格") and f"{ch}|b" in EA["格"]:
        eg = EA["格"][f"{ch}|b"]; egr = EA["格"][f"{ch}|r"]
        eline = (f"<li>早年 2005～2014：{cell(eg, '早年')}（{e(eg['早年_標籤'])}；現實版 {cell(egr, '早年')}），同段 0050 {_p(EA['0050']['cagr'])}／{_p(EA['0050']['mdd'])}。"
                 f"對照 A 早年 {_p(EAB.get('A', {}).get('早年_年化'))}、延後假訊號中位 {_p(EAB.get('B', {}).get('年化中位'))}。</li>")
    else:
        eline = f"<li>早年：{e(V['早年'])}。</li>"
    cA = CUD[ch]["確認"]
    head = ("這樣挑，扣成本後沒有通過對 0050 的判準" if str(V["判定"]).startswith("不合格") else "")
    head2 = ("；而且「多這個條件」也沒有穩定地比「急跌隔天就買」或「同樣晚幾天買」好" if not CU["條件有用"] else "；多這個條件比「急跌隔天就買」與「同樣晚幾天買」都好")
    lead = (f"<div class=box><p class=lead><b>結論：{head}{head2}。</b></p>"
            f"<p>判定「{e(V['判定'])}」（現實版「{e(V['現實版判定'])}」）；{e(CU['一句'])}。</p>"
            f"<p>這是同批急跌事件第 {C['nth']} 次切分（急跌錯殺 seq1 是第 1 次），結果最多只能到「暫定」。</p></div><ul>"
            f"<li>{len(CELLS)} 格裡探索段挑中 <b>{e(cname(ck, ch))}</b>：探索 {cell(cb, '探索')}（{e(cb['探索_標籤'])}），確認 2022-01～2026-08 {cell(cb, '確認')}"
            f"（{e(cb['確認_標籤'])}），同段 0050 {_p(Z['確認']['cagr'])}／{_p(Z['確認']['mdd'])}。</li>" + eline +
            f"<li>多這個條件有沒有比較好（確認段）：本格 {_p(cA['該格年化'])}，對照 A（急跌不看條件、隔天買、同出場）{_p(cA['A年化'])}，"
            f"延後假訊號（同批急跌隨機晚同樣天數買）中位 {_p(cA['B年化中位'])}（p ＝ {_f(cA['B的p'], 2)}）。</li>"
            f"<li>現實版（每邊多 0.3%、衝擊、漲跌停買賣不到）確認段 {cell(cr, '確認')}。</li></ul>"
            + "".join(f"<p class=m>※ {e(x)}</p>" for x in S["結果句必附"]))
    # 主表
    rows = []
    for c in CELLS:
        r = G[(c, "b")]; rr = G[(c, "r")]
        rows.append(f"<tr><th>{'★ ' if c == ch else ''}{e(cname(ck, c))}</th>" + "".join(f"<td>{cell(r, s)}<br><span class=m>{e(str(r[f'{s}_標籤']))}</span></td>" for s in SEGN)
                    + f"<td>{cell(rr, '確認')}</td><td>{S['訊號'][c]}</td></tr>")
    for x in ("X1", "X2"):
        rows.append(f"<tr><th>對照 A（急跌、不看條件、隔天買｜{XN[x]}）</th>" + "".join(f"<td>{cell(DS[f'A|{x}'], s)}</td>" for s in SEGN) + f"<td>—</td><td>{DS[f'A|{x}'].get('訊號（主窗）', '—')}</td></tr>")
    rows.append("<tr><th>0050</th>" + "".join(f"<td>{_p(Z[s]['cagr'])}／{_p(Z[s]['mdd'])}</td>" for s in SEGN) + "<td>—</td><td>—</td></tr>")
    for nm in ("營量 v1", "營飆 v1"):
        y = S["營量營飆"].get(nm, {})
        rows.append(f"<tr><th>{nm}（參考）</th>" + "".join(f"<td>{_p(y.get(s, {}).get('年化'))}／{_p(y.get(s, {}).get('回落'))}</td>" for s in SEGN) + "<td>—</td><td>—</td></tr>")
    main_t = ("<table><thead><tr><th>格（年化中位／最大回落中位，200 顆）</th><th>探索 2017-03～2021-12</th><th>確認 2022-01～2026-08</th><th>主窗</th><th>現實版確認</th><th>主窗訊號</th></tr></thead><tbody>"
              + "".join(rows) + "</tbody></table><p class=m>標籤：合格 ＝ 年化贏 0050 且 年化÷|回落| 不輸 0050；另列 ＝ 只贏年化。★ ＝ 探索段挑中格。</p>")
    # A／B
    br = []
    for c in CELLS:
        for s in SEGN:
            d = CUD[c][s]
            br.append(f"<tr><th>{e(c)} {s}</th><td>{_p(d['該格年化'])}</td><td>{_p(d['A年化'])}</td><td>{_p(d['B年化中位'])}</td><td>{_f(d['B的p'], 2)}</td>"
                      f"<td>{'贏' if d['贏A'] else '輸'}</td><td>{'贏' if d['贏B'] else '輸'}</td></tr>")
    if "挑中格早年" in CUD:
        d = CUD["挑中格早年"]
        br.append(f"<tr><th>{e(ch)} 早年</th><td>{_p(d['該格年化'])}</td><td>{_p(d['A年化'])}</td><td>{_p(d['B年化中位'])}</td><td>{_f(d['B的p'], 2)}</td>"
                  f"<td>{'贏' if d['贏A'] else '輸'}</td><td>{'贏' if d['贏B'] else '輸'}</td></tr>")
    bnote = "；".join(f"{k}：{v}" for k, v in S["B說明"].items())
    ab = ("<table><thead><tr><th>格／段</th><th>本格年化</th><th>對照 A 年化</th><th>延後假訊號年化中位</th><th>p（假訊號 ≥ 本格）</th><th>vs A</th><th>vs 延後假訊號</th></tr></thead><tbody>"
          + "".join(br) + "</tbody></table>"
          f"<p class=m>判「條件有用」要挑中格在確認段（早年可判時再加早年段）同時贏 A 與延後假訊號。延後假訊號：同一批急跌事件，買進日從隔天隨機延後 d 天（d 抽自該格實際等待天數），"
          f"同出場、200 抽。{e(bnote)}</p>"
          f"<p class=m>對照 A 重現急跌錯殺 seq1 的對照①（X2）："
          + "；".join(f"{s} {_p(v['本件A|X2年化'])} vs {_p(v['急跌錯殺對照①年化'])}（{'逐位元相同' if v['逐位元相同'] else '不同'}）" for s, v in S["meta"]["A重現急跌錯殺對照①"].items()) + "</p>")
    # 退化
    DG = S["退化"]["持股與現金"]
    deg = ("<table><thead><tr><th>格</th><th>探索 平均持股／現金</th><th>確認</th><th>主窗</th><th>退化段</th></tr></thead><tbody>"
           + "".join(f"<tr><th>{e(k)}</th>" + "".join(f"<td>{_f(v[f'{s}_平均持股'], 2)}／{_pp(v[f'{s}_平均現金'])}</td>" for s in SEGN)
                     + f"<td>{'、'.join(S['退化']['各段退化列表'][k]) or '無'}</td></tr>" for k, v in DG.items() if k.endswith("|b"))
           + "</tbody></table>"
           f"<p class=m>degeneracy.json 寫入 {e(S['退化']['寫入時間'])}（在任何報酬彙總之前）。排除的格：{'、'.join(S['退化']['排除的格（探索段退化）']) or '無'}。"
           + (f"早年：" + "；".join(f"{k} {_f(v['早年_平均持股'], 2)} 檔／現金 {_pp(v['早年_平均現金'])}{'（退化）' if v['早年_退化'] else ''}" for k, v in S["退化"]["早年"]["持股與現金"].items() if k.endswith("|b"))
              if "早年" in S["退化"] else "") + "</p>")
    # 必報
    T = S["逐筆"]["b"]; NE = S["等效獨立"]; ov = S["重疊"]
    why = "、".join(f"{k} {v:.0f}" for k, v in T["出場原因（每顆平均）"].items())
    wt = S["等待天數"]
    must = ("<ul>"
            f"<li>等效獨立檔數（確認段）：平均 {_f(NE.get('確認', {}).get('平均N_eff'), 2)} 檔（平均持股 {_f(NE.get('確認', {}).get('平均持股'), 2)}、兩兩相關 {_f(NE.get('確認', {}).get('平均ρ'), 2)}）；"
            f"最大產業中位 {_f(NE.get('確認', {}).get('最大產業檔數中位'), 0)} 檔。主窗 {_f(NE.get('主窗', {}).get('平均N_eff'), 2)}。</li>"
            f"<li>現金比例（確認段）：{_pp(DG[f'{ch}|b']['確認_平均現金'])}；候選不足月份（月均持股 ＜ 10）："
            f"{_pp(DG[f'{ch}|b']['候選不足']['確認']['候選不足月份占比（月平均持股＜10）'], 0)}。</li>"
            f"<li>持有天數（主窗、已出場）：中位 {_f(T['持有天數（交易日，已出場，種子合計）'].get('中位'), 0)}、p10 {_f(T['持有天數（交易日，已出場，種子合計）'].get('p10'), 0)}、"
            f"p90 {_f(T['持有天數（交易日，已出場，種子合計）'].get('p90'), 0)} 個交易日；出場原因（每顆平均）：{e(why)}。</li>"
            f"<li>窗尾仍持有：{_f(T['窗尾仍持有（檔，種子中位）'], 0)} 檔；一年內先跌 15%：{_pp(T['一年內先跌15%比例'])}（{T['觀察窗滿250筆']} 筆）。</li>"
            + "".join(f"<li>等待天數 {e(ty)}（t 到進場，交易日）：中位 {_f(v['e − t（交易日）'].get('中位'), 0)}、p10 {_f(v['e − t（交易日）'].get('p10'), 0)}、"
                      f"p90 {_f(v['e − t（交易日）'].get('p90'), 0)}（{v['e − t（交易日）'].get('n', 0)} 筆）。</li>" for ty, v in wt.items())
            + "".join(f"<li>{e(ty)} 成立率（主窗急跌事件）：{v['成立']}／{v['主窗事件']} ＝ {_pp(v['成立占事件'])}（不明 {v['不明']}、通過進場檢查 {v['可進']}）。</li>" for ty, v in S["成立率"].items())
            + f"<li>與營量 v1 持股重疊 {_pp(ov['確認']['與營量 v1持股重疊率'])}、與營飆 v1 {_pp(ov['確認']['與營飆 v1持股重疊率'])}（確認段）。</li></ul>")
    # 描述
    dd = []
    for k, v in DS.items():
        if k.startswith("A|") and k.count("|") == 1:
            continue
        nm = {"固定20": "固定持有 20 天", "固定60": "固定持有 60 天", "固定120": "固定持有 120 天", "0050在200日線上才買": "0050 在 200 日線上才買（擋長空頭、不是急跌保護）",
              f"A|{cx}|r": "對照 A 現實版"}.get(k, k)
        if k.startswith("D|"):
            nm = f"反面：{C['tn'][k[2:4]]}"
        dd.append(f"<tr><th>{e(nm)}</th>" + "".join(f"<td>{cell(v, s)}</td>" for s in SEGN) + f"<td>{v.get('訊號（主窗）', '—')}</td></tr>")
    desc = ("<table><thead><tr><th>只描述（⛔ 不判、不計 N）</th><th>探索</th><th>確認</th><th>主窗</th><th>訊號</th></tr></thead><tbody>" + "".join(dd) + "</tbody></table>"
            "<p class=m>固定天數只描述（seq308）；0050 濾網的角色是擋長空頭、不是急跌保護。</p>")
    # 每年
    yk = [k for k in S["每年事件"][0] if k != "年"]
    years = ("<table><thead><tr><th>年</th>" + "".join(f"<th>{e(k)}</th>" for k in yk) + "</tr></thead><tbody>"
             + "".join(f"<tr><th>{r['年']}</th>" + "".join(f"<td>{r[k]}</td>" for k in yk) + "</tr>" for r in S["每年事件"]) + "</tbody></table>")
    yr = S["各年"]
    yret = ("<table><thead><tr><th>年</th><th>挑中格</th><th>現實版</th><th>0050</th></tr></thead><tbody>"
            + "".join(f"<tr><th>{k}</th><td>{_p(yr['策略'][k])}</td><td>{_p(yr['策略現實版'][k])}</td><td>{_p(yr['0050'][k])}</td></tr>" for k in yr["策略"]) + "</tbody></table>")
    def fv(x):
        if isinstance(x, bool):
            return "是" if x else "否"
        if isinstance(x, float):
            return _p(x) if abs(x) <= 5 else _f(x, 2)
        if isinstance(x, list):
            return "、".join(map(str, x)) or "無"
        if isinstance(x, dict):
            return "；".join(f"{k} {fv(v)}" for k, v in x.items())
        return str(x)

    def fp(v):
        if isinstance(v, dict) and "成立" in v:
            st = {True: "成立", False: "不成立", None: "—"}.get(v["成立"], str(v["成立"]))
            return f"<b>{st}</b>（" + "；".join(f"{e(k)} {e(fv(x))}" for k, x in v.items() if k != "成立") + "）"
        if isinstance(v, dict):
            return "；".join(f"{e(k)}：{fp(x)}" for k, x in v.items())
        return e(fv(v))
    prior = "<ul>" + "".join(f"<li>{e(k)}：{fp(v)}</li>" for k, v in S["先驗"].items()) + "</ul><p class=m>先驗是登錄時寫下的猜測，只對照、不影響判定。</p>"
    vf = S["meta"]["同一事件集"]
    notes = ("<ul>"
             f"<li>急跌事件：照急跌錯殺 seq1 原樣重建（10 日還原報酬減同產業中位、當天最低 2%、10 日報酬為負、同檔 20 日只取第一筆；母體 R1；急跌窗內有壞根不算），"
             f"逐筆對它的事件表：main {vf['main']['事件筆數']} 筆、早年 {vf['早年']['事件筆數']} 筆，不同 {vf['main']['事件欄不同'] + vf['早年']['事件欄不同']}；"
             f"出場函式在隔天買時對它的出場不同 {vf['main']['出場函式（e＝t+1）對 X1a／X2 不同'] + vf['早年']['出場函式（e＝t+1）對 X1a／X2 不同']}。⛔ 不再用 F1／F2。</li>"
             "<li>進場檢查（每格、延後假訊號同一套）：急跌前 10 天到進場前一天有重大訊息關鍵字（訴訟、搜索、退票…18 個）不買；進場前一天收盤已回到急跌前（t−10）收盤以上不買；"
             "急跌後到進場之間有壞根不進。</li>"
             "<li>出場：X1 收盤回到急跌前收盤 ⇒ 修復，或進場後才公布的月營收年增 ≤ 0 ⇒ 轉壞，隔天開盤賣；X2 從持有期最高收盤回落 20% 隔天開盤賣；⛔ 不設最長天數。"
             "持有中遇壞根（缺口 ≥ 5 日等，seq335 全線規則）⇒ 壞根前一根收盤強制賣。</li>"
             "<li>最多 10 檔等權、候選多於空位抽籤（200 顆報中位）；GATE_V2 開、含已下市；月營收 2026-01 期起次月 15 日後才用。</li>"
             "<li>現實版：每邊另加 0.3%、平方根衝擊（50 萬資金）、一字漲停買不到、一字跌停賣不掉、停牌買不到、進出用當日均價。</li>"
             + (f"<li>獨立查核（--check，另一支程式自己讀 csv 重算抽樣）：總不同 {ckj.get('總不同', '—')}（{e(json.dumps(ckj.get('摘要', {}), ensure_ascii=False))[:300]}）。</li>" if ckj else "")
             + f"<li>補讀法寫死 {e(S['meta']['補讀法寫死'])}；執行 {e(S['meta']['run'])}；資料 tw-stock-data {S['meta']['tw-stock-data'][:10]}、價量快照 edc6f8002f；"
             f"程式 backtest/researchCrashExt.py；結果 backtest/resultsCrashExt/{e(C['name'])}/。補讀法全文在程式開頭 docstring（K1～K15）。</li></ul>")
    doc = (f"<!doctype html><html lang=zh-Hant><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>{e(C['name'])}</title>"
           f"<style>{CSS}</style></head><body><h1>{e(C['title'])}</h1>"
           f"<p class=m>{e(C['reg'])}（sha {C['sha']}；裁定 seq336 §二、N_組合 ＋1；同批急跌事件第 {C['nth']} 次切分 ⇒ 標籤最多暫定）｜回測線</p>"
           + lead + "<h2>和 0050、對照 A 比</h2>" + main_t + "<h2>條件有沒有用：對照 A 與延後假訊號</h2>" + ab + "<h2>退化檢查（先寫才算報酬）</h2>" + deg
           + "<h2>必報</h2>" + must + "<h2>描述（不判）</h2>" + desc + "<h2>各年報酬（挑中格）</h2>" + yret + "<h2>每年急跌事件與本件成立數</h2>" + years
           + "<h2>先驗對照</h2>" + prior + "<h2>怎麼算的</h2>" + notes
           + f"<p class=m>產出 {now_tpe()}（台北）。⛔ 不是買賣建議。</p></body></html>")
    p = os.path.join(OUT, f"{C['name']}.html")
    open(p, "w", encoding="utf-8").write(doc)
    print("寫出", p)


def main():
    global OUTROOT
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["run", "page", "exits"])
    ap.add_argument("--smoke", action="store_true", help="冒煙測試：輸出改到 ~/crashextwork/smoke（數字不是本件結果）")
    ap.add_argument("--case", required=True, help="rev／stop／inst／margin，逗號分隔或 all")
    ap.add_argument("--procs", type=int, default=4); ap.add_argument("--reps", type=int, default=200); ap.add_argument("--fake", type=int, default=200)
    a = ap.parse_args()
    if a.smoke:
        OUTROOT = os.path.join(WORK, "smoke")
    cs = list(CASES) if a.case == "all" else a.case.split(",")
    for ck in cs:
        {"run": run_case, "exits": dump_exits}[a.cmd](ck, a) if a.cmd != "page" else page(ck)


if __name__ == "__main__":
    main()
