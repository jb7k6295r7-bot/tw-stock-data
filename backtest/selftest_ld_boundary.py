# -*- coding: utf-8 -*-
"""⛔⛔ ld_boundary.py 數出「邊界例外 0 次」——而 0 是最危險的結果：
   它可能是「那條路真的沒被走」，也可能是「本支的計數器根本不會響」。
⭐ 依本線交接檔〈追五七〉：一個 0 必須先證明【它是可達的】。
⇒ 本支手造兩個必定踩到那條路的案例，餵給同一個包裝函式，assert 計數器真的響。
⇒ 再用一個必定【不】踩的案例，assert 它不會誤報。
"""
from __future__ import annotations
import os
import sys
import collections
import numpy as np

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import research11 as R

CAP = R.CAP
CNT = collections.Counter()
_orig = R.cond_exit


def counting_cond_exit(o, c, k, nb, cond):
    """⭐ 與 ld_boundary.py 逐字相同的包裝（⛔ 不可改，否則就不是同一個計數器）。"""
    r = _orig(o, c, k, nb, cond)
    n = len(c)
    last = min(n - 1, k + CAP)
    if last >= nb:
        lab = "none_窗不足"
        assert r is None
    else:
        j = None
        for jj in range(k + 1, last + 1):
            if cond(jj):
                j = jj
                break
        if j is None:
            lab = "cap_抱到上限"
            assert r is not None and r[0] == last and r[2] is False
        else:
            tail = (j + 1 > n - 1)
            badw = (j + 1 >= nb)
            if not tail and not badw:
                lab = "normal_次日開盤"
                assert r[0] == j + 1 and r[2] is True
            else:
                lab = ("exc_資料尾" if tail and not badw else
                       "exc_壞根窗" if badw and not tail else "exc_兩者同時")
                assert r[0] == j and r[2] is True
    CNT[lab] += 1
    return r


def bars(n):
    o = np.arange(1.0, n + 1.0)
    c = np.arange(1.0, n + 1.0) + 0.5
    return o, c


print("=== 案例 F1：cond 只在【最後一根】成立、且 k+CAP 蓋到資料尾 ⇒ 必走「資料尾」那條 ===")
n = 30
o, c = bars(n)
k = 5
nb = n + 99                       # 沒有壞根
assert min(n - 1, k + CAP) == n - 1, "⛔ 這個案例必須讓 last ＝ n−1（否則不是資料尾情境）"
r = counting_cond_exit(o, c, k, nb, lambda j: j == n - 1)
print("  n={} k={} nb={} last={} ⇒ 引擎回 {!r}".format(n, k, nb, min(n - 1, k + CAP), r))
assert CNT["exc_資料尾"] == 1, "⛔ 計數器沒響 ⇒ ld_boundary 的 0 不可信！得到 {}".format(dict(CNT))
assert r[0] == n - 1, "⛔ 應退回 j＝n−1 收盤"
assert abs(r[1] - (c[n - 1] / o[k + 1] - 1)) < 1e-12, "⛔ 報酬應是 c[j]/o[k+1]−1（同一根收盤）"
print("  ✅ exc_資料尾 計到 1；報酬確實用 c[j]（收盤）⇒ ⭐ 計數器可達")

print()
print("=== 案例 F2：cond 只在 last 成立，而 last ＝ nb−1 ⇒ 必走「壞根窗」那條 ===")
n = 400
o, c = bars(n)
k = 10
nb = k + CAP                      # ⇒ last = min(n−1, k+CAP) = k+CAP = nb ⇒ 會被頂端 None 擋
assert min(n - 1, k + CAP) >= nb
r = counting_cond_exit(o, c, k, nb, lambda j: True)
assert r is None and CNT["none_窗不足"] == 1, "⛔ 這一組應該被頂端 last>=nb 擋成 None"
print("  ⭐ 先確認頂端那道：nb ＝ k+CAP ⇒ last ≥ nb ⇒ 回 None ✅")
nb = k + CAP + 1                  # ⇒ last = k+CAP = nb−1 ⇒ 過頂端；cond 在 last 成立 ⇒ j+1 = nb
last = min(n - 1, k + CAP)
assert last == nb - 1, "⛔ 這個案例必須讓 last ＝ nb−1"
r = counting_cond_exit(o, c, k, nb, lambda j: j == last)
print("  n={} k={} nb={} last={} ⇒ 引擎回 {!r}".format(n, k, nb, last, r))
assert CNT["exc_壞根窗"] == 1, "⛔ 壞根窗那條沒被計到：{}".format(dict(CNT))
assert r[0] == last and abs(r[1] - (c[last] / o[k + 1] - 1)) < 1e-12
print("  ✅ exc_壞根窗 計到 1 ⇒ ⭐ 兩條例外路都證明可達")

print()
print("=== 案例 F3：cond 在中間成立、離兩個邊界都很遠 ⇒ ⛔ 不可誤報成例外 ===")
n = 400
o, c = bars(n)
k = 10
nb = n + 99
r = counting_cond_exit(o, c, k, nb, lambda j: j == 50)
print("  引擎回 {!r} ⇒ 應是 (51, …, True)".format(r))
assert r[0] == 51 and r[2] is True
assert CNT["normal_次日開盤"] == 1
assert CNT["exc_資料尾"] == 1 and CNT["exc_壞根窗"] == 1, "⛔ 例外計數被誤加"
print("  ✅ 走 normal，例外計數沒有被誤加")

print()
print("=== 案例 F4：cond 從不成立 ⇒ 抱到上限，⛔ 也不可誤報 ===")
r = counting_cond_exit(o, c, k, nb, lambda j: False)
assert r[0] == min(n - 1, k + CAP) and r[2] is False and CNT["cap_抱到上限"] == 1
print("  ✅ 走 cap_抱到上限")

print()
print("=== 總計 ===")
for kk in sorted(CNT):
    print("  {:16s} {}".format(kk, CNT[kk]))
print()
print("⭐⭐ 結論：兩條例外路【都可達且被正確計數】")
print("⇒ 所以 ld_boundary.py 在研究十三上數到的 0 是【真的 0】，⛔ 不是計數器壞掉。")
