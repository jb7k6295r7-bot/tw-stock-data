# -*- coding: utf-8 -*-
"""存貨天數下降＋營收轉強 seq1 頻率表【獨立對帳】——回測線計算子代理。⛔ 只讀結果夾（只寫 freq/check.json、check.log）；⛔ 不算任何報酬。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchInvRev_freq_check [--dry]

K1 登錄 sha 獨立重算 ＋ 裁定 seq454 信在。
K2 本件路徑在 443ee8ce96ec 與 freq.json 記的最新 main 之間 git diff 相同。
K3 事件集合另一條路自算：自讀 fs_xbrl（cr 優先）、自讀 filing_dates（AI1 優先、上傳日 ＜ A）、自算近 4 季營業成本、I、D、存貨÷總資產、法定期限落後、
   up（rev 快取）、上月 cond、閘、非金融、12 個月去重 ⇒（代號, 期別）集合與 events.csv 相同；事件列 D、財報季逐值相同。
K4 配對抽驗 200 件：主對照每檔 up ∧ 財報可算 ∧ 有實體存貨 ∧ D ＞ −15%、描述對照每檔 ¬up；同產業、過閘、e 可進場、市值十分位與前 12 月三分位（自寫排名）相同；主對照候選數自算相同。
K5 freq_段.csv 事件、可進場、主對照配到、主格、n_eff 由 events 自算相同。
K6 無報酬欄；策略鎖 25 支相符；git 工作樹相對開跑前只多本件新檔、結果夾（他處新檔另列）。
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import pickle
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchInvRev_freq as IV               # noqa: E402
from backtest import researchRevTurn_freq as RT              # noqa: E402
from backtest import researchIndMom_freq as IMF              # noqa: E402
from backtest import researchShortageExit_check as SC        # noqa: E402  sha_of、mail

LOGL: list = []


def log(s):
    print(s, flush=True); LOGL.append(str(s))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry", action="store_true"); a = ap.parse_args()
    out = os.path.join(IV.WORK, "dry_ivr") if a.dry else IV.OUT
    CK = {}
    fs = SC.mail(f"sha{IV.REG_SHA}"); rul = SC.mail("seq454")
    CK["K1"] = {"登錄": [os.path.basename(f) for f in fs], "相符": bool(fs) and all(SC.sha_of(f) == IV.REG_SHA for f in fs), "裁定seq454": [os.path.basename(f) for f in rul]}
    log(f"[K1] {CK['K1']}")
    if not (CK["K1"]["相符"] and rul):
        raise SystemExit("⛔ K1")
    J = json.load(open(os.path.join(out, "freq.json"), encoding="utf-8"))
    same = {p: subprocess.run(["git", "diff", "--quiet", IV.BASE_SHA, J["origin/main（最新）"], "--", p]).returncode == 0 for p in IV.SAME_PATHS}
    CK["K2"] = {"全相同": all(same.values())}
    log(f"[K2] {CK['K2']}")
    _, DN, MD = RT.ensure_data(IV.BASE_SHA)
    PX = RT.prices(IV.BASE_SHA, DN, 3)
    CAL, ix, G, C, MC, VP, CB = PX["CAL"], PX["ix"], PX["G"], PX["C"], PX["MC"], PX["VP"], PX["CB"]
    CEND = len(CAL) - 1
    RV = pickle.load(open(os.path.join(RT.WORK, f"rv_all_s{RT.SHIFT_Y}.pkl"), "rb"))["RV"]
    # ── 自讀財報
    L = []
    for f in sorted(glob.glob(os.path.join(DN, "meta", "fs_xbrl", "fs_xbrl_*.csv"))):
        x = pd.read_csv(f, dtype=str, usecols=lambda c: c in ("period", "stock_id", "report", "inventories", "total_assets", "cost_of_sales_ytd"))
        L.append(x)
    X = pd.concat(L)
    X["pri"] = np.where(X["report"] == "cr", 0, 1)
    X = X.sort_values(["stock_id", "period", "pri"], kind="stable").drop_duplicates(["stock_id", "period"], keep="first")
    X["q"] = X["period"].str[:4].astype(int) * 4 + X["period"].str[-1].astype(int) - 1
    for c in ("inventories", "total_assets", "cost_of_sales_ytd"):
        X[c] = pd.to_numeric(X[c], errors="coerce")
    X = X.set_index(["stock_id", "q"])
    inv = X["inventories"].to_dict(); ta = X["total_assets"].to_dict(); cy = X["cost_of_sales_ytd"].to_dict()

    def cq(s, q):
        v = cy.get((s, q), np.nan)
        if q % 4 == 0:
            return v
        p = cy.get((s, q - 1), np.nan)
        return v - p if (np.isfinite(v) and np.isfinite(p)) else np.nan

    def I_of(s, q):
        c4 = [cq(s, j) for j in range(q - 3, q + 1)]
        v = inv.get((s, q), np.nan)
        if not np.isfinite(c4).all() or sum(c4) <= 0 or not np.isfinite(v) or v < 0:
            return np.nan
        return v / (sum(c4) / 365.0)
    fd = pd.read_csv(os.path.join(DN, "meta", "filing_dates.csv"), dtype=str)
    fd["d"] = pd.to_datetime(fd["uploaded_at"].str[:10], errors="coerce"); fd = fd.dropna(subset=["d"])
    fd["q"] = fd["year"].astype(int) * 4 + fd["season"].astype(int) - 1
    a1 = fd[fd["doc_code"] == "AI1"].groupby(["stock_id", "q"])["d"].min(); al = fd.groupby(["stock_id", "q"])["d"].min()
    AVd = al.to_dict(); AVd.update(a1.to_dict())
    AVS = {}
    for (s, q), d in AVd.items():
        AVS.setdefault(s, []).append((d, q))
    AVS = {s: (np.array([d for d, _ in sorted(v)], dtype="datetime64[ns]"), np.maximum.accumulate(np.array([q for _, q in sorted(v)]))) for s, v in AVS.items()}

    def deadline(q):
        y, qq = q // 4, q % 4 + 1
        return {1: pd.Timestamp(y, 5, 15), 2: pd.Timestamp(y, 8, 14), 3: pd.Timestamp(y, 11, 14), 4: pd.Timestamp(y + 1, 3, 31)}[qq]
    pit = IMF.load_pit(DN)

    def avail(P):
        y, m = int(P[:4]), int(P[5:7]); y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
        return int(np.searchsorted(CAL.values, np.datetime64(pd.Timestamp(y2, m2, 15 if P >= "2026-01" else 10)), "right"))
    AP = {P: avail(P) for P in RV["period"].unique()}
    rows = {}
    for s, P, up in zip(RV["sid"], RV["period"], RV["up"]):
        A_ = AP[P]
        if A_ > CEND:
            continue
        t = CAL[A_]; z = AVS.get(s)
        q = -1
        if z is not None:
            k = int(np.searchsorted(z[0], np.datetime64(t), "left")) - 1
            q = int(z[1][k]) if k >= 0 else -1
        qr = max(k for k in range(t.year * 4 - 8, t.year * 4 + 4) if deadline(k) < t)
        ok = q >= 0 and qr - q < 2
        Iq = I_of(s, q) if ok else np.nan; Ip = I_of(s, q - 4) if ok else np.nan
        D = Iq / Ip - 1 if (np.isfinite(Iq) and np.isfinite(Ip) and Ip > 0) else np.nan
        v, w = inv.get((s, q), np.nan), ta.get((s, q), np.nan)
        phys = bool(np.isfinite(v) and np.isfinite(w) and w > 0 and v / w >= 0.05)
        rows[(s, P)] = (bool(up), ok, phys, D, q, A_)
    cond = {k: (v[0] and v[1] and v[2] and np.isfinite(v[3]) and v[3] <= -0.15) for k, v in rows.items()}
    mine = []; last = {}
    for (s, P) in sorted(k for k, c in cond.items() if c):
        n = int(P[:4]) * 12 + int(P[5:7]) - 2
        if cond.get((s, f"{n // 12:04d}-{n % 12 + 1:02d}"), False):
            continue
        i = ix.get(s, -1); A_ = rows[(s, P)][5]
        if i < 0 or A_ < 1 or not G[i, A_ - 1]:
            continue
        if (pit.at(s, CAL[A_])[0] or "") == "金融保險":
            continue
        mm = int(P[:4]) * 12 + int(P[5:7])
        if s in last and mm - last[s] < 12:
            continue
        last[s] = mm; mine.append((s, P))
    EV = pd.read_csv(os.path.join(out, "events.csv.gz"), dtype={"sid": str, "期別": str, "主對照": str, "描述對照": str}, keep_default_na=False)
    theirs = set(zip(EV["sid"], EV["期別"])); mineS = set(mine)
    if a.dry:
        mineS = {k for k in mineS if k[0] in set(EV["sid"]) or True} & {k for k in mineS if k[0] in set(RV["sid"])}
    dv = 0
    for s, P, D in zip(EV["sid"], EV["期別"], EV["D"]):
        r = rows.get((s, P))
        if r is None or not (abs(r[3] - float(D)) <= 1e-9 * max(1, abs(r[3]))):
            dv += 1
    CK["K3"] = {"自算": len(mineS), "events": len(theirs), "只在自算": len(mineS - theirs) if not a.dry else "乾跑不比", "只在events": len(theirs - mineS), "D不同": dv}
    log(f"[K3] {CK['K3']}")
    # ── K4 配對抽驗
    def r12(i, p1):
        if not np.isfinite(C[i, p1]):
            return np.nan
        p0 = int(np.searchsorted(CAL.values, np.datetime64(CAL[p1] - pd.DateOffset(months=12)), "right")) - 1
        vp = VP[i]; pr = vp[vp <= p0]
        if p0 < 0 or not len(pr):
            return np.nan
        if CB[i, p1] - CB[i, int(pr[-1])] > 0:
            return np.nan
        return C[i, p1] / C[i, int(pr[-1])] - 1

    def rk(v):
        v = np.asarray(v, float); ok = np.isfinite(v); o = np.full(len(v), np.nan); vv = v[ok]; s_ = np.sort(vv)
        lo = np.searchsorted(s_, vv, "left"); hi = np.searchsorted(s_, vv, "right"); o[ok] = (lo + (hi - lo + 1) / 2.0) / len(vv)
        return o
    M = EV[EV["主對照配到"].astype(str) == "True"]
    M = M.sample(min(200, len(M)), random_state=9)
    b4 = {"抽驗": len(M), "主對照不符": 0, "描述對照不符": 0, "候選數不符": 0}
    memo = {}
    RVP = RV.groupby("period")
    for _, r in M.iterrows():
        P = r["期別"]; A_ = AP[P]; p1 = A_ - 1
        if P not in memo:
            U = np.flatnonzero(G[:, p1]); mc = MC[U, p1]; mc = np.where(np.isfinite(mc) & (mc > 0), mc, np.nan)
            pm, pr = rk(mc), rk([r12(int(i), p1) for i in U])
            memo[P] = ({int(i): (int(math.ceil(x * 10)) if np.isfinite(x) else -1) for i, x in zip(U, pm)},
                       {int(i): (int(math.ceil(x * 3)) if np.isfinite(x) else -1) for i, x in zip(U, pr)})
        dec, ter = memo[P]; i0 = ix[r["sid"]]; ind = pit.at(r["sid"], CAL[A_])[0] or ""

        def okc(s, kind):
            j = ix.get(s, -1)
            if j < 0 or not G[j, p1] or dec.get(j) != dec[i0] or ter.get(j) != ter[i0] or dec[i0] < 0 or ter[i0] < 0:
                return False
            if (pit.at(s, CAL[A_])[0] or "") != ind or ind == "金融保險" or IMF.entry_flag(PX, j, A_, A_ + 1) != "保留":
                return False
            v = rows.get((s, P))
            if v is None:
                return False
            return (v[0] and v[1] and v[2] and np.isfinite(v[3]) and v[3] > -0.15) if kind == "m" else (not v[0])
        for s in r["主對照"].split():
            b4["主對照不符"] += int(not okc(s, "m"))
        for s in r["描述對照"].split():
            b4["描述對照不符"] += int(not okc(s, "d"))
        nc = sum(1 for s in RVP.get_group(P)["sid"] if okc(s, "m"))
        b4["候選數不符"] += int(nc != int(r["主對照候選數"]))
    CK["K4"] = b4
    log(f"[K4] {b4}")
    # ── K5
    FR = pd.read_csv(os.path.join(out, "freq_段.csv"), encoding="utf-8-sig")
    k5 = []
    for _, r in FR.iterrows():
        d = EV[EV["段"] == r["段"]]; m = d[(d["主對照配到"].astype(str) == "True") & (d["H250走得完"].astype(str) == "True")]
        mine_ = [len(d), int((d["進場"] == "保留").sum()), int((d["主對照配到"].astype(str) == "True").sum()), len(m), m["月"].nunique()]
        th = [r["事件(新成立∧過閘∧去重)"], r["e可進場"], r["主對照配到"], r["主格事件"], r["主格月數=n_eff"]]
        if [int(x) for x in mine_] != [int(x) for x in th]:
            k5.append((r["段"], mine_, th))
    CK["K5"] = {"不符": k5}
    log(f"[K5] {CK['K5']}")
    cols = list(EV.columns) + [c for f in glob.glob(os.path.join(out, "*.csv")) for c in pd.read_csv(f, nrows=0, encoding="utf-8-sig").columns]
    badc = [c for c in cols if any(w in c for w in ("報酬", "年化", "淨值", "回落", "價格", "收盤", "R事件", "X平均")) and "配對特徵" not in c]
    lk = subprocess.run([os.path.expanduser("~/tw-p16/.venv/bin/python"), "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True,
                        env={**os.environ, "PYTHONPATH": os.path.expanduser("~/tw-p17")})
    lock = (lk.stdout + lk.stderr).strip().splitlines()[-1:]
    before = set(open(os.path.join(RT.WORK, "git_before_ivr.txt")).read().splitlines())
    now = set(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines())
    extra = sorted(now - before)
    allowed = ("researchInvRev_freq", "resultsInvRev")
    others = [x for x in extra if not any(w in x for w in allowed)]
    CK["K6"] = {"報酬類欄": badc, "策略鎖": lock, "git 新增": extra, "本件以外（他處同時新增）": others, "只多本件或他處新檔": all(x.startswith("?? ") for x in others)}
    ok = (CK["K1"]["相符"] and CK["K2"]["全相同"] and (a.dry or (not (mineS ^ theirs))) and dv == 0 and b4["主對照不符"] == 0 and b4["描述對照不符"] == 0
          and b4["候選數不符"] == 0 and not k5 and not badc and "相符" in "".join(lock) and CK["K6"]["只多本件或他處新檔"])
    CK["全過"] = bool(ok)
    log(f"[K6] {CK['K6']}｜全過 {ok}")
    json.dump(CK, open(os.path.join(out, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=RT.jdef)
    open(os.path.join(out, "check.log"), "w", encoding="utf-8").write("\n".join(LOGL) + "\n")


if __name__ == "__main__":
    main()
