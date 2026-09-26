# -*- coding: utf-8 -*-
"""裁定 seq207 §一：營量 v1（#13：P1 AND｜N20｜d=inf｜relvol｜H60，⛔ 無大盤閘）每日候選清單（⛔ 只列訊號與日期，不算、不報任何報酬）。

    python3 -m backtest.list_yl13

⭐ 訊號與營飆 v1 名單同一管線（list_prereg10 build 的輸出 resultsList/and_signals_ext.csv.gz，⛔ 不重算）；差別只有：
  ① ⛔ 不套大盤閘（營量 v1 沒有 regime）
  ② 同一天候選多於空槽 ⇒ 照 relvol 大者先（引擎 pick="relvol"，同分照訊號表列序；rerun17 _sim_engine P1 路徑），⛔ 不抽籤
  ③ 20 槽；每檔金額 ＝ 總資金 ÷ 20（各半配時 ÷ 2 ÷ 20）；第 60 個交易日收盤賣（D.exit_pos(entry_pos, 60)）
  ④ 名單 ＝ 資料最後 20 個交易日內的 AND 訊號；已過進場日的照規則不補買（回測只算訊號隔天開盤買進）
  出場日超出資料日曆 ⇒ gate_b_status.future_trading_days 外推（未公告的休市只扣週末 ⇒ 實際只會更晚）
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from . import rerun17 as RR

RR.use_snapshot()
from . import data as D                 # noqa: E402
from . import gate_b_status as GB       # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsList")
HOLD = 60
N_SLOTS = 20


def main():
    cal = D.load_calendar(); n = len(cal)
    assert str(cal[-1].date()) == "2026-09-24", cal[-1]
    A = pd.read_csv(os.path.join(OUT, "and_signals_ext.csv.gz"), dtype={"sid": str})
    fut, basis = GB.future_trading_days(cal, 2 * HOLD + 10)
    cal_ext = cal.append(fut)
    stocks = pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str).drop_duplicates("stock_id").set_index("stock_id")
    Y = pd.read_csv(os.path.join(OUT, "list_PREREG10_1_2026-09-24.csv"), dtype={"stock_id": str}).set_index(["stock_id", "signal_date"])
    d = A[A["pos"] >= n - 20].copy()
    assert d["relvol"].notna().all(), "⛔ relvol 有缺"
    rows = []
    for r in d.itertuples():
        e = int(r.entry_pos); xp = D.exit_pos(e, HOLD)
        sd = str(cal[int(r.pos)].date())
        b = "資料日曆" if xp < n else basis[xp - n]
        if "只扣週末" in b:
            b += " ⇒ 實際只會更晚"
        y = Y.loc[(r.sid, sd)] if (r.sid, sd) in Y.index else None
        rows.append({"stock_id": r.sid, "name": stocks["name"].get(r.sid, ""), "market": stocks["market"].get(r.sid, ""),
                     "signal_date": sd, "batch": "最後交易日當天" if int(r.pos) == n - 1 else "近20交易日",
                     "entry_date": str(cal_ext[e].date()), "exit_date_60": str(cal_ext[xp].date()), "exit_basis": b,
                     "relvol": float(r.relvol),
                     "also_in_營飆v1": (None if y is None else bool(y["regime_list_t1"])),
                     "score": (None if y is None else int(y["score"])), "rev_period": (None if y is None else y["rev_period"])})
    L = pd.DataFrame(rows)
    # 同一進場日依 relvol 大者先排名（引擎 pick="relvol" 的次序；同分照訊號表列序 ⇒ 用 stable 排序＋原列序）
    L["_ord"] = np.arange(len(L))
    L = L.sort_values(["entry_date", "relvol", "_ord"], ascending=[True, False, True], kind="stable")
    L["rank_in_day"] = L.groupby("entry_date").cumcount() + 1
    L["status"] = np.where(L["batch"] == "最後交易日當天", "候選（次一交易日開盤可買；空槽多於候選時全買，少於時照 relvol 名次）",
                           "已過進場日 ⇒ 照規則不補買")
    L = L.drop(columns="_ord").sort_values(["signal_date", "rank_in_day"]).reset_index(drop=True)
    tag = str(cal[-1].date())
    p = os.path.join(OUT, f"list_YL13_{tag}.csv")
    L.to_csv(p, index=False, encoding="utf-8-sig")
    last = L[L["batch"] == "最後交易日當天"]
    print(f"[營量 v1 名單] 近 20 個交易日 {cal[n - 20].date()}～{cal[-1].date()}：{len(L)} 筆／{L['stock_id'].nunique()} 檔；"
          f"最後交易日當天 {len(last)} 筆（進場 {last['entry_date'].iloc[0] if len(last) else '—'}）")
    print(last[["stock_id", "name", "entry_date", "exit_date_60", "relvol", "rank_in_day", "also_in_營飆v1"]].to_string(index=False))
    print("營飆 v1 閘關（t−1）但營量 v1 照買的筆數：", int((L["also_in_營飆v1"] == False).sum()))
    print(p)


if __name__ == "__main__":
    main()
