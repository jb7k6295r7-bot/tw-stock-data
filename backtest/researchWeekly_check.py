# -*- coding: utf-8 -*-
"""researchWeekly 獨立查核（另一套寫法）。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchWeekly_check.py

甲（抽 5 筆訊號：確認段 S1～S4 各一、早年一筆；取各類中位那筆）：
  週 K 用 pandas to_period("W-SUN") 分組（主程式用週一日期 factorize）；KD、RSI 用另一種遞迴寫法、MACD 用 pandas ewm(adjust=False)；
  重判：該週是訊號、已過 52 週暖機、前後 1 週無壞根、同訊號前 8 週內沒有保留訊號（自己從頭走合併）；
  R_k 用日曆重找進出場日；基準② 自己重建那一週的橫斷面（母體沿用 researchEvt.eligibility、壞根沿用 load_bars，其餘自己算）⇒ X 比對
乙（挑中格、主窗確認段抽 5 筆：週收觸發 3、觸頂 C 1、其他 1）：週 K、週 MA、觸發週、賣出根、g 用另一套寫法重算，比對 researchWeekly.build_b
"""
import json
import os
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import tradability as TR
from backtest import universe_gate as UG
from backtest import research11 as R11
from backtest import rerun17 as RR
from backtest import researchEvt as EV

OUT = "backtest/resultsWeekly"
ST = EV.ST
_G = {}


def wk_frame(sid, mk, cal):
    st = D.load_stock(sid, mk, cal)
    if st is None:
        return None, None
    df = st.df.copy(); df.index = cal
    v = df[np.isfinite(df["close"].to_numpy(float))]
    g = v.groupby(v.index.to_period("W-SUN"))
    W = pd.DataFrame({"O": g["open"].first(), "H": g["high"].max(), "L": g["low"].min(), "C": g["close"].last(),
                      "V": g["volume"].apply(lambda s: np.nansum(pd.to_numeric(s, errors="coerce")))})
    return W, df


def sig_series(W):
    C, H, L, O, V = (W[k].to_numpy(float) for k in ("C", "H", "L", "O", "V")); n = len(C)
    K = [np.nan] * n; Dd = [np.nan] * n; kp, dp = 50.0, 50.0
    for t in range(8, n):
        lo, hi = min(L[t - 8:t + 1]), max(H[t - 8:t + 1])
        rsv = 50.0 if hi == lo else 100.0 * (C[t] - lo) / (hi - lo)
        kp = (2 * kp + rsv) / 3.0; dp = (2 * dp + kp) / 3.0; K[t], Dd[t] = kp, dp
    s = pd.Series(C)
    dif = s.ewm(span=12, adjust=False).mean() - s.ewm(span=26, adjust=False).mean(); osc = (dif - dif.ewm(span=9, adjust=False).mean()).to_numpy()
    R = [np.nan] * n
    if n > 14:
        up = [max(C[i] - C[i - 1], 0) for i in range(1, n)]; dn = [max(C[i - 1] - C[i], 0) for i in range(1, n)]
        ag = sum(up[:14]) / 14; al = sum(dn[:14]) / 14
        R[14] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
        for t in range(15, n):
            ag = (13 * ag + up[t - 1]) / 14; al = (13 * al + dn[t - 1]) / 14
            R[t] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    out = {k: np.zeros(n, bool) for k in ("S1", "S2", "S3", "S4")}
    for t in range(1, n):
        out["S1"][t] = K[t - 1] <= Dd[t - 1] and K[t] > Dd[t] and K[t] <= 30
        out["S2"][t] = osc[t - 1] <= 0 < osc[t]
        out["S3"][t] = R[t - 1] < 30 <= R[t]
        if t >= 26:
            out["S4"][t] = O[t] > 0 and C[t] / O[t] - 1 >= 0.08 and C[t] > max(C[t - 26:t]) and V[t] >= 2 * np.mean(V[t - 10:t])
    return out


def _init(cal):
    D.DATA = ST; _G["cal"] = cal


def cross(args):
    """一檔：回 {週期間: (R_k dict, r4, 可買, 無壞根窗)}，只算要查的那幾週。"""
    sid, mk, weeks = args
    cal = _G["cal"]; n = len(cal)
    st = D.load_stock(sid, mk, cal)
    B = R11.load_bars(sid, mk, cal)
    if st is None or B is None:
        return sid, None
    df = st.df; c = df["close"].to_numpy(float); o = df["open"].to_numpy(float); cff = pd.Series(c).ffill().to_numpy()
    valid = np.isfinite(c); tb = TR.one(sid, cal)
    bad = np.zeros(n, bool); nb = B["next_bad"]; idx = B["idx"]; bad[idx[[k for k in range(len(idx)) if nb[k] == k]]] = True
    raw = pd.read_csv(os.path.join(ST, "stocks", sid + ".csv"), dtype={"date": str}, usecols=["date", "market"]).drop_duplicates("date")
    raw.index = pd.to_datetime(raw["date"]); mkt = raw.reindex(cal)["market"].ffill()
    per = cal.to_period("W-SUN"); TP = list(pd.unique(per))             # 有交易日的週（依序）
    res = {}
    for w0, ks in weeks:
        dw = np.flatnonzero(per == w0)
        if not valid[dw].any():
            continue
        j0 = TP.index(w0)
        dn = np.flatnonzero(per == TP[j0 + 1])
        e = dn[0]
        can = bool(tb["trd"][e] and np.isfinite(o[e]) and o[e] > 0 and not tb["up_o"][e])
        d4 = np.flatnonzero(per == TP[j0 - 4])
        r4 = cff[dw[-1]] / cff[d4[-1]] - 1 if len(d4) else np.nan
        Rk = {}
        for k in ks:
            dx = np.flatnonzero(per == TP[j0 + k]) if j0 + k < len(TP) else np.zeros(0, int)
            if not can or not len(dx) or dx[-1] >= n or bad[dw[0]:dx[-1] + 1].any():
                Rk[k] = np.nan; continue
            Rk[k] = cff[dx[-1]] / o[e] - 1
        res[str(w0)] = (Rk, r4, dw[-1], bool(mkt.iloc[dw[-1]] == "twse"))
    return sid, res


def check_a(rep):
    D.DATA = ST
    cal = D.load_calendar()
    SG = pd.read_csv(os.path.join(OUT, "甲_signals.csv.gz"), dtype={"sid": str})
    wl_of = {}
    per = cal.to_period("W-SUN")
    last_day = pd.Series(np.arange(len(cal))).groupby(per).max()
    picks = []
    for sg in ("S1", "S2", "S3", "S4"):
        g = SG[(SG["訊號"] == sg) & (SG["段"] == "確認") & np.isfinite(SG["X2_8"])].sort_values(["X2_8", "w"])
        if len(g):
            picks.append(g.iloc[len(g) // 2])
    g = SG[(SG["段"] == "早年") & np.isfinite(SG["X2_8"])].sort_values(["X2_8", "w"])
    picks.append(g.iloc[len(g) // 2])
    roster = pd.read_csv(os.path.join(ST, "meta", "stocks.csv"), dtype=str)
    mk = dict(zip(roster["stock_id"], roster["market"]))
    # 主程式的週號 ⇒ 週期間
    mon = (cal - pd.to_timedelta(cal.weekday, unit="D")).normalize(); wid = pd.factorize(mon)[0]
    wper = {int(w): per[np.flatnonzero(wid == w)[0]] for w in set(int(r["w"]) for r in picks)}
    out = []; bad_n = 0
    for r in picks:
        s = r["sid"]; W, df = wk_frame(s, mk.get(s, "twse"), cal); p0 = wper[int(r["w"])]
        B = R11.load_bars(s, mk.get(s, "twse"), cal); idx = B["idx"]; nb = B["next_bad"]
        badd = set(cal[idx[[k for k in range(len(idx)) if nb[k] == k]]].to_period("W-SUN"))
        S = sig_series(W); pos = list(W.index).index(p0)
        TP = list(pd.unique(per)); ti = {q: i for i, q in enumerate(TP)}
        nbr = lambda q: [TP[i] for i in (ti[q] - 1, ti[q], ti[q] + 1) if 0 <= i < len(TP)]
        prev = [W.index[t] for t in range(pos) if S[r["訊號"]][t] and t >= 52 and not any(q in badd for q in nbr(W.index[t]))]
        kept = []
        for q in prev:
            if not kept or ti[q] - ti[kept[-1]] > 8:
                kept.append(q)
        d = {"sid": s, "訊號": r["訊號"], "週": str(p0), "本支是訊號": bool(S[r["訊號"]][pos]), "暖機≥52": pos >= 52,
             "前後週無壞根": not any(q in badd for q in nbr(p0)), "8 週內無保留訊號": not kept or ti[p0] - ti[kept[-1]] > 8}
        out.append((r, d))
    # 基準② 重建（這 5 週的橫斷面）
    U = UG.gate3(roster); sids = sorted(set(U["stock_id"]) & {f[:-4] for f in os.listdir(os.path.join(ST, "stocks"))})
    weeks = [(wper[int(r["w"])], (4, 8, 12, 26)) for r, _ in out]
    with Pool(2, initializer=_init, initargs=(cal,)) as pool:
        CR = dict(pool.map(cross, [(s, mk.get(s, "twse"), weeks) for s in sids], chunksize=16))
    # 母體（共用 researchEvt.eligibility；需要 nbars、valid、amt）
    P = {}
    for s in sids:
        st = D.load_stock(s, mk.get(s, "twse"), cal)
        if st is None:
            continue
        v = np.isfinite(st.df["close"].to_numpy(float))
        raw = pd.read_csv(os.path.join(ST, "stocks", s + ".csv"), dtype={"date": str}, usecols=["date", "amount"]).drop_duplicates("date")
        raw.index = pd.to_datetime(raw["date"])
        P[s] = {"valid": v, "nbars": np.cumsum(v), "amt": pd.to_numeric(raw.reindex(cal)["amount"], errors="coerce").to_numpy(float)}
    ss = [s for s in sids if s in P]
    E, _ = EV.eligibility(cal, P, ss, print)
    ixs = {s: i for i, s in enumerate(ss)}
    bi = int(cal.searchsorted(pd.Timestamp("2015-01-05")))
    for r, d in out:
        p0 = wper[int(r["w"])]; key = str(p0); dl = int(last_day[p0])
        for k in (4, 8, 12, 26):
            pool = []
            for s in ss:
                v = CR.get(s)
                if v is None or key not in v:
                    continue
                Rk, r4, dlast, tw = v[key]
                if not E[ixs[s], dl] or not np.isfinite(Rk[k]) or (dl < bi and not tw):
                    continue
                pool.append((s, Rk[k], r4))
            pl = [(s, R_, r4) for s, R_, r4 in pool if np.isfinite(r4)]
            arr = np.array([x[2] for x in pl]); order = np.lexsort((np.arange(len(arr)), arr))
            dec = np.empty(len(arr), int); dec[order] = (np.arange(len(arr)) * 10) // len(arr)
            me = [i for i, x in enumerate(pl) if x[0] == r["sid"]]
            if not me:
                d[f"k{k}：本支池內找不到該股"] = True; continue
            i = me[0]; oth = [pl[j][1] for j in range(len(pl)) if dec[j] == dec[i] and j != i]
            x2 = pl[i][1] - np.mean(oth)
            d[f"k{k} R 差"] = float(abs(pl[i][1] - r[f"R{k}"])); d[f"k{k} X② 差"] = float(abs(x2 - r[f"X2_{k}"]))
        b = int(not d["本支是訊號"]) + int(not d["暖機≥52"]) + int(not d["前後週無壞根"]) + int(not d["8 週內無保留訊號"])
        b += sum(int(v > 1e-5) for k_, v in d.items() if k_.endswith("差")) + sum(1 for k_ in d if k_.endswith("找不到該股"))
        d["不符"] = b; bad_n += b
        rep["甲"].append(d); print("[甲]", json.dumps(d, ensure_ascii=False, default=str), flush=True)
    return bad_n


def check_b(rep):
    from backtest import researchWeekly as RW
    from backtest import researchYLexit3_b as YB
    Wm, We, ctx = YB.worlds(print)
    for W in (Wm, We):
        wk, wf, wl = RW.weeks_of(W["cal"]); W["WK"], W["WF"], W["WL"] = wk, wf, wl
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    pick = S["乙"]["挑中"]; L, m, C = (int(x[1:]) for x in pick.split("_"))
    RR.use_snapshot()
    sig, kinds, _ = RW.build_b(Wm, (L, m, C))
    cal = Wm["cal"]; t0c, t1c = Wm["SEGP"]["確認"]
    sg = sig.assign(類=kinds); sg = sg[(sg["entry_pos"] > t0c) & (sg["entry_pos"] <= t1c)]
    rows = list(sg[sg["類"] == "週收觸發"].iloc[[0, len(sg[sg["類"] == "週收觸發"]) // 2, -1]].itertuples()) if (sg["類"] == "週收觸發").sum() >= 3 else list(sg[sg["類"] == "週收觸發"].itertuples())
    rows += list(sg[sg["類"] == "觸頂C"].head(1).itertuples()) + list(sg[~sg["類"].isin(["週收觸發", "觸頂C"])].head(1).itertuples())
    per = cal.to_period("W-SUN"); bad_n = 0
    TP = list(pd.unique(per)); ti = {q: i for i, q in enumerate(TP)}
    for r in rows:
        s = r.sid; B = R11.load_bars(s, Wm["mk"].get(s, "twse"), cal)
        idx, o, c = B["idx"], B["o"], B["c"]; dts = cal[idx]; pw = dts.to_period("W-SUN")
        wkly = pd.Series(c, index=range(len(c))).groupby(pw).last()                     # 週收（只有有週 K 的週）
        ma = wkly.rolling(L).mean()
        ke = int(r.k) + 1; pe = pw[ke]
        trig = None
        for j in range(m, C + 1):
            if ti[pe] + j - 1 >= len(TP):
                break
            q = TP[ti[pe] + j - 1]
            if q in wkly.index and np.isfinite(ma.get(q, np.nan)) and wkly[q] < ma[q]:
                trig = q; break
        if trig is not None:
            if (pw > trig).any():
                xb = int(np.flatnonzero(pw > trig)[0]); g = o[xb] / o[ke] - 1; kind = "週收觸發"
            else:                                                                  # 觸發後已無 K 棒 ⇒ 資料尾（B4）
                xb = len(idx) - 1; g = c[xb] / o[ke] - 1
                kind = "T1 補" if int(idx[-1]) == len(cal) - 1 else "停止交易（引擎 stop_force）"
        elif ti[pe] + C - 1 >= len(TP):                                           # 第 C 週超出日曆 ⇒ 資料尾（B4）
            xb = len(idx) - 1; g = c[xb] / o[ke] - 1
            kind = "T1 補" if int(idx[-1]) == len(cal) - 1 else "停止交易（引擎 stop_force）"
        else:
            q = TP[ti[pe] + C - 1]; cand = np.flatnonzero(pw <= q); xb = int(cand[-1]); g = c[xb] / o[ke] - 1; kind = "觸頂C"
        nbk = B["next_bad"][ke]
        if xb is not None and xb >= nbk and nbk - 1 >= ke and nbk <= len(idx) - 1:
            xb = nbk - 1; g = c[xb] / o[ke] - 1; kind = "壞根前出"
        xpos = int(idx[xb]) if xb is not None else None
        if kind in ("T1 補", "停止交易（引擎 stop_force）"):
            xpos = len(cal)                                                        # T1 補：xpos ＝ ncal、末日收盤計
        d = {"sid": s, "進場": str(cal[int(r.entry_pos)].date()), "本支類": kind, "主程式類": r.類, "本支 xpos": xpos, "主程式 xpos": int(r.xpos_W),
             "g 差": float(abs(g - r.g_W)) if np.isfinite(g) else None}
        b = int(kind != r.類) + int(xpos != int(r.xpos_W)) + int(d["g 差"] is None or d["g 差"] > 1e-9)
        d["不符"] = b; bad_n += b
        rep["乙"].append(d); print("[乙]", json.dumps(d, ensure_ascii=False, default=str), flush=True)
    return bad_n


def main():
    rep = {"甲": [], "乙": []}
    if "--only-b" in sys.argv:                                                  # 乙重跑時沿用上一輪甲的結果
        old = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")); rep["甲"] = old["甲"]
        b1 = sum(d["不符"] for d in old["甲"])
    else:
        b1 = check_a(rep)
    b2 = check_b(rep)
    rep["合計不符"] = b1 + b2
    json.dump(rep, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("合計不符", b1 + b2)


if __name__ == "__main__":
    main()
