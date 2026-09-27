# -*- coding: utf-8 -*-
"""researchYLretest 第一批的獨立查核（⛔ 不 import researchYLretest）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchYLretest_check.py [--n 3]

① 從 b1_seeds.csv 自己算各格中位、比值、標籤（0050 同窗自己算）、④ 配對差 CI ⇒ 對 summary.json
② 停止交易股：自己用 D.load_stock 找「最後有效收盤 ＜ 主窗尾、之後沒有成交」⇒ 檔數對 summary
③ 假訊號：照檔頭寫的抽樣規格自己重建第 0～n−1 次的假訊號列（relvol、H60 出場用自己寫的迴圈），自己呼叫引擎 ⇒ 年化／回落 對 b1_fake.csv；
   並驗每筆假訊號與對應真訊號同月、當天有 K 棒
④ 219 取最好估計：從 b1_fake.csv 自己算 F(1.124)、K＝219／17 的百分位

第二批：researchYLretest_check.py --part b2 [--n 2]（見 main2 的說明）⇒ check_b2.json
"""
from __future__ import annotations
import argparse, json, math, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import rerun17 as RR
RR.use_snapshot()
from backtest import data as D
from backtest import research11 as R
from backtest import universe_gate as UG
OUT = os.path.expanduser("~/tw-p17/backtest/resultsYLretest")
HERE_ = os.path.expanduser("~/tw-p17/backtest")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=3); a = ap.parse_args()
    errs = []; info = {}
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    Sd = pd.read_csv(os.path.join(OUT, "b1_seeds.csv"), float_precision="round_trip"); FK = pd.read_csv(os.path.join(OUT, "b1_fake.csv"), float_precision="round_trip")
    cal = D.load_calendar(); w0, w1 = RR.win_bounds(cal); bench = RR.load_bench(cal)
    for k, g in Sd.groupby("key"):
        c, m = float(g["cagr"].median()), float(g["mdd"].median())
        ws = w0 + int(k.split("+")[1]) if "起點+" in k else w0
        b = RR.bench_row(cal, bench, ws, w1 + 1); r50 = b["cagr"] / abs(b["mdd"])
        lab = "合格" if (c > b["cagr"] and c / abs(m) >= r50) else ("另列" if c > b["cagr"] else "不合格")
        x = S["格"][k]
        if abs(x["年化中位"] - c) > 1e-15 or abs(x["回落中位"] - m) > 1e-15 or x["標籤"] != lab:
            errs.append(f"格 {k}")
    on = Sd[Sd["key"] == "#13_開"].set_index("r"); s14 = Sd[Sd["key"] == "#14_開"].set_index("r")
    d = (on["cagr"] - s14["cagr"]).to_numpy(); ci = [d.mean() - 1.96 * d.std(ddof=1) / math.sqrt(len(d)), d.mean() + 1.96 * d.std(ddof=1) / math.sqrt(len(d))]
    if max(abs(ci[0] - S["④relvol減隨機"]["cagr"]["CI"][0]), abs(ci[1] - S["④relvol減隨機"]["cagr"]["CI"][1])) > 1e-12:
        errs.append("④ CI")
    # ② 停止交易股
    U = D.load_universe(); U = U[U["stock_id"].isin(set(UG.gate3(pd.read_csv(os.path.join(RR.H2D, "meta", "stocks.csv"), dtype=str))["stock_id"]))]
    mk = U.set_index("stock_id")["market"]; n_stop = 0; last = {}
    for s in sorted(U["stock_id"]):
        st = D.load_stock(s, mk[s], cal)
        if st is None:
            continue
        v = np.flatnonzero(np.isfinite(st.df["close"].to_numpy(float)))
        if len(v):
            last[s] = int(v[-1])
            n_stop += int(v[-1] < w1)
    if n_stop != S["停止交易股（母體、主窗內）"]:
        errs.append(f"② 停止交易股 {n_stop} vs {S['停止交易股（母體、主窗內）']}")
    info["停止交易股"] = n_stop
    # ③ 假訊號重建
    RR.setup_and(cal, os.path.join(RR.OUT, "sig_edc6f", "and_signals.csv.gz"), "branch", lambda x: None)
    G = RR._G; AND = G["AND"]; e = AND["entry_pos"].to_numpy()
    real = AND[(e >= w0) & (e <= w1)]; real = real[real["xpos_H60"] >= 0]
    mon = np.array([str(x)[:7] for x in cal])
    closes, opens = RR.load_prices(sorted(set(U["stock_id"])), cal, mk, "branch")
    for s_ in G["closes"]:
        closes[s_] = G["closes"][s_]; opens[s_] = G["opens"][s_]
    bars = {}; alive = {}
    for s_ in sorted(closes):
        B = R.load_bars(s_, mk.get(s_, "twse"), cal)
        if B is None:
            continue
        bars[s_] = B
        for dd in B["idx"]:
            alive.setdefault(int(dd), []).append(s_)
    SF = {s_: L for s_, L in last.items() if L < w1 and s_ in closes}
    for i in range(a.n):
        rng = np.random.default_rng([20260927, i]); rows = []
        for m_ in mon[real["pos"].to_numpy(int)]:
            ds = [d_ for d_ in range(len(cal)) if mon[d_] == m_]
            for _ in range(50):
                d_ = ds[int(rng.integers(len(ds)))]
                pool = alive.get(d_)
                if not pool:
                    continue
                sid = pool[int(rng.integers(len(pool)))]
                B = bars[sid]; idx = B["idx"]
                k = int(np.searchsorted(idx, d_))
                if k + 1 >= len(idx):
                    continue
                if int(idx[k]) != d_ or mon[d_] != m_:
                    errs.append(f"③ 第 {i} 次 {sid} 日期不對")
                amt = B["amt"]
                if k >= 60:
                    w = [x for x in amt[k - 60:k] if math.isfinite(x)]
                    med = float(np.median(w)) if w else float("nan")
                    rel = float(amt[k]) / med if med > 0 and math.isfinite(amt[k]) else float("nan")
                else:
                    rel = float("nan")
                nb = B["next_bad"][max(0, k - 20)]; ex = k + 60 - 1 + 1       # 進場 k＋1、持有 60 根 ⇒ 出場根 k＋60
                if nb > k and ex < len(B["c"]) and ex < nb:
                    xp, g = int(idx[ex]), float(B["c"][ex] / B["o"][k + 1] - 1)
                else:
                    xp, g = -1, float("nan")
                rows.append((sid, k, d_, int(idx[k + 1]), xp, g, rel))
                break
        F = pd.DataFrame(rows, columns=["sid", "k", "pos", "entry_pos", "xpos_H60", "g_H60", "relvol"]).drop_duplicates(["sid", "entry_pos"])
        F = F[(F["entry_pos"] >= w0) & (F["entry_pos"] <= w1)].reset_index(drop=True)
        s = R.simulate_mtm(F, "H60", 20, np.random.default_rng(7000 + i), closes, opens, len(cal), return_equity=True, log=[], d_max=None,
                           pick="relvol", queue_days=0, stop_force=SF)
        c, m, _ = RR.win_metrics(s["equity"], s["first"], s["end"], w0, w1)
        ref = FK[FK["i"] == i].iloc[0]
        if repr(float(c)) != repr(float(ref["cagr"])) or repr(float(m)) != repr(float(ref["mdd"])):
            errs.append(f"③ 第 {i} 次：自己 {c}／{m} vs 檔 {ref['cagr']}／{ref['mdd']}")
    info["假訊號重建次數"] = a.n
    # ④ 百分位
    Fc = float((FK["ratio"] <= 1.124).mean()); E_ = S["②假訊號"]["219取最好_估計"]
    if abs(Fc - E_["F(1.124)"]) > 1e-15 or abs(Fc ** 219 - E_["K=219 百分位"]) > 1e-12 or abs(Fc ** 17 - E_["K=17 百分位"]) > 1e-12:
        errs.append("④ 百分位")
    info["錯誤數"] = len(errs)
    print(json.dumps(info, ensure_ascii=False))
    for e_ in errs[:20]:
        print("  ⛔", e_)
    json.dump({"info": info, "errors": errs}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("查核：" + ("全過" if not errs else f"⛔ {len(errs)} 項不過"))



def main2(a):
    """第二批查核（⛔ 不 import researchYLretest）：
    ⑤ 自己數 219 表中以 AND 為底的格（63）與不重複設定（44）；從 b2_rand219.csv 自己算每顆最大比值的百分位、各設定中位、同尺度自助抽樣；
       交叉：P1|N20|d=None 隨機分數那一組 ＝ 第一批 #14_開（b1_seeds.csv）逐位元（同引擎、同種子 7000＋r、同 stop_force）
    ⑥ 自己用 merge_asof 找「下市股、45 日內沒有營收面板」的 S 列 ⇒ 列數／檔數；自己組訊號集、自己算 relvol、自己呼叫引擎跑 −100％／0％ 下界前 n 顆
       ⇒ 對 b2_bound_seeds.csv；並從 b2_bound_seeds.csv 自己算中位與標籤
    ⑦⑧ 從 b2_early_seeds.csv 自己算中位與標籤（0050 用 summary 存的早年同窗值）；關的那格 ＝ resultsV/body_seeds.csv.gz #13 逐位元（主版、剔轉上市版）
    """
    errs = []; info = {}
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    rp = dict(float_precision="round_trip")
    # ⑤
    T = pd.read_csv(os.path.join(HERE_, "resultsN219", "table219.csv"))
    n63 = 0; cfg = set()
    for fam, cell in zip(T["族"], T["格"]):
        p_ = cell.split("｜")
        if fam in ("PREREG10／研究十三", "PREREG11／研究十三b") and p_[0] == "AND":
            n63 += 1; cfg.add(("P10", p_[1], p_[2], p_[3]))
        elif fam == "P1" and p_[0] == "AND":
            n63 += 1; cfg.add(("P1", p_[1], p_[2]))
        elif fam == "P3 乙臂（閒置放 0050）":
            n63 += 1; cfg.add(("P3B", p_[1], p_[2]))
    R5 = S["⑤219隨機分數"]
    info["⑤ 63 格／不重複設定（自數）"] = [n63, len(cfg)]
    if n63 != R5["63 格"] or len(cfg) != R5["不重複設定"]:
        errs.append(f"⑤ 格數 {n63}／{len(cfg)} vs {R5['63 格']}／{R5['不重複設定']}")
    RND = pd.read_csv(os.path.join(OUT, "b2_rand219.csv"), **rp)
    if RND["設定"].nunique() != len(cfg) or RND.groupby("設定")["r"].nunique().min() != RND["r"].nunique():
        errs.append("⑤ 設定×種子 不齊")
    mx = (RND["cagr"] / RND["mdd"].abs()).groupby(RND["r"]).max()
    if abs(float((mx <= 1.124).mean()) - R5["1.124 的百分位（最大值 ≤ 1.124 的比例）"]) > 1e-15 or abs(float(mx.median()) - R5["每顆最大比值_中位"]) > 1e-12:
        errs.append("⑤ 最大值分佈")
    per = {}
    for k, g in RND.groupby("設定"):
        per[k] = float(g["cagr"].median()) / abs(float(g["mdd"].median()))
    kbest = max(per, key=per.get)
    if abs(per[kbest] - R5["各設定 200 顆中位比值_最大"]) > 1e-12 or kbest != R5["各設定 200 顆中位比值_最大的設定"] or \
            sum(v >= 1.124 for v in per.values()) != R5["各設定 200 顆中位比值 ≥ 1.124 的設定數"]:
        errs.append("⑤ 各設定中位")
    keys = sorted(RND["設定"].unique())
    Cm = RND.pivot(index="r", columns="設定", values="cagr")[keys].to_numpy(float)
    Mm = RND.pivot(index="r", columns="設定", values="mdd")[keys].to_numpy(float)
    rb = np.random.default_rng(20260928); bs = np.empty(2000)
    for t in range(2000):
        ix = rb.integers(0, Cm.shape[0], Cm.shape[0])
        bs[t] = np.max(np.median(Cm[ix], axis=0) / np.abs(np.median(Mm[ix], axis=0)))
    if abs(float((bs <= 1.124).mean()) - R5["同尺度_1.124 的百分位"]) > 1e-15 or abs(float(np.median(bs)) - R5["同尺度_最大中位比值_中位"]) > 1e-12:
        errs.append("⑤ 同尺度自助抽樣")
    info["⑤ 同尺度百分位（自算）"] = float((bs <= 1.124).mean())
    b1s = pd.read_csv(os.path.join(OUT, "b1_seeds.csv"), **rp)
    s14 = b1s[b1s["key"] == "#14_開"].set_index("r")
    x14 = RND[RND["設定"] == "P1|reg=False|N20|H60|d=None"].set_index("r")
    rr_ = sorted(set(s14.index) & set(x14.index))
    nd = sum(repr(float(s14.at[r, "cagr"])) != repr(float(x14.at[r, "cagr"])) or repr(float(s14.at[r, "mdd"])) != repr(float(x14.at[r, "mdd"])) for r in rr_)
    info["⑤ P1|N20|d=inf 隨機 ＝ #14_開 逐位元（顆數／不同）"] = [len(rr_), nd]
    if nd or not rr_:
        errs.append(f"⑤ 與 #14_開 不同 {nd} 顆")
    # ⑥
    cal = D.load_calendar(); w0, w1 = RR.win_bounds(cal)
    RR.setup_and(cal, os.path.join(RR.OUT, "sig_edc6f", "and_signals.csv.gz"), "branch", lambda x: None)
    G = RR._G; AND = G["AND"]; e = AND["entry_pos"].to_numpy()
    sig = AND[(e >= w0) & (e <= w1)].reset_index(drop=True)
    Ss = pd.read_csv(os.path.join(RR.OUT, "sig_edc6f", "signals_S.csv.gz"), dtype={"sid": str},
                     usecols=["sid", "k", "pos", "entry_pos", "month", "g_H60", "xpos_H60"])
    dls = set(pd.read_csv(os.path.join(RR.H2D, "meta", "delisted.csv"), dtype=str)["stock_id"])
    PR = pd.read_csv(os.path.join(RR.OUT, "sig_edc6f", "panel_rev.csv.gz"), dtype={"stock_id": str}, usecols=["stock_id", "signal_pos"])
    W = Ss[(Ss["entry_pos"] >= w0) & (Ss["entry_pos"] <= w1) & Ss["sid"].isin(dls) & (Ss["xpos_H60"] >= 0)].copy()
    W["_o"] = np.arange(len(W)); W["pos"] = W["pos"].astype(np.int64)
    P2 = PR.rename(columns={"stock_id": "sid"}).astype({"signal_pos": np.int64}).sort_values("signal_pos")
    L_ = pd.merge_asof(W.sort_values("pos"), P2, left_on="pos", right_on="signal_pos", by="sid", direction="backward")
    miss = L_[~((L_["pos"] - L_["signal_pos"]) <= 45)].sort_values("_o").drop(columns=["_o", "signal_pos"]).reset_index(drop=True)
    R6 = S["⑥下市月營收"]
    info["⑥ 加進來的列／檔數（自算）"] = [len(miss), int(miss["sid"].nunique())]
    if len(miss) != R6["加進來的列"] or miss["sid"].nunique() != R6["檔數"]:
        errs.append(f"⑥ 列數 {len(miss)}／{miss['sid'].nunique()} vs {R6['加進來的列']}／{R6['檔數']}")
    U = D.load_universe(); U = U[U["stock_id"].isin(set(UG.gate3(pd.read_csv(os.path.join(RR.H2D, "meta", "stocks.csv"), dtype=str))["stock_id"]))]
    mk = U.set_index("stock_id")["market"]
    rel = []
    for s_, k in zip(miss["sid"], miss["k"].astype(int)):
        B = R.load_bars(s_, mk.get(s_, "twse"), cal); amt = B["amt"]
        w = [x for x in amt[k - 60:k] if math.isfinite(x)] if k >= 60 else []
        md = float(np.median(w)) if w else float("nan")
        rel.append(float(amt[k]) / md if (md > 0 and math.isfinite(amt[k])) else float("nan"))
    miss["relvol"] = rel
    closes, opens = RR.load_prices(sorted(set(G["closes"]) | set(miss["sid"])), cal, mk, "branch")
    for s_ in G["closes"]:
        closes[s_] = G["closes"][s_]; opens[s_] = G["opens"][s_]
    last = {}
    for s_ in sorted(closes):
        st = D.load_stock(s_, mk.get(s_, "twse"), cal)
        v = np.flatnonzero(np.isfinite(st.df["close"].to_numpy(float))) if st is not None else []
        if len(v):
            last[s_] = int(v[-1])
    msid = set(miss["sid"])
    SF = {s_: L for s_, L in last.items() if L < w1 and s_ not in msid}
    BS = pd.read_csv(os.path.join(OUT, "b2_bound_seeds.csv"), **rp)
    bench = RR.load_bench(cal); b = RR.bench_row(cal, bench, w0, w1 + 1); r50 = b["cagr"] / abs(b["mdd"])
    for tag, v in (("下界_−100％", -1.0), ("下界_0％", 0.0)):
        g = BS[BS["tag"] == tag]
        c, m = float(g["cagr"].median()), float(g["mdd"].median())
        lab = "合格" if (c > b["cagr"] and c / abs(m) >= r50) else ("另列" if c > b["cagr"] else "不合格")
        if abs(c - R6[tag]["年化中位"]) > 1e-15 or abs(m - R6[tag]["回落中位"]) > 1e-15 or lab != R6[tag]["標籤"]:
            errs.append(f"⑥ {tag} 中位／標籤")
        add = miss.copy(); add["g_H60"] = v
        sg = pd.concat([sig, add[[c_ for c_ in sig.columns if c_ in add.columns]]], ignore_index=True)
        for r in range(a.n):
            s = R.simulate_mtm(sg, "H60", 20, np.random.default_rng(7000 + r), closes, opens, len(cal), return_equity=True, log=[], d_max=None,
                               pick="relvol", queue_days=0, stop_force=SF)
            c1, m1, _ = RR.win_metrics(s["equity"], s["first"], s["end"], w0, w1)
            ref = g[g["r"] == r].iloc[0]
            if repr(float(c1)) != repr(float(ref["cagr"])) or repr(float(m1)) != repr(float(ref["mdd"])):
                errs.append(f"⑥ {tag} 第 {r} 顆：自己 {c1}／{m1} vs 檔 {ref['cagr']}／{ref['mdd']}")
    info["⑥ 引擎重跑顆數（每個下界）"] = a.n
    # ⑦⑧
    E_ = S["⑦⑧早年"]; ES = pd.read_csv(os.path.join(OUT, "b2_early_seeds.csv"), **rp)
    ref = pd.read_csv(os.path.join(HERE_, "resultsV", "body_seeds.csv.gz"), **rp)
    for k, g in ES.groupby("key"):
        var = k.split("|")[0]; b = E_[f"{var}_0050"]; r50 = b["cagr"] / abs(b["mdd"])
        c, m = float(g["cagr"].median()), float(g["mdd"].median())
        lab = "合格" if (c > b["cagr"] and c / abs(m) >= r50) else ("另列" if c > b["cagr"] else "不合格")
        if abs(c - E_[k]["年化中位"]) > 1e-15 or abs(m - E_[k]["回落中位"]) > 1e-15 or lab != E_[k]["標籤"]:
            errs.append(f"⑦⑧ {k}")
        if "|關|" in k:
            rr = ref[(ref["variant"] == var) & (ref["cell"] == 13)].set_index("r"); g = g.set_index("r")
            nd = sum(repr(float(g.at[r, "cagr"])) != repr(float(rr.at[r, "cagr"])) or repr(float(g.at[r, "mdd"])) != repr(float(rr.at[r, "mdd"]))
                     for r in g.index)
            info[f"⑦ {var} 關＝resultsV #13（顆數／不同）"] = [len(g), nd]
            if nd or len(g) != len(rr):
                errs.append(f"⑦ {var} 關 ≠ resultsV #13：{nd}")
    info["⑦⑧ 格數"] = int(ES["key"].nunique())
    info["錯誤數"] = len(errs)
    print(json.dumps(info, ensure_ascii=False))
    for e_ in errs[:20]:
        print("  ⛔", e_)
    json.dump({"info": info, "errors": errs}, open(os.path.join(OUT, "check_b2.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("第二批查核：" + ("全過" if not errs else f"⛔ {len(errs)} 項不過"))


if __name__ == "__main__":
    if "--part" in sys.argv and sys.argv[sys.argv.index("--part") + 1] == "b2":
        ap = argparse.ArgumentParser(); ap.add_argument("--part"); ap.add_argument("--n", type=int, default=2); main2(ap.parse_args())
    else:
        main()
