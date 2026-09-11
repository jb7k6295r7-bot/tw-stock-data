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


# ★ 2026-09-09：融資融券補存四欄，**接在舊表頭後面**。
#   ⇒ 回補進行到一半時，同一個 kind 底下會同時有 9 欄與 13 欄的日檔。
MG13 = MG + ",m_prev,m_ret,s_prev,s_ret"
# ⛔ 而「表頭不一致要中止」那條原本的測試，fixture 是「多一欄 extra」——
#   那在新規則下**是合法的加欄**。⇒ 那個 fixture 不再測得到它要測的東西，
#   改成**換欄序**（欄名一樣、位置不同），那才是真的錯位。
MGX = "date,stock_id,m_sell,m_buy,m_balance,m_limit,s_buy,s_sell,s_balance"


def build_fixture(root, break_header=False, overlap=False, skip_price_inst=False,
                  grow_header=False):
    uni = os.path.join(root, "data", "universe")
    for i, d in enumerate(DAYS):
        # margin：上市 / 上櫃 各一檔
        write(os.path.join(uni, "margin", f"{d}.csv"), MG,
              [[d, c, 1, 2, 100 + i, 999, 0, 0, 5] for c in TW])
        h = MGX if break_header else (MG13 if grow_header else MG)
        ot = OT + (["2330"] if overlap else [])
        # ⭐ grow_header：只有**上櫃**那半邊有新四欄，上市那半邊還是舊 9 欄
        #   ——這正是回補跑到一半的樣子。
        write(os.path.join(uni, "otcmargin", f"{d}.csv"), h,
              [[d, c, 1, 2, 200 + i, 999, 0, 0, 5]
               + ([11, 12, 13, 14] if grow_header else []) for c in ot])
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


def run(root, kind, *extra):
    p = subprocess.run([sys.executable, "transpose.py", "--kind", kind,
                        *extra], cwd=root, capture_output=True, text=True)
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
        chk("上櫃**換欄序**時整支中止（回傳碼非 0）", rc != 0, f"rc={rc}")
        chk("而且說得出是哪個檔、差在哪",
            "不是前綴關係" in out, out[-400:])
    finally:
        shutil.rmtree(root, ignore_errors=True)

    # ── ⭐ 表頭「加欄」：這一種要**放行**，而且舊檔缺的欄要補空字串（⛔ 不是 0）──
    #   ⚠ 沒有這個案例的話，2026-09-09 融資融券回補跑到一半時個股庫會整個壞掉，
    #     而那會壞好幾個小時、甚至好幾趟——**而且是靜默的**（transpose 直接 return 1）。
    root = tempfile.mkdtemp(prefix="tposetest_")
    try:
        build_fixture(root, grow_header=True)
        rc, out = run(root, "margin")
        print("── 判定：表頭加欄（回補進行中）──")
        chk("新舊欄數混在一起時**不中止**", rc == 0, f"rc={rc}｜{out[-500:]}")
        chk("而且有講出欄數不一致與「補空字串不是 0」",
            "欄數不一致" in out and "空字串" in out, out[-500:])
        d = os.path.join(root, "data", "stocks_margin")
        new_rows = rows_of(os.path.join(d, "8299.csv"))     # 上櫃＝有新欄
        old_rows = rows_of(os.path.join(d, "2330.csv"))     # 上市＝沒有新欄
        chk("新欄有進到個股檔（8299 的 m_prev=11）",
            new_rows and new_rows[0].get("m_prev") == "11", str(new_rows[:1]))
        chk("⛔ 舊檔那半邊的新欄是**空字串**，不是 0",
            old_rows and old_rows[0].get("m_prev") == "", str(old_rows[:1]))
        chk("舊欄沒有錯位（2330 的 m_buy 還是 1、m_balance 還是 100）",
            old_rows and old_rows[0].get("m_buy") == "1"
            and old_rows[0].get("m_balance") == "100", str(old_rows[:1]))
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
        # ══════════════════════════════════════════════════════
        # ⭐⭐ 跨層落後：**19:00 那一趟一定會落後一天，而那不是缺陷**
        #
        #   台股 13:30 收盤 ⇒ price 19:00 就有；
        #   ⚠ 融資融券／本益比是**當天晚間**才發布 ⇒ 19:00 那趟必然停在前一交易日。
        #   ⛔ 而「每天紅」的代價是**會被學會忽略**，然後真的落後兩天那次沒人看。
        #
        # ⛔ 但「一律容忍一天」會把 2026-09-05 那個洞原封不動打開回去
        #   ——那次的形狀正是「**每天**落後一天而且看不出來」。
        # ⇒ 這一節要證明的是：容忍度**真的在起作用**，而且**只容忍到你說的那一格**。
        # ══════════════════════════════════════════════════════
        print("── 判定：跨層落後與容忍度 ──")
        root = tempfile.mkdtemp(prefix="tposelag_")
        build_fixture(root)
        # 讓 margin／per 少掉最後一天 ⇒ 落後 **1 個交易日**
        for k in ("margin", "otcmargin", "per", "otcper"):
            os.remove(os.path.join(root, "data", "universe", k,
                                   f"{DAYS[-1]}.csv"))
        rc0, out0 = run(root, "all")
        chk("⛔ 預設（容忍 0）：落後一個交易日就要紅",
            "✗" in out0 and "各層的來源日檔都跟上 price" in out0, out0[-400:])
        chk("⚠ 而且訊息要講出「19:00 那趟要帶 --lag-tolerance 1」"
            "（⛔ 不然看的人只知道紅、不知道該怎麼辦）",
            "--lag-tolerance 1" in out0, out0[-400:])
        chk("  落後量是用**交易日**數講的", "落後 1 個交易日" in out0, out0[-400:])
        rc1, out1 = run(root, "all", "--lag-tolerance", "1")
        # ⚠ runlog 只印**沒過**的檢查 ⇒ 判準是「那條完全不出現」
        chk("⭐ 帶 --lag-tolerance 1：同一份資料**不紅了**",
            "各層的來源日檔都跟上 price" not in out1, out1[-400:])
        chk("  ⚠ 而其他檢查照樣有跑（⛔ 不是整支中途 return 了）",
            "逐層結果" in out1 and out1.count("ok") >= 4, out1[-300:])
        # 再少一天 ⇒ 落後 **2 個交易日**：⛔ 容忍 1 也必須紅
        for k in ("margin", "otcmargin", "per", "otcper"):
            os.remove(os.path.join(root, "data", "universe", k,
                                   f"{DAYS[-2]}.csv"))
        rc2, out2 = run(root, "all", "--lag-tolerance", "1")
        chk("⭐⭐ 落後**兩個**交易日時，容忍 1 照樣紅"
            "（⛔ 這條才是 2026-09-05 那個洞的守門）",
            "✗" in out2 and "各層的來源日檔都跟上 price" in out2, out2[-400:])
        chk("  講得出落後 2 個交易日", "落後 2 個交易日" in out2, out2[-400:])
        shutil.rmtree(root, ignore_errors=True)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    chk("真的 repo 的 data/ 沒有被建立或改動",
        os.path.isdir(REAL_DATA) == real_before)

    print(f"\n[selftest] 通過 {ok}｜失敗 {fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
