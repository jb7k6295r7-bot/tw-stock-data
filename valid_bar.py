# -*- coding: utf-8 -*-
"""`valid_bar`：一根 K 棒**可不可以拿來算**的單一判準。

## ⭐ 由來（K線分析線 2026-09-11 19:00 裁定「方案乙」）

K線分析線原本走「甲」：**他們自己**看 `price_basis` 判。
⛔ 而那等於同一段邏輯散在每一條線裡（CLAUDE.md 四點五），
⚠ 而且每一條線判得不一樣的時候，**沒有人會發現**——
兩邊都算得出數字，只是母體不同。

⇒ 乙＝資料庫這一邊把它**物化成一欄**。而 K線分析線給了**兩個條件**，
⛔ 缺一個就不准落地：

### 條件一：⛔ **不可以取代 `price_basis`，必須並存**

> 「一欄衍生值如果把來源欄蓋掉，它就變成不可反證的。」

⇒ 本模組只在 `price_basis` **還在表頭裡**的時候才發 `valid_bar`
（`assert_coexists()`）。⚠ 來源欄不見了就**大聲失敗**，
⛔ 不是「照樣發一欄、只是沒得對照」。

### 條件二：⭐ 要帶**定義版本**與**產生它那一趟的輸入指紋**

> 「`valid_bar` 只要早一趟跑，就會跟 `daily` 不一致，
>  ⭐ 而它長得跟對的一模一樣 ⇒ **沒有指紋的衍生欄，就是下一次的 `_db_status.md`**」

⇒ `transpose.write_stamp()` 把 `{"version", "rule", "from"}` 一起寫進
`data/stocks/_built.json`，跟既有的 `src` 指紋放在同一份。
⚠ 指紋不是這裡算的（`transpose.source_fingerprint`），⛔ 這裡不再算第二份。

## ⛔ 「有列」那一條是**呼叫端**的責任，不是這裡

判準三條：**有列** 且 `price_basis != 無成交` 且 `close` 非空。
⚠ 而「有列」在個股庫裡是**沒有那一天的列**——
⛔ 一個不存在的列沒有地方可以放 `valid_bar=0`。
⇒ ⭐ 所以讀的人一定要記得：**缺日期 ＝ 沒有有效 K 棒**，
跟 `valid_bar=0` 是同一件事的兩種長相。
（`tw-technical-analysis` 的「硬斷點＝連續 5 個交易日沒有有效 K 棒」
  兩種都要算進去。）
"""
import io
import json
import os

VERSION = "v1"
RULE = "有列 且 price_basis != 無成交 且 close 非空"
NOTRADE = "無成交"
COL = "valid_bar"
NEEDS = ("price_basis", "close")      # ⛔ 少任何一欄就不准發


def is_notrade(row):
    """→ 這一列是不是**無成交**（`price_basis == "無成交"`）。

    ⭐ **只有這一份實作**（CLAUDE.md 四點五）：`hole_kinds`、
      `notrade_watermark` 與這裡的 `flag()` 共用。
    ⚠ 取值前 `.strip()`——CSV 讀進來常帶空白，⛔ 而帶空白時會靜靜判成「不是無成交」。
    """
    return (row.get("price_basis") or "").strip() == NOTRADE


def flag(row):
    """→ `"1"` 或 `"0"`（字串，⛔ 因為它要直接寫進 CSV）。

    ⚠ 傳進來的一定是**存在的那一列** ⇒ 「有列」那一條在這裡恆成立，
      ⛔ 見模組說明：缺日期是呼叫端要處理的。
    """
    if is_notrade(row):
        return "0"
    return "0" if not (row.get("close") or "").strip() else "1"


def assert_coexists(header):
    """條件一的閘門：→ `(可不可以發, 說明)`。

    ⛔ 這支**不回 True/False 就算了**——說明字串要進 runlog，
      ⚠ 否則「沒發這一欄」跟「這一欄全是 0」在下游長得一樣。
    """
    miss = [c for c in NEEDS if c not in header]
    if miss:
        return False, (f"⛔ 表頭缺 {miss} ⇒ **不發 `{COL}`**："
                       f"衍生欄蓋掉或取代來源欄就變成不可反證的（K線分析線 條件一）")
    if COL in header:
        return False, f"⛔ 表頭裡已經有 `{COL}` ⇒ 來源自己有這一欄，這裡不重複發"
    return True, f"`{COL}` 與 {list(NEEDS)} **並存**（⛔ 不取代）"


def contract(src_fingerprint):
    """→ 要寫進 `_built.json` 的那一塊（條件二）。

    ⚠ `src_fingerprint` 由 `transpose.source_fingerprint()` 算好傳進來，
      ⛔ 這裡不自己再算一份。
    """
    return {"version": VERSION, "rule": RULE, "from": src_fingerprint}


def read_contract(out_dir, stamp="_built.json"):
    """→ `(這份個股庫的 valid_bar 契約 dict 或 None, 說明)`。

    ⭐ 給下游用：拿數字之前先問「這一欄是哪一版、用哪一批日檔算的」。
    ⛔ 讀不到一律回 `None`——⚠ 而 `None` 的意思是
      **「這份個股庫證明不了它的 `valid_bar` 是新的」**，
      ⛔ 不是「它沒有 valid_bar」。
    """
    p = os.path.join(out_dir, stamp)
    if not os.path.exists(p):
        return None, f"⛔ 沒有 `{stamp}` ⇒ 證明不了 `{COL}` 是用哪一批日檔算的"
    try:
        body = json.load(io.open(p, encoding="utf-8")) or {}
    except (ValueError, OSError) as ex:                       # noqa: BLE001
        return None, f"⛔ `{stamp}` 讀不動（{type(ex).__name__}）"
    c = body.get(COL)
    if not isinstance(c, dict) or not c.get("version"):
        return None, f"⛔ `{stamp}` 裡沒有 `{COL}` 那一塊 ⇒ 這份是**加這一欄之前**建的"
    f = c.get("from") or {}
    return c, (f"`{COL}` {c['version']}｜{c.get('rule', '')}"
               f"｜用 {f.get('files')} 檔／{f.get('bytes')} 位元組"
               f"／最後一天 {f.get('last')} 的日檔算的")
