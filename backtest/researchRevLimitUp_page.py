# -*- coding: utf-8 -*-
"""PREREG好營收再加漲停 seq2 —— 網頁（讀 resultsRevLimitUp/summary.json、check.json）⇒ backtest/好營收再加漲停.html。回測線計算子代理。"""
from __future__ import annotations

import html
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.expanduser("~/tw-p17/backtest")
OUT = os.path.join(HERE, "resultsRevLimitUp")
PAGE = os.path.join(HERE, "好營收再加漲停.html")
SEGN = ("探索", "確認", "主窗")


def p(x, d=1):
    return "—" if x is None or not isinstance(x, (int, float)) or not np.isfinite(x) else f"{x * 100:+.{d}f}%"


def pp(x, d=1):
    return "—" if x is None or not isinstance(x, (int, float)) or not np.isfinite(x) else f"{x * 100:.{d}f}%"


def f1(x, d=1):
    return "—" if x is None or not isinstance(x, (int, float)) or not np.isfinite(x) else f"{x:.{d}f}"


def page():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    ck = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else {}
    e = html.escape
    V = S["判定"]; ch = V["挑中格"]; other = [c for c in ("E1", "E2") if c != ch][0]
    G = {(r["格"], r["版本"]): r for r in S["格"]}
    Z = S["meta"]["0050"]
    CN = {"E1": "E1（營收不再創新高就賣）", "E2": "E2（從最高回落 20% 就賣）"}
    cb, cr = G[(ch, "b")], G[(ch, "r")]
    DJ = S["退化"]["持股與現金"]
    excl = S["退化"].get("排除的格", [])
    # ── 結論 ──
    lead = (f"<p class=lead><b>結論：挑中 {e(CN[ch])}；現實版（主要參考）判定「{e(V['現實版判定（主要參考）'])}」，0.585% 版判定「{e(V['判定'])}」。</b></p><ul>"
            f"<li>現實版：探索段 {p(cr['探索_年化'])}／回落 {p(cr['探索_回落'])}（{cr['探索_標籤']}），確認段 {p(cr['確認_年化'])}／{p(cr['確認_回落'])}（{cr['確認_標籤']}）；"
            f"同段 0050：探索 {p(Z['探索']['cagr'])}／{p(Z['探索']['mdd'])}、確認 {p(Z['確認']['cagr'])}／{p(Z['確認']['mdd'])}。</li>"
            f"<li>0.585% 版：探索 {p(cb['探索_年化'])}／{p(cb['探索_回落'])}（{cb['探索_標籤']}），確認 {p(cb['確認_年化'])}／{p(cb['確認_回落'])}（{cb['確認_標籤']}）；早年段：{e(str(V['早年']))}（現實版 {e(str(V['現實版早年']))}）。</li>"
            + (lambda E_: (f"<li>判定取「確認段、早年段」較嚴：早年 {E_['窗'][0][:4]}～{E_['窗'][1][:4]} 挑中格現實版 {p(E_['格'][f'{ch}|r']['早年_年化'])}／{p(E_['格'][f'{ch}|r']['早年_回落'])}、"
                           f"0.585% 版 {p(E_['格'][f'{ch}|b']['早年_年化'])}／{p(E_['格'][f'{ch}|b']['早年_回落'])}，0050 同段 {p(E_['0050']['cagr'])}／{p(E_['0050']['mdd'])} ⇒ 早年段沒過，所以整件判不合格。</li>")
                   if E_.get("窗") else "")(S.get("早年") or {})
            + "<li>⚠ <b>多重檢定邊緣</b>（事件層 t ≈ 3.2 ＜ 3.33）。</li>"
            "<li>⚠ <b>抽籤型、多數個股會跌</b>（事件層個股中位 −1.05%）⇒ 要分散買才吃得到平均。</li>"
            "<li>⚠ 事件層結果（情報 #26）事前看過 ⇒ 這是事後重切，就算兩段都合格也最多「暫定」、只進前瞻紀錄。⛔ 不是買賣建議。</li></ul>")
    # ── 主表 ──
    YC = S["營量營飆"]
    FK = S["假訊號"]

    def cell(r, s):
        return f"{p(r[f'{s}_年化'])}／{p(r[f'{s}_回落'])}<br><span class=m>{r[f'{s}_標籤']}</span>"
    rows = []
    for nm, r in ((f"{CN[ch]} 現實版 ★", cr), (f"{CN[ch]} 0.585% 版", cb), (f"{CN[other]} 現實版", G[(other, 'r')]), (f"{CN[other]} 0.585% 版", G[(other, 'b')])):
        rows.append(f"<tr><th>{e(nm)}</th>" + "".join(f"<td>{cell(r, s)}</td>" for s in SEGN) + "</tr>")
    rows.append("<tr><th>假訊號臂（隨機股、同進場日同筆數、同持有天數分佈）</th>" + "".join(
        f"<td>{p(FK[s]['年化中位'])}／{p(FK[s]['回落中位'])}<br><span class=m>p ＝ {FK[s]['p（假訊號年化 ≥ 挑中格）']:.2f}</span></td>" for s in SEGN) + "</tr>")
    for nm in ("營飆 v1", "營飆 v1 現實版", "營量 v1", "營量 v1 現實版"):
        y = YC[nm]
        rows.append(f"<tr><th>{e(nm)}</th>" + "".join(f"<td>{p(y[s]['年化'])}／{p(y[s]['回落'])}<br><span class=m>{y[s]['標籤']}</span></td>" for s in SEGN) + "</tr>")
    rows.append("<tr><th>0050</th>" + "".join(f"<td>{p(Z[s]['cagr'])}／{p(Z[s]['mdd'])}</td>" for s in SEGN) + "</tr>")
    main_t = ("<table><thead><tr><th></th><th>探索 2017-03～2021-12</th><th>確認 2022-01～2026-08</th><th>主窗</th></tr></thead><tbody>" + "".join(rows)
              + "</tbody></table><p class=m>格內：年化中位／回落中位（200 顆抽籤種子）；標籤對 0050 同段：合格 ＝ 年化較高且年化÷回落不低於 0050；另列 ＝ 只贏年化。"
              "p ＝ 假訊號 200 抽裡年化不輸挑中格（0.585% 版）的比例。營量／營飆數字引 resultsYLmargin（同窗、同引擎）。</p>")
    # ── 退化 ──
    drows = "".join(f"<tr><th>{e(k)}</th><td>{f1(v['探索_平均持股'])} 檔／現金 {pp(v['探索_平均現金'])}</td><td>{f1(v['確認_平均持股'])} 檔／現金 {pp(v['確認_平均現金'])}</td>"
                    f"<td>{'是' if v['探索_退化'] else '否'}</td></tr>" for k, v in DJ.items())
    deg = ("<table><thead><tr><th>格｜版本</th><th>探索</th><th>確認</th><th>探索段退化</th></tr></thead><tbody>" + drows + "</tbody></table>"
           f"<p class=m>退化 ＝ 平均持股 ＜ 3 檔或平均現金 ＞ 30%（裁定 seq325）；先寫 degeneracy.json（{e(S['退化']['寫入時間'])}）再彙總報酬。"
           f"照登錄排除的格：{e('、'.join(excl) if excl else '無')}{'；⚠ 兩格都退化 ⇒ 照共用規則在全部格裡挑' if V['全退化'] else ''}。</p>")
    # ── 早年 ──
    E = S.get("早年") or {}
    if E.get("窗"):
        er = "".join(f"<tr><th>{e(k)}</th><td>{p(v['早年_年化'])}／{p(v['早年_回落'])}</td><td>{v['早年_標籤']}</td><td>{f1(v['早年_平均持股'])}／{pp(v['早年_平均現金'])}</td></tr>"
                     for k, v in E["格"].items())
        early = (f"<p>早年窗 {E['窗'][0]}～{E['窗'][1]}（月營收覆蓋以上市判），0050 同段 {p(E['0050']['cagr'])}／{p(E['0050']['mdd'])}；訊號 {E['訊號']} 筆。</p>"
                 "<table><thead><tr><th>格｜版本</th><th>年化／回落</th><th>標籤</th><th>平均持股／現金</th></tr></thead><tbody>" + er + "</tbody></table>"
                 f"<p class=m>IFRS：期別 2013 的訊號占 {pp(E.get('IFRS：期別 2013 的訊號占比'))}；回看跨 2013-01 的占 {pp(E.get('IFRS：回看跨 2013-01（期別 2013-01～2014-11）占比'))}（照報、不剔）。"
                 "早年上櫃日 K 2007-07 起；漲停門檻 2015-06 前 6.5%。</p>")
    else:
        early = f"<p>早年段：不可判定（{e(str(E.get('原因', '')))}）。</p>"
    # ── 漲停判定、滑價 ──
    LU = S["漲停判定"]; L1 = LU["窗內母體股-日（主段、5,000 萬母體、好營收股）"]; L2 = LU["訊號層（主窗內）"]
    lu = (f"<ul><li>訊號（主窗內）：<b>官方判定 {L2['官方判定']} 筆、備援判定 {L2['備援判定']} 筆</b>；官方可判的訊號裡備援也判漲停 {L2['官方可判訊號中備援也判漲停']} 筆、"
          f"不一致（官方是、備援否）{L2['不一致（官方是、備援否）']} 筆。</li>"
          f"<li>窗內母體股-日（好營收股、主段全期）：官方可判 {L1['官方可判股-日']:,}，其中官方判漲停 {L1['官方判漲停']}、備援判漲停 {L1['備援判漲停（官方可判日）']}；"
          f"不一致 {L1['官方與備援不一致']}（官方是備援否 {L1['官方是、備援否']}、官方否備援是 {L1['官方否、備援是']}）。</li>"
          f"<li>{e(LU['說明'])}。除權息表 {LU['除權息表']['列（limit_up 有值）']:,} 列（哨兵「無漲跌幅限制」{LU['除權息表']['哨兵（無漲跌幅限制）']} 列，走備援）。</li></ul>")
    SLP = S["滑價與買不到"]; s1 = SLP["訊號層（主窗內訊號）"]
    slip = (f"<ul><li>漲停隔天開盤一價到底（鎖漲停、買不到）：訊號層 <b>{s1['e 開盤鎖漲停（一價到底）筆']} 筆</b>／{s1['訊號筆']} 筆；現實版引擎每顆實際擋掉（種子中位）"
            + "、".join(f"{c} {v['漲停買不到']:.0f} 筆" for c, v in SLP["引擎（現實版，種子中位）"].items()) + "（名額當天持現金、不遞補）。</li>"
            f"<li>隔天開盤跳空（開 ÷ 前收 − 1）：平均 {p(s1['隔天開盤跳空 o[e]÷c[d]−1']['平均'], 2)}、中位 {p(s1['隔天開盤跳空 o[e]÷c[d]−1']['中位'], 2)}（已算在報酬裡）。</li>"
            f"<li>滑價：均價對開盤 平均 {p(s1['均價對開盤 avg[e]÷o[e]−1']['平均'], 2)}；C2 進場衝擊（單邊）平均 {pp(s1['C2 進場衝擊（單邊）']['平均'], 3)}；另每邊 ＋0.3%。</li>"
            "<li>現實版比 0.585% 版少的年化點數：" + "；".join(f"{c} " + "、".join(f"{s} {v[s]:+.1f}" for s in SEGN) for c, v in SLP["現實版比 0.585% 版（年化點）"].items()) + "。</li></ul>")
    # ── 必報 ──
    TS = S["逐筆"]; NE = S["等效獨立"]; OV = S["重疊"]

    def ts_html(t, nm):
        h = t["持有天數（交易日，已出場，種子合計）"]
        why = "、".join(f"{k} {v:.1f}" for k, v in t["出場原因（每顆平均）"].items())
        return (f"<li>{e(nm)}：每顆窗內買進 {t['每顆平均買進筆（窗內）']:.0f} 筆；持有天數中位 {f1(h.get('中位'), 0)}（p10～p90 {f1(h.get('p10'), 0)}～{f1(h.get('p90'), 0)}）；"
                f"出場原因（每顆平均筆）：{e(why)}；窗尾（2026-08-24）仍持有 {f1(t['窗尾仍持有（檔，種子中位）'], 0)} 檔；一年內先跌 15% 的比例 {pp(t['一年內先跌15%比例'])}"
                f"（觀察滿 250 日 {t['觀察窗滿250筆']} 筆，種子合計）。</li>")
    ne_rows = "".join(f"<tr><th>{s}</th><td>{f1(v['平均持股'])}</td><td>{f1(v['平均ρ'], 2)}</td><td>{f1(v['平均N_eff'])}</td><td>{f1(v['最大產業檔數中位'], 0)}（最多 {v['最大產業檔數最大']}）</td>"
                      f"<td>{pp(v['最大產業＞3檔的換股日占比'])}</td><td>{pp(OV[s]['與營飆 v1持股重疊率'])}</td><td>{pp(OV[s]['與營量 v1持股重疊率'])}</td></tr>" for s, v in NE.items())
    must = ("<ul>" + ts_html(TS["b"], f"{CN[ch]} 0.585% 版") + ts_html(TS["r"], f"{CN[ch]} 現實版") + ts_html(S["逐筆（另一格）"][other], f"{CN[other]} 0.585% 版") + "</ul>"
            "<table><thead><tr><th>段</th><th>換股日平均持股</th><th>平均相關 ρ</th><th>等效獨立檔數</th><th>最大產業占幾檔（中位）</th><th>最大產業＞3 檔的日子</th>"
            "<th>與營飆 v1 持股重疊</th><th>與營量 v1 持股重疊</th></tr></thead><tbody>" + ne_rows + "</tbody></table>"
            "<p class=m>等效獨立檔數 ＝ N ÷ (1＋(N−1)ρ)，ρ ＝ 換股日持股前 60 日報酬兩兩平均相關（r＝0）；產業 ＝ 上市櫃官方產業別單層；重疊 ＝ 逐日本件持股中也在對方持股的比例（r＝0）。</p>")
    yr = S["各年"]
    yrows = "".join(f"<tr><td>{y}</td><td>{p(yr['策略現實版'].get(y))}</td><td>{p(yr['策略'][y])}</td><td>{p(yr['0050'].get(y))}</td></tr>" for y in yr["策略"])
    years = ("<table><thead><tr><th>年</th><th>挑中格現實版</th><th>挑中格 0.585% 版</th><th>0050</th></tr></thead><tbody>" + yrows + "</tbody></table>"
             "<p class=m>同一條權益曲線各曆年（2017 從 03-02、2026 到 08-24），種子中位。</p>")
    # ── 描述 ──
    DS = S["描述"]
    drows = "".join(f"<tr><th>{e(k)}</th>" + "".join(f"<td>{p(v[f'{s}_年化'])}／{p(v[f'{s}_回落'])}</td>" for s in SEGN) + f"<td>{f1(v['探索_平均持股'])}／{pp(v['探索_平均現金'])}</td></tr>"
                    for k, v in DS.items())
    desc = ("<table><thead><tr><th>描述臂（⛔ 不判）</th><th>探索</th><th>確認</th><th>主窗</th><th>探索持股／現金</th></tr></thead><tbody>" + drows + "</tbody></table>"
            f"<p class=m>固定持有只描述（全線規則：主臂是條件出場、⛔ 不設最長天數）。R1 排名版：X ＝ {S['R1']['X']:.4f}（2016-01-04 {S['R1']['2016-01-04 5,000萬母體（非金融生技）']}／{S['R1']['同日全市場']}），"
            f"主窗訊號 {DS.get('R1排名版', {}).get('訊號（主窗）', '—')} 筆。0050 在 200 日線上才買：0050 濾網的角色是「擋長空頭、不是急跌保護」。</p>")
    # ── 先驗 ──
    p3 = "成立" if G[("E1", "b")]["確認_年化"] > G[("E2", "b")]["確認_年化"] else "不成立"
    ov = OV["主窗"]["與營飆 v1持股重疊率"]
    prior = (f"<ul><li>先驗 ①「兩段都合格的格 0 個」：{'成立' if V['判定'] != '暫定（事後重切；只進前瞻紀錄）' else '不成立'}（0.585% 版）。</li>"
             f"<li>先驗 ②「與營飆 v1 持股重疊率 ＞ 40%」：主窗 {pp(ov)} ⇒ {'成立' if ov > 0.4 else '不成立'}。</li>"
             f"<li>先驗 ③「E1 年化 ＞ E2」：確認段 E1 {p(G[('E1', 'b')]['確認_年化'])} vs E2 {p(G[('E2', 'b')]['確認_年化'])} ⇒ {p3}（探索段 E1 {p(G[('E1', 'b')]['探索_年化'])} vs E2 {p(G[('E2', 'b')]['探索_年化'])}）。</li></ul>")
    gate = S.get("營量營飆r0閘", {})
    notes = ("<ul>"
             "<li>規則：月營收創 24 個月新高（本月 ＞ 前 23 個月最高）的四碼股，營收可用日起 20 個交易日內某天收漲停，隔天開盤買；最多 10 檔等權，候選多於空位抽籤；"
             "母體 20 日均成交金額 ≥ 5,000 萬、排除金融與生技。</li>"
             "<li>出場兩格：E1 之後每月營收可用日、最新一期不再創新高就當天開盤賣；E2 收盤從持有期最高回落 20% 隔天開盤賣；⛔ 不設最長天數。</li>"
             "<li>可用日：2025-12 期以前次月 10 日後第一個交易日，2026-01 期起 15 日後。漲停：上市除權息日用交易所漲停價，其餘用還原收盤日報酬 ≥ 9.5%（2015-06 前 6.5%）。</li>"
             "<li>現實版（主要參考）：每邊另加 0.3%、平方根衝擊（50 萬資金）、一字漲停買不到、一字跌停賣不掉、進出用當日均價。</li>"
             f"<li>引擎：research11.simulate_mtm；停止交易強制出場開；GATE_V2 開、含下市；營量／營飆 r＝0 重跑閘（＝ resultsT1fix）：{e(json.dumps(gate, ensure_ascii=False))}。</li>"
             + (f"<li>獨立查核（--check）：{e(ck.get('結論', ''))}。</li>" if ck else "")
             + f"<li>讀法寫死 {e(S['meta']['讀法寫死'])}；執行 {e(S['meta']['run'])}；資料 tw-stock-data {e(S['meta']['tw-stock-data'][:10])}、價量快照 edc6f8002f；"
             "程式 backtest/researchRevLimitUp.py；結果 backtest/resultsRevLimitUp/。</li></ul>")
    css = """:root{--bg:#fbfaf7;--fg:#1d1d1b;--mut:#6b6a66;--line:#e2dfd8;--acc:#1f5f8b;--card:#ffffff}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#161615;--fg:#ecebe6;--mut:#a3a19a;--line:#33322f;--acc:#7cb6de;--card:#1e1e1c}}
:root[data-theme="dark"]{--bg:#161615;--fg:#ecebe6;--mut:#a3a19a;--line:#33322f;--acc:#7cb6de;--card:#1e1e1c}
body{background:var(--bg);color:var(--fg);font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif;line-height:1.6;margin:0 auto;padding:24px 16px;max-width:980px}
h1{font-size:1.5rem;margin:.2em 0}h2{font-size:1.2rem;border-bottom:2px solid var(--acc);padding-bottom:.2em;margin-top:2em}
.lead{font-size:1.08rem}.m{color:var(--mut);font-size:.88rem}
table{border-collapse:collapse;width:100%;margin:.4em 0;font-size:.9rem;display:block;overflow-x:auto;background:var(--card)}
th,td{border:1px solid var(--line);padding:5px 8px;text-align:right;white-space:nowrap}th{text-align:left}thead th{background:var(--line)}"""
    doc = (f"<!doctype html><html lang=zh-Hant><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>好營收再加漲停</title>"
           f"<style>{css}</style></head><body><h1>好營收再加漲停</h1>"
           f"<p class=m>PREREG好營收再加漲停 seq2（sha {S['meta']['sha']}；裁定 seq326 §二、N_組合 ＋1、E1／E2 兩格挑 1；事後重切 ⇒ 最多暫定）｜回測線</p>"
           + lead + "<h2>和 0050、假訊號、營量營飆比</h2>" + main_t + "<h2>退化檢查</h2>" + deg + "<h2>早年段</h2>" + early
           + "<h2>漲停怎麼判的</h2>" + lu + "<h2>漲停隔天買不買得到、滑價</h2>" + slip + "<h2>必報</h2>" + must + "<h2>各年報酬</h2>" + years
           + "<h2>描述（不判）</h2>" + desc + "<h2>先驗對照</h2>" + prior + "<h2>怎麼算的</h2>" + notes
           + f"<p class=m>產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。⛔ 不是買賣建議。</p></body></html>")
    open(PAGE, "w", encoding="utf-8").write(doc)
    print("寫出", PAGE)


if __name__ == "__main__":
    page()
