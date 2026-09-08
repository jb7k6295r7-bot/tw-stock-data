#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mops_history.py 的 `ledger_from_disk` 自測。**不連網、不碰 repo 的 data/。**

★ 為什麼要有這一支
────────────────────────────────
`data/mops/_hist_status.csv` 是回補歷史的狀態帳本。寫它那一段的註解寫著
「**這是資料庫的狀態，不只是這一趟**」——但 `--fill`／`--resume` 會先跳過
已經有檔的期別，那些**永遠不會進這一趟的 state**。

2026-09-08 實測：資料庫 2015-01 起全數回補完成（revenue_hist 280 檔、
fs_hist 與 bs_hist 各 372 檔），帳本卻只有 **6 列而且全是 pending**。
讀的人會以為整批都還沒補。**註解說的是意圖，程式做的是另一件事**——
一份宣稱是整體、實際只有這一趟的帳本，比沒有帳本更糟。

所以收尾時要用「真的寫出來的檔」這個直接證據補齊。第 1 節就是釘這件事。

跑法：python3 selftest_mops_history.py（不連網、不需要資料）
"""
import io
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ok = fail = 0

REPO_LEDGER = os.path.join(HERE, "data", "mops", "_hist_status.csv")


def chk(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ✓ {label}" + (f"　（{detail}）" if detail else ""))
    else:
        fail += 1
        print(f"  ✗ {label}" + (f"　（{detail}）" if detail else ""))


def touch(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8").write("stock_id\n")


def main():
    import mops_history as H

    tmp = tempfile.mkdtemp(prefix="histtest_")
    led_before = (io.open(REPO_LEDGER, "rb").read()
                  if os.path.isfile(REPO_LEDGER) else None)
    real_out = H.OUT
    H.OUT = tmp
    try:
        # 造出跟真的一樣的檔名形狀
        touch(os.path.join(tmp, "revenue_hist", "2015-01_twse.csv"))
        touch(os.path.join(tmp, "revenue_hist", "2015-01_tpex.csv"))
        for tag in ("basi", "bd", "ci"):
            touch(os.path.join(tmp, "fs_hist", f"2015Q1_{tag}_twse.csv"))
        touch(os.path.join(tmp, "bs_hist", "2015Q1_ci_tpex.csv"))

        print("── 1. ★ 這一趟沒碰到、但檔案已經在的期別要補成 ok ──")
        st = {}
        n = H.ledger_from_disk(st)
        chk("★ 空帳本被補齊（--fill 跳過的期別不會消失）", n == 4, f"補進 {n} 筆")
        chk("revenue 兩個市場都補成 ok",
            st.get(("revenue", "2015-01", "sii"), ("",))[0] == "ok"
            and st.get(("revenue", "2015-01", "otc"), ("",))[0] == "ok")
        chk("★ 市場名有轉換（檔名 twse/tpex → 帳本 sii/otc）",
            ("revenue", "2015-01", "sii") in st and ("revenue", "2015-01", "otc") in st,
            str(sorted(k[2] for k in st)))
        chk("fs 三張業別表算成同一期的 3 張",
            st[("fs", "2015Q1", "sii")][1].startswith("3 張表"),
            st[("fs", "2015Q1", "sii")][1][:12])
        chk("bs 的三段檔名也解析得對", ("bs", "2015Q1", "otc") in st)
        chk("note 有講清楚證據等級",
            "不證明內容完整" in st[("bs", "2015Q1", "otc")][1])

        print("\n── 2. 有檔但這一趟失敗：狀態是 ok，失敗原文不可以丟掉 ──")
        st = {("revenue", "2015-01", "sii"): ("fail", "連線中斷")}
        H.ledger_from_disk(st)
        v = st[("revenue", "2015-01", "sii")]
        chk("★ 資料庫的狀態是「有」", v[0] == "ok", v[0])
        chk("★ 這一趟的失敗留在 note 裡，沒被藏起來", "連線中斷" in v[1], v[1][-24:])

        print("\n── 3. 沒有檔的期別維持原判，不可以憑空變成 ok ──")
        st = {("fs", "2099Q9", "sii"): ("pending", "0 張表")}
        H.ledger_from_disk(st)
        chk("★ 沒檔就不會被補成 ok", st[("fs", "2099Q9", "sii")][0] == "pending")
        chk("沒碰過又沒檔的期別不會憑空出現",
            ("fs", "2098Q1", "sii") not in st)

        print("\n── 4. 目錄不存在時不可以爆掉 ──")
        H.OUT = os.path.join(tmp, "空的")
        st = {}
        try:
            H.ledger_from_disk(st)
            chk("目錄不存在時安靜略過", st == {})
        except Exception as ex:                              # noqa: BLE001
            chk("目錄不存在時安靜略過", False, f"{type(ex).__name__}: {ex}")

        print("\n── 5. 沒有碰到 repo ──")
        led_after = (io.open(REPO_LEDGER, "rb").read()
                     if os.path.isfile(REPO_LEDGER) else None)
        chk("★ repo 的 _hist_status.csv 逐位元沒變", led_before == led_after)
    finally:
        H.OUT = real_out
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n[selftest] 通過 {ok}｜失敗 {fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
