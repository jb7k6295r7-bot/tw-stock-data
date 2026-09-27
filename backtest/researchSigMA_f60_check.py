# -*- coding: utf-8 -*-
"""researchSigMA_f60 的獨立查核（⛔ 不 import researchSigMA_f60、researchSigMA、researchSig）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchSigMA_f60_check.py [--n 400]

① 過濾條件逐筆重算：確認段 E1、E2 各抽 n 列【過濾後】列 ⇒ 逐根迴圈（math.fsum）算 MA60，驗 收盤[t] ＞ MA60[t]；
   各抽 n 列【被過濾掉】的列（未過濾有、過濾後沒有）⇒ 驗 收盤[t] ≤ MA60[t] 或 MA60 無值；並驗 過濾後 ⊆ 未過濾、同列 dX 相同
② 過濾比例：列數 ⇒ 對 summary.json
③ 標籤：cells.csv 每格照使用者判準重算 ⇒ 對 label；並排表的差（點）重算
"""
from __future__ import annotations
import argparse, json, math, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchH2 as H2
D = H2.D
OUT = os.path.expanduser("~/tw-p17/backtest/resultsSigMA/f60")


def ma60_at(c, t):
    b = [i for i in range(t + 1) if math.isfinite(c[i])]
    if len(b) < 60 or b[-1] != t:
        return float("nan")
    return math.fsum(c[i] for i in b[-60:]) / 60


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=400); a = ap.parse_args()
    errs = []; info = {}
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    cal = D.load_calendar()
    from backtest import universe_gate as UG
    mk = UG.gate3(pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str)).set_index("stock_id")["market"]
    rng = np.random.default_rng(31); cache = {}

    def close(sid):
        if sid not in cache:
            cache[sid] = D.load_stock(sid, mk.get(sid, "twse"), cal).df["close"].to_numpy(float)
        return cache[sid]
    for E in ("E1", "E2"):
        Fq = pd.read_csv(os.path.join(OUT, f"rows_filtered_confirm_{E}.csv.gz"), dtype={"sid": str})
        U = pd.read_csv(os.path.join(OUT, f"rows_unfiltered_confirm_{E}.csv.gz"), dtype={"sid": str})
        m = U.merge(Fq[["sid", "t", "dX"]], on=["sid", "t"], how="left", suffixes=("", "_f"), indicator=True)
        extra = Fq.merge(U[["sid", "t"]], on=["sid", "t"], how="left", indicator=True)
        if (extra["_merge"] != "both").any():
            errs.append(f"{E}：過濾後有 {int((extra['_merge'] != 'both').sum())} 列不在未過濾裡")
        both = m[m["_merge"] == "both"]
        if (both["dX"] != both["dX_f"]).any():
            errs.append(f"{E}：同列 dX 不同 {int((both['dX'] != both['dX_f']).sum())}")
        dropped = m[m["_merge"] == "left_only"]
        for df_, want, tag in ((Fq, True, "保留"), (dropped, False, "濾掉")):
            if not len(df_):
                continue
            for i in rng.choice(len(df_), size=min(a.n, len(df_)), replace=False):
                r = df_.iloc[i]; c = close(r["sid"]); t = int(r["t"]); ma = ma60_at(c, t)
                ok = math.isfinite(ma) and c[t] > ma
                if ok != want:
                    errs.append(f"{E} {tag} {r['sid']} t={t}：收盤 {c[t]} MA60 {ma}")
        fr = S["過濾比例"][f"確認|{E}|MA60"]
        if fr["未過濾列"] != len(U) or fr["過濾後列"] != len(Fq):
            errs.append(f"{E} 過濾比例列數")
        info[f"{E}_未過濾列"] = len(U); info[f"{E}_過濾後列"] = len(Fq); info[f"{E}_濾掉"] = int(len(dropped))
    C = pd.read_csv(os.path.join(OUT, "cells.csv"))
    for q in C.itertuples():
        b = S["0050同段"][q.段]; c50, r50 = b["cagr"], b["cagr"] / abs(b["mdd"])
        lab = "合格" if (q.cagr_med > c50 and q.cagr_med / abs(q.mdd_med) >= r50) else ("另列" if q.cagr_med > c50 else "不合格")
        if lab != q.label:
            errs.append(f"標籤 {q.版} {q.段} {q.E} {q.出場}")
    SB = pd.read_csv(os.path.join(OUT, "side_by_side.csv"))
    if (np.abs((SB["過濾_年化"] - SB["未過濾_年化"]) * 100 - SB["年化差_點"]) > 1e-9).any():
        errs.append("並排年化差")
    info["錯誤數"] = len(errs)
    print(json.dumps(info, ensure_ascii=False))
    for e_ in errs[:25]:
        print("  ⛔", e_)
    json.dump({"info": info, "errors": errs[:300]}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("查核：" + ("全過" if not errs else f"⛔ {len(errs)} 項不過"))


if __name__ == "__main__":
    main()
