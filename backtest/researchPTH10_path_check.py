# -*- coding: utf-8 -*-
"""researchPTH10_path【獨立對帳】——回測線計算子代理。⛔ 只讀、不改任何既有檔（只寫 resultsPTH10path/check.json、check.log）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTH10_path_check

K1 抽 10 筆（default_rng(20261020)，主 5、早年 5，另強制含「前 10% 且曾 ≤ −15%」的全部筆）手算：
   ⛔ 不用 W["CM"]／build_world；直接讀 ~/rluwork/world_<part>.pkl 的原始快取收盤 c、開盤 o，自寫逐日迴圈 ffill（最近一個 >0 有限值），
   日曆 ＝ researchAscTri_freq.load_world 的 cal（只取日期序與股欄）；交易 ＝ resultsPTHn/trades_<世界>_N10.csv.gz。
   驗：買價 ＝ o[買進日]、c(ffill)[賣出日] ÷ 買價 − 1 ＝ R用、最大浮虧／浮盈（clip 0）、最大浮虧日序、淨報酬 ⇒ 對 path_trades.csv（≤1e−6）。
K2 由 path_trades.csv 自算分組（段內 ceil 10%）、門檻比例、反向比例、停損占比 ⇒ 對 groups.csv、deep15.csv、stop15.csv。
K3 策略鎖 25 支相符；git 工作樹：本件只新增檔。
"""
from __future__ import annotations

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
from backtest import researchAscTri_freq as AF              # noqa: E402  只取日曆、股欄
from backtest import researchAddOn as RA                    # noqa: E402
from backtest import universe_gate as UG                    # noqa: E402

UG.set_gate_v2(True)

OUT = "backtest/resultsPTH10path"
SRC = "backtest/resultsPTHn"
COST = 0.00585


def ff(row, t):
    """t 位置（含）往前最近一個 >0 有限收盤。"""
    k = t
    while k >= 0:
        v = row[k]
        if np.isfinite(v) and v > 0:
            return float(v)
        k -= 1
    return float("nan")


def hand(row, orow, e, s):
    ep = float(orow[e])
    xs = [ff(row, t) / ep - 1.0 for t in range(e, s)]
    if not xs:
        xs = [ff(row, s) / ep - 1.0]
    lo = min(xs); hi = max(xs)
    k = xs.index(lo) + 1 if (s > e) else (s - e + 1)
    return {"買價": ep, "末": ff(row, s) / ep - 1.0, "最大浮虧": min(0.0, lo), "最大浮盈": max(0.0, hi), "最大浮虧日序": k}


def main():
    log = RA.log_to(os.path.join(OUT, "check.log"))
    P = pd.read_csv(os.path.join(OUT, "path_trades.csv"), dtype={"sid": str, "買進日": str, "賣出日": str})
    J = {"K1": [], "K2": {}, "K3": {}}; ok = True
    rng = np.random.default_rng(20261020)
    pick = []
    for wn in ("主", "早年"):
        idx = P.index[P["世界"] == wn].to_numpy()
        pick += list(rng.choice(idx, 5, replace=False))
    forced = P.index[(P["組"] == "前10%") & (P["最大浮虧"] <= -0.15 + 1e-12)].tolist()
    pick = sorted(set(pick) | set(forced))
    log(f"[K1] 抽 {len(pick)} 筆（隨機 10 ＋ 前10%且曾≤−15% {len(forced)}）")
    for wn, part in (("主", "main"), ("早年", "early")):
        W = AF.load_world(wn)
        cal = W["cal"]; dates = [str(d.date()) for d in cal]; dpos = {d: i for i, d in enumerate(dates)}
        Z = pickle.load(open(os.path.expanduser(f"~/rluwork/world_{part}.pkl"), "rb"))
        col = {s: i for i, s in enumerate(Z["sids"])}
        C = np.asarray(Z["c"], float); Oo = np.asarray(Z["o"], float)
        tr = pd.read_csv(os.path.join(SRC, f"trades_{wn}_N10.csv.gz"), dtype={"sid": str, "買進日": str, "賣出日": str}, keep_default_na=False)
        for q in [p for p in pick if P.loc[p, "世界"] == wn]:
            r = P.loc[q]
            t = tr.iloc[int(r["列"])]
            if not (t["sid"] == r["sid"] and t["買進日"] == r["買進日"] and t["賣出日"] == r["賣出日"]):
                ok = False; log(f"⛔ 列對不上 {q}"); continue
            j = col[r["sid"]]; e = dpos[r["買進日"]]; s = dpos[r["賣出日"]]
            h = hand(C[j], Oo[j], e, s)
            net = float(t["R用"]) - COST
            chk = {"買價=o": abs(h["買價"] - float(t["市值基準價"])) <= 1e-9 * h["買價"], "末=R用": abs(h["末"] - float(t["R用"])) <= 1e-9,
                   "最大浮虧": abs(h["最大浮虧"] - r["最大浮虧"]) <= 1e-6, "最大浮盈": abs(h["最大浮盈"] - r["最大浮盈"]) <= 1e-6,
                   "日序": int(h["最大浮虧日序"]) == int(r["最大浮虧日序"]), "淨報酬": abs(net - r["淨報酬"]) <= 1e-6}
            good = all(chk.values()); ok &= good
            row = {"世界": wn, "sid": r["sid"], "名稱": r["名稱"], "買進日": r["買進日"], "賣出日": r["賣出日"], "手算最大浮虧": h["最大浮虧"],
                   "檔案最大浮虧": float(r["最大浮虧"]), "手算日序": int(h["最大浮虧日序"]), "手算最大浮盈": h["最大浮盈"], "淨報酬": net, "相符": good,
                   **({} if good else {"細項": chk})}
            J["K1"].append(row)
            log(f"[K1] {wn} {r['sid']} {r['名稱']} {r['買進日']}→{r['賣出日']} 手算浮虧 {h['最大浮虧']:+.4f}（檔 {r['最大浮虧']:+.4f}）第{h['最大浮虧日序']}日 "
                f"浮盈 {h['最大浮盈']:+.4f} 淨 {net:+.4f} ⇒ {'相符' if good else '⛔不符 ' + str(chk)}")
        del Z, C, Oo, W
    # K2
    G = pd.read_csv(os.path.join(OUT, "groups.csv")); DP = pd.read_csv(os.path.join(OUT, "deep15.csv")); ST = pd.read_csv(os.path.join(OUT, "stop15.csv"))
    views = [("主", "探索", (P["世界"] == "主") & (P["段"] == "探索")), ("主", "確認", (P["世界"] == "主") & (P["段"] == "確認")),
             ("主", "探索＋確認", P["世界"] == "主"), ("早年", "早年", P["世界"] == "早年")]
    k2 = 0; k2bad = []
    for wn, sg, m in views:
        D = P[m].reset_index(drop=True)
        v = D["淨報酬"].to_numpy(); n = len(v); k = math.ceil(n / 10)
        order = sorted(range(n), key=lambda i: (-v[i], i))
        grp = np.array(["中間80%"] * n, object); grp[order[:k]] = "前10%"; grp[order[n - k:]] = "後10%"
        lo = D["最大浮虧"].to_numpy()
        for gname in ("前10%", "中間80%", "後10%", "全部"):
            sel = np.ones(n, bool) if gname == "全部" else grp == gname
            ref = G[(G["世界"] == wn) & (G["段"] == sg) & (G["組"] == gname)].iloc[0]
            for th, c_ in ((-0.10, "曾≤-10%"), (-0.15, "曾≤-15%"), (-0.20, "曾≤-20%")):
                mine = float(np.mean(lo[sel] <= th + 1e-12)); k2 += 1
                if abs(mine - ref[c_]) > 1e-4:
                    k2bad.append((wn, sg, gname, c_, mine, ref[c_]))
            mine = float(np.median(lo[sel])); k2 += 1
            if abs(mine - ref["最大浮虧中位"]) > 1e-4:
                k2bad.append((wn, sg, gname, "中位", mine, ref["最大浮虧中位"]))
        hit = lo <= -0.15 + 1e-12
        rd = DP[(DP["世界"] == wn) & (DP["段"] == sg)].iloc[0]
        for c_, mine in (("曾≤-15%筆", int(hit.sum())), ("最後賺筆", int((v[hit] > 0).sum())), ("大賺筆", int((v[hit] > 0.30).sum())),
                         ("收在≤-15%筆", int((v[hit] <= -0.15).sum()))):
            k2 += 1
            if mine != int(rd[c_]):
                k2bad.append((wn, sg, c_, mine, rd[c_]))
        rs = ST[(ST["世界"] == wn) & (ST["段"] == sg)].iloc[0]
        mm = hit & (grp == "前10%")
        for c_, mine in (("前10%中曾≤-15%筆", int(mm.sum())), ("前10%中曾≤-15%：淨報酬和÷全部淨報酬和", float(v[mm].sum() / v.sum())),
                         (">+30%中曾≤-15%筆", int((hit & (v > 0.30)).sum())),
                         (">+30%中曾≤-15%：淨報酬和÷全部淨報酬和", float(v[hit & (v > 0.30)].sum() / v.sum()))):
            k2 += 1
            if abs(float(mine) - float(rs[c_])) > 1e-4:
                k2bad.append((wn, sg, c_, mine, rs[c_]))
    J["K2"] = {"比對項": k2, "不符": [list(map(str, b)) for b in k2bad]}
    ok &= not k2bad
    log(f"[K2] 自算分組／門檻／反向／停損 {k2} 項 ⇒ {'全相符' if not k2bad else '⛔ 不符 ' + str(k2bad)}")
    # K3
    p = subprocess.run([sys.executable, "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True)
    gs = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines()
    mine_new = [l for l in gs if "PTH10_path" in l or "resultsPTH10path" in l]
    mod_mine = [l for l in mine_new if not l.startswith("??")]
    J["K3"] = {"strategy_lock": p.stdout.strip().splitlines()[-1] if p.stdout.strip() else p.stderr.strip()[-200:], "rc": p.returncode,
               "本件 git 列": mine_new, "本件非新增": mod_mine}
    ok &= p.returncode == 0 and not mod_mine
    log(f"[K3] {J['K3']}")
    J["全過"] = bool(ok)
    json.dump(J, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] 全過 = {ok}")
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
