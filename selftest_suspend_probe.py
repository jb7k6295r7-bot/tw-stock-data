#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""suspend_probe.py 的自測。**不連網**：把 get() 換成罐頭回應。

要釘住的是探針自己的失效模式：
  ① 欄位名要**照抄**，不可以被改寫、翻譯或補上探針以為該有的欄位
  ② **參數被無視要抓得到**——兩發相同就要判 ✗。這是 TWTAWU `date=` 的真實形狀，
     stat 是 OK、不報錯，只有指紋比對看得出來
  ③ 不同回傳形狀（頂層 fields／tables[i].fields／純 list）都要抄得到欄位名
  ④ 探針**不可以動到 data/ 底下的真資料**
"""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
FAILED = []


def ck(cond, msg):
    print(("  ok   " if cond else "  ✗ 失敗 ") + msg)
    if not cond:
        FAILED.append(msg)


def twse_like(title, rows, fields):
    return json.dumps({"stat": "OK", "title": title, "fields": fields,
                       "data": rows}, ensure_ascii=False).encode()


def tables_like(fields, rows):
    return json.dumps({"stat": "OK", "tables": [
        {"title": "表一", "fields": fields, "data": rows}]},
        ensure_ascii=False).encode()


def run(cands, fake, only="", tmp=None):
    import importlib
    import suspend_probe as P
    importlib.reload(P)
    P.CANDIDATES = cands
    P.get = lambda url, timeout=40: fake(url)
    P.OUT = os.path.join(tmp, "data", "meta", "_suspend_probe.txt")
    sys.argv = ["suspend_probe.py", "--sleep", "0"] + (["--only", only] if only else [])
    P.main()
    return open(P.OUT, encoding="utf-8").read()


def main():
    print("=" * 66)
    print("suspend_probe.py 自測（不連網）")
    print("=" * 66)

    F = ["編號", "證券代號", "證券名稱", "暫停交易日期", "恢復交易日期"]

    # [1] 欄位名照抄 + 指紋不同 → 判 ✓
    print("\n[1] 參數真的有作用（兩發不同）")
    tmp = tempfile.mkdtemp()
    try:
        def fake(u):
            if "20150101" in u:
                return twse_like("期間 104/01/01 到 104/12/31",
                                 [[1, "3051", "力特", "104/04/27", "104/04/30"]], F), None
            return twse_like("期間 109/01/01 到 109/12/31",
                             [[1, "1218", "泰山", "109/08/13", "109/08/14"]], F), None

        r = run([("t", "twse", "http://x?startDate={s}&endDate={e}")], fake, tmp=tmp)
        ck("指紋不同" in r, "指紋不同 → 判 ✓")
        ck("'暫停交易日期'" in r or "暫停交易日期" in r, "★ 欄位名有照抄")
        ck("力特" in r, "首列有照抄（不是只給筆數）")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # [2] ★ 參數被無視 → 一定要判 ✗
    print("\n[2] 參數被無視（兩發一模一樣，stat 仍是 OK）")
    tmp = tempfile.mkdtemp()
    try:
        same = twse_like("期間 115/08/13 到 115/08/13",
                         [[1, "1218", "泰山", "115/08/13", "115/08/14"]], F)
        r = run([("t", "twse", "http://x?date={s}&e={e}")],
                lambda u: (same, None), tmp=tmp)
        ck("這個參數是假的" in r, "★ 抓到參數被無視（TWTAWU date= 的真實形狀）")
        ck("✓ 指紋不同" not in r, "沒有誤判成可用")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # [3] 三種回傳形狀都要抄得到欄位名
    print("\n[3] 回傳形狀")
    tmp = tempfile.mkdtemp()
    try:
        r = run([("a", "tpex", "http://a")],
                lambda u: (tables_like(["代號", "名稱"], [["1", "x"]]), None), tmp=tmp)
        ck("tables[0]" in r and "代號" in r, "tables[i].fields 抄得到")
        r = run([("b", "tpex", "http://b")],
                lambda u: (json.dumps([{"SecuritiesCompanyCode": "1", "X": 2}]).encode(),
                           None), tmp=tmp)
        ck("SecuritiesCompanyCode" in r, "純 list 的鍵名抄得到")
        r = run([("c", "tpex", "http://c")], lambda u: (b"<html>403</html>", None), tmp=tmp)
        ck("不是 JSON" in r and "html" in r, "不是 JSON 時把原文前段抄出來")
        r = run([("d", "tpex", "http://d")], lambda u: (None, "HTTP 403"), tmp=tmp)
        ck("HTTP 403" in r, "失敗原因有寫出來")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # [4] 沒動到真資料
    print("\n[4] 沒有動到 repo 的 data/")
    ck(DATA_BEFORE == os.path.exists(os.path.join(HERE, "data")),
       "★ repo 的 data/ 存在與否沒有改變")

    print("\n" + "=" * 66)
    if FAILED:
        print(f"✗ {len(FAILED)} 項失敗：")
        for m in FAILED:
            print("   -", m)
        return 1
    print("全部通過")
    return 0


DATA_BEFORE = os.path.exists(os.path.join(HERE, "data"))

if __name__ == "__main__":
    sys.exit(main())
