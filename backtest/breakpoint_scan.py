"""全母體掃斷點，並與資料庫線的 `data/meta/par_change.csv`（24 筆／22 檔）對帳。

    python3 -m backtest.breakpoint_scan            # 印統計，寫 results/breakpoints_scan.csv

規則在 `data.breakpoints`（K線線 2026-09-09 三訂：①比值 ≤ 0.55／≥ 1.8、②連續缺 ≥ 5 個交易日，
且區間 (前一次有成交, 這一次有成交] 內無 data/adj/ 事件）。這支只讀不改。
對帳的期待：par_change.csv 的 24 筆**全部**要被規則抓到（漏掉任何一筆就是規則寫錯）；
規則多抓的是「不論成因都算斷點」的其他長停牌，另列出來看。
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

from . import data as D

RESULTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


def main():
    cal = D.load_calendar()
    uni = D.load_universe()
    rows = []
    all_holes: list[dict] = []
    adj_dates: dict[str, set] = {}
    for sid, market in zip(uni["stock_id"], uni["market"]):
        st = D.load_stock(sid, market, cal)
        if st is None:
            continue
        for b in D.breakpoints(st.df, st.event_dates):
            rows.append({"stock_id": sid, "market": market, "date": cal[b["pos"]].strftime("%Y-%m-%d"),
                         "prev_date": cal[b["prev_pos"]].strftime("%Y-%m-%d"), "ratio": round(b["ratio"], 4),
                         "missing_trading_days": b["gap"], "rule": b["rule"]})
        adj_dates[sid] = st.event_dates
        # 附表：所有 ≥ GAP_MIN 且無事件的洞（不論流動性）
        c = st.df["close"].to_numpy(float); v = st.df["volume"].to_numpy(float)
        tr = np.flatnonzero(~np.isnan(c))
        if len(tr) >= 2:
            p_, t_ = tr[:-1], tr[1:]
            ev = np.array(sorted(pd.Timestamp(x) for x in st.event_dates), dtype="datetime64[ns]")
            idx = st.df.index.values.astype("datetime64[ns]")
            for k in np.flatnonzero((t_ - p_ - 1) >= D.GAP_MIN):
                if len(ev) and np.searchsorted(ev, idx[t_[k]], side="right") > np.searchsorted(ev, idx[p_[k]], side="right"):
                    continue
                w = v[max(0, p_[k] - D.GAP_LIQ_WINDOW + 1):p_[k] + 1]; w = w[~np.isnan(w)]
                med = float(np.median(w)) if len(w) else float("nan")
                all_holes.append({"stock_id": sid, "market": market, "date": cal[t_[k]].strftime("%Y-%m-%d"),
                                  "prev_date": cal[p_[k]].strftime("%Y-%m-%d"), "ratio": round(float(c[t_[k]] / c[p_[k]]), 4),
                                  "missing_trading_days": int(t_[k] - p_[k] - 1), "median_vol_60d": med,
                                  "liq_ok": bool(len(w) and med >= D.GAP_LIQ_SHARES)})
    bp = pd.DataFrame(rows, columns=["stock_id", "market", "date", "prev_date", "ratio", "missing_trading_days", "rule"])
    os.makedirs(RESULTS, exist_ok=True)
    bp.to_csv(os.path.join(RESULTS, "breakpoints_scan.csv"), index=False)
    # 附表（給資料層看，不進回測判準）：所有「缺 ≥ 5 日且區間內無事件」的洞，不論流動性，另加 liq_ok 欄。
    # 條件②的流動性前提是 K線線裁的回測／判讀判準；資料層要列「有沒有公司行動缺口」時不該被它濾掉（CODE 09:40 Q1，3073 那種）。
    holes = pd.DataFrame(all_holes, columns=["stock_id", "market", "date", "prev_date", "ratio", "missing_trading_days", "median_vol_60d", "liq_ok"])
    holes.to_csv(os.path.join(RESULTS, "holes_scan.csv"), index=False)
    print(f"附表 holes_scan.csv：缺 ≥ {D.GAP_MIN} 日且無事件的洞 {len(holes)} 個、{holes['stock_id'].nunique()} 檔；其中 liq_ok {int(holes['liq_ok'].sum())} 個（＝ 進斷點清單的 gap 規則）")
    print(f"母體 {len(uni)} 檔，斷點 {len(bp)} 個、{bp['stock_id'].nunique()} 檔")
    print(bp["rule"].value_counts().to_string())
    if len(bp):
        print("missing_trading_days 分布：", bp["missing_trading_days"].describe()[["min", "50%", "max"]].to_dict())

    pc_path = os.path.join(D.DATA, "meta", "par_change.csv")
    if not os.path.exists(pc_path):
        print("（沒有 data/meta/par_change.csv，略過對帳）")
        return 0
    pc = pd.read_csv(pc_path, dtype={"stock_id": str})
    key = set(zip(bp["stock_id"], bp["date"]))
    # 每一筆面額變更只能有兩種狀態：data/adj/ 已有因子（→ 不是斷點，正確）或 規則抓到（→ 仍是斷點，等因子）；
    # 兩者都不是 ＝ 規則寫錯（漏抓）。
    status = []
    for s, d in zip(pc["stock_id"], pc["event_date"]):
        ev = adj_dates.get(s, set())
        has_factor = any(abs((pd.Timestamp(e) - pd.Timestamp(d)).days) <= 12 for e in ev)   # 因子日應等於復牌日；留 12 日容錯給停牌區間
        status.append("factor" if has_factor else ("breakpoint" if (s, d) in key else "MISSED"))
    pc["status"] = status
    cnt = pc["status"].value_counts().to_dict()
    print(f"\n對帳 par_change.csv：{len(pc)} 筆／{pc['stock_id'].nunique()} 檔 → 已有因子 {cnt.get('factor', 0)}、仍為斷點 {cnt.get('breakpoint', 0)}、漏抓 {cnt.get('MISSED', 0)}")
    miss = pc[pc["status"] == "MISSED"]
    if len(miss):
        print("⛔ 漏抓（既無因子、規則也沒抓到）：\n" + miss[["stock_id", "event_date", "ratio"]].to_string(index=False))
    pcs = set(zip(pc["stock_id"], pc["event_date"]))
    extra = bp[[(s, d) not in pcs for s, d in zip(bp["stock_id"], bp["date"])]]
    print(f"規則另外抓到（不在 par_change.csv）：{len(extra)} 個、{extra['stock_id'].nunique()} 檔；其中 price 規則 {int((extra['rule'] != 'gap').sum())} 個")
    with pd.option_context("display.width", 160, "display.max_rows", 200):
        print(extra.to_string(index=False))
    return 1 if len(miss) else 0


if __name__ == "__main__":
    sys.exit(main())
