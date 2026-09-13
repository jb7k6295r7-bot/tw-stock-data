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
import glob
import io
import json
import os
import shutil
import sys
import tempfile
import time

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
            # ⛔ 這裡**不可以**寫成 bytes literal 加 `\\u` 跳脫：
            #   `\\u` 在 bytes literal 裡不是跳脫序列 ⇒ SyntaxWarning，
            #   ⚠ 而 `selftest_syntax_warnings.py` 會擋下整趟（run 112 就是它掛的）。
            #   ⇒ 照真回應的形狀：str 寫中文，再 `.encode("utf-8")`。
            return ('[{"公司代號":"2330","年度":"115","季別":"2"}]'
                    .encode("utf-8")), ""
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

        print("\n── 7之三. ⭐⭐ 兩個市場申報進度不同步 ⇒ **分開寫檔** ──")
        # ⛔ 這一節是**實測踩到的**（main，台北 2026-09-14 04:45）：
        #   data/mops/revenue/2026-07.csv 1,976 列裡
        #     twse 1,085 列 資料年月 = 11507 ✅
        #     tpex 　891 列 資料年月 = **11508** ⛔ 八月的資料貼著七月的檔名
        #   ⇒ 舊版取「最常見的那一期」，把兩期寫進同一個檔。
        #   ⚠ 假資料照真回應的形狀做：上市一期、上櫃**另一期**。
        recs = ([{"公司代號": f"1{i:03d}", "資料年月": "11507"} for i in range(5)]
                + [{"SecuritiesCompanyCode": f"6{i:03d}",
                    "資料年月": "11508"} for i in range(3)])
        g, nop = M.group_by_period("revenue", recs)
        chk("⭐ 兩期各自成組（⛔ 不是取最常見的那一期）",
            sorted(g) == ["2026-07", "2026-08"], str(sorted(g)))
        chk("⭐ 而列數沒有被吃掉（5 ＋ 3）",
            len(g.get("2026-07", [])) == 5 and len(g.get("2026-08", [])) == 3,
            str({k: len(v) for k, v in g.items()}))
        chk("⛔ 反向：舊寫法（取最常見）會把 8 列全部貼上 2026-07"
            "　⇒ 這一節不是憑空擔心",
            max(((len(v), k) for k, v in g.items()))[1] == "2026-07"
            and sum(len(v) for v in g.values()) == 8)
        # ⭐ 取不到期別的列：不寫、但要數出來（⛔ 不可以靜靜丟掉）
        g2, nop2 = M.group_by_period("revenue",
                                     recs + [{"公司代號": "9999"}])
        chk("⭐ 取不到期別的列**不進任何一組**，而且數得出來（1 列）",
            nop2 == 1 and sum(len(v) for v in g2.values()) == 8,
            f"noperiod={nop2}")
        chk("⚠ 而全都取得到時它是 0（⛔ 否則上面那條分不出是不是永遠回 1）",
            nop == 0, str(nop))
        # ⭐ 單一期別那條路（最常見的情形）不可以壞掉
        g3, _ = M.group_by_period("revenue",
                                  [{"公司代號": "1101", "資料年月": "11508"}])
        chk("⭐ 只有一期時就只有一組（⛔ 不要為了分檔而分檔）",
            list(g3) == ["2026-08"], str(list(g3)))
        # ⭐ 季報那一半用的是另一組欄名 ⇒ 要各自有一條
        g4, _ = M.group_by_period("fs", [{"公司代號": "2330", "年度": "115",
                                          "季別": "2"},
                                         {"SecuritiesCompanyCode": "6488",
                                          "Year": "115", "Season": "1"}])
        chk("⭐ 季報也照每一列自己的年度／季別分組（⚠ 上櫃用英文欄名）",
            sorted(g4) == ["2026Q1", "2026Q2"], str(sorted(g4)))

        print("\n── 7之四. ⭐⭐ 呼叫點：兩期真的落成**兩個檔**（⛔ 只測純函式抓不到）──")
        # ⛔⛔ 這一節存在的理由：只測 `group_by_period` 時，把呼叫點改成
        #   `for period in sorted(groups)[:1]:`（分組對了、只寫第一期）**全綠**。
        #   ⚠ 「測了判準、沒測呼叫點」在本專案這是第六次（CLAUDE.md 第七點③）。
        import argparse as _ap
        import backfill as _B
        import runlog as _RL
        _old_get, _old_rl, _old_sleep = _B.get, _RL.PATH, time.sleep
        _RL.PATH = os.path.join(tmp, "_last_run.md")
        _rl_real = os.path.join(HERE, "data", "meta", "_last_run.md")
        _rl_before = (io.open(_rl_real, "rb").read()
                      if os.path.isfile(_rl_real) else None)
        # ⭐ 假回應照真回應的形狀：頂層是 list、欄名兩市場不同、
        #   而**兩個市場的資料年月不一樣**（上市 7 月、上櫃已經 8 月）。
        _TW = json.dumps([{"公司代號": "1101", "公司名稱": "台泥",
                           "資料年月": "11507", "出表日期": "1150812",
                           "營業收入-當月營收": "1"}]).encode()
        _TP = json.dumps([{"SecuritiesCompanyCode": "6488",
                           "CompanyName": "環球晶", "資料年月": "11508",
                           "Date": "1150912", "營業收入-當月營收": "2"}]).encode()

        def _fake_get(url, *a, **k):
            u = str(url)
            if "t187ap05_L" in u:
                return _TW, None
            if "mopsfin_t187ap05_O" in u:
                return _TP, None
            return None, "selftest：不連外"
        _B.get = _fake_get
        time.sleep = lambda *a, **k: None      # ⛔ 不要真的睡 B.SLEEP
        try:
            M.cmd_run(_ap.Namespace(sleep=0, kind="revenue"))
        finally:
            _B.get, _RL.PATH, time.sleep = _old_get, _old_rl, _old_sleep
        _made = sorted(os.path.basename(x) for x in
                       glob.glob(os.path.join(tmp, "revenue", "*.csv")))
        chk("⭐⭐ 兩個期別 ⇒ **兩個檔**（⛔ 舊版只會有一個）",
            _made == ["2026-07.csv", "2026-08.csv"], str(_made))
        # ⚠ 檔不在時要**印 ✗ 繼續跑**，⛔ 不是崩潰：崩潰吐 traceback、不印 ✗，
        #   而且後面的斷言一條都不會跑（CLAUDE.md 第七點②）。
        def _rows(fn):
            fp = os.path.join(tmp, "revenue", fn)
            if not os.path.isfile(fp):
                return []
            return list(csv.DictReader(io.open(fp, encoding="utf-8")))
        _p7, _p8 = _rows("2026-07.csv"), _rows("2026-08.csv")
        chk("⭐ 上市那一列在 7 月檔、上櫃那一列在 8 月檔（⛔ 不是混在一起）",
            [r["stock_id"] for r in _p7] == ["1101"]
            and [r["stock_id"] for r in _p8] == ["6488"],
            f"{[r['stock_id'] for r in _p7]}｜{[r['stock_id'] for r in _p8]}")
        chk("⭐⭐ `period` 欄與**每一列自己的 `資料年月`** 對得上"
            "（⛔ 舊版是整欄覆蓋成檔名那一期）",
            bool(_p7) and bool(_p8)
            and _p7[0]["period"] == "2026-07" and _p7[0]["資料年月"] == "11507"
            and _p8[0]["period"] == "2026-08" and _p8[0]["資料年月"] == "11508",
            f"7月檔 {len(_p7)} 列｜8月檔 {len(_p8)} 列")
        chk("⭐ runlog 有把「含多個期別、已分開寫檔」講出來（⛔ 只印 stderr 不夠）",
            "已分開寫檔" in io.open(_RL.PATH if False else
                                os.path.join(tmp, "_last_run.md"),
                                encoding="utf-8").read(),
            io.open(os.path.join(tmp, "_last_run.md"), encoding="utf-8").read()[-300:])
        chk("★ 沒有動到 repo 真的 _last_run.md",
            _rl_before == (io.open(_rl_real, "rb").read()
                           if os.path.isfile(_rl_real) else None))
        print("\n── 7之五. ⭐⭐ 期別自癒：把**已經寫錯期**的舊列搬回去 ──")
        # ⛔ 這一節對應的是 main 上真的躺著的東西（台北 2026-09-14 04:45 實測）：
        #   data/mops/revenue/2026-07.csv 裡 tpex 891 列的 `資料年月` 是 11508。
        #   ⚠ 而它不會自己好：上市也換到 8 月之後，**沒有人會再寫 2026-07.csv**。
        rd = os.path.join(tmp, "revenue")
        os.makedirs(rd, exist_ok=True)
        for f in glob.glob(os.path.join(rd, "*.csv")):
            os.remove(f)
        _H = "stock_id,name,period,market,報表日期,公司代號,資料年月,營收"
        io.open(os.path.join(rd, "2026-07.csv"), "w", encoding="utf-8").write(
            _H + "\n"
            "1101,台泥,2026-07,twse,1150812,1101,11507,1\n"      # ✅ 對的
            "6488,環球晶,2026-07,tpex,1150912,6488,11508,2\n"    # ⛔ 錯期
            "8069,元太,2026-07,tpex,1150912,8069,11508,3\n")     # ⛔ 錯期
        n, msg = M.repair_periods("revenue")
        made = sorted(os.path.basename(x) for x in glob.glob(os.path.join(rd, "*.csv")))
        chk("⭐ 搬了 2 列（⛔ 對的那一列不動）", n == 2, f"{n}｜{msg}")
        chk("⭐ 8 月那個檔被建出來", made == ["2026-07.csv", "2026-08.csv"], str(made))
        # ⚠ 檔不在時印 ✗ 繼續跑，⛔ 不是崩潰（第七點②）
        def _rd(fn):
            fp = os.path.join(rd, fn)
            return (list(csv.DictReader(io.open(fp, encoding="utf-8")))
                    if os.path.isfile(fp) else [])
        r7, r8 = _rd("2026-07.csv"), _rd("2026-08.csv")
        chk("⭐ 7 月檔只剩那一列對的（⛔ 而它沒有被搬走）",
            [r["stock_id"] for r in r7] == ["1101"], str([r["stock_id"] for r in r7]))
        chk("⭐ 兩列錯期的都到 8 月檔了", sorted(r["stock_id"] for r in r8)
            == ["6488", "8069"], str([r["stock_id"] for r in r8]))
        chk("⭐⭐ `period` 欄跟著改（⛔ 只搬檔不改欄 ⇒ 欄與檔名又互相矛盾）",
            bool(r8) and all(r["period"] == "2026-08" for r in r8),
            str([r["period"] for r in r8]))
        chk("⭐ 總列數不變（3 → 3）⛔ 這一支絕不可以變成刪東西的那個人",
            len(r7) + len(r8) == 3, f"{len(r7)}＋{len(r8)}")
        n2, msg2 = M.repair_periods("revenue")
        chk("⭐ 再跑一次是 no-op（⛔ 否則它會天天產生 commit）", n2 == 0, msg2)
        # ⭐ 取不到期別的列要**原地不動**，⛔ 不是丟掉
        io.open(os.path.join(rd, "2026-07.csv"), "a", encoding="utf-8").write(
            "9999,無期別,2026-07,twse,,9999,,9\n")
        n3, _ = M.repair_periods("revenue")
        r7b = list(csv.DictReader(io.open(os.path.join(rd, "2026-07.csv"),
                                          encoding="utf-8")))
        chk("⭐ 取不到期別的列留在原地（⛔ 不丟）",
            n3 == 0 and sorted(r["stock_id"] for r in r7b) == ["1101", "9999"],
            f"n={n3}｜{[r['stock_id'] for r in r7b]}")

        # ⛔⛔ 整批都搬走的檔要**刪掉**，⛔ 不是留一個只有表頭的空殼
        #   （空殼會被讀成「那一期沒有資料」；⚠ 而且原檔沒被重寫的話，
        #     同一列會在兩個檔裡各留一份——實測踩到）
        for f in glob.glob(os.path.join(rd, "*.csv")):
            os.remove(f)
        io.open(os.path.join(rd, "2026-07.csv"), "w", encoding="utf-8").write(
            _H + "\n8069,元太,2026-07,tpex,1150912,8069,11508,3\n")
        M.repair_periods("revenue")
        chk("⭐⭐ 整批搬走 ⇒ 舊檔被刪掉（⛔ 不是空殼、⛔ 也不是原封不動留著）",
            not os.path.exists(os.path.join(rd, "2026-07.csv"))
            and os.path.exists(os.path.join(rd, "2026-08.csv")),
            str(sorted(os.path.basename(x)
                       for x in glob.glob(os.path.join(rd, "*.csv")))))
        chk("⭐ 而那一列**只有一份**（⛔ 不可以兩個檔各留一份）",
            len(_rd("2026-08.csv")) == 1 and not _rd("2026-07.csv"))
        # ⛔⛔ ①那道「列數不符就一列都不寫」的閘門：拿掉它的突變原本**全綠**
        for f in glob.glob(os.path.join(rd, "*.csv")):
            os.remove(f)
        io.open(os.path.join(rd, "2026-07.csv"), "w", encoding="utf-8").write(
            _H + "\n"
            "6488,環球晶,2026-07,tpex,1150912,6488,11508,2\n"
            "6488,環球晶,2026-07,tpex,1150911,6488,11508,9\n")   # ⚠ 同代號兩列
        _before = io.open(os.path.join(rd, "2026-07.csv"), "rb").read()
        n4, msg4 = M.repair_periods("revenue")
        chk("⛔⛔ 搬家會少列時 **回 -1 並一列都不寫**"
            "（⚠ 這一支絕不可以變成刪東西的那個人）",
            n4 == -1 and "一列都不寫" in msg4, f"{n4}｜{msg4}")
        # ⚠ 檔不在時要印 ✗ 繼續跑，⛔ 不是崩潰（第七點②）
        _p07 = os.path.join(rd, "2026-07.csv")
        _now = io.open(_p07, "rb").read() if os.path.isfile(_p07) else None
        chk("⭐ 而檔案真的**逐位元沒變**（⛔ 只看回傳值不夠）",
            _now == _before and not os.path.exists(os.path.join(rd, "2026-08.csv")),
            "⛔ 檔不見了" if _now is None else "內容被動過")

        print("\n── 7之六. ⭐⭐ 呼叫點：`cmd_run` 真的會先自癒（⛔ 只測函式抓不到）──")
        # ⛔ 把 cmd_run 裡那一段拿掉的突變（R5）原本**全綠**。
        for f in glob.glob(os.path.join(rd, "*.csv")):
            os.remove(f)
        io.open(os.path.join(rd, "2026-07.csv"), "w", encoding="utf-8").write(
            _H + "\n8069,元太,2026-07,tpex,1150912,8069,11508,3\n")
        _old_get2, _old_rl2, _old_sleep2 = _B.get, _RL.PATH, time.sleep
        _RL.PATH = os.path.join(tmp, "_last_run2.md")
        _B.get, time.sleep = _fake_get, (lambda *a, **k: None)
        try:
            M.cmd_run(_ap.Namespace(sleep=0, kind="revenue"))
        finally:
            _B.get, _RL.PATH, time.sleep = _old_get2, _old_rl2, _old_sleep2
        _r7 = _rd("2026-07.csv")
        _r8 = _rd("2026-08.csv")
        chk("⭐⭐ 那一列錯期的舊列被 `cmd_run` 自己搬走了",
            "8069" not in [r["stock_id"] for r in _r7]
            and "8069" in [r["stock_id"] for r in _r8],
            f"7月 {[r['stock_id'] for r in _r7]}｜8月 {[r['stock_id'] for r in _r8]}")
        chk("⭐ runlog 講得出它搬了（⛔ 靜靜搬 = 列數變了沒有人知道）",
            "期別自癒" in io.open(os.path.join(tmp, "_last_run2.md"),
                               encoding="utf-8").read())

        print("\n── 8. 沒有碰到 repo ──")
        log_after = io.open(REPO_LOG, "rb").read() if os.path.isfile(REPO_LOG) else None
        chk("★ repo 的 data/mops/_changes.log 逐位元沒變", log_before == log_after)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\n[selftest] 通過 {ok}｜失敗 {fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
