# -*- coding: utf-8 -*-
"""seq527 二：S87 假訊號前組的組成描述（⛔ 不碰任何報酬）。
照 returns_add.py 的 shuffle_V 逐月重建假訊號前組（default_rng(5)、同順序），比對 monthly/S87_shuffle.csv 的 ntop；
再比前組與母體的市值、股價（未還原）、上櫃比例、真 S87 值、母體內缺 S87 的檔數。輸出 ~/scanadd/shuffle_comp_add.csv。"""
import os
import numpy as np, pandas as pd
import snap
from backtest import data as D
D = snap.fix()
BASE = snap.BASE; FAC = os.path.join(BASE, "factors"); CACHE = os.path.join(BASE, "cache")
U_df = pd.read_parquet(os.path.join(FAC, "universe.parquet"))
U = U_df.to_numpy(bool); sids = list(U_df.columns); me = pd.DatetimeIndex(pd.to_datetime(U_df.index)); NM = len(me)
hold = np.array([str(d.to_period("M") + 1) for d in me])
seg = np.where((hold >= "2017-03") & (hold <= "2021-12"), "探索", np.where((hold >= "2022-01") & (hold <= "2026-08"), "確認", ""))
P = np.load(os.path.join(CACHE, "panel.npz")); cal = pd.DatetimeIndex(pd.to_datetime(P["cal"])); assert list(P["sids"]) == sids
RC = pd.DataFrame(np.where(P["VALID"] == 1, P["RC"], np.nan)).ffill(limit=5).to_numpy()
SH = pd.DataFrame(P["SH"].astype(float)).ffill(limit=5).to_numpy()
mpos = np.array([cal.get_loc(d) for d in me]); PX = RC[mpos]; MCAP = PX * SH[mpos]; MCAP[~(MCAP > 0)] = np.nan
mk = pd.read_csv(os.path.join(CACHE, "universe_meta.csv"), dtype=str).set_index("stock_id").loc[sids, "market"].to_numpy()
OTC = (mk == "tpex")


def shuffle_V(V, rng):          # 與 returns_add.py／resultsScan64 returns.py 相同
    S = np.full_like(V, np.nan)
    for i in range(NM):
        ok = U[i] & np.isfinite(V[i]); idx = np.flatnonzero(ok)
        S[i, idx] = V[i, idx][rng.permutation(len(idx))]
    return S


def topq(V, i):
    ok = U[i] & np.isfinite(V[i])
    pct = pd.Series(np.where(ok, V[i], np.nan)).rank(pct=True, method="average").to_numpy()
    return ok & (pct > 0.8), ok


out = []
for code in ("S87", "S29", "S30"):
    V = pd.read_parquet(os.path.join(FAC, f"{code}.parquet")).reindex(index=U_df.index, columns=sids).to_numpy(float)
    S = shuffle_V(V, np.random.default_rng(5))
    ref = pd.read_csv(os.path.join(BASE, "monthly", f"{code}_shuffle.csv"))
    V87 = pd.read_parquet(os.path.join(FAC, "S87.parquet")).reindex(index=U_df.index, columns=sids).to_numpy(float)
    for i in range(NM):
        if not seg[i]:
            continue
        ts, ok = topq(S, i); tr, _ = topq(V, i); u = U[i]
        assert int(ts.sum()) == int(ref.loc[i, "ntop"]), (code, i)
        def d(m):
            return dict(n=int(m.sum()), lmcap_med=float(np.nanmedian(np.log10(MCAP[i][m]))), px_med=float(np.nanmedian(PX[i][m])),
                        otc=float(OTC[m].mean()), s87_mean=float(np.nanmean(V87[i][m])))
        a, b, c = d(ts), d(u), d(tr)
        out.append(dict(code=code, form=str(me[i].date()), seg=seg[i], u_missing=int((u & ~np.isfinite(V[i])).sum()),
                        **{f"shuf_{k}": v for k, v in a.items()}, **{f"uni_{k}": v for k, v in b.items()}, **{f"real_{k}": v for k, v in c.items()}))
df = pd.DataFrame(out); df.to_csv(os.path.join(BASE, "shuffle_comp_add.csv"), index=False)
for (code, sg), g in df.groupby(["code", "seg"], sort=False):
    print(code, sg, "母體缺值檔數中位", g.u_missing.median(),
          "｜log10市值中位 假前組/母體/真前組", round(g.shuf_lmcap_med.mean(), 3), round(g.uni_lmcap_med.mean(), 3), round(g.real_lmcap_med.mean(), 3),
          "｜股價中位", round(g.shuf_px_med.mean(), 1), round(g.uni_px_med.mean(), 1), round(g.real_px_med.mean(), 1),
          "｜上櫃比例", round(g.shuf_otc.mean(), 3), round(g.uni_otc.mean(), 3), round(g.real_otc.mean(), 3),
          "｜真S87平均", round(g.shuf_s87_mean.mean(), 2), round(g.uni_s87_mean.mean(), 2), round(g.real_s87_mean.mean(), 2),
          "｜假前組市值中位>母體的月比例", round((g.shuf_lmcap_med > g.uni_lmcap_med).mean(), 3))
print("ntop 重建與 monthly/*_shuffle.csv 一致")
