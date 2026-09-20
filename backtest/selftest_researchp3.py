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
from backtest import research11 as R11  # noqa: E402
from backtest import researchp3 as R  # noqa: E402
from backtest import researchp9 as P9  # noqa: E402

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
    check(cl[:3] == [(30, None, "null"), (40, None, "null"), (40, None, "relvol")] and cl[3:5] == [(30, None, "relvol"), (20, None, "null")] and all(c[0] <= 8 for c in cl[5:]) and len(cl) == 3 + 2 + 14, f"格子：三主格＋兩對照格（輸）＋N≤8 共 {len(cl)} 格（P1 網格 N≤8 是 14 格，⚠ 登錄寫 16）")
    es2 = R.shuffle_exposure(e2, np.random.default_rng(5), "shift")
    k = int(np.random.default_rng(5).integers(1, len(e2)))
    check(np.allclose(es2, np.roll(e2, -k)) and abs(es2.mean() - e2.mean()) < 1e-12 and 1 <= k <= len(e2) - 1, f"shift 重排：e'_t＝e_(t+k)（k={k} ∈ [1,T−1]）、平均曝險相同")
    ac = lambda x: np.corrcoef(x[:-1], x[1:])[0, 1]
    ee = np.repeat(rng.uniform(0, 1, 60), 10)   # 有自相關的曝險
    check(abs(ac(R.shuffle_exposure(ee, np.random.default_rng(6), "shift")) - ac(ee)) < 0.05 and ac(R.shuffle_exposure(ee, np.random.default_rng(6), "day")) < 0.3, "shift 保住一階自相關、day 重排把它打掉")
    ist = R.idle_stats(np.array([0, 0, 0.5, 0, 0, 0, 1.0]))
    check(ist["idle_day_share"] == 5 / 7 and ist["longest_idle_run"] == 3 and abs(ist["avg_idle_frac"] - (1 - 1.5 / 7)) < 1e-12, "idle_stats：空手佔比 5/7、最長連續 3、平均閒置")
    jl = R.judge_cell((20, None, "null"), mk(0.2, -0.2, 0.2, -0.35), b, 100)
    check(jl["judge"].startswith("對照格"), "對照格（輸）不判定")
    print("[researchp3] 冒煙（真實 P1 訊號，一格三種子五重排）")
    out = tempfile.mkdtemp(prefix="p3_")
    r = subprocess.run([sys.executable, "-m", "backtest.researchp3", "--out", out, "--cells", "1", "--reps", "3", "--shuffles", "5", "--procs", "2"], cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))), capture_output=True, text=True)
    check(r.returncode == 0, f"rc={r.returncode} {r.stderr[-300:]}")
    if r.returncode == 0:
        S = pd.read_csv(os.path.join(out, "summary.csv"), comment="#"); sd = pd.read_csv(os.path.join(out, "seeds.csv"), comment="#")
        P = pd.read_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultsp1", "portfolio.csv"))
        check({"A_mdd_med", "B_mdd_med", "C1_mdd_p50_med", "C2_mdd_p50_med", "A_mdd_pct_in_C1_med", "AminusC1_mdd_med", "C1minusC2_mdd_med", "idle_day_share_med", "judge", "bench_mdd"} <= set(S.columns) and len(S) == 1 and S["N"].iloc[0] == 30, "summary.csv 欄位齊（丙1／丙2／前置）、第一格 N30 null")
        ref = P[(P.set == "AND") & (P.N == 30) & (P.rule.isna()) & (P.d == np.inf)]
        s0 = sd[sd.seed == 7000].iloc[0]
        check(len(ref) == 1 and abs(s0["A_slot"] - ref["slot"].iloc[0]) < 0.02, f"甲 N30 null 種子 7000 槽位 {s0['A_slot']:.3f} ≈ P1 portfolio 中位 {ref['slot'].iloc[0]:.3f}（同引擎同種子；⚠ 中位 vs 單種子，只驗量級）")
        check(((sd["B_slot"] - sd["A_slot"]).abs() < 0.05).all() and (sd["avg_exposure"] > 0).all() and (sd["B_trades"] > 0).all(), f"乙槽位與甲相差 < 5pp（同進場序列；bench 賣出扣成本可能少一點：{(sd['B_slot'] - sd['A_slot']).round(4).tolist()}）、平均曝險 > 0")
    # ───────────────────────────────── PREREGP9 2-C ⓑ（回測線 2026-09-20 15:10 追加；⛔ 不新增第 10 支自測檔）
    print("[researchp9] 引擎：弱勢日半個 slot")
    ncal9 = 20; sids9 = ["A", "B"]
    cl9 = {s_: np.linspace(10.0, 20.0, ncal9) for s_ in sids9}
    op9 = {s_: np.linspace(10.0, 20.0, ncal9) + 0.1 for s_ in sids9}
    sig9 = pd.DataFrame([{"sid": s_, "entry_pos": 5, "xpos_H5": 12,
                          "g_H5": cl9[s_][12] / op9[s_][5] - 1.0} for s_ in sids9])
    def sim9(**kw):
        return R11.simulate_mtm(sig9, "H5", 2, np.random.default_rng(3), cl9, op9, ncal9, return_equity=True, **kw)
    base9 = sim9()
    zeros9 = sim9(weak=np.zeros(ncal9, bool))
    check(np.array_equal(base9["equity"], zeros9["equity"]) and base9["cagr"] == zeros9["cagr"],
          "weak 全 False ⇒ 與不傳 weak 【逐位元】相同（新參數不動原版路徑）")
    allT9 = np.ones(ncal9, bool)
    half9 = sim9(weak=allT9)                                   # ⭐ 不傳 weak_size ⇒ 走【預設值 0.5】那條路
    check(abs(half9["hold_val"][5] / base9["hold_val"][5] - 0.5) < 1e-12 and base9["hold_val"][5] > 0,
          f"weak 全 True（⛔ 不傳 weak_size ⇒ 預設 0.5）⇒ 進場日持股市值恰為一半（{half9['hold_val'][5]:.6f} vs {base9['hold_val'][5]:.6f}）")
    one9 = sim9(weak=allT9, weak_size=1.0)
    check(np.array_equal(one9["equity"], base9["equity"]), "weak 全 True 但 weak_size=1.0 ⇒ 與基準逐位元相同（⇒ 縮的是 weak_size 不是別的）")
    check("max_pos_frac" not in base9, "report_maxw 預設 False ⇒ 回傳【沒有】max_pos_frac 這個鍵（原版回傳逐位元相同）")
    solo = R11.simulate_mtm(sig9, "H5", 1, np.random.default_rng(3), cl9, op9, ncal9, return_equity=True, report_maxw=True)
    want_mw = float(np.max(solo["hold_val"] / solo["equity"]))
    check(abs(solo["max_pos_frac"] - want_mw) < 1e-12 and 0 < solo["max_pos_frac"] <= 1,
          f"max_pos_frac ＝ 逐日 max(部位市值÷equity)＝{want_mw:.4f}（N=1 ⇒ 單一部位就是全部持股）")
    print("[researchp9] 弱勢旗標的時序與暖身")
    bn = np.full(200, 100.0); bn[120:125] = 90.0
    w9 = P9.weak_flags(bn, 200)
    check(not w9[:P9.MA_WIN].any(), f"暖身不足（前 {P9.MA_WIN} 天）weak 一律 False")
    check((not w9[120]) and w9[121] and w9[125] and (not w9[126]),
          "時序：t−1 收盤跌破才算 ⇒ 跌破當天(120) False、次日(121) True；回到均線上的次日(126) 才 False")
    check(int(w9.sum()) == 5, f"弱勢日數 ＝ 跌破段長度（平移一天、不增不減）：{int(w9.sum())}")
    print("[researchp9] 回落事件與分型")
    eq9 = np.array([90, 95, 98, 100, 90, 80, 74, 85, 95, 99, 101, 97, 93, 90, 92, 95], float)
    ev9 = P9.dd_events(eq9, 0, len(eq9))                        # ⭐ 不傳 thresh ⇒ 走【預設值 0.20】那條路
    check(len(ev9) == 1 and ev9[0]["peak"] == 3 and ev9[0]["trough"] == 6 and ev9[0]["recover"] == 10
          and abs(ev9[0]["dd"] + 0.26) < 1e-12 and ev9[0]["recovered"],
          f"一個 −26% 事件：高點 3 → 谷底 6 → 回到高點 10（⛔ 後面那段 −10.9% 不算）：{[(e['peak'], e['trough'], round(e['dd'], 4)) for e in ev9]}")
    check(len(P9.dd_events(np.array([100, 95, 90, 85, 95, 101], float), 0, 6)) == 0, "反向驗：只跌 15% ⇒ 0 個事件（⛔ 門檻是 20%）")
    k1, p2a, _ = P9.dd_type(np.array([100, 70, 69, 68, 67], float), 0, 4)
    k2, _, p5b = P9.dd_type(np.concatenate([[100.0], 100 * 0.99 ** np.arange(1, 41)]), 0, 40)
    k3, p2c, p5c = P9.dd_type(np.array([100, 92, 84.6, 79.6, 74.8, 70.3, 69.6, 68.9, 68.2, 67.5, 66.9], float), 0, 10)
    check(k1 == "單日暴跌型" and p2a >= 0.5, f"分型：最差 2 日占總跌幅 {p2a * 100:.1f}% ≥ 50% ⇒ 單日暴跌型")
    check(k2 == "延續下跌型" and p5b < 0.5, f"分型：40 天等速下跌、最差 5 日只占 {p5b * 100:.1f}% ⇒ 延續下跌型")
    check(k3 == "混合型" and p2c < 0.5 <= p5c, f"分型：最差2日 {p2c * 100:.1f}% < 50% ≤ 最差5日 {p5c * 100:.1f}% ⇒ 混合型")
    check(abs(P9.window_mdd(np.array([100, 90, 95, 80, 85], float), 1, 4) - (80 / 95 - 1)) < 1e-12,
          "window_mdd 用【窗內自己】的累積高點（95）⇒ −15.8%，⛔ 不是窗外的 100（−20%）")
    check(P9.ma_break_segments(bn, 100, 199) == [(120, 5)], f"跌破段：起日＝前一日仍在之上的那一天、段長 5：{P9.ma_break_segments(bn, 100, 199)}")
    check(P9.ma_break_segments(bn, 122, 199) == [] and P9.ma_break_segments(bn, 121, 130) == [],
          "⭐ 窗從【已經在均線之下】的那幾天開始 ⇒ 那一段**不算新訊號**（登錄 §7-1：訊號＝前一日仍在之上的第一天）"
          f"：{P9.ma_break_segments(bn, 122, 199)}")
    print("[researchp9] 母體月報酬與判定方向")
    cal9 = pd.DatetimeIndex(pd.date_range("2020-01-01", periods=40, freq="D"))
    cl10 = {"A": np.full(40, 100.0), "B": np.full(40, 100.0), "C": np.full(40, 100.0)}
    cl10["A"][39] = 110.0; cl10["B"][39] = 50.0; cl10["C"][30] = np.nan
    pn9 = pd.DataFrame([{"stock_id": "A", "eligible": True, "measure_date": pd.Timestamp("2020-02-05")},
                        {"stock_id": "B", "eligible": False, "measure_date": pd.Timestamp("2020-02-05")},
                        {"stock_id": "C", "eligible": True, "measure_date": pd.Timestamp("2020-02-05")}])
    MU9 = P9.month_universe_returns(pn9, cal9, cl10)
    check(len(MU9) == 1 and MU9["ym"].iloc[0] == "2020-02" and MU9["n"].iloc[0] == 1 and abs(MU9["ret"].iloc[0] - 0.10) < 1e-12,
          f"母體月報酬：只收 eligible（B 被擋）、兩端要有值（C 的上月底是 NaN）⇒ n=1、ret={MU9['ret'].iloc[0]:.4f}")
    check(bool(P9.passes(0.30, -0.30, 0.2403, -0.34)) and not bool(P9.passes(0.30, -0.40, 0.2403, -0.34)),
          "判定：年化夠且回落【較淺】才過；回落 −40% 深於 −34% ⇒ 不過（⛔ 負數的方向）")
    check(not bool(P9.passes(0.20, -0.30, 0.2403, -0.34)) and not bool(P9.passes(0.20, -0.40, 0.2403, -0.34)),
          "判定：年化不夠 ⇒ 不論回落多淺都不過（⛔ 兩條同時成立才算）")
    src9 = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "researchp9.py"), encoding="utf-8").read()
    check('_S["weak"] if arm == "b" else None' in src9, "呼叫點：基準組傳 weak=None（⛔ 不是傳全 False 的陣列繞過去）")
    check('passes(md["cagr"], md["mdd"], b_c, b_m)' in src9 and 'passes(md["ca"], md["ma"], b_ca, b_ma)' in src9,
          "呼叫點：主判定與 A 窗都走同一個 passes()（⛔ 沒有第二份不等式）")
    check("evs = dd_events(eb," in src9 and 'eb = eqs["base"]["equity"]' in src9, "呼叫點：事件用【基準組】的曲線找（追加一 §八：用 ⓑ 自己的會循環）")
    check('EV["saved_pp"] = (EV["mdd_win_b"] - EV["mdd_win_base"]) * 100' in src9, "呼叫點：救到幾 pp ＝ ⓑ 窗內回落 − 基準窗內回落（正值＝救到）")
    print("結果：", "全綠" if FAIL == 0 else f"✗ {FAIL} 條")
    sys.exit(1 if FAIL else 0)

# PREREGP9 突變（前後 rm -rf backtest/__pycache__）：weak 平移拿掉（w[:]=below）⇒ 時序條紅；slot*weak_size 改成不乘 ⇒ 半個 slot 條紅；\n#   dd_events 的門檻改 0.10 ⇒ 反向驗條紅；dd_type 的 p2>=0.50 改 >0.50 或兩型順序對調 ⇒ 分型條紅；window_mdd 用全序列高點 ⇒ 窗內條紅；\n#   passes 的 mdd >= 改 <= ⇒ 判定方向兩條紅；month_universe_returns 不濾 eligible ⇒ 母體月報酬條紅。\n# 突變（前後 rm -rf backtest/__pycache__）：rebuild 用 e_t 而非 e_{t−1} ⇒ 第 1 條紅；shuffle 不重排 ⇒ day 條紅；judge 的 h1 改 >= ⇒ H1 兩條紅；
#   N_MIN_MONTHS 改 20 ⇒ 還沒測條紅；MAIN_CELLS 少一格 ⇒ 格子條紅。
