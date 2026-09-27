# -*- coding: utf-8 -*-
"""稽核 §五（seq3 §五、§七之六；裁定 seq257 順 7）第 4 件：留現金跌深加碼、強勢類股（K7）⇒ 列出退化格；挑中格若是退化格才重挑。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchAudit5_4 Sector|Dip [--procs 2] [--reps 1000]
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchAudit5_4_check.py

讀法（⭐ 看數字前寫定）：
  強勢類股（PREREG強勢類股 seq1；resultsSector）：退化 ＝ seq246 字面：探索段（月換續抱，主版）平均持股 ＜ 一半檔數（5）或現金比例 ＞ 30%
     ⇒ 挑中格是退化格 ⇒ 在非退化格裡照原挑法重挑（過判準者取比值最高；都沒過取比值最高；同分照原件 年化、L、k、挑法 a 先）
     ⇒ 新挑中格在確認段照使用者判準判；對照臂（(c) 類股內隨機、假訊號臂 隨機 k 類股）各 --reps 次重跑新格
     ⭐ 停止交易強制出場：開（新挑中格與對照臂都用 researchScore.sim_book＝researchSector.sim_book＋stop_force；閘：SF 空時 ＝ researchSector.sim_book 逐位元）
  留現金跌深加碼（PREREG跌深加碼 seq2；resultsDip）：沒有檔數與出場 ⇒ seq246 的持股／現金門檻依構造不適用（留現金是規則本身）；
     K7 的「出場幾乎不觸發」在本件對應「加碼幾乎不觸發」⇒ 本件列兩級：
       完全退化 ＝ 探索段一次都沒加碼（該格 ≡ C1 只留現金）；部分退化 ＝ 梯的三階中有階在探索段從未觸發
     ⇒ 挑中格若「完全退化」才重挑；部分退化照列、⛔ 不重挑（由裁定線定是否改用部分退化當門檻）
輸出 backtest/resultsAudit5/4/：Sector_*、Dip_*、REPORT.md、summary.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsAudit5", "4")
_G: dict = {}


def _load_px(args):
    sid, mk = args
    sys.path.insert(0, HERE)
    import researchSector as RS
    r = RS.load_full((sid, mk))
    if r[1] is None:
        return r
    st = RS.D.load_stock(sid, mk, _G["cal"])
    r[1]["valid"] = np.isfinite(st.df["close"].to_numpy(float))
    return r


def _ctrl(args):
    kind, r = args
    sys.path.insert(0, HERE)
    from . import researchScore as SC
    import researchSector as RS
    B = _G["book"]; L, k, pk = _G["cell"]
    rng = np.random.default_rng(RS.SEED0 + r)
    if kind == "c":
        sel = {e: B.pick(e, L, k, "c", rng=rng) for e in B.reb}
    else:
        sel = {e: B.pick(e, L, k, pk, rng=rng, fake=True) for e in B.reb}
    res = SC.sim_book(sel, _G["P"], _G["dl"], _G["SF"], _G["t0"], _G["t1"], "hold", RS.N)
    out = {"arm": kind, "r": r}
    for nm, (a, b) in _G["seg"].items():
        c, m, ratio = RS.seg_metrics(res["eq"], a, b)
        out.update({f"{nm}_年化": c, f"{nm}_回落": m})
    return out


def run_sector(a):
    sys.path.insert(0, HERE)
    import researchSector as RS
    from . import researchScore as SC
    D, TR, UG, H2 = RS.D, RS.TR, RS.UG, RS.H2
    os.makedirs(OUT, exist_ok=True)
    t00 = time.time()
    T = pd.read_csv(os.path.join(HERE, "resultsSector", "cells.csv"), float_precision="round_trip")
    J = json.load(open(os.path.join(HERE, "resultsSector", "body.json"), encoding="utf-8"))
    ex = T[(T["段"] == "探索") & (T["版本"] == "月換續抱")].copy()
    ex["退化"] = (ex["平均持股"] < RS.N / 2) | (ex["現金比例"] > 0.30)
    Z = J["0050"]
    c0, r0 = Z["探索"]["年化"], Z["探索"]["比值"]
    ex["過判準"] = (ex["年化"] > c0) & (ex["比值"] >= r0)
    orig = J["探索挑格"]["挑中"]
    orig_deg = bool(ex.loc[ex["格"] == orig, "退化"].iloc[0])
    cand = ex[~ex["退化"]]
    pool_ = cand[cand["過判準"]] if cand["過判準"].any() else cand
    pool_ = pool_.assign(_pk=pool_["挑法"].map({"a": 0, "b": 1}))
    best = pool_.sort_values(["比值", "年化", "L", "k", "_pk"], ascending=[False, False, True, True, True]).iloc[0]
    ck = best["格"]; L, k, pk = int(best["L"]), int(best["k"]), best["挑法"]
    ex[["格", "L", "k", "挑法", "年化", "比值", "平均持股", "現金比例", "退化", "過判準"]].to_csv(os.path.join(OUT, "Sector_explore_cells.csv"), index=False)
    S = {"原挑中": orig, "原挑中是退化格": orig_deg, "退化格": ex.loc[ex["退化"], "格"].tolist(), "非退化格數": int(len(cand)),
         "非退化中過判準": int(cand["過判準"].sum()), "重挑": ck if orig_deg else None}
    if not orig_deg:
        json.dump(S, open(os.path.join(OUT, "Sector_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
        return S
    # ── 重跑新挑中格（researchSector.main_body 的資料段，逐字同式）
    cal = D.load_calendar(); n = len(cal)
    t0 = int(cal.searchsorted(pd.Timestamp(RS.W0))); t1 = int(cal.searchsorted(pd.Timestamp(RS.W1)))
    SEGP = {nm: (int(cal.searchsorted(pd.Timestamp(x))), int(cal.searchsorted(pd.Timestamp(y)))) for nm, (x, y) in RS.SEG.items()}
    cols = ["measure_date", "stock_id", "market", "eligible"]
    ext = pd.read_csv(RS.PANEL_EXT, dtype={"stock_id": str}, usecols=cols, parse_dates=["measure_date"])
    stocks = pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str)
    G = UG.gate3(stocks)
    ind = pd.read_csv(os.path.join(H2.H2D, "meta", "industry.csv"), dtype=str)
    blank = ind["industry_name"].isna() | (ind["industry_name"].astype(str).str.strip() == "")
    ind.loc[blank, "industry_name"] = ind.loc[blank, "industry_code"].map(RS.CODE_NAME)
    ind = ind[ind["industry_name"] != "存託憑證"]
    cls = {s: RS.NAME_MAP.get(nm, nm) for s, nm in zip(ind["stock_id"], ind["industry_name"])}
    rev, _, _ = RS.R34.load_revenue()
    rf = RS.P4F.rev_hi24_flags(rev, cal)
    rd = RS.R34.rebalance_dates(list(rev.index), cal, 10)
    reb = sorted({e for _, e in rd.values() if t0 <= e <= t1})
    _G.update(cal=cal)
    RS._G.update(cal=cal)
    with Pool(a.procs, initializer=RS._init, initargs=(cal,)) as pool:
        P = dict(pool.map(_load_px, list(zip(G["stock_id"], G["market"])), chunksize=16))
    P = {s: v for s, v in P.items() if v is not None}
    dl = TR.delist_status({s: {"trd": v["trd"]} for s, v in P.items()}, cal, official=TR.load_official())
    pm = {d: g for d, g in ext.groupby("measure_date")}; meas = sorted(pm)
    elig = {}
    for e in reb:
        d = cal[e]; mm = [m for m in meas if m.year == d.year and m.month == d.month]
        g = pm[max(mm)]; elig[e] = [s for s in g.loc[g["eligible"].astype(str) == "True", "stock_id"] if s in P]
    revset = {e: set(rf.iloc[e].index[rf.iloc[e].to_numpy() == 100]) for e in reb}
    B = RS.Book(reb, cal, P, cls, elig, revset)
    SF = SC.R.stop_force_days({s: v["valid"] for s, v in P.items()}, t1)
    sel = {e: B.pick(e, L, k, pk) for e in reb}
    r_orig = RS.sim_book(sel, P, dl, t0, t1, "hold")
    r_nosf = SC.sim_book(sel, P, dl, {}, t0, t1, "hold", RS.N)
    gate = {"SF 空 ＝ researchSector.sim_book（權益逐位元）": bool(np.array_equal(r_orig["eq"], r_nosf["eq"]))}
    cf0 = T[(T["格"] == ck) & (T["段"] == "確認") & (T["版本"] == "月換續抱")].iloc[0]
    cm0 = RS.seg_metrics(r_orig["eq"], *SEGP["確認"])
    gate["researchSector.sim_book 確認段 ＝ cells.csv"] = abs(cm0[0] - cf0["年化"]) < 1e-12 and abs(cm0[1] - cf0["回落"]) < 1e-12
    r_sf = SC.sim_book(sel, P, dl, SF, t0, t1, "hold", RS.N)
    out = {}
    for nm, (x, y) in SEGP.items():
        for tag, rr in (("原件（強制出場關）", r_orig), ("強制出場開", r_sf)):
            c, m, ratio = RS.seg_metrics(rr["eq"], x, y)
            out[f"{nm}_{tag}"] = {"年化": c, "回落": m, "比值": ratio, "標籤": RS.label(c, m, Z[nm]["年化"], Z[nm]["回落"])}
    out["強制出場筆數"] = int(r_sf["cnt"]["stop_force"])
    _G.update(book=B, cell=(L, k, pk), P=P, dl=dl, SF=SF, t0=t0, t1=t1, seg=SEGP)
    with Pool(a.procs) as pool:
        CT = pd.DataFrame(pool.map(_ctrl, [("c", r) for r in range(a.reps)] + [("fake", r) for r in range(a.reps)], chunksize=10))
    CT.to_csv(os.path.join(OUT, "Sector_controls.csv.gz"), index=False)
    real = out["確認_強制出場開"]["年化"]
    arms = {}
    for arm in ("c", "fake"):
        x = CT[CT["arm"] == arm]["確認_年化"].to_numpy(float)
        arms[arm] = {"中位": float(np.median(x)), "p（年化 ≥ 本格）": float(np.mean(x >= real)), "贏0050同段的比例": float(np.mean(x > Z["確認"]["年化"]))}
    S.update({"新挑中": {"格": ck, "探索": {kk: float(best[kk]) for kk in ("年化", "比值", "平均持股", "現金比例")}}, "新格結果": out, "對照": arms, "閘": gate,
              "原挑中確認（引 body.json）": J["確認"], "秒": round(time.time() - t00)})
    json.dump(S, open(os.path.join(OUT, "Sector_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps({k_: v for k_, v in S.items() if k_ != "退化格"}, ensure_ascii=False, default=str)[:1500])
    if not all(gate.values()):
        raise SystemExit("⛔ 閘不過")
    return S


def run_dip(a):
    sys.path.insert(0, HERE)
    from . import researchDip as DP
    from . import researchTri as T_
    from . import researchTri_0052 as T52
    from . import data as D
    os.makedirs(OUT, exist_ok=True)
    G = T_.load_all(); cal = list(G["cal"]); pos = G["pos"]; N = len(cal)
    calm = D.load_calendar(); mstr = [str(x.date()) for x in calm]; off = pos[mstr[0]]
    O52, C52, _ = T52.load_0052(G)
    st = D.load_stock("00685L", "twse", calm).df
    O85 = np.full(N, np.nan); C85 = np.full(N, np.nan)
    O85[off:off + len(mstr)] = st["open"].to_numpy(float); C85[off:off + len(mstr)] = st["close"].to_numpy(float)
    C85 = pd.Series(C85).ffill().to_numpy()
    M = DP.Mkt(G, O52, C52, O85, C85)
    dd, NH, _ = DP.dd_series(G)
    SEG = {"主窗": (pos[DP.EXP[0]], pos[DP.EXP[1]]), "00685L窗": (pos[DP.L85[0]], pos[DP.L85[1]])}
    CL = DP.cells_all()
    ref = pd.read_csv(os.path.join(HERE, "resultsDip", "body_cells.csv"), float_precision="round_trip")
    rows = []; bad = 0
    for idx, c in CL[CL["型"] == "格"].iterrows():
        i0, i1 = SEG[c["窗"]]
        r = DP.run_cell(M, c, i0, i1, dd, NH, cal)
        th = DP.LADDER[c["梯"]]
        fired = {f"−{int(x * 100)}%": 0 for x in th}
        for act in r["acts"]:
            if act["類"] == "加碼":
                for lv in re.findall(r"−(\d+)%", act["內容"].split("觸發")[1]):
                    fired[f"−{lv}%"] += 1
        q = ref[(ref["列"] == idx) & (ref["跑在"] == c["窗"]) & (ref["段"] == "探索")].iloc[0]
        bad += int(abs(q["年化"] - r["年化"]) > 1e-12)
        nf = sum(fired.values())
        rows.append({"列": idx, "窗": c["窗"], "名稱": DP.cname(c), "梯": c["梯"], "探索_年化": r["年化"], "探索_加碼次數": nf, **{f"觸發{k_}": v for k_, v in fired.items()},
                     "完全退化": nf == 0, "部分退化": nf > 0 and min(fired.values()) == 0,
                     "未觸發的階": "、".join(k_ for k_, v in fired.items() if v == 0)})
    X = pd.DataFrame(rows); X.to_csv(os.path.join(OUT, "Dip_explore_cells.csv"), index=False)
    SJ = json.load(open(os.path.join(HERE, "resultsDip", "body_summary.json"), encoding="utf-8"))
    pick = SJ["挑法乙"]["格"]
    pr = X[(X["名稱"] == pick) & (X["窗"] == "主窗")].iloc[0]
    S = {"閘_探索年化＝body_cells": {"不同格數": bad}, "格數": int(len(X)), "完全退化格數": int(X["完全退化"].sum()), "部分退化格數": int(X["部分退化"].sum()),
         "挑中（挑法乙）": pick, "挑中_完全退化": bool(pr["完全退化"]), "挑中_部分退化": bool(pr["部分退化"]), "挑中_未觸發的階": pr["未觸發的階"],
         "各梯未觸發的階（主窗探索）": X[X["窗"] == "主窗"].groupby("梯")["未觸發的階"].agg(lambda s: sorted(set(s))).to_dict(),
         "重挑": "不需要（挑中格不是完全退化）" if not pr["完全退化"] else "需要"}
    json.dump(S, open(os.path.join(OUT, "Dip_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(S, ensure_ascii=False, default=str))
    if bad:
        raise SystemExit("⛔ 閘不過")
    return S


def report():
    L = ["# 稽核 第 4 件：留現金跌深加碼、強勢類股（K7）退化格", "", f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。回測線。", ""]
    Ss = json.load(open(os.path.join(OUT, "Sector_summary.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "Sector_summary.json")) else None
    Sd = json.load(open(os.path.join(OUT, "Dip_summary.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "Dip_summary.json")) else None
    if Ss:
        L += ["## 一、強勢類股（PREREG強勢類股 seq1）", "",
              f"- 退化（seq246：探索段平均持股 ＜ 5 或現金 ＞ 30%）：{len(Ss['退化格'])}／18 格 ⇒ {'、'.join(Ss['退化格'])}",
              f"- 原挑中 **{Ss['原挑中']}** 是退化格：{'是' if Ss['原挑中是退化格'] else '否'}"]
        if Ss.get("新挑中"):
            nw = Ss["新挑中"]; r = Ss["新格結果"]
            L += [f"- 重挑（非退化 {Ss['非退化格數']} 格、過判準 {Ss['非退化中過判準']} 格 ⇒ 取比值最高）：**{nw['格']}**（探索 {nw['探索']['年化'] * 100:+.2f}%、比值 {nw['探索']['比值']:.3f}、平均持股 {nw['探索']['平均持股']:.1f}、現金 {nw['探索']['現金比例'] * 100:.1f}%）",
                  f"- 新格確認段：強制出場開 {r['確認_強制出場開']['年化'] * 100:+.2f}%／{r['確認_強制出場開']['回落'] * 100:+.2f}% ⇒ **{r['確認_強制出場開']['標籤']}**"
                  f"（原件口徑 {r['確認_原件（強制出場關）']['年化'] * 100:+.2f}%／{r['確認_原件（強制出場關）']['回落'] * 100:+.2f}% {r['確認_原件（強制出場關）']['標籤']}；強制出場 {r['強制出場筆數']} 筆）",
                  f"- 對照（確認段、各 1,000 次、強制出場開）：(c) 類股內隨機 中位 {Ss['對照']['c']['中位'] * 100:+.2f}%、p＝{Ss['對照']['c']['p（年化 ≥ 本格）']:.3f}；"
                  f"假訊號臂（隨機類股）中位 {Ss['對照']['fake']['中位'] * 100:+.2f}%、p＝{Ss['對照']['fake']['p（年化 ≥ 本格）']:.3f}",
                  f"- 原挑中確認段（引原件）：{Ss['原挑中確認（引 body.json）']}", f"- 閘：{Ss['閘']}", ""]
    if Sd:
        L += ["## 二、留現金跌深加碼（PREREG跌深加碼 seq2）", "",
              "- seq246 的持股／現金門檻依構造不適用（沒有檔數、留現金是規則本身）；K7 對應「加碼幾乎不觸發」⇒ 列兩級",
              f"- 完全退化（探索段一次都沒加碼）：{Sd['完全退化格數']}／{Sd['格數']} 格；部分退化（梯有階從未觸發）：{Sd['部分退化格數']}／{Sd['格數']} 格",
              f"- 各梯在主窗探索段沒觸發過的階：{json.dumps(Sd['各梯未觸發的階（主窗探索）'], ensure_ascii=False)}",
              f"- 挑中（挑法乙）**{Sd['挑中（挑法乙）']}**：完全退化 {'是' if Sd['挑中_完全退化'] else '否'}、部分退化 {'是' if Sd['挑中_部分退化'] else '否'}（未觸發 {Sd['挑中_未觸發的階'] or '—'}）⇒ 重挑：{Sd['重挑']}",
              "- ⚠ 若裁定改用「部分退化」當門檻：主窗每一格的梯都有階在探索段沒觸發過 ⇒ 無格可挑（探索段 0050 最深約 −28%，−30% 以下的階依資料就不會觸發）", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("part", choices=["Sector", "Dip", "report"])
    ap.add_argument("--procs", type=int, default=2); ap.add_argument("--reps", type=int, default=1000)
    a = ap.parse_args()
    if a.part == "Sector":
        run_sector(a)
    elif a.part == "Dip":
        run_dip(a)
    report()


if __name__ == "__main__":
    main()
