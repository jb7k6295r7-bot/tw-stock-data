# -*- coding: utf-8 -*-
"""頂部樣子 seq1【單段描述】2020-07～2025-08（裁定 seq443 §三：依構造不可判定、N_前段 −1、轉前瞻；本段結果只描述、⛔ 不當判定）——回測線計算子代理。
⭐ 結果句一律寫「單段描述、依構造不可判定、不當判定」。⛔ 不 commit、不改既有檔；條件與報酬一律 import topsell_cond（唯一來源）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTopSell_desc
輸出 backtest/resultsTopSell/desc_single/：desc.json（含結果句）、主表.csv、單項.csv、分組.csv、年.csv、出場.csv、rows.csv.gz、run.log

讀法（U 標；★＝執行者定）：
 U1 列 ＝ resultsTopSell/freq/events.csv.gz（已凍結頻率表）的 入判 ∧ 可用（日曆走得完、e 有成交、(t,e] 無壞根）∧ 月底 2020-07～2025-08（＝ 集保可算起～12 個月窗走得完）。
    ⭐ 一段（不分探索／確認）。e 開盤鎖漲停不剔（本件是「持有中的股票賣不賣」，鎖漲停賣得掉）★。
 U2 價格 ＝ researchIndMom_freq.build_panel 主世界（＝ 頻率表同源：還原收盤、還原開盤、壞根）；報酬、出場、腰斬 ＝ topsell_cond.ret_window。
 U3 量（登錄 §四）：d ＝ R(S 成立股) − 同月（同形成月底）入判可用列中 S 不成立股 R 的平均；成本兩邊各 0.585% ⇒ d 內抵銷（R淨 另列）；
    CI ＝ 形成月分群（research11.cl_stats，1.96）；n_eff ＝ min(筆數, 月數)。6 個月 d 同式（描述）。
 U4 描述（登錄 §四）：12 個月內腰斬比例兩組；T1、T2、T3 單項與兩兩（條件成立 vs 同月條件不成立，三值不可判者不進）；
    融資÷股數、60 日周轉率高低 ★ ＝ 同月入判可用列中位數切兩半（≥ 中位 ＝ 高），各半內 S 對 S 不成立的 d；逐年 d。
 U5 必附：單段描述、依構造不可判定、不當判定｜只看單筆，沒算賣掉的錢去哪｜條件是看過對照 D 結果才挑的｜集保 2020-07 起才可算。
"""
from __future__ import annotations

import gzip
import json
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import topsell_cond as TC                     # noqa: E402  唯一條件／報酬來源
from backtest import researchIndMom_freq as IMF             # noqa: E402  build_panel
from backtest import research11 as R11                      # noqa: E402  cl_stats
from backtest import researchTopSell_freq as TSF            # noqa: E402  PANEL、REG_SHA

OUT = "backtest/resultsTopSell/desc_single"
EVF = "backtest/resultsTopSell/freq/events.csv.gz"
M0, M1 = "2020-07", "2025-08"
SENT = "單段描述、依構造不可判定、不當判定"
NOTES = [SENT, "只看單筆，沒算賣掉的錢去哪", "條件是看過對照 D 結果才挑的", "集保 12 月變化 2020-07 月底起才可算 ⇒ 只有這一段",
         "裁定 seq443：N_前段 −1、轉前瞻，累積到兩段各 n_eff ≥ 30 再判"]
LOG: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def b3(x):
    return None if (x is None or (isinstance(x, float) and np.isnan(x)) or x == "") else (str(x) == "True")


def dstat(df, flag, rcol="R12"):
    """flag 為 True 的列 d ＝ R − 同月 flag 為 False 列 R 平均；回 cl_stats ＋ 兩組平均。"""
    t = df[df[flag] == True]; f = df[df[flag] == False]  # noqa: E712
    base = f.groupby("月")[rcol].mean()
    tt = t[t["月"].isin(base.index)].copy()
    tt["d"] = tt[rcol] - tt["月"].map(base)
    st = R11.cl_stats(tt["d"].to_numpy(float), tt["月"].to_numpy())
    out = {"成立筆": int(len(t)), "不成立筆": int(len(f)), "可比筆(同月有對照)": int(len(tt)), "月數": int(tt["月"].nunique()),
           "n_eff": int(min(len(tt), tt["月"].nunique())), "成立R平均": float(t[rcol].mean()) if len(t) else np.nan,
           "不成立R平均": float(f[rcol].mean()) if len(f) else np.nan, "成立R淨平均": float(t[rcol].mean() - TC.COST) if len(t) else np.nan,
           "d平均": st.get("mean", np.nan), "d中位": st.get("median", np.nan), "d_CI下": st.get("lo", np.nan), "d_CI上": st.get("hi", np.nan),
           "d>0比例": st.get("win", np.nan)}
    out["CI含0"] = bool(out["d_CI下"] <= 0 <= out["d_CI上"]) if np.isfinite(out["d_CI下"]) else None
    return out


def main():
    t0 = time.time(); os.makedirs(OUT, exist_ok=True)
    EV = pd.read_csv(EVF, dtype={"sid": str})
    for c in ("T1a", "T1b", "T1", "T2", "T3", "S", "S12"):
        EV[c] = [b3(x) for x in EV[c]]
    EV["入判"] = EV["入判"].astype(str) == "True"; EV["可用"] = EV["可用"].astype(str) == "True"
    X = EV[EV["入判"] & EV["可用"] & (EV["月"] >= M0) & (EV["月"] <= M1)].copy().reset_index(drop=True)
    log(f"[列] 入判∧可用∧{M0}～{M1}：{len(X)}｜S 成立 {int((X['S'] == True).sum())}、不成立 {int((X['S'] == False).sum())}、不可判 {int(X['S'].isna().sum())}")  # noqa: E712
    Zm = IMF.build_panel("主", 2, log); cal = Zm["cal"]; n0 = Zm["n0"]; ix = {s: i for i, s in enumerate(Zm["sids"])}
    PN = pickle.load(open(TSF.PANEL, "rb")); P = PN["P"]
    rows = []; okr = []
    for sid, pi, pk, ed in zip(X["sid"], X["_i"], X["_k"], X["e"]):
        i = ix[sid]; e = int(cal.get_loc(pd.Timestamp(ed)))
        vp = np.flatnonzero(np.isfinite(Zm["C"][i])); vc = Zm["C"][i, vp]; vb = Zm["BAD"][i, vp]; o = float(Zm["O"][i, e])
        okr.append(o / Zm["C"][i, e] - 1 if np.isfinite(Zm["C"][i, e]) else np.nan)
        rec = {"R12": np.nan, "出場12": "", "腰斬12": None, "最大回落12": np.nan, "R6": np.nan, "出場6": ""}
        for mth, sfx in ((12, "12"), (6, "6")):
            x, _, done = TC.window_end(cal, e, mth)
            if not done:
                continue
            w = TC.ret_window(vp, vc, vb, o, e, x, n0 - 1)
            if w is None:
                continue
            rec[f"R{sfx}"] = w["R"]; rec[f"出場{sfx}"] = w["出場"]
            if mth == 12:
                rec["腰斬12"] = w["腰斬"]; rec["最大回落12"] = w["最大回落"]
        rec["融資÷股數"] = float(P["融資餘額÷股數"][int(pi), int(pk)]); rec["60日周轉率"] = float(P["60日周轉率"][int(pi), int(pk)])
        rows.append(rec)
    X = pd.concat([X, pd.DataFrame(rows)], axis=1)
    okr = np.asarray(okr, float)
    log(f"[報酬] R12 可算 {int(X['R12'].notna().sum())}／{len(X)}｜開盤÷收盤−1 中位 {np.nanmedian(okr):+.4f}（同一還原尺度檢查）｜{time.time() - t0:.0f}s")
    X = X[X["R12"].notna()].copy()
    for a_, b_ in (("T1", "T2"), ("T1", "T3"), ("T2", "T3")):
        X[f"{a_}∧{b_}"] = [TC.kleene(p, q) for p, q in zip(X[a_], X[b_])]
    # 主表
    MAIN = []
    for nm, rc in (("12 個月（登錄主量）", "R12"), ("6 個月（描述）", "R6")):
        r = {"量": nm, **dstat(X, "S", rc)}; MAIN.append(r)
    s_ = X[X["S"] == True]; f_ = X[X["S"] == False]  # noqa: E712
    MAIN.append({"量": "12 個月內腰斬（路徑最大回落 ≤ −50%）比例", "成立筆": len(s_), "不成立筆": len(f_),
                 "成立R平均": float(s_["腰斬12"].astype(float).mean()), "不成立R平均": float(f_["腰斬12"].astype(float).mean())})
    MAIN = pd.DataFrame(MAIN)
    SING = pd.DataFrame([{"條件": c, **dstat(X, c, "R12")} for c in ("T1", "T2", "T3", "T1∧T2", "T1∧T3", "T2∧T3", "S")])
    GR = []
    for col in ("融資÷股數", "60日周轉率"):
        Y = X[np.isfinite(X[col])].copy()
        med = Y.groupby("月")[col].transform("median")
        Y["半"] = np.where(Y[col] >= med, "高", "低")
        for h in ("高", "低"):
            GR.append({"分組欄": col, "半": h, **dstat(Y[Y["半"] == h], "S", "R12")})
    GR = pd.DataFrame(GR)
    X["年"] = X["月"].str[:4]
    YR = pd.DataFrame([{"年": y, **dstat(g, "S", "R12")} for y, g in X.groupby("年")])
    EXT = X.groupby([X["S"].map({True: "S成立", False: "S不成立", None: "不可判"}), "出場12"]).size().rename("筆").reset_index()
    m = MAIN.iloc[0]
    sent = (f"【{SENT}】2020-07～2025-08 單段：S 成立 {int(m['成立筆'])} 筆（{int(m['月數'])} 個月、n_eff {int(m['n_eff'])}），"
            f"之後 12 個月平均比同月其他大漲股 {m['d平均'] * 100:+.1f} 個百分點（月分群 95% CI {m['d_CI下'] * 100:+.1f}～{m['d_CI上'] * 100:+.1f}）；"
            f"只看單筆、沒算賣掉的錢去哪；條件是看過結果才挑的；⛔ 不當判定，待前瞻累積兩段各 n_eff ≥ 30。")
    w = lambda df, nm: df.to_csv(os.path.join(OUT, nm), index=False, encoding="utf-8-sig")
    w(MAIN, "主表.csv"); w(SING, "單項.csv"); w(GR, "分組.csv"); w(YR, "年.csv"); w(EXT, "出場.csv")
    keep = ["sid", "月", "t", "e", "S", "T1", "T2", "T3", "R12", "出場12", "腰斬12", "最大回落12", "R6", "出場6", "融資÷股數", "60日周轉率"]
    with gzip.open(os.path.join(OUT, "rows.csv.gz"), "wt", encoding="utf-8") as fh:
        X[keep].to_csv(fh, index=False)
    J = {"性質": "單段描述（裁定 seq443 §三；⛔ 不當判定）", "結果句": sent, "登錄": TSF.REG_SHA, "頻率表 events": EVF, "段": f"{M0}～{M1}",
         "列數": int(len(X)), "開盤÷收盤−1 中位": float(np.nanmedian(okr)), "必附": NOTES, "讀法": __doc__.split("讀法（U 標")[1],
         "時間": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M"), "耗時秒": round(time.time() - t0)}
    json.dump(J, open(os.path.join(OUT, "desc.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(sent)
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
