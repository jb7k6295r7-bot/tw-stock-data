# -*- coding: utf-8 -*-
"""researchGroupRevUp_freq 最少 fixture 自測（回測線計算子代理，2026-11-10）。⛔ 不讀任何真實報酬；全部是合成資料。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.selftest_researchGroupRevUp_freq

T1 Ward：ward_cut 對「每步窮舉全部群對 ΔSSE 取最小」的暴力版，隨機 3 組 × 多個 K，分群相同（同一分割）
T2 24 月新高兩讀法：手算序列
T3 族群轉強規則：≥3 家、≥1/3（含邊界 1/3、群 2 家恆假）
T4 引擎三版（價格全 1、毛 0）：1 槽、同日 3 候選 ⇒ 只買版只買旗標列；營量優先版旗標列先進（即使 relvol 較小）；
   prio 全 0 ⇒ 與原版逐筆相同（營量 relvol、營飆抽籤＋pick_tie＝rng 各驗）
T5 intervals／held_count／overlap_count／shortage：手算
"""
from __future__ import annotations

import itertools
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchGroupRevUp_freq as M   # noqa: E402

FAIL = []


def ok(c, msg):
    print(("OK  " if c else "FAIL") + " " + msg)
    if not c:
        FAIL.append(msg)


def brute_ward(X, K):
    cl = [[i] for i in range(len(X))]
    while len(cl) > K:
        best = None
        for a, b in itertools.combinations(range(len(cl)), 2):
            A, B = X[cl[a]], X[cl[b]]
            d = len(A) * len(B) / (len(A) + len(B)) * ((A.mean(0) - B.mean(0)) ** 2).sum()
            if best is None or d < best[0] - 1e-12:
                best = (d, a, b)
        _, a, b = best
        cl[a] = cl[a] + cl[b]; del cl[b]
    return sorted(sorted(c) for c in cl)


def part(lab):
    return sorted(sorted(np.flatnonzero(lab == g).tolist()) for g in set(lab.tolist()))


# T1
rng = np.random.default_rng(7)
for rep in range(3):
    X = np.vstack([rng.normal(c, 0.7, size=(6, 4)) for c in (0, 3, 6)]) + rng.normal(0, 0.05, size=(18, 4))
    for K in (2, 3, 5, 9):
        ok(part(M.ward_cut(X, K)) == brute_ward(X, K), f"T1 Ward rep{rep} K{K}")

# T2
idx = pd.period_range("2020-01", periods=30, freq="M").strftime("%Y-%m")
v = np.arange(30, dtype=float); v[24] = 10.0; v[25] = 100.0
rev = pd.DataFrame({"A": v}, index=idx)
hi, hib = M.hi24_tables(rev)
ok(not bool(hi["A"].iloc[23]) and bool(hib["A"].iloc[23]), "T2 第 24 期：主讀法要前 24 期 ⇒ 假；另一讀法前 23 期 ⇒ 真")
ok(bool(hi["A"].iloc[25]) and not bool(hi["A"].iloc[24]), "T2 第 26 期創高真、第 25 期非創高")
w2 = np.arange(30, dtype=float); w2[2] = np.nan
hi2, _ = M.hi24_tables(pd.DataFrame({"A": w2}, index=idx))
ok(not bool(hi2["A"].iloc[26]) and bool(hi2["A"].iloc[27]), "T2 前 24 期有缺 ⇒ 假；缺值移出窗後 ⇒ 真")

# T3
ok(M.group_up(1, 3) and not M.group_up(0, 3), "T3 3 家 1 家創高 ⇒ 真；0 家 ⇒ 假")
ok(not M.group_up(2, 2), "T3 2 家群恆假")
ok(M.group_up(4, 12) and not M.group_up(3, 12), "T3 12 家：4 家真、3 家假（1/3 邊界）")

# T4 引擎
NP = 40
S = pd.DataFrame({"sid": ["a", "b", "c", "d", "e"], "k": 0, "pos": [9, 9, 9, 19, 19], "entry_pos": [10, 10, 10, 20, 20],
                  "month": "2020-01", "xpos_H60": [15, 15, 15, 25, 25], "xpos_H120": [15, 15, 15, 25, 25],
                  "relvol": [5.0, 3.0, 1.0, 2.0, 9.0], "gated": True, "grp": [False, False, True, True, False]})
ones = {s: np.ones(NP) for s in S["sid"]}
M.STRATS["營量"]["N"] = 1; M.STRATS["營飆"]["N"] = 1
B = {}
for st in ("營量", "營飆"):
    for ver in M.VERS:
        sig = M.make_sig(S, st, ver)
        B[(st, ver)], _ = M.run_engine(sig, st, ver, 0, ones, NP, {})
ok(B[("營量", "原版")] == [(10, "a"), (20, "e")], "T4 營量原版 relvol 大者先")
ok(B[("營量", "只買版")] == [(10, "c"), (20, "d")], "T4 營量只買版只買旗標列")
ok(B[("營量", "優先版")] == [(10, "c"), (20, "d")], "T4 營量優先版旗標列先進（relvol 較小也先）")
ok(B[("營飆", "只買版")] == [(10, "c"), (20, "d")], "T4 營飆只買版")
ok(B[("營飆", "優先版")] == [(10, "c"), (20, "d")], "T4 營飆優先版旗標列先進")
for st in ("營量", "營飆"):
    for r in range(5):
        a, _ = M.run_engine(M.make_sig(S, st, "原版"), st, "原版", r, ones, NP, {})
        z, _ = M.run_engine(M.make_sig(S, st, "優先版", zero_prio=True), st, "優先版", r, ones, NP, {})
        ok(a == z, f"T4 {st} r{r} prio 全 0 ＝ 原版")

# T5
iv = M.intervals([(10, "a"), (20, "a"), (12, "b")], [(15, "a"), (25, "a")], 40)
ok(sorted(iv) == [("a", 10, 15), ("a", 20, 25), ("b", 12, 40)], "T5 intervals 配對")
hc = M.held_count(iv, 40)
ok(hc[9] == 0 and hc[10] == 1 and hc[12] == 2 and hc[15] == 1 and hc[20] == 2 and hc[39] == 1, "T5 held_count [買, 賣)")
ov = M.overlap_count([("a", 10, 15)], [("a", 12, 30), ("b", 10, 15)], 40)
ok(ov[11] == 0 and ov[12] == 1 and ov[14] == 1 and ov[15] == 0, "T5 overlap_count")
sg = pd.DataFrame({"sid": ["a", "x", "y"], "entry_pos": [13, 13, 13], "grp": [True, True, False]})
sh = M.shortage(sg, iv, 3, 40)
ok(sh[13] == (2, 1, 1), "T5 shortage：a 已持有不算、空槽 3−2")

# ── 增補 2026-11-11（--groups industry）──
# T6 產業檔讀入驗證（真實交件檔；只讀分群／旗標／名單，三份都不含報酬）
if os.path.isdir(M.IND_DIR):
    cl, gm, sg = M.load_industry()
    got, okk = M.check_industry(cl, gm, sg)
    ok(okk and got == {"clusters 列": 8824, "in_seq111": 4930, "族群轉強": 1030, "營收月": 113}, f"T6 產業檔讀入 {got}")
    ok(all(M.cyear(m) == int(y) for m, y in zip(gm["revenue_month"], gm["cluster_year"])), "T6 group_month_flags 分群年 ＝ m＋1 月的年")
    memi, upi = M.ind_tables(cl, gm)
    ok(sum(len(v) for v in memi.values()) == 8824 and len(upi) == len(gm), "T6 ind_tables 列數")
else:
    ok(False, f"T6 找不到產業交件夾 {M.IND_DIR}")

# T7 小 fixture：cyear、apply_flags（sig／pos 兩讀法、used＝0、查無）、readme_up 邊界、pair_stats、set_agree
ok(M.cyear("2016-12") == 2017 and M.cyear("2017-11") == 2017, "T7 cyear")
Sx = pd.DataFrame({"sid": ["a", "b", "c", "d", "a"], "period": ["2017-11", "2017-11", "2017-11", None, "2016-12"], "year": [2018, 2017, 2017, 2017, 2017]})
mem = {2017: {"a": (1, True), "b": (2, False), "c": (1, True)}, 2018: {"a": (5, True)}}
upx = {("2017-11", 2017, 1): True, ("2016-12", 2017, 1): False}
f, inu, cy, miss = M.apply_flags(Sx, mem, upx, "sig")
ok(f.tolist() == [True, False, True, False, False] and inu.tolist() == [True, False, True, False, True] and miss == 0, "T7 apply_flags sig")
f2, _, _, miss2 = M.apply_flags(Sx, mem, upx, "pos")
ok(f2.tolist() == [False, False, True, False, False] and miss2 == 1, "T7 apply_flags pos（a 在 2018 群 5 查無 ⇒ 0、計 1）")
idx = pd.period_range("2015-01", "2017-12", freq="M").strftime("%Y-%m")
rv = pd.DataFrame(1.0, index=idx, columns=list("pqrstuvwxy"))
rv.loc["2017-06", :] = 0.5
rv.loc["2017-06", ["p", "q", "r"]] = 9.0; rv.loc["2017-06", "s"] = np.nan
_, hb = M.hi24_tables(rv)
memA = {2017: {**{k: (0, True) for k in "pqrstu"}, "z": (1, False)}}
up_, st_ = M.readme_up(memA, rv, hb)
ok(st_[("2017-06", 2017, 0)] == (5, 3) and up_[("2017-06", 2017, 0)], "T7 readme_up：分母 ＝ 當月有營收 5（s 缺）、創高 3 ⇒ 真")
ok(("2017-06", 2017, 1) not in up_, "T7 readme_up：used＝0 群不算")
memB = {2017: {k: (0, True) for k in "pqrstuvwxy"}}
upB, stB = M.readme_up(memB, rv, hb)
ok(stB[("2017-06", 2017, 0)] == (9, 3) and upB[("2017-06", 2017, 0)], "T7 readme_up：9 家 3 家（＝1/3 邊界）⇒ 真")
rv.loc["2017-06", "s"] = 0.5
_, hb = M.hi24_tables(rv)
upC, stC = M.readme_up(memB, rv, hb)
ok(stC[("2017-06", 2017, 0)] == (10, 3) and not upC[("2017-06", 2017, 0)], "T7 readme_up：10 家 3 家 ⇒ 假（＜1/3）")
ps = M.pair_stats([0, 0, 1, 1, 2], [5, 5, 7, 7, 9])
ok(abs(ps["ARI"] - 1.0) < 1e-12 and ps["同群配對_兩邊都同群"] == 2, "T7 pair_stats 換號同分割 ARI＝1")
ps2 = M.pair_stats([0, 0, 0, 1, 1, 1], [0, 1, 2, 0, 1, 2])
ok(ps2["ARI"] < 0 and ps2["同群配對_兩邊都同群"] == 0, "T7 pair_stats 正交分割 ARI＜0")
sa = M.set_agree([(1, "a"), (1, "b")], [(1, "b"), (1, "c"), (2, "d")])
ok(sa["交集"] == 1 and abs(sa["交集÷聯集"] - 0.25) < 1e-12 and abs(sa["交集÷產業"] - 1 / 3) < 1e-12, "T7 set_agree")

# T8 --groups 預設 ⇒ 舊輸出逐位元相同（另起行程跑 --step report，GRU_OUT 指到暫存夾，對 git HEAD 的 freq/ 八檔）
import subprocess
import tempfile
need = [os.path.join(M.WORK, f"{k}_{w}.pkl") for k in ("world", "groups", "sim") for w in ("main", "early")]
if all(os.path.exists(x) for x in need):
    td = tempfile.mkdtemp(prefix="gru_selftest_")
    env = {**os.environ, "GRU_OUT": td, "PYTHONPATH": os.path.expanduser("~/tw-p17")}
    pr = subprocess.run([sys.executable, "-m", "backtest.researchGroupRevUp_freq", "--step", "report"], env=env, capture_output=True, text=True,
                        cwd=os.path.expanduser("~/tw-p17"))
    ok(pr.returncode == 0, "T8 預設 report 跑完")
    fs = subprocess.run(["git", "-c", "core.quotepath=off", "ls-files", "backtest/resultsGroupRevUp/freq/"], capture_output=True, text=True,
                        cwd=os.path.expanduser("~/tw-p17")).stdout.split()
    ok(len(fs) == 8, f"T8 HEAD freq/ 檔數 {len(fs)}")
    for f_ in fs:
        head = subprocess.run(["git", "show", f"HEAD:{f_}"], capture_output=True, cwd=os.path.expanduser("~/tw-p17")).stdout
        p_ = os.path.join(td, os.path.basename(f_))
        ok(os.path.exists(p_) and open(p_, "rb").read() == head, f"T8 逐位元相同 {os.path.basename(f_)}")
else:
    ok(False, "T8 ~/grpwork 中間檔不在（先照舊流程跑 world／groups／sim）")

print("全部通過" if not FAIL else f"⛔ 失敗 {len(FAIL)}：{FAIL}")
sys.exit(1 if FAIL else 0)
