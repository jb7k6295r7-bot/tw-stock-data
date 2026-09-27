# -*- coding: utf-8 -*-
"""PREREG跌深加碼（台股策略線登錄 seq2 sha 0f64d57a6e92be1f；裁定 seq229、230、231；N_組合 ＋1）。回測線，2026-09-27。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchDip pre     # ⛔ 不讀報酬
    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchDip body    # 讀法 D1～D4 見 body 段開頭
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchDip_check.py

pre 段：格數、訊號（0050 距 250 日最高收盤）各段的觸發頻率、各窗起點的訊號狀態、會改動格或判定的讀法 ⇒ 停下回報
  ⛔ 不算任何組合、任何標的的報酬／回落（只看 0050 距 250 日高這一個訊號的狀態與次數）
沿用：0050 序列 ＝ researchTri.load_all（早年 3edc0e2206 接主快照 edc6f，有效 K 棒上算、日曆對齊、無 K 棒日沿用前值）
      0052 早年 ＝ researchTri_0052.load_0052（2006-09-12 起，除息已對官方）；00685L ＝ 主快照（2017-03-30 起）
"""
from __future__ import annotations

import argparse
import json
import os
from itertools import product

import numpy as np
import pandas as pd

from . import researchTri as T

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsDip")
LOGF = "pre_run.log"
EXP = ("2015-11-02", "2021-12-30"); CONF = ("2022-01-03", "2026-08-24"); L85 = ("2018-01-15", "2021-12-30")
STRESS = ("2006-09-12", "2014-12-31")
LADDER = {"L1": (0.10, 0.20, 0.30), "L2": (0.15, 0.30, 0.45)}
RS = (0.2, 0.3, 0.5)


def log(m):
    print(m, flush=True)
    with open(os.path.join(OUT, LOGF), "a", encoding="utf-8") as f:
        f.write(m + "\n")


def grid():
    main = [(h, a) for h in ("0050", "0052", "00631L") for a in ((h, "00631L") if h != "00631L" else ("00631L",))]
    l85 = [("00685L", a) for a in ("00685L", "00631L")]
    cells = [dict(窗="主窗", H=h, A=a, r=r, 梯=L, 回補=R) for (h, a), r, L, R in product(main, RS, LADDER, ("R1", "R2"))]
    cells += [dict(窗="00685L窗", H=h, A=a, r=r, 梯=L, 回補=R) for (h, a), r, L, R in product(l85, RS, LADDER, ("R1", "R2"))]
    ctrl = [dict(窗=w, H=h, 型="C0") for w, hs in (("主窗", ("0050", "0052", "00631L")), ("00685L窗", ("00685L",))) for h in hs]
    ctrl += [dict(窗=w, H=h, 型="C1", r=r) for w, hs in (("主窗", ("0050", "0052", "00631L")), ("00685L窗", ("00685L",))) for h in hs for r in RS]
    return pd.DataFrame(cells), pd.DataFrame(ctrl)


def dd_series(G):
    """0050 還原收盤 ÷ 含當根 250 根最高收盤 − 1（有效 K 棒上算、日曆對齊、無 K 棒日沿用前值）；另回「當根創 250 日新高」。"""
    c0 = G["C"]["0050"]; bars = np.flatnonzero(np.isfinite(c0)); c = c0[bars]
    hi = np.full(len(c), np.nan); hi[249:] = np.lib.stride_tricks.sliding_window_view(c, 250).max(axis=1)
    dd = c / hi - 1
    newhi = np.zeros(len(c), bool); newhi[249:] = c[249:] >= hi[249:]          # 收盤 ＝ 250 日最高（含當根）
    N = len(G["cal"]); D_ = np.full(N, np.nan); NH = np.zeros(N, bool)
    D_[bars] = dd; NH[bars] = newhi
    return pd.Series(D_).ffill().to_numpy(), NH, int(bars[249])


def pre(a):
    global LOGF
    os.makedirs(OUT, exist_ok=True); LOGF = "pre_run.log"; open(os.path.join(OUT, LOGF), "w").close()
    log(f"===== researchDip pre {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）⛔ 不讀報酬 =====")
    G = T.load_all(); cal = G["cal"]; pos = G["pos"]
    from . import rerun17 as RR
    from . import data as D
    calm = D.load_calendar(); w0, w1 = RR.win_bounds(calm)
    bw = RR.bench_row(calm, RR.load_bench(calm), w0, w1 + 1)
    anc = repr(bw["cagr"]) == repr(RR.ANCHOR[0]) and repr(bw["mdd"]) == repr(RR.ANCHOR[1])
    cells, ctrl = grid()
    cells.to_csv(os.path.join(OUT, "pre_grid.csv"), index=False, encoding="utf-8"); ctrl.to_csv(os.path.join(OUT, "pre_controls.csv"), index=False, encoding="utf-8")
    dd, NH, f250 = dd_series(G)
    # 標的資料
    from . import researchTri_0052 as T52
    O52, C52, info52 = T52.load_0052(G)
    st85 = D.load_stock("00685L", "twse", calm)
    first = {"0050": str(cal[int(np.flatnonzero(np.isfinite(G["C"]["0050"]))[0])]), "0052（含早年）": info52["0052 早年首日"],
             "00631L（主快照）": str(cal[int(np.flatnonzero(np.isfinite(G["C"]["00631L"]))[0])]),
             "00685L（主快照）": str(st85.df.index[st85.df["traded"]][0].date())}
    segs = {"壓力 2006-09-12～2014-12-31": STRESS, "探索 2015-11-02～2021-12-30": EXP, "00685L 探索 2018-01-15～2021-12-30": L85, "確認 2022-01-03～2026-08-24": CONF}
    rows = []
    for nm, (s, e) in segs.items():
        i0, i1 = pos[s], pos[e]
        r = {"段": nm, "交易日": i1 - i0 + 1, "窗首前一日 dd（t−1）": round(float(dd[i0 - 1]), 4),
             "創 250 日新高日數": int(NH[i0:i1 + 1].sum())}
        yrs = pd.Series(NH[i0:i1 + 1], index=pd.to_datetime(cal[i0:i1 + 1])).groupby(lambda x: x.year).sum()
        r["每年新高日數（最少～最多）"] = f"{int(yrs.min())}～{int(yrs.max())}"
        for x in sorted(set(LADDER["L1"] + LADDER["L2"])):
            b = dd[i0 - 1:i1 + 1] <= -x
            r[f"跌破 −{int(x * 100)}% 次數（由上往下穿）"] = int(np.sum(b[1:] & ~b[:-1]))
            r[f"≤ −{int(x * 100)}% 日數"] = int(b[1:].sum())
        # 年初第一個交易日前一日 dd ≤ −10% 的年數（R2 年初回補時仍在跌勢中）
        yf = [i for i in range(i0, i1 + 1) if i == i0 or cal[i][:4] != cal[i - 1][:4]]
        r["年初前一日 dd ≤ −10% 的年（R2 重新上膛問題）"] = ",".join(cal[i][:4] + f"({dd[i - 1]:.2f})" for i in yf[1:] if dd[i - 1] <= -0.10)
        rows.append(r)
    sig = pd.DataFrame(rows); sig.to_csv(os.path.join(OUT, "pre_signal.csv"), index=False, encoding="utf-8")
    S = {"登錄": "PREREG跌深加碼 seq2 sha 0f64d57a6e92be1f（裁定 seq229、230、231）", "閘_0050主窗錨逐位元": anc,
         "格數": {"主窗": int((cells["窗"] == "主窗").sum()), "00685L窗": int((cells["窗"] == "00685L窗").sum()),
                "C0": ctrl[ctrl["型"] == "C0"].groupby("窗").size().to_dict(), "C1": ctrl[ctrl["型"] == "C1"].groupby("窗").size().to_dict(),
                "判定": "1 格（挑法乙：主窗 60 格探索段年化最高）", "N_組合": "+1"},
         "250日高第一個可算日": str(cal[f250]), "標的首日": first, "0052 早年": {k: info52[k] for k in ("早年有效收盤列", "早年無成交日（列在、收盤空）")}}
    json.dump(S, open(os.path.join(OUT, "pre_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[閘] 0050 錨 {anc}｜[格] {S['格數']}｜250 日高首可算 {S['250日高第一個可算日']}｜首日 {first}")
    log("[訊號]\n" + sig.T.to_string())
    log("[完] pre（⛔ 未讀報酬）")


# ═══════════════════════════════════════════════════════════════════════════
# 本體（body）——讀法 D1～D4 由回測線建議、協調者轉達定案（登錄沒寫死）；E1～E8 照 PRE_REPORT §四
# ═══════════════════════════════════════════════════════════════════════════
"""
  D1 (b) R1 只在「上次調回之後至少加碼過一次」的第一個 250 日新高（t−1 收盤）後調回；沒加碼過就不動
       理由：回補的意思是把加碼用掉的現金補回來；字面「每個新高日都調回」會讓 R1 在多頭期一年動手近 50 次
  D2 (b) 各階只在 0050 創 250 日新高（跌勢結束）時重新上膛；R2 的年初只把現金補回 r
       理由：守住登錄「同一段跌勢只觸發一次」；否則 2023 年初（−25%）會在同一段跌勢再買一輪
  D3 (b) 窗首前一日已跌破的階視為這段跌勢已觸發（等創新高才上膛）；敏感度 (a)「窗首一律上膛」另報、只描述
       理由：上膛狀態本來就該從 0050 歷史接續；窗首不是一段跌勢的開始
  D4 (a) 每階投入 ＝ 上次調回（窗首／回補／年初）後那筆現金 ÷ 3（固定金額）；第三階投入剩下的全部現金
       理由：字面「起始現金 r 的 1/3」
  其餘：t−1 收盤判、t 開盤成交；換手 ＝ ½Σ|目標−現有|（含現金）× 0.385%；加碼的成本從現金出；同一天跨過多階 ⇒ 同一筆買；
        需要的標的沒開盤 ⇒ 整筆延後（加碼則次日依 t−1 訊號重判）；「動手」＝ 實際成交且換手 ＞ 0 的日子（建倉不算）
"""
from . import researchLev2 as L2          # noqa: E402
from . import researchTri_0052 as T52     # noqa: E402

COST = 0.00385
CASH_G = 1.01 ** (1 / 245) - 1
P08 = ("2008-01-02", "2009-03-31")
SEED_NULL = 20260930; NREP = 1000


class Mkt:
    """spliced 日曆上的 O／C（C 已 ffill）。LEV 在壓力段換合成。"""
    def __init__(self, G, O52, C52, O85, C85, syn=None):
        b50 = pd.Series(G["C"]["0050"]).ffill().to_numpy()
        self.O = {"0050": G["O"]["0050"], "0052": O52, "00631L": G["O"]["00631L"], "00685L": O85}
        self.C = {"0050": b50, "0052": C52, "00631L": pd.Series(G["C"]["00631L"]).ffill().to_numpy(), "00685L": C85}
        if syn is not None:
            self.O["00631L"], self.C["00631L"] = syn


def sim(M, H, A, r, ladder, R, i0, i1, dd, NH, cal, d3="b", cash_g=0.0, rand_days=None, log_actions=False):
    """跌深加碼一格（或 C0：r＝0、ladder None；C1：ladder None、R＝R2）。回傳 dict。"""
    th = LADDER[ladder] if ladder else ()
    assets = [H] if A == H else [H, A]
    u = {a: 0.0 for a in assets}; cash = 1.0
    armed = [True] * len(th)
    creset = 0.0; bought = False; pend_rb = False; init_done = False
    n = i1 - i0 + 1; eq = np.empty(n); cashw = np.empty(n)
    acts = []; cst = 0.0; cst_rel = 0.0; nbuy_rungs = 0
    rset = set(rand_days) if rand_days is not None else None
    for k in range(n):
        t = i0 + k
        O = {a: M.O[a][t] for a in assets}; C = {a: M.C[a][t] for a in assets}
        todo = []                                   # (類, 內容)
        if not init_done:
            todo.append(("建倉", None))
        else:
            if NH[t - 1]:
                armed = [True] * len(th)
            yr_first = cal[t][:4] != cal[t - 1][:4]
            if (R == "R1" and NH[t - 1] and bought) or (R == "R2" and yr_first) or pend_rb:
                todo.append(("回補" if R == "R1" else "年初調回", None))
        # 加碼：訊號（或隨機日）
        fire = []
        if th:
            if rset is None:
                fire = [j for j, x in enumerate(th) if armed[j] and dd[t - 1] <= -x] if (init_done or d3 == "a") else []
            elif k in rset:
                fire = ["rand"]
        need = set()
        if todo:
            need |= {H} | {a for a in assets if u[a] > 0}
        if fire:
            need.add(A)
        if (todo or fire) and not all(np.isfinite(O[a]) for a in need):
            if todo and todo[0][0] != "建倉":
                pend_rb = True                       # R8：整筆延後
            todo, fire = [], []
        if todo and todo[0][0] == "建倉":
            init_done = True
            if d3 == "b":
                armed = [not (dd[t - 1] <= -x) for x in th]   # D3 (b)：窗首前已跌破的階視為已觸發
        # 只加碼、H 當天沒開盤（例：0052 早年無成交）⇒ H 用前一日收盤估市值（只影響成本占市值的分母）
        V = sum(u[a] * (O[a] if np.isfinite(O[a]) else M.C[a][t - 1]) for a in assets if u[a] > 0) + cash if (todo or fire) else None
        if todo:
            typ = todo[0][0]
            tgtH = (1.0 - r) * V
            hold = {a: u[a] * O[a] if u[a] > 0 else 0.0 for a in assets}
            tg = {a: 0.0 for a in assets}; tg[H] = tgtH
            tr = 0.5 * (sum(abs(tg[a] - hold[a]) for a in assets) + abs(r * V - cash))
            c_ = tr * COST; V2 = V - c_
            u = {a: 0.0 for a in assets}; u[H] = (1.0 - r) * V2 / O[H]; cash = r * V2
            creset = cash; bought = False; pend_rb = False
            if typ != "建倉" and tr > 0:
                acts.append({"日": cal[t], "類": typ, "內容": f"調回 {H} {int(round((1 - r) * 100))}%＋現金 {int(round(r * 100))}%" + (f"（{A} 全賣）" if A != H else ""),
                             "換手占市值": tr / V, "成本占市值": c_ / V})
                cst += c_; cst_rel += c_ / V
            V = V2
        if fire:
            if rset is None:
                last = any(j == len(th) - 1 for j in fire)
                amt = cash if last else min(cash, creset / 3 * len(fire))
                for j in fire:
                    armed[j] = False
                nbuy_rungs += len(fire)
            else:
                amt = min(cash, creset / 3); nbuy_rungs += 1
            amt = min(amt, cash / (1 + COST))
            if amt > 0:
                c_ = amt * COST
                u[A] += amt / O[A]; cash -= amt + c_
                cst += c_; cst_rel += c_ / V
                bought = True
                lvl = "、".join(f"−{int(th[j] * 100)}%" for j in fire) if rset is None else "隨機日"
                acts.append({"日": cal[t], "類": "加碼", "內容": f"0050 距一年高 {dd[t - 1] * 100:.1f}%（觸發 {lvl}）⇒ 投入 {'剩下全部' if (rset is None and last) else f'{len(fire)}/3'} 現金買 {A}",
                             "換手占市值": amt / V, "成本占市值": c_ / V})
        if k > 0:
            cash *= 1.0 + cash_g
        v = sum(u[a] * C[a] for a in assets if u[a] > 0) + cash
        eq[k] = v; cashw[k] = cash / v
    yrs = n / 245
    days = sorted(set(a["日"] for a in acts))
    idx = [cal.index(d) - i0 for d in days] if days else []
    gaps = np.diff([0] + idx + [n - 1]) if n else [n]
    byyear = pd.Series([d[:4] for d in days]).value_counts() if days else pd.Series(dtype=int)
    typc = pd.Series([a["類"] for a in acts]).value_counts() if acts else pd.Series(dtype=int)
    c, m = L2.perf(eq)
    return {"eq": eq, "acts": acts, "年化": c, "回落": m, "比值": L2.ratio(c, m),
            "加碼／年": float(typc.get("加碼", 0)) / yrs, "回補／年": float(typc.get("回補", 0)) / yrs, "年初調回／年": float(typc.get("年初調回", 0)) / yrs,
            "動手日／年": len(days) / yrs, "最長不用動（交易日）": int(max(gaps)), "最密集一年動手日": int(byyear.max()) if len(byyear) else 0,
            "成本／年（占市值）": cst_rel / yrs, "現金平均占比": float(np.mean(cashw)), "加碼階數": nbuy_rungs}


def cells_all():
    cells, ctrl = grid()
    out = []
    for _, c in cells.iterrows():
        out.append(dict(窗=c["窗"], 型="格", H=c["H"], A=c["A"], r=c["r"], 梯=c["梯"], 回補=c["回補"]))
    for _, c in ctrl.iterrows():
        if c["型"] == "C0":
            out.append(dict(窗=c["窗"], 型="C0", H=c["H"], A=c["H"], r=0.0, 梯=None, 回補="—"))
        else:
            out.append(dict(窗=c["窗"], 型="C1", H=c["H"], A=c["H"], r=c["r"], 梯=None, 回補="R2"))
    return pd.DataFrame(out)


def run_cell(M, c, i0, i1, dd, NH, cal, **kw):
    return sim(M, c["H"], c["A"], float(c["r"]), c["梯"] if isinstance(c["梯"], str) else None, c["回補"], i0, i1, dd, NH, cal, **kw)


def cname(c):
    if c["型"] == "C0":
        return f"C0 純抱 {c['H']}"
    if c["型"] == "C1":
        return f"C1 {c['H']} {int(c['r'] * 100)}%現金、年初調回、不加碼"
    return f"{c['H']}｜留 {int(c['r'] * 100)}%｜{c['梯']}｜買 {c['A']}｜{c['回補']}"


def body(a):
    global LOGF
    os.makedirs(OUT, exist_ok=True); LOGF = "body_run.log"; open(os.path.join(OUT, LOGF), "w").close()
    log(f"===== researchDip body {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜D1～D4 ＝ b／b／b／a =====")
    G = T.load_all(); cal = list(G["cal"]); pos = G["pos"]; N = len(cal)
    from . import data as D
    calm = D.load_calendar(); mstr = [str(x.date()) for x in calm]; off = pos[mstr[0]]
    O52, C52, _ = T52.load_0052(G)
    st = D.load_stock("00685L", "twse", calm).df
    O85 = np.full(N, np.nan); C85 = np.full(N, np.nan)
    O85[off:off + len(mstr)] = st["open"].to_numpy(float); C85[off:off + len(mstr)] = st["close"].to_numpy(float)
    C85 = pd.Series(C85).ffill().to_numpy()
    M = Mkt(G, O52, C52, O85, C85)
    dd, NH, _ = dd_series(G)
    b50 = M.C["0050"]
    SEG = {("主", "探索"): (pos[EXP[0]], pos[EXP[1]]), ("主", "確認"): (pos[CONF[0]], pos[CONF[1]]),
           ("L", "探索"): (pos[L85[0]], pos[L85[1]]), ("L", "確認"): (pos[CONF[0]], pos[CONF[1]])}

    def bperf(i0, i1):
        seg = b50[i0:i1 + 1]; c, m = L2.R13.window_stats(seg / seg[0], 0, len(seg), 0, len(seg)); return float(c), float(m)
    B = {k: bperf(*v) for k, v in SEG.items()}
    S = {"讀法": {"D1": "b", "D2": "b", "D3": "b（敏感度 a 另報）", "D4": "a"}, "0050同窗": {f"{k[0]}{k[1]}": v for k, v in B.items()}}
    CL = cells_all()
    rows = []; RUN = {}
    for _, c in CL.iterrows():
        wins = [("主" if c["窗"] == "主窗" else "L")]
        if c["窗"] == "主窗":
            wins.append("L")                       # E1：主窗 72 格也在 00685L 窗重跑（刪減用，描述）
        for w in wins:
            for sg in ("探索", "確認"):
                i0, i1 = SEG[(w, sg)]
                r = run_cell(M, c, i0, i1, dd, NH, cal)
                RUN[(c.name, w, sg)] = r
                c50, m50 = B[(w, sg)]
                rows.append({"列": c.name, "窗組": c["窗"], "跑在": "主窗" if w == "主" else "00685L窗", "段": sg, "型": c["型"], "名稱": cname(c),
                             "H": c["H"], "A": c["A"], "r": c["r"], "梯": c["梯"], "回補": c["回補"],
                             **{k: v for k, v in r.items() if k not in ("eq", "acts")},
                             "對0050（描述）": L2.label(r["年化"], r["回落"], c50, m50)})
    df = pd.DataFrame(rows); df.to_csv(os.path.join(OUT, "body_cells.csv"), index=False, encoding="utf-8")
    log(f"[格] {len(df)} 列")

    def sel(pool, key):
        p = pool.copy(); p["_o"] = range(len(p))
        return p.sort_values([key, "動手日／年", "_o"], ascending=[False, True, True]).iloc[0]
    ex = df[(df["跑在"] == "主窗") & (df["窗組"] == "主窗") & (df["型"] == "格") & (df["段"] == "探索")].reset_index(drop=True)
    pick = sel(ex, "年化"); picka = sel(ex, "比值")
    ex.sort_values(["年化", "動手日／年"], ascending=[False, True]).head(10).to_csv(os.path.join(OUT, "body_top10_explore.csv"), index=False, encoding="utf-8")

    def conf_row(lst, win="主窗"):
        return df[(df["列"] == lst) & (df["跑在"] == win) & (df["段"] == "確認")].iloc[0]
    cp = conf_row(pick["列"])
    c0 = df[(df["型"] == "C0") & (df["H"] == pick["H"]) & (df["跑在"] == "主窗") & (df["窗組"] == "主窗")]
    c0e, c0c = c0[c0["段"] == "探索"].iloc[0], c0[c0["段"] == "確認"].iloc[0]
    c1 = df[(df["型"] == "C1") & (df["H"] == pick["H"]) & (df["r"] == pick["r"]) & (df["跑在"] == "主窗") & (df["窗組"] == "主窗")]
    c1c = c1[c1["段"] == "確認"].iloc[0]
    S["挑法乙"] = {"格": pick["名稱"], "探索": {k: pick[k] for k in ("年化", "回落", "比值", "動手日／年")},
                 "確認": {k: cp[k] for k in ("年化", "回落", "比值", "加碼／年", "回補／年", "年初調回／年", "動手日／年", "最長不用動（交易日）",
                                            "最密集一年動手日", "成本／年（占市值）", "現金平均占比", "加碼階數", "對0050（描述）")},
                 "C0同H確認": {"年化": c0c["年化"], "回落": c0c["回落"]}, "C0同H探索": {"年化": c0e["年化"]},
                 "C1同H同r確認": {"年化": c1c["年化"], "回落": c1c["回落"]},
                 "主問": "高賣低買有加到報酬" if cp["年化"] > c0c["年化"] else "高賣低買沒有加到報酬",
                 "對0050年化差": cp["年化"] - B[("主", "確認")][0]}
    cpa = conf_row(picka["列"])
    S["挑法甲（並列）"] = {"格": picka["名稱"], "探索": {k: picka[k] for k in ("年化", "回落", "比值")}, "確認": {k: cpa[k] for k in ("年化", "回落", "比值", "動手日／年", "對0050（描述）")}}
    log(f"[挑法乙] {S['挑法乙']}\n[挑法甲] {S['挑法甲（並列）']}")
    # 挑中那組：確認段逐筆動作
    pc = CL.loc[pick["列"]]
    acts = pd.DataFrame(RUN[(pick["列"], "主", "確認")]["acts"])
    acts.to_csv(os.path.join(OUT, "body_pick_actions_confirm.csv"), index=False, encoding="utf-8")
    pd.DataFrame(RUN[(pick["列"], "主", "探索")]["acts"]).to_csv(os.path.join(OUT, "body_pick_actions_explore.csv"), index=False, encoding="utf-8")
    log("[挑中那組 確認段動作]\n" + (acts.to_string() if len(acts) else "（無）"))

    # D3 敏感度（描述）
    rows3 = []
    for li, c in CL[(CL["窗"] == "主窗") & (CL["型"] == "格")].iterrows():
        i0, i1 = SEG[("主", "探索")]
        r = run_cell(M, c, i0, i1, dd, NH, cal, d3="a")
        rows3.append({"列": li, "名稱": cname(c), "年化": r["年化"], "回落": r["回落"], "比值": r["比值"], "動手日／年": r["動手日／年"]})
    d3 = pd.DataFrame(rows3); d3.to_csv(os.path.join(OUT, "body_d3a_explore.csv"), index=False, encoding="utf-8")
    p3 = sel(d3, "年化"); cp3 = conf_row(p3["列"])
    S["D3敏感度（a 窗首一律上膛；描述）"] = {"挑中": p3["名稱"], "探索年化": p3["年化"], "確認年化": cp3["年化"], "確認回落": cp3["回落"],
                                     "與主讀法同一格": bool(p3["列"] == pick["列"])}
    log(f"[D3 敏感度] {S['D3敏感度（a 窗首一律上膛；描述）']}")

    # 2022 谷底
    c0i, c1i = SEG[("主", "確認")]; ny = pos["2022-12-30"] - c0i + 1

    def trough(eq, nday=None):
        p_ = np.r_[1.0, eq if nday is None else eq[:nday]]; il = int(np.argmin(p_))
        aft = np.flatnonzero(np.r_[1.0, eq][il:] >= 1.0) if p_.min() < 1 else []
        return {"谷底（100萬）": float(p_.min() * 1e6), "谷底日": cal[c0i + il - 1] if il > 0 else "起點",
                "期末（100萬）": float((eq if nday is None else eq[:nday])[-1] * 1e6),
                "谷底後回到100萬（交易日）": int(aft[0]) if len(aft) else "未回本"}
    c0run = RUN[(c0.index[0] if False else int(c0c["列"]), "主", "確認")]
    S["2022"] = {"挑中": trough(RUN[(pick["列"], "主", "確認")]["eq"], ny), "C0同H": trough(c0run["eq"], ny),
                 "0050": trough(b50[c0i:c1i + 1] / b50[c0i - 1], ny)}
    log(f"[2022] {S['2022']}")

    # 假訊號
    K = RUN[(pick["list"] if False else pick["列"], "主", "確認")]["加碼階數"]
    n = c1i - c0i + 1; rng = np.random.default_rng(SEED_NULL); res = []; alld = []
    for j in range(NREP):
        dsel = np.sort(rng.choice(np.arange(1, n), size=K, replace=False)) if K > 0 else np.array([], int)
        alld.append(dsel)
        r = sim(M, pc["H"], pc["A"], float(pc["r"]), pc["梯"], pc["回補"], c0i, c1i, dd, NH, cal, rand_days=list(dsel))
        res.append((r["年化"], r["回落"]))
    res = np.array(res)
    np.savez_compressed(os.path.join(OUT, "body_null_days.npz"), days=np.array(alld, dtype=np.int64).reshape(NREP, K))
    pd.DataFrame(res, columns=["年化", "回落"]).to_csv(os.path.join(OUT, "body_null.csv"), index=False, encoding="utf-8")
    S["假訊號"] = {"加碼階數（確認段）": int(K), "贏同H C0 比例（主讀）": float(np.mean(res[:, 0] > c0c["年化"])),
                 "對0050合格比例": float(np.mean([L2.label(x, y, *B[("主", "確認")]) == "合格" for x, y in res]))}
    log(f"[假訊號] {S['假訊號']}")

    # 刪減（問②）
    X5 = ("0050", "0052", "00631L", "00685L", "現金")

    def uses(row, x):
        if x == "現金":
            return row["型"] != "C0"
        return x in (row["H"], row["A"])
    dl = []
    for key in ("年化", "比值"):
        for x in X5:
            w = "00685L窗" if x == "00685L" else "主窗"
            e = df[(df["跑在"] == w) & (df["段"] == "探索")]
            if x != "00685L":
                e = e[e["窗組"] == "主窗"]
            with_ = e[[uses(r, x) for _, r in e.iterrows()]]; without = e[[not uses(r, x) for _, r in e.iterrows()]]
            pw, po = sel(with_, key), sel(without, key)
            cw, co = conf_row(pw["列"], w), conf_row(po["列"], w)
            d_c = co["年化"] - cw["年化"]; d_m = co["回落"] - cw["回落"]
            dl.append({"挑法": "乙 只看年化（主表）" if key == "年化" else "甲 年化÷回落（並列）", "X": x, "窗": w + ("（窗較短）" if x == "00685L" else ""),
                       "含X最好": pw["名稱"], "含X確認年化": cw["年化"], "含X確認回落": cw["回落"],
                       "不含X最好": po["名稱"], "不含X確認年化": co["年化"], "不含X確認回落": co["回落"],
                       "拿掉後年化變化（點）": d_c * 100, "拿掉後回落變化（點）": d_m * 100,
                       "判": "可刪" if (d_c >= -0.005 and d_m >= -0.01) else "有貢獻"})
    dlt = pd.DataFrame(dl); dlt.to_csv(os.path.join(OUT, "body_delete.csv"), index=False, encoding="utf-8")
    log("[刪減]\n" + dlt[["挑法", "X", "含X最好", "不含X最好", "拿掉後年化變化（點）", "拿掉後回落變化（點）", "判"]].to_string())

    # 壓力段（合成正2、0052 早年實價、00685L 無資料）
    s0 = pos[STRESS[0]]; s1 = pos[STRESS[1]]
    o, cc = G["O"]["0050"], b50
    Lc = np.full(N, np.nan); Lo = np.full(N, np.nan); Lc[s0 - 2] = 1.0
    for t in range(s0 - 1, N):
        Lo[t] = Lc[t - 1] * (1 + 2 * (o[t] / cc[t - 1] - 1)) if np.isfinite(o[t]) else np.nan
        Lc[t] = Lc[t - 1] * (1 + 2 * (cc[t] / cc[t - 1] - 1) - T.FEE)
    MS = Mkt(G, O52, C52, O85, C85, syn=(Lo, Lc))
    srows = []
    for wn, (a_, b_) in (("2006-09-12～2014-12-31", (s0, s1)), ("2008-01～2009-03", (pos[P08[0]], pos[P08[1]]))):
        for nm, c in (("挑中那組", pc), ("C0 純抱同 H", CL.loc[int(c0c["列"])])):
            if "00685L" in (c["H"], c["A"]):
                srows.append({"期間": wn, "對象": nm, "註": "無資料（00685L 2017 才上市）"}); continue
            r = run_cell(MS, c, a_, b_, dd, NH, cal)
            p_ = np.r_[1.0, r["eq"]]; pk = np.maximum.accumulate(p_); il = int(np.argmin(p_))
            aft = np.flatnonzero(p_[il:] >= 1.0) if p_.min() < 1 else []
            srows.append({"期間": wn, "對象": nm + ("（正2 為合成）" if "00631L" in (c["H"], c["A"]) else ""), "名稱": cname(c), "最大跌幅": float(((p_ - pk) / pk).min()),
                          "100萬谷底剩": float(p_.min() * 1e6), "谷底日": cal[a_ + il - 1] if il > 0 else "起點",
                          "谷底後回到100萬（交易日）": int(aft[0]) if len(aft) else "期間內未回本", "100萬期末": float(r["eq"][-1] * 1e6),
                          "年化": r["年化"], "動手日／年": r["動手日／年"]})
        eq = b50[a_:b_ + 1] / b50[a_ - 1]; p_ = np.r_[1.0, eq]; pk = np.maximum.accumulate(p_); il = int(np.argmin(p_))
        aft = np.flatnonzero(p_[il:] >= 1.0) if p_.min() < 1 else []
        srows.append({"期間": wn, "對象": "0050", "名稱": "0050 還原收盤、不含成本", "最大跌幅": float(((p_ - pk) / pk).min()), "100萬谷底剩": float(p_.min() * 1e6),
                      "谷底日": cal[a_ + il - 1] if il > 0 else "起點", "谷底後回到100萬（交易日）": int(aft[0]) if len(aft) else "期間內未回本",
                      "100萬期末": float(eq[-1] * 1e6), "年化": float(eq[-1] ** (245 / len(eq)) - 1)})
    stp = pd.DataFrame(srows); stp.to_csv(os.path.join(OUT, "body_stress.csv"), index=False, encoding="utf-8")
    log("[壓力（合成、非實際 ETF）]\n" + stp.to_string())
    # 描述：現金年 1%
    r1 = sim(M, pc["H"], pc["A"], float(pc["r"]), pc["梯"], pc["回補"], c0i, c1i, dd, NH, cal, cash_g=CASH_G)
    S["描述_現金年1%"] = {"確認年化": r1["年化"], "確認回落": r1["回落"]}
    S["壓力"] = srows; S["刪減"] = dl
    json.dump(S, open(os.path.join(OUT, "body_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=lambda o: o.item() if hasattr(o, "item") else str(o))
    log("[完] body")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("stage", choices=["pre", "body"])
    a = ap.parse_args(); pre(a) if a.stage == "pre" else body(a)


if __name__ == "__main__":
    main()
