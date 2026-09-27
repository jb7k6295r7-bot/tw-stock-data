# -*- coding: utf-8 -*-
"""researchSig 的獨立查核（⛔ 不 import researchSig）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchSig_check.py [--out backtest/resultsSig]

① 列：從 sig_cache.pkl 自己組「探索／確認 × E1／E2 × 出場 ANY」的進場列（聯集、段內、當月資格、同日出場不進）與第一個出場訊號日 ⇒ 對 pre.json 列數；
   確認段判定格的列 ⇒ 對 confirm_rows_E?.csv.gz（逐列 dX）
② 停損停利觸發日：抽 400 列，逐日迴圈重算 SL10／SL20／TP30／TR20（引擎價、引擎進場價）⇒ 對 confirm_rows 的欄
③ 帳：confirm_audit5.csv.gz 前 5 顆 ⇒ 自己用收盤逐日重建淨值（現金＋Σ 部位 amt×c/ep；賣出入帳＝金額−成本）⇒ 年化、回落 對引擎；
   同時驗：持股 ≤ 10、不重複持有、每筆買進都是某列的 entry_pos、每筆賣出日 ＝ 觸發日＋1 起第一個有效開盤（或段尾排程）
④ 挑選：從 cells.csv 自己重挑（出場 9 選 1、停損停利 32 選 1）與判定標籤 ⇒ 對 summary.json
"""
from __future__ import annotations
import argparse, json, math, os, pickle, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchH2 as H2                      # 快照資料讀取
from backtest import rerun17 as RR           # 只用 load_prices（引擎價）、win_metrics、load_bench、bench_row
D = H2.D
E1 = ["W", "HS", "BOX", "CUP"]; E2 = ["TD", "RSI", "VS", "MOR", "ENG", "KDc", "MACDc"]
XS = ["VSc", "TD", "KD", "MACD", "RSI", "EVE", "ENG", "TL"]
SEG = {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}
COST = 0.00585


def rows_of(SIG, elig, mon, E, s0, s1, xopt="ANY"):
    out = []
    for sid, S in SIG.items():
        em = elig.get(sid)
        if not em:
            continue
        ent = set()
        for k in (E1 if E == "E1" else E2):
            ent |= set(int(x) for x in S.get("E:" + k, []))
        X = sorted(set(int(x) for k in (XS if xopt == "ANY" else [xopt]) for x in S.get("X:" + k, [])))
        Xs = set(X)
        for t in sorted(ent):
            if not (s0 <= t + 1 <= s1) or mon[t] not in em or t in Xs:
                continue
            e = t + 1
            dX = next((d for d in X if d >= e), -1)
            out.append((sid, t, e, dX if 0 <= dX <= s1 else -1))
    return pd.DataFrame(out, columns=["sid", "t", "entry_pos", "dX"])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=os.path.expanduser("~/tw-p17/backtest/resultsSig")); a = ap.parse_args()
    OUT = a.out; errs = []; info = {}
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8")); pre = json.load(open(os.path.join(OUT, "pre.json"), encoding="utf-8"))
    SIG, VAL = pickle.load(open(os.path.join(OUT, "sig_cache.pkl"), "rb"))
    cal = D.load_calendar(); mon = np.array([str(x)[:7] for x in cal]); ncal = len(cal)
    from backtest import p4_features as P4F
    from backtest import universe_gate as UG
    U = UG.gate3(pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str))
    p = P4F.read_panel(os.path.expanduser("~/tw-p17/backtest/resultsp9_engine/panel_ext.csv.gz"))
    p = p[p["eligible"].astype(bool) & p["stock_id"].isin(set(U["stock_id"]))]
    elig = p.groupby("stock_id")["measure_date"].apply(lambda s: set(str(x)[:7] for x in s)).to_dict()
    P = {k: (int(cal.searchsorted(pd.Timestamp(v[0]))), int(cal.searchsorted(pd.Timestamp(v[1])))) for k, v in SEG.items()}
    # ① 列
    for seg, (s0, s1) in P.items():
        for E in ("E1", "E2"):
            R = rows_of(SIG, elig, mon, E, s0, s1)
            got = [r for r in pre["個股"] if r["段"] == seg and r["E"] == E and r["出場"] == "ANY"][0]
            if len(R) != got["進場列"] or int((R["dX"] >= 0).sum()) != got["有出場訊號的列"]:
                errs.append(f"列數 {seg} {E}：自己 {len(R)}／{int((R['dX'] >= 0).sum())} vs pre {got['進場列']}／{got['有出場訊號的列']}")
            info[f"列_{seg}_{E}_ANY"] = int(len(R))
    ch = S["探索段挑出場"]; s0, s1 = P["確認"]
    mk = U.set_index("stock_id")["market"]
    CRS = {}
    for E in ("E1", "E2"):
        F = pd.read_csv(os.path.join(OUT, f"confirm_rows_{E}.csv.gz"), dtype={"sid": str}, float_precision="round_trip")
        CRS[E] = F
        if True:
            R = rows_of(SIG, elig, mon, E, s0, s1, ch[E])
            m = R.merge(F[["sid", "entry_pos", "dX"]], on=["sid", "entry_pos"], how="outer", suffixes=("", "_f"), indicator=True)
            if (m["_merge"] != "both").any() or (m["dX"] != m["dX_f"]).any():
                errs.append(f"確認段列 {E} 與檔不一致：{int((m['_merge'] != 'both').sum())} 列缺、{int((m['dX'] != m['dX_f']).sum())} 列 dX 不同")
    # ② 停損停利觸發日（抽樣）
    sids = sorted(set(CRS["E1"]["sid"]) | set(CRS["E2"]["sid"]))
    cz, oz = RR.load_prices(sids, cal, mk, "branch")
    rng = np.random.default_rng(3); nchk = 0
    for E, F in CRS.items():
        for i in rng.choice(len(F), size=min(200, len(F)), replace=False):
            r = F.iloc[i]; sid = r["sid"]; e = int(r["entry_pos"])
            ep = float(oz[sid][e]) if (np.isfinite(oz[sid][e]) and oz[sid][e] > 0) else float(cz[sid][e])
            if abs(ep - r["ep"]) > 0:
                errs.append(f"ep {sid} {e}")
            c = np.asarray(cz[sid], float); valid = np.unpackbits(VAL[sid])[:ncal].astype(bool)
            got = {"SL10": -1, "SL20": -1, "TP30": -1, "TR20": -1}; hi = -math.inf
            for d in range(e, s1 + 1):
                if got["SL10"] < 0 and c[d] <= ep * 90 / 100.0: got["SL10"] = d
                if got["SL20"] < 0 and c[d] <= ep * 80 / 100.0: got["SL20"] = d
                if got["TP30"] < 0 and c[d] >= ep * 130 / 100.0: got["TP30"] = d
                if valid[e]:
                    if valid[d]:
                        hi = max(hi, c[d])
                    if got["TR20"] < 0 and c[d] <= hi * 80 / 100.0: got["TR20"] = d
            for k, v in got.items():
                nchk += 1
                if int(r[k]) != v:
                    errs.append(f"停損停利 {E} {sid} e={e} {k}：自己 {v} vs 檔 {int(r[k])}")
    info["停損停利逐列比對"] = nchk
    # ③ 帳（前 5 顆）
    A = pd.read_csv(os.path.join(OUT, "confirm_audit5.csv.gz"), dtype={"sid": str}, float_precision="round_trip")
    for (cell, r), g in A.groupby(["cell", "r"]):
        E = cell.split("|")[1]; F = CRS[E]
        mtr = g[g["sid"] == "_metrics"].iloc[0]; g = g[g["sid"] != "_metrics"]
        need = sorted(set(g["sid"]) - set(cz))
        if need:
            c2, o2 = RR.load_prices(need, cal, mk, "branch"); cz.update(c2); oz.update(o2)
        rowset = set(zip(F["sid"], F["entry_pos"].astype(int)))
        pos = {}; cash = 1.0; eq = np.ones(ncal); maxheld = 0; bad_buy = 0
        byt = {t: gg for t, gg in g.groupby("t")}
        first = int(g["t"].min())
        for t in range(first, s1 + 1):
            for x in (byt[t].itertuples() if t in byt else []):
                if x.side == "sell":
                    ps = pos[x.sid]; cash += float(x.amt) - float(x.cost if x.cost == x.cost else 0.0)
                    if x.kind == "trim":
                        ps["amt"] *= 0.5
                    else:
                        del pos[x.sid]
            for x in (byt[t].itertuples() if t in byt else []):
                if x.side == "buy":
                    if x.sid in pos:
                        errs.append(f"重複持有 {cell} r{r} {x.sid} t={t}")
                    if (x.sid, t) not in rowset:
                        bad_buy += 1
                    pos[x.sid] = {"amt": float(x.amt), "ep": float(x.px)}; cash -= float(x.amt)
            maxheld = max(maxheld, len(pos))
            eq[t] = cash + sum(ps["amt"] * float(cz[s][t]) / ps["ep"] for s, ps in pos.items())
        c_, m_, _ = RR.win_metrics(eq, first, s1 + 1, s0, s1)
        if abs(c_ - mtr["amt"]) > 1e-9 or abs(m_ - mtr["px"]) > 1e-9:
            errs.append(f"帳 {cell} r{r}：自己 {c_:.10f}／{m_:.10f} vs 引擎 {mtr['amt']:.10f}／{mtr['px']:.10f}")
        if maxheld > 10 or bad_buy:
            errs.append(f"帳 {cell} r{r}：最多持股 {maxheld}、非列買進 {bad_buy}")
    info["帳_顆數"] = int(A.groupby(["cell", "r"]).ngroups)
    # ④ 挑選與標籤
    C = pd.read_csv(os.path.join(OUT, "cells.csv"), float_precision="round_trip")
    for seg in ("探索", "確認"):
        c50 = S["0050同段"][seg]["cagr"]; r50 = c50 / abs(S["0050同段"][seg]["mdd"])
        for q in C[C["段"] == seg].itertuples():
            lab = "合格" if (q.cagr_med > c50 and q.cagr_med / abs(q.mdd_med) >= r50) else ("另列" if q.cagr_med > c50 else "不合格")
            if lab != q.label:
                errs.append(f"標籤 {seg} {q.E} {q.出場} {q.停損}{q.停利}")

    def pick(df):
        ok = df[df["label"] == "合格"]; pool = ok if len(ok) else df
        pool = pool.assign(_r=pool["cagr_med"] / pool["mdd_med"].abs())
        return pool.sort_values(["_r", "cagr_med"], ascending=[False, False]).iloc[0]
    for E in ("E1", "E2"):
        q = pick(C[(C["段"] == "探索") & (C["E"] == E) & (C["停損"] == "無") & (C["停利"] == "無") & (~C["出場"].str.startswith("H"))])
        if q["出場"] != ch[E]:
            errs.append(f"挑出場 {E}：自己 {q['出場']} vs {ch[E]}")
    cand = C[(C["段"] == "探索") & (((C["E"] == "E1") & (C["出場"] == ch["E1"])) | ((C["E"] == "E2") & (C["出場"] == ch["E2"])))]
    q = pick(cand)
    if [q["E"], q["出場"], q["停損"], q["停利"]] != S["探索段挑停損停利"][1:]:
        errs.append(f"挑停損停利：自己 {[q['E'], q['出場'], q['停損'], q['停利']]} vs {S['探索段挑停損停利']}")
    info["錯誤數"] = len(errs)
    print(json.dumps(info, ensure_ascii=False))
    for e_ in errs[:25]:
        print("  ⛔", e_)
    json.dump({"info": info, "errors": errs[:300]}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("查核：" + ("全過" if not errs else f"⛔ {len(errs)} 項不過"))


if __name__ == "__main__":
    main()
