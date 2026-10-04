# -*- coding: utf-8 -*-
"""PREREG外部三件 X1 網頁（resultsExtX1/REPORT.html）：先講判定、手機可讀。只讀 summary.json、check.json。"""
import json
import os

OUT = os.path.expanduser("~/tw-p17/backtest/resultsExtX1")
CSS = """<style>body{font-family:-apple-system,'Noto Sans TC',sans-serif;margin:0 auto;max-width:760px;padding:0 16px 40px;line-height:1.6;color:#222;background:#fff}
h1{font-size:1.3em}h2{font-size:1.1em;margin-top:1.6em;border-bottom:1px solid #ddd}.box{background:#f4f6fa;border-left:4px solid #3a6;padding:10px 12px;margin:12px 0}
.bad{border-left-color:#c44}.wrap{overflow-x:auto}table{border-collapse:collapse;font-size:.9em;min-width:100%}td,th{border:1px solid #ddd;padding:4px 6px;text-align:right;white-space:nowrap}
td.l,th.l{text-align:left}.note{color:#666;font-size:.85em}@media(prefers-color-scheme:dark){body{background:#111;color:#ddd}.box{background:#1d2230}td,th{border-color:#444}}</style>"""


def p(x, d=1):
    return f"{x * 100:+.{d}f}%"


def main():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    ck = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else {}
    J = S["判定（早年段，月換主格）"]; z = S["0050"]; W = S["窗"]; F = S["假訊號（同池隨機 40 檔等權，1,000 次）"]; O = S["描述_原文期間 2018-01～2026-06"]
    lab = J["標籤"]
    sent = {"合格": "這套做法在原文沒用過的早年段贏 0050", "另列": "報酬贏 0050、但回落相對太深", "不合格": "這套做法在原文沒用過的早年段沒有贏 0050"}[lab]
    pre = "隨機挑也做得到：" if F["早年 p（隨機年化 ≥ 本格）"] >= 0.05 else ""
    H = ["<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
         "<title>X1 多因子回測</title>", CSS, "</head><body>",
         "<h1>外部研究 X1：FinLab 四因子選股（營收動能＋價格動能＋ROE＋低波動，40 檔）</h1>"]
    H.append(f"<div class='box{'' if lab == '合格' else ' bad'}'><b>判定：{lab}</b>。{pre}{sent}："
             f"早年段 {W['早年甲（早年版面、只上市）'][0]}～{W['早年乙（主快照）'][1]}（約 {W['早年段年數']:.1f} 年）年化 {p(J['年化'])}、回落 {p(J['回落'])}，"
             f"0050 {p(z['早年段'][0])}／{p(z['早年段'][1])}。<br>原文期間 2018-01～2026-06 照跑（描述）：{p(O['年化'])}／{p(O['回落'])}（原文 +29.45%／−26.07%；0050 {p(O['0050'][0])}／{p(O['0050'][1])}）。</div>")
    H.append("<p class='note'>出處為公開研究、原文數字未必可重現。原文程式（strategy.py）已取得，照它的算式自寫；含已下市股、扣來回 0.585%。"
             "⚠ 早年段沒有財報上傳時戳（資料庫只補 2019 起）⇒ ROE 可用日用「法定期限＋5 個交易日」代。這是全部選到的股票平均起來的結果，不是對某一檔的預測。</p>")
    H.append("<h2>主要數字</h2><div class='wrap'><table><tr><th class='l'>段</th><th>年化</th><th>回落</th><th>比值</th><th>0050</th></tr>")
    H.append(f"<tr><td class='l'>早年段（判定）</td><td>{p(J['年化'])}</td><td>{p(J['回落'])}</td><td>{J['比值']:.3f}</td><td>{p(z['早年段'][0])}／{p(z['早年段'][1])}（{z['早年段'][2]:.3f}）</td></tr>")
    H.append(f"<tr><td class='l'>原文期間（描述）</td><td>{p(O['年化'])}</td><td>{p(O['回落'])}</td><td>{O['年化'] / abs(O['回落']):.3f}</td><td>{p(O['0050'][0])}／{p(O['0050'][1])}</td></tr>")
    t = S["描述_2026-07～08"]
    H.append(f"<tr><td class='l'>2026-07～08（描述）</td><td colspan='3'>區間 {p(t['區間報酬'])}</td><td>{p(t['0050'])}</td></tr></table></div>")
    H.append(f"<p>假訊號（同池隨機 40 檔、等權，1,000 次）：早年段隨機年化中位 {p(F['早年 隨機年化中位'])}，本格以上的比例 {F['早年 p（隨機年化 ≥ 本格）']:.1%}，"
             f"隨機也合格 {F['早年 隨機合格比例']:.1%}；原文期間隨機中位 {p(F['原文期間 隨機年化中位'])}，p {F['原文期間 p']:.1%}。</p>")
    H.append("<h2>描述（不判）</h2><div class='wrap'><table><tr><th class='l'>版本</th><th>早年段</th><th>原文期間</th></tr>")
    for k, v in S["描述"].items():
        if k.startswith("月分群"):
            continue
        if "早年" in v:
            H.append(f"<tr><td class='l'>{k}</td><td>{p(v['早年'][0])}／{p(v['早年'][1])} {v['早年'][2]}</td><td>{p(v['原文期間'][0])}／{p(v['原文期間'][1])}</td></tr>")
        else:
            H.append(f"<tr><td class='l'>{k}</td><td>—</td><td>{p(v['原文期間'][0])}／{p(v['原文期間'][1])}（含已下市多 {v['含已下市 − 只含存活（年化點）']:+.1f} 點）</td></tr>")
    H.append("</table></div>")
    for k in ("月分群（早年段，逐月超額對 0050）", "月分群（原文期間）"):
        v = S["描述"][k]
        H.append(f"<p>{k}：每月平均 {p(v['月超額平均'], 2)}（95% {p(v['lo'], 2)}～{p(v['hi'], 2)}，{v['月數']} 個月）</p>")
    sens = S["出場敏感度（seq242 ②，描述）"]
    if isinstance(sens, dict):
        H.append("<p>出場敏感度（早年段）：" + "；".join(f"{k} {p(v[0])}／{p(v[1])} {v[2]}" if isinstance(v, list) else f"{k}：{v}" for k, v in sens.items()) + "</p>")
    else:
        H.append(f"<p>出場敏感度：{sens}</p>")
    sp = os.path.join(OUT, "sens_lag20.json")
    if os.path.exists(sp):
        L = json.load(open(sp, encoding="utf-8"))
        e, b, o = L["早年段"], L["0050"], L["主跑（＋5）"]
        H.append(f"<h2>可用日敏感度（裁定 seq290）：早年段 ROE 可用日改「法定期限＋20 交易日」</h2>")
        H.append(f"<div class='box bad'><b>對外標籤：{L['對外標籤（seq290）']}</b>。＋20 版早年段 {p(e['年化'])}／{p(e['回落'])}（比值 {e['比值']:.3f}），"
                 f"0050 {p(b['年化'])}／{p(b['回落'])}（{b['比值']:.3f}）⇒ 計算標籤 {e['標籤（計算）']}；＋5 版 {p(o['年化'])}／{p(o['回落'])} {o['標籤（計算）']} ⇒ "
                 f"標籤{'翻轉' if L['標籤翻轉'] else '沒有翻轉'}。</div>")
        H.append(f"<p class='note'>其餘一字不變；窗沿用主跑（新補位下早年甲起點規則會落在 {L['新補位下早年甲起點規則會落在']}，未用來改窗）。讀法時間 {L['讀法時間']}。</p>")
    H.append("<h2>做法與查核</h2><ul>")
    H.append("<li>每月底：池 ＝ 最近 3 期月營收年增都 ＞ 0 且最新一期 10%～150%；四因子在池內排百分位相加；取前 40；權重 ∝ 分數平方；月底後 14 天開盤換股。</li>")
    H.append(f"<li>早年段：早年版面（只上市）{W['早年甲（早年版面、只上市）'][0]}～{W['早年甲（早年版面、只上市）'][1]} ＋ 主快照 {W['早年乙（主快照）'][0]}～{W['早年乙（主快照）'][1]} 串接。</li>")
    H.append(f"<li>池大小中位：{json.dumps(S['池大小（中位）'], ensure_ascii=False)}；ROE 可用日來源（入選股，ts＝上傳時戳、a2＝期限＋5）：{json.dumps(S['ROE 可用日來源（入選股）'], ensure_ascii=False)}</li>")
    H.append(f"<li>0050 錨逐位元：{S['閘']['0050 主窗錨逐位元']}；查核：{ck.get('結論', '（未跑）')}</li>")
    H.append("<li>出處：backtest/researchExtX1.py、resultsExtX1/summary.json、picks.csv.gz、fake.csv.gz、eq.npz、check.json</li></ul></body></html>")
    open(os.path.join(OUT, "REPORT.html"), "w", encoding="utf-8").write("\n".join(H))
    print("ok")


if __name__ == "__main__":
    main()
