# -*- coding: utf-8 -*-
"""researchSigMA 的獨立查核（⛔ 不 import researchSigMA、researchSig）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchSigMA_check.py [--n 80]

① 均線出場日：抽 n 檔，逐根迴圈（math.fsum 均線）重算「由上往下穿越」與「收盤 ＜ MA」日 ⇒ 對 ma_cache.pkl
② 確認段挑中格的列：自己從 resultsSig/sig_cache.pkl ＋ 自己的穿越日組（聯集、段內、當月資格、同日出場不進、第一個出場日）⇒ 對 confirm_rows_E?.csv.gz
③ 帳：confirm_audit5.csv.gz 前 5 顆 ⇒ 自己逐日重建淨值 ⇒ 年化、回落 對引擎；持股 ≤ 10、不重複持有、買進都是列、賣出都在觸發日之後
④ 排除與挑選：從 cells.csv 自己算「觸發 ＜ 1 次／年 或 段尾未出場 ＞ 50%」⇒ 對 summary.json；在未排除格照登錄挑法重挑 ⇒ 對 summary.json；標籤重算
"""
from __future__ import annotations
import argparse, json, math, os, pickle, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchH2 as H2
from backtest import rerun17 as RR
D = H2.D
OUT = os.path.expanduser("~/tw-p17/backtest/resultsSigMA")
SIGP = os.path.expanduser("~/tw-p17/backtest/resultsSig/sig_cache.pkl")
PANEL = os.path.expanduser("~/tw-p17/backtest/resultsp9_engine/panel_ext.csv.gz")
E1 = ["W", "HS", "BOX", "CUP"]; E2 = ["TD", "RSI", "VS", "MOR", "ENG", "KDc", "MACDc"]
SEG = {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}


def loop_ma_days(c):
    b = [i for i in range(len(c)) if math.isfinite(c[i])]
    cross = {10: [], 20: [], 60: []}; below = {10: [], 20: [], 60: []}
    for n in (10, 20, 60):
        prev = None
        for j in range(len(b)):
            ma = math.fsum(c[b[k]] for k in range(j - n + 1, j + 1)) / n if j >= n - 1 else None
            if ma is not None:
                if c[b[j]] < ma:
                    below[n].append(b[j])
                if prev is not None and c[b[j - 1]] >= prev and c[b[j]] < ma:
                    cross[n].append(b[j])
            prev = ma
    return cross, below


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=80); a = ap.parse_args()
    errs = []; info = {}
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    M = pickle.load(open(os.path.join(OUT, "ma_cache.pkl"), "rb")); SIG, VAL = pickle.load(open(SIGP, "rb"))
    cal = D.load_calendar(); mon = np.array([str(x)[:7] for x in cal])
    from backtest import universe_gate as UG
    from backtest import p4_features as P4F
    U = UG.gate3(pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str)); mk = U.set_index("stock_id")["market"]
    # ① 均線出場日
    rng = np.random.default_rng(21); sids = sorted(M); pick = [sids[i] for i in rng.choice(len(sids), size=min(a.n, len(sids)), replace=False)]
    for sid in pick:
        c = D.load_stock(sid, mk.get(sid, "twse"), cal).df["close"].to_numpy(float)
        cr, bl = loop_ma_days(c)
        for n in (10, 20, 60):
            if cr[n] != M[sid][f"X:MA{n}"].tolist() or bl[n] != M[sid][f"X:MAs{n}"].tolist():
                errs.append(f"均線日 {sid} MA{n}")
    info["均線日_抽檢檔數"] = len(pick)
    # ② 確認段列
    p = P4F.read_panel(PANEL); p = p[p["eligible"].astype(bool) & p["stock_id"].isin(set(U["stock_id"]))]
    elig = p.groupby("stock_id")["measure_date"].apply(lambda s: set(str(x)[:7] for x in s)).to_dict()
    s0, s1 = (int(cal.searchsorted(pd.Timestamp(v))) for v in SEG["確認"])
    ch = S["探索段挑出場"]; CR = {}
    for E in ("E1", "E2"):
        if not ch.get(E):
            continue
        n = int(ch[E][2:]); out = []
        for sid, Sg in SIG.items():
            em = elig.get(sid)
            if not em or sid not in M:
                continue
            ent = sorted(set(int(x) for k in (E1 if E == "E1" else E2) for x in Sg.get("E:" + k, [])))
            Xd = [int(x) for x in M[sid][f"X:MA{n}"]]; Xs = set(Xd)
            for t in ent:
                if not (s0 <= t + 1 <= s1) or mon[t] not in em or t in Xs:
                    continue
                dX = next((d for d in Xd if d >= t + 1), -1)
                out.append((sid, t + 1, dX if 0 <= dX <= s1 else -1))
        mine = pd.DataFrame(out, columns=["sid", "entry_pos", "dX"])
        F = pd.read_csv(os.path.join(OUT, f"confirm_rows_{E}.csv.gz"), dtype={"sid": str}); CR[E] = F
        mm = mine.merge(F[["sid", "entry_pos", "dX"]], on=["sid", "entry_pos"], how="outer", suffixes=("", "_f"), indicator=True)
        if (mm["_merge"] != "both").any() or (mm["dX"] != mm["dX_f"]).any():
            errs.append(f"確認段列 {E}：缺 {int((mm['_merge'] != 'both').sum())}、dX 不同 {int((mm['dX'] != mm['dX_f']).sum())}")
        info[f"確認段列_{E}"] = int(len(mine))
    # ③ 帳
    A = pd.read_csv(os.path.join(OUT, "confirm_audit5.csv.gz"), dtype={"sid": str}, float_precision="round_trip")
    need = sorted(set(A["sid"]) - {"_metrics"})
    cz, oz = RR.load_prices(need, cal, mk, "branch")
    for (cell, r), g in A.groupby(["cell", "r"]):
        E = cell.split("|")[1]; F = CR[E]; rowset = set(zip(F["sid"], F["entry_pos"].astype(int)))
        dmap = {(s, int(e)): int(d) for s, e, d in zip(F["sid"], F["entry_pos"], F["dX"])}
        mt = g[g["sid"] == "_metrics"].iloc[0]; g = g[g["sid"] != "_metrics"]
        pos = {}; cash = 1.0; eq = np.ones(len(cal)); mh = 0; bad = 0
        byt = {t: gg for t, gg in g.groupby("t")}; first = int(g["t"].min())
        for t in range(first, s1 + 1):
            for x in (byt[t].itertuples() if t in byt else []):
                if x.side == "sell":
                    b = pos.pop(x.sid); cash += float(x.amt) - float(x.cost)
                    d = dmap.get((x.sid, b["tb"]), -1)
                    if t <= s1 and not (0 <= d < t):
                        bad += 1
            for x in (byt[t].itertuples() if t in byt else []):
                if x.side == "buy":
                    if x.sid in pos or (x.sid, t) not in rowset:
                        bad += 1
                    pos[x.sid] = {"amt": float(x.amt), "ep": float(x.px), "tb": t}; cash -= float(x.amt)
            mh = max(mh, len(pos))
            eq[t] = cash + sum(v["amt"] * float(cz[s][t]) / v["ep"] for s, v in pos.items())
        c_, m_, _ = RR.win_metrics(eq, first, s1 + 1, s0, s1)
        if abs(c_ - mt["amt"]) > 1e-9 or abs(m_ - mt["px"]) > 1e-9 or mh > 10 or bad:
            errs.append(f"帳 {cell} r{r}：{c_:.10f}／{m_:.10f} vs {mt['amt']:.10f}／{mt['px']:.10f}；最多持股 {mh}；違規 {bad}")
    info["帳_顆數"] = int(A.groupby(["cell", "r"]).ngroups)
    # ④ 排除與挑選
    C = pd.read_csv(os.path.join(OUT, "cells.csv"), float_precision="round_trip")
    for E in ("E1", "E2"):
        ok = []
        for n in (10, 20, 60):
            q = C[(C["段"] == "探索") & (C["E"] == E) & (C["出場"] == f"MA{n}")].iloc[0]
            ex = bool(q["每檔出場觸發_次每年"] < 1.0 or q["段尾未出場比例"] > 0.5)
            if ex != S["退化排除"][f"{E}_MA{n}"]["排除"]:
                errs.append(f"排除 {E} MA{n}")
            if not ex:
                ok.append(q)
        if ok:
            c50 = S["0050同段"]["探索"]["cagr"]; r50 = c50 / abs(S["0050同段"]["探索"]["mdd"])
            df = pd.DataFrame(ok); df["_r"] = df["cagr_med"] / df["mdd_med"].abs()
            pool = df[(df["cagr_med"] > c50) & (df["_r"] >= r50)]
            pool = pool if len(pool) else df
            best = pool.sort_values(["_r", "cagr_med"], ascending=[False, False]).iloc[0]["出場"]
            if best != ch.get(E):
                errs.append(f"挑選 {E}：自己 {best} vs {ch.get(E)}")
        elif ch.get(E):
            errs.append(f"挑選 {E}：全排除但檔有挑")
    for seg in ("探索", "確認"):
        c50 = S["0050同段"][seg]["cagr"]; r50 = c50 / abs(S["0050同段"][seg]["mdd"])
        for q in C[C["段"] == seg].itertuples():
            lab = "合格" if (q.cagr_med > c50 and q.cagr_med / abs(q.mdd_med) >= r50) else ("另列" if q.cagr_med > c50 else "不合格")
            if lab != q.label:
                errs.append(f"標籤 {seg} {q.E} {q.出場}")
    info["錯誤數"] = len(errs)
    print(json.dumps(info, ensure_ascii=False))
    for e_ in errs[:25]:
        print("  ⛔", e_)
    json.dump({"info": info, "errors": errs[:300]}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("查核：" + ("全過" if not errs else f"⛔ {len(errs)} 項不過"))


if __name__ == "__main__":
    main()
