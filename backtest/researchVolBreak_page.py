# -*- coding: utf-8 -*-
"""PREREG爆量突破進跌破EMA出 seq2 網頁（resultsVolBreak/爆量突破跌破EMA出.html）：先講判定、手機可讀。只讀結果檔。"""
import json
import os

import numpy as np
import pandas as pd

OUT = os.path.expanduser("~/tw-p17/backtest/resultsVolBreak")
CSS = """<style>body{font-family:-apple-system,'Noto Sans TC',sans-serif;margin:0 auto;max-width:780px;padding:0 16px 40px;line-height:1.6;color:#222;background:#fff}
h1{font-size:1.3em}h2{font-size:1.1em;margin-top:1.6em;border-bottom:1px solid #ddd}.box{background:#f4f6fa;border-left:4px solid #3a6;padding:10px 12px;margin:12px 0}
.bad{border-left-color:#c44}.wrap{overflow-x:auto}table{border-collapse:collapse;font-size:.85em;min-width:100%}td,th{border:1px solid #ddd;padding:3px 5px;text-align:right;white-space:nowrap}
td.l,th.l{text-align:left}.note{color:#666;font-size:.85em}.g{background:#e6f4ea}.y{background:#fff6dd}
@media(prefers-color-scheme:dark){body{background:#111;color:#ddd}.box{background:#1d2230}td,th{border-color:#444}.g{background:#1f3a26}.y{background:#3a3420}}</style>"""


def p(x, d=1):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—"
    return "—" if not np.isfinite(x) else f"{x * 100:+.{d}f}%"


def main():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    C = pd.read_csv(os.path.join(OUT, "cells.csv"))
    FP = pd.read_csv(os.path.join(OUT, "fake_p.csv")); RL = pd.read_csv(os.path.join(OUT, "real.csv"))
    SG = pd.read_csv(os.path.join(OUT, "single.csv"))
    ck = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else {}
    cnt = S["各段標籤格數（M 臂 60 格）"]; v = S["整套判定"]; z = S["0050"]
    M = C[(C["出場"] == "ema") & (C["臂"] == "M")]
    H = ["<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
         "<title>爆量突破跌破EMA出</title>", CSS, "</head><body>", "<h1>爆量突破進場、收盤跌破 EMA 出場（Threads 作者指標；60 種設定全報）</h1>"]
    if v.startswith("合格"):
        sent = f"爆量突破進、跌破 EMA 出，60 種設定有 {cnt['確認']['合格']} 種在 2022～2026、{cnt['探索']['合格']} 種在 2017～2021 贏 0050 且風險調整後不輸"
    elif v.startswith("另列"):
        sent = "多數設定報酬贏 0050，但回落比例上不划算"
    else:
        sent = f"60 種設定只有 {cnt['確認']['合格']} 種在 2022～2026 合格（2017～2021 有 {cnt['探索']['合格']} 種），不構成可用規則"
    ms = S["M−S（描述）"]; fx = S["EMA 出場 − 固定抱（描述）"]
    H.append(f"<div class='box{'' if v.startswith('合格') else ' bad'}'><b>判定（整套一判）：{v}</b>。{sent}。<br>"
             f"爆量條件加了多少（M − S，年化中位差）：確認段中位 {ms['確認']['中位（點）']:+.2f} 點（{ms['確認']['M−S＞0 的格數／60']}／60 格為正）、探索段 {ms['探索']['中位（點）']:+.2f} 點。<br>"
             f"EMA 出場 − 固定抱 60 天：確認段中位 {fx['確認']['H60']['中位（點）']:+.2f} 點（20 天 {fx['確認']['H20']['中位（點）']:+.2f}、120 天 {fx['確認']['H120']['中位（點）']:+.2f}）。<br>"
             f"作者原參數不明，用常見值網格（B 突破天數 × k 爆量倍數 × L 均線天數 ＝ 60 格）。</div>")
    H.append(f"<p class='note'>合格門檻：兩段各 ≥ 31 格合格。各段格數（合格／另列／不合格）：探索 {cnt['探索']['合格']}／{cnt['探索']['另列']}／{cnt['探索']['不合格']}、"
             f"確認 {cnt['確認']['合格']}／{cnt['確認']['另列']}／{cnt['確認']['不合格']}、早年（2005～2014，只上市）{cnt['早年']['合格']}／{cnt['早年']['另列']}／{cnt['早年']['不合格']}。"
             f"0050：探索 {p(z['探索']['cagr'])}／{p(z['探索']['mdd'])}、確認 {p(z['確認']['cagr'])}／{p(z['確認']['mdd'])}、早年 {p(z['早年']['cagr'])}／{p(z['早年']['mdd'])}。"
             f"這是全部選到的股票平均起來的結果，不是對某一檔的預測。50 顆抽籤種子取中位；成本來回 0.585%；母體閘新口徑（GATE_V2）。</p>")
    for seg in ("確認", "探索", "早年"):
        x = M[M["段"] == seg]
        H.append(f"<h2>{seg}段：60 格年化中位（綠＝合格、黃＝另列）</h2><div class='wrap'><table><tr><th class='l'>B × k</th>" + "".join(f"<th>L{L}</th>" for L in (5, 10, 20, 60)) + "</tr>")
        for B in (5, 10, 20, 60, 120):
            for k in (1.5, 2.0, 3.0):
                tds = []
                for L in (5, 10, 20, 60):
                    q = x[(x["B"] == B) & (x["k"].astype(float) == k) & (x["L"] == L)].iloc[0]
                    cls = " class='g'" if q["標籤"] == "合格" else (" class='y'" if q["標籤"] == "另列" else "")
                    tds.append(f"<td{cls}>{p(q['年化中位'])}／{p(q['回落中位'], 0)}</td>")
                H.append(f"<tr><td class='l'>B{B} k{k}</td>{''.join(tds)}</tr>")
        H.append("</table></div>")
    g = S["分組合格格數（描述）"]
    H.append("<h2>分組合格格數（描述，⛔ 不據此挑格）</h2><div class='wrap'><table><tr><th class='l'>段</th>" + "".join(f"<th>{k}</th>" for k in g["確認"]) + "</tr>")
    for seg, d in g.items():
        H.append(f"<tr><td class='l'>{seg}</td>" + "".join(f"<td>{vv}</td>" for vv in d.values()) + "</tr>")
    H.append("</table></div>")
    H.append(f"<h2>對照（描述）</h2><ul><li>隨機出場（確認段、同進場、持有天數抽自本格，每格 100 次）：p ＜ 0.05 的格 {S['隨機出場（確認段）']['p＜0.05 的格數／60']}／60，p 中位 {S['隨機出場（確認段）']['p 中位']:.2f}</li>"
             f"<li>現實版（確認段：每邊多 0.3%＋50 萬衝擊＋均價成交）：合格 {S['現實版（確認段）']['合格格數／60']}／60、另列 {S['現實版（確認段）']['另列']}</li>"
             f"<li>EMA 出場比固定抱好的格數（確認段）：20 天 {fx['確認']['H20']['EMA 較好格數／60']}、60 天 {fx['確認']['H60']['EMA 較好格數／60']}、120 天 {fx['確認']['H120']['EMA 較好格數／60']}（／60）</li>"
             f"<li>S 臂（不看量）：M − S ＞ 0 的格數 探索 {ms['探索']['M−S＞0 的格數／60']}、確認 {ms['確認']['M−S＞0 的格數／60']}、早年 {ms['早年']['M−S＞0 的格數／60']}（／60）</li>"
             f"<li>退化標記（探索段平均持有 ＜ 2 日）：{S['退化標記格數（探索段）']} 格</li></ul>")
    x = M[M["段"] == "確認"]
    H.append(f"<p>確認段交易面（60 格平均）：每顆交易 {x['trades'].mean():.0f} 筆、勝率 {x['win'].mean():.1%}、賺賠比 {x['payoff'].mean():.2f}、平均持有 {x['hold'].mean():.1f} 天、"
             f"年換手 {x['turn'].mean():.1f} 倍、空倉比例 {x['cash'].mean():.1%}；逐格見 cells.csv。</p>")
    s2 = SG[(SG["段"] == "確認") & (SG["H"] == 20)]
    if len(s2):
        H.append("<h2>單筆層（描述）：訊號後 20 天 vs 同日同前 20 日漲幅十分位的股票（確認段）</h2><div class='wrap'><table><tr><th class='l'>B × k</th><th>筆數</th><th>X 平均</th><th>95% CI（月分群）</th><th>扣成本後平均</th></tr>")
        for r in s2.to_dict("records"):
            H.append(f"<tr><td class='l'>B{r['B']} k{r['k']}</td><td>{int(r['n']):,}</td><td>{p(r['X 平均'], 2)}</td><td>{p(r['lo'], 2)}～{p(r['hi'], 2)}</td><td>{p(r['R−成本 平均'], 2)}</td></tr>")
        H.append("</table></div><p class='note'>其他 H（5／10／60 天）、各段見 single.csv。</p>")
    pv = S["先驗（登錄 §六）"]
    H.append("<h2>先驗（登錄 §六）</h2><ul>" + "".join(f"<li>{k}：{'中' if vv else '沒中'}</li>" for k, vv in pv.items()) + "</ul>")
    H.append("<h2>做法與查核</h2><ul><li>規則照作者程式碼：收盤突破前 B 日最高價且收紅K、當日量 ＞ k 倍前 20 日均量 ⇒ 次日開盤買；收盤 ＜ EMA(L) ⇒ 次日開盤賣；可再進場；10 檔、每檔投入當時淨值 1/10、多選一抽籤。</li>"
             "<li>執行者補：訊號日自己收在 EMA 下 ⇒ 不進（同訊號系統骨架）；早年段母體用流動性＋K 棒數（2012-06 前無個股法人）；種子數主格 50、固定持有 10、隨機出場 100、現實版 10（耗時）。</li>"
             f"<li>查核：{ck.get('結論', '（未跑）')}</li><li>出處：backtest/researchVolBreak.py、resultsVolBreak/（summary.json、cells.csv、seeds.csv.gz、fake_p.csv、real.csv、m_minus_s.csv、ema_vs_fixed.csv、single.csv、check.json）</li></ul></body></html>")
    open(os.path.join(OUT, "爆量突破跌破EMA出.html"), "w", encoding="utf-8").write("\n".join(H))
    print("ok")


if __name__ == "__main__":
    main()
