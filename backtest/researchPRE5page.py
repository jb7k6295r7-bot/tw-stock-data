# -*- coding: utf-8 -*-
"""seq323／seq324 四件＋口徑件的網頁（繁體中文、白話、結論先講）。只讀各件 summary.json、degeneracy.json；⛔ 不算任何數字。"""
from __future__ import annotations

import html
import json
import os

import numpy as np

E = html.escape
CSS = """:root{--bg:#fff;--fg:#1d1d1f;--mut:#6b6b70;--line:#e3e3e8;--acc:#0b5cad;--warn:#a1520b;--card:#f6f7f9}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#141416;--fg:#ececf0;--mut:#a0a0a8;--line:#33333a;--acc:#6aa8ff;--warn:#f0a35a;--card:#1d1e22}}
:root[data-theme="dark"]{--bg:#141416;--fg:#ececf0;--mut:#a0a0a8;--line:#33333a;--acc:#6aa8ff;--warn:#f0a35a;--card:#1d1e22}
body{background:var(--bg);color:var(--fg);font:15px/1.65 -apple-system,"Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif;margin:0;padding:16px;max-width:980px;margin:auto}
h1{font-size:1.35em;margin:.4em 0}h2{font-size:1.1em;margin-top:1.6em;border-bottom:1px solid var(--line);padding-bottom:.2em}
.box{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 14px;margin:10px 0}
.wrap{overflow-x:auto}table{border-collapse:collapse;font-size:13px;min-width:100%}th,td{border-bottom:1px solid var(--line);padding:4px 6px;text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left}.m{color:var(--mut);font-size:12.5px}.w{color:var(--warn)}b{color:var(--acc)}"""


def p(x, d=1):
    try:
        x = float(x)
    except Exception:
        return "—"
    return "—" if not np.isfinite(x) else f"{x * 100:+.{d}f}%"


def pc(x):
    try:
        x = float(x)
    except Exception:
        return "—"
    return "—" if not np.isfinite(x) else f"{x * 100:.1f}%"


def r2(x):
    try:
        x = float(x)
    except Exception:
        return "—"
    return "—" if not np.isfinite(x) else f"{x:.2f}"


def table(head, rows):
    h = "<div class=wrap><table><tr>" + "".join(f"<th>{E(str(x))}</th>" for x in head) + "</tr>"
    for r in rows:
        h += "<tr>" + "".join(f"<td>{x}</td>" for x in r) + "</tr>"
    return h + "</table></div>"


def doc(title, body):
    return f"<!doctype html><html lang=zh-Hant><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>{E(title)}</title><style>{CSS}</style></head><body>{body}</body></html>"


def page(ST):
    S = json.load(open(os.path.join(ST.OUT, "summary.json"), encoding="utf-8"))
    V = S["判定"]; ch = V["挑中格"]; B = S["挑中格"]["b"]; Rr = S["挑中格"]["r"]; Z = S["meta"]["0050"]
    EA = S.get("早年") or {}
    H = [f"<h1>{E(ST.NAME)}：組合層回測結果</h1>",
         f"<p class=m>回測線計算子代理｜登錄 sha {S['meta']['sha']}｜讀法寫死 {E(S['meta']['讀法寫死'])}｜跑完 {E(S['meta']['run'])}（台北）｜⛔ 不是買賣建議</p>"]
    eline = ""
    if EA and EA.get("窗"):
        ee = EA["格"][f"{ch}|b"]
        eline = f"早年段 {EA['窗'][0]}～{EA['窗'][1]}：{p(ee['早年_年化'])}／回落 {p(ee['早年_回落'])}（0050 {p(EA['0050']['cagr'])}／{p(EA['0050']['mdd'])}）⇒ {E(ee['早年_標籤'])}。"
    else:
        eline = f"早年段：{E((EA or {}).get('原因') or getattr(ST, 'early_note', '') or '不可判定')}。"
    concl = (f"<b>判定：{E(V['判定'])}</b>（現實版：{E(V['現實版判定'])}）。挑中格 {E(ch)}："
             f"確認段 2022-01～2026-08 年化 {p(B['確認_年化'])}、回落 {p(B['確認_回落'])}；0050 同窗 {p(Z['確認']['cagr'])}／{p(Z['確認']['mdd'])} ⇒ {E(B['確認_標籤'])}。{eline}")
    H.append(f"<div class=box><p>{concl}</p><p>{E(ST.result_sentence())}</p></div>")
    H.append(f"<p class=m>{E(S['meta'].get('件說明', ''))}</p>")
    # 退化
    DJ = S["退化"]
    H.append("<h2>一、退化檢查（在算報酬之前寫入 degeneracy.json：" + E(DJ["寫入時間"]) + "）</h2>")
    rows = []
    for nm, v in DJ["持股與現金"].items():
        rows.append([E(nm)] + [f"{r2(v[f'{sg}_平均持股'])} 檔／{pc(v[f'{sg}_平均現金'])}" for sg in ("探索", "確認", "主窗")] + ["<span class=w>退化</span>" if v["探索_退化"] else "否"])
    H.append(table(["格｜版本（b＝0.585%，r＝現實版）", "探索 持股／現金", "確認", "主窗", "探索段退化"], rows))
    rows = [[E(c), v["換股日數"], r2(v["每換股日候選數"].get("中位")), v["候選 0 的換股日"], E("、".join(f"{k}:{x}" for k, x in v["訊號數逐年"].items()))] for c, v in DJ["候選與訊號"].items()]
    H.append(table(["格", "換股日", "每換股日候選中位", "候選 0 的換股日", "訊號數逐年"], rows))
    H.append("<p class=m>退化 ＝ 平均持股 ＜ 3 檔或平均現金 ＞ 30%（種子中位）；照登錄與裁定 seq325 排除，不參加挑格。</p>")
    # 判定表
    H.append("<h2>二、全部格（年化／回落／比值／標籤；探索段挑格，確認段判）</h2>")
    rows = []
    for g in S["格"]:
        rows.append([E(f"{g['格']}｜{g['版本']}")] + [f"{p(g[f'{sg}_年化'])}／{p(g[f'{sg}_回落'])}｜{r2(g[f'{sg}_比值'])}｜{E(g[f'{sg}_標籤'])}" for sg in ("探索", "確認", "主窗")])
    rows.append(["0050"] + [f"{p(Z[sg]['cagr'])}／{p(Z[sg]['mdd'])}｜{r2(Z[sg]['cagr'] / abs(Z[sg]['mdd']))}" for sg in ("探索", "確認", "主窗")])
    for nm, v in S["營量營飆"].items():
        rows.append([E(nm + "（同窗）")] + [f"{p(v[f'{sg}_年化'])}／{p(v[f'{sg}_回落'])}｜{r2(v[f'{sg}_比值'])}｜{E(v[f'{sg}_標籤'])}" for sg in ("探索", "確認", "主窗")])
    H.append(table(["格", "探索 2017-03～2021", "確認 2022～2026-08", "主窗"], rows))
    H.append(f"<p class=m>挑法：探索段非退化格中先合格、再比值最大。挑中 {E(ch)}{'（⚠ 全部格退化）' if V['全退化'] else ''}。營量／營飆對照閘：{E(json.dumps(S['營量營飆閘'], ensure_ascii=False))}</p>")
    if EA and EA.get("窗"):
        H.append("<h3>早年段</h3>")
        rows = [[E(k), f"{p(v['早年_年化'])}／{p(v['早年_回落'])}｜{r2(v['早年_比值'])}｜{E(v['早年_標籤'])}", f"{r2(v['早年_平均持股'])}／{pc(v['早年_平均現金'])}"] for k, v in EA["格"].items()]
        rows.append(["0050", f"{p(EA['0050']['cagr'])}／{p(EA['0050']['mdd'])}", ""])
        H.append(table(["格", "早年 年化／回落｜比值｜標籤", "持股／現金"], rows))
        if EA.get("覆蓋"):
            H.append(f"<p class=m>早年月營收覆蓋率（上市，年平均）：{E(json.dumps(EA['覆蓋'], ensure_ascii=False))}；IFRS 窗（2013 期別）訊號占比 {p(EA.get('2013 期別訊號占比（IFRS 窗）'))}（照舊標、不剔）</p>")
    # 對照
    H.append("<h2>三、假訊號臂與描述臂（⛔ 不判、不計 N）</h2>")
    F = S["假訊號"]
    rows = [[sg, f"{p(F[sg]['年化中位'])}（p10～p90 {p(F[sg]['年化p10'])}～{p(F[sg]['年化p90'])}）", p(F[sg]["回落中位"]), f"{F[sg]['p（假訊號年化 ≥ 挑中格）']:.2f}", p(B[f'{sg}_年化'])] for sg in ("探索", "確認", "主窗")]
    H.append(table(["段", "假訊號年化（200 抽）", "回落中位", "p（假訊號 ≥ 挑中格）", "挑中格年化"], rows))
    rows = [[E(k)] + [f"{p(v[f'{sg}_年化'])}／{p(v[f'{sg}_回落'])}" for sg in ("探索", "確認", "主窗")] for k, v in S["描述"].items()]
    H.append(table(["描述臂（挑中格同進場）", "探索", "確認", "主窗"], rows))
    H.append(f"<p class=m>R1 排名版：X ＝ {S['R1']['X']:.3f}（2016-01-04 5,000 萬母體 {S['R1']['2016-01-04 5,000萬母體']} ÷ 同日全市場 {S['R1']['同日全市場']}）。固定持有、0050 濾網、R1 各 50 顆種子中位。0050 濾網的角色：擋長空頭、不是急跌保護。</p>")
    # 必報
    H.append("<h2>四、必報</h2>")
    NE = S["等效獨立"]
    rows = [[sg, r2(v["平均持股"]), r2(v["平均ρ"]), r2(v["平均N_eff"]), r2(v["最大產業檔數中位"]), v["最大產業檔數最大"], p(v["最大產業＞3檔的換股日占比"], 0)] for sg, v in NE.items()]
    H.append(table(["段", "換股日平均持股", "平均 ρ", "等效獨立檔數 N÷(1＋(N−1)ρ)", "最大產業檔數中位", "最大", "＞3 檔的換股日"], rows))
    H.append("<p class=m>產業分類層：上市櫃官方產業別（單層，industry_pit pit 版）；ρ ＝ 換股日持股前 60 日報酬兩兩相關平均（r＝0）。</p>")
    for v_, nm in (("b", "0.585% 版"), ("r", "現實版")):
        T = S["逐筆"][v_]; hd = T["持有天數（交易日，已出場）"]
        H.append(f"<p><b>{nm}</b>：每顆窗內買進 {T['每顆平均買進筆（窗內）']:.1f} 筆；持有天數中位 {r2(hd.get('中位'))}（p10～p90 {r2(hd.get('p10'))}～{r2(hd.get('p90'))}、平均 {r2(hd.get('平均'))}）；"
                 f"窗尾 2026-08-24 仍持有 {r2(T['窗尾仍持有（檔，種子中位）'])} 檔；一年內先跌 15% 的比例 {p(T['一年內先跌15%比例'], 0)}（{T['觀察窗滿250筆']} 筆）；"
                 f"出場原因（每顆平均）{E('、'.join(f'{k} {x:.1f}' for k, x in T['出場原因（每顆平均）'].items()))}。</p>")
    YR = S["各年"]
    H.append(table(["年"] + list(YR["策略"].keys()), [["挑中格（種子中位）"] + [p(x) for x in YR["策略"].values()], ["0050"] + [p(YR["0050"].get(k)) for k in YR["策略"]]]))
    OV = S["重疊"]
    H.append(f"<p class=m>與營量 v1／營飆 v1 持股重疊率（逐日、r＝0）：" + "；".join(f"{sg} {p(v['與營量 v1 持股重疊率'], 0)}／{p(v['與營飆 v1 持股重疊率'], 0)}" for sg, v in OV.items()) + "</p>")
    if S.get("件專屬"):
        H.append(f"<p class=m>件專屬：{E(json.dumps(S['件專屬'], ensure_ascii=False, default=str)[:1500])}</p>")
    H.append("<h2>五、讀法與限制</h2><ul>" + "".join(f"<li>{E(x)}</li>" for x in ST.notes()) + "</ul>")
    H.append(f"<p class=m>檔案：backtest/{os.path.basename(ST.OUT)}/（summary.json、degeneracy.json、grid.csv、seeds.csv.gz、run.log、check.json）；程式 backtest/research{ST.KEY}.py、researchPRE5core.py。</p>")
    open(ST.PAGE, "w", encoding="utf-8").write(doc(ST.NAME, "".join(H)))
    print("寫出", ST.PAGE)


def page_yl3m():
    from backtest import researchYL3m as Y
    S = json.load(open(os.path.join(Y.OUT, "summary.json"), encoding="utf-8"))
    H = ["<h1>營量 v1、營飆 v1：月營收「單月創新高」改成「三個月合計創新高」</h1>",
         f"<p class=m>口徑敏感度（⛔ 不計 N）｜登錄 sha {S['sha']}｜讀法寫死 {E(S['讀法寫死'])}｜跑完 {E(S['run'])}（台北）｜⛔ 不是買賣建議</p>",
         f"<div class=box><b>{E(S['結論'])}</b></div>"]
    rows = []
    for arm, T in S["表"].items():
        for nm, v in T.items():
            rows.append([E(f"{nm}｜{arm}")] + [f"{p(v[f'{sg}_年化'])}／{p(v[f'{sg}_回落'])}｜{r2(v[f'{sg}_比值'])}｜{E(v[f'{sg}_標籤'])}" for sg in ("探索", "確認", "主窗")]
                        + [E(S["標籤（兩段取較嚴）"][f"{nm}｜{arm}"])])
    Z = S["0050"]
    rows.append(["0050"] + [f"{p(Z[sg]['cagr'])}／{p(Z[sg]['mdd'])}" for sg in ("探索", "確認", "主窗")] + [""])
    H.append(table(["策略｜臂", "探索", "確認", "主窗", "標籤（探索、確認取較嚴）"], rows))
    H.append("<h2>訊號換了多少</h2>")
    H.append(table(["策略", "現行臂列", "3M 臂列", "兩臂都有", "換掉", "換進", "重疊率"],
                   [[E(k), v["現行臂列"], v["3M 臂列"], v["兩臂都有"], v["只在現行臂（換掉）"], v["只在 3M 臂（換進）"], p(v["重疊率（交集÷聯集）"], 0)] for k, v in S["重疊"].items()]))
    H.append("<h2>退化檢查（先寫）</h2>")
    H.append(table(["策略｜臂", "探索 持股／現金", "確認", "主窗"], [[E(k)] + [f"{r2(v[f'{sg}_平均持股'])}／{pc(v[f'{sg}_平均現金'])}" for sg in ("探索", "確認", "主窗")] for k, v in S["退化"].items()]))
    H.append(f"<h2>閘</h2><p class=m>{E(json.dumps(S['閘'], ensure_ascii=False, default=str))}</p>")
    H.append("<ul><li>只換月營收條件：現行臂＝當月 ≥ 前 24 期最大；3M 臂＝近三期合計 ≥ 前 21 期內任何連續三期合計最大（比較號同正式程式「≥」，登錄寫「＞」，兩者不同的列數見閘）。</li>"
             "<li>其他一字不動（強勢股 5 取 3、大盤閘、檔數、排序、持有 120／60 根、成本 0.585%、可用日 10 日）；營飆 200 顆、營量 relvol 排序 r＝0。</li>"
             "<li>⛔ 本線不自行改正式規則。</li></ul>")
    open(Y.PAGE, "w", encoding="utf-8").write(doc("營量營飆三個月合計口徑", "".join(H)))
    print("寫出", Y.PAGE)
