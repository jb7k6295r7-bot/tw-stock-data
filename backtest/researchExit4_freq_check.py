# -*- coding: utf-8 -*-
"""出場第四輪 seq1 頻率表乾跑——獨立對帳（回測線計算子代理；⛔ 不算報酬、不 commit）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchExit4_freq_check [--n 150]

C1 抽樣逐股重算（主 n 檔、早年 n/2 檔，default_rng(20261021)）：價格、tradability、exright 改判、硬斷點、狀態、各出法判斷日／賣出日，
   ⭐ 全部用本檔逐日迴圈另寫（只共用 data.load_stock、data.breakpoints、tradability.one／delist_status、research11.limit_price、seq6 setup 的母體與月營收），
   與 events.csv.gz 逐列逐欄比（sid、e、狀態、T、kb、各出法 _d／_s、S0 上下緣日、S− K2 兩條日）。
C2 freq.csv 由 events.csv.gz 另寫彙總逐列比（收件、曆月、n_eff、壞根截斷、各出法觸發數）。
C3 構造：S+ K2 ≡ K1；K4 觸發 ⇒ K3 判斷日 ≤ K4；所有 _s ≥ _d＋1；S0 事件 T ＝ e＋N−1；S± 事件 T ∈ [e, e＋249]。
C4 ⛔ 輸出檔不得有報酬／價格欄；freq.json 的登錄 sha。
C5 策略鎖 --check 相符（25 支）。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pickle
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchExitGen as G6                                # noqa: E402  setup（母體）、rev_turns、avail_map
D = G6.D
from backtest import tradability as TRD                     # noqa: E402
from backtest import research11 as R11                      # noqa: E402

OUT = os.environ.get("X4F_OUT", os.path.expanduser("~/tw-p17/backtest/resultsExit4/freq"))
EXR_PKL = os.path.expanduser("~/b2fwork/exrtab_b5532121f8d8.pkl")
REG_SHA = "e86e45b37aaa66e2"
RES: dict = {}


def log(s):
    print(s, flush=True)


def stock(sid, market, cal, off, tab):
    st = D.load_stock(sid, market, cal)
    if st is None:
        return None
    df = st.df; n = len(cal)
    o = df["open"].to_numpy(float); c = df["close"].to_numpy(float)
    valid = np.isfinite(c)
    if valid.sum() < 2:
        return None
    pb = np.zeros(n, bool)
    for b in D.breakpoints(df, st.event_dates):
        if b["rule"] in ("price", "price+gap"):
            pb[b["pos"]] = True
    tb = TRD.one(sid, cal)
    ds = TRD.delist_status({sid: tb}, cal, official=off).get(sid)
    upto = ds["last"] if (ds is not None and ds["status"].startswith("delisted")) else None
    g5 = np.zeros(n, bool); run = 0
    for i in range(n):
        miss = (not valid[i]) and (upto is None or i <= upto)
        run = run + 1 if miss else 0
        g5[i] = run >= 5
    up = tb["up_o"].copy(); dn = tb["dn_o"].copy()
    rows = tab.get(sid, [])
    if rows:
        raw = pd.read_csv(os.path.join(D.DATA, "stocks", f"{sid}.csv"), dtype={"date": str}, usecols=["date", "open", "close"])
        raw["date"] = pd.to_datetime(raw["date"]); raw = raw.drop_duplicates("date").set_index("date")
        ro = pd.to_numeric(raw["open"], errors="coerce"); rc = pd.to_numeric(raw["close"], errors="coerce")
        for d, ob in rows:
            if d not in raw.index:
                continue
            p = cal.get_indexer([d])[0]
            if p < 0 or not (rc[d] > 0):
                continue
            lim = 0.07 if d < TRD.CUT else 0.10
            x = ro[d]
            up[p] = bool(x > 0 and abs(x - R11.limit_price(ob, True, lim)) < 1e-6)
            dn[p] = bool(x > 0 and abs(x - R11.limit_price(ob, False, lim)) < 1e-6)
    okb = tb["trd"] & ~up & np.isfinite(o) & (np.nan_to_num(o) > 0)
    oks = tb["trd"] & ~dn & np.isfinite(o) & (np.nan_to_num(o) > 0)
    # MA20：日曆 ffill，最近 20 個有值平均（上市前不計）
    cf = c.copy(); lastv = np.nan
    for i in range(n):
        if np.isfinite(cf[i]):
            lastv = cf[i]
        else:
            cf[i] = lastv
    ma = np.full(n, np.nan)
    for i in range(n):
        w = cf[max(0, i - 19):i + 1]; w = w[np.isfinite(w)]
        ma[i] = math.fsum(w) / len(w) if len(w) else np.nan
    return {"o": o, "c": c, "valid": valid, "pb": pb, "g5": g5, "okb": okb, "oks": oks, "ma": ma, "lastbar": int(np.flatnonzero(valid)[-1])}


def recompute(sid, market, es, cal, off, tab, turns, nrev):
    S = stock(sid, market, cal, off, tab)
    n = len(cal); last = n - 1
    out = []
    if S is None:
        return out
    o, c, v, ma = S["o"], S["c"], S["valid"], S["ma"]

    def sell(k):
        if k < 0:
            return -1
        for q in range(k + 1, n):
            if S["oks"][q]:
                return q
        return -1

    for e in es:
        if e > last or not S["okb"][e]:
            continue
        kb = None
        for t in range(e, n):
            if S["pb"][t] or (S["g5"][t] and t >= e + 4):
                kb = t; break
        if kb == e:
            continue
        kbv = kb if kb is not None else 10 ** 9
        P0 = o[e]
        hi = min(e + 249, kbv - 1, last)
        fu = fd = None
        for t in range(e, hi + 1):
            if not v[t]:
                continue
            r = c[t] / P0 - 1
            if fu is None and r >= 0.15:
                fu = t
            if fd is None and r <= -0.15:
                fd = t
        evs = []
        if fu is not None:
            evs.append(("S+", fu))
        if fd is not None:
            evs.append(("S−", fd))
        for N in (30, 40, 60):
            Tn = e + N - 1
            if Tn <= hi and Tn <= S["lastbar"] and (fu is None or fu > Tn) and (fd is None or fd > Tn):
                evs.append((f"S0_{N}", Tn))
        for st, T in evs:
            W = min(T + 250, kbv - 1, last); kmax = W - 1
            r = {"sid": sid, "e": e, "狀態": st, "T": T, "kb": kb if kb is not None else -1, "K1_d": T, "K1_s": sell(T)}
            ks = [k for k in range(T, kmax + 1) if v[k]]
            if st == "S+":
                d3 = d4 = d5 = -1; mx = -np.inf
                for k in ks:
                    mx = max(mx, c[k])
                    if d3 < 0 and c[k] <= 0.9 * mx:
                        d3 = k
                    if d4 < 0 and c[k] <= 0.8 * mx:
                        d4 = k
                    if d5 < 0 and c[k] < ma[k]:
                        d5 = k
                for code, d in (("K3", d3), ("K4", d4), ("K5", d5)):
                    r[f"{code}_d"] = d; r[f"{code}_s"] = sell(d)
                r["K2_d"], r["K2_s"] = r["K1_d"], r["K1_s"]
            elif st.startswith("S0"):
                vals = [c[t] for t in range(e, T + 1) if v[t]]
                lo, up = min(vals), max(vals)
                dl = next((k for k in ks if c[k] < lo), -1); du = next((k for k in ks if c[k] > up), -1)
                r["K2_d"] = dl; r["K2_s"] = sell(dl); r["上緣突破_d"] = du; r["下緣跌破_d"] = dl
                d3 = -1; brk = False
                for k in ks:
                    if not brk:
                        if c[k] < lo:
                            d3 = k; break
                        if c[k] > up:
                            brk = True
                    elif c[k] < up:
                        d3 = k; break
                r["K3_d"] = d3; r["K3_s"] = sell(d3)
            else:
                f5 = next((k for k in ks if c[k] / P0 - 1 >= -0.05), -1); fm = next((k for k in ks if c[k] >= ma[k]), -1)
                d2 = min([x for x in (f5, fm) if x >= 0], default=-1)
                r["K2_d"] = d2; r["K2_s"] = sell(d2); r["K2_r5_d"] = f5; r["K2_ma_d"] = fm
                d3 = next((k for k in ks if c[k] / P0 - 1 <= -0.25), -1)
                r["K3_d"] = d3; r["K3_s"] = sell(d3)
                tt = [a for a in turns if T <= a <= kmax]
                d4 = min(tt) if tt else -1
                r["K4_d"] = d4; r["K4_s"] = sell(d4)
            out.append(r)
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=150)
    a = ap.parse_args()
    EV = pd.read_csv(os.path.join(OUT, "events.csv.gz"), dtype={"sid": str})
    F = pd.read_csv(os.path.join(OUT, "freq.csv"))
    J = json.load(open(os.path.join(OUT, "freq.json"), encoding="utf-8"))
    tab = pickle.load(open(EXR_PKL, "rb"))["tab"]
    rng = np.random.default_rng(20261021)
    COLS = ["T", "kb", "K1_d", "K1_s", "K2_d", "K2_s", "K3_d", "K3_s", "K4_d", "K4_s", "K5_d", "K5_s", "上緣突破_d", "下緣跌破_d", "K2_r5_d", "K2_ma_d"]
    # C1
    c1 = {}
    for world, wn, nn in (("main", "主", a.n), ("early", "早年", a.n // 2)):
        Wd = G6.setup(world, log)
        cal = Wd["cal"]; p = Wd["p"]
        off = TRD.load_official()
        sids = sorted(p["stock_id"].unique())
        pick = sorted(rng.choice(sids, size=min(nn, len(sids)), replace=False))
        mine = []
        for sid in pick:
            es = sorted(p.loc[p["stock_id"] == sid, "e"].astype(int))
            turns, nrev = G6.rev_turns(sid, Wd["rev"], Wd["rly"], Wd["A"])
            mine += recompute(sid, Wd["mk"].get(sid, "twse"), es, cal, off, tab, list(turns), nrev)
        M = pd.DataFrame(mine)
        R = EV[(EV["世界"] == wn) & EV["sid"].isin(pick)]
        key = ["sid", "e", "狀態"]
        M = M.sort_values(key).reset_index(drop=True); R = R.sort_values(key).reset_index(drop=True)
        same_keys = len(M) == len(R) and (M[key].astype(str).to_numpy() == R[key].astype(str).to_numpy()).all()
        diffs = {}
        if same_keys:
            for col in COLS:
                if col in M.columns:
                    a_ = M[col].fillna(-999).astype(int).to_numpy(); b_ = R[col].fillna(-999).astype(int).to_numpy()
                    # 程式版只在該狀態群寫欄；缺欄 ⇒ −999
                    nd = int((a_ != b_).sum())
                    if nd:
                        diffs[col] = nd
        c1[wn] = {"抽樣股": len(pick), "重算事件": len(M), "程式事件": len(R), "鍵相同": bool(same_keys), "欄不同": diffs, "過": bool(same_keys and not diffs)}
        log(f"[C1 {wn}] {c1[wn]}")
    RES["C1"] = c1
    # C2
    bad2 = 0; n2 = 0
    for _, r in F.iterrows():
        wn, sg, st, h = r["世界"], r["段"], r["狀態"], int(r["終點"].split("+")[1])
        sub = EV[(EV["世界"] == wn) & (EV["段"] == sg) & (EV["狀態"] == st) & EV[f"E在資料內_{h}"]]
        n = len(sub); mo = sub["T月"].nunique()
        ok = (n == r["收件(E在資料內)"]) and (min(n, mo) == r["n_eff"]) and (int(sub[f"壞根截斷_{h}"].sum()) == r["壞根截斷"])
        if r["出法"] != "K0" and n:
            code = r["出法"]; Eh = sub[f"E_{h}"].to_numpy(); d = sub[f"{code}_d"].to_numpy(); s = sub[f"{code}_s"].to_numpy()
            k = int(((d >= 0) & (d < Eh) & (s > d) & (s <= Eh)).sum())
            ok &= k == r["觸發"]
        n2 += 1; bad2 += int(not ok)
    RES["C2"] = {"列": n2, "不同": bad2, "過": bad2 == 0}
    log(f"[C2] {RES['C2']}")
    # C3
    sp = EV[EV["狀態"] == "S+"]
    t4 = (sp["K4_s"] >= 0) & (sp["K4_d"] >= 0)
    c3 = {"S+ K2≡K1": bool(((sp["K2_d"] == sp["K1_d"]) & (sp["K2_s"] == sp["K1_s"])).all()),
          "K4 觸發 ⇒ 0 ≤ K3_d ≤ K4_d": bool(((sp["K3_d"] >= 0) & (sp["K3_d"] <= sp["K4_d"]))[t4].all())}
    ss = True
    for code in ("K1", "K2", "K3", "K4", "K5"):
        if f"{code}_s" in EV:
            m = EV[f"{code}_s"].fillna(-1) >= 0
            ss &= bool((EV.loc[m, f"{code}_s"] >= EV.loc[m, f"{code}_d"] + 1).all())
    c3["_s ≥ _d＋1"] = ss
    s0 = EV[EV["狀態"].str.startswith("S0")]
    c3["S0 T＝e＋N−1"] = bool((s0["T"] == s0["e"] + s0["狀態"].str[3:].astype(int) - 1).all())
    spm = EV[EV["狀態"].isin(["S+", "S−"])]
    c3["S± T∈[e,e+249]"] = bool(((spm["T"] >= spm["e"]) & (spm["T"] <= spm["e"] + 249)).all())
    c3["過"] = all(v for v in c3.values())
    RES["C3"] = c3
    log(f"[C3] {c3}")
    # C4
    badc = []
    for f in ("freq.csv", "cells.csv", "years.csv", "market.csv", "equiv.csv"):
        cols = pd.read_csv(os.path.join(OUT, f), nrows=1).columns
        badc += [f"{f}:{c}" for c in cols if any(w in c for w in ("報酬", "R平均", "勝率", "ret", "價"))]
    badc += [f"events:{c}" for c in EV.columns if any(w in c for w in ("報酬", "R_", "ret", "價", "V_"))]
    RES["C4"] = {"疑似報酬欄": badc, "登錄sha": REG_SHA in J["登錄"], "過": (not badc) and REG_SHA in J["登錄"]}
    log(f"[C4] {RES['C4']}")
    # C5
    p_ = subprocess.run([sys.executable, "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True, cwd=os.path.expanduser("~/tw-p17"),
                        env={**os.environ, "PYTHONPATH": os.path.expanduser("~/tw-p17")})
    tail = (p_.stdout + p_.stderr).strip().splitlines()[-1:]
    RES["C5"] = {"輸出": tail, "過": bool(tail and "相符（25 支）" in tail[0])}
    log(f"[C5] {RES['C5']}")
    RES["全過"] = all(RES[k]["過"] if k != "C1" else all(v["過"] for v in RES[k].values()) for k in ("C1", "C2", "C3", "C4", "C5"))
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[全過] {RES['全過']}")


if __name__ == "__main__":
    main()
