# -*- coding: utf-8 -*-
"""PREREG營量出場 甲件 使用者版 v2（甲 v1 暫出／買回 ＋ 乙續抱確認決定最後出場；描述臂：不計 N、不改判定）。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLexit3_u2 [--procs 2]
    簡短查核：~/tw-p16/.venv/bin/python backtest/researchYLexit3_u2_check.py

使用者原話（逐字）：「你的出場要用確認的啊，你是單純抱天數？」
═══ 規則（協調者轉述使用者本意）＋ 本線讀法（⚠ 標 V 者為本線讀法，請使用者／台股確認；看任何本件數字前寫死）═══
 持有期間 ＝ user_v1 甲規則（researchYLexit3_u.pathU 同式）：收盤 ＜ 成本×0.90、隔日收盤 ＜ 該日最低才確認、再隔日開盤暫出；等 15 根、(a) 或 (b) 延長到 25 根；
   站回成本或新營量訊號 ⇒ 下一根開盤買回（最多一次；買回後再確認跌破 ⇒ 賣出即放棄）；警訊 W1～W4 看／不看兩版
 最後出場 ＝ 乙續抱確認：第 k 根收盤 ＝ 基準 B；之後每 c 根確認一次，收盤 ≥ B ⇒ B 上調（只上不下）；
   任一根收盤 ＜ B ＝ 基準跌破；下一根收盤 ＜ 該根最低 ⇒ 確認，再下一根開盤賣出（整筆結束、名額釋出）；沒確認 ⇒ 不賣（計「最後出場擋下」）
   持有上限 C（第 C 根收盤）
 V1 第 k 根時在場外（暫出中）⇒ 買回那一根才開始看乙：基準 ＝ 買回那根收盤、確認根自那根起每 c 根；到第 C 根仍在場外 ⇒ 照甲放棄（下一根釋出）
 V2 乙啟用後（人在場內、已過第 k 根），甲的「跌破成本 10% 暫出」不再作用：之後的出場只看乙（跌破基準確認）與上限 C；乙啟用前照甲
 V3 第 C 根超過資料末日 ⇒ 窗內照市值（T1 讀法，xpos ＝ ncal）；持有中遇壞根（next_bad）⇒ 壞根前一根收盤出（同 seq3 乙）；計數必報
 格：k {55, 60} × c {5, 10} × C {120, 250} × 警訊 看／不看 ＝ 16；其餘（成本、合成序列、held_map、強制出場、T1、20 檔 relvol）同 user_v1
 並列：user_v1（甲 H40、看警訊）、seq3 乙挑中 k55_c10_C120、營量 v1、0050；對營量 v1 同段配對差（95% CI）
 每格報：三段年化／回落／標籤、配對差、平均持有根數、觸頂 C 比例、兩日確認擋下（持有中／最後出場分開）、上調次數
 閘：營量 v1 ＝ resultsYLexit3 種子 0（主、早年）；營量不抽籤 ⇒ 1 顆
 網頁：對照表＋6 張例子（k55_c10_C120、看警訊、主、確認段實際成交；各類取「差 ＝ 本規則 − 原版」中位那筆）：
   續抱多賺（持有 ＞ 60 根且差 ＞ 0）、續抱後確認出場（乙確認出場）、暫出後買回再續抱、暫出後放棄、最後出場被確認擋下過、觸頂上限 C
輸出 backtest/resultsYLexit3/user_v2/
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
from backtest import researchYLexit3_u as U
from backtest import chart_svg as CS

OUT = "backtest/resultsYLexit3/user_v2"
F_HTML = "營量出場_使用者版v2_20260928.html"
COST = R11.COST
RAW = "你的出場要用確認的啊，你是單純抱天數？"
K_S, CC_S, C_S = (55, 60), (5, 10), (120, 250)
_W: dict = {}


def pathV2(W, s, k, e, K, cs, C, warn=True, M=1):
    """回 (Sc 或 None, xpos, g, st)。"""
    B = YX.bars_of(W, s)
    st = {"出": 0, "進": 0, "擋_持有": 0, "擋_出場": 0, "放棄": None, "延長": None, "乙啟用t": None, "上調": 0, "結束": None, "事件": [], "基準0": np.nan, "基準F": np.nan, "持有根": np.nan}
    if B is None:
        return None, -1, None, st
    idx, _, _, nb, _, _ = B; n = len(idx); NP = W["NP"]; n0 = len(W["cal"]); cl, op = W["closes"][s], W["opens"][s]
    LM = U.lowma(W, s); lo = LM["l"]; WA = Y3.warns(W, s); nk = W["NEWK"]["營量"].get(s, set())
    ke = k + 1; nbk = nb[max(0, k - 20)]; kc = ke + C - 1; kk = ke + K - 1
    last = min(kc, n - 1, nbk - 1)
    P0 = float(op[e]); inm = True; ve = 1.0; pe = P0; vf = None; touched = False; vals = {}
    pend = None; cand = None; s_bar = None; lim = U.L1; xrel = None; xclose = None
    act = None; Bv = None; bcand = None
    for j in range(ke, last + 1):
        t = int(idx[j]); o_t = float(op[t]); c_t = float(cl[t])
        if pend == "sell" and inm and np.isfinite(o_t) and o_t > 0:
            vf = ve * o_t / pe; inm = False; touched = True; st["出"] += 1; s_bar = j; lim = U.L1; st["事件"].append(("賣", t, o_t))
        elif pend == "buy" and (not inm) and np.isfinite(o_t) and o_t > 0:
            ve = vf * (1.0 - COST); pe = o_t; inm = True; st["進"] += 1; cand = None; st["事件"].append(("買回", t, o_t))
        elif pend == "abandon":
            if inm and np.isfinite(o_t) and o_t > 0:
                vf = ve * o_t / pe; inm = False; touched = True; st["出"] += 1; st["事件"].append(("賣", t, o_t))
            vals[t] = vf; xrel = t; st["事件"].append(("放棄", t, float(cl[t]))); st["結束"] = f"甲放棄（{st['放棄']}）"; break
        elif pend == "final":
            if np.isfinite(o_t) and o_t > 0:
                vals[t] = ve * o_t / pe; xrel = t; st["事件"].append(("續抱出", t, o_t)); st["結束"] = "乙確認出場"; break
        pend = None
        vals[t] = (ve * c_t / pe) if inm else vf
        # 乙啟用（V1）
        if act is None and inm and j >= kk:
            act = j; Bv = c_t; st["乙啟用t"] = t; st["基準0"] = Bv
        if j >= last:
            xclose = j
            break
        if inm and act is not None:                            # 乙（V2：甲的 10% 暫出不再作用）
            confirmed = bcand is not None and c_t < lo[bcand]
            if bcand is not None and not confirmed:
                st["擋_出場"] += 1
            if confirmed:
                pend = "final"; bcand = None; continue
            if (j - act) % cs == 0 and c_t >= Bv:
                st["上調"] += int(c_t > Bv); Bv = c_t
            bcand = j if c_t < Bv else None
        elif inm:                                              # 甲（乙啟用前）
            confirmed = cand is not None and c_t < lo[cand]
            if cand is not None and not confirmed:
                st["擋_持有"] += 1
            if confirmed:
                cand = None
                if M is not None and st["進"] >= M:
                    pend = "abandon"; st["放棄"] = "買回上限"; continue
                pend = "sell"
                hit = [w for w in Y3.WS if WA[w][j]] if warn else []
                if hit:
                    pend = "abandon"; st["放棄"] = "警訊"
            else:
                cand = j if c_t < P0 * (1.0 - U.B_U) else None
        else:
            hit = [w for w in Y3.WS if WA[w][j]] if warn else []
            nout = j - s_bar + 1
            if hit:
                pend = "abandon"; st["放棄"] = "警訊"
            elif c_t >= P0 or j in nk:
                pend = "buy"
            elif nout == U.L1 and lim == U.L1:
                ca, _, _ = U.cond_a(lo, s_bar, j); cb = U.cond_b(LM["ma"], j)
                if ca or cb:
                    lim = U.L2; st["延長"] = ("a" if ca else "") + ("b" if cb else "")
                else:
                    pend = "abandon"; st["放棄"] = f"等滿{U.L1}"
            elif lim == U.L2 and nout >= U.L2:
                pend = "abandon"; st["放棄"] = f"延長後等滿{U.L2}"
    if xrel is None:                                           # 走到最後一根收盤
        t = int(idx[xclose]); st["基準F"] = Bv if Bv is not None else np.nan
        if not inm:
            xrel = t + 1 if t + 1 < NP else NP - 1; st["結束"] = "到上限仍在外、甲放棄"
            vals[xrel] = vf
        elif xclose == kc:
            xrel = t; st["結束"] = "觸頂上限 C"
        elif xclose == nbk - 1 and nbk <= min(kc, n - 1):
            xrel = t; st["結束"] = "壞根前截"
        else:
            xrel = n0 if t == n0 - 1 else t; st["結束"] = "資料尾（窗內照市值）" if t == n0 - 1 else "停止交易（最後有效收盤）"
    else:
        st["基準F"] = Bv if Bv is not None else np.nan
    st["持有根"] = int(np.searchsorted(idx, min(xrel, n0 - 1), side="right") - 1) - ke + 1
    if not touched:
        g = float(cl[min(xrel, NP - 1)]) / P0 - 1.0 if st["結束"] != "乙確認出場" else vals[xrel] - 1.0
        return None, xrel, g, st
    Sc = np.array(cl, dtype=float, copy=True); lastv = None
    for t in range(e, NP):
        if t in vals:
            lastv = vals[t]
        if lastv is not None:
            Sc[t] = P0 * lastv
    return Sc, xrel, Sc[xrel if xrel < NP else NP - 1] / P0 - 1.0, st


def inputs(W, cell):
    Cc = W.setdefault("C2", {})
    if cell in Cc:
        return Cc[cell]
    K, cs, C, warn = cell
    base = W["SIGH"][("營量", 60)]
    rows = []; ac = {}; ao = {}; hm = {}; stats = []
    for r in base.itertuples(index=False):
        s, k, e, x0 = r.sid, int(r.k), int(r.entry_pos), int(r.xpos_H60)
        if x0 < 0:
            rows.append((s, s, k, e, x0, np.nan, r.relvol)); continue
        Sc, xp, g, st = pathV2(W, s, k, e, K, cs, C, warn=warn)
        st.update({"sid": s, "e": e}); stats.append(st)
        if Sc is None:                                         # 從沒暫出：原序列、只改 xpos／g（開盤出場也只影響入帳，引擎出場日不以收盤計值）
            rows.append((s, s, k, e, xp, g, r.relvol))
        else:
            key = f"{s}#{e}"; ac[key] = Sc; ao[key] = W["opens"][s]; hm[key] = s; rows.append((key, s, k, e, xp, g, r.relvol))
    sig = pd.DataFrame(rows, columns=["sid", "usid", "k", "entry_pos", "xpos_HX", "g_HX", "relvol"])
    for s in set(sig["usid"]):
        hm.setdefault(s, s)
    SF = {**W["SF"], **{k_: W["SF"][u] for k_, u in hm.items() if u in W["SF"] and k_ != u}}
    Cc[cell] = (sig, "HX", {**W["closes"], **ac}, {**W["opens"], **ao}, SF, hm, stats)
    return Cc[cell]


def cname(cell):
    K, cs, C, warn = cell
    return f"使用者v2_k{K}_c{cs}_C{C}" + ("" if warn else "_不看警訊")


def run_cell(job):
    wk, cell = job
    W = _W[wk]
    if cell == "base":
        sig, rule = W["SIGH"][("營量", 60)], "H60"; cl = op = SF = hm = None; nm = "營量v1"
    else:
        sig, rule, cl, op, SF, hm, _ = inputs(W, cell); nm = cname(cell)
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
    log(f"===== researchYLexit3_u2 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜使用者版 v2（描述臂、不計 N、不改判定） =====")
    S = {"身分": "使用者版 v2；描述臂、不計 N、不改判定", "使用者原話": RAW, "閘": {}}
    Wm, We, ctx = YB.worlds(log)
    _W["主"] = Wm; _W["早年"] = We
    RR.use_snapshot()
    for s in sorted(set(ctx["sig13"]["sid"])):
        U.lowma(Wm, s)
    from backtest import researchV as V
    D.DATA = V.body_paths("main")[0]
    for s in sorted(set(We["SIGH"][("營量", 60)]["sid"])):
        U.lowma(We, s)
    RR.use_snapshot()
    CELLS = [(K, cs, C, w) for K in K_S for cs in CC_S for C in C_S for w in (True, False)]
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
            if wk == "主" and c == (55, 10, 120, True):
                KEEP["aud"] = ea[1]
        for c in CELLS:
            inputs(W, c)
        log(f"[{wk}] 完成｜{S['閘']}")
    SEED = pd.DataFrame(ROWS); SEED.to_csv(os.path.join(OUT, "seeds.csv"), index=False, float_format="%.17g")
    Z = json.load(open("backtest/resultsYLexit3/summary.json", encoding="utf-8"))["0050"]
    cal, ecal = Wm["cal"], We["cal"]
    months = {sg: np.array([str(d)[:7] for d in cal[x + 1:y + 1]]) for sg, (x, y) in Wm["SEGP"].items()}
    months["早年"] = np.array([str(d)[:7] for d in ecal[We["w0"] + 1:We["w1"] + 1]])
    TB = []
    for c in CELLS:
        k = cname(c); row = {"格": k, "k": c[0], "c": c[1], "C": c[2], "警訊": "看" if c[3] else "不看"}
        for sg, wk in (("探索", "主"), ("確認", "主"), ("早年", "早年")):
            g = SEED[(SEED["世界"] == wk) & (SEED["格"] == k)].iloc[0]
            cc, mm = float(g[f"{sg}_年化"]), float(g[f"{sg}_回落"])
            row.update({f"{sg}_年化": cc, f"{sg}_回落": mm, f"{sg}_比值": cc / abs(mm), f"{sg}_標籤": YX.label(cc, mm, Z[sg])})
            m_, se_ = YX.cr0(DIFF[(wk, k, sg)], months[sg])
            row[f"{sg}_配對差年化"] = m_ * 245
            if sg == "確認":
                row["確認_配對差lo"] = (m_ - 1.96 * se_) * 245; row["確認_配對差hi"] = (m_ + 1.96 * se_) * 245
        for wk, W in (("主", Wm), ("早年", We)):
            st = [x for x in inputs(W, c)[6] if W["w0"] <= x["e"] <= W["w1"]]
            h = np.array([x["持有根"] for x in st], float)
            row.update({f"{wk}_筆": len(st), f"{wk}_平均持有根數": float(np.mean(h)), f"{wk}_觸頂C比例": float(np.mean([x["結束"] == "觸頂上限 C" for x in st])),
                        f"{wk}_乙確認出場比例": float(np.mean([x["結束"] == "乙確認出場" for x in st])), f"{wk}_甲放棄比例": float(np.mean([str(x["結束"]).startswith(("甲放棄", "到上限")) for x in st])),
                        f"{wk}_擋下_持有中": sum(x["擋_持有"] for x in st), f"{wk}_擋下_最後出場": sum(x["擋_出場"] for x in st),
                        f"{wk}_平均上調次數": float(np.mean([x["上調"] for x in st])), f"{wk}_有暫出筆": sum(x["出"] > 0 for x in st), f"{wk}_買回": sum(x["進"] for x in st),
                        f"{wk}_資料尾補": sum(str(x["結束"]).startswith("資料尾") for x in st)})
        TB.append(row)
    TB = pd.DataFrame(TB); TB.to_csv(os.path.join(OUT, "cells.csv"), index=False, float_format="%.17g")
    old = pd.read_csv("backtest/resultsYLexit3/cells.csv").set_index("格"); u1 = pd.read_csv("backtest/resultsYLexit3/user_v1/cells.csv").set_index("格")
    CMP = [("user_v1 甲 H40（看警訊）", u1.loc["使用者v1_H40"]), ("seq3 乙挑中 k55_c10_C120（單用乙、一日確認）", old.loc["營量_乙3_k55_c10_C120"]), ("營量 v1", old.loc["營量v1"])]
    S["並列"] = {nm: {sg: [float(r[f"{sg}_年化"]), float(r[f"{sg}_回落"]), r[f"{sg}_標籤"]] for sg in ("探索", "確認", "早年")} for nm, r in CMP}; S["0050"] = Z
    log("[結果] " + "；".join(f"{r.格} 確認 {r.確認_年化:+.2%} {r.確認_標籤}｜早年 {r.早年_年化:+.2%} {r.早年_標籤}｜持有 {r.主_平均持有根數:.0f}" for r in TB.itertuples()))
    # ── 例子
    CX = (55, 10, 120, True)
    sig, _, _, _, _, _, stl_ = inputs(Wm, CX); stl = {(x["sid"], x["e"]): x for x in stl_}
    gmap = {(u, int(e_)): (int(x_), float(g_)) for u, e_, x_, g_ in zip(sig["usid"], sig["entry_pos"], sig["xpos_HX"], sig["g_HX"])}
    base = ctx["sig13"]; orig = {(s_, int(e_)): (int(x_), float(g_)) for s_, e_, x_, g_ in zip(base["sid"], base["entry_pos"], base["xpos_H60"], base["g_H60"])}
    t0c = int(cal.searchsorted(pd.Timestamp("2022-01-03"))); t1c = int(cal.searchsorted(pd.Timestamp("2026-08-24")))
    opn = {}; rows = []
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
    CK = {"k55_c10_C120 看警訊：audit 淨 ＝ 路徑 g − 成本（排程出場者最大差）": float((T["規則淨"] - T["路徑淨"]).abs().max())}
    cats = {"續抱多賺（持有 ＞ 60 天且比原版多賺）": T.apply(lambda r: r["st"]["持有根"] > 60 and r["差"] > 0, axis=1),
            "續抱後確認出場（跌破基準、隔天確認）": T["st"].map(lambda z: z["結束"] == "乙確認出場"),
            "暫出後買回再續抱": T["st"].map(lambda z: z["進"] > 0 and not str(z["結束"]).startswith(("甲放棄", "到上限"))),
            "暫出後放棄": T["st"].map(lambda z: str(z["結束"]).startswith(("甲放棄", "到上限"))),
            "最後出場被確認擋下過": T["st"].map(lambda z: z["擋_出場"] > 0),
            "抱到上限 120 天": T["st"].map(lambda z: z["結束"] == "觸頂上限 C")}
    EX = []
    for cat, msk in cats.items():
        g = T[msk.to_numpy(bool)].sort_values(["差", "t_in"])
        EX.append((cat, g.index[(len(g) - 1) // 2] if len(g) else None, len(g)))
    uni = D.load_universe().set_index("stock_id")["name"]
    dt = lambda t: str(cal[int(t)].date()) if int(t) < len(cal) else "資料尾"
    P = lambda x: "—" if x is None or not np.isfinite(x) else f"{x * 100:+.2f}%"
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0] + "\n.pick{background:#fff4cc}td.l,th.l{text-align:left}"
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>營量出場 使用者版 v2</title>", f"<style>{CSS}</style></head><body><main>", "<h1>營量出場：使用者版 v2（暫出／買回 ＋ 續抱確認出場）</h1>",
         f"<p class='lead'>使用者原話：「{html.escape(RAW)}」<br>⛔ 描述臂：不計 N、不改判定。</p>",
         "<p class='note'>規則：持有中照 v1（跌破成本×0.90、隔天確認才暫出；等 15 天，(a) 或 (b) 可延 10 天；站回或新訊號買回，最多一次）；最後出場改用續抱確認："
         "第 k 天收盤當基準、每 c 天收盤 ≥ 基準就上調；收盤跌破基準、隔天收盤再低於那天最低價才確認，再隔天開盤賣；最多抱 C 天。"
         "⚠ <b>本線讀法、請使用者／台股確認</b>：第 k 天時若在場外，買回那天才開始看基準（基準＝買回那天收盤）；基準啟用後不再看「跌破成本 10% 暫出」；到 C 天仍在場外 ⇒ 放棄。</p>"]
    H.append("<h2>對照表（年化／回落／標籤；都扣成本）</h2><div class='wrap'><table><tr><th class='l'>版本</th><th>探索 17-21</th><th>確認 22-26</th><th>標籤</th><th>早年 12-14</th><th>標籤</th><th>確認對營量 v1〔CI〕</th><th>平均持有</th><th>觸頂 C</th><th>擋下 持有中／出場</th></tr>")
    for r in TB.to_dict("records"):
        H.append(f"<tr class='pick'><td class='l'>v2 k{r['k']} c{r['c']} C{r['C']}（{r['警訊']}警訊）</td><td>{P(r['探索_年化'])}／{P(r['探索_回落'])}</td><td>{P(r['確認_年化'])}／{P(r['確認_回落'])}</td><td>{r['確認_標籤']}</td>"
                 f"<td>{P(r['早年_年化'])}／{P(r['早年_回落'])}</td><td>{r['早年_標籤']}</td><td>{P(r['確認_配對差年化'])}〔{P(r['確認_配對差lo'])}, {P(r['確認_配對差hi'])}〕</td>"
                 f"<td>{r['主_平均持有根數']:.0f} 天</td><td>{r['主_觸頂C比例']:.0%}</td><td>{r['主_擋下_持有中']}／{r['主_擋下_最後出場']}</td></tr>")
    for nm, r in CMP:
        cd = "" if nm == "營量 v1" else f"{P(r['確認_配對差年化'])}〔{P(r['確認_配對差lo'])}, {P(r['確認_配對差hi'])}〕"
        H.append(f"<tr><td class='l'>{nm}</td><td>{P(r['探索_年化'])}／{P(r['探索_回落'])}</td><td>{P(r['確認_年化'])}／{P(r['確認_回落'])}</td><td>{r['確認_標籤']}</td>"
                 f"<td>{P(r['早年_年化'])}／{P(r['早年_回落'])}</td><td>{r['早年_標籤']}</td><td>{cd}</td><td></td><td></td><td></td></tr>")
    H.append(f"<tr><td class='l'>0050</td><td>{P(Z['探索']['cagr'])}／{P(Z['探索']['mdd'])}</td><td>{P(Z['確認']['cagr'])}／{P(Z['確認']['mdd'])}</td><td>—</td><td>{P(Z['早年']['cagr'])}／{P(Z['早年']['mdd'])}</td><td>—</td><td></td><td></td><td></td><td></td></tr></table></div>")
    H.append("<p class='note'>平均持有、觸頂 C、擋下次數 ＝ 主窗 2017～2026 訊號。</p>")
    H.append("<h2>例子（k55 c10 C120、看警訊、確認段實際成交；每類取「差 ＝ 本規則 − 原版」中位那筆）</h2>" + CS.legend_html())
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
                marks.append({"i": t_ - i0, "px": p_, "kind": "exit", "label": f"暫出 {p_:.2f}", "color": "#c62828"})
            elif a_ == "買回":
                marks.append({"i": t_ - i0, "px": p_, "kind": "entry", "label": f"買回 {p_:.2f}", "color": "#ef6c00", "row": 1})
            elif a_ == "放棄":
                marks.append({"i": t_ - i0, "px": p_, "kind": "exit", "label": "放棄、換下一檔", "row": 2})
            else:
                marks.append({"i": t_ - i0, "px": p_, "kind": "exit", "label": f"確認出場 {p_:.2f}"})
        if st["結束"] in ("觸頂上限 C",):
            marks.append({"i": t_out - i0, "px": float(cf[t_out]), "kind": "exit", "label": f"抱滿 120 天 {cf[t_out]:.2f}"})
        hl = [{"px": P0 * 0.9, "label": f"成本×0.90 ＝ {P0 * 0.9:.2f}", "color": "#e65100"}]
        if np.isfinite(st["基準0"]):
            hl.append({"px": float(st["基準0"]), "label": f"起始基準 {st['基準0']:.2f}", "color": "#1565c0"})
            if np.isfinite(st["基準F"]) and st["基準F"] > st["基準0"]:
                hl.append({"px": float(st["基準F"]), "label": f"最終基準 {st['基準F']:.2f}（上調 {st['上調']} 次）", "color": "#0d47a1"})
        if st["乙啟用t"] is not None and i0 <= st["乙啟用t"] <= i1:
            marks.append({"i": st["乙啟用t"] - i0, "px": float(st["基準0"]), "kind": "entry", "label": "開始續抱確認", "color": "#1565c0", "row": 2})
        ma = {kk_: CS.moving_avg(cf, kk_)[sl] for kk_ in (5, 20, 60)}
        svg = CS.kline_svg([str(z.date()) for z in cal[sl]], df["open"].to_numpy(float)[sl], df["high"].to_numpy(float)[sl], df["low"].to_numpy(float)[sl], df["close"].to_numpy(float)[sl],
                           df["volume"].to_numpy(float)[sl] / 1000.0, ma=ma, marks=marks, shade=(t_in - i0, t_out - i0), title=cat, show_title=False, hlines=hl)
        H.append(f"<details class='card' open><summary><b>{html.escape(cat)}</b>｜{s} {html.escape(str(uni.get(s, '')))}｜進場 {dt(t_in)}｜原版 {P(r['原版淨'])} → 本規則 {P(r['規則淨'])}｜差 {r['差'] * 100:+.2f} 點</summary>"
                 f"<div class='meta'>這一類在確認段 {n_} 筆（共 {len(T)} 筆）；取差的中位那筆｜持有 {st['持有根']} 天｜{html.escape(str(st['結束']))}｜暫出 {st['出']}、買回 {st['進']}、擋下 持有中 {st['擋_持有']}／出場 {st['擋_出場']}</div>{svg}</details>")
    H.append("</main></body></html>")
    open(os.path.join(OUT, F_HTML), "w", encoding="utf-8").write("\n".join(H))
    S["例子"] = [{"類": cat, "sid": (T.at[i, "sid"] if i is not None else None), "進場": (dt(T.at[i, "t_in"]) if i is not None else None),
                "原版淨": (float(T.at[i, "原版淨"]) if i is not None else None), "規則淨": (float(T.at[i, "規則淨"]) if i is not None else None), "類筆數": n_} for cat, i, n_ in EX]
    S["例子查核"] = CK
    NL = chr(10)
    R_ = ["# PREREG營量出場 甲件 使用者版 v2（描述臂）" + NL, "使用者原話（逐字）：「" + RAW + "」" + NL,
          "> ⛔ 描述臂：不計 N、不改判定。⚠ 本線讀法 V1～V3（程式開頭）請使用者／台股確認。" + NL,
          "| 版本 | 探索 | 確認 | 確認標籤 | 早年 | 早年標籤 | 確認對營量 v1〔CI〕 | 平均持有 | 觸頂 C | 擋下 持有中／出場 | 上調（平均） |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in TB.to_dict("records"):
        R_.append(f"| k{r['k']} c{r['c']} C{r['C']}（{r['警訊']}警訊） | {P(r['探索_年化'])}／{P(r['探索_回落'])} | {P(r['確認_年化'])}／{P(r['確認_回落'])} | {r['確認_標籤']} | "
                  f"{P(r['早年_年化'])}／{P(r['早年_回落'])} | {r['早年_標籤']} | {P(r['確認_配對差年化'])}〔{P(r['確認_配對差lo'])}, {P(r['確認_配對差hi'])}〕 | {r['主_平均持有根數']:.1f} | {r['主_觸頂C比例']:.1%} | "
                  f"{r['主_擋下_持有中']}／{r['主_擋下_最後出場']} | {r['主_平均上調次數']:.2f} |")
    R_.append(NL + "並列：" + "；".join(f"{nm} 確認 {P(v['確認'][0])}／{P(v['確認'][1])} {v['確認'][2]}、早年 {P(v['早年'][0])} {v['早年'][2]}" for nm, v in S["並列"].items()) + f"；0050 確認 {P(Z['確認']['cagr'])}")
    R_.append(NL + f"閘：{S['閘']}｜例子查核：{CK}｜網頁：{F_HTML}")
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write(NL.join(R_) + NL)
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] 網頁 {os.path.getsize(os.path.join(OUT, F_HTML))} bytes｜{CK}｜例子 {[(c, n) for c, _, n in EX]}｜{time.time() - T0:.0f}s")


if __name__ == "__main__":
    main()
