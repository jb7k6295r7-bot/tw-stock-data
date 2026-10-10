# -*- coding: utf-8 -*-
"""PREREG營量營飆同產業上限 —— 抽樣獨立查核（回測線計算子代理）。
⭐ 獨立寫法：⛔ 不 import researchYLindcap、researchIndRev_prereg、research11；產業直接讀 industry_pit.csv／industry.csv 自己判，持股由 ~/yicwork/ex.pkl 的逐筆區間重建。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLindcap_check [--n 400] [--seeds 20]

查：① 抽 n 個（股, 決策日）：產業分類（industry_pit 段 → 最後已知 → 現值）與主程式 Ind.at 的結果比（主程式結果取自 skipped.csv.gz 的產業欄＋ex.pkl 的被問紀錄重算）
    ② 營量 r0、營飆前 seeds 顆：每一筆「被跳過」當下，同產業持股（前一天以前買進、當天還沒賣 ＋ 當天排在前面已被接受的）確實 ≥ 3；
       每一筆「被接受」當下確實 ＜ 3；每個換股日收盤持股的同產業檔數 ≤ 3（新買那一檔所屬產業）
    ③ 被接受的候選 ＝ 實際買進（逐筆區間裡有當天買進的那一檔）；跳過的候選當天沒有買進
輸出 backtest/resultsYLindcap/check.json
"""
from __future__ import annotations

import argparse
import json
import os
import pickle

import numpy as np
import pandas as pd

OUT = os.path.expanduser("~/tw-p17/backtest/resultsYLindcap")
WORK = os.path.expanduser("~/yicwork")
H2D = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")


def ind_fn(DATA):
    p = pd.read_csv(os.path.join(DATA, "meta", "industry_hist", "industry_pit.csv"), dtype=str)
    seg = {}
    for s, ind, a, b in zip(p["stock_id"], p["industry"], p["start"], p["end"]):
        seg.setdefault(s, []).append((pd.Timestamp(a) if isinstance(a, str) and a else pd.Timestamp.min, pd.Timestamp(b) if isinstance(b, str) and b else pd.Timestamp.max, ind))
    cur = pd.read_csv(os.path.join(DATA, "meta", "industry.csv"), dtype=str).fillna("")
    now = {}
    for s, nm, code in zip(cur["stock_id"], cur["industry_name"], cur["industry_code"]):
        nm = nm or {"32": "文化創意業", "33": "農業科技業", "91": "存託憑證"}.get(code, "")
        if nm:
            now[s] = nm
    memo = {}

    def f(s, d):
        k = (s, d)
        if k in memo:
            return memo[k]
        sg = sorted(seg.get(s, []), key=lambda z: z[0]); r = None
        if sg:
            for a, b, ind in sg:
                if a <= d <= b:
                    r = ind; break
            if r is None:
                if d > sg[-1][1]:
                    r = sg[-1][2]
                elif d < sg[0][0]:
                    r = sg[0][2]
                else:
                    r = [z for z in sg if z[1] < d][-1][2]
        elif s in now:
            r = now[s]
        memo[k] = r
        return r
    return f


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=400); ap.add_argument("--seeds", type=int, default=20)
    a = ap.parse_args()
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    DATA = S["setup"]["產業資料"]
    IND = ind_fn(DATA)
    cal = pd.DatetimeIndex(pd.to_datetime(pd.read_csv(os.path.join(H2D, "meta", "calendar_twse.csv"))["date"]))
    X = pickle.load(open(os.path.join(WORK, "ex.pkl"), "rb")); EX = X["EX"]
    res = {}
    # ① 分類：被問紀錄裡的（股, t）抽 n 個，主程式產業 ＝ skipped.csv.gz（r0）；另比「被跳過 ⇔ 同產業 ≥ 3」用的是本檔分類
    SK = pd.read_csv(os.path.join(OUT, "skipped.csv.gz"), dtype={"sid": str})
    rng = np.random.default_rng(20261014)
    pick = rng.choice(len(SK), min(a.n, len(SK)), replace=False) if len(SK) else []
    d1 = []
    for i in pick:
        r = SK.iloc[int(i)]
        t = int(cal.searchsorted(pd.Timestamp(r["日"])))
        mine = IND(r["sid"], cal[t - 1])
        main_ = r["產業"] if isinstance(r["產業"], str) else None
        if mine != main_:
            d1.append({"sid": r["sid"], "日": r["日"], "本檔": mine, "主程式": main_})
    res["① 產業分類"] = {"抽": int(len(pick)), "不同": len(d1), "明細": d1[:20]}
    # ②③ 上限規則
    d2 = []; na = []; nchk = {"被跳過": 0, "被接受": 0, "換股日": 0}
    for f, nrun in (("vol", 1), ("fly", a.seeds)):
        for r in range(nrun):
            e = EX.get((f"{f}|cap", r))
            if e is None:
                continue
            iv = e["iv"]; rec = e["rec"]
            buys = {}
            for s, t0, t1 in iv:
                buys.setdefault(t0, set()).add(s)
            byday = {}
            for t, sid, i, av, ok in rec:
                byday.setdefault(t, []).append((i, sid, ok))
            for t, L in byday.items():
                L.sort()
                before = [s for s, t0, t1 in iv if t0 < t < t1]
                acc = []
                for i, sid, ok in L:
                    ind = IND(sid, cal[t - 1])
                    cnt = sum(1 for h in before + acc if IND(h, cal[t - 1]) == ind) if ind is not None else -1
                    if ok:
                        nchk["被接受"] += 1
                        if ind is not None and cnt >= 3:
                            d2.append({"策略": f, "r": r, "日": str(cal[t].date()), "sid": sid, "問題": f"被接受但同產業已 {cnt}"})
                        acc.append(sid)
                    else:
                        nchk["被跳過"] += 1
                        if ind is None or cnt < 3:
                            d2.append({"策略": f, "r": r, "日": str(cal[t].date()), "sid": sid, "問題": f"被跳過但同產業只有 {cnt}"})
                        if sid in buys.get(t, set()):
                            d2.append({"策略": f, "r": r, "日": str(cal[t].date()), "sid": sid, "問題": "被跳過卻買進"})
                bought = buys.get(t, set())
                if set(acc) - bought - set(before):
                    # 被接受但沒買到：只可能是現金不足（引擎 break）；照列
                    na.append({"策略": f, "r": r, "日": str(cal[t].date()), "sid": sorted(set(acc) - bought)})
            for t in sorted(buys):
                held = [s for s, t0, t1 in iv if t0 <= t < t1]
                for s in buys[t]:
                    ind = IND(s, cal[t - 1])
                    if ind is None:
                        continue
                    c = sum(1 for h in held if IND(h, cal[t - 1]) == ind)
                    nchk["換股日"] += 1
                    if c > 3:
                        d2.append({"策略": f, "r": r, "日": str(cal[t].date()), "sid": s, "問題": f"買進後同產業 {c} 檔"})
    res["②③ 上限規則"] = {"查": nchk, "不同": len(d2), "明細": d2[:30],
                         "被接受未買（另列、不算不同）": na,
                         "被接受未買說明": "引擎原規則：當天現金用盡（amt ≤ 0 ⇒ 停買），與上限無關；2025-09-17 營量 r0 那筆已另核：前一日收盤現金 0.0（權益全在持股）"}
    tot = len(d1) + len(d2)
    res["結論"] = f"產業分類抽 {res['① 產業分類']['抽']} 筆、上限規則查 被跳過 {nchk['被跳過']}／被接受 {nchk['被接受']}／新買 {nchk['換股日']} 筆（營量 r0＋營飆 {a.seeds} 顆），獨立重算 {tot} 筆不同（另 {len(na)} 筆被接受未買 ＝ 現金用盡，見說明）"
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(res, ensure_ascii=False, indent=1, default=str)[:3000])


if __name__ == "__main__":
    main()
