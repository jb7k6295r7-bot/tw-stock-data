# -*- coding: utf-8 -*-
"""USREG-A2 交件頁：resultsUSA2/REPORT.md（給各線）＋ resultsUSA2/美股四件新母體重跑.html（給使用者：結論先講、白話、手機可讀）。
⛔ 只讀 resultsUSA2/ 的彙總 JSON（不讀私有庫、不寫任何逐日或逐筆數字）。

    PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSA2_page
"""
import json
import os

import numpy as np

OUT = os.path.expanduser("~/tw-p17/backtest/resultsUSA2")
G3 = ("只S&P400", "合併", "只S&P500")
GN = {"只S&P400": "只 S&P 400", "合併": "合併（500＋400）", "只S&P500": "只 S&P 500"}
CSS = """<style>:root{--fg:#222;--bg:#fff;--box:#f4f6fa;--line:#ddd;--mut:#666;--ok:#3a6;--bad:#c44;--mid:#c90}
@media(prefers-color-scheme:dark){:root:not([data-theme="light"]){--fg:#ddd;--bg:#111;--box:#1d2230;--line:#444;--mut:#999}}
:root[data-theme="dark"]{--fg:#ddd;--bg:#111;--box:#1d2230;--line:#444;--mut:#999}
body{font-family:-apple-system,'Noto Sans TC',sans-serif;margin:0 auto;max-width:860px;padding:0 16px 40px;line-height:1.65;color:var(--fg);background:var(--bg)}
h1{font-size:1.3em}h2{font-size:1.12em;margin-top:1.8em;border-bottom:1px solid var(--line)}h3{font-size:1em;margin-top:1.2em}
.box{background:var(--box);border-left:4px solid var(--ok);padding:10px 12px;margin:12px 0}.bad{border-left-color:var(--bad)}.mid{border-left-color:var(--mid)}
.wrap{overflow-x:auto}table{border-collapse:collapse;font-size:.85em;min-width:100%}td,th{border:1px solid var(--line);padding:3px 6px;text-align:right;white-space:nowrap}
td.l,th.l{text-align:left;white-space:normal}.note{color:var(--mut);font-size:.85em}</style>"""


def J(n):
    return json.load(open(os.path.join(OUT, n), encoding="utf-8"))


def p(x, d=2, sign=True):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—"
    if not np.isfinite(x):
        return "—"
    return f"{x * 100:+.{d}f}%" if sign else f"{x * 100:.{d}f}%"


def pp(x, d=2):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—"
    return "—" if not np.isfinite(x) else f"{x * 100:+.{d}f}pp"


def short(r):
    if not isinstance(r, str):
        return "—"
    if r.startswith("結果②"):
        return "測得出（＋）"
    if r.startswith("結果③"):
        return "測得出（−）"
    if r.startswith("結果①"):
        return "測不出"
    return "樣本不足"


def tbl(head, rows, left=1):
    h = "<div class='wrap'><table><tr>" + "".join(f"<th class='{'l' if i < left else ''}'>{c}</th>" for i, c in enumerate(head)) + "</tr>"
    for r in rows:
        h += "<tr>" + "".join(f"<td class='{'l' if i < left else ''}'>{c}</td>" for i, c in enumerate(r)) + "</tr>"
    return h + "</table></div>"


def mdt(head, rows):
    return ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(str(x) for x in r) + " |" for r in rows]


XN = {"box": "箱型", "cup": "杯柄", "w": "W 底", "hs": "頭肩底", "flag": "旗形", "trend": "趨勢線"}
MN = {"甲": "(甲) 兩點法", "乙": "(乙) 三點驗證法", "丙": "(丙) 回歸法"}


def lab_short(s):
    return s.split("（")[0] if isinstance(s, str) else "—"


def main():
    M, U, X, W = J("M_summary.json"), J("U_summary.json"), J("X_summary.json"), J("W1b_summary.json")
    CK = J("check.json") if os.path.exists(os.path.join(OUT, "check.json")) else {}
    cov = M["覆蓋_存活者偏差"]
    # ── 逐格表（事件層）
    cells = []      # (件, 格, 三欄 (數值, 判語), A2標籤, 假訊號, |ret|敏感度標籤變不變)
    for m in ("甲", "乙", "丙"):
        c = M["格"][m]
        cells.append(("M 下降趨勢線突破", MN[m], {g: (p(c[g].get("平均")), short(c[g]["結果"]), c[g].get("n"), c[g].get("n_eff")) for g in G3},
                      c["A2標籤"], c["合併"]["假訊號臂_新預設"]["x／30（CI不含0）"], c["只S&P400"]["假訊號臂_新預設"]["x／30（CI不含0）"],
                      all(short(c[g]["敏感度_剔除未確認|ret|>50%列"]["結果"]) == short(c[g]["結果"]) for g in G3), "20 日超額報酬"))
    u = U["天數"]["20"]
    cells.append(("U 費波那契回撤", "38.2／61.8 比鄰位", {g: (pp(u[g].get("D")), short(u[g]["結果"]), u[g].get("保留"), u[g].get("n_eff")) for g in G3},
                  u["A2標籤"], "真 D 百分位 {:.0f}".format(u["合併"]["假訊號臂_登錄200組"]["真D百分位"]), "{:.0f}".format(u["只S&P400"]["假訊號臂_登錄200組"]["真D百分位"]),
                  all(short(u[g]["敏感度_剔除未確認|ret|>50%列"]["結果"]) == short(u[g]["結果"]) for g in G3), "反彈率差"))
    for t in ("box", "cup", "w", "hs", "flag"):
        c = X["甲"][t]
        cells.append(("X 甲 量幅目標（60 日）", XN[t], {g: (pp(c[g]["H60（判定）"].get("D")), short(c[g]["格的結果"]), c[g]["H60（判定）"].get("n"), c[g]["H60（判定）"].get("n_eff")) for g in G3},
                      c["A2標籤"], c["合併"]["假訊號臂_新預設"]["x／30（CI不含0）"], c["只S&P400"]["假訊號臂_新預設"]["x／30（CI不含0）"],
                      all(short(c[g]["敏感度_剔除未確認|ret|>50%列"]["結果"]) == short(c[g]["格的結果"]) for g in ("只S&P400", "合併")), "達成率差"))
    for t in ("box", "cup", "w", "hs", "flag", "trend"):
        c = X["乙"][t]
        cells.append(("X 乙 成形前（20 日）", XN[t], {g: (p(c[g]["20日（判定）"].get("D")), short(c[g]["格的結果"]), c[g]["20日（判定）"].get("n"), c[g]["20日（判定）"].get("n_eff")) for g in G3},
                      c["A2標籤"], c["合併"]["假訊號臂_新預設"]["x／30（CI不含0）"], c["只S&P400"]["假訊號臂_新預設"]["x／30（CI不含0）"],
                      all(short(c[g]["敏感度_剔除未確認|ret|>50%列"]["結果"]) == short(c[g]["格的結果"]) for g in ("只S&P400", "合併")), "20 日超額報酬"))
    n_ok = sum(1 for c in cells if c[3].startswith("合格"))
    n_exp = sum(1 for c in cells if c[3].startswith("事後擴母體"))
    wr = W["結果"]; B = W["基準"]["SP500TR"]
    wm = {g: wr[g]["main"] for g in G3}
    w_ok = W["A2標籤"]
    xw = X["甲"]["w"]
    # ── HTML
    H = ["<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
         "<title>美股四件新母體重跑</title>", CSS, "</head><body>",
         "<h1>美股四件新母體重跑（S&amp;P 500＋S&amp;P 400）</h1>",
         "<p class='note'>USREG-A2-M／U／X／W1b｜回測線 2026-10-07（台北）｜登錄 sha 8be74b36592db3f4｜裁定 seq316 發號｜資料 us-stock-data 881c86a9｜窗 2016-01-04～2026-09-30</p>",
         "<h2>結論</h2>",
         f"<div class='box mid'><b>16 格裡，照事先定死的口徑：合格 {n_ok + (1 if w_ok.startswith('合格') else 0)} 格、事後擴母體 {n_exp}、其餘不合格。</b><br>"
         f"唯一合格的是 <b>X 甲「W 底」</b>：W 底突破後 60 個交易日內碰到量幅目標的比例，比同一天、波動相近的對照股高 "
         f"{pp(xw['合併']['H60（判定）']['D'], 1)}（合併）、{pp(xw['只S&P400']['H60（判定）']['D'], 1)}（只 S&amp;P 400），兩個都測得出。<br>"
         f"⚠ 但要打折：① 隨便挑日子（假訊號）30 次裡也有 {xw['合併']['假訊號臂_新預設']['x／30（CI不含0）']} 次（合併）、"
         f"{xw['只S&P400']['假訊號臂_新預設']['x／30（CI不含0）']} 次（只 400）一樣「測得出」⇒ 這個差多半不是 W 底本身造成的；"
         f"② 樣本中等（有效樣本約 {xw['合併']['H60（判定）']['n_eff']} 段）；③ 只 S&amp;P 500 那欄若對照改從 S&amp;P 500 自己抽，差縮成 "
         f"{pp(xw['只S&P500']['敏感度_對照改抽該欄自己的指數']['D'], 1)}、測不出（S&amp;P 500 舊結果也是測不出）。"
         "⇒ 照規矩只能進前瞻紀錄觀察，⛔ 不當買進理由。</div>",
         f"<div class='box bad'><b>W1b 條件換股（季營收創 8 季新高＋均線條件，不再符合就換）：不合格。</b><br>"
         f"合併年化中位 {p(wm['合併']['年化中位'], 1)}、只 S&amp;P 400 {p(wm['只S&P400']['年化中位'], 1)}，都輸大盤含息 {p(B['年化'], 1)}；"
         f"最大回落中位 {p(wm['合併']['回落中位'], 0)}（大盤 {p(B['回落'], 0)}）。平均抱 {wm['合併']['持有天數_平均（逐種子平均的中位）']:.0f} 個交易日就換（中位 "
         f"{wm['合併']['持有天數_中位（逐種子中位的中位）']:.0f}、最長 {wm['合併']['最長持有（200 顆中最大）']:.0f}），比固定抱 60 或 120 天的版本略差。</div>",
         "<div class='box bad'>其餘 14 格都不合格：多數三欄都測不出；X「箱型」突破（甲、乙）合併反而<b>測得出（−）</b>＝比對照差；"
         "X 甲「頭肩底」「旗形」只有 S&amp;P 400 單獨測得出（＋）、合併沒有 ⇒ 依口徑不合格（也不算事後擴母體）。</div>",
         "<p class='note'>同一想法在 S&amp;P 500 已測過一次（先驗受污染）；S&amp;P 400 整段缺價的 48 檔（多為破產、被併）不在母體 ⇒ 結果偏向存活股、偏樂觀。</p>",
         "<h2>怎麼判的（白話）</h2>",
         "<p>這四件之前只在 S&amp;P 500 測過（都沒過）。這次把中型股 S&amp;P 400 加進來。因為 S&amp;P 500 的結果已經看過，裁定線事先定死："
         "<b>「只 S&amp;P 400」和「合併」兩個都過才算合格</b>；只有合併過 ⇒「事後擴母體」，最多暫定；只 S&amp;P 500 那欄只是對照舊結果，不判。"
         "每一格照原登錄的判法（20 日、W1b 對大盤含息）；60／120／240 日只描述（240 日在 10 年窗裡只有約 11 段，依構造判不了）。</p>",
         "<h2>事件層 15 格</h2>",
         tbl(["件", "格", "只 S&amp;P 400", "合併", "只 S&amp;P 500", "標籤", "假訊號 x／30（合併／400）"],
             [[c[0], c[1]] + [f"{c[2][g][0]} {c[2][g][1]}" for g in G3] + [lab_short(c[3]), f"{c[4]}／{c[5]}"] for c in cells], left=2),
         "<p class='note'>數字：M、X 乙 ＝ 平均超額報酬（對合併母體等權）；U ＝ 38.2／61.8 位置的反彈率比鄰位高幾個百分點；X 甲 ＝ 60 日內達量幅目標的比例比對照高幾個百分點。"
         "U 的假訊號欄是「真 D 在 200 組隨機位置中的百分位」。</p>",
         "<h2>W1b 組合層（200 顆種子中位）</h2>",
         tbl(["臂", "只 S&amp;P 400", "合併", "只 S&amp;P 500"],
             [[nm] + [f"{p(wr[g][a]['年化中位'], 1)}／{p(wr[g][a]['回落中位'], 0)}　{wr[g][a]['標籤']}" if a in wr[g] else "—" for g in G3]
              for a, nm in (("main", "主臂：不再符合才換（判定）"), ("fix20", "固定 20 日（描述）"), ("fix60", "固定 60 日（描述）"), ("fix120", "固定 120 日（描述；原件）"),
                            ("fix240", "固定 240 日（描述）"), ("ret50", "剔除未確認 |ret|＞50% 列"), ("cost_0.10%", "成本 0.10%"))], left=1),
         f"<p class='note'>格內：年化中位／最大回落中位　標籤。大盤 ^SP500TR 同窗：年化 {p(B['年化'], 1)}、回落 {p(B['回落'], 0)}。"
         f"母體等權（描述）：合併 {p(W['基準']['母體等權_合併（描述）']['年化'], 1)}、只 400 {p(W['基準']['母體等權_只S&P400（描述）']['年化'], 1)}、只 500 {p(W['基準']['母體等權_只S&P500（描述）']['年化'], 1)}。"
         f"主臂窗尾仍持有 {wm['合併']['窗尾仍持有件數（逐種子中位）']:.0f} 件（滿倉 8 槽，2026-09-30 收盤結算）。"
         f"主臂 − 固定 120 日 年化差中位 {pp(wr['合併']['配對差（同種子）']['主臂−固定120日']['年化差中位'], 1)}（合併）。</p>",
         "<h2>限制（一定要知道）</h2><ul>",
         f"<li><b>存活者偏差</b>：S&amp;P 400 在指數股-日有 {p(cov['sp400']['缺價股日比例'], 1, False)} 沒有價格（整段缺 {cov['sp400']['窗內整段沒有價格的檔數']} 檔：破產、被併、代號重用）；"
         f"S&amp;P 500 {p(cov['sp500']['缺價股日比例'], 1, False)}（{cov['sp500']['窗內整段沒有價格的檔數']} 檔）⇒ 偏樂觀。</li>",
         "<li><b>S&amp;P 400 單日漲跌超過 50% 的 23 列</b>資料庫還沒逐筆確認：主結果照用；把它們當斷點剔除的敏感度，16 格的判語都沒有變。</li>",
         "<li>S&amp;P 400 名冊 2016～2019-09 只有年度驗證點；與 500 無關的變動日期約 19% 差 1 天以上；季營收 S&amp;P 400 覆蓋 91.3%（不適用的不進候選）。</li>",
         "<li>母體同一檔在 400↔500 升降級時當成同一家（價格連續）；當天在哪個指數就算哪一欄。</li>",
         "<li>窗只從 2016 年起，沒有更早的驗收段；W 底即使合格也只能前瞻再驗。</li></ul>",
         f"<p class='note'>N（美股帳）本批 +16：M 3、U 1、X 11（甲 5＋乙 6）、W1b 1。"
         f"獨立查核：{'全部通過（0 不同）' if CK.get('全部通過') else '見 check.json'}。逐筆檔只在本機 repo 外。</p>",
         "</body></html>"]
    open(os.path.join(OUT, "美股四件新母體重跑.html"), "w", encoding="utf-8").write("\n".join(H))
    # ── REPORT.md
    L = ["# USREG-A2-M／U／X／W1b 交件：S&P 500＋400 新母體重跑（回測線）", "",
         "| 欄 | 值 |", "|---|---|",
         "| 判準 | USREG-A2 seq1（sha 8be74b36592db3f4）；裁定 seq316（合格＝只 S&P 400 與合併兩者都過；只合併過＝事後擴母體）；正文 USREG seq2～seq5、讀法 seq214 §三 |",
         f"| 資料 | us-stock-data `{M['資料commit']}`（~/usdata/881c86a 唯讀快照）；窗 2016-01-04～2026-09-30 |",
         "| 程式 | `backtest/researchUSA2_data.py`（聯集轉接 D1～D7）、`researchUSA2.py`（M／U／X，讀法 A1～A6）、`researchUSA2_w1b.py`（W1～W9）、`researchUSA2_check.py`（獨立路）、`researchUSA2_page.py` |",
         "| 授權 | 逐筆事件、權益、訊號、面板只在 `~/us_work/a2/`（repo 外），sha 見各 summary 的「逐筆檔sha」；本資料夾只有彙總 |",
         f"| N（美股帳） | +16：A2-M 前段 +3、A2-U +1、A2-X 甲 5＋乙 6 ＝ +11、A2-W1b 組合 +1 |", "",
         "## 〇、結論", "", "```"]
    for c in cells:
        L.append("{}｜{}：{}  ⇒ {}".format(c[0], c[1], "｜".join("{} {} {}".format(GN[g], c[2][g][0], c[2][g][1]) for g in G3), c[3]))
    L.append("W1b 主臂（條件換股）：" + "｜".join("{} 年化中位 {} 回落中位 {} 比值 {:.3f} {}".format(GN[g], p(wm[g]['年化中位']), p(wm[g]['回落中位']), wm[g]['比值'], wm[g]['標籤']) for g in G3)
             + "（^SP500TR {}／{}／{:.3f}） ⇒ {}".format(p(B['年化']), p(B['回落']), B['比值'], w_ok))
    L += ["```", "",
          f"⚠ X 甲 W 底 合格帶警語：假訊號臂（新預設）合併 {xw['合併']['假訊號臂_新預設']['x／30（CI不含0）']}／30、只 400 {xw['只S&P400']['假訊號臂_新預設']['x／30（CI不含0）']}／30 也測得出（＋）⇒ 結果句前必加警語、⛔ 不改判定；"
          f"樣本中等（n_eff {xw['合併']['H60（判定）']['n_eff']}，出口②）；敏感度「對照改抽該欄自己的指數」：只 400 {pp(xw['只S&P400']['敏感度_對照改抽該欄自己的指數']['D'])} {short(xw['只S&P400']['敏感度_對照改抽該欄自己的指數']['結果'])}、"
          f"只 500 {pp(xw['只S&P500']['敏感度_對照改抽該欄自己的指數']['D'])} {short(xw['只S&P500']['敏感度_對照改抽該欄自己的指數']['結果'])}（S&P 500 舊結果 +1.30pp 測不出）。",
          "⚠ 每件必附：同一想法在 S&P 500 已測過一次；S&P 400 整段缺價 48 檔不在母體 ⇒ 結果偏向存活股、偏樂觀。", "",
          "## 一、資料與存活者偏差", ""]
    L += mdt(["指數", "窗內在指數股-日", "其中沒有價格", "比例", "整段沒有價格檔數"],
             [[k, f"{v['窗內在指數股日']:,}", f"{v['其中沒有價格列']:,}", p(v['缺價股日比例'], 2, False), v["窗內整段沒有價格的檔數"]] for k, v in cov.items()])
    L += ["", f"聯集轉接計數：{M['資料轉接計數']}（D3②：成分內但該指數 panel 寧缺 ⇒ 不借另一指數同代號的列；D3③：CHK 兩邊 src 不同 13 天）。",
          "S&P 400 七項限制（資料庫 0245）照寫：①2016～2019-09 只有年度驗證點 ②與 500 無關的變動約 19% 差 ≥1 天 ③名冊 2026-10-04 重建 ④整段缺價（本快照 48 檔）⇒ 偏樂觀 ⑤代號重用 COR／WTW 寧缺 ⑥價格檔與 500 共用 ⑦單日 |ret|>50% 23 列未逐筆確認。",
          "季財報（B1）：S&P 400 季營收在指數期間季覆蓋 91.3%；分段代號 AZPN COHR CR CZR HR RBC RCM VAL 依日期挑 CIK。產業分類（B3）本四件不用。", "",
          "## 二、|ret|＞50% 未確認列的敏感度（裁定 seq316）", "",
          "S&P 400 清單 23 列全部未確認 ⇒ 主結果照用；敏感度＝把它們當硬斷點剔除。16 格判語：" +
          ("全部不變。" if all(c[6] for c in cells) else "有變（見 summary）。") +
          " W1b ret50 臂：合併 {} {}、只 400 {} {}。".format(p(wr['合併']['ret50']['年化中位']), wr['合併']['ret50']['標籤'], p(wr['只S&P400']['ret50']['年化中位']), wr['只S&P400']['ret50']['標籤']), "",
          "## 三、W1b 條件換股（必報）", ""]
    rows = []
    for g in G3:
        a = wr[g]["main"]
        rows.append([GN[g], f"{a['持有天數_平均（逐種子平均的中位）']:.1f}", f"{a['持有天數_中位（逐種子中位的中位）']:.0f}", f"{a['最長持有（200 顆中最大）']:.0f}",
                     f"{a['窗尾仍持有件數（逐種子中位）']:.0f}（{a['窗尾仍持有件數（範圍）'][0]}～{a['窗尾仍持有件數（範圍）'][1]}）", f"{a['交易數中位']:.0f}", p(a["槽位使用率中位"], 1, False)]
                    + [pp(wr[g]["配對差（同種子）"][f"主臂−固定{H}日"]["年化差中位"]) for H in (20, 60, 120, 240)])
    L += mdt(["母體", "持有天數平均", "中位", "最長", "窗尾仍持有", "交易數", "槽位使用率", "主−固20 年化差", "主−固60", "主−固120", "主−固240"], rows)
    L += ["", "（持有天數 ＝ 賣出成交日 − 買進成交日，交易日；固定 H 日臂依原件收盤出 ⇒ 顯示 H−1。）", "", "各臂（200 顆中位；只有 main 進判定）：", ""]
    rows = []
    for g in G3:
        for a, v in wr[g].items():
            if a == "配對差（同種子）":
                continue
            rows.append([GN[g], a, p(v["年化中位"]), p(v["回落中位"]), f"{v['比值']:.3f}", v["標籤"], "{:.0%}／{:.0%}／{:.0%}".format(*[v["逐種子標籤比例"][k] for k in ("合格", "另列", "不合格")]), v["訊號表筆數"]])
    L += mdt(["母體", "臂", "年化中位", "回落中位", "比值", "標籤", "逐種子 合格／另列／不合格", "訊號表筆數"], rows)
    L += ["", "基準：" + "；".join(f"{k} {p(v['年化'])}／{p(v['回落'])}／{v['比值']:.3f}" for k, v in W["基準"].items()), "",
          f"候選盤點：{json.dumps(W['候選盤點'], ensure_ascii=False)}", f"Z4 流動性：{json.dumps(W['Z4_liq_amt20美元'], ensure_ascii=False)}；倒閉銀行訊號數 {json.dumps(W['倒閉銀行'], ensure_ascii=False)}", "",
          "## 四、事件層描述天數（⛔ 不判）", ""]
    rows = []
    for m in ("甲", "乙", "丙"):
        for g in G3:
            c = M["格"][m][g]
            rows.append([f"M {m}", GN[g]] + [f"{p(c[f'描述_{H}日']['平均'])} {short(c[f'描述_{H}日']['結果（描述、⛔ 不判）'])}（n_eff {c[f'描述_{H}日']['n_eff']}）" for H in (60, 120, 240)])
    for g in G3:
        rows.append(["U", GN[g]] + [f"{pp(U['天數'][str(H)][g].get('D'))} {short(U['天數'][str(H)][g]['結果'])}（n_eff {U['天數'][str(H)][g].get('n_eff')}）" for H in (60, 120, 240)])
    for t in ("box", "cup", "w", "hs", "flag"):
        for g in G3:
            c = X["甲"][t][g]
            rows.append([f"X 甲 {XN[t]}", GN[g], "（判定格 H60）", f"{pp(c['H120（描述：依構造不可判定）'].get('D'))}（n_eff {c['H120（描述：依構造不可判定）'].get('n_eff')}）",
                         f"{pp(c['H240（描述：依構造不可判定）'].get('D'))}（n_eff {c['H240（描述：依構造不可判定）'].get('n_eff')}）"])
    for t in ("box", "cup", "w", "hs", "flag", "trend"):
        for g in G3:
            c = X["乙"][t][g]
            rows.append([f"X 乙 {XN[t]}", GN[g]] + [f"{p(c[f'{H}日（描述、⛔ 不判）'].get('D'))} {short(c[f'{H}日（描述、⛔ 不判）'].get('結果'))}（n_eff {c[f'{H}日（描述、⛔ 不判）'].get('n_eff')}）" for H in (60, 120, 240)])
    L += mdt(["件", "欄", "60 日", "120 日", "240 日"], rows)
    L += ["", "（120 日最多 22 段、240 日最多 11 段 ⇒ 依構造出口①，只描述。）", "",
          "## 五、敏感度（描述）", "",
          "- 基準改用該欄自己的指數等權（M、X 乙）、X 甲 對照改抽該欄自己的指數：見各 summary 的「敏感度_」鍵；判語有變的格：" +
          "、".join(f"X 甲 {XN[t]}／{GN[g]}（{short(X['甲'][t][g]['格的結果'])}→{short(X['甲'][t][g]['敏感度_對照改抽該欄自己的指數']['結果'])}）"
                   for t in ("box", "cup", "w", "hs", "flag") for g in ("只S&P400", "只S&P500")
                   if short(X['甲'][t][g]['格的結果']) != short(X['甲'][t][g]['敏感度_對照改抽該欄自己的指數']['結果'])) +
          "；" + "、".join(f"X 乙 {XN[t]}／{GN[g]}（{short(X['乙'][t][g]['格的結果'])}→{short(X['乙'][t][g]['敏感度_基準改用該欄自己的指數等權']['結果'])}）"
                          for t in ("box", "cup", "w", "hs", "flag", "trend") for g in ("只S&P400", "只S&P500")
                          if short(X['乙'][t][g]['格的結果']) != short(X['乙'][t][g]['敏感度_基準改用該欄自己的指數等權']['結果'])), "",
          "## 六、先驗（只記錄，⛔ 不改判）", "",
          f"- 四件標籤與 S&P 500 時相同（約七成）：M、U、W1b 相同（不合格）；X 甲 W 底由「測不出」變「合格（帶警語）」、其餘 X 格不合格同舊。",
          f"- 只 S&P 400 效果量比只 S&P 500 大（約五成）：M {M['先驗_只400效果量大於只500（只記錄）']}；U {U['先驗_只400效果量大於只500（只記錄）']}；X {X['先驗_只400效果量大於只500（只記錄）']}",
          f"- W1b 條件換股主臂仍不合格（約七成）：{W['先驗_主臂仍不合格（只記錄）']}；平均持有天數短於 120（約六成）：{W['先驗_平均持有天數短於120（只記錄）']}", "",
          "## 七、偏離與執行者補讀法", "",
          "- 實體＝代號聯集（D1～D3）；事件歸欄＝事件日當天屬哪個指數（A1）；基準與 X 甲 對照池＝合併母體（A2，登錄「同母體（合併）」）。",
          "- 描述天數 H 的事件與區段（A3）：M、X 乙 用判定那批事件延伸到 T+1+H，區段長 H；U 每個 H 各自偵測（原描述臂 b 同式）、區段長 H；X 甲 H240 另一批（T ≤ 窗尾−240、對照可用 240 日）。",
          "- 假訊號臂只跑判定用那一版（M、X 新預設 30 次；U 登錄 200 組）；不排除版、同檔同月版、U 描述用假訊號臂、M 描述臂 a～f、U §五／§六 其餘描述、X 描述細項本批未重跑（A4、A6）。",
          "- 登錄寫「|ret|>50% 開跑前逐筆確認、未確認當缺」，依裁定 seq316 改為：主結果照用、另報剔除敏感度（A5、W6）。",
          "- W1b 固定天數臂超過窗尾 ⇒ 窗尾收盤結算（原件是 xpos 超過日曆就剔除；W4）；條件檢查的季營收序列用進場那筆（W2）；條件值缺 ⇒ 視為不成立（W3）。",
          "- W1b「合格／另列 ⇒ 固定跟進出場敏感度」：主臂不合格 ⇒ 未觸發（固定 20／60／120／240 日臂照報）。",
          "- W1b 的 keep_pb、exact、div_net30 只在合併跑（描述）。", "",
          "## 八、獨立查核（researchUSA2_check.py，不 import 任何主程式）", "", "```", json.dumps(CK, ensure_ascii=False, indent=1, default=float), "```"]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("寫出 REPORT.md、美股四件新母體重跑.html")


if __name__ == "__main__":
    main()
