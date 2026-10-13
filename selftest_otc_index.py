#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""otc_calendar.build_otc_index（櫃買指數日收盤 ⇒ data/history/otc_index.csv）的自測。不連網、不碰真的 data/。"""
import io, os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import otc_calendar as C   # noqa: E402
OK = FAIL = 0


def ck(name, cond):
    global OK, FAIL
    if cond:
        OK += 1; print("  ok   " + name)
    else:
        FAIL += 1; print("  ✗    " + name)


def acc(d, idx, chg):
    return [d, "1", "1", "1", idx, chg, "2026-10-13"]


d = tempfile.mkdtemp()
try:
    seed = os.path.join(d, "seed.csv")
    with io.open(seed, "w", encoding="utf-8") as f:
        f.write("date,volume_k,amount_k_ntd,transactions,tpex_index,change\n"
                "2026-08-28,1,1,1,401.70,2.1\n2026-09-01,1,1,1,410.77,9.07\n")
    C.OTC_INDEX = os.path.join(d, "history", "otc_index.csv")
    rows = {"2026-09-01": acc("2026-09-01", "410.77", "9.07"), "2026-09-02": acc("2026-09-02", "406.96", "-3.81")}
    n, msg = C.build_otc_index(rows, seed)
    out = io.open(C.OTC_INDEX, encoding="utf-8").read().splitlines()
    ck("兩段接起來 3 天", n == 3 and len(out) == 4)
    ck("表頭", out[0] == "date,close,change")
    ck("排序且含種子最早那天", out[1].startswith("2026-08-28,401.70"))
    ck("負號保留", out[3] == "2026-09-02,406.96,-3.81")
    ck("數值相同、寫法不同（9.07 vs 9.070）不算衝突",
       C.build_otc_index({"2026-09-01": acc("2026-09-01", "410.770", "9.070")}, seed)[0] == 2)
    os.remove(C.OTC_INDEX)
    n, msg = C.build_otc_index({"2026-09-01": acc("2026-09-01", "410.78", "9.07")}, seed)
    ck("重疊日對不上 ⇒ -1", n == -1 and "對不上" in msg)
    ck("對不上時一列都不寫", not os.path.exists(C.OTC_INDEX))
    ck("index 空白的累積列不收", C.build_otc_index({"2026-09-03": acc("2026-09-03", "", "")}, seed)[0] == 2)
    ck("沒有種子也能只用累積段", C.build_otc_index(rows, os.path.join(d, "none.csv"))[0] == 2)
finally:
    shutil.rmtree(d)
print("[selftest] 通過 %d｜失敗 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
