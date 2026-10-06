# -*- coding: utf-8 -*-
"""USREG-A1-4 反轉訊號（移植台股 大盤高低點反轉訊號 seq3，sha d868b4e3bde64203；事件研究；大盤層 SPY＋個股層 S&P 500＋400）。

    PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSA1 a4 [--procs 3]

⭐ 偵測、合併、確認、報酬、出口一律 import 台股原件（researchRev 502cf9761f 的 detect／merge20／confirm_day／fwd／base_days／succ、
   researchRev_win 的 judge／stability、avgdown 的 r20_cal／deciles、researchM_freq._g5）⇒ 同一件事只一份實作；本檔只換資料與窗。
判定：視窗 {5, 10, 20, 60} 判（seq3 §九）；120、240 日描述（依構造多半只能出口①，事前寫明）；兩版（原版、加確認）；
      Bonferroni α ＝ 0.05／k，k ＝ 該層「訊號 × 版本 × 視窗」可判定格（n_eff ≥ 10）照實算；N_前段 ＝ 兩層 k 合計（裁定 seq309：照可判定格數實計）。
      通過 ＝ 高點 結果③（CI 全 ＜ 0）、低點 結果②（CI 全 ＞ 0）；扣成本版 ＝ X 往不利方向移 0.05%（美股來回成本；台股 0.585%）。
      穩不穩（裁定 seq249 讀法）照 researchRev_win.stability。事件研究 ⇒ 照舊用固定 H（裁定 seq308 §四④）。

══ 執行者補讀法（⭐ 2026-10-07 台北 02:40 寫死於看任何 A1 數字之前）══
 R1 訊號 21 種（⚠ 登錄寫「高點 12／低點 12、個股 24 種全收」）：頭肩頂、2B 頂、2B 底 本專案沒有機器定義 ⇒ 不收（同台股裁定 seq226「無定義不收」）⇒ 高 10＋低 11；
    外資、融資本來就不在清單 ⇒ 兩層同為 21 種。⭐ 偏離登錄字面，交件列明。
 R2 大盤層：SPY 還原 OHLC（Yahoo 原始 × adjclose÷close）、K 棒型態的「原始價等式」用 Yahoo 原始 OHLC；主窗 2007-04-02～2026-09-30；
    早年描述 1993-01-29（SPY 首日）～2007-03-30（只用 SPY，⛔ 不接指數）；對照 ＝ 同窗所有交易日的 R_H 平均；CI 以 20 日區段分群（台股原件）。
 R3 個股層母體 ＝ S&P 500 ∪ S&P 400 point-in-time：訊號日 T 當天在任一指數（面板 in_index＝1）；價格照面板每列 src 取檔
    （yahoo 還原同 D2；tiingo 用 adj*、原始價等式用未還原 open／high／low／close、量用 adjVolume）；同一天兩個面板都有列 ⇒ 取 S&P 500 面板的 src。
    窗 ＝ 2016-01-04～2026-09-30（⚠ 面板 2015-12 起 ⇒ 個股層無 2007～2015；與大盤層主窗不同，照標）。
 R4 個股層硬斷點 ＝ 來源接縫（相鄰兩根 src 不同）、同日拆股＋配息（src 帶 * 或兩個 _report.md 那一節）、ret_blank 列的日子（資料庫標的假報酬）、
    連續缺 ≥ 5 日（researchM_freq._g5；最後一根之後不算缺 ＝ 台股「下市 on」：持有期跨下市 ⇒ 用最後一根收盤）；
    [first, T＋H] 有斷點 ⇒ 剔除；T＋1 沒有 K 棒 ⇒ 剔除_停牌（美股沒有漲跌停 ⇒ 開盤漲跌停閘不適用）。
 R5 個股層基準②：同一天在母體、有效 K 棒、T＋1 有開盤、[d, d＋H] 無斷點的股日，依前 20 根報酬（avgdown.r20_cal）當天橫斷面十分位 ⇒
    同月同十分位的 R_H 平均；X ＝ R_H − 基準②；CI 以基準日曆月分群；基準① ＝ 同月全部股日。
 R6 假訊號臂：大盤層可判定格（4 個判定視窗）同事件數隨機日 1,000 次（種子 20260927，台股原件）⇒ 隨機也過的比例（描述）；個股層照台股原件不跑。
"""
from __future__ import annotations

import json
import os
import sys
import time
from multiprocessing import Pool
from statistics import NormalDist

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchRev as RV                    # noqa: E402
import researchRev_win as RW                # noqa: E402
from backtest import researchUSA1_data as A  # noqa: E402

AV, MF = RV.AV, RV.MF
HS_J = (5, 10, 20, 60)
HS_D = (120, 240)
HS = HS_J + HS_D
STK0 = "2016-01-04"
EARLY0 = "1993-01-29"
FAKE_N = 1000
_G: dict = {}


def zb(k):
    return NormalDist().inv_cdf(1 - (0.05 / max(k, 1)) / 2)


# ═════════════ 大盤層 ═════════════
def spy_series(M):
    k = "SPY"
    X = {"dates": M["cal"], "o": M["O"][k], "h": M["H"][k], "l": M["L"][k], "c": M["C"][k], "v": M["V"][k],
         "ro": M["RO"][k], "rh": M["RH"][k], "rl": M["RL"][k], "rc": M["RC"][k]}
    X["valid"] = np.isfinite(X["c"]); X["bars"] = np.flatnonzero(X["valid"]); X["lv"] = AV.last_valid(X["valid"])
    return X


def market_cells(M, log):
    X = spy_series(M)
    ev = RV.detect_series(X)
    g_up, n_up = RV.gate_upline(X["o"][X["bars"]], X["l"][X["bars"]], X["c"][X["bars"]])
    pos = M["pos"]
    segs = {"主窗": (pos[A.EXP[0]], pos[A.CONF[1]]), "早年": (pos[EARLY0], pos[A.EARLY_END])}
    cells, evrows, base_info = [], [], {}
    for seg, (lo, hi) in segs.items():
        for H in HS:
            bd = RV.base_days(X, lo, hi, H)
            base = np.array([RV.fwd(X, d, H, hi) for d in bd]); bm = float(base.mean())
            base_info[f"{seg}_H{H}"] = {"R平均": bm, "日數": int(len(base)), "跌比例": float((base < 0).mean()), "漲比例": float((base > 0).mean())}
            for code in RV.CODES:
                top = RV.SIDE[code] == "高"
                T = np.array([t for t, _ in ev[code]], int); F = np.array([f for _, f in ev[code]], int)
                m = (T >= lo) & (T <= hi - H); T, F = T[m], F[m]
                keep = RV.merge20(T)
                E = []
                for t, f, kk in zip(T, F, keep):
                    if not kk:
                        continue
                    st = "保留" if np.isfinite(X["o"][t + 1]) else "剔除_停牌"
                    C = RV.confirm_day(X["c"], X["valid"], X["h"][t], X["l"][t], t, top, hi)
                    stc = "沒確認" if C < 0 else ("窗外" if C + H > hi else ("保留" if np.isfinite(X["o"][C + 1]) else "剔除_停牌"))
                    E.append((t, C, st, stc))
                for ver in ("原版", "確認版"):
                    b = np.array([t for t, C, st, stc in E if st == "保留"] if ver == "原版" else [C for t, C, st, stc in E if stc == "保留"], int)
                    R = np.array([RV.fwd(X, d, H, hi) for d in b])
                    for d, r in zip(b, R):
                        evrows.append({"段": seg, "code": code, "版": ver, "H": H, "基準日": X["dates"][d], "R": r})
                    row = {"層": "大盤", "段": seg, "code": code, "名": RV.NAME[code], "邊": RV.SIDE[code], "版": ver, "H": H, "_X": R - bm, "_g": (b - lo) // 20, "_b": b,
                           "成功率": RV.succ(code, R) if len(R) else np.nan, "基準成功率": RV.succ(code, base), "R平均": float(R.mean()) if len(R) else np.nan,
                           "基準R平均": bm, "候選事件（窗內、合併後）": int(keep.sum())}
                    if ver == "確認版":
                        orig = [t for t, C, st, stc in E if st == "保留"]
                        unc = [t for t, C, st, stc in E if st == "保留" and C < 0]
                        Ru = np.array([RV.fwd(X, d, H, hi) for d in unc])
                        row.update({"沒確認比例": len(unc) / max(1, len(orig)), "放棄組R平均": float(Ru.mean()) if len(Ru) else np.nan})
                    cells.append(row)
    return cells, evrows, base_info, {"上升線鏡像(num=100)＝trendline_m取負": bool(g_up), "事件數": int(n_up)}, X, segs


# ═════════════ 個股層 ═════════════
def _report_days(panel_dir):
    out, on = set(), False
    for line in open(A.p_(panel_dir, "_report.md"), encoding="utf-8"):
        if line.startswith("## "):
            on = "同一天拆股" in line
            continue
        if on and line.startswith("- "):
            p = line[2:].split()
            if len(p) >= 2:
                out.add((p[0], p[1][:10]))
    return out


def _src_frame(src):
    kind, f = src.split(":", 1)
    if kind == "yahoo":
        d = pd.read_csv(A.p_("prices_yahoo", f + ".csv"), dtype={"date": str})
        k = d["adjclose"] / d["close"]
        o = pd.DataFrame({"o": d["open"] * k, "h": d["high"] * k, "l": d["low"] * k, "c": d["close"] * k, "v": d["volume"],
                          "ro": d["open"], "rh": d["high"], "rl": d["low"], "rc": d["close"]})
        chk = d[["open", "high", "low", "close", "adjclose"]]
    else:
        d = pd.read_csv(A.p_("prices", f + ".csv"), dtype={"date": str})
        o = pd.DataFrame({"o": d["adjOpen"], "h": d["adjHigh"], "l": d["adjLow"], "c": d["adjClose"], "v": d["adjVolume"],
                          "ro": d["open"], "rh": d["high"], "rl": d["low"], "rc": d["close"]})
        chk = d[["adjOpen", "adjHigh", "adjLow", "adjClose"]]
    o.index = d["date"].to_numpy(str)
    ok = chk.notna().all(axis=1).to_numpy() & (chk > 0).all(axis=1).to_numpy()
    o = o[ok].astype(float)
    return o[~o.index.duplicated()]


def stock_series(t, cal):
    """R3：兩個面板合併 ⇒ 日曆長度的 o,h,l,c,v,ro..rc、member、src、star。"""
    parts = []
    for tag, d in (("500", "panel"), ("400", "panel_sp400")):
        p = A.p_(d, t + ".csv")
        if os.path.exists(p):
            x = pd.read_csv(p, dtype={"date": str, "src": str}, keep_default_na=False)
            x["idx"] = tag
            parts.append(x)
    if not parts:
        return None
    P = pd.concat(parts, ignore_index=True)
    P["in_index"] = pd.to_numeric(P["in_index"], errors="coerce").fillna(0).astype(int)
    mem = P.groupby("date")["in_index"].max()
    P["_o"] = P["idx"].map({"500": 0, "400": 1})
    P = P.sort_values(["date", "_o"]).drop_duplicates("date", keep="first")
    P = P.set_index("date")
    P["star"] = P["src"].str.endswith("*"); P["src0"] = P["src"].str.rstrip("*")
    n = len(cal); pos = _G["pos"]
    arr = {k: np.full(n, np.nan) for k in ("o", "h", "l", "c", "v", "ro", "rh", "rl", "rc")}
    srcs = np.array([""] * n, dtype=object); star = np.zeros(n, bool); member = np.zeros(n, bool)
    for s, g in P.groupby("src0", sort=False):
        fr = _src_frame(s)
        dd = [x for x in g.index if x in pos and x in fr.index]
        if not dd:
            continue
        ii = np.array([pos[x] for x in dd])
        for k in arr:
            arr[k][ii] = fr.loc[dd, k].to_numpy(float)
        srcs[ii] = s
    for x, v in mem.items():
        if x in pos:
            member[pos[x]] = v == 1
    for x in P.index[P["star"].to_numpy()]:
        if x in pos:
            star[pos[x]] = True
    return arr, srcs, star, member


def stock_one(t):
    cal, w0, w1 = _G["cal"], _G["w0"], _G["w1"]
    r = stock_series(t, cal)
    if r is None:
        return None
    arr, srcs, star, member = r
    o, h, l, c, v = arr["o"], arr["h"], arr["l"], arr["c"], arr["v"]
    valid = np.isfinite(c) & np.isfinite(o); bars = np.flatnonzero(valid)
    if len(bars) < 30:
        return None
    c = np.where(valid, c, np.nan)
    sel = lambda x: np.asarray(x, float)[bars]
    ev = RV.detect(sel(o), sel(h), sel(l), c[bars], sel(v), sel(arr["ro"]), sel(arr["rh"]), sel(arr["rl"]), sel(arr["rc"]))
    n = len(cal)
    pb = np.zeros(n, bool)
    sb = srcs[bars]; pb[bars[1:][sb[1:] != sb[:-1]]] = True
    pb |= star
    for (tk, d) in _G["sd"]:
        if tk == t and d in _G["pos"]:
            pb[_G["pos"][d]] = True
    for d in _G["blank"].get(t, ()):
        if d in _G["pos"]:
            pb[_G["pos"][d]] = True
    g5 = MF._g5(valid, upto=int(bars[-1]))
    g5[:bars[0]] = False
    S = {"cs_pb": np.cumsum(pb).astype(np.int32), "cs_g5": np.cumsum(g5).astype(np.int32)}
    lv = AV.last_valid(valid)
    halt = ~valid

    def brk(a, b):
        return bool(AV.brk_vec(S["cs_pb"], S["cs_g5"], a, b)[0])
    rows = []
    for code in RV.CODES:
        top = RV.SIDE[code] == "高"
        if not ev[code]:
            continue
        T0 = bars[np.array([x for x, _ in ev[code]], int)]; F0 = bars[np.array([f for _, f in ev[code]], int)]
        for H in HS:
            m = (T0 >= w0) & (T0 <= w1 - H)
            T, F = T0[m], F0[m]
            if len(T):
                m2 = member[T]; T, F = T[m2], F[m2]
            keep = RV.merge20(T)
            for tt, f, k in zip(T, F, keep):
                if not k:
                    continue
                rr = {"sid": t, "code": code, "H": H, "T": int(tt), "first": int(f)}
                rr["st"] = "剔除_硬斷點" if brk(int(f), int(tt) + H) else ("剔除_停牌" if halt[tt + 1] else "保留")
                C = RV.confirm_day(c, valid, h[tt], l[tt], int(tt), top, w1)
                rr["C"] = int(C)
                if C >= 0:
                    rr["st_c"] = "窗外" if C + H > w1 else ("剔除_硬斷點" if brk(int(f), int(C) + H) else ("剔除_停牌" if halt[C + 1] else "保留"))
                else:
                    rr["st_c"] = "沒確認"
                if rr["st"] == "保留":
                    rr["R"] = float(c[lv[tt + H]] / o[tt + 1] - 1.0)
                if rr["st_c"] == "保留":
                    rr["Rc"] = float(c[lv[C + H]] / o[C + 1] - 1.0)
                rows.append(rr)
    dd = np.arange(w0, w1 - HS[0] + 1)
    dd = dd[member[dd]]
    days = {"d": dd.astype(np.int32), "r20p": AV.r20_cal(c, bars)[dd]}
    for H in HS:
        R = np.full(len(dd), np.nan)
        mm = dd + H <= w1
        if mm.any():
            d_ = dd[mm]
            ok = valid[d_] & ~halt[d_ + 1] & ~AV.brk_vec(S["cs_pb"], S["cs_g5"], d_, d_ + H)
            with np.errstate(invalid="ignore", divide="ignore"):
                Rall = c[lv[d_ + H]] / o[d_ + 1] - 1.0
            R[mm] = np.where(ok, Rall, np.nan)
        days[f"R{H}"] = R
    return {"sid": t, "rows": rows, "days": days, "gate": RV.gate_upline(sel(o), sel(l), c[bars])}


def _init(d):
    _G.update(d)


def stock_cells(M, procs, limit, log):
    cal = M["cal"]; pos = M["pos"]
    w0, w1 = pos[STK0], pos[A.CONF[1]]
    u5 = pd.read_csv(A.p_("membership", "universe.csv"), dtype=str)["ticker"].tolist()
    u4 = pd.read_csv(A.p_("membership_sp400", "universe.csv"), dtype=str)["ticker"].tolist()
    tick = sorted(set(u5) | set(u4))
    if limit:
        tick = tick[:limit]
    sd = _report_days("panel") | _report_days("panel_sp400")
    blank = {}
    for f in (A.p_("membership", "ret_blank.csv"), A.p_("membership_sp400", "ret_blank.csv")):
        if os.path.exists(f):
            b = pd.read_csv(f, dtype=str)
            for tk, d in zip(b["file_ticker"], b["date"]):
                blank.setdefault(tk, set()).add(d)
    init = {"cal": cal, "pos": pos, "w0": w0, "w1": w1, "sd": sd, "blank": blank}
    res = []; t0 = time.time()
    with Pool(procs, initializer=_init, initargs=(init,)) as pool:
        for i, r in enumerate(pool.imap_unordered(stock_one, tick, chunksize=4)):
            if r is not None:
                res.append(r)
            if (i + 1) % 300 == 0:
                log(f"  [A1-4 個股] {i + 1}/{len(tick)}｜{time.time() - t0:.0f}s")
    rows = pd.DataFrame([r for x in res for r in x["rows"]])
    mon = np.array([d[:7] for d in cal])
    DD = pd.concat([pd.DataFrame({"sid": x["sid"], **x["days"]}) for x in res if len(x["days"]["d"])], ignore_index=True).sort_values(["d", "sid"]).reset_index(drop=True)
    dec = np.full(len(DD), -1, int)
    for d, idx in DD.groupby("d").indices.items():
        dec[idx] = AV.deciles(DD["r20p"].to_numpy()[idx])
    DD["dec"] = dec; DD["m"] = mon[DD["d"].to_numpy()]
    key = {(s, int(d)): int(q) for s, d, q in zip(DD["sid"], DD["d"], DD["dec"])}
    cells = []; info = {"母體檔數（S&P500∪400）": len(tick), "有資料檔數": len(res), "股日": int(len(DD)),
                        "上升線閘不一致檔數": int(sum(1 for x in res if not x["gate"][0])), "窗": [cal[w0], cal[w1]]}
    stk_ev = []
    for H in HS:
        f = DD[np.isfinite(DD[f"R{H}"]) & (DD["dec"] >= 0)]
        B2 = f.groupby(["m", "dec"])[f"R{H}"].mean()
        B1 = DD[np.isfinite(DD[f"R{H}"])].groupby("m")[f"R{H}"].mean()
        sneg = f.assign(x=f[f"R{H}"] < 0).groupby(["m", "dec"])["x"].mean(); spos = f.assign(x=f[f"R{H}"] > 0).groupby(["m", "dec"])["x"].mean()
        info[f"基準_H{H}"] = {"有報酬股日": int(np.isfinite(DD[f"R{H}"]).sum()), "R平均": float(np.nanmean(DD[f"R{H}"]))}
        e = rows[rows["H"] == H] if len(rows) else rows
        for code in RV.CODES:
            ec = e[e["code"] == code] if len(e) else e
            for ver in ("原版", "確認版"):
                k = ec[ec["st"] == "保留"] if ver == "原版" else ec[ec["st_c"] == "保留"]
                bd = k["T"].to_numpy(int) if ver == "原版" else k["C"].to_numpy(int)
                R = k["R"].to_numpy(float) if ver == "原版" else k["Rc"].to_numpy(float)
                mm = mon[bd] if len(bd) else np.zeros(0, str)
                q = [key.get((s, int(d)), -1) for s, d in zip(k["sid"], bd)]
                b2 = np.array([B2.get((m_, qq), np.nan) if qq >= 0 else np.nan for m_, qq in zip(mm, q)], float)
                b1 = np.array([B1.get(m_, np.nan) for m_ in mm], float)
                sn = np.array([(sneg if RV.SIDE[code] == "高" else spos).get((m_, qq), np.nan) if qq >= 0 else np.nan for m_, qq in zip(mm, q)], float)
                ok = np.isfinite(b2)
                row = {"層": "個股", "段": "主窗", "code": code, "名": RV.NAME[code], "邊": RV.SIDE[code], "版": ver, "H": H, "_X": R[ok] - b2[ok], "_g": mm[ok],
                       "成功率": RV.succ(code, R[ok]) if ok.any() else np.nan, "基準成功率": float(sn[ok].mean()) if ok.any() else np.nan,
                       "R平均": float(R[ok].mean()) if ok.any() else np.nan, "基準R平均": float(b2[ok].mean()) if ok.any() else np.nan,
                       "基準1R平均": float(np.nanmean(b1)) if len(b1) else np.nan, "候選事件（窗內、合併後）": int(len(ec)), "基準2缺": int((~ok).sum()),
                       "剔除_硬斷點": int((ec["st"] == "剔除_硬斷點").sum()) if len(ec) else 0, "剔除_停牌": int((ec["st"] == "剔除_停牌").sum()) if len(ec) else 0}
                if ver == "確認版" and len(ec):
                    orig = ec[ec["st"] == "保留"]; unc = orig[orig["C"] < 0]
                    row.update({"沒確認比例": len(unc) / max(1, len(orig)), "放棄組R平均": float(unc["R"].mean()) if len(unc) else np.nan})
                cells.append(row)
                if len(k) and H in HS_J:
                    kk = k.assign(版=ver, b2=np.where(ok, b2, np.nan))
                    stk_ev.append(kk[["sid", "code", "版", "H", "T", "C", "R", "Rc", "b2"]] if "Rc" in kk else kk)
    return cells, info, (pd.concat(stk_ev, ignore_index=True) if stk_ev else pd.DataFrame()), DD


def judge_layer(cells, lay, log):
    J = [c for c in cells if c["層"] == lay and c["段"] == "主窗"]
    for c in J:
        c["n_eff"] = int(min(len(c["_X"]), len(np.unique(c["_g"])))) if len(c["_X"]) else 0
    k = sum(1 for c in J if c["H"] in HS_J and c["n_eff"] >= RV.NEFF_MIN)
    z = zb(k)
    RW.COST = A.COST                                     # 扣成本：美股 0.05%（台股原件 0.585%）
    for c in J:
        if c["H"] in HS_J:
            c.update(RW.judge(c["code"], c["_X"], c["_g"], z)); c["事件"] = int(len(c["_X"]))
        else:                                            # 描述：95% CI、⛔ 不判
            X = np.asarray(c["_X"], float); c["事件"] = int(len(X))
            if len(X) >= 2:
                m, se, ng = AV.cr0(X, np.asarray(c["_g"]))
                c.update(mean=m, se=se, lo=m - 1.96 * se, hi=m + 1.96 * se, 判定="描述（不判）")
            else:
                c.update(mean=float(X.mean()) if len(X) else np.nan, 判定="描述（不判）")
    log(f"  [A1-4 {lay}] Bonferroni k＝{k}、z＝{z:.3f}")
    return {"k": k, "α": 0.05 / max(k, 1), "z": z, "k 的算法": "訊號 × 版本 × 視窗{5,10,20,60} 的可判定格（n_eff ≥ 10）"}


def run_a4(M, procs, limit, log):
    t0 = time.time()
    cells, evm, binfo, gate, X, segs = market_cells(M, log)
    log(f"  [A1-4 大盤] 閘 {gate}｜{time.time() - t0:.0f}s")
    BF = {"大盤": judge_layer(cells, "大盤", log)}
    for c in cells:
        if c["段"] == "早年":
            Xx = np.asarray(c["_X"], float); c["事件"] = int(len(Xx))
            c["n_eff"] = int(min(len(Xx), len(np.unique(c["_g"])))) if len(Xx) else 0
            c["mean"] = float(Xx.mean()) if len(Xx) else np.nan; c["判定"] = "描述（不判）"
    # 假訊號臂（R6）
    rng = np.random.default_rng(20260927)
    lo, hi = segs["主窗"]
    for H in HS_J:
        bd = RV.base_days(X, lo, hi, H); base = np.array([RV.fwd(X, d, H, hi) for d in bd]); bm = float(base.mean())
        for c in cells:
            if c["層"] != "大盤" or c["段"] != "主窗" or c["H"] != H or c.get("n_eff", 0) < RV.NEFF_MIN:
                continue
            n = c["事件"]; passed = 0
            for _ in range(FAKE_N):
                ii = np.sort(rng.choice(len(bd), size=n, replace=False))
                r = RW.judge(c["code"], base[ii] - bm, (bd[ii] - lo) // 20, BF["大盤"]["z"])
                passed += r["判定"] == "通過"
            c["假訊號過的比例"] = passed / FAKE_N
    scells, sinfo, sev, DD = stock_cells(M, procs, limit, log)
    cells += scells
    BF["個股"] = judge_layer(cells, "個股", log)
    C = pd.DataFrame([{k: v for k, v in c.items() if not k.startswith("_")} for c in cells])
    Cj = C[(C["段"] == "主窗") & (C["H"].isin(HS_J))].copy()
    stab = RW.stability(Cj)
    C["穩不穩"] = [stab.get((r.層, r.code, r.版), "") if r.段 == "主窗" else "" for r in C.itertuples()]
    os.makedirs(A.OUT, exist_ok=True); os.makedirs(A.WORK, exist_ok=True)
    C.to_csv(os.path.join(A.OUT, "A4_cells.csv"), index=False, encoding="utf-8")
    p1 = os.path.join(A.WORK, "a4_events_market.csv"); pd.DataFrame(evm).to_csv(p1, index=False)
    p2 = os.path.join(A.WORK, "a4_events_stock.csv.gz"); sev.to_csv(p2, index=False)
    p3 = os.path.join(A.WORK, "a4_stock_days.csv.gz"); DD.to_csv(p3, index=False)
    Pm = C[(C["層"] == "大盤") & (C["段"] == "主窗") & (C["判定"] == "通過")]
    Ps = C[(C["層"] == "個股") & (C["判定"] == "通過")]
    S = {"件": "USREG-A1-4 反轉訊號", "登錄": "USREG-A1 seq1 件四（移植 大盤高低點反轉訊號 seq3 sha d868b4e3bde64203）",
         "N_前段（照可判定格數實計）": int(BF["大盤"]["k"] + BF["個股"]["k"]), "Bonferroni": BF, "大盤閘": gate, "大盤基準": binfo, "個股": sinfo,
         "大盤窗": {k: [M["cal"][a], M["cal"][b]] for k, (a, b) in segs.items()},
         "通過_大盤": [f"{r.名}｜{r.版}｜{r.H}天" for r in Pm.itertuples()], "通過_個股": [f"{r.名}｜{r.版}｜{r.H}天" for r in Ps.itertuples()],
         "第三層（給 A1-5）": sorted({(r.code, r.版) for r in Pm.itertuples()}), "母體限制": A.LIMITS_SP400,
         "私有檔sha（repo外 ~/us_work/usa1/）": {os.path.basename(p): A.sha256f(p) for p in (p1, p2, p3)}, "秒": round(time.time() - t0)}
    json.dump(S, open(os.path.join(A.OUT, "A4_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[A1-4] N_前段 {S['N_前段（照可判定格數實計）']}｜通過 大盤 {S['通過_大盤']}｜個股 {S['通過_個股']}｜{S['秒']}s")
    return S
