# -*- coding: utf-8 -*-
"""「100 萬放一年」加件：效率前緣＋與 0050 混五檔＋流動性（台股策略線 seq241／242／243；裁定 seq186 §六；回測線計算助手 2026-09-26）。

⭐ 全部是描述、⛔ 不判、⛔ 不計 N。⛔ 不改任何既有 .py；引擎呼叫一律走 researchYear1M.run_engine（G1 已對主窗逐位元），
   合成一律走 researchp17.compose（P17 原件的權益層合成：再平衡日換手 × 0.585%）、P14 用 researchp14.blend。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYear1M_mix frontier
    ... -m backtest.researchYear1M_mix mix [--procs 2]

═══ ① 前緣表（⛔ 不重跑，一律讀既有結果檔）═══
  F1 來源：resultsN17/regime_t1/all17.csv（17 格；regime 五格＝t−1 版）、resultsN17/rerun17.csv（regime 五格原版 ⇒ 標「含日內前視、不進前緣」）、
     resultsN17/seeds_main.csv 格 0 的 200 顆中位（門檻B W1，rerun17 描述臂）、resultsP9run/cells.csv（12 判定格＋基準臂＋ⓑ參照）、
     resultsN219/table219.csv（219 表）、0050 主窗錨
  F2 219 表各族的窗不同（錨 0.2402／0.241／0.2454／0.246／0.248／0.249…）⇒ 只有錨＝主窗 0.240202 的列算「主窗」；
     其餘列標「舊窗（錨 x）」、⛔ 不進主前緣，另給一欄「含舊窗」的前緣只供參考（窗不同、不可直接比）
  F3 219 表裡已由 rerun17 在主窗重跑的 17 格（年化、回落與 rerun17.csv 的 原交件_年化／回落 相同）⇒ 標「已有主窗重跑版」、兩種前緣都不進
     219 表的 PREREG10／11 regime=True 舊窗列 ⇒ 同樣是進場日收盤判閘 ⇒ 標「含日內前視」、兩種前緣都不進
     PREREGI 四列是回落拆解量（不是權益曲線）⇒ 不進
  F4 主窗 219 列（P13～P17、D4、PREREGA/C/D5/F）是【舊資料快照】上跑的（例 P14 w=0.50：219 表 0.262577、edc6f 重跑 0.262245）⇒ 照列、標「舊快照」
  F5 前緣格 ＝ 同一集合裡沒有任何別格【年化嚴格更高且回落嚴格更淺】；比值 ＝ 年化 ÷ |回落|
═══ ② 與 0050 混 ═══
  M1 臂 ＝ 主前緣裡年化最高的 3 格 ∪ {#1 t−1}（#1 若已在前 3 ⇒ 臂數 3，⛔ 不往下補）
  M2 逐種子：該臂的逐日權益 E（主窗 ＝ 引擎原樣版、與前緣數字同一條；固定窗 ＝ researchYear1M 主版，窗起點空手）與 0050 還原收盤 B，
     P17.compose(E, B, w 常數, 再平衡＝窗內每年第一個交易日（窗首當天不算）, 成本 0.585%×換手) ⇒ 200 顆各算、報中位
     w ＝ 選股占比 0／0.25／0.5／0.75／1；w＝0 必須 ＝ 0050、w＝1 必須 ＝ 該臂本身（查核）
  M3 P14 w=0.25 這一臂本身就是「P12 策略 25%＋0050 75%、期初配置不再平衡」（P14.blend）⇒ 先 blend 成該臂的 E，再照 M2 與 0050 混
═══ ③ 流動性 ═══
  L1 部位 ＝ 主窗內（w0 ≤ t ≤ w1）引擎 audit 的每一筆 buy（200 顆種子全部彙總）；ADV20 ＝ 該股進場日之前最後 20 個有成交日的成交金額平均（元）
  L2 單檔部位 ＝ 總投入 × 選股袖占比 ÷ 檔數（#1 N10、#13 N20、P14 w=0.25 ＝ 0.25 × 總額 ÷ 8）；比例 ＝ 單檔部位 ÷ ADV20
  L3 ⚠ 回測不含衝擊成本，成本只有手續費與稅（引擎來回 0.585%；合成換手 0.585%）
"""
from __future__ import annotations

import argparse
import json
import os
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import researchYear1M as Y
from . import rerun17 as RR
from . import research13 as R13
from . import data as D

HERE = Y.HERE
OUT = Y.OUT
RTP = dict(float_precision="round_trip")
ANC = RR.ANCHOR
WS = (0.0, 0.25, 0.5, 0.75, 1.0)
TOTALS = (1_000_000, 3_000_000, 5_000_000)
WORDING = {"前緣": "前緣是在同一段看完結果畫出來的，是這段歷史的最優，不是往後的最優",
           "混0050族": "混 0050 族的假訊號也常過",
           "流動性": "回測不含衝擊成本，成本只有手續費與稅"}
_G: dict = {}


# ═════════════ ① 前緣 ═════════════
def dominated(c, m):
    c = np.asarray(c, float); m = np.asarray(m, float)
    out = np.zeros(len(c), bool)
    for i in range(len(c)):
        out[i] = bool(np.any((c > c[i]) & (m > m[i])))
    return out


def frontier(log):
    rows = []
    r17 = pd.read_csv(os.path.join(RR.OUT, "rerun17.csv"), **RTP)
    a17 = pd.read_csv(os.path.join(RR.OUT, "regime_t1", "all17.csv"), **RTP)
    for q in a17.itertuples():
        t1 = q.出處 == "t1"
        rows.append({"來源": "PREREGV 17 格（resultsN17/regime_t1/all17.csv）", "編號": f"#{q.編號}", "族": q.族,
                     "格": q.格 + ("（t−1 閘）" if t1 else ""), "窗": "主窗", "資料": "edc6f", "年化中位": q.年化, "回落中位": q.回落,
                     "進前緣": True, "註": "t−1 版" if t1 else ""})
    for q in r17[r17["編號"].isin([1, 4, 7, 16, 17])].itertuples():
        rows.append({"來源": "rerun17.csv 主窗（原版）", "編號": f"#{q.編號}", "族": q.族, "格": q.格 + "（原版：進場日收盤判閘）",
                     "窗": "主窗", "資料": "edc6f", "年化中位": q.主窗_年化, "回落中位": q.主窗_回落, "進前緣": False,
                     "註": "含日內前視、不進前緣"})
    sm = pd.read_csv(os.path.join(RR.OUT, "seeds_main.csv"), **RTP)
    g0 = sm[(sm["stage"] == "main") & (sm["cell"] == 0)]
    rows.append({"來源": "resultsN17/seeds_main.csv 格 0（200 顆中位）", "編號": "門檻B", "族": "P12", "格": "門檻B W1（策略側 H120 N8；rerun17 描述臂）",
                 "窗": "主窗", "資料": "edc6f", "年化中位": float(g0["cagr"].median()), "回落中位": float(g0["mdd"].median()),
                 "進前緣": True, "註": ""})
    p9 = pd.read_csv(os.path.join(HERE, "resultsP9run", "cells.csv"), **RTP)
    for q in p9.itertuples():
        rows.append({"來源": "resultsP9run/cells.csv", "編號": f"P9 {q.arm}", "族": f"P9 {q.族}", "格": q.格, "窗": "主窗", "資料": "edc6f",
                     "年化中位": q.cagr, "回落中位": q.mdd, "進前緣": True,
                     "註": "" if q.判定 else ("基準臂（＝門檻B N8、種子 99000＋r）" if q.arm == "base" else "參照臂（不判）")})
    T = pd.read_csv(os.path.join(HERE, "resultsN219", "table219.csv"), **RTP)
    orig = [(float(a), float(b)) for a, b in zip(r17["原交件_年化"], r17["原交件_回落"])]
    for q in T.itertuples():
        main = abs(float(q.錨年化) - ANC[0]) < 1e-5
        note = []; ok = True
        if not np.isfinite(q.年化):
            note.append("不是權益曲線（回落拆解量）"); ok = False
        elif any(abs(q.年化 - a) < 1e-12 and abs(q.回落 - b) < 1e-12 for a, b in orig):
            k = [int(e) for e, a, b in zip(r17["編號"], r17["原交件_年化"], r17["原交件_回落"]) if abs(q.年化 - a) < 1e-12 and abs(q.回落 - b) < 1e-12]
            note.append(f"已有主窗重跑版（#{k[0]}）"); ok = False
        elif ("PREREG10" in q.族 or "PREREG11" in q.族) and "regime=True" in q.格:
            note.append("含日內前視（進場日收盤判閘）"); ok = False
        rows.append({"來源": "resultsN219/table219.csv", "編號": "219", "族": q.族, "格": q.格,
                     "窗": "主窗" if main else f"舊窗（0050 錨 {q.錨年化:.4f}）", "資料": "舊快照" if main else "舊快照＋舊窗",
                     "年化中位": q.年化, "回落中位": q.回落, "進前緣": ok, "註": "；".join(note) + ("" if pd.isna(q.註) else f"｜219 註：{q.註}")})
    rows.append({"來源": "rerun17 0050 錨（P17 W0 逐位元）", "編號": "0050", "族": "0050", "格": "0050 買進持有", "窗": "主窗", "資料": "edc6f",
                 "年化中位": ANC[0], "回落中位": ANC[1], "進前緣": True, "註": ""})
    F = pd.DataFrame(rows)
    F["比值"] = F["年化中位"] / F["回落中位"].abs()
    F["混0050族"] = F["族"].astype(str).str.contains("P14|P17") | F["格"].astype(str).str.contains("混 0050")
    for col, mask in (("前緣_主窗", F["進前緣"] & (F["窗"] == "主窗")), ("前緣_含舊窗（窗不同、只供參考）", F["進前緣"])):
        idx = F.index[mask]
        dom = dominated(F.loc[idx, "年化中位"], F.loc[idx, "回落中位"])
        F[col] = False
        F.loc[idx[~dom], col] = True
    F["措辭"] = np.where(F["前緣_主窗"], WORDING["前緣"], "")
    F.loc[F["混0050族"], "措辭"] = (F.loc[F["混0050族"], "措辭"] + "｜" + WORDING["混0050族"]).str.strip("｜")
    F = F.sort_values(["前緣_主窗", "年化中位"], ascending=[False, False], kind="stable").reset_index(drop=True)
    F.to_csv(os.path.join(OUT, "frontier.csv"), index=False)
    fr = F[F["前緣_主窗"]]
    log(f"[前緣] {len(F)} 列｜主前緣 {len(fr)} 格：" + "；".join(f"{a} {b} {c:.4f}/{d:.4f}" for a, b, c, d in
                                                           zip(fr["編號"], fr["格"], fr["年化中位"], fr["回落中位"])))
    fr2 = F[F["前緣_含舊窗（窗不同、只供參考）"]]
    log(f"[前緣 含舊窗] {len(fr2)} 格：" + "；".join(f"{a} {b} {c:.4f}/{d:.4f}" for a, b, c, d in
                                                zip(fr2["族"], fr2["格"], fr2["年化中位"], fr2["回落中位"])))
    return F


# ═════════════ ② 混 ═════════════
def arm_recipe(row):
    """前緣列 ⇒ 模擬配方 (cid, blend)。回 None ＝ 本檔沒有這一族的引擎配方。"""
    k = str(row["編號"])
    if k.startswith("#") and int(k[1:]) in Y.CELL:
        cid = int(k[1:])
        return {"arm": k, "cid": cid, "blend": None, "N": Y.CELL[cid][4].get("N", RR.P12_N), "sleeve": 1.0, "name": row["格"]}
    if k == "門檻B":
        return {"arm": k, "cid": 0, "blend": None, "N": RR.P12_N, "sleeve": 1.0, "name": row["格"]}
    if k == "219" and row["族"] == "P14" and str(row["格"]).startswith("w="):
        w = float(str(row["格"])[2:6])
        return {"arm": f"P14 w={w:.2f}", "cid": 0, "blend": w, "N": RR.P12_N, "sleeve": w, "name": f"P14 w={w:.2f}（P12 策略 {w:.0%}＋0050、期初配置不再平衡）"}
    return None


def year_mask(cal, a, b):
    """窗內每年第一個交易日（相對位置；窗首當天不算）。"""
    yr = pd.DatetimeIndex(cal[a:b + 1]).year
    m = np.zeros(b - a + 1, bool)
    m[1:] = yr[1:] != yr[:-1]
    return m


def adv20(sid, t):
    a = _G["amt"].get(sid)
    if a is None:
        return np.nan
    idx, cs = a
    k = int(np.searchsorted(idx, t))          # t 之前的有成交根數
    return float((cs[k] - cs[k - 20]) / 20.0) if k >= 20 else np.nan


def _mix(args):
    from . import researchp14 as P14
    from . import researchp17 as P17
    arm, r = args
    rc = _G["arms"][arm]; cal = Y._G["cal"]; B = Y._G["bench"]
    out = {"rows": [], "liq": []}
    # 主窗（引擎原樣版 ＝ 前緣數字同一條）
    w0, w1 = RR.win_bounds(cal); n = w1 - w0 + 1
    au = []
    sig = Y.sig_of(rc["cid"], "eng", w0, w1)
    s = Y.run_engine(rc["cid"], sig, r, "eng", audit=au)
    E = np.asarray(s["equity"], float)[w0:w1 + 1]; Bm = B[w0:w1 + 1]
    if rc["blend"] is not None:
        E = P14.blend(E, Bm, rc["blend"])
    m = year_mask(cal, w0, w1)
    for w in WS:
        V, turn, cst = P17.compose(E, Bm, np.full(n, w), m)
        c, dd = R13.window_stats(V, 0, n, 0, n)
        out["rows"].append({"arm": arm, "scope": "主窗", "w": w, "r": r, "cagr": float(c), "mdd": float(dd),
                            "end_value": Y.CAPITAL * V[-1] / V[0], "cost_sum": float(cst.sum())})
    if rc["blend"] is None:
        c1, m1 = R13.window_stats(E, 0, n, 0, n)
        out["self"] = (float(c1), float(m1))
    for a_ in au:
        if a_["side"] == "buy" and w0 <= a_["t"] <= w1:
            out["liq"].append({"arm": arm, "r": r, "sid": a_["sid"], "t": int(a_["t"]), "adv20": adv20(a_["sid"], int(a_["t"]))})
    # 固定窗（主版）
    for fw in _G["FW"]:
        a, b = fw["w0"], fw["w1"]; nn = b - a + 1
        sig = Y.sig_of(rc["cid"], "mtm", a, b)
        s = Y.run_engine(rc["cid"], sig, r, "mtm")
        E = np.asarray(s["equity"], float)[a:b + 1]; Bw = B[a:b + 1]
        if rc["blend"] is not None:
            E = P14.blend(E, Bw, rc["blend"])
        mm = year_mask(cal, a, b)
        for w in WS:
            V, _, cst = P17.compose(E, Bw, np.full(nn, w), mm)
            ret, dd = Y.seg_stats(V)
            out["rows"].append({"arm": arm, "scope": fw["key"], "w": w, "r": r, "cagr": np.nan, "mdd": dd,
                                "end_value": Y.CAPITAL * (1 + ret), "cost_sum": float(cst.sum())})
    return out


def load_amt(sids, cal, log):
    uni = Y._G["uni"]; t0 = time.time(); out = {}
    for s in sorted(sids):
        st = D.load_stock(s, uni.get(s, "twse"), cal)
        if st is None:
            continue
        tr = st.df["traded"].to_numpy(bool); am = st.df["amount"].to_numpy(float)
        idx = np.flatnonzero(tr & np.isfinite(am))
        out[s] = (idx, np.r_[0.0, np.cumsum(am[idx])])
    log(f"[成交金額] {len(out)} 檔｜{time.time() - t0:.0f}s")
    return out


def mix(procs, log):
    F = pd.read_csv(os.path.join(OUT, "frontier.csv"), **RTP)
    fr = F[F["前緣_主窗"]].sort_values("年化中位", ascending=False)
    top = fr.head(3)
    recs = {}
    for _, row in top.iterrows():
        rc = arm_recipe(row)
        if rc is None:
            raise SystemExit(f"⛔ 前緣前 3 的 {row['族']} {row['格']} 本檔沒有引擎配方 ⇒ 停、回報")
        recs[rc["arm"]] = rc
    if "#1" not in recs:
        recs["#1"] = arm_recipe(F[(F["編號"] == "#1") & F["進前緣"]].iloc[0])
    log(f"[臂] {json.dumps({k: {kk: vv for kk, vv in v.items()} for k, v in recs.items()}, ensure_ascii=False)}")
    Y.setup(log)
    cal = Y._G["cal"]
    FW = Y.fixed_windows(cal)
    sids = set(Y._G["AND_eng"]["sid"]) | set(Y._G["AND_mtm"]["sid"]) | set(Y._G["s12_mtm"]["sid"]) | set(Y._G["s12_eng"]["sid"])
    _G.update(arms=recs, FW=FW, amt=load_amt(sids, cal, log))
    jobs = [(a, r) for a in recs for r in range(Y.REPS)]
    t0 = time.time(); rows = []; liq = []; selfc = {}
    with Pool(procs) as pool:
        for i, o in enumerate(pool.imap_unordered(_mix, jobs, chunksize=2)):
            rows += o["rows"]; liq += o["liq"]
            if "self" in o:
                selfc[(o["rows"][0]["arm"], o["rows"][0]["r"])] = o["self"]
            if (i + 1) % 100 == 0:
                log(f"  {i + 1}/{len(jobs)}｜{time.time() - t0:.0f}s")
    S = pd.DataFrame(rows).sort_values(["arm", "scope", "w", "r"], kind="stable").reset_index(drop=True)
    S.to_csv(os.path.join(OUT, "mix_seeds.csv.gz"), index=False, compression={"method": "gzip", "mtime": 0})
    L = pd.DataFrame(liq).sort_values(["arm", "r", "t", "sid"], kind="stable").reset_index(drop=True)
    L["date"] = [str(cal[t].date()) for t in L["t"]]
    L.to_csv(os.path.join(OUT, "liq_positions.csv.gz"), index=False, compression={"method": "gzip", "mtime": 0})
    # 查核：w＝1 對既有逐種子檔（#1 → regime_t1 t1；#13 等 → seeds_main）；w＝0 對 0050 錨／bench_windows
    chk = {}
    ref_t1 = pd.read_csv(os.path.join(RR.OUT, "regime_t1", "seeds.csv"), **RTP)
    ref_m = pd.read_csv(os.path.join(RR.OUT, "seeds_main.csv"), **RTP)
    for arm, rc in recs.items():
        g = S[(S["arm"] == arm) & (S["scope"] == "主窗") & (S["w"] == 1.0)].set_index("r").sort_index()
        if rc["blend"] is None:
            cid = rc["cid"]
            ref = (ref_t1[(ref_t1["stage"] == "t1") & (ref_t1["cell"] == cid)] if cid in Y.REG_T1
                   else ref_m[(ref_m["stage"] == "main") & (ref_m["cell"] == cid)]).set_index("r").sort_index()
            chk[f"{arm} w=1 對既有逐種子（compose 以日報酬連乘 ⇒ 報最大絕對差）"] = {
                k: float((g[k] - ref.loc[g.index, k]).abs().max()) for k in ("cagr", "mdd")} | {"顆數": len(g)}
        g0 = S[(S["arm"] == arm) & (S["scope"] == "主窗") & (S["w"] == 0.0)]
        chk[f"{arm} w=0 對 0050 錨"] = {"年化最大差": float((g0["cagr"] - ANC[0]).abs().max()), "回落最大差": float((g0["mdd"] - ANC[1]).abs().max())}
    Bw = pd.read_csv(os.path.join(OUT, "bench_windows.csv"), **RTP)
    Bw = Bw[Bw["kind"] == "fixed"].set_index("win")
    fz = S[(S["scope"] != "主窗") & (S["w"] == 0.0)]
    chk["固定窗 w=0 對 bench_windows 最大相對差"] = float((fz["end_value"] / fz["scope"].map(Bw["end_value"]) - 1).abs().max())
    FS = pd.read_csv(os.path.join(OUT, "seeds.csv.gz"), **RTP)
    for arm, rc in recs.items():
        if rc["blend"] is None:
            f1 = S[(S["arm"] == arm) & (S["scope"] != "主窗") & (S["w"] == 1.0)]
            ref = FS[(FS["kind"] == "fixed") & (FS["cell"] == rc["cid"]) & (FS["variant"] == "mtm")]
            mg = f1.merge(ref, left_on=["scope", "r"], right_on=["win", "r"], suffixes=("", "_ref"))
            chk[f"{arm} 固定窗 w=1 對 seeds.csv.gz"] = {"列": len(mg), "期末最大相對差": float((mg["end_value"] / mg["end_value_ref"] - 1).abs().max())}
    log(f"[查核] {json.dumps(chk, ensure_ascii=False)}")
    # 彙總表
    out = []
    for arm in recs:
        for w in WS:
            g = S[(S["arm"] == arm) & (S["w"] == w)]
            gm = g[g["scope"] == "主窗"]
            row = {"臂": arm, "名稱": recs[arm]["name"], "選股占比w": w, "0050占比": 1 - w,
                   "主窗年化_中位": float(gm["cagr"].median()), "主窗最大回落_中位": float(gm["mdd"].median()),
                   "主窗比值（中位÷|中位|）": float(gm["cagr"].median() / abs(gm["mdd"].median())),
                   "主窗100萬期末_中位": float(gm["end_value"].median()), "主窗100萬期末_p10": float(gm["end_value"].quantile(0.10)),
                   "主窗100萬期末_p90": float(gm["end_value"].quantile(0.90)), "主窗再平衡成本合計_中位": float(gm["cost_sum"].median())}
            for fw in FW:
                gf = g[g["scope"] == fw["key"]]["end_value"]
                row[f"{fw['key']}_期末中位"] = float(gf.median())
            row["措辭"] = WORDING["前緣"] + ("｜" + WORDING["混0050族"] if (recs[arm]["blend"] is not None or w < 1) else "")
            out.append(row)
    M = pd.DataFrame(out)
    M.to_csv(os.path.join(OUT, "mix.csv"), index=False)
    # 流動性
    lq = []
    for arm, rc in recs.items():
        g = L[L["arm"] == arm]; a = g["adv20"].to_numpy(float); ok = np.isfinite(a) & (a > 0)
        row = {"臂": arm, "檔數N": rc["N"], "選股袖占比": rc["sleeve"], "部位筆數（200 顆合計）": len(g), "ADV20 缺（前面不足 20 根）": int((~ok).sum()),
               "ADV20_中位（元）": float(np.median(a[ok])), "ADV20_p10（元）": float(np.percentile(a[ok], 10))}
        for T in TOTALS:
            pos = T * rc["sleeve"] / rc["N"]; ratio = pos / a[ok]
            lab = f"{T // 10000}萬"
            row[f"{lab}_單檔部位（元）"] = pos
            row[f"{lab}_占ADV20_中位"] = float(np.median(ratio)); row[f"{lab}_占ADV20_p90"] = float(np.percentile(ratio, 90))
            row[f"{lab}_超過10%筆數占比"] = float((ratio > 0.10).mean())
        row["註"] = WORDING["流動性"]
        lq.append(row)
    LQ = pd.DataFrame(lq)
    LQ.to_csv(os.path.join(OUT, "liquidity.csv"), index=False)
    json.dump({"臂": recs, "查核": chk, "措辭": WORDING, "流動性讀法": "部位＝主窗內 audit 的每一筆 buy（200 顆合計）；ADV20＝進場日前最後 20 個有成交日成交金額平均；單檔部位＝總投入×選股袖占比÷檔數",
               "混合讀法": "P17.compose：w 常數、每年第一個交易日再平衡（窗首不算）、換手×0.585%；主窗用引擎原樣版、固定窗用 researchYear1M 主版"},
              open(os.path.join(OUT, "mix_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完成] mix.csv {len(M)} 列｜liquidity.csv {len(LQ)} 列｜mix_seeds {len(S):,}｜liq_positions {len(L):,}｜{time.time() - t0:.0f}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["frontier", "mix"])
    ap.add_argument("--procs", type=int, default=2)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "a", encoding="utf-8")
    T0 = time.time()

    def log(x):
        x = f"[{time.time() - T0:6.0f}s] {x}"
        print(x, flush=True); logf.write(x + "\n"); logf.flush()

    log(f"===== researchYear1M_mix {a.stage} {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）=====")
    if a.stage == "frontier":
        frontier(log)
    else:
        mix(a.procs, log)


if __name__ == "__main__":
    main()
