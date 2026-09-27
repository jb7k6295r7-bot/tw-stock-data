# -*- coding: utf-8 -*-
"""PREREG外部作者 早年段（描述、⛔ 不判、⛔ 不計 N）：探索段挑中的格照跑。由 researchExtAuth.py early 呼叫。

⚠ 範圍照 PREREG訊號系統 早年段前例（researchSig.early）：W1 eligible 要個股三大法人，data/early 自 2012-05 起才有
  ⇒ 只跑 2012-06～2016、只上市；A 段 2012-06-01～2014-12-30（early 版面 3edc0e2206）、B 段 2015-08-03～2016-12-30（主快照；
  panel_ext 在 2015-01～07 因 K 棒數不足無人合格）；兩段各自期初全現金
⚠ W2 基本面早年只用月營收條件（登錄 §五：季財報早年無）——逐字：「早年段 W2 只用月營收條件（季財報早年無）」
"""
from __future__ import annotations
import json, os, time
from multiprocessing import Pool
import numpy as np
import pandas as pd

import researchExtAuth as EA
SG, RR, D, L = EA.SG, EA.RR, EA.D, EA.L


def run(a, log):
    SP = os.path.join(EA.OUT, "summary.json"); S = json.load(open(SP, encoding="utf-8"))
    ch = S["探索段挑格"]
    log(f"===== researchExtAuth early reps={a.reps}｜挑中：{ch} =====")
    OUTE = {}
    for part, (lo_d, hi_d) in (("A", SG.EARLY_A), ("B", SG.EARLY_B)):
        if part == "A":
            st_ = json.load(open(os.path.join(os.path.dirname(SG.EARLY_DATA), "STATUS.json"), encoding="utf-8"))
            assert st_.get("complete"), "⛔ 早年版面不完整"
            D.DATA = SG.EARLY_DATA; panel = SG.EARLY_PANEL
        else:
            D.DATA = EA.H2.H2D; panel = EA.PANEL
        cal = D.load_calendar(); ncal = len(cal); mon = np.array([str(x)[:7] for x in cal])
        s0, s1 = int(cal.searchsorted(pd.Timestamp(lo_d))), int(cal.searchsorted(pd.Timestamp(hi_d)))
        assert str(cal[s0].date()) == lo_d and str(cal[s1].date()) == hi_d and s1 + 1 < ncal
        sids, elig, mk = SG.stock_universe(cal, panel, os.path.join(D.DATA, "meta", "stocks.csv"), twse_only=True)
        FUND, fst = EA.load_fund(cal, log, with_fin=False)
        t0 = time.time(); SIG = {}
        with Pool(a.procs, initializer=EA._init, initargs=({"cal": cal, "mode": "pre", "FUND": FUND},)) as pool:
            for r in pool.imap_unordered(EA.stock_work, [(s_, mk.get(s_, "twse")) for s_ in sids], chunksize=4):
                if r is not None:
                    SIG[r["sid"]] = r
        log(f"[早年 {part}] 訊號 {len(SIG)} 檔｜月營收 {fst}｜{time.time() - t0:.0f}s")
        cz, oz = RR.load_prices(sorted(SIG), cal, mk, "branch")
        bench = RR.load_bench(cal); b50 = RR.bench_row(cal, bench, s0, s1 + 1)
        CELLS = {}
        SG._G.update(cal=cal, cz=cz, oz=oz, ncal=ncal, CELLS=CELLS)
        keys = []; info = {}
        base = None
        for g, cn in ch.items():
            if "|" not in cn:
                continue
            code, x_ = cn.split("|")
            if code in EA.ENTRIES:
                R, drop = EA.entry_rows(SIG, elig, mon, code, x_, s0, s1); R = R.reset_index(drop=True)
                info[f"{g}_列"] = int(len(R))
                if len(R) == 0:
                    OUTE[f"早年{part}|{code}|{x_}"] = "無列"; continue
                SD = pd.DataFrame({"ep": [L.engine_ep(oz, cz, s_, e_) for s_, e_ in zip(R["sid"], R["entry_pos"])]})
                sig, kw, reason = SG.make_cell(R, SD, s1, "無", "無", cz, oz)
                k = (f"早年{part}", code, x_); CELLS[k] = (sig, kw, reason, None); keys.append(k); info[f"{g}_列"] = int(len(R))
            else:
                if base is None:
                    Rb = EA.base_rows(SIG, elig, mon, s0, s1).reset_index(drop=True)
                    epb = np.array([L.engine_ep(oz, cz, s_, e_) for s_, e_ in zip(Rb["sid"], Rb["entry_pos"])])
                    base = (Rb, epb)
                Rb, epb = base; H = int(x_[1:])
                for c_ in (code, "BASE"):
                    xp, d = EA.overlay_days(Rb, SIG, None if c_ == "BASE" else c_, H, s1, epb, ncal)
                    sig, kw, reason = EA.make_fixed(Rb, xp, d, epb, cz, c_)
                    k = (f"早年{part}", c_, x_); CELLS[k] = (sig, kw, reason, None); keys.append(k)
                    info[f"{g}_{c_}_基準列"] = int(len(Rb)); info[f"{g}_{c_}_觸發列"] = int((d >= 0).sum())
        keys = list(dict.fromkeys(keys))
        res = EA.run_cells(keys, s0, s1, a.reps, a.procs, f"早年 {part}", log)
        for k in keys:
            c = EA.agg2(res[k], b50) if res[k] else None
            OUTE["|".join(k)] = {kk: v for kk, v in c.items() if not kk.startswith("_")} if c else "無列"
        OUTE[f"早年{part}_窗"] = [lo_d, hi_d]; OUTE[f"早年{part}_0050"] = b50; OUTE[f"早年{part}_列"] = info; OUTE[f"早年{part}_資料"] = D.DATA
    D.DATA = EA.H2.H2D
    S["早年段"] = OUTE
    S["早年段_註"] = ("照 PREREG訊號系統 早年段前例：W1 eligible 要個股三大法人，data/early 自 2012-05 起才有 ⇒ 只跑 2012-06～2016、只上市；"
                  "A 段 2012-06-01～2014-12-30（early 版面 3edc0e2206）、B 段 2015-08-03～2016-12-30（主快照）；兩段各自期初全現金；"
                  "早年段 W2 只用月營收條件（季財報早年無）；描述、⛔ 不判、⛔ 不計 N")
    json.dump(S, open(SP, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log("[早年段 完成]")
