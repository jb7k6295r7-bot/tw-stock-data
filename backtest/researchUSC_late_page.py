# -*- coding: utf-8 -*-
"""USREG-C 批後四件網頁：讀 resultsUSC/late/*.json ⇒「美股自選研究C批後四件.html」（繁體中文、白話、結論先講；只放彙總）。

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSC_late_page
"""
from __future__ import annotations

import html
import json
import os

OUT = os.path.expanduser("~/tw-p17/backtest/resultsUSC/late")


def J(n):
    return json.load(open(os.path.join(OUT, n), encoding="utf-8"))


def pc(x, d=1, sign=False):
    if x is None:
        return "—"
    return (f"{x * 100:+.{d}f}%" if sign else f"{x * 100:.{d}f}%")


def wan(x):
    return "—" if x is None else (f"{x:.1f} 萬" if x >= 1 else f"{x * 10000:,.0f} 元")


def yr(x):
    return x if isinstance(x, str) else f"{x:.1f} 年"


def tb(head, rows, cls=""):
    h = "".join(f"<th>{html.escape(str(c))}</th>" for c in head)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="tw"><table class="{cls}"><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'


def tag(lab):
    k = "ok" if lab.startswith("合格") else ("mid" if lab.startswith(("另列", "看段")) else ("no" if lab.startswith("不合格") else "na"))
    return f'<span class="tag {k}">{html.escape(lab)}</span>'


def main():
    A = J("C11_summary.json"); B = J("C12_summary.json"); C = J("C9_summary.json"); D = J("C2_summary.json"); K = J("check.json")
    # ── C11
    cj = A["對照"]["判定格 50% SSO＋30% IEF＋20% GLD（每年）"]
    se_key = [k for k in A["對照"] if k.startswith("同曝險對照：")][0]; se = A["對照"][se_key]
    c11_sent = (f"一半 SSO、三成中期公債、兩成黃金（每年調一次）：年化 {pc(A['判定']['年化'])}（^SP500TR {pc(A['基準']['年化'])}）、回落 {pc(A['判定']['回落'])}；"
                f"2008 最低剩 {wan(cj['危機']['2008']['窗內最低剩（萬）'])}、2022 最低剩 {wan(cj['危機']['2022']['窗內最低剩（萬）'])}")
    debt = A["債在2022"]
    debt_txt = ("有擋" if debt["判定格 2022 最低剩"] > debt["同曝險 SSO＋國庫券 2022 最低剩"] else "幫倒忙")
    rows11 = []
    for k, v in A["對照"].items():
        cr = v.get("危機", {})
        rows11.append([html.escape(k), pc(v["年化"]), pc(v["回落"]), f"{v['比值']:.2f}" if v.get("比值") is not None else "—", tag(v["標籤"]) if v.get("標籤") else "—",
                       wan(cr["2008"]["窗內最低剩（萬）"]) if "2008" in cr else "—", wan(cr["2020"]["窗內最低剩（萬）"]) if "2020" in cr else "—",
                       wan(cr["2022"]["窗內最低剩（萬）"]) if "2022" in cr else "—", yr(cr["2022"]["回本年數（從窗首）"]) if "2022" in cr else "—"])
    gv = A["黃金與股票債券_危機"]
    # ── C12
    seg_names = list(B["段"].keys())
    rows12 = []
    for s in seg_names:
        v = B["段"][s]
        for k in ("1 倍×主規則", "1 倍×單用月線", "1 倍×Sahm版", "1 倍×修正後失業率", "1 倍×一直抱", "2 倍×主規則", "2 倍×單用月線", "2 倍×一直抱"):
            x = v[k]
            rows12.append([s.split("（")[0], k + ("（判定）" if k.endswith("主規則") else "（描述）"), pc(x["年化"]), pc(x["回落"]), tag(x["標籤"]),
                           str(x.get("換手次數（狀態改變）", "—")), "是" if x.get("持有", {}).get("段尾仍持有") else ("—" if "持有" not in x else "否"),
                           pc(v["基準"]["年化"]) + "／" + pc(v["基準"]["回落"])])
    ex = B["逐筆出場彙總"]
    cr12 = [[r["大跌"], r["窗"], pc(r["^SP500TR 同期"]), pc(r["1 倍×主規則 同期"]), pc(r["1 倍×主規則 躲了幾成"], 0) if r["1 倍×主規則 躲了幾成"] is not None else "—",
             pc(r["1 倍×單用月線 躲了幾成"], 0), pc(r["2 倍×主規則 同期"]), pc(r["2 倍×一直抱 同期"])] for r in B["四次大跌"]]
    sh = [[r["月底"], r["最新已公布月"], "是" if r["M（站上10月線）"] else "否", "是" if r["E（失業率低於12月平均）"] else "否", "是" if r["Sahm觸發"] else "否",
           "持有" if r["主規則持有"] else "出場", "持有" if r["Sahm版持有"] else "出場"] for r in B["2024Sahm假警報"]]
    rev = B["先驗對照"]["修正後失業率高估年化（1 倍，逐段：修正後 − 首次公布）"]
    # ── C9
    rows9 = []
    for k, v in C["格"].items():
        nm, sg = k.split("｜")
        rows9.append([nm, sg, pc(v["年化"]), pc(v["回落"]), tag(v["標籤"]), wan(v["100萬最低剩（萬）"]), yr(v["回本年數"]),
                      f"{v['每年換手']:.1f}" if v["每年換手"] else "0", pc(v["同規則2倍"]["年化"]) + "／" + pc(v["同規則2倍"]["回落"]), pc(v["基準年化"])])
    cr9 = []
    for p in ("UPRO", "TQQQ"):
        for k, v in C["大跌"][p].items():
            if k.startswith("^"):
                continue
            x3 = v["3倍"]; x2 = v.get("2倍")
            cr9.append([p, html.escape(k), wan(x3["窗內最低剩（萬）"]), yr(x3["回本年數（從窗首）"]), wan(x2["窗內最低剩（萬）"]) if x2 else "—", yr(x2["回本年數（從窗首）"]) if x2 else "—"])
        for cn, x in C["大跌"][p]["^SP500TR 同窗"].items():
            cr9.append([p, f"^SP500TR｜{cn}", wan(x["窗內最低剩（萬）"]), yr(x["回本年數（從窗首）"]), "—", "—"])
    up = C["大跌"]["UPRO"]; tq = C["大跌"]["TQQQ"]
    c9H = (f"一直抱 UPRO：2000～2002（合成）100 萬最低剩 {wan(up['H｜2000～2002（合成連續路徑）']['3倍']['窗內最低剩（萬）'])}、回本 {yr(up['H｜2000～2002（合成連續路徑）']['3倍']['回本年數（從窗首）'])}；"
           f"2022 年（真實）最低剩 {wan(up['H｜2022（真實 UPRO）']['3倍']['窗內最低剩（萬）'])}｜一直抱 TQQQ：2000～2002（合成）最低剩 {wan(tq['H｜2000～2002（合成連續路徑）']['3倍']['窗內最低剩（萬）'])}、"
           f"{yr(tq['H｜2000～2002（合成連續路徑）']['3倍']['回本年數（從窗首）'])}；2022 年（真實）最低剩 {wan(tq['H｜2022（真實 TQQQ）']['3倍']['窗內最低剩（萬）'])}")
    rec = [[k, f"{v['窗'][0]}～{v['窗'][1]}", pc(v["真實年化"]), pc(v["合成年化"]), pc(v["年化差（合成−真實）"], 2, True), f"{v['日報酬相關']:.4f}"] for k, v in C["對帳"].items()]
    # ── C2
    v20 = {c: D["甲"][f"{c}｜合併｜H20｜對照同十分位"] for c in "ABCD"}
    TXT = {"A": "任何董事或高階主管買進", "B": "機會型買進", "C": "多人一起買（30 天內 ≥3 人）", "D": "執行長或財務長買進"}
    rows2 = []
    for c in "ABCD":
        for col in ("合併", "只400", "只500"):
            s = D["甲"][f"{c}｜{col}｜H20｜對照同十分位"]
            rows2.append([f"{c} {TXT[c]}", col + ("（判定）" if col == "合併" else "（描述）"), str(s["n"]), str(s["n_eff"]), pc(s["平均"], 2, True),
                          f"{pc(s['lo'], 2, True)}～{pc(s['hi'], 2, True)}", f"{pc(s['lo_Bonf'], 2, True)}～{pc(s['hi_Bonf'], 2, True)}", html.escape(s["判"])])
    hz = []
    for c in "ABCD":
        hz.append([f"{c}"] + [pc(D["甲"][f"{c}｜合併｜H{H}｜對照同十分位"]["平均"], 2, True) + f"（{D['甲'][f'{c}｜合併｜H{H}｜對照同十分位']['判'][:3]}）" for H in (20, 60, 120, 240)])
    pre = [[c, str(v["n"]), pc(v["中位"], 1, True), pc(v["p10"], 1, True), pc(v["落在最低十分位比例"], 0), pc(v["落在最低三個十分位比例"], 0)] for c, v in D["前20日報酬分佈"].items()]
    pl = [[c, pc(v["真平均"], 2, True), pc(v["假訊號平均的中位"], 2, True), pc(v["p（假訊號 ≥ 真）"], 1)] for c, v in D["甲假訊號"].items()]
    Y = D["乙"]
    rowsP = []
    for k, v in Y["主"].items():
        rowsP.append([k.replace("｜主", ""), pc(v["年化中位"]), pc(v["回落中位"]), f"{v['比值']:.2f}", tag(v["標籤"]), f"{v['持有天數_中位（逐種子中位）']:.0f}",
                      f"{v['持有天數_p10']:.0f}～{v['持有天數_p90']:.0f}", f"{v['最長持有（200 顆最大）']:.0f}", f"{v['窗尾仍持有件數（逐種子中位）']:.0f}（{v['窗尾仍持有件數（範圍）'][0]}～{v['窗尾仍持有件數（範圍）'][1]}）"])
    fx = [[k.replace("｜合併｜", " "), pc(v["年化中位"]), pc(v["回落中位"]), tag(v["標籤"])] for k, v in Y["固定天數（描述）"].items()]
    rsn = [[k, pc(v.get("機會型賣出", 0), 0), pc(v.get("12個月無新買進且跌破200日線", 0), 0), pc(v.get("窗尾", 0), 0), str(v["訊號筆數"])] for k, v in Y["出場原因（訊號層）"].items()]
    pl2 = Y["假訊號"]
    must = D["必報"]
    yrows = [[r["年（事件日）"], str(r["A 去重後事件"]), str(r["B 去重後事件"]), str(r["C 去重後事件"]), str(r["D 去重後事件"]), pc(r["機會型比例"], 0), pc(r["例行型比例"], 0),
              pc(r["不分類型比例"], 0), f"{r['中位買進金額（美元）']:,.0f}"] for r in must["每年"]]
    rvo = D["例行vs機會（A 內，合併 H20）"]
    ck = K
    css = """
:root{--bg:#fbfaf7;--fg:#1d1d1f;--mut:#5f6368;--line:#e3e0d8;--card:#ffffff;--ok:#1f7a3a;--okb:#e5f4e9;--mid:#8a5a00;--midb:#fbf0d9;--no:#a8261d;--nob:#fbe6e3;--acc:#2b5cab}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#16171a;--fg:#ececec;--mut:#a8abb2;--line:#33363c;--card:#1e2024;--ok:#7fd49a;--okb:#1d3325;--mid:#f0c26b;--midb:#3a2f17;--no:#ff978b;--nob:#3d1f1c;--acc:#8fb3ff}}
:root[data-theme="dark"]{--bg:#16171a;--fg:#ececec;--mut:#a8abb2;--line:#33363c;--card:#1e2024;--ok:#7fd49a;--okb:#1d3325;--mid:#f0c26b;--midb:#3a2f17;--no:#ff978b;--nob:#3d1f1c;--acc:#8fb3ff}
body{background:var(--bg);color:var(--fg);font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif;margin:0;line-height:1.65}
main{max-width:1020px;margin:0 auto;padding:20px 16px 60px}
h1{font-size:1.5rem;margin:.2em 0}h2{font-size:1.2rem;margin-top:2em;border-bottom:2px solid var(--line);padding-bottom:.2em}h3{font-size:1.02rem;margin-top:1.4em}
.sub{color:var(--mut);font-size:.88rem}.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin:12px 0}
.tw{overflow-x:auto;margin:8px 0}table{border-collapse:collapse;font-size:.84rem;min-width:100%}th,td{border-bottom:1px solid var(--line);padding:5px 8px;text-align:left;vertical-align:top;white-space:nowrap}
th{color:var(--mut);font-weight:600}.tag{display:inline-block;border-radius:6px;padding:0 6px;font-size:.82rem;white-space:normal}
.ok{background:var(--okb);color:var(--ok)}.mid{background:var(--midb);color:var(--mid)}.no{background:var(--nob);color:var(--no)}.na{color:var(--mut)}
.big{font-size:1.02rem}li{margin:.25em 0}code{font-size:.85em}
"""
    body = f"""
<main>
<h1>美股自選研究 C 批後四件</h1>
<p class="sub">回測線｜台北 2026-10-11｜C11 股債金、C12 月線＋失業率、C9 三倍 ETF、C2 內部人買進｜裁定 seq321 §三發號｜美股帳 N：C2 6、C9 4、C12 2、C11 1（共 13）｜⚠ 只放彙總，私有原始資料不在本頁</p>

<h2>先講結論</h2>
<div class="card big"><ul>
<li><b>C11 股債金（判定 1 格）</b>：{tag(A['標籤'])}。{c11_sent}。⚠ 債在 2022 是<b>{debt_txt}</b>（同曝險的「SSO＋國庫券」2022 最低剩 {wan(debt['同曝險 SSO＋國庫券 2022 最低剩'])}，比搭配版 {wan(debt['判定格 2022 最低剩'])} 好）；但同曝險對照全期只有 {pc(se['年化'])}／{pc(se['回落'])}，搭配版贏在 2008（債、金都有擋）⇒ 好處不全是降曝險。只有一個窗（2007-04～2026-09），沒有另一段可驗。</li>
<li><b>C12 月線＋失業率（判定 2 格）</b>：1 倍、2 倍都是 {tag(B['標籤']['1 倍×主規則'])}。只在 1990～2006、2007～2021 兩段有用；2022～2026-09 不合格（1 倍 {pc(B['段'][seg_names[2]]['1 倍×主規則']['年化'])}，大盤 {pc(B['段'][seg_names[2]]['基準']['年化'])}）。好處幾乎都來自 2008（躲掉 93%）與 2000～2002（躲掉 59%）；2020、2022 兩次一成都沒躲到。換手 {B['先驗對照']['換手次數 主規則 vs 單用月線'][0]} 次，單用月線 {B['先驗對照']['換手次數 主規則 vs 單用月線'][1]} 次（少一半以上）。</li>
<li><b>C9 三倍 ETF（判定 4 格）</b>：四格都是「看段」（三段標籤不一）。{c9H}。加 200 日線：UPRO 早年合成段合格、之後兩段另列；TQQQ 早年合成段不合格（2000～2002 仍剩 {wan(tq['M｜2000～2002（合成連續路徑）']['3倍']['窗內最低剩（萬）'])}）、之後兩段合格。⚠ 每年換手約 4～8.5 次，大跌第一段跌幅躲不掉。</li>
<li><b>C2 內部人買進</b>：事件層四格（任何、機會型、多人一起買、執行長／財務長）<b>全部測不出</b>：買進後 20 天，比同樣跌過、但沒有內部人買的股票只多 {pc(v20['A']['平均'], 2, True)}～{pc(v20['B']['平均'], 2, True)}，信賴區間都含 0。組合層兩格 {tag(Y['標籤（合併欄判定）']['B'])}{tag(Y['標籤（合併欄判定）']['C'])}：<b>隨機也做得到 {pc(pl2['B']['p（假訊號年化 ≥ 真）'], 0)}</b>——機會型年化 {pc(Y['主']['B｜合併｜主']['年化中位'])}；<b>隨機也做得到 {pc(pl2['C']['p（假訊號年化 ≥ 真）'], 0)}</b>——多人一起買 {pc(Y['主']['C｜合併｜主']['年化中位'])}（^SP500TR {pc(Y['判準']['年化'])}）。只 S&amp;P 500、只 S&amp;P 400 兩欄方向相同（沒有相反）。偏向存活股。</li>
</ul></div>
<p class="sub">標籤用使用者判準：年化贏 ^SP500TR 同窗、且「年化 ÷ |最大回落|」不比它差 ⇒ 合格；只有年化贏 ⇒ 另列；否則不合格。分段的件三段同一標籤才下該標籤，否則寫「看段」。</p>

<h2>C11　抱 2 倍 ETF 時搭配公債與黃金</h2>
<p>判定格：50% SSO＋30% IEF（7～10 年美債）＋20% GLD，每年第一個交易日調回；窗 {A['窗'][0]}～{A['窗'][1]}（SSO 上市後 200 日起）。平均總股票曝險 {A['平均總股票曝險']:.2f} 倍；等效獨立部位數 {A['等效獨立部位數（L5）']:.2f}。描述網格 {A['網格格數']} 格中 {A['網格年化>基準格數']} 格年化贏大盤、{A['網格合格格數（描述）']} 格合格（⛔ 不挑格、只判一格）。</p>
{tb(["組合", "年化", "最大回落", "比值", "標籤", "2008 最低剩", "2020 最低剩", "2022 最低剩", "2022 回本"], rows11)}
<p class="sub">危機窗：2008 ＝ 2007-10-01～2009-03-31｜2020 ＝ 2020-02-03～03-31｜2022 ＝ 全年；100 萬放在窗首前一交易日。HFEA 與「判定格（同 HFEA 窗）」從 UPRO 上市日 2009-06-25 起。</p>
<h3>單一資產在危機裡（100 萬最低剩）</h3>
{tb(["危機", "GLD 黃金", "SPY 股票", "IEF 中期債", "TLT 長債"], [[k, wan(v['GLD']['窗內最低剩（萬）']), wan(v['SPY']['窗內最低剩（萬）']), wan(v['IEF']['窗內最低剩（萬）']), wan(v['TLT']['窗內最低剩（萬）'])] for k, v in gv.items()])}
<p>股債金逐年相關係數見 <code>C11_corr_by_year.csv</code>。先驗對照：判定格標籤 {A['先驗對照']['判定格標籤']}（押另列或合格）；2022 IEF 版比 TLT 版跌得淺 {'是' if A['先驗對照']['2022 IEF 版跌幅比 TLT 版淺'] else '否'}；黃金 2008、2022 都比 SPY 少跌 {'是' if A['先驗對照']['黃金 2008、2022 都比 SPY 少跌'] else '否'}；同曝險對照搭配版比值較好 {'是' if A['先驗對照']['同曝險對照：搭配版比值較好'] else '否'}；HFEA 回落 ≥ 60% {'是' if A['先驗對照']['HFEA 最大回落 ≥ 60%'] else '否'}。</p>
<p class="sub">條件出場：本件是靜態配置、每年調回，沒有進出場訊號 ⇒ 全期持有、窗尾仍持有；固定天數不適用。</p>

<h2>C12　月線擇時加失業率濾網</h2>
<p>規則：月底 ^SP500TR 站上 10 個月均線（M），或最近一次【當時公布】的失業率低於最近 12 次平均（E），任一成立就持有，兩個都不成立才換國庫券；下個月第一個交易日開盤換。</p>
{tb(["段", "標的×規則", "年化", "最大回落", "標籤", "換手次數", "段尾仍持有", "^SP500TR 年化／回落"], rows12)}
<h3>出場與被洗（出場後指數又漲 ＝ 被洗）</h3>
{tb(["規則", "出場次數", "被洗", "段一", "段二", "段三"], [[k, str(v['出場次數']), str(v['被洗次數'])] + [f"{v['逐段'][s]['出場']} 次（洗 {v['逐段'][s]['被洗']}）" for s in seg_names] for k, v in ex.items()])}
<p class="sub">逐筆出場（出場日、回場日、期間指數漲跌）見 <code>C12_exits.csv</code>。</p>
<h3>四次大跌躲到幾成</h3>
{tb(["大跌", "窗", "^SP500TR", "1 倍主規則", "主規則躲了", "單用月線躲了", "2 倍主規則", "一直抱 2 倍"], cr12)}
<h3>2024 Sahm 假警報期間</h3>
{tb(["月底", "最新已公布月", "M 站上月線", "E 失業率在降", "Sahm 觸發", "主規則", "Sahm 版"], sh)}
<p>Sahm 在 2024-08～10 觸發，但股市一直站在月線上 ⇒ 主規則與 Sahm 版都照抱，沒有被假警報洗掉。用修正後失業率（偷看未來）的年化差（修正後 − 首次公布）：段一 {pc(rev[seg_names[0]], 2, True)}、段二 {pc(rev[seg_names[1]], 2, True)}、段三 {pc(rev[seg_names[2]], 2, True)} ⇒ 沒有一致高估。E 剛好相等的月份 {B['E 相等月份數']} 個（照字面算「不成立」）。</p>
<p class="sub">條件出場：主規則本身就是條件出場（⛔ 無最長天數）；三段末都仍持有。固定 20／60／120／240 日只描述（見 C12_summary.json）。</p>

<h2>C9　三倍 ETF（UPRO、TQQQ）長抱 vs 200 日線</h2>
<p>早年段用每日重設合成：3 × 指數日報酬 − 2 ×（國庫券＋0.25%）− 費用率（SEC 497K 淨費用率：UPRO {C['費用率（SEC 497K 淨／毛）']['UPRO']['淨'] * 100:.2f}%、TQQQ {C['費用率（SEC 497K 淨／毛）']['TQQQ']['淨'] * 100:.2f}%）；TQQQ 版 1999-03 之前沒有 Nasdaq-100 總報酬 ⇒ 不可判定、段從 200 日線可算後的 2000-01 起。</p>
{tb(["件", "段", "年化", "最大回落", "標籤", "100 萬最低剩", "回本", "每年換手", "同規則 2 倍 年化／回落", "^SP500TR 年化"], rows9)}
<h3>三次大跌（100 萬放在窗首）</h3>
{tb(["件", "臂｜大跌", "3 倍 最低剩", "3 倍 回本（從窗首）", "2 倍 最低剩", "2 倍 回本"], cr9)}
<p class="sub">大跌窗：2000-01-03～2002-12-31、2007-10-01～2009-03-31、2022 全年。早年用「合成一路接到 2026-09-30」的連續路徑量回本；2022 另用真實 ETF。</p>
<h3>合成 vs 真實對帳（上市日～2026-09-30）</h3>
{tb(["件", "窗", "真實年化", "合成年化", "差（合成−真實）", "日報酬相關"], rec)}
<p>先驗對照：TQQQ 一直抱早年段 100 萬最低剩不到 1 萬 {'是' if C['先驗對照']['TQQQ×H 早年段 100 萬最低剩 ＜ 1 萬'] else '否'}；「3 倍＋200 日線比 2 倍＋200 日線年化高、但回落深 10 點以上」：UPRO 三段皆是；TQQQ 早年段否、後兩段是。</p>
<p class="sub">條件出場：M 臂跌破 200 日線才出、站回才進（⛔ 無最長天數）；各段持有段天數分佈、段尾仍持有、錯過的反彈、假突破次數、100／150 日線、±3% 緩衝、波動目標 V（描述）見 C9_summary.json。A1-1 問二（2 倍＋200 日線，已看過）只並列。</p>

<h2>C2　內部人公開市場買進（Form 4）</h2>
<p>母體：可用日當天在 S&amp;P 500 或 400；窗 2016-01-04～2026-08-31（可用日）。⭐ 合併母體當判定（美股原生新題，不套 seq316）；只 S&amp;P 500、只 S&amp;P 400 只描述。
資料：≥1 萬美元的董事／高階主管買進 {D['取列']['≥1 萬美元的 A 級買進']:,} 筆，窗內在母體 {D['母體']['其中在母體']:,} 筆；去重後事件 A {D['去重後事件']['A']:,}、B {D['去重後事件']['B']:,}、C {D['去重後事件']['C']:,}、D {D['去重後事件']['D']:,}。</p>
<h3>甲　買進後 20 天，對「同日、同樣跌過（前 20 日報酬同十分位）、沒有內部人買」的股票（Bonferroni 0.05／4）</h3>
{tb(["訊號", "欄", "n", "n_eff", "平均異常報酬", "95% 群集 CI", "Bonferroni CI", "判"], rows2)}
<h3>甲　不同天數（合併欄，描述）</h3>
{tb(["訊號", "20 日", "60 日", "120 日", "240 日"], hz)}
<h3>買之前的「前提」：前 20 日報酬分佈</h3>
{tb(["訊號", "n", "中位", "p10", "落在最低十分位", "落在最低三個十分位"], pre)}
<p>例行型 vs 機會型（A 內、合併、20 日）：例行 {pc(rvo['例行']['平均'], 2, True)}（n {rvo['例行']['n']}）、機會 {pc(rvo['機會']['平均'], 2, True)}（n {rvo['機會']['n']}）、不分類 {pc(rvo['不分類']['平均'], 2, True)}（n {rvo['不分類']['n']}）；三者都測不出。⚠ 約八成內部人不夠「前 3 年每年都有交易」⇒ 不分類（資料只含名冊公司申報）。</p>
<h3>甲　假訊號（同檔、同季、隨機日，1,000 次；⛔ 不判）</h3>
{tb(["訊號", "真平均", "假訊號平均（中位）", "p（假訊號 ≥ 真）"], pl)}
<p class="sub">⚠ 同季隨機日多半落在買進前、股價還在跌的那段 ⇒ 假訊號平均偏負；本表 p 小不代表內部人買進有效（判定看上表 CI）。</p>
<h3>乙　組合層（8 槽等權、200 顆抽籤；判準 ^SP500TR 同窗 {pc(Y['判準']['年化'])}／{pc(Y['判準']['回落'])}）</h3>
{tb(["格｜欄", "年化中位", "回落中位", "比值", "標籤", "持有天數中位", "p10～p90", "最長", "窗尾仍持有（中位，範圍）"], rowsP)}
<p><b>假訊號（同檔、隨機進場日、出場規則同，200 次）</b>：機會型 隨機也做得到 {pc(pl2['B']['p（假訊號年化 ≥ 真）'], 1)}（假訊號年化中位 {pc(pl2['B']['假訊號年化中位'])}）；多人一起買 隨機也做得到 {pc(pl2['C']['p（假訊號年化 ≥ 真）'], 1)}（{pc(pl2['C']['假訊號年化中位'])}）。
等效獨立檔數：機會型 {Y['等效獨立檔數']['B']['等效獨立檔數（月平均）']:.1f}（平均持 {Y['等效獨立檔數']['B']['平均持股檔數']:.1f} 檔）、多人一起買 {Y['等效獨立檔數']['C']['等效獨立檔數（月平均）']:.1f}（平均持 {Y['等效獨立檔數']['C']['平均持股檔數']:.1f} 檔）。每年交易筆數約 {Y['每年交易筆數（中位÷年）']['B｜合併｜主']:.1f}／{Y['每年交易筆數（中位÷年）']['C｜合併｜主']:.1f}。不合格 ⇒ 成本敏感度不跑（登錄：合格或另列才跑）。</p>
{tb(["出場原因（訊號層）", "機會型賣出", "12 個月無新買進且跌破 200 日線", "窗尾結算", "訊號筆數"], rsn)}
{tb(["固定天數（描述，⛔ 不當判定對照）", "年化中位", "回落中位", "標籤"], fx)}
<h3>必報：每年事件數與買法</h3>
{tb(["年", "A", "B", "C", "D", "機會型", "例行型", "不分類", "中位買進金額（美元）"], yrows)}
<p>10b5-1 勾選比例（2023-04 起的買進）：{pc(must['10b5-1 勾選比例（trans_date ≥ 2023-04-01 的 A 級買進）'], 1)}。執行長類若照字面把「含 President」的副總裁也算進去：{must['D 字面版（含副總裁）事件數（去重前）']:,} 筆（本讀法 {must['D 本讀法（去重前）']:,} 筆）。</p>
<p class="sub">偏向存活股：S&amp;P 400 整段缺價 48 檔、S&amp;P 500 18 檔不在母體 ⇒ 結果偏樂觀。</p>

<h2>讀法、偏離與查核</h2>
<div class="card"><ul>
<li>補讀法寫死於看數字之前：ETF 三件 L1～L24（台北 2026-10-10 23:16，<code>researchUSC_late.py</code> 開頭）；C2 K1～K15（台北 2026-10-10 23:41，<code>researchUSC_late_c2.py</code> 開頭）。</li>
<li>偏離登錄字面：C11 HFEA 從 2009-06-25 起（UPRO 6 月才上市）｜C9 費用率改用 SEC 497K 淨費用率（裁定：以 SEC 版為準），早年段從 200 日線可算後的第一個月初起（UPRO 1990-11、TQQQ 2000-01），H 與 M 同起點｜C12 段一從 1990-11 起（10 個月均線要暖身），合成 SSO 費用率照 A1 seq3 的 0.89%｜C2 「President」排除副總裁（字面版件數另報）、聯合申報以第一申報人為代表、4/A 全不用、價格與母體沿用 A3 快取（us-stock-data 881c86a9）而 Form 4 用 b33bde68、出場②的「新的 P 訊號」讀成 A 級買進、出場①在賣出可用日開盤賣。</li>
<li>--check（獨立重寫、抽樣）：{'；'.join(f"{k} 不同 {v['不同']}" for k, v in ck.items() if isinstance(v, dict))} ⇒ 總不同 {ck['總不同']}。</li>
<li>條件出場（seq308）：C12、C9 的主規則與 C2 乙的出場都是條件出場、⛔ 無最長天數；窗尾仍持有與持有天數已報；固定天數只描述。C11 是靜態配置（全期持有）。</li>
<li>資料：us-stock-data b33bde68（ETF 含息日線、DTB3、費用率、ALFRED 首次公布值、Form 4）；私有原始資料（逐日價格、Form 4 逐筆、逐筆事件、權益曲線）⛔ 不在 repo，中間檔在 ~/us_work/c_late/。</li>
</ul></div>
</main>"""
    page = f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>美股 C 批後四件</title><style>{css}</style></head><body>{body}</body></html>"""
    p = os.path.join(OUT, "美股自選研究C批後四件.html")
    open(p, "w", encoding="utf-8").write(page)
    print("→", p, len(page))


if __name__ == "__main__":
    main()
