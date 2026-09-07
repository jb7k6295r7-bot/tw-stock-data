#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""capital.py --run 的自測。**不連任何網路**：把 capital.get() 換成假端點。

為什麼要有這一支：2026-09-07 抓到的 bug 是「上櫃有股數、股本全空」，
而那個狀態**跑起來完全正常**——沒有例外、沒有錯誤訊息、`_capital_missing.txt`
也不會列它（那個檔只看股數缺不缺）。這種只能靠自測釘住。

跑法：python3 selftest_capital.py
"""
import csv
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FAILED = []


def _cap_mtime():
    p = os.path.join(HERE, "data", "meta", "capital.csv")
    return os.path.getmtime(p) if os.path.exists(p) else None


# 開跑前先把 repo 現況記下來，跑完再比對——證據要在被檢查的東西外面
REPO_DATA_BEFORE = os.path.exists(os.path.join(HERE, "data"))
REPO_CAP_MTIME = _cap_mtime()


def ck(cond, msg):
    print(("  ok   " if cond else "  ✗ 失敗 ") + msg)
    if not cond:
        FAILED.append(msg)


def _row(code, name, cap, shr, par="10"):
    return {"SecuritiesCompanyCode": code, "CompanyName": name,
            "ParValueOfCommonStock": par, "Paidin.Capital.NTDollars": cap,
            "PreferredStock.shares": "0", "IssueShares": shr}


def _twse_row(code, name, cap, shr, par="10"):
    return {"公司代號": code, "公司名稱": name, "普通股每股面額": par,
            "實收資本額": cap, "特別股": "0",
            "已發行普通股數或TDR原股發行股數": shr}


def build_sandbox(tmp, daily_rows):
    d = os.path.join(tmp, "data", "universe", "daily")
    os.makedirs(d)
    with open(os.path.join(d, "2026-09-04.csv"), "w", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["stock_id", "name", "market", "close", "volume", "shares"])
        for r in daily_rows:
            w.writerow(r)


def run_once(tmp, daily_rows, fake):
    """在 tmp 這個沙箱裡跑一次 cmd_run，回 {code: row}。"""
    sys.path.insert(0, HERE)
    import importlib
    import capital as C
    importlib.reload(C)
    C.UNI_DAILY = os.path.join(tmp, "data", "universe", "daily")
    C.META_DIR = os.path.join(tmp, "data", "meta")
    C.OUT = os.path.join(C.META_DIR, "capital.csv")
    C.MISSING = os.path.join(C.META_DIR, "_capital_missing.txt")
    C.get = lambda url, retries=1, timeout=40: fake(url)
    rc = C.cmd_run(None)
    out = {}
    if os.path.exists(C.OUT):
        with open(C.OUT, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                out[r["stock_id"]] = r
    return rc, out


def main():
    print("=" * 66)
    print("capital.py --run 自測（不連網）")
    print("=" * 66)

    # 上櫃 8299：daily 有官方股數；端點另外給得出股本
    # 上市 1101：daily 沒股數，端點兩者都給
    # 上櫃 00679B：ETF，端點查無此檔
    daily = [["8299", "群聯", "tpex", "500", "1000", "199000000"],
             ["1101", "台泥", "twse", "30", "5000", ""],
             ["00679B", "元大美債20年", "tpex", "30", "100", "50000000"]]

    O = json.dumps([_row("8299", "群聯電子", "1990000000", "199000000")]).encode()
    L = json.dumps([_twse_row("1101", "臺灣水泥", "77231817420",
                              "7523181742")]).encode()

    def fake(url):
        if "opendata/t187ap03_L" in url:
            return L, None
        if "mopsfin_t187ap03_O" in url:
            return O, None
        return None, "HTTP 404"

    # ── 情境一：正常一趟
    print("\n[1] 正常跑一趟")
    tmp = tempfile.mkdtemp()
    try:
        build_sandbox(tmp, daily)
        rc, out = run_once(tmp, daily, fake)
        ck(rc == 0, "結束碼 0")
        ck("8299" in out, "上櫃 8299 有落檔")
        ck(out["8299"]["shares"] == "199000000",
           "上櫃股數仍用 daily 的官方值（不被端點覆蓋）")
        ck(out["8299"]["capital"] == "1990000000",
           "★ 上櫃股本補進來了（這就是 2026-09-07 修的那個 bug）")
        ck(out["8299"]["source"].startswith("universe:") and
           "tpex-mopsfin-O" in out["8299"]["source"],
           "source 同時記下兩個來源")
        ck(out["1101"]["capital"] == "77231817420", "上市股本照舊補得到")
        ck(out["00679B"]["capital"] == "", "端點查無的 ETF 股本留空，不亂填")
        ck(out["00679B"]["shares"] == "50000000", "ETF 的 daily 股數仍保留")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # ── 情境二：第二趟端點全掛，已抓到的股本不可以被洗掉
    print("\n[2] 第二趟端點全掛（① 不可以把上一趟的股本清成空白）")
    tmp = tempfile.mkdtemp()
    try:
        build_sandbox(tmp, daily)
        run_once(tmp, daily, fake)
        rc, out = run_once(tmp, daily, lambda url: (None, "HTTP 503"))
        ck(rc == 0, "端點全掛仍正常結束（本來就是 continue-on-error 的設計）")
        ck(out["8299"]["capital"] == "1990000000",
           "★ 上櫃股本沒有被洗掉")
        ck(out["1101"]["capital"] == "77231817420", "上市股本沒有被洗掉")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # ── 情境三：兩邊股數不一致要留痕
    print("\n[3] daily 與端點的股數不一致 → 要寫進 note，不可以安靜吃掉")
    tmp = tempfile.mkdtemp()
    try:
        build_sandbox(tmp, daily)
        O2 = json.dumps([_row("8299", "群聯電子", "1990000000",
                              "198000000")]).encode()

        def fake2(url):
            if "mopsfin_t187ap03_O" in url:
                return O2, None
            return None, "HTTP 404"

        rc, out = run_once(tmp, daily, fake2)
        ck("股數以 daily 為準" in out["8299"]["note"], "★ 不一致有寫進 note")
        ck(out["8299"]["shares"] == "199000000", "股數仍以 daily 為準")
        # ★★ 這一項是 2026-09-07 當天釘上去的：
        #    端點自己那一對（1990000000 ÷ 198000000）不是整數 10，但那是端點的快照較舊，
        #    不是資料壞掉。面額要用端點自己那一對驗，**不可以拿端點的資本額 ÷ daily 的股數**
        #    ——那樣會把 37 檔乾淨的資料標成 mismatch，而 mismatch 的意思是
        #    「這一檔的股數不要拿來算佔股本比重」。
        ck(not out["8299"]["note"].startswith("mismatch"),
           "★ 兩源日期不同不可以被誤判成 mismatch")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # ── 情境四：端點自己那一對真的對不起來，才可以標 mismatch
    print("\n[4] 端點自己的資本額與股數對不起來 → 這才是真的 mismatch")
    tmp = tempfile.mkdtemp()
    try:
        build_sandbox(tmp, daily)
        O3 = json.dumps([_row("8299", "群聯電子", "1990000000",
                              "398000000")]).encode()   # 比值 5，不是 10

        def fake3(url):
            if "mopsfin_t187ap03_O" in url:
                return O3, None
            return None, "HTTP 404"

        rc, out = run_once(tmp, daily, fake3)
        ck(out["8299"]["note"].startswith("mismatch"),
           "★ 端點自己對不起來時仍然要標 mismatch（不可以連真警報一起關掉）")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # ── 情境五：真的沒動到 repo 的 data/
    #   ⚠ 這一節不可以寫成 ck(True, ...)。斷言自己成立＝循環自證，
    #   本專案 2026-09-07 才因為同一件事重跑過整套稽核。
    print("\n[5] 沙箱隔離（真的去看檔案系統，不是宣告自己沒事）")
    ck(REPO_DATA_BEFORE == os.path.exists(os.path.join(HERE, "data")),
       "跑完之後 repo 的 data/ 存在與否沒有改變")
    if not REPO_DATA_BEFORE:
        ck(not os.path.exists(os.path.join(HERE, "data")),
       "★ 沒有在 repo 底下生出 data/（測試若寫錯路徑，這裡會抓到）")
    else:
        ck(REPO_CAP_MTIME == _cap_mtime(),
           "★ repo 的 data/meta/capital.csv 沒有被動到（mtime 不變）")

    print("\n" + "=" * 66)
    if FAILED:
        print(f"✗ {len(FAILED)} 項失敗：")
        for m in FAILED:
            print("   -", m)
        return 1
    print("全部通過")
    return 0


if __name__ == "__main__":
    sys.exit(main())
