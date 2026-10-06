# -*- coding: utf-8 -*-
"""USREG-A2（M／U／X／W1b）的【獨立路】抽樣查核。⛔ 不 import researchUSA2*、researchUSM*／USU／USX／USW1b、us_data、research11、
trendline_m、fib_u、patterns_x；只讀 ~/usdata/881c86a/data 原始 CSV、~/us_work/a2/（repo 外）主程式的逐筆檔、resultsUSA2/*_summary.json。

    PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSA2_check

自己重寫一遍的東西：聯集 panel（兩個指數逐日成分、那天用哪一列）、還原 OHLC、有效 K 棒、硬斷點（seam／同日拆股配息）、出場價退路、
等權基準（M 開盤版 EW20、X 乙 收盤版 EW20）、月分群 CI、n_eff、出口／結果字樣、U 的 ±5% 帶反彈判定與 D、X 甲 的達成判定、
W1b 的季營收新高（含 S&P 400 分段 CIK）、ma_stack／ma60_up、條件換股出場日、權益窗內年化回落、成交紀錄重建現金。
查核項（全部要 0 不同）：
 C1 M 抽 40×3 筆事件：T 當天屬哪個指數、g ＝ px(T+21)／open(T+1) − 1、EW20(T+1)（抽 4 個日子全母體重算）
 C2 M 三格 × 三欄：平均／CI／n_eff／結果字樣 由事件檔重算 ＝ summary
 C3 U H20 抽 60 筆：反彈判定 y 由原始收盤重算；三欄 D／CI 由事件檔重算 ＝ summary
 C4 X 甲 抽 60 筆：事件與對照的 60 日達成由原始最高價重算；甲 五型 × 三欄 D／CI ＝ summary；乙 抽 60 筆 R 由原始價重算、EW20 抽 3 日重算；乙 六型 × 三欄 ＝ summary
 C5 W1b：基準；各母體各臂 年化中位／回落中位／標籤 由 W1b_seeds.csv 重算；種子 102000 權益窗內年化回落、成交紀錄重建現金；
    抽 30 筆成交價；抽 60 列面板重算 營收新高（含 S&P 400 分段）／ma_stack／ma60_up／bars／成分；抽 40 筆訊號重算條件換股出場日
輸出：resultsUSA2/check.json（只有差與計數）。
"""
import json
import os
import re
import sys

import numpy as np
import pandas as pd

ROOT = os.path.expanduser("~/usdata/881c86a/data")
WORK = os.path.expanduser("~/us_work/a2")
OUT = os.path.expanduser("~/tw-p17/backtest/resultsUSA2")
W0, W1 = pd.Timestamp("2016-01-04"), pd.Timestamp("2026-09-30")
CAL0 = pd.Timestamp("2015-11-02")
COST = 0.0005
CALF = pd.DatetimeIndex(sorted(pd.to_datetime(pd.read_csv(os.path.join(ROOT, "macro", "yahoo_GSPC.csv"), usecols=["date"])["date"])))
CAL = CALF[CALF >= CAL0]
NC = len(CAL)
I0, I1 = CAL.get_loc(W0), CAL.get_loc(W1)
PD = {"sp500": "panel", "sp400": "panel_sp400"}
MD = {"sp500": "membership", "sp400": "membership_sp400"}
RNG = np.random.default_rng(20261007)


# ═════════════ 聯集 panel（自己寫一遍）═════════════
def spans(idx):
    u = pd.read_csv(os.path.join(ROOT, MD[idx], "universe.csv"), dtype=str, keep_default_na=False)
    out = {}
    for t, s in zip(u["ticker"], u["spans"]):
        L = []
        for x in s.split(";"):
            a, b = x.split("~"); L.append((np.datetime64(a), np.datetime64(b) if b else np.datetime64("2200-01-01")))
        out[t] = L
    return out


SP = {k: spans(k) for k in PD}


def splitdiv():
    out = set()
    for idx in PD:
        on = False
        for line in open(os.path.join(ROOT, PD[idx], "_report.md"), encoding="utf-8"):
            if line.startswith("## "):
                on = "同一天拆股" in line; continue
            m = re.match(r"^- (\S+) (\d{4}-\d{2}-\d{2})：", line)
            if on and m:
                out.add((m.group(1), np.datetime64(m.group(2))))
    return out


SD = splitdiv()
_SRC = {}


def src_px(src):
    if src in _SRC:
        return _SRC[src]
    k, f = src.split(":", 1)
    if k == "yahoo":
        d = pd.read_csv(os.path.join(ROOT, "prices_yahoo", f + ".csv"), dtype={"date": str}); a = d["adjclose"] / d["close"]
        o, h, l, c = d["open"] * a, d["high"] * a, d["low"] * a, d["close"] * a
    else:
        d = pd.read_csv(os.path.join(ROOT, "prices", f + ".csv"), dtype={"date": str})
        o, h, l, c = d["adjOpen"], d["adjHigh"], d["adjLow"], d["adjClose"]
    x = pd.DataFrame({"o": o.to_numpy(float), "h": h.to_numpy(float), "l": l.to_numpy(float), "c": c.to_numpy(float)},
                     index=pd.DatetimeIndex(pd.to_datetime(d["date"])))
    _SRC[src] = x
    return x


_UN = {}


class Stock:
    """一檔在日曆 CAL 上的陣列：m5、m4（逐指數成分）、o h l c（無效 ⇒ NaN）、pb（硬斷點）、src。"""

    def __init__(self, t):
        self.t = t
        P = {}
        for idx in PD:
            p = os.path.join(ROOT, PD[idx], t + ".csv")
            P[idx] = pd.read_csv(p, dtype=str, keep_default_na=False).set_index("date") if os.path.exists(p) else None
        cv = CAL.values
        M = {}; R = {}
        for idx in PD:
            m = np.zeros(NC, bool)
            for a, b in SP[idx].get(t, []):
                m |= (cv >= a) & (cv < b)
            r = np.full(NC, None, dtype=object)
            if P[idx] is not None:
                dd = pd.DatetimeIndex(pd.to_datetime(P[idx].index)).values
                i = np.searchsorted(cv, dd)
                hit = (i < NC) & (cv[np.minimum(i, NC - 1)] == dd)
                m[i[hit]] = P[idx]["in_index"].to_numpy()[hit] == "1"
                r[i[hit]] = P[idx]["src"].to_numpy(object)[hit]
            M[idx] = m; R[idx] = list(r)
        self.m5, self.m4 = M["sp500"], M["sp400"]
        src = [None] * NC
        for i in range(NC):
            a, b = R["sp500"][i], R["sp400"][i]
            if self.m5[i]:
                src[i] = a
            elif self.m4[i]:
                src[i] = b
            elif a is not None and b is not None:
                src[i] = a if a.rstrip("*") == b.rstrip("*") else None
            else:
                src[i] = a if a is not None else b
        self.src = src
        self.o = np.full(NC, np.nan); self.h = np.full(NC, np.nan); self.l = np.full(NC, np.nan); self.c = np.full(NC, np.nan)
        star = np.zeros(NC, bool)
        s0arr = np.array([x.rstrip("*") if x else "" for x in src], dtype=object)
        for s in set(s0arr) - {""}:
            px = src_px(s)
            ii = np.flatnonzero(s0arr == s)
            v = px.reindex(CAL[ii])[["o", "h", "l", "c"]].to_numpy(float)
            with np.errstate(invalid="ignore"):
                ok = np.isfinite(v).all(axis=1) & (v > 0).all(axis=1) & (v[:, 2] <= np.minimum(v[:, 0], v[:, 3])) & (np.maximum(v[:, 0], v[:, 3]) <= v[:, 1])
            self.o[ii[ok]], self.h[ii[ok]], self.l[ii[ok]], self.c[ii[ok]] = v[ok, 0], v[ok, 1], v[ok, 2], v[ok, 3]
        star = np.array([bool(x and x.endswith("*")) for x in src])
        for tk, d in SD:
            if tk == t and d in set(CAL.values):
                star[int(np.searchsorted(CAL.values, d))] = True
        self.valid = np.isfinite(self.c)
        # 硬斷點：有效 K 棒序列上 src 換檔、或同日拆股配息（無效那根帶斷點 ⇒ 移到下一根有效）
        pb = np.zeros(NC, bool); prev = None; carry = False
        for i in range(NC):
            s0 = src[i].rstrip("*") if src[i] else None
            if s0 is None:
                continue
            brk = (prev is not None and s0 != prev) or star[i]
            prev = s0
            if self.valid[i]:
                pb[i] = brk or carry; carry = False
            elif brk:
                carry = True
        self.pb = pb
        self.mem = self.m5 | self.m4
        self.cff = pd.Series(self.c).ffill().to_numpy()

    def px(self, j):
        return self.o[j] if (self.valid[j] and self.o[j] > 0) else self.cff[j]


def S(t):
    if t not in _UN:
        _UN[t] = Stock(t)
    return _UN[t]


def all_tickers():
    return sorted(set(SP["sp500"]) | set(SP["sp400"]))


def nobreak(st, a, b):
    """(a, b] 內無 pb。"""
    return not st.pb[a + 1:b + 1].any()


def ew_open(d, H):
    """M 基準：d 日在聯集成分、有效 K 棒、開盤 > 0；(d, d+H] 無斷點；px(d+H)／open(d) − 1 等權。"""
    v = []
    for t in all_tickers():
        st = S(t)
        if not (st.mem[d] and st.valid[d] and st.o[d] > 0) or not nobreak(st, d, d + H):
            continue
        v.append(st.px(d + H) / st.o[d] - 1.0)
    return float(np.mean(v)), len(v)


def ew_close(d, H):
    """X 乙 基準：同上但出場 ＝ ≤ d+H−1 最後一根有效收盤；(d, d+H−1] 無斷點。"""
    v = []
    for t in all_tickers():
        st = S(t)
        if not (st.mem[d] and st.valid[d] and st.o[d] > 0) or not nobreak(st, d, d + H - 1):
            continue
        v.append(st.cff[d + H - 1] / st.o[d] - 1.0)
    return float(np.mean(v)), len(v)


# ═════════════ 統計（自己寫）═════════════
def clci(x, months):
    x = np.asarray(x, float); n = len(x); mu = x.mean()
    g = pd.Series(x - mu).groupby(np.asarray(months)).sum().to_numpy()
    se = np.sqrt((g ** 2).sum()) / n
    return mu, mu - 1.96 * se, mu + 1.96 * se


def verdict_m(n, neff, lo, hi, mu):
    if n < 30:
        return "結果④（事件 < 30，併入出口①：樣本不足以分辨）"
    if neff < 30:
        return "—（出口①：樣本不足以分辨）"
    if lo <= 0 <= hi:
        return "結果①（測不出）"
    return "結果②（測得出（＋））" if mu > 0 else "結果③（測得出（−））"


def mon(T):
    return [str(CAL[int(t)])[:7] for t in T]


def worst(a, b):
    try:
        if a is None and b is None:
            return 0.0
        return abs(float(a) - float(b))
    except (TypeError, ValueError):
        return np.inf


# ═════════════ C1、C2：M ═════════════
def check_m(res):
    J = json.load(open(os.path.join(OUT, "M_summary.json"), encoding="utf-8"))
    cap = J["區段上限_20日"]
    d1 = 0.0; bad_idx = 0; nchk = 0; d2 = 0.0; bad_lab = 0
    ew = {}
    for m in ("甲", "乙", "丙"):
        E = pd.read_csv(os.path.join(WORK, f"M_events_{m}.csv"), dtype={"sid": str, "idx": str})
        for i in RNG.choice(len(E), 40, replace=False):
            r = E.iloc[int(i)]; st = S(r["sid"]); T = int(r["T"])
            assert str(CAL[T].date()) == r["T_date"]
            bad_idx += int(("400" if st.m4[T] else "500") != r["idx"] or not st.mem[T])
            g = st.px(T + 21) / st.o[T + 1] - 1.0
            d1 = max(d1, abs(g - r["g"]))
            nchk += 1
        for d in RNG.choice(E["T"].to_numpy(), 2 if m != "丙" else 0, replace=False):
            d = int(d) + 1
            if d not in ew:
                ew[d] = ew_open(d, 20)
            row = E[E["T"] == d - 1].iloc[0]
            d1 = max(d1, abs(ew[d][0] - row["EW"]))
        for g_ in ("合併", "只S&P400", "只S&P500"):
            e = E if g_ == "合併" else E[E["idx"] == ("400" if g_ == "只S&P400" else "500")]
            mu, lo, hi = clci(e["X"], mon(e["T"]))
            nb = int(np.minimum((e["T"] - I0) // 20, cap - 1).nunique()); neff = min(len(e), nb)
            s = J["格"][m][g_]
            d2 = max(d2, worst(mu, s["平均"]), worst(lo, s["lo"]), worst(hi, s["hi"]), abs(neff - s["n_eff"]))
            bad_lab += int(verdict_m(len(e), neff, lo, hi, mu) != s["結果"])
    res["C1_M逐筆"] = {"抽查事件": nchk, "抽查基準日": len(ew), "g與EW最大差": d1, "指數歸屬或成分不符": bad_idx}
    res["C2_M三格三欄"] = {"平均CI_n_eff最大差": d2, "結果字樣不符": bad_lab}
    print("C1 M 逐筆 {} 筆＋基準 {} 日：最大差 {:.1e}｜歸屬不符 {}｜C2 三格三欄 最大差 {:.1e}｜字樣不符 {}".format(nchk, len(ew), d1, bad_idx, d2, bad_lab), flush=True)
    return d1 < 1e-9 and bad_idx == 0 and d2 < 1e-9 and bad_lab == 0


# ═════════════ C3：U ═════════════
WD = {"38.2": 0.5, "61.8": 0.5, "30": -0.25, "45": -0.25, "55": -0.25, "70": -0.25}


def dstat(E):
    d = E[E["pos"].isin(list(WD)) & (E["y"] >= 0)]
    b = {p: d.loc[d["pos"] == p, "y"].mean() for p in WD}; nn = {p: (d["pos"] == p).sum() for p in WD}
    D = sum(WD[p] * b[p] for p in WD)
    contrib = np.array([WD[p] * (y - b[p]) / nn[p] for p, y in zip(d["pos"], d["y"])])
    g = pd.Series(contrib).groupby(d["mon"].to_numpy()).sum().to_numpy()
    se = np.sqrt((g ** 2).sum())
    return D, D - 1.96 * se, D + 1.96 * se


def check_u(res):
    J = json.load(open(os.path.join(OUT, "U_summary.json"), encoding="utf-8"))
    E = pd.read_csv(os.path.join(WORK, "U_events_H20.csv.gz"), dtype={"sid": str, "idx": str, "pos": str})
    bad = 0; n = 0
    for i in RNG.choice(len(E), 60, replace=False):
        r = E.iloc[int(i)]; st = S(r["sid"]); T = int(r["T"]); p = float(r["p"])
        y = -1
        for k in range(21):
            c = st.c[T + k]
            if not np.isfinite(c):
                continue
            if c > p * 1.05:
                y = 1; break
            if c < p * 0.95:
                y = 0; break
        bad += int(y != int(r["y"])); n += 1
    d = 0.0
    for g_ in ("合併", "只S&P400", "只S&P500"):
        e = E if g_ == "合併" else E[E["idx"] == ("400" if g_ == "只S&P400" else "500")]
        D, lo, hi = dstat(e)
        s = J["天數"]["20"][g_]
        d = max(d, worst(D, s["D"]), worst(lo, s["lo"]), worst(hi, s["hi"]))
    res["C3_U"] = {"抽查反彈判定": n, "不符": bad, "三欄D與CI最大差": d}
    print("C3 U 抽 {} 筆反彈判定 不符 {}｜三欄 D／CI 最大差 {:.1e}".format(n, bad, d), flush=True)
    return bad == 0 and d < 1e-9


# ═════════════ C4：X ═════════════
def check_x(res):
    J = json.load(open(os.path.join(OUT, "X_summary.json"), encoding="utf-8"))
    bad = 0; n = 0; dD = 0.0
    for typ in ("box", "cup", "w", "hs", "flag"):
        X = pd.read_csv(os.path.join(WORK, f"X_A_{typ}.csv.gz"), dtype={"sid": str, "ctl": str, "idx": str})
        if len(X) == 0:
            continue
        for i in RNG.choice(len(X), min(12, len(X)), replace=False):
            r = X.iloc[int(i)]; T = int(r["t"]); st = S(r["sid"]); ct = S(r["ctl"])
            tg = st.c[T] * (1 + r["dist"]); tc = ct.c[T] * (1 + r["dist"])
            for H in (60, 120):
                hs = st.h[T + 1:T + H + 1]; hc = ct.h[T + 1:T + H + 1]
                a = int(np.isfinite(hs).any() and np.nanmax(hs) >= tg * (1 - 1e-12)); b = int(np.isfinite(hc).any() and np.nanmax(hc) >= tc)
                bad += int(a != int(r[f"sig_{H}"])) + int(b != int(r[f"ctl_{H}"]))
            bad += int(("400" if st.m4[T] else "500") != r["idx"])
            n += 1
        for g_ in ("合併", "只S&P400", "只S&P500"):
            e = X if g_ == "合併" else X[X["idx"] == ("400" if g_ == "只S&P400" else "500")]
            s = J["甲"][typ][g_]["H60（判定）"]
            if len(e) == 0:
                continue
            mu, lo, hi = clci(e["d_60"], e["month"])
            dD = max(dD, worst(mu, s["D"]), worst(lo, s["lo"]), worst(hi, s["hi"]))
    badB = 0; nB = 0; dB = 0.0; ewc = {}
    for typ in ("box", "cup", "w", "hs", "flag", "trend"):
        X = pd.read_csv(os.path.join(WORK, f"X_B_{typ}.csv.gz"), dtype={"sid": str, "idx": str})
        if len(X) == 0:
            continue
        for i in RNG.choice(len(X), min(10, len(X)), replace=False):
            r = X.iloc[int(i)]; t = int(r["t"]); st = S(r["sid"])
            R_ = st.cff[t + 20] / st.o[t + 1] - 1.0
            dB = max(dB, abs(R_ - r["R"])); badB += int(("400" if st.m4[t] else "500") != r["idx"]); nB += 1
        if typ in ("box", "trend"):
            for i in RNG.choice(len(X), 1, replace=False):
                t = int(X.iloc[int(i)]["t"]) + 1
                if t not in ewc:
                    ewc[t] = ew_close(t, 20)
                dB = max(dB, abs(ewc[t][0] - X.iloc[int(i)]["EW"]))
        for g_ in ("合併", "只S&P400", "只S&P500"):
            e = X if g_ == "合併" else X[X["idx"] == ("400" if g_ == "只S&P400" else "500")]
            s = J["乙"][typ][g_]["20日（判定）"]
            if len(e) == 0:
                continue
            mu, lo, hi = clci(e["X"], e["month"])
            dD = max(dD, worst(mu, s["D"]), worst(lo, s["lo"]), worst(hi, s["hi"]))
    res["C4_X"] = {"甲抽查": n, "甲達成或歸屬不符": bad, "乙抽查": nB, "乙歸屬不符": badB, "乙R與EW最大差": dB, "抽查EW日": len(ewc), "格D與CI最大差": dD}
    print("C4 X 甲 {} 筆 不符 {}｜乙 {} 筆 歸屬不符 {}、R／EW 最大差 {:.1e}｜格 D／CI 最大差 {:.1e}".format(n, bad, nB, badB, dB, dD), flush=True)
    return bad == 0 and badB == 0 and dB < 1e-9 and dD < 1e-9


# ═════════════ C5：W1b ═════════════
def wm(x, ann=252):
    x = np.asarray(x, float); c = (x[-1] / x[0]) ** (ann / len(x)) - 1
    pk = np.maximum.accumulate(x)
    return c, float(((x - pk) / pk).min())


def lab(c, m, cb, mb):
    return "合格" if (c > cb and c / abs(m) >= cb / abs(mb)) else ("另列" if c > cb else "不合格")


class Rev:
    def __init__(self):
        F = os.path.join(ROOT, "fundamentals")
        self.q5 = pd.read_csv(os.path.join(F, "quarterly_revenue.csv"), dtype={"ticker": str, "cik": str}, usecols=["ticker", "cik", "period_end", "value", "first_filed"])
        self.q4 = pd.read_csv(os.path.join(F, "quarterly_revenue_sp400.csv"), dtype={"ticker": str, "cik": str}, usecols=["ticker", "cik", "period_end", "value", "first_filed"])
        for q in (self.q5, self.q4):
            q["period_end"] = pd.to_datetime(q["period_end"]); ff = pd.to_datetime(q["first_filed"])
            k = CALF.searchsorted(ff.values, side="right"); q["avail"] = [CALF[x] if x < len(CALF) else pd.NaT for x in k]
        self.cm = pd.read_csv(os.path.join(F, "cik_map_sp400.csv"), dtype=str, keep_default_na=False)
        pr = pd.read_csv(os.path.join(F, "cik_predecessor_sp400.csv"), dtype=str, keep_default_na=False)
        self.pred = {}
        for a, b, v in zip(pr["cik_now"], pr["pred_cik"], pr["verdict"]):
            if v == "ok":
                self.pred.setdefault(a, set()).add(b)

    def rows(self, t, idx, d_for_seg):
        if idx == "sp500":
            return self.q5[self.q5["ticker"] == t]
        g = self.q4[self.q4["ticker"] == t]
        c = self.cm[self.cm["ticker"] == t]
        if ((c["seg_from"] != "") | (c["seg_to"] != "")).any():
            for _, r in c.iterrows():
                a = pd.Timestamp(r["seg_from"]) if r["seg_from"] else pd.Timestamp("1900-01-01")
                b = pd.Timestamp(r["seg_to"]) if r["seg_to"] else pd.Timestamp("2200-01-01")
                if a <= d_for_seg < b:
                    return g[g["cik"].isin({r["cik"]} | self.pred.get(r["cik"], set()))]
            return g.iloc[0:0]
        return g

    @staticmethod
    def newhigh(q, d):
        q = q[q["avail"] <= d].sort_values(["period_end", "avail"]).drop_duplicates("period_end", keep="first")
        if len(q) < 8:
            return False
        q = q.tail(8)
        gap = np.diff(q["period_end"].to_numpy("datetime64[D]")).astype(int); v = q["value"].to_numpy(float)
        if (gap > 140).any() or (v <= 0).any():
            return False
        mx = v[:-1].max()
        return bool(v[-1] >= mx - abs(mx) * 1e-4)


def tech(st, d):
    c = pd.Series(np.where(st.valid, st.c, np.nan)).ffill()
    c[np.arange(NC) < np.flatnonzero(st.valid)[0]] = np.nan
    c = c.iloc[:d + 1]
    if c.iloc[-120:].isna().any() or len(c) < 120:
        ms = np.nan
    else:
        m20, m60, m120 = c.iloc[-20:].mean(), c.iloc[-60:].mean(), c.iloc[-120:].mean()
        ms = 100.0 if (c.iloc[-1] > m20 > m60 > m120) else 0.0
    if len(c) < 80 or c.iloc[-80:].isna().any():
        mu = np.nan
    else:
        mu = 100.0 if c.iloc[-60:].mean() > c.iloc[-80:-20].mean() else 0.0
    return ms, mu


def check_w(res):
    J = json.load(open(os.path.join(OUT, "W1b_summary.json"), encoding="utf-8"))
    tr = pd.read_csv(os.path.join(ROOT, "macro", "yahoo_SP500TR.csv"), usecols=["date", "adjclose"])
    tr = pd.Series(tr["adjclose"].to_numpy(float), pd.to_datetime(tr["date"])).reindex(CAL).ffill().to_numpy()
    bc, bm = wm(tr[I0:I1 + 1])
    d1 = max(abs(bc - J["基準"]["SP500TR"]["年化"]), abs(bm - J["基準"]["SP500TR"]["回落"]))
    gs = pd.read_csv(os.path.join(ROOT, "macro", "yahoo_GSPC.csv"), usecols=["date", "close"])
    gs = pd.Series(gs["close"].to_numpy(float), pd.to_datetime(gs["date"])).reindex(CAL).ffill().to_numpy()
    net = np.r_[1.0, np.cumprod(gs[1:] / gs[:-1] + 0.7 * (tr[1:] / tr[:-1] - gs[1:] / gs[:-1]))]
    nc_, nm_ = wm(net[I0:I1 + 1])
    D = pd.read_csv(os.path.join(WORK, "W1b_seeds.csv"))
    d2 = 0.0; same = True
    for (pop, arm), g in D.groupby(["pop", "arm"]):
        cb, mb = (nc_, nm_) if arm == "div_net30" else (bc, bm)
        c, m = float(np.median(g["cagr"])), float(np.median(g["mdd"]))
        s = J["結果"][pop][arm]
        d2 = max(d2, abs(c - s["年化中位"]), abs(m - s["回落中位"])); same &= lab(c, m, cb, mb) == s["標籤"] and len(g) == J["種子數"]
    E = pd.read_csv(os.path.join(WORK, "W1b_equity_seed102000_main_comb.csv")); eq = E["equity"].to_numpy(float)
    dd = pd.to_datetime(E["date"]); a = int(np.flatnonzero(dd == W0)[0]); b = int(np.flatnonzero(dd == W1)[0])
    c0, m0 = wm(eq[a:b + 1]); row = D[(D["pop"] == "合併") & (D["arm"] == "main") & (D["seed"] == 102000)].iloc[0]
    d3 = max(abs(c0 - row["cagr"]), abs(m0 - row["mdd"]))
    A = pd.read_csv(os.path.join(WORK, "W1b_audit_seed102000_main_comb.csv"), dtype={"sid": str})
    cash = 1.0 + float(-A.loc[A["side"] == "buy", "amt"].sum() + (A.loc[A["side"] == "sell", "amt"] - A.loc[A["side"] == "sell", "cost"]).sum())
    open_at_end = A.groupby("sid")["side"].apply(lambda s: (s == "buy").sum() - (s == "sell").sum()).sum()
    d_cash = abs(cash - eq[-1]) if open_at_end == 0 else None
    pxd = 0.0; npx = 0
    for i in RNG.choice(len(A), min(30, len(A)), replace=False):
        r = A.iloc[int(i)]; st = S(r["sid"]); t = int(r["t"])
        if r["side"] == "buy":
            v = st.o[t]
        else:
            cand = [st.o[t], st.c[t], st.cff[t]]
            v = min(cand, key=lambda x: abs(x - r["px"]) if np.isfinite(x) else np.inf)
        pxd = max(pxd, abs(v - r["px"]) / v); npx += 1
    # 面板 60 列
    P = pd.read_csv(os.path.join(WORK, "W1b_panel_monthly.csv.gz"), dtype={"t": str})
    base = P[P["base"]]
    rv = Rev(); badp = {"rev": 0, "ma_stack": 0, "ma60_up": 0, "bars": 0, "member": 0, "idx": 0}; nchk = 0
    for i in RNG.choice(len(base), 60, replace=False):
        r = base.iloc[int(i)]; t = r["t"]; d = int(r["d"]); st = S(t); day = CAL[d]
        idx = "sp500" if st.m5[d] else "sp400"
        badp["idx"] += int(bool(r["m4"]) != bool(st.m4[d]))
        q = rv.rows(t, idx, day)
        badp["rev"] += int(Rev.newhigh(q, day) != bool(r["rev_ok"]))
        ms, mu = tech(st, d)
        badp["ma_stack"] += int(not (ms == r["ma_stack"] or (np.isnan(ms) and np.isnan(r["ma_stack"]))))
        badp["ma60_up"] += int(not (mu == r["ma60_up"] or (np.isnan(mu) and np.isnan(r["ma60_up"]))))
        badp["bars"] += int(int(st.valid[:d + 1].sum()) != int(r["bars"])); badp["member"] += int(not (st.mem[d] and st.valid[d]))
        nchk += 1
    # 訊號 40 筆：條件換股出場日
    SG = pd.read_csv(os.path.join(WORK, "W1b_signals.csv.gz"), dtype={"sid": str})
    per = CAL.to_period("M"); meas = np.flatnonzero(np.r_[True, per[1:] != per[:-1]]); meas = meas[meas + 1 <= I1]
    badx = 0; nx = 0
    for i in RNG.choice(len(SG), 40, replace=False):
        r = SG.iloc[int(i)]; st = S(r["sid"]); d = int(r["measure"])
        idx = "sp500" if st.m5[d] else "sp400"
        q = rv.rows(r["sid"], idx, CAL[d])
        x = None
        for dp in meas[meas > d]:
            ms, mu = tech(st, int(dp))
            if not (Rev.newhigh(q, CAL[dp]) and ms == 0 and mu == 100):
                x = int(dp) + 1; break
        x = I1 if x is None else x
        badx += int(x != int(r["xpos_main"])); nx += 1
    res["C5_W1b"] = {"基準最大差": d1, "各臂中位最大差": d2, "標籤與種子數全同": bool(same), "種子102000窗內差": d3,
                     "成交紀錄重建現金差": d_cash, "模擬尾未平倉": int(open_at_end), "抽查成交價": npx, "成交價最大相對差": pxd,
                     "面板抽查": nchk, "面板不符": badp, "條件換股出場日抽查": nx, "出場日不符": badx}
    print("C5 W1b 基準 {:.1e}｜臂 {:.1e} 標籤 {}｜種子 {:.1e}｜現金 {}｜成交價 {} 筆 {:.1e}｜面板 {} 列 {}｜出場日 {} 筆 不符 {}".format(
        d1, d2, same, d3, d_cash, npx, pxd, nchk, badp, nx, badx), flush=True)
    return d1 < 1e-12 and d2 < 1e-12 and same and d3 < 1e-12 and (d_cash is None or d_cash < 1e-9) and pxd < 1e-9 and sum(badp.values()) == 0 and badx == 0


def main():
    res = {}
    ok = []
    which = [a for a in ("m", "u", "x", "w") if "--" + a in sys.argv] or ["m", "u", "x", "w"]
    for k in which:
        ok.append({"m": check_m, "u": check_u, "x": check_x, "w": check_w}[k](res))
    res["全部通過"] = bool(all(ok))
    p = os.path.join(OUT, "check.json")
    old = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    old.update(res); old["全部通過"] = all(v for k, v in old.items() if k == "全部通過") and res["全部通過"]
    json.dump(old, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print("全部通過" if res["全部通過"] else "⛔ 有不符", flush=True)
    sys.exit(0 if res["全部通過"] else 1)


if __name__ == "__main__":
    main()
