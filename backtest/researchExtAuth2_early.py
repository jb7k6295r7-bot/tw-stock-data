# -*- coding: utf-8 -*-
"""PREREG外部作者追加 早年段（描述、⛔ 不判、⛔ 不計 N）：探索段挑中的格照跑；範圍與前例同 PREREG外部作者 seq1 早年段
（W1 eligible 要個股法人 ⇒ 只 2012-06～2016、只上市；A 段 early 版面、B 段主快照；各自期初全現金；W2 只用月營收；停止交易強制出場：開）。
由 researchExtAuth2.py early 呼叫。"""
from __future__ import annotations
import json, os, time
from multiprocessing import Pool
import numpy as np
import pandas as pd

import researchExtAuth2 as X2
EA, SG, RR, D, L, R11 = X2.EA, X2.SG, X2.RR, X2.D, X2.L, X2.R11


def run(a, log):
    SP = os.path.join(X2.OUT, "summary.json"); S = json.load(open(SP, encoding="utf-8"))
    ch = S["探索段挑格"]
    log(f"===== researchExtAuth2 early reps={a.reps}｜挑中：{ch} =====")
    OUTE = {}
    for part, (lo_d, hi_d) in (("A", SG.EARLY_A), ("B", SG.EARLY_B)):
        if part == "A":
            D.DATA = SG.EARLY_DATA; panel = SG.EARLY_PANEL
        else:
            D.DATA = EA.H2.H2D; panel = EA.PANEL
        cal = D.load_calendar(); ncal = len(cal); mon = np.array([str(x)[:7] for x in cal])
        s0, s1 = int(cal.searchsorted(pd.Timestamp(lo_d))), int(cal.searchsorted(pd.Timestamp(hi_d)))
        sids, elig, mk = SG.stock_universe(cal, panel, os.path.join(D.DATA, "meta", "stocks.csv"), twse_only=True)
        FUND, _ = EA.load_fund(cal, log, with_fin=False)
        t0 = time.time(); SIG = {}
        with Pool(a.procs, initializer=X2._init2, initargs=({"cal": cal, "mode": "pre", "FUND": FUND},)) as pool:
            for r in pool.imap_unordered(X2.stock_work2, [(s_, mk.get(s_, "twse")) for s_ in sids], chunksize=4):
                if r is not None:
                    SIG[r["sid"]] = r
        log(f"[早年 {part}] 訊號 {len(SIG)} 檔｜{time.time() - t0:.0f}s")
        cz, oz = RR.load_prices(sorted(SIG), cal, mk, "branch")
        valid = {sid: np.unpackbits(X["valid"])[:ncal].astype(bool) for sid, X in SIG.items()}
        SF = {s1: R11.stop_force_days(valid, s1)}
        bench = RR.load_bench(cal); b50 = RR.bench_row(cal, bench, s0, s1 + 1)
        CELLS = {}
        SG._G.update(cal=cal, cz=cz, oz=oz, ncal=ncal, CELLS=CELLS, SF=SF)
        keys = []; info = {}
        for g, cn in ch.items():
            if "|" not in cn:
                continue
            code, x_ = cn.split("|")
            if code in X2.NEW_ENT:
                R, _ = X2.o1_rows(SIG, elig, mon, x_, s0, s1) if code == "O1" else EA.entry_rows(SIG, elig, mon, code, x_, s0, s1)
                R = R.reset_index(drop=True); info[f"{g}_列"] = int(len(R))
                if not len(R):
                    OUTE[f"早年{part}|{code}|{x_}"] = "無列"; continue
                SD = pd.DataFrame({"ep": [L.engine_ep(oz, cz, s_, e_) for s_, e_ in zip(R["sid"], R["entry_pos"])]})
                sig, kw, reason = SG.make_cell(R, SD, s1, "無", "無", cz, oz)
                k = (f"早年{part}", code, x_); CELLS[k] = (sig, kw, reason, None); keys.append(k)
            else:
                Rb = EA.base_rows(SIG, elig, mon, s0, s1).reset_index(drop=True)
                epb = np.array([L.engine_ep(oz, cz, s_, e_) for s_, e_ in zip(Rb["sid"], Rb["entry_pos"])])
                for c_ in (code, "BASE"):
                    if x_.startswith("H"):
                        xp, d = EA.overlay_days(Rb, SIG, None if c_ == "BASE" else c_, int(x_[1:]), s1, epb, ncal)
                        sig, kw, reason = EA.make_fixed(Rb, xp, d, epb, cz, c_)
                    else:
                        dX, why = X2.ma_base_with(Rb, SIG, x_, s1, c_ == "S1")
                        sig, kw, reason = SG.make_cell(Rb.assign(dX=dX), pd.DataFrame({"ep": epb}), s1, "無", "無", cz, oz)
                    k = (f"早年{part}", c_, x_); CELLS[k] = (sig, kw, reason, None); keys.append(k)
                info[f"{g}_基準列"] = int(len(Rb))
        keys = list(dict.fromkeys(keys))
        res = X2.run_cells(keys, s0, s1, a.reps, a.procs, f"早年 {part}", log)
        for k in keys:
            c = X2.agg3(res[k], b50)
            OUTE["|".join(k)] = {kk: v for kk, v in c.items() if not kk.startswith("_")}
        OUTE[f"早年{part}_窗"] = [lo_d, hi_d]; OUTE[f"早年{part}_0050"] = b50; OUTE[f"早年{part}_列"] = info
    D.DATA = EA.H2.H2D
    S["早年段"] = OUTE
    S["早年段_註"] = ("照 PREREG外部作者 seq1 早年段：只跑 2012-06～2016、只上市；A 段 2012-06-01～2014-12-30（early 版面）、B 段 2015-08-03～2016-12-30（主快照）；"
                  "各自期初全現金；停止交易強制出場：開；描述、⛔ 不判、⛔ 不計 N")
    json.dump(S, open(SP, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log("[早年段 完成]")
