#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把回測線的 `backtest/breakpoint_scan.py` 接進每日管線，寫 `_last_run.md`。

    python3 breakpoint_check.py

## 為什麼是一層薄殼，不是把那支複製過來

`backtest/` 是**回測線**的，`breakpoint_scan.py` 的規則（比值 ≤ 0.55／≥ 1.8、
連續缺 ≥ 5 個交易日、流動性門檻）由 K線線裁定。⛔ 共用的引擎不可以在本地分岔——
複製一份過來，兩邊就會各自演化，而且**不會有人發現**，直到兩份的數字對不起來。
所以這一支只做三件本來就屬於施工這一邊的事：

  ① 呼叫他們的 `main()`，把 stdout 原封不動存成 `data/meta/_breakpoint_scan.md`
  ② 用他們的回傳碼寫進 `data/meta/_last_run.md`
  ③ pandas 缺席時**報 ✗，不是安靜跳過**

## 判定

市場情報分析線 2026-09-09 08:45 裁定：**要排、不擋整批、報 ✗ 吐差異清單**。
只有「漏抓」（`par_change.csv` 裡既無因子、規則也沒抓到）才是 ✗——
那代表規則寫錯了。規則另外抓到的長停牌**不算錯**，那是「洞算不算斷點」的
語意問題，歸情報分析裁；這裡只把數字列出來。
"""
import io
import os
import re
import sys

import runlog

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "data", "meta", "_breakpoint_scan.md")


def main():
    rl = runlog.Run("breakpoint_scan")

    try:
        from backtest import breakpoint_scan as BS
    except Exception as ex:                                      # noqa: BLE001
        # ⚠ 不可以安靜跳過。這一支唯一的價值就是「規則有沒有寫錯」，
        #   跳過等於天天回報「沒問題」——那是最貴的失敗形狀。
        rl.info("狀態", f"載入失敗：{type(ex).__name__}: {ex}")
        rl.check("backtest.breakpoint_scan 載得起來（需要 pandas）", False,
                 "載不起來就沒有對帳，等於這道檢查不存在")
        return rl.finish()

    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        rc = BS.main()
    except Exception as ex:                                      # noqa: BLE001
        sys.stdout = old
        txt = buf.getvalue()
        rl.info("狀態", f"執行中丟例外：{type(ex).__name__}: {ex}")
        _write(txt + f"\n\n⛔ 例外：{type(ex).__name__}: {ex}\n")
        rl.check("掃描跑完", False, f"{type(ex).__name__}: {ex}")
        return rl.finish()
    finally:
        sys.stdout = old
    txt = buf.getvalue()
    print(txt, end="")
    _write(txt)

    # 從輸出裡把數字撈出來當摘要。⛔ 判定用的是 rc，不是這幾個數字——
    #   正則沒對到只會讓摘要少一行，不會讓判定失準。
    m = re.search(r"斷點 (\d+) 個、(\d+) 檔", txt)
    if m:
        rl.info("全母體斷點", f"{m.group(1)} 個／{m.group(2)} 檔")
    m = re.search(r"已有因子 (\d+)、仍為斷點 (\d+)、漏抓 (\d+)", txt)
    if m:
        rl.info("對帳 par_change.csv",
                f"已有因子 {m.group(1)}／仍為斷點 {m.group(2)}／漏抓 {m.group(3)}")
    m = re.search(r"規則另外抓到（不在 par_change.csv）：(\d+) 個、(\d+) 檔", txt)
    if m:
        rl.info("規則另外抓到（長停牌，成因未定）",
                f"{m.group(1)} 個／{m.group(2)} 檔——"
                "「洞算不算斷點」歸情報分析裁，這裡只列數")
    rl.info("完整輸出", "data/meta/_breakpoint_scan.md")

    rl.check("par_change.csv 沒有一筆漏抓", rc == 0,
             "漏抓＝既無還原因子、規則也沒抓到 ⇒ 規則寫錯了，"
             "清單在 data/meta/_breakpoint_scan.md")
    return rl.finish()


def _write(txt):
    try:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with io.open(OUT, "w", encoding="utf-8") as f:
            f.write("# breakpoint_scan 的輸出（全母體斷點掃描＋與 par_change.csv 對帳）\n")
            f.write("# 規則屬回測線／K線線，這裡只是把它接進每日管線。\n")
            f.write("# 產生方式：python3 breakpoint_check.py\n\n```\n")
            f.write(txt.rstrip("\n") + "\n```\n")
    except OSError as ex:                                        # noqa: BLE001
        print(f"[breakpoint] 寫檔失敗：{ex}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
