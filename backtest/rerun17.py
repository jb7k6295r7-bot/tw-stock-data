# -*- coding: utf-8 -*-
"""裁定線 seq143 §三②：候選 17 格在主窗（2017-03-02～2026-08-24）重跑一次，統一 0050 錨、補年化波動。

⛔ 本支只跑計算、不訂判準、不改任何既有 .py；策略邏輯一律呼叫原程式的函式：
   引擎 research11.simulate_mtm／窗內年化與回落 research13.window_stats／
   P14 合成 researchp14.blend／P17 算式與合成 researchp17.{rebal_days, sigma_at, w_paths, compose}／
   P12 策略側訊號 researchp7.build_sig_gate_b。

    python3 -m backtest.rerun17 repro   [--px branch|npz:<closes.npz 所在目錄>] [--procs 4]   # 閘一：原資料、原窗重現
    python3 -m backtest.rerun17 winonly [--px ...]                                         # 中間版：只換窗、不換資料
    python3 -m backtest.rerun17 main                                                       # 主窗：edc6f 快照 ＋ 主窗
    python3 -m backtest.rerun17 dataonly                                                   # 中間版：只換資料、不換窗
    python3 -m backtest.rerun17 table                                                      # 彙總 → resultsN17/rerun17.csv

主窗讀法（⭐ 看結果前寫定）：
  ・訊號只留 entry_pos ∈ [w0, w1] ⇒ 組合在 w0 之前全現金、w0 開盤起才可能進場（以現金起算）
  ・年化／回落 ＝ research13.window_stats(eq, min(first, w0), max(end, w1+1), w0, w1+1)
      ＝ 以 eq[w0] 為起點、2313 日／245 年化（與 0050 錨 P17 W0 ＝ B/B[0] 同一口徑）
      ⚠ window_stats 會把 a clamp 到 first ⇒ 照 researchp12.win_read 先取 min(first, w0)
  ・w1 仍持有的部位以 w1 收盤市值計（引擎本來就逐日市值）
  ・年化波動 ＝ 窗內日報酬 eq[t]/eq[t−1]−1（t ∈ (w0, w1]，2312 個）標準差 ddof=1 × √245
      （repo 慣例：p4_features.vol60、researchp13 te、researchAFC 皆 × √245；年化天數 245 同 simulate_mtm）
  ・比值 ＝ 年化中位 ÷ |回落中位|（⛔ 不是逐種子比值的中位）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

SHA = "edc6f8002fed8803795e3486ad57db513f7e9f65"
H2D = os.path.expanduser(f"~/h2data/{SHA}/data")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsN17")
W0, W1 = "2017-03-02", "2026-08-24"
WIN_DAYS = 2313
ANCHOR = (0.24020209886370614, -0.3395700527611012)      # P17 W0 釘死值（年化、回落）
ANN = 245

from . import data as D                                   # noqa: E402
from . import research11 as R                             # noqa: E402
from . import research13 as R13                           # noqa: E402

COST_STD = R.COST
P1_SEED0, P1_QUEUE = 7000, 5                              # researchp1.SEED0／QUEUE（⛔ 不 import 以免誤觸 load_prices 的寫檔路徑；值另在 selfcheck 對）
P10_SEED0 = 1000                                          # research13：default_rng(1000 + r)
P12_SEED0, P12_N, P12_RULE = 102000, 8, "H120"
REPS = 200

# ── 17 格（編號＝裁定線 seq143 §三② 的順序）─────────────────────────────
CELLS = [
    (1, "主", "PREREG10", "AND｜regime=True｜N10｜H120", dict(fam="P10", reg=True, N=10, rule="H120")),
    (2, "主", "P3乙", "N≤8｜N8｜d=1.0｜relvol", dict(fam="P3B", N=8, d=1, pick="relvol")),
    (3, "主", "P1", "AND｜N8｜d=1.0｜relvol", dict(fam="P1", N=8, d=1, pick="relvol")),
    (4, "主", "PREREG10", "AND｜regime=True｜N10｜LD", dict(fam="P10", reg=True, N=10, rule="LD")),
    (5, "主", "P17", "R_eq（判定格）", dict(fam="P17")),
    (6, "主", "P1", "AND｜N8｜d=2.0｜relvol", dict(fam="P1", N=8, d=2, pick="relvol")),
    (7, "主", "PREREG10", "AND｜regime=True｜N10｜H60", dict(fam="P10", reg=True, N=10, rule="H60")),
    (8, "主", "P14", "w=0.50（＝各半混 0050）", dict(fam="P14")),
    (9, "主", "P1", "AND｜N10｜d=inf｜relvol", dict(fam="P1", N=10, d=None, pick="relvol")),
    (10, "主", "P3乙", "N≤8｜N8｜d=2.0｜relvol", dict(fam="P3B", N=8, d=2, pick="relvol")),
    (11, "主", "P1", "AND｜N8｜d=inf｜relvol", dict(fam="P1", N=8, d=None, pick="relvol")),
    (12, "主", "PREREG10", "AND｜regime=False｜N10｜H120", dict(fam="P10", reg=False, N=10, rule="H120")),
    (13, "次", "P1", "AND｜N20｜d=inf｜relvol", dict(fam="P1", N=20, d=None, pick="relvol")),
    (14, "次", "P1", "AND｜N20｜d=inf｜null", dict(fam="P1", N=20, d=None, pick=None)),
    (15, "次", "PREREG10", "AND｜regime=False｜N20｜H60", dict(fam="P10", reg=False, N=20, rule="H60")),
    (16, "次", "PREREG10", "AND｜regime=True｜N20｜H60", dict(fam="P10", reg=True, N=20, rule="H60")),
    (17, "次", "PREREG10", "AND｜regime=True｜N20｜H120", dict(fam="P10", reg=True, N=20, rule="H120")),
]
T219_FAM = {"PREREG10": "PREREG10／研究十三", "P3乙": "P3 乙臂（閒置放 0050）", "P1": "P1", "P14": "P14", "P17": "P17"}
T219_CELL = {2: "N≤8｜N8｜d=1.0｜relvol", 10: "N≤8｜N8｜d=2.0｜relvol"}


# ═════════════ 共用 ═════════════
def use_snapshot():
    """⭐ 一律讀釘住的 main 快照（同 researchH2）。"""
    if not os.path.isdir(H2D):
        raise SystemExit(f"⛔ 快照不在 {H2D}")
    D.DATA = H2D


def win_bounds(cal):
    w0 = int(cal.searchsorted(pd.Timestamp(W0))); w1 = int(cal.searchsorted(pd.Timestamp(W1)))
    if str(cal[w0].date()) != W0 or str(cal[w1].date()) != W1 or w1 - w0 + 1 != WIN_DAYS:
        raise SystemExit(f"⛔ 主窗端點／天數不對：{cal[w0].date()}～{cal[w1].date()} {w1 - w0 + 1} 日")
    return w0, w1


def load_bench(cal):
    return pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy()).ffill().to_numpy(float)


def ann_vol(seg):
    seg = np.asarray(seg, float)
    r = seg[1:] / seg[:-1] - 1.0
    return float(np.std(r, ddof=1) * np.sqrt(ANN))


def win_metrics(eq, first, end, w0, w1):
    lo = min(first, w0)
    c, m = R13.window_stats(eq, lo, max(end, w1 + 1), w0, w1 + 1)
    return float(c), float(m), ann_vol(eq[w0:w1 + 1])


def load_prices(sids, cal, uni_mk, px: str):
    """px＝"branch"：D.load_stock（當下 D.DATA）；"npz:<dir>"：唯讀讀 <dir>/closes.npz、opens.npz（⛔ 不寫回）。
    ⛔ 不呼叫 researchp1.load_prices —— 它在快取缺檔時會【覆寫】resultsp1/regress/closes.npz。"""
    sids = sorted(set(sids))
    if px.startswith("npz:"):
        d = px[4:]
        cz, oz = np.load(os.path.join(d, "closes.npz")), np.load(os.path.join(d, "opens.npz"))
        miss = [s for s in sids if s not in cz.files]
        if miss:
            raise SystemExit(f"⛔ npz 快取缺 {len(miss)} 檔（例 {miss[:5]}）⇒ 不混用來源，停")
        return {s: cz[s] for s in sids}, {s: oz[s] for s in sids}
    closes, opens = {}, {}
    for s in sids:
        st = D.load_stock(s, uni_mk.get(s, "twse"), cal)
        if st is None:
            continue
        closes[s] = pd.Series(st.df["close"].to_numpy()).ffill().to_numpy(np.float32)
        opens[s] = st.df["open"].to_numpy(np.float32)
    return closes, opens


def regime_mask(bench):
    ma = pd.Series(bench).rolling(R13.MA_REGIME, min_periods=R13.MA_REGIME).mean().to_numpy()
    return bench > ma


# ═════════════ 引擎呼叫（⭐ 全檔只有這一個地方）═════════════
_G: dict = {}


def _sim_engine(sp, sig, seed):
    fam = sp["fam"]
    if fam == "P10":
        return R.simulate_mtm(sig, sp["rule"], sp["N"], np.random.default_rng(seed), _G["closes"], _G["opens"], _G["ncal"],
                              return_equity=True)
    kw = dict(d_max=sp["d"], pick=sp["pick"], queue_days=P1_QUEUE if sp["d"] is not None else 0, return_equity=True)
    if fam == "P1":          # researchp1._sim_one：log=lg 照原樣傳（純記錄）
        return R.simulate_mtm(sig, "H60", sp["N"], np.random.default_rng(seed), _G["closes"], _G["opens"], _G["ncal"], log=[], **kw)
    if fam == "P3B":         # researchp3.sim_cell_seed 的 B（乙）
        return R.simulate_mtm(sig, "H60", sp["N"], np.random.default_rng(seed), _G["closes"], _G["opens"], _G["ncal"],
                              cash_mode="bench", bench=_G["bench"], bench_cost=COST_STD / 2, **kw)
    raise ValueError(fam)


def sig_for(sp, mode):
    sig = _G["AND"]
    if sp["fam"] == "P10" and sp["reg"]:
        sig = sig[_G["regime"][sig["entry_pos"].to_numpy()]]
    if mode == "win":
        e = sig["entry_pos"].to_numpy()
        sig = sig[(e >= _G["w0"]) & (e <= _G["w1"])]
    return sig


def _one(args):
    cid, mode, r = args
    sp = dict(CELLS[cid - 1][4])
    seed = (P10_SEED0 if sp["fam"] == "P10" else P1_SEED0) + r
    sig = sig_for(sp, mode)
    s = _sim_engine(sp, sig, seed)
    eq, first, end = s["equity"], s["first"], s["end"]
    row = {"cell": cid, "mode": mode, "r": r, "seed": seed, "first": int(first), "end": int(end), "trades": int(s["trades"]),
           "eq_sha": hashlib.sha256(np.asarray(eq, float).tobytes()).hexdigest()[:16]}
    if mode == "orig":
        if sp["fam"] == "P3B":          # researchp3._stats 的全期那一格
            a, b = max(_G["first_all"], first), min(_G["ncal"], end)
            c, m = R13.window_stats(eq, first, end, _G["first_all"], _G["ncal"])
        else:                           # research13／researchp1：引擎自己的 cagr／mdd
            a, b = first, end
            c, m = s["cagr"], s["mdd"]
        row.update(cagr=float(c), mdd=float(m), vol=ann_vol(eq[max(a - 1, 0):b]), win_a=int(a), win_b=int(b))
    else:
        c, m, v = win_metrics(eq, first, end, _G["w0"], _G["w1"])
        row.update(cagr=c, mdd=m, vol=v, win_a=_G["w0"], win_b=_G["w1"] + 1)
    return row


# ── P12 策略側（P14 w=0.50／P17 R_eq 共用）──
def _one_p12(r):
    from . import researchp14 as P14
    from . import researchp17 as P17
    R.COST = COST_STD
    try:
        s = R.simulate_mtm(_G["sig12"], P12_RULE, P12_N, np.random.default_rng(P12_SEED0 + r), _G["closes"], _G["opens"], _G["ncal"],
                           return_equity=True, pick=None, cap_fn=None, d_max=None, queue_days=0, cash_mode="zero", bench=None, log=None)
    finally:
        R.COST = COST_STD
    w0, w1 = _G["w0"], _G["w1"]; n = w1 - w0 + 1
    eq = np.asarray(s["equity"], float)
    E = eq[w0:w1 + 1]; B = _G["B"]
    out = []
    V14 = P14.blend(E, B, 0.50)
    c, m = R13.window_stats(V14, 0, n, 0, n)
    out.append({"cell": 8, "r": r, "seed": P12_SEED0 + r, "cagr": float(c), "mdd": float(m), "vol": ann_vol(V14),
                "first": int(s["first"]), "end": int(s["end"]), "trades": int(s["trades"]),
                "eq_sha": hashlib.sha256(eq.tobytes()).hexdigest()[:16]})
    wp = P17.w_paths(E, B, _G["rb"], n, _G["sB"])["R_eq"]
    V17, _, _ = P17.compose(E, B, wp, _G["rebal_mask"])
    c, m = R13.window_stats(V17, 0, n, 0, n)
    out.append({"cell": 5, "r": r, "seed": P12_SEED0 + r, "cagr": float(c), "mdd": float(m), "vol": ann_vol(V17),
                "first": int(s["first"]), "end": int(s["end"]), "trades": int(s["trades"]),
                "eq_sha": hashlib.sha256(eq.tobytes()).hexdigest()[:16], "w_mean": float(wp.mean())})
    # 描述：P12 策略側本身（W1）
    c, m = R13.window_stats(E, 0, n, 0, n)
    out.append({"cell": 0, "r": r, "seed": P12_SEED0 + r, "cagr": float(c), "mdd": float(m), "vol": ann_vol(E),
                "first": int(s["first"]), "end": int(s["end"]), "trades": int(s["trades"]), "eq_sha": ""})
    return out


def setup_p12(cal, panel_path, px, log):
    from . import p4_features as P4F
    from . import researchp7 as P7
    from . import researchp17 as P17
    uni = D.load_universe().set_index("stock_id")["market"]
    panel = P4F.read_panel(panel_path)
    closes, opens = load_prices(set(panel["stock_id"]), cal, uni, px)
    sig = P7.build_sig_gate_b(panel, cal, closes, opens, start="2017-01-01", signal="B")
    acc = P7.accept_sig_b(sig)
    log(f"[P12 sig] 面板 {panel_path}｜驗收數 {acc}｜原件要 {P7.WANT_SIG_B}｜相同 {acc == P7.WANT_SIG_B}")
    w0, w1 = win_bounds(cal)
    bench = load_bench(cal)
    B = bench[w0:w1 + 1]
    rb = P17.rebal_days(cal, w0, w1)
    mask = np.zeros(w1 - w0 + 1, bool); mask[[int(t) for t in rb]] = True
    sB = {int(t): P17.sigma_at(B, int(t)) for t in rb}
    _G.update(sig12=sig, closes=closes, opens=opens, ncal=len(cal), w0=w0, w1=w1, B=B, rb=rb, rebal_mask=mask, sB=sB)
    return acc


def run_p12(procs, reps, log):
    with Pool(procs) as pool:
        res = pool.map(_one_p12, range(reps), chunksize=4)
    return pd.DataFrame([x for y in res for x in y])


# ═════════════ 各階段 ═════════════
def setup_and(cal, and_path, px, log):
    uni = D.load_universe().set_index("stock_id")["market"]
    AND = pd.read_csv(and_path, dtype={"sid": str})
    closes, opens = load_prices(set(AND["sid"]), cal, uni, px)
    miss = sorted(set(AND["sid"]) - set(closes))
    if miss:
        raise SystemExit(f"⛔ AND 訊號有 {len(miss)} 檔讀不到價格：{miss[:10]}")
    bench = load_bench(cal)
    w0, w1 = win_bounds(cal)
    _G.update(AND=AND, closes=closes, opens=opens, ncal=len(cal), bench=bench, regime=regime_mask(bench),
              w0=w0, w1=w1, first_all=int(AND["entry_pos"].min()))
    log(f"[AND] {and_path}｜{len(AND):,} 筆／{AND['sid'].nunique():,} 檔｜relvol 缺 {int(AND['relvol'].isna().sum()) if 'relvol' in AND else '—'}"
        f"｜entry_pos {AND['entry_pos'].min()}～{AND['entry_pos'].max()}（{cal[AND['entry_pos'].min()].date()}～{cal[AND['entry_pos'].max()].date()}）")


def run_cells(mode, procs, reps, cells, log):
    rows = []
    with Pool(procs) as pool:
        for cid in cells:
            t0 = time.time()
            st = pool.map(_one, [(cid, mode, r) for r in range(reps)], chunksize=4)
            df = pd.DataFrame(st); rows.append(df)
            md = df.median(numeric_only=True)
            log(f"  [{mode}] 格{cid:>2} {CELLS[cid - 1][2]}｜{CELLS[cid - 1][3]}：年化中位 {md['cagr']!r}／回落中位 {md['mdd']!r}／波動中位 {md['vol']:.6f}"
                f"｜first {int(df['first'].min())}～{int(df['first'].max())}｜{time.time() - t0:.0f}s")
    return pd.concat(rows, ignore_index=True)


def bench_row(cal, bench, a, b):
    seg = bench[a:b]
    c, m = R13.window_stats(seg / seg[0], 0, len(seg), 0, len(seg))
    return {"cagr": float(c), "mdd": float(m), "vol": ann_vol(seg)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["repro", "winonly", "main", "dataonly", "table"])
    ap.add_argument("--px", default="branch")
    ap.add_argument("--data", default=None, help="repro／winonly：把 D.DATA 指到這個 data 目錄（例：git archive 取出的舊快照）")
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--reps", type=int, default=REPS)
    ap.add_argument("--cells", type=int, nargs="*", default=None)
    ap.add_argument("--tag", default=None, help="輸出檔名後綴（預設＝stage）")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    tag = a.tag or a.stage
    logf = open(os.path.join(OUT, f"run_{tag}.log"), "a", encoding="utf-8")

    def log(x):
        print(x, flush=True); logf.write(x + "\n"); logf.flush()

    if a.stage == "table":
        from . import rerun17_table as T
        T.build(OUT, log); return
    log(f"===== rerun17 {a.stage} px={a.px} reps={a.reps} {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）=====")
    snap = a.stage in ("main", "dataonly")
    if snap:
        use_snapshot()
    elif a.data:
        D.DATA = os.path.expanduser(a.data)
    log(f"[資料] D.DATA ＝ {D.DATA}")
    cal = D.load_calendar()
    log(f"[日曆] {len(cal)} 根 {cal[0].date()}～{cal[-1].date()}")
    w0, w1 = win_bounds(cal)
    bench = load_bench(cal)
    bw = bench_row(cal, bench, w0, w1 + 1)
    log(f"[0050 主窗] 年化 {bw['cagr']!r}／回落 {bw['mdd']!r}／波動 {bw['vol']!r}｜錨 {ANCHOR}｜逐位元 {repr(bw['cagr']) == repr(ANCHOR[0]) and repr(bw['mdd']) == repr(ANCHOR[1])}")
    cells = a.cells or [c[0] for c in CELLS]
    p10p1 = [c for c in cells if CELLS[c - 1][4]["fam"] in ("P10", "P1", "P3B")]
    p12 = [c for c in cells if CELLS[c - 1][4]["fam"] in ("P14", "P17")]
    mode = "orig" if a.stage in ("repro", "dataonly") else "win"
    frames = []
    meta = {"stage": a.stage, "px": a.px, "data": D.DATA, "bench_win": bw}
    if p10p1:
        and_path = (os.path.join(OUT, "sig_edc6f", "and_signals.csv.gz") if snap
                    else os.path.join(HERE, "resultsp1", "and_signals_p1.csv.gz"))
        setup_and(cal, and_path, "branch" if snap else a.px, log)
        # 原窗 0050（P10／P1／P3 各自的全期窗：first_all～日曆尾），給中間版的對照
        meta["bench_orig"] = bench_row(cal, bench, _G["first_all"], len(cal))
        log(f"[0050 原窗] {cal[_G['first_all']].date()}～{cal[-1].date()}：{meta['bench_orig']}")
        df = run_cells(mode, a.procs, a.reps, p10p1, log); frames.append(df)
    if p12:
        if a.stage in ("winonly", "dataonly"):
            log("[P12] 窗本來就是主窗 ⇒ winonly／dataonly 不另跑（repro＝winonly、main＝dataonly）")
        else:
            panel = os.path.join(HERE, "resultsAFC", "panel.csv.gz") if snap else os.path.join(HERE, "resultsp4", "panel.csv.gz")
            meta["p12_accept"] = setup_p12(cal, panel, "branch" if snap else a.px, log)
            df = run_p12(a.procs, a.reps, log); df["mode"] = "win"; frames.append(df)
            for cid in (8, 5, 0):
                g = df[df["cell"] == cid]; md = g.median(numeric_only=True)
                log(f"  [P12] 格{cid}：年化中位 {md['cagr']!r}／回落中位 {md['mdd']!r}／波動中位 {md['vol']:.6f}｜first {int(g['first'].min())}")
    out = pd.concat(frames, ignore_index=True)
    out.insert(0, "stage", a.stage)
    out.to_csv(os.path.join(OUT, f"seeds_{tag}.csv"), index=False)
    json.dump(meta, open(os.path.join(OUT, f"meta_{tag}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完成] seeds_{tag}.csv {len(out):,} 列")


if __name__ == "__main__":
    main()
