# -*- coding: utf-8 -*-
"""每日名單「## 九、VIX 狀態」（使用者 10/20：「好」——VIX 飆高時提醒；描述，不是買賣建議）——回測線，2026-10-20。

    python3 -m backtest.vix_daily --md backtest/resultsDaily/daily_<資料日>.md     # 在名單檔尾加（或取代）第九節
    python3 -m backtest.vix_daily                                                  # 只印

資料：私有庫 ~/us-stock-data（origin/main）的 data/macro/fred_VIXCLS.csv（FRED VIXCLS 收盤，公開資料；"." 缺值列丟掉）。只讀，不寫私有庫。
段定義同 researchUSC13 C13-7：不在段內時 VIX 收盤 ≥ 門檻 ⇒ 段起；之後第一個收盤 ≤ 20 ⇒ 段止。門檻 30、40 各自一條。
輸出：
  平常：「VIX <日> 收盤 x（未達 30）」或段內狀態；
  段起當天 ≥40：「【LINE】⭐ …首次站上 40…」（情報推 LINE；⭐ 才推）；段起當天 30～40：一般行（不推）。
  歷史數字取自 resultsVIXbuy（commit ba6a596ccd）：首次 ≥40 隔天買 1 年平均 美股 +20.3%、0050 +40.1%；首次 ≥30 美股 +5.5%（平常 +12.4%）。
  VIX 最新日距今天（台北）> 4 個日曆日 ⇒ 加「⚠ VIX 資料停在 …」。
"""
from __future__ import annotations

import argparse
import io
import os
import re
import subprocess
import sys
import time

import pandas as pd

REPO = os.path.expanduser(os.environ.get("US_STOCK_REPO", "~/us-stock-data"))
PATH = "data/macro/fred_VIXCLS.csv"
TITLE = "## 九、VIX 狀態（FRED VIXCLS 收盤；描述，不是買賣建議）"


def load():
    subprocess.run(["git", "-C", REPO, "fetch", "-q", "origin", "main"], capture_output=True, timeout=120)
    t = subprocess.run(["git", "-C", REPO, "show", f"origin/main:{PATH}"], capture_output=True, text=True, check=True).stdout
    d = pd.read_csv(io.StringIO(t), dtype=str)
    d.columns = ["date", "v"]
    d = d[d["v"].str.strip() != "."].copy()
    d["date"] = pd.to_datetime(d["date"]); d["v"] = d["v"].astype(float)
    return d.sort_values("date").reset_index(drop=True)


def seg_start(v, th):
    """每一天：此日是否為門檻 th 的段起；以及最後一天時是否在段內與段起日索引。"""
    starts, inseg, s0 = [], False, None
    for i, x in enumerate(v):
        if not inseg and x >= th:
            inseg, s0 = True, i; starts.append(i)
        elif inseg and x <= 20:
            inseg, s0 = False, None
    return starts, inseg, s0


def lines(d, today=None):
    v = d["v"].to_list(); n = len(v) - 1; dt = d["date"].iloc[n].date(); x = v[n]
    L = [TITLE, ""]
    st30, in30, s30 = seg_start(v, 30); st40, in40, s40 = seg_start(v, 40)
    if st40 and st40[-1] == n:
        L.append(f"- 【LINE】⭐ VIX {dt} 收盤 {x:.2f}，首次站上 40（歷史：之後 1 年美股平均 +20%、0050 +40%，但買進後常再跌約兩成；樣本極少，描述不是建議）")
    elif st30 and st30[-1] == n:
        L.append(f"- VIX {dt} 收盤 {x:.2f}，首次站上 30（歷史上這時買，1 年後沒有比平常好：美股 +5.5% vs 平常 +12.4%）")
    elif in40:
        L.append(f"- VIX {dt} 收盤 {x:.2f}；本段曾 ≥40（{d['date'].iloc[s40].date()} 起），尚未回落到 20 以下")
    elif in30:
        L.append(f"- VIX {dt} 收盤 {x:.2f}；本段曾 ≥30（{d['date'].iloc[s30].date()} 起），尚未回落到 20 以下")
    else:
        L.append(f"- VIX {dt} 收盤 {x:.2f}（未達 30）")
    today = pd.Timestamp(today or time.strftime("%Y-%m-%d"))
    if (today - pd.Timestamp(dt)).days > 4:
        L.append(f"- ⚠ VIX 資料停在 {dt}（私有庫 fred_VIXCLS 未更新；提醒可能延遲）")
    return L + [""]


def put(md, L):
    s = open(md, encoding="utf-8").read()
    s = re.sub(r"\n## 九、VIX 狀態.*?(?=\n## |\Z)", "\n", s, flags=re.S).rstrip("\n") + "\n\n" + "\n".join(L)
    open(md, "w", encoding="utf-8").write(s)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--md"); ap.add_argument("--today")
    a = ap.parse_args()
    L = lines(load(), a.today)
    if a.md:
        put(a.md, L)
    print("\n".join(L))


if __name__ == "__main__":
    main()
