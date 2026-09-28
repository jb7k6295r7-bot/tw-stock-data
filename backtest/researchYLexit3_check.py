# -*- coding: utf-8 -*-
"""PREREG營量出場 seq3 獨立查核（⛔ 不 import researchYLexit3、researchYLexit）。
世界照本體來源（researchT1fix.build_ctx(True)、researchV.body_setup("main")）；警訊、甲 seq3 路徑（含買回上限 1）、乙 seq3 出場、配對差、統計全部自寫；引擎 research11。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchYLexit3_check.py

 ① 兩件挑中格＋營量 v1（主、早年）自寫 ⇒ 種子 0 eq_sha ＝ seeds.csv
 ② 配對差序列 ＝ pairdiff.npz；CR0 CI ＝ cells.csv
 ③ 中位、標籤、退化、挑格、件標籤、對營量讀法
 ④ 甲路徑必報（主、早年）：放棄原因、各 W 筆數、買回次數分佈（有上限）＝ summary
 ⑤ 假訊號 p ＝ summary
"""
from __future__ import annotations
import hashlib, json, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import research11 as R
from backtest import rerun17 as RR

OUT = "backtest/resultsYLexit3"
COST = R.COST


def h16(eq):
    return hashlib.sha256(np.asarray(eq, float).tobytes()).hexdigest()[:16]


def load(s, mk, cal, rev):
    b = R.load_bars(s, mk.get(s, "twse"), cal)
    if b is None:
        return None
    idx = b["idx"]; o, h, l, c = b["o"], b["h"], b["l"], b["c"]; v = b["df"]["volume"].to_numpy(float)[idx]; nbar = len(idx)
    vm = np.full(nbar, np.nan)
    for i in range(20, nbar):
        w = v[i - 20:i]
        if np.isfinite(w).all():
            vm[i] = w.sum() / 20
    hh = np.full(nbar, np.nan)
    for i in range(60, nbar):
        hh[i] = h[i - 60:i].max()
    ma = np.full(nbar, np.nan)
    for i in range(49, nbar):
        ma[i] = c[i - 49:i + 1].mean()
    W = {w: np.zeros(nbar, bool) for w in ("W1", "W2", "W3", "W4")}
    for i in range(1, nbar):
        if np.isfinite(vm[i]):
            W["W1"][i] = c[i] / c[i - 1] - 1 <= -0.03 and v[i] >= vm[i] * 2
            W["W2"][i] = np.isfinite(hh[i]) and c[i] >= hh[i] * 0.95 and v[i] >= vm[i] * 2 and (c[i] - o[i]) / o[i] <= -0.04
            W["W3"][i] = np.isfinite(ma[i - 1]) and c[i - 1] >= ma[i - 1] and np.isfinite(ma[i]) and c[i] < ma[i] and v[i] >= vm[i] * 1.5
    for sp_, y_ in rev.get(s, ()):
        j = int(np.searchsorted(idx, sp_, side="right"))
        if j < nbar and np.isfinite(y_) and y_ < 0:
            W["W4"][j] = True
    return {"idx": idx, "o": o, "c": c, "nb": b["next_bad"], "W": W, "of": b["df"]["open"].to_numpy(float), "cf": b["df"]["close"].to_numpy(float)}


def exit_h(sig, H, B, n0, EVD):
    X = []; G = []
    for s, k in zip(sig["sid"], sig["k"].astype(int)):
        b = B.get(s)
        if b is None:
            X.append(-1); G.append(np.nan); continue
        idx, o, c = b["idx"], b["o"], b["c"]; n = len(idx); nbk = b["nb"][max(0, k - 20)]; ex = k + H
        if ex < n and ex < nbk:
            x, g = int(idx[ex]), c[ex] / o[k + 1] - 1
        elif ex >= n and nbk > n - 1 and int(idx[n - 1]) == n0 - 1:
            x, g = n0, float(c[n - 1] / o[k + 1] - 1)
        else:
            X.append(-1); G.append(np.nan); continue
        ent = int(idx[k + 1])
        for pe, pL in EVD.get(s, []):
            if ent <= pL and x >= pe:
                x, g = pL, b["cf"][pL] / b["of"][ent] - 1
        X.append(x); G.append(g)
    t = sig.copy(); t[f"xpos_H{H}"] = np.array(X, np.int64); t[f"g_H{H}"] = np.array(G)
    return t[t[f"xpos_H{H}"] >= 0]


def jia3(sig, H, bb, cl, op, NP, n0, B, newk, M=1, L=10):
    rows = []; ac = {}; ao = {}; hm = {}; st = []
    for s, k, e, x, g0, rv in zip(sig["sid"], sig["k"].astype(int), sig["entry_pos"].astype(int), sig[f"xpos_H{H}"].astype(int), sig[f"g_H{H}"].astype(float), sig["relvol"]):
        b = B.get(s)
        if b is None or x < 0:
            rows.append((s, s, e, x, g0, rv)); st.append((e, 0, 0, None, (), False)); continue
        idx = b["idx"]; Wn = b["W"]; nk = newk.get(s, set())
        last = int(np.searchsorted(idx, (NP - 2) if x >= n0 else x, side="right") - 1)
        P0 = float(op[s][e]); inm = True; ve = 1.0; pe = P0; vf = 0.0; todo = None; nout = nre = 0; val = {}; sb = None; why = None; ws = (); rel = None
        for j in range(k + 1, last + 1):
            t = int(idx[j]); ot = float(op[s][t]); ct = float(cl[s][t])
            if todo == "s" and inm and np.isfinite(ot) and ot > 0:
                vf = ve * ot / pe; inm = False; nout += 1; sb = j
            elif todo == "b" and not inm and np.isfinite(ot) and ot > 0:
                ve = vf * (1 - COST); pe = ot; inm = True; nre += 1
            elif todo == "a":
                if inm and np.isfinite(ot) and ot > 0:
                    vf = ve * ot / pe; inm = False; nout += 1; sb = j
                val[t] = vf; rel = t; break
            todo = None
            val[t] = ve * ct / pe if inm else vf
            if j >= last:
                break
            if inm:
                if ct < P0 * (1 - bb):
                    todo = "s"
                    if M is not None and nre >= M:
                        todo = "a"; why = "買回上限"; continue
                    h_ = tuple(w for w in ("W1", "W2", "W3", "W4") if Wn[w][j])
                    if h_:
                        todo = "a"; why = "警訊"; ws = h_
            else:
                h_ = tuple(w for w in ("W1", "W2", "W3", "W4") if Wn[w][j])
                if h_:
                    todo = "a"; why = "警訊"; ws = h_
                elif ct >= P0 or j in nk:
                    todo = "b"
                elif j - sb + 1 >= L:
                    todo = "a"; why = f"等滿{L}"
        st.append((e, nout, nre, why, ws, (not inm) and rel is None))
        if nout == 0:
            rows.append((s, s, e, x, g0, rv)); continue
        arr = np.array(cl[s], dtype=float, copy=True); cur = None
        for t in range(e, NP):
            cur = val.get(t, cur)
            if cur is not None:
                arr[t] = P0 * cur
        xp = rel if rel is not None else x
        key = f"{s}#{e}"; ac[key] = arr; ao[key] = op[s]; hm[key] = s
        rows.append((key, s, e, xp, arr[min(xp, NP - 1)] / P0 - 1, rv))
    T = pd.DataFrame(rows, columns=["sid", "u", "entry_pos", f"xpos_H{H}", f"g_H{H}", "relvol"])
    for u in set(T["u"]):
        hm.setdefault(u, u)
    return T, ac, ao, hm, st


def yi3(sig, K, cs, C, B, n0):
    S2 = sig.copy(); X = S2["xpos_H60"].to_numpy(np.int64).copy(); G = S2["g_H60"].to_numpy(float).copy()
    for i, (s, k, x0) in enumerate(zip(S2["sid"], S2["k"].astype(int), X)):
        b = B.get(s)
        if x0 < 0 or b is None:
            continue
        idx, o, c = b["idx"], b["o"], b["c"]; n = len(idx); nbk = b["nb"][max(0, k - 20)]; ke = k + 1; kk = ke + K - 1; kc = ke + C - 1; ep = o[ke]
        if kk > n - 1 or kk >= nbk:
            continue
        Bv = c[kk]; lim = min(kc, n - 1, nbk - 1); done = False
        for j in range(kk + 1, lim + 1):
            if c[j] < Bv:
                X[i], G[i] = (int(idx[j + 1]), o[j + 1] / ep - 1) if j + 1 <= lim else (int(idx[j]), c[j] / ep - 1); done = True; break
            if (j - kk) % cs == 0:
                Bv = max(Bv, c[j])
        if done:
            continue
        if lim == kc:
            X[i], G[i] = int(idx[kc]), c[kc] / ep - 1
        elif lim == nbk - 1 and nbk <= min(kc, n - 1):
            X[i], G[i] = int(idx[lim]), c[lim] / ep - 1
        else:
            X[i], G[i] = (n0 if int(idx[n - 1]) == n0 - 1 else int(idx[n - 1])), c[n - 1] / ep - 1
    S2["xpos_H60"] = X; S2["g_H60"] = G
    return S2


def run(sig, rule, cl, op, NP, SF, hm=None):
    return np.asarray(R.simulate_mtm(sig, rule, 20, np.random.default_rng(7000), cl, op, NP, return_equity=True, log=[], d_max=None, pick="relvol",
                                     queue_days=0, stop_force=SF, held_map=hm)["equity"], float)


def main():
    RES = {}
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    SE = pd.read_csv(os.path.join(OUT, "seeds.csv.gz"), dtype={"eq_sha": str}, low_memory=False)
    PT = pd.read_csv(os.path.join(OUT, "cells.csv"))
    PD = np.load(os.path.join(OUT, "pairdiff.npz"))
    J = S["判定"]; pj, py = J["甲"]["挑中"], J["乙"]["挑中"]
    bj = int(pj.split("_b")[1].split("_")[0]) / 100; Hj = int(pj.split("_H")[1].split("_")[0])
    Ky = int(py.split("_k")[1].split("_")[0]); cy = int(py.split("_c")[1].split("_")[0]); Cy = int(py.split("_C")[1])
    bad1 = []; bad2 = []; bad4 = []
    for wk in ("主", "早年"):
        RR.use_snapshot()
        if wk == "主":
            from backtest import researchT1fix as T1
            ctx = T1.build_ctx(True); cal = ctx["cal"]; cl, op, NP = ctx["closes"], ctx["opens"], ctx["ncal"]; mk = ctx["mk"]; w0, w1 = ctx["w0"], ctx["w1"]
            base = ctx["sig13"]; ALL = RR._G["AND"]; EVD = {}; rp = os.path.join(RR.OUT, "sig_edc6f", "panel_rev.csv.gz")
            segs = {sg: (int(cal.searchsorted(pd.Timestamp(x))), int(cal.searchsorted(pd.Timestamp(y)))) for sg, (x, y) in (("探索", ("2017-03-02", "2021-12-30")), ("確認", ("2022-01-03", "2026-08-24")))}
        else:
            from backtest import researchV as V
            from backtest import researchYear1M as Y
            from backtest import early_data as E
            V.body_setup("main", lambda x: None)
            cal = V._B["cal"]; w0, w1 = V._B["w0"], V._B["w1"]; cl, op, NP = Y._G["closes"], Y._G["opens"], Y._G["NP"]; mk = Y._G["uni"]
            base = Y.sig_of(13, "mtm", w0, w1); ALL = Y.sig_of(13, "mtm", 0, len(cal) + 5); rp = os.path.join(V.body_paths("main")[1], "panel_rev.csv.gz")
            EV = pd.read_csv(os.path.join(E.snap_dir(E.BODY_SHA), "reduce_events.csv"), dtype=str)
            pos = {d.strftime("%Y-%m-%d"): j for j, d in enumerate(cal)}; EVD = {}
            for s_, e_, L_ in zip(EV["stock_id"], EV["e"], EV["L"]):
                if e_ in pos and L_ in pos:
                    EVD.setdefault(s_, []).append((pos[e_], pos[L_]))
            segs = {"早年": (w0, w1)}
        rvd = pd.read_csv(rp, dtype={"stock_id": str}, usecols=["stock_id", "signal_pos", "yoy"])
        rev = {s: list(zip(g["signal_pos"].astype(int), g["yoy"].astype(float))) for s, g in rvd.groupby("stock_id")}
        B = {s: load(s, mk, cal, rev) for s in sorted(set(base["sid"]))}
        newk = {s: set(g["k"].astype(int)) for s, g in ALL.groupby("sid")}
        SF = {}
        for s in sorted(cl):
            st_ = D.load_stock(s, mk.get(s, "twse"), cal)
            if st_ is None:
                continue
            v_ = np.flatnonzero(np.isfinite(st_.df["close"].to_numpy(float)))
            if len(v_) and v_[-1] < w1:
                SF[s] = int(v_[-1])
        sj = base if Hj == 60 else exit_h(base, Hj, B, len(cal), EVD)
        TJ, ac, ao, hm, st = jia3(sj, Hj, bj, cl, op, NP, len(cal), B, newk)
        SFJ = {**SF, **{k_: SF[u] for k_, u in hm.items() if u in SF and k_ != u}}
        TY = yi3(base, Ky, cy, Cy, B, len(cal))
        eb = run(base, "H60", cl, op, NP, SF); ej = run(TJ, f"H{Hj}", {**cl, **ac}, {**op, **ao}, NP, SFJ, hm); ey = run(TY, "H60", cl, op, NP, SF)
        for nm, eq in (("營量v1", eb), (pj, ej), (py, ey)):
            ref = SE[(SE["世界"] == wk) & (SE["格"] == nm) & (SE["r"] == 0)]["eq_sha"].iloc[0]
            if h16(eq) != ref:
                bad1.append((wk, nm))
        for nm, eq in ((pj, ej), (py, ey)):
            for sg, (x, y) in segs.items():
                d = (eq[x + 1:y + 1] / eq[x:y] - 1) - (eb[x + 1:y + 1] / eb[x:y] - 1)
                mon = np.array([str(z)[:7] for z in cal[x + 1:y + 1]]); mu = d.mean(); s_ = pd.Series(d - mu).groupby(mon).sum().to_numpy(); se = np.sqrt((s_ ** 2).sum()) / len(d)
                r_ = PT[PT["格"] == nm].iloc[0]
                if np.max(np.abs(d - PD[f"{wk}|{nm}|{sg}"])) > 1e-12 or abs(mu * 245 - r_[f"{sg}_配對差年化"]) > 1e-12 or abs((mu + 1.96 * se) * 245 - r_[f"{sg}_配對差hi"]) > 1e-12:
                    bad2.append((wk, nm, sg))
        inw = [x for x in st if w0 <= x[0] <= w1]; ot = [x for x in inw if x[1] > 0]
        ref4 = S["路徑必報"][f"{wk}|甲"]
        mine = {"放棄原因：警訊": sum(x[3] == "警訊" for x in ot), "放棄原因：等滿10": sum(x[3] == "等滿10" for x in ot), "放棄原因：買回上限": sum(x[3] == "買回上限" for x in ot),
                **{f"警訊含 {w}（筆）": sum(w in x[4] for x in ot) for w in ("W1", "W2", "W3", "W4")}}
        for k_, v_ in mine.items():
            if v_ != ref4[k_]:
                bad4.append((wk, k_, v_, ref4[k_]))
        dist = pd.Series([x[2] for x in inw]).value_counts().sort_index().to_dict()
        if {str(k_): v_ for k_, v_ in dist.items()} != {str(k_): v_ for k_, v_ in ref4["每筆買回次數分佈（有上限 1）"].items()}:
            bad4.append((wk, "買回次數分佈"))
        print(wk, "done", bad1, bad2, bad4, flush=True)
    RES["① 挑中格與營量 v1 自寫 ⇒ 種子 0 eq_sha（主、早年）"] = {"不符": bad1, "過": not bad1}
    RES["② 配對差序列、CR0 CI"] = {"不符": bad2, "過": not bad2}
    RES["④ 甲路徑必報（放棄原因、各 W、買回次數分佈）"] = {"不符": bad4, "過": not bad4}
    Z = S["0050"]; bad3 = []; picks = {}
    main_ = PT[PT["件"].isin(["base", "甲", "乙", "營飆描述"])]
    for r_ in main_.to_dict("records"):
        for sg in ("探索", "確認", "早年"):
            c, m = r_[f"{sg}_年化"], r_[f"{sg}_回落"]
            lab = "合格" if (c > Z[sg]["cagr"] and c / abs(m) >= Z[sg]["cagr"] / abs(Z[sg]["mdd"])) else ("另列" if c > Z[sg]["cagr"] else "不合格")
            if lab != r_[f"{sg}_標籤"]:
                bad3.append((r_["格"], sg))
    for fam in ("甲", "乙"):
        c = PT[PT["件"] == fam].copy(); c = c[~((c["探索_持股"] < 10) | ((fam == "乙") & (c["探索_現金"] > 0.30)))]
        q = c[c["探索_標籤"] == "合格"] if (c["探索_標籤"] == "合格").any() else c
        picks[fam] = q.sort_values(["探索_比值", "探索_年化"], ascending=[False, False]).iloc[0]["格"]
        rr = PT[PT["格"] == picks[fam]].iloc[0]; order = {"不合格": 0, "另列": 1, "合格": 2}
        if min((rr["確認_標籤"], rr["早年_標籤"]), key=lambda z: order[z]) != J[fam]["件標籤"]:
            bad3.append((fam, "件標籤"))
        lo, hi, ed = rr["確認_配對差lo"], rr["確認_配對差hi"], rr["早年_配對差年化"]
        vs = ("比營量 v1 好" if ed > 0 else "不穩（確認段好、早年反向）") if lo > 0 else (("比營量 v1 差" if ed < 0 else "不穩（確認段差、早年反向）") if hi < 0 else "分不出（確認段配對差 CI 含 0）")
        if vs != J[fam]["對營量v1"]:
            bad3.append((fam, "對營量"))
    RES["③ 標籤、挑格、件標籤、對營量讀法"] = {"不符": bad3, "自挑": picks, "過": not bad3 and picks["甲"] == pj and picks["乙"] == py}
    FK = pd.read_csv(os.path.join(OUT, "fake.csv.gz")); bad5 = []
    for fam, pk in (("甲", pj), ("乙", py)):
        f_ = FK[FK["格"] == pk]
        for sg, v in J[fam]["假訊號"].items():
            if abs(float(np.mean(f_[f"{sg}_年化"].dropna() >= J[fam][f"{sg}_年化"])) - v["p（假年化 ≥ 本格年化）"]) > 1e-12:
                bad5.append((fam, sg))
    RES["⑤ 假訊號 p"] = {"不符": bad5, "過": not bad5}
    RES["全部過"] = all(v["過"] for v in RES.values() if isinstance(v, dict))
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(RES, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
