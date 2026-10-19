# -*- coding: utf-8 -*-
"""USREG-C11L seq2（月頻）獨立查核：⭐ 不 import 主程式的計算函式；csv 模組讀原始檔、純 Python 迴圈重算。回測線，台北 2026-10-20。

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSC11L_m_check            # 真實資料（主程式跑完後）
    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSC11L_m_check --fixture  # 合成 fixture（不碰真實資料）

X1 判定格全重算：日曆、^SP500TR、DTB3 前值補、合成 SSO 逐日、月底、(DGS7＋DGS10)/2 月底、平價債 D／C（直接定價數值微分）、Pink Sheet、組合迴圈
   ⇒ 年化、回落、比值、標籤、基準、1994、2000～02、同曝險、IEF／黃金對帳年差 對 C11L_m_summary.json（|差| ≤ 1e-6：D、C 用直接定價數值微分，與解析式差約 1e-7 相對）。
X2 月報酬連乘 ＝ 日頻首尾：主程式逐月序列（~/us_work/c11l_m/series.npz）連乘 對 本檔自算的日頻首尾比（合成 SSO、^SP500TR、真實 SSO／IEF／GLD、Pink Sheet）。
X3 抽樣月手算：1990-08、1994-02、2001-09（合成三腿）、2008-10（真實三腿）逐腿手算 對 主程式序列（門檻 1e-9；IEF 因 D、C 用數值微分 ⇒ 1e-7）。
X4 判準重算：由主程式權益路徑重算年化、回落、比值與標籤（A1 判準式逐字重寫）對 summary。
fixture：常數報酬假資料（~/us_work/c11l_m/fixture，repo 外），主程式跑一次，逐項對解析值；另以直接定價驗 D、C。
⛔ check.json 只放差值與通過旗標，不放任何價格。
"""
from __future__ import annotations

import csv
import json
import math
import os
import subprocess
import sys

import numpy as np

OUT = os.environ.get("C11LM_OUT", os.path.expanduser("~/tw-p17/backtest/resultsUSC11L_m"))
WORK = os.environ.get("C11LM_WORK", os.path.expanduser("~/us_work/c11l_m"))
ROOT = os.environ.get("US_DATA_ROOT_C11LM", os.path.expanduser("~/usdata/4bdd82b"))
CAL_END = "2026-09-30"
TOL = 1e-9


def rd(root, name):
    with open(os.path.join(root, "data", "macro", name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def num(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def mprev(m):
    y, k = int(m[:4]), int(m[5:7])
    return f"{y - 1}-12" if k == 1 else f"{y}-{k - 1:02d}"


def months(a, b):
    out = []; m = a
    while m <= b:
        out.append(m); y, k = int(m[:4]), int(m[5:7]); m = f"{y + 1}-01" if k == 12 else f"{y}-{k + 1:02d}"
    return out


def price(y, cpn, T=8.5):
    n = int(round(T * 2)); return sum(cpn / 2 / (1 + y / 2) ** k for k in range(1, n + 1)) + 1 / (1 + y / 2) ** n


def dc_num(y, h=1e-4):
    p0, pu, pdn = price(y, y), price(y + h, y), price(y - h, y)
    return -(pu - pdn) / (2 * h) / p0, (pu - 2 * p0 + pdn) / h ** 2 / p0


def load(root):
    cal = sorted({r["date"] for r in rd(root, "yahoo_GSPC.csv") if r["date"] <= CAL_END})
    me = {}
    for i, d in enumerate(cal):
        if i == len(cal) - 1 or cal[i + 1][:7] != d[:7]:
            me[d[:7]] = i
    def series(name, col="adjclose"):
        m = {r["date"]: num(r[col]) for r in rd(root, name)}
        out = []; last = None
        for d in cal:
            v = m.get(d)
            if v is not None and v > 0:
                last = v
            out.append(last)
        return out
    tr_map = {r["date"]: num(r["adjclose"]) for r in rd(root, "yahoo_SP500TR.csv")}
    tr = [tr_map.get(d) for d in cal]
    dtm = {r["date"]: num(r["value"]) for r in rd(root, "fred_DTB3.csv") if r["date"] <= CAL_END}
    keys = sorted(set(dtm) | set(cal)); last = None; ff = {}
    for d in keys:
        if dtm.get(d) is not None:
            last = dtm[d]
        ff[d] = last
    dt = [ff[d] for d in cal]
    # 合成 SSO（A1 seq3 逐字，獨立重寫）
    L = [1.0]
    for t in range(1, len(cal)):
        if tr[t] is None or tr[t - 1] is None or L[-1] is None:
            L.append(None); continue
        r = tr[t] / tr[t - 1] - 1
        L.append(L[-1] * (1 + 2 * r - (dt[t - 1] / 100 + 0.0025) / 252 - 0.0089 / 252))
    a7 = {r["date"]: num(r["value"]) for r in rd(root, "fred_DGS7.csv")}
    a10 = {r["date"]: num(r["value"]) for r in rd(root, "fred_DGS10.csv")}
    ym = {}
    for d in sorted(set(a7) & set(a10)):
        if d <= CAL_END and a7[d] is not None and a10[d] is not None:
            ym[d[:7]] = (a7[d] + a10[d]) / 200.0
    gold = {r["month"]: float(r["gold_usd_per_troy_oz"]) for r in rd(root, "worldbank_gold_monthly.csv")}
    cg = [0.0] + [dt[t - 1] / 100 / 252 for t in range(1, len(cal))]
    return {"cal": cal, "me": me, "tr": tr, "L": L, "ym": ym, "gold": gold, "cg": cg,
            "SSO": series("yahoo_SSO.csv"), "IEF": series("yahoo_IEF.csv"), "GLD": series("yahoo_GLD.csv")}


def b0(Dx, m):
    return Dx["me"].get(mprev(m), 0)


def mr(Dx, arr, m):
    return arr[Dx["me"][m]] / arr[b0(Dx, m)] - 1


def ief(Dx, m):
    y0, y1 = Dx["ym"][mprev(m)], Dx["ym"][m]; D, C = dc_num(y0); dy = y1 - y0
    return y0 / 12 - D * dy + 0.5 * C * dy * dy - 0.0015 / 12


def gld(Dx, m):
    return Dx["gold"][m] / Dx["gold"][mprev(m)] - 1 - 0.004 / 12


def cash(Dx, m):
    p = 1.0
    for t in range(b0(Dx, m) + 1, Dx["me"][m] + 1):
        p *= 1 + Dx["cg"][t]
    return p - 1


def portfolio(rows, w, ms, crow=None):
    hold = [x * (1 - 0.0005 * sum(w)) for x in w]; c = (1 - sum(w)) * (1 - 0.0005 * sum(w)); eq = []; aw = []
    for j, r in enumerate(rows):
        hold = [h * (1 + x) for h, x in zip(hold, r)]; c *= 1 + (crow[j] if crow else 0.0)
        V = sum(hold) + c; eq.append(V); aw.append([h / V for h in hold])
        if ms[j].endswith("-12") and j < len(rows) - 1:
            tgt = [x * V for x in w]; tc = (1 - sum(w)) * V
            trn = 0.5 * (sum(abs(a - b) for a, b in zip(tgt, hold)) + abs(tc - c)); V2 = V - trn * 0.0005
            hold = [x * V2 for x in w]; c = (1 - sum(w)) * V2
    return eq, aw


def st(eq):
    p = [1.0] + list(eq); pk = 0; dd = 0
    for x in p:
        pk = max(pk, x); dd = min(dd, (x - pk) / pk)
    c = eq[-1] ** (12 / len(eq)) - 1
    return c, dd, (c / abs(dd) if dd < 0 else float("nan"))


def lab(c, m, cb, mb):
    k1 = c > cb; k2 = (c / abs(m)) >= (cb / abs(mb))
    return "合格" if k1 and k2 else ("另列" if k1 else "不合格")


def crisis(eq, ms, a, b):
    i0, i1 = ms.index(a), ms.index(b); base = eq[i0 - 1]
    seg = [1.0] + [x / base for x in eq[i0:i1 + 1]]; pk = 0; dd = 0
    for x in seg:
        pk = max(pk, x); dd = min(dd, (x - pk) / pk)
    return dd, seg[-1] - 1


def yearly_absmean(a, b, ms):
    ya, yb = {}, {}
    for x, y, m in zip(a, b, ms):
        ya[m[:4]] = ya.get(m[:4], 1.0) * (1 + x); yb[m[:4]] = yb.get(m[:4], 1.0) * (1 + y)
    return sum(abs(ya[k] - yb[k]) * 100 for k in ya) / len(ya)


def real_check():
    S = json.load(open(os.path.join(OUT, "C11L_m_summary.json"), encoding="utf-8"))
    Z = np.load(os.path.join(WORK, "series.npz"))
    Dx = load(ROOT); RES = {}
    MJ = months("1990-01", "2006-06"); MS = months("1990-01", CAL_END[:7])
    # X1
    rows = [[mr(Dx, Dx["L"], m), ief(Dx, m), gld(Dx, m)] for m in MJ]
    eq, aw = portfolio(rows, [0.5, 0.3, 0.2], MJ)
    trJ = [mr(Dx, Dx["tr"], m) for m in MJ]; treq = list(np.cumprod([1 + x for x in trJ]))
    c, m_, r_ = st(eq); cb, mb, rb = st(treq)
    J = S["判定"]
    x1 = {"年化差": abs(c - J["年化"]), "回落差": abs(m_ - J["回落"]), "比值差": abs(r_ - J["比值"]), "基準年化差": abs(cb - J["基準年化"]),
          "基準回落差": abs(mb - J["基準回落"]), "標籤同": lab(c, m_, cb, mb) == S["標籤"]}
    # 1994、2000～02（接續段：2006-07 起真實）
    rowsS = [[mr(Dx, Dx["L"], m), ief(Dx, m), gld(Dx, m)] if m < "2006-07" else [mr(Dx, Dx["SSO"], m), mr(Dx, Dx["IEF"], m), mr(Dx, Dx["GLD"], m)] for m in MS]
    eqS, _ = portfolio(rowsS, [0.5, 0.3, 0.2], MS)
    trS = list(np.cumprod([1 + mr(Dx, Dx["tr"], m) for m in MS]))
    CR = S["必報"]["危機"]
    for k, (a, b) in {"2000～02": ("2000-03", "2002-10"), "1994": ("1994-01", "1994-12")}.items():
        d1, e1 = crisis(eqS, MS, a, b); d2, e2 = crisis(trS, MS, a, b)
        x1[f"{k} 組合回落差"] = abs(d1 - CR[k]["組合"]["窗內最大回落"]); x1[f"{k} 組合窗末差"] = abs(e1 - CR[k]["組合"]["窗末報酬"])
        x1[f"{k} 指數回落差"] = abs(d2 - CR[k]["^SP500TR"]["窗內最大回落"])
    expo = sum(a[0] * 2 for a in aw) / len(aw)
    x1["平均曝險差"] = abs(expo - S["必報"]["同曝險對照"]["平均總股票曝險"])
    eqE, _ = portfolio([[r[0]] for r in rows], [expo / 2], MJ, crow=[cash(Dx, m) for m in MJ])
    ce, me_, _ = st(eqE); E = S["必報"]["同曝險對照"]["結果"]
    x1["同曝險年化差"] = abs(ce - E["年化"]); x1["同曝險回落差"] = abs(me_ - E["回落"])
    MI = months("2002-08", CAL_END[:7])
    x1["IEF 年差絕對值平均差"] = abs(yearly_absmean([ief(Dx, m) for m in MI], [mr(Dx, Dx["IEF"], m) for m in MI], MI)
                                 - S["對帳"]["IEF（判準用）"]["年差絕對值平均（點，含首尾部分年）"])
    MG = months("2004-12", "2025-12")
    x1["黃金 年差絕對值平均差"] = abs(yearly_absmean([gld(Dx, m) for m in MG], [mr(Dx, Dx["GLD"], m) for m in MG], MG)
                                - S["對帳"]["黃金"]["年差絕對值平均（點，含首尾部分年）"])
    x1["不同"] = int(any(v > 1e-6 for k, v in x1.items() if isinstance(v, float)) or not x1["標籤同"])
    RES["X1 判定格全重算"] = x1
    # X2 連乘 ＝ 首尾
    me = Dx["me"]
    x2 = {"合成SSO 判定窗": abs(np.prod(1 + Z["RJ"][:, 0]) - Dx["L"][me["2006-06"]] / Dx["L"][0]),
          "^SP500TR 判定窗": abs(np.prod(1 + Z["trJ"]) - Dx["tr"][me["2006-06"]] / Dx["tr"][0]),
          "黃金（加回費用）判定窗": abs(np.prod(1 + Z["RJ"][:, 2] + 0.004 / 12) - Dx["gold"]["2006-06"] / Dx["gold"]["1989-12"])}
    for j, k in enumerate(("SSO", "IEF", "GLD")):
        x2[f"真實{k} 2007-04～2026-09"] = abs(np.prod(1 + Z["RC"][:, j]) - Dx[k][me["2026-09"]] / Dx[k][me["2007-03"]])
    x2["^SP500TR C11 窗"] = abs(Z["trC"][-1] - Dx["tr"][me["2026-09"]] / Dx["tr"][me["2007-03"]])
    x2 = {k: float(v / 1.0) for k, v in x2.items()}
    x2["相對差最大"] = max(x2.values()); x2["不同"] = int(x2["相對差最大"] > 1e-9)
    RES["X2 月報酬連乘對日頻首尾"] = x2
    # X3 抽樣月手算
    MJl = list(Z["MJ"]); x3 = {}
    for m in ("1990-08", "1994-02", "2001-09"):
        j = MJl.index(m)
        hand = [mr(Dx, Dx["L"], m), ief(Dx, m), gld(Dx, m)]
        x3[m] = {"SSO差": abs(hand[0] - Z["RJ"][j, 0]), "IEF差": abs(hand[1] - Z["RJ"][j, 1]), "金差": abs(hand[2] - Z["RJ"][j, 2])}
    MCl = list(Z["MC"]); j = MCl.index("2008-10")
    x3["2008-10（真實）"] = {k + "差": abs(mr(Dx, Dx[k], "2008-10") - Z["RC"][j, i]) for i, k in enumerate(("SSO", "IEF", "GLD"))}
    # 門檻：IEF 手算用直接定價數值微分的 D、C（與解析式相對差約 1e-7）⇒ ≤ 1e-7；其餘腿 ≤ 1e-9
    mx = max(v for d in x3.values() for k, v in d.items() if k != "IEF差")
    mxi = max(d["IEF差"] for d in x3.values() if "IEF差" in d)
    x3 = {k: {a: float(b) for a, b in d.items()} for k, d in x3.items()}
    x3["最大差（IEF 以外，門檻 1e-9）"] = float(mx); x3["IEF 最大差（數值微分，門檻 1e-7）"] = float(mxi)
    x3["不同"] = int(mx > 1e-9 or mxi > 1e-7)
    RES["X3 抽樣月手算"] = x3
    # X4 判準重算（由主程式路徑）
    c4, m4, r4 = st(list(Z["eqJ"])); cb4, mb4, rb4 = st(list(np.cumprod(1 + Z["trJ"])))
    x4 = {"年化差": abs(c4 - J["年化"]), "回落差": abs(m4 - J["回落"]), "比值差": abs(r4 - J["比值"]), "基準比值差": abs(rb4 - J["基準比值"]),
          "條件一 年化＞基準": bool(c4 > cb4), "條件二 比值≥基準比值": bool(r4 >= rb4), "標籤重算": lab(c4, m4, cb4, mb4), "summary 標籤": S["標籤"]}
    x4["不同"] = int(x4["標籤重算"] != S["標籤"] or max(x4["年化差"], x4["回落差"], x4["比值差"]) > 1e-9)
    RES["X4 判準重算"] = x4
    RES["總結"] = {"不同項數": sum(v["不同"] for v in RES.values() if isinstance(v, dict) and "不同" in v)}
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print(json.dumps(RES, ensure_ascii=False, indent=1, default=float))
    return RES


# ═════════════ fixture（常數報酬假資料，repo 外）═════════════
def fixture():
    import pandas as pd
    fx = os.path.join(WORK, "fixture"); root = os.path.join(fx, "data"); mac = os.path.join(root, "data", "macro"); out = os.path.join(fx, "out")
    os.makedirs(mac, exist_ok=True); os.makedirs(out, exist_ok=True)
    open(os.path.join(root, ".commit"), "w").write("fixture\n")
    days = [d.strftime("%Y-%m-%d") for d in pd.bdate_range("1990-01-02", "2026-09-30")]
    r_i = 0.0004
    def ywrite(name, start, g):
        with open(os.path.join(mac, f"yahoo_{name}.csv"), "w", newline="") as f:
            w = csv.writer(f); w.writerow(["date", "open", "high", "low", "close", "volume", "adjclose"]); v = 100.0
            for d in days:
                if d < start:
                    continue
                o = v; v *= 1 + g; w.writerow([d, o, v, o, v, 0, v])
    ywrite("GSPC", "1990-01-02", r_i); ywrite("SP500TR", "1990-01-02", r_i)
    ywrite("SSO", "2006-06-21", 0.0007); ywrite("IEF", "2002-07-30", 0.0002); ywrite("GLD", "2004-11-18", 0.0003)
    def fwrite(name, val):
        with open(os.path.join(mac, f"fred_{name}.csv"), "w", newline="") as f:
            w = csv.writer(f); w.writerow(["date", "value"])
            for d in ["1989-12-01"] + days:
                w.writerow([d, val])
    fwrite("DTB3", 4.0); fwrite("DGS7", 5.0); fwrite("DGS10", 5.0)
    with open(os.path.join(mac, "worldbank_gold_monthly.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["month", "gold_usd_per_troy_oz"]); v = 400.0
        for m in months("1989-01", "2025-12"):
            w.writerow([m, v]); v *= 1.005
    env = dict(os.environ, C11LM_FIXTURE="1", US_DATA_ROOT_C11LM=root, C11LM_OUT=out, C11LM_WORK=fx)
    subprocess.run([sys.executable, "-m", "backtest.researchUSC11L_m"], check=True, env=env, cwd=os.path.expanduser("~/tw-p17"))
    S = json.load(open(os.path.join(out, "C11L_m_summary.json"), encoding="utf-8")); Z = np.load(os.path.join(fx, "series.npz"))
    MJ = [str(x) for x in Z["MJ"]]
    ndays = {}
    for d in days:
        ndays[d[:7]] = ndays.get(d[:7], 0) + 1
    ndays["1990-01"] -= 1                                   # 首日收盤起
    dsso = 1 + 2 * r_i - (0.04 + 0.0025) / 252 - 0.0089 / 252
    R = {"合成SSO 月報酬": max(abs(Z["RJ"][j, 0] - (dsso ** ndays[m] - 1)) for j, m in enumerate(MJ)),
         "合成IEF 月報酬（殖利率不變 ⇒ y/12 − 費用）": float(np.max(np.abs(Z["RJ"][:, 1] - (0.05 / 12 - 0.0015 / 12)))),
         "黃金月報酬": float(np.max(np.abs(Z["RJ"][:, 2] - (0.005 - 0.004 / 12)))),
         "^SP500TR 月報酬": max(abs(Z["trJ"][j] - ((1 + r_i) ** ndays[m] - 1)) for j, m in enumerate(MJ))}
    rows = [[dsso ** ndays[m] - 1, 0.05 / 12 - 0.0015 / 12, 0.005 - 0.004 / 12] for m in MJ]
    eq, _ = portfolio(rows, [0.5, 0.3, 0.2], MJ)
    R["組合年化（獨立迴圈）"] = abs(st(eq)[0] - S["判定"]["年化"])
    R["組合權益逐月"] = float(np.max(np.abs(np.array(eq) - Z["eqJ"])))
    cash_m = [(1 + 0.04 / 252) ** ndays[m] - 1 for m in MJ]
    R["國庫券月報酬"] = float(np.max(np.abs(np.array(cash_m) - Z["cashJ"])))
    # D、C：解析式（主程式）對 直接定價數值微分；泰勒近似對真實價格變化
    sys.path.insert(0, os.path.expanduser("~/tw-p17"))
    from backtest.researchUSC11L_m import bond_dc                # 只取這一個函式來比對數值微分（被驗對象）
    dcd = []
    for y in (0.02, 0.05, 0.08, 0.12):
        a, b = bond_dc(y); c, d = dc_num(y); dcd.append(max(abs(a - c) / c, abs(b - d) / d))
        dy = 0.001; true = price(y + dy, y) - 1; approx = -a * dy + 0.5 * b * dy * dy
        dcd.append(abs(true - approx) / abs(true) * 1e-3)        # 三階項應 ≲ 千分之幾 ⇒ 乘 1e-3 後 ≤ 1e-5
    R["D、C 相對差（對數值微分）"] = float(max(dcd))
    ok = all(v < (1e-5 if "D、C" in k else 1e-9) for k, v in R.items())
    R["結果"] = "通過" if ok else "不通過"
    print(json.dumps(R, ensure_ascii=False, indent=1))
    return R


if __name__ == "__main__":
    if "--fixture" in sys.argv:
        r = fixture(); sys.exit(0 if r["結果"] == "通過" else 1)
    r = real_check(); sys.exit(0 if r["總結"]["不同項數"] == 0 else 1)
