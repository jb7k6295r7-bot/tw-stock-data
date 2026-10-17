# -*- coding: utf-8 -*-
"""大盤大跌後 C+ 名單的【排除規則】描述性測試（像 2221 大甲：大跌前 60 日大漲、已從高點轉弱）——⛔ 不計 N、⛔ 不判定、⛔ 不是買賣建議
回測線計算子代理，2026-10-17。使用者：「像這種怎麼在名單內排除？或是可以試試看？」

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMktDrop_excl

═══ 讀法（寫死於第一次跑之前；⚠ 規則是看過 10/15 大甲被挑中之後才提的 ⇒ 事後設計）═══
 E0 ⛔ 不重算任何特徵與分數：tc_r60、tc_d52、ch_i20、淨報酬、買得到讀 resultsMktDrop/fund/features.csv；F6、F7、Q 讀 resultsMktDrop/f9/features.csv（18 事件 1007 列）
 E1 排除規則（每條單獨；門檻見下方常數，讀報酬前寫死）：
    X1 前 60 日漲 ＞ 100%（tc_r60 ＞ 1.00）；X2 前 60 日漲 ＞ 50%（tc_r60 ＞ 0.50）
    X3 大跌前距 52 週高已跌 ＞ 15%（tc_d52 ＜ −0.15；tc_d52 原檔定義 ＝ c[事件日前一天] ÷ max(前 250 日收盤) − 1，本來就不含大跌當天 ⇒ 不必用 tc_drop 還原；程式內驗 tc_d52 ≤ 0）
    X4 X1 且 X3；X5 近 20 日（含事件日）三大法人淨買÷成交量 ＜ 0（ch_i20 ＜ 0，賣超）
    特徵缺值 ⇒ 不排除（留下）；ch_i20 2015 年起才有
 E2 逐檔層：被排除 vs 留下 vs 全部（只計買得到者）：逐檔平均、中位、賺錢比例、虧 ＞10% 比例；事件等權平均；
    事件群集 bootstrap（2000 次）95% CI：每事件（留下等權 − C+ 全部等權）的事件平均；留下為空 ⇒ 該事件留下報酬記 0（空手）
 E3 組合層：每條規則排除後，C+ 全買、隨機挑 1/2/3（2000 次，同 pick／fund／f9 種子與事件序號；在剩下名單中抽）、F8 前 3、F9 前 3
    （F8／F9 在剩下名單內重算名次百分位再排序 ＝ 遞補；同分規則同 f8／f9）；選中買不到者不計、全買不到 ⇒ 0
    報每次平均、中位、勝率、最差、虧 ＞10% 次數、空手事件數；隨機的最差、虧 ＞10% 次數 ＝ 每輪段內值的平均；
    「無排除」版本程式內對帳 f9/summary.csv、f8/summary.csv、f9/event_picks.csv
 E4 分段：2015～2021（7）、2022～（11）、2015～（18 事件）；逐檔層另附 2006～2014 與 28 事件（X5 早年無資料 ⇒ 不排）
 E5 10/15 前瞻：C+ 75 檔各規則排掉哪些；2221 是否被排；F8、F9 前 3 排除前後（無排除版本對帳 f8／f9 forward）
 E6 必附：事後設計（看過大甲才提）；5 條規則 × 多種方法 × 3 段 ⇒ 多重比較；只有 18 事件；描述性、不計 N、不判定
輸出 backtest/resultsMktDrop/excl/：MktDrop_excl.json、stock.csv、portfolio.csv、forward_20261015.csv、forward_top3.csv、run.log
"""
from __future__ import annotations

import json
import os
import time

import numpy as np
import pandas as pd

from backtest import researchMktDrop_fund as FU

# ═══ 門檻（讀報酬前寫死）═══
X_R60_HI = 1.00     # X1：前 60 日漲 > 100%
X_R60_MID = 0.50    # X2：前 60 日漲 > 50%
X_D52 = -0.15       # X3：大跌前距 52 週高 < -15%
X_I20 = 0.0         # X5：ch_i20 < 0
RULES = ["無", "X1", "X2", "X3", "X4", "X5"]
RNAME = {"無": "不排除", "X1": "X1 前60日漲>100%", "X2": "X2 前60日漲>50%", "X3": "X3 大跌前距52週高<-15%",
         "X4": "X4 X1且X3", "X5": "X5 近20日法人賣超"}
NB = 2000
BSEED = 2026101703

REPO = os.path.expanduser("~/tw-p17")
FD = os.path.join(REPO, "backtest/resultsMktDrop/fund")
F8D = os.path.join(REPO, "backtest/resultsMktDrop/f8")
F9D = os.path.join(REPO, "backtest/resultsMktDrop/f9")
QD = os.path.join(REPO, "backtest/resultsMktDrop/quality")
OUT = os.path.join(REPO, "backtest/resultsMktDrop/excl")
NR, SEED = FU.NR, FU.SEED
NOTES = ["描述性：⛔ 不計 N、⛔ 不判定、⛔ 不是買賣建議；候選一律只限該事件 C+（大跌日跌最多一成 ∧ 營收年增 ＞ 0）",
         "⚠ 事後設計：五條規則都是看過 10/15 F8／F9 挑中 2221 大甲之後才提的；門檻 100%、50%、15% 是整數直覺值，沒有調",
         "⚠ 多重比較：5 條規則 × （逐檔＋C+ 全買＋隨機 3 種＋F8＋F9）× 3 段；碰巧好看或難看的格子一定會有",
         "⚠ 只有 18 個事件（2015～2021 7、2022～ 11）；一兩個事件就能翻動平均；CI 只反映事件抽樣，不含多重比較",
         "tc_d52 原檔就是大跌前一天收盤距前 250 日最高收盤 ⇒ X3 直接用 tc_d52，不必用 tc_drop 還原",
         "ch_i20 含事件日當天；2221 在 10/15 的 ch_i20 ＝ +0.3%（20 日小買）、ch_i5 ＝ −3.3% ⇒ X5 不會排掉 2221",
         "主出場「加權收盤收復事件前一日收盤 ⇒ 隔天開盤賣」不設天數；成本 0.585% 來回；未含滑價"]
LOG = []


def log(s):
    print(s, flush=True); LOG.append(s)


def flags(d):
    r60 = d["tc_r60"].to_numpy(float); d52 = d["tc_d52"].to_numpy(float); i20 = d["ch_i20"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        x1 = np.nan_to_num(r60, nan=-9) > X_R60_HI
        x2 = np.nan_to_num(r60, nan=-9) > X_R60_MID
        x3 = np.nan_to_num(d52, nan=0) < X_D52
        x5 = np.nan_to_num(i20, nan=0) < X_I20
    return {"無": np.zeros(len(d), bool), "X1": x1, "X2": x2, "X3": x3, "X4": x1 & x3, "X5": x5}


def add_rank(d):
    """在 d（單一事件、已排除後）內重算名次百分位 ⇒ F8、F9（同 f8／f9 規則）"""
    d = d.copy()
    d["r6"] = d["F6"].rank(pct=True, method="average") * 100
    d["r7"] = d["F7"].rank(pct=True, method="average") * 100
    d["F8"] = d["r6"] + d["r7"]
    if "Q" in d:
        d["rQ"] = d["Q"].rank(pct=True, method="average") * 100
        d["F9"] = (d["r6"] + d["r7"] + d["rQ"]).round(6)
    return d


def order(d, sc):
    d = d.sort_values("sid", kind="mergesort")
    return d.sort_values([sc, "F7"], ascending=[False, False], kind="mergesort")


def pret(d):
    b = d[d["買得到"]]
    return (float(b["淨報酬"].mean()) if len(b) else 0.0), len(b)


def main():
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    pd.set_option("display.width", 260); pd.set_option("display.max_rows", 900); pd.set_option("display.max_columns", 40)
    ALL = pd.read_csv(os.path.join(FD, "features.csv"), dtype={"sid": str})
    ALL["買得到"] = ALL["買得到"].astype(str).str.lower().eq("true")
    assert len(ALL) == 1402 and ALL["事件日"].nunique() == 28
    assert (ALL["tc_d52"].dropna() <= 1e-9).all(), "tc_d52 應 ≤ 0（距高點）"
    evs_all = sorted(ALL["事件日"].unique()); seg_of = ALL.drop_duplicates("事件日").set_index("事件日")["段"].to_dict()
    F9F = pd.read_csv(os.path.join(F9D, "features.csv"), dtype={"sid": str})
    CP = ALL.merge(F9F[["事件日", "sid", "Q", "F6", "F7"]].rename(columns={"F6": "F6_9", "F7": "F7_9"}), on=["事件日", "sid"], how="inner")
    assert len(CP) == 1007 and CP["事件日"].nunique() == 18
    assert float((CP["F6"] - CP["F6_9"]).abs().max()) < 1e-5 and float((CP["F7"] - CP["F7_9"]).abs().max()) < 1e-3
    CP = CP.drop(columns=["F6_9", "F7_9"])
    evs = sorted(CP["事件日"].unique())
    segev = {"2015～2021": [e for e in evs if seg_of[e] == "2015～2021"], "2022～": [e for e in evs if seg_of[e] == "2022～"], "2015～（18事件）": evs}
    FL = flags(ALL)
    for r in RULES:
        ALL[f"ex_{r}"] = FL[r]
    CP = CP.merge(ALL[["事件日", "sid"] + [f"ex_{r}" for r in RULES]], on=["事件日", "sid"], how="left")
    log(f"[讀檔] fund/features 1402 列 28 事件；f9/features Q ⇒ 2015 起 {len(CP)} 列 {len(evs)} 事件")
    log(f"[缺值] 18 事件 tc_r60 缺 {int(CP['tc_r60'].isna().sum())}、tc_d52 缺 {int(CP['tc_d52'].isna().sum())}、ch_i20 缺 {int(CP['ch_i20'].isna().sum())}（缺 ⇒ 不排除）")
    log("[排除檔數（18 事件 C+ 1007 列）] " + "、".join(f"{r} {int(CP[f'ex_{r}'].sum())}" for r in RULES[1:]))

    # ── 逐檔層 ──
    rng_b = np.random.default_rng(BSEED)
    STK = []
    segstk = dict(segev); segstk["2006～2014"] = [e for e in evs_all if seg_of[e] == "2006～2014"]; segstk["全部（28事件）"] = evs_all
    boot_ix = {sg: rng_b.integers(0, len(es), size=(NB, len(es))) for sg, es in segstk.items()}
    for sg, es in segstk.items():
        D = ALL[ALL["事件日"].isin(es)]
        for r in RULES[1:]:
            row = {"段": sg, "規則": r, "名稱": RNAME[r], "事件數": len(es)}
            for gname, m in (("排除", D[f"ex_{r}"]), ("留下", ~D[f"ex_{r}"]), ("全部", pd.Series(True, index=D.index))):
                g = D[m & D["買得到"]]; x = g["淨報酬"].to_numpy(float)
                row[f"{gname}_檔數"] = int(m.sum()); row[f"{gname}_買得到"] = len(x)
                if len(x):
                    em = g.groupby("事件日")["淨報酬"].mean()
                    row.update({f"{gname}_逐檔平均": x.mean(), f"{gname}_中位": float(np.median(x)), f"{gname}_賺錢比例": float((x > 0).mean()),
                                f"{gname}_虧>10%比例": float((x < -0.10).mean()), f"{gname}_事件等權平均": float(em.mean()), f"{gname}_有檔事件數": len(em)})
            # 事件群集 bootstrap：每事件 留下 − 全部（留下空 ⇒ 0）；另 排除 − 留下（兩者都有才算）
            dk = []; dx = []
            for e in es:
                de = D[D["事件日"] == e]; a_, _ = pret(de); k_, nk = pret(de[~de[f"ex_{r}"]]); x_, nx = pret(de[de[f"ex_{r}"]])
                dk.append(k_ - a_)
                dx.append(x_ - k_ if (nk and nx) else np.nan)
            dk = np.array(dk); bi = boot_ix[sg]; bm = dk[bi].mean(axis=1)
            row.update({"留下−全部_事件平均": float(dk.mean()), "留下−全部_CI低": float(np.quantile(bm, .025)), "留下−全部_CI高": float(np.quantile(bm, .975)),
                        "留下勝過全部事件數": int((dk > 1e-12).sum()), "留下輸給全部事件數": int((dk < -1e-12).sum())})
            dx = np.array(dx); okx = np.isfinite(dx)
            if okx.sum() >= 3:
                bx = np.array([np.nanmean(dx[b]) if np.isfinite(dx[b]).any() else np.nan for b in bi])
                row.update({"排除−留下_事件平均": float(np.nanmean(dx)), "排除−留下_可比事件數": int(okx.sum()),
                            "排除−留下_CI低": float(np.nanquantile(bx, .025)), "排除−留下_CI高": float(np.nanquantile(bx, .975))})
            STK.append(row)
    STK = pd.DataFrame(STK)
    STK.to_csv(os.path.join(OUT, "stock.csv"), index=False, float_format="%.6g", encoding="utf-8")
    sc_ = ["段", "規則", "排除_買得到", "排除_逐檔平均", "排除_中位", "排除_賺錢比例", "排除_虧>10%比例", "留下_買得到", "留下_逐檔平均", "留下_中位",
           "留下_賺錢比例", "留下_虧>10%比例", "全部_逐檔平均", "全部_賺錢比例", "排除_事件等權平均", "留下_事件等權平均", "全部_事件等權平均",
           "留下−全部_事件平均", "留下−全部_CI低", "留下−全部_CI高", "排除−留下_事件平均", "排除−留下_CI低", "排除−留下_CI高"]
    log("[逐檔層：排除 vs 留下（只計買得到）]\n" + STK[sc_].to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    # 對帳：全部_事件等權平均（18 事件段）＝ f9 C+全買
    F9S = pd.read_csv(os.path.join(F9D, "summary.csv")); F9S["N_"] = pd.to_numeric(F9S["N"], errors="coerce").fillna(0).astype(int)
    F8S = pd.read_csv(os.path.join(F8D, "summary.csv"))
    mx = 0.0
    for sg in segev:
        v = float(STK[(STK["段"] == sg)]["全部_事件等權平均"].iloc[0]); f = float(F9S[(F9S["段"] == sg) & (F9S["方法"] == "C+全買")]["平均"].iloc[0])
        mx = max(mx, abs(v - f))
    log(f"[對帳] 逐檔層「全部」事件等權平均 vs f9/summary C+全買：最大差 {mx:.2e}"); assert mx < 1e-6

    # ── 組合層 ──
    EPK = []; PRT = []
    RSall = {}
    for r in RULES:
        res = {}
        for i, ev in enumerate(evs_all):
            if ev not in evs:
                continue
            d = CP[CP["事件日"] == ev]; k = d[~d[f"ex_{r}"]]
            # 隨機：同種子、同事件序號；在剩下名單中抽（不排除版本 ＝ 原 f9 隨機；列序同 fund features）
            dk_all = ALL[(ALL["事件日"] == ev)]; dk_all = dk_all[~dk_all[f"ex_{r}"]]
            net = np.where(dk_all["買得到"].to_numpy(), dk_all["淨報酬"].to_numpy(float), np.nan); m = len(net)
            for N in (1, 2, 3):
                rng = np.random.default_rng([SEED, i, N])
                if m == 0:
                    rng.random((NR, 0)); RSall[(r, ev, N)] = np.zeros(NR); continue
                ix = np.argsort(rng.random((NR, m)), axis=1)[:, :min(N, m)]
                v = net[ix]; fin = np.isfinite(v); cnt = fin.sum(axis=1)
                RSall[(r, ev, N)] = np.where(cnt > 0, np.where(fin, v, 0.0).sum(axis=1) / np.maximum(cnt, 1), 0.0)
            ret, nb = pret(k); res[(ev, "C+全買")] = (ret, nb == 0, len(k), "")
            if len(k):
                kk = add_rank(k)
                for sc in ("F8", "F9"):
                    pk = order(kk, sc).head(3); ret, nb = pret(pk)
                    res[(ev, sc)] = (ret, nb == 0, len(k), " ".join(pk["sid"]))
                    EPK.append({"規則": r, "段": seg_of[ev], "事件日": ev, "分數": sc, "C+留下檔數": len(k), "選中": " ".join(pk["sid"]), "報酬": ret,
                                "選中各檔報酬": " ".join(f"{x:.4f}" if b else "買不到" for x, b in zip(pk["淨報酬"], pk["買得到"]))})
            else:
                for sc in ("F8", "F9"):
                    res[(ev, sc)] = (0.0, True, 0, "")
                    EPK.append({"規則": r, "段": seg_of[ev], "事件日": ev, "分數": sc, "C+留下檔數": 0, "選中": "", "報酬": 0.0, "選中各檔報酬": ""})
        for sg, es in segev.items():
            for mth in ("C+全買", "F8", "F9"):
                x = np.array([res[(e, mth)][0] for e in es]); s = FU.stats(x)
                PRT.append({"規則": r, "段": sg, "方法": mth if mth == "C+全買" else f"{mth}前3", "N": "" if mth == "C+全買" else 3, **s,
                            "空手事件數": int(sum(res[(e, mth)][1] for e in es))})
            for N in (1, 2, 3):
                M_ = np.stack([RSall[(r, e, N)] for e in es]); flat = M_.ravel()
                PRT.append({"規則": r, "段": sg, "方法": f"隨機{N}", "N": N, "事件數": len(es), "平均": float(flat.mean()), "中位": float(np.median(flat)),
                            "勝率": float((flat > 0).mean()), "最差": float(M_.min(axis=0).mean()), "最好": float(M_.max(axis=0).mean()),
                            "虧＞10%次數": float((M_ < -0.10).sum(axis=0).mean()), "空手事件數": np.nan})
    PRT = pd.DataFrame(PRT); EPK = pd.DataFrame(EPK)
    # ── 對帳「無排除」──
    mxs = 0.0; nchk = 0
    for _, r in PRT[PRT["規則"] == "無"].iterrows():
        if r["方法"] == "C+全買":
            f = F9S[(F9S["段"] == r["段"]) & (F9S["方法"] == "C+全買")]
        elif r["方法"].startswith("隨機"):
            f = F9S[(F9S["段"] == r["段"]) & (F9S["方法"] == "隨機") & (F9S["N_"] == int(r["N"]))]
        else:
            f = F9S[(F9S["段"] == r["段"]) & (F9S["方法"] == r["方法"][:2]) & (F9S["N_"] == 3)]
        assert len(f) == 1, (r["段"], r["方法"]); f = f.iloc[0]
        for c in ("事件數", "平均", "中位", "勝率", "最差", "虧＞10%次數"):
            mxs = max(mxs, abs(float(r[c]) - float(f[c]))); nchk += 1
    log(f"[對帳] 無排除 C+全買／隨機1-3／F8前3／F9前3 vs f9/summary.csv：{nchk} 格、最大差 {mxs:.2e}"); assert mxs < 1e-5
    mx8 = 0.0
    for sg in ("2015～2021", "2022～"):
        a = PRT[(PRT["規則"] == "無") & (PRT["段"] == sg) & (PRT["方法"] == "F8前3")].iloc[0]
        f = F8S[(F8S["段"] == sg) & (F8S["方法"] == "F8") & (pd.to_numeric(F8S["N"], errors="coerce") == 3)].iloc[0]
        for c in ("平均", "中位", "最差", "虧＞10%次數"):
            mx8 = max(mx8, abs(float(a[c]) - float(f[c])))
    log(f"[對帳] 無排除 F8前3 vs f8/summary.csv（兩段）：最大差 {mx8:.2e}"); assert mx8 < 1e-5
    F9E = pd.read_csv(os.path.join(F9D, "event_picks.csv"), dtype={"選中": str}); F9E = F9E[F9E["N"] == 3].set_index(["事件日", "分數"])
    bad = 0
    for _, r in EPK[EPK["規則"] == "無"].iterrows():
        bad += int(str(F9E.loc[(r["事件日"], r["分數"]), "選中"]).split() != r["選中"].split())
    log(f"[對帳] 無排除 F8／F9 前 3 選中 vs f9/event_picks.csv：不同 {bad}/36"); assert bad == 0
    # 排除後選中改變事件數
    CHG = []
    for r in RULES[1:]:
        for sc in ("F8", "F9"):
            a = EPK[(EPK["規則"] == "無") & (EPK["分數"] == sc)].set_index("事件日")["選中"]
            b = EPK[(EPK["規則"] == r) & (EPK["分數"] == sc)].set_index("事件日")["選中"]
            chg = [e for e in evs if a[e] != b[e]]
            CHG.append({"規則": r, "分數": sc, "前3有變事件數": len(chg), "原前3被排檔數合計":
                        int(sum(len([s for s in a[e].split() if bool(CP[(CP['事件日'] == e) & (CP['sid'] == s)][f'ex_{r}'].iloc[0])]) for e in evs))})
    CHG = pd.DataFrame(CHG); log("[F8／F9 前 3 因排除而改變（18 事件）]\n" + CHG.to_string(index=False))
    PRT.to_csv(os.path.join(OUT, "portfolio.csv"), index=False, float_format="%.6g", encoding="utf-8")
    EPK.to_csv(os.path.join(OUT, "event_picks.csv"), index=False, float_format="%.6g", encoding="utf-8")
    pc = ["規則", "段", "方法", "事件數", "平均", "中位", "勝率", "最差", "虧＞10%次數", "空手事件數"]
    log("[組合層]\n" + PRT[pc].to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    FW = forward()
    S = {"程式": "backtest/researchMktDrop_excl.py", "時間（台北）": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M"), "讀法": __doc__, "註": NOTES,
         "門檻": {"X1": X_R60_HI, "X2": X_R60_MID, "X3": X_D52, "X5": X_I20},
         "stock": STK.replace({np.nan: None}).to_dict("records"), "portfolio": PRT.replace({np.nan: None}).to_dict("records"),
         "前3改變": CHG.to_dict("records"), "forward_20261015": FW, "耗時秒": round(time.time() - T0, 1)}
    with open(os.path.join(OUT, "MktDrop_excl.json"), "w", encoding="utf-8") as f:
        json.dump(S, f, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    with open(os.path.join(OUT, "run.log"), "w", encoding="utf-8") as f:
        f.write("\n".join(LOG) + "\n")


def forward():
    W = pd.read_csv(os.path.join(FD, "forward_20261015_features.csv"), dtype={"sid": str})
    QW = pd.read_csv(os.path.join(QD, "forward_20261015.csv"), dtype={"代號": str})
    assert len(W) == 75 and len(QW) == 75
    W = W.merge(QW[["代號", "Q"]].rename(columns={"代號": "sid"}), on="sid", how="left"); assert W["Q"].notna().all()
    FL = flags(W)
    for r in RULES:
        W[f"ex_{r}"] = FL[r]
    log(f"[10/15] C+ 75 檔；缺值 tc_r60 {int(W['tc_r60'].isna().sum())}、tc_d52 {int(W['tc_d52'].isna().sum())}、ch_i20 {int(W['ch_i20'].isna().sum())}")
    F8W = pd.read_csv(os.path.join(F8D, "forward_20261015.csv"), dtype={"代號": str})
    F9W = pd.read_csv(os.path.join(F9D, "forward_20261015.csv"), dtype={"代號": str})
    TOP = []; out = {}
    base = add_rank(W)
    for sc, ref in (("F8", F8W), ("F9", F9W)):
        t = order(base, sc)["sid"].tolist()[:3]
        assert t == ref["代號"].tolist()[:3], (sc, t, ref["代號"].tolist()[:3])
    log("[對帳] 10/15 無排除 F8／F9 前 3 ＝ f8／f9 forward 前 3")
    nm = W.set_index("sid")["名稱"].to_dict()
    for r in RULES:
        k = add_rank(W[~W[f"ex_{r}"]])
        row = {"規則": r, "名稱": RNAME[r], "排除檔數": int(W[f"ex_{r}"].sum()), "2221被排": bool(W.loc[W["sid"] == "2221", f"ex_{r}"].iloc[0])}
        for sc in ("F8", "F9"):
            t = order(k, sc)["sid"].tolist()[:3]
            row[f"{sc}前3"] = " ".join(f"{s}{nm[s]}" for s in t)
        TOP.append(row)
    TOP = pd.DataFrame(TOP)
    TOP.to_csv(os.path.join(OUT, "forward_top3.csv"), index=False, encoding="utf-8")
    log("[10/15 各規則排除檔數與 F8／F9 前 3]\n" + TOP.to_string(index=False))
    ex = W[W[[f"ex_{r}" for r in RULES[1:]]].any(axis=1)].copy()
    ex["F8名次（無排除）"] = [order(base, "F8")["sid"].tolist().index(s) + 1 for s in ex["sid"]]
    ex["F9名次（無排除）"] = [order(base, "F9")["sid"].tolist().index(s) + 1 for s in ex["sid"]]
    cols = ["sid", "名稱", "tc_r60", "tc_d52", "ch_i20", "ch_i5", "ret1", "F8名次（無排除）", "F9名次（無排除）"] + [f"ex_{r}" for r in RULES[1:]]
    ex = ex[cols].sort_values("F9名次（無排除）").rename(columns={"sid": "代號", "tc_r60": "前60日漲幅", "tc_d52": "大跌前距52週高", "ch_i20": "20日法人÷量",
                                                              "ch_i5": "5日法人÷量", "ret1": "當日報酬", **{f"ex_{r}": r for r in RULES[1:]}})
    ex.to_csv(os.path.join(OUT, "forward_20261015.csv"), index=False, float_format="%.6g", encoding="utf-8")
    log("[10/15 被任一規則排掉的股（依無排除 F9 名次）]\n" + ex.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    return {"top3": TOP.to_dict("records"), "被排": ex.replace({np.nan: None}).to_dict("records")}


if __name__ == "__main__":
    main()
