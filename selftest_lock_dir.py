#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""釘住 `fetch._lock_dir`：鎖死那一天的方向不可以再把「平盤」判成「跌停」。

    python3 selftest_lock_dir.py

## 為什麼要一支專門的

2026-09-09 全庫實測：`limit=down` 但 `change` 恰為 0 的有 **50,382 列**，
佔所有 `down` 的 **47.7%**。成因是 `"down" if chg else "flat"`——
`chg` 是**字串**，`"0.0"` 是 truthy。

⚠ 這種錯**不會報錯**，只會讓下游把「整天鎖死在平盤」讀成「跌停」。
  技術面判讀會直接吃到（漲跌停是停損停利與當沖可行性的閘門）。
  ⇒ 值得一支自測釘死，而不是靠註解提醒。
"""
import sys

import fetch

CASES = [
    # (change 的原始字串, 期望)
    ("0.11", "up"), ("+1.5", "up"), ("1,234.5", "up"),
    ("-0.1", "down"), ("-2", "down"),
    ("0.0", "flat"),      # ⛔ 這一條就是 50,382 列的那一種
    ("0", "flat"),
    ("-0", "flat"),
    ("0.00", "flat"),
    ("", "flat"),         # 解析不出來 → 維持原行為
    ("X", "flat"),
    (None, "flat"),
]


def main():
    bad = 0
    for raw, want in CASES:
        got = fetch._lock_dir(raw)
        mark = "ok" if got == want else "✗"
        if got != want:
            bad += 1
        print(f"  {mark} change={raw!r:10s} → {got:5s}（期望 {want}）")
    print("全過" if not bad else f"⛔ {bad} 項沒過")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
