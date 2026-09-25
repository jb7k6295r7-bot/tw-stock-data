# -*- coding: utf-8 -*-
"""PREREGX §一之二 閘門段：箱型、杯柄以研究二 Frame.gate 跑一次，【只為】重現研究二筆數與杯柄目標達成率（⛔ 不進判定）。

登錄逐字：「箱型、杯柄另以 Frame.gate 跑一次，【只為】重現研究二筆數（6,417／116）與杯柄 60%／41%」。
⭐ 走的是本件主跑同一條包裝（patterns_x.box_events／cup_events／cup_scan），只把 Frame.gate 換回研究二的
   （前 20 日全有成交 ∧ 20 日均量 ≥ 500 張 ∧ 母體存續期 ∧ 非處置〔含出關 5 日〕）。

研究二有兩個版本的逐筆檔（都在 git 裡）：
   v1 ＝ commit ce56d1c252（09-08 第一版；CONCLUSIONS 表頭的 6,417 就是這一版）：斷點＝ data.jump_days（比值 ＜0.55／＞1.8、非事件日），
        剔除訊號日 ∈ [i−121, i+20]
   v3 ＝ commit 5ae07bc00a（09-09 第三版；summary.md 的 6,415）：斷點＝ data.breakpoints（更正三＋更正四），剔除 [T−131, T+479]
⇒ 兩版都用【當時 commit 的 data/ 與 data.py】（git archive 到 ~/x_r2data/<sha>/，唯讀），偵測器用現行 patterns.py
   （box_breakout／cup_handle 自 ce56d1c252 起未改，git diff 可查）。逐筆與當時的 signals.csv.gz 比對（代號＋訊號日）。

    ~/tw-p16/.venv/bin/python backtest/researchX_recon.py v1|v3 [--procs 2]
"""
from __future__ import annotations
import importlib.util
import json
import os
import subprocess
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import patterns as P          # noqa: E402
from backtest import evaluate as E          # noqa: E402
from backtest import patterns_x as PX       # noqa: E402

SHAS = {"v1": "ce56d1c252024ac88d303417bb403d98c87eced8", "v3": "5ae07bc00a0d0f8d05f69d2a39ee061576b02bb0"}
SIG_START, SIG_END = "2016-01-04", "2026-07-31"
OUT = "backtest/resultsX"
_G = {}


def load_old_data(ver):
    root = os.path.expanduser(f"~/x_r2data/{SHAS[ver]}")
    spec = importlib.util.spec_from_file_location(f"r2data_{ver}", os.path.join(root, "backtest", "data.py"))
    mod = importlib.util.module_from_spec(spec); sys.modules[spec.name] = mod; spec.loader.exec_module(mod)
    mod.DATA = os.path.join(root, "data")
    return mod


def _init(ver, cal, bench, disp, lo, hi):
    _G.update(ver=ver, D=load_old_data(ver), cal=cal, bench=bench, disp=disp, lo=lo, hi=hi)


def one(args):
    sid, market, fs, ls = args
    D, cal, ver = _G["D"], _G["cal"], _G["ver"]
    st = D.load_stock(sid, market, cal)
    if st is None:
        return []
    df = st.df
    in_life = (cal >= fs) & (cal <= ls)
    f = P.Frame(df, st.event_dates)
    f.gate = f.gate & in_life & ~D.disposal_mask(sid, cal, _G["disp"])     # ⭐ 研究二 Frame.gate
    ncal = len(cal)
    if ver == "v1":
        jw = np.zeros(ncal, bool)
        for i in np.flatnonzero(D.jump_days(df, st.event_dates)):
            jw[max(0, i - E.ATR_CAP - 1):min(ncal, i + 21)] = True
    else:
        H = 1 + max(E.HOLD, E.ATR_CAP, E.TARGET_WINDOW) + E.DEFER_MAX
        jw = D.breakpoint_window(D.breakpoints(df, st.event_dates), ncal, H, P.max_lookback())
    arr = {"o": f.o, "h": f.h, "l": f.l, "c": f.c, "prev_c": f.prev_c, "atr14": f.atr14}
    out = []
    # 箱型：本件包裝（事件日＝站穩確認日）⇒ 研究二的訊號日 ＝ sig
    for e in PX.box_events(f):
        s = e["sig"]
        if not (_G["lo"] <= s <= _G["hi"]) or jw[s]:
            continue
        r = E.evaluate_signal(arr, _G["bench"], {"pattern": "P1_box_breakout", "signal_pos": s, "entry_pos": e["entry"], "direction": 1})
        if r is None:
            continue
        out.append({"pattern": "P1_box_breakout", "stock_id": sid, "signal_date": str(cal[s].date())})
    # 杯柄：本件包裝；目標 ＝ 起點開盤＋杯深（全）／＋半杯深，H＝120（＝研究二 TARGET_WINDOW）
    ce = PX.cup_events(f)
    sig2, _ = PX.cup_scan(f)
    assert [x["signal_pos"] for x in sig2] == [x["T"] for x in ce], (sid, "cup_scan ≠ patterns.cup_handle")
    for e in ce:
        s = e["T"]
        if not (_G["lo"] <= s <= _G["hi"]) or jw[s]:
            continue
        sg = {"pattern": "P6_cup_handle", "signal_pos": s, "entry_pos": e["entry"], "direction": 1,
              "cup_L": f.c[e["L"]], "cup_B": f.c[e["B"]], "handle_low": 0.0}
        r = E.evaluate_signal(arr, _G["bench"], sg)
        if r is None:
            continue
        ep = f.o[e["entry"]]
        mine = PX_targets(f, e["entry"], ep, e["depth_px"])
        out.append({"pattern": "P6_cup_handle", "stock_id": sid, "signal_date": str(cal[s].date()),
                    "tgt_half": bool(r["tgt_half"]), "tgt_full": bool(r["tgt_full"]),
                    "x_half": mine[0], "x_full": mine[1]})
    return out


def PX_targets(f, entry, ep, depth_px, H=120):
    """本件的達成判法（另一條路）：[entry, entry+H−1] 內任一日還原 high ≥ 目標。"""
    seg = f.h[entry:entry + H]
    mx = np.nanmax(seg) if np.isfinite(seg).any() else np.nan
    return (bool(mx >= ep + 0.5 * depth_px), bool(mx >= ep + depth_px))


def main():
    ver = sys.argv[1]
    procs = int(sys.argv[sys.argv.index("--procs") + 1]) if "--procs" in sys.argv else 2
    t0 = time.time()
    D = load_old_data(ver)
    cal = D.load_calendar(); uni = D.load_universe()
    bench_df = D.load_benchmark(cal)
    bench = {"o": bench_df["open"].to_numpy(float), "c": bench_df["close"].to_numpy(float)}
    disp = D.load_disposal_intervals()
    lo = int(cal.searchsorted(pd.Timestamp(SIG_START))); hi = int(cal.searchsorted(pd.Timestamp(SIG_END), side="right") - 1)
    jobs = list(zip(uni["stock_id"], uni["market"], uni["first_seen"], uni["last_seen"]))
    with Pool(procs, initializer=_init, initargs=(ver, cal, bench, disp, lo, hi)) as pool:
        res = pool.map(one, jobs, chunksize=16)
    X = pd.DataFrame([r for rr in res for r in rr])
    ref = pd.read_csv(subprocess.run(["git", "show", f"{SHAS[ver]}:backtest/results/signals.csv.gz"], capture_output=True).stdout
                      and _tmp_ref(SHAS[ver]), dtype={"stock_id": str})
    out = {"版本": ver, "commit": SHAS[ver], "母體檔數": len(jobs), "耗時s": round(time.time() - t0)}
    for pat in ("P1_box_breakout", "P6_cup_handle"):
        a = X[X["pattern"] == pat]; b = ref[ref["pattern"] == pat]
        ka = set(zip(a["stock_id"], a["signal_date"])); kb = set(zip(b["stock_id"], b["signal_date"]))
        d = {"本件": len(a), "研究二逐筆": len(b), "只在本件": len(ka - kb), "只在研究二": len(kb - ka),
             "逐筆相同": ka == kb}
        if pat == "P6_cup_handle":
            m = a.merge(b[["stock_id", "signal_date", "tgt_half", "tgt_full"]], on=["stock_id", "signal_date"], suffixes=("", "_r2"))
            d.update({"半杯深達成率_本件": float(a["x_half"].mean()), "全杯深達成率_本件": float(a["x_full"].mean()),
                      "半杯深達成率_研究二": float(b["tgt_half"].mean()), "全杯深達成率_研究二": float(b["tgt_full"].mean()),
                      "逐筆達成相同_半": bool((m["x_half"] == m["tgt_half_r2"].astype(bool)).all()),
                      "逐筆達成相同_全": bool((m["x_full"] == m["tgt_full_r2"].astype(bool)).all()),
                      "evaluate.targets_hit 與本件判法逐筆相同": bool((a["x_half"] == a["tgt_half"]).all() and (a["x_full"] == a["tgt_full"]).all())})
        out[pat] = d
    os.makedirs(OUT, exist_ok=True)
    json.dump(out, open(os.path.join(OUT, f"recon_r2_{ver}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


def _tmp_ref(sha):
    p = f"/tmp/x_r2sig_{sha[:10]}.csv.gz"
    with open(p, "wb") as fh:
        fh.write(subprocess.run(["git", "show", f"{sha}:backtest/results/signals.csv.gz"], capture_output=True).stdout)
    return p


if __name__ == "__main__":
    main()
