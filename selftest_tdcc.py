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

# ⛔⛔ 2026-09-15 付過代價：⑦⑧ 兩節要 pyarrow，而我在 ⑦ 裡寫的是**裸 import**
#   ⇒ runner 上沒有 pyarrow ⇒ 這支當場 traceback ⇒ ⛔ `set -e` 把同一個 job 裡
#     後面**六個步驟**掐死，其中一個是「把程式同步到 main」（probe run 84／86 實測）
#   ⇒ ⭐ CLAUDE.md 六點五那條逐字成立：
#     **一條在某個環境下【必然】不成立的斷言，等於把那個環境的整條線關掉。**
# ⇒ 處置：條件不成立就**大聲印「這一層沒跑」**，⛔ 不算失敗。
# ⚠ 而它只准有**一份**（四點五）：⑧ 本來自己 try 了一次，已改成讀這裡。
try:
    import numpy as _np  # noqa: F401,E402  ⭐ derive_levels 的夾逼要用
    import pyarrow as _pa2  # noqa: E402
    import pyarrow.parquet as _pq_early  # noqa: E402
    HAS_PA = True
except ImportError:
    _np = _pa2 = _pq_early = None
    HAS_PA = False

# ⚠ 這一行要寫成**不會被讀成「驗過了」**的樣子——⛔ 一行 `skipped` 跟一行 `ok`
#   在捲動的 log 裡看起來一樣。
NO_PA = ("  ⚠⚠ **這一層沒跑**：這台沒有 pyarrow／numpy"
         "　⇒ ⛔ 不算失敗，⛔ **也不算驗過**")

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

print("\n── ⑥.8 ⛔⛔ 截斷要**直接問**，不要從別的症狀推 ──")
_hdr2 = b"\xef\xbb\xbf" + "資料日期,證券代號,持股分級,人數,股數,占集保庫存數比例%\r\n".encode()
_body = "20231020,1101,1,96,15269,0.02\r\n".encode()
ck("正常（有換行、欄數齊）⇒ 不算截斷",
   T.looks_truncated(_hdr2 + _body) == "", repr(T.looks_truncated(_hdr2 + _body)))
# ⚠ 真檔那一行是 `…,760864,`（結尾有逗號）⇒ **逗號數跟表頭一樣**
#   ⇒ 欄數那條抓不到它，真正抓到它的是「檔尾沒有換行」＋「KiB 整數倍」。
_cut_comma = _hdr2 + _body + "20231020,8162,2,343,760864,".encode()
ck("⛔ 切在逗號後（欄數一樣）⇒ 仍然靠『檔尾沒換行』抓到",
   "檔尾沒有換行" in T.looks_truncated(_cut_comma), T.looks_truncated(_cut_comma))
# ⭐ 切在欄位**中間** ⇒ 欄數那條才會說話
_cut_mid = _hdr2 + _body + "20231020,8162,2,343,7608".encode()
ck("⛔ 切在欄位中間 ⇒ 欄數那條說得出來",
   "欄" in T.looks_truncated(_cut_mid), T.looks_truncated(_cut_mid))
_pad = _hdr2 + _body * 10
_pad = _pad + b"x" * ((1024 - len(_pad) % 1024) % 1024)
ck("⭐⭐ 大小剛好是 KiB 整數倍 ⇒ 也算（⛔ 切在列邊界時只剩這個線索）",
   "區塊邊界" in T.looks_truncated(_pad), T.looks_truncated(_pad))
ck("  ⛔ 空的位元組不算截斷（⚠ 那是別的問題）", T.looks_truncated(b"") == "")

print("\n── ⑦ `import_hist`：不過就不寫、不帶 --apply 就不寫 ──")
if not HAS_PA:
    print(NO_PA)
else:
    with tempfile.TemporaryDirectory() as d:
        import csv as _csv
        src = os.path.join(d, "src", "2019"); os.makedirs(src)
        def _w(name, rows):
            with io.open(os.path.join(src, name), "w", encoding="utf-8", newline="") as f:
                w = _csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
        _w("20190628.csv", _rows("20190628"))
        out = os.path.join(d, "out")
        old_out = T.OUT_DIR
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
            # ⛔⛔ 逐週排除，**不是**整批不寫：一週壞掉不可以賠掉其餘的。
            #   ⚠ 我第一版是整批擋 ⇒ 372 週裡 1 份截斷就全部寫不出來。
            ck("⭐⭐ 壞掉那一週被**排除**，其餘照寫（⛔ 不是整批不寫）",
               os.path.exists(os.path.join(out, "2019.parquet")),
               str(os.path.isdir(out)))
            ck("  ⭐ 而排除的那幾週要**逐筆講出原因**",
               any("排除的週" in k and "20190705" in v for k, v in rl.infos),
               str([i for i in rl.infos if "排除" in str(i)]))
            _t0 = _pq_early.read_table(os.path.join(out, "2019.parquet"))
            ck("  ⭐⭐ 而壞掉那一週**一列都沒寫進去**（⛔ 絕不寫部分資料）",
               "2019-07-05" not in set(_t0.column("date").to_pylist()),
               str(sorted(set(_t0.column("date").to_pylist()))))
            _sh0b = __import__("shutil"); _sh0b.rmtree(out, ignore_errors=True)
            ck("  ⭐ 而母體只有 2 份 ⇒ 通過率那道**大聲說判不出來**"
               "（⛔ 不假裝判過，⛔ 也不假紅）",
               any("這一層沒跑" in k and "通過率" in k for k, _v in rl.infos),
               str([i for i in rl.infos if "通過率" in str(i)]))
            # ⛔⛔ 而「截斷」要真的接在 `import_hist` 裡（⚠ 只驗純函式不夠：
            #   突變 W9「截斷不擋」第一次**全綠**，因為我只測了 `looks_truncated`）
            _sh0c = __import__("shutil"); _sh0c.rmtree(out, ignore_errors=True)
            for f in list(os.listdir(src)):
                os.remove(os.path.join(src, f))
            _w("20190628.csv", _rows("20190628"))
            # 造一份截斷的：把檔尾的換行砍掉、並補到 KiB 整數倍
            _p2 = os.path.join(src, "20190705.csv")
            _w("20190705.csv", _rows("20190705"))
            _b = io.open(_p2, "rb").read().rstrip(b"\r\n")
            _b += b" " * ((1024 - len(_b) % 1024) % 1024)
            io.open(_p2, "wb").write(_b)
            rl = FakeRun()
            T.import_hist(rl, os.path.join(d, "src"), out_dir=out, apply=True)
            ck("⭐⭐ 截斷的那一週被**排除**（⚠ 只驗純函式不夠，要驗呼叫點）",
               any("排除的週" in k and "被截斷" in v for k, v in rl.infos),
               str([i for i in rl.infos if "排除" in str(i)]))
            _t9 = _pq_early.read_table(os.path.join(out, "2019.parquet"))
            ck("  ⭐ 而它**一列都沒寫進去**",
               "2019-07-05" not in set(_t9.column("date").to_pylist()),
               str(sorted(set(_t9.column("date").to_pylist()))))
            _sh0c.rmtree(out, ignore_errors=True)
            # ⭐ 母體夠大、而**大部分**壞掉 ⇒ 通過率那道要紅
            for f in list(os.listdir(src)):
                os.remove(os.path.join(src, f))
            for i in range(30):
                day = f"201908{i+1:02d}"
                rr = _rows(day)
                if i >= 3:
                    rr[0]["股數"] = "999999"          # ⛔ 27/30 壞 ⇒ 10%
                _w(f"{day}.csv", rr)
            rl = FakeRun()
            T.import_hist(rl, os.path.join(d, "src"), out_dir=out, apply=True)
            ck("⭐⭐ 母體 30 份、通過率 10% ⇒ **整批不寫**"
               "（⛔ 少數壞掉是封存的事，多數壞掉是我方讀錯）",
               any("通過率" in k and c is False for k, c, _ in rl.checks)
               and not os.path.isdir(out), str(rl.checks))
            for f in list(os.listdir(src)):
                os.remove(os.path.join(src, f))
            _w("20190628.csv", _rows("20190628"))
            _w("20190705.csv", _rows("20190705", break_shares=True))
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

            # ⭐⭐ 檔數斷崖：⛔ 三道驗算抓不到「截斷剛好落在列邊界」那一種
            import shutil as _sh1; _sh1.rmtree(out, ignore_errors=True)
            T.OUT_DIR = os.path.join(d, "nope2")
            for f in list(os.listdir(src)):
                os.remove(os.path.join(src, f))
            def _many(day, n_codes):
                out_rows = []
                for i in range(n_codes):
                    code = f"{1000+i}"
                    tp = ts = 0
                    for lv in range(1, 18):
                        if lv <= 15: p, sh = 10*lv, 100*lv; tp += p; ts += sh
                        elif lv == 16: p, sh = 7, 500; ts -= sh
                        else: p, sh = tp, ts
                        out_rows.append({"資料日期": day, "證券代號": code,
                                         "持股分級": str(lv), "人數": str(p),
                                         "股數": str(sh), "占集保庫存數比例%": "1.0"})
                return out_rows
            for day, n in (("20230106", 100), ("20230113", 100), ("20230120", 100),
                           ("20230127", 60)):      # ⛔ 最後一週斷崖，⚠ 但每檔都剛好 17 級
                _w(f"{day}.csv", _many(day, n))
            rl = FakeRun()
            T.import_hist(rl, os.path.join(d, "src"), out_dir=out, apply=True)
            ck("⭐⭐ 檔數斷崖（60 vs 中位 100）⇒ 擋下來"
               "　⚠ 而那四週**三道驗算全過**（⛔ 它們抓不到截斷）",
               any("斷崖" in k and c is False for k, c, _ in rl.checks)
               and not os.path.isdir(out), str([c for c in rl.checks]))
            ck("  ⭐⭐ 而那四週**一週都沒被排除**（⇒ 三道驗算全過）"
               "　⇒ 這就證明斷崖那道**不是多餘的**",
               not any("排除的週" in k for k, _v in rl.infos),
               str([i for i in rl.infos if "排除" in str(i)]))
            ck("  ⭐ 訊息講得出**檔數、中位數、檔案大小**（⇒ 看得出是截斷）",
               any("斷崖" in k and "中位" in dt and "bytes" in dt
                   for k, _c, dt in rl.checks), str(rl.checks))
            # ⭐ 反向：檔數正常的四週不可以假紅
            _w("20230127.csv", _many("20230127", 98))
            rl = FakeRun()
            T.import_hist(rl, os.path.join(d, "src"), out_dir=out, apply=True)
            ck("⭐ 反向：98 vs 中位 100（差 2%）⇒ 不可以假紅",
               any("斷崖" in k and c is True for k, c, _ in rl.checks)
               and os.path.exists(os.path.join(out, "2023.parquet")), str(rl.checks))
            for f in list(os.listdir(src)):
                os.remove(os.path.join(src, f))
            _sh1.rmtree(out, ignore_errors=True)
            _w("20190628.csv", _rows("20190628"))
            T.OUT_DIR = os.path.join(d, "nope")

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

print("\n── ⑧ ⭐⭐ 持股級距是**夾出來**的，⛔ 不是抄坊間表 ──")
# ⭐ 判準本身拿**合成**資料驗（環境無關）：造一個級距**已知**的假庫，
#   看 `derive_levels()` 夾不夾得回那些邊界。
#   ⛔ 拿真實 tdcc_hist 驗判準的話，這條的壽命會綁在「現在剛好是那批資料」上
#     （第七點第七個陷阱）。
_pq3 = _pq_early          # ⭐ 同一份探測（⛔ 不再各 try 一次）
if not HAS_PA:
    print(NO_PA)
else:
    with tempfile.TemporaryDirectory() as d:
        # 真邊界（我自己訂的）：1-99｜100-500｜501-2000｜2001 以上
        TRUE_UB = [99, 500, 2000]
        recs = []
        import random as _rnd
        _rnd.seed(15)
        for wk in range(40):
            for code in range(30):
                bounds = [(1, 99), (100, 500), (501, 2000), (2001, 50000)]
                for k, (a, b) in enumerate(bounds, start=1):
                    # ⭐ 讓每一級偶爾出現「只有 1 個人、剛好持有**下界**／**上界**」
                    #   ⇒ 那兩格正是把 min(avg)／max(avg) 推到邊界的那一格。
                    # ⭐⭐ 而第 1 級**故意不給上界那一格** ⇒ 造出
                    #   「**上界夾死、下界沒夾死**」的第 2 級
                    #   ⇒ 那是 `exact` 那一欄唯一會分岔的形狀（⛔ 沒有它，
                    #     「exact 只看上界」的寫法跟正確的寫法長得一模一樣）。
                    if wk % 7 == k % 7 and k != 1:
                        pe, sh = 1, b if b < 50000 else 9999
                    elif wk % 11 == k % 11:
                        pe, sh = 1, a
                    else:
                        pe = _rnd.randint(2, 50)
                        top = (b - 5) if k == 1 else b       # ⛔ 第 1 級搆不到上界
                        sh = _rnd.randint(a * pe, top * pe)
                    recs.append((f"2020-01-{wk+1:02d}", f"{1000+code}", k, pe, sh))
                for k in (4 + 1, 4 + 2):   # 補到 17 級的形狀（16 調整、17 合計）
                    recs.append((f"2020-01-{wk+1:02d}", f"{1000+code}", k, 0, 0))
        _pq3.write_table(_pa2.table({
            "date": _pa2.array([r[0] for r in recs]),
            "stock_id": _pa2.array([r[1] for r in recs]),
            "level": _pa2.array([r[2] for r in recs], _pa2.int8()),
            "people": _pa2.array([r[3] for r in recs], _pa2.int64()),
            "shares": _pa2.array([r[4] for r in recs], _pa2.int64()),
        }), os.path.join(d, "2020.parquet"))
        _old_n = T.N_LEVELS
        try:
            T.N_LEVELS = 6            # 4 個級距 ＋ 調整 ＋ 合計
            rows, note = T.derive_levels(d)
            ck("⭐ 夾得出 4 級", len(rows) == 4, f"{len(rows)}｜{note}")
            for i, ub in enumerate(TRUE_UB):
                r = rows[i]
                ck(f"  ⭐⭐ 第 {i+1} 級的真上界 {ub} 落在夾出來的 "
                   f"[{r[3]}, {r[4]}] 裡（⛔ 夾錯就是判準壞了）",
                   r[3] <= ub <= r[4], f"{r[3]} ~ {r[4]}")
            # ⛔⛔ 而**下界**也是一個區間——第一版把它寫成
            #   `round(hi[k-1]) + 1`（上一級上界的**樂觀端**）
            #   ⇒ 最高那一級印出一個看起來確定、其實差 1 股沒夾死的數字。
            TRUE_LB = [1] + [u + 1 for u in TRUE_UB]
            for i, lb in enumerate(TRUE_LB):
                r = rows[i]
                ck(f"  ⭐⭐ 第 {i+1} 級的真下界 {lb} 也落在夾出來的 "
                   f"[{r[1]}, {r[2]}] 裡",
                   r[1] <= lb <= r[2], f"{r[1]} ~ {r[2]}")
            ck("  ⭐ 而下界的區間 ＝ 上一級上界的區間 +1（⛔ 不是取一端）",
               all(rows[i + 1][1] == rows[i][3] + 1
                   and rows[i + 1][2] == rows[i][4] + 1
                   for i in range(len(rows) - 1)),
               str([(r[1], r[2], r[3], r[4]) for r in rows]))
            ck("  ⭐ 而級距接得起來（a_{k+1} = b_k + 1）",
               not T.levels_gaps(rows), str(T.levels_gaps(rows)))
            ck("  ⭐ 至少夾出一級**兩端都是**唯一解（⇒ 樣本夠）",
               any(r[5] == "1" for r in rows), str([r[5] for r in rows]))
            # ⭐⭐ `exact` 是「**兩端都**夾死」，⛔ 不是「上界夾死」。
            #   ⚠ 這一條要有「上界夾死、下界沒夾死」的樣本才驗得到
            #     ⇒ 上面的假庫**刻意**造了一級出來（⛔ 不是碰運氣）。
            _half = [r for r in rows if r[3] == r[4] and r[1] != r[2]]
            ck("⭐⭐ 假庫真的造出「上界夾死、下界沒夾死」那一級"
               "（⛔ 沒有它，這條斷言驗不到東西）",
               bool(_half), str([(r[0], r[1], r[2], r[3], r[4]) for r in rows]))
            ck("⭐⭐ 而那一級的 `exact` 必須是 **0**（⛔ `exact` 不是只看上界）",
               all(r[5] == "0" for r in _half),
               str([(r[0], r[5]) for r in _half]))
            # ⛔ 接不起來要抓到
            _broken = [list(r) for r in rows]
            _broken[1][1] = _broken[0][3] + 99      # 造一個縫
            ck("⛔ 級距中間有縫 ⇒ `levels_gaps` 抓到",
               bool(T.levels_gaps(_broken)), str(T.levels_gaps(_broken)))
            # ⭐⭐ 而**只有一端**對不上也要抓到（⛔ 第一版只比一端 ⇒ 這個會漏）
            _one = [list(r) for r in rows]
            _one[1][2] = _one[1][2] + 7             # 只動下界的 hi 那一端
            ck("⛔⛔ **只有一端**接不上也要抓到（⚠ 三點1：只比一個方向）",
               bool(T.levels_gaps(_one)), str(T.levels_gaps(_one)))

            # ── `level_of`：沒夾死的地方要回**兩個**級別 ──
            # 真邊界 1-99｜100-500｜501-2000｜2001+ ⇒ 99 與 500 都夾死了嗎？
            ck("⭐ 某個**確定**在第 1 級的股數 ⇒ 回 (1, 1)",
               T.level_of(rows, 50) == (1, 1), str(T.level_of(rows, 50)))
            ck("⭐ 某個**確定**在最高級的股數 ⇒ 兩端都是最高級",
               T.level_of(rows, 999_999) == (4, 4), str(T.level_of(rows, 999_999)))
            # ⭐⭐ 造一個**沒夾死**的邊界，問那一股 ⇒ 必須回兩個級別
            _fz = [list(r) for r in rows]
            _fz[0][3], _fz[0][4] = 99, 101          # 第 1 級上界故意不夾死
            _fz[1][1], _fz[1][2] = 100, 102
            ck("⭐⭐ 邊界沒夾死時 ⇒ `level_of` 回**兩個**級別（⛔ 不挑一端）",
               T.level_of(_fz, 100) == (1, 2), str(T.level_of(_fz, 100)))
            ck("  ⭐ 而區間外那一股仍然只有一個答案",
               T.level_of(_fz, 99) == (1, 1) and T.level_of(_fz, 102) == (2, 2),
               f"{T.level_of(_fz, 99)}｜{T.level_of(_fz, 102)}")
        finally:
            T.N_LEVELS = _old_n

        # ⭐ 而呼叫點（`levels_cmd`）真的把那兩道接上去
        rl = FakeRun()
        T.N_LEVELS = 6
        try:
            T.levels_cmd(rl, apply=False, hist_dir=d)
        finally:
            T.N_LEVELS = _old_n
        ck("⭐ `levels_cmd` 有「接得起來」那道 check",
           any("接得起來" in k for k, _c, _d in rl.checks), str(rl.checks))
        ck("⭐ 也有「唯一解夠不夠」那道",
           any("唯一解" in k for k, _c, _d in rl.checks), str(rl.checks))
        ck("⭐⭐ 而它**自己講出**千張大戶落在哪一級（⛔ 那是 E3 卡住的原因）",
           any("千張大戶" in k for k, _v in rl.infos),
           str([i for i in rl.infos if "千張" in str(i)]))
        # ⭐⭐ 而它要**分開**講「剛好 N 張」與「超過 N 張」
        #   ⛔ 只講一個 ⇒ 讀的人會把「以上」跟「超過」當同一件事，
        #     ⚠ 而實測那兩個**不是同一級**（1,000 張整在第 14 級）。
        _qz = " ".join(f"{k}{v}" for k, v in rl.infos)
        ck("⭐⭐ 而「剛好 N 張」與「超過 N 張」**分開講**"
           "（⛔ 合成一句就是把精度講掉了）",
           "剛好" in _qz and "超過" in _qz,
           str([i for i in rl.infos if "張" in str(i)]))
        ck("⛔ 不帶 `--apply` ⇒ 不寫檔",
           any("只算不寫" in f"{k}{v}" for k, v in rl.infos))
        # ⛔ 沒有 parquet ⇒ 大聲說這一層沒跑
        rl = FakeRun()
        T.levels_cmd(rl, apply=False, hist_dir=os.path.join(d, "空"))
        ck("⛔ 沒有 tdcc_hist ⇒ 大聲說**這一層沒跑**（⚠ 不是算出空表）",
           any("這一層沒跑" in k for k, _v in rl.infos), str(rl.infos))

print("\n── ④ ★ 沒有動到 repo 真的 `_tdcc_weeks_low.txt` ──")
ck("★ 逐位元沒變（含「本來就不存在」這一種）", _dig(REAL_LOW) == B4,
   f"{B4} → {_dig(REAL_LOW)}")

print(f"\n[selftest] 通過 {_n[0] - _n[1]}｜失敗 {_n[1]}")
sys.exit(1 if _n[1] else 0)
