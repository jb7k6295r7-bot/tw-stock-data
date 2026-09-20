"""researchp2 自測：① parent_of 映射；② 逐日標籤的兩個月遲滯與 ffill；③ cap_fn 甲／丙／乙的擋法（合成三檔同母類股）；
④ simulate_mtm 預設 cap_fn=None 與原版逐位元相同（合成資料）；⑤ 重疊度；⑥ 判定函式的四個出口；⑦ 種子區間不重疊。
rc != 0 或輸出含 ✗ 才算紅。

    python3 -m backtest.selftest_researchp2
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from . import research11 as R
from . import researchp2 as P2

FAIL = 0


def check(cond, msg):
    global FAIL
    print(("  ✓ " if cond else "  ✗ ") + msg)
    FAIL += 0 if cond else 1


def t_parent():
    check(P2.parent_of("半導體業") == "電子" and P2.parent_of("其他電子業") == "電子", "半導體業／其他電子業 → 電子")
    check(P2.parent_of("化學工業") == "化學生技醫療" and P2.parent_of("生技醫療業") == "化學生技醫療", "化學工業／生技醫療業 → 化學生技醫療")
    check(P2.parent_of(P2.KY_LABEL) == P2.KY_LABEL and P2.parent_of("水泥工業") == "水泥工業", "KY 自成一組、其餘各自一組")
    check(len(P2.ELEC) == 8 and P2.MAX_SUB == 2 and P2.MAX_PAR == 2 and P2.MDD_MIN_DIFF == 0.03 and P2.COST_ANCHOR == 0.00585 and P2.OVERLAP_MAX == 0.90, "常數寫死：電子 8 業、上限 2／2、3pp、0.585%、重疊 90%")


def t_labels():
    cal = pd.DatetimeIndex(pd.bdate_range("2024-01-02", "2024-06-28"))
    ind = pd.DataFrame({"A": ["水泥工業", "水泥工業", np.nan, "鋼鐵工業"], "B": [np.nan, "半導體業", "半導體業", "半導體業"]}, index=["2023-11", "2023-12", "2024-01", "2024-02"])
    sub, par, vocab = P2.daily_labels(ind, cal, ["A", "B", "Z"])
    lab = lambda s, d: vocab[sub[s][int(np.searchsorted(cal, pd.Timestamp(d)))]]
    check(lab("A", "2024-01-15") == "水泥工業" and lab("A", "2024-04-15") == "鋼鐵工業", "A：1 月用 2023-11、4 月用 2024-02（往前兩個月）")
    check(lab("A", "2024-03-15") == "水泥工業", "A：3 月目標期 2024-01 是 NaN ⇒ ffill 到 2023-12 的水泥")
    check(lab("B", "2024-01-15") == P2.KY_LABEL and lab("B", "2024-02-15") == "半導體業", "B：2023-11 沒有 ⇒ 1 月是 KY／無產業別，2 月起半導體")
    check(lab("Z", "2024-05-15") == P2.KY_LABEL and vocab[par["B"][-1]] == "電子", "不在面板 ⇒ KY／無產業別；B 的母類股＝電子")
    tp = P2.target_periods(pd.DatetimeIndex([pd.Timestamp("2024-01-10"), pd.Timestamp("2024-02-10")]))
    check(tp == ["2023-11", "2023-12"], f"目標期跨年：{tp}")


def _synthetic(n_days=60, sids=("A", "B", "C", "D")):
    closes = {s: np.full(n_days, 100.0) + i for i, s in enumerate(sids)}; opens = {s: c.copy() for s, c in closes.items()}
    sig = pd.DataFrame({"sid": list(sids), "entry_pos": [5] * len(sids), "xpos_H60": [25] * len(sids), "g_H60": [0.05, 0.04, 0.03, 0.02], "month": ["2024-01"] * len(sids)})
    return sig, closes, opens


def t_cap():
    sig, closes, opens = _synthetic()
    n = 60
    sub = {"A": np.full(n, 1), "B": np.full(n, 1), "C": np.full(n, 2), "D": np.full(n, 3)}     # A、B 同子類股；C 另一子類股；D 別的
    par = {"A": np.full(n, 10), "B": np.full(n, 10), "C": np.full(n, 10), "D": np.full(n, 20)}  # A、B、C 同母類股
    jia = P2.make_cap("甲", sub, par); bing = P2.make_cap("丙", sub, par)
    check(P2.make_cap("乙", sub, par) is None, "乙 ⇒ cap_fn None（原版路徑）")
    check(jia("B", 3, {"A"}) and not jia("B", 3, {"A", "C"}) and not jia("C", 3, {"A", "B"}), "甲：母類股已 2 檔 ⇒ 擋；同母類股 1 檔 ⇒ 可進")
    check(bing("C", 3, {"A", "B"}) is False and bing("C", 3, {"A"}) and bing("D", 3, {"A", "B"}), "丙：只看母類股 ≤2")
    sub2 = {"A": np.full(n, 1), "B": np.full(n, 1), "C": np.full(n, 1), "D": np.full(n, 3)}; par2 = {k: np.full(n, 99) for k in "ABC"} | {"D": np.full(n, 20)}
    jia2 = P2.make_cap("甲", sub2, par2)
    check(jia2("B", 0, {"A"}) and not jia2("C", 0, {"A", "B"}), "甲：子類股滿 2 也擋（母類股上限另設很大時）")
    # 用引擎：四檔同日、N=4；甲 ⇒ 母類股 10 只能進兩檔（A、B 或 A、C…看隨機順序）、D 進 ⇒ 進 3 檔、cap 1 檔
    lg = []
    s = R.simulate_mtm(sig, "H60", 4, np.random.default_rng(0), closes, opens, n, return_equity=True, log=lg, cap_fn=P2.make_cap("甲", sub, par))
    ins = [r["sid"] for r in lg if r["reason"] == "in"]; caps = [r["sid"] for r in lg if r["reason"] == "cap"]
    check(len(ins) == 3 and len(caps) == 1 and "D" in ins and caps[0] in ("A", "B", "C"), f"引擎＋甲：進 {ins}、cap {caps}（母類股 10 只進兩檔、D 進）")
    check(s["trades"] == 3, "trades 與 in 一致")
    # cap 擋掉的名額讓給下一個：N=2、順序若先 A 再 B（同子類股）⇒ B 被 cap，C 或 D 補上 ⇒ 仍進 2 檔
    lg2 = []
    R.simulate_mtm(sig, "H60", 2, np.random.default_rng(1), closes, opens, n, log=lg2, cap_fn=P2.make_cap("甲", sub2 | {"D": np.full(n, 3)}, par2))
    ins2 = [r["sid"] for r in lg2 if r["reason"] == "in"]
    check(len(ins2) == 2, f"N=2：被 cap 的名額讓給下一個候選 ⇒ 仍進 2 檔（{ins2}）")


def t_default_identical():
    sig, closes, opens = _synthetic()
    a = R.simulate_mtm(sig, "H60", 2, np.random.default_rng(7), closes, opens, 60, return_equity=True)
    b = R.simulate_mtm(sig, "H60", 2, np.random.default_rng(7), closes, opens, 60, return_equity=True, cap_fn=None)
    check(np.array_equal(a["equity"], b["equity"]) and a["trades"] == b["trades"] and a["cagr"] == b["cagr"], "cap_fn=None 與原呼叫逐位元相同")
    always = lambda sid, t, h: True
    c = R.simulate_mtm(sig, "H60", 2, np.random.default_rng(7), closes, opens, 60, return_equity=True, cap_fn=always)
    check(np.array_equal(a["equity"], c["equity"]) and a["trades"] == c["trades"], "cap_fn 永遠放行 ⇒ 與原版同（同 rng 順序）")


def _stop_fixture(n=40):
    """PREREGP7 的手工序列：A 先漲到 120 再回落 107（trail 10% 咬、fix 10% 不咬）；
    B 一路跌到 85（fix 10% 咬）；C 漲到 170 後回落 135（排程出場 g=+0.80 是右尾，trail 10% 會砍掉它）。"""
    a = np.full(n, 100.0); a[6] = 110; a[7] = 115; a[8] = 120; a[9] = 112; a[10] = 107; a[11:] = 109
    b = np.full(n, 100.0); b[6] = 97; b[7] = 94; b[8] = 91; b[9] = 88; b[10] = 85; b[11:] = 86
    c = np.full(n, 100.0); c[6:9] = [130, 150, 170]; c[9] = 140; c[10] = 135; c[11:] = 180
    closes = {"A": a, "B": b, "C": c}
    opens = {k: v.copy() for k, v in closes.items()}
    sig = pd.DataFrame({"sid": ["A", "B", "C"], "entry_pos": [5, 5, 5], "xpos_H60": [20, 20, 20],
                        "g_H60": [float(a[20] / a[5] - 1), float(b[20] / b[5] - 1), float(c[20] / c[5] - 1)]})
    return sig, closes, opens


def t_stop():
    """PREREGP7（策略線 0945）：停損兩族。⛔ 判準是手算的出場日與出場價，不是總量。"""
    sig, closes, opens = _stop_fixture()
    n = 40
    run = lambda stop: R.simulate_mtm(sig, "H60", 3, np.random.default_rng(11), closes, opens, n, return_equity=True, log=[], stop=stop)
    # ⭐ 逐位元回歸：stop=None 與【改動前】的舊版同一組數字（2026-09-20 從 HEAD 那一版抓的基準，⛔ 寫死）
    base = run(None)
    check(abs(base["cagr"] - 22.296123610477732) < 1e-12 and abs(base["mdd"] - (-0.14173228346456707)) < 1e-12 and base["trades"] == 3,
          f"stop=None 與改動前逐位元相同（cagr {base['cagr']:.12f}、mdd {base['mdd']:.12f}）")
    eq = [round(float(x), 12) for x in base["equity"][4:25]]
    check(eq == [1.0, 1.0, 1.123333333333, 1.196666666667, 1.27, 1.133333333333, 1.09, 1.25, 1.25, 1.25, 1.25, 1.25, 1.25, 1.25, 1.25, 1.25, 1.24415, 1.24415, 1.24415, 1.24415, 1.24415],
          "stop=None 的逐日權益也逐位元相同")
    check("stop_exits" not in base, "⛔ stop=None 不多出 stop_* 那幾個鍵（回傳形狀不變）")
    # fix 10%：B 第 10 天收 85 ≤ 進場價 100×0.9 ⇒ 第 11 天結清、記 85/100−1 ＝ −15%；A（107）與 C（135）不咬
    fx = run(("fix", 0.10))
    check(fx["stop_exits"] == 1 and fx["stop_max_same_day"] == 1, f"fix 10%：只有 B 觸發（實得 {fx['stop_exits']} 筆）")
    check(fx["stop_days"] == [(9, 1)], f"fix 10%：觸發日＝第 9 天（B 收 88 ≤ 100×0.9 的**第一天**；第 8 天收 91 還在線上）；實得 {fx['stop_days']}")
    check(abs(fx["stop_rate"] - 1 / 3) < 1e-12, "停損出場率＝1/3（⛔ 分母是 trades）")
    check(fx["stop_cut_right_tail"] == 0, "fix 10% 沒砍到右尾（B 排程出場是 −14%）")
    # trail 10%：A 峰 120 ⇒ 線 108，第 10 天收 107 ⇒ 咬，記 107/100−1 ＝ +7%
    #            C 峰 170 ⇒ 線 153，第 9 天收 140 ⇒ 咬（第 10 天結清），而它排程出場是 +80% ⇒ 右尾被砍掉 1 筆
    #            B 峰 100 ⇒ 線 90，第 9 天收 88 ⇒ 咬
    tr = run(("trail", 0.10))
    check(tr["stop_exits"] == 3, f"trail 10%：三檔全咬（實得 {tr['stop_exits']}）⇒ ⭐ 同一個 X 下 trail 比 fix 敏感得多")
    check(tr["stop_cut_right_tail"] == 1, f"trail 10% 砍掉 1 筆原本會賺 > 50% 的（C 排程 +80%）；實得 {tr['stop_cut_right_tail']}")
    check(max(n_ for _, n_ in tr["stop_days"]) == tr["stop_max_same_day"] and tr["stop_max_same_day"] >= 2,
          f"單日觸發家數最大值＝{tr['stop_max_same_day']}（B 與 C 同一天破線）")
    # ⭐ 沒有前視：第 10 天破線 ⇒ 第 10 天【還在持倉】、第 11 天才結清
    check(abs(float(fx["equity"][9]) - float(base["equity"][9])) < 1e-12, "⭐ 觸發日（第 9 天）當天的權益與不停損相同 ⇒ ⛔ 沒有前視（那天還在持倉）")
    check(abs(float(fx["equity"][11]) - float(base["equity"][11])) > 1e-9, "第 10 天結清、第 11 天起權益才不同（⇒ 結清發生在觸發日之後）")
    # ⭐ 記帳用觸發日收盤：B 的實現報酬＝85/100−1
    check(abs(float(fx["equity"][-1]) - float(run(("fix", 0.10))["equity"][-1])) < 1e-12, "同參數重跑逐位元相同（決定性）")
    # 放寬到不可能觸發 ⇒ 回到原版數字
    loose = run(("fix", 0.99))
    check(abs(loose["cagr"] - base["cagr"]) < 1e-12 and loose["stop_exits"] == 0, "X 大到不可能觸發 ⇒ 與 stop=None 逐位元相同")
    # ⭐ 記帳用的是【觸發日】的收盤，⛔ 不是結清日的：單檔單槽 ⇒ 期末權益可以手算
    solo = pd.DataFrame({"sid": ["B"], "entry_pos": [5], "xpos_H60": [20], "g_H60": [float(closes["B"][20] / closes["B"][5] - 1)]})
    one = R.simulate_mtm(solo, "H60", 1, np.random.default_rng(3), closes, opens, n, return_equity=True, stop=("fix", 0.10))
    want = 1.0 * (1 + (88.0 / 100.0 - 1.0) - R.COST)          # 觸發日（第 9 天）收 88；⛔ 結清日（第 10 天）是 85
    check(abs(float(one["equity"][-1]) - want) < 1e-12, f"單檔單槽：期末權益＝1+(88/100−1)−成本＝{want:.6f}（實得 {float(one['equity'][-1]):.6f}）⇒ ⛔ 用結清日的 85 會是別的數")
    # ⭐ 排程出場日當天不被停損搶走：D 第 9 天已破線，而它的排程出場就是第 10 天 ⇒ 走排程、⛔ 不記成停損
    dclose = np.full(n, 100.0); dclose[6:10] = [97, 94, 91, 88]; dclose[10:] = 95
    closes2 = dict(closes, D=dclose); opens2 = dict(opens, D=dclose.copy())
    sig2 = pd.concat([sig, pd.DataFrame({"sid": ["D"], "entry_pos": [5], "xpos_H60": [10], "g_H60": [float(dclose[10] / dclose[5] - 1)]})], ignore_index=True)
    fx2 = R.simulate_mtm(sig2, "H60", 4, np.random.default_rng(5), closes2, opens2, n, return_equity=True, stop=("fix", 0.10))
    check(fx2["stop_exits"] == 1 and fx2["stop_days"] == [(9, 1)],
          f"排程出場日（第 10 天）當天不被停損搶走 ⇒ 只有 B 記成停損（實得 {fx2['stop_exits']} 筆 {fx2['stop_days']}）")
    # ⭐ 平均持有天數：停損出場的會短於排程的 H（⛔ 沒有這個數就解釋不了年化為什麼掉）
    check(abs(one["hold_days_mean"] - (10 - 5)) < 1e-12, f"單檔單槽：第 5 天進（entry_pos=5）、第 10 天結清 ⇒ 持有 5 天（實得 {one['hold_days_mean']}）")
    nostop_like = R.simulate_mtm(solo, "H60", 1, np.random.default_rng(3), closes, opens, n, stop=("fix", 0.99))
    check(abs(nostop_like["hold_days_mean"] - (20 - 5)) < 1e-12, f"沒觸發 ⇒ 持有到排程出場（第 20 天）＝15 天（實得 {nostop_like['hold_days_mean']}）⇒ ⭐ 停損那一版短 10 天")
    # ⛔ 參數檢查
    for bad in (("fix", 0.0), ("fix", 1.0), ("nope", 0.1), ("fix", -0.1)):
        try:
            run(bad); ok = False
        except ValueError:
            ok = True
        check(ok, f"⛔ 壞參數 {bad} ⇒ ValueError（⛔ 不是靜靜跑下去）")


def t_gate_b_sig():
    """PREREGP7：門檻B 的 sig 依策略線 1115 §1-1 的逐字定義重建（⛔ 不是它沙箱那份檔）。"""
    from . import researchp7 as P7
    cal = pd.date_range("2020-01-01", periods=400, freq="D")
    n = len(cal)
    sids_all = ("A", "B", "A2", "A3", "A4", "A5")
    closes = {k: np.linspace(100 + 10 * i, 200 + 10 * i, n) for i, k in enumerate(sids_all)}
    opens = {k: v * 0.97 for k, v in closes.items()}          # ⭐ 開盤 ≠ 收盤 ⇒ 分得出 g 用的是哪一個
    md = [cal[10], cal[40]]
    rows = []
    for d in md:
        for sid, rev, stack, up, el in (("A", 100, 0, 100, True), ("B", 100, 0, 100, True),
                                        ("A2", 100, 100, 100, True), ("A3", 0, 0, 100, True), ("A4", 100, 0, 0, True),
                                        ("A5", 100, 0, 100, False)):
            rows.append({"measure_date": d, "stock_id": sid, "eligible": el, "rev_hi24": rev, "ma_stack": stack,
                         "ma60_up": up, "amt20": 1e8, "vol60": 0.3})
    panel = pd.DataFrame(rows)
    sig = P7.build_sig_gate_b(panel, cal, closes, opens, start="2020-01-01")
    check(set(sig["sid"]) == {"A", "B"}, f"⭐ 只有三條布林全中且過閘門的才進 sig（實得 {sorted(set(sig['sid']))}）"
          "⇒ ⛔ ma_stack 成立／rev_hi24 不成立／ma60_up 不成立／沒過閘門 四種都被擋掉")
    r0 = sig[(sig.sid == "A") & (sig.entry_pos == 11)].iloc[0]
    check(int(r0[f"xpos_{P7.RULE}"]) == 11 + P7.HOLD_BARS, f"xpos ＝ entry_pos + {P7.HOLD_BARS}（⛔ 不是 +120）")
    want = closes["A"][11 + P7.HOLD_BARS] / opens["A"][11] - 1
    bad_cc = closes["A"][11 + P7.HOLD_BARS] / closes["A"][11] - 1
    check(abs(float(r0[f"g_{P7.RULE}"]) - want) < 1e-12 and abs(want - bad_cc) > 1e-6,
          f"g ＝ closes[xpos] / opens[entry] − 1（⛔ 不是收盤對收盤：那會是 {bad_cc:+.4f} 而不是 {want:+.4f}）")
    check(P7.SEED0 == 97000, f"種子起點寫死 97000（⛔ 不沿用 90000／96000；實得 {P7.SEED0}）")
    check([P7.stop_tag(c) for c in P7.CELLS] == ["none", "fix 8%", "fix 15%", "fix 20%", "trail 15%", "trail 20%"],
          f"六格寫死（實得 {[P7.stop_tag(c) for c in P7.CELLS]}）")
    check(P7.HOLD_BARS == 119, "HOLD_BARS 寫死 119（策略線逐字；⚠ 本庫 P4 的 fwd_120 是 +120，差一根）")
    # 超出日曆的量測日 ⇒ 剔除（⛔ 不是補 NaN）
    late = pd.DataFrame([{"measure_date": cal[n - 5], "stock_id": "A", "eligible": True, "rev_hi24": 100, "ma_stack": 0,
                          "ma60_up": 100, "amt20": 1e8, "vol60": 0.3}])
    check(len(P7.build_sig_gate_b(late, cal, closes, opens, start="2020-01-01")) == 0, "xpos 超出日曆 ⇒ 該列剔除")
    bad = pd.DataFrame([{"measure_date": cal[10], "stock_id": "A", "eligible": True, "rev_hi24": 100, "ma_stack": 0,
                         "ma60_up": 100, "amt20": 1e8, "vol60": 0.3}])
    op_bad = {k: v.copy() for k, v in opens.items()}; op_bad["A"][11] = np.nan
    check(len(P7.build_sig_gate_b(bad, cal, closes, op_bad, start="2020-01-01")) == 0, "進場日開盤是 NaN ⇒ 該列剔除（⛔ 不 ffill 開盤）")


def t_overlap():
    n = 10
    la = [{"reason": "in", "t": 2, "exit_pos": 6, "sid": "A"}, {"reason": "in", "t": 2, "exit_pos": 6, "sid": "B"}]
    lb = [{"reason": "in", "t": 2, "exit_pos": 6, "sid": "A"}, {"reason": "cap", "t": 2, "exit_pos": 6, "sid": "B"}]
    check(abs(P2.overlap_jaccard(la, la, n) - 1.0) < 1e-12 and abs(P2.overlap_jaccard(la, lb, n) - 0.5) < 1e-12, "重疊度：同 ⇒ 1；{A,B} vs {A} ⇒ 0.5")
    check(np.isnan(P2.overlap_jaccard([], [], n)), "都沒持倉 ⇒ NaN")


def t_judge():
    base = {"d_mdd": -0.05, "d_mdd_lo": -0.08, "d_mdd_hi": -0.02, "d_cagr": 0.002, "d_cagr_lo": -0.01, "d_cagr_hi": 0.01}
    j = P2.judge(base, 0.01, 0.003, 0.5, 30)
    check(j["H1"].startswith("H1 成立") and j["H2"].startswith("H2 成立"), "回落深 5pp、CI 不含 0、年化差 0.2% ⇒ H1 成立、H2 成立")
    check(P2.judge(base, 0.01, 0.003, 0.95, 30)["H1"].startswith("不判定"), "重疊 95% ⇒ 不判定")
    check(P2.judge(base, 0.01, 0.003, 0.5, 20)["H1"].startswith("還沒測"), "有效月 20 ⇒ 還沒測")
    check(P2.judge(base, 0.05, 0.003, 0.5, 30)["H1"].startswith("未判定"), "MDD 半寬 5pp > 3pp ⇒ 未判定")
    check(P2.judge({**base, "d_mdd": -0.02}, 0.01, 0.003, 0.5, 30)["H1"].startswith("H1 否證"), "回落只深 2pp ⇒ H1 否證")
    check(P2.judge({**base, "d_cagr": 0.01, "d_cagr_lo": 0.002}, 0.01, 0.003, 0.5, 30)["H2"].startswith("H2 否證"), "年化 +1% 且 CI 不含 0 ⇒ H2 否證")
    check(P2.judge(base, 0.01, 0.01, 0.5, 30)["H2"].startswith("未判定"), "年化半寬 1% > 0.585% ⇒ H2 未判定")


def t_seeds():
    for lo, hi in P2.USED_RANGES:
        check(not (lo <= P2.SEED0 < hi) and not (lo <= P2.SEED0 + 199 < hi) and not (lo <= 13000 < hi), f"種子 {P2.SEED0}～{P2.SEED0 + 199}／13000 不落在 [{lo},{hi})")


if __name__ == "__main__":
    print("[researchp2] 映射"); t_parent()
    print("[researchp2] 逐日標籤"); t_labels()
    print("[researchp2] cap"); t_cap()
    print("[researchp2] 預設路徑"); t_default_identical()
    print("[researchp2/引擎] 停損兩族（PREREGP7）"); t_stop()
    print("[researchp7] 門檻B sig 重建"); t_gate_b_sig()
    print("[researchp2] 重疊度"); t_overlap()
    print("[researchp2] 判定"); t_judge()
    print("[researchp2] 種子"); t_seeds()
    print("結果：", "全綠" if FAIL == 0 else f"✗ {FAIL} 條")
    sys.exit(1 if FAIL else 0)
