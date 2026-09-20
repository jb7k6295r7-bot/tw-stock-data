"""researchp2 自測：① parent_of 映射；② 逐日標籤的兩個月遲滯與 ffill；③ cap_fn 甲／丙／乙的擋法（合成三檔同母類股）；
④ simulate_mtm 預設 cap_fn=None 與原版逐位元相同（合成資料）；⑤ 重疊度；⑥ 判定函式的四個出口；⑦ 種子區間不重疊。
rc != 0 或輸出含 ✗ 才算紅。

    python3 -m backtest.selftest_researchp2
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from . import data as D
from . import research11 as R
from . import researchp2 as P2
from . import researchp7 as P7

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
    check(int(r0[f"xpos_{P7.RULE}"]) == D.exit_pos(11, P7.HOLD_BARS_N), f"xpos ＝ D.exit_pos(entry_pos, {P7.HOLD_BARS_N}) ＝ entry_pos+{P7.HOLD_BARS_N - 1}（⛔ 不是 +{P7.HOLD_BARS_N}）")
    want = closes["A"][11 + P7.HOLD_BARS] / opens["A"][11] - 1
    bad_cc = closes["A"][11 + P7.HOLD_BARS] / closes["A"][11] - 1
    check(abs(float(r0[f"g_{P7.RULE}"]) - want) < 1e-12 and abs(want - bad_cc) > 1e-6,
          f"g ＝ closes[xpos] / opens[entry] − 1（⛔ 不是收盤對收盤：那會是 {bad_cc:+.4f} 而不是 {want:+.4f}）")
    check(P7.SEED0 == 97000, f"種子起點寫死 97000（⛔ 不沿用 90000／96000；實得 {P7.SEED0}）")
    check([P7.stop_tag(c) for c in P7.CELLS] == ["none", "fix 8%", "fix 15%", "fix 20%", "trail 15%", "trail 20%"],
          f"六格寫死（實得 {[P7.stop_tag(c) for c in P7.CELLS]}）")
    check(P7.HOLD_BARS_N == 120 and P7.HOLD_BARS == 119,
          f"⭐ HOLD_BARS_N 寫死 120＝【持有根數】、HOLD_BARS＝119 只給「平均持有天數」那一欄（日數差）；實得 {P7.HOLD_BARS_N}／{P7.HOLD_BARS}")
    # 超出日曆的量測日 ⇒ 剔除（⛔ 不是補 NaN）
    late = pd.DataFrame([{"measure_date": cal[n - 5], "stock_id": "A", "eligible": True, "rev_hi24": 100, "ma_stack": 0,
                          "ma60_up": 100, "amt20": 1e8, "vol60": 0.3}])
    check(len(P7.build_sig_gate_b(late, cal, closes, opens, start="2020-01-01")) == 0, "xpos 超出日曆 ⇒ 該列剔除")
    bad = pd.DataFrame([{"measure_date": cal[10], "stock_id": "A", "eligible": True, "rev_hi24": 100, "ma_stack": 0,
                         "ma60_up": 100, "amt20": 1e8, "vol60": 0.3}])
    op_bad = {k: v.copy() for k, v in opens.items()}; op_bad["A"][11] = np.nan
    check(len(P7.build_sig_gate_b(bad, cal, closes, op_bad, start="2020-01-01")) == 0, "進場日開盤是 NaN ⇒ 該列剔除（⛔ 不 ffill 開盤）")


def t_hold_bars_ruling():
    """P4_v3 追加二十一：H〈n〉＝持有 n 根，出場根走唯一實作 `D.exit_pos`；⭐ 兩個口徑差【剛好一根】。"""
    check(D.exit_pos(523, 120) == 642 and D.exit_pos(100, 1) == 100,
          f"exit_pos(entry, n) ＝ entry+n−1（持有 1 根 ⇒ 當根出場）；實得 {D.exit_pos(523, 120)}／{D.exit_pos(100, 1)}")
    check(D.exit_pos(7, 121) - D.exit_pos(7, 120) == 1,
          "⭐ 持有 121 根（P4 面板 fwd_120）比持有 120 根（sig 慣例 H120）晚【剛好一根】")
    try:
        D.exit_pos(10, 0); ok = False
    except ValueError:
        ok = True
    check(ok, "hold_bars < 1 ⇒ 大聲失敗（⛔ 不是靜靜回 entry−1）")
    check(D.P4_FWD_HOLD_BARS == 1, f"P4_FWD_HOLD_BARS 寫死 1（P4 面板 fwd_H ＝ 持有 H+1 根）；實得 {D.P4_FWD_HOLD_BARS}")
    # research11.fixed_exit：⭐ 走 exit_pos 之後要與舊式 k+H 逐位元相同
    n = 60
    o = np.linspace(10, 20, n); c = np.linspace(10.5, 21.0, n)      # ⭐ 開盤 ≠ 收盤、逐根不同 ⇒ 分得出用了哪一根哪一價
    k, H = 5, 20
    r = R.fixed_exit(o, c, k, H, n)
    check(r is not None and r[0] == D.exit_pos(k + 1, H) == k + H,
          f"fixed_exit 出場根 ＝ exit_pos(k+1, H) ＝ k+H ＝ {k + H}（實得 {None if r is None else r[0]}）")
    check(r is not None and abs(r[1] - (c[k + H] / o[k + 1] - 1)) < 1e-15 and abs(r[1] - (c[k + H + 1] / o[k + 1] - 1)) > 1e-6,
          "fixed_exit 的毛報酬用【出場根】收盤 ÷ 進場根開盤（⛔ 不是晚一根那個收盤）")
    check(R.fixed_exit(o, c, n - H, H, n) is None, "出場根超出序列 ⇒ None（⛔ 不是回最後一根）")
    check(P7.BASE_NS == (3, 5, 8, 10, 15, 20, 30), f"基準線 7 個 N 寫死（策略線 0810 §二那張表）；實得 {P7.BASE_NS}")


def t_p6_drop_and_pair():
    """PREREGP6：第二道篩與【逐種子配對】的判定量。"""
    from . import researchp6 as P6
    sig = pd.DataFrame({"sid": ["A", "B", "C", "A"], "month": ["2024-01", "2024-01", "2024-01", "2024-02"],
                        "entry_pos": [1, 1, 1, 20], "xpos_H120": [2, 2, 2, 21], "g_H120": [0.1, 0.2, 0.3, 0.4]})
    # ⚠ 歸型表【比 sig 長】（含沒進門檻B 的股-月）⇒ 分母用錯就會被抓到
    cl = pd.DataFrame({"measure_date": pd.to_datetime(["2024-01-02"] * 3 + ["2024-02-01"] * 5),
                       "stock_id": ["A", "B", "C", "A", "D", "E", "F", "G"],
                       "type": ["④死水", "①營收＋回檔", "④死水", "③純技術＋回檔"] + ["④死水"] * 4})
    kept, info = P6.drop_type4(sig, cl)
    check(list(kept["sid"]) == ["B", "A"] and info["dropped_rows"] == 2, f"④型那兩列被拿掉（實得 {list(kept['sid'])}）")
    check(abs(info["dropped_share_pct"] - 50.0) < 1e-9, f"⭐ 佔比的分母是【門檻B 池】4 列 ⇒ 50%（實得 {info['dropped_share_pct']:.1f}%）")
    check(info["unmatched_rows"] == 0, "歸型全部對得上 ⇒ unmatched 0")
    miss = P6.drop_type4(sig, cl.iloc[:1])[1]
    check(miss["unmatched_rows"] == 3, f"⭐ 對不上歸型的要數出來（實得 {miss['unmatched_rows']}）⇒ ⛔ 不可靜靜當成「不是④」")
    # ⭐ 判定量是【逐種子配對】，⛔ 不是兩組各取中位再相減
    x = pd.DataFrame({"seed": [1, 2, 3, 4], "cagr": [0.10, 0.30, 0.12, 0.28]})
    y = pd.DataFrame({"seed": [1, 2, 3, 4], "cagr": [0.09, 0.29, 0.11, 0.27]})
    st = P6._pair_stats(x, y)
    check(abs(st["diff_median"] - 0.01) < 1e-12 and st["detectable"], "配對差 ＝ 每顆種子各自相減 ⇒ 中位 +1.00pp、CI 不含 0")
    check(abs((x["cagr"].median() - y["cagr"].median()) - 0.01) < 1e-12, "⚠ 這一組恰好兩種算法同值（⇒ 下一條才是分辨點）")
    x2 = pd.DataFrame({"seed": [1, 2, 3], "cagr": [0.10, 0.20, 0.30]})
    y2 = pd.DataFrame({"seed": [1, 2, 3], "cagr": [0.05, 0.25, 0.26]})
    st2 = P6._pair_stats(x2, y2)
    unpaired = float(x2["cagr"].median() - y2["cagr"].median())
    check(abs(st2["diff_median"] - 0.04) < 1e-12 and abs(unpaired - (-0.05)) < 1e-12,
          f"⭐ 配對中位 {st2['diff_median'] * 100:+.1f}pp vs 兩組各取中位再相減 {unpaired * 100:+.1f}pp ⇒ ⛔ 不是同一個量（連符號都不同）")
    check(abs(P6._pair_stats(x2, y2.iloc[::-1])["diff_median"] - 0.04) < 1e-12, "配對是照 seed 對，⛔ 不是照列序（把一邊倒過來答案不變）")
    check(P6.SEED0 == 96000 and P6.N_JUDGE == 8 and P6.NS == (5, 8, 10, 20), "種子 96000、判定只看 N=8、8 格寫死")
    check(abs(P6.NULL_EXPECT - 0.4) < 1e-12, "虛無期望寫死 0.4 格（＝0.05×8）")


def t_p8_helpers():
    """PREREGP8：逐月橫斷面分位、十分位表、逐月配對差、單調例外、代理檢定的雙重分位。"""
    from . import researchp8 as P8
    d = pd.to_datetime(["2024-01-02"] * 10 + ["2024-02-01"] * 10)
    df = pd.DataFrame({"measure_date": d, "stock_id": [f"S{i}" for i in range(10)] * 2,
                       "dist_hi120": list(np.arange(10.0)) + list(np.arange(10.0) * -1),
                       "fwd120": list(np.arange(10.0) / 100) + list(np.arange(10.0) / 100)})
    b = P8.xs_bucket(df, "dist_hi120", 10)
    check(list(b[:10]) == list(range(10)), f"⭐ 逐月橫斷面切：第一個月由小到大 ⇒ 0..9（實得 {list(b[:10])}）")
    check(list(b[10:]) == list(range(9, -1, -1)), "⭐ 第二個月的值是反的 ⇒ 分位也反過來（⛔ 全期一起切會看不出來）")
    df["bucket"] = b
    t = P8.decile_table(df, 120)
    check(len(t) == 10 and abs(t[t.bucket == 10]["mean"].iloc[0] - 0.045) < 1e-12,
          f"十分位表 10 格；第 10 格平均＝(0.09+0.00)/2＝0.045（實得 {t[t.bucket == 10]['mean'].iloc[0]:.4f}）")
    # ⭐ 兩個月的 D10−D1 一個 +9pp 一個 −9pp ⇒ 配對差 0、CI 含 0 ⇒ ⛔ 測不出
    pdif = P8.paired_diff(df, 120, 9, 0)
    check(pdif["n_months"] == 2 and abs(pdif["diff_pp"]) < 1e-9 and not pdif["detectable"],
          f"逐月配對：兩個月一正一負 ⇒ 差 0、⛔ 測不出（實得 {pdif['diff_pp']:+.2f}pp）")
    # ⭐⭐ 分辨點：第三個月【D1 那一桶沒有報酬】⇒ 配對法要【整月丟掉】，⛔ 各取全期均值會把它算進去
    d3 = pd.DataFrame({"measure_date": pd.to_datetime(["2024-03-01"] * 10), "stock_id": [f"S{i}" for i in range(10)],
                       "dist_hi120": np.arange(10.0), "fwd120": [np.nan] + [1.0] * 9})
    df3 = pd.concat([df.drop(columns=["bucket"]), d3], ignore_index=True)
    df3["bucket"] = P8.xs_bucket(df3, "dist_hi120", 10)
    p3 = P8.paired_diff(df3, 120, 9, 0)
    check(p3["n_months"] == 2 and abs(p3["diff_pp"]) < 1e-9,
          f"⭐ 第三個月缺 D1 ⇒ 配對法只用 2 個月、差仍是 0（實得 {p3['n_months']} 月 {p3['diff_pp']:+.2f}pp）"
          "⇒ ⛔ 兩桶各取全期均值會被那一個月拉走")
    up = pd.DataFrame({"bucket": range(1, 11), "mean": np.arange(10.0)})
    dn = up.copy(); dn.loc[3, "mean"] = -5.0                 # 一個坑 ⇒ 相鄰遞減 1 次
    dn2 = up.copy(); dn2.loc[3, "mean"] = -5.0; dn2.loc[7, "mean"] = -5.0   # 兩個坑 ⇒ 2 次
    check(P8.monotonic_exceptions(up) == 0, "單調遞增 ⇒ 例外 0")
    check(P8.monotonic_exceptions(dn) == 1, f"⭐ 中間一個坑 ⇒ 例外 1（判準 ≤ 1 ⇒ 還算單調；實得 {P8.monotonic_exceptions(dn)}）")
    check(P8.monotonic_exceptions(dn2) == 2, f"⭐ 兩個坑 ⇒ 例外 2 ⇒ ⛔ 判測不出（實得 {P8.monotonic_exceptions(dn2)}）")
    check(P8.monotonic_exceptions(up.assign(mean=np.arange(10.0)[::-1])) == 9, "整條反過來 ⇒ 例外 9（⛔ 不是 0）")
    # ⭐ 雙重分位：控制維度切五分位、內部再切三分位
    n = 150
    rng = np.random.default_rng(0)
    ctl = np.arange(n, dtype=float)
    d2 = pd.DataFrame({"measure_date": pd.to_datetime(["2024-01-02"] * n), "stock_id": [f"T{i}" for i in range(n)],
                       "ret_120": ctl, "dist_lo120": rng.normal(size=n),
                       "dist_hi120": ctl + rng.normal(size=n) * 0.01,   # ⭐ 與控制維度高度相關 ⇒ 分得出內層有沒有在分位【內部】切
                       "fwd120": rng.normal(size=n) / 100})
    T = P8.proxy_double_sort(d2, "ret_120", 120)
    check(set(T["ctl_quintile"]) == {1, 2, 3, 4, 5} and set(T["tercile"]) == {1, 2, 3},
          f"雙重分位 5×3 格（實得 {T['ctl_quintile'].nunique()}×{T['tercile'].nunique()}）")
    check(len(T) == 15 and int(T["n"].min()) == int(T["n"].max()) == 10,
          f"⭐⭐ 內層是在【每一個控制分位內部】切 ⇒ 15 格各 10 檔（實得 {int(T['n'].min())}~{int(T['n'].max())}）"
          "⇒ ⛔ 用全域切點會讓每個分位裡只剩一種 tercile")
    check(P8.SEED0 == 98000 and P8.HOLDS == (20, 60, 120) and P8.FEATURE == "dist_hi120",
          "種子 98000、三個持有期、特徵名寫死")
    check(P8.N_DEC == 10 and P8.N_TER == 3 and P8.N_QUI == 5, "十分位／三分位／五分位寫死")
    # ⭐ 出場口徑：本件是新工作 ⇒ 持有 n 根
    cal = pd.date_range("2024-01-01", periods=300, freq="D")
    cl = {"A": np.linspace(100, 200, 300)}; op = {"A": np.linspace(100, 200, 300) * 0.99}
    one = pd.DataFrame([{"measure_date": cal[5], "stock_id": "A", "amt20": 1e8, "vol60": 0.3}])
    f = P8.add_forward(one, cal, cl, op, holds=(20,))
    want = cl["A"][D.exit_pos(6, 20)] / op["A"][6] - 1
    check(abs(float(f["fwd20"].iloc[0]) - want) < 1e-12, "fwd20 ＝ 收盤[exit_pos(entry,20)] / 開盤[entry] − 1（持有 20 根）")
    check(D.exit_pos(6, 20) == 25, f"⛔ 持有 20 根 ⇒ 出場位置 entry+19＝25（⛔ 不是 26；實得 {D.exit_pos(6, 20)}）")


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


def t_p11():
    """PREREGP11（回測線 2026-09-20 15:40）：half-up、逐日容量、逐月報酬、月分群 CI、B⊂C、呼叫點。"""
    import os as _os

    from . import researchp8 as P8
    from . import researchp11 as P11
    # ① half-up（追加一⑤）：⚠ Python 的 round() 是 banker's rounding
    check(P11.n_of(0.5, 5) == 3 and round(0.5 * 5) == 2,
          "N ＝ half-up ⇒ 0.5×5＝2.5 取 3（⚠ Python 的 round(2.5) 是 2 ⇒ 那條路會少一檔）")
    check(P11.n_of(0.35, 10) == 4 and P11.n_of(0.25, 1) == 1 and P11.n_of(0.25, 2) == 1,
          "half-up 其餘三格：3.5→4／下限 1 檔（0.25×1＝0.25→1、0.25×2＝0.5→1）")
    # ② 逐日容量（追加一①②）
    sig11 = pd.DataFrame([{"sid": f"s{i}", "entry_pos": e, "month": m}
                          for m, e, k in (("2020-01", 10, 4), ("2020-02", 30, 2), ("2020-03", 50, 10))
                          for i in range(k)])
    caps, tab = P11.caps_series(sig11, 0.5, 60)
    check(list(tab["cand"]) == [4, 2, 10] and list(tab["N"]) == [2, 1, 5],
          f"候選數＝該月 sig 筆數、N＝half-up(0.5×候選)：{list(tab['cand'])} ⇒ {list(tab['N'])}")
    check(caps[9] == 2 and caps[10] == 2 and caps[29] == 2 and caps[30] == 1 and caps[49] == 1 and caps[50] == 5 and caps[59] == 5,
          "容量從【該月進場日】生效到下個月進場日前一天；第一個進場日之前用第一個月的 N")
    check(list(tab["sold_out"]) == [False, False, False] and list(P11.caps_series(sig11, 0.75, 60)[1]["sold_out"]) == [False, True, False],
          "買光月 ＝ N_t ≥ 候選數（0.75×2＝1.5→2 ＝ 候選 2 ⇒ 買光）")
    # ③ 引擎吃逐日容量：純量 ≡ 同值陣列；容量變小⛔ 不強制出場；slot_use 分母 ＝ Σ 容量
    ncal = 20
    cl = {k: np.linspace(10.0, 20.0, ncal) for k in ("A", "B")}
    op = {k: v + 0.1 for k, v in cl.items()}
    sg = pd.DataFrame([{"sid": k, "entry_pos": 5, "xpos_H5": 12, "g_H5": cl[k][12] / op[k][5] - 1.0} for k in ("A", "B")])
    run = lambda n: R.simulate_mtm(sg, "H5", n, np.random.default_rng(3), cl, op, ncal, return_equity=True)
    a2 = run(2); arr2 = run(np.full(ncal, 2, int))
    check(np.array_equal(a2["equity"], arr2["equity"]) and a2["slot_use"] == arr2["slot_use"],
          "逐日容量【全等於 2】⇒ 與純量 n_slots=2 逐位元相同（新路徑不動原版）")
    drop = np.full(ncal, 2, int); drop[8:] = 1
    ad = run(drop)
    check(np.array_equal(ad["equity"][:20], a2["equity"][:20]) and ad["trades"] == a2["trades"],
          "容量在持倉期間變小 ⇒ ⛔ 不強制出場（權益路徑與沒變小時相同）")
    bind = np.full(ncal, 2, int); bind[5:] = 1
    ab = run(bind)
    check(ab["trades"] == 1 and a2["trades"] == 2,
          f"容量是【逐日讀 t 那一天】的：進場日容量 1 ⇒ 只進 1 筆（⛔ 不是讀第 0 天的 2）：{ab['trades']} vs {a2['trades']}")
    mix = np.full(ncal, 4, int); mix[10:] = 8
    a4 = run(np.full(ncal, 4, int)); am = run(mix)
    used4 = a4["slot_use"] * (a4["end"] - a4["first"]) * 4
    check(abs(am["slot_use"] - used4 / mix[a4["first"]:a4["end"]].sum()) < 1e-12,
          f"slot_use 的分母 ＝ Σ 逐日容量（⛔ 不是 (end−first)×某一個 N）：{am['slot_use']:.6f}")
    check(P11.n_of(0.35, 23) == 8 and [P11.n_of(r, 23) for r in P11.RATES] == [6, 8, 12, 17],
          "固定 N（追加一⑫）＝ half-up(選擇率×23) ＝ 6／8／12／17，判定格 35% ⇒ 8 檔")
    # ④ 逐月報酬與月分群 CI
    eq = np.array([1.0, 1.1, 1.1, 1.32, 1.32, 0.99], float)
    mr = P11.monthly_returns(eq, np.array([1, 3, 5]))
    check(len(mr) == 2 and abs(mr[0] - 0.2) < 1e-12 and abs(mr[1] + 0.25) < 1e-12,
          f"逐月報酬用【月底相除】、⛔ 第一個月不算（實得 {np.round(mr, 6).tolist()}）")
    ci = P8.month_ci(np.full(40, 0.01))
    ci0 = P8.month_ci(np.linspace(-0.1, 0.1, 41))
    check(ci["detectable"] and abs(ci["diff_pp"] - 1.0) < 1e-12 and ci["n_months"] == 40 and ci["pos_months"] == 40,
          "月分群 CI：40 個月都 +1% ⇒ CI 不含 0、diff 1.00pp")
    check((not ci0["detectable"]) and abs(ci0["diff_pp"]) < 1e-9 and not P8.month_ci([0.01])["detectable"],
          "反向驗：對稱分佈 ⇒ CI 含 0；⛔ 只有 1 個月 ⇒ 不可判定")
    dd = np.linspace(-0.05, 0.09, 100)                     # 平均 +2%、sd ≈ 4.1% ⇒ ⭐ 有沒有除 √n 會給相反答案
    cn = P8.month_ci(dd); half = (cn["hi_pp"] - cn["lo_pp"]) / 2
    want_half = 1.96 * float(dd.std(ddof=1)) / np.sqrt(len(dd)) * 100
    check(cn["detectable"] and abs(half - want_half) < 1e-9 and half < abs(cn["diff_pp"]),
          f"⭐ SE 要【除以 √n】：n=100、sd {dd.std(ddof=1) * 100:.2f}pp ⇒ 半寬 {half:.3f}pp（⛔ 不除 √n 會是 {want_half * 10:.2f}pp ⇒ CI 含 0）")
    # ⑤ 訊號集：C ＝ B 拿掉 ¬ma_stack ⇒ B ⊂ C
    cal2 = pd.date_range("2020-01-01", periods=400, freq="D")
    cl2 = {k: np.linspace(100.0, 200.0, len(cal2)) for k in ("A", "S")}
    op2 = {k: v * 0.97 for k, v in cl2.items()}
    pn = pd.DataFrame([{"measure_date": cal2[10], "stock_id": sid, "eligible": True, "rev_hi24": 100,
                        "ma_stack": stk, "ma60_up": 100, "amt20": 1e8, "vol60": 0.3}
                       for sid, stk in (("A", 0), ("S", 100))])
    sb = P7.build_sig_gate_b(pn, cal2, cl2, op2, start="2020-01-01")
    sc = P7.build_sig_gate_b(pn, cal2, cl2, op2, start="2020-01-01", signal="C")
    check(set(sb["sid"]) == {"A"} and set(sc["sid"]) == {"A", "S"},
          "參考C ＝ 門檻B 拿掉 ¬ma_stack ⇒ ma_stack 成立的那一檔只進 C（⇒ B ⊂ C）")
    try:
        P7.build_sig_gate_b(pn, cal2, cl2, op2, signal="X"); bad = False
    except ValueError:
        bad = True
    check(bad, "signal 只收 'B'／'C'，其餘大聲失敗（⛔ 不靜靜當成 B）")
    # ⑥ 呼叫點（⭐ 測完純函式再掃一次原始碼）
    src = open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "researchp11.py"), encoding="utf-8").read()
    check("P8.month_ci(dm)" in src and "np.nanmean(np.vstack([mret[(\"C\"" in src,
          "呼叫點：判定用 P8.month_ci、而 dm 是【先逐種子配對（C−B）再對種子取平均】")
    check("P3.exposure_series(" in src and "expo_m" in src, "呼叫點：閒置用 researchp3.exposure_series（⛔ 不是槽位使用率）")
    check("P9.passes(" in src and "def passes" not in src, "呼叫點：三條判準走 researchp9.passes（⛔ 本檔沒有第二份不等式）")
    check('caps[(k, "fix", rate)] = n_of(rate, B_CAND_MED)' in src and P11.MAIN_RATE == 0.35,
          "呼叫點：固定 N 兩個訊號集用同一組（n_of(rate, B_CAND_MED)）；判定格寫死 35%")
    check(P11.SEED0 == 101000 and P11.RATES == (0.25, 0.35, 0.50, 0.75),
          f"種子起點寫死 101000、四個選擇率寫死（實得 {P11.SEED0}／{P11.RATES}）")



def t_p12():
    """PREREGP12（回測線 2026-09-20）：窗口徑、T0 建倉、C0 最小 n_slots、成本切換不外洩、主效果與加法表、呼叫點。"""
    import os as _os

    from . import researchp8 as P8
    from . import researchp12 as P12
    # ① 登錄寫死的常數（⛔ 不是「程式有跑」而已）
    check(P12.SEED0 == 102000 and P12.C0_FRAC == 0.999 and P12.N_C1 == 8 and P12.ANCHOR_TOL == 0.01,
          f"寫死：種子 102000／買光判準 0.999／C1＝8 檔／容差 ±1pp（實得 {P12.SEED0}／{P12.C0_FRAC}／{P12.N_C1}／{P12.ANCHOR_TOL}）")
    check(len(P12.CORNERS) == 12 and P12.C_LEVELS == ("C1", "C0a", "C0f")
          and P12.ANCHOR_OWN_DD == -0.409 and P12.ANCHORS[("主格窗", "S0", "C0a", "T0", "成本0")] == -0.1521
          and [c[0] for c in P12.COSTS] == ["成本0.585%", "成本0"],
          "十二格（C0 兩版）；⭐ 錨點①-引擎對【自己最深回落】−40.9%、錨點②對【窗期報酬】−15.21% 成本 0（裁定①）")
    check(P12.FACTOR_LEVELS["C"] == ("C1", "C0a") and "C0f" not in P12.FACTOR_LEVELS["C"]
          and P12.GAP_REF_PP == -13.25 and P12.PRIOR_PP["S"] == (-10.3, -5.2) and P12.PRIOR_PP["T"] == (-5.2, -1.5)
          and P12.PRIOR_PP["殘差"] == (-4.0, -1.3),
          "⭐ 判定用 C0a（⛔ C0f 只作描述）；被拆的量 −13.25pp（⭐ 帶負號 ⇒ 表上不會印成 +13.25）；先驗是 25.7pp 版【按比例機械換算】的三組區間（裁定②③④）")
    check(P12.WINDOWS["主格窗"] == ("2023-07-03", "2025-04-09") and P12.WIN_DAYS["主格窗"] == 428
          and P12.WINDOWS["全窗"] == ("2017-03-02", "2026-08-24"),
          "兩個窗的端點與天數寫死（⛔ 天數對不上程式會停）")
    # ② 窗與月界（合成日曆：⛔ 不碰真資料）
    cal = pd.DatetimeIndex(pd.bdate_range("2020-01-01", periods=400))
    try:
        P12.win_bounds(cal, "主格窗"); bad = False
    except SystemExit:
        bad = True
    check(bad, "窗端點不是交易日／天數對不上 ⇒ 大聲失敗（⛔ 不靜靜挪到最近的一天）")
    mk = P12.month_marks(cal, 10, 120)
    check(mk[0] == 10 and mk[-1] == 120 and (np.diff(mk) > 0).all() and len(mk) - 1 == 6,
          f"月界 ＝ [w0, 各月最後一個交易日…, w1]、嚴格遞增、段數＝月數（實得 {len(mk) - 1} 段：{mk.tolist()}）")
    check(list(pd.DatetimeIndex(cal[mk[1:-1]]).strftime("%m")) == ["01", "02", "03", "04", "05"],
          "中間那幾個月界真的落在各月的最後一個交易日")
    # ③ T0 的 sig：只取窗內第一個訊號月、xpos ＝ 窗尾、gross 用建倉日開盤重算
    ncal = 400; w0, w1 = 100, 380
    cl = {k: np.linspace(10.0, 20.0, ncal) for k in ("A", "B", "C")}
    op = {k: v * 0.99 for k, v in cl.items()}
    op["C"] = op["C"].copy(); op["C"][110] = np.nan            # ⭐ 建倉日沒有開盤價 ⇒ 要被丟掉
    base = pd.DataFrame([{"sid": "A", "entry_pos": 110, "month": "2020-06"},
                         {"sid": "C", "entry_pos": 110, "month": "2020-06"},
                         {"sid": "B", "entry_pos": 150, "month": "2020-07"},
                         {"sid": "A", "entry_pos": 90, "month": "2020-05"}])
    base[f"xpos_{P12.RULE}"] = base["entry_pos"] + 119
    base[f"g_{P12.RULE}"] = 0.0
    t0sig = P12.sig_hold_to(base, w0, w1, cl, op)
    check(list(t0sig["sid"]) == ["A"] and int(t0sig["entry_pos"].iloc[0]) == 110,
          f"T0 只取【窗內第一個】訊號月（110，⛔ 不是窗外的 90、⛔ 不是後面的 150），且丟掉沒有開盤價的 C（實得 {list(t0sig['sid'])}）")
    check(int(t0sig[f"xpos_{P12.RULE}"].iloc[0]) == w1
          and abs(float(t0sig[f"g_{P12.RULE}"].iloc[0]) - (cl["A"][w1] / op["A"][110] - 1)) < 1e-12,
          "T0 的 xpos ＝ 窗尾、gross ＝ 窗尾收盤 ÷ 建倉日開盤 − 1（⛔ 不是沿用 T1 那一欄）")
    # ④ ⭐⭐ 窗期總報酬的分母：equity[w0]（⛔ 不是 first）——T0 的 first 在 w0 之後
    eq = np.ones(ncal); eq[:w0] = np.linspace(0.80, 0.95, w0)     # ⭐ 窗頭前一天 ≠ 窗頭 ⇒ 分母寫錯抓得到
    eq[w0:] = np.linspace(1.0, 1.5, ncal - w0); eq[110:] *= 1.2
    hv = np.zeros(ncal); hv[110:] = eq[110:] * 0.8
    out = {"equity": eq, "hold_val": hv, "first": 110, "end": ncal, "slot_use": 0.5, "trades": 3}
    rd = P12.win_read(out, w0, w1, P12.month_marks(cal, w0, w1))
    check(abs(rd["tr"] - (eq[w1] / eq[w0] - 1)) < 1e-12 and abs(rd["tr_prev"] - (eq[w1] / eq[w0 - 1] - 1)) < 1e-12,
          "窗期總報酬 ＝ equity[w1]/equity[w0] − 1（對帳版另報 w0−1）")
    want_cagr = (eq[w1] / eq[w0]) ** (245 / (w1 + 1 - w0)) - 1
    check(abs(rd["cagr"] - want_cagr) < 1e-12,
          f"⭐ 窗內年化的分母也是 equity[w0]：⛔ 讓 window_stats 把 a clamp 到 first(110) 會漏掉建倉那一段（"
          f"實得 {rd['cagr'] * 100:+.3f}%／要 {want_cagr * 100:+.3f}%）")
    check(abs(rd["expo"] - np.r_[np.zeros(10), np.full(w1 - 109, 0.8)].mean()) < 1e-12 and len(rd["mret"]) == len(P12.month_marks(cal, w0, w1)) - 1,
          "曝險 ＝ 窗內【日均】持股市值佔比（⭐ 含建倉前那幾天的 0，⛔ 不是只算有倉位的日子）")
    # ⑤ ⭐ 成本用模組常數切換：⛔ 不外洩（跑完要還原）
    P12._init({}, {}, cl, op, ncal, {}, {})
    sg = pd.DataFrame([{"sid": k, "entry_pos": 110, f"xpos_{P12.RULE}": 229, f"g_{P12.RULE}": cl[k][229] / op[k][110] - 1.0} for k in ("A", "B")])
    a0 = P12._sim(sg, 2, 5, P12.COST_STD)
    b0 = P12._sim(sg, 2, 5, 0.0); after = R.COST                   # ⭐ 就在成本 0 那一跑【之後】立刻看模組常數
    a1 = P12._sim(sg, 2, 5, P12.COST_STD)
    check(not np.array_equal(a0["equity"], b0["equity"]), "成本 0 與含成本【跑出來不一樣】（⛔ 不是設了沒用）")
    check(after == P12.COST_STD and R.COST == P12.COST_STD,
          f"⭐ 成本【跑完立刻還原】⇒ 不會外洩給同一個行程裡的別人（實得 {after}）")
    check(np.array_equal(a0["equity"], a1["equity"]),
          "成本 0 跑完之後再跑含成本，與全新跑逐位元相同")
    # ⑥ C0 ＝ 使 trades 達上限的【最小】n_slots
    sg6 = pd.DataFrame([{"sid": k, "entry_pos": 110, f"xpos_{P12.RULE}": 300, f"g_{P12.RULE}": cl[k[0]][300] / op[k[0]][110] - 1.0}
                        for k in ("A1", "A2", "A3", "B1", "B2", "B3")])
    for k in ("A1", "A2", "A3", "B1", "B2", "B3"):
        cl[k] = cl[k[0]]; op[k] = op[k[0]]
    P12._init({("S0", "T0", "W"): sg6}, {}, cl, op, ncal, {"W": (w0, w1)}, {"W": P12.month_marks(cal, w0, w1)})
    shim = type("P", (), {"map": staticmethod(lambda f, it: [f(x) for x in it])})()
    n, lad = P12.choose_c0(shim, "S0", "T0", "W", "W", len(sg6), log=lambda *_: None)
    check(n == 6 and int(lad.loc[lad["n_slots"] == 6, "trades"].iloc[0]) == 6,
          f"買光 ＝ 6 個候選要 6 個槽（⛔ 不是更大的數 ⇒ 那會把曝險稀釋掉）：實得 {n}")
    check(int(lad.loc[lad["n_slots"] == 5, "trades"].iloc[0]) == 5 and (lad["n_slots"] < 6).any(),
          "梯度表留下了【沒買光】那幾點（n_slots=5 ⇒ 只進 5 筆）⇒ ⭐ 這就是 §四⑤ 要的證據")
    # ⑥b ⭐⭐ C0a 的逐日容量（裁定④ ＋ §十-4）：在場部位數、⛔ 不是當天新訊號數
    cap6 = P12.caps_buy_all(pd.DataFrame([{"sid": "A", "entry_pos": 10, f"xpos_{P12.RULE}": 20},
                                          {"sid": "A", "entry_pos": 15, f"xpos_{P12.RULE}": 25},   # ⭐ 已持有 ⇒ 不重入
                                          {"sid": "B", "entry_pos": 15, f"xpos_{P12.RULE}": 30}]), 40)
    check(cap6[9] == 1 and cap6[10] == 1 and cap6[14] == 1 and cap6[15] == 2 and cap6[19] == 2,
          f"容量 ＝ 當日【在場】的部位數（10 進 A ⇒ 1；15 再進 B ⇒ 2）：{cap6[9:21].tolist()}")
    check(cap6[20] == 1 and cap6[25] == 1 and cap6[29] == 1 and cap6[30] == 1,
          "⭐ 出場日【不算在場】（A 的 xpos=20 ⇒ 第 20 天只剩 B）；⛔ 同一 sid 的第二筆訊號不會把它延長到 25")
    check(cap6.min() >= 1 and len(cap6) == 40, "沒有任何一天容量 < 1（引擎要求）、長度 ＝ ncal")
    # ⑥c ⭐ 掛上引擎：⛔ 兩版都買光的情況下，C0a 的【曝險】才是被拉起來的那一個（裁定④ 要證的就是這件）
    coh = ((110, 8), (150, 4), (190, 2), (230, 1))      # ⭐ 群體不重疊（持有 30 天、間隔 40 天）⇒ 出場的錢剛好夠下一批
    rowsA = []
    for e, k in coh:
        for i_ in range(k):
            sid = f"X{e}_{i_}"
            cl[sid] = cl["A"]; op[sid] = op["A"]
            rowsA.append({"sid": sid, "entry_pos": e, f"xpos_{P12.RULE}": e + 30, f"g_{P12.RULE}": cl["A"][e + 30] / op["A"][e] - 1.0})
    sgA = pd.DataFrame(rowsA)
    wa0, wa1 = 100, 345
    mkA = P12.month_marks(cal, wa0, wa1)
    P12._init({("S0", "T1", "*"): sgA}, {}, cl, op, ncal, {"W": (wa0, wa1)}, {"W": mkA})
    capA = P12.caps_buy_all(sgA, ncal)
    check(capA[110] == 8 and capA[145] == 1 and capA[150] == 4 and capA[190] == 2 and capA[230] == 1,
          f"容量隨【在場部位數】逐日變（8→4→2→1，空手時下限 1）：{[int(capA[x]) for x in (110, 145, 150, 190, 230)]}")
    oa = P12._sim(sgA, capA, 7, 0.0); of_ = P12._sim(sgA, 8, 7, 0.0)
    ra = P12.win_read(oa, wa0, wa1, mkA); rf = P12.win_read(of_, wa0, wa1, mkA)
    check(ra["trades"] == rf["trades"] == 15,
          f"⭐ 兩版都【買光】（各 {ra['trades']} 筆 ＝ 全部候選）⇒ 曝險的差不是「買比較少」造成的")
    check(ra["expo"] > rf["expo"] + 0.20,
          f"⭐⭐ 而曝險差很多：C0a 對齊版 {ra['expo'] * 100:.1f}% vs C0f 字面版 {rf['expo'] * 100:.1f}%"
          " ⇒ ⭐ 兩版之差就是【現金效應】那一格（裁定④）")
    # ⑦ 主效果 ＝ 4 種組合上平均（⛔ 不是單一角落的差）；加法表的殘差
    aS, bC, dT, k3 = -0.10, 0.02, -0.05, 0.04
    rows, mr = [], {}
    for s_ in ("S1", "S0"):
        for c_ in ("C1", "C0a", "C0f"):
            for t_ in ("T1", "T0"):
                si, ci, ti = int(s_ == "S1"), int(c_ == "C1"), int(t_ == "T1")
                y = aS * si + bC * ci + dT * ti + k3 * si * ci * ti
                if c_ == "C0f":
                    y = 9.9                     # ⭐ 毒藥：描述版若漏進因子，下面每一條都會炸開
                for sd in (0, 1):
                    rows.append({"S": s_, "C": c_, "T": t_, "win": "W", "cost": "成本0", "seed": sd, "tr": y})
                    # ⭐ 種子項【兩臂相同】⇒ 正確配對會消掉它；⛔ 配錯種子就消不掉（M10 突變）
                    mr[(s_, c_, t_, "W", "成本0", sd)] = np.full(10, y / 10) + sd * 0.037
    dfx = pd.DataFrame(rows)
    eS = P12.main_effect(dfx, mr, "S", "W", "成本0")
    check(abs(eS["point_pp"] - (aS + k3 / 4) * 100) < 1e-9,
          f"S 主效果 ＝ 在 C、T 四種組合上平均（{(aS + k3 / 4) * 100:+.1f}pp）⛔ 不是 (S1,C1,T1)−(S0,C1,T1)（那會是 {(aS + k3) * 100:+.1f}pp）：實得 {eS['point_pp']:+.3f}pp")
    check(abs(eS["diff_pp"] - eS["point_pp"] / 10) < 1e-9,
          f"⭐ 逐月配對差 ＝ 【同種子】相減 ⇒ 種子項被消掉（要 {eS['point_pp'] / 10:+.3f}pp、實得 {eS['diff_pp']:+.3f}pp；"
          "⛔ 配錯種子那一項就留在差裡)")
    check(abs(eS["point_pp"] - (aS + k3 / 4) * 100) < 1e-9 and eS["n_pairs"] == 8,
          "⭐ C0f（描述版）沒有漏進因子：它的值是 +990pp，漏了主效果一定不是 −9pp（裁定④）")
    check(eS["n_pairs"] == 8 and eS["n_months"] == 10 and eS["verdict"] == "測得出" and eS["detectable"],
          f"配對數 ＝ 4 組合 × 2 種子 ＝ 8；抽樣單位是【月】(10)；零變異且非 0 ⇒ 測得出（實得 {eS['n_pairs']}／{eS['n_months']}／{eS['verdict']}）")
    mr2 = dict(mr)
    for kk in mr2:
        mr2[kk] = mr2[kk] + (np.arange(10) % 2 * 2 - 1) * (0.5 if kk[0] == "S1" else 0.0)
    check(P12.main_effect(dfx, mr2, "S", "W", "成本0")["verdict"] == "測不出",
          "反向驗：逐月差一半 +50%／一半 −50% ⇒ CI 含 0 ⇒ 測不出（⛔ 點估計一樣大也不算）")
    eT_all = P12.main_effect(dfx, mr, "T", "W", "成本0")
    eT_s0 = P12.main_effect(dfx, mr, "T", "W", "成本0", arms={"S": "S0"})
    check(eT_s0["n_pairs"] == 4 and eT_all["n_pairs"] == 8 and eT_s0["arm"] == "S0" and eT_all["arm"] == "全部"
          and abs(eT_s0["point_pp"] - dT * 100) < 1e-9 and abs(eT_all["point_pp"] - (dT + k3 / 4) * 100) < 1e-9,
          f"裁定⑤：T 主效果要報兩版 —— 全部（8 對，{eT_all['point_pp']:+.1f}pp）與【只 S0 臂】（4 對，{eT_s0['point_pp']:+.1f}pp）")
    eS_t1 = P12.main_effect(dfx, mr, "S", "W", "成本0", arms={"T": "T1"})
    check(eS_t1["n_pairs"] == 4 and eS_t1["arm"] == "T1" and abs(eS_t1["point_pp"] - (aS + k3 / 2) * 100) < 1e-9,
          f"⭐ S 也要報兩版（策略線 1830 §三②）：【只 T1】那一版是 4 對、{(aS + k3 / 2) * 100:+.1f}pp"
          f"（⛔ 不是全部那版的 {(aS + k3 / 4) * 100:+.1f}pp）⇒ 拿掉 T0 那一欄【連同它的對子】")
    eff = pd.DataFrame([P12.main_effect(dfx, mr, f, "W", "成本0") for f in ("S", "C", "T")])
    at = P12.attribution(dfx, eff, "W", "成本0")
    check(abs(at["gap_pp"] - (aS + bC + dT + k3) * 100) < 1e-9 and abs(at["resid_pp"] - k3 / 4 * 100) < 1e-9,
          f"加法表：gap ＝ 角落差、殘差 ＝ gap −(S＋C＋T) ＝ 三階交互的 1/4（要 {k3 / 4 * 100:+.2f}pp、實得 {at['resid_pp']:+.2f}pp）")
    def _att(a_, k_):                                  # ⭐ 同一條路餵兩組係數 ⇒ 正反例各一
        rr = [{**r, "tr": (9.9 if r["C"] == "C0f" else
                           a_ * ((r["S"] == "S1") + (r["C"] == "C1") + (r["T"] == "T1"))
                           + k_ * (r["S"] == "S1") * (r["C"] == "C1") * (r["T"] == "T1"))} for r in rows]
        d_ = pd.DataFrame(rr)
        e_ = pd.DataFrame([P12.main_effect(d_, mr, f, "W", "成本0") for f in ("S", "C", "T")])
        return P12.attribution(d_, e_, "W", "成本0")
    big = _att(-0.02, 0.4)                             # 主效果 −2＋10 ＝ 8pp、殘差 10pp ⇒ 殘差較大
    small = _att(-0.10, 0.04)                          # 主效果 −9pp、殘差 1pp ⇒ 殘差較小
    check(big["resid_gt_max"] and not small["resid_gt_max"] and not at["resid_gt_max"],
          f"否證②：殘差 > 最大主效果 ⇒ 旗標亮（殘差 {big['resid_pp']:+.1f}pp vs 主效果 {big['S_pp']:+.1f}pp）；"
          f"反例（殘差 {small['resid_pp']:+.1f}pp vs {small['S_pp']:+.1f}pp）⇒ 不亮 ⭐ 正反例各一")
    # ⑦a ⭐ 加法表用【種子平均】（⛔ 中位數不可加）：只有 (S0,C0,T0) 的第三顆種子歪掉
    r3, mr3 = [], {}
    for s_, c_, t_ in P12.CORNERS:
        for sd in (0, 1, 2):
            y3 = 0.3 if (s_, c_, t_, sd) == ("S0", "C0a", "T0", 2) else (9.9 if c_ == "C0f" else 0.0)
            r3.append({"S": s_, "C": c_, "T": t_, "win": "W", "cost": "成本0", "seed": sd, "tr": y3})
            mr3[(s_, c_, t_, "W", "成本0", sd)] = np.full(10, y3 / 10)
    d3 = pd.DataFrame(r3)
    e3 = pd.DataFrame([P12.main_effect(d3, mr3, f, "W", "成本0") for f in ("S", "C", "T")])
    a3 = P12.attribution(d3, e3, "W", "成本0")
    check(abs(a3["gap_pp"] - (-10.0)) < 1e-9 and abs(a3["resid_pp"] - (-2.5)) < 1e-9,
          f"⭐ 加法表用【平均】：三顆種子 0／0／+30% ⇒ 平均 +10% ⇒ gap −10.00pp（⛔ 用中位數會是 0.00pp；實得 {a3['gap_pp']:+.2f}pp）")
    # ⑦b 錨點對帳：⭐ 用【中位種子】（§八①）、容差 ±1pp
    fake = pd.DataFrame([{"win": "主格窗", "cost": "成本0.585%", "S": "S1", "C": "C1", "T": "T1", "tr_med": -0.295, "tr_mean": -0.350},
                         {"win": "主格窗", "cost": "成本0", "S": "S0", "C": "C0a", "T": "T0", "tr_med": -0.1721, "tr_mean": -0.1521}])
    ac = P12.check_anchors(fake, own_med=-0.400)
    check(list(ac["過"]) == [True, False] and len(ac) == 1 + len(P12.ANCHORS),
          f"裁定①：①-引擎看【自己最深回落】−40.0% vs −40.9% ⇒ 過；②看【窗期報酬】−17.21% vs −15.21% ⇒ 不過（實得 {list(ac['過'])}）")
    check(abs(float(ac["本線中位"].iloc[0]) - (-0.400)) < 1e-12,
          "⭐ 報表上的「本線中位」就是傳進去的那個量（⛔ 不是另外一格的數字 ⇒ 否則表會誤導讀的人）")
    check(abs(float(ac["差pp"].iloc[0]) - 0.9) < 1e-9 and "C0a" in ac["錨點"].iloc[1],
          "⭐ 錨點①【不看】那一格的窗期報酬（−29.5% 就在表裡，⛔ 它不是錨點）；錨點② 對的是 C0a 那一格")
    check(list(P12.check_anchors(fake.assign(tr_med=[-0.295, -0.1521]), own_med=-0.500)["過"]) == [False, True],
          "反向驗：①-引擎 −50% ⇒ 不過；② −15.21% ⇒ 過（⛔ 兩條各自獨立，不是一起過一起不過）")
    # ⑧ 直算（口徑差）與 S0 訊號集
    dd = P12.direct_equal_weight(["A", "B"], cl, op, w0, w1, 110)
    check(abs(dd["A"] - np.mean([cl[k][w1] / cl[k][w0] - 1 for k in ("A", "B")])) < 1e-12
          and abs(dd["B"] - np.mean([cl[k][w1] / op[k][110] - 1 for k in ("A", "B")])) < 1e-12,
          "直算A ＝ 窗頭【收盤】起算（策略線口徑）、直算B ＝ 建倉日【開盤】起算（引擎口徑）⇒ 差就是口徑差")
    cal2 = pd.date_range("2020-01-01", periods=400, freq="D")
    cl2 = {k: np.linspace(100.0, 200.0, len(cal2)) for k in ("A", "S", "N")}
    op2 = {k: v * 0.97 for k, v in cl2.items()}
    pn = pd.DataFrame([{"measure_date": cal2[10], "stock_id": sid, "eligible": el, "rev_hi24": rv,
                        "ma_stack": stk, "ma60_up": up, "amt20": 1e8, "vol60": 0.3}
                       for sid, el, rv, stk, up in (("A", True, 100, 0, 100), ("S", True, 0, 100, 0), ("N", False, 100, 0, 100))])
    sb = P7.build_sig_gate_b(pn, cal2, cl2, op2, start="2020-01-01")
    sa = P7.build_sig_gate_b(pn, cal2, cl2, op2, start="2020-01-01", signal="ALL")
    check(set(sb["sid"]) == {"A"} and set(sa["sid"]) == {"A", "S"},
          "S0 ＝ 全市場 ＝ 【過閘門就算訊號】（三條布林都不看），⛔ 但沒過閘門的 N 仍然不算")
    check(P12.SIG_OF == {"S1": "B", "S0": "ALL"} and len(sa) >= len(sb), "S1→signal='B'、S0→signal='ALL'（⇒ B ⊆ ALL）")
    # ⑧b ⭐ 錨點沒過之後的【查】：最深那一段回落的峰谷位置
    eqd = np.array([1.0, 1.2, 1.1, 1.3, 0.9, 1.0, 1.4, 1.35, 1.0, 1.5], float)   # 兩段回落：1.3→0.9（−30.8%）與 1.4→1.0（−28.6%）
    cal3 = pd.DatetimeIndex(pd.bdate_range("2021-01-01", periods=len(eqd)))
    pk, tr, dep = P12.deepest_episode(eqd, 1, len(eqd), cal3)
    check(pk == 3 and tr == 4 and abs(dep - (0.9 / 1.3 - 1)) < 1e-12,
          f"最深的那一段 ＝ 峰 1.3(位置 3) → 谷 0.9(位置 4)、深度 {dep * 100:.1f}%（⛔ 不是後面那段較淺的 1.4→1.0）")
    check(P12.deepest_episode(np.array([1.0, 1.1, 1.2]), 0, 3, cal3[:3]) == (-1, -1, 0.0),
          "反向驗：一路往上、沒有回落 ⇒ (−1, −1, 0)（⛔ 不是丟例外、⛔ 不是傳回 0 當位置）")
    # ⑨ 呼叫點（⭐ 測完純函式再掃一次原始碼）
    src = open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "researchp12.py"), encoding="utf-8").read()
    check(src.count("R.simulate_mtm(") == 1 and 'pick=None, cap_fn=None, d_max=None, queue_days=0, cash_mode="zero"' in src,
          "呼叫點：全檔只有【一個】地方呼叫引擎，且六個固定參數逐字寫在那一行（§八⑦）")
    check("P8.month_ci(dm)" in src and "P11.monthly_returns(eq, marks)" in src and "P3.exposure_series(eq, hv" in src
          and "R13.window_stats(eq, lo," in src,
          "呼叫點：CI 走 P8.month_ci、逐月報酬走 P11.monthly_returns、曝險走 P3.exposure_series、年化回落走 R13.window_stats（⛔ 本檔沒有第二份）")
    check('raise SystemExit("⛔ 否證①' in src and src.index("anchor_report(") < src.index('raise SystemExit("⛔ 否證①'),
          "⛔ 否證①：錨點沒過 ⇒ 先寫對帳檔再 SystemExit（⛔ 不會往下算主效果）")
    def _before(a_, b_):                       # ⭐ 找不到就回 False（⛔ 不讓 .index 丟例外把整支測試中斷）
        return a_ in src and b_ in src and src.index(a_) < src.index(b_)
    check(_before("check_anchors(tab, own_med)", "main_effect(df, mr, f, w, ct, arms)"),
          "順序：先對帳錨點、後算主效果（⛔ 不是算完才回頭看錨點）")
    check("caps_buy_all(sigs[(s, t, wk)], ncal)" in src and "P11.caps_series(sg, 1.0, ncal)[0]" in src,
          "呼叫點：C0a 用 caps_buy_all、【窄讀】那一版用 P11.caps_series（⛔ 本檔沒有第二份逐日容量實作）")
    check('("T", w, ct, {"S": "S0"})' in src, "呼叫點：T 的主效果真的有跑【只 S0 臂】那一版（裁定⑤）")
    check('("S", w, ct, {"T": "T1"})' in src and '("S", w, ct, {"T": "T0"})' not in src,
          "呼叫點：S 的第二版是【只 T1】（＝拿掉 4 檔那一欄），⛔ 不是只 T0（那剛好是反的）"
          "——策略線 1830 §三② ＋ K線分析線 1845 §二")


def t_weight_fn():
    """PREREGP13 seq=3 §二：引擎的 weight_fn（⭐ 預設 None 逐位元相同、nocap 不連累後面、現金最後一道保險）。"""
    ncal = 40
    cl = {k: np.linspace(10.0, 30.0, ncal) for k in ("A", "B", "C", "D", "E")}
    cl["E"] = np.linspace(30.0, 10.0, ncal)      # ⭐ E 一路跌：⛔ 沒有這個，「誰拿多少」改變了也看不出來（兩檔同報酬 ⇒ 權益相同）
    op = {k: v * 0.99 for k, v in cl.items()}
    sg = pd.DataFrame([{"sid": k, "entry_pos": 5, "xpos_H5": 20, "g_H5": cl[k][20] / op[k][5] - 1.0} for k in ("A", "B", "C")])
    # ⭐ 第二批在 t=25 進場（此時 equity 已經長大）⇒ ⛔ 沒有這一批，「equity[t−1] vs equity[t]」的前視分不出來
    #   （引擎在進場當下還沒寫 equity[t] ⇒ 它還是初始化的 1.0 ⇒ 只有一個進場日時兩者剛好相同）
    sg2 = pd.concat([sg, pd.DataFrame([{"sid": k, "entry_pos": 25, "xpos_H5": 35, "g_H5": cl[k][35] / op[k][25] - 1.0}
                                       for k in ("A", "B")])], ignore_index=True)
    run = lambda **kw: R.simulate_mtm(sg, "H5", 4, np.random.default_rng(11), cl, op, ncal, return_equity=True, **kw)
    base = run()
    # ① 預設 None ⇒ 原版路徑（本身就是同一條路，⭐ 這一條驗的是「加了參數沒有動到原版」）
    check(base["trades"] == 3 and abs(base["equity"][-1] - run()["equity"][-1]) == 0.0,
          "weight_fn 預設 None ⇒ 原版路徑（3 檔都進場）")
    # ② ⭐ 複製原版行為的 weight_fn ⇒ 權益【逐位元】相同（§四⑥ 要的回歸）
    def w0i(batch, t, equity, cash):
        slot = equity / 4; out = []
        for _ in batch:
            a = min(slot, cash); out.append(a); cash -= a
        return out
    r0i = run(weight_fn=w0i)
    check(np.array_equal(base["equity"], r0i["equity"]) and r0i["trades"] == base["trades"],
          "⭐ 複製 min(slot, cash) 的 weight_fn ⇒ 權益逐位元相同（⛔ 不是「差 0.5pp 以內」）")
    # ②b ⭐⭐ 兩個進場日的版本：驗 weight_fn 收到的 equity 是【t−1】那一天（⛔ 不是還沒寫的 equity[t]）
    run2 = lambda **kw: R.simulate_mtm(sg2, "H5", 4, np.random.default_rng(11), cl, op, ncal, return_equity=True, **kw)
    b2, i2 = run2(), run2(weight_fn=w0i)
    check(b2["trades"] == 5 and np.array_equal(b2["equity"], i2["equity"]) and b2["equity"][24] > 1.0,
          f"⭐ 兩個進場日（第二批在 equity ＝ {b2['equity'][24]:.3f} 時進場）⇒ 仍然逐位元相同"
          " ⇒ ⭐ weight_fn 收到的是 equity[t−1]（⛔ 傳 equity[t] 會拿到還沒寫的 1.0）")
    # ②c ⭐⭐ weight_fn 收到的 cash 必須是【當下的現金】（⛔ 不是 equity）——
    #     ⚠ 只有在 weight_fn【自己用 cash 做事】（P13 W1 的「按比例縮全批」）時才分得出來：
    #     引擎最後那道 min(target, cash) 會把「min(slot,·) 型」的差異全部吃掉。
    sg3 = pd.concat([pd.DataFrame([{"sid": k, "entry_pos": 5, "xpos_H5": 30, "g_H5": cl[k][30] / op[k][5] - 1.0} for k in ("A", "B", "C")]),
                     pd.DataFrame([{"sid": k, "entry_pos": 25, "xpos_H5": 35, "g_H5": cl[k][35] / op[k][25] - 1.0} for k in ("D", "E")])],
                    ignore_index=True)

    def _shrink(use_cash):                       # ＝ P13 的 W1 現金處置：Σtarget > cash ⇒ 全批同乘 k
        def f(batch, t, equity, cash):
            tg = [equity / 5] * len(batch)
            lim = cash if use_cash else equity    # ⭐ use_cash=False ＝ 模擬「引擎把 equity 當 cash 傳進來」
            ssum = sum(tg)
            return [x * (lim / ssum) for x in tg] if ssum > lim else tg
        return f
    r3 = lambda uc: R.simulate_mtm(sg3, "H5", 5, np.random.default_rng(11), cl, op, ncal, return_equity=True,
                                   weight_fn=_shrink(uc))
    ra, rb = r3(True), r3(False)
    check(ra["trades"] == rb["trades"] == 5 and not np.array_equal(ra["equity"], rb["equity"]),
          "⭐⭐ weight_fn 收到的 cash 必須是【當下的現金】：同一支函式改用 equity 當上限 ⇒ 權益路徑不同"
          "（⛔ 若引擎把 equity 當 cash 傳，這兩條會變成同一條 ⇒ 這條斷言就是在驗那件事）")
    check(abs(ra["equity"][-1] - rb["equity"][-1]) > 1e-6,
          f"⭐ 而差異看得見：按比例縮 ⇒ 兩檔各拿一半；不縮 ⇒ 第一檔吃飽、第二檔撿剩的"
          f"（末值 {ra['equity'][-1]:.6f} vs {rb['equity'][-1]:.6f}）")
    # ③ 市值加權：同一批之內金額不同 ⇒ ⭐ 這是原版做不到的那件事
    w = {"A": 3.0, "B": 2.0, "C": 1.0}
    rw = run(weight_fn=lambda b, t, eq, ca: [eq / 4 * len(b) * w[r["sid"]] / sum(w[x["sid"]] for x in b) for r in b])
    check(rw["trades"] == 3 and not np.array_equal(base["equity"], rw["equity"]),
          "按比例分配 ⇒ 同一天每檔金額不同（⛔ 原版辦不到）⇒ 權益與等權不同")
    # ④ ⛔ target ≤ 0 ⇒ 那一檔不進場、記 nocap，⭐ 而**後面的候選照常進場**（⛔ 不是 break）
    lg = []
    rn = R.simulate_mtm(sg, "H5", 4, np.random.default_rng(11), cl, op, ncal, return_equity=True, log=lg,
                        weight_fn=lambda b, t, eq, ca: [0.0 if r["sid"] == b[0]["sid"] else eq / 4 for r in b])
    check(rn["trades"] == 2 and sum(1 for r in lg if r["reason"] == "nocap") == 1,
          f"第一檔 target=0 ⇒ 它記 nocap 不進場，⭐ 其餘兩檔照常進場（實得 trades {rn['trades']}）")
    # ⑤ 引擎最後一道保險：target > cash ⇒ 只買得起 cash
    rc = run(weight_fn=lambda b, t, eq, ca: [eq * 10.0] + [eq * 10.0] * (len(b) - 1))
    check(rc["trades"] == 1, f"target 超過現金 ⇒ 第一檔吃光現金、其餘 nocap（實得 trades {rc['trades']}）")
    # ⑥ 長度對不上 ⇒ 大聲失敗
    try:
        run(weight_fn=lambda b, t, eq, ca: [eq / 4]); bad = False
    except ValueError:
        bad = True
    check(bad, "weight_fn 回的長度與 batch 對不上 ⇒ ValueError（⛔ 不靜靜只買一檔）")


def t_p13():
    """PREREGP13 seq=3 §二／§三 的三個 weight_fn ＋ 0050 代理 ＋ 重疊度。"""
    from . import researchp13 as P13
    B = [{"sid": x} for x in ("A", "B", "C")]
    caps = {"A": np.array([300.0] * 6), "B": np.array([100.0] * 6), "C": np.array([np.nan] * 6)}
    st = {"nocap": 0, "shrink": 0, "short": 0, "short_amt": 0.0, "k": []}
    f = P13.w_mktcap(caps, 8, st)
    tg = f(B, 3, 800.0, 1e9)                       # slot ＝ 100；可用 ＝ len(batch)×slot ＝ 300
    check(abs(tg[0] - 225.0) < 1e-9 and abs(tg[1] - 75.0) < 1e-9 and tg[2] == 0.0 and st["nocap"] == 1,
          f"W1：按【當批市值合計】分配 300 ⇒ A 300/400×300＝225、B 75、C 沒市值 ⇒ 0 並記 nocap（實得 {np.round(tg, 3).tolist()}）")
    check(abs(sum(tg) - 3 * 100.0 * (400 / 400)) < 1e-9,
          "⭐ 分母是 len(batch)（含 nocap 那一檔）⇒ 沒市值的那一格的錢【不投入】（⛔ 不是讓別人吃掉）")
    st2 = {"nocap": 0, "shrink": 0, "short": 0, "short_amt": 0.0, "k": []}
    tg2 = P13.w_mktcap(caps, 8, st2)(B, 3, 800.0, 150.0)   # cash 150 < Σtarget 300 ⇒ k=0.5
    check(abs(tg2[0] - 112.5) < 1e-9 and abs(tg2[1] - 37.5) < 1e-9 and st2["shrink"] == 1 and abs(st2["k"][0] - 0.5) < 1e-12,
          f"W1 現金不足 ⇒【按比例縮全批】k ＝ cash/Σtarget ＝ 0.5（⛔ 不是照順序給到沒錢；實得 {np.round(tg2, 3).tolist()}）")
    check(abs(tg2[0] / tg2[1] - tg[0] / tg[1]) < 1e-12, "⭐ 縮全批之後【批內比例不變】——那正是選它的理由")
    st3 = {"nocap": 0, "shrink": 0, "short": 0, "short_amt": 0.0, "k": []}
    e3 = P13.w_equal_shrink(8, st3)(B, 3, 800.0, 150.0)
    check(len(set(np.round(e3, 9))) == 1 and abs(sum(e3) - 150.0) < 1e-9,
          "W0′：等權 ＋ 縮全批 ⇒ 三檔金額相同、合計剛好等於現金")
    st4 = {"nocap": 0, "shrink": 0, "short": 0, "short_amt": 0.0, "k": []}
    e4 = P13.w_equal_seq(8, st4)(B, 3, 800.0, 150.0)
    check(abs(e4[0] - 100.0) < 1e-9 and abs(e4[1] - 50.0) < 1e-9 and e4[2] == 0.0 and st4["short"] == 2,
          f"W0i：複製 min(slot, cash) ⇒ 100／50／0（⭐ 與 W0′ 的 50/50/50 不同）並記 2 次現金不足（實得 {np.round(e4, 3).tolist()}）")
    # ⭐ 呼叫點：make_arm 有沒有把四個臂接到【對的】函式上（⛔ 上面那幾條測的是函式本身）
    fns = {a_: P13.make_arm(a_, caps, 8) for a_ in P13.ARMS}
    check(fns["W0"][0] is None and [round(x, 6) for x in fns["W0i"][0](B, 3, 800.0, 150.0)] == [100.0, 50.0, 0.0]
          and [round(x, 6) for x in fns["W0p"][0](B, 3, 800.0, 150.0)] == [50.0, 50.0, 50.0]
          and round(fns["W1"][0](B, 3, 800.0, 150.0)[0], 6) == 112.5,
          "make_arm：W0→None／W0i→min(slot,cash)／W0′→等權縮全批／W1→市值加權（⛔ 四個不可接錯）")
    # 0050 代理：只看上市普通股、逐月重算
    caps2 = {s: np.array([float(v)]) for s, v in (("A", 9), ("B", 8), ("C", 7), ("D", 99))}
    P13.TOP_N, keep = 2, P13.TOP_N
    top = P13.top50_by_month(caps2, {"A", "B", "C"}, np.array([0]), 1)
    P13.TOP_N = keep
    check(top[0] == {"A", "B"}, f"代理 ＝【上市普通股】市值前 N（⛔ D 市值最大但不在上市普通股清單裡）：{top[0]}")
    # 重疊度：兩個方向
    lg = [{"reason": "in", "t": 2, "exit_pos": 5, "sid": "A"}, {"reason": "in", "t": 2, "exit_pos": 5, "sid": "Z"}]
    P13.TOP_N, keep = 4, P13.TOP_N
    ov = P13._daily_overlap(lg, 10, 2, 4, {2: {"A", "Q"}}, np.array([2]))
    P13.TOP_N = keep
    check(abs(ov["ov_hold"] - 0.5) < 1e-12 and abs(ov["ov_50"] - 0.25) < 1e-12,
          f"重疊度【兩個方向】：持股 2 檔有 1 檔在前 N ⇒ 0.5；÷N(4) ⇒ 0.25（實得 {ov['ov_hold']}／{ov['ov_50']}）")
    # ⭐⭐ 整條分佈都要回（⛔ 只回中位會把「四成的日子有重疊」讀成「完全不重疊」，〈九十二〉）
    lg2 = [{"reason": "in", "t": 2, "exit_pos": 3, "sid": "A"}, {"reason": "in", "t": 2, "exit_pos": 5, "sid": "Z"}]
    P13.TOP_N, keep = 4, P13.TOP_N
    o2 = P13._daily_overlap(lg2, 10, 2, 4, {2: {"A", "Q"}}, np.array([2]))
    P13.TOP_N = keep
    check(o2["ov_hold"] == 0.0 and abs(o2["ov_hold_mean"] - 1 / 6) < 1e-12 and o2["ov_hold_max"] == 0.5
          and abs(o2["ov_days"] - 1 / 3) < 1e-12,
          f"⭐ A 只持有一天（t=2）、Z 持有三天 ⇒ 中位 0.0% 而平均 {o2['ov_hold_mean'] * 100:.1f}%、"
          f"最大 {o2['ov_hold_max'] * 100:.0f}%、有重疊的日子 {o2['ov_days'] * 100:.0f}%"
          " ⇒ ⛔ 只看中位會讀成【完全不重疊】")


def t_top50_share():
    """K線分析線 1915 §六：參考C 候選裡市值前 50 的比例（⛔ 描述性交件，⛔ 不是判定）。"""
    from . import researchp13 as P13
    from . import top50_share as TS
    sig = pd.DataFrame([("A", "2020-01", 11), ("B", "2020-01", 11), ("C", "2020-01", 11),
                        ("A", "2020-02", 31), ("D", "2020-02", 31), ("E", "2020-02", 31), ("F", "2020-02", 31),
                        ("G", "2020-03", 51), ("H", "2020-03", 51)], columns=["sid", "month", "entry_pos"])
    mp = TS.measure_pos(sig)
    check(mp == {"2020-01": 10, "2020-02": 30, "2020-03": 50},
          f"量測日位置 ＝ entry_pos − 1（⛔ 不是進場日；實得 {mp}）")
    try:
        TS.measure_pos(pd.DataFrame([("A", "2020-01", 11), ("B", "2020-01", 12)], columns=["sid", "month", "entry_pos"]))
        bad = True
    except SystemExit:
        bad = False
    check(not bad, "⭐ 同一個量測月有兩個 entry_pos ⇒ 「當月」沒有唯一量測日 ⇒ 必須【停】，⛔ 不可挑一個")
    # ⚠ 誘餌：進場日那三格的名單【故意不同】⇒ 取錯日期當場紅
    top = {10: {"A", "B"}, 30: {"D", "E"}, 50: {"A"},
           11: set(), 31: {"A", "D", "E", "F"}, 51: {"G", "H"}}
    tab = TS.share_by_month(sig, mp, top)
    check(tab["hit"].tolist() == [2, 2, 0] and tab["n"].tolist() == [3, 4, 2],
          f"逐月分子 ＝ 該月候選中落在【該月】前 50 的檔數、分母 ＝ 該月候選數（實得 "
          f"{tab['hit'].tolist()}／{tab['n'].tolist()}）")
    check(abs(tab["share"].tolist()[1] - 0.5) < 1e-12 and abs(tab["share"].tolist()[0] - 2 / 3) < 1e-12,
          "比例 ＝ hit ÷ n（⛔ 不是 hit ÷ 50、⛔ 不是 hit ÷ 前 50 名單長度）")
    s = TS.summarize(tab)
    check(s["hit"] == 4 and s["n"] == 9 and abs(s["share"] - 4 / 9) < 1e-12,
          f"⭐ 必報① 全窗合計 ＝ Σ分子 ÷ Σ分母 ＝ 4/9 ＝ {4 / 9:.4f}（⛔ 不是逐月比例的平均 "
          f"{np.mean(tab['share']):.4f} —— 兩者不同，月大小不一樣）")
    check(abs(s["med"] - 0.5) < 1e-12 and abs(s["p10"] - 0.1) < 1e-12 and abs(s["p90"] - 0.6333333333) < 1e-9,
          f"⭐ 必報② 逐月比例的中位／p10／p90 ＝ {s['med']:.4f}／{s['p10']:.4f}／{s['p90']:.4f}")
    check(s["zero_months"] == 1,
          "⭐ 分子為 0 的月份數要一起報（⛔ 只報中位會把「有些月一檔都沒有」蓋掉，〈九十二〉）")
    check(TS.EVENT_WIN == ("2023-07", "2025-04") and TS.WANT_EVENT_B == {"rows": 503, "stocks": 323, "months": 22},
          "對帳目標 ＝ 策略線 1445 §三 的【503 筆／323 檔／22 個月】（⛔ 寫死，⛔ 不是本件的判準）")
    check(TS.WANT_EVENT_HIT == 38 and TS.FIX_DAY == "2023-07-03",
          "⭐ 分子的對帳目標 38（1445 §四）與代理籃的【建籃日】2023-07-03（1445 §一）⛔ 都寫死")
    # ⭐ 對帳格：名單【逐月重算】vs【固定在窗頭】是兩個不同的數（⛔ 混用會得到一個對得上但口徑錯的答案）
    cap2 = {"A": np.array([9.0, 9.0, 1.0]), "B": np.array([8.0, 8.0, 8.0]), "C": np.array([1.0, 1.0, 9.0]),
            "Z": np.array([99.0, 99.0, 99.0])}
    sg = pd.DataFrame([("A", "2020-01", 1), ("C", "2020-01", 1), ("B", "2020-02", 3), ("C", "2020-02", 3)],
                      columns=["sid", "month", "entry_pos"])
    P13.TOP_N, keep = 1, P13.TOP_N
    g = TS.recon_grid(sg, TS.measure_pos(sg), cap2, {"含Z": {"A", "B", "C", "Z"}, "不含Z": {"A", "B", "C"}}, 0, 3)
    P13.TOP_N = keep
    got = {(r.universe, r.rule): r.hit for r in g.itertuples()}
    check(got == {("含Z", "逐月重算"): 0, ("含Z", "固定在窗頭"): 0,
                  ("不含Z", "逐月重算"): 2, ("不含Z", "固定在窗頭"): 1},
          f"⭐ 四格各自不同：母體含 Z ⇒ 前 1 永遠是 Z ⇒ 0 命中；不含 Z 時【逐月重算】2 命中"
          f"（1 月 A、2 月 C —— ⭐ 第 2 個月的龍頭換人了），⛔ 而【固定在窗頭】只有 1 命中"
          f"（兩個月都用 0 位的名單 {{A}}，而 2 月的候選裡沒有 A）；實得 {got}")
    check(int(g["n"].iloc[0]) == 4 and abs(float(g["share"].iloc[2]) - 0.5) < 1e-12,
          "對帳格的分母 ＝ 事件窗訊號筆數（⛔ 不是檔數），比例 ＝ hit ÷ n")
    # ⭐ 呼叫點：光測純函式不夠（四點五／七的第三個陷阱）
    import os as _os
    src = open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "top50_share.py"), encoding="utf-8").read()
    body = src.split("def main(")[1]
    check('signal="B"' in body and 'signal="C"' in body and "build_sig_gate_b" in body,
          "⭐ B 與 C 都由【同一支】build_sig_gate_b 造（⛔ 不另寫第二份 sig 建構）")
    check('"全市場"' in body and '"上市普通股"' in body and body.count("top50_by_month") == 2,
          "⭐ 前 50 的兩個母體【都要算】：全市場（1915 §六 字面）與上市普通股（策略線 38/503 的代理）⛔ 不挑一個")


def t_p13probe():
    """K線分析線 1755 §四 的兩個必報（⛔ 描述量，⛔ 不是判定）：單日崩跌、持有期間下市／停止交易。"""
    from . import p13_riskprobe as RP
    cl = np.array([100.0, 100.0, 69.0, 69.0, 80.0, 80.0, 80.0, 80.0], float)   # 第 2 天 −31%
    check(RP.crash_days(cl, 1, 7, -0.30) == [2] and RP.crash_days(cl, 3, 7, -0.30) == [],
          "單日 ≤ −30% 只算【窗內】那一天（⛔ 窗起點之前的不算、⛔ 不是拿 close[lo] 當基準算累積）")
    check(RP.crash_days(cl, 1, 7, -0.20) == [2] and RP.crash_days(cl, 1, 7, -0.35) == [],
          f"門檻是【≤】：−31% 打得到 −30%／−20%，打不到 −35%（⛔ 方向寫反會全中）")
    nanc = np.array([100.0, np.nan, 50.0, 25.0], float)
    check(RP.crash_days(nanc, 1, 3, -0.30) == [3],
          "⭐ 前一日收盤是 NaN 的那兩天【都不算】（⛔ NaN 比較永遠 False，⛔ 不可把它讀成「沒跌」以外的東西）；"
          "⭐ 而 25÷50 那一天的基準是真的收盤 ⇒ 它【要算】")
    # ⭐ 沒成交的天數【不連續】：總共 5 天，⛔ 最長連續只有 3 天
    op = np.array([1.0, np.nan, np.nan, 1.0, np.nan, np.nan, np.nan, 1.0], float)
    h3 = RP.halt_case(op, 0, 7, last_pos=-1, gap=3)
    check(h3["max_gap"] == 3 and h3["halted"] and not RP.halt_case(op, 0, 7, -1, gap=4)["halted"],
          f"連續沒成交的【最長段】＝ 3 天（⛔ 不是總天數 5 天）⇒ gap=3 算停止交易、gap=4 不算")
    check(RP.halt_case(op, 0, 7, last_pos=3)["delisted"] and not RP.halt_case(op, 4, 7, last_pos=2)["delisted"]
          and not RP.halt_case(op, 0, 7, last_pos=9)["delisted"],
          "下市 ＝ last_seen 落在【持有期間之內】：⛔ 在持有【之前】就消失的（last_seen 2 < 進場 4）不算、之後的也不算")
    check(RP.DROP_1D == -0.30 and RP.HALT_GAP == 5 and RP.CUM_LEVELS == (-0.30, -0.50),
          "1755 §四① 的門檻寫死 −30%（⛔ 本線不改）；累積那兩格是【另報的描述】")


if __name__ == "__main__":
    print("[researchp2] 映射"); t_parent()
    print("[researchp2] 逐日標籤"); t_labels()
    print("[researchp2] cap"); t_cap()
    print("[researchp2] 預設路徑"); t_default_identical()
    print("[researchp2/引擎] 停損兩族（PREREGP7）"); t_stop()
    print("[researchp7] 門檻B sig 重建"); t_gate_b_sig()
    print("[口徑] H〈n〉＝持有 n 根（追加二十一）"); t_hold_bars_ruling()
    print("[researchp6] 第二道篩與配對判定量"); t_p6_drop_and_pair()
    print("[researchp8] 分位／配對／代理檢定"); t_p8_helpers()
    print("[researchp2] 重疊度"); t_overlap()
    print("[researchp2] 判定"); t_judge()
    print("[researchp2] 種子"); t_seeds()
    print("[researchp11] 同選擇率（逐月 N_t）"); t_p11()
    print("[researchp12] 2×2×2 全因子（S／C／T）"); t_p12()
    print("[引擎] weight_fn（PREREGP13 seq=3 §二）"); t_weight_fn()
    print("[researchp13] 三個 weight_fn ＋ 0050 代理 ＋ 重疊度"); t_p13()
    print("[p13_riskprobe] 單一檔歸零的兩個必報（1755 §四）"); t_p13probe()
    print("[top50_share] 參考C 候選裡市值前 50 的比例（1915 §六）"); t_top50_share()
    print("結果：", "全綠" if FAIL == 0 else f"✗ {FAIL} 條")
    sys.exit(1 if FAIL else 0)
