# -*- coding: utf-8 -*-
"""PREREG營量出場 seq1 獨立查核（⛔ 不 import researchYLexit）。
世界照本體來源取（researchT1fix.build_ctx(True)、researchV.body_setup("main")），甲的合成路徑、乙的出場改寫、配對差、統計全部自寫；引擎 research11.simulate_mtm。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchYLexit_check.py [--seeds 200]

 ① 兩件挑中格（主、早年）自寫 ⇒ 引擎 200 顆 eq_sha ＝ seeds.csv（逐位元）；營量 v1 同
 ② 自算 200 顆平均日報酬配對差 ⇒ ＝ pairdiff.npz；CR0 CI ＝ cells.csv；「對營量 v1」讀法重判
 ③ 自 seeds.csv 重算各格中位、標籤、退化、挑格、件標籤
 ④ 甲挑中格路徑必報（主）：每筆平均出／進、有暫出比例、結束仍在外比例 ＝ summary
 ⑤ 假訊號 p、挪起點中位 ＝ summary
"""
from __future__ import annotations
import argparse, hashlib, json, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import research11 as R
from backtest import rerun17 as RR

OUT = "backtest/resultsYLexit"
COST = R.COST


def h16(eq):
    return hashlib.sha256(np.asarray(eq, float).tobytes()).hexdigest()[:16]


def bars(cache, s, mk, cal):
    if s not in cache:
        b = R.load_bars(s, mk.get(s, "twse"), cal)
        cache[s] = None if b is None else (b["idx"], b["o"], b["c"], b["next_bad"], b["df"]["open"].to_numpy(float), b["df"]["close"].to_numpy(float))
    return cache[s]


def exitH(sig, H, cache, mk, cal, EVD):
    n0 = len(cal); X = []; G = []
    for s, k in zip(sig["sid"], sig["k"].astype(int)):
        B = bars(cache, s, mk, cal)
        if B is None:
            X.append(-1); G.append(np.nan); continue
        idx, o, c, nb, of_, cf_ = B; n = len(idx); nbk = nb[max(0, k - 20)]; ex = k + H
        if ex < n and ex < nbk:
            x, g = int(idx[ex]), c[ex] / o[k + 1] - 1
        elif ex >= n and nbk > n - 1 and int(idx[n - 1]) == n0 - 1:
            x, g = n0, float(c[n - 1] / o[k + 1] - 1.0)
        else:
            X.append(-1); G.append(np.nan); continue
        ent = int(idx[k + 1])
        for pe, pL in EVD.get(s, []):
            if ent <= pL and x >= pe:
                x, g = pL, cf_[pL] / of_[ent] - 1.0
        X.append(x); G.append(g)
    out = sig.copy(); out[f"xpos_H{H}"] = np.array(X, np.int64); out[f"g_H{H}"] = np.array(G)
    return out[out[f"xpos_H{H}"] >= 0]


def jia(sig, H, b, cl, op, NP, n0, cache, mk, cal):
    """自寫合成：回 (sig 合成鍵表, closes 附加, opens 附加, held_map, 路徑統計)。"""
    rows = []; ac = {}; ao = {}; hm = {}; st = []
    for s, k, e, x, g0, rv in zip(sig["sid"], sig["k"].astype(int), sig["entry_pos"].astype(int), sig[f"xpos_H{H}"].astype(int), sig[f"g_H{H}"].astype(float), sig["relvol"]):
        B = bars(cache, s, mk, cal)
        if B is None or x < 0:
            rows.append((s, s, e, x, g0, rv)); st.append((e, 0, 0, False)); continue
        idx = B[0]; ke = k + 1
        last = int(np.searchsorted(idx, (NP - 2) if x >= n0 else x, side="right") - 1)
        P0 = float(op[s][e]); inm = True; ve = 1.0; pe = P0; vf = 0.0; todo = None; nout = nin = 0; val = {}
        for j in range(ke, last + 1):
            t = int(idx[j]); ot = float(op[s][t]); ct = float(cl[s][t])
            if todo == "s" and inm and np.isfinite(ot) and ot > 0:
                vf = ve * ot / pe; inm = False; nout += 1
            elif todo == "b" and not inm and np.isfinite(ot) and ot > 0:
                ve = vf * (1 - COST); pe = ot; inm = True; nin += 1
            todo = None
            val[t] = ve * ct / pe if inm else vf
            if j < last:
                if inm and ct < P0 * (1 - b):
                    todo = "s"
                elif not inm and ct >= P0:
                    todo = "b"
        st.append((e, nout, nin, not inm))
        if nout == 0:
            rows.append((s, s, e, x, g0, rv)); continue
        arr = np.array(cl[s], dtype=float, copy=True); cur = None
        for t in range(e, NP):
            cur = val.get(t, cur)
            if cur is not None:
                arr[t] = P0 * cur
        key = f"{s}#{e}"; ac[key] = arr; ao[key] = op[s]; hm[key] = s
        rows.append((key, s, e, x, arr[min(x, NP - 1)] / P0 - 1, rv))
    T = pd.DataFrame(rows, columns=["sid", "u", "entry_pos", f"xpos_H{H}", f"g_H{H}", "relvol"])
    for u in set(T["u"]):
        hm.setdefault(u, u)
    return T, ac, ao, hm, st


def yi(sig, K, C, cache, mk, cal):
    n0 = len(cal); S2 = sig.copy(); X = S2["xpos_H60"].to_numpy(np.int64).copy(); G = S2["g_H60"].to_numpy(float).copy()
    for i, (s, k, x0) in enumerate(zip(S2["sid"], S2["k"].astype(int), X)):
        if x0 < 0:
            continue
        B = bars(cache, s, mk, cal)
        if B is None:
            continue
        idx, o, c, nb, _, _ = B; n = len(idx); nbk = nb[max(0, k - 20)]; ke = k + 1; kk = ke + K - 1; kc = ke + C - 1; ep = o[ke]
        if kk > n - 1 or kk >= nbk:
            continue
        lim = min(kc, n - 1, nbk - 1); hit = None
        for j in range(kk + 1, lim + 1):
            if c[j] < c[kk]:
                hit = j; break
        if hit is not None:
            if hit + 1 <= lim:
                X[i], G[i] = int(idx[hit + 1]), o[hit + 1] / ep - 1.0
            else:
                X[i], G[i] = int(idx[hit]), c[hit] / ep - 1.0
        elif lim == kc:
            X[i], G[i] = int(idx[kc]), c[kc] / ep - 1.0
        elif lim == nbk - 1 and nbk <= min(kc, n - 1):
            X[i], G[i] = int(idx[lim]), c[lim] / ep - 1.0
        elif int(idx[n - 1]) == n0 - 1:
            X[i], G[i] = n0, c[n - 1] / ep - 1.0
        else:
            X[i], G[i] = int(idx[n - 1]), c[n - 1] / ep - 1.0
    S2["xpos_H60"] = X; S2["g_H60"] = G
    return S2


def run(sig, rule, seed, cl, op, NP, SF, hm=None):
    return np.asarray(R.simulate_mtm(sig, rule, 20, np.random.default_rng(seed), cl, op, NP, return_equity=True, log=[], d_max=None, pick="relvol",
                                     queue_days=0, stop_force=SF, held_map=hm)["equity"], float)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--seeds", type=int, default=200); a = ap.parse_args()
    RES = {}
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    SE = pd.read_csv(os.path.join(OUT, "seeds.csv.gz"), dtype={"eq_sha": str}, float_precision="round_trip", low_memory=False)
    PT = pd.read_csv(os.path.join(OUT, "cells.csv"), float_precision="round_trip")
    PD = np.load(os.path.join(OUT, "pairdiff.npz"))
    J = S["判定"]; pj, py = J["甲"]["挑中"], J["乙"]["挑中"]
    b_ = int(pj.split("_b")[1].split("_")[0]) / 100; Hj = int(pj.split("_H")[1]); Ky = int(py.split("_k")[1].split("_")[0]); Cy = int(py.split("_C")[1])
    bad1 = []; n1 = 0; bad2 = []; stat4 = None
    for wk in ("主", "早年"):
        RR.use_snapshot()
        if wk == "主":
            from backtest import researchT1fix as T1
            ctx = T1.build_ctx(True); cal = ctx["cal"]; cl, op, NP = ctx["closes"], ctx["opens"], ctx["ncal"]; mk = ctx["mk"]; w0, w1 = ctx["w0"], ctx["w1"]
            base = ctx["sig13"]; EVD = {}
            segs = {sg: (int(cal.searchsorted(pd.Timestamp(x))), int(cal.searchsorted(pd.Timestamp(y)))) for sg, (x, y) in (("探索", ("2017-03-02", "2021-12-30")), ("確認", ("2022-01-03", "2026-08-24")))}
        else:
            from backtest import researchV as V
            from backtest import researchYear1M as Y
            from backtest import early_data as E
            V.body_setup("main", lambda x: None)
            cal = V._B["cal"]; w0, w1 = V._B["w0"], V._B["w1"]; cl, op, NP = Y._G["closes"], Y._G["opens"], Y._G["NP"]; mk = Y._G["uni"]
            base = Y.sig_of(13, "mtm", w0, w1)
            EV = pd.read_csv(os.path.join(E.snap_dir(E.BODY_SHA), "reduce_events.csv"), dtype=str)
            pos = {d.strftime("%Y-%m-%d"): j for j, d in enumerate(cal)}; EVD = {}
            for s_, e_, L_ in zip(EV["stock_id"], EV["e"], EV["L"]):
                if e_ in pos and L_ in pos:
                    EVD.setdefault(s_, []).append((pos[e_], pos[L_]))
            segs = {"早年": (w0, w1)}
        SF = {}
        for s in sorted(cl):
            st = D.load_stock(s, mk.get(s, "twse"), cal)
            if st is None:
                continue
            v = np.flatnonzero(np.isfinite(st.df["close"].to_numpy(float)))
            if len(v) and v[-1] < w1:
                SF[s] = int(v[-1])
        cache = {}
        sj = base if Hj == 60 else exitH(base, Hj, cache, mk, cal, EVD)
        TJ, ac, ao, hm, st = jia(sj, Hj, b_, cl, op, NP, len(cal), cache, mk, cal)
        clJ = {**cl, **ac}; opJ = {**op, **ao}; SFJ = {**SF, **{k_: SF[u] for k_, u in hm.items() if u in SF and k_ != u}}
        TY = yi(base, Ky, Cy, cache, mk, cal)
        if wk == "主":
            m_ = [(e, o_, i_, f_) for e, o_, i_, f_ in st if w0 <= e <= w1]
            stat4 = {"每筆平均出": float(np.mean([x[1] for x in m_])), "每筆平均進": float(np.mean([x[2] for x in m_])), "有暫出的筆比例": float(np.mean([x[1] > 0 for x in m_])),
                     "暫出後沒再站回（結束時仍在外）比例（有暫出者）": float(np.mean([x[3] for x in m_ if x[1] > 0]))}
        acc = {"甲": None, "乙": None}
        for r in range(a.seeds):
            eb = run(base, "H60", 7000 + r, cl, op, NP, SF)
            ej = run(TJ, f"H{Hj}", 7000 + r, clJ, opJ, NP, SFJ, hm)
            ey = run(TY, "H60", 7000 + r, cl, op, NP, SF)
            for nm, eq in (("營量v1", eb), (pj, ej), (py, ey)):
                ref = SE[(SE["世界"] == wk) & (SE["格"] == nm) & (SE["r"] == r)]["eq_sha"].iloc[0]
                n1 += 1
                if h16(eq) != ref:
                    bad1.append((wk, nm, r))
            for fam, eq in (("甲", ej), ("乙", ey)):
                d = {sg: (eq[x + 1:y + 1] / eq[x:y] - 1.0) - (eb[x + 1:y + 1] / eb[x:y] - 1.0) for sg, (x, y) in segs.items()}
                acc[fam] = d if acc[fam] is None else {sg: acc[fam][sg] + d[sg] for sg in d}
        for fam, nm in (("甲", pj), ("乙", py)):
            for sg, (x, y) in segs.items():
                mine = acc[fam][sg] / a.seeds; ref = PD[f"{nm}|{sg}"]
                mon = np.array([str(d)[:7] for d in cal[x + 1:y + 1]])
                mu = mine.mean(); s_ = pd.Series(mine - mu).groupby(mon).sum().to_numpy(); se = np.sqrt((s_ ** 2).sum()) / len(mine)
                row = PT[PT["格"] == nm].iloc[0]
                if np.max(np.abs(mine - ref)) > 1e-12 or abs(mu * 245 - row[f"{sg}_配對差年化"]) > 1e-12 or abs((mu - 1.96 * se) * 245 - row[f"{sg}_配對差lo"]) > 1e-12:
                    bad2.append((wk, nm, sg))
        print(wk, "done", len(bad1), bad2, flush=True)
    RES["① 挑中格與營量 v1 自寫 ⇒ 200 顆 eq_sha（主、早年）"] = {"比對": n1, "不符": bad1[:10], "過": not bad1}
    RES["② 配對差序列、CR0 CI"] = {"不符": bad2, "過": not bad2}
    # ③
    Z = S["0050"]; bad3 = []
    for r in PT.to_dict("records"):
        for sg, wk in (("探索", "主"), ("確認", "主"), ("早年", "早年")):
            g = SE[(SE["世界"] == wk) & (SE["格"] == r["格"])]
            c, m = g[f"{sg}_年化"].median(), g[f"{sg}_回落"].median()
            lab = "合格" if (c > Z[sg]["cagr"] and c / abs(m) >= Z[sg]["cagr"] / abs(Z[sg]["mdd"])) else ("另列" if c > Z[sg]["cagr"] else "不合格")
            if abs(c - r[f"{sg}_年化"]) > 1e-15 or abs(m - r[f"{sg}_回落"]) > 1e-15 or lab != r[f"{sg}_標籤"]:
                bad3.append((r["格"], sg))
    picks = {}
    for fam in ("甲", "乙"):
        c = PT[PT["格"].str.startswith(f"營量_{fam}")].copy()
        c = c[~((c["探索_持股"] < 10) | ((fam == "乙") & (c["探索_現金"] > 0.30)))]
        q = c[c["探索_標籤"] == "合格"] if (c["探索_標籤"] == "合格").any() else c
        picks[fam] = q.sort_values(["探索_比值", "探索_年化"], ascending=[False, False]).iloc[0]["格"]
        rr = PT[PT["格"] == picks[fam]].iloc[0]; order = {"不合格": 0, "另列": 1, "合格": 2}
        if min((rr["確認_標籤"], rr["早年_標籤"]), key=lambda z: order[z]) != J[fam]["件標籤"]:
            bad3.append((fam, "件標籤"))
    RES["③ 中位、標籤、退化、挑格、件標籤"] = {"不符": bad3, "自挑": picks, "過": not bad3 and picks["甲"] == pj and picks["乙"] == py}
    # ④
    ref4 = S["路徑必報"][f"主|{pj}"]
    d4 = max(abs(stat4[k] - ref4[k]) for k in stat4)
    RES["④ 甲挑中格路徑必報（主）"] = {"最大差": d4, "過": d4 < 1e-12}
    # ⑤
    FK = pd.read_csv(os.path.join(OUT, "fake.csv.gz"), float_precision="round_trip"); SH = pd.read_csv(os.path.join(OUT, "shift.csv.gz"), float_precision="round_trip")
    bad5 = []
    for fam, pk in (("甲", pj), ("乙", py)):
        f_ = FK[FK["格"] == pk]
        for sg, v in J[fam]["假訊號"].items():
            if abs(float(np.mean(f_[f"{sg}_年化"].dropna() >= J[fam][f"{sg}_年化"])) - v["p（假年化 ≥ 本格年化中位）"]) > 1e-12:
                bad5.append((fam, sg))
        for key, v in J[fam]["挪起點（本格年化、營量年化、本格回落、營量回落 中位）"].items():
            sg, sh = key.split("+"); g = SH[(SH["段"] == sg) & (SH["挪"] == int(sh))]
            if abs(g[g["格"] == pk]["年化"].median() - v[0]) > 1e-15 or abs(g[g["格"] == "營量v1"]["年化"].median() - v[1]) > 1e-15:
                bad5.append((fam, key))
    RES["⑤ 假訊號 p、挪起點"] = {"不符": bad5, "過": not bad5}
    RES["全部過"] = all(v["過"] for v in RES.values() if isinstance(v, dict))
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(RES, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
