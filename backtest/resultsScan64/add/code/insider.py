# -*- coding: utf-8 -*-
"""scanadd：內部人月報（IRB110 持股、IRB130 質權）讀檔與「量測日可用最新一期」對齊。
⭐ 可用日一律用 published（表頭「資料日期」，裁定 seq352／seq526）；⛔ 不用 data_ym、不用月底。
量測日 t 只能用 published ≤ t 的最新一期。stock_id 當鍵（⛔ 不用公司名）。"""
import glob, os
import numpy as np, pandas as pd

NUM110 = ["issued_shares", "ds_increase", "ds_decrease", "ds_shares", "ds_pct_of_issued", "mgr_shares", "major_shares"]
NUM130 = ["ds_shares", "ds_pledge_set", "ds_pledge_release", "ds_pledged_cum", "ds_pledged_pct", "mgr_shares", "major_shares",
          "mgr_major_pledged", "mgr_major_pledged_pct"]


def ymi(p):
    """Period/字串 'YYYY-MM' → 整數月碼。"""
    s = str(p)
    return int(s[:4]) * 12 + int(s[5:7]) - 1


def load(snapdir, table):
    fs = sorted(glob.glob(os.path.join(snapdir, "meta", "insider_holding", f"{table}_*.csv")))
    assert fs, f"{table} 沒檔"
    x = pd.concat([pd.read_csv(f, dtype={"stock_id": str, "data_ym": str, "published": str, "market": str, "company": str}) for f in fs],
                  ignore_index=True)
    return prep(x, NUM110 if table == "irb110" else NUM130)


def prep(x, num):
    x = x.copy()
    x["published"] = pd.to_datetime(x["published"])
    x["ymi"] = x["data_ym"].map(ymi)
    for c in num:
        if c in x:
            x[c] = pd.to_numeric(x[c], errors="coerce")
    # 同月同代號兩列（轉市場當月上市、上櫃各一列）：★取最早 published 那列（資料最早可用）；數字欄須相同
    x = x.sort_values(["stock_id", "ymi", "published"]).reset_index(drop=True)
    dupm = x.duplicated(["stock_id", "ymi"], keep=False)
    d = x[dupm]
    mism = 0
    for _, g in d.groupby(["stock_id", "ymi"]):
        v = g[[c for c in num if c in g]].to_numpy(float)
        if not np.allclose(v, v[0], equal_nan=True):
            mism += 1
    info = dict(rows=len(x), dup_pairs=int(dupm.sum() // 2), dup_value_mismatch=mism)
    x = x.drop_duplicates(["stock_id", "ymi"], keep="first").reset_index(drop=True)
    return x, info


def asof(x, cols, me_dates, sids, max_lag=2):
    """每個量測日 t（me_dates）、每檔 sids：published ≤ t 的最新一期 k（data_ym 最大）。
    ★ 該期 data_ym 須 ≥ t 所在月 − max_lag（太舊 ⇒ 空）。
    回傳 val[col]（第 k 期值）、prev[col]（第 k−1 期、同檔、published 也 ≤ t；缺 ⇒ 空）、kym（第 k 期月碼，無 ⇒ −1）。"""
    sidx = {s: i for i, s in enumerate(sids)}
    x = x[x["stock_id"].isin(sidx)]
    y0, y1 = int(x["ymi"].min()), int(x["ymi"].max())
    NY, N, NM = y1 - y0 + 1, len(sids), len(me_dates)
    r = (x["ymi"].to_numpy() - y0); c = x["stock_id"].map(sidx).to_numpy()
    PUB = np.full((NY, N), np.datetime64("NaT"), dtype="datetime64[ns]")
    PUB[r, c] = x["published"].to_numpy()
    V = {}
    for col in cols:
        A = np.full((NY, N), np.nan); A[r, c] = x[col].to_numpy(float); V[col] = A
    ar = np.arange(NY)[:, None]
    val = {col: np.full((NM, N), np.nan) for col in cols}
    prev = {col: np.full((NM, N), np.nan) for col in cols}
    kym = np.full((NM, N), -1)
    jj = np.arange(N)
    for i, t in enumerate(pd.DatetimeIndex(me_dates)):
        tt = np.datetime64(t)
        ok = PUB <= tt                         # NaT 比較為 False
        k = np.where(ok, ar, -1).max(axis=0)
        tm = t.year * 12 + t.month - 1
        k[(k >= 0) & (k + y0 < tm - max_lag)] = -1
        m = k >= 0
        kym[i, m] = k[m] + y0
        pk = k - 1
        mp = m & (pk >= 0)
        mp[mp] = PUB[pk[mp], jj[mp]] <= tt
        for col in cols:
            val[col][i, m] = V[col][k[m], jj[m]]
            prev[col][i, mp] = V[col][pk[mp], jj[mp]]
    return dict(val=val, prev=prev, kym=kym, y0=y0)
