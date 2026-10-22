# -*- coding: utf-8 -*-
"""營收「轉強」之後是否勝過同類未轉強 seq2【正式跑】（台股策略線 登錄 sha 03f8b072ecfcf67c；裁定 seq447 §三 發號 N_單筆 ＋1、seq448 §二 核准開跑：
兩段可判、最多暫定；結果句加「乙（首創 24 月新高）與 G1 重疊 94%，乙這半幾乎就是 G1」與「與營量／營飆同月重疊 5～12%，不是同一件」；
價量拆分只報兩代理、依構造不可判定；加不重疊起點第二欄）——回測線計算子代理。
⛔ 不 commit、不改既有檔；researchRevTurn_freq（頻率表，⛔ 只 import）、researchShortageExit（seam_open、lastvalid_le、cl）、research11（cl_stats）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchRevTurn --sha <頻率表同一版> [--procs 3]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchRevTurn_check
輸出 backtest/resultsRevTurn/main/：main.json、cells.csv（主格＋H 描述）、split.csv（拆組）、group12.csv（不重疊起點第二欄）、yearly.csv、
     events_R.csv.gz（逐事件 事件 R、對照 R、X、大盤報酬指數 R）、run.log

═══ 讀法（N 標；頻率表讀法 V0～V10 原樣沿用；以下為正式跑新增；⛔ 在讀任何本件報酬之前寫死於 2026-10-22（台北）；★＝執行者定）═══
 N1 事件、配對 ＝ 頻率表：本程式先以 researchRevTurn_freq.main 原樣（同一 --sha）重建到 ~/rtfwork/rebuild_rt，events.csv.gz、freq_段.csv、split.csv、
    overlap.csv 與已 commit 的 resultsRevTurn/freq 逐字比，任一不同 ⇒ 中止、⛔ 不算報酬。
 N2 R（登錄 §二，IndMom I13 同式）：進場 ＝ e 還原開盤（★ 主世界開盤乘接縫倍數，researchShortageExit M2 同式）；出場 x ＝ e ＋ H 收盤；
    (e, x] 有壞根 ⇒ 第一個壞根前一根收盤強制；最後有效 K 棒 ＜ x 且距資料尾 ≥ 5 日 ⇒ 末根收盤（下市）；x 無成交 ⇒ x 之前最後一根收盤。R ＝ 出場 ÷ 進場 − 1。
    對照各檔同式（同一 e、同一 H）。
 N3 主格 X ＝（R事件 − 0.585%）−（對照 R 平均 − 0.585%）★ ＝ R事件 − 對照平均（兩邊都是買得到的股票、成本兩邊都扣 ⇒ 相消）；
    另報「只扣事件一邊」X − 0.585%（描述）。事件等權；月分群 CI ＝ research11.cl_stats（按可用日月份 A 月），N_單筆 ＝ 1 ⇒ z ＝ 1.96。
 N4 判定（登錄 §三）：H＝250；探索 2017-01～2021-12、確認 2022-01～2025-08（依 A）；
    兩段點估計 ＞ 0 ∧ 確認段 CI 下界 ＞ 0 ⇒「轉強後 12 個月比同類沒轉強的好（暫定）」；確認段點估計 ≤ 0 ⇒ 不合格；其餘 ⇒ 測不出；任一段 n_eff ＜ 24 ⇒ 還沒測。
 N5 第二欄（只描述）：段內可用月依（月序 mod 12）分 12 組（同組起點相隔 12 個月 ⇒ 250 日不重疊），每組 X 平均 ⇒ 12 組的中位、最小、最大、＞0 組數。
 N6 描述：H＝60、120；早年 2005～2014；拆組 ①a／①b（代理，不是價量拆分）②③④；事件 R − 大盤報酬指數 R（origin/main data/history/market_tri.csv，
    ★ 只有收盤 ⇒ 指數 R ＝ TRI[x] ÷ TRI[e−1] − 1，合併日曆 ffill）；分年（A 年）X 平均。
 N7 先驗（登錄 §六，寫死不改）：① 主格點估計 ＞ 0 但確認段 CI 含 0；② H＝60 比 H＝250 明顯 ★ ＝ 兩段 H60 的 |t|（X̄ ÷ se）皆 ＞ H250 的 |t|；
    ③ 原物料型代理組比其他組差 ＝ 兩段 X 平均 原物料 ＜ 其他；④ 市值前 30% 組差距較小 ＝ 兩段 |X 平均| 前 30% ＜ 後 70%。
"""
from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchRevTurn_freq as RT             # noqa: E402
from backtest import researchShortageExit as SM             # noqa: E402  seam_open、lastvalid_le、cl
from backtest import researchIndMom_freq as IMF             # noqa: E402

OUT = "backtest/resultsRevTurn/main"
FREQ = RT.OUT
REB = os.path.join(RT.WORK, "rebuild_rt")
COST = 0.00585
SEGJ = ["探索", "確認"]
NOTES = ["這是全市場事件統計，不是 4 檔小部位的表現；4 檔前瞻照跑、條件不改",
         "乙（首創 24 月新高）與 G1 重疊 94%，乙這半幾乎就是 G1",
         "與營量／營飆同月重疊 5～12%，不是同一件",
         "價量拆分依構造不可判定（月營收拆不出價與量），只報兩個代理：原物料型產業 vs 其他、毛利率年增 ＞0／≤0（代理，不是價量拆分）",
         "持有 250 日、月與月不獨立 ⇒ 月分群 CI 偏窄 ⇒ 結論最多「暫定」",
         "配對（同月、同產業、市值十分位、前 12 月三分位）成功約五成，配不到的事件不在主格",
         "2015～2018 下市 58 家月營收補不回（存活者偏差）"]
LOG = RT.LOG
log = RT.log


def rebuild(sha, procs):
    if os.path.isdir(REB):
        shutil.rmtree(REB)
    RT.OUT = REB
    argv = sys.argv
    sys.argv = ["researchRevTurn_freq", "--procs", str(procs), "--sha", sha]
    try:
        RT.main()
    finally:
        sys.argv = argv
        RT.OUT = FREQ
    res = {}
    for f in ("events.csv.gz", "freq_段.csv", "split.csv", "overlap.csv", "yearly.csv", "group12.csv"):
        a = pd.read_csv(os.path.join(REB, f), dtype=str, keep_default_na=False)
        b = pd.read_csv(os.path.join(FREQ, f), dtype=str, keep_default_na=False)
        res[f] = bool(a.shape == b.shape and (a.columns == b.columns).all() and a.equals(b))
    return res


def hold_R(PX, O, i, e, H):
    """N2：回 (R, 狀態)。"""
    C, BAD, LASTV = PX["C"], PX["BAD"], PX["LASTV"]
    CEND = len(PX["CAL"]) - 1
    x = e + H; st = "完整"
    bb = np.flatnonzero(BAD[i, e + 1:x + 1])
    if len(bb):
        x = e + int(bb[0]); st = "壞根強制"
    lv = int(LASTV[i])
    if (CEND - lv) >= 5 and lv < x:
        x = lv; st = "下市末根"
    xv = SM.lastvalid_le(PX["VP"], i, x)
    if xv < e:
        return np.nan, "無出場價"
    if xv != x and st == "完整":
        st = "x無成交"
    return float(C[i, xv] / O[i, e] - 1.0), st


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); ap.add_argument("--sha", required=True)
    a = ap.parse_args()
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    reg = IMF.reg_check(RT.REG_SHA); log(f"[登錄] {reg}（sha {RT.REG_SHA} 已驗）")
    FJ = json.load(open(os.path.join(FREQ, "freq.json"), encoding="utf-8"))
    if FJ["origin/main"] != a.sha:
        raise SystemExit(f"⛔ --sha {a.sha} ≠ 頻率表 {FJ['origin/main']}")
    same = rebuild(a.sha, a.procs)
    log(f"[N1 重建] {same}")
    if not all(same.values()):
        raise SystemExit(f"⛔ 頻率表重建不同：{same}")
    sha, DN, MD = RT.ensure_data(a.sha)
    PX = RT.prices(sha, DN, a.procs)
    CAL, ix = PX["CAL"], PX["ix"]
    CEND = len(CAL) - 1
    O, nseam = SM.seam_open(PX)
    log(f"[N2] 接縫倍數套到主世界開盤：{nseam} 檔")
    tri = pd.read_csv(io.BytesIO(subprocess.run(["git", "show", f"{sha}:data/history/market_tri.csv"], capture_output=True, check=True).stdout))
    tri["date"] = pd.to_datetime(tri["date"]); tri = tri.drop_duplicates("date").set_index("date")["close"].astype(float)
    TRI = tri.reindex(tri.index.union(CAL)).ffill().reindex(CAL).to_numpy(float)
    nfill = int((~CAL.isin(tri.index)).sum())
    EV = pd.read_csv(os.path.join(FREQ, "events.csv.gz"), dtype=str, keep_default_na=False)
    EV = EV[EV["配到"].astype(str) == "True"].reset_index(drop=True)
    rows = []; stc = {}
    for rd in EV.to_dict("records"):                       # ⚠ itertuples 會把「市值前30%」等非識別字欄名改成位置名
        i = ix[rd["sid"]]; e = int(CAL.searchsorted(pd.Timestamp(rd["e"])))
        ctl = [ix[s] for s in rd["對照"].split()]
        for H in RT.HS:
            if str(rd[f"H{H}走得完"]) != "True":
                continue
            Re, se = hold_R(PX, O, i, e, H)
            stc[se] = stc.get(se, 0) + 1
            rc = []
            for j in ctl:
                v, sj = hold_R(PX, O, j, e, H); rc.append(v)
                stc["對照" + sj] = stc.get("對照" + sj, 0) + 1
            rcm = float(np.nanmean(rc)) if np.isfinite(rc).any() else np.nan
            x = e + H
            Ri = TRI[x] / TRI[e - 1] - 1 if (np.isfinite(TRI[x]) and np.isfinite(TRI[e - 1])) else np.nan
            rows.append({"sid": rd["sid"], "期別": rd["期別"], "A": rd["A"], "e": rd["e"], "月": rd["月"], "年": int(rd["年"]), "段": rd["段"], "H": H,
                         "甲": rd["甲"] == "True", "乙": rd["乙"] == "True", "原物料型": rd["原物料型"] == "True", "市值前30%": rd["市值前30%"],
                         "前60日≥中位": rd["前60日≥中位"], "毛利率年增>0": rd["毛利率年增>0"], "對照數": len(ctl),
                         "R事件": Re, "事件出場": se, "R對照平均": rcm, "X": Re - rcm, "X_只扣事件": Re - rcm - COST, "R大盤報酬指數": Ri, "事件−指數": Re - Ri})
    RR = pd.DataFrame(rows)
    log(f"[N2] 事件×H {len(RR)}｜出場狀態 {stc}｜指數補值日 {nfill}｜{time.time() - t0:.0f}s")
    # ── 判定（N4）與 H 描述
    CE = []
    st = {}
    for H in RT.HS:
        for sg in ["早年(描述)"] + SEGJ:
            d = RR[(RR["段"] == sg) & (RR["H"] == H)].dropna(subset=["X"])
            s_ = SM.cl(d["X"].to_numpy(float), d["月"].to_numpy())
            si = SM.cl(d["事件−指數"].dropna().to_numpy(float), d.dropna(subset=["事件−指數"])["月"].to_numpy())
            st[(H, sg)] = s_
            CE.append({"H": H, "段": sg, "身分": ("判定" if (H == 250 and sg in SEGJ) else "描述"), "n": s_["n"], "n_eff": s_.get("months", 0),
                       "X平均": s_.get("mean"), "X中位": s_.get("median"), "X>0比例": s_.get("win"), "se": s_.get("se"), "CI95下": s_.get("lo"), "CI95上": s_.get("hi"),
                       "X只扣事件平均": float(d["X_只扣事件"].mean()) if len(d) else np.nan, "R事件平均": float(d["R事件"].mean()) if len(d) else np.nan,
                       "R對照平均": float(d["R對照平均"].mean()) if len(d) else np.nan, "事件−指數平均": si.get("mean"), "事件−指數CI95": (f"[{si['lo']:+.4f}, {si['hi']:+.4f}]" if si.get("n") else "")})
    CE = pd.DataFrame(CE)
    ex, cf = st[(250, "探索")], st[(250, "確認")]
    if min(ex["months"], cf["months"]) < 24:
        verdict = "還沒測（n_eff ＜ 24）"
    elif ex["mean"] > 0 and cf["mean"] > 0 and cf["lo"] > 0:
        verdict = "合格（暫定）：轉強後 12 個月比同類沒轉強的好（暫定）"
    elif cf["mean"] <= 0:
        verdict = "不合格：確認段點估計 ≤ 0"
    else:
        verdict = "測不出"
    log(f"[N4 判定] {verdict}｜探索 {ex['mean']:+.4f} [{ex['lo']:+.4f}, {ex['hi']:+.4f}] n_eff {ex['months']}｜確認 {cf['mean']:+.4f} [{cf['lo']:+.4f}, {cf['hi']:+.4f}] n_eff {cf['months']}")
    # ── 第二欄（N5）
    G12 = []
    for sg, m0 in (("探索", "2017-01"), ("確認", "2022-01")):
        d = RR[(RR["段"] == sg) & (RR["H"] == 250)].dropna(subset=["X"])
        v = d.groupby(d["月"].map(lambda s: (RT.mnum(s) - RT.mnum(m0)) % 12))["X"].mean()
        G12.append({"段": sg, "組數": int(len(v)), "組X中位": float(v.median()), "組X最小": float(v.min()), "組X最大": float(v.max()), "＞0組數": int((v > 0).sum()),
                    "各組X": " ".join(f"{x:+.4f}" for x in v.to_numpy())})
    G12 = pd.DataFrame(G12)
    # ── 拆組（N6）
    SP = []
    for sg in ["早年(描述)"] + SEGJ:
        d = RR[(RR["段"] == sg) & (RR["H"] == 250)].dropna(subset=["X"])
        groups = [("①a 原物料型代理（代理，不是價量拆分）", "原物料型八業", d["原物料型"]), ("①a 原物料型代理（代理，不是價量拆分）", "其他產業", ~d["原物料型"]),
                  ("①b 毛利率年增代理", "毛利率年增>0", d["毛利率年增>0"] == "True"), ("①b 毛利率年增代理", "毛利率年增≤0（≈轉嫁型）", d["毛利率年增>0"] == "False"),
                  ("①b 毛利率年增代理", "毛利率不可算", d["毛利率年增>0"] == ""),
                  ("② 甲乙", "甲單獨", d["甲"] & ~d["乙"]), ("② 甲乙", "乙單獨", ~d["甲"] & d["乙"]), ("② 甲乙", "甲且乙", d["甲"] & d["乙"]),
                  ("③ 市值", "前30%", d["市值前30%"] == "True"), ("③ 市值", "後70%", d["市值前30%"] == "False"),
                  ("④ 前60日", "≥當日中位", d["前60日≥中位"] == "True"), ("④ 前60日", "＜當日中位", d["前60日≥中位"] == "False")]
        for gname, lab, m in groups:
            dd = d[m.to_numpy(bool)]
            s_ = SM.cl(dd["X"].to_numpy(float), dd["月"].to_numpy())
            SP.append({"段": sg, "拆組": gname, "組": lab, "n": s_["n"], "n_eff": s_.get("months", 0), "X平均": s_.get("mean"), "X中位": s_.get("median"),
                       "CI95下": s_.get("lo"), "CI95上": s_.get("hi")})
    SP = pd.DataFrame(SP)
    YR = RR[(RR["H"] == 250)].dropna(subset=["X"]).groupby("年").agg(件數=("X", "size"), X平均=("X", "mean"), X中位=("X", "median")).reset_index()
    # ── 先驗（N7）
    def tval(H, sg):
        s_ = st[(H, sg)]
        return abs(s_["mean"] / s_["se"]) if s_.get("se") else np.nan
    sp = lambda sg, g: float(SP[(SP["段"] == sg) & (SP["組"] == g)]["X平均"].iloc[0])  # noqa: E731
    PRI = [{"先驗": "① 主格點估計 ＞ 0 但確認段 CI 含 0（約五成）", "實際": f"探索 {ex['mean']:+.4f}、確認 {cf['mean']:+.4f} [{cf['lo']:+.4f}, {cf['hi']:+.4f}]",
            "中": bool(ex["mean"] > 0 and cf["mean"] > 0 and cf["lo"] <= 0 <= cf["hi"])},
           {"先驗": "② H＝60 比 H＝250 明顯（約六成）", "實際": "；".join(f"{sg} |t| H60 {tval(60, sg):.2f}／H250 {tval(250, sg):.2f}" for sg in SEGJ),
            "中": all(tval(60, sg) > tval(250, sg) for sg in SEGJ)},
           {"先驗": "③ 原物料型代理組比其他組差（約六成）", "實際": "；".join(f"{sg} 原物料 {sp(sg, '原物料型八業'):+.4f}／其他 {sp(sg, '其他產業'):+.4f}" for sg in SEGJ),
            "中": all(sp(sg, "原物料型八業") < sp(sg, "其他產業") for sg in SEGJ)},
           {"先驗": "④ 市值前 30% 組差距較小（約六成）", "實際": "；".join(f"{sg} 前30% {sp(sg, '前30%'):+.4f}／後70% {sp(sg, '後70%'):+.4f}" for sg in SEGJ),
            "中": all(abs(sp(sg, "前30%")) < abs(sp(sg, "後70%")) for sg in SEGJ)}]
    sent = [f"營收轉強後 12 個月（H＝250）對同月同產業、市值與前 12 月漲跌相近的未轉強股：{verdict}；"
            f"探索段 X 平均 {ex['mean'] * 100:+.2f} 點（n_eff {ex['months']}）、確認段 {cf['mean'] * 100:+.2f} 點 CI95 [{cf['lo'] * 100:+.2f}, {cf['hi'] * 100:+.2f}]（n_eff {cf['months']}）"] + NOTES
    RR.to_csv(os.path.join(OUT, "events_R.csv.gz"), index=False, encoding="utf-8-sig", compression="gzip")
    CE.to_csv(os.path.join(OUT, "cells.csv"), index=False, encoding="utf-8-sig")
    SP.to_csv(os.path.join(OUT, "split.csv"), index=False, encoding="utf-8-sig")
    G12.to_csv(os.path.join(OUT, "group12.csv"), index=False, encoding="utf-8-sig")
    YR.to_csv(os.path.join(OUT, "yearly.csv"), index=False, encoding="utf-8-sig")
    MJ = {"性質": "營收轉強驗證 seq2 正式跑（事件層主格 1 格）", "登錄": f"台股策略線 seq2 sha {RT.REG_SHA}", "裁定": "seq447 §三、seq448 §二",
          "origin/main": sha, "頻率表重建": same, "接縫開盤倍數檔數": nseam, "出場狀態": stc, "大盤報酬指數": {"來源": f"git:{sha[:12]}:data/history/market_tri.csv", "補值日": nfill},
          "判定": verdict, "判定格": CE[CE["身分"] == "判定"].to_dict("records"), "先驗": PRI, "結果句": sent, "讀法": __doc__.split("═══ 讀法")[1], "秒": round(time.time() - t0)}
    json.dump(MJ, open(os.path.join(OUT, "main.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=RT.jdef)
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    log(f"[完成] {OUT}｜{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
