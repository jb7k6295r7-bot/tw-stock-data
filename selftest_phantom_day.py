# -*- coding: utf-8 -*-
"""selftest：休市日興櫃端點回前一天 ⇒ ① 不採用 ② 已寫進去的假日檔會被刪掉、真的交易日不動。
（2026-09-25 中秋：上市上櫃正確回休市，興櫃 361 列 Date=1150924 被寫成 09-25 的日檔）"""
import os, sys, tempfile
import fetch

H = fetch.UNIVERSE_HEADER
bad = 0
def ok(cond, msg):
    global bad
    print(("ok  " if cond else "✗   ") + msg)
    bad += (not cond)

# ① _list_said_day
ok(fetch._list_said_day([{"Date": "1150924", "SecuritiesCompanyCode": "1260"}]) == "20260924", "民國 7 碼 Date 讀成西元")
ok(fetch._list_said_day([{"SecuritiesCompanyCode": "1260"}]) == "", "沒有日期欄 ⇒ 不擋")
ok(fetch._list_said_day([{"Date": "1150924"}, {"Date": "1150925"}]) == "20260924/20260925", "各列日期不一致 ⇒ 全列出（必不等於任一天）")
ok(fetch._list_said_day([]) == "", "空 list ⇒ 不擋（交給休市那條）")

# ② purge_phantom_days
def row(day, sid, mk, close):
    r = {h: "" for h in H}
    r.update(key=f"{day}_{sid}", date=day, stock_id=sid, name="x", market=mk, close=close, volume="10")
    return [r[h] for h in H]

with tempfile.TemporaryDirectory() as t:
    fetch.UNI_DIR = t
    fetch.COVERAGE = os.path.join(t, "_coverage_daily.csv")
    dd = os.path.join(t, "daily"); os.makedirs(dd)
    def put(day, rows):
        with open(os.path.join(dd, f"{day}.csv"), "w", encoding="utf-8") as f:
            f.write(",".join(H) + "\n")
            for r in rows: f.write(",".join(r) + "\n")
    put("2026-09-23", [row("2026-09-23", "2330", "twse", "1"), row("2026-09-23", "1260", "emerging", "9")])
    put("2026-09-24", [row("2026-09-24", "2330", "twse", "1"), row("2026-09-24", "1260", "emerging", "30")])
    put("2026-09-25", [row("2026-09-25", "1260", "emerging", "30")])           # 假日檔：與 09-24 相同
    put("2026-09-28", [row("2026-09-28", "1260", "emerging", "31")])           # 只有興櫃、但數字不同 ⇒ 不刪
    with open(fetch.COVERAGE, "w", encoding="utf-8") as f:
        f.write(",".join(fetch.COV_HEADER) + "\n")
        f.write("2026-09-23,1,0,1,2,ok\n2026-09-24,1,0,1,2,ok\n")
        f.write("2026-09-25,0,0,1,1,twse=stat=x;tpex=休市或無成交\n2026-09-28,0,0,1,1,ok\n")
    gone = fetch.purge_phantom_days()
    left = sorted(os.listdir(dd))
    ok(len(gone) == 1 and gone[0].startswith("2026-09-25"), f"刪掉 09-25 假日檔：{gone}")
    ok("2026-09-24.csv" in left and "2026-09-23.csv" in left, "真的交易日不動")
    ok("2026-09-28.csv" in left, "只有興櫃但數字不同 ⇒ 不刪（寧可漏刪）")
    cov = open(fetch.COVERAGE, encoding="utf-8").read()
    ok("2026-09-25,0,0,0,0," in cov and "已刪" in cov, "覆蓋率帳 09-25 改為 0 並註明")
    ok(fetch.purge_phantom_days() == [], "再跑一次不再刪（冪等）")

print("✓ 全部通過" if not bad else f"✗ {bad} 項沒過")
sys.exit(1 if bad else 0)
