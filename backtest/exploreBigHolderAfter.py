# -*- coding: utf-8 -*-
"""集保大戶比例 4 週升幅前 5%（全收版）買進後：股價與大戶比例的關聯——探索、只描述；看過才定；不判、不計 N。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.exploreBigHolderAfter

母體：backtest/resultsBigHolderRise/formal/trades.csv 的「全收版」全部買進筆（正式跑主口徑，毛報酬＝未扣成本）。
訊號、價格、大戶比例一律用 researchBigHolderRise.build76()（同一份 cal／ACf／AO／bw／dates／SIG），⛔ 不另寫第二套。

週對齊：
 第 0 週 ＝ 訊號資料日那週（買進前）；第 k 週 ＝ 週序號 w0+k（週 ＝ (資料日 − 2017-01-02)//7，同週取較晚那份＝bw）。
 「持有期間的週」＝ 資料日落在 [進場日, 出場日] 的那幾週。
 出場前最後一週 ＝ 持有期間資料日最晚、且該股比例有值的那週。
 同週連動：相鄰兩週（週序號連續、兩個資料日都在持有期間內）的比例變化 vs 同期還原收盤報酬
   （資料日當天或之前最後一個交易日收盤 → 下一個資料日當天或之前最後一個交易日收盤；ACf 停牌沿用前值）。
   集保資料日是週五、公布約 +2 日 ⇒ 這是「同週」事後描述，不是買進當時看得到的東西。
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

from backtest import data as D
from backtest import researchBigHolderRise as R

OUTE = os.path.join(R.HERE, "resultsBigHolderRise", "explore_after")
TRADES = os.path.join(R.OUTF, "trades.csv")
FLAT = 0.001          # ±0.1 百分點
BIG_UP = 0.30
BIG_DN = -0.20
TOPQ = 0.95
KMAX = 12
SMALL = 30


def flag(n):
    return "樣本少" if n < SMALL else ""


def ret_stats(r: pd.Series) -> dict:
    n = len(r)
    if n == 0:
        return {"筆數": 0, "中位": np.nan, "平均": np.nan, "為正": np.nan, "大漲≥+30%": np.nan, "大跌≤−20%": np.nan, "註": "樣本少"}
    return {"筆數": n, "中位": float(r.median()), "平均": float(r.mean()), "為正": float((r > 0).mean()),
            "大漲≥+30%": float((r >= BIG_UP).mean()), "大跌≤−20%": float((r <= BIG_DN).mean()), "註": flag(n)}


def build_trades(Bx):
    cal = Bx["cal"]; bw = Bx["bw"]; dates = Bx["dates"]; ACf = Bx["ACf"]; AO = Bx["AO"]; SIG = Bx["SIG"]
    T = pd.read_csv(TRADES, dtype={"sid": str}, encoding="utf-8-sig")
    T = T[T["版"] == "全收版"].copy()
    T["進場日"] = pd.to_datetime(T["進場日"]); T["賣出日"] = pd.to_datetime(T["賣出日"])
    S = SIG.copy()
    S["進場日"] = pd.to_datetime(S["進場日"]); S["資料日"] = pd.to_datetime(S["資料日"])
    S = S.sort_values(["資料日", "當週名次"])
    S["n"] = S.groupby(["進場日", "sid"]).cumcount()
    T["n"] = T.groupby(["進場日", "sid"]).cumcount()
    M = T.merge(S[["進場日", "sid", "n", "資料日", "升幅_pp", "e", "x"]], on=["進場日", "sid", "n"], how="left")
    miss = int(M["資料日"].isna().sum())
    R.log(f"[母體] 全收版買進 {len(T)} 筆（探索 {(T['段'] == '探索').sum()}｜確認 {(T['段'] == '確認').sum()}）｜對不到訊號 {miss}")
    M = M.dropna(subset=["資料日"]).copy()
    # 毛報酬核對（ACf[x]/AO[e]−1）
    chk = np.array([ACf.iat[int(x), ACf.columns.get_loc(s)] / AO.iat[int(e), AO.columns.get_loc(s)] - 1
                    for s, e, x in zip(M.sid, M.e, M.x)])
    dmax = float(np.nanmax(np.abs(chk - M["毛報酬"].values)))
    sell_ok = bool((pd.to_datetime([cal[int(x)] for x in M.x]) == M["賣出日"].values).all())
    R.log(f"[核對] 毛報酬 vs ACf[x]/AO[e]−1 最大差 {dmax:.2e}｜賣出日＝第 60 根 {sell_ok}")
    wk_of = {d: w for w, d in dates.items()}
    bwcols = set(bw.columns)
    recs = []; pairs = []; paths = []
    for i, r in M.iterrows():
        s = r.sid; d0 = r["資料日"]; w0 = int(wk_of[d0]); ed = r["進場日"]; xd = r["賣出日"]
        if s not in bwcols:
            continue
        col = bw[s]
        b0 = col.get(w0, np.nan)
        # 路徑 0..KMAX（不論是否在持有期間；另記是否在持有期間）
        for k in range(KMAX + 1):
            w = w0 + k
            if w in col.index and pd.notna(col[w]) and pd.notna(b0):
                paths.append((i, k, float(col[w] - b0), bool(ed <= dates[w] <= xd)))
        hold = [w for w in col.index if w > w0 and ed <= dates[w] <= xd and pd.notna(col[w])]
        rec = {"i": i, "段": r["段"], "sid": s, "資料日": d0.date(), "進場日": ed.date(), "賣出日": xd.date(), "毛報酬": float(r["毛報酬"]),
               "訊號週比例": float(b0), "訊號週Δ4_pp": float(r["升幅_pp"]), "持有週數": len(hold)}
        if hold and pd.notna(b0):
            vals = np.array([col[w] for w in hold])
            rec["最後週"] = int(hold[-1] - w0); rec["最後週比例"] = float(vals[-1]); rec["變化"] = float(vals[-1] - b0)
            allv = np.concatenate([[b0], vals]); allk = np.concatenate([[0], np.array(hold) - w0])
            rec["最高點週"] = int(allk[int(np.argmax(allv))])
            rec["持有期最大升幅"] = float(vals.max() - b0)
        recs.append(rec)
        # 同週連動
        cidx = ACf.columns.get_loc(s)
        for a_, b_ in zip(hold[:-1], hold[1:]):
            if b_ != a_ + 1:
                continue
            ia = int(cal.searchsorted(dates[a_], side="right")) - 1
            ib = int(cal.searchsorted(dates[b_], side="right")) - 1
            pa = ACf.iat[ia, cidx]; pb = ACf.iat[ib, cidx]
            if not (np.isfinite(pa) and np.isfinite(pb) and pa > 0):
                continue
            pairs.append((i, r["段"], s, int(b_), float(col[b_] - col[a_]), float(pb / pa - 1)))
    P = pd.DataFrame(recs)
    PR = pd.DataFrame(pairs, columns=["i", "段", "sid", "wk", "比例週變化", "股價週報酬"])
    PA = pd.DataFrame(paths, columns=["i", "k", "累積變化", "在持有期間"])
    return P, PR, PA, {"對不到訊號": miss, "毛報酬最大差": dmax, "賣出日核對": sell_ok, "母體筆數": len(T)}


def scopes(df):
    yield "探索", df[df["段"] == "探索"]
    yield "確認", df[df["段"] == "確認"]
    yield "合計", df


def cls(v):
    return np.where(v > FLAT, "續升", np.where(v < -FLAT, "回落", "持平"))


def main():
    os.makedirs(OUTE, exist_ok=True)
    D.DATA = R.DATA
    R.LOGS.clear()
    R.log(f"[資料] tw-stock-data {R.SHA[:10]}｜探索、只描述（不判、不計 N）")
    Bx = R.build76()
    P, PR, PA, info = build_trades(Bx)
    P.to_csv(os.path.join(OUTE, "per_trade.csv"), index=False, encoding="utf-8-sig", float_format="%.8g")
    has = P.dropna(subset=["變化"]).copy()
    has["類"] = cls(has["變化"].values)
    R.log(f"[週資料] 有持有期間比例的筆 {len(has)}／{len(P)}；持有週數分布 {P['持有週數'].value_counts().sort_index().to_dict()}")

    # ① 續升／持平／回落；最高點週
    t1 = []; t1p = []
    for sc, d in scopes(has):
        n = len(d)
        row = {"範圍": sc, "筆數": n}
        for c in ("續升", "持平", "回落"):
            row[c] = float((d["類"] == c).mean()) if n else np.nan
        row["變化中位_pp"] = float(d["變化"].median() * 100); row["變化平均_pp"] = float(d["變化"].mean() * 100)
        row["持有期曾高於訊號週"] = float((d["持有期最大升幅"] > 0).mean())
        row["註"] = flag(n); t1.append(row)
        vc = d["最高點週"].value_counts()
        for k in range(0, KMAX + 2):
            m = int(vc.get(k, 0))
            if k == KMAX + 1:
                m = int(vc[vc.index > KMAX].sum())
            t1p.append({"範圍": sc, "最高點週": (f"{k}+" if k == KMAX + 1 else k), "筆數": m, "占比": m / n if n else np.nan})
    T1 = pd.DataFrame(t1); T1P = pd.DataFrame(t1p)
    T1.to_csv(os.path.join(OUTE, "t1_change_class.csv"), index=False, encoding="utf-8-sig", float_format="%.6g")
    T1P.to_csv(os.path.join(OUTE, "t1_peak_week.csv"), index=False, encoding="utf-8-sig", float_format="%.6g")

    # ② 報酬 by 類、by 五等分
    t2 = []; t2q = []
    for sc, d in scopes(has):
        for c in ("續升", "持平", "回落"):
            t2.append({"範圍": sc, "組": c} | ret_stats(d.loc[d["類"] == c, "毛報酬"]))
        t2.append({"範圍": sc, "組": "全部（有週資料）"} | ret_stats(d["毛報酬"]))
        q = pd.qcut(d["變化"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5])
        for k in range(1, 6):
            dd = d[q == k]
            t2q.append({"範圍": sc, "五等分": k, "變化下限_pp": float(dd["變化"].min() * 100), "變化上限_pp": float(dd["變化"].max() * 100)}
                       | ret_stats(dd["毛報酬"]))
    T2 = pd.DataFrame(t2); T2Q = pd.DataFrame(t2q)
    T2.to_csv(os.path.join(OUTE, "t2_ret_by_class.csv"), index=False, encoding="utf-8-sig", float_format="%.6g")
    T2Q.to_csv(os.path.join(OUTE, "t2_ret_by_quintile.csv"), index=False, encoding="utf-8-sig", float_format="%.6g")

    # ③ 同週連動
    t3 = []
    for sc, d in scopes(PR):
        for lab, dd in (("全部週對（含重複持有的同股同週）", d), ("同股同週去重", d.drop_duplicates(["sid", "wk"]))):
            n = len(dd)
            rho = float(np.corrcoef(dd["比例週變化"].rank(), dd["股價週報酬"].rank())[0, 1]) if n > 2 else np.nan   # Spearman＝名次（平手取平均）的 Pearson
            up = dd["比例週變化"] > 0; dn = dd["比例週變化"] < 0; z = dd["比例週變化"] == 0
            upb = dd["比例週變化"] > FLAT; dnb = dd["比例週變化"] < -FLAT
            px = dd["股價週報酬"] > 0
            t3.append({"範圍": sc, "口徑": lab, "週對數": n, "Spearman": rho,
                       "比例升_週數": int(up.sum()), "比例升_股價漲比例": float(px[up].mean()),
                       "比例降_週數": int(dn.sum()), "比例降_股價漲比例": float(px[dn].mean()),
                       "比例不變_週數": int(z.sum()), "比例不變_股價漲比例": float(px[z].mean()) if z.any() else np.nan,
                       "升超0.1pp_週數": int(upb.sum()), "升超0.1pp_股價漲比例": float(px[upb].mean()),
                       "降超0.1pp_週數": int(dnb.sum()), "降超0.1pp_股價漲比例": float(px[dnb].mean()),
                       "全部_股價漲比例": float(px.mean()),
                       "比例升_股價週報酬中位": float(dd.loc[up, "股價週報酬"].median()), "比例降_股價週報酬中位": float(dd.loc[dn, "股價週報酬"].median()),
                       "註": flag(min(int(up.sum()), int(dn.sum())))})
    T3 = pd.DataFrame(t3)
    T3.to_csv(os.path.join(OUTE, "t3_sameweek.csv"), index=False, encoding="utf-8-sig", float_format="%.6g")

    # ④ 大漲股（各範圍持有期報酬前 5%）vs 其他：第 0～12 週平均累積變化
    t4 = []
    PA2 = PA.merge(P[["i", "段", "毛報酬"]], on="i")
    for sc, d in scopes(P):
        cut = float(d["毛報酬"].quantile(TOPQ))
        top = set(d.loc[d["毛報酬"] >= cut, "i"])
        pa = PA2[PA2.i.isin(set(d.i))]
        for k in range(KMAX + 1):
            pk = pa[pa.k == k]
            row = {"範圍": sc, "週": k, "前5%門檻_毛報酬": cut}
            for lab, g in (("大漲股", pk[pk.i.isin(top)]), ("其他", pk[~pk.i.isin(top)])):
                row[f"{lab}_筆數"] = len(g); row[f"{lab}_平均累積_pp"] = float(g["累積變化"].mean() * 100) if len(g) else np.nan
                row[f"{lab}_中位累積_pp"] = float(g["累積變化"].median() * 100) if len(g) else np.nan
                row[f"{lab}_升的比例"] = float((g["累積變化"] > 0).mean()) if len(g) and k > 0 else np.nan
                row[f"{lab}_在持有期間比例"] = float(g["在持有期間"].mean()) if len(g) else np.nan
            row["註"] = flag(min(row["大漲股_筆數"], row["其他_筆數"]))
            t4.append(row)
    T4 = pd.DataFrame(t4)
    T4.to_csv(os.path.join(OUTE, "t4_path_top5_vs_rest.csv"), index=False, encoding="utf-8-sig", float_format="%.6g")

    write_md(P, has, T1, T1P, T2, T2Q, T3, T4, info)
    with open(os.path.join(OUTE, "run.log"), "w", encoding="utf-8") as f:
        f.write("\n".join(R.LOGS) + "\n")


def pc(x, d=1):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x * 100:.{d}f}%"


def pp(x, d=2):
    return "—" if not np.isfinite(x) else f"{x:+.{d}f}"


def write_md(P, has, T1, T1P, T2, T2Q, T3, T4, info):
    L = ["# 集保大戶比例升幅前 5%（全收版）買進後：股價與大戶比例的關聯", "",
         "**探索、只描述；看過才定；不判、不計 N。**（不是出場訊號測試、不是事前預測；不與抱固定天數比較）", "",
         f"回測線計算子代理｜資料 tw-stock-data `{R.SHA[:10]}`｜程式 `backtest/exploreBigHolderAfter.py`（訊號、價格、大戶比例全用 `researchBigHolderRise.build76()`）", "",
         "## 〇、母體與口徑", "",
         f"- 母體：`formal/trades.csv` 全收版全部買進筆 {info['母體筆數']} 筆（對不到訊號 {info['對不到訊號']}）；毛報酬核對最大差 {info['毛報酬最大差']:.1e}；賣出日＝第 60 根：{info['賣出日核對']}",
         f"- 持有期報酬＝毛報酬（進場開盤 → 第 60 根收盤，還原；**未扣成本**）。",
         f"- 有持有期間週資料（比例有值）的筆：{len(has)}／{len(P)}。",
         "- 大戶比例＝集保第 12～15 級股數 ÷ 第 1～15 級；第 0 週＝訊號資料日那週（買進前），第 k 週＝之後第 k 個週序號；持有期間的週＝資料日在 [進場日, 出場日]。",
         "- 續升／持平／回落：出場前最後一週比例 − 訊號週比例，> +0.1 百分點／±0.1 內／< −0.1 百分點。",
         "- ⚠ 時間對齊：集保資料日是週五、公布約 +2 日；第三節是「同週」對齊（同一資料日所屬那週的收盤），**屬事後描述**，當週收盤時還看不到該週集保。",
         "- ⚠ 第一、二、四節的分組（續升／回落、五等分、大漲股）用到出場時才知道的資訊，同屬事後描述；比例與股價都是持有期間同時發生的事。",
         "- ⚠ 集保缺週：2018-12-28～2019-06-28 中間缺 25 週（另有數個 1 週缺口，如 2023-10-20 排除）；2018-11～12 進場的探索段部分筆持有期間週資料很少或沒有（沒有的 16 筆不列入第一、二節）。",
         "- 分組筆數 < 30 標「樣本少」。", ""]
    # 1
    L += ["## 一、買進後大戶比例還在升嗎", "", "| 範圍 | 筆數 | 續升 | 持平 | 回落 | 變化中位 (pp) | 變化平均 (pp) | 持有期曾高於訊號週 | 註 |", "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for _, r in T1.iterrows():
        L.append(f"| {r['範圍']} | {r['筆數']} | {pc(r['續升'])} | {pc(r['持平'])} | {pc(r['回落'])} | {pp(r['變化中位_pp'])} | {pp(r['變化平均_pp'])} | {pc(r['持有期曾高於訊號週'])} | {r['註']} |")
    L += ["", "持有期間比例最高點出現在第幾週（0＝訊號週就是最高，之後都沒超過）：", ""]
    piv = T1P.pivot(index="最高點週", columns="範圍", values="占比")
    cnt = T1P.pivot(index="最高點週", columns="範圍", values="筆數")
    order = list(T1P["最高點週"].drop_duplicates())
    L += ["| 最高點週 | 探索 | 確認 | 合計（筆） |", "|---|---:|---:|---:|"]
    for k in order:
        L.append(f"| {k} | {pc(piv.loc[k, '探索'])} | {pc(piv.loc[k, '確認'])} | {pc(piv.loc[k, '合計'])}（{int(cnt.loc[k, '合計'])}） |")
    # 2
    def rtab(df, key):
        out = [f"| 範圍 | {key} | 筆數 | 中位 | 平均 | 為正 | 大漲 ≥+30% | 大跌 ≤−20% | 註 |", "|---|---|---:|---:|---:|---:|---:|---:|---|"]
        for _, r in df.iterrows():
            lab = r[key] if key != "五等分" else f"Q{r['五等分']}（{r['變化下限_pp']:+.2f}～{r['變化上限_pp']:+.2f}pp）"
            out.append(f"| {r['範圍']} | {lab} | {r['筆數']} | {pc(r['中位'])} | {pc(r['平均'])} | {pc(r['為正'])} | {pc(r['大漲≥+30%'])} | {pc(r['大跌≤−20%'])} | {r['註']} |")
        return out
    L += ["", "## 二、比例續升 vs 回落：持有期報酬（毛）", ""] + rtab(T2, "組")
    L += ["", "依「出場前最後一週 − 訊號週」比例變化分五等分（各範圍內各自切；Q1 回落最多、Q5 升最多）：", ""] + rtab(T2Q, "五等分")
    # 3
    L += ["", "## 三、同週連動（事後描述）", "",
          "持有期間相鄰兩週（兩個資料日都在持有期間內、週序號連續）：比例週變化 vs 同期還原收盤週報酬。買進後第一個不完整的週不算。", "",
          "| 範圍 | 口徑 | 週對數 | Spearman | 比例升：股價漲（週數） | 比例降：股價漲（週數） | 比例不變：股價漲（週數） | 升 >0.1pp：股價漲 | 降 >0.1pp：股價漲 | 全部週股價漲 |",
          "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _, r in T3.iterrows():
        L.append(f"| {r['範圍']} | {r['口徑']} | {r['週對數']} | {r['Spearman']:+.3f} | {pc(r['比例升_股價漲比例'])}（{r['比例升_週數']}） | {pc(r['比例降_股價漲比例'])}（{r['比例降_週數']}） | "
                 f"{pc(r['比例不變_股價漲比例'])}（{r['比例不變_週數']}） | {pc(r['升超0.1pp_股價漲比例'])}（{r['升超0.1pp_週數']}） | {pc(r['降超0.1pp_股價漲比例'])}（{r['降超0.1pp_週數']}） | {pc(r['全部_股價漲比例'])} |")
    # 4
    L += ["", "## 四、大漲股（各範圍持有期毛報酬前 5%）vs 其他：買進後大戶比例路徑", "",
          "每週相對訊號週（第 0 週）的累積變化（百分點）；第 12 週的資料日可能已在出場日之後（見 csv「在持有期間比例」）。", ""]
    for sc in ("探索", "確認", "合計"):
        d = T4[T4["範圍"] == sc]
        L += [f"**{sc}**（前 5% 門檻：毛報酬 ≥ {pc(d['前5%門檻_毛報酬'].iloc[0])}）", "",
              "| 週 | 大漲股 平均 | 大漲股 中位 | 大漲股 升的比例 | 筆數 | 其他 平均 | 其他 中位 | 其他 升的比例 | 筆數 | 註 |", "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
        for _, r in d.iterrows():
            L.append(f"| {r['週']} | {pp(r['大漲股_平均累積_pp'])} | {pp(r['大漲股_中位累積_pp'])} | {pc(r['大漲股_升的比例'])} | {r['大漲股_筆數']} | "
                     f"{pp(r['其他_平均累積_pp'])} | {pp(r['其他_中位累積_pp'])} | {pc(r['其他_升的比例'])} | {r['其他_筆數']} | {r['註']} |")
        L.append("")
    L += ["## 五、檔案", "", "- `per_trade.csv`：逐筆（訊號週比例、最後週、變化、最高點週、毛報酬）",
          "- `t1_change_class.csv`、`t1_peak_week.csv`、`t2_ret_by_class.csv`、`t2_ret_by_quintile.csv`、`t3_sameweek.csv`、`t4_path_top5_vs_rest.csv`、`run.log`", ""]
    with open(os.path.join(OUTE, "探索.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    main()
