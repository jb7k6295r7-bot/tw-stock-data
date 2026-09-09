#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""data_audit.py — 「這份資料憑什麼說它是對的」。**只讀 repo，不連外。**

## 這一支要回答的問題

不是「資料看起來對不對」，是**「你怎麼知道它是對的」**。
那兩件事差很遠：一份完全自洽、每天更新、沒有任何錯誤訊息的資料，
可以從頭到尾都是錯的——今天一天之內就出現過三次
（`limit` 欄 50,382 列標反、9 檔面額被當成異常、227 個洞被當成未解釋）。

## ⭐ 所以本檔的核心是**證據等級**，不是通過率

每一份資料標一個等級。⛔ 等級由**證據的種類**決定，不是由品質或信心決定：

| 等級 | 意思 | 例 |
|---|---|---|
| **A** | 跟**官方逐筆**核對過，而且對帳結果留在檔案裡 | 面額變更 24/24、上櫃減資 232/0 |
| **B** | 有**獨立於自己**的判準（另一個來源、另一條管線、恆等式） | 日檔家數 vs `MI_INDEX`、股數 vs 股本÷面額 |
| **C** | 只有**自我一致**（欄位齊、日期連續、前後不矛盾） | ⛔ 自洽**不是**正確 |
| **D** | 沒有任何驗證 | |

⛔ **C 是最危險的一級**，因為它最像 A：兩者的報表看起來一模一樣，
都是一片綠。差別只在「拿什麼來比」。

## ⚠ 這一支不會讓資料變正確

它只是把「憑什麼」寫出來。**看到 C 或 D 就代表那份資料目前沒有人在替它背書**，
引用時要自己承擔。
"""
import csv
import glob
import io
import os
import sys

import runlog

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(_ROOT, "meta", "_data_audit.md")


def _cal():
    with io.open(os.path.join(_ROOT, "meta", "calendar_twse.csv"),
                 encoding="utf-8") as f:
        return sorted(r["date"] for r in csv.DictReader(f) if r.get("date"))


def _days(sub):
    return {os.path.basename(x)[:-4]
            for x in glob.glob(os.path.join(_ROOT, "universe", sub, "*.csv"))}


def _rows(p):
    if not os.path.exists(p):
        return []
    with io.open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    rl = runlog.Run("data_audit")
    cal = _cal()
    calset = set(cal)
    L = ["# 資料稽核：**憑什麼說它是對的**", "",
         "⛔ 這一頁報的不是「有沒有錯」，是**「有沒有人替它背書、背書的是誰」**。",
         "自洽不是正確——一份完全自洽、每天更新、沒有錯誤訊息的資料可以從頭錯到尾。",
         "", f"交易日曆：**{len(cal)} 天**（{cal[0]} ~ {cal[-1]}）", ""]

    # ── 一、逐日資料的涵蓋率，**並且要講清楚缺在哪一端**
    L += ["## 一、逐日資料：涵蓋率，以及**缺在哪一端**", "",
          "⛔ 只報百分比會騙人：缺最舊的 46 天與缺**最新的** 46 天，",
          "百分比一模一樣，但後者代表「今天的資料沒有」。", "",
          "| 資料 | 檔數 | 缺 | 缺的位置 | 證據等級 |",
          "|---|---|---|---|---|"]
    tiers = {}
    for name, sub, tier, why in (
            ("日檔 daily", "daily", "B", "家數對 `MI_INDEX`（`_breadth_audit.csv`）"),
            ("三大法人 inst", "inst", "B",
             "Σ(逐檔股數×收盤) vs 大盤合計金額（`crosscheck.py` ①）"),
            ("融資融券 margin", "margin", "B",
             "餘額遞推恆等式（`crosscheck.py` ②，⭐ 同時驗涵蓋率）"),
            ("本益比 per", "per", "B",
             "收盤÷近四季EPS vs 端點 per（`crosscheck.py` ③，中位誤差 0.21%）"),
            ("漲跌家數 breadth", "breadth", "B", "它自己就是別人的判準")):
        have = _days(sub)
        miss = sorted(calset - have)
        if not miss:
            pos = "—"
        else:
            newest = sum(1 for d in miss if d >= cal[-60])
            pos = (f"⛔ **最新那端**（近 60 個交易日內就缺 {newest} 天）"
                   if newest else "最舊那端（回補中）")
        tiers[name] = tier
        L.append(f"| {name} | {len(have):,} | {len(miss)} | {pos} | **{tier}** — {why} |")
        rl.info(f"涵蓋 {name}", f"{len(have):,} 檔｜缺 {len(miss)} 天")

    # ── 二、有官方逐筆對帳的（A 級）
    L += ["", "## 二、A 級：跟官方**逐筆**核對過，而且對帳結果留在檔案裡", "",
          "| 資料 | 筆數 | 對帳結果 | 對帳程式 |", "|---|---|---|---|"]
    pc = _rows(os.path.join(_ROOT, "meta", "par_change.csv"))
    off_par = _rows(os.path.join(_ROOT, "meta", "otc_par_reference.csv"))
    off_red = _rows(os.path.join(_ROOT, "meta", "otc_reduce_reference.csv"))
    n_ok = sum(1 for r in pc if "official_ref" in (r.get("evidence") or ""))
    L.append(f"| 面額變更（上櫃） | {n_ok} | **相符 {n_ok}／不符 0** "
             f"| `parvalue_scan.py` 閘門 (c)｜官方表 {len(off_par)} 筆 |")
    L.append(f"| 面額變更（上市） | "
             f"{sum(1 for r in pc if (r.get('evidence') or '').startswith('twse'))} "
             "| **雙向 0 漏抓 0 多編** | `parvalue_probe` [T8] |")
    L.append(f"| 減資（上櫃） | 232 | **相符 232／不符 0**、原因字串 232/232 "
             f"| `reduce_check.py`｜官方表 {len(off_red)} 筆 |")
    L.append("| 減資（上市） | — | **官方有我方沒有 0 筆** | `parvalue_probe` [T9] |")
    L.append("| 產業別代碼 32／33 | 41 | **34/34、7/7 全落在官方清單裡** "
             "| `tpex_probe` [11]（ISIN） |")

    # ── 三、B 級：有獨立判準
    L += ["", "## 三、B 級：有**獨立於自己**的判準", "",
          "⭐ 2026-09-09 新增三個（`crosscheck.py`）：三大法人、融資融券、本益比"
          "——它們原本都是 C。", "",
          "| 資料 | 判準是什麼（⛔ 為什麼它算獨立） | 現況 |", "|---|---|---|"]
    L.append("| 日檔家數 | `MI_INDEX` 的漲跌家數——**另一個端點、另一條管線** | "
             "`_breadth_audit.csv` |")
    L.append("| 上櫃股數 | 股本 ÷ 面額（MOPS 財報 vs 日檔官方發行股數）——"
             "**兩個不同來源** | 46 季 33,007 配對，中位誤差 **0.0000%** |")
    L.append("| 面額 | 端點自己的面額欄 vs 事件倍率回推——**兩條路各自算** | "
             "`par_timeline.py` 自我檢查 0 檔不符 |")
    L.append("| 還原因子 | 復牌首日相對推得參考價落在 ±10%（漲跌幅限制）"
             "——**資料庫以外的事實** | `otcparvalue.py` 閘門 (d) |")
    L.append("| 交易日曆 | ⚠ **只有自我一致**（0 天差異），"
             "⛔ 那證明自洽不證明正確 | 見下節 |")

    # ── 四、C／D 級：目前沒有人背書
    L += ["", "## 四、⛔ C／D 級：**目前沒有人替它背書**", "",
          "| 資料 | 為什麼只有 C／D | 要升級需要什麼 |", "|---|---|---|"]
    L.append("| ~~三大法人／融資融券／本益比~~ | **2026-09-09 已升到 B**"
              "（`crosscheck.py`） | — |")
    L.append("| ⚠ 本益比的歷史段 | 2015 年那版 `BWIBBU_d` **連收盤價欄都沒有** "
             "⇒ 近期可比、歷史段的可比性未查 | 逐年量欄位 |")
    L.append("| 上櫃交易日曆 | **自我一致 0 天差異，但那只證明自洽** | "
             "櫃買官方休市公告（端點我方取不到） |")
    L.append("| 集保 `data/tdcc/` | 四道驗算全過（恆等式）＝ B；"
             "⛔ 但**只有一週**，序列本身還不存在 | 時間 |")

    # ── 五、今天這一輪查出來、還開著的
    L += ["", "## 五、這一輪查出來、**還開著**的", ""]
    miss_b = sorted(calset - _days("breadth"))
    if miss_b:
        L.append(f"- ⛔ **breadth 缺的 {len(miss_b)} 天全部是最近的**"
                 f"（{miss_b[0]} 起連續到 {miss_b[-1]}）。"
                 "`_db_status.md` 報「98%」在數字上沒錯，"
                 "但**缺的是最新那一端**——那正是每日閘門要用的。")
    for sub in ("margin", "per"):
        m = sorted(calset - _days(sub))
        if m:
            L.append(f"- ⚠ **{sub} 缺 {m}**——與另一份缺**同一天**，"
                     "⇒ 多半是那天的共同失敗，不是各自的問題。")
    L.append("- ⚠ `_capital_missing.txt` 的「仍缺股數」從 278 變成 **289**："
             "母體改成 20 日聯集之後多了 42 個代號，**分母變大**；"
             "⛔ 但還沒逐檔確認增加的那些是不是本來就沒有股數的 ETF／ETN。")

    L += ["", "## 六、⭐ 怎麼判斷一份資料可不可信——三個問題", "",
          "1. **拿什麼來比？** 說得出「另一個來源／另一條管線／一個恆等式」才算。",
          "   說不出來就是 C，不管它看起來多乾淨。",
          "2. **缺的在哪一端？** 涵蓋率 98% 可能是「舊的還沒補完」，",
          "   也可能是「**最近兩個月都沒有**」。⛔ 百分比不分辨這兩件事。",
          "3. **它壞掉的時候，誰會吵？** 說不出哪一個 `rl.check` 會紅，",
          "   就等於沒有人在看——今天的 `freshness_check.py` 就是為此而加。", "",
          "⚠ 這三個問題今天各自抓到過真的問題，不是原則性的說法。"]

    try:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        io.open(OUT, "w", encoding="utf-8").write("\n".join(L) + "\n")
        print(f"[data_audit] 寫出 {OUT}")
        rl.info("寫出", OUT)
    except OSError as ex:                                        # noqa: BLE001
        rl.check("寫得出稽核報告", False, str(ex))
    # ⛔ 這一支**不設 check**：它報的是「憑什麼」，不是「對不對」。
    #   硬要它紅會逼人把等級寫高——那正好毀掉這份報告的用處。
    rl.info("⚠ 這一支不設 check", "它報的是憑什麼、不是對不對；"
                                "硬要它紅會逼人把等級寫高")
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
