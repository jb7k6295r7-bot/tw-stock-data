# -*- coding: utf-8 -*-
"""PREREG品質 A0 定案重跑 網頁（resultsQualA0/REPORT.html）：先講判定、A2→A0 差異、手機可讀。只讀 summary.json、diff_A2_A0.json、check.json、cells.csv。"""
import json
import os

import pandas as pd

OUT = os.path.expanduser("~/tw-p17/backtest/resultsQualA0")
CSS = """<style>body{font-family:-apple-system,'Noto Sans TC',sans-serif;margin:0 auto;max-width:760px;padding:0 16px 40px;line-height:1.6;color:#222;background:#fff}
h1{font-size:1.3em}h2{font-size:1.1em;margin-top:1.6em;border-bottom:1px solid #ddd}.box{background:#f4f6fa;border-left:4px solid #3a6;padding:10px 12px;margin:12px 0}
.bad{border-left-color:#c44}.wrap{overflow-x:auto}table{border-collapse:collapse;font-size:.9em;min-width:100%}td,th{border:1px solid #ddd;padding:4px 6px;text-align:right;white-space:nowrap}
td.l,th.l{text-align:left}.note{color:#666;font-size:.85em}@media(prefers-color-scheme:dark){body{background:#111;color:#ddd}.box{background:#1d2230}td,th{border-color:#444}}</style>"""
QN = {"Q1": "ROE", "Q2": "營業利益÷資產", "Q3": "ROA", "Q4": "研發強度", "量": "成交量相對放大"}


def p(x, d=2):
    return f"{x * 100:+.{d}f}%"


def cellname(k):
    fam, q, fq, n = k.split("_")
    return f"{'單用' if fam == '甲' else '營收創高池內'}・{QN[q]}・{fq}換・{n[1:]} 檔"


def main():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    Df = json.load(open(os.path.join(OUT, "diff_A2_A0.json"), encoding="utf-8"))
    ck = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else {}
    PK = S["挑格"]; z = S["0050"]
    H = ["<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
         "<title>品質因子 A0 定案</title>", CSS, "</head><body>", "<h1>品質因子選股：財報可用日改 A0（上傳時戳）定案重跑</h1>"]
    li = []
    for fam, nm in (("甲", "甲族（單用品質）"), ("乙", "乙族（月營收創 24 月新高池內用品質挑）")):
        k = PK[fam]; d = Df["挑中格"][fam]
        pre = "隨機挑也做得到：" if k["假訊號_確認"]["p（隨機年化 ≥ 本格）"] >= 0.05 else ""
        li.append(f"<li>{pre}<b>{nm}</b> 挑中「{cellname(k['格'])}」：確認段 {p(k['確認']['年化'])}／{p(k['確認']['回落'])} {k['確認']['標籤']}、"
                  f"早年段 {p(k['早年']['年化'])}／{p(k['早年']['回落'])} {k['早年']['標籤']} ⇒ <b>{k['件標籤']}</b>"
                  f"（A2 暫定版：{cellname(d['A2'])}，{d['件標籤 A2']}）</li>")
    same = all(Df["挑中格"][f]["件標籤 A2"] == Df["挑中格"][f]["件標籤 A0"] for f in ("甲", "乙"))
    H.append(f"<div class='box bad'><b>判定（A0 定案）</b><ul>{''.join(li)}</ul>"
             f"A2→A0：兩族件標籤{'都沒變' if same else '有變'}。0050 確認段 {p(z['確認']['年化'])}／{p(z['確認']['回落'])}、早年段 {p(z['早年']['年化'])}／{p(z['早年']['回落'])}。</div>")
    H.append("<p class='note'>只差在財報可用日：有上傳時戳（2019～2026）用「該季最早上傳日的下一個交易日」，沒有時戳的季（2019 以前幾乎全部）照舊用法定期限＋5 個交易日。"
             "程式一字未改。這是全部選到的股票平均起來的結果，不是對某一檔的預測。</p>")
    if "乙" in PK and "同池用量挑（營量 v1 挑法）" in PK["乙"]:
        v = PK["乙"]["同池用量挑（營量 v1 挑法）"]
        H.append(f"<p>乙族同池改用成交量挑（營量 v1 挑法）：確認段 {p(v['確認']['年化'])}／{p(v['確認']['回落'])} {v['確認']['標籤']}；品質挑 − 量挑 ＝ {v['確認 品質 − 量（點）']:+.2f} 點。</p>")
    H.append("<h2>A2 → A0 差在哪</h2><div class='wrap'><table><tr><th class='l'>項</th><th class='l'>A2 暫定</th><th class='l'>A0 定案</th></tr>")
    for fam in ("甲", "乙"):
        d = Df["挑中格"][fam]
        H.append(f"<tr><td class='l'>{fam}族 挑中格</td><td class='l'>{cellname(d['A2'])}</td><td class='l'>{cellname(d['A0'])}</td></tr>")
        H.append(f"<tr><td class='l'>{fam}族 確認段</td><td class='l'>{p(d['確認 A2'][0])}／{p(d['確認 A2'][1])} {d['確認 A2'][2]}</td><td class='l'>{p(d['確認 A0'][0])}／{p(d['確認 A0'][1])} {d['確認 A0'][2]}</td></tr>")
        H.append(f"<tr><td class='l'>{fam}族 早年段</td><td class='l'>{p(d['早年 A2'][0])} {d['早年 A2'][1]}</td><td class='l'>{p(d['早年 A0'][0])} {d['早年 A0'][1]}</td></tr>")
        H.append(f"<tr><td class='l'>{fam}族 件標籤</td><td class='l'>{d['件標籤 A2']}</td><td class='l'>{d['件標籤 A0']}</td></tr>")
        H.append(f"<tr><td class='l'>{fam}族 假訊號 p（確認）</td><td class='l'>{d['假訊號確認 p A2']:.3f}</td><td class='l'>{d['假訊號確認 p A0']:.3f}</td></tr>")
    H.append("</table></div>")
    av = Df["可用日來源"]
    H.append("<p>財報季的可用日：" + "；".join(f"{k}：{v['季數']:,} 季，A2 有時戳 {v['A2 有時戳']:,}、A0 有時戳 {v['A0 有時戳']:,}，可用日變動 {v['可用日變動的季']:,} 季（變早中位 {v['變早（交易日）中位']:.0f} 個交易日、變晚 {v['變晚的季']} 季）" for k, v in av.items()) + "。</p>")
    fl = Df["判定格標籤翻轉（段 × 格）"]
    H.append(f"<p>48 個判定格 × 三段裡，標籤翻轉 {len(fl)} 處" + ("：" + "；".join(f"{cellname(x['格'])}｜{x['段']} {x['標籤_A2']}→{x['標籤_A0']}" for x in fl[:12]) if fl else "") + "。</p>")
    H.append("<p>各段全格年化差（A0−A2，點）：" + "；".join(f"{k} 中位 {v['中位']:+.2f}、最大 {v['最大絕對']:.2f}" for k, v in Df["全格年化差（點）"].items()) + "</p>")
    C = pd.read_csv(os.path.join(OUT, "cells.csv"))
    c = C[(C["段"] == "確認") & C["判定格"]]
    H.append("<h2>全部判定格（確認段，A0）</h2><div class='wrap'><table><tr><th class='l'>族</th><th class='l'>量測</th>" + "".join(f"<th>{f} N{n}</th>" for f in ("月", "季", "半年") for n in (10, 20)) + "</tr>")
    for fam in ("甲", "乙"):
        for q in ("Q1", "Q2", "Q3", "Q4"):
            row = [f"<td class='l'>{fam}</td><td class='l'>{QN[q]}</td>"]
            for f in ("月", "季", "半年"):
                for n in (10, 20):
                    x = c[c["格"] == f"{fam}_{q}_{f}_N{n}"].iloc[0]
                    row.append(f"<td>{x['年化'] * 100:+.1f}%／{x['回落'] * 100:+.1f}% {x['標籤']}</td>")
            H.append("<tr>" + "".join(row) + "</tr>")
    H.append("</table></div>")
    H.append("<h2>查核</h2><ul>")
    H.append(f"<li>獨立查核 researchQual_check（⛔ 不 import 本體；路徑改 A0 版）：{json.dumps({k: v for k, v in ck.items() if k != '時間'}, ensure_ascii=False)[:600]}</li>")
    H.append("<li>出處：backtest/researchQualA0.py（import researchQual 一字未改、只換財報快照）、resultsQualA0/summary.json、cells.csv、picks.csv.gz、fake.csv.gz、diff_A2_A0.json、check.json</li></ul></body></html>")
    open(os.path.join(OUT, "REPORT.html"), "w", encoding="utf-8").write("\n".join(H))
    print("ok")


if __name__ == "__main__":
    main()
