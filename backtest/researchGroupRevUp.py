# -*- coding: utf-8 -*-
"""額外策略「營量 v1、營飆 v1 加『同族群營收也一起轉強』（只買版、優先版）」【正式跑】——回測線計算子代理，2026-11-11。
登錄：台股策略線 seq2（sha e72a759aefc7bfdc，6686 B）〈營量營飆加族群營收也轉強_只買版與優先版_組合層登錄〉
發號、裁定：seq501 §三（發號）、seq502（優先版兩格撤判、只描述、標「等同原版」、⛔ 不進全策略排名；N_組合 ＋2；分群用產業版）、
           seq503（核可正式跑；營飆只買版判語事先固定「還沒測（依構造）」（確認段有效月數 21 ＜ 24），報酬只描述；營量只買版照 seq2 判定、最多合格（暫定））
⛔ 不改策略鎖內任何檔（research11、rerun17、researchYL_integrate… 只 import）；開跑前、跑完各驗一次 strategy_lock。
⛔ 模擬與分組只有一份：本檔重用 researchGroupRevUp_freq 的 cell_sig／make_sig（dry=False ⇒ 真實毛報酬）、run_engine（真價格、full）、intervals、
   產業分群旗標（~/grpwork/groups_<世界>_industry.pkl，freq --step groups --groups industry 產出）；本檔只加「真價格、對大盤、重疊度（金額權重）」的計算。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchGroupRevUp --formal --ruling seq503 [--procs 3]
    （⛔ 缺 --formal、缺 --ruling、裁定號不是 seq503 ⇒ 拒跑；信箱找不到 seq501／502／503 裁定 ⇒ 拒跑）
    前置：freq 的 --step world／groups --groups industry 中間檔在 ~/grpwork（不在 ⇒ 先照 freq 用法重跑）
    自測：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.selftest_researchGroupRevUp_freq（T9～T11 為本檔）
輸出 backtest/resultsGroupRevUp/formal/：result.json、結果.md、cells.csv、overlap.csv、overlap_yearly.csv、trades_split.csv、seeds.csv.gz、run.log

═══ 讀法（⛔ 在算任何本件報酬之前寫死於 2026-11-11 10:08（台北）；★ ＝ 登錄、裁定沒寫清、執行者定；〔 〕＝ 另一讀法並報）═══
 寫死前看過：登錄 seq2 全文、裁定 seq501／502／503、頻率表（freq、freq_industry，⛔ 無報酬）、既有程式 researchYLSell5（組合層正式跑口徑）、benchmark_rejudge、
   researchPTH10vsYL（月分群 CI、金額重疊口徑）；⚠ 回測線看過營量 v1、營飆 v1 全部正式結果；⛔ 沒看過本件任何報酬。
 P0 閘：--formal --ruling seq503；登錄 sha（freq.check_reg）；信箱 seq501／502／503 裁定；策略鎖前後；
    世界 ＝ researchAddOn.worlds 快取（＝ researchYL_integrate.main_world／early_world）⇒ 與 freq 的訊號表逐列相同（sid、pos、entry_pos、xpos_H60／H120、relvol、閘）才接真實 g；
    候選逐年「族群轉強」筆數 ＝ 已 commit 的 freq_industry/cand_yearly.csv；乾跑重現（營量 r0、營飆 r0～2，三版買進 ＝ ~/grpwork/sim_<世界>_industry.pkl）；
    原版權益 eq_sha ＝ resultsYL_integrate/seeds.csv.gz 同世界同格同 r（＝ 正式營量 v1／營飆 v1，200 顆全比）；逐日持股市值重建 ＝ 引擎 hold_val（相對差 ＜ 1e−9）
 P1 三版 ＝ freq F2 原式（cell_sig、run_engine），只把價格換成世界真實還原開收盤、毛報酬換成世界 g_H；成本 research11.COST 0.585%；stop_force 照正式；
    營量 r0、營飆 r ＝ 0～199（同 freq、同正式種子）；旗標 ＝ 主段產業版、早年自建 v2（裁定 seq502／503）
 P2 段 ＝ 世界 segp：探索 2017-03-02～2021-12-30、確認 2022-01-03～2026-08-24（★ ＝ 正式窗尾、freq F1 同）、早年 2005-02-01～2014-12-31（只描述）
    年化、回落 ＝ rerun17.win_metrics；營飆 ＝ 200 顆中位（年化中位、回落中位、比值 ＝ 年化中位 ÷ |回落中位|，seq342／rerun17 慣例），另報 p10～p90 與 r0
 P3 大盤 ＝ 臺灣加權報酬指數 origin/main data/history/market_tri.csv（benchmark_rejudge.read_series；世界日曆 reindex＋ffill；執行時記 sha）；
    段統計 ＝ benchmark_rejudge.bstat；標籤 ＝ researchAscTri.label（合格 ＝ 年化 ＞ 大盤 且 比值 ≥ 大盤；另列 ＝ 只年化贏；其餘不合格）；0050 ＝ 世界 bench、只當一欄
 P4 判語（每格）：
    營量只買版 ★ ＝ 探索、確認兩段標籤都「合格」⇒「合格（暫定）」；兩段年化都贏大盤但不是兩段都合格 ⇒「另列」；其餘 ⇒「不合格」；
       ★ 任一段有效月數（段內有買進的月份數，freq F4④ 同式、真價格重算）＜ 24 ⇒「還沒測」（頻率表 40／35，預期不觸發）
    營飆只買版 ＝「還沒測（依構造）」（裁定 seq503 事先固定；報酬、標籤只描述）
    優先版兩格 ＝「等同原版（只描述）」（裁定 seq502；⛔ 不出合格／不合格、⛔ 不進全策略排名）
    原版 ＝ 對照、只描述
 P5 對大盤差 ＝ 年化（中位）− 大盤年化（同窗）
    ★ 月超額 CI（描述，⛔ 不進判語）：段內點 ＝ 段首 ∪ 段內完整月底（researchPTH_freq.month_ends）∪ 段尾；月超額 ＝ 策略月報酬 − 大盤月報酬；
      平均 ± t(0.975, n−1)·sd/√n（每月一群，researchPTH10vsYL.t975）；營飆 ＝ 先把 200 顆同月報酬取平均再減大盤〔另報 r0〕；⚠ 持有 60／120 日 ⇒ 月與月不獨立、CI 偏窄
 P6 重疊度（登錄 §三；三配對 ＝ 優先 vs 原、只買 vs 原、只買 vs 優先；營飆每顆算、報中位〔p10～p90〕）：
    ① 買進重疊 ＝ 同日同檔買進 ÷ 前者買進（另報 ÷ 後者）；真價格引擎重算（乾跑頻率表因「現金不足」一步可能差幾筆）
    ② 持股重疊（金額權重）★ ＝ 逐日 Σ_檔 min(甲該檔市值 ÷ 甲權益, 乙該檔市值 ÷ 乙權益)；市值 ＝ 買進金額 × 收盤 ÷ 進場價（引擎 hold_val 同式），
       持有 ＝ [買進日, 賣出日)；平均、中位、逐年（主窗、早年窗）；〔另報等權槽口徑 ＝ freq 已交〕
    ③ 日報酬相關 ＝ 段內兩條權益逐日報酬的 Pearson 相關，探索、確認分開（早年一段）
 P7 正式跑另報（登錄 §四）：
    被剔除 vs 留下 ★ ＝ 原版實際成交依旗標分「族群轉強（只買版會留）」與「否（只買版剔除）」；被換掉 ★ ＝ 原版買進不在優先版 vs 優先版換進（不在原版）；
       每筆淨報酬 ＝ 賣出金額 ÷ 買進金額 − 1 − 0.585%（資料尾仍持有不算、照報筆數）；依買進日落段；營飆 ＝ 每顆平均的中位
    換手 ＝ 段內買進筆數 ÷ 年、買進金額 ÷ 平均權益 ÷ 年（researchYL_integrate.stats 同式，年 ＝ 交易日 ÷ 245）；平均持股、現金比例 ＝ 1 − hold_val ÷ 權益
    真實成本版 ★ ＝ researchSlip「現實版（C1 0.3%＋C2 50 萬＋C3＋C4）」，走 researchYLSell5.slip_setup／slip_run（只主世界、原版與只買版；
       優先版等同原版、引擎 pick 參數不經過 slip_run ⇒ 不另算）
 P8 必附：「額外策略、與正式營量營飆分開；正式規則不動」「想法來自產業 seq111，看過同期結果才提」「營量、營飆本身已看過結果」；
    優先版固定句（seq502）並引用重疊數字；N_組合 ＋2（只買版兩格）；早年附 reduce_v2 約 0.3% 與上櫃早年註；結尾「描述，不是買賣建議」
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import pickle
import subprocess
import sys
import time
from collections import Counter, defaultdict, deque
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchGroupRevUp_freq as M           # noqa: E402  模擬、分組（⛔ 不另寫）
from backtest import research11 as R                        # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402
from backtest import researchAddOn as AO                    # noqa: E402  worlds
from backtest import researchAscTri as AS                   # noqa: E402  label、ratio
from backtest import benchmark_rejudge as BR                # noqa: E402  read_series、bstat
from backtest import researchPTH_freq as PFQ                # noqa: E402  month_ends
from backtest import researchPTH10vsYL as PV                # noqa: E402  t975
from backtest import researchYL_integrate as IG             # noqa: E402  sha、YL、YF
from backtest import strategy_lock as SLK                   # noqa: E402

TIME = "2026-11-11 10:08（台北）"
RULING = "seq503"
RULINGS_NEED = ("seq501", "seq502", "seq503")
OUT = "backtest/resultsGroupRevUp/formal"
NSEED = 200
if os.environ.get("GRF_QUICK"):                              # 煙霧測試（不是交件）：3 顆、輸出另一個夾
    NSEED, OUT = 3, "/tmp/grf_quick"
WNM = {"main": "主", "early": "早年"}
SEGS = {"main": ("探索", "確認", "主窗"), "early": ("早年",)}
JSEG = ("探索", "確認")
NEFF_MIN = 24
COST = 0.00585
TRI_SRC = "git:origin/main:data/history/market_tri.csv"
SENT = ["額外策略、與正式營量營飆分開；正式規則不動", "想法來自產業 seq111，看過同期結果才提", "營量、營飆本身已看過結果"]
PRIO_SENT = "名額不夠時先買族群也轉強的，九成以上買到的和原版一樣，等於原版；有差別的是『只買版』。"
NOTE_EARLY = "早年：只描述（旗標＝自建 v2）；含減資假飆股約 0.3%（reduce_v2；剩 22 筆未解釋）；上櫃 2007-07～12 除權息未還原；上櫃減資 2007～2012 為偵測、非官方；2005-01～2007-06 只有上市"
_F: dict = {}
LOGF = None


def log(x):
    s = f"[{time.strftime('%H:%M:%S')}] {x}"
    print(s, flush=True)
    if LOGF:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(s + "\n")


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


# ═════════════ P0 閘 ═════════════
def gate_args(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--formal", action="store_true")
    ap.add_argument("--ruling", default=None)
    ap.add_argument("--procs", type=int, default=3)
    a = ap.parse_args(argv)
    if not a.formal:
        raise SystemExit(f"⛔ 正式跑要 --formal --ruling {RULING}")
    if a.ruling is None:
        raise SystemExit(f"⛔ 缺裁定號：要 --formal --ruling {RULING}")
    if a.ruling != RULING:
        raise SystemExit(f"⛔ 裁定號不符：收到 {a.ruling!r}，要 {RULING}")
    return a


def ruling_verify(mailbox=None):
    mb = mailbox or M.MAILBOX
    got = {}
    for sq in RULINGS_NEED:
        fs = [f for f in glob.glob(os.path.join(mb, "*.md")) if sq in os.path.basename(f) and "裁定線" in os.path.basename(f)]
        if not fs:
            raise SystemExit(f"⛔ 信箱找不到裁定 {sq}")
        got[sq] = os.path.basename(sorted(fs)[0])
    return got


def lock_check(tag):
    diff = SLK.check()
    log(f"[策略鎖 {tag}] {'相符（' + str(len(SLK.digest())) + ' 支）' if not diff else diff}")
    if diff:
        raise SystemExit(f"⛔ 策略鎖不符：{diff}")
    return {"時點": tag, "相符": True, "支數": len(SLK.digest())}


def same_col(a, b):
    a = pd.Series(a).reset_index(drop=True); b = pd.Series(b).reset_index(drop=True)
    if len(a) != len(b):
        return False
    if a.dtype.kind in "fc" or b.dtype.kind in "fc":
        x = pd.to_numeric(a, errors="coerce").to_numpy(float); y = pd.to_numeric(b, errors="coerce").to_numpy(float)
        return bool(np.all((x == y) | (np.isnan(x) & np.isnan(y))))
    return bool((a.astype(str) == b.astype(str)).all())


def attach_g(S, W):
    """freq 訊號表 S 與 AO 世界 SIG[False] 逐列相同才接真實 g_H60／g_H120。"""
    base = W["SIG"][False].reset_index(drop=True)
    bad = [c for c in ("sid", "pos", "entry_pos", "xpos_H60", "xpos_H120", "relvol") if not same_col(S[c], base[c])]
    if bad:
        raise SystemExit(f"⛔ freq 訊號表與世界 SIG 不同欄：{bad}")
    gk = set(zip(W["SIG"][True]["sid"].astype(str), W["SIG"][True]["entry_pos"].astype(int)))
    sk = set(zip(S.loc[S["gated"], "sid"].astype(str), S.loc[S["gated"], "entry_pos"].astype(int)))
    if gk != sk:
        raise SystemExit(f"⛔ 閘內列不同：{len(gk ^ sk)}")
    S = S.copy()
    S["g_H60"] = base["g_H60"].to_numpy(float); S["g_H120"] = base["g_H120"].to_numpy(float)
    return S, {"列": int(len(S)), "閘內": int(len(sk)), "欄相同": True}


def cand_gate(S, wn, cal):
    ref = pd.read_csv(os.path.join(M.OUT_IND, "cand_yearly.csv"))
    ref = ref[ref["世界"] == wn]
    bad = 0; n = 0
    for st in M.STRATS:
        s = M.cell_sig(S, st, "原版")
        yy = np.array([cal[int(e)].year for e in s["entry_pos"]])
        for Y in sorted(set(yy)):
            g = s[yy == Y]
            r = ref[(ref["策略"] == st) & (ref["年"] == Y)]
            n += 1
            bad += int(len(r) != 1 or int(r["候選"].iloc[0]) != len(g) or int(r["族群轉強"].iloc[0]) != int(g["grp"].sum()))
    return {"年×策略": n, "不符": bad}


def dry_repro(wn, Sfreq):
    """乾跑重現：freq.job（價格 1）對 ~/grpwork/sim_<世界>_industry.pkl 的三版買進。"""
    P = pickle.load(open(os.path.join(M.WORK, f"world_{wn}.pkl"), "rb"))
    SIM = pickle.load(open(os.path.join(M.WORK, f"sim_{wn}_industry.pkl"), "rb"))
    M._W.clear(); M._W.update(P=P, S=Sfreq, ones={s: np.ones(P["NP"]) for s in P["sids"]})
    bad = 0; n = 0
    for st, r in (("營量", 0), ("營飆", 0), ("營飆", 1), ("營飆", 2)):
        res = M.job((wn, st, r))
        ref = next(x for x in SIM if x["st"] == st and x["r"] == r)
        for v in M.VERS:
            n += 1; bad += int(res["ver"][v]["buys"] != ref["ver"][v]["buys"])
    return P, {"比對（策略×種子×版）": n, "不同": bad}


# ═════════════ 逐筆、逐日 ═════════════
def pos_book(au):
    """audit ⇒ [(sid, 買進 t, 賣出 t 或 None, 買進金額, 進場價, 賣出金額 或 None)]；同檔同時只持一筆 ⇒ 依時間 FIFO 配對。"""
    openq = defaultdict(deque); out = []
    for a in au:
        sid = str(a["sid"])
        if a["side"] == "buy":
            rec = [sid, int(a["t"]), None, float(a["amt"]), float(a["px"]), None]
            out.append(rec); openq[sid].append(rec)
        else:
            if openq[sid]:
                rec = openq[sid].popleft(); rec[2] = int(a["t"]); rec[5] = float(a["amt"])
    return [tuple(x) for x in out]


def pos_values(pb, closes, NP):
    """{sid: 逐日市值}；持有 [買進, 賣出)（未賣 ⇒ 到 NP）；市值 ＝ 買進金額 × 收盤 ÷ 進場價（引擎 hold_val 同式）。"""
    V = {}
    for sid, tb, ts, amt, px, _ in pb:
        te = NP if ts is None else ts
        if sid not in V:
            V[sid] = np.zeros(NP)
        V[sid][tb:te] += amt * np.asarray(closes[sid][tb:te], float) / px
    return V


def amt_overlap(VA, eA, VB, eB, NP):
    """逐日 Σ_檔 min(甲權重, 乙權重)。"""
    ov = np.zeros(NP)
    with np.errstate(invalid="ignore", divide="ignore"):
        for sid in set(VA) & set(VB):
            ov += np.minimum(VA[sid] / eA, VB[sid] / eB)
    return np.nan_to_num(ov)


def seg_points(ME, x, y):
    return np.array(sorted({x, y} | {int(m) for m in ME if x < m < y}), int)


# ═════════════ 工作（一顆種子、三版）═════════════
def job(args):
    wn, st, r = args
    F = _F[wn]; S = F["S"]; NP = F["NP"]; cal = F["cal"]; segs = F["segp"]
    out = {"wn": wn, "st": st, "r": r, "ver": {}, "pair": {}}
    BK = {}
    for v in M.VERS:
        sig = M.cell_sig(S, st, v, dry=False)
        buys, sells, o, au = M.run_engine(sig, st, v, r, F["closes"], NP, F["SF"], opens=F["opens"], full=True)
        eq = np.asarray(o["equity"], float); hv = np.asarray(o["hold_val"], float)
        f_, e_ = int(o["first"]), int(o["end"])
        pb = pos_book(au)
        V = pos_values(pb, F["closes"], NP)
        tot = np.sum(list(V.values()), axis=0) if V else np.zeros(NP)
        hvd = float(np.max(np.abs(tot[f_:e_] - hv[f_:e_]) / eq[f_:e_])) if e_ > f_ else 0.0
        rec = {"eq_sha": IG.sha(eq), "hv閘": hvd, "seg": {}}
        bkey = {(t, s) for t, s in buys}
        hc = M.held_count(M.intervals(buys, sells, NP), NP)
        bamt = Counter()
        for sid, tb, ts, amt, px, sa in pb:
            bamt[tb] += amt
        for sg, (x, y) in segs.items():
            c, m, _ = RR.win_metrics(eq, f_, e_, x, y)
            pts = F["pts"][sg]
            yrs = (y - x + 1) / 245.0
            bs = [(t, s) for t, s in buys if x <= t <= y]
            rec["seg"][sg] = {"年化": float(c), "回落": float(m), "月報酬": eq[pts[1:]] / eq[pts[:-1]] - 1.0,
                              "有效月數": len({cal[t].strftime("%Y-%m") for t, _ in bs}), "買進": len(bs), "買進每年": len(bs) / yrs,
                              "換手每年": float(sum(bamt[t] for t in range(x, y + 1)) / np.mean(eq[x:y + 1]) / yrs),
                              "平均持股": float(np.mean(hc[x:y + 1])),
                              "現金比例": float(1.0 - np.mean(hv[x:y + 1] / eq[x:y + 1]))}
        out["ver"][v] = rec
        BK[v] = {"eq": eq, "V": V, "bkey": bkey, "pb": pb}
    # 重疊度
    yrs_ = cal.year.to_numpy()
    for a, b in M.PAIRS:
        A, B = BK[a], BK[b]
        ov = amt_overlap(A["V"], A["eq"], B["V"], B["eq"], NP)
        z = {}
        for sg, (x, y) in segs.items():
            ka = {k for k in A["bkey"] if x <= k[0] <= y}; kb = {k for k in B["bkey"] if x <= k[0] <= y}
            ra = A["eq"][x + 1:y + 1] / A["eq"][x:y] - 1.0; rb = B["eq"][x + 1:y + 1] / B["eq"][x:y] - 1.0
            cc = float(np.corrcoef(ra, rb)[0, 1]) if (np.std(ra) > 0 and np.std(rb) > 0) else float("nan")
            z[sg] = {"買進重疊÷前者": len(ka & kb) / len(ka) if ka else None, "買進重疊÷後者": len(ka & kb) / len(kb) if kb else None,
                     "金額持股重疊_平均": float(np.mean(ov[x:y + 1])), "金額持股重疊_中位": float(np.median(ov[x:y + 1])), "日報酬相關": cc}
        wx, wy = segs["主窗"] if "主窗" in segs else segs["早年"]
        z["逐年"] = {int(Y): float(np.mean(ov[np.flatnonzero((yrs_ == Y) & (np.arange(len(cal)) >= wx) & (np.arange(len(cal)) <= wy))]))
                    for Y in sorted(set(yrs_[wx:wy + 1]))}
        out["pair"][f"{a}vs{b}"] = z
    # 被剔除／被換掉 vs 留下
    fl = F["flag"]
    pbo = BK["原版"]["pb"]; kp = BK["優先版"]["bkey"]; ko = BK["原版"]["bkey"]
    sp = {}
    for sg, (x, y) in segs.items():
        def nets(rows):
            v_ = [sa / amt - 1.0 - COST for sid, tb, ts, amt, px, sa in rows if sa is not None]
            return {"筆": len(rows), "已賣筆": len(v_), "平均": float(np.mean(v_)) if v_ else None, "中位": float(np.median(v_)) if v_ else None}
        ro = [p for p in pbo if x <= p[1] <= y]
        sp[sg] = {"原版_族群轉強（只買版留下）": nets([p for p in ro if fl.get((p[1], p[0]), False)]),
                  "原版_非族群轉強（只買版剔除）": nets([p for p in ro if not fl.get((p[1], p[0]), False)]),
                  "原版_被優先版換掉": nets([p for p in ro if (p[1], p[0]) not in kp]),
                  "優先版_換進（不在原版）": nets([p for p in BK["優先版"]["pb"] if x <= p[1] <= y and (p[1], p[0]) not in ko]),
                  "只買版_全部": nets([p for p in BK["只買版"]["pb"] if x <= p[1] <= y])}
    out["split"] = sp
    return out


# ═════════════ 彙總 ═════════════
def qd(v):
    v = np.asarray([x for x in v if x is not None and np.isfinite(x)], float)
    if not len(v):
        return {"中位": None, "p10": None, "p90": None}
    return {"中位": float(np.median(v)), "p10": float(np.percentile(v, 10)), "p90": float(np.percentile(v, 90))}


def mci(d):
    d = np.asarray(d, float); n = len(d)
    if n < 3:
        return {"月數": n, "平均": None, "CI95": [None, None]}
    se = float(np.std(d, ddof=1)) / np.sqrt(n); tq = PV.t975(n - 1)
    return {"月數": n, "平均": float(d.mean()), "中位": float(np.median(d)), "CI95": [float(d.mean() - tq * se), float(d.mean() + tq * se)],
            "正的月比例": float((d > 0).mean())}


def verdict(st, v, cells):
    if v == "優先版":
        return "等同原版（只描述）"
    if v == "原版":
        return "對照（只描述）"
    if st == "營飆":
        return "還沒測（依構造）"
    ex, cf = cells["探索"], cells["確認"]
    if min(ex["有效月數"], cf["有效月數"]) < NEFF_MIN:
        return "還沒測"
    if ex["對大盤"] == "合格" and cf["對大盤"] == "合格":
        return "合格（暫定）"
    if ex["對大盤"] in ("合格", "另列") and cf["對大盤"] in ("合格", "另列"):
        return "另列"
    return "不合格"


def aggregate(wn, RES, W, tri):
    cal = W["cal"]; segs = W["segp"]; F = _F[wn]
    CELL, PAIR, SPLIT, OVY, SEEDS = [], [], [], [], []
    for st in M.STRATS:
        rs = sorted([x for x in RES if x["wn"] == wn and x["st"] == st], key=lambda z: z["r"])
        cells_v = {}
        for v in M.VERS:
            cells_v[v] = {}
            for sg, (x, y) in segs.items():
                cs = [z["ver"][v]["seg"][sg]["年化"] for z in rs]; ms = [z["ver"][v]["seg"][sg]["回落"] for z in rs]
                for z in rs:
                    SEEDS.append({"世界": wn, "策略": st, "版": v, "段": sg, "r": z["r"], "年化": z["ver"][v]["seg"][sg]["年化"], "回落": z["ver"][v]["seg"][sg]["回落"]})
                c, m = float(np.median(cs)), float(np.median(ms))
                bt = BR.bstat(cal, tri, x, y)
                b50 = RR.bench_row(cal, np.asarray(W["bench"], float), x, y + 1)
                pts = F["pts"][sg]
                tm = tri[pts[1:]] / tri[pts[:-1]] - 1.0
                mr = np.mean([z["ver"][v]["seg"][sg]["月報酬"] for z in rs], axis=0)
                m0 = rs[0]["ver"][v]["seg"][sg]["月報酬"]
                row = {"世界": wn, "策略": st, "版": v, "段": sg, "段起": str(cal[x].date()), "段尾": str(cal[y].date()), "種子數": len(rs),
                       "年化": c, "回落": m, "比值": AS.ratio(c, m), "年化_p10": qd(cs)["p10"], "年化_p90": qd(cs)["p90"],
                       "回落_p10": qd(ms)["p10"], "回落_p90": qd(ms)["p90"], "年化_r0": cs[0], "回落_r0": ms[0],
                       "大盤年化": bt["cagr"] if bt else None, "大盤回落": bt["mdd"] if bt else None, "大盤比值": bt["ratio"] if bt else None,
                       "對大盤差": (c - bt["cagr"]) if bt else None, "對大盤": AS.label(c, m, bt) if bt else "—",
                       "逐顆合格比例": float(np.mean([AS.label(a_, b_, bt) == "合格" for a_, b_ in zip(cs, ms)])) if bt else None,
                       "0050年化": b50["cagr"], "0050回落": b50["mdd"], "對0050（只一欄）": AS.label(c, m, b50)}
                ce = mci(mr - tm); c0 = mci(m0 - tm)
                row.update({"月超額平均": ce["平均"], "月超額CI下": ce["CI95"][0], "月超額CI上": ce["CI95"][1], "月數": ce["月數"],
                            "月超額正比例": ce.get("正的月比例"), "r0月超額平均": c0["平均"], "r0月超額CI下": c0["CI95"][0], "r0月超額CI上": c0["CI95"][1]})
                for k in ("有效月數", "買進", "買進每年", "換手每年", "平均持股", "現金比例"):
                    row[k] = float(np.median([z["ver"][v]["seg"][sg][k] for z in rs]))
                cells_v[v][sg] = row
        for v in M.VERS:
            vd = verdict(st, v, cells_v[v]) if wn == "main" else "早年只描述"
            for sg in segs:
                cells_v[v][sg]["判語"] = vd
                CELL.append(cells_v[v][sg])
        for pk in rs[0]["pair"]:
            for sg in segs:
                row = {"世界": wn, "策略": st, "配對": pk, "段": sg}
                for k in rs[0]["pair"][pk][sg]:
                    qq = qd([z["pair"][pk][sg][k] for z in rs])
                    row[k] = qq["中位"]; row[k + "_p10"] = qq["p10"]; row[k + "_p90"] = qq["p90"]
                PAIR.append(row)
            for Y in rs[0]["pair"][pk]["逐年"]:
                OVY.append({"世界": wn, "策略": st, "配對": pk, "年": Y, "金額持股重疊_平均": float(np.median([z["pair"][pk]["逐年"][Y] for z in rs]))})
        for sg in segs:
            for k in rs[0]["split"][sg]:
                row = {"世界": wn, "策略": st, "段": sg, "組": k}
                for f in ("筆", "已賣筆", "平均", "中位"):
                    row[f] = float(np.median([z["split"][sg][k][f] for z in rs if z["split"][sg][k][f] is not None])) \
                        if any(z["split"][sg][k][f] is not None for z in rs) else None
                SPLIT.append(row)
    return CELL, PAIR, SPLIT, OVY, SEEDS


def slip_part(WS, S, procs):
    """P7 真實成本版：researchYLSell5.slip_setup／slip_run（主世界；原版、只買版）。"""
    from backtest import researchYLSell5 as YS
    W = WS["主"]
    YS._G["COST0"] = R.COST
    SL, X = YS.slip_setup(W, procs, log)
    res = {}
    for st in M.STRATS:
        for v in ("原版", "只買版"):
            sig = M.cell_sig(S, st, v, dry=False)
            rr = YS.slip_run(SL, X, W, st, sig, False, list(range(1 if st == "營量" else NSEED)))
            res[f"{st}·{v}"] = {sg: {"年化中位": float(np.median([q["met"][sg][0] for q in rr])), "回落中位": float(np.median([q["met"][sg][1] for q in rr]))}
                                for sg in W["segp"]}
            log(f"[現實版] {st}·{v} {len(rr)} 顆")
    if abs(R.COST - YS._G["COST0"]) > 1e-15:
        raise SystemExit("⛔ 現實版跑完引擎成本沒還原")
    return res, YS.SLIP_ARM


# ═════════════ 主流程 ═════════════
def run(a):
    T0 = time.time()
    A = {"讀法寫死": TIME, "開跑": now_tpe() + "（台北）", "種子": NSEED}
    A["登錄"] = M.check_reg(); A["裁定"] = ruling_verify(); log(f"[登錄] {A['登錄']}｜[裁定] {A['裁定']}")
    A["策略鎖"] = [lock_check("開跑前")]
    if abs(R.COST - COST) > 1e-15:
        raise SystemExit(f"⛔ 引擎成本 {R.COST} ≠ 0.585%")
    WS = AO.worlds(log, a.procs)
    tri_s = BR.read_series(TRI_SRC)
    tri_sha = subprocess.run(["git", "rev-parse", "origin/main"], capture_output=True, text=True).stdout.strip()
    gates = {}
    for wn in ("main", "early"):
        W = WS[WNM[wn]]
        Gp = pickle.load(open(os.path.join(M.WORK, f"groups_{wn}_industry.pkl"), "rb"))
        P, dr = dry_repro(wn, Gp["S"])
        gates[f"{wn} 乾跑重現"] = dr
        if dr["不同"]:
            raise SystemExit(f"⛔ {wn} 乾跑重現不符 {dr}")
        if not (len(P["cal"]) == len(W["cal"]) and (P["cal"] == W["cal"]).all() and P["NP"] == W["NP"] and P["SF"] == W["SF"]):
            raise SystemExit(f"⛔ {wn} freq 世界與 AddOn 世界不同（日曆／NP／SF）")
        S, ag = attach_g(Gp["S"], W)
        gates[f"{wn} 訊號表接 g"] = ag
        cg = cand_gate(S, wn, W["cal"])
        gates[f"{wn} 候選逐年族群轉強 ＝ freq_industry"] = cg
        if cg["不符"]:
            raise SystemExit(f"⛔ {wn} 候選逐年不符 freq_industry {cg}")
        ME, _ = PFQ.month_ends(W["cal"])
        tri = np.r_[tri_s.reindex(W["cal"]).ffill().to_numpy(float), [np.nan] * (W["NP"] - len(W["cal"]))]
        _F[wn] = {"S": S, "NP": W["NP"], "cal": W["cal"], "segp": W["segp"], "closes": W["closes"], "opens": W["opens"], "SF": W["SF"],
                  "pts": {sg: seg_points(ME, x, y) for sg, (x, y) in W["segp"].items()}, "tri": tri,
                  "flag": dict(zip(zip(S["entry_pos"].astype(int), S["sid"].astype(str)), S["grp"].astype(bool)))}
        gates[f"{wn} 大盤報酬指數補值日"] = int(tri_s.reindex(W["cal"]).isna().sum())
        log(f"[{wn}] 閘 {dr}｜{ag}｜{cg}")
    jobs = [(wn, "營量", 0) for wn in ("main", "early")] + [(wn, "營飆", r) for wn in ("main", "early") for r in range(NSEED)]
    RES = []
    with Pool(a.procs) as pool:
        for i, z in enumerate(pool.imap_unordered(job, jobs, chunksize=2)):
            RES.append(z)
            if (i + 1) % 40 == 0:
                log(f"  真價格 {i + 1}/{len(jobs)} {time.time() - T0:.0f}s")
    # 原版 eq_sha 閘、hold_val 閘
    ref = pd.read_csv("backtest/resultsYL_integrate/seeds.csv.gz", dtype={"eq_sha": str}, usecols=["世界", "格", "r", "eq_sha"])
    REF = {(w, k, int(r)): s for w, k, r, s in zip(ref["世界"], ref["格"], ref["r"], ref["eq_sha"])}
    nb = sum(int(z["ver"]["原版"]["eq_sha"] != REF.get((WNM[z["wn"]], IG.YL if z["st"] == "營量" else IG.YF, z["r"]))) for z in RES)
    gates["原版 eq_sha ≠ resultsYL_integrate（條數）"] = nb
    gates["逐日持股市值重建 vs hold_val 最大相對差"] = float(max(z["ver"][v]["hv閘"] for z in RES for v in M.VERS))
    log(f"[閘] 原版 eq_sha 不同 {nb}／{len(RES)}｜hold_val {gates['逐日持股市值重建 vs hold_val 最大相對差']:.2e}")
    if nb:
        raise SystemExit("⛔ 原版權益與正式營量 v1／營飆 v1 不同")
    if gates["逐日持股市值重建 vs hold_val 最大相對差"] > 1e-9:
        raise SystemExit("⛔ 持股市值重建與引擎 hold_val 不符")
    CELL, PAIR, SPLIT, OVY, SEEDS = [], [], [], [], []
    for wn in ("main", "early"):
        c_, p_, s_, o_, z_ = aggregate(wn, RES, WS[WNM[wn]], _F[wn]["tri"])
        CELL += c_; PAIR += p_; SPLIT += s_; OVY += o_; SEEDS += z_
    SLIP, arm = slip_part(WS, _F["main"]["S"], a.procs)
    A.update({"閘": gates, "大盤報酬指數": f"{TRI_SRC}（origin/main {tri_sha}）", "現實版": {"臂": arm, "值": SLIP}})
    A["策略鎖"].append(lock_check("跑完"))
    A["耗時秒"] = round(time.time() - T0)
    write_all(A, CELL, PAIR, SPLIT, OVY, SEEDS)
    log(f"[完成] {time.time() - T0:.0f}s ⇒ {OUT}")


# ═════════════ 輸出 ═════════════
def pc(x, d=1, sign=False):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "—"
    return f"{100 * x:+.{d}f}%" if sign else f"{100 * x:.{d}f}%"


def f2(x):
    return "—" if x is None or not np.isfinite(x) else f"{x:.2f}"


def write_all(A, CELL, PAIR, SPLIT, OVY, SEEDS):
    os.makedirs(OUT, exist_ok=True)
    C = pd.DataFrame(CELL); Pd = pd.DataFrame(PAIR); Sp = pd.DataFrame(SPLIT); Oy = pd.DataFrame(OVY)
    for nm, df in (("cells", C), ("overlap", Pd), ("trades_split", Sp), ("overlap_yearly", Oy)):
        df.to_csv(os.path.join(OUT, f"{nm}.csv"), index=False, encoding="utf-8-sig", float_format="%.6g")
    pd.DataFrame(SEEDS).to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False, float_format="%.8g")

    def cell(wn, st, v, sg):
        return C[(C["世界"] == wn) & (C["策略"] == st) & (C["版"] == v) & (C["段"] == sg)].iloc[0].to_dict()

    def pair(wn, st, pk, sg):
        return Pd[(Pd["世界"] == wn) & (Pd["策略"] == st) & (Pd["配對"] == pk) & (Pd["段"] == sg)].iloc[0].to_dict()

    four = {}
    for st in M.STRATS:
        for v in ("只買版", "優先版"):
            four[f"{st}{v}"] = {"判語": cell("main", st, v, "探索")["判語"], **{sg: {k: cell("main", st, v, sg)[k] for k in
                                ("年化", "回落", "比值", "年化_p10", "年化_p90", "大盤年化", "大盤回落", "大盤比值", "對大盤差", "對大盤", "對0050（只一欄）",
                                 "月超額平均", "月超額CI下", "月超額CI上", "月數", "有效月數", "逐顆合格比例")} for sg in JSEG}}
    A["四格"] = four
    A["N_組合"] = "＋2（只買版兩格；裁定 seq502／503）"
    ov = {f"{st}·{sg}": {pk: {k: pair("main", st, pk, sg)[k] for k in ("買進重疊÷前者", "買進重疊÷後者", "金額持股重疊_平均", "金額持股重疊_中位", "日報酬相關")}
                         for pk in ("優先版vs原版", "只買版vs原版", "只買版vs優先版")} for st in M.STRATS for sg in JSEG}
    A["重疊度"] = ov
    y_, f_ = four["營量只買版"], four["營飆只買版"]

    def seg_s(z, sg):
        return f"{sg} {pc(z[sg]['年化'])} 對大盤 {pc(z[sg]['大盤年化'])}、比值 {f2(z[sg]['比值'])} 對 {f2(z[sg]['大盤比值'])}（{z[sg]['對大盤']}）"
    po = {st: {sg: ov[f"{st}·{sg}"]["優先版vs原版"] for sg in JSEG} for st in M.STRATS}
    A["結果句"] = [f"營量只買版：{seg_s(y_, '探索')}；{seg_s(y_, '確認')} ⇒ {y_['判語']}",
                 f"營飆只買版：還沒測（依構造，裁定 seq503 事先固定）；只描述：{seg_s(f_, '探索')}；{seg_s(f_, '確認')}",
                 PRIO_SENT + "（優先版對原版買進重疊：" + "；".join(
                     f"{st} 探索 {pc(po[st]['探索']['買進重疊÷前者'])}、確認 {pc(po[st]['確認']['買進重疊÷前者'])}，金額持股重疊 {pc(po[st]['探索']['金額持股重疊_平均'])}／"
                     f"{pc(po[st]['確認']['金額持股重疊_平均'])}，日報酬相關 {f2(po[st]['探索']['日報酬相關'])}／{f2(po[st]['確認']['日報酬相關'])}" for st in M.STRATS) + "）",
                 "N_組合 ＋2（只買版兩格）；優先版兩格不計、不進全策略排名"] + SENT
    json.dump(A, open(os.path.join(OUT, "result.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=lambda o: o.item() if hasattr(o, "item") else str(o))
    L = ["# 營量／營飆加族群營收也轉強（只買版、優先版）額外策略　正式跑", "",
         f"登錄 台股 seq2 sha {A['登錄']['sha16']}（{A['登錄']['bytes']} B，相符）｜裁定 seq501 §三、seq502、seq503（閘 `--formal --ruling seq503`）｜"
         f"讀法寫死 {TIME}｜開跑 {A['開跑']}｜回測線計算子代理", "",
         "｜".join(SENT), "",
         f"N_組合 {A['N_組合']}｜大盤 ＝ {A['大盤報酬指數']}｜營飆 ＝ 200 顆中位〔p10～p90〕、營量 ＝ r0 一條｜確認段到 2026-08-24（正式窗尾）", "",
         "## 一、四格主表（各自對大盤報酬指數；兩段都合格才合格，最多「合格（暫定）」）", "",
         "| 格 | 判語 | 段 | 年化 | 最大回落 | 年化÷\\|回落\\| | 大盤 年化／回落／比值 | 對大盤差 | 對大盤標籤 | 月超額平均〔95% CI〕 | 有效月數 | 0050 欄 |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for st in M.STRATS:
        for v in ("只買版", "優先版"):
            for sg in JSEG:
                c = cell("main", st, v, sg)
                yr = pc(c["年化"])
                if st == "營飆":
                    yr += f"〔{pc(c['年化_p10'])}～{pc(c['年化_p90'])}〕"
                L.append(f"| {st}{v} | {c['判語']} | {sg} | {yr} | {pc(c['回落'])} | {f2(c['比值'])} | {pc(c['大盤年化'])}／{pc(c['大盤回落'])}／{f2(c['大盤比值'])} | "
                         f"{pc(c['對大盤差'], sign=True)} | {c['對大盤'] if v == '只買版' and st == '營量' else c['對大盤'] + '（只描述）'} | "
                         f"{pc(c['月超額平均'], 2, True)}〔{pc(c['月超額CI下'], 2, True)}～{pc(c['月超額CI上'], 2, True)}〕 | {c['有效月數']:.0f} | {c['對0050（只一欄）']} |")
    L += ["", "- 營飆只買版：裁定 seq503 事先固定「還沒測（依構造）」（確認段有效月數 21 ＜ 24），上表報酬、標籤只描述。",
          f"- 優先版兩格：撤判、只描述、標「等同原版」、⛔ 不進全策略排名（seq502）。{PRIO_SENT}",
          "- 月超額 CI：每月一群、描述用、⛔ 不進判語；持有 60／120 日 ⇒ 月與月不獨立、CI 偏窄。", ""]
    L += ["## 二、對原版（只描述，⛔ 不據此改正式規則）", "",
          "| 策略 | 段 | 原版 年化／回落／比值 | 只買版 年化／回落／比值 | 優先版 年化／回落／比值 | 原版 對大盤 | 平均持股 原／只買 | 現金比例 原／只買 | 買進每年 原／只買 | 金額換手每年 原／只買 |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for st in M.STRATS:
        for sg in JSEG:
            o_, b_, p_ = cell("main", st, "原版", sg), cell("main", st, "只買版", sg), cell("main", st, "優先版", sg)
            L.append(f"| {st} | {sg} | {pc(o_['年化'])}／{pc(o_['回落'])}／{f2(o_['比值'])} | {pc(b_['年化'])}／{pc(b_['回落'])}／{f2(b_['比值'])} | "
                     f"{pc(p_['年化'])}／{pc(p_['回落'])}／{f2(p_['比值'])} | {o_['對大盤']} | {o_['平均持股']:.1f}／{b_['平均持股']:.1f} | "
                     f"{pc(o_['現金比例'])}／{pc(b_['現金比例'])} | {o_['買進每年']:.1f}／{b_['買進每年']:.1f} | {o_['換手每年']:.2f}／{b_['換手每年']:.2f} |")
    L += ["", "## 三、重疊度（主段；營飆 200 顆中位）", "",
          "| 策略 | 段 | 配對 | ① 買進重疊 ÷前者／÷後者 | ② 金額持股重疊 平均／中位 | ③ 日報酬相關 |", "|---|---|---|---|---|---|"]
    for st in M.STRATS:
        for sg in JSEG:
            for pk in ("優先版vs原版", "只買版vs原版", "只買版vs優先版"):
                p = pair("main", st, pk, sg)
                L.append(f"| {st} | {sg} | {pk.replace('vs', ' vs ')} | {pc(p['買進重疊÷前者'])}／{pc(p['買進重疊÷後者'])} | "
                         f"{pc(p['金額持股重疊_平均'])}／{pc(p['金額持股重疊_中位'])} | {f2(p['日報酬相關'])} |")
    L += ["", "逐年金額持股重疊：overlap_yearly.csv（主窗、早年窗）。", "",
          "## 四、被剔除／被換掉 vs 留下（每筆淨報酬，扣 0.585%；主段；只描述）", "",
          "| 策略 | 段 | 組 | 筆 | 平均 | 中位 |", "|---|---|---|---|---|---|"]
    for r_ in SPLIT:
        if r_["世界"] == "main" and r_["段"] in JSEG:
            L.append(f"| {r_['策略']} | {r_['段']} | {r_['組']} | {r_['筆']:.0f} | {pc(r_['平均'], 2, True)} | {pc(r_['中位'], 2, True)} |")
    L += ["", "營飆的筆、平均、中位 ＝ 200 顆各自的值取中位；資料尾仍持有不計入平均。", "", f"## 五、真實成本版（{A['現實版']['臂']}；主世界；只描述）", "", "| 格 | 段 | 年化 | 回落 |", "|---|---|---|---|"]
    for k, z in A["現實版"]["值"].items():
        for sg in JSEG:
            L.append(f"| {k} | {sg} | {pc(z[sg]['年化中位'])} | {pc(z[sg]['回落中位'])} |")
    L += ["", "## 六、早年 2005～2014（只描述；旗標＝自建 v2）", "",
          "| 策略 | 版 | 年化 | 回落 | 比值 | 大盤 年化／回落 | 對大盤差 | 對大盤標籤（描述） | 有效月數 |", "|---|---|---|---|---|---|---|---|---|"]
    for st in M.STRATS:
        for v in M.VERS:
            c = cell("early", st, v, "早年")
            L.append(f"| {st} | {v} | {pc(c['年化'])} | {pc(c['回落'])} | {f2(c['比值'])} | {pc(c['大盤年化'])}／{pc(c['大盤回落'])} | "
                     f"{pc(c['對大盤差'], sign=True)} | {c['對大盤']} | {c['有效月數']:.0f} |")
    for st in M.STRATS:
        p = pair("early", st, "只買版vs原版", "早年"); q = pair("early", st, "優先版vs原版", "早年")
        L.append(f"- 早年重疊 {st}：優先 vs 原 買進 {pc(q['買進重疊÷前者'])}、金額持股 {pc(q['金額持股重疊_平均'])}、日報酬相關 {f2(q['日報酬相關'])}；"
                 f"只買 vs 原 買進 {pc(p['買進重疊÷前者'])}、金額持股 {pc(p['金額持股重疊_平均'])}、日報酬相關 {f2(p['日報酬相關'])}")
    L += ["", NOTE_EARLY, "", "## 七、閘", "", f"- {json.dumps(A['閘'], ensure_ascii=False, default=str)}", f"- 策略鎖：{A['策略鎖']}", "",
          "## 八、結果句（必附）", ""] + [f"- {s}" for s in A["結果句"]] + ["", "描述，不是買賣建議"]
    open(os.path.join(OUT, "結果.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


def main(argv=None):
    global LOGF
    a = gate_args(sys.argv[1:] if argv is None else argv)
    os.makedirs(OUT, exist_ok=True)
    LOGF = os.path.join(OUT, "run.log")
    log(f"[開跑] {now_tpe()}（台北）NSEED {NSEED}")
    run(a)


if __name__ == "__main__":
    main()
