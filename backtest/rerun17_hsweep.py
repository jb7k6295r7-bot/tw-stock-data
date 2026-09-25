# -*- coding: utf-8 -*-
"""裁定 seq187 §一甲／seq188 ①：#1（PREREG10 AND regime=True N10 H120，t−1 大盤閘版）持有天數敏感度。

⭐ 敏感度描述：⛔ 不計 N、⛔ 不拿最好的 H 換掉 120（掃參數挑最好 ＝ 事後配適）；H 只用使用者點名的 7 個。
H ∈ {90, 100, 110, 120, 130, 140, 150}；其餘（訊號、t−1 大盤閘、N10、200 顆種子 1000＋r、主窗、0050 錨）照 rerun17_regime_t1 一字不動。

出場欄 xpos_H{n}／g_H{n}：照原件產生器（research11.stock_features 的 fixed_exit(o, c, k, H, nb_sig[k])，
  nb_sig[k] ＝ next_bad[max(0, k−20)]、load_bars 同一支）逐列重算；⚠ 引擎慣例：出場根超出資料尾或碰到壞根 ⇒ xpos＝−1 ⇒ 該訊號不進模擬
  （H 越長、被這條剔掉的越多 ⇒ 逐 H 報剔除數）。
閘門（先過才跑）：
  閘一 0050 錨逐位元
  閘二 重算的 H20／H60／H120 出場欄與 and_signals.csv.gz 逐位元相同（xpos 整數、g 以 repr）
  閘三 H120 用新欄重跑 200 顆 ⇒ 與 resultsN17/regime_t1/seeds.csv 的 t1 階段 #1 逐位元相同（cagr／mdd／vol／first／end／trades／eq_sha）
    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.rerun17_hsweep [--procs 1] [--cell 1|13] [--end YYYY-MM-DD]

裁定 seq191（使用者「好優先」）：--cell 13 ＝ #13（P1 AND N20 d=inf relvol；⛔ 無大盤閘）同一套 H90～150
  ⚠ P1 族原件持有期 ＝ H60（rerun17._sim_engine 寫死 "H60"）⇒ 7 點＋原件 H60 一列；閘三改成 H60 對 rerun17_seeds.csv main #13 逐位元
  P1 路徑的 rule 由本支包一層傳入（其餘 d_max／pick／queue_days／log＝[] 照 rerun17._sim_engine 逐字）；輸出 resultsN17/hsweep13/
輸出 backtest/resultsN17/hsweep/：seeds.csv、cells.csv、sigcount.csv、run.log
"""
from __future__ import annotations

import argparse
import io
import os
import time

import numpy as np
import pandas as pd

from . import rerun17 as RR

RR.use_snapshot()
from . import data as D                  # noqa: E402
from . import research11 as R            # noqa: E402
from . import rerun17_table as RT        # noqa: E402

OUT = os.path.join(RR.OUT, "hsweep")
HS = [90, 100, 110, 120, 130, 140, 150]
GATE_H = [20, 60, 120]
RTP = dict(float_precision="round_trip")
CMP = ["cagr", "mdd", "vol", "first", "end", "trades", "eq_sha"]


def exits(AND, cal, mk, Hs):
    out = {H: (np.full(len(AND), -1, np.int64), np.full(len(AND), np.nan)) for H in Hs}
    bad_k = 0
    for sid, g in AND.groupby("sid"):
        B = R.load_bars(sid, mk[sid], cal)
        idx, o, c, nbar = B["idx"], B["o"], B["c"], B["next_bad"]
        for i, k, pos in zip(g.index.to_numpy(), g["k"].to_numpy(int), g["pos"].to_numpy(int)):
            if int(idx[k]) != pos:
                bad_k += 1; continue
            nb = nbar[max(0, k - 20)]
            for H in Hs:
                r = R.fixed_exit(o, c, k, H, nb)
                if r:
                    out[H][0][i] = int(idx[r[0]]); out[H][1][i] = r[1]
    if bad_k:
        raise SystemExit(f"⛔ k 與 pos 對不上 {bad_k} 列")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=1)
    ap.add_argument("--reps", type=int, default=RR.REPS)
    ap.add_argument("--cell", type=int, default=1, choices=[1, 13])
    ap.add_argument("--end", default=None, help="描述版：判讀窗尾改成這一天（含）之前最後一個交易日；⛔ 不跑閘三、另存子目錄")
    a = ap.parse_args()
    global OUT, HS
    H0 = 120 if a.cell == 1 else 60                  # 原件持有期
    if a.cell == 13:
        OUT = os.path.join(RR.OUT, "hsweep13")
        HS = [60] + HS
    if a.end:
        OUT = os.path.join(OUT, f"end_{a.end}")
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "a", encoding="utf-8")

    def log(x):
        print(x, flush=True); logf.write(x + "\n"); logf.flush()

    log(f"===== rerun17_hsweep procs={a.procs} reps={a.reps} {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）=====")
    cal = D.load_calendar()
    w0, w1 = RR.win_bounds(cal)
    bench = RR.load_bench(cal)
    bw = RR.bench_row(cal, bench, w0, w1 + 1)
    g1 = repr(bw["cagr"]) == repr(RR.ANCHOR[0]) and repr(bw["mdd"]) == repr(RR.ANCHOR[1])
    log(f"[閘一 0050 錨] {bw['cagr']!r}／{bw['mdd']!r}｜逐位元 {g1}")
    if not g1:
        raise SystemExit("⛔ 閘一不過")
    if a.end:
        w1 = int(cal.searchsorted(pd.Timestamp(a.end), side="right") - 1)
        bw = RR.bench_row(cal, bench, w0, w1 + 1)
        log(f"[描述版窗尾] {cal[w1].date()}（w1＝{w1}）｜0050 同窗 {bw['cagr']!r}／{bw['mdd']!r}")

    and_path = os.path.join(RR.OUT, "sig_edc6f", "and_signals.csv.gz")
    RR.setup_and(cal, and_path, "branch", log)
    G = RR._G
    if a.end:
        G["w1"] = w1                               # sig_for 的進場上限與 win_metrics 的窗尾都讀 _G["w1"]
    AND = G["AND"]
    if not AND.index.equals(pd.RangeIndex(len(AND))):
        raise SystemExit("⛔ AND 索引不是 0..n−1")
    mk = D.load_universe().set_index("stock_id")["market"]
    t0 = time.time()
    allH = sorted(set(HS) | set(GATE_H))
    EX = exits(AND, cal, mk, allH)
    log(f"[出場欄] 重算 {len(AND):,} 列 × {len(allH)} 個 H｜{time.time() - t0:.0f}s")
    # ⚠ 原件管線：stock_features 的 g_H60／g_H120 先寫 signals_S.csv.gz、再用【預設精度】read_csv 讀回（rerun17_build ②→③）⇒ 可差 1 ulp；
    #   g_H20 由 attach_features 另算、沒經過這一道。⇒ H60 以上的新欄照同一道「to_csv → 預設 read_csv」轉一次，口徑才與 H120 相同
    for H in allH:
        if H == 20:
            continue
        s = pd.DataFrame({"g": EX[H][1]}).to_csv(index=False)
        EX[H] = (EX[H][0], pd.read_csv(io.StringIO(s))["g"].to_numpy(float))
    bad = {}
    ANDr = pd.read_csv(and_path, dtype={"sid": str}, **RTP)      # ⚠ setup_and 用預設 float 解析（可差 1 ulp）⇒ 對檔要 round_trip 讀
    assert (ANDr["sid"].to_numpy() == AND["sid"].to_numpy()).all()
    for H in GATE_H:
        xp, gg = EX[H]
        ox = ANDr[f"xpos_H{H}"].to_numpy(int); og = ANDr[f"g_H{H}"].to_numpy(float)
        dmax = float(np.nanmax(np.abs(gg - og)))
        log(f"  H{H}：g 最大差 {dmax:.2e}")
        nx = int((xp != ox).sum())
        ng = int(sum((np.isnan(p) != np.isnan(q)) or (not np.isnan(p) and repr(float(p)) != repr(float(q))) for p, q in zip(gg, og)))
        bad[H] = (nx, ng)
    g2 = all(v == (0, 0) for v in bad.values())
    log(f"[閘二 H20／H60／H120 出場欄逐位元] 不同（xpos, g）{bad}｜{g2}")
    if not g2:
        raise SystemExit("⛔ 閘二不過")

    # setup_and 讀 and_signals 時又是預設精度 ⇒ 模擬實際用的值再過一道；H60／H120 驗「兩道後」與 _G["AND"] 逐位元同
    def _rt(x):
        return pd.read_csv(io.StringIO(pd.DataFrame({"g": x}).to_csv(index=False)))["g"].to_numpy(float)
    g2b = {}
    for H in (60, 120):
        y = _rt(EX[H][1]); z = AND[f"g_H{H}"].to_numpy(float)
        g2b[H] = int(sum((np.isnan(p) != np.isnan(q)) or (not np.isnan(p) and repr(float(p)) != repr(float(q))) for p, q in zip(y, z)))
    log(f"[閘二b 再過一道預設讀 vs 模擬用的 _G['AND']] 不同 {g2b}")
    if any(g2b.values()):
        raise SystemExit("⛔ 閘二b不過")
    reg = G["regime"].copy()
    reg_t1 = np.zeros_like(reg); reg_t1[1:] = reg[:-1]
    for H in HS:
        if H in GATE_H:
            continue
        AND[f"xpos_H{H}"] = EX[H][0]; AND[f"g_H{H}"] = _rt(EX[H][1])
    G["regime"] = reg_t1
    e = AND["entry_pos"].to_numpy()
    inwin = (e >= w0) & (e <= w1)
    on = (reg_t1[e] if a.cell == 1 else np.ones(len(e), bool)) & inwin     # #13 無大盤閘
    sc = []
    for H in HS:
        x = AND[f"xpos_H{H}"].to_numpy()
        sc.append({"H": H, "窗內t1判開訊號": int(on.sum()), "進模擬（xpos≥0）": int((on & (x >= 0)).sum()),
                   "剔除（出場超出資料尾或碰壞根）": int((on & (x < 0)).sum()),
                   "其中出場超出資料尾": int((on & (x < 0) & (e + H - 1 >= len(cal))).sum())})
    SC = pd.DataFrame(sc); SC.to_csv(os.path.join(OUT, "sigcount.csv"), index=False)
    log(SC.to_string(index=False))

    base = len(RR.CELLS)
    ids = {}
    for j, H in enumerate(HS):
        cid = base + j + 1
        if a.cell == 1:
            RR.CELLS.append((cid, "敏感度", "PREREG10", f"AND｜regime=True(t−1)｜N10｜H{H}", dict(fam="P10", reg=True, N=10, rule=f"H{H}")))
        else:
            RR.CELLS.append((cid, "敏感度", "P1", f"AND｜N20｜d=inf｜relvol｜H{H}", dict(fam="P1", N=20, d=None, pick="relvol", rule=f"H{H}")))
        ids[H] = cid
        assert RR.CELLS[cid - 1][4]["rule"] == f"H{H}"
    _orig = RR._sim_engine

    def _sim2(sp, sig, seed):                        # P1 路徑：只把寫死的 "H60" 換成 sp["rule"]，其餘照 rerun17._sim_engine 逐字
        if sp["fam"] == "P1" and "rule" in sp:
            kw = dict(d_max=sp["d"], pick=sp["pick"], queue_days=RR.P1_QUEUE if sp["d"] is not None else 0, return_equity=True)
            return RR.R.simulate_mtm(sig, sp["rule"], sp["N"], np.random.default_rng(seed), RR._G["closes"], RR._G["opens"], RR._G["ncal"],
                                     log=[], **kw)
        return _orig(sp, sig, seed)
    RR._sim_engine = _sim2
    t0 = time.time()
    d = RR.run_cells("win", a.procs, a.reps, [ids[H] for H in HS], log)
    d.insert(0, "H", d["cell"].map({v: k for k, v in ids.items()}))
    log(f"[跑完] {time.time() - t0:.0f}s")

    if a.cell == 1:
        ref = pd.read_csv(os.path.join(RR.OUT, "regime_t1", "seeds.csv"), dtype={"eq_sha": str}, **RTP)
        ref = ref[(ref["stage"] == "t1") & (ref["cell"] == 1)].sort_values("r").reset_index(drop=True)
    else:
        ref = pd.read_csv(os.path.join(RR.OUT, "rerun17_seeds.csv"), dtype={"eq_sha": str}, **RTP)
        ref = ref[(ref["stage"] == "main") & (ref["cell"] == 13)].sort_values("r").reset_index(drop=True)
    mine = d[d["H"] == H0].sort_values("r").reset_index(drop=True)
    diff = {}
    for c in CMP:
        if c in ("cagr", "mdd", "vol"):
            diff[c] = int(sum(repr(float(p)) != repr(float(q)) for p, q in zip(mine[c], ref[c])))
        elif c == "eq_sha":
            diff[c] = int(sum(str(p) != str(q) for p, q in zip(mine[c], ref[c])))
        else:
            diff[c] = int(sum(int(p) != int(q) for p, q in zip(mine[c], ref[c])))
    g3 = len(mine) == len(ref) == a.reps and all(v == 0 for v in diff.values())
    log(f"[閘三 H{H0} 對原件 #{a.cell}] 不同 {diff}｜逐位元 {g3}" + ("（描述版窗尾不同 ⇒ 本來就不會同，⛔ 不當閘）" if a.end else ""))
    if not g3 and not a.end:
        d.to_csv(os.path.join(OUT, "seeds_gatefail.csv"), index=False)
        raise SystemExit("⛔ 閘三不過")
    d.to_csv(os.path.join(OUT, "seeds.csv"), index=False)

    b_c, b_m = bw["cagr"], bw["mdd"]
    h120 = d[d["H"] == H0].set_index("r")          # 名稱沿用 h120（#1 的原件 H）；#13 時是 H60
    r120 = float(h120["cagr"].median()) / abs(float(h120["mdd"].median()))
    rows = []
    for H in HS:
        g = d[d["H"] == H].set_index("r")
        c, m, v = float(g["cagr"].median()), float(g["mdd"].median()), float(g["vol"].median())
        lab, ratio, extra = RT.label(c, m, b_c, b_m)
        dc = g["cagr"] - h120["cagr"]; dm = g["mdd"] - h120["mdd"]
        rows.append({"H": H, "原件": H == H0, "年化中位": c, "回落中位": m, "比值": ratio, "年化波動中位": v, "標籤（對0050）": lab, "深淺註": extra,
                     "年化p10": float(g["cagr"].quantile(.1)), "年化p90": float(g["cagr"].quantile(.9)),
                     "回落p10": float(g["mdd"].quantile(.1)), "回落p90": float(g["mdd"].quantile(.9)),
                     f"對H{H0}_年化中位差pp": (c - float(h120["cagr"].median())) * 100,
                     f"對H{H0}_回落中位差pp": (m - float(h120["mdd"].median())) * 100,
                     f"對H{H0}_比值差": ratio - r120,
                     f"同顆種子_年化高於H{H0}": int((dc > 0).sum()), f"同顆種子_回落淺於H{H0}": int((dm > 0).sum()),
                     "同顆種子_兩項皆好": int(((dc > 0) & (dm > 0)).sum()), "同顆種子_兩項皆差": int(((dc < 0) & (dm < 0)).sum()),
                     "trades中位": float(g["trades"].median()), "種子數": len(g)})
    C = pd.DataFrame(rows)
    C.to_csv(os.path.join(OUT, "cells.csv"), index=False)
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        log(C.to_string(index=False))
    log(f"[0050] {b_c!r}／{b_m!r}／比值 {b_c / abs(b_m)!r}")


if __name__ == "__main__":
    main()
