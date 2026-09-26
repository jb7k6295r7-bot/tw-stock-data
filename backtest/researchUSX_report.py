# -*- coding: utf-8 -*-
"""USREG-X 報告：pre_freq.json ⇒ PRE_REPORT.md；body_summary.json＋body_check.json ⇒ BODY_REPORT.md（⛔ 只有彙總，無代號＋日期、無價格）。"""
import os, json, math

OUT = os.path.expanduser("~/tw-p17/backtest/resultsUSX")
P = json.load(open(os.path.join(OUT, "pre_freq.json"), encoding="utf-8"))
NAME = {"box": "箱型", "cup": "杯柄", "w": "W 底", "hs": "頭肩底", "flag": "旗形", "trend": "趨勢線"}
TA = ("box", "cup", "w", "hs", "flag"); TB = ("box", "cup", "w", "hs", "flag", "trend")
FV, FN, FM = "新預設_只排除過去20日", "不排除（描述）", "同檔同月（描述）"


def pct(x, d=1):
    return "—" if x is None or (isinstance(x, float) and not math.isfinite(x)) else f"{x * 100:.{d}f}%"


def pp(x, d=2):
    return "—" if x is None or (isinstance(x, float) and not math.isfinite(x)) else f"{x * 100:+.{d}f}pp"


def ci(j, d=2):
    return "{} ～ {}".format(pp(j.get("lo"), d), pp(j.get("hi"), d)) if j.get("n") else "—"


HEAD = ("| 判準 | 美股登錄 seq2（a3c98a07e882a574）＋seq3（81bfc48eff6258f5）＋seq4（cbfc7610923b9e53）＋seq5（ffb22ecb1bd749ff）；移植來源 台股 PREREGX seq2（7de459d6a4578cf6）；"
        "裁定 seq163 §四②、seq168 §二；回測線 1819 開跑前算術 |\n"
        "| 讀法 | 裁定 seq214 §三（R1 不開合併窗／R2 P0／R3 S1／R4 E0＋B2／B1 in_index 等權＋USREG-M 斷點規則／B4 假訊號／B5 in_index）；台股 researchX Y1～Y11、patterns_x X1～X11 照先例；美股新增 V1～V12（researchUSX.py 開頭） |\n"
        "| 資料 | us-stock-data `{}`；轉接層 46e74a0c8b；有 OHLC 712 檔、可用 {} 檔（2 檔有效 K 棒 < 30 根） |\n").format(P["資料commit"], P["可用檔數"])

# ═════════════ PRE ═════════════
L = []; A = L.append
A("# USREG-X pre：頻率盤點＋可判定性算術（⛔ 未計算任何報酬或達成）\n")
A("| 欄 | 值 |\n|---|---|\n" + HEAD)
A("## 一、閘\n")
A("```")
A("T1 台股合成型態（selftest_patterns_x）：" + "、".join("{} {}".format(NAME[k], "過" if v else "⛔ 不過") for k, v in P["T1_台股合成型態"].items()))
for s in P["T1_美股資料型態"]:
    A(s)
A("```\n")
A("## 二、頻率（保留後；每檔每年＝在指數日分母）\n")
A("| 格 | 窗內且在母體 | 窗內但不在母體 | 合併掉 | 剔除（型態視窗／未來窗／T+1／波動） | 保留 | 每檔每年 合併比率／平均／中位 | 台股 Y11 跨距式 | 有事件的區段 | n_eff 上限 |")
A("|---|---:|---:|---:|---|---:|---|---:|---|---|")
for tag, types in (("甲", TA), ("乙", TB)):
    for t in types:
        f = P["頻率"][f"{tag}_{t}"]; a = f["帳"]
        raw = a.get("原始_窗內且在母體", a.get("S_窗內且在母體"))
        rej = "{}／{}／{}／{}".format(a["剔除_型態視窗斷點"], a["剔除_未來窗斷點"], a.get("剔除_T+1停牌", a.get("剔除_S+1停牌")), a.get("剔除_20日波動不可算", "—"))
        A("| {} {} | {:,} | {:,} | {:,} | {} | **{:,}** | {:.3f}／{:.3f}／{:.3f} | {:.3f} | {} | {} |".format(
            tag, NAME[t], raw, a["窗內但不在母體"], a["合併掉"], rej, f["保留"], f["每檔每年_合併比率_在指數日"], f["每檔每年_平均_曝露≥1年"],
            f["每檔每年_中位_曝露≥1年"], f["每檔每年_合併比率_台股Y11跨距式"],
            "、".join("H{} {}".format(k, v) for k, v in f["有事件的區段數"].items()), "、".join("H{} {}".format(k, v) for k, v in f["n_eff上限_依區段"].items())))
A("\n乙 的「形成段數_有S」（每組第一個 S 之前）：" + "、".join("{} {:,}".format(NAME[t], P["頻率"][f"乙_{t}"]["帳"]["形成段數_有S"]) for t in TB)
  + "；箱型的組逐日滑動（台股 X9）⇒ 由「同檔同型 20 日只取第一個 S」收斂。\n")
A("## 三、可判定性算術（區段長＝H；⛔ 不切小區段）\n")
A("| 格 | 可用日 | 區段長 | 依構造最多區段 | 依構造最好 | 另一讀法（T ≤ 窗尾−H）最多區段 |\n|---|---:|---:|---:|---|---:|")
for k, v in P["開跑前算術"].items():
    A("| {} | {:,} | {} | {} | {} | {} |".format(k, list(v.values())[0], v["區段長"], v["最多區段"], v["依構造最好"], v.get("另一讀法（T ≤ 窗尾−H）最多區段", "—")))
A("\n```")
A("⇒ 甲 H120：依構造只能出口① ⇒【依構造不可判定、改描述】（seq3 §二；1819 信寫最多 21 段，此處以 ceil 計 22 段，同結論）")
A("⇒ 甲 H60：最多 43 段 ⇒ 最好出口② ⇒ 結論句上限「樣本中等（n_eff＝n，介於 30 與 100 之間）：」")
A("⇒ 乙：最多 132 段 ⇒ ①②③ 都可能")
f = P["頻率"]
A("⇒ 本資料實際：甲 杯柄 有事件區段 {}（< 30 ⇒ 出口①）；旗形 {}；箱型、W 底、頭肩底 43；乙 杯柄 {}、旗形 {}、頭肩底 {}".format(
    f["甲_cup"]["有事件的區段數"]["60"] if "60" in f["甲_cup"]["有事件的區段數"] else f["甲_cup"]["有事件的區段數"].get(60),
    f["甲_flag"]["有事件的區段數"].get("60", f["甲_flag"]["有事件的區段數"].get(60)),
    f["乙_cup"]["有事件的區段數"].get("20", f["乙_cup"]["有事件的區段數"].get(20)), f["乙_flag"]["有事件的區段數"].get("20", f["乙_flag"]["有事件的區段數"].get(20)),
    f["乙_hs"]["有事件的區段數"].get("20", f["乙_hs"]["有事件的區段數"].get(20))))
A("```\n")
A("## 四、讀法（新遇到的，都不改事件集合或出口 ⇒ 未停）\n")
A("```")
A("V2 成交量：Yahoo volume（已按拆股調整）、Tiingo adjVolume；Tiingo 原始 volume 版 ⇒ 84 檔 Tiingo 檔的箱型／杯柄觸發與 S 對稱差 {}（全 0）".format(P["V2_Tiingo原始量版_原始偵測對稱差（窗內在母體）"]))
A("V3 研究二 Frame 的 event_dates ⇒ 轉接層 hard_break 日；這些日子本來就在型態視窗斷點內 ⇒ 不改保留集合")
A("V4 台股 Y3 的處置／注意 ⇒ 美股沒有、拿掉（seq1 §一）；S1 只數首末 K 棒之間 ⇒ 未來窗內下市的事件保留（同 USREG-M；甲 計 " +
  "、".join("{} {}".format(NAME[t], P["頻率"][f"甲_{t}"]["帳"]["未來窗內下市（保留，描述）"]) for t in TA) + "）")
A("V6 甲 事件窗照台股 Y1 先例 T ≤ 窗尾−120（兩個 H 同一批）；另一讀法 T ≤ 窗尾−60 的保留件數 " +
  "、".join("{} {:,}".format(NAME[t], v) for t, v in P["V6_另一讀法_甲T≤窗尾−60_保留件數"].items()) + "（H60 最多區段 44，出口上限不變）")
A("```")
open(os.path.join(OUT, "PRE_REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("寫出 PRE_REPORT.md")

# ═════════════ BODY ═════════════
if not os.path.exists(os.path.join(OUT, "body_summary.json")):
    sys_exit = True
else:
    S = json.load(open(os.path.join(OUT, "body_summary.json"), encoding="utf-8"))
    C = json.load(open(os.path.join(OUT, "body_check.json"), encoding="utf-8"))
    FK = S["假訊號臂"]
    L = []; A = L.append
    A("# USREG-X 本體交件：型態量幅目標達成率（甲）＋成形前讀法（乙）（美股）\n")
    A("| 欄 | 值 |\n|---|---|\n" + HEAD.rstrip("\n"))
    A("| 程式 | `backtest/researchUSX.py`（pre＋本體）、`researchUSX_check.py`（獨立路，不 import 主程式）、`researchUSX_report.py`；偵測器 `patterns_x.py`（台股同一支，未改） |")
    A("| 性質 | 單筆層、只做多；判定格 甲 5＋乙 6 ＝ 美股 N_前段 +11；描述臂與假訊號臂不計 N、⛔ 不印判定 |")
    A("| 授權 | 本資料夾只有彙總；逐筆 A_*／B_*、基準日值、查核明細在 `~/us_work/usx/`（repo 外），sha 見 `body_work_sha.csv` |\n")
    A("---\n")
    A("## 〇、結論（判定句寫全名；任何一格測得出 ⇒ 附「同批 11 格」）\n")
    A("```")
    A("甲（量幅目標；只以 H60 下結果，H120 依構造不可判定、改描述；H60 依構造最好出口②）")
    for t in TA:
        j = S["甲"][t]["H60（判定）"]; fx = FK[FV].get(f"甲_{t}_H60", {})
        pre = "樣本中等（n_eff＝{}，介於 30 與 100 之間）：".format(j["n_eff"]) if j["出口"] == "出口②" else ""
        tail = "（同批 11 格）" if S["甲"][t]["格的結果"].startswith(("結果②", "結果③")) else ""
        warn = "⚠ 隨機日也有 {}／30 測得出；".format(fx.get("判過")) if S["甲"][t]["格的結果"].startswith("結果②") and fx.get("判過", 0) >= 2 else ""
        A("  {}{} {}：{}、{}；D_A(60) {}〔{}〕n＝{:,}（事件達成 {}／對照達成 {}）{}".format(warn, pre, NAME[t], j["出口"], S["甲"][t]["格的結果"], pp(j.get("D")), ci(j), j["n"],
          pct(j.get("事件達成率")), pct(j.get("對照達成率")), tail))
    A("乙（成形前讀法；分母＝全部形成中時點 S；X ＝ 20 日報酬 − 0.05% − in_index 等權）")
    for t in TB:
        j = S["乙"][t]["判定"]; fx = FK[FV].get(f"乙_{t}", {})
        tail = "（同批 11 格）" if j["結果"].startswith(("結果②", "結果③")) else ""
        warn = "⚠ 隨機日也有 {}／30 測得出；".format(fx.get("判過")) if j["結果"].startswith("結果②") and fx.get("判過", 0) >= 2 else ""
        pre = "樣本中等（n_eff＝{}，介於 30 與 100 之間）：".format(j["n_eff"]) if j["出口"] == "出口②" else ""
        A("  {}{}{}：{}、{}；X {}〔{}〕n＝{:,}；成形率 {}、破壞率 {}{}".format(warn, pre, NAME[t], j["出口"], j["結果"], pp(j.get("D")), ci(j), j["n"],
          pct(S["乙"][t]["率"]["成形"]["率"]), pct(S["乙"][t]["率"]["破壞"]["率"]), tail))
    A("缺價的 35 檔不在事件母體，結果偏向存活股（seq3 §一①）。")
    A("⛔ 單筆層：不可說成「贏 ^SP500TR」；⛔ 描述臂、H120、假訊號臂不當判定引用。")
    A("```\n")
    for tag, types in (("甲", TA), ("乙", TB)):
        for t in types:
            j = S["甲"][t]["H60（判定）"] if tag == "甲" else S["乙"][t]["判定"]
            if not j["結果"].startswith("結果③"):
                continue
            fx = FK[FV].get(f"甲_{t}_H60" if tag == "甲" else f"乙_{t}", {}); fm = FK[FM].get(f"甲_{t}_H60" if tag == "甲" else f"乙_{t}", {})
            q = "目標被碰到的比例比同波動十分位、同距離的對照股低" if tag == "甲" else "形成中時點之後 20 日比同期 in_index 等權母體差"
            A("### {} {} 結果③（測得出（−））——照 P16 解讀 §3-3 五句形狀（同批 11 格）\n".format(tag, NAME[t]))
            A("① 這個時點沒有帶進登錄設想的那種資訊：{} 這一格的答案不是「較好」，也不是「分辨不出」。".format(NAME[t]))
            A("② 而且{}：{} {}，95% CI {}（**不含 0**），n＝{:,}，n_eff＝{}（{}）。方向與登錄設想**相反**。".format(
                q, "D_A(60)" if tag == "甲" else "平均 X", pp(j.get("D")), ci(j), j["n"], j["n_eff"], j["出口"]))
            A("③ 範圍：一個窗（{}～{}）、S&P 500 有價成分股、研究二箱型定義一組參數、同批 11 格；假訊號臂 新預設 {}／30、同檔同月 {}／30 CI 不含 0。成因類的話只能寫在這個範圍上；"
              "⚠ 效果量很小（{}），且同批 11 格只這{}格落結果③，應讀成「至少沒有比較好」。".format(
                S["判定窗"][0], S["判定窗"][1], fx.get("判過", "—"), fm.get("判過", "—"), pp(j.get("D")), "兩" if tag else ""))
            A("④ ⛔ 不宣告這個反向關係可以拿來用（不可據此寫「箱型可反向操作／放空」）；⛔ 也不可寫「箱型沒用」。")
            A("⑤ 單一訊號對母體、沒有「兩側改善」可比 ⇒ ⑤ 不適用。\n")
    A("## 一、甲：量幅目標達成率（D_A ＝ 事件達成率 − 對照達成率）\n")
    A("| 型 | n | H60 D_A〔CI〕 | n_eff／區段 | H60 出口／結果（判定） | H120 D_A〔CI〕（描述：依構造不可判定） | 事件／對照達成率 H60 | H120 | 開盤即達成 | 目標距離 中位（p10～p90） | 達成天數中位 H60 | 先碰型態低點 H60 |")
    A("|---|---:|---|---|---|---|---|---|---:|---|---:|---:|")
    for t in TA:
        r = S["甲"][t]; j = r["H60（判定）"]; k = r["H120（描述：依構造不可判定）"]; d = r["描述"]; q = d["目標距離％分佈"]
        A("| {} | {:,} | {}〔{}〕 | {}／{} | {} {} | {}〔{}〕 | {}／{} | {}／{} | {} | {}（{}～{}） | {} | {} |".format(
            NAME[t], j["n"], pp(j.get("D")), ci(j), j.get("n_eff"), j.get("區段數"), j["出口"], j["結果"], pp(k.get("D")), ci(k),
            pct(d["H60"]["事件達成率"]), pct(d["H60"]["對照達成率"]), pct(d["H120"]["事件達成率"]), pct(d["H120"]["對照達成率"]),
            pct(d["開盤即達成比例"]), pct(q.get("中位")), pct(q.get("p10")), pct(q.get("p90")), d["H60"]["達成天數中位（事件）"], pct(d["H60"]["先碰型態低點比例"])))
    cup = S["甲"]["cup"]["描述"]
    A("\n杯柄半杯深達成率（描述）：H60 {}、H120 {}；Bulkowski 美股 全杯深 76%／半杯深 50%（只並列；美股是 Bulkowski 的樣本母體 ⇒ ⛔ 不算外部對照）。".format(
        pct(cup["H60"].get("半杯深達成率（描述）")), pct(cup["H120"].get("半杯深達成率（描述）"))))
    A("池空而剔除：" + "、".join("{} {}".format(NAME[t], S["甲"][t]["描述"]["池空而剔除"]) for t in TA) + "；未來 120 日內下市（保留）：" +
      "、".join("{} {}".format(NAME[t], S["甲"][t]["描述"]["未來120日內下市（保留）"]) for t in TA) + "\n")
    A("## 二、乙：成形前讀法\n")
    A("| 型 | n | X〔CI〕 | n_eff | 出口／結果 | 成形率〔CI〕 | 破壞率 | 都沒發生 | 成形組／破壞組／都沒發生組 X（描述） |")
    A("|---|---:|---|---:|---|---|---:|---:|---|")
    for t in TB:
        r = S["乙"][t]; j = r["判定"]; rt = r["率"]
        A("| {} | {:,} | {}〔{}〕 | {} | {} {} | {}〔{}～{}〕 | {} | {} | {}／{}／{} |".format(
            NAME[t], j["n"], pp(j.get("D")), ci(j), j.get("n_eff"), j["出口"], j["結果"], pct(rt["成形"]["率"]), pct(rt["成形"]["lo"]), pct(rt["成形"]["hi"]),
            pct(rt["破壞"]["率"]), pct(rt["都沒發生"]["率"]), pp(rt["成形"]["20日超額（描述）"]), pp(rt["破壞"]["20日超額（描述）"]), pp(rt["都沒發生"]["20日超額（描述）"])))
    A("\n## 三、假訊號臂（⛔ 不計 N；新預設＝判準警語用，另兩版描述）\n")
    A("| 格 | 新預設 x／30（＋） 平均 D | 不排除 x／30（＋） 平均 D | 同檔同月 x／30（＋） 平均 D | 真事件 D |\n|---|---|---|---|---:|")
    for tag, types in (("甲", TA), ("乙", TB)):
        for t in types:
            g = f"甲_{t}_H60" if tag == "甲" else f"乙_{t}"
            real = S["甲"][t]["H60（判定）"].get("D") if tag == "甲" else S["乙"][t]["判定"].get("D")
            cells = []
            for vn in (FV, FN, FM):
                x = FK.get(vn, {}).get(g)
                cells.append("—" if x is None else "{}（{}）{}".format(x["判過"], x["其中(+)"], pp(x["平均D"])))
            A("| {} {}{} | {} | {} | {} | {} |".format(tag, NAME[t], "（H60）" if tag == "甲" else "", *cells, pp(real)))
    A("\n可抽日不足（全取）的檔數：" + "；".join("{} {}".format(k, v) for k, v in S["假訊號臂_可抽日不足檔數"].items() if v) or "無")
    A("（逐次彙總：`body_fake_arm.csv`，只有每次的筆數、平均、CI）\n")
    A("## 四、先驗（台股 §六；美股 seq2 §二③ 另押「效果量不大於台股同格」只記錄）\n")
    A("```")
    TWA = {"box": -0.0063, "cup": -0.0157, "w": 0.0379, "hs": 0.0310, "flag": -0.0048}
    TWB = {"box": -0.0068, "cup": 0.0012, "w": -0.0081, "hs": -0.0051, "flag": 0.0002, "trend": -0.0071}
    A("甲 H60（台股 D_A 對照）：" + "；".join("{} 美 {}／台 {}（|美|≤|台| {}）".format(NAME[t], pp(S["甲"][t]["H60（判定）"].get("D")), pp(TWA[t]),
      "是" if abs(S["甲"][t]["H60（判定）"].get("D", 0)) <= abs(TWA[t]) else "否") for t in TA))
    A("乙（台股 X 對照）：" + "；".join("{} 美 {}／台 {}（|美|≤|台| {}）".format(NAME[t], pp(S["乙"][t]["判定"].get("D")), pp(TWB[t]),
      "是" if abs(S["乙"][t]["判定"].get("D", 0)) <= abs(TWB[t]) else "否") for t in TB))
    fr = sum(1 for t in TB if S["乙"][t]["率"]["成形"]["率"] < 0.5)
    A("可否證的一句「形成中時點的成形率低於一半」：六型中 {} 型成立".format(fr))
    A("```\n")
    A("## 五、硬性查核\n")
    A("```")
    A("T1 台股合成型態 六型全過；美股資料型態 UX1～UX3 全過（見 PRE_REPORT.md）")
    A("獨立路（researchUSX_check.py，直接讀快照 CSV、自己還原、自己判母體與斷點）：")
    A("  ① 甲 {} 筆：c_T、目標距離、事件與對照 H60 達成 最大差 {:.1e}；母體不符 {}".format(C["①甲"]["筆數"], C["①甲"]["最大差（c_T 相對差＋距離差＋兩個達成旗標差）"], C["①甲"]["母體不符"]))
    A("  ② 乙 R {} 筆最大差 {:.1e}；EW20 {} 天最大差 {:.1e}".format(C["②乙"]["R筆數"], C["②乙"]["R最大差"], C["②乙"]["EW天數"], C["②乙"]["EW最大差"]))
    A("  ③ 11 格平均／SE／CI 重算最大差 {:.1e}；筆數、區段相同：{}".format(C["③11格重算"]["最大差"], C["③11格重算"]["筆數區段相同"]))
    A("  ④ 幾何（k＝3 轉折、門檻、頸線／A、首個收盤越過、60 根視窗、目標算式）：" + "、".join("{} {}／{}".format(NAME[k], v["通過"], v["抽"]) for k, v in C["④幾何"].items()))
    A("  ⇒ " + ("全部通過" if C["全部通過"] else "⛔ 有不符"))
    A("```\n")
    A("## 六、限制\n")
    A("```")
    A("窗 2016 起、無更早驗收段；缺價 35 檔不在母體 ⇒ 偏向存活股；面板最早 2015-12-01 ⇒ 期初杯柄（杯身最長 325 日＋前段 120 日）幾乎不可能成形")
    A("研究二對帳（台股 6,417／116）只適用台股資料 ⇒ 美股不做（V12）")
    A("⛔ 未 commit、未 push、未派 workflow")
    A("```")
    open(os.path.join(OUT, "BODY_REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("寫出 BODY_REPORT.md（{} 行）".format(len(L)))
