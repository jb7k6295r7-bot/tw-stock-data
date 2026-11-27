# -*- coding: utf-8 -*-
"""真資料上驗 published 可用日（不含報酬）：
1) 所有被用到的期別，其 published ≤ 量測日；S29 的前一期也 ≤ 量測日。
2) 注入：每個量測月替 50 檔造一筆「data_ym＝量測月、published＝量測日＋1 天、值極端」的假列 ⇒ 重算後 S29、S87 必須完全不變。"""
import os
import numpy as np, pandas as pd
import snap
import insider as I
D = snap.fix()
FAC = os.path.join(snap.BASE, "factors")
U_df = pd.read_parquet(os.path.join(FAC, "universe.parquet"))
me = pd.DatetimeIndex(pd.to_datetime(U_df.index)); sids = list(U_df.columns)
x, _ = I.load(snap.SNAP, "irb110")
x["dm"] = x["ds_shares"] + x["mgr_shares"]
kym = pd.read_parquet(os.path.join(FAC, "aux_kym.parquet")).reindex(index=U_df.index, columns=sids).to_numpy()
pub = x.set_index(["stock_id", "ymi"])["published"]
bad = bad_prev = n = 0
ii, jj = np.nonzero(np.isfinite(kym) & (kym >= 0))
keys = list(zip([sids[j] for j in jj], kym[ii, jj].astype(int)))
pp = pub.reindex(keys).to_numpy()
bad = int((pp > me[ii].values).sum()); n = len(keys)
keys_p = list(zip([sids[j] for j in jj], kym[ii, jj].astype(int) - 1))
pq = pub.reindex(keys_p).to_numpy()
okp = ~pd.isna(pq)
S29 = pd.read_parquet(os.path.join(FAC, "S29.parquet")).reindex(index=U_df.index, columns=sids).to_numpy(float)
used_prev = np.isfinite(S29[ii, jj])
bad_prev = int(((pq > me[ii].values) & okp & used_prev).sum())
lag = (me[ii].values.astype("datetime64[M]").astype(int) - (kym[ii, jj].astype(int) - 1970 * 12))
print(f"用到的期別 {n:,} 格：published > 量測日 {bad} 格；S29 前一期 published > 量測日 {bad_prev} 格")
print("量測月 − 所用 data_ym（月）分布：", pd.Series(lag).value_counts().sort_index().to_dict())
assert bad == 0 and bad_prev == 0
# 注入（逐量測月各自注入、各自重算該月）
rng = np.random.default_rng(1)
raw = x.drop(columns=["ymi", "dm"]).copy(); raw["published"] = raw["published"].dt.strftime("%Y-%m-%d")
S87 = pd.read_parquet(os.path.join(FAC, "S87.parquet")).reindex(index=U_df.index, columns=sids).to_numpy(float)
nf = n29 = n87 = 0
for i, t in enumerate(me):
    fake = [dict(data_ym=f"{t.year}-{t.month:02d}", published=str((t + pd.Timedelta(days=1)).date()), market="sii", stock_id=s, company="FAKE",
                 issued_shares=1e9, ds_increase=0, ds_decrease=0, ds_shares=9e8, ds_pct_of_issued=99.0, mgr_shares=9e7, major_shares=0)
            for s in rng.choice(sids, 50, replace=False)]
    nf += len(fake)
    y, _ = I.prep(pd.concat([raw, pd.DataFrame(fake)], ignore_index=True), I.NUM110)
    y["dm"] = y["ds_shares"] + y["mgr_shares"]
    A = I.asof(y, ["dm", "ds_pct_of_issued"], me[i:i + 1], sids)
    with np.errstate(all="ignore"):
        s29 = np.where(A["prev"]["dm"] > 0, A["val"]["dm"] / A["prev"]["dm"] - 1, np.nan)
    s29[~np.isfinite(A["val"]["dm"]) | ~np.isfinite(A["prev"]["dm"])] = np.nan
    n29 += int((~np.isclose(s29[0], S29[i], equal_nan=True, rtol=1e-6, atol=1e-7)).sum())
    n87 += int((~np.isclose(A["val"]["ds_pct_of_issued"][0], S87[i], equal_nan=True, rtol=1e-6, atol=1e-6)).sum())
print(f"注入 {nf:,} 筆 published＝量測日＋1 的假列（每月 50 檔、該月各自重算）：S29 變動格 {n29}、S87 變動格 {n87}")
assert n29 == 0 and n87 == 0
# 正對照（確認注入機制有效）：同樣的假列改 published＝量測日 ⇒ 應被用到
i = len(me) // 2; t = me[i]; ss = list(rng.choice(sids, 50, replace=False))
fake = [dict(data_ym=f"{t.year}-{t.month:02d}", published=str(t.date()), market="sii", stock_id=s, company="FAKE",
             issued_shares=1e9, ds_increase=0, ds_decrease=0, ds_shares=9e8, ds_pct_of_issued=99.0, mgr_shares=9e7, major_shares=0) for s in ss]
y, _ = I.prep(pd.concat([raw, pd.DataFrame(fake)], ignore_index=True), I.NUM110)
A = I.asof(y, ["ds_pct_of_issued"], me[i:i + 1], sids)
hit = int((A["val"]["ds_pct_of_issued"][0][[sids.index(s) for s in ss]] == 99.0).sum())
print(f"正對照 {t.date()}：published＝量測日的 50 筆假列被用到 {hit}／50")
assert hit == 50
print("CHECK_PUB OK")
