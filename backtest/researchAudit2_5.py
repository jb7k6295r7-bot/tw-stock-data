# -*- coding: utf-8 -*-
"""稽核 ② 5（seq3 §二 第 1 列、§八 研究三／四；裁定 seq257 順 5、seq258 §二）：選股條件 G1 營收創 24 月新高、G3 創高＋多頭排列 重測。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchAudit2_5 [--procs 2]
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchAudit2_5_check.py

原件：research34.py（研究三／四，PREREG3 更正一～三；面板 results3/panel.csv.gz，2026-09-18 分支快照）。
  G1 20 日超額 +1.87 pp、G3 +2.57 pp（對全期同批換股日平均、兩邊都扣 0.585% ⇒ 互抵）。股價創新高那條已刪（裁定 seq258 §二）。
問題：K1 只前後兩段、無早年；K2 只 20 日；K3 兩邊扣成本互抵；K4 無基準②；K5 月營收缺已下市。
═══ 照原件、⛔ 不改（import research34：process_stock、load_revenue、rebalance_dates；PREREG3 全部定義）═══
  換股日 D_M ＝ M＋1 月 10 日之後第一個交易日（訊號日 ＝ 前一日）；閘門 patterns.Frame.gate（500 張、處置、斷點視窗 [T−71, T＋59]）；
  G1 ＝ rev_hi24（M 月營收 ≥ 前 24 個月最高、24 個月完整）；C1 ＝ 訊號日 close ＞ MA20 ＞ MA60；G3 ＝ G1 ∧ C1；
  報酬 ＝ 固定持有 n 日（第 n 日收盤、跌停鎖死順延 ≤ 10 日）÷ D_M 開盤 − 1（evaluate.hold_exit ＝ 停止交易時用窗內最後收盤了結）
═══ 本件改／加（⭐ 開跑前寫死；本線讀法）═══
  資料：main 快照 edc6f8002f（rerun17.use_snapshot）；母體 ＝ universe_gate.gate3（原件 footnote：新跑件一律 gate3）⇒ 原件數字不逐位元重現（原件是 09-18 分支快照、無 gate3），
        本件先報「原件定義在快照上」的 G1／G3 20 日全期數字與原件並列（量級對照，⛔ 非閘）
  早年 2012～2014：早年版面 ~/earlydata/3edc0e2206/main（只上市；營收 data/early/revenue；0050 還原 2012～2014 三筆除息）；訊號日 2012-01～2014-12、出場 ≤ 2014-12-31
  H ∈ {5, 10, 20, 60}（patch research34.HOLDS；斷點視窗 H_FORWARD 不變 ＝ 71）
  段：探索 ＝ 訊號日 2016～2020；確認 ＝ 訊號日 2021 起、進場＋H−1 ≤ 2026-08-24；早年 ＝ 訊號日 2012～2014、進場＋H−1 ≤ 2014-12-31
  量（逐列）：X1 ＝ ret_H − 同一換股日全部閘門列 ret_H 平均（基準①）；X2 ＝ ret_H − 同一換股日、訊號日前 20 日報酬（有效 K 棒 20 根前收盤）
        同十分位（avgdown.deciles，該日閘門列、股票代號序）的其他列 ret_H 平均（基準②；自己不算）
  兩種成本口徑：甲「互抵」＝ X（兩邊都扣 0.585% ⇒ 抵銷）；乙「對成本」＝ X − 0.585%（超額要付得起一次來回；稽核「＞ 0.585% 慣例」）
  CI ＝ 換股月分群 CR0；出口 ＝ n_eff ＝ min(n, 月數)（＜30 ①／30～99 ②／≥100 ③）；結果② 好／③ 差／① 分不出
  同月隨機（假訊號，⛔ 不判）：每個換股日從該日閘門列（ret_H 可算）不放回抽與 G 同數量的列，X1 平均；200 次（rng 20260928＋r）；
        p ＝ 隨機平均 ≥ 真 G 平均 的比例
  G3 對「只看多頭排列」（C1）同月配對：每個換股日 m：d_m ＝ G3 列 ret_H 平均 − C1 列 ret_H 平均（兩邊都有列的月）；
        平均與 CI（月為單位；有效月數 ＝ 月數 ÷ max(1, H÷20)，research34 十分位差同法）
  下市月營收（照 P4 survivor_bound 報下界）：段內「rev_hi24 缺（該月沒有營收列）」的閘門列 ⇒ 全部當 G1（G3 另要 C1）、ret_H 代入 −100％／0％，
        X1 用它自己那個換股日的基準；報下界兩版的平均與 CI（⛔ 最壞情境、非估計值）；並報缺列中已下市（meta/delisted.csv）的列數
  「穩」：確認段四個 H、兩種成本口徑、基準② 的結果全同才寫
輸出 backtest/resultsAudit2/5/
"""
from __future__ import annotations

import argparse
import json
import os
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import data as D
from . import research34 as R34
from . import rerun17 as RR
from . import universe_gate as UG
from . import avgdown as AV
from . import evaluate as E

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsAudit2", "5")
HS = (5, 10, 20, 60)
COST = E.COST
EARLY = os.path.expanduser("~/earlydata/3edc0e2206/main/data")
SEGS = {"主": {"data": None, "sig": ("2016-01-01", "2026-08-24"), "end": "2026-08-24"},
        "早年": {"data": EARLY, "sig": ("2012-01-01", "2014-12-31"), "end": "2014-12-31"}}
NREP = 200


def work(args):
    rows = R34.process_stock(args)
    if not rows:
        return rows
    sid, market = args[0], args[1]
    cal = R34._G["cal"]
    st = D.load_stock(sid, market, cal)
    c = st.df["close"].to_numpy(float)
    r20 = AV.r20_cal(c, np.flatnonzero(np.isfinite(c)))
    for r in rows:
        r["r20"] = float(r20[r["signal_pos"]])
    return rows


def build(name, seg, procs, log, lim=None):
    if seg["data"]:
        D.DATA = seg["data"]
    else:
        RR.use_snapshot()
    R34.HOLDS = HS
    assert R34.H_FORWARD == 71
    cal = D.load_calendar()
    U = UG.gate3(pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str))
    if lim:
        U = U.head(lim)
    bdf = D.load_benchmark(cal)
    bench = {"o": bdf["open"].to_numpy(float), "c": bdf["close"].to_numpy(float)}
    disp = D.load_disposal_intervals()
    rev, rev_ly, ind = R34.load_revenue()
    rdates = R34.rebalance_dates(list(rev.index), cal, 10)
    lo = int(cal.searchsorted(pd.Timestamp(seg["sig"][0]))); hi = int(cal.searchsorted(pd.Timestamp(seg["sig"][1]), side="right") - 1)
    jobs = list(zip(U["stock_id"], U["market"], U["first_seen"], U["last_seen"]))
    rows = []; t0 = time.time()
    with Pool(procs, initializer=R34._init, initargs=(cal, bench, disp, rev, rev_ly, rdates, lo, hi)) as pool:
        for r in pool.imap_unordered(work, jobs, chunksize=8):
            if r:
                rows += r
    P = pd.DataFrame(rows)
    for c_ in ("rev_hi12", "rev_hi24", "rev_hi36", "bull"):
        if c_ in P:
            P[c_] = P[c_].astype("boolean")
    P["signal_date"] = [str(cal[i].date()) for i in P["signal_pos"]]
    w_end = int(cal.searchsorted(pd.Timestamp(seg["end"]), side="right") - 1)
    P["w_end"] = w_end
    dl = set(pd.read_csv(os.path.join(D.DATA, "meta", "delisted.csv"), dtype={"stock_id": str})["stock_id"])
    P["delisted"] = P["stock_id"].isin(dl)
    log(f"[{name}] 面板 {len(P):,} 列｜{P['stock_id'].nunique():,} 檔｜換股日 {P['period'].nunique()}｜{time.time() - t0:.0f}s｜資料 {D.DATA}")
    return P, cal


def cr0(x, g):
    x = np.asarray(x, float); n = len(x)
    m = float(x.mean()); d = x - m
    s = pd.Series(d).groupby(np.asarray(g)).sum().to_numpy()
    return m, float(np.sqrt((s ** 2).sum()) / n), len(s)


def judge(x, g):
    x = np.asarray(x, float); ok = np.isfinite(x); x, g = x[ok], np.asarray(g)[ok]
    if len(x) < 2:
        return {"n": int(len(x))}
    m, se, ng = cr0(x, g)
    ne = int(min(len(x), ng))
    lo, hi = m - 1.96 * se, m + 1.96 * se
    ex = "出口①" if ne < 30 else ("出口②" if ne < 100 else "出口③")
    rs = "樣本不足以分辨" if ne < 30 else ("結果①" if lo <= 0 <= hi else ("結果②" if m > 0 else "結果③"))
    return {"n": int(len(x)), "月數": int(ng), "n_eff": ne, "mean": m, "lo": lo, "hi": hi, "出口": ex, "結果": rs,
            "判定": {"結果②": "好", "結果③": "差"}.get(rs, "分不出")}


def add_x(P, H):
    """X1、X2（同一換股日）。回傳 P 的副本（只含 ret_H 可算的列）。"""
    col = f"ret{H}"
    Q = P[np.isfinite(P[col].astype(float))].copy()
    Q["b1"] = Q.groupby("period")[col].transform("mean")
    Q["X1"] = Q[col] - Q["b1"]
    Q = Q.sort_values(["period", "stock_id"]).reset_index(drop=True)
    x2 = np.full(len(Q), np.nan)
    for p, g in Q.groupby("period", sort=False):
        idx = g.index.to_numpy(); r = g["r20"].to_numpy(float); v = g[col].to_numpy(float)
        dec = AV.deciles(r)
        for k in range(10):
            mk = dec == k
            n = mk.sum()
            if n < 2:
                continue
            s = v[mk].sum()
            x2[idx[mk]] = v[mk] - (s - v[mk]) / (n - 1)
    Q["X2"] = x2
    return Q


def segment_rows(Q, name, cal, H):
    w_end = int(Q["w_end"].iloc[0])
    ok_end = (Q["entry_pos"] + H - 1) <= w_end
    y = pd.to_datetime(Q["signal_date"]).dt.year
    if name == "主":
        return {"探索 2016～2020": Q[ok_end & (y >= 2016) & (y <= 2020)], "確認 2021～2026": Q[ok_end & (y >= 2021)]}
    return {"早年 2012～2014": Q[ok_end & (y >= 2012) & (y <= 2014)]}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); ap.add_argument("--limit", type=int, default=None); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    log(f"===== researchAudit2_5（G1／G3 重測）{pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）procs {a.procs} =====")
    S = {"原件": "research34.py／results3（PREREG3 更正一～三；2026-09-18 分支快照）", "結果": {}}
    PAN = {}
    for name, seg in SEGS.items():
        P, cal = build(name, seg, a.procs, log, a.limit)
        P.to_csv(os.path.join(OUT, f"panel_{'main' if name == '主' else 'early'}.csv.gz"), index=False, float_format="%.17g")
        PAN[name] = (P, cal)
    # 量級對照：原件定義在快照上的 G1／G3 20 日全期（原件式：全期平均當基準、非重疊 SE）
    P, cal = PAN["主"]
    split = int(cal.searchsorted(pd.Timestamp("2021-01-04")))
    Pm = P[(P["signal_pos"] <= int(cal.searchsorted(pd.Timestamp("2026-07-31"), side="right") - 1))]
    orig = {}
    for nm, m in (("G1", Pm["rev_hi24"] == True), ("G3", (Pm["rev_hi24"] == True) & (Pm["bull"] == True)), ("C1", Pm["bull"] == True)):
        s = R34.stats(Pm[m.fillna(False)], "ret20", 20, Pm["ret20"].dropna().mean() - COST)
        orig[nm] = {"n": s["n"], "超額": s["excess"], "CI": [s["excess_ci_lo"], s["excess_ci_hi"]]}
    S["量級對照（原件式、本快照、訊號 2016-01～2026-07）"] = orig
    S["原件（results3 summary 第三版）"] = {"G1": {"n": 8827, "超額": 0.0187}, "G3": {"超額": 0.0257}}
    log(f"[量級對照] {orig}")
    rng0 = 20260928
    for name in SEGS:
        P, cal = PAN[name]
        for H in HS:
            Q = add_x(P, H)
            for sn, G in segment_rows(Q, name, cal, H).items():
                cell = {"閘門列": int(len(G)), "換股日": int(G["period"].nunique())}
                g1 = G["rev_hi24"] == True; c1 = G["bull"] == True; g3 = g1 & c1
                for tag, m in (("G1", g1), ("G3", g3), ("C1（描述）", c1)):
                    X = G[m.fillna(False)]
                    d = {"n": int(len(X))}
                    for xn in ("X1", "X2"):
                        d[f"{xn} 甲互抵"] = judge(X[xn], X["period"])
                        d[f"{xn} 乙對成本"] = judge(X[xn] - COST, X["period"])
                    d["X2 沒配對"] = int(X["X2"].isna().sum())
                    cell[tag] = d
                # 同月隨機（G1、G3）
                for tag, m in (("G1", g1), ("G3", g3)):
                    k = G[m.fillna(False)].groupby("period").size()
                    real = float(G[m.fillna(False)]["X1"].mean()) if k.sum() else np.nan
                    byp = {p: g["X1"].to_numpy(float) for p, g in G.groupby("period")}
                    reps = []
                    for r in range(NREP):
                        rng = np.random.default_rng([rng0 + r, H, len(sn)])
                        vals = []
                        for p, kk in k.items():
                            v = byp[p]
                            vals.append(v[rng.choice(len(v), size=min(int(kk), len(v)), replace=False)])
                        reps.append(float(np.concatenate(vals).mean()) if vals else np.nan)
                    reps = np.array(reps)
                    cell[tag]["同月隨機"] = {"真 X1 平均": real, "隨機平均的中位": float(np.nanmedian(reps)), "p95": float(np.nanpercentile(reps, 95)),
                                           "p（隨機 ≥ 真）": float(np.mean(reps >= real))}
                # G3 − C1 同月配對
                a3 = G[g3.fillna(False)].groupby("period")[f"ret{H}"].mean(); ac = G[c1.fillna(False)].groupby("period")[f"ret{H}"].mean()
                dd = (a3 - ac).dropna()
                if len(dd) >= 2:
                    eff = max(1, len(dd) // max(1, H // 20)); se = dd.std(ddof=1) / np.sqrt(eff)
                    lo_, hi_ = dd.mean() - 1.96 * se, dd.mean() + 1.96 * se
                    cell["G3 − C1 同月配對"] = {"月數": int(len(dd)), "有效月數": int(eff), "mean": float(dd.mean()), "lo": float(lo_), "hi": float(hi_),
                                              "判定": "分不出" if lo_ <= 0 <= hi_ else ("好" if dd.mean() > 0 else "差")}
                # 下市月營收下界（照 P4）
                miss = G[G["rev_hi24"].isna()]
                bd = {"缺營收列": int(len(miss)), "其中已下市": int(miss["delisted"].sum()), "檔數": int(miss["stock_id"].nunique())}
                for tag, m in (("G1", g1), ("G3", g3)):
                    base = G[m.fillna(False)]
                    add = miss if tag == "G1" else miss[miss["bull"] == True]
                    for v, lab in ((-1.0, "−100％"), (0.0, "0％")):
                        x = np.r_[base["X1"].to_numpy(float), v - add["b1"].to_numpy(float)]
                        gg = np.r_[base["period"].to_numpy(), add["period"].to_numpy()]
                        bd[f"{tag} 下界 {lab}（X1 甲）"] = judge(x, gg)
                        bd[f"{tag} 下界 {lab}（X1 乙）"] = judge(x - COST, gg)
                    bd[f"{tag} 加入列"] = int(len(add))
                cell["下市月營收下界"] = bd
                S["結果"][f"{sn}｜H{H}"] = cell
                log(f"[{sn} H{H}] G1 n {cell['G1']['n']} X1 {cell['G1']['X1 甲互抵'].get('mean', np.nan):+.3%} {cell['G1']['X1 甲互抵'].get('判定')}／"
                    f"X2 {cell['G1']['X2 甲互抵'].get('mean', np.nan):+.3%} {cell['G1']['X2 甲互抵'].get('判定')}／X2−成本 {cell['G1']['X2 乙對成本'].get('判定')}｜"
                    f"G3 n {cell['G3']['n']} X2 {cell['G3']['X2 甲互抵'].get('mean', np.nan):+.3%} {cell['G3']['X2 甲互抵'].get('判定')}／X2−成本 {cell['G3']['X2 乙對成本'].get('判定')}｜"
                    f"G3−C1 {cell.get('G3 − C1 同月配對', {}).get('mean', np.nan):+.3%} {cell.get('G3 − C1 同月配對', {}).get('判定')}")
    conf = [S["結果"][f"確認 2021～2026｜H{H}"] for H in HS]
    for tag in ("G1", "G3"):
        S[f"穩_{tag}（確認段四個 H × 兩口徑 × 基準② 同結果）"] = len({c[tag][k]["結果"] for c in conf for k in ("X2 甲互抵", "X2 乙對成本")}) == 1
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=lambda o_: o_.item() if hasattr(o_, "item") else str(o_))
    log(f"[完] {time.time() - T0:.0f}s")


if __name__ == "__main__":
    main()
