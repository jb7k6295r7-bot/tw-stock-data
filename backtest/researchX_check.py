# -*- coding: utf-8 -*-
"""PREREGX 硬性查核（另一條路手算）：⛔ 不 import data.load_stock／patterns_x／researchX 的任何計算函式。

 K1 抽 20 筆 甲 事件（每型 4 筆，種子 1）：直接讀快照 data/stocks/<代號>.csv 原始價 ＋ data/adj 的 factor 欄自己連乘還原
    （⛔ 不用 cum_factor 欄），依【日期】取點：由型態取點日期重算目標價、目標距離％、T+1..T+H 的最高價 ⇒ 事件達成（H60、H120）；
    對照股同法 ⇒ 對照目標與達成。與 resultsX/A_<型>.csv.gz 逐欄比。
 K2 抽 20 筆 乙 S（每型 3～4 筆，種子 2）：同一條讀價路徑算 20 日報酬 R；EW20 另從 gate3 全部股票原始檔重算；X ＝ R − 0.585% − EW。
    若結局＝破壞：破壞日收盤 ＜ 破壞位，且 S+1～破壞日前一天收盤都 ≥ 破壞位。
 K3 對照組抽樣另寫一支（小樣本 30 筆 甲 事件，種子 3）：T 日全部 gate3 股票的 20 日波動（自己算）⇒ pandas rank(method='first')
    ⇒ 十分位 ⌊(名次−1)×10／N⌋；池 ＝ 同十分位 ∧ T 日無原始觸發（raw_triggers）∧ T+1 有成交、有開盤、非開盤漲停（tradability.one）
    ∧ (T, T+120] 無價格斷點（自己寫：相鄰成交日收盤比 ≤0.55／≥1.8 且其間無 adj 事件）∧ 無連續 ≥5 日無成交 ∧ 不是事件股
    ⇒ 池大小＝pool_n、且對照股＝排序後池的第 pool_k 個。

    ~/tw-p16/.venv/bin/python backtest/researchX_check.py
"""
from __future__ import annotations
import json
import os
import sys

import numpy as np
import pandas as pd

SNAP = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
OUT = os.path.expanduser("~/tw-p17/backtest/resultsX")
sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import universe_gate as UG      # noqa: E402  只拿 gate3 名單
from backtest import data as Dm               # noqa: E402
Dm.DATA = SNAP
from backtest import tradability as TR        # noqa: E402  只拿開盤漲停旗標（K3）

CAL = pd.DatetimeIndex(pd.to_datetime(pd.read_csv(os.path.join(SNAP, "meta", "calendar_twse.csv"))["date"])).sort_values()
POS = {d: i for i, d in enumerate(CAL)}
_cache = {}


def px(sid):
    """原始價 × 自己連乘的還原因子（事件日嚴格大於 d 的 factor 連乘），依日期索引、只含有成交日。"""
    if sid in _cache:
        return _cache[sid]
    r = pd.read_csv(os.path.join(SNAP, "stocks", f"{sid}.csv"), dtype={"date": str}, usecols=["date", "open", "high", "low", "close"])
    r["date"] = pd.to_datetime(r["date"]); r = r.drop_duplicates("date").set_index("date").sort_index()
    for k in ("open", "high", "low", "close"):
        r[k] = pd.to_numeric(r[k], errors="coerce")
    bad = (r[["open", "high", "low", "close"]] <= 0).any(axis=1)
    r.loc[bad, ["open", "high", "low", "close"]] = np.nan
    p = os.path.join(SNAP, "adj", f"{sid}.csv")
    F = np.ones(len(r))
    ev = []
    if os.path.exists(p):
        a = pd.read_csv(p, dtype={"date": str}); a["date"] = pd.to_datetime(a["date"])
        ev = list(a["date"])
        for d, fct in zip(a["date"], a["factor"].astype(float)):
            F[r.index < d] *= fct
    for k in ("open", "high", "low", "close"):
        r[k] = r[k] * F
    r = r[r.index.isin(CAL)]
    r = r[np.isfinite(r["close"])]
    _cache[sid] = (r, ev)
    return _cache[sid]


def cal_after(d, k):
    return CAL[POS[pd.Timestamp(d)] + k]


def hmax(sid, T, H):
    r, _ = px(sid)
    seg = r.loc[(r.index > pd.Timestamp(T)) & (r.index <= cal_after(T, H)), "high"]
    return float(seg.max()) if seg.notna().any() else np.nan


def close_on(sid, d):
    r, _ = px(sid); return float(r.loc[pd.Timestamp(d), "close"])


def target_indep(typ, sid, T, pts):
    r, _ = px(sid); c = r["close"]
    P_ = {k: pd.Timestamp(v) for k, v in pts.items()}
    if typ == "w":
        cA = c[P_["A"]]; m = min(c[P_["L1"]], c[P_["L2"]]); return cA + (cA - m)
    if typ == "hs":
        neck = (c[P_["A1"]] + c[P_["A2"]]) / 2; return neck + (neck - c[P_["H"]])
    if typ == "flag":
        face = c[(c.index > P_["E"]) & (c.index < pd.Timestamp(T))]
        return face.max() + (c[P_["E"]] - c[P_["S0"]])
    if typ == "cup":
        o1 = float(r.loc[cal_after(T, 1), "open"]); return o1 + (c[P_["L"]] - c[P_["B"]])
    if typ == "box":
        sig = cal_after(T, -2)
        w = r[(r.index >= cal_after(sig, -20)) & (r.index < sig)]
        top = np.maximum(w["open"], w["close"]).max(); bot = np.minimum(w["open"], w["close"]).min()
        return top + (top - bot)


def k1():
    rng = np.random.default_rng(1)
    rows = []
    for typ in ("box", "cup", "w", "hs", "flag"):
        A = pd.read_csv(os.path.join(OUT, f"A_{typ}.csv.gz"), dtype={"sid": str, "ctl": str})
        for i in rng.choice(len(A), size=min(4, len(A)), replace=False):
            e = A.iloc[int(i)]
            tg = target_indep(typ, e["sid"], e["date"], json.loads(e["pts"])) if typ != "box" else target_indep(typ, e["sid"], e["date"], {})
            dist = tg / close_on(e["sid"], e["date"]) - 1
            tc = close_on(e["ctl"], e["date"]) * (1 + dist)
            row = {"型": typ, "sid": e["sid"], "T": e["date"], "目標_程式": e["target"], "目標_手算": tg,
                   "對照": e["ctl"], "對照目標_程式": e["ctl_target"], "對照目標_手算": tc}
            ok = abs(tg / e["target"] - 1) < 1e-6 and abs(tc / e["ctl_target"] - 1) < 1e-6
            for H in (60, 120):
                s_ = int(hmax(e["sid"], e["date"], H) >= tg); c_ = int(hmax(e["ctl"], e["date"], H) >= tc)
                row[f"達成{H}_程式"] = int(e[f"sig_{H}"]); row[f"達成{H}_手算"] = s_
                row[f"對照{H}_程式"] = int(e[f"ctl_{H}"]); row[f"對照{H}_手算"] = c_
                ok &= (s_ == e[f"sig_{H}"]) and (c_ == e[f"ctl_{H}"])
            row["相符"] = bool(ok); rows.append(row)
    return pd.DataFrame(rows)


def ew_indep(dates, sids):
    num = {pd.Timestamp(d): 0.0 for d in dates}; den = {pd.Timestamp(d): 0 for d in dates}
    for s in sids:
        try:
            r, _ = px(s)
        except FileNotFoundError:
            continue
        if r.empty:
            continue
        for d in dates:
            d = pd.Timestamp(d)
            if d not in r.index or not np.isfinite(r.loc[d, "open"]) or r.loc[d, "open"] <= 0:
                continue
            end = cal_after(d, 19)
            cc = r.loc[(r.index <= end), "close"]
            if cc.empty:
                continue
            num[d] += cc.iloc[-1] / r.loc[d, "open"] - 1; den[d] += 1
    return {d: num[pd.Timestamp(d)] / den[pd.Timestamp(d)] for d in dates}


def k2(sids):
    rng = np.random.default_rng(2)
    pick = []
    for typ, k in (("box", 4), ("cup", 3), ("w", 3), ("hs", 3), ("flag", 3), ("trend", 4)):
        B = pd.read_csv(os.path.join(OUT, f"B_{typ}.csv.gz"), dtype={"sid": str})
        for i in rng.choice(len(B), size=min(k, len(B)), replace=False):
            pick.append((typ, B.iloc[int(i)]))
    d1 = sorted({str(cal_after(b["date"], 1).date()) for _, b in pick})
    EW = ew_indep(d1, sids)
    rows = []
    for typ, b in pick:
        r, _ = px(b["sid"])
        e1 = cal_after(b["date"], 1); e20 = cal_after(b["date"], 20)
        R_ = r.loc[r.index <= e20, "close"].iloc[-1] / r.loc[e1, "open"] - 1
        X = R_ - 0.00585 - EW[str(e1.date())]
        ok = abs(R_ - b["R"]) < 1e-6 and abs(EW[str(e1.date())] - b["EW"]) < 1e-6 and abs(X - b["X"]) < 1e-6
        if b["結局"] == "破壞":
            dd = pd.Timestamp(b["破壞日"])
            seg = r.loc[(r.index > pd.Timestamp(b["date"])) & (r.index < dd), "close"]
            ok &= bool(r.loc[dd, "close"] < b["low"] and (seg >= b["low"] * (1 - 1e-7)).all())   # 1e-7：factor 連乘與 cum_factor 8 位小數的浮點差
        rows.append({"型": typ, "sid": b["sid"], "S": b["date"], "R_程式": b["R"], "R_手算": R_, "EW_程式": b["EW"],
                     "EW_手算": EW[str(e1.date())], "X_程式": b["X"], "X_手算": X, "結局": b["結局"], "相符": bool(ok)})
    return pd.DataFrame(rows)


def breaks_fwd(sid, T, H=120):
    """(T, T+H] 內：價格斷點（自己寫）或連續 ≥ 5 個交易日無成交（5 日全在窗內）。"""
    r, ev = px(sid)
    a, b = POS[pd.Timestamp(T)] + 1, POS[pd.Timestamp(T)] + H
    idx = np.array([POS[d] for d in r.index])
    c = r["close"].to_numpy()
    for k in range(1, len(idx)):
        if a <= idx[k] <= b:
            ratio = c[k] / c[k - 1]
            if (ratio <= 0.55 or ratio >= 1.8) and not any(r.index[k - 1] < x <= r.index[k] for x in ev):
                return True
    have = set(idx.tolist()); run = 0
    for t in range(max(0, a - 4), b + 1):
        run = run + 1 if t not in have else 0
        if run >= 5 and t - 4 >= a:
            return True
    return False


def k3(sids):
    rng = np.random.default_rng(3)
    trig = pd.read_csv(os.path.join(OUT, "raw_triggers.csv.gz"), dtype={"sid": str})
    trig_set = set(zip(trig["sid"], trig["T"]))
    rows = []
    allA = pd.concat([pd.read_csv(os.path.join(OUT, f"A_{t}.csv.gz"), dtype={"sid": str, "ctl": str}).assign(型=t)
                      for t in ("box", "cup", "w", "hs", "flag")])
    samp = allA.iloc[rng.choice(len(allA), size=30, replace=False)]
    trcache = {}
    for _, e in samp.iterrows():
        T = pd.Timestamp(e["date"]); t = POS[T]
        vol = {}
        for s in sids:
            try:
                r, _ = px(s)
            except FileNotFoundError:
                continue
            w = r["close"].reindex(CAL[t - 20:t + 1])
            if w.isna().any():
                continue
            vol[s] = float(w.pct_change().iloc[1:].std(ddof=1))
        V = pd.Series(vol).sort_index()
        rk = V.rank(method="first").astype(int)
        dec = ((rk - 1) * 10) // len(V)
        d0 = dec[e["sid"]]
        pool = []
        for s in dec.index[dec == d0]:
            if s == e["sid"] or (s, e["date"]) in trig_set:
                continue
            if s not in trcache:
                trcache[s] = TR.one(s, CAL)
            tb = trcache[s]; r, _ = px(s)
            nd = CAL[t + 1]
            if not tb["trd"][t + 1] or nd not in r.index or not np.isfinite(r.loc[nd, "open"]) or tb["up_o"][t + 1]:
                continue
            if breaks_fwd(s, T):
                continue
            pool.append(s)
        pool = sorted(pool)
        ok = len(pool) == int(e["pool_n"]) and pool[int(e["pool_k"])] == e["ctl"]
        rows.append({"型": e["型"], "sid": e["sid"], "T": e["date"], "十分位": int(d0), "池_程式": int(e["pool_n"]), "池_另算": len(pool),
                     "對照_程式": e["ctl"], "對照_另算": pool[int(e["pool_k"])] if int(e["pool_k"]) < len(pool) else None, "相符": bool(ok)})
    return pd.DataFrame(rows)


def main():
    stocks = pd.read_csv(os.path.join(SNAP, "meta", "stocks.csv"), dtype=str)
    sids = sorted(UG.gate3(stocks)["stock_id"])
    K1 = k1(); print(K1.to_string()); print("K1 相符 {}/{}".format(int(K1["相符"].sum()), len(K1)), flush=True)
    K2 = k2(sids); print(K2.to_string()); print("K2 相符 {}/{}".format(int(K2["相符"].sum()), len(K2)), flush=True)
    K3 = k3(sids); print(K3.to_string()); print("K3 相符 {}/{}".format(int(K3["相符"].sum()), len(K3)), flush=True)
    K1.to_csv(os.path.join(OUT, "check_K1.csv"), index=False); K2.to_csv(os.path.join(OUT, "check_K2.csv"), index=False)
    K3.to_csv(os.path.join(OUT, "check_K3.csv"), index=False)
    json.dump({"K1": [int(K1["相符"].sum()), len(K1)], "K2": [int(K2["相符"].sum()), len(K2)], "K3": [int(K3["相符"].sum()), len(K3)]},
              open(os.path.join(OUT, "check.json"), "w"), ensure_ascii=False)


if __name__ == "__main__":
    main()
