# -*- coding: utf-8 -*-
"""美股合理價機械版——頻率表換資料版差異（b7572463c → 89d9f8550；裁定 seq481 §二）。⛔ 不算任何報酬。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSFairValue_freq_diff

讀：舊版 resultsUSFairValue/freq_b7572463/（freq_by_eval.csv、freq_summary.json；repo 內）＋ 私有逐檔明細 ~/us_work/fairvalue/b7572463/；
    新版 resultsUSFairValue/freq/ ＋ ~/us_work/fairvalue/classify_by_eval_ticker.csv。
寫：resultsUSFairValue/freq/freq_diff_b7572463.json（只放筆數、中位數、代號層級的變動筆數；⛔ 不寫價格、財報值）。
變動歸因（每筆 (評估日,檔) 只歸一類，依序）：★19 分段 CIK 代號（IR、DD、BHGE、FTI）→ ★20 多類股 6 檔 → 其他（資料庫第二輪修補、價格檔更新等）。
"""
from __future__ import annotations

import json
import os
from collections import Counter

import numpy as np
import pandas as pd

from backtest import researchUSFairValue_freq as FQ

OLD_D = os.path.join(os.path.dirname(FQ.OUTD), "freq_b7572463")
OLD_PRIV = os.path.join(FQ.PRIVD, "b7572463", "classify_by_eval_ticker.csv")
NEW_PRIV = os.path.join(FQ.PRIVD, "classify_by_eval_ticker.csv")
COLS = ("名冊在指數", "在指數無價格", "財報對不上公司", "市值不可算", "市值<100億", "母體", "全過", "過門檻全部", "可買", "接近", "偏貴")


def label(R):
    g = R["group"].where(R["val"] == "ok", "不在組") if "val" in R else pd.Series("不在組", index=R.index)
    st = R["stage"].fillna("")
    g = g.where(st == "pop", "非母體:" + st)
    return dict(zip(zip(R["eval"], R["ticker"]), g.fillna("不在組")))


def main():
    T0 = pd.read_csv(os.path.join(OLD_D, "freq_by_eval.csv"), encoding="utf-8-sig", dtype={"eval": str})
    T1 = pd.read_csv(os.path.join(FQ.OUTD, "freq_by_eval.csv"), encoding="utf-8-sig", dtype={"eval": str})
    S0 = json.load(open(os.path.join(OLD_D, "freq_summary.json"), encoding="utf-8"))
    S1 = json.load(open(os.path.join(FQ.OUTD, "freq_summary.json"), encoding="utf-8"))
    assert S1["資料commit"] == FQ.DATA_COMMIT_FULL
    assert list(T0["eval"]) == list(T1["eval"]), "評估日不同"
    per = []
    for (_, a), (_, b) in zip(T0.iterrows(), T1.iterrows()):
        r = {"eval": a["eval"]}
        for c in COLS:
            r[c] = [int(a[c]), int(b[c])]
        per.append(r)
    med = {c: {"舊": float(T0[c].median()), "新": float(T1[c].median()),
               "舊_總和": int(T0[c].sum()), "新_總和": int(T1[c].sum())} for c in COLS}
    small = {G: {"舊": int((T0[G] < 3).sum()), "新": int((T1[G] < 3).sum())} for G in ("可買", "偏貴")}
    # 逐檔變動（私有明細只拿來計數）
    R0 = pd.read_csv(OLD_PRIV, dtype={"eval": str, "ticker": str}, low_memory=False)
    R1 = pd.read_csv(NEW_PRIV, dtype={"eval": str, "ticker": str}, low_memory=False)
    a, b = label(R0), label(R1)
    seg = set(FQ.cik_segments())
    six = set(FQ.CLASS_PICK)
    ch = {"★19分段CIK": Counter(), "★20多類股6檔": Counter(), "其他": Counter()}
    tick = {"★19分段CIK": Counter(), "★20多類股6檔": Counter(), "其他": Counter()}
    for k in sorted(set(a) | set(b)):
        x, y = a.get(k, "不在名冊"), b.get(k, "不在名冊")
        if x == y:
            continue
        cat = "★19分段CIK" if k[1] in seg else ("★20多類股6檔" if k[1] in six else "其他")
        ch[cat]["%s→%s" % (x, y)] += 1
        tick[cat][k[1]] += 1
    grp = ("可買", "接近", "偏貴")
    moves = {cat: {"變動(評估日,檔)": int(sum(c.values())),
                   "組別變動(進出三組或換組)": int(sum(v for kk, v in c.items() if any(g in kk for g in grp))),
                   "種類": dict(c.most_common()), "代號數": len(tick[cat]),
                   "變動最多的代號": dict(tick[cat].most_common(25))} for cat, c in ch.items()}
    gate = {}
    for k in ("r1", "r2", "r3", "r4"):
        m = R0[R0["stage"] == "pop"].merge(R1[R1["stage"] == "pop"], on=["eval", "ticker"], suffixes=("_0", "_1"))
        gate[k] = dict(Counter("%s→%s" % (p, q) for p, q in zip(m[k + "_0"], m[k + "_1"]) if p != q))
    out = {
        "說明": "b7572463c → 89d9f8550 頻率表差異（⛔ 無報酬）。中位＝每評估日檔數的中位數；[舊, 新]。",
        "資料commit": {"舊": S0["資料commit"], "新": S1["資料commit"]},
        "評估日數": len(T1),
        "每評估日檔數_中位與總和": med,
        "樣本不足_組<3檔的評估日數": small,
        "樣本不足_觸發": {"舊": S0["樣本不足"]["觸發"], "新": S1["樣本不足"]["觸發"]},
        "★15★16_筆數": {
            "舊": {"權益用equity_incl_nci補_年": S0.get("權益用equity_incl_nci補★16_年"),
                  "EPS單季種類": S0.get("EPS單季種類筆數"),
                  "另讀法分組差異": S0.get("★15★16另一讀法（EPS 字面＋權益只用 equity）_分組差異", {}).get("變動筆數(評估日,檔)")},
            "新": {"權益用equity_incl_nci補_年": S1.get("權益用equity_incl_nci補★16_年"),
                  "EPS單季種類": S1.get("EPS單季種類筆數"),
                  "另讀法分組差異": S1.get("★15★16另一讀法（EPS 字面＋權益只用 equity）_分組差異", {}).get("變動筆數(評估日,檔)")}},
        "門檻狀態變動_(評估日,檔)": gate,
        "逐檔變動歸因": moves,
        "每評估日": per,
    }
    FQ.jdump(out, os.path.join(FQ.OUTD, "freq_diff_b7572463.json"))
    print(json.dumps({k: v for k, v in out.items() if k != "每評估日"}, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
