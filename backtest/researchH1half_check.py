# -*- coding: utf-8 -*-
"""H1 先賣一半 seq1 正式跑（裁定 seq475）獨立重算——回測線計算子代理。⛔ 不 commit、不改既有檔。
獨立處：⛔ 不 import researchH1half／researchLampCensus／researchV41EV；價格改讀 PIN 版 data/stocks/<代號>.csv 未還原開收＋data/adj/<代號>.csv factor 自行還原
（還原(d)＝原始(d)×Π_{事件日>d} factor ⇒ 兩日比值＝原始比值 ÷ Π_{前日<事件日≤後日} factor）；大盤讀 market_tri.csv。
  (a) 普查未到 E 件的全抱 R、大盤 ＝ resultsLampCensus/rows.csv（燈1、到末日）逐筆對（同進場、同結算到面板尾）
  (b) 普查每件全抱 R、賣出那半 R、大盤：原始價＋factor 重算逐筆對
  (c) 年化、d、d份、訊號層中位／平均／P25／P75／最好／最壞、觸發數、緊接版觸發數：由 (b) 重算值重新彙總，對 stats.csv
  (d) 賣後 12 月又漲 ≥1 倍筆數（普查）：原始收盤＋factor 重算
舊 31 段含 2015 前（data/early）⇒ 只做 (c) 用主程式 R 重新彙總，不重抓價格。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchH1half_check
"""
import json
import os
import subprocess
from io import StringIO

import numpy as np
import pandas as pd

os.chdir(os.path.expanduser("~/tw-p17"))
PIN = "9b0e9882572c"
OUT = "backtest/resultsH1half/main"
COST = 0.00585
TOL = 1e-6


def gshow(p):
    t = subprocess.run(["git", "show", f"{PIN}:{p}"], capture_output=True, text=True)
    return t.stdout if t.returncode == 0 else None


_px = {}


def px(sid):
    if sid not in _px:
        d = pd.read_csv(StringIO(gshow(f"data/stocks/{sid}.csv")), dtype={"stock_id": str})
        d["date"] = pd.to_datetime(d["date"]); d = d.set_index("date")
        a = gshow(f"data/adj/{sid}.csv")
        A = pd.read_csv(StringIO(a)) if a else pd.DataFrame(columns=["date", "factor"])
        A["date"] = pd.to_datetime(A["date"]); A["factor"] = pd.to_numeric(A["factor"], errors="coerce")
        _px[sid] = (d, A)
    return _px[sid]


def ratio(sid, d0, f0, d1, f1):
    """還原 f1(d1) ÷ 還原 f0(d0)。"""
    d, A = px(sid)
    v0 = float(d.at[pd.Timestamp(d0), f0]); v1 = float(d.at[pd.Timestamp(d1), f1])
    fac = A[(A["date"] > pd.Timestamp(d0)) & (A["date"] <= pd.Timestamp(d1))]["factor"].prod()
    return v1 / v0 / fac


def ann(R, H):
    if not np.isfinite(R):
        return np.nan
    return -1.0 if 1 + R <= 0 else (1 + R) ** (250.0 / max(int(H), 60)) - 1


def main():
    T = pd.read_csv(StringIO(gshow("data/history/market_tri.csv"))); T["date"] = pd.to_datetime(T["date"])
    T = T.dropna().drop_duplicates("date").sort_values("date").set_index("date")["close"]
    CAL = pd.DatetimeIndex(T.index)

    def tri(d):
        return float(T[T.index <= pd.Timestamp(d)].iloc[-1])

    def prev_td(d):
        return CAL[CAL < pd.Timestamp(d)][-1]

    RW = pd.read_csv(os.path.join(OUT, "rows.csv"), dtype={"代號": str})
    ST = pd.read_csv(os.path.join(OUT, "stats.csv"))
    rep = {}
    cen = RW[RW["樣本"] == "普查"].copy()
    # (a)
    LCR = pd.read_csv("backtest/resultsLampCensus/rows.csv", dtype={"代號": str})
    LCR = LCR[(LCR["段"] == "燈1") & (LCR["H"].astype(str) == "末")][["訊號", "代號", "R", "大盤", "結算日"]]
    nt = cen[cen["未到"].astype(bool)].merge(LCR, on=["訊號", "代號"], suffixes=("", "_LC"))
    rep["(a)未到件對普查到末日"] = {"件": len(nt), "R最大差": float((nt["全抱R"] - nt["R"]).abs().max()), "大盤最大差": float((nt["全抱大盤"] - nt["大盤"]).abs().max()),
                              "結算日不同": int((nt["全抱結算日"] != nt["結算日"]).sum())}
    # (b)
    rec = []
    for _, r in cen.iterrows():
        sid = r["代號"]; e = r["進場日"]; x = r["全抱結算日"]
        Rf = ratio(sid, e, "open", x, "close") - 1 - COST
        Mf = tri(x) / tri(prev_td(e)) - 1
        o = {"訊號": r["訊號"], "代號": sid, "Rf": Rf, "Mf": Mf, "dRf": Rf - r["全抱R"], "dMf": Mf - r["全抱大盤"]}
        Hf = int(r["全抱H"])
        o["af"] = ann(Rf, Hf)
        if bool(r["觸發"]):
            s = r["賣出日"]
            Rs = ratio(sid, e, "open", s, "open") - 1 - COST
            Ms = tri(prev_td(s)) / tri(prev_td(e)) - 1
            o.update({"Rs": Rs, "dRs": Rs - r["賣R"], "dMs": Ms - r["賣大盤"]})
            a_s = ann(Rs, int(r["賣H"]))
            o["H1"] = (a_s + o["af"]) / 2
            o["d份"] = 0.5 * (Rs - Ms) - 0.5 * (Rf - Mf)
            # (d)
            d, A = px(sid)
            end = min(pd.Timestamp(s) + pd.DateOffset(months=12), pd.Timestamp(x))
            win = d[(d.index >= pd.Timestamp(s)) & (d.index <= end)]
            mx = max(ratio(sid, s, "open", dd, "close") for dd in win.index if np.isfinite(win.at[dd, "close"]) and win.at[dd, "close"] > 0)
            o["又漲1倍"] = bool(mx - 1 >= 1.0)
        else:
            o["H1"] = o["af"]; o["d份"] = 0.0; o["又漲1倍"] = False
        o["d"] = o["H1"] - o["af"]
        o["dd"] = o["d"] - r["d"]
        rec.append(o)
    B = pd.DataFrame(rec)
    rep["(b)原始價重算"] = {"件": len(B), "全抱R最大差": float(B["dRf"].abs().max()), "大盤最大差": float(B["dMf"].abs().max()),
                        "賣R最大差": float(B["dRs"].abs().max()) if "dRs" in B else 0.0, "賣大盤最大差": float(B["dMs"].abs().max()) if "dMs" in B else 0.0,
                        "d最大差": float(B["dd"].abs().max()), "超過1e-6件": int(((B[["dRf", "dMf", "dd"]].abs() > TOL).any(axis=1)).sum())}
    # (c)
    cen = cen.merge(B[["訊號", "代號", "d", "d份", "又漲1倍"]], on=["訊號", "代號"], suffixes=("", "_chk"))
    cc = {}
    for ver in ("甲", "乙"):
        for ty in ("全部", "缺貨", "新需求", "政策"):
            ev = cen[cen[ver].astype(bool)]
            ev = ev if ty == "全部" else ev[ev["型"] == ty]
            sg = ev.groupby("訊號").agg(d=("d_chk", "mean"), d份=("d份_chk", "mean"))
            row = ST[(ST["樣本"] == "普查") & (ST["組"] == ver) & (ST["型"] == ty)].iloc[0]
            mine = {"d中位(訊號)": float(sg["d"].median()), "d平均(訊號)": float(sg["d"].mean()), "dP25(訊號)": float(np.percentile(sg["d"], 25)),
                    "dP75(訊號)": float(np.percentile(sg["d"], 75)), "d最好(訊號)": float(sg["d"].max()), "d最壞(訊號)": float(sg["d"].min()),
                    "d份中位(訊號)": float(sg["d份"].median()), "觸發數": int(ev["觸發"].astype(bool).sum()), "緊接版觸發數": int(ev["緊接版觸發"].astype(bool).sum()),
                    "賣後12月又漲≥1倍": int(ev["又漲1倍"].sum())}
            diffs = {k: (abs(v - float(row[k])) if isinstance(v, float) else int(v != int(row[k]))) for k, v in mine.items()}
            cc[f"{ver}{ty}"] = {"最大差": max(diffs.values()), "不同欄": [k for k, v in diffs.items() if v > TOL],
                                "門檻描述句(重算)": bool(mine["d平均(訊號)"] >= 0 and mine["d中位(訊號)"] > 0), "門檻描述句(主)": bool(row["門檻描述句成立"])}
    old = RW[RW["樣本"] == "舊31段"]
    for var in ("代表股版", "同業等權版"):
        ev = old[old["版"] == var]
        dd = (ev["H1年化"] - ev["全抱年化"] - ev["d"]).abs().max()
        sg = ev.groupby("訊號")["d"].mean()
        row = ST[(ST["樣本"] == "舊31段") & (ST["組"] == var) & (ST["結果類"] == "全部") & (ST["型"] == "全部")].iloc[0]
        cc[var] = {"d欄自洽最大差": float(dd), "中位差": abs(float(sg.median()) - float(row["d中位(訊號)"])), "觸發數一致": int(ev["觸發"].sum()) == int(row["觸發數"])}
    rep["(c)彙總重算"] = cc
    ok = (rep["(a)未到件對普查到末日"]["R最大差"] < TOL and rep["(a)未到件對普查到末日"]["結算日不同"] == 0 and rep["(b)原始價重算"]["超過1e-6件"] == 0
          and all((v.get("最大差", 0) <= TOL and v.get("門檻描述句(重算)") == v.get("門檻描述句(主)")) if "最大差" in v else (v["中位差"] < TOL and v["觸發數一致"])
                  for v in cc.values()))
    rep["CHECK"] = "PASS" if ok else "FAIL"
    B.to_csv(os.path.join(OUT, "check_rows.csv"), index=False, encoding="utf-8-sig")
    json.dump(rep, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(rep, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
