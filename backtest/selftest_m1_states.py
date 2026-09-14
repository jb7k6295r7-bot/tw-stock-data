"""m1_states 自測：① 雜訊加大 ⇒ 去抖後 n 不可往上走（K線分析 09-14 1935 1-2）；② 合成序列的去抖結果逐格比對；③ 0050 上的 n 與 09-14 信件數字一致。
每條先證明會紅（突變見檔尾註解）再證明會綠。rc != 0 或輸出含 ✗ 才算紅。"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest import m1_states as M  # noqa: E402

FAIL = 0


def check(cond, msg):
    global FAIL
    print(("  ✓ " if cond else "  ✗ ") + msg)
    if not cond:
        FAIL += 1


def t_synthetic():
    idx = pd.bdate_range("2020-01-01", periods=300)
    s = pd.Series(["上"] * 100 + ["下"] * 3 + ["上"] * 100 + ["下"] * 50 + ["上"] * 47, index=idx, dtype=object)
    seg = M.segments(s)
    check(list(seg["len"]) == [100, 3, 100, 50, 47], f"segments 長度 {list(seg['len'])}")
    db = M.debounce(s, 20)
    check(list(db["state"]) == ["上", "下", "上"] and list(db["len"]) == [203, 50, 47], f"去抖：3 日抖動併入前段再合併 ⇒ {list(zip(db['state'], db['len']))}")
    # 第一段 < K：沒有前一段 ⇒ 保留
    s2 = pd.Series(["下"] * 5 + ["上"] * 100, index=idx[:105], dtype=object)
    db2 = M.debounce(s2, 20)
    check(list(db2["state"]) == ["下", "上"], f"第一段 < K 保留 ⇒ {list(db2['state'])}")
    # 連續兩個短段：都併入同一個前段
    s3 = pd.Series(["上"] * 50 + ["下"] * 5 + ["上"] * 5 + ["下"] * 50, index=idx[:110], dtype=object)
    db3 = M.debounce(s3, 20)
    check(list(db3["state"]) == ["上", "下"] and list(db3["len"]) == [60, 50], f"兩個短段都併入前段 ⇒ {list(zip(db3['state'], db3['len']))}")


def t_noise_monotone():
    """把雜訊加大：隨機翻轉單日狀態；去抖後 n 不可以比乾淨版大。"""
    idx = pd.bdate_range("2015-01-01", periods=2000)
    rng = np.random.default_rng(1)
    base = []
    st = "上"
    while len(base) < 2000:
        base += [st] * int(rng.integers(25, 200)); st = "下" if st == "上" else "上"
    clean = pd.Series(base[:2000], index=idx, dtype=object)
    n0 = len(M.debounce(clean, 20)) - 1
    worst = 0
    for p in (0.01, 0.03, 0.05, 0.10):
        for seed in range(5):
            r = np.random.default_rng(seed)
            noisy = clean.copy()
            flip = r.random(2000) < p
            noisy[flip] = noisy[flip].map({"上": "下", "下": "上"})
            n1 = len(M.debounce(noisy, 20)) - 1
            raw0 = len(M.segments(clean)) - 1; raw1 = len(M.segments(noisy)) - 1
            worst = max(worst, n1 - n0)
            check(raw1 >= raw0, f"p={p} seed={seed}: 素切換 {raw0} → {raw1}（雜訊確實變多）")
            check(n1 <= n0, f"p={p} seed={seed}: 去抖後 n {n0} → {n1}（不可往上走）")
    print(f"  雜訊加大後 n 最大變化 {worst:+d}")


def t_0050():
    c = M.load_series(None)
    t = M.n_table(c, 20).set_index("signal")
    # 09-14 1914／2021 信：本線復算 a 9／b 16／ab 12／c 28／d 47（策略線 9/17/13/30/50，差在細節定義）
    for key, exp in (("a", 9), ("b", 16), ("ab", 12), ("c", 28), ("d", 47)):
        check(int(t.loc[key, "n"]) == exp, f"0050 {key} 去抖後 n＝{int(t.loc[key, 'n'])}（信裡 {exp}）")
    check(int(t.loc["a", "raw_switches"]) == 61, f"0050 a 素切換 {int(t.loc['a', 'raw_switches'])}（信裡 61）")
    check(t.loc["a", "judge"].startswith("還沒測") and t.loc["c", "judge"] == "可跑", "a 還沒測、c 可跑")
    # 狀態序列本身：a 在 240 根之前 NaN；d 月初可得（第一個有值的月是第三個月）
    sig = M.signals(c)
    check(sig["a"].iloc[:239].isna().all() and sig["a"].iloc[239:].notna().all(), "a 前 239 根 NaN、之後全有值")
    check(sig["d"].dropna().index[0].to_period("M") == c.index[0].to_period("M") + 2, "d 第一個有值的月＝起算後第三個月")


if __name__ == "__main__":
    print("[m1_states] 合成序列"); t_synthetic()
    print("[m1_states] 雜訊單調性"); t_noise_monotone()
    print("[m1_states] 0050 對帳"); t_0050()
    print("結果：", "全綠" if FAIL == 0 else f"✗ {FAIL} 條")
    sys.exit(1 if FAIL else 0)

# 突變（每次前後 rm -rf backtest/__pycache__）：
#  M1 debounce 改成「短段丟掉不併入」（1835 那個定義）⇒ 合成第 2 條紅（200 vs 203）、雜訊單調性紅（n 往上走）
#  M2 `ln < k` 改 `ln <= k`         ⇒ 合成第 4 條可能仍綠；0050 對帳紅
#  M3 c 的分位改含當日               ⇒ 0050 c 對帳紅
