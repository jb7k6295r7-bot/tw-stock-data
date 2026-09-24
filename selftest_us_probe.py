#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""驗 us_probe 的判準分不分得出來（⛔ 離線，不連網、不寫 repo 的輸出檔）。

⭐ 這一支的重點不是「函式跑得完」，是**每一種結論都要有一個會紅的樣本**：
  ⛔ 一條永遠回同一個值的判準，跟一條有效的判準在報告上長得一模一樣。
"""
import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import us_probe as U

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  ok     " + name)
    else:
        FAIL += 1
        print("  ✗      " + name + ("｜" + hint if hint else ""))


def _yahoo(days, closes=None):
    """造一份 Yahoo 形狀的回應。⚠ 日期用 UTC 正午，免得時區把日期推掉一天。"""
    ts = [int(time.mktime(time.strptime(d + " 12:00", "%Y-%m-%d %H:%M"))) for d in days]
    q = {"close": closes if closes else [1.0] * len(days)}
    return json.dumps({"chart": {"result": [
        {"timestamp": ts, "indicators": {"quote": [q]}}]}}).encode()


def main():
    print("① ⛔ 判準不可以是「HTTP 200」或「有回東西」")
    sp = U.yahoo_span(_yahoo(["2020-01-02", "2020-01-03", "2020-01-06"]))
    ck("  ⭐ 正常回應解得出（列數、第一天、最後一天）",
       sp is not None and sp[0] == 3 and sp[1] == "2020-01-02" and sp[2] == "2020-01-06",
       f"實際：{sp}")
    ck("  ⛔⛔ 空的 chart（HTTP 200 但沒有資料）⇒ 必須回 None",
       U.yahoo_span(json.dumps({"chart": {"result": []}}).encode()) is None,
       "⛔ 把空回應當成有資料 ⇒ 整個阻斷項失效")
    ck("  ⛔ result 有但 timestamp 缺 ⇒ 也要回 None",
       U.yahoo_span(json.dumps({"chart": {"result": [{}]}}).encode()) is None)
    ck("  ⛔ 根本不是 JSON（擋機器人的 HTML）⇒ 回 None，⚠ 不可以炸掉",
       U.yahoo_span(b"<html>Too Many Requests</html>") is None)

    print("\n② Stooq 的 CSV 形狀")
    csv = (b"Date,Open,High,Low,Close,Volume\n"
           b"2018-01-02,1,2,0.5,1.5,100\n"
           b"2018-10-15,2,3,1.5,2.5,200\n")
    sp = U.stooq_span(csv)
    ck("  ⭐ 解得出兩列與頭尾日期",
       sp == (2, "2018-01-02", "2018-10-15"), f"實際：{sp}")
    ck("  ⛔⛔ 查不到時 Stooq 回一行純文字（也是 200）⇒ 必須回 None",
       U.stooq_span(b"No data\n") is None)
    ck("  ⛔ 只有表頭沒有資料列 ⇒ 回 None",
       U.stooq_span(b"Date,Open,High,Low,Close,Volume\n") is None)

    print("\n③ ⛔⛔ 下市判準的【四種結論】都要分得出來")
    v_missing = U.delisted_verdict("LEH", 2008, None)[0]
    v_ok = U.delisted_verdict("LEH", 2008, (500, "2000-01-03", "2008-09-12"))[0]
    v_reused = U.delisted_verdict("LEH", 2008, (500, "2000-01-03", "2026-09-23"))[0]
    v_trunc = U.delisted_verdict("LEH", 2008, (500, "2000-01-03", "2005-06-30"))[0]
    ck("  ⛔ 查不到 ⇒ missing（倖存者偏誤的直接證據）", v_missing == "missing")
    ck("  ✅ 最後一天落在下市年 ±1 ⇒ ok", v_ok == "ok")
    ck("  ⛔⛔ 最後一天晚於下市年兩年以上 ⇒ reused"
       "（⚠ 代號被別家重用 ⇒ 查得到比查不到更危險）", v_reused == "reused")
    ck("  ⚠ 最後一天早於下市年 ⇒ truncated（資料被截斷）", v_trunc == "truncated")
    ck("  ★ 四種【互不相同】（⛔ 都回同一個值的話上面四條等於沒跑）",
       len({v_missing, v_ok, v_reused, v_trunc}) == 4,
       f"實際：{[v_missing, v_ok, v_reused, v_trunc]}")
    ck("  ⭐ 而 reused 的訊息要講出「比查不到更危險」（⛔ 不能只說有資料）",
       "更危險" in U.delisted_verdict("LEH", 2008, (5, "2000-01-03", "2026-01-02"))[1])

    print("\n④ 拆股還原：來源已還原 vs 給原始價")
    a = U.split_verdict(120.0, 125.0, 4)[0]      # 比 ≈ 1
    r = U.split_verdict(500.0, 125.0, 4)[0]      # 比 ≈ 4
    u1 = U.split_verdict(250.0, 125.0, 4)[0]     # 比 ≈ 2 ⇒ 兩邊都不像
    u2 = U.split_verdict(None, 125.0, 4)[0]
    u3 = U.split_verdict(120.0, 0.0, 4)[0]       # ⛔ 除以 0 不可以炸
    ck("  ✅ 拆股前/後 ≈ 1 ⇒ adjusted（來源已還原）", a == "adjusted")
    ck("  ⛔ 拆股前/後 ≈ 4 ⇒ raw（我方要自己還原）", r == "raw")
    ck("  ⚠ 兩邊都不像 ⇒ unknown（⛔ 不硬歸類）", u1 == "unknown")
    ck("  ⛔ 取不到價格 ⇒ unknown，⚠ 不猜", u2 == "unknown")
    ck("  ⛔ 分母是 0 也要回 unknown（⚠ 不可以丟 ZeroDivisionError）", u3 == "unknown")
    ck("  ★ adjusted 與 raw 分得出來", a != r)
    ck("  ⭐ 而 adjusted 的訊息要追問「什麼時候重算歷史」"
       "（⚠ 已還原不等於歷史不會變）",
       "重算歷史" in U.split_verdict(120.0, 125.0, 4)[1])

    print("\n⑤ ⭐ 下市樣本本身要是一條梯子（⛔ 年份擠在一起就量不出邊界）")
    yrs = sorted(y for _s, y, _d in U.DELISTED)
    ck("  ⭐ 四檔下市年份互不相同", len(set(yrs)) == 4, f"實際：{yrs}")
    ck("  ⭐ 跨度 ≥ 10 年（⇒ 量得出倖存者邊界落在哪個年代）",
       yrs[-1] - yrs[0] >= 10, f"跨度 {yrs[-1] - yrs[0]} 年")
    ck("  ⛔ 一定要有在市的對照組（⚠ 少了它「全都查不到」分不出成因）",
       U.LIVE[0] and isinstance(U.LIVE[0], str))

    print("\n⑥ ★ 沒有動到 repo 真的輸出檔")
    before = os.path.exists(U.OUT)
    ck("  ★ 這一支自測沒有建立或改動 data/meta/_us_probe.txt",
       os.path.exists(U.OUT) == before)

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
