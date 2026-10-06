# -*- coding: utf-8 -*-
"""兩件已結案產業營收研究的挑中格持股 vs 營量 v1 正式版（T1）持股：重疊比例（描述，⛔ 不計 N、⛔ 不改任何結論）。回測線計算子代理，2026-10-07。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchOverlapYL yl | lag | rev | report
    （四步各自一個行程：lag 與 rev 的 PRE 全域狀態不同，⛔ 不可同一行程；yl 先跑，lag／rev 讀它的持股）

來源（⛔ 不改原程式、⛔ 不改 results 原檔、⛔ 不重跑挑格、⛔ 不改參數）
  ① PREREG產業營收加速但股價落後 seq2 挑中格 P2｜L250｜A2｜K1｜S1（條件換股）：researchIndRevLag_prereg（setup 用 meta 的 main sha、
     A 表讀 resultsIndRevLag/prereg/A_table.csv.gz、段快取 ~/indrevlagwork/ctx_{main,early}.pkl）⇒ 原 sim_cond 逐日重放
  ② PREREG產業營收加速 seq3 挑中格 A2｜K1｜S1｜季｜E0：researchIndRev_prereg（meta 的 main sha、resultsIndRev/prereg/A_table.csv.gz、
     ~/h2data/indrevpr_cache_{main,early}.pkl）⇒ 原 sim_ind（E0、top）逐日重放
  營量 v1 正式版 T1 ＝ researchT1fix #13 t1（build_ctx(True)、simulate_mtm(sig13, "H60", 20, default_rng(7000＋0), …, pick="relvol",
     queue_days=0, stop_force=SF)；relvol 排序不抽籤 ⇒ 種子無影響）；audit 逐筆 ⇒ 每日持股
對帳（照實報）：重放權益 vs 原 eq.npz 逐日最大差；重放 vs 原函式權益與成交逐筆；營量 eq_sha vs resultsT1fix/seeds.csv.gz（c13｜t1｜r0）、
  audit vs resultsYLlist/audit_seed0.csv.gz、由 audit 重建的權益 vs 引擎權益最大差
口徑
  持股 ＝ 當日收盤計值時仍在簿上的部位（各引擎自己的計值集合）；權重 ＝ 部位收盤市值 ÷ 該策略當日權益（含現金）
    ⚠ 營量引擎排程出場在出場日收盤賣 ⇒ 出場日已不在簿上（持有 ＝ 進場日～出場日前一日）；產業件開盤賣 ⇒ 賣出日不在簿上
  a 檔數重疊率 ＝ |兩邊都持有| ÷ 該件持有檔數（該件持有 0 檔的日子不入平均）；另報 ÷ 營量持有檔數（營量 0 檔的日子不入平均）
  b 金額重疊率 ＝ Σ min(該件權重, 營量權重)（每個交易日都算，一邊空手 ＝ 0），日平均
  c 營量持股屬於該件當日挑中產業的比例 ＝ 營量持股裡產業（該件 PIT 產業別，當日）＝ 該件當日持有中產業者 ÷ 營量持有檔數（另報金額版）；
    ① 的「當日挑中產業」＝ 位置上持有中的產業（含名單 0 檔、整個位置現金的情形）；② ＝ 最近一次換股日挑中的產業
  d 日報酬相關係數（Pearson；段內每個交易日 eq[t]／eq[t−1] − 1）；另附各自與 0050（RR.load_bench 還原收盤）的相關係數
  段：探索 2017-03-02～2021-12-30、確認 2022-01-03～2026-08-24、早年 2012-06-01～2014-12-30
    ⚠ 營量 v1 正式版（T1，resultsT1fix）只有主窗 2017-03-02～2026-08-24 ⇒ 早年段沒有營量持股 ⇒ a／b／c 與兩件互相關照實寫「沒有」
輸出 backtest/resultsOverlapYL/：summary.json、REPORT.md（中間檔放 ~/overlapylwork/，不進 repo）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pickle
import sys
import time
from collections import defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))

OUT = "backtest/resultsOverlapYL"
WORK = os.path.expanduser("~/overlapylwork")
SEGS = {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24"), "早年": ("2012-06-01", "2014-12-30")}
LAG_DIR = "backtest/resultsIndRevLag/prereg"
REV_DIR = "backtest/resultsIndRev/prereg"


class _A:
    procs = 3
    reuse_a = True


def log(x):
    print(f"[{time.strftime('%H:%M:%S')}] {x}", flush=True)


# ═════════════ 營量 v1 T1 ═════════════
def run_yl():
    from backtest import research11 as R
    from backtest import rerun17 as RR
    from backtest import researchT1fix as RT
    t0_ = time.time()
    ctx = RT.build_ctx(True)
    cal = ctx["cal"]; NC = len(cal); NP = ctx["ncal"]; w0, w1 = ctx["w0"], ctx["w1"]
    closes, opens, mk = ctx["closes"], ctx["opens"], ctx["mk"]
    SF = R.stop_force_days(R.valid_from_data(sorted(closes), mk, cal), w1)
    au = []
    o = R.simulate_mtm(ctx["sig13"], "H60", 20, np.random.default_rng(RR.P1_SEED0 + 0), closes, opens, NP, log=[], d_max=None,
                       pick="relvol", queue_days=0, return_equity=True, audit=au, stop_force=SF)
    eq = np.asarray(o["equity"], float)
    sha = hashlib.sha256(eq.tobytes()).hexdigest()[:16]
    c_, m_, v_ = RR.win_metrics(eq, o["first"], o["end"], w0, w1)
    ref = pd.read_csv("backtest/resultsT1fix/seeds.csv.gz", dtype={"eq_sha": str}, float_precision="round_trip")
    ref = ref[(ref["key"] == "c13") & (ref["var"] == "t1") & (ref["r"] == 0)].iloc[0]
    gate = {"eq_sha": sha == str(ref["eq_sha"]), "cagr": repr(float(c_)) == repr(float(ref["cagr"])), "mdd": repr(float(m_)) == repr(float(ref["mdd"])),
            "vol": repr(float(v_)) == repr(float(ref["vol"])), "first": int(o["first"]) == int(ref["first"]), "end": int(o["end"]) == int(ref["end"]),
            "trades": int(o["trades"]) == int(ref["trades"])}
    AU = pd.DataFrame(au)
    F0 = pd.read_csv("backtest/resultsYLlist/audit_seed0.csv.gz", dtype={"sid": str}, float_precision="round_trip")
    same_audit = bool(len(AU) == len(F0) and (AU["t"].to_numpy() == F0["t"].to_numpy()).all() and (AU["sid"].astype(str).to_numpy() == F0["sid"].to_numpy()).all()
                      and (AU["side"].to_numpy() == F0["side"].to_numpy()).all()
                      and all(np.array_equal(AU[k].to_numpy(float), F0[k].to_numpy(float)) for k in ("amt", "px", "cost")))
    gate["audit＝audit_seed0"] = same_audit
    # audit ⇒ 每日持股與重建權益
    byt = defaultdict(list)
    for a in au:
        byt[int(a["t"])].append(a)
    cash = 1.0; op = {}; eqR = np.full(NP, np.nan); hold = [dict() for _ in range(NC)]
    for t in range(NP):
        for a in byt.get(t, []):
            if a["side"] == "buy":
                cash -= a["amt"]; op[a["sid"]] = (a["amt"], a["px"])
            else:
                op.pop(a["sid"]); cash += a["amt"] - a["cost"]
        hv = 0.0
        for s, (amt, ep) in op.items():
            hv += amt * float(closes[s][t]) / ep
        eqR[t] = cash + hv
        if t < NC:
            hold[t] = {s: amt * float(closes[s][t]) / ep / eq[t] for s, (amt, ep) in op.items()}
    f_, e_ = int(o["first"]), int(o["end"])
    rng_ = slice(f_, min(e_, NP - 1) + 1)
    dif = np.abs(eqR[rng_] - eq[rng_])
    recon = {"比對日": [str(cal[f_].date()), str(cal[min(e_, NC - 1)].date())], "最大絕對差": float(np.nanmax(dif)),
             "最大相對差": float(np.nanmax(dif / np.abs(eq[rng_]))), "窗首前權益皆 1": bool(np.all(eq[:f_] == 1.0))}
    Y = {"dates": [str(d.date()) for d in cal], "eq": eq[:NC].copy(), "hold": hold, "gate": gate, "recon": recon,
         "win": [str(cal[w0].date()), str(cal[w1].date())], "first": f_, "end": e_, "trades": int(o["trades"]), "sf_n": int(o.get("x_stop_force_n", -1)),
         "cagr_mdd_主窗": [float(c_), float(m_)], "秒": round(time.time() - t0_)}
    os.makedirs(WORK, exist_ok=True)
    pickle.dump(Y, open(os.path.join(WORK, "yl.pkl"), "wb"), protocol=5)
    log(f"[營量] 閘 {gate}｜重建 {recon}｜{Y['秒']}s")
    if not all(gate.values()):
        log("⚠ 營量閘有不過的項目（照實報）")


# ═════════════ ① 條件換股重放（sim_cond 同一套，⛔ 只多記每日持股） ═════════════
def replay_cond(L, PRE, C, t0, t1, cfg):
    P, dl, ncal = C["P"], C["dl"], C["ncal"]
    SF = L.sfdays(C, t1)
    ver = "pit"; P_, A, Lw, K, S = cfg["P"], cfg["A"], cfg["L"], cfg["K"], cfg["S"]
    checks = set(c for c in C["checks"] if t0 - 1 <= c <= t1 - 1)
    eq = np.ones(ncal); scash = [1.0 / K] * K; sval = [1.0 / K] * K; sind = [None] * K
    pos = {}; pend = set(); trades = []; H = {}; IND = {}
    for t in range(t0, t1 + 1):
        for s in [s for s in pos if SF.get(s) is not None and t == SF[s] + 1]:
            u, amt, k = pos.pop(s)
            px = P[s]["c"][t]; cr = L.COST
            scash[k] += u * px - amt * cr
            pend.discard(s); trades.append((t, s, "sf", px))
        newbuy = {}
        if (t - 1) in checks:
            tc = t - 1
            RK = L.rank_tab(C, ver, tc, tc)
            for k in range(K):
                i = sind[k]
                if i is None:
                    continue
                x1, x2 = L.exit_test(RK, i, A, Lw)
                if x1 or x2:
                    pend |= {s for s, p_ in pos.items() if p_[2] == k}
                    sind[k] = None
            vac = [k for k in range(K) if sind[k] is None]
            if vac:
                held = {i for i in sind if i is not None}
                cl = L.cands(RK, P_, A, Lw, held, "rule", None)
                if cl is None:
                    cl = []
                PK = PRE.picks_at(C, ver, "W1", t)
                for k in vac:
                    if not cl:
                        continue
                    i = cl.pop(0)
                    lst = PK.get(i, {}).get(S, [])
                    buy = []
                    for s in lst:
                        if s in pos:
                            if pos[s][2] == k and s in pend:
                                pend.discard(s)
                            continue
                        buy.append(s)
                    sind[k] = i
                    newbuy[k] = (buy, len(lst))
        for s in sorted(pend):
            x = P[s]; o_t = x["o"][t]
            if x["trd"][t] and not x["dn_o"][t] and np.isfinite(o_t) and o_t > 0:
                px = o_t; kd = "open"
            elif (not x["trd"][t]) and s in dl and t > dl[s]["last"] and dl[s]["status"].startswith("delisted"):
                px = x["c"][t]; kd = "delist"
            else:
                continue
            u, amt, k = pos.pop(s)
            cr = L.COST
            scash[k] += u * px - amt * cr
            pend.discard(s); trades.append((t, s, kd, px))
        for k in sorted(newbuy):
            buy, n_i = newbuy[k]
            for s in buy:
                x = P[s]; o_t = x["o"][t]
                if not x["trd"][t] or not (np.isfinite(o_t) and o_t > 0):
                    continue
                if x["up_o"][t]:
                    continue
                amt = min(sval[k] / n_i, scash[k])
                if amt <= 1e-12:
                    break
                scash[k] -= amt
                pos[s] = [amt / o_t, amt, k]
                trades.append((t, s, "buy", o_t))
        hv = [0.0] * K
        for s, (u, _, k) in pos.items():
            hv[k] += u * P[s]["c"][t]
        sval = [scash[k] + hv[k] for k in range(K)]
        eq[t] = sum(sval)
        H[t] = {s: u * P[s]["c"][t] / eq[t] for s, (u, _, k) in pos.items()}
        IND[t] = [i for i in sind if i is not None]
    eq[t1 + 1:] = eq[t1]
    return {"eq": eq, "H": H, "IND": IND, "trades": trades}


# ═════════════ ② 定期換股重放（sim_ind E0／top 同一套，⛔ 只多記每日持股） ═════════════
def replay_ind(PRE, R, C, t0, t1, cfg):
    P, dl, ncal = C["P"], C["dl"], C["ncal"]
    if t1 not in C["SF"]:
        C["SF"][t1] = R.stop_force_days({s: v["valid"] for s, v in P.items()}, t1)
    SF = C["SF"][t1]
    ver = cfg["ver"]; A = cfg["A"]; K = cfg["K"]; S = cfg["S"]
    assert cfg["E"] == "E0" and cfg["order"] == "top" and cfg["elig"] == "W1"
    reb = PRE.reb_days(C, cfg["R"], t0, t1); rebset = set(reb)
    eq = np.ones(ncal); cash = 1.0
    pos = {}; pend = set(); held = {}; trades = []; H = {}; IND = {}
    chosen = []
    for t in range(t0, t1 + 1):
        for s in [s for s in pos if SF.get(s) is not None and t == SF[s] + 1]:
            u, amt = pos.pop(s)
            px = P[s]["c"][t]; cr = PRE.COST
            cash += u * px - amt * cr
            pend.discard(s); trades.append((t, s, "sf", px))
        sel = None
        if t in rebset:
            M = C["Mlast"][t]
            rk = PRE.ranked(ver, A, M, "top")
            if rk:
                chosen = list(rk[:K])
                PK = PRE.picks_at(C, ver, "W1", t)
                sel = []; div = {}
                for i in chosen:
                    lst = PK.get(i, {}).get(S, [])
                    n_i = PRE.SN["S3"] if S == "S3" else len(lst)
                    for s in lst:
                        sel.append(s); div[s] = K * n_i
            if sel is not None:
                pend = (pend | (set(pos) - set(sel))) - set(sel)
                for i in list(held):
                    if i not in chosen:
                        held.pop(i)
                for i in chosen:
                    if i not in held:
                        held[i] = t
        for s in sorted(pend):
            x = P[s]; o_t = x["o"][t]
            if x["trd"][t] and not x["dn_o"][t] and np.isfinite(o_t) and o_t > 0:
                px = o_t; kd = "open"
            elif (not x["trd"][t]) and s in dl and t > dl[s]["last"] and dl[s]["status"].startswith("delisted"):
                px = x["c"][t]; kd = "delist"
            else:
                continue
            u, amt = pos.pop(s)
            cr = PRE.COST
            cash += u * px - amt * cr
            pend.discard(s); trades.append((t, s, kd, px))
        if sel is not None:
            for s in [s for s in sel if s not in pos]:
                x = P[s]; o_t = x["o"][t]
                if not x["trd"][t] or not (np.isfinite(o_t) and o_t > 0):
                    continue
                if x["up_o"][t]:
                    continue
                amt = min(eq[t - 1] / div[s], cash)
                if amt <= 1e-12:
                    break
                cash -= amt
                pos[s] = [amt / o_t, amt]
                trades.append((t, s, "buy", o_t))
        hv = 0.0
        for s, (u, _) in pos.items():
            hv += u * P[s]["c"][t]
        eq[t] = cash + hv
        H[t] = {s: u * P[s]["c"][t] / eq[t] for s, (u, _) in pos.items()}
        IND[t] = sorted(held)
    eq[t1 + 1:] = eq[t1]
    return {"eq": eq, "H": H, "IND": IND, "trades": trades}


# ═════════════ 指標 ═════════════
def _corr(x, y):
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 3:
        return None
    return float(np.corrcoef(x[m], y[m])[0, 1])


def seg_metrics(C, rp, Y, PIT, bench, seg):
    cal = C["cal"]; eqA = rp["eq"]
    a_d, b_d = pd.Timestamp(SEGS[seg][0]), pd.Timestamp(SEGS[seg][1])
    ts = [t for t in range(1, C["ncal"]) if a_d <= cal[t] <= b_d]
    rA = np.array([eqA[t] / eqA[t - 1] - 1 for t in ts])
    rB = np.array([bench[t] / bench[t - 1] - 1 for t in ts])
    nA = [len(rp["H"].get(t, {})) for t in ts]
    out = {"交易日": len(ts), "日期": [str(cal[ts[0]].date()), str(cal[ts[-1]].date())], "該件平均持有檔數": float(np.mean(nA)),
           "該件空手日": int(sum(n == 0 for n in nA)), "d_該件對0050相關": _corr(rA, rB)}
    if Y is None or seg == "早年":
        out.update({"營量": "沒有（營量 v1 正式版 T1 只有主窗 2017-03-02～2026-08-24；早年段無正式版持股）",
                    "a_檔數重疊率_除該件": "沒有", "a_檔數重疊率_除營量": "沒有", "b_金額重疊率": "沒有", "c_營量持股屬該件挑中產業_檔數": "沒有",
                    "c_營量持股屬該件挑中產業_金額": "沒有", "d_兩件日報酬相關": "沒有"})
        return out
    yi = {d: k for k, d in enumerate(Y["dates"])}
    miss = [str(cal[t].date()) for t in ts if str(cal[t].date()) not in yi]
    a1, a2, b, c1, c2, anyov = [], [], [], [], [], []
    rY = []; nY = []
    for t in ts:
        ds = str(cal[t].date())
        HA = rp["H"].get(t, {})
        k = yi.get(ds)
        HY = Y["hold"][k] if k is not None else {}
        rY.append(Y["eq"][k] / Y["eq"][k - 1] - 1 if (k is not None and k >= 1) else np.nan)
        nY.append(len(HY))
        both = set(HA) & set(HY)
        if HA:
            a1.append(len(both) / len(HA))
        if HY:
            a2.append(len(both) / len(HY))
        anyov.append(int(len(both) > 0))
        b.append(sum(min(HA[s], HY[s]) for s in both))
        if HY:
            inds = set(rp["IND"].get(t, []))
            inn = [s for s in HY if PIT.at(s, cal[t], "pit")[0] in inds]
            c1.append(len(inn) / len(HY))
            tw = sum(HY.values())
            c2.append(sum(HY[s] for s in inn) / tw if tw > 0 else np.nan)
    rY = np.array(rY, float)
    out.update({"營量平均持有檔數": float(np.mean(nY)), "營量空手日": int(sum(n == 0 for n in nY)), "營量日曆缺日": len(miss),
                "a_檔數重疊率_除該件": float(np.mean(a1)) if a1 else None, "a_分母日數_該件有持股": len(a1),
                "a_檔數重疊率_除營量": float(np.mean(a2)) if a2 else None, "a_分母日數_營量有持股": len(a2),
                "同日至少一檔重疊的日子比例": float(np.mean(anyov)),
                "b_金額重疊率": float(np.mean(b)), "b_最大單日": float(np.max(b)),
                "c_營量持股屬該件挑中產業_檔數": float(np.mean(c1)) if c1 else None,
                "c_營量持股屬該件挑中產業_金額": float(np.nanmean(c2)) if c2 else None, "c_分母日數": len(c1),
                "d_兩件日報酬相關": _corr(rA, rY), "d_營量對0050相關": _corr(rY, rB)})
    return out


def _load_Y():
    return pickle.load(open(os.path.join(WORK, "yl.pkl"), "rb"))


def _recon(rp, ref_eq, orig, C, t0, t1):
    d = np.abs(rp["eq"] - ref_eq)
    return {"重放權益 vs eq.npz 最大絕對差": float(d.max()), "逐位元相同": bool(np.array_equal(rp["eq"], ref_eq)),
            "原函式權益 vs eq.npz 逐位元相同": bool(np.array_equal(orig["eq"], ref_eq)),
            "重放成交 ＝ 原函式成交（逐筆）": bool([(a, b, c, float(d_)) for a, b, c, d_ in rp["trades"]] == [(a, b, c, float(d_)) for a, b, c, d_ in orig["trades"]]),
            "成交筆數": len(rp["trades"]), "窗": [str(C["cal"][t0].date()), str(C["cal"][t1].date())]}


# ═════════════ ① ═════════════
def run_lag():
    from backtest import researchIndRevLag_prereg as L
    PRE = L.PRE
    t00 = time.time()
    meta = json.load(open(os.path.join(LAG_DIR, "meta.json"), encoding="utf-8"))
    L.setup(_A, meta["main"])
    AT = pd.read_csv(os.path.join(LAG_DIR, "A_table.csv.gz"), float_precision="round_trip")
    L.install_A(AT)
    Cm = L.prep_part("main", L.MAIN_W, L.SEG, _A); Ce = L.prep_part("early", L.EARLY_A, {"早年": L.EARLY_A}, _A)
    CH = meta["挑格"]["挑中參數"]; CH = {"P": CH["P"], "L": int(CH["L"]), "A": CH["A"], "K": int(CH["K"]), "S": CH["S"]}
    EQ = np.load(os.path.join(LAG_DIR, "eq.npz"))
    Y = _load_Y()
    res = {"件": "① PREREG產業營收加速但股價落後 seq2", "挑中格": meta["挑格"]["挑中"], "main_sha": meta["main"], "對帳": {}, "段": {}}
    for part, C in (("main", Cm), ("early", Ce)):
        t0, t1 = C["win"]
        orig = L.sim_cond(C, t0, t1, dict(CH, ver="pit", order="rule"))
        rp = replay_cond(L, PRE, C, t0, t1, CH)
        res["對帳"][part] = _recon(rp, EQ[part], orig, C, t0, t1)
        log(f"[① {part}] 對帳 {res['對帳'][part]}")
        for seg in (("探索", "確認") if part == "main" else ("早年",)):
            res["段"][seg] = seg_metrics(C, rp, Y if part == "main" else None, PRE._C["PIT"], C["bench"], seg)
            res["段"][seg]["meta平均持股"] = meta["挑中格細項"][seg]["平均持股"]
            log(f"[① {seg}] {res['段'][seg]}")
    res["秒"] = round(time.time() - t00)
    json.dump(res, open(os.path.join(WORK, "lag.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)


# ═════════════ ② ═════════════
def run_rev():
    from backtest import researchIndRev_prereg as PRE
    from backtest import research11 as R
    from backtest import researchScore as SC
    t00 = time.time()
    meta = json.load(open(os.path.join(REV_DIR, "meta.json"), encoding="utf-8"))
    PRE.setup(_A, meta["main"])
    AT = pd.read_csv(os.path.join(REV_DIR, "A_table.csv.gz"), float_precision="round_trip")
    PRE._C["RANK"] = PRE.build_rank(pd.concat([AT, AT[AT["ver"] == "pit"].assign(ver="剔除2023")], ignore_index=True))
    PRE._C["AV"] = {(v, M, i): {"A1": a1, "A2": a2, "A3": a3} for v, M, i, a1, a2, a3 in zip(AT["ver"], AT["M"], AT["產業"], AT["A1"], AT["A2"], AT["A3"])}
    for part, win, segs in (("main", PRE.MAIN_W, PRE.SEG), ("early", PRE.EARLY_A, {"早年": PRE.EARLY_A})):
        C = PRE.part_ctx(part, _A.procs); PRE.attach_months(C)
        C["win"] = (SC.pos_of(C["cal"], win[0]), SC.pos_of(C["cal"], win[1])); C["segp"] = PRE.segpos(C, segs)
        PRE._C[part] = C
    CH = meta["挑格"]["挑中參數"]; CH = {"A": CH["A"], "K": int(CH["K"]), "S": CH["S"], "R": CH["R"], "E": CH["E"]}
    EQ = np.load(os.path.join(REV_DIR, "eq.npz"))
    Y = _load_Y()
    res = {"件": "② PREREG產業營收加速 seq3", "挑中格": meta["挑格"]["挑中"], "main_sha": meta["main"], "對帳": {}, "段": {}}
    for part in ("main", "early"):
        C = PRE._C[part]; t0, t1 = C["win"]
        cfg = dict(CH, ver="pit", order="top", elig="W1")
        orig = PRE.sim_ind(C, t0, t1, cfg)
        rp = replay_ind(PRE, R, C, t0, t1, cfg)
        res["對帳"][part] = _recon(rp, EQ[part], orig, C, t0, t1)
        log(f"[② {part}] 對帳 {res['對帳'][part]}")
        for seg in (("探索", "確認") if part == "main" else ("早年",)):
            res["段"][seg] = seg_metrics(C, rp, Y if part == "main" else None, PRE._C["PIT"], C["bench"], seg)
            res["段"][seg]["meta平均持股"] = meta["挑中格細項"][seg]["平均持股"]
            log(f"[② {seg}] {res['段'][seg]}")
    res["秒"] = round(time.time() - t00)
    json.dump(res, open(os.path.join(WORK, "rev.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)


# ═════════════ 報告 ═════════════
def _p(x):
    return x if isinstance(x, str) else ("—" if x is None else f"{x * 100:.1f}%")


def _r(x):
    return x if isinstance(x, str) else ("—" if x is None else f"{x:+.2f}")


def report():
    Y = _load_Y()
    LG = json.load(open(os.path.join(WORK, "lag.json"), encoding="utf-8"))
    RV = json.load(open(os.path.join(WORK, "rev.json"), encoding="utf-8"))
    S = {"件": "產業營收兩件挑中格 vs 營量 v1（T1）持股重疊（描述，不計 N、不改結論）", "產出": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M") + "（台北）",
         "營量v1": {"閘": Y["gate"], "audit重建權益": Y["recon"], "窗": Y["win"], "成交": Y["trades"], "強制出場": Y["sf_n"], "主窗年化回落": Y["cagr_mdd_主窗"]},
         "①": LG, "②": RV, "口徑": __doc__.split("口徑")[1].split("輸出")[0].strip()}
    os.makedirs(OUT, exist_ok=True)
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    Ln = ["# 產業營收兩件挑中格 vs 營量 v1：持股重疊", "",
          f"產出 {S['產出']}。回測線計算子代理。⛔ 描述統計、不計 N、不改任何結論（兩件皆已結案）。", ""]
    for key, X in (("①", LG), ("②", RV)):
        Ln += [f"## {X['件']}（挑中格 {X['挑中格']}）", "",
               "| 段 | a 檔數重疊（÷該件） | a 檔數重疊（÷營量） | b 金額重疊 | c 營量持股屬該件挑中產業（檔數／金額） | d 日報酬相關 | 該件對 0050 | 營量對 0050 | 平均持股 該件／營量 |",
               "|---|---|---|---|---|---|---|---|---|"]
        for seg in ("探索", "確認", "早年"):
            m = X["段"][seg]
            if isinstance(m.get("b_金額重疊率"), str):
                Ln.append(f"| {seg}（{m['日期'][0]}～{m['日期'][1]}） | 沒有 | 沒有 | 沒有 | 沒有 | 沒有 | {_r(m['d_該件對0050相關'])} | 沒有 | {m['該件平均持有檔數']:.1f}／— |")
            else:
                Ln.append(f"| {seg}（{m['日期'][0]}～{m['日期'][1]}） | {_p(m['a_檔數重疊率_除該件'])} | {_p(m['a_檔數重疊率_除營量'])} | {_p(m['b_金額重疊率'])} | "
                          f"{_p(m['c_營量持股屬該件挑中產業_檔數'])}／{_p(m['c_營量持股屬該件挑中產業_金額'])} | {_r(m['d_兩件日報酬相關'])} | "
                          f"{_r(m['d_該件對0050相關'])} | {_r(m['d_營量對0050相關'])} | {m['該件平均持有檔數']:.1f}／{m['營量平均持有檔數']:.1f} |")
        Ln += ["", "對帳：" + "；".join(f"{p} 重放權益 vs eq.npz 最大差 {v['重放權益 vs eq.npz 最大絕對差']:.3g}（逐位元 {v['逐位元相同']}）、原函式 vs eq.npz 逐位元 {v['原函式權益 vs eq.npz 逐位元相同']}、"
                                     f"成交逐筆相同 {v['重放成交 ＝ 原函式成交（逐筆）']}（{v['成交筆數']} 筆）" for p, v in X["對帳"].items()), ""]
        for seg in ("探索", "確認"):
            m = X["段"][seg]
            Ln.append(f"- {seg}：同日至少一檔重疊的日子 {_p(m['同日至少一檔重疊的日子比例'])}；b 單日最大 {_p(m['b_最大單日'])}；該件空手 {m['該件空手日']} 日、營量空手 {m['營量空手日']} 日；營量日曆缺日 {m['營量日曆缺日']}")
        Ln.append("")
    Ln += ["## 營量 v1（T1）來源與對帳", "",
           f"- 重跑 researchT1fix #13 t1 r0：{json.dumps(Y['gate'], ensure_ascii=False)}",
           f"- 由 audit 逐筆重建權益 vs 引擎權益：{json.dumps(Y['recon'], ensure_ascii=False)}",
           f"- 早年段：營量 v1 正式版（T1）沒有早年結果 ⇒ 寫「沒有」", "",
           "## 口徑", "", S["口徑"], ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(Ln) + "\n")
    log("[report] 完")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["yl", "lag", "rev", "report"])
    a = ap.parse_args()
    {"yl": run_yl, "lag": run_lag, "rev": run_rev, "report": report}[a.mode]()
