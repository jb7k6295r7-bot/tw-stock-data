#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`valid_bar`（K線分析線 方案乙）的自測。

## ⭐ 這一支要釘住的，是**兩個條件**，⛔ 不是「那個函式算得對不對」

    條件一  ⛔ 不可以取代 `price_basis`，必須**並存**
            （「一欄衍生值如果把來源欄蓋掉，它就變成不可反證的」）
    條件二  ⭐ 要帶**定義版本**與**產生它那一趟的輸入指紋**
            （「沒有指紋的衍生欄，就是下一次的 `_db_status.md`」）

## ⛔ 所以這裡有一半是**端到端**，不是純函式

CLAUDE.md 第七點第三個陷阱：「測了判準、沒測呼叫點」已經兩次。
⇒ 第四節真的跑一次 `transpose.build("price")`，然後**讀回寫出去的 CSV**
（四點二：斷言那一步**要造成的後果**，⛔ 不是斷言它跑完了）。
"""
import io
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import transpose as T                                          # noqa: E402
import valid_bar as V                                          # noqa: E402

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


def day(path, rows):
    """照**真日檔**的形狀寫（⛔ 假的比真的簡單＝那段沒測）。"""
    with io.open(path, "w", encoding="utf-8") as f:
        f.write("key,date,stock_id,name,market,close,volume,price_basis\n")
        for r in rows:
            f.write(",".join(r) + "\n")


def main():
    print("=" * 64)
    print("valid_bar：方案乙的兩個條件（不連網、不碰 repo 的 data/）")
    print("=" * 64)

    print("\n── ① flag()：三條判準 ──")
    ck("有成交、close 有值 ⇒ 1",
       V.flag({"price_basis": "均價", "close": "10.5"}) == "1")
    ck("`price_basis=無成交` ⇒ 0（⛔ 就算 close 有值也一樣）",
       V.flag({"price_basis": "無成交", "close": "10.5"}) == "0",
       "⛔ 無成交那天的 close 是前收殘留，不是成交價")
    ck("close 是空的 ⇒ 0",
       V.flag({"price_basis": "均價", "close": ""}) == "0")
    ck("close 只有空白 ⇒ 0（⛔ `\"\" or\"` 那種寫法會放行）",
       V.flag({"price_basis": "均價", "close": "   "}) == "0")
    ck("`price_basis` 帶前後空白照樣判得出無成交",
       V.flag({"price_basis": " 無成交 ", "close": "10"}) == "0",
       "⛔ CSV 讀進來常帶空白，⚠ 而帶空白時會靜靜判成「有成交」")
    ck("整列缺 `price_basis` 時不會爆，而且判成有效（close 有值）",
       V.flag({"close": "10"}) == "1")
    ck("★ 反向驗：`is_notrade` 對「均價」確實回 False",
       V.is_notrade({"price_basis": "均價"}) is False,
       "⛔ 恆回 True 的話上面那幾條全是假的")

    print("\n── ② 條件一：⛔ 不可以取代 `price_basis` ──")
    full = ["date", "stock_id", "close", "volume", "price_basis"]
    okc, note = V.assert_coexists(full)
    ck("兩欄都在 ⇒ 准發", okc and "並存" in note, note)
    okc, note = V.assert_coexists([c for c in full if c != "price_basis"])
    ck("⛔ 少了 `price_basis` ⇒ **不准發**（衍生欄不可以是孤兒）",
       not okc and "price_basis" in note, note)
    okc, note = V.assert_coexists([c for c in full if c != "close"])
    ck("⛔ 少了 `close` ⇒ 不准發", not okc and "close" in note, note)
    okc, note = V.assert_coexists(full + [V.COL])
    ck("⛔ 表頭裡已經有 `valid_bar` ⇒ 不重複發", not okc, note)
    ck("不准發的時候，說明字串**講得出理由**"
       "（⛔ 否則「沒發」跟「全是 0」在下游長得一樣）",
       bool(V.assert_coexists(["date"])[1].strip()))

    print("\n── ③ 條件二：定義版本 ＋ 輸入指紋 ──")
    fp = {"files": 3, "bytes": 12345, "last": "2026-09-11"}
    c = V.contract(fp)
    ck("契約帶著版本", c.get("version") == V.VERSION, c)
    ck("契約帶著判準原文（⛔ 版本號自己講不出它判了什麼）",
       "price_basis" in c.get("rule", "") and "close" in c.get("rule", ""), c)
    ck("契約帶著**產生它那一趟的輸入指紋**",
       c.get("from") == fp, c)

    d = tempfile.mkdtemp(prefix="tvb_")
    try:
        ck("⛔ 沒有 `_built.json` ⇒ `read_contract` 回 None（⚠ 讀不到 ≠ 沒問題）",
           V.read_contract(d)[0] is None)
        io.open(os.path.join(d, "_built.json"), "w", encoding="utf-8").write(
            json.dumps({"kind": "price", "rows": 9, "src": fp}))
        got, note = V.read_contract(d)
        ck("⛔ **加這一欄之前**建的個股庫（stamp 裡沒有那一塊）⇒ 回 None",
           got is None and "之前" in note, note)
        io.open(os.path.join(d, "_built.json"), "w", encoding="utf-8").write(
            json.dumps({"kind": "price", "rows": 9, "src": fp,
                        V.COL: V.contract(fp)}))
        got, note = V.read_contract(d)
        # ⭐ 這一條**故意不傳 `stamp=`**：有預設值的參數一定要有一條不傳它的
        #   斷言（CLAUDE.md 第七點第三個陷阱，`month_is_open` 付過代價）。
        ck("有那一塊 ⇒ 回得出版本與指紋（⛔ 這條沒傳 `stamp=`，走預設值那條路）",
           got is not None and got["version"] == V.VERSION
           and got["from"]["last"] == "2026-09-11", note)
        io.open(os.path.join(d, "_built.json"), "w", encoding="utf-8").write("{壞")
        ck("⛔ stamp 壞掉 ⇒ 回 None，不丟例外",
           V.read_contract(d)[0] is None)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    print("\n── ④ 呼叫點：真的跑一趟 `transpose.build`，然後**讀回寫出去的檔** ──")
    d = tempfile.mkdtemp(prefix="tvbe_")
    src, out = os.path.join(d, "daily"), os.path.join(d, "stocks")
    os.makedirs(src)
    _s, _o = T.SRC["price"], T.OUT["price"]
    try:
        T.SRC["price"], T.OUT["price"] = [src], out
        day(os.path.join(src, "2026-09-10.csv"), [
            ["k1", "2026-09-10", "2330", "台積電", "twse", "1000", "50000", "均價"],
            ["k2", "2026-09-10", "9999", "冷門", "twse", "12.3", "0", "無成交"]])
        day(os.path.join(src, "2026-09-11.csv"), [
            ["k3", "2026-09-11", "2330", "台積電", "twse", "1010", "40000", "均價"],
            ["k4", "2026-09-11", "9999", "冷門", "twse", "", "0", "無成交"]])
        rc, info = T.build("price")
        ck("build 回 0", rc == 0, info)

        head = None
        rows = {}
        with io.open(os.path.join(out, "2330.csv"), encoding="utf-8") as f:
            import csv as _csv
            rd = _csv.reader(f)
            head = next(rd)
            for r in rd:
                rows[r[head.index("date")]] = r
        ck("⭐ 寫出去的表頭**真的多了** `valid_bar`", V.COL in head, head)
        ck("⛔ 而 `price_basis` **還在**（條件一：並存，不取代）",
           "price_basis" in head, head)
        ck("`valid_bar` 接在**最後一欄**"
           "（⇒ 來源日檔的欄位仍是全庫表頭的前綴，那道檢查不會誤判）",
           head and head[-1] == V.COL, head)
        ck("有成交那兩天 `valid_bar=1`",
           all(rows[k][head.index(V.COL)] == "1" for k in rows), rows)

        nt = {}
        with io.open(os.path.join(out, "9999.csv"), encoding="utf-8") as f:
            import csv as _csv
            rd = _csv.reader(f)
            h2 = next(rd)
            for r in rd:
                nt[r[h2.index("date")]] = r
        ck("⭐ 無成交那一檔**兩天都有列**（⛔ 不是被刪掉）", len(nt) == 2, nt)
        ck("而兩列的 `valid_bar` 都是 0",
           all(v[h2.index(V.COL)] == "0" for v in nt.values()), nt)
        ck("⛔ 而 `close` 那一格**原封不動**（1000 那種前收殘留照樣看得到）"
           "⇒ 這一欄是可反證的",
           nt["2026-09-10"][h2.index("close")] == "12.3", nt)

        got, note = V.read_contract(out)
        ck("⭐⭐ `_built.json` 裡真的有契約（條件二）", got is not None, note)
        ck("而契約裡的指紋 ＝ **這一趟**的來源（2 檔日檔、最後一天 2026-09-11）",
           got and got["from"]["files"] == 2
           and got["from"]["last"] == "2026-09-11", note)
    finally:
        T.SRC["price"], T.OUT["price"] = _s, _o
        shutil.rmtree(d, ignore_errors=True)

    print("\n── ⑤ 只准有一份實作（CLAUDE.md 四點五）──")
    for f in ("hole_kinds.py", "notrade_watermark.py", "transpose.py"):
        s = io.open(os.path.join(HERE, f), encoding="utf-8").read()
        body = "\n".join(ln for ln in s.split("\n")
                         if not ln.lstrip().startswith("#"))
        ck(f"{f} 判無成交／有效走的是共用那一份",
           "valid_bar." in body
           and '"無成交"' not in body.replace('NOTRADE = "無成交"', ""),
           "⛔ 還有一份自己寫的 `== \"無成交\"`")

    print("\n── ⑥ `_db_status.md` 講不講得出這一欄 ──")
    # ⛔ 「這份個股庫沒有 valid_bar」跟「那一欄全是 0」在讀的人眼裡長得一樣，
    #   ⚠ 而意思完全相反 ⇒ 契約指定回答「有什麼」的那份文件要自己講出來。
    # ⭐ 比**機制**，⛔ 不比字串（「valid_bar」四個字在註解裡也有一份）。
    import ast as _ast
    with open(os.path.join(HERE, "db_status.py"), encoding="utf-8") as _f:
        _tree = _ast.parse(_f.read())
    _calls = [n for n in _ast.walk(_tree) if isinstance(n, _ast.Call)
              and isinstance(n.func, _ast.Attribute)
              and n.func.attr == "read_contract"
              and getattr(n.func.value, "id", "") == "valid_bar"]
    ck("★ `db_status` 真的去讀了契約（⛔ 不是自己另外判一次）",
       len(_calls) == 1, f"⛔ 掃到 {len(_calls)} 個 valid_bar.read_contract(…)")

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
