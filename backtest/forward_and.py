"""前瞻紀錄：凍結規則 AND（3/5 ∧ 最新一期月營收創 24 月新高）× H60 × N∈{30,40} 槽，從 2026-09-14 起逐日記帳、只追加不回改。
規則見 backtest/forward/RULE.md（PREREG10／11 的兩格，凍結）。

    python3 -m backtest.forward_and [--procs 4] [--start 2026-09-14] [--out backtest/forward] [--ns 30 40]

訊號（3/5）＝ research11.stock_features 主格；營收創高 ＝ research34.process_stock 的 rev_hi24（同閘門）；AND ＝ research13.and_flags。
⛔ 同一件事只有一份實作：本檔不重寫任何判準，只做「逐日記帳」。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import data as D
from . import research11 as R
from . import research13 as R13
from . import research34 as R34

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "forward")
START = "2026-09-14"
HOLD = 60
COST = R.COST
NS = [30, 40]
_W: dict = {}


def _init(cal, bench, disp, rev, rev_ly, rdates, lo, hi, start_pos):
    R._init(cal)
    R34._init(cal, bench, disp, rev, rev_ly, rdates, lo, hi)
    _W["start_pos"] = start_pos


def worker(args):
    """一檔：3/5 主格訊號（pos ≥ start−1）、G1 面板列、還原開收盤（日曆索引）、有效 K 棒位置。"""
    sid, market, first_seen, last_seen = args
    f = R.stock_features((sid, market, first_seen))
    if f is None:
        return None
    main = [r for r in f["main"] if r["pos"] >= _W["start_pos"] - 1]
    g = R34.process_stock((sid, market, first_seen, last_seen)) or []
    B = R.load_bars(sid, market, R._G["cal"])
    return {"sid": sid, "main": main, "g": [{"stock_id": sid, "signal_pos": r["signal_pos"], "rev_hi24": bool(r.get("rev_hi24") or False)} for r in g],
            "close": f["close"] if f["close"] is not None else pd.Series(B["df"]["close"].to_numpy()).ffill().to_numpy(np.float32),
            "open": f.get("open") if f["close"] is not None else B["df"]["open"].to_numpy(np.float32),
            "idx": B["idx"]}


def load_state(out, N):
    p = os.path.join(out, f"state_N{N}.json")
    if os.path.exists(p):
        return json.load(open(p, encoding="utf-8"))
    return {"N": N, "cash": 1.0, "equity": 1.0, "last_pos": None, "positions": []}


def save_state(out, st):
    with open(os.path.join(out, f"state_N{st['N']}.json"), "w", encoding="utf-8") as fh:
        json.dump(st, fh, ensure_ascii=False, indent=1)


def append_csv(path, rows, cols):
    if not rows:
        return
    df = pd.DataFrame(rows)[cols]
    df.to_csv(path, mode="a", index=False, header=not os.path.exists(path))


def run_engine(st, sig, series, cal, from_pos, to_pos):
    """逐日：先出（k+60 根收盤）、再進（次一有效 K 棒開盤，成交金額÷前 60 根中位數 大者先）、收盤市值。回傳 (權益列, 成交列, 進場的 (sid,pos))。"""
    N = st["N"]; cash = st["cash"]; eq_prev = st["equity"]; pos_list = st["positions"]
    by_entry = {t: g.sort_values("amt_ratio60", ascending=False) for t, g in sig.groupby("entry_pos")}
    eq_rows = []; trades = []; taken = []
    for t in range(from_pos, to_pos + 1):
        still = []
        for p in pos_list:
            s = series[p["sid"]]; idx = s["idx"]; kx = p["k"] + HOLD
            ep = float(s["open"][p["entry_pos"]])
            if kx < len(idx) and int(idx[kx]) <= t:
                x = int(idx[kx]); gross = float(s["close"][x]) / ep - 1
                cash += p["amt"] * (1 + gross - COST)
                trades.append({"sid": p["sid"], "signal_date": str(cal[p["pos"]].date()), "entry_date": str(cal[p["entry_pos"]].date()),
                               "exit_date": str(cal[x].date()), "bars": HOLD, "gross": gross, "net": gross - COST, "amt": p["amt"], "pnl": p["amt"] * (gross - COST)})
            else:
                still.append(p)
        pos_list = still
        g = by_entry.get(t)
        if g is not None and len(pos_list) < N:
            held = {p["sid"] for p in pos_list}
            slot = eq_prev / N
            for r in g.itertuples():
                if len(pos_list) >= N:
                    break
                if r.sid in held or r.sid not in series:
                    continue
                ep = float(series[r.sid]["open"][t])
                if not np.isfinite(ep) or ep <= 0:
                    continue
                amt = min(slot, cash)
                if amt <= 1e-9:
                    break
                cash -= amt
                pos_list.append({"sid": r.sid, "k": int(r.k), "pos": int(r.pos), "entry_pos": int(t), "amt": float(amt)}); held.add(r.sid); taken.append((r.sid, int(r.pos)))
        mv = sum(p["amt"] * float(series[p["sid"]]["close"][t]) / float(series[p["sid"]]["open"][p["entry_pos"]]) for p in pos_list)
        eq_prev = cash + mv
        eq_rows.append({"date": str(cal[t].date()), "equity": eq_prev, "cash": cash, "n_pos": len(pos_list), "slot_use": len(pos_list) / N})
    st["cash"] = cash; st["equity"] = eq_prev; st["positions"] = pos_list; st["last_pos"] = to_pos
    return eq_rows, trades, taken


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4); ap.add_argument("--start", default=START); ap.add_argument("--out", default=OUT)
    ap.add_argument("--ns", nargs="*", type=int, default=NS); ap.add_argument("--limit", type=int)
    ap.add_argument("--end", default=None, help="只記到這一天（測試續跑用；正式不用）")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()
    cal = D.load_calendar(); uni = D.load_universe()
    start_pos = int(cal.searchsorted(pd.Timestamp(a.start))); end_pos = len(cal) - 1
    if a.end:
        end_pos = min(end_pos, int(cal.searchsorted(pd.Timestamp(a.end), side="right")) - 1)
    states = {N: load_state(a.out, N) for N in a.ns}
    from_pos = min((st["last_pos"] + 1) if st["last_pos"] is not None else start_pos for st in states.values())
    now = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")
    sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=HERE).stdout.strip()
    log = [f"## {now}（台北）　資料到 {cal[end_pos].date()}　HEAD {sha}", ""]
    if from_pos > end_pos:
        for st in states.values():
            if st["last_pos"] is None:
                st["last_pos"] = start_pos - 1; save_state(a.out, st)
        log.append(f"- 沒有新交易日（起算 {a.start}，上次記到 {cal[from_pos - 1].date()}）；狀態檔已建立。")
        with open(os.path.join(a.out, "runlog.md"), "a", encoding="utf-8") as fh:
            fh.write("\n".join(log) + "\n\n")
        print("\n".join(log), file=sys.stderr); return
    # 供料
    if a.limit:
        uni = uni.head(a.limit)
    bdf = D.load_benchmark(cal); bench = {"o": bdf["open"].to_numpy(float), "c": bdf["close"].to_numpy(float)}
    disp = D.load_disposal_intervals(); rev, rev_ly, _ = R34.load_revenue(); rdates = R34.rebalance_dates(list(rev.index), cal)
    lo = max(0, start_pos - 80); hi = end_pos
    jobs = list(zip(uni["stock_id"], uni["market"], uni["first_seen"], uni["last_seen"]))
    series = {}; main_rows = []; g_rows = []
    with Pool(a.procs, initializer=_init, initargs=(cal, bench, disp, rev, rev_ly, rdates, lo, hi, start_pos)) as pool:
        for i, r in enumerate(pool.imap_unordered(worker, jobs, chunksize=8)):
            if r is None:
                continue
            series[r["sid"]] = {"close": r["close"], "open": r["open"], "idx": r["idx"]}
            main_rows.extend(r["main"]); g_rows.extend(r["g"])
            if (i + 1) % 400 == 0:
                print(f"  {i + 1}/{len(jobs)} {time.time() - t0:.0f}s", file=sys.stderr)
    S = pd.DataFrame(main_rows); panel = pd.DataFrame(g_rows)
    if len(S) == 0 or len(panel) == 0:
        S = pd.DataFrame(columns=["sid", "k", "pos", "entry_pos", "month", "score", "amt_ratio60"]); flags = np.zeros(0, bool)
    else:
        flags, _ = R13.and_flags(S, panel)
    AND = S[flags].copy() if len(S) else S
    # 只記新的（entry_pos ≥ from_pos）
    new = AND[(AND["entry_pos"] >= from_pos) & (AND["entry_pos"] <= end_pos)].copy()
    sig_path = os.path.join(a.out, "signals.csv")
    taken_all = {}
    for N, st in states.items():
        f0 = (st["last_pos"] + 1) if st["last_pos"] is not None else start_pos
        eq_rows, trades, taken = run_engine(st, new[new["entry_pos"] >= f0], series, cal, f0, end_pos)
        append_csv(os.path.join(a.out, f"equity_N{N}.csv"), eq_rows, ["date", "equity", "cash", "n_pos", "slot_use"])
        append_csv(os.path.join(a.out, f"trades_N{N}.csv"), trades, ["sid", "signal_date", "entry_date", "exit_date", "bars", "gross", "net", "amt", "pnl"])
        taken_all[N] = set(taken); save_state(a.out, st)
        log.append(f"- N＝{N}：記到 {cal[end_pos].date()}，權益 {st['equity']:.4f}、現金 {st['cash']:.4f}、持倉 {len(st['positions'])}（槽位 {len(st['positions']) / N * 100:.0f}%）、本次進 {len(taken)} 筆、出 {len(trades)} 筆")
    rows = [{"signal_date": str(cal[int(r.pos)].date()), "entry_date": str(cal[int(r.entry_pos)].date()), "sid": r.sid, "score": int(r.score), "amt_ratio60": float(r.amt_ratio60),
             **{f"taken_N{N}": (r.sid, int(r.pos)) in taken_all[N] for N in states}} for r in new.sort_values(["entry_pos", "sid"]).itertuples()]
    append_csv(sig_path, rows, ["signal_date", "entry_date", "sid", "score", "amt_ratio60"] + [f"taken_N{N}" for N in states])
    log.append(f"- 新 AND 訊號 {len(rows)} 筆（3/5 主格 {int((S['entry_pos'] >= from_pos).sum()) if len(S) else 0} 筆）；營收面板最新期 {panel['signal_pos'].max() if len(panel) else '—'}（{cal[int(panel['signal_pos'].max())].date() if len(panel) else '—'}）；{time.time() - t0:.0f}s")
    with open(os.path.join(a.out, "runlog.md"), "a", encoding="utf-8") as fh:
        fh.write("\n".join(log) + "\n\n")
    print("\n".join(log), file=sys.stderr)


if __name__ == "__main__":
    main()
