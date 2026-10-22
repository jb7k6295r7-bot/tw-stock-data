# -*- coding: utf-8 -*-
"""頂部樣子前瞻 fixture（裁定 seq443 §三 交辦 3：月份判斷、凍結、到期填報酬、不前視）＋ 條件唯一來源等價證明——回測線開發子代理。
⛔ 只寫暫存夾 ~/tpswork/fx_*（不碰 backtest/forward/topsell）與 resultsTopSell/fwd_check/check.json、check.log。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.topsell_fwd_check [--skip-int]

F1 等價：topsell_cond 函式 ＋ 頻率表同一份月底面板／價格，重跑全部月底 ⇒ 與已凍結 resultsTopSell/freq/events.csv.gz 逐列相同
   （母體集合、入判、R36 完整旗標、本益比位置、近 4 季 EPS、T1a、T1b、T1、T2、T3、S、S12、壞根(t,e]、e無成交、e開盤鎖漲停）。
F1b 集保：topsell_cond.lastok ＋ 存活規則 ＋ 最新 main tdcc_hist（topsell_fwd.load_tdcc）⇒ 面板 12 月變化逐列相同（含頻率表對帳那 14 列非存活月）。
F1c 財報：topsell_fwd.load_fund ＋ sel_q ＋ topsell_cond.eps4／roe4 ⇒ 面板 fs_qk、ROE（float32，相對 1e−5）、events 近 4 季 EPS 相同。
F2 月份判斷（pending_months 純函式）：月底當晚不判、隔一交易日起判、漏跑補齊照月序、已判不重判、起始月之前不判、資料尾不完整月不判。
F3 整合（暫存夾）：① --asof 2026-06-30 --start 2026-03 判 2026-03～05 ② 同夾 --asof 資料尾 ⇒ 舊列逐字不變（凍結）、補判 2026-06～09、到期填 6 個月；
   ③ 另一空夾 --asof 資料尾 --start 2026-03 ⇒ 2026-03～05 判定欄與 ① 相同（資料日之後的價格不影響判定 ＝ 不前視）；
   ④ 同指令再跑一次 ⇒ events.csv 位元相同（冪等）；⑤ 2025-06～08 形成月（--start 2025-06）母體／S 對已凍結頻率表的一致率，12 個月 R 對單段描述 rows 的差。
F4 凍結守門：write_events 遇舊格被改 ⇒ 中止不寫。
F5 突變（不前視）：子母體世界，月底 t 之後的價格／壞根／閘／本益比、上傳日 ≥ t 的財報、t−1 之後的集保全部亂改 ⇒ judge_month 判定欄不變；
   正對照：改 t 當天收盤 ⇒ 判定改變（證明測得到）。
F6 名單第十三節：寫入、重寫冪等、其他段逐字不變、無事移除。
F7 策略鎖 25 支相符；git 相對開工前只多本件新檔。
"""
from __future__ import annotations

import argparse
import copy
import glob
import hashlib
import json
import os
import pickle
import shutil
import subprocess
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import topsell_cond as TC                     # noqa: E402
from backtest import topsell_fwd as TF                      # noqa: E402
from backtest import researchTopSell_freq as TSF            # noqa: E402
from backtest import researchIndMom_freq as IMF             # noqa: E402
from backtest import researchPTH_freq as PF                 # noqa: E402
from backtest import bigrun_monthly as BM                   # noqa: E402
from backtest import researchIndRev_prereg as PRE           # noqa: E402
from backtest import researchAddOn as RA                    # noqa: E402
from backtest import data as D                              # noqa: E402

OUT = "backtest/resultsTopSell/fwd_check"
PY = os.path.expanduser("~/tw-p16/.venv/bin/python")
FX = os.path.join(TF.WORK, "fx")


def b3(x):
    return None if (x is None or (isinstance(x, float) and np.isnan(x)) or x == "") else (str(x) == "True")


def same(a, b, tol=0.0):
    if isinstance(a, float) or isinstance(b, float):
        a = np.nan if a is None else float(a); b = np.nan if b is None else float(b)
        if np.isnan(a) or np.isnan(b):
            return np.isnan(a) and np.isnan(b)
        return abs(a - b) <= tol * max(1.0, abs(a))
    return a == b


def run_fwd(args, log):
    r = subprocess.run([PY, "-m", "backtest.topsell_fwd"] + args, capture_output=True, text=True, env={**os.environ, "PYTHONPATH": os.path.expanduser("~/tw-p17")})
    log(f"  topsell_fwd {' '.join(args)} ⇒ rc {r.returncode}｜{(r.stdout.strip().splitlines() or [''])[-1]}")
    if r.returncode:
        raise SystemExit(f"⛔ topsell_fwd 失敗：{r.stderr[-1500:]}")
    return r


def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--skip-int", action="store_true"); ap.add_argument("--int-reuse", action="store_true"); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    if os.path.exists(os.path.join(OUT, "check.log")):
        os.remove(os.path.join(OUT, "check.log"))
    log = RA.log_to(os.path.join(OUT, "check.log"))
    CK = {}; t0 = time.time()
    sha = BM.git("rev-parse", "origin/main").strip()
    # ══ F1 等價（面板 ＋ topsell_cond 重跑全部月底）
    EV = pd.read_csv(TSF.OUT + "/events.csv.gz", dtype={"sid": str, "產業": str})
    for c in ("T1a", "T1b", "T1", "T2", "T3", "S", "S12", "壞根(t,e]", "e無成交", "e開盤鎖漲停", "入判", "R36_36月完整無壞根"):
        EV[c] = [b3(x) for x in EV[c]]
    PN = pickle.load(open(TSF.PANEL, "rb")); P = PN["P"]; SIDS = PN["SIDS"]; MEp = np.asarray(PN["MEp"], np.int64); K = len(MEp)
    META = PN["META"]; INDM = PN["INDM"]
    Ze = IMF.build_panel("早年", 2, log); Zm = IMF.build_panel("主", 2, log)
    CAL, NE, C, BAD, G, TRD, UPL, seam, ie, im = TSF.merged_prices(Ze, Zm, SIDS)
    NC = len(CAL)
    FDm = os.path.join(TSF.WORK, f"main_{json.load(open(TSF.OUT + '/freq.json', encoding='utf-8'))['origin/main'][:12]}", "data")
    L = []
    for f in sorted(glob.glob(os.path.join(FDm, "mops", "fin_hist", "*.csv"))):
        b = os.path.basename(f)[:6]
        x = pd.read_csv(f, dtype={"stock_id": str}, usecols=["stock_id", "eps_ytd"]); x["qk"] = int(b[:4]) * 4 + int(b[5]) - 1; L.append(x)
    FN = pd.concat(L).drop_duplicates(["stock_id", "qk"], keep="last"); FN["eps_ytd"] = pd.to_numeric(FN["eps_ytd"], errors="coerce")
    EPSY = {s: g.set_index("qk")["eps_ytd"].to_dict() for s, g in FN.groupby("stock_id")}
    ROE = P["ROE"].astype(float); PE = P["本益比"].astype(float); TD12 = P["集保千張大戶比12月變化"].astype(float); HI1 = P["距一年高點"].astype(float)
    MED = {}
    for k in range(K):
        for ind in set(INDM[:, k]) - {""}:
            MED[(ind, k)] = TC.ind_median(ROE[INDM[:, k] == ind, k])[0]
    mine = []
    for i in range(len(SIDS)):
        vp = np.flatnonzero(np.isfinite(C[i]))
        if not len(vp):
            continue
        vc = C[i, vp]; vb = BAD[i, vp]; last = -999
        for k in range(K):
            p = int(MEp[k])
            if not G[i, p] or not np.isfinite(C[i, p]):
                continue
            rr, full36 = TC.r36(vp, vc, vb, p, int(MEp[k - 36]) if k >= 36 else -1)
            if not TC.in_pop(rr, HI1[i, k]):
                continue
            take = TC.dedupe_take(k, last)
            if take:
                last = k
            pos = TC.pe_pos(PE[i, max(0, k - TC.PE_WIN + 1):k + 1])
            e4 = TC.eps4(EPSY.get(SIDS[i]), int(META["fs_qk"][i, k]))
            ind = INDM[i, k]; med = MED.get((ind, k), np.nan) if ind else np.nan
            sg = TC.signals(pos, e4, ROE[i, k], med, TD12[i, k])
            ef = TC.entry_flags(C[i], BAD[i], TRD[i], UPL[i], p + 1, NC)
            mine.append({"sid": SIDS[i], "_k": k, "入判": take, "R36_36月完整無壞根": full36, "本益比5年月底位置": pos, "近4季EPS": e4, **sg, **ef})
    MI = pd.DataFrame(mine).set_index(["sid", "_k"]); EVi = EV.set_index(["sid", "_k"])
    setok = set(MI.index) == set(EVi.index)
    bad = {}
    if setok:
        MI = MI.loc[EVi.index]
        for c in ("入判", "R36_36月完整無壞根", "T1a", "T1b", "T1", "T2", "T3", "S", "S12", "壞根(t,e]", "e無成交", "e開盤鎖漲停"):
            bad[c] = int(sum(x != y for x, y in zip(MI[c], EVi[c])))
        for c in ("本益比5年月底位置", "近4季EPS"):
            bad[c] = int(sum(not same(x, y, 1e-12) for x, y in zip(MI[c], EVi[c])))
    CK["F1_條件唯一來源重現凍結頻率表"] = {"列（自算／凍結）": [len(MI), len(EVi)], "母體集合相同": setok, "逐欄不符": bad,
                                  "過": bool(setok and not any(bad.values()))}
    log(f"[F1] {CK['F1_條件唯一來源重現凍結頻率表']}｜{time.time() - t0:.0f}s")
    # ══ F1b 集保（最新 main）
    TDD = TF.ensure_tdcc(sha)
    TD = TF.load_tdcc(TDD, CAL, set(EV["sid"]))
    VPs = {}
    nb = 0; n = 0
    for s, i, k in zip(EV["sid"], EV["_i"], EV["_k"]):
        if s not in VPs:
            VPs[s] = np.flatnonzero(np.isfinite(C[i]))
        vp = VPs[s]

        def lev(kk):
            a_ = TD.get(s)
            if a_ is None or kk < 0 or not TC.alive(vp, int(MEp[kk])):
                return np.nan
            j = TC.lastok(a_, int(MEp[kk]) - 1, TC.TD_LAG)
            return float(a_[j]) if j >= 0 else np.nan
        v = lev(k) - lev(k - 12) if k >= 12 else np.nan
        n += 1
        if not same(v, float(TD12[i, k]), 1e-5):
            nb += 1
    CK["F1b_集保"] = {"列": n, "不符": nb, "過": nb == 0}
    log(f"[F1b] {CK['F1b_集保']}")
    # ══ F1c 財報
    FD = BM.ensure_fund(sha, sha)
    AV, FIN = TF.load_fund(FD, set(EV["sid"]))
    bq = br = be = 0
    for s, i, k, e0 in zip(EV["sid"], EV["_i"], EV["_k"], EV["近4季EPS"]):
        t = CAL[MEp[k]]; q, _ = TF.sel_q(AV, s, t)
        q = q if (q < 0 or q >= 2012 * 4) else -1                    # 面板 KS 自 2012Q1
        if q != int(META["fs_qk"][i, k]):
            bq += 1
        f = FIN.get(s, {})
        if not same(TC.eps4(f.get("eps_ytd"), q), e0, 1e-9):
            be += 1
        r_ = TC.roe4(f.get("nip_ytd"), f.get("equity_parent"), q)
        if not same(r_, float(ROE[i, k]), 1e-5) and not (q < 2012 * 4 + 3):
            br += 1
    CK["F1c_財報"] = {"列": len(EV), "選季不符": bq, "EPS不符": be, "ROE不符(相對1e−5)": br, "過": bq == be == br == 0}
    log(f"[F1c] {CK['F1c_財報']}｜{time.time() - t0:.0f}s")
    del C, BAD, G, TRD, UPL, Ze, Zm
    # ══ F2 月份判斷
    H = BM.ensure_snapshot(sha); D.DATA = H; cal = D.load_calendar()
    c2 = cal[cal <= pd.Timestamp("2026-10-21")]

    def pm(asof, done=(), start="2026-09"):
        cc = cal[cal <= pd.Timestamp(asof)]
        return [x[0] for x in TF.pending_months(cc, pd.Timestamp(asof), set(done), start)]
    cases = {"9/30 月底當晚": (pm("2026-09-30"), []), "10/1 判定夜": (pm("2026-10-01"), ["2026-09"]),
             "10/21 已判 9 月": (pm("2026-10-21", ["2026-09"]), []), "起始 2026-03、資料日 6/30（6 月未完、當晚不判）": (pm("2026-06-30", start="2026-03"), ["2026-03", "2026-04", "2026-05"]),
             "漏跑補齊（起始 2026-06、資料日 10/21）": (pm("2026-10-21", start="2026-06"), ["2026-06", "2026-07", "2026-08", "2026-09"]),
             "已判 6、8 月不重判": (pm("2026-10-21", ["2026-06", "2026-08"], "2026-06"), ["2026-07", "2026-09"])}
    F2 = {k: {"得": v[0], "應": v[1], "過": v[0] == v[1]} for k, v in cases.items()}
    CK["F2_月份判斷"] = F2
    log(f"[F2] {all(v['過'] for v in F2.values())}｜{F2}")
    # ══ F4 凍結守門
    tmp = os.path.join(FX, "guard"); shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
    df = pd.DataFrame([{c: "" for c in TF.COLS}]); df.loc[0, "sid"] = "2330"; df.loc[0, "S"] = "True"
    p_ = os.path.join(tmp, "events.csv"); TF.write_events(p_, df.iloc[:0], df)
    df2 = df.copy(); df2.loc[0, "S"] = "False"
    try:
        TF.write_events(p_, df, df2); g_ok = False
    except SystemExit:
        g_ok = True
    df3 = df.copy(); df3.loc[0, "R12"] = "0.1"; TF.write_events(p_, df, df3)
    CK["F4_凍結守門"] = {"改舊格被擋": g_ok, "空格可填": TF.read_events(p_).loc[0, "R12"] == "0.1", "過": g_ok}
    log(f"[F4] {CK['F4_凍結守門']}")
    # ══ F5 突變（子母體）
    rng = np.random.default_rng(443)
    F = EV[(EV["月"] == "2025-06") & (EV["入判"] == True)]  # noqa: E712
    sub = sorted(set(F["sid"]) | set(rng.choice(sorted(set(EV["sid"])), 120, replace=False)))
    calx = cal[cal <= pd.Timestamp("2026-10-21")]
    W, names = TF.build_world(H, calx, sub, 3)
    ME, _ = PF.month_ends(calx); ME = np.asarray(ME, np.int64)
    k = int(np.flatnonzero(calx[ME] == pd.Timestamp("2025-06-30"))[0]); p = int(ME[k]); t = calx[p]
    AV, FIN = TF.load_fund(FD, set(W)); TD = TF.load_tdcc(TDD, calx, set(W))
    _, _, cat, _, _, _ = PRE.load_rev(H); PIT = PRE.PIT(H, cat)
    base = TF.judge_month(W, calx, ME, k, AV, FIN, TD, PIT, names, {})
    W2 = copy.deepcopy(W)
    for s, r in W2.items():
        n0 = len(calx)
        r["C"][p + 1:] = r["C"][p + 1:] * rng.uniform(0.2, 5, n0 - p - 1); r["BAD"][p + 1:] = rng.random(n0 - p - 1) < 0.3
        r["G"][p + 1:] = rng.random(n0 - p - 1) < 0.5; r["PER"][p + 1:] = rng.uniform(1, 500, n0 - p - 1); r["MC"][p + 1:] = rng.uniform(1e8, 1e12, n0 - p - 1)
    AV2 = AV
    FIN2 = copy.deepcopy(FIN)
    for s, v in AV.items():
        for d, q in v:
            if d >= t and s in FIN2:
                for c in FIN2[s]:
                    if q in FIN2[s][c]:
                        FIN2[s][c][q] = float(rng.uniform(-50, 50))
    TD2 = {s: np.r_[a_[:p], rng.uniform(0, 100, len(a_) - p)] for s, a_ in TD.items()}
    mut = TF.judge_month(W2, calx, ME, k, AV2, FIN2, TD2, PIT, names, {})
    JC = [c for c in TF.JUDGE_COLS if c not in ("名稱",)]
    fx = lambda rows: [tuple(TF.fmt(r[c]) for c in JC) for r in rows]
    nomut = fx(base) == fx(mut)
    W3 = copy.deepcopy(W)
    for s in W3:
        W3[s]["C"][p] = W3[s]["C"][p] * 0.5
    pos_ctl = fx(TF.judge_month(W3, calx, ME, k, AV, FIN, TD, PIT, names, {})) != fx(base)
    CK["F5_突變不前視"] = {"子母體檔": len(W), "月底": str(t.date()), "母體列": len(base), "S成立": sum(r["S"] is True for r in base),
                       "t 之後亂改 ⇒ 判定欄相同": nomut, "正對照（改 t 收盤）⇒ 不同": pos_ctl, "過": nomut and pos_ctl}
    log(f"[F5] {CK['F5_突變不前視']}｜{time.time() - t0:.0f}s")
    del W, W2, W3
    # ══ F6 名單第十三節
    src = sorted(glob.glob("backtest/resultsDaily/daily_2026-10-*.md"))[-1]
    md = os.path.join(FX, "daily.md"); os.makedirs(FX, exist_ok=True); shutil.copy(src, md)
    orig = open(md, encoding="utf-8").read()
    BM.put_daily(md, [[TF.SEC + "（內部・不推 LINE）", "", "- 測試行"]], prefix=TF.SEC); t1 = open(md, encoding="utf-8").read()
    BM.put_daily(md, [[TF.SEC + "（內部・不推 LINE）", "", "- 測試行"]], prefix=TF.SEC); t2 = open(md, encoding="utf-8").read()
    BM.put_daily(md, [], prefix=TF.SEC); t3 = open(md, encoding="utf-8").read()
    CK["F6_名單第十三節"] = {"寫入": "- 測試行" in t1 and "【LINE】" not in t1.split(TF.SEC)[1], "冪等": t1 == t2,
                          "移除後回原樣": t3.rstrip("\n") == orig.rstrip("\n"), "過": ("- 測試行" in t1) and t1 == t2 and t3.rstrip("\n") == orig.rstrip("\n")}
    log(f"[F6] {CK['F6_名單第十三節']}")
    # ══ F3 整合
    if not a.skip_int:
        last = str(cal[-1].date())
        if a.int_reuse:                                  # 逐步前景跑時釘住的 sha 與資料日（tps_int*.sh 寫入）
            sha = open(os.path.join(FX, "SHA")).read().strip(); last = open(os.path.join(FX, "LAST")).read().strip()
        d1 = os.path.join(FX, "int1"); d2 = os.path.join(FX, "int2"); d3 = os.path.join(FX, "int3")
        d1s = os.path.join(FX, "int1_snap")
        if not a.int_reuse:
            for d_ in (d1, d2, d3, d1s):
                shutil.rmtree(d_, ignore_errors=True)
            run_fwd(["--sha", sha, "--asof", "2026-06-30", "--start", "2026-03", "--fwd", d1, "--fund-at", sha], log)
            shutil.copytree(d1, d1s)
        # --int-reuse：①～③、⑤ 已由 tps_int*.sh 逐步在前景跑好（單一指令 ≤ 10 分鐘）；本檔只讀結果、自跑 ④
        e1 = TF.read_events(os.path.join(d1s, "events.csv")); m1 = set(json.load(open(os.path.join(d1s, "state.json")))["months"])
        if not a.int_reuse:
            run_fwd(["--sha", sha, "--asof", last, "--start", "2026-03", "--fwd", d1, "--fund-at", sha], log)
        e1b = TF.read_events(os.path.join(d1, "events.csv")); m1b = set(json.load(open(os.path.join(d1, "state.json")))["months"])
        old = e1b.iloc[:len(e1)].reindex(columns=TF.COLS); o0 = e1.reindex(columns=TF.COLS)
        frozen = bool((((o0 != "") & (o0 != old)).to_numpy()).sum() == 0)
        filled6 = int((e1b.iloc[:len(e1)]["出場6"] != "").sum())
        h1 = md5(os.path.join(d1, "events.csv"))
        run_fwd(["--sha", sha, "--asof", last, "--start", "2026-03", "--fwd", d1, "--fund-at", sha], log)
        idem = md5(os.path.join(d1, "events.csv")) == h1
        if not a.int_reuse:
            run_fwd(["--sha", sha, "--asof", last, "--start", "2026-03", "--fwd", d2, "--fund-at", sha], log)
        e2 = TF.read_events(os.path.join(d2, "events.csv"))
        JC2 = [c for c in TF.JUDGE_COLS] + ["e", "壞根(t,e]", "e無成交", "e開盤鎖漲停", "可用"]
        a_ = e1[JC2].reset_index(drop=True); b_ = e2[e2["形成月"].isin(sorted(m1))][JC2].reset_index(drop=True)
        nolook = a_.equals(b_)
        CK["F3_整合"] = {"①資料日 6/30 判": sorted(m1), "①列": len(e1), "②資料尾補判": sorted(m1b - m1), "②舊列非空格不變（凍結）": frozen,
                       "②舊列到期填 6 個月": f"{filled6}／{len(e1)}", "④再跑位元相同（冪等）": idem,
                       "③空夾資料尾重判 2026-03～05 判定欄與 ① 相同（不前視）": nolook}
        # ⑤ 對凍結頻率表、單段描述
        if not a.int_reuse:
            run_fwd(["--sha", sha, "--asof", last, "--start", "2025-06", "--fwd", d3, "--fund-at", sha], log)
        e3 =TF.read_events(os.path.join(d3, "events.csv"))
        fz = EV[(EV["月"] >= "2025-06") & (EV["月"] <= "2026-08")].copy()
        A = e3[e3["形成月"] <= "2026-08"].set_index(["sid", "形成月"]); B = fz.set_index(["sid", "月"])
        both = A.index.intersection(B.index)
        agreeS = float(np.mean([str(A.at[ix, "S"]) == ("" if B.at[ix, "S"] is None else str(B.at[ix, "S"])) for ix in both])) if len(both) else np.nan
        agreeJ = float(np.mean([A.at[ix, "入判"] == str(B.at[ix, "入判"]) for ix in both])) if len(both) else np.nan
        DS = pd.read_csv("backtest/resultsTopSell/desc_single/rows.csv.gz", dtype={"sid": str})
        DS = DS.set_index(["sid", "月"]); jj = [ix for ix in A.index if ix in DS.index and A.at[ix, "R12"] != ""]
        dR = [abs(float(A.at[ix, "R12"]) - float(DS.at[ix, "R12"])) for ix in jj]
        CK["F3_整合"]["⑤對凍結頻率表（2025-06～2026-08）"] = {"前瞻列": int(len(A)), "凍結列": int(len(B)), "共同": int(len(both)),
                                                     "只在前瞻": [list(x) for x in list(A.index.difference(B.index))[:8]], "只在凍結": [list(x) for x in list(B.index.difference(A.index))[:8]],
                                                     "共同列 S 一致率": agreeS, "共同列 入判 一致率": agreeJ}
        CK["F3_整合"]["⑤R12 對單段描述（2025-06～08）"] = {"比對列": len(jj), "最大絕對差": float(max(dR)) if dR else None,
                                                    "差＞1e−6 列": int(sum(x > 1e-6 for x in dR))}
        CK["F3_整合"]["過"] = bool(frozen and idem and nolook and filled6 > 0)
        log(f"[F3] {CK['F3_整合']}｜{time.time() - t0:.0f}s")
    # ══ F7
    lk = subprocess.run([PY, "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True, env={**os.environ, "PYTHONPATH": os.path.expanduser("~/tw-p17")})
    before = set(open(os.path.join(TF.WORK, "git_before2.txt")).read().splitlines())
    now = set(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines())
    extra = sorted(now - before)
    allowed = ("topsell_", "researchTopSell_desc", "resultsTopSell/", "forward/topsell")
    CK["F7"] = {"策略鎖": (lk.stdout + lk.stderr).strip().splitlines()[-1:], "git 新增": extra, "只多本件": all(any(w in x for w in allowed) for x in extra)}
    CK["全過"] = bool(all(v.get("過", True) for k_, v in CK.items() if k_.startswith("F") and isinstance(v, dict) and "過" in v)
                    and all(v["過"] for v in F2.values()) and "相符" in "".join(CK["F7"]["策略鎖"]) and CK["F7"]["只多本件"])
    log(f"[F7] {CK['F7']}｜全過 {CK['全過']}｜{time.time() - t0:.0f}s")
    json.dump(CK, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)


if __name__ == "__main__":
    main()
