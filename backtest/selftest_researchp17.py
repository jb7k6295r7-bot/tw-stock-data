"""PREREGP17 自測：§八 8-1 的兩半（17 格手算 fixture ＋ 原始碼突變測試）＋ 登錄常數守門。

    python3 -m backtest.selftest_researchp17

⛔ 登錄 §八 8-1 逐字：
  「✅ 至少 8 格手算 … ⇒ 逐位元對
   ⛔⛔ 而依〈一百一十三〉：fixture 必須先被證明【分得出來】——
     ⇒ ✅ 對程式做 ≥ 5 種突變（σ 的窗偏移一天／ddof 改 0／w 的分母寫錯／
        再平衡日錯一天／成本漏算一邊）⇒ ⭐ 每一種都必須讓 fixture 變紅
     ⇒ ⛔ 若某一種突變 fixture 仍是綠的 ⇒ ⭐ 那一格要補，⛔ 不可跳過
   ⛔ 原始碼突變測試：每次突變前後都清 __pycache__，未套用一律 exit 9」

⭐ 做法：在【原檔】上做字串取代 ⇒ 清 __pycache__ ⇒ 用【子行程】跑 fixture ⇒ 還原。
  ⚠ 用子行程而不是 importlib.reload：本檔在同一個直譯器裡已經 import 過 researchp17，
    reload 有快取與相依殘留的風險 ⇒ ⭐ 子行程是乾淨的。
  ⛔⛔ 還原之後要用 sha256 驗原檔沒被改壞 —— ⛔ 否則自測本身會污染交件程式。
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "researchp17.py")
PYC = os.path.join(HERE, "__pycache__")

_fail = 0


def check(ok: bool, msg: str) -> None:
    global _fail
    print(("  ✅ " if ok else "  ⛔ ") + msg)
    if not ok:
        _fail += 1


# (代號, 說明, 原字串, 換成)
MUTANTS = [
    ("M1", "σ 的窗偏移一天",
     "np.asarray(series, float)[t - lb - 1:t]",
     "np.asarray(series, float)[t - lb:t + 1]"),
    ("M2", "ddof 改 0",
     "DDOF = 1                        # §1-2：日報酬標準差 ddof=1",
     "DDOF = 0                        # §1-2：日報酬標準差 ddof=1"),
    ("M3", "w_eq 的分母少加一項",
     "    d = se + sb",
     "    d = se"),
    ("M4", "再平衡日錯一天",
     "        if rebal[t]:",
     "        if rebal[t - 1]:"),
    ("M5", "成本漏算一邊（只有買進付）",
     "            c = tr * cost",
     "            c = tr * cost if tgt > ve else 0.0"),
    ("M6", "w_tv 漏掉 min(1,·) 的截斷",
     "    return float(np.clip(min(1.0, sb / se), 0.0, 1.0))",
     "    return float(sb / se)"),
    ("M7", "compose 期初配置寫死 0.5",
     "    ve, vb = w_first, 1.0 - w_first",
     "    ve, vb = 0.5, 0.5  #"),
    ("M8", "ρ 的窗偏移一天",
     "    ra = _ret(np.asarray(a, float)[t - lb - 1:t])",
     "    ra = _ret(np.asarray(a, float)[t - lb:t + 1])"),
]

RUN_FIXTURE = (
    "import sys; sys.path.insert(0, %r); "
    "from backtest import researchp17 as P; P.fixture_check(); print('GREEN')"
)


def _clear_pycache() -> None:
    if os.path.isdir(PYC):
        shutil.rmtree(PYC)


def _run_fixture_subprocess() -> tuple[bool, str]:
    """回傳 (fixture 是否全綠, 說明)。⭐ 崩潰也算被抓到，⛔ 但與「值不同」分開報。"""
    root = os.path.dirname(HERE)
    p = subprocess.run([sys.executable, "-c", RUN_FIXTURE % root],
                       capture_output=True, text=True, cwd=root, timeout=300)
    if p.returncode == 0 and "GREEN" in p.stdout:
        return True, "綠"
    err = (p.stderr or "") + (p.stdout or "")
    # ⭐ fixture_check 用 SystemExit 報「值不同」⇒ 那是【fixture 抓到了】
    #   ⛔ 其他例外才是【崩潰】—— 崩潰代表那個突變連跑都跑不完，fixture 的鑑別力沒被用到。
    if "⛔⛔ 否證：§八 8-1 手算 fixture 不過" in err:
        bad = [l.strip() for l in err.splitlines() if l.strip().startswith("格") or "：得 " in l]
        return False, "值不同：{}".format(bad[0][:52] if bad else "（見輸出）")
    last = [l for l in err.strip().splitlines() if l.strip()]
    return False, "崩潰：{}".format(last[-1][:52] if last else "（無輸出）")


def main() -> int:
    print("=== PREREGP17 自測 ===")
    orig = open(SRC, encoding="utf-8").read()
    orig_sha = hashlib.sha256(orig.encode("utf-8")).hexdigest()

    # ── ① 登錄寫死的常數（⛔ 改了就不是這一份登錄了）──
    from . import researchp17 as P17
    print("\n① 登錄寫死的常數")
    check(P17.LOOKBACK == 120, "§1-2 L ＝ 120")
    check(P17.DDOF == 1, "§1-2 ddof ＝ 1")
    check(P17.MOVE_COST == 0.00585, "§1-4 換手成本 ＝ 0.585%")
    check(P17.BURN_W == 0.50 and P17.W_FIX == 0.50, "§1-4／§1-3 burn-in 與 W_fix ＝ 0.50")
    check(P17.R_SHUF == 30, "§1-3 重排次數 ＝ 30")
    check(P17.REPS == 200, "§1-3 種子數 ＝ 200")
    check(P17.SEED_SHUF == 108000, "§1-3 重排流 ＝ 108000+r（⛔ 獨立於選股流 102000+r）")
    check(P17.BENCH_CAGR == 0.24020209886370614, "§二 基準年化【未捨入值】")
    check(P17.BENCH_MDD_ABS == 0.33957005276110119, "§二 基準回落【未捨入值】")
    check(P17.BISECT_TOL == 1e-12, "§1-2 二分搜尋收斂門檻 ＝ 1e−12")

    # ── ② §八 8-1 前半：手算 fixture ──
    print("\n② §八 8-1 手算 fixture")
    rows = P17.fixture_check()
    check(len(rows) >= 8, "格數 {} ≥ 8（登錄下限）".format(len(rows)))
    check(all(r["判"].startswith("✅") for r in rows), "{} 格全過".format(len(rows)))
    n_bit = sum(1 for r in rows if r["判"] == "✅逐位元")
    print("     （其中 {} 格是【逐位元】；其餘因手算與實作的運算順序不同而用 ≤4ulp，"
          "⏳ 已於 20260923-1850 §三 請裁）".format(n_bit))

    # ── ③ ⭐⭐ R_rp 恆等於 R_eq（本線 1850 §一 的守門）──
    print("\n③ ⭐ R_rp 與 R_eq 的關係（⛔ 這是【事實】不是選擇）")
    import numpy as np
    rng = np.random.default_rng(20260923)
    worst = 0.0
    for _ in range(2000):
        se, sb, rr = rng.uniform(1e-4, .2), rng.uniform(1e-4, .2), rng.uniform(-.999, .999)
        worst = max(worst, abs(P17.w_rp(se, sb, rr) - P17.w_eq(se, sb)))
    check(worst <= P17.BISECT_TOL * 10,
          "2,000 組隨機 (σ_E,σ_B,ρ)：|w_rp − w_eq| 最大 {:.3e} ⇒ ⭐ ρ 是惰性輸入".format(worst))

    # ── ④ 再平衡日與登錄 §四⑦ 事前算的值 ──
    print("\n④ 再平衡日（§1-2 每月第一個交易日）")
    from . import data as D
    from . import researchp12 as P12
    cal = D.load_calendar()
    w0, w1 = P12.win_bounds(cal, P17.WIN)
    rb = P17.rebal_days(cal, w0, w1)
    check(str(cal[w0 + int(rb[0])].date()) == "2017-04-05",
          "第一個再平衡日 ＝ {}（⭐ 登錄 §四⑦ 事前算 2017-04-05）".format(cal[w0 + int(rb[0])].date()))
    check(len(rb) == len(set(int(t) for t in rb)), "{} 個再平衡日無重複".format(len(rb)))
    check(all(0 < int(t) <= w1 - w0 for t in rb), "全部落在窗內（⭐ 窗內相對索引）")

    # ── ⑤ §八 8-1 後半：原始碼突變測試 ──
    print("\n⑤ ⭐⭐ 原始碼突變測試（⛔ 每一種都必須讓 fixture 變紅）")
    _clear_pycache()
    base_green, _ = _run_fixture_subprocess()
    check(base_green, "⭐ 先確認【未突變】的原版是綠的（⛔ 否則整個突變測試沒有意義）")
    if not base_green:
        return 1

    survivors = []
    try:
        for tag, desc, old, new in MUTANTS:
            if orig.count(old) != 1:
                print("  ⛔ {} {}：突變字串命中 {} 次（要恰好 1 次）⇒ exit 9"
                      .format(tag, desc, orig.count(old)))
                return 9
            with open(SRC, "w", encoding="utf-8") as fh:
                fh.write(orig.replace(old, new, 1))
            _clear_pycache()
            green, how = _run_fixture_subprocess()
            _clear_pycache()
            check(not green, "{} {:<26} ⇒ {}".format(tag, desc, "⛔ 仍然全綠" if green else "變紅（{}）".format(how)))
            if green:
                survivors.append(tag)
    finally:
        with open(SRC, "w", encoding="utf-8") as fh:
            fh.write(orig)
        _clear_pycache()

    back = hashlib.sha256(open(SRC, encoding="utf-8").read().encode("utf-8")).hexdigest()
    check(back == orig_sha, "⭐⭐ 突變後原檔【逐位元還原】（sha256 {}）".format(back[:16]))
    check(not survivors, "⭐ {} 種突變全部被 fixture 抓到".format(len(MUTANTS)))

    print("\n=== {} ===".format("✅ 全部通過" if _fail == 0 else "⛔ 有 {} 項不通過".format(_fail)))
    return 0 if _fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
