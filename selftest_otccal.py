#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 `otc_calendar.main()` **整條走一遍**（假回應、沙箱路徑），驗它真的做了事。

    python3 selftest_otccal.py

## 為什麼這一支要存在

`otc_calendar.py` 是「**不累積就永久失去**」那一族的第三個
（前兩個：集保、開休市行事曆）。這一族壞掉的樣子都一樣：
**管線是綠的、檔案在、格式對，只是內容沒有長大**。

⛔ 而且今天已經有兩次教訓，兩次都是同一個原因——**假的比真的簡單**：
  ① `selftest_holiday` 把 `B.get` 換成「一律回錯誤」⇒ `_schedule()` 在第一個
     `if err` 就 return ⇒ `json.loads` 那行從沒跑到 ⇒ 少 import 兩個模組
     一路過關到 Actions。
  ② `selftest_probes` 的假頁面沒有 `<script src>` ⇒ 撈 js 那條分支沒被走到。

⇒ 所以這一支的假回應**逐字照** `otccal_probe.py` 在 Actions 上實測到的形狀
  （民國 7 碼的 `Date`、六個欄位），並且**驗它真的把列寫進累積檔**，
  ⛔ 不是只驗「沒有丟例外」。
"""
import io
import json
import os
import sys
import tempfile

import backfill as _B
import runlog as _RL
import otc_calendar as C

FAIL = []


def ck(name, cond, note=""):
    print(("  ok   " if cond else "  ✗    ") + name + (f"　（{note}）" if note else ""))
    if not cond:
        FAIL.append(name)


# ⛔ 逐字照 Actions 實測（`data/meta/_otccal_probe.txt` [2] 首列）。
ROWS = [{"Date": "1150901", "TradeVolume": "902905474",
         "TradeAmount": "252387964702", "NumberOfTransactions": "1095837",
         "TPExIndex": "410.77", "Change": "9.07"},
        {"Date": "1150902", "TradeVolume": "800000000",
         "TradeAmount": "200000000000", "NumberOfTransactions": "1000000",
         "TPExIndex": "411.11", "Change": "0.34"}]


def _stat(p):
    try:
        return os.stat(p).st_mtime
    except OSError:
        return None


def main():
    print("[1] `_iso()`：民國 7 碼與西元 8 碼**不可以**混為一談")
    ck("民國 1150901 → 2026-09-01", C._iso("1150901") == "2026-09-01", C._iso("1150901"))
    ck("西元 20260901 → 2026-09-01", C._iso("20260901") == "2026-09-01", C._iso("20260901"))
    ck("已是 ISO 就原樣", C._iso("2026-09-01") == "2026-09-01")
    ck("⛔ 認不出來回 None，不亂猜", C._iso("115/9/1") is None
       and C._iso("") is None and C._iso("abc") is None)

    print("[2] 端到端（沙箱，⛔ 不碰 repo 的 data/）")
    d = tempfile.mkdtemp()
    real_out = C.OUT
    real_lastrun = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "data", "meta", "_last_run.md")
    # ⛔ 「跑之前」就記下來。跑完才取兩次＝拿同一個值跟自己比，永遠通過。
    out_before, lr_before = _stat(real_out), _stat(real_lastrun)
    old_out, old_rl, old_get = C.OUT, _RL.PATH, _B.get
    C.OUT = os.path.join(d, "calendar_tpex.csv")
    _RL.PATH = os.path.join(d, "_last_run.md")
    _B.get = lambda *a, **k: (json.dumps(ROWS).encode(), None)
    try:
        sys.argv = ["otc_calendar.py"]
        C.main()
        first = io.open(C.OUT, encoding="utf-8").read()
        ck("寫得出 calendar_tpex.csv", os.path.exists(C.OUT))
        ck("表頭逐字是 " + ",".join(C.HEADER),
           first.splitlines()[0] == ",".join(C.HEADER), first.splitlines()[0])
        ck("兩列假資料都進去了", len(first.strip().splitlines()) == 3,
           f"實際 {len(first.strip().splitlines())} 行（含表頭）")
        ck("民國日期已轉成西元", "2026-09-01" in first and "1150901" not in first)

        # ★★ 這一支的本體是**累積**：第二趟拿到不重疊的新窗口，舊的不可以掉。
        #   ⛔ 只跑一趟只證明「寫得出來」，證明不了「會長大」。
        _B.get = lambda *a, **k: (json.dumps(
            [{"Date": "1150903", "TradeVolume": "1", "TradeAmount": "2",
              "NumberOfTransactions": "3", "TPExIndex": "4", "Change": "5"}]
        ).encode(), None)
        C.main()
        second = io.open(C.OUT, encoding="utf-8").read()
        ck("★ 第二趟是**累積**不是覆蓋（舊的兩天還在）",
           "2026-09-01" in second and "2026-09-02" in second
           and "2026-09-03" in second,
           f"{len(second.strip().splitlines()) - 1} 天")

        # ⛔ 抓不到時**不可以**把累積檔寫短。這一族失去的資料補不回來。
        _B.get = lambda *a, **k: (None, "selftest：假裝 403")
        C.main()
        third = io.open(C.OUT, encoding="utf-8").read()
        ck("★ 抓不到時累積檔原封不動（⛔ 不可以寫短）", third == second,
           f"{len(second.strip().splitlines()) - 1} → "
           f"{len(third.strip().splitlines()) - 1} 天")
    finally:
        C.OUT, _RL.PATH, _B.get = old_out, old_rl, old_get

    print("[3] ⛔ 真的去看檔案系統，不是宣告自己沒事")
    ck("★ 沒有動到 repo 真的 calendar_tpex.csv", out_before == _stat(real_out),
       f"{out_before} → {_stat(real_out)}")
    ck("★ 沒有動到 repo 真的 _last_run.md", lr_before == _stat(real_lastrun),
       f"{lr_before} → {_stat(real_lastrun)}")

    print()
    if FAIL:
        print(f"⛔ {len(FAIL)} 項沒過：{FAIL}")
        return 1
    print("全過")
    return 0


if __name__ == "__main__":
    sys.exit(main())
