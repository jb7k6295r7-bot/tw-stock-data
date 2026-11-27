# -*- coding: utf-8 -*-
"""scanadd step 2：S29、S87（＋S30 各候選讀法，只供頻率表）月底因子值。⛔ 不算任何持有期報酬。
讀 ~/scanadd/cache/panel.npz、factors/universe.parquet（factors.py universe）；內部人月報 data/meta/insider_holding（origin/main dcefaa4ef3）。
可用日＝published（≤ 量測日＝形成月最後交易日）。"""
import os, sys, json
import numpy as np, pandas as pd
import snap
import factors as F            # 只為共用月底、股票清單與 save（module 層只讀面板）
import insider as I
D = snap.fix()

snap.check()
x110, info110 = I.load(snap.SNAP, "irb110")
x130, info130 = I.load(snap.SNAP, "irb130")
print("irb110", info110, "irb130", info130, flush=True)

# S29：董監＋經理人實際持有股數（看板定義「董監經理人持股月變化」；10% 大股東不加）
x110["dm"] = x110["ds_shares"] + x110["mgr_shares"]
A = I.asof(x110, ["dm", "ds_shares", "mgr_shares", "ds_pct_of_issued", "issued_shares"], F.me_dates, F.sids)
dm, dmp = A["val"]["dm"], A["prev"]["dm"]
with np.errstate(all="ignore"):
    s29 = np.where(dmp > 0, dm / dmp - 1, np.nan)
s29[~np.isfinite(dm) | ~np.isfinite(dmp)] = np.nan
F.save("S29", s29)
# S87：董監持股佔股份總額 %（官方欄原值；6945 2026-06 issued_shares 官方打錯不影響此欄）
s87 = A["val"]["ds_pct_of_issued"].copy()
F.save("S87", s87)

# 輔助（只描述、檢查用）：同期發行股數月變化、所用期別
with np.errstate(all="ignore"):
    iss = np.where(A["prev"]["issued_shares"] > 0, A["val"]["issued_shares"] / A["prev"]["issued_shares"] - 1, np.nan)
    ds_only = np.where(A["prev"]["ds_shares"] > 0, A["val"]["ds_shares"] / A["prev"]["ds_shares"] - 1, np.nan)
    dpct = A["val"]["ds_pct_of_issued"] - A["prev"]["ds_pct_of_issued"]
for nm, arr in (("aux_issued_chg", iss), ("aux_S29_dsonly", ds_only), ("aux_S29_dpct", dpct), ("aux_kym", A["kym"].astype(float))):
    F.save(nm, arr)

# S30 候選讀法（登錄沒寫清楚「內部人」含誰、水準或變化 ⇒ ⛔ 不跑報酬；只做頻率表供裁定）
B = I.asof(x130, ["ds_pledged_pct", "ds_pledged_cum", "ds_shares", "mgr_shares", "major_shares", "mgr_major_pledged"], F.me_dates, F.sids)
v, p = B["val"], B["prev"]
with np.errstate(all="ignore"):
    allv = (v["ds_pledged_cum"] + v["mgr_major_pledged"]) / (v["ds_shares"] + v["mgr_shares"] + v["major_shares"]) * 100
    allp = (p["ds_pledged_cum"] + p["mgr_major_pledged"]) / (p["ds_shares"] + p["mgr_shares"] + p["major_shares"]) * 100
allv[~np.isfinite(allv)] = np.nan; allp[~np.isfinite(allp)] = np.nan
F.save("S30v1_ds_level", v["ds_pledged_pct"])
F.save("S30v2_ds_change", v["ds_pledged_pct"] - p["ds_pledged_pct"])
# S30（裁定 seq527）：只用董監 ds_pledged_pct 本期 − 前一期（百分點），取高；可用日、期別限制、前一期規則同 S29
F.save("S30", v["ds_pledged_pct"] - p["ds_pledged_pct"])
F.save("S30v3_all_level", allv)
F.save("S30v4_all_change", allv - allp)

# 6945 2026-06 檢查
r = x110[(x110.stock_id == "6945") & (x110.data_ym.between("2026-05", "2026-07"))][["data_ym", "published", "issued_shares", "ds_shares", "ds_pct_of_issued"]]
print(r.to_string())
json.dump(dict(irb110=info110, irb130=info130, sha=snap.SHA), open(os.path.join(snap.BASE, "factors", "insider_info.json"), "w"))
snap.check()
print("done")
