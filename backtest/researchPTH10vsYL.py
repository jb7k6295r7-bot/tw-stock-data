# -*- coding: utf-8 -*-
"""52 週新高「10 檔版」對 營量 v1：持股重疊、進場重疊、報酬相關與各半——回測線計算子代理（使用者問「10 檔版跟營量重疊多高？」，2026-10-20）。
⭐ 描述、⛔ 不計 N、⛔ 不判；看過 resultsPTHpf／PTHn 結果之後才問 ⇒「描述、看過結果才問；前瞻照 seq402，不因此改」。
⛔ 只計算：不 commit、不改既有檔；researchPTHpf（build_world、load_events、tranche_sim、yl_compare、metrics）、researchPTHn（run_slot、trades_df、
   df_text、NOTE_EARLY）、researchPTH（stock_job）、researchYL_integrate（main_world、early_world、eng、YL）、researchYLvsYF（book、sha）、
   rerun17（win_metrics、bench_row）、researchAscTri（label、ratio）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTH10vsYL [--procs 4]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTH10vsYL_check
輸出 backtest/resultsPTH10vsYL/：PTH10vsYL.json、seg.csv、rolling12.csv、daily_<世界>.csv.gz、entries_<世界>.csv.gz、yl_trades_<世界>.csv.gz、run.log

讀法（★ 執行者定）：
 A1 10 檔版 ＝ researchPTHn.run_slot(ev, W, 10, False)（＝ researchPTHpf 描述①、seq402 前瞻口徑：10 格補空位、PTH 由高往下、空位抱 0050）；
    閘：eq/hv/u/pend/nh ＝ resultsPTHn/eq_<世界>.npz N10_* 與 resultsPTHpf/eq_<世界>.npz S10_* 逐位元；交易檔全文 ＝ resultsPTHn trades_<世界>_N10 逐字。
    營量 v1 ＝ researchYL_integrate.eng(W, YL, 0)（＝ T1fix c13 t1 r0）；持股 ＝ researchYLvsYF.book；閘：eq_sha ＝ 整合件 seeds r0、resultsYLvsYF 營量 eq_sha；
    主世界另對 T1fix c13 t1 r0（eq_sha、主窗年化／回落 repr）。管線閘：主判臂（6 份）重算 researchPTHpf.yl_compare ⇒ 與 resultsPTHpf/yl.csv（%.6g）逐字。
 A2 段 ＝ PTH 世界段（探索、確認、早年）∩ 營量窗（主 2017-03-02～2026-08-24；早年 2005-02-01～2014-12-31）共同交易日（＝ researchPTHpf.yl_compare 同式）。
 A3 持股（當日收盤仍在簿上 ＝ [買進日, 賣出日)）：逐日 ⓐ 10 檔版持股中營量也持有 ÷ 10 檔版持股（持股 ＞0 的日子）、ⓑ 反向；
    金額重疊 Σ_檔 min(10 檔版權重, 營量權重)（權重 ＝ 市值 ÷ 該策略淨值；10 檔版的 0050 不算持股）；同時持有檔數 ＝ |P∩Y| 逐日平均。
    ⓐⓑ、金額重疊 ＝ researchPTHpf.yl_compare 原式；本支另算一次並驗相同。
 A4 進場：10 檔版段內每筆買進 (檔, 日 t)，營量在 [t−20, t＋20] 個交易日內也買過同檔（買進日差以營量日曆計）⇒ 比例；另報 ±0、±5、
    「買進當天收盤營量正持有」；反向（營量買進中 10 檔版 ±20 也買過）。
 A5 報酬：日報酬相關、月報酬相關（段內月底、段首為基）＝ yl_compare；月報酬差 d ＝ 10 檔版 − 營量：平均、中位、正的月比例、
    月分群 95% CI ＝ 平均 ± t(0.975, n−1)·sd/√n（每月一群；⚠ 10 檔版抱 6 個月、營量抱 60 日 ⇒ 月與月不獨立，CI 偏窄）。
    各半 ③（本題口徑）：段首 ½／½；每年第一個交易日收盤調回 ½／½，成本 ＝ 搬動金額 × 0.585%（從淨值扣）；
    並列 10 檔版、營量單獨、0050（同窗）與 yl_compare 的各半①（每日再平衡、無成本）②（不再平衡）。年化、回落 ＝ rerun17.win_metrics；標籤 ＝ researchAscTri.label。
 A6 seq401 檢查條件的歷史值（⛔ 不判）：「相關 ＜0.9 或 對營量有正差」⇒ 段級（月報酬相關、年化差、月差平均）；
    滾動 12 個月（連續 12 個月報酬；主世界用 探索＋確認 全共同窗）：月報酬相關、12 個月累積報酬差（10 檔版 − 營量）；
    報 相關＜0.9 比例、差＞0 比例、任一成立比例（依窗尾月歸段）。
 必附：「描述、看過結果才問；前瞻照 seq402，不因此改」；早年附 researchPTHn.NOTE_EARLY（reduce_v2 約 0.3%）。
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchPTHpf as M                     # noqa: E402  ⛔ 只 import
from backtest import researchPTHn as PN                     # noqa: E402
from backtest import researchPTH as PTH                     # noqa: E402
from backtest import researchAscTri as AS                   # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402
from backtest import researchAddOn as RA                    # noqa: E402

OUT = "backtest/resultsPTH10vsYL"
COST = M.COST
WINS = (0, 5, 20)
SENT = "描述、看過結果才問；前瞻照 seq402，不因此改"
NOTE_EARLY = PN.NOTE_EARLY
SAMPLE_SEED = 20261021


def t975(df):
    """t 分佈 0.975 分位（Cornish–Fisher 展開；df ≥ 30 誤差 ＜ 1e−4）。"""
    z = 1.959963984540054
    return z + (z ** 3 + z) / (4 * df) + (5 * z ** 5 + 16 * z ** 3 + 3 * z) / (96 * df ** 2) + (3 * z ** 7 + 19 * z ** 5 + 17 * z ** 3 - 15 * z) / (384 * df ** 3)


def yl_build(wn, log, procs):
    """＝ researchPTHpf.yl_load 同式，另留 TR、cal、o。"""
    from backtest import researchYL_integrate as IG
    from backtest import researchYLvsYF as YV
    Wy, _ = IG.main_world(log) if wn == "主" else IG.early_world(log, procs)
    o, au = IG.eng(Wy, IG.YL, 0)
    eq, TR, cnt, H = YV.book(Wy, o, au)
    cal = Wy["cal"]; n = min(len(cal), len(eq))
    Y = {"dates": np.array([str(d.date()) for d in cal[:n]]), "eq": np.asarray(eq, float)[:n],
         "H": {k: (v[0][:n], v[1][:n]) for k, v in H.items()}, "sha": YV.sha(eq), "first": int(o["first"]), "end": int(o["end"]),
         "窗": [str(cal[Wy["w0"]].date()), str(cal[min(Wy["w1"], n - 1)].date())], "w0": int(Wy["w0"]), "w1": int(min(Wy["w1"], n - 1)),
         "TR": TR, "trades": int(o["trades"]), "eq_full": np.asarray(eq, float)}
    gate = {}
    ref = pd.read_csv("backtest/resultsYL_integrate/seeds.csv.gz", dtype={"eq_sha": str}, float_precision="round_trip")
    b_ = ref[(ref["世界"] == wn) & (ref["格"] == IG.YL) & (ref["r"] == 0)].iloc[0]
    gate["eq_sha ＝ resultsYL_integrate/seeds r0"] = Y["sha"] == b_["eq_sha"]
    segs = ("探索", "確認", "主窗") if wn == "主" else ("早年",)
    gate["各段年化／回落 repr ＝ 整合件 r0"] = all(
        repr(float(RR.win_metrics(eq, o["first"], o["end"], *Wy["segp"][sg])[i])) == repr(float(b_[f"{sg}_{k}"]))
        for sg in segs for i, k in ((0, "年化"), (1, "回落")))
    yv = json.load(open("backtest/resultsYLvsYF/summary.json", encoding="utf-8"))["營量"][wn]
    gate["eq_sha ＝ resultsYLvsYF 營量"] = Y["sha"] == yv["eq_sha"]
    if wn == "主":
        t1 = pd.read_csv("backtest/resultsT1fix/seeds.csv.gz", dtype={"eq_sha": str}, float_precision="round_trip")
        c13 = t1[(t1["key"] == "c13") & (t1["var"] == "t1") & (t1["r"] == 0)].iloc[0]
        c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], *Wy["segp"]["主窗"])
        gate["eq_sha、主窗年化／回落 ＝ T1fix c13 t1 r0"] = bool(Y["sha"] == c13["eq_sha"] and repr(float(c_)) == repr(float(c13["cagr"]))
                                                           and repr(float(m_)) == repr(float(c13["mdd"])))
    bad = [k for k, v in gate.items() if not v]
    if bad:
        raise SystemExit(f"⛔ 營量 v1 {wn} 閘不過 {bad}")
    log(f"[營量 v1 {wn}] eq_sha {Y['sha']}｜窗 {Y['窗']}｜trades {Y['trades']}｜閘 {gate}")
    return Y, {k: "相同" for k in gate}


def build_mv(W, S):
    """10 檔版逐檔市值（[買進日, 賣出日)），與 simulate 的 hv、nh 對。"""
    n0 = W["n0"]; CM = W["CM"]
    MV = np.zeros((CM.shape[0], n0))
    sl = {q: t for t, q, amt, proc in S["sells"]}
    for t, q, amt in S["buys"]:
        j = int(S["j"][q]); end = sl.get(q, n0)
        if end > t:
            MV[j, t:end] += amt * CM[j, t:end] / S["ep"][q]
    return MV


def common_days(W, Y, x, y):
    dP = W["dates"]; posY = {d: i for i, d in enumerate(Y["dates"])}
    tp = np.array([t for t in range(x, y + 1) if dP[t] in posY and Y["w0"] <= posY[dP[t]] <= Y["w1"]], np.int64)
    ty = np.array([posY[dP[t]] for t in tp], np.int64)
    return tp, ty


def daily_overlap(W, S, Y, tp, ty):
    ix = W["ix"]; MV = S["MV"]; sids = W["sids"]
    ys = list(Y["H"].keys()); jmap = np.array([ix.get(s, -1) for s in ys])
    YH = np.stack([Y["H"][s][0][ty] for s in ys], 1); YW = np.stack([Y["H"][s][1][ty] for s in ys], 1)
    A = MV[:, tp] > 0; WP = MV[:, tp] / S["eq"][tp][None, :]
    inY = jmap >= 0
    Asub = np.zeros_like(YH); Wsub = np.zeros_like(YW)
    Asub[:, inY] = A[jmap[inY], :].T; Wsub[:, inY] = WP[jmap[inY], :].T
    inter = (YH & Asub).sum(1); nA = A.sum(0); nB = YH.sum(1); amt = np.minimum(Wsub, YW).sum(1)
    hold_P = [";".join(sorted(sids[j] for j in np.flatnonzero(A[:, k]))) for k in range(len(tp))]
    hold_Y = [";".join(sorted(ys[i] for i in np.flatnonzero(YH[k]))) for k in range(len(tp))]
    return inter, nA, nB, amt, hold_P, hold_Y


def entries(W, S, Y, tp, ty, x, y):
    """A4：10 檔版段內買進 vs 營量買進；反向。"""
    dP = W["dates"]; posY = {d: i for i, d in enumerate(Y["dates"])}; posP = {d: i for i, d in enumerate(dP)}
    sid = W["sids"]
    BY = {}
    for s, tb, *_ in Y["TR"]:
        BY.setdefault(s, []).append(tb)
    BY = {s: np.array(sorted(v)) for s, v in BY.items()}
    lo, hi = int(ty[0]), int(ty[-1]); tlo, thi = int(tp[0]), int(tp[-1])
    rows = []
    for t, q, amt in S["buys"]:
        if not (tlo <= t <= thi) or dP[t] not in posY:
            continue
        s = sid[int(S["j"][q])]; k = posY[dP[t]]
        v = BY.get(s)
        dmin = int(np.min(np.abs(v - k))) if v is not None else -1
        held = bool(Y["H"][s][0][k]) if s in Y["H"] else False
        rows.append({"sid": s, "買進日": dP[t], "營量最近買進差(交易日)": dmin, **{f"營量±{w}": bool(v is not None and dmin <= w) for w in WINS},
                     "買進日營量正持有": held})
    BP = {}
    for t, q, amt in S["buys"]:
        BP.setdefault(sid[int(S["j"][q])], []).append(t)
    BP = {s: np.array(sorted(v)) for s, v in BP.items()}
    rev = {w: [0, 0] for w in WINS}
    for s, tb, *_ in Y["TR"]:
        if not (lo <= tb <= hi):
            continue
        d = Y["dates"][tb]
        if d not in posP:
            continue
        k = posP[d]; v = BP.get(s)
        for w in WINS:
            rev[w][0] += 1; rev[w][1] += int(v is not None and np.any(np.abs(v - k) <= w))
    return pd.DataFrame(rows), {f"營量買進中10檔版±{w}也買": (m / n if n else np.nan) for w, (n, m) in rev.items()} | {"營量段內買進數": rev[20][0]}


def month_idx(W, tp):
    mon = np.asarray(W["cal"].year * 12 + W["cal"].month)[tp]
    return [0] + [k for k in range(1, len(tp)) if k == len(tp) - 1 or mon[k + 1] != mon[k]]


def blend_annual(eP, eY, years):
    A = 0.5; B = 0.5; V = np.empty(len(eP)); V[0] = 1.0; cost = 0.0; moved = []
    for k in range(1, len(eP)):
        A *= eP[k] / eP[k - 1]; B *= eY[k] / eY[k - 1]
        if years[k] != years[k - 1]:
            tot = A + B; mv = abs(A - tot / 2.0); c = mv * COST
            moved.append(mv / tot); cost += c / tot
            tot -= c; A = B = tot / 2.0
        V[k] = A + B
    return V, moved, cost


def mt(e, bb):
    c_, m_, _ = RR.win_metrics(e, 0, len(e), 0, len(e) - 1)
    return {"年化": float(c_), "回落": float(m_), "比值": AS.ratio(c_, m_), "標籤": AS.label(c_, m_, bb)}


def seg_block(W, S, Y, x, y, sg, log):
    o = M.yl_compare(W, S, Y, x, y)
    tp, ty = common_days(W, Y, x, y)
    eP = S["eq"][tp]; eY = Y["eq"][ty]; b = W["Bc"][tp]
    inter, nA, nB, amt, hP, hY = daily_overlap(W, S, Y, tp, ty)
    with np.errstate(invalid="ignore", divide="ignore"):
        fa = np.where(nA > 0, inter / nA, np.nan); fb = np.where(nB > 0, inter / nB, np.nan)
    chk = {"ⓐ": (float(np.nanmean(fa)), o["本件持股中營量也持有(相異檔,逐日平均)"]), "ⓑ": (float(np.nanmean(fb)), o["營量持股中本件也持有(逐日平均)"]),
           "金額": (float(np.mean(amt)), o["金額重疊Σmin權重(逐日平均)"])}
    bad = {k: v for k, v in chk.items() if v[0] != v[1]}
    if bad:
        raise SystemExit(f"⛔ {sg} 本支重疊 ≠ yl_compare {bad}")
    me = month_idx(W, tp)
    mP = eP[me][1:] / eP[me][:-1] - 1.0; mY = eY[me][1:] / eY[me][:-1] - 1.0; d = mP - mY
    n = len(d); sd = float(np.std(d, ddof=1)); se = sd / math.sqrt(n); tq = t975(n - 1)
    years = np.asarray(W["cal"].year)[tp]
    V, moved, cst = blend_annual(eP, eY, years)
    bb = RR.bench_row(None, b, 0, len(b))
    EN, rev = entries(W, S, Y, tp, ty, x, y)
    R = {"窗": o["窗"], "共同交易日": o["共同交易日"], "月數": o["月數"],
         "持股": {"10檔版持股中營量也持有(逐日平均)": o["本件持股中營量也持有(相異檔,逐日平均)"], "營量持股中10檔版也持有(逐日平均)": o["營量持股中本件也持有(逐日平均)"],
                "金額重疊Σmin權重(逐日平均)": o["金額重疊Σmin權重(逐日平均)"], "同時持有檔數(逐日平均)": float(np.mean(inter)),
                "10檔版持股檔數(平均)": float(np.mean(nA)), "營量持股檔數(平均)": float(np.mean(nB)),
                "10檔版空手日比例": float(np.mean(nA == 0)), "同時持有≥1檔日比例": float(np.mean(inter >= 1)),
                "同時持有檔數分佈": {str(k): float(np.mean(inter == k)) for k in range(int(inter.max()) + 1)}},
         "進場": {"10檔版段內買進數": int(len(EN)), **{f"10檔版買進中營量±{w}也買": float(EN[f"營量±{w}"].mean()) if len(EN) else np.nan for w in WINS},
                "10檔版買進日營量正持有": float(EN["買進日營量正持有"].mean()) if len(EN) else np.nan, **rev},
         "報酬": {"日報酬相關": o["日報酬相關"], "月報酬相關": o["月報酬相關"],
                "月報酬差(10檔版−營量)": {"平均": float(d.mean()), "中位": float(np.median(d)), "正的月比例": float((d > 0).mean()), "sd": sd, "月數": n,
                                     "月分群95%CI": [float(d.mean() - tq * se), float(d.mean() + tq * se)], "t": float(d.mean() / se) if se > 0 else np.nan,
                                     "註": "每月一群；10 檔版抱 6 個月、營量抱 60 日 ⇒ 月與月不獨立，CI 偏窄"},
                "年化差(10檔版−營量)": o["本件(同窗)"]["年化"] - o["營量v1(同窗)"]["年化"]},
         "績效(同窗)": {"10檔版": o["本件(同窗)"], "營量v1": o["營量v1(同窗)"], "0050": o["0050"],
                     "各半③每年首日調回(扣0.585%)": {**mt(V, bb), "調回次數": len(moved), "平均搬動占淨值": float(np.mean(moved)) if moved else 0.0,
                                               "成本合計占淨值(累加)": float(cst), "成本每年": float(cst / (len(tp) / 245.0))},
                     "各半①每日再平衡(無成本,參考)": o["各半①每日再平衡"], "各半②段首各半不再平衡(參考)": o["各半②段首各半不再平衡"]}}
    DL = pd.DataFrame({"日": W["dates"][tp], "段": sg, "10檔版淨值": eP, "營量淨值": eY, "0050收盤": b, "各半③": V, "10檔版持股": nA, "營量持股": nB,
                       "同時持有": inter, "金額重疊": amt, "10檔版名單": hP, "營量名單": hY})
    EN.insert(0, "段", sg)
    log(f"[{sg}] {json.dumps(R, ensure_ascii=False, default=float)}")
    return R, DL, EN


def rolling12(W, S, Y, x, y, segp):
    tp, ty = common_days(W, Y, x, y)
    eP = S["eq"][tp]; eY = Y["eq"][ty]
    me = month_idx(W, tp)
    mP = eP[me][1:] / eP[me][:-1] - 1.0; mY = eY[me][1:] / eY[me][:-1] - 1.0
    ends = [W["dates"][tp[k]] for k in me[1:]]
    rows = []
    for k in range(11, len(mP)):
        a, b_ = mP[k - 11:k + 1], mY[k - 11:k + 1]
        cr = float(np.corrcoef(a, b_)[0, 1]); df = float(np.prod(1 + a) - np.prod(1 + b_))
        tE = tp[me[k + 1]]
        sg = next((s for s, (u, v) in segp.items() if u <= tE <= v), "")
        rows.append({"窗首月底": W["dates"][tp[me[k - 11]]], "窗尾月底": ends[k], "歸段(窗尾)": sg, "月報酬相關12m": cr, "12m報酬差(10檔版−營量)": df,
                     "10檔版12m": float(np.prod(1 + a) - 1), "營量12m": float(np.prod(1 + b_) - 1), "相關<0.9": cr < 0.9, "差>0": df > 0,
                     "任一成立": (cr < 0.9) or (df > 0)})
    return pd.DataFrame(rows)


def roll_sum(R):
    if not len(R):
        return {}
    return {"窗數": int(len(R)), "相關中位": float(R["月報酬相關12m"].median()), "相關p10": float(R["月報酬相關12m"].quantile(.1)),
            "相關p90": float(R["月報酬相關12m"].quantile(.9)), "相關最低": float(R["月報酬相關12m"].min()), "相關最高": float(R["月報酬相關12m"].max()),
            "相關<0.9比例": float(R["相關<0.9"].mean()), "差中位": float(R["12m報酬差(10檔版−營量)"].median()),
            "差p10": float(R["12m報酬差(10檔版−營量)"].quantile(.1)), "差p90": float(R["12m報酬差(10檔版−營量)"].quantile(.9)),
            "差>0比例": float(R["差>0"].mean()), "任一成立比例": float(R["任一成立"].mean()), "兩項皆不成立窗數": int((~R["任一成立"]).sum())}


def run(a, log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    J = {"題": "使用者問 52 週新高「10 檔版」與營量 v1 重疊多高", "身分": "描述（⛔ 不判、不計 N）", "結果句必附": SENT, "早年註": NOTE_EARLY,
         "開跑": M.now_tpe(), "閘": {}, "段": {}, "seq401檢查條件歷史值(不判)": {}}
    SEG = []; ROLL = []
    ylref = pd.read_csv(os.path.join(M.OUT, "yl.csv"), encoding="utf-8-sig", dtype=str)
    for wn in ("主", "早年"):
        W = M.build_world(wn, log)
        t0 = time.time(); RES = {}
        with Pool(a.procs) as pool:
            for sid, r in pool.imap_unordered(PTH.stock_job, [(wn, s) for s in W["sids"]], chunksize=8):
                if r is not None:
                    RES[sid] = r
        log(f"[{wn}] 逐股完 {len(RES)} 檔｜{time.time() - t0:.0f}s")
        ev, info = M.load_events(W, wn, "跳月", RES)
        del RES
        S = PN.run_slot(ev, W, 10, False)
        Zn = np.load(os.path.join(PN.OUT, f"eq_{wn}.npz")); Zp = np.load(os.path.join(M.OUT, f"eq_{wn}.npz"))
        for k in ("eq", "hv", "u", "pend", "nh"):
            if not (np.array_equal(S[k], Zn[f"N10_{k}"]) and np.array_equal(S[k], Zp[f"S10_{k}"])):
                raise SystemExit(f"⛔ 10 檔版 {wn} {k} ≠ resultsPTHn N10 / resultsPTHpf S10")
        with gzip.open(os.path.join(PN.OUT, f"trades_{wn}_N10.csv.gz"), "rt", encoding="utf-8") as fh:
            if PN.df_text(PN.trades_df(W, ev, S), "%.17g") != fh.read():
                raise SystemExit(f"⛔ 10 檔版 {wn} 交易檔 ≠ resultsPTHn")
        J["閘"][f"{wn}|10檔版 eq/hv/u/pend/nh ＝ resultsPTHn N10 ＝ resultsPTHpf S10"] = "逐位元相同"
        J["閘"][f"{wn}|10檔版交易檔 ＝ resultsPTHn trades_N10（全文）"] = f"逐字相同（{len(S['buys'])} 筆）"
        S["MV"] = build_mv(W, S)
        dh = float(np.max(np.abs(S["MV"].sum(0) - S["hv"])))
        nhk = bool(np.array_equal((S["MV"] > 0).sum(0), S["nh"].astype(int)))
        if dh > 1e-9 or not nhk:
            raise SystemExit(f"⛔ 逐檔市值 ≠ hv（{dh}）或檔數 ≠ nh（{nhk}）")
        J["閘"][f"{wn}|逐檔市值合計 ＝ hv（最大差）、檔數 ＝ nh"] = [dh, nhk]
        Y, g = yl_build(wn, log, a.procs)
        for k, v in g.items():
            J["閘"][f"{wn}|營量 {k}"] = v
        # 管線閘：主判臂 yl_compare ＝ resultsPTHpf/yl.csv
        SMv = M.tranche_sim(ev, 6, W, False, want_mv=True)
        if not np.array_equal(SMv["eq"], Zp["M_eq"]):
            raise SystemExit("⛔ 主判臂 eq ≠ resultsPTHpf")
        nbad = 0
        for sg, (x, y) in W["segp"].items():
            o = M.yl_compare(W, SMv, Y, x, y)
            if o is None:
                continue
            flat = {"世界": wn, "段": sg, **{k: v for k, v in o.items() if not isinstance(v, dict)},
                    **{f"{k}_{kk}": vv for k, v in o.items() if isinstance(v, dict) for kk, vv in v.items()}}
            txt = pd.DataFrame([flat]).to_csv(index=False, float_format="%.6g", header=False).strip().split(",")
            ref = ylref[(ylref["世界"] == wn) & (ylref["段"] == sg)].iloc[0].tolist()
            nbad += int(txt != [str(v) for v in ref])
        if nbad:
            raise SystemExit(f"⛔ 主判臂 yl_compare ≠ resultsPTHpf/yl.csv（{nbad} 段）")
        J["閘"][f"{wn}|管線：主判臂重算 yl_compare ＝ resultsPTHpf/yl.csv（%.6g 全列）"] = "逐字相同"
        del SMv
        # 日曆
        tpw, _ = common_days(W, Y, 0, W["n0"] - 1)
        yw = set(Y["dates"][Y["w0"]:Y["w1"] + 1]); pw = set(W["dates"][tpw[0]:tpw[-1] + 1])
        J["閘"][f"{wn}|日曆：營量窗內不在 PTH 日曆 / PTH 共同窗內不在營量日曆"] = [len(yw - pw), len(pw - yw)]
        DLs, ENs = [], []
        segs = {sg: v for sg, v in W["segp"].items()}
        for sg, (x, y) in segs.items():
            R, DL, EN = seg_block(W, S, Y, x, y, sg, log)
            J["段"][f"{wn}|{sg}"] = R; DLs.append(DL); ENs.append(EN)
            P_ = R["績效(同窗)"]
            SEG.append({"世界": wn, "段": sg, "窗": R["窗"], "共同交易日": R["共同交易日"], **R["持股"], **{k: v for k, v in R["進場"].items()},
                        "日報酬相關": R["報酬"]["日報酬相關"], "月報酬相關": R["報酬"]["月報酬相關"],
                        "月差平均": R["報酬"]["月報酬差(10檔版−營量)"]["平均"], "月差CI下": R["報酬"]["月報酬差(10檔版−營量)"]["月分群95%CI"][0],
                        "月差CI上": R["報酬"]["月報酬差(10檔版−營量)"]["月分群95%CI"][1], "月差正比例": R["報酬"]["月報酬差(10檔版−營量)"]["正的月比例"],
                        "年化差": R["報酬"]["年化差(10檔版−營量)"],
                        **{f"{k}_{m}": P_[k][m] for k in ("10檔版", "營量v1", "各半③每年首日調回(扣0.585%)", "各半①每日再平衡(無成本,參考)") for m in ("年化", "回落", "比值", "標籤")},
                        "0050_年化": P_["0050"]["年化"], "0050_回落": P_["0050"]["回落"], "0050_比值": P_["0050"]["比值"],
                        "各半③成本每年": P_["各半③每年首日調回(扣0.585%)"]["成本每年"]})
        # 抽樣日（查核用）
        rng = np.random.default_rng(SAMPLE_SEED)
        DLa = pd.concat(DLs, ignore_index=True)
        smp = []
        for sg in segs:
            v = DLa.index[DLa["段"] == sg].to_numpy()
            smp += sorted(int(i) for i in rng.choice(v, 3, replace=False))
        J["閘"][f"{wn}|抽樣日"] = {DLa.at[i, "日"]: f"{DLa.at[i, '10檔版持股']}/{DLa.at[i, '營量持股']}/{DLa.at[i, '同時持有']}" for i in smp}
        with gzip.open(os.path.join(OUT, f"daily_{wn}.csv.gz"), "wt", encoding="utf-8") as fh:
            DLa.to_csv(fh, index=False, float_format="%.17g")
        with gzip.open(os.path.join(OUT, f"entries_{wn}.csv.gz"), "wt", encoding="utf-8") as fh:
            pd.concat(ENs, ignore_index=True).to_csv(fh, index=False)
        with gzip.open(os.path.join(OUT, f"yl_trades_{wn}.csv.gz"), "wt", encoding="utf-8") as fh:
            pd.DataFrame([{"sid": s, "買進日": Y["dates"][tb] if tb < len(Y["dates"]) else "", "賣出日": Y["dates"][ts] if ts < len(Y["dates"]) else "",
                           "金額": amt, "買價": pin, "賣價": pout} for s, tb, ts, amt, pin, pout, _ in Y["TR"]]).to_csv(fh, index=False, float_format="%.17g")
        # 滾動 12 個月（主：探索＋確認 全共同窗）
        rs = {k: v for k, v in segs.items()}
        x0 = min(v[0] for v in rs.values()); y0 = max(v[1] for v in rs.values())
        RL = rolling12(W, S, Y, x0, y0, rs)
        RL.insert(0, "世界", wn); ROLL.append(RL)
        o = {"全部窗": roll_sum(RL)}
        for sg in segs:
            o[f"窗尾在{sg}"] = roll_sum(RL[RL["歸段(窗尾)"] == sg])
        for sg in segs:
            R = J["段"][f"{wn}|{sg}"]["報酬"]
            o[f"段級|{sg}"] = {"月報酬相關": R["月報酬相關"], "<0.9": R["月報酬相關"] < 0.9, "年化差": R["年化差(10檔版−營量)"],
                              "月差平均": R["月報酬差(10檔版−營量)"]["平均"], "正差(年化)": R["年化差(10檔版−營量)"] > 0}
        J["seq401檢查條件歷史值(不判)"][wn] = o
        log(f"[seq401 {wn}] {json.dumps(o, ensure_ascii=False, default=float)}")
        del W, S, Y, ev, Zn, Zp
    pd.DataFrame(SEG).to_csv(os.path.join(OUT, "seg.csv"), index=False, float_format="%.6g", encoding="utf-8-sig")
    pd.concat(ROLL, ignore_index=True).to_csv(os.path.join(OUT, "rolling12.csv"), index=False, float_format="%.6g", encoding="utf-8-sig")
    J["耗時秒"] = round(time.time() - T0); J["完成"] = M.now_tpe()
    json.dump(J, open(os.path.join(OUT, "PTH10vsYL.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 80)
    log("[段表]\n" + pd.DataFrame(SEG).T.to_string())
    log(f"[閘] {json.dumps(J['閘'], ensure_ascii=False, default=float)}")
    log(f"[完] {J['耗時秒']}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    run(a, RA.log_to(os.path.join(OUT, "run.log")))


if __name__ == "__main__":
    main()
