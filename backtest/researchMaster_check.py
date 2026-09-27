# -*- coding: utf-8 -*-
"""PREREG大師三套 —— 獨立查核（⛔ 不 import researchMaster；不共用它的任何函式）。

    python -m backtest.researchMaster_check --part pre

pre：用【另一種寫法】（寬表 pivot＋逐量測日向量化）重算 2020-04-01 起每個量測日的
     分母（eligible ∧ 上市滿 5 年）、三套可算比例、三套候選數（本益比 P1＝per＋otcper 恰 t−1），
     與 resultsMaster/pre_coverage.csv 逐欄比（候選數要逐一相同；比例容差 1e-12）。
⛔ 不讀任何報酬。
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pandas as pd

FD = os.path.expanduser("~/msdata/572b5993aa87a48fd1f860a5bdc13cbbdf2e5964/data")
SNAP = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
REPO = os.path.expanduser("~/tw-p17")
OUT = os.path.join(REPO, "backtest/resultsMaster")


def col(df, *names):
    for n in names:
        if n in df.columns:
            return pd.to_numeric(df[n], errors="coerce")
    return pd.Series(np.nan, index=df.index)


def load_tables():
    parts = []
    for f in sorted(os.listdir(f"{FD}/mops/fs_hist")):
        a = pd.read_csv(f"{FD}/mops/fs_hist/{f}", dtype={"stock_id": str})
        b = pd.read_csv(f"{FD}/mops/bs_hist/{f}", dtype={"stock_id": str}) if os.path.exists(f"{FD}/mops/bs_hist/{f}") else None
        if a.empty:
            continue
        t = pd.DataFrame({"sid": a["stock_id"].str.strip(), "per": f[:6]})
        t["rev"] = col(a, "營業收入").values
        t["oi"] = col(a, "營業利益（損失）", "營業利益").values
        t["ni"] = col(a, "淨利（淨損）歸屬於母公司業主", "淨利（損）歸屬於母公司業主").fillna(col(a, "本期淨利（淨損）", "本期稅後淨利（淨損）")).values
        t["eps"] = col(a, "基本每股盈餘（元）", "基本每股盈餘").values
        if b is not None and not b.empty:
            u = pd.DataFrame({"sid": b["stock_id"].str.strip()})
            u["ta"] = col(b, "資產總計", "資產總額", "資產合計").values
            u["tl"] = col(b, "負債總計", "負債總額", "負債合計").values
            u["eq"] = col(b, "歸屬於母公司業主之權益合計", "歸屬於母公司業主權益合計", "歸屬於母公司業主之權益").fillna(
                col(b, "權益總計", "權益總額", "權益合計")).values
            t = t.merge(u, on="sid", how="outer"); t["per"] = f[:6]
        parts.append(t)
    A = pd.concat(parts, ignore_index=True)
    A["k"] = A["per"].str[:4].astype(int) * 4 + A["per"].str[5].astype(int) - 1
    return A


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--part", default="pre"); a = ap.parse_args()
    cal = pd.to_datetime(pd.read_csv(f"{SNAP}/meta/calendar_twse.csv")["date"]).sort_values().reset_index(drop=True)
    cal = pd.DatetimeIndex(cal)
    A = load_tables()
    ks = np.arange(A["k"].min(), A["k"].max() + 1)
    wide = {c: A.pivot_table(index="sid", columns="k", values=c, aggfunc="first").reindex(columns=ks) for c in ("rev", "oi", "ni", "eps", "ta", "tl", "eq")}
    has = A.assign(v=1).pivot_table(index="sid", columns="k", values="v", aggfunc="first").reindex(columns=ks).notna()
    sids = has.index
    for c in wide:
        wide[c] = wide[c].reindex(sids)

    def sq(c):                                         # 單季
        w = wide[c]
        prev = w.shift(1, axis=1)
        q1 = np.broadcast_to(np.array([k % 4 == 0 for k in ks]), w.shape)
        return w.where(q1, w - prev)
    rq, oq = sq("rev"), sq("oi")
    # 研發
    R = pd.concat([pd.read_csv(f"{FD}/mops/rd_hist/{f}", dtype={"stock_id": str}) for f in sorted(os.listdir(f"{FD}/mops/rd_hist"))])
    R["sid"] = R["stock_id"].str.strip(); R["k"] = R["period"].str[:4].astype(int) * 4 + R["period"].str[5].astype(int) - 1
    rk = sorted(R["k"].unique())
    RD = R.pivot_table(index="sid", columns="k", values="rd_ytd", aggfunc="first").reindex(columns=rk)
    RV = R.pivot_table(index="sid", columns="k", values="rev_ytd", aggfunc="first").reindex(columns=rk)
    RH = R.assign(v=1).pivot_table(index="sid", columns="k", values="v", aggfunc="first").reindex(columns=rk).notna()
    RD, RV = RD.reindex(RH.index), RV.reindex(RH.index)

    def avail(k):
        y, q = divmod(int(k), 4)
        d = pd.Timestamp(f"{y + 1}-03-31") if q == 3 else pd.Timestamp(f"{y}-" + ("05-15", "08-14", "11-14")[q])
        return cal[cal > d][0] if (cal > d).any() else pd.Timestamp("2100-01-01")
    av = pd.Series({k: avail(k) for k in ks})
    st = pd.read_csv(f"{SNAP}/meta/stocks.csv", dtype=str).set_index("stock_id")
    fseen = pd.to_datetime(st["first_seen"])
    panel = pd.read_csv(f"{REPO}/backtest/resultsAFC/panel.csv.gz", dtype={"stock_id": str}, usecols=["measure_date", "stock_id", "eligible"])
    panel["measure_date"] = pd.to_datetime(panel["measure_date"])
    panel = panel[(panel["measure_date"] >= "2020-04-01") & panel["eligible"].astype(bool)]
    ref = pd.read_csv(f"{OUT}/pre_coverage.csv").set_index("measure_date")
    bad = 0; rows = []
    for T, g in panel.groupby("measure_date"):
        e = pd.Index(g["stock_id"].unique())
        ok_k = [k for k in ks if av[k] <= T]
        # 每家最新可用季
        hv = has.reindex(e).fillna(False)[ok_k]
        L = hv.apply(lambda r: max([k for k, v in r.items() if v], default=-1), axis=1)
        fs_ = fseen.reindex(e)
        age5 = (fs_ <= pd.Timestamp("2015-01-05")) | (fs_ <= T - pd.DateOffset(years=5))
        res = pd.DataFrame(False, index=e, columns=["m1d", "m1", "m2d", "m2", "m3d", "m3", "m4d", "m4", "x2d", "x2", "o1d", "o1", "o3d", "o3"], dtype=object)
        for s in e:
            l = L[s]
            if l < 0 or s not in sids:
                res.loc[s, ["m1d", "m1", "m2d", "m2", "m3d", "m3", "m4d", "m4", "x2d", "x2", "o1d", "o1", "o3d", "o3"]] = [False] * 14
                continue
            win = list(range(l - 11, l + 1))
            hrow = has.loc[s]
            okrows = all(hrow.get(k, False) for k in win) and all(hrow.get(k - 1, False) for k in win if k % 4)
            r12 = rq.loc[s, win].to_numpy(float) if okrows else np.full(12, np.nan)
            o12 = oq.loc[s, win].to_numpy(float) if okrows else np.full(12, np.nan)
            m1d = okrows and np.isfinite(r12).all() and np.isfinite(o12).all()
            m1 = bool(m1d and (r12 > 0).all() and np.mean(o12 / r12) > 0.10)
            Y = l // 4 if l % 4 == 3 else l // 4 - 1
            yk = [y * 4 + 3 for y in range(Y - 4, Y + 1)]
            gv = lambda c, kk: np.array([wide[c].loc[s].get(k, np.nan) for k in kk], float)
            ni, eq, ta, tl = gv("ni", yk), gv("eq", yk), gv("ta", yk), gv("tl", yk)
            m2d = np.isfinite(ni).all() and np.isfinite(eq).all(); m2 = bool(m2d and (eq > 0).all() and np.mean(ni / eq) > 0.08)
            o1d = np.isfinite(ni).all() and np.isfinite(ta).all(); o1 = bool(o1d and (ta > 0).all() and np.mean(ni / ta) > 0.08)
            x2d = np.isfinite(tl).all() and np.isfinite(ta).all(); x2 = bool(x2d and (ta > 0).all() and np.mean(tl / ta) < 0.30)
            rv, ep = gv("rev", yk[1:]), gv("eps", yk[1:])
            # Y−3..Y 四個年報 ⇒ 三個增率
            m3d = np.isfinite(rv).all(); m3 = bool(m3d and (rv[:-1] > 0).all() and np.mean(rv[1:] / rv[:-1] - 1) > 0.10)
            o3d = np.isfinite(ep).all(); o3 = bool(o3d and (ep[:-1] > 0).all() and np.mean(ep[1:] / ep[:-1] - 1) > 0.30)
            y, q = divmod(l, 4)
            need = [l] if q == 3 else [l, (y - 1) * 4 + 3, (y - 1) * 4 + q]
            sg = np.array([1.0] if q == 3 else [1.0, 1.0, -1.0])
            if s not in RH.index or not all(RH.loc[s].get(k, False) for k in need):
                m4d, m4 = True, False
            else:
                rd = RD.loc[s, need].to_numpy(float); rvv = RV.loc[s, need].to_numpy(float)
                if not np.isfinite(rd).all():
                    m4d, m4 = True, False
                elif not np.isfinite(rvv).all():
                    m4d, m4 = False, False
                else:
                    den = (sg * rvv).sum(); m4d = True; m4 = bool(den > 0 and (sg * rd).sum() / den > 0.05)
            res.loc[s, ["m1d", "m1", "m2d", "m2", "m3d", "m3", "m4d", "m4", "x2d", "x2", "o1d", "o1", "o3d", "o3"]] = [m1d, m1, m2d, m2, m3d, m3, m4d, m4, x2d, x2, o1d, o1, o3d, o3]
        res = res.astype(bool)
        t = cal.get_loc(T)
        d1 = str(cal[t - 1].date())
        pe = {}
        for sub in ("per", "otcper"):
            p = f"{FD}/universe/{sub}/{d1}.csv"
            x = pd.read_csv(p, dtype={"stock_id": str}, usecols=["stock_id", "per"])
            for s_, v in zip(x["stock_id"].str.strip(), pd.to_numeric(x["per"], errors="coerce")):
                pe.setdefault(s_, v)
        ped = pd.Series({s: s in pe for s in e}); pev = pd.Series({s: pe.get(s, np.nan) for s in e})
        peok = ped & (pev > 0) & (pev < 15)
        den = age5.to_numpy(bool)
        M_d = res.m1d & res.m2d & res.m3d & res.m4d; M = res.m1 & res.m2 & res.m3 & res.m4 & age5
        X_d = res.m2d & res.x2d & ped & res.m3d; X = res.m2 & res.x2 & peok & res.m3 & age5
        O_d = res.o1d & res.m2d & res.o3d & ped; O = res.o1 & res.m2 & res.o3 & peok & age5
        me = {"denom_5y": int(den.sum()), "cov_M": float(M_d[den].mean()), "cov_X_P1": float(X_d[den].mean()), "cov_O_P1": float(O_d[den].mean()),
              "cand_M": int(M.sum()), "cand_X_P1": int(X.sum()), "cand_O_P1": int(O.sum())}
        r0 = ref.loc[str(T.date())]
        diff = {k: (v, r0[k]) for k, v in me.items() if (abs(v - r0[k]) > 1e-12)}
        bad += bool(diff)
        rows.append({"measure_date": str(T.date()), **me, "diff": str(diff) if diff else ""})
        print(str(T.date()), me, "⛔ " + str(diff) if diff else "✅", flush=True)
    pd.DataFrame(rows).to_csv(f"{OUT}/check_pre.csv", index=False)
    print(f"[查核 pre] {len(rows)} 個量測日｜不一致 {bad} 個 {'✅' if bad == 0 else '⛔'}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
