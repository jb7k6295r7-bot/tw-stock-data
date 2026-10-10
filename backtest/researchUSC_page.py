# -*- coding: utf-8 -*-
"""USREG-C 批（C3～C8）＋ A3-17 驗證段 網頁：resultsUSC/美股自選研究C批.html（只讀各件 JSON 彙總；⛔ 不含任何逐日價格或財報原值）。

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSC_page
"""
from __future__ import annotations

import html
import json
import os

from backtest import researchUSC as K


def J(n):
    return json.load(open(os.path.join(K.OUT, n), encoding="utf-8"))


def pc(x, d=1):
    return "—" if x is None else f"{x * 100:+.{d}f}%"


def e(s):
    return html.escape(str(s))


def main():
    c8, c7, c3, c4, c5, c6 = (J(f"{k}.json") for k in ("C8", "C7", "C3", "C4", "C5", "C6"))
    ck = J("check.json")
    a17 = json.load(open(os.path.expanduser("~/tw-p17/backtest/resultsUSA34/A3/A3-17_verify.json"), encoding="utf-8"))
    rows = [
        ("C7 進場方式", "12", c7["卡片"]["標籤"], "大盤、QQQ、正2：一次買都比定期定額好（約七到八成起點贏）；等跌 10% 再買在大盤／QQQ 分不出、在正2 反而比定期定額好。"),
        ("C3 經典動能", "1", c3["卡片"]["標籤"], f"年化 {pc(c3['三欄']['合併']['年化'])}，回落 {pc(c3['三欄']['合併']['回落'])}，沒贏 ^SP500TR；只 S&P 500 合格、只 S&P 400 不合格（方向相反）。"),
        ("C4 剔除股反彈", "2", f"事件層 {c4['卡片']['標籤']['甲 事件層']}；組合層 {c4['卡片']['標籤']['乙 組合層']}", f"被踢後一年平均輸大盤 {pc(-c4['甲']['主（determined＝1）']['平均'])[1:]}（CI 含 0）；組合層近乎一路抱 8 檔到窗尾。"),
        ("C5 同月季節性", "2", f"事件層 {c5['卡片']['標籤']['事件層']}；組合層 {c5['卡片']['標籤']['組合層']}", f"組合年化 {pc(c5['三欄']['合併']['組合']['年化'])}、回落 {pc(c5['三欄']['合併']['組合']['回落'])}，比隨機挑還差。"),
        ("C6 現金獲利", "2", f"事件層 {c6['卡片']['標籤']['事件層']}；組合層 {c6['卡片']['標籤']['組合層']}", f"組合年化 {pc(c6['三欄']['合併']['組合']['年化'])}，沒贏大盤；與 Chen & Welch 2026 一致。"),
        ("C8 波動目標穩健性", "不計", c8["卡片"]["標籤"], "原格好，但放大網格後不是一大片：真實一（2007～2021）只有 25% 格子好；不判合格、只描述。"),
    ]
    H = ["<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
         "<title>美股自選研究C批</title><style>body{background:#fff;color:#222;font-family:system-ui,'Noto Sans TC',sans-serif;margin:0 auto;max-width:960px;padding:16px;line-height:1.6}",
         "table{border-collapse:collapse;width:100%;font-size:14px}td,th{border:1px solid #ddd;padding:6px;vertical-align:top}th{background:#f3f4f6;text-align:left}",
         ".k{background:#fff7e6;border-left:4px solid #f59e0b;padding:8px 12px;margin:12px 0}.w{overflow-x:auto}h2{border-bottom:2px solid #eee;padding-bottom:4px;margin-top:28px}small{color:#666}</style></head><body>",
         "<h1>美股自選研究 C 批（C3～C8）＋ A3-17 驗證段</h1>",
         f"<p><small>回測線計算子代理｜算於 {e(K.now_tpe())}（台北）｜裁定 seq321｜只放彙總，⛔ 無逐日價格、財報原值</small></p>",
         "<div class='k'><b>結論先講：</b>六件裡沒有一件「選股／擇時」規則贏過 ^SP500TR。唯一有用的是 C7：<b>手上有一筆錢要買大盤（或 QQQ、正2），一次買進大多數時候比分 12 個月定期定額好</b>（約七到八成的起點）；"
         "等跌 10% 再買沒有好處（大盤、QQQ 分不出）。C8 波動目標的好成績不是一大片參數都好，只是「中間」。A3-17 的 9 個飆股「結束特徵」在 2024～2026 驗證段全部沒站住。</div>",
         "<h2>一、各件一句話</h2><div class='w'><table><tr><th>件</th><th>N</th><th>標籤</th><th>白話</th></tr>"]
    for a, n, l, s in rows:
        H.append(f"<tr><td>{e(a)}</td><td>{e(n)}</td><td>{e(l)}</td><td>{e(s)}</td></tr>")
    H.append("</table></div><p><small>N 合計（本子代理六件）：C7 12＋C3 1＋C4 2＋C5 2＋C6 2 ＝ 19；C8 不計。A3-17 驗證 N 9。</small></p>")
    H.append("<h2>二、結果句（照登錄查表）</h2>")
    for nm, d in (("C7", c7), ("C3", c3), ("C4", c4), ("C5", c5), ("C6", c6), ("C8", c8)):
        H.append(f"<h3>{nm}｜{e(d['卡片']['名稱'])}</h3><p>{e(d['卡片']['結果句'])}</p>")
        if "條件出場必報" in d["卡片"]:
            H.append(f"<p><small>條件出場必報：{e(json.dumps(d['卡片']['條件出場必報'], ensure_ascii=False))}</small></p>")
        if d["卡片"].get("偏離"):
            H.append("<p><small>偏離：" + "；".join(e(x) for x in d["卡片"]["偏離"]) + "</small></p>")
    H.append("<h2>三、C7 十二格</h2><div class='w'><table><tr><th>標的</th><th>法</th><th>3 年後比定期定額（中位）</th><th>贏的起點比例</th><th>Bonferroni CI</th><th>判語</th><th>最差 10% 起點</th></tr>")
    for c in c7["逐格"]:
        H.append(f"<tr><td>{e(c['標的'])}</td><td>{e({'L': '一次買', 'B': '等跌10%', 'T': '均線擇時'}[c['法']])}</td><td>{pc(c['中位'])}</td><td>{c['贏D比例']:.0%}</td>"
                 f"<td>{c['贏D_CI'][0]:.0%}～{c['贏D_CI'][1]:.0%}</td><td>{e(c['判語'])}</td><td>{pc(c['x_p10'])}</td></tr>")
    H.append("</table></div><p><small>起點每月滾動、相鄰起點重疊 ⇒ 有效樣本約等於年數（^SP500TR 約 34 年、QLD 約 17 年）。SSO 2006-06 前是合成。</small></p>")
    H.append("<h2>四、C8 參數高原（112 格）</h2><div class='w'><table><tr><th>段</th><th>好格</th><th>讀法</th><th>SSO 好格</th><th>QLD 好格</th><th>贏同槓桿固定比例</th></tr>")
    for sg, p in c8["高原"].items():
        H.append(f"<tr><td>{e(sg)}</td><td>{p['好格數']}／{p['格數']}</td><td>{e(p['讀法'])}</td><td>{p['SSO好格比例']:.0%}</td><td>{p['QLD好格比例']:.0%}</td><td>{p['看波動贏固定同槓桿比例（全部格）']:.0%}</td></tr>")
    H.append(f"</table></div><p>前瞻：2026-10 原格建議 QLD 比例 {c8['前瞻']['2026-10 建議 QLD 比例']:.0%}（σ̂ {c8['前瞻']['σ̂']:.1%}）。</p>")
    H.append("<h2>五、A3-17 驗證段（結束族 9 個）</h2><div class='w'><table><tr><th>族</th><th>級距</th><th>探索過門檻格</th><th>驗證 Bonf 下緣＞1 格</th><th>標籤</th></tr>")
    for r in a17["逐級距"]:
        H.append(f"<tr><td>{e(r['族'])}</td><td>{e(r['級距'])}</td><td>{r['探索']['過門檻格數']}</td><td>{r['合併']['Bonf下緣>1格數']}／250</td><td>{e(r['標籤'])}</td></tr>")
    H.append(f"</table></div><p>{e(a17['卡片']['結果句'])}</p>")
    H.append(f"<h2>六、查核</h2><p>--check 獨立重算抽樣 {ck['總抽樣']} 個值、不同 {ck['總不同']}；A3-17 驗證段另抽 3 個級距、不同 0。換股簿三件主臂與 researchUSA4.sim_book 逐日相同。</p>")
    H.append(f"<p><small>{e(K.SURV)}。</small></p></body></html>")
    p = os.path.join(K.OUT, "美股自選研究C批.html")
    open(p, "w", encoding="utf-8").write("\n".join(H))
    print(p)


if __name__ == "__main__":
    main()
