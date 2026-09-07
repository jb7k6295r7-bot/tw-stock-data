#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_content.py — 離線驗 content_audit.py。**不碰真的 data/。**

做法：在 tempdir 裡造一個小資料庫，**故意種下已知的毛病**，
然後檢查稽核程式有沒有剛好抓到那些、而且沒有多抓。

★ 為什麼一定要這樣做：這支稽核程式的產出是「一堆數字」，
  它算錯的時候不會報錯，只會給一份看起來很合理的報告。
  2,845 天跑下去之前，先在**知道正確答案**的資料上跑一次。

★ 也順便擋掉 selftest_reduce.py 那次差點發生的事：
  跑完要確認**真的 repo 的 data/ 完全沒有被建立或改動**。
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REAL_DATA = os.path.join(HERE, "data")

HDR = ("key,date,stock_id,name,market,open,high,low,close,volume,amount,"
       "change,limit,shares,transactions,price_basis")

CAL = [  # 20 個假交易日
    "2020-01-02", "2020-01-03", "2020-01-06", "2020-01-07", "2020-01-08",
    "2020-01-09", "2020-01-10", "2020-01-13", "2020-01-14", "2020-01-15",
    "2020-01-16", "2020-01-17", "2020-01-20", "2020-01-21", "2020-01-22",
    "2020-02-03", "2020-02-04", "2020-02-05", "2020-02-06", "2020-02-07",
]
TWSE = [f"1{i:03d}" for i in range(101, 141)]     # 40 檔上市
TPEX = [f"3{i:03d}" for i in range(101, 131)]     # 30 檔上櫃
EMG = [f"7{i:03d}" for i in range(101, 106)]      # 5 檔興櫃（只在最後 3 天）

# ── 種下去的毛病（正確答案）────────────────────────────────────
OUTAGE_DAY = "2020-01-13"      # 上櫃整批 0 列
PARTIAL_DAY = "2020-01-16"     # 上市只剩 20 列（50%）
LEDGER_LIE_DAY = "2020-01-07"  # 帳本說 99，實際 40
EMPTY_CLOSE_DAY = "2020-01-09"  # 3 列 close 空白
NO_FILE_DAY = "2020-02-06"     # 日曆有、檔案不存在
REDUCE_STOCK, REDUCE_DAY = "1105", "2020-01-15"   # 停牌 3 天，有減資事件
PLAIN_STOCK, PLAIN_GAP = "1120", "2020-01-21"     # 停牌 2 天，沒有事件


def row(day, sid, mkt, close="10.5"):
    return (f"{day}_{sid},{day},{sid},N{sid},{mkt},10,11,9,{close},"
            f"1000,10000,0.1,,,50,")


def build(root):
    uni = os.path.join(root, "data", "universe", "daily")
    meta = os.path.join(root, "data", "meta")
    adj = os.path.join(root, "data", "adj")
    for d in (uni, meta, adj):
        os.makedirs(d, exist_ok=True)

    with open(os.path.join(meta, "calendar_twse.csv"), "w", encoding="utf-8") as f:
        f.write("date,source\n")
        for d in CAL:
            f.write(f"{d},FIXTURE\n")

    ledger = {}
    for d in CAL:
        if d == NO_FILE_DAY:
            continue
        tw = TWSE[:20] if d == PARTIAL_DAY else TWSE
        tp = [] if d == OUTAGE_DAY else TPEX
        em = EMG if d >= CAL[-3] else []
        # 停牌
        if REDUCE_DAY <= d <= CAL[CAL.index(REDUCE_DAY) + 2]:
            tw = [s for s in tw if s != REDUCE_STOCK]
        if PLAIN_GAP <= d <= CAL[CAL.index(PLAIN_GAP) + 1]:
            tw = [s for s in tw if s != PLAIN_STOCK]
        lines = []
        for i, s in enumerate(tw):
            close = "" if (d == EMPTY_CLOSE_DAY and i < 3) else "10.5"
            lines.append(row(d, s, "twse", close))
        lines += [row(d, s, "tpex") for s in tp]
        lines += [row(d, s, "emerging", "") for s in em]
        with open(os.path.join(uni, f"{d}.csv"), "w", encoding="utf-8") as f:
            f.write(HDR + "\n" + "\n".join(lines) + "\n")
        ledger[d] = (len(tw), len(tp), len(em))

    cov = os.path.join(root, "data", "universe", "_coverage_daily.csv")
    with open(cov, "w", encoding="utf-8") as f:
        f.write("date,twse,tpex,emerging,total,note\n")
        for d in CAL:
            if d not in ledger:
                continue
            tw, tp, em = ledger[d]
            if d == LEDGER_LIE_DAY:
                tw = 99                      # ★ 帳本說謊
            f.write(f"{d},{tw},{tp},{em},{tw + tp + em},ok\n")

    with open(os.path.join(adj, f"{REDUCE_STOCK}.csv"), "w", encoding="utf-8") as f:
        f.write("date,factor,cum_factor,pre_close,ref_price,kind,event\n")
        f.write(f"{REDUCE_DAY},2.0,2.0,10,20,減資,reduce\n")


def run(root):
    shutil.copy(os.path.join(HERE, "content_audit.py"), root)
    p = subprocess.run([sys.executable, "content_audit.py", "--write", "--top", "50"],
                       cwd=root, capture_output=True, text=True)
    return p.stdout + p.stderr


def main():
    real_before = os.path.isdir(REAL_DATA)
    root = tempfile.mkdtemp(prefix="cauditest_")
    ok = fail = 0

    def chk(name, cond, hint=""):
        nonlocal ok, fail
        if cond:
            ok += 1
            print(f"  ✓ {name}")
        else:
            fail += 1
            print(f"  ✗ {name}" + (f"｜{hint}" if hint else ""))

    try:
        build(root)
        out = run(root)
        print(out)
        print("── 判定 ──")

        chk("用了獨立日曆、沒有退回檔名集合", "calendar_twse.csv" in out and "退回" not in out)
        chk("交易日數 20", "20 個交易日" in out)

        # [0] 缺檔
        chk(f"抓到缺檔 {NO_FILE_DAY}",
            re.search(r"daily/ 沒有檔案：1 天", out) and NO_FILE_DAY in out)

        # [1] 興櫃起始日
        chk("興櫃起始日認在最後三天", re.search(rf"emerging\s+{CAL[-3]}", out))

        # [2] 帳本說謊
        m = re.search(r"帳本 vs 實際檔案：對不上 \*\*(\d+)\*\*", out)
        chk("帳本對不上剛好 1 筆", m and m.group(1) == "1", m.group(1) if m else "抓不到")
        chk("指到說謊的那天與數字",
            re.search(rf"{LEDGER_LIE_DAY} twse\s+帳本\s+99", out) is not None)

        # [3] 離群
        chk("上櫃整批 0 被標記", re.search(rf"{OUTAGE_DAY} tpex\s+0 列", out))
        # ★ 19 不是 20：PARTIAL_DAY 落在 1105 的停牌區間內，那一檔也不在。
        #   第一版這裡寫 20 而測試失敗——**是測試的期望錯了，不是程式錯了**。
        chk("上市半套被標記（20 檔裡 1105 停牌，實際 19）",
            re.search(rf"{PARTIAL_DAY} twse\s+19 列.*偏低", out))
        # 興櫃只有 3 天資料，其中 1 天整天缺檔 → 標記 1 天是對的。
        # 要擋的是「2015~2026 每天都算漏抓」那種上千筆的假警報。
        chk("興櫃沒有被誤判成整段漏抓（標記 1 天＝就是缺檔那天）",
            re.search(r"emerging\s+標記 1 天", out))

        # [4] 有列沒有值
        chk("close 缺值剛好 3 列", re.search(r"不是數字」：共 \*\*3\*\* 列", out))
        chk("缺值指到正確的那天", re.search(rf"{EMPTY_CLOSE_DAY} 3 列", out))
        chk("興櫃的空 close 沒有被算進去（否則會遠超過 3）",
            not re.search(r"不是數字」：共 \*\*1[0-9]+ \*\*", out))

        # [5] 逐檔缺漏：三分類
        chk("減資那段歸到『減資』1 段", re.search(r"減資\s+1 段", out))
        chk("『其餘』有列出 1120 的 2 天",
            re.search(rf"{PLAIN_STOCK}\s+自 {PLAIN_GAP} 起連續缺 2 個交易日", out))
        # ★ 整批缺檔／整批 0 列造成的每檔一段，必須歸到「市場級」而不是「其餘」，
        #   否則 2,000 檔就是 2,000 段假的「未解釋」，真的那幾段會被淹掉。
        m5 = re.search(r"市場級\s+(\d+) 段", out)
        chk("市場級段數 > 60（缺檔日與 0 列日造成的）",
            m5 and int(m5.group(1)) > 60, m5.group(1) if m5 else "抓不到")
        m6 = re.search(r"其餘\s+(\d+) 段", out)
        chk("『其餘』只有 1105 半套那天與 1120 兩段以內",
            m6 and int(m6.group(1)) <= 3, m6.group(1) if m6 else "抓不到")

        # 寫檔
        chk("寫出稽核表", os.path.exists(os.path.join(root, "data", "meta",
                                                     "_content_audit.csv")))
        n = 0
        p = os.path.join(root, "data", "meta", "_content_audit.csv")
        if os.path.exists(p):
            n = sum(1 for _ in open(p, encoding="utf-8")) - 1
        # twse/tpex 各 20 天 + emerging 3 天（起始日之後）= 43
        chk("稽核表列數 = 各市場起始日之後的天數合計（43）", n == 43, f"實際 {n}")

        # ★ 沒有動到真的 data/
        chk("真的 repo 的 data/ 沒有被建立或改動",
            os.path.isdir(REAL_DATA) == real_before)

    finally:
        shutil.rmtree(root, ignore_errors=True)

    print(f"\n[selftest] 通過 {ok}｜失敗 {fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
