# -*- coding: utf-8 -*-
"""PREREG地雷股濾網 seq3 網頁（resultsMine/地雷股濾網.html）：結論先講、白話、手機可讀。只讀結果檔。"""
import json
import os

import numpy as np
import pandas as pd

OUT = os.path.expanduser("~/tw-p17/backtest/resultsMine")
CSS = """<style>:root{--bg:#fff;--fg:#222;--box:#f4f6fa;--line:#ddd;--g:#e6f4ea;--y:#fff6dd;--note:#666}
@media(prefers-color-scheme:dark){:root{--bg:#111;--fg:#ddd;--box:#1d2230;--line:#444;--g:#1f3a26;--y:#3a3420;--note:#aaa}}
body{font-family:-apple-system,'Noto Sans TC',sans-serif;margin:0 auto;max-width:820px;padding:0 16px 40px;line-height:1.65;color:var(--fg);background:var(--bg)}
h1{font-size:1.3em}h2{font-size:1.1em;margin-top:1.8em;border-bottom:1px solid var(--line)}h3{font-size:1em;margin-bottom:.3em}
.box{background:var(--box);border-left:4px solid #3a6;padding:10px 12px;margin:12px 0}.bad{border-left-color:#c44}
.wrap{overflow-x:auto}table{border-collapse:collapse;font-size:.85em;min-width:100%}td,th{border:1px solid var(--line);padding:3px 6px;text-align:right;white-space:nowrap}
td.l,th.l{text-align:left}.note{color:var(--note);font-size:.85em}.g{background:var(--g)}.y{background:var(--y)}</style>"""
FN = {"G1": "G1 任一旗", "G2": "G2 兩旗以上", "G3": "G3 淨值偏低或官方警示", "F1_50": "F1 長期下探（一年跌 50% 且在年線下）", "F1_70": "F1 長期下探（跌 70%）",
      "F2_1": "F2 股價低於面額", "F2_05": "F2 低於半個面額", "F3_half": "F3 淨值低於面額一半", "F3_neg": "F3 淨值為負", "F4a": "F4 近 4 季合計虧且最近一季虧",
      "F4b": "F4 近 8 季 ≥ 6 季虧", "F4": "F4 連續虧損", "F5a": "F5 全額交割／變更交易／管理股票", "F5b": "F5 懲罰型停資停券", "F5": "F5 官方警示", "G3n": "G3 窄版（淨值為負或官方警示）"}


def p(x, d=1, sign=False):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—"
    if not np.isfinite(x):
        return "—"
    return f"{x * 100:+.{d}f}%" if sign else f"{x * 100:.{d}f}%"


def tb(head, rows, cls=None):
    h = ["<div class='wrap'><table><tr>" + "".join(f"<th{' class=l' if i == 0 else ''}>{x}</th>" for i, x in enumerate(head)) + "</tr>"]
    for k, r in enumerate(rows):
        c = f" class='{cls[k]}'" if cls and cls[k] else ""
        h.append(f"<tr{c}>" + "".join(f"<td{' class=l' if i == 0 else ''}>{x}</td>" for i, x in enumerate(r)) + "</tr>")
    return "".join(h) + "</table></div>"


def main():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    Y = pd.read_csv(os.path.join(OUT, "yi.csv")); J = pd.read_csv(os.path.join(OUT, "jia.csv")); RC = pd.read_csv(os.path.join(OUT, "jia_recall.csv"))
    DP = pd.read_csv(os.path.join(OUT, "jia_disposal.csv")); BG = pd.read_csv(os.path.join(OUT, "bing_grid.csv")); FR = pd.read_csv(os.path.join(OUT, "flag_rate.csv"))
    DG = pd.read_csv(os.path.join(OUT, "ding.csv")) if os.path.exists(os.path.join(OUT, "ding.csv")) else None
    DJ = json.load(open(os.path.join(OUT, "ding.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "ding.json")) else {}
    CK = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else {}
    V = S["乙判定"]; SE = S["必附一句"]
    H = ["<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
         "<title>地雷股濾網</title>", CSS, "</head><body>",
         "<h1>地雷股濾網：濾掉「長期下探、可能下市」的股票，躲掉什麼、又誤殺多少飆股</h1>",
         "<p class='note'>使用者原話：「濾掉地雷股，長期股價下探的、很有可能會下市的公司…看看會有多少飆股被濾掉！？」｜PREREG地雷股濾網 seq3（sha d38143d4aa992c6e）；"
         "裁定 seq310、311、313、314｜回測線執行，讀法寫死 2026-10-07 02:10（台北）。這是歷史統計，不是對任何一檔的預測或買賣建議。</p>"]
    # ── 結論
    nok = sum(v["該躲格數"] >= 3 for v in V.values())
    H.append("<div class='box bad'><b>結論</b><ul>")
    H.append(f"<li><b>濾掉的股票之後並沒有比較差。</b>三種濾網（G1 任一旗、G2 兩旗以上、G3 淨值偏低或官方警示）跟「同一天、前 20 日漲跌差不多的股票」比，"
             f"持有 20／60／120／250 天，在 2017～2021 和 2022～2026 兩段都明顯較差的格數各是 {V['G1']['該躲格數']}、{V['G2']['該躲格數']}、{V['G3']['該躲格數']} 格（要 4 格中 ≥ 3 格才算）"
             f"⇒ <b>「該躲」三個都不成立（N_單筆 3 判，成立 {nok}）</b>。</li>")
    for g in ("G1", "G2", "G3"):
        x = SE[g]
        H.append(f"<li><b>{FN[g]}</b>：這個濾網躲掉 <b>{x['x 躲掉下市（檔）']} 檔下市</b>（2017-03～2026-08 財務性下市 {x['財務性下市總數']} 檔中，下市前一年內帶過旗的；代理）、"
                 f"<b>{p(x['y 大跌中帶旗比例'], 0)} 的大跌</b>（之後一年跌掉一半以上的股-月中，事前帶旗的比例），代價是<b>誤殺 {p(x['z 誤殺飆股（網格中位）'], 0)} 的飆股</b>"
                 f"（全網格 250 格各格誤殺率的中位，p10～p90：{p(x['z p10'], 0)}～{p(x['z p90'], 0)}；登錄主格 {p(x['登錄主格'], 0)}）。"
                 f"它平常會濾掉母體 {p(x['帶旗股-月占母體'], 1)} 的股票-月。</li>")
    jj = J[(J["代理"] == "主") & (J["k月"] == 12) & (J["旗"] == "G1") & J["段"].isin(["探索", "確認"])]
    nfin = int(jj["帶旗下市"].sum() + jj["無旗下市"].sum()); nall = int(jj["帶旗股-月"].sum() + jj["無旗股-月"].sum())
    H.append(f"<li><b>為什麼躲掉下市卻沒有更好的報酬？</b>本專案的選股母體（W1：有流動性、有足夠交易日）本身就把快下市的股票擋掉了："
             f"2017～2026 母體內 {nall:,} 個股-月，之後一年內財務性下市的只有 {nfin} 個；濾網多擋的大多是之後會反彈的股票。"
             "（下市股「事前帶旗」的比例很高，有一部分是構造使然：主代理本身就是看下市前跌幅，跟 F1 長期下探同一類訊號。）</li>")
    if DG is not None:
        t = DG.set_index(["策略", "濾網"])
        def dd(st, f):
            return t.loc[(st, f), "主窗年化中位"] - t.loc[(st, "不濾（正式）"), "主窗年化中位"]
        H.append(f"<li><b>加在營量 v1、營飆 v1 前面</b>（描述，⛔ 不改正式規則）：營量 v1 濾 G1 年化 {dd('營量 v1', '濾 G1') * 100:+.2f} 點、濾 G3 {dd('營量 v1', '濾 G3') * 100:+.2f} 點；"
                 f"營飆 v1 濾 G1 {dd('營飆 v1', '濾 G1') * 100:+.2f} 點、濾 G3 {dd('營飆 v1', '濾 G3') * 100:+.2f} 點（2017-03～2026-08 主窗，200 顆中位）。"
                 "兩個策略方向相反，且營飆的差大多出在 2017～2021 一段（見四）⇒ 只是描述，撐不起「加濾網比較好」或「比較差」的結論。</li>")
    H.append("</ul></div>")
    H.append("<p class='note'>「飆股」照使用者固定規矩：飆股回推 seq6 網格（250 格），結果取格中位；登錄主格只是網格裡的一格，並列參考。"
             "「財務性下市」：上櫃用官方原因（拒絕往來、管理股票），上市與上櫃「其他」用代理（下市前最後 60 根 K 棒跌超過一半，或淨值為負），標「代理」。</p>")
    # ── 乙
    H.append("<h2>一、濾掉的股票之後表現如何（乙，主判）</h2>")
    H.append("<p>每月最後一個交易日判旗，隔天開盤買、持有 H 天收盤；跟「同一天、前 20 日漲跌在同一個十分位」的股票平均比（基準②）。數字是「帶旗股票 − 基準」的平均，括號是月分群 95% 信賴區間。"
             "要兩段的區間上緣都 ＜ 0 才算「該躲」。<span class='note'>⚠ 60 天以上持有期相鄰月份重疊，區間偏窄。</span></p>")
    rows = []; cls = []
    for g in ("G1", "G2", "G3"):
        for Hh in (20, 60, 120, 250):
            r = {}
            for seg in ("探索", "確認", "早年"):
                q = Y[(Y["段"] == seg) & (Y["旗"] == g) & (Y["H"] == Hh)]
                r[seg] = q.iloc[0] if len(q) else None
            def cell(q):
                if q is None:
                    return "不可判"
                return f"{p(q['X 平均'], 1, True)}（{p(q['lo'], 1, True)}～{p(q['hi'], 1, True)}）n＝{int(q['事件']):,}"
            ok = next(h["該躲"] for h in V[g]["格"] if h["H"] == Hh)
            rows.append([f"{FN[g]}｜{Hh} 天", cell(r["探索"]), cell(r["確認"]), cell(r["早年"]), "是" if ok else "否"]); cls.append("y" if ok else "")
    H.append(tb(["旗｜持有", "2017～2021", "2022～2026", "2005～2014（只上市）", "該躲"], rows, cls))
    H.append("<p class='note'>早年 G3 不可判（淨值資料 2015 起、官方警示 2015 起）；早年 G1、G2 只用 F1、F2。下市股以最後有成交日收盤計。"
             "另算「財務性下市者報酬代 −100%」的對照，結果幾乎不變（母體內這種筆數 0～3 筆，見 yi.csv「含歸零」欄）。</p>")
    # 單旗
    rows = []
    for f in ("F1_50", "F1_70", "F2_1", "F2_05", "F3_half", "F3_neg", "F4a", "F4b", "F5a", "F5b"):
        rr = [FN[f]]
        for seg in ("探索", "確認"):
            for Hh in (60, 250):
                q = Y[(Y["段"] == seg) & (Y["旗"] == f) & (Y["H"] == Hh)]
                rr.append("—" if not len(q) else f"{p(q.iloc[0]['X 平均'], 1, True)}（上緣 {p(q.iloc[0]['hi'], 1, True)}）n＝{int(q.iloc[0]['事件'])}")
        rows.append(rr)
    H.append("<h3>單一旗（描述）</h3>" + tb(["旗", "2017～2021 持有 60 天", "2017～2021 持有 250 天", "2022～2026 持有 60 天", "2022～2026 持有 250 天"], rows))
    # ── 甲
    H.append("<h2>二、帶旗的股票有多少會下市（甲，描述）</h2>")
    H.append("<p>單位是「母體內的股票-月」。精準度＝帶旗之後 k 個月內財務性下市的比例；倍數＝帶旗 ÷ 無旗。主代理與資料庫建議版（下市前 250 個交易日內進過全額交割／變更交易、懲罰型停資停券或處置）並列。</p>")
    rows = []
    for ver in ("主", "並報"):
        for seg in ("探索", "確認", "早年"):
            for g in ("G1", "G2", "G3", "F1_50", "F4", "F5"):
                q = J[(J["代理"] == ver) & (J["段"] == seg) & (J["旗"] == g)]
                if not len(q):
                    continue
                rr = [f"{'主代理' if ver == '主' else '資料庫建議版'}｜{seg}｜{FN[g]}"]
                for k in (12, 24, 36):
                    z = q[q["k月"] == k]
                    if len(z):
                        z = z.iloc[0]
                        rr.append(f"{int(z['帶旗下市'])}／{int(z['帶旗股-月']):,}＝{p(z['精準度'], 2)}；無旗 {p(z['無旗比例'], 2)}；×{z['倍數']:.1f}" if np.isfinite(z["倍數"]) else
                                  f"{int(z['帶旗下市'])}／{int(z['帶旗股-月']):,}＝{p(z['精準度'], 2)}；無旗 {p(z['無旗比例'], 2)}")
                    else:
                        rr.append("—")
                rows.append(rr)
    H.append(tb(["代理｜段｜旗", "12 個月內", "24 個月內", "36 個月內"], rows))
    rows = []
    for ver in ("主", "並報"):
        for seg in ("探索", "確認", "早年"):
            for g in ("G1", "G2", "G3", "F1_50", "F2_1", "F4", "F5"):
                q = RC[(RC["代理"] == ver) & (RC["段"] == seg) & (RC["旗"] == g)]
                if not len(q):
                    continue
                z = q.iloc[0]
                rows.append([f"{'主代理' if ver == '主' else '資料庫建議版'}｜{seg}｜{FN[g]}", f"{int(z['下市前12月內帶旗'])}／{int(z['財務性下市'])}", p(z["召回"], 0),
                             "—" if not np.isfinite(z["提前月數中位（36月內第一次帶旗）"]) else f"{z['提前月數中位（36月內第一次帶旗）']:.0f} 個月", int(z["下市前12月內曾在母體"])])
    H.append("<h3>下市股中，事前一年內有帶旗的比例（召回）</h3>" + tb(["代理｜段｜旗", "帶旗／財務性下市", "召回", "提前多久（中位）", "下市前一年曾在母體"], rows))
    H.append("<p class='note'>「下市前一年曾在母體」很少 ⇒ 快下市的股票大多早就因為流動性不足掉出選股母體。提前多久＝下市前 36 個月內第一次帶旗到下市的月數。"
             "資料庫建議版會把一些被收購、私有化的上市股也算成財務性（收購前常有股權過度集中的停資停券），兩版不一致 "
             f"{S['下市']['兩代理不一致（在名冊）']} 筆（名冊內 {S['下市']['在名冊']} 筆下市）。</p>")
    rows = [[f"{z['段']}｜{FN.get(z['旗'], z['旗'])}", p(z["帶旗 12 月內被列處置"], 1), p(z["無旗"], 1)] for _, z in DP.iterrows()]
    H.append("<h3>有旗股之後 12 個月內被列處置的比例</h3>" + tb(["段｜旗", "帶旗", "無旗"], rows))
    # ── 丙
    H.append("<h2>三、會誤殺多少飆股（丙，描述；使用者要的數）</h2>")
    H.append("<p>飆股＝飆股回推網格的每一格事件（全上市櫃普通股，含沒有流動性的）；看起漲前一天正在生效的那次月底判旗。第一個數是 250 格各格誤殺率的中位，"
             "括號是 p10～p90；登錄主格只是其中一格。</p>")
    rows = []
    for seg in ("探索＋確認", "探索", "確認", "早年"):
        for f in ("G1", "G2", "G3", "F1_50", "F2_1", "F3_half", "F4", "F5"):
            q = BG[(BG["段"] == seg) & (BG["版本"] == "全部") & (BG["旗"] == f)]
            w = BG[(BG["段"] == seg) & (BG["版本"] == "W1 母體內") & (BG["旗"] == f)]
            if not len(q):
                continue
            z = q.iloc[0]
            rows.append([f"{seg}｜{FN[f]}", f"<b>{p(z['網格中位'], 0)}</b>（{p(z['p10'], 0)}～{p(z['p90'], 0)}）", f"{p(z['網格中位(≥30)'], 0)}",
                         f"{p(z['登錄主格 H120 g100%'], 0)}", "—" if not len(w) else f"{p(w.iloc[0]['網格中位'], 0)}（{p(w.iloc[0]['p10'], 0)}～{p(w.iloc[0]['p90'], 0)}）"])
    H.append(tb(["段｜旗", "誤殺率（網格中位）", "只算 ≥30 事件的格", "登錄主格", "只算起漲時在 W1 母體內的"], rows))
    rows = []
    for x in S["丙_變飆股"]:
        m = x["主格"] or {}
        rows.append([f"{x['段']}｜{FN[x['旗']]}", f"×{x['全網格倍數中位']:.2f}（{x['p10']:.2f}～{x['p90']:.2f}）",
                     f"{p(m.get('帶旗起漲比例'), 2)} vs {p(m.get('無旗起漲比例'), 2)}（×{m.get('倍數', float('nan')):.2f}）"])
    H.append("<h3>反過來看：帶旗的股票，下個月開始起漲的機率是無旗的幾倍</h3>" + tb(["段｜旗", "全網格倍數中位（p10～p90）", "登錄主格：帶旗 vs 無旗"], rows))
    H.append("<p class='note'>倍數 ＞ 1 ＝ 帶旗股票反而比較常起漲（低檔、虧損股的波動大）。被濾掉的飆股之後的最大漲幅（起漲後 250 日內最高點）與沒被濾掉的差不多，逐格見 bing_cells.csv。</p>")
    # ── 丁
    if DG is not None:
        H.append("<h2>四、加在營量 v1、營飆 v1 前面（丁，描述；⛔ 不改正式規則）</h2>")
        rows = [[f"{z['策略']}｜{z['濾網']}", p(z["主窗年化中位"], 2), p(z["主窗回落中位"], 1), p(z["探索年化中位"], 2), p(z["確認年化中位"], 2),
                 f"{z['濾掉筆數平均（每顆）']:.1f}", p(z["濾掉那些筆 淨報酬平均（毛−0.585%）"], 1, True)] for _, z in DG.iterrows()]
        H.append(tb(["策略｜濾網", "年化中位", "回落中位", "2017～2021 年化", "2022～2026 年化", "每顆濾掉幾筆", "被濾掉那些筆的報酬（扣成本）"], rows))
        sig = DJ.get("帶旗訊號", {})
        H.append("<p class='note'>選股當天正在生效的旗；帶旗就不買、名額留現金（⛔ 不遞補）。不濾版與正式數字（resultsT1fix t1 版，T1 開、停止交易強制出場開）"
                 f"逐位元相同（{DJ.get('閘門', {})}）。窗內訊號帶旗比例："
                 + "；".join(f"{g} 營飆 {v['c1']['帶旗訊號']}／{v['c1']['窗內訊號']}、營量 {v['c13']['帶旗訊號']}／{v['c13']['窗內訊號']}" for g, v in sig.items()) + "</p>")
    # ── 先驗
    H.append("<h2>五、事前押注對照</h2>")
    j36 = J[(J["代理"] == "主") & (J["k月"] == 36) & (J["旗"] == "G3")]
    r12 = RC[(RC["代理"] == "主") & (RC["旗"] == "G3") & RC["段"].isin(["探索", "確認"])]
    rec = r12["下市前12月內帶旗"].sum() / max(r12["財務性下市"].sum(), 1)
    g1z = SE["G1"]["z 誤殺飆股（網格中位）"]
    pr = [["① G3 三年內財務性下市比例 ＞ 無旗 10 倍", "；".join(f"{r['段']} ×{r['倍數']:.1f}" if np.isfinite(r["倍數"]) else f"{r['段']} 帶旗 0 筆下市" for _, r in j36.iterrows())],
          ["① 下市股中事前一年有 G3 的 ≤ 六成", f"{p(rec, 0)}"],
          ["② G3 該躲成立", V["G3"]["判定"]], ["② G1 該躲不成立", V["G1"]["判定"]],
          ["③ 飆股起漲前帶 G1 ≥ 20%", f"網格中位 {p(g1z, 0)}"]]
    if DG is not None:
        t = DG.set_index(["策略", "濾網"])
        pr.append(["④ 加 G3 對營量／營飆幾乎沒差", f"營量 {(t.loc[('營量 v1', '濾 G3'), '主窗年化中位'] - t.loc[('營量 v1', '不濾（正式）'), '主窗年化中位']) * 100:+.2f} 點、"
                                                 f"營飆 {(t.loc[('營飆 v1', '濾 G3'), '主窗年化中位'] - t.loc[('營飆 v1', '不濾（正式）'), '主窗年化中位']) * 100:+.2f} 點"])
    H.append(tb(["台股策略線押注", "結果"], pr))
    # ── 揭露
    f3 = S.get("F3 下市股覆蓋", {})
    H.append("<h2>六、必須知道的限制</h2><ul>")
    H.append(f"<li><b>淨值（F3）只有現存公司</b>：2015 下半年起下市、在名冊內的 {f3.get('2015-07 起下市且在主名冊', '?')} 檔中，淨值表有資料的只有 {f3.get('其中 bs_hist（淨值）有任何一季', '?')} 檔"
             f"（EPS 表有 {f3.get('其中 fin_hist（EPS）有任何一季', '?')} 檔）⇒ 下市股的 F3 幾乎全部不可判，G3 對下市股實際上只剩官方警示；主代理的「淨值為負」也因此幾乎用不到。⛔ 沒有拿權益 ÷ 股本代替。</li>")
    H.append("<li>官方警示（F5）只有 2015 起；會計師繼續經營疑慮（b3）不做。懲罰型停資停券：上市用 marginratio 的四種原因，上櫃用融資融券備註 A～D；"
             "其中「股權過度集中」很常見，F5 平常約占母體 3～7% 股-月（逐年見 flag_rate.csv）。注意股、處置股不進 F5。</li>")
    H.append(f"<li>面額：par_timeline 只收現存股 ⇒ 已下市股與少數空白一律假設 10 元（母體內曾出現 {len(S['面額假設10元（母體內曾出現）'])} 檔，清單在 summary.json）。</li>")
    H.append("<li>早年（2005～2014）只有上市、母體用流動性＋交易日數；只能判 F1、F2。早年下市原因的代理只看跌幅（主）或處置（資料庫版，2010-12 起）。</li>")
    H.append("<li>季報可用日：有上傳時戳用時戳次一交易日，否則法定期限後第 1 個交易日再加 5 天（2016～2018 沒有時戳）。官方警示以快照日的次一交易日起可用。</li>")
    H.append("<li>母體：上市櫃普通股含已下市（⛔ 不剔），新母體閘（GATE_V2）；W1 eligible 用 panel_ext（edc6f 快照）。資料：tw-stock-data main 796d94c9da。</li>")
    if CK:
        H.append(f"<li>抽樣查核（另一套寫法從原始 CSV 重算）：合計不同 {CK.get('合計不同')} ⇒ {'過' if CK.get('過') else '⚠ 未過'}"
                 f"（旗 {CK.get('① 旗', {}).get('股-月')} 股-月、乙橫斷面 {CK.get('② 乙 R／基準② 橫斷面', {}).get('格')} 格、下市分類 {CK.get('③ 甲 下市分類（全部列）', {}).get('列')} 列、丙 {CK.get('④ 丙 事件旗', {}).get('事件')} 事件）。</li>")
    H.append("</ul><p class='note'>檔案：backtest/resultsMine/（summary.json、yi.csv、jia*.csv、bing_*.csv、ding.csv、flag_rate.csv、delist.csv、check.json）；程式 backtest/researchMine.py。</p>")
    H.append("</body></html>")
    open(os.path.join(OUT, "地雷股濾網.html"), "w", encoding="utf-8").write("\n".join(H))
    print("page ok")


if __name__ == "__main__":
    main()
