# -*- coding: utf-8 -*-
"""PREREG接近52週新高組合層 seq1【正式跑】（台股策略線 登錄 sha eae8a7706bf45b1f，2026-10-20 18:47；裁定 seq396 准起草、seq398 發號 N_組合 ＋1、
組合規則與描述「過目照跑」）——回測線計算子代理。
⛔ 只計算：不 commit、不改既有程式與結果夾；researchPTH_freq（月底、進場日）、researchPTH（到期日、stock_job 逐股報酬、TYP）、researchAscTri（load_world、
label、ratio、NOTE_EARLY）、researchTurtleS2PF（simulate、verdict、成本常數）、researchDumb（eff_n 對帳用）、rerun17（win_metrics、bench_row）、
researchYL_integrate（營量 v1 世界與引擎）、researchYLvsYF（book、sha）⛔ 只 import。用語「假訊號」；⛔ 不給買賣建議。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTHpf [--procs 2] [--dry]
    乾跑（⛔ 不算任何組合報酬；只驗登錄 sha、fixture、事件重現與價格閘）：--dry
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTHpf_check
輸出 backtest/resultsPTHpf/：degeneracy.json（先寫）、PTHpf.json、PTHpf_main.csv、by_year.csv、yl.csv、random_<世界>.csv.gz、
    trades_<世界>_<臂>.csv.gz、eq_<世界>.npz、run.log

⭐ 讀法寫死：2026-10-20 19:05～19:40（台北）寫檔；寫死前 ⛔ 沒看過任何本件組合層數字（看過的只有事件層結果與頻率表）。

═══ 讀法（Q 標；登錄沒寫清楚、執行者補的都在這裡；★＝執行者定，〔 〕內為另一讀法）═══
 Q0 事件與出場 ⛔ 不另寫：世界 ＝ researchAscTri.load_world（＝ researchAscTri_freq.load_world ＋ 快取收盤、0050）；月底、進場日 ＝ researchPTH_freq.month_ends／
    entry_pos；到期日 ＝ researchPTH.exit_positions；逐股 R、出場種類、出場日 ＝ researchPTH.stock_job 原樣。
    事件 ＝ 已提交 resultsPTH/events/trades_<世界>_<格>.csv.gz 每一列（入選 ∧ 保留）；逐列比 進場日、R、出場種類、出場日 與本支重算，任一不同 ⇒ 中止、⛔ 不算組合。
    買價 P ＝ 快取還原開盤 O[e]；賣價 ＝ P×(1＋R)；價格閘：賣價 ÷ 賣出日快取收盤（ffill）− 1 ≤ 1e−9（不過 ⇒ 中止）。
 Q1 組合（登錄 §一）：帳戶分 H 份（H ＝ 6 判；3、12 描述）；第 m 個曆月（年×12＋月−1）進場的批次屬第 m mod H 份；
    ★ 各份資金各自滾、⛔ 份與份之間不再平衡（＝「每月只換其中 1 份」字面、Jegadeesh–Titman 式）〔另一讀法：每月把新批調到淨值 1/H——不跑〕。
    窗首（日曆第 0 日收盤）淨值 1 全抱 0050、各份 1/H（⛔ 不扣建倉成本，引擎慣例）＝「未滿 6 批的份放 0050」。
    批次進場日 e 開盤：該份 0050 全賣（還原開盤、0.2425%）＋ 該份現金 ⇒ 等權買進當批全部事件股（每檔 ＝ 該份資金 ÷ 當批檔數；同檔多批各自持有）。
    每檔賣出：到期收盤 ⇒ 記在到期日 X；到期日無成交（用前一根收盤）⇒ ★ 也記在 X；壞根前一根收盤強制、下市末根 ⇒ 記在該根日曆日；
    入帳 ＝ 金額 ×（1 ＋ R − 0.585%）（引擎口徑：0.585% 在賣出時對買進金額一次扣），當天留現金；隔天：該份下一批進場 ⇒ 直接用；
    否則隔天 0050 還原開盤買進（0.1425%）＝ 登錄「該份剩餘放 0050 到批次到期」。資料尾未出場 ⇒ 持有到資料尾、按收盤計值（⛔ 不賣、不扣賣出成本）。
    市值 ＝ 金額 × 快取收盤（ffill）÷ P。0050 開盤缺值 ⇒ 前一日還原收盤（＝ 海龜組合層 K2）。0050 成本照海龜組合層 K2 字面（買 0.1425%、賣 0.2425%）。
 Q2 滑價版（登錄 §二、seq369）：個股買價 ×1.005、每筆賣價 ×0.995（含強制、末根）；R_滑 ＝ 賣價×0.995 ÷ (P×1.005) − 1；市值以 P×1.005 計；
    0050 不加滑價；其餘全同主判（同一批事件）。
 Q3 段、判準 ⛔ 不另寫：段 ＝ researchAscTri_freq.SEGS（探索 2017-03-02～2021-12-30｜確認 2022-01-03～資料尾｜早年 2005 首個交易日～2014-12-31）；
    一個世界跑一次（主 2015-01-05 起、早年 2004-02-11 起）、各段切權益曲線窗：年化、回落 ＝ rerun17.win_metrics；0050 ＝ rerun17.bench_row（同窗）；
    標籤 ＝ researchAscTri.label（合格 ＝ 年化 ＞ 0050 且 年化÷|回落| ≥ 0050；另列 ＝ 只勝年化；其餘不合格）、比值 ＝ researchAscTri.ratio。
    整件 ＝ researchTurtleS2PF.verdict（主判探索、確認、滑價探索、確認、主判早年）原樣照報，再套 seq398 發號表上限：
    滑價版探索或確認不合格 ⇒ 最多另列（verdict 的「紙上合格、實務不可用」即此情形）；早年主判不合格 ⇒ 最多暫定。
    退化（seq325）：探索段平均持股 ＜ 3 ⇒ 退化不判；先寫 degeneracy.json（只含持股數）再讀任何報酬。
 Q4 必報（＝ 海龜組合層 K10 同式）：換手 ＝ 段內買進金額 ÷ 段內平均淨值 ÷ 年（年 ＝ 交易日 ÷ 245）；成本／年 ＝ 換手 × 0.585%（另報實付個股、實付 0050、合計）；
    平均持股 ＝ 段內逐日收盤持股筆數平均（買進日算、賣出日不算；★ 同檔多批算多筆，另報相異檔數）；個股、0050、待買回現金各占淨值（段內平均）；
    等效獨立檔數 ＝ researchDumb.eff_n 同式（段內每個買進日、當天持有中各筆、前 60 日日報酬兩兩相關（≥ 40 個共同值、快取原始收盤）、N ÷ (1＋(N−1)ρ̄)、段內平均）；
    ★ 以矩陣化實作（fixture 與對帳抽日對 researchDumb.eff_n）。逐筆（依買進日歸段）：勝率（R − 0.585% ＞ 0）、平均賺賠比、出場種類占比、平均持有天數；
    分年（日曆年末 ÷ 前一年末；段首年用段首）對 0050；上市／上櫃（持股市值中上櫃占比、逐筆淨報酬平均）；
    最差 12 個月（段首＋段內月底序列滾動 12 個月，報最差窗與 0050 同窗）。
 Q5 描述（⛔ 不判、不計 N）：
    ① 10 檔版 ＝ researchTurtleS2PF.simulate（主模式：10 槽、新部位 min(前一日淨值÷10, 可撥 0050)、T 開盤賣 0050 撥款、賣出當天留現金隔天買回、
       同檔不重複、同日先出後進）原樣；候選 ＝ 跳月各批事件，★ 依 PTH 由高往下（同 PTH 以 default_rng([20261023, 形成月序 j]).random 打破，＝ 事件層 R9 種子；
       隨機數依事件檔列序（代號序）配給）⇒ 傳入「不洗牌」生成器（permutation ＝ 原順序；np.random.default_rng(生成器) 原樣回傳）。
    ② 與營量 v1：營量 v1 ＝ researchYL_integrate.eng(W, YL, 0)（主 main_world、早年 early_world；原規則、⛔ 不改），持股 ＝ researchYLvsYF.book；
       閘：eq_sha ＝ resultsYL_integrate/seeds.csv.gz 同世界同格 r0。日期取兩邊共同交易日；月報酬相關（段內月底，段首為基）、日報酬相關；
       持股重疊：逐日「本件持股（相異檔）中營量也持有的比例」與反向、金額重疊 Σ min(本件權重, 營量權重)，段內平均；
       「本件與營量 v1 各半」：① 每日再平衡（r ＝ ½ r本件 ＋ ½ r營量）② 段首各半、不再平衡；年化、回落、比值、對 0050（同窗）。
       ⚠ 營量主世界資料尾 2026-08-24 ⇒ 確認段的相關、重疊、各半只到 2026-08-24；早年營量窗 2005-02-01 起。
    ③ 不跳月版組合（事件 ＝ trades_<世界>_不跳，6 份）；持有天數軸 3、12 個月（事件 ＝ trades_<世界>_跳月_3月／_12月，份數 3、12）。
    ④ 10 檔版隨機：同 ① 但候選依代號排序、由 researchTurtleS2PF.simulate 原生抽籤（default_rng([20261020, 世界, i])）挑，200 次；
       ★ 讀成「從當批前 30% 隨機挑、與 10 檔版同檔數」⇒ 看前 30% 之內「由高往下排」本身有沒有用；p ＝ 隨機 比值 ≥ 10 檔版 的比例（另報年化）。
 Q6 結果句必附：登錄 §四 四句（「單筆層兩段都比隨便買好，但組合是另一回事」「營量入選股多半本來就在 PTH 前 30%」「原文拆股調整價、本件含息還原價」
    「早年事件層結論不穩（區塊 CI 含 0）」）＋ seq396「樣本中等、單筆通過不等於組合會贏」＋ 早年附 researchAscTri.NOTE_EARLY。
"""
from __future__ import annotations

import argparse
import glob
import gzip
import hashlib
import json
import os
import sys
import time
from collections import Counter
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchPTH_freq as PT                 # noqa: E402  月底、進場日（⛔ 只 import）
from backtest import researchPTH as PTH                     # noqa: E402  exit_positions、stock_job、TYP
from backtest import researchAscTri as AS                   # noqa: E402  load_world、label、ratio、NOTE_EARLY
from backtest import researchTurtleS2PF as TS               # noqa: E402  simulate、verdict、成本常數
from backtest import researchDumb as RD                     # noqa: E402  eff_n（fixture 對帳）
from backtest import rerun17 as RR                          # noqa: E402  win_metrics、bench_row
from backtest import data as D                              # noqa: E402
from backtest import researchAddOn as RA                    # noqa: E402  log_to
from backtest import universe_gate as UG                    # noqa: E402

UG.set_gate_v2(True)

TIME = "2026-10-20 19:05～19:40（台北）"
REG_SHA = "eae8a7706bf45b1f"
MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
OUT = "backtest/resultsPTHpf"
EVD = "backtest/resultsPTH/events"
PTHJ = "backtest/resultsPTH/PTH.json"
COST = TS.COST
BC_BUY, BC_SELL, SLIP = TS.BC_BUY, TS.BC_SELL, TS.SLIP
NS = TS.NS
NRAND = 200
RSEED = 20261020
SEED_TOP = PTH.SEED_TOP
WID = {"主": 0, "早年": 1}
DEG_HOLD = 3.0
TYPN = PTH.TYP
CELLS = {"跳月": (2, 6), "不跳": (1, 6), "跳月_3月": (2, 3), "跳月_12月": (2, 12)}
ARMS = {"M": {"名": "主判：PTH 前 30% 等權、跳 1 月、6 份重疊、空位 0050", "cell": "跳月", "kind": "tr", "slip": False, "judge": True},
        "Mslip": {"名": "主判＋滑價每邊 0.5%（seq369 可執行性條款）", "cell": "跳月", "kind": "tr", "slip": True, "judge": True},
        "S10": {"名": "描述①：10 檔版（每月 PTH 由高往下補空位、空位 0050）", "cell": "跳月", "kind": "slot", "slip": False, "judge": False},
        "NOSKIP": {"名": "描述③：不跳月版（6 份）", "cell": "不跳", "kind": "tr", "slip": False, "judge": False},
        "H3": {"名": "描述：抱 3 個月（3 份）", "cell": "跳月_3月", "kind": "tr", "slip": False, "judge": False},
        "H12": {"名": "描述：抱 12 個月（12 份）", "cell": "跳月_12月", "kind": "tr", "slip": False, "judge": False}}
SENT_REG = ["單筆層兩段都比隨便買好，但組合是另一回事", "營量入選股多半本來就在 PTH 前 30%", "原文拆股調整價、本件含息還原價",
            "早年事件層結論不穩（區塊 CI 含 0）"]
SENT_396 = "樣本中等、單筆通過不等於組合會贏"
NOTE_EARLY = AS.NOTE_EARLY
_G: dict = {}


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


def reg_check(sha):
    fs = [f for f in glob.glob(os.path.join(MAILBOX, "*.md")) if f"sha{sha}" in os.path.basename(f)]
    if len(fs) != 1:
        raise SystemExit(f"⛔ 信箱找不到唯一一封登錄全文 sha{sha}：{fs}")
    b = open(fs[0], "rb").read()
    h = hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]
    if h != sha:
        raise SystemExit(f"⛔ 登錄 sha {h} ≠ {sha}")
    return os.path.basename(fs[0])


def pct(x, d=2):
    return "—" if x is None or not np.isfinite(x) else "{:+.{}f}%".format(x * 100, d)


class KeepOrder(np.random.Generator):
    """「不洗牌」生成器：permutation(n) ＝ 原順序（給 researchTurtleS2PF.simulate 依傳入順序補空位用）。"""

    def permutation(self, x):
        return np.arange(x) if isinstance(x, (int, np.integer)) else np.asarray(x).copy()


def keep_order():
    return KeepOrder(np.random.PCG64(0))


# ═════════════ 世界 ═════════════
def bench_open(W):
    D.DATA = W["data"]; cal = W["cal"]
    bo = D.load_stock("0050", "twse", cal).df["open"].to_numpy(float)
    Bc = np.asarray(W["bench"], float); Bo = bo.copy()
    nbo = np.flatnonzero(~(np.isfinite(bo) & (bo > 0)))
    for t in nbo:
        Bo[t] = Bc[t - 1] if t > 0 else Bc[0]
    W["Bc"], W["Bo"], W["nbo"] = Bc, Bo, [str(cal[t].date()) for t in nbo]


def finish_world(W):
    cal = W["cal"]
    bench_open(W)
    W["CM"] = pd.DataFrame(np.asarray(W["C"], float)).ffill(axis=1).to_numpy(float)
    W["mon"] = np.asarray(cal.year * 12 + cal.month - 1, np.int64)
    W["otc"] = np.array([W["mk"].get(s, "twse") != "twse" for s in W["sids"]])
    W["dates"] = np.array([str(d.date()) for d in cal])
    W["srank"] = np.empty(len(W["sids"]), np.int64); W["srank"][np.argsort(np.array(W["sids"]))] = np.arange(len(W["sids"]))


def build_world(wn, log):
    W = AS.load_world(wn, log)
    cal = W["cal"]
    ME, MK = PT.month_ends(cal)
    W["ME"] = ME; W["EP"] = {L: PT.entry_pos(cal, MK, L) for L in (1, 2)}
    W["XP"] = PTH.exit_positions(W)
    PT._G[wn] = W
    finish_world(W)
    return W


# ═════════════ 事件（Q0）═════════════
def load_events(W, wn, cell, RES):
    L, H = CELLS[cell]
    fr = pd.read_csv(os.path.join(EVD, f"trades_{wn}_{cell}.csv.gz"), dtype=str, keep_default_na=False)
    cal = W["cal"]; ME = W["ME"]; n0 = W["n0"]; ix = W["ix"]
    dpos = {d: i for i, d in enumerate(W["dates"])}
    jm_of = {W["dates"][p]: j for j, p in enumerate(ME)}
    tinv = {v: k for k, v in TYPN.items()}
    i_ = np.array([ix[s] for s in fr["sid"]], np.int64)
    jm = np.array([jm_of[d] for d in fr["形成月底"]], np.int64)
    e = np.array([dpos[d] for d in fr["進場日"]], np.int64)
    R = np.array([float(x) if x != "" else np.nan for x in fr["R"]])
    typ = np.array([tinv[x] for x in fr["出場種類"]], np.int8)
    sd = np.array([dpos[x] if x != "" else -1 for x in fr["出場日"]], np.int64)
    nd = Counter()
    nd["進場日≠EP"] = int((W["EP"][L][jm] != e).sum())
    for q, s in enumerate(fr["sid"]):
        r = RES[s][(L, H)]; j = jm[q]
        a_, b_ = r["R"][j], R[q]
        if not ((np.isnan(a_) and np.isnan(b_)) or abs(a_ - b_) <= 1e-12):
            nd["R"] += 1
        if int(r["T"][j]) != int(typ[q]):
            nd["出場種類"] += 1
        if int(r["S"][j]) != int(sd[q]):
            nd["出場日"] += 1
    X = W["XP"][(L, H)][jm]
    sale = np.where(np.isin(typ, (1, 2)), X, np.where(np.isin(typ, (3, 4)), sd, -1)).astype(np.int64)
    P = np.asarray(W["O"], float)[i_, e]
    px = P * (1.0 + R)
    nd["買價缺"] = int((~(np.isfinite(P) & (P > 0))).sum())
    nd["到期越界"] = int(((typ == 1) | (typ == 2)).sum() - ((X[(typ == 1) | (typ == 2)] <= n0 - 1)).sum())
    sold = sale >= 0
    rel = np.abs(px[sold] / W["CM"][i_[sold], sale[sold]] - 1.0)
    nd["賣價≠賣出日收盤(>1e-9)"] = int((rel > 1e-9).sum())
    nd["出場早於進場"] = int((sold & (sale < e)).sum())
    nd["資料尾R有值"] = int(((typ == 5) & np.isfinite(R)).sum())
    bad = {k: v for k, v in nd.items() if v}
    if bad:
        raise SystemExit(f"⛔ {wn} {cell} 事件／價格閘不過 {bad}")
    pth = np.array([float(x) for x in fr["PTH"]])
    rk = np.zeros(len(fr))
    for j in np.unique(jm):
        q = np.flatnonzero(jm == j)
        rk[q] = np.random.default_rng([SEED_TOP, int(j)]).random(len(q))
    o_ = np.lexsort((i_, e))
    ev = {"sid": fr["sid"].to_numpy()[o_], "j": i_[o_], "jm": jm[o_], "e": e[o_], "X": X[o_], "typ": typ[o_], "R": R[o_], "sd": sd[o_],
          "sale": sale[o_], "P": P[o_], "px": px[o_], "pth": pth[o_], "rk": rk[o_], "form": fr["形成月底"].to_numpy()[o_]}
    info = {"列": int(len(fr)), "最大相對差(賣價vs收盤)": float(rel.max()) if len(rel) else 0.0,
            "出場種類": {TYPN[int(k)]: int(v) for k, v in Counter(typ.tolist()).items()}, "批次數": int(len(np.unique(e)))}
    return ev, info


# ═════════════ 組合迴圈（Q1、Q2）═════════════
def tranche_sim(ev, H, W, slip, want_mv=False):
    n0 = W["n0"]; CM = W["CM"]; Bc = W["Bc"]; Bo = W["Bo"]; S_ = CM.shape[0]
    j_, e_, sale = ev["j"], ev["e"], ev["sale"]
    ep = ev["P"] * (1 + SLIP) if slip else ev["P"].copy()
    g = ev["px"] * (1 - SLIP) / ep - 1.0 if slip else ev["R"].copy()
    trn = W["mon"][e_] % H
    ue = np.unique(e_)
    batches = {int(e): np.flatnonzero(e_ == e) for e in ue}
    for e, idx in batches.items():
        if len(set(trn[idx].tolist())) != 1:
            raise SystemExit("⛔ 同一批跨兩份")
    eq = np.zeros(n0); hv = np.zeros(n0); uv = np.zeros(n0); cv = np.zeros(n0); nh = np.zeros(n0, np.int32)
    MV = np.zeros((S_, n0)) if want_mv else None
    buys, sells, etf = [], [], []
    amt_q = np.full(len(e_), np.nan); tr_q = np.full(len(e_), -1, np.int64)
    for k in range(H):
        bk = {e: idx for e, idx in batches.items() if trn[idx[0]] == k}
        u = (1.0 / H) / Bc[0]; carry = 0.0; busy = -1
        inflow = np.zeros(n0); hvk = np.zeros(n0)
        for t in range(n0):
            idx = bk.get(t)
            if idx is not None:
                if busy >= t:
                    raise SystemExit(f"⛔ 份 {k} 前一批尚未出清（{busy} ≥ {t}）")
                cap = carry; carry = 0.0
                if u > 0.0:
                    gro = u * Bo[t]; cst = gro * BC_SELL
                    cap += gro - cst; etf.append((t, -1, gro, cst)); u = 0.0
                amt = cap / len(idx)
                for q in idx:
                    s_ = int(sale[q]); end = s_ if s_ >= 0 else n0
                    if end > t:
                        v = amt * CM[j_[q], t:end] / ep[q]
                        hvk[t:end] += v; nh[t:end] += 1
                        if MV is not None:
                            MV[j_[q], t:end] += v
                    if s_ >= 0:
                        proc = amt * (1.0 + g[q] - COST)
                        inflow[s_] += proc; sells.append((s_, int(q), amt, proc)); busy = max(busy, s_)
                    else:
                        busy = n0
                    buys.append((t, int(q), amt)); amt_q[q] = amt; tr_q[q] = k
            elif carry > 0.0:
                cst = carry * BC_BUY
                u += (carry - cst) / Bo[t]; etf.append((t, 1, carry, cst)); carry = 0.0
            carry += inflow[t]
            eq[t] += u * Bc[t] + carry + hvk[t]; uv[t] += u * Bc[t]; cv[t] += carry
        hv += hvk
    if not np.all(np.isfinite(eq)):
        raise SystemExit("⛔ 權益非有限值")
    buys.sort(); sells.sort(); etf.sort()
    return {"eq": eq, "hv": hv, "u": uv, "pend": cv, "nh": nh, "buys": buys, "sells": sells, "etf": etf, "MV": MV,
            "amt": amt_q, "tranche": tr_q, "g": g, "ep": ep, "ext": sale, "j": j_}


def slot_tr(ev, slip, order):
    o_ = order
    ep = ev["P"] * (1 + SLIP) if slip else ev["P"]
    g = ev["px"] * (1 - SLIP) / ep - 1.0 if slip else ev["R"]
    return {"j": ev["j"][o_], "ent": ev["e"][o_], "ext": ev["sale"][o_], "ep": np.asarray(ep)[o_], "g": np.asarray(g)[o_], "q": np.asarray(o_)}


def slot_sim(tr, W, seed):
    S = TS.simulate(tr, W["n0"], W["CM"], W["Bc"], W["Bo"], "main", seed=seed, record=True)
    S["j"] = tr["j"]; S["ext"] = tr["ext"]; S["g"] = tr["g"]; S["ep"] = tr["ep"]; S["MV"] = None; S["q"] = tr["q"]
    return S


# ═════════════ 統計 ═════════════
def intervals(S, n0):
    """⇒ (j, tb, ts)：ts ＝ 賣出日；未賣 ⇒ n0＋1（researchDumb.eff_n 以 NP 代）。"""
    sl = {q: t for t, q, amt, proc in S["sells"]}
    out = [(int(S["j"][q]), int(t), int(sl.get(q, n0 + 1))) for t, q, amt in S["buys"]]
    return np.array(out, np.int64).reshape(-1, 3)


def uniq_count(iv, n0, nS):
    M = np.zeros((n0 + 2, nS), np.int32)
    np.add.at(M, (iv[:, 1], iv[:, 0]), 1)
    np.add.at(M, (np.minimum(iv[:, 2], n0 + 1), iv[:, 0]), -1)
    C = np.cumsum(M, axis=0)[:n0]
    return C


def effn_vec(Craw, js, t):
    """researchDumb.eff_n 同式（矩陣化）：js ＝ 當天持有中各筆的股欄（含重複）。⇒ (t, N, ρ̄, 等效)。"""
    N = len(js)
    if N == 0:
        return None
    if N == 1:
        return (t, 1, np.nan, 1.0)
    if t - 60 < 0:
        return (t, N, np.nan, np.nan)
    cc = np.asarray(Craw[np.asarray(js)][:, t - 60:t + 1], float)
    with np.errstate(invalid="ignore", divide="ignore"):
        Rm = cc[:, 1:] / cc[:, :-1] - 1.0
    Mk = np.isfinite(Rm); X = np.where(Mk, Rm, 0.0); Mf = Mk.astype(float)
    n = Mf @ Mf.T; Sx = X @ Mf.T; Sxx = (X * X) @ Mf.T; Sxy = X @ X.T
    iu = np.triu_indices(N, 1)
    nn = n[iu]; sa = Sx[iu]; sb = Sx.T[iu]; saa = Sxx[iu]; sbb = Sxx.T[iu]; sab = Sxy[iu]
    with np.errstate(invalid="ignore", divide="ignore"):
        va = saa - sa * sa / nn; vb = sbb - sb * sb / nn; cv = sab - sa * sb / nn
        ok = (nn >= 40) & (va > 0) & (vb > 0)
        r = cv[ok] / np.sqrt(va[ok] * vb[ok])
    rho = float(np.mean(r)) if len(r) else np.nan
    return (t, N, rho, N / (1 + (N - 1) * rho) if np.isfinite(rho) else np.nan)


def effn_seg(W, iv, x, y):
    days = sorted({int(t) for t in iv[:, 1] if x <= t <= y})
    res = []
    Cr = W["C"]
    for t in days:
        m = (iv[:, 1] <= t) & (t < iv[:, 2])
        z = effn_vec(Cr, iv[m, 0], t)
        if z is not None:
            res.append(z)
    return {"等效獨立檔數": float(np.nanmean([z[3] for z in res])) if res else np.nan,
            "平均ρ": float(np.nanmean([z[2] for z in res])) if res else np.nan, "買進日數": len(days),
            "買進日持有筆數平均": float(np.mean([z[1] for z in res])) if res else np.nan}


def yearly(eq, bench, cal, x, y):
    yrs = np.asarray(cal.year)
    out = {}
    base = x
    for Y in sorted(set(yrs[x:y + 1].tolist())):
        e = int(np.flatnonzero((yrs == Y) & (np.arange(len(yrs)) <= y))[-1])
        out[str(Y)] = {"本件": float(eq[e] / eq[base] - 1.0), "0050": float(bench[e] / bench[base] - 1.0),
                       "起": str(cal[base].date()), "訖": str(cal[e].date())}
        base = e
    return out


def worst12(eq, bench, cal, x, y):
    mon = np.asarray(cal.year * 12 + cal.month)
    pts = [x] + [int(t) for t in range(x, y + 1) if (t == y or mon[t + 1] != mon[t]) and t != x]
    if len(pts) < 13:
        return None
    best = None
    for k in range(12, len(pts)):
        a_, b_ = pts[k - 12], pts[k]
        r = eq[b_] / eq[a_] - 1.0
        if best is None or r < best[0]:
            best = (r, a_, b_)
    r, a_, b_ = best
    return {"最差12個月": float(r), "窗": f"{cal[a_].date()}～{cal[b_].date()}", "0050同窗": float(bench[b_] / bench[a_] - 1.0)}


def pf_stats(W, S, x, y, typ_q=None):
    """海龜組合層 seg_stats 同式（K10）。S：模擬結果；typ_q：每筆出場種類（依 q）。"""
    eq, hv, u, pend, nh = S["eq"], S["hv"], S["u"], S["pend"], S["nh"]
    yrs = (y - x + 1) / 245.0
    meq = float(np.mean(eq[x:y + 1]))
    sells = {q: (t, amt, proc) for t, q, amt, proc in S["sells"]}
    bs = [(t, q, amt) for t, q, amt in S["buys"] if x <= t <= y]
    sc = sum(amt * COST for t, q, amt, proc in S["sells"] if x <= t <= y)
    ec = sum(c[3] for c in S["etf"] if x <= c[0] <= y)
    hd = [sells[q][0] - t for t, q, amt in bs if q in sells]
    d = {"平均持股(筆)": float(np.mean(nh[x:y + 1])), "個股占淨值": float(np.mean(hv[x:y + 1] / eq[x:y + 1])),
         "0050占淨值": float(np.mean(u[x:y + 1] / eq[x:y + 1])), "待買回現金占淨值": float(np.mean(pend[x:y + 1] / eq[x:y + 1])),
         "買進筆": len(bs), "買進每年": len(bs) / yrs, "換手每年": float(sum(a_ for _, _, a_ in bs) / meq / yrs),
         "平均持有天數": float(np.mean(hd)) if hd else np.nan}
    d["成本每年(換手×0.585%)"] = d["換手每年"] * COST
    d["個股成本每年(實付)"] = float(sc / meq / yrs)
    d["0050成本每年(實付)"] = float(ec / meq / yrs)
    d["成本合計每年(實付)"] = d["個股成本每年(實付)"] + d["0050成本每年(實付)"]
    qs = [q for _, q, _ in bs]
    g = S["g"]; ext = S["ext"]
    rn = np.array([g[q] - COST for q in qs], float)
    fin = np.array([ext[q] >= 0 for q in qs], bool)
    v = rn[fin]; w_ = v[v > 0]; l_ = v[v <= 0]
    d.update({"勝率": float((v > 0).mean()) if len(v) else np.nan,
              "平均賺賠比": float(w_.mean() / abs(l_.mean())) if (len(w_) and len(l_) and l_.mean() != 0) else np.nan,
              "逐筆淨報酬平均": float(v.mean()) if len(v) else np.nan, "資料尾未出場筆": int((~fin).sum())})
    if typ_q is not None and qs:
        ty = np.array([typ_q[q] for q in qs])
        for k_, nm in TYPN.items():
            d[f"出場占比_{nm}"] = float((ty == k_).mean())
    otc = W["otc"]
    if qs:
        oq = np.array([otc[S["j"][q]] for q in qs], bool)
        d["上櫃筆數占比"] = float(oq.mean())
        d["逐筆淨報酬平均_上市"] = float(v[~oq[fin]].mean()) if (~oq[fin]).any() else np.nan
        d["逐筆淨報酬平均_上櫃"] = float(v[oq[fin]].mean()) if oq[fin].any() else np.nan
    if S.get("MV") is not None:
        mv = S["MV"][:, x:y + 1]; tot = mv.sum(0)
        with np.errstate(invalid="ignore", divide="ignore"):
            d["持股市值上櫃占比"] = float(np.nanmean(mv[otc].sum(0) / tot))
    return d


def metrics(W, eq, x, y):
    c_, m_, _ = RR.win_metrics(eq, 0, W["n0"], x, y)
    b = RR.bench_row(W["cal"], W["bench"], x, y + 1)
    return float(c_), float(m_), b


def capped(L, early_none=False):
    """seq398 發號表上限：滑價版（探索／確認）不合格 ⇒ 最多另列；早年主判不合格（或無早年段）⇒ 最多暫定。"""
    le, lc = L["主判探索"], L["主判確認"]
    if le == "合格" and lc == "合格":
        v = "合格"
    elif le in ("合格", "另列") and lc in ("合格", "另列"):
        v = "另列"
    else:
        v = "不合格"
    why = []
    if v == "合格" and (early_none or L.get("主判早年") == "不合格"):
        v = "暫定"; why.append("無早年段 ⇒ 最多暫定" if early_none else "早年主判不合格 ⇒ 最多暫定")
    if v in ("合格", "暫定") and (L["滑價探索"] == "不合格" or L["滑價確認"] == "不合格"):
        v = "另列"; why.append("滑價版有不合格段 ⇒ 最多另列（seq369）")
    return v, why


# ═════════════ 營量 v1（Q5 ②）═════════════
def yl_load(wn, log, procs):
    from backtest import researchYL_integrate as IG
    from backtest import researchYLvsYF as YV
    if wn == "主":
        Wy, _ = IG.main_world(log)
    else:
        Wy, _ = IG.early_world(log, procs)
    o, au = IG.eng(Wy, IG.YL, 0)
    eq, TR, cnt, H = YV.book(Wy, o, au)
    ref = pd.read_csv("backtest/resultsYL_integrate/seeds.csv.gz", dtype={"eq_sha": str}, float_precision="round_trip")
    b_ = ref[(ref["世界"] == wn) & (ref["格"] == IG.YL) & (ref["r"] == 0)].iloc[0]
    s = YV.sha(eq)
    if s != b_["eq_sha"]:
        raise SystemExit(f"⛔ 營量 v1 {wn} eq_sha {s} ≠ 整合件 {b_['eq_sha']}")
    cal = Wy["cal"]; n = min(len(cal), len(eq))
    out = {"dates": np.array([str(d.date()) for d in cal[:n]]), "eq": np.asarray(eq, float)[:n],
           "H": {k: (v[0][:n], v[1][:n]) for k, v in H.items()}, "sha": s, "first": int(o["first"]), "end": int(o["end"]),
           "窗": [str(cal[Wy["w0"]].date()), str(cal[min(Wy["w1"], n - 1)].date())], "w0": int(Wy["w0"]), "w1": int(min(Wy["w1"], n - 1))}
    log(f"[營量 v1 {wn}] eq_sha {s} ＝ resultsYL_integrate/seeds ✓｜窗 {out['窗']}｜trades {o['trades']}")
    return out


def yl_compare(W, S, Y, x, y):
    """本件（S：MV 必備）對營量 v1（Y）：月／日報酬相關、持股重疊、各半。"""
    dP = W["dates"]; posY = {d: i for i, d in enumerate(Y["dates"])}
    tp = np.array([t for t in range(x, y + 1) if dP[t] in posY and Y["w0"] <= posY[dP[t]] <= Y["w1"]], np.int64)
    if len(tp) < 30:
        return None
    ty = np.array([posY[dP[t]] for t in tp], np.int64)
    eP = S["eq"][tp]; eY = Y["eq"][ty]; b = W["Bc"][tp]
    rP = eP[1:] / eP[:-1] - 1.0; rY = eY[1:] / eY[:-1] - 1.0
    cal = W["cal"]; mon = np.asarray(cal.year * 12 + cal.month)[tp]
    me = [0] + [k for k in range(1, len(tp)) if k == len(tp) - 1 or mon[k + 1] != mon[k]]
    mP = eP[me][1:] / eP[me][:-1] - 1.0; mY = eY[me][1:] / eY[me][:-1] - 1.0
    o = {"窗": f"{dP[tp[0]]}～{dP[tp[-1]]}", "共同交易日": int(len(tp)), "月數": int(len(mP)),
         "月報酬相關": float(np.corrcoef(mP, mY)[0, 1]), "日報酬相關": float(np.corrcoef(rP, rY)[0, 1])}
    # 持股重疊
    ix = W["ix"]; MV = S["MV"]
    ys = list(Y["H"].keys()); jmap = np.array([ix.get(s, -1) for s in ys])
    YH = np.stack([Y["H"][s][0][ty] for s in ys], 1) if ys else np.zeros((len(tp), 0), bool)
    YW = np.stack([Y["H"][s][1][ty] for s in ys], 1) if ys else np.zeros((len(tp), 0))
    A = MV[:, tp] > 0                                                  # S × T
    WP = MV[:, tp] / S["eq"][tp][None, :]
    inY = jmap >= 0
    Asub = np.zeros_like(YH); Wsub = np.zeros_like(YW)
    Asub[:, inY] = A[jmap[inY], :].T; Wsub[:, inY] = WP[jmap[inY], :].T
    inter = (YH & Asub).sum(1); nA = A.sum(0); nB = YH.sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        fa = np.where(nA > 0, inter / nA, np.nan); fb = np.where(nB > 0, inter / nB, np.nan)
    o.update({"本件持股中營量也持有(相異檔,逐日平均)": float(np.nanmean(fa)), "營量持股中本件也持有(逐日平均)": float(np.nanmean(fb)),
              "金額重疊Σmin權重(逐日平均)": float(np.mean(np.minimum(Wsub, YW).sum(1))), "本件相異檔數(平均)": float(nA.mean()),
              "營量持股數(平均)": float(nB.mean()), "營量持股不在本件世界": int((~inY).sum())})
    # 各半、單獨（同窗）
    bb = RR.bench_row(None, b, 0, len(b))

    def mt(e):
        c_, m_, _ = RR.win_metrics(e, 0, len(e), 0, len(e) - 1)
        return {"年化": float(c_), "回落": float(m_), "比值": AS.ratio(c_, m_), "標籤": AS.label(c_, m_, bb)}
    e1 = np.r_[1.0, np.cumprod(1.0 + 0.5 * rP + 0.5 * rY)]
    e2 = 0.5 * eP / eP[0] + 0.5 * eY / eY[0]
    o.update({"0050": {"年化": bb["cagr"], "回落": bb["mdd"], "比值": AS.ratio(bb["cagr"], bb["mdd"])}, "本件(同窗)": mt(eP / eP[0]),
              "營量v1(同窗)": mt(eY / eY[0]), "各半①每日再平衡": mt(e1), "各半②段首各半不再平衡": mt(e2)})
    return o


# ═════════════ fixture ═════════════
def selftest(log):
    msgs = []
    # F1 份迴圈手算
    CM = np.array([[10.0, 11.0, 12.0, 12.5, 13.0, 13.0], [20.0, 19.0, 18.0, 18.0, 18.0, 18.0]])
    Bc = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0]); Bo = np.array([99.0, 100.5, 101.5, 102.5, 103.5, 104.5])
    W = {"n0": 6, "CM": CM, "Bc": Bc, "Bo": Bo, "mon": np.zeros(6, np.int64)}
    P = np.array([10.5, 19.5]); R = np.array([12.5 / 10.5 - 1, 18.0 / 19.5 - 1])
    ev = {"j": np.array([0, 1]), "e": np.array([1, 1]), "sale": np.array([3, 4]), "P": P, "px": P * (1 + R), "R": R}
    r = tranche_sim(ev, 1, W, False)
    u0 = 1 / 100.0; cap = u0 * Bo[1] * (1 - BC_SELL); a = cap / 2
    e1 = a * 11 / 10.5 + a * 19 / 19.5; e2 = a * 12 / 10.5 + a * 18 / 19.5
    p0 = a * (1 + R[0] - COST); e3 = p0 + a * 18 / 19.5
    u4 = p0 * (1 - BC_BUY) / Bo[4]; p1 = a * (1 + R[1] - COST); e4 = u4 * Bc[4] + p1
    u5 = u4 + p1 * (1 - BC_BUY) / Bo[5]; e5 = u5 * Bc[5]
    assert np.allclose(r["eq"], [1.0, e1, e2, e3, e4, e5], rtol=0, atol=1e-15), (r["eq"], [1.0, e1, e2, e3, e4, e5])
    assert r["nh"].tolist() == [0, 2, 2, 1, 0, 0]
    msgs.append("F1 份迴圈手算（e 開盤賣 0050 0.2425% 撥款、等權、收盤計值、強制賣當天留現金、隔天開盤買回 0050 0.1425%）逐位元相同")
    # F1b 兩份：第二份未滿批期間全抱 0050、份與份不互撥
    W2 = dict(W); W2["mon"] = np.array([0, 0, 1, 1, 1, 1], np.int64)
    ev2 = {"j": np.array([0]), "e": np.array([2]), "sale": np.array([5]), "P": np.array([12.0]), "px": np.array([13.0]), "R": np.array([13 / 12 - 1])}
    r2 = tranche_sim(ev2, 2, W2, False)
    half = 0.5 / Bc[0]
    a2 = half * Bo[2] * (1 - BC_SELL)
    exp = [half * Bc[t] * 2 if t < 2 else half * Bc[t] + a2 * CM[0, t] / 12.0 for t in range(5)] + [half * Bc[5] + a2 * (1 + 13 / 12 - 1 - COST)]
    assert np.allclose(r2["eq"], exp, rtol=0, atol=1e-15), (r2["eq"], exp)
    msgs.append("F1b 兩份：未進場的份全抱 0050、只賣該份 0050 撥款（份與份不互撥）")
    # F2 不洗牌生成器 ⇒ simulate 依傳入順序補空位
    n0 = 8; S_ = 14
    CMf = 10 + np.cumsum(np.random.default_rng(5).normal(0, 0.1, (S_, n0)), axis=1)
    order = np.random.default_rng(6).permutation(S_)
    tr = {"j": order, "ent": np.full(S_, 1), "ext": np.full(S_, 6), "ep": CMf[order, 1], "g": CMf[order, 6] / CMf[order, 1] - 1}
    Bf = np.linspace(100, 101, n0)
    s1 = TS.simulate(tr, n0, CMf, Bf, Bf, "main", seed=keep_order())
    assert [q for _, q, _ in s1["buys"]] == list(range(10))
    assert np.random.default_rng(keep_order()) is not None and isinstance(np.random.default_rng(keep_order()), KeepOrder)
    msgs.append("F2 不洗牌生成器：researchTurtleS2PF.simulate 依傳入順序補 10 個空位（前 10 筆）")
    # F3 矩陣化等效獨立檔數 ＝ researchDumb.eff_n
    rng = np.random.default_rng(9)
    n0 = 200; S_ = 30
    C = 20 * np.exp(np.cumsum(rng.normal(0, 0.02, (S_, n0)) + rng.normal(0, 0.01, (1, n0)), axis=1))
    C[rng.random((S_, n0)) < 0.05] = np.nan
    C[3, 100:200] = C[3, 99]
    sids = [f"{1000 + i}" for i in range(S_)]
    Wd = {"C": C, "ix": {s: i for i, s in enumerate(sids)}, "NP": n0 + 1}
    TRd = []
    for _ in range(80):
        i = int(rng.integers(0, S_)); tb = int(rng.integers(30, 180)); ts = tb + int(rng.integers(1, 40))
        TRd.append({"r": {"sid": sids[i]}, "tb": tb, "ts": ts if ts < n0 else None})
    days = sorted({z["tb"] for z in TRd})
    ref = RD.eff_n(Wd, TRd, days)
    iv = np.array([(Wd["ix"][z["r"]["sid"]], z["tb"], z["ts"] if z["ts"] is not None else n0 + 1) for z in TRd])
    worst = 0.0
    for (t, N, rho, en) in ref:
        m = (iv[:, 1] <= t) & (t < iv[:, 2])
        z = effn_vec(C, iv[m, 0], t)
        assert z[1] == N
        if np.isfinite(en) or np.isfinite(z[3]):
            worst = max(worst, abs(z[3] / en - 1))
    assert worst < 1e-9, worst
    msgs.append(f"F3 矩陣化等效獨立檔數 ＝ researchDumb.eff_n（合成 {len(ref)} 天、含缺值與停滯價；最大相對差 {worst:.1e}）")
    # F4 滑價式
    P_, px_ = 10.0, 12.0
    assert abs(px_ * (1 - SLIP) / (P_ * (1 + SLIP)) - 1 - (11.94 / 10.05 - 1)) < 1e-15
    msgs.append("F4 滑價 R ＝ 賣價×0.995 ÷ (買價×1.005) − 1")
    # F5 上限
    assert capped({"主判探索": "合格", "主判確認": "合格", "滑價探索": "不合格", "滑價確認": "合格", "主判早年": "合格"})[0] == "另列"
    assert capped({"主判探索": "合格", "主判確認": "合格", "滑價探索": "合格", "滑價確認": "另列", "主判早年": "不合格"})[0] == "暫定"
    assert capped({"主判探索": "合格", "主判確認": "合格", "滑價探索": "合格", "滑價確認": "合格", "主判早年": "—"}, early_none=True)[0] == "暫定"
    assert capped({"主判探索": "另列", "主判確認": "合格", "滑價探索": "不合格", "滑價確認": "不合格", "主判早年": "合格"})[0] == "另列"
    assert capped({"主判探索": "不合格", "主判確認": "合格", "滑價探索": "合格", "滑價確認": "合格", "主判早年": "合格"})[0] == "不合格"
    msgs.append("F5 seq398 上限（滑價不合格最多另列、早年不合格／無早年最多暫定）")
    for m_ in msgs:
        log("✅ " + m_)
    return msgs


# ═════════════ 隨機（Q5 ④）═════════════
def rand_job(a):
    wn, i = a
    G = _G[wn]
    S = TS.simulate(G["tr"], G["n0"], G["CM"], G["Bc"], G["Bo"], "main", seed=[RSEED, WID[wn], i], record=True)
    row = {"世界": wn, "i": i, "買進筆": len(S["buys"])}
    for sg, (x, y) in G["segp"].items():
        c_, m_, _ = RR.win_metrics(S["eq"], 0, G["n0"], x, y)
        row[f"{sg}_年化"] = float(c_); row[f"{sg}_回落"] = float(m_); row[f"{sg}_平均持股"] = float(np.mean(S["nh"][x:y + 1]))
    return row


# ═════════════ 主程式 ═════════════
def run(a, log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    if abs(COST - 0.00585) > 1e-15:
        raise SystemExit(f"⛔ COST {COST} ≠ 0.585%")
    regf = reg_check(REG_SHA)
    log(f"[登錄] sha {REG_SHA} ✓ {regf}｜讀法寫死 {TIME}｜開跑 {now_tpe()}")
    J = {"讀法寫死": TIME, "登錄": f"PREREG接近52週新高組合層 seq1 sha {REG_SHA}（裁定 seq396 准起草、seq398 發號 N_組合 ＋1、過目照跑）", "登錄檔": regf,
         "臂": {k: v["名"] for k, v in ARMS.items()}, "成本": {"個股來回": COST, "0050買": BC_BUY, "0050賣": BC_SELL, "滑價每邊": SLIP},
         "閘": {}, "時點": {"開跑": now_tpe()}}
    J["fixture"] = selftest(log)
    pj = json.load(open(PTHJ, encoding="utf-8"))
    WS = {}; EVS = {}; SIMS = {}
    for wn in ("主", "早年"):
        W = build_world(wn, log); WS[wn] = W
        t0 = time.time(); RES = {}
        with Pool(a.procs) as pool:
            for k_, (sid, r) in enumerate(pool.imap_unordered(PTH.stock_job, [(wn, s) for s in W["sids"]], chunksize=8)):
                if r is not None:
                    RES[sid] = r
                if (k_ + 1) % 500 == 0:
                    log(f"  [{wn}] 逐股 {k_ + 1}／{len(W['sids'])}｜{time.time() - t0:.0f}s")
        log(f"[{wn}] 逐股完 {len(RES)} 檔｜{time.time() - t0:.0f}s")
        EVS[wn] = {}
        J["閘"][wn] = {"0050開盤缺值日(用前一日收盤)": W["nbo"]}
        for cell in CELLS:
            ev, info = load_events(W, wn, cell, RES)
            EVS[wn][cell] = ev
            J["閘"][wn][f"事件 {cell}"] = info
            log(f"[查核 {wn}/{cell}] 事件檔 {info['列']:,} 列 ＝ researchPTH.stock_job 重算（R、出場種類、出場日、進場日）｜賣價 vs 收盤 最大相對差 "
                f"{info['最大相對差(賣價vs收盤)']:.1e}｜批次 {info['批次數']}")
        del RES
        if a.dry:
            continue
        # ── 組合（⛔ 先不讀報酬）
        SIMS[wn] = {}
        for arm, cfg in ARMS.items():
            ev = EVS[wn][cfg["cell"]]
            if cfg["kind"] == "tr":
                SIMS[wn][arm] = tranche_sim(ev, CELLS[cfg["cell"]][1], W, cfg["slip"], want_mv=(arm == "M"))
            else:
                o_ = np.lexsort((ev["rk"], -ev["pth"], ev["e"]))
                SIMS[wn][arm] = slot_sim(slot_tr(ev, cfg["slip"], o_), W, keep_order())
            log(f"[組合 {wn}] {arm} 買進 {len(SIMS[wn][arm]['buys']):,} 筆（⛔ 尚未讀報酬）｜{time.time() - T0:.0f}s")
    if a.dry:
        log(f"[乾跑] 完（未算任何組合報酬）｜{time.time() - T0:.0f}s")
        json.dump(J, open(os.path.join(OUT, "dry.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
        return
    # ── 退化（先寫）
    DEG = {"規則": "seq325：探索段平均持股 ＜ 3 ⇒ 退化、不判；空位抱 0050 ⇒「現金 ＞ 30%」不適用（seq360 §一）", "格": {}}
    for wn, W in WS.items():
        for arm in ARMS:
            nh = SIMS[wn][arm]["nh"]
            for sg, (x, y) in W["segp"].items():
                DEG["格"][f"{wn}|{arm}|{sg}"] = {"平均持股(筆)": float(np.mean(nh[x:y + 1])), "退化": bool(np.mean(nh[x:y + 1]) < DEG_HOLD)}
    DEG["主判探索段退化"] = DEG["格"]["主|M|探索"]["退化"]
    DEG["寫入時間（台北）"] = now_tpe()
    json.dump(DEG, open(os.path.join(OUT, "degeneracy.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[退化] 已寫 degeneracy.json（{DEG['寫入時間（台北）']}）｜主判探索 {DEG['格']['主|M|探索']}")
    J["退化"] = DEG
    J["時點"]["第一次讀報酬"] = now_tpe()
    # ── 報酬、必報
    TAB = []; LAB = {}; BY = []
    for wn, W in WS.items():
        cal = W["cal"]
        for arm, cfg in ARMS.items():
            S = SIMS[wn][arm]
            ev = EVS[wn][cfg["cell"]]
            typ_q = ev["typ"] if cfg["kind"] == "tr" else ev["typ"][S["q"]] if "q" in S else None
            iv = intervals(S, W["n0"])
            UC = uniq_count(iv, W["n0"], len(W["sids"])) if arm in ("M", "S10") else None
            for sg, (x, y) in W["segp"].items():
                c_, m_, b = metrics(W, S["eq"], x, y)
                lab = AS.label(c_, m_, b); LAB[(wn, arm, sg)] = lab
                row = {"世界": wn, "臂": arm, "臂名": cfg["名"],
                       "身分": ("判定" if cfg["judge"] and wn == "主" else ("早年（最多暫定用）" if (cfg["judge"] and arm == "M") else "描述（⛔ 不判）")),
                       "段": sg, "窗": f"{cal[x].date()}～{cal[y].date()}", "年化": c_, "回落": m_, "比值": AS.ratio(c_, m_),
                       "0050年化": b["cagr"], "0050回落": b["mdd"], "0050比值": AS.ratio(b["cagr"], b["mdd"]), "標籤": lab,
                       **pf_stats(W, S, x, y, typ_q)}
                if UC is not None:
                    row["平均持股(相異檔)"] = float(np.mean((UC[x:y + 1] > 0).sum(1)))
                    row.update(effn_seg(W, iv, x, y))
                    w12 = worst12(S["eq"], W["Bc"], cal, x, y)
                    if w12:
                        row.update({"最差12個月": w12["最差12個月"], "最差12個月窗": w12["窗"], "最差12個月_0050同窗": w12["0050同窗"]})
                if arm in ("M", "Mslip", "S10"):
                    for Y_, v_ in yearly(S["eq"], W["Bc"], cal, x, y).items():
                        BY.append({"世界": wn, "臂": arm, "段": sg, "年": Y_, **v_})
                TAB.append(row)
            log(f"  [{wn}] {arm} 統計完｜{time.time() - T0:.0f}s")
    TB = pd.DataFrame(TAB)
    TB.to_csv(os.path.join(OUT, "PTHpf_main.csv"), index=False, float_format="%.6g", encoding="utf-8-sig")
    pd.DataFrame(BY).to_csv(os.path.join(OUT, "by_year.csv"), index=False, float_format="%.6g", encoding="utf-8-sig")
    J["主表"] = TAB
    log("[主表]\n" + TB[["世界", "臂", "段", "年化", "回落", "比值", "0050年化", "0050回落", "0050比值", "標籤", "平均持股(筆)", "換手每年",
                       "成本合計每年(實付)", "0050占淨值"]].to_string())
    L = {"主判探索": LAB[("主", "M", "探索")], "主判確認": LAB[("主", "M", "確認")], "滑價探索": LAB[("主", "Mslip", "探索")],
         "滑價確認": LAB[("主", "Mslip", "確認")], "主判早年": LAB[("早年", "M", "早年")], "滑價早年(描述)": LAB[("早年", "Mslip", "早年")]}
    v0 = TS.verdict(L)
    v1, why = capped(L)
    if DEG["主判探索段退化"]:
        v1 = f"退化、照 seq325 不判（標籤照報：{v1}）"
    J["判語"] = {**L, "researchTurtleS2PF.verdict 原樣": v0, "整件（套 seq398 上限）": v1, "上限理由": why}
    J["描述標籤"] = {f"{w}|{arm}|{sg}": LAB[(w, arm, sg)] for (w, arm, sg) in LAB if not ARMS[arm]["judge"]}
    log(f"[判語] {json.dumps(J['判語'], ensure_ascii=False)}")
    # ── 存檔（權益、逐筆）
    for wn, W in WS.items():
        dates = W["dates"]
        np.savez_compressed(os.path.join(OUT, f"eq_{wn}.npz"), Bc=W["Bc"], Bo=W["Bo"],
                            **{f"{arm}_{k}": SIMS[wn][arm][k] for arm in ARMS for k in ("eq", "hv", "u", "pend", "nh")})
        for arm, cfg in ARMS.items():
            S = SIMS[wn][arm]; ev = EVS[wn][cfg["cell"]]
            qmap = S["q"] if "q" in S else np.arange(len(ev["e"]))
            sl = {q: (t, proc) for t, q, amt, proc in S["sells"]}
            df = pd.DataFrame({"sid": [ev["sid"][qmap[q]] for _, q, _ in S["buys"]], "形成月底": [ev["form"][qmap[q]] for _, q, _ in S["buys"]],
                               "PTH": [ev["pth"][qmap[q]] for _, q, _ in S["buys"]], "買進日": [dates[t] for t, _, _ in S["buys"]],
                               "份": [int(S["tranche"][q]) if "tranche" in S else -1 for _, q, _ in S["buys"]],
                               "金額": [amt for _, _, amt in S["buys"]], "市值基準價": [S["ep"][q] for _, q, _ in S["buys"]],
                               "R用": [S["g"][q] for _, q, _ in S["buys"]], "出場種類": [TYPN[int(ev["typ"][qmap[q]])] for _, q, _ in S["buys"]],
                               "排程賣出日": [dates[S["ext"][q]] if S["ext"][q] >= 0 else "" for _, q, _ in S["buys"]],
                               "賣出日": [dates[sl[q][0]] if q in sl else "" for _, q, _ in S["buys"]],
                               "入帳": [sl[q][1] if q in sl else np.nan for _, q, _ in S["buys"]]})
            with gzip.open(os.path.join(OUT, f"trades_{wn}_{arm}.csv.gz"), "wt", encoding="utf-8") as fh:
                df.to_csv(fh, index=False, float_format="%.17g")
    # ── 隨機（Q5 ④）
    J["隨機10檔"] = {}
    for wn, W in WS.items():
        ev = EVS[wn]["跳月"]
        o_ = np.lexsort((W["srank"][ev["j"]], ev["e"]))
        tr = slot_tr(ev, False, o_)
        bench = {sg: RR.bench_row(W["cal"], W["bench"], x, y + 1) for sg, (x, y) in W["segp"].items()}
        _G[wn] = {"tr": tr, "n0": W["n0"], "CM": W["CM"], "Bc": W["Bc"], "Bo": W["Bo"], "segp": W["segp"]}
        with Pool(a.procs) as pool:
            RES_ = pool.map(rand_job, [(wn, i) for i in range(NRAND)], chunksize=4)
        RDF = pd.DataFrame(RES_)
        RDF.to_csv(os.path.join(OUT, f"random_{wn}.csv.gz"), index=False, float_format="%.10g")
        o = {}
        for sg in W["segp"]:
            z = TB[(TB["世界"] == wn) & (TB["臂"] == "S10") & (TB["段"] == sg)].iloc[0]
            rr = RDF[f"{sg}_年化"] / RDF[f"{sg}_回落"].abs()
            lab_r = [AS.label(c_, m_, bench[sg]) for c_, m_ in zip(RDF[f"{sg}_年化"], RDF[f"{sg}_回落"])]
            o[sg] = {"10檔版 年化": float(z["年化"]), "10檔版 比值": float(z["比值"]), "隨機 年化中位": float(RDF[f"{sg}_年化"].median()),
                     "隨機 年化 p10／p90": [float(RDF[f"{sg}_年化"].quantile(.1)), float(RDF[f"{sg}_年化"].quantile(.9))],
                     "隨機 回落中位": float(RDF[f"{sg}_回落"].median()), "隨機 比值中位": float(rr.median()),
                     "p（隨機比值 ≥ 10檔版）": float((rr >= z["比值"]).mean()), "p（隨機年化 ≥ 10檔版）": float((RDF[f"{sg}_年化"] >= z["年化"]).mean()),
                     "隨機 標籤比例": dict(Counter(lab_r)), "次數": int(len(RDF))}
        J["隨機10檔"][wn] = o
        log(f"[隨機10檔 {wn}] {json.dumps(o, ensure_ascii=False)}")
    # ── 營量 v1（Q5 ②）
    J["營量v1"] = {}; YLROW = []
    for wn, W in WS.items():
        Y = yl_load(wn, log, a.procs)
        J["營量v1"][wn] = {"eq_sha": Y["sha"], "窗": Y["窗"]}
        for sg, (x, y) in W["segp"].items():
            o = yl_compare(W, SIMS[wn]["M"], Y, x, y)
            J["營量v1"][wn][sg] = o
            if o:
                YLROW.append({"世界": wn, "段": sg, **{k: v for k, v in o.items() if not isinstance(v, dict)},
                              **{f"{k}_{kk}": vv for k, v in o.items() if isinstance(v, dict) for kk, vv in v.items()}})
            log(f"[營量 {wn}/{sg}] {json.dumps(o, ensure_ascii=False, default=float)}")
        del Y
    pd.DataFrame(YLROW).to_csv(os.path.join(OUT, "yl.csv"), index=False, float_format="%.6g", encoding="utf-8-sig")
    # ── 先驗
    def row(wn, arm, sg):
        return TB[(TB["世界"] == wn) & (TB["臂"] == arm) & (TB["段"] == sg)].iloc[0]
    zE = row("主", "M", "探索")
    J["先驗對照"] = {
        "① 確認段合格（約四成）": {"確認段標籤": L["主判確認"], "成立": L["主判確認"] == "合格"},
        "② 探索段年化 ＞ 0050（約六成），比值未必（約四成五）": {"年化": float(zE["年化"]), "0050年化": float(zE["0050年化"]),
                                                "年化＞0050": bool(zE["年化"] > zE["0050年化"]), "比值≥0050": bool(zE["比值"] >= zE["0050比值"])},
        "③ 與營量 v1 月報酬相關 ≥ 0.7（約六成）": {sg: (J["營量v1"]["主"][sg] or {}).get("月報酬相關") for sg in ("探索", "確認")},
        "④ 10 檔版回落比主版深（約八成）": {f"{wn}/{sg}": {"10檔版": float(row(wn, "S10", sg)["回落"]), "主版": float(row(wn, "M", sg)["回落"]),
                                               "成立": bool(row(wn, "S10", sg)["回落"] < row(wn, "M", sg)["回落"])}
                                   for wn, W in WS.items() for sg in W["segp"]}}
    J["先驗對照"]["③ 與營量 v1 月報酬相關 ≥ 0.7（約六成）"]["成立(兩段皆≥0.7)"] = bool(all(
        (v or 0) >= 0.7 for k, v in J["先驗對照"]["③ 與營量 v1 月報酬相關 ≥ 0.7（約六成）"].items()))
    log(f"[先驗] {json.dumps(J['先驗對照'], ensure_ascii=False, default=float)}")
    # ── 結果句
    ovl = pj["引自頻率表"]["重疊_營量營飆在PTH前30%比例"]
    s_ov = "營量入選股多半本來就在 PTH 前 30%（頻率表：營量 v1 入選股月中在 PTH 前 30% 的比例 探索 {:.0f}%、確認 {:.0f}%、早年 {:.0f}%）".format(
        ovl["主/探索"]["營量v1"] * 100, ovl["主/確認"]["營量v1"] * 100, ovl["早年/早年"]["營量v1"] * 100)
    tail = [SENT_REG[0], s_ov, SENT_REG[2], SENT_REG[3], SENT_396]
    sents = {}
    for wn, W in WS.items():
        for sg in W["segp"]:
            z = row(wn, "M", sg); zs = row(wn, "Mslip", sg)
            s = (f"接近 52 週新高組合層（PTH 前 30% 等權、跳 1 月、6 份重疊、空位抱 0050）{sg}段：年化 {pct(z['年化'])}、最大回落 {pct(z['回落'])}、比值 {z['比值']:.2f}"
                 f"（0050 {pct(z['0050年化'])}、{pct(z['0050回落'])}、{z['0050比值']:.2f}）⇒ {z['標籤']}；滑價每邊 +0.5% 版：年化 {pct(zs['年化'])}、回落 {pct(zs['回落'])} ⇒ {zs['標籤']}"
                 + ("（早年只定上限：早年不合格 ⇒ 最多暫定）" if wn == "早年" else "") + "｜" + "；".join(tail + (NOTE_EARLY if wn == "早年" else [])))
            sents[f"{wn}|{sg}"] = s
    sents["整件"] = (f"接近 52 週新高組合層整件：{v1}" + (f"（{'；'.join(why)}）" if why else "") + "｜" + "；".join(tail))
    J["結果句"] = sents
    for k, s in sents.items():
        log(f"[結果句 {k}] {s}")
    J["N"] = {"本件": "N_組合 ＋1（判定 1 件；滑價版為可執行性條款；10 檔版、不跳月、3／12 個月、隨機、營量相關／重疊／各半 皆描述不計）"}
    J["耗時秒"] = round(time.time() - T0); J["時點"]["完成"] = now_tpe()
    J["讀法"] = __doc__.split("═══ 讀法")[1]
    json.dump(J, open(os.path.join(OUT, "PTHpf.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] {J['耗時秒']}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=2)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    log = RA.log_to(os.path.join(OUT, "dry.log" if a.dry else "run.log"))
    run(a, log)


if __name__ == "__main__":
    main()
