# -*- coding: utf-8 -*-
"""PREREG跌深加碼 獨立查核（⛔ 不 import backtest 任何模組）。

    cd ~/tw-p17 && ~/tw-p16/.venv/bin/python backtest/researchDip_check.py

獨立：自接 0050／0052（早年 tar ＋ 主快照 CSV／adj）、00631L／00685L 自還原；dd 用 pandas rolling max；
      模擬用【金額制】（各檔持有金額逐日乘價格比；成交日拆 前收→開盤、開盤→收盤）
K1 body_cells.csv 全部 344 列 年化／回落／動手日數／加碼階數｜K2 挑法乙、甲｜K3 挑中那組確認段逐筆動作（日期、類別）｜
K4 假訊號 1,000 次（讀存的隨機日）｜K5 刪減表（兩種挑法、判）｜K6 2022 與壓力段
"""
import glob
import io
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

SNAP = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
YD = os.path.expanduser("~/ydata/3edc0e2206")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultsDip")
COST, FEE, ANN, TOL = 0.00385, 0.01 / 245, 245, 1e-9
LAD = {"L1": (0.10, 0.20, 0.30), "L2": (0.15, 0.30, 0.45)}
bad = []


def chk(n, ok, det=""):
    print(("✅" if ok else "⛔"), n, det, flush=True)
    if not ok:
        bad.append(n)


st = pd.read_csv(os.path.join(YD, "data/early/_structure.csv"), dtype=str)
early = sorted(st.loc[(st["market"] == "twse") & (pd.to_numeric(st["rows"]) > 0), "date"])
mainc = pd.read_csv(os.path.join(SNAP, "meta/calendar_twse.csv"), dtype=str)["date"].tolist()
cal = early + mainc; N = len(cal); pos = {d: i for i, d in enumerate(cal)}


def main_part(sid):
    r = pd.read_csv(os.path.join(SNAP, "stocks", f"{sid}.csv"), dtype=str)
    a = pd.read_csv(os.path.join(SNAP, "adj", f"{sid}.csv"), dtype=str)
    O = np.full(N, np.nan); C = np.full(N, np.nan); first_raw = None
    for d, o, h, l, c in zip(r["date"], *(pd.to_numeric(r[k], errors="coerce") for k in ("open", "high", "low", "close"))):
        if not all(pd.notna(x) and x > 0 for x in (o, h, l, c)):
            continue
        f = next((float(x) for e, x in zip(a["date"], a["cum_factor"]) if e > d), 1.0)
        O[pos[d]] = o * f; C[pos[d]] = c * f
        if first_raw is None:
            first_raw = (d, c)
    return O, C, first_raw


def early_part(sid, O, C, first_raw):
    s = C[pos[first_raw[0]]] / first_raw[1]
    txt = subprocess.run(f"grep -h '^[0-9-]*_{sid},' {YD}/data/early/daily/*.csv", shell=True, capture_output=True, text=True).stdout
    ex = []
    for fn in sorted(glob.glob(f"{YD}/data/early/exright/*.csv")):
        x = pd.read_csv(fn, dtype=str); x = x[x["stock_id"] == sid]
        ex += [(q["date"], float(q["ref_price"]) / float(q["pre_close"])) for _, q in x.iterrows()]
    for line in txt.splitlines():
        p = line.split(",")
        if p[1] >= mainc[0]:
            continue
        vals = [pd.to_numeric(v, errors="coerce") for v in p[5:9]]
        if not all(pd.notna(v) and v > 0 for v in vals):
            continue
        f = s
        for e, q in ex:
            if e > p[1]:
                f *= q
        O[pos[p[1]]] = vals[0] * f; C[pos[p[1]]] = vals[3] * f


PX = {}
for sid in ("0050", "0052", "00631L", "00685L"):
    O, C, fr = main_part(sid)
    if sid in ("0050", "0052"):
        early_part(sid, O, C, fr)
    PX[sid] = (O, pd.Series(C).ffill().to_numpy(), C)
b = np.flatnonzero(np.isfinite(PX["0050"][2])); c50 = pd.Series(PX["0050"][2][b])
hi = c50.rolling(250).max().to_numpy(); ddb = c50.to_numpy() / hi - 1; nhb = c50.to_numpy() >= hi
DD = pd.Series(np.full(N, np.nan)); DD[b] = ddb; DD = DD.ffill().to_numpy()
NH = np.zeros(N, bool); NH[b] = np.nan_to_num(nhb.astype(float), nan=0).astype(bool)


def sim(P, H, A, r, lad, R, i0, i1, d3="b", rand=None):
    th = LAD[lad] if isinstance(lad, str) else ()
    ass = [H] if A == H else [H, A]
    hv = {a: 0.0 for a in ass}; cash = 1.0; armed = [True] * len(th); cres = 0.0; bought = False; pend = False; init = False
    eq = []; acts = []; rungs = 0
    rs = set(rand) if rand is not None else None
    for k, t in enumerate(range(i0, i1 + 1)):
        O = {a: P[a][0][t] for a in ass}; C = {a: P[a][1][t] for a in ass}; Cp = {a: P[a][1][t - 1] for a in ass}
        reb = (not init) or (init and ((R == "R1" and NH[t - 1] and bought) or (R == "R2" and cal[t][:4] != cal[t - 1][:4]) or pend))
        if init and NH[t - 1]:
            armed = [True] * len(th)
        fire = []
        if th and (init or d3 == "a"):
            fire = [j for j, x in enumerate(th) if armed[j] and DD[t - 1] <= -x] if rs is None else (["r"] if k in rs else [])
        need = ({H} | {a for a in ass if hv[a] > 0} if reb else set()) | ({A} if fire else set())
        if (reb or fire) and not all(np.isfinite(O[a]) for a in need):
            if reb and init:
                pend = True
            reb, fire = False, []
        traded = bool(reb or fire)
        tset = set(ass) if reb else ({A} if fire else set())          # 當天經過開盤的標的
        hvo = {a: hv[a] * O[a] / Cp[a] if (hv[a] > 0 and a in tset) else 0.0 for a in ass}
        keep = {a: hv[a] * C[a] / Cp[a] if (hv[a] > 0 and a not in tset) else 0.0 for a in ass}
        if reb:
            first = not init
            if first:
                init = True
                if d3 == "b":
                    armed = [not (DD[t - 1] <= -x) for x in th]
            V = sum(hvo.values()) + cash
            tr = 0.5 * (abs((1 - r) * V - hvo[H]) + sum(hvo[a] for a in ass if a != H) + abs(r * V - cash))
            V -= tr * COST
            hvo = {a: 0.0 for a in ass}; hvo[H] = (1 - r) * V; cash = r * V; cres = cash; bought = False; pend = False
            if not first and tr > 0:
                acts.append((cal[t], "回補" if R == "R1" else "年初調回"))
        if fire:
            if rs is None:
                last = (len(th) - 1) in fire
                amt = cash if last else min(cash, cres / 3 * len(fire))
                for j in fire:
                    armed[j] = False
                rungs += len(fire)
            else:
                amt = min(cash, cres / 3); rungs += 1
            amt = min(amt, cash / (1 + COST))
            if amt > 0:
                hvo[A] += amt; cash -= amt * (1 + COST); bought = True; acts.append((cal[t], "加碼"))
        if traded:
            hv = {a: (hvo[a] * C[a] / O[a] if hvo[a] > 0 else 0.0) + keep[a] for a in ass}
        else:
            hv = {a: hv[a] * C[a] / Cp[a] if hv[a] > 0 else 0.0 for a in ass}
        eq.append(sum(hv.values()) + cash)
    eq = np.array(eq); p = np.r_[1.0, eq]; pk = np.maximum.accumulate(p)
    return eq, eq[-1] ** (ANN / len(eq)) - 1, ((p - pk) / pk).min(), acts, rungs


def lab(c, m, c5, m5):
    return "合格" if (c > c5 and (c / abs(m) if m < 0 else np.nan) >= c5 / abs(m5)) else ("另列" if c > c5 else "不合格")


W = {("主窗", "探索"): ("2015-11-02", "2021-12-30"), ("主窗", "確認"): ("2022-01-03", "2026-08-24"),
     ("00685L窗", "探索"): ("2018-01-15", "2021-12-30"), ("00685L窗", "確認"): ("2022-01-03", "2026-08-24")}
B5 = {}
for k, (a, e) in W.items():
    s = PX["0050"][1][pos[a]:pos[e] + 1] / PX["0050"][1][pos[a]]; pk = np.maximum.accumulate(s)
    B5[k] = ((s[-1]) ** (1 / (len(s) / ANN)) - 1, ((s - pk) / pk).min())
df = pd.read_csv(os.path.join(OUT, "body_cells.csv"), dtype={"H": str, "A": str})
mx = 0.0; nb = 0; RES = {}
for _, r in df.iterrows():
    i0, i1 = pos[W[(r["跑在"], r["段"])][0]], pos[W[(r["跑在"], r["段"])][1]]
    eq, cg, md, acts, rg = sim(PX, r["H"], r["A"], float(r["r"]), r["梯"], r["回補"], i0, i1)
    RES[(r["列"], r["跑在"], r["段"])] = (cg, md, eq, acts)
    nd = len(set(a[0] for a in acts)) / ((i1 - i0 + 1) / ANN)
    dmx = max(abs(cg - r["年化"]), abs(md - r["回落"])); mx = max(mx, dmx)
    if dmx > TOL or rg != r["加碼階數"]:
        print("  差", r["名稱"], r["跑在"], r["段"], cg, r["年化"], rg, r["加碼階數"])
    nb += (abs(nd - r["動手日／年"]) > 1e-9) + (rg != r["加碼階數"]) + (lab(cg, md, *B5[(r["跑在"], r["段"])]) != r["對0050（描述）"])
chk("K1 344 列 年化／回落／動手日數／加碼階數／標籤", mx < TOL and nb == 0, f"最大差 {mx:.1e}、次數或標籤不符 {nb}")

S = json.load(open(os.path.join(OUT, "body_summary.json"), encoding="utf-8"))
ex = df[(df["跑在"] == "主窗") & (df["窗組"] == "主窗") & (df["型"] == "格") & (df["段"] == "探索")]
top = ex.loc[ex["年化"].idxmax()]; topa = ex.loc[ex["比值"].idxmax()]
chk("K2 挑法乙／甲", top["名稱"] == S["挑法乙"]["格"] and topa["名稱"] == S["挑法甲（並列）"]["格"], f"乙 {top['名稱']}；甲 {topa['名稱']}")

act = pd.read_csv(os.path.join(OUT, "body_pick_actions_confirm.csv"))
mine = RES[(top["列"], "主窗", "確認")][3]
chk("K3 挑中那組確認段逐筆動作", [(a, b_) for a, b_ in mine] == list(zip(act["日"], act["類"])), f"{len(mine)} 筆")

z = np.load(os.path.join(OUT, "body_null_days.npz")); days = z["days"]
nl = pd.read_csv(os.path.join(OUT, "body_null.csv"))
i0, i1 = pos["2022-01-03"], pos["2026-08-24"]
c0 = df[(df["型"] == "C0") & (df["H"] == top["H"]) & (df["跑在"] == "主窗") & (df["窗組"] == "主窗") & (df["段"] == "確認")].iloc[0]
cs = np.array([sim(PX, top["H"], top["A"], float(top["r"]), top["梯"], top["回補"], i0, i1, rand=list(d))[1] for d in days])
chk("K4 假訊號 1,000 次", np.max(np.abs(cs - nl["年化"].to_numpy())) < TOL and float(np.mean(cs > c0["年化"])) == S["假訊號"]["贏同H C0 比例（主讀）"],
    f"贏同 H C0 {np.mean(cs > c0['年化'])}")

dl = pd.read_csv(os.path.join(OUT, "body_delete.csv")); okd = 0
for _, r in dl.iterrows():
    w = "00685L窗" if r["X"] == "00685L" else "主窗"
    e = df[(df["跑在"] == w) & (df["段"] == "探索")]
    if r["X"] != "00685L":
        e = e[e["窗組"] == "主窗"]
    use = e.apply(lambda q: (q["型"] != "C0") if r["X"] == "現金" else (r["X"] in (q["H"], q["A"])), axis=1)
    key = "年化" if r["挑法"].startswith("乙") else "比值"
    pw = e[use].sort_values([key, "動手日／年"], ascending=[False, True], kind="stable").iloc[0]
    po = e[~use].sort_values([key, "動手日／年"], ascending=[False, True], kind="stable").iloc[0]
    cw = RES[(pw["列"], w, "確認")]; co = RES[(po["列"], w, "確認")]
    judge = "可刪" if (co[0] - cw[0] >= -0.005 and co[1] - cw[1] >= -0.01) else "有貢獻"
    okd += (pw["名稱"] == r["含X最好"]) and (po["名稱"] == r["不含X最好"]) and judge == r["判"]
chk("K5 刪減表 10 列", okd == len(dl), f"{okd}/{len(dl)}")

# K6 2022、壓力
ny = pos["2022-12-30"] - i0 + 1
eqp = RES[(top["列"], "主窗", "確認")][2]
t22 = min(1.0, eqp[:ny].min()) * 1e6
s0, s1 = pos["2006-09-12"], pos["2014-12-31"]
o, cc = PX["0050"][0], PX["0050"][1]
Lc = np.full(N, np.nan); Lo = np.full(N, np.nan); Lc[s0 - 2] = 1.0
for t in range(s0 - 1, N):
    Lo[t] = Lc[t - 1] * (1 + 2 * (o[t] / cc[t - 1] - 1)) if np.isfinite(o[t]) else np.nan
    Lc[t] = Lc[t - 1] * (1 + 2 * (cc[t] / cc[t - 1] - 1) - FEE)
PS = dict(PX); PS["00631L"] = (Lo, Lc, Lc)
stv = pd.read_csv(os.path.join(OUT, "body_stress.csv")); mx = 0.0
for _, r in stv.iterrows():
    a, e_ = (s0, s1) if r["期間"].startswith("2006") else (pos["2008-01-02"], pos["2009-03-31"])
    if r["對象"].startswith("挑中"):
        eq = sim(PS, top["H"], top["A"], float(top["r"]), top["梯"], top["回補"], a, e_)[0]
    elif r["對象"].startswith("C0"):
        eq = sim(PS, top["H"], top["H"], 0.0, None, "—", a, e_)[0]
    else:
        eq = cc[a:e_ + 1] / cc[a - 1]
    p = np.r_[1.0, eq]; pk = np.maximum.accumulate(p)
    mx = max(mx, abs(((p - pk) / pk).min() - r["最大跌幅"]), abs(p.min() * 1e6 - r["100萬谷底剩"]) / 1e6)
chk("K6 2022 谷底、壓力段 6 列", abs(t22 - S["2022"]["挑中"]["谷底（100萬）"]) < 1e-3 and mx < TOL, f"2022 {t22:.0f}；壓力最大差 {mx:.1e}")
print("⛔ 不過：" + "、".join(bad) if bad else "✅ 全過")
sys.exit(1 if bad else 0)
