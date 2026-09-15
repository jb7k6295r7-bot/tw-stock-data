#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reduce_check.py 的自測。造假的 data/ 再跑，⛔ 不連網、不碰 repo 的 data/。

## ⛔⛔ 這一支是為了一個**炸在最後一行**的 KeyError 生出來的（2026-09-11）

    KeyError: ('6291', '2013-09-14')   reduce_check.py:163

成因：④ 用 `ref[k][2]`，而 `k` 來自**縮窄前**算出來的 `same`；
中間那一行把 `ref` 就地換成「只留我方涵蓋區間」的版本
⇒ 比我方日曆更早、而且兩邊都有的那一筆，鍵就不在了。

⚠ 它的傷害不在自己：`set -e` 連坐把同一個 step 後面的步驟全掐死
（`push_data.sh` 之前那幾支全部沒跑）——CLAUDE.md 四點二那一族。

⭐ 所以這一支要釘的**不是**「有沒有算對」，是
**「比我方資料更早的官方事件不會讓它炸」**——那是它真正壞掉的方式。
"""
import io
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


def w(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8").write(text)


def run(root):
    """在假 root 上跑一趟 main()，→ (回傳碼, runlog 文字)。"""
    import importlib
    import reduce_check as R
    import runlog
    importlib.reload(R)
    R._ROOT = root
    R.REF = os.path.join(root, "meta", "otc_reduce_reference.csv")
    R.ADJ = os.path.join(root, "adj")
    R.IND = os.path.join(root, "meta", "industry.csv")
    # ⛔ runlog 不可以寫到真的 `_last_run.md`
    _old = runlog.PATH
    runlog.PATH = os.path.join(root, "meta", "_last_run.md")
    try:
        rc = R.main()
    finally:
        runlog.PATH = _old
    txt = ""
    p = os.path.join(root, "meta", "_last_run.md")
    if os.path.exists(p):
        txt = io.open(p, encoding="utf-8").read()
    return rc, txt


def fixture(root, early_in_both=True):
    """⚠ 照真的形狀做：官方表有一筆**早於我方日曆**、而且我方 `data/adj/` 也有。

    ⛔ 只造「官方有、我方沒有」的早期事件測不到那個 bug——
      它要進得了 `same` 才會被 ④ 用鍵去查。
    """
    w(os.path.join(root, "meta", "calendar_twse.csv"),
      "date\n2015-01-05\n2015-01-06\n2020-06-01\n")
    w(os.path.join(root, "meta", "industry.csv"),
      "stock_id,market\n6291,tpex\n6461,tpex\n")
    rows = ["event_date,stock_id,last_close,ref_price,reason"]
    if early_in_both:
        rows.append("2013-09-14,6291,10.00,12.00,彌補虧損")
    rows.append("2020-06-01,6461,16.65,26.92,彌補虧損")
    w(os.path.join(root, "meta", "otc_reduce_reference.csv"), "\n".join(rows) + "\n")
    hdr = "date,factor,factor_official,cum_factor,pre_close,ref_price,kind,event"
    if early_in_both:
        w(os.path.join(root, "adj", "6291.csv"),
          hdr + "\n2013-09-14,1.2,,1.2,10.00,12.00,彌補虧損,reduce\n")
    w(os.path.join(root, "adj", "6461.csv"),
      hdr + "\n2020-06-01,1.61681,1.61662,1.61681,16.65,26.92,彌補虧損,reduce\n")


def main():
    print("=" * 60)
    print("reduce_check.py 自測（不連網）")
    print("=" * 60)

    print("\n[1] ⛔⛔ 官方事件早於我方日曆、而且兩邊都有 ⇒ **不可以炸**")
    d = tempfile.mkdtemp(prefix="rchk_")
    try:
        fixture(d, early_in_both=True)
        boom = None
        try:
            rc, txt = run(d)
        except Exception as e:            # noqa: BLE001 —— 就是要抓住它
            boom = f"{type(e).__name__}: {e}"
            rc, txt = 99, ""
        ck("⭐⭐ 跑得完（⛔ 原本是 KeyError，而 `set -e` 會連坐掐死後面六行）",
           boom is None, boom or "")
        ck("  而『我方上櫃有、官方沒有』**不會**把那一筆誤報成多出來的",
           "我方沒有編出官方沒有的上櫃減資" in txt
           and "- ok　我方沒有編出官方沒有的上櫃減資" in txt,
           [x for x in txt.splitlines() if "官方沒有的上櫃減資" in x])
        ck("  ⭐ 而『官方有我方沒有』也不算它漏抓（它在區間外）",
           "**真的沒有 0 筆**" in txt,
           [x for x in txt.splitlines() if "官方有我方沒有" in x])
        ck("  ④ 減資原因字串照樣算得出來（⛔ 不是因為炸掉才沒報）",
           "減資原因字串" in txt,
           [x for x in txt.splitlines() if "減資原因" in x])
    finally:
        shutil.rmtree(d, ignore_errors=True)

    print("\n[2] 反向：沒有那筆早期事件時，結果不變（⇒ 上面不是靠放寬判準過的）")
    d = tempfile.mkdtemp(prefix="rchk2_")
    try:
        fixture(d, early_in_both=False)
        rc, txt = run(d)
        ck("  照樣跑得完", True)
        ck("  ⭐ 逐筆比對相符 1 筆（⛔ 正例：判準真的有在比，不是空轉）",
           "相符 1｜不符 0" in txt,
           [x for x in txt.splitlines() if "逐筆比對" in x])
    finally:
        shutil.rmtree(d, ignore_errors=True)

    print("\n[2之二] ⭐ 正例：我方真的編出一筆官方沒有的 ⇒ **照樣要抓到**")
    #   ⛔ 沒有這一節，上面那條「不誤報」就只證明了「這個閘門關著」。
    d = tempfile.mkdtemp(prefix="rchk2b_")
    try:
        fixture(d, early_in_both=True)
        hdr = ("date,factor,factor_official,cum_factor,"
               "pre_close,ref_price,kind,event")
        # ⚠ 日期在官方表涵蓋期**之內**（2013-09-14 之後）⇒ 沒有豁免理由
        w(os.path.join(d, "adj", "6461.csv"),
          hdr + "\n2020-06-01,1.61681,1.61662,1.61681,16.65,26.92,彌補虧損,reduce"
          "\n2019-03-05,1.20,,1.20,10.00,12.00,彌補虧損,reduce\n")
        rc, txt = run(d)
        ck("⭐ 抓到那 1 筆", "我方沒有編出官方沒有的上櫃減資　（1 筆）" in txt,
           [x for x in txt.splitlines() if "官方沒有的上櫃減資" in x])
        ck("  而它是 ✗ 不是 ok（⛔ 不是印出來就算）",
           any(x.startswith("- **✗**") and "官方沒有的上櫃減資" in x
               for x in txt.splitlines()))
    finally:
        shutil.rmtree(d, ignore_errors=True)

    print("\n[2之三] ⭐ 而早於**官方表自己的起點**的我方事件 ⇒ 不算編造")
    d = tempfile.mkdtemp(prefix="rchk2c_")
    try:
        fixture(d, early_in_both=True)
        hdr = ("date,factor,factor_official,cum_factor,"
               "pre_close,ref_price,kind,event")
        w(os.path.join(d, "adj", "6461.csv"),
          hdr + "\n2020-06-01,1.61681,1.61662,1.61681,16.65,26.92,彌補虧損,reduce"
          "\n2011-03-05,1.20,,1.20,10.00,12.00,彌補虧損,reduce\n")
        rc, txt = run(d)
        ck("  2011 那筆不算（官方表從 2013-09 起）",
           "我方沒有編出官方沒有的上櫃減資　（0 筆）" in txt,
           [x for x in txt.splitlines() if "官方沒有的上櫃減資" in x])
    finally:
        shutil.rmtree(d, ignore_errors=True)

    print("\n[3] ⛔ 對照表不存在 ⇒ 大聲失敗，不是靜靜回 0")
    d = tempfile.mkdtemp(prefix="rchk3_")
    try:
        os.makedirs(os.path.join(d, "meta"))
        rc, txt = run(d)
        ck("  回非 0", rc != 0, str(rc))
        ck("  而且說得出是哪個檔", "官方上櫃減資對照表存在" in txt)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # ══════════════════════════════════════════════════════════════
    # [4] ⭐⭐ 「未來事件」的基準是**我方資料最後一天**，⛔ 不是「今天」
    #
    # ⛔⛔ 2026-09-15 修的就是這個：這一支本來用 `runlog.now_tpe()`
    #   ⇒ 這是同一個坑的**第三次**（`adjust.last_data_day()` 的檔頭記著前兩次）。
    #   ⚠ 差別只在週末與盤中：今天 09-15（週一）而我方日檔停在 09-11（週五）時，
    #     一筆 09-14 的官方減資會被報成「⛔ 我方漏抓」，⚠ 而我方只是還沒抓到那天。
    #
    # ⭐ 判準要釘在**沙箱**上：答案必須是沙箱日檔的**檔名**，⛔ 不是今天
    #   ——比「不傳 upper == 傳 last_data_day()」那種**恆真**的寫法強
    #   （兩邊一起變，突變照樣全綠；CLAUDE.md 四點五那一節逐字記著）。
    # ══════════════════════════════════════════════════════════════
    print("\n[4] ⭐⭐ 基準是**我方資料最後一天**，⛔ 不是今天")
    import adjust as _A
    d4 = tempfile.mkdtemp(prefix="rchk4_")
    _old_daily = _A.DAILY_DIR
    try:
        # 我方日檔停在 2020-06-01
        for day in ("2015-01-05", "2015-01-06", "2020-06-01"):
            w(os.path.join(d4, "universe", "daily", day + ".csv"), "date\n")
        _A.DAILY_DIR = os.path.join(d4, "universe", "daily")
        ck("★ 沙箱真的接上了（`last_data_day()` 回的是**檔名**，⛔ 不是今天）",
           _A.last_data_day() == ("2020-06-01", False), str(_A.last_data_day()))

        w(os.path.join(d4, "meta", "calendar_twse.csv"),
          "date\n2015-01-05\n2015-01-06\n2020-06-01\n")
        w(os.path.join(d4, "meta", "industry.csv"),
          "stock_id,market\n6461,tpex\n7777,tpex\n8888,tpex\n")
        w(os.path.join(d4, "meta", "otc_reduce_reference.csv"),
          "event_date,stock_id,last_close,ref_price,reason\n"
          "2020-06-01,6461,16.65,26.92,彌補虧損\n"
          "2020-06-05,7777,10.00,12.00,彌補虧損\n")     # ⭐ 晚於我方最後一天
        hdr = "date,factor,factor_official,cum_factor,pre_close,ref_price,kind,event"
        w(os.path.join(d4, "adj", "6461.csv"),
          hdr + "\n2020-06-01,1.61681,1.61662,1.61681,16.65,26.92,彌補虧損,reduce\n")
        rc, txt = run(d4)
        ck("⭐⭐ 晚於我方最後一天的那筆 ⇒ 算**預告**，⛔ 不算漏抓",
           "**真的沒有 0 筆**" in txt,
           [x for x in txt.splitlines() if "官方有我方沒有" in x])
        ck("  ⭐ 而訊息要**講出那個基準是哪一天**（⛔ 不是只說「未來」）",
           "2020-06-01" in txt and "晚於我方最後一天" in txt,
           [x for x in txt.splitlines() if "晚於我方" in x])

        # ⛔ 反向：**不晚於**我方最後一天而我方沒有 ⇒ 照樣要抓到
        #   ⚠ 沒有這一半，「全部當成預告」也會全綠（三點1：只比一個方向）
        w(os.path.join(d4, "meta", "otc_reduce_reference.csv"),
          "event_date,stock_id,last_close,ref_price,reason\n"
          "2020-06-01,6461,16.65,26.92,彌補虧損\n"
          "2015-01-06,8888,10.00,12.00,彌補虧損\n")
        rc, txt = run(d4)
        ck("⛔ 反向：早於我方最後一天而我方沒有 ⇒ **照樣**報漏抓",
           "**真的沒有 1 筆**" in txt and "8888" in txt,
           [x for x in txt.splitlines() if "官方有我方沒有" in x or "漏抓" in x])

        # ⭐ 邊界：事件日 **等於** 我方最後一天 ⇒ 那天的價格我方已經有了 ⇒ 算漏抓
        w(os.path.join(d4, "meta", "otc_reduce_reference.csv"),
          "event_date,stock_id,last_close,ref_price,reason\n"
          "2020-06-01,7777,10.00,12.00,彌補虧損\n")
        rc, txt = run(d4)
        ck("⭐⭐ 邊界：事件日 **==** 我方最後一天 ⇒ 算漏抓（⛔ 不是預告）",
           "**真的沒有 1 筆**" in txt,
           [x for x in txt.splitlines() if "官方有我方沒有" in x])

        # ⛔ 讀不到日檔目錄 ⇒ 要**講出來**它退回用今天了
        _A.DAILY_DIR = os.path.join(d4, "沒這個目錄")
        rc, txt = run(d4)
        ck("⛔ 讀不到日檔 ⇒ 大聲說「退回用今天」（⚠ 靜靜退回 ＝ 判準悄悄變回舊的）",
           "退回用今天" in txt,
           [x for x in txt.splitlines() if "退回" in x])
    finally:
        _A.DAILY_DIR = _old_daily
        shutil.rmtree(d4, ignore_errors=True)

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
