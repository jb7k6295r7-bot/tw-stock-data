#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`official_formula` 的自測。**不連網、不讀檔。**

⭐ 這一支要釘的是**四種狀態不可以合併**：
⛔ `unknown` 併進 `same` ⇒ 新端點的公式永遠不會有人看；
⛔ `unknown` 併進 `changed` ⇒ 它天天紅，然後被學會忽略（六點五）。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import official_formula as F                                    # noqa: E402

OK = FAIL = 0

# ⭐ 這一段是 2026-09-13 `_reduce_ratio_probe.txt` 逐字抄回來的官方回應
REAL = ["退還股款：恢復買賣參考價＝（停止買賣前收盤價-息值-每股退還股款）/（減資換股率）",
        "彌補虧損：恢復買賣參考價＝（停止買賣前收盤價）/（減資換股率）",
        "彌補虧損之減資並現金增資：<br>　恢復買賣參考價＝（停止買賣前收盤價）/（減資換股率）"
        "<br>　減資後現金增資除權參考價＝（恢復買賣參考價+現金增資認購價*減資後現金增資配股率）"
        "/（1+減資後現金增資配股率）"]


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


def main():
    print("=" * 64)
    print("official_formula：官方公式的留存與盯梢（不連網）")
    print("=" * 64)

    print("\n── ① 四種狀態 ──")
    ck("⭐ 逐字相同 ⇒ same", F.check("reduce", {"formula": REAL})[0] == "same",
       F.check("reduce", {"formula": REAL})[1])
    ck("⛔ 少一段 ⇒ changed", F.check("reduce", {"formula": REAL[:2]})[0] == "changed")
    ck("⛔ 改一個字 ⇒ changed（⚠ 「息值」被拿掉就是這樣）",
       F.check("reduce", {"formula": [REAL[0].replace("-息值", "")] + REAL[1:]})[0]
       == "changed")
    ck("⚠ 沒有記錄的 feed ⇒ unknown（⛔ 不是 same、也不是 changed）",
       F.check("沒見過這條", {"formula": ["x＝y"]})[0] == "unknown")
    ck("沒有 formula 鍵 ⇒ absent", F.check("reduce", {})[0] == "absent")
    ck("⛔ 不是 dict 也不炸 ⇒ absent", F.check("reduce", [1, 2, 3])[0] == "absent")
    ck("⭐ formula 是空陣列 ⇒ absent（⛔ 不是 changed）",
       F.check("reduce", {"formula": []})[0] == "absent")

    print("\n── ② 正規化：⛔ 標記與空白不算差異，⚠ 而**字**算 ──")
    ck("`<br>` 與全形空白不算差異",
       F.normalize("a<br>　b") == F.normalize("ab"))
    ck("⭐ 全形冒號分號正規化成半形（⚠ 官方兩種都用過）",
       F.normalize("甲：乙；丙") == F.normalize("甲:乙;丙"))
    ck("⛔ 而換一個字就是不同", F.normalize("停止買賣前收盤價")
       != F.normalize("停止買賣後收盤價"))
    ck("⭐ 順序不同不算變（官方三段的順序不保證）",
       F.check("reduce", {"formula": list(reversed(REAL))})[0] == "same")

    print("\n── ③ pull：兩種形狀都要吃 ──")
    ck("字串 ⇒ 一段", F.pull({"formula": "abc"}) == ["abc"])
    ck("陣列 ⇒ 照數", len(F.pull({"formula": ["a", "b"]})) == 2)
    ck("沒有 ⇒ 空", F.pull({"stat": "OK"}) == [])

    print("\n── ④ ⛔ 官方那段裡有我方**推錯**的兩件事（記在這裡免得再推一次）──")
    ck("⭐ 退還股款那一條有 **息值** 這一項（⛔ 我方式子裡沒有）",
       "息值" in REAL[0])
    ck("⭐ 而扣的是官方欄位「每股退還股款」（⛔ 不是我推的「面額 10 × 減資比率」）",
       "每股退還股款" in REAL[0] and "面額" not in REAL[0])

    print("\n── ④.5 ⭐ TWT49U 那兩條也釘住（⛔ 我方推了兩輪的那兩條）──")
    EX = ["除權息參考價 = (除權息前收盤價-息值+現金增資認購價*現金增資配股率)"
          "/(1+無償配股率+現金增資配股率)",
          "減除股利參考價 = (除權息前收盤價-息值)/(1+無償配股率)"]
    ck("⭐ `exright` 的兩條逐字相同", F.check("exright", {"formula": EX})[0] == "same",
       F.check("exright", {"formula": EX})[1])
    ck("⭐ 而它也有 **息值** 那一項（⛔ 我把除權與除息當兩件事分開推，官方是同一條）",
       "息值" in EX[0] and "息值" in EX[1])
    ck("⛔ 把現金增資那一項拿掉 ⇒ changed",
       F.check("exright", {"formula": [EX[0].replace(
           "+現金增資認購價*現金增資配股率", ""), EX[1]]})[0] == "changed")

    print("\n── ⑤ feeds 端的收集：⛔ `changed` 不可以被後來的 `same` 蓋掉 ──")
    import feeds
    feeds._FORMULA_SEEN.clear()
    feeds._watch_formula("reduce", {"formula": REAL[:2]})        # changed
    feeds._watch_formula("reduce", {"formula": REAL})            # same
    ck("⭐ 同一趟問幾十次，最壞的那個要留著",
       feeds._FORMULA_SEEN.get("reduce", ("?",))[0] == "changed",
       str(feeds._FORMULA_SEEN))
    feeds._FORMULA_SEEN.clear()
    feeds._watch_formula("reduce", {"stat": "OK"})
    ck("⛔ absent 不進收集（⚠ 否則每張沒給公式的表都會佔一行）",
       not feeds._FORMULA_SEEN)

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
