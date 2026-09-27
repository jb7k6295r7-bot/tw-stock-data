# -*- coding: utf-8 -*-
"""K5 截斷補跑（裁定 seq260 §二、seq261；背景 backtest/audit_trunc/REPORT.md，commit 853e9e9fc1）。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchT1fix run|report [--procs 2] [--reps 200] [--only key,...]
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchT1fix_check.py

問題：research11.fixed_exit 對「出場超出資料尾」的 AND 訊號回 None ⇒ AND 表 xpos_H＝−1 ⇒ 引擎整筆濾掉（主窗 H120 丟 327 列、H60 丟 74 列）。
補法（T1 ＝ researchYear1M.and_censor／AFCext V3 讀法）：共用函式 rerun17.t1_censor＋rerun17.pad_px_t1，
  開關 rerun17.setup_and(..., t1=False)／listexit_lines.setup_t1(log, t1=False)（⭐ 預設關 ⇒ 逐位元不變；本檔閘門驗）
  ⇒ 截斷列出場日設在墊檔日（日曆位置 ncal），價格尾端墊一根（收盤＝最後收盤、開盤 NaN），引擎 ncal＋1
  ⇒ 窗內照收盤計值、⛔ 不賣、⛔ 不扣成本
⭐ 停止交易強制出場：開（research11.simulate_mtm stop_force ＝ stop_force_days(valid_from_data(AND 全部股票), 主窗尾)）
主窗 2017-03-02～2026-08-24（rerun17 win 讀法）；200 顆；對 0050：年化中位 ＞ 0.24020209886370614 且 比值 ≥ 0.7073712681980713 ⇒ 合格；只過第一條 ⇒ 另列

格（每格三個版本；⭐ 看數字前寫死）：
  off ＝ T1 關、強制出場關（＝ 原件；只跑閘門格）   sf ＝ T1 關、強制出場開   t1 ＝ T1 開、強制出場開（⭐ 正式／補跑數字）
  #1   營飆 v1 ＝ regime_t1 t1 #1：listexit_lines.sim（H120 N10、default_rng(1000＋r)、t−1 大盤閘）
  #13  營量 v1 ＝ rerun17 #13：simulate_mtm(AND 窗內, "H60", 20, default_rng(7000＋r), log=[], d_max=None, pick="relvol", queue_days=0)
  #16  regime_t1 #16：rerun17 CELLS[15]（P10 regime=True N20 H60）、t−1 大盤閘、default_rng(1000＋r)
  滑價現實版（researchSlip.ARMS 原名、arm_inputs／run_engine／metrics 原函式；researchSlip 本來就開強制出場 ⇒ 只有 sf、t1）：
     營飆 v1 現實版、營量 v1 現實版、營量 v1 現實版＋C5 低消 20 元
  營飆時停 9 格（researchYfTime.time_arms 的判定臂）、營飆停損 6 格（researchYfStop.stop_arms）、名單出場乙 6 格（researchListExit.arms）
     ⇒ 全部經 listexit_lines.sim；kw 照原件，另加 stop_force
閘門：
  G0 0050 主窗錨逐位元
  G1 off（T1 開關關、走改過的 setup 路徑）＝ 原件逐位元（cagr／mdd／vol repr、first／end／trades、eq_sha）：
     #1、#16 ＝ resultsN17/regime_t1/seeds.csv t1；#13 ＝ resultsN17/seeds_main.csv cell 13；
     時停 NH_40 ＝ resultsYfTime/seeds_arms.csv；停損 M50 ＝ resultsYfStop/body_seeds_arms.csv；名單出場 S1 ＝ resultsListExit/seeds_arms.csv（各 200 顆）
  G2 滑價 sf ＝ resultsSlip/seeds_main.csv.gz 同臂（cagr／mdd repr、eq_sha；營飆 200 顆、營量 r＝0）
每格報：原件（交件檔）、sf、T1、差（T1 − 原件）、標籤有沒有翻；時停／停損／名單出場另報 T1 下對營飆 v1（T1 版 #1 同顆配對，190／200）
輸出 backtest/resultsT1fix/：seeds.csv.gz、cells.csv、summary.json、run.log、REPORT.md（seeds_part.csv ＝ 續跑用）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import data as D
from . import listexit_lines as L
from . import rerun17 as RR
from . import research11 as R

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsT1fix")
TAG = "停止交易強制出場：開"
C50, R50 = 0.24020209886370614, 0.7073712681980713
ANCHOR = (0.24020209886370614, -0.3395700527611012)
SP16 = RR.CELLS[15][4]
SLIP_REAL, SLIP_C5 = "現實版（C1 0.3%＋C2 50 萬＋C3＋C4）", "現實版＋C5 低消 20 元"
TIME_CELLS = [f"{k}_{d}" for k in ("R0", "R10", "NH") for d in (20, 40, 60)]
STOP_CELLS = ["P15", "T20", "A3", "M20", "M50", "F"]
LE_CELLS = ["S1", "S2", "T1", "T2", "S1T1", "S2T1"]
# (key, 族, 參數, 名稱)
CELLS = [("c1", "base", None, "營飆 v1（#1 t−1）"), ("c13", "p13", None, "營量 v1（#13）"), ("c16", "p16", None, "regime_t1 #16（N20 H60）"),
         ("slip1_real", "slip", (1, SLIP_REAL), "營飆 v1 滑價現實版"), ("slip13_real", "slip", (13, SLIP_REAL), "營量 v1 滑價現實版"),
         ("slip13_c5", "slip", (13, SLIP_C5), "營量 v1 滑價現實版＋C5 低消 20 元")] + \
        [(f"time_{c}", "time", c, f"營飆時停 {c}") for c in TIME_CELLS] + \
        [(f"stop_{c}", "stop", c, f"營飆停損 {c}") for c in STOP_CELLS] + \
        [(f"le_{c}", "le", c, f"名單出場乙 {c}") for c in LE_CELLS]
CELL = {k: (f, p, n) for k, f, p, n in CELLS}
GATE_OFF = {"c1": ("regime_t1", 1), "c16": ("regime_t1", 16), "c13": ("seeds_main", 13),
            "time_NH_40": ("resultsYfTime/seeds_arms.csv", "NH_40"), "stop_M50": ("resultsYfStop/body_seeds_arms.csv", "M50"),
            "le_S1": ("resultsListExit/seeds_arms.csv", "S1")}
_G: dict = {}
LOGF = None


def log(x):
    print(x, flush=True)
    if LOGF:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(x + "\n")


def label(c, m):
    ratio = c / abs(m)
    return ("合格" if (c > C50 and ratio >= R50) else ("另列" if c > C50 else "不合格")), ratio


# ═════════════ 設定 ═════════════
def build_ctx(t1):
    ctx = L.setup_t1(log, t1=t1)
    G = RR._G; AND = G["AND"]; e = AND["entry_pos"].to_numpy()
    ctx["sig13"] = AND[(e >= G["w0"]) & (e <= G["w1"])]
    return ctx


def fam_kw(ctx):
    """時停／停損／名單出場的判定臂 kw（原件建構器；線建在這個 ctx 的訊號上 ⇒ T1 版含補回列的線）。"""
    from . import researchListExit as LE
    from . import researchYfStop as YS
    from . import researchYfTime as YT
    YS._G["ctx"] = ctx
    out = {}
    A, _ = YT.time_arms(ctx)
    for c in TIME_CELLS:
        out[f"time_{c}"] = A[c][0]
    A, _ = YS.stop_arms(ctx)
    for c in STOP_CELLS:
        out[f"stop_{c}"] = A[c][0]
    S1L = L.s1_lines(ctx["sig"], "H120", ctx["opens"], ctx["closes"])
    S2L, _ = L.s2_lines(ctx["sig"], "H120", ctx["opens"], ctx["closes"], lambda s: R.load_bars(s, ctx["mk"].get(s, "twse"), ctx["cal"]), 2.0, "entry_close")
    A = LE.arms(S1L, S2L, None)
    for c in LE_CELLS:
        out[f"le_{c}"] = A[c][0]
    return out


def slip_setup(ctx, X_full, SF, procs):
    """researchSlip.setup 主窗段落的同一套（SIG／X／SF／dl／INP），價格與 NP 取這個 ctx（T1 ⇒ 墊一根）。"""
    from . import researchSlip as S
    from . import tradability as TR
    cal = ctx["cal"]; ncal = len(cal); NP = ctx["ncal"]
    X = X_full if NP == ncal + 1 else {s: (None if v is None else {k: (a[:ncal] if isinstance(a, np.ndarray) and len(a) == ncal + 1 else a)
                                                                   for k, a in v.items()}) for s, v in X_full.items()}
    SIG = {1: ctx["sig"], 13: ctx["sig13"]}
    trad_full = {s: {"trd": v["trd"][:ncal]} for s, v in X.items() if v is not None}
    try:
        off = TR.load_official()
    except Exception:
        off = {}
    dl = TR.delist_status(trad_full, cal, official=off)
    subsegs = {k: (int(cal.searchsorted(pd.Timestamp(x))), int(cal.searchsorted(pd.Timestamp(y)))) for k, (x, y) in S.SEGS.items()}
    SG = dict(cal=cal, NP=NP, closes=ctx["closes"], opens=ctx["opens"], w0=ctx["w0"], w1=ctx["w1"], SF=SF, dl=dl, subsegs=subsegs, X=X, SIG=SIG,
              part="main", ncal=ncal)
    S._G.clear(); S._G.update(SG)
    spec = dict(S.ARMS)
    INP = {}
    for cell, arm in ((1, SLIP_REAL), (13, SLIP_REAL), (13, SLIP_C5)):
        INP[(cell, arm)] = S.arm_inputs(cell, spec[arm], SIG[cell], X, ctx["closes"], ctx["opens"])
    SG["INP"] = INP
    return SG


def _load_x(args):
    from . import researchSlip as S
    sid, mk = args
    return sid, S.stock_extra(sid, mk, _G["cal"], _G["NPX"])


def setup(a):
    t0 = time.time()
    CTX = {False: build_ctx(False), True: build_ctx(True)}
    c0, c1 = CTX[False], CTX[True]
    cal = c0["cal"]; ncal = len(cal); w0, w1 = c0["w0"], c0["w1"]
    bw = RR.bench_row(cal, RR.load_bench(cal), w0, w1 + 1)
    g0 = repr(bw["cagr"]) == repr(ANCHOR[0]) and repr(bw["mdd"]) == repr(ANCHOR[1])
    log(f"[G0 0050 錨] 逐位元 {g0}")
    if not g0:
        raise SystemExit("⛔ G0 不過")
    if not (c1["ncal"] == ncal + 1 and c0["ncal"] == ncal and c0["sig"].index.equals(c1["sig"].index) and c0["sig13"].index.equals(c1["sig13"].index)):
        raise SystemExit("⛔ T1 前後訊號列不同或 ncal 不對")
    mk = c0["mk"]
    sids = sorted(c0["closes"])
    SF = R.stop_force_days(R.valid_from_data(sids, mk, cal), w1)
    # 補回列計數（窗內）
    cnt = {}
    for nm, s0, s1, rule in (("#1／#16 訊號（t−1 閘）H120", c0["sig"], c1["sig"], "H120"), ("#1／#16 訊號（t−1 閘）H60", c0["sig"], c1["sig"], "H60"),
                             ("#13 訊號（無閘）H60", c0["sig13"], c1["sig13"], "H60")):
        x0 = s0[f"xpos_{rule}"].to_numpy(); x1 = s1[f"xpos_{rule}"].to_numpy()
        cnt[nm] = {"窗內列": int(len(s0)), "原 xpos＜0": int((x0 < 0).sum()), "T1 補回": int(((x0 < 0) & (x1 == ncal)).sum()),
                   "補回進場日": [str(cal[int(v)].date()) for v in (s1.loc[(x0 < 0) & (x1 == ncal), "entry_pos"].min(), s1.loc[(x0 < 0) & (x1 == ncal), "entry_pos"].max())]
                   if ((x0 < 0) & (x1 == ncal)).any() else None}
    log(f"[T1 補回（主窗）] {json.dumps(cnt, ensure_ascii=False)}｜全表 {json.dumps(c1['t1_cnt'], ensure_ascii=False)}")
    KW = {}
    for t1 in (False, True):
        k = fam_kw(CTX[t1])
        k.update({"c1": {}, "c13": {}, "c16": {}})
        KW[t1] = k
    # 滑價
    slip_sids = sorted(set(c0["sig"]["sid"]) | set(c0["sig13"]["sid"]))
    _G.update(cal=cal, NPX=ncal + 1)
    with Pool(a.procs) as pool:
        X_full = dict(pool.map(_load_x, [(s, mk.get(s, "twse")) for s in slip_sids], chunksize=8))
    SLIP = {t1: slip_setup(CTX[t1], X_full, SF, a.procs) for t1 in (False, True)}
    _G.update(CTX=CTX, KW=KW, SF=SF, SLIP=SLIP, w0=w0, w1=w1, ncal=ncal, bench=bw)
    info = {"日曆": ncal, "窗": [str(cal[w0].date()), str(cal[w1].date())], "停止交易股": len(SF), "補回": cnt, "全表補回": c1["t1_cnt"],
            "滑價股數": len(slip_sids), "秒": round(time.time() - t0)}
    log(f"[setup] {json.dumps({k: v for k, v in info.items() if k not in ('補回', '全表補回')}, ensure_ascii=False)}")
    return info, bw


# ═════════════ 一顆 ═════════════
def _one(args):
    key, var, r = args
    fam, par, _ = CELL[key]
    t1 = var == "t1"; sf = var != "off"
    ctx = _G["CTX"][t1]; w0, w1 = _G["w0"], _G["w1"]
    if fam == "slip":
        from . import researchSlip as S
        S._G.clear(); S._G.update(_G["SLIP"][t1])
        cell, arm = par
        sig, op, cost, kw = S._G["INP"][(cell, arm)]
        o = S.run_engine(cell, sig, op, cost, kw, r)
        m = S.metrics(o)
        eq = np.asarray(o["equity"], float)
        c, mm, v = RR.win_metrics(eq, o["first"], o["end"], w0, w1)
        if repr(float(c)) != repr(m["cagr"]) or repr(float(mm)) != repr(m["mdd"]):
            raise RuntimeError("滑價 metrics 與 win_metrics 不同")
        return {"key": key, "var": var, "r": r, "cagr": float(c), "mdd": float(mm), "vol": float(v), "first": int(o["first"]), "end": int(o["end"]),
                "trades": int(o["trades"]), "eq_sha": m["eq_sha"], "sf_n": int(o.get("x_stop_force_n", -1))}
    kw = dict(_G["KW"][t1][key])
    if sf:
        kw["stop_force"] = _G["SF"]
    if fam == "p13":
        o = R.simulate_mtm(ctx["sig13"], "H60", 20, np.random.default_rng(RR.P1_SEED0 + r), ctx["closes"], ctx["opens"], ctx["ncal"],
                           log=[], d_max=None, pick="relvol", queue_days=0, return_equity=True, **kw)
    elif fam == "p16":
        o = R.simulate_mtm(ctx["sig"], SP16["rule"], SP16["N"], np.random.default_rng(RR.P10_SEED0 + r), ctx["closes"], ctx["opens"], ctx["ncal"],
                           return_equity=True, **kw)
    else:
        o = L.sim(ctx, kw, r)
    eq = np.asarray(o["equity"], float)
    c, mm, v = RR.win_metrics(eq, o["first"], o["end"], w0, w1)
    return {"key": key, "var": var, "r": r, "cagr": float(c), "mdd": float(mm), "vol": float(v), "first": int(o["first"]), "end": int(o["end"]),
            "trades": int(o["trades"]), "eq_sha": hashlib.sha256(eq.tobytes()).hexdigest()[:16], "sf_n": int(o.get("x_stop_force_n", -1))}


def plan(keys):
    out = []
    for k in keys:
        fam = CELL[k][0]
        if k in GATE_OFF:
            out.append((k, "off"))
        out.append((k, "sf"))
        out.append((k, "t1"))
    return out


# ═════════════ 閘門 ═════════════
def gate_off(SD, reps):
    res = {}
    for key, (src, arm) in GATE_OFF.items():
        g = SD[(SD["key"] == key) & (SD["var"] == "off")].set_index("r").sort_index()
        if g.empty:
            continue
        if src == "regime_t1":
            ref = pd.read_csv(os.path.join(RR.OUT, "regime_t1", "seeds.csv"), dtype={"eq_sha": str}, float_precision="round_trip")
            ref = ref[(ref["stage"] == "t1") & (ref["cell"] == arm)]
        elif src == "seeds_main":
            ref = pd.read_csv(os.path.join(RR.OUT, "seeds_main.csv"), dtype={"eq_sha": str}, float_precision="round_trip")
            ref = ref[(ref["cell"] == arm) & (ref["mode"] == "win")]
        else:
            ref = pd.read_csv(os.path.join(HERE, src), dtype={"eq_sha": str}, float_precision="round_trip")
            ref = ref[ref["arm"] == arm]
        ref = ref.set_index("r").sort_index().loc[g.index]
        bad = 0
        for r in g.index:
            ok = all(repr(float(g.at[r, k])) == repr(float(ref.at[r, k])) for k in ("cagr", "mdd", "vol")) and \
                all(int(g.at[r, k]) == int(ref.at[r, k]) for k in ("first", "end", "trades")) and str(g.at[r, "eq_sha"]) == str(ref.at[r, "eq_sha"])
            bad += not ok
        res[key] = {"顆數": int(len(g)), "不同": int(bad), "對照": f"{src}｜{arm}"}
    return res


def gate_slip(SD):
    ref = pd.read_csv(os.path.join(HERE, "resultsSlip", "seeds_main.csv.gz"), dtype={"eq_sha": str}, float_precision="round_trip")
    res = {}
    for key, (cell, arm) in (("slip1_real", (1, SLIP_REAL)), ("slip13_real", (13, SLIP_REAL)), ("slip13_c5", (13, SLIP_C5))):
        g = SD[(SD["key"] == key) & (SD["var"] == "sf")].set_index("r").sort_index()
        if g.empty:
            continue
        rf = ref[(ref["cell"] == cell) & (ref["arm"] == arm)].set_index("r").sort_index()
        rr = [r for r in g.index if r in rf.index]
        bad = sum(not (repr(float(g.at[r, "cagr"])) == repr(float(rf.at[r, "cagr"])) and repr(float(g.at[r, "mdd"])) == repr(float(rf.at[r, "mdd"]))
                       and str(g.at[r, "eq_sha"]) == str(rf.at[r, "eq_sha"])) for r in rr)
        same = int((g["eq_sha"] == g["eq_sha"].iloc[0]).sum()) if cell == 13 else None
        res[key] = {"比對顆數": len(rr), "不同": int(bad), "對照": f"resultsSlip/seeds_main.csv.gz｜{cell}｜{arm}", **({"200 顆 eq_sha 相同": same} if same is not None else {})}
    return res


# ═════════════ 原件（交件檔）═════════════
def originals():
    o = {}
    r1 = pd.read_csv(os.path.join(RR.OUT, "regime_t1", "cells.csv"), float_precision="round_trip").set_index("編號")
    for cid in (1, 16):
        o[f"c{cid}"] = (float(r1.at[cid, "t1_年化"]), float(r1.at[cid, "t1_回落"]), str(r1.at[cid, "t1_標籤"]), "resultsN17/regime_t1/cells.csv")
    r17 = pd.read_csv(os.path.join(RR.OUT, "rerun17.csv"), float_precision="round_trip").set_index("編號")
    o["c13"] = (float(r17.at[13, "主窗_年化"]), float(r17.at[13, "主窗_回落"]), str(r17.at[13, "主窗_標籤"]), "resultsN17/rerun17.csv")
    ts = pd.read_csv(os.path.join(HERE, "resultsSlip", "table_main.csv"), float_precision="round_trip")
    for key, (nm, arm) in (("slip1_real", ("營飆 v1", SLIP_REAL)), ("slip13_real", ("營量 v1", SLIP_REAL)), ("slip13_c5", ("營量 v1", SLIP_C5))):
        q = ts[(ts["策略"] == nm) & (ts["臂"] == arm)].iloc[0]
        o[key] = (float(q["主窗_年化"]), float(q["主窗_回落"]), str(q["主窗_標籤"]), "resultsSlip/table_main.csv")
    for pre, f, cells in (("time_", "resultsYfTime/cells.csv", TIME_CELLS), ("stop_", "resultsYfStop/body_cells.csv", STOP_CELLS),
                          ("le_", "resultsListExit/cells.csv", LE_CELLS)):
        t = pd.read_csv(os.path.join(HERE, f), float_precision="round_trip").set_index("arm")
        for c in cells:
            o[pre + c] = (float(t.at[c, "cagr_med"]), float(t.at[c, "mdd_med"]), str(t.at[c, "label"]), f)
    return o


# ═════════════ 主程式 ═════════════
def run(a):
    global LOGF
    os.makedirs(OUT, exist_ok=True); LOGF = os.path.join(OUT, "run.log")
    t00 = time.time()
    src = {f: hashlib.sha256(open(os.path.join(HERE, f), "rb").read()).hexdigest()[:16]
           for f in ("research11.py", "rerun17.py", "listexit_lines.py", "researchSlip.py", "researchYfStop.py", "researchYfTime.py", "researchListExit.py",
                     "yfstop_lines.py", "researchT1fix.py")}
    log(f"===== researchT1fix run procs={a.procs} reps={a.reps} {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜{TAG}｜{src} =====")
    info, bw = setup(a)
    keys = [k for k, *_ in CELLS] if not a.only else a.only.split(",")
    fp = os.path.join(OUT, "seeds_part.csv")
    done = pd.read_csv(fp, dtype={"eq_sha": str}, float_precision="round_trip") if os.path.exists(fp) else None
    have = set() if done is None else {(k, v) for (k, v), g in done.groupby(["key", "var"]) if g["r"].nunique() >= a.reps}
    todo = [(k, v) for k, v in plan(keys) if (k, v) not in have]
    log(f"[計畫] {len(plan(keys))} 批（格×版本），已落檔 {len(have)}、待跑 {len(todo)}")
    with Pool(a.procs) as pool:
        for k, v in todo:
            t0 = time.time()
            rows = pool.map(_one, [(k, v, r) for r in range(a.reps)], chunksize=4)
            df = pd.DataFrame(rows)
            df.to_csv(fp, mode="a", header=not os.path.exists(fp), index=False)
            c, m = float(df["cagr"].median()), float(df["mdd"].median())
            log(f"  [{k}｜{v}] {c * 100:+.2f}%／{m * 100:+.2f}%（{label(c, m)[0]}）｜強制出場中位 {df['sf_n'].median():.0f}｜{time.time() - t0:.0f}s")
    json.dump({"setup": info, "程式": src, "reps": a.reps, "秒_run": round(time.time() - t00)},
              open(os.path.join(OUT, "setup.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    report(a)


def report(a):
    global LOGF
    LOGF = os.path.join(OUT, "run.log")
    SD = pd.read_csv(os.path.join(OUT, "seeds_part.csv"), dtype={"eq_sha": str}, float_precision="round_trip")
    SD = SD.drop_duplicates(["key", "var", "r"], keep="last")
    SD = SD[SD["r"] < a.reps].sort_values(["key", "var", "r"]).reset_index(drop=True)
    SD.to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False)
    setup_info = json.load(open(os.path.join(OUT, "setup.json"), encoding="utf-8"))
    G1 = gate_off(SD, a.reps); G2 = gate_slip(SD)
    gates_ok = all(v["不同"] == 0 for v in list(G1.values()) + list(G2.values()))
    log(f"[G1 off ＝ 原件] {json.dumps(G1, ensure_ascii=False)}")
    log(f"[G2 滑價 sf ＝ resultsSlip] {json.dumps(G2, ensure_ascii=False)}")
    ORIG = originals()
    base_t1 = SD[(SD["key"] == "c1") & (SD["var"] == "t1")].set_index("r").sort_index()
    rows = []
    for key, fam, par, nm in CELLS:
        g = {v: SD[(SD["key"] == key) & (SD["var"] == v)].set_index("r").sort_index() for v in ("off", "sf", "t1")}
        if g["t1"].empty:
            continue
        oc, om, ol, osrc = ORIG[key]
        row = {"key": key, "族": fam, "名": nm, "原件_年化": oc, "原件_回落": om, "原件_比值": oc / abs(om), "原件_標籤": ol, "原件_出處": osrc}
        for v in ("off", "sf", "t1"):
            if g[v].empty:
                continue
            c, m = float(g[v]["cagr"].median()), float(g[v]["mdd"].median())
            lab, ratio = label(c, m)
            row.update({f"{v}_年化": c, f"{v}_回落": m, f"{v}_比值": ratio, f"{v}_標籤": lab, f"{v}_顆數": int(len(g[v])),
                        f"{v}_強制出場中位": float(g[v]["sf_n"].median())})
        row["差_年化pt"] = (row["t1_年化"] - oc) * 100; row["差_回落pt"] = (row["t1_回落"] - om) * 100; row["差_比值"] = row["t1_比值"] - oc / abs(om)
        if "sf_年化" in row:
            row["其中T1_年化pt"] = (row["t1_年化"] - row["sf_年化"]) * 100; row["其中強制出場_年化pt"] = (row["sf_年化"] - oc) * 100
        row["翻"] = "無" if row["t1_標籤"] == ol else f"{ol} → {row['t1_標籤']}"
        if fam in ("time", "stop", "le") and not base_t1.empty:
            x = g["t1"].loc[base_t1.index]
            dc = x["cagr"] - base_t1["cagr"]; dm = x["mdd"] - base_t1["mdd"]
            npos = int(((dc > 0) & (dm > 0)).sum()); nneg = int(((dc < 0) & (dm < 0)).sum())
            row.update({"T1_對營飆v1_兩項皆正": npos, "T1_對營飆v1_兩項皆負": nneg,
                        "T1_對營飆v1": "好" if npos >= 190 else ("差" if nneg >= 190 else "分不出")})
        rows.append(row)
    TB = pd.DataFrame(rows)
    TB.to_csv(os.path.join(OUT, "cells.csv"), index=False)
    S = {"件": "K5 截斷補跑（裁定 seq260 §二、seq261）", "停止交易強制出場": "開", "閘": {"G0": True, "G1_off＝原件": G1, "G2_滑價sf＝resultsSlip": G2, "全過": gates_ok},
         "setup": setup_info["setup"], "程式": setup_info["程式"], "判準": {"C50": C50, "R50": R50}, "格": rows}
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    write_report(TB, S)
    if not gates_ok:
        raise SystemExit("⛔ 閘門不過")


def _p(x):
    return "—" if x is None or not np.isfinite(x) else f"{x * 100:+.2f}%"


def write_report(TB, S):
    T = TB.set_index("key")
    fl = TB[TB["翻"] != "無"]
    one = lambda k: T.loc[k]
    L_ = ["# K5 截斷補跑：AND 族資料尾截斷補回（T1）", "",
          f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。裁定 seq260 §二、seq261；背景 audit_trunc/REPORT.md（853e9e9fc1）。回測線。⭐ **{TAG}**。", ""]
    a1, a13 = one("c1"), one("c13")
    L_.append(f"**結論：補回資料尾截斷的訊號後，營飆 v1 {_p(a1['t1_年化'])}／{_p(a1['t1_回落'])}（{a1['t1_標籤']}）、營量 v1 {_p(a13['t1_年化'])}／{_p(a13['t1_回落'])}（{a13['t1_標籤']}）；"
              f"{len(TB)} 格裡標籤翻了 {len(fl)} 格" + ("（" + "、".join(f"{r['名']} {r['翻']}" for _, r in fl.iterrows()) + "）" if len(fl) else "") + "。**")
    L_ += ["", "## 翻不翻", "", "| 格 | 原件標籤 | T1 標籤 | 翻 | 年化差（點） | 回落差（點） |", "|---|---|---|---|---|---|"]
    for _, r in TB.iterrows():
        L_.append(f"| {r['名']} | {r['原件_標籤']} | {r['t1_標籤']} | {r['翻']} | {r['差_年化pt']:+.2f} | {r['差_回落pt']:+.2f} |")
    L_ += ["", "## 正式數字（⭐ 以 T1 版為準；舊數字只列在「沿革」）", "",
           "| 策略 | 年化中位 | 回落中位 | 比值 | 標籤 |", "|---|---|---|---|---|"]
    for k in [k_ for k_ in ("c1", "c13", "slip1_real", "slip13_real", "slip13_c5") if k_ in T.index]:
        r = one(k)
        L_.append(f"| {r['名']}（T1） | {_p(r['t1_年化'])} | {_p(r['t1_回落'])} | {r['t1_比值']:.3f} | {r['t1_標籤']} |")
    L_ += ["", "### 沿革（舊數字，⛔ 不並列引用）", ""]
    for k in [k_ for k_ in ("c1", "c13", "slip1_real", "slip13_real", "slip13_c5") if k_ in T.index]:
        r = one(k)
        L_.append(f"- {r['名']}：舊 {_p(r['原件_年化'])}／{_p(r['原件_回落'])}（{r['原件_標籤']}；{r['原件_出處']}；資料尾截斷丟訊號；原件強制出場關，滑價件原件為開）"
                  f" ⇒ T1 {_p(r['t1_年化'])}／{_p(r['t1_回落'])}；差 年化 {r['差_年化pt']:+.2f} 點、回落 {r['差_回落pt']:+.2f} 點")
    L_ += ["", "## 全部格（原件 → 強制出場開 → T1）", "",
           "| 格 | 原件 | 強制出場開（T1 關） | T1（強制出場開） | 差 年化／回落（點） | 其中 T1／強制出場（年化點） | 翻 |", "|---|---|---|---|---|---|---|"]
    for _, r in TB.iterrows():
        sfv = f"{_p(r['sf_年化'])}／{_p(r['sf_回落'])}" if pd.notna(r.get("sf_年化")) else "—"
        dec = f"{r['其中T1_年化pt']:+.2f}／{r['其中強制出場_年化pt']:+.2f}" if pd.notna(r.get("其中T1_年化pt")) else "—"
        L_.append(f"| {r['名']} | {_p(r['原件_年化'])}／{_p(r['原件_回落'])} {r['原件_標籤']} | {sfv} | {_p(r['t1_年化'])}／{_p(r['t1_回落'])} {r['t1_標籤']} | "
                  f"{r['差_年化pt']:+.2f}／{r['差_回落pt']:+.2f} | {dec} | {r['翻']} |")
    fam = TB[TB["族"].isin(["time", "stop", "le"])]
    if len(fam) and "T1_對營飆v1" in fam:
        L_ += ["", "## 時停／停損／名單出場：T1 下對營飆 v1（T1 版 #1 同顆配對；兩項皆正 ≥ 190 ⇒ 好、皆負 ≥ 190 ⇒ 差）", "",
               "| 格 | 兩項皆正 | 兩項皆負 | 對營飆 v1 |", "|---|---|---|---|"]
        for _, r in fam.iterrows():
            L_.append(f"| {r['名']} | {int(r['T1_對營飆v1_兩項皆正'])} | {int(r['T1_對營飆v1_兩項皆負'])} | {r['T1_對營飆v1']} |")
    su = S["setup"]
    L_ += ["", "## 補法與閘門", "",
           "- 補法：共用函式 `rerun17.t1_censor`＋`rerun17.pad_px_t1`（＝ researchYear1M.and_censor／AFCext V3 讀法，fixture 在查核）；"
           "開關 `rerun17.setup_and(..., t1=False)`、`listexit_lines.setup_t1(log, t1=False)`，⭐ 預設關",
           "- 截斷列：出場日設墊檔日（日曆位置 ncal），價格尾端墊一根（收盤＝最後收盤、開盤 NaN），引擎 ncal＋1 ⇒ 窗內照收盤計值、⛔ 不賣、⛔ 不扣成本",
           f"- 主窗補回列：{json.dumps(su['補回'], ensure_ascii=False)}",
           f"- 全表補回（含窗外）：{json.dumps(su['全表補回'], ensure_ascii=False)}",
           "- ⚠ 與 audit_trunc 的 327／74 差 1 列：2464（進場 2026-08-07）k−20 之後有壞根 ⇒ T1 定義（Year1M 同式）不算資料尾截斷、照原件丟（查核 ② 列出）",
           f"- 停止交易股（AND 全部股票、主窗內）{su['停止交易股']} 檔",
           f"- G0 0050 主窗錨逐位元：{S['閘']['G0']}",
           f"- G1 T1 開關關（走改過的 setup 路徑）＝ 原件逐位元：{json.dumps(S['閘']['G1_off＝原件'], ensure_ascii=False)}",
           f"- G2 滑價 強制出場開、T1 關 ＝ resultsSlip 同臂逐位元：{json.dumps(S['閘']['G2_滑價sf＝resultsSlip'], ensure_ascii=False)}",
           "- 營量 v1 以 relvol 排序、不抽籤 ⇒ 200 顆相同（滑價件只跑 r＝0；本件照 200 顆跑、G2 只比 r＝0）",
           "- ⚠ 時停／停損／名單出場的停損線在 T1 版建在含補回列的訊號上（同一套建構器；補回列的線延伸到墊檔日）", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L_) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["run", "report"])
    ap.add_argument("--procs", type=int, default=2); ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--only", default=""); ap.add_argument("--out", default="")
    a = ap.parse_args()
    if a.out:
        OUT = a.out
    run(a) if a.mode == "run" else report(a)
