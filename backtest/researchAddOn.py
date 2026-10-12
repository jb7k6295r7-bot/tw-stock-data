# -*- coding: utf-8 -*-
"""PREREG營量營飆持股漲多加碼 seq1（台股策略線登錄 sha fd1a36205bacf2d8，2026-10-12 17:26；裁定 seq341 §四發號 N_組合 ＋1、事後重切、最多暫定；
裁定 seq342 修正（使用者逐字：「同樣的錢拿去買 0050，不用這樣算，這樣很複雜，單純看策略會不會變好就好!」））——回測線計算子代理。
⛔ 只計算：不 commit、不改既有程式與結果夾、引擎 ⛔ 不改；用語「假訊號」；⛔ 不給買賣建議。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchAddOn [--procs 3]
    獨立查核：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchAddOn_check [--procs 3]

⭐ 讀法寫死：TIME（台北，WSL TZ=Asia/Taipei date）；寫死前 ⛔ 沒算任何本件數字（只跑過世界建構與 r0 引擎 eq_sha 探針，確認 ＝ resultsYL_integrate 正式值；
   看過的：登錄全文 seq1、裁定 seq341、seq342、回測 1845 知會、既有程式 researchStopRule／researchYL_integrate／researchCrashOversold／researchRevLimitUp／
   researchEarlyOTC_rerun／early_data reduce_v2；⚠ 回測線看過營量 v1／營飆 v1 各段的年化與回落（seq2 停用條件、整合件），⛔ 沒看過任何「加碼」輸出）

═══ 讀法（U 標；登錄沒寫清楚、執行者補的都在這裡）═══
 U0 判定只有一題（seq342 以最新指示為準，登錄 §三 的 0050 臂撤回）：營量、營飆各自「加碼版」對「原策略」有沒有變好；
    變好 ＝ 加碼版年化 ＞ 原策略年化 且 加碼版 年化÷|回落| ≥ 原策略；探索 2017-03-02～2021-12-30、確認 2022-01-03～2026-08-24 兩段都要；
    營飆 ＝ 200 顆中位（年化中位、回落中位、比值 ＝ 年化中位 ÷ |回落中位|，同 researchYL_integrate）；另報「逐顆變好」的顆數比例（描述）
    ⛔ 0050 同額臂不算；隨機加碼另一檔 ＝ 描述（⛔ 不進判定）；早年 2005-02～2014-12 ＝ 描述並報
    與登錄衝突處（以 seq342 為準）：登錄 §三 判定 ①（逐筆對 0050 配對差）、②（對原策略＋同額 0050）、B0050 ⇒ 全部撤；先驗 ① 改讀成「加碼版是否變好」
 U1 原策略（⛔ 不改引擎、一字不動）：營量 v1 ＝ IG.eng(W, "H60·S20·無·relvol", 0)；營飆 v1 ＝ IG.eng(W, "H120·S10·閘·抽籤", r)，r ＝ 0～199
    主世界 ＝ researchYL_integrate.main_world（＝ researchT1fix.build_ctx(True)：AND T1、停止交易強制出場開）；
    早年 ＝ researchYL_integrate.early_world（上市＋上櫃 eotc_f65bb03e11、AND T1＋R8 減資截斷）＝ 營量營飆早年既有規則
    閘：每條權益 eq_sha ＝ backtest/resultsYL_integrate/seeds.csv.gz 同世界、同格、同 r
    ⚠ 早年 reduce_v2（seq341 §六「新件一律用 v2」）的讀法：reduce_v2 版面只有「上市本體」（~/earlydata/950ad26e12/reduce_v2），沒有營量營飆早年用的
      上市＋上櫃版面 ⇒ 原策略早年照既有版面（換版面 ＝ 改原策略早年結果，⛔ 不做）；reduce_v2 的減資事件（上市官方＋上市偵測 2004～2010＋上櫃早年偵測，
      ＋ 未解釋跳動 22 筆）全部併入早年「壞根」集合 ⇒ 用在 g、q(h) 的窗剔除與加碼部位強制賣（U4）；並報原策略早年持有期跨到這些事件（未截斷）的筆數
 U2 加碼條件（登錄 §一 寫死）：持股 j（買進日 tb、進場價 ep ＝ 引擎 audit 的 px ＝ tb 開盤還原價）；決策日 t（收盤）：h ＝ t − tb ＋ 1（日曆交易日位置，進場那根算第 1 根）
    g ＝ closes[t] ÷ ep − 1（引擎同一份還原收盤）；h ＜ 10 不判；t 那天該股要有 K 棒；(tb, t] 內有壞根 ⇒ 不判（之後也不再判：窗已含壞根）
    q(h, t) ＝ 當天 R1 母體（U3）裡「有 K 棒、C[t−h] 有值、(t−h, t] 沒有壞根」的股票 C[t] ÷ C[t−h] − 1 的分布；有效檔數 ＜ 20 ⇒ 不判
    A1：g ≥ np.percentile(·, 95)（線性內插）；A2：g ≥ 第 99 百分位
    成立 ⇒ 次一交易日 ta ＝ t＋1 開盤加碼；要 ta ≤ 原持股的出場根（xbar）；ta 沒有有效開盤 ⇒ 當天不加、之後照常再判；ta 是壞根 ⇒ 不加且不再判
    每筆持股最多 1 次；加碼金額 ＝ 該筆原始買進金額（audit amt）；加碼的錢另外撥（U5），⛔ 不動策略內其他持股、⛔ 不擠空位
    xbar：正常出場 ＝ 原出場根（第 H 根收盤；audit 賣出日 ＝ 訊號列 xpos）；停止交易強制出場 ＝ L（最後有效收盤根，賣出記在 L＋1、用 L 收盤）；
      資料尾仍持有（T1 補回列）＝ 墊根位置（無賣出）
 U3 R1 母體（seq321 §五、登錄 §一）：每日「有 K 棒 ∧ pit_valid ∧ amt20 有值」（四碼、首碼 1～9、非 91xx、UG.gate3 GATE_V2 開 ⇒ 排除 -DR、創新板；⭐ 不排金融）
    依 amt20（含當日最近 20 根有效 K 棒原始成交金額平均）由大到小前 ⌈X × 檔數⌉（同值依代號序）；
    X ＝ 主世界 2016-01-04 上述母體中 amt20 ≥ 5,000 萬的檔數 ÷ 同日母體檔數（固定；早年段沿用同一個 X；同 researchCrashOversold K3 寫法，差在本件不排金融）
    矩陣取自 researchRevLimitUp.World 快取 ~/rluwork/world_{main,early}.pkl（GATE_V2 開建、唯讀；main ＝ rerun17 H2D、early ＝ eotc_f65bb03e11 ＝ 本件同兩個版面）
    閘：持股股票的快取收盤 vs 世界 closes 相對差 ≤ 1e−6；快取沒有的持股股票（例 6854）⇒ 現場 D.load_stock＋BARR.bad_part 補 K 棒與壞根（不進母體）
 U4 壞根（seq335 全線：research11.load_bars「缺口 ≥ 5 日即壞根」）：主世界 ＝ ~/crashwork/bad_main.pkl（researchCrashOversold K4：load_bars 壞根 ∪ adj 減資／面額事件日）；
    早年 ＝ bad_early.pkl ∪ R8 事件恢復日（EO.events("O","W_B")）∪ reduce_v2 減資（上市偵測 date、上櫃偵測 resume_day）∪ 未解釋 22 筆 date（日期 ⇒ 該日或之後第一個交易日）
    加碼部位出場（登錄 §二 主臂）：原持股同一天、同一價格（引擎 audit 賣出價、記帳日同引擎）；(ta, xbar] 內有壞根 kb ⇒ kb 前最後一根有效收盤強制賣（當天入帳）
    成本 ＝ 引擎 COST（0.585%、出場一次扣、按買進金額）：入帳 ＝ A × (賣價 ÷ 加碼價 − COST)
 U5 資金讀法（⚠ 登錄沒寫死，兩讀法並列判定；另一個 C 只描述）：加碼子帳戶 K（現金、報酬 0）：每一段段首 a ＝ max(段首, first) 歸零，只算 ta ∈ (a, 段尾] 的加碼；
      加碼在開盤先用 K（前幾日出場入帳的錢），不足才從外部撥入 F；出場入帳加進 K（同日先加碼、後入帳）；W_t ＝ 原權益 E_t ＋ K_t ＋ 加碼部位市值 MV_t
    讀法 A「累計撥入」：分母 ＝ 原資本＋累計撥入，隨撥隨進 ⇒ 時間加權：r_t ＝ W_t ÷ (W_{t−1} ＋ F_t) − 1
    讀法 B「峰值撥入」：段首就預留全段累計撥入總額 I（＝ 子帳戶重用下的累計需要峰值），閒置報酬 0 ⇒ NAV_t ∝ W_t ＋ (I − 累計 F_t)
    讀法 C（描述、⛔ 不判）「撥入即用、出場退回」：r_t ＝ (ΔE_t ＋ 加碼當日損益) ÷ (E_{t−1} ＋ MV_{t−1} ＋ 當日新加碼金額)
    年化、回落 ＝ rerun17.win_metrics 同式（NAV 接在原權益同一陣列的段內位置上）；閘：沒有加碼時三讀法 NAV ＝ 原權益（相對差 ≤ 1e−12）
 U6 退化（seq325：先寫 degeneracy.json 附台北時間，再算任何報酬）：觸發太少 ＝ 探索段實際加碼筆數（營飆 200 顆中位）＜ 20 ⇒ 該格不進挑選；
    兩格都退化 ⇒ 在兩格裡照同規則挑、標「全退化」；確認段加碼筆數 ＜ 20 ⇒ 確認段「樣本不足、不判變好」
 U7 挑格（每策略、每讀法各自）：探索段非退化格中「變好」者；兩格都變好 ⇒ 加碼版比值大者（同 ⇒ 年化大者 ⇒ A1）；都沒變好 ⇒ 取加碼版比值大者、照報「探索段就沒變好」
    判定 ＝ 挑中格在確認段也變好 ⇒「變好（暫定）」（事後重切、最多暫定）；否則「沒有變好」；兩讀法結論不同 ⇒ 標出
 U8 必報（登錄 §三，拿掉 0050）：逐年觸發次數與占持股比例（依買進年；營飆 200 顆平均）、加碼時已持有天數 h 分佈、加碼後到出場的報酬分佈（毛、淨；中位、前 10%（p90）、後 10%（p10））、
    加碼部位一年內先跌 15% 比例（researchRevLimitUp.trade_stats 同式：ta＋1～ta＋250 收盤先 ≤ 0.85×加碼價 或先 ≥ 1.15×；觀察窗不滿 250 根不計）、
    組合層最大回落變化（加碼版 − 原策略）、加碼部位資金占比峰值（MV ÷ W，讀法 A 的 W）、T2 關係（U9）、退化（U6）
 U9 停用條件 T2（seq2 數字：營量 Dmax −34.4%／警戒 −27.5%；營飆 −56.1%／−44.9%）：段 ＝ 主窗、早年（同 seq2 歷史驗算的段）；
    月底（researchStopRule.month_ends）D ＝ NAV ÷ 段首起逐日最高 − 1；報第一個 D ≤ 警戒、D ≤ 停用的月底，原策略 vs 加碼版（A、B）；營飆報逐顆「提早／一樣／延後／新增／消失」
 U10 描述臂（⛔ 不判、不計 N）：加碼部位 ① 從加碼後最高收盤（含加碼日）回落 20% ⇒ 次一個有效開盤先賣（不早於主臂出場才算）；② 固定抱 20、60 根（加碼根算第 1 根、第 H 根有效 K 棒收盤賣；
    途中壞根 ⇒ 壞根前收盤強制；股票停止交易 ⇒ L 收盤、記在 L＋1）；③ 隨機加碼另一檔：每次實際加碼的決策日 t，改從同一條路徑「當天持有、h ≥ 10、(tb, t＋1] 無壞根、
    t＋1 有開盤、g ＜ 該格門檻、還沒被加碼過」的其他持股等機率抽 1 檔加一份（金額 ＝ 該檔原始買進金額、出場照該檔主臂）；沒有候選 ⇒ 該次不加（照報）；
    default_rng([20261012, 世界, 策略, 格, i])；營量 200 抽；營飆 第 i 抽配第 i 顆；p ＝ 隨機版年化 ≥ 實際加碼版年化（營飆取中位）的比例
 結果句必附：「加碼用的是另外的錢；⛔ 不代表該把原策略的錢集中到漲最多的那檔」「營量、營飆已看過結果，本件最多暫定」「加碼版用的錢比原策略多」
   早年另附：「早年含減資假飆股約 0.3%（剩 22 筆未解釋）」；上櫃 2007-07～12 除權息未還原；上櫃減資 2007～2012 為偵測、非官方；2005-01～2007-06 只有上市
輸出 backtest/resultsAddOn/：degeneracy.json（先寫）、AddOn.json、AddOn_main.csv、seeds.csv.gz、triggers.csv.gz、run.log；大檔 ~/addonwork/（世界快取、engine_200.pkl）
── 事後註（寫死之後、照實記；讀法沒改）──
 ① 19:06、19:13 跑過 3 顆煙霧測試（ADD_QUICK，輸出 /tmp/addon_quick，數字不是本件結果）；只修程式錯（win_metrics 回傳三個值）
 ② 19:27 第一次全跑時，前一輪的幾處修補沒有套上（編輯工具沒生效）；19:38 套上後重跑：隨機臂候選改成預先建表（只加速、結果同）、HMAX 少算 1 根、
    壞根前無 K 棒防呆、T2 月底限段內 ⇒ 兩次判定相同；交件數字 ＝ 套修補後這一版
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import pickle
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D                              # noqa: E402
from backtest import research11 as R                        # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402
from backtest import researchYL_integrate as IG             # noqa: E402
from backtest import universe_gate as UG                    # noqa: E402

TIME = "2026-10-12 19:00（台北）"
REG_SHA = "fd1a36205bacf2d8"
MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
OUT = "backtest/resultsAddOn"
WORK = os.path.expanduser("~/addonwork")
RLU_WORK = os.path.expanduser("~/rluwork")
CRASH_WORK = os.path.expanduser("~/crashwork")
EOTC = os.path.expanduser("~/earlydata/eotc_f65bb03e11/otc/data")
V2EXT = os.path.expanduser("~/earlydata/950ad26e12/reduce_ext_b45c9e94dc")
NSEED = 200
NRAND = 200
if os.environ.get("ADD_QUICK"):                                 # 煙霧測試（不是交件）
    NSEED, NRAND, OUT = 3, 3, "/tmp/addon_quick"
STRATS = {"營量": IG.YL, "營飆": IG.YF}
HOF = {"營量": 60, "營飆": 120}
CELLS = {"A1": 95.0, "A2": 99.0}
HMIN, MINPOP, DEG_MIN = 10, 20, 20
LIQ, R1_DAY = 5e7, "2016-01-04"
COST = R.COST
SEGS = {"主": ("探索", "確認", "主窗"), "早年": ("早年",)}
JUDGE = ("探索", "確認")
T2 = {"營量": (-0.344, -0.275), "營飆": (-0.561, -0.449)}
ARMS = ("主臂", "回落20%先賣", "固定20根", "固定60根", "隨機另一檔")
READS = ("A", "B", "C")
RSEED = 20261012
TRAIL = 0.20
WID = {"主": 0, "早年": 1}
SID_ = {"營量": 0, "營飆": 1}
CID = {"A1": 0, "A2": 1}
SENT = ["加碼用的是另外的錢；⛔ 不代表該把原策略的錢集中到漲最多的那檔", "營量、營飆已看過結果，本件最多暫定", "加碼版用的錢比原策略多"]
NOTE_EARLY = ["早年含減資假飆股約 0.3%（剩 22 筆未解釋）", "上櫃 2007-07～12 除權息未還原；上櫃減資 2007～2012 為偵測、非官方；2005-01～2007-06 只有上市"]
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


def seeds_of(sn):
    return [0] if sn == "營量" else list(range(NSEED))


# ═════════════ 世界（正式，快取）═════════════
def worlds(log, procs):
    os.makedirs(WORK, exist_ok=True)
    out = {}
    for wn in ("主", "早年"):
        cp = os.path.join(WORK, f"world_{wn}.pkl")
        if os.path.exists(cp):
            out[wn] = pickle.load(open(cp, "rb")); log(f"[世界 {wn}] 讀快取 {cp}"); continue
        if wn == "主":
            W, g = IG.main_world(log); bench = np.asarray(RR._G["bench"], float).copy(); data = RR.H2D; EV = None
        else:
            from backtest import researchEarlyOTC_rerun as EO
            W, g = IG.early_world(log, procs); bench = np.asarray(RR.load_bench(W["cal"]), float); data = EOTC
            EV = EO.events("O", "W_B", IG.MSHA)
        Z = {k: W[k] for k in ("name", "cal", "w0", "w1", "closes", "opens", "NP", "SF", "segp", "SIG")}
        Z.update(gate=g, bench=bench, data=data, EV=EV, uni=dict(W["uni"]))
        pickle.dump(Z, open(cp, "wb"), protocol=5)
        out[wn] = Z
    return out


def job_eng(a):
    wn, sn, r = a
    o, au = IG.eng(_G["W"][wn], STRATS[sn], r)
    eq = np.asarray(o["equity"], float)
    auc = [(int(x["t"]), x["side"], x["sid"], float(x["amt"]), float(x.get("cost", 0.0)), float(x["px"])) for x in au]
    return wn, sn, r, eq, int(o["first"]), int(o["end"]), auc


def run_engines(WS, procs, log):
    cp = os.path.join(WORK, f"engine_{NSEED}.pkl")
    _G["W"] = WS
    jobs = [(wn, sn, r) for wn in ("主", "早年") for sn in STRATS for r in seeds_of(sn)]
    with Pool(procs) as pool:
        res = pool.map(job_eng, jobs, chunksize=4)
    ref = pd.read_csv("backtest/resultsYL_integrate/seeds.csv.gz", dtype={"eq_sha": str}, usecols=["世界", "格", "r", "eq_sha"])
    REF = {(w, k, int(r)): s for w, k, r, s in zip(ref["世界"], ref["格"], ref["r"], ref["eq_sha"])}
    bad = sum(int(IG.sha(eq) != REF[(wn, STRATS[sn], r)]) for wn, sn, r, eq, *_ in res)
    ENG = {(wn, sn, r): {"eq": eq, "first": f, "end": e, "au": au} for wn, sn, r, eq, f, e, au in res}
    pickle.dump(ENG, open(cp, "wb"), protocol=5)
    log(f"[引擎] {len(res)} 條｜eq_sha ≠ resultsYL_integrate：{bad}｜存 {cp}")
    if bad:
        raise SystemExit("⛔ eq_sha 閘不過")
    return ENG, bad


# ═════════════ 母體、壞根、門檻 ═════════════
def date_pos(cal, d):
    k = int(cal.searchsorted(pd.Timestamp(d)))
    return k if k < len(cal) else None


def early_extra_bad(W, log):
    """早年另加壞根：R8 事件恢復日、reduce_v2 減資（上市偵測、上櫃偵測）、未解釋 22 筆。⇒ {sid: set(pos)}, 計數。"""
    cal = W["cal"]; X = {}; cnt = {}

    def add(src, sids, dates):
        n = 0
        for s, d in zip(sids, dates):
            s = str(s).strip(); d = str(d).strip()
            if not d:
                continue
            k = date_pos(cal, d)
            if k is None:
                continue
            X.setdefault(s, set()).add(k); n += 1
        cnt[src] = n
    EV = W["EV"]
    add("R8 事件恢復日（官方＋上市偵測＋上櫃）", EV["stock_id"], EV["e"])
    t = pd.read_csv(os.path.join(V2EXT, "twse_reduce_detected_2004_2010.csv"), dtype=str, keep_default_na=False)
    add("reduce_v2 上市偵測減資 2004～2010", t["stock_id"], t["date"])
    o = pd.read_csv(os.path.join(V2EXT, "otc_reduce_detected_2007_2012.csv"), dtype=str, keep_default_na=False)
    o = o[(o["shares_down"].str.strip() == "1") & (o["exright_in_gap"].str.strip() == "0")]
    add("reduce_v2 上櫃早年偵測減資（shares_down＝1∧exright_in_gap＝0）", o["stock_id"], o["resume_day"])
    u = pd.read_csv(os.path.join(V2EXT, "twse_jump_unexplained_2004_2010.csv"), dtype=str, keep_default_na=False)
    add("reduce_v2 未解釋跳動 22 筆", u["stock_id"], u["date"])
    man = json.load(open(os.path.join(V2EXT, "manifest.json"), encoding="utf-8"))
    cnt["reduce_ext manifest ext_sha"] = man.get("ext_sha")
    log(f"[早年另加壞根] {cnt}")
    return X, cnt


def extra_stock(sid, mk, data, cal):
    """快取沒有的持股股票：K 棒（收盤有值）與壞根（BARR.bad_part ∪ adj 減資／面額）。"""
    from backtest import researchBARR as BARR
    D.DATA = data
    st = D.load_stock(sid, mk, cal)
    bar = np.isfinite(st.df["close"].to_numpy(float)) if st is not None else np.zeros(len(cal), bool)
    bad = BARR.bad_part(sid, data, cal).copy()
    adj = D.load_adj(sid) if os.path.exists(os.path.join(data, "stocks", f"{sid}.csv")) else None
    if adj is not None and len(adj) and "event" in adj:
        for d, e in zip(adj["date"], adj["event"].astype(str)):
            if e in ("reduce", "parvalue"):
                k = int(cal.searchsorted(d))
                if k < len(cal):
                    bad[k] = True
    return bar, bad


def market(wn, W, X, log, hold_sids):
    part = "main" if wn == "主" else "early"
    Z = pickle.load(open(os.path.join(RLU_WORK, f"world_{part}.pkl"), "rb"))
    sids = Z["sids"]; ix = {s: i for i, s in enumerate(sids)}
    C, BAR, A20, PV = Z["c"], Z["bar"], Z["a20"], Z["pv"]
    S, n = C.shape
    if n != len(W["cal"]):
        raise SystemExit(f"⛔ {wn} 快取日曆長 {n} ≠ 世界 {len(W['cal'])}")
    MKT = BAR & PV & np.isfinite(A20)
    B = pickle.load(open(os.path.join(CRASH_WORK, f"bad_{part}.pkl"), "rb"))
    BAD = np.zeros((S, n), bool)
    for i, s in enumerate(sids):
        a, b = B[s]; BAD[i, a] = True; BAD[i, b] = True
    info = {"快取": f"~/rluwork/world_{part}.pkl", "檔數": S, "壞根股日（bad_{part}.pkl）": int(BAD.sum())}
    if wn == "早年":
        EX, cnt = early_extra_bad(W, log)
        n0 = int(BAD.sum())
        for s, ks in EX.items():
            if s in ix:
                BAD[ix[s], sorted(ks)] = True
        info["早年另加壞根來源"] = cnt; info["早年另加後壞根股日"] = int(BAD.sum()); info["早年另加新增股日"] = int(BAD.sum()) - n0
        _G[("EX", wn)] = EX
    if X is None:
        d = int(W["cal"].searchsorted(pd.Timestamp(R1_DAY))); assert str(W["cal"][d].date()) == R1_DAY
        nu = int((MKT[:, d] & (A20[:, d] >= LIQ)).sum()); nm = int(MKT[:, d].sum()); X = nu / nm
        info["R1 X"] = {"X": X, "2016-01-04 amt20≥5000萬": nu, "同日母體": nm}
        log(f"[R1] X ＝ {nu}／{nm} ＝ {X:.6f}")
    R1m = np.zeros((S, n), bool)
    for d in range(n):
        ii = np.flatnonzero(MKT[:, d])
        if len(ii):
            R1m[ii[np.argsort(-A20[ii, d], kind="stable")[:int(np.ceil(X * len(ii)))]], d] = True
    info["R1 每日檔數（中位）"] = float(np.median(R1m.sum(0)[R1m.sum(0) > 0]))
    # 持股股票：K 棒、壞根、收盤閘
    NP = W["NP"]; HB = {}; md = 0.0; extra = []
    for s in hold_sids:
        if s in ix:
            bar = BAR[ix[s]]; bad = BAD[ix[s]]
            cl = W["closes"][s][:n].astype(float); ok = np.isfinite(cl) & np.isfinite(C[ix[s]])
            if ok.any():
                md = max(md, float(np.max(np.abs(cl[ok] / C[ix[s]][ok] - 1.0))))
        else:
            bar, bad = extra_stock(s, W["uni"].get(s, "twse"), W["data"], W["cal"]); extra.append(s)
            if wn == "早年" and s in _G.get(("EX", wn), {}):
                bad = bad.copy(); bad[sorted(_G[("EX", wn)][s])] = True
        HB[s] = (np.r_[bar, np.zeros(NP - n, bool)], np.r_[bad, np.zeros(NP - n, bool)])
    info["持股股票收盤 vs 快取 最大相對差"] = md; info["快取沒有、現場補的持股股票"] = extra
    if md > 1e-6:
        raise SystemExit(f"⛔ {wn} 收盤閘 {md}")
    log(f"[母體 {wn}] {info}")
    return {"C": C, "BAR": BAR, "BAD": BAD, "R1": R1m, "n": n, "S": S}, HB, X, info


def thresholds(M, HMAX, t_lo, log, wn):
    C, BAR, BAD, R1m, n, S = M["C"], M["BAR"], M["BAD"], M["R1"], M["n"], M["S"]
    CB = np.zeros((S, n + 1), np.int32); CB[:, 1:] = np.cumsum(BAD, axis=1)
    okC = np.isfinite(C)
    Q = {c: np.full((HMAX + 1, n), np.nan) for c in CELLS}
    NPOP = np.zeros((HMAX + 1, n), np.int32)
    t0 = time.time()
    for h in range(HMIN, HMAX + 1):
        t = np.arange(max(h, t_lo), n)
        if not len(t):
            continue
        den = C[:, t - h]; num = C[:, t]
        nb = CB[:, t + 1] - CB[:, t - h + 1]
        m = R1m[:, t] & BAR[:, t] & okC[:, t - h] & (nb == 0)
        with np.errstate(invalid="ignore", divide="ignore"):
            Rr = np.where(m, num / den - 1.0, np.nan)
        cnt = np.isfinite(Rr).sum(0)
        NPOP[h, t] = cnt
        ok = cnt >= MINPOP
        if ok.any():
            P = np.nanpercentile(Rr[:, ok], [CELLS["A1"], CELLS["A2"]], axis=0)
            Q["A1"][h, t[ok]] = P[0]; Q["A2"][h, t[ok]] = P[1]
        if h % 20 == 0:
            log(f"[門檻 {wn}] h＝{h}｜{time.time() - t0:.0f}s")
    return Q, NPOP


# ═════════════ 持股、觸發、出場 ═════════════
def holdings(au):
    """audit ⇒ [sid, tb, amt, ep, ts, pxs]（同股先進先出；賣出 audit 的 px ＝ ep × (1＋gross)）。"""
    op = {}; H = []
    for (t, side, sid, amt, cost, px) in au:
        if side == "buy":
            op.setdefault(sid, []).append(len(H)); H.append([sid, t, amt, px, None, None])
        else:
            j = op[sid].pop(0); H[j][4] = t; H[j][5] = px
    return H


def first_true(a, lo, hi):
    """a[lo:hi+1] 第一個 True 的位置（絕對）或 None。"""
    if hi < lo:
        return None
    w = np.flatnonzero(a[lo:hi + 1])
    return lo + int(w[0]) if len(w) else None


def main_exit(hk, ta):
    """加碼部位主臂出場 ⇒ (入帳日, 價, 價所在根, 種類)；入帳日 None ＝ 資料尾仍持有。"""
    I = _G["HI"][hk]; bar, bad = I["bar"], I["bad"]; cl = I["cl"]
    kb = first_true(bad, ta + 1, I["xbar"])
    if kb is not None:
        w_ = np.flatnonzero(bar[ta:kb]); vb = (int(w_[-1]) + ta) if len(w_) else ta
        return vb, float(cl[vb]), vb, "壞根前收盤強制"
    if I["ts"] is None:
        return None, None, len(cl) - 1, "資料尾仍持有"
    return I["ts"], I["pxs"], I["xbar"], ("同原持股（停止交易強制）" if I["sf"] else "同原持股")


def trail_exit(hk, ta, mx):
    I = _G["HI"][hk]; bar = I["bar"]; cl = I["cl"]; op = I["op"]
    md, mpx, mbar, mk = mx
    pk = -np.inf
    for u in range(ta, mbar):
        if not bar[u]:
            continue
        c = float(cl[u]); pk = max(pk, c)
        if c <= (1.0 - TRAIL) * pk:
            for d in range(u + 1, mbar + 1):
                if bar[d] and np.isfinite(op[d]) and op[d] > 0:
                    return d, float(op[d]), d, "回落20%"
            break
    return mx


def fixed_exit(hk, ta, H):
    I = _G["HI"][hk]; bar, bad = I["bar"], I["bad"]; cl = I["cl"]
    vb = np.flatnonzero(bar[ta:]) + ta
    tgt = int(vb[H - 1]) if len(vb) >= H else None
    hi = tgt if tgt is not None else len(cl) - 1
    kb = first_true(bad, ta + 1, hi)
    if kb is not None:
        w_ = np.flatnonzero(bar[ta:kb]); v = (int(w_[-1]) + ta) if len(w_) else ta
        return v, float(cl[v]), v, "壞根前收盤強制"
    if tgt is not None:
        return tgt, float(cl[tgt]), tgt, f"固定{H}根"
    L = I["L"]
    if L is not None and L + 1 < len(cl) - 1:
        return L + 1, float(cl[L]), L, "停止交易強制"
    return None, None, len(cl) - 1, "資料尾仍持有"


def hold_info(wn, sn, W, HB, sid, tb, ep, ts, pxs, Q):
    """唯一持股的觸發（兩格）與各出場臂。"""
    H = HOF[sn]
    cl = W["closes"][sid]; op = W["opens"][sid]; bar, bad = HB[sid]
    xpos = _G["XPOS"][wn][H].get((sid, tb))
    sf = False; L = W["SF"].get(sid)
    if ts is None:
        xbar = len(cl) - 1
    elif xpos is not None and ts == xpos:
        xbar = ts
    elif xpos is not None and ts < xpos and L is not None and ts == L + 1:
        xbar = L; sf = True
    else:
        raise SystemExit(f"⛔ 出場對不上 {wn} {sn} {sid} tb{tb} ts{ts} xpos{xpos} L{L}")
    I = {"sid": sid, "tb": tb, "ep": ep, "ts": ts, "pxs": pxs, "xbar": xbar, "sf": sf, "L": L, "cl": cl, "op": op, "bar": bar, "bad": bad}
    # 原持股跨壞根（描述：主世界 adj 減資／面額、早年 reduce_v2 等）
    I["orig_cross_bad"] = first_true(bad, tb + 1, min(xbar, len(cl) - 1)) is not None
    # 逐日 g、門檻、可判
    T = np.arange(tb + HMIN - 1, xbar)                      # t ∈ [tb+9, xbar−1]
    I["T"] = T
    n = Q["A1"].shape[1]
    trig = {}
    elig = {}
    if len(T):
        badc = np.cumsum(bad[tb + 1:xbar + 1])               # badc[k] ＝ (tb, tb+1+k] 的壞根數
        nb_t = badc[T - tb - 1]                              # (tb, t]
        nb_a = badc[T - tb]                                  # (tb, t+1]
        h = T - tb + 1
        g = cl[T].astype(float) / ep - 1.0
        barT = bar[T]
        opa = op[T + 1].astype(float); opok = np.isfinite(opa) & (opa > 0)
        inT = T < n
        for c in CELLS:
            q = np.full(len(T), np.nan)
            q[inT] = Q[c][h[inT], T[inT]]
            judge = barT & (nb_t == 0) & np.isfinite(q)
            hit = judge & (g >= q)
            tr = None; why = "沒觸發"
            for k in np.flatnonzero(hit):
                if nb_a[k] > 0:
                    why = "加碼日是壞根"; break
                if not opok[k]:
                    continue
                tr = {"t": int(T[k]), "h": int(h[k]), "g": float(g[k]), "q": float(q[k]), "ta": int(T[k] + 1), "ep_a": float(opa[k])}
                why = "加碼"; break
            trig[c] = (tr, why)
            elig[c] = judge & (g < q) & (nb_a == 0) & opok          # 隨機臂候選（還沒漲到門檻）
    else:
        for c in CELLS:
            trig[c] = (None, "持有不足 10 根")
            elig[c] = np.zeros(0, bool)
    I["trig"] = trig; I["elig"] = elig
    return I


def addon_pos(hk, ta, ep_a, A, arm):
    if arm == "主臂" or arm == "隨機另一檔":
        mx = main_exit(hk, ta)
    elif arm == "回落20%先賣":
        mx = trail_exit(hk, ta, main_exit(hk, ta))
    else:
        mx = fixed_exit(hk, ta, 20 if arm == "固定20根" else 60)
    sd, px, xb, kind = mx
    return (ta, A, ep_a, hk, sd, px, kind)


def one_year_drop(hk, ta, ep_a):
    cl = _G["HI"][hk]["cl"]; ncal = _G["NCAL"][hk[0]]
    if ta + 250 > ncal - 1:
        return None
    cc = cl[ta + 1:ta + 251].astype(float)
    up = np.flatnonzero(cc >= ep_a * 1.15); dw = np.flatnonzero(cc <= ep_a * 0.85)
    return bool((dw[0] if len(dw) else 999) < (up[0] if len(up) else 999))


# ═════════════ 記帳（U5）═════════════
def account(E, a, y, pos):
    """pos：[(ta, A, ep_a, hk, sd, px, kind)]，只收 ta ∈ (a, y]。⇒ NAV_A、NAV_B、NAV_C（長 y−a+1）與統計。"""
    L = y - a + 1
    MV = np.zeros(L); ADD = np.zeros(L); PROC = np.zeros(L)
    for (ta, A, ep, hk, sd, px, kind) in pos:
        if not (a < ta <= y):
            continue
        cl = _G["HI"][hk]["cl"]
        e2 = min(sd if sd is not None else y + 1, y + 1)
        if e2 > ta:
            MV[ta - a:e2 - a] += A * cl[ta:e2].astype(float) / ep
        ADD[ta - a] += A
        if sd is not None and sd <= y:
            PROC[sd - a] += A * (px / ep - COST)
    K = 0.0; F = np.zeros(L); Kc = np.zeros(L)
    for i in range(1, L):
        if ADD[i] > 0:
            u = min(K, ADD[i]); K -= u; F[i] = ADD[i] - u
        if PROC[i] != 0.0:
            K += PROC[i]
        Kc[i] = K
    Es = np.asarray(E[a:y + 1], float)
    Wt = Es + Kc + MV
    rA = np.ones(L); rA[1:] = Wt[1:] / (Wt[:-1] + F[1:])
    navA = Es[0] * np.cumprod(rA)
    I = float(F.sum()); WB = Wt + (I - np.cumsum(F))
    navB = Es[0] * WB / WB[0]
    rC = np.ones(L)
    rC[1:] = 1.0 + (Es[1:] - Es[:-1] + MV[1:] + PROC[1:] - MV[:-1] - ADD[1:]) / (Es[:-1] + MV[:-1] + ADD[1:])
    navC = Es[0] * np.cumprod(rC)
    st = {"加碼筆數": int(sum(1 for p in pos if a < p[0] <= y)),
          "撥入總額÷段首權益": I / Es[0], "MV÷W峰值": float(np.max(MV / Wt)), "MV÷E峰值": float(np.max(MV / Es))}
    return {"A": navA, "B": navB, "C": navC}, st


def metrics(E, first, end, x, y, a, nav):
    full = np.asarray(E, float).copy(); full[a:a + len(nav)] = nav
    c, m, _ = RR.win_metrics(full, first, end, x, y)
    return c, m


def t2_first(cal, nav, a, y, MEs, thr):
    seg = nav; rm = np.maximum.accumulate(seg); dd = seg / rm - 1.0
    Dm = dd[np.asarray(MEs) - a]
    out = {}
    for nm, v in (("停用", thr[0]), ("警戒", thr[1])):
        k = np.flatnonzero(Dm <= v)
        out[f"第一次{nm}月底"] = str(cal[MEs[k[0]]].date()) if len(k) else None
        out[f"{nm}月底數"] = int(len(k))
    out["月底最深D"] = float(Dm.min()) if len(Dm) else None
    return out


# ═════════════ 每條路徑（pool）═════════════
def path_job(key):
    wn, sn, r = key
    E = _G["ENG"][key]; eq = E["eq"]; first, end = E["first"], E["end"]
    W = _G["WS"][wn]; cal = W["cal"]
    HL = _G["PATHH"][key]                         # [(hk, amt)]
    rows = []; t2rows = []; trade_rows = []
    for c in CELLS:
        # 實際加碼（各臂）
        acts = []
        for hk, amt in HL:
            tr, why = _G["HI"][hk]["trig"][c]
            if tr is not None:
                acts.append((tr["t"], hk, amt, tr))
        acts.sort(key=lambda z: (z[0], z[1][2]))
        POS = {arm: [addon_pos(hk, tr["ta"], tr["ep_a"], amt, arm) for _, hk, amt, tr in acts] for arm in ARMS if arm != "隨機另一檔"}
        # 隨機另一檔（第 r 抽配第 r 顆；營量 200 抽在 r＝0 這條上）
        draws = range(NRAND) if sn == "營量" else [r]
        RPOS = {}
        tset = sorted({t for t, _, _, _ in acts})
        EL = {t: [] for t in tset}
        for hk, amt in HL:
            I = _G["HI"][hk]; T_ = I["T"]
            if not len(T_):
                continue
            el = I["elig"][c]
            for t in tset:
                if T_[0] <= t <= T_[-1] and el[t - T_[0]]:
                    EL[t].append((hk, amt))
        for i in draws:
            rng = np.random.default_rng([RSEED, WID[wn], SID_[sn], CID[c], i])
            used = {hk for _, hk, _, _ in acts}; rp = []; miss = 0
            for t, hk0, amt0, tr in acts:
                cand = [z for z in EL[t] if z[0] not in used]
                if not cand:
                    miss += 1; continue
                hk, amt = cand[int(rng.integers(len(cand)))]
                used.add(hk)
                ta = t + 1; ep_a = float(_G["HI"][hk]["op"][ta])
                rp.append(addon_pos(hk, ta, ep_a, amt, "隨機另一檔"))
            RPOS[i] = (rp, miss)
        for sg in SEGS[wn]:
            x, y = W["segp"][sg]
            a = max(x, first); yy = min(y, end - 1)
            c0, m0, _ = RR.win_metrics(eq, first, end, x, y)
            base = {"世界": wn, "策略": sn, "r": r, "格": c, "段": sg, "原_年化": c0, "原_回落": m0}
            arms = [(arm, POS[arm], None) for arm in POS] + [("隨機另一檔", RPOS[i][0], i) for i in draws]
            for arm, pos, di in arms:
                navs, st = account(eq, a, yy, pos)
                row = dict(base, 臂=arm, 抽=di, **st)
                if arm == "隨機另一檔":
                    row["無候選次數"] = RPOS[di][1]
                for rd in READS:
                    cc, mm = metrics(eq, first, end, x, y, a, navs[rd])
                    row[f"{rd}_年化"] = cc; row[f"{rd}_回落"] = mm
                rows.append(row)
                if arm == "主臂" and sg in ("主窗", "早年"):
                    MEs = [m_ for m_ in _G["ME"][wn] if a <= m_ <= yy]
                    t2 = {"世界": wn, "策略": sn, "r": r, "格": c, "段": sg}
                    for nm, nav in (("原", eq[a:yy + 1]), ("A", navs["A"]), ("B", navs["B"])):
                        for k, v in t2_first(cal, np.asarray(nav, float), a, yy, MEs, T2[sn]).items():
                            t2[f"{nm}_{k}"] = v
                    t2rows.append(t2)
        # 逐筆（主臂、全窗）
        for (t, hk, amt, tr), p in zip(acts, POS["主臂"]):
            ta, A, ep_a, _, sd, px, kind = p
            g_a = (px / ep_a - 1.0) if px is not None else float(_G["HI"][hk]["cl"][-1]) / ep_a - 1.0
            trade_rows.append({"世界": wn, "策略": sn, "r": r, "格": c, "sid": hk[2], "tb": hk[3], "t": t, "ta": ta, "h": tr["h"], "g": tr["g"], "q": tr["q"],
                               "加碼價": ep_a, "出場日": sd, "出場價": px, "出場種類": kind, "毛報酬": g_a, "淨報酬": g_a - COST,
                               "一年內先跌15%": one_year_drop(hk, ta, ep_a), "買進年": int(cal[hk[3]].year), "加碼年": int(cal[min(ta, len(cal) - 1)].year)})
    return rows, t2rows, trade_rows


# ═════════════ 彙總工具 ═════════════
def q3(v):
    v = np.asarray([x for x in v if x is not None and np.isfinite(x)], float)
    if not len(v):
        return {"n": 0}
    return {"n": int(len(v)), "中位": float(np.median(v)), "p10": float(np.quantile(v, .1)), "p90": float(np.quantile(v, .9)), "平均": float(v.mean())}


def ratio(c, m):
    return c / abs(m) if (m is not None and np.isfinite(m) and m != 0 and np.isfinite(c)) else np.nan


def better(ca, ma, co, mo):
    return bool(ca > co and ratio(ca, ma) >= ratio(co, mo))


def run(a, log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    regf = reg_check(); log(f"[登錄] sha {REG_SHA} ✓ {regf}")
    WS = worlds(log, a.procs)
    gates = {}
    for wn, W in WS.items():
        gates.update(W["gate"])
    ENG, bad = run_engines(WS, a.procs, log)
    gates["eq_sha ≠ resultsYL_integrate（條數）"] = bad
    UG.set_gate_v2(True)                                  # seq296；本件新建的只有 R1 母體（快取為 GATE_V2 開建）
    # 持股
    PATHH = {}; RAW = {}
    for key, E in ENG.items():
        RAW[key] = holdings(E["au"])
    XPOS = {}
    for wn, W in WS.items():
        base = W["SIG"][False]
        XPOS[wn] = {H: {(s, int(e)): int(x) for s, e, x in zip(base["sid"], base["entry_pos"], base[f"xpos_H{H}"])} for H in (60, 120)}
    _G["XPOS"] = XPOS
    # 母體、門檻、唯一持股
    HI = {}; X = None; MINFO = {}; Qs = {}
    for wn in ("主", "早年"):
        W = WS[wn]
        uh = {}
        for (w_, sn, r), Hs in RAW.items():
            if w_ != wn:
                continue
            for sid, tb, amt, ep, ts, pxs in Hs:
                hk = (wn, sn, sid, tb)
                if hk in uh and (uh[hk][0] != ep or uh[hk][1] != ts or uh[hk][2] != pxs):
                    raise SystemExit(f"⛔ 同一筆持股在不同種子出場不同 {hk}")
                uh[hk] = (ep, ts, pxs)
        hold_sids = sorted({hk[2] for hk in uh})
        M, HB, X, info = market(wn, W, X, log, hold_sids)
        MINFO[wn] = info
        HMAX = max(max(min(_xb(W, hk, v), len(W["cal"])) - hk[3] for hk, v in uh.items()), HMIN)
        t_lo = min(hk[3] for hk in uh) + HMIN - 1
        log(f"[{wn}] 唯一持股 {len(uh)}｜HMAX {HMAX}｜t_lo {t_lo}")
        Q, NPOP = thresholds(M, HMAX, t_lo, log, wn)
        Qs[wn] = (Q, NPOP)
        for hk, (ep, ts, pxs) in uh.items():
            HI[hk] = hold_info(wn, hk[1], W, HB, hk[2], hk[3], ep, ts, pxs, Q)
        del M
    _G["HI"] = HI
    _G["NCAL"] = {wn: len(W["cal"]) for wn, W in WS.items()}
    for key, Hs in RAW.items():
        PATHH[key] = [((key[0], key[1], sid, tb), amt) for sid, tb, amt, ep, ts, pxs in Hs]
    # 觸發清單（唯一持股）
    TR = []
    for hk, I in HI.items():
        for c in CELLS:
            tr, why = I["trig"][c]
            TR.append({"世界": hk[0], "策略": hk[1], "sid": hk[2], "tb": hk[3], "格": c, "結果": why, "xbar": I["xbar"], "停止交易強制": I["sf"],
                       "原持股跨壞根": I["orig_cross_bad"], **({k: tr[k] for k in ("t", "h", "g", "q", "ta", "ep_a")} if tr else {})})
    TR = pd.DataFrame(TR).sort_values(["世界", "策略", "格", "sid", "tb"]).reset_index(drop=True)
    TR.to_csv(os.path.join(OUT, "triggers.csv.gz"), index=False, float_format="%.17g")
    log(f"[觸發] 唯一持股×格 {len(TR)}｜結果 {TR.groupby(['世界', '策略', '格'])['結果'].value_counts().to_dict()}")
    # ── 退化（U6）：先寫 degeneracy.json（不含任何報酬）──
    DG = {"寫入時間": now_tpe() + "（台北）", "說明": "⭐ 本檔在彙總任何報酬之前寫入（U6、裁定 seq325）；退化 ＝ 探索段實際加碼筆數（營飆 200 顆中位）＜ 20 ⇒ 不進挑選；確認段 ＜ 20 ⇒ 不判變好",
          "格": {}}
    for sn in STRATS:
        for c in CELLS:
            d = {}
            for wn in ("主", "早年"):
                W = WS[wn]
                for sg in SEGS[wn]:
                    x, y = W["segp"][sg]; cnts = []
                    for r in seeds_of(sn):
                        E = ENG[(wn, sn, r)]; a_ = max(x, E["first"]); y_ = min(y, E["end"] - 1)
                        n_ = 0
                        for hk, amt in PATHH[(wn, sn, r)]:
                            tr = HI[hk]["trig"][c][0]
                            if tr is not None and a_ < tr["ta"] <= y_:
                                n_ += 1
                        cnts.append(n_)
                    d[sg] = {"加碼筆數（中位）": float(np.median(cnts)), "p10": float(np.quantile(cnts, .1)), "p90": float(np.quantile(cnts, .9))}
            d["退化（探索 ＜ 20）"] = bool(d["探索"]["加碼筆數（中位）"] < DEG_MIN)
            d["確認段樣本不足（＜ 20）"] = bool(d["確認"]["加碼筆數（中位）"] < DEG_MIN)
            DG["格"][f"{sn}·{c}"] = d
    json.dump(DG, open(os.path.join(OUT, "degeneracy.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[退化] 已寫 degeneracy.json：{ {k: (v['探索']['加碼筆數（中位）'], v['確認']['加碼筆數（中位）'], v['退化（探索 ＜ 20）']) for k, v in DG['格'].items()} }")
    # ── 記帳 ──
    from backtest import researchStopRule as SR
    _G["ME"] = {wn: SR.month_ends(W["cal"], W["w0"], W["w1"]) for wn, W in WS.items()}
    _G["ENG"] = ENG; _G["WS"] = WS; _G["PATHH"] = PATHH
    # 閘：空加碼時 NAV ＝ 原權益
    g0 = 0.0
    for key in [("主", "營量", 0), ("早年", "營飆", 0)]:
        E = ENG[key]; W = WS[key[0]]
        for sg in SEGS[key[0]]:
            x, y = W["segp"][sg]; a_ = max(x, E["first"]); y_ = min(y, E["end"] - 1)
            navs, _ = account(E["eq"], a_, y_, [])
            for rd in READS:
                g0 = max(g0, float(np.max(np.abs(navs[rd] / E["eq"][a_:y_ + 1] - 1.0))))
    gates["空加碼 NAV vs 原權益 最大相對差"] = g0
    if g0 > 1e-12:
        raise SystemExit(f"⛔ 空加碼閘 {g0}")
    keys = sorted(ENG)
    with Pool(a.procs) as pool:
        res = pool.map(path_job, keys, chunksize=2)
    SE = pd.DataFrame([r_ for rr, _, _ in res for r_ in rr])
    T2R = pd.DataFrame([r_ for _, rr, _ in res for r_ in rr])
    TRD = pd.DataFrame([r_ for _, _, rr in res for r_ in rr])
    SE.to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False, float_format="%.17g")
    log(f"[記帳] {len(SE)} 列｜{time.time() - T0:.0f}s")
    # ── 主表 ──
    MAIN = []; SUM = {}
    for sn in STRATS:
        for c in CELLS:
            for wn in ("主", "早年"):
                for sg in SEGS[wn]:
                    g = SE[(SE["世界"] == wn) & (SE["策略"] == sn) & (SE["格"] == c) & (SE["段"] == sg) & (SE["臂"] == "主臂")]
                    co, mo = float(g["原_年化"].median()), float(g["原_回落"].median())
                    for rd in READS:
                        ca, ma = float(g[f"{rd}_年化"].median()), float(g[f"{rd}_回落"].median())
                        per = [better(x1, x2, x3, x4) for x1, x2, x3, x4 in zip(g[f"{rd}_年化"], g[f"{rd}_回落"], g["原_年化"], g["原_回落"])]
                        MAIN.append({"策略": sn, "格": c, "段": sg, "讀法": rd, "顆數": len(g),
                                     "原_年化": co, "原_回落": mo, "原_比值": ratio(co, mo),
                                     "加碼_年化": ca, "加碼_回落": ma, "加碼_比值": ratio(ca, ma),
                                     "年化差": ca - co, "回落差（加碼−原）": ma - mo, "變好": better(ca, ma, co, mo),
                                     "逐顆變好比例": float(np.mean(per)),
                                     "加碼_年化p10": float(g[f"{rd}_年化"].quantile(.1)), "加碼_年化p90": float(g[f"{rd}_年化"].quantile(.9)),
                                     "加碼_回落p10": float(g[f"{rd}_回落"].quantile(.1)), "加碼_回落p90": float(g[f"{rd}_回落"].quantile(.9)),
                                     "原_年化p10": float(g["原_年化"].quantile(.1)), "原_年化p90": float(g["原_年化"].quantile(.9)),
                                     "加碼筆數中位": float(g["加碼筆數"].median()), "撥入總額÷段首權益中位": float(g["撥入總額÷段首權益"].median()),
                                     "MV÷W峰值中位": float(g["MV÷W峰值"].median())})
    MT = pd.DataFrame(MAIN)
    MT.to_csv(os.path.join(OUT, "AddOn_main.csv"), index=False, float_format="%.10g")
    # ── 挑格與判定 ──
    VER = {}
    for sn in STRATS:
        for rd in ("A", "B"):
            row = lambda c, sg: MT[(MT["策略"] == sn) & (MT["格"] == c) & (MT["段"] == sg) & (MT["讀法"] == rd)].iloc[0]
            nd = [c for c in CELLS if not DG["格"][f"{sn}·{c}"]["退化（探索 ＜ 20）"]]
            alld = not nd
            pool_ = list(CELLS) if alld else nd
            good = [c for c in pool_ if bool(row(c, "探索")["變好"])]
            cand = good if good else pool_
            pick = sorted(cand, key=lambda c: (-row(c, "探索")["加碼_比值"], -row(c, "探索")["加碼_年化"], list(CELLS).index(c)))[0]
            ex, cf = row(pick, "探索"), row(pick, "確認")
            insuff = DG["格"][f"{sn}·{pick}"]["確認段樣本不足（＜ 20）"]
            ok = bool(ex["變好"]) and bool(cf["變好"]) and not insuff
            VER[f"{sn}·{rd}"] = {"挑中格": pick, "全退化": alld, "探索段變好": bool(ex["變好"]), "確認段變好": bool(cf["變好"]), "確認段樣本不足": insuff,
                                 "結論": "變好（暫定）" if ok else ("沒有變好（探索段就沒變好）" if not ex["變好"] else ("確認段樣本不足、不判" if insuff else "沒有變好（確認段沒變好）")),
                                 "探索": {k: ex[k] for k in ("原_年化", "原_回落", "原_比值", "加碼_年化", "加碼_回落", "加碼_比值")},
                                 "確認": {k: cf[k] for k in ("原_年化", "原_回落", "原_比值", "加碼_年化", "加碼_回落", "加碼_比值")}}
        VER[f"{sn}·兩讀法一致"] = VER[f"{sn}·A"]["結論"] == VER[f"{sn}·B"]["結論"] and VER[f"{sn}·A"]["挑中格"] == VER[f"{sn}·B"]["挑中格"]
    log(f"[判定] {json.dumps(VER, ensure_ascii=False, default=float)[:3000]}")
    # ── 描述臂 ──
    DESC = {}
    for sn in STRATS:
        for c in CELLS:
            for wn in ("主", "早年"):
                for sg in SEGS[wn]:
                    g = SE[(SE["世界"] == wn) & (SE["策略"] == sn) & (SE["格"] == c) & (SE["段"] == sg)]
                    m = g[g["臂"] == "主臂"]; d = {}
                    for arm in ARMS:
                        h = g[g["臂"] == arm]
                        dd = {"列數": int(len(h))}
                        for rd in READS:
                            dd[f"{rd}_年化中位"] = float(h[f"{rd}_年化"].median()); dd[f"{rd}_回落中位"] = float(h[f"{rd}_回落"].median())
                        if arm == "隨機另一檔":
                            for rd in READS:
                                ref = float(m[f"{rd}_年化"].median())
                                dd[f"{rd}_p（隨機年化 ≥ 實際加碼版中位）"] = float((h[f"{rd}_年化"] >= ref).mean())
                            dd["無候選次數（中位）"] = float(h["無候選次數"].median()); dd["加碼筆數（中位）"] = float(h["加碼筆數"].median())
                        d[arm] = dd
                    DESC[f"{sn}·{c}·{sg}"] = d
    # ── 必報 ──
    REP = {}
    for sn in STRATS:
        for c in CELLS:
            for wn in ("主", "早年"):
                W = WS[wn]; ns = len(seeds_of(sn))
                t_ = TRD[(TRD["世界"] == wn) & (TRD["策略"] == sn) & (TRD["格"] == c)]
                x0, y0 = W["segp"]["主窗" if wn == "主" else "早年"]
                yr = {}
                for r in seeds_of(sn):
                    for hk, amt in PATHH[(wn, sn, r)]:
                        if not (x0 <= hk[3] <= y0):
                            continue
                        Y = int(W["cal"][hk[3]].year)
                        z = yr.setdefault(Y, [0, 0]); z[0] += 1
                        z[1] += int(HI[hk]["trig"][c][0] is not None)
                tw = t_[(t_["tb"] >= x0) & (t_["tb"] <= y0)]
                rep = {"逐年（依買進年；每顆平均）": {str(Y): {"持股筆": v[0] / ns, "加碼筆": v[1] / ns, "占比": v[1] / v[0] if v[0] else None} for Y, v in sorted(yr.items())},
                       "合計占比": (sum(v[1] for v in yr.values()) / max(sum(v[0] for v in yr.values()), 1)),
                       "加碼時已持有天數 h": q3(tw["h"]),
                       "h 分組占比": {k: float(((tw["h"] >= lo) & (tw["h"] <= hi)).mean()) if len(tw) else None
                                    for k, (lo, hi) in {"10～19": (10, 19), "20～39": (20, 39), "40～59": (40, 59), "60～89": (60, 89), "90～119": (90, 119), "120+": (120, 9999)}.items()},
                       "加碼後到出場報酬（毛）": q3(tw[tw["出場日"].notna()]["毛報酬"]), "加碼後到出場報酬（淨）": q3(tw[tw["出場日"].notna()]["淨報酬"]),
                       "淨報酬 ＞ 0 比例": float((tw[tw["出場日"].notna()]["淨報酬"] > 0).mean()) if len(tw) else None,
                       "出場種類": tw["出場種類"].value_counts().to_dict(),
                       "一年內先跌15%比例": float(tw["一年內先跌15%"].dropna().astype(bool).mean()) if tw["一年內先跌15%"].notna().any() else None,
                       "一年觀察窗滿的筆數": int(tw["一年內先跌15%"].notna().sum()),
                       "營飆說明": "營飆逐筆分佈 ＝ 200 顆合併（同一筆在多顆出現就算多次）" if sn == "營飆" else None}
                for sg in SEGS[wn]:
                    xs, ys = W["segp"][sg]
                    ts_ = t_[(t_["ta"] > xs) & (t_["ta"] <= ys) & t_["出場日"].notna()]
                    rep[f"{sg}段 加碼後報酬（淨）"] = q3(ts_["淨報酬"])
                REP[f"{sn}·{c}·{wn}"] = rep
    # T2
    T2S = {}
    for sn in STRATS:
        for c in CELLS:
            for sg in ("主窗", "早年"):
                g = T2R[(T2R["策略"] == sn) & (T2R["格"] == c) & (T2R["段"] == sg)]
                d = {}
                for nm in ("停用", "警戒"):
                    o_ = g[f"原_第一次{nm}月底"];
                    for rd in ("A", "B"):
                        a_ = g[f"{rd}_第一次{nm}月底"]
                        cls = []
                        for x1, x2 in zip(o_, a_):
                            if x1 is None or (isinstance(x1, float) and np.isnan(x1)):
                                cls.append("新增" if isinstance(x2, str) else "都沒有")
                            elif not isinstance(x2, str):
                                cls.append("消失")
                            else:
                                cls.append("提早" if x2 < x1 else ("一樣" if x2 == x1 else "延後"))
                        d[f"{nm}·{rd}"] = pd.Series(cls).value_counts().to_dict()
                    d[f"{nm}·原 月底數中位"] = float(g[f"原_{nm}月底數"].median())
                    for rd in ("A", "B"):
                        d[f"{nm}·{rd} 月底數中位"] = float(g[f"{rd}_{nm}月底數"].median())
                if sn == "營量":
                    d["營量逐條"] = g.drop(columns=["世界", "策略", "r", "格", "段"]).iloc[0].to_dict()
                d["月底最深D 中位"] = {k: float(g[f"{k}_月底最深D"].median()) for k in ("原", "A", "B")}
                T2S[f"{sn}·{c}·{sg}"] = d
    # 原策略早年持有期跨壞根（未截斷）
    cross = {}
    for wn in ("主", "早年"):
        for sn in STRATS:
            hs = [hk for hk in HI if hk[0] == wn and hk[1] == sn]
            cross[f"{wn}·{sn}"] = {"唯一持股": len(hs), "持有期跨壞根": int(sum(HI[hk]["orig_cross_bad"] for hk in hs))}
    S = {"讀法寫死": TIME, "登錄": f"營量營飆持股漲多加碼 seq1 sha {REG_SHA}（裁定 seq341 §四發號 N_組合＋1；seq342 改判定）", "登錄檔": regf,
         "結果句必附": SENT, "早年必附": NOTE_EARLY, "閘": gates, "母體": MINFO, "退化": DG, "判定": VER,
         "主表（主臂）": MT.to_dict("records"), "描述臂": DESC, "必報": REP, "T2": T2S, "原策略持有期跨壞根（描述）": cross,
         "讀法清單": {"A": "累計撥入（隨需撥入、子帳戶出場錢重用、時間加權）", "B": "峰值撥入（段首預留段內累計撥入總額，閒置報酬 0）",
                    "C": "描述：撥入即用、出場退回（時間加權，分母 ＝ 原權益＋在外加碼市值）"},
         "與登錄衝突處（以 seq342 為準）": ["登錄 §三 B0050、判定 ①②（對 0050）⇒ 撤，改判加碼版 vs 原策略", "B隨機 ⇒ 描述、不進判定",
                                      "先驗 ① 改讀成「加碼版是否變好」"],
         "耗時秒": round(time.time() - T0)}
    json.dump(S, open(os.path.join(OUT, "AddOn.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    log(f"[完成] {time.time() - T0:.0f}s ⇒ {OUT}")


def _xb(W, hk, v):
    ep, ts, pxs = v
    return ts if ts is not None else W["NP"] - 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=3)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    log = log_to(os.path.join(OUT, "run.log"))
    log(f"[開跑] {now_tpe()}（台北）NSEED {NSEED}")
    run(a, log)


if __name__ == "__main__":
    main()
