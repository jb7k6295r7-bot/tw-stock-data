# -*- coding: utf-8 -*-
"""每日「持股歷史同狀態」行 same_state_<資料日>.md（情報 1219：跟 daily 一起產、07:15 前到；台股 seq346／seq348 §三）——回測線，2026-09-29。

    建表（一次；之後固定，要不要更新由裁定定）：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.same_state --build-table
    每日查表：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.same_state --data <archive>/data --sha <main sha>
    （run_daily_list.sh 在 daily 產檔／略過之後呼叫；失敗只記 log、不影響 daily）

⛔ 描述、不判、不計 N。狀態定義、格、統計一字照 researchHoldState（7db449131d）：
   A 收盤相對 MA60 × MA60 方向（對 20 根前）｜B 收盤相對 MA20｜C 最新可用月營收創 24 月新高（p4_features.rev_hi24_flags）｜
   D 近 5 個交易日三大法人合計（stocks_inst total）＞ 0｜E 距 250 根最高收盤 三級；「上」用嚴格 ＞
 表 ＝ resultsHoldState/cell_table.csv：主窗（狀態日 2017-03-01～2026-08-31）96 格 × 20／60／120 天的統計＋「全部」對照列；
      由 researchHoldState 全量明細 rows_main.npz 一次算出（本支 --build-table），⭐ 之後每天只查表、不重掃
 每日：持股清單 ＝ backtest/holdings_same_state.txt（一行一個代號，輸出照檔內順序；清單變動由情報來信、協調者改檔；⛔ 不讀情報的資料夾）
      只算持股在最新資料日 t 的狀態（價格＝archive 的 data/；法人＝`git show <sha>:data/stocks_inst/<代號>.csv`，daily 的 archive 沒收 stocks_inst）
 輸出 backtest/resultsDaily/same_state_<t>.md：與 researchHoldState 的 LINE 行逐字同格式（情報要求「維持現行行格式」）
 測試掛鉤：環境變數 SAME_STATE_FAKE_FAIL=1 ⇒ 直接失敗（給 run_daily_list.sh 驗「same_state 失敗不拖累 daily」）
"""
from __future__ import annotations

import argparse
import glob
import io
import os
import subprocess
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
from . import data as D
from . import research11 as R11
from . import p4_features as P4F

TABLE = os.path.join(HERE, "resultsHoldState", "cell_table.csv")
HOLD = os.path.join(HERE, "holdings_same_state.txt")
OUT = os.path.join(HERE, "resultsDaily")
EARLY_REV = os.path.expanduser("~/earlydata/3edc0e2206/main/data/mops/revenue_hist")
HEAD = "歷史同狀態的平均分佈，不是對這一檔的預測"
HS = (20, 60, 120)
ALL = -9                                                          # 「全部股票任一天」列的格碼
P = lambda x: "—" if x is None or not np.isfinite(x) else f"{x * 100:+.1f}%"
Q = lambda x: "—" if x is None or not np.isfinite(x) else f"{x * 100:.0f}%"


# ═════════════ 建表 ═════════════
def build_table():
    from . import researchHoldState as RH
    import json
    S = json.load(open(os.path.join(HERE, "resultsHoldState", "summary.json"), encoding="utf-8"))
    D.DATA = os.path.expanduser(f"~/h2data/{S['main']}/data")
    cal = D.load_calendar()
    Z = np.load(os.path.join(HERE, "resultsHoldState", "rows_main.npz"))
    T = pd.DataFrame({k: Z[k] for k in ("d", "A", "B", "C", "D", "E", "R20", "R60", "R120", "X20", "X60", "X120")})
    T["sid"] = Z["sid"]; T["月"] = np.array([str(x)[:7] for x in cal[T["d"].to_numpy()]])
    rows = []
    for key, g in [((ALL,) * 5, T)] + list(T.groupby(["A", "B", "C", "D", "E"])):
        if key != (ALL,) * 5 and min(key) < 0:
            continue                                                 # 狀態不明（C／D 缺）不成格
        r = dict(zip(("A", "B", "C", "D", "E"), (int(k) for k in key)))
        for h in HS:
            st = RH.stats(g, h)
            for k, v in st.items():
                r[f"{k}_{h}"] = v
        rows.append(r)
    tb = pd.DataFrame(rows)
    hdr = [f"# 持股歷史同狀態 查表（researchHoldState 7db449131d 全量明細 rows_main.npz；main {S['main'][:10]}）",
           f"# 期間：狀態日 {S['資料']['主窗']['狀態日'][0]}～{S['資料']['主窗']['狀態日'][1]}（主窗、W1 eligible ∩ gate3 innov_ky 開）；報酬 ＝ 收盤到收盤 20／60／120 交易日、還原價",
           f"# 產表：{pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）；⛔ 固定不動，要不要更新由裁定定｜A＝B＝C＝D＝E＝{ALL} ⇒ 全部股票任一天（對照）"]
    with open(TABLE, "w", encoding="utf-8") as f:
        f.write("\n".join(hdr) + "\n")
        tb.to_csv(f, index=False, float_format="%.17g")
    # 閘：持股 7 格查表 ＝ summary 全量數字
    bad = 0
    for s, r in S["持股"].items():
        stt = r["狀態"]
        row = tb[(tb["A"] == stt["A"]) & (tb["B"] == stt["B"]) & (tb["C"] == stt["C"]) & (tb["D"] == stt["D"]) & (tb["E"] == stt["E"])].iloc[0]
        for h in HS:
            for k in ("n", "上漲機率", "中位", "贏0050"):
                if row[f"{k}_{h}"] != r["主窗"][str(h)][k]:
                    bad += 1
    print(f"[建表] {len(tb)} 列（含對照）→ {TABLE}｜持股 7 格 × 3 期 × 4 項 查表 ≠ 全量：{bad}")
    return bad


# ═════════════ 每日 ═════════════
def state_of(sid, mk, cal, flag_col, inst_csv):
    B = R11.load_bars(sid, mk, cal)
    idx, cb = B["idx"], B["c"]; n = len(cal)
    ma60 = pd.Series(cb).rolling(60).mean().to_numpy(); ma20 = pd.Series(cb).rolling(20).mean().to_numpy()
    hi = pd.Series(cb).rolling(250).max().to_numpy(); i = len(cb) - 1
    A = 2 * int(cb[i] > ma60[i]) + int(ma60[i] > ma60[i - 20]); Bc = int(cb[i] > ma20[i])
    dist = cb[i] / hi[i] - 1; E = 0 if dist >= -0.10 else (1 if dist >= -0.30 else 2)
    v = flag_col[idx[i]] if flag_col is not None else np.nan
    C = int(v == 100) if np.isfinite(v) else -1
    Dc = -1
    if inst_csv is not None:
        it = pd.read_csv(io.StringIO(inst_csv), dtype={"date": str}, usecols=["date", "total"]).drop_duplicates("date", keep="last")
        tot = pd.to_numeric(it.set_index(pd.to_datetime(it["date"]))["total"], errors="coerce").reindex(cal).fillna(0.0).to_numpy()
        first = int(cal.searchsorted(pd.to_datetime(it["date"]).min()))
        Dc = int(tot[idx[i] - 4:idx[i] + 1].sum() > 0) if idx[i] - 4 >= first else -1
    return {"日": str(cal[idx[i]].date()), "A": A, "B": Bc, "C": C, "D": Dc, "E": E}


def daily(data, sha):
    if os.environ.get("SAME_STATE_FAKE_FAIL") == "1":
        raise SystemExit("⛔ SAME_STATE_FAKE_FAIL=1（測試用：故意失敗）")
    D.DATA = data
    cal = D.load_calendar(); asof = str(cal[-1].date())
    meta = pd.read_csv(os.path.join(data, "meta", "stocks.csv"), dtype=str).set_index("stock_id")
    sids = [x.strip() for x in open(HOLD, encoding="utf-8") if x.strip() and not x.startswith("#")]
    fs = sorted(glob.glob(os.path.join(EARLY_REV, "*.csv"))) + sorted(glob.glob(os.path.join(data, "mops", "revenue_hist", "*.csv")))
    df = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收"]) for f in fs])
    df = df[df["stock_id"].isin(sids)].copy()
    df["rev"] = pd.to_numeric(df["當月營收"], errors="coerce"); df = df.drop_duplicates(["stock_id", "period"], keep="last")
    fl = P4F.rev_hi24_flags(df.pivot(index="period", columns="stock_id", values="rev").sort_index(), cal)
    tb = pd.read_csv(TABLE, comment="#")
    L = [f"【持股：歷史同狀態】{HEAD}（資料 {asof}；比對 2017～2026 全市場同狀態的股票）"]
    for s in sids:
        nm = meta.loc[s, "name"] if s in meta.index else s
        if s not in meta.index or meta.loc[s, "market"] not in ("twse", "tpex"):
            L.append(f"{s} {nm}：不是上市櫃普通股，沒有同格歷史"); continue
        r = subprocess.run(["git", "-C", REPO, "show", f"{sha}:data/stocks_inst/{s}.csv"], capture_output=True, text=True)
        st = state_of(s, meta.loc[s, "market"], cal, fl[s].to_numpy(float) if s in fl.columns else None, r.stdout if r.returncode == 0 else None)
        if st["日"] != asof:
            L.append(f"{s} {nm}：資料日 {asof} 沒有成交（最後一根 {st['日']}），今天不比"); continue
        if min(st["C"], st["D"]) < 0:
            L.append(f"{s} {nm}：{'營收' if st['C'] < 0 else '法人'}資料不明，今天不比"); continue
        m = tb[(tb["A"] == st["A"]) & (tb["B"] == st["B"]) & (tb["C"] == st["C"]) & (tb["D"] == st["D"]) & (tb["E"] == st["E"])]
        n60 = int(m["n_60"].iloc[0]) if len(m) and np.isfinite(m["n_60"].iloc[0]) else 0
        if n60 == 0:
            L.append(f"{s} {nm}：歷史上沒有跟它同狀態的股票（格內 0 筆）"); continue
        z = m.iloc[0]
        L.append(f"{s} {nm}：歷史上跟它同狀態的股票，60 天後上漲 {Q(z['上漲機率_60'])}、中間值 {P(z['中位_60'])}、比 0050 好 {Q(z['贏0050_60'])}"
                 + ("（樣本少）" if n60 < 200 else ""))
    b = tb[(tb["A"] == ALL)].iloc[0]
    L.append(f"（對照：全部股票任一天，60 天後上漲 {Q(b['上漲機率_60'])}、中間值 {P(b['中位_60'])}、比 0050 好 {Q(b['贏0050_60'])}）")
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, f"same_state_{asof}.md")
    open(p, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(f"[same_state] {p}｜{len(sids)} 檔｜main {sha[:10]}")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--build-table", action="store_true"); ap.add_argument("--data"); ap.add_argument("--sha")
    a = ap.parse_args()
    if a.build_table:
        sys.exit(1 if build_table() else 0)
    daily(a.data, a.sha)


if __name__ == "__main__":
    main()
