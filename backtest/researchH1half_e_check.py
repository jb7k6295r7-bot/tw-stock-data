# -*- coding: utf-8 -*-
"""H1 先賣一半 seq1 電子＋傳產普查正式跑獨立重算——回測線計算子代理。⛔ 不 commit、不改既有檔。
⛔ 不 import researchH1half／researchH1half_e／researchLampCensus；價格用 researchH1half_check 的原始價＋factor 自行還原函式（ratio、ann）。
  (a) 未到 E 件全抱 R、大盤 ＝ 普查 948dc4dc38 rows.csv（燈1、到末日）逐筆
  (b) 每件全抱 R、賣出那半 R、大盤、d：原始價＋factor 重算逐筆
  (c) 情境（照實／嚴格／剔自評知道）× 類（電子／傳產／合計）× 甲乙 × 型：由 (b) 重算值重新彙總，對 stats.csv（中位、平均、P25／P75、最好最壞、份口徑中位、
      觸發數、緊接版觸發數、又漲 ≥1 倍、門檻描述句）

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchH1half_e_check
"""
import io
import json
import os
import subprocess
from io import StringIO

import numpy as np
import pandas as pd

from backtest import researchH1half_check as K

os.chdir(os.path.expanduser("~/tw-p17"))
OUT = "backtest/resultsH1half/main_e"
CREV = "948dc4dc38"
TOL = 1e-6


def main():
    T = pd.read_csv(StringIO(K.gshow("data/history/market_tri.csv"))); T["date"] = pd.to_datetime(T["date"])
    T = T.dropna().drop_duplicates("date").sort_values("date").set_index("date")["close"]
    CAL = pd.DatetimeIndex(T.index)

    def tri(d):
        return float(T[T.index <= pd.Timestamp(d)].iloc[-1])

    def prev_td(d):
        return CAL[CAL < pd.Timestamp(d)][-1]

    RW = pd.read_csv(os.path.join(OUT, "rows.csv"), dtype={"代號": str})
    ST = pd.read_csv(os.path.join(OUT, "stats.csv"))
    rep = {}
    LCR = pd.read_csv(io.BytesIO(subprocess.run(["git", "show", f"{CREV}:backtest/resultsLampCensus/rows.csv"], capture_output=True, check=True).stdout), dtype={"代號": str})
    LCR = LCR[(LCR["段"] == "燈1") & (LCR["H"].astype(str) == "末")][["訊號", "代號", "R", "大盤", "結算日"]]
    nt = RW[RW["未到"].astype(bool)].merge(LCR, on=["訊號", "代號"], suffixes=("", "_LC"))
    rep["(a)未到件對普查到末日"] = {"件": len(nt), "未到件總數": int(RW["未到"].astype(bool).sum()), "R最大差": float((nt["全抱R"] - nt["R"]).abs().max()),
                              "大盤最大差": float((nt["全抱大盤"] - nt["大盤"]).abs().max()), "結算日不同": int((nt["全抱結算日"] != nt["結算日"]).sum())}
    rec = []; errs = []
    for _, r in RW.iterrows():
        sid = r["代號"]; e = r["進場日"]; x = r["全抱結算日"]
        try:
            Rf = K.ratio(sid, e, "open", x, "close") - 1 - K.COST
        except Exception as ex:          # noqa: BLE001
            errs.append(f"{r['訊號']} {sid} 全抱 {type(ex).__name__}"); continue
        Mf = tri(x) / tri(prev_td(e)) - 1
        o = {"訊號": r["訊號"], "代號": sid, "dRf": Rf - r["全抱R"], "dMf": Mf - r["全抱大盤"], "af": K.ann(Rf, int(r["全抱H"]))}
        if bool(r["觸發"]):
            s = r["賣出日"]
            Rs = K.ratio(sid, e, "open", s, "open") - 1 - K.COST
            Ms = tri(prev_td(s)) / tri(prev_td(e)) - 1
            o.update({"dRs": Rs - r["賣R"], "dMs": Ms - r["賣大盤"]})
            o["H1"] = (K.ann(Rs, int(r["賣H"])) + o["af"]) / 2
            o["d份"] = 0.5 * (Rs - Ms) - 0.5 * (Rf - Mf)
            d, A = K.px(sid)
            end = min(pd.Timestamp(s) + pd.DateOffset(months=12), pd.Timestamp(x))
            win = d[(d.index >= pd.Timestamp(s)) & (d.index <= end)]
            mx = max(K.ratio(sid, s, "open", dd, "close") for dd in win.index if np.isfinite(win.at[dd, "close"]) and win.at[dd, "close"] > 0)
            o["又漲1倍"] = bool(mx - 1 >= 1.0)
        else:
            o["H1"] = o["af"]; o["d份"] = 0.0; o["又漲1倍"] = False
        o["d"] = o["H1"] - o["af"]; o["dd"] = o["d"] - r["d"]
        rec.append(o)
    B = pd.DataFrame(rec)
    rep["(b)原始價重算"] = {"件": len(B), "總件": len(RW), "重算失敗": errs, "全抱R最大差": float(B["dRf"].abs().max()), "大盤最大差": float(B["dMf"].abs().max()),
                        "賣R最大差": float(B["dRs"].abs().max()), "賣大盤最大差": float(B["dMs"].abs().max()), "d最大差": float(B["dd"].abs().max()),
                        "超過1e-6件": int(((B[["dRf", "dMf", "dd"]].abs() > TOL).any(axis=1)).sum())}
    M = RW.merge(B[["訊號", "代號", "d", "d份", "又漲1倍"]], on=["訊號", "代號"], suffixes=("", "_chk"))
    cc = {}; nbad = 0
    for _, row in ST.iterrows():
        ev = M[M[row["組"]].astype(bool)]
        ev = ev if row["類"] == "合計" else ev[ev["類"] == row["類"]]
        if row["情境"] == "嚴格":
            ev = ev[~ev["兩可"].astype(bool)]
        elif row["情境"] == "剔自評知道":
            ev = ev[~ev["自評知道"].astype(bool)]
        ev = ev if row["型"] == "全部" else ev[ev["型"] == row["型"]]
        sg = ev.groupby("訊號").agg(d=("d_chk", "mean"), d份=("d份_chk", "mean"))
        if not len(sg):
            continue
        mine = {"d中位(訊號)": float(sg["d"].median()), "d平均(訊號)": float(sg["d"].mean()), "dP25(訊號)": float(np.percentile(sg["d"], 25)),
                "dP75(訊號)": float(np.percentile(sg["d"], 75)), "d最好(訊號)": float(sg["d"].max()), "d最壞(訊號)": float(sg["d"].min()),
                "d份中位(訊號)": float(sg["d份"].median()), "觸發數": int(ev["觸發"].astype(bool).sum()), "緊接版觸發數": int(ev["緊接版觸發"].astype(bool).sum()),
                "賣後12月又漲≥1倍": int(ev["又漲1倍"].sum())}
        diffs = {k: (abs(v - float(row[k])) if isinstance(v, float) else int(v != int(row[k]))) for k, v in mine.items()}
        th = bool(mine["d平均(訊號)"] >= 0 and mine["d中位(訊號)"] > 0)
        bad = [k for k, v in diffs.items() if v > TOL] + (["門檻句"] if th != bool(row["門檻描述句成立"]) else [])
        nbad += bool(bad)
        cc[f"{row['情境']}|{row['類']}|{row['組']}|{row['型']}"] = {"最大差": max(diffs.values()), "不同": bad}
    rep["(c)彙總重算"] = {"格數": len(cc), "不符格": nbad, "不符明細": {k: v for k, v in cc.items() if v["不同"]}}
    ok = (rep["(a)未到件對普查到末日"]["R最大差"] < TOL and rep["(a)未到件對普查到末日"]["結算日不同"] == 0 and rep["(a)未到件對普查到末日"]["件"] == rep["(a)未到件對普查到末日"]["未到件總數"]
          and rep["(b)原始價重算"]["超過1e-6件"] == 0 and not errs and nbad == 0)
    rep["CHECK"] = "PASS" if ok else "FAIL"
    B.to_csv(os.path.join(OUT, "check_rows.csv"), index=False, encoding="utf-8-sig")
    json.dump(rep, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(rep, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
