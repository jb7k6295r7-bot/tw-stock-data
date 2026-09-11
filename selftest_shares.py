#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_shares.py — 離線驗 shares_check 的守門，**尤其是那道日期驗證**。

⛔ 這一支要逼出來的四條分支：

  ① 正常：欄位對得上、日期對得上 ⇒ 解析得出列
  ② ⛔⛔ **端點靜靜回「今天」**（日期格式寫錯時的真實行為）⇒ 必須整批拒收
     ⚠ 沒有這道驗證的話，回補歷史時每天都拿到今天的數字，而且看起來完全正常
  ③ 回 0 列 ⇒ 當失敗，⛔ 不是「那天沒有股票」
  ④ 欄位對不上 ⇒ 講得出缺哪一個，不猜別的欄

⭐ 每一條都要**證明它會擋下來**，不是只證明正常情況會過。
"""
import io
import json
import os
import sys

import shares_check as S

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


FIELDS = ["排名", "股票代號", "股票名稱", "發行股數", "收盤價", "市值(佰萬元)"]


def payload(roc, rows, fields=None):
    return {"stat": "ok", "date": roc,
            "tables": [{"title": f"{roc} 個股市值排行",
                        "fields": fields or FIELDS, "data": rows}]}


def main():
    real = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "data", "meta", "shares_official_tpex.csv")
    before = os.path.exists(real)

    # ① 正常
    good = payload("115/09/09",
                   [[1, "6104", "創惟", "91,129,107", "92.50", "8,429"],
                    [2, "8921", "沈氏", "1,000,000", "10.00", "10"]])
    rows, note = S.parse(good, "2026-09-09")
    ck("① 正常回應解析得出兩列", len(rows) == 2, note)
    ck("① 逗號有拿掉、日期填成 ISO",
       rows and rows[0][3] == "91129107" and rows[0][0] == "2026-09-09",
       str(rows[:1]))

    # ② ⛔⛔ 端點靜靜回「今天」——我請求 2015-01-05，它回 115/09/09
    rows2, note2 = S.parse(good, "2015-01-05")
    ck("② ⛔ 回應講的是別天時**整批拒收**（不是照收）", not rows2, note2)
    ck("② 而且訊息講得出那個陷阱",
       "靜靜回今天" in note2 or "沒有講出我請求的日期" in note2, note2)

    # ③ 0 列
    rows3, note3 = S.parse(payload("115/09/09", []), "2026-09-09")
    ck("③ 回 0 列 ⇒ 當失敗，⛔ 不是「那天沒有股票」",
       not rows3 and "0 列當失敗" in note3, note3)

    # ④ 欄位對不上
    rows4, note4 = S.parse(
        payload("115/09/09", [[1, "6104", "創惟", "1"]],
                fields=["排名", "股票代號", "股票名稱", "成交量"]),
        "2026-09-09")
    ck("④ 欄位對不上 ⇒ 講得出缺哪一個",
       not rows4 and "缺" in note4 and "shares" in note4, note4)

    # ⑤ roc_slash 的兩端
    ck("⑤ 2026-09-09 → 115/09/09", S.roc_slash("2026-09-09") == "115/09/09",
       S.roc_slash("2026-09-09"))
    ck("⑤ 2015-01-05 → 104/01/05", S.roc_slash("2015-01-05") == "104/01/05",
       S.roc_slash("2015-01-05"))

    ck("★ 沒有動到 repo 真的累積檔", os.path.exists(real) == before)
    print("⑥ ⛔ 只有「當天的還沒出」才准退一天（⚠ 更早的 0 列是真的失敗）")
    # ⭐ 2026-09-10 的紅燈：`ds[-1]` 是我方最新日檔＝當天，
    #   而櫃買的個股市值排行**當天下午還沒出** ⇒ 回 0 列。
    #   ⚠ 同一天、兩份官方資料，**發布時間不同**。
    # ⛔ 這一節測的是**行為**，不是原始碼裡有沒有那串字
    #   ——「斷言字串跟程式脫節的話，那條就變成在測字串」。
    import datetime as _dt
    import json as _json
    import shutil as _sh
    import tempfile as _tf

    import backfill as _B
    import runlog as _RL
    import shares_check as _S

    _today = _dt.datetime.now(_S.TPE).strftime("%Y-%m-%d")
    _yest = (_dt.datetime.now(_S.TPE) - _dt.timedelta(days=1)).strftime("%Y-%m-%d")

    def _payload(day, n):
        """n 列的假回應。⚠ 形狀照真回應：tables[0] 有 fields/data，title 帶日期。"""
        # ⚠ 欄名逐字照 `parse()` 要的那幾個（`發行股數`／`收盤價`）——
        #   ⛔ 假回應比真的簡單就等於那一段沒測。
        f = ["排名", "代號", "名稱", "收盤價", "發行股數", "市值(百萬元)"]
        d = [[str(i + 1), f"{1100 + i}", "假", "10.00", "1000000", "10"]
             for i in range(n)]
        return _json.dumps({"stat": "ok",
                            "tables": [{"title": f"個股市值排行 {day.replace('-', '')}",
                                        "fields": f, "data": d}]}).encode()

    def _run(days_on_disk, rows_by_day):
        """→ (問過哪幾天, runlog 文字)。⛔ 全部導到沙箱，不碰 repo。"""
        sand = _tf.mkdtemp(prefix="sc_")
        asked = []
        old = (_S.DAILY, _RL.PATH, _B.get, _S.OUT if hasattr(_S, "OUT") else None)
        try:
            _S.DAILY = os.path.join(sand, "daily")
            os.makedirs(_S.DAILY)
            for d in days_on_disk:
                io.open(os.path.join(_S.DAILY, d + ".csv"), "w",
                        encoding="utf-8").write("stock_id,shares\n1101,1\n")
            _RL.PATH = os.path.join(sand, "lr.md")
            if hasattr(_S, "OUT"):
                _S.OUT = os.path.join(sand, "out.csv")

            def _fake(url, retries=3, timeout=60):
                # 從 URL 裡把民國日期還原成西元，決定回幾列
                import re as _re
                m = _re.search(r"(\d{3})/(\d{2})/(\d{2})", url)
                d = (f"{int(m.group(1)) + 1911}-{m.group(2)}-{m.group(3)}"
                     if m else "?")
                asked.append(d)
                return _payload(d, rows_by_day.get(d, 0)), None
            _B.get = _fake
            sys.argv = ["shares_check.py"]
            try:
                _S.main()
            except SystemExit:
                pass
            txt = (io.open(_RL.PATH, encoding="utf-8").read()
                   if os.path.exists(_RL.PATH) else "")
            return asked, txt
        finally:
            _S.DAILY, _RL.PATH, _B.get = old[0], old[1], old[2]
            if old[3] is not None:
                _S.OUT = old[3]
            _sh.rmtree(sand, ignore_errors=True)

    a1, t1 = _run([_yest, _today], {_today: 0, _yest: 5})
    ck("  ⭐ 今天回 0 列 ⇒ **退到前一個交易日再問一次**",
       a1 == [_today, _yest], str(a1))
    ck("  ⚠ 而且退的理由有寫進報告", "當天的還沒出" in t1,
       [l for l in t1.splitlines() if "還沒出" in l])

    a2, t2 = _run([_yest, _today], {_today: 5, _yest: 5})
    ck("  今天有列 ⇒ **不多問一次**（⛔ 不要每天多打對方一發）",
       a2 == [_today], str(a2))

    # ★★ 反向：**更早**的日子回 0 列 ⇒ ⛔ 不准退，那是真的失敗
    a3, t3 = _run(["2026-09-01", "2026-09-02"], {})
    ck("  ★ 最後一個日檔不是今天且回 0 列 ⇒ **只問一次就認賠**",
       a3 == ["2026-09-02"], str(a3))
    ck("  ★ 而且那一趟是 ✗（⛔ 判準沒有被放寬）", "**✗**" in t3,
       [l for l in t3.splitlines() if "✗" in l][:2])

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
