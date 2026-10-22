# -*- coding: utf-8 -*-
"""缺貨型持股確認後怎麼賣 seq1 頻率表【獨立對帳】——回測線計算子代理。⛔ 只讀結果夾、不改任何既有檔（只寫 freq/check.json、check.log）；⛔ 不算任何報酬。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchShortageExit_freq_check [--dry]

K1 登錄 sha 獨立重算（信箱根目錄＋_封存-*，去 pw1 行 sha256 前 16 碼）＋ 裁定 seq447 信在。
K2 事件：由 rv 快取自算 起點 ∧ 面板 ∧ G[A−1] ∧ 24 個月去重 ⇒（代號, 期別）集合與 events.csv 完全相同；母體別（八業／一般／無類別）逐列自判相同。
K3 七種賣法判到位置：抽 400 個主格事件（e 可進場 ∧ E250 走得完），另一條路自算（C1～C3 直接查 rv 列、C4 逐判日 Python 迴圈、C5 pandas cummax、
   C6 自讀 filing_dates（AI1 優先）選季、自讀 fin_hist 差分成單季 EPS、C7 自讀 filing_dates 求可判日）⇒ k 偏移逐值相同。
K4 freq_段.csv（E250）判到、賣出、事件、月數與 counts.csv 主格、n_eff 由 events.csv.gz 自算相同。
K5 輸出無報酬欄；策略鎖 25 支相符；git 工作樹相對開跑前只多本件新檔與結果夾。
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import pickle
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchRevTurn_freq as RT             # noqa: E402
from backtest import researchShortageExit_freq as SX        # noqa: E402
from backtest import researchIndMom_freq as IMF             # noqa: E402

MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
LOGL: list = []


def log(s):
    print(s, flush=True); LOGL.append(str(s))


def sha_of(f):
    b = open(f, "rb").read()
    return hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]


def avail_k(CAL, P):
    y, m = int(P[:4]), int(P[5:7]); y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
    return int(np.searchsorted(CAL.values, np.datetime64(pd.Timestamp(y2, m2, 15 if P >= "2026-01" else 10)), "right"))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry", action="store_true"); ap.add_argument("--procs", type=int, default=3); a = ap.parse_args()
    out = os.path.join(SX.WORK, "dry_sx") if a.dry else SX.OUT
    CK = {}
    fs = [f for d in [MAILBOX] + sorted(glob.glob(os.path.join(MAILBOX, "_封存-*"))) for f in glob.glob(os.path.join(d, "*.md")) if f"sha{SX.REG_SHA}" in os.path.basename(f)]
    rul = [f for d in [MAILBOX] + sorted(glob.glob(os.path.join(MAILBOX, "_封存-*"))) for f in glob.glob(os.path.join(d, "*.md")) if "seq447" in os.path.basename(f)]
    CK["K1_登錄sha"] = {"檔": [os.path.basename(f) for f in fs], "相符": bool(fs) and all(sha_of(f) == SX.REG_SHA for f in fs), "裁定seq447": [os.path.basename(f) for f in rul]}
    log(f"[K1] {CK['K1_登錄sha']}")
    if not CK["K1_登錄sha"]["相符"] or not rul:
        raise SystemExit("⛔ K1")
    J = json.load(open(os.path.join(out, "freq.json"), encoding="utf-8")); sha = J["origin/main"]
    _, DN, MD = RT.ensure_data(sha)
    tag = "all" if not a.dry else f"drysx{J['乾跑股數']}"
    RV = pickle.load(open(os.path.join(RT.WORK, f"rv_{tag}_s{RT.SHIFT_Y}.pkl"), "rb"))["RV"]
    EV = pd.read_csv(os.path.join(out, "events.csv.gz"), dtype={"sid": str, "期別": str})
    PX = RT.prices(sha, DN, a.procs)
    CAL, ix, G, C, BAD, VP = PX["CAL"], PX["ix"], PX["G"], PX["C"], PX["BAD"], PX["VP"]
    CEND = len(CAL) - 1
    # ── K2
    st = RV[RV["up"] & ~RV["up_prev"]].sort_values(["sid", "period"])
    keep = []; lastk = {}
    for sid, P in zip(st["sid"], st["period"]):
        i = ix.get(sid, -1)
        if i < 0:
            continue
        k = avail_k(CAL, P)
        if k > CEND or k < 1 or not G[i, k - 1]:
            continue
        mm = int(P[:4]) * 12 + int(P[5:7])
        if sid in lastk and mm - lastk[sid] < SX.DEDUP_M:
            continue
        lastk[sid] = mm; keep.append((sid, P))
    mine = set(keep); theirs = set(zip(EV["sid"], EV["期別"]))
    pit = IMF.load_pit(DN)
    popbad = 0
    for sid, A_, pop in zip(EV["sid"], EV["A"], EV["母體"]):
        ind = pit.at(sid, pd.Timestamp(A_))[0] or ""
        p2 = "缺貨型" if ind in SX.RAW8 else ("一般股" if ind else "無類別")
        popbad += int(p2 != pop)
    CK["K2_事件與母體"] = {"自算": len(mine), "events": len(theirs), "只在自算": len(mine - theirs), "只在events": len(theirs - mine), "母體別不同": popbad}
    log(f"[K2] {CK['K2_事件與母體']}")
    # ── K3 判到位置
    RVd = {s: g.set_index("period") for s, g in RV.groupby("sid")}
    fd = pd.read_csv(os.path.join(DN, "meta", "filing_dates.csv"), dtype=str)
    fd["d"] = pd.to_datetime(fd["uploaded_at"].str[:10], errors="coerce"); fd = fd.dropna(subset=["d"])
    fd["q"] = fd["year"].astype(int) * 4 + fd["season"].astype(int) - 1
    a1 = fd[fd["doc_code"] == "AI1"].groupby(["stock_id", "q"])["d"].min(); al = fd.groupby(["stock_id", "q"])["d"].min()
    AV = al.to_dict(); AV.update(a1.to_dict())
    AVS = {}
    for (s, q), d in AV.items():
        AVS.setdefault(s, []).append((d, q))
    fl = []
    for f in sorted(glob.glob(os.path.join(DN, "mops", "fin_hist", "*.csv"))):
        b = os.path.basename(f)[:6]
        x = pd.read_csv(f, dtype={"stock_id": str}, usecols=["stock_id", "eps_ytd"]); x["q"] = int(b[:4]) * 4 + int(b[5]) - 1; fl.append(x)
    FN = pd.concat(fl).drop_duplicates(["stock_id", "q"], keep="last"); FN["eps_ytd"] = pd.to_numeric(FN["eps_ytd"], errors="coerce")
    EPS = {s: dict(zip(g["q"], g["eps_ytd"])) for s, g in FN.groupby("stock_id")}

    def eps1(s, q):
        y = EPS.get(s, {})
        v = y.get(q, np.nan)
        if q % 4 == 0:
            return v
        p = y.get(q - 1, np.nan)
        return v - p if (np.isfinite(v) and np.isfinite(p)) else np.nan

    def r4(s, q):
        v = [eps1(s, j) for j in range(q - 3, q + 1)]
        return float(sum(v)) if np.isfinite(v).all() else np.nan
    GM, _ = RT.gm_table(DN)
    PN = pickle.load(open(SX.PANEL, "rb")); PE = np.asarray(PN["P"]["本益比"], float); MEp = np.asarray(PN["MEp"]); del PN
    sellable = None
    M = EV[(EV["進場"] == "保留") & (EV["E250走得完"] == True)]  # noqa: E712
    M = M.sample(min(400, len(M)), random_state=3)
    bad = {c: 0 for c in SX.RULES}
    periods = sorted(RV["period"].unique())
    for _, r in M.iterrows():
        sid = r["sid"]; i = ix[sid]; P = r["期別"]
        A_ = int(np.searchsorted(CAL.values, np.datetime64(pd.Timestamp(r["A"])))); e = A_ + 1
        W = min(e + 500, CEND)
        bb = [p for p in range(e + 1, W + 1) if BAD[i, p]]
        if bb:
            W = min(W, bb[0] - 1)
        lv = int(VP[i][-1])
        if CEND - lv >= 5 and lv < W:
            W = lv
        kmax = W - 1
        g = RVd.get(sid)
        Qs = [(Q, avail_k(CAL, Q)) for Q in periods if Q > P and g is not None and Q in g.index]
        Qs = [(Q, k) for Q, k in Qs if e <= k <= kmax]
        res = {}
        res["C1"] = next((k for Q, k in Qs if g.at[Q, "flag_mom2"] == 1.0), -1)

        def prevm(Q):
            n = int(Q[:4]) * 12 + int(Q[5:7]) - 2
            return f"{n // 12:04d}-{n % 12 + 1:02d}"
        res["C2"] = next((k for Q, k in Qs if (prevm(Q) in g.index) and np.isfinite(g.at[Q, "yoy"]) and np.isfinite(g.at[prevm(Q), "yoy"])
                          and g.at[Q, "yoy"] < 0 and g.at[prevm(Q), "yoy"] >= 0), -1)
        res["C3"] = next((k for Q, k in Qs if np.isfinite(g.at[Q, "accel"]) and g.at[Q, "accel"] <= -0.05), -1)
        k4 = -1
        for d in [e] + [k for _, k in Qs]:
            if d > kmax or not np.isfinite(C[i, d]):
                continue
            win = [p for p in range(max(0, d - 249), d + 1) if np.isfinite(C[i, p])]
            bads = [p for p in win[1:] if BAD[i, p]]
            if bads:
                win = [p for p in win if p >= bads[-1]]
            if C[i, d] / max(C[i, p] for p in win) - 1 <= -0.30:
                k4 = d; break
        res["C4"] = k4
        s_ = pd.Series(C[i, e:kmax + 1]) if kmax >= e else pd.Series([], dtype=float)
        cm = s_.cummax()
        hit = s_.notna() & (s_ <= 0.7 * cm)
        res["C5"] = e + int(np.flatnonzero(hit.to_numpy())[0]) if hit.any() else -1
        k6 = -1
        lst = sorted(AVS.get(sid, []))
        for k in np.flatnonzero((MEp >= e) & (MEp <= kmax)):
            t = CAL[int(MEp[k])]
            qs = [q for d, q in lst if d < t]
            if not qs:
                continue
            q = max(qs)
            win = [r4(sid, j) for j in range(q - 19, q + 1)]
            pw = PE[i, max(0, k - 59):k + 1]; pw = pw[np.isfinite(pw)]
            if not (np.isfinite(PE[i, k]) and len(pw) >= 36 and np.isfinite(win).all()):
                continue
            if win[-1] > 0 and win[-1] >= max(win) and PE[i, k] <= np.percentile(pw, 20):
                k6 = int(MEp[k]); break
        res["C6"] = k6
        k7 = -1
        gm = GM.get(sid, {})
        for d, q in sorted((d, q) for d, q in lst):
            pq = int(np.searchsorted(CAL.values, np.datetime64(d), "right"))
            if pq < e or pq > kmax:
                continue
            v = [gm.get(q, np.nan), gm.get(q - 4, np.nan), gm.get(q - 1, np.nan), gm.get(q - 5, np.nan)]
            if np.isfinite(v).all() and v[0] - v[1] < 0 and v[2] - v[3] >= 0:
                k7 = pq; break
        res["C7"] = k7
        for c in SX.RULES:
            mine_ = (res[c] - e) if res[c] >= 0 else None
            th = r[f"{c}_k偏移"]
            th = None if (th is None or (isinstance(th, float) and not np.isfinite(th))) else int(th)
            if mine_ != th:
                bad[c] += 1
    CK["K3_判到位置自算"] = {"抽驗主格事件": len(M), "不同": bad}
    log(f"[K3] {CK['K3_判到位置自算']}")
    # ── K4
    FR = pd.read_csv(os.path.join(out, "freq_段.csv"), encoding="utf-8-sig")
    CNT = pd.read_csv(os.path.join(out, "counts.csv"), encoding="utf-8-sig")
    k4b = []
    pops = {"缺貨型": EV["母體"] == "缺貨型", "一般股": EV["母體"] == "一般股", **{f"族群:{g}": EV["族群"].fillna("").str.contains(g) for g in SX.GROUPS}}
    for _, r in FR[FR["E"] == 250].iterrows():
        d = EV[(EV["段"] == r["段"]) & pops[r["母體"]] & (EV["進場"] == "保留") & (EV["E250走得完"] == True)]  # noqa: E712
        col = d[f"{r['賣法']}_E250"]
        mine_ = [len(d), int(d["進場月"].nunique()), int((col != "不賣").sum()), int((col == "賣出").sum())]
        th = [r["事件"], r["月數"], r["判到"], r["賣出"]]
        if [int(x) for x in mine_] != [int(x) for x in th]:
            k4b.append((r["段"], r["母體"], r["賣法"], mine_, th))
    for _, r in CNT.iterrows():
        d = EV[(EV["段"] == r["段"]) & pops[r["母體"]] & (EV["進場"] == "保留") & (EV["E250走得完"] == True)]  # noqa: E712
        if [len(d), d["進場月"].nunique()] != [int(r["E250走得完(主格)"]), int(r["主格進場月數=n_eff"])]:
            k4b.append((r["段"], r["母體"], "counts"))
    CK["K4_表自算"] = {"不符": k4b}
    log(f"[K4] {CK['K4_表自算']}")
    # ── K5
    cols = list(EV.columns) + [c for f in glob.glob(os.path.join(out, "*.csv")) for c in pd.read_csv(f, nrows=0, encoding="utf-8-sig").columns]
    badc = [c for c in cols if any(w in c for w in ("報酬", "年化", "淨值", "回落率", "價格", "收盤", "開盤價", "R值", "d值"))]
    lk = subprocess.run([os.path.expanduser("~/tw-p16/.venv/bin/python"), "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True,
                        env={**os.environ, "PYTHONPATH": os.path.expanduser("~/tw-p17")})
    lock = (lk.stdout + lk.stderr).strip().splitlines()[-1:]
    before = set(open(os.path.join(RT.WORK, "git_before.txt")).read().splitlines())
    now = set(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines())
    extra = sorted(now - before)
    allowed = ("researchRevTurn_freq", "researchShortageExit_freq", "resultsRevTurn", "resultsShortageExit")
    CK["K5"] = {"報酬類欄": badc, "策略鎖": lock, "git 新增（相對開跑前）": extra, "git 只多本件": all(any(w in x for w in allowed) for x in extra)}
    ok = (CK["K1_登錄sha"]["相符"] and not (mine ^ theirs) and popbad == 0 and all(v == 0 for v in bad.values()) and not k4b and not badc
          and "相符" in "".join(lock) and CK["K5"]["git 只多本件"])
    CK["全過"] = bool(ok)
    log(f"[K5] {CK['K5']}｜全過 {ok}")
    json.dump(CK, open(os.path.join(out, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=RT.jdef)
    open(os.path.join(out, "check.log"), "w", encoding="utf-8").write("\n".join(LOGL) + "\n")


if __name__ == "__main__":
    main()
