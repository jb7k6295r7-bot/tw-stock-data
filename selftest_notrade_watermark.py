#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_notrade_watermark.py — 驗「這一天已經是新語意了嗎」的判準。

⛔ 這支要證明的事，每一條都對應 K線線 13:00 那個條件：
  ① 有無成交列的那一天 → `new_semantics=1`
  ② 一列都沒有的那一天 → `0`（⚠ **不可判定**，不是「乾淨」）
  ③ 逐檔清單真的數對「多幾列」（那是 Q1 要的重算範圍）
  ④ ⚠ 判準走 `price_basis`，⛔ **不走「close 是不是空的」**
     ——反向測試：造一列 close 空、`price_basis` 卻是別的值，它不可以被算進去
  ⑤ ⚠ 興櫃的無成交列也要算得到（它的 market 是 emerging，不是被漏掉）
"""
import csv
import io
import os
import shutil
import sys
import tempfile

import notrade_watermark as W

OK = FAIL = 0
H = ("key,date,stock_id,name,market,open,high,low,close,volume,amount,"
     "change,limit,shares,transactions,price_basis").split(",")


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


def row(code, market="twse", close="10", basis=""):
    r = {h: "" for h in H}
    r.update({"stock_id": code, "market": market, "close": close,
              "price_basis": basis, "name": "N"})
    return r


def write(dirpath, day, rows):
    with io.open(os.path.join(dirpath, day + ".csv"), "w",
                 encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=H)
        w.writeheader()
        for r in rows:
            r = dict(r)
            r["date"], r["key"] = day, f"{day}_{r['stock_id']}"
            w.writerow(r)


def main():
    sand = tempfile.mkdtemp(prefix="ntw_")
    try:
        # 補過的一天：兩檔有價、兩檔無成交（其中一檔是興櫃）
        write(sand, "2026-09-08", [
            row("2330"), row("6104"),
            row("6904", "tpex", "", "無成交"),
            row("6740", "emerging", "", "無成交"),
        ])
        # 還沒補的一天：全部有價
        write(sand, "2026-09-07", [row("2330"), row("6104")])
        # ⚠ 陷阱：close 是空的，但 price_basis 不是「無成交」
        #   （現實裡的來源：興櫃 open 整欄空白、或欄位對不上時留空）
        write(sand, "2026-09-09", [
            row("2330"), row("6740", "emerging", "", "均價/額推算")])

        per_day, per_stock = W.scan(sand)
        d = {r[0]: r for r in per_day}

        ck("① 有無成交列的那一天 new_semantics=1",
           d.get("2026-09-08", ["", ""])[1] == "1", str(d.get("2026-09-08")))
        ck("① 那一天數到 2 列無成交",
           d.get("2026-09-08", ["", "", "", ""])[3] == "2", str(d.get("2026-09-08")))
        ck("② 還沒補的那一天是 0（⚠ 不可判定，不是乾淨）",
           d.get("2026-09-07", ["", ""])[1] == "0", str(d.get("2026-09-07")))
        ck("② n_rows 照樣數（2 列）",
           d.get("2026-09-07", ["", "", ""])[2] == "2", str(d.get("2026-09-07")))
        ck("④ ⛔ close 空但 price_basis 不是『無成交』**不算**",
           d.get("2026-09-09", ["", ""])[1] == "0", str(d.get("2026-09-09")))
        ck("⑤ 興櫃的無成交列有被算到 emerging 那一格",
           d.get("2026-09-08", [""] * 7)[6] == "1", str(d.get("2026-09-08")))
        ck("⑤ 上櫃那一列算在 tpex",
           d.get("2026-09-08", [""] * 6)[5] == "1", str(d.get("2026-09-08")))

        st = {e[0]: e for e in per_stock}
        ck("③ 逐檔清單只收無成交的那兩檔（⛔ 不是全部四檔）",
           sorted(st) == ["6740", "6904"], str(sorted(st)))
        ck("③ 各多 1 列，first/last 都是那一天",
           st.get("6904") == ["6904", "tpex", 1, "2026-09-08", "2026-09-08"],
           str(st.get("6904")))
        ck("③ 興櫃那一檔的 market 記成 emerging（身分沒有被 price_basis 吃掉）",
           st.get("6740", ["", ""])[1] == "emerging", str(st.get("6740")))

        # ⭐⭐ 反向測試：把判準改成「close 是不是空的」——⑤④ 那一條必須紅。
        #   ⛔ 沒證明過會失敗的測試不算測試。
        def _by_close(dirpath):
            days = sorted(n[:-4] for n in os.listdir(dirpath) if n.endswith(".csv"))
            out = {}
            for day in days:
                with io.open(os.path.join(dirpath, day + ".csv"), encoding="utf-8") as f:
                    out[day] = sum(1 for r in csv.DictReader(f)
                                   if not (r.get("close") or "").strip())
            return out
        bad = _by_close(sand)
        ck("★ 反向：用『close 空不空』當判準時 09-09 會**被誤判成已補**"
           "（證明這支測得到東西）",
           bad.get("2026-09-09", 0) > 0 and d.get("2026-09-09", ["", ""])[1] == "0",
           f"close 法數到 {bad.get('2026-09-09')}｜本支判 {d.get('2026-09-09')}")

        # 空目錄
        empty = tempfile.mkdtemp(prefix="ntw_empty_")
        try:
            pd2, ps2 = W.scan(empty)
            ck("⑥ 空目錄回 ([], []) 不是炸掉", pd2 == [] and ps2 == [])
        finally:
            shutil.rmtree(empty, ignore_errors=True)
        pd3, _ = W.scan(os.path.join(sand, "不存在"))
        ck("⑥ 目錄不存在也回 ([], [])", pd3 == [])
    finally:
        shutil.rmtree(sand, ignore_errors=True)

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
