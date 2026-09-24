# -*- coding: utf-8 -*-
"""資金費率讀取層（PREREGC2 §六①）——⭐ 報酬計算層的一部分，⛔ 不是共用引擎。

⛔⛔ 三條硬規矩（逐字出自 C2 v4 §六① 與資料庫線 1857／1936）：
  ① **逐列讀 funding_interval_hours**，⛔ 不可寫死 8（2023 年起部分交易對改 4／1 小時；
     ⭐ 實測 SOLUSDT 2022-11 就有 8／4／2 三種）
  ② last_funding_rate 是【小數】，⛔ 不是百分比（0.0001 ＝ 0.01%）
  ③ 月檔 absent（404）⇒ **該幣該月沒有永續合約** ⇒ ⛔ 不可當成費率 0
     ⇒ 要嘛拒絕該窗、要嘛把窗首切到第一個有檔的月；⛔ 不可靜默當 0
"""
from __future__ import annotations
import os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
FIXDIR = os.path.join(HERE, "fixtures_c2")
COLS = ["calc_time", "funding_interval_hours", "last_funding_rate"]


class FundingAbsent(Exception):
    """該幣該月沒有月檔 ⇒ ⛔ 不是費率 0，是【沒有永續合約】。"""


def load_month(sym: str, y: int, m: int, root: str | None = None) -> pd.DataFrame:
    p = os.path.join(root or FIXDIR, "{}USDT-{:04d}-{:02d}.csv".format(sym, y, m))
    if not os.path.exists(p):
        raise FundingAbsent("{}USDT {:04d}-{:02d} 沒有月檔（⛔ 不可當費率 0）".format(sym, y, m))
    d = pd.read_csv(p)
    if list(d.columns) != COLS:
        raise SystemExit("⛔ 表頭不是逐字的 {} ⇒ 收到 {}".format(COLS, list(d.columns)))
    d["ts"] = pd.to_datetime(d["calc_time"], unit="ms", utc=True)
    return d


def settlements(sym: str, months: list[tuple[int, int]], root: str | None = None) -> pd.DataFrame:
    """把幾個月接起來。⛔ 任何一個月 absent 就丟 FundingAbsent（⛔ 不跳過、不補 0）。"""
    return pd.concat([load_month(sym, y, m, root) for y, m in months], ignore_index=True)


def cum_cost(d: pd.DataFrame) -> float:
    """累計資金費率成本 ＝ Σ last_funding_rate（⭐ 逐列，⛔ 不依間隔加權、⛔ 不補值）。"""
    return float(d["last_funding_rate"].sum())


def interval_mix(d: pd.DataFrame) -> dict:
    return {int(k): int(v) for k, v in d["funding_interval_hours"].value_counts().items()}
