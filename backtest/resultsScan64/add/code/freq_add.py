# -*- coding: utf-8 -*-
"""scanadd：頻率表＋等價／退化檢查（⛔ 不碰任何報酬）。輸出 ~/scanadd/freq_add.csv、degen_add.csv。"""
import os
import numpy as np, pandas as pd
import snap
from backtest import data as D
D = snap.fix()

BASE = snap.BASE; FAC = os.path.join(BASE, "factors"); CACHE = os.path.join(BASE, "cache")
U_df = pd.read_parquet(os.path.join(FAC, "universe.parquet"))
U = U_df.to_numpy(bool); sids = list(U_df.columns); me = pd.DatetimeIndex(pd.to_datetime(U_df.index))
hold = np.array([str(d.to_period("M") + 1) for d in me])
seg = np.where((hold >= "2017-03") & (hold <= "2021-12"), "探索", np.where((hold >= "2022-01") & (hold <= "2026-08"), "確認", ""))
MIN_VAL = 50


def rd(code):
    return pd.read_parquet(os.path.join(FAC, f"{code}.parquet")).reindex(index=U_df.index, columns=sids).to_numpy(float)


def monthly(V, dirn="high"):
    rows = []; prev = None; pok = False
    for i in range(len(me)):
        u = U[i]; v = V[i]; ok = u & np.isfinite(v); nv = int(ok.sum())
        sv = v if dirn == "high" else -v
        pct = pd.Series(np.where(ok, sv, np.nan)).rank(pct=True, method="average").to_numpy()
        top = ok & (pct > 0.8); ntop = int(top.sum()); usable = nv >= MIN_VAL and ntop > 0
        to = 1 - (top & prev).sum() / ntop if (usable and pok and ntop > 0) else np.nan
        vv = v[ok]
        rows.append(dict(form=str(me[i].date()), hold=hold[i], seg=seg[i], nuni=int(u.sum()), nval=nv, ntop=ntop, usable=usable, turnover=to,
                         zero=float((vv == 0).mean()) if nv else np.nan, pos=float((vv > 0).mean()) if nv else np.nan,
                         neg=float((vv < 0).mean()) if nv else np.nan))
        prev, pok = top, usable
    return pd.DataFrame(rows)


SPEC = [("S29", "內部人持股增加", "董監＋經理人實際持有股數月變化（本期÷前一期−1），取高", "可跑"),
        ("S87", "董監持股比例水準", "IRB110 ds_pct_of_issued（董監佔股份總額 %，官方欄原值），取高", "可跑"),
        ("S30", "內部人質押比上升（seq527 讀法）", "IRB130 董監 ds_pledged_pct 本期−前一期（百分點），取高；可用日、期別限制、前一期規則同 S29", "可跑（seq527）"),
        ("S30v1_ds_level", "內部人質押比上升｜讀法1 董監質押比水準", "IRB130 ds_pledged_pct，取高", "⛔ seq527 不跑、不計 N"),
        ("S30v3_all_level", "內部人質押比上升｜讀法3 董監＋經理人＋10%大股東質押比水準", "(ds_pledged_cum+mgr_major_pledged)÷(ds+mgr+major 持股)，取高", "⛔ seq527 不跑、不計 N"),
        ("S30v4_all_change", "內部人質押比上升｜讀法4 同讀法3 月變化", "讀法3 本期−前一期（百分點），取高", "⛔ seq527 不跑、不計 N")]
out = []; MON = {}
for code, name, defn, lab in SPEC:
    d = monthly(rd(code)); MON[code] = d
    d.to_csv(os.path.join(BASE, "freqmonthly", f"{code}.csv"), index=False)
    r = dict(S號=code, 因子=name, 定義=defn)
    for sg in ("探索", "確認"):
        x = d[d.seg == sg]
        r[f"可用月{sg}"] = int(x.usable.sum()); r[f"形成月數{sg}"] = len(x)
        r[f"母體中位{sg}"] = float(x.nuni.median()); r[f"有值中位{sg}"] = float(x.nval.median())
        r[f"可算比例中位{sg}"] = round(float((x.nval / x.nuni).median()), 4)
        r[f"前五分之一平均檔數{sg}"] = round(float(x.loc[x.usable, "ntop"].mean()), 1) if x.usable.any() else np.nan
        r[f"月換手中位{sg}"] = round(float(x.turnover.median()), 3) if x.turnover.notna().any() else np.nan
        r[f"值＝0比例中位{sg}"] = round(float(x.zero.median()), 4); r[f"值>0比例中位{sg}"] = round(float(x.pos.median()), 4)
    r["標籤"] = lab
    r["可用日規則"] = "published（表頭資料日期）≤ 形成月最後交易日的最新一期；data_ym 須 ≥ 形成月−2"
    out.append(r)
fq = pd.DataFrame(out)
fq.to_csv(os.path.join(BASE, "freq_add.csv"), index=False, encoding="utf-8-sig")
print(fq.T.to_string())

# ───── 等價／退化檢查（只用因子值與母體） ─────
S29, S87, ISS = rd("S29"), rd("S87"), rd("aux_issued_chg")
DPCT = rd("aux_S29_dpct")
P = np.load(os.path.join(CACHE, "panel.npz"))
cal = pd.DatetimeIndex(pd.to_datetime(P["cal"])); assert list(P["sids"]) == sids
RC = pd.DataFrame(np.where(P["VALID"] == 1, P["RC"], np.nan)).ffill(limit=5).to_numpy()
SH = pd.DataFrame(P["SH"].astype(float)).ffill(limit=5).to_numpy()
mpos = np.array([cal.get_loc(d) for d in me]); MCAP = RC[mpos] * SH[mpos]; MCAP[~(MCAP > 0)] = np.nan
S30 = rd("S30")


def sp(a, b, m):
    return pd.Series(a[m]).rank().corr(pd.Series(b[m]).rank()) if m.sum() > 10 else np.nan


def s30desc(i, u, top, t29, t87):
    """S30（seq527）：與 S29、S87 的 Spearman、前組重疊；前組大小與『質押比升』檔數。"""
    t30, o30 = top(S30[i])
    v = S30[i]
    return dict(rho_S30_S29=sp(S30[i], S29[i], o30 & np.isfinite(S29[i])), rho_S30_S87=sp(S30[i], S87[i], o30 & np.isfinite(S87[i])),
                S30_top=int(t30.sum()), S30_pos=int((o30 & (v > 0)).sum()), S30_val=int(o30.sum()),
                top_overlap_S30_in_S29=(t30 & t29).sum() / max(t30.sum(), 1), top_overlap_S30_in_S87=(t30 & t87).sum() / max(t30.sum(), 1))


rows = []
for i in range(len(me)):
    if not seg[i]:
        continue
    u = U[i]
    def top(v, hi=True):
        ok = u & np.isfinite(v)
        pct = pd.Series(np.where(ok, v if hi else -v, np.nan)).rank(pct=True).to_numpy()
        return ok & (pct > 0.8), ok
    t29, o29 = top(S29[i]); t87, o87 = top(S87[i]); tdp, odp = top(DPCT[i])
    both = o29 & o87
    rho = pd.Series(S29[i][both]).rank().corr(pd.Series(S87[i][both]).rank()) if both.sum() > 10 else np.nan
    bm = o87 & np.isfinite(MCAP[i])
    rho87m = pd.Series(S87[i][bm]).rank().corr(pd.Series(MCAP[i][bm]).rank()) if bm.sum() > 10 else np.nan
    # S29 前組裡：同期發行股數也增加（≥0.5%）、且董監經理人持股變化幅度與發行股數變化相差 <1 個百分點（機械性：配股、增資等比例）
    t = t29 & np.isfinite(ISS[i])
    iss_up = t & (ISS[i] >= 0.005)
    mech = iss_up & (np.abs(S29[i] - ISS[i]) < 0.01)
    rows.append(dict(form=str(me[i].date()), seg=seg[i], rho_S29_S87=rho, top_overlap_S29_in_S87=(t29 & t87).sum() / max(t29.sum(), 1),
                     rho_S87_mcap=rho87m, S29_top=int(t29.sum()), S29_top_issued_up=int(iss_up.sum()), S29_top_mech=int(mech.sum()),
                     S29_top_overlap_with_dpct_top=(t29 & tdp).sum() / max(t29.sum(), 1), **s30desc(i, u, top, t29, t87)))
dg = pd.DataFrame(rows); dg.to_csv(os.path.join(BASE, "degen_add.csv"), index=False)
for sg in ("探索", "確認"):
    x = dg[dg.seg == sg]
    print(sg, "S29×S87 月 Spearman 中位", round(x.rho_S29_S87.median(), 3), "〔", round(x.rho_S29_S87.min(), 3), round(x.rho_S29_S87.max(), 3), "〕",
          "S29 前組落在 S87 前組比例中位", round(x.top_overlap_S29_in_S87.median(), 3),
          "｜S87×市值 Spearman 中位", round(x.rho_S87_mcap.median(), 3),
          "｜S29 前組中發行股數同增≥0.5% 比例", round(x.S29_top_issued_up.sum() / x.S29_top.sum(), 3),
          "、機械性（差<1pp）比例", round(x.S29_top_mech.sum() / x.S29_top.sum(), 3),
          "｜S29 前組與『董監持股比例變化』前組重疊中位", round(x.S29_top_overlap_with_dpct_top.median(), 3))
    print(sg, "S30×S29 Spearman 中位", round(x.rho_S30_S29.median(), 3), "〔", round(x.rho_S30_S29.min(), 3), round(x.rho_S30_S29.max(), 3), "〕",
          "S30×S87 Spearman 中位", round(x.rho_S30_S87.median(), 3), "〔", round(x.rho_S30_S87.min(), 3), round(x.rho_S30_S87.max(), 3), "〕",
          "｜S30 前組落在 S29 前組比例中位", round(x.top_overlap_S30_in_S29.median(), 3), "、落在 S87 前組", round(x.top_overlap_S30_in_S87.median(), 3),
          "｜S30 前組檔數 最小／中位／最大", int(x.S30_top.min()), int(x.S30_top.median()), int(x.S30_top.max()),
          "｜前組占有值比例中位", round((x.S30_top / x.S30_val).median(), 4), "｜前組＝質押比升者的月數", int((x.S30_top == x.S30_pos).sum()), "／", len(x))
