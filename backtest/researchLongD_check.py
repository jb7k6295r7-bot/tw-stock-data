# -*- coding: utf-8 -*-
"""researchLongD 的獨立查核（⛔ 不 import researchLongD、⛔ 不 import researchWeekly）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchLongD_check.py

① 週線箱型：抽 12 檔（有週線訊號者），自己用 pandas 依「週一起算日曆週」聚合週 K、自己寫箱型狀態機（D1～D5）
   ⇒ 買訊週最後一天、進場日、出場日（未出場 ⇒ 資料尾）對 trades_W.csv.gz（同檔全部列）
② 日線箱型：同 12 檔中抽 4 檔、自己寫日線版 ⇒ 對 trades_D.csv.gz
③ 格：標籤（0050 同段）、退化、挑格、件標籤自己重判 ⇒ 對 cells.csv／summary.json
④ 種子 0：挑中格（主、早年兩條）自己從 trades_W 組訊號、自己呼叫 research11.simulate_mtm ⇒ 三段年化對 seeds.csv.gz（repr）
⚠ 範圍：壞根週判定用 research11.load_bars（共用引擎）；① 只比買賣日期，不比 g
⇒ backtest/resultsLongD/check.json
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
OUT = "backtest/resultsLongD"
D.DATA = ST
cal = D.load_calendar(); n = len(cal)
mk = pd.read_csv(os.path.join(ST, "meta", "stocks.csv"), dtype=str).set_index("stock_id")["market"].to_dict()
TW = pd.read_csv(os.path.join(OUT, "trades_W.csv.gz"), dtype={"sid": str}, float_precision="round_trip")
TD = pd.read_csv(os.path.join(OUT, "trades_D.csv.gz"), dtype={"sid": str}, float_precision="round_trip")
S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
PT = pd.read_csv(os.path.join(OUT, "cells.csv"))
errs = []; info = {}
mon = (cal - pd.to_timedelta(cal.weekday, unit="D")).normalize()
wkid = pd.Series(pd.factorize(mon)[0], index=range(n))
wfirst_cal = wkid.reset_index().groupby(0)["index"].min().to_dict()


def machine(H, L, C, near, look):
    """另寫一份（同規則）：回 [(買訊 i, 賣訊 i 或 None)]。"""
    res = []; i = look; N = len(C)
    state = {"c": None, "tok": False, "bot": None}

    def reset():
        state.update(c=None, tok=False, bot=None)
    while i < N:
        c = state["c"]
        if c is not None and state["tok"] and state["bot"] is not None and C[i] > c[1]:
            if near[i]:
                reset(); i += 1; continue
            B = state["bot"]; hi = max(c[1], H[i]); nc = None; nt = False; nbt = None; sell = None
            for j in range(i + 1, N):
                if C[j] < B:
                    sell = j; break
                if H[j] > hi:
                    hi = H[j]; nc = (j, H[j]); nt = False; nbt = None
                elif nc is not None and not nt and j - nc[0] == 3 and max(H[nc[0] + 1:j + 1]) < nc[1]:
                    nt = True
                if nc is not None and nbt is None and j - 2 >= nc[0] and L[j - 2] < L[j - 1] < L[j]:
                    nbt = L[j - 2]
                if nc is not None and nt and nbt is not None:
                    B = nbt; nc = None; nt = False; nbt = None
            res.append((i, sell))
            if sell is None:
                return res
            i = sell + 1; reset(); continue
        if c is not None and state["tok"] and state["bot"] is not None and C[i] < state["bot"]:
            reset()
        prevmax = max(H[i - look:i])
        if H[i] > prevmax:
            state.update(c=(i, H[i]), tok=False, bot=None)
        elif state["c"] is not None:
            if H[i] >= state["c"][1]:
                reset()
            elif not state["tok"] and i - state["c"][0] == 3:
                state["tok"] = True
        c = state["c"]
        if c is not None and state["bot"] is None and i - 2 >= c[0] and L[i - 2] < L[i - 1] < L[i]:
            state["bot"] = L[i - 2]
        i += 1
    return res


rng = np.random.default_rng(20260929)
cands = sorted(set(TW["sid"]))
smp = list(rng.choice(cands, size=min(12, len(cands)), replace=False))
nbw = 0; nbd = 0; ncw = 0
for k_, s in enumerate(smp):
    st = D.load_stock(s, mk.get(s, "twse"), cal); df = st.df
    c = df["close"].to_numpy(float); v = np.isfinite(c); ix = np.flatnonzero(v)
    o, h, l = (df[x].to_numpy(float) for x in ("open", "high", "low"))
    tb = TR.one(s, cal); trd, up = np.asarray(tb["trd"], bool), np.asarray(tb["up_o"], bool)
    B = R.load_bars(s, mk.get(s, "twse"), cal)
    bad_k = B["next_bad"][:len(B["idx"])] == np.arange(len(B["idx"])); bad_day = np.zeros(n, bool); bad_day[B["idx"][bad_k]] = True
    g = pd.DataFrame({"d": ix, "w": wkid.to_numpy()[ix], "h": h[ix], "l": l[ix], "c": c[ix]}).groupby("w").agg(d0=("d", "min"), d1=("d", "max"), h=("h", "max"), l=("l", "min"), c=("c", "last"))
    wks = g.index.to_numpy(); badw = set(wkid.to_numpy()[bad_day])
    near = np.array([(w in badw) or (w - 1 in badw) or (w + 1 in badw) for w in wks])
    mine = []
    for bi, si in machine(g["h"].to_numpy(), g["l"].to_numpy(), g["c"].to_numpy(), near, 52):
        if bi + 1 >= len(wks) or wks[bi + 1] != wks[bi] + 1:
            continue
        ed = int(g["d0"].iloc[bi + 1])
        if ed != wfirst_cal[int(wks[bi + 1])] or not (trd[ed] and np.isfinite(o[ed]) and o[ed] > 0 and not up[ed]):
            continue
        mine.append((int(g["d1"].iloc[bi]), ed))
    ref = list(zip(TW.loc[TW["sid"] == s, "pos"].astype(int), TW.loc[TW["sid"] == s, "entry_pos"].astype(int)))
    ncw += 1
    if mine != ref:
        nbw += 1; errs.append(f"① {s} 週 自算 {len(mine)} 檔 {len(ref)}")
    if k_ < 4:
        idx = B["idx"]; nd = bad_k.copy(); nd[1:] |= bad_k[:-1]; nd[:-1] |= bad_k[1:]
        md = []
        for bi, si in machine(B["h"], B["l"], B["c"], nd, 250):
            if bi + 1 >= len(idx):
                continue
            ed = int(idx[bi + 1])
            if not (trd[ed] and np.isfinite(o[ed]) and o[ed] > 0 and not up[ed]):
                continue
            md.append((int(idx[bi]), ed))
        rd = list(zip(TD.loc[TD["sid"] == s, "pos"].astype(int), TD.loc[TD["sid"] == s, "entry_pos"].astype(int)))
        if md != rd:
            nbd += 1; errs.append(f"② {s} 日 自算 {len(md)} 檔 {len(rd)}")
info["① 週線 抽檔／不同"] = [ncw, nbw]; info["② 日線 抽 4 檔 不同"] = nbd
# ③
B50 = S["0050"]
lab = lambda c, m, b: "合格" if (c > b["cagr"] and c / abs(m) >= b["cagr"] / abs(b["mdd"])) else ("另列" if c > b["cagr"] else "不合格")
nb3 = 0
for _, r in PT.iterrows():
    for sg in ("探索", "確認", "早年"):
        if lab(r[f"{sg}_年化"], r[f"{sg}_回落"], B50[sg]) != r[f"{sg}_標籤"]:
            nb3 += 1; errs.append(f"③ {r['格']} {sg}")
    if bool(r["探索_持股"] < r["N"] / 2 or r["探索_現金"] > 0.30) != bool(r["退化"]):
        nb3 += 1; errs.append(f"③ {r['格']} 退化")
c = PT[(PT["mode"] == "W") & ~PT["退化"].astype(bool)].copy()
pk = None
if len(c):
    q = c[c["探索_標籤"] == "合格"] if (c["探索_標籤"] == "合格").any() else c
    pk = q.assign(r_=q["探索_年化"] / q["探索_回落"].abs()).sort_values(["r_", "探索_年化", "N"], ascending=[False, False, True]).iloc[0]["格"]
if pk != S["挑中格"]:
    nb3 += 1; errs.append("③ 挑格")
info["③ 挑中（自算）"] = pk; info["③ 不同"] = nb3
# ④
if pk:
    N = int(pk.split("_N")[1])
    SEED = pd.read_csv(os.path.join(OUT, "seeds.csv.gz"), float_precision="round_trip")
    for win, (x0, x1), segs in (("主", ("2017-03-02", "2026-08-24"), {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}),
                                ("早年", ("2005-01-03", "2014-12-31"), {"早年": ("2005-01-03", "2014-12-31")})):
        a0, a1 = int(cal.searchsorted(pd.Timestamp(x0))), int(cal.searchsorted(pd.Timestamp(x1)))
        T = TW[TW["elig"].astype(str) == "True"]
        T = T[(T["entry_pos"] >= a0) & (T["entry_pos"] <= a1)].sort_values(["entry_pos", "sid"]).reset_index(drop=True)
        sig = T[["sid", "pos", "entry_pos", "xpos_DB", "g_DB"]].assign(relvol=T["rs"].fillna(-1e9))
        cl, op = RR.load_prices(sorted(set(sig["sid"])), cal, pd.Series(mk), "branch"); cl, op = RR.pad_px_t1(cl, op)
        allsid = sorted(set(TW.loc[TW["elig"].astype(str) == "True", "sid"]) | set(TD.loc[TD["elig"].astype(str) == "True", "sid"]))
        SF = R.stop_force_days(R.valid_from_data(sorted(set(sig["sid"])), pd.Series(mk), cal), int(cal.searchsorted(pd.Timestamp("2026-08-24"))))
        o = R.simulate_mtm(sig, "DB", N, np.random.default_rng(1000), cl, op, n + 1, return_equity=True, log=[], d_max=None, pick="relvol", queue_days=0, stop_force=SF)
        eq = np.asarray(o["equity"], float)
        for sg, (x, y) in segs.items():
            aa, bb = int(cal.searchsorted(pd.Timestamp(x))), int(cal.searchsorted(pd.Timestamp(y)))
            cg, mg, _ = RR.win_metrics(eq, o["first"], o["end"], aa, bb)
            ref = SEED[(SEED["mode"] == "W") & (SEED["win"] == win) & (SEED["N"] == N) & (SEED["r"] == 0)].iloc[0]
            info[f"④ 種子0 {pk} {sg}（自跑／檔）"] = [float(cg), float(ref[f"{sg}_年化"])]
            if repr(float(cg)) != repr(float(ref[f"{sg}_年化"])):
                errs.append(f"④ {sg}")
info["錯誤數"] = len(errs)
json.dump({"info": info, "errors": errs[:40]}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(info, ensure_ascii=False, default=str)); [print("  ⛔", e) for e in errs[:15]]
print("查核：" + ("全過" if not errs else "⛔ 不過"))
