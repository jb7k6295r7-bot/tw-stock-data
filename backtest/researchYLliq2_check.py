# -*- coding: utf-8 -*-
"""researchYLliq2 獨立查核（回測線計算子代理；⛔ 不改既有檔、⛔ 不 commit）。

    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLliq2_check
 C1 訊號與定版一致：resultsYLliq2/signals 的 (sid, entry_pos, xpos, 淨, 超額) ＝ resultsYLskip／resultsYFskip signals（repr 逐位元）
 C2 抽樣手算均量／均額／進場日成交額：直接讀資料目錄 stocks/<sid>.csv 原始列（不經 patterns.Frame），訊號日前 20 個日曆交易日
 C3 抽樣手算淨報酬：D.load_stock 還原開收（不經引擎 closes）⇒ 收[xpos] ÷ 開[entry] − 1 − COST（非強制出場、已滿、開盤有效）
 C4 cells 重算：由 signals 直接 groupby 算筆數、淨中位／平均、勝率、超額中位／平均 ＝ cells.csv
 C5 6782 對帳：資料 main a3a7f4eabe（forward 名單所用）的訊號日 2026-10-16 均量 vs 營收可用日（2026-09-10）均量
輸出 backtest/resultsYLliq2/check.json、run_check.log
"""
from __future__ import annotations

import glob
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D                              # noqa: E402
from backtest import patterns as P                          # noqa: E402
from backtest import research11 as R                        # noqa: E402

OUT = "backtest/resultsYLliq2"
SRC = {"營量": "backtest/resultsYLskip/signals.csv.gz", "營飆": "backtest/resultsYFskip/signals.csv.gz"}
NS = 40


def main():
    L = []
    log = lambda m: (print(m, flush=True), L.append(m))  # noqa: E731
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    A = pd.read_csv(os.path.join(OUT, "signals.csv.gz"), dtype={"sid": str}, float_precision="round_trip")
    CAL = np.load(os.path.join(OUT, "cal.npz"))
    out = {}
    # C1
    for rn, p in SRC.items():
        t = pd.read_csv(p, dtype={"sid": str}, float_precision="round_trip")
        a = A[A["規則"] == rn]
        m = a.merge(t, on=["世界", "sid", "entry_pos"], suffixes=("", "_src"), how="outer", indicator=True)
        out[f"C1 {rn} 不配對"] = int((m["_merge"] != "both").sum())
        out[f"C1 {rn} xpos/淨/超額/段 不同"] = int(sum((m["xpos"] != m["xpos_src"]) | (m["淨"].map(repr) != m["淨_src"].map(repr))
                                                     | (m["超額"].map(repr) != m["超額_src"].map(repr)) | (m["段"] != m["段_src"])))
    # C2／C3
    rng = np.random.default_rng(7)
    c2v = c2a = c2e = 0.0; c2n = 0; c2nan = 0; c3 = 0.0; c3n = 0; ex = []
    for wn in ("主", "早年"):
        D.DATA = S["資料目錄"][wn]; cal = pd.to_datetime(CAL[wn])
        sub = A[A["世界"] == wn]
        for i in rng.choice(len(sub), NS, replace=False):
            r = sub.iloc[i]; sid = r["sid"]; p_, e_ = int(r["pos"]), int(r["entry_pos"])
            raw = pd.read_csv(os.path.join(D.DATA, "stocks", f"{sid}.csv"), dtype={"date": str}, usecols=["date", "volume", "amount"])
            raw["date"] = pd.to_datetime(raw["date"]); raw = raw.drop_duplicates("date").set_index("date")
            win = cal[p_ - 20:p_]
            v = pd.to_numeric(raw["volume"], errors="coerce").reindex(win).to_numpy(float)
            am = pd.to_numeric(raw["amount"], errors="coerce").reindex(win).fillna(0.0).to_numpy(float)
            hv = float(v.mean()) if np.isfinite(v).all() else np.nan
            ha = float(am.mean())
            ea = float(pd.to_numeric(raw["amount"], errors="coerce").reindex([cal[e_]]).iloc[0])
            if np.isfinite(hv) != np.isfinite(r["訊號日均量"]):
                c2nan += 1
            elif np.isfinite(hv):
                c2v = max(c2v, abs(hv - r["訊號日均量"]))
            c2a = max(c2a, abs(ha - r["訊號日均額"])); c2e = max(c2e, abs(ea - r["進場日成交金額"]) if np.isfinite(ea) else 0.0); c2n += 1
            if len(ex) < 6:
                ex.append({"世界": wn, "規則": r["規則"], "sid": sid, "訊號日": str(cal[p_].date()), "手算均量(張)": hv / 1000, "表均量(張)": r["訊號日均量"] / 1000,
                           "手算均額(萬)": ha / 1e4, "表均額(萬)": r["訊號日均額"] / 1e4, "進場日成交額(萬)": ea / 1e4, "2萬占": 20000 / ea if ea > 0 else None,
                           "組": r["均量組"], "淨": r["淨"]})
            if r["強制出場"] == 0 and r["未滿"] == 0:
                st = D.load_stock(sid, "twse", cal)                 # market 只記錄、不影響讀檔
                if st is None or not np.isfinite(st.df["open"].iloc[e_]):
                    continue
                df = st.df
                hn = float(df["close"].iloc[int(r["xpos"])] / df["open"].iloc[e_] - 1.0 - R.COST)
                c3 = max(c3, abs(hn - r["淨"])); c3n += 1
    out.update({"C2 抽樣筆": c2n, "C2 均量最大差（股）": c2v, "C2 均量 NaN 不一致": c2nan, "C2 均額最大差（元）": c2a, "C2 進場日成交額最大差": c2e,
                "C3 手算淨報酬筆": c3n, "C3 淨報酬最大差": c3})
    out["C2 例"] = ex
    # C4
    C = pd.read_csv(os.path.join(OUT, "cells.csv"), encoding="utf-8-sig")
    bad = 0
    for _, c in C.iterrows():
        g = A[(A["世界"] == c["世界"]) & (A["段"] == c["段"]) & (A["規則"] == c["規則"]) & (A["均量組" if c["分組"] == "均量" else "均額組"] == c["組"])]
        if len(g) != c["筆數"]:
            bad += 1; continue
        if len(g):
            for k, v in (("淨_中位", g["淨"].median()), ("淨_平均", g["淨"].mean()), ("勝率", (g["淨"] > 0).mean()),
                         ("超額_中位", g["超額"].median()), ("超額_平均", g["超額"].mean())):
                bad += int(abs(v - c[k]) > 1e-9)
    out["C4 cells 重算不符（項）"] = bad
    # C5 6782
    dd = sorted(glob.glob(os.path.expanduser("~/h2data/a3a7f4eabe*/data")))
    if dd:
        D.DATA = dd[0]
        cal5 = pd.to_datetime(pd.read_csv(os.path.join(D.DATA, "calendar.csv"))["date"]) if os.path.exists(os.path.join(D.DATA, "calendar.csv")) else None
        raw = pd.read_csv(os.path.join(D.DATA, "stocks", "6782.csv"), dtype={"date": str}, usecols=["date"])
        cal5 = pd.DatetimeIndex(sorted(set(pd.to_datetime(raw["date"])) | (set(cal5) if cal5 is not None else set())))
        cal5 = cal5[cal5 <= pd.Timestamp("2026-10-16")]
        st = D.load_stock("6782", "twse", cal5); f = P.Frame(st.df, st.event_dates)
        res = {}
        for lab, d in (("訊號日 2026-10-16", "2026-10-16"), ("可用日 2026-09-10", "2026-09-10")):
            if pd.Timestamp(d) in cal5:
                j = int(cal5.get_loc(pd.Timestamp(d))); res[lab] = {"均量張": float(f.vol_ma20[j]) / 1000, "gate": bool(f.gate[j])}
        out["C5 6782（資料 " + os.path.basename(os.path.dirname(dd[0]))[:10] + "）"] = res
    else:
        out["C5 6782"] = "找不到 ~/h2data/a3a7f4eabe*"
    hard = [k for k, v in out.items() if k.startswith(("C1", "C4")) and v != 0] + \
           [k for k in ("C2 均量 NaN 不一致",) if out[k] != 0] + [k for k in ("C2 均量最大差（股）", "C2 均額最大差（元）", "C2 進場日成交額最大差") if out[k] > 1e-6] + \
           (["C3 淨報酬最大差"] if out["C3 淨報酬最大差"] > 1e-9 else [])
    out["不符項"] = hard
    json.dump(out, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(json.dumps(out, ensure_ascii=False, indent=1, default=float))
    open(os.path.join(OUT, "run_check.log"), "w", encoding="utf-8").write("\n".join(L))
    if hard:
        raise SystemExit(f"⛔ 查核不符 {hard}")


if __name__ == "__main__":
    main()
