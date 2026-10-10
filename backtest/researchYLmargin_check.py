# -*- coding: utf-8 -*-
"""researchYLmargin 的獨立查核（⛔ 不 import researchYLmargin；毛利率、可用日、假訊號抽樣、段讀法都自己寫）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLmargin_check [--n 300]

① 抽樣 n 筆訊號（加上全部「不適用」列）：csv 模組自己讀 fs_hist、自己算 q*（期限後第一個交易日）、單季毛利率、狀態 ⇒ 對 signals.csv.gz（狀態、q*、兩個毛利率）
② fin_hist（origin/main，XBRL）旁證：同一批「符／不符」列用 gp_ytd、rev_ytd 自己算 ⇒ 狀態一致率（只報、不當閘）
③ 自己由 signals.csv.gz 的 keep 欄組訊號、自己寫假訊號抽樣，呼叫引擎重跑抽樣種子 ⇒ 對 seeds.csv.gz（eq_sha、各段年化／回落）；段年化／回落用自己寫的式子
④ 0050 各段自己算 ⇒ 對 summary；⑤ 從 seeds.csv.gz 自己算中位、比值、標籤 ⇒ 對 cells.csv；剔除筆數逐年自己數 ⇒ 對 summary
⇒ resultsYLmargin/check.json
"""
from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import io
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import listexit_lines as L
from backtest import research11 as R
from backtest import rerun17 as RR

HERE = os.path.expanduser("~/tw-p17/backtest")
OUT = os.path.join(HERE, "resultsYLmargin")
FSD = os.path.expanduser("~/tw-p17/data/mops/fs_hist")
RP = dict(float_precision="round_trip")
SEG = {"主窗": ("2017-03-02", "2026-08-24"), "探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}


def num(x):
    x = (x or "").replace(",", "").strip()
    try:
        return float(x)
    except ValueError:
        return float("nan")


class FS:
    def __init__(self):
        self.rows = {}           # (sid, y, q) -> list[(fmt, file, rev, gp)]
        for f in sorted(glob.glob(os.path.join(FSD, "*.csv"))):
            b = os.path.basename(f); stem = b[:-4].split("_")
            y, q, fmt = int(stem[0][:4]), int(stem[0][5]), stem[1]
            with open(f, encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    self.rows.setdefault((r["stock_id"].strip(), y, q), []).append(
                        (fmt, b, num(r.get("營業收入")) if fmt == "ci" else float("nan"), num(r.get("營業毛利（毛損）")) if fmt == "ci" else float("nan")))

    def get(self, sid, y, q):
        L_ = self.rows.get((sid, y, q))
        if not L_:
            return None
        return sorted(L_, key=lambda t: (t[0] != "ci", t[1]))[0]

    def gm(self, sid, y, q):
        a = self.get(sid, y, q)
        if a is None or a[0] != "ci":
            return float("nan")
        rev, gp = a[2], a[3]
        if q > 1:
            p = self.get(sid, y, q - 1)
            if p is None or p[0] != "ci":
                return float("nan")
            rev, gp = rev - p[2], gp - p[3]
        if not (np.isfinite(rev) and np.isfinite(gp)) or rev <= 0:
            return float("nan")
        return gp / rev

    def fmt_any(self, sid, y, q):
        a = self.get(sid, y, q)
        if a is not None:
            return a[0]
        k = y * 4 + q - 1
        allq = sorted((yy * 4 + qq - 1, self.get(s, yy, qq)[0]) for (s, yy, qq) in self.rows if s == sid)
        le = [f for kk, f in allq if kk <= k]; gt = [f for kk, f in allq if kk > k]
        return le[-1] if le else (gt[0] if gt else None)


def qstar(d, cal):
    """自己算：往回列出候選季，取可用日 ≤ d 的最晚一季。"""
    best = None
    for y in range(d.year - 2, d.year + 1):
        for q, (dy, mo, dd) in {1: (0, 5, 15), 2: (0, 8, 14), 3: (0, 11, 14), 4: (1, 3, 31)}.items():
            dl = pd.Timestamp(y + dy, mo, dd)
            nxt = cal[cal > dl]
            if len(nxt) and nxt[0] <= d:
                if best is None or (y, q) > best:
                    best = (y, q)
    return best


def my_status(fs, sid, d, cal):
    y, q = qstar(d, cal)
    fy, fq = (y - 1, q)
    fmt = fs.fmt_any(sid, y, q)
    here = fs.get(sid, y, q)
    if fmt in ("basi", "bd", "fh", "ins"):
        st = "不適用・金融"
    elif fmt == "other":
        st = "不適用・異業"
    else:
        g0, g4 = fs.gm(sid, y, q), fs.gm(sid, fy, fq)
        if here is None or here[0] != "ci" or not np.isfinite(g0):
            st = "缺值・本季"
        elif not np.isfinite(g4):
            st = "缺值・去年同季"
        else:
            st = "符" if g0 >= g4 else "不符"
    return f"{y}Q{q}", st, fs.gm(sid, y, q), fs.gm(sid, fy, fq)


def fin_gm(sid, y, q, cache):
    def load(yy, qq):
        k = f"{yy}Q{qq}"
        if k not in cache:
            try:
                txt = subprocess.run(["git", "show", f"origin/main:data/mops/fin_hist/{k}.csv"], capture_output=True, text=True, check=True).stdout
                cache[k] = {r["stock_id"]: r for r in csv.DictReader(io.StringIO(txt))}
            except subprocess.CalledProcessError:
                cache[k] = {}
        return cache[k].get(sid)
    a = load(y, q)
    if a is None:
        return float("nan")
    rev, gp = num(a["rev_ytd"]), num(a["gp_ytd"])
    if q > 1:
        p = load(y, q - 1)
        if p is None:
            return float("nan")
        rev, gp = rev - num(p["rev_ytd"]), gp - num(p["gp_ytd"])
    return gp / rev if np.isfinite(rev) and np.isfinite(gp) and rev > 0 else float("nan")


def my_win(eq, first, end, a, b):
    seg = np.asarray(eq[a:b + 1], float)          # 段 [a, b]（引擎權益在 first 之前是現金 1.0、end 之後不動）
    cagr = (seg[-1] / seg[0]) ** (245.0 / len(seg)) - 1
    pk = np.maximum.accumulate(seg)
    return cagr, float(((seg - pk) / pk).min())


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=300); a = ap.parse_args()
    RES = {}
    ST = pd.read_csv(os.path.join(OUT, "signals.csv.gz"), dtype={"sid": str}, **RP)
    SM = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    SD = pd.read_csv(os.path.join(OUT, "seeds.csv.gz"), dtype={"eq_sha": str}, **RP)
    TB = pd.read_csv(os.path.join(OUT, "cells.csv"), **RP)
    ctx = L.setup_t1(print, t1=True)          # ⭐ 自己走 setup（不經 researchT1fix）
    G = RR._G; cal = ctx["cal"]; AND = G["AND"]; e = AND["entry_pos"].to_numpy()
    sig13 = AND[(e >= G["w0"]) & (e <= G["w1"])]; sigF = ctx["sig"]
    # ① 抽樣
    fs = FS()
    rng = np.random.default_rng(424242)
    pick = set(rng.choice(len(ST), size=min(a.n, len(ST)), replace=False).tolist()) | set(np.flatnonzero(ST["status"].str.startswith("不適用")).tolist())
    bad1 = []; fin_cmp = []; cache = {}
    for i in sorted(pick):
        r = ST.iloc[i]
        d = cal[int(r["pos"])]
        qs, st, g0, g4 = my_status(fs, r["sid"], d, cal)
        same = qs == r["qstar"] and st == r["status"] and ((not np.isfinite(g0) and not np.isfinite(r["gm_q"])) or g0 == r["gm_q"]) and \
            ((not np.isfinite(g4) and not np.isfinite(r["gm_q4"])) or g4 == r["gm_q4"])
        if not same:
            bad1.append({"and_idx": int(r["and_idx"]), "sid": r["sid"], "我": [qs, st, g0, g4], "件": [r["qstar"], r["status"], r["gm_q"], r["gm_q4"]]})
        if st in ("符", "不符"):
            y, q = int(qs[:4]), int(qs[5])
            f0, f4 = fin_gm(r["sid"], y, q, cache), fin_gm(r["sid"], y - 1, q, cache)
            if np.isfinite(f0) and np.isfinite(f4):
                fin_cmp.append(st == ("符" if f0 >= f4 else "不符"))
    RES["①毛利率狀態抽樣"] = {"抽樣": len(pick), "不同": len(bad1), "例": bad1[:5]}
    RES["②fin_hist旁證"] = {"可比筆數": len(fin_cmp), "狀態一致率": float(np.mean(fin_cmp)) if fin_cmp else None}
    # 訊號集合對得上
    RES["訊號集合"] = {"營量窗內 ＝ signals": bool(set(sig13.index) == set(ST["and_idx"])),
                    "營飆（t−1 閘）＝ in_fly": bool(set(sigF.index) == set(ST.loc[ST["in_fly"], "and_idx"]))}
    # ③ 重跑
    keep = dict(zip(ST["and_idx"], ST["keep"]))
    POOL = {"fly": sigF, "vol": sig13}
    Q = {f: P[[bool(keep[i]) for i in P.index]] for f, P in POOL.items()}
    SF = R.stop_force_days(R.valid_from_data(sorted(ctx["closes"]), ctx["mk"], cal), G["w1"])
    segpos = {k: (int(cal.searchsorted(pd.Timestamp(x))), int(cal.searchsorted(pd.Timestamp(y)))) for k, (x, y) in SEG.items()}

    def fake(f, i):
        P = POOL[f]; kp = np.array([bool(keep[j]) for j in P.index]); pos = P["pos"].to_numpy()
        g = np.random.default_rng([20261010, 1 if f == "fly" else 13, i]); drop = np.zeros(len(P), bool)
        for p in sorted(set(pos.tolist())):
            ix = np.where(pos == p)[0]; n = int((~kp[ix]).sum())
            if n > 0:
                drop[ix[g.choice(len(ix), size=n, replace=False)]] = True
        return P[~drop]

    def eng(f, sig, r):
        if f == "fly":
            return R.simulate_mtm(sig, "H120", 10, np.random.default_rng(1000 + r), ctx["closes"], ctx["opens"], ctx["ncal"], return_equity=True, stop_force=SF)
        return R.simulate_mtm(sig, "H60", 20, np.random.default_rng(7000 + r), ctx["closes"], ctx["opens"], ctx["ncal"], return_equity=True, log=[], d_max=None,
                              pick="relvol", queue_days=0, stop_force=SF)
    jobs = [("fly|q1", 0), ("fly|q1", 1), ("fly|q1", 137), ("fly|base", 5), ("vol|q1", 0), ("vol|base", 0), ("fly|fake", 5), ("fly|fake", 160), ("vol|fake", 0), ("vol|fake", 77)]
    bad3 = []
    for k, r in jobs:
        f, arm = k.split("|")
        sig = POOL[f] if arm == "base" else (Q[f] if arm == "q1" else fake(f, r))
        o = eng(f, sig, r); eq = np.asarray(o["equity"], float)
        row = SD[(SD["key"] == k) & (SD["r"] == r)].iloc[0]
        diffs = []
        if hashlib.sha256(eq.tobytes()).hexdigest()[:16] != row["eq_sha"]:
            diffs.append("eq_sha")
        for s, (aa, bb) in segpos.items():
            c, m = my_win(eq, o["first"], o["end"], aa, bb)
            if abs(c - row[f"{s}_cagr"]) > 1e-12 or abs(m - row[f"{s}_mdd"]) > 1e-12:
                diffs.append(s)
        if diffs:
            bad3.append({"key": k, "r": r, "不同": diffs})
    RES["③引擎抽樣重跑"] = {"抽樣": len(jobs), "不同": len(bad3), "例": bad3}
    # ④ 0050
    b = pd.Series(RR.load_bench(cal))
    bad4 = []
    for s, (aa, bb) in segpos.items():
        seg = b.iloc[aa:bb + 1].to_numpy(float)
        c = (seg[-1] / seg[0]) ** (245.0 / len(seg)) - 1; pk = np.maximum.accumulate(seg); m = float(((seg - pk) / pk).min())
        ref = SM["setup"]["0050"][s]
        if abs(c - ref["cagr"]) > 1e-12 or abs(m - ref["mdd"]) > 1e-12:
            bad4.append(s)
    RES["④0050各段"] = {"不同": len(bad4), "例": bad4}
    # ⑤ 中位與標籤、剔除數
    bad5 = []
    for _, r in TB.iterrows():
        g = SD[SD["key"] == r["key"]]
        c, m = g[f"{r['段']}_cagr"].median(), g[f"{r['段']}_mdd"].median()
        ref = SM["setup"]["0050"][r["段"]]; c50 = ref["cagr"]; r50 = c50 / abs(ref["mdd"])
        lb = "合格" if (c > c50 and c / abs(m) >= r50) else ("另列" if c > c50 else "不合格")
        if repr(float(c)) != repr(float(r["年化"])) or repr(float(m)) != repr(float(r["回落"])) or lb != r["標籤"]:
            bad5.append([r["key"], r["段"]])
    for f, col in (("fly", "in_fly"), ("vol", "in_vol")):
        P = ST[ST[col]]
        if int((~P["keep"]).sum()) != SM["策略"][f]["剔除"]["剔除"]:
            bad5.append([f, "剔除數"])
        for y in SM["策略"][f]["剔除"]["逐年"]:
            g = P[P["date"].str[:4] == y["年"]]
            if len(g) != y["訊號"] or int((g["status"] == "不符").sum()) != y["不符"]:
                bad5.append([f, y["年"]])
    RES["⑤彙總重算"] = {"格段數": int(len(TB)), "不同": len(bad5), "例": bad5[:5]}
    n_bad = len(bad1) + len(bad3) + len(bad4) + len(bad5) + (0 if all(RES["訊號集合"].values()) else 1)
    RES["結論"] = (f"抽樣 {len(pick)} 筆毛利率狀態、{len(jobs)} 顆引擎重跑、0050 三段、{len(TB)} 格段彙總：0 不同" if n_bad == 0 else f"⛔ 有 {n_bad} 處不同")
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print(json.dumps(RES, ensure_ascii=False, indent=1, default=float))
    if n_bad:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
