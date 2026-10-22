# -*- coding: utf-8 -*-
"""公開收購／經營權／私募 seq2 報酬（描述）【獨立對帳】——回測線計算子代理。⛔ 只讀結果夾、不改任何既有檔（只寫結果夾 check.json、check.log）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTakeover_check [--dry]

R1 登錄 sha 獨立重算。
R2 事件與配對 ＝ 頻率表：recon.csv 全同；main/events.csv.gz 的頻率表欄位與 freq/events.csv.gz 逐字相同。
R3 報酬另一條路：不用 LV／CB／walk，直接以 C、BAD 陣列與有效 K 棒位置重算每列每窗 R事件、R配對、X（E3 有減資 +250：參考價另行讀表、
   原始收盤另行讀檔、接續與截斷另寫迴圈）⇒ 與 events.csv.gz 全列比（相對誤差 ≤ 1e-9）。乾跑 ⇒ 另一條路的值也寫 0 再比。
R4 表.csv 由 events 自算（平均、中位、勝率、月分群 se 另寫 groupby）⇒ 全格相同。
R5 追蹤（注意、處置、後來減資、全額交割）另寫 pandas 區間比對 ⇒ 全列相同。
R6 先驗.csv ＝ 表.csv 對應格；策略鎖 25 支相符；git 工作樹相對開跑前只多 researchTakeover.py、researchTakeover_check.py、resultsTakeover/main/。
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchTakeover as TK                 # noqa: E402
from backtest import researchTakeover_freq as TF            # noqa: E402
from backtest import researchRevTurn_freq as RT             # noqa: E402

MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
LOGL: list = []


def log(s):
    print(s, flush=True); LOGL.append(str(s))


def sha_of(f):
    b = open(f, "rb").read()
    return hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]


def close(a, b):
    a, b = float(a), float(b)
    if np.isnan(a) or np.isnan(b):
        return np.isnan(a) and np.isnan(b)
    return abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry", action="store_true"); ap.add_argument("--procs", type=int, default=2)
    a = ap.parse_args()
    out = os.path.join(TK.WORK, "dry_main") if a.dry else TK.OUT
    CK = {}
    fs = [f for d in [MAILBOX] + sorted(glob.glob(os.path.join(MAILBOX, "_封存-*"))) for f in glob.glob(os.path.join(d, "*.md")) if f"sha{TK.REG_SHA}" in os.path.basename(f)]
    CK["R1"] = {"檔": [os.path.basename(f) for f in fs], "相符": bool(fs) and all(sha_of(f) == TK.REG_SHA for f in fs)}
    log(f"[R1] {CK['R1']}")
    J = json.load(open(os.path.join(out, "main.json"), encoding="utf-8")); sha = J["頻率表sha"]
    rc = pd.read_csv(os.path.join(out, "recon.csv"), encoding="utf-8-sig")
    E = pd.read_csv(os.path.join(out, "events.csv.gz"), dtype=str, keep_default_na=False)
    F = pd.read_csv(os.path.join(TF.OUT, "events.csv.gz"), dtype=str, keep_default_na=False)
    same = len(E) == len(F) and all((E[c] == F[c]).all() for c in F.columns)
    CK["R2"] = {"recon全同": bool(int(rc["不同列數"].sum()) == 0), "頻率表欄逐字相同": bool(same)}
    log(f"[R2] {CK['R2']}")
    # ── R3
    sha_, DN, MD = RT.ensure_data(sha)
    PX = TF.price_panel(sha, DN, a.procs); CAL = PX["CAL"]; NC = len(CAL); C = PX["C"]; BAD = PX["BAD"]; ix = PX["ix"]
    VP = {}

    def vp(i):
        if i not in VP:
            VP[i] = np.flatnonzero(np.isfinite(C[i]))
        return VP[i]

    def lv(i, p):
        v = vp(i); k = int(np.searchsorted(v, p, "right"))
        return int(v[k - 1]) if k else -1
    DX = TK.ensure_extra(sha)
    tab, _ = TK.red_table(DX)
    RAW = {}

    def raw(i, p):
        data = PX["early_data"] if p < PX["NE"] else PX["main_data"]; s = PX["SIDS"][i]
        if (data, s) not in RAW:
            x = pd.read_csv(os.path.join(data, "stocks", f"{s}.csv"), dtype=str, usecols=["date", "close"]).drop_duplicates("date", keep="last")
            RAW[(data, s)] = dict(zip(x["date"].str[:10], pd.to_numeric(x["close"], errors="coerce")))
        return float(RAW[(data, s)].get(CAL[p].strftime("%Y-%m-%d"), np.nan))

    def g_of(i, k):
        pv = lv(i, k - 1)
        c = sorted([x for x in tab.get(PX["SIDS"][i], ()) if CAL[pv] < x[0] <= CAL[k]], key=lambda x: (x[4], x[0]))
        if pv < 0 or not c:
            return None
        _, pre, ref, _, _ = c[0]; rp, rk = raw(i, pv), raw(i, k)
        if not (rp > 0 and rk > 0) or (np.isfinite(pre) and abs(pre / rp - 1) > TK.PRE_TOL) or not (TK.G_LO <= rk / ref <= TK.G_HI):
            return None
        return rk / ref

    def R(i, p0, a_, b_, red=False, mode="接續", exit_pos=None):
        base = p0 + a_ - 1; end = p0 + b_ if exit_pos is None else exit_pos
        if p0 + b_ > NC - 1 or base < 0:
            return np.nan, -1
        bv = lv(i, base)
        if bv < 0:
            return np.nan, -1
        last = int(vp(i)[-1])
        if last <= base:
            return 0.0, -1
        hi = min(end, last)
        bk = [bv + 1 + int(x) for x in np.flatnonzero(BAD[i, bv + 1:hi + 1])]
        if bk and not red:
            return np.nan, -1
        gs = [g_of(i, k) for k in bk]
        if any(g is None for g in gs):
            return np.nan, -1
        if bk and mode == "截斷":
            pv = lv(i, bk[0] - 1); return C[i, pv] / C[i, bv] - 1, pv
        v = 1.0; cur = bv
        for k, g in zip(bk, gs):
            v *= C[i, lv(i, k - 1)] / C[i, cur] * g; cur = k
        return v * C[i, lv(i, hi)] / C[i, cur] - 1, -1
    bad3 = Counter(); n3 = 0
    for _, r in E[E["st"] == "保留"].iterrows():
        i = ix[r["sid"]]; p0 = int(np.searchsorted(CAL.values, np.datetime64(pd.Timestamp(r["day0"])))); j = ix.get(r["配對sid"]) if r["配對sid"] else None
        red = r["類"] == "E3" and r["with_reduction"] == "1"
        for w, (a_, b_) in TK.WINS.items():
            rr = red and w == TK.W250
            re_ = R(i, p0, a_, b_, rr)[0]; rm = R(j, p0, a_, b_, rr)[0] if j is not None else np.nan
            vals = [(f"R{w}", re_), (f"配R{w}", rm), (f"X{w}", re_ - rm)]
            if rr:
                rt, cut = R(i, p0, a_, b_, True, "截斷")
                rmt = R(j, p0, a_, b_, True, "接續", cut if cut >= 0 else None)[0] if (j is not None and np.isfinite(rt)) else np.nan
                vals += [(f"R截斷{w}", rt), (f"配R截斷{w}", rmt), (f"X截斷{w}", rt - rmt)]
            for c, v in vals:
                if a.dry and np.isfinite(v):
                    v = 0.0
                n3 += 1
                got = float(r[c]) if r[c] != "" else np.nan
                if not close(got, v):
                    bad3[c.rstrip("]").split("[")[0]] += 1
    CK["R3"] = {"比對格": n3, "不符": dict(bad3)}
    log(f"[R3] {CK['R3']}")
    # ── R4
    T = pd.read_csv(os.path.join(out, "表.csv"), encoding="utf-8-sig")
    E2 = E.copy(); E2["date_dt"] = pd.to_datetime(E2["date"])
    bad4 = []
    for _, t in T[T["R_n"].notna()].iterrows():
        sg = [s for s in TK.SEGS if s[0] == t["段"]][0]
        sub = TK.gsel(E2, t["組"]); sub = sub[(sub["date_dt"] >= pd.Timestamp(sg[1])) & (sub["date_dt"] <= pd.Timestamp(sg[2])) & (sub["st"] == "保留")]
        w = t["窗"].replace("（減資前截斷，敏感度）", ""); pre = "截斷" if "截斷" in t["窗"] else ""
        x = pd.to_numeric(sub[f"X{pre}{w}"], errors="coerce"); m = sub["公告月"]
        ok = x.notna(); x = x[ok]; m = m[ok]
        if len(x) == 0:
            if int(t["X_n"]) != 0:
                bad4.append((t["段"], t["組"], t["窗"], "n"))
            continue
        mu = x.mean(); se = np.sqrt((x.sub(mu).groupby(m).sum() ** 2).sum()) / len(x)
        mine = {"X_n": len(x), "X平均": mu, "X中位": x.median(), "X勝率": (x > 0).mean(), "X_lo": mu - 1.96 * se, "X_hi": mu + 1.96 * se,
                "X月數": m.nunique()}
        rr = pd.to_numeric(sub[f"R{pre}{w}"], errors="coerce").dropna()
        mine.update({"R_n": len(rr), "R平均": rr.mean() if len(rr) else np.nan})
        for k, v in mine.items():
            if not close(t[k], v):
                bad4.append((t["段"], t["組"], t["窗"], k, t[k], v))
    CK["R4"] = {"格": int(T["R_n"].notna().sum()), "不符": bad4[:10]}
    log(f"[R4] 格 {CK['R4']['格']} 不符 {len(bad4)}")
    # ── R5
    att = pd.read_csv(os.path.join(DX, "meta", "attention.csv"), dtype=str); dis = pd.read_csv(os.path.join(DX, "meta", "disposal.csv"), dtype=str)
    fd = pd.concat([pd.read_csv(f, dtype=str, usecols=["date", "stock_id"]) for f in sorted(glob.glob(os.path.join(DX, "universe", "fulldelivery", "*.csv")))])
    red_dates = pd.DataFrame([(s, x[0]) for s, v in tab.items() for x in v], columns=["stock_id", "d"])
    src = {"注意": att.assign(d=pd.to_datetime(att["date"], errors="coerce")), "處置": dis.assign(d=pd.to_datetime(dis["announce_date"], errors="coerce")),
           "全額交割": fd.assign(d=pd.to_datetime(fd["date"])), "後來減資": red_dates}
    G = {k: v.groupby("stock_id")["d"].apply(lambda s: sorted(s.dropna())) for k, v in src.items()}
    a0 = pd.Timestamp("2011-01-03"); f0 = pd.to_datetime(fd["date"]).min()
    bad5 = Counter(); n5 = 0
    for _, r in E[E["st"] == "保留"].iterrows():
        p0 = int(np.searchsorted(CAL.values, np.datetime64(pd.Timestamp(r["day0"])))); d0 = CAL[p0]
        for who, s in (("", r["sid"]), ("配", r["配對sid"])):
            if not s:
                continue
            for nm, H, st in (("注意", 20, a0), ("注意", 60, a0), ("處置", 20, a0), ("處置", 60, a0), ("後來減資", 250, None), ("全額交割", 250, f0)):
                if p0 + H >= NC or (st is not None and d0 < st):
                    v = ""
                else:
                    hi = CAL[p0 + H]; ds = G[nm].get(s, [])
                    v = str(any((d0 < d if nm == "後來減資" else d0 <= d) and d <= hi for d in ds))
                n5 += 1
                if r[f"{who}{nm}{H}"] != v:
                    bad5[f"{who}{nm}{H}"] += 1
    CK["R5"] = {"格": n5, "不符": dict(bad5)}
    log(f"[R5] {CK['R5']}")
    # ── R6
    P = pd.read_csv(os.path.join(out, "先驗.csv"), encoding="utf-8-sig")
    q = T[(T["段"] == "全期(2005～)")]
    c1 = q[(q["組"] == "E1") & (q["窗"] == "前[-30,-1]")].iloc[0]; c2 = q[(q["組"] == "E1") & (q["窗"] == TK.W250)].iloc[0]
    c3 = q[(q["組"] == "E3_有減資") & (q["窗"] == TK.W250)].iloc[0]
    exp = ["中" if c1["X平均"] > 0 else "不中", "中" if c1 is not None and c2["X_lo"] <= 0 <= c2["X_hi"] else "不中", "中" if c3["X平均"] < 0 else "不中"]
    pri_ok = list(P["結果"][:3]) == exp
    lk = subprocess.run([os.path.expanduser("~/tw-p16/.venv/bin/python"), "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True,
                        env={**os.environ, "PYTHONPATH": os.path.expanduser("~/tw-p17")})
    lock = (lk.stdout + lk.stderr).strip().splitlines()[-1:]
    before = set(open(os.path.join(TK.WORK, "git_before_main.txt")).read().splitlines())
    now = set(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines())
    extra = sorted(now - before)
    mine = [x for x in extra if ("researchTakeover.py" in x) or ("researchTakeover_check.py" in x) or ("resultsTakeover/main" in x)]
    other = [x for x in extra if x not in mine]
    CK["R6"] = {"先驗對表": pri_ok, "策略鎖": lock, "git 本件新增": mine, "git 其他新增（同時段他件，非本件）": other,
                "git 只多本件": all(x.startswith("??") for x in mine) and not any(x[:2].strip() in ("M", "D", "MM", "AM") for x in other)}
    log(f"[R6] {CK['R6']}")
    ok = (CK["R1"]["相符"] and CK["R2"]["recon全同"] and CK["R2"]["頻率表欄逐字相同"] and not bad3 and not bad4 and not bad5 and pri_ok
          and "相符" in "".join(lock) and CK["R6"]["git 只多本件"])
    CK["全部通過"] = bool(ok)
    log(f"[結論] 全部通過 {ok}")
    json.dump(CK, open(os.path.join(out, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(out, "check.log"), "w", encoding="utf-8").write("\n".join(LOGL) + "\n")


if __name__ == "__main__":
    main()
