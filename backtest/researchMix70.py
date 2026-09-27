# -*- coding: utf-8 -*-
"""使用者可承受 −70%：正2 配比描述（裁定 seq233、234、235；⛔ 不判、⛔ 不計 N）。回測線，2026-09-27。

⚠ 看完結果才算的配比、只供選；2008 是合成（非實際 ETF）

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMix70
    查核：~/tw-p16/.venv/bin/python backtest/researchMix70_check.py

口徑（同 PREREG正2現金 本體）：窗首開盤建倉付一次成本；調回日開盤成交、換手 × 0.385%；某檔沒開盤 ⇒ 整筆延後；不留現金；
  年化 ＝ 末值^(245／窗內日數) − 1；回落含 1.0 起點；價格已內含經理費 ⇒ 真實段 ⛔ 不再扣
  0050、0052 早年接主快照（researchTri／researchTri_0052）；00631L、00685L 主快照
① seq233 兩檔：00631L x%＋（0050 或 0052）(100−x)%，x＝0～100 每 10；每年第一個交易日調回
   全段 2015-11-02～2026-08-24：年化、真實最大回落（與谷底日）、2022 谷底（2021-12-30 收盤時 100 萬 ⇒ 2022 年內最低與 12-30）
   2008 合成：壓力窗 2006-09-12～2014-12-31（0052 早年首日起；最大回落 ＝ 2007-10 高點到 2008-11 低點那一段）；
     正2 ＝ 0050 還原日報酬 ×2 每日重設、扣 1.0%／年（逐字標「合成」）；0052 早年實價；另報 2008-01～2009-03 窗
   ⭐「2008 合成（壓力窗最大回落）與 真實最大回落 都不超過 −70%」的最大 x（0050 版、0052 版）
   00631L 對 00685L（2018-01-15～2026-08-24）：純抱各一、⭐ 配比（0050 版最大 x）各一；00685L 流動性（分割前後分開）
② seq234 三檔：0050／00631L／00685L 每 10%、和 100%（66 種）；窗 2018-01-15～2026-08-24；每年第一個交易日調回
   2008 合成：00631L ＝ 0050×2 扣 1.0%／年；00685L ＝ ⚠ 資料庫沒有加權指數早年序列（data/history/market_index 2026-09-01 起）
     ⇒ 用 0050×2 扣 0.3%／年（逐字標）；壓力窗 2006-09-12～2014-12-31
   ⭐ 兩者都 ≥ −70% 的格中年化前 5 名（標正2 合計）；第 1 名 × 調整方式 {每年初、每半年、每季、偏離 ±10 個百分點}
③ seq235：同一第 1 名、一年一次，調整日 ＝ 1～12 月各月第一個交易日（⛔ 不推薦月份）
"""
from __future__ import annotations

import json
import os
from itertools import product

import numpy as np
import pandas as pd

from . import data as D
from . import researchLev2 as L2
from . import researchTri as T
from . import researchTri_0052 as T52

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsMix70")
COST = 0.00385
ANN = 245
FULL = ("2015-11-02", "2026-08-24"); W18 = ("2018-01-15", "2026-08-24")
STRESS = ("2006-09-12", "2014-12-31"); P08 = ("2008-01-02", "2009-03-31")
LIMIT = -0.70
TAG = "看完結果才算的配比、只供選；2008 是合成"
LOGF = os.path.join(OUT, "run.log")


def log(m):
    print(m, flush=True)
    with open(LOGF, "a", encoding="utf-8") as f:
        f.write(m + "\n")


def load():
    G = T.load_all(); cal = list(G["cal"]); pos = G["pos"]; N = len(cal)
    calm = D.load_calendar(); mstr = [str(x.date()) for x in calm]; off = pos[mstr[0]]
    O52, C52, info52 = T52.load_0052(G)
    st = D.load_stock("00685L", "twse", calm).df
    O85 = np.full(N, np.nan); C85 = np.full(N, np.nan)
    O85[off:off + len(mstr)] = st["open"].to_numpy(float); C85[off:off + len(mstr)] = st["close"].to_numpy(float)
    b50 = pd.Series(G["C"]["0050"]).ffill().to_numpy(); o50 = G["O"]["0050"]
    O = {"0050": o50, "0052": O52, "00631L": G["O"]["00631L"], "00685L": O85}
    C = {"0050": b50, "0052": C52, "00631L": pd.Series(G["C"]["00631L"]).ffill().to_numpy(), "00685L": pd.Series(C85).ffill().to_numpy()}
    # 合成正2（0050×2，每日重設；開盤 ＝ 前收 ×（1＋2×隔夜報酬））
    s0 = pos[STRESS[0]]

    def syn(fee):
        Lc = np.full(N, np.nan); Lo = np.full(N, np.nan); Lc[s0 - 2] = 1.0
        for t in range(s0 - 1, N):
            Lo[t] = Lc[t - 1] * (1 + 2 * (o50[t] / b50[t - 1] - 1)) if np.isfinite(o50[t]) else np.nan
            Lc[t] = Lc[t - 1] * (1 + 2 * (b50[t] / b50[t - 1] - 1) - fee / 245)
        return Lo, Lc
    SO = dict(O); SC = dict(C)
    SO["00631L"], SC["00631L"] = syn(0.010)
    SO["00685L"], SC["00685L"] = syn(0.003)
    return dict(cal=cal, pos=pos, O=O, C=C, SO=SO, SC=SC, info52=info52, st85=st, mstr=mstr)


def reb_days(cal, i0, i1, rule, month=1):
    """rule：Y（每年 month 月第一個交易日）、H（1、7 月）、Q（1、4、7、10 月）；窗首當天不算。回傳 bool（窗內相對）。"""
    n = i1 - i0 + 1; m = np.zeros(n, bool)
    months = {"Y": {month}, "H": {1, 7}, "Q": {1, 4, 7, 10}}[rule]
    for k in range(1, n):
        a, b = cal[i0 + k - 1], cal[i0 + k]
        if a[:7] != b[:7] and int(b[5:7]) in months:
            m[k] = True
    return m


def sim(assets, w, i0, i1, O, C, cal, rule="Y", month=1, band=None):
    """單位制；rule ∈ Y／H／Q，或 band＝0.10（t−1 收盤權重偏離目標超過 band ⇒ t 開盤調回）。"""
    w = np.asarray(w, float); k = len(assets); n = i1 - i0 + 1
    R = reb_days(cal, i0, i1, rule, month) if band is None else np.zeros(n, bool)
    u = np.zeros(k); cash = 1.0; eq = np.empty(n); pend = True; acts = []; crel = 0.0; delay = 0
    for j in range(n):
        t = i0 + j
        o = np.array([O[a][t] for a in assets]); c = np.array([C[a][t] for a in assets])
        if j > 0:
            if R[j]:
                pend = True
            if band is not None:
                cp = np.array([C[a][t - 1] for a in assets]); v = u * cp; V = v.sum() + cash
                if V > 0 and np.max(np.abs(v / V - w)) > band + 1e-12:
                    pend = True
        if pend:
            need = (u > 0) | (w > 0)
            if np.all(np.isfinite(o[need])):
                hold = np.where(u > 0, u * np.where(np.isfinite(o), o, 0), 0.0); V = hold.sum() + cash
                tr = 0.5 * (np.abs(w * V - hold).sum() + abs((1 - w.sum()) * V - cash))
                cc = tr * COST; V2 = V - cc
                with np.errstate(invalid="ignore", divide="ignore"):
                    u = np.where(w > 0, w * V2 / o, 0.0)
                cash = (1 - w.sum()) * V2; pend = False
                if j > 0 and tr > 0:
                    acts.append(cal[t]); crel += cc / V
            else:
                delay += 1
        eq[j] = float(np.where(u > 0, u * c, 0.0).sum() + cash)
    return eq, acts, crel, delay


def stats(eq, cal, i0, acts=None, crel=0.0):
    c, m = L2.perf(eq)
    p = np.r_[1.0, eq]; pk = np.maximum.accumulate(p); ddv = (p - pk) / pk; it = int(np.argmin(ddv))
    out = {"年化": c, "最大回落": m, "谷底日": cal[i0 + it - 1] if it > 0 else "起點"}
    if acts is not None:
        yrs = len(eq) / ANN
        out.update({"每年動手": len(acts) / yrs, "成本／年（占市值）": crel / yrs})
    return out


def y2022(eq, cal, i0, pos):
    """100 萬在 2022-01-03 那天的市值起算，2022 年內谷底與 12-30。"""
    a, b = pos["2022-01-03"] - i0, pos["2022-12-30"] - i0
    base = eq[a - 1] if a > 0 else 1.0
    seg = eq[a:b + 1] / base
    return float(min(1.0, seg.min()) * 1e6), float(seg[-1] * 1e6)


def main():
    os.makedirs(OUT, exist_ok=True); open(LOGF, "w").close()
    log(f"===== researchMix70 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜{TAG}｜⛔ 不判、不計 N =====")
    X = load(); cal, pos = X["cal"], X["pos"]
    f0, f1 = pos[FULL[0]], pos[FULL[1]]; g0, g1 = pos[W18[0]], pos[W18[1]]; s0, s1 = pos[STRESS[0]], pos[STRESS[1]]
    q0, q1 = pos[P08[0]], pos[P08[1]]
    S = {"標": TAG}
    # 閘：年度調回 ＝ researchLev2.engine（PREREG正2現金 本體引擎）
    e1, _, _, _ = sim(("0050", "00631L"), (0.5, 0.5), f0, f1, X["O"], X["C"], cal)
    n = f1 - f0 + 1
    e2 = L2.engine(("0050", "00631L"), np.tile([0.5, 0.5], (n, 1)), reb_days(cal, f0, f1, "Y"), f0, X["O"], X["C"])["eq"]
    S["閘_對researchLev2.engine最大相對差"] = float(np.max(np.abs(e1 / e2 - 1)))
    log(f"[閘] 對 L2.engine {S['閘_對researchLev2.engine最大相對差']:.1e}")
    if S["閘_對researchLev2.engine最大相對差"] > 1e-12:
        raise SystemExit("⛔ 閘不過")

    # ① 兩檔
    rows = []
    for etf, x in product(("0050", "0052"), range(0, 11)):
        w = (x / 10, 1 - x / 10); a = ("00631L", etf)
        eq, acts, crel, _ = sim(a, w, f0, f1, X["O"], X["C"], cal)
        r = {"ETF": etf, "正2%": x * 10, **stats(eq, cal, f0, acts, crel)}
        r["2022谷底（100萬）"], r["2022-12-30（100萬）"] = y2022(eq, cal, f0, pos)
        es, _, _, dl = sim(a, w, s0, s1, X["SO"], X["SC"], cal)
        st = stats(es, cal, s0); r["2008合成最大回落（2006-09～2014）"] = st["最大回落"]; r["2008合成谷底日"] = st["谷底日"]
        r["2008合成年化（2006-09～2014）"] = st["年化"]; r["壓力窗R8延後"] = dl
        e8, _, _, _ = sim(a, w, q0, q1, X["SO"], X["SC"], cal)
        p8 = np.r_[1.0, e8]; r["2008-01～2009-03 最大回落"] = float(((p8 - np.maximum.accumulate(p8)) / np.maximum.accumulate(p8)).min())
        r["兩者都不超過−70%"] = r["最大回落"] >= LIMIT and r["2008合成最大回落（2006-09～2014）"] >= LIMIT
        rows.append(r)
    two = pd.DataFrame(rows); two.to_csv(os.path.join(OUT, "mix2_grid.csv"), index=False, encoding="utf-8")
    best2 = {e: int(two[(two["ETF"] == e) & two["兩者都不超過−70%"]]["正2%"].max()) for e in ("0050", "0052")}
    S["①最大正2比例"] = best2
    log("[① 兩檔]\n" + two.to_string() + f"\n⭐ 最大 x：{best2}")

    # ①b 00631L 對 00685L（2018-01-15 起）
    rows = []
    for lev in ("00631L", "00685L"):
        for nm, a, w in ((f"純抱 {lev}", (lev,), (1.0,)), (f"{lev} {best2['0050']}%＋0050 {100 - best2['0050']}%", (lev, "0050"), (best2["0050"] / 100, 1 - best2["0050"] / 100))):
            eq, acts, crel, dl = sim(a, w, g0, g1, X["O"], X["C"], cal)
            r = {"對象": nm, **stats(eq, cal, g0, acts, crel), "R8延後": dl}
            r["2022谷底（100萬）"], r["2022-12-30（100萬）"] = y2022(eq, cal, g0, pos)
            rows.append(r)
    lv = pd.DataFrame(rows); lv.to_csv(os.path.join(OUT, "lev631_vs_685.csv"), index=False, encoding="utf-8")
    log("[①b 00631L 對 00685L]\n" + lv.to_string())
    # 00685L 流動性
    liq = []
    for sid in ("00685L", "00631L"):
        r = pd.read_csv(os.path.join(D.DATA, "stocks", f"{sid}.csv"), dtype={"date": str})
        r["amount"] = pd.to_numeric(r["amount"], errors="coerce"); r["close"] = pd.to_numeric(r["close"], errors="coerce")
        for nm, (a, b) in (("分割前 2018-01-15～2026-06-30", ("2018-01-15", "2026-06-30")), ("分割後 2026-07-07～2026-09-24（資料末日）", ("2026-07-07", "2026-09-24"))):
            z = r[(r["date"] >= a) & (r["date"] <= b)]
            calw = [d for d in X["mstr"] if a <= d <= b]
            liq.append({"標的": sid, "期間": nm, "交易日": len(calw), "日均成交金額（元）": float(z["amount"].fillna(0).sum() / len(calw)),
                        "日成交金額中位（元）": float(pd.Series([z.set_index("date")["amount"].get(d, 0.0) for d in calw]).fillna(0).median()),
                        "無成交日數": int(len(calw) - z["close"].notna().sum())})
    lq = pd.DataFrame(liq); lq.to_csv(os.path.join(OUT, "liquidity.csv"), index=False, encoding="utf-8")
    log("[流動性]\n" + lq.to_string())

    # ② 三檔 66 種
    rows = []
    A3 = ("0050", "00631L", "00685L")
    for e, l1 in ((e, l1) for e in range(11) for l1 in range(11 - e)):
        l2 = 10 - e - l1; w = (e / 10, l1 / 10, l2 / 10)
        eq, acts, crel, dl = sim(A3, w, g0, g1, X["O"], X["C"], cal)
        r = {"0050%": e * 10, "00631L%": l1 * 10, "00685L%": l2 * 10, "正2合計%": (l1 + l2) * 10, **stats(eq, cal, g0, acts, crel), "R8延後": dl}
        r["2022谷底（100萬）"], r["2022-12-30（100萬）"] = y2022(eq, cal, g0, pos)
        es, _, _, _ = sim(A3, w, s0, s1, X["SO"], X["SC"], cal)
        st = stats(es, cal, s0); r["2008合成最大回落（2006-09～2014）"] = st["最大回落"]
        r["兩者都不超過−70%"] = r["最大回落"] >= LIMIT and st["最大回落"] >= LIMIT
        rows.append(r)
    three = pd.DataFrame(rows); three.to_csv(os.path.join(OUT, "mix3_grid.csv"), index=False, encoding="utf-8")
    ok = three[three["兩者都不超過−70%"]].copy(); ok["_o"] = range(len(ok))
    top5 = ok.sort_values(["年化", "_o"], ascending=[False, True]).head(5).drop(columns=["_o"])
    top5.to_csv(os.path.join(OUT, "mix3_top5.csv"), index=False, encoding="utf-8")
    log(f"[② 三檔] 合格 {len(ok)}／66\n" + top5.to_string())
    b = top5.iloc[0]; wb = (b["0050%"] / 100, b["00631L%"] / 100, b["00685L%"] / 100)
    S["②第1名"] = {k: b[k] for k in ("0050%", "00631L%", "00685L%", "正2合計%", "年化", "最大回落", "2008合成最大回落（2006-09～2014）")}
    # 調整方式
    rows = []
    for nm, kw in (("每年初", dict(rule="Y", month=1)), ("每半年（1、7 月）", dict(rule="H")), ("每季（1、4、7、10 月）", dict(rule="Q")),
                   ("偏離目標 ±10 個百分點才調", dict(band=0.10))):
        eq, acts, crel, dl = sim(A3, wb, g0, g1, X["O"], X["C"], cal, **kw)
        rows.append({"調整方式": nm, **stats(eq, cal, g0, acts, crel), "R8延後": dl})
    fr = pd.DataFrame(rows); fr.to_csv(os.path.join(OUT, "rebalance_freq.csv"), index=False, encoding="utf-8")
    log("[② 調整方式]\n" + fr.to_string())
    # ③ 12 個月
    rows = []
    for mth in range(1, 13):
        eq, acts, crel, dl = sim(A3, wb, g0, g1, X["O"], X["C"], cal, rule="Y", month=mth)
        rows.append({"調整月": mth, **stats(eq, cal, g0, acts, crel), "R8延後": dl})
    mo = pd.DataFrame(rows); mo.to_csv(os.path.join(OUT, "rebalance_month.csv"), index=False, encoding="utf-8")
    S["③12個月"] = {"年化最好－最差（點）": float((mo["年化"].max() - mo["年化"].min()) * 100),
                  "回落最淺－最深（點）": float((mo["最大回落"].max() - mo["最大回落"].min()) * 100)}
    log("[③ 12 個月]\n" + mo.to_string() + f"\n{S['③12個月']}")
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    log("[完]")


if __name__ == "__main__":
    main()
