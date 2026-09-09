#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""驗 `suspend_twse.main()` 整條走得完，⛔ 而且驗它**會擋下該擋的**。

    python3 selftest_suspend_twse.py

這一支盯三件會靜默出錯的事：

1. **民國年沒轉成西元** ——`115/08/13` 與 `2015-08-13` 長得都像日期，
   錯一個世紀不會有人發現。
2. **`title` 的期間回音沒對上** ——那是**唯一**能證明 startDate/endDate
   有生效的東西（`TWT49U` 就是回音沒對上，把 2026 的資料寫進 2015 的每一天）。
3. **整份重寫寫短了** ——這一支不是累積式而是每趟整份重寫，
   寫短了就是資料掉了，而檔案還在、格式還對。
"""
import io
import json
import os
import sys
import tempfile

import backfill as _B
import runlog as _RL
import suspend_twse as S

FAIL = []


def ck(name, cond, note=""):
    print(("  ok   " if cond else "  ✗    ") + name + (f"　（{note}）" if note else ""))
    if not cond:
        FAIL.append(name)


def body(title, data):
    return json.dumps({
        "stat": "OK", "title": title,
        "fields": ["編號", "證券代號", "證券名稱", "暫停交易日期",
                   "暫停交易時間", "恢復交易日期", "恢復交易時間"],
        "data": data}, ensure_ascii=False).encode()


ROWS3 = [[1, "1218", "泰山", "115/08/13", "8:00", "115/08/14", "8:00"],
         [2, "4414", "如興", "107/02/26", "8:00", "107/02/27", "8:00"],
         [3, "9136", "巨路", "115/04/23", "8:00", "115/05/19", "8:00"]]


def run(raw, out, lastrun):
    old = (S.OUT, _RL.PATH, _B.get)
    S.OUT, _RL.PATH = out, lastrun
    _B.get = lambda *a, **k: (raw, None)
    try:
        sys.argv = ["suspend_twse.py"]
        S.main()
        return io.open(lastrun, encoding="utf-8").read()
    finally:
        S.OUT, _RL.PATH, _B.get = old


def main():
    import datetime as dt
    today = dt.datetime.now(S.TPE).strftime("%Y-%m-%d")
    roc = f"{int(today[:4]) - 1911}/{today[5:7]}/{today[8:]}"
    good = f"暫停交易證券 查詢範圍：全部上市證券 期間：104/01/01 到 {roc}"

    print("[1] `roc_to_iso()`：⛔ 民國與西元不可以混")
    ck("115/08/13 → 2026-08-13", S.roc_to_iso("115/08/13") == "2026-08-13",
       S.roc_to_iso("115/08/13"))
    ck("104/01/01 → 2015-01-01", S.roc_to_iso("104/01/01") == "2015-01-01")
    ck("⛔ 認不出回 None，不猜", S.roc_to_iso("2026-08-13") is None
       and S.roc_to_iso("") is None and S.roc_to_iso("abc") is None)

    print("[2] `title_range()`：唯一能證明參數生效的東西")
    ck("抽得出兩個日期", S.title_range(good) == ("2015-01-01", today),
       str(S.title_range(good)))
    ck("⛔ 沒有『期間』就回 (None, None)",
       S.title_range("暫停交易證券") == (None, None))

    d = tempfile.mkdtemp()
    out = os.path.join(d, "suspend_twse.csv")
    lr = os.path.join(d, "_last_run.md")
    real_out = S.OUT
    real_lr = _RL.PATH
    before = (os.path.exists(real_out), os.path.getmtime(real_lr)
              if os.path.exists(real_lr) else None)

    print("[3] 端到端（沙箱）")
    txt = run(body(good, ROWS3), out, lr)
    csvtxt = io.open(out, encoding="utf-8").read()
    ck("寫得出 suspend_twse.csv", os.path.exists(out))
    ck("表頭逐字", csvtxt.splitlines()[0] == ",".join(S.HEADER),
       csvtxt.splitlines()[0])
    ck("三列都在", len(csvtxt.strip().splitlines()) == 4)
    ck("★ 民國已轉西元（檔案裡不可以留 115/）",
       "2026-08-13" in csvtxt and "115/08/13" not in csvtxt)
    ck("★ 算得出停牌天數（9136 是 26 天）", ",26" in csvtxt,
       [l for l in csvtxt.splitlines() if l.startswith("9136")])
    ck("title 期間對得上 ⇒ 那一項是 ok", "**✗**　title 的期間" not in txt)

    print("[4] ★★ 驗它**擋得下**該擋的（⛔ 沒證明過會失敗的測試不算測試）")
    bad = "暫停交易證券 查詢範圍：全部上市證券 期間：115/08/13 到 115/08/13"
    txt2 = run(body(bad, ROWS3), os.path.join(d, "b.csv"),
               os.path.join(d, "b.md"))
    ck("★ 回音對不上 ⇒ 那一項要變 ✗（TWT49U 那種假生效）",
       "**✗**　title 的期間" in txt2)

    # 整份重寫寫短了 ⇒ 不可以覆蓋
    txt3 = run(body(good, ROWS3[:1]), out, lr)
    after = io.open(out, encoding="utf-8").read()
    ck("★ 列數變少 ⇒ 報 ✗", "**✗**　列數只增不減" in txt3)
    ck("★ 列數變少 ⇒ **不覆蓋**，舊檔原封不動", after == csvtxt,
       f"{len(csvtxt.strip().splitlines()) - 1} → "
       f"{len(after.strip().splitlines()) - 1} 列")

    print("[5] ⛔ 真的去看檔案系統")
    ck("★ 沒有動到 repo 真的 suspend_twse.csv",
       os.path.exists(real_out) == before[0])
    ck("★ 沒有動到 repo 真的 _last_run.md",
       (os.path.getmtime(real_lr) if os.path.exists(real_lr) else None)
       == before[1])

    print()
    if FAIL:
        print(f"⛔ {len(FAIL)} 項沒過：{FAIL}")
        return 1
    print("全過")
    return 0


if __name__ == "__main__":
    sys.exit(main())
