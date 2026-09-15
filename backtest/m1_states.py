"""PREREGM1 層一的狀態訊號、去抖與有效樣本數——同一件事只有一份實作（researchm1 與前置 n 表都 import 這裡）。

    python3 -m backtest.m1_states [--index CSV] [--col close] [--k 20]

訊號（PREREGM1 §二、K線分析 09-14 1935 裁定）：
  a  收盤 vs 240MA（上／下）
  b  近 60 日報酬正負（正／負）
  ab a∧b 三態：同向多（上∧正）／同向空（下∧負）／不同向
  c  20 日實現波動率在過去 500 日的歷史分位（>70% 高／30～70% 中／<30% 低）；分位只用【過去 499 日】，不含當日
  d  月線方向：該月狀態＝上月收盤 vs 上上月收盤（多／空），月初即可得、不看本月，日展開
去抖（M1 §〇，K線分析 1935 採用）：連續長度 < K 的區段【併入前一段】（第一段沒有前一段 ⇒ 保留），再合併相鄰同狀態。
有效 n ＝ 去抖後的切換次數（＝ 段數 − 1；最後一段未結束，本來就不構成一次切換）。
⚠ 檢查有效樣本數定義的第一件事：把雜訊加大，n 不可以往上走（selftest_m1_states.py）。
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
K_DEFAULT = 20
SIGNALS = ("a", "b", "ab", "c", "d")
LABELS = {"a": "a 收盤 vs 240MA", "b": "b 近 60 日報酬正負", "ab": "a∧b 三態", "c": "c 20 日波動 500 日分位三態", "d": "d 月線方向（日展開）"}


def signals(close: pd.Series) -> dict[str, pd.Series]:
    """close：DatetimeIndex（交易日）、已 ffill、全正。回傳五條狀態序列（object，NaN＝尚不可得）。"""
    c = close.astype(float)
    ma240 = c.rolling(240, min_periods=240).mean()
    a = (c > ma240).where(ma240.notna()).map({True: "上", False: "下"})
    r60 = c / c.shift(60) - 1
    b = (r60 > 0).where(r60.notna()).map({True: "正", False: "負"})
    ab = pd.Series(np.where((a == "上") & (b == "正"), "同向多", np.where((a == "下") & (b == "負"), "同向空", "不同向")), index=c.index, dtype=object).where(a.notna() & b.notna())
    rv20 = np.log(c).diff().rolling(20).std() * np.sqrt(250)
    pct = rv20.rolling(500, min_periods=500).apply(lambda x: float((x[:-1] < x[-1]).mean()), raw=True)
    cc = pd.Series(np.where(pct > 0.7, "高", np.where(pct < 0.3, "低", "中")), index=c.index, dtype=object).where(pct.notna())
    m = c.resample("ME").last()
    dm = (m > m.shift(1)).where(m.shift(1).notna()).map({True: "多", False: "空"})
    dm.index = dm.index.to_period("M")
    per = c.index.to_period("M")
    d = pd.Series([dm.get(p - 1, np.nan) for p in per], index=c.index, dtype=object)
    return {"a": a, "b": b, "ab": ab, "c": cc, "d": d}


def segments(s: pd.Series) -> pd.DataFrame:
    """去掉 NaN 後的連續同狀態區段：state、len、start（區段第一天）。"""
    s = s.dropna()
    grp = (s != s.shift()).cumsum()
    g = s.groupby(grp)
    return pd.DataFrame({"state": g.first(), "len": g.size(), "start": g.apply(lambda x: x.index[0])}).reset_index(drop=True)


def debounce(s: pd.Series, k: int = K_DEFAULT) -> pd.DataFrame:
    """M1 去抖：< k 的區段併入前一段，再合併相鄰同狀態。回傳去抖後的區段表。"""
    seg = segments(s)
    states, lens, starts = [], [], []
    for st, ln, t0 in zip(seg["state"], seg["len"], seg["start"]):
        if ln < k and states:
            lens[-1] += int(ln); continue
        states.append(st); lens.append(int(ln)); starts.append(t0)
    ms, ml, mt = [], [], []
    for st, ln, t0 in zip(states, lens, starts):
        if ms and ms[-1] == st:
            ml[-1] += ln
        else:
            ms.append(st); ml.append(ln); mt.append(t0)
    return pd.DataFrame({"state": ms, "len": ml, "start": mt})


def n_table(close: pd.Series, k: int = K_DEFAULT) -> pd.DataFrame:
    rows = []
    for key in SIGNALS:
        s = signals(close)[key]
        raw = max(len(segments(s)) - 1, 0)
        db = debounce(s, k)
        n = max(len(db) - 1, 0)
        comp = db.iloc[:-1]
        by = comp.groupby("state").size().to_dict() if len(comp) else {}
        last = db.iloc[-1] if len(db) else None
        rows.append({"signal": key, "label": LABELS[key], "raw_switches": raw, "n": n, "n_by_state": by,
                     "seg_len_median": int(db["len"].median()) if len(db) else 0, "seg_len_min": int(db["len"].min()) if len(db) else 0, "seg_len_max": int(db["len"].max()) if len(db) else 0,
                     "last_state": None if last is None else str(last["state"]), "last_len": None if last is None else int(last["len"]),
                     "first_date": str(s.dropna().index[0].date()) if s.notna().any() else None, "judge": "可跑" if n >= 24 else "還沒測（n < 24）"})
    return pd.DataFrame(rows)


def load_series(path: str | None, col: str = "close") -> pd.Series:
    if path is None:
        sys.path.insert(0, os.path.dirname(HERE))
        from backtest import data as D
        cal = D.load_calendar()
        return pd.Series(D.load_benchmark(cal)["close"].to_numpy(float), index=cal).ffill()
    df = pd.read_csv(path, parse_dates=["date"]).sort_values("date")
    return pd.Series(df[col].to_numpy(float), index=pd.DatetimeIndex(df["date"])).ffill()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", default=None, help="指數 CSV（date,<col>）；不給就用 0050 還原收盤（data.load_benchmark）")
    ap.add_argument("--col", default="close"); ap.add_argument("--k", type=int, default=K_DEFAULT)
    a = ap.parse_args()
    c = load_series(a.index, a.col)
    t = n_table(c, a.k)
    print(f"序列 {'0050 還原收盤' if a.index is None else a.index}：{c.index[0].date()} ～ {c.index[-1].date()}，{len(c):,} 日；K＝{a.k}")
    for r in t.itertuples():
        print(f"{r.label}: 素切換 {r.raw_switches}｜去抖後 n＝{r.n} {r.n_by_state}｜段長 中位 {r.seg_len_median} 最短 {r.seg_len_min} 最長 {r.seg_len_max}｜最後一段 {r.last_state} {r.last_len} 日（未結束）｜起算 {r.first_date}｜{r.judge}")


if __name__ == "__main__":
    main()
