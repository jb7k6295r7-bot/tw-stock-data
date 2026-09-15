"""researchp3 自測——合成序列為主；末條用真實 P1 訊號跑一格三種子五重排（冒煙，不判定）。
① exposure_series＋rebuild 逐位元重現甲的權益（e 不重排）；② 重排後平均曝險相同、mode=month 每月塊內容整塊搬；③ 常數曝險 ⇒ 丙＝甲；
④ p1_win 六條件；⑤ judge：主格 H1 成立／否證、N≤8 H2、ⓑ 分不出、n<24；⑥ cells：三主格在前、其餘 N ≤ 8；⑦ 冒煙：summary.csv 欄位齊、甲對 P1 portfolio.csv 同種子同值。"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest import researchp3 as R  # noqa: E402

FAIL = 0


def check(cond, msg):
    global FAIL
    try:
        ok = bool(cond)
    except Exception as e:  # noqa: BLE001
        ok = False; msg += f"（炸掉：{e!r}）"
    print(("  ✓ " if ok else "  ✗ ") + msg)
    if not ok:
        FAIL += 1


if __name__ == "__main__":
    rng = np.random.default_rng(0); n = 600
    r_stock = rng.normal(0.0005, 0.02, n); e = np.clip(rng.uniform(0, 1, n), 0, 1); e[:5] = 0.0
    eq = np.empty(n); eq[0] = 1.0
    for t in range(1, n):
        eq[t] = eq[t - 1] * (1 + e[t - 1] * r_stock[t])
    hv = eq * e
    print("[researchp3] 曝險分解")
    e2, r_inv, nz = R.exposure_series(eq, hv, 0, n)
    check(np.allclose(e2, e) and np.allclose(R.rebuild(e2, r_inv), eq, rtol=1e-12, atol=1e-12) and nz == 5, f"e 還原、rebuild 逐位元重現甲、零曝險日 {nz}")
    check(np.allclose(r_inv[6:], r_stock[6:]), "e>0 的日子 r_inv＝持股報酬")
    es = R.shuffle_exposure(e2, np.random.default_rng(1), "day")
    check(abs(es.mean() - e2.mean()) < 1e-12 and sorted(es) == sorted(e2) and not np.allclose(es, e2), "day 重排：平均曝險相同、多重集相同、順序變了")
    mids = np.repeat(np.arange(30), 20)
    em = R.shuffle_exposure(e2, np.random.default_rng(2), "month", mids)
    blocks_src = {tuple(np.round(e2[mids == m], 12)) for m in range(30)}
    check(all(tuple(np.round(em[mids == m], 12)) in blocks_src for m in range(30)) and abs(em.mean() - e2.mean()) < 1e-9, "month 重排：每個月塊的內容整塊來自某個原月塊、平均曝險相同")
    ec = np.full(n, 0.7); eqc = R.rebuild(ec, r_inv); eqc2 = R.rebuild(R.shuffle_exposure(ec, np.random.default_rng(3), "day"), r_inv)
    check(np.allclose(eqc, eqc2), "常數曝險 ⇒ 重排後權益不變")
    print("[researchp3] 判定")
    b = {"c": 0.10, "m": -0.30, "ca": 0.08, "ma": -0.25, "cb": 0.12, "mb": -0.30}
    def mk(A_c, A_m, B_c, B_m, spread=0.0, reps=50):
        d = pd.DataFrame({"A_cagr": A_c + np.linspace(-spread, spread, reps), "A_mdd": A_m + np.linspace(-spread, spread, reps), "A_ca": A_c, "A_ma": A_m, "A_cb": A_c, "A_mb": A_m,
                          "B_cagr": B_c + np.linspace(-spread, spread, reps), "B_mdd": B_m + np.linspace(spread, -spread, reps), "B_ca": B_c, "B_ma": B_m, "B_cb": B_c, "B_mb": B_m})
        return d
    md = mk(0.2, -0.2, 0.2, -0.35).median(numeric_only=True)
    check(R.p1_win(md, "A", b) and not R.p1_win(md, "B", b), "p1_win：甲（年化高、回落淺）贏、乙（回落 −35% 深於 0050）沒贏")
    j = R.judge_cell((30, None, "null"), mk(0.2, -0.2, 0.2, -0.35), b, 100)
    check(j["judge"].startswith("H1 成立") and j["win_A"] and not j["win_B"], "主格：乙回落 ≤ 0050 ⇒ H1 成立")
    j2 = R.judge_cell((40, None, "relvol"), mk(0.2, -0.2, 0.22, -0.22), b, 100)
    check(j2["judge"].startswith("H1 否證") and j2["win_B"], "主格：乙仍淺於 0050 ⇒ H1 否證、乙 win")
    j3 = R.judge_cell((30, None, "null"), mk(0.2, -0.2, 0.2, -0.2, spread=0.05), b, 100)
    check("分不出" in j3["judge"] and j3["undistinguishable"], "乙−甲 p10～p90 含 0 ⇒ ⓑ 分不出")
    j4 = R.judge_cell((5, None, "null"), mk(0.05, -0.5, 0.06, -0.5), b, 100); j5 = R.judge_cell((5, None, "null"), mk(0.05, -0.5, 0.2, -0.2), b, 100)
    check(j4["judge"].startswith("H2 成立") and j5["judge"].startswith("H2 否證"), "N≤8：乙下沒贏 ⇒ H2 成立；出現贏格 ⇒ H2 否證")
    check(R.judge_cell((30, None, "null"), mk(0.2, -0.2, 0.2, -0.35), b, 23)["judge"].startswith("還沒測"), "有效月 23 ⇒ 還沒測（⚠ 寫死 24）")
    cl = R.cells()
    check(cl[:3] == [(30, None, "null"), (40, None, "null"), (40, None, "relvol")] and all(c[0] <= 8 for c in cl[3:]) and len(cl) == 3 + 14, f"格子：三主格＋N≤8 共 {len(cl)} 格（P1 網格 N≤8 是 14 格，⚠ 登錄寫 16）")
    print("[researchp3] 冒煙（真實 P1 訊號，一格三種子五重排）")
    out = tempfile.mkdtemp(prefix="p3_")
    r = subprocess.run([sys.executable, "-m", "backtest.researchp3", "--out", out, "--cells", "1", "--reps", "3", "--shuffles", "5", "--procs", "2"], cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))), capture_output=True, text=True)
    check(r.returncode == 0, f"rc={r.returncode} {r.stderr[-300:]}")
    if r.returncode == 0:
        S = pd.read_csv(os.path.join(out, "summary.csv"), comment="#"); sd = pd.read_csv(os.path.join(out, "seeds.csv"), comment="#")
        P = pd.read_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultsp1", "portfolio.csv"))
        check({"A_mdd_med", "B_mdd_med", "C_mdd_p50_med", "A_mdd_pct_in_C_med", "judge", "bench_mdd"} <= set(S.columns) and len(S) == 1 and S["N"].iloc[0] == 30, "summary.csv 欄位齊、第一格 N30 null")
        ref = P[(P.set == "AND") & (P.N == 30) & (P.rule.isna()) & (P.d == np.inf)]
        s0 = sd[sd.seed == 7000].iloc[0]
        check(len(ref) == 1 and abs(s0["A_slot"] - ref["slot"].iloc[0]) < 0.02, f"甲 N30 null 種子 7000 槽位 {s0['A_slot']:.3f} ≈ P1 portfolio 中位 {ref['slot'].iloc[0]:.3f}（同引擎同種子；⚠ 中位 vs 單種子，只驗量級）")
        check(((sd["B_slot"] - sd["A_slot"]).abs() < 0.05).all() and (sd["avg_exposure"] > 0).all() and (sd["B_trades"] > 0).all(), f"乙槽位與甲相差 < 5pp（同進場序列；bench 賣出扣成本可能少一點：{(sd['B_slot'] - sd['A_slot']).round(4).tolist()}）、平均曝險 > 0")
    print("結果：", "全綠" if FAIL == 0 else f"✗ {FAIL} 條")
    sys.exit(1 if FAIL else 0)

# 突變（前後 rm -rf backtest/__pycache__）：rebuild 用 e_t 而非 e_{t−1} ⇒ 第 1 條紅；shuffle 不重排 ⇒ day 條紅；judge 的 h1 改 >= ⇒ H1 兩條紅；
#   N_MIN_MONTHS 改 20 ⇒ 還沒測條紅；MAIN_CELLS 少一格 ⇒ 格子條紅。
