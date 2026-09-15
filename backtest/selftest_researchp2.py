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
    print("[researchp2] 重疊度"); t_overlap()
    print("[researchp2] 判定"); t_judge()
    print("[researchp2] 種子"); t_seeds()
    print("結果：", "全綠" if FAIL == 0 else f"✗ {FAIL} 條")
    sys.exit(1 if FAIL else 0)
