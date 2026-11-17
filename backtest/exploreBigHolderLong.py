# -*- coding: utf-8 -*-
"""集保大戶比例 4 週升幅前 5%（B60）訊號後一年：大戶比例與股價的關係怎麼隨時間變——探索、只描述；看過才定；不判、不計 N。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.exploreBigHolderLong

母體：researchBigHolderRise.build76() 的 SIG（全部 B60 訊號事件，每檔每訊號週一筆），進場日落在 SEGS 兩段內。
訊號、價格（還原收盤 ACf、還原開盤 AO）、大戶比例（bw）一律用 build76()，⛔ 不另寫第二套。
口徑沿用 exploreBigHolderAfter：FLAT ±0.1pp、大漲 ≥+30%、大跌 ≤−20%、Spearman＝名次 Pearson、N<30 標「樣本少」。

週對齊：
 第 0 週＝訊號資料日那週（買進前）；第 k 週＝週序號 w0+k（週＝(資料日−2017-01-02)//7）。
 第 k 週的「日期」＝該週集保資料日；該週集保缺 ⇒ 用名目週五（WK0+7w+4）只為取股價。
 第 k 週股價＝該日期當天或之前最後一個交易日的還原收盤（ACf，停牌沿用前值）。
 累積報酬（第 k 週）＝第 k 週股價 ÷ 進場日還原開盤 − 1（進場規則同 B60）。
 資料尾：第 k 週日期超過集保最後資料日或價格最後交易日 ⇒ 該筆在第 k 週之後退出。
 比例在某週缺（集保缺週、或下市後無資料）⇒ 該格不算（N 照實報）。
去重版：每檔只取第一次訊號，之後 52 週（週序號差 < 52）內的訊號不算；過了 52 週再出現算新的一次。
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from backtest import data as D
from backtest import researchBigHolderRise as R
from backtest import exploreBigHolderAfter as EA

OUTL = os.path.join(R.HERE, "resultsBigHolderRise", "explore_long")
HMAX = 52
HS = [4, 8, 12, 26, 39, 52]
FLAT = EA.FLAT
BIG_UP = EA.BIG_UP
BIG_DN = EA.BIG_DN
SMALL = EA.SMALL
LAGS = list(range(-4, 5))
BANDS = [("第 2–12 週", 2, 12), ("第 13–26 週", 13, 26), ("第 27–52 週", 27, 52)]
PEAK_MINCOV = 48      # 最高點分析：53 週中比例至少有 48 週有值
flag = EA.flag
ret_stats = EA.ret_stats


def spear(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 3:
        return np.nan
    return float(np.corrcoef(pd.Series(a[m]).rank().values, pd.Series(b[m]).rank().values)[0, 1])


def build(Bx):
    cal = Bx["cal"]; bw = Bx["bw"]; dates = Bx["dates"]; ACf = Bx["ACf"]; AO = Bx["AO"]; SIG = Bx["SIG"]
    wk_of = {d: w for w, d in dates.items()}
    S = SIG.copy()
    S["資料日"] = pd.to_datetime(S["資料日"]); S["進場日"] = pd.to_datetime(S["進場日"])
    S["w0"] = [int(wk_of[d]) for d in S["資料日"]]
    S["段"] = ""
    for sg, (a, b) in R.SEGS.items():
        S.loc[(S["進場日"] >= pd.Timestamp(a)) & (S["進場日"] <= pd.Timestamp(b)), "段"] = sg
    n_out = int((S["段"] == "").sum())
    R.log(f"[母體] B60 訊號 {len(S)} 筆；進場日在兩段外（2018-11-01 前）{n_out} 筆不列入")
    S = S[S["段"] != ""].sort_values(["sid", "w0"]).reset_index(drop=True)
    assert not S.duplicated(["sid", "w0"]).any()
    # 去重：每檔第一次，之後 52 週內不重複
    keep = np.zeros(len(S), bool); last = {}
    for i, (s, w) in enumerate(zip(S.sid, S.w0)):
        if s not in last or w - last[s] >= HMAX:
            keep[i] = True; last[s] = w
    S["去重"] = keep
    R.log(f"[母體] 全部訊號 {len(S)}（探索 {(S['段'] == '探索').sum()}｜確認 {(S['段'] == '確認').sum()}）；"
          f"去重 {keep.sum()}（探索 {(S['去重'] & (S['段'] == '探索')).sum()}｜確認 {(S['去重'] & (S['段'] == '確認')).sum()}）")

    wmin = int(bw.index.min()); wmax = int(bw.index.max())
    weeks = np.arange(wmin, wmax + 1); nW = len(weeks)
    cols = bw.columns
    WR = bw.reindex(weeks).to_numpy(float)
    nominal = pd.to_datetime(R.WK0) + pd.to_timedelta(weeks * 7 + 4, unit="D")
    dw = pd.Series(dates.reindex(weeks).values, index=weeks)
    dw = pd.DatetimeIndex(np.where(dw.isna(), nominal, dw.values))
    end = min(cal[-1], dates.iloc[-1])
    vweek = np.asarray(dw <= end)
    iw = cal.searchsorted(dw, side="right") - 1
    ACc = ACf.reindex(columns=cols).to_numpy(float)
    AOc = AO.reindex(columns=cols).to_numpy(float)
    PW = np.where((iw >= 0)[:, None], ACc[np.clip(iw, 0, None)], np.nan)
    R.log(f"[週] 週序號 {wmin}～{wmax}（{nW} 週，集保有值 {len(bw)} 週）；價格最後交易日 {cal[-1].date()}｜集保最後資料日 {dates.iloc[-1].date()}｜資料尾取 {end.date()}")

    cidx = {s: i for i, s in enumerate(cols)}
    c = S.sid.map(cidx).to_numpy(int)
    e = S.e.to_numpy(int)
    idx = (S.w0.to_numpy(int) - wmin)[:, None] + np.arange(HMAX + 1)[None, :]
    inr = idx < nW
    idxc = np.clip(idx, 0, nW - 1)
    inwin = inr & vweek[idxc]
    RAT = np.where(inwin, WR[idxc, c[:, None]], np.nan)
    PRC = np.where(inwin, PW[idxc, c[:, None]], np.nan)
    IW = np.where(inwin, iw[idxc], -1)
    ao = AOc[e, c]
    RET = np.where(IW >= e[:, None], PRC / ao[:, None] - 1, np.nan)
    R.log(f"[核對] 進場開盤缺 {int(np.isnan(ao).sum())}；第 1 週股價日已在進場日之後 {float((IW[:, 1] >= e).mean()):.4f}")
    return S, RAT, PRC, RET, IW, inwin, e


def scopes(S):
    for lab, m0 in (("全部訊號", np.ones(len(S), bool)), ("去重", S["去重"].to_numpy())):
        for sg in ("探索", "確認", "合計"):
            m = m0 if sg == "合計" else (m0 & (S["段"] == sg).to_numpy())
            yield lab, sg, m


def main():
    os.makedirs(OUTL, exist_ok=True)
    D.DATA = R.DATA
    R.LOGS.clear()
    R.log(f"[資料] tw-stock-data {R.SHA[:10]}｜探索、只描述（不判、不計 N）")
    Bx = R.build76()
    S, RAT, PRC, RET, IW, inwin, e = build(Bx)
    sid = S.sid.to_numpy(); w0 = S.w0.to_numpy(int)
    CH = RAT - RAT[:, [0]]                      # 累積比例變化

    # 每筆存活（各週在窗內／有比例／有成對）
    t0 = []
    for lab, sg, m in scopes(S):
        for h in [0] + HS:
            t0.append({"口徑": lab, "範圍": sg, "週": h, "在窗內": int(inwin[m, h].sum()), "比例有值": int(np.isfinite(RAT[m, h]).sum()),
                       "比例與報酬成對": int((np.isfinite(CH[m, h]) & np.isfinite(RET[m, h])).sum()) if h else 0})
    T0 = pd.DataFrame(t0)

    # ① 比例走勢
    t1 = []; t1p = []
    for lab, sg, m in scopes(S):
        for h in HS:
            d = CH[m, h]; d = d[np.isfinite(d)]; n = len(d)
            t1.append({"口徑": lab, "範圍": sg, "週": h, "N": n,
                       "高於訊號週": float((d > 0).mean()) if n else np.nan,
                       "升超0.1pp": float((d > FLAT).mean()) if n else np.nan,
                       "降超0.1pp": float((d < -FLAT).mean()) if n else np.nan,
                       "累積變化中位_pp": float(np.median(d) * 100) if n else np.nan,
                       "累積變化平均_pp": float(d.mean() * 100) if n else np.nan, "註": flag(n)})
        full = m & inwin.all(axis=1) & (np.isfinite(RAT).sum(axis=1) >= PEAK_MINCOV)
        R_ = RAT[full]
        pk = np.nanargmax(R_, axis=1) if len(R_) else np.array([], int)
        n = len(pk)
        for k in range(HMAX + 1):
            t1p.append({"口徑": lab, "範圍": sg, "最高點週": k, "筆數": int((pk == k).sum()), "占比": float((pk == k).mean()) if n else np.nan, "N": n})
    T1 = pd.DataFrame(t1); T1P = pd.DataFrame(t1p)

    # ② 每個週數：累積比例變化 vs 累積報酬
    t2 = []
    for lab, sg, m in scopes(S):
        for h in HS:
            ch = CH[m, h]; r = RET[m, h]; ok = np.isfinite(ch) & np.isfinite(r)
            ch = ch[ok]; r = pd.Series(r[ok])
            base = {"口徑": lab, "範圍": sg, "週": h, "N成對": int(ok.sum()), "Spearman": spear(ch, r.values)}
            for g, gm in (("續升", ch > FLAT), ("持平", np.abs(ch) <= FLAT), ("回落", ch < -FLAT), ("全部", np.ones(len(ch), bool))):
                st = ret_stats(r[gm])
                t2.append(base | {"組": g, "占比": float(gm.mean()) if len(ch) else np.nan} | st)
    T2 = pd.DataFrame(t2)

    # ③ 同週連動（逐週）＋ ④ 超前落後
    DR = np.full_like(RAT, np.nan); PR = np.full_like(RAT, np.nan)
    DR[:, 1:] = RAT[:, 1:] - RAT[:, :-1]
    with np.errstate(invalid="ignore", divide="ignore"):
        PR[:, 1:] = PRC[:, 1:] / PRC[:, :-1] - 1
    PR[:, :2] = np.nan; DR[:, :2] = np.nan            # 第 1 週（含進場前的不完整週）不算
    PR[IW < e[:, None]] = np.nan
    PRm1 = np.full_like(PR, np.nan); PRm1[:, 1:] = (IW[:, :-1] >= e[:, None])
    PR[PRm1 != 1] = np.nan                             # 前一週股價日也要在進場日之後
    kk = np.broadcast_to(np.arange(HMAX + 1), RAT.shape)
    absw = w0[:, None] + kk
    t3 = []
    for lab, sg, m in scopes(S):
        for band, lo, hi in BANDS + [("第 2–52 週合計", 2, 52)]:
            sel = np.zeros_like(RAT, bool); sel[m, lo:hi + 1] = True
            ok = sel & np.isfinite(DR) & np.isfinite(PR)
            L = pd.DataFrame({"sid": np.broadcast_to(sid[:, None], RAT.shape)[ok], "w": absw[ok], "dr": DR[ok], "pr": PR[ok]})
            vers = (("逐筆週對", L), ("同股同週去重", L.drop_duplicates(["sid", "w"]))) if lab == "全部訊號" else (("逐筆週對（去重版本身同股同週不重複）", L),)
            for dd_lab, dd in vers:
                up = dd.dr > 0; dn = dd.dr < 0; upb = dd.dr > FLAT; dnb = dd.dr < -FLAT; px = dd.pr > 0
                t3.append({"口徑": lab, "範圍": sg, "段落": band, "週對口徑": dd_lab, "週對數": len(dd), "Spearman": spear(dd.dr, dd.pr),
                           "比例升_週數": int(up.sum()), "比例升_股價漲": float(px[up].mean()) if up.any() else np.nan,
                           "比例降_週數": int(dn.sum()), "比例降_股價漲": float(px[dn].mean()) if dn.any() else np.nan,
                           "升超0.1pp_股價漲": float(px[upb].mean()) if upb.any() else np.nan,
                           "降超0.1pp_股價漲": float(px[dnb].mean()) if dnb.any() else np.nan,
                           "全部_股價漲": float(px.mean()) if len(dd) else np.nan,
                           "註": flag(min(int(up.sum()), int(dn.sum())))})
    T3 = pd.DataFrame(t3)

    t4 = []
    for lab, sg, m in scopes(S):
        for lag in LAGS:
            ts = np.arange(2, HMAX + 1); ts = ts[(ts + lag >= 2) & (ts + lag <= HMAX)]
            a = DR[np.ix_(m, ts)]; b = PR[np.ix_(m, ts + lag)]
            sw = np.broadcast_to(sid[m][:, None], a.shape); ww = absw[np.ix_(m, ts)]
            ok = np.isfinite(a) & np.isfinite(b)
            L = pd.DataFrame({"sid": sw[ok], "w": ww[ok], "dr": a[ok], "pr": b[ok]})
            for dd_lab, dd in (("逐筆週對", L), ("同股同週去重", L.drop_duplicates(["sid", "w"]))):
                up = dd.dr > 0; dn = dd.dr < 0; px = dd.pr > 0
                t4.append({"口徑": lab, "範圍": sg, "k": lag, "週對口徑": dd_lab, "週對數": len(dd), "Spearman": spear(dd.dr, dd.pr),
                           "比例升_股價漲": float(px[up].mean()) if up.any() else np.nan,
                           "比例降_股價漲": float(px[dn].mean()) if dn.any() else np.nan, "註": flag(len(dd))})
    T4 = pd.DataFrame(t4)

    # ④b 最高點先後
    t4p = []; per = []
    for lab, sg, m in scopes(S):
        full = m & inwin.all(axis=1) & (np.isfinite(RAT).sum(axis=1) >= PEAK_MINCOV) & np.isfinite(PRC).all(axis=1)
        pr_ = np.nanargmax(RAT[full], axis=1) if full.any() else np.array([], int)
        pp_ = np.nanargmax(PRC[full], axis=1) if full.any() else np.array([], int)
        dif = pp_ - pr_; n = len(dif)
        t4p.append({"口徑": lab, "範圍": sg, "N": n,
                    "比例先到頂": float((dif > 0).mean()) if n else np.nan, "同週": float((dif == 0).mean()) if n else np.nan,
                    "股價先到頂": float((dif < 0).mean()) if n else np.nan,
                    "相差週數中位_股價減比例": float(np.median(dif)) if n else np.nan,
                    "相差週數絕對值中位": float(np.median(np.abs(dif))) if n else np.nan,
                    "比例最高點週中位": float(np.median(pr_)) if n else np.nan, "股價最高點週中位": float(np.median(pp_)) if n else np.nan,
                    "相差≤4週": float((np.abs(dif) <= 4).mean()) if n else np.nan, "註": flag(n)})
        if lab == "全部訊號" and sg == "合計":
            per = pd.DataFrame({"sid": sid[full], "資料日": S["資料日"].dt.date.to_numpy()[full], "段": S["段"].to_numpy()[full],
                                "去重": S["去重"].to_numpy()[full], "比例最高點週": pr_, "股價最高點週": pp_})
    T4P = pd.DataFrame(t4p)

    # ⑤ 第 52 週：比例累積變化五等分
    t5 = []
    for lab, sg, m in scopes(S):
        ch = CH[m, HMAX]; r = RET[m, HMAX]; ok = np.isfinite(ch) & np.isfinite(r)
        ch = pd.Series(ch[ok]); r = pd.Series(r[ok])
        if len(ch) < 5:
            continue
        q = pd.qcut(ch.rank(method="first"), 5, labels=[1, 2, 3, 4, 5])
        for k in range(1, 6):
            g = q == k
            t5.append({"口徑": lab, "範圍": sg, "五等分": k, "變化下限_pp": float(ch[g].min() * 100), "變化上限_pp": float(ch[g].max() * 100)} | ret_stats(r[g]))
    T5 = pd.DataFrame(t5)

    # 逐筆
    Pe = pd.DataFrame({"sid": sid, "資料日": S["資料日"].dt.date, "進場日": S["進場日"].dt.date, "段": S["段"], "去重": S["去重"],
                       "訊號週比例": RAT[:, 0], "窗內週數": inwin.sum(axis=1), "比例有值週數": np.isfinite(RAT).sum(axis=1)})
    for h in HS:
        Pe[f"比例變化_w{h}"] = CH[:, h]; Pe[f"報酬_w{h}"] = RET[:, h]
    if len(per):
        Pe = Pe.merge(per[["sid", "資料日", "比例最高點週", "股價最高點週"]], on=["sid", "資料日"], how="left")

    w = lambda df, f: df.to_csv(os.path.join(OUTL, f), index=False, encoding="utf-8-sig", float_format="%.6g")
    w(Pe, "per_event.csv"); w(T0, "t0_coverage.csv"); w(T1, "t1_ratio_path.csv"); w(T1P, "t1_peak_week.csv")
    w(T2, "t2_cum_by_horizon.csv"); w(T3, "t3_sameweek_bands.csv"); w(T4, "t4_leadlag.csv"); w(T4P, "t4_peak_order.csv")
    w(T5, "t5_w52_quintile.csv")
    write_md(S, T0, T1, T1P, T2, T3, T4, T4P, T5, Bx)
    with open(os.path.join(OUTL, "run.log"), "w", encoding="utf-8") as f:
        f.write("\n".join(R.LOGS) + "\n")


pc = EA.pc


def pp(x, d=2):
    return "—" if x is None or not np.isfinite(x) else f"{x:+.{d}f}"


def f3(x):
    return "—" if x is None or not np.isfinite(x) else f"{x:+.3f}"


def write_md(S, T0, T1, T1P, T2, T3, T4, T4P, T5, Bx):
    dates = Bx["dates"]; cal = Bx["cal"]
    L = ["# 集保大戶比例升幅前 5%（B60）訊號後一年：大戶比例與股價的關係怎麼變", "",
         "**探索、只描述；看過才定；不判、不計 N。**（不是出場訊號測試、不是事前預測；不與抱固定天數比較）", "",
         f"回測線計算子代理｜資料 tw-stock-data `{R.SHA[:10]}`（快照；價格到 {cal[-1].date()}、集保到 {dates.iloc[-1].date()}）｜程式 `backtest/exploreBigHolderLong.py`"
         "（訊號、價格、大戶比例全用 `researchBigHolderRise.build76()`；口徑常數沿用 `exploreBigHolderAfter`）", "",
         "## 〇、母體與口徑", "",
         f"- 母體：`build76()` 的 B60 訊號事件（每檔每訊號週一筆），進場日在探索（2018-11-01～2021-12-31）或確認（2022-01-01 起）段；"
         f"全部訊號 {len(S)} 筆（探索 {(S['段'] == '探索').sum()}｜確認 {(S['段'] == '確認').sum()}）。同檔連續多週訊號照筆數算。",
         f"- 去重版：每檔只取第一次訊號，之後 52 週內不重複；{int(S['去重'].sum())} 筆（探索 {int((S['去重'] & (S['段'] == '探索')).sum())}｜確認 {int((S['去重'] & (S['段'] == '確認')).sum())}）。",
         "- 第 0 週＝訊號資料日那週（買進前）；第 k 週＝之後第 k 個週序號。第 k 週股價＝該週集保資料日（缺週用名目週五）當天或之前最後一個交易日的還原收盤。",
         "- 累積報酬＝第 k 週股價 ÷ 進場日還原開盤 − 1（進場同 B60：資料日 +2 日後第一個交易日開盤）；**未扣成本**。",
         "- 大戶比例＝集保第 12～15 級 ÷ 第 1～15 級；累積比例變化＝第 k 週比例 − 第 0 週比例（百分點 pp）。續升／持平／回落：> +0.1pp／±0.1pp／< −0.1pp。",
         "- 資料尾：第 k 週日期超過資料尾的筆在該週之後退出；下市後比例無值，成對的格自動不算（股價沿用前值不影響成對結果）。每格附 N，N < 30 標「樣本少」。",
         "- ⚠ 集保缺週：2018-12-28～2019-06-28 中間缺 25 週，另有數個 1 週缺口（如 2023-10-20 排除）；落在缺週的格不算，所以早期探索段在某些週數 N 明顯較少。",
         "- ⚠ 所有分組（續升／回落、五等分）用到第 k 週才知道的比例，屬**事後描述**；集保資料日是週五、公布約 +2 日，「同週」對齊也是事後對齊。",
         "- 沒有對照組、沒有門檻判讀；同一檔重疊的訊號不獨立，Spearman 與百分比只當描述。", ""]
    # 樣本
    L += ["### 各週樣本數（在窗內／比例有值／比例與報酬成對）", "",
          "| 口徑 | 範圍 | " + " | ".join(f"第 {h} 週" for h in HS) + " |", "|---|---|" + "---:|" * len(HS)]
    for (lab, sg), d in T0[T0["週"] > 0].groupby(["口徑", "範圍"], sort=False):
        d = d.set_index("週")
        L.append(f"| {lab} | {sg} | " + " | ".join(f"{d.loc[h, '在窗內']}／{d.loc[h, '比例有值']}／{d.loc[h, '比例與報酬成對']}" for h in HS) + " |")

    # 1
    L += ["", "## 一、大戶比例本身怎麼走", "",
          "| 口徑 | 範圍 | 週 | N | 高於訊號週 | 升超 0.1pp | 降超 0.1pp | 累積變化中位 (pp) | 平均 (pp) | 註 |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for _, r in T1.iterrows():
        L.append(f"| {r['口徑']} | {r['範圍']} | {r['週']} | {r['N']} | {pc(r['高於訊號週'])} | {pc(r['升超0.1pp'])} | {pc(r['降超0.1pp'])} | "
                 f"{pp(r['累積變化中位_pp'])} | {pp(r['累積變化平均_pp'])} | {r['註']} |")
    L += ["", f"比例最高點落在第幾週（第 0～52 週；只算 52 週窗完整、53 週中比例至少 {PEAK_MINCOV} 週有值的筆；0＝訊號週就是最高；逐週見 `t1_peak_week.csv`）：", ""]
    bins = [("0", 0, 0), ("1–4", 1, 4), ("5–8", 5, 8), ("9–12", 9, 12), ("13–26", 13, 26), ("27–39", 27, 39), ("40–52", 40, 52)]
    L += ["| 口徑 | 範圍 | N | " + " | ".join(b[0] for b in bins) + " | 中位週 | 註 |", "|---|---|---:|" + "---:|" * len(bins) + "---:|---|"]
    for (lab, sg), d in T1P.groupby(["口徑", "範圍"], sort=False):
        n = int(d["N"].iloc[0])
        cnt = d.set_index("最高點週")["筆數"]
        cs = cnt.cumsum(); med = int(cs.index[np.searchsorted(cs.values, n / 2)]) if n else np.nan
        L.append(f"| {lab} | {sg} | {n} | " + " | ".join(pc(cnt.loc[a:b].sum() / n if n else np.nan) for _, a, b in bins) + f" | {med} | {flag(n)} |")

    # 2
    L += ["", "## 二、每個週數：累積比例變化 vs 累積報酬", "",
          "Spearman＝同一週數下，各筆「累積比例變化」與「累積報酬」的名次相關。", "",
          "| 口徑 | 範圍 | 週 | N 成對 | Spearman | 續升占比 | 續升：報酬中位 | 為正 | 大漲 ≥+30% | 大跌 ≤−20% | 回落占比 | 回落：報酬中位 | 為正 | 大漲 ≥+30% | 大跌 ≤−20% | 全部：報酬中位 | 註 |",
          "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for (lab, sg, h), d in T2.groupby(["口徑", "範圍", "週"], sort=False):
        d = d.set_index("組"); u = d.loc["續升"]; v = d.loc["回落"]; a = d.loc["全部"]
        note = flag(min(u["筆數"], v["筆數"]))
        L.append(f"| {lab} | {sg} | {h} | {a['N成對']} | {f3(a['Spearman'])} | {pc(u['占比'])} | {pc(u['中位'])} | {pc(u['為正'])} | {pc(u['大漲≥+30%'])} | {pc(u['大跌≤−20%'])} | "
                 f"{pc(v['占比'])} | {pc(v['中位'])} | {pc(v['為正'])} | {pc(v['大漲≥+30%'])} | {pc(v['大跌≤−20%'])} | {pc(a['中位'])} | {note} |")
    L += ["", "（持平組另見 `t2_cum_by_horizon.csv`。）"]

    # 3
    L += ["", "## 三、同週連動隨時間（逐週，事後對齊）", "",
          "相鄰兩週（週序號連續、兩週比例都有值）：比例週變化 vs 同期還原收盤週報酬。第 1 週（含進場前的不完整週）不算，所以第一段從第 2 週起。", "",
          "| 口徑 | 範圍 | 段落 | 週對口徑 | 週對數 | Spearman | 比例升：股價漲（週數） | 比例降：股價漲（週數） | 升 >0.1pp：股價漲 | 降 >0.1pp：股價漲 | 全部週股價漲 | 註 |",
          "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for _, r in T3.iterrows():
        L.append(f"| {r['口徑']} | {r['範圍']} | {r['段落']} | {r['週對口徑']} | {r['週對數']} | {f3(r['Spearman'])} | {pc(r['比例升_股價漲'])}（{r['比例升_週數']}） | "
                 f"{pc(r['比例降_股價漲'])}（{r['比例降_週數']}） | {pc(r['升超0.1pp_股價漲'])} | {pc(r['降超0.1pp_股價漲'])} | {pc(r['全部_股價漲'])} | {r['註']} |")

    # 4
    L += ["", "## 四、誰先誰後", "",
          "### 週層級超前落後（事後對齊）", "",
          "第 t 週比例週變化 vs 第 t+k 週股價週報酬（t、t+k 都在第 2～52 週）。k > 0：比例變化在前、股價在後；k < 0：股價在前、比例在後。"
          "⚠ 集保資料日週五、公布約 +2 日，k = 0 是同週事後對齊；k = +1 那週股價的前一兩個交易日，當時集保還沒公布。只描述。", "",
          "Spearman（同股同週去重；逐筆週對版見 csv）：", "",
          "| 口徑 | 範圍 | " + " | ".join(f"k={k:+d}" for k in LAGS) + " |", "|---|---|" + "---:|" * len(LAGS)]
    T4d = T4[T4["週對口徑"] == "同股同週去重"]
    for (lab, sg), d in T4d.groupby(["口徑", "範圍"], sort=False):
        d = d.set_index("k")
        L.append(f"| {lab} | {sg} | " + " | ".join(f3(d.loc[k, "Spearman"]) for k in LAGS) + " |")
    L += ["", "比例升的週 → 第 t+k 週股價漲的比例／比例降的週 → 第 t+k 週股價漲的比例（同股同週去重，合計範圍）：", "",
          "| 口徑 | " + " | ".join(f"k={k:+d}" for k in LAGS) + " |", "|---|" + "---|" * len(LAGS)]
    for lab, d in T4d[T4d["範圍"] == "合計"].groupby("口徑", sort=False):
        d = d.set_index("k")
        L.append(f"| {lab} | " + " | ".join(f"{pc(d.loc[k, '比例升_股價漲'])}／{pc(d.loc[k, '比例降_股價漲'])}" for k in LAGS) + " |")
    L += ["", f"週對數（同股同週去重，合計）：" + "；".join(f"{lab} " + "、".join(f"k={k:+d} {int(n)}" for k, n in zip(d['k'], d['週對數']))
                                                   for lab, d in T4d[T4d['範圍'] == '合計'].groupby('口徑', sort=False))]
    L += ["", "### 每筆的「比例最高點週」與「股價最高點週」（第 0～52 週）", "",
          f"只算 52 週窗完整、比例至少 {PEAK_MINCOV} 週有值的筆。股價最高點用第 0～52 週各週還原收盤（第 0 週＝訊號週收盤）。", "",
          "| 口徑 | 範圍 | N | 比例先到頂 | 同週 | 股價先到頂 | 相差週數中位（股價−比例） | 相差絕對值中位 | 相差 ≤4 週 | 比例最高點週中位 | 股價最高點週中位 | 註 |",
          "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for _, r in T4P.iterrows():
        L.append(f"| {r['口徑']} | {r['範圍']} | {r['N']} | {pc(r['比例先到頂'])} | {pc(r['同週'])} | {pc(r['股價先到頂'])} | {r['相差週數中位_股價減比例']:+.0f} | "
                 f"{r['相差週數絕對值中位']:.0f} | {pc(r['相差≤4週'])} | {r['比例最高點週中位']:.0f} | {r['股價最高點週中位']:.0f} | {r['註']} |")

    # 5
    L += ["", "## 五、一年後（第 52 週）：依比例累積變化五等分", "", "各範圍內各自切；Q1 回落最多、Q5 升最多。", "",
          "| 口徑 | 範圍 | 五等分 | 筆數 | 報酬中位 | 平均 | 為正 | 大漲 ≥+30% | 大跌 ≤−20% | 註 |", "|---|---|---|---:|---:|---:|---:|---:|---:|---|"]
    for _, r in T5.iterrows():
        L.append(f"| {r['口徑']} | {r['範圍']} | Q{r['五等分']}（{r['變化下限_pp']:+.2f}～{r['變化上限_pp']:+.2f}pp） | {r['筆數']} | {pc(r['中位'])} | {pc(r['平均'])} | "
                 f"{pc(r['為正'])} | {pc(r['大漲≥+30%'])} | {pc(r['大跌≤−20%'])} | {r['註']} |")
    L += ["", "## 六、檔案", "",
          "- `per_event.csv`：逐筆（訊號週比例、各週數比例累積變化與累積報酬、最高點週）",
          "- `t0_coverage.csv`、`t1_ratio_path.csv`、`t1_peak_week.csv`、`t2_cum_by_horizon.csv`、`t3_sameweek_bands.csv`、`t4_leadlag.csv`、`t4_peak_order.csv`、`t5_w52_quintile.csv`、`run.log`", ""]
    with open(os.path.join(OUTL, "探索.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    main()
