# -*- coding: utf-8 -*-
"""PREREG期貨短線日線四題 查核（回測線）。⛔ 不呼叫 researchTXF／researchTXS 的 load_fut、daily、cal_events、holiday_blocks、tx_cost、rsi_wilder、run_engine、part_*：
用 researchTXF_check.Raw 從私有庫原始列（csv 模組）自己讀、自己逐日走契約；帳戶用「契約口數 × 200 × 點數」記帳（與本體的契約價值比例寫法不同）。
只從本體 import 資料常數（LUNAR 農曆表、FIXED 假日名單、段、L、H、格名）。比對本體寫在 ~/txfwork/short 與 resultsTXS 的結果。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTXS --check
"""
from __future__ import annotations

import csv
import datetime as dt
import glob
import json
import math
import os
import random
import time

import numpy as np
import pandas as pd

from backtest.researchTXF_check import Raw, fnum, margin_tbl, margin_at, rate_tbl
from backtest.researchTXS import LUNAR, FIXED, SEG, END, T0, LS, HS, CELL_A, CELL_C

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsTXS")
WORK = os.path.expanduser("~/txfwork/short")
TAIEX_CSV = "/home/chemtim/us-stock-data/data/macro/twse_taiex.csv"
FEE_H, FEE_L = 50.0, 20.0


def side(p, fee):
    return 0.00002 + (1.0 + fee / 50.0) / p


def close_ret(R):
    """自己逐日走：每個交易日 i 的近月連續收盤報酬（i−1 收 → i 收）。"""
    out = [float("nan")]
    for i in range(1, len(R.days)):
        out.append(R.walk(i - 1, i, "close", "close"))
    return np.array(out)


def trade_cost(R, i0, i1, start, fee):
    if start == "open":
        cur = R.near(i0); c = side(R.P(cur, i0, 0), fee); first = i0
    else:
        cur = R.near(i0)
        if R.last[cur] == i0:
            cur = R.nxt(i0, cur)
        c = side(R.P(cur, i0, 3), fee); first = i0 + 1
    for i in range(first, i1 + 1):
        if R.last[cur] == i:
            if i == i1:
                return c + side(R.SP(cur, i), fee)
            nc = R.nxt(i, cur); c += side(R.SP(cur, i), fee) + side(R.P(nc, i, 3), fee); cur = nc
        elif i == i1:
            return c + side(R.P(cur, i, 3), fee)
    raise RuntimeError("走不到出場日")


# ═════════════ 甲：事件日（自己的寫法） ═════════════
def my_holidays():
    H = {}
    for y in range(1989, 2028):
        for md, a, b, nm in FIXED:
            if (a is None or y >= a) and (b is None or y <= b):
                H[f"{y}-{md}"] = nm
    for y, (cny, dw, ma) in LUNAR.items():
        g = dt.date.fromisoformat(cny)
        for k in (-1, 0, 1, 2):
            H[(g + dt.timedelta(days=k)).isoformat()] = "春節"
        H[dw] = "端午"; H[ma] = "中秋"
    return H


def my_events(days):
    H = my_holidays()
    D = [dt.date.fromisoformat(d) for d in days]
    ev = {CELL_A["甲1"]: set(), CELL_A["甲2"]: set(), CELL_A["甲3"]: set(), "甲2 另報：春節前": set()}
    bym = {}
    for i, d in enumerate(D):
        bym.setdefault((d.year, d.month), []).append(i)
    keys = sorted(bym)
    for a, b in zip(keys[:-1], keys[1:]):
        j = bym[a][-1]; nx = bym[b]
        if j >= 1 and len(nx) >= 3 and nx[0] == j + 1:
            ev[CELL_A["甲1"]].add((days[j - 1], days[nx[2]]))
    for i in range(1, len(D)):
        if D[i].weekday() == 0:
            ev[CELL_A["甲3"]].add((days[i - 1], days[i]))
    for i in range(1, len(D) - 1):
        x = D[i] + dt.timedelta(days=1); wk = False; nm = set()
        while x < D[i + 1]:
            wk |= x.weekday() < 5
            if x.isoformat() in H:
                nm.add(H[x.isoformat()])
            x += dt.timedelta(days=1)
        if wk and nm:
            ev[CELL_A["甲2"]].add((days[i - 1], days[i]))
            if "春節" in nm:
                ev["甲2 另報：春節前"].add((days[i - 1], days[i]))
    return ev


def seg_of(d, segs):
    for s, (a, b) in segs.items():
        if a <= d <= b:
            return s
    return None


def cstats(x, m):
    x = np.asarray(x, float); n = len(x); mu = x.mean()
    g = {}
    for v, k in zip(x - mu, m):
        g[k] = g.get(k, 0.0) + v
    se = math.sqrt(sum(v * v for v in g.values())) / n
    return mu, mu - 1.96 * se, mu + 1.96 * se


def close_enough(a, b, rel=1e-8):
    return abs(a - b) <= rel * max(1e-6, abs(b))


def check_A(R, dr, out):
    days = R.days; ix = R.ix
    E = pd.read_csv(os.path.join(WORK, "A_events.csv.gz"), dtype={"entry": str, "exit": str})
    C = pd.read_csv(os.path.join(OUT, "A_cells.csv"))
    mine = my_events(days)
    bad = 0; cmp = 0
    # 事件集合：四格 × 三段
    for cell, st in mine.items():
        for seg, (a, b) in SEG.items():
            m_ = {x for x in st if a <= x[1] <= b}
            f_ = set(zip(E[(E["序列"] == "TX 近月") & (E["格"] == cell) & (E["段"] == seg)]["entry"], E[(E["序列"] == "TX 近月") & (E["格"] == cell) & (E["段"] == seg)]["exit"]))
            cmp += 1; bad += int(m_ != f_)
    # 全部 TX 判定格事件：報酬逐日走；成本逐日走；格平均重算
    tx = E[(E["序列"] == "TX 近月") & (E["格"].isin(list(CELL_A.values())))].reset_index(drop=True)
    Rm = np.array([R.walk(ix[a], ix[b], "close", "close") for a, b in zip(tx["entry"], tx["exit"])])
    ch = np.array([trade_cost(R, ix[a], ix[b], "close", FEE_H) for a, b in zip(tx["entry"], tx["exit"])])
    cmp += 2 * len(tx)
    bad += int((np.abs(Rm - tx["R"].to_numpy()) > 1e-12).sum()) + int((np.abs(ch - tx["cost_hi"].to_numpy()) > 1e-12 * ch).sum())
    cum = np.r_[1.0, np.cumprod(1.0 + dr[1:])]
    lab = {}
    for key, cell in CELL_A.items():
        k = 4 if key == "甲1" else 1
        res = {}
        for seg, (a, b) in SEG.items():
            base = np.mean([cum[i] / cum[i - k] - 1.0 for i in range(k, len(days)) if a <= days[i] <= b])
            q = tx[(tx["格"] == cell) & (tx["段"] == seg)]
            idx = q.index.to_numpy()
            mu, lo, hi = cstats(Rm[idx] - base, [d[:7] for d in q["exit"]])
            tmu, tlo, thi = cstats(Rm[idx] - ch[idx], [d[:7] for d in q["exit"]])
            row = C[(C["序列"] == "TX 近月") & (C["格"] == cell) & (C["段"] == seg)].iloc[0]
            cmp += 3
            bad += int(not close_enough(mu, row["X"])) + int(not close_enough(lo, row["lo"])) + int(not close_enough(tlo, row["扣成本高_lo"]))
            res[seg] = (mu, lo, hi, tlo)
        has = all(res[s][1] > 0 or res[s][2] < 0 for s in ("探索", "確認")) and np.sign(res["探索"][0]) == np.sign(res["確認"][0])
        lab[key] = (bool(has), bool(has and res["探索"][3] > 0 and res["確認"][3] > 0))
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    for key, (h, t) in lab.items():
        cmp += 2; bad += int(S["甲"]["判定"][key]["有"] != h) + int(S["甲"]["判定"][key]["可交易"] != t)
    # 加權指數早年：自己讀 csv
    tx_ = {}
    for r in csv.DictReader(open(TAIEX_CSV, encoding="utf-8")):
        v = fnum(r["close"])
        if v and v > 0:
            tx_[r["date"]] = v
    td = sorted(tx_); tpos = {d: i for i, d in enumerate(td)}
    mi = my_events(td)
    for key, cell in CELL_A.items():
        k = 4 if key == "甲1" else 1
        a, b = "1990-01-01", "2014-12-31"
        ev = sorted(x for x in mi[cell] if a <= x[1] <= b)
        base = np.mean([tx_[td[i]] / tx_[td[i - k]] - 1.0 for i in range(k, len(td)) if a <= td[i] <= b])
        x = [tx_[e1] / tx_[e0] - 1.0 - base for e0, e1 in ev]
        mu, lo, hi = cstats(x, [e1[:7] for e0, e1 in ev])
        row = C[(C["序列"] == "加權指數") & (C["格"] == cell)].iloc[0]
        cmp += 2; bad += int(not close_enough(mu, row["X"])) + int(int(row["n"]) != len(ev))
    out["① 甲 事件集合（4 格×3 段）、全部判定格事件的報酬與成本（逐日走契約）、9 格 X／lo／扣成本 lo、判定、加權指數早年 3 格"] = {"比對": cmp, "不同": bad}
    return bad


# ═════════════ 丙 ═════════════
def my_rsi2(P):
    out = [float("nan")] * len(P)
    ch = [P[i] - P[i - 1] for i in range(1, len(P))]
    up = [max(c, 0.0) for c in ch]; dn = [max(-c, 0.0) for c in ch]
    ag = (up[0] + up[1]) / 2.0; al = (dn[0] + dn[1]) / 2.0

    def f(ag, al):
        return (50.0 if ag == 0 else 100.0) if al == 0 else 100.0 - 100.0 / (1.0 + ag / al)
    out[2] = f(ag, al)
    for k in range(2, len(ch)):
        ag = (ag + up[k]) / 2.0; al = (al + dn[k]) / 2.0
        out[k + 1] = f(ag, al)
    return np.array(out)


def check_C(R, dr, out):
    days = R.days; nd = len(days)
    P = np.r_[1.0, np.cumprod(1.0 + dr[1:])]
    rsi = my_rsi2(P)
    trig = {CELL_C["丙1"]: dr <= -0.02, CELL_C["丙2"]: dr <= -0.03, CELL_C["丙3"]: rsi <= 10, CELL_C["丙4"]: rsi <= 5}
    E = pd.read_csv(os.path.join(WORK, "C_events.csv.gz"), dtype={"signal": str})
    C = pd.read_csv(os.path.join(OUT, "C_cells.csv"))
    bad = 0; cmp = 0
    lab = {}
    for H in HS:
        RH = {}
        for t in range(nd - H):
            RH[t] = R.walk(t + 1, t + H, "open", "close")
        nh = nt = 0
        for cell, tg in trig.items():
            res = {}
            for seg, (a, b) in SEG.items():
                ok = [t for t in range(nd - H) if days[t + 1] >= a and days[t + H] <= b]
                base = np.mean([RH[t] for t in ok])
                ev = [t for t in ok if tg[t]]
                f_ = E[(E["格"] == cell) & (E["H"] == H) & (E["段"] == seg)]
                cmp += 1; bad += int([days[t] for t in ev] != list(f_["signal"]))
                if not ev:
                    continue
                r = np.array([RH[t] for t in ev])
                cst = np.array([trade_cost(R, t + 1, t + H, "open", FEE_H) for t in ev])
                cmp += 2 * len(ev)
                if len(f_) == len(ev):
                    bad += int((np.abs(r - f_["R"].to_numpy()) > 1e-12).sum()) + int((np.abs(cst - f_["cost_hi"].to_numpy()) > 1e-12 * cst).sum())
                else:
                    bad += 2 * len(ev)
                mon = [days[t][:7] for t in ev]
                mu, lo, hi = cstats(r - base, mon); tmu, tlo, thi = cstats(r - cst, mon)
                row = C[(C["格"] == cell) & (C["H"] == H) & (C["段"] == seg)].iloc[0]
                cmp += 3; bad += int(not close_enough(mu, row["X"])) + int(not close_enough(lo, row["lo"])) + int(not close_enough(tlo, row["扣成本高_lo"]))
                res[seg] = (mu, lo, hi, tlo)
            has = all(res[s][1] > 0 or res[s][2] < 0 for s in ("探索", "確認")) and np.sign(res["探索"][0]) == np.sign(res["確認"][0])
            nh += has; nt += bool(has and res["探索"][3] > 0 and res["確認"][3] > 0)
        lab[f"H{H}"] = (nh >= 3, nt >= 3)
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    for k, (h, t) in lab.items():
        cmp += 2; bad += int(S["丙"]["判定"][k]["H 有"] != h) + int(S["丙"]["判定"][k]["H 可交易"] != t)
    out["② 丙 4 觸發×3H×3 段 事件日集合、全部事件 R_H 與成本（逐日走契約）、36 格 X／lo／扣成本 lo、H 判定"] = {"比對": cmp, "不同": bad}
    return bad


# ═════════════ 甲交易版、丁：契約口數記帳 ═════════════
def account(R, i0, i1, want_open, want_close, fee=FEE_H):
    tbl = margin_tbl(); rate = rate_tbl(); days = R.days
    E0 = 1e7; E = E0; n = 0.0; px = None; cur = None
    nav = {days[i0]: 1.0}

    def dirn(x):
        return 0 if x == 0 else (1 if x > 0 else -1)
    q = want_close[i0]
    if q:
        cur = R.near(i0)
        if R.last[cur] == i0:
            cur = R.nxt(i0, cur)
        p = R.P(cur, i0, 3); n = q * E / (200 * p); E -= abs(n) * 200 * p * side(p, fee); px = p
    for i in range(i0 + 1, i1 + 1):
        d = days[i]; dp = days[i - 1]
        im, _ = margin_at(tbl, dp)
        it = max(E - (im or 0.0) * abs(n), 0.0) * rate(dp) * (dt.date.fromisoformat(d) - dt.date.fromisoformat(dp)).days / 365.0
        near = R.near(i)
        O = R.P(near, i, 0)
        if n != 0:
            assert cur == near
            E += n * 200 * (O - px)
        E += it; px = O
        qo = want_open[i]
        if qo != dirn(n):
            E -= abs(n) * 200 * O * side(O, fee)
            n = qo * E / (200 * O); E -= abs(n) * 200 * O * side(O, fee); cur = near
        expiring = R.last[near] == i
        pc = R.SP(near, i) if expiring else R.P(near, i, 3)
        E += n * 200 * (pc - px); px = pc
        qc = want_close[i]
        if expiring:
            E -= abs(n) * 200 * pc * side(pc, fee)
            nc = R.nxt(i, near); pn = R.P(nc, i, 3)
            n = qc * E / (200 * pn); E -= abs(n) * 200 * pn * side(pn, fee); cur = nc; px = pn
        elif qc != dirn(n):
            E -= abs(n) * 200 * pc * side(pc, fee)
            n = qc * E / (200 * pc); E -= abs(n) * 200 * pc * side(pc, fee); cur = near
        nav[d] = E / E0
    return nav


def seg_nav(nav, a, b):
    ds = sorted(nav); base = [d for d in ds if d < a][-1]; w = [base] + [d for d in ds if a <= d <= b]
    v = np.array([nav[d] for d in w])
    cd = (dt.date.fromisoformat(w[-1]) - dt.date.fromisoformat(w[0])).days
    return (v[-1] / v[0]) ** (365.25 / cd) - 1, float(np.min(v / np.maximum.accumulate(v) - 1))


def check_paths(R, dr, out):
    days = R.days; nd = len(days)
    i1 = max(i for i, d in enumerate(days) if d <= END)
    z = np.load(os.path.join(WORK, "paths.npz"), allow_pickle=True)
    assert list(z["days"]) == days
    P = np.r_[1.0, np.cumprod(1.0 + dr[1:])]
    want = {}
    one = [1] * nd
    want["A_hold"] = (one, one); want["D_hold"] = (one, one)
    mine = my_events(days)
    for key, nm in (("甲1", "A_A1"), ("甲2", "A_A2"), ("甲3", "A_A3")):
        w = [0] * nd
        for a, b in mine[CELL_A[key]]:
            for i in range(R.ix[a], R.ix[b]):
                w[i] = 1
        want[nm] = ([0] + w[:-1], w)
    for L in LS:
        sig = [0] * nd; cur = 0
        for t in range(nd):
            if t >= L:
                s = P[t] / P[t - L] - 1.0
                cur = 1 if s > 0 else (-1 if s < 0 else cur)
            sig[t] = cur
        for tag, sg in (("ls", sig), ("lo", [max(x, 0) for x in sig])):
            op = [0] * nd
            for t in range(T0 + 1, nd):
                op[t] = sg[t - 1]
            want[f"D_L{L}_{tag}"] = (op, op)
    bad = 0; cmp = 0; worst = 0.0; navs = {}
    for key, (wo, wc) in want.items():
        nav = account(R, T0, i1, wo, wc)
        u = z[key]; navs[key] = nav
        for d, v in nav.items():
            x = u[R.ix[d]]; rd = abs(x / v - 1); worst = max(worst, rd); cmp += 1; bad += int(not (rd <= 1e-9))
    # 丁 判定格年化、回落（三段）
    D = pd.read_csv(os.path.join(OUT, "D_cells.csv"))
    for L in LS:
        for seg in ("早年", "探索", "確認"):
            row = D[(D["版"] == f"L{L} 多空") & (D["段"] == seg)].iloc[0]
            a, b = row["窗"].split("～")
            c_, m_ = seg_nav(navs[f"D_L{L}_ls"], a, b)
            cmp += 2; bad += int(not close_enough(c_, row["年化"], 1e-8)) + int(not close_enough(m_, row["最大回落"], 1e-8))
    # 判定重算（用 D_cells 的 0050 欄）
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    cnt = {}
    for seg in ("探索", "確認"):
        q = D[D["版"].str.endswith("多空") & (D["段"] == seg)]
        g = [(r["年化"] > r["0050_年化"]) and (r["回落比"] >= r["0050_回落比"]) for _, r in q.iterrows()]
        l1 = [(r["年化"] > r["0050_年化"]) for _, r in q.iterrows()]
        cnt[seg] = (sum(g), sum(l1))
    lab = "合格" if all(cnt[s][0] >= 3 for s in cnt) else ("另列" if all(cnt[s][1] >= 3 for s in cnt) else "不合格")
    cmp += 1; bad += int(lab != S["丁"]["判定"]["標籤"])
    out["③ 甲交易版 3 條＋一直持多 2 條＋丁 8 條 逐日淨值（契約口數記帳）、丁 12 格年化／回落、丁 標籤"] = {"比對": cmp, "不同": bad, "最大相對差": worst}
    return bad


# ═════════════ ④ 條款 ═════════════
def check_terms(out):
    banned = {"open", "high", "low", "close", "settle", "open_interest", "put_oi", "call_oi", "put_volume", "call_volume", "pc_oi_ratio_pct",
              "pc_volume_ratio_pct", "net_oi_volume", "initial_margin", "maintenance_margin", "initial_after", "maintenance_after", "結算價", "未平倉",
              "date", "entry", "exit", "signal", "R", "rsi2", "r"}
    hits = []; big = []
    for f in sorted(os.listdir(OUT)):
        p = os.path.join(OUT, f)
        if os.path.getsize(p) > 10 * 1024 * 1024:
            big.append(f)
        if f.endswith(".csv"):
            cols = set(pd.read_csv(p, nrows=0).columns)
            hits += [f"{f}:{c}" for c in cols & banned]
    priv = [os.path.relpath(x, os.path.expanduser("~/tw-p17")) for x in glob.glob(os.path.expanduser("~/tw-p17/**/taifex_private*"), recursive=True)]
    priv += [os.path.relpath(x, os.path.expanduser("~/tw-p17")) for x in glob.glob(os.path.expanduser("~/tw-p17/**/*.csv.gz"), recursive=True) if "short" in x or "txfwork" in x]
    out["④ 條款：resultsTXS 只放彙總（無原始欄、無逐日檔欄、每檔 < 10MB；repo 內無私有庫／中間檔複本）"] = {"原始欄命中": hits, "超過 10MB": big, "複本": priv,
                                                                               "不同": len(hits) + len(big) + len(priv)}
    return len(hits) + len(big) + len(priv)


def main():
    T_ = time.time()
    out = {"時間": f"{pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）"}
    R = Raw("TX")
    dr = close_ret(R)
    tot = 0
    for fn in (check_A, check_C, check_paths):
        tot += fn(R, dr, out)
        print(json.dumps({k: v for k, v in out.items() if k != "時間"}, ensure_ascii=False)[-260:], flush=True)
    tot += check_terms(out)
    out["耗時s"] = round(time.time() - T_)
    out["結論"] = "✅ 全過（0 不同）" if tot == 0 else f"⛔ 有不同（{tot}）"
    json.dump(out, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
