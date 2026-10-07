# -*- coding: utf-8 -*-
"""USREG-A4 彙總：REPORT.md、summary.json、GICS 對照表、HTML「美股季財報選股十二件.html」（繁體中文、白話、結論先講）。

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSA4_page
只讀 resultsUSA34/A4/*.json 與 check.json（彙總）；⛔ 不寫任何逐日價格、財報原值、逐筆明細。
"""
from __future__ import annotations

import html
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchUSA4 as C
from backtest import researchUSA4_gics as GICS

OUT = C.OUT
H = html.escape


def J(name):
    p = os.path.join(OUT, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def pc(x, d=1):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else ("%+.*f%%" % (d, 100 * x))


def f2(x):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else "%.2f" % x


def cell3(st):
    """book／slot stats ⇒ (年化, 回落, 比值, 標籤)。"""
    if st is None:
        return (None, None, None, "—")
    c = st.get("年化", st.get("年化中位")); m = st.get("回落", st.get("回落中位"))
    return (c, m, st.get("比值"), st.get("標籤", "—"))


def units():
    """每個判定單位：件、名稱、挑中格、段、三欄 stats、標籤、N、條件出場量、前綴。"""
    U_ = []
    d = J("A4-1.json")
    if d:
        for fam in ("甲", "乙"):
            D = d["族"][fam]; ch = D["挑中格"]
            U_.append({"件": "A4-1", "名稱": "品質因子 %s族（%s）" % (fam, "單用" if fam == "甲" else "8 季新高池內"),
                       "挑中格": "%s %s N%d" % (ch["Qk"], ch["頻率"], ch["N"]), "段": "確認",
                       "欄": {p: D["判定"]["欄"][p]["確認"] for p in C.COLS}, "標籤": D["標籤"], "N": 1,
                       "持有": dict(D["判定"]["欄"]["合併"]["確認"], 窗尾=D["判定"]["欄"]["合併"].get("窗尾仍持有（檔）")), "p": D.get("同池隨機", {}).get("p_確認")})
    d = J("A4-2.json")
    FU = J("followup.json") or {}
    if d:
        for nm, T in d["套"].items():
            fk = (FU.get("A4-2 " + nm) or {}).get("合併", {}).get("假訊號（同日同池隨機一檔、持有區間不變）")
            if fk and fk["合格比例"] >= 0.05:
                T["前綴"] = ("%s；" % T["前綴"] if T.get("前綴") else "") + "⚠ 隨機也有 %.1f%% 合格（假訊號 1,000 次）" % (100 * fk["合格比例"])
            U_.append({"件": "A4-2", "名稱": "仿 App %s條件" % nm, "挑中格": "不再符合才換、10 檔", "段": "確認",
                       "欄": {p: T["欄"][p]["main"]["確認"] for p in C.COLS}, "標籤": T["標籤"], "N": 1, "前綴": T.get("前綴", ""),
                       "持有": (lambda h: dict(h, 窗尾=h.get("窗尾仍持有（筆，2026-09-30 收盤結算）")))((T.get("持有分佈（合併主臂、種子102000實際成交）") or {}).get("確認", {}))})
    d = J("A4-3.json")
    if d:
        for x in ("X1", "X2"):
            D = d[x]
            U_.append({"件": "A4-3", "名稱": {"X1": "X1 多因子（FinLab）", "X2": "X2 CGO＋低波動（TEJ）"}[x],
                       "挑中格": D["判定"]["格"], "段": "全窗", "欄": {p: D["判定"]["欄"][p]["全窗"] for p in C.COLS},
                       "標籤": D["標籤（全窗，P12）"], "N": 1, "持有": dict(D["判定"]["欄"]["合併"]["全窗"], 窗尾=D["判定"]["欄"]["合併"].get("窗尾仍持有（檔）"))})
        X3 = d["X3"]["H20"]
        U_.append({"件": "A4-3", "名稱": "X3 季營收創紀錄（事件，20 日）", "挑中格": "公告次日買、抱 20 日、對母體等權", "段": "全窗",
                   "事件": {p: X3[p] for p in C.COLS}, "標籤": d["X3"]["標籤"], "N": 1})
    d = J("A4-4.json")
    if d:
        for fam in ("甲", "乙"):
            D = d["族"][fam]; ch = D["挑中格"]
            U_.append({"件": "A4-4", "名稱": "低週轉 %s族" % fam, "挑中格": "TO(%d) %s N%d" % (ch["L"], ch["頻率"], ch["N"]), "段": "確認",
                       "欄": {p: D["判定"]["欄"][p]["確認"] for p in C.COLS}, "標籤": D["標籤"], "N": 1 if fam == "甲" else 0,
                       "持有": dict(D["判定"]["欄"]["合併"]["確認"], 窗尾=D["判定"]["欄"]["合併"].get("窗尾仍持有（檔）")), "p": D.get("同池隨機", {}).get("p_確認")})
    for it, nm in (("A4-5", "強勢類股（熱力圖邏輯）"), ("A4-12", "十一票等權投票")):
        d = J(it + ".json")
        if d:
            ch = d["挑中格"]
            U_.append({"件": it, "名稱": nm, "挑中格": " ".join("%s%s" % (k, v) for k, v in ch.items()), "段": "確認",
                       "欄": {p: d["判定"]["欄"][p]["確認"] for p in C.COLS}, "標籤": d["標籤"], "N": 1, "持有": dict(d["判定"]["欄"]["合併"]["確認"], 窗尾=d["判定"]["欄"]["合併"].get("窗尾仍持有（檔）")),
                       "p": (d.get("隨機挑類股") or d.get("丙 隨機挑同檔數") or {}).get("p_確認")})
    d = J("A4-6.json")
    if d:
        ch = d["挑中格"]
        U_.append({"件": "A4-6", "名稱": "產業營收加速（季版）", "挑中格": "%s K%d %s %s %s" % (ch["A"], ch["K"], ch["S"], ch["R"], ch["E"]), "段": "確認",
                   "欄": {p: d["判定"]["欄"][p]["確認"] for p in C.COLS}, "標籤": d["標籤"], "N": 1, "持有": dict(d["判定"]["欄"]["合併"]["確認"], 窗尾=d["判定"]["欄"]["合併"].get("窗尾仍持有（檔）")),
                   "p": d.get("隨機挑產業", {}).get("p_確認")})
    d = J("A4-7.json")
    if d:
        for key, nm in (("庫藏股代理（每季前10%）", "庫藏股代理（季買回占市值前 10%）"), ("成分剔除", "指數成分剔除")):
            P = d[key]["組合層"]
            hh = P.get("挑中H")
            U_.append({"件": "A4-7", "名稱": nm, "挑中格": ("10 檔、抱 %s 日" % hh) if hh else "—", "段": "確認",
                       "欄": {p: P["全表"].get("H%s|%s" % (hh, p), {}).get("確認") for p in C.COLS} if hh else {}, "標籤": P.get("標籤"), "N": 1})
    d = J("A4-9.json")
    if d:
        ma = d.get("挑中格", "—")
        L = ma.replace("跌破 MA", "") if isinstance(ma, str) else ""
        U_.append({"件": "A4-9", "名稱": "年線戰法基本面季版", "挑中格": ma, "段": "確認",
                   "欄": {p: d["全表"].get("MA%s|%s" % (L, p), {}).get("確認") for p in C.COLS}, "標籤": d.get("標籤"), "N": 1,
                   "持有": (lambda h: dict(h, 窗尾=h.get("窗尾仍持有（筆，2026-09-30 收盤結算）")))((d.get("持有分佈（合併、種子102000）") or {}).get("確認", {}))})
    d = J("A4-11.json")
    if d:
        ch = d["挑中格"]
        U_.append({"件": "A4-11", "名稱": "機器學習改目標（numpy）", "挑中格": "目%s %s %s N%d" % (ch["目標"], ch["模型"], ch["頻率"], ch["N"]), "段": "確認",
                   "欄": {p: d["判定"]["欄"][p]["確認"] for p in C.COLS}, "標籤": d["標籤"], "N": 1, "持有": dict(d["判定"]["欄"]["合併"]["確認"], 窗尾=d["判定"]["欄"]["合併"].get("窗尾仍持有（檔）")),
                   "p": d.get("同池隨機", {}).get("p_確認")})
    d = J("A4-13.json")
    if d:
        for i, k in enumerate(d["線索"]):
            T = d["確認"][k]
            U_.append({"件": "A4-13", "名稱": "探索批線索 %d：%s" % (i + 1, k), "挑中格": "8 檔、第 120 根收盤出", "段": "確認",
                       "欄": {"合併": T["合併"], "只400": T["只400"], "只500": T["只500（描述）"]}, "標籤": T["標籤"], "N": 1})
        if not d["線索"]:
            best = sorted(d["探索全表"].items(), key=lambda kv: -kv[1]["年化中位"])[0]
            U_.append({"件": "A4-13", "名稱": "探索批：0 條線索（105 格探索段年化都沒贏 ^SP500TR；最好 %s %s）" % (best[0], pc(best[1]["年化中位"])),
                       "挑中格": "—（依原登錄 §四③「不足 5 有幾條算幾條」⇒ 0 條、確認段不跑）", "段": "探索",
                       "欄": {"合併": best[1]}, "標籤": "無線索（不可判定）", "N": 0})
    return U_


def main(a=None):
    cal, w0, w1, sp, c0 = C.setup_cal()
    BM = C.bench_metrics(cal, {"探索": (w0, sp), "確認": (c0, w1), "全窗": (w0, w1)})
    CK = J("check.json") or {}
    UN = units()
    S10 = J("A4-10.json")
    # GICS 對照表（公開資訊：名稱 ⇒ group）
    gm = pd.DataFrame(sorted([(k, v) for k, v in GICS._MAP.items() if v is not None]), columns=["sub-industry（正規化名稱）", "industry group（2023 名稱）"])
    gm.to_csv(os.path.join(OUT, "GICS_industry_group對照表.csv"), index=False, encoding="utf-8-sig")
    # N
    Ntot = sum(u["N"] for u in UN)
    cov = CK.get("K3_GICS對照率", {})
    k4 = CK.get("K4_基準", {})
    k4ok = all(abs(k4.get(s, {}).get("年化", 9) - BM[s]["年化"]) < 1e-9 and abs(k4.get(s, {}).get("回落", 9) - BM[s]["回落"]) < 1e-9 for s in BM) if k4 else None
    summ = {"件": [], "N實數（不含 A4-10）": Ntot, "A4-10": "待裁定（探索段挑出 %s 個特徵級距；N ＝ 驗證段實際驗的數）" % (S10["挑出數"] if S10 else "—"),
            "基準": BM, "GICS對照率": cov, "查核": {"K1不同": CK.get("K1_季財報與市值", {}).get("不同"), "K2全同": CK.get("總結", {}).get("K2全同"),
                                                "K4基準相同": k4ok}}
    for u in UN:
        row = {"件": u["件"], "名稱": u["名稱"], "挑中格": u["挑中格"], "判定段": u["段"], "標籤": u["標籤"], "N": u["N"]}
        if "欄" in u:
            for p in C.COLS:
                c_, m_, r_, l_ = cell3(u["欄"].get(p))
                row[p] = {"年化": c_, "回落": m_, "比值": r_, "標籤": l_}
        if "事件" in u:
            for p in C.COLS:
                s = u["事件"][p]
                row[p] = {"平均超額": s.get("平均"), "CI": [s.get("lo"), s.get("hi")], "n": s.get("n"), "n_eff": s.get("n_eff"), "判語": s.get("判語")}
        if u.get("持有"):
            h = u["持有"]
            row["條件出場"] = {k: h.get(k) for k in ("持有天數_平均", "持有天數_中位", "持有天數_p10", "持有天數_p90", "持有天數_最長", "離頂多近_中位")}
            row["條件出場"]["窗尾仍持有"] = h.get("窗尾")
        if u.get("p") is not None:
            row["隨機對照p"] = u["p"]
        summ["件"].append(row)
    C.jdump(summ, os.path.join(OUT, "summary.json"))
    md = report_md(UN, BM, CK, S10, Ntot, cov, k4ok)
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write(md)
    open(os.path.join(OUT, "美股季財報選股十二件.html"), "w", encoding="utf-8").write(page_html(UN, BM, S10, Ntot, cov))
    print("[page] 完成：判定單位 %d、N %d" % (len(UN), Ntot))


def lab_count(UN):
    from collections import Counter
    return Counter(u["標籤"] for u in UN if u["N"] or u["件"] == "A4-4")


def report_md(UN, BM, CK, S10, Ntot, cov, k4ok):
    L = []
    L.append("# USREG-A4 交件：美股季財報選股十二件（A4-1～7、A4-9～13）")
    L.append("")
    L.append("**回測線計算子代理｜讀法寫死 %s｜算於 %s｜資料 us-stock-data 881c86a9a7**" % (C.READ_TS, C.now_tpe()))
    L.append("依據：登錄 USREG-A3A4 seq1（sha 0dc16d3267725d7c）＋seq2（sha bc0927fed5996fd4）；裁定 seq318、seq319（Q1、Q6～Q10、Q14～Q16）、seq316。")
    L.append("")
    L.append("## 一、結論")
    L.append("")
    lc = lab_count(UN)
    L.append("- 判定單位 %d 個（A4-4 兩族共計 1、A4-10 待裁定），**N 實數 %d**（A4-13 0 條線索、A4-10 挑出 0 個 ⇒ 都記 0、請裁定；若 A4-13 照登錄記 5 則為 21）。標籤分佈：%s。" % (len(UN), Ntot, "、".join("%s %d" % (k, v) for k, v in lc.items())))
    L.append("- 判定口徑：探索段挑格（合併欄）、確認段判；只 S&P 400 與合併兩欄都過才「合格」，只合併過 ⇒「事後擴母體」（最多暫定）；美股沒有早年段 ⇒ 標「缺早年段」。")
    L.append("- 基準 ^SP500TR：探索 %s／%s、確認 %s／%s、全窗 %s／%s。" % (pc(BM["探索"]["年化"]), pc(BM["探索"]["回落"]), pc(BM["確認"]["年化"]), pc(BM["確認"]["回落"]),
                                                                pc(BM["全窗"]["年化"]), pc(BM["全窗"]["回落"])))
    L.append("- 每件結果句都標「%s」；%s。" % (C.IDEA, C.SURV))
    L.append("")
    L.append("## 二、逐件（判定段；年化／回落／比值／標籤）")
    L.append("")
    L.append("| 件 | 判定單位 | 挑中格 | 段 | 只 S&P 400 | 合併 | 只 S&P 500（描述） | 標籤 | N |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for u in UN:
        if "事件" in u:
            cells = []
            for p in ("只400", "合併", "只500"):
                s = u["事件"][p]
                cells.append("平均超額 %s（CI %s～%s，n_eff %s）%s" % (pc(s.get("平均"), 2), pc(s.get("lo"), 2), pc(s.get("hi"), 2), s.get("n_eff", "—"), s.get("判語", "")))
        else:
            cells = []
            for p in ("只400", "合併", "只500"):
                c_, m_, r_, l_ = cell3(u.get("欄", {}).get(p))
                cells.append("%s／%s／%s／%s" % (pc(c_), pc(m_), f2(r_), l_))
        L.append("| %s | %s%s | %s | %s | %s | %s | %s | **%s** | %s |" % (u["件"], ("〔%s〕" % u["前綴"]) if u.get("前綴") else "", u["名稱"], u["挑中格"], u["段"],
                                                                       cells[0], cells[1], cells[2], u["標籤"], u["N"]))
    L.append("")
    L.append("## 三、條件出場必報（合併欄、判定段；⛔ 不設最長天數；看離頂多近、不看抱幾天）")
    L.append("")
    L.append("| 件 | 單位 | 持有天數 平均／中位／p10／p90／最長（交易日） | 離頂多近（中位） | 窗尾仍持有（2026-09-30 收盤結算） |")
    L.append("|---|---|---|---|---|")
    for u in UN:
        h = u.get("持有")
        if not h:
            continue
        L.append("| %s | %s | %s／%s／%s／%s／%s | %s | %s |" % (u["件"], u["名稱"], f2(h.get("持有天數_平均")), f2(h.get("持有天數_中位")), f2(h.get("持有天數_p10")),
                                                         f2(h.get("持有天數_p90")), f2(h.get("持有天數_最長")), pc(h.get("離頂多近_中位")), h.get("窗尾", "—")))
    L.append("")
    L.append("## 四、A4-10 飆股季財報特徵（探索段 2021～2023 挑出、⛔ 未開驗證段，待裁定）")
    L.append("")
    if S10:
        L.append("- 網格 250 格（美股母體重算，⛔ 不搬台股門檻）；股-日 %s 列；挑選規則 ≥125 格「① 下緣 ＞1 且 ② ≥5%%」。" % S10["股-日列數"])
        L.append("- 挑出 %d 個特徵級距：" % S10["挑出數"])
        for s in S10["挑出的特徵級距（待裁定）"]:
            L.append("  - %s %s：過 %d／250 格；提升倍數網格中位 %s、涵蓋率網格中位 %s" % (s["特徵"], s["級距"], s["過的格數（/250）"], f2(s["①提升倍數_網格中位"]), pc(s["②涵蓋率_網格中位"])))
        L.append("- 全部級距見 `A4-10_探索段_特徵級距.csv`；網格事件數見 `A4-10_探索段_網格事件數.csv`。")
    L.append("")
    FU = J("followup.json") or {}
    L.append("## 四之二、跟進出場敏感度（seq242 ②：合併欄合格／另列者；描述、⛔ 不判、不計 N；確認段）")
    L.append("")
    for k, v in FU.items():
        if not isinstance(v, dict):
            continue
        for pop, arms in v.items():
            parts = []
            for an, st in arms.items():
                if "合格比例" in st:
                    parts.append("%s：合格比例 %.1f%%、假年化中位 %s、p %s" % (an, 100 * st["合格比例"], pc(st["年化中位"]), f2(st["p（假 ≥ 真年化中位）"])))
                else:
                    c_ = st.get("年化", st.get("年化中位")); m_ = st.get("回落", st.get("回落中位"))
                    parts.append("%s %s／%s %s" % (an, pc(c_), pc(m_), st.get("標籤", "")))
            L.append("- %s｜%s：%s" % (k, pop, "；".join(parts)))
    d11 = J("A4-11.json")
    if d11 and d11["判定"].get("跟進出場敏感度（描述）"):
        for pop, arms in d11["判定"]["跟進出場敏感度（描述）"].items():
            L.append("- A4-11｜%s：%s" % (pop, "；".join("%s %s／%s %s" % (an, pc(st["年化"]), pc(st["回落"]), st["標籤"]) for an, st in arms.items())))
    L.append("- A4-6（合併合格）：產業層 E0～E3 出場臂本身就是登錄的出場網格，⛔ 未另加個股停損／檔數敏感度（照實寫）。")
    L.append("")
    L.append("## 五、GICS industry group 對照率（seq319 Q8；先報再算）")
    L.append("")
    for k, v in cov.items():
        L.append("- %s：有 sub-industry 名稱的在指數股-月 %s 中對得上 %s（%s）；占全部在指數股-月 %s ⇒ ≥95%%，用 industry group（25 類）。" % (
            k, v.get("有sub-industry的股月"), v.get("對得上"), pc(v.get("對照率（有名稱者）"), 2), pc(v.get("占全部在指數股月"), 2)))
    L.append("- 對照表 `GICS_industry_group對照表.csv`（執行者依 GICS 2016／2018／2023 官方結構手寫；⚠ B3 本身是 Wikipedia 近似、非官方）。")
    L.append("")
    L.append("## 六、偏離與補讀法（詳見程式 docstring）")
    L.append("")
    for s in DEVS:
        L.append("- " + s)
    L.append("")
    L.append("## 七、查核（researchUSA4_check.py，獨立寫法）")
    L.append("")
    k1 = CK.get("K1_季財報與市值", {})
    L.append("- K1 季財報與市值：抽 %s 列、比 %s 個量 ⇒ 不同 %s。" % (k1.get("抽樣列"), k1.get("比較數"), k1.get("不同")))
    for k, v in CK.get("K2_換股簿引擎", {}).items():
        L.append("- K2 %s：獨立逐日迴圈確認段年化 %s vs 本體 %s ⇒ %s。" % (k, pc(v["確認段年化_查核"], 4), pc(v["確認段年化_本體"], 4), "相同" if v["相同(≤1e-9)"] else "⚠ 不同"))
    L.append("- K3 GICS 對照率：獨立重算（數字同上節）。")
    L.append("- K4 ^SP500TR 三段：獨立讀 macro CSV ⇒ %s。" % ("與本體相同" if k4ok else "⚠ 不同"))
    L.append("")
    L.append("## 八、檔案")
    L.append("")
    L.append("- 程式：backtest/researchUSA4.py（底座、G1～G16）、researchUSA4_items.py（各件 I1～I21）、researchUSA4_ml.py（A4-11 M1～M7）、researchUSA4_surge.py（A4-10 S1～S6）、"
             "researchUSA4_gics.py（G15 對照表）、researchUSA4_check.py、researchUSA4_page.py")
    L.append("- 結果：resultsUSA34/A4/（A4-*.json、summary.json、check.json、REPORT.md、HTML、GICS 對照表、A4-10 兩個 csv）；逐股中間檔只在 ~/us_work/a4/（repo 外）。")
    L.append("- ⛔ 結果夾只有彙總（年化、回落、比值、件數、比例、CI、判語）；沒有逐日價格、財報原值、逐筆成交。")
    return "\n".join(L) + "\n"


DEVS = [
    "A4-13：探索段 105 格（2016～2021）沒有一格年化贏 ^SP500TR（最好 F04＋F10 +16.8% 對 +17.7%）⇒ 依原登錄 §四③「不足 5 有幾條算幾條」0 條線索、確認段不跑；登錄 N 5、實際驗 0（請裁定 N 怎麼記）。S0 確認段仍照跑（描述）。",
    "A4-10：250 格中 194 格事件 ＜30（網格事件數中位 3；美股大中型股很少短期翻倍）⇒ 沒有任何特徵級距達到「≥125 格站得住」，挑出 0 個；N 待裁定（實際 0）。",
    "P8 市值實作改正（照 P8 文字）：prices_yahoo 的 close 已按日後拆股調整，prep 直接當原始收盤 ⇒ 日後有拆股的股票市值被低估（面板 8.6% 股-月市值與 prep 不同，99 分位差 10 倍）；"
    "本件用 Yahoo close × 日後拆股比（Tiingo 本來就是原始）。影響 A4-2 本益比、A4-6 市值排序、A4-7 買回比、A4-13 F16／F18、A4-11 logcap；覆蓋率不變。",
    "代號重用 8 檔（AZPN COHR CR CZR HR RBC RCM VAL）依日期挑 CIK（G9）；prep 的面板沒分段 ⇒ 本件季財報量與 prep 有 0.2% 股-月不同。",
    "A4-3 X1：60 日報酬與波動用還原價（原文用未還原；美股未還原價有拆股跳動）；換股日 ＝ 月底後第一個交易日（原文延後 14 天是為月營收；prep 已改 first_filed）。",
    "A4-3 X2：CGO 的 P ＝（高＋低＋收）÷3、V 的股數用換股日的今日基準股數（100 日內不變）；主臂改換股簿「不再符合才換」（50 檔）。",
    "A4-7 庫藏股「每季前 10%」門檻用【前一曆季】那組的第 90 百分位（同季要等全部申報完 ⇒ 避免前視）。成分剔除照 P11 含 S&P 400 升級到 S&P 500 的剔除；另報排除升級的描述版。",
    "A4-10 事件鏈只在母體列（在指數的日子）上走；③ 可交易曲線、妖股、結束特徵本步不做（Q16 只准探索段挑特徵）。",
    "A4-11 一個模型（合併母體訓練）三欄共用、選股只取該欄母體；基準報酬用 ^SP500TR 收盤（e−1 代 e 開盤）；訓練起點依台股同規則（r12s 可算 ≥50%）落在 2017 初、比台股晚。",
    "A4-13 運氣基準（丙）假條件每個用 50 顆種子（台股 200 顆；只影響「與運氣分不開」標記、⛔ 不淘汰線索）。",
    "A4-13 主臂照原文 8 槽、第 120 根收盤出（原文寫死天數，登錄 §〇）；未另跑「不再符合才換」版。",
    "換股簿型（選股類）持股遇轉接層斷點 ⇒ 前一日收盤結清；槽位型訊號持有期碰斷點 ⇒ 剔除（W1b W5）。",
    "固定 {20,60,120,240} 日描述臂：換股簿型 ＝ 新進者抱滿 H 根收盤賣、空槽到下個換股日補；X1（權重型）未做固定天數描述。",
    "A4-2、A4-7、A4-9、A4-13 用 research11.simulate_mtm（200 顆種子中位）；其餘選股類是決定性排名 ⇒ 單一條權益（台股原件同）。",
]


def page_html(UN, BM, S10, Ntot, cov):
    css = """
:root{--bg:#fbfaf7;--fg:#1d1d1f;--muted:#5f6368;--card:#ffffff;--line:#e3e1dc;--ok:#1a7f37;--warn:#9a6700;--bad:#b42318;--accent:#2f5aa8}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#16171a;--fg:#e8e6e1;--muted:#a3a7ad;--card:#1f2125;--line:#33363b;--ok:#4cc16a;--warn:#e0b44c;--bad:#f07167;--accent:#7aa2f7}}
:root[data-theme="dark"]{--bg:#16171a;--fg:#e8e6e1;--muted:#a3a7ad;--card:#1f2125;--line:#33363b;--ok:#4cc16a;--warn:#e0b44c;--bad:#f07167;--accent:#7aa2f7}
body{background:var(--bg);color:var(--fg);font-family:-apple-system,"Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif;line-height:1.65;margin:0;padding:16px}
main{max-width:980px;margin:0 auto}h1{font-size:1.45rem;margin:.2em 0}h2{font-size:1.15rem;margin-top:1.6em;border-bottom:1px solid var(--line);padding-bottom:.2em}
.lead{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}.muted{color:var(--muted);font-size:.9rem}
.tw{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:.88rem;background:var(--card)}th,td{border:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
th{background:var(--bg)}.ok{color:var(--ok);font-weight:600}.warn{color:var(--warn);font-weight:600}.bad{color:var(--bad)}.tag{display:inline-block;border-radius:6px;padding:0 6px;border:1px solid var(--line)}
"""
    def cls(l):
        l = l or ""
        return "ok" if l == "合格" else ("warn" if ("事後擴母體" in l or "另列" in l or "測得出（＋）" in l) else "bad")
    lc = lab_count(UN)
    good = [u for u in UN if u["標籤"] in ("合格",)]
    semi = [u for u in UN if ("事後擴母體" in (u["標籤"] or "")) or (u["標籤"] or "").startswith("另列")]
    rows = []
    for u in UN:
        if "事件" in u:
            cs = []
            for p in ("只400", "合併", "只500"):
                s = u["事件"][p]
                cs.append("20 日超額 %s<br><span class='muted'>CI %s～%s</span>" % (pc(s.get("平均"), 2), pc(s.get("lo"), 2), pc(s.get("hi"), 2)))
        else:
            cs = []
            for p in ("只400", "合併", "只500"):
                c_, m_, r_, l_ = cell3(u.get("欄", {}).get(p))
                cs.append("%s／%s<br><span class='muted'>%s</span>" % (pc(c_), pc(m_), H(l_ or "—")))
        pre = ("<b>%s</b>：" % H(u["前綴"])) if u.get("前綴") else ""
        rows.append("<tr><td>%s</td><td>%s%s<br><span class='muted'>%s</span></td><td>%s</td><td>%s</td><td>%s</td><td><span class='tag %s'>%s</span></td></tr>" % (
            H(u["件"]), pre, H(u["名稱"]), H(u["挑中格"]), cs[0], cs[1], cs[2], cls(u["標籤"]), H(u["標籤"] or "—")))
    s10 = ""
    if S10:
        items = "".join("<li>%s %s：250 格中 %d 格站得住；比一般股票多變飆股 %s 倍（網格中位）、飆股裡有這個特徵的占 %s</li>" % (
            H(s["特徵"]), H(s["級距"]), s["過的格數（/250）"], f2(s["①提升倍數_網格中位"]), pc(s["②涵蓋率_網格中位"])) for s in S10["挑出的特徵級距（待裁定）"])
        s10 = "<p>在 2021～2023 年的美股裡，用季財報找「起漲前比較常見」的特徵，挑出 %d 個（還沒用 2024 以後的資料驗證，等裁定）：</p><ul>%s</ul>" % (S10["挑出數"], items or "<li>沒有任何特徵過門檻</li>")
    covs = "；".join("%s %s" % (k, pc(v.get("對照率（有名稱者）"), 2)) for k, v in cov.items())
    first = ("<b>%d 個判定單位裡，兩個母體都過的「合格」有 %d 個</b>%s。" % (len(UN), len(good), ("：" + "、".join(H(u["件"] + " " + u["名稱"] + ("（%s；算法照本線定義、不保證與 App 相同）" % u["前綴"] if u.get("前綴") else "")) for u in good)) if good else "")) + \
            ("另有 %d 個只在合併母體過（事後擴母體或另列，最多暫定）：%s。" % (len(semi), "、".join(H(u["件"] + " " + u["名稱"]) for u in semi)) if semi else "其餘都沒有贏過 ^SP500TR。")
    body = f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>美股季財報選股十二件</title><style>{css}</style></head><body><main>
<h1>美股季財報選股十二件（USREG-A4）</h1>
<p class="muted">回測線｜讀法寫死 {H(C.READ_TS)}｜算於 {H(C.now_tpe())}｜資料 us-stock-data 881c86a9a7｜{H(C.IDEA)}</p>
<div class="lead"><p>{first}</p>
<p>比的是同期 S&amp;P 500 含息指數（^SP500TR）：2022～2026-09 確認段年化 {pc(BM['確認']['年化'])}、最大回落 {pc(BM['確認']['回落'])}。要贏，得「報酬比它高」而且「報酬÷回落不比它差」。</p>
<p class="muted">N 實數 {Ntot}（A4-13 探索段 0 條線索、A4-10 挑出 0 個特徵，都記 0、待裁定）。美股沒有台股那種早年資料 ⇒ 每件都是「缺早年段」；{H(C.SURV)}。用到「創 8 季新高」的件：{H(C.Q14)}。</p></div>
<h2>一、每件結果</h2>
<p class="muted">格子裡是「年化／最大回落」與該欄標籤；只 S&amp;P 500 一欄只當參考。判定段：多數是 2022-01～2026-09；A4-3 X1～X3 是全窗 2016～2026-09（原文期間是台股的，美股全都沒看過）。</p>
<div class="tw"><table><thead><tr><th>件</th><th>做法</th><th>挑中的設定</th><th>只 S&amp;P 400</th><th>合併</th><th>只 S&amp;P 500</th><th>標籤</th></tr></thead><tbody>
{''.join(rows)}</tbody></table></div>
<h2>二、飆股的季財報特徵（A4-10，待裁定）</h2>{s10}
<h2>三、怎麼算的（白話）</h2>
<ul><li>每件都先在 2016～2021（A4-2 從 2018-03、A4-11 從 2019）挑一個設定，再拿 2022～2026-09 沒看過的年份判。</li>
<li>只在 S&amp;P 400 與合併（500＋400）兩邊都贏才算「合格」；只有合併贏 ⇒「事後擴母體」，最多暫定。</li>
<li>選股類都是「不再符合才換」：每次換股時還在名單裡就續抱、掉出名單才賣；條件出場沒有最長天數。</li>
<li>類股用 GICS industry group（25 類），由 sub-industry 對官方結構推得，對照率 {H(covs)}。</li>
<li>成本來回 0.05%；起漲、產業、財報都只用當時看得到的資料（季報以 SEC 第一次申報的隔天起算）。</li></ul>
<p class="muted">這是全部選到的股票平均起來的結果，不是對某一檔的預測。詳細數字見同資料夾 REPORT.md 與 A4-*.json。</p>
</main></body></html>"""
    return body


if __name__ == "__main__":
    main()
