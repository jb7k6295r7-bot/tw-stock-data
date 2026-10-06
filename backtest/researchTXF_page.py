# -*- coding: utf-8 -*-
"""PREREG台指期貨六題 seq2 網頁（resultsTXF/台指期貨六題.html）：結論先講、白話、手機可讀。只讀 resultsTXF 的彙總檔（⛔ 不讀私有庫）。"""
import json
import os

import numpy as np
import pandas as pd

OUT = os.path.expanduser("~/tw-p17/backtest/resultsTXF")
CSS = """<style>:root{--fg:#222;--bg:#fff;--box:#f4f6fa;--line:#ddd;--mut:#666;--ok:#3a6;--bad:#c44;--mid:#c90}
@media(prefers-color-scheme:dark){:root{--fg:#ddd;--bg:#111;--box:#1d2230;--line:#444;--mut:#999}}
body{font-family:-apple-system,'Noto Sans TC',sans-serif;margin:0 auto;max-width:820px;padding:0 16px 40px;line-height:1.65;color:var(--fg);background:var(--bg)}
h1{font-size:1.3em}h2{font-size:1.12em;margin-top:1.8em;border-bottom:1px solid var(--line)}h3{font-size:1em;margin-top:1.2em}
.box{background:var(--box);border-left:4px solid var(--ok);padding:10px 12px;margin:12px 0}.bad{border-left-color:var(--bad)}.mid{border-left-color:var(--mid)}
.wrap{overflow-x:auto}table{border-collapse:collapse;font-size:.85em;min-width:100%}td,th{border:1px solid var(--line);padding:3px 6px;text-align:right;white-space:nowrap}
td.l,th.l{text-align:left}.note{color:var(--mut);font-size:.85em}b.hl{color:var(--bad)}</style>"""


def p(x, d=1, sign=True):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—" if x is None else str(x)
    if not np.isfinite(x):
        return "—"
    return f"{x * 100:+.{d}f}%" if sign else f"{x * 100:.{d}f}%"


def pt(x, d=1):
    return f"{x * 100:.{d}f} 點"


def tbl(head, rows, left=1):
    h = "<div class='wrap'><table><tr>" + "".join(f"<th class='{'l' if i < left else ''}'>{c}</th>" for i, c in enumerate(head)) + "</tr>"
    for r in rows:
        h += "<tr>" + "".join(f"<td class='{'l' if i < left else ''}'>{c}</td>" for i, c in enumerate(r)) + "</tr>"
    return h + "</table></div>"


def main():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    ck = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else {}
    A, B, Cc, Dd, E, F = (S[k] for k in ("甲", "乙", "丙", "丁", "戊", "己"))
    CA = pd.read_csv(os.path.join(OUT, "A_cells.csv")); CB = pd.read_csv(os.path.join(OUT, "B_cells.csv"))
    CC = pd.read_csv(os.path.join(OUT, "C_cells.csv")); CD = pd.read_csv(os.path.join(OUT, "D_cells.csv")); CE = pd.read_csv(os.path.join(OUT, "E_cells.csv"))
    CR = pd.read_csv(os.path.join(OUT, "F_rev_cells.csv")); CY = pd.read_csv(os.path.join(OUT, "F_y_cells.csv"))
    H = ["<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
         "<title>台指期貨六題</title>", CSS, "</head><body>", "<h1>台指期貨六題：小台／微台能做到哪裡</h1>",
         f"<p class='note'>回測線｜{S['產出']}｜登錄 PREREG台指期貨六題 seq2（sha 8ea4f8b4010de81f）｜讀法寫死 {S['讀法寫死']}｜"
         "期交所原始數字只放私有庫，本頁只有統計結果。</p>"]
    # ── 結論
    mt = A["主表"]
    seg_line = "；".join(f"{s}段 年化 {p(mt[s]['期貨_年化'])} vs 0050 {p(mt[s]['ETF_年化'])}，最大回落 {p(mt[s]['期貨_回落'], 2)} vs {p(mt[s]['ETF_回落'], 2)}"
                        for s in ("探索", "確認"))
    deep = "；".join(f"{s}段 回落比 0050 深 {pt(abs(mt[s]['期貨_回落']) - abs(mt[s]['ETF_回落']))}、報酬多 {pt(mt[s]['期貨_年化'] - mt[s]['ETF_年化'])}" for s in ("探索", "確認", "早年"))
    b5 = CB[(CB["L"].astype(str) == "5") & (CB["起點組"] == "保證金有資料（2004-09-30 起）")].iloc[0]
    b10 = CB[(CB["L"].astype(str) == "10") & (CB["起點組"] == "保證金有資料（2004-09-30 起）")].iloc[0]
    b14 = CB[(CB["L"].astype(str) == "14") & (CB["起點組"] == "保證金有資料（2004-09-30 起）")].iloc[0]
    H.append("<div class='box mid'><b>一句話（照登錄排序）</b><ol>"
             f"<li><b>甲 用期貨代替 0050／正2：2 倍期貨對 0050 判「{A['判定']['標籤']}」</b>（探索、確認、早年三段都合格）。{seg_line}。"
             f"<br>⚠ 合格但風險大很多：{deep}。這格沒有假訊號臂。1 倍期貨對 0050 只描述：早年、探索贏、確認輸（{p(A['先驗①']['L1 與 0050 年化差（各段）']['確認'])}），"
             "主要因為台指期跟的是加權指數，0050 跟的是台灣 50，近幾年台灣 50 漲得比較多。</li>"
             f"<li><b>乙 槓桿</b>（只描述）：1～3 倍每月調回，2004 年以來任何一天進場、抱一年，<b>沒有一次碰到追繳、沒有賠光</b>；"
             f"5 倍有 {p(b5['一年內碰到追繳比例'], 0, False)} 的起點一年內碰到追繳，10 倍 {p(b10['一年內碰到追繳比例'], 0, False)}，14 倍 {p(b14['一年內碰到追繳比例'], 0, False)}；"
             f"不補錢的話一年內賠光：5 倍 {p(b5['不補_一年內賠光比例'], 0, False)}、10 倍 {p(b10['不補_一年內賠光比例'], 0, False)}、14 倍 {p(b14['不補_一年內賠光比例'], 0, False)}。</li>"
             f"<li><b>丙 夜盤 → 隔天日盤：6 格 {Cc['成立格數']} 格成立</b>，測不出延續或反轉，照夜盤進出扣成本也不能做。</li>"
             f"<li><b>丁 TXO 賣買權比：6 格 {Dd['成立格數']} 格有預測力</b>；外資期貨未平倉只有約 2 年資料，只描述、不判。</li>"
             f"<li><b>戊 結算週：3 格 {E['成立格數']} 格成立</b>，測不出固定走勢。</li>"
             f"<li><b>己 舊大盤訊號改用期貨成本：翻轉 {F['翻轉格數合計']} 格</b>（事後重算）。舊結論不變：不是成本的問題。</li></ol></div>")
    # ── 甲
    H.append("<h2>甲　用台指期代替 0050／正2</h2>")
    H.append("<p>做法：一直持有台指期近月；每月結算日用結算價了結、同一天收盤買下個月（轉倉），轉倉後把槓桿調回 1 倍或 2 倍。"
             "帳戶裡保證金以外的現金收臺銀一年定存利息。成本：期交稅每邊 0.002%＋滑價每邊 1 點＋手續費每口小台 50 元（判定用這個高案）。"
             "台指是不含息的價格指數，所以期貨價格平常比指數低（逆價差），持有到結算會慢慢收斂回來，這部分本頁照實算進報酬。</p>")
    rows = []
    for s in ("早年", "探索", "確認"):
        m = mt[s]
        rows.append([f"{s}（{m['窗']}）", p(m["期貨_年化"], 2), p(m["ETF_年化"], 2), p(m["期貨_回落"], 2), p(m["ETF_回落"], 2), f"{m['期貨_回落比']:.3f}", f"{m['ETF_回落比']:.3f}",
                     A["判定"]["各段"][s], f"{m['期貨_年化÷波動']:.2f}／{m['ETF_年化÷波動']:.2f}"])
    H.append("<h3>判定格：2 倍期貨（結算日轉倉、每月調回、手續費高案）vs 0050</h3>")
    H.append(tbl(["段", "期貨年化", "0050 年化", "期貨最大回落", "0050 最大回落", "期貨 年化÷|回落|", "0050 年化÷|回落|", "判準", "年化÷波動（期貨／0050）"], rows))
    H.append("<p class='note'>使用者判準：條件一 年化 ＞ 0050；條件二 年化÷|最大回落| ≥ 0050。兩段（探索、確認）都合格才算合格；早年段照報。"
             "年化用日曆天數算、與 0050 同窗同式（不是 0050 錨 24.02% 那個窗，不並列）。</p>")

    def arow(var, bn):
        x = CA[(CA["變體"] == var) & (CA["對照"] == bn)]
        return x.set_index("段")
    H.append("<h3>其他比較（只描述）</h3>")
    rows = []
    for lab, var, bn in (("1 倍期貨 vs 0050", "L1|結算日轉倉|每月調回|手續費高", "0050"), ("2 倍期貨 vs 00631L（正2）", "L2|結算日轉倉|每月調回|手續費高", "00631L"),
                         ("2 倍期貨 vs 0050 每日 2 倍（合成）", "L2|結算日轉倉|每月調回|手續費高", "0050×2合成")):
        x = arow(var, bn)
        for s in ("早年", "探索", "確認"):
            if s not in x.index:
                continue
            r = x.loc[s]
            rows.append([lab, s, p(r["期貨_年化"]), p(r["ETF_年化"]), p(r["年化差"]), p(r["期貨_回落"], 2), p(r["ETF_回落"], 2),
                         f"{p(r['每年差_平均'])}（{p(r['每年差_lo'])}～{p(r['每年差_hi'])}，{int(r['年數'])} 年）", p(r["6～9月差_年均"]), p(r["其餘月差_年均"])])
    H.append(tbl(["比較", "段", "期貨年化", "對照年化", "年化差", "期貨回落", "對照回落", "每年差 平均（95%）", "6～9 月差／年", "其餘月差／年"], rows, left=2))
    ix = A["加權指數（不含息，描述）"]
    H.append(f"<p class='note'>同窗加權指數（不含息）年化：早年 {p(ix['早年']['年化'])}、探索 {p(ix['探索']['年化'])}、確認 {p(ix['確認']['年化'])}。"
             "1 倍期貨 ≈ 加權指數漲幅 ＋ 逆價差收斂 ＋ 現金利息 − 成本；0050 ＝ 台灣 50 漲幅 ＋ 配息。兩者差主要來自「指數不同」。</p>")
    rows = []
    for var in sorted(CA["變體"].unique()):
        x = CA[(CA["變體"] == var) & (CA["對照"] == "0050")].set_index("段")
        rows.append([var.replace("|", "｜")] + [f"{p(x.loc[s, '期貨_年化'])}／{p(x.loc[s, '期貨_回落'])}（{x.loc[s, '判準']}）" for s in ("早年", "探索", "確認")])
    H.append("<h3>16 個變體（年化／最大回落；括號是對 0050 的判準，只有主格算數）</h3>" + tbl(["變體", "早年", "探索", "確認"], rows))
    g = A["轉倉價差"]
    H.append("<ul>" + "".join(f"<li>{s}：轉倉 {v['轉倉次數']} 次，次月比近月平均每年 {p(v['每年加總平均（正＝正價差＝做多吃虧）'])}（負＝逆價差，對做多有利），"
                                 f"逆價差占 {p(v['逆價差占比'], 0, False)}；其中 6～9 月除息季每年 {p(v['6～9 月轉倉 每年加總平均'])}</li>" for s, v in g.items()) + "</ul>")
    ev = A["帳戶事件"]["L2|結算日轉倉|每月調回|手續費高"]
    ka, kt = A["核對"]["MTX vs TX"], A["核對"]["TMF vs TX"]
    H.append(f"<p class='note'>主格 2005-02～2026-09：追繳 {ev['追繳次數']} 次、賠光 {ev['賠光日數']} 次。小台（MTX）與大台日報酬相關 {ka['日報酬相關']:.4f}、年化差 {p(ka['年化差（本商品 − TX）'], 2)}；"
             f"微台（TMF，{kt['起']} 起）相關 {kt['日報酬相關']:.4f}、年化差 {p(kt['年化差（本商品 − TX）'], 2)} ⇒ 歷史用大台價格代表小台、微台。"
             f"利率 {A['利率']['最後月']} 以後延用最後一個月（{A['利率']['延用天數']} 個交易日）。最後結算價：期交所資料 {S['資料']['結算價來源']['到期次數']} 次到期中 "
             f"{S['資料']['結算價來源']['以收盤代表']} 次沒給，用到期契約當日收盤代表。</p>")
    # ── 乙
    H.append("<h2>乙　開幾倍槓桿、多常碰到追繳、多常賠光（只描述）</h2>")
    H.append("<p>做法：每個交易日都當一次進場日，抱 250 個交易日（約一年），每月轉倉後把槓桿調回原倍數。追繳 ＝ 收盤權益低於維持保證金（用當時的保證金標準）；"
             "賠光 ＝ 盤中最低價（含夜盤）就把權益打到 0。期貨上市前（1990～1998-07）用加權指數同幅度「推算」，只有收盤價。保證金 2004-09 以前沒有資料 ⇒ 那段追繳寫「無資料」。</p>")
    rows = []
    for _, r in CB.iterrows():
        def q(v, d=0):
            return v if isinstance(v, str) and not v.replace(".", "").replace("-", "").isdigit() else p(v, d, False)
        rows.append([str(r["L"]), r["起點組"], int(r["起點數"]), q(r["一年內碰到追繳比例"], 1), q(r["不補_一年內賠光比例"], 1), q(r["補足_一年內賠光比例"], 1),
                     p(r["不補_一年後權益中位"], 0), p(r["不補_一年後權益最差"], 1), r["不補_最差起點（同為賠光取最早）"]])
    H.append(tbl(["倍數", "起點", "起點數", "一年內碰到追繳", "一年內賠光（不補錢）", "一年內賠光（追繳就補）", "一年後權益中位（不補）", "最差", "最差起點"], rows, left=2))
    H.append("<p class='note'>「追繳就補」＝ 每次追繳都補到原始保證金。⚠ 倍數高過「契約價值÷原始保證金」（近年約 8～28 倍）時，補進去的錢會在下次調倉被再放大，"
             "所以補入金額只放在 B_cells.csv 參考。盤中最低照官方資料，包含盤中瞬間急跌、收盤幾乎平盤的日子。乙不計利息（登錄未列）。</p>")
    # ── 丙
    H.append("<h2>丙　夜盤漲跌之後，隔天日盤延續還是反轉？</h2>")
    H.append("<p>夜盤報酬 ＝ 夜盤收 ÷ 前一天日盤收 − 1，跟過去 250 天比排成 10 組；看最高組、最低組隔天日盤（開→收）與「夜盤收→日盤收」比平常多多少。兩段同方向且 95% 區間不跨 0 才算。</p>")
    rows = []
    for k, v in Cc["判定"].items():
        a = CC[(CC["段"] == "探索") & (CC["格"] == k)].iloc[0]; b = CC[(CC["段"] == "確認") & (CC["格"] == k)].iloc[0]
        rows.append([k, f"{p(a['X'], 3)}（{p(a['lo'], 3)}～{p(a['hi'], 3)}，n {int(a['n'])}）", f"{p(b['X'], 3)}（{p(b['lo'], 3)}～{p(b['hi'], 3)}，n {int(b['n'])}）",
                     "成立" if (v.get("成立") or v.get("可交易")) else "不成立"])
    H.append(tbl(["格（d＝日盤開→收；d2＝夜盤收→日盤收；交易＝扣成本後）", "探索 2017-05～2021", "確認 2022～2026-09", "判定"], rows))
    H.append(f"<p class='note'>夜盤報酬與隔天日盤報酬的相關 {Cc['描述']['n 與 d 相關']:.3f}（幾乎 0）。分組要 250 個前值 ⇒ 實際從 2018-05 起。"
             "描述：探索段夜盤大跌（最低組）的隔天日盤偏漲、區間不跨 0（像反轉），照登錄的「最低組放空」做反而虧、區間也不跨 0；確認段兩者都不見了 ⇒ 兩段不一致，不算。</p>")
    # ── 丁
    H.append("<h2>丁　選擇權賣權買權比（P/C）能不能預測之後大盤</h2>")
    H.append("<p>指標當天收盤後算、隔天開盤進（公布時點沒實測）；最高 10% 的日子減最低 10% 的日子，看之後 1／5／20 天台指期報酬差。探索、確認都同方向且不跨 0 才算有預測力。</p>")
    rows = []
    for k, v in Dd["判定"].items():
        xn, h = k.split("｜H")
        q = CD[(CD["指標"] == xn) & (CD["H"] == int(h))].set_index("段")
        rows.append([xn, h] + [f"{p(q.loc[s, '差'], 2)}（{p(q.loc[s, 'lo'], 2)}～{p(q.loc[s, 'hi'], 2)}）" for s in ("早年", "探索", "確認")] + ["有" if v["有預測力"] else "沒有"])
    H.append(tbl(["指標", "H", "早年 2002～2014", "探索 2015～2020", "確認 2021～2026-09", "預測力"], rows, left=2))
    xd = CD[CD["指標"].str.startswith("x1") | CD["指標"].str.startswith("x2")]
    H.append("<p class='note'>外資期貨淨未平倉（只有 2023-10 起，分位要 250 天 ⇒ 2024-10 起；不可判定、只描述）："
             + "；".join(f"{r['指標'].split('（')[0]} H{int(r['H'])} 高−低 {p(r['差'], 2)}（{p(r['lo'], 2)}～{p(r['hi'], 2)}，高 {int(r['最高10%_n'])} 天／低 {int(r['最低10%_n'])} 天）" for _, r in xd.iterrows())
             + "。約 2 年、大多是同一段多頭，不可據以判斷。</p>")
    H.append("<p class='note'>描述：早年段（2002～2014）賣權偏多（P/C 高）之後台指期偏漲，x3 H1、x4 H5、x4 H20 區間不跨 0；探索段同方向但區間跨 0，確認段 x4 反向 ⇒ 判準要的探索、確認兩段都沒過。</p>")
    # ── 戊
    H.append("<h2>戊　結算週、結算日前後有沒有固定走勢</h2>")
    rows = []
    for wn, v in E["判定"].items():
        q = CE[(CE["序列"] == "加權指數") & (CE["窗"] == wn)].set_index("段"); qt = CE[(CE["序列"] == "TX 近月") & (CE["窗"] == wn)].set_index("段")
        rows.append([wn] + [f"{p(q.loc[s, 'X'], 2)}（{p(q.loc[s, 'lo'], 2)}～{p(q.loc[s, 'hi'], 2)}）" for s in ("早年", "探索", "確認")]
                    + [f"{p(qt.loc['探索', 'X'], 2)}／{p(qt.loc['確認', 'X'], 2)}", "有" if v["有（加權指數）"] else "沒有"])
    H.append(tbl(["窗（比其他同長度窗多多少）", "早年 1998～2014", "探索 2015～2020", "確認 2021～2026-09", "TX 探索／確認", "判定（加權指數）"], rows))
    H.append("<p class='note'>結算日 ＝ 台指期每月到期日（多半是第 3 個星期三，遇休市順延）。每月一筆，95% 區間。</p>")
    # ── 己
    H.append("<h2>己　以前測過的大盤短線訊號，改用期貨成本會不會翻（事後重算）</h2>")
    j = CR[CR["n_eff"] >= 10]
    passed = int((j["TX扣期貨成本_判定"] == "通過").sum())
    H.append(f"<p>大盤 21 種高低點反轉訊號（原版＋確認版，可判定 {len(j)} 格）：原件 0 格通過；改用台指期報酬、扣期貨來回成本（約 {p(float(np.nanmean(pd.to_numeric(CY['TX扣期貨成本_平均成本'], errors='coerce'))), 3, False)}）後 <b>{passed} 格通過</b>，"
             f"翻轉 {F['反轉訊號']['翻轉']['原不過、現過'] + F['反轉訊號']['翻轉']['原過、現不過']} 格。"
             f"大盤驅動因素 16 格：原件 4 格判得動、都測不出，12 格樣本不足；改期貨後 4 格仍都測不出，翻轉 {F['驅動因素']['翻轉']['原不過、現過'] + F['驅動因素']['翻轉']['原過、現不過']} 格。</p>")
    rows = []
    for _, r in j.iterrows():
        rows.append([f"{r['名']}（{r['版']}）", int(r["事件"]), p(r["0050原（不扣）_X"], 2), p(r["TX扣期貨成本_X"], 2), f"{p(r.get('TX扣期貨成本_lo'), 2)}～{p(r.get('TX扣期貨成本_hi'), 2)}",
                     r["原_判定"], r["TX扣期貨成本_判定"]])
    H.append(tbl(["訊號", "事件", "原件 差（0050、不扣）", "台指期 差（扣成本）", "Bonferroni 區間", "原判定", "改期貨"], rows))
    rows = []
    for _, r in CY.iterrows():
        if r["原_出口"] != "出口①":
            rows.append([f"{r['因素']} {r['名稱']}｜{r['端']}", r["n"], p(r["0050原（不扣）_D"], 2), p(r["TX扣期貨成本_D"], 2),
                         f"{p(r['TX扣期貨成本_lo'], 2)}～{p(r['TX扣期貨成本_hi'], 2)}", r["原_候選"], r["TX扣期貨成本_候選"]])
    H.append(tbl(["驅動因素格（出口②）", "n", "原件 D", "台指期 D", "Bonferroni 區間（未扣成本）", "原", "改期貨"], rows))
    H.append("<p class='note'>⚠ 這些訊號的毛報酬以前就看過 ⇒ 標「事後重算」；就算翻成合格也最多「暫定」、只進前瞻紀錄。期貨來回成本約 0.03%，遠小於股票 0.585%，"
             "但原件不扣成本時就已經 0 格過，所以成本不是原因。閘：0050 原欄逐格等於原件（不同 0）。</p>")
    # ── 先驗與做法
    pri = {"①": A["先驗①"], "②": B["先驗②"], "③": Cc["先驗③"], "④": Dd["先驗④"], "⑤": E["先驗⑤"], "⑥": F["先驗⑥"]}
    H.append("<h2>先驗（登錄 §九，寫下就不改）</h2><ul>" + "".join(
        f"<li>{k}："
        + "；".join(f"{kk}：{'中' if vv is True else ('沒中' if vv is False else '—')}" for kk, vv in v.items() if isinstance(vv, bool)) + "</li>" for k, v in pri.items()) + "</ul>")
    H.append("<h2>做法、限制與查核</h2><ul>"
             "<li>價格一律用台指期大台（TX）近月；小台、微台照契約規模換算（日報酬相關 0.998 以上）。部位用小數口計，實際下單有整數口限制，帳戶小時 1 倍、2 倍不一定湊得剛好。</li>"
             "<li>期交稅照登錄寫死 0.002%（早年實際稅率較高，未依歷史調）。夜盤歸日照官方（t 日的盤後 ＝ 前一天 15:00～t 日 05:00）。</li>"
             "<li>執行者補的讀法都寫在 backtest/researchTXF.py 開頭（2026-10-06 11:50 台北寫死），主要是：最後結算價缺時用收盤代表、各段怎麼合成甲的判定、乙 14 倍用固定 14 倍（另報只放原始保證金版）、"
             "丙丁分位不含當天、戊以加權指數判定、己沿用原件事件與 Bonferroni。</li>"
             "<li>本件沒有個股母體，GATE_V2 不適用。</li>"
             f"<li>查核（--check，從原始列自己逐日走契約、契約口數記帳）：{ck.get('結論', '（未跑）')}；"
             + "；".join(f"{k.split('（')[0]} 比對 {v['比對']}、不同 {v['不同']}" for k, v in ck.items() if isinstance(v, dict) and "比對" in v) + "。</li>"
             "<li>出處：backtest/researchTXF.py、researchTXF_check.py、researchTXF_page.py；resultsTXF/（summary.json、A～E_cells.csv、F_rev_cells.csv、F_y_cells.csv、check.json）。</li></ul></body></html>")
    open(os.path.join(OUT, "台指期貨六題.html"), "w", encoding="utf-8").write("\n".join(H))
    print("ok")


if __name__ == "__main__":
    main()
