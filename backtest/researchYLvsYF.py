# -*- coding: utf-8 -*-
"""營量 v1 對 營飆 v1：規則差異、實際持股重疊、大盤閘影響、績效（使用者問：「量與飆到底差多少？選出來的是否幾乎都一樣？」）——回測線計算子代理。
⭐ 描述、⛔ 不計 N、⛔ 不改營量 v1／營飆 v1 任何規則。⛔ 不改任何既有 .py／結果夾；⛔ 不 commit。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLvsYF [--procs 3]
    獨立查核：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLvsYF_check [--procs 3]

═══ 讀法（寫於 2026-10-18（台北），在算任何本件數字之前；⚠ 本線看過：營量 v1、營飆 v1 各段年化／回落（resultsYL_integrate、resultsYF_N）、
    resultsYL_blend 主窗相似度（金額重疊日均約 14%、營飆實買被營量同日買約 51%、日報酬相關約 0.77）與 50:50 合併主窗數字）═══
 V1 兩策略 ＝ researchYL_integrate.eng 原式（不改任何參數）：
    營量 v1 ＝ 格 "H60·S20·無·relvol"：simulate_mtm(SIG[無閘], "H60", 20, default_rng(7000＋0), ..., log=[], d_max=None, pick="relvol", queue_days=0, stop_force=SF)；relvol 決定、r＝0 一條
    營飆 v1 ＝ 格 "H120·S10·閘·抽籤"：simulate_mtm(SIG[閘], "H120", 10, default_rng(1000＋r), ..., stop_force=SF)；r ＝ 0～199
    世界 ＝ researchYL_integrate.main_world（主窗；探索／確認切段）與 early_world（早年 2005-02-01～2014-12-31，上市＋上櫃 eotc_f65bb03e11、R8 截斷）
 V2 段（＝ 營飆 v1 原報告／整合件 I3）：探索 2017-03-02～2021-12-30、確認 2022-01-03～2026-08-24、早年 2005-02-01～2014-12-31；另附主窗（只供對帳）
 V3 持股（＝ researchYL_blend.holdings_w 口徑）：當日收盤仍在簿上 ＝ 持有 [買進日, 賣出日)；未賣 ⇒ 到權益尾
    逐日 ⓐ「營飆持股中也在營量持股的比例」＝ |F∩Y| ÷ |F|（|F|＞0 的日子）；ⓑ「營量持股中也在營飆持股的比例」＝ |F∩Y| ÷ |Y|（|Y|＞0 的日子）；段內逐日平均
    另報 金額重疊 ＝ Σ_檔 min(營量權重, 營飆權重)（權重 ＝ 市值 ÷ 該策略權益；＝ blend 件 ⓑ）、營飆空手日比例
    起點效應：主窗與早年窗首起第 1～20、21～60、61～120、121～250 個交易日的 ⓐ、ⓑ 平均（兩策略都從空簿開始）
 V4 買進交易層：營飆段內每筆買進 (檔, 買進日 t)，營量在 [t−5, t＋5] 個交易日內也買過同一檔 ⇒ 算「營量也買過」；報比例（200 顆中位、p10／p90）
    另報 ±0（同日）、「營飆買進當天收盤營量正持有該檔」；反向：營量買進中營飆 ±5 也買過的比例
 V5 大盤閘：閘關 ＝ 進場日 e 的前一日 0050 還原收盤 ≤ 200 日均（W["reg"][e−1] 為 False；＝ 營飆 v1 閘）
    段內 ① 閘關的交易日占比；② 有窗內訊號的日子中閘關的占比；③ 被閘擋掉的訊號筆數 ÷ 段內訊號筆數
    營量 v1 在閘關日的買進：筆數、占營量買進比例、淨報酬（賣價 ÷ 買價 − 1 − 0.585%；未賣用權益尾收盤）平均／中位、勝率、對組合貢獻和（金額 × 淨報酬 ÷ 買進前一日權益）；對照閘開日
    閘關日的日報酬累乘（營量、營飆 200 顆中位、0050）；段內連續閘關 ≥ 10 個交易日的區間逐一列（營量買進數、那些買進的淨報酬平均、區間報酬）
 V6 績效：各段 年化、最大回落 ＝ rerun17.win_metrics；比值 ＝ 年化 ÷ |回落|（營飆用 200 顆中位）；對 0050 ＝ researchYL_integrate.label
    逐日報酬相關（段內 t ＝ x＋1～y，營飆每顆對營量一條）；組合「一半營量＋一半營飆」只描述：
      ① 每日再平衡（researchYL_integrate.blend_eq w＝0.5，＝ blend 件 ①）；② 段首各半、不再平衡（eq ＝ ½ 營飆/營飆[x] ＋ ½ 營量/營量[x]）
 V7 現在的照規則簿 backtest/forward/yl_rule/positions.csv（工作樹當下內容，唯讀）：兩策略持有中名單交集；註明起點效應（9/29 起點兩邊空槽、都買光訊號）
 V8 閘（不過即停）：
    G1 營量 主 ＝ resultsT1fix c13 t1 r0（eq_sha、年化、回落 repr）；G2 營量 兩世界 ＝ resultsYL_integrate/seeds 同格 r0（eq_sha、各段年化／回落 repr）
    G3 營飆 主 ＝ resultsT1fix c1 t1 r0～199；G4 營飆 兩世界 ＝ resultsYL_integrate/seeds 同格同 r；G5 營飆各段中位 ＝ resultsYF_N/summary.json N10 列（repr）
    G6 0050 各段 ＝ 整合件 summary.json；G7 主窗金額重疊、同日實買比例、日報酬相關 ＝ resultsYL_blend/similarity_seeds.csv 同 r（差 ≤ 1e−9）
 必附：「描述、不計 N」；早年附「早年含減資假飆股約 0.3%（reduce_v2；剩 22 筆未解釋）」與 NOTE3
輸出 backtest/resultsYLvsYF/：seeds.csv.gz、cells.csv、gate_spells.csv、summary.json、REPORT.md、run.log
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import research11 as R                        # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402
from backtest import researchYL_integrate as IG             # noqa: E402

TIME = "2026-10-18（台北）"
OUT = "backtest/resultsYLvsYF"
NSEED = 200
if os.environ.get("YLYF_QUICK"):                             # 煙霧測試（不是交件）
    NSEED, OUT = 2, "/tmp/ylyf_quick"
COST = R.COST
WIN = 5
SEGS = {"主": ("探索", "確認", "主窗"), "早年": ("早年",)}
REPSEG = (("主", "探索"), ("主", "確認"), ("早年", "早年"))
WORD = "描述、不計 N"
NOTE_EARLY = ["早年含減資假飆股約 0.3%（reduce_v2；剩 22 筆未解釋）；早年照營飆 v1 早年既有版面（上市＋上櫃 eotc_f65bb03e11、R8 截斷）", IG.NOTE3]
STARTB = ((0, 20), (20, 60), (60, 120), (120, 250))
_W: dict = {}


def sha(eq):
    return hashlib.sha256(np.asarray(eq, float).tobytes()).hexdigest()[:16]


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


def log_to(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    f = open(path, "a", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); f.write(m + "\n"); f.flush()
    return log


def trades_of(au, n):
    """audit ⇒ [(sid, tb, ts, amt, px_in, px_out, eq_prev)]；未賣 ⇒ ts ＝ n、px_out ＝ NaN（同 researchYF_N.trades_of，尾端用權益長 n）。"""
    op, T = {}, []
    for a in au:
        if a["side"] == "buy":
            if a["sid"] in op:
                raise SystemExit(f"⛔ {a['sid']} 重複買進")
            op[a["sid"]] = (a["t"], a["amt"], a["px"], a["equity_prev"])
        else:
            tb, amt, px, ep_ = op.pop(a["sid"])
            T.append((a["sid"], tb, a["t"], amt, px, a["px"], ep_))
    for s, (tb, amt, px, ep_) in op.items():
        T.append((s, tb, n, amt, px, np.nan, ep_))
    return T


def net_ret(W, o, tr):
    s, tb, ts, amt, pin, pout, ep_ = tr
    if not np.isfinite(pout):
        pout = float(W["closes"][s][min(o["end"], W["NP"]) - 1])
    return pout / pin - 1.0 - COST


def book(W, o, au):
    """⇒ eq, TR, cnt[d]（持股檔數）, {sid: (bool[n], w[n])}（持有、權重）。"""
    eq = np.asarray(o["equity"], float); n = len(eq)
    TR = trades_of(au, n)
    cnt = np.zeros(n); H = {}
    for s, tb, ts, amt, pin, *_ in TR:
        ts = min(ts, n)
        cnt[tb:ts] += 1
        if s not in H:
            H[s] = (np.zeros(n, bool), np.zeros(n))
        H[s][0][tb:ts] = True
        H[s][1][tb:ts] += amt * np.asarray(W["closes"][s][tb:ts], float) / pin
    for s in H:
        H[s][1][:] /= eq
    return eq, TR, cnt, H


def overlap_series(F, Y):
    """F、Y ＝ book() 結果 ⇒ inter[d]、ovA[d]。"""
    n = len(F[0]); inter = np.zeros(n); ovA = np.zeros(n)
    for s, (hb, hw) in F[3].items():
        if s in Y[3]:
            yb, yw = Y[3][s]
            inter += (hb & yb); ovA += np.minimum(hw, yw)
    return inter, ovA


def buys_by_sid(TR):
    d = {}
    for s, tb, *_ in TR:
        d.setdefault(s, []).append(tb)
    return {s: np.array(sorted(v)) for s, v in d.items()}


def match_frac(TRa, Bb, x, y, win):
    """TRa 段內買進中，另一邊 Bb（{sid: 買進日}）在 ±win 交易日內也買過的比例。"""
    k = m = 0
    for s, tb, *_ in TRa:
        if not (x <= tb <= y):
            continue
        k += 1
        v = Bb.get(s)
        if v is not None and np.any(np.abs(v - tb) <= win):
            m += 1
    return (m / k if k else np.nan), k


def seg_overlap(F, Y, inter, ovA, x, y):
    nF = F[2][x:y + 1]; nY = Y[2][x:y + 1]; it = inter[x:y + 1]
    a = float(np.mean(it[nF > 0] / nF[nF > 0])) if (nF > 0).any() else np.nan
    b = float(np.mean(it[nY > 0] / nY[nY > 0])) if (nY > 0).any() else np.nan
    return a, b, float(np.mean(ovA[x:y + 1])), float(np.mean(nF == 0)), float(np.mean(nY == 0))


def daily_r(eq, x, y):
    return eq[x + 1:y + 1] / eq[x:y] - 1.0


# ═════════════ 營飆每顆種子 ═════════════
def job(args):
    wn, r = args
    W = _W[wn]; Y = W["YLB"]; oY = W["YLo"]
    o, au = IG.eng(W, IG.YF, r)
    F = book(W, o, au)
    eq = F[0]
    inter, ovA = overlap_series(F, Y)
    BY, BF = W["YLBUY"], buys_by_sid(F[1])
    row = {"世界": wn, "r": r, "eq_sha": sha(eq), "first": int(o["first"]), "end": int(o["end"]), "trades": int(o["trades"])}
    eB, fB, nB = IG.blend_eq(eq, o["first"], o["end"], Y[0], oY["first"], oY["end"], w=0.5)
    for sg in SEGS[wn]:
        x, y = W["segp"][sg]
        c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], x, y)
        row[f"{sg}_年化"] = float(c_); row[f"{sg}_回落"] = float(m_)
        a, b, am, f0, y0 = seg_overlap(F, Y, inter, ovA, x, y)
        row[f"{sg}_F中也在Y"] = a; row[f"{sg}_Y中也在F"] = b; row[f"{sg}_金額重疊"] = am; row[f"{sg}_營飆空手日"] = f0; row[f"{sg}_營量空手日"] = y0
        row[f"{sg}_營飆持股"] = float(np.mean(F[2][x:y + 1]))
        row[f"{sg}_F買Y±5"], row[f"{sg}_F買進數"] = match_frac(F[1], BY, x, y, WIN)
        row[f"{sg}_F買Y±0"], _ = match_frac(F[1], BY, x, y, 0)
        row[f"{sg}_Y買F±5"], row[f"{sg}_Y買進數"] = match_frac(Y[1], BF, x, y, WIN)
        hold_ = [Y[3][s][0][tb] for s, tb, *_ in F[1] if x <= tb <= y and s in Y[3]]
        kF = row[f"{sg}_F買進數"]
        row[f"{sg}_F買時Y持有"] = (float(np.sum(hold_)) / kF) if kF else np.nan
        row[f"{sg}_日報酬相關"] = float(np.corrcoef(daily_r(eq, x, y), daily_r(Y[0], x, y))[0, 1])
        c1, m1, _ = RR.win_metrics(eB, fB, nB, x, y)
        row[f"{sg}_半半①年化"] = float(c1); row[f"{sg}_半半①回落"] = float(m1)
        e2 = 0.5 * eq / eq[x] + 0.5 * Y[0] / Y[0][x]
        c2, m2, _ = RR.win_metrics(e2, x, y + 1, x, y)
        row[f"{sg}_半半②年化"] = float(c2); row[f"{sg}_半半②回落"] = float(m2)
        # 閘關日（營飆）報酬累乘
        cl = W["CLOSED"][x + 1:y + 1]
        row[f"{sg}_閘關日累乘"] = float(np.prod(1 + daily_r(eq, x, y)[cl]) - 1)
        row[f"{sg}_閘開日累乘"] = float(np.prod(1 + daily_r(eq, x, y)[~cl]) - 1)
    # 起點效應（窗首 w0 起）
    w0 = W["w0"]
    for a_, b_ in STARTB:
        x, y = w0 + a_, w0 + b_ - 1
        a, b, am, f0, y0 = seg_overlap(F, Y, inter, ovA, x, y)
        row[f"起點{a_ + 1}-{b_}_F中也在Y"] = a; row[f"起點{a_ + 1}-{b_}_Y中也在F"] = b
    # 閘關區間報酬
    for i, (x, y) in enumerate(W["SPELLS"]):
        row[f"spell{i}"] = float(eq[y] / eq[x - 1] - 1)
    # 抽樣日（查核用）：探索／確認／早年各 3 天的 |F|、|Y|、|F∩Y|
    for d in W["SAMPLE"]:
        row[f"d{d}"] = f"{int(F[2][d])}/{int(Y[2][d])}/{int(inter[d])}"
    return row


def prep_world(W, log):
    o, au = IG.eng(W, IG.YL, 0)
    Y = book(W, o, au)
    W["YLo"], W["YLau"], W["YLB"], W["YLBUY"] = o, au, Y, buys_by_sid(Y[1])
    reg = np.asarray(W["reg"], bool); n = len(Y[0])
    CL = np.zeros(n, bool)
    m = min(n - 1, len(reg))
    CL[1:m + 1] = ~reg[:m]                                   # 第 e 天閘關 ＝ reg[e−1] False
    W["CLOSED"] = CL
    # 自檢：窗內被閘擋的訊號數 ＝ 無閘表 − 有閘表
    e_ = W["base"]["entry_pos"].to_numpy(int)
    if int(CL[e_].sum()) != len(W["SIG"][False]) - len(W["SIG"][True]):
        raise SystemExit("⛔ 閘關日與有閘訊號表不一致")
    # 段內連續閘關 ≥ 10 交易日
    sp = []
    for sg in SEGS[W["name"]]:
        if sg == "主窗":
            continue
        x, y = W["segp"][sg]; d = x
        while d <= y:
            if CL[d]:
                e = d
                while e + 1 <= y and CL[e + 1]:
                    e += 1
                if e - d + 1 >= 10:
                    sp.append((d, e))
                d = e + 1
            else:
                d += 1
    W["SPELLS"] = sp
    rng = np.random.default_rng(20261018)
    smp = []
    for sg in SEGS[W["name"]]:
        if sg == "主窗":
            continue
        x, y = W["segp"][sg]
        smp += sorted(int(v) for v in rng.choice(np.arange(x, y + 1), 3, replace=False))
    W["SAMPLE"] = smp
    log(f"[{W['name']} 營量] eq_sha {sha(Y[0])}｜trades {o['trades']}｜閘關區間 {len(sp)}｜抽樣日 {[str(W['cal'][d].date()) for d in smp]}")


def gate_tables(W, YFq):
    """V5：閘關日統計、營量閘關買進表現、閘關區間表。YFq ＝ {spell i: 營飆 200 顆區間報酬中位}。"""
    Y = W["YLB"]; oY = W["YLo"]; CL = W["CLOSED"]; cal = W["cal"]; bench = W["bench"]
    base = W["base"]; e = base["entry_pos"].to_numpy(int)
    out, spells = {}, []
    for sg in SEGS[W["name"]]:
        x, y = W["segp"][sg]
        days = np.arange(x, y + 1)
        sigd = np.unique(e[(e >= x) & (e <= y)])
        ins = (e >= x) & (e <= y)
        rec = {"交易日": int(len(days)), "閘關日": int(CL[days].sum()), "閘關日占比": float(CL[days].mean()),
               "有訊號日": int(len(sigd)), "有訊號日中閘關": int(CL[sigd].sum()), "有訊號日中閘關占比": float(CL[sigd].mean()) if len(sigd) else np.nan,
               "段內訊號": int(ins.sum()), "被閘擋訊號": int((ins & CL[np.clip(e, 0, len(CL) - 1)]).sum())}
        rec["被閘擋訊號占比"] = rec["被閘擋訊號"] / rec["段內訊號"] if rec["段內訊號"] else np.nan
        for lab, want in (("閘關", True), ("閘開", False)):
            T = [tr for tr in Y[1] if x <= tr[1] <= y and bool(CL[tr[1]]) == want]
            nets = np.array([net_ret(W, oY, tr) for tr in T]); con = np.array([tr[3] * net_ret(W, oY, tr) / tr[6] for tr in T])
            rec[f"營量{lab}買進數"] = int(len(T))
            rec[f"營量{lab}淨報酬平均"] = float(nets.mean()) if len(T) else np.nan
            rec[f"營量{lab}淨報酬中位"] = float(np.median(nets)) if len(T) else np.nan
            rec[f"營量{lab}勝率"] = float((nets > 0).mean()) if len(T) else np.nan
            rec[f"營量{lab}貢獻和"] = float(con.sum()) if len(T) else 0.0
        rec["營量閘關買進占比"] = rec["營量閘關買進數"] / (rec["營量閘關買進數"] + rec["營量閘開買進數"])
        cl = CL[x + 1:y + 1]
        rY = daily_r(Y[0], x, y); rB = bench[x + 1:y + 1] / bench[x:y] - 1
        rec["營量閘關日累乘"] = float(np.prod(1 + rY[cl]) - 1); rec["營量閘開日累乘"] = float(np.prod(1 + rY[~cl]) - 1)
        rec["0050閘關日累乘"] = float(np.prod(1 + rB[cl]) - 1); rec["0050閘開日累乘"] = float(np.prod(1 + rB[~cl]) - 1)
        out[sg] = rec
    for i, (x, y) in enumerate(W["SPELLS"]):
        sg = next(s for s in SEGS[W["name"]] if s != "主窗" and W["segp"][s][0] <= x <= W["segp"][s][1])
        T = [tr for tr in Y[1] if x <= tr[1] <= y]
        nets = [net_ret(W, oY, tr) for tr in T]
        spells.append({"世界": W["name"], "段": sg, "起": str(cal[x].date()), "迄": str(cal[y].date()), "交易日": int(y - x + 1),
                       "營量買進數": len(T), "營量那些買進淨報酬平均": float(np.mean(nets)) if T else np.nan,
                       "營量那些買進勝率": float(np.mean(np.array(nets) > 0)) if T else np.nan,
                       "營量區間報酬": float(Y[0][y] / Y[0][x - 1] - 1), "營飆區間報酬中位": YFq.get(i, np.nan),
                       "0050區間報酬": float(bench[y] / bench[x - 1] - 1)})
    return out, spells


def rulebook():
    p = "backtest/forward/yl_rule/positions.csv"
    P = pd.read_csv(p, dtype={"代號": str}, encoding="utf-8-sig")
    h = P[P["狀態"] == "持有中"]
    A = h[h["策略"] == "營量v1"]; B = h[h["策略"] == "營飆v1"]
    sa, sb = set(A["代號"]), set(B["代號"])
    m = B.merge(A, on="代號", suffixes=("_飆", "_量"))
    same = bool((m["進場日_飆"] == m["進場日_量"]).all() and (m["進場價_飆"] == m["進場價_量"]).all())
    S = pd.read_csv("backtest/forward/yl_rule/signals.csv", dtype={"代號": str}, encoding="utf-8-sig")
    return {"檔": p, "檔sha16": hashlib.sha256(open(p, "rb").read()).hexdigest()[:16], "營量持有中": len(sa), "營飆持有中": len(sb),
            "交集": len(sa & sb), "營飆在營量中占比": len(sa & sb) / len(sb) if sb else np.nan, "營量在營飆中占比": len(sa & sb) / len(sa) if sa else np.nan,
            "交集同進場日同價": same, "營飆最後進場日": str(B["進場日"].max()), "營量最後進場日": str(A["進場日"].max()),
            "最早進場日": str(h["進場日"].min()), "訊號數": int(len(S)), "訊號日": [str(S["訊號日"].min()), str(S["訊號日"].max())],
            "閘關訊號數": int((~S["營飆大盤閘"].astype(bool)).sum()),
            "註": "起點效應：照規則簿 2026-09-29 起點兩邊都是空槽，前幾天訊號少於空槽 ⇒ 營飆把前 10 筆訊號全買、營量把前 20 筆全買 ⇒ 營飆 10 檔必然全在營量 20 檔裡；"
                  "之後營量 60 天到期換股、營飆抱 120 天、閘關時營飆不進，兩邊會分開（見回測起點效應列）"}


def q(v):
    v = pd.Series(v).astype(float)
    return float(v.median()), float(v.quantile(.1)), float(v.quantile(.9))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    log = log_to(os.path.join(OUT, "run.log"))
    log(f"[開始] {now_tpe()}（台北）｜讀法寫死 {TIME}｜營飆種子 {NSEED}")
    Wm, gm = IG.main_world(log)
    We, ge = IG.early_world(log, a.procs)
    Wm["bench"] = RR._G["bench"]; We["bench"] = RR.load_bench(We["cal"])
    for W in (Wm, We):
        prep_world(W, log)
    _W["主"], _W["早年"] = Wm, We
    S = {"讀法寫死": TIME, "性質": WORD, "早年註": NOTE_EARLY, "世界閘": {**gm, **ge}}
    jobs = [(wn, r) for wn in ("主", "早年") for r in range(NSEED)]
    T0 = time.time()
    with Pool(a.procs) as pool:
        ROWS = pool.map(job, jobs, chunksize=4)
    SE = pd.DataFrame(ROWS)
    log(f"[營飆] {len(SE)} 次｜{time.time() - T0:.0f}s")
    # ── 營量各段 ──
    YLrow = {}
    for wn, W in _W.items():
        Y = W["YLB"]; o = W["YLo"]
        rr = {"eq_sha": sha(Y[0]), "first": int(o["first"]), "end": int(o["end"]), "trades": int(o["trades"])}
        for sg in SEGS[wn]:
            x, y = W["segp"][sg]
            c_, m_, _ = RR.win_metrics(Y[0], o["first"], o["end"], x, y)
            rr[f"{sg}_年化"] = float(c_); rr[f"{sg}_回落"] = float(m_); rr[f"{sg}_營量持股"] = float(np.mean(Y[2][x:y + 1]))
        YLrow[wn] = rr
    # ── 閘 ──
    gate = {}
    t1 = pd.read_csv("backtest/resultsT1fix/seeds.csv.gz", dtype={"eq_sha": str}, float_precision="round_trip")
    c13 = t1[(t1["key"] == "c13") & (t1["var"] == "t1") & (t1["r"] == 0)].iloc[0]
    gate["G1 營量 主 ＝ T1fix c13 t1 r0"] = int(YLrow["主"]["eq_sha"] != c13["eq_sha"] or repr(YLrow["主"]["主窗_年化"]) != repr(float(c13["cagr"]))
                                           or repr(YLrow["主"]["主窗_回落"]) != repr(float(c13["mdd"])))
    refI = pd.read_csv("backtest/resultsYL_integrate/seeds.csv.gz", dtype={"eq_sha": str}, float_precision="round_trip")
    for wn in ("主", "早年"):
        b_ = refI[(refI["世界"] == wn) & (refI["格"] == IG.YL) & (refI["r"] == 0)].iloc[0]
        gate[f"G2 營量 {wn} ＝ 整合件 {IG.YL} r0"] = int(YLrow[wn]["eq_sha"] != b_["eq_sha"] or any(
            repr(YLrow[wn][f"{sg}_{k}"]) != repr(float(b_[f"{sg}_{k}"])) for sg in SEGS[wn] for k in ("年化", "回落")))
    r1 = t1[(t1["key"] == "c1") & (t1["var"] == "t1")].set_index("r")
    m1 = SE[SE["世界"] == "主"].set_index("r")
    gate["G3 營飆 主 ＝ T1fix c1 t1（不同顆數）"] = int(sum(m1.loc[r, "eq_sha"] != r1.loc[r, "eq_sha"] or repr(float(m1.loc[r, "主窗_年化"])) != repr(float(r1.loc[r, "cagr"]))
                                                 or repr(float(m1.loc[r, "主窗_回落"])) != repr(float(r1.loc[r, "mdd"])) for r in m1.index))
    for wn in ("主", "早年"):
        a_ = SE[SE["世界"] == wn].set_index("r"); b_ = refI[(refI["世界"] == wn) & (refI["格"] == IG.YF)].set_index("r")
        gate[f"G4 營飆 {wn} ＝ 整合件 {IG.YF}（不同顆數／{len(a_)}）"] = int(sum(
            a_.loc[r, "eq_sha"] != b_.loc[r, "eq_sha"] or any(repr(float(a_.loc[r, f"{sg}_{k}"])) != repr(float(b_.loc[r, f"{sg}_{k}"])) for sg in SEGS[wn] for k in ("年化", "回落"))
            for r in a_.index))
    if NSEED == 200:
        yfn = [z for z in json.load(open("backtest/resultsYF_N/summary.json", encoding="utf-8"))["表"] if z["N"] == 10]
        bad = 0
        for z in yfn:
            g = SE[SE["世界"] == z["世界"]]
            for k in ("年化", "回落"):
                bad += repr(float(g[f"{z['段']}_{k}"].median())) != repr(float(z[f"{k}_中位"]))
        gate["G5 營飆各段中位 ＝ resultsYF_N N10（不同項數）"] = int(bad)
    sm = json.load(open("backtest/resultsYL_integrate/summary.json", encoding="utf-8"))["0050"]
    gate["G6 0050 各段 ＝ 整合件（不同項數）"] = int(sum(repr(float(_W[wn]["b50"][sg][k])) != repr(float(sm[wn][sg][k]))
                                              for wn in ("主", "早年") for sg in SEGS[wn] for k in ("cagr", "mdd")))
    sim = pd.read_csv("backtest/resultsYL_blend/similarity_seeds.csv").set_index("r")
    gd = 0.0
    for r in m1.index:
        gd = max(gd, abs(m1.loc[r, "主窗_金額重疊"] - sim.loc[r, "持股重疊（按金額，日均）"]),
                 abs(m1.loc[r, "主窗_F買Y±0"] - sim.loc[r, "實買：營飆的買進也被營量同日買"]),
                 abs(m1.loc[r, "主窗_日報酬相關"] - sim.loc[r, "日報酬相關"]))
    gate["G7 主窗 金額重疊／同日實買／日報酬相關 ＝ blend 件（最大差）"] = float(gd)
    S["閘"] = gate
    log(f"[閘] {gate}")
    SE.to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False, float_format="%.17g")
    bad = [k for k, v in gate.items() if (v > 1e-9 if k.startswith("G7") else v != 0)]
    if bad:
        json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
        raise SystemExit(f"⛔ 閘不過 {bad}")
    # ── 彙總 ──
    C = []
    for wn in ("主", "早年"):
        W = _W[wn]; g = SE[SE["世界"] == wn]; yl = YLrow[wn]
        for sg in SEGS[wn]:
            x, y = W["segp"][sg]; b = W["b50"][sg]
            row = {"世界": wn, "段": sg, "窗": f"{W['cal'][x].date()}～{W['cal'][y].date()}", "營飆顆數": len(g)}
            row["營量_年化"], row["營量_回落"] = yl[f"{sg}_年化"], yl[f"{sg}_回落"]
            row["營量_比值"] = yl[f"{sg}_年化"] / abs(yl[f"{sg}_回落"]); row["營量_對0050"] = IG.label(yl[f"{sg}_年化"], yl[f"{sg}_回落"], b)
            row["營量_持股"] = yl[f"{sg}_營量持股"]
            for k in ("年化", "回落", "F中也在Y", "Y中也在F", "金額重疊", "營飆空手日", "營量空手日", "營飆持股", "F買Y±5", "F買Y±0", "F買時Y持有", "Y買F±5",
                      "F買進數", "Y買進數", "日報酬相關", "半半①年化", "半半①回落", "半半②年化", "半半②回落", "閘關日累乘", "閘開日累乘"):
                m_, p10, p90 = q(g[f"{sg}_{k}"])
                row[f"{k}_中位"], row[f"{k}_p10"], row[f"{k}_p90"] = m_, p10, p90
            row["營飆_比值"] = row["年化_中位"] / abs(row["回落_中位"]); row["營飆_對0050"] = IG.label(row["年化_中位"], row["回落_中位"], b)
            for z in ("①", "②"):
                row[f"半半{z}_比值"] = row[f"半半{z}年化_中位"] / abs(row[f"半半{z}回落_中位"])
                row[f"半半{z}_對0050"] = IG.label(row[f"半半{z}年化_中位"], row[f"半半{z}回落_中位"], b)
            row["0050年化"], row["0050回落"] = b["cagr"], b["mdd"]; row["0050比值"] = b["cagr"] / abs(b["mdd"])
            C.append(row)
    C = pd.DataFrame(C)
    C.to_csv(os.path.join(OUT, "cells.csv"), index=False, encoding="utf-8-sig", float_format="%.10g")
    ST = []
    for wn in ("主", "早年"):
        g = SE[SE["世界"] == wn]
        for a_, b_ in STARTB:
            k = f"起點{a_ + 1}-{b_}"
            ST.append({"世界": wn, "窗首起交易日": f"{a_ + 1}～{b_}", "窗": f"{_W[wn]['cal'][_W[wn]['w0'] + a_].date()}～{_W[wn]['cal'][_W[wn]['w0'] + b_ - 1].date()}",
                       "F中也在Y_中位": q(g[f"{k}_F中也在Y"])[0], "Y中也在F_中位": q(g[f"{k}_Y中也在F"])[0]})
    GT, SP = {}, []
    for wn in ("主", "早年"):
        g = SE[SE["世界"] == wn]
        yq = {i: float(g[f"spell{i}"].median()) for i in range(len(_W[wn]["SPELLS"]))}
        GT[wn], sp = gate_tables(_W[wn], yq); SP += sp
    pd.DataFrame(SP).to_csv(os.path.join(OUT, "gate_spells.csv"), index=False, encoding="utf-8-sig", float_format="%.6g")
    S["表"] = C.to_dict("records"); S["起點效應"] = ST; S["大盤閘"] = GT; S["閘關區間"] = SP; S["營量"] = YLrow
    S["照規則簿"] = rulebook()
    S["規則差異"] = [
        {"項": "進場訊號", "營量v1": "AND 訊號（T1 版；同一張訊號表）", "營飆v1": "同一組 AND 訊號（同一張訊號表）"},
        {"項": "持有天數", "營量v1": "60 個交易日（第 60 根收盤出）", "營飆v1": "120 個交易日（第 120 根收盤出）"},
        {"項": "檔數", "營量v1": "20 槽、每槽 ＝ 前一日權益 ÷ 20", "營飆v1": "10 槽、每槽 ＝ 前一日權益 ÷ 10"},
        {"項": "候選多於空槽時", "營量v1": "relvol（訊號日成交額 ÷ 前 60 日中位）大者先，無抽籤", "營飆v1": "抽籤（default_rng(1000＋r)，回測 200 顆）"},
        {"項": "大盤閘", "營量v1": "無", "營飆v1": "訊號日（進場前一日）0050 還原收盤 ＞ 200 日均才進"},
        {"項": "共同", "營量v1": "次日開盤進、等權、一檔一格、續抱不加碼、成本 0.585%／來回、停止交易強制出場", "營飆v1": "同左"}]
    S["完成（台北）"] = now_tpe()
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    report(S, C)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 60)
    log("\n" + C[["世界", "段", "營量_年化", "營量_回落", "年化_中位", "回落_中位", "F中也在Y_中位", "Y中也在F_中位", "金額重疊_中位", "F買Y±5_中位", "Y買F±5_中位", "日報酬相關_中位",
                  "半半①年化_中位", "半半①回落_中位"]].to_string(index=False))
    log(f"[完] {now_tpe()}（台北）")


def pct(v, d=1):
    return "—" if v is None or not np.isfinite(v) else f"{v * 100:.{d}f}%"


def sg_(v, d=1):
    return "—" if v is None or not np.isfinite(v) else f"{v * 100:+.{d}f}%"


def report(S, C):
    L = ["# 營量 v1 對 營飆 v1：差多少、選出來是否幾乎一樣", "", f"產出 {S['完成（台北）']}（台北）。回測線計算子代理。⭐ {WORD}；⛔ 不改任何規則。", "",
         "## ① 規則差異", "", "| 項 | 營量 v1 | 營飆 v1 |", "|---|---|---|"]
    L += [f"| {z['項']} | {z['營量v1']} | {z['營飆v1']} |" for z in S["規則差異"]]
    L += ["", "## ② 實際持股重疊（營量 1 條；營飆 200 顆中位〔p10～p90〕）", "",
          "| 段 | 營飆持股中也在營量 | 營量持股中也在營飆 | 金額重疊 | 營飆買進 ±5 天營量也買 | 同日 | 營飆買進時營量正持有 | 營量買進 ±5 天營飆也買 | 平均持股 營量／營飆 |",
          "|---|---|---|---|---|---|---|---|---|"]
    for _, r in C.iterrows():
        if r["段"] == "主窗":
            continue
        f = lambda k: f"{pct(r[k + '_中位'])}〔{pct(r[k + '_p10'])}～{pct(r[k + '_p90'])}〕"
        L.append(f"| {r['段']}（{r['窗']}） | {f('F中也在Y')} | {f('Y中也在F')} | {pct(r['金額重疊_中位'])} | {f('F買Y±5')} | {pct(r['F買Y±0_中位'])} | {pct(r['F買時Y持有_中位'])} | "
                 f"{f('Y買F±5')} | {r['營量_持股']:.1f}／{r['營飆持股_中位']:.1f} |")
    L += ["", "起點效應（回測窗首兩邊都從空簿開始）：", "", "| 世界 | 窗首起交易日 | 窗 | 營飆持股中也在營量 | 營量持股中也在營飆 |", "|---|---|---|---|---|"]
    L += [f"| {z['世界']} | {z['窗首起交易日']} | {z['窗']} | {pct(z['F中也在Y_中位'])} | {pct(z['Y中也在F_中位'])} |" for z in S["起點效應"]]
    L += ["", "## ③ 大盤閘", "", "| 段 | 閘關交易日占比 | 有訊號日中閘關 | 被閘擋訊號 | 營量閘關日買進（占比） | 淨報酬平均／中位／勝率（閘關） | 同（閘開） | 營量閘關買進貢獻和 | 閘關日累乘 營量／營飆中位／0050 |",
          "|---|---|---|---|---|---|---|---|---|"]
    for wn, sg in REPSEG:
        g = S["大盤閘"][wn][sg]; r = C[(C["世界"] == wn) & (C["段"] == sg)].iloc[0]
        L.append(f"| {sg} | {pct(g['閘關日占比'])}（{g['閘關日']}／{g['交易日']}） | {pct(g['有訊號日中閘關占比'])} | {g['被閘擋訊號']}／{g['段內訊號']}（{pct(g['被閘擋訊號占比'])}） | "
                 f"{g['營量閘關買進數']}（{pct(g['營量閘關買進占比'])}） | {sg_(g['營量閘關淨報酬平均'])}／{sg_(g['營量閘關淨報酬中位'])}／{pct(g['營量閘關勝率'], 0)} | "
                 f"{sg_(g['營量閘開淨報酬平均'])}／{sg_(g['營量閘開淨報酬中位'])}／{pct(g['營量閘開勝率'], 0)} | {sg_(g['營量閘關貢獻和'])} | "
                 f"{sg_(g['營量閘關日累乘'])}／{sg_(r['閘關日累乘_中位'])}／{sg_(g['0050閘關日累乘'])} |")
    L += ["", "連續閘關 ≥ 10 個交易日的區間：見 gate_spells.csv（營量買進數、那些買進的淨報酬、區間報酬 營量／營飆中位／0050）。", "",
          "## ④ 績效（營飆 200 顆中位；比值 ＝ 年化 ÷ |回落|）", "",
          "| 段 | 營量 年化／回落／比值／對 0050 | 營飆 年化／回落／比值／對 0050 | 0050 年化／回落／比值 | 日報酬相關 | 一半一半①每日再平衡 | 一半一半②段首各半不再平衡 |", "|---|---|---|---|---|---|---|"]
    for _, r in C.iterrows():
        if r["段"] == "主窗":
            continue
        L.append(f"| {r['段']} | {sg_(r['營量_年化'])}／{sg_(r['營量_回落'])}／{r['營量_比值']:.2f}／{r['營量_對0050']} | "
                 f"{sg_(r['年化_中位'])}／{sg_(r['回落_中位'])}／{r['營飆_比值']:.2f}／{r['營飆_對0050']} | {sg_(r['0050年化'])}／{sg_(r['0050回落'])}／{r['0050比值']:.2f} | "
                 f"{r['日報酬相關_中位']:.2f}〔{r['日報酬相關_p10']:.2f}～{r['日報酬相關_p90']:.2f}〕 | "
                 f"{sg_(r['半半①年化_中位'])}／{sg_(r['半半①回落_中位'])}／{r['半半①_比值']:.2f}／{r['半半①_對0050']} | "
                 f"{sg_(r['半半②年化_中位'])}／{sg_(r['半半②回落_中位'])}／{r['半半②_比值']:.2f}／{r['半半②_對0050']} |")
    rb = S["照規則簿"]
    L += ["", "## ⑤ 現在的照規則簿", "",
          f"positions.csv（sha16 {rb['檔sha16']}）：營量持有中 {rb['營量持有中']} 檔、營飆 {rb['營飆持有中']} 檔，交集 {rb['交集']} 檔（營飆 {pct(rb['營飆在營量中占比'], 0)} 在營量裡；"
          f"交集同進場日同價 {rb['交集同進場日同價']}）；最早進場 {rb['最早進場日']}、營飆最後進場 {rb['營飆最後進場日']}、營量最後進場 {rb['營量最後進場日']}。", "",
          f"⚠ {rb['註']}。回測起點效應列可對照：窗首頭 20 個交易日營飆持股幾乎全在營量裡，之後降到段平均。", "",
          "## 對帳", "", "```", json.dumps(S["閘"], ensure_ascii=False, indent=1), "```", "",
          f"早年註：{'；'.join(S['早年註'])}", "", f"⭐ {WORD}。"]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
