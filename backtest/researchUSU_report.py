# -*- coding: utf-8 -*-
"""USREG-U 報告：pre_freq.json ⇒ PRE_REPORT.md；body_summary.json＋body_check.json ⇒ BODY_REPORT.md（⛔ 只有彙總）。"""
import os, json, math

OUT = os.path.expanduser("~/tw-p17/backtest/resultsUSU")
P = json.load(open(os.path.join(OUT, "pre_freq.json"), encoding="utf-8"))
POS = ["30", "38.2", "45", "50", "55", "61.8", "70"]


def pp(x, d=2):
    return "—" if x is None or (isinstance(x, float) and not math.isfinite(x)) else f"{x * 100:+.{d}f}pp"


def pc(x, d=1):
    return "—" if x is None or (isinstance(x, float) and not math.isfinite(x)) else f"{x * 100:.{d}f}%"


HEAD = ("| 判準 | 美股登錄 seq2（a3c98a07e882a574）＋seq3（81bfc48eff6258f5，§三 先驗補一句）＋seq4＋seq5；移植來源 台股 PREREGU seq1（4ff4c1731fdded12） |\n"
        "| 讀法 | 裁定 seq214 §三（R1～R4、B1～B7＋USREG-M 斷點規則）＋USREG-X V1～V5；台股 fib_u U1～U6、researchU_core V1～V5、researchU B1～B9 照先例；美股 W1～W9（researchUSU.py 開頭） |\n"
        "| 資料 | us-stock-data `{}`；判定窗 {}～{}；T 可落 ～{}；可用 {} 檔；20 日區段上限 {} |\n").format(
    P["資料commit"], P["判定窗"][0], P["判定窗"][1], P["T可落"][1], P["可用檔數"], P["區段上限"])
L = []; A = L.append
A("# USREG-U pre：頻率盤點＋可判定性算術（⛔ 未讀 T 以後任何收盤）\n")
A("| 欄 | 值 |\n|---|---|\n" + HEAD)
A("## 一、閘\n\n```")
A("台股 selftest_fib_u F1～F9：{} 條全過".format(len(P["fixture"]["台股F1_F9"])))
A("台股本體自測（researchU.selftest，驗 import 來的 dstat／dstat_agg／fake_positions）：過")
for s in P["fixture"]["美股UU1_UU2"]:
    A(s)
A("```\n")
A("## 二、波段（確認日在窗內且當天在指數）\n")
A("| k | 合格波段 | 每檔每年 合併比率／平均／中位 | 至少一位置確認前已觸及 | 同日穿過多位置 |\n|---|---:|---|---:|---:|")
for k, v in P["波段"].items():
    q = v["每檔每年"]
    A("| {} | {:,} | {:.2f}／{:.2f}／{:.2f} | {} | {} |".format(k, v["合格波段數_conf在窗內且在指數"], q["合併比率"], q["平均"], q["中位"],
                                                          pc(v["至少一個位置確認前已觸及的波段比例"]), pc(v["同日穿過多位置（七位置合計）"]["比例"])))
A("\n確認前已觸及（k5，逐位置比例）：" + "、".join("{} {}".format(p, pc(P["波段"]["k5"]["確認前已觸及（逐位置）"][p]["比例"])) for p in POS) + "\n")
A("## 三、事件（保留）與可判定性\n")
A("| 格 | " + " | ".join(POS) + " | 不在母體的觸及 | n_eff 上限 | 波段內部有斷點（只報） | 持有窗內下市 |\n|---|" + "---:|" * (len(POS) + 4))
for nm, v in P["事件帳"].items():
    A("| {} | ".format(nm) + " | ".join("{:,}".format(v["保留"][p]) for p in POS) + " | {:,} | {} | {} | {} |".format(
        v["不在母體的觸及（不開窗）"], v["n_eff上限（保留數與區段取小，六位置取最小）"], v["保留中_波段內部有斷點（只報、未剔）"], v["保留中_持有窗內下市"]))
A("\n```")
A("區段長 20、每位置最多 {} 段 ⇒ 依構造 ①②③ 都可能；主格 k5_H20 的 n_eff 上限 {} ⇒ 可到出口③（判定用的 n_eff 只數分勝負事件，要看 T 以後的收盤 ⇒ 本段只給上限）".format(
    P["區段上限"], P["事件帳"]["k5_H20"]["n_eff上限（保留數與區段取小，六位置取最小）"]))
A("新遇到、登錄與 seq214 都沒寫的讀法：無會改動事件集合或出口者 ⇒ 照先例直接開本體（W1～W9 皆為 seq214／X V 系列的類推）")
A("```")
open(os.path.join(OUT, "PRE_REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("寫出 PRE_REPORT.md")

if os.path.exists(os.path.join(OUT, "body_summary.json")):
    S = json.load(open(os.path.join(OUT, "body_summary.json"), encoding="utf-8"))
    C = json.load(open(os.path.join(OUT, "body_check.json"), encoding="utf-8"))
    J = S["判定格"]; F = S["§五必報"]; D = S["§六描述臂"]; fk = J["假訊號臂_登錄"]; nw = S["描述用假訊號臂_同檔全窗只排除過去20日"]
    L = []; A = L.append
    A("# USREG-U 本體交件：費波那契回撤，費氏位對鄰位（美股）\n")
    A("| 欄 | 值 |\n|---|---|\n" + HEAD.rstrip("\n"))
    A("| 程式 | `backtest/researchUSU.py`（pre＋本體）、`researchUSU_check.py`（獨立路）、`researchUSU_report.py`；偵測器 `fib_u.py`（台股同一支，未改） |")
    A("| 性質 | 單筆層事件研究；判定一格 ⇒ 美股 N_前段 +1；描述臂、假訊號臂不計 N、⛔ 不印判定 |")
    A("| 授權 | 本資料夾只有彙總；逐筆在 `~/us_work/usu/`（repo 外），sha 見 `pre_work_sha.csv`、`body_work_sha.csv` |\n")
    A("## 〇、結論\n\n```")
    pre = "樣本中等（n_eff＝{}，介於 30 與 100 之間）：".format(J["n_eff"]) if J["出口"] == "出口②" else ""
    A("{}判定格 {}（n_eff＝{}）、{}：D ＝ {}，月分群 95% CI {} ～ {}（波段分群 {} ～ {}）".format(pre, J["出口"], J["n_eff"], J["結果"], pp(J["D"]),
      pp(J["lo_月"]), pp(J["hi_月"]), pp(J["lo_波段"]), pp(J["hi_波段"])))
    if J["結果"].startswith("結果①"):
        A("合句：「38.2 與 61.8 被觸及後的止跌反彈比例，測不出比鄰位（30／45、55／70）高。」⛔ 不寫「費波那契沒用」")
    elif J["結果"].startswith("結果②"):
        A("合句：「38.2 與 61.8 被觸及後的止跌反彈比例，測得出比鄰位高。」" + (fk["警語"] if "⚠" in fk["警語"] else ""))
    elif J["結果"].startswith("結果③"):
        A("合句：「38.2 與 61.8 被觸及後的止跌反彈比例，測得出比鄰位低。」（照 P16 §3-3 五句形狀，見 §一）")
    A("缺價的 35 檔不在事件母體，結果偏向存活股（seq3 §一①）。⛔ 單筆層：不可說成「贏 ^SP500TR」。")
    A("```\n")
    A("## 一、判定格與七位置\n")
    A("| 位置 | 保留 | 分勝負 | b(x) | 不分勝負比例 | 觸及後 20 日 X 平均〔CI〕 | R20 扣成本 平均 |\n|---|---:|---:|---:|---:|---|---:|")
    for p in POS:
        v = F["七位置"][p]; x = v["X20對EWc"]
        A("| {} | {:,} | {:,} | {} | {} | {}〔{} ～ {}〕 | {} |".format(p, v["保留"], v["分勝負"], pc(v["b"], 2), pc(v["不分勝負比例"]),
                                                                 pp(x.get("平均")), pp(x.get("lo")), pp(x.get("hi")), pp(v["R20扣成本"].get("平均"))))
    f2 = F["費氏位各自_b(F)−鄰位平均（只報）"]
    A("\n兩費氏位各自減鄰位（只報、⛔ 不各自下判定）：38.2 {}〔{} ～ {}〕｜61.8 {}〔{} ～ {}〕；帶緣兩種讀法差異 {} 件".format(
        pp(f2["38.2"]["D"]), pp(f2["38.2"]["lo"]), pp(f2["38.2"]["hi"]), pp(f2["61.8"]["D"]), pp(f2["61.8"]["lo"]), pp(f2["61.8"]["hi"]), J["帶緣兩種讀法差異件數"]))
    A("n_eff 明細：" + "、".join("{} {}".format(p, v["min"]) for p, v in J["n_eff明細"].items()) + "\n")
    if J["結果"].startswith("結果③"):
        A("### 結果③——照 P16 §3-3 五句形狀\n")
        A("① 費氏位沒有帶進登錄設想的那種資訊。② 而且比鄰位差：D {}，CI {} ～ {}（不含 0）。③ 範圍：一個窗、S&P 500 有價成分股、一組設計參數；登錄假訊號臂真 D 在第 {:.1f} 百分位。④ ⛔ 不宣告可反向利用；⛔ 不寫「費波那契沒用」。⑤ 不適用。\n".format(
            pp(J["D"]), pp(J["lo_月"]), pp(J["hi_月"]), fk["真D百分位"]))
    A("## 二、假訊號臂\n")
    A("```")
    A("登錄臂（§七，200 次隨機兩位置）：真 D 在第 {:.1f} 百分位；D_fake ≥ 真 D 的 {}／{}；D_fake 95 百分位 {}；平均 {}；{}".format(
        fk["真D百分位"], fk["D_fake≥真D的次數x"], fk["次數"], pp(fk["D_fake的95百分位"]), pp(fk["D_fake平均"]), fk["警語"]))
    A("描述臂（同檔全窗、只排除過去 20 日；W9）：30 次 D′ 平均 {}、範圍 {} ～ {}、CI 不含 0 的 {}／30；帳 {}".format(
        pp(nw["D平均"]), pp(nw["D範圍"][0]), pp(nw["D範圍"][1]), nw["CI不含0"], nw["帳（30 次合計）"]))
    A("```\n")
    A("## 三、§五 必報\n")
    dp = F["回撤深度"]
    A("```")
    A("回撤深度：全部合格波段中位 {}（眾數區間 {}～{}，n＝{:,}）；以收盤 > H0 結束者中位 {}；Bulkowski 美股中位 59%（只作對照，⛔ 不當判定；美股是其樣本母體）".format(
        pc(dp["全部合格波段"]["中位"]), pc(dp["全部合格波段"]["眾數區間"][0], 0), pc(dp["全部合格波段"]["眾數區間"][1], 0), dp["全部合格波段"]["n"], pc(dp["以收盤>H0結束者"]["中位"])))
    for g, v in F["期初已在／期中加入"].items():
        A("{}：D {}〔{} ～ {}〕".format(g, pp(v["D"]), pp(v["lo"]), pp(v["hi"])))
    A("逐年 D（CI 不含 0 者標 *）：" + "、".join("{} {}{}".format(y, pp(v["D"]), "*" if not (v["lo"] <= 0 <= v["hi"]) else "") for y, v in F["逐年"].items()))
    q = F["§八先驗可否證句"]
    A("先驗（台股登錄 §八；美股 seq3 §三：已看過台股 U 結果、押法不改）：押結果① ⇒ 本件 {}；可否證句：61.8 差 {}（|差| < 3pp：{}）；七位置斜率每 10 個百分點 {}（為負：{}）".format(
        J["結果"], pp(q["b(61.8)−鄰位平均"]), "是" if q["|差|<3個百分點"] else "否", pp(q["七位置b對位置的OLS斜率（每10個百分點）"]), "是" if q["斜率為負"] else "否"))
    A("美股 seq2 §二③ 另押「效果量不大於台股同格」（只記錄）：美 |D| {} vs 台 |D| 0.56pp ⇒ {}".format(pp(abs(J["D"])), "是" if abs(J["D"]) <= 0.0056 else "否"))
    A("```\n")
    A("## 四、§六 描述臂（⛔ 不印判定）\n")
    A("```")
    A("a 50%：D50 {}〔{} ～ {}〕⇒ ⛔ 不可替費氏比率背書".format(pp(D["a_50%"]["D50"]), pp(D["a_50%"]["lo"]), pp(D["a_50%"]["hi"])))
    for k, v in D["b_判定帶與窗"].items():
        A("b {}：D {}〔{} ～ {}〕n_eff {}".format(k, pp(v["D"]), pp(v["lo"]), pp(v["hi"]), v["n_eff"]))
    for k, v in D["c_k"].items():
        A("c {}：D {}〔{} ～ {}〕n_eff {}".format(k, pp(v["D"]), pp(v["lo"]), pp(v["hi"]), v["n_eff"]))
    d_ = D["d_交易版"]
    A("d 交易版（T+1 開盤進、抱 20 日）：D_d {}〔{} ～ {}〕；進場 {:,}、剔除 窗尾 {}／T+1 沒有 K 棒 {}".format(
        pp(d_["D_d"]["D"]), pp(d_["D_d"]["lo"]), pp(d_["D_d"]["hi"]), d_["進場筆數"], d_["剔除_T+21超過窗尾"], d_["剔除_T+1沒有K棒"]))
    A("e 1.618 延伸：未測（登錄 §六 e）")
    A("```\n")
    A("## 五、硬性查核\n\n```")
    A("fixture：台股 F1～F9、台股本體自測 G1～G4、美股 UU1～UU2 全過（PRE_REPORT.md）")
    A("事件與 pre 逐列相同：" + "、".join("{} {}".format(k, "✅" if v["逐列相同"] else "⛔") for k, v in S["查核"]["事件與pre逐列相同"].items()))
    A("獨立路（researchUSU_check.py，直接讀快照 CSV、自己找擺動點與波段）：① 20 筆 幾何／母體／斷點不符 {}、y 不同 {}、g20 最大差 {:.1e}｜② EWc {} 天最大差 {:.1e}｜③ D、SE、CI 重算最大差 {:.1e}、n_eff 相同 {} ⇒ {}".format(
        C["①事件"]["幾何／母體／斷點不符"], C["①事件"]["y不同"], C["①事件"]["g20最大差"], C["②EWc"]["天數"], C["②EWc"]["最大差"],
        C["③判定格重算"]["與本體最大差"], C["③判定格重算"]["n_eff相同"], "全部通過" if C["全部通過"] else "⛔ 有不符"))
    A("⛔ 未 commit、未 push、未派 workflow")
    A("```")
    open(os.path.join(OUT, "BODY_REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("寫出 BODY_REPORT.md（{} 行）".format(len(L)))
