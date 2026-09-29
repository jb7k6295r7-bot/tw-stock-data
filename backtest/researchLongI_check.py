# -*- coding: utf-8 -*-
"""researchLongI 的獨立查核（⛔ 不 import researchLongI）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchLongI_check.py

① 抽 10 檔：自己用 pandas 算轉換、基準、先行 A／B（前移 26）、延遲線 ⇒ 三役條件由不成立轉成立的那一根 ⇒ 訊號日、進場日對 signals.csv.gz；
   同一批自己算 Wilder ATR(14) 與 k＝2、3 的移動停損出場日 ⇒ 對 xpos_k2、xpos_k3
② 格：0050 同段標籤自己重判 ⇒ 對 cells.csv
③ 種子 0：乙 k3 主窗自己組訊號、自己呼叫 research11.simulate_mtm ⇒ A、B 段年化對 seeds.csv.gz（repr）；有甲則甲 k3 同法
④ 臺灣50 成分另寫一次（代號全換新代號、逐檔找 d 前後最近一筆調整）⇒ 對 signals 甲 欄（主窗全部）；每日檔數 ≠ 50 只能是 2010-06-24～28 的 51
⚠ 範圍：壞根判定用 research11.load_bars（共用引擎）
⇒ backtest/resultsLongI/check.json
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import universe_gate as UG
UG.set_innov_ky(True)
from backtest import data as D
from backtest import tradability as TR
from backtest import research11 as R
from backtest import rerun17 as RR

ST = os.path.expanduser("~/evtdata/stitch_950ad26e12_edc6f8002f/data")
OUT = "backtest/resultsLongI"
D.DATA = ST
cal = D.load_calendar(); n = len(cal)
mk = pd.read_csv(os.path.join(ST, "meta", "stocks.csv"), dtype=str).set_index("stock_id")["market"].to_dict()
T = pd.read_csv(os.path.join(OUT, "signals.csv.gz"), dtype={"sid": str}, float_precision="round_trip")
PT = pd.read_csv(os.path.join(OUT, "cells.csv"))
S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
errs = []; info = {}
rng = np.random.default_rng(20260929)
smp = list(rng.choice(sorted(set(T["sid"])), size=10, replace=False))
nb = 0
for s in smp:
    B = R.load_bars(s, mk.get(s, "twse"), cal)
    idx = B["idx"]; h = pd.Series(B["h"]); l = pd.Series(B["l"]); c = pd.Series(B["c"]); o = B["o"]
    bad = B["next_bad"][:len(idx)] == np.arange(len(idx)); near = bad | np.r_[False, bad[:-1]] | np.r_[bad[1:], False]
    tk = (h.rolling(9).max() + l.rolling(9).min()) / 2; kj = (h.rolling(26).max() + l.rolling(26).min()) / 2
    sa = ((tk + kj) / 2).shift(26); sb = ((h.rolling(52).max() + l.rolling(52).min()) / 2).shift(26); lag = c.shift(26)
    okv = tk.notna() & kj.notna() & sa.notna() & sb.notna() & lag.notna()
    cond = okv & (tk > kj * 1.01) & (c > lag) & (c > np.fmax(sa, sb))
    tb = TR.one(s, cal); trd, up = np.asarray(tb["trd"], bool), np.asarray(tb["up_o"], bool)
    hh, ll, cc = B["h"], B["l"], B["c"]
    tr = np.r_[hh[0] - ll[0], np.maximum.reduce([hh[1:] - ll[1:], np.abs(hh[1:] - cc[:-1]), np.abs(ll[1:] - cc[:-1])])]
    atr = np.full(len(cc), np.nan); atr[13] = tr[:14].mean()
    for k in range(14, len(cc)):
        atr[k] = (atr[k - 1] * 13 + tr[k]) / 14
    mine = []
    for k in range(1, len(idx)):
        if not (cond.iloc[k] and okv.iloc[k - 1] and not cond.iloc[k - 1]):
            continue
        if k < 77 or near[k] or k + 1 >= len(idx) or idx[k + 1] != idx[k] + 1:
            continue
        ed = int(idx[k + 1])
        if not (trd[ed] and np.isfinite(o[k + 1]) and o[k + 1] > 0 and not up[ed]):
            continue
        xs = []
        for km in (2, 3):
            mx = cc[k + 1]; xp = None
            for j in range(k + 2, len(cc)):
                if bad[j]:
                    xp = int(idx[j - 1]); break
                if np.isfinite(atr[j - 1]) and cc[j] < mx - km * atr[j - 1]:
                    xp = int(idx[j + 1]) if (j + 1 < len(cc) and not bad[j + 1]) else int(idx[j]); break
                mx = max(mx, cc[j])
            xs.append(xp if xp is not None else n)
        mine.append((int(idx[k]), ed, xs[0], xs[1]))
    ref = [tuple(int(v) for v in r) for r in T.loc[T["sid"] == s, ["pos", "entry_pos", "xpos_k2", "xpos_k3"]].itertuples(index=False)]
    if mine != ref:
        nb += 1; errs.append(f"① {s} 自算 {len(mine)} 檔 {len(ref)}")
info["① 抽 10 檔 訊號＋出場 不同"] = nb
B50 = S["0050"]
lab = lambda c, m, b: "合格" if (c > b["cagr"] and c / abs(m) >= b["cagr"] / abs(b["mdd"])) else ("另列" if c > b["cagr"] else "不合格")
n2 = 0
for _, r in PT.iterrows():
    for sg in B50:
        if f"{sg}_年化" in r and pd.notna(r.get(f"{sg}_年化")) and lab(r[f"{sg}_年化"], r[f"{sg}_回落"], B50[sg]) != r[f"{sg}_標籤"]:
            n2 += 1; errs.append(f"② {r['格']} {sg}")
info["② 標籤不同"] = n2
SEED = pd.read_csv(os.path.join(OUT, "seeds.csv.gz"), float_precision="round_trip")
w0, w1 = int(cal.searchsorted(pd.Timestamp("2009-01-05"))), int(cal.searchsorted(pd.Timestamp("2026-08-24")))
segs = {k: v for k, v in {"A 2009-01～2019-03（判）": ("2009-01-05", "2019-03-29"), "B 2024-04～2026-08（判）": ("2024-04-01", "2026-08-24")}.items()}
for fam in ("甲", "乙"):
    if fam not in T.columns or not T[fam].astype(str).eq("True").any():
        continue
    g = T[T[fam].astype(str).eq("True") & (T["entry_pos"] >= w0) & (T["entry_pos"] <= w1)].sort_values(["entry_pos", "sid"]).reset_index(drop=True)
    sig = g[["sid", "pos", "entry_pos", "xpos_k3", "g_k3"]].assign(relvol=g["ratio"])
    cl, op = RR.load_prices(sorted(set(sig["sid"])), cal, pd.Series(mk), "branch"); cl, op = RR.pad_px_t1(cl, op)
    SF = R.stop_force_days(R.valid_from_data(sorted(set(sig["sid"])), pd.Series(mk), cal), w1)
    o = R.simulate_mtm(sig, "k3", 20, np.random.default_rng(1000), cl, op, n + 1, return_equity=True, log=[], d_max=None, pick="relvol", queue_days=0, stop_force=SF)
    eq = np.asarray(o["equity"], float)
    for sg, (x, y) in segs.items():
        a_, b_ = int(cal.searchsorted(pd.Timestamp(x))), int(cal.searchsorted(pd.Timestamp(y)))
        cg, _, _ = RR.win_metrics(eq, o["first"], o["end"], a_, b_)
        ref = SEED[(SEED["fam"] == fam) & (SEED["win"] == "主") & (SEED["k"] == 3) & (SEED["r"] == 0)].iloc[0]
        info[f"③ 種子0 {fam}_k3 {sg}（自跑／檔）"] = [float(cg), float(ref[f"{sg}_年化"])]
        if repr(float(cg)) != repr(float(ref[f"{sg}_年化"])):
            errs.append(f"③ {fam} {sg}")
# ④ 臺灣50 成分：另一種寫法（代號先全換成新代號、逐檔找「d 之後第一筆／d 之前最後一筆」調整）⇒ 對 signals 的 甲 欄；並數每日檔數
TWD = os.path.expanduser("~/evtdata/tw50_d365c37f89/data/meta/tw50")
if "甲" in T.columns and T["甲"].astype(str).eq("True").any():
    cmap = pd.read_csv(os.path.join(TWD, "tw50_code_map.csv"), dtype=str, encoding="utf-8-sig")
    canon = dict(zip(cmap["old_id"], cmap["new_id"])); cf = lambda s: canon.get(s, s)
    chg = pd.read_csv(os.path.join(TWD, "tw50_changes.csv"), dtype=str, encoding="utf-8-sig")
    chg = chg[chg["action"].isin(["add", "delete"])]
    chg = chg.assign(sid=chg["stock_id"].str.strip().map(cf), eff=pd.to_datetime(chg["effective_date"]))
    bs = pd.read_csv(os.path.join(TWD, "tw50_base_2026-06-30.csv"), dtype=str, encoding="utf-8-sig")
    bset = {cf(s.strip()) for s in bs["stock_id"]}; bday = pd.Timestamp("2026-06-30")
    evs = {s: g.sort_values("eff")[["eff", "action"]].values.tolist() for s, g in chg.groupby("sid")}
    allc = sorted(bset | set(evs))

    def member(s, d):
        E = evs.get(s, [])
        if d <= bday:
            nxt = [a for e, a in E if d < e <= bday]
            return (nxt[0] == "delete") if nxt else (s in bset)
        prv = [a for e, a in E if bday < e <= d]
        return (prv[-1] == "add") if prv else (s in bset)
    J = T[T["entry_pos"] >= int(cal.searchsorted(pd.Timestamp("2009-01-05")))]
    mine = [member(cf(s), cal[p]) for s, p in zip(J["sid"], J["pos"])]
    nm = int(np.sum(np.array(mine) != J["甲"].astype(str).eq("True").to_numpy()))
    info["④ 甲 欄（主窗全部訊號）不同"] = [int(len(J)), nm]
    if nm:
        errs.append(f"④ 甲 欄 {nm} 列不同")
    days = cal[(cal >= pd.Timestamp("2009-01-05"))]
    off = {}
    for d in days:
        k = sum(member(s, d) for s in allc)
        if k != 50:
            off[f"{d:%Y-%m-%d}"] = k
    info["④ 每日檔數 ≠ 50（自算）"] = off
    if set(off) != {"2010-06-24", "2010-06-25", "2010-06-28"} or set(off.values()) != {51}:
        errs.append(f"④ 檔數 {off}")
info["錯誤數"] = len(errs)
json.dump({"info": info, "errors": errs[:40]}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(info, ensure_ascii=False, default=str)); [print("  ⛔", e) for e in errs[:15]]
print("查核：" + ("全過" if not errs else "⛔ 不過"))
