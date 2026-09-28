# -*- coding: utf-8 -*-
"""營量出場 甲件 使用者版 v1 ＋ W2′（台股 seq332 ③；描述、不計 N、不改判定）。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLexit3_u_w2p [--procs 2]
    簡短查核：~/tw-p16/.venv/bin/python backtest/researchYLexit3_u_w2p_check.py

⭐ 只 import researchYLexit3_u（94f4069edb，另一個子代理所寫，⛔ 不改）：worlds、lowma、inputsU、run_cell、cname 原樣；
   做法 ＝ 在世界的警訊快取 W["WARN"][s]（researchYLexit3.warns 的快取）裡把 "W2" 換成 W2′，其餘（W1、W3、W4、兩天確認、15／25 天、(a)(b)、成本、強制出場、T1）一字不動
W2′（台股 seq332 ③，只用在本描述臂）：有效 K 棒、還原價、原始成交股數
   高檔：c ≥ max(h 前 60 根)×0.95（原條件，researchYLexit3.rmax 同式）且 c ≥ MA60×1.2（MA60 ＝ 收盤 60 根均、含當根）
   長黑：c ＜ o 且 c ÷ c[−1] − 1 ≤ −4%（對前一日收盤）
   爆量：v ≥ vm×2，vm ＝ 前 20 根均量、不含當根（researchYLexit3.vma 同式）
格：甲件 使用者版 v1 H {40, 60, 80}、看警訊（W1、W2′、W3、W4）
並列：原 W2 版、不看警訊版（取自 resultsYLexit3/user_v1 原檔）、營量 v1
閘：警訊換回原 W2（不動快取）⇒ 營量 v1 與 H40／60／80 看警訊版 eq_sha ＝ user_v1/seeds.csv（主、早年）
另報：W2′ 與原 W2 在「營量訊號股」有效 K 棒上的觸發根數（各世界、訊號窗內）；逐列列出「原 W2 判成警訊（整筆因含 W2 的警訊放棄）、W2′ 不判」的筆（主、早年、各 H）
網頁：手機一頁（對照表＋5475 德宏 2025-12-04 那筆的圖）
輸出 backtest/resultsYLexit3/user_v1_w2p/
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
from backtest import researchYLexit3_u as U                  # ⭐ 只 import
from backtest import data as D
from backtest import rerun17 as RR
from backtest import research11 as R11
from backtest import chart_svg as CS

Y3, YX, YB = U.Y3, U.YX, U.YB
OUT = "backtest/resultsYLexit3/user_v1_w2p"
REF = "backtest/resultsYLexit3/user_v1"
F_HTML = "營量出場_使用者版v1_W2p_20260928.html"
CELLS = [(H, True) for H in U.H_S]


def w2p_of(W, s):
    """W2′ 布林陣列（有效 K 棒空間）＋ 除錯欄。"""
    b = R11.load_bars(s, W["mk"].get(s, "twse"), W["cal"])
    idx = b["idx"]; o, h, c = b["o"], b["h"], b["c"]
    v = b["df"]["volume"].to_numpy(float)[idx]
    vm = Y3.vma(v, 20); hh60 = Y3.rmax(h, 60)
    ma60 = pd.Series(c).rolling(60, min_periods=60).mean().to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        r1 = np.r_[np.nan, c[1:] / c[:-1] - 1.0]
        hi = np.isfinite(hh60) & (c >= hh60 * 0.95)
        hi2 = np.isfinite(ma60) & (c >= ma60 * 1.2)
        vol = np.isfinite(vm) & (v >= vm * 2)
        blk = (c < o) & (r1 <= -0.04)
        w2p = hi & hi2 & vol & blk
    return w2p, {"idx": idx, "o": o, "c": c, "hh60": hh60, "ma60": ma60, "v": v, "vm": vm, "r1": r1, "oc": (c - o) / o, "hi": hi, "hi2": hi2, "vol": vol, "blk": blk}


def run_set(tag, worlds, procs, log):
    ROWS = []; DIFF = {}
    for wk, W in worlds:
        W.pop("CU", None)
        row, _, (eqb, _) = U.run_cell((wk, "base")); W["V1EQ"] = eqb; ROWS.append(row)
        with Pool(procs) as pool:
            res = pool.map(U.run_cell, [(wk, c) for c in CELLS])
        for c, (row, diffs, _) in zip(CELLS, res):
            ROWS.append(row)
            for sg, d in diffs.items():
                DIFF[(wk, row["格"], sg)] = d
        for c in CELLS:
            U.inputsU(W, c)                                   # 路徑統計（主行程；快取留著給逐筆比對）
        log(f"[{tag} {wk}] 完成")
    return pd.DataFrame(ROWS), DIFF


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    log(f"===== researchYLexit3_u_w2p {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜使用者版 v1 ＋ W2′（描述、不計 N、不改判定） =====")
    S = {"身分": "使用者版 v1 ＋ W2′（台股 seq332 ③）；描述、不計 N、不改判定", "閘": {}}
    Wm, We, ctx = YB.worlds(log)
    U._W["主"] = Wm; U._W["早年"] = We
    from backtest import researchV as V
    RR.use_snapshot()
    for s in sorted(set(ctx["sig13"]["sid"])):
        U.lowma(Wm, s)
    D.DATA = V.body_paths("main")[0]
    for s in sorted(set(We["SIGH"][("營量", 60)]["sid"])):
        U.lowma(We, s)
    RR.use_snapshot()
    # ── 閘：原 W2 ──
    ref = pd.read_csv(os.path.join(REF, "seeds.csv"), dtype={"eq_sha": str})
    SEED0, DIFF0 = run_set("原W2", (("主", Wm), ("早年", We)), a.procs, log)
    for r in SEED0.to_dict("records"):
        rr = ref[(ref["世界"] == r["世界"]) & (ref["格"] == r["格"])]
        S["閘"][f"{r['世界']}｜{r['格']} ＝ user_v1"] = bool(len(rr) and rr["eq_sha"].iloc[0] == r["eq_sha"])
    log(f"[閘] {S['閘']}")
    ST0 = {wk: {c: {(x["sid"], x["e"]): x for x in U.inputsU(W, c)[6]} for c in CELLS} for wk, W in (("主", Wm), ("早年", We))}
    SIG0 = {wk: {c: U.inputsU(W, c)[0].copy() for c in CELLS} for wk, W in (("主", Wm), ("早年", We))}
    # ── W2′ 換進快取 ──
    DBG = {}; cnt = {}
    for wk, W, data in (("主", Wm, RR.H2D), ("早年", We, V.body_paths("main")[0])):
        D.DATA = data
        n_old = n_new = 0
        a0, a1 = W["w0"], W["w1"]
        for s in sorted(W["WARN"]):
            if W["WARN"][s] is None:
                continue
            wp, dbg = w2p_of(W, s)
            old = W["WARN"][s]["W2"]
            assert len(old) == len(wp), s
            m = (dbg["idx"] >= a0) & (dbg["idx"] <= a1)
            n_old += int(old[m].sum()); n_new += int(wp[m].sum())
            DBG[(wk, s)] = dbg; DBG[(wk, s)]["W2old"] = old
            W["WARN"][s] = {**W["WARN"][s], "W2": wp}
        cnt[wk] = {"原 W2 觸發根": n_old, "W2′ 觸發根": n_new, "檔": len(W["WARN"])}
    RR.use_snapshot()
    TRG = []
    for (wk, s_), dbg in DBG.items():
        calw = (Wm if wk == "主" else We)["cal"]
        wp = (Wm if wk == "主" else We)["WARN"][s_]["W2"]
        for j in np.flatnonzero(dbg["W2old"] | wp):
            TRG.append((wk, s_, str(calw[int(dbg["idx"][j])].date()), bool(dbg["W2old"][j]), bool(wp[j])))
    pd.DataFrame(TRG, columns=["世界", "sid", "日期", "W2", "W2p"]).to_csv(os.path.join(OUT, "w2_triggers.csv.gz"), index=False)
    S["觸發根數（營量訊號股、訊號窗內有效 K 棒）"] = cnt
    log(f"[觸發] {cnt}")
    SEED1, DIFF1 = run_set("W2′", (("主", Wm), ("早年", We)), a.procs, log)
    ST1 = {wk: {c: {(x["sid"], x["e"]): x for x in U.inputsU(W, c)[6]} for c in CELLS} for wk, W in (("主", Wm), ("早年", We))}
    SIG1 = {wk: {c: U.inputsU(W, c)[0] for c in CELLS} for wk, W in (("主", Wm), ("早年", We))}
    # ── 對照表 ──
    Z = json.load(open("backtest/resultsYLexit3/summary.json", encoding="utf-8"))["0050"]
    cal, ecal = Wm["cal"], We["cal"]
    months = {sg: np.array([str(d)[:7] for d in cal[x + 1:y + 1]]) for sg, (x, y) in Wm["SEGP"].items()}
    months["早年"] = np.array([str(d)[:7] for d in ecal[We["w0"] + 1:We["w1"] + 1]])
    old = pd.read_csv(os.path.join(REF, "cells.csv")).set_index("格")
    TB = []
    for c in CELLS:
        k = U.cname(c); row = {"格": k + "_W2p", "H": c[0], "版本": "W2′"}
        for sg, wk in (("探索", "主"), ("確認", "主"), ("早年", "早年")):
            g = SEED1[(SEED1["世界"] == wk) & (SEED1["格"] == k)].iloc[0]
            cc, mm = float(g[f"{sg}_年化"]), float(g[f"{sg}_回落"])
            row.update({f"{sg}_年化": cc, f"{sg}_回落": mm, f"{sg}_比值": cc / abs(mm), f"{sg}_標籤": YX.label(cc, mm, Z[sg])})
            m_, se_ = YX.cr0(DIFF1[(wk, k, sg)], months[sg])
            row.update({f"{sg}_配對差年化": m_ * 245, f"{sg}_配對差lo": (m_ - 1.96 * se_) * 245, f"{sg}_配對差hi": (m_ + 1.96 * se_) * 245})
        for wk in ("主", "早年"):
            W_ = Wm if wk == "主" else We
            st0 = [x for x in ST0[wk][c].values() if W_["w0"] <= x["e"] <= W_["w1"]]; st1 = [x for x in ST1[wk][c].values() if W_["w0"] <= x["e"] <= W_["w1"]]
            row[f"{wk}_W2放棄筆（原）"] = sum(x["放棄"] == "警訊" and "W2" in x["警訊"] for x in st0)
            row[f"{wk}_W2′放棄筆"] = sum(x["放棄"] == "警訊" and "W2" in x["警訊"] for x in st1)
            row[f"{wk}_警訊放棄筆（原／W2′）"] = [sum(x["放棄"] == "警訊" for x in st0), sum(x["放棄"] == "警訊" for x in st1)]
        TB.append(row)
    TB = pd.DataFrame(TB)
    TB.to_csv(os.path.join(OUT, "cells.csv"), index=False, float_format="%.17g")
    pd.concat([SEED0.assign(版本="原W2"), SEED1.assign(版本="W2′")]).to_csv(os.path.join(OUT, "seeds.csv"), index=False, float_format="%.17g")
    PAR = {}
    for c in CELLS:
        for suf, nm in (("", "原 W2 版"), ("_不看警訊", "不看警訊版")):
            r = old.loc[f"使用者v1_H{c[0]}{suf}"]
            PAR[f"H{c[0]} {nm}"] = {sg: [float(r[f"{sg}_年化"]), float(r[f"{sg}_回落"]), r[f"{sg}_標籤"]] for sg in ("探索", "確認", "早年")}
            PAR[f"H{c[0]} {nm}"]["確認配對差"] = [float(r["確認_配對差年化"]), float(r["確認_配對差lo"]), float(r["確認_配對差hi"])]
    v1 = SEED0[(SEED0["格"] == "營量v1")]
    PAR["營量 v1"] = {sg: [float(v1[v1["世界"] == ("早年" if sg == "早年" else "主")][f"{sg}_年化"].iloc[0]), float(v1[v1["世界"] == ("早年" if sg == "早年" else "主")][f"{sg}_回落"].iloc[0])]
                    for sg in ("探索", "確認", "早年")}
    S["並列"] = PAR; S["0050"] = Z
    # ── 逐筆：原 W2 判成警訊、W2′ 不判（持有窗 [進場根, 出場根] 內的每一根；另標該根有沒有造成原版放棄）──
    names = D.load_universe().set_index("stock_id")["name"]
    rows = []
    for wk, W_ in (("主", Wm), ("早年", We)):
        calw = W_["cal"]; n0 = len(calw)
        for c in CELLS:
            g0 = SIG0[wk][c]; g1 = SIG1[wk][c]
            for key, x0 in ST0[wk][c].items():
                s, e = key
                if not (W_["w0"] <= e <= W_["w1"]) or (wk, s) not in DBG:
                    continue
                dbg = DBG[(wk, s)]; idx = dbg["idx"]
                r0 = g0[(g0["usid"] == s) & (g0["entry_pos"] == e)].iloc[0]; r1_ = g1[(g1["usid"] == s) & (g1["entry_pos"] == e)].iloc[0]
                xe = int(r0[f"xpos_H{c[0]}"]); xe = min(xe, n0 - 1)
                ja, jb = int(np.searchsorted(idx, e)), int(np.searchsorted(idx, xe, side="right")) - 1
                t_ab = [t for a_, t, _ in x0["事件"] if a_ == "放棄"]
                jw = (int(np.searchsorted(idx, t_ab[0])) - 1) if (t_ab and x0["放棄"] == "警訊" and "W2" in x0["警訊"]) else None
                x1 = ST1[wk][c].get(key)
                for j in range(ja, jb + 1):
                    if not (dbg["W2old"][j] and not W_["WARN"][s]["W2"][j]):
                        continue
                    why = [nm for nm, f in (("高檔 MA60×1.2", "hi2"), ("高檔 60 高×0.95", "hi"), ("爆量", "vol"), ("長黑（對前收 −4%）", "blk")) if not dbg[f][j]]
                    eff = "原版因此放棄" if j == jw else ("當天成立但沒有作用（不在確認賣出／暫出期間）")
                    rows.append({"世界": wk, "H": c[0], "sid": s, "名稱": str(names.get(s, "")), "進場": str(calw[e].date()), "警訊根": str(calw[int(idx[j])].date()),
                                 "原版作用": eff, "c": float(dbg["c"][j]), "o": float(dbg["o"][j]), "對前收": float(dbg["r1"][j]), "(c−o)/o": float(dbg["oc"][j]),
                                 "60高×0.95": float(dbg["hh60"][j] * 0.95), "MA60×1.2": float(dbg["ma60"][j] * 1.2), "v÷vm": float(dbg["v"][j] / dbg["vm"][j]) if dbg["vm"][j] else np.nan,
                                 "W2′ 不成立的條件": "、".join(why), "原結果 g": float(r0[f"g_H{c[0]}"]), "W2′ 結果 g": float(r1_[f"g_H{c[0]}"]),
                                 "W2′ 路徑": (x1["放棄"] or ("站回買回" if x1["進"] else "到期")) if x1 and x1["出"] else "沒暫出、到期",
                                 "_e": int(e), "_j": int(idx[j]), "_ev0": x0["事件"], "_ev1": x1["事件"] if x1 else []})
    L = pd.DataFrame(rows).sort_values(["世界", "H", "進場", "sid"]) if rows else pd.DataFrame()
    if len(L):
        L.drop(columns=["_ev0", "_ev1"]).to_csv(os.path.join(OUT, "w2_dropped.csv"), index=False, float_format="%.10g")
    hit = L[(L["sid"] == "5475") & (L["警訊根"] == "2025-12-04")] if len(L) else L
    S["逐筆（原 W2 判、W2′ 不判）筆數"] = {f"{wk} H{H}": int(((L["世界"] == wk) & (L["H"] == H)).sum()) for wk in ("主", "早年") for H in U.H_S} if len(L) else {}
    S["其中造成原版放棄"] = {f"{wk} H{H}": int(((L["世界"] == wk) & (L["H"] == H) & (L["原版作用"] == "原版因此放棄")).sum()) for wk in ("主", "早年") for H in U.H_S} if len(L) else {}
    tj = pd.read_csv("backtest/resultsYLexit3/view/trades_jia_seed0.csv", dtype={"sid": str})
    q = tj[(tj["sid"] == "5475") & (tj["t_in"].astype(int) == int(cal.searchsorted(pd.Timestamp("2025-12-04"))))]
    S["德宏在 seq3 挑中格（b5_H40）"] = q[["事件", "結果", "規則淨", "原版淨"]].to_dict("records")
    S["5475 德宏 2025-12-04 在清單內"] = bool(len(hit))
    log(f"[逐筆] {S['逐筆（原 W2 判、W2′ 不判）筆數']}｜德宏 {S['5475 德宏 2025-12-04 在清單內']}")
    # ── 網頁 ──
    P = lambda x: "—" if x is None or not np.isfinite(x) else f"{x * 100:+.2f}%"
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0] + "\n.pick{background:#fff4cc}td.l,th.l{text-align:left}"
    Hh = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
          "<title>使用者版 v1 換 W2′</title>", f"<style>{CSS}</style></head><body><main>", "<h1>營量出場 使用者版 v1：高檔爆量長黑改用 W2′</h1>",
          "<p class='lead'>W2′：高檔（收盤 ≥ 前 60 根最高×0.95，<b>而且</b> 收盤 ≥ MA60×1.2）＋ 爆量（量 ≥ 前 20 根均量×2）＋ 長黑（收黑，<b>而且</b> 對前一日收盤跌 ≥ 4%）。"
          "<br>⛔ 描述臂：不計 N、不改判定。</p>",
          "<h2>對照表（年化／回落，扣成本）</h2><div class='wrap'><table><tr><th class='l'>版本</th><th>探索 17-21</th><th>確認 22-26</th><th>標籤</th><th>早年 12-14</th><th>標籤</th><th>確認對營量 v1〔CI〕</th></tr>"]
    for r in TB.to_dict("records"):
        Hh.append(f"<tr class='pick'><td class='l'>H{r['H']} W2′</td><td>{P(r['探索_年化'])}／{P(r['探索_回落'])}</td><td>{P(r['確認_年化'])}／{P(r['確認_回落'])}</td><td>{r['確認_標籤']}</td>"
                  f"<td>{P(r['早年_年化'])}／{P(r['早年_回落'])}</td><td>{r['早年_標籤']}</td><td>{P(r['確認_配對差年化'])}〔{P(r['確認_配對差lo'])}, {P(r['確認_配對差hi'])}〕</td></tr>")
        for nm in ("原 W2 版", "不看警訊版"):
            p_ = PAR[f"H{r['H']} {nm}"]
            Hh.append(f"<tr><td class='l'>H{r['H']} {nm}</td><td>{P(p_['探索'][0])}／{P(p_['探索'][1])}</td><td>{P(p_['確認'][0])}／{P(p_['確認'][1])}</td><td>{p_['確認'][2]}</td>"
                      f"<td>{P(p_['早年'][0])}／{P(p_['早年'][1])}</td><td>{p_['早年'][2]}</td><td>{P(p_['確認配對差'][0])}〔{P(p_['確認配對差'][1])}, {P(p_['確認配對差'][2])}〕</td></tr>")
    v_ = PAR["營量 v1"]
    Hh.append(f"<tr><td class='l'>營量 v1</td><td>{P(v_['探索'][0])}／{P(v_['探索'][1])}</td><td>{P(v_['確認'][0])}／{P(v_['確認'][1])}</td><td></td><td>{P(v_['早年'][0])}／{P(v_['早年'][1])}</td><td></td><td></td></tr>")
    Hh.append(f"<tr><td class='l'>0050</td><td>{P(Z['探索']['cagr'])}／{P(Z['探索']['mdd'])}</td><td>{P(Z['確認']['cagr'])}／{P(Z['確認']['mdd'])}</td><td></td><td>{P(Z['早年']['cagr'])}／{P(Z['早年']['mdd'])}</td><td></td><td></td></tr></table></div>")
    Hh.append(f"<p class='note'>觸發根數（營量訊號股、訊號窗內）：主 原 W2 {cnt['主']['原 W2 觸發根']} 根 → W2′ {cnt['主']['W2′ 觸發根']} 根；早年 {cnt['早年']['原 W2 觸發根']} → {cnt['早年']['W2′ 觸發根']}。"
              f"因 W2 放棄的筆（主，H40／60／80）：原 {'／'.join(str(r['主_W2放棄筆（原）']) for r in TB.to_dict('records'))} → W2′ {'／'.join(str(r['主_W2′放棄筆']) for r in TB.to_dict('records'))}。</p>")
    if len(L):
        LV = L[(L["原版作用"] == "原版因此放棄") | ((L["sid"] == "5475") & (L["警訊根"] == "2025-12-04"))]
        Hh.append(f"<h2>原 W2 判成警訊、W2′ 不判的筆</h2><p class='note'>持有期間內這種 K 棒共 {len(L)} 根（{json.dumps(S['逐筆（原 W2 判、W2′ 不判）筆數'], ensure_ascii=False)}）；"
                  f"真的造成原版放棄的只有 {int((L['原版作用'] == '原版因此放棄').sum())} 根。下表只列這些，外加德宏那根；全部見 w2_dropped.csv。</p>")
        Hh.append("<div class='wrap'><table><tr><th class='l'>世界 H</th><th class='l'>股票</th><th>進場</th><th>警訊根</th><th>對前收</th><th>收÷MA60</th><th class='l'>W2′ 不成立</th><th class='l'>原版作用</th><th>原結果</th><th>W2′ 結果</th></tr>")
        for r in LV.to_dict("records"):
            pk = " class='pick'" if (r["sid"] == "5475" and r["警訊根"] == "2025-12-04") else ""
            Hh.append(f"<tr{pk}><td class='l'>{r['世界']} H{r['H']}</td><td class='l'>{r['sid']} {html.escape(r['名稱'])}</td><td>{r['進場']}</td><td>{r['警訊根']}</td><td>{P(r['對前收'])}</td>"
                      f"<td>{r['c'] / (r['MA60×1.2'] / 1.2):.3f}</td><td class='l'>{html.escape(r['W2′ 不成立的條件'])}</td><td class='l'>{html.escape(r['原版作用'])}</td><td>{P(r['原結果 g'])}</td><td>{P(r['W2′ 結果 g'])}（{html.escape(str(r['W2′ 路徑']))}）</td></tr>")
        Hh.append("</table></div>")
    if len(hit):
        r = hit.sort_values("H").iloc[0]; s = "5475"; e = r["_e"]; tj = r["_j"]
        df = D.load_stock(s, Wm["mk"].get(s, "twse"), cal).df; cf = pd.Series(df["close"].to_numpy(float)).ffill().to_numpy()
        i0 = max(0, e - 40); i1 = min(len(cal) - 1, tj + 45); sl = slice(i0, i1 + 1)
        P0 = float(Wm["opens"][s][e])
        marks = [{"i": e - i0, "px": P0, "kind": "entry", "label": f"進 {P0:.2f}"},
                 {"i": tj - i0, "px": float(df["high"].to_numpy(float)[tj]), "kind": "exit", "label": "原 W2 判警訊", "color": "#c62828", "row": 2}]
        for a_, t_, p_ in r["_ev0"]:
            if a_ == "放棄" and i0 <= t_ <= i1:
                marks.append({"i": t_ - i0, "px": p_, "kind": "exit", "label": "原版：放棄", "color": "#888888", "row": 1})
        for a_, t_, p_ in r["_ev1"]:
            if i0 <= t_ <= i1:
                marks.append({"i": t_ - i0, "px": p_, "kind": "entry" if a_ == "買回" else "exit", "label": f"W2′：{a_} {p_:.2f}", "color": "#1565c0", "row": 0})
        ma = {k: CS.moving_avg(cf, k)[sl] for k in (5, 20, 60)}
        hl = [{"px": P0 * 0.9, "label": f"成本×0.90 ＝ {P0 * 0.9:.2f}", "color": "#e65100"}, {"px": P0, "label": f"成本 {P0:.2f}", "color": "#1565c0"},
              {"px": r["MA60×1.2"], "label": f"MA60×1.2 ＝ {r['MA60×1.2']:.2f}（警訊根）", "color": "#6a1b9a"}]
        svg = CS.kline_svg([str(z.date()) for z in cal[sl]], df["open"].to_numpy(float)[sl], df["high"].to_numpy(float)[sl], df["low"].to_numpy(float)[sl], df["close"].to_numpy(float)[sl],
                           df["volume"].to_numpy(float)[sl] / 1000.0, ma=ma, marks=marks, title="5475 德宏", show_title=False, hlines=hl)
        s3 = S["德宏在 seq3 挑中格（b5_H40）"]
        s3t = (f"seq3 挑中格（b5_H40）這一筆：{html.escape(str(s3[0]['事件']))}，{html.escape(str(s3[0]['結果']))}（本規則 {P(float(s3[0]['規則淨']))}、原版 {P(float(s3[0]['原版淨']))}）；"
               "W2′ 下這一根不算警訊。使用者版 v1 要收盤 ＜ 成本×0.90 且隔天確認才賣，這筆沒跌到那裡，W2 當天成立但沒有作用。") if s3 else ""
        Hh.append("<h2>5475 德宏：2025-12-04 那一根</h2>" + f"<p class='note'>{s3t}</p>" + CS.legend_html() +
                  f"<div class='meta'>進場 {r['進場']}（H{int(r['H'])}）｜警訊根收盤 {r['c']:.2f}、開盤 {r['o']:.2f}、對前收 {P(r['對前收'])}、(收−開)÷開 {P(r['(c−o)/o'])}｜"
                  f"60 高×0.95 ＝ {r['60高×0.95']:.2f}、MA60×1.2 ＝ {r['MA60×1.2']:.2f}、量 ÷ 均量 ＝ {r['v÷vm']:.2f}｜W2′ 不成立：{html.escape(r['W2′ 不成立的條件'])}｜"
                  f"結果 原 {P(r['原結果 g'])} → W2′ {P(r['W2′ 結果 g'])}</div>{svg}")
    Hh.append("</main></body></html>")
    open(os.path.join(OUT, F_HTML), "w", encoding="utf-8").write("\n".join(Hh))
    # ── REPORT ──
    NL = chr(10)
    R_ = ["# 營量出場 甲件 使用者版 v1 ＋ W2′（描述臂）" + NL, "> 台股 seq332 ③：W2′ 只用在描述臂；⛔ 不計 N、不改判定。" + NL,
          "| 版本 | 探索 | 確認 | 確認標籤 | 早年 | 早年標籤 | 確認對營量 v1〔CI〕 | 因 W2 放棄筆 主（原→W2′） |", "|---|---|---|---|---|---|---|---|"]
    for r in TB.to_dict("records"):
        R_.append(f"| H{r['H']} W2′ | {P(r['探索_年化'])}／{P(r['探索_回落'])} | {P(r['確認_年化'])}／{P(r['確認_回落'])} | {r['確認_標籤']} | {P(r['早年_年化'])}／{P(r['早年_回落'])} | {r['早年_標籤']} | "
                  f"{P(r['確認_配對差年化'])}〔{P(r['確認_配對差lo'])}, {P(r['確認_配對差hi'])}〕 | {r['主_W2放棄筆（原）']}→{r['主_W2′放棄筆']} |")
        for nm in ("原 W2 版", "不看警訊版"):
            p_ = PAR[f"H{r['H']} {nm}"]
            R_.append(f"| H{r['H']} {nm} | {P(p_['探索'][0])}／{P(p_['探索'][1])} | {P(p_['確認'][0])}／{P(p_['確認'][1])} | {p_['確認'][2]} | {P(p_['早年'][0])}／{P(p_['早年'][1])} | {p_['早年'][2]} | "
                      f"{P(p_['確認配對差'][0])}〔{P(p_['確認配對差'][1])}, {P(p_['確認配對差'][2])}〕 | |")
    R_.append(f"| 營量 v1 | {P(v_['探索'][0])}／{P(v_['探索'][1])} | {P(v_['確認'][0])}／{P(v_['確認'][1])} | | {P(v_['早年'][0])}／{P(v_['早年'][1])} | | | |")
    R_ += [NL + f"觸發根數：{json.dumps(cnt, ensure_ascii=False)}", f"原 W2 判、W2′ 不判的筆：{json.dumps(S['逐筆（原 W2 判、W2′ 不判）筆數'], ensure_ascii=False)}（明細 w2_dropped.csv）；"
           f"5475 德宏 2025-12-04 在清單內：{S['5475 德宏 2025-12-04 在清單內']}；其中造成原版放棄：{json.dumps(S['其中造成原版放棄'], ensure_ascii=False)}；德宏在 seq3 挑中格：{json.dumps(S['德宏在 seq3 挑中格（b5_H40）'], ensure_ascii=False)}", f"閘（W2′ 換回 W2 ＝ user_v1 逐位元）：{json.dumps(S['閘'], ensure_ascii=False)}", f"網頁：{F_HTML}"]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write(NL.join(R_) + NL)
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    bad = not all(S["閘"].values())
    log(f"[完] 閘 {'不過' if bad else '過'}｜網頁 {os.path.getsize(os.path.join(OUT, F_HTML))} bytes")
    if bad:
        raise SystemExit("⛔ 閘不過")


if __name__ == "__main__":
    main()
