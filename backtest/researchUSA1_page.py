# -*- coding: utf-8 -*-
"""USREG-A1-1～5 交件頁：resultsUSA1/REPORT.md（給各線）＋ resultsUSA1/美股大盤ETF五件.html（給使用者：結論先講、白話、手機可讀）。
⛔ 只讀 resultsUSA1/ 的彙總檔（不讀私有庫、不寫任何逐日數字）。

    PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSA1_page
"""
import json
import os

import numpy as np
import pandas as pd

OUT = os.path.expanduser("~/tw-p17/backtest/resultsUSA1")
CSS = """<style>:root{--fg:#222;--bg:#fff;--box:#f4f6fa;--line:#ddd;--mut:#666;--ok:#3a6;--bad:#c44;--mid:#c90}
@media(prefers-color-scheme:dark){:root{--fg:#ddd;--bg:#111;--box:#1d2230;--line:#444;--mut:#999}}
body{font-family:-apple-system,'Noto Sans TC',sans-serif;margin:0 auto;max-width:820px;padding:0 16px 40px;line-height:1.65;color:var(--fg);background:var(--bg)}
h1{font-size:1.3em}h2{font-size:1.12em;margin-top:1.8em;border-bottom:1px solid var(--line)}h3{font-size:1em;margin-top:1.2em}
.box{background:var(--box);border-left:4px solid var(--ok);padding:10px 12px;margin:12px 0}.bad{border-left-color:var(--bad)}.mid{border-left-color:var(--mid)}
.wrap{overflow-x:auto}table{border-collapse:collapse;font-size:.85em;min-width:100%}td,th{border:1px solid var(--line);padding:3px 6px;text-align:right;white-space:nowrap}
td.l,th.l{text-align:left}.note{color:var(--mut);font-size:.85em}</style>"""


def J(n):
    return json.load(open(os.path.join(OUT, n), encoding="utf-8"))


def p(x, d=1, sign=True):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—" if x is None else str(x)
    if not np.isfinite(x):
        return "—"
    return f"{x * 100:+.{d}f}%" if sign else f"{x * 100:.{d}f}%"


def tbl(head, rows, left=1):
    h = "<div class='wrap'><table><tr>" + "".join(f"<th class='{'l' if i < left else ''}'>{c}</th>" for i, c in enumerate(head)) + "</tr>"
    for r in rows:
        h += "<tr>" + "".join(f"<td class='{'l' if i < left else ''}'>{c}</td>" for i, c in enumerate(r)) + "</tr>"
    return h + "</table></div>"


def mdt(head, rows):
    return ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(str(x) for x in r) + " |" for r in rows]


CELLNAME = {"甲": "月底看 SPY 在不在長均線上", "乙": "依最近波動調整正2 比例", "丙": "SPY 從一年高點跌 x% 就全換國庫券"}
VNAME = {"M6": "6 個月線", "M10": "10 個月線", "M12": "12 個月線", "D200": "200 日線（月底看）"}


def a2_plain(fam, key):
    p_ = key.split("_")
    if fam == "甲":
        return f"月底 SPY 收盤在{VNAME[p_[0]]}之上 ⇒ 下個月抱 {p_[2]}，否則抱{'SPY' if p_[1] == 'a' else '國庫券'}"
    if fam == "乙":
        return f"每月初把 {p_[3]} 比例調成 min(1, {p_[0][1:]}% ÷ 過去 {p_[1][1:]} 日年化波動)，其餘放{'SPY' if p_[2] == 'a' else '國庫券'}"
    return f"抱 {p_[0]}；SPY 從 250 日高點跌 {p_[1][1:]}% 全換國庫券；{'SPY 創 60 日新高' if p_[2] == 'R1' else 'SPY 站上 200 日線'}再買回（{'每天' if p_[3] == 'D' else '只在月底'}檢查）"


def main():
    S1, S2, S3, S4, S5 = (J(f"A{i}_summary.json") for i in range(1, 6))
    REC = J("A0_synth_recon.json"); AUD = J("data_audit.json")
    CK = J("check.json") if os.path.exists(os.path.join(OUT, "check.json")) else {}
    C3 = pd.read_csv(os.path.join(OUT, "A3_cells.csv")); C4 = pd.read_csv(os.path.join(OUT, "A4_cells.csv"))
    now = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")
    Bc = S1["確認段"]["基準"]; Be = S1["基準"]["探索"]
    c1, c2 = S1["確認段"]["問一"], S1["確認段"]["問二"]
    rmain = [r for r in REC["結果"] if r["主"]]
    # ── 一句話
    L1 = []
    pk2 = S1["問二"].get("挑中")
    COND = {"C1": "在 200 日線之上", "C2": "在 60 日線之上", "C3": "在 20 日線之上", "C4": "的 50 日線在 200 日線之上"}
    q2txt = (f"SPY 前一天收盤{COND[pk2['條件']]} ⇒ 抱 {pk2['正2']}，否則" + {"X1": "全換國庫券", "X2": f"抱 {pk2['ETF']}", "X3": "照問一比例、正2 那份換國庫券"}[pk2["換法"]]) if pk2 else c2["格"]
    w1_ = S1["假訊號_問一"]["p_合格"]; w2_ = S1.get("假訊號_問二", {}).get("p_合格", np.nan)
    L1.append(f"件一 ETF 比例轉換：比例 ⇒ " + (f"⚠ 隨便配也有 {p(w1_, 1, False)} 合格。" if w1_ >= 0.05 else "")
              + f"探索段挑出「{c1['格']}」，2022～2026 年化 {p(c1.get('年化'))}（S&P 500 含息 {p(Bc['年化'])}）、最大回落 {p(c1.get('回落'))}（{p(Bc['回落'])}）⇒ <b>{c1['標籤']}</b>"
              + ("，照純 SPY" if c1["標籤"] != "合格" else "") + "；轉換 ⇒ " + (f"⚠ 隨便換也有 {p(w2_, 1, False)} 合格。" if w2_ >= 0.05 else "")
              + f"「{q2txt}」年化 {p(c2.get('年化'))}、回落 {p(c2.get('回落'))} ⇒ <b>{c2['標籤']}</b>（報酬高但回落比 S&P 500 深）")
    jd = S2["判定"]
    fk0 = S2["假訊號"]

    def warn2(f):
        v = fk0.get(f, {})
        ps = [v[s]["p（隨機 ≥ 本格）"] for s in ("確認", "早年") if s in v]
        return f"⚠ 隨機換也做得到（p 確認 {v['確認']['p（隨機 ≥ 本格）']:.2f}、早年 {v['早年']['p（隨機 ≥ 本格）']:.2f}）" if ps and max(ps) >= 0.05 else ""
    L1.append("件二 擇時三件：" + "；".join(f"{f} {CELLNAME[f]} ⇒ <b>{j.get('讀法', j.get('判定'))}</b>（挑中：{a2_plain(f, j['格'])}；確認段 年化 {p(j['確認']['年化'])}、一直抱 {j['正2']} {p(j['一直抱正2']['確認']['年化'])}、對 S&P 500 {j['確認']['對基準判準']}；{warn2(f)}）"
                                    for f, j in jd.items() if "格" in j))
    L1.append(f"件三 驅動因素（聯準會升降息、美元、10 年債、VIX）：8 格 <b>{len(S3['候選']['加碼候選']) + len(S3['候選']['減碼候選'])} 格</b>測得出 ⇒ 大盤驅動因素沒有可用的")
    P4s = C4[(C4["層"] == "個股") & (C4["判定"] == "通過")]
    s4 = "無"
    if len(P4s):
        s4 = "；".join(f"〔{nm}（{ver}）〕{'、'.join(str(int(h)) for h in g['H'])} 天：之後比同月、前 20 日同走勢的股票{'少漲' if g['mean'].mean() < 0 else '多漲'} "
                      f"{abs(g['mean']).min() * 100:.1f}～{abs(g['mean']).max() * 100:.1f} 點（{'扣 0.05% 後仍過' if (g['扣成本後'] == '仍過').all() else '扣成本後有不過'}；"
                      f"{'相鄰視窗同向＝穩' if g['穩不穩'].str.contains('穩（').all() else '不穩'}）"
                      for (nm, ver), g in P4s.groupby(["名", "版"]))
    L1.append(f"件四 反轉訊號：大盤層（SPY）21 種訊號 × 2 版 × 4 個天數 <b>{len(S4['通過_大盤'])} 格通過</b>（看不出比隨便一天準）；個股層（S&P 500＋400，2016～2026）通過 {len(P4s)} 格：{s4}"
              "；⚠ 全市場平均、不是對某一檔的預測；S&P 400 有存活者偏差偏樂觀")
    pb = S5["挑法乙"]
    st5 = S5["壓力"]
    worst = [x for x in st5 if x["對象"] == "輪動" and "合成" in x["期間"]]
    s08 = [x for x in st5 if x["對象"] == "輪動" and x["期間"].startswith("2008")]
    lev5 = pb["格"][3]; ph5 = S5["純抱"][lev5]["確認"]
    pw = S5["假訊號"]["p_年化贏基準"]
    L1.append(f"件五 三態輪動：" + (f"⚠ 隨便換也有 {p(pw, 1, False)} 贏 S&P 500。" if pw >= 0.05 else "") + f"「{pb['白話']}」在沒看過的 2022～2026 年化 {p(pb['確認']['年化'])}（S&P 500 {p(Bc['年化'])}）⇒ <b>{pb['判定']}</b>，"
              f"使用者判準 <b>{pb['使用者判準']}</b>（回落 {p(pb['確認']['回落'])}）；對一直抱 {lev5}（{p(ph5['年化'])}）多 {(pb['確認']['年化'] - ph5['年化']) * 100:+.1f} 點；"
              f"⚠ 從 {S5['從x種挑出']:,} 種組合挑出"
              + (f"、2000～2002 科技泡沫（合成）最慘剩 {min(x['谷底剩（萬）'] for x in worst):.0f} 萬" if worst else "")
              + (f"、2008（真實）最慘剩 {s08[0]['谷底剩（萬）']:.0f} 萬" if s08 else "") + "；正2 每日重設、盤整耗損；確認段只有約 4.75 年")
    # ═══ HTML ═══
    H = ["<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
         "<title>美股大盤ETF五件</title>", CSS, "</head><body>", "<h1>美股大盤／ETF 五件：比例、擇時、驅動因素、反轉訊號、三態輪動</h1>",
         f"<p class='note'>回測線｜{now}（台北）｜登錄 USREG-A1 seq1～3（sha 4d6b82a0d0fe84c3／cea9cc6132c26f2f／2f26cfea3035d3a7）｜資料 us-stock-data {AUD['資料commit'][:10]}｜"
         "⚠ 想法來自台股（多數在台股不合格）；美股私有原始數字只放私有庫，本頁只有統計結果。</p>"]
    H.append("<div class='box mid'><b>一句話（照登錄順序）</b><ol>" + "".join(f"<li>{x}</li>" for x in L1) + "</ol>"
             f"<p class='note'>比較對象一律是 S&P 500 含息指數（^SP500TR）同一段；「合格」＝年化比它高、而且年化÷最大回落也不比它差；「另列」＝只有年化比它高。"
             f"確認段 2022-01～2026-09 是挑選時沒看過的資料。正2（SSO、QLD）每天重設 2 倍，長期報酬不等於 2 倍、盤整會耗損，大跌時回落很深。</p></div>")
    # 件一
    H.append("<h2>件一　SPY／QQQ＋正2（SSO／QLD）＋國庫券：怎麼配、什麼時候換</h2>")
    H.append("<p>做法：探索段（2007-04～2021-12，含 2008 金融海嘯與 2020）把每一種比例、每一種換法都跑一次，挑出年化贏 S&P 500 的格裡「年化÷回落」最高的一格，"
             "再拿到沒看過的 2022-01～2026-09 檢查。現金放 3 個月國庫券（年 0～5%）。成本：換手金額 × 0.05%。</p>")
    rows = [["問一 比例（探索段挑中）", c1["格"], p(c1.get("年化")), p(c1.get("回落")), f"{c1.get('比值', float('nan')):.3f}" if "比值" in c1 else "—", c1["標籤"]],
            ["問二 轉換（探索段挑中）", c2["格"], p(c2.get("年化")), p(c2.get("回落")), f"{c2.get('比值', float('nan')):.3f}" if "比值" in c2 else "—", c2["標籤"]],
            ["S&P 500 含息（基準）", "—", p(Bc["年化"]), p(Bc["回落"]), f"{Bc['比值']:.3f}", "—"]]
    for a in ("SPY", "QQQ", "SSO", "QLD"):
        h = S1["並列一直抱"]["確認"][a]; rows.append([f"一直抱 {a}", "—", p(h["年化"]), p(h["回落"]), f"{h['比值']:.3f}", "（並列）"])
    H.append("<h3>確認段 2022-01-03～2026-09-30</h3>" + tbl(["", "格", "年化", "最大回落", "年化÷|回落|", "判準"], rows, left=2))
    H.append(f"<p class='note'>問一 池 {S1['問一']['池']} 格（年化贏 S&P 500 的 {S1['問一']['年化>基準']} 格）；問二 池 {S1['問二']['池']} 格（{S1['問二']['年化>基準']} 格）。"
             f"問二確認段每年換約 {c2.get('每年轉換', float('nan')):.1f} 次；2026-09-30 窗尾仍持有正2：{'是' if c2.get('窗尾持有正2') else '否'}。"
             f"假訊號：隨便挑一種比例在確認段合格 {p(S1['假訊號_問一']['p_合格'], 1, False)}（≥ 5% ⇒ ⚠）；隨便換日子合格 {p(S1.get('假訊號_問二', {}).get('p_合格', np.nan), 1, False)}。</p>")
    rows = [[r["年"], r["對象"], p(r["年內最大回落"]), f"{r['期末（萬）']:.1f} 萬", f"{r['谷底剩（萬）']:.1f} 萬", r["谷底日"]] for r in S1["必報_2008_2022"]]
    H.append("<h3>必報：2008、2022 那一年（100 萬放進去）</h3>" + tbl(["年", "對象", "年內最大跌幅", "年底剩", "最低剩", "谷底日"], rows, left=2))
    D1 = pd.read_csv(os.path.join(OUT, "A1_desc.csv"))
    rows = [[r["段"], r["格"], r["臂"], p(r["年化"]), p(r["回落"]), r["標籤（描述）"]] for _, r in D1.iterrows()]
    H.append("<h3>描述（⛔ 不改判定）：現金 0%、每季／每月再平衡、成本、股息扣 30%、固定天數</h3>" + tbl(["段", "格", "變化", "年化", "回落", "對基準"], rows, left=3))
    rows = [[r["格"], r["利差"], f"{r['起']}～{r['迄']}", p(r["年化"]), p(r["回落"]), p(r.get("^SP500TR 年化")), r.get("標籤（描述）", "—")] for r in S1["早年合成段（描述）"]]
    H.append("<h3>早年合成段（描述；合成、非實際 ETF）</h3>" + tbl(["格", "融資利差", "期間", "年化", "回落", "S&P 500 年化", "對基準"], rows, left=3))
    H.append(f"<p class='note'>{S1['先驗']}。QLD 追蹤 Nasdaq-100（科技集中），每日 2 倍重設，大跌時回落比 SSO 深。QQQ 上市前（1999-03）沒有 Nasdaq-100 總報酬 ⇒ 含 QQQ／QLD 的格早年段只從 1999-04 起。</p>")
    # 件二
    H.append("<h2>件二　擇時三件：每月看一次的慢規則能不能比一直抱正2 多賺</h2>")
    H.append("<p>甲 月底看 SPY 在不在長均線上；乙 依波動調整正2 比例；丙 SPY 從一年高點跌 x% 就全換國庫券、條件回來再買。每件在探索段挑年化最高的一格，"
             "看確認段（2022～2026）和早年合成段（合成正2）兩段是不是都比一直抱正2 多賺：兩段都多賺＝穩、只一段＝不穩、都沒有＝沒多賺。</p>")
    rows = []
    for f, j in jd.items():
        if "格" not in j:
            rows.append([f, "—", j.get("判定"), "", "", "", "", ""]); continue
        rows.append([f"{f} {CELLNAME[f]}", a2_plain(f, j["格"]), f"<b>{j['讀法']}</b>",
                     f"{p(j['確認']['年化'])}／{p(j['確認']['回落'])}（{j['確認']['對基準判準']}）", f"{p(j['一直抱正2']['確認']['年化'])}／{p(j['一直抱正2']['確認']['回落'])}",
                     f"{j['早年']['起']}～ {p(j['早年']['年化'])}／{p(j['早年']['回落'])}", f"{p(j['一直抱正2']['早年']['年化'])}／{p(j['一直抱正2']['早年']['回落'])}",
                     f"{j['早年最慘']['100萬在高點_谷底剩（萬）']:.1f} 萬"])
    H.append(tbl(["件", "挑中的規則", "讀法", "確認段 年化／回落（對 S&P 500）", "一直抱正2 確認段", "早年合成段", "一直抱合成正2 早年", "早年最慘（100 萬在高點）"], rows, left=3))
    fk = S2["假訊號"]
    H.append("<p class='note'>假訊號（同換手次數、隨機換手日 1,000 次；p ＝ 隨機年化 ≥ 本格的比例，≥ 0.05 ⇒「隨機換也做得到」）：" +
             "；".join(f"{f} 確認 p＝{v['確認']['p（隨機 ≥ 本格）']:.3f}、早年 p＝{v['早年']['p（隨機 ≥ 本格）']:.3f}" for f, v in fk.items()) +
             f"。格數 甲 16、乙 24、丙 36；退化不進挑選：{('、'.join(S2['退化格']) or '無')}。⚠ 三件挑中的都是 QLD 版 ⇒ 早年段只能從 {S2['窗']['早年（QLD，部分段）'][0]} 起（含 2000～2002 科技泡沫）。</p>")
    # 件三
    H.append("<h2>件三　大盤驅動因素：某件事發生後 20 天 SPY 比平常好或差？</h2>")
    rows = []
    for _, r in C3.iterrows():
        rows.append([f"{r['名稱']}｜{r['端']}" + ("" if r["版"] == "主" else f"（{r['版']}）"), int(r["n"]), int(r["n_eff"]), r["出口"], r["結果"],
                     p(r.get("D"), 2), f"[{p(r.get('Bonf下'), 2)}, {p(r.get('Bonf上'), 2)}]", r["候選"]])
    H.append(tbl(["因素｜端", "事件", "n_eff", "出口", "結果", "差（20 日）", "Bonferroni 區間", "候選"], rows))
    H.append(f"<p class='note'>主窗 {S3['主窗'][0]}～{S3['主窗'][1]}；門檻＝過去 756 個觀測日的 5％／95％；同端 20 日內只取第一筆；Bonferroni 0.05／8。"
             "美元指數（DTWEXBGS）聯準會每週一才公布上週每日值 ⇒ 主讀法從公布後才起算（「隔天就起算」會偷看最多一週，只描述）。事件 &lt; 30 個獨立區段 ⇒ 出口①（樣本不足以分辨，不算數）。</p>")
    # 件四
    H.append("<h2>件四　高點／低點反轉訊號：大盤（SPY）＋個股（S&P 500＋400）</h2>")
    M4 = C4[(C4["段"] == "主窗") & (C4["H"].isin([5, 10, 20, 60]))]
    rows = []
    for code in M4["code"].unique():
        g = M4[M4["code"] == code]; nm = g["名"].iloc[0]
        cell = []
        for lay in ("大盤", "個股"):
            for ver in ("原版", "確認版"):
                x = g[(g["層"] == lay) & (g["版"] == ver)].set_index("H")
                cell.append(" ".join(f"{H}{'✓' if x.at[H, '判定'] == '通過' else ('✗' if x.at[H, '判定'] == '不通過' else '·')}" for H in (5, 10, 20, 60) if H in x.index))
        rows.append([nm, g["邊"].iloc[0] + "點"] + cell)
    H.append(tbl(["訊號", "邊", "大盤 原版", "大盤 加確認", "個股 原版", "個股 加確認"], rows, left=2))
    P4 = C4[(C4["判定"] == "通過")]
    if len(P4):
        rows = [[r["層"], r["名"], r["版"], r["H"], int(r["事件"]), int(r["n_eff"]), p(r["成功率"], 1, False), p(r["基準成功率"], 1, False), p(r["mean"], 2),
                 f"[{p(r['lo'], 2)}, {p(r['hi'], 2)}]", r.get("扣成本後", "")] for _, r in P4.iterrows()]
        H.append("<h3>通過的格</h3>" + tbl(["層", "訊號", "版", "天數", "事件", "n_eff", "成功率", "基準成功率", "差", "Bonferroni 區間", "扣 0.05% 後"], rows, left=3))
    bf = S4["Bonferroni"]
    H.append(f"<p class='note'>✓ 通過、✗ 不通過、· 事件太少不可判定。大盤層 {S4['大盤窗']['主窗'][0]}～{S4['大盤窗']['主窗'][1]}，對照＝同窗所有交易日；個股層 {S4['個股']['窗'][0]}～{S4['個股']['窗'][1]}"
             f"（資料庫面板 2015-12 起），對照＝同月、前 20 日漲跌同十分位的股票。Bonferroni k：大盤 {bf['大盤']['k']}、個股 {bf['個股']['k']} ⇒ N_前段 ＋{S4['N_前段（照可判定格數實計）']}。"
             f"21 種訊號（登錄寫 24 種；頭肩頂、2B 頂、2B 底 本專案沒有機器定義 ⇒ 不收，同台股）。{S4['母體限制']}。120、240 日只描述。</p>")
    # 件五
    H.append("<h2>件五　三態輪動：趨勢向上抱正2、轉弱換 SPY／QQQ／國庫券、跌深買 SPY／QQQ、反彈換回正2</h2>")
    rows = [["挑法乙（年化最高，判定用）", pb["白話"], f"{p(pb['探索']['年化'])}／{p(pb['探索']['回落'])}", f"{p(pb['確認']['年化'])}／{p(pb['確認']['回落'])}", f"{pb['確認']['每年轉換']:.1f}", pb["判定"] + "；" + pb["使用者判準"]]]
    if S5.get("挑法甲"):
        pa = S5["挑法甲"]
        rows.append(["挑法甲（使用者判準，並列）", pa["白話"], f"{p(pa['探索']['年化'])}／{p(pa['探索']['回落'])}", f"{p(pa['確認']['年化'])}／{p(pa['確認']['回落'])}", f"{pa['確認']['每年轉換']:.1f}", pa["確認"]["使用者判準"]])
    ph = S5["純抱"]
    for a in ("SSO", "QLD", "SPY", "QQQ"):
        rows.append([f"一直抱 {a}", "—", f"{p(ph[a]['探索']['年化'])}／{p(ph[a]['探索']['回落'])}", f"{p(ph[a]['確認']['年化'])}／{p(ph[a]['確認']['回落'])}", "0", "（並列）"])
    rows.append(["S&P 500 含息（基準）", "—", f"{p(S5['基準']['探索']['年化'])}／{p(S5['基準']['探索']['回落'])}", f"{p(S5['基準']['確認']['年化'])}／{p(S5['基準']['確認']['回落'])}", "—", "—"])
    H.append(tbl(["", "規則", "探索 年化／回落", "確認 年化／回落", "每年轉換", "判定"], rows, left=2))
    rows = [[x["期間"], x["對象"], f"{x['起']}～{x['迄']}", p(x.get("年化")), p(x["年內最大回落"]), f"{x['谷底剩（萬）']:.1f} 萬", f"{x['期末（萬）']:.1f} 萬"] for x in S5["壓力"]]
    H.append("<h3>壓力段（100 萬放進去）</h3>" + tbl(["期間", "對象", "起訖", "年化", "最大跌幅", "最低剩", "期末"], rows, left=3))
    rows = [[x["版"], x["格"], f"{p(x['探索年化'])}／{p(x['探索回落'])}", f"{p(x['確認年化'])}／{p(x['確認回落'])}", x["確認判準"]] for x in S5["12版各自探索第一名（描述）"]]
    H.append("<h3>12 版各自探索段第一名（描述，⛔ 不判）</h3>" + tbl(["A／B／C 態持有", "轉弱｜跌深｜反彈", "探索", "確認", "確認判準"], rows, left=2))
    H.append(f"<p class='note'>狀態機從 {S5['狀態機起跑']} 起跑（SPY 上市前用 S&P 500 含息指數代）；第二層（件三）0 個、第三層（件四大盤層）0 個可加 ⇒ 只跑第一層：轉弱 {len(S5['訊號']['轉弱'])} × 跌深 {len(S5['訊號']['跌深'])} × 反彈 {len(S5['訊號']['反彈'])} × 12 版 ＝ {S5['從x種挑出']:,}。"
             f"「站回 20 日線」與「站回布林中軌」是同一個訊號（U1≡U7：{S5['訊號']['U1≡U7']}），照字面都算。假訊號（確認段同轉換次數、隨機日 1,000 次）：年化贏 S&P 500 {p(S5['假訊號']['p_年化贏基準'], 1, False)}、合格 {p(S5['假訊號']['使用者判準合格比例'], 1, False)}。"
             f"2026-09-30 窗尾狀態 {S5['窗尾狀態（2026-09-30）']} 態。</p>")
    # 資料與限制
    H.append("<h2>資料、讀法與限制</h2><ul>")
    for r in rmain:
        H.append(f"<li>合成 {r['正2']} 對帳（2007-04～2021-12，同一公式套真實期間）：合成年化 {p(r['合成年化'], 2)} vs 真實 {p(r['真實年化'], 2)}，差 {r['年化差（點）']:+.2f} 點、追蹤誤差 {p(r['追蹤誤差（年化）'], 2, False)}"
                 + ("；⚠ 超過 1 點" if r["超過1點"] else "；未超過 1 點") + ("、⚠ 超過費用率" if r["超過費用率"] else "、未超過費用率") + "。</li>")
    H.append("<li>早年合成 2 倍：每天 2×指數報酬 −（國庫券＋0.25%）− 費用率（SSO 0.89%、QLD 0.95%）；QLD 用 QQQ 含息價（QQQ 本身另有 0.20% 費用 ⇒ 合成 QLD 略被多扣）。融資利差 0／0.50% 結果另列在 A1、A2 描述。</li>"
             "<li>現金 ＝ 3 個月國庫券（偏離台股 0%，已核准）；0% 版只描述。年化用 252 個交易日。</li>"
             "<li>執行者補的讀法與偏離寫死在程式開頭（researchUSA1*.py 的 D1～D8、P1～P15、Y1～Y6、R1～R6），都在看任何 A1 數字之前寫好。</li></ul>")
    if CK:
        H.append(f"<p class='note'>獨立查核（researchUSA1_check.py，不 import 主程式）：{'全部通過' if CK.get('全部通過') else '⛔ 有不同'}；"
                 + "；".join(f"{k} {v}" for k, v in CK.items() if k[0] in "①②③④⑤⑥⑦⑧") + "</p>")
    H.append("</body></html>")
    open(os.path.join(OUT, "美股大盤ETF五件.html"), "w", encoding="utf-8").write("\n".join(H))
    # ═══ REPORT.md ═══
    R = ["# USREG-A1-1～5 交件：美股大盤／ETF 五件（美股帳）", "",
         f"回測線｜{now}（台北）｜資料 us-stock-data `{AUD['資料commit']}`（快照 ~/usdata/60d2f99）｜登錄 seq1 4d6b82a0d0fe84c3、seq2 cea9cc6132c26f2f、seq3 2f26cfea3035d3a7｜裁定 seq308 §三§四、309、311 §二、313 §二", "",
         "⚠ 想法來自台股（多數在台股不合格）。私有原始資料只在 ~/us_work/usa1/（repo 外，sha 在各 summary）；本資料夾只有彙總。", "", "## 〇、結論", ""]
    R += [f"{i + 1}. " + x.replace("<b>", "**").replace("</b>", "**") for i, x in enumerate(L1)]
    R += ["", "## 一、N（美股帳）", ""] + mdt(["件", "N", "說明"], [["A1-1", "N_組合 ＋2", "問一、問二確認段各 1 格"], ["A1-2", "N_組合 ＋3", "甲乙丙各 1 格"],
                                                                   ["A1-3", "N_前段 ＋8", "8 格全可判定性照實：出口① " + str(int((C3[C3['版'] == '主']['出口'] == '出口①').sum())) + " 格"],
                                                                   ["A1-4", f"N_前段 ＋{S4['N_前段（照可判定格數實計）']}", f"大盤 k {S4['Bonferroni']['大盤']['k']}＋個股 k {S4['Bonferroni']['個股']['k']}（訊號×版本×視窗{{5,10,20,60}} 可判定格）"],
                                                                   ["A1-5", "N_組合 ＋1", f"從 {S5['從x種挑出']:,} 種挑出"]])
    R += ["", "## 二、偏離與執行者補讀法（全部看數字前寫死）", "",
          "- 現金 3 個月國庫券（偏離台股 0%，seq309 已核准）；判準基準 ^SP500TR、並列一直抱 SPY／SSO（另列 QQQ、QLD）",
          "- A1-4 訊號 21 種（登錄字面 24）：頭肩頂、2B 頂、2B 底無機器定義 ⇒ 不收（同台股 seq226）",
          "- A1-4 個股層窗 2016-01-04～2026-09-30（面板 2015-12 起；大盤層 2007-04～）；扣成本版移 0.05%（美股來回；台股 0.585%）",
          "- A1-3 #6 DTWEXBGS：H.10 每週一公布上週值 ⇒ 主讀法公布後次一交易日起算；次一日版只描述（前視）",
          "- 早年合成段：資料 1990-01-02 起、暖身後 SPY／SSO 格 E0 ＝ " + S1["早年段"]["E0（SPY／SSO）"] + "（A1-1）、" + S2["窗"]["早年（SPY／SSO）"][0] + "（A1-2）；含 QQQ／QLD 的格只從 1999 起（部分段）；1993-01-29 前的 SPY 用 ^SP500TR 比例接（未扣 SPY 費用）",
          "- 早年段全段用合成（含 2006-06～2007-03 已有真實 SSO／QLD）；合成開盤 ＝ 前收 ×(1＋2×隔夜漲跌)",
          "- 年化 ANN 252；A1-2 乙 σ̂ 年化 √252；條件出場主臂 ＝ 規則本身；固定 {20,60,120,240} 日只描述（進風險部位抱滿 H 日、到期退出、等下一次由不成立變成立才再進）",
          "- A1-5 第二、三層訊號在自己可算前一律不成立（不延後起跑）；本次兩層都 0 個", "",
          "## 三、合成 2 倍對帳（seq3；⛔ 不判）", ""]
    R += mdt(["正2", "利差", "合成年化", "真實年化", "差（點）", "追蹤誤差", "相關", "＞1 點", "＞費用率"],
             [[r["正2"], f"{r['利差']:.2%}", p(r["合成年化"], 2), p(r["真實年化"], 2), f"{r['年化差（點）']:+.2f}", p(r["追蹤誤差（年化）"], 2, False), f"{r['日報酬相關']:.4f}", r["超過1點"], r["超過費用率"]] for r in REC["結果"]])
    R += ["", "## 四、各件要點", "", "### A1-1", ""]
    R += [f"- 確認段 基準 {p(Bc['年化'], 2)}／{p(Bc['回落'], 2)}｜問一 {c1['格']} ⇒ {p(c1.get('年化'), 2)}／{p(c1.get('回落'), 2)}【{c1['標籤']}】｜問二 {c2['格']} ⇒ {p(c2.get('年化'), 2)}／{p(c2.get('回落'), 2)}【{c2['標籤']}】，窗尾仍持有正2 {c2.get('窗尾持有正2')}",
          f"- 探索段 基準 {p(Be['年化'], 2)}／{p(Be['回落'], 2)}｜問一挑中探索 {p(S1['問一'].get('挑中', {}).get('年化'), 2)}｜問二挑中探索 {p(S1['問二'].get('挑中', {}).get('年化'), 2)}",
          f"- 假訊號 問一 p_合格 {S1['假訊號_問一']['p_合格']:.3f}、問二 p_合格 {S1.get('假訊號_問二', {}).get('p_合格')}",
          f"- 先驗（受污染照標）：{S1['先驗']}", "", "### A1-2", ""]
    for f, j in jd.items():
        if "格" in j:
            R.append(f"- {f} {j['格']}：{j['讀法']}｜確認 {p(j['確認']['年化'], 2)}／{p(j['確認']['回落'], 2)}（一直抱 {j['正2']} {p(j['一直抱正2']['確認']['年化'], 2)}；對 ^SP500TR {j['確認']['對基準判準']}）｜"
                     f"早年 {j['早年']['起']}～ {p(j['早年']['年化'], 2)}（一直抱合成 {p(j['一直抱正2']['早年']['年化'], 2)}）｜假訊號 p 確認 {fk[f]['確認']['p（隨機 ≥ 本格）']:.3f}、早年 {fk[f]['早年']['p（隨機 ≥ 本格）']:.3f}")
    R += ["", "### A1-3", "", f"- 候選：{S3['候選']}；出口 {S3['出口計數']}；結果 {S3['結果計數']}", "", "### A1-4", "",
          f"- 通過 大盤 {S4['通過_大盤'] or '無'}；個股 {S4['通過_個股'] or '無'}；第三層給 A1-5：{S4['第三層（給 A1-5）'] or '無'}", f"- {S4['母體限制']}", "", "### A1-5", "",
          f"- 挑法乙 {pb['格']}：{pb['白話']}｜探索 {p(pb['探索']['年化'], 2)}｜確認 {p(pb['確認']['年化'], 2)}／{p(pb['確認']['回落'], 2)} ⇒ {pb['判定']}；{pb['使用者判準']}；從 {S5['從x種挑出']:,} 種挑出",
          f"- 假訊號 {S5['假訊號']}｜窗尾狀態 {S5['窗尾狀態（2026-09-30）']}", "", "## 五、查核", "",
          f"- researchUSA1_check.py（獨立路）：{'全部通過' if CK.get('全部通過') else CK.get('不同')}", "",
          "## 六、檔案", "", "- 程式：backtest/researchUSA1.py（A1-1、2、5＋主程式）、researchUSA1_data.py、researchUSA1_drv.py（A1-3）、researchUSA1_rev.py（A1-4）、researchUSA1_check.py、researchUSA1_page.py",
          "- 結果：resultsUSA1/A0～A5_*.json／csv、check.json、data_audit.json、REPORT.md、美股大盤ETF五件.html", "- 私有（repo 外）：~/us_work/usa1/（事件逐筆、權益、狀態路徑）", "",
          "⛔ 未 commit、未 push、未派 workflow"]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(R) + "\n")
    print("寫出 REPORT.md、美股大盤ETF五件.html")


if __name__ == "__main__":
    main()
