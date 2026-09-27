# -*- coding: utf-8 -*-
"""稽核 ② 9（seq1／seq3 §二 第 9 列；裁定 seq257 順 7）：攤平停利（單筆層，甲）補 5、10 日。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchAudit2_9.py [--procs 2]
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchAudit2_9_check.py

原件：researchAvg.py 甲（回測 PREREG攤平停利 甲，69cdc62bd8）：4 格（跌 −10% 加碼／漲 +15% 賣半 × H20、H60）皆結果①。
  判定量 X ＝ 加（賣）的那一份 vs 同一筆錢換 0050（avgdown.x_value）；H20 曆月分群、H60 60 日區段；必附句 y ＝ 同日前 20 日報酬同十分位、
  當天沒觸發的持股換 0050（讀法 A10，＝ 基準②）
═══ 本件（⭐ 開跑前寫死）═══
  import researchAvg 原樣，只改三個模組常數：H_ALL ＝ (5, 10, 20, 60, 120)、H_JUDGE ＝ (5, 10, 20, 60)（讓 work／match_controls 也算 5、10 日）、
    REPS ＝ 0（⛔ 5、10 日不跑假訊號臂：原件假訊號陣列的 H 維寫死 2 格；原件 4 格假訊號 x2 ＝ 0）
  閘：H20、H60 的逐筆 X、y_bar ＝ 原件 A_events_kept.csv.gz（逐位元）
  H5／H10：分群 ＝ T 的曆月（同 H20；⚠ 原件 cell_stats 的 H ≠ 20 走 60 日區段，那是給 H60 的 ⇒ 本件不呼叫它）；出口 ＝ avgdown.exit_result；
    句子 ＝ researchAvg.sentence 同一張表；配對組 y、X − y 的 CI 同原件
  stop_force：原件 delist on（下市了結）＝ 停止交易強制出場：開；單筆層、T ≤ 窗尾 − H ⇒ T1 不適用
  「穩」：同型 4 個天數同結果才寫
輸出 backtest/resultsAudit2/9/
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchAvg as RA                           # ⭐ 原件（import 時 researchH2 把 D.DATA 指到快照、chdir 到 repo）
from backtest import avgdown as AV
from backtest import research11 as R11

OUT = "backtest/resultsAudit2/9"
HN = (5, 10)


def stats(x, T, H, cal, w0):
    x = np.asarray(x, float); T = np.asarray(T, int); ok = np.isfinite(x); x, T = x[ok], T[ok]
    g = np.array([str(cal[t])[:7] for t in T]) if H != 60 else np.maximum(T - w0, 0) // 60
    cs = R11.cl_stats(x, g)
    ne = int(min(len(x), cs["months"]))
    ex, rs = AV.exit_result(cs["mean"], cs["lo"], cs["hi"], len(x), ne)
    return {"n": int(len(x)), "X̄": float(cs["mean"]), "lo": float(cs["lo"]), "hi": float(cs["hi"]), "群數": int(cs["months"]), "n_eff": ne, "出口": ex, "結果": rs}


def main():
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    log(f"===== researchAudit2_9（攤平停利 甲：補 5、10 日）{pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）=====")
    RA.H_ALL = (5, 10, 20, 60, 120); RA.H_JUDGE = (5, 10, 20, 60); RA.REPS = 0
    argv = sys.argv[1:]
    procs, lim, cal, w0, w1, wlo, U, off, o50, c50ff, below60 = RA.setup(argv)
    res, _, _ = RA.run_pool(U, cal, w0, w1, wlo, off, "body", procs, o50, c50ff, below60)
    log(f"[讀檔＋偵測] {len(res):,} 檔")
    K = pd.DataFrame([row for r in res for row in r["rows"]])
    mc = RA.match_controls(res, K[K["H"].isin(RA.H_JUDGE)], wlo, body=True)
    K["decile"] = -1; K["n_ctrl"] = 0; K["y_bar"] = np.nan
    for (kind, H), (idx, dec, nct, yb) in mc.items():
        K.loc[idx, "decile"] = dec; K.loc[idx, "n_ctrl"] = nct; K.loc[idx, "y_bar"] = yb
    K["d"] = K["X"] - K["y_bar"]
    S = {"原件": "researchAvg.py 甲（回測 PREREG攤平停利 甲，69cdc62bd8）", "閘": {}, "結果": {}}
    ref = pd.read_csv("backtest/resultsAvg/A_events_kept.csv.gz", dtype={"sid": str}, float_precision="round_trip")
    for H in (20, 60):
        a = K[K["H"] == H].sort_values(["kind", "sid", "e", "T"]).reset_index(drop=True)
        b = ref[ref["H"] == H].sort_values(["kind", "sid", "e", "T"]).reset_index(drop=True)
        same = len(a) == len(b) and (a["sid"].values == b["sid"].values).all() and (a["T"].values == b["T"].values).all()
        nd = {c: (int(sum(not ((np.isnan(p) and np.isnan(q)) or repr(float(p)) == repr(float(q))) for p, q in zip(a[c], b[c]))) if same else None) for c in ("X", "y_bar")}
        S["閘"][f"H{H} 逐筆 X、y_bar ＝ 原件 A_events_kept"] = {"筆數": [len(a), len(b)], "同一批": bool(same), "不逐位元": nd}
    log(f"[閘] {S['閘']}")
    if not all(v["同一批"] and all(x == 0 for x in v["不逐位元"].values()) for v in S["閘"].values()):
        json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
        raise SystemExit("⛔ 閘不過")
    for kind in AV.TYPES:
        for H in (5, 10, 20, 60):
            k = K[(K["kind"] == kind) & (K["H"] == H)]
            J = stats(k["X"], k["T"], H, cal, w0)
            km = k[np.isfinite(k["y_bar"])]
            dstat = stats(km["d"], km["T"], H, cal, w0)
            dci0 = bool(dstat["lo"] <= 0 <= dstat["hi"])
            J["必附句_配對組"] = {"有配對的事件": int(len(km)), "沒有配對的事件": int(len(k) - len(km)), "y": float(km["y_bar"].mean()), "X−y": dstat, "X−y的CI含0": dci0}
            J["對現金版（描述）"] = stats(k["Xcash"], k["T"], H, cal, w0)
            J["給使用者的句子"] = RA.sentence(kind, H, J, float(km["y_bar"].mean()), dci0, 0) + ("" if H in (20, 60) else "（5、10 日沒有假訊號臂）")
            J["身分"] = "原件判定格（重算）" if H in (20, 60) else "本件補的天數"
            S["結果"][f"{AV.CELL[kind]}_H{H}"] = J
            log(f"[{AV.CELL[kind]} H{H}] n {J['n']:,}｜X̄ {J['X̄']:+.3%} [{J['lo']:+.3%}, {J['hi']:+.3%}]｜{J['出口']} {J['結果']}｜y {J['必附句_配對組']['y']:+.3%}｜X−y {dstat['X̄']:+.3%} [{dstat['lo']:+.3%}, {dstat['hi']:+.3%}]")
        S[f"穩_{AV.CELL[kind]}（四個天數同結果）"] = len({S["結果"][f"{AV.CELL[kind]}_H{H}"]["結果"] for H in (5, 10, 20, 60)}) == 1
    K[K["H"].isin(HN)][["sid", "market", "kind", "H", "e", "T", "s", "j_end", "R", "R0", "X", "Xcash", "decile", "n_ctrl", "y_bar", "d"]].to_csv(
        os.path.join(OUT, "events_h5_h10.csv.gz"), index=False, float_format="%.17g")
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] {time.time() - T0:.0f}s")


if __name__ == "__main__":
    main()
