# -*- coding: utf-8 -*-
"""出場第三輪 seq1【正式跑】（台股策略線 登錄 sha 3180c03723d875e3，2026-10-20 20:08；裁定 seq403 發號 N_前段 ＋7（S+ 3、S0 2、S− 2；Bonferroni 7 格）、
seq406 §四 核准開正式跑（7 格以兩策略合併判；結果句必寫「對照組多數時候其實是賣掉改放 0050」））——回測線計算子代理。
⛔ 不 commit、不改既有程式與結果夾（resultsExit3/freq 不動）；researchExit3_freq（reg_check、trades_of、events_of、seg_of、STR、讀法 Q1～Q6 寫死、沿用）、
   researchYL_integrate（main_world、early_world、eng；引擎 research11.simulate_mtm ⛔ 不改）、researchAddOn、research34、researchTurtle ⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchExit3 --procs 2
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchExit3_check
輸出 backtest/resultsExit3/（⛔ 不碰 freq/）：exit3.json、判定表.csv（7 格 × 段 × 策略 × 終點）、描述表.csv（觸發、天數、離之後最高、換 0050、放棄組…）、
     先驗.csv、events_d.csv.gz（逐事件逐出法：帳戶值、d、賣出日、換到哪裡）、run.log

═══ 讀法（Q 標續編；頻率表 Q1～Q6 原樣沿用，以下為正式跑新增；⛔ 在讀任何本件報酬之前寫死；★＝執行者定，〔 〕內為另一讀法）═══
 Q7 事件重用：引擎 r0 兩策略重跑 ⇒ trades_of、events_of（頻率表同函式）與已提交 freq/trades_r0、events_r0 逐列比（sid、e、x、狀態、T、候選數），任一不同 ⇒ 中止、⛔ 不算報酬。
     bp（買價）取引擎 audit 的 buy px。
 Q8 帳戶（登錄 §三、§四）：T 收盤的帳戶值 ＝ 1（＝ 持股 c[T]）；終點 E ＝ min(T＋h, 資料尾, 該股 T 之後第一個壞根前一根)（同 Q5；h ＝ 120 判、60／250 描述），各出法共用同一個 E。
     價格 ＝ 引擎同一份 closes（ffill）／opens（無成交 ＝ 缺）；停止交易後 closes 持平 ⇒ 等於末根收盤凍結成現金，之後沒有開盤可賣（＝ 不再換股）。
     出法觸發 ＝ 收盤判（判斷日 k ∈ [T＋1, E−1]）；★ 執行 ＝ k 之後第一個有開盤的交易日 s（≤ E；沒有 ⇒ 視同沒賣）開盤賣，同一個開盤把錢等權投入「換下一檔」（Q4 同義）：
       候選 ＝ 同策略訊號表 entry_pos ＝ s 的代號，扣自己、扣同帳戶（r0）s 當天仍持有者（e ≤ s ＜ x）；★ 候選在 s 沒有開盤 ⇒ 剔除該候選（筆數照報），全被剔除 ⇒ 0050。
       每檔候選：opens[s] → closes[E]；候選在 (s, E] 遇壞根 ⇒ 第一個壞根前一根收盤賣、之後現金 ★。換股成本：候選 × (1−0.585%)；0050 × (1−0.385%)（手續費 0.285%＋ETF 證交稅 0.1%）。
       ⭐ 事件股自己的賣出成本各出法都要付一次（終點收盤賣或中途賣）⇒ 互相抵銷，不扣。
     沒賣 ⇒ 帳戶值 ＝ c[E] ÷ c[T]；賣 ⇒ o[s] ÷ c[T] × 換股後倍數。
 Q9 出法（登錄 §三）：① s ＝ T 之後第一個有開盤日（立即賣、換下一檔）；
     S+ ② c[k] ≤ (1−10%) × max(c[e..k])（20% 並報）｜S+ ③ c[k] ＜ 20 日均（★ 同 Q5：日曆上最近 20 個 ffill 收盤平均）｜S+ ④ ＝ ½① ＋ ½③（帳戶值線性組合；d(④) ＝ ½d(③) 恆等，照報）；
     S0 ② c[k] ＜ 下緣（[e, T] 最低收盤）｜S0 ③ 先突破（c[k] ＞ 上緣）前：c[k] ＜ 下緣 ⇒ 賣；突破後：c[k] ＜ 上緣 ⇒ 賣（★ 突破後不再看下緣，上緣較嚴已涵蓋）；
     S− ② c[k]/bp − 1 ≥ −5% 或 c[k] ≥ 20 日均（先到者）｜S− ③ ＝ seq6 X7 同式：依可用日排序的月營收公布序列，本期年增 ＜ 0 且前一次公布年增 ≥ 0；
       可用日 A ＝ 期別次月 10 日（≤ 2025-12）／15 日（≥ 2026-01）之後第一個交易日；判斷日 k ＝ A ∈ [T＋1, E−1]，s ＝ A 之後第一個有開盤日（seq6 R3 同）。
     參考列（⛔ 不判）：照原規則出場 ＝ 原 x 當天（排程第 H 日收盤，或停止交易強制 L＋1 以 L 收盤）收盤賣，x ＋1 起第一個有開盤日換下一檔；x ≥ E ⇒ 抱到 E。
 Q10 判定（登錄 §四）：d ＝ 出法帳戶值 − ① 帳戶值；段依事件日 T（Q3）；CI ＝ 事件月分群（research11.cl_stats 的 se）× z，z ＝ Φ⁻¹(1 − 0.05/14)（Bonferroni 7 格、雙尾 99.29%）；
     每段 ＞0 且 CI 不含 0 ⇒ 好｜＜0 且不含 0 ⇒ 差｜其餘分不出；n_eff ＜ 30 ⇒ 依構造不可判定；整格：探索、確認兩段同號且都不含 0 ⇒ 成立，其餘分不出。
     主判 ＝ 合併（營量 r0 ＋ 營飆 r0，seq406）、終點 T＋120；兩策略分報、60／250 日、S0_30／S0_60、S+② 20%、早年 ⇒ 描述（⛔ 不判）。
     T＋1 超出資料（T ＝ 資料最後一天）⇒ 剔除（筆數照報）。
 Q11 必報（登錄 §六）：每格每段 觸發比例（終點前賣出）、T 到賣出的交易日數、賣出點離之後最高收盤（(事件股 (s, E] 最高收盤 ÷ 賣價 − 1)；真頂措辭 seq343）、
     換手（每事件換股次數）與換股成本、賣出時換到 0050 的比例、放棄組（被賣掉那檔若抱到終點：c[E] ÷ o[s] − 1）。
     ⛔ seq6 隨便買樣本（登錄 §二「描述」）：沒有「已達成名單」⇒ 對照①「換下一檔」不可定義 ⇒ 本件不做（〈三十九〉不可定義不自補，照寫）。
     ⛔ 下市營收補（seq406 §三）：要重產營量／營飆訊號（策略鎖內）⇒ 本件不做，照寫。
 Q12 結果句必附：「不是跟抱固定天數比，而是跟立即賣掉換下一檔比」「營量、營飆照規則的歷史交易，不是你的實際成交」「對照組多數時候其實是賣掉改放 0050」
     「2015 後營收母體無下市股（存活者偏差，偏樂觀）」「單筆層通過 ≠ 組合會贏 0050」；早年附 researchTurtle.NOTE_EARLY（reduce_v2 約 0.3%）；
     ⛔ 不得寫「不賣最好」，要回答「漲／盤整／跌的時候，各自怎麼出比較好」；真頂措辭 seq343；
     同根兩出場價取較低（seq373）：本件全部出法收盤判、隔日開盤賣，每法每筆只有一個賣價 ⇒ 不會有同根兩價，照寫。
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
import time
from statistics import NormalDist

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchExit3_freq as XF               # noqa: E402  reg_check、trades_of、events_of、seg_of、STR（⛔ 只 import）
from backtest import researchYL_integrate as IG             # noqa: E402  main_world、early_world、eng
from backtest import researchAddOn as RA                    # noqa: E402  early_extra_bad、WORK、CRASH_WORK
from backtest import research11 as R                        # noqa: E402  cl_stats
from backtest import research34 as R34                      # noqa: E402  load_revenue、rebalance_dates
from backtest import researchTurtle as TU                   # noqa: E402  NOTE_EARLY
from backtest import evaluate as EVAL                       # noqa: E402  COST
from backtest import data as D                              # noqa: E402

OUT = "backtest/resultsExit3"
FREQ = XF.OUT
COST = EVAL.COST
COST50 = 0.001425 * 2 + 0.001
Z7 = NormalDist().inv_cdf(1 - 0.05 / 14)
HJ = 120
ENDS = (60, 120, 250)
NEFF_MIN = 30
# (狀態群, 格名, 事件狀態, 出法碼, 身分)
CELLS = [("S+", "②回落10%才賣", "S+", "trail10", "判定"), ("S+", "③跌破20日線", "S+", "ma20dn", "判定"), ("S+", "④半立即半③", "S+", "half", "判定"),
         ("S0", "②跌破箱底", "S0_40", "box_lo", "判定"), ("S0", "③Darvas箱型", "S0_40", "darvas", "判定"),
         ("S−", "②反彈−5%或站回20日線", "S−", "rebound", "判定"), ("S−", "③營收年增轉負", "S−", "revneg", "判定")]
DESC = [("S+", "②′回落20%才賣（並報）", "S+", "trail20"),
        ("S0", "②跌破箱底（S0_30 描述）", "S0_30", "box_lo"), ("S0", "③Darvas箱型（S0_30 描述）", "S0_30", "darvas"),
        ("S0", "②跌破箱底（S0_60 描述）", "S0_60", "box_lo"), ("S0", "③Darvas箱型（S0_60 描述）", "S0_60", "darvas")]
METHODS_BY_STATE = {"S+": ["imm", "trail10", "trail20", "ma20dn", "half", "orig"], "S0_30": ["imm", "box_lo", "darvas", "orig"],
                    "S0_40": ["imm", "box_lo", "darvas", "orig"], "S0_60": ["imm", "box_lo", "darvas", "orig"], "S−": ["imm", "rebound", "revneg", "orig"]}
SENT_MUST = ["不是跟抱固定天數比，而是跟立即賣掉換下一檔比", "營量、營飆照規則的歷史交易，不是你的實際成交", "對照組多數時候其實是賣掉改放 0050",
             "2015 後營收母體無下市股（存活者偏差，偏樂觀）", "單筆層通過 ≠ 組合會贏 0050"]
SENT_373 = "同根兩出場價取較低（seq373）：全部出法收盤判、隔日開盤賣，每筆只有一個賣價 ⇒ 不適用，照寫"
LOG: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def pct(x, d=2):
    return "—" if x is None or not np.isfinite(x) else "{:+.{}f}%".format(x * 100, d)


def rev_turns(sid, rev, rly, A):
    """seq6 X7 同式（researchExitGen.rev_turns 逐字，因該模組 import 會改 D.DATA ⇒ 抄寫不 import）。"""
    if rev is None or sid not in rev.columns:
        return np.zeros(0, int), 0
    rv = rev[sid].to_numpy(float); rl = rly[sid].to_numpy(float); per = list(rev.index)
    ev = []
    for k, p in enumerate(per):
        if not np.isfinite(rv[k]) or p not in A:
            continue
        yoy = rv[k] / rl[k] - 1.0 if (np.isfinite(rl[k]) and rl[k] > 0) else np.nan
        ev.append((A[p], yoy))
    ev.sort(key=lambda z: z[0])
    turns = [ev[i][0] for i in range(1, len(ev)) if np.isfinite(ev[i][1]) and np.isfinite(ev[i - 1][1]) and ev[i][1] < 0 <= ev[i - 1][1]]
    return np.asarray(turns, int), len(ev)


def avail_map(periods, cal):
    a10 = R34.rebalance_dates([p for p in periods if p <= "2025-12"], cal, pub_day=10)
    a15 = R34.rebalance_dates([p for p in periods if p >= "2026-01"], cal, pub_day=15)
    return {p: v[1] for p, v in {**a10, **a15}.items()}


def first_trig(c, k0, k1, fn):
    """k ∈ [k0, k1] 第一個 fn(k) 為真；沒有 ⇒ −1。"""
    for k in range(k0, k1 + 1):
        if fn(k):
            return k
    return -1


def ma20_arr(c):
    """最近 20 個日曆交易日 ffill 收盤平均（上市前的缺值不計）。⚠ 第一版用 cumsum，遇上市前缺值整條變 NaN、20 日線觸發失效；對帳 C1 抓到後改（結果已重跑）。"""
    return pd.Series(np.asarray(c, float)).rolling(20, min_periods=1).mean().to_numpy()


class World:
    def __init__(self, W, wn, BADw, trades, rev):
        self.W = W; self.wn = wn; self.cal = W["cal"]; self.last = len(self.cal) - 1
        self.BAD = BADw; self.trades = trades
        D.DATA = W["data"]
        st = D.load_stock("0050", "twse", self.cal)
        self.o50 = st.df["open"].to_numpy(float); self.c50 = pd.Series(st.df["close"].to_numpy(float)).ffill().to_numpy(float)
        self.byS = {sn: W["SIG"][XF.STR[sn]["G"]].groupby("entry_pos")["sid"].apply(list).to_dict() for sn in XF.STR}
        self.rev, self.rly = rev
        self.A = avail_map(list(self.rev.index), self.cal)
        self.turns = {}
        self.cnt = {"候選無開盤剔除": 0, "候選遇壞根強制": 0, "全部候選剔除改0050": 0}

    def cl(self, s):
        return np.asarray(self.W["closes"][s], float)

    def op(self, s):
        return np.asarray(self.W["opens"][s], float)

    def next_open(self, s, d, E):
        o = self.op(s)
        for q in range(d + 1, E + 1):
            if np.isfinite(o[q]) and o[q] > 0:
                return q
        return -1

    def reinvest(self, sn, self_sid, s, E):
        """⇒ (倍數, 去向, 候選數)。"""
        if s >= E:
            return 1.0, "到終點", 0
        T = self.trades[sn]
        held = set(T["sid"][(T["e"] <= s) & (T["x"] > s)])
        cand = [c for c in self.byS[sn].get(s, []) if c != self_sid and c not in held]
        vals = []
        for c in cand:
            oc = self.op(c); cc = self.cl(c)
            if not (np.isfinite(oc[s]) and oc[s] > 0):
                self.cnt["候選無開盤剔除"] += 1; continue
            Ec = E
            bb = self.BAD.get(c)
            if bb is not None:
                kk = bb[(bb > s) & (bb <= E)]
                if len(kk):
                    Ec = int(kk[0]) - 1; self.cnt["候選遇壞根強制"] += 1
            vals.append(cc[Ec] / oc[s])
        if vals:
            return float(np.mean(vals)) * (1 - COST), "候選", len(vals)
        if cand:
            self.cnt["全部候選剔除改0050"] += 1
        return float(self.c50[E] / self.o50[s]) * (1 - COST50), "0050", 0


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2)
    a = ap.parse_args()
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    reg = XF.reg_check()
    log(f"[登錄] {reg}（sha {XF.REG_SHA} 已驗）")
    J = {"性質": "出場第三輪 seq1 正式跑", "登錄": f"台股策略線 seq1 sha {XF.REG_SHA}",
         "裁定": "seq403 發號 N_前段 ＋7（Bonferroni 7 格）；seq406 §四 核准正式跑、7 格以兩策略合併判、必寫「對照組多數時候其實是賣掉改放 0050」；§三 必附存活者偏差句",
         "z": Z7}
    WS = {}
    WS["主"], _ = IG.main_world(log)
    WS["早年"], _ = IG.early_world(log, a.procs)
    # 壞根（同頻率表）
    BAD = {}
    for wn, part in (("主", "main"), ("早年", "early")):
        B = pickle.load(open(os.path.join(RA.CRASH_WORK, f"bad_{part}.pkl"), "rb"))
        BAD[wn] = {s: set(int(x) for x in a_) | set(int(x) for x in b_) for s, (a_, b_) in B.items()}
    Wa = pickle.load(open(os.path.join(RA.WORK, "world_早年.pkl"), "rb"))
    EX, excnt = RA.early_extra_bad(Wa, lambda *x: None)
    for s, ks in EX.items():
        BAD["早年"].setdefault(s, set()).update(int(k) for k in ks)
    BAD = {wn: {s: np.array(sorted(v), np.int64) for s, v in d.items()} for wn, d in BAD.items()}
    # ── Q7 事件重用與重建
    TRref = pd.read_csv(os.path.join(FREQ, "trades_r0.csv.gz"), dtype={"sid": str})
    EVref = pd.read_csv(os.path.join(FREQ, "events_r0.csv.gz"), dtype={"sid": str})
    TR = {}; DE = []
    for wn in ("主", "早年"):
        W = WS[wn]; cal = W["cal"]; last = len(cal) - 1
        TR[wn] = {}
        for sn, S in XF.STR.items():
            o, au = IG.eng(W, S["key"], 0, audit=True)
            T = XF.trades_of(au, len(cal))
            ref = TRref[(TRref["世界"] == wn) & (TRref["策略"] == sn)].reset_index(drop=True)
            if not (len(T) == len(ref) and (T["sid"].to_numpy() == ref["sid"].to_numpy()).all() and (T["e"].to_numpy() == ref["e"].to_numpy()).all()
                    and (T["x"].to_numpy() == ref["x"].to_numpy()).all()):
                raise SystemExit(f"⛔ {wn}·{sn} 引擎 r0 交易 ≠ 已提交 trades_r0 ⇒ 中止")
            TR[wn][sn] = {"sid": T["sid"].to_numpy(), "e": T["e"].to_numpy(), "x": T["x"].to_numpy(), "bp": dict(zip(zip(T["sid"], T["e"]), T["bp"]))}
            E, _ = XF.events_of(T, W, BAD[wn], last)
            E["策略"] = sn; E["世界"] = wn
            E["候選數"] = XF.cand_info(E, T, W["SIG"][S["G"]], len(cal))
            DE.append(E)
    DE = pd.concat(DE, ignore_index=True)
    k_ = ["世界", "策略", "sid", "e", "狀態", "T"]
    a1 = DE.sort_values(k_).reset_index(drop=True)
    b1 = EVref.sort_values(k_).reset_index(drop=True)
    same = len(a1) == len(b1) and bool((a1[k_ + ["x", "候選數"]].astype(str).to_numpy() == b1[k_ + ["x", "候選數"]].astype(str).to_numpy()).all())
    log(f"[對照重建] 引擎 r0 交易 ＝ trades_r0；events_of 重建 {len(a1)} 列 vs 已提交 {len(b1)}｜逐列相同 {same}")
    if not same:
        raise SystemExit("⛔ 事件重建 ≠ 已提交 events_r0 ⇒ 中止（未算任何報酬）")
    EV = b1.copy()
    J["對照重建"] = {"trades_r0 相同": True, "events_r0 逐列相同": same, "事件列": int(len(EV))}
    # 月營收
    REV = {}
    for wn in ("主", "早年"):
        D.DATA = WS[wn]["data"]
        rv, rl, _ = R34.load_revenue()
        REV[wn] = (rv, rl)
    WO = {wn: World(WS[wn], wn, BAD[wn], TR[wn], REV[wn]) for wn in ("主", "早年")}
    # ── 逐事件
    ROWS = []
    nskip = 0
    for q, ev in EV.iterrows():
        wn, sn, s, e, x, st, T = ev["世界"], ev["策略"], ev["sid"], int(ev["e"]), int(ev["x"]), ev["狀態"], int(ev["T"])
        Wd = WO[wn]; last = Wd.last
        if T + 1 > last:
            nskip += 1; continue
        c = Wd.cl(s); bp = Wd.trades[sn]["bp"][(s, e)]
        bb = Wd.BAD.get(s)
        nb_after = int(bb[bb > T][0]) if (bb is not None and (bb > T).any()) else 10 ** 9
        ma = None
        if s not in Wd.turns:
            Wd.turns[s] = rev_turns(s, Wd.rev, Wd.rly, Wd.A)[0]
        for h in ENDS:
            E = min(T + h, last, nb_after - 1)
            if E <= T:
                continue
            cT = c[T]
            meths = METHODS_BY_STATE[st]
            out = {}

            def acct(d, code):
                """判斷日 d（−1 ＝ 沒觸發）⇒ dict。"""
                if d < 0:
                    return {"V": c[E] / cT, "賣": False}
                s_ = Wd.next_open(s, d, E)
                if s_ < 0:
                    return {"V": c[E] / cT, "賣": False, "觸發未成交": True}
                o_ = Wd.op(s)[s_]
                m, where, nc = Wd.reinvest(sn, s, s_, E)
                return {"V": o_ / cT * m, "賣": True, "賣日": s_, "判斷日": d, "賣價": o_, "去向": where, "候選數": nc,
                        "之後最高÷賣價−1": float(c[s_:E + 1].max() / o_ - 1.0), "放棄組": float(c[E] / o_ - 1.0)}

            k0, k1 = T + 1, E - 1
            for mth in meths:
                if mth == "imm":
                    out[mth] = acct(T, mth)
                elif mth in ("trail10", "trail20"):
                    p_ = 0.10 if mth == "trail10" else 0.20
                    rm = np.maximum.accumulate(c[e:E + 1])
                    out[mth] = acct(first_trig(c, k0, k1, lambda k: c[k] <= (1 - p_) * rm[k - e]), mth)
                elif mth in ("ma20dn", "rebound"):
                    if ma is None:
                        ma = ma20_arr(c)
                    if mth == "ma20dn":
                        out[mth] = acct(first_trig(c, k0, k1, lambda k: c[k] < ma[k]), mth)
                    elif mth == "rebound":
                        out[mth] = acct(first_trig(c, k0, k1, lambda k: (c[k] / bp - 1.0 >= -0.05) or (c[k] >= ma[k])), mth)
                elif mth == "box_lo":
                    lo_ = c[e:T + 1].min()
                    out[mth] = acct(first_trig(c, k0, k1, lambda k: c[k] < lo_), mth)
                elif mth == "darvas":
                    lo_, up_ = c[e:T + 1].min(), c[e:T + 1].max()
                    d = -1; brk = False
                    for k in range(k0, k1 + 1):
                        if not brk:
                            if c[k] < lo_:
                                d = k; break
                            if c[k] > up_:
                                brk = True
                        elif c[k] < up_:
                            d = k; break
                    r_ = acct(d, mth); r_["先突破"] = brk
                    out[mth] = r_
                elif mth == "revneg":
                    tt = Wd.turns[s]; w = tt[(tt >= k0) & (tt <= k1)]
                    out[mth] = acct(int(w.min()) if len(w) else -1, mth)
                elif mth == "orig":
                    if x <= E - 1:
                        Vx = c[x] / cT
                        s_ = x + 1
                        m, where, nc = Wd.reinvest(sn, s, s_, E)
                        out[mth] = {"V": Vx * m, "賣": True, "賣日": x, "去向": where, "候選數": nc, "賣價": float(c[x]),
                                    "之後最高÷賣價−1": float(c[x:E + 1].max() / c[x] - 1.0), "放棄組": float(c[E] / c[x] - 1.0)}
                    else:
                        out[mth] = {"V": c[E] / cT, "賣": False}
            if st == "S+":
                if ma is None:
                    ma = ma20_arr(c)
                out["ma20dn"] = out.get("ma20dn") or acct(first_trig(c, k0, k1, lambda k: c[k] < ma[k]), "ma20dn")
                v1, v3 = out["imm"], out["ma20dn"]
                out["half"] = {"V": 0.5 * v1["V"] + 0.5 * v3["V"], "賣": v1["賣"], "賣日": v1.get("賣日", -1), "去向": v1.get("去向", ""), "候選數": v1.get("候選數", np.nan),
                               "之後最高÷賣價−1": v1.get("之後最高÷賣價−1"), "放棄組": v1.get("放棄組"), "半③賣": v3["賣"]}
            V1 = out["imm"]["V"]
            for mth, r_ in out.items():
                ROWS.append({"世界": wn, "策略": sn, "sid": s, "e": e, "x": x, "狀態": st, "T": T, "段": ev["段"], "事件日": ev["事件日"], "終點h": h, "E": E,
                             "E截斷(壞根或資料尾)": E < T + h, "出法": mth, "V": r_["V"], "V_立即換": V1, "d": r_["V"] - V1, "賣": r_["賣"],
                             "賣日": r_.get("賣日", -1), "判斷日": r_.get("判斷日", -1), "T到賣出天數": (r_["賣日"] - T) if r_.get("賣日", -1) >= 0 else np.nan,
                             "去向": r_.get("去向", ""), "候選數": r_.get("候選數", np.nan), "之後最高÷賣價−1": r_.get("之後最高÷賣價−1", np.nan),
                             "放棄組": r_.get("放棄組", np.nan), "觸發未成交": r_.get("觸發未成交", False), "先突破": r_.get("先突破", None),
                             "半③賣": r_.get("半③賣", None)})
        if (q + 1) % 500 == 0:
            log(f"  事件 {q + 1}／{len(EV)}｜{time.time() - t0:.0f}s")
    DD = pd.DataFrame(ROWS)
    DD["事件月"] = DD["事件日"].str[:7]
    J["T＋1超出資料剔除"] = nskip
    J["換股計數"] = {wn: WO[wn].cnt for wn in WO}
    log(f"[逐事件] 列 {len(DD):,}｜T＋1 超出資料剔除 {nskip}｜換股計數 {J['換股計數']}｜{time.time() - t0:.0f}s")
    # 恆等檢查：d(④) ＝ ½ d(③)
    hf = DD[DD["出法"] == "half"].set_index(["世界", "策略", "sid", "e", "T", "終點h"])["d"]
    m3 = DD[DD["出法"] == "ma20dn"].set_index(["世界", "策略", "sid", "e", "T", "終點h"])["d"]
    J["④＝½③ 最大誤差"] = float((hf - 0.5 * m3.reindex(hf.index)).abs().max())
    log(f"[恆等] d(④) − ½d(③) 最大 {J['④＝½③ 最大誤差']:.2e}")

    # ── 判定與描述
    def cell_stats(sub, z):
        x = sub["d"].to_numpy(float); key = sub["事件月"].to_numpy()
        n = len(x)
        if n == 0:
            return {"n": 0, "n_eff": 0, "結果": "依構造不可判定"}
        cs = R.cl_stats(x, key)
        m, se, ng = cs["mean"], cs["se"], cs["months"]
        ne = int(min(n, ng))
        lo, hi = m - z * se, m + z * se
        if ne < NEFF_MIN:
            rs = "依構造不可判定"
        else:
            rs = "分不出" if lo <= 0 <= hi else ("好" if m > 0 else "差")
        return {"n": n, "n_eff": ne, "群數": ng, "d平均": m, "d中位": float(np.median(x)), "d>0比例": float((x > 0).mean()), "se": se,
                "lo": lo, "hi": hi, "結果": rs, "t": m / se if se > 0 else None}

    def desc_stats(sub, imm):
        o = {}
        n = len(sub)
        if n == 0:
            return o
        sold = sub[sub["賣"]]
        o["觸發比例(終點前賣出)"] = float(len(sold) / n)
        o["T到賣出天數平均"] = float(sold["T到賣出天數"].mean()) if len(sold) else None
        o["T到賣出天數中位"] = float(sold["T到賣出天數"].median()) if len(sold) else None
        o["賣出後最高÷賣價−1 中位"] = float(sold["之後最高÷賣價−1"].median()) if len(sold) else None
        o["賣在之後最高之上比例"] = float((sold["之後最高÷賣價−1"] <= 0).mean()) if len(sold) else None
        o["賣出換到0050比例"] = float((sold["去向"] == "0050").mean()) if len(sold) else None
        o["賣出換到候選比例"] = float((sold["去向"] == "候選").mean()) if len(sold) else None
        o["每事件換股次數"] = float(((sold["去向"] == "候選") | (sold["去向"] == "0050")).sum() / n)
        o["每事件換股成本(平均)"] = float((((sold["去向"] == "候選").sum() * COST) + ((sold["去向"] == "0050").sum() * COST50)) / n)
        o["放棄組平均"] = float(sold["放棄組"].mean()) if len(sold) else None
        o["放棄組中位"] = float(sold["放棄組"].median()) if len(sold) else None
        o["帳戶值平均"] = float(sub["V"].mean()); o["立即換帳戶值平均"] = float(sub["V_立即換"].mean())
        o["E截斷比例"] = float(sub["E截斷(壞根或資料尾)"].mean())
        return o

    TAB = []
    allcells = [(g, n_, st, m, "判定") for g, n_, st, m, _ in CELLS] + [(g, n_, st, m, "描述") for g, n_, st, m in DESC] + \
               [(st[:2] if st.startswith("S0") else st, f"參考：照原規則出場（{st}）", st, "orig", "參考（⛔不判）") for st in ("S+", "S0_40", "S−")] + \
               [(st[:2] if st.startswith("S0") else st, f"①立即換（{st}）本身", st, "imm", "對照組描述") for st in ("S+", "S0_40", "S−")]
    for grp, nm, st, mth, role in allcells:
        for h in ENDS:
            for strat in ("合併", "營量", "營飆"):
                for sg in ("探索", "確認", "早年"):
                    sub = DD[(DD["狀態"] == st) & (DD["出法"] == mth) & (DD["終點h"] == h) & (DD["段"] == sg)]
                    if strat != "合併":
                        sub = sub[sub["策略"] == strat]
                    isj = (role == "判定" and h == HJ and strat == "合併" and sg in ("探索", "確認"))
                    cs = cell_stats(sub, Z7) if mth != "imm" else {"n": len(sub)}
                    row = {"狀態群": grp, "格": nm, "事件狀態": st, "出法": mth, "身分": role if isj or role != "判定" else "判定格的描述版", "終點": f"T+{h}",
                           "策略": strat, "段": sg, **{f"d_{k}": v for k, v in cs.items()}, **desc_stats(sub, None)}
                    if mth == "imm":
                        row["立即換_帳戶值平均"] = float(sub["V"].mean()) if len(sub) else None
                    TAB.append(row)
    TAB = pd.DataFrame(TAB)
    # 整格判定
    VER = []
    for grp, nm, st, mth, _ in CELLS:
        r = {sg: TAB[(TAB["格"] == nm) & (TAB["終點"] == f"T+{HJ}") & (TAB["策略"] == "合併") & (TAB["段"] == sg)].iloc[0] for sg in ("探索", "確認", "早年")}
        rs = [r["探索"]["d_結果"], r["確認"]["d_結果"]]
        ok = rs[0] == rs[1] and rs[0] in ("好", "差")
        verdict = ("成立（比立即換" + rs[0] + "）") if ok else "分不出"
        VER.append({"狀態": grp, "格": nm, "事件": st, "探索_n": r["探索"]["d_n"], "探索_n_eff": r["探索"]["d_n_eff"], "探索_d": r["探索"]["d_d平均"],
                    "探索_lo": r["探索"]["d_lo"], "探索_hi": r["探索"]["d_hi"], "探索": rs[0],
                    "確認_n": r["確認"]["d_n"], "確認_n_eff": r["確認"]["d_n_eff"], "確認_d": r["確認"]["d_d平均"], "確認_lo": r["確認"]["d_lo"], "確認_hi": r["確認"]["d_hi"],
                    "確認": rs[1], "整格": verdict, "早年_d(描述)": r["早年"]["d_d平均"], "早年(描述)": r["早年"]["d_結果"],
                    "探索_觸發比例": r["探索"].get("觸發比例(終點前賣出)"), "確認_觸發比例": r["確認"].get("觸發比例(終點前賣出)")})
    VER = pd.DataFrame(VER)
    for _, v in VER.iterrows():
        log(f"[判定] {v['狀態']} {v['格']}：探索 {pct(v['探索_d'])}（{v['探索']}）｜確認 {pct(v['確認_d'])}（{v['確認']}）⇒ {v['整格']}")
    # 0050 比例（對照組）
    imm = DD[(DD["出法"] == "imm") & (DD["終點h"] == HJ)]
    Z50 = {}
    for sg in ("探索", "確認", "早年"):
        for st in ("S+", "S0_40", "S−"):
            u = imm[(imm["段"] == sg) & (imm["狀態"] == st) & imm["賣"]]
            Z50[f"{sg}_{st}"] = float((u["去向"] == "0050").mean()) if len(u) else None
        u = imm[(imm["段"] == sg) & imm["狀態"].isin(["S+", "S0_40", "S−"]) & imm["賣"]]
        Z50[f"{sg}_三狀態合計"] = float((u["去向"] == "0050").mean()) if len(u) else None
    J["對照組改放0050比例(T+120)"] = Z50
    log(f"[對照組 0050] {Z50}")
    # 結果句
    SEN = {}
    stname = {"S+": "漲 15% 以上", "S0": "盤整很久（40 日都在 ±15% 內）", "S−": "跌 15% 以上"}
    tail = SENT_MUST + ["真頂措辭 seq343：「賣出點離之後最高收盤」只描述賣得多早，⛔ 不稱最高點、頂部", SENT_373]
    for _, v in VER.iterrows():
        if v["整格"].startswith("成立"):
            w = "好" if "好" in v["整格"] else "差"
            body = f"持股{stname[v['狀態']]}時，{v['格'][1:]}比立即賣掉換下一檔{w}（探索 {pct(v['探索_d'])}、確認 {pct(v['確認_d'])}，兩段一致）"
        else:
            body = (f"持股{stname[v['狀態']]}時，{v['格'][1:]}跟立即賣掉換下一檔分不出（探索 {pct(v['探索_d'])}〔{v['探索']}〕、確認 {pct(v['確認_d'])}〔{v['確認']}〕，"
                    f"兩段{'一致' if v['探索'] == v['確認'] else '不一致'}）")
        SEN[v["格"] + "_" + v["狀態"]] = body
    nsucc = int(VER["整格"].str.startswith("成立").sum())
    per_state = {}
    for g in ("S+", "S0", "S−"):
        vv = VER[VER["狀態"] == g]
        good = vv[vv["整格"].str.contains("好")]; bad_ = vv[vv["整格"].str.contains("差")]
        if len(good):
            per_state[g] = f"{stname[g]}時：{'、'.join(x[1:] for x in good['格'])} 比立即換好（兩段一致）"
        elif len(bad_) == len(vv):
            per_state[g] = f"{stname[g]}時：試過的出法都比立即換差 ⇒ 這個狀態下立即賣掉換下一檔較好（⚠ 對照組多數時候其實是改放 0050）"
        elif len(bad_):
            per_state[g] = f"{stname[g]}時：{'、'.join(x[1:] for x in bad_['格'])} 比立即換差，其餘分不出"
        else:
            per_state[g] = f"{stname[g]}時：試過的出法都跟立即換下一檔分不出來"
    allnone = nsucc == 0
    J["結果句"] = {"各格": SEN, "三狀態怎麼出": per_state,
                 "總句": ("這三種狀態下，試過的出法都跟立即換下一檔分不出來" if allnone else "；".join(per_state.values())), "必附": tail + TU.NOTE_EARLY}
    for k, v in J["結果句"]["三狀態怎麼出"].items():
        log(f"[句] {k}：{v}")
    log(f"[總句] {J['結果句']['總句']}")
    # 先驗
    def vrow(nm):
        return VER[VER["格"] == nm].iloc[0]
    PR = []
    v = vrow("②回落10%才賣")
    PR.append({"先驗": "① S+ ②（回落 10% 才賣）比立即換好（約五成五）", "結果": v["整格"], "中": "比立即換好" in v["整格"]})
    v2, v3 = vrow("②反彈−5%或站回20日線"), vrow("③營收年增轉負")
    PR.append({"先驗": "② S− 立即換比 ②③ 好，即 S− ②③ 格 d ＜0（約五成）★ 以整格「成立（比立即換差）」判",
               "結果": f"② {v2['整格']}（{pct(v2['探索_d'])}／{pct(v2['確認_d'])}）；③ {v3['整格']}（{pct(v3['探索_d'])}／{pct(v3['確認_d'])}）",
               "中": ("差" in v2["整格"]) and ("差" in v3["整格"])})
    s0 = VER[VER["狀態"] == "S0"]
    PR.append({"先驗": "③ S0 兩格分不出（約六成五）", "結果": "；".join(f"{r['格']} {r['整格']}" for _, r in s0.iterrows()), "中": bool((s0["整格"] == "分不出").all())})
    PR.append({"先驗": "④ 7 格成立 ≤ 2 格（約七成）", "結果": f"成立 {nsucc} 格", "中": nsucc <= 2})
    PR = pd.DataFrame(PR)
    for _, r in PR.iterrows():
        log(f"[先驗] {r['先驗']}｜{r['結果']}｜{r['中']}")
    # 輸出
    J["判定"] = VER.to_dict("records")
    J["不做"] = {"seq6 隨便買樣本": "對照①「換下一檔」需同策略已達成名單，隨便買沒有 ⇒ 不可定義（〈三十九〉），不自補",
               "下市營收補": "要重產營量／營飆訊號（策略鎖內）⇒ 本件不做；結果句附存活者偏差句"}
    J["讀法"] = __doc__.split("═══ 讀法")[1]
    J["時間"] = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")
    VER.to_csv(os.path.join(OUT, "判定表.csv"), index=False, encoding="utf-8-sig")
    TAB.to_csv(os.path.join(OUT, "描述表.csv"), index=False, encoding="utf-8-sig")
    PR.to_csv(os.path.join(OUT, "先驗.csv"), index=False, encoding="utf-8-sig")
    DD.to_csv(os.path.join(OUT, "events_d.csv.gz"), index=False, compression="gzip")
    json.dump(J, open(os.path.join(OUT, "exit3.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] {time.time() - t0:.0f}s")
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
