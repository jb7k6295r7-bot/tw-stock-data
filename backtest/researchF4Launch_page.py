# -*- coding: utf-8 -*-
"""researchF4Launch 網頁與彙總（連續虧損股起漲進場.html、summary.json）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchF4Launch page
只讀 backtest/resultsF4Launch/ 的輸出與 ~/f4lwork/prep_meta.json；營飆／營量引 backtest/resultsT1fix/cells.csv。
"""
from __future__ import annotations

import html
import json
import os

import numpy as np
import pandas as pd

OUT = os.path.expanduser("~/tw-p17/backtest/resultsF4Launch")
WORK = os.path.expanduser("~/f4lwork")
T1F = os.path.expanduser("~/tw-p17/backtest/resultsT1fix/cells.csv")
CSSF = os.path.expanduser("~/tw-p17/backtest/list_yl13_hist.py")
KS = (5, 10); XS = (10, 20, 30, 50); ES = ("E1", "E2")
ENAME = {"E1": "E1 飆股流程（不含買回）", "E2": "E2 最高回落 30%"}
GNAME = {"F4": "帶 F4（本件）", "NF4": "不帶 F4", "ALL": "不看 F4（描述）", "FAKE": "假訊號臂"}
PRIOR = ["① 兩段都合格的格 0 個（約六成）", "② 同格「帶 F4」年化高於「不帶 F4」（約五成五）", "③ x 越大年化越高（約五成）", "④ E2 吃到「起漲→頂」幾成高於 E1（約五成五）"]

P_ = lambda x: "—" if x is None or not np.isfinite(x) else f"{x * 100:.1f}%"
F2 = lambda x: "—" if x is None or not np.isfinite(x) else f"{x:.2f}"
F1 = lambda x: "—" if x is None or not np.isfinite(x) else f"{x:.1f}"
I_ = lambda x: "—" if x is None or not np.isfinite(x) else f"{x:,.0f}"


def cell_txt(c):
    k, x, E = c.split("_")
    return f"k≥{k[1:]}、從 60 日低點已漲 {x[1:]}%、{ENAME[E]}"


def load():
    G = pd.read_csv(os.path.join(OUT, "grid.csv"))
    M = json.load(open(os.path.join(OUT, "meta_run.json"), encoding="utf-8"))
    PM = json.load(open(os.path.join(WORK, "prep_meta.json"), encoding="utf-8"))
    TS = json.load(open(os.path.join(OUT, "trades_summary.json"), encoding="utf-8"))
    SS = pd.read_csv(os.path.join(OUT, "signals_summary.csv"))
    CK = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else None
    T1 = pd.read_csv(T1F).set_index("key")
    return G, M, PM, TS, SS, CK, T1


def row_of(G, pop, grp, cell, v):
    r = G[(G["母體"] == pop) & (G["群"] == grp) & (G["格"] == cell) & (G["版本"] == v)]
    return r.iloc[0] if len(r) else None


def verdict(G, M):
    ch = M["挑中格"]
    rb = row_of(G, "all", "F4", ch, "b"); rr = row_of(G, "all", "F4", ch, "r")
    eb, cb = rb["探索_標籤"], rb["確認_標籤"]
    if eb == "合格" and cb == "合格":
        fin = "暫定（事後重切 ⇒ 最多暫定；早年不可判定、只進前瞻紀錄）"
    elif cb == "另列":
        fin = "另列（確認段只贏報酬、沒贏報酬÷回落；不進前瞻紀錄）"
    else:
        fin = "不合格"
    return ch, rb, rr, fin


def build_summary(G, M, PM, TS, SS, CK, T1):
    ch, rb, rr, fin = verdict(G, M)
    Z = M["0050"]
    S = {"登錄": "PREREG連續虧損起漲 seq1（sha 207e7f0db9763c36；裁定 seq320）", "讀法寫死": M["讀法寫死"], "種子": M["reps"],
         "0050": Z, "挑中格": ch, "挑中格說明": cell_txt(ch) if ch else None, "探索合格格數": M["探索合格格數"], "非退化格數": M["非退化格數"],
         "判定": fin, "早年": "不可判定（F4 月底旗 2015-01 起、季報 2013Q1 起 ⇒ 2012-06～2014-12 F4 可判 0%；FEATS 融資使用率 0%、EPS 轉正 38% 有值）"}
    for v, r in (("0.585%", rb), ("現實版", rr)):
        S[f"挑中格 {v}"] = {sg: {"年化": float(r[f"{sg}_年化"]), "回落": float(r[f"{sg}_回落"]), "比值": float(r[f"{sg}_比值"]), "標籤": r[f"{sg}_標籤"],
                               "平均持股": float(r[f"{sg}_平均持股"]), "平均現金": float(r[f"{sg}_平均現金"])} for sg in ("探索", "確認", "主窗")}
    S["16格"] = []
    for k in KS:
        for x in XS:
            for E in ES:
                c = f"k{k}_x{x}_{E}"
                for v in ("b", "r"):
                    r = row_of(G, "all", "F4", c, v)
                    if r is None:
                        continue
                    S["16格"].append({"格": c, "版本": v, **{f"{sg}_{m}": (r[f"{sg}_{m}"] if m == "標籤" else float(r[f"{sg}_{m}"]))
                                                           for sg in ("探索", "確認", "主窗") for m in ("年化", "回落", "比值", "標籤")},
                                     "探索退化": bool(r["探索_退化"]), "探索平均持股": float(r["探索_平均持股"]), "探索平均現金": float(r["探索_平均現金"])})
    S["對照（挑中格）"] = {}
    for pop, grp in (("all", "NF4"), ("all", "ALL"), ("all", "FAKE"), ("W1", "F4"), ("W1", "NF4")):
        for v in ("b", "r"):
            r = row_of(G, pop, grp, ch, v)
            if r is not None:
                S["對照（挑中格）"][f"{pop}|{grp}|{v}"] = {sg: {"年化": float(r[f"{sg}_年化"]), "回落": float(r[f"{sg}_回落"]), "標籤": r[f"{sg}_標籤"]} for sg in ("探索", "確認", "主窗")}
    S["營飆營量（resultsT1fix 主窗）"] = {T1.loc[k, "名"]: {"年化": float(T1.loc[k, "t1_年化"]), "回落": float(T1.loc[k, "t1_回落"]), "標籤": T1.loc[k, "t1_標籤"]}
                                     for k in ("c1", "c13", "slip1_real", "slip13_real")}
    S["逐筆（挑中格）"] = TS
    S["F4 point-in-time"] = {"閘": PM["F4 閘"], "重編遮罩": PM["F4 重編遮罩差異"]}
    S["營收15日"] = PM["營收15日"]
    S["E1 錨移下單（訊號層）"] = PM.get("E1 錨移下單筆（b）")
    S["查核"] = None if CK is None else {"錯誤數": CK["錯誤數"], "項目": CK["項目"]}
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    return S


def page():
    G, M, PM, TS, SS, CK, T1 = load()
    S = build_summary(G, M, PM, TS, SS, CK, T1)
    ch, rb, rr, fin = verdict(G, M)
    Z = M["0050"]
    CSS = open(CSSF, encoding="utf-8").read().split('CSS = """')[1].split('"""')[0]
    CSS += ("\ntd.l,th.l{text-align:left;white-space:normal;min-width:10em}small{color:#666}.warn{border-left:4px solid #d64045;padding:6px 10px;background:#fff4f4}"
            "\ntr.hl td{background:#fff8e1}tr.sep td{border-top:2px solid #bbb}ul.k li{margin:.25em 0}.ok{color:#2e7d32}.bad{color:#c62828}")

    def lab(x):
        return f"<b class='{'ok' if x == '合格' else ('bad' if x == '不合格' else '')}'>{html.escape(str(x))}</b>"

    tsb = TS.get("F4|b", {}).get("主窗", {}); tsr = TS.get("F4|r", {}).get("主窗", {}); tnb = TS.get("NF4|b", {}).get("主窗", {})
    fk = row_of(G, "all", "FAKE", ch, "b"); fkr = row_of(G, "all", "FAKE", ch, "r"); nf = row_of(G, "all", "NF4", ch, "b"); nfr = row_of(G, "all", "NF4", ch, "r")
    w1b = row_of(G, "W1", "F4", ch, "b")
    yb = T1.loc["c1"]; yl = T1.loc["c13"]
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>連續虧損股起漲進場</title>", f"<style>{CSS}</style></head><body><main>",
         "<h1>連續虧損股起漲進場：連續虧損＋起漲特徵＋從低點已漲 x%，隔天開盤買</h1>",
         f"<p class='lead'><b>結論：{html.escape(fin)}。</b> 探索段挑出的格是「{html.escape(cell_txt(ch))}」；"
         f"確認段（2022-01～2026-08）年化 {P_(rb['確認_年化'])}、最大回落 {P_(rb['確認_回落'])}，同期 0050 年化 {P_(Z['確認']['cagr'])}、回落 {P_(Z['確認']['mdd'])} ⇒ {lab(rb['確認_標籤'])}。"
         f"扣掉滑價與漲跌停買賣不到的現實版（主要參考）確認段年化 {P_(rr['確認_年化'])}、回落 {P_(rr['確認_回落'])} ⇒ {lab(rr['確認_標籤'])}。</p>",
         "<p class='warn'>回測結果，⛔ 不是買賣建議。本件是「事後重切」（登錄前已看過分界描述）⇒ 就算兩段都合格也最多「暫定」。早年段（2012-06～2014-12）沒有連續虧損的季報判定 ⇒ 不可判定。用語：假訊號 ＝ 隨機挑一天買的對照。</p>",
         "<h2>先講結論</h2><ul class='k'>",
         f"<li><b>16 格整套一判</b>：探索段（2017-03～2021-12）16 格中合格 {M['探索合格格數']} 格、沒有退化的 {M['非退化格數']} 格；"
         f"k≥10 的格每天訊號太少（整段只有個位數到幾十筆），持股湊不滿 ⇒ 退化、不參加挑選。挑中 {html.escape(ch)}（探索段 {lab(rb['探索_標籤'])}：年化 {P_(rb['探索_年化'])} vs 0050 {P_(Z['探索']['cagr'])}）。</li>",
         f"<li><b>主窗（2017-03～2026-08）</b>：年化 {P_(rb['主窗_年化'])}、回落 {P_(rb['主窗_回落'])}；現實版 {P_(rr['主窗_年化'])}、{P_(rr['主窗_回落'])}；"
         f"0050 {P_(Z['主窗']['cagr'])}、{P_(Z['主窗']['mdd'])}；營飆 v1 {P_(yb['t1_年化'])}、營量 v1 {P_(yl['t1_年化'])}。</li>",
         f"<li><b>帶 F4 有沒有比較好</b>：同格不帶 F4（其他條件一樣）主窗年化 {P_(nf['主窗_年化'])}（現實版 {P_(nfr['主窗_年化'])}）；帶 F4 {P_(rb['主窗_年化'])}。</li>",
         f"<li><b>假訊號臂</b>（同一批股票、隨機挑一天買、持有天數照本件分佈）：主窗年化 {P_(fk['主窗_年化'])}（現實版 {P_(fkr['主窗_年化'])}）。</li>",
         f"<li><b>一年內先跌 15%</b>：實際成交的筆 {P_(tsb.get('一年內先跌15%'))}（不帶 F4 {P_(tnb.get('一年內先跌15%'))}）；"
         f"<b>吃到「起漲→頂」幾成</b>中位 {P_(tsb.get('吃到起漲→頂幾成', {}).get('中位'))}；持有天數中位 {F1(tsb.get('持有天數', {}).get('中位'))} 根 K 棒；"
         f"窗尾 2026-08-24 仍持有 {F1(rb['窗尾持有'])} 檔。</li>",
         f"<li><b>只看 W1 母體（營量、營飆能買的）</b>：主窗年化 {P_(w1b['主窗_年化']) if w1b is not None else '—'}。</li></ul>"]
    # 16 格表
    H.append("<h2>一、16 格（主母體全部上市櫃、帶 F4、成本 0.585%；括號＝現實版）</h2><div class='wrap'><table>"
             "<tr><th class='l'>格</th><th>探索 年化</th><th>探索 回落</th><th>探索 比值</th><th>探索</th><th>平均持股</th><th>現金</th>"
             "<th>確認 年化</th><th>確認 回落</th><th>確認</th><th>主窗 年化</th><th>主窗 回落</th></tr>")
    H.append(f"<tr class='sep'><td class='l'>0050 同窗</td><td>{P_(Z['探索']['cagr'])}</td><td>{P_(Z['探索']['mdd'])}</td><td>{F2(Z['探索']['cagr'] / abs(Z['探索']['mdd']))}</td><td></td><td></td><td></td>"
             f"<td>{P_(Z['確認']['cagr'])}</td><td>{P_(Z['確認']['mdd'])}</td><td></td><td>{P_(Z['主窗']['cagr'])}</td><td>{P_(Z['主窗']['mdd'])}</td></tr>")
    for k in KS:
        for x in XS:
            for E in ES:
                c = f"k{k}_x{x}_{E}"; b = row_of(G, "all", "F4", c, "b"); r = row_of(G, "all", "F4", c, "r")
                if b is None:
                    continue
                dg = " <small>退化</small>" if b["探索_退化"] else ""
                H.append(f"<tr{' class=hl' if c == ch else ''}><td class='l'>k≥{k}、已漲 {x}%、{E}{dg}</td>"
                         f"<td>{P_(b['探索_年化'])}<br><small>({P_(r['探索_年化'])})</small></td><td>{P_(b['探索_回落'])}</td><td>{F2(b['探索_比值'])}</td><td>{lab(b['探索_標籤'])}</td>"
                         f"<td>{F1(b['探索_平均持股'])}</td><td>{P_(b['探索_平均現金'])}</td>"
                         f"<td>{P_(b['確認_年化'])}<br><small>({P_(r['確認_年化'])})</small></td><td>{P_(b['確認_回落'])}</td><td>{lab(b['確認_標籤'])}<br><small>({html.escape(str(r['確認_標籤']))})</small></td>"
                         f"<td>{P_(b['主窗_年化'])}<br><small>({P_(r['主窗_年化'])})</small></td><td>{P_(b['主窗_回落'])}</td></tr>")
    H.append(f"</table></div><p class='note'>年化、回落 ＝ {M['reps']} 顆抽籤種子的中位；比值 ＝ 年化 ÷ |回落|；合格 ＝ 年化 ＞ 0050 且 比值 ≥ 0050；另列 ＝ 只贏報酬。"
             "退化 ＝ 探索段平均持股 ＜ 3 檔或現金 ＞ 30%（事前排除）。E1 ＝ W1 賣 3 成、剩 7 成等 W2 或回落 30%、W1 前 40 天沒新高全賣（每日名單現行算法，不含買回）；E2 ＝ 最高回落 30% 全賣；都不設最長天數。</p>")
    # 對照
    H.append(f"<h2>二、對照（挑中格 {html.escape(ch)}）</h2><div class='wrap'><table><tr><th class='l'>臂</th><th>探索 年化</th><th>探索 回落</th><th>確認 年化</th><th>確認 回落</th><th>確認</th><th>主窗 年化</th><th>主窗 回落</th></tr>")
    for pop, grp, v, nm in (("all", "F4", "b", "本件（帶 F4）"), ("all", "F4", "r", "本件 現實版"), ("all", "NF4", "b", "不帶 F4"), ("all", "NF4", "r", "不帶 F4 現實版"),
                            ("all", "ALL", "b", "不看 F4（描述）"), ("all", "FAKE", "b", "假訊號臂"), ("all", "FAKE", "r", "假訊號臂 現實版"),
                            ("W1", "F4", "b", "W1 母體內 帶 F4"), ("W1", "F4", "r", "W1 母體內 帶 F4 現實版"), ("W1", "NF4", "b", "W1 母體內 不帶 F4")):
        r = row_of(G, pop, grp, ch, v)
        if r is None:
            continue
        H.append(f"<tr><td class='l'>{nm}</td><td>{P_(r['探索_年化'])}</td><td>{P_(r['探索_回落'])}</td><td>{P_(r['確認_年化'])}</td><td>{P_(r['確認_回落'])}</td><td>{lab(r['確認_標籤'])}</td>"
                 f"<td>{P_(r['主窗_年化'])}</td><td>{P_(r['主窗_回落'])}</td></tr>")
    for k_, nm in (("c1", "營飆 v1（resultsT1fix）"), ("slip1_real", "營飆 v1 現實版"), ("c13", "營量 v1（resultsT1fix）"), ("slip13_real", "營量 v1 現實版")):
        H.append(f"<tr class='{'sep' if k_ == 'c1' else ''}'><td class='l'>{nm}</td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td><td>{P_(T1.loc[k_, 't1_年化'])}</td><td>{P_(T1.loc[k_, 't1_回落'])}</td></tr>")
    H.append(f"<tr><td class='l'>0050</td><td>{P_(Z['探索']['cagr'])}</td><td>{P_(Z['探索']['mdd'])}</td><td>{P_(Z['確認']['cagr'])}</td><td>{P_(Z['確認']['mdd'])}</td><td></td><td>{P_(Z['主窗']['cagr'])}</td><td>{P_(Z['主窗']['mdd'])}</td></tr>")
    H.append("</table></div><p class='note'>營飆、營量只有主窗數字（resultsT1fix 正式版）。不帶 F4 ＝ 同格條件、訊號日連續虧損判定為否或判不出。假訊號臂 ＝ 每筆換成同一檔、同一段內隨機一天買，持有天數從本格實際持有天數抽，到期隔天開盤賣。</p>")
    # 逐筆必報
    H.append("<h2>三、必報（挑中格實際成交的筆，各種子合計；括號＝現實版）</h2><div class='wrap'><table><tr><th class='l'>項目</th><th>探索</th><th>確認</th><th>主窗</th></tr>")
    def tsv(key, sg, f, v="b"):
        d = TS.get(f"F4|{v}", {}).get(sg, {})
        return d.get(key) if f is None else (d.get(key, {}) or {}).get(f)
    items = [("每顆種子平均成交筆", "每顆種子平均筆", None, F1), ("逐筆報酬（扣成本）中位", "實現報酬", "中位", P_), ("逐筆報酬平均", "實現報酬", "平均", P_), ("勝率", "勝率", None, P_),
             ("一年內先跌 15%", "一年內先跌15%", None, P_), ("吃到「起漲→頂」幾成（中位）", "吃到起漲→頂幾成", "中位", P_), ("吃到幾成（買價基準，中位）", "吃到（買價基準）", "中位", P_),
             ("持有天數中位（K 棒）", "持有天數", "中位", F1), ("持有天數 p90", "持有天數", "p90", F1), ("未完（到資料尾還抱著）", "未完筆", None, I_),
             ("停止交易（下市等）筆", "停止交易（下市等）筆", None, I_), ("停止交易筆報酬平均", "停止交易筆實現報酬", "平均", P_)]
    for nm, key, f, fmt in items:
        H.append(f"<tr><td class='l'>{nm}</td>" + "".join(f"<td>{fmt(tsv(key, sg, f))}<br><small>({fmt(tsv(key, sg, f, 'r'))})</small></td>" for sg in ("探索", "確認", "主窗")) + "</tr>")
    H.append("</table></div>")
    r3 = tsb.get("出場原因3成", {}); r7 = tsb.get("出場原因7成", {})
    H.append("<p class='note'>出場原因（主窗、0.585% 版，筆數）：先賣的 3 成 " + "、".join(f"{html.escape(k)} {v}" for k, v in r3.items())
             + "；剩下 7 成 " + "、".join(f"{html.escape(k)} {v}" for k, v in r7.items()) + "（E2 兩部分同一天，原因相同）。"
             f"「W1（買進前）」＝ 買進時這一段已出現過第一頂警示 ⇒ 每日名單的算法在買進隔天就先賣 3 成。錨移 ＝ 每天重算起漲點時起漲點移動、回頭認定更早就該賣 ⇒ 隔天開盤補賣（{tsb.get('錨移下單', 0)} 筆）。</p>")
    H.append(f"<p class='note'>窗尾 2026-08-24 仍持有（種子中位）：{F1(rb['窗尾持有'])} 檔；漲停買不到（現實版，每顆種子中位）：{F1(rr['漲停買不到'])} 筆；停牌買不到 {F1(rr['停牌買不到'])} 筆；"
             f"停止交易強制出場 {F1(rb['停止交易強制出場'])} 筆。</p>")
    # 各年
    yc = [c for c in G.columns if c.startswith("年")]
    H.append("<h3>各年報酬（種子中位）</h3><div class='wrap'><table><tr><th class='l'>臂</th>" + "".join(f"<th>{c[1:]}</th>" for c in yc) + "</tr>")
    for nm, r in (("本件", rb), ("本件 現實版", rr), ("不帶 F4", nf), ("假訊號臂", fk)):
        H.append(f"<tr><td class='l'>{nm}</td>" + "".join(f"<td>{P_(r[c])}</td>" for c in yc) + "</tr>")
    H.append("<tr><td class='l'>0050</td>" + "".join(f"<td>{P_(M['0050 年度'].get(c[1:], M['0050 年度'].get(int(c[1:]), np.nan)) if isinstance(M['0050 年度'], dict) else np.nan)}</td>" for c in yc) + "</tr>")
    H.append("</table></div><p class='note'>2017 年從 3 月 2 日起、2026 年到 8 月 24 日。</p>")
    # 訊號層
    H.append("<h2>四、訊號層（每天訊號數、先跌 15%、吃到幾成；主母體、成本前）</h2><div class='wrap'><table><tr><th class='l'>格</th><th>群</th><th>段</th><th>訊號</th><th>每天</th><th>先跌 15%</th><th>吃到起漲→頂 中位</th><th>持有中位</th></tr>")
    for c in [f"k{k}_x{x}_{E}" for k in KS for x in XS for E in ES]:
        for grp in ("F4", "NF4"):
            for sg in ("探索", "確認"):
                q = SS[(SS["母體"] == "all") & (SS["群"] == grp) & (SS["格"] == c) & (SS["段"] == sg)]
                if not len(q):
                    continue
                q = q.iloc[0]
                H.append(f"<tr{' class=hl' if c == ch else ''}><td class='l'>{c}</td><td>{GNAME[grp]}</td><td>{sg}</td><td>{I_(q['訊號數'])}</td><td>{F2(q['每天訊號'])}</td>"
                         f"<td>{P_(q['一年內先跌15%'])}</td><td>{P_(q['吃到起漲→頂中位'])}</td><td>{F1(q['持有天數中位'])}</td></tr>")
    H.append("</table></div>")
    # 先驗
    H.append("<h2>五、先驗（登錄時寫下、不改）對照結果</h2><ul class='k'>")
    both = sum(1 for d in S["16格"] if d["版本"] == "b" and d["探索_標籤"] == "合格" and d["確認_標籤"] == "合格")
    def ann(c):
        r = row_of(G, "all", "F4", c, "b"); n_ = row_of(G, "all", "NF4", c, "b"); return r["主窗_年化"], n_["主窗_年化"]
    win2 = sum(1 for k in KS for x in XS for E in ES if ann(f"k{k}_x{x}_{E}")[0] > ann(f"k{k}_x{x}_{E}")[1])
    H.append(f"<li>{PRIOR[0]} ⇒ 兩段都合格的格 {both} 個（0.585% 版）。</li>")
    H.append(f"<li>{PRIOR[1]} ⇒ 16 格中帶 F4 主窗年化較高的 {win2} 格。</li>")
    mono = []
    for k in KS:
        for E in ES:
            v_ = [row_of(G, "all", "F4", f"k{k}_x{x}_{E}", "b")["主窗_年化"] for x in XS]
            mono.append(f"k≥{k} {E}：" + "→".join(P_(t) for t in v_))
    H.append(f"<li>{PRIOR[2]} ⇒ x＝10→20→30→50% 主窗年化：" + "；".join(mono) + "。</li>")
    e12 = []
    for k in KS:
        for x in XS:
            a_ = SS[(SS["母體"] == "all") & (SS["群"] == "F4") & (SS["格"] == f"k{k}_x{x}_E1")]["吃到起漲→頂中位"].median()
            b_ = SS[(SS["母體"] == "all") & (SS["群"] == "F4") & (SS["格"] == f"k{k}_x{x}_E2")]["吃到起漲→頂中位"].median()
            e12.append((a_, b_))
    nE2 = sum(1 for a_, b_ in e12 if np.isfinite(a_) and np.isfinite(b_) and b_ > a_)
    H.append(f"<li>{PRIOR[3]} ⇒ 8 組（k × x）訊號層「吃到起漲→頂」中位，E2 高於 E1 的 {nE2} 組。</li></ul>")
    # 早年
    cov = PM["覆蓋"]["早年"]
    H.append("<h2>六、早年段（2012-06～2014-12）：不可判定</h2>"
             f"<p>連續虧損（F4）要用季報：資料庫季報從 2013Q1 起、月底判定表從 2015-01 起 ⇒ 早年 F4 可判 {P_(cov['F4 可判（股-日）'])}。"
             f"起漲特徵 14 個裡，融資使用率有值 {P_(cov['有值：融資使用率｜Q5'])}、EPS 轉正 {P_(cov['有值：原：EPS轉正｜是'])}（探索段 {P_(PM['覆蓋']['探索']['有值：原：EPS轉正｜是'])}）。"
             "照裁定 seq320 第 3 條標「不可判定」，⛔ 不硬判 ⇒ 判定只看確認段。</p>")
    # 讀法與資料
    fd = PM["F4 重編遮罩差異"]
    H.append("<h2>七、怎麼算的（重點）</h2><ul class='k'>"
             "<li><b>進場</b>：同一天收盤三條都成立 ⇒ 隔天開盤買：① 連續虧損（當天之前最後一個月底、當時已公布的季報：近 4 季合計虧且最近一季虧，或近 8 季 ≥ 6 季虧）"
             "② 14 個起漲特徵符合 ≥ k 個 ③ 收盤 ÷ 近 60 根最低收盤 − 1 ≥ x，而且是這一段第一次達到（之後 60 根內不再算）。觸發當天 ①② 不成立 ⇒ 這一段沒有訊號。</li>"
             f"<li><b>連續虧損只用第一次公布的數字、以公布日為準</b>：公布日 ＝ 公開資訊觀測站最早上傳時間（2016～2018 沒有時戳 ⇒ 法定期限後 5 個交易日，偏晚不偏早）；"
             f"後來重編過的季（{fd['重編季數（filing_dates）']} 季）資料庫只有重編後的數字 ⇒ 當作沒有 ⇒ 判不出就當不帶 F4；因此由「帶」變「不帶」{fd['F4 由有變無（股-月）']} 個股-月"
             f"（原表帶 F4 的 {fd['flags_main 帶 F4（股-月）']:,} 個股-月中）。</li>"
             "<li><b>E1 照每日名單現行算法逐日重播</b>：每天只用當天以前的資料重算起漲點與 W1／W2，該賣就隔天開盤賣；起漲點移動讓程式回頭認定早該賣的，也是隔天開盤補賣；不買回。</li>"
             "<li><b>組合</b>：最多 10 檔、每檔 1/10、候選多於空位抽籤、已過進場日不補、同一檔不重複買；成本 0.585%／來回；停止交易的股票在最後一根收盤出。"
             "現實版 ＝ 每邊再加 0.3%、平方根衝擊（50 萬 ÷ 10 檔）、一字漲停買不到、一字跌停賣不掉、用當天均價成交（低消 20 元在每筆 2.5 萬時不加成本）。</li>"
             "<li><b>2026 年月營收</b>：2026-01 期起改成次月 15 日後才可用（營收兩個特徵在 10～15 日之間改用前一期）。</li></ul>")
    ck = "（查核未跑）" if CK is None else f"獨立寫法抽樣重算：不同 {CK['錯誤數']} 處（{html.escape('；'.join(CK['項目']))}）。"
    H.append(f"<p class='note'>讀法寫死 {html.escape(M['讀法寫死'])}；{ck} 全部數字見 grid.csv、seeds.csv.gz、trades_summary.json、signals_summary.csv、summary.json。</p></main></body></html>")
    open(os.path.join(OUT, "連續虧損股起漲進場.html"), "w", encoding="utf-8").write("\n".join(H))
    print("page ok")


if __name__ == "__main__":
    page()
