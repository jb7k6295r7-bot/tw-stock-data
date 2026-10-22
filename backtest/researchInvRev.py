# -*- coding: utf-8 -*-
"""存貨天數下降＋營收轉強 seq1【正式跑】（台股策略線 登錄 sha 3b637980fe4de0c3；裁定 seq454 §二 發號 N_單筆 ＋1、seq456 核准開跑：
主對照要求有實體存貨（不要求版只描述）；兩段可判、最多暫定；門檻 −10%／−25% 只描述；H＝250 照登錄判）——回測線計算子代理。
⛔ 不 commit、不改既有檔；researchInvRev_freq（頻率表，⛔ 只 import）、researchRevTurn（hold_R）、researchShortageExit（seam_open、cl）、
   researchRevTurn_freq（prices、ensure_data、filing_pos、back_ret、ranks…）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchInvRev --stage main [--dry]   # 重建＋主格＋描述
                   PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchInvRev --stage sens [--dry]   # 門檻 −10%／−25%（描述）
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchInvRev_check
    --dry ＝ 乾跑：所有 R 一律記 0（⛔ 不讀進場後價格），輸出到 ~/rtfwork/dry_ivrm
輸出 backtest/resultsInvRev/main/：main.json、cells.csv、desc.csv、split.csv、industry.csv、group12.csv、yearly.csv、sens.csv、events_R.csv.gz、run.log

═══ 讀法（Y 標；頻率表讀法 W0～W9 原樣沿用；以下為正式跑新增；⛔ 在讀任何本件報酬之前寫死於 2026-10-23（台北）；★＝執行者定）═══
 Y1 事件、主對照、描述對照 ＝ 頻率表：先以 researchInvRev_freq.main 原樣重建到 ~/rtfwork/rebuild_ivr，events.csv.gz、freq_段.csv、yearly.csv、coverage.csv、
    dist.csv、industry.csv、sens.csv、overlap.csv 與已 commit 的 resultsInvRev/freq 逐字比，任一不同 ⇒ 中止、⛔ 不算報酬。
    ★ 重跑時頻率表內建的「最新 main 路徑比對」釘在頻率表記錄的 9b0e9882572c（第一次正式 main 階段跑完後 main 前進到 a37825eb85b9，_changes.log、stocks.csv 有變，敏感度階段因此中止；
    資料本來就一律取 443ee8 archive，不受影響）。
 Y2 R ＝ researchRevTurn.hold_R 原式（e 還原開盤（主世界乘接縫倍數，researchShortageExit M2）進；x ＝ e＋H 收盤出；(e, x] 有壞根 ⇒ 第一個壞根前一根收盤；
    下市 ⇒ 末根收盤；x 無成交 ⇒ 之前最後一根）。對照各檔同式（同 e、同 H）。
 Y3 主格 X ＝（R事件 − 0.585%）−（主對照 R 平均 − 0.585%）★ ＝ R事件 − 主對照平均（成本兩邊都扣、相消）；另報「只扣事件一邊」X − 0.585%（描述）。
    事件等權；月分群 CI ＝ research11.cl_stats（按可用日月份），N ＝ 1 ⇒ z 1.96。
 Y4 判定（登錄 §三）：H＝250；探索 2015-04～2019-12、確認 2020-01～2025-08（依 A）；兩段點估計 ＞ 0 ∧ 確認段 CI 下界 ＞ 0 ⇒「存貨下降讓營收轉強更準（暫定）」；
    確認段點估計 ≤ 0 ⇒ 不合格；其餘 ⇒ 測不出；任一段 n_eff ＜ 24 ⇒ 還沒測。
 Y5 描述（不判）：H＝60、120；對「營收沒轉強」描述對照的差 X_desc；★ 不要求有實體存貨的主對照版 X_alt ＝ 同期、up、財報可算、D 可算且 ＞ −15%、同產業、
    市值十分位、前 12 月三分位、過閘、非金融、e 可進場（不看存貨 ÷ 總資產），候選依代號序、np.random.default_rng(20261022)、事件依（A, 代號）序抽 1～3；
    原物料八業 vs 其他；產業層（段內各產業 X 平均）；事件 − 大盤報酬指數（最新 origin/main data/history/market_tri.csv，TRI[x] ÷ TRI[e−1] − 1）；
    ★ 750 日內曾 3 倍 ＝ (e, min(e＋750, 第一個壞根前一根, 末根, 資料尾)] 有效收盤最高 ≥ 3 × 進場價（另報 750 日窗完整的件數）；分年；第二欄 12 組（月序 mod 12）。
 Y6 門檻敏感度（--stage sens，只描述）：researchInvRev_freq.main 以 D_THR ＝ −10%、−25% 各重跑到 ~/rtfwork/ivr_sens_<門檻>（事件與兩種對照照頻率表同式），
    再同 Y2、Y3 算 X（H＝250，探索、確認）。
 Y7 先驗（登錄 §六，寫死不改）：① 主格點估計 ＞ 0 ★ ＝ 兩段皆 ＞ 0；② 確認段 CI 含 0；③ 事件集中在原物料、電子零組件 ★ ＝ 兩段事件中（八業 ∪ 電子零組件業）≥ 50%；
    ④ 對「營收沒轉強」的差大於主格 ★ ＝ 兩段 X_desc 平均 ＞ X 平均。
"""
from __future__ import annotations

import argparse
import io
import json
import math
import os
import shutil
import subprocess
import sys
import time
from collections import defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchInvRev_freq as IV              # noqa: E402
from backtest import researchRevTurn as RM                  # noqa: E402  hold_R
from backtest import researchShortageExit as SM             # noqa: E402  seam_open、cl、lastvalid_le
from backtest import researchRevTurn_freq as RT             # noqa: E402
from backtest import researchIndMom_freq as IMF             # noqa: E402

OUT = "backtest/resultsInvRev/main"
FREQ = IV.OUT
REB = os.path.join(RT.WORK, "rebuild_ivr")
DRY = os.path.join(RT.WORK, "dry_ivrm")
COST = 0.00585
SEGJ = ["探索", "確認"]
HS = IV.HS
NOTES = ["主對照（營收也轉強、有實體存貨、但存貨天數沒降 15%）配到 31%／47%（探索／確認），配不到的事件不在主格",
         "事件多集中在電子（半導體、零組件等），缺貨型八業只 7～8% ⇒「缺貨的財報代理」實際多數抓到電子股",
         "約 46% 同時是營收轉強驗證的事件",
         "250 日重疊 ⇒ 月分群 CI 偏窄 ⇒ 結論最多「暫定」", "門檻 −10%／−25% 只描述；不要求有實體存貨的主對照版只描述",
         "2015～2018 下市 58 家月營收補不回（存活者偏差）"]
LOG = RT.LOG
log = RT.log


def run_freq(dst, thr=None):
    """頻率表原樣重跑到 dst。★「最新 origin/main」釘在頻率表當時記錄的版本（freq.json；之後 main 再前進不影響：資料一律取 443ee8 archive，
    釘版只讓頻率表內建的路徑比對沿用當時那一版）。"""
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    pin = json.load(open(os.path.join(FREQ, "freq.json"), encoding="utf-8"))["origin/main（最新）"]
    old_out, old_thr, old_git = IV.OUT, IV.D_THR, RT.git
    IV.OUT = dst
    if thr is not None:
        IV.D_THR = thr
    RT.git = lambda *a: pin if a == ("rev-parse", "origin/main") else old_git(*a)
    argv = sys.argv; sys.argv = ["researchInvRev_freq", "--procs", "3"]
    try:
        IV.main()
    finally:
        sys.argv = argv; IV.OUT = old_out; IV.D_THR = old_thr; RT.git = old_git


def rebuild_same():
    run_freq(REB)
    res = {}
    for f in ("events.csv.gz", "freq_段.csv", "yearly.csv", "coverage.csv", "dist.csv", "industry.csv", "sens.csv", "overlap.csv", "group12.csv"):
        a = pd.read_csv(os.path.join(REB, f), dtype=str, keep_default_na=False)
        b = pd.read_csv(os.path.join(FREQ, f), dtype=str, keep_default_na=False)
        res[f] = bool(a.shape == b.shape and (a.columns == b.columns).all() and a.equals(b))
    return res


def setup(dry):
    J = json.load(open(os.path.join(FREQ, "freq.json"), encoding="utf-8"))
    sha, DN, MD = RT.ensure_data(IV.BASE_SHA)
    PX = RT.prices(sha, DN, 3)
    O, nseam = SM.seam_open(PX)
    latest = J["origin/main（最新）"]
    tri = pd.read_csv(io.BytesIO(subprocess.run(["git", "show", f"{latest}:data/history/market_tri.csv"], capture_output=True, check=True).stdout))
    tri["date"] = pd.to_datetime(tri["date"]); tri = tri.drop_duplicates("date").set_index("date")["close"].astype(float)
    TRI = tri.reindex(tri.index.union(PX["CAL"])).ffill().reindex(PX["CAL"]).to_numpy(float)
    return J, DN, MD, PX, O, nseam, TRI


def returns(EV, PX, O, TRI, dry, alt=None):
    """逐事件 × H：R事件、主對照平均、描述對照平均、（alt）不要求存貨版主對照平均、指數、3 倍。"""
    CAL, ix, C, BAD, LASTV, VP = PX["CAL"], PX["ix"], PX["C"], PX["BAD"], PX["LASTV"], PX["VP"]
    CEND = len(CAL) - 1

    def R(i, e, H):
        return (0.0, "乾跑") if dry else RM.hold_R(PX, O, i, e, H)
    rows = []
    for rd in EV.to_dict("records"):
        if rd["進場"] != "保留":
            continue
        i = ix[rd["sid"]]; e = int(CAL.searchsorted(pd.Timestamp(rd["e"])))
        tri3 = None; full750 = False
        if not dry:
            x = min(e + 750, CEND)
            bb = np.flatnonzero(BAD[i, e + 1:x + 1])
            if len(bb):
                x = e + int(bb[0])
            if CEND - int(LASTV[i]) >= 5:
                x = min(x, int(LASTV[i]))
            seg = C[i, e + 1:x + 1]; seg = seg[np.isfinite(seg)]
            tri3 = bool(len(seg) and seg.max() >= 3 * O[i, e]); full750 = bool(x == e + 750)
        for H in HS:
            if rd[f"H{H}走得完"] != "True":
                continue
            Re, se = R(i, e, H)
            out = {"sid": rd["sid"], "期別": rd["期別"], "A": rd["A"], "e": rd["e"], "月": rd["月"], "年": int(rd["年"]), "段": rd["段"], "產業": rd["產業"],
                   "原物料型": rd["原物料型"] == "True", "H": H, "R事件": Re, "事件出場": se, "750日內曾3倍": tri3, "750日窗完整": full750}
            for lab, col in (("主", "主對照"), ("描述", "描述對照")) + ((("無存貨要求", None),) if alt is not None else ()):
                ss = (rd[col].split() if col else alt.get((rd["sid"], rd["期別"]), []))
                rc = [R(ix[s], e, H)[0] for s in ss]
                m = float(np.nanmean(rc)) if (len(rc) and np.isfinite(rc).any()) else np.nan
                out[f"R{lab}對照平均"] = m; out[f"X_{lab}"] = Re - m if np.isfinite(m) else np.nan; out[f"{lab}對照數"] = len(ss)
            out["X_只扣事件"] = out["X_主"] - COST if np.isfinite(out["X_主"]) else np.nan
            out["R指數"] = (TRI[e + H] / TRI[e - 1] - 1) if not dry else 0.0
            out["事件−指數"] = Re - out["R指數"]
            rows.append(out)
    return pd.DataFrame(rows)


def alt_controls(EV, PX, DN, MD):
    """Y5：不要求有實體存貨的主對照（描述）。判點欄位以頻率表同一批函式重算（fin_table、filing_pos、qref_of、rev 快取）。"""
    CAL, ix, G = PX["CAL"], PX["ix"], PX["G"]
    CEND = len(CAL) - 1
    RV, _ = RT.rev_table(MD, PX["SIDS"], 3, tag="all")
    pit = IMF.load_pit(DN)
    F, _ = IV.fin_table(DN)
    FP, _ = RT.filing_pos(DN, CAL)
    FPD = {s: (np.array([d for d, q, p in v], dtype="datetime64[ns]"), np.maximum.accumulate(np.array([q for d, q, p in v]))) for s, v in FP.items()}
    APOS = RT.avail_pos(CAL, sorted(RV["period"].unique()))
    evP = sorted(set(EV["期別"]))
    sub = RV[RV["period"].isin(evP) & RV["up"]]
    feat = {}
    for P in evP:
        A_ = APOS[P]; p1 = A_ - 1
        U = np.flatnonzero(G[:, p1])
        p12 = int(CAL.searchsorted(CAL[p1] - pd.DateOffset(months=12), side="right")) - 1
        mc = PX["MC"][U, p1]; mc = np.where(np.isfinite(mc) & (mc > 0), mc, np.nan)
        r12 = np.array([RT.back_ret(PX, int(i), p1, p12) if p12 >= 0 else np.nan for i in U])
        pm = np.full(len(U), np.nan); pr = np.full(len(U), np.nan)
        if np.isfinite(mc).any():
            pm[np.isfinite(mc)] = RT.ranks(mc[np.isfinite(mc)])
        if np.isfinite(r12).any():
            pr[np.isfinite(r12)] = RT.ranks(r12[np.isfinite(r12)])
        for k, i in enumerate(U):
            feat[(int(i), P)] = (int(math.ceil(pm[k] * 10)) if np.isfinite(pm[k]) else -1, int(math.ceil(pr[k] * 3)) if np.isfinite(pr[k]) else -1)
    pool = defaultdict(list)
    for s, P in zip(sub["sid"], sub["period"]):
        i = ix.get(s, -1); A_ = APOS[P]
        if i < 0 or A_ > CEND or not G[i, A_ - 1]:
            continue
        ind = pit.at(s, CAL[A_])[0] or ""
        if not ind or ind == IV.FIN:
            continue
        z = FPD.get(s)
        if z is None:
            continue
        k = int(np.searchsorted(z[0], np.datetime64(CAL[A_]), "left")) - 1
        if k < 0:
            continue
        q = int(z[1][k])
        if IV.qref_of(CAL[A_]) - q >= IV.LAG_BAD:
            continue
        D = F.get(s, {}).get(q, {}).get("D", np.nan)
        if not (np.isfinite(D) and D > IV.D_THR):
            continue
        f = feat.get((i, P))
        if f is None or f[0] < 0 or f[1] < 0:
            continue
        if IMF.entry_flag(PX, i, A_, A_ + 1) != "保留":
            continue
        pool[(P, ind, f[0], f[1])].append(s)
    rng = np.random.default_rng(IV.SEED)
    alt = {}
    for rd in EV.to_dict("records"):
        if rd["進場"] != "保留":
            continue
        i = ix[rd["sid"]]; A_ = APOS[rd["期別"]]
        f = feat.get((i, rd["期別"]), (-1, -1))
        cm = sorted(pool.get((rd["期別"], rd["產業"], f[0], f[1]), [])) if f[0] >= 0 and f[1] >= 0 else []
        if cm:
            alt[(rd["sid"], rd["期別"])] = sorted(rng.choice(cm, 3, replace=False).tolist()) if len(cm) >= 3 else cm
    return alt


def stats_X(RR, col, segs, H=250):
    out = {}
    for sg in segs:
        d = RR[(RR["段"] == sg) & (RR["H"] == H)].dropna(subset=[col])
        out[sg] = SM.cl(d[col].to_numpy(float), d["月"].to_numpy()) if len(d) else {"n": 0, "months": 0}
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--stage", choices=["main", "sens"], required=True); ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    out = DRY if a.dry else OUT
    os.makedirs(out, exist_ok=True)
    reg = IMF.reg_check(IV.REG_SHA); log(f"[登錄] {reg}（sha {IV.REG_SHA} 已驗）｜{'乾跑：R 全 0' if a.dry else '正式'}")
    if a.stage == "sens":
        J, DN, MD, PX, O, nseam, TRI = setup(a.dry)
        SE = []
        for thr in IV.SENS:
            dst = os.path.join(RT.WORK, f"ivr_sens_{int(-thr * 100)}")
            run_freq(dst, thr)
            EV = pd.read_csv(os.path.join(dst, "events.csv.gz"), dtype=str, keep_default_na=False)
            RR = returns(EV, PX, O, TRI, a.dry)
            st = stats_X(RR, "X_主", SEGJ)
            for sg in SEGJ:
                s_ = st[sg]
                SE.append({"門檻": thr, "段": sg, "身分": "描述", "事件": int((EV["段"] == sg).sum()), "主格n": s_.get("n", 0), "n_eff": s_.get("months", 0),
                           "X平均": s_.get("mean"), "X中位": s_.get("median"), "CI95下": s_.get("lo"), "CI95上": s_.get("hi")})
        SE = pd.DataFrame(SE)
        SE.to_csv(os.path.join(out, "sens.csv"), index=False, encoding="utf-8-sig")
        log(f"[Y6] {SE.round(4).to_dict('records')}｜{time.time() - t0:.0f}s")
        open(os.path.join(out, "run_sens.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
        return
    same = rebuild_same()
    log(f"[Y1 重建] {same}")
    if not all(same.values()):
        raise SystemExit(f"⛔ 頻率表重建不同：{same}")
    J, DN, MD, PX, O, nseam, TRI = setup(a.dry)
    EV = pd.read_csv(os.path.join(FREQ, "events.csv.gz"), dtype=str, keep_default_na=False)
    alt = alt_controls(EV, PX, DN, MD)
    log(f"[Y5] 不要求存貨版主對照配到 {len(alt)}／{int((EV['進場'] == '保留').sum())}｜{time.time() - t0:.0f}s")
    RR = returns(EV, PX, O, TRI, a.dry, alt)
    log(f"[Y2] 事件×H {len(RR)}｜{time.time() - t0:.0f}s")
    # 判定與 H 描述
    CE = []; ST = {}
    for H in HS:
        for sg in SEGJ:
            d = RR[(RR["段"] == sg) & (RR["H"] == H)]
            row = {"H": H, "段": sg, "身分": "判定" if H == 250 else "描述"}
            for col in ("X_主", "X_描述", "X_無存貨要求", "事件−指數"):
                dd = d.dropna(subset=[col])
                s_ = SM.cl(dd[col].to_numpy(float), dd["月"].to_numpy()) if len(dd) else {"n": 0, "months": 0}
                if col == "X_主":
                    ST[(H, sg)] = s_
                row.update({f"{col}_n": s_.get("n", 0), f"{col}_n_eff": s_.get("months", 0), f"{col}_平均": s_.get("mean"), f"{col}_中位": s_.get("median"),
                            f"{col}_>0比例": s_.get("win"), f"{col}_CI95下": s_.get("lo"), f"{col}_CI95上": s_.get("hi")})
            dm = d.dropna(subset=["X_主"])
            row.update({"R事件平均(主格)": float(dm["R事件"].mean()) if len(dm) else np.nan, "R主對照平均(主格)": float(dm["R主對照平均"].mean()) if len(dm) else np.nan,
                        "X只扣事件平均": float(dm["X_只扣事件"].mean()) if len(dm) else np.nan})
            CE.append(row)
    CE = pd.DataFrame(CE)
    ex, cf = ST[(250, "探索")], ST[(250, "確認")]
    if min(ex["months"], cf["months"]) < 24:
        verdict = "還沒測（n_eff ＜ 24）"
    elif ex["mean"] > 0 and cf["mean"] > 0 and cf["lo"] > 0:
        verdict = "合格（暫定）：存貨下降讓營收轉強更準（暫定）"
    elif cf["mean"] <= 0:
        verdict = "不合格：確認段點估計 ≤ 0"
    else:
        verdict = "測不出"
    log(f"[Y4 判定] {verdict}｜探索 {ex['mean']:+.4f} [{ex['lo']:+.4f}, {ex['hi']:+.4f}] n_eff {ex['months']}｜確認 {cf['mean']:+.4f} [{cf['lo']:+.4f}, {cf['hi']:+.4f}] n_eff {cf['months']}")
    # 描述
    SP = []; IN = []; G12 = []
    for sg in SEGJ:
        d = RR[(RR["段"] == sg) & (RR["H"] == 250)].dropna(subset=["X_主"])
        for lab, m in (("原物料八業", d["原物料型"]), ("其他產業", ~d["原物料型"])):
            s_ = SM.cl(d[m]["X_主"].to_numpy(float), d[m]["月"].to_numpy()) if m.any() else {"n": 0}
            SP.append({"段": sg, "組": lab, "n": s_.get("n", 0), "n_eff": s_.get("months", 0), "X平均": s_.get("mean"), "X中位": s_.get("median"), "CI95下": s_.get("lo"), "CI95上": s_.get("hi")})
        for ind, g in d.groupby("產業"):
            IN.append({"段": sg, "產業": ind, "n": len(g), "X平均": float(g["X_主"].mean()), "X中位": float(g["X_主"].median())})
        m0 = RT.mnum("2015-04" if sg == "探索" else "2020-01")
        v = d.groupby(d["月"].map(lambda s: (RT.mnum(s) - m0) % 12))["X_主"].mean()
        G12.append({"段": sg, "組數": int(len(v)), "組X中位": float(v.median()) if len(v) else np.nan, "組X最小": float(v.min()) if len(v) else np.nan,
                    "組X最大": float(v.max()) if len(v) else np.nan, "＞0組數": int((v > 0).sum()), "各組X": " ".join(f"{x:+.4f}" for x in v.to_numpy())})
        e3 = RR[(RR["段"] == sg) & (RR["H"] == 250)].dropna(subset=["X_主"])
        SP.append({"段": sg, "組": "750日內曾3倍（主格事件）", "n": len(e3), "比例": float(e3["750日內曾3倍"].astype(float).mean()) if len(e3) and not a.dry else np.nan,
                   "750日窗完整": int(e3["750日窗完整"].sum())})
    SP = pd.DataFrame(SP); IN = pd.DataFrame(IN).sort_values(["段", "n"], ascending=[True, False]); G12 = pd.DataFrame(G12)
    YR = RR[RR["H"] == 250].dropna(subset=["X_主"]).groupby("年").agg(件數=("X_主", "size"), X平均=("X_主", "mean"), X中位=("X_主", "median")).reset_index()
    # 先驗
    FRf = pd.read_csv(os.path.join(FREQ, "events.csv.gz"), dtype=str, keep_default_na=False)
    conc = {sg: float(((FRf["段"] == sg) & ((FRf["原物料型"] == "True") | (FRf["產業"] == "電子零組件業"))).sum() / max(1, (FRf["段"] == sg).sum())) for sg in SEGJ}
    xd = {sg: CE[(CE["H"] == 250) & (CE["段"] == sg)]["X_描述_平均"].iloc[0] for sg in SEGJ}
    PRI = [{"先驗": "① 主格點估計 ＞ 0（約六成）", "實際": f"探索 {ex['mean']:+.4f}、確認 {cf['mean']:+.4f}", "中": bool(ex["mean"] > 0 and cf["mean"] > 0)},
           {"先驗": "② 確認段 CI 含 0（約六成）", "實際": f"[{cf['lo']:+.4f}, {cf['hi']:+.4f}]", "中": bool(cf["lo"] <= 0 <= cf["hi"])},
           {"先驗": "③ 事件集中在原物料、電子零組件（約五成）", "實際": "；".join(f"{sg}（八業 ∪ 電子零組件業）占 {v:.1%}" for sg, v in conc.items()), "中": all(v >= 0.5 for v in conc.values())},
           {"先驗": "④ 對「營收沒轉強」的差大於主格（約七成）", "實際": "；".join(f"{sg} X_描述 {xd[sg]:+.4f}／X {ST[(250, sg)]['mean']:+.4f}" for sg in SEGJ),
            "中": all(xd[sg] > ST[(250, sg)]["mean"] for sg in SEGJ)}]
    sent = [f"營收轉強且存貨天數年減 ≥15% 的股票，之後 250 日對「營收也轉強、有實體存貨、但存貨沒降」的同類：{verdict}；"
            f"探索段 X 平均 {ex['mean'] * 100:+.2f} 點（n_eff {ex['months']}）、確認段 {cf['mean'] * 100:+.2f} 點 CI95 [{cf['lo'] * 100:+.2f}, {cf['hi'] * 100:+.2f}]（n_eff {cf['months']}）"] + NOTES
    RR.to_csv(os.path.join(out, "events_R.csv.gz"), index=False, encoding="utf-8-sig", compression="gzip")
    CE.to_csv(os.path.join(out, "cells.csv"), index=False, encoding="utf-8-sig")
    SP.to_csv(os.path.join(out, "split.csv"), index=False, encoding="utf-8-sig")
    IN.to_csv(os.path.join(out, "industry.csv"), index=False, encoding="utf-8-sig")
    G12.to_csv(os.path.join(out, "group12.csv"), index=False, encoding="utf-8-sig")
    YR.to_csv(os.path.join(out, "yearly.csv"), index=False, encoding="utf-8-sig")
    MJ = {"性質": "存貨天數下降＋營收轉強 seq1 正式跑（事件層主格 1 格）" + ("【乾跑：R 全 0】" if a.dry else ""), "登錄": f"台股策略線 seq1 sha {IV.REG_SHA}",
          "裁定": "seq454 §二、seq456", "資料": {"archive": IV.BASE_SHA, "最新 main": J["origin/main（最新）"]}, "頻率表重建": same, "接縫開盤倍數檔數": nseam,
          "不要求存貨版主對照配到": len(alt), "判定": verdict, "判定格": CE[CE["身分"] == "判定"].to_dict("records"), "先驗": PRI, "結果句": sent,
          "讀法": __doc__.split("═══ 讀法")[1], "秒": round(time.time() - t0)}
    json.dump(MJ, open(os.path.join(out, "main.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=RT.jdef)
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    log(f"[完成] {out}｜{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
