# -*- coding: utf-8 -*-
"""researchThemeTag（seq480 正式）獨立查核——另一套寫法：csv 模組讀 trades_W 重算每筆 R、git show 自己解析 market_tri、
統計量與同月隨機、月群自助法逐一重算，前瞻名單另寫解析。⛔ 不 import 主檔（0050 序列例外：同用 researchV41EV.z50，另驗分割停牌補值）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchThemeTag_check [--dir backtest/resultsThemeTag/main]
K1 rows.csv 與 freq/entries.csv（入統計那批）逐列對齊；R ＝ amt_out ÷ amt − 1 − 0.585%（|差| < 1e−12）
K2 大盤 ＝ market_tri（PIN 9b0e9882572c）進場前一交易日收盤 → 出場日收盤；0050 ＝ z50 同式（缺日用前一收盤）；超額 ＝ R − 基準
K3 stats.csv：主題／非主題 筆數、中位、平均、去最大 1 筆平均、勝率；差 列 ＝ 相減
K4 同月隨機：default_rng(20261026)、1,000 次、依月份序 rng.choice 不放回 ⇒ 中位 ＝ stats.csv
K5 ci.csv：月群自助法重算 ＝ 檔值
K6 描述句：主題組 ＜ 30 ⇒「筆數不足、不下描述結論」
K7 前瞻：period01_main／supp sha16 與家數（42／7、聯集 48）；forward.csv 列數 ＝ positions.csv 進場日 ≥ 2026-11-01 的 (月, 策略) 組數
輸出 <dir>/check.json、check.log
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import os
import re
import subprocess
import sys

import numpy as np

REPO = os.path.expanduser("~/tw-p17")
os.chdir(REPO); sys.path.insert(0, REPO)
LOG, BAD = [], []
ACCT = {"營量": "YL", "營飆": "v1"}
SEED = 20261026


def log(s):
    LOG.append(s); print(s, flush=True)


def ok(name, cond, extra=""):
    log(f"[{'過' if cond else '✖'}] {name} {extra}")
    if not cond:
        BAD.append(name)


def st_(x):
    x = sorted(float(v) for v in x); n = len(x)
    if n == 0:
        return [0, None, None, None, None]
    med = (x[(n - 1) // 2] + x[n // 2]) / 2
    return [n, med, sum(x) / n, (sum(x[:-1]) / (n - 1)) if n >= 2 else None, sum(1 for v in x if v > 0) / n]


def close(a, b, tol=1e-9):
    if a is None or b is None or (isinstance(b, float) and np.isnan(b)):
        return (a is None or (isinstance(a, float) and np.isnan(a))) and (b is None or (isinstance(b, float) and np.isnan(b)))
    return abs(a - b) <= tol


def fnum(s):
    return None if s in ("", "nan", None) else float(s)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dir", default="backtest/resultsThemeTag/main"); a = ap.parse_args()
    D = a.dir
    rows = list(csv.DictReader(open(os.path.join(D, "rows.csv"), encoding="utf-8")))
    ent = [r for r in csv.DictReader(open("backtest/resultsThemeTag/freq/entries.csv", encoding="utf-8")) if r["持有狀態"] != "未滿"]
    ok("K1 rows 與 entries 入統計 對齊", [(r["策略"], r["代號"], r["進場日"], r["出場日"]) for r in rows] ==
       [(r["策略"], r["代號"], r["進場日"], r["出場日"]) for r in ent], f"（{len(rows)}）")
    # R
    with gzip.open("backtest/resultsYFallin/trades_W.csv.gz", "rt", encoding="utf-8") as f:
        tw = [r for r in csv.DictReader(f) if r["世界"] == "主"]
    buy = {(r["帳"], int(r["sid"]), int(r["t"])): float(r["amt"]) for r in tw if r["side"] == "buy"}
    sel = {(r["帳"], int(r["sid"]), int(r["t"])): float(r["amt_out"]) for r in tw if r["side"] == "sell"}
    dR = 0.0
    for r, e in zip(rows, ent):
        k = ACCT[e["策略"]]; sid = int(e["代號"])
        R = sel[(k, sid, int(e["出場t"]))] / buy[(k, sid, int(e["進場t"]))] - 1 - 0.00585
        dR = max(dR, abs(R - float(r["R"])))
    ok("K1 R 重算", dR < 1e-12, f"（最大差 {dR:.2e}）")
    # 日曆、大盤
    with gzip.open("backtest/resultsYFallin/daily_W.csv.gz", "rt", encoding="utf-8") as f:
        cal = {int(r["t"]): r["日期"] for r in csv.DictReader(f) if r["世界"] == "主" and r["帳"] == "YL"}
    raw = subprocess.run(["git", "show", "9b0e9882572c:data/history/market_tri.csv"], capture_output=True, check=True).stdout.decode("utf-8")
    tri = {}
    for r in csv.DictReader(io.StringIO(raw)):
        if r["close"] not in ("", "nan") and r["date"][:10] not in tri:
            tri[r["date"][:10]] = float(r["close"])
    from backtest import researchV41EV as V
    Z = V.z50(subprocess.run(["git", "rev-parse", "9b0e9882572c"], capture_output=True, text=True, check=True).stdout.strip())
    zd = {str(d.date()): float(v) for d, v in Z.items()}
    zk = sorted(zd)

    def z_at(d):
        if d in zd:
            return zd[d]
        import bisect
        return zd[zk[bisect.bisect_right(zk, d) - 1]]
    dB = dZ = dX = 0.0; nfill = 0
    for r, e in zip(rows, ent):
        b = cal[int(e["進場t"]) - 1]; x = e["出場日"]
        mk = tri[x] / tri[b] - 1
        nfill += (b not in zd) or (x not in zd)
        zz = z_at(x) / z_at(b) - 1
        dB = max(dB, abs(mk - float(r["大盤"]))); dZ = max(dZ, abs(zz - float(r["0050"])))
        dX = max(dX, abs(float(r["R"]) - mk - float(r["超額_大盤"])), abs(float(r["R"]) - zz - float(r["超額_0050"])))
    ok("K2 大盤／0050／超額 重算", dB < 1e-12 and dZ < 1e-12 and dX < 1e-12, f"（差 {dB:.1e}／{dZ:.1e}／{dX:.1e}；0050 補值筆 {nfill}）")
    # 統計
    S = list(csv.DictReader(open(os.path.join(D, "stats.csv"), encoding="utf-8")))
    C = list(csv.DictReader(open(os.path.join(D, "ci.csv"), encoding="utf-8")))
    K = ["中位", "平均", "去最大1筆平均", "勝率"]
    g3 = g4 = g5 = True
    for stg in ("營量", "營飆"):
        Rs = [r for r in rows if r["策略"] == stg]
        for v in ("寬", "嚴"):
            tag = [r[f"標籤_{v}"] == "True" for r in Rs]
            mon = [r["月"] for r in Rs]
            months_t = sorted({m for m, t in zip(mon, tag) if t})
            rng = np.random.default_rng(SEED)
            draws = []
            for _ in range(1000):
                idx = []
                for m in months_t:
                    ii = np.array([i for i, mm in enumerate(mon) if mm == m]); k = sum(1 for i in ii if tag[i])
                    idx += list(rng.choice(ii, size=k, replace=False))
                draws.append(idx)
            for bn in ("大盤", "0050"):
                y = [float(r[f"超額_{bn}"]) for r in Rs]
                th = st_([y[i] for i in range(len(y)) if tag[i]]); no = st_([y[i] for i in range(len(y)) if not tag[i]])
                rd = [st_([y[i] for i in d]) for d in draws]
                rm = [None] + [None if all(z[j] is None for z in rd) else float(np.median([z[j] for z in rd if z[j] is not None])) for j in range(1, 5)]
                get = {r["組"]: r for r in S if r["策略"] == stg and r["版"] == v and r["基準"] == bn}
                for grp, s in (("主題", th), ("非主題", no)):
                    g = get[grp]
                    g3 &= int(float(g["筆數"])) == s[0] and all(close(s[j + 1], fnum(g[K[j]])) for j in range(4))
                g = get["同月隨機（1000 次中位）"]
                g4 &= all(close(rm[j + 1], fnum(g[K[j]])) for j in range(4))
                for nm, other in (("差：主題−非主題", no), ("差：主題−隨機", rm)):
                    g = get[nm]
                    for j in range(4):
                        exp = None if th[j + 1] is None or other[j + 1] is None else th[j + 1] - other[j + 1]
                        g3 &= close(exp, fnum(g[K[j]]))
                # K5 月群自助法
                rng2 = np.random.default_rng(SEED)
                ms = sorted(set(mon))
                by = {m: ([y[i] for i in range(len(y)) if mon[i] == m], [tag[i] for i in range(len(y)) if mon[i] == m]) for m in ms}
                dm, dt, sk = [], [], 0
                for _ in range(2000):
                    pick = rng2.choice(np.array(ms), size=len(ms), replace=True)
                    a1 = [x for m in pick for x, t in zip(*by[m]) if t]; b1 = [x for m in pick for x, t in zip(*by[m]) if not t]
                    A, Bq = st_(a1), st_(b1)
                    if A[0] == 0 or Bq[0] == 0 or A[3] is None or Bq[3] is None:
                        sk += 1; continue
                    dm.append(A[1] - Bq[1]); dt.append(A[3] - Bq[3])
                c = [r for r in C if r["策略"] == stg and r["版"] == v and r["基準"] == bn][0]
                g5 &= int(c["跳過"]) == sk and close(float(np.percentile(dm, 2.5)), float(c["中位差CI_下"])) and \
                    close(float(np.percentile(dm, 97.5)), float(c["中位差CI_上"])) and close(float(np.percentile(dt, 2.5)), float(c["去最大1筆平均差CI_下"])) and \
                    close(float(np.percentile(dt, 97.5)), float(c["去最大1筆平均差CI_上"]))
    ok("K3 主題／非主題／差 統計重算", bool(g3)); ok("K4 同月隨機 1000 次中位重算", bool(g4)); ok("K5 月群自助法區間重算", bool(g5))
    J = json.load(open(os.path.join(D, "run.json"), encoding="utf-8"))
    nth = {f"{s_}_{v}": sum(1 for r in rows if r["策略"] == s_ and r[f"標籤_{v}"] == "True") for s_ in ("營量", "營飆") for v in ("寬", "嚴")}
    ok("K6 描述句", all((J["描述句"][k].startswith("筆數不足、不下描述結論") if n < 30 else J["描述句"][k] in ("成立", "不成立")) for k, n in nth.items()),
       str(nth))
    # K7
    fr = "backtest/forward/frontier"
    h1 = hashlib.sha256(open(f"{fr}/period01_main.md", "rb").read()).hexdigest()[:16]
    h2 = hashlib.sha256(open(f"{fr}/period01_supp.md", "rb").read()).hexdigest()[:16]
    t1 = open(f"{fr}/period01_main.md", encoding="utf-8").read().split("## 二、")[1].split("## 三、")[0]
    c1 = set()
    for ln in t1.splitlines():
        if ln.startswith("| ") and "---" not in ln and "| 組 |" not in ln:
            c1 |= set(re.findall(r"\b(\d{4})\b", re.sub(r"（.*?）", "", ln.split("|")[3])))
    t2 = open(f"{fr}/period01_supp.md", encoding="utf-8").read().split("## 一、")[1].split("## 二、")[0]
    c2 = set()
    for ln in t2.splitlines():
        if ln.startswith("| ") and "---" not in ln and "| 名次 |" not in ln:
            c2 |= set(re.findall(r"\b(\d{4})\b", ln.split("|")[-2]))
    pos = list(csv.DictReader(open("backtest/forward/yl_rule/positions.csv", encoding="utf-8-sig")))
    grp = {(r["進場日"][:7], r["策略"]) for r in pos if r["進場日"] >= "2026-11-01"}
    fw = list(csv.DictReader(open(os.path.join(D, "forward.csv"), encoding="utf-8")))
    ok("K7 前瞻名單與月列", h1 == "30e87e3eb701136f" and h2 == "db0aab7b8a76ef1f" and len(c1) == 42 and len(c2) == 7 and len(c1 | c2) == 48
       and len(fw) == len(grp), f"（{h1}、{h2}、{len(c1)}＋{len(c2)}＝聯集 {len(c1 | c2)}；月列 {len(fw)}）")
    json.dump({"不過": BAD, "全過": not BAD}, open(os.path.join(D, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(os.path.join(D, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    log(f"== 查核 {'全過' if not BAD else '有不過：' + '、'.join(BAD)}")
    return 1 if BAD else 0


if __name__ == "__main__":
    sys.exit(main())
