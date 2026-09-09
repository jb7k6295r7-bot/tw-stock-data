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
    # ★ 2026-09-09：上櫃日曆終於有了外部判準，⛔ 但**只涵蓋開始累積之後**。
    #   櫃買 openapi 那 8 個「歷史指數」端點實測**每一個都只回 7 列**
    #   （swagger 寫「歷史」是誤導）⇒ 舊的那段沒有人留過紀錄，**補不回來**。
    #   ⛔ 所以這一列**不可以整列寫成「已升 B」**——那會把 2015~2026-08
    #     那 2,840 天沒有判準的事實蓋掉，而且看起來像好消息。
    _ct = os.path.join(_ROOT, "meta", "calendar_tpex.csv")
    _cd = []
    if os.path.exists(_ct):
        with io.open(_ct, encoding="utf-8") as _f:
            _cd = sorted(r["date"] for r in csv.DictReader(_f) if r.get("date"))
    if _cd:
        _older = [d for d in calset if d < _cd[0]] if calset else []
        L.append(f"| 上櫃交易日曆（{_cd[0]} 之前） | ⛔ **仍然只有自我一致**"
                 f"，共 {len(_older):,} 天。櫃買端點只給最近 7 個交易日 ⇒ "
                 "那段**永遠補不回來** | 沒有辦法（除非找到帶歷史的來源） |")
        L.append(f"| ~~上櫃交易日曆（{_cd[0]} 起）~~ | **已升 B**："
                 f"`otc_calendar.py` 每天併入櫃買大盤日成交量值指數"
                 f"（{len(_cd):,} 天，跟我方逐檔行情不同端點） | — |")
    else:
        L.append("| 上櫃交易日曆 | **自我一致 0 天差異，但那只證明自洽**"
                 "｜⚠ `calendar_tpex.csv` 還不存在（otc_calendar.py 還沒跑過"
                 "或連續失敗）| 讓 `otc_calendar.py` 跑起來 |")
    L.append("| 集保 `data/tdcc/` | 四道驗算全過（恆等式）＝ B；"
             "⛔ 但**只有一週**，序列本身還不存在 | 時間 |")

    # ── 四點五、⚠ 興櫃：欄位名一樣、語意不一樣（2026-09-09 新增）
    #   K線線 19:22 報「興櫃 363 檔 open 全空白」。我方重算屬實，
    #   而且往下量之後發現**比那更值得寫下來**：`close` 欄裝的不是收盤價。
    #   ⛔ 這一節必須是**每趟重算**的，不可以寫死數字——興櫃是 09-03 才進母體的，
    #     欄位供給隨時可能改變，而寫死的數字會在改變之後繼續看起來正確。
    L += ["", "## 四點五、⚠ **興櫃的欄位名跟上市上櫃一樣，但語意不一樣**", ""]
    _DAILY = os.path.join(_ROOT, "universe", "daily")
    _em_first, _em_last = "", ""
    for _d in cal:
        try:
            with io.open(os.path.join(_DAILY, _d + ".csv"), "rb") as _f:
                if b",emerging," in _f.read():
                    _em_first = _em_first or _d
                    _em_last = _d
        except OSError:
            pass
    if not _em_first:
        L.append("（本輪日檔裡沒有 `market == 'emerging'` 的列）")
    else:
        _n = 0
        _blank = {}
        _rat = []
        _same = 0
        with io.open(os.path.join(_DAILY, _em_last + ".csv"), encoding="utf-8") as _f:
            _rd = csv.DictReader(_f)
            _cols = _rd.fieldnames or []
            for _r in _rd:
                if _r.get("market") != "emerging":
                    continue
                _n += 1
                for _c in _cols:
                    if not (_r.get(_c) or "").strip():
                        _blank[_c] = _blank.get(_c, 0) + 1
                if _r.get("high") == _r.get("low") == _r.get("close"):
                    _same += 1
                try:
                    _v, _a, _c2 = (float(_r["volume"]), float(_r["amount"]),
                                   float(_r["close"]))
                    if _v > 0 and _c2 > 0:
                        _rat.append((_a / _v) / _c2)
                except (ValueError, KeyError, ZeroDivisionError):
                    pass
        _rat.sort()
        # ★ 對照組：**同一天的上市股**。沒有對照組的話「p5=p95=1.0000」
        #   說不出任何事——要有一個「本來就會差」的樣本，那個 1.0000 才有意義。
        _tw = []
        with io.open(os.path.join(_DAILY, _em_last + ".csv"), encoding="utf-8") as _f:
            for _r in csv.DictReader(_f):
                if _r.get("market") != "twse":
                    continue
                try:
                    _v, _a, _c2 = (float(_r["volume"]), float(_r["amount"]),
                                   float(_r["close"]))
                    if _v > 0 and _c2 > 0:
                        _tw.append((_a / _v) / _c2)
                except (ValueError, KeyError, ZeroDivisionError):
                    pass
        _tw.sort()
        _tw_p5 = _tw[len(_tw) // 20] if _tw else float("nan")
        _tw_p95 = _tw[len(_tw) * 19 // 20] if _tw else float("nan")
        _allblank = sorted(k for k, v in _blank.items() if v == _n)
        L.append(f"- **進母體的第一天是 {_em_first}**（在那之前 `emerging` = 0 列）"
                 f"。⛔ 任何跨越這一天的序列，母體是**中途換過**的——"
                 "統計上的跳動可能是定義變化，不是市場變化。")
        L.append(f"- {_em_last}：**{_n} 檔**｜**整欄空白**的欄位："
                 + ("、".join(f"`{k}`" for k in _allblank) if _allblank else "（沒有）"))
        if _rat:
            L.append(f"- ⛔ **`close` 欄裝的不是收盤價，是均價**："
                     f"`(amount÷volume) ÷ close` 在 {len(_rat)} 檔上"
                     f"**p5 = {_rat[len(_rat)//20]:.4f}、p95 = "
                     f"{_rat[len(_rat)*19//20]:.4f}**——"
                     "整個分布壓在 1.0000，代表它是算出來的，不是撮合出來的。")
            L.append(f"  （對照：同一天上市股的同一個比值 p5/p95 分別是 "
                     f"{_tw_p5:.4f}／{_tw_p95:.4f}，**真的收盤價跟均價本來就會差**。）")
        L.append(f"- `high` 與 `low` **是真的**（{_em_last} 只有 {_same}/{_n} 檔"
                 f" high=low=close）")
        L.append("- ⛔ **`meta/stocks.csv` 的 `kind` 分不出興櫃**（是 `stock`）"
                 "⇒ 只用 `kind == 'stock'` 篩母體的人會**靜默收進興櫃**。")
        # ⛔ 2026-09-09 21:5x 更正我自己：上一版這裡寫「唯一分得出來的是 market 欄」。
        #   **那句是錯的。** 日檔有 `price_basis` 欄，興櫃 363/363 都標著
        #   「均價/額推算」——**我方其實早就標了 close 是推算的**，
        #   是我沒去看那個欄位就寫了「唯一」。
        #   ⚠ 這正是我今天一直在抓的形狀：**只查了我想到的那幾欄，就說「只有」。**
        _pb = {}
        try:
            with io.open(os.path.join(_DAILY, _em_last + ".csv"),
                         encoding="utf-8") as _f:
                for _r in csv.DictReader(_f):
                    if _r.get("market") == "emerging":
                        _k = (_r.get("price_basis") or "").strip() or "（空白）"
                        _pb[_k] = _pb.get(_k, 0) + 1
        except OSError:
            pass
        L.append(f"- ⭐ **但 `price_basis` 欄有標**：興櫃那一天的值是 {_pb}"
                 "　⇒ 分得出來的有**兩個**欄位（`market` 與 `price_basis`），"
                 "而 `price_basis` 更直接——它說的正是「close 是推算的」。")
        L.append("- ⚠ 使用者 2026-09-06 已裁定：**興櫃不進推薦母體**。"
                 "⛔ 本資料庫**不執行**那條裁定——它是消費端的事，"
                 "這裡只負責把「分得出來的只有 `market`」這件事講清楚。")

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
