# -*- coding: utf-8 -*-
"""營量 v1 跌破停損、直接換下一檔（使用者問；描述臂：不計 N、不改任何判定）。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLstop [--procs 2]
    簡短查核：~/tw-p16/.venv/bin/python backtest/researchYLstop_check.py

使用者原話（逐字）：「我如果跌破10%是不是直接換下一檔比較有效？」
⭐ 先驗提醒（裁定 seq266 §二）：本專案停損類（營飆停損、回測 研究五／六、四類單獨）全部不如抱著。
═══ 規則（協調者轉述）＋ 本線讀法（S 標；看數字前寫死）═══
 營量 v1（T1、20 檔、relvol、stop_force 開）持有中：
   一日版：第 j 根收盤 ＜ 成本×(1−b) ⇒ 第 j＋1 根開盤賣出；名額當天釋出、照引擎當天候選（relvol 排序）接新股；不等、不買回
   兩日確認版：第 d 根收盤 ＜ 成本×(1−b)（跌破）；第 d＋1 根收盤 ＜ 第 d 根最低價 ⇒ 確認、第 d＋2 根開盤賣；沒確認 ⇒ 不賣、之後再跌破重算（同 user_v1 U1）
   沒停損 ⇒ 第 H 根收盤出（H40／H80 ＝ fixed_exit＋T1，H60 ＝ AND 表原值）
 S1 停損只看「進場根 … 第 H 根前一根」的收盤（第 H 根收盤觸發的不執行）；成本 ＝ 進場開盤；還原價、有效 K 棒
 S2 「接當時的候選」＝ 引擎原本就在出場當天先結清、再照當天訊號（entry_pos ＝ 當天）依 relvol 進場；⛔ 不排隊、不回頭找前幾天的訊號（同營量 v1 queue_days＝0）
 S3 只改每筆 xpos／g（真實代號、不需合成序列），引擎一字不動
 格：b {5, 7, 10, 15%} × H {40, 60, 80} × {一日, 兩日確認} ＝ 24
 每格報：三段年化／回落／標籤、對營量 v1 同段配對差（95% CI）、觸發率（窗內訊號被停損的比例）
 另報（主窗、種子 0、組合實際成交）：
   釋出名額有接到新股的比例 ＝ 停損賣出那天同日有新買進的停損筆 ÷ 停損筆（另報同日買進數 ÷ 同日停損數）
   被停損那批如果不停損、抱到 H 的報酬（扣成本）vs 停損實際報酬（扣成本）
 並列：b 掃描版（等 10 天買回那套，bsweep bcurve 同 b、H）、營量 v1、0050
 閘：營量 v1 ＝ resultsYLexit3 種子 0（主、早年）；營量不抽籤 ⇒ 1 顆
 網頁：對照表＋ b10_H60（一日版）4 張例子（確認段、組合實際成交；各類取「差」中位那筆）：
   停損後躲過大跌（被停損、原版抱到 H 更差）、停損後反彈（原版抱到 H 更好）、換到的新股賺、換到的新股虧（停損當天同日買進的新部位）
輸出 backtest/resultsYLstop/
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
from backtest import researchYLexit3_b as YB
from backtest import chart_svg as CS

OUT = "backtest/resultsYLstop"
F_HTML = "營量跌破停損換股_20260928.html"
COST = R11.COST
RAW = "我如果跌破10%是不是直接換下一檔比較有效？"
B_S = (0.05, 0.07, 0.10, 0.15); H_S = (40, 60, 80)
_W: dict = {}


def lows(W, s):
    C_ = W.setdefault("LOW", {})
    if s not in C_:
        C_[s] = R11.load_bars(s, W["mk"].get(s, "twse"), W["cal"])["l"]
    return C_[s]


def stop_sig(W, H, b, two):
    """回（改好 xpos／g 的表, 每筆資訊）。"""
    base = W["SIGH"][("營量", H)]; xs, gs = f"xpos_H{H}", f"g_H{H}"
    S2 = base.copy(); X = S2[xs].to_numpy(np.int64).copy(); G = S2[gs].to_numpy(float).copy()
    info = []
    for i, (s, k, e, x0, g0) in enumerate(zip(S2["sid"], S2["k"].astype(int), S2["entry_pos"].astype(int), X.copy(), G.copy())):
        rec = {"sid": s, "e": int(e), "停損": False, "原xpos": int(x0), "原g": float(g0), "擋": 0}
        B = YX.bars_of(W, s)
        if B is None or x0 < 0:
            info.append(rec); continue
        idx, o, c, _, _, _ = B; lo = lows(W, s); n0 = len(W["cal"])
        ke = k + 1; kx = int(np.searchsorted(idx, min(x0, n0 - 1), side="right") - 1); P0 = o[ke]
        cand = None; hit = None
        for j in range(ke, kx):
            if not two:
                if c[j] < P0 * (1 - b):
                    hit = j; break
            else:
                if cand is not None and c[j] < lo[cand]:
                    hit = j; break
                if cand is not None:
                    rec["擋"] += 1
                cand = j if c[j] < P0 * (1 - b) else None
        if hit is not None and hit + 1 <= kx:
            X[i] = int(idx[hit + 1]); G[i] = o[hit + 1] / P0 - 1.0; rec.update({"停損": True, "觸發t": int(idx[hit]), "賣t": int(idx[hit + 1])})
        info.append(rec)
    S2[xs] = X; S2[gs] = G
    return S2, info


def cname(cell):
    b, H, two = cell
    return f"停損_b{int(round(b * 100))}_H{H}" + ("_兩日確認" if two else "")


def inputs(W, cell):
    Cc = W.setdefault("CS", {})
    if cell not in Cc:
        Cc[cell] = stop_sig(W, cell[1], cell[0], cell[2])
    return Cc[cell]


def run_cell(job):
    wk, cell = job
    W = _W[wk]
    if cell == "base":
        sig, rule, nm = W["SIGH"][("營量", 60)], "H60", "營量v1"
    else:
        sig, _ = inputs(W, cell); rule, nm = f"H{cell[1]}", cname(cell)
    o, aud = YX._eng(W, "營量", sig, rule, 7000)
    row, eq, _ = YX._stats(W, o, aud, W["SEGP"], 20)
    row.update({"世界": wk, "格": nm, "eq_sha": YX.sha(eq)})
    diffs = {}
    if W.get("V1EQ") is not None and cell != "base":
        V1 = W["V1EQ"]
        for sg, (x, y) in W["SEGP"].items():
            diffs[sg] = (eq[x + 1:y + 1] / eq[x:y] - 1.0) - (V1[x + 1:y + 1] / V1[x:y] - 1.0)
    return row, diffs, aud


def trades(aud):
    op = {}; rows = []
    for a in sorted(aud, key=lambda z: (z["t"], z["side"] != "sell")):
        if a["side"] == "buy":
            op[a["sid"]] = a
        else:
            b = op.pop(a["sid"])
            rows.append({"sid": a["sid"], "t_in": b["t"], "t_out": a["t"], "淨": a["amt"] / b["amt"] - 1 - a["cost"] / b["amt"]})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    log(f"===== researchYLstop {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜跌破停損換股（描述臂、不計 N、不改判定） =====")
    S = {"身分": "描述臂、不計 N、不改任何判定", "使用者原話": RAW, "先驗提醒": "本專案停損類（營飆停損、回測 研究五／六、四類單獨）全部不如抱著", "閘": {}}
    Wm, We, ctx = YB.worlds(log)
    _W["主"] = Wm; _W["早年"] = We
    RR.use_snapshot()
    for s in sorted(set(ctx["sig13"]["sid"])):
        lows(Wm, s)
    from backtest import researchV as V
    D.DATA = V.body_paths("main")[0]
    for s in sorted(set(We["SIGH"][("營量", 60)]["sid"])):
        lows(We, s)
    RR.use_snapshot()
    CELLS = [(b, H, two) for two in (False, True) for b in B_S for H in H_S]
    ref = pd.read_csv("backtest/resultsYLexit3/seeds.csv.gz", dtype={"eq_sha": str}, low_memory=False)
    ROWS = []; DIFF = {}; AUD = {}
    for wk, W in (("主", Wm), ("早年", We)):
        row, _, audb = run_cell((wk, "base"))
        W["V1EQ"] = None
        o, _ = YX._eng(W, "營量", W["SIGH"][("營量", 60)], "H60", 7000); W["V1EQ"] = np.asarray(o["equity"], float); ROWS.append(row)
        rr = ref[(ref["世界"] == wk) & (ref["格"] == "營量v1") & (ref["r"] == 0)]["eq_sha"].iloc[0]
        S["閘"][f"{wk}｜營量 v1 ＝ resultsYLexit3 種子 0"] = bool(row["eq_sha"] == rr)
        with Pool(a.procs) as pool:
            res = pool.map(run_cell, [(wk, c) for c in CELLS])
        for c, (row, diffs, aud) in zip(CELLS, res):
            ROWS.append(row)
            for sg, d in diffs.items():
                DIFF[(wk, row["格"], sg)] = d
            if wk == "主":
                AUD[c] = aud
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
        k = cname(c); row = {"格": k, "b": c[0], "H": c[1], "版本": "兩日確認" if c[2] else "一日"}
        for sg, wk in (("探索", "主"), ("確認", "主"), ("早年", "早年")):
            g = SEED[(SEED["世界"] == wk) & (SEED["格"] == k)].iloc[0]
            cc, mm = float(g[f"{sg}_年化"]), float(g[f"{sg}_回落"])
            row.update({f"{sg}_年化": cc, f"{sg}_回落": mm, f"{sg}_比值": cc / abs(mm), f"{sg}_標籤": YX.label(cc, mm, Z[sg])})
            m_, se_ = YX.cr0(DIFF[(wk, k, sg)], months[sg])
            row[f"{sg}_配對差年化"] = m_ * 245
            if sg == "確認":
                row["確認_配對差lo"] = (m_ - 1.96 * se_) * 245; row["確認_配對差hi"] = (m_ + 1.96 * se_) * 245
        for wk, W in (("主", Wm), ("早年", We)):
            inf = [x for x in inputs(W, c)[1] if W["w0"] <= x["e"] <= W["w1"] and x["原xpos"] >= 0]
            row[f"{wk}_觸發率"] = float(np.mean([x["停損"] for x in inf])); row[f"{wk}_擋下次數"] = sum(x["擋"] for x in inf)
        # 組合實際成交（主、種子 0）
        TR = trades(AUD[c]); infm = {(x["sid"], x["e"]): x for x in inputs(Wm, c)[1]}
        buys = pd.Series([z["t"] for z in AUD[c] if z["side"] == "buy"]).value_counts().to_dict()
        stops = []
        for r in TR.itertuples():
            x = infm.get((r.sid, int(r.t_in)))
            if x and x["停損"] and x.get("賣t") == r.t_out:
                stops.append((r.t_out, r.淨, x["原g"] - COST))
        sd = pd.Series([t for t, _, _ in stops]).value_counts().to_dict()
        row["主_組合停損筆"] = len(stops)
        row["主_釋出後同日有接新股的停損筆比例"] = float(np.mean([buys.get(t, 0) > 0 for t, _, _ in stops])) if stops else np.nan
        row["主_同日買進數÷同日停損數"] = float(sum(min(buys.get(t, 0), n) for t, n in sd.items()) / max(sum(sd.values()), 1))
        row["主_被停損那批：停損實際（扣成本）"] = float(np.mean([s_ for _, s_, _ in stops])) if stops else np.nan
        row["主_被停損那批：不停損抱到H（扣成本）"] = float(np.mean([h_ for _, _, h_ in stops])) if stops else np.nan
        TB.append(row)
    TB = pd.DataFrame(TB); TB.to_csv(os.path.join(OUT, "cells.csv"), index=False, float_format="%.17g")
    bs = pd.read_csv("backtest/resultsYLexit3/bsweep/bcurve.csv").set_index("格"); old = pd.read_csv("backtest/resultsYLexit3/cells.csv").set_index("格")
    S["0050"] = Z; S["營量v1"] = {sg: [float(old.loc["營量v1", f"{sg}_年化"]), float(old.loc["營量v1", f"{sg}_回落"]), old.loc["營量v1", f"{sg}_標籤"]] for sg in ("探索", "確認", "早年")}
    log("[結果] " + "；".join(f"{r.格} 確認 {r.確認_年化:+.2%} {r.確認_標籤}｜差 {r.確認_配對差年化:+.2%}" for r in TB.itertuples()))
    # ── 例子（b10_H60 一日版）
    CX = (0.10, 60, False)
    TR = trades(AUD[CX]); infm = {(x["sid"], x["e"]): x for x in inputs(Wm, CX)[1]}
    t0c = int(cal.searchsorted(pd.Timestamp("2022-01-03"))); t1c = int(cal.searchsorted(pd.Timestamp("2026-08-24")))
    base = ctx["sig13"]; orig = {(s_, int(e_)): (int(x_), float(g_)) for s_, e_, x_, g_ in zip(base["sid"], base["entry_pos"], base["xpos_H60"], base["g_H60"])}
    TR = TR[(TR["t_in"] >= t0c) & (TR["t_in"] <= t1c)].copy()
    TR["停損"] = [bool(infm.get((r.sid, int(r.t_in)), {}).get("停損")) and infm[(r.sid, int(r.t_in))].get("賣t") == r.t_out for r in TR.itertuples()]
    TR["原版淨"] = [orig[(r.sid, int(r.t_in))][1] - COST for r in TR.itertuples()]
    TR["差"] = TR["淨"] - TR["原版淨"]
    sgs = TR[TR["停損"]]
    stop_days = set(sgs["t_out"])
    newp = TR[TR["t_in"].isin(stop_days) & ~TR["停損"]].copy()
    # 新股對應被停損的（同日）
    CK = {}
    sig10 = inputs(Wm, CX)[0]; gm = {(s_, int(e_)): float(g_) for s_, e_, g_ in zip(sig10["sid"], sig10["entry_pos"], sig10["g_H60"])}
    CK["b10_H60：停損筆 audit 淨 ＝ 開盤賣 g − 成本（最大差）"] = float(max([abs(r.淨 - (gm[(r.sid, int(r.t_in))] - COST)) for r in sgs.itertuples()] + [0.0]))
    cats = [("停損後躲過大跌（原版抱到 60 天更差）", sgs[sgs["差"] > 0]), ("停損後反彈（原版抱到 60 天更好）", sgs[sgs["差"] < 0]),
            ("換到的新股賺", newp[newp["淨"] > 0]), ("換到的新股虧", newp[newp["淨"] <= 0])]
    EX = []
    for cat, g in cats:
        key = "差" if cat.startswith("停損") else "淨"
        g = g.sort_values([key, "t_in"])
        EX.append((cat, g.index[(len(g) - 1) // 2] if len(g) else None, len(g), key))
    uni = D.load_universe().set_index("stock_id")["name"]
    dt = lambda t: str(cal[int(t)].date()) if int(t) < len(cal) else "資料尾"
    P = lambda x: "—" if x is None or not np.isfinite(x) else f"{x * 100:+.2f}%"
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0] + "\n.pick{background:#fff4cc}td.l,th.l{text-align:left}"
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>營量 跌破停損換股</title>", f"<style>{CSS}</style></head><body><main>", "<h1>營量 v1：跌破就停損、直接換下一檔</h1>",
         f"<p class='lead'>使用者原話：「{html.escape(RAW)}」<br>⛔ 描述臂：不計 N、不改任何判定。⚠ 先驗提醒：{S['先驗提醒']}。</p>",
         "<p class='note'>規則：收盤 ＜ 成本×(1−b) ⇒ 隔天開盤賣，名額當天照營量 v1 的挑法（relvol）接當天的新訊號；不等、不買回；沒停損就抱到第 H 天。"
         "「兩日確認」版：跌破後隔天收盤再低於跌破那天最低價才賣。本線讀法：當天沒有新訊號就空著（營量 v1 本來就不排隊）。都扣成本。</p>"]
    v1 = S["營量v1"]
    H.append("<h2>對照表</h2>")
    for two in (False, True):
        H.append(f"<h3>{'兩日確認版' if two else '一日版'}</h3><div class='wrap'><table><tr><th class='l'>b、H</th><th>探索</th><th>確認</th><th>標籤</th><th>早年</th><th>標籤</th><th>確認對營量 v1〔CI〕</th><th>觸發率</th><th>接到新股</th><th>被停損批：停損／不停損抱到 H</th><th>b 掃描版（等 10 天買回）確認</th></tr>")
        for r in TB[TB["版本"] == ("兩日確認" if two else "一日")].to_dict("records"):
            kb = f"營量_甲3_b{int(round(r['b'] * 100))}_H{r['H']}"
            bsv = f"{P(bs.loc[kb, '確認_年化'])}（{bs.loc[kb, '確認_標籤']}）" if kb in bs.index else "—"
            c_ = "pick" if (r["b"] == 0.10 and r["H"] == 60 and not two) else ""
            H.append(f"<tr class='{c_}'><td class='l'>{int(round(r['b'] * 100))}%、{r['H']} 天</td><td>{P(r['探索_年化'])}／{P(r['探索_回落'])}</td><td>{P(r['確認_年化'])}／{P(r['確認_回落'])}</td><td>{r['確認_標籤']}</td>"
                     f"<td>{P(r['早年_年化'])}／{P(r['早年_回落'])}</td><td>{r['早年_標籤']}</td><td>{P(r['確認_配對差年化'])}〔{P(r['確認_配對差lo'])}, {P(r['確認_配對差hi'])}〕</td>"
                     f"<td>{r['主_觸發率']:.0%}</td><td>{r['主_釋出後同日有接新股的停損筆比例']:.0%}</td><td>{P(r['主_被停損那批：停損實際（扣成本）'])}／{P(r['主_被停損那批：不停損抱到H（扣成本）'])}</td><td>{bsv}</td></tr>")
        H.append("</table></div>")
    H.append(f"<p class='note'>營量 v1：探索 {P(v1['探索'][0])}／{P(v1['探索'][1])}、確認 {P(v1['確認'][0])}／{P(v1['確認'][1])}（{v1['確認'][2]}）、早年 {P(v1['早年'][0])}；"
             f"0050 確認 {P(Z['確認']['cagr'])}／{P(Z['確認']['mdd'])}、早年 {P(Z['早年']['cagr'])}。觸發率、接到新股、被停損批 ＝ 主窗 2017～2026；接到新股 ＝ 停損賣出那天同一天有買進新股的比例。</p>")
    H.append("<h2>b10、60 天（一日版）例子（確認段、實際成交；每類取中位那筆）</h2>" + CS.legend_html())
    op_ = ctx["opens"]
    for cat, i, n_, key in EX:
        if i is None:
            H.append(f"<p class='note'>{cat}：沒有例子。</p>"); continue
        r = TR.loc[i]; s = r["sid"]; t_in = int(r["t_in"]); t_out = min(int(r["t_out"]), len(cal) - 1); x0 = min(orig[(s, t_in)][0], len(cal) - 1)
        df = D.load_stock(s, Wm["mk"].get(s, "twse"), cal).df; cf = pd.Series(df["close"].to_numpy(float)).ffill().to_numpy()
        i0 = max(0, t_in - 30); i1 = min(len(cal) - 1, max(x0, t_out) + 10); sl = slice(i0, i1 + 1)
        P0 = float(op_[s][t_in])
        marks = [{"i": t_in - i0, "px": P0, "kind": "entry", "label": f"進 {P0:.2f}"}]
        hl = []
        if r["停損"]:
            marks.append({"i": t_out - i0, "px": float(op_[s][t_out]), "kind": "exit", "label": f"停損賣 {op_[s][t_out]:.2f}", "color": "#c62828"})
            marks.append({"i": x0 - i0, "px": float(cf[x0]), "kind": "exit", "label": f"不停損抱到60天 {cf[x0]:.2f}", "color": "#888888", "row": 1})
            hl.append({"px": P0 * 0.9, "label": f"成本×0.90 ＝ {P0 * 0.9:.2f}", "color": "#e65100"})
            sub = f"停損 {P(r['淨'])}；不停損抱到 60 天 {P(r['原版淨'])}；差 {r['差'] * 100:+.2f} 點"
        else:
            marks.append({"i": t_out - i0, "px": float(cf[t_out]), "kind": "exit", "label": f"出 {cf[t_out]:.2f}"})
            rep = sgs[sgs["t_out"] == t_in]["sid"].tolist()
            sub = f"停損釋出名額當天買進（同日被停損：{'、'.join(rep)}）｜這筆 {P(r['淨'])}"
        ma = {kk: CS.moving_avg(cf, kk)[sl] for kk in (5, 20, 60)}
        svg = CS.kline_svg([str(z.date()) for z in cal[sl]], df["open"].to_numpy(float)[sl], df["high"].to_numpy(float)[sl], df["low"].to_numpy(float)[sl], df["close"].to_numpy(float)[sl],
                           df["volume"].to_numpy(float)[sl] / 1000.0, ma=ma, marks=marks, shade=(t_in - i0, t_out - i0), title=cat, show_title=False, hlines=hl)
        H.append(f"<details class='card' open><summary><b>{html.escape(cat)}</b>｜{s} {html.escape(str(uni.get(s, '')))}｜進場 {dt(t_in)}</summary>"
                 f"<div class='meta'>這一類在確認段 {n_} 筆；取中位那筆｜{html.escape(sub)}</div>{svg}</details>")
    H.append("</main></body></html>")
    open(os.path.join(OUT, F_HTML), "w", encoding="utf-8").write("\n".join(H))
    S["例子"] = [{"類": cat, "sid": (TR.at[i, "sid"] if i is not None else None), "進場": (dt(TR.at[i, "t_in"]) if i is not None else None), "淨": (float(TR.at[i, "淨"]) if i is not None else None),
                "原版淨": (float(TR.at[i, "原版淨"]) if i is not None else None), "類筆數": n_} for cat, i, n_, _ in EX]
    S["例子查核"] = CK
    NL = chr(10)
    R_ = ["# 營量 v1 跌破停損、直接換下一檔（描述臂）" + NL, "使用者原話（逐字）：「" + RAW + "」" + NL,
          "> ⛔ 描述臂：不計 N、不改任何判定。⚠ 先驗提醒：" + S["先驗提醒"] + "。本線讀法 S1～S3 見程式開頭。" + NL,
          "| 版本 | b | H | 探索 | 確認 | 確認標籤 | 早年 | 早年標籤 | 確認對營量 v1〔CI〕 | 觸發率 | 接到新股 | 被停損批 停損／不停損 |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in TB.to_dict("records"):
        R_.append(f"| {r['版本']} | {int(round(r['b'] * 100))}% | {r['H']} | {P(r['探索_年化'])}／{P(r['探索_回落'])} | {P(r['確認_年化'])}／{P(r['確認_回落'])} | {r['確認_標籤']} | "
                  f"{P(r['早年_年化'])}／{P(r['早年_回落'])} | {r['早年_標籤']} | {P(r['確認_配對差年化'])}〔{P(r['確認_配對差lo'])}, {P(r['確認_配對差hi'])}〕 | {r['主_觸發率']:.0%} | "
                  f"{r['主_釋出後同日有接新股的停損筆比例']:.0%} | {P(r['主_被停損那批：停損實際（扣成本）'])}／{P(r['主_被停損那批：不停損抱到H（扣成本）'])} |")
    R_.append(NL + f"營量 v1 確認 {P(v1['確認'][0])}／{P(v1['確認'][1])}；0050 確認 {P(Z['確認']['cagr'])}；b 掃描版見 resultsYLexit3/bsweep。閘：{S['閘']}｜例子查核：{CK}｜網頁：{F_HTML}")
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write(NL.join(R_) + NL)
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] 網頁 {os.path.getsize(os.path.join(OUT, F_HTML))} bytes｜{CK}｜例子 {[(c, n) for c, _, n, _ in EX]}｜{time.time() - T0:.0f}s")


if __name__ == "__main__":
    main()
