#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""revenue_first_seen 的自測。不連網、不碰真的 data/。"""
import datetime, io, os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import revenue_first_seen as R   # noqa: E402
OK = FAIL = 0


def ck(name, cond):
    global OK, FAIL
    if cond:
        OK += 1; print("  ok   " + name)
    else:
        FAIL += 1; print("  ✗    " + name)


T = datetime.timezone(datetime.timedelta(hours=8))
ck("1 日 ⇒ 上個月", R.target_period(datetime.datetime(2026, 10, 1, tzinfo=T)) == "2026-09")
ck("20 日 ⇒ 上個月", R.target_period(datetime.datetime(2026, 10, 20, tzinfo=T)) == "2026-09")
ck("21 日 ⇒ 不打", R.target_period(datetime.datetime(2026, 10, 21, tzinfo=T)) is None)
ck("1 月 ⇒ 去年 12 月", R.target_period(datetime.datetime(2027, 1, 5, tzinfo=T)) == "2026-12")
d = tempfile.mkdtemp()
try:
    R.BASE = d
    os.makedirs(os.path.join(d, "2026-09"))
    def w(name, rows):
        with io.open(os.path.join(d, "2026-09", name), "w", encoding="utf-8") as f:
            f.write("stock_id,market,part,revenue\n" + "".join("%s,sii,0,1\n" % r for r in rows))
    w("2026-10-09T162342_first.csv", ["1101", "2330"])
    w("2026-10-09T234700.csv", ["1102"])
    w("2026-10-10T182300.csv", ["1102", "2317"])     # 工作樹舊時重記 1102 ⇒ 取最小
    s = R.summary("2026-09")
    ck("首趟 censored＝1", s["1101"][1] == 1 and s["2330"][1] == 1)
    ck("之後 censored＝0", s["1102"][1] == 0 and s["2317"][1] == 0)
    ck("重記取最小時戳", s["1102"][0] == "2026-10-09T234700")
    ck("家數", len(s) == 4)
finally:
    shutil.rmtree(d)
print("[selftest] 通過 %d｜失敗 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
