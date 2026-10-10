# -*- coding: utf-8 -*-
"""seq323／seq324 四件的抽樣查核（獨立寫法）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPRE5check TrendAll|RevPriceOK|PreFinRev|EPSqoq [--procs 2]

⭐ 寫法：⛔ 不呼叫 researchPRE5core／各件檔的訊號、母體、價格、引擎函式；從原始 csv（stocks／adj／meta／月營收／industry_pit／fs_hist）自讀自算：
  ① 價格：原始價 × Π（事件日嚴格晚於該日的 adj factor）；≤ 0 當缺；收盤 ffill
  ② 母體：meta/stocks.csv kind＝stock、market∈twse／tpex、名稱無 -DR、四碼首碼 1～9 非 91xx、至少一天板外上市櫃列；逐日列 market∈twse／tpex 且名稱不含 -創／-KY創
     （沒列的日子沿用前一列）；近 20 根有效 K 棒成交金額平均 ≥ 5,000 萬
  ③ 抽 6 個決策日（default_rng(20261011)）：獨立算候選集合、每筆出場日與毛報酬 ⇒ 與本體引擎輸入（~/pre5work/<件>_run.pkl 的 FB）逐筆比
  ④ 引擎：挑中格 r＝0 用獨立寫的逐日迴圈（10 槽、抽籤 default_rng(20261010)、停止交易強制出場、成本 0.585%）重算權益 ⇒ 與本體 r＝0 權益比（相對差 ≤ 1e−9）
  0 不同才算過；結果寫 backtest/results<件>/check.json
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import pickle
import re
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

H2D = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
WORK = os.path.expanduser("~/pre5work")
TW = sorted(glob.glob(os.path.expanduser("~/h2data/indrevpr_69e257c88206/data")))[0]
FS = os.path.expanduser("~/tw-p17/data/mops/fs_hist")
COST = 0.00585
W0, W1 = "2017-03-02", "2026-08-24"
BOARD = re.compile(r"-(?:KY)?創")
TOL = 1e-9
TIES = set()
_G = {}


def ok4(s):
    return isinstance(s, str) and len(s) == 4 and s.isdigit() and s[0] in "123456789" and not s.startswith("91")


def cal_of(data):
    c = pd.read_csv(os.path.join(data, "meta", "calendar_twse.csv"), dtype=str)
    return pd.DatetimeIndex(pd.to_datetime(c.iloc[:, 0]))


def stock_list(data):
    st = pd.read_csv(os.path.join(data, "meta", "stocks.csv"), dtype=str)
    st = st[(st["kind"] == "stock") & st["market"].isin(["twse", "tpex"]) & ~st["name"].fillna("").str.contains("-DR") & st["stock_id"].map(ok4)]
    return list(zip(st["stock_id"], st["market"]))


def _load(args):
    sid, mk = args
    data, cal = _G["data"], _G["cal"]; n = len(cal)
    p = os.path.join(data, "stocks", f"{sid}.csv")
    if not os.path.exists(p):
        return sid, None
    df = pd.read_csv(p, dtype=str).drop_duplicates("date")
    df["date"] = pd.to_datetime(df["date"]); df = df.set_index("date").sort_index()
    rowok = df["market"].isin(["twse", "tpex"]) & ~df["name"].fillna("").str.contains(BOARD)
    if not rowok.any():
        return sid, None
    num = {k: pd.to_numeric(df[k], errors="coerce") for k in ("open", "close", "amount")}
    for k in ("open", "close"):
        num[k] = num[k].where(num[k] > 0)
    fac = pd.Series(1.0, index=df.index)
    ap = os.path.join(data, "adj", f"{sid}.csv")
    if os.path.exists(ap):
        ad = pd.read_csv(ap, dtype=str)
        ev = sorted(zip(pd.to_datetime(ad["date"]), pd.to_numeric(ad["cum_factor"], errors="coerce")), reverse=True)
        for d, cf in ev:                      # 由晚到早：事件日之前的日子 ＝ 該事件列的 cum_factor（＝ 該列含之後所有因子連乘）
            if np.isfinite(cf):
                fac[fac.index < d] = cf
    o = (num["open"] * fac).reindex(cal).to_numpy(float); c0 = (num["close"] * fac).reindex(cal).to_numpy(float)
    rc = num["close"].reindex(cal).to_numpy(float); amt = num["amount"].reindex(cal).to_numpy(float)
    bar = np.isfinite(c0)
    c = pd.Series(c0).ffill().to_numpy()
    rv = rowok.astype(float).reindex(cal.union(rowok.index)).ffill().reindex(cal).to_numpy()
    pv = np.where(np.isnan(rv), True, rv > 0.5)
    idx = np.flatnonzero(bar); a20 = np.full(n, np.nan)
    if len(idx) >= 20:
        a20[idx] = pd.Series(amt[idx]).rolling(20).mean().to_numpy()
    return sid, {"o": o, "c": c, "bar": bar, "rc": rc, "a20": a20, "pv": pv}


def load_all(data, procs):
    cp = os.path.join(WORK, "check_world.pkl")
    if os.path.exists(cp):
        return pickle.load(open(cp, "rb"))
    cal = cal_of(data); _G.update(data=data, cal=cal)
    with Pool(procs) as pool:
        res = dict(pool.map(_load, stock_list(data), chunksize=16))
    res = {k: v for k, v in res.items() if v is not None}
    out = (cal, res)
    pickle.dump(out, open(cp, "wb"), protocol=5)
    return out


def uni(P, s, d):
    x = P[s]
    return bool(x["bar"][d] and x["pv"][d] and np.isfinite(x["a20"][d]) and x["a20"][d] >= 5e7)


def first_open(x, t):
    w = np.flatnonzero(x["bar"][t:] & np.isfinite(x["o"][t:]))
    return t + int(w[0]) if len(w) else None


def gross(P, s, e, kind, x):
    """獨立出場 ⇒ (xpos, g)。"""
    q = P[s]; n = len(q["c"]); ep = q["o"][e]
    if kind == "open" and x is not None and 0 <= x < n:
        xp = first_open(q, x)
        if xp is not None:
            return xp, q["o"][xp] / ep - 1
    if kind == "close" and x is not None and 0 <= x < n:
        return x + 1, q["c"][x] / ep - 1
    return n, q["c"][n - 1] / ep - 1


# ═════════════ 各件獨立訊號 ═════════════
def month_firsts(cal):
    m = cal.year * 100 + cal.month
    return np.flatnonzero(np.r_[True, m[1:] != m[:-1]])


def trend_state(q, d):
    """d 收盤：三條線各自多／不多（有效 K 棒序列）。"""
    idx = np.flatnonzero(q["bar"][:d + 1])
    if not len(idx) or idx[-1] != d:
        return None
    cb = q["c"][idx]; st = []
    for L in (20, 60, 240):
        if len(cb) < L + 5:
            st.append(False); continue
        ma = cb[-L:].mean(); ma5 = cb[-L - 5:-5].mean()
        if abs(cb[-1] - ma) <= 1e-9 * abs(ma) or abs(ma - ma5) <= 1e-9 * abs(ma5):
            _G["tie"] = True                      # 浮點平手（價格相同）：兩種寫法可能各判一邊 ⇒ 不比、計數
        st.append(bool(cb[-1] > ma and ma > ma5))
    return st


def sig_trend(P, cal, days, cell):
    mf = month_firsts(cal); mf = mf[mf < len(cal) - 1]
    out = {}
    for d in days:
        rows = []
        for s, q in P.items():
            if not uni(P, s, d) or not np.isfinite(q["o"][d + 1]):
                continue
            _G["tie"] = False
            st = trend_state(q, d)
            if _G["tie"]:
                TIES.add((s, d + 1)); continue
            if st is None or not all(st):
                continue
            x = None
            for t2 in mf[mf > d]:
                _G["tie"] = False
                s2 = trend_state(q, int(t2))
                if _G["tie"]:
                    TIES.add((s, d + 1))
                if s2 is None:
                    continue
                if (cell == "D1" and not all(s2)) or (cell == "D2" and not any(s2)):
                    x = int(t2) + 1; break
            rows.append((s, d + 1) + gross(P, s, d + 1, "open", x))
        out[d] = rows
    return out


def rev_tables():
    fs = sorted(glob.glob(os.path.join(TW, "early", "revenue", "*.csv"))) + sorted(glob.glob(os.path.join(TW, "mops", "revenue_hist", "*.csv")))
    df = pd.concat([pd.read_csv(f, dtype=str) for f in fs], ignore_index=True).drop_duplicates(["stock_id", "period"], keep="last")
    T = {}
    for k, c in (("rev", "當月營收"), ("ly", "去年當月營收"), ("mom", "上月比較增減(%)"), ("yoy", "去年同月增減(%)")):
        df[k] = pd.to_numeric(df[c].astype(str).str.replace(",", ""), errors="coerce")
    for r in df.itertuples(index=False):
        T[(r.stock_id, r.period)] = (r.rev, r.ly, r.mom, r.yoy)
    cat = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "產業別"]) for f in fs], ignore_index=True)
    return T, cat


def pshift(M, k):
    y, m = int(M[:4]), int(M[5:]); t = y * 12 + m - 1 + k
    return f"{t // 12:04d}-{t % 12 + 1:02d}"


def avail(cal, M):
    y, m = int(M[:4]), int(M[5:]); y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
    day = 10 if M <= "2025-12" else 15
    return int(cal.searchsorted(pd.Timestamp(y2, m2, day), side="right"))


class Ind:
    def __init__(self, cat):
        p = pd.read_csv(os.path.join(TW, "meta", "industry_hist", "industry_pit.csv"), dtype=str)
        self.seg = {}
        for sid, ind, a, b in zip(p["stock_id"], p["industry"], p["start"], p["end"]):
            self.seg.setdefault(sid, []).append((pd.Timestamp(a) if isinstance(a, str) and a else pd.Timestamp.min,
                                                 pd.Timestamp(b) if isinstance(b, str) and b else pd.Timestamp.max, ind))
        for k in self.seg:
            self.seg[k].sort(key=lambda z: z[0])
        self.cat = {}
        for s, per, c in zip(cat["stock_id"], cat["period"], cat["產業別"]):
            self.cat.setdefault(s, []).append((per, c))
        for k in self.cat:
            self.cat[k].sort()

    def at(self, s, d):
        if s in self.seg:
            sg = self.seg[s]
            for a, b, i in sg:
                if a <= d <= b:
                    return i
            if d > sg[-1][1]:
                return sg[-1][2]
            if d < sg[0][0]:
                return sg[0][2]
            return [z for z in sg if z[1] < d][-1][2]
        lim = pshift(f"{d.year:04d}-{d.month:02d}", -1 if d.day > 10 else -2)
        c = [x for x in self.cat.get(s, []) if x[0] <= lim]
        if not c:
            return None
        v = c[-1][1]
        return {"金融業": "金融保險", "證券": "金融保險", "金融保險業": "金融保險", "生物科技": "生技醫療業"}.get(v, v)


def sig_revprice(P, cal, Ms, cell, T, IND):
    out = {}
    allM = sorted({k[1] for k in T})
    for M in Ms:
        e = avail(cal, M); d = e - 1
        nm = pd.Timestamp(int(M[:4]) + (M[5:] == "12"), int(M[5:]) % 12 + 1, 1); me = int(cal.searchsorted(nm)) - 1
        U = [s for s in P if uni(P, s, d) and IND.at(s, cal[d]) not in ("金融保險", "生技醫療業")]
        R = {s: P[s]["c"][d] / P[s]["c"][me] - 1 for s in U if np.isfinite(P[s]["c"][me])}
        mu = np.mean(list(R.values()))

        def ok(s, MM):
            r = T.get((s, MM))
            if r is None or not (np.isfinite(r[2]) and np.isfinite(r[3]) and r[2] >= 0 and r[3] >= 15):
                return False
            if cell.startswith("C2"):
                h = [T.get((s, pshift(MM, -k)), (np.nan,))[0] for k in range(1, 25)]
                if not (np.isfinite(r[0]) and all(np.isfinite(h)) and r[0] <= max(h)):
                    return False
            return True
        G = [s for s in R if ok(s, M)]
        rk = pd.Series([R[s] - mu for s in G]).rank().to_numpy()
        top = [s for s, k in zip(G, rk) if k > 2 * len(G) / 3]
        rows = []
        for s in top:
            if not np.isfinite(P[s]["o"][e]):
                continue
            x = None
            for M2 in allM:
                if M2 <= M:
                    continue
                e2 = avail(cal, M2)
                if e2 >= len(cal):
                    break
                if not ok(s, M2):
                    x = e2; break
            rows.append((s, e) + gross(P, s, e, "open", x) + (R[s] - mu,))
        out[M] = rows
    return out


DEAD = {3: (0, 5, 15), 6: (0, 8, 14), 9: (0, 11, 14), 12: (1, 3, 31)}


def sig_prefin(P, cal, Ms, T, IND):
    out = {}
    for M in Ms:
        e = avail(cal, M); d = e - 1
        y = {}
        for s in P:
            if not uni(P, s, d) or IND.at(s, cal[d]) in ("金融保險", "生技醫療業"):
                continue
            v = [T.get((s, pshift(M, -k)), (np.nan, np.nan)) for k in (2, 1, 0)]
            a = [x[0] for x in v]; b = [x[1] for x in v]
            if all(np.isfinite(a)) and all(np.isfinite(b)) and sum(b) > 0:
                y[s] = sum(a) / sum(b) - 1
        ss = list(y); rk = pd.Series([y[s] for s in ss]).rank().to_numpy()
        top = [s for s, k in zip(ss, rk) if k > 0.9 * len(ss)]
        dy, mo, dd = DEAD[int(M[5:])]
        t0 = int(cal.searchsorted(pd.Timestamp(int(M[:4]) + dy, mo, dd), side="right"))
        out[M] = [(s, e) + gross(P, s, e, "close", t0 - 1 if t0 < len(cal) else None) + (y[s],) for s in top if np.isfinite(P[s]["o"][e])]
    return out


def eps_table():
    S = {}
    rows = []
    for f in sorted(glob.glob(os.path.join(FS, "*.csv"))):
        m = re.fullmatch(r"(\d{4})Q([1-4])_([a-z]+)_(twse|tpex)\.csv", os.path.basename(f))
        if not m:
            continue
        df = pd.read_csv(f, dtype=str, keep_default_na=False)
        col = [c for c in df.columns if c.startswith("基本每股盈餘")]
        for sid, v in zip(df["stock_id"].str.strip(), df[col[0]] if col else [""] * len(df)):
            rows.append((sid, int(m[1]) * 4 + int(m[2]) - 1, m[3], os.path.basename(f), pd.to_numeric(str(v).replace(",", ""), errors="coerce")))
    F = pd.DataFrame(rows, columns=["sid", "qi", "fmt", "file", "eps"])
    F["o"] = (F["fmt"] != "ci").astype(int)
    F = F.sort_values(["sid", "qi", "o", "file"]).drop_duplicates(["sid", "qi"])
    ci = {(s, q): v for s, q, v, fm in zip(F["sid"], F["qi"], F["eps"], F["fmt"]) if fm == "ci"}
    for (s, q), v in ci.items():
        if q % 4 == 0:
            S[(s, q)] = v
        elif (s, q - 1) in ci:
            S[(s, q)] = v - ci[(s, q - 1)]
        else:
            S[(s, q)] = np.nan
    return S, ci


def sig_eps(P, cal, qs, S, ci):
    def t0(q):
        y, k = q // 4, q % 4 + 1
        dy, mo, dd = {1: (0, 5, 15), 2: (0, 8, 14), 3: (0, 11, 14), 4: (1, 3, 31)}[k]
        return int(cal.searchsorted(pd.Timestamp(y + dy, mo, dd), side="right"))

    def good(s, q):
        a, b = S.get((s, q), np.nan), S.get((s, q - 1), np.nan)
        return bool(np.isfinite(a) and np.isfinite(b) and a > b)
    out = {}
    for q in qs:
        e = t0(q); d = e - 1
        rows = []
        for s in P:
            if not uni(P, s, d) or (s, q) not in ci or not good(s, q) or not np.isfinite(P[s]["o"][e]):
                continue
            x = None; q2 = q + 1
            while t0(q2) < len(cal):
                if not good(s, q2):
                    x = t0(q2); break
                q2 += 1
            key = (S[(s, q)] - S[(s, q - 1)]) / P[s]["rc"][d] if np.isfinite(P[s]["rc"][d]) and P[s]["rc"][d] > 0 else np.nan
            rows.append((s, e) + gross(P, s, e, "open", x) + (key,))
        out[q] = rows
    return out


# ═════════════ 獨立引擎 ═════════════
def replay(P, cal, F, pick, seed=20261010, slots=10):
    n = len(cal) + 1
    C = {s: np.r_[P[s]["c"], P[s]["c"][-1]] for s in set(F["sid"])}
    O = {s: np.r_[P[s]["o"], np.nan] for s in set(F["sid"])}
    w1 = int(cal.searchsorted(pd.Timestamp(W1)))
    SF = {}
    for s in C:
        b = np.flatnonzero(P[s]["bar"])
        if len(b) and b[-1] < w1:
            SF[s] = int(b[-1])
    rows = list(zip(F["sid"], F["e"].astype(int), F["xpos"].astype(int), F["g"].astype(float), F["key"].astype(float)))
    by = {}
    for r in rows:
        by.setdefault(r[1], []).append(r)
    first = min(by); last = max(r[2] for r in rows)
    rng = np.random.default_rng(seed)
    eq = np.ones(n); cash = 1.0; pos = []; held = set()
    for t in range(first, min(n, last + 2)):
        if pos:
            pos = [((t, s, a, C[s][SF[s]] / ep - 1, ep) if (s in SF and t == SF[s] + 1 and ex > t) else (ex, s, a, g, ep)) for ex, s, a, g, ep in pos]
        keep = []
        for ex, s, a, g, ep in pos:
            if ex <= t:
                cash += a * (1 + g - COST); held.discard(s)
            else:
                keep.append((ex, s, a, g, ep))
        pos = keep
        if t in by and len(pos) < slots:
            cand = [r for r in by[t] if r[0] not in held]
            if cand:
                if pick:
                    k = np.array([r[4] for r in cand], float); k = np.where(np.isnan(k), -np.inf, k)
                    order = np.argsort(-k, kind="stable")
                else:
                    order = rng.permutation(len(cand))
                slot = eq[t - 1] / slots
                for i in order[:slots - len(pos)]:
                    amt = min(slot, cash)
                    if amt <= 1e-9:
                        break
                    s, e, x, g, _ = cand[i]
                    cash -= amt
                    ep = O[s][t] if (np.isfinite(O[s][t]) and O[s][t] > 0) else C[s][t]
                    pos.append((x, s, amt, g, ep)); held.add(s)
        eq[t] = cash + sum(a * C[s][t] / ep for ex, s, a, g, ep in pos)
    end = min(n, last + 2)
    eq[end:] = eq[end - 1]
    return eq


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("study"); ap.add_argument("--procs", type=int, default=2)
    a = ap.parse_args()
    K = a.study
    OUT = os.path.expanduser(f"~/tw-p17/backtest/results{K}")
    cal, P = load_all(H2D, a.procs)
    run = pickle.load(open(os.path.join(WORK, f"{K}_run.pkl"), "rb"))
    ch = run["chosen"]; FB = run["FB"][ch]
    rng = np.random.default_rng(20261011)
    w0, w1 = int(cal.searchsorted(pd.Timestamp(W0))), int(cal.searchsorted(pd.Timestamp(W1)))
    res = {"件": K, "挑中格": ch}
    # ③ 訊號
    if K == "TrendAll":
        mf = month_firsts(cal); mf = mf[(mf + 1 >= w0) & (mf + 1 <= w1)]
        days = sorted(rng.choice(mf, 6, replace=False).tolist())
        S_ = sig_trend(P, cal, days, ch); keyed = {d + 1: v for d, v in S_.items()}
        pick = False
    elif K in ("RevPriceOK", "PreFinRev"):
        T, cat = rev_tables(); IND = Ind(cat)
        if K == "RevPriceOK":
            Ms = [M for M in (f"{y}-{m:02d}" for y in range(2017, 2027) for m in range(1, 13)) if w0 <= avail(cal, M) <= w1]
            Ms = sorted(rng.choice(Ms, 6, replace=False).tolist())
            S_ = sig_revprice(P, cal, Ms, ch, T, IND); pick = ch.endswith("S2")
        else:
            Ms = [M for M in (f"{y}-{m:02d}" for y in range(2017, 2027) for m in (3, 6, 9, 12)) if w0 <= avail(cal, M) <= w1]
            Ms = sorted(rng.choice(Ms, 6, replace=False).tolist())
            S_ = sig_prefin(P, cal, Ms, T, IND); pick = ch == "A1"
        keyed = {avail(cal, M): v for M, v in S_.items()}
    else:
        S, ci = eps_table()
        qs = [q for q in range(2015 * 4, 2026 * 4 + 2)]
        def t0(q):
            y, k = q // 4, q % 4 + 1
            dy, mo, dd = {1: (0, 5, 15), 2: (0, 8, 14), 3: (0, 11, 14), 4: (1, 3, 31)}[k]
            return int(cal.searchsorted(pd.Timestamp(y + dy, mo, dd), side="right"))
        qs = [q for q in qs if w0 <= t0(q) <= w1]
        qs = sorted(rng.choice(qs, 6, replace=False).tolist())
        S_ = sig_eps(P, cal, qs, S, ci); pick = ch == "G2"
        keyed = {t0(q): v for q, v in S_.items()}
    diff = []; ncmp = 0
    for e, rows in keyed.items():
        mine = {r[0]: r for r in rows if (r[0], e) not in TIES}
        theirs = FB[FB["e"] == e]
        th = {s: r for s, r in zip(theirs["sid"], theirs.itertuples(index=False)) if (s, e) not in TIES}
        if set(mine) != set(th):
            diff.append({"e": str(cal[e].date()), "只在獨立": sorted(set(mine) - set(th))[:10], "只在本體": sorted(set(th) - set(mine))[:10]})
        for s in set(mine) & set(th):
            ncmp += 1
            m = mine[s]; t = th[s]
            if int(m[2]) != int(t.xpos) or abs(m[3] - t.g) > TOL * max(1, abs(t.g)):
                diff.append({"e": str(cal[e].date()), "sid": s, "獨立": [int(m[2]), float(m[3])], "本體": [int(t.xpos), float(t.g)]})
            if pick and len(m) > 4 and not (np.isclose(m[4], t.key, rtol=1e-9, atol=1e-12) or (np.isnan(m[4]) and np.isnan(t.key))):
                diff.append({"e": str(cal[e].date()), "sid": s, "鍵": [float(m[4]), float(t.key)]})
    res["③ 訊號抽樣"] = {"抽樣日": [str(cal[e].date()) for e in keyed], "比對筆": ncmp, "候選數": {str(cal[e].date()): len(v) for e, v in keyed.items()},
                       "浮點平手不比（股-進場日）": len(TIES), "毛報酬容差（相對）": TOL, "不同": len(diff), "明細": diff[:20]}
    # ④ 引擎（訊號表用本體的；價格用獨立讀的）
    eq = replay(P, cal, FB, pick)
    eq0 = run["eq0"]
    rel = float(np.max(np.abs(eq[w0:w1 + 1] / eq0[w0:w1 + 1] - 1)))
    res["④ 引擎 r＝0 權益（主窗）最大相對差"] = rel
    res["④ 不同"] = int(rel > TOL)
    res["容差說明"] = "還原價：adj 檔 cum_factor 欄（事件日嚴格晚於該日的第一列）；容差 1e−9"
    res["過"] = bool(len(diff) == 0 and rel <= TOL)
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(res, ensure_ascii=False, default=str)[:3000])


if __name__ == "__main__":
    main()
