# -*- coding: utf-8 -*-
"""大盤大跌後「只能買 1～3 檔」——Q ＝ 純優質（長期體質）分數，只在該事件 C+ 內挑（描述性初測；⛔ 不計 N、⛔ 不判定、⛔ 不是買賣建議）
回測線計算子代理，2026-10-17。使用者：「優質股跟我們這樣挑不一樣嗎？」——F6／F7 偏近期成長＋籌碼＋線型，不是長期體質 ⇒ 做一個只看體質的 Q

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMktDrop_quality

═══ 讀法（寫死於第一次跑之前；⚠ Q 是看過 pick／fund／f8 結果之後才提的 ⇒ 事後設計）═══
 W0 ⛔ 不重跑引擎：C+ 名單、逐筆淨報酬、買得到只讀 resultsMktDrop/fund/features.csv（＝ deep/c_rows.csv 主出場「加權收盤收復事件前一日收盤 ⇒ 隔天開盤賣」、
    成本 0.585%）；F6／F7 挑檔讀 fund/event_picks.csv、F8 讀 f8/event_picks.csv；0050、00631L、C+ 全買 ＝ 同 fund（v1／yl event_rows，程式內對帳）；
    隨機 ＝ 同 pick／fund（同種子、同列序、事件序號照 28 事件，程式內對帳 pick/random.csv 與 fund/summary.csv）
 W1 只比 2015 年以後 18 事件（2015～2021 7、2022～ 11）；2006～2014 段標缺（財報 2013 起，早年 10 事件都在 2011-08 以前）
 W2 Q 子項（6 個；全部只用事件日 t 以前可得）
    財報 ＝ data/mops/fin_hist（年初至今差分成單季），fs_xbrl 只當負債比、營業現金流的備援；origin/main f48d0851da 唯讀 archive（同 fund）
    可得日（seq352）＝ filing_dates.csv（t57sb01）該季最早上傳日；上傳日 ＜ t 才可用；沒有時戳（2013、2014 全部等）⇒ 法定期限（Q1 5/15、Q2 8/14、Q3 11/14、年報次年 3/31）
    q_roe_m 近 12 季單季 ROE 平均（高好）；單季 ROE ＝ 單季母公司淨利 ÷ 季末母公司權益（母公司欄缺 ⇒ 單季淨利 ÷ 季末權益總額）×4；權益 ≤ 0 ⇒ 該季缺
    q_roe_s 近 12 季單季 ROE 標準差（低好）
    q_gm_s  近 12 季單季毛利率標準差（低好）；單季營收 ≤ 0 或毛利缺 ⇒ 該季缺（金融保險多半整個缺）
            ⇒ 三者都要「最近可得季往回 12 季中 ≥ 8 季有值」，否則缺（2015-08-24 事件最多 10 季）
    q_debt  最近可得季負債比 ＝ 總負債 ÷ 總資產（低好）；負債欄缺 ⇒ 1 − 權益總額 ÷ 總資產；再缺 ⇒ fs_xbrl 1 − total_equity ÷ total_assets
    q_ocf   近 4 季營業現金流合計 ＞ 0（1／0）：最近可得季往回 4 季單季（年初至今差分）都要有；fin_hist ocf_ytd 缺 ⇒ fs_xbrl operating_cash_flow_ytd
    q_div   近 3 年每年有配息（1／0）：事件年 Y 的 Y−3、Y−2、Y−1 三個日曆年，每年都至少有一次除息（data/adj kind 含「息」：息、除息、權息、除權息；
            只有除權（股票股利）不算）；除息日 ＜ t 才算（Y−1 年整年都在 t 之前）；資料 ＝ h2data 4b26f6（≤ 2026-10-15）data/adj
            ⚠ 上市 adj 2015-01-05 起、上櫃 2008 起 ⇒ 上市股 Y−3 ＜ 2015（只有 2015-08-24 事件）⇒ 缺；adj 沒有這檔 ⇒ 視為 2015 起（上櫃 2008 起）都沒有除權息 ⇒ 0（報檔數）
 W3 Q ＝ 6 子項在該事件 C+ 內的百分位（rank pct、同值取平均；低好者取負值再排）等權平均；缺值該子項 0 分、分母固定 6（同 fund F1～F6）
    同分 ⇒ 代號小者（同 fund order）
 W4 挑 N ＝ 只在該事件 C+ 內按 Q 降冪前 N 檔；報酬 ＝ 選中中買得到者淨報酬等權；全買不到 ⇒ 0（同 pick／fund）
 W5 報：2015～2021、2022～、2015～（18 事件）三段；平均、中位、勝率、最差、虧 ＞10% 次數、隨機段平均分布中的位置（百分位 ＝ 隨機段平均 ＜ 分數段平均 的比例）
    對照 0050、00631L（正2）、C+ 全買、C+ 隨機、F6、F7、F8
 W6 Q 五分位：每事件 C+ 依 Q 排序切 5 組（Q5 高分）；組內買得到者等權；段內事件等權；事件群集 bootstrap 2000 次 CI；Q5−Q1；每事件 Spearman
 W7 10/15 前瞻：fund/forward_20261015_features.csv 的 C+ 75 檔；財報 f48d0851da 只用上傳日 ＜ 10/15；除息用 4b26f6（≤ 10/15）
 W8 必附：Q 是第 20 種分數（fund 18 ＋ F8 ＋ Q）× 3 N × 段 ⇒ 多重比較；只有 18 事件；Q 是看過前面結果之後才提的（事後設計）；描述性、不計 N、不判定
輸出 backtest/resultsMktDrop/quality/：MktDrop_quality.json、summary.csv、quintile.csv、quintile_mono.csv、event_picks.csv、features.csv、missing.csv、
     forward_20261015.csv、run.log
"""
from __future__ import annotations

import glob
import json
import os
import time

import numpy as np
import pandas as pd

from backtest import researchMktDrop_fund as FU

REPO = os.path.expanduser("~/tw-p17")
FD = os.path.join(REPO, "backtest/resultsMktDrop/fund")
F8D = os.path.join(REPO, "backtest/resultsMktDrop/f8")
OUT = os.path.join(REPO, "backtest/resultsMktDrop/quality")
XD = FU.XD
ADJ = os.path.join(FU.FDATA, "adj")
NR, SEED, NBOOT = FU.NR, FU.SEED, FU.NBOOT
QSEED = 2026101703
SEGS = ["2015～2021", "2022～", "2015～（18事件）"]
SUBS = ["q_roe_m", "q_roe_s", "q_gm_s", "q_debt", "q_ocf", "q_div"]
LOWGOOD = {"q_roe_s", "q_gm_s", "q_debt"}
SUBNAME = {"q_roe_m": "近12季ROE平均（高好）", "q_roe_s": "近12季ROE標準差（低好）", "q_gm_s": "近12季毛利率標準差（低好）",
           "q_debt": "負債比（低好）", "q_ocf": "近4季營業現金流合計>0", "q_div": "近3年每年有配息"}
MINQ = 8
TWSE_ADJ0, TPEX_ADJ0 = 2015, 2008
CMP = ["Q", "F6", "F7", "F8"]
CMPNAME = {"Q": "⭐Q 純優質（6 子項 C+ 內百分位等權）", "F6": FU.SCNAME["F6"], "F7": FU.SCNAME["F7"], "F8": "F8（F6 名次＋F7 名次）"}
NOTES = ["描述性初測：⛔ 不計 N、⛔ 不判定、⛔ 不是買賣建議；挑檔候選一律只限該事件 C+（大跌日跌最多一成 ∧ 營收年增 ＞ 0）",
         "⚠ 多重比較：fund 18 種分數 ＋ F8 ＋ Q ⇒ Q 是第 20 種分數，× 3 N × 段；分數越多、碰巧好看的越多；百分位只是位置、不是檢定",
         "⚠ 只有 18 個事件（2015～2021 7、2022～ 11）；早年 10 事件沒有財報 ⇒ 標缺；差異多半是運氣",
         "⚠ 事後設計：Q 是看過 pick（單一特徵）、fund（F1～F7）、f8 結果之後才提的；子項與權重是執行者設定 ⇒ 任何「看起來較好／較差」只是待驗線索",
         "Q 缺值該子項 0 分 ⇒ 金融保險（沒有毛利）、上市未滿 2 年（不足 8 季）的股票分數偏低；負債比對金融業天生高 ⇒ 金融業被壓低；缺值比例見 missing.csv",
         "配息只看「有沒有除息」不看金額；上市 adj 2015 起 ⇒ 2015-08-24 事件上市股配息缺；adj 沒有這檔 ⇒ 當成沒有除息（0）",
         "財報可得日：t57sb01 上傳時戳（seq352）；沒時戳（2013、2014 全部）用法定期限（偏晚）",
         "主出場「加權收盤收復事件前一日收盤 ⇒ 隔天開盤賣」不設天數；成本 0.585% 來回；未含滑價"]
LOG = []


def log(s):
    print(s, flush=True); LOG.append(s)


# ═════════════ 財報 ═════════════
def load_fin():
    F = []
    for f in sorted(glob.glob(os.path.join(XD, "mops", "fin_hist", "*.csv"))):
        x = pd.read_csv(f, dtype={"stock_id": str})
        x["_r"] = (x["report"] != "cr").astype(int)
        F.append(x[["stock_id", "period", "industry", "_r", "rev_ytd", "gp_ytd", "nip_ytd", "ni_ytd", "equity_parent", "equity_total", "assets",
                    "liabilities", "ocf_ytd"]])
    F = pd.concat(F).sort_values(["stock_id", "period", "_r"]).drop_duplicates(["stock_id", "period"], keep="first").drop(columns="_r")
    X = []
    for f in sorted(glob.glob(os.path.join(XD, "meta", "fs_xbrl", "fs_xbrl_*.csv"))):
        x = pd.read_csv(f, dtype={"stock_id": str})
        x["_r"] = (x["report"] != "cr").astype(int)
        x = x.sort_values(["stock_id", "period", "_r"]).drop_duplicates(["stock_id", "period"], keep="first")
        X.append(x[["stock_id", "period", "total_assets", "total_equity", "operating_cash_flow_ytd"]])
    X = pd.concat(X)
    M = F.merge(X, on=["stock_id", "period"], how="outer")
    for c in ["rev_ytd", "gp_ytd", "nip_ytd", "ni_ytd", "equity_parent", "equity_total", "assets", "liabilities", "ocf_ytd", "total_assets", "total_equity",
              "operating_cash_flow_ytd"]:
        M[c] = pd.to_numeric(M[c], errors="coerce")
    M["y"] = M["period"].str[:4].astype(int); M["q"] = M["period"].str[-1].astype(int); M["qk"] = [FU.qkey(a, b) for a, b in zip(M["y"], M["q"])]
    # 負債比
    db = M["liabilities"] / M["assets"]
    db = db.where(np.isfinite(db) & (M["assets"] > 0), 1 - M["equity_total"] / M["assets"])
    db = db.where(np.isfinite(db) & (M["assets"] > 0), 1 - M["total_equity"] / M["total_assets"])
    M["debt"] = db.where(np.isfinite(db))
    M["debt_src"] = np.where(np.isfinite(M["liabilities"] / M["assets"]) & (M["assets"] > 0), "fin_hist負債÷資產",
                             np.where(np.isfinite(1 - M["equity_total"] / M["assets"]) & (M["assets"] > 0), "fin_hist 1−權益÷資產",
                                      np.where(M["debt"].notna(), "fs_xbrl 1−權益÷資產", "缺")))
    M["ocf"] = M["ocf_ytd"].where(M["ocf_ytd"].notna(), M["operating_cash_flow_ytd"])
    # 可得日
    fd = pd.read_csv(os.path.join(XD, "meta", "filing_dates.csv"), dtype=str)
    fd["d"] = pd.to_datetime(fd["uploaded_at"].astype(str).str[:10], errors="coerce"); fd = fd.dropna(subset=["d"])
    fd["qk"] = [FU.qkey(a, b) for a, b in zip(fd["year"], fd["season"])]
    fmin = fd.groupby(["stock_id", "qk"])["d"].min()
    dl = {1: (5, 15), 2: (8, 14), 3: (11, 14)}
    av = []; src = []
    for s, k, y, q in zip(M["stock_id"], M["qk"], M["y"], M["q"]):
        t = fmin.get((s, k))
        if t is not None and pd.notna(t):
            av.append(t); src.append("t57sb01")
        else:
            av.append(pd.Timestamp(year=y + 1, month=3, day=31) if q == 4 else pd.Timestamp(year=y, month=dl[q][0], day=dl[q][1])); src.append("法定期限")
    M["avail"] = pd.to_datetime(av); M["avail_src"] = src
    out = {}
    for s, g in M.groupby("stock_id"):
        g = g.set_index("qk").sort_index()
        g = pd.DataFrame(index=np.arange(g.index.min(), g.index.max() + 1)).join(g)
        q = (g.index.to_numpy() % 4) + 1
        for c in ["rev_ytd", "gp_ytd", "nip_ytd", "ni_ytd", "ocf"]:
            v = g[c].to_numpy(float); pv = np.r_[np.nan, v[:-1]]
            g[c + "_q"] = np.where(q == 1, v, v - pv)
        ep = g["equity_parent"].to_numpy(float); et = g["equity_total"].to_numpy(float)
        rp = np.where(ep > 0, g["nip_ytd_q"].to_numpy(float) / np.where(ep > 0, ep, 1), np.nan)
        rt = np.where(et > 0, g["ni_ytd_q"].to_numpy(float) / np.where(et > 0, et, 1), np.nan)
        roe = 4 * np.where(np.isfinite(rp), rp, rt)
        rv = g["rev_ytd_q"].to_numpy(float); gp = g["gp_ytd_q"].to_numpy(float)
        gm = np.where((rv > 0) & np.isfinite(gp), gp / np.where(rv > 0, rv, 1), np.nan)
        out[s] = {"qk": g.index.to_numpy(), "avail": g["avail"].to_numpy("datetime64[ns]"), "src": g["avail_src"].to_numpy(object),
                  "has": (g["rev_ytd"].notna() | g["ni_ytd"].notna() | g["assets"].notna()).to_numpy(),
                  "roe": roe, "gm": gm, "debt": g["debt"].to_numpy(float), "debt_src": g["debt_src"].fillna("缺").to_numpy(object),
                  "ocf_q": g["ocf_q"].to_numpy(float), "ind": g["industry"].ffill().bfill().to_numpy(object)}
    nts = int((M["avail_src"] == "t57sb01").sum())
    info = {"季列": int(len(M)), "有t57sb01時戳": nts, "無時戳": int(len(M) - nts),
            "無時戳占比（依年）": {int(k): round(float(v), 3) for k, v in M.groupby("y")["avail_src"].apply(lambda z: (z == "法定期限").mean()).items()},
            "負債比來源": M["debt_src"].value_counts().to_dict()}
    return out, info


def fin_q(g, t):
    f = {k: np.nan for k in ["q_roe_m", "q_roe_s", "q_gm_s", "q_debt", "q_ocf"]}
    f.update({"q_finq": None, "q_finsrc": None, "q_nroe": 0, "q_ngm": 0, "q_debtsrc": None, "q_ind": None})
    j, src = FU.fin_latest(g, t)
    if j is None:
        return f
    k = int(g["qk"][j]); f["q_finq"] = f"{k // 4}Q{k % 4 + 1}"; f["q_finsrc"] = src; f["q_ind"] = g["ind"][j]
    lo = max(0, j - 11)
    r = g["roe"][lo:j + 1]; r = r[np.isfinite(r)]; f["q_nroe"] = int(len(r))
    if len(r) >= MINQ:
        f["q_roe_m"] = float(r.mean()); f["q_roe_s"] = float(r.std(ddof=1))
    m = g["gm"][lo:j + 1]; m = m[np.isfinite(m)]; f["q_ngm"] = int(len(m))
    if len(m) >= MINQ:
        f["q_gm_s"] = float(m.std(ddof=1))
    if np.isfinite(g["debt"][j]):
        f["q_debt"] = float(g["debt"][j]); f["q_debtsrc"] = g["debt_src"][j]
    if j >= 3:
        o = g["ocf_q"][j - 3:j + 1]
        if np.isfinite(o).all():
            f["q_ocf"] = float(o.sum() > 0)
    return f


# ═════════════ 配息（data/adj 除息）═════════════
def load_div():
    I = pd.read_csv(os.path.join(ADJ, "_index.csv"), dtype=str)
    mk = dict(zip(I["stock_id"], I["market"]))
    DV = {}
    for s in I["stock_id"]:
        fp = os.path.join(ADJ, f"{s}.csv")
        if not os.path.exists(fp):
            continue
        x = pd.read_csv(fp, dtype=str)
        x = x[x["kind"].astype(str).str.contains("息")]
        DV[s] = pd.to_datetime(x["date"]).to_numpy("datetime64[ns]")
    sm = pd.read_csv(os.path.join(FU.FDATA, "meta", "stocks.csv"), dtype=str).drop_duplicates("stock_id", keep="last")
    smk = dict(zip(sm["stock_id"], sm["market"]))
    return DV, mk, smk


def div_q(DV, mk, smk, sid, t):
    """⇒ (值, 註)"""
    Y = t.year
    market = mk.get(sid) or smk.get(sid, "twse")
    start = TWSE_ADJ0 if market == "twse" else TPEX_ADJ0
    if Y - 3 < start:
        return np.nan, f"缺（{market} adj {start} 起）"
    d = DV.get(sid)
    if d is None:
        return 0.0, "adj無此檔⇒0"
    d = d[d < np.datetime64(t)]
    yrs = set(pd.DatetimeIndex(d).year)
    ok = all(y in yrs for y in (Y - 3, Y - 2, Y - 1))
    return float(ok), "adj"


def add_q(d, key):
    for s in SUBS:
        v = -d[s] if s in LOWGOOD else d[s]
        d["p_" + s] = v.groupby(d[key]).rank(pct=True, method="average").fillna(0.0)
    d["Q"] = d[["p_" + s for s in SUBS]].sum(axis=1) / len(SUBS)
    d["q_nmiss"] = d[SUBS].isna().sum(axis=1)
    return d


def order(d):
    return d.sort_values("sid", kind="mergesort").sort_values("Q", ascending=False, kind="mergesort")


def stats(x):
    return FU.stats(x)


def main():
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    pd.set_option("display.width", 260); pd.set_option("display.max_rows", 900); pd.set_option("display.max_columns", 40)
    ALL = pd.read_csv(os.path.join(FD, "features.csv"), dtype={"sid": str})
    ALL["買得到"] = ALL["買得到"].astype(str).str.lower().eq("true")
    evs_all = sorted(ALL["事件日"].unique()); seg_of = ALL.drop_duplicates("事件日").set_index("事件日")["段"].to_dict()
    assert len(evs_all) == 28 and len(ALL) == 1402
    evs = [e for e in evs_all if seg_of[e] != "2006～2014"]; assert len(evs) == 18
    segev = {"2015～2021": [e for e in evs if seg_of[e] == "2015～2021"], "2022～": [e for e in evs if seg_of[e] == "2022～"], "2015～（18事件）": evs}
    CP = ALL[ALL["事件日"].isin(evs)].copy()
    log(f"[讀檔] fund/features.csv C+ {len(ALL)} 列 28 事件；2015 起 {len(CP)} 列 {len(evs)} 事件（2015～2021 {len(segev['2015～2021'])}、2022～ {len(segev['2022～'])}）")
    # ── 對照（同 fund）──
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
    # ── Q 子項 ──
    FIN, finfo = load_fin(); log(f"[財報] {finfo}")
    DV, mk, smk = load_div(); log(f"[配息] adj 有除息紀錄 {len(DV)} 檔（含 ETF 等）")
    FQ = pd.DataFrame([fin_q(FIN.get(s), pd.Timestamp(e)) for s, e in zip(CP["sid"], CP["事件日"])], index=CP.index)
    for c in FQ.columns:
        CP[c] = FQ[c]
    dv = [div_q(DV, mk, smk, s, pd.Timestamp(e)) for s, e in zip(CP["sid"], CP["事件日"])]
    CP["q_div"] = [x[0] for x in dv]; CP["q_divsrc"] = [x[1] for x in dv]
    log("[配息來源] " + str(CP.groupby("段")["q_divsrc"].value_counts().to_dict()))
    CP = add_q(CP, "事件日")
    # ── 缺值 ──
    MS = []
    for sg, es in segev.items():
        q = CP[CP["事件日"].isin(es)]
        for s in SUBS:
            MS.append({"段": sg, "子項": s, "名稱": SUBNAME[s], "C+列數": len(q), "缺值比例": float(q[s].isna().mean())})
        MS.append({"段": sg, "子項": "全缺", "名稱": "6 子項全缺（Q＝0）", "C+列數": len(q), "缺值比例": float((q["q_nmiss"] == 6).mean())})
        MS.append({"段": sg, "子項": "任一缺", "名稱": "至少缺 1 子項", "C+列數": len(q), "缺值比例": float((q["q_nmiss"] > 0).mean())})
    for e in evs:
        q = CP[CP["事件日"] == e]
        MS.append({"段": e, "子項": "各事件平均缺值子項數", "名稱": "", "C+列數": len(q), "缺值比例": float(q["q_nmiss"].mean() / 6)})
    MS = pd.DataFrame(MS); MS.to_csv(os.path.join(OUT, "missing.csv"), index=False, float_format="%.4g", encoding="utf-8")
    log("[缺值]\n" + MS[MS["段"].isin(SEGS)].pivot_table(index=["子項", "名稱"], columns="段", values="缺值比例", sort=False).to_string(float_format=lambda v: f"{v:.3f}"))
    log("[各事件平均缺值比例] " + "、".join(f"{r['段']} {r['缺值比例']:.2f}" for _, r in MS[MS["子項"] == "各事件平均缺值子項數"].iterrows()))
    # ── 與 F6／F7 的關係 ──
    rel = {}
    for oth in ("F6", "F7"):
        rh = [float(g["Q"].rank().corr(g[oth].rank())) for _, g in CP.groupby("事件日")]
        rel[f"Q vs {oth} 事件內 Spearman 平均"] = float(np.mean(rh))
    log(f"[Q 與 F6／F7 名次相關] {rel}")
    # ── 挑檔 ──
    EP = []; picks = {}
    for ev in evs:
        d = CP[CP["事件日"] == ev]; o = order(d)
        for N in (1, 2, 3):
            pk = o.head(N); nb = pk[pk["買得到"]]
            ret = float(nb["淨報酬"].mean()) if len(nb) else 0.0
            picks[(ev, "Q", N)] = list(pk["sid"])
            EP.append({"段": seg_of[ev], "事件日": ev, "分數": "Q", "N": N, "C+檔數": len(d), "選中": " ".join(pk["sid"]),
                       "選中Q": " ".join(f"{x:.3f}" for x in pk["Q"]), "選中缺值子項數": " ".join(str(int(x)) for x in pk["q_nmiss"]),
                       "買到檔數": len(nb), "空手": len(nb) == 0, "報酬": ret,
                       "選中各檔報酬": " ".join(f"{x:.4f}" if b else "買不到" for x, b in zip(pk["淨報酬"], pk["買得到"]))})
    FE = pd.read_csv(os.path.join(FD, "event_picks.csv"), dtype={"選中": str}); FE = FE[FE["分數"].isin(["F6", "F7"])]
    F8E = pd.read_csv(os.path.join(F8D, "event_picks.csv"), dtype={"選中": str}); F8E = F8E[F8E["分數"] == "F8"]
    for X_ in (FE, F8E):
        for _, r in X_[X_["事件日"].isin(evs)].iterrows():
            picks[(r["事件日"], r["分數"], int(r["N"]))] = str(r["選中"]).split()
            EP.append({"段": r["段"], "事件日": r["事件日"], "分數": r["分數"], "N": int(r["N"]), "C+檔數": int(r["C+檔數"]), "選中": str(r["選中"]),
                       "買到檔數": int(r["買到檔數"]), "空手": str(r["空手"]).lower() == "true", "報酬": float(r["報酬"]),
                       "選中各檔報酬": r["選中各檔報酬"]})
    EP = pd.DataFrame(EP)
    # 對帳：F6／F7／F8 報酬由 features 重算
    nret = CP.set_index(["事件日", "sid"])
    mx = 0.0
    for _, r in EP[EP["分數"] != "Q"].iterrows():
        rows = nret.loc[[(r["事件日"], s) for s in r["選中"].split()]]
        b = rows[rows["買得到"]]; v = float(b["淨報酬"].mean()) if len(b) else 0.0
        mx = max(mx, abs(v - r["報酬"]))
    log(f"[對帳] F6／F7／F8 挑檔報酬 由 features 重算 vs event_picks 最大差 {mx:.2e}"); assert mx < 1e-4
    OV = []
    for N in (1, 2, 3):
        for oth in ("F6", "F7", "F8"):
            ov = [len(set(picks[(e, "Q", N)]) & set(picks[(e, oth, N)])) for e in evs]
            OV.append({"N": N, "比較": oth, "完全相同事件數（18）": int(sum(o == N for o in ov)), "平均重疊檔數": float(np.mean(ov)), "至少重疊1檔事件數": int(sum(o > 0 for o in ov))})
    OV = pd.DataFrame(OV); log("[Q 選中與 F6／F7／F8 重疊]\n" + OV.to_string(index=False, float_format=lambda v: f"{v:.2f}"))
    # ── 隨機（同 pick／fund：同種子、同列序、事件序號照 28 事件）──
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
    PR = pd.read_csv(FU.PICKRND); FS = pd.read_csv(os.path.join(FD, "summary.csv")); m1 = 0.0; m2 = 0.0
    for sg in ("2015～2021", "2022～"):
        for N in (1, 2, 3):
            a = float(np.stack([RS[(e, N)] for e in segev[sg]]).mean())
            m1 = max(m1, abs(a - float(PR[(PR["段"] == sg) & (PR["N"] == N)]["平均"].iloc[0])))
            m2 = max(m2, abs(a - float(FS[(FS["段"] == sg) & (FS["方法"] == "隨機") & (pd.to_numeric(FS["N"], errors="coerce") == N)]["平均"].iloc[0])))
    log(f"[對帳] 隨機平均 vs pick/random.csv 最大差 {m1:.2e}；vs fund/summary.csv 最大差 {m2:.2e}"); assert m1 < 1e-5 and m2 < 1e-5
    # ── 彙總 ──
    SUM = [{"段": "2006～2014", "方法": "Q", "名稱": CMPNAME["Q"], "N": "", "事件數": 0, "備註": "缺（10 事件都在 2011-08 以前，財報 2013 起）"}]
    for sg, es in segev.items():
        for cd, nm in (("A", "0050"), ("B", "00631L（正2）"), ("C+全買", "C+ 全部等權")):
            x = np.array([ref[e][cd] for e in es]); x = x[np.isfinite(x)]
            SUM.append({"段": sg, "方法": cd, "名稱": nm, "N": "", **stats(x)})
        for N in (1, 2, 3):
            M_ = np.stack([RS[(e, N)] for e in es]); flat = M_.ravel(); sa = M_.mean(axis=0)
            SUM.append({"段": sg, "方法": "隨機", "名稱": f"C+ 隨機挑 {N} 檔（{NR} 次）", "N": N, "事件數": len(es), "平均": float(flat.mean()),
                        "中位": float(np.median(flat)), "勝率": float((flat > 0).mean()), "最差": float(M_.min(axis=0).mean()),
                        "虧＞10%次數": float((M_ < -0.10).sum(axis=0).mean()),
                        "隨機段平均P10": float(np.quantile(sa, .1)), "隨機段平均P50": float(np.quantile(sa, .5)), "隨機段平均P90": float(np.quantile(sa, .9)),
                        "備註": "最差、虧＞10%次數 ＝ 每輪段內值的平均"})
            for sc in CMP:
                q = EP[(EP["分數"] == sc) & (EP["N"] == N)].set_index("事件日").loc[es]
                x = q["報酬"].to_numpy(float); s = stats(x); cpa = np.array([ref[e]["C+全買"] for e in es])
                SUM.append({"段": sg, "方法": sc, "名稱": CMPNAME[sc], "N": N, **s, "空手事件數": int(q["空手"].sum()),
                            "隨機段平均P10": float(np.quantile(sa, .1)), "隨機段平均P50": float(np.quantile(sa, .5)), "隨機段平均P90": float(np.quantile(sa, .9)),
                            "隨機中位置（百分位）": float((sa < s["平均"]).mean()), "p（隨機≥分數）": float((sa >= s["平均"]).mean()),
                            "勝過C+全買事件數": int((x > cpa).sum()),
                            "勝過A事件數": int(sum(1 for e, v in zip(es, x) if np.isfinite(ref[e]["A"]) and v > ref[e]["A"])),
                            "勝過A可比事件數": int(sum(1 for e in es if np.isfinite(ref[e]["A"])))})
    SUM = pd.DataFrame(SUM)
    m3 = 0.0
    for _, r in SUM[SUM["方法"].isin(["F6", "F7"]) & SUM["段"].isin(["2015～2021", "2022～"])].iterrows():
        f = FS[(FS["段"] == r["段"]) & (FS["方法"] == r["方法"]) & (pd.to_numeric(FS["N"], errors="coerce") == r["N"])].iloc[0]
        m3 = max(m3, abs(float(f["平均"]) - r["平均"]), abs(float(f["隨機中位置（百分位）"]) - r["隨機中位置（百分位）"]))
    log(f"[對帳] F6／F7 彙總（平均、隨機百分位）vs fund/summary.csv 最大差 {m3:.2e}"); assert m3 < 1e-4
    SUM.to_csv(os.path.join(OUT, "summary.csv"), index=False, float_format="%.6g", encoding="utf-8")
    EP.to_csv(os.path.join(OUT, "event_picks.csv"), index=False, float_format="%.6g", encoding="utf-8")
    cols = ["段", "方法", "N", "事件數", "平均", "中位", "勝率", "最差", "虧＞10%次數", "隨機中位置（百分位）", "勝過C+全買事件數", "勝過A事件數"]
    log("[彙總]\n" + SUM[cols].to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    # ── 五分位 ──
    QT, QX = quintiles(CP, segev)
    QT.to_csv(os.path.join(OUT, "quintile.csv"), index=False, float_format="%.6g", encoding="utf-8")
    QX.to_csv(os.path.join(OUT, "quintile_mono.csv"), index=False, float_format="%.6g", encoding="utf-8")
    log("[Q 五分位]\n" + QT.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    log("[Q 單調／Q5−Q1]\n" + QX.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    keep = ["段", "事件日", "sid", "買得到", "淨報酬", "q_finq", "q_finsrc", "q_ind", "q_nroe", "q_ngm", "q_debtsrc", "q_divsrc"] + SUBS + \
           ["p_" + s for s in SUBS] + ["q_nmiss", "Q", "F6", "F7"]
    CP[keep].to_csv(os.path.join(OUT, "features.csv"), index=False, float_format="%.6g", encoding="utf-8")
    FW = forward(FIN, DV, mk, smk)
    S = {"程式": "backtest/researchMktDrop_quality.py", "時間（台北）": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M"), "讀法": __doc__, "註": NOTES,
         "子項": SUBNAME, "財報": finfo, "Q與F6F7相關": rel, "重疊": OV.to_dict("records"), "summary": SUM.replace({np.nan: None}).to_dict("records"),
         "quintile": QT.replace({np.nan: None}).to_dict("records"), "單調": QX.replace({np.nan: None}).to_dict("records"),
         "missing": MS.to_dict("records"), "forward_20261015": FW, "耗時秒": round(time.time() - T0, 1)}
    with open(os.path.join(OUT, "MktDrop_quality.json"), "w", encoding="utf-8") as f:
        json.dump(S, f, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    with open(os.path.join(OUT, "run.log"), "w", encoding="utf-8") as f:
        f.write("\n".join(LOG) + "\n")


def quintiles(CP, segev):
    G = {}
    for ev in sorted(CP["事件日"].unique()):
        d = order(CP[CP["事件日"] == ev]).reset_index(drop=True); n = len(d)
        d["Qg"] = 5 - (np.arange(n) * 5 // n)
        b = d[d["買得到"]]
        qm = np.array([b[b["Qg"] == q]["淨報酬"].mean() if (b["Qg"] == q).any() else np.nan for q in range(1, 6)])
        rho = float(b["Q"].rank().corr(b["淨報酬"].rank())) if len(b) >= 5 else np.nan
        G[ev] = (qm, rho, b.groupby("Qg")["淨報酬"].agg(["sum", "count"]).reindex(range(1, 6)).fillna(0).to_numpy())
    rows = []; X = []
    for si, (sg, es) in enumerate(segev.items()):
        QM = np.stack([G[e][0] for e in es]); E = len(es)
        rng = np.random.default_rng([QSEED, si]); ix = rng.integers(0, E, (NBOOT, E))
        SCt = np.stack([G[e][2] for e in es])
        for q in range(5):
            v = QM[:, q]; ok = np.isfinite(v)
            bm = np.array([np.nanmean(v[r]) for r in ix])
            rows.append({"段": sg, "組": f"Q{q + 1}" + ("（高分）" if q == 4 else ("（低分）" if q == 0 else "")), "事件數": int(ok.sum()),
                         "檔次": int(SCt[:, q, 1].sum()), "事件等權平均": float(np.nanmean(v)), "CI95低": float(np.nanpercentile(bm, 2.5)),
                         "CI95高": float(np.nanpercentile(bm, 97.5)), "檔次合併平均": float(SCt[:, q, 0].sum() / max(SCt[:, q, 1].sum(), 1)),
                         "事件組平均＞0比例": float(np.mean(v[ok] > 0))})
        dq = QM[:, 4] - QM[:, 0]; okd = np.isfinite(dq)
        bd = np.array([np.nanmean(dq[r]) for r in ix]); rh = np.array([G[e][1] for e in es], float)
        mq = np.nanmean(QM, axis=0)
        X.append({"段": sg, "事件數": E, "Q1": mq[0], "Q2": mq[1], "Q3": mq[2], "Q4": mq[3], "Q5": mq[4],
                  "Q5−Q1": float(np.nanmean(dq)), "Q5−Q1 CI95低": float(np.nanpercentile(bd, 2.5)), "Q5−Q1 CI95高": float(np.nanpercentile(bd, 97.5)),
                  "Q5＞Q1 事件比例": float(np.mean(dq[okd] > 0)), "Spearman 事件平均": float(np.nanmean(rh)),
                  "Spearman＞0 事件比例": float(np.mean(rh[np.isfinite(rh)] > 0)), "五組單調遞增": bool(np.all(np.diff(mq) > 0)),
                  "五組單調遞減": bool(np.all(np.diff(mq) < 0))})
    return pd.DataFrame(rows), pd.DataFrame(X)


def forward(FIN, DV, mk, smk):
    W = pd.read_csv(os.path.join(FD, "forward_20261015_features.csv"), dtype={"sid": str})
    assert len(W) == 75
    t = pd.Timestamp("2026-10-15")
    FQ = pd.DataFrame([fin_q(FIN.get(s), t) for s in W["sid"]], index=W.index)
    for c in FQ.columns:
        W[c] = FQ[c]
    dv = [div_q(DV, mk, smk, s, t) for s in W["sid"]]
    W["q_div"] = [x[0] for x in dv]; W["q_divsrc"] = [x[1] for x in dv]
    W = add_q(W, "事件日")
    log("[10/15 缺值比例] " + ", ".join(f"{s} {W[s].isna().mean():.2f}" for s in SUBS) + f"；財報季 {W['q_finq'].value_counts().to_dict()}；配息來源 {W['q_divsrc'].value_counts().to_dict()}")
    F8 = pd.read_csv(os.path.join(F8D, "forward_20261015.csv"), dtype={"代號": str})
    W["r6"] = W["F6"].rank(pct=True) * 100; W["r7"] = W["F7"].rank(pct=True) * 100; W["F8"] = W["r6"] + W["r7"]
    o = order(W).reset_index(drop=True); o["Q名次"] = np.arange(1, len(o) + 1)
    rk = {}
    for sc in ("F6", "F7"):
        lst = FU.order(W, sc)["sid"].tolist(); rk[sc] = {s: lst.index(s) + 1 for s in lst}
    lst8 = W.sort_values("sid", kind="mergesort").sort_values(["F8", "F7"], ascending=[False, False], kind="mergesort")["sid"].tolist()
    assert lst8[:10] == F8["代號"].tolist()[:10], "F8 前 10 與 f8/forward 不符"
    rk["F8"] = {s: lst8.index(s) + 1 for s in lst8}
    for sc in ("F6", "F7", "F8"):
        o[f"{sc}名次"] = [rk[sc][s] for s in o["sid"]]
    cols = ["Q名次", "sid", "名稱", "Q", "q_roe_m", "q_roe_s", "q_gm_s", "q_debt", "q_ocf", "q_div", "q_nmiss", "q_finq", "q_ind", "F6名次", "F7名次", "F8名次", "ret1"]
    fw = o[cols].rename(columns={"sid": "代號", "ret1": "當日報酬", "q_finq": "財報季", "q_ind": "財報產業別", "q_nmiss": "缺值子項數"})
    fw.to_csv(os.path.join(OUT, "forward_20261015.csv"), index=False, float_format="%.6g", encoding="utf-8")
    log("[10/15 Q 前 10]\n" + fw.head(10).to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    top = {}
    for sc in ("F6", "F7", "F8"):
        ids = [s for s, r in sorted(rk[sc].items(), key=lambda z: z[1])[:3]]
        top[sc] = [{"代號": s, "Q名次": int(o.loc[o["sid"] == s, "Q名次"].iloc[0]), "Q": float(o.loc[o["sid"] == s, "Q"].iloc[0])} for s in ids]
    log(f"[10/15 F6／F7／F8 前 3 在 Q 的名次（75 檔）] {top}")
    return {"前10": fw.head(10).replace({np.nan: None}).to_dict("records"), "F6F7F8前3在Q名次": top,
            "缺值比例": {s: float(W[s].isna().mean()) for s in SUBS}}


if __name__ == "__main__":
    main()
