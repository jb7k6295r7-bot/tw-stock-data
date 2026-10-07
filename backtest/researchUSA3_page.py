# -*- coding: utf-8 -*-
"""USREG-A3 交件頁：resultsUSA34/A3/美股價格訊號十六件.html（給使用者：結論先講、白話、手機可讀）。
⛔ 只讀 resultsUSA34/A3/ 的彙總 JSON（不讀私有庫、不寫任何逐日或逐筆數字）。

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSA3_page
"""
import html
import re
import json
import os

OUT = os.path.expanduser("~/tw-p17/backtest/resultsUSA34/A3")
ITEMS = ["A3-1", "A3-2", "A3-3", "A3-4", "A3-5", "A3-6", "A3-7", "A3-8", "A3-10", "A3-11", "A3-12", "A3-13", "A3-14", "A3-15", "A3-16", "A3-17"]
CSS = """<style>:root{--fg:#222;--bg:#fff;--box:#f4f6fa;--line:#ddd;--mut:#666;--ok:#3a6;--bad:#c44;--mid:#c90}
@media(prefers-color-scheme:dark){:root:not([data-theme="light"]){--fg:#ddd;--bg:#111;--box:#1d2230;--line:#444;--mut:#999}}
:root[data-theme="dark"]{--fg:#ddd;--bg:#111;--box:#1d2230;--line:#444;--mut:#999}
body{font-family:-apple-system,'Noto Sans TC',sans-serif;margin:0 auto;max-width:900px;padding:0 16px 40px;line-height:1.65;color:var(--fg);background:var(--bg)}
h1{font-size:1.3em}h2{font-size:1.12em;margin-top:1.8em;border-bottom:1px solid var(--line)}h3{font-size:1em;margin-top:1.2em}
.box{background:var(--box);border-left:4px solid var(--ok);padding:10px 12px;margin:12px 0}.bad{border-left-color:var(--bad)}.mid{border-left-color:var(--mid)}
.wrap{overflow-x:auto}table{border-collapse:collapse;font-size:.85em;min-width:100%}td,th{border:1px solid var(--line);padding:3px 6px;text-align:left;vertical-align:top}
.note{color:var(--mut);font-size:.85em}.tag{font-weight:bold}.t-ok{color:var(--ok)}.t-bad{color:var(--bad)}.t-mid{color:var(--mid)}</style>"""


def e(x):
    return html.escape(str(x)) if x is not None else "—"


def lab0(s):
    return s.split("（")[0] if isinstance(s, str) else "—"


def tcls(l):
    return "t-ok" if l == "合格" else ("t-mid" if l.startswith("事後擴母體") or l.startswith("另列") or l.startswith("待裁定") else "t-bad")


def tbl(head, rows):
    h = "<div class='wrap'><table><tr>" + "".join(f"<th>{c}</th>" for c in head) + "</tr>"
    for r in rows:
        h += "<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>"
    return h + "</table></div>"


def fmt_exit(x):
    if not isinstance(x, dict):
        return "—"
    out = []
    for k, v in x.items():
        if isinstance(v, float):
            v = f"{v:.3f}" if abs(v) < 1 else f"{v:.1f}"
        elif isinstance(v, (dict, list)):
            v = json.dumps(v, ensure_ascii=False, default=str)
        out.append(f"{e(k)}：{e(v)}")
    return "<br>".join(out)


def main():
    J = {it: json.load(open(os.path.join(OUT, it + ".json"), encoding="utf-8")) for it in ITEMS if os.path.exists(os.path.join(OUT, it + ".json"))}
    C = {k: v["卡片"] for k, v in J.items()}
    S = json.load(open(os.path.join(OUT, "A3_summary.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "A3_summary.json")) else {}
    CK = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else {}
    multi = [k for k, c in C.items() if k != "A3-17" and isinstance(c.get("標籤"), str) and re.search(r"（\d+ 格）", c.get("標籤"))]
    labs = {k: lab0(c.get("標籤")) for k, c in C.items() if k != "A3-17" and k not in multi}
    ok = [k for k, l in labs.items() if l == "合格"]
    exp = [k for k, l in labs.items() if l.startswith("事後擴母體") or l.startswith("另列")]
    cannot = [k for k, l in labs.items() if l.startswith("不可判定")]
    bad = [k for k, l in labs.items() if l == "不合格"]
    nm = lambda k: f"{k} {C[k].get('名稱', '')}"
    cov = None
    for v in J.values():
        if "覆蓋_存活者偏差" in v:
            cov = v["覆蓋_存活者偏差"]; break
    H = ["<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
         "<title>美股價格訊號十六件</title>", CSS, "</head><body>",
         "<h1>美股價格訊號十六件（S&amp;P 500＋S&amp;P 400）</h1>",
         "<p class='note'>USREG-A3（A3-1～8、A3-10～17）｜回測線 2026-10-07（台北）｜登錄 sha 0dc16d3267725d7c＋bc0927fed5996fd4｜裁定 seq318 發號、seq319 裁示｜"
         "資料 us-stock-data 881c86a9｜窗 2016-01-04～2026-09-30（探索 2016～2021、確認 2022～2026-09）</p>",
         "<h2>結論</h2>"]
    box = "box" if ok else "box bad"
    H.append(f"<div class='{box}'><b>15 件（A3-17 另計）照事先定死的口徑：合格 {len(ok)} 件、事後擴母體／另列 {len(exp)} 件、不合格 {len(bad)} 件、不可判定 {len(cannot)} 件"
             + (f"；多格整族件 {len(multi)} 件另述" if multi else "") + "。</b><br>"
             + "".join(f"{e(nm(k))}：{e(C[k].get('標籤'))}——{e(C[k].get('三欄', {}).get('合併'))}（詳見下方一句話）。<br>" for k in multi)
             + (f"合格：{'、'.join(e(nm(k)) for k in ok)}。<br>" if ok else "")
             + (f"事後擴母體（只有合併過、S&amp;P 400 自己沒過 ⇒ 最多暫定、只進前瞻紀錄）：{'、'.join(e(nm(k)) for k in exp)}。<br>" if exp else "")
             + (f"不可判定：{'、'.join(e(nm(k)) for k in cannot)}。<br>" if cannot else "")
             + "這些想法都來自台股（多數在台股就不合格）；美股沒有早年段可以再驗一次。</div>")
    if "A3-17" in C:
        c = C["A3-17"]
        H.append(f"<div class='box mid'><b>A3-17 飆股價量特徵：只做到探索段挑選，等裁定。</b><br>{e(c.get('結果句'))}</div>")
    H += ["<h2>怎麼判的（白話）</h2>",
          "<p>每個想法在兩個母體各判一次：<b>「只 S&amp;P 400」和「合併（500＋400）」兩個都過才算合格</b>；只有合併過 ⇒「事後擴母體」，最多暫定。"
          "只 S&amp;P 500 那欄只是描述、不判。原登錄有「探索／確認」兩段的，在探索段（2016～2021）用合併欄挑一格，確認段（2022～2026-09）兩個母體都判。"
          "進場是條件觸發的，主臂一律「條件出場」：收盤看到出場訊號、隔天開盤賣，不設最長天數；窗尾還抱著的照實報。固定抱 20／60／120／240 天只當描述。</p>",
          "<h2>逐件一覽</h2>",
          tbl(["件", "名稱", "標籤", "N", "合併", "只 S&amp;P 400", "只 S&amp;P 500（描述）"],
              [[e(it), e(C[it].get("名稱")), f"<span class='tag {tcls(lab0(C[it].get('標籤')))}'>{e(C[it].get('標籤'))}</span>",
                e(C[it].get("N") if C[it].get("N") is not None else "待裁定"),
                e(C[it].get("三欄", {}).get("合併")), e(C[it].get("三欄", {}).get("只400")), e(C[it].get("三欄", {}).get("只500"))] for it in ITEMS if it in C]),
          "<h2>每件一句話</h2><ul>"]
    for it in ITEMS:
        if it in C:
            H.append(f"<li><b>{e(nm(it))}</b>：{e(C[it].get('結果句'))}</li>")
    H.append("</ul>")
    rows = [[e(it), fmt_exit(C[it].get("條件出場必報"))] for it in ITEMS if it in C and C[it].get("條件出場必報")]
    if rows:
        H += ["<h2>條件出場（必報：抱多久、窗尾還抱著幾檔、賣在離頂多近）</h2>",
              "<p class='note'>看的是「賣的時候離持有期間最高點多近」，不是抱幾天。離頂距離 ＝ 出場價 ÷ 持有期間最高收盤 − 1（越接近 0 越貼近頂）。</p>",
              tbl(["件", "主臂（判定格）"], rows)]
    H += ["<h2>限制（一定要知道）</h2><ul>",
          "<li><b>想法來自台股</b>：這 16 件都是台股先測過的想法（多數在台股不合格），搬到美股是新資料再測一次。</li>",
          "<li><b>缺早年段</b>：台股原登錄多有「早年段」再驗；美股資料從 2016 起，沒有早年段 ⇒ 判定只看確認段＋兩個母體都要過（裁定 seq319）。</li>"]
    if cov:
        H.append(f"<li><b>存活者偏差</b>：S&amp;P 400 在指數股-日有 {cov['sp400']['缺價股日比例'] * 100:.1f}% 沒有價格（整段缺 {cov['sp400']['窗內整段沒有價格的檔數']} 檔：破產、被併、代號重用）；"
                 f"S&amp;P 500 {cov['sp500']['缺價股日比例'] * 100:.1f}%（{cov['sp500']['窗內整段沒有價格的檔數']} 檔）⇒ 結果偏樂觀。</li>")
    H += ["<li><b>S&amp;P 400 單日漲跌超過 50% 的 23 列</b>資料庫還沒逐筆確認：主結果照用；把它們剔除的敏感度逐件另報（見 REPORT.md）。</li>",
          "<li>台股的漲跌停、處置、法人、融資等條件美股沒有 ⇒ 拿掉（標「特徵不全」）；月營收改季營收（季版比月版寬：創 8 季新高觸發 34%）。</li></ul>"]
    nsum = S.get("N合計（A3-1～16，不含 A3-17）")
    H.append(f"<p class='note'>N（美股帳）：A3-1～16 合計 {e(nsum)}；A3-17 待裁定（探索段挑出 {e(S.get('A3-17 N 待裁定（＝探索段挑出數）'))} 個，開驗證段時才計）。"
             f"獨立查核：{'全部通過（0 不同）' if CK.get('全部通過') else '見 check.json'}。逐筆檔只在本機 repo 外。</p>")
    H.append("</body></html>")
    open(os.path.join(OUT, "美股價格訊號十六件.html"), "w", encoding="utf-8").write("\n".join(H))
    print("寫出 美股價格訊號十六件.html")


if __name__ == "__main__":
    main()
