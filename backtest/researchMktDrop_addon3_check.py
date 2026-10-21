# -*- coding: utf-8 -*-
"""大跌 4 檔「分段加碼兩次」【獨立對帳】——回測線計算子代理，2026-10-21。⛔ 只讀結果夾、不改任何既有檔（只寫 resultsMktDrop_addon3/check.json）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMktDrop_addon3_check

C1 主程式 recon.csv 全部通過（含 addon2 重跑逐位元、K1／K2 ＝ addon2、曲線 ＝ 排名表）。
C2 另一條路：K3／K3s 逐事件報酬 ＝ 由 addon2/event_rows.csv 原檔（F9／乙／主）的「不加碼 ＋ T2 加碼份 ＋ T3 加碼份」÷ 份數自算（%.8g 精度內）；K1、K2 ＝ 原檔加碼後欄。
C3 曲線結構：K3 與 K1 在第一次 −10% 加碼日之前逐位元同、與 K2 在第一次 −5% 加碼日之前逐位元同；K3s 與 K3 在 2024-08-06 之前同；K0 與 K1 在第一次 −5% 加碼日之前同。
C4 事件層 summary.csv 由 event_rows.csv 自算相同（%.6g）；乙主臂 ⇒ 各臂持有天數 ＝ K0；最大帳面虧損 ≤ 0；加碼份數 ≤ 2。
C5 組合層 portfolio.csv：K0、K1、大盤、0050 兩窗 ＝ resultsBenchRejudge/rank.csv。
C6 策略鎖 25 支相符；既有檔未動（git diff 不含 researchMktDrop*.py、benchmark_rejudge.py、resultsMktDrop/、resultsBenchRejudge/）；新增檔在。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

REPO = os.path.expanduser("~/tw-p17")
OUT = os.path.join(REPO, "backtest/resultsMktDrop_addon3")
AD2 = os.path.join(REPO, "backtest/resultsMktDrop/addon2")


def main():
    J = {}; ok = True
    RC = pd.read_csv(os.path.join(OUT, "recon.csv"))
    J["C1"] = {"recon 列數": len(RC), "未通過": int((~RC["通過"].astype(bool)).sum())}
    ok &= J["C1"]["未通過"] == 0 and len(RC) >= 20
    EV = pd.read_csv(os.path.join(OUT, "event_rows.csv"), dtype={"事件日": str})
    E0 = pd.read_csv(os.path.join(AD2, "event_rows.csv"))
    E0 = E0[(E0["世界"] == "主") & (E0["候選"] == "F9") & (E0["方式"] == "乙") & (E0["出場"] == "主")]
    T2 = E0[E0["觸發"] == "T2"].set_index("事件日"); T3 = E0[E0["觸發"] == "T3"].set_index("事件日")
    mx = 0.0; n = 0
    for _, r in EV.iterrows():
        d = r["事件日"]; base = T2.loc[d, "不加碼_報酬"]
        a2 = T2.loc[d, "加碼份_報酬"] if (str(T2.loc[d, "加碼進場"]) == "True") else None
        a3 = T3.loc[d, "加碼份_報酬"] if (str(T3.loc[d, "加碼進場"]) == "True") else None
        same = (str(T2.loc[d, "加碼進場"]) == "True") and (str(T3.loc[d, "加碼進場"]) == "True") and T2.loc[d, "觸發日"] == T3.loc[d, "觸發日"]
        parts = {"K0": [], "K1": [a2], "K2": [a3], "K3": [a2, a3], "K3s": [a2] + ([] if same else [a3])}[r["臂"]]
        parts = [x for x in parts if x is not None]
        exp = (base + sum(parts)) / (1 + len(parts))
        mx = max(mx, abs(exp - r["報酬"])); n += 1
        if int(r["加碼份數"]) != len(parts):
            mx = max(mx, 1.0)
    J["C2"] = {"比對列": n, "最大差": mx}
    ok &= mx < 5e-8 and n == 18 * 5
    Z = np.load(os.path.join(OUT, "curves.npz")); dts = list(Z["dates"])
    TRG = pd.read_csv(os.path.join(OUT, "triggers.csv"), dtype=str)
    cal = pd.to_datetime(dts)

    def nxt(d):
        return int(cal.searchsorted(pd.Timestamp(d), side="right"))          # ta＋1 位置
    f5 = min(nxt(d) for d in TRG["−5%觸發日"].dropna()); f10 = min(nxt(d) for d in TRG["−10%觸發日"].dropna()); fs = nxt("2024-08-05")
    J["C3"] = {"第一次 −5% 加碼日": dts[f5], "第一次 −10% 加碼日": dts[f10],
               "K3＝K1 至 −10% 前": bool(np.array_equal(Z["K3"][:f10], Z["K1"][:f10])), "K3≠K1 之後": bool(not np.array_equal(Z["K3"], Z["K1"])),
               "K3＝K2 至 −5% 前": bool(np.array_equal(Z["K3"][:f5], Z["K2"][:f5])),
               "K3s＝K3 至 2024-08-06 前": bool(np.array_equal(Z["K3s"][:fs], Z["K3"][:fs])),
               "K0＝K1 至 −5% 前": bool(np.array_equal(Z["K0"][:f5], Z["K1"][:f5]))}
    ok &= all(v for k, v in J["C3"].items() if isinstance(v, bool))
    SM = pd.read_csv(os.path.join(OUT, "summary.csv"), dtype=str)
    bad = 0; trig = set(TRG.loc[TRG["−5%觸發日"].notna(), "事件日"])
    for _, s in SM[SM["段"] != "2006～2014"].iterrows():
        q = EV[EV["臂"] == s["臂"]]
        q = q if s["段"] == "2015～" else q[q["段"] == s["段"]]
        if s["子集"] != "全部事件":
            q = q[q["事件日"].isin(trig)]
        r_ = q["報酬"].to_numpy(float)
        for col, v in (("平均", r_.mean()), ("中位", np.median(r_)), ("最差", r_.min()), ("最大帳面虧損_最差", q["最大帳面虧損"].min()),
                       ("最低帳面損益（首次＝1）_最差", q["最低帳面損益（首次＝1）"].min())):
            bad += int(abs(float(s[col]) - v) > 5e-6 * max(1, abs(v)))
        bad += int(int(s["虧＞10%次數"]) != int((r_ < -0.10).sum()))
    hd = EV.pivot(index="事件日", columns="臂", values="持有天數")
    J["C4"] = {"summary 自算不符": bad, "持有天數 各臂 ＝ K0": bool(all((hd[k] == hd["K0"]).all() for k in hd.columns)),
               "最大帳面虧損 ≤ 0": bool((EV["最大帳面虧損"] <= 0).all()), "加碼份數 ≤ 2": bool((EV["加碼份數"] <= 2).all())}
    ok &= bad == 0 and J["C4"]["持有天數 各臂 ＝ K0"] and J["C4"]["最大帳面虧損 ≤ 0"] and J["C4"]["加碼份數 ≤ 2"]
    PO = pd.read_csv(os.path.join(OUT, "portfolio.csv")); RK = pd.read_csv(os.path.join(REPO, "backtest/resultsBenchRejudge/rank.csv"))
    nm = {"K0 不加碼": "大跌 4 檔（甲：撥 20%、不加碼）", "K1 只在 −5% 加一次（現行）": "大跌 4 檔（甲：撥 20%、−5% 加碼同一批）", "大盤（報酬指數）": "大盤（報酬指數）", "0050": "0050"}
    mx = 0.0; nn = 0
    for w in ("確認", "探索"):
        for a, b in nm.items():
            p = PO[(PO["窗"] == f"排名表 {w}") & (PO["策略"] == a)].iloc[0]; q = RK[(RK["段"] == w) & (RK["策略"] == b)].iloc[0]
            mx = max(mx, abs(p["年化"] - q["年化"]), abs(p["最大回落"] - q["回落"])); nn += 1
    J["C5"] = {"比對": nn, "最大差": mx}
    ok &= mx < 5e-6 and nn == 8
    lk = subprocess.run([sys.executable, "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True, cwd=REPO)
    dif = subprocess.run(["git", "-C", REPO, "diff", "--name-only"], capture_output=True, text=True).stdout.split()
    touched = [f for f in dif if f.startswith(("backtest/researchMktDrop", "backtest/benchmark_rejudge", "backtest/resultsMktDrop/", "backtest/resultsBenchRejudge/"))]
    unt = subprocess.run(["git", "-C", REPO, "status", "--short", "--untracked-files=all", "backtest/researchMktDrop_addon3.py", "backtest/researchMktDrop_addon3_check.py",
                          "backtest/resultsMktDrop_addon3"], capture_output=True, text=True).stdout.splitlines()
    J["C6"] = {"策略鎖": lk.stdout.strip(), "既有檔被動": touched, "新增（未追蹤）": len(unt)}
    ok &= lk.returncode == 0 and "25 支" in lk.stdout and not touched and len(unt) >= 3
    J["全部通過"] = bool(ok)
    json.dump(J, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(J, ensure_ascii=False, indent=1, default=str))
    if not ok:
        raise SystemExit("⛔ 對帳不過")


if __name__ == "__main__":
    main()
