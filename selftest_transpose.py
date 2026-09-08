#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_transpose.py — 離線驗 transpose.py 的四層轉置。**不碰真的 data/。**

★ 為什麼要跑：2026-09-07 幫 `margin` 與 `per` 加上個股軸時，改的是 `SRC`／`OUT`
  兩個 dict 看起來很安全——但這支程式**合併多個來源目錄**，而合併正是它最會靜默出錯的地方：
  表頭差一欄、代號在兩個市場重疊、跨 chunk 之後日期不再升冪，
  三種都**不會報錯**，只會產出一份看起來正常的個股庫。

  `inst` 當初就踩過一次：`otcinst` 補完 2,844 天，跑完 transpose 個股庫卻一列都沒多，
  因為程式只讀 `inst`。**列數與檔數都「正常」，只是少了一半。**

做法：在 tempdir 造一個小 universe，種下已知的東西再檢查有沒有剛好對上。
"""
import csv
import io
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REAL_DATA = os.path.join(HERE, "data")

DAYS = ["2026-09-01", "2026-09-02", "2026-09-03"]
MG = "date,stock_id,m_buy,m_sell,m_balance,m_limit,s_buy,s_sell,s_balance"
PR = "date,stock_id,close,yield_pct,dividend_year,per,pbr,fs_quarter"
TW = ["2330", "2317"]          # 上市
OT = ["8299", "6488"]          # 上櫃


def write(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(header + "\n")
        for r in rows:
            f.write(",".join(str(x) for x in r) + "\n")


def build_fixture(root, break_header=False, overlap=False, skip_price_inst=False):
    uni = os.path.join(root, "data", "universe")
    for i, d in enumerate(DAYS):
        # margin：上市 / 上櫃 各一檔
        write(os.path.join(uni, "margin", f"{d}.csv"), MG,
              [[d, c, 1, 2, 100 + i, 999, 0, 0, 5] for c in TW])
        h = MG + ",extra" if break_header else MG
        ot = OT + (["2330"] if overlap else [])
        write(os.path.join(uni, "otcmargin", f"{d}.csv"), h,
              [[d, c, 1, 2, 200 + i, 999, 0, 0, 5] + ([9] if break_header else [])
               for c in ot])
        # per
        write(os.path.join(uni, "per", f"{d}.csv"), PR,
              [[d, c, 100 + i, 2.5, 114, 15.0, 3.0, "114/2"] for c in TW])
        write(os.path.join(uni, "otcper", f"{d}.csv"), PR,
              [[d, c, 50 + i, 1.5, 114, 25.0, 4.0, "114/2"] for c in OT])
    # ★ price 與 inst 也要造，否則 `--kind all` 那一趟會因為那兩層沒來源而回非 0，
    #   測到的就不是「四層合併對不對」而是「缺目錄會不會失敗」——那是另一個案例。
    #   （第一版就是這樣：兩個判定失敗，看起來像程式壞了，其實是 fixture 沒造齊。）
    if not skip_price_inst:
        DAILY = ("key,date,stock_id,name,market,open,high,low,close,volume,amount,"
                 "change,limit,shares,transactions,price_basis")
        INST = "date,stock_id,foreign,trust,dealer,total"
        for i, d in enumerate(DAYS):
            write(os.path.join(uni, "daily", f"{d}.csv"), DAILY,
                  [[f"{d}_{c}", d, c, f"N{c}", "twse", 10, 11, 9, 10 + i,
                    1000, 10000, 0.1, "", "", 50, ""] for c in TW + OT])
            write(os.path.join(uni, "inst", f"{d}.csv"), INST,
                  [[d, c, 1, 2, 3, 6] for c in TW])
            write(os.path.join(uni, "otcinst", f"{d}.csv"), INST,
                  [[d, c, 1, 2, 3, 6] for c in OT])
    shutil.copy(os.path.join(HERE, "transpose.py"), root)
    # transpose.py 會 import runlog 寫 _last_run.md，沙盒裡也要有它，
    # 否則整支在 import 就死掉，而失敗訊息看起來像轉置本身壞了。
    shutil.copy(os.path.join(HERE, "runlog.py"), root)


def run(root, kind):
    p = subprocess.run([sys.executable, "transpose.py", "--kind", kind],
                       cwd=root, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def rows_of(path):
    with io.open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    real_before = os.path.isdir(REAL_DATA)
    ok = fail = 0

    def chk(name, cond, hint=""):
        nonlocal ok, fail
        if cond:
            ok += 1
            print(f"  ✓ {name}")
        else:
            fail += 1
            print(f"  ✗ {name}" + (f"｜{hint}" if hint else ""))

    # ── 正常案例 ──
    root = tempfile.mkdtemp(prefix="tposetest_")
    try:
        build_fixture(root)
        rc, out = run(root, "all")
        print(out)
        print("── 判定：正常案例 ──")
        chk("四層一起跑，回傳碼 0", rc == 0, f"rc={rc}")
        chk("有逐層結果摘要（不是只給一個 exit code）",
            "逐層結果" in out and out.count(" ok") >= 4, out[-400:])

        for kind, n_codes in (("margin", 4), ("per", 4)):
            d = os.path.join(root, "data", f"stocks_{kind}")
            files = sorted(n for n in os.listdir(d) if n.endswith(".csv")
                           and not n.startswith("_"))
            chk(f"{kind}：上市＋上櫃合併成 {n_codes} 檔",
                len(files) == n_codes, f"實際 {files}")
            # 每檔 3 列、日期升冪
            bad = []
            for n in files:
                rs = rows_of(os.path.join(d, n))
                ds = [r["date"] for r in rs]
                if len(rs) != len(DAYS) or ds != sorted(ds):
                    bad.append((n, len(rs), ds))
            chk(f"{kind}：每檔 3 列且日期升冪", not bad, str(bad))
            # 上櫃的值真的進去了（inst 那次事故就是這裡沒過）
            rs = rows_of(os.path.join(d, "8299.csv"))
            chk(f"{kind}：上櫃 8299 有資料（不是只讀上市那一半）", len(rs) == 3)
            # _index.csv
            idx = rows_of(os.path.join(d, "_index.csv"))
            chk(f"{kind}：_index.csv 有 {n_codes} 列且 rows 都是 3",
                len(idx) == n_codes and all(r["rows"] == "3" for r in idx),
                str(idx))

        chk("margin 與 per 是**分開的**輸出目錄，沒有互相蓋掉",
            rows_of(os.path.join(root, "data", "stocks_margin", "2330.csv"))[0].get("m_buy") == "1"
            and rows_of(os.path.join(root, "data", "stocks_per", "2330.csv"))[0].get("per") == "15.0")

        # ★ both 的意思不可以被偷改
        rc2, out2 = run(root, "both")
        chk("`--kind both` 仍然只做 price＋inst（沒有偷偷擴成四層）",
            "margin" not in out2.split("判定")[0] and "stocks_margin" not in out2)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    # ── 表頭不一致：必須中止，不可以默默合併 ──
    root = tempfile.mkdtemp(prefix="tposetest_")
    try:
        build_fixture(root, break_header=True)
        rc, out = run(root, "margin")
        print("── 判定：表頭不一致 ──")
        chk("上櫃多一欄時整支中止（回傳碼非 0）", rc != 0, f"rc={rc}")
        chk("而且說得出是哪個檔、差在哪", "欄位與先前不同" in out)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    # ── 代號重疊：不擋，但要數出來 ──
    root = tempfile.mkdtemp(prefix="tposetest_")
    try:
        build_fixture(root, overlap=True)
        rc, out = run(root, "margin")
        print("── 判定：代號重疊 ──")
        chk("2330 同時出現在兩個市場時，有把重複列數印出來",
            "同一檔同一天出現兩次" in out, out[-300:])
        rs = rows_of(os.path.join(root, "data", "stocks_margin", "2330.csv"))
        chk("重複的列照寫（3 天 × 2 個市場 = 6 列），沒有被默默丟掉", len(rs) == 6,
            f"實際 {len(rs)} 列")
    finally:
        shutil.rmtree(root, ignore_errors=True)

    # ── 缺來源目錄：要失敗，而且摘要要指名是哪一層 ──
    root = tempfile.mkdtemp(prefix="tposetest_")
    try:
        build_fixture(root, skip_price_inst=True)
        rc, out = run(root, "all")
        print("── 判定：缺來源目錄 ──")
        chk("有一層沒有來源時整趟回非 0", rc != 0, f"rc={rc}")
        chk("摘要指名 price 與 inst 沒完成",
            "這幾層沒有完成" in out and "price" in out and "inst" in out)
        chk("★ 但成功的 margin／per 有寫出來，沒有被整批當成沒跑",
            os.path.isdir(os.path.join(root, "data", "stocks_margin"))
            and os.path.isdir(os.path.join(root, "data", "stocks_per")))
    finally:
        shutil.rmtree(root, ignore_errors=True)

    chk("真的 repo 的 data/ 沒有被建立或改動",
        os.path.isdir(REAL_DATA) == real_before)

    print(f"\n[selftest] 通過 {ok}｜失敗 {fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
