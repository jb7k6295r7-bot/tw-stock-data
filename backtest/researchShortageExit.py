# -*- coding: utf-8 -*-
"""缺貨型持股「確認後」怎麼賣 seq1【正式跑】（台股策略線 登錄 sha 2b3c853a8290be22；裁定 seq447 §一 發號、seq448 §一 核准開跑：
C6 依構造不可判定、標「還沒測」、N_單筆 ＋6、Bonferroni 6 格（雙尾 99.17%）、C6 確認段只描述；C7 照跑照報退化、探索段可判部分 n_eff ＜ 24 ⇒ 還沒測；
C1 結果句附分月觸發率與「C1 主要是 2 月（過年）觸發」；族群只描述；250 日重疊 ⇒ 最多暫定；賣掉的錢不計）——回測線計算子代理。
⛔ 不 commit、不改既有檔；researchShortageExit_freq（頻率表，⛔ 只 import）、researchRevTurn_freq（prices 等共用）、research11（cl_stats）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchShortageExit --sha <頻率表同一版> [--procs 3]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchShortageExit_check
輸出 backtest/resultsShortageExit/main/：main.json、cells.csv（判定 6 格＋C6 描述）、desc.csv（段×母體×E×賣法）、group12.csv（不重疊起點第二欄）、
     yearly.csv、after.csv（賣後走勢）、events_R.csv.gz（逐事件各賣法 R 與 d）、run.log

═══ 讀法（M 標；頻率表讀法 S0～S6 原樣沿用；以下為正式跑新增；⛔ 在讀任何本件報酬之前寫死於 2026-10-22（台北）；★＝執行者定）═══
 M1 事件與觸發 ＝ 頻率表：本程式先以 researchShortageExit_freq.main 原樣（同一 --sha）重建到 ~/rtfwork/rebuild_sx，events.csv.gz、counts.csv、freq_段.csv
    與已 commit 的 resultsShortageExit/freq 逐字比，任一不同 ⇒ 中止、⛔ 不算報酬。
 M2 價格：進場價 P0 ＝ e 的還原開盤；賣出價 ＝ s 的還原開盤（頻率表 s 偏移；s ≤ E_eff 才算賣）；不賣 ＝ E_eff 當天或之前最後一根有效 K 棒的還原收盤；
    E_eff ＝ 頻率表 S2（壞根截斷 ⇒ 第一個壞根前一根；下市 ⇒ 最後有效 K 棒）。★ 合併日曆的主世界還原開盤乘上與收盤相同的接縫倍數（TopSell merged_prices
    只把收盤乘 M；本件跨 2014→2015 的持有要用同一倍數，否則開、收不同基準），倍數 ＝ 合併後收盤 ÷ 主世界面板收盤（該檔主世界第一根）。
 M3 R ＝ 出場價 ÷ P0 − 1 − 0.4425%（賣出一次；各賣法同計，含不賣 ⇒ d 中相消）；d_k ＝ R(Ck) − R(C0)，同一事件配對。
    另報滑價（每邊 +0.5%：P0×1.005、出場價×0.995）版 d（描述）。同根兩出場價取較低（seq373）：每法每筆只有一個賣價 ⇒ 不適用。
 M4 判定（登錄 §五 ＋ seq448）：缺貨型、E＝250、判定 6 格 C1～C5、C7；段 ＝ 探索 2006-04～2015-12、確認 2016-01～（依進場日、E 走得完）。
    CI ＝ research11.cl_stats 同式按進場月分群（se ＝ √Σ(月內離差和)² ÷ n），Bonferroni 6 格 ⇒ z ＝ Φ⁻¹(1 − 0.05/12) ＝ 2.638（雙尾 99.17%）。
    兩段平均 d 皆 ＞ 0 ∧ 確認段 Bonferroni CI 下界 ＞ 0 ⇒「Ck 比不賣有利（暫定）」；兩段皆 ＜ 0 ∧ 確認段上界 ＜ 0 ⇒「Ck 比不賣差（暫定）」；其他 ⇒「分不出」；
    任一段 n_eff（進場月數）＜ 24 ⇒「還沒測」。★ C7 另以「該段 C7 至少一個季判點可判的事件」算 n_eff（seq448「探索段可判部分」），＜ 24 ⇒ 還沒測。
    C6 ＝「還沒測（依構造不可判定：探索段 0% 可判）」，確認段 d 只描述。
 M5 第二欄（只描述）：段內進場月依（月序 mod 12）分 12 組（同一組相鄰起點相隔 12 個月 ⇒ 250 日持有不重疊），每組 d 平均 ⇒ 報 12 組的中位、最小、最大、＞0 組數。
 M6 描述（不判）：一般股同表、缺貨型 − 一般股 差；族群三組；E＝120／500；早於探索段（2004-03～2006-03）；平均與中位並報；分年（進場年）d 平均；
    賣後走勢（E250、賣出者）：賣出後到 E_eff 的最高還原收盤 ≥ 賣出價 × 1.2 的比例（賣太早）、E_eff 收盤 ＜ 賣出價的比例（賣對）；
    C1 分月觸發率 ＝ 頻率表 c1_month.csv／c1_first_month.csv 原值引用。
 M7 先驗（登錄 §十，寫死不改）：① 7 格「比不賣有利」≤ 1 格 ⇒ ★ 以判定 6 格計；② C4、C5 比不賣差或分不出；
    ③ 營收類（C1～C3）在缺貨型比在一般股相對好 ★ ＝ 兩段的 C1～C3 平均 d（缺貨型 − 一般股）皆 ＞ 0；④ C6 多數事件判不了 ＝ 頻率表 judge（探索段 0%）。
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import shutil
import sys
import time
from statistics import NormalDist

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchShortageExit_freq as SX        # noqa: E402
from backtest import researchRevTurn_freq as RT             # noqa: E402
from backtest import researchIndMom_freq as IMF             # noqa: E402
from backtest import research11 as R                        # noqa: E402

OUT = "backtest/resultsShortageExit/main"
FREQ = SX.OUT
REB = os.path.join(RT.WORK, "rebuild_sx")
COST = 0.004425
SLIP = 0.005
CELLS = ["C1", "C2", "C3", "C4", "C5", "C7"]
NB = 6
ZB = NormalDist().inv_cdf(1 - 0.05 / (2 * NB))
NEFF_MIN = 24
SEGJ = ["探索", "確認"]
NOTES = ["只看這一筆，沒算賣掉的錢拿去做什麼", "缺貨型以產業別代理（塑膠、鋼鐵等八業），不是逐檔判定的缺貨",
         "持有 250 日、月與月不獨立 ⇒ 月分群 CI 偏窄 ⇒ 結論最多「暫定」", "C6 依構造不可判定（探索段 0% 可判）⇒ 還沒測；確認段只描述",
         "C1 主要是 2 月（過年）觸發", "族群名單是事後挑的（台股策略線 10/20 十條供應鏈），只描述",
         "2015～2018 下市 58 家月營收補不回（存活者偏差）；早年上櫃 2007-07 前無價", "同根兩出場價取較低（seq373）：每法每筆只有一個賣價 ⇒ 不適用"]
LOG = RT.LOG
log = RT.log


def rebuild(sha, procs):
    """M1：頻率表原樣重建到 REB，與已 commit 的 freq 逐字比。"""
    if os.path.isdir(REB):
        shutil.rmtree(REB)
    SX.OUT = REB
    argv = sys.argv
    sys.argv = ["researchShortageExit_freq", "--procs", str(procs), "--sha", sha]
    try:
        SX.main()
    finally:
        sys.argv = argv
    res = {}
    for f in ("events.csv.gz", "counts.csv", "freq_段.csv", "judge.csv", "equiv.csv", "c1_month.csv"):
        a = pd.read_csv(os.path.join(REB, f), dtype=str, keep_default_na=False)
        b = pd.read_csv(os.path.join(FREQ, f), dtype=str, keep_default_na=False)
        res[f] = bool(a.shape == b.shape and (a.columns == b.columns).all() and a.equals(b))
    return res


def seam_open(PX):
    """M2：主世界還原開盤乘接縫倍數（合併收盤 ÷ 主世界面板收盤）。"""
    Zm = IMF.build_panel("主", 2, log)
    NE = PX["NE"]; O = PX["O"].copy(); n = 0
    for i, s in enumerate(PX["SIDS"]):
        if s not in PX["im"]:
            continue
        j = PX["im"][s]
        v = np.flatnonzero(np.isfinite(Zm["C"][j]))
        if not len(v):
            continue
        f = PX["C"][i, NE + v[0]] / Zm["C"][j, v[0]]
        if not np.isfinite(f) or f <= 0:
            raise SystemExit(f"⛔ 接縫倍數不可算 {s}")
        if abs(f - 1) > 1e-12:
            O[i, NE:] *= f; n += 1
    return O, n


def lastvalid_le(VP, i, x):
    vp = VP[i]
    k = int(np.searchsorted(vp, x, "right")) - 1
    return int(vp[k]) if k >= 0 else -1


def cl(x, m, z=1.96):
    x = np.asarray(x, float); m = np.asarray(m)
    if not len(x):
        return {"n": 0, "months": 0}
    s = R.cl_stats(x, m)
    s["lo_b"] = s["mean"] - z * s["se"]; s["hi_b"] = s["mean"] + z * s["se"]
    return s


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); ap.add_argument("--sha", required=True)
    a = ap.parse_args()
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    reg = IMF.reg_check(SX.REG_SHA); log(f"[登錄] {reg}（sha {SX.REG_SHA} 已驗）")
    FJ = json.load(open(os.path.join(FREQ, "freq.json"), encoding="utf-8"))
    if FJ["origin/main"] != a.sha:
        raise SystemExit(f"⛔ --sha {a.sha} ≠ 頻率表 {FJ['origin/main']}")
    same = rebuild(a.sha, a.procs)
    log(f"[M1 重建] {same}")
    if not all(same.values()):
        raise SystemExit(f"⛔ 頻率表重建不同：{same}")
    sha, DN, MD = RT.ensure_data(a.sha)
    PX = RT.prices(sha, DN, a.procs)
    CAL, ix, C, BAD, VP, LASTV = PX["CAL"], PX["ix"], PX["C"], PX["BAD"], PX["VP"], PX["LASTV"]
    CEND = len(CAL) - 1
    O, nseam = seam_open(PX)
    log(f"[M2] 接縫倍數套到主世界開盤：{nseam} 檔")
    EV = pd.read_csv(os.path.join(FREQ, "events.csv.gz"), dtype={"sid": str, "期別": str})
    EV = EV[EV["進場"] == "保留"].reset_index(drop=True)
    rows = []
    for r in EV.itertuples(index=False):
        rd = r._asdict()
        i = ix[rd["sid"]]; e = int(CAL.searchsorted(pd.Timestamp(rd["e"])))
        P0 = O[i, e]
        if not (np.isfinite(P0) and P0 > 0):
            raise SystemExit(f"⛔ 進場價缺 {rd['sid']} {rd['e']}")
        lastv = int(LASTV[i]); delist = (CEND - lastv) >= 5
        for E in SX.ES:
            if not rd[f"E{E}走得完"]:
                continue
            x = e + E
            bb = np.flatnonzero(BAD[i, e + 1:x + 1])
            st = "完整"
            if len(bb):
                x = e + int(bb[0]); st = "壞根截斷"          # 第一個壞根前一根 ＝ e＋1＋bb[0]−1
            if delist and lastv < x:
                x = lastv; st = "下市結算"
            if st != rd[f"E{E}狀態"]:
                raise SystemExit(f"⛔ E_eff 狀態與頻率表不同 {rd['sid']} {rd['e']} E{E}")
            xv = lastvalid_le(VP, i, x)
            PX0 = C[i, xv]
            R0 = PX0 / P0 - 1 - COST
            R0s = PX0 * (1 - SLIP) / (P0 * (1 + SLIP)) - 1 - COST
            row = {"sid": rd["sid"], "期別": rd["期別"], "e": rd["e"], "段": rd["段"], "母體": rd["母體"], "族群": rd["族群"] if isinstance(rd["族群"], str) else "",
                   "進場月": rd["進場月"], "進場年": int(rd["e"][:4]), "E": E, "E狀態": st, "R_C0": R0, "R_C0_滑價": R0s}
            for c in SX.RULES:
                oc = rd[f"{c}_E{E}"]
                if oc == "賣出":
                    s = e + int(rd[f"{c}_s偏移"])
                    ps = O[i, s]
                    if not (np.isfinite(ps) and ps > 0) or s > x:
                        raise SystemExit(f"⛔ 賣出價缺或晚於 E_eff {rd['sid']} {c}")
                    Rk = ps / P0 - 1 - COST; Rks = ps * (1 - SLIP) / (P0 * (1 + SLIP)) - 1 - COST
                    if E == 250:
                        seg = C[i, s:x + 1]; seg = seg[np.isfinite(seg)]
                        row[f"{c}_賣太早"] = bool(len(seg) and seg.max() >= 1.2 * ps)
                        row[f"{c}_賣對"] = bool(PX0 < ps)
                else:
                    Rk, Rks = R0, R0s
                row[f"R_{c}"] = Rk; row[f"d_{c}"] = Rk - R0; row[f"d_{c}_滑價"] = Rks - R0s; row[f"{c}_結果"] = oc
            row["C7可判"] = bool(rd["C7可判點"] > 0)
            rows.append(row)
    RR = pd.DataFrame(rows)
    log(f"[M3] 事件×E {len(RR)}｜{time.time() - t0:.0f}s")
    # ── 判定 6 格（M4）
    J = RR[(RR["母體"] == "缺貨型") & (RR["E"] == 250)]
    cells = []
    for c in SX.RULES:
        st = {}
        for sg in SEGJ:
            d = J[J["段"] == sg]
            st[sg] = cl(d[f"d_{c}"].to_numpy(float), d["進場月"].to_numpy(), ZB)
            st[sg]["n_eff"] = int(d["進場月"].nunique())
            if c == "C7":
                dj = d[d["C7可判"]]
                st[sg]["n_eff_可判部分"] = int(dj["進場月"].nunique()); st[sg]["可判事件"] = int(len(dj))
        ex, cf = st["探索"], st["確認"]
        if c == "C6":
            v = "還沒測（依構造不可判定：探索段 0% 可判）；確認段只描述"
        elif min(ex["n_eff"], cf["n_eff"]) < NEFF_MIN or (c == "C7" and min(ex["n_eff_可判部分"], cf["n_eff_可判部分"]) < NEFF_MIN):
            v = "還沒測（n_eff ＜ 24" + ("，C7 可判部分" if c == "C7" else "") + "）"
        elif ex["mean"] > 0 and cf["mean"] > 0 and cf["lo_b"] > 0:
            v = f"{c} 比不賣有利（暫定）"
        elif ex["mean"] < 0 and cf["mean"] < 0 and cf["hi_b"] < 0:
            v = f"{c} 比不賣差（暫定）"
        else:
            v = f"{c} 跟不賣分不出"
        row = {"賣法": c, "名稱": SX.RNAME[c], "身分": ("描述（還沒測）" if c == "C6" else "判定"), "判定": v}
        for sg in SEGJ:
            s_ = st[sg]
            row.update({f"{sg}_n": s_["n"], f"{sg}_n_eff": s_["n_eff"], f"{sg}_d平均": s_["mean"], f"{sg}_d中位": s_["median"], f"{sg}_d>0比例": s_["win"],
                        f"{sg}_CI95": f"[{s_['lo']:+.4f}, {s_['hi']:+.4f}]", f"{sg}_CI99.17(Bonf6)": f"[{s_['lo_b']:+.4f}, {s_['hi_b']:+.4f}]",
                        f"{sg}_賣出率": float((J[J['段'] == sg][f"{c}_結果"] == "賣出").mean())})
            if c == "C7":
                row[f"{sg}_C7可判事件"] = s_["可判事件"]; row[f"{sg}_C7可判部分n_eff"] = s_["n_eff_可判部分"]
        cells.append(row)
    CE = pd.DataFrame(cells)
    log("[M4 判定] " + "｜".join(f"{r['賣法']}：{r['判定']}" for r in cells))
    # ── 描述表（M6）
    pops = {"缺貨型": RR["母體"] == "缺貨型", "一般股": RR["母體"] == "一般股", **{f"族群:{g}": RR["族群"].str.contains(g) for g in SX.GROUPS}}
    DS = []
    for sg in ["早於探索(不入段)"] + SEGJ:
        for pn, pm in pops.items():
            for E in SX.ES:
                d = RR[(RR["段"] == sg) & pm & (RR["E"] == E)]
                if not len(d):
                    continue
                for c in ["C0"] + SX.RULES:
                    if c == "C0":
                        s_ = cl(d["R_C0"].to_numpy(float), d["進場月"].to_numpy())
                        DS.append({"段": sg, "母體": pn, "E": E, "賣法": "C0(不賣)的R", "n": s_["n"], "n_eff": s_["months"], "平均": s_["mean"], "中位": s_["median"],
                                   "CI95下": s_["lo"], "CI95上": s_["hi"], ">0比例": s_["win"], "滑價版平均": float(d["R_C0_滑價"].mean())})
                        continue
                    s_ = cl(d[f"d_{c}"].to_numpy(float), d["進場月"].to_numpy())
                    DS.append({"段": sg, "母體": pn, "E": E, "賣法": f"{c} d", "n": s_["n"], "n_eff": s_["months"], "平均": s_["mean"], "中位": s_["median"],
                               "CI95下": s_["lo"], "CI95上": s_["hi"], ">0比例": s_["win"], "滑價版平均": float(d[f"d_{c}_滑價"].mean()),
                               "賣出率": float((d[f"{c}_結果"] == "賣出").mean()), "R平均": float(d[f"R_{c}"].mean())})
    DS = pd.DataFrame(DS)
    # 缺貨型 − 一般股
    DF = []
    for sg in SEGJ:
        for c in SX.RULES:
            a_ = DS[(DS["段"] == sg) & (DS["母體"] == "缺貨型") & (DS["E"] == 250) & (DS["賣法"] == f"{c} d")]["平均"].iloc[0]
            b_ = DS[(DS["段"] == sg) & (DS["母體"] == "一般股") & (DS["E"] == 250) & (DS["賣法"] == f"{c} d")]["平均"].iloc[0]
            DF.append({"段": sg, "賣法": c, "缺貨型d平均": a_, "一般股d平均": b_, "缺貨型−一般股": a_ - b_})
    DF = pd.DataFrame(DF)
    # 第二欄（M5）
    G12 = []
    for sg in SEGJ:
        d = J[J["段"] == sg]
        m0 = RT.mnum(sorted(d["進場月"].unique())[0]) if sg == "確認" else RT.mnum("2006-04")
        if sg == "確認":
            m0 = RT.mnum("2016-01")
        g = d.groupby(d["進場月"].map(lambda s: (RT.mnum(s) - m0) % 12))
        for c in SX.RULES:
            v = g[f"d_{c}"].mean()
            G12.append({"段": sg, "賣法": c, "組數": int(len(v)), "組d中位": float(v.median()), "組d最小": float(v.min()), "組d最大": float(v.max()),
                        "＞0組數": int((v > 0).sum()), "各組d": " ".join(f"{x:+.4f}" for x in v.to_numpy())})
    G12 = pd.DataFrame(G12)
    # 分年、賣後走勢
    YR = J.groupby("進場年")[[f"d_{c}" for c in SX.RULES] + ["R_C0"]].mean().reset_index()
    YR["件數"] = J.groupby("進場年").size().to_numpy()
    AF = []
    for sg in SEGJ:
        for pn in ("缺貨型", "一般股"):
            d = RR[(RR["段"] == sg) & (RR["母體"] == pn) & (RR["E"] == 250)]
            for c in SX.RULES:
                s_ = d[d[f"{c}_結果"] == "賣出"]
                AF.append({"段": sg, "母體": pn, "賣法": c, "賣出": len(s_), "賣太早(之後最高≥賣價×1.2)": (float(s_[f"{c}_賣太早"].astype(bool).mean()) if len(s_) else np.nan),
                           "賣對(E收盤＜賣價)": (float(s_[f"{c}_賣對"].astype(bool).mean()) if len(s_) else np.nan)})
    AF = pd.DataFrame(AF)
    # 先驗（M7）
    nwin = int(sum(1 for r in cells if r["身分"] == "判定" and "有利" in r["判定"]))
    p3 = [float(DF[(DF["段"] == sg) & DF["賣法"].isin(["C1", "C2", "C3"])]["缺貨型−一般股"].mean()) for sg in SEGJ]
    PRI = [{"先驗": "① C0 不賣仍排前段，「比不賣有利」≤ 1 格（約七成）", "實際": f"有利 {nwin} 格（判定 6 格）", "中": nwin <= 1},
           {"先驗": "② C4、C5 比不賣差或分不出（約七成五）", "實際": "；".join(r["判定"] for r in cells if r["賣法"] in ("C4", "C5")),
            "中": all("有利" not in r["判定"] for r in cells if r["賣法"] in ("C4", "C5"))},
           {"先驗": "③ 營收類 C1～C3 在缺貨型比在一般股相對好（約五成）", "實際": f"C1～C3 平均 d 差（缺貨型−一般股）探索 {p3[0]:+.4f}、確認 {p3[1]:+.4f}",
            "中": all(x > 0 for x in p3)},
           {"先驗": "④ C6 多數事件判不了（約五成）", "實際": "探索段 0% 可判、確認段 76% 事件至少一個月底可判（頻率表 judge.csv）", "中": True}]
    # 結果句
    C1M = pd.read_csv(os.path.join(FREQ, "c1_month.csv"), encoding="utf-8-sig")
    c1s = C1M[(C1M["母體"] == "缺貨型") & C1M["段"].isin(SEGJ)].pivot_table(index="期別月份", columns="段", values="成立率")
    sent = [f"{r['名稱']}（{r['賣法']}）：{r['判定']}；確認段 d 平均 {r['確認_d平均'] * 100:+.2f} 點 Bonf6 CI {r['確認_CI99.17(Bonf6)']}，探索段 {r['探索_d平均'] * 100:+.2f} 點"
            for r in cells]
    sent.append("C1 分月觸發率（缺貨型，期別月份的條件成立率）：" + "、".join(f"{int(m)} 月 {c1s.loc[m, '探索'] * 100:.0f}%／{c1s.loc[m, '確認'] * 100:.0f}%" for m in c1s.index)
                + "（探索／確認）；C1 主要是 2 月（過年）觸發")
    sent += NOTES
    # 輸出
    RR.to_csv(os.path.join(OUT, "events_R.csv.gz"), index=False, encoding="utf-8-sig", compression="gzip")
    CE.to_csv(os.path.join(OUT, "cells.csv"), index=False, encoding="utf-8-sig")
    DS.to_csv(os.path.join(OUT, "desc.csv"), index=False, encoding="utf-8-sig")
    DF.to_csv(os.path.join(OUT, "diff_pop.csv"), index=False, encoding="utf-8-sig")
    G12.to_csv(os.path.join(OUT, "group12.csv"), index=False, encoding="utf-8-sig")
    YR.to_csv(os.path.join(OUT, "yearly.csv"), index=False, encoding="utf-8-sig")
    AF.to_csv(os.path.join(OUT, "after.csv"), index=False, encoding="utf-8-sig")
    MJ = {"性質": "缺貨型持股確認後怎麼賣 seq1 正式跑（單筆層）", "登錄": f"台股策略線 seq1 sha {SX.REG_SHA}", "裁定": "seq447 §一、seq448 §一（N_單筆 ＋6、Bonferroni 6 格 99.17%）",
          "origin/main": sha, "頻率表重建": same, "接縫開盤倍數檔數": nseam, "z_Bonf6": ZB, "判定": cells, "先驗": PRI, "結果句": sent,
          "缺貨型−一般股": DF.to_dict("records"), "讀法": __doc__.split("═══ 讀法")[1], "秒": round(time.time() - t0)}
    json.dump(MJ, open(os.path.join(OUT, "main.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=RT.jdef)
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    log(f"[完成] {OUT}｜{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
