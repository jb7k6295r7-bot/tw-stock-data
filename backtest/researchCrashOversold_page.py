# -*- coding: utf-8 -*-
"""PREREG急跌錯殺 seq1 —— 網頁（讀 resultsCrashOversold/summary.json、degeneracy.json、check.json）⇒ resultsCrashOversold/急跌錯殺.html。回測線計算子代理。"""
from __future__ import annotations

import html
import json
import os

import numpy as np
import pandas as pd

OUT = os.path.expanduser("~/tw-p17/backtest/resultsCrashOversold")
PAGE = os.path.join(OUT, "急跌錯殺.html")
SEGN = ("探索", "確認", "主窗")
CELLS = ["F1X1", "F1X2", "F2X1", "F2X2"]
CN = {"F1X1": "F1X1 營收沒變差｜修復或轉壞才賣", "F1X2": "F1X2 營收沒變差｜從最高回落 20% 才賣",
      "F2X1": "F2X1 營收＋獲利沒變差｜修復或轉壞才賣", "F2X2": "F2X2 營收＋獲利沒變差｜從最高回落 20% 才賣"}


def ok(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and np.isfinite(x)


def p(x, d=1):
    return f"{x * 100:+.{d}f}%" if ok(x) else "—"


def pp(x, d=1):
    return f"{x * 100:.{d}f}%" if ok(x) else "—"


def f1(x, d=1):
    return f"{x:.{d}f}" if ok(x) else "—"


def page():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    DJ = json.load(open(os.path.join(OUT, "degeneracy.json"), encoding="utf-8"))
    ck = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else {}
    e = html.escape
    V = S["判定"]; ch = V["挑中格"]
    G = {(r["格"], r["版本"]): r for r in S["格"]}
    Z = S["meta"]["0050"]; EA = S.get("早年") or {}
    cb, cr = G[(ch, "b")], G[(ch, "r")]
    DS = S["描述"]; FK = S["假訊號"]; YC = S["營量營飆"]
    n1 = DS["對照①急跌不看基本面"]
    # ── 結論 ──
    ew = EA.get("窗")
    eline = ""
    if ew and ch.startswith("F1"):
        eg = EA["格"][f"{ch}|b"]; egr = EA["格"][f"{ch}|r"]
        eline = (f"<li>早年 {ew[0][:4]}～{ew[1][:4]}：{p(eg['早年_年化'])}／回落 {p(eg['早年_回落'])}（{eg['早年_標籤']}；現實版 {p(egr['早年_年化'])}／{p(egr['早年_回落'])}），"
                 f"同段 0050 {p(EA['0050']['cagr'])}／{p(EA['0050']['mdd'])}。</li>")
    head = "這樣挑「急跌錯殺」，扣成本後沒有通過對 0050 的判準。" if V["判定"] == "不合格" else ""
    lead = (f"<p class=lead><b>結論：{head}判定「{e(V['判定'])}」（現實版「{e(V['現實版判定'])}」）。</b></p><ul>"
            f"<li>四格裡探索段挑中 <b>{e(CN[ch])}</b>。探索段 {p(cb['探索_年化'])}／回落 {p(cb['探索_回落'])}（{cb['探索_標籤']}：年化贏 0050 {p(Z['探索']['cagr'])}，"
            f"但回落 {p(cb['探索_回落'])} 比 0050 {p(Z['探索']['mdd'])} 深太多）。</li>"
            f"<li>確認段 2022-01～2026-08：{p(cb['確認_年化'])}／{p(cb['確認_回落'])}（{cb['確認_標籤']}），同段 0050 {p(Z['確認']['cagr'])}／{p(Z['確認']['mdd'])}。</li>"
            + eline +
            f"<li>四格沒有一格在探索段合格；兩段取較嚴 ⇒ 不合格。標籤上限本來就只到「暫定」（裁定 seq335 §四），這次沒碰到上限。</li>"
            f"<li>「基本面沒變差」這一刀：確認段 挑中格 {p(cb['確認_年化'])} vs 不看基本面的全部急跌 {p(n1['確認_年化'])}；探索段 {p(cb['探索_年化'])} vs {p(n1['探索_年化'])} ⇒ "
            + ("兩段都比較好" if (cb['確認_年化'] > n1['確認_年化'] and cb['探索_年化'] > n1['探索_年化']) else
               ("兩段都沒有比較好" if (cb['確認_年化'] <= n1['確認_年化'] and cb['探索_年化'] <= n1['探索_年化']) else "兩段方向不一致，看不出穩定的幫助")) + "。</li>"
            f"<li>假訊號臂（隨機挑同日同數量的「非急跌」股、持有天數照本件）：確認段年化中位 {p(FK['確認']['年化中位'])}，p ＝ {f1(FK['確認']['p（假訊號年化 ≥ 挑中格）'], 2)}；"
            f"探索段 p ＝ {f1(FK['探索']['p（假訊號年化 ≥ 挑中格）'], 2)}。</li>"
            f"<li>⚠ {e(S['結果句必附'][0])}。</li><li>⚠ {e(S['結果句必附'][1])}。</li>"
            "<li>N_組合 ＋1（四格挑 1）。⛔ 不是買賣建議。</li></ul>")

    def cell(r, s):
        return f"{p(r[f'{s}_年化'])}／{p(r[f'{s}_回落'])}<br><span class=m>{r[f'{s}_標籤']}</span>"
    rows = []
    for c in CELLS:
        for v, nm in (("b", "0.585%"), ("r", "現實版")):
            star = " ★" if c == ch else ""
            rows.append(f"<tr><th>{e(CN[c])}（{nm}）{star}</th>" + "".join(f"<td>{cell(G[(c, v)], s)}</td>" for s in SEGN) + "</tr>")
    rows.append("<tr><th>對照① 急跌但不看基本面（同出場）</th>" + "".join(f"<td>{cell(n1, s)}</td>" for s in SEGN) + "</tr>")
    rows.append("<tr><th>對照② 急跌而且營收變差（描述）</th>" + "".join(f"<td>{cell(DS['對照②急跌且營收變差'], s)}</td>" for s in SEGN) + "</tr>")
    rows.append("<tr><th>假訊號臂（同日同數量非急跌股）</th>" + "".join(
        f"<td>{p(FK[s]['年化中位'])}／{p(FK[s]['回落中位'])}<br><span class=m>p ＝ {f1(FK[s]['p（假訊號年化 ≥ 挑中格）'], 2)}</span></td>" for s in SEGN) + "</tr>")
    for nm in ("營飆 v1", "營飆 v1 現實版", "營量 v1", "營量 v1 現實版"):
        y = YC[nm]
        rows.append(f"<tr><th>{e(nm)}</th>" + "".join(f"<td>{p(y[s]['年化'])}／{p(y[s]['回落'])}<br><span class=m>{y[s]['標籤']}</span></td>" for s in SEGN) + "</tr>")
    rows.append("<tr><th>0050</th>" + "".join(f"<td>{p(Z[s]['cagr'])}／{p(Z[s]['mdd'])}</td>" for s in SEGN) + "</tr>")
    main_t = ("<table><thead><tr><th></th><th>探索 2017-03～2021-12</th><th>確認 2022-01～2026-08</th><th>主窗</th></tr></thead><tbody>" + "".join(rows)
              + "</tbody></table><p class=m>格內：年化中位／回落中位（200 顆抽籤種子；對照② 50 顆）；標籤對 0050 同段：合格 ＝ 年化較高且年化÷回落不低於 0050；另列 ＝ 只贏年化。"
              "p ＝ 假訊號 200 抽裡年化不輸挑中格的比例。營量／營飆引 resultsYLmargin（同窗、同引擎）。★ ＝ 探索段挑中格。</p>")
    # ── 退化 ──
    dr = []
    for c in CELLS:
        for v in ("b", "r"):
            h = DJ["持股與現金"][f"{c}|{v}"]
            dr.append(f"<tr><th>{c}（{'0.585%' if v == 'b' else '現實版'}）</th>" + "".join(
                f"<td>{f1(h[f'{s}_平均持股'], 2)} 檔／{pp(h[f'{s}_平均現金'])}<br><span class=m>候選不足月 {pp(h['候選不足'][s]['候選不足月份占比（月平均持股＜10）'], 0)}</span></td>"
                for s in SEGN) + f"<td>{'⛔ 退化' if h['探索_退化'] else '否'}</td></tr>")
    deg = (f"<p>先寫 degeneracy.json（{e(DJ['寫入時間'])}）才彙總報酬。規則：平均持股 ＜ 3 或平均現金 ＞ 30% ⇒ 照登錄排除。"
           f"<b>排除的格：{e('、'.join(DJ['排除的格（探索段退化）']) or '沒有')}</b>（四格都不退化）。</p>"
           "<table><thead><tr><th></th><th>探索</th><th>確認</th><th>主窗</th><th>探索退化</th></tr></thead><tbody>" + "".join(dr) + "</tbody></table>"
           "<p class=m>候選不足月 ＝ r＝0 那顆種子、該月平均持股 ＜ 10 檔的月份比例（10 槽沒滿就算）。</p>")
    if DJ.get("早年"):
        de = DJ["早年"]
        deg += ("<p>早年段（" + e("～".join(de["窗"])) + "）：" + "；".join(
            f"{k} {f1(h['早年_平均持股'], 2)} 檔／現金 {pp(h['早年_平均現金'])}{'（退化）' if h['早年_退化'] else ''}" for k, h in de["持股與現金"].items())
                + f"。F2 兩格：{e(de.get('F2 兩格', ''))}。</p>")
    # ── 早年 ──
    early = ""
    if ew:
        rr = []
        for k, h in EA["格"].items():
            rr.append(f"<tr><th>{e(k.replace('|b', '（0.585%）').replace('|r', '（現實版）'))}</th><td>{p(h['早年_年化'])}</td><td>{p(h['早年_回落'])}</td><td>{h['早年_標籤']}</td></tr>")
        early = ("<table><thead><tr><th></th><th>年化中位</th><th>回落中位</th><th>標籤</th></tr></thead><tbody>" + "".join(rr)
                 + f"<tr><th>0050</th><td>{p(EA['0050']['cagr'])}</td><td>{p(EA['0050']['mdd'])}</td><td></td></tr></tbody></table>"
                 f"<p class=m>早年判定窗 {e(ew[0])}～{e(ew[1])}（月營收覆蓋：上市各年 ≥ 90% 起算）；只有 F1 兩格可判，F2 要季財報（2015Q1 起）⇒ 早年不可判定（照登錄）。"
                 "早年版面的資料沒有減資事件列（資料庫補早年減資因子中），硬斷點只靠缺口 ≥ 5 日規則與斷點規則。</p>")
    # ── 必報 ──
    TS = S["逐筆"]["b"]; TA = S["逐筆（各格）"]; NE = S["等效獨立"]; OV = S["重疊"]
    hd = TS["持有天數（交易日，已出場，種子合計）"]
    must = "<ul>"
    for sg in SEGN:
        if sg in NE:
            x = NE[sg]
            must += (f"<li>{sg}：等效獨立檔數平均 {f1(x['平均N_eff'], 2)}（中位 {f1(x['N_eff中位'], 2)}；持股 {f1(x['平均持股'], 1)} 檔、兩兩相關 {f1(x['平均ρ'], 2)}）；"
                     f"最大產業占檔數中位 {f1(x['最大產業檔數中位'], 0)}、最多 {x['最大產業檔數最大']}、超過 3 檔的換股日 {pp(x['最大產業＞3檔的換股日占比'], 0)}。</li>")
    must += (f"<li>挑中格持有天數（交易日，已出場）：中位 {f1(hd['中位'], 0)}、平均 {f1(hd['平均'], 0)}、p10～p90 {f1(hd['p10'], 0)}～{f1(hd['p90'], 0)}。</li>"
             f"<li>窗尾（2026-08-24）仍持有 {f1(TS['窗尾仍持有（檔，種子中位）'], 0)} 檔（已持有天數中位 {f1(TS['窗尾仍持有已持有天數'].get('中位'), 0)}）；"
             f"一年內先跌 15%（比先漲 15% 早）：{pp(TS['一年內先跌15%比例'])}。</li>"
             "<li>出場原因（每顆種子平均筆數）：" + "；".join(
                 f"{c} " + "、".join(f"{e(k)} {f1(v, 0)}" for k, v in TA[c]["出場原因（每顆平均）"].items()) for c in CELLS) + "。</li>"
             f"<li>與營飆 v1 持股重疊率（主窗、逐日）{pp(OV['主窗']['與營飆 v1持股重疊率'])}；與營量 v1 {pp(OV['主窗']['與營量 v1持股重疊率'])}。</li>"
             f"<li>現金比例：見退化檢查表。</li></ul>")
    # ── 事件分組 ──
    ED = S["事件描述"]
    er = []
    for k, d in ED.items():
        for g, x in d.items():
            er.append(f"<tr><th>{e(k)}｜{e(g)}</th><td>{x['筆']}</td><td>{p(x['平均報酬（毛）'])}</td><td>{p(x['中位報酬（毛）'])}</td><td>{pp(x['勝率'], 0)}</td>"
                      f"<td>{f1(x['平均持有（交易日位置差）'], 0)}</td></tr>")
    evd = ("<table><thead><tr><th>分組（主窗內、挑中格的出場、逐筆、不扣成本）</th><th>筆</th><th>平均</th><th>中位</th><th>賺錢比例</th><th>平均持有日</th></tr></thead><tbody>"
           + "".join(er) + "</tbody></table><p class=m>大盤也急跌 ＝ 0050 同期 10 日報酬落在當天以前歷史最低 5%；前 60 日已大漲 ＝ 急跌前 60 日漲幅在當天母體前 10%。"
           "逐筆平均被少數大賺的拉高、中位是負的 ⇒ 要分散才吃得到平均。只描述、⛔ 不判。</p>")
    # ── 每年 ──
    yr = "".join(f"<tr><td>{y['年']}</td><td>{y['急跌事件（去重後）']}</td><td>{y['公司事件剔']}</td><td>{y['F1成立']}</td><td>{y['F1不成立']}</td><td>{y['F1不明']}</td>"
                 f"<td>{y['F2成立'] if y['年'] >= 2015 else '—'}</td><td>{y['大盤也急跌']}</td></tr>" for y in S["每年事件"])
    years = ("<table><thead><tr><th>年</th><th>急跌事件</th><th>公司事件剔</th><th>F1 成立</th><th>F1 不成立</th><th>F1 不明</th><th>F2 成立</th><th>大盤也急跌</th></tr></thead><tbody>"
             + yr + "</tbody></table><p class=m>急跌事件 ＝ 母體 R1、當天比同產業多跌最嚴重 2% 且 10 日報酬為負、同檔 20 日只取第一筆、急跌窗內沒有壞根。F2 2015 起才有季報（毛利率要比去年同季 ⇒ 2016 起才多數可判）。</p>")
    # 每年報酬
    YR = S["各年"]
    yret = "".join(f"<tr><td>{k}</td><td>{p(YR['策略'][k])}</td><td>{p(YR['策略現實版'].get(k))}</td><td>{p(YR['0050'].get(k))}</td></tr>" for k in YR["策略"])
    yret = ("<table><thead><tr><th>年</th><th>挑中格（0.585%）</th><th>現實版</th><th>0050</th></tr></thead><tbody>" + yret + "</tbody></table>"
            "<p class=m>2017 從 3/2 起、2026 到 8/24；種子中位。</p>")
    # ── 描述 ──
    dd = []
    for k, nm in (("固定5", "固定持有 5 天"), ("固定20", "固定持有 20 天"), ("固定60", "固定持有 60 天"), ("t後第5日才買", "t 後第 5 個交易日才買（等止跌）"),
                  ("0050在200日線上才買", "0050 在 200 日線上才買（擋長空頭、不是急跌保護）"), ("被公司事件排除者", "被公司事件排除的那幾筆（同出場）"),
                  ("對照①急跌不看基本面（現實版）", "對照① 現實版")):
        if k in DS:
            dd.append(f"<tr><th>{e(nm)}</th>" + "".join(f"<td>{cell(DS[k], s)}</td>" for s in SEGN) + "</tr>")
    desc = ("<table><thead><tr><th>只描述（⛔ 不判、不計 N、不當對照）</th><th>探索</th><th>確認</th><th>主窗</th></tr></thead><tbody>" + "".join(dd) + "</tbody></table>"
            f"<p class=m>固定天數只描述（seq308）；被公司事件排除者主窗只有 {DS.get('被公司事件排除者', {}).get('訊號（主窗）', '—')} 筆，組合多數時間是現金，數字不能讀。"
            "0050 濾網的角色：擋長空頭、不是急跌保護。</p>")
    # ── 先驗 ──
    PR = S["先驗"]
    p2 = PR["② 對照①（不看基本面）比本件差"]
    prior = ("<ul>"
             f"<li>① 兩段都合格的格 0 個：{'成立' if PR['① 兩段都合格的格 0 個']['成立'] else '不成立'}。</li>"
             "<li>② 對照①（不看基本面）比本件差：" + "；".join(f"{s} 挑中格 {p(v['挑中格年化'])} vs 對照① {p(v['對照①年化'])}（{'成立' if v['對照①較差（年化）'] else '不成立'}）" for s, v in p2.items()) + "。</li>"
             f"<li>③ 事件 40% 以上落在大盤也急跌：主窗 {PR['③ 事件 40% 以上落在大盤也急跌']['主窗內事件（公司事件排除後）']} 筆中 {pp(PR['③ 事件 40% 以上落在大盤也急跌']['大盤也急跌占比'])} ⇒ "
             f"{'成立' if PR['③ 事件 40% 以上落在大盤也急跌']['成立'] else '不成立'}（本件「最低 2%」是比同產業多跌，大盤一起跌的日子反而少）。</li>"
             "<li>④ X1 出場多數是修復：" + "；".join(f"{c} 修復占 {pp(v['修復占（修復＋轉壞）'], 0)}" for c, v in PR["④ X1 出場多數是修復"].items()) + "。</li></ul>")
    # ── 怎麼算 ──
    M = S["meta"]; H = M["硬斷點"]; C_ = M["事件計數"]
    notes = ("<ul>"
             "<li>母體 R1：每天 20 日均成交金額排名前 X%（X ＝ 2016-01-04 的 5,000 萬母體占比 "
             f"{pp(M['R1']['X'], 2)}），四碼普通股、排除金融保險、-DR、創新板；KY 不排；GATE_V2 開、含已下市。</li>"
             "<li>急跌：10 個交易日還原報酬減同產業（官方產業別；同產業 ＜ 5 檔用全母體）中位，當天最嚴重 2% 且 10 日報酬為負；同檔 20 日只取第一筆。</li>"
             "<li>公司事件：急跌 10 天內（含當天、13:30 後的公告算隔天）重大訊息主旨含訴訟、起訴、搜索、檢調、退票、扣押、強制執行、駭客、資安、撤銷、停工、火災、裁罰、"
             "變更交易、全額交割、重編、保留意見、繼續經營 ⇒ 不買。</li>"
             "<li>F1：最新可用月營收年增 ＞ 0 且近 3 個月合計年增 ＞ 0；F2：再加最新可用一季單季 EPS ＞ 0、單季毛利率不低於去年同季。月營收可用日：2025-12 期以前次月 10 日後、"
             "2026-01 期起 15 日後；季報用法定期限後第一個交易日。缺資料 ⇒ 不買。</li>"
             "<li>隔天開盤買、最多 10 檔等權、候選多於空位抽籤；X1：收盤回到急跌前（t−10）收盤 ⇒ 修復，或之後新公布的月營收年增 ≤ 0（F2 另加單季 EPS ≤ 0）⇒ 轉壞，隔天開盤賣；"
             "X2：從持有期最高收盤回落 20% 隔天開盤賣；⛔ 不設最長天數。</li>"
             f"<li><b>硬斷點（全線規則 seq335）：research11.load_bars 的壞根規則「缺口 ≥ 5 日即壞根」</b>（不看流動性），加幽靈事件、斷點、減資／面額變更。"
             f"急跌窗內有壞根 ⇒ 那天不算急跌（不讓停牌減資造成的假急跌佔名額）；持有中碰到壞根 ⇒ 壞根前一根收盤強制賣。"
             f"main 壞根 {H['main']['合計壞根股-日']} 股-日、早年 {H['早年']['合計壞根股-日']}；若不剔，main 最低 2% 裡會有 {C_['main']['若不剔壞根窗：其中壞根窗']} 筆是壞根窗。</li>"
             "<li>偏離：登錄寫「持有期跨停牌、減資 ⇒ 剔除」；買的當下不知道之後會停牌，事後剔除是偷看未來 ⇒ 改成壞根前收盤強制出（同 BARR 底）。</li>"
             "<li>現實版：每邊另加 0.3%、平方根衝擊（50 萬資金）、一字漲停買不到、一字跌停賣不掉、停牌買不到、進出用當日均價。</li>"
             + (f"<li>獨立查核（--check，另一支程式自己讀 csv 重算）：壞根對 load_bars、R1 的 X、抽 {len(ck.get('③ 抽樣日最低 2%', []))} 天的最低 2% 名單、全部事件的去重／公司事件／F1／F2、"
                f"抽 {ck.get('⑤ 出場抽樣', {}).get('抽筆', '—')} 筆出場 ⇒ 總不同 {ck.get('總不同', '—')}。</li>" if ck else "")
             + f"<li>讀法寫死 {e(M['讀法寫死'])}；執行 {e(M['run'])}；資料 tw-stock-data {e(M['tw-stock-data'][:10])}、價量快照 edc6f8002f；"
             "程式 backtest/researchCrashOversold.py；結果 backtest/resultsCrashOversold/。</li></ul>")
    css = """:root{--bg:#ffffff;--fg:#1d1d1b;--mut:#6b6a66;--line:#e2dfd8;--acc:#1f5f8b;--card:#ffffff}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#161615;--fg:#ecebe6;--mut:#a3a19a;--line:#33322f;--acc:#7cb6de;--card:#1e1e1c}}
:root[data-theme="dark"]{--bg:#161615;--fg:#ecebe6;--mut:#a3a19a;--line:#33322f;--acc:#7cb6de;--card:#1e1e1c}
body{background:var(--bg);color:var(--fg);font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif;line-height:1.6;margin:0 auto;padding:24px 16px;max-width:980px}
h1{font-size:1.5rem;margin:.2em 0}h2{font-size:1.2rem;border-bottom:2px solid var(--acc);padding-bottom:.2em;margin-top:2em}
.lead{font-size:1.08rem}.m{color:var(--mut);font-size:.88rem}
table{border-collapse:collapse;width:100%;margin:.4em 0;font-size:.9rem;display:block;overflow-x:auto;background:var(--card)}
th,td{border:1px solid var(--line);padding:5px 8px;text-align:right;white-space:nowrap}th{text-align:left}thead th{background:var(--line)}"""
    doc = (f"<!doctype html><html lang=zh-Hant><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>急跌錯殺</title>"
           f"<style>{css}</style></head><body><h1>急跌錯殺：十天內比同業多跌、營收獲利沒變差，隔天買</h1>"
           f"<p class=m>PREREG急跌錯殺 seq1（sha {S['meta']['sha']}；裁定 seq335 §四、N_組合 ＋1、四格挑 1；標籤上限最多暫定）｜回測線</p>"
           + lead + "<h2>和 0050、對照、假訊號、營量營飆比</h2>" + main_t + "<h2>退化檢查（先寫才算報酬）</h2>" + deg + "<h2>早年段</h2>" + early
           + "<h2>必報</h2>" + must + "<h2>事件分組（描述）</h2>" + evd + "<h2>各年報酬</h2>" + yret + "<h2>每年事件數</h2>" + years
           + "<h2>描述（不判）</h2>" + desc + "<h2>先驗對照</h2>" + prior + "<h2>怎麼算的</h2>" + notes
           + f"<p class=m>產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。⛔ 不是買賣建議。</p></body></html>")
    open(PAGE, "w", encoding="utf-8").write(doc)
    print("寫出", PAGE)


if __name__ == "__main__":
    page()
