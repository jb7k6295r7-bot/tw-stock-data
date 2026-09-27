# -*- coding: utf-8 -*-
"""稽核 ② 8 突破過濾、限價 獨立查核（⛔ 不 import researchAudit2_8、researchBF、researchLimit、limit_entry、research11）。
只 import backtest.data（讀檔、還原因子）、backtest.tradability（成交、漲跌停、下市狀態）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchAudit2_8_check.py

 ① 甲：由原件 body_events.csv.gz 自算 14 格 × H20／H60 的 Δ、CR0 CI（H20 曆月、H60 blk）、n_eff、出口、結果類；H120 子集（in120）點估計 ⇒ ＝ bf_cells.csv
 ② 乙：抽 300 筆，自寫出場規則（x＝e＋59：有成交、收盤非跌停、收盤有效 ⇒ 收盤出；否則之後第一個有成交且開盤非跌停的開盤；
    無成交且已過最後成交日 ⇒ 下市者以該日（ffill）收盤了結）與報酬（出場還原價 ÷（成交未還原價 × 因子）− 1 − 0.585%；沒成交 ⇒ 0）
    ⇒ ＝ limit_h60.csv.gz；再由 limit_h60 自算三格 D、60 日區段 CR0、n_eff、出口、結果 ⇒ ＝ summary.json
"""
from __future__ import annotations
import json, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import tradability as TR

SNAP = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
D.DATA = SNAP
B = os.path.expanduser("~/tw-p17/backtest")
OUT = os.path.join(B, "resultsAudit2/8")
TOL, COST = 1e-12, 0.00585
FNAME = {"B": "幅度 3% 過濾", "C": "站穩 3 天過濾", "D": "放量 1.5 倍過濾", "E": "等回測頸線＋量縮＋止跌 K", "F": "三道全加"}


def cr0(x, g):
    x = np.asarray(x, float); n = len(x); m = x.mean()
    s = pd.Series(x - m).groupby(np.asarray(g)).sum().to_numpy()
    return m, np.sqrt((s ** 2).sum()) / n, len(s)


def main():
    RES = {}
    X = pd.read_csv(os.path.join(B, "resultsBF/body_events.csv.gz"), dtype={"sid": str}, float_precision="round_trip")
    C = pd.read_csv(os.path.join(OUT, "bf_cells.csv"), float_precision="round_trip")
    NM = {"w": "W 底", "hs": "頭肩底", "box": "箱型"}; ARMS = {"w": "BCDEF", "hs": "BCDEF", "box": "BDEF"}
    bad = []
    for H in (20, 60, 120):
        for typ in ("w", "hs", "box"):
            Y = X[X["type"] == typ]
            if H == 120:
                Y = Y[Y["in120"] == 1]
            g = pd.to_datetime(Y["T"]).dt.strftime("%Y-%m").to_numpy() if H == 20 else Y["blk"].to_numpy()
            for a in ARMS[typ]:
                d = (Y[f"r{H}_{a}"] - Y[f"r{H}_A"]).to_numpy(float)
                ref = C[(C["H"] == H) & (C["型態"] == NM[typ]) & (C["買法"] == a)].iloc[0]
                if H == 120:
                    if abs(d.mean() - ref["Δ"]) > TOL or ref["結果類"] != "依構造不可判定":
                        bad.append((H, typ, a))
                    continue
                m, se, ng = cr0(d, g); lo, hi = m - 1.96 * se, m + 1.96 * se; ne = min(len(d), ng)
                cat = "分不出來" if lo <= 0 <= hi else ("加過濾較差" if m < 0 else "加過濾比較好／單格過關")
                if abs(m - ref["Δ"]) > TOL or abs(lo - ref["CI95_lo"]) > TOL or ne != ref["n_eff"] or not str(ref["結果類"]).startswith(cat.split("／")[0][:4]):
                    bad.append((H, typ, a))
    RES["① 甲 14 格 × 三個 H"] = {"不符": bad, "過": not bad}
    print(RES, flush=True)
    # ②
    L = pd.read_csv(os.path.join(OUT, "limit_h60.csv.gz"), dtype={"sid": str}, float_precision="round_trip")
    Tt = pd.read_csv(os.path.join(B, "resultsLimit/trades.csv.gz"), dtype={"sid": str}, float_precision="round_trip").set_index("i")
    cal = D.load_calendar(); n = len(cal); off = TR.load_official()
    rng = np.random.default_rng(20260928); pick = L.iloc[np.sort(rng.choice(len(L), 300, replace=False))]
    cache = {}; mx = 0.0; nst = 0
    MK = pd.read_csv(os.path.join(SNAP, "meta", "stocks.csv"), dtype=str).set_index("stock_id")["market"].to_dict()
    for r in pick.itertuples():
        if r.sid not in cache:
            st = D.load_stock(r.sid, MK.get(r.sid, "twse"), cal)
            df = st.df
            tb = TR.one(r.sid, cal); ds = TR.delist_status({r.sid: tb}, cal, official=off).get(r.sid, {"last": n - 1, "status": "live"})
            cache[r.sid] = (pd.Series(df["close"].to_numpy(float)).ffill().to_numpy(), df["open"].to_numpy(float), np.asarray(tb["trd"], bool),
                            np.asarray(tb["dn_c"], bool), np.asarray(tb["dn_o"], bool), ds["last"], ds["status"])
        c, o, trd, dnc, dno, last, stt = cache[r.sid]
        x = int(r.e) + 59
        if x >= n:
            status, px = "beyond_cal", np.nan
        elif trd[x] and not dnc[x] and np.isfinite(c[x]) and c[x] > 0:
            status, px = "ok", c[x]
        else:
            status, px = "unresolved", np.nan
            for t in range(x + 1, n):
                if trd[t] and not dno[t] and np.isfinite(o[t]) and o[t] > 0:
                    status, px = "exit_delayed", o[t]; break
                if (not trd[t]) and t > last:
                    status, px = ("delist_settled", c[t]) if stt.startswith("delisted") else ("delist_ambig", np.nan); break
        nst += int(status != r.x60_status)
        t0 = Tt.loc[int(r.i)]
        for a in ("M0", "L1", "L2", "L3"):
            fr = t0[f"{a}_fill_raw"]; want = getattr(r, f"r60_{a}")
            if status not in ("ok", "exit_delayed", "delist_settled"):
                continue
            if not np.isfinite(fr):
                v = 0.0
            else:
                tt = int(t0[f"{a}_t"]) if a != "M0" else int(r.e)
                F = D.cum_factor_series(cal, D.load_adj(r.sid))[tt]
                v = px / (fr * F) - 1 - COST
            mx = max(mx, abs(v - want))
    RES["② 乙 抽 300 筆 H60 出場與報酬"] = {"出場狀態不符": nst, "報酬最大差": mx, "過": nst == 0 and mx <= 1e-9}
    Sm = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))["乙 限價"]
    w0 = int(cal.searchsorted(pd.Timestamp("2017-03-02"))); b2 = []
    for k in (1, 2, 3):
        d = (L[f"r60_L{k}"] - L["r60_M0"]); ok = d.notna()
        m, se, ng = cr0(d[ok].to_numpy(float), ((L.loc[ok, "e"].to_numpy(int) - w0) // 60))
        ref = Sm[f"H60_L{k}"]
        if abs(m - ref["D"]) > TOL or abs(m - 1.96 * se - ref["lo"]) > TOL or min(int(ok.sum()), ng) != ref["n_eff"]:
            b2.append(k)
    RES["③ 乙 H60 三格 D、CI、n_eff"] = {"不符": b2, "過": not b2}
    RES["全部過"] = all(v["過"] for v in RES.values() if isinstance(v, dict))
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(RES, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
