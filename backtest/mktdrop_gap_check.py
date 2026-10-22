# -*- coding: utf-8 -*-
"""複核情報 2340 §二.2 引的下單清單限價依據（裁定 seq455 §三：不入登錄、只描述）——回測線開發子代理，2026-10-23。
⛔ 不算任何報酬；只數「開盤跳空超過門檻」的檔次比例。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.mktdrop_gap_check [--sha SHA] [--since 2015-01-01]

事件 ＝ backtest/resultsMktDrop/v1/events.csv（q2、接受；researchMktDrop_v1.index_events）事件日 ≥ since；收復日同檔（未收復的不算收復那半）。
母體 ＝ 唯讀快照 stocks/ 下四碼、非 0 開頭（排除 0050 類 ETF）的上市櫃股；兩天都有效（前收 ＞ 0、開盤 ＞ 0）才算一檔次。
 ① 事件隔天開盤 ＞ 事件日收盤 ×1.07 的檔次比例（買限價 +7% 會買不到的比例）
 ② 收復隔天開盤 ＜ 收復日收盤 ×0.95（及 ×0.98）的檔次比例（賣限價 −5%／−2% 會賣不到的比例）
未還原價（同下單清單口徑）；跨除權息日的前收未調整（事件隔天剛好除權息的檔次極少，附註）。
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess

import numpy as np
import pandas as pd

REPO = os.path.expanduser("~/tw-p17")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--sha", default=None); ap.add_argument("--since", default="2015-01-01")
    a = ap.parse_args()
    sha = a.sha or subprocess.run(["git", "-C", REPO, "rev-parse", "origin/main"], capture_output=True, text=True).stdout.strip()
    DATA = os.path.expanduser(f"~/h2data/{sha}/data")
    cal = pd.to_datetime(pd.read_csv(os.path.join(DATA, "meta", "calendar_twse.csv"), dtype=str).iloc[:, 0])
    cal = pd.DatetimeIndex(sorted(set(cal)))
    E = pd.read_csv(os.path.join(REPO, "backtest", "resultsMktDrop", "v1", "events.csv"), dtype=str)
    E = E[(E["定義"] == "q2") & (E["判定"] == "接受") & (pd.to_datetime(E["日期"]) >= pd.Timestamp(a.since))]
    pairs_up, pairs_dn = [], []
    for _, r in E.iterrows():
        t = pd.Timestamp(r["日期"]); k = int(cal.searchsorted(t))
        if k + 1 < len(cal) and cal[k] == t:
            pairs_up.append((cal[k], cal[k + 1]))
        if isinstance(r["收復日"], str) and r["收復日"]:
            d = pd.Timestamp(r["收復日"]); k = int(cal.searchsorted(d))
            if k + 1 < len(cal) and cal[k] == d:
                pairs_dn.append((cal[k], cal[k + 1]))
    need = sorted({x for p in pairs_up + pairs_dn for x in p})
    sids = sorted(f[:-4] for f in os.listdir(os.path.join(DATA, "stocks")) if re.fullmatch(r"[1-9]\d{3}\.csv", f))
    O = {}; C = {}
    for s in sids:
        df = pd.read_csv(os.path.join(DATA, "stocks", f"{s}.csv"), dtype={"date": str}, usecols=["date", "open", "close"]).drop_duplicates("date")
        df.index = pd.to_datetime(df["date"]); df = df.reindex(need)
        O[s] = pd.to_numeric(df["open"], errors="coerce").to_numpy(float); C[s] = pd.to_numeric(df["close"], errors="coerce").to_numpy(float)
    ix = {d: i for i, d in enumerate(need)}

    def rate(pairs, op, mult):
        n = hit = 0; per = []
        for d0, d1 in pairs:
            nn = hh = 0
            for s in sids:
                c, o = C[s][ix[d0]], O[s][ix[d1]]
                if c > 0 and o > 0:
                    nn += 1; hh += bool(o > c * mult) if op == ">" else bool(o < c * mult)
            n += nn; hit += hh; per.append(hh / nn if nn else np.nan)
        return hit, n, (hit / n if n else np.nan), float(np.nanmean(per)) if per else np.nan, len(pairs)

    out = [f"快照 {sha[:10]}｜事件 q2 接受、事件日 ≥ {a.since}：{len(pairs_up)} 次；有收復隔天資料的 {len(pairs_dn)} 次｜母體 四碼非 0 開頭 {len(sids)} 檔"]
    for name, pairs, op, m in (("事件隔天開盤 ＞ 前收 +7%", pairs_up, ">", 1.07), ("收復隔天開盤 ＜ 前收 −5%", pairs_dn, "<", 0.95),
                               ("收復隔天開盤 ＜ 前收 −2%", pairs_dn, "<", 0.98)):
        h, n, r_, pe, ne = rate(pairs, op, m)
        out.append(f"- {name}：{h:,}／{n:,} 檔次 ＝ {r_:.2%}（逐事件比例平均 {pe:.2%}；{ne} 次）")
    print("\n".join(out))


if __name__ == "__main__":
    main()
