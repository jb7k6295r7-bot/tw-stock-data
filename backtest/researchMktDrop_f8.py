# -*- coding: utf-8 -*-
"""大盤大跌後「只能買 1～3 檔」——F8 ＝ 回測線 F6 與情報 F7 的【名次相加】，只在該事件 C+ 內挑（描述性初測；⛔ 不計 N、⛔ 不判定、⛔ 不是買賣建議）
回測線計算子代理，2026-10-17。使用者：「那你跟他的分數相加來挑呢？」

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMktDrop_f8

═══ 讀法（寫死於第一次跑之前）═══
 V0 ⛔ 不重算 F6／F7：逐檔分數只讀 resultsMktDrop/fund/features.csv（28 事件 C+ 1402 列）與 forward_20261015_features.csv（10/15 C+ 75 檔）；
    逐筆淨報酬、買得到同 features.csv（＝ deep/c_rows.csv 主出場、成本 0.585%）
 V1 F8 ＝ 同一事件 C+ 內 F6 名次百分位 ＋ F7 名次百分位（各自 rank(pct, 同值取平均) × 100，範圍 0～200）；同分 ⇒ F7 高者 ⇒ 再同 ⇒ 代號
 V2 挑 N ＝ 只在該事件 C+ 內按 F8 降冪前 N 檔；報酬 ＝ 選中中買得到者淨報酬等權；全買不到 ⇒ 0（同 pick／fund）
 V3 對照：A 0050、B 00631L（正2）、C+ 全買 ＝ 同 fund（v1／yl event_rows）；隨機 ＝ 同 pick／fund（同種子、同列序，程式內對帳 pick/random.csv 與 fund/summary.csv）；
    F6、F7 挑 N ＝ 由 features.csv 依 fund 同一排序重挑，程式內對帳 fund/event_picks.csv
 V4 報：平均、中位、勝率、最差、虧 ＞10% 次數、隨機段平均分布中的位置（百分位 ＝ 隨機段平均 ＜ 分數段平均 的比例）；三段＋全部
 V5 F8 五分位：同 fund U5（每事件 C+ 依 F8 排序切 5 組、組內買得到者等權、段內事件等權、事件群集 bootstrap 2000 次 CI、Q5−Q1、每事件 Spearman；bootstrap 種子同 fund F6）
 V6 10/15 前瞻：C+ 75 檔 F8 前 3 名（附前 10）
 V7 必附：再多一個分數 ⇒ 多重比較更大；F6 是看過結果後設計的；差異多半是運氣；28 事件；描述性、不計 N、不判定
輸出 backtest/resultsMktDrop/f8/：MktDrop_f8.json、summary.csv、quintile.csv、quintile_mono.csv、event_picks.csv、forward_20261015.csv、run.log
"""
from __future__ import annotations

import json
import os
import time

import numpy as np
import pandas as pd

from backtest import researchMktDrop_fund as FU

FU_ORDER = FU.order  # 原排序（monkeypatch 前保存）

REPO = os.path.expanduser("~/tw-p17")
FD = os.path.join(REPO, "backtest/resultsMktDrop/fund")
OUT = os.path.join(REPO, "backtest/resultsMktDrop/f8")
SEGS = FU.SEGS
NR, SEED = FU.NR, FU.SEED
SCS = ["F8", "F6", "F7"]
SCNAME = {"F8": "⭐F8（F6 名次＋F7 名次，C+ 內）", "F6": FU.SCNAME["F6"], "F7": FU.SCNAME["F7"]}
NOTES = ["描述性初測：⛔ 不計 N、⛔ 不判定、⛔ 不是買賣建議；挑檔候選一律只限該事件 C+",
         "⚠ 再多一個分數 ⇒ 多重比較更大：fund 已有 18 種分數 × 3 N × 3 段，F8 是第 19 種；分數越多、碰巧好看的越多",
         "⚠ F6 是看過 pick 結果之後才設計的（F7 是情報線未看結果先寄、凍結）⇒ F8 一半來自事後設計的分數，不能當成事前規則",
         "⚠ 只有 28 個事件（早年 10、2015～2021 7、2022～ 11）；差異多半是運氣；百分位只是位置、不是檢定",
         "早年（2006～2014）F6 只有營收＋線型、F7 的 B、C、D ＝ 50 ⇒ 早年 F8 實際上是營收＋線型",
         "F8 用名次相加（不是原始分數相加）：F6 是 C+ 內百分位平均（0～1）、F7 是大母體百分位加權（0～100），尺度不同",
         "主出場「加權收盤收復事件前一日收盤 ⇒ 隔天開盤賣」不設天數；成本 0.585% 來回；未含滑價；00631L 2014-10 才上市 ⇒ 早年沒有 B"]
LOG = []


def log(s):
    print(s, flush=True); LOG.append(s)


def add_f8(d, key):
    d["r6"] = d.groupby(key)["F6"].rank(pct=True, method="average") * 100
    d["r7"] = d.groupby(key)["F7"].rank(pct=True, method="average") * 100
    d["F8"] = d["r6"] + d["r7"]
    return d


def order(d, sc):
    d = d.sort_values("sid", kind="mergesort")
    if sc == "F8":
        return d.sort_values(["F8", "F7"], ascending=[False, False], kind="mergesort")
    return FU_ORDER(d, sc)


def main():
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    CP = pd.read_csv(os.path.join(FD, "features.csv"), dtype={"sid": str})
    CP["買得到"] = CP["買得到"].astype(str).str.lower().eq("true")
    evs = sorted(CP["事件日"].unique()); seg_of = CP.drop_duplicates("事件日").set_index("事件日")["段"].to_dict()
    assert len(evs) == 28 and len(CP) == 1402, (len(evs), len(CP))
    log(f"[讀檔] fund/features.csv C+ {len(CP)} 列、事件 {len(evs)}；F6 缺 {int(CP['F6'].isna().sum())}、F7 缺 {int(CP['F7'].isna().sum())}")
    assert CP["F6"].notna().all() and CP["F7"].notna().all()
    CP = add_f8(CP, "事件日")
    rho = [float(pd.Series(g["F6"]).rank().corr(pd.Series(g["F7"]).rank())) for _, g in CP.groupby("事件日")]
    rhos = {sg: float(np.mean([r for e, r in zip(sorted(CP["事件日"].unique()), rho) if sg == "全部" or seg_of[e] == sg])) for sg in SEGS}
    log("[F6 vs F7 名次相關（事件內 Spearman 平均）] " + "、".join(f"{k} {v:.2f}" for k, v in rhos.items()))
    # ── 對照（同 fund）──
    V = pd.read_csv(FU.V1ER); V = V[(V["出場"] == "主") & (V["定義"] == "q2")]
    Y = pd.read_csv(FU.YLER); Y = Y[Y["r"].isna() | (Y["r"].astype(str) == "") | (Y["r"].astype(str) == "nan")]
    ref = {}
    for ev in evs:
        wn = "早年" if seg_of[ev] == "2006～2014" else "主"; r = {}
        for cd in ("A", "B"):
            q = V[(V["世界"] == wn) & (V["候選"] == cd) & (V["日期"] == ev)]; q = q[q["進場"].astype(str).str.lower() == "true"]
            r[cd] = float(q["報酬"].iloc[0]) if len(q) else np.nan
        q = Y[(Y["世界"] == wn) & (Y["候選"] == "C+") & (Y["日期"] == ev)]; assert len(q) == 1
        r["C+全買"] = float(q["報酬"].iloc[0])
        mine = float(CP[(CP["事件日"] == ev) & CP["買得到"]]["淨報酬"].mean()); assert abs(mine - r["C+全買"]) < 1e-6
        ref[ev] = r
    log("[對帳] C+ 全買（features 重算）＝ yl event_rows：28/28 差 ＜ 1e-6")
    # ── 挑檔 ──
    EP = []; picks = {}
    for ev in evs:
        d = CP[CP["事件日"] == ev]
        for sc in SCS:
            o = order(d, sc)
            for N in (1, 2, 3):
                pk = o.head(N); nb = pk[pk["買得到"]]
                ret = float(nb["淨報酬"].mean()) if len(nb) else 0.0
                picks[(ev, sc, N)] = list(pk["sid"])
                EP.append({"段": seg_of[ev], "事件日": ev, "分數": sc, "N": N, "C+檔數": len(d), "選中": " ".join(pk["sid"]),
                           "選中F8": " ".join(f"{x:.1f}" for x in pk["F8"]), "選中F6名次": " ".join(f"{x:.1f}" for x in pk["r6"]),
                           "選中F7名次": " ".join(f"{x:.1f}" for x in pk["r7"]), "買到檔數": len(nb), "空手": len(nb) == 0, "報酬": ret,
                           "選中各檔報酬": " ".join(f"{x:.4f}" if b else "買不到" for x, b in zip(pk["淨報酬"], pk["買得到"]))})
    EP = pd.DataFrame(EP)
    # 對帳 F6／F7 挑檔 vs fund/event_picks
    FE = pd.read_csv(os.path.join(FD, "event_picks.csv"), dtype={"選中": str})
    FE = FE[FE["分數"].isin(["F6", "F7"])].set_index(["事件日", "分數", "N"])
    bad = 0; mxr = 0.0
    for _, r in EP[EP["分數"].isin(["F6", "F7"])].iterrows():
        f = FE.loc[(r["事件日"], r["分數"], r["N"])]
        bad += int(str(f["選中"]).split() != r["選中"].split()); mxr = max(mxr, abs(float(f["報酬"]) - r["報酬"]))
    log(f"[對帳] F6／F7 重挑 vs fund/event_picks：選中不同 {bad}/{28 * 6}；報酬最大差 {mxr:.2e}")
    assert bad == 0 and mxr < 1e-5
    # 重疊
    OV = []
    for N in (1, 2, 3):
        for other in ("F6", "F7"):
            ov = [len(set(picks[(e, "F8", N)]) & set(picks[(e, other, N)])) for e in evs]
            OV.append({"N": N, "比較": other, "F8 與它選中完全相同事件數": int(sum(o == N for o in ov)), "平均重疊檔數": float(np.mean(ov))})
    OV = pd.DataFrame(OV); log("[F8 選中與 F6／F7 重疊（28 事件）]\n" + OV.to_string(index=False, float_format=lambda v: f"{v:.2f}"))
    # ── 隨機（同 pick／fund：同種子、同列序）──
    RS = {}
    for i, ev in enumerate(evs):
        d = CP[CP["事件日"] == ev]
        net = np.where(d["買得到"].to_numpy(), d["淨報酬"].to_numpy(float), np.nan); m = len(net)
        for N in (1, 2, 3):
            rng = np.random.default_rng([SEED, i, N])
            ix = np.argsort(rng.random((NR, m)), axis=1)[:, :N]
            v = net[ix]; fin = np.isfinite(v); cnt = fin.sum(axis=1)
            RS[(ev, N)] = np.where(cnt > 0, np.where(fin, v, 0.0).sum(axis=1) / np.maximum(cnt, 1), 0.0)
    PR = pd.read_csv(FU.PICKRND); FS = pd.read_csv(os.path.join(FD, "summary.csv")); mx = 0.0; mx2 = 0.0
    for sg in SEGS:
        es = [e for e in evs if sg == "全部" or seg_of[e] == sg]
        for N in (1, 2, 3):
            a = float(np.stack([RS[(e, N)] for e in es]).mean())
            mx = max(mx, abs(a - float(PR[(PR["段"] == sg) & (PR["N"] == N)]["平均"].iloc[0])))
            mx2 = max(mx2, abs(a - float(FS[(FS["段"] == sg) & (FS["方法"] == "隨機") & (pd.to_numeric(FS["N"], errors="coerce") == N)]["平均"].iloc[0])))
    log(f"[對帳] 隨機平均 vs pick/random.csv 最大差 {mx:.2e}；vs fund/summary.csv 最大差 {mx2:.2e}")
    assert mx < 1e-5 and mx2 < 1e-5
    # ── 彙總 ──
    SUM = []
    for sg in SEGS:
        es = [e for e in evs if sg == "全部" or seg_of[e] == sg]
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
            for sc in SCS:
                q = EP[(EP["分數"] == sc) & (EP["N"] == N) & EP["事件日"].isin(es)].set_index("事件日").loc[es]
                x = q["報酬"].to_numpy(float); s = FU.stats(x)
                cpa = np.array([ref[e]["C+全買"] for e in es])
                SUM.append({"段": sg, "方法": sc, "名稱": SCNAME[sc], "N": N, **s, "空手事件數": int(q["空手"].sum()),
                            "隨機段平均P10": float(np.quantile(sa, .1)), "隨機段平均P50": float(np.quantile(sa, .5)), "隨機段平均P90": float(np.quantile(sa, .9)),
                            "隨機中位置（百分位）": float((sa < s["平均"]).mean()), "p（隨機≥分數）": float((sa >= s["平均"]).mean()),
                            "勝過C+全買事件數": int((x > cpa).sum()),
                            "勝過A事件數": int(sum(1 for e, v in zip(es, x) if np.isfinite(ref[e]["A"]) and v > ref[e]["A"])),
                            "勝過A可比事件數": int(sum(1 for e in es if np.isfinite(ref[e]["A"])))})
    SUM = pd.DataFrame(SUM)
    # 對帳 F6／F7 彙總 vs fund/summary
    mx3 = 0.0
    for _, r in SUM[SUM["方法"].isin(["F6", "F7"])].iterrows():
        f = FS[(FS["段"] == r["段"]) & (FS["方法"] == r["方法"]) & (pd.to_numeric(FS["N"], errors="coerce") == r["N"])].iloc[0]
        mx3 = max(mx3, abs(float(f["平均"]) - r["平均"]), abs(float(f["隨機中位置（百分位）"]) - r["隨機中位置（百分位）"]))
    log(f"[對帳] F6／F7 彙總（平均、隨機百分位）vs fund/summary.csv 最大差 {mx3:.2e}")
    SUM.to_csv(os.path.join(OUT, "summary.csv"), index=False, float_format="%.6g", encoding="utf-8")
    EP.to_csv(os.path.join(OUT, "event_picks.csv"), index=False, float_format="%.6g", encoding="utf-8")
    pd.set_option("display.width", 260); pd.set_option("display.max_rows", 900); pd.set_option("display.max_columns", 40)
    cols = ["段", "方法", "N", "事件數", "平均", "中位", "勝率", "最差", "虧＞10%次數", "隨機中位置（百分位）", "勝過A事件數"]
    log("[彙總]\n" + SUM[cols].to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    # ── 五分位（借 fund.quintiles，排序換成 F8）──
    FU.order = order
    QT, QX = FU.quintiles(CP, evs, seg_of, "F8")
    QX = pd.DataFrame(QX)
    QT.to_csv(os.path.join(OUT, "quintile.csv"), index=False, float_format="%.6g", encoding="utf-8")
    QX.to_csv(os.path.join(OUT, "quintile_mono.csv"), index=False, float_format="%.6g", encoding="utf-8")
    log("[F8 五分位]\n" + QT.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    log("[F8 單調／Q5−Q1]\n" + QX.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    # ── 10/15 前瞻 ──
    W = pd.read_csv(os.path.join(FD, "forward_20261015_features.csv"), dtype={"sid": str})
    assert len(W) == 75 and W["F6"].notna().all() and W["F7"].notna().all(), (len(W), W["F6"].isna().sum(), W["F7"].isna().sum())
    W = add_f8(W, "事件日")
    o = order(W, "F8").reset_index(drop=True)
    o6 = order(W, "F6")["sid"].tolist(); o7 = order(W, "F7")["sid"].tolist()
    o["F8名次"] = np.arange(1, len(o) + 1)
    o["F6名次（75檔）"] = [o6.index(s) + 1 for s in o["sid"]]; o["F7名次（75檔）"] = [o7.index(s) + 1 for s in o["sid"]]
    fw = o.head(10)[["F8名次", "sid", "名稱", "F8", "r6", "r7", "F6名次（75檔）", "F7名次（75檔）", "F6", "F7", "F7A", "F7B", "F7C", "F7D", "F7E",
                     "F1", "F4", "F5", "ret1", "fin_q", "inU"]].rename(columns={"sid": "代號", "r6": "F6百分位名次", "r7": "F7百分位名次", "ret1": "當日報酬",
                                                                                "fin_q": "財報季", "inU": "在F7大母體", "F1": "F1基本面", "F4": "F4籌碼", "F5": "F5線型"})
    fw.to_csv(os.path.join(OUT, "forward_20261015.csv"), index=False, float_format="%.6g", encoding="utf-8")
    log("[10/15 F8 前 10]\n" + fw.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    S = {"程式": "backtest/researchMktDrop_f8.py", "時間（台北）": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M"), "讀法": __doc__, "註": NOTES,
         "F6vsF7名次相關": rhos, "重疊": OV.to_dict("records"), "summary": SUM.replace({np.nan: None}).to_dict("records"),
         "quintile": QT.replace({np.nan: None}).to_dict("records"), "單調": QX.replace({np.nan: None}).to_dict("records"),
         "forward_20261015_前10": fw.replace({np.nan: None}).to_dict("records"), "耗時秒": round(time.time() - T0, 1)}
    with open(os.path.join(OUT, "MktDrop_f8.json"), "w", encoding="utf-8") as f:
        json.dump(S, f, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    with open(os.path.join(OUT, "run.log"), "w", encoding="utf-8") as f:
        f.write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
