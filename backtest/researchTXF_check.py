# -*- coding: utf-8 -*-
"""PREREG台指期貨六題 抽樣查核（回測線）。⛔ 不呼叫 researchTXF 的 load_fut／daily／run_path／run_starts／pct_prior／part_*：
從私有庫原始列用 csv 模組自己讀、自己逐日走契約（契約口數記帳，與本體的「契約價值比例」寫法不同），比對本體寫在 ~/txfwork 與 resultsTXF 的結果。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTXF --check
"""
from __future__ import annotations

import csv
import glob
import json
import math
import os
import random
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsTXF")
WORK = os.path.expanduser("~/txfwork")
PRIV = "/home/chemtim/us-stock-data/data/taifex_private"
TAIEX_CSV = "/home/chemtim/us-stock-data/data/macro/twse_taiex.csv"
REL = 1e-9


def fnum(x):
    try:
        v = float(x)
    except ValueError:
        return None
    return v


class Raw:
    def __init__(self, prod="TX"):
        self.G = {}; self.N = {}
        for f in sorted(glob.glob(f"{PRIV}/fut_daily/{prod}/*.csv")):
            with open(f, encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    if r["is_spread"] != "0" or r["is_weekly"] != "0" or r["dup_seq"] not in ("", "1"):
                        continue
                    o, h, l, c = (fnum(r[k]) for k in ("open", "high", "low", "close"))
                    o, h, l, c = (v if (v is not None and v > 0) else None for v in (o, h, l, c))
                    if r["session"] == "一般":
                        s = fnum(r["settle"])
                        self.G.setdefault(r["date"], {})[r["expiry"]] = (o, h, l, c, s)
                    else:
                        self.N.setdefault(r["date"], {})[r["expiry"]] = (o, h, l, c)
        self.days = sorted(self.G)
        self.ix = {d: i for i, d in enumerate(self.days)}
        last = {}
        for i, d in enumerate(self.days):
            for e in self.G[d]:
                last[e] = i
        n = len(self.days)
        self.last = {e: (i if i < n - 1 else 10 ** 9) for e, i in last.items()}

    def near(self, i):
        return min(self.G[self.days[i]])

    def nxt(self, i, cur):
        return min(e for e in self.G[self.days[i]] if e > cur)

    def P(self, e, i, k):
        return self.G[self.days[i]][e][k]

    def SP(self, e, i):
        o, h, l, c, s = self.G[self.days[i]][e]
        return s if (s is not None and s > 0) else c

    def walk(self, i0, i1, start="open", end="close"):
        """i0 的 start 價進、i1 的 end 價出；到期日以結算價了結、同日收盤換次月。"""
        if start == "open":
            cur = self.near(i0); px = self.P(cur, i0, 0); first = i0
        else:  # close：i0 收盤持有的契約（到期日已換到次月）
            cur = self.near(i0)
            if self.last[cur] == i0:
                cur = self.nxt(i0, cur)
            px = self.P(cur, i0, 3); first = i0 + 1
        val = 1.0
        for i in range(first, i1 + 1):
            if end == "open" and i == i1:
                return val * self.P(cur, i, 0) / px - 1.0
            if self.last[cur] == i:
                val *= self.SP(cur, i) / px
                if i == i1:
                    return val - 1.0
                cur = self.nxt(i, cur); px = self.P(cur, i, 3)
            elif i == i1:
                return val * self.P(cur, i, 3) / px - 1.0
        return val - 1.0


def margin_tbl():
    rows = list(csv.DictReader(open(f"{PRIV}/margin/history_tx_mtx_tmf.csv", encoding="utf-8")))
    rows = sorted([r for r in rows if r["product"] == "TX"], key=lambda r: r["effective_date"])
    return [(r["effective_date"], float(r["initial_after"]), float(r["maintenance_after"])) for r in rows]


def margin_at(tbl, d):
    im = mm = None
    for eff, a, b in tbl:
        if eff <= d:
            im, mm = a, b
        else:
            break
    return im, mm


def rate_tbl():
    rows = list(csv.DictReader(open(f"{PRIV}/rates/bot_1y_deposit_monthly.csv", encoding="utf-8")))
    mp = {r["ym"]: float(r["fixed_1y_time_deposit"]) / 100 for r in rows}
    last = max(mp)
    return lambda d: mp.get(d[:7], mp[last] if d[:7] > last else 0.0)


# ═════════════ ① 甲：契約口數記帳的獨立帳戶 ═════════════
def acct(R, d0, d1, L, preday, rebal, fee):
    tbl = margin_tbl(); rate = rate_tbl()
    i0 = R.ix[d0]; i1 = R.ix[d1]
    feept = fee / 50.0
    def side(n, p):
        return abs(n) * 200.0 * (0.00002 * p + 1.0 + feept)
    E = 1e7
    cur = R.near(i0)
    if R.last[cur] <= i0 + (1 if preday else 0):
        cur = R.nxt(i0, cur)
    px = R.P(cur, i0, 3); n = L * E / (200 * px); E -= side(n, px)
    nav = {d0: 1.0}; navv = 1.0; Eprev = E
    for i in range(i0 + 1, i1 + 1):
        d = R.days[i]; dp = R.days[i - 1]
        im_p, _ = margin_at(tbl, dp)
        cash = E - (im_p or 0.0) * n
        days_ = (pd.Timestamp(d) - pd.Timestamp(dp)).days
        it = max(cash, 0.0) * rate(dp) * days_ / 365.0
        expiring = (R.last[cur] == i)
        p = R.SP(cur, i) if expiring else R.P(cur, i, 3)
        E += n * 200 * (p - px) + it
        im, mm = margin_at(tbl, d); dep = 0.0
        if mm is not None and E < mm * n:
            dep = im * n - E; E += dep
        roll = expiring if not preday else (R.last[cur] == i + 1)
        if roll:
            E -= side(n, p)
            new = R.nxt(i, cur); pn = R.P(new, i, 3)
            nn = L * E / (200 * pn) if rebal else n
            E -= side(nn, pn); cur, n, px = new, nn, pn
        else:
            px = p
        navv *= (E - dep) / Eprev; Eprev = E; nav[d] = navv
    return nav


def seg_from_nav(nav, a, b):
    ds = sorted(nav); base = [d for d in ds if d < a][-1]; w = [base] + [d for d in ds if a <= d <= b]
    v = np.array([nav[d] for d in w])
    cd = (pd.Timestamp(w[-1]) - pd.Timestamp(w[0])).days
    return (v[-1] / v[0]) ** (365.25 / cd) - 1, float(np.min(v / np.maximum.accumulate(v) - 1))


def check_A(R, out):
    z = np.load(os.path.join(WORK, "A_paths.npz"), allow_pickle=True)
    days = list(z["days"])
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    bad = 0; cmp = 0; worst = 0.0
    for key, (L, pre, reb, fee) in {"L2__結算日轉倉__每月調回__手續費高": (2, False, True, 50.0),
                                     "L1__結算前一日轉倉__不調__手續費低": (1, True, False, 20.0)}.items():
        nav = acct(R, "2005-01-31", "2026-09-30", L, pre, reb, fee)
        u = z[key]
        idx = {d: i for i, d in enumerate(days)}
        for d, v in nav.items():
            x = u[idx[d]]; cmp += 1
            rd = abs(x / v - 1)
            worst = max(worst, rd)
            bad += int(not (rd <= REL))
        if key.startswith("L2__結算日"):
            from backtest.researchTXF import A_SEG
            for seg, (a, b) in A_SEG.items():
                c_, m_ = seg_from_nav(nav, a, b)
                t = S["甲"]["主表"][seg]
                cmp += 2
                bad += int(abs(c_ - t["期貨_年化"]) > 1e-9) + int(abs(m_ - t["期貨_回落"]) > 1e-9)
    out["① 甲 逐日淨值（兩個變體、契約口數記帳）＋主格三段年化回落"] = {"比對": cmp, "不同": bad, "最大相對差": worst}
    return bad


# ═════════════ ② 乙：抽起點逐日重走 ═════════════
def check_B(R, out):
    z = np.load(os.path.join(WORK, "B_starts.npz"), allow_pickle=True)
    sd = list(z["days"])
    tx = {}
    for r in csv.DictReader(open(TAIEX_CSV, encoding="utf-8")):
        v = fnum(r["close"])
        if v and v > 0:
            tx[r["date"]] = v
    tdays = sorted(tx)
    timeline = [d for d in tdays if d < R.days[0]] + R.days
    tbl = margin_tbl()
    # 推算段調倉日
    reb = set()
    pre = [d for d in tdays if d < R.days[0]]
    bym = {}
    for d in pre:
        bym.setdefault(d[:7], []).append(d)
    for ym, ds in bym.items():
        y, m = int(ym[:4]), int(ym[5:])
        f = pd.Timestamp(year=y, month=m, day=1); w3 = f + pd.Timedelta(days=(2 - f.weekday()) % 7 + 14)
        k = [d for d in ds if pd.Timestamp(d) >= w3]
        if k:
            reb.add(k[0])
    rng = random.Random(7)
    picks = rng.sample(range(len(sd)), 60)
    bad = 0; cmp = 0
    for L in (2, 5, 10, 14):
        fin = z[f"L{L}_final"]; fc = z[f"L{L}_fc"]
        for s in picks:
            d0 = sd[s]; pos0 = timeline.index(d0)
            E = 1.0; V = float(L)
            if d0 >= R.days[0]:
                i = R.ix[d0]; cur = R.near(i)
                if R.last[cur] == i:
                    cur = R.nxt(i, cur)
                ref = R.P(cur, i, 3); E -= V * (0.00002 + 2.0 / ref)
            else:
                cur = None; ref = tx[d0]
            alive = True; first = -1
            for k in range(pos0 + 1, pos0 + 251):
                d = timeline[k]
                if d < R.days[0]:
                    r = tx[d] / tx[timeline[k - 1]] - 1; lr = r; roll = d in reb; cx = ce = 0.0; mmf = None; pn = None
                elif d == R.days[0]:
                    r = tx[d] / tx[timeline[k - 1]] - 1; lr = r; roll = True; cx = 0.0
                    i = 0; cur = R.near(0); pn = R.P(cur, 0, 3); ce = 0.00002 + 2.0 / pn; mmf = None
                else:
                    i = R.ix[d]
                    expiring = R.last[cur] == i
                    p = R.SP(cur, i) if expiring else R.P(cur, i, 3)
                    lo = R.P(cur, i, 2); nl = R.N.get(d, {}).get(cur)
                    if nl and nl[2] is not None:
                        lo = min(lo, nl[2])
                    r = p / ref - 1; lr = min(lo / ref - 1, r)
                    im, mm = margin_at(tbl, d); mmf = (mm / (200 * p)) if mm else None
                    roll = expiring; cx = 0.00002 + 2.0 / p if roll else 0.0
                    if roll:
                        cur = R.nxt(i, cur); pn = R.P(cur, i, 3); ce = 0.00002 + 2.0 / pn
                    else:
                        pn = None; ce = 0.0
                if alive and E + V * lr <= 0:
                    alive = False
                if not alive:
                    E = 0.0; V = 0.0
                    continue
                E += V * r; V *= (1 + r)
                if mmf is not None and first < 0 and E < mmf * V:
                    first = k
                if roll:
                    E -= V * cx; V = L * E; E -= V * ce
                if d >= R.days[0]:
                    ref = pn if roll else p
                    if d == R.days[0]:
                        ref = pn
                else:
                    ref = tx[d]
            got_f = fin[s]; got_c = fc[s]
            mine_f = E if alive else 0.0
            cmp += 2
            bad += int(not (abs(got_f - mine_f) <= 1e-9 * max(1, abs(mine_f))))
            exp_c = (sd.index(timeline[first]) if False else first)
            bad += int((got_c >= 0) != (first >= 0) or (first >= 0 and timeline[int(got_c)] != timeline[first]))
    out["② 乙 抽 60 個起點 × L{2,5,10,14}（不補路一年後權益、第一次追繳日）"] = {"比對": cmp, "不同": bad}
    return bad


# ═════════════ ③ 丙 ═════════════
def check_C(R, out):
    ev = pd.read_csv(os.path.join(WORK, "C_days.csv.gz"), dtype={"date": str})
    nser = []
    for i in range(1, len(R.days)):
        d = R.days[i]
        if d < "2017-05-16":
            continue
        cur = R.near(i)
        nn = R.N.get(d, {}).get(cur); pc = R.G[R.days[i - 1]].get(cur)
        if nn and nn[3] and pc and pc[3]:
            nser.append((d, nn[3] / pc[3] - 1, i, cur))
    vals = [x[1] for x in nser]
    grp = {}
    for k in range(250, len(nser)):
        p = sum(1 for v in vals[k - 250:k] if v < vals[k]) / 250
        grp[nser[k][0]] = (min(9, int(math.floor(p * 10))), nser[k])
    rng = random.Random(11); pick = rng.sample(list(ev.index), 300)
    bad = 0
    for j in pick:
        r = ev.loc[j]; g, (d, n, i, cur) = grp[r["date"]]
        o, h, l, c, s = R.G[d][cur]; nc = R.N[d][cur][3]
        bad += int(g != int(r["grp"])) + int(abs(n - r["n"]) > 1e-12) + int(abs((c / o - 1) - r["d"]) > 1e-12) + int(abs((c / nc - 1) - r["d2"]) > 1e-12)
    # 格平均由逐日重算
    C = pd.read_csv(os.path.join(OUT, "C_cells.csv"))
    from backtest.researchTXF import C_SEG
    mism = 0
    for seg, (a, b) in C_SEG.items():
        s_ = ev[(ev["date"] >= a) & (ev["date"] <= b)]
        for y in ("d", "d2"):
            base = s_[y].mean()
            for gname, gv in (("最高組", 9), ("最低組", 0)):
                x = (s_[s_["grp"] == gv][y] - base).mean()
                t = C[(C["段"] == seg) & (C["格"] == f"{y}｜{gname}")]["X"].iloc[0]
                mism += int(not (abs(x - t) <= 1e-8 * max(1e-6, abs(t))))      # cells.csv 存 10 位有效數字
    out["③ 丙 抽 300 日（n、d、d2、分組）＋ 8 格平均"] = {"比對": 300 * 4 + 8, "不同": bad + mism}
    return bad + mism


# ═════════════ ④ 丁 ═════════════
def check_D(R, out):
    ev = pd.read_csv(os.path.join(WORK, "D_events.csv.gz"), dtype={"date": str})
    ev = ev[ev["指標"].str.startswith("x3") | ev["指標"].str.startswith("x4")]
    pc = {r["date"]: r for r in csv.DictReader(open(f"{PRIV}/pc_ratio.csv", encoding="utf-8"))}
    def series(col):
        out_ = []
        for d in R.days:
            if d in pc and fnum(pc[d][col]) is not None:
                out_.append((d, float(pc[d][col])))
        return out_
    pcts = {}
    for name, col in (("x3", "pc_oi_ratio_pct"), ("x4", "pc_volume_ratio_pct")):
        s = series(col); v = [x[1] for x in s]
        pcts[name] = {s[k][0]: sum(1 for q in v[k - 250:k] if q < v[k]) / 250 for k in range(250, len(s))}
    rng = random.Random(13); pick = rng.sample(list(ev.index), 200)
    bad = 0
    for j in pick:
        r = ev.loc[j]; name = r["指標"][:2]; d = r["date"]; H = int(r["H"]); i = R.ix[d]
        p = pcts[name][d]
        grp = "高" if p >= 0.9 else ("低" if p < 0.1 else "中")
        Rm = R.walk(i + 1, i + H, "open", "close")
        bad += int(grp != r["組"]) + int(abs(Rm - r["R"]) > 1e-12)
    out["④ 丁 抽 200 筆（分位組、R_H 逐日走契約）"] = {"比對": 400, "不同": bad}
    return bad


# ═════════════ ⑤ 戊 ═════════════
def check_E(R, out):
    ev = pd.read_csv(os.path.join(WORK, "E_events.csv.gz"), dtype={"end": str})
    tx = {}
    for r in csv.DictReader(open(TAIEX_CSV, encoding="utf-8")):
        v = fnum(r["close"])
        if v and v > 0:
            tx[r["date"]] = v
    td = sorted(tx); tix = {d: i for i, d in enumerate(td)}
    expd = sorted(R.days[i] for e, i in R.last.items() if i < 10 ** 9)
    rng = random.Random(17); pick = rng.sample(list(ev.index), 200)
    bad = 0
    for j in pick:
        r = ev.loc[j]; k = 3 if r["窗"].startswith("①") else 1
        post = r["窗"].startswith("③")
        if r["序列"] == "加權指數":
            i = tix[r["end"]]; Rm = tx[td[i]] / tx[td[i - k]] - 1
            e = td[i - 1] if post else td[i]
        else:
            i = R.ix[r["end"]]; Rm = R.walk(i - k, i, "close", "close")
            e = R.days[i - 1] if post else R.days[i]
        bad += int(abs(Rm - r["R"]) > 1e-12) + int(e not in expd)
    out["⑤ 戊 抽 200 筆（窗報酬、結算日身分）"] = {"比對": 400, "不同": bad}
    return bad


# ═════════════ ⑥ 己 ═════════════
def check_F(R, out):
    from backtest import data as D
    from backtest import exit_signal as XS
    ev = pd.read_csv(os.path.join(WORK, "F_rev_events.csv.gz"), dtype={"基準日": str})
    old = D.DATA; D.DATA = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
    try:
        cal = [str(x.date()) for x in D.load_calendar()]
    finally:
        D.DATA = old
    pos = {d: i for i, d in enumerate(cal)}
    w1 = pos["2026-08-24"]
    rng = random.Random(19); pick = rng.sample(list(ev.index), 150)
    bad = 0
    for j in pick:
        r = ev.loc[j]; b = pos[r["基準日"]]
        d_in = cal[b + 1]; d_out = cal[b + 20]
        while d_out not in R.ix:
            d_out = cal[pos[d_out] - 1]
        Rm = R.walk(R.ix[d_in], R.ix[d_out], "open", "close")
        o = R.P(R.near(R.ix[d_in]), R.ix[d_in], 0)
        cost = 2 * (0.00002 + 2.0 / o)
        bad += int(abs(Rm - r["R20_TX"]) > 1e-12) + int(abs(cost - r["cost"]) > 1e-12 * cost)
    # 判定由逐筆重算
    C = pd.read_csv(os.path.join(OUT, "F_rev_cells.csv"))
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    z = S["己"]["反轉訊號"]["Bonferroni z（沿用原件 k＝28）"]; btx = S["己"]["反轉訊號"]["TX 基準 R20 平均"]
    w0 = pos["2017-03-02"]; mism = 0
    for _, c in C[C["n_eff"] >= 10].iterrows():
        e = ev[(ev["code"] == c["code"]) & (ev["版"] == c["版"])]
        g = np.array([(pos[d] - w0) // 20 for d in e["基準日"]])
        sg = 1.0 if c["邊"] == "低" else -1.0
        x = e["R20_TX"].to_numpy() - btx - sg * e["cost"].to_numpy()
        m = x.mean(); dd = x - m
        keys = sorted(set(g)); se = math.sqrt(sum(dd[g == k].sum() ** 2 for k in keys)) / len(x)
        lo, hi = m - z * se, m + z * se
        ne = min(len(x), len(keys))
        if ne < 30:
            res = "—（樣本不足以分辨）"
        elif lo <= 0 <= hi:
            res = "結果①"
        else:
            res = "結果③" if m < 0 else "結果②"
        ok = (res == "結果③") if c["邊"] == "高" else (res == "結果②")
        mism += int(not (abs(m - c["TX扣期貨成本_X"]) <= 1e-8 * max(1e-6, abs(m)))) + int(("通過" if ok else "不通過") != c["TX扣期貨成本_判定"])
    out["⑥ 己 抽 150 筆 R20_TX 與成本 ＋ 28 格判定重算"] = {"比對": 300 + 2 * int((C["n_eff"] >= 10).sum()), "不同": bad + mism}
    return bad + mism


# ═════════════ ⑦ 條款：repo 只放彙總 ═════════════
def check_terms(out):
    banned = {"open", "high", "low", "close", "settle", "open_interest", "put_oi", "call_oi", "put_volume", "call_volume", "pc_oi_ratio_pct",
              "pc_volume_ratio_pct", "net_oi_volume", "initial_margin", "maintenance_margin", "initial_after", "maintenance_after", "結算價", "未平倉"}
    hits = []; big = []
    for f in sorted(os.listdir(OUT)):
        p = os.path.join(OUT, f)
        if os.path.getsize(p) > 10 * 1024 * 1024:
            big.append(f)
        if f.endswith(".csv"):
            cols = set(pd.read_csv(p, nrows=0).columns)
            hits += [f"{f}:{c}" for c in cols & banned]
            if "date" in cols:
                hits.append(f"{f}:date（逐日檔）")
    priv_copies = [os.path.relpath(x, os.path.expanduser("~/tw-p17")) for x in glob.glob(os.path.expanduser("~/tw-p17/**/taifex_private*"), recursive=True)]
    out["⑦ 條款：resultsTXF 只放彙總（無原始欄、無逐日檔、< 10MB；repo 內無私有庫複本）"] = {"原始欄命中": hits, "超過 10MB": big, "私有庫複本": priv_copies,
                                                                       "不同": len(hits) + len(big) + len(priv_copies)}
    return len(hits) + len(big) + len(priv_copies)


def main():
    T0 = time.time()
    out = {"時間": f"{pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）"}
    R = Raw("TX")
    tot = 0
    for fn in (check_A, check_B, check_C, check_D, check_E, check_F):
        tot += fn(R, out)
        print(json.dumps({k: v for k, v in out.items() if k != "時間"}, ensure_ascii=False)[-300:], flush=True)
    tot += check_terms(out)
    out["耗時s"] = round(time.time() - T0)
    out["結論"] = "✅ 全過（0 不同）" if tot == 0 else f"⛔ 有不同（{tot}）"
    json.dump(out, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
