# -*- coding: utf-8 -*-
"""稽核 §四 資料核對的查核腳本（台股策略線 稽核 seq1 sha c3aa47ca0c2f9eaa；⛔ 不重跑判定、不讀報酬以外的新東西）。回測線，2026-09-27。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/audit_s4/check.py

逐件從【檔案本身】重取 REPORT.md 表裡的每個事實：
  ① 各面板的量測日起迄、個數、eligible 列、sha256
  ② W1 家族 S1 訊號（researchAFC summary「S1訊號」月數）＝ 2017-03～2026-03 的 109 個月
  ③ 探索批：探索段切點 CUT、確認段 A 的 pos_end 常數（原始碼）
  ④ 219 主窗重跑：AND 訊號 2026-04～08 每月進場數（沒斷）；P12 系格（#5 P17、#8 P14）用的面板路徑（原始碼）
  ⑤ 含已下市：load_universe ∩ gate3 裡有多少檔已下市（snapshot stocks.csv 的 last_seen ＜ 日曆尾、或 delisted.csv）；各程式有沒有傳 tradable／delist（原始碼）
  ⑥ 0050 2026-03-02→2026-08-24 報酬（估計用）
輸出 backtest/audit_s4/check.json
"""
from __future__ import annotations
import hashlib, json, os, re, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchH2 as H2
B = os.path.expanduser("~/tw-p17/backtest")
D = H2.D


def src(f):
    return open(os.path.join(B, f), encoding="utf-8").read()


def main():
    out = {}; cal = D.load_calendar()
    for p in ("resultsp4/panel.csv.gz", "resultsAFC/panel.csv.gz", "resultsp9_engine/panel_ext.csv.gz"):
        q = pd.read_csv(os.path.join(B, p), usecols=["measure_date", "eligible"])
        out[p] = {"量測日起": q["measure_date"].min(), "量測日迄": q["measure_date"].max(), "個數": int(q["measure_date"].nunique()),
                  "eligible列": int(q["eligible"].astype(bool).sum()), "sha256": hashlib.sha256(open(os.path.join(B, p), "rb").read()).hexdigest()[:16]}
    S = json.load(open(os.path.join(B, "resultsAFC/summary.json"), encoding="utf-8"))
    out["W1_S1訊號"] = S["S1訊號"]
    s = src("researchExplore.py"); out["探索段_CUT"] = re.search(r'CUT = pd.Timestamp\("([0-9-]+)"\)', s).group(1)
    s = src("researchExploreConfirm.py"); out["確認段A_pos_end"] = re.search(r'"pos_end": "([0-9-]+)"', s).group(1)
    a = pd.read_csv(os.path.join(B, "resultsN17/sig_edc6f/and_signals.csv.gz"), usecols=["entry_pos"])
    m = pd.Series([str(cal[e])[:7] for e in a["entry_pos"]]).value_counts()
    out["AND_2026每月進場"] = {k: int(m.get(k, 0)) for k in ("2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08")}
    s = src("rerun17.py")
    out["rerun17_P12面板"] = re.search(r'panel = (os.path.join\(HERE, "resultsAFC", "panel.csv.gz"\)) if snap', s).group(1)
    out["傳 tradable／delist 給引擎"] = {f: ("delist=" in src(f) and "tradable=" in src(f)) for f in ("researchAFC.py", "researchD5.py", "researchExplore.py", "researchExploreConfirm.py", "rerun17.py", "listexit_lines.py")}
    U = D.load_universe(); G = H2.UG.gate3(pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str))
    U = U[U["stock_id"].isin(set(G["stock_id"]))]
    out["load_universe∩gate3"] = {"檔數": int(len(U)), "last_seen 早於日曆尾（已下市或停止）": int((U["last_seen"] < cal[-1]).sum())}
    bench = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy()).ffill().to_numpy(float)
    i0, i1 = cal.searchsorted(pd.Timestamp("2026-03-02")), cal.searchsorted(pd.Timestamp("2026-08-24"))
    out["0050_2026-03-02至08-24報酬"] = float(bench[i1] / bench[i0] - 1)
    json.dump(out, open(os.path.join(B, "audit_s4", "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
