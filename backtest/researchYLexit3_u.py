# -*- coding: utf-8 -*-
"""PREREG營量出場 甲件 使用者版 v1（描述臂：不計 N、不改判定、不重挑）。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLexit3_u [--procs 2]
    簡短查核：~/tw-p16/.venv/bin/python backtest/researchYLexit3_u_check.py

使用者原話（逐字，含兩次更正後的版本）：
  「跌破10%+等待改15天（並股價最低點緩步上升或均線即將多頭排列之個股等待期再加10天），一般跌破賣出是已當天最低點+隔天收盤做確認！」
  「（a)要從跌倒的最低點才開始看喔！」
═══ 本線讀法（⚠ 登錄沒寫、本線補；請使用者／台股確認）；看任何本件數字前寫死 ═══
 U1 跌破確認（兩天）：第 d 根收盤 ＜ 成本×0.90 ＝「跌破」；第 d＋1 根收盤 ＜ 第 d 根最低價 ⇒ 確認，第 d＋2 根開盤賣；
    第 d＋1 根沒確認 ⇒ 不賣（計「確認規則擋下」一次）；若第 d＋1 根收盤自己也 ＜ 成本×0.90 ⇒ 它成為新的「跌破」根，再看下一根（下次跌破重新算）
    成本 ＝ 進場開盤；收盤、最低價 ＝ 還原價、有效 K 棒
 U2 等待期 15 根（取代 10），自賣出那根算第 1 根；期間：① 警訊（W1～W4，seq3 同定義）⇒ 放棄 ② 收盤 ≥ 成本 ⇒ 下一根開盤買回 ③ 新營量訊號根 ⇒ 下一根開盤買回；
    同根 ① 優先；買回最多 1 次（買回後再「確認跌破」⇒ 下一根開盤賣出即放棄，同 seq3）；警訊期間從「確認根」起算（含）
 U3 延長 10 根：第 15 根收盤仍 ＜ 成本 且沒 ①②③ ⇒ 檢查 (a) 或 (b)，任一成立 ⇒ 等待期延長到第 25 根；都不成立 ⇒ 放棄（名額下一根釋出）；第 25 根仍未站回 ⇒ 放棄
    (a) 最低點緩步上升（使用者更正「要從跌倒的最低點才開始看」）：在檢查根 j，找賣出根 s 到 j 之間最低價那根 m（同低取最後一根）；
        須 j − m ≥ 6；自 m＋1 起每 3 根一段（不足 3 根的最後一段捨去），各段最低價嚴格遞增、且都 ＞ m 的最低價
    (b) 均線即將多頭排列：MA5 ＞ MA10 ＞ MA20、MA20 ＞ 5 根前的 MA20、且 MA20 ≥ MA60×0.98（收盤均線、含當根、有效 K 棒）
 U4 H {40, 60, 80}；另附「不看警訊」版；其餘（名額保留、成本、合成序列、held_map、強制出場、T1）同 seq3
 U5 並列：seq3 挑中格（b5_H40）、b10 掃描版（同 H；bsweep）、營量 v1、0050；對營量 v1 同段配對差（95% CI）
    另報：確認規則擋下次數、確認後賣出次數、延長觸發次數（(a)、(b)、兩者都成立）、延長後買回、延長後放棄
 閘：營量 v1 ＝ resultsYLexit3 種子 0 eq_sha（主、早年）；種子 1 顆（營量不抽籤）
 網頁：對照表＋6 張例子（H40 看警訊版、確認段實際成交；各類取「差 ＝ 本規則 − 原版」中位那筆）：
    確認後賣出、被確認規則擋下（整筆沒賣）、延長後買回、延長後放棄、(a) 判法示意（標 m 與各段低點）、(b) 觸發延長
輸出 backtest/resultsYLexit3/user_v1/
"""
from __future__ import annotations

import argparse
import html
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import rerun17 as RR
from backtest import research11 as R11
from backtest import researchYLexit as YX
from backtest import researchYLexit3 as Y3
from backtest import researchYLexit3_b as YB
from backtest import chart_svg as CS

OUT = "backtest/resultsYLexit3/user_v1"
F_HTML = "營量出場_使用者版v1_20260928.html"
COST = R11.COST
B_U, L1, L2 = 0.10, 15, 25
H_S = (40, 60, 80)
RAW = ["跌破10%+等待改15天（並股價最低點緩步上升或均線即將多頭排列之個股等待期再加10天），一般跌破賣出是已當天最低點+隔天收盤做確認！",
       "（a)要從跌倒的最低點才開始看喔！"]
_W: dict = {}


def lowma(W, s):
    Cc = W.setdefault("LM", {})
    if s not in Cc:
        b = R11.load_bars(s, W["mk"].get(s, "twse"), W["cal"])
        c = b["c"]; sr = pd.Series(c)
        Cc[s] = {"l": b["l"], "h": b["h"], "ma": {n: sr.rolling(n, min_periods=n).mean().to_numpy() for n in (5, 10, 20, 60)}}
    return Cc[s]


def cond_a(lo, s_bar, j):
    seg = lo[s_bar:j + 1]
    m = s_bar + (len(seg) - 1 - int(np.argmin(seg[::-1])))           # 同低取最後一根
    if j - m < 6:
        return False, m, []
    n = (j - m) // 3; mins = [float(lo[m + 1 + 3 * q: m + 4 + 3 * q].min()) for q in range(n)]
    ok = all(x > lo[m] for x in mins) and all(mins[q] < mins[q + 1] for q in range(n - 1))
    return bool(ok), m, mins


def cond_b(ma, j):
    m5, m10, m20, m60 = ma[5][j], ma[10][j], ma[20][j], ma[60][j]
    if j < 5 or not np.all(np.isfinite([m5, m10, m20, m60, ma[20][j - 5]])):
        return False
    return bool(m5 > m10 > m20 and m20 > ma[20][j - 5] and m20 >= m60 * 0.98)


def pathU(W, s, k, e, x, warn=True, M=1):
    B = YX.bars_of(W, s)
    st = {"出": 0, "進": 0, "擋": 0, "確認賣": 0, "放棄": None, "警訊": [], "延長": None, "延長後": None, "事件": [], "擋根": [], "a圖": None, "終於暫出": False}
    if B is None or x < 0:
        return None, x, None, st
    idx = B[0]; NP = W["NP"]; n0 = len(W["cal"]); cl, op = W["closes"][s], W["opens"][s]
    LM = lowma(W, s); lo = LM["l"]; WA = Y3.warns(W, s); nk = W["NEWK"]["營量"].get(s, set())
    ke = k + 1; kx = int(np.searchsorted(idx, (NP - 2) if x >= n0 else x, side="right") - 1)
    P0 = float(op[e]); inm = True; ve = 1.0; pe = P0; vf = None; touched = False; vals = {}
    pend = None; cand = None; s_bar = None; s_open = None; lim = L1; xrel = None
    for j in range(ke, kx + 1):
        t = int(idx[j]); o_t = float(op[t]); c_t = float(cl[t])
        if pend == "sell" and inm and np.isfinite(o_t) and o_t > 0:
            vf = ve * o_t / pe; inm = False; touched = True; st["出"] += 1; s_bar = j; s_open = o_t; lim = L1; st["事件"].append(("賣", t, o_t))
        elif pend == "buy" and (not inm) and np.isfinite(o_t) and o_t > 0:
            ve = vf * (1.0 - COST); pe = o_t; inm = True; st["進"] += 1; cand = None; st["事件"].append(("買回", t, o_t))
            if st["延長"] is not None:
                st["延長後"] = "買回"
        elif pend == "abandon":
            if inm and np.isfinite(o_t) and o_t > 0:
                vf = ve * o_t / pe; inm = False; touched = True; st["出"] += 1; s_bar = j; st["事件"].append(("賣", t, o_t))
            vals[t] = vf; xrel = t; st["事件"].append(("放棄", t, float(cl[t])))
            if st["延長"] is not None and st["延長後"] is None:
                st["延長後"] = "放棄"
            break
        pend = None
        vals[t] = (ve * c_t / pe) if inm else vf
        if j >= kx:
            break
        if inm:
            confirmed = cand is not None and c_t < lo[cand]
            if cand is not None and not confirmed:
                st["擋"] += 1; st["擋根"].append(int(idx[cand]))
            if confirmed:
                cand = None; st["確認賣"] += 1
                if M is not None and st["進"] >= M:
                    pend = "abandon"; st["放棄"] = "買回上限"; continue
                pend = "sell"
                hit = [w for w in Y3.WS if WA[w][j]] if warn else []
                if hit:
                    pend = "abandon"; st["放棄"] = "警訊"; st["警訊"] = hit
            else:
                cand = j if c_t < P0 * (1.0 - B_U) else None
        else:
            hit = [w for w in Y3.WS if WA[w][j]] if warn else []
            nout = j - s_bar + 1
            if hit:
                pend = "abandon"; st["放棄"] = "警訊"; st["警訊"] = hit
            elif c_t >= P0 or j in nk:
                pend = "buy"
            elif nout == L1 and lim == L1:
                ca, m_, mins = cond_a(lo, s_bar, j); cb = cond_b(LM["ma"], j)
                if ca or cb:
                    lim = L2; st["延長"] = ("a" if ca else "") + ("b" if cb else "")
                    st["a圖"] = (int(idx[m_]), float(lo[m_]), [(int(idx[m_ + 1 + 3 * q]), int(idx[min(m_ + 3 + 3 * q, j)]), v) for q, v in enumerate(mins)], int(idx[j]), bool(ca))
                else:
                    pend = "abandon"; st["放棄"] = f"等滿{L1}"
            elif lim == L2 and nout >= L2:
                pend = "abandon"; st["放棄"] = f"延長後等滿{L2}"
    if not touched:
        return None, x, None, st
    if xrel is None and not inm:
        st["終於暫出"] = True
    Sc = np.array(cl, dtype=float, copy=True); lastv = None
    for t in range(e, NP):
        if t in vals:
            lastv = vals[t]
        if lastv is not None:
            Sc[t] = P0 * lastv
    xp = xrel if xrel is not None else x
    return Sc, xp, Sc[xp if xp < NP else NP - 1] / P0 - 1.0, st


def inputsU(W, cell):
    Cc = W.setdefault("CU", {})
    if cell in Cc:
        return Cc[cell]
    H, warn = cell
    base = W["SIGH"][("營量", H)]
    rows = []; ac = {}; ao = {}; hm = {}; stats = []
    for r in base.itertuples(index=False):
        s, k, e, x, g0 = r.sid, int(r.k), int(r.entry_pos), int(getattr(r, f"xpos_H{H}")), float(getattr(r, f"g_H{H}"))
        Sc, xp, g, st = pathU(W, s, k, e, x, warn=warn)
        st.update({"sid": s, "e": e}); stats.append(st)
        if Sc is None:
            rows.append((s, s, k, e, x, g0, r.relvol))
        else:
            key = f"{s}#{e}"; ac[key] = Sc; ao[key] = W["opens"][s]; hm[key] = s; rows.append((key, s, k, e, xp, g, r.relvol))
    sig = pd.DataFrame(rows, columns=["sid", "usid", "k", "entry_pos", f"xpos_H{H}", f"g_H{H}", "relvol"])
    for s in set(sig["usid"]):
        hm.setdefault(s, s)
    SF = {**W["SF"], **{k_: W["SF"][u] for k_, u in hm.items() if u in W["SF"] and k_ != u}}
    Cc[cell] = (sig, f"H{H}", {**W["closes"], **ac}, {**W["opens"], **ao}, SF, hm, stats)
    return Cc[cell]


def cname(cell):
    return f"使用者v1_H{cell[0]}" + ("" if cell[1] else "_不看警訊")


def run_cell(job):
    wk, cell = job
    W = _W[wk]
    if cell == "base":
        sig, rule = W["SIGH"][("營量", 60)], "H60"; cl = op = SF = hm = None; nm = "營量v1"
    else:
        sig, rule, cl, op, SF, hm, _ = inputsU(W, cell); nm = cname(cell)
    o, aud = YX._eng(W, "營量", sig, rule, 7000, closes=cl, opens=op, SF=SF, held_map=hm)
    row, eq, _ = YX._stats(W, o, aud, W["SEGP"], 20)
    row.update({"世界": wk, "格": nm, "eq_sha": YX.sha(eq)})
    diffs = {}
    if W.get("V1EQ") is not None and cell != "base":
        V1 = W["V1EQ"]
        for sg, (x, y) in W["SEGP"].items():
            diffs[sg] = (eq[x + 1:y + 1] / eq[x:y] - 1.0) - (V1[x + 1:y + 1] / V1[x:y] - 1.0)
    return row, diffs, (eq, aud)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    log(f"===== researchYLexit3_u {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜使用者版 v1（描述臂、不計 N、不改判定、不重挑） =====")
    S = {"身分": "使用者版 v1；描述臂、不計 N、不改判定、不重挑", "使用者原話": RAW, "閘": {}}
    Wm, We, ctx = YB.worlds(log)
    _W["主"] = Wm; _W["早年"] = We
    for W in (Wm, We):                                     # 低價、均線預載（依各自版面）
        pass
    RR.use_snapshot()
    for s in sorted(set(ctx["sig13"]["sid"])):
        lowma(Wm, s)
    from backtest import researchV as V
    D.DATA = V.body_paths("main")[0]
    for s in sorted(set(We["SIGH"][("營量", 60)]["sid"])):
        lowma(We, s)
    RR.use_snapshot()
    CELLS = [(H, w) for H in H_S for w in (True, False)]
    ref = pd.read_csv("backtest/resultsYLexit3/seeds.csv.gz", dtype={"eq_sha": str}, low_memory=False)
    ROWS = []; DIFF = {}; KEEP = {}
    for wk, W in (("主", Wm), ("早年", We)):
        row, _, (eqb, _) = run_cell((wk, "base")); W["V1EQ"] = eqb; ROWS.append(row)
        rr = ref[(ref["世界"] == wk) & (ref["格"] == "營量v1") & (ref["r"] == 0)]["eq_sha"].iloc[0]
        S["閘"][f"{wk}｜營量 v1 ＝ resultsYLexit3 種子 0"] = bool(row["eq_sha"] == rr)
        with Pool(a.procs) as pool:
            res = pool.map(run_cell, [(wk, c) for c in CELLS])
        for c, (row, diffs, ea) in zip(CELLS, res):
            ROWS.append(row)
            for sg, d in diffs.items():
                DIFF[(wk, row["格"], sg)] = d
            if wk == "主" and c == (40, True):
                KEEP["aud"] = ea[1]
        for c in CELLS:
            inputsU(W, c)                                  # 路徑統計（主行程）
        log(f"[{wk}] 完成｜{S['閘']}")
    SEED = pd.DataFrame(ROWS); SEED.to_csv(os.path.join(OUT, "seeds.csv"), index=False, float_format="%.17g")
    Z = json.load(open("backtest/resultsYLexit3/summary.json", encoding="utf-8"))["0050"]
    cal, ecal = Wm["cal"], We["cal"]
    months = {sg: np.array([str(d)[:7] for d in cal[x + 1:y + 1]]) for sg, (x, y) in Wm["SEGP"].items()}
    months["早年"] = np.array([str(d)[:7] for d in ecal[We["w0"] + 1:We["w1"] + 1]])
    old = pd.read_csv("backtest/resultsYLexit3/cells.csv").set_index("格"); bs = pd.read_csv("backtest/resultsYLexit3/bsweep/bcurve.csv").set_index("格")
    TB = []
    for c in CELLS:
        k = cname(c); row = {"格": k, "H": c[0], "警訊": "看" if c[1] else "不看"}
        for sg, wk in (("探索", "主"), ("確認", "主"), ("早年", "早年")):
            g = SEED[(SEED["世界"] == wk) & (SEED["格"] == k)].iloc[0]
            cc, mm = float(g[f"{sg}_年化"]), float(g[f"{sg}_回落"])
            row.update({f"{sg}_年化": cc, f"{sg}_回落": mm, f"{sg}_比值": cc / abs(mm), f"{sg}_標籤": YX.label(cc, mm, Z[sg])})
            m_, se_ = YX.cr0(DIFF[(wk, k, sg)], months[sg])
            row[f"{sg}_配對差年化"] = m_ * 245
            if sg == "確認":
                row["確認_配對差lo"] = (m_ - 1.96 * se_) * 245; row["確認_配對差hi"] = (m_ + 1.96 * se_) * 245
        for wk, W in (("主", Wm), ("早年", We)):
            st = [x for x in inputsU(W, c)[6] if W["w0"] <= x["e"] <= W["w1"]]
            n = len(st)
            row.update({f"{wk}_筆": n, f"{wk}_擋下次數": sum(x["擋"] for x in st), f"{wk}_確認賣出次數": sum(x["確認賣"] for x in st), f"{wk}_有暫出筆": sum(x["出"] > 0 for x in st),
                        f"{wk}_延長_a": sum(x["延長"] == "a" for x in st), f"{wk}_延長_b": sum(x["延長"] == "b" for x in st), f"{wk}_延長_ab": sum(x["延長"] == "ab" for x in st),
                        f"{wk}_延長後買回": sum(x["延長後"] == "買回" for x in st), f"{wk}_延長後放棄": sum(x["延長後"] == "放棄" for x in st),
                        f"{wk}_放棄_警訊": sum(x["放棄"] == "警訊" for x in st), f"{wk}_放棄_等滿15": sum(x["放棄"] == "等滿15" for x in st),
                        f"{wk}_放棄_延長後等滿25": sum(x["放棄"] == "延長後等滿25" for x in st), f"{wk}_放棄_買回上限": sum(x["放棄"] == "買回上限" for x in st),
                        f"{wk}_買回": sum(x["進"] for x in st)})
        TB.append(row)
    TB = pd.DataFrame(TB); TB.to_csv(os.path.join(OUT, "cells.csv"), index=False, float_format="%.17g")
    CMP = [("seq3 挑中 b5_H40（判定格）", old.loc["營量_甲3_b5_H40"]), ("營量 v1", old.loc["營量v1"])] + [(f"b10_H{H}（掃描版）", bs.loc[f"營量_甲3_b10_H{H}"]) for H in H_S]
    S["並列"] = {nm: {sg: [float(r[f"{sg}_年化"]), float(r[f"{sg}_回落"]), r[f"{sg}_標籤"]] for sg in ("探索", "確認", "早年")} for nm, r in CMP}
    S["0050"] = Z
    log("[結果] " + "；".join(f"{r.格} 確認 {r.確認_年化:+.2%}／{r.確認_回落:+.2%} {r.確認_標籤}｜早年 {r.早年_年化:+.2%} {r.早年_標籤}" for r in TB.itertuples()))
    # ── 例子（H40 看警訊、主、確認段、實際成交）
    CX = (40, True)
    sig = inputsU(Wm, CX)[0]; stl = {(x["sid"], x["e"]): x for x in inputsU(Wm, CX)[6]}
    base = ctx["sig13"]; orig = {(s_, int(e_)): (int(x_), float(g_)) for s_, e_, x_, g_ in zip(base["sid"], base["entry_pos"], base["xpos_H60"], base["g_H60"])}
    gmap = {(u, int(e_)): (int(x_), float(g_)) for u, e_, x_, g_ in zip(sig["usid"], sig["entry_pos"], sig["xpos_H40"], sig["g_H40"])}
    opn = {}; rows = []
    t0c = int(cal.searchsorted(pd.Timestamp("2022-01-03"))); t1c = int(cal.searchsorted(pd.Timestamp("2026-08-24")))
    for a_ in sorted(KEEP["aud"], key=lambda z: (z["t"], z["side"] != "sell")):
        if a_["side"] == "buy":
            opn[a_["sid"]] = a_
        else:
            b0 = opn.pop(a_["sid"]); s_ = a_["sid"].split("#")[0]; ti = b0["t"]
            if not (t0c <= ti <= t1c):
                continue
            st = stl[(s_, ti)]; x0, g0 = orig[(s_, ti)]; xr, gr = gmap[(s_, ti)]
            net = a_["amt"] / b0["amt"] - 1 - a_["cost"] / b0["amt"]
            rows.append({"sid": s_, "t_in": ti, "t_out": a_["t"], "規則淨": net, "路徑淨": gr - COST if a_["t"] == xr else np.nan, "原版淨": g0 - COST, "x0": x0, "st": st})
    T = pd.DataFrame(rows); T["差"] = T["規則淨"] - T["原版淨"]
    CK = {"H40 看警訊：audit 淨 ＝ 路徑 g − 成本（排程出場者最大差）": float((T["規則淨"] - T["路徑淨"]).abs().max())}
    cats = {"確認後賣出": T["st"].map(lambda z: z["確認賣"] > 0 and z["放棄"] is None),
            "被確認規則擋下（整筆沒賣）": T["st"].map(lambda z: z["擋"] > 0 and z["出"] == 0),
            "延長後買回": T["st"].map(lambda z: z["延長後"] == "買回"),
            "延長後放棄": T["st"].map(lambda z: z["延長後"] == "放棄"),
            "(a) 判法示意：最低點緩步上升觸發延長": T["st"].map(lambda z: z["延長"] in ("a", "ab")),
            "(b) 均線即將多頭排列觸發延長": T["st"].map(lambda z: z["延長"] == "b")}
    EX = []
    for cat, msk in cats.items():
        g = T[msk.to_numpy(bool)].sort_values(["差", "t_in"])
        EX.append((cat, g.index[(len(g) - 1) // 2] if len(g) else None, len(g)))
    uni = D.load_universe().set_index("stock_id")["name"]
    dt = lambda t: str(cal[int(t)].date())
    P = lambda x: "—" if x is None or not np.isfinite(x) else f"{x * 100:+.2f}%"
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0] + "\n.pick{background:#fff4cc}td.l,th.l{text-align:left}"
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>營量出場 使用者版 v1</title>", f"<style>{CSS}</style></head><body><main>", "<h1>營量出場 甲件：使用者版 v1（描述臂）</h1>",
         "<p class='lead'>使用者原話：「" + html.escape(RAW[0]) + "」「" + html.escape(RAW[1]) + "」<br>⛔ 描述臂：不計 N、不改判定、不重挑。</p>",
         "<p class='note'>⚠ <b>本線讀法、請使用者／台股確認</b>：① 跌破＝收盤 ＜ 成本×0.90；隔天收盤 ＜ 跌破那天的最低價才確認，再隔天開盤賣；沒確認就不賣，下次跌破重算 "
         "② 賣出後等 15 天（賣出那天算第 1 天）：站回成本或出現新的營量訊號 ⇒ 隔天買回；出現下跌警訊 ⇒ 放棄換下一檔；買回最多一次 "
         "③ 第 15 天仍沒站回：(a) 從賣出後最低那天 m 起，每 3 天一段、各段最低價一段比一段高且都高於 m（m 之後至少 6 天）或 (b) MA5＞MA10＞MA20、MA20 比 5 天前高、MA20 ≥ MA60×0.98 ⇒ 再等 10 天（到第 25 天）；否則放棄。</p>"]
    H.append("<h2>對照表（年化／回落／標籤；都扣成本）</h2><div class='wrap'><table><tr><th class='l'>版本</th><th>探索 17-21</th><th>確認 22-26</th><th>標籤</th><th>早年 12-14</th><th>標籤</th><th>確認對營量 v1〔CI〕</th></tr>")
    for r in TB.to_dict("records"):
        H.append(f"<tr class='pick'><td class='l'>使用者版 H{r['H']}（{r['警訊']}警訊）</td><td>{P(r['探索_年化'])}／{P(r['探索_回落'])}</td><td>{P(r['確認_年化'])}／{P(r['確認_回落'])}</td><td>{r['確認_標籤']}</td>"
                 f"<td>{P(r['早年_年化'])}／{P(r['早年_回落'])}</td><td>{r['早年_標籤']}</td><td>{P(r['確認_配對差年化'])}〔{P(r['確認_配對差lo'])}, {P(r['確認_配對差hi'])}〕</td></tr>")
    for nm, r in CMP:
        cd = "" if nm == "營量 v1" else f"{P(r['確認_配對差年化'])}〔{P(r['確認_配對差lo'])}, {P(r['確認_配對差hi'])}〕"
        H.append(f"<tr><td class='l'>{nm}</td><td>{P(r['探索_年化'])}／{P(r['探索_回落'])}</td><td>{P(r['確認_年化'])}／{P(r['確認_回落'])}</td><td>{r['確認_標籤']}</td>"
                 f"<td>{P(r['早年_年化'])}／{P(r['早年_回落'])}</td><td>{r['早年_標籤']}</td><td>{cd}</td></tr>")
    H.append(f"<tr><td class='l'>0050</td><td>{P(Z['探索']['cagr'])}／{P(Z['探索']['mdd'])}</td><td>{P(Z['確認']['cagr'])}／{P(Z['確認']['mdd'])}</td><td>—</td><td>{P(Z['早年']['cagr'])}／{P(Z['早年']['mdd'])}</td><td>—</td><td></td></tr></table></div>")
    H.append("<h2>規則觸發次數（主窗 2017～2026 訊號）</h2><div class='wrap'><table><tr><th class='l'>版本</th><th>筆</th><th>確認擋下（次）</th><th>確認後賣出（次）</th><th>延長 只(a)／只(b)／兩者</th><th>延長後買回／放棄</th><th>放棄 警訊／15 天／25 天／上限</th><th>買回（次）</th></tr>")
    for r in TB.to_dict("records"):
        H.append(f"<tr><td class='l'>H{r['H']}（{r['警訊']}警訊）</td><td>{r['主_筆']}</td><td>{r['主_擋下次數']}</td><td>{r['主_確認賣出次數']}</td><td>{r['主_延長_a']}／{r['主_延長_b']}／{r['主_延長_ab']}</td>"
                 f"<td>{r['主_延長後買回']}／{r['主_延長後放棄']}</td><td>{r['主_放棄_警訊']}／{r['主_放棄_等滿15']}／{r['主_放棄_延長後等滿25']}／{r['主_放棄_買回上限']}</td><td>{r['主_買回']}</td></tr>")
    H.append("</table></div>")
    H.append("<h2>例子（H40、看警訊、確認段實際成交；每類取「差 ＝ 本規則 − 原版」中位那筆）</h2>" + CS.legend_html())
    op_ = ctx["opens"]
    for cat, i, n_ in EX:
        if i is None:
            H.append(f"<p class='note'>{cat}：確認段沒有這種例子。</p>"); continue
        r = T.loc[i]; s = r["sid"]; st = r["st"]; t_in = int(r["t_in"]); t_out = min(int(r["t_out"]), len(cal) - 1); xo = min(int(r["x0"]), len(cal) - 1)
        df = D.load_stock(s, Wm["mk"].get(s, "twse"), cal).df; cf = pd.Series(df["close"].to_numpy(float)).ffill().to_numpy()
        i0 = max(0, t_in - 30); i1 = min(len(cal) - 1, max(xo, t_out) + 10); sl = slice(i0, i1 + 1)
        P0 = float(op_[s][t_in])
        marks = [{"i": t_in - i0, "px": P0, "kind": "entry", "label": f"進 {P0:.2f}"},
                 {"i": xo - i0, "px": float(cf[xo]), "kind": "exit", "label": f"原版出 {cf[xo]:.2f}", "color": "#888888", "row": 1}]
        for a_, t_, p_ in st["事件"]:
            if a_ == "賣":
                marks.append({"i": t_ - i0, "px": p_, "kind": "exit", "label": f"賣 {p_:.2f}", "color": "#c62828"})
            elif a_ == "買回":
                marks.append({"i": t_ - i0, "px": p_, "kind": "entry", "label": f"買回 {p_:.2f}", "color": "#ef6c00", "row": 1})
            else:
                marks.append({"i": t_ - i0, "px": p_, "kind": "exit", "label": f"放棄（{st['放棄']}）、換下一檔", "row": 2})
        for tb_ in st["擋根"][:3]:
            if i0 <= tb_ <= i1:
                marks.append({"i": tb_ - i0, "px": float(df["low"].to_numpy(float)[tb_]), "kind": "entry", "label": "跌破未確認", "color": "#6a1b9a", "row": 2})
        if st["放棄"] is None and not st["終於暫出"]:
            marks.append({"i": t_out - i0, "px": float(cf[t_out]), "kind": "exit", "label": f"第 40 天出場 {cf[t_out]:.2f}"})
        hl = [{"px": P0 * 0.9, "label": f"成本×0.90 ＝ {P0 * 0.9:.2f}", "color": "#e65100"}, {"px": P0, "label": f"成本 {P0:.2f}（站回線）", "color": "#1565c0"}]
        extra = ""
        if st["a圖"] is not None and cat.startswith("(a)"):
            tm, lm, segs_, tj, ok = st["a圖"]
            marks.append({"i": tm - i0, "px": lm, "kind": "entry", "label": f"m 最低 {lm:.2f}", "color": "#2e7d32", "row": 2})
            for q, (ta, tb2, v) in enumerate(segs_):
                marks.append({"i": ta - i0, "px": v, "kind": "entry", "label": f"段{q + 1} 低 {v:.2f}", "color": "#43a047", "row": q % 2})
            extra = f"｜(a) 判法：第 15 天（{dt(tj)}）往回找最低點 m＝{dt(tm)}（{lm:.2f}），之後每 3 天一段的最低價：" + "、".join(f"{v:.2f}" for _, _, v in segs_) + f" ⇒ {'一段比一段高、成立' if ok else '不成立'}"
        ma = {k: CS.moving_avg(cf, k)[sl] for k in (5, 20, 60)}
        svg = CS.kline_svg([str(z.date()) for z in cal[sl]], df["open"].to_numpy(float)[sl], df["high"].to_numpy(float)[sl], df["low"].to_numpy(float)[sl], df["close"].to_numpy(float)[sl],
                           df["volume"].to_numpy(float)[sl] / 1000.0, ma=ma, marks=marks, shade=(t_in - i0, t_out - i0), title=cat, show_title=False, hlines=hl)
        H.append(f"<details class='card' open><summary><b>{html.escape(cat)}</b>｜{s} {html.escape(str(uni.get(s, '')))}｜進場 {dt(t_in)}｜原版 {P(r['原版淨'])} → 本規則 {P(r['規則淨'])}｜差 {r['差'] * 100:+.2f} 點</summary>"
                 f"<div class='meta'>這一類在確認段 {n_} 筆（共 {len(T)} 筆）；取差的中位那筆｜擋下 {st['擋']} 次、賣 {st['出']} 次、買回 {st['進']} 次、延長 {st['延長'] or '無'}{html.escape(extra)}</div>{svg}</details>")
    H.append("</main></body></html>")
    open(os.path.join(OUT, F_HTML), "w", encoding="utf-8").write("\n".join(H))
    S["例子"] = [{"類": cat, "sid": (T.at[i, "sid"] if i is not None else None), "進場": (dt(T.at[i, "t_in"]) if i is not None else None),
                "原版淨": (float(T.at[i, "原版淨"]) if i is not None else None), "規則淨": (float(T.at[i, "規則淨"]) if i is not None else None), "類筆數": n_} for cat, i, n_ in EX]
    S["例子查核"] = CK
    NL = chr(10)
    R_ = ["# PREREG營量出場 甲件 使用者版 v1（描述臂）" + NL, "使用者原話（逐字）：「" + RAW[0] + "」「" + RAW[1] + "」" + NL,
          "> ⛔ 描述臂：不計 N、不改判定、不重挑。⚠ 本線讀法（U1～U3，見程式開頭）請使用者／台股確認。" + NL,
          "| 版本 | 探索 | 確認 | 確認標籤 | 早年 | 早年標籤 | 確認對營量 v1〔CI〕 | 擋下／確認賣 | 延長 a／b／ab | 延長後 買回／放棄 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in TB.to_dict("records"):
        R_.append(f"| H{r['H']}（{r['警訊']}警訊） | {P(r['探索_年化'])}／{P(r['探索_回落'])} | {P(r['確認_年化'])}／{P(r['確認_回落'])} | {r['確認_標籤']} | {P(r['早年_年化'])}／{P(r['早年_回落'])} | {r['早年_標籤']} | "
                  f"{P(r['確認_配對差年化'])}〔{P(r['確認_配對差lo'])}, {P(r['確認_配對差hi'])}〕 | {r['主_擋下次數']}／{r['主_確認賣出次數']} | {r['主_延長_a']}／{r['主_延長_b']}／{r['主_延長_ab']} | {r['主_延長後買回']}／{r['主_延長後放棄']} |")
    R_.append(NL + "並列：" + "；".join(f"{nm} 確認 {P(v['確認'][0])}／{P(v['確認'][1])} {v['確認'][2]}" for nm, v in S["並列"].items()) + f"；0050 確認 {P(Z['確認']['cagr'])}")
    R_.append(NL + f"閘：{S['閘']}｜例子查核：{CK}｜網頁：{F_HTML}")
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write(NL.join(R_) + NL)
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] 網頁 {os.path.getsize(os.path.join(OUT, F_HTML))} bytes｜{CK}｜例子 {[(c, n) for c, _, n in EX]}｜{time.time() - T0:.0f}s")


if __name__ == "__main__":
    main()
