# -*- coding: utf-8 -*-
"""researchAddOnExit5 獨立查核（回測線計算子代理，2026-10-13）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchAddOnExit5_check [--procs 3]

獨立寫法（⛔ 不 import researchAddOnExit5、researchExit5、researchAddOn）：
 K0 degeneracy.json 修改時間早於 seeds.csv.gz、AddOnExit5.json
 K1 逐筆抽樣（exits.csv.gz 唯一 加碼×格：每世界隨機 30 筆 ＋ 每個判定臂各隨機 5 筆已觸發；random_state 20261013）逐日迴圈從頭重算：
    有效 K 棒（research11.load_bars）、壞根／R1 母體／q99(h,d)／q2(d)／營收（researchExit5_check 的獨立實作 Pop、early_extra、stock_bad、revenue、rev_list）、
    ATR（決策日 t 往前 20 根 TR 迴圈）、MA5、加碼後最高收盤 M ⇒ 各臂 觸發、訊號日 d、賣出日 X、賣出比例 w、賣價 ⇒ 與 exits.csv.gz 比（0 不同才過）
 K2 組合：由 exits.csv.gz ＋ paths.csv.gz 自組每路徑每臂加碼部位（提早部分 ＋ 其餘照臂 S），逐日迴圈記帳（researchAddOn_truetop_check.nav3，讀法 A／B／C）、
    RR.win_metrics ⇒ 與 seeds.csv.gz 全部列（原、S、五法、描述臂）比，差 ≤ 1e−9
 K3 主表與判定：由 seeds.csv.gz 自算中位、比值、變好（vs 原／S／T）⇒ 與 AddOnExit5_main.csv、AddOnExit5.json 判定比
"""
from __future__ import annotations

import argparse
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
from backtest import researchExit5_check as XC              # noqa: E402  （獨立查核用的母體、壞根、營收）
from backtest import researchAddOn_truetop_check as TC      # noqa: E402  （獨立查核用的逐日記帳 nav3）

OUT = "backtest/resultsAddOn/exit5"
AWORK = os.path.expanduser("~/addonwork")
TOL = 1e-9
JUD = ["E1a", "E1b", "E2", "E3", "E4", "E5"]
EXA = JUD + ["D1_5", "D1_10", "D4", "D5"]
HALF = {"E4", "E5", "D4", "D5"}
SEGN = {"主": ["探索", "確認", "主窗"], "早年": ["早年"]}
PICK = {"營量": "A2", "營飆": "A1"}
_G: dict = {}


# ═════════ K1 ═════════
def one(r, W, LB, bad, P, REV, n0):
    sid = r["sid"]; ta = int(r["ta"]); t = int(r["t"]); ep = float(r["加碼價"])
    c = np.asarray(W["closes"][sid], float); o = np.asarray(W["opens"][sid], float)
    idx = [int(x) for x in LB["idx"] if x < n0]; isb = np.zeros(n0, bool); isb[idx] = True
    sd, pb = int(r["S_出場日"]), int(r["S_價根"])
    cap = pb if (sd >= 0 and pb < n0) else n0 - 1
    # ATR：決策日 t 那根往前 20 根
    li = list(LB["idx"]); k = li.index(t) if t in li else -1
    if k >= 20:
        atr = sum(max(LB["h"][j], LB["c"][j - 1]) - min(LB["l"][j], LB["c"][j - 1]) for j in range(k - 19, k + 1)) / 20.0
    else:
        atr = np.nan
    ma5 = {}
    for q_, d in enumerate(idx):
        if q_ >= 4:
            ma5[d] = sum(c[idx[q_ - j]] for j in range(5)) / 5.0
    M = {}; m_ = -np.inf; nb = {}; cnt = 0
    for d in range(ta, n0):
        if isb[d]:
            m_ = max(m_, c[d]); cnt += 1
        M[d] = m_; nb[d] = cnt
    kb = None
    for p in range(ta + 1, len(bad)):
        if bad[p]:
            kb = p; break

    def c4(d):
        if d < ta + 9 or not isb[d] or (kb is not None and kb <= d) or d >= P.n:
            return False
        q = P.q(d - ta + 1, d, 99.0)
        return bool(np.isfinite(q) and c[d] / ep - 1.0 >= q)

    def c5(d):
        if d < ta + 1 or not isb[d] or bad[d] or d >= P.n:
            return False
        q = P.q(1, d, 2.0); rr = c[d] / c[d - 1] - 1.0
        return bool(np.isfinite(q) and np.isfinite(rr) and rr <= q and rr < 0)
    cond = {"E1a": lambda d: isb[d] and np.isfinite(atr) and c[d] <= M[d] - 2 * atr,
            "E1b": lambda d: isb[d] and np.isfinite(atr) and c[d] <= M[d] - 4 * atr,
            "E2": lambda d: isb[d] and nb[d] >= 6 and d in ma5 and c[d] < ma5[d],
            "E4": c4, "E5": c5,
            "D1_5": lambda d: isb[d] and c[d] <= 0.95 * M[d], "D1_10": lambda d: isb[d] and c[d] <= 0.90 * M[d],
            "D4": lambda d: isb[d] and c[d] / ep - 1.0 >= 1.0,
            "D5": lambda d: d >= ta + 1 and isb[d] and not bad[d] and c[d] / c[d - 1] - 1.0 < -0.05}
    res = {}
    for v in EXA:
        d = None
        if v == "E3":
            for A, yoy, hi in REV:
                if ta <= A <= cap - 1 and np.isfinite(yoy) and yoy <= 0:
                    d = A; break
        else:
            for dd in range(ta, min(cap - 1, n0 - 1) + 1):
                if cond[v](dd):
                    d = dd; break
        X = None
        if d is not None:
            x = d + 1
            while x < n0 and not (isb[x] and np.isfinite(o[x]) and o[x] > 0):
                x += 1
            X = x if (x < n0 and x <= cap) else None
        res[v] = {"trig": int(X is not None), "d": -1 if d is None else d, "X": -1 if X is None else X,
                  "w": (0.5 if v in HALF else 1.0) if X is not None else 0.0, "px1": float(o[X]) if X is not None else np.nan}
    return res, atr


def k1(log):
    ER = pd.read_csv(os.path.join(OUT, "exits.csv.gz"), dtype={"sid": str}, float_precision="round_trip")
    out = {}; ex = []; X_ = None
    for wn in ("主", "早年"):
        W = pickle.load(open(os.path.join(AWORK, f"world_{wn}.pkl"), "rb")); cal = W["cal"]; n0 = len(cal); NP = W["NP"]
        P = XC.Pop("main" if wn == "主" else "early", X_)
        if P.X is None:
            P.set_X(cal); X_ = P.X
        EX = XC.early_extra(W) if wn == "早年" else None
        D.DATA = W["data"]
        PER, RV = XC.revenue(W["data"]); dates = list(cal)
        T = ER[ER["世界"] == wn]
        smp = [T.sample(30, random_state=20261013)]
        for v in JUD:
            t_ = T[T[f"{v}_trig"] == 1]
            if len(t_):
                smp.append(t_.sample(min(5, len(t_)), random_state=20261013))
        S = pd.concat(smp).drop_duplicates(["策略", "sid", "tb", "格"])
        nd = 0; nchk = 0; LBc = {}; atr_d = 0.0
        for _, r in S.iterrows():
            sid = r["sid"]
            if sid not in LBc:
                LBc[sid] = R.load_bars(sid, W["uni"].get(sid, "twse"), cal)
            bad = XC.stock_bad(sid, W, P, EX, NP)
            REV = XC.rev_list(sid, PER, RV, dates)
            res, atr = one(r, W, LBc[sid], bad, P, REV, n0)
            if np.isfinite(atr) or np.isfinite(r["ATR"]):
                atr_d = max(atr_d, abs(atr - float(r["ATR"])) / max(abs(atr), 1e-12))
            for v, z in res.items():
                nchk += 1; why = []
                for k in ("trig", "d", "X"):
                    if int(z[k]) != int(r[f"{v}_{k}"]):
                        why.append(f"{k} {z[k]}≠{r[f'{v}_{k}']}")
                if abs(z["w"] - float(r[f"{v}_w"])) > 0:
                    why.append(f"w {z['w']}≠{r[f'{v}_w']}")
                a_, b_ = z["px1"], float(r[f"{v}_px1"])
                if not ((np.isnan(a_) and np.isnan(b_)) or abs(a_ - b_) <= TOL * max(1.0, abs(b_))):
                    why.append(f"px1 {a_}≠{b_}")
                if why:
                    nd += 1; ex.append(f"{wn}·{r['策略']}·{r['格']} {sid} tb{r['tb']} {v}: {'; '.join(why)}")
        out[wn] = {"抽樣筆": int(len(S)), "比對（筆×臂）": nchk, "不同": nd, "ATR 相對差最大": atr_d}
        log(f"[K1 {wn}] {out[wn]}")
    out["例"] = ex[:20]
    return out


# ═════════ K2 ═════════
def k2_job(key):
    wn, sn, r = key
    W = _G["W"][wn]; E = _G["ENG"][key]; eq = np.asarray(E["eq"], float); first, end = E["first"], E["end"]
    EX = _G["EXI"][wn]; PRk = _G["PR"].get((wn, sn, r), [])
    cl_of = lambda s: W["closes"][s]
    rows = []
    for c in ("A1", "A2"):
        lst = [z for z in PRk if z[0] == c]
        for sg in SEGN[wn]:
            x, y = W["segp"][sg]; a = max(x, first); yy = min(y, end - 1)
            c0, m0, _ = RR.win_metrics(eq, first, end, x, y)
            row = {"世界": wn, "策略": sn, "r": r, "格": c, "段": sg, "原_年化": c0, "原_回落": m0}
            for arm in ["S"] + EXA:
                P = []
                for _, sid, tb, amt in lst:
                    e = EX[(sn, sid, tb, c)]
                    ta = int(e["ta"])
                    if not (a < ta <= yy):
                        continue
                    sS = int(e["S_出場日"]); sS = None if (sS < 0 or sS > yy) else sS
                    if arm == "S" or int(e[f"{arm}_trig"]) == 0:
                        P.append((ta, amt, float(e["加碼價"]), sid, sS, float(e["S_價"])))
                    else:
                        w = float(e[f"{arm}_w"]); X = int(e[f"{arm}_X"])
                        P.append((ta, amt * w, float(e["加碼價"]), sid, None if X > yy else X, float(e[f"{arm}_px1"])))
                        if w < 1.0:
                            P.append((ta, amt * (1 - w), float(e["加碼價"]), sid, sS, float(e["S_價"])))
                navs = TC.nav3(eq, a, yy, P, cl_of)
                for rd in ("A", "B", "C"):
                    full = eq.copy(); full[a:a + len(navs[rd])] = navs[rd]
                    cc, mm, _ = RR.win_metrics(full, first, end, x, y)
                    row[f"{arm}_{rd}_年化"] = cc; row[f"{arm}_{rd}_回落"] = mm
            rows.append(row)
    return rows


def k2(procs, log):
    ER = pd.read_csv(os.path.join(OUT, "exits.csv.gz"), dtype={"sid": str}, float_precision="round_trip")
    PR = pd.read_csv(os.path.join(OUT, "paths.csv.gz"), dtype={"sid": str}, float_precision="round_trip")
    SE = pd.read_csv(os.path.join(OUT, "seeds.csv.gz"), float_precision="round_trip").set_index(["世界", "策略", "r", "格", "段"])
    _G["W"] = {wn: pickle.load(open(os.path.join(AWORK, f"world_{wn}.pkl"), "rb")) for wn in ("主", "早年")}
    _G["ENG"] = pickle.load(open(os.path.join(AWORK, "engine_200.pkl"), "rb"))
    _G["EXI"] = {wn: {(z["策略"], z["sid"], int(z["tb"]), z["格"]): z for z in ER[ER["世界"] == wn].to_dict("records")} for wn in ("主", "早年")}
    _G["PR"] = {}
    for z in PR.itertuples(index=False):
        _G["PR"].setdefault((z.世界, z.策略, int(z.r)), []).append((z.格, z.sid, int(z.tb), float(z.金額)))
    keys = sorted(_G["ENG"])
    with Pool(procs) as pool:
        res = pool.map(k2_job, keys, chunksize=2)
    md = 0.0; n = 0; nbad = 0
    for rows in res:
        for row in rows:
            ref = SE.loc[(row["世界"], row["策略"], row["r"], row["格"], row["段"])]
            for k, v in row.items():
                if k.endswith("_年化") or k.endswith("_回落"):
                    dd = abs(v - float(ref[k])); md = max(md, dd); n += 1; nbad += int(dd > TOL)
    out = {"路徑": len(keys), "比對值": n, "差＞1e−9": nbad, "最大差": md}
    log(f"[K2] {out}")
    return out


# ═════════ K3 ═════════
def k3(log):
    SE = pd.read_csv(os.path.join(OUT, "seeds.csv.gz"), float_precision="round_trip")
    MT = pd.read_csv(os.path.join(OUT, "AddOnExit5_main.csv"), float_precision="round_trip")
    S = json.load(open(os.path.join(OUT, "AddOnExit5.json"), encoding="utf-8"))
    DG = json.load(open(os.path.join(OUT, "degeneracy.json"), encoding="utf-8"))
    rat = lambda c, m: c / abs(m)
    bt = lambda ca, ma, co, mo: bool(ca > co and rat(ca, ma) >= rat(co, mo))
    MED = {}
    for (wn, sn, c, sg), g in SE.groupby(["世界", "策略", "格", "段"]):
        MED[(wn, sn, c, sg, "原", "-")] = (float(np.median(g["原_年化"])), float(np.median(g["原_回落"])))
        for rd in ("A", "B", "C"):
            for arm in ["S", "T"] + EXA:
                if f"{arm}_{rd}_年化" in g and g[f"{arm}_{rd}_年化"].notna().all():
                    MED[(wn, sn, c, sg, arm, rd)] = (float(np.median(g[f"{arm}_{rd}_年化"])), float(np.median(g[f"{arm}_{rd}_回落"])))
    nd = 0; n = 0; ex = []
    for r in MT.itertuples(index=False):
        n += 1
        if r.臂 == "原":
            ca, ma = MED[(r.世界, r.策略, r.格, r.段, "原", "-")]
            bad = abs(ca - r.年化) > TOL or abs(ma - r.回落) > TOL
        else:
            ca, ma = MED[(r.世界, r.策略, r.格, r.段, r.臂, r.讀法)]; co, mo = MED[(r.世界, r.策略, r.格, r.段, "原", "-")]
            bad = abs(ca - r.年化) > TOL or abs(ma - r.回落) > TOL or bt(ca, ma, co, mo) != bool(r.變好vs原)
            if r.臂 != "S":
                sa, sm = MED[(r.世界, r.策略, r.格, r.段, "S", r.讀法)]
                bad = bad or bt(ca, ma, sa, sm) != bool(r.變好vsS)
            if r.臂 in EXA and r.世界 == "主":
                ta_, tm = MED[(r.世界, r.策略, r.格, r.段, "T", r.讀法)]
                bad = bad or bt(ca, ma, ta_, tm) != bool(r.變好vsT)
        if bad:
            nd += 1; ex.append(f"{r.世界}·{r.策略}·{r.格}·{r.段}·{r.讀法}·{r.臂}")
    vd = 0
    for sn in ("營量", "營飆"):
        for c in ("A1", "A2"):
            for rd in ("A", "B"):
                for mth, cells in {"法1": ["E1a", "E1b"], "法2": ["E2"], "法3": ["E3"], "法4": ["E4"], "法5": ["E5"]}.items():
                    nde = [v for v in cells if not DG["格"][f"{sn}·{c}·{v}"]["退化"]]
                    pool_ = nde if nde else cells
                    pk = sorted(pool_, key=lambda v: (-rat(*MED[("主", sn, c, "探索", v, rd)]), -MED[("主", sn, c, "探索", v, rd)][0], cells.index(v)))[0]
                    dg = DG["格"][f"{sn}·{c}·{pk}"]; V = S["判定"][f"{sn}·{c}·{rd}·{mth}"]
                    for nm, ref in (("原", None), ("S", "S"), ("T", "T")):
                        ok = {}
                        for sg in ("探索", "確認"):
                            ca, ma = MED[("主", sn, c, sg, pk, rd)]
                            co, mo = MED[("主", sn, c, sg, "原", "-")] if ref is None else MED[("主", sn, c, sg, ref, rd)]
                            ok[sg] = bt(ca, ma, co, mo)
                        con = ("退化、不判" if dg["退化"] else ("確認段樣本不足、不判" if dg["確認段樣本不足（繼承）"] and ok["探索"] else
                               ("變好（事後重切、最多暫定；N 待裁定）" if ok["探索"] and ok["確認"] else ("沒有變好（探索段就沒變好）" if not ok["探索"] else "沒有變好（確認段沒變好）"))))
                        if V["臂"] != pk or V[f"vs{nm} 結論"] != con:
                            vd += 1; ex.append(f"判定 {sn}·{c}·{rd}·{mth} vs{nm}: {V['臂']}/{V[f'vs{nm} 結論']} vs {pk}/{con}")
    out = {"主表列": n, "主表不同": nd, "判定不同": vd, "例": ex[:10]}
    log(f"[K3] {out}")
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); a = ap.parse_args()
    T0 = time.time()
    log = lambda m: print(f"[{time.time() - T0:6.0f}s] {m}", flush=True)
    res = {"時間": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M") + "（台北）"}
    dg = os.path.getmtime(os.path.join(OUT, "degeneracy.json"))
    res["K0 degeneracy.json 早於 seeds.csv.gz、AddOnExit5.json"] = bool(dg < os.path.getmtime(os.path.join(OUT, "seeds.csv.gz")) and dg < os.path.getmtime(os.path.join(OUT, "AddOnExit5.json")))
    res["K3"] = k3(log)
    res["K1"] = k1(log)
    res["K2"] = k2(a.procs, log)
    ok = (res["K0 degeneracy.json 早於 seeds.csv.gz、AddOnExit5.json"] and res["K3"]["主表不同"] == 0 and res["K3"]["判定不同"] == 0
          and all(v["不同"] == 0 for k, v in res["K1"].items() if k != "例") and res["K2"]["差＞1e−9"] == 0)
    res["通過"] = bool(ok); res["耗時秒"] = round(time.time() - T0)
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[查核] {json.dumps(res, ensure_ascii=False, default=str)[:3000]}")


if __name__ == "__main__":
    main()
