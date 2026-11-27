# -*- coding: utf-8 -*-
"""scan55 step 1：日線面板（只價量，⛔ 不算任何報酬統計）。
重用：backtest.data（load_universe、load_calendar、load_stock）、backtest.research11.load_bars（還原價、壞根 next_bad、漲跌停旗標）。
輸出 cache/panel.npz：日曆 × 股票 float32 矩陣。
"""
import os, re, sys
from multiprocessing import Pool
import numpy as np, pandas as pd
from backtest import data as D
from backtest import research11 as R11
import snap; D = snap.fix()

HERE = snap.BASE   # 沒設 SCAN_BASE 時＝本檔所在資料夾（同 64 格）
CACHE = os.path.join(HERE, "cache"); os.makedirs(CACHE, exist_ok=True)
KEYS = ["C", "O", "H", "L", "V", "A", "RC", "SH", "LIM1", "UP", "BAD", "VALID"]


def one(args):
    sid, market, cal = args
    n = len(cal)
    out = {k: np.full(n, np.nan, np.float32) for k in KEYS}
    p = os.path.join(D.DATA, "stocks", f"{sid}.csv")
    if not os.path.exists(p):
        return sid, None, "no_file"
    raw = pd.read_csv(p, dtype={"date": str}, usecols=lambda c: c in ("date", "close", "limit", "shares", "valid_bar", "market"))
    raw["date"] = pd.to_datetime(raw["date"]); raw = raw.drop_duplicates("date").set_index("date").sort_index()
    raw = raw.reindex(cal)
    out["RC"] = pd.to_numeric(raw["close"], errors="coerce").to_numpy(np.float32)
    out["SH"] = pd.to_numeric(raw["shares"], errors="coerce").to_numpy(np.float32)
    lim = raw["limit"].astype(str)
    out["LIM1"] = np.where(raw["close"].isna(), np.nan, lim.isin(["up", "down"]).astype(float)).astype(np.float32)
    b = R11.load_bars(sid, market, cal)
    note = "load_bars"
    if b is not None:
        idx = b["idx"]; df = b["df"]
        for k, src in (("C", "c"), ("O", "o"), ("H", "h"), ("L", "l"), ("A", "amt")):
            out[k][idx] = b[src]
        out["V"] = df["volume"].to_numpy(np.float32)
        out["UP"][idx] = b["up"].astype(np.float32)
        nb = b["next_bad"]; nn = len(idx)
        bad = np.array([nb[k] == k for k in range(nn)], dtype=np.float32)
        out["BAD"][:] = 0; out["BAD"][idx] = bad
        out["VALID"] = df["traded"].to_numpy(np.float32)
    else:
        st = D.load_stock(sid, market, cal)
        if st is None:
            return sid, None, "no_stock"
        df = st.df
        note = "fallback(<260 bars)"
        for k, src in (("C", "close"), ("O", "open"), ("H", "high"), ("L", "low"), ("A", "amount"), ("V", "volume")):
            out[k] = df[src].to_numpy(np.float32)
        tr = df["traded"].to_numpy()
        out["VALID"] = tr.astype(np.float32)
        out["BAD"][:] = 0
        ti = np.flatnonzero(tr)
        if len(ti) > 1:
            gap = np.diff(ti) - 1
            out["BAD"][ti[1:][gap >= 5]] = 1
        for bp in D.breakpoints(df, st.event_dates):
            if D.applies(bp):
                out["BAD"][bp["pos"]] = 1
    # valid_bar 欄：有就一併要求 =1
    if "valid_bar" in raw:
        vb = pd.to_numeric(raw["valid_bar"], errors="coerce").to_numpy()
        out["VALID"] = np.where((out["VALID"] == 1) & (vb == 1), 1, 0).astype(np.float32)
    return sid, out, note


def main():
    snap.check(); print("D.DATA =", D.DATA, "SHA", snap.SHA, flush=True)
    cal = D.load_calendar()
    uni = D.load_universe()
    uni = uni[uni["stock_id"].str.fullmatch(r"\d{4}")].reset_index(drop=True)
    sids = uni["stock_id"].tolist(); mk = uni["market"].tolist()
    procs = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    res = {}
    notes = {}
    with Pool(procs) as pool:
        for i, (sid, out, note) in enumerate(pool.imap(one, [(s, m, cal) for s, m in zip(sids, mk)], chunksize=8)):
            notes[sid] = note
            if out is not None:
                res[sid] = out
            if i % 200 == 0:
                print(i, sid, note, flush=True)
    keep = [s for s in sids if s in res]
    arr = {k: np.stack([res[s][k] for s in keep], axis=1) for k in KEYS}
    np.savez(os.path.join(CACHE, "panel.npz"), cal=cal.values.astype("datetime64[D]").astype(str), sids=np.array(keep), **arr)
    uni[uni.stock_id.isin(keep)].to_csv(os.path.join(CACHE, "universe_meta.csv"), index=False)
    pd.Series(notes).to_csv(os.path.join(CACHE, "panel_notes.csv"))
    print("done", len(keep), "of", len(sids), pd.Series(notes).value_counts().to_dict())


if __name__ == "__main__":
    main()
