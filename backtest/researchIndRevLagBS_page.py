# -*- coding: utf-8 -*-
"""PREREG產業落後買賣點 seq2 的網頁（讀 backtest/resultsIndRevLag/buysell/ 的輸出，⛔ 不重算）。由 researchIndRevLagBS --page 呼叫。"""
from __future__ import annotations

import html
import json
import os

import numpy as np
import pandas as pd

ORDER = ["B0|T60", "B0|T120", "B0|T250", "B0|T無上限", "B1|T60", "B1|T120", "B1|T250", "B1|T無上限"]


def bname(k):
    b, t = k.split("|")
    bb = "照原本買" if b == "B0" else "轉強才買"
    tt = "不設天數" if t == "T無上限" else f"最多抱 {t[1:]} 天"
    return f"{bb}＋{tt}"


def page(OUT):
    e = html.escape
    M = json.load(open(os.path.join(OUT, "meta.json"), encoding="utf-8"))
    TM = pd.read_csv(os.path.join(OUT, "cells.csv")).set_index("key")
    YR = pd.read_csv(os.path.join(OUT, "years.csv"))
    CKp = os.path.join(OUT, "check.json"); CK = json.load(open(CKp, encoding="utf-8")) if os.path.exists(CKp) else None
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0]
    CSS += ("\ntd.l,th.l{text-align:left;white-space:normal}small{color:#666}.warn{border-left:4px solid #d64045;padding:6px 10px;background:#fff4f4}"
            ".ok{border-left:4px solid #2b6cb0;padding:8px 12px;background:#eef4fb}.big{font-size:1.05rem}li{margin:.35em 0}"
            "details{margin:.6em 0}summary{font-weight:600;cursor:pointer;padding:4px 0}tr.pick td{background:#fffbe6}")
    P1 = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:+.1f}%"
    PC = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:.0f}%"
    F2 = lambda v: "—" if v is None or not np.isfinite(v) else f"{v:.2f}"
    G = M["挑格"]; Z = M["0050"]; CT = M["對照"]; ck = G["挑中"]; prev = CT["seq2挑中格（原買賣點）"]; fk = CT["假訊號臂"]; yl = CT["營量v1_T1"]
    EA = M["吃到起漲到頂"]
    nolim = f"{ck.split('|')[0]}|T無上限"
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>產業落後買賣點改版</title>", f"<style>{CSS}</style></head><body><main>", "<h1>產業營收落後：買賣點改版回測</h1>",
         "<p class='warn'>⚠ <b>事後重切</b>：買賣點是看過上一版（營收加速但股價落後）全部結果之後才改的，所以就算兩段都過，最多也只算「暫定」、只進前瞻紀錄。"
         "這是歷史回測的描述，<b>不是買賣建議</b>。</p>"]
    cf, ea, ex = G["確認"], G["早年"], G["探索"]

    def eat(k, sg):
        d = EA.get(f"{k}|{sg}") or {}
        return d.get("實際持有吃到幾成中位", np.nan), d.get("筆數", 0)
    e_me = [eat(ck, sg) for sg in ("探索", "確認", "早年")]; e_pv = [eat("seq2原買賣點", sg) for sg in ("探索", "確認", "早年")]
    H.append(f"<div class='ok big'><b>結論：判定【{e(G['判定'])}】。</b><ul>"
             f"<li>挑同一種產業（營收加速、股價落後，沿用上一版挑中的那一格），8 種買賣點在 2017～2021 挑出的是：<b>{e(bname(ck))}</b>"
             f"（買：{'選出就買' if ck.startswith('B0') else '等產業指數站上 60 日線才買'}；賣：{'抱滿天數、' if 'T無上限' not in ck else ''}產業跌破年線、個股出真頂，任一先到）。</li>"
             f"<li>2022-01～2026-08：年化 {P1(cf['年化'])}、最大回落 {P1(cf['回落'])}；0050 {P1(Z['確認']['年化'])}／{P1(Z['確認']['回落'])} ⇒ <b>{e(G['確認標籤'])}</b>。"
             f"早年 2012-06～2014：{P1(ea['年化'])}／{P1(ea['回落'])}；0050 {P1(Z['早年']['年化'])}／{P1(Z['早年']['回落'])} ⇒ <b>{e(G['早年標籤'])}</b>。</li>"
             f"<li>跟上一版原本的買賣點（同窗重跑）比，確認段 {P1(cf['年化'])} vs {P1(prev['確認']['年化'])}，早年 {P1(ea['年化'])} vs {P1(prev['早年']['年化'])}。</li>"
             f"<li>跟「假訊號」比（同樣買法，但隨機挑一天整個產業賣掉、持有天數分佈相同，1,000 次）：確認段假訊號中位 {P1(fk['確認']['中位'])}，"
             f"假訊號比挑中格好的比例 {PC(fk['確認']['p_年化（假訊號 ≥ 挑中格）'])}。營量 v1 同窗確認段 {P1(yl['確認']['年化'])}。</li>"
             f"<li>賣點離頂多近（吃到起漲到頂幾成，中位）：本件挑中格 探索 {PC(e_me[0][0])}、確認 {PC(e_me[1][0])}、早年 {PC(e_me[2][0])}；"
             f"上一版原買賣點 {PC(e_pv[0][0])}、{PC(e_pv[1][0])}、{PC(e_pv[2][0])}（產業指數口徑）。</li>"
             f"<li>8 格裡兩段都合格的有 {G['兩段都合格格數']} 格（確認段合格 {G['確認段合格格數']}、早年段合格 {G['早年段合格格數']}）。</li>"
             "</ul></div>")
    if CK:
        H.append(f"<p class='note'>查核：{'通過' if CK['通過'] else '⛔ 不通過'}（不同 {CK['不同項數']} 項；另一套寫法重算起漲點、真頂第一天、整條權益與每筆交易）。讀法寫死 {e(M['讀法寫死'])}。</p>")
    # 一、8 格
    H.append("<h2>一、8 種買賣點（三段）</h2><div class='wrap'><table><tr><th class='l'>買賣點</th><th>探索<br><small>2017-03～2021（挑）</small></th><th>確認<br><small>2022～2026-08</small></th>"
             "<th>早年<br><small>2012-06～2014</small></th><th>平均持股／現金<br><small>探索</small></th></tr>")
    for k in ORDER:
        r = TM.loc[k]
        H.append(f"<tr class='{'pick' if k == ck else ''}'><td class='l'>{e(bname(k))}{' ⭐挑中' if k == ck else ''}{'<br><small>退化（排除）</small>' if r['退化'] else ''}</td>"
                 + "".join(f"<td>{P1(r[f'{sg}_年化'])}<br><small>回落 {P1(r[f'{sg}_回落'])}・{e(str(r[f'{sg}_標籤']))}</small></td>" for sg in ("探索", "確認", "早年"))
                 + f"<td>{r['探索_平均持股']:.1f}／{PC(r['探索_現金比例'])}</td></tr>")
    H.append(f"<tr><td class='l'>0050</td>" + "".join(f"<td>{P1(Z[sg]['年化'])}<br><small>回落 {P1(Z[sg]['回落'])}</small></td>" for sg in ("探索", "確認", "早年")) + "<td></td></tr>")
    H.append("</table></div>")
    H.append(f"<p class='note'>挑法：先排除平均持股不到 3 檔或現金超過 30% 的格（{G['退化格數']} 格{'；8 格都退化 ⇒ 從 8 格挑' if G['8格都退化'] else ''}），"
             f"再看 2017～2021 有沒有過判準（年化 ＞ 0050 且 年化÷|回落| ≥ 0050；過的有 {G['探索過判準格數']} 格），"
             f"{'過的裡面' if G['探索過判準格數'] else '都沒過 ⇒ 全部裡面'}取「年化÷|回落|」最高。判定取確認段、早年段較嚴的那個。</p>")
    # 二、對照
    H.append("<h2>二、跟誰比</h2><div class='wrap'><table><tr><th class='l'>項</th><th>探索</th><th>確認</th><th>早年</th></tr>")
    fm = lambda d: f"{P1(d['年化'])}<br><small>回落 {P1(d['回落'])}</small>" if d else "—"
    H.append(f"<tr class='pick'><td class='l'><b>本件挑中格</b>（{e(bname(ck))}）</td><td>{fm(ex)}</td><td>{fm(cf)}<br><b>{e(G['確認標籤'])}</b></td><td>{fm(ea)}<br><b>{e(G['早年標籤'])}</b></td></tr>")
    if nolim != ck:
        r = TM.loc[nolim]
        H.append(f"<tr><td class='l'>同買法、不設天數（並報）</td>" + "".join(f"<td>{P1(r[f'{sg}_年化'])}<br><small>回落 {P1(r[f'{sg}_回落'])}</small></td>" for sg in ("探索", "確認", "早年")) + "</tr>")
    H.append(f"<tr><td class='l'>上一版原買賣點（營收不再加速／股價不再落後才賣；同窗重跑）</td><td>{fm(prev['探索'])}</td><td>{fm(prev['確認'])}</td><td>{fm(prev['早年'])}</td></tr>")
    H.append(f"<tr><td class='l'>0050</td><td>{fm(Z['探索'])}</td><td>{fm(Z['確認'])}</td><td>{fm(Z['早年'])}</td></tr>")
    H.append(f"<tr><td class='l'>營量 v1（引前件）</td><td>{fm(yl['探索'])}</td><td>{fm(yl['確認'])}</td><td>{fm(yl['早年'])}<br><small>窗 2012-06-04～2014-12-31</small></td></tr>")
    H.append("<tr><td class='l'>假訊號（同買法、隨機日整個產業賣，1,000 次中位）</td>" + "".join(
        f"<td>{P1(fk[sg]['中位'])}<br><small>p10～p90 {P1(fk[sg]['p10'])}～{P1(fk[sg]['p90'])}・假訊號 ≥ 挑中格 {PC(fk[sg]['p_年化（假訊號 ≥ 挑中格）'])}</small></td>" for sg in ("探索", "確認", "早年")) + "</tr>")
    H.append("</table></div>")
    # 三、先驗
    H.append("<h2>三、事前猜測對答</h2><div class='wrap'><table><tr><th>#</th><th class='l'>猜測</th><th class='l'>結果</th><th>對錯</th></tr>")
    for k, pr, rs, ok in M["先驗"]:
        H.append(f"<tr><td>{k}</td><td class='l'>{e(pr)}</td><td class='l'>{e(rs)}</td><td><b>{e(ok)}</b></td></tr>")
    H.append("</table></div>")
    # 四、必報
    H.append("<h2>四、必報</h2><h3>出場原因（次數）</h3><div class='wrap'><table><tr><th class='l'>買賣點｜段</th><th>產業層<br><small>抱滿天數／跌破年線／窗尾仍持有</small></th>"
             "<th>個股層賣出<br><small>真頂／天數／年線</small></th><th>持有段數</th><th>持有天數<br><small>平均／中位</small></th></tr>")
    for k in ORDER:
        r = TM.loc[k]
        for sg in ("探索", "確認", "早年"):
            H.append(f"<tr class='{'pick' if k == ck else ''}'><td class='l'>{e(bname(k))}｜{sg}</td><td>{int(r[f'{sg}_產業出場T'])}／{int(r[f'{sg}_產業出場Y'])}／{int(r[f'{sg}_窗尾仍持有'])}</td>"
                     f"<td>{int(r[f'{sg}_個股賣Z'])}／{int(r[f'{sg}_個股賣T'])}／{int(r[f'{sg}_個股賣Y'])}</td><td>{int(r[f'{sg}_產業持有段數'])}</td>"
                     f"<td>{F2(r[f'{sg}_平均持有天數'])}／{F2(r[f'{sg}_持有天數中位'])}</td></tr>")
    H.append("</table></div><p class='note'>產業層 ＝ 整個產業一起賣；個股層 ＝ 每檔股票被賣的原因（真頂只賣那一檔，錢留著等整個產業出場）。</p>")
    H.append("<h3>轉強才買：等多久、放棄幾次</h3><div class='wrap'><table><tr><th class='l'>買賣點｜段</th><th>選出次數</th><th>等到買進</th><th>當天已站上</th>"
             "<th>等待天數中位<br><small>買進者</small></th><th>放棄① 等滿兩個月</th><th>放棄② 條件不在</th><th>窗尾仍在等</th></tr>")
    for k in ORDER[4:]:
        r = TM.loc[k]
        for sg in ("探索", "確認", "早年"):
            H.append(f"<tr class='{'pick' if k == ck else ''}'><td class='l'>{e(bname(k))}｜{sg}</td><td>{int(r[f'{sg}_等待次數'])}</td><td>{int(r[f'{sg}_等待後買進'])}</td>"
                     f"<td>{int(r[f'{sg}_等待0天（當天已站上）'])}</td><td>{F2(r[f'{sg}_等待天數中位（買進者）'])}</td><td>{int(r[f'{sg}_放棄①'])}</td><td>{int(r[f'{sg}_放棄②'])}</td><td>{int(r[f'{sg}_窗尾仍在等'])}</td></tr>")
    H.append("</table></div>")
    H.append("<h3>賣點離頂多近：吃到起漲到頂幾成（中位）</h3><div class='wrap'><table><tr><th class='l'>買賣點</th><th>探索</th><th>確認</th><th>早年</th></tr>")
    for k in ORDER + ["seq2原買賣點"]:
        nm = bname(k) if k != "seq2原買賣點" else "上一版原買賣點"
        H.append(f"<tr class='{'pick' if k == ck else ''}'><td class='l'>{e(nm)}</td>" + "".join(
            f"<td>{PC(eat(k, sg)[0])}<br><small>{eat(k, sg)[1]} 段</small></td>" for sg in ("探索", "確認", "早年")) + "</tr>")
    H.append("</table></div><p class='note'>吃到幾成 ＝（出場時產業指數 ÷ 進場前一天）÷（之後 500 日最高 ÷ 進場前 250 日最低），取對數比；100% ＝ 從起漲低點到之後最高點全吃到，"
             "0% ＝ 白抱、負的 ＝ 賠。用產業指數算（同上一版口徑），個股層真頂提早賣的部分不在這個數字裡。</p>")
    # 窗尾與無上限
    H.append("<h3>不設天數的兩格、窗尾還抱著什麼</h3><ul class='note'>")
    for k in sorted({ck, nolim, "B0|T無上限", "B1|T無上限"}, key=ORDER.index):
        d = M["細項"][k]
        for part, nm in (("main", "主段"), ("early", "早年")):
            w = d[f"{part}_窗尾"]; hd = d[f"{part}_持有天數分佈"]
            ind = "、".join(f"{x['產業']}（{x['進場日']} 進、已 {x['已持有交易日']} 日、{x['仍持有檔數']} 檔）" for x in w["產業"]) or "無"
            wait = "、".join(f"{x['ind']}" for x in w["仍在等"]) or "無"
            H.append(f"<li><b>{e(bname(k))}</b>｜{nm}：窗尾 {w['窗尾']} 仍持有 {e(ind)}；仍持有股票共 {w['仍持有檔數（含延後賣）']} 檔；仍在等的產業 {e(wait)}。"
                     + (f"持有天數 {hd['筆數']} 段，中位 {hd['p50']:.0f}、p25～p75 {hd['p25']:.0f}～{hd['p75']:.0f}、最長 {hd['最長']}；≤21 日 {hd['≤21']}、22～63 日 {hd['22～63']}、64～250 日 {hd['64～250']}、＞250 日 {hd['＞250']}。" if hd.get("筆數") else "")
                     + "</li>")
    H.append("</ul>")
    H.append("<h3>各年報酬</h3><div class='wrap'><table><tr><th>年</th><th>本件挑中格</th><th>上一版原買賣點</th><th>0050</th></tr>")
    for _, r in YR.iterrows():
        H.append(f"<tr><td>{r['年']}{'<small>（早年段）</small>' if r['段'] == 'early' else ''}</td><td>{P1(r['挑中格'])}</td><td>{P1(r['seq2原買賣點'])}</td><td>{P1(r['0050'])}</td></tr>")
    H.append("</table></div><p class='note'>首年、末年是不滿一年的窗內報酬。逐段明細見 episodes.csv、waits.csv、sells.csv.gz、eat.csv。</p>")
    # 五、真頂
    sw = M["飆股資料"]
    H.append("<h2>五、個股「真頂」怎麼認</h2><ul class='note'>"
             "<li>用回測線 10/6 的 T1 定義：股票被處置後出關、或從起漲點以來已處置過又再次進處置，而且當天收盤還在近 20 根 K 棒最高收盤的九成以上 ⇒ 隔天開盤賣這一檔。</li>"
             "<li><b>起漲點只用當天以前的價格認</b>：每天收盤，往前 250 個交易日找最高收盤，再找最高收盤之前的最低收盤日當起漲點；若起漲點比買進日還晚，改用買進日往前 250 日找；"
             "若那段漲勢在買進前已從最高跌掉 30%，改用跌完到買進日之間的最低點。這跟每日追蹤工具（surge_flow_daily）的規則逐字相同，查核時直接呼叫它逐日比對。</li>"
             "<li>價格用還原收盤；之後才發生的除權息只會把整段價格同乘一個數，最高、最低、跌幅都不變，所以等於當時看得到的價格。</li>"
             f"<li>處置資料 2010-12 起；飆股資料母體沒有的股票沒有真頂訊號：主段 {len(sw['main'].get('不在飆股母體的檔', []))} 檔、早年 {len(sw['early'].get('不在飆股母體的檔', []))} 檔。</li></ul>")
    # 六、讀法
    H.append("<h2>六、資料與執行者補的讀法</h2><ul class='note'>"
             "<li>挑產業沿用上一版挑中格（營收加速前三分之一裡、近 250 日股價漲最少的 1 個產業，買市值前 20 大），每月營收可用日收盤判、隔天開盤做；成本來回 0.585%。</li>"
             "<li>★ 站上／跌破 ＝ 收盤嚴格大於／小於均線；均線要湊滿 60 或 240 天才算。</li>"
             "<li>★ 轉強才買：選出當天收盤已在 60 日線上就隔天買；之後每天收盤看。放棄②（加速不在、或不在前三分之一、或股價已不落後）在檢查日先判；"
             "放棄①＝選出後第 2 個檢查日收盤仍沒站上。剛放棄的產業當天不再選，下個檢查日起可再選。</li>"
             "<li>★ 抱滿 T 天 ＝ 買進那天算第 1 天，第 T 天收盤賣（專案慣例）；那天停牌或收盤跌停就延到之後第一個能開盤賣的日子。</li>"
             "<li>★ 跌破年線要先「上膛」：買進前一天收盤或之後曾經站上 240 日線，之後第一次收盤跌破才賣。</li>"
             "<li>★ 假訊號：同買法，不用三條賣點，改成每次進場時從挑中格同段的持有天數裡隨機抽一個，到期整個產業賣。</li>"
             "<li>早年段用上市＋上櫃版面，但上櫃沒有法人資料 ⇒ 挑股實際只有上市；產業指數含上櫃（同上一版標註）。2005～2012-05 不可判定。</li>"
             "<li>偏離：確認段資料尾沿用上一版 2026-08-24；營量 v1 引前件數字（舊母體口徑）。</li></ul>")
    H.append("</main></body></html>")
    open(os.path.join(OUT, "產業落後買賣點改版.html"), "w", encoding="utf-8").write("\n".join(H))
    print("[網頁] 完成", flush=True)
