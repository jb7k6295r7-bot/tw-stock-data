#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mops.py 的 `_log_changes` 自測。**不連網、不碰 repo 的 data/。**

★ 為什麼要有這一支
────────────────────────────────
`data/mops/_changes.log` 存在的唯一理由是「**財報更正不可以被靜默覆蓋**」。
它壞掉的方式不是不寫，而是**寫太多**：

舊版按**位置**配對舊列與新列（`zip(o[code], n[code])`），欄名卻取自舊表頭。
欄序改一次，每一格都對到別人的值——2026-09-06 一次塞進上百筆
「market: twse→2816」這種鬼影，而實際檔案是對齊的、一個數字都沒變。

**真的更正被鬼影淹掉，這個機制等於不存在——比沒有還糟，因為它看起來在運作。**
所以第 2 節那條（欄序改變、值不變 → 零筆列變動）是本檔的核心回歸測試。

跑法：python3 selftest_mops.py（不連網、不需要資料）
"""
import io
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ok = fail = 0

# 這支測試不可以動到 repo 的 data/mops/_changes.log
REPO_LOG = os.path.join(HERE, "data", "mops", "_changes.log")


def chk(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ✓ {label}" + (f"　（{detail}）" if detail else ""))
    else:
        fail += 1
        print(f"  ✗ {label}" + (f"　（{detail}）" if detail else ""))


def csvtext(header, rows):
    return "\n".join([",".join(header)] + [",".join(r) for r in rows]) + "\n"


def main():
    import mops as M

    tmp = tempfile.mkdtemp(prefix="mopstest_")
    log_before = io.open(REPO_LOG, "rb").read() if os.path.isfile(REPO_LOG) else None
    M.OUT_DIR = tmp
    M.CHANGES = os.path.join(tmp, "_changes.log")

    def run(old, new):
        """跑一次 _log_changes，回傳這一次新增的紀錄行。"""
        n0 = 0
        if os.path.exists(M.CHANGES):
            n0 = len(io.open(M.CHANGES, encoding="utf-8").read().splitlines())
        M._log_changes("fs", "115Q2_ci.csv", old, new)
        if not os.path.exists(M.CHANGES):
            return []
        return io.open(M.CHANGES, encoding="utf-8").read().splitlines()[n0:]

    # 正規化欄在前，原始欄在後——跟 write_period 產生的形狀一致
    H1 = ["stock_id", "name", "period", "market", "公司代號", "營業收入", "每股盈餘"]
    R1 = [["2330", "台積電", "115Q2", "twse", "2330", "1000", "15.5"],
          ["2317", "鴻海", "115Q2", "twse", "2317", "2000", "3.2"]]

    try:
        print("── 1. 真的改了要記下來 ──")
        R2 = [["2330", "台積電", "115Q2", "twse", "2330", "1000", "16.8"],
              ["2317", "鴻海", "115Q2", "twse", "2317", "2000", "3.2"]]
        got = run(csvtext(H1, R1), csvtext(H1, R2))
        chk("只記有變的那一檔", len(got) == 1, f"{len(got)} 行")
        chk("記的是正確的代號", got and "\t2330\t" in got[0])
        chk("欄名對得上值", got and "每股盈餘: 15.5→16.8" in got[0], got[0] if got else "")
        chk("沒有把沒變的欄也記進去", got and "營業收入" not in got[0])

        print("\n── 2. ★★ 只有欄序改變、值完全沒變 ──")
        # 這就是 2026-09-06 上百筆鬼影的成因。
        H2 = ["stock_id", "name", "period", "公司代號", "market", "營業收入", "每股盈餘"]
        R1b = [[r[0], r[1], r[2], r[4], r[3], r[5], r[6]] for r in R1]
        got = run(csvtext(H1, R1), csvtext(H2, R1b))
        rowlines = [l for l in got if "\t(表頭)\t" not in l]
        chk("★ 零筆列變動（舊版在這裡會產生每一列都變）", not rowlines,
            f"實得 {len(rowlines)} 行：{rowlines[:1]}")
        chk("表頭變動記成一行檔案層級的紀錄", len(got) == 1 and "(表頭)" in got[0])
        chk("說明是欄序改變、值不受影響",
            got and "欄序改變" in got[0], got[0] if got else "")
        chk("★ 沒有出現 market: twse→2330 這種鬼影",
            not any("market: twse→" in l for l in got))

        print("\n── 3. 新增欄／移除欄 ──")
        H3 = H1 + ["本期淨利"]
        R3 = [r + ["888"] for r in R1]
        got = run(csvtext(H1, R1), csvtext(H3, R3))
        chk("新增欄記在表頭那一行", any("新增欄 本期淨利" in l for l in got))
        chk("★ 不讓新增欄變成每一列都在變",
            not [l for l in got if "\t(表頭)\t" not in l],
            f"{len([l for l in got if '(表頭)' not in l])} 行列變動")
        got = run(csvtext(H3, R3), csvtext(H1, R1))
        chk("移除欄記在表頭那一行", any("移除欄 本期淨利" in l for l in got))

        print("\n── 4. 代號新增與消失 ──")
        R4 = R1 + [["2454", "聯發科", "115Q2", "twse", "2454", "500", "40.0"]]
        got = run(csvtext(H1, R1), csvtext(H1, R4))
        chk("新代號記成「新增」", any("\t2454\t新增" in l for l in got))
        got = run(csvtext(H1, R4), csvtext(H1, R1))
        chk("代號不見了記成「消失」", any("\t2454\t消失" in l for l in got))

        print("\n── 5. 截斷要說出來 ──")
        # 舊版直接 [:6]，看起來就像「只差 6 欄」。
        H5 = ["stock_id", "name", "period", "market", "公司代號"] + [f"欄{i}" for i in range(9)]
        A = [["2330", "台積電", "115Q2", "twse", "2330"] + ["1"] * 9]
        Bv = [["2330", "台積電", "115Q2", "twse", "2330"] + ["2"] * 9]
        got = run(csvtext(H5, A), csvtext(H5, Bv))
        chk("超過 6 欄時有寫「另有 N 欄」", got and "另有 3 欄" in got[0],
            got[0][-40:] if got else "")

        print("\n── 6. 沒有變動就不要寫 ──")
        got = run(csvtext(H1, R1), csvtext(H1, R1))
        chk("完全相同時不寫任何一行", not got, f"{len(got)} 行")

        print("\n── 7. 沒有碰到 repo ──")
        log_after = io.open(REPO_LOG, "rb").read() if os.path.isfile(REPO_LOG) else None
        chk("★ repo 的 data/mops/_changes.log 逐位元沒變", log_before == log_after)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n[selftest] 通過 {ok}｜失敗 {fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
