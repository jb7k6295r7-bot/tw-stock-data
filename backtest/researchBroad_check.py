# -*- coding: utf-8 -*-
"""廣撒長抱 seq1 正式跑【獨立對帳】——回測線計算子代理。⛔ 只讀結果夾、不改任何既有檔（只寫 main/check.json、check.log）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBroad_check [--dry0]

K1 登錄 sha 獨立重算 ＋ 裁定 seq454、seq455 信在。
K2 頻率表重建：~/brdwork/rebuild 與已 commit 的 resultsBroad/freq 逐檔逐字再比一次。
K3 出場另路：抽 5,000 筆以 BAD／TRD／UPL／有效 K 棒直接判，與 prep 相同。
K4 帳另路（全部 9 條 0.585% 版）：先算每批「每 1 元的整批價值路徑」g_j（逐筆 Cf÷O、扣成本、賣後持現金、買不到持現金），
   再逐批決定投入 A_j ＝ min(前一日權益 ÷ n_H, 可用現金) ⇒ 權益曲線；與 nav.csv.gz 逐日相同（相對差 ＜ 1e−9）。
K5 指標：大盤報酬指數另讀（git show）、各格三段年化、MDD、比值、標籤由 nav.csv 自算與 cells.csv 相同；挑格與判定自算相同。
K6 對純廣撒差與隨機：vs_broad 的年化差、隨機 ≥ 訊號比例由 cells.csv 與隨機檔自算相同；另以自寫抽樣與 K4 帳重算第 0、1、2 次隨機的三段年化，與隨機檔相同。
K7 第 25～36 個月與前 5 檔：由 K4 的 g_j 自算 G1、G2、純廣撒 H750 第 25～36 月平均、挑中格 Σ前5÷Σ整批 相同。
K8 策略鎖相符（25 支）；git 相對正式跑前只多本件新檔與結果夾。
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import io
import json
import os
import pickle
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchBroad as BM                    # noqa: E402
from backtest import researchBroad_freq as BF               # noqa: E402
from backtest import researchRevTurn_freq as RT             # noqa: E402
from backtest import researchShortageExit as SM             # noqa: E402

MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
LOGL: list = []


def log(s):
    print(s, flush=True); LOGL.append(str(s))


def sha_of(f):
    b = open(f, "rb").read()
    return hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]


def close(a, b, tol=1e-9):
    a = float(a); b = float(b)
    return bool((np.isnan(a) and np.isnan(b)) or abs(a - b) <= tol * max(1.0, abs(a)))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry0", action="store_true"); a = ap.parse_args()
    out = os.path.join(BF.WK, "dry0") if a.dry0 else BM.OUT
    CK = {}
    dirs = [MAILBOX] + sorted(glob.glob(os.path.join(MAILBOX, "_封存-*")))
    allmd = [f for d in dirs for f in glob.glob(os.path.join(d, "*.md"))]
    fs = [f for f in allmd if f"sha{BF.REG_SHA}" in os.path.basename(f)]
    ruls = {q: [os.path.basename(f) for f in allmd if q in os.path.basename(f) and "裁定線-" in os.path.basename(f)] for q in ("seq454", "seq455")}
    CK["K1"] = {"相符": bool(fs) and all(sha_of(f) == BF.REG_SHA for f in fs), "裁定": ruls}; log(f"[K1] {CK['K1']}")
    k2 = {}
    for f in BM.FILES:
        x = pd.read_csv(os.path.join(BM.REB, f), dtype=str, keep_default_na=False); y = pd.read_csv(os.path.join(BF.OUT, f), dtype=str, keep_default_na=False)
        k2[f] = bool(x.shape == y.shape and (x.values == y.values).all())
    CK["K2"] = k2; log(f"[K2] {k2}")
    MJ = json.load(open(os.path.join(out, "main.json"), encoding="utf-8")); sha = MJ["origin/main"]
    PR = pickle.load(open(os.path.join(BF.WK, f"prep_{sha[:12]}.pkl"), "rb"))
    sha_, DN, MD = RT.ensure_data(sha)
    PX = RT.prices(sha, DN, 4)
    CAL, ix = PX["CAL"], PX["ix"]; CEND = len(CAL) - 1
    C, BAD, TRD, UPL, LASTV = PX["C"], PX["BAD"], PX["TRD"], PX["UPL"], PX["LASTV"]
    O, _ = SM.seam_open(PX)
    BT = PR["BT"]
    # ── K3
    def ex2(i, b, H):
        mat = b + H - 1
        if not (np.isfinite(C[i, b]) and TRD[i, b] and np.isfinite(O[i, b]) and O[i, b] > 0) or BAD[i, b] or UPL[i, b]:
            return None
        end = min(mat, CEND); opts = []
        bb = np.flatnonzero(BAD[i, b + 1:end + 1])
        if len(bb):
            q = b + int(bb[0])
            while not np.isfinite(C[i, q]):
                q -= 1
            opts.append(q)
        if LASTV[i] < end and CEND - LASTV[i] >= 5:
            opts.append(int(LASTV[i]))
        if opts:
            return min(opts)
        if mat > CEND:
            return CEND + 1
        q = mat
        while q <= CEND and not np.isfinite(C[i, q]):
            q += 1
        return q if q <= CEND else CEND + 1
    keys = list(PR["LX"]); rng = np.random.default_rng(17)
    samp = [keys[k] for k in rng.choice(len(keys), 5000, replace=False)]
    b3 = sum(1 for k in samp if ex2(*k) != PR["LX"][k][0])
    CK["K3"] = {"抽": 5000, "不同": b3}; log(f"[K3] {CK['K3']}")
    # ── K4
    lastc = {}

    def cpath(i, b, q):
        seg = C[i, b:q + 1]
        idx = np.where(np.isfinite(seg), np.arange(len(seg)), 0)
        return seg[np.maximum.accumulate(idx)]

    def gpaths(members, H, zero):
        cst = 0.0 if zero else BM.COST
        G = []
        for j, x in enumerate(BT):
            b = x["b"]; mat = b + H - 1; lst = members[j]
            r = mat if mat <= CEND else None
            info = []
            for s in lst:
                i = ix[s]; q = PR["LX"][(i, b, H)][0]
                info.append((i, q))
                if q is not None and q > mat:
                    r = None if (q > CEND or r is None) else max(r, q)
            end = CEND if r is None else r
            g = np.zeros(end - b + 1); lots = []
            if not lst:
                g[:] = 1.0
            else:
                w = 1.0 / len(lst)
                for i, q in info:
                    if q is None:
                        g += w; continue
                    qq = min(q, CEND)
                    p = np.ones(qq - b + 1) if zero else cpath(i, b, qq) / O[i, b] * (1 - cst)
                    g[:qq - b + 1] += w * p
                    g[qq - b + 1:] += w * p[-1]
                    lots.append(w * p[-1] - w)
            G.append((b, r, g, lots))
        return G

    def navof(GP, H):
        n = CEND + 1; nH = round(H / 21)
        nav = np.ones(n); act = []   # (b, r, g, A)
        freecash = 1.0
        val = np.zeros(n)
        fevents = np.zeros(n + 2)
        Aj_list = []
        for (b, r, g, _) in GP:
            keep = []
            for (b2, r2, g2, A2) in act:
                if r2 is not None and r2 < b:
                    freecash += A2 * g2[-1]
                else:
                    keep.append((b2, r2, g2, A2))
            act = keep
            eq = freecash + sum(A2 * g2[b - 1 - b2] for (b2, r2, g2, A2) in act if b - 1 - b2 >= 0)
            A = min(eq / nH, max(freecash, 0.0))
            freecash -= A; fevents[b] -= A
            act.append((b, r, g, A)); Aj_list.append(A)
            val[b:b + len(g)] += A * g
            if r is not None:
                fevents[r + 1] += A * g[-1]
        nav = 1.0 + np.cumsum(fevents)[:n] + val
        return nav, Aj_list
    NV = pd.read_csv(os.path.join(out, "nav.csv.gz"), encoding="utf-8-sig")
    p0 = int(CAL.searchsorted(pd.Timestamp(NV["date"].iloc[0])))
    MEM = {"G1": [x["G1"] for x in BT], "G2": [x["G2"] for x in BT], "純廣撒": [x["W1"] for x in BT]}
    k4 = {}; GPS = {}
    for G in ("G1", "G2", "純廣撒"):
        for H in BF.HS:
            GP = gpaths(MEM[G], H, a.dry0); GPS[(G, H)] = GP
            nav, _ = navof(GP, H)
            th = NV[f"{G} H{H}"].to_numpy(float)
            k4[f"{G} H{H}"] = float(np.max(np.abs(nav[p0:] / th - 1)))
    CK["K4_帳另路(最大相對差)"] = k4; log(f"[K4] {k4}")
    # ── K5
    tri = pd.read_csv(io.BytesIO(subprocess.run(["git", "show", f"{sha}:data/history/market_tri.csv"], capture_output=True, check=True).stdout))
    tri["date"] = pd.to_datetime(tri["date"]); tri = tri.drop_duplicates("date").set_index("date")["close"].astype(float)
    TRI = tri.reindex(tri.index.union(CAL)).ffill().reindex(CAL).to_numpy(float)
    if a.dry0:
        TRI = np.ones(len(CAL))
    CE = pd.read_csv(os.path.join(out, "cells.csv"), encoding="utf-8-sig")
    navs = {c: np.concatenate([np.ones(p0), NV[c].to_numpy(float)]) for c in NV.columns if c != "date"}

    def mt(v, a0, z):
        w = v[a0:z + 1]; yrs = (CAL[z] - CAL[a0]).days / 365.25
        cg = (w[-1] / w[0]) ** (1 / yrs) - 1; mdd = (w / np.maximum.accumulate(w) - 1).min()
        return cg, mdd, (cg / abs(mdd) if mdd < 0 else np.nan)
    SB = {}
    for nm, x_, y_ in BF.SEGS:
        a_ = max(int(CAL.searchsorted(pd.Timestamp(x_))), BT[0]["b"]); z_ = min(int(CAL.searchsorted(pd.Timestamp(y_), "right")) - 1, CEND); SB[nm] = (a_ - 1, z_)
    k5 = []; lab = {}
    for G in ("G1", "G2", "純廣撒"):
        for H in BF.HS:
            for nm, (a0, z) in SB.items():
                cg, mdd, rt = mt(navs[f"{G} H{H}"], a0, z); tc, tm, trt = mt(TRI, a0, z)
                L = "合格" if (cg > tc and rt >= trt) else ("另列" if cg > tc else "不合格")
                r = CE[(CE["格"] == G) & (CE["H"] == H) & (CE["段"] == nm) & (CE["版本"] == "0.585%")].iloc[0]
                lab[(G, H, nm)] = (L, rt)
                if not (close(cg, r["年化"]) and close(mdd, r["MDD"]) and close(rt, r["比值"]) and close(tc, r["大盤年化"]) and L == r["標籤"]):
                    k5.append((G, H, nm, [cg, mdd, rt, tc, L], [r["年化"], r["MDD"], r["比值"], r["大盤年化"], r["標籤"]]))
    GR = {"合格": 2, "另列": 1, "不合格": 0}
    sig = [(G, H) for G in ("G1", "G2") for H in BF.HS]
    pk = max(sig, key=lambda gh: (GR[lab[(*gh, "探索")][0]], lab[(*gh, "探索")][1] if np.isfinite(lab[(*gh, "探索")][1]) else -9))
    CK["K5"] = {"不符": k5, "挑中自算": list(pk), "挑中檔": MJ["挑中"], "同": list(pk) == MJ["挑中"]}; log(f"[K5] {CK['K5']}")
    # ── K6
    VS = pd.read_csv(os.path.join(out, "vs_broad.csv"), encoding="utf-8-sig")
    k6 = []
    for r in VS.to_dict("records"):
        s = CE[(CE["格"] == r["格"]) & (CE["H"] == r["H"]) & (CE["段"] == r["段"]) & (CE["版本"] == "0.585%")].iloc[0]
        bb = CE[(CE["格"] == "純廣撒") & (CE["H"] == r["H"]) & (CE["段"] == r["段"]) & (CE["版本"] == "0.585%")].iloc[0]
        if not close((s["年化"] - bb["年化"]) * 100, r["年化差(點)"]):
            k6.append(("差", r["格"], r["H"], r["段"]))
        fp = os.path.join(BF.WK, f"rand_{r['格']}_{'dry0' if a.dry0 else 'real'}.pkl")
        if "隨機年化≥訊號比例" in r and os.path.exists(fp):
            rd = pd.read_pickle(fp); d = rd[(rd["H"] == r["H"]) & (rd["段"] == r["段"])]
            if not close((d["年化"] >= s["年化"]).mean(), r["隨機年化≥訊號比例"]):
                k6.append(("隨機比例", r["格"], r["H"], r["段"]))
    for G in ("G1", "G2"):
        fp = os.path.join(BF.WK, f"rand_{G}_{'dry0' if a.dry0 else 'real'}.pkl")
        rd = pd.read_pickle(fp)
        for rr in (0, 1, 2):
            rg = np.random.default_rng([BF.SEED, rr]); draw = []
            for x in BT:
                pool = sorted(x["W1"]); nb = len(x[G])
                draw.append([pool[k] for k in rg.permutation(len(pool))[:nb]] if nb else [])
            for H in BF.HS:
                nav, _ = navof(gpaths(draw, H, a.dry0), H)
                for nm, (a0, z) in SB.items():
                    cg = mt(nav, a0, z)[0]
                    th = rd[(rd["r"] == rr) & (rd["H"] == H) & (rd["段"] == nm)]["年化"].iloc[0]
                    if not close(cg, th, 1e-8):
                        k6.append(("隨機重算", G, rr, H, nm, cg, th))
    CK["K6"] = {"不符": k6[:10], "數": len(k6)}; log(f"[K6] {CK['K6']}")
    # ── K7
    M25 = pd.read_csv(os.path.join(out, "m25_36.csv"), encoding="utf-8-sig"); CT = pd.read_csv(os.path.join(out, "top5.csv"), encoding="utf-8-sig")
    k7 = []
    for G in ("G1", "G2", "純廣撒"):
        _, Aj750 = navof(GPS[(G, 750)], 750)
        v = [g[749] / g[499] - 1 for (b, r, g, _), A in zip(GPS[(G, 750)], Aj750) if b + 749 <= CEND and len(g) >= 750 and g[499] > 0 and A > 0]
        th = M25[M25["格"] == G]["第25-36月平均"].iloc[0]
        if not close(np.mean(v) if v else np.nan, th, 1e-8):
            k7.append(("m25", G, np.mean(v), th))
    G, H = MJ["挑中"]
    nav, Aj = navof(GPS[(G, H)], H)
    t5 = tot = 0.0
    for (b, r, g, lots), A in zip(GPS[(G, H)], Aj):
        if r is None or not lots or b + H - 1 > CEND:
            continue
        pn = sorted(lots); t5 += A * sum(pn[-5:]); tot += A * (g[-1] - 1)
    th = CT[(CT["格"] == G) & (CT["H"] == H)]["Σ前5損益÷Σ整批損益"].iloc[0]
    if not close(t5 / tot if tot else np.nan, th, 1e-7):
        k7.append(("top5", t5 / tot if tot else np.nan, th))
    CK["K7"] = {"不符": k7}; log(f"[K7] {CK['K7']}")
    # ── K8
    lk = subprocess.run([os.path.expanduser("~/tw-p16/.venv/bin/python"), "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True,
                        env={**os.environ, "PYTHONPATH": os.path.expanduser("~/tw-p17")})
    lock = (lk.stdout + lk.stderr).strip().splitlines()[-1:]
    before = set(open(os.path.join(BF.WK, "git_before_main.txt")).read().splitlines())
    now = set(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines())
    extra = sorted(now - before)
    mine = [x for x in extra if any(w in x for w in ("researchBroad.py", "researchBroad_check.py", "resultsBroad/"))]
    CK["K8"] = {"策略鎖": lock, "git 新增": extra, "其中本件": mine, "git 只多本件": len(mine) == len(extra)}
    ok = (CK["K1"]["相符"] and all(ruls.values()) and all(k2.values()) and b3 == 0 and max(k4.values()) < 1e-9 and not k5 and CK["K5"]["同"]
          and not k6 and not k7 and "相符" in "".join(lock) and CK["K8"]["git 只多本件"])
    CK["全過"] = bool(ok)
    log(f"[K8] {CK['K8']}｜全過 {ok}")
    json.dump(CK, open(os.path.join(out, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=RT.jdef)
    open(os.path.join(out, "check.log"), "w", encoding="utf-8").write("\n".join(LOGL) + "\n")


if __name__ == "__main__":
    main()
