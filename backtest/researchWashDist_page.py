# -*- coding: utf-8 -*-
"""PREREG洗盤還是出貨 seq1 網頁（resultsWashDist/洗盤還是出貨.html）：先講判定、手機可讀。只讀結果檔。"""
import json
import os

import numpy as np
import pandas as pd

OUT = os.path.expanduser("~/tw-p17/backtest/resultsWashDist")
CSS = """<style>body{font-family:-apple-system,'Noto Sans TC',sans-serif;margin:0 auto;max-width:780px;padding:0 16px 40px;line-height:1.6;color:#222;background:#fff}
h1{font-size:1.3em}h2{font-size:1.1em;margin-top:1.6em;border-bottom:1px solid #ddd}.box{background:#f4f6fa;border-left:4px solid #3a6;padding:10px 12px;margin:12px 0}
.bad{border-left-color:#c44}.wrap{overflow-x:auto}table{border-collapse:collapse;font-size:.85em;min-width:100%}td,th{border:1px solid #ddd;padding:3px 5px;text-align:right;white-space:nowrap}
td.l,th.l{text-align:left}.note{color:#666;font-size:.85em}@media(prefers-color-scheme:dark){body{background:#111;color:#ddd}.box{background:#1d2230}td,th{border-color:#444}}</style>"""
QN = {"Q1": "洗盤組可買（洗盤組 比同漲跌股票好、扣成本）", "Q2": "分得出（洗盤組 − 出貨組 ＞ 0）", "Q3": "出貨組該賣（出貨組 比同漲跌股票差）"}


def p(x, d=2):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—"
    return "—" if not np.isfinite(x) else f"{x * 100:+.{d}f}%"


def main():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    C = pd.read_csv(os.path.join(OUT, "cells.csv"))
    ck = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else {}
    J = S["判定"]
    ok = [k for k, v in J.items() if v["成立（主版）"]]
    H = ["<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
         "<title>洗盤還是出貨</title>", CSS, "</head><body>", "<h1>洗盤還是出貨：圖卡四條（位置＋量能＋走勢＋反彈）合判</h1>"]
    lines = []
    for q in ("Q1", "Q2", "Q3"):
        res = "；".join(f"{H_} 天{'成立' if J[f'{q}_H{H_}']['成立（主版）'] else '不成立'}" for H_ in (5, 20, 60))
        lines.append(f"<li><b>{QN[q]}</b>：{res}</li>")
    H.append(f"<div class='box{'' if ok else ' bad'}'><b>判定</b>（兩段都要過半格才算；9 題 ＝ 3 問 × 3 種天數）：{len(ok)} 題成立。<ul>{''.join(lines)}</ul>"
             "⚠ 量縮、放量滯漲、長上影、跌破支撐、等拉回這幾條先前單獨測過，多半不支持；本件只回答「四條合在一起判有沒有增量」，不改寫單條的舊結論。"
             "圖卡的「看後續」是事後才知道的標籤，沒有放進條件。</div>")
    H.append("<p class='note'>事件：漲過一段（前 60 日漲 ≥ U）、回檔 ≥ D 之後，收盤回升到跌幅的 1/3 那天（T）收盤判四條、T＋1 開盤進。基準② ＝ 同日、前 20 日漲幅同十分位的股票。"
             "16 格 ＝ U{20%, 40%} × D{8%, 15%} × 位置門檻 P{50%, 100%} × 支撐{60 日線, 起漲段 50% 回撤}。月分群 95% 區間。這是全部事件平均起來的結果，不是對某一檔的預測。</p>")
    H.append("<h2>各題各段通過格數（足樣本格中通過／足樣本格；全格版通過／16）</h2><div class='wrap'><table><tr><th class='l'>題</th><th>H</th><th>探索</th><th>確認</th><th>早年</th><th>成立</th></tr>")
    for k, v in J.items():
        q, h = k.split("_H")
        H.append(f"<tr><td class='l'>{q}</td><td>{h}</td>" + "".join(f"<td>{v[s]['足樣本中通過']}／{v[s]['足樣本格']}（{v[s]['通過格（全）']}／16）</td>" for s in ("探索", "確認", "早年"))
                 + f"<td>{'成立' if v['成立（主版）'] else '—'}{'；早年同向' if v['早年同向'] else ''}</td></tr>")
    H.append("</table></div>")
    for seg in ("確認", "探索", "早年"):
        x = C[(C["段"] == seg) & (C["H"] == 20)]
        H.append(f"<h2>{seg}段、H＝20：16 格</h2><div class='wrap'><table><tr><th class='l'>U／D／P／支撐</th><th>洗盤 n</th><th>洗盤 X−成本（95%）</th><th>出貨 n</th><th>出貨 X（95%）</th><th>洗−出（95%）</th></tr>")
        for d in x.to_dict("records"):
            H.append(f"<tr><td class='l'>{d['U']:.0%}／{d['D']:.0%}／{d['P']:.0%}／{d['支撐']}{'（樣本少：' + d['樣本少'] + '）' if isinstance(d['樣本少'], str) and d['樣本少'] else ''}</td>"
                     f"<td>{int(d['洗盤_n'])}</td><td>{p(d['洗盤_X−成本'])}（{p(d['洗盤_lo'])}～{p(d['洗盤_hi'])}）</td><td>{int(d['出貨_n'])}</td><td>{p(d['出貨_X'])}（{p(d['出貨_lo'])}～{p(d['出貨_hi'])}）</td>"
                     f"<td>{p(d.get('Q2_差'))}（{p(d.get('Q2_lo'))}～{p(d.get('Q2_hi'))}）</td></tr>")
        H.append("</table></div>")
    dsc = S["描述"]
    H.append("<h2>描述（不判）</h2><ul>")
    for seg, v in dsc.items():
        H.append(f"<li>{seg}：各組事件數 {json.dumps(v['各組事件數（16 格合計）'], ensure_ascii=False)}；逐條 像洗盤−像出貨（H20）{ {k: round(vv * 100, 2) for k, vv in v['逐條 像洗盤−像出貨 X20 差（16 格合計）'].items()} } 點；"
                 f"事後 20 日創前高比例 洗盤 {v['事後創前高比例'].get('洗盤') or 0:.1%}、出貨 {v['事後創前高比例'].get('出貨') or 0:.1%}、混合 {v['事後創前高比例'].get('混合') or 0:.1%}</li>")
    nr = [v["沒反彈比例"] for v in S["事件帳（全史、逐檔：成事件／30日沒反彈／不足250根）"].values()]
    H.append(f"<li>回檔後 30 日內沒反彈的比例：{min(nr):.0%}～{max(nr):.0%}（依 U、D 與去重版本）</li></ul>")
    pv = S["先驗（登錄 §五）"]
    H.append("<h2>先驗（登錄 §五）</h2><ul>" + "".join(f"<li>{k}：{'中' if vv else '沒中'}</li>" for k, vv in pv.items()) + "</ul>")
    H.append(f"<h2>做法與查核</h2><ul><li>母體 W1 eligible、含已下市、還原價、量用原始股數、母體閘新口徑（GATE_V2）；T＋1 停牌或開盤漲停 ⇒ 買不到、剔除；硬斷點剔除。</li>"
             "<li>執行者補：起漲段漲幅量在前高；前高前需 250 根；反彈確認從回檔觸發日起 30 根內；Q2 的誤差合併兩組各自的月分群誤差；早年段母體用流動性＋K 棒數。</li>"
             f"<li>查核：{ck.get('結論', '（未跑）')}</li><li>出處：backtest/researchWashDist.py、resultsWashDist/（summary.json、cells.csv、events.csv.gz、check.json）</li></ul></body></html>")
    open(os.path.join(OUT, "洗盤還是出貨.html"), "w", encoding="utf-8").write("\n".join(H))
    print("ok")


if __name__ == "__main__":
    main()
