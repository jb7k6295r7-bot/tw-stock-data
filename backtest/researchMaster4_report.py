# -*- coding: utf-8 -*-
"""PREREG大師三套 seq4 網頁（resultsMaster4/REPORT.html）：先講判定、手機可讀。只讀 summary.json、cells.csv、check.json。"""
import json
import os

OUT = os.path.expanduser("~/tw-p17/backtest/resultsMaster4")
CSS = """<style>body{font-family:-apple-system,'Noto Sans TC',sans-serif;margin:0 auto;max-width:760px;padding:0 16px 40px;line-height:1.6;color:#222;background:#fff}
h1{font-size:1.3em}h2{font-size:1.1em;margin-top:1.6em;border-bottom:1px solid #ddd}.box{background:#f4f6fa;border-left:4px solid #3a6;padding:10px 12px;margin:12px 0}
.bad{border-left-color:#c44}.wrap{overflow-x:auto}table{border-collapse:collapse;font-size:.9em;min-width:100%}td,th{border:1px solid #ddd;padding:4px 6px;text-align:right;white-space:nowrap}
td.l,th.l{text-align:left}.note{color:#666;font-size:.85em}@media(prefers-color-scheme:dark){body{background:#111;color:#ddd}.box{background:#1d2230}td,th{border-color:#444}}</style>"""


def p(x, d=1):
    return f"{x * 100:+.{d}f}%"


def main():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    ck = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else {}
    z = S["0050同窗"]; C = S["判定9格"]; st = S["起點"]
    k = sum(c["標籤"] == "合格" for c in C)
    names = {"M": "麥克墨菲", "X": "麥克喜偉", "O": "詹姆士歐沙那希"}
    H = ["<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
         "<title>仿 App 大師三套回測</title>", CSS, "</head><body>"]
    H.append("<h1>仿 App 大師三套（墨菲／喜偉／歐沙那希）：10 檔、抱 20／60／120 天</h1>")
    lines = []
    for s in ("M", "X", "O"):
        cs = [c for c in C if c["套"] == s]
        lab = "、".join(f"{c['H']} 天{c['標籤']}" for c in cs)
        best = max(cs, key=lambda c: c["年化中位"])
        pre = []
        if S["候選數分佈（窗內量測日）"][s]["候選＜10 的量測日比例"] > 0.3:
            pre.append("常常湊不滿 10 檔")
        pfk = max(c["假訊號合格比例 p"] for c in cs)
        if pfk >= 0.05:
            pre.append(f"⚠ 隨機也有 {pfk:.0%} 合格")
        lines.append(f"<li>{'；'.join(pre) + '：' if pre else ''}<b>仿 App {names[s]}條件</b>：{lab}；最好是 {best['H']} 天 {p(best['年化中位'])}／{p(best['回落中位'])}"
                     f"（0050 {p(z['年化'])}／{p(z['回落'])}）</li>")
    cls = "box" if k else "box bad"
    H.append(f"<div class='{cls}'><b>判定</b>：9 格（3 套 × 3 種天數）{k} 格合格。"
             + ("這三套在我們的資料裡沒有贏 0050。" if k == 0 else f"試了 9 格，{k} 格合格，可能是運氣。")
             + f"<ul>{''.join(lines)}</ul>窗 {st['窗'][0]}～{st['窗'][1]}（約 {st['窗年數']:.1f} 年）；財報可用日 A0（上傳時戳）定案。</div>")
    H.append("<p class='note'>這是全部選到的股票平均起來的結果，不是對某一檔的預測。條件照 App 畫面；算法照本線定義，不保證與 App 相同。200 顆抽籤種子取中位。</p>")
    H.append("<h2>9 格</h2><div class='wrap'><table><tr><th class='l'>條件</th><th>天數</th><th>年化中位</th><th>回落中位</th><th>比值</th><th>判定</th><th>假訊號合格比例</th></tr>")
    for c in C:
        H.append(f"<tr><td class='l'>{names[c['套']]}</td><td>{c['H']}</td><td>{p(c['年化中位'])}</td><td>{p(c['回落中位'])}</td><td>{c['比值']:.3f}</td><td>{c['標籤']}</td><td>{c['假訊號合格比例 p']:.1%}</td></tr>")
    H.append(f"<tr><td class='l'>0050 同窗</td><td></td><td>{p(z['年化'])}</td><td>{p(z['回落'])}</td><td>{z['比值']:.3f}</td><td></td><td></td></tr></table></div>")
    H.append("<p class='note'>天數：測過 20／60／120 天；" + "；".join(
        f"{names[s]}最好 {max([c for c in C if c['套'] == s], key=lambda c: c['年化中位'])['H']} 天" for s in ("M", "X", "O")) + "。</p>")
    H.append("<h2>候選與起點</h2><ul>")
    for s in ("M", "X", "O"):
        d = S["候選數分佈（窗內量測日）"][s]
        H.append(f"<li>{names[s]}：每月候選中位 {d['中位']:.0f} 檔（p10～p90 {d['p10']:.0f}～{d['p90']:.0f}）；不到 10 檔的月份 {d['候選＜10 的量測日比例']:.0%}</li>")
    H.append(f"<li>起點 {st['起點']}：三套可算比例 {st['三套可算比例首次都 ≥ 90%']} 就 ≥ 90%，但 2018-04～2019-05 每家的最新一季財報都沒有上傳時戳（只能用法定期限代，有前視、裁定 seq231 禁用）⇒ 改從上傳時戳覆蓋 ≥ 90% 的 {st['最新一季有 A0 時戳比例首次 ≥ 90%（執行者補）']} 起算（執行者補）。</li></ul>")
    H.append("<h2>描述（不判）</h2>")
    alt = S.get("描述_起點敏感度", {})
    if alt:
        H.append("<p>起點改動：</p><div class='wrap'><table><tr><th class='l'>起點</th><th class='l'>格</th><th>年化中位</th><th>回落中位</th><th>判定</th></tr>")
        for al, d in alt.items():
            for kk, v in d.items():
                if kk == "0050同窗":
                    H.append(f"<tr><td class='l'>{al}</td><td class='l'>0050</td><td>{p(v['年化'])}</td><td>{p(v['回落'])}</td><td></td></tr>")
                else:
                    H.append(f"<tr><td class='l'>{al}</td><td class='l'>{names[kk[0]]} {kk.split('_H')[1]} 天</td><td>{p(v['年化中位'])}</td><td>{p(v['回落中位'])}</td><td>{v['標籤']}</td></tr>")
        H.append("</table></div>")
    H.append("<p>拿掉一條（看哪一條在出力）：</p><div class='wrap'><table><tr><th class='l'>拿掉</th><th>20 天</th><th>60 天</th><th>120 天</th></tr>")
    for kk, v in S["描述_拿掉一條"].items():
        H.append(f"<tr><td class='l'>{names[kk[0]]}：{kk.split('（拿掉 ')[1][:-1]}</td>" + "".join(f"<td>{p(v[f'H{h}']['年化中位'])}</td>" for h in (20, 60, 120)) + "</tr>")
    H.append("</table></div>")
    H.append("<p>其他版本：</p><div class='wrap'><table><tr><th class='l'>版本</th><th class='l'>條件</th><th>20 天</th><th>60 天</th><th>120 天</th></tr>")
    for nm, key in (("現實版（每邊多 0.3%＋50 萬衝擊＋均價）", "描述_現實版"), ("不看上市年數（L2）", "描述_L2不看上市年數")):
        for s in ("M", "X", "O"):
            v = S[key][s]
            H.append(f"<tr><td class='l'>{nm}</td><td class='l'>{names[s]}</td>" + "".join(f"<td>{p(v[f'H{h}']['年化中位'])}／{p(v[f'H{h}']['回落中位'])}</td>" for h in (20, 60, 120)) + "</tr>")
    H.append("</table></div>")
    mx = S["描述_混營飆v1 50／50"]
    H.append(f"<p>與營飆 v1 各半（每年初調回）：營飆 v1 同窗 {p(mx['營飆v1同窗']['年化中位'])}／{p(mx['營飆v1同窗']['回落中位'])}</p><div class='wrap'><table><tr><th class='l'>格</th><th>混合年化</th><th>混合回落</th><th>日報酬相關</th><th>同時持有檔數</th></tr>")
    for kk, v in mx.items():
        if kk == "營飆v1同窗":
            continue
        ho = S["描述_與營飆v1同時持有（種子0）"].get(kk, {})
        H.append(f"<tr><td class='l'>{names[kk[0]]} {kk.split('_H')[1]} 天</td><td>{p(v['混合年化中位'])}</td><td>{p(v['混合回落中位'])}</td><td>{v['日報酬相關中位']:.2f}</td><td>{ho.get('同時持有檔數平均', float('nan')):.2f}</td></tr>")
    H.append("</table></div>")
    y1 = S["描述_逐年100萬期末（200顆中位）"]
    yrs = sorted(y1["0050"])
    H.append("<p>每年初放 100 萬、年底剩多少（萬；2019 為 6/3 起）：</p><div class='wrap'><table><tr><th class='l'>格</th>" + "".join(f"<th>{y}</th>" for y in yrs) + "</tr>")
    for kk, v in y1.items():
        nm = "0050" if kk == "0050" else f"{names[kk[0]]} {kk.split('_H')[1]} 天"
        H.append(f"<tr><td class='l'>{nm}</td>" + "".join(f"<td>{v[str(y)] / 1e4:.0f}</td>" if str(y) in v else f"<td>{v[y] / 1e4:.0f}</td>" for y in yrs) + "</tr>")
    H.append("</table></div>")
    mc = S["描述_月分群（年化第100顆）"]
    H.append("<p>逐月比 0050 多賺（以月為群、95% 區間）：" + "；".join(f"{names[kk[0]]} {kk.split('_H')[1]} 天 {p(v['月超額平均'], 2)}（{p(v['lo'], 2)}～{p(v['hi'], 2)}）" for kk, v in mc.items()) + "</p>")
    ov = S["描述_三套候選重疊（Jaccard，量測日平均）"]
    H.append("<p>三套候選重疊：" + "、".join(f"{names[a[0]]}×{names[a[2]]} {v:.0%}" for a, v in ov.items()) + "</p>")
    sens = S["出場敏感度（seq242 ②，描述）"]
    H.append(f"<p>出場敏感度：{sens if isinstance(sens, str) else json.dumps(sens, ensure_ascii=False)}</p>")
    H.append("<h2>資料與查核</h2><ul>")
    H.append(f"<li>財報 fin_hist（含已下市）、研發 XBRL、可用日＝上傳時戳最早一筆的下一個交易日（盤中盤後不分）；本益比 上市＋上櫃官方值（取前一交易日）</li>")
    H.append(f"<li>0050 主窗錨逐位元：{S['閘']['0050 主窗錨逐位元']}；查核：{ck.get('結論', '（未跑）')}</li>")
    H.append("<li>出處：backtest/researchMaster4.py、resultsMaster4/summary.json、cells.csv、seeds.csv.gz、fake.csv.gz、gate_by_month.csv、check.json</li></ul>")
    H.append("</body></html>")
    open(os.path.join(OUT, "REPORT.html"), "w", encoding="utf-8").write("\n".join(H))
    print("ok")


if __name__ == "__main__":
    main()
