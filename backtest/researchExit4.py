# -*- coding: utf-8 -*-
"""出場第四輪 seq1【正式跑】（台股策略線 登錄 sha e86e45b37aaa66e2；裁定 seq417 發號 N_前段 ＋3、最多暫定；裁定 seq418 §二 核准正式跑）——回測線計算子代理。
母體 ＝ 隨便買（seq6 §二，researchExitGen.setup），⛔ 不套任何策略；純單筆：R ＝ 賣價或評估點收盤 ÷ T 收盤 − 1 − 賣出成本 0.4425%；
賣掉的錢不再計算（⛔ 不放 0050、不換股）；含 K0 不賣。
⭐ 事件、狀態、觸發日、賣出日 ＝ 頻率表 researchExit4_freq.work 原樣呼叫（⛔ 只 import），重建後與 resultsExit4/freq/events.csv.gz 逐列比（對帳項）。
⛔ 不 commit、不改既有檔；只新增本檔、researchExit4_check.py、resultsExit4/ 下新檔（⛔ 不動 freq/）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchExit4 [--procs 3] [--dry] [--limit N]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchExit4_check
--dry：價格全換成 1（R 全為 −成本，⛔ 無任何報酬資訊），輸出到 resultsExit4/dry/；只用來驗流程。

═══ 讀法（R 標；頻率表 F1～F9 照用，裁定 seq418 不推翻；以下是正式跑才需要的補充，⛔ 在看任何本件報酬之前寫死；★＝執行者定）═══
 R1 基準價 PT ＝ c[lv[T]]（T 當根還原收盤；S+／S− 的 T 必為有效 K 棒；★ S0 的 T 是日曆位置，若 T 停牌 ⇒ 用 T 以前最後一根有效收盤，筆數照報）。
 R2 評估點 E_h（F5）：T＋h ＞ 日曆尾 ⇒ 該 h 不收；壞根 kb ≤ T＋h ⇒ E_h ＝ kb−1（截斷）；結算價 PE ＝ c[lv[E_h]]（E_h 以前最後一根有效收盤；
    下市者同，seq6 同式）。
 R3 賣出（F6）：判斷日 d ∈ [T, E_h−1] 且賣出日 s ≤ E_h ⇒ 賣價 ＝ 還原開盤 o[s]；否則 ＝ 不賣，以 PE 結算（登錄「到 E 都沒觸發 ⇒ 等於不賣」）。
 R4 成本：★ R ＝ 價 ÷ PT − 1 − 0.004425（手續費 0.1425%＋證交稅 0.3%，減法式，seq6 同；各出法同計，含 K0 在 E 結算）；
    滑價版 ＝ 價 ×（1 − 0.5%）÷ PT − 1 − 0.004425（★ 只有賣出一邊；PT 是持有中的標價、不是買進，不加滑價）。
 R5 S+ K2 ＝ ½ R(K1) ＋ ½ R(K0)（登錄 §五）；持有天數 ＝ 兩半平均；賣後走勢 ＝ 賣掉那一半（＝ K1）。
 R6 持有天數 ＝ 賣 ⇒ s − T；不賣 ⇒ E_h − T（交易日，日曆位置差）。賣後走勢（只計賣出者）＝ PE ÷ o[s] − 1；「賣後下跌比例」＝ 該值 ＜ 0。
 R7 判定（登錄 §六）：h＝120；S+、S0_40、S− 三格；段依 T（F7）。每段依平均 R 排名（★ 同分照代號順序，實際不會同分）。
    兩段第一名相同 ⇒ 各段以「該段自己的第二名」做配對差 d ＝ R(第一) − R(第二)（同一事件兩法相減），T 曆月分群 CR0（exit_signal.cr0），
    z ＝ Φ⁻¹(1 − 0.05／3／2) ≈ 2.394（3 格 Bonferroni 雙尾 98.33%）；兩段 d ＞ 0 且 CI 下界 ＞ 0 ⇒ 成立（最多「暫定」）；
    否則「排第一但跟第二名分不出」；兩段第一名不同 ⇒「排名不穩」。n_eff ＝ min(n, 曆月) 須 ≥ 30（F7 已確認三格都能判）。
 R8 描述（不判）：全部出法兩兩配對差（95% 與 98.33% 兩種 CI 並列）、各出法對 K0、h＝60／250、S0_30／60、早年、上市／上櫃、分年。
 R9 同根兩出場價取較低（seq373）：每法每筆只有一個賣價 ⇒ 不適用（F6 同）。
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import subprocess
import sys
import time
from multiprocessing import Pool
from statistics import NormalDist

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchExit4_freq as F4                             # noqa: E402  ⛔ 只 import：work（事件與觸發）、add_h、seg_bounds、reg_check
G6, Q = F4.G6, F4.Q
from backtest import exit_signal as XS                      # noqa: E402  cr0
from backtest import research11 as R11                      # noqa: E402

HERE = os.path.expanduser("~/tw-p17/backtest")
OUT_MAIN = os.path.join(HERE, "resultsExit4")
FREQ_DIR = os.path.join(OUT_MAIN, "freq")
COST1 = 0.001425 + 0.003
SLIP = 0.005
HS, HJ = F4.HS, F4.HJ
EXITS, ENAME, STATES, BIG = F4.EXITS, F4.ENAME, F4.STATES, F4.BIG
Z95 = NormalDist().inv_cdf(0.975)
ZB = NormalDist().inv_cdf(1 - 0.05 / 3 / 2)
CELLS = (("S+", "S+"), ("S0", "S0_40"), ("S−", "S−"))
MUST = ["隨便買的歷史單筆，不是你的實際成交；隨便買的平均，不是對某一檔的預測",
        "只看這一筆，沒算賣掉的錢拿去做什麼",
        "各出法持有時間不同，R 是到賣出或評估點為止的這一筆報酬，不是年化",
        "看過相近結果後重切，最多暫定",
        "S+ K2（賣一半）＝ ½K1＋½K0，依構造不可能唯一第一（照報、不當新證據）",
        "S− K2 實質是「站回 20 日線才賣」；S+ K5、S− K2 幾乎一定 3 週內賣",
        "早年 reduce_v2：含減資假飆股約 0.3%；早年只上市、母體 liq_ok∧bars_ok（描述）",
        "S− K4 用月營收：2015 後下市股部分補回（seq411）⇒ 存活者缺口"]
_W: dict = {}
LOG: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


# ═════════════════════════════ worker
def _cached_stock_data(orig):
    box = {}

    def f(sid, market):
        k = (sid, market)
        if box.get("k") != k:
            box["k"] = k; box["v"] = orig(sid, market)
        return box["v"]
    return f


def _init_r(cal, off, b60, b200, tab, rev, rly, A, dry):
    F4._init(cal, off, b60, b200, tab, rev, rly, A)
    Q.stock_data = _cached_stock_data(Q.stock_data)          # 同一檔 F4.work 與本檔只讀一次（行程內修補，不改檔）
    _W["dry"] = dry


def price_rows(ev, S, last, dry):
    """把 R 等欄加到 F4.work 的事件列（R1～R6）。"""
    o = np.asarray(S["o"], float); c = np.asarray(S["c"], float); lv = np.asarray(S["lv"], int)
    if dry:                                                   # ⛔ 乾跑：價格全 1
        o = np.where(np.isfinite(o), 1.0, np.nan); c = np.where(np.isfinite(c), 1.0, np.nan)
    for r in ev:
        T = int(r["T"]); kb = int(r["kb"]) if int(r["kb"]) >= 0 else BIG
        jT = int(lv[T]); PT = float(c[jT])
        r["T基準根"] = jT
        g = F4.grp(r["狀態"])
        for h in HS:
            Tn = T + h
            if Tn > last:
                continue
            Eh = kb - 1 if kb <= Tn else Tn
            jE = int(lv[Eh]); PE = float(c[jE])
            r[f"Eh_{h}"] = Eh; r[f"jE_{h}"] = jE
            res = {}
            for code in EXITS[g]:
                if code == "K0":
                    sold = False
                else:
                    d = int(r[f"{code}_d"]); s = int(r[f"{code}_s"])
                    sold = (d >= 0) and (d <= Eh - 1) and (s >= 0) and (s <= Eh)
                if sold:
                    px = float(o[s]); hold = s - T; aft = PE / px - 1.0
                else:
                    px = PE; hold = Eh - T; aft = np.nan
                res[code] = (px / PT - 1.0 - COST1, px * (1 - SLIP) / PT - 1.0 - COST1, hold, aft, int(sold))
            if g == "S+":
                a, b = res["K1"], res["K0"]
                res["K2"] = (0.5 * (a[0] + b[0]), 0.5 * (a[1] + b[1]), 0.5 * (a[2] + b[2]), a[3], a[4])
            for code, (R, Rs, hold, aft, sd) in res.items():
                r[f"R_{code}_{h}"] = R; r[f"Rsl_{code}_{h}"] = Rs; r[f"hold_{code}_{h}"] = hold
                r[f"aft_{code}_{h}"] = aft; r[f"sold_{code}_{h}"] = sd
    return ev


def work_r(args):
    ev, st, xc = F4.work(args)
    if ev:
        sid, market, _ = args
        S = Q.stock_data(sid, market)
        ev = price_rows(ev, S, len(Q._G["cal"]) - 1, _W["dry"])
    return ev, st, xc


def run_world(world, procs, tab, dry, limit=None):
    Wd = G6.setup(world, log)
    cal = Wd["cal"]; p = Wd["p"]
    if limit:
        p = p[p["stock_id"].isin(sorted(p["stock_id"].unique())[:limit])]
    off = Q.RA.TR.load_official()
    b60 = R11.regime_below(Wd["c50ff"], 60)
    tasks = [(sid, Wd["mk"].get(sid, "twse"), sorted(g["e"].astype(int))) for sid, g in p.groupby("stock_id")]
    EV = []; ST = []; XC = {}
    with Pool(procs, initializer=_init_r, initargs=(cal, off, b60, Wd["below200"], tab, Wd["rev"], Wd["rly"], Wd["A"], dry)) as pool:
        for ev, st, xc in pool.imap_unordered(work_r, tasks, chunksize=8):
            EV += ev; ST += st
            for k, v in xc.items():
                XC[k] = XC.get(k, 0) + v
    E = pd.DataFrame(EV).sort_values(["sid", "e", "狀態"]).reset_index(drop=True)
    return Wd, E, pd.DataFrame(ST), XC


# ═════════════════════════════ 統計
def cr(x, mon, z):
    x = np.asarray(x, float)
    if len(x) == 0:
        return {"mean": np.nan, "se": np.nan, "lo": np.nan, "hi": np.nan, "月": 0}
    m, se, ng = XS.cr0(x, mon)
    return {"mean": m, "se": se, "lo": m - z * se, "hi": m + z * se, "月": int(ng)}


def subset(E, world, cal, seg, stt, h):
    x, y = F4.seg_bounds(cal, world)[seg]
    return E[(E["狀態"] == stt) & (E["T"] >= x) & (E["T"] <= y) & E[f"E在資料內_{h}"]]


def rank_rows(sub, g, h, extra):
    rows = []
    n = len(sub); mo = sub["T月"].nunique() if n else 0
    for code in EXITS[g]:
        R = sub[f"R_{code}_{h}"].to_numpy(float)
        sd = sub[f"sold_{code}_{h}"].to_numpy(int) == 1
        aft = sub[f"aft_{code}_{h}"].to_numpy(float)[sd]
        dd = (sub[f"hold_{code}_{h}"].to_numpy(float))
        r = {**extra, "出法": code, "出法名": ENAME[(g, code)], "n": n, "n_eff": int(min(n, mo)),
             "平均R": float(R.mean()) if n else np.nan, "中位R": float(np.median(R)) if n else np.nan,
             "勝率(R>0)": float((R > 0).mean()) if n else np.nan,
             "觸發比例(E前賣出)": float(sd.mean()) if n else np.nan,
             "平均持有天數": float(dd.mean()) if n else np.nan,
             "賣出者15交易日內賣比例": (float(((dd <= 15) & sd).sum() / sd.sum()) if sd.sum() and not (g == "S+" and code == "K2") else np.nan),
             "全部事件15交易日內賣比例": (float(((dd <= 15) & sd).mean()) if n and not (g == "S+" and code == "K2") else np.nan),
             "滑價版平均R": float(sub[f"Rsl_{code}_{h}"].mean()) if n else np.nan,
             "賣後到E漲跌平均(賣出者)": float(aft.mean()) if len(aft) else np.nan,
             "賣後到E漲跌中位(賣出者)": float(np.median(aft)) if len(aft) else np.nan,
             "賣後下跌比例(賣對了)": float((aft < 0).mean()) if len(aft) else np.nan}
        rows.append(r)
    order = sorted(range(len(rows)), key=lambda i: (-rows[i]["平均R"] if np.isfinite(rows[i]["平均R"]) else np.inf, i))
    for rk, i in enumerate(order, 1):
        rows[i]["名次"] = rk
    return rows


def pair_rows(sub, g, h, extra):
    rows = []
    if not len(sub):
        return rows
    mon = sub["T月"].to_numpy()
    cs = EXITS[g]
    for i, a in enumerate(cs):
        for b in cs[i + 1:]:
            d = sub[f"R_{a}_{h}"].to_numpy(float) - sub[f"R_{b}_{h}"].to_numpy(float)
            c95 = cr(d, mon, Z95); cB = cr(d, mon, ZB)
            rows.append({**extra, "A": a, "B": b, "A名": ENAME[(g, a)], "B名": ENAME[(g, b)], "n": len(d), "月": c95["月"],
                         "d平均(A−B)": c95["mean"], "d中位": float(np.median(d)), "A勝比例(d>0)": float((d > 0).mean()), "se": c95["se"],
                         "lo95": c95["lo"], "hi95": c95["hi"], "lo98.33": cB["lo"], "hi98.33": cB["hi"]})
    return rows


def verdicts(RK, E_by_world, cal_main):
    out = []
    E = E_by_world["main"]
    for g, stt in CELLS:
        seg_info = {}
        for sg in ("探索", "確認"):
            t = RK[(RK["世界"] == "主") & (RK["段"] == sg) & (RK["狀態"] == stt) & (RK["終點"] == f"T+{HJ}")].sort_values("名次")
            seg_info[sg] = t
        f1, f2 = seg_info["探索"].iloc[0]["出法"], seg_info["確認"].iloc[0]["出法"]
        row = {"格": g, "事件": stt, "探索第一": f1, "確認第一": f2}
        for sg in ("探索", "確認"):
            t = seg_info[sg]
            row[f"{sg}_n"] = int(t.iloc[0]["n"]); row[f"{sg}_n_eff"] = int(t.iloc[0]["n_eff"])
            row[f"{sg}_排名"] = "＞".join(f"{c}({m * 100:+.2f}%)" for c, m in zip(t["出法"], t["平均R"]))
            first, second = t.iloc[0]["出法"], t.iloc[1]["出法"]
            sub = subset(E, "main", cal_main, sg, stt, HJ)
            d = sub[f"R_{first}_{HJ}"].to_numpy(float) - sub[f"R_{second}_{HJ}"].to_numpy(float)
            c = cr(d, sub["T月"].to_numpy(), ZB)
            row[f"{sg}_第二"] = second; row[f"{sg}_d(第一−第二)"] = c["mean"]; row[f"{sg}_lo98.33"] = c["lo"]; row[f"{sg}_hi98.33"] = c["hi"]
            row[f"{sg}_d>0比例"] = float((d > 0).mean())
        if f1 != f2:
            row["結果"] = "排名不穩，分不出哪個最好"
        else:
            ok = all(row[f"{sg}_d(第一−第二)"] > 0 and row[f"{sg}_lo98.33"] > 0 and row[f"{sg}_n_eff"] >= 30 for sg in ("探索", "確認"))
            sec = row["探索_第二"] if row["探索_第二"] == row["確認_第二"] else f"{row['探索_第二']}／{row['確認_第二']}"
            row["結果"] = (f"暫定成立：{f1}（{ENAME[(g, f1)]}）最有利（贏第二名 {sec}）" if ok
                         else f"{f1}（{ENAME[(g, f1)]}）排第一，但跟第二名 {sec} 分不出")
            row["成立"] = bool(ok)
        row.setdefault("成立", False)
        out.append(row)
    return pd.DataFrame(out)


def priors(V, RK):
    def first(stt, sg):
        t = RK[(RK["世界"] == "主") & (RK["段"] == sg) & (RK["狀態"] == stt) & (RK["終點"] == f"T+{HJ}")].sort_values("名次")
        return t.iloc[0]["出法"]
    vs = V.set_index("格")
    p = {}
    sp = [first("S+", sg) for sg in ("探索", "確認")]
    p["① S+ 第一名是 K0 不賣或 K4 回落20%"] = {"探索第一": sp[0], "確認第一": sp[1],
                                       "中": bool(sp[0] == sp[1] and sp[0] in ("K0", "K4")), "註": "★ 以兩段第一名相同且屬 K0／K4 才算中"}
    sm = [first("S−", sg) for sg in ("探索", "確認")]
    p["② S− 第一名是 K2 等反彈"] = {"探索第一": sm[0], "確認第一": sm[1], "中": bool(sm[0] == sm[1] == "K2"), "註": "★ 同上"}
    nun = int((V["結果"].str.startswith("排名不穩")).sum())
    p["③ 三狀態至少一個排名不穩"] = {"排名不穩格數": nun, "中": bool(nun >= 1)}
    nok = int(V["成立"].sum())
    p["④ 3 格成立 ≤ 1 格"] = {"成立格數": nok, "中": bool(nok <= 1)}
    return p


# ═════════════════════════════ main
def lock_check():
    r = subprocess.run(["python3", "-m", "backtest.strategy_lock", "--check"], cwd=os.path.expanduser("~/tw-p17"), capture_output=True, text=True)
    s = (r.stdout + r.stderr).strip().splitlines()
    return s[-1] if s else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=3); ap.add_argument("--limit", type=int, default=None); ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    OUT = os.path.join(OUT_MAIN, "dry" if a.dry else "main")
    os.makedirs(OUT, exist_ok=True)
    reg = F4.reg_check()
    lk = lock_check()
    log(f"[登錄] {reg}（sha {F4.REG_SHA} 已驗）｜策略鎖：{lk}｜{'⛔ 乾跑（價格全 1）' if a.dry else '正式跑'}")
    if "相符（25 支）" not in lk:
        raise SystemExit("⛔ 策略鎖不符")
    X = pickle.load(open(F4.EXR_PKL, "rb")); tab = X["tab"]
    J = {"性質": ("⛔ 乾跑（價格全 1，無報酬資訊）" if a.dry else "出場第四輪 seq1 正式跑"), "登錄": f"台股策略線 seq1 sha {F4.REG_SHA}",
         "裁定": "seq417 發號 N_前段 ＋3、最多暫定；seq418 §二 核准正式跑；頻率表讀法 F1～F9 不推翻", "策略鎖_開工": lk,
         "z": {"95": Z95, "Bonferroni3_98.33": ZB}, "成本": {"賣出一次": COST1, "滑價(賣出一邊)": SLIP}}
    FREQ_EV = pd.read_csv(os.path.join(FREQ_DIR, "events.csv.gz"), dtype={"sid": str})
    RK = []; PR = []; MK = []; YR = []; EB = {}; CALS = {}; STAT = {}; RECON = {}
    for world in ("main", "early"):
        Wd, E, STt, XC = run_world(world, a.procs, tab, a.dry, a.limit)
        cal = Wd["cal"]; CALS[world] = cal
        E = F4.add_h(E, cal)
        E["世界"] = F4.WNAME[world]
        sb = F4.seg_bounds(cal, world); E["段"] = ""
        for sg, (x, y) in sb.items():
            E.loc[(E["T"] >= x) & (E["T"] <= y), "段"] = sg
        # 一致：worker 的 Eh ＝ add_h 的 E_h
        for h in HS:
            m = E[f"E在資料內_{h}"]
            assert (E.loc[m, f"Eh_{h}"].astype(int) == E.loc[m, f"E_{h}"].astype(int)).all(), f"Eh≠E_{h}"
            assert E.loc[~m, f"R_K0_{h}"].isna().all()
        # 對帳：與頻率表 events 逐列相同
        fe = FREQ_EV[FREQ_EV["世界"] == F4.WNAME[world]].sort_values(["sid", "e", "狀態"]).reset_index(drop=True)
        cols = [c for c in fe.columns if c in E.columns]
        if a.limit:
            fe = fe[fe["sid"].isin(set(E["sid"]))].reset_index(drop=True)
        mine = E[cols].copy()
        same_shape = len(mine) == len(fe)
        diffcols = {}
        if same_shape:
            for c in cols:
                x1, x2 = mine[c], fe[c]
                if pd.api.types.is_numeric_dtype(x1) and pd.api.types.is_numeric_dtype(x2):
                    bad = ~((x1.astype(float) == x2.astype(float)) | (x1.isna() & x2.isna()))
                else:
                    bad = ~((x1.astype(str) == x2.astype(str)))
                if bad.any():
                    diffcols[c] = int(bad.sum())
        RECON[F4.WNAME[world]] = {"列數(本件)": len(mine), "列數(頻率表)": len(fe), "比對欄": len(cols), "欄不同": diffcols,
                                  "逐列相同": bool(same_shape and not diffcols)}
        log(f"[對帳 {F4.WNAME[world]}] {RECON[F4.WNAME[world]]}")
        STAT[F4.WNAME[world]] = {"事件": E["狀態"].value_counts().to_dict(), "exright": XC,
                                 "S0 T 非有效根(用前一根收盤)": int(((E["狀態"].str.startswith("S0")) & (E["T基準根"] != E["T"])).sum()),
                                 **{f"壞根截斷_{h}": int((E[f"E在資料內_{h}"] & E[f"壞根截斷_{h}"]).sum()) for h in HS},
                                 **{f"下市末根<E_{h}": int(E[f"下市末根<E_{h}"].sum()) for h in HS}}
        log(f"[{F4.WNAME[world]}] {json.dumps(STAT[F4.WNAME[world]], ensure_ascii=False, default=str)}｜{time.time() - t0:.0f}s")
        for sg in sb:
            for stt in STATES:
                g = F4.grp(stt)
                for h in HS:
                    sub = subset(E, world, cal, sg, stt, h)
                    ex = {"世界": F4.WNAME[world], "段": sg, "狀態": stt, "終點": f"T+{h}"}
                    RK += rank_rows(sub, g, h, ex)
                    PR += pair_rows(sub, g, h, ex)
                    if h == HJ:
                        for mk, gm in sub.groupby("market"):
                            for r in rank_rows(gm, g, h, {**ex, "市場": mk}):
                                MK.append(r)
                        for yr, gy in sub.groupby("T年"):
                            rr = rank_rows(gy, g, h, {**ex, "T年": int(yr)})
                            YR.append({**ex, "T年": int(yr), "n": len(gy), "第一": min(rr, key=lambda z: z["名次"])["出法"],
                                       **{f"{z['出法']}平均R": z["平均R"] for z in rr}})
        EB[world] = E
    RK = pd.DataFrame(RK); PR = pd.DataFrame(PR)
    V = verdicts(RK, EB, CALS["main"])
    for _, v in V.iterrows():
        log(f"[判定] {v['格']}（{v['事件']}）探索 {v['探索_排名']}｜確認 {v['確認_排名']}｜⇒ {v['結果']}")
    P = priors(V, RK)
    log(f"[先驗] {json.dumps(P, ensure_ascii=False)}")
    J.update({"對帳_頻率表events逐列": RECON, "事件": STAT, "判定": V.to_dict("records"), "先驗": P, "必附": MUST,
              "讀法R": __doc__.split("═══ 讀法")[1], "時間": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")})
    J["策略鎖_交件"] = lock_check()
    RK.to_csv(os.path.join(OUT, "ranks.csv"), index=False, encoding="utf-8-sig")
    PR.to_csv(os.path.join(OUT, "pairs.csv"), index=False, encoding="utf-8-sig")
    V.to_csv(os.path.join(OUT, "verdict.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(MK).to_csv(os.path.join(OUT, "market.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(YR).to_csv(os.path.join(OUT, "years.csv"), index=False, encoding="utf-8-sig")
    keep = ["世界", "sid", "market", "e", "狀態", "T", "T日", "段", "kb", "T基準根"] + \
           [f"R_{c}_{h}" for h in HS for c in ("K0", "K1", "K2", "K3", "K4", "K5")]
    EV = pd.concat([EB["main"], EB["early"]], ignore_index=True)
    EV[[c for c in keep if c in EV.columns]].round(7).to_csv(os.path.join(OUT, "events_R.csv.gz"), index=False, compression="gzip")
    json.dump(J, open(os.path.join(OUT, "results.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] {time.time() - t0:.0f}s｜策略鎖 {J['策略鎖_交件']}")
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
