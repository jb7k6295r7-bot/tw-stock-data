#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_tdcc.py — 釘住集保週檔那道「累積週數只准往上」的閘門。

    python3 selftest_tdcc.py

## ⛔⛔ 這支要擋的第一件事：**閘門掛在一條走不到的路上**

2026-09-14 我加那道閘門時把它寫在 `main()` **最後面**，
⚠ 而 `main()` 在「這一週的檔已經存在」時**早就 return 了**
——⭐ 而那是**每天都會走的那條路**（一週只有一天會寫新檔）。

```
實測 daily run 49（2026-09-15 00:16 台北）：
  tdcc ✓ 正常｜「2026-09-11 已存在，跳過」
  ⛔ 而 `_tdcc_weeks_low.txt` **根本沒有被建立**
  ⇒ 那道閘門一週只跑一天，⚠ 而它要擋的事每天都可能發生
```

⇒ ⚠ 這正是 CLAUDE.md 第七點③那一族：**測了判準、沒測呼叫點**
——判準本身沒問題，⛔ 而它掛在一條正常情況下走不到的路上。
⭐ 所以這支的主角是「**每一條 return 之前都叫到了嗎**」，⛔ 不是 `weeks_gate` 本身。

## ⚠ 而它**不連外**

`tdcc.py` 的 `main()` 第一件事就是打端點（開發容器 403、runner 上要花時間）
⇒ 這支**只驗 `weeks_gate` 與呼叫點**，⛔ 不跑 `main()`。
⇒ 呼叫點那一半靠**掃原始碼的 AST**。
"""
import ast
import hashlib
import io
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import lowwater  # noqa: E402
import tdcc as T  # noqa: E402

REAL_LOW = os.path.join(HERE, "data", "meta", "_tdcc_weeks_low.txt")


def _dig(p):
    return (hashlib.sha256(io.open(p, "rb").read()).hexdigest()
            if os.path.exists(p) else None)


B4 = _dig(REAL_LOW)
_n = [0, 0]


def ck(name, cond, detail=""):
    _n[0] += 1
    if cond:
        print(f"  ✓ {name}" + (f"　{detail}" if detail else ""))
    else:
        _n[1] += 1
        print(f"  ✗ {name}　{detail}")


class FakeRun:
    def __init__(self):
        self.infos, self.checks = [], []

    def info(self, k, v=""):
        self.infos.append((k, v))

    def check(self, k, cond, detail=""):
        self.checks.append((k, bool(cond), detail))

    def note(self, *a, **kw):
        self.infos.append(("note", str(a)))

    def finish(self):
        return 1 if any(not c for _k, c, _d in self.checks) else 0


print("\n── ① ⭐⭐ 每一條 return 之前都要叫到 `weeks_gate`（掃 AST）──")
_src = io.open(os.path.join(HERE, "tdcc.py"), encoding="utf-8").read()
_tree = ast.parse(_src)
_main = next((f for f in ast.walk(_tree)
              if isinstance(f, ast.FunctionDef) and f.name == "main"), None)
ck("找得到 `main()`", _main is not None)

# 每一個 `return rl.finish()` 之前，同一個 block 裡要有 weeks_gate(...)
def _returns_with_gate(node):
    """→ [(return 的行號, 它前面同一層有沒有 weeks_gate)]。"""
    out = []
    for blk in ast.walk(node):
        body = getattr(blk, "body", None)
        if not isinstance(body, list):
            continue
        for i, st in enumerate(body):
            if not (isinstance(st, ast.Return) and st.value is not None
                    and "finish" in ast.dump(st.value)):
                continue
            before = body[:i]
            has = any(isinstance(n, ast.Call)
                      and getattr(n.func, "id", "") == "weeks_gate"
                      for s in before for n in ast.walk(s))
            out.append((st.lineno, has))
    return out


_rets = _returns_with_gate(_main)
ck(f"⭐ `main()` 裡有 {len(_rets)} 個 `return rl.finish()`"
   "（⛔ 0 個代表這條掃描壞了）", len(_rets) >= 4, str(_rets))

# ⚠ 前面幾條是「端點掛了／欄位對不上」——那幾條**不必**叫閘門（目錄可能還沒建）。
#   ⭐ 要釘的是**「已存在，跳過」那一條**：它是每天都會走的。
_skip_ln = next((i + 1 for i, l in enumerate(_src.split("\n"))
                 if "已存在，跳過（--force 可覆寫）" in l), None)
ck("找得到「已存在，跳過」那一條路", _skip_ln is not None, str(_skip_ln))
_after_skip = [(ln, has) for ln, has in _rets if ln > (_skip_ln or 0)]
ck("⭐⭐ 「已存在，跳過」之後那個 return **前面有** `weeks_gate`"
   "（⛔ 這就是一週只守一天的那個 bug）",
   bool(_after_skip) and _after_skip[0][1],
   str(_after_skip[:2]))
_last = _rets[-1] if _rets else None
ck("⭐ 而正常寫完那一條也有", _last is not None and _last[1], str(_last))
_n_gate = sum(1 for n in ast.walk(_main)
              if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "weeks_gate")
ck("⭐ `weeks_gate` 在 `main()` 裡被叫**至少兩次**（跳過那條＋正常那條）",
   _n_gate >= 2, f"{_n_gate} 次")

print("\n── ② 方向是 `UP`，⛔ 不是 DOWN（週檔只會變多）──")
_dirs = [n.attr for n in ast.walk(_tree)
         if isinstance(n, ast.Attribute)
         and getattr(n.value, "id", "") == "lowwater"
         and n.attr in ("UP", "DOWN")]
ck("⭐⭐ 用到的方向**全部是 UP**（⛔ 抄成 DOWN ⇒ 週數變少也會綠）",
   _dirs and all(d == "UP" for d in _dirs), str(_dirs))

print("\n── ③ `weeks_gate` 自己：數目錄、退步要紅 ──")
with tempfile.TemporaryDirectory() as d:
    old_out, old_low = T.OUT_DIR, T.LOW
    try:
        T.OUT_DIR = os.path.join(d, "tdcc")
        T.LOW = os.path.join(d, "_tdcc_weeks_low.txt")
        os.makedirs(T.OUT_DIR)
        for w in ("2026-08-28", "2026-09-04", "2026-09-11"):
            io.open(os.path.join(T.OUT_DIR, f"{w}.csv"), "w").write("x\n")
        rl = FakeRun()
        ck("數得出 3 週", T.weeks_gate(rl) == 3)
        ck("  第一趟不判定（沒有水位檔）", not rl.checks, str(rl.checks))
        ck("  ⭐ 而水位檔被建立成 3",
           io.open(T.LOW, encoding="utf-8").read().startswith("3,"),
           io.open(T.LOW, encoding="utf-8").read())
        # ⛔ 少一週 ⇒ 要紅
        os.remove(os.path.join(T.OUT_DIR, "2026-08-28.csv"))
        rl = FakeRun()
        ck("⭐⭐ 週數從 3 掉到 2 ⇒ check 是 False", T.weeks_gate(rl) == 2
           and rl.checks and rl.checks[0][1] is False, str(rl.checks))
        ck("  ⛔ 而水位檔**還是 3**（⚠ 被寫小 = 那道閘門從此永遠綠）",
           io.open(T.LOW, encoding="utf-8").read().startswith("3,"),
           io.open(T.LOW, encoding="utf-8").read())
        # ⭐ 反向：多一週要綠並上修
        for w in ("2026-08-28", "2026-09-18"):
            io.open(os.path.join(T.OUT_DIR, f"{w}.csv"), "w").write("x\n")
        rl = FakeRun()
        ck("⭐ 反向：週數變多 ⇒ 綠，而且水位上修到 4",
           T.weeks_gate(rl) == 4 and rl.checks[0][1] is True
           and io.open(T.LOW, encoding="utf-8").read().startswith("4,"),
           io.open(T.LOW, encoding="utf-8").read())
        # ⛔ 目錄不存在不可以炸掉
        T.OUT_DIR = os.path.join(d, "沒這個目錄")
        rl = FakeRun()
        ck("⛔ 目錄不存在 ⇒ 回 0 而不是炸掉", T.weeks_gate(rl) == 0)
        ck("  ⭐ 而且明講「目錄是空的」（⚠ 0 週跟沒跑長得一樣）",
           any("目錄是空的" in f"{k}{v}" for k, v in rl.infos), str(rl.infos))
    finally:
        T.OUT_DIR, T.LOW = old_out, old_low

print("\n── ⑤ ⭐⭐ 三道驗算**只有一份實作**（`week_facts`）──")
# ⛔ 2026-09-15 之前那三道整段寫在 `main()` 裡 ⇒ 要匯入歷史檔就只能抄一份，
#   ⚠ 而「同一個判準的兩份實作，只要外觀不同就躲得過 selftest_no_dup」（四點五第八次）。
_src = io.open(os.path.join(HERE, "tdcc.py"), encoding="utf-8").read()
_t = ast.parse(_src)
_main = next(f for f in ast.walk(_t) if isinstance(f, ast.FunctionDef) and f.name == "main")
_imp = next(f for f in ast.walk(_t) if isinstance(f, ast.FunctionDef) and f.name == "import_hist")
for fn, node in (("main", _main), ("import_hist", _imp)):
    ck(f"⭐ `{fn}()` 走的是共用的 `week_facts`",
       any(isinstance(n, ast.Call) and getattr(n.func, "id", "") == "week_facts"
           for n in ast.walk(node)))
    ck(f"  ⛔ 而 `{fn}()` 裡**沒有**自己再算一次恆等式（⚠ 抄第二份就是那一族）",
       "TOTAL_LEVEL" not in ast.dump(node))

print("\n── ⑥ 三道驗算各自會紅（合成資料，⛔ 不靠現場）──")
def _rows(day="20190628", n_lv=17, break_people=False, break_shares=False, day2=None):
    out = []
    for code in ("1101", "2330"):
        tot_p = tot_s = 0
        for lv in range(1, n_lv + 1):
            d = day2 if (day2 and code == "2330" and lv == 1) else day
            if lv <= 15:
                p, sh = 10 * lv, 100 * lv
                tot_p += p; tot_s += sh
            elif lv == 16:            # 差異數調整
                p, sh = 7, 500
                tot_s -= sh           # 股數要減它
            else:                     # 17 = 合計
                p, sh = tot_p, tot_s
                if break_people: p += 1
                if break_shares: sh += 1
            out.append({"資料日期": d, "證券代號": code, "持股分級": str(lv),
                        "人數": str(p), "股數": str(sh), "占集保庫存數比例%": "1.0"})
    return out

_d, _by, _bl, _bad, _ds = T.week_facts(_rows())
ck("乾淨的一份：三道全過", not _bl and not _bad["人數"] and not _bad["股數"]
   and len(_ds) == 1 and _d == "2019-06-28", f"{_d}｜{_bl}｜{_bad}")
ck("⛔ 少一級 ⇒ 抓到", bool(T.week_facts(_rows(n_lv=16))[2]))
ck("⛔ 人數合計錯 ⇒ 抓到", T.week_facts(_rows(break_people=True))[3]["人數"] == ["1101", "2330"])
ck("⛔ 股數合計錯 ⇒ 抓到", T.week_facts(_rows(break_shares=True))[3]["股數"] == ["1101", "2330"])
ck("⭐⭐ 而人數那道**不減**差異數調整（⛔ 兩條式子不一樣）",
   not T.week_facts(_rows())[3]["人數"], "乾淨的一份人數要全過")
ck("⛔ 兩個資料日期（累計檔）⇒ 抓到",
   len(T.week_facts(_rows(day2="20190705"))[4]) == 2)

print("\n── ⑥.5 ⛔⛔ **兩個 BOM**：`utf-8-sig` 只吃掉一個 ──")
# 【實測 2026-09-15】使用者封存裡 2020 年有 6 份開頭是 `efbbbf efbbbf`
#   ⇒ 第一個欄名變成 `\ufeff資料日期` ⇒ 對不上 DATE_KEYS ⇒ 那六週整批被擋。
# ⚠ 而這是**我方 parse() 的缺口**：官方端點哪天多送一個 BOM，`main()`
#   會用一模一樣的方式壞掉——⛔ 而它會長成「缺 date 欄」，不像 BOM 問題。
_hdr = "資料日期,證券代號,持股分級,人數,股數,占集保庫存數比例%\n20190628,1101,1,1,1,1.0\n"
for n_bom, label in ((0, "沒有 BOM"), (1, "一個 BOM"), (2, "⭐ 兩個 BOM"), (3, "三個 BOM")):
    raw = ("\ufeff" * n_bom + _hdr).encode("utf-8")
    rows, note = T.parse(raw)
    ok = bool(rows) and not T.cols_of(rows)["missing"]
    ck(f"{label} ⇒ 六個欄名都認得出來", ok,
       f"{note}｜missing={T.cols_of(rows)['missing'] if rows else '(沒有列)'}")
ck("  ⭐ 而 BOM 剝掉之後第一個欄名逐字是 `資料日期`（⛔ 不是 \\ufeff資料日期）",
   list(T.parse(("\ufeff\ufeff" + _hdr).encode())[0][0])[0] == "資料日期",
   repr(list(T.parse(("\ufeff\ufeff" + _hdr).encode())[0][0])[0]))

print("\n── ⑦ `import_hist`：不過就不寫、不帶 --apply 就不寫 ──")
with tempfile.TemporaryDirectory() as d:
    import csv as _csv
    src = os.path.join(d, "src", "2019"); os.makedirs(src)
    def _w(name, rows):
        with io.open(os.path.join(src, name), "w", encoding="utf-8", newline="") as f:
            w = _csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    _w("20190628.csv", _rows("20190628"))
    out = os.path.join(d, "out")
    old_out = T.OUT_DIR
    import pyarrow.parquet as _pq_early
    try:
        T.OUT_DIR = os.path.join(d, "nope")      # 沒有重疊週
        rl = FakeRun()
        T.import_hist(rl, os.path.join(d, "src"), out_dir=out, apply=False)
        ck("⛔ 不帶 `--apply` ⇒ 一個檔都不寫", not os.path.isdir(out))
        ck("  ⭐ 而且明講「只驗不寫」",
           any("只驗不寫" in f"{k}{v}" for k, v in rl.infos), str(rl.infos[-3:]))
        ck("⭐⭐ 沒有重疊週 ⇒ 大聲說**這一層沒跑**（⛔ 不是靜靜通過）",
           any("這一層沒跑" in f"{k}{v}" for k, v in rl.infos),
           str([i for i in rl.infos if "沒跑" in str(i)]))
        # ⛔ 壞掉的一份 ⇒ 整批不寫
        _w("20190705.csv", _rows("20190705", break_shares=True))
        rl = FakeRun()
        T.import_hist(rl, os.path.join(d, "src"), out_dir=out, apply=True)
        ck("⛔⛔ 有一份沒過驗算 ⇒ **一個檔都不寫**", not os.path.isdir(out),
           str(os.path.isdir(out)))
        ck("  ⭐ 而那一條 check 是 False", any(
            "三道驗算" in k and c is False for k, c, _ in rl.checks), str(rl.checks))
        os.remove(os.path.join(src, "20190705.csv"))
        # ⛔ 檔名與內容講的日期不一致
        _w("20190712.csv", _rows("20190719"))
        rl = FakeRun()
        T.import_hist(rl, os.path.join(d, "src"), out_dir=out, apply=True)
        # ⛔⛔ 檔名≠內容**不該擋**——內容才是判準（第二點），檔名是人取的。
        #   ⭐ 要驗的是兩件事：① 大聲講出來 ② 它照**內容**的日期落地。
        #   ⚠ 我第一版斷言它要擋，那是把「檔名」當成了判準。
        ck("⭐ 檔名 0712／內容 0719 ⇒ **大聲講**，⛔ 但不擋",
           any("檔名與內容講的日期不一致" in k for k, _v in rl.infos)
           and os.path.exists(os.path.join(out, "2019.parquet")),
           str([i for i in rl.infos if "檔名" in str(i)]))
        _t3 = _pq_early.read_table(os.path.join(out, "2019.parquet"))
        ck("  ⭐⭐ 而它照**內容**的日期（2019-07-19）落地，⛔ 不是檔名那個",
           "2019-07-19" in set(_t3.column("date").to_pylist()),
           str(sorted(set(_t3.column("date").to_pylist()))))
        os.remove(os.path.join(src, "20190712.csv"))
        import shutil as _sh0; _sh0.rmtree(out, ignore_errors=True)

        # ⭐⭐ 同一天兩份：內容相同 ⇒ 歸因（不擋）；內容不同 ⇒ ⛔ 擋
        _w("20200612.csv", _rows("20200612"))
        _w("20200619.csv", _rows("20200612"))      # 逐格相同 ⇒ 檔名重複
        rl = FakeRun()
        T.import_hist(rl, os.path.join(d, "src"), out_dir=out, apply=True)
        ck("⭐⭐ 同一週存成兩個檔名（內容相同）⇒ 歸因、丟一份，⛔ 不擋",
           any("同一週被存成兩個檔名" in k for k, _v in rl.infos)
           and os.path.exists(os.path.join(out, "2020.parquet")),
           str([i for i in rl.infos if "兩個檔名" in str(i)]))
        ck("  ⭐ 而且明講「那幾個檔名對應的週其實沒有」（⚠ 別把檔案數當週數）",
           any("其實沒有" in f"{k}{v}" for k, v in rl.infos))
        _t4 = _pq_early.read_table(os.path.join(out, "2020.parquet"))
        ck("  ⭐ 2020 只落地 1 週（⛔ 不是 2 週）",
           len(set(_t4.column("date").to_pylist())) == 1,
           str(sorted(set(_t4.column("date").to_pylist()))))
        _sh0.rmtree(out, ignore_errors=True)
        _w("20200619.csv", _rows("20200612"))
        # ⚠ 造一份同一天但**內容不同**的——⛔ 而那個「不同」不可以順便
        #   破壞恆等式，否則它會在更前面就被擋掉，⭐ 這一條就測不到重複那道。
        #   （第一版改 `人數` ⇒ 合計對不上 ⇒ 走的是「三道驗算」那條路。）
        #   ⇒ 改 `pct`：它不屬於任何一道恆等式。
        _bad_rows = _rows("20200612")
        _bad_rows[0]["占集保庫存數比例%"] = "99.9"
        _w("20200626.csv", _bad_rows)
        rl = FakeRun()
        T.import_hist(rl, os.path.join(d, "src"), out_dir=out, apply=True)
        ck("⛔⛔ 同一天但內容**不同** ⇒ 真的矛盾 ⇒ 整批不寫",
           any("不可以不同" in k and c is False for k, c, _ in rl.checks)
           and not os.path.isdir(out), str(rl.checks))
        for f in ("20200612.csv", "20200619.csv", "20200626.csv"):
            os.remove(os.path.join(src, f))
        # ⭐ 正常 ⇒ 寫得出來、而且重讀對得回來
        rl = FakeRun()
        rc = T.import_hist(rl, os.path.join(d, "src"), out_dir=out, apply=True)
        ck("⭐ 乾淨的一份 ⇒ 寫出 2019.parquet",
           os.path.exists(os.path.join(out, "2019.parquet")))
        ck("  ⭐⭐ 而它**重讀**驗過（⛔ 不是斷言寫檔成功）",
           any("寫完重讀" in k and c is True for k, c, _ in rl.checks), str(rl.checks))
        _t2 = _pq_early.read_table(os.path.join(out, "2019.parquet"))
        ck("  ⭐ 讀回來 34 列（2 檔 × 17 級）", _t2.num_rows == 34, str(_t2.num_rows))
        ck("  ⭐ 欄名逐字＝HIST_COLS", _t2.column_names == T.HIST_COLS, str(_t2.column_names))

        # ⭐⭐ 重疊週對不上 ⇒ 擋下來
        T.OUT_DIR = os.path.join(d, "mine"); os.makedirs(T.OUT_DIR)
        with io.open(os.path.join(T.OUT_DIR, "2019-06-28.csv"), "w",
                     encoding="utf-8", newline="") as f:
            w = _csv.writer(f); w.writerow(T.HEADER)
            w.writerow(["2019-06-28", "1101", "1", "999999", "100", "1.0"])
        import shutil as _sh; _sh.rmtree(out, ignore_errors=True)
        rl = FakeRun()
        T.import_hist(rl, os.path.join(d, "src"), out_dir=out, apply=True)
        ck("⭐⭐ 重疊週跟我方對不上 ⇒ **整批不寫**（⛔ 這是唯一的獨立驗證點）",
           any("逐格相同" in k and c is False for k, c, _ in rl.checks)
           and not os.path.isdir(out), str(rl.checks))
    finally:
        T.OUT_DIR = old_out

print("\n── ④ ★ 沒有動到 repo 真的 `_tdcc_weeks_low.txt` ──")
ck("★ 逐位元沒變（含「本來就不存在」這一種）", _dig(REAL_LOW) == B4,
   f"{B4} → {_dig(REAL_LOW)}")

print(f"\n[selftest] 通過 {_n[0] - _n[1]}｜失敗 {_n[1]}")
sys.exit(1 if _n[1] else 0)
