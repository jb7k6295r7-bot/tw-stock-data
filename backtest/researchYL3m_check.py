# -*- coding: utf-8 -*-
"""營量營飆單月營收改三個月合計 seq2 的抽樣查核（獨立寫法）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYL3m_check

⛔ 不呼叫 research34／research13／researchYL3m 的函式：
  ① 自讀 edc6f 快照 data/mops/revenue_hist/*.csv（同 (代號, 期別) 取最後一列），以「曆月」往回數（⛔ 不用表格位置），
     抽 600 列面板（default_rng(20261011)）重算 單月 ≥ 前 24 月最大（24 月全有值）、三個月合計 ≥ 前 21 月內 19 個連續三月合計最大（24 月全有值）
     ⇒ 與 ~/pre5work/yl3m_panel_flags.csv.gz 逐列比
  ② 抽 600 筆強勢股訊號（signals_S.csv.gz）：自找「signal_pos ≤ 訊號根、距離 ≤ 45」的最新一期面板列，用 ① 的 3M 旗 ⇒ 是否在 3M 臂 AND 表，逐筆比
輸出 backtest/resultsYL3m/check.json
"""
from __future__ import annotations

import glob
import json
import os

import numpy as np
import pandas as pd

H2D = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
SIG = os.path.expanduser("~/tw-p17/backtest/resultsN17/sig_edc6f")
OUT = os.path.expanduser("~/tw-p17/backtest/resultsYL3m")


def ms(p, k):
    y, m = int(p[:4]), int(p[5:]); t = y * 12 + m - 1 + k
    return f"{t // 12:04d}-{t % 12 + 1:02d}"


def main():
    rng = np.random.default_rng(20261011)
    fs = sorted(glob.glob(os.path.join(H2D, "mops", "revenue_hist", "*.csv")))
    df = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收"]) for f in fs]).drop_duplicates(["stock_id", "period"], keep="last")
    V = {(s, p): float(v) for s, p, v in zip(df["stock_id"], df["period"], pd.to_numeric(df["當月營收"], errors="coerce"))}
    FL = pd.read_csv(os.path.join(os.path.expanduser("~/pre5work"), "yl3m_panel_flags.csv.gz"), dtype={"stock_id": str})
    idx = rng.choice(len(FL), 600, replace=False)
    bad1 = []; tr = [0, 0]

    def get(s, p):
        v = V.get((s, p), np.nan)
        return v if np.isfinite(v) else np.nan

    def flags(s, p):
        x = [get(s, ms(p, -k)) for k in range(0, 25)]          # x[0] ＝ 當月、x[k] ＝ k 月前
        one = bool(np.isfinite(x[0]) and all(np.isfinite(x[1:25])) and x[0] >= max(x[1:25]))
        w = x[0:24]
        three = False
        if all(np.isfinite(w)):
            cur = w[0] + w[1] + w[2]
            prev = [w[k] + w[k + 1] + w[k + 2] for k in range(3, 22)]
            three = bool(cur >= max(prev))
        return one, three
    for i in idx:
        r = FL.iloc[i]
        o, t = flags(r["stock_id"], r["period"])
        tr[0] += o; tr[1] += t
        if o != bool(r["one_ge"]) or t != bool(r["three_ge"]):
            bad1.append({"代號": r["stock_id"], "期": r["period"], "獨立": [o, t], "本體": [bool(r["one_ge"]), bool(r["three_ge"])]})
    # ②
    S = pd.read_csv(os.path.join(SIG, "signals_S.csv.gz"), dtype={"sid": str}, usecols=["sid", "k", "pos"])
    A3 = pd.read_csv(os.path.expanduser("~/pre5work/and3m_signals.csv.gz"), dtype={"sid": str}, usecols=["sid", "k"])
    in3 = set(zip(A3["sid"], A3["k"].astype(int)))
    by = {s: g.sort_values("signal_pos") for s, g in FL.groupby("stock_id")}
    j = rng.choice(len(S), 600, replace=False); bad2 = []; npos = 0
    for i in j:
        s, k, pos = S.iloc[i]["sid"], int(S.iloc[i]["k"]), int(S.iloc[i]["pos"])
        g = by.get(s); f = False
        if g is not None:
            q = g[g["signal_pos"] <= pos]
            if len(q) and pos - int(q.iloc[-1]["signal_pos"]) <= 45:
                f = flags(s, q.iloc[-1]["period"])[1]
        npos += f
        if f != ((s, k) in in3):
            bad2.append({"代號": s, "k": k, "獨立": f, "本體": (s, k) in in3})
    res = {"① 面板抽樣": {"列": 600, "單月 True": tr[0], "3M True": tr[1], "不同": len(bad1), "明細": bad1[:10]},
           "② 訊號抽樣": {"筆": 600, "在 3M 臂": npos, "不同": len(bad2), "明細": bad2[:10]}, "過": not bad1 and not bad2}
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
