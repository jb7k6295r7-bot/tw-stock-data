# -*- coding: utf-8 -*-
"""selftest：backtest/researchBigHolderRise.py（集保大戶比例上升 seq1，裁定 seq508）——玩具資料，不讀資料庫、不出報酬。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/selftest_researchBigHolderRise.py

測：① 閘（沒帶 --formal --ruling seq508 不出報酬）② 訊號門檻（第 95 百分位且 > 0）③ Δ4 只認剛好 4 週前那一週、同週取較晚
    ④ 全收版 12 份都沒出場 ⇒ 略過 ⑤ 10 檔版不重複買已持有 ⑥ 成本出場時以進場金額扣 0.585%
突變：把對應程式行改壞（_MUT_* 記號）⇒ 對應測試必須變紅。
"""
from __future__ import annotations

import os
import sys
import types

import numpy as np
import pandas as pd

from backtest import researchBigHolderRise as M0

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "researchBigHolderRise.py")


def t_gate(M):
    P = M.parse_args
    assert not M.formal_allowed(P([]))
    assert not M.formal_allowed(P(["--formal"]))
    assert not M.formal_allowed(P(["--ruling", "seq508"]))
    assert not M.formal_allowed(P(["--formal", "--ruling", "seq507"]))
    assert M.formal_allowed(P(["--formal", "--ruling", "seq508"]))
    try:
        M.formal(P([]), None, None)
    except SystemExit as e:
        assert "不出報酬" in str(e)
    else:
        raise AssertionError("沒帶閘卻沒擋")
    try:
        M.formal(P(["--formal", "--ruling", "seq508"]), None, {"一致率_交集除聯集": 0.97})
    except SystemExit as e:
        assert "98%" in str(e)
    else:
        raise AssertionError("一致率 < 98% 卻沒擋")


def t_sig(M):
    x = pd.Series(np.arange(-10, 90, dtype=float))          # 100 檔；第 95 百分位（線性內插）＝ 84.05
    m = M.sig_mask(x)
    assert m.sum() == 5 and set(x[m]) == {85, 86, 87, 88, 89}, x[m].tolist()
    neg = pd.Series(np.linspace(-1.0, -0.01, 100))           # 全負 ⇒ 過百分位也不算（要 > 0）
    assert M.sig_mask(neg).sum() == 0
    x2 = pd.Series([0.0] * 96 + [0.0, 0.0, 0.0, 0.0])         # 全 0 ⇒ 0 檔
    assert M.sig_mask(x2).sum() == 0


def t_delta4(M):
    ds = pd.to_datetime(["2020-01-03", "2020-01-10", "2020-01-17",            # 01-20 那週整週缺
                         "2020-01-27",                                         # 與 02-21−28＝01-24 差 3 日，但在下一週
                         "2020-02-03", "2020-02-07",                           # 同一週兩份 ⇒ 取 02-07
                         "2020-02-14", "2020-02-21", "2020-02-28"])
    vals = {d: i * 0.01 for i, d in enumerate(ds)}
    B = pd.DataFrame({"1101": [vals[d] for d in ds]}, index=ds)
    B.loc[pd.Timestamp("2020-02-03"), "1101"] = 9.9           # 被同週較晚那份蓋掉，不可出現
    bw, dates, D4 = M.delta4_frame(B)
    wk = lambda d: int((pd.Timestamp(d) - pd.Timestamp(M.WK0)).days // 7)
    assert pd.Timestamp("2020-02-03") not in set(dates.values)
    assert dates[wk("2020-02-07")] == pd.Timestamp("2020-02-07")
    # 02-21 的 4 週前那週（01-20 週）缺 ⇒ NaN（⛔ 不用 01-27 補）
    assert np.isnan(D4.loc[wk("2020-02-21"), "1101"])
    # 02-28 的 4 週前那週 ＝ 01-27 那週 ⇒ 有值
    assert abs(D4.loc[wk("2020-02-28"), "1101"] - (vals[pd.Timestamp("2020-02-28")] - vals[pd.Timestamp("2020-01-27")])) < 1e-12
    # 02-07 的 4 週前 ＝ 01-10
    assert abs(D4.loc[wk("2020-02-07"), "1101"] - (vals[pd.Timestamp("2020-02-07")] - vals[pd.Timestamp("2020-01-10")])) < 1e-12


def _flat(T=200, S=30):
    return np.ones((T, S)), np.ones((T, S))


def t_rotation(M):
    C, O = _flat()
    W = [{"e": e, "cols": [i], "sids": [f"{1101 + i}"]} for i, e in enumerate(range(0, 49, 4))]   # 13 週、間隔 4 根 ⇒ 第 13 週 12 份都沒出場
    r = M.sim_book("full", W, 0, 150, C, O)
    assert r["st"]["略過週"] == 1 and r["skipped"] == [48], (r["st"], r["skipped"])
    assert r["st"]["買進"] == 12
    W2 = W[:12] + [{"e": 60, "cols": [20], "sids": ["2000"]}]          # 第 1 份第 59 根出場 ⇒ 第 60 根可用
    r2 = M.sim_book("full", W2, 0, 150, C, O)
    assert r2["st"]["略過週"] == 0
    W3 = W[:12] + [{"e": 59, "cols": [20], "sids": ["2000"]}]          # 第 59 根當天收盤才出場 ⇒ 還不能用
    r3 = M.sim_book("full", W3, 0, 150, C, O)
    assert r3["st"]["略過週"] == 1
    W4 = [{"e": 10, "cols": [0], "sids": ["A"]}, {"e": 10, "cols": [1, 2], "sids": ["B", "C"]}]   # 連假：兩個資料週同一進場日 ⇒ 各用一份
    r4 = M.sim_book("full", W4, 0, 150, C, O)
    assert r4["st"]["買進"] == 3 and r4["st"]["略過週"] == 0, r4["st"]


def t_nodup(M):
    C, O = _flat()
    W = [{"e": 0, "cols": [0, 1, 2, 3, 4], "sids": list("ABCDE")},
         {"e": 5, "cols": [0, 1, 5, 6], "sids": list("ABFG")}]
    r = M.sim_book("ten", W, 0, 100, C, O)
    bought = sorted((t["e"], t["col"]) for t in r["trades"])
    assert r["st"]["已持有略過"] == 2, r["st"]
    assert bought == [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (5, 5), (5, 6)], bought
    # 滿了不買：12 檔訊號只買 10
    W2 = [{"e": 0, "cols": list(range(12)), "sids": [str(i) for i in range(12)]}]
    r2 = M.sim_book("ten", W2, 0, 100, C, O)
    assert r2["st"]["買進"] == 10 and r2["st"]["滿了沒買"] == 2


def t_cost(M):
    C, O = _flat()
    O[0, 0] = 10.0; C[:, 0] = 10.0; C[59:, 0] = 12.0
    W = [{"e": 0, "cols": [0], "sids": ["A"]}]
    r = M.sim_book("ten", W, 0, 80, C, O)
    want = 0.9 + 0.1 * (1 + 0.2 - 0.00585)
    assert abs(r["eq"][-1] - want) < 1e-12, (r["eq"][-1], want)
    assert abs(r["eq"][58] - (0.9 + 0.1)) < 1e-12           # 持有中市值不扣成本
    r2 = M.sim_book("full", W, 0, 80, C, O)
    want2 = 1 - 1 / 12 + 1 / 12 * (1 + 0.2 - 0.00585)
    assert abs(r2["eq"][-1] - want2) < 1e-12
    r3 = M.sim_book("ten", W, 0, 80, C, O, drop={(0, 0)})      # 改持現金 ⇒ 不扣成本、報酬 0
    assert abs(r3["eq"][-1] - 1.0) < 1e-12


TESTS = [("閘", t_gate), ("訊號門檻", t_sig), ("Δ4 那週", t_delta4), ("輪動略過", t_rotation), ("10 檔不重複買", t_nodup), ("成本扣法", t_cost)]
MUTS = [("_MUT_SIG", "(x >= q) & (x > 0)", "(x >= q)", "訊號門檻"),
        ("_MUT_D4", "full.shift(4)", "full.shift(3)", "Δ4 那週"),
        ("_MUT_SLOT", "if slot_exit[i] < t]", "]", "輪動略過"),
        ("_MUT_DUP", "if c not in held]", "]", "10 檔不重複買"),
        ("_MUT_COST", "amt * (1 + gross - cost)", "amt * (1 + gross)", "成本扣法")]


def run(M, names=None):
    bad = []
    for nm, f in TESTS:
        if names and nm not in names:
            continue
        try:
            f(M)
        except AssertionError as e:
            bad.append((nm, str(e)[:120]))
    return bad


def mutant(tag, old, new):
    src = open(SRC, encoding="utf-8").read()
    lines = src.split("\n")
    hit = [i for i, l in enumerate(lines) if tag in l and old in l]
    assert len(hit) == 1, f"突變點 {tag} 找到 {len(hit)} 行"
    lines[hit[0]] = lines[hit[0]].replace(old, new)
    m = types.ModuleType(f"mut{tag}")
    m.__file__ = SRC
    exec(compile("\n".join(lines), SRC, "exec"), m.__dict__)
    return m


def main():
    ok = True
    bad = run(M0)
    for nm, _ in TESTS:
        st = "紅 " + next(b[1] for b in bad if b[0] == nm) if any(b[0] == nm for b in bad) else "綠"
        print(f"[原程式] {nm}：{st}")
    ok &= not bad
    for tag, old, new, target in MUTS:
        b = run(mutant(tag, old, new), [target])
        red = bool(b)
        print(f"[突變 {tag}] {old} → {new}｜{target}：{'紅（抓到）' if red else '綠（⛔ 沒抓到）'}")
        ok &= red
    print("SELFTEST", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
