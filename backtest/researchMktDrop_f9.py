# -*- coding: utf-8 -*-
"""大盤大跌後「只能買 1～3 檔」——F9 ＝ F6 名次＋F7 名次＋Q 名次（三者等權相加），只在該事件 C+ 內挑（描述性初測；⛔ 不計 N、⛔ 不判定、⛔ 不是買賣建議）
回測線計算子代理，2026-10-17。使用者：「三個綜合起來呢？」

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMktDrop_f9

═══ 讀法（寫死於第一次跑之前；⚠ F9 是看過 fund／f8／quality 結果之後才提的 ⇒ 事後設計）═══
 Z0 ⛔ 不重算 F6／F7／Q：F6、F7、F7A、淨報酬、買得到只讀 resultsMktDrop/fund/features.csv；Q 只讀 resultsMktDrop/quality/features.csv（18 事件 1007 列）；
    兩檔以（事件日, sid）合併，程式內對帳兩檔 F6／F7／淨報酬一致；缺值處理沿用各自原檔（F6／F7 原檔無缺；Q 子項缺 ⇒ 該子項 0 分、分母 6，已含在 Q 內）
 Z1 只比 2015 年以後 18 事件（2015～2021 7、2022～ 11）；2006～2014 段標缺（Q 沒有早年財報）
 Z2 F9 ＝ 同一事件 C+ 內 F6、F7、Q 各自 rank(pct, 同值取平均) × 100 相加（0～300；三者方向都是高分＝好）；同分 ⇒ F7 高者 ⇒ 再同 ⇒ 代號（同 F8 規則）
    F9 四捨五入到 1e-6 再排序（去浮點雜訊，讓真同分走 F7 決勝）；Q 讀自 quality/features.csv（％.6g 存檔）
 Z3 挑 N ＝ 只在該事件 C+ 內按 F9 降冪前 N 檔；報酬 ＝ 選中中買得到者淨報酬等權；全買不到 ⇒ 0（同 pick／fund／f8／quality）
 Z4 對照：0050、00631L、C+ 全買 ＝ v1／yl event_rows（同 quality）；隨機 ＝ 同 pick／fund／quality（同種子、同列序、事件序號照 28 事件）；
    F6、F7、F8、Q 選中 ＝ 讀 quality/event_picks.csv，報酬由 features 重算；全部對照的彙總數字對帳 quality/summary.csv（另 F8 對帳 f8/summary.csv、F6／F7 對帳 fund/summary.csv）
 Z5 報：2015～2021、2022～、2015～（18 事件）三段；平均、中位、勝率、最差、虧 ＞10% 次數、隨機段平均分布中的位置（百分位 ＝ 隨機段平均 ＜ 分數段平均 的比例）
 Z6 F9 五分位：借 quality.quintiles（每事件 C+ 依 F9 排序切 5 組、組內買得到者等權、段內事件等權、事件群集 bootstrap 2000 次 CI〔種子同 Q〕、Q5−Q1、每事件 Spearman）
 Z7 集中度：18 事件中拿掉「該方法報酬最高的那一個事件」（單一最大貢獻）後的 17 事件平均；F9 另報拿掉同一事件後在隨機中的位置
 Z8 10/15 前瞻：fund/forward_20261015_features.csv（F6、F7）＋ quality/forward_20261015.csv（Q）的 C+ 75 檔；F9 前 3（附前 10）與 F8 前 3 比較
 Z9 必附：F9 是第 21 種分數（fund 18 ＋ F8 ＋ Q ＋ F9）× 3 N × 段 ⇒ 多重比較；事後設計；只有 18 事件；百分位只是位置、不是檢定；描述性、不計 N、不判定
輸出 backtest/resultsMktDrop/f9/：MktDrop_f9.json、summary.csv、segment.csv、concentration.csv、quintile.csv、quintile_mono.csv、event_picks.csv、
     features.csv、forward_20261015.csv、run.log
"""
from __future__ import annotations

import json
import os
import time

import numpy as np
import pandas as pd

from backtest import researchMktDrop_fund as FU
from backtest import researchMktDrop_quality as QL

REPO = os.path.expanduser("~/tw-p17")
FD = os.path.join(REPO, "backtest/resultsMktDrop/fund")
F8D = os.path.join(REPO, "backtest/resultsMktDrop/f8")
QD = os.path.join(REPO, "backtest/resultsMktDrop/quality")
OUT = os.path.join(REPO, "backtest/resultsMktDrop/f9")
NR, SEED = FU.NR, FU.SEED
SEGS = QL.SEGS  # ["2015～2021", "2022～", "2015～（18事件）"]
CMP = ["F9", "F6", "F7", "F8", "Q"]
CMPNAME = {"F9": "⭐F9（F6 名次＋F7 名次＋Q 名次，C+ 內）", "F6": FU.SCNAME["F6"], "F7": FU.SCNAME["F7"], "F8": "F8（F6 名次＋F7 名次）",
           "Q": "Q 純優質（6 子項 C+ 內百分位等權）"}
NOTES = ["描述性初測：⛔ 不計 N、⛔ 不判定、⛔ 不是買賣建議；挑檔候選一律只限該事件 C+（大跌日跌最多一成 ∧ 營收年增 ＞ 0）",
         "⚠ 多重比較：fund 18 種分數 ＋ F8 ＋ Q ＋ F9 ⇒ F9 是第 21 種分數，× 3 N × 段；分數越多、碰巧好看的越多；百分位只是位置、不是檢定",
         "⚠ 事後設計：F9 是看過 fund（F6、F7）、f8、quality（Q）結果之後才提的；F6、Q 本身也是事後設計 ⇒ 任何「看起來較好／較差」只是待驗線索",
         "⚠ 只有 18 個事件（2015～2021 7、2022～ 11）；早年 10 事件沒有 Q ⇒ 標缺；差異多半是運氣",
         "F9 用名次相加（不是原始分數相加）：F6 是 C+ 內百分位平均、F7 是大母體百分位加權、Q 是 C+ 內百分位平均，尺度不同 ⇒ 一律先轉成 C+ 內名次百分位",
         "Q 缺值子項 0 分（沿用 quality）⇒ 金融保險、上市未滿 2 年者 Q 名次偏低，F9 也跟著偏低",
         "主出場「加權收盤收復事件前一日收盤 ⇒ 隔天開盤賣」不設天數；成本 0.585% 來回；未含滑價"]
LOG = []


def log(s):
    print(s, flush=True); LOG.append(s)


def add_f9(d, key):
    g = d.groupby(key)
    d["r6"] = g["F6"].rank(pct=True, method="average") * 100
    d["r7"] = g["F7"].rank(pct=True, method="average") * 100
    d["rQ"] = g["Q"].rank(pct=True, method="average") * 100
    d["F8"] = d["r6"] + d["r7"]
    # 三個名次分母都是該事件 C+ 檔數 n（F6／F7／Q 都無缺）⇒ F9 只取 100／(2n) 的倍數；四捨五入到 1e-6 去掉浮點雜訊，真同分才走 F7 決勝
    d["F9"] = (d["r6"] + d["r7"] + d["rQ"]).round(6)
    return d


def order(d, sc="F9"):
    d = d.sort_values("sid", kind="mergesort")
    return d.sort_values([sc, "F7"], ascending=[False, False], kind="mergesort")


def load_cp():
    """⇒ ALL（28 事件 fund features）、CP（18 事件，含 Q、F9）"""
    ALL = pd.read_csv(os.path.join(FD, "features.csv"), dtype={"sid": str})
    ALL["買得到"] = ALL["買得到"].astype(str).str.lower().eq("true")
    assert ALL["事件日"].nunique() == 28 and len(ALL) == 1402
    QF = pd.read_csv(os.path.join(QD, "features.csv"), dtype={"sid": str})
    assert len(QF) == 1007 and QF["事件日"].nunique() == 18 and QF["Q"].notna().all()
    CP = ALL.merge(QF[["事件日", "sid", "Q", "q_nmiss", "F6", "F7", "淨報酬"]].rename(columns={"F6": "F6_q", "F7": "F7_q", "淨報酬": "淨報酬_q"}),
                   on=["事件日", "sid"], how="inner")
    assert len(CP) == 1007, len(CP)
    d6 = float((CP["F6"] - CP["F6_q"]).abs().max()); d7 = float((CP["F7"] - CP["F7_q"]).abs().max())
    dr = float((CP["淨報酬"] - CP["淨報酬_q"]).abs().max(skipna=True))
    assert d6 < 1e-5 and d7 < 1e-3 and dr < 1e-5, (d6, d7, dr)
    CP = CP.drop(columns=["F6_q", "F7_q", "淨報酬_q"])
    CP = add_f9(CP, "事件日")
    return ALL, CP, (d6, d7, dr)


def main():
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    pd.set_option("display.width", 260); pd.set_option("display.max_rows", 900); pd.set_option("display.max_columns", 40)
    ALL, CP, dd = load_cp()
    evs_all = sorted(ALL["事件日"].unique()); seg_of = ALL.drop_duplicates("事件日").set_index("事件日")["段"].to_dict()
    evs = sorted(CP["事件日"].unique()); assert len(evs) == 18 and all(seg_of[e] != "2006～2014" for e in evs)
    segev = {"2015～2021": [e for e in evs if seg_of[e] == "2015～2021"], "2022～": [e for e in evs if seg_of[e] == "2022～"], "2015～（18事件）": evs}
    log(f"[讀檔] fund/features.csv 1402 列 28 事件 ＋ quality/features.csv Q ⇒ 2015 起 {len(CP)} 列 {len(evs)} 事件；"
        f"兩檔 F6 最大差 {dd[0]:.1e}、F7 {dd[1]:.1e}、淨報酬 {dd[2]:.1e}（％.6g 存檔誤差）")
    rel = {}
    for a, b in (("F6", "F7"), ("F6", "Q"), ("F7", "Q"), ("F9", "F8"), ("F9", "Q")):
        rel[f"{a} vs {b}"] = float(np.mean([g[a].rank().corr(g[b].rank()) for _, g in CP.groupby("事件日")]))
    log("[事件內 Spearman 平均（18 事件）] " + "、".join(f"{k} {v:.2f}" for k, v in rel.items()))
    # ── 對照：0050、00631L、C+ 全買（同 quality）──
    V = pd.read_csv(FU.V1ER); V = V[(V["出場"] == "主") & (V["定義"] == "q2")]
    Y = pd.read_csv(FU.YLER); Y = Y[Y["r"].isna() | (Y["r"].astype(str) == "") | (Y["r"].astype(str) == "nan")]
    ref = {}
    for ev in evs:
        r = {}
        for cd in ("A", "B"):
            q = V[(V["世界"] == "主") & (V["候選"] == cd) & (V["日期"] == ev)]; q = q[q["進場"].astype(str).str.lower() == "true"]
            r[cd] = float(q["報酬"].iloc[0]) if len(q) else np.nan
        q = Y[(Y["世界"] == "主") & (Y["候選"] == "C+") & (Y["日期"] == ev)]; assert len(q) == 1
        r["C+全買"] = float(q["報酬"].iloc[0])
        mine = float(CP[(CP["事件日"] == ev) & CP["買得到"]]["淨報酬"].mean()); assert abs(mine - r["C+全買"]) < 1e-6
        ref[ev] = r
    log("[對帳] C+ 全買（features 重算）＝ yl event_rows：18/18 差 ＜ 1e-6")
    # ── 挑檔 ──
    nret = CP.set_index(["事件日", "sid"])

    def ret_of(ev, ids):
        rows = nret.loc[[(ev, s) for s in ids]]; b = rows[rows["買得到"]]
        return (float(b["淨報酬"].mean()) if len(b) else 0.0), len(b)

    EP = []; picks = {}
    for ev in evs:
        d = CP[CP["事件日"] == ev]; o = order(d, "F9")
        for N in (1, 2, 3):
            pk = o.head(N); ret, nb = ret_of(ev, list(pk["sid"]))
            picks[(ev, "F9", N)] = list(pk["sid"])
            EP.append({"段": seg_of[ev], "事件日": ev, "分數": "F9", "N": N, "C+檔數": len(d), "選中": " ".join(pk["sid"]),
                       "選中F9": " ".join(f"{x:.1f}" for x in pk["F9"]), "選中F6名次": " ".join(f"{x:.1f}" for x in pk["r6"]),
                       "選中F7名次": " ".join(f"{x:.1f}" for x in pk["r7"]), "選中Q名次": " ".join(f"{x:.1f}" for x in pk["rQ"]),
                       "買到檔數": nb, "空手": nb == 0, "報酬": ret,
                       "選中各檔報酬": " ".join(f"{x:.4f}" if b else "買不到" for x, b in zip(pk["淨報酬"], pk["買得到"]))})
    QE = pd.read_csv(os.path.join(QD, "event_picks.csv"), dtype={"選中": str})
    for _, r in QE.iterrows():
        ids = str(r["選中"]).split(); ret, nb = ret_of(r["事件日"], ids)
        assert abs(ret - float(r["報酬"])) < 1e-5, (r["事件日"], r["分數"], r["N"], ret, r["報酬"])
        picks[(r["事件日"], r["分數"], int(r["N"]))] = ids
        EP.append({"段": r["段"], "事件日": r["事件日"], "分數": r["分數"], "N": int(r["N"]), "C+檔數": int(r["C+檔數"]), "選中": " ".join(ids),
                   "買到檔數": nb, "空手": nb == 0, "報酬": ret, "選中各檔報酬": r["選中各檔報酬"]})
    EP = pd.DataFrame(EP)
    assert len(EP) == 18 * 3 * 5, len(EP)
    log("[對帳] F6／F7／F8／Q 選中讀 quality/event_picks.csv，報酬由 features 重算：216/216 差 ＜ 1e-5")
    # 交叉：F8、Q 由本程式名次重挑 ＝ 既有選中
    bad8 = badq = 0
    for ev in evs:
        d = CP[CP["事件日"] == ev]; o8 = order(d, "F8"); oq = QL.order(d)
        for N in (1, 2, 3):
            bad8 += int(list(o8.head(N)["sid"]) != picks[(ev, "F8", N)]); badq += int(list(oq.head(N)["sid"]) != picks[(ev, "Q", N)])
    log(f"[對帳] 本程式名次重挑 F8 vs 既有選中不同 {bad8}/54；Q（quality.order）不同 {badq}/54"); assert bad8 == 0 and badq == 0
    OV = []
    for N in (1, 2, 3):
        for oth in ("F6", "F7", "F8", "Q"):
            ov = [len(set(picks[(e, "F9", N)]) & set(picks[(e, oth, N)])) for e in evs]
            OV.append({"N": N, "比較": oth, "完全相同事件數（18）": int(sum(o == N for o in ov)), "平均重疊檔數": float(np.mean(ov)),
                       "至少重疊1檔事件數": int(sum(o > 0 for o in ov))})
    OV = pd.DataFrame(OV); log("[F9 選中與 F6／F7／F8／Q 重疊]\n" + OV.to_string(index=False, float_format=lambda v: f"{v:.2f}"))
    # ── 隨機（同 pick／fund／quality：同種子、同列序、事件序號照 28 事件）──
    RS = {}
    for i, ev in enumerate(evs_all):
        if ev not in evs:
            continue
        d = ALL[ALL["事件日"] == ev]
        net = np.where(d["買得到"].to_numpy(), d["淨報酬"].to_numpy(float), np.nan); m = len(net)
        for N in (1, 2, 3):
            rng = np.random.default_rng([SEED, i, N])
            ix = np.argsort(rng.random((NR, m)), axis=1)[:, :N]
            v = net[ix]; fin = np.isfinite(v); cnt = fin.sum(axis=1)
            RS[(ev, N)] = np.where(cnt > 0, np.where(fin, v, 0.0).sum(axis=1) / np.maximum(cnt, 1), 0.0)
    # ── 彙總 ──
    SUM = [{"段": "2006～2014", "方法": "F9", "名稱": CMPNAME["F9"], "N": "", "事件數": 0, "備註": "缺（Q 沒有早年財報；10 事件都在 2011-08 以前）"}]
    for sg, es in segev.items():
        for cd, nm in (("A", "0050"), ("B", "00631L（正2）"), ("C+全買", "C+ 全部等權")):
            x = np.array([ref[e][cd] for e in es]); x = x[np.isfinite(x)]
            SUM.append({"段": sg, "方法": cd, "名稱": nm, "N": "", **FU.stats(x)})
        for N in (1, 2, 3):
            M_ = np.stack([RS[(e, N)] for e in es]); flat = M_.ravel(); sa = M_.mean(axis=0)
            SUM.append({"段": sg, "方法": "隨機", "名稱": f"C+ 隨機挑 {N} 檔（{NR} 次）", "N": N, "事件數": len(es), "平均": float(flat.mean()),
                        "中位": float(np.median(flat)), "勝率": float((flat > 0).mean()), "最差": float(M_.min(axis=0).mean()),
                        "虧＞10%次數": float((M_ < -0.10).sum(axis=0).mean()),
                        "隨機段平均P10": float(np.quantile(sa, .1)), "隨機段平均P50": float(np.quantile(sa, .5)), "隨機段平均P90": float(np.quantile(sa, .9)),
                        "備註": "最差、虧＞10%次數 ＝ 每輪段內值的平均"})
            for sc in CMP:
                q = EP[(EP["分數"] == sc) & (EP["N"] == N)].set_index("事件日").loc[es]
                x = q["報酬"].to_numpy(float); s = FU.stats(x); cpa = np.array([ref[e]["C+全買"] for e in es])
                SUM.append({"段": sg, "方法": sc, "名稱": CMPNAME[sc], "N": N, **s, "空手事件數": int(q["空手"].sum()),
                            "隨機段平均P10": float(np.quantile(sa, .1)), "隨機段平均P50": float(np.quantile(sa, .5)), "隨機段平均P90": float(np.quantile(sa, .9)),
                            "隨機中位置（百分位）": float((sa < s["平均"]).mean()), "p（隨機≥分數）": float((sa >= s["平均"]).mean()),
                            "勝過C+全買事件數": int((x > cpa).sum()),
                            "勝過A事件數": int(sum(1 for e, v in zip(es, x) if np.isfinite(ref[e]["A"]) and v > ref[e]["A"])),
                            "勝過A可比事件數": int(sum(1 for e in es if np.isfinite(ref[e]["A"])))})
    SUM = pd.DataFrame(SUM)
    # 對帳：全部對照 vs quality/summary.csv（同欄位）
    QS = pd.read_csv(os.path.join(QD, "summary.csv")); QS["N_"] = pd.to_numeric(QS["N"], errors="coerce").fillna(0).astype(int)
    numc = ["事件數", "平均", "中位", "勝率", "最差", "最好", "虧＞10%次數", "隨機段平均P10", "隨機段平均P50", "隨機段平均P90", "空手事件數",
            "隨機中位置（百分位）", "p（隨機≥分數）", "勝過C+全買事件數", "勝過A事件數", "勝過A可比事件數"]
    mxq = 0.0; nchk = 0
    for _, r in SUM[(SUM["方法"] != "F9") & SUM["段"].isin(SEGS)].iterrows():
        n_ = int(r["N"]) if str(r["N"]) not in ("", "nan") else 0
        f = QS[(QS["段"] == r["段"]) & (QS["方法"] == r["方法"]) & (QS["N_"] == n_)]; assert len(f) == 1, (r["段"], r["方法"], n_)
        f = f.iloc[0]
        for c in numc:
            a, b = r.get(c), f.get(c)
            if pd.isna(a) and pd.isna(b):
                continue
            mxq = max(mxq, abs(float(a) - float(b)) / max(1.0, abs(float(b)))); nchk += 1
    log(f"[對帳] 0050／正2／C+全買／隨機／F6／F7／F8／Q 彙總 vs quality/summary.csv：{nchk} 格、最大相對差 {mxq:.2e}"); assert mxq < 1e-5
    F8S = pd.read_csv(os.path.join(F8D, "summary.csv")); FS = pd.read_csv(os.path.join(FD, "summary.csv")); mx8 = 0.0
    for _, r in SUM[SUM["方法"].isin(["F6", "F7", "F8"]) & SUM["段"].isin(["2015～2021", "2022～"])].iterrows():
        src = F8S if r["方法"] == "F8" else FS
        f = src[(src["段"] == r["段"]) & (src["方法"] == r["方法"]) & (pd.to_numeric(src["N"], errors="coerce") == r["N"])].iloc[0]
        mx8 = max(mx8, abs(float(f["平均"]) - r["平均"]), abs(float(f["隨機中位置（百分位）"]) - r["隨機中位置（百分位）"]))
    log(f"[對帳] F8 vs f8/summary.csv、F6／F7 vs fund/summary.csv（兩段平均與隨機百分位）最大差 {mx8:.2e}"); assert mx8 < 1e-5
    SUM.to_csv(os.path.join(OUT, "summary.csv"), index=False, float_format="%.6g", encoding="utf-8")
    EP.to_csv(os.path.join(OUT, "event_picks.csv"), index=False, float_format="%.6g", encoding="utf-8")
    cols = ["段", "方法", "N", "事件數", "平均", "中位", "勝率", "最差", "虧＞10%次數", "隨機中位置（百分位）", "勝過C+全買事件數", "勝過A事件數"]
    log("[彙總]\n" + SUM[SUM["段"].isin(SEGS)][cols].to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    # ── 分段精簡 ──
    SG = []
    for sg in SEGS:
        for N in (1, 2, 3):
            row = {"段": sg, "N": N}
            for sc in CMP + ["隨機"]:
                r = SUM[(SUM["段"] == sg) & (SUM["方法"] == sc) & (SUM["N"].astype(str) == str(N))].iloc[0]
                row[f"{sc}平均"] = r["平均"]
                if sc != "隨機":
                    row[f"{sc}百分位"] = r["隨機中位置（百分位）"]
            for cd in ("A", "B", "C+全買"):
                row[f"{cd}平均"] = SUM[(SUM["段"] == sg) & (SUM["方法"] == cd)].iloc[0]["平均"]
            SG.append(row)
    SG = pd.DataFrame(SG); SG.to_csv(os.path.join(OUT, "segment.csv"), index=False, float_format="%.6g", encoding="utf-8")
    log("[分段]\n" + SG.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    # ── 集中度：拿掉單一最大貢獻事件 ──
    CC = []
    for N in (1, 2, 3):
        M_ = np.stack([RS[(e, N)] for e in evs])
        for sc in CMP:
            q = EP[(EP["分數"] == sc) & (EP["N"] == N)].set_index("事件日").loc[evs]; x = q["報酬"].to_numpy(float)
            k = int(np.argmax(x)); keep = np.arange(len(evs)) != k
            sa = M_[keep].mean(axis=0)
            CC.append({"N": N, "方法": sc, "18事件平均": float(x.mean()), "最大貢獻事件": evs[k], "該事件報酬": float(x[k]),
                       "拿掉後17事件平均": float(x[keep].mean()), "拿掉後中位": float(np.median(x[keep])),
                       "拿掉同事件後隨機平均": float(M_[keep].mean()), "拿掉後隨機中位置（百分位）": float((sa < x[keep].mean()).mean())})
        for cd in ("A", "B", "C+全買"):
            if N > 1:
                continue
            x = np.array([ref[e][cd] for e in evs]); ok = np.isfinite(x); xe = np.where(ok, x, -np.inf); k = int(np.argmax(xe)); keep = ok & (np.arange(len(evs)) != k)
            CC.append({"N": "", "方法": cd, "18事件平均": float(x[ok].mean()), "最大貢獻事件": evs[k], "該事件報酬": float(x[k]),
                       "拿掉後17事件平均": float(x[keep].mean()), "拿掉後中位": float(np.median(x[keep]))})
    CC = pd.DataFrame(CC); CC.to_csv(os.path.join(OUT, "concentration.csv"), index=False, float_format="%.6g", encoding="utf-8")
    log("[集中度：拿掉單一最大貢獻事件]\n" + CC.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    # ── 五分位（借 quality.quintiles：把 F9 放進 Q 欄、排序換成 F9 規則）──
    QX_ = CP.copy(); QX_["Q"] = QX_["F9"]
    _qo = QL.order
    QL.order = lambda d: order(d, "Q")
    try:
        QT, QX = QL.quintiles(QX_, segev)
    finally:
        QL.order = _qo
    QT.to_csv(os.path.join(OUT, "quintile.csv"), index=False, float_format="%.6g", encoding="utf-8")
    QX.to_csv(os.path.join(OUT, "quintile_mono.csv"), index=False, float_format="%.6g", encoding="utf-8")
    log("[F9 五分位]\n" + QT.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    log("[F9 單調／Q5−Q1]\n" + QX.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    keep = ["段", "事件日", "sid", "買得到", "淨報酬", "F6", "F7", "F7A", "Q", "q_nmiss", "r6", "r7", "rQ", "F8", "F9"]
    CP[keep].to_csv(os.path.join(OUT, "features.csv"), index=False, float_format="%.6g", encoding="utf-8")
    FW = forward()
    S = {"程式": "backtest/researchMktDrop_f9.py", "時間（台北）": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M"), "讀法": __doc__, "註": NOTES,
         "名次相關": rel, "重疊": OV.to_dict("records"), "summary": SUM.replace({np.nan: None}).to_dict("records"),
         "segment": SG.to_dict("records"), "concentration": CC.replace({np.nan: None}).to_dict("records"),
         "quintile": QT.replace({np.nan: None}).to_dict("records"), "單調": QX.replace({np.nan: None}).to_dict("records"),
         "forward_20261015": FW, "耗時秒": round(time.time() - T0, 1)}
    with open(os.path.join(OUT, "MktDrop_f9.json"), "w", encoding="utf-8") as f:
        json.dump(S, f, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    with open(os.path.join(OUT, "run.log"), "w", encoding="utf-8") as f:
        f.write("\n".join(LOG) + "\n")


def forward():
    W = pd.read_csv(os.path.join(FD, "forward_20261015_features.csv"), dtype={"sid": str})
    QW = pd.read_csv(os.path.join(QD, "forward_20261015.csv"), dtype={"代號": str})
    F8W = pd.read_csv(os.path.join(F8D, "forward_20261015.csv"), dtype={"代號": str})
    assert len(W) == 75 and len(QW) == 75 and W["F6"].notna().all() and W["F7"].notna().all() and QW["Q"].notna().all()
    W = W.merge(QW[["代號", "Q", "Q名次", "缺值子項數"]].rename(columns={"代號": "sid"}), on="sid", how="left"); assert W["Q"].notna().all()
    W = add_f9(W, "事件日")
    o = order(W, "F9").reset_index(drop=True); o["F9名次"] = np.arange(1, len(o) + 1)
    rk = {}
    for sc in ("F6", "F7"):
        lst = FU.order(W, sc)["sid"].tolist(); rk[sc] = {s: lst.index(s) + 1 for s in lst}
    lst8 = order(W, "F8")["sid"].tolist(); assert lst8[:10] == F8W["代號"].tolist()[:10], "F8 前 10 與 f8/forward 不符"
    rk["F8"] = {s: lst8.index(s) + 1 for s in lst8}
    for sc in ("F6", "F7", "F8"):
        o[f"{sc}名次"] = [rk[sc][s] for s in o["sid"]]
    cols = ["F9名次", "sid", "名稱", "F9", "r6", "r7", "rQ", "F6名次", "F7名次", "Q名次", "F8名次", "F6", "F7", "Q", "缺值子項數", "ret1"]
    fw = o[cols].rename(columns={"sid": "代號", "r6": "F6百分位名次", "r7": "F7百分位名次", "rQ": "Q百分位名次", "ret1": "當日報酬", "缺值子項數": "Q缺值子項數"})
    fw.to_csv(os.path.join(OUT, "forward_20261015.csv"), index=False, float_format="%.6g", encoding="utf-8")
    log("[10/15 F9 前 10]\n" + fw.head(10).to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    f8top = F8W["代號"].tolist()[:3]
    cmp_ = [{"代號": s, "名稱": o.loc[o["sid"] == s, "名稱"].iloc[0], "F8名次": rk["F8"][s], "F9名次": int(o.loc[o["sid"] == s, "F9名次"].iloc[0]),
             "Q名次": int(o.loc[o["sid"] == s, "Q名次"].iloc[0])} for s in f8top]
    log(f"[10/15 F8 前 3 在 F9 的名次] {cmp_}")
    return {"前10": fw.head(10).replace({np.nan: None}).to_dict("records"), "F8前3": cmp_}


if __name__ == "__main__":
    main()
