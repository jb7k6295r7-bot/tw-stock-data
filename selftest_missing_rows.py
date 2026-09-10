#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_missing_rows.py — 離線驗 missing_rows.scan()。**不碰真的 data/。**

⛔ 這一支要防的四件事，每一件都對應一個 fixture：

  ① 官方清單有、日檔沒有 ⇒ **要抓到**
  ② 官方清單**檔案不存在** ⇒ ⛔ 不可以當成「那天官方沒有這些檔」
     （那會把「我沒存」讀成「它沒有」——今晚這個形狀已經出現十幾次）
  ③ ETF／權證不算：`kind != stock` 的要濾掉，否則數字虛胖
  ④ `sources` 欄要講得出是**哪一張清單**指認的
"""
import io
import os
import shutil
import sys
import tempfile

import missing_rows as M

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


def w(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(header + "\n")
        for r in rows:
            f.write(",".join(str(x) for x in r) + "\n")


def build(root):
    uni = os.path.join(root, "data", "universe")
    w(os.path.join(root, "data", "meta", "stocks.csv"),
      "stock_id,name,market,kind,first_seen,last_seen",
      [["2330", "台積電", "twse", "stock", "2015-01-05", "2026-09-08"],
       ["6904", "伯鑫", "tpex", "stock", "2018-01-02", "2026-09-08"],
       ["8921", "沈氏", "tpex", "stock", "2015-01-05", "2026-09-08"],
       ["0050", "元大台灣50", "twse", "etf", "2015-01-05", "2026-09-08"]])
    # ⭐ 8921 在 09-01 官方公告暫停交易 ⇒ 那一筆漏列要被歸因；6904 沒有 ⇒ 要留空
    w(os.path.join(root, "data", "meta", "suspend_twse.csv"),
      "stock_id,name,susp_date,susp_time,resume_date,resume_time,days",
      [["8921", "沈氏", "2026-09-01", "8:00", "2026-09-02", "8:00", "1"]])
    DH = ("key,date,stock_id,name,market,open,high,low,close,volume,amount,"
          "change,limit,shares,transactions,price_basis")
    # D1：2330 與 0050 有成交；6904／8921 沒有 ⇒ 日檔裡沒有它們
    w(os.path.join(uni, "daily", "2026-09-01.csv"), DH,
      [[f"2026-09-01_{c}", "2026-09-01", c, "N", m, 1, 1, 1, 1, 1, 1, 0,
        "", "", 1, ""] for c, m in (("2330", "twse"), ("0050", "twse"))])
    # D2：四檔都有成交 ⇒ 一筆都不該漏
    w(os.path.join(uni, "daily", "2026-09-02.csv"), DH,
      [[f"2026-09-02_{c}", "2026-09-02", c, "N", m, 1, 1, 1, 1, 1, 1, 0,
        "", "", 1, ""] for c, m in (("2330", "twse"), ("0050", "twse"),
                                    ("6904", "tpex"), ("8921", "tpex"))])
    # D3：只有 2330 ⇒ 但這一天**六張官方清單一張都沒存**
    #     ⛔ 必須整天跳過，不可以算成「漏了 3 檔」
    w(os.path.join(uni, "daily", "2026-09-03.csv"), DH,
      [["2026-09-03_2330", "2026-09-03", "2330", "N", "twse", 1, 1, 1, 1,
        1, 1, 0, "", "", 1, ""]])
    PR = "date,stock_id,close,yield_pct,dividend_year,per,pbr,fs_quarter"
    IN = "date,stock_id,foreign,trust,dealer,total"
    for d in ("2026-09-01", "2026-09-02"):
        # otcper：列 6904 與 8921（掛牌中，不管有沒有成交）
        w(os.path.join(uni, "otcper", d + ".csv"), PR,
          [[d, c, "", 0, 114, 0, 0, "115Q2"] for c in ("6904", "8921")])
        # otcinst：只列 8921（法人有交易 ⇒ **鐵證**）
        w(os.path.join(uni, "otcinst", d + ".csv"), IN,
          [[d, "8921", 1, 0, 0, 1]])
        # per：列 2330 與 0050（0050 是 etf，⛔ 不該被算進去）
        w(os.path.join(uni, "per", d + ".csv"), PR,
          [[d, c, 100, 1, 114, 10, 1, "115/2"] for c in ("2330", "0050")])


def main():
    real = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    before = os.path.isdir(real)
    root = tempfile.mkdtemp(prefix="misrows_")
    try:
        build(root)
        rows, byday, bysrc, n_cmp = M.scan(root=root)
        got = {(r[0], r[1]): r[4] for r in rows}
        got_why = {(r[0], r[1]): r[5] for r in rows}
        print("  scan →", rows, "｜byday", byday, "｜bysrc", bysrc, "｜可比", n_cmp)
        ck("① 官方有、日檔沒有 ⇒ 09-01 抓到 6904 與 8921",
           ("2026-09-01", "6904") in got and ("2026-09-01", "8921") in got,
           str(sorted(got)))
        ck("① 09-02 四檔都有成交 ⇒ 一筆都不漏", byday.get("2026-09-02") == 0,
           f"byday={byday}")
        ck("② 官方清單整天沒存的 09-03 ⛔ 整天跳過（不是算成漏 3 檔）",
           "2026-09-03" not in byday and n_cmp == 2, f"byday={byday} n_cmp={n_cmp}")
        ck("③ 0050 是 etf ⇒ 不算（否則數字虛胖）",
           not any(r[1] == "0050" for r in rows), str(rows))
        # ⭐ 歸因欄：官方那天公告暫停交易的，要標出來；沒有的要留空。
        #   ⛔ 這一項要**兩個方向都驗**——只驗「標得出來」的話，
        #     一個「全部都標成暫停交易」的 bug 也會通過。
        ck("⑤ 官方暫停交易那一筆有標出來",
           got_why.get(("2026-09-01", "8921")) == "官方暫停交易", str(got_why))
        ck("⑤ ⛔ 沒有暫停紀錄的那一筆**留空**（不是全部都標）",
           got_why.get(("2026-09-01", "6904")) == "", str(got_why))
        ck("④ sources 講得出是哪一張清單指認的",
           got.get(("2026-09-01", "8921")) == "otcper+otcinst"
           and got.get(("2026-09-01", "6904")) == "otcper",
           str(got))
        # ⚠ 這裡我第一次寫成 `== 2`，**錯的是我不是程式**：
        #   09-02 那天四檔都在日檔裡 ⇒ otcinst 指認不到任何一筆。
        #   ⇒ 只有 09-01 的 8921 一筆。⛔ 期望值也要自己先算過。
        ck("⭐ 鐵證（otcinst）有被單獨數出來（只有 09-01 的 8921）",
           bysrc.get("otcinst") == 1, str(bysrc))
        # ── 反向驗：把 otcper 那兩天的檔刪掉，漏列數必須**變少**（不是不變）──
        #   ⛔ 沒有這一項的話，「掃不到來源」與「來源說沒漏」會長得一模一樣。
        for d in ("2026-09-01", "2026-09-02"):
            os.remove(os.path.join(root, "data", "universe", "otcper", d + ".csv"))
        rows2, _b2, _s2, _n2 = M.scan(root=root)
        ck("★ 拿掉一張官方清單，抓到的筆數會變少（證明它真的在用那張清單）",
           len(rows2) < len(rows), f"{len(rows)} → {len(rows2)}")
    finally:
        shutil.rmtree(root, ignore_errors=True)
    ck("★ 沒有動到 repo 真的 data/", os.path.isdir(real) == before)
    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
