# -*- coding: utf-8 -*-
"""PREREG營量出場 seq3 甲件 b 掃描描述臂（使用者問跌破 10%；描述臂、不計 N、不改判定）。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLexit3_b [--procs 2]
    簡短查核：~/tw-p16/.venv/bin/python backtest/researchYLexit3_b_check.py

使用者（逐字）：「跌破10%有測嗎？」（登錄只測 b {0, 3, 5%}）
⇒ seq3 甲件規則一字不改（警訊 W1～W4、等滿 10 天、買回最多一次；researchYLexit3.build3 同一支），只把 b 換成 {7, 10, 15%} × H {40, 60, 80} ＝ 9 格；
   並列 seq3 原本 b {0, 3, 5%} 同 H（resultsYLexit3 cells.csv 原值）⇒ b 0～15% 整條曲線
⛔ 不計 N、不改 seq3 判定（甲 b5_H40 不合格、對營量 v1 分不出）、不重挑
種子：營量依 relvol 排序、不抽籤 ⇒ 每格 1 顆（seq3 已驗 5 顆逐位元相同）
閘：b5_H40 重跑 ＝ resultsYLexit3 seeds.csv 種子 0 eq_sha（主、早年）；營量 v1 同
每格報：三段年化、回落、比值、標籤；對營量 v1 同段配對差（曆月 CR0、95% CI ×245）；觸發率（窗內訊號有暫出的比例）；放棄原因（警訊／等滿 10／買回上限）
網頁：b 曲線表＋ b10_H40 四張例子（確認段、種子 0、實際成交；各取一類「差 ＝ 本規則 − 原版」的中位那筆：沒觸發／警訊放棄／10 天放棄／買回後（未放棄））
輸出 backtest/resultsYLexit3/bsweep/
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
from backtest import chart_svg as CS

OUT = "backtest/resultsYLexit3/bsweep"
F_HTML = "營量出場seq3_跌破幅度曲線_20260928.html"
COST = R11.COST
B_NEW = (0.07, 0.10, 0.15); H_S = (40, 60, 80)
TAG = "使用者問跌破 10%；描述臂、不計 N、不改判定"


def worlds(log):
    from backtest import researchT1fix as T1
    ctx = T1.build_ctx(True)
    cal = ctx["cal"]; mk = ctx["mk"]; AND = RR._G["AND"]
    SF = R11.stop_force_days(R11.valid_from_data(sorted(ctx["closes"]), mk, cal), ctx["w1"])
    SEGP = {sg: (int(cal.searchsorted(pd.Timestamp(x))), int(cal.searchsorted(pd.Timestamp(y)))) for sg, (x, y) in YX.SEG_C.items()}
    Wm = {"cal": cal, "NP": ctx["ncal"], "closes": ctx["closes"], "opens": ctx["opens"], "SF": SF, "mk": mk, "w0": ctx["w0"], "w1": ctx["w1"], "SEGP": SEGP,
          "BARS": {}, "EVD": {}, "REV": Y3.rev_events(os.path.join(RR.OUT, "sig_edc6f", "panel_rev.csv.gz"))}
    Wm["SIGH"] = {("營量", 60): ctx["sig13"]}
    for H in (40, 80):
        t_, _ = YX.exits_H(Wm, ctx["sig13"], H); Wm["SIGH"][("營量", H)] = t_[t_[f"xpos_H{H}"] >= 0]
    Wm["NEWK"] = {"營量": {s: set(g["k"].astype(int)) for s, g in AND.groupby("sid")}}
    from backtest import researchV as V
    from backtest import researchYear1M as Y
    from backtest import early_data as E
    V.body_setup("main", log)
    ecal = V._B["cal"]; ew0, ew1 = V._B["w0"], V._B["w1"]; euni = Y._G["uni"]
    EV = pd.read_csv(os.path.join(E.snap_dir(E.BODY_SHA), "reduce_events.csv"), dtype=str)
    posd = {d.strftime("%Y-%m-%d"): j for j, d in enumerate(ecal)}; EVD = {}
    for s_, e_, L_ in zip(EV["stock_id"], EV["e"], EV["L"]):
        if e_ in posd and L_ in posd:
            EVD.setdefault(s_, []).append((posd[e_], posd[L_]))
    ecl, eop = Y._G["closes"], Y._G["opens"]
    eSF = R11.stop_force_days(R11.valid_from_data(sorted(ecl), euni, ecal), ew1)
    We = {"cal": ecal, "NP": Y._G["NP"], "closes": ecl, "opens": eop, "SF": eSF, "mk": euni, "w0": ew0, "w1": ew1, "SEGP": {"早年": (ew0, ew1)}, "BARS": {}, "EVD": EVD,
          "REV": Y3.rev_events(os.path.join(V.body_paths("main")[1], "panel_rev.csv.gz"))}
    EALL = Y.sig_of(13, "mtm", 0, len(ecal) + 5); es13 = Y.sig_of(13, "mtm", ew0, ew1)
    We["SIGH"] = {("營量", 60): es13}
    for H in (40, 80):
        t_, _ = YX.exits_H(We, es13, H); We["SIGH"][("營量", H)] = t_[t_[f"xpos_H{H}"] >= 0]
    We["NEWK"] = {"營量": {s: set(g["k"].astype(int)) for s, g in EALL.groupby("sid")}}
    RR.use_snapshot()
    for s in sorted(set(ctx["sig13"]["sid"])):
        YX.bars_of(Wm, s); Y3.warns(Wm, s)
    D.DATA = V.body_paths("main")[0]
    for s in sorted(set(es13["sid"])):
        YX.bars_of(We, s); Y3.warns(We, s)
    RR.use_snapshot()
    return Wm, We, ctx


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    log(f"===== researchYLexit3_b {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜{TAG} =====")
    S = {"身分": TAG, "使用者原話": "跌破10%有測嗎？", "閘": {}}
    Wm, We, ctx = worlds(log)
    Y3._W["主"] = Wm; Y3._W["早年"] = We
    BASEc = ("營量", "base", None)
    NEW = [("營量", "甲", (b, H, Y3.WS, 10, 1)) for b in B_NEW for H in H_S]
    OLD = [("營量", "甲", (b, H, Y3.WS, 10, 1)) for b in (0.0, 0.03, 0.05) for H in H_S]
    GATE = ("營量", "甲", (0.05, 40, Y3.WS, 10, 1))
    ref = pd.read_csv("backtest/resultsYLexit3/seeds.csv.gz", dtype={"eq_sha": str}, low_memory=False)
    ROWS = []; DIFF = {}
    for wk, W in (("主", Wm), ("早年", We)):
        W["KEEP"] = BASEc
        bres = Y3.run_cell((wk, BASEc, 0)); W["V1EQ"] = bres[2][0]; W["KEEP"] = None
        ROWS.append(bres[0])
        with Pool(a.procs) as pool:
            for row, diffs, _ in pool.imap_unordered(Y3.run_cell, [(wk, c, 0) for c in NEW + [GATE]]):
                ROWS.append(row)
                for sg, d in diffs.items():
                    DIFF[(wk, row["格"], sg)] = d
        for nm in ("營量v1", Y3.cname(GATE)):
            rr = ref[(ref["世界"] == wk) & (ref["格"] == nm) & (ref["r"] == 0)]["eq_sha"].iloc[0]
            mine = [x for x in ROWS if x["世界"] == wk and x["格"] == nm][0]["eq_sha"]
            S["閘"][f"{wk}｜{nm} ＝ resultsYLexit3 種子 0 eq_sha"] = bool(mine == rr)
        log(f"[{wk}] 完成｜閘 {S['閘']}")
    SEED = pd.DataFrame(ROWS); SEED.to_csv(os.path.join(OUT, "seeds.csv"), index=False, float_format="%.17g")
    Z = json.load(open("backtest/resultsYLexit3/summary.json", encoding="utf-8"))["0050"]
    cal, ecal = Wm["cal"], We["cal"]
    months = {sg: np.array([str(d)[:7] for d in cal[x + 1:y + 1]]) for sg, (x, y) in Wm["SEGP"].items()}
    months["早年"] = np.array([str(d)[:7] for d in ecal[We["w0"] + 1:We["w1"] + 1]])
    old = pd.read_csv("backtest/resultsYLexit3/cells.csv").set_index("格")
    TB = []
    # 路徑統計（觸發率、放棄原因）：新舊 b 都算（build3 決定性）
    for c in OLD + NEW:
        k = Y3.cname(c); b, H = c[2][0], c[2][1]
        row = {"b": b, "H": H, "格": k, "來源": "seq3 判定格（resultsYLexit3）" if c in OLD else "本描述臂"}
        if c in OLD:
            r = old.loc[k]
            for sg in ("探索", "確認", "早年"):
                row.update({f"{sg}_年化": r[f"{sg}_年化"], f"{sg}_回落": r[f"{sg}_回落"], f"{sg}_比值": r[f"{sg}_比值"], f"{sg}_標籤": r[f"{sg}_標籤"]})
            row.update({"確認_配對差年化": r["確認_配對差年化"], "確認_配對差lo": r["確認_配對差lo"], "確認_配對差hi": r["確認_配對差hi"], "早年_配對差年化": r["早年_配對差年化"]})
        else:
            for sg, wk in (("探索", "主"), ("確認", "主"), ("早年", "早年")):
                g = SEED[(SEED["世界"] == wk) & (SEED["格"] == k)].iloc[0]
                cc, mm = float(g[f"{sg}_年化"]), float(g[f"{sg}_回落"])
                row.update({f"{sg}_年化": cc, f"{sg}_回落": mm, f"{sg}_比值": cc / abs(mm), f"{sg}_標籤": YX.label(cc, mm, Z[sg])})
                d = DIFF[(wk, k, sg)]; m_, se_ = YX.cr0(d, months[sg])
                if sg in ("確認", "早年"):
                    row[f"{sg}_配對差年化"] = m_ * 245
                    if sg == "確認":
                        row["確認_配對差lo"] = (m_ - 1.96 * se_) * 245; row["確認_配對差hi"] = (m_ + 1.96 * se_) * 245
        for wk, W in (("主", Wm), ("早年", We)):
            Y3.inputs(W, c)
            st = [x for x in W["JST"][c] if W["w0"] <= x["e"] <= W["w1"]]; ot = [x for x in st if x["出"] > 0]
            row[f"{wk}_觸發率"] = len(ot) / max(len(st), 1)
            for why in ("警訊", "等滿10", "買回上限"):
                row[f"{wk}_放棄_{why}"] = sum(x["放棄"] == why for x in ot) / max(len(st), 1)
            row[f"{wk}_買回後未放棄"] = sum((x["進站回"] + x["進新訊號"] > 0) and x["放棄"] is None for x in ot) / max(len(st), 1)
        TB.append(row)
    TB = pd.DataFrame(TB).sort_values(["H", "b"]); TB.to_csv(os.path.join(OUT, "bcurve.csv"), index=False, float_format="%.17g")
    S["0050"] = Z; S["營量v1"] = {sg: [float(old.loc["營量v1", f"{sg}_年化"]), float(old.loc["營量v1", f"{sg}_回落"])] for sg in ("探索", "確認", "早年")}
    S["b10_H40"] = TB[(TB["b"] == 0.10) & (TB["H"] == 40)].iloc[0].to_dict()
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log("[曲線] " + "；".join(f"b{int(round(r.b * 100))}_H{r.H} 確認 {r.確認_年化:+.2%}" for r in TB.itertuples()))
    # ── 例子（b10_H40，主、確認段、種子 0）
    C10 = ("營量", "甲", (0.10, 40, Y3.WS, 10, 1))
    Wm["KEEP"] = C10; _, _, kept = Y3.run_cell(("主", C10, 0)); Wm["KEEP"] = None
    eq, aud = kept
    opn = {}; trd = []
    for a_ in sorted(aud, key=lambda z: (z["t"], z["side"] != "sell")):
        if a_["side"] == "buy":
            opn[a_["sid"]] = a_
        else:
            b0 = opn.pop(a_["sid"]); trd.append((a_["sid"], b0["t"], a_["t"], a_["amt"] / b0["amt"] - 1 - a_["cost"] / b0["amt"]))
    t0c = int(cal.searchsorted(pd.Timestamp("2022-01-03"))); t1c = int(cal.searchsorted(pd.Timestamp("2026-08-24")))
    base = ctx["sig13"]; orig = {(s, int(e)): (int(x), float(g)) for s, e, x, g in zip(base["sid"], base["entry_pos"], base["xpos_H60"], base["g_H60"])}
    sig = Y3.inputs(Wm, C10)[0]; gmap = {(u, int(e)): (int(x), float(g)) for u, e, x, g in zip(sig["usid"], sig["entry_pos"], sig["xpos_H40"], sig["g_H40"])}
    jst = {(x["sid"], int(x["e"])): x for x in Wm["JST"][C10]}
    rows = []
    for key, ti, to, net in trd:
        if not (t0c <= ti <= t1c):
            continue
        s = key.split("#")[0]; st = jst[(s, ti)]; x0, g0 = orig[(s, ti)]; xr, gr = gmap[(s, ti)]
        nre = st["進站回"] + st["進新訊號"]; ab = st["放棄"]
        cat = "沒觸發" if st["出"] == 0 else ("警訊放棄" if ab == "警訊" else ("10 天放棄" if ab == "等滿10" else ("買回上限放棄" if ab == "買回上限" else ("買回後（未放棄）" if nre > 0 else "暫出未買回、到期結束"))))
        rows.append({"sid": s, "t_in": ti, "t_out": to, "規則淨": net, "路徑淨": gr - COST if to == xr else np.nan, "原版淨": g0 - COST, "x0": x0, "類": cat, "st": st})
    T = pd.DataFrame(rows); T["差"] = T["規則淨"] - T["原版淨"]
    CK = {"b10_H40 audit 淨 ＝ 路徑 g − 成本（排程出場者最大差）": float((T["規則淨"] - T["路徑淨"]).abs().max())}
    EX = []
    for cat in ("沒觸發", "警訊放棄", "10 天放棄", "買回後（未放棄）"):
        g = T[T["類"] == cat].sort_values(["差", "t_in"])
        if len(g):
            EX.append((cat, g.index[(len(g) - 1) // 2], len(g)))
    uni = D.load_universe().set_index("stock_id")["name"]
    dt = lambda t: str(cal[int(t)].date())
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0] + "\n.pick{background:#fff4cc}td.l,th.l{text-align:left}"
    P = lambda x: "—" if x is None or not np.isfinite(x) else f"{x * 100:+.2f}%"
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>營量出場 跌破幅度曲線</title>", f"<style>{CSS}</style></head><body><main>", "<h1>營量出場 seq3 甲件：跌破幾 % 才暫出（b 0～15%）</h1>",
         f"<p class='lead'><b>{TAG}</b>。使用者原話：「跌破10%有測嗎？」b 7／10／15% 是新加的描述臂；b 0／3／5% 是原本的判定格（挑中 b5_H40、不合格）。</p>"]
    r10 = S["b10_H40"]
    H.append(f"<p class='note'>b10_H40：確認段 {P(r10['確認_年化'])}／{P(r10['確認_回落'])}（{r10['確認_標籤']}），對營量 v1 配對差 {P(r10['確認_配對差年化'])}〔{P(r10['確認_配對差lo'])}, {P(r10['確認_配對差hi'])}〕；"
             f"營量 v1 確認段 {P(S['營量v1']['確認'][0])}、0050 {P(Z['確認']['cagr'])}。都扣成本。⛔ 只描述，不改判定。</p>")
    for H_ in H_S:
        H.append(f"<h2>H＝{H_} 天</h2><div class='wrap'><table><tr><th class='l'>b</th><th>探索</th><th>確認</th><th>標籤</th><th>早年</th><th>標籤</th><th>確認配對差〔CI〕</th><th>早年配對差</th><th>觸發率</th><th>放棄：警訊／10 天／上限</th><th>買回後未放棄</th></tr>")
        for r in TB[TB["H"] == H_].to_dict("records"):
            c_ = "pick" if (r["b"] == 0.05 and H_ == 40) else ""
            H.append(f"<tr class='{c_}'><td class='l'>{int(round(r['b'] * 100))}%{'（新）' if r['來源'] == '本描述臂' else ''}{' ★seq3 挑中' if c_ else ''}</td>"
                     f"<td>{P(r['探索_年化'])}／{P(r['探索_回落'])}</td><td>{P(r['確認_年化'])}／{P(r['確認_回落'])}</td><td>{r['確認_標籤']}</td>"
                     f"<td>{P(r['早年_年化'])}／{P(r['早年_回落'])}</td><td>{r['早年_標籤']}</td><td>{P(r['確認_配對差年化'])}〔{P(r['確認_配對差lo'])}, {P(r['確認_配對差hi'])}〕</td>"
                     f"<td>{P(r['早年_配對差年化'])}</td><td>{r['主_觸發率']:.0%}</td><td>{r['主_放棄_警訊']:.0%}／{r['主_放棄_等滿10']:.0%}／{r['主_放棄_買回上限']:.0%}</td><td>{r['主_買回後未放棄']:.0%}</td></tr>")
        H.append("</table></div>")
    H.append(f"<p class='note'>觸發率與放棄比例 ＝ 主窗 2017～2026 訊號裡的比例。營量 v1：探索 {P(S['營量v1']['探索'][0])}、確認 {P(S['營量v1']['確認'][0])}、早年 {P(S['營量v1']['早年'][0])}；"
             f"0050 確認 {P(Z['確認']['cagr'])}／{P(Z['確認']['mdd'])}。</p>")
    H.append("<h2>b10_H40 例子（確認段、實際成交；每類取「差 ＝ 本規則 − 原版」的中位那筆）</h2>" + CS.legend_html())
    op_, cl_ = ctx["opens"], ctx["closes"]
    for cat, i, n_ in EX:
        r = T.loc[i]; s = r["sid"]; st = r["st"]; t_in = int(r["t_in"]); t_out = min(int(r["t_out"]), len(cal) - 1); xo = min(int(r["x0"]), len(cal) - 1)
        df = D.load_stock(s, Wm["mk"].get(s, "twse"), cal).df; cf = pd.Series(df["close"].to_numpy(float)).ffill().to_numpy()
        i0 = max(0, t_in - 30); i1 = min(len(cal) - 1, max(xo, t_out) + 10); sl = slice(i0, i1 + 1)
        P0 = float(op_[s][t_in]); idx = YX.bars_of(Wm, s)[0]; nre = st["進站回"] + st["進新訊號"]
        marks = [{"i": t_in - i0, "px": P0, "kind": "entry", "label": f"進 {P0:.2f}"},
                 {"i": xo - i0, "px": float(cf[xo]), "kind": "exit", "label": f"原版出 {cf[xo]:.2f}", "color": "#888888", "row": 1}]
        for n2, (sb, rb, _) in enumerate(st["段"]):
            ts = int(idx[sb]); marks.append({"i": ts - i0, "px": float(op_[s][ts]), "kind": "exit", "label": f"賣 {op_[s][ts]:.2f}", "color": "#c62828"})
            if n2 < nre:
                tb = int(idx[rb]); marks.append({"i": tb - i0, "px": float(op_[s][tb]), "kind": "entry", "label": f"買回 {op_[s][tb]:.2f}", "color": "#ef6c00", "row": 1})
        ab = st["放棄"]
        if ab:
            marks.append({"i": t_out - i0, "px": float(cf[t_out]), "kind": "exit", "label": f"放棄（{'10 天' if ab == '等滿10' else ab}）、換下一檔", "row": 2})
        elif st["終於暫出"]:
            marks.append({"i": t_out - i0, "px": float(cf[t_out]), "kind": "exit", "label": "第 40 天結束（仍在外）", "row": 2})
        else:
            marks.append({"i": t_out - i0, "px": float(cf[t_out]), "kind": "exit", "label": f"第 40 天出場 {cf[t_out]:.2f}"})
        ma = {k: CS.moving_avg(cf, k)[sl] for k in (5, 20, 60)}
        svg = CS.kline_svg([str(z.date()) for z in cal[sl]], df["open"].to_numpy(float)[sl], df["high"].to_numpy(float)[sl], df["low"].to_numpy(float)[sl], df["close"].to_numpy(float)[sl],
                           df["volume"].to_numpy(float)[sl] / 1000.0, ma=ma, marks=marks, shade=(t_in - i0, t_out - i0), title=cat, show_title=False,
                           hlines=[{"px": P0 * 0.9, "label": f"成本×0.90 ＝ {P0 * 0.9:.2f}", "color": "#e65100"}])
        H.append(f"<details class='card' open><summary><b>{cat}</b>｜{s} {html.escape(str(uni.get(s, '')))}｜進場 {dt(t_in)}｜原版 {P(r['原版淨'])} → 本規則 {P(r['規則淨'])}｜差 {r['差'] * 100:+.2f} 點</summary>"
                 f"<div class='meta'>這一類在確認段 {n_} 筆（占 {n_ / len(T):.0%}）；取差的中位那筆</div>{svg}</details>")
    H.append("</main></body></html>")
    open(os.path.join(OUT, F_HTML), "w", encoding="utf-8").write("\n".join(H))
    S["例子"] = [{"類": cat, "sid": T.at[i, "sid"], "進場": dt(T.at[i, "t_in"]), "原版淨": float(T.at[i, "原版淨"]), "規則淨": float(T.at[i, "規則淨"]), "差": float(T.at[i, "差"]), "類筆數": n_} for cat, i, n_ in EX]
    S["例子查核"] = CK
    NL = chr(10)
    R_ = ["# PREREG營量出場 seq3 甲件 b 掃描（描述臂）" + NL, TAG + NL,
          "> 使用者原話：「跌破10%有測嗎？」｜seq3 甲件規則不改，只換 b；b 0／3／5% ＝ 原判定格（resultsYLexit3），7／10／15% ＝ 本描述臂。⛔ 不計 N、不改判定、不重挑。" + NL,
          "| b | H | 探索 | 確認 | 確認標籤 | 早年 | 早年標籤 | 確認配對差〔CI〕 | 觸發率 | 放棄 警訊／10 天／上限 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in TB.to_dict("records"):
        R_.append(f"| {int(round(r['b'] * 100))}%{'（新）' if r['來源'] == '本描述臂' else ''} | {r['H']} | {P(r['探索_年化'])}／{P(r['探索_回落'])} | {P(r['確認_年化'])}／{P(r['確認_回落'])} | {r['確認_標籤']} | "
                  f"{P(r['早年_年化'])}／{P(r['早年_回落'])} | {r['早年_標籤']} | {P(r['確認_配對差年化'])}〔{P(r['確認_配對差lo'])}, {P(r['確認_配對差hi'])}〕 | {r['主_觸發率']:.0%} | "
                  f"{r['主_放棄_警訊']:.0%}／{r['主_放棄_等滿10']:.0%}／{r['主_放棄_買回上限']:.0%} |")
    R_.append(NL + f"營量 v1：確認 {P(S['營量v1']['確認'][0])}；0050 確認 {P(Z['確認']['cagr'])}。閘：{S['閘']}。例子查核：{CK}。網頁：{F_HTML}")
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write(NL.join(R_) + NL)
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] 網頁 {os.path.getsize(os.path.join(OUT, F_HTML))} bytes｜{CK}｜{time.time() - T0:.0f}s")


if __name__ == "__main__":
    main()
