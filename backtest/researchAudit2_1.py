# -*- coding: utf-8 -*-
"""稽核 ② 5（seq3 §二 第 5 列、§七之六；裁定 seq257 順 5）：正2 三態輪動 K7 重挑。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchAudit2_1
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchAudit2_1_check.py

原件：researchTri.py（bf4192c348；0052 描述臂 2adebff957 不動）。資料、訊號、狀態機、引擎、兩段、判準、假訊號、壓力段 ⇒ 全部 import 原件，⛔ 不改。
問題（稽核 K7）：挑中的 W4×P3×U4×現金，其跌深訊號「距 250 日高 −30%」在探索段 0 天成立 ⇒ 探索段實為「正2 ↔ 現金」兩態。

═══ 退化格排除（⭐ 本線讀法；開跑前寫死於此；⚠ 舊件的報酬本線已看過 ⇒ 規則只用【探索段狀態路徑的次數】，⛔ 不用任何報酬）═══
  計數：探索段 [2015-11-02, 2021-12-30] 內，狀態路徑（原件 machine，2005-02-02 起連續跑）每一個轉換日 t（st[t] ≠ st[t−1]）：
        nB ＝ A→B 次數｜nC ＝ B→C 次數（＝ 跌深態真的被用到）｜nA ＝ 回到 A 的次數（B→A＋C→A）
  X1 依構造兩態：B 態抱 0050 的格，B 與 C 都抱 0050（原件 weights）⇒ 持股路徑與跌深訊號無關（7 種跌深逐位元相同，本檔驗）⇒ 排除
  X2 跌深太少：nC ＜ 3（探索段約 6.2 年，平均兩年不到一次）⇒ 排除
  X3 轉弱太少：nB ＜ 3 ⇒ 排除
  X4 跌深太多：nC ÷ nB ＞ 0.9（幾乎每次轉弱都立刻落入跌深 ⇒ B 態幾乎不存在、實為 A ↔ C 兩態）⇒ 排除（〈一百二十六〉兩側都寫死）
  主版 ＝ 排除 X1～X4 後，照原件挑法（T7）重挑：乙 ＝ 探索年化最高（判定）、甲 ＝ 使用者判準合格中比值最高（並列）
  描述（⛔ 不判）：門檻改 1／5（X2、X3）、只套 X2～X4（保留 B 抱 0050 格）三種的挑中格與確認段數字
  N：重挑取代原挑法，⛔ 不另加 N（登錄 N_組合 ＋1 不變）
═══ 其他 ═══
  stop_force、T1 補尾：本件是 0050／00631L 兩檔 ETF 輪動、沒有固定持有天數出場、兩檔都沒停止交易 ⇒ 不適用（照實寫）
  閘：重跑 1,120 格 × 兩段 ⇒ ＝ resultsTri/body_cells.csv 逐位元；原挑法重挑 ⇒ ＝ W4×P3×U4×現金
輸出 backtest/resultsAudit2/1/
"""
from __future__ import annotations

import json
import os
import time
from itertools import product

import numpy as np
import pandas as pd

from . import researchTri as T

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsAudit2", "1")
TH, RATIO_MAX = 3, 0.9


def counts(st, i0, i1):
    """[i0, i1] 內的轉換計數與各態停留天數。"""
    t = np.arange(max(i0, 1), i1 + 1)
    a, b = st[t - 1], st[t]
    ch = a != b
    return {"nB（A→B）": int(np.sum(ch & (a == 0) & (b == 1))), "nC（B→C）": int(np.sum(ch & (a == 1) & (b == 2))),
            "nA（回 A）": int(np.sum(ch & (b == 0))), "A日": int(np.sum(st[i0:i1 + 1] == 0)), "B日": int(np.sum(st[i0:i1 + 1] == 1)),
            "C日": int(np.sum(st[i0:i1 + 1] == 2))}


def excl(row, th=TH, x1=True):
    why = []
    if x1 and row["B態"] == "B0050":
        why.append("X1")
    if row["nC（B→C）"] < th:
        why.append("X2")
    if row["nB（A→B）"] < th:
        why.append("X3")
    if row["nB（A→B）"] >= th and row["nC（B→C）"] / row["nB（A→B）"] > RATIO_MAX:
        why.append("X4")
    return "、".join(why)


def main():
    os.makedirs(OUT, exist_ok=True)
    T.OUT, T.LOGF = OUT, "run.log"
    open(os.path.join(OUT, "run.log"), "w").close()
    log = T.log
    t00 = time.time()
    log(f"===== researchAudit2_1（三態輪動 K7 重挑）{pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）=====")
    G = T.load_all(); cal = G["cal"]; N = len(cal)
    S, first, _ = T.signals(G); s0 = max(first.values())
    e0, e1 = T.idx(G, T.EXP[0]), T.idx(G, T.EXP[1]); c0, c1 = T.idx(G, T.CONF[0]), T.idx(G, T.CONF[1])
    x0, x1 = s0, T.idx(G, T.STRESS_END)
    b50 = pd.Series(G["C"]["0050"]).ffill().to_numpy()

    def bperf(i0, i1):
        seg = b50[i0:i1 + 1]; c, m = T.L2.R13.window_stats(seg / seg[0], 0, len(seg), 0, len(seg)); return float(c), float(m)
    B = {"探索": bperf(e0, e1), "確認": bperf(c0, c1)}
    hold = np.zeros((N, 2)); hold[:, 1] = 1.0
    PH = {sg: T.L2.perf(T.seg_run(G, hold, i0, i1)["eq"]) for sg, (i0, i1) in (("探索", (e0, e1)), ("確認", (c0, c1)))}
    Sx = {"原件": "researchTri.py bf4192c348", "0050同窗": {k: {"年化": v[0], "回落": v[1], "比值": T.L2.ratio(*v)} for k, v in B.items()},
          "純抱00631L": {k: {"年化": v[0], "回落": v[1]} for k, v in PH.items()}, "規則": {"門檻": TH, "X4 比例上限": RATIO_MAX},
          "stop_force／T1": "不適用（兩檔 ETF 輪動、無固定持有天數出場、無停止交易）", "閘": {}}
    # ── 1,120 格重跑＋計數
    rows = []; ST = {}; t0 = time.time()
    for (w, _), (p, _), (u, _), (b, _) in product(T.WEAK, T.DEEP, T.UP, T.BST):
        if (w, p, u) not in ST:
            ST[(w, p, u)] = T.machine(S, w, p, u, s0, N)
        st = ST[(w, p, u)]; W = T.weights(st, b)
        cnt = {sg: counts(st, i0, i1) for sg, (i0, i1) in (("早年", (x0, x1)), ("探索", (e0, e1)), ("確認", (c0, c1)))}
        for sg, (i0, i1) in (("探索", (e0, e1)), ("確認", (c0, c1))):
            r = T.seg_run(G, W, i0, i1)
            x = T.seg_stats(r, st[i0:i1 + 1], i1 - i0 + 1)
            c50, m50 = B[sg]
            rows.append({"段": sg, "轉弱": w, "跌深": p, "反彈": u, "B態": b, **x, "年化>0050": x["年化"] > c50,
                         "使用者判準": T.L2.label(x["年化"], x["回落"], c50, m50), "年化>純抱正2": x["年化"] > PH[sg][0],
                         **{f"{k}": v for k, v in cnt["探索"].items()},
                         **{f"確認_{k}": v for k, v in cnt["確認"].items()}, **{f"早年_{k}": v for k, v in cnt["早年"].items()}})
    df = pd.DataFrame(rows)
    log(f"[格] {len(df)} 列｜{time.time() - t0:.0f}s")
    # 閘：＝ 原件 body_cells.csv 逐位元
    old = pd.read_csv(os.path.join(HERE, "resultsTri", "body_cells.csv"), float_precision="round_trip")
    cols = [c for c in old.columns]
    mine = df[cols].reset_index(drop=True)
    diff = {c: int(sum(repr(a) != repr(b_) for a, b_ in zip(mine[c], old[c]))) for c in cols}
    Sx["閘"]["1,120 格×兩段 ＝ body_cells.csv（逐位元，各欄不同列數）"] = diff
    ok_gate = sum(diff.values()) == 0
    # X1 依構造：B 抱 0050 的格，7 種跌深逐位元相同
    g50 = df[df["B態"] == "B0050"].groupby(["段", "轉弱", "反彈"])
    x1_same = bool(all(g[c].nunique() == 1 for _, g in g50 for c in ("年化", "回落", "成交次數")))
    Sx["閘"]["X1 B 抱 0050 的格：7 種跌深年化／回落／成交次數全同"] = x1_same
    log(f"[閘] body_cells 逐位元 {ok_gate}（{diff}）｜X1 依構造同 {x1_same}")
    if not (ok_gate and x1_same):
        df.to_csv(os.path.join(OUT, "cells.csv"), index=False, encoding="utf-8", float_format="%.17g")
        raise SystemExit("⛔ 閘不過")
    ex = df[df["段"] == "探索"].reset_index(drop=True); ex["_o"] = range(len(ex))
    ex["排除（主版）"] = [excl(r) for _, r in ex.iterrows()]
    df = df.merge(ex[["轉弱", "跌深", "反彈", "B態", "排除（主版）"]], on=["轉弱", "跌深", "反彈", "B態"], how="left")
    df.to_csv(os.path.join(OUT, "cells.csv"), index=False, encoding="utf-8", float_format="%.17g")

    def cf(pk):
        return df[(df["段"] == "確認") & (df["轉弱"] == pk["轉弱"]) & (df["跌深"] == pk["跌深"]) & (df["反彈"] == pk["反彈"]) & (df["B態"] == pk["B態"])].iloc[0]

    def picks(pool):
        pb = pool.sort_values(["年化", "狀態轉換", "_o"], ascending=[False, True, True]).iloc[0]
        q = pool[(pool["年化"] > B["探索"][0]) & (pool["比值"] >= T.L2.ratio(*B["探索"]))]
        pa = q.sort_values(["比值", "狀態轉換", "_o"], ascending=[False, True, True]).iloc[0] if len(q) else None
        return pb, pa, len(q)

    def brief(pk):
        if pk is None:
            return None
        c = cf(pk)
        return {"格": [pk["轉弱"], pk["跌深"], pk["反彈"], pk["B態"]], "白話": f"{T.NAME[pk['轉弱']]} ⇒ 換{'0050' if pk['B態'] == 'B0050' else '現金'}｜"
                f"{T.NAME[pk['跌深']]} ⇒ 抱 0050｜{T.NAME[pk['反彈']]} ⇒ 回 00631L",
                "探索": {k: float(pk[k]) for k in ("年化", "回落", "比值", "每年轉換")},
                "探索計數": {k: int(pk[k]) for k in ("nB（A→B）", "nC（B→C）", "nA（回 A）", "A日", "B日", "C日")},
                "確認": {k: (float(c[k]) if isinstance(c[k], (float, np.floating)) else c[k]) for k in ("年化", "回落", "比值", "每年轉換", "每年成本", "使用者判準")},
                "確認計數": {k.replace("確認_", ""): int(c[k]) for k in c.index if k.startswith("確認_")},
                "早年計數": {k.replace("早年_", ""): int(c[k]) for k in c.index if k.startswith("早年_")},
                "判定": "只看報酬，贏 0050" if c["年化"] > B["確認"][0] else "沒有贏 0050", "年化>純抱正2": bool(c["年化"] > PH["確認"][0])}
    ob, oa, _ = picks(ex)
    Sx["閘"]["原挑法重挑 ＝ W4×P3×U4×現金"] = [ob["轉弱"], ob["跌深"], ob["反彈"], ob["B態"]] == ["W4", "P3", "U4", "Bcash"]
    Sx["原件挑法乙（K7 前）"] = brief(ob); Sx["原件挑法甲（K7 前）"] = brief(oa)
    pool = ex[ex["排除（主版）"] == ""]
    Sx["排除統計"] = {"探索 1,120 格": len(ex), "保留": len(pool), "X1": int(ex["排除（主版）"].str.contains("X1").sum()),
                    "X2": int(ex["排除（主版）"].str.contains("X2").sum()), "X3": int(ex["排除（主版）"].str.contains("X3").sum()),
                    "X4": int(ex["排除（主版）"].str.contains("X4").sum()),
                    "B現金格中被 X2～X4 排除": int(((ex["B態"] == "Bcash") & (ex["排除（主版）"] != "")).sum()),
                    "跌深 7 種各自在 B現金格的 nC 中位": {p: float(ex[(ex["B態"] == "Bcash") & (ex["跌深"] == p)]["nC（B→C）"].median()) for p, _ in T.DEEP}}
    pb, pa, nq = picks(pool)
    Sx["主版挑法乙（判定）"] = brief(pb); Sx["主版挑法甲（並列）"] = brief(pa); Sx["主版探索合格格數"] = nq
    log(f"[排除] {Sx['排除統計']}\n[主版乙] {Sx['主版挑法乙（判定）']}\n[主版甲] {Sx['主版挑法甲（並列）']}")
    # 描述：門檻 1／5、只套 X2～X4
    desc = {}
    for nm, th, x1 in (("門檻 1", 1, True), ("門檻 5", 5, True), ("保留 B 抱 0050（只 X2～X4）", TH, False)):
        pl = ex[[excl(r, th, x1) == "" for _, r in ex.iterrows()]]
        b_, a_, _ = picks(pl)
        desc[nm] = {"保留格數": len(pl), "乙": brief(b_), "甲": brief(a_)}
    Sx["描述_門檻敏感"] = desc
    # 2022、假訊號、壓力（主版乙；原件同法）
    st_b = ST[(pb["轉弱"], pb["跌深"], pb["反彈"])]; Wb = T.weights(st_b, pb["B態"])
    rb = T.seg_run(G, Wb, c0, c1)
    y1 = T.idx(G, "2022-12-30"); ny = y1 - c0 + 1

    def y22(eq):
        p_ = np.concatenate([[1.0], eq[:ny]]); return float(p_.min() * 1e6), float(eq[ny - 1] * 1e6)
    Sx["2022（100 萬：谷底、12-30）"] = {"主版乙": y22(rb["eq"]), "純抱00631L": y22(T.seg_run(G, hold, c0, c1)["eq"]),
                                    "0050": y22(b50[c0:c1 + 1] / b50[c0 - 1])}
    stc = st_b[c0:c1 + 1]; n = len(stc)
    chg = np.flatnonzero(stc[1:] != stc[:-1]) + 1
    seq = [int(stc[0])] + [int(stc[i]) for i in chg]
    rng = np.random.default_rng(T.SEED); res = []; days = np.zeros((T.NREP, len(chg)), np.int32)
    for j in range(T.NREP):
        dd = np.sort(rng.choice(np.arange(1, n), size=len(chg), replace=False)); days[j] = dd
        s2 = np.full(n, seq[0], np.int8)
        for q_, dday in enumerate(dd):
            s2[dday:] = seq[q_ + 1]
        full = np.zeros(N, np.int8); full[c0:c1 + 1] = s2
        c_, m_ = T.L2.perf(T.seg_run(G, T.weights(full, pb["B態"]), c0, c1)["eq"]); res.append((c_, m_))
    res = np.array(res)
    np.savez_compressed(os.path.join(OUT, "null_days.npz"), days=days, seq=np.array(seq, np.int8))
    pd.DataFrame(res, columns=["年化", "回落"]).to_csv(os.path.join(OUT, "null.csv"), index=False, float_format="%.17g")
    Sx["假訊號（主版乙，確認段）"] = {"轉換次數": int(len(chg)), "p_年化贏0050": float(np.mean(res[:, 0] > B["確認"][0])),
                               "年化贏純抱00631L比例": float(np.mean(res[:, 0] > PH["確認"][0])),
                               "使用者判準合格比例": float(np.mean([T.L2.label(c_, m_, *B["確認"]) == "合格" for c_, m_ in res]))}
    o, c = G["O"]["0050"], b50
    Lc = np.full(N, np.nan); Lo = np.full(N, np.nan); Lc[s0 - 1] = 1.0
    for t in range(s0, N):
        Lo[t] = Lc[t - 1] * (1 + 2 * (o[t] / c[t - 1] - 1)) if np.isfinite(o[t]) else np.nan
        Lc[t] = Lc[t - 1] * (1 + 2 * (c[t] / c[t - 1] - 1) - T.FEE)
    G["O"]["SYN"], G["C"]["SYN"] = Lo, Lc
    srows = []
    for nm, (a_, b_) in (("早年全段（起跑～2014-12-31）", (s0, T.idx(G, T.STRESS_END))), ("2008-01～2009-03", (T.idx(G, T.P08[0]), T.idx(G, T.P08[1])))):
        n_ = b_ - a_ + 1
        for who, W in (("主版乙（A 抱合成正2）", Wb), ("原件乙（A 抱合成正2）", T.weights(ST[(ob["轉弱"], ob["跌深"], ob["反彈"])], ob["B態"])),
                       ("純抱合成正2", hold), ("0050", None)):
            eq = b50[a_:b_ + 1] / b50[a_ - 1] if W is None else T.seg_run(G, W, a_, b_, lev="SYN")["eq"]
            p_ = np.concatenate([[1.0], eq]); pk = np.maximum.accumulate(p_)
            srows.append({"期間": nm, "起": str(cal[a_]), "迄": str(cal[b_]), "對象": who, "最大跌幅": float(((p_ - pk) / pk).min()),
                          "100萬谷底剩": float(p_.min() * 1e6), "100萬期末": float(eq[-1] * 1e6), "年化": float(eq[-1] ** (T.ANN / n_) - 1)})
    pd.DataFrame(srows).to_csv(os.path.join(OUT, "stress.csv"), index=False, encoding="utf-8", float_format="%.17g")
    Sx["壓力（合成、非實際 ETF）"] = srows
    log(f"[2022] {Sx['2022（100 萬：谷底、12-30）']}\n[假訊號] {Sx['假訊號（主版乙，確認段）']}\n[壓力]\n{pd.DataFrame(srows).to_string()}")
    json.dump(Sx, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=lambda o_: o_.item() if hasattr(o_, "item") else str(o_))
    log(f"[完] {time.time() - t00:.0f}s")


if __name__ == "__main__":
    main()
