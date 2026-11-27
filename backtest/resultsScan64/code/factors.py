# -*- coding: utf-8 -*-
"""scan55 step 2：各因子月底值與事件表（只算因子值與事件日期，⛔ 不算持有期報酬、超額、IC、價差）。
讀 cache/panel.npz（panel.py）；輸出 factors/<S號>.parquet（月底 × 股票）、factors/<S號>_events.csv、factors/universe.parquet。
重用：backtest.data、backtest.research34.load_revenue、backtest.researchLongPool（load_filing、qkey、rev_avail）。
"""
import os, sys, glob, json
from multiprocessing import Pool
import numpy as np, pandas as pd
from backtest import data as D
from backtest import research34 as R34
from backtest import researchLongPool as RLP
import snap; D = snap.fix()   # ⚠ import researchLongPool 會換 D.DATA；改指 scan64 快照（origin/main 9e1316ff3c）

HERE = snap.BASE   # 沒設 SCAN_BASE 時＝本檔所在資料夾（同 64 格）
CACHE = os.path.join(HERE, "cache")
FAC = os.path.join(HERE, "factors"); os.makedirs(FAC, exist_ok=True)
FD = snap.SNAP          # 預設 origin/main 9e1316ff3c 抽出（全部資料同一快照）；補格用 SCAN_SNAP
TAIEX = os.path.expanduser("~/msdata/us_macro/c10a1d00c358760fb8780b79863068eca9341dfc/twse_taiex.csv")
FIRST_ME, LAST_ME = "2016-06", "2026-08"           # 快取的形成月範圍（計數另依段落裁）

# ───────────────────────── 基本 ─────────────────────────
P = np.load(os.path.join(CACHE, "panel.npz"))
cal = pd.DatetimeIndex(pd.to_datetime(P["cal"]))
sids = [str(s) for s in P["sids"]]
T, N = len(cal), len(sids)
M = {k: P[k].astype(np.float64) for k in ["C", "O", "H", "L", "V", "A", "RC", "SH", "LIM1", "UP", "BAD", "VALID"]}
VALID = M["VALID"] == 1
for k in ["C", "O", "H", "L", "A", "RC", "V"]:
    M[k][~VALID] = np.nan
BAD = np.nan_to_num(M["BAD"]) > 0
meta = pd.read_csv(os.path.join(CACHE, "universe_meta.csv"), dtype=str).set_index("stock_id").loc[sids]
FS_ = pd.to_datetime(meta["first_seen"]).values; LS_ = pd.to_datetime(meta["last_seen"]).values

ym = cal.to_period("M")
me_pos = np.array([np.flatnonzero(ym == p)[-1] for p in ym.unique()])
me_dates = cal[me_pos]
sel = (me_dates.to_period("M") >= pd.Period(FIRST_ME)) & (me_dates.to_period("M") <= pd.Period(LAST_ME))
me_pos, me_dates = me_pos[sel], me_dates[sel]
NM = len(me_pos)


def cs(x):
    x = np.nan_to_num(np.asarray(x, float))
    return np.vstack([np.zeros((1,) + x.shape[1:]), np.cumsum(x, axis=0)])


def W(c, L):
    """長度 L、結尾於各月底（含）的窗內和。"""
    hi = me_pos + 1; lo = np.maximum(hi - L, 0)
    out = c[hi] - c[lo]
    out[me_pos + 1 - L < 0] = np.nan
    return out


CS_BAD = cs(BAD)


def badwin(L):
    """窗 (t−L, t] 內有壞根（research11 缺口 ≥5 日／斷點／幽靈事件）⇒ True。"""
    return W(CS_BAD, L) > 0


Cff = pd.DataFrame(M["C"]).ffill(limit=5).to_numpy()
RCff = pd.DataFrame(M["RC"]).ffill(limit=5).to_numpy()
SHff = pd.DataFrame(M["SH"]).ffill(limit=5).to_numpy()
Rd = M["C"][1:] / M["C"][:-1] - 1
Rd = np.vstack([np.full((1, N), np.nan), Rd]); Rd[BAD] = np.nan
Rd[np.abs(Rd) > 0.5] = np.nan


def at(x, lag=0):
    p = me_pos - lag
    out = x[np.maximum(p, 0)].astype(float)
    out[p < 0] = np.nan
    return out


def roll(x, L, fn, minp):
    r = getattr(pd.DataFrame(x).rolling(L, min_periods=minp), fn)()
    return r.to_numpy()[me_pos]


def save(code, arr, binary=False):
    df = pd.DataFrame(arr.astype(np.float32), index=me_dates.strftime("%Y-%m-%d"), columns=sids)
    df.to_parquet(os.path.join(FAC, f"{code}.parquet"))
    print(code, "nonnan", int(np.isfinite(arr).sum()), flush=True)


def save_events(code, ev):
    ev = pd.DataFrame(ev, columns=["stock_id", "event_date", "entry_date", "kind"])
    ev.to_csv(os.path.join(FAC, f"{code}_events.csv"), index=False)
    print(code, "events", len(ev), flush=True)


# ───────────────────────── 母體 ─────────────────────────
def universe():
    nv = W(cs(VALID), 250)
    a = np.where(VALID, np.nan_to_num(M["A"]), 0)
    amt60 = W(cs(a), 60) / np.maximum(W(cs(VALID), 60), 1)
    t = me_dates.values[:, None]
    alive = (FS_[None, :] <= t) & (LS_[None, :] >= t)
    U = alive & (nv >= 200) & (amt60 >= 1e7)
    pd.DataFrame(U, index=me_dates.strftime("%Y-%m-%d"), columns=sids).to_parquet(os.path.join(FAC, "universe.parquet"))
    return U


# ───────────────────────── 價量 ─────────────────────────
def price_factors():
    c0 = at(Cff)
    def ret(L, skip=0):
        v = at(Cff, skip) / at(Cff, L) - 1
        v[badwin(L)] = np.nan
        return v
    save("S01", ret(252, 21))
    save("S02", ret(21))
    ma = pd.DataFrame(Cff).rolling(240, min_periods=200).mean().to_numpy()
    v = ((c0 > at(ma)) & (at(ma) > at(ma, 20))).astype(float)
    v[~np.isfinite(at(ma)) | ~np.isfinite(at(ma, 20)) | ~np.isfinite(c0) | badwin(260)] = np.nan
    save("S05", v, True)
    v = roll(M["V"], 20, "mean", 15) / roll(M["V"], 120, "mean", 90); v[badwin(120)] = np.nan
    save("S06", v)
    v = W(cs(M["V"]), 20) / at(SHff); v[~(at(SHff) > 0)] = np.nan
    save("S07", v)
    v = roll(Rd, 60, "std", 50); save("S08", v)
    # beta、特異波動：對加權指數日報酬（us-stock-data twse_taiex.csv，價格指數）
    tx = pd.read_csv(TAIEX, dtype={"date": str}); tx["date"] = pd.to_datetime(tx["date"])
    m = tx.set_index("date")["close"].reindex(cal).astype(float)
    mr = (m / m.shift(1) - 1).to_numpy()
    ok = np.isfinite(Rd) & np.isfinite(mr)[:, None]
    r0 = np.where(ok, Rd, 0); m0 = np.where(ok, mr[:, None], 0)
    C = {k: cs(x) for k, x in dict(n=ok.astype(float), r=r0, m=m0, rm=r0 * m0, rr=r0 * r0, mm=m0 * m0).items()}
    def reg(L, minp):
        n = W(C["n"], L); sr, sm, srm, srr, smm = (W(C[k], L) for k in ("r", "m", "rm", "rr", "mm"))
        cov = srm - sr * sm / n; vm = smm - sm * sm / n; vr = srr - sr * sr / n
        beta = cov / vm; res = (vr - beta * cov) / (n - 2)
        beta[n < minp] = np.nan; res[n < minp] = np.nan
        return beta, np.sqrt(np.maximum(res, 0))
    b250, _ = reg(250, 200); save("S09", b250)
    _, iv60 = reg(60, 50); save("S81", iv60)
    save("S10", roll(Rd, 20, "max", 15))
    lim = np.where(VALID, M["LIM1"], np.nan)
    save("S11", roll(lim, 20, "sum", 15))
    save("S14", ret(126))
    save("S15", at(RCff))
    am = np.abs(Rd) / M["A"]; save("S16", roll(am, 20, "mean", 15))
    save("S17", roll(M["A"], 20, "mean", 15))
    save("S78", ret(756))
    save("S79", ret(5))
    mn = pd.DataFrame(Cff).rolling(252, min_periods=200).min().to_numpy()
    v = c0 / at(mn); v[badwin(252)] = np.nan; save("S80", v)
    save("S82", roll(Rd, 60, "skew", 50))
    up = np.where(VALID, M["UP"], np.nan)
    save("S83alt", roll(up, 20, "sum", 15))     # ⚠ research11 規則推算漲停價（非官方）；登錄要官方 ⇒ 只當備註
    # S12 向上跳空（事件）：開盤（還原）＞前一交易日最高（還原），兩日皆有效且相鄰、非壞根
    O, H = M["O"], M["H"]
    g = np.zeros((T, N), bool)
    g[1:] = (O[1:] > H[:-1]) & VALID[1:] & VALID[:-1] & ~BAD[1:]
    ev = []
    for j in range(N):
        for p in np.flatnonzero(g[:, j]):
            if p + 1 < T:
                ev.append((sids[j], cal[p].date(), cal[p + 1].date(), "gap_up"))
    save_events("S12", ev)
    # S64 季節性（Heston–Sadka 讀法）：持有月同曆月、過去各年該月月報酬平均（≥2 年）
    cme = Cff[me_pos]
    mr_ = np.full((NM, N), np.nan); mr_[1:] = cme[1:] / cme[:-1] - 1
    bw = np.zeros((NM, N), bool)
    cb = CS_BAD
    for i in range(1, NM):
        bw[i] = (cb[me_pos[i] + 1] - cb[me_pos[i - 1] + 1]) > 0
    mr_[bw] = np.nan
    # 補 2015 年各月（快取從 FIRST_ME 起）：另算全期月底
    allme = np.array([np.flatnonzero(ym == p)[-1] for p in ym.unique()])
    ca = Cff[allme]; ra = np.full((len(allme), N), np.nan); ra[1:] = ca[1:] / ca[:-1] - 1
    for i in range(1, len(allme)):
        if ((cb[allme[i] + 1] - cb[allme[i - 1] + 1]) > 0).any():
            ra[i][(cb[allme[i] + 1] - cb[allme[i - 1] + 1]) > 0] = np.nan
    amon = cal[allme].month.values; adate = cal[allme]
    v = np.full((NM, N), np.nan)
    for i, t in enumerate(me_dates):
        hm = (t.month % 12) + 1
        rows = np.flatnonzero((amon == hm) & (adate < t))
        if len(rows) >= 2:
            x = ra[rows]
            cnt = np.isfinite(x).sum(0)
            mu = np.nanmean(np.where(np.isfinite(x), x, np.nan), axis=0)
            mu[cnt < 2] = np.nan
            v[i] = mu
    save("S64", v)


# ───────────────────────── 籌碼 ─────────────────────────
def _load_chip(sid):
    out = {}
    for sub, cols in (("stocks_inst", ["foreign", "trust", "dealer", "total"]), ("stocks_margin", ["m_balance", "m_limit", "s_balance"])):
        p = os.path.join(D.DATA, sub, f"{sid}.csv")
        if not os.path.exists(p):
            for c in cols:
                out[c] = np.full(T, np.nan)
            continue
        x = pd.read_csv(p, dtype={"date": str}); x["date"] = pd.to_datetime(x["date"])
        x = x.drop_duplicates("date").set_index("date").reindex(cal)
        for c in cols:
            out[c] = pd.to_numeric(x[c], errors="coerce").to_numpy(float) if c in x else np.full(T, np.nan)
    return out


def chip_factors():
    with Pool(6) as pool:
        res = pool.map(_load_chip, sids, chunksize=20)
    X = {k: np.stack([r[k] for r in res], axis=1) for k in res[0]}
    f = X["foreign"]
    run = np.zeros(N); runs = np.full((T, N), np.nan)
    for p in range(T):
        pos = np.nan_to_num(f[p]) > 0
        run = np.where(pos, run + 1, 0); runs[p] = run
    v = runs[me_pos].copy(); v[~np.isfinite(f[me_pos]) & (v == 0)] = np.nan
    save("S18", v)
    tr = X["trust"]
    v = W(cs(tr), 5) / at(SHff); v[~(at(SHff) > 0) | (W(cs(np.isfinite(tr)), 5) < 3)] = np.nan
    save("S19", v)
    vm20 = roll(M["V"], 20, "mean", 15)
    for code, k in (("S21", "dealer"), ("S22", "total")):
        x = X[k]; v = W(cs(x), 5) / vm20; v[(W(cs(np.isfinite(x)), 5) < 3) | ~(vm20 > 0)] = np.nan
        save(code, v)
    mb, ml, sb = X["m_balance"], X["m_limit"], X["s_balance"]
    mbf = pd.DataFrame(mb).ffill(limit=5).to_numpy()
    v = at(mbf) / at(mbf, 20) - 1; v[~(at(mbf, 20) > 0)] = np.nan; save("S23", v)
    v = at(mbf) / at(pd.DataFrame(ml).ffill(limit=5).to_numpy()); v[~np.isfinite(v)] = np.nan; save("S24", v)
    v = at(pd.DataFrame(sb).ffill(limit=5).to_numpy()) / at(mbf); v[~(at(mbf) > 0)] = np.nan; save("S25", v)
    # S20 投信首次大買（事件）：當日投信買超 × 未還原收盤 ≥ 1,000 萬，且前 60 個交易日投信無一日買超（有資料日 ≥ 40）
    big = (np.nan_to_num(tr) * np.nan_to_num(M["RC"]) >= 1e7) & VALID
    buy = cs(np.nan_to_num(tr) > 0); has = cs(np.isfinite(tr))
    ev = []
    for p in range(61, T - 1):
        nb = buy[p] - buy[p - 60]; nh = has[p] - has[p - 60]
        hit = big[p] & (nb == 0) & (nh >= 40)
        for j in np.flatnonzero(hit):
            ev.append((sids[j], cal[p].date(), cal[p + 1].date(), "trust_first_big"))
    save_events("S20", ev)


def tdcc_factors():
    L = []
    for f in sorted(glob.glob(os.path.join(D.DATA, "tdcc_hist", "*.parquet"))):
        x = pd.read_parquet(f, columns=["date", "stock_id", "level", "people", "pct"])
        x["level"] = x["level"].astype(int)
        x = x[x["level"].isin([1, 2, 3, 4, 5, 15, 17])]
        x["date"] = pd.to_datetime(x["date"].astype(str)); x["stock_id"] = x["stock_id"].astype(str)
        L.append(x[x["stock_id"].isin(sids)])
    x = pd.concat(L)
    retail = x[x.level <= 5].groupby(["date", "stock_id"])["pct"].sum().unstack()
    ppl = x[x.level == 17].groupby(["date", "stock_id"])["people"].sum().unstack()
    big = x[x.level == 15].groupby(["date", "stock_id"])["people"].sum().unstack()
    dates = retail.index.sort_values()
    out = {}
    for code, tab, kind in (("S26", retail, "diff"), ("S27", ppl, "pct"), ("S28", big, "pct")):
        tab = tab.reindex(index=dates, columns=sids)
        v = np.full((NM, N), np.nan)
        for i, t in enumerate(me_dates):
            k = dates.searchsorted(t, side="right") - 1
            if k < 4 or (t - dates[k]).days > 14 or (dates[k] - dates[k - 4]).days > 35:     # 4 週前那一筆須真的在 4～5 週前（2018～2019 有斷週）
                continue
            a, b = tab.iloc[k].to_numpy(float), tab.iloc[k - 4].to_numpy(float)
            if kind == "diff":
                v[i] = a - b
            else:
                with np.errstate(all="ignore"):
                    v[i] = np.where(b > 0, a / b - 1, np.nan)
        save(code, v)


def foreign_holding():
    L = [pd.read_csv(f, dtype={"stock_id": str}, usecols=["date", "stock_id", "foreign_pct"]) for f in sorted(glob.glob(os.path.join(FD, "meta", "foreign_holding", "foreign_holding_*.csv")))]
    x = pd.concat(L); x["date"] = pd.to_datetime(x["date"])
    x["foreign_pct"] = pd.to_numeric(x["foreign_pct"], errors="coerce")
    tab = x.drop_duplicates(["date", "stock_id"], keep="last").pivot(index="date", columns="stock_id", values="foreign_pct").reindex(columns=sids)
    d = tab.index.sort_values()
    v = np.full((NM, N), np.nan)
    for i, t in enumerate(me_dates):
        k = d.searchsorted(t, side="right") - 1
        if k >= 0 and (t - d[k]).days <= 10:
            v[i] = tab.loc[d[k]].to_numpy(float)
    save("S67", v)


# ───────────────────────── 營收 ─────────────────────────
def revenue_factors():
    rev, rev_ly, ind = R34.load_revenue()
    rev = rev.reindex(columns=sids); rev_ly = rev_ly.reindex(columns=sids)
    per = list(rev.index)
    yoy = rev / rev_ly - 1; yoy[~(rev_ly > 0)] = np.nan
    R = rev.to_numpy(float); Y = yoy.to_numpy(float)
    np_ = len(per)
    def sh(A, k):
        out = np.full_like(A, np.nan); out[k:] = A[:-k]; return out
    mom = R / sh(R, 1) - 1; mom[~(sh(R, 1) > 0)] = np.nan
    run = np.zeros(N); cons = np.full_like(R, np.nan)
    for i in range(np_):
        y = Y[i]; run = np.where(np.isfinite(y) & (y > 0), run + 1, 0); cons[i] = np.where(np.isfinite(y), run, np.nan)
    acc = Y - sh(Y, 3)
    ma3 = pd.DataFrame(R).rolling(3, min_periods=3).mean().to_numpy(); ma12 = pd.DataFrame(R).rolling(12, min_periods=12).mean().to_numpy()
    gx = ((ma3 > ma12) & (sh(ma3, 1) <= sh(ma12, 1))).astype(float)
    gx[~(np.isfinite(ma12) & np.isfinite(sh(ma12, 1)))] = np.nan
    mx24 = pd.DataFrame(R).shift(1).rolling(24, min_periods=24).max().to_numpy()
    hi24 = (R >= mx24).astype(float); hi24[~np.isfinite(mx24) | ~np.isfinite(R)] = np.nan
    first = ((hi24 == 1) & (sh(hi24, 1) == 0)).astype(float); first[~np.isfinite(hi24) | ~np.isfinite(sh(hi24, 1))] = np.nan
    # 季節性驚奇：e＝ln(rev/rev_ly)；驚奇＝(e − 前 12 月 e 平均) ÷ 前 12 月 e 標準差（≥10 個）
    with np.errstate(all="ignore"):
        e = np.log(rev.to_numpy(float) / rev_ly.to_numpy(float))
    e[~np.isfinite(e)] = np.nan
    ed = pd.DataFrame(e).shift(1)
    sur = (e - ed.rolling(12, min_periods=10).mean().to_numpy()) / ed.rolling(12, min_periods=10).std().to_numpy()
    # 產業內年增排名
    im = pd.read_csv(os.path.join(D.DATA, "meta", "industry.csv"), dtype=str).set_index("stock_id")["industry_code"]
    grp = pd.Series([im.get(s, ind.get(s, np.nan)) for s in sids])
    yr = pd.DataFrame(Y, columns=sids)
    rank = np.full_like(Y, np.nan)
    for gname, cols in grp.groupby(grp).groups.items():
        cidx = np.array(list(cols))
        sub = pd.DataFrame(Y[:, cidx])
        cnt = sub.notna().sum(1).to_numpy()
        rk = sub.rank(axis=1, pct=True).to_numpy().copy(); rk[cnt < 5] = np.nan
        rank[:, cidx] = rk
    avail = [RLP.rev_avail(p) for p in per]
    def pick(A):
        v = np.full((NM, N), np.nan)
        for i, t in enumerate(me_dates):
            ok = [k for k, a in enumerate(avail) if a < t]
            if ok:
                v[i] = A[ok[-1]]
        return v
    for code, A, b in (("S33", mom, 0), ("S34", cons, 0), ("S35", acc, 0), ("S36", gx, 1), ("S38", rank, 0), ("S73", first, 1), ("S77", sur, 0)):
        save(code, pick(A), b)
    # 事件：S37 創 2015 以來新高（前面 ≥24 個月有值）；S76 年增由負轉正（上月 <0、本月 >0）
    hist_max = pd.DataFrame(R).shift(1).expanding(min_periods=24).max().to_numpy()
    nprior = pd.DataFrame(np.isfinite(R).astype(float)).shift(1).expanding().sum().to_numpy()
    ath = (R > hist_max) & (nprior >= 24)
    turn = (Y > 0) & (sh(Y, 1) < 0)
    for code, A, kind in (("S37", ath, "rev_ath"), ("S76", turn, "yoy_turn_pos")):
        ev = []
        for i, p in enumerate(per):
            e_ = int(cal.searchsorted(avail[i], side="right"))     # 可用日（10／15 日）之後第一個交易日
            if e_ >= T:
                continue
            for j in np.flatnonzero(A[i]):
                ev.append((sids[j], cal[e_].date(), cal[e_].date(), f"{kind}:{p}"))
        save_events(code, ev)


# ───────────────────────── 財報 ─────────────────────────
def _qk_period(s):
    return int(s[:4]) * 4 + int(s[-1]) - 1


def _deadline(k):
    y, q = k // 4, k % 4 + 1
    return {1: pd.Timestamp(y, 5, 15), 2: pd.Timestamp(y, 8, 14), 3: pd.Timestamp(y, 11, 14), 4: pd.Timestamp(y + 1, 3, 31)}[q]


def fs_factors():
    fmin, _ = RLP.load_filing(FD)
    # fs_xbrl
    L = []
    for f in sorted(glob.glob(os.path.join(FD, "meta", "fs_xbrl", "fs_xbrl_*.csv"))):
        L.append(pd.read_csv(f, dtype={"stock_id": str}))
    X = pd.concat(L); X["_r"] = (X["report"] != "cr").astype(int)
    X = X.sort_values(["stock_id", "period", "_r"]).drop_duplicates(["stock_id", "period"], keep="first")
    X["qk"] = X["period"].map(_qk_period)
    X = X[X.stock_id.isin(sids)]
    num = ["inventories", "accounts_receivable", "accounts_receivable_related", "notes_receivable", "contract_liabilities_current", "contract_liabilities_noncurrent",
           "cash", "total_assets", "total_equity", "revenue_ytd", "net_income_ytd", "operating_cash_flow_ytd", "depreciation_ytd", "gross_profit_ytd", "operating_income_ytd"]
    for c in num:
        X[c] = pd.to_numeric(X[c], errors="coerce")
    # bs_hist（各檔各讀 header）
    B = []
    for f in sorted(glob.glob(os.path.join(FD, "mops", "bs_hist", "*.csv"))):
        b = os.path.basename(f); k = int(b[:4]) * 4 + int(b[5]) - 1
        x = pd.read_csv(f, dtype={"stock_id": str})
        y = pd.DataFrame({"stock_id": x["stock_id"], "qk": k})
        for cs_, nm in ((("流動資產",), "ca"), (("流動負債",), "cl_"), (("負債總計", "負債總額"), "liab"), (("資產總計", "資產總額"), "ta_b"), (("股本",), "cap"), (("非流動負債",), "ncl")):
            c = next((z for z in cs_ if z in x.columns), None)          # 2015～2017Q4 ci 檔名為「負債總額」（各檔各讀 header）
            y[nm] = pd.to_numeric(x[c], errors="coerce") if c is not None else np.nan
        B.append(y)
    B = pd.concat(B).drop_duplicates(["stock_id", "qk"], keep="last")
    E = []
    for f in sorted(glob.glob(os.path.join(FD, "mops", "fs_hist", "*.csv"))):
        b = os.path.basename(f); k = int(b[:4]) * 4 + int(b[5]) - 1
        x = pd.read_csv(f, dtype={"stock_id": str})
        c = "基本每股盈餘（元）"
        E.append(pd.DataFrame({"stock_id": x["stock_id"], "qk": k, "eps_ytd": pd.to_numeric(x[c], errors="coerce") if c in x.columns else np.nan}))
    E = pd.concat(E).drop_duplicates(["stock_id", "qk"], keep="last")
    RD = pd.concat([pd.read_csv(f, dtype={"stock_id": str}) for f in sorted(glob.glob(os.path.join(FD, "mops", "rd_hist", "*.csv")))])
    RD["_r"] = (RD["report"] != "cr").astype(int)
    RD = RD.sort_values(["stock_id", "period", "_r"]).drop_duplicates(["stock_id", "period"], keep="first")
    RD["qk"] = RD["period"].map(_qk_period)
    RD = RD[["stock_id", "qk", "rd_ytd", "rev_ytd"]].rename(columns={"rev_ytd": "rd_rev_ytd"})
    Q = X.merge(B, on=["stock_id", "qk"], how="outer").merge(E, on=["stock_id", "qk"], how="outer").merge(RD, on=["stock_id", "qk"], how="outer")
    Q = Q[Q.stock_id.isin(sids)]
    kmin, kmax = Q.qk.min(), Q.qk.max()
    ks = np.arange(kmin, kmax + 1); NK = len(ks)
    sidx = {s: i for i, s in enumerate(sids)}
    def mat(c):
        A = np.full((NK, N), np.nan)
        A[(Q.qk - kmin).to_numpy(), Q.stock_id.map(sidx).to_numpy()] = pd.to_numeric(Q[c], errors="coerce").to_numpy(float)
        return A
    def single(A):
        out = A.copy(); prev = np.vstack([np.full((1, N), np.nan), A[:-1]])
        notq1 = (ks % 4 != 0)[:, None]
        out = np.where(notq1, A - prev, A)
        return out
    def ttm(A):
        return pd.DataFrame(A).rolling(4, min_periods=4).sum().to_numpy()
    def lag(A, k):
        out = np.full_like(A, np.nan); out[k:] = A[:-k]; return out
    rev, gp, oi, ni = (single(mat(c)) for c in ("revenue_ytd", "gross_profit_ytd", "operating_income_ytd", "net_income_ytd"))
    dep = single(mat("depreciation_ytd")); eps = single(mat("eps_ytd")); rd = single(mat("rd_ytd")); rdrev = single(mat("rd_rev_ytd"))
    ta, te, inv, cash = mat("total_assets"), mat("total_equity"), mat("inventories"), mat("cash")
    ar = np.nansum(np.stack([mat("accounts_receivable"), mat("accounts_receivable_related"), mat("notes_receivable")]), axis=0)
    ar[np.all(~np.isfinite(np.stack([mat("accounts_receivable"), mat("accounts_receivable_related"), mat("notes_receivable")])), axis=0)] = np.nan
    a1, a2 = mat("contract_liabilities_current"), mat("contract_liabilities_noncurrent")
    cl = np.where(np.isfinite(a1) | np.isfinite(a2), np.nan_to_num(a1) + np.nan_to_num(a2), np.nan)
    ca, cl_, liab, tab, cap, ncl = (mat(c) for c in ("ca", "cl_", "liab", "ta_b", "cap", "ncl"))
    with np.errstate(all="ignore"):
        pos = lambda a: np.where(a > 0, a, np.nan)
        gm = gp / pos(rev); om = oi / pos(rev)
        f = {}
        f["S39"] = (eps - lag(eps, 4)) / np.where(lag(eps, 4) != 0, np.abs(lag(eps, 4)), np.nan)
        f["S40"] = gm - lag(gm, 4)
        f["S41"] = om - lag(om, 4)
        f["S42"] = ttm(ni) / pos((te + lag(te, 4)) / 2)
        f["S43"] = ttm(ni) / pos((ta + lag(ta, 4)) / 2)
        f["S44"] = liab / pos(tab)
        f["S45"] = ca / pos(cl_)
        f["S47"] = (inv / pos(lag(inv, 4)) - 1) - (rev / pos(lag(rev, 4)) - 1)
        f["S48"] = (ar / pos(lag(ar, 4)) - 1) - (rev / pos(lag(rev, 4)) - 1)
        f["S49"] = (cl - lag(cl, 1)) / pos(ta)
        f["S88"] = ttm(rd) / pos(ttm(rdrev))
        f["S90"] = cap / pos(lag(cap, 4)) - 1
        roa = ttm(ni) / pos(ta); lev = ncl / pos(tab); cr = ca / pos(cl_)
        gmt = ttm(gp) / pos(ttm(rev)); ato = ttm(rev) / pos(ta)
        parts = [roa > 0, roa > lag(roa, 4), lev < lag(lev, 4), cr > lag(cr, 4), cap <= lag(cap, 4), gmt > lag(gmt, 4), ato > lag(ato, 4)]
        okp = [np.isfinite(roa), np.isfinite(roa) & np.isfinite(lag(roa, 4)), np.isfinite(lev) & np.isfinite(lag(lev, 4)), np.isfinite(cr) & np.isfinite(lag(cr, 4)),
               np.isfinite(cap) & np.isfinite(lag(cap, 4)), np.isfinite(gmt) & np.isfinite(lag(gmt, 4)), np.isfinite(ato) & np.isfinite(lag(ato, 4))]
        fs7 = np.sum(parts, axis=0).astype(float); fs7[~np.all(okp, axis=0)] = np.nan
        f["S52"] = fs7
        ebitda = ttm(oi) + ttm(dep)
    # 可用季：上傳時戳 ≤ 月底（bigrun_monthly 口徑：uploaded_at ＜ 月底隔天 00:00）；且 ≥ 最近到期季 − 1
    upl = np.full((NK, N), np.datetime64("NaT"), dtype="datetime64[ns]")
    for (s, k), d in fmin.items():
        if s in sidx and kmin <= k <= kmax:
            upl[k - kmin, sidx[s]] = np.datetime64(d)
    kq = np.full((NM, N), -1)
    for i, t in enumerate(me_dates):
        lim = np.datetime64(t + pd.Timedelta(days=1))
        okm = upl < lim
        due = max(k for k in ks if _deadline(k) < t)
        cand = np.where(okm, ks[:, None], -1).max(axis=0)
        cand[cand < due - 1] = -1
        kq[i] = cand
    def pick(A):
        v = np.full((NM, N), np.nan)
        for i in range(NM):
            k = kq[i]; m_ = k >= 0
            v[i, m_] = A[k[m_] - kmin, np.flatnonzero(m_)]
        return v
    for code, A in f.items():
        save(code, pick(A), code == "S52")
    # S70 上傳早晚：最近到期季（期限 ＜ 月底）的上傳日 − 法定期限（日曆天），月底前未上傳 ⇒ 空
    v = np.full((NM, N), np.nan)
    for i, t in enumerate(me_dates):
        due = max(k for k in ks if _deadline(k) < t)
        u = upl[due - kmin]
        okm = u < np.datetime64(t + pd.Timedelta(days=1))
        v[i, okm] = (u[okm] - np.datetime64(_deadline(due))).astype("timedelta64[D]").astype(float)
    save("S70", v)
    # 價值：市值＝未還原收盤 × 股數（stocks 每列 shares）
    mcap = at(RCff) * at(SHff)
    mcap[~(mcap > 0)] = np.nan
    save("S57", mcap)
    rev_m, rev_ly, _ = R34.load_revenue(); rev_m = rev_m.reindex(columns=sids)
    per = list(rev_m.index); avail = [RLP.rev_avail(p) for p in per]
    r12 = rev_m.rolling(12, min_periods=12).sum().to_numpy() * 1000      # 千元 → 元
    v = np.full((NM, N), np.nan)
    for i, t in enumerate(me_dates):
        ok = [k for k, a in enumerate(avail) if a < t]
        if ok:
            v[i] = r12[ok[-1]] / mcap[i]
    save("S54", v)
    cash_k, liab_k, eb_k = pick(cash), pick(liab * 1000), pick(ebitda)   # bs_hist 千元 ⇒ ×1000；fs_xbrl 元
    evv = (mcap + liab_k - cash_k) / np.where(eb_k > 0, eb_k, np.nan)
    save("S56", evv)


# ───────────────────────── 事件（名冊、除權息、減資、處置、注意、信用資格） ─────────────────────────
def misc_events():
    # S58 新上市（櫃）：first_seen ＞ 2015-03-01，第一次進入當年母體的月底，且距 first_seen ≤ 550 天
    U = pd.read_parquet(os.path.join(FAC, "universe.parquet")).to_numpy()
    ev58, ev59 = [], []
    for j, s in enumerate(sids):
        fs = pd.Timestamp(FS_[j])
        if fs <= pd.Timestamp("2015-03-01"):
            continue
        rows = np.flatnonzero(U[:, j])
        if len(rows) == 0:
            continue
        t = me_dates[rows[0]]
        if (t - fs).days > 550:
            continue
        p = int(cal.searchsorted(t)); e = cal[min(p + 1, T - 1)]
        ev58.append((s, t.date(), e.date(), f"first_in_universe;first_seen={fs.date()}"))
        raw = pd.read_csv(os.path.join(D.DATA, "stocks", f"{s}.csv"), dtype=str, nrows=1, usecols=["market"])
        if raw["market"].iloc[0] == "tpex":
            ev59.append((s, t.date(), e.date(), "proxy:新上櫃(無興櫃歷史可核)"))
    save_events("S58", ev58); save_events("S59proxy", ev59)
    # 除權息（data/adj）
    ex = []
    for j, s in enumerate(sids):
        a = D.load_adj(s)
        if a is None:
            continue
        a = a[a["event"] == "exright"] if "event" in a else a
        for d, k, pc in zip(a["date"], a.get("kind", pd.Series(dtype=str)).astype(str), a["pre_close"]):
            ex.append((j, s, pd.Timestamp(d), k, float(pc) if pd.notna(pc) else np.nan))
    ev61, ev91 = [], []
    for j, s, d, k, pc in ex:
        if "息" not in k:
            continue
        p = int(cal.searchsorted(d))
        if p >= T or p - 5 < 0:
            continue
        ev61.append((s, d.date(), cal[p - 5].date(), f"exdiv:{k};entry=除息前5個交易日"))
        if k in ("息", "除息") and np.isfinite(pc) and p + 20 < T:
            rc = M["RC"][p:p + 20, j]
            if np.nanmax(np.where(np.isfinite(rc), rc, -np.inf)) >= pc:
                ev91.append((s, d.date(), cal[p + 20].date(), "filled_within_20d;entry=除息後第21個交易日"))
    save_events("S61", ev61); save_events("S91", ev91)
    ev62 = []
    for j, s in enumerate(sids):
        a = D.load_adj(s)
        if a is None or "event" not in a:
            continue
        r = a[(a["event"] == "reduce") & (a["kind"].astype(str).isin(["現金減資", "退還股款"]))]
        for d, k in zip(r["date"], r["kind"]):
            p = int(cal.searchsorted(pd.Timestamp(d)))
            if p + 1 < T:
                ev62.append((s, pd.Timestamp(d).date(), cal[p + 1].date(), f"reduce:{k}"))
    save_events("S62", ev62)
    dsp = pd.read_csv(os.path.join(D.DATA, "meta", "disposal.csv"), dtype=str)
    dsp = dsp[(dsp["sec_kind"] == "普通股") & dsp["stock_id"].isin(sids)]
    ev63 = []
    for s, g in dsp.groupby("stock_id"):
        iv = sorted((pd.Timestamp(a), pd.Timestamp(b)) for a, b in zip(g["start_date"], g["end_date"]))
        mg = []
        for a, b in iv:
            if mg and a <= mg[-1][1] + pd.Timedelta(days=1):
                mg[-1][1] = max(mg[-1][1], b)
            else:
                mg.append([a, b])
        for a, b in mg:
            p = int(cal.searchsorted(b, side="right"))
            if p < T:
                ev63.append((s, b.date(), cal[p].date(), "disposal_end(merged)"))
    save_events("S63", ev63)
    att = pd.read_csv(os.path.join(D.DATA, "meta", "attention.csv"), dtype=str, usecols=["stock_id", "sec_kind", "date"])
    att = att[(att["sec_kind"] == "普通股") & att["stock_id"].isin(sids)]
    ev72 = []
    for s, g in att.groupby("stock_id"):
        ds = sorted(set(pd.Timestamp(x) for x in g["date"]))
        lastp = -10 ** 9
        for d in ds:
            p = int(cal.searchsorted(d))
            if p + 1 >= T:
                continue
            first = (p - lastp) > 20
            ev72.append((s, d.date(), cal[p + 1].date(), "first20" if first else "repeat"))
            lastp = p
    save_events("S72", ev72)
    mm = pd.read_csv(os.path.join(FD, "meta", "margin_membership.csv"), dtype=str)
    mm = mm[mm["stock_id"].isin(sids)]
    ev74 = []
    for s, st, en, oe in zip(mm["stock_id"], mm["start"], mm["end"], mm["open_ended"]):
        st, en = pd.Timestamp(st), pd.Timestamp(en)
        if st > pd.Timestamp("2015-01-05"):
            p = int(cal.searchsorted(st))
            if p + 1 < T:
                ev74.append((s, st.date(), cal[p + 1].date(), "gain"))
        if oe == "0":
            p = int(cal.searchsorted(en, side="right"))
            if p < T:
                ev74.append((s, en.date(), cal[p].date(), "loss"))
    save_events("S74", ev74)


if __name__ == "__main__":
    steps = sys.argv[1:] or ["universe", "price", "chip", "tdcc", "fh", "rev", "fs", "events"]
    snap.check(); print("D.DATA =", D.DATA, "SHA", snap.SHA, flush=True)
    if "universe" in steps:
        universe()
    for st, fn in (("price", price_factors), ("chip", chip_factors), ("tdcc", tdcc_factors), ("fh", foreign_holding), ("rev", revenue_factors), ("fs", fs_factors), ("events", misc_events)):
        if st in steps:
            fn()
            snap.check()
