# -*- coding: utf-8 -*-
"""H1 半賣 seq1 頻率表對帳（獨立重算觸發幾筆）——回測線計算子代理。⛔ 不算報酬、不 commit、不改既有檔。
獨立處：⛔ 不 import 主程式、bigrun_monthly、researchLampCensus；月營收直接讀 revpit 原始 csv（revenue_hist ＋ 每日版 revenue/<期>.csv，每日版優先）；
       交易日曆改用 market_tri.csv（PIN 版、截到面板尾）；S、P、確認全部重寫（逐月 for 迴圈，不用 rolling）。
沿用主程式輸出的：進場日、截斷日（壞根／下市；價格面板位置，本檔不重算）、面板尾、入選。
另報敏感度（描述）：① 去年同月改用 m−12 期自身 rev 當分母；② 確認窗只看 P 月之後緊接的 3 個月（不滑動）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchH1half_freq_check
"""
import glob
import json
import os
import re
import subprocess
from io import StringIO

import numpy as np
import pandas as pd

os.chdir(os.path.expanduser("~/tw-p17"))
OUT = "backtest/resultsH1half/freq"
PIN = "9b0e9882572c"
RP = os.path.expanduser(f"~/rtfwork/main_{PIN}/revpit")


def roc(p):
    return str((int(p[:4]) - 1911) * 100 + int(p[5:]))


def load_rev(codes):
    H = []
    for f in sorted(glob.glob(os.path.join(RP, "revenue_hist", "*.csv"))):
        x = pd.read_csv(f, dtype=str)
        x = x[x["stock_id"].isin(codes)]
        if len(x):
            H.append(x[["stock_id", "period", "當月營收", "去年當月營收"]].rename(columns={"當月營收": "rev", "去年當月營收": "ly"}))
    h = pd.concat(H).drop_duplicates(["stock_id", "period"], keep="last")
    D = []
    for f in sorted(glob.glob(os.path.join(RP, "revenue", "*.csv"))):
        b = os.path.basename(f)[:-4]
        if not re.fullmatch(r"\d{4}-\d{2}", b):
            continue
        x = pd.read_csv(f, dtype=str)
        x = x[(x["資料年月"].astype(str).str.strip() == roc(b)) & (x["period"].astype(str) == b) & x["stock_id"].isin(codes)]
        D.append(pd.DataFrame({"stock_id": x["stock_id"], "period": b, "rev": x["營業收入-當月營收"], "ly": x["營業收入-去年當月營收"]}))
    d = pd.concat(D).drop_duplicates(["stock_id", "period"], keep="last")
    R = {}
    for sid in codes:
        a = h[h["stock_id"] == sid].set_index("period")[["rev", "ly"]].apply(pd.to_numeric, errors="coerce")
        b = d[d["stock_id"] == sid].set_index("period")[["rev", "ly"]].apply(pd.to_numeric, errors="coerce")
        for p, r in b.iterrows():
            if np.isfinite(r["rev"]):
                a.loc[p] = r                                  # 每日版優先
        R[sid] = a.sort_index()
    return R


def S_of(tab, p, mode):
    """mode 'ly'＝同列去年當月；'own'＝m−12 期自身 rev。"""
    num = den = 0.0
    for k in range(3):
        q = str(pd.Period(p, "M") - k)
        if q not in tab.index:
            return np.nan
        rv = tab.at[q, "rev"]
        if mode == "ly":
            l = tab.at[q, "ly"]
        else:
            q12 = str(pd.Period(q, "M") - 12)
            l = tab.at[q12, "rev"] if q12 in tab.index else np.nan
        if not (np.isfinite(rv) and np.isfinite(l)):
            return np.nan
        num += rv; den += l
    return num / den - 1 if den > 0 else np.nan


def main():
    meta = json.load(open(os.path.join(OUT, "main.json"), encoding="utf-8"))
    tail = pd.Timestamp(meta["面板尾"])
    T = pd.read_csv(StringIO(subprocess.run(["git", "show", f"{PIN}:data/history/market_tri.csv"], capture_output=True, text=True).stdout))
    CAL = pd.DatetimeIndex(sorted(pd.to_datetime(T["date"]).unique())); CAL = CAL[CAL <= tail]

    def ftd(ts):
        k = CAL.searchsorted(pd.Timestamp(ts))
        return CAL[k] if k < len(CAL) else None

    EV = pd.read_csv(os.path.join(OUT, "events.csv"), dtype={"代號": str})
    EV = EV[EV["入選"].astype(str) == "True"].copy()
    R = load_rev(sorted(EV["代號"].unique()))
    rows = []
    for _, r in EV.iterrows():
        ent = pd.Timestamp(r["進場日"])
        ems = (ent.to_period("M") + 60).to_timestamp(); E = ftd(ems)
        if E is not None and E.to_period("M") != ems.to_period("M"):
            E = None
        lim = E if E is not None else tail + pd.Timedelta(days=1)
        trunc = pd.Timestamp(r["截斷日"]) if isinstance(r["截斷日"], str) and r["截斷日"] else tail
        out = {}
        for mode in ("ly", "own"):
            tab = R[r["代號"]]
            # 可用月
            m = ent.to_period("M") - 3
            while True:
                j = ftd((m + 1).to_timestamp() + pd.Timedelta(days=12))
                if j is None or j > ent:
                    break
                m += 1
            ms, ss, js = [], [], []
            while True:
                j = ftd((m + 1).to_timestamp() + pd.Timedelta(days=12))
                if j is None or j >= lim:
                    break
                ms.append(m); js.append(j); ss.append(S_of(tab, str(m), mode)); m += 1
            res = {"觸發": False}
            for slide in (True, False):
                hit = None; P = np.nan; Pk = -1
                for k in range(len(ss)):
                    if k >= 3 and np.isfinite(P) and P > 0:
                        w = ss[k - 2:k + 1]
                        ok = all(np.isfinite(x) and x < P for x in w) and (w[2] <= P / 2 or w[2] <= 0)
                        if ok and (slide or k - 3 == Pk):
                            hit = k; break
                    # 每輪結尾把 ss[k−2] 併入累計最高 ⇒ 下一輪 k+1 檢查時 P＝m0～(k+1)−3 的最高（同值取最早）
                    if k - 2 >= 0 and np.isfinite(ss[k - 2]) and (not np.isfinite(P) or ss[k - 2] > P):
                        P = ss[k - 2]; Pk = k - 2
                if hit is not None and js[hit] < lim and js[hit] <= trunc:
                    res[("滑動" if slide else "緊接")] = (str(ms[hit]), float(P), str(js[hit].date()))
                else:
                    res[("滑動" if slide else "緊接")] = None
            out[mode] = res
        a = out["ly"]["滑動"]
        rows.append({"樣本": r["樣本"], "組": r["版本"] if r["樣本"] == "普查" else r["版"], "甲": r["甲"], "乙": r["乙"], "訊號": r["訊號"], "代號": r["代號"],
                     "主_結果": r["結果"], "主_確認月": r["確認月"], "主_P": r["P"], "主_J日": r["J日"],
                     "chk_觸發": a is not None, "chk_確認月": a[0] if a else "", "chk_P": a[1] if a else np.nan, "chk_J日": a[2] if a else "",
                     "own_觸發": out["own"]["滑動"] is not None, "own_確認月": out["own"]["滑動"][0] if out["own"]["滑動"] else "",
                     "緊接_觸發": out["ly"]["緊接"] is not None})
    C = pd.DataFrame(rows)
    C["主_觸發"] = C["主_結果"] == "觸發"
    C["一致"] = (C["主_觸發"] == C["chk_觸發"]) & ((~C["主_觸發"]) | ((C["主_確認月"] == C["chk_確認月"]) & (abs(C["主_P"] - C["chk_P"]) < 1e-9) &
                                                               (C["主_J日"] == C["chk_J日"])))
    C.to_csv(os.path.join(OUT, "check_rows.csv"), index=False, encoding="utf-8-sig")
    summ = {}
    for lab, sub in (("普查甲", C[(C["樣本"] == "普查") & (C["甲"].astype(str) == "True")]), ("普查乙", C[(C["樣本"] == "普查") & (C["乙"].astype(str) == "True")]),
                     ("舊31段代表股版", C[C["組"] == "代表股版"]), ("舊31段同業等權版", C[C["組"] == "同業等權版"])):
        summ[lab] = {"件": len(sub), "主觸發": int(sub["主_觸發"].sum()), "check觸發": int(sub["chk_觸發"].sum()), "逐筆一致": int(sub["一致"].sum()),
                     "敏感①分母m−12自身rev觸發": int(sub["own_觸發"].sum()),
                     "敏感①確認月不同(兩者都觸發)": int(((sub["own_觸發"]) & (sub["chk_觸發"]) & (sub["own_確認月"] != sub["chk_確認月"])).sum()),
                     "敏感②只看緊接3月觸發": int(sub["緊接_觸發"].sum())}
    bad = C[~C["一致"]]
    summ["不一致"] = bad[["樣本", "組", "訊號", "代號", "主_結果", "主_確認月", "chk_確認月", "主_J日", "chk_J日"]].to_dict("records")
    json.dump(summ, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(summ, ensure_ascii=False, indent=1, default=str))
    print("CHECK", "PASS" if bad.empty else f"FAIL {len(bad)}")


if __name__ == "__main__":
    main()
