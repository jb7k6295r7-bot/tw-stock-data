# -*- coding: utf-8 -*-
"""researchSwapWorst（換掉最差那檔 正式跑）fixture 自測＋突變測試（回測線計算子代理，2026-11-11）。⛔ 全部合成資料，不讀任何真實報酬。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.selftest_researchSwapWorst

T1 換最差那檔（觸發日收盤 ÷ 進場價）　T2 同分 ⇒ 換較早買進的　T3 隔天本來就要依原版出場的 ⇒ 不當換股對象（照原版補）
T4 同日多檔觸發：營量依 relvol 排序，依序換最差、次差　T5 觸發多於池 ⇒ 換完為止　T6 剛買（t−1）的也可被換
T7 換進來的也可再被換　T8 換進來的照原策略第 60 日（營飆第 120 日）收盤出場、毛報酬 ＝ 該列 g　T9 成本：賣出時一次扣來回 0.585%（買、賣各半）
T10 閘 G：swap=False（以及 swap=True 但沒有族群轉強）與 research11.simulate_mtm 逐筆、權益、hold_val 逐位元相同（營量 relvol、營飆抽籤、stop_force、tradable）
T11 營飆觸發股順序 ＝ 衍生抽籤流 default_rng([1000＋r, 505])；滿 20 日版：池只留持有 ≥ 20 日者
M1 突變「換最好那檔」⇒ T1／T4 必須失敗　M2 突變「不排除隔天出場的」⇒ T3 必須失敗
"""
from __future__ import annotations

import os
import sys
import types

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchSwapWorst as SW   # noqa: E402
from backtest import research11 as R           # noqa: E402

RES = {"PASS": 0, "FAIL": 0}
FAILS = []
COST = 0.00585


def ok(c, msg):
    RES["PASS" if c else "FAIL"] += 1
    print(("PASS " if c else "FAIL ") + msg)
    if not c:
        FAILS.append(msg)


def prices(sids, NP, base=10.0):
    return {s: np.full(NP, base) for s in sids}, {s: np.full(NP, base) for s in sids}


def frame(rows, cl, op, H=60):
    d = pd.DataFrame(rows, columns=["sid", "entry_pos", f"xpos_H{H}", "relvol", "grp"])
    d[f"g_H{H}"] = [cl[s][x] / op[s][e] - 1.0 for s, e, x in zip(d["sid"], d["entry_pos"], d[f"xpos_H{H}"])]
    return d


# ───────────── 情境（每個回傳 True／False 清單，給正常版與突變版共用）─────────────
def case_worst(S):
    """T1＋T8＋T9：2 槽，A、B 第 1 日買；第 4 日收盤 A −10%、B +10%；第 5 日 C（族群）觸發 ⇒ 換 A。"""
    NP = 20
    cl, op = prices("ABC", NP)
    cl["A"][4:] = 9.0; op["A"][5:] = 9.0; cl["B"][4:] = 11.0; op["B"][5:] = 11.0; cl["C"][6:] = 12.0
    sig = frame([("A", 1, 15, 1.0, 0), ("B", 1, 15, 2.0, 0), ("C", 5, 12, 1.0, 1)], cl, op)
    z = S.sim_swap(sig, "營量", 0, cl, op, NP, {}, swap=True, N=2)
    sw = z["swaps"]
    res = {"T1 換最差：第 5 日換出 A、換進 C": len(sw) == 1 and sw[0]["out"] == "A" and sw[0]["in"] == "C" and sw[0]["t"] == 5}
    if len(sw) == 1:
        gA = 9.0 / 10.0 - 1.0
        sell = [a for a in z["audit"] if a["side"] == "sell" and a.get("kind") == "swap"]
        buy = [a for a in z["audit"] if a["side"] == "buy" and a.get("kind") == "swap"]
        cash_after = 0.5 * (1 + gA - COST)
        exp_in = min(z["equity"][4] / 2, cash_after)
        res["T9 換出入帳 ＝ 金額 ×（1 ＋ 毛 − 0.585%）、換進金額 ＝ min(權益 ÷ N, 現金)"] = (abs(sell[0]["amt"] - 0.5 * (1 + gA)) < 1e-15 and abs(buy[0]["amt"] - exp_in) < 1e-15)
        cx = [a for a in z["audit"] if a["sid"] == "C" and a["side"] == "sell"]
        gC = 12.0 / 10.0 - 1.0
        res["T8 換進 C 照原排程第 12 日收盤出、毛 ＝ 該列 g"] = len(cx) == 1 and cx[0]["t"] == 12 and abs(cx[0]["amt"] - buy[0]["amt"] * (1 + gC)) < 1e-15
        gB = 11.0 / 10.0 - 1.0
        fin = cash_after - exp_in + exp_in * (1 + gC - COST) + 0.5 * (1 + gB - COST)
        res["T9 期末權益 ＝ 手算（每筆賣出各扣一次來回 0.585%）"] = abs(z["equity"][-1] - fin) < 1e-12 and R.COST == COST
    return res


def case_tie(S):
    """T2：A 第 1 日、B 第 2 日買，第 4 日收盤同為 −10% ⇒ 換較早買進的 A。"""
    NP = 20
    cl, op = prices("ABC", NP)
    cl["A"][4:] = 9.0; cl["B"][4:] = 9.0
    sig = frame([("A", 1, 15, 1.0, 0), ("B", 2, 15, 1.0, 0), ("C", 5, 12, 1.0, 1)], cl, op)
    z = S.sim_swap(sig, "營量", 0, cl, op, NP, {}, swap=True, N=2)
    return {"T2 同分 ⇒ 換較早買進的 A": len(z["swaps"]) == 1 and z["swaps"][0]["out"] == "A"}


def case_excl(S):
    """T3：A 最差但第 5 日本來就排程出場 ⇒ 不當換股對象：A 照原版收盤出、空位照原版補 D（relvol 大），C 觸發換 B。"""
    NP = 20
    cl, op = prices("ABCD", NP)
    cl["A"][4:] = 8.0; cl["B"][4:] = 9.5
    sig = frame([("A", 1, 5, 1.0, 0), ("B", 1, 15, 2.0, 0), ("D", 5, 15, 9.0, 0), ("C", 5, 12, 1.0, 1)], cl, op)
    z = S.sim_swap(sig, "營量", 0, cl, op, NP, {}, swap=True, N=2)
    sA = [a for a in z["audit"] if a["sid"] == "A" and a["side"] == "sell"]
    return {"T3 隔天就要出場的 A 不當換股對象：換出 B、換進 C": len(z["swaps"]) == 1 and z["swaps"][0]["out"] == "B" and z["swaps"][0]["in"] == "C",
            "T3 A 照原版第 5 日收盤出（不是換股賣）、D 照原版補": len(sA) == 1 and "kind" not in sA[0] and ("D" in {s for t, s in z["buys"] if t == 5})}


def case_multi(S):
    """T4＋T5：2 槽 A（−20%）、B（−10%）；第 5 日觸發 C（relvol 3）、E（relvol 5）、G（relvol 1）⇒ E 換 A、C 換 B、G 池不足不買。"""
    NP = 20
    cl, op = prices("ABCEG", NP)
    cl["A"][4:] = 8.0; cl["B"][4:] = 9.0
    sig = frame([("A", 1, 15, 1.0, 0), ("B", 1, 15, 2.0, 0), ("C", 5, 12, 3.0, 1), ("E", 5, 12, 5.0, 1), ("G", 5, 12, 1.0, 1)], cl, op)
    z = S.sim_swap(sig, "營量", 0, cl, op, NP, {}, swap=True, N=2)
    pr = [(e["in"], e["out"]) for e in z["swaps"]]
    rec = z["tlog"][0] if z["tlog"] else {}
    return {"T4 依 relvol 依序換最差、次差：E→A、C→B": pr == [("E", "A"), ("C", "B")],
            "T5 觸發多於池 ⇒ 換完為止（G 不買、記 1 筆）": rec.get("池不足未換") == 1 and "G" not in {s for _, s in z["buys"]}}


def case_fresh(S):
    """T6：B 第 4 日剛買、當天收盤 −20% ⇒ 第 5 日可被換。"""
    NP = 20
    cl, op = prices("ABC", NP)
    cl["B"][4:] = 8.0
    sig = frame([("A", 1, 15, 1.0, 0), ("B", 4, 15, 1.0, 0), ("C", 5, 12, 1.0, 1)], cl, op)
    z = S.sim_swap(sig, "營量", 0, cl, op, NP, {}, swap=True, N=2)
    z20 = S.sim_swap(sig, "營量", 0, cl, op, NP, {}, swap=True, N=2, min_hold=20)
    return {"T6 剛買（t−1）的也可被換：換出 B": len(z["swaps"]) == 1 and z["swaps"][0]["out"] == "B",
            "T11 滿 20 日版：持有不到 20 日 ⇒ 池空、不換": len(z20["swaps"]) == 0}


def case_reswap(S):
    """T7：第 5 日 C 換進（換出 A），第 5 日收盤 C −20%；第 6 日 E 觸發 ⇒ 換出 C。"""
    NP = 20
    cl, op = prices("ABCE", NP)
    cl["A"][4:] = 9.0; cl["C"][5:] = 8.0
    sig = frame([("A", 1, 15, 1.0, 0), ("B", 1, 15, 2.0, 0), ("C", 5, 12, 1.0, 1), ("E", 6, 14, 1.0, 1)], cl, op)
    z = S.sim_swap(sig, "營量", 0, cl, op, NP, {}, swap=True, N=2)
    pr = [(e["t"], e["in"], e["out"]) for e in z["swaps"]]
    return {"T7 換進來的也可再被換：(5,C←A)、(6,E←C)": pr == [(5, "C", "A"), (6, "E", "C")]}


def case_fly(S):
    """T8（營飆）＋T11：營飆換進的照第 120 日欄出場；兩檔同日觸發的順序 ＝ default_rng([1000＋r, 505]) 的抽籤。"""
    NP = 30
    cl, op = prices("ABCE", NP)
    cl["A"][4:] = 8.0; cl["B"][4:] = 9.0
    sig = frame([("A", 1, 25, 0.0, 0), ("B", 1, 25, 0.0, 0), ("C", 5, 20, 0.0, 1), ("E", 5, 22, 0.0, 1)], cl, op, H=120)
    r = 3
    z = S.sim_swap(sig, "營飆", r, cl, op, NP, {}, swap=True, N=2)
    perm = np.random.default_rng([1000 + r, 505]).permutation(2)
    exp_in = [["C", "E"][j] for j in perm]
    pr = [(e["in"], e["out"]) for e in z["swaps"]]
    ex = {a["sid"]: a["t"] for a in z["audit"] if a["side"] == "sell" and a["sid"] in ("C", "E")}
    return {"T11 營飆觸發順序 ＝ 衍生抽籤流，依序換最差 A、次差 B": pr == [(exp_in[0], "A"), (exp_in[1], "B")],
            "T8 營飆換進的照該列第 120 日欄出場（C 第 20 日、E 第 22 日）": ex == {"C": 20, "E": 22}}


def rand_fixture(seed, H, NP=90, nsid=14, nrow=70):
    rg = np.random.default_rng(seed)
    sids = [f"S{i:02d}" for i in range(nsid)]
    cl = {s: 10 * np.exp(np.cumsum(rg.normal(0, 0.02, NP))) for s in sids}
    op = {s: cl[s] * np.exp(rg.normal(0, 0.005, NP)) for s in sids}
    op[sids[0]][12] = np.nan
    cl[sids[1]][60:] = cl[sids[1]][59]
    SF = {sids[1]: 59}
    seen = set(); rows = []
    for _ in range(nrow):
        s = sids[int(rg.integers(nsid))]; e = int(rg.integers(1, NP - 15)); x = min(NP - 1, e + int(rg.integers(3, 14)))
        if (s, e) in seen:
            continue
        seen.add((s, e))
        rows.append((s, e, x, float(rg.normal()) if rg.random() > 0.1 else np.nan, int(rg.random() < 0.4)))
    d = frame(rows, cl, op, H)
    trd = {s: {"trd": rg.random(NP + 1) > 0.05, "up_o": rg.random(NP + 1) < 0.05, "dn_o": rg.random(NP + 1) < 0.05, "dn_c": rg.random(NP + 1) < 0.05} for s in sids}
    return d, cl, op, SF, trd


def engine(d, st, r, cl, op, NP, SF, N, tradable=None):
    au = []
    kw = {} if tradable is None else {"tradable": tradable}
    if st == "營量":
        o = R.simulate_mtm(d, "H60", N, np.random.default_rng(7000 + r), cl, op, NP, return_equity=True, log=[], d_max=None, pick="relvol",
                           queue_days=0, stop_force=SF, audit=au, **kw)
    else:
        o = R.simulate_mtm(d, "H120", N, np.random.default_rng(1000 + r), cl, op, NP, return_equity=True, stop_force=SF, audit=au, **kw)
    return o, au


def t_gate():
    n_ok = n = 0; swaps_seen = 0
    for st, H in (("營量", 60), ("營飆", 120)):
        for seed in range(6):
            for trad in (False, True):
                d, cl, op, SF, T = rand_fixture(seed, H)
                NP = 90
                tr = T if trad else None
                o, au = engine(d, st, seed, cl, op, NP, SF, 3, tr)
                for sw_flag, dd in ((False, d), (True, d.assign(grp=0))):
                    z = SW.sim_swap(dd, st, seed, cl, op, NP, SF, swap=sw_flag, N=3, tradable=tr)
                    g = SW.same_path([(int(a["t"]), str(a["sid"])) for a in au if a["side"] == "buy"],
                                     [(int(a["t"]), str(a["sid"])) for a in au if a["side"] != "buy"], o["equity"], o["hold_val"], o["first"], o["end"], au, z)
                    n += 1; n_ok += int(all(g.values()))
                zs = SW.sim_swap(d, st, seed, cl, op, NP, SF, swap=True, N=3, tradable=tr)
                swaps_seen += len(zs["swaps"])
                ok(sum(e["池內已出場"] for e in zs["tlog"]) == 0, f"T10 {st} seed{seed} {'tradable ' if trad else ''}開換股：池內已出場 0（換 {len(zs['swaps'])}）")
    ok(n_ok == n, f"T10 閘 G：關換股／無族群轉強 ＝ simulate_mtm 逐筆＋權益＋hold_val 逐位元（{n_ok}/{n}）")
    ok(swaps_seen > 0, f"T10 隨機 fixture 開換股確有換股（{swaps_seen} 次）⇒ 不是恆等於原版")


CASES = (case_worst, case_tie, case_excl, case_multi, case_fresh, case_reswap, case_fly)


def mutant(marker, old, new):
    src = open(SW.__file__, encoding="utf-8").read().split("\n")
    hit = 0
    for i, l in enumerate(src):
        if marker in l and not l.lstrip().startswith("#") and old in l:
            src[i] = l.replace(old, new); hit += 1
    if hit != 1:
        raise SystemExit(f"⛔ 突變點 {marker} 命中 {hit} 行（要 1）")
    m = types.ModuleType(f"sw_mut_{marker}"); m.__file__ = SW.__file__
    exec(compile("\n".join(src), m.__name__, "exec"), m.__dict__)
    return m


def main():
    for f in CASES:
        for k, v in f(SW).items():
            ok(v, k)
    t_gate()
    # 突變：必須被抓到（至少一條情境失敗）
    for name, (marker, old, new), cases in (
            ("M1 換最好那檔", ("_MUT_WORST", "(z[0], z[1], z[2])", "(-z[0], z[1], z[2])"), (case_worst, case_multi)),
            ("M2 不排除隔天出場的", ("_MUT_EXCL", "ex > t and ", ""), (case_excl,))):
        mm = mutant(marker, old, new)
        bad = [k for f in cases for k, v in f(mm).items() if not v]
        ok(len(bad) > 0, f"{name}：突變版被抓到（失敗 {len(bad)} 條：{bad[:2]}）")
    print(f"\n自測 PASS {RES['PASS']}／FAIL {RES['FAIL']}")
    if FAILS:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
