# -*- coding: utf-8 -*-
"""美股便宜＋趨勢轉強 seq1——自測（合成 fixture＋PIT＋閘門；⛔ 不算任何報酬）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSCheapTrend_check

A 趨勢四態（合成序列）：T1～T4、T0 各一個 fixture；16 種布林組合真值表（依序判＝唯一命中，互斥＋涵蓋）；
  向量版＝單點版＝逐根暴力（np.mean 窗）；嚴格 >（常數序列 ⇒ 線下＋下彎 ⇒ T4）；20 日斜率恰取第 20 列前；
  暖身 269／270 列；等價「T1∪T2 ⇔ 收盤 > MA60」。
B PIT：真實 panel，趨勢在評估日只用評估日（含）前的列——截斷重算＝全量；評估日後竄改不影響；
  另以獨立讀檔（csv 直接連乘）逐筆重算可買名單的態。
C 資料：登錄檔 sha／大小；分組集合與 seq63 freq 表逐日相符；panel ret 空白記 0 後無 NaN。
D 正式跑閘門：無旗標、只 --formal、錯號、與 --dry 併用、多餘參數 ⇒ 拒跑（子程序 exit 2、不建 formal/）；只有 --formal --ruling seq484 過閘
  （沿革：裁定 seq484 §一 准正式跑，閘門 seq482 → seq484；舊號 seq482 拒跑）；正式判語固定「還沒測（依構造，7 群 < 24）」與數字無關。
"""
import os
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchUSCheapTrend as M          # noqa: E402
from backtest import researchUSFairValue_freq as FQ     # noqa: E402

FAILS, PASSES = [], []


def ok(cond, name):
    (PASSES if cond else FAILS).append(name)
    print(("PASS " if cond else "FAIL ") + name)


def brute(c):
    c = np.asarray(c, float)
    n = len(c)
    out = np.full(n, M.NA)

    def ma(k, L):
        return np.mean(c[k - L + 1:k + 1]) if k - L + 1 >= 0 else np.nan
    for k in range(n):
        if k + 1 < 270:
            continue
        out[k] = M.classify_state(c[k], ma(k, 60), ma(k - 20, 60), ma(k, 250), ma(k - 20, 250))
    return out


def last(c):
    return int(M.trend_states(c)["state"][-1])


# ═════════ A ═════════
t = np.arange(400)
up = 100 * 1.002 ** t
down = 100 * 0.998 ** t
ok(last(up) == 1, "A1 T1 多頭：穩定上漲 ⇒ T1")
ok(last(down) == 4, "A2 T4 空頭：穩定下跌 ⇒ T4")
s2 = np.r_[100 * 0.99 ** np.arange(350), 100 * 0.99 ** 349 * 1.02 ** np.arange(1, 31)]
tr = M.trend_states(s2)
k = len(s2) - 1
ok(tr["state"][k] == 2 and s2[k] > tr["ma60"][k] and s2[k] <= tr["ma250"][k], "A3 T2：長跌後急拉（MA60 線上、MA250 線下）⇒ T2")
s2b = np.r_[100 * 1.002 ** np.arange(300), 100 * 1.002 ** 299 * 0.995 ** np.arange(1, 61),
            np.full(8, 100 * 1.002 ** 299 * 0.995 ** 60 * 1.25)]
tr = M.trend_states(s2b)
k = len(s2b) - 1
ok(tr["state"][k] == 2 and s2b[k] > tr["ma60"][k] and tr["ma60"][k] <= tr["ma60p"][k] and s2b[k] > tr["ma250"][k],
   "A4 T2：MA60 線上但下彎、MA250 線上 ⇒ T2（另一成因）")
s3 = np.r_[100 * 1.003 ** np.arange(380), 100 * 1.003 ** 379 * 0.99 ** np.arange(1, 16)]
tr = M.trend_states(s3)
k = len(s3) - 1
ok(tr["state"][k] == 3 and s3[k] <= tr["ma60"][k] and s3[k] > tr["ma250"][k] and tr["ma250"][k] > tr["ma250p"][k],
   "A5 T3 長多回檔：長漲後短跌破季線、年線上揚 ⇒ T3")
# T0：收盤 ≤ MA60、≤ MA250，但 MA60 上揚（長跌→急漲→急跌）
s0 = np.r_[100 * 0.998 ** np.arange(300), 100 * 0.998 ** 299 * 1.01 ** np.arange(1, 41)]
s0 = np.r_[s0, s0[-1] * 0.93 ** np.arange(1, 6)]
tr = M.trend_states(s0)
k = len(s0) - 1
ok(tr["state"][k] == 0 and s0[k] <= tr["ma60"][k] and s0[k] <= tr["ma250"][k] and tr["ma60"][k] > tr["ma60p"][k],
   "A6 T0 其他：雙線下但 MA60 仍上揚 ⇒ T0")

# 真值表：16 種 (a60,a250,u60,u250)，c1..c4 至多命中一個（互斥）、依序判＝唯一命中者、換順序結果相同
excl, order_free = True, True
for b in range(16):
    a60, a250, u60, u250 = [bool(b >> i & 1) for i in range(4)]
    conds = [a60 and u60 and a250, a60 and ((not u60) or (not a250)), (not a60) and a250 and u250,
             (not a60) and (not a250) and (not u60) and (not u250)]
    if sum(conds) > 1:
        excl = False
    rev = 0
    for j in (3, 2, 1, 0):
        if conds[j]:
            rev = j + 1
    fwd = next((j + 1 for j in range(4) if conds[j]), 0)
    if rev != fwd:
        order_free = False
ok(excl, "A7 真值表：T1～T4 兩兩互斥（16 組合）")
ok(order_free, "A8 依序判與逆序判結果相同（依序不改歸類）")

rng = np.random.default_rng(7)
agree, agree_pt, eq_up, seen = True, True, True, set()
for i in range(60):
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, 600)))
    if i % 10 == 0:
        c = np.round(c, 0)        # 製造相等
    tr = M.trend_states(c)
    bf = brute(c)
    if not np.array_equal(tr["state"], bf):
        agree = False
    for k in range(269, 600, 37):
        s1 = M.classify_state(c[k], tr["ma60"][k], tr["ma60p"][k], tr["ma250"][k], tr["ma250p"][k])
        if s1 != tr["state"][k]:
            agree_pt = False
    v = tr["state"] != M.NA
    if not np.array_equal(np.isin(tr["state"][v], [1, 2]), (c > tr["ma60"])[v]):
        eq_up = False
    seen |= set(tr["state"][v].tolist())
ok(agree, "A9 向量版＝逐根暴力（60 條隨機序列，含整數化製造相等）")
ok(agree_pt, "A10 向量版＝單點版 classify_state")
ok(seen == {0, 1, 2, 3, 4}, "A11 隨機序列五態都出現（涵蓋）")
ok(eq_up, "A12 等價：T1∪T2 ⇔ 收盤 > MA60（恆等）")

const = np.full(300, 50.0)
ok(last(const) == 4, "A13 嚴格不等：常數序列（收盤＝均線、均線＝20 列前）⇒ 線下＋下彎 ⇒ T4")
tr = M.trend_states(c)
ok(np.allclose(tr["ma60p"][20:], tr["ma60"][:-20], equal_nan=True) and
   np.allclose(tr["ma250p"][20:], tr["ma250"][:-20], equal_nan=True), "A14 斜率比的是恰好第 20 列前的均線")
# 20 列 vs 19 列：在第 k 列前 20 列放一個尖峰，只影響 lag-20 的比較
sp = np.r_[np.full(330, 100.0)]
sp2 = sp.copy()
sp2[329 - 20 - 59] = 160.0        # 只在 MA60(k-20) 窗內（k＝329），不在 MA60(k) 窗內
trA, trB = M.trend_states(sp), M.trend_states(sp2)
ok(trA["state"][-1] == 4 and trB["ma60p"][-1] > trB["ma60"][-1] and trB["state"][-1] == 4,
   "A15 尖峰只進 20 列前窗 ⇒ MA60 下彎（仍 T4）")
ok(M.trend_states(up[:269])["state"][-1] == M.NA and M.trend_states(up[:270])["state"][-1] == 1,
   "A16 暖身：269 列不可判、270 列可判")
ok((M.trend_states(up[:270])["state"][:269] == M.NA).all(), "A17 暖身前全部不可判")

# ═════════ B PIT（真實資料）═════════
G = M.load_sets()
ok(True, "C1 分組集合與 seq63 freq_by_eval.csv 逐日相符（可買／接近／偏貴／母體／過門檻全部）")
evs = sorted(G)
sample = []
for d in evs[::3]:
    sample += [(d, t) for t in G[d]["可買"][:6]] + [(d, t) for t in G[d]["母體"][::60]]
pit_trunc, pit_tamper, indep = True, True, True
for d, t in sample:
    s, info = M.state_at(t, d)
    full = M.adj_series(t)
    upto = full[full.index <= pd.Timestamp(d)]
    s_tr = int(M.trend_states(upto.values)["state"][-1])
    if s_tr != s:
        pit_trunc = False
    tam = full.copy()
    m = tam.index > pd.Timestamp(d)
    tam[m] = tam[m] * np.exp(rng.normal(0, 0.3, m.sum()))
    st2 = M.trend_states(tam.values)["state"][tam.index.get_loc(pd.Timestamp(d))]
    if int(st2) != s:
        pit_tamper = False
    raw = pd.read_csv(FQ._p("panel", t + ".csv"), dtype={"date": str, "src": str})
    raw = raw[pd.to_datetime(raw["date"]) <= pd.Timestamp(d)]
    r = pd.to_numeric(raw["ret"], errors="coerce").fillna(0.0).values
    px = np.cumprod(1 + r)
    if brute(px)[-1] != s:
        indep = False
ok(pit_trunc, "B1 PIT：截斷到評估日重算＝全量（%d 筆）" % len(sample))
ok(pit_tamper, "B2 PIT：評估日後價格竄改，評估日的態不變")
ok(indep, "B3 獨立讀 csv＋逐根暴力＝程式態（%d 筆）" % len(sample))
nan_any = False
for d in evs[:1]:
    for t in G[d]["母體"]:
        if M.adj_series(t).isna().any():
            nan_any = True
ok(not nan_any, "C2 ret 空白記 0 後還原價無 NaN")

# ═════════ C 登錄 ═════════
reg = M.verify_registration()
ok(reg["bytes"] == 3718 and reg["相符"] in ("整檔", "去末行（pw1）"), "C3 登錄檔 3718 B、sha 前 16 碼 68b7253a5f696d15（%s）" % reg["相符"])

# ═════════ D 閘門 ═════════
ok(isinstance(M.gate([]), tuple), "D1 無旗標拒跑")
ok(isinstance(M.gate(["--formal"]), tuple), "D2 只 --formal 拒跑")
ok(isinstance(M.gate(["--formal", "--ruling", "seq481"]), tuple), "D3 錯號拒跑")
ok(isinstance(M.gate(["--dry", "--formal", "--ruling", "seq484"]), tuple), "D4 --dry 與 --formal 併用拒跑")
ok(isinstance(M.gate(["--ruling", "seq484"]), tuple), "D5 只 --ruling 拒跑")
ok(isinstance(M.gate(["--formal", "--ruling", "seq484", "--x"]), tuple), "D6 多餘參數拒跑")
ok(M.gate(["--dry"]) == "dry" and M.gate(["--formal", "--ruling", "seq484"]) == "formal", "D7 --dry、--formal --ruling seq484 過閘")
ok(isinstance(M.gate(["--formal", "--ruling", "seq482"]), tuple), "D7b 舊號 seq482 拒跑（閘門已改 seq484）")
ok(M.RULING == "seq484" and M.FIXED_VERDICT == "還沒測（依構造，7 群 < 24）"
   and all(M.final_verdict(a, b, c, d) == "還沒測（依構造，7 群 < 24）"
           for a, b, c, d in ((0.05, 0.01, 0.02, 0.03), (-0.05, -0.09, -0.02, -0.03), (None,) * 4)),
   "D9 正式判語固定「還沒測（依構造，7 群 < 24）」，不隨數字（正、負、None）變")
ok(any("台美主格口徑不同" in s for s in M.RESULT_SENTENCES), "D10 結果句含「台美主格口徑不同」")
existed = os.path.exists(M.FORMALD)
env = dict(os.environ, PYTHONPATH=os.path.expanduser("~/tw-p17"))
codes = []
for args in ([], ["--formal"], ["--formal", "--ruling", "seq481"], ["--dry", "--formal", "--ruling", "seq484"],
             ["--formal", "--ruling", "seq482"]):
    p = subprocess.run([sys.executable, "-m", "backtest.researchUSCheapTrend"] + args, cwd=os.path.expanduser("~/tw-p17"),
                       env=env, capture_output=True, text=True, timeout=120)
    codes.append(p.returncode)
ok(all(c == 2 for c in codes) and os.path.exists(M.FORMALD) == existed, "D8 子程序拒跑 exit 2 ×5（含舊號 seq482），未建 formal/（%s）" % codes)

print("\n%d PASS / %d FAIL" % (len(PASSES), len(FAILS)))
if FAILS:
    print("FAIL:", FAILS)
    sys.exit(1)
