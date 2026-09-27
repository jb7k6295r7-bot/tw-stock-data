# -*- coding: utf-8 -*-
"""X2 早年段 獨立查核（⛔ 不 import researchExtX2early、researchExt、p4_features、researchH2、rerun17、research13）。
只 import backtest.data（讀檔、還原）、backtest.universe_gate（gate3）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchExtX2early_check.py

 ① 版面：950ad26e12 與 3edc0e2206 的 main 版面，除 stocks/*.csv 的 shares 欄外逐檔相同；shares 有值比例
 ② 因子：全部股 × 全部月初自算 CGO（原始均價 × 還原係數、周轉率 ＝ 量 ÷ shares（只 ffill）、截到 1、100 日權重）與 TV100（有效 K 棒報酬 ≥ 75、ddof 1）、
    年齡 ≥ 100 ⇒ 每月初名單（TV100 最低 ⌈10%⌉ 裡 CGO 前 50；同值依代號）＝ picks_monthly.csv.gz
 ③ 窗內年化／回落：由 equity.csv.gz 自算（窗首當日為基、(b−a+1)/245 年、峰谷）＝ summary（三個頻率與 0050）
"""
from __future__ import annotations
import filecmp, json, math, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import universe_gate as UG

A = os.path.expanduser("~/earlydata/3edc0e2206/main/data"); B = os.path.expanduser("~/earlydata/950ad26e12/main/data")
OUT = os.path.expanduser("~/tw-p17/backtest/resultsExtX2early")
TOL = 1e-12


def wst(seg):
    c = (seg[-1] / seg[0]) ** (245 / len(seg)) - 1
    pk = np.maximum.accumulate(seg)
    return c, float(((seg - pk) / pk).min())


def main():
    RES = {}; Sm = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    # ①
    bad = []
    for d in ("adj", "meta", "stocks_inst", "stocks_per", "mops/revenue_hist"):
        fa, fb = sorted(os.listdir(os.path.join(A, d))), sorted(os.listdir(os.path.join(B, d)))
        if fa != fb or not all(filecmp.cmp(os.path.join(A, d, f), os.path.join(B, d, f), shallow=False) for f in fa):
            bad.append(d)
    nd = 0; sha = shb = tot = 0
    for f in sorted(os.listdir(os.path.join(B, "stocks"))):
        a = pd.read_csv(os.path.join(A, "stocks", f), dtype=str); b = pd.read_csv(os.path.join(B, "stocks", f), dtype=str)
        if not a.drop(columns=["shares"]).fillna("").equals(b.drop(columns=["shares"]).fillna("")):
            nd += 1
        sha += a["shares"].notna().sum(); shb += b["shares"].notna().sum(); tot += len(b)
    RES["① 版面只差 shares 欄"] = {"其他資料夾不同": bad, "stocks 非 shares 欄不同的檔": nd, "shares 有值比例（舊→新）": [sha / tot, shb / tot], "過": not bad and nd == 0}
    print(RES, flush=True)
    # ②
    D.DATA = B
    cal = D.load_calendar(); n = len(cal)
    per = cal.to_period("M"); mf = np.flatnonzero(np.r_[True, per[1:] != per[:-1]])
    U = UG.gate3(pd.read_csv(os.path.join(B, "meta", "stocks.csv"), dtype=str))
    F = {}
    for sid, mk in zip(U["stock_id"], U["market"]):
        st = D.load_stock(sid, mk, cal)
        if st is None:
            continue
        df = st.df; c = df["close"].to_numpy(float); v = np.isfinite(c)
        raw = pd.read_csv(os.path.join(B, "stocks", sid + ".csv"), dtype={"date": str}).drop_duplicates("date")
        raw.index = pd.to_datetime(raw["date"]); raw = raw.reindex(cal)
        rc = pd.to_numeric(raw["close"], errors="coerce").to_numpy(float)
        vol = pd.to_numeric(raw["volume"], errors="coerce").to_numpy(float); amt = pd.to_numeric(raw["amount"], errors="coerce").to_numpy(float)
        shr = pd.to_numeric(raw["shares"], errors="coerce").ffill().to_numpy(float)
        shr = np.where(shr > 0, shr, np.nan)
        with np.errstate(invalid="ignore", divide="ignore"):
            fac = np.where(v & (rc > 0), c / rc, np.nan)
            P = np.where(v & (vol > 0), amt / vol * fac, np.nan)
            V = np.where(v & (vol > 0), np.minimum(vol / shr, 1.0), 0.0)
        V = np.where(np.isfinite(shr) | ~v | ~(vol > 0), V, np.nan)
        nb = np.cumsum(v)
        rows = {}
        for k, d in enumerate(mf):
            t = d - 1
            if t < 99 or not v[t] or nb[t] < 100:
                continue
            sl = slice(t - 99, t + 1); cv = c[sl][v[sl]]
            if len(cv) < 76:
                continue
            tv = float(np.std(cv[1:] / cv[:-1] - 1, ddof=1))
            vr = V[sl][::-1]; pr = P[sl][::-1]
            if not np.isfinite(vr).all():
                continue
            w = vr * np.r_[1.0, np.cumprod(1 - vr)[:-1]]; ok = np.isfinite(pr) & (w > 0)
            if not ok.any() or w[ok].sum() <= 0:
                continue
            rows[k] = (tv, (c[t] - (pr[ok] * w[ok]).sum() / w[ok].sum()) / c[t])
        F[sid] = rows
    PK = pd.read_csv(os.path.join(OUT, "picks_monthly.csv.gz"), dtype={"sid": str})
    ref = {d: list(g.sort_values("名次")["sid"]) for d, g in PK.groupby("換股日")}
    nb_ = 0; nm = 0
    for k, d in enumerate(mf):
        rows = [(s, F[s][k][0], F[s][k][1]) for s in F if k in F[s]]
        if not rows:
            continue
        rows.sort(key=lambda r: (r[1], r[0])); lv = rows[:math.ceil(0.1 * len(rows))]
        top = [r[0] for r in sorted(lv, key=lambda r: (-r[2], r[0]))[:50]]
        nm += 1; nb_ += int(top != ref.get(str(cal[d].date()), []))
    RES["② 自算 CGO、TV100 ⇒ 每月初名單"] = {"比對月數": nm, "不同": nb_, "過": nb_ == 0}
    print(RES, flush=True)
    # ③
    E = pd.read_csv(os.path.join(OUT, "equity.csv.gz"), float_precision="round_trip")
    a_ = int(np.flatnonzero(E["date"].to_numpy() >= Sm["描述窗"][0])[0]); b_ = int(np.flatnonzero(E["date"].to_numpy() <= Sm["描述窗"][1])[-1])
    mx = 0.0
    c50, m50 = wst(E["0050"].to_numpy(float)[a_:b_ + 1] / E["0050"].to_numpy(float)[a_])
    mx = max(mx, abs(c50 - Sm["0050同窗（描述窗）"]["年化"]), abs(m50 - Sm["0050同窗（描述窗）"]["回落"]))
    for nm_ in ("5個月（主格）", "月換", "季換"):
        c, m = wst(E[f"X2_{nm_}"].to_numpy(float)[a_:b_ + 1])
        mx = max(mx, abs(c - Sm["X2"][nm_]["年化"]), abs(m - Sm["X2"][nm_]["回落"]))
    RES["③ 窗內年化／回落（三頻率＋0050）"] = {"最大差": mx, "過": mx <= 1e-12}
    RES["全部過"] = all(v["過"] for v in RES.values() if isinstance(v, dict))
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(RES, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
