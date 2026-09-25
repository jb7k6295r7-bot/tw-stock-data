# -*- coding: utf-8 -*-
"""PREREGP9 seq8 開跑前補件（裁定線 seq162 §四③④①）的 fixture 與真資料檢查。回測線，2026-09-25。

    cd ~/tw-p17 && python -m backtest.selftest_p9_builders fixtures          # 手算小例、無前視突變、鑑別力、對照臂
    cd ~/tw-p17 && python -m backtest.selftest_p9_builders real              # 真資料（edc6f 快照＋主窗）：旗標對 panel、不是恆等輸出
    cd ~/tw-p17 && python -m backtest.selftest_p9_builders addcount [--procs 2]   # 2-B 三格 × 200 顆種子的實際加成次數分佈
    cd ~/tw-p17 && python -m backtest.selftest_p9_builders panelsha          # resultsp4/panel.csv.gz 的 sha256 與位元組數 ⇒ PANEL_SHA.md

⛔⛔ 本檔【不跑 P9 的 12 格】、⛔ 不讀也不存任何年化／回落（seq162 §四③：12 格一次跑、一次交件）。
   addcount 只取引擎回傳的計數鍵（x_new_n／x_add_*），其餘鍵當場丟掉；ē 對照的真資料檢查只用【測試用 ē＝0.5】（⛔ 不是 ⓕⓖⓗ 的 ē）。
⭐ 預期值一律用獨立的手算式（整數名次規則、逐行算術），⛔ 不呼叫被測函式本身來產生預期。
結果寫到 backtest/resultsp9_engine/builders_*.json、b2_addcounts*.{csv,json}、PANEL_SHA.md（只新增檔）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import types
from multiprocessing import Pool

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(HERE, "resultsp9_engine")
SEED0 = 99000                     # PREREGP9 seq8 §一：default_rng(99000 + r)，r ∈ [0,200)
REPS = 200
N_MAIN = 8
RULE = "H120"
RESULTS: list = []


def chk(name, cond, detail=""):
    RESULTS.append({"name": name, "ok": bool(cond), "detail": detail})
    print(("  ✓ " if cond else "  ✗ ") + name + (f"｜{detail}" if detail else ""), flush=True)
    return bool(cond)


def dump(tag, extra=None):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, f"builders_{tag}.json")
    d = {"when": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M"), "n": len(RESULTS),
         "fail": sum(not r["ok"] for r in RESULTS), "checks": RESULTS}
    if extra:
        d["info"] = extra
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(f"寫入 {p}：{len(RESULTS)} 條，失敗 {d['fail']}")


# ─────────────────────────── 獨立的預期值（⛔ 不呼叫被測程式）
def expect_top(vals) -> list[bool]:
    """一個月的「前三分位」，整數規則：有限值依【出現順序】穩定排序給名次 1..n（同值先出現者名次小），
    名次 v 在前三分位 ⇔ 3v > 2n（＝ ceil(3v/n) − 1 ＝ 2，⛔ 不經浮點）；n < 3 ⇒ 全部 False；非有限 ⇒ False。"""
    v = np.asarray(vals, float)
    ok = np.flatnonzero(np.isfinite(v))
    n = len(ok)
    out = [False] * len(v)
    if n < 3:
        return out
    order = sorted(ok.tolist(), key=lambda i: (v[i], i))        # 值由小到大，同值依出現順序
    for rank, i in enumerate(order, start=1):
        out[i] = 3 * rank > 2 * n
    return out


def load_mutant(tag: str):
    """鑑別力用突變體（原始檔文字替換）：
       lag ＝ 量測日 d 的值改讀 d+1 的收盤（改讀當天之後的資料）
       pos ＝ 旗標放到 d−1（引擎在 d 開盤就讀到用 d 收盤算的旗標 ＝ 改讀當天）"""
    import backtest  # noqa: F401
    from backtest import p9_flags as F
    src = open(F.__file__, encoding="utf-8").read()
    rep = {"lag": ("v = ds[ix]  # _FLAG_LAG", "v = ds[np.minimum(ix + 1, len(ds) - 1)]  # _FLAG_LAG"),
           "pos": ("flags[sid][ix] = True  # _FLAG_POS", "flags[sid][np.maximum(ix - 1, 0)] = True  # _FLAG_POS")}[tag]
    if src.count(rep[0]) != 1:
        raise SystemExit(f"⛔ 突變點 {tag} 找不到（或不唯一）：{rep[0]!r}")
    name = f"backtest._p9f_mut_{tag}"
    mod = types.ModuleType(name)
    mod.__dict__.update({"__package__": "backtest", "__name__": name, "__file__": F.__file__})
    exec(compile(src.replace(rep[0], rep[1]), f"<{name}>", "exec"), mod.__dict__)
    return mod


def mdays(cal: pd.DatetimeIndex) -> np.ndarray:
    per = cal.to_period("M")
    return np.flatnonzero(np.r_[True, per[1:] != per[:-1]])


def mkpanel(rows):
    """rows：(measure_date, stock_id, eligible, dist)，⭐ 依給的順序（＝ panel 列順序）。"""
    return pd.DataFrame(rows, columns=["measure_date", "stock_id", "eligible", "dist_hi120"])


# ═════════════════════════════════════════ fixtures
def fixtures():
    from backtest import p9_flags as F
    from backtest import p9_controls as C
    from backtest import research11 as R
    from backtest import researchp8 as P8
    from backtest import researchp17 as P17

    print("── A. 旗標：三分位手算小例（source='panel'，P8 逐字）")
    cal = pd.bdate_range("2020-01-01", periods=260)
    md = mdays(cal)
    M = [cal[i] for i in md]
    rows = []
    # M0：10 檔 eligible（值刻意亂序）＋ 1 檔 not eligible 但最貼近高點 ⇒ 不排名、不進分母
    v10 = [-0.05, -0.50, -0.20, -0.35, 0.0, -0.45, -0.10, -0.30, -0.15, -0.40]
    rows += [(M[0], f"A{i}", True, v) for i, v in enumerate(v10)] + [(M[0], "Z", False, 0.0)]
    # M1：9 檔 ⇒ 前三名
    v9 = [-0.9, -0.8, -0.7, -0.6, -0.5, -0.4, -0.3, -0.2, -0.1]
    rows += [(M[1], f"A{i}", True, v) for i, v in enumerate(v9)]
    # M2：4 檔 ⇒ 名次 3、4（3v > 8）
    rows += [(M[2], f"A{i}", True, v) for i, v in enumerate([-0.4, -0.1, -0.3, -0.2])]
    # M3：2 檔 ⇒ n < 3 ⇒ 全 False
    rows += [(M[3], "A0", True, 0.0), (M[3], "A1", True, -0.5)]
    # M4：等號：S1..S6 ＝ −0.3, −0.2, −0.1, 0, 0, 0 ⇒ 名次 4、5、6 同值；n＝6 ⇒ 3v > 12 ⇒ S5、S6 進、S4 不進
    rows += [(M[4], f"S{i + 1}", True, v) for i, v in enumerate([-0.3, -0.2, -0.1, 0.0, 0.0, 0.0])]
    # M5：一檔 eligible 但值 NaN ⇒ 不進分母；其餘 3 檔 ⇒ 只有最大者
    rows += [(M[5], "A0", True, np.nan), (M[5], "A1", True, -0.3), (M[5], "A2", True, -0.2), (M[5], "A3", True, -0.1)]
    P = mkpanel(rows)
    fl = F.build_flags(P, cal, sids=list(set(P["stock_id"])) + ["NOPE"])
    pos = {d: i for i, d in enumerate(cal)}
    bad = []
    for d, g in P.groupby("measure_date", sort=False):
        e = g[g["eligible"]]
        exp = expect_top(e["dist_hi120"].to_numpy())
        for (sid, x) in zip(e["stock_id"], exp):
            if bool(fl[sid][pos[d]]) != x:
                bad.append((str(d.date()), sid, x))
    chk("A1 六個月的前三分位 ＝ 獨立整數規則（3·名次 > 2n、同值依列順序）", not bad, f"不符 {bad[:5]}")
    top0 = sorted(s for s in (f"A{i}" for i in range(10)) if fl[s][pos[M[0]]])
    chk("A2 n＝10 ⇒ 前 4 名（名次 7～10）；not eligible 的 Z（值 0、最高）不進、也不佔分母", top0 == ["A0", "A4", "A6", "A8"] and not fl["Z"].any(),
        f"前三分位 {top0}")
    chk("A3 n＝9 ⇒ 3 檔；n＝4 ⇒ 名次 3、4 共 2 檔；n＝2 ⇒ 0 檔",
        sum(fl[f"A{i}"][pos[M[1]]] for i in range(9)) == 3 and sum(fl[f"A{i}"][pos[M[2]]] for i in range(4)) == 2
        and not fl["A0"][pos[M[3]]] and not fl["A1"][pos[M[3]]])
    chk("A4 等號（P8 rank(method='first')）：S4／S5／S6 同為 0 ⇒ S5、S6 進、S4 不進（依列順序）",
        [bool(fl[f"S{i}"][pos[M[4]]]) for i in range(1, 7)] == [False, False, False, False, True, True])
    P_rev = pd.concat([P[P["measure_date"] != M[4]], P[P["measure_date"] == M[4]].iloc[::-1]])
    fl_rev = F.build_flags(P_rev, cal)
    chk("A5 等號的列順序依賴（揭露用）：M4 列順序倒過來 ⇒ 改成 S5、S4 進（S6 不進）",
        [bool(fl_rev[f"S{i}"][pos[M[4]]]) for i in range(1, 7)] == [False, False, False, True, True, False])
    chk("A6 值 NaN ⇒ 不排名、不進分母（其餘 3 檔 ⇒ 只 A3）",
        [bool(fl[f"A{i}"][pos[M[5]]]) for i in range(4)] == [False, False, False, True])
    nonm = np.ones(len(cal), bool); nonm[md] = False
    chk("A7 非量測日一律 False；不在 panel 的 sid 全 False",
        not any(f[nonm].any() for f in fl.values()) and not fl["NOPE"].any())
    el = P[P["eligible"]].copy(); el["ter"] = P8.xs_bucket(el, "dist_hi120", 3)
    via = {(r.measure_date, r.stock_id) for r in el[el["ter"] == 2].itertuples()}
    mine = {(cal[i], s) for s, f in fl.items() for i in np.flatnonzero(f)}
    chk("A8 與 researchp8 的切法（xs_bucket 桶 2）逐格相同", via == mine, f"{len(via)} vs {len(mine)}")

    print("── B. 三分位邊界的浮點（P8 的 ceil(名次/n×3)−1）：n＝3..600 與幾個大 n，前三分位檔數 ＝ n − ⌊2n/3⌋")
    ns = list(range(3, 601)) + [999, 1000, 1001, 1500, 2001, 2400, 3000]
    df = pd.DataFrame({"measure_date": np.repeat(np.arange(len(ns)), ns),
                       "x": np.concatenate([np.arange(n, dtype=float) for n in ns])})
    b = P8.xs_bucket(df, "x", 3)
    got = (b == 2).groupby(df["measure_date"]).sum().to_numpy()
    want = np.array([n - (2 * n) // 3 for n in ns])
    chk("B1 每個 n 的前三分位檔數都等於整數規則（⛔ 沒有浮點把邊界名次推進或推出）", (got == want).all(),
        f"不符的 n：{[n for n, g, w in zip(ns, got, want) if g != w][:10]}")

    print("── C. source='closes' 與無前視（合成隨機漫步 12 檔 × 400 日）")
    rng = np.random.default_rng(20260925)
    cal2 = pd.bdate_range("2019-01-01", periods=400)
    md2 = mdays(cal2); md2 = md2[md2 >= 130]
    sids = [f"K{i:02d}" for i in range(12)]
    closes = {s: 50 * np.exp(np.cumsum(rng.normal(0, 0.02, len(cal2)))) for s in sids}
    Pc = mkpanel([(cal2[d], s, True, np.nan) for d in md2 for s in sids])
    Pc["dist_hi120"] = [F.dist_hi120(closes[s])[d] for d in md2 for s in sids]
    chk("C1 dist_hi120 手算：第 i 天 ＝ close[i] ÷ max(close[i−119..i]) − 1；第 118 天 NaN（暖身）",
        abs(F.dist_hi120(closes["K00"])[200] - (closes["K00"][200] / closes["K00"][81:201].max() - 1)) < 1e-15
        and np.isnan(F.dist_hi120(closes["K00"])[118]) and np.isfinite(F.dist_hi120(closes["K00"])[119]))
    fa = F.build_flags(Pc, cal2); fb = F.build_flags(Pc, cal2, closes=closes, source="closes")
    chk("C2 source='closes' 與 source='panel'（同一條算式寫進 panel）逐日相同",
        all((fa[s] == fb[s]).all() for s in sids), f"旗標為真 {sum(int(f.sum()) for f in fa.values())} 個")
    cuts = sorted({int(d) + k for d in md2 for k in (-1, 0)})

    def leak(mod):
        base = mod.build_flags(Pc, cal2, closes=closes, source="closes")
        viol, changed = 0, 0
        for s in cuts:
            r2 = np.random.default_rng(s)
            c2 = {k: np.r_[v[:s + 1], v[s + 1:] * r2.uniform(0.6, 1.4)] for k, v in closes.items()}
            f2 = mod.build_flags(Pc, cal2, closes=c2, source="closes")
            viol += sum(int((f2[k][:s + 1] != base[k][:s + 1]).any()) for k in sids)
            changed += int(any((f2[k][s + 1:] != base[k][s + 1:]).any() for k in sids))
        return viol, changed

    v0, ch0 = leak(F)
    chk("C3 無前視：改 s 之後的收盤 ⇒ 旗標[≤ s] 一個都不變（s ＝ 每個量測日 d 與 d−1，共 %d 個切點）" % len(cuts), v0 == 0,
        f"違反 {v0}")
    chk("C4 修改不是空的：同一批修改在 s 之後確實改變了旗標", ch0 > 0, f"{ch0}／{len(cuts)} 個切點之後有變")
    for tag, what in (("lag", "量測日改讀 d+1 收盤"), ("pos", "旗標放到 d−1（引擎在 d 開盤就用 d 收盤）")):
        vm, _ = leak(load_mutant(tag))
        chk(f"C5 鑑別力：突變體「{what}」被抓到", vm > 0, f"違反 {vm}")

    print("── D. 旗標 × 引擎：量測日 d 前三分位 ⇒ d+1 開盤加 0.5 slot，只一次；進場前的旗標不算")
    cal3 = pd.bdate_range("2021-01-01", periods=200)
    md3 = mdays(cal3)                                   # 每月第一個交易日
    peers = [f"P{i}" for i in range(5)]
    X = "X0"
    rows = []
    # 每個量測日 6 檔 eligible；X 的值：m0 最高（在進場前）、m1 最低、m2 最高、m3 最高
    xval = {0: 0.0, 1: -0.9, 2: 0.0, 3: 0.0}
    for k, d in enumerate(md3[:6]):
        pv = [-0.5, -0.4, -0.3, -0.2, -0.1]
        rows += [(cal3[d], p, True, v) for p, v in zip(peers, pv)] + [(cal3[d], X, True, xval.get(k, -0.95))]
    Pd = mkpanel(rows).sort_values(["measure_date", "stock_id"], kind="stable").reset_index(drop=True)
    fl3 = F.build_flags(Pd, cal3, sids=[X])
    e = int(md3[0]) + 1; x = e + 119
    o = np.full(len(cal3), 10.0); c = np.full(len(cal3), 10.0)
    sig = pd.DataFrame([{"sid": X, "entry_pos": e, "xpos_HX": x, "g_HX": 0.0}])
    au = []
    out = R.simulate_mtm(sig, "HX", 2, np.random.default_rng(0), {X: c}, {X: o}, len(cal3), return_equity=True, audit=au,
                         add_rule={"kind": "flag", "flags": fl3})
    adds = [r for r in au if r.get("kind") == "add"]
    want_t = int(md3[2]) + 1
    chk("D1 旗標只在量測日：X 的旗標 ＝ m0、m2、m3 三天", np.flatnonzero(fl3[X]).tolist() == [int(md3[0]), int(md3[2]), int(md3[3])])
    chk("D2 m0 的旗標在進場前（引擎讀不到）、m1 不在前三分位 ⇒ 第一次加碼在 m2＋1 開盤；m3 不再加（只一次）",
        [r["t"] for r in adds] == [want_t] and out["x_add_n"] == 1 and out["x_add_trig"] == 1, f"加碼日 {[r['t'] for r in adds]}，要 {want_t}")
    chk("D3 加碼金額 ＝ 0.5 × equity[t−1] ÷ N（N＝2、價格不動 ⇒ 0.25）", adds and abs(adds[0]["amt"] - 0.25) < 1e-12,
        f"{adds[0]['amt'] if adds else None}")

    print("── E. ē 對照：手算小例（逐日權重、再平衡、成本、持股簿空的日子）")
    cal4 = pd.DatetimeIndex(["2020-01-27", "2020-01-28", "2020-01-29", "2020-01-30", "2020-01-31", "2020-02-03",
                             "2020-02-04", "2020-02-05", "2020-02-06", "2020-02-07", "2020-02-10", "2020-02-11"])
    K = 0.00585
    # 基準臂（手寫）：t1 開盤買 0.8；t2 +10%；t3 −5%；t4 平；t5（2/3）+20%；t6 收盤全出場（扣 0.8×K）；
    #               t7 開盤買 0.6、收盤 +5%；t8 −10%；t9 平；t10 +2%；窗 a＝1、b＝10
    H = np.zeros(12); E = np.ones(12)
    H[1] = 0.8; E[1] = 1.0
    H[2] = 0.88; E[2] = 1.08
    H[3] = 0.836; E[3] = 1.036
    H[4] = 0.836; E[4] = 1.036
    H[5] = 1.0032; E[5] = 1.2032
    H[6] = 0.0; E[6] = 1.2032 - 0.8 * K
    H[7] = 0.63; E[7] = E[6] + 0.03
    H[8] = 0.567; E[8] = E[7] - 0.063
    H[9] = 0.567; E[9] = E[8]
    H[10] = 0.57834; E[10] = E[9] + 0.01134
    H[11] = H[10]; E[11] = E[10]
    au4 = [{"t": 1, "side": "buy", "amt": 0.8}, {"t": 6, "side": "sell", "amt": 1.0032}, {"t": 7, "side": "buy", "amt": 0.6}]
    eb = 0.5
    # 手算：r_s ＝ (E[t]−E[t−1])/(H[t−1]+A[t])
    rs = {1: 0.0, 2: 0.10, 3: -0.05, 4: 0.0, 5: 0.20, 6: -0.8 * K / 1.0032, 7: 0.05, 8: -0.10, 9: 0.0, 10: 0.02}
    for mode in ("engine", "p17"):
        S = 0.5; Cc = 0.5; Vx = {}; cx = {}
        S *= 1 + rs[1]; Vx[1] = S + Cc
        S *= 1 + rs[2]; Vx[2] = S + Cc                                   # 0.55 + 0.5
        S *= 1 + rs[3]; Vx[3] = S + Cc
        S *= 1 + rs[4]; Vx[4] = S + Cc
        S *= 1 + rs[5]; v = S + Cc                                       # 2/3 ＝ 再平衡日
        d = eb * v - S                                                   # 需要賣（S 偏高）
        cx[5] = (abs(d) if mode == "p17" else max(-d, 0.0)) * K
        v -= cx[5]; S, Cc = eb * v, (1 - eb) * v; Vx[5] = v
        for t in (6, 7, 8, 9, 10):
            S *= 1 + rs[t]; Vx[t] = S + Cc
        res = C.ebar_control(E, H, au4, cal4, 1, 10, eb, cost=K, cost_mode=mode)
        okV = all(abs(res["V"][t] - Vx[t]) < 1e-12 for t in range(1, 11)) and abs(res["V"][11] - Vx[10]) < 1e-15 and res["V"][0] == 1.0
        chk(f"E1[{mode}] 逐日權益 ＝ 手算（10 天＋窗後持平＋窗前＝基準臂）", okV,
            json.dumps({t: [round(res["V"][t], 12), round(Vx[t], 12)] for t in (2, 5, 6, 10)}))
        chk(f"E2[{mode}] 再平衡日只有 2/3（窗首當月 1/27 不算）、成本 ＝ 手算", res["rebal"].tolist() == [5] and abs(res["cost"][5] - cx[5]) < 1e-15
            and res["cost"].sum() == res["cost"][5], f"成本 {res['cost'][5]!r}／手算 {cx[5]!r}")
    res = C.ebar_control(E, H, au4, cal4, 1, 10, eb, cost=K)
    h_hand = {1: 0.5 / 1.0, 2: 0.55 / 1.05, 5: 0.5}
    chk("E3 逐日持股比例：t1＝0.5、t2＝0.55/1.05、再平衡日＝ē（逐位元）；持股簿空（t6）＝0", abs(res["h"][1] - h_hand[1]) < 1e-12 and
        abs(res["h"][2] - h_hand[2]) < 1e-12 and res["h"][5] == 0.5 and res["h"][6] == 0.0)
    chk("E4 engine 口徑：再平衡日要賣 ⇒ 付 COST；p17 口徑兩向都付 ⇒ 相同（本例只有賣）",
        abs(C.ebar_control(E, H, au4, cal4, 1, 10, eb, cost=K, cost_mode="p17")["cost"][5] - res["cost"][5]) < 1e-18)
    # 一個要【買】的再平衡：同一條路但 t5 改成 −20%（窗 [1, 5]）⇒ 再平衡日 S 偏低 ⇒ engine 不付、p17 付
    E2_ = E.copy(); H2_ = H.copy(); H2_[5] = 0.836 * 0.8; E2_[5] = 0.2 + H2_[5]
    r_eng = C.ebar_control(E2_, H2_, au4, cal4, 1, 5, 0.5, cost=K, cost_mode="engine")
    r_p17 = C.ebar_control(E2_, H2_, au4, cal4, 1, 5, 0.5, cost=K, cost_mode="p17")
    S = 0.5 * 1.10 * 0.95 * 0.80; v = S + 0.5
    chk("E5 要買的再平衡（S＝0.418 ＜ ē·v＝0.459）：engine 口徑成本 0、p17 口徑 ＝ |ē·v − S| × COST", r_eng["cost"][5] == 0.0 and
        abs(r_p17["cost"][5] - abs(0.5 * v - S) * K) < 1e-15 and abs(r_eng["V"][5] - v) < 1e-12, f"S {S:.6f} v {v:.6f}")
    chk("E6 ebar_of 手算：equity [1,2,4]、持股 [0.5,1,1] ⇒ (0.5+0.5+0.25)/3",
        abs(C.ebar_of([1, 2, 4], [0.5, 1, 1], 0, 2) - 1.25 / 3) < 1e-15)
    calr = pd.bdate_range("2016-12-20", "2018-03-10")
    a_, b_ = 5, len(calr) - 3
    chk("E7 再平衡日 ＝ researchp17.rebal_days（+w0 還原成日曆位置）", C.rebal_days(calr, a_, b_).tolist() ==
        (P17.rebal_days(calr, a_, b_) + a_).tolist())
    rz = C.ebar_control(E, H, au4, cal4, 1, 10, 1.0, cost=0.0)
    chk("E8 退化解：ē＝1、成本 0 ⇒ V ＝ Π(1+r_s)（全額跟著持股簿）", abs(rz["V"][10] - np.prod([1 + rs[t] for t in range(1, 11)])) < 1e-12)

    print("── F. m̄ 對照：份數與 m̄ 的算法")
    chk("F1 mbar_of 2-B：新部位 10、加成 3、觸發 5 ⇒ executed 1.15／nominal 1.25",
        abs(C.mbar_of({"x_new_n": 10, "x_add_n": 3, "x_add_trig": 5}, "add") - 1.15) < 1e-15 and
        abs(C.mbar_of({"x_new_n": 10, "x_add_n": 3, "x_add_trig": 5}, "add", reading="nominal") - 1.25) < 1e-15)
    o15 = {"x_new_n": 4, "x_mbar_nominal": 1.25, "x_mult_short": 1}
    chk("F2 mbar_of ⓒ 1.5：4 個新部位、名目 (1+1+1.5+1.5)/4、其中 1 個現金不足只買 1 ⇒ executed 1.125／nominal 1.25",
        abs(C.mbar_of(o15, "mult", mult=1.5) - 1.125) < 1e-15 and C.mbar_of(o15, "mult", mult=1.5, reading="nominal") == 1.25)
    chk("F3 cell_value：中位（預設）與 pooled（按新部位數加權）", C.cell_value([1.0, 1.2, 1.1]) == 1.1 and
        abs(C.cell_value([1.0, 1.5], "pooled", weights=[3, 1]) - 1.125) < 1e-15)
    NC = 80
    def run(rows_, prices, N, **kw):
        cl = {s: p[1] for s, p in prices.items()}; op = {s: p[0] for s, p in prices.items()}
        sg = pd.DataFrame([{"sid": s, "entry_pos": e_, "xpos_HX": x_, "g_HX": float(cl[s][x_]) / float(op[s][e_]) - 1.0} for s, e_, x_ in rows_])
        au_ = []
        o_ = R.simulate_mtm(sg, "HX", N, np.random.default_rng(0), cl, op, NC, return_equity=True, audit=au_, **kw)
        return o_, au_
    flat = lambda: (np.full(NC, 10.0), np.full(NC, 10.0))
    rise = (np.r_[np.full(15, 10.0), np.full(NC - 15, 12.0)], np.r_[np.full(15, 10.0), np.full(NC - 15, 12.0)])
    pr = {"a": flat(), "b": rise, "c": flat()}
    o_, au_ = run([("a", 5, 60), ("b", 10, 60), ("c", 20, 60)], pr, 4, **C.mbar_kwargs(0.825, NC))
    buys = [r for r in au_ if r["side"] == "buy"]
    okb = len(buys) == 3 and all(abs(r["amt"] - 0.825 * r["equity_prev"] / 4) < 1e-12 for r in buys)
    chk("F4 m̄＝0.825：每個新部位都買 0.825 × equity[t−1] ÷ N（不看大盤）；x_mbar_nominal＝0.825、x_mult_n＝3",
        okb and abs(o_["x_mbar_nominal"] - 0.825) < 1e-15 and o_["x_mult_n"] == 3, f"{[round(r['amt'], 6) for r in buys]}")
    o_, au_ = run([("a", 5, 60), ("b", 5, 60)], {"a": flat(), "b": flat()}, 2, **C.mbar_kwargs(1.2, NC))
    buys = sorted((r["amt"] for r in au_ if r["side"] == "buy"), reverse=True)
    chk("F5 m̄＝1.2、同日兩檔、N＝2：第一檔 1.2×0.5＝0.6；第二檔現金 0.4 ＜ 0.6 ⇒ 照 2-B 規則只買 min(slot, 現金)＝0.4、x_mult_short＝1",
        len(buys) == 2 and abs(buys[0] - 0.6) < 1e-12 and abs(buys[1] - 0.4) < 1e-12 and o_["x_mult_short"] == 1, f"{buys}")
    below = np.zeros(NC, bool); below[19] = True                       # 引擎讀 below[t−1] ⇒ 第 20 日進場那一檔 ×0.5
    o_, _ = run([("a", 5, 60), ("b", 10, 60), ("c", 20, 60), ("d", 30, 60)], {"a": flat(), "b": flat(), "c": flat(), "d": flat()}, 4,
                size_mult_by_regime={"mult": 0.5, "below": below})
    chk("F6 m̄ 從格的輸出算：4 個新部位、1 個在線下 ×0.5 ⇒ (1+1+0.5+1)/4 ＝ 0.875", abs(C.mbar_of(o_, "mult", mult=0.5) - 0.875) < 1e-15,
        f"{o_['x_mbar_nominal']!r}")


# ═════════════════════════════════════════ 真資料（edc6f 快照＋主窗）
_G: dict = {}


def setup_real(log=print, need64=False):
    from backtest import rerun17 as RR
    RR.use_snapshot()
    from backtest import data as D
    from backtest import p4_features as P4F
    from backtest import researchp7 as P7
    cal = D.load_calendar(); ncal = len(cal)
    w0, w1 = RR.win_bounds(cal)
    uni = D.load_universe().set_index("stock_id")["market"]
    ppath = os.path.join(HERE, "resultsAFC", "panel.csv.gz")
    panel = P4F.read_panel(ppath)
    closes, opens = RR.load_prices(set(panel["stock_id"]), cal, uni, "branch")
    sig = P7.build_sig_gate_b(panel, cal, closes, opens, start="2017-01-01", signal="B")
    acc = P7.accept_sig_b(sig)
    e = sig["entry_pos"].to_numpy()
    sig_w = sig[(e >= w0) & (e <= w1)].reset_index(drop=True)
    info = {"data": D.DATA, "calendar": f"{len(cal)} 根 {cal[0].date()}～{cal[-1].date()}", "w0": [w0, str(cal[w0].date())],
            "w1": [w1, str(cal[w1].date())], "panel": ppath, "sig_accept": acc, "sig_rows_in_window": len(sig_w)}
    log(f"[真資料] {json.dumps(info, ensure_ascii=False, default=str)}")
    _G.update(cal=cal, ncal=ncal, w0=w0, w1=w1, uni=uni, panel=panel, closes=closes, opens=opens, sig=sig_w, D=D, info=info)
    return info


def real():
    from backtest import p9_flags as F
    from backtest import p9_controls as C
    from backtest import research11 as R
    from backtest import researchp17 as P17
    info = setup_real()
    cal, ncal, w0, w1, panel, closes, opens, sig, D = (_G[k] for k in ("cal", "ncal", "w0", "w1", "panel", "closes", "opens", "sig", "D"))
    extra = {"setup": info}

    print("── R1 旗標 vs 獨立整數規則（真 panel 全部量測日）")
    el = F.top_tercile(panel)
    bad = 0; tie_months = 0; n_months = 0; tops = 0
    for d, g in el.groupby("measure_date", sort=False):
        exp = np.array(expect_top(g["dist"].to_numpy()))
        bad += int((exp != g["top"].to_numpy()).sum()); tops += int(exp.sum()); n_months += 1
        v = np.sort(g["dist"].dropna().to_numpy()); n = len(v)
        if n >= 3:
            k = (2 * n) // 3                                   # 名次 k 是最後一個不進的、k+1 是第一個進的
            tie_months += int(v[k - 1] == v[k])
    chk("R1 前三分位 ＝ 獨立整數規則（逐列）", bad == 0, f"{n_months} 個量測日、前三分位 {tops:,} 列、不符 {bad}")
    extra["boundary_tie_months"] = tie_months
    chk("R1b 切點上的同值（名次 ⌊2n/3⌋ 與其下一名同值 ⇒ 列順序決定誰進）", True, f"{tie_months}／{n_months} 個量測日")

    print("── R2 panel 的 dist_hi120 ＝ 由 float64 還原收盤自算（⇒ panel 值只用 d 以前的收盤）")
    elig = panel[panel["eligible"].astype(bool)]
    c64 = {}
    for s in sorted(set(elig["stock_id"])):
        st = D.load_stock(s, _G["uni"].get(s, "twse"), cal)
        if st is not None:
            c64[s] = pd.Series(st.df["close"].to_numpy()).ffill().to_numpy(float)
    el2 = F.top_tercile(panel, cal, c64, source="closes")
    a = el["dist"].to_numpy(); b2 = el2["dist"].to_numpy()
    same = (a == b2) | (np.isnan(a) & np.isnan(b2))
    chk("R2 eligible 每一列 dist 逐位元相同", same.all(), f"{int(same.sum()):,}／{len(a):,} 列相同；最大差 {np.nanmax(np.abs(a - b2)):.3g}")
    chk("R2b source='closes' 的前三分位 ＝ source='panel'", (el["top"].to_numpy() == el2["top"].to_numpy()).all())

    print("── R3 主窗再平衡日 ＝ researchp17.rebal_days")
    rb = C.rebal_days(cal, w0, w1)
    chk("R3 再平衡日一致", rb.tolist() == (P17.rebal_days(cal, w0, w1) + w0).tolist(), f"{len(rb)} 個（{cal[rb[0]].date()}～{cal[rb[-1]].date()}）")

    print("── R4 ⛔ 不是恆等輸出（種子 0 ＝ default_rng(99000)；⛔ 只報觸發次數與「與全關不同」）")
    flags = F.build_flags(panel, cal, sids=set(sig["sid"]))
    fs = F.flag_summary(flags, w0, w1 + 1)
    last_md = str(panel["measure_date"].max().date())
    chk("R4a 門檻B 股票在主窗內的旗標有觸發", fs["flag_true"] > 0, f"{json.dumps(fs, ensure_ascii=False)}；panel 最後量測日 {last_md}")
    au0 = []
    base = R.simulate_mtm(sig, RULE, N_MAIN, np.random.default_rng(SEED0), closes, opens, ncal, return_equity=True, audit=au0)
    ob = R.simulate_mtm(sig, RULE, N_MAIN, np.random.default_rng(SEED0), closes, opens, ncal, return_equity=True,
                        add_rule={"kind": "flag", "flags": flags})
    cnt = {k: ob[k] for k in ("x_new_n", "x_add_trig", "x_add_n", "x_add_short", "x_add_blocked_days")}
    chk("R4b 2-B ⓑ（P8 三分位旗標）：equity 與全關不同、加碼有觸發", ob["equity"].tobytes() != base["equity"].tobytes() and ob["x_add_trig"] > 0,
        json.dumps(cnt, ensure_ascii=False))
    extra["seed0_2Bb_counts"] = cnt
    # 讀法 ③ 的影響量：基準臂種子 0 的每個部位，持有期間（進場日 … 出場前一日）遇到的量測日裡，該股 eligible／不是 eligible
    mdpos = {d: i for i, d in enumerate(cal)}
    E_ = {(mdpos[d], s) for d, s in zip(panel.loc[panel["eligible"].astype(bool), "measure_date"], panel.loc[panel["eligible"].astype(bool), "stock_id"]) if d in mdpos}
    mset = sorted({mdpos[d] for d in panel["measure_date"].unique() if d in mdpos})
    exit_of = dict(zip(zip(sig["sid"], sig["entry_pos"]), sig[f"xpos_{RULE}"]))
    n_el = n_nel = n_fl = n_after = 0
    for r in au0:
        if r["side"] != "buy":
            continue
        e_ = int(r["t"]); x_ = int(exit_of[(r["sid"], e_)])
        for m in mset:
            if e_ <= m <= x_ - 2:                             # 引擎在 m+1 ≤ x−1 開盤讀得到
                if (m, r["sid"]) in E_:
                    n_el += 1; n_fl += int(flags[r["sid"]][m])
                else:
                    n_nel += 1
        mx = max(mset)
        n_after += int(x_ - 2 > mx)
    rd = {"持有中遇到的量測日（eligible）": n_el, "其中前三分位": n_fl, "持有中遇到的量測日（不是 eligible ⇒ 讀法③ 記 False）": n_nel,
          "持有期超過 panel 最後量測日的部位": n_after}
    chk("R4c 讀法③／⑤ 的影響量（種子 0 基準臂部位；只報次數）", True, json.dumps(rd, ensure_ascii=False))
    extra["reading3_seed0"] = rd

    print("── R5 ē 對照（測試用 ē＝0.5，⛔ 不是 ⓕⓖⓗ 的 ē）與 m̄ 對照（測試用 m̄＝0.8、1.1）")
    ec = C.ebar_control(base["equity"], base["hold_val"], au0, cal, w0, w1, 0.5)
    chk("R5a ē 對照：與基準臂不同、有再平衡、實際平均持股比例貼近 ē", (ec["V"][w0:w1 + 1] != base["equity"][w0:w1 + 1]).any()
        and ec["n_rebal"] > 0 and abs(ec["ebar_realized"] - 0.5) < 0.05,
        f"再平衡 {ec['n_rebal']} 次、成本>0 的 {int((ec['cost'] > 0).sum())} 次、實際 ē {ec['ebar_realized']:.4f}")
    for mb in (0.8, 1.1):
        om = R.simulate_mtm(sig, RULE, N_MAIN, np.random.default_rng(SEED0), closes, opens, ncal, return_equity=True, **C.mbar_kwargs(mb, ncal))
        cm = {k: om[k] for k in ("x_new_n", "x_mult_n", "x_mult_short")}
        cm["x_mbar_nominal"] = round(float(om["x_mbar_nominal"]), 12)
        chk(f"R5b m̄＝{mb}：與全關不同、每個新部位都套倍數", om["equity"].tobytes() != base["equity"].tobytes() and om["x_mult_n"] == om["x_new_n"] > 0,
            json.dumps(cm, ensure_ascii=False))
    return extra


# ═════════════════════════════════════════ 2-B 三格實際加成次數（⛔ 只取計數）
KEEP = ("x_new_n", "x_add_trig", "x_add_n", "x_add_short", "x_add_blocked_days")


def _cells():
    return {"2-B ⓐ 收盤 ≥ 進場價 +15%": {"kind": "gain", "x": 0.15},
            "2-B ⓑ 貼近 120 日高點三分位（P8）": {"kind": "flag", "flags": _G["flags"]},
            "2-B ⓒ 持有滿 40 根仍為正": {"kind": "hold", "days": 40}}


def _count_one(args):
    from backtest import research11 as R
    cell, r = args
    au = []
    o = R.simulate_mtm(_G["sig"], RULE, N_MAIN, np.random.default_rng(SEED0 + r), _G["closes"], _G["opens"], _G["ncal"],
                       audit=au, add_rule=_cells()[cell])
    row = {"cell": cell, "r": r, "seed": SEED0 + r, **{k: int(o[k]) for k in KEEP}}
    row["x_add_n_in_window"] = sum(1 for a in au if a.get("kind") == "add" and a["t"] <= _G["w1"])
    del o, au                                                  # ⛔ cagr／mdd 等鍵不讀、不存
    return row


def addcount(procs=2):
    from backtest import p9_flags as F
    info = setup_real()
    _G["flags"] = F.build_flags(_G["panel"], _G["cal"], sids=set(_G["sig"]["sid"]))
    jobs = [(c, r) for c in _cells() for r in range(REPS)]
    t0 = time.time()
    with Pool(procs) as pool:
        rows = pool.map(_count_one, jobs, chunksize=10)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "b2_addcounts.csv"), index=False)
    summ = {"when": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M"), "setup": info, "secs": round(time.time() - t0),
            "note": "⛔ 只有計數；引擎其他回傳鍵（含年化／回落）當場丟掉、未讀未存。short='skip'（seq162 §四①）。百分位 numpy 線性內插。",
            "cells": {}}
    for c, g in df.groupby("cell", sort=False):
        d = {}
        for k in ("x_add_n", "x_add_n_in_window", "x_add_trig", "x_add_short", "x_new_n"):
            x = g[k].to_numpy(float)
            d[k] = {"median": float(np.median(x)), "p10": float(np.percentile(x, 10)), "p90": float(np.percentile(x, 90)),
                    "min": int(x.min()), "max": int(x.max())}
        d["structurally_near_unattainable（中位 ≤ 2）"] = bool(d["x_add_n"]["median"] <= 2)
        summ["cells"][c] = d
        print(f"  {c}：加成 中位 {d['x_add_n']['median']:g}（p10 {d['x_add_n']['p10']:g}／p90 {d['x_add_n']['p90']:g}）"
              f"｜窗內 中位 {d['x_add_n_in_window']['median']:g}｜觸發 中位 {d['x_add_trig']['median']:g}｜現金不足 中位 {d['x_add_short']['median']:g}"
              f"｜新部位 中位 {d['x_new_n']['median']:g}", flush=True)
    json.dump(summ, open(os.path.join(OUT, "b2_addcounts_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(f"寫入 b2_addcounts.csv（{len(df)} 列）、b2_addcounts_summary.json（{summ['secs']}s）")


# ═════════════════════════════════════════ panel sha
def panelsha():
    rows = []
    for rel in ("backtest/resultsp4/panel.csv.gz", "backtest/resultsAFC/panel.csv.gz"):
        p = os.path.join(REPO, rel)
        raw = open(p, "rb").read()
        tracked = subprocess.run(["git", "-C", REPO, "ls-files", "--error-unmatch", rel], capture_output=True).returncode == 0
        ign = subprocess.run(["git", "-C", REPO, "check-ignore", "-v", rel], capture_output=True, text=True).stdout.strip()
        blob = subprocess.run(["git", "-C", REPO, "hash-object", rel], capture_output=True, text=True).stdout.strip()
        pan = pd.read_csv(p, dtype={"stock_id": str}, parse_dates=["measure_date"], usecols=["measure_date", "stock_id", "eligible"])
        rows.append({"path": rel, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                     "mtime": pd.Timestamp(os.path.getmtime(p), unit="s", tz="UTC").tz_convert("Asia/Taipei").strftime("%Y-%m-%d %H:%M:%S"),
                     "tracked": tracked, "ignore": ign, "blob": blob, "rows": len(pan),
                     "md": f"{pan['measure_date'].min().date()}～{pan['measure_date'].max().date()}", "elig": int(pan["eligible"].astype(bool).sum())})
    head = subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    r4, rA = rows
    L = ["# resultsp4/panel.csv.gz 的指紋（裁定線 seq162 §四④）", "",
         f"量測 {pd.Timestamp.now(tz='Asia/Taipei').strftime('%Y-%m-%d %H:%M')}（台北）；工作樹 `~/tw-p17`（HEAD {head[:10]}，分支 claude/stock-analysis-backtest-iv9xji）。",
         "由 `python -m backtest.selftest_p9_builders panelsha` 產生（hashlib.sha256 讀整個檔的位元組）。", "",
         "⭐ 為什麼要記：這一份【沒有進 git】（.gitignore 擋掉）⇒ 別人要能確認拿到的是同一份（〈一百〇一〉）。",
         "P9 回歸閘 2（ENGINE_REPORT §三）與 P8、P9 2-C ⓑ 的 sig 都是從這一份建的。", "",
         "| 項 | 值 |", "|---|---|",
         f"| 路徑 | `{r4['path']}` |", f"| **sha256** | `{r4['sha256']}` |", f"| **位元組數** | {r4['bytes']:,}（{r4['bytes']} B） |",
         f"| 檔案時戳 | {r4['mtime']}（台北） |", f"| 進 git？ | {'是' if r4['tracked'] else '否'}（`{r4['ignore'] or '—'}`） |",
         f"| git hash-object（未入庫，只供比對） | `{r4['blob']}` |",
         f"| 內容 | {r4['rows']:,} 列、量測日 {r4['md']}、eligible {r4['elig']:,} 列 |", "",
         "## 參照：主窗（edc6f8002f 快照）用的 panel", "",
         f"`{rA['path']}` 有進 git（git blob `{rA['blob']}`）⇒ 以 git 為準；另記 sha256 `{rA['sha256']}`、{rA['bytes']:,} B、"
         f"{rA['rows']:,} 列、量測日 {rA['md']}、eligible {rA['elig']:,} 列。",
         "rerun17 main（主窗重跑）與本件 2-B 加成次數分佈用的是這一份。", ""]
    open(os.path.join(OUT, "PANEL_SHA.md"), "w", encoding="utf-8").write("\n".join(L))
    for r in rows:
        print(json.dumps(r, ensure_ascii=False))
    print(f"寫入 {os.path.join(OUT, 'PANEL_SHA.md')}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["fixtures", "real", "addcount", "panelsha"])
    ap.add_argument("--procs", type=int, default=2)
    a = ap.parse_args()
    t0 = time.time()
    if a.mode == "fixtures":
        fixtures(); dump("fixtures")
    elif a.mode == "real":
        ex = real(); dump("real", ex)
    elif a.mode == "addcount":
        addcount(a.procs)
    else:
        panelsha()
    print(f"完成（{time.time() - t0:.0f}s）")
    sys.exit(1 if any(not r["ok"] for r in RESULTS) else 0)
