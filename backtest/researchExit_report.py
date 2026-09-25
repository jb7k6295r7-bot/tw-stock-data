# -*- coding: utf-8 -*-
"""PREREG出場訊號 交件報告產生器：從 resultsExit/{pre_run,summary,check_recompute,check_hand20}.json 產 EXIT_REPORT.md
（數字一律由程式抄，⛔ 不手打）。"""
import os, json

OUT = os.path.expanduser("~/tw-p17/backtest/resultsExit")
SIGN = {"甲": "收盤跌破破壞價", "乙": "收盤跌破 MA20", "丙": "收盤跌破 MA60"}


READINGS = [
    "【兩種讀法①】續抱終點從【實際賣出日 s】（遞延後）起算 s＋(H−1)（主）；另一讀法從排程 T＋1 起算 ⇒ 受影響＝有遞延的筆數（每格 < 1%，見二）",
    "【兩種讀法②】合併對「上一個【保留】事件」數 20 個交易日、被剔除者不開合併窗（主，同 researchM／H2 R5）；另一讀法「對上一個原始事件連鎖」⇒ 每格多合併的保留事件數見事件帳",
    "【兩種讀法③】H20 的 n_eff 區段 ＝ 曆月（主，登錄 §四、seq165）；另一讀法 20 日區段 ⇒ 115（H20）／113（H60），出口不變",
    "【兩種讀法④】假訊號臂「排除真事件前後 20 日」的真事件 ＝ 該格【保留】真事件（主，PREREGU B6 同）；原始事件版未另跑",
    "E1 MA、擺動點、T−1 在該股有效 K 棒序列上數；T＋1、s＋(H−1)、合併、斷點窗、區段在交易日曆上數",
    "E2 MA ＝ 逐根 np.mean（與 state_label.core 同式）；close ＝ 線 不算跌破、close_{T−1} ＝ 線 算在線上；近似相等件數與敏感度見七",
    "E5 可賣 ＝ 有成交 ∧ 開盤非跌停（tradability.dn_o）∧ 還原開盤有限 > 0；開盤缺值也遞延；到最後成交都賣不掉 ⇒ 剔除計數",
    "E6 硬斷點窗 [max(0,T−60), s＋(H−1)]；價格規則 ＋ 連缺 5 日（已下市者最後成交後不算）",
    "B1 H60 主 CI 以 60 日區段分群（(T−窗起點)//60）；B3 H120 不印 CI；B5 對照②扣 0.1425% 買進成本",
    "B6 狀態標籤不套處置／注意閘門；門檻B 進場 ＝ build_sig_gate_b(signal=B) 的 entry_pos ≤ T ≤ entry_pos＋119",
    "80 根閘 ＝「不產生事件」⇒ 在合併之前拿掉、不開合併窗",
]


def P(x, d=2):
    return "—" if x is None else "{:+.{}f}%".format(x * 100, d)


def main():
    pre = json.load(open(os.path.join(OUT, "pre_run.json"), encoding="utf-8"))
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    ck = json.load(open(os.path.join(OUT, "check_recompute.json"), encoding="utf-8"))
    hd = json.load(open(os.path.join(OUT, "check_hand20.json"), encoding="utf-8"))
    L = []
    a = L.append
    a("# PREREG出場訊號 交件（回測線）")
    a("")
    a("- 登錄：台股策略線 seq3（sha 5de87a1fc7699368，2026-09-25 18:56）；裁定：seq167 §一（N_前段 +6）")
    a("- 資料：main {}；gate3；tradable＋delist on；判定窗 {}～{}；gate3 {:,} 檔、可讀 {:,} 檔".format(S["快照"][:10], *S["判定窗"], S["gate3母體"], S["可讀檔數"]))
    a("- 時點：開跑前報 {}；本體第一次彙總報酬 {}；本體完成 {}".format(pre["時戳"], S["時點"]["本體第一次彙總報酬"], S["時點"]["本體完成"]))
    a("- 程式：backtest/exit_signal.py（核心）、selftest_exit_signal.py（fixture）、researchExit.py（pre／body）、researchExit_check.py（獨立重算）、researchExit_hand.py（手算 20 筆）、researchExit_report.py（本報告）")
    a("")
    a("## 一、fixture")
    for m in S["fixture"]:
        a("- ✅ " + m)
    a("")
    a("## 二、開跑前報（⛔ 不看報酬）")
    a("")
    a("| 格 | 保留 | 分群單位 | 有事件區段 | 上限 | n_eff | 可能出口 |")
    a("|---|---:|---|---:|---:|---:|---|")
    for k, v in pre["§四_區段數與可能出口"].items():
        a("| {} | {:,} | {} | {} | {} | {} | {} |".format(k, v["保留事件"], v["分群單位"], v["有事件的區段數"], v["理論上限"], v["n_eff"], v["可能出口"]))
    a("")
    a("頻率（保留事件，每檔每年）：")
    for g in "甲乙丙":
        f = pre["§七第一列_頻率（close 規則、保留事件）"][g + "_H20"]
        a("- {}（H20 母體）：合併母體 {:.2f} 次／股票年；曝露 ≥1 年 {:,} 檔 平均 {:.2f}、中位 {:.2f}、p90 {:.2f}；上市 {:.2f}／上櫃 {:.2f}；逐年 {}".format(
            SIGN[g], f["合併母體比率_事件每股票年"], f["曝露≥1年的股票"], f["每檔每年_平均"], f["每檔每年_中位"], f["每檔每年_p90"], f["上市"], f["上櫃"],
            "、".join("{} {:.2f}".format(y, v["每檔每年"]) for y, v in f["逐年"].items() if v["每檔每年"] is not None)))
    a("")
    a("遞延（保留事件）：")
    for g in "甲乙丙":
        for H in (20, 60):
            d = pre["跌停／停牌遞延"]["{}_H{}".format(g, H)]
            a("- {} H{}：{:,} 筆中遞延 {:,}（{}）；遞延日數分佈 {}；終點狀態 {}".format(g, H, d["保留事件"], d["有遞延"], d["遞延原因"], d["遞延天數分佈"], d["終點狀態"]))
    a("")
    a("## 三、判定 6 格")
    a("")
    a("| 格 | n | n_eff | E | 95% CI（主） | 第二欄 CI（非重疊） | 出口 | 結果 | 假訊號 x／30 | 假 E | 真 E − 假 E |")
    a("|---|---:|---:|---:|---|---|---|---|---:|---:|---:|")
    for g in "甲乙丙":
        for H in (20, 60):
            J = S["判定6格"]["{}_H{}".format(g, H)]; f = J["假訊號"]
            a("| {} H{} | {:,} | {} | {} | {} ～ {}（{} {} 群） | {} ～ {} | {} | {} | {} | {} | {} |".format(
                g, H, J["n"], J["n_eff"], P(J["E"], 3), P(J["lo"], 3), P(J["hi"], 3), J["分群單位"], J["群數"], P(J["lo_非重疊"], 3), P(J["hi_非重疊"], 3),
                J["出口"], J["結果"], f["x／30（落結果③）"], P(f["假訊號日平均E"], 3), P(f["真E−假E"], 3)))
    a("")
    a("給使用者的句子（經情報線；逐格）：")
    for g in "甲乙丙":
        for H in (20, 60):
            a("- {} H{}：{}".format(g, H, S["判定6格"]["{}_H{}".format(g, H)]["給使用者的句子"]))
    a("")
    a("## 四、必報")
    a("")
    a("| 格 | 原始 | K棒不足 | 合併掉 | 硬斷點 | 賣不掉 | 超出日曆 | 保留 | 中位 | 續抱賺的比例 | 最差 | p10 | p90 | 對照① 超額 | 對照② 換0050−續抱 |")
    a("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|")
    for g in "甲乙丙":
        for H in (20, 60):
            J = S["判定6格"]["{}_H{}".format(g, H)]; e = J["事件帳"]; c1 = J["對照①_超額（R−gate3等權同段）"]; c2 = J["對照②_換成0050減續抱（已扣0.1425%）"]
            a("| {} H{} | {:,} | {:,} | {:,} | {:,} | {:,} | {:,} | {:,} | {} | {:.1%} | {} | {} | {} | {}（{}～{}） | {}（{}～{}） |".format(
                g, H, e["原始_窗內"], e["剔除_K棒不足"], e["合併掉"], e["剔除_硬斷點"], e["剔除_賣不掉"], e["剔除_超出日曆"], e["保留"],
                P(J["中位"]), J["續抱賺的比例"], P(J["最差"]), P(J["p10"]), P(J["p90"]), P(c1["E"]), P(c1["lo"]), P(c1["hi"]), P(c2["E"]), P(c2["lo"]), P(c2["hi"])))
    M = S["必報"]
    a("")
    a("H120（依構造不可判定，描述）：" + "；".join("{} n {:,} E {} 中位 {} p10 {} p90 {}".format(g, v["n"], P(v["E"]), P(v["中位"]), P(v["p10"]), P(v["p90"])) for g, v in M["H120_描述（依構造不可判定）"].items()))
    a("")
    a("描述臂 b（H5、H10）：" + "；".join("{} n {:,} E {}（{}～{}）".format(k, v["n"], P(v["E"]), P(v.get("lo")), P(v.get("hi"))) for k, v in M["描述臂b_H5_H10"].items()))
    a("")
    a("描述臂 a（鄰格全報）：" + "；".join("{} n {:,} E {}（{}～{}）".format(k, v["n"], P(v["E"]), P(v.get("lo")), P(v.get("hi"))) for k, v in M["描述臂a"].items()))
    a("")
    a("三訊號兩兩同日重疊（H20 保留事件）：" + "；".join("{} 同日 {:,}（{}）".format(k, v["同檔同日"], "、".join("{} {:.1%}".format(kk, vv) for kk, vv in v.items() if kk != "同檔同日")) for k, v in M["三訊號兩兩同日重疊（H20保留事件）"].items()))
    a("")
    a("分組（描述）：")
    for k, v in M["分組"].items():
        a("- {}：a 前60日三分位 {}｜b 標籤 {}｜c 門檻B後120日內 {}｜d 上市 {}／上櫃 {}".format(
            k, "、".join("{} {}（n {:,}）".format(q, P(x["E"]), x["n"]) for q, x in v["a_跌破前60日報酬三分位"].items()),
            "、".join("{} {}（n {:,}）".format(q, P(x.get("E")), x["n"]) for q, x in v["b_狀態標籤"].items()),
            "、".join("{} {}（n {:,}）".format(q, P(x.get("E")), x["n"]) for q, x in v["c_門檻B進場後120日內"].items()),
            P(v["d_上市上櫃"]["上市"]["E"]), P(v["d_上市上櫃"]["上櫃"]["E"])))
        a("  - 逐年：" + "、".join("{} {}".format(y, P(x["E"])) for y, x in v["d_逐年"].items()))
    a("")
    a("放棄組（續抱最後大漲 R ≥ p90 那批 vs 其餘）：")
    for k, v in M["放棄組_賣掉會錯過哪種"].items():
        t, r = v["續抱最後大漲（R≥p90）"], v["其餘"]
        a("- {}（p90 {}）：pre60 中位 {} vs {}；pre20 中位 {} vs {}；離線中位 {} vs {}；MA20 斜率中位 {} vs {}；偏跌比例 {:.1%} vs {:.1%}；上櫃 {:.1%} vs {:.1%}".format(
            k, P(v["p90門檻"]), P(t["pre60_中位"]), P(r["pre60_中位"]), P(t["pre20_中位"]), P(r["pre20_中位"]), P(t["離線_中位"]), P(r["離線_中位"]),
            P(t["MA20斜率_中位"]), P(r["MA20斜率_中位"]), t["狀態標籤"]["偏跌"], r["狀態標籤"]["偏跌"], t["上櫃比例"], r["上櫃比例"]))
    a("")
    a("## 五、0050 描述臂③（⛔ 不判、⛔ 不計 N）")
    for k, v in S["0050描述臂③"]["格"].items():
        a("- {}：n {}，E {}，中位 {}{}{}".format(k, v.get("n", 0), P(v.get("E")), P(v.get("中位")),
            "，CI {} ～ {}".format(P(v["lo"]), P(v["hi"])) if "lo" in v else "",
            "，n_eff {} ⇒ {} {}".format(v["n_eff"], v["出口"], v["結果"]) if "n_eff" in v else ("，" + v["註"] if "註" in v else "")))
    a("- 00631L：參考 0050 描述臂，未另測；00757、00910：本件未涵蓋 ⇒ 無法判定")
    a("")
    fd = json.load(open(os.path.join(OUT, "fake_diag.json"), encoding="utf-8"))
    ts = json.load(open(os.path.join(OUT, "tie_sensitivity.json"), encoding="utf-8"))
    a("## 六、假訊號臂的診斷（描述；⛔ 不改登錄的假訊號臂、⛔ 不進判定）")
    a("")
    a("登錄的假訊號臂（同檔、全窗、排除真事件前後 20 日）的假 E 遠高於真 E。診斷：同一套可落日【每一天】都當訊號日（不抽、不合併）：")
    a("")
    a("| 格 | 真 E | A 不排除 | B 排除前後 20 日（＝登錄母體） | C 只排除之前 20 日（不用未來） | D 只排除之後 20 日（用了未來） | 本體假 E |")
    a("|---|---:|---:|---:|---:|---:|---:|")
    for k, d in fd["格"].items():
        v = [d[x]["平均R"] for x in ("A 不排除", "B 排除前後各20日（登錄假訊號臂母體）", "C 只排除之前20日（不用未來）", "D 只排除之後20日（用了未來）")]
        a("| {} | {} | {} | {} | {} | {} | {} |".format(k, P(d["真E"], 3), *[P(x, 3) for x in v], P(d["假訊號臂平均E（本體）"], 3)))
    a("")
    a("⇒ 抬高假 E 的是「排除之後 20 日內有跌破的日子」（D ≫ A ≈ C）：未來 20 日沒有跌破的日子，本來就是之後走得好的日子 ⇒ 登錄那一欄的「真 E − 假 E」含前視選樣，⛔ 不宜照字面讀成「跌破之後比平常差這麼多」。"
      "不用未來的對照（A、C）下，真 E 仍低於同檔平常日，但差距小得多。判定不受影響（x／30 只影響結果③ 的措辭，而 6 格沒有結果③）。")
    a("")
    a("## 七、等號讀法（E2）的敏感度（描述）")
    for g in "甲乙丙":
        for H in (20, 60):
            x, y = ts["{}_H{}_全部".format(g, H)], ts["{}_H{}_剔除近似相等".format(g, H)]
            a("- {} H{}：全部 n {:,} E {}（{}～{}）｜剔除近似相等 n {:,} E {}（{}～{}）".format(g, H, x["n"], P(x["E"], 3), P(x["lo"], 3), P(x["hi"], 3), y["n"], P(y["E"], 3), P(y["lo"], 3), P(y["hi"], 3)))
    a("- ⚠ summary.json 的「敏感度_剔除近似相等事件後」為修正前程式所產（沒剔到任何一筆），以 tie_sensitivity.json 為準（程式已修；判定 6 格不受影響）")
    a("")
    a("## 八、查核")
    a("- 獨立重算（不 import 主程式）：{}；逐筆 R 重算最大差 {:.1e}".format(ck["判"], ck["逐筆R重算最大差"]))
    a("- 手算 20 筆（原始價＋還原因子，獨立讀 csv）：{}；路二（cum_factor）最大相對差 {}；路一（factor 自乘，只報）{}".format(
        hd["判"], {k: "{:.1e}".format(v) for k, v in hd["最大相對差"].items()}, {k: "{:.1e}".format(v) for k, v in hd["路一最大相對差"].items()}))
    a("- 本體重數的事件帳與區段數 ＝ 開跑前報（逐鍵相同）")
    a("")
    a("## 九、讀法（兩種讀法處選一種；⛔ 沒有改規則）")
    for t in READINGS:
        a("- " + t)
    a("")
    a("## 十、對照登錄 §八 先驗（只列事實，⛔ 不改先驗）")
    J6 = S["判定6格"]
    n3 = [k for k, v in J6.items() if v["結果"] == "結果③"]
    a("- 「6 格沒有一格落結果③」：{}（結果③ 格數 {}）".format("相符" if not n3 else "不符", len(n3)))
    a("- 「真 E − 假 E 三訊號都 ＜ 0」：H20 {}；⚠ 登錄假訊號臂含前視選樣（見六）".format("、".join("{} {}".format(g, P(J6[g + "_H20"]["假訊號"]["真E−假E"])) for g in "甲乙丙")))
    hi3 = M["分組"]["丙_H20"]["a_跌破前60日報酬三分位"]["高"]
    a("- 可否證句「漲一大段之後跌破 MA60（分組 a 最高三分位），續抱 H20 是負的」：最高三分位 n {:,}，E {}（描述 CI {} ～ {}）".format(hi3["n"], P(hi3["E"]), P(hi3["lo"]), P(hi3["hi"])))
    open(os.path.join(OUT, "EXIT_REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
