# -*- coding: utf-8 -*-
"""PREREG突破過濾 本體——獨立查核（⛔ 不 import researchBF／researchX／researchH2）。

    python backtest/researchBF_check.py [--procs 2]

① 從 resultsBF/body_events.csv.gz 重算 14 格的 Δ、CR0 分群 SE（60 日區段）、95% CI、Bonferroni（0.05／14）區間、出口、結果句
   （結果句照登錄 seq2 §三 的表另寫一份），與 body_cells.csv 逐格比（浮點 ≤ 1e-12、字串逐字）。
② 從 main edc6f8002f 快照價格（backtest.data.load_stock：還原 OHLC）逐筆重算每一臂的 r60／r20／r120 與 0050 同段，
   與 body_events.csv.gz 逐筆比（≤ 1e-12）；沒買到 ⇒ 0；終點收盤 ＝ ≤ 終點最後一根有效 K 棒（本支自己 ffill）。
③ 重算 body_abandon.csv（買到比例、沒買到那批若照 A）與 body_vs0050.csv 的點估計。
輸出：resultsBF/body_check_indep.json；任一不符 ⇒ exit 1。
"""
from __future__ import annotations
import json
import os
import sys
from multiprocessing import Pool
from statistics import NormalDist

import numpy as np
import pandas as pd

SHA = "edc6f8002fed8803795e3486ad57db513f7e9f65"
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D          # noqa: E402  只用讀檔（⛔ 不用任何研究腳本）
D.DATA = os.path.expanduser(f"~/h2data/{SHA}/data")
OUT = "backtest/resultsBF"
W0 = "2017-03-02"
COST = 0.00585
TOL = 1e-12
ARMS = {"w": "BCDEF", "hs": "BCDEF", "box": "BDEF"}
FN = {"B": "幅度 3% 過濾", "C": "站穩 3 天過濾", "D": "放量 1.5 倍過濾", "E": "等回測頸線＋量縮＋止跌 K", "F": "三道全加"}
BAD = []


def close(a, b):
    return (np.isnan(a) and np.isnan(b)) or abs(a - b) <= TOL * max(1.0, abs(b))


def cr0(x, g):
    x = np.asarray(x, float); m = x.mean()
    s = pd.Series(x - m).groupby(np.asarray(g)).sum().to_numpy()
    return m, float(np.sqrt((s ** 2).sum()) / len(x)), len(s)


def verdict(m, lo, hi, blo, ex, fname):
    """登錄 seq2 §三 結果句（本支獨立寫）。"""
    if ex == "出口①":
        return "—（出口①：樣本不足以分辨）"
    head = {"出口②": "樣本中等，", "出口③": ""}[ex]
    if not (lo > 0 or hi < 0):
        return head + "分不出來 ⇒ 直接買（突破隔天開盤）"
    if m > 0:
        if blo > 0:
            return head + "突破後加{}再買，比直接買平均好 {:.2f}%（Bonferroni 下界 {:+.2f}%）".format(fname, m * 100, blo * 100)
        return head + "單格過關、與多次嘗試分不開 ⇒ 直接買"
    return head + "加{}反而比較差：濾掉的比省下的多".format(fname)


_C = {}


def _init(cal):
    _C["cal"] = cal


def recompute(args):
    sid, market, rows = args
    cal = _C["cal"]
    st = D.load_stock(sid, market, cal)
    o = st.df["open"].to_numpy(float); c = st.df["close"].to_numpy(float)
    pos = {d: i for i, d in enumerate(cal.strftime("%Y-%m-%d"))}

    def last_close(end):
        k = end
        while k >= 0 and not np.isfinite(c[k]):
            k -= 1
        return c[k]
    out = []
    for r in rows:
        T = pos[r["T"]]
        res = {"_i": r["_i"]}
        for arm in "A" + ARMS[r["type"]]:
            e = r[f"entry_{arm}"]
            for H, col in ((60, "r60"), (20, "r20"), (120, "r120")):
                if H == 120 and not r["in120"]:
                    res[f"{col}_{arm}"] = np.nan; continue
                if not isinstance(e, str) or e == "" or pos[e] > T + H:
                    res[f"{col}_{arm}"] = 0.0
                else:
                    res[f"{col}_{arm}"] = last_close(T + H) / o[pos[e]] - 1.0 - COST
        out.append(res)
    return out


def main():
    procs = int(sys.argv[sys.argv.index("--procs") + 1]) if "--procs" in sys.argv else 2
    X = pd.read_csv(os.path.join(OUT, "body_events.csv.gz"), dtype={"sid": str, "T": str}, keep_default_na=False, na_values=[""], low_memory=False)
    for c_ in [c for c in X.columns if c.startswith("entry_")]:
        X[c_] = X[c_].fillna("")
    C = pd.read_csv(os.path.join(OUT, "body_cells.csv"))
    cal = D.load_calendar()
    w0 = int(cal.searchsorted(pd.Timestamp(W0)))
    rep = {}
    # ⓪ 區段欄
    tpos = cal.searchsorted(pd.to_datetime(X["T"]))
    ok0 = bool((((tpos - w0) // 60) == X["blk"].to_numpy()).all())
    rep["blk欄＝(T−窗起點)//60"] = ok0
    if not ok0:
        BAD.append("blk")
    # ② 逐筆重算報酬
    X["_i"] = np.arange(len(X))
    jobs = [(sid, g["market"].iloc[0], g.to_dict("records")) for sid, g in X.groupby("sid")]
    with Pool(procs, initializer=_init, initargs=(cal,)) as pool:
        res = [r for part in pool.map(recompute, jobs, chunksize=8) for r in part]
    R = pd.DataFrame(res).set_index("_i").sort_index()
    nbad = 0; ncmp = 0
    for col in R.columns:
        a = R[col].to_numpy(float); b = X[col].to_numpy(float)
        both = ~(np.isnan(a) & np.isnan(b))
        diff = np.abs(np.nan_to_num(a, nan=9e9) - np.nan_to_num(b, nan=-9e9))[both]
        nb = int((diff > TOL * np.maximum(1.0, np.abs(np.nan_to_num(b[both])))).sum())
        nbad += nb; ncmp += int(both.sum())
    rep["逐筆報酬重算"] = {"比對格數": ncmp, "不符": nbad}
    if nbad:
        BAD.append("逐筆報酬")
    b50 = D.load_stock("0050", "twse", cal).df
    o50 = b50["open"].to_numpy(float); c50 = pd.Series(b50["close"].to_numpy(float)).ffill().to_numpy(float)
    fo = np.flatnonzero(np.isfinite(o50))
    e50 = fo[np.searchsorted(fo, tpos + 1)]                  # T＋1 起第一個有開盤的日子（0050 分割停牌）
    bm = c50[tpos + 60] / o50[e50] - 1.0
    nb50 = int((np.abs(bm - X["bench60"].to_numpy(float)) > TOL).sum())
    rep["0050同段重算不符"] = nb50
    if nb50:
        BAD.append("0050")
    # ① 判定重算
    zb = NormalDist().inv_cdf(1 - 0.05 / 14 / 2)
    cells = []
    for typ in ("w", "hs", "box"):
        Y = X[X["type"] == typ]
        for arm in ARMS[typ]:
            d = Y[f"r60_{arm}"].to_numpy(float) - Y["r60_A"].to_numpy(float)
            m, se, k = cr0(d, Y["blk"])
            lo, hi = m - 1.96 * se, m + 1.96 * se
            blo = m - zb * se
            ne = min(len(d), k)
            ex = "出口①" if ne < 30 else ("出口②" if ne < 100 else "出口③")
            s = verdict(m, lo, hi, blo, ex, FN[arm])
            ref = C[(C["typ"] == typ) & (C["買法"] == arm)].iloc[0]
            same = (close(m, ref["Δ"]) and close(se, ref["SE"]) and close(lo, ref["CI95_lo"]) and close(hi, ref["CI95_hi"])
                    and close(blo, ref["Bonf_lo"]) and ex == ref["出口"] and s == ref["結果句"] and int(ref["事件數"]) == len(d) and int(ref["區段數"]) == k)
            cells.append({"格": f"{typ}_{arm}", "Δ": m, "SE": se, "Bonf_lo": blo, "出口": ex, "結果句": s, "與主程式相同": same})
            if not same:
                BAD.append(f"cell_{typ}_{arm}")
    rep["判定重算"] = cells
    rep["Bonferroni_z"] = zb
    # ③ 放棄組、0050
    AB = pd.read_csv(os.path.join(OUT, "body_abandon.csv"))
    nab = 0
    for _, r in AB.iterrows():
        typ = {"W 底": "w", "頭肩底": "hs", "箱型": "box"}[r["型態"]]
        Y = X[X["type"] == typ]; b = Y[f"entry_{r['買法']}"] != ""
        chk = [close(float(b.mean()), r["買到比例"])]
        if (~b).any():
            chk.append(close(float(Y.loc[~b, "r60_A"].mean()), r["沒買到那批_若照A"]))
        if b.any():
            chk.append(close(float(Y.loc[b, f"r60_{r['買法']}"].mean()), r["買到那批_平均報酬"]))
        nab += int(not all(chk))
    rep["放棄組重算不符列"] = nab
    V = pd.read_csv(os.path.join(OUT, "body_vs0050.csv"))
    nv = 0
    for _, r in V.iterrows():
        typ = {"W 底": "w", "頭肩底": "hs", "箱型": "box"}[r["型態"]]
        Y = X[X["type"] == typ]
        nv += int(not close(float((Y["r60_A"] + COST - Y["bench60"]).mean()), r["A毛−0050"]))
    rep["vs0050重算不符列"] = nv
    if nab or nv:
        BAD.append("abandon/vs0050")
    rep["全過"] = not BAD; rep["不符項"] = BAD
    json.dump(rep, open(os.path.join(OUT, "body_check_indep.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print(json.dumps({k: v for k, v in rep.items() if k != "判定重算"}, ensure_ascii=False, default=float))
    print("判定重算：{}／14 格與主程式相同".format(sum(c["與主程式相同"] for c in cells)))
    sys.exit(0 if not BAD else 1)


if __name__ == "__main__":
    main()
