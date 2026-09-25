# -*- coding: utf-8 -*-
"""PREREG型態全量 獨立查核（⛔ 不 import researchPatAll、researchPatAll_freq、patterns_all、research11 任何一行；
只 import backtest.data（讀快照、斷點規則）、backtest.tradability（漲跌停旗標、下市狀態）、backtest.universe_gate（gate3））。
body 跑完後才用：

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchPatAll_check.py [--dir backtest/resultsPatAll/body] [--sample 20]

C1 從逐筆檔（events/events_<vid>.csv.gz）重算全部判定格（180）與 H120 描述：逐筆 X ＝ R − 對照平均、dX ＝ d·X 重算；
   n、d×X̄、中位、勝率、最差、p10／p90；CR0 分群 SE（自己寫：Σ_g(Σ_{i∈g}(x_i − x̄))² 開根號 ÷ n；H20 曆月、H60 (T−窗起點)//60）、
   95% CI、Bonferroni（z 用二分法解 erfc(z/√2)＝0.05／180，自己算）、非重疊 CI、n_eff、出口、結果；只配 r10 版、未配對版的平均；
   ⇒ 與 cells.csv 逐格比（數值差 < 1e-12、標籤相同）；族 a、b 重數；每格逐筆列數 ＝ cells.csv 保留 ＝ 頻率階段 freq.csv 保留。
C2 假訊號臂：由 fake_acc.npz 逐群 (n, Σ) 重算 30 次 × 兩版 ⇒ 每格 x／30、每次全族過關格數與最大值 ⇒ 與 cells.csv、summary.json 比。
C3 抽 --sample 筆（種子 20260930：先不放回抽 20 個判定格、每格抽 1 筆有對照的保留事件）：從快照【原始價】stocks/<sid>.csv
   ＋【還原因子】adj/<sid>.csv（F(d) ＝ 事件日嚴格大於 d 的第一列 cum_factor；沒有 ⇒ 1）逐筆手算
   R ＝ 原始收盤(j)·F(j) ÷ 原始開盤(T＋1)·F(T＋1) − 1（j ＝ ≤ T＋H 最後一個有成交日）⇒ 與逐筆檔 R 比。
C4 同一批：全市場逐檔獨立重建對照組（十分位 ＝ pd.qcut(rank(method="first"), 10)；當天原始偵測取自頻率階段已提交的事件檔（任何狀態）；
   T＋1 可成交（有成交、開盤非缺、非開盤漲停／跌停）；硬斷點：區間內價格斷點（data.breakpoints 的 price／price+gap）或
   連續 ≥5 個交易日沒成交且 5 天都在區間內（下市者最後成交後不算）——逐日掃，⛔ 不用累加和）⇒ 對照平均、對照數、只配 r10 版 ⇒ 與逐筆檔比。
C5 fixture：T＋1 以後價格固定的合成市場 ⇒ 用 C4 同一支函式重建 ⇒ X ＝ 0（主版、只配 r10 版、價格結構版）。
結果寫 check.json，並把「十二、獨立查核」一節寫進 PATALL_REPORT.md（有舊的就換掉）。
"""
from __future__ import annotations
import os, sys, json, gzip, math
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
SHA = "edc6f8002fed8803795e3486ad57db513f7e9f65"
SNAP = os.path.expanduser("~/h2data/{}/data".format(SHA))
from backtest import data as D
D.DATA = SNAP
from backtest import tradability as TR
from backtest import universe_gate as UG

W0, W1 = "2017-03-02", "2026-08-24"
FREQ = "backtest/resultsPatAll"
N_FAM = 180
TOL = 1e-12


def z_bonf(alpha):
    lo, hi = 0.0, 10.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if math.erfc(mid / math.sqrt(2)) > alpha:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


ZB = z_bonf(0.05 / N_FAM)


def cr0(x, g):
    x = np.asarray(x, float); n = len(x); m = float(x.mean())
    acc = {}
    for xi, gi in zip(x, g):
        acc[gi] = acc.get(gi, 0.0) + (xi - m)
    return m, math.sqrt(sum(v * v for v in acc.values())) / n, len(acc)


def verdict(m, se, ne):
    if ne < 30:
        return "出口①", "樣本不足以分辨"
    ex = "出口②" if ne < 100 else "出口③"
    lo, hi = m - 1.96 * se, m + 1.96 * se
    if lo <= 0 <= hi:
        return ex, "結果①"
    return ex, ("結果②" if m > 0 else "結果③")


def close(a, b, tol=TOL):
    if a is None or b is None:
        return a is None and b is None
    a = float(a); b = float(b)
    if not (np.isfinite(a) and np.isfinite(b)):
        return np.isnan(a) and np.isnan(b)
    return abs(a - b) <= tol


# ═════════════ C4／C5 的獨立重建 ═════════════
def load_all(sids, mkts, cal, off):
    ST = {}
    for s, m in zip(sids, mkts):
        st = D.load_stock(s, m, cal)
        if st is None:
            continue
        df = st.df
        o = df["open"].to_numpy(float); c = df["close"].to_numpy(float)
        valid = np.isfinite(c)
        if not valid.any():
            continue
        tb = TR.one(s, cal)
        ds = TR.delist_status({s: tb}, cal, official=off).get(s)
        last = ds["last"] if (ds is not None and ds["status"].startswith("delisted")) else None
        pbp = set(b["pos"] for b in D.breakpoints(df, st.event_dates) if b["rule"] in ("price", "price+gap"))
        ST[s] = {"o": o, "c": c, "valid": valid, "bars": np.flatnonzero(valid), "cff": pd.Series(c).ffill().to_numpy(),
                 "trd": tb["trd"], "up_o": tb["up_o"], "dn_o": tb["dn_o"], "pb": pbp, "last": last}
    return ST


def has_break(P, a, b):
    """[a, b] 內：價格斷點日，或連續 ≥5 個缺日且 5 天都在 [a, b]（下市者最後成交後的缺日不算）。逐日掃。"""
    for q in range(a, b + 1):
        if q in P["pb"]:
            return True
    run = 0
    for q in range(a, b + 1):
        miss = (not P["valid"][q]) and (P["last"] is None or q <= P["last"])
        run = run + 1 if miss else 0
        if run >= 5:
            return True
    return False


def ret(P, T, H):
    q = T + 1
    if not (P["valid"][q] and np.isfinite(P["o"][q]) and P["o"][q] > 0):
        return np.nan
    return P["cff"][T + H] / P["o"][q] - 1.0


def tradable(P, T):
    q = T + 1
    return bool(P["trd"][q] and np.isfinite(P["o"][q]) and not P["up_o"][q] and not P["dn_o"][q])


def dec_of(vals):
    """vals：{sid: v}（已去缺值）⇒ {sid: 十分位}（pd.qcut(rank first)）。"""
    s = pd.Series(vals)
    if len(s) < 10:
        return {}
    q = pd.qcut(s.rank(method="first"), 10, labels=False)
    return q.to_dict()


def rebuild(ST, ev, raw, fam, k, pre, anchor_n):
    """ev：{sid, T, first, H}；raw：當天有原始偵測的 sid 集合 ⇒ (主對照平均, 數, r10 版平均, 數)。"""
    T, H, f, e = ev["T"], ev["H"], ev["first"], ev["sid"]
    if fam == "K":
        r10, prd, fk = {}, {}, {}
        for s, P in ST.items():
            if not P["valid"][T]:
                continue
            b = int(np.searchsorted(P["bars"], T))
            if b - k - 10 < 0:
                continue
            cb = P["c"][P["bars"]]
            x = cb[b - k] / cb[b - k - 10] - 1.0; y = cb[b] / cb[b - k] - 1.0
            if np.isfinite(x) and np.isfinite(y):
                r10[s] = x; prd[s] = y; fk[s] = int(P["bars"][b - k + 1])
        d1 = dec_of(r10); d2 = dec_of(prd)
        xs, xs10 = [], []
        for s in r10:
            if s == e or s in raw or s not in d1:
                continue
            sg = np.sign(r10[s])
            if (pre == "升" and sg != 1) or (pre == "降" and sg != -1) or (pre == "無" and sg == 0):
                continue
            P = ST[s]
            if not tradable(P, T) or has_break(P, fk[s], T + H):
                continue
            R = ret(P, T, H)
            if not np.isfinite(R):
                continue
            if d1[s] == d1[e]:
                xs10.append(R)
                if d2[s] == d2[e]:
                    xs.append(R)
        return (float(np.mean(xs)) if xs else np.nan), len(xs), (float(np.mean(xs10)) if xs10 else np.nan), len(xs10)
    A = {}
    for s, P in ST.items():
        if not P["valid"][f]:
            continue
        b = int(np.searchsorted(P["bars"], f))
        if b - anchor_n - 1 < 0:
            continue
        cb = P["c"][P["bars"]]
        x = cb[b - 1] / cb[b - 1 - anchor_n] - 1.0
        if np.isfinite(x):
            A[s] = x
    dA = dec_of(A)
    xs = []
    for s in A:
        if s == e or s in raw or s not in dA or dA[s] != dA[e]:
            continue
        P = ST[s]
        if not P["valid"][T] or not tradable(P, T) or has_break(P, f, T + H):
            continue
        R = ret(P, T, H)
        if np.isfinite(R):
            xs.append(R)
    return (float(np.mean(xs)) if xs else np.nan), len(xs), np.nan, -1


def fixture_zero():
    """T＋1 以後價格固定 ⇒ 所有 R ＝ 0 ⇒ X ＝ 0。"""
    rng = np.random.default_rng(3)
    n = 120; T = 70; H = 20
    ST = {}
    for j in range(306):                               # 300 條隨機路徑＋6 條與 S00 同路徑（保證事件的格子有人）
        if j == 0 or j >= 300:
            rng0 = np.random.default_rng(99)
            c = 10 * np.exp(np.cumsum(rng0.normal(0, 0.03, n))); c[T + 1:] = c[T]
            o = c.copy(); o[:T + 1] = c[:T + 1] * np.exp(rng0.normal(0, 0.01, T + 1))
        else:
            c = 10 * np.exp(np.cumsum(rng.normal(0, 0.03, n)))
            c[T + 1:] = c[T]
            o = c.copy(); o[:T + 1] = c[:T + 1] * np.exp(rng.normal(0, 0.01, T + 1))
        ST["S{:02d}".format(j)] = {"o": o, "c": c, "valid": np.ones(n, bool), "bars": np.arange(n), "cff": c.copy(),
                                    "trd": np.ones(n, bool), "up_o": np.zeros(n, bool), "dn_o": np.zeros(n, bool), "pb": set(), "last": None}
    out = []
    for fam, k, pre, an in (("K", 1, "無", None), ("K", 3, "無", None), ("S", None, None, 60)):
        e = "S00"
        ev = {"sid": e, "T": T, "first": T - 5, "H": H}
        m1, n1, m10, n10 = rebuild(ST, ev, set(), fam, k, pre, an)
        R = ret(ST[e], T, H)
        out.append({"族": fam, "k": k, "R": R, "對照數": n1, "X": R - m1 if n1 > 0 else None, "X_r10": (R - m10) if n10 > 0 else None})
    ok = all(q["R"] == 0.0 and (q["X"] is None or q["X"] == 0.0) and (q["X_r10"] is None or q["X_r10"] == 0.0) for q in out) \
        and all(q["對照數"] > 0 for q in out)
    return ok, out


# ═════════════ 主 ═════════════
def main():
    argv = sys.argv
    DIR = argv[argv.index("--dir") + 1] if "--dir" in argv else "backtest/resultsPatAll/body"
    NS = int(argv[argv.index("--sample") + 1]) if "--sample" in argv else 20
    os.chdir(os.path.expanduser("~/tw-p17"))
    cal = D.load_calendar(); pos = {str(d.date()): i for i, d in enumerate(cal)}
    w0 = pos[W0]
    C = pd.read_csv(os.path.join(DIR, "cells.csv"), encoding="utf-8-sig", dtype={"vid": str})
    SUM = json.load(open(os.path.join(DIR, "summary.json"), encoding="utf-8"))
    FQ = pd.read_csv(os.path.join(FREQ, "freq.csv"), encoding="utf-8-sig", dtype={"vid": str}).set_index("vid")
    OUTJ = {"C1": {}, "C2": {}, "C3": [], "C4": [], "C5": None}
    bad = []
    # ── C1
    maxdiff = {"X": 0.0, "dX": 0.0}
    EV = {}
    for vid in C["vid"].unique():
        p = os.path.join(DIR, "events", "events_{}.csv.gz".format(vid))
        E = pd.read_csv(p, dtype={"sid": str}) if os.path.exists(p) else None
        EV[vid] = E
        for _, row in C[C["vid"] == vid].iterrows():
            H = int(row["H"]); key = "{}_H{}".format(vid, H)
            if row["身分"] not in ("判定格", "H120 描述"):
                if E is not None and (E["H"] == H).any():
                    bad.append(key + ":不可判定格卻有逐筆")
                continue
            k = E[E["H"] == H]
            chk = {"逐筆列數＝保留": len(k) == int(row["保留"]), "保留＝freq.csv": int(row["保留"]) == int(FQ.loc[vid, "保留_H{}".format(H)])}
            m = (k["配對"] == "有").to_numpy()
            R = k["R"].to_numpy(float); ctl = k["對照平均"].to_numpy(float); d = k["d"].to_numpy(float)
            x = R - ctl; dx = d * x
            maxdiff["X"] = max(maxdiff["X"], float(np.nanmax(np.abs(x[m] - k["X"].to_numpy(float)[m])) if m.any() else 0.0))
            maxdiff["dX"] = max(maxdiff["dX"], float(np.nanmax(np.abs(dx[m] - k["dX"].to_numpy(float)[m])) if m.any() else 0.0))
            chk["配對有＝X有限"] = bool((np.isfinite(x) == m).all())
            dx = dx[m]; Tp = np.array([pos[t] for t in k["T"].to_numpy()[m]])
            n = len(dx)
            chk["n"] = n == int(row["n"])
            if n:
                chk["d×X̄"] = close(dx.mean(), row["dX̄"]); chk["中位"] = close(np.median(dx), row["中位"])
                chk["勝率"] = close((dx > 0).mean(), row["勝率"]); chk["最差"] = close(dx.min(), row["最差"])
                chk["p10"] = close(np.percentile(dx, 10), row["p10"]); chk["p90"] = close(np.percentile(dx, 90), row["p90"])
            if H != 120 and n:
                g = [t[:7] for t in k["T"].to_numpy()[m]] if H == 20 else list((Tp - w0) // 60)
                mm, se, ng = cr0(dx, g)
                ne = min(n, ng); ex, rs = verdict(mm, se, ne)
                blk = (Tp - w0) // (20 if H == 20 else 60)
                bm = pd.Series(dx).groupby(blk).mean()
                se2 = float(bm.std(ddof=1) / math.sqrt(len(bm)))
                chk.update({"se": close(se, row["se"]), "CI": close(mm - 1.96 * se, row["lo"]) and close(mm + 1.96 * se, row["hi"]),
                            "Bonferroni": close(mm - ZB * se, row["bonf_lo"], 1e-9) and close(mm + ZB * se, row["bonf_hi"], 1e-9),
                            "Bonf不含0": bool((mm - ZB * se > 0) or (mm + ZB * se < 0)) == bool(row["bonf不含0"]),
                            "非重疊": close(mm - 1.96 * se2, row["lo_非重疊"]) and close(mm + 1.96 * se2, row["hi_非重疊"]),
                            "n_eff": ne == int(row["n_eff"]), "出口": ex == row["出口"], "結果": rs == row["結果"]})
                # 只配 r10、未配對
                if vid.startswith("K"):
                    m10 = (k["對照數_r10"] > 0).to_numpy()
                    v10 = (d * (R - k["對照平均_r10"].to_numpy(float)))[m10]
                    chk["只配r10平均"] = close(v10.mean(), row["只配r10_dX_平均"])
                vu = (d * k["X_未配對"].to_numpy(float))[m]
                chk["未配對平均"] = close(vu.mean(), row["未配對_dXu_平均"])
            OUTJ["C1"][key] = {kk: bool(vv) for kk, vv in chk.items()}
            bad += [key + ":" + kk for kk, vv in chk.items() if not vv]
    J = C[C["身分"] == "判定格"]
    a_ = int((J["結果"] == "結果②").sum()); b_ = int((J["結果"] == "結果③").sum())
    fam = SUM["族"]
    OUTJ["C1"]["族"] = {"判定格數": int(len(J)), "a": a_, "b": b_, "與summary同": a_ == fam["a_d方向過關"] and b_ == fam["b_反方向過關"] and len(J) == N_FAM}
    if not OUTJ["C1"]["族"]["與summary同"]:
        bad.append("族 a／b 或 N")
    OUTJ["C1"]["逐筆X與dX重算最大差"] = maxdiff
    if max(maxdiff.values()) > TOL:
        bad.append("逐筆 X／dX 重算")
    print("[C1] 判定格 {}、H120 描述 {}｜a＝{}、b＝{}｜逐筆重算最大差 {}｜不一致 {} 項".format(
        len(J), int((C["身分"] == "H120 描述").sum()), a_, b_, maxdiff, len(bad)), flush=True)
    # ── C2
    npz = np.load(os.path.join(DIR, "fake_acc.npz"))
    keys = [str(k_) for k_ in npz["keys"]]; ACC = npz["acc"]
    per = {0: np.zeros(30, int), 1: np.zeros(30, int)}
    c2bad = []
    for ki, key in enumerate(keys):
        vid, H = key.split("_"); H = int(H)
        row = C[(C["vid"] == vid) & (C["H"] == H)].iloc[0]
        for ver, vn in ((0, "新預設"), (1, "不排除")):
            x2 = 0
            for r in range(ACC.shape[1]):
                a = ACC[ki, r, ver]; nn, sm = a[:, 0], a[:, 1]; N = nn.sum()
                if N == 0:
                    continue
                mm = sm.sum() / N; se = math.sqrt(((sm - nn * mm) ** 2).sum()) / N
                rs = verdict(mm, se, int(min(N, (nn > 0).sum())))[1]
                if rs == "結果②":
                    x2 += 1; per[ver][r] += 1
            if x2 != int(row["假訊號_{}_x2".format(vn)]):
                c2bad.append("{}:{}".format(key, vn))
    okfam = per[0].tolist() == fam["假訊號_新預設_30次全族d方向過關格數"] and per[1].tolist() == fam["假訊號_不排除_30次"]
    OUTJ["C2"] = {"格數": len(keys), "x／30 不一致": c2bad, "每次全族過關格數（新預設）": per[0].tolist(), "最大": int(per[0].max()),
                  "不排除 最大": int(per[1].max()), "與summary同": bool(okfam)}
    bad += c2bad + ([] if okfam else ["假訊號全族格數"])
    if len(keys) != N_FAM:
        bad.append("假訊號格數 ≠ 180")
    print("[C2] 假訊號 {} 格｜每次全族過關格數 {}（最大 {}）｜與本體同 {}".format(len(keys), per[0].tolist(), int(per[0].max()), okfam and not c2bad), flush=True)
    # ── C3、C4：抽樣
    rng = np.random.default_rng(20260930)
    jl = J[["vid", "H"]].values.tolist()
    pick_cells = [jl[i] for i in rng.choice(len(jl), size=min(NS, len(jl)), replace=False)]
    picks = []
    for vid, H in pick_cells:
        E = EV[vid]; k = E[(E["H"] == int(H)) & (E["配對"] == "有")]
        r = k.iloc[int(rng.integers(0, len(k)))]
        picks.append({"vid": vid, "H": int(H), "sid": r["sid"], "market": r["market"], "T": r["T"], "first": r["first"], "d": int(r["d"]),
                      "R": float(r["R"]), "對照平均": float(r["對照平均"]), "對照數": int(r["對照數"]),
                      "對照平均_r10": float(r["對照平均_r10"]) if np.isfinite(r["對照平均_r10"]) else None,
                      "對照數_r10": int(r["對照數_r10"])})
    # C3 原始價＋還原因子
    c3max = 0.0
    for q in picks:
        raw = pd.read_csv(os.path.join(SNAP, "stocks", "{}.csv".format(q["sid"])), dtype={"date": str}, usecols=["date", "open", "high", "low", "close"])
        raw = raw.drop_duplicates("date").set_index("date")
        for c_ in ("open", "high", "low", "close"):
            raw[c_] = pd.to_numeric(raw[c_], errors="coerce")
        badr = (raw[["open", "high", "low", "close"]] <= 0).any(axis=1)          # 零價列視為整列缺（讀檔層同一條規則，自己再寫一次）
        raw.loc[badr, ["open", "high", "low", "close"]] = np.nan
        adj = os.path.join(SNAP, "adj", "{}.csv".format(q["sid"]))
        A = pd.read_csv(adj, dtype={"date": str}).sort_values("date") if os.path.exists(adj) else None
        def F(dstr):
            if A is None:
                return 1.0
            later = A[A["date"] > dstr]
            return float(later["cum_factor"].iloc[0]) if len(later) else 1.0
        T = pos[q["T"]]; d1 = str(cal[T + 1].date())
        o1 = float(raw.loc[d1, "open"])
        j = T + q["H"]
        while True:
            dj = str(cal[j].date())
            if dj in raw.index and np.isfinite(float(raw.loc[dj, "close"])):
                break
            j -= 1
        cj = float(raw.loc[dj, "close"])
        R = cj * F(dj) / (o1 * F(d1)) - 1.0
        diff = abs(R - q["R"]); c3max = max(c3max, diff)
        OUTJ["C3"].append({"vid": q["vid"], "H": q["H"], "sid": q["sid"], "T": q["T"], "T+1": d1, "出場日": dj, "原始開盤": o1, "F(T+1)": F(d1),
                           "原始收盤": cj, "F(出場)": F(dj), "手算R": R, "逐筆R": q["R"], "差": diff})
    if c3max > 1e-12:
        bad.append("C3 手算 R")
    print("[C3] {} 筆原始價＋還原因子手算 R｜最大差 {:.1e}".format(len(picks), c3max), flush=True)
    # C4 重建對照
    stocks = pd.read_csv(os.path.join(SNAP, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(stocks)
    if "--limit" in argv:                              # 只給除錯（對應本體 --limit）
        U = U.head(int(argv[argv.index("--limit") + 1]))
    off = TR.load_official()
    print("[C4] 逐檔讀 {:,} 檔（獨立讀檔）…".format(len(U)), flush=True)
    ST = load_all(list(U["stock_id"]), list(U["market"]), cal, off)
    DT = pd.read_csv(os.path.join(FREQ, "direction_table.csv"), encoding="utf-8-sig", dtype={"vid": str}).set_index("vid")
    rawcache = {}
    c4max = 0.0; c4n = True
    for q in picks:
        vid = q["vid"]
        if vid not in rawcache:
            fn = [f for f in os.listdir(FREQ) if f.startswith("events_{}_".format(vid))][0]
            R_ = pd.read_csv(os.path.join(FREQ, fn), dtype={"sid": str}, usecols=["sid", "T"])
            rawcache[vid] = R_
        R_ = rawcache[vid]
        raw = set(R_.loc[R_["T"] == q["T"], "sid"])
        T = pos[q["T"]]; f = pos[q["first"]]
        P = ST[q["sid"]]
        if vid.startswith("K"):
            k = int(np.searchsorted(P["bars"], T) - np.searchsorted(P["bars"], f) + 1)
            pre = str(DT.loc[vid, "登錄_事前"])
            m1, n1, m10, n10 = rebuild(ST, {"sid": q["sid"], "T": T, "first": f, "H": q["H"]}, raw, "K", k, pre, None)
        else:
            an = 20 if vid in ("S25", "S26", "S27") else 60
            m1, n1, m10, n10 = rebuild(ST, {"sid": q["sid"], "T": T, "first": f, "H": q["H"]}, raw, "S", None, None, an)
        d1 = abs(m1 - q["對照平均"])
        ok = n1 == q["對照數"] and d1 <= 1e-12
        if vid.startswith("K"):
            ok = ok and n10 == q["對照數_r10"] and abs(m10 - q["對照平均_r10"]) <= 1e-12
            c4max = max(c4max, abs(m10 - q["對照平均_r10"]))
        c4max = max(c4max, d1); c4n &= ok
        OUTJ["C4"].append({"vid": vid, "H": q["H"], "sid": q["sid"], "T": q["T"], "重建對照數": n1, "逐筆對照數": q["對照數"], "重建對照平均": m1,
                           "逐筆對照平均": q["對照平均"], "重建_r10數": n10, "逐筆_r10數": q["對照數_r10"], "同": bool(ok)})
    if not c4n:
        bad.append("C4 對照重建")
    print("[C4] {} 筆全市場獨立重建對照組｜對照數全同 {}｜平均最大差 {:.1e}".format(len(picks), c4n, c4max), flush=True)
    # C5
    ok5, det5 = fixture_zero()
    OUTJ["C5"] = {"過": ok5, "明細": det5}
    if not ok5:
        bad.append("C5 fixture")
    print("[C5] 0 報酬 fixture ⇒ X＝0：{}".format("過" if ok5 else "⛔"), flush=True)
    OUTJ["不一致"] = bad
    OUTJ["判"] = "✅ 全同" if not bad else "⛔ 有不一致"
    OUTJ["Bonferroni_z（二分法）"] = ZB
    json.dump(OUTJ, open(os.path.join(DIR, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    # 報告第十二節
    rp = os.path.join(DIR, "PATALL_REPORT.md")
    if os.path.exists(rp):
        txt = open(rp, encoding="utf-8").read().split("\n## 十二、獨立查核", 1)[0].rstrip("\n")
        L = ["", "## 十二、獨立查核（researchPatAll_check.py；⛔ 不 import 主程式）", "", "```",
             "C1 從逐筆檔重算：判定格 {} 格＋H120 描述 {} 格 ⇒ n、d×X̄、中位、勝率、最差、p10／p90、CR0 SE、95% CI、Bonferroni、非重疊 CI、n_eff、出口、結果、只配 r10、未配對 ⇒ {}".format(
                 len(J), int((C["身分"] == "H120 描述").sum()), "全同" if not [b for b in bad if not b.startswith(("C3", "C4", "C5", "假訊號"))] else "⛔ 見 check.json"),
             "   逐筆 X＝R−對照、dX＝d·X 重算最大差 {:.1e}／{:.1e}｜族 a＝{}、b＝{}（與本體同）｜保留＝逐筆列數＝freq.csv".format(maxdiff["X"], maxdiff["dX"], a_, b_),
             "C2 假訊號臂由逐群累加重算：180 格 x／30 {}｜每次全族過關格數 {}（最大 {}）".format("全同" if not c2bad else "⛔", per[0].tolist(), int(per[0].max())),
             "C3 {} 筆原始價＋還原因子手算 R：最大差 {:.1e}".format(len(picks), c3max),
             "C4 同 {} 筆全市場逐檔獨立重建對照組（qcut 十分位、事件檔的原始偵測、逐日斷點）：對照數 {}、平均最大差 {:.1e}".format(len(picks), "全同" if c4n else "⛔", c4max),
             "C5 T＋1 後價格固定的合成市場 ⇒ X＝0（K 主版、只配 r10、價格結構）：{}".format("過" if ok5 else "⛔"),
             "判：{}".format(OUTJ["判"]), "```", ""]
        open(rp, "w", encoding="utf-8").write(txt + "\n" + "\n".join(L))
    print("判：{}｜不一致 {}".format(OUTJ["判"], bad[:20]), flush=True)


if __name__ == "__main__":
    main()
