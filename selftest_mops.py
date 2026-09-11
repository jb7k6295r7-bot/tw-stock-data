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
import csv
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



def _retry_section():
    """⭐ 「第一次失敗、隔久再試一次」——⛔ 而且**重試成功不可以是靜悄悄的**。

    ## 為什麼（2026-09-11）

    `_last_run.md` 的 `mops` 區塊常駐紅：22 個請求裡 `fs/ci/tpex` **沒回應**。
    ⚠ 而 `B.get` 的 `retries=2` 是**同一個時間窗**內連打三發
    ⇒ 被限流時三發一起掛，跟「這張表不存在」長得一模一樣。

    ⇒ 隔久一點再試**一次**。⛔ 而「靜靜重試成功」是這裡最容易犯的錯：
      一張**天天要重試才活**的表跟一張一次就過的表不是同一件事，
      ⚠ 抹掉那個訊號，等於把「它在惡化」這件事藏起來。
    """
    import io as _io
    import os as _o
    import shutil as _sh
    import tempfile as _tf
    import mops as M
    import backfill as B
    import runlog

    calls = {"n": 0}

    def make_get(fail_first_on):
        """→ 假的 `B.get`。`fail_first_on` 裡的網址**第一次**失敗、第二次成功。"""
        seen = {}

        def _get(url, retries=2, timeout=60):
            calls["n"] += 1
            if url in fail_first_on and not seen.get(url):
                seen[url] = True
                return b"", "429 Too Many Requests"
            return (b'[{"\u516c\u53f8\u4ee3\u865f":"2330",'
                    b'"\u5e74\u5ea6":"115","\u5b63\u5225":"2"}]'), ""
        return _get

    class _A:
        run = True
        kind = "fs"
        sleep = 0

    bad_url = M.TPEX + "mopsfin_t187ap06_O_ci"
    out = {}
    for label, failing in (("重試才成功", {bad_url}), ("一次就過", set())):
        d = _tf.mkdtemp(prefix="mopsretry_")
        _oget, _oout, _ochg, _opath, _olisted = (
            B.get, M.OUT_DIR, M.CHANGES, runlog.PATH, M.listed_codes)
        try:
            B.get = make_get(failing)
            M.OUT_DIR = d
            M.CHANGES = _o.path.join(d, "_changes.log")
            runlog.PATH = _o.path.join(d, "_last_run.md")
            M.listed_codes = lambda: ({"2330"}, {"6488"})
            _sleep = M.time.sleep
            M.time.sleep = lambda *_a, **_k: None
            try:
                M.cmd_run(_A())
            finally:
                M.time.sleep = _sleep
            out[label] = _io.open(runlog.PATH, encoding="utf-8").read()
        finally:
            (B.get, M.OUT_DIR, M.CHANGES, runlog.PATH, M.listed_codes) = (
                _oget, _oout, _ochg, _opath, _olisted)
            _sh.rmtree(d, ignore_errors=True)

    t = out["重試才成功"]
    chk("⭐ 第一次 429、隔久再試成功 ⇒ 那一格**不算沒回應**",
        "- ok　每一個表×市場都有回應" in t,
        [x for x in t.splitlines() if "都有回應" in x])
    chk("⭐⭐ ⛔ 而且**不可以靜悄悄**：runlog 要點名是哪一格重試才活的",
        "fs/ci/tpex" in t and "隔久再試才成功的**：1 個" in t,
        [x for x in t.splitlines() if "隔久再試" in x])

    t2 = out["一次就過"]
    chk("  ⚠ 反向：沒有重試時那一列是 **0 個**（⛔ 不是整列消失）",
        "隔久再試才成功的**：0 個" in t2,
        [x for x in t2.splitlines() if "隔久再試" in x])
    chk("  ⛔ 而 0 個的那一趟不可以把任何一格報成沒回應",
        "- ok　每一個表×市場都有回應" in t2)



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

        print("\n── 7. ★ 出表日期兩種欄名都要收（正規化欄 報表日期）──")
        # 來源端每一張表、每個市場用中文還是英文欄名是**不固定的**，
        # 2026-09-08 實測連同一列都會混用。讀原始欄一定會踩到空白。
        M.OUT_DIR = tmp
        recs = [
            {"公司代號": "2330", "公司名稱": "台積電", "出表日期": "1150908"},   # 全中文
            {"SecuritiesCompanyCode": "8299", "CompanyName": "群聯",
             "Date": "1150908"},                                              # 全英文
            {"SecuritiesCompanyCode": "6488", "公司名稱": "環球晶",
             "Date": "1150908"},                                              # 混用
        ]
        mk = {id(recs[0]): "twse", id(recs[1]): "tpex", id(recs[2]): "tpex"}
        M.write_period("fs", "ci", "2026Q2", recs, mk)
        out = list(csv.DictReader(io.open(
            os.path.join(tmp, "fs", "2026Q2_ci.csv"), encoding="utf-8")))
        chk("三列都寫出來了", len(out) == 3, f"{len(out)} 列")
        chk("★ 每一列的 報表日期 都有值（含混用那一列）",
            all(r["報表日期"] == "1150908" for r in out),
            str([r["報表日期"] for r in out]))
        chk("stock_id 兩種欄名都取得到",
            sorted(r["stock_id"] for r in out) == ["2330", "6488", "8299"])
        chk("name 兩種欄名都取得到",
            all(r["name"] for r in out), str([r["name"] for r in out]))
        # ⚠ 這裡要按 stock_id 查，不可以用 out[0]——write_period 會依
        #   (market, 代號) 排序，位置不是寫進去的順序。**位置定位就是本檔在講的那個坑。**
        by = {r["stock_id"]: r for r in out}
        chk("原始欄位仍原樣保留（沒有被回填）",
            by["2330"]["Date"] == "" and by["2330"]["出表日期"] == "1150908"
            and by["8299"]["出表日期"] == "" and by["8299"]["Date"] == "1150908",
            "正規化欄補齊，raw 欄照來源原樣")

        print("\n── 7之二. ⭐ 隔久重試（⛔ 重試成功不可以靜悄悄）──")
        _retry_section()

        print("\n── 8. 沒有碰到 repo ──")
        log_after = io.open(REPO_LOG, "rb").read() if os.path.isfile(REPO_LOG) else None
        chk("★ repo 的 data/mops/_changes.log 逐位元沒變", log_before == log_after)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n[selftest] 通過 {ok}｜失敗 {fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
