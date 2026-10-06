# -*- coding: utf-8 -*-
"""PREREG期貨短線日線四題 seq2 網頁（resultsTXS/期貨短線日線四題.html）：結論先講、白話、手機可讀。只讀 resultsTXS 的彙總檔（⛔ 不讀私有庫）。"""
import json
import os

import pandas as pd

from backtest.researchTXF_page import CSS, p, tbl

OUT = os.path.expanduser("~/tw-p17/backtest/resultsTXS")


def ci(r, d=2, x="X", lo="lo", hi="hi"):
    return f"{p(r[x], d)}（{p(r[lo], d)}～{p(r[hi], d)}）"


def main():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    ck = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else {}
    A, B, Cc, Dd = S["甲"], S["乙"], S["丙"], S["丁"]
    CA = pd.read_csv(os.path.join(OUT, "A_cells.csv")); TA = pd.read_csv(os.path.join(OUT, "A_trade.csv"))
    CC = pd.read_csv(os.path.join(OUT, "C_cells.csv")); CD = pd.read_csv(os.path.join(OUT, "D_cells.csv"))
    H = ["<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
         "<title>期貨短線日線四題</title>", CSS, "</head><body>", "<h1>期貨短線日線四題：日曆、大跌隔天、短期趨勢</h1>",
         f"<p class='note'>回測線｜{S['產出']}｜登錄 {S['件']}｜讀法寫死 {S['讀法寫死']}｜期交所原始數字只放私有庫，本頁只有統計結果。</p>"]

    def acell(cell, seg, ser="TX 近月"):
        return CA[(CA["序列"] == ser) & (CA["格"] == cell) & (CA["段"] == seg)].iloc[0]

    def tr(key, seg):
        return TA[(TA["格"] == key) & (TA["段"] == seg)].iloc[0]
    J = A["判定"]
    a1e = acell(J["甲1"]["格"], "早年"); a2e = acell(J["甲2"]["格"], "早年"); a3i = acell(J["甲3"]["格"], "早年（加權指數）", "加權指數")
    c_ = lambda cell, H_, seg: CC[(CC["格"] == cell) & (CC["H"] == H_) & (CC["段"] == seg)].iloc[0]
    k2 = "丙2 收盤報酬 ≤ −3%"
    d_ = lambda ver, seg: CD[(CD["版"] == ver) & (CD["段"] == seg)].iloc[0]
    o50 = Dd["0050"]
    best = max((5, 10, 20, 60), key=lambda L: d_(f"L{L} 多空", "確認")["年化"])
    jc = [acell(J[k]["格"], s) for k in ("甲1", "甲2", "甲3") for s in ("探索", "確認")]
    all_neg_cost = all(r["扣成本高_lo"] < 0 for r in jc)
    cmin = min(r["平均來回成本高"] for r in jc); cmax = max(r["平均來回成本高"] for r in jc)
    hold_rng = [tr(k, s)["持多比例"] for k in ("甲1", "甲2", "甲3") for s in ("早年", "探索", "確認")]
    lo_rows = [(d_(f"L{L} 只做多（描述）", s), o50[s]) for L in (5, 10, 20, 60) for s in ("探索", "確認")]
    lo_all_lower = all(r["年化"] < o["年化"] for r, o in lo_rows); lo_all_shallow = all(r["最大回落"] > o["最大回落"] for r, o in lo_rows)
    ls_below_lo = all(d_(f"L{L} 多空", s)["年化"] < d_(f"L{L} 只做多（描述）", s)["年化"] for L in (5, 10, 20, 60) for s in ("早年", "探索", "確認"))
    # ── 結論
    H.append("<div class='box bad'><b>結論：四題做了三題，都沒有找到可以拿來交易的規律；乙（台指VIX）停判。</b><ol>"
             f"<li><b>甲 日曆效應：3 格 {A['有 格數']} 格成立</b>（月底月初、節前、星期一都「測不出」）。"
             f"月底月初、節前在早年偏漲（節前在台指期 1998～2014 比平常多 {p(a2e['X'], 2)}、區間不跨 0；兩者在加權指數 1990～2014 也都不跨 0），"
             "但 2015 年以後的探索、確認兩段都不見了。"
             f"只在這幾天持有台指期，扣成本後年化遠低於一直持有（月底月初版：探索 {p(tr('甲1', '探索')['年化'])}、確認 {p(tr('甲1', '確認')['年化'])}；"
             f"一直持有 {p(tr('（對照）', '探索')['年化'])}、{p(tr('（對照）', '確認')['年化'])}）。</li>"
             f"<li><b>丙 大跌隔天開盤買：3 個持有天數（1／3／5 天）{Cc['成立 H 數']} 個成立</b>（每個持有天數 4 格裡 "
             + "、".join(f"H{h} {Cc['判定'][f'H{h}']['有 格數（/4）']} 格" for h in (1, 3, 5)) + " 成立，要 3 格才算）。"
             f"早年大跌之後隔天確實偏漲，但近幾年不穩：跌 3% 以上隔天，探索段比平常多 {p(c_(k2, 1, '探索')['X'], 2)}、確認段反而少 {p(abs(c_(k2, 1, '確認')['X']), 2, False)}，"
             "兩段方向相反。<br>⚠ 這四格和以前測過的「大盤反轉訊號」（RSI 跌破 30 後站回、低檔爆量長下影）同屬「超賣後反彈」一族；同族舊訊號已經 0 格，這次也一樣。</li>"
             f"<li><b>丁 看過去 5／10／20／60 天漲跌做多或放空：不合格</b>（對 0050，探索、確認兩段各 4 格，合格 "
             f"{Dd['判定']['各段合格數']['探索']['合格']}／4、{Dd['判定']['各段合格數']['確認']['合格']}／4）。"
             f"四種天數的年化都輸 0050（確認段最好的 L{best} 是 {p(d_(f'L{best} 多空', '確認')['年化'])}，0050 {p(o50['確認']['年化'])}）。</li>"
             "<li><b>乙 台指VIX 恐慌後：停判</b>——台指VIX 免費資料只有約 3 個月，資料庫每日累積中；滿兩段可切時另登錄。⛔ 沒有用選擇權價格自己重算 VIX 代替。</li></ol>"
             "<p class='note'>白話：台指期日線上這些常聽到的短線規律（月初效應、節前行情、週一效應、大跌搶反彈、短期追趨勢），在 2015 年以後扣掉期貨成本都沒有穩定的優勢。</p></div>")
    # ── 甲
    H.append("<h2>甲　日曆效應：特定日子大盤有沒有固定偏多／偏空</h2>")
    H.append("<p>做法：月底月初＝每月最後 1 個交易日加次月前 3 個交易日（4 天，前一天收盤買、第 4 天收盤賣）；節前＝國定假日（含春節，颱風停市不算）前最後一個交易日；"
             "星期一＝上週最後一天收盤到週一收盤。跟同一段所有交易日、同樣持有天數的平均比（差），兩段（探索 2015～2020、確認 2021～2026-09）都同方向、95% 區間都不跨 0 才算「有」。</p>")
    rows = []
    for key in ("甲1", "甲2", "甲3"):
        cell = J[key]["格"]
        rows.append([cell, ci(acell(cell, "早年")), ci(acell(cell, "早年（加權指數）", "加權指數")), ci(acell(cell, "探索")), ci(acell(cell, "確認")),
                     f"{int(acell(cell, '探索')['n'])}／{int(acell(cell, '確認')['n'])}", J[key]["標籤"]])
    H.append("<h3>判定格（台指期近月；比平常多多少，括號 95% 區間）</h3>")
    H.append(tbl(["格", "早年 1998～2014", "早年 加權指數 1990～2014", "探索", "確認", "筆數 探索／確認", "判定"], rows))
    rows = []
    for cell in ("甲1 另報：3 日讀法", "甲2 另報：春節前", "甲2 另報：春節以外的節前", "甲3 另報：星期二", "甲3 另報：星期三", "甲3 另報：星期四", "甲3 另報：星期五"):
        rows.append([cell.replace("另報：", ""), ci(acell(cell, "早年")), ci(acell(cell, "早年（加權指數）", "加權指數")), ci(acell(cell, "探索")), ci(acell(cell, "確認")),
                     f"{int(acell(cell, '探索')['n'])}／{int(acell(cell, '確認')['n'])}"])
    H.append("<h3>另報（只描述、不判）</h3>" + tbl(["格", "早年 1998～2014", "早年 加權指數", "探索", "確認", "筆數 探索／確認"], rows))
    H.append(f"<p class='note'>早年方向：月底月初、節前在早年偏正（加權指數 1990～2014 也一樣、區間不跨 0）；星期一早年偏負"
             f"（加權指數 {p(a3i['X'], 2)}，區間 {p(a3i['lo'], 2)}～{p(a3i['hi'], 2)}），探索段轉正、確認段又負。"
             f"扣成本後（期交稅＋滑價＋手續費高案，一筆來回平均 {p(cmin, 3, False)}～{p(cmax, 3, False)}）三格兩段的區間下緣"
             + ("也都 ＜ 0。" if all_neg_cost else "並非都 ＜ 0（見 A_cells.csv）。") + "</p>")
    rows = []
    for key, lab in (("（對照）", "一直持有台指期 1 倍"), ("甲1", "只在月底月初持有"), ("甲2", "只在節前持有"), ("甲3", "只在星期一持有")):
        rows.append([lab] + [f"{p(tr(key, s)['年化'])}／{p(tr(key, s)['最大回落'])}" for s in ("早年", "探索", "確認")] + [p(tr(key, "確認")["持多比例"], 0, False)])
    H.append("<h3>交易版（只描述）：只在那幾天持有台指期多單、其餘時間空手（年化／最大回落）</h3>")
    H.append(tbl(["做法", f"早年（{tr('（對照）', '早年')['窗'][:7]} 起）", "探索", "確認", "持有天數占比"], rows))
    H.append("<p class='note'>空手時現金收臺銀一年定存利息、持有時保證金以外的現金也收利息；每月結算日轉倉。"
             f"持有天數只占 {p(min(hold_rng), 0, False)}～{p(max(hold_rng), 0, False)}，報酬自然比一直持有低很多。</p>")
    h = A["假日辨識"]
    H.append(f"<p class='note'>國定假日怎麼認：官方休市表本機只有 2021 年起，所以用交易日曆找「平日沒開盤」的休市段，段內有國定假日（含農曆春節、端午、中秋，"
             f"農曆日期用 Windows 內建台灣農曆換算，並驗證 {h['農曆驗證（TX 日曆）']['落在平日的初一／端午／中秋']} 個落在平日的農曆節日都沒開盤）才算；"
             f"颱風、地震等其他休市 {len(h['TX 非假日平日休市（颱風、地震、選舉等；⛔ 不算節前）'])} 次不算。台指期期間共 {h['TX 假日休市段']} 次節前（春節 {h['其中春節']} 次）。</p>")
    # ── 乙
    H.append("<h2>乙　台指VIX 恐慌之後買台指期</h2>")
    H.append(f"<div class='box mid'><b>停判</b>：台指VIX 免費資料只有約 3 個月（2026-07 起），資料庫每日累積中；照登錄「資料缺 ⇒ 本題停」。"
             "⛔ 不用選擇權價格自行重算 VIX 代替（屬「拿別的資料代替」，要做須使用者明示）。原 6 格（N_單筆 6）待裁定核減。</div>")
    # ── 丙
    H.append("<h2>丙　大盤大跌之後，隔天開盤買、抱 1／3／5 天</h2>")
    H.append("<p>觸發（收盤後判斷）：台指期當天跌 2% 以上、跌 3% 以上、2 日 RSI ≤ 10、2 日 RSI ≤ 5。隔天開盤買、第 1／3／5 個交易日收盤賣，"
             "跟同段所有日子同樣買法的平均比。每個持有天數 4 格裡要有 3 格「兩段同方向且區間不跨 0」才算這個持有天數成立。</p>")
    for h_ in (1, 3, 5):
        rows = []
        for cell in ("丙1 收盤報酬 ≤ −2%", "丙2 收盤報酬 ≤ −3%", "丙3 2 日 RSI ≤ 10", "丙4 2 日 RSI ≤ 5"):
            v = Cc["判定"][f"H{h_}"]["格"][cell[:2]]
            rows.append([cell] + [ci(c_(cell, h_, s)) for s in ("早年", "探索", "確認")] + [f"{int(c_(cell, h_, '探索')['n'])}／{int(c_(cell, h_, '確認')['n'])}",
                         f"{p(c_(cell, h_, '探索')['扣成本高_lo'], 2)}／{p(c_(cell, h_, '確認')['扣成本高_lo'], 2)}", "有" if v["有"] else "沒有"])
        jj = Cc["判定"][f"H{h_}"]
        H.append(f"<h3>抱 {h_} 天：{jj['有 格數（/4）']}／4 格成立 ⇒ {jj['標籤']}</h3>")
        H.append(tbl(["觸發", "早年 1998～2014", "探索 2015～2020", "確認 2021～2026-09", "筆數 探索／確認", "扣成本後下緣 探索／確認", "格判定"], rows))
    H.append(f"<p class='note'>全期觸發天數：" + "、".join(f"{k} {v} 天" for k, v in Cc["觸發日數（全期）"].items())
             + "。連續幾天都符合就各算一筆（持有期會重疊，區間用月分群處理）。⚠ " + Cc["同族註"] + "</p>")
    # ── 丁
    H.append("<h2>丁　看過去 L 天漲跌：漲就做多、跌就放空台指期（1 倍）</h2>")
    H.append("<p>每天收盤看過去 L 天（5／10／20／60）台指期漲跌，方向變了隔天開盤換（多翻空、空翻多）；保證金以外的現金收定存利息，成本用高案。"
             "判準（使用者的）：年化 ＞ 0050，而且「年化 ÷ 最大回落」不比 0050 差；探索、確認兩段都要 4 格裡 3 格合格。</p>")
    rows = []
    for L in (5, 10, 20, 60):
        rows.append([f"L{L}"] + [f"{p(d_(f'L{L} 多空', s)['年化'])}／{p(d_(f'L{L} 多空', s)['最大回落'])}（{d_(f'L{L} 多空', s)['判準（對 0050）']}）" for s in ("早年", "探索", "確認")]
                    + [f"{d_(f'L{L} 多空', '確認')['換手次數／年']:.0f}"])
    rows.append(["0050"] + [f"{p(o50[s]['年化'])}／{p(o50[s]['最大回落'])}" for s in ("早年", "探索", "確認")] + ["—"])
    H.append(f"<h3>判定：{Dd['判定']['標籤']}（年化／最大回落；括號是對 0050 的判準）</h3>")
    H.append(tbl(["L", f"早年（{o50['早年']['窗']}，照報不判）", "探索", "確認", "確認段每年換手次數"], rows))
    rows = []
    for ver, lab in [(f"L{L} 只做多（描述）", f"L{L} 只做多（跌就空手）") for L in (5, 10, 20, 60)] + [("TX 一直持多 1 倍（描述）", "台指期一直持多 1 倍")]:
        rows.append([lab] + [f"{p(d_(ver, s)['年化'])}／{p(d_(ver, s)['最大回落'])}" for s in ("早年", "探索", "確認")])
    H.append("<h3>描述（不判）：只做多版、一直持有</h3>" + tbl(["做法", "早年", "探索", "確認"], rows))
    H.append("<p class='note'>"
             + ("只做多版在探索、確認兩段的最大回落都比 0050 淺，" if lo_all_shallow else "只做多版的回落見上表，")
             + ("但年化都低於 0050（不合判準條件一）；" if lo_all_lower else "年化並非都低於 0050（見 D_cells.csv）；")
             + ("多空版每一格年化都低於只做多版 ⇒ 放空那一半整體是虧的。" if ls_below_lo else "")
             + "台指期一直持多跟 0050 的差主要來自指數不同（加權指數 vs 台灣 50），見期貨六題。</p>")
    # ── 先驗
    pri = {"①（甲）": A["先驗①"], "③（丙）": Cc["先驗③"], "④（丁）": Dd["先驗④"]}
    H.append("<h2>先驗（登錄 §七，寫下就不改）</h2><ul>" + "".join(
        f"<li>{k}：" + "；".join(f"{kk}：{'中' if vv else '沒中'}" for kk, vv in v.items() if isinstance(vv, bool)) + "</li>" for k, v in pri.items())
        + "<li>②（乙）：停判，無法驗。</li></ul>")
    # ── 做法
    H.append("<h2>做法、限制與查核</h2><ul>"
             "<li>價格一律用台指期大台（TX）近月連續價格（結算日以結算價了結、同日收盤換下個月）；資料、轉倉、成本、區間算法都直接沿用期貨六題的程式。</li>"
             "<li>成本高案：期交稅每邊 0.002%＋滑價每邊 1 點＋手續費每口小台 50 元；判定用高案，低案（20 元）在 CSV。</li>"
             "<li>執行者補的讀法寫在 backtest/researchTXS.py 開頭（2026-10-06 14:55 台北寫死），主要是：月底月初取 4 天窗（括號裡 3 天的寫法另報）、"
             "國定假日用交易日曆＋假日名單辨識（15:05 補上 2025 年起恢復的教師節、光復節、行憲紀念日，判定不變）、2 日 RSI 用 Wilder 平滑、"
             "「可交易」須先「有」、丁的早年窗從 0050 有資料起。</li>"
             "<li>本件沒有個股母體，GATE_V2 不適用。</li>"
             f"<li>查核（--check，從原始列自己逐日走契約、帳戶用契約口數記帳）：{ck.get('結論', '（未跑）')}；"
             + "；".join(f"{k.split('（')[0].split(' ')[0]} 比對 {v['比對']}、不同 {v['不同']}" for k, v in ck.items() if isinstance(v, dict) and "比對" in v) + "。</li>"
             "<li>出處：backtest/researchTXS.py、researchTXS_check.py、researchTXS_page.py；resultsTXS/（summary.json、A_cells.csv、A_trade.csv、C_cells.csv、D_cells.csv、check.json）。</li></ul>"
             "</body></html>")
    open(os.path.join(OUT, "期貨短線日線四題.html"), "w", encoding="utf-8").write("\n".join(H))
    print("ok")


if __name__ == "__main__":
    main()
