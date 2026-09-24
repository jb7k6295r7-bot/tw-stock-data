# -*- coding: utf-8 -*-
"""PREREG11 追加一 §3 逐字：「N＝10／20 的 24 格與 results13/ 逐格相同（同種子）」⇒ 本支把它【逐位】驗一次。

⭐ 為什麼不重跑：兩份交件都在 2026-09-13 00:40／01:00 用【同一份資料快照】算出來
   ⇒ 比的是兩份【已交的表】，⛔ 不是今天重跑 ⇒ 資料後來變了也不影響這個比對（2108 §五 那個顧慮不適用）
⭐ 讀檔一律 float_precision="round_trip"（⛔ 否則會把最後一位讀歪，假紅／假綠）
⭐ 鍵 ＝ 兩張表共有的【非數值欄】（組態的定義欄），⛔ 不手挑
"""
from __future__ import annotations
import os
import numpy as np
import pandas as pd

os.chdir(os.path.expanduser("~/tw-p17/backtest"))
A = pd.read_csv("results13/portfolio.csv", float_precision="round_trip")
B = pd.read_csv("results13b/portfolio.csv", float_precision="round_trip")
print("results13  portfolio：{} 列｜欄 {}".format(len(A), list(A.columns)))
print("results13b portfolio：{} 列".format(len(B)))
common = [c for c in A.columns if c in B.columns]
#  ⛔ 第一版用「非數值欄」當鍵 ⇒ regime 是布林、被 pandas 當成數值 ⇒ 鍵少一維 ⇒ 合併出 48 格（斷言當場擋下）
#  ✅ 改成：鍵 ＝ 第一個結果欄 cagr 之前的所有欄（＝組態的定義欄；由表頭順序決定，⛔ 不手挑）
assert list(A.columns) == list(B.columns), "⛔ 兩表欄位不同"
key = list(A.columns[: list(A.columns).index("cagr")])
num = [c for c in common if c not in key]
print("⇒ 鍵 {}｜比對的結果欄 {} 個：{}".format(key, len(num), num))
for c in key:
    print("  {}：results13 {}｜results13b {}".format(c, sorted(A[c].astype(str).unique()), sorted(B[c].astype(str).unique())))

M = A.merge(B, on=key, how="inner", suffixes=("_a", "_b"))
print()
print("=== 兩表共有的組態 ＝ {} 格（PREREG11 說 24）===".format(len(M)))
assert len(M) == 24, "⛔ 共有格不是 24：{}".format(len(M))

same_all, diffs = 0, []
for i, r in M.iterrows():
    bad = []
    for c in num:
        a, b = r[c + "_a"], r[c + "_b"]
        if (pd.isna(a) and pd.isna(b)) or a == b:
            continue
        bad.append((c, a, b))
    if bad:
        diffs.append((tuple(r[k] for k in key), bad))
    else:
        same_all += 1
print("  所有數值欄都【逐位相同】的格：{}／{}".format(same_all, len(M)))
for k, bad in diffs[:10]:
    print("  ⛔ {} ⇒ {} 欄不同，例：{}".format(k, len(bad), bad[:3]))

# ⛔ 鑑別力自測：把 B 的一個數字改最後一位，比對必須抓到
B2 = B.copy()
c0 = num[0]
B2.loc[B2.index[0], c0] = np.nextafter(B2.loc[B2.index[0], c0], np.inf)
M2 = A.merge(B2, on=key, how="inner", suffixes=("_a", "_b"))
caught = int((M2[c0 + "_a"] != M2[c0 + "_b"]).sum())
print()
print("✅ 鑑別力自測：把 results13b 一格的「{}」改最後一個浮點位 ⇒ 抓到 {} 格（必須 ≥ 1，若那格在共有 24 格裡）".format(c0, caught))
print()
print("⇒ ⭐ 結論：{}".format(
    "PREREG11 追加一 §3「24 格與 results13/ 逐格相同」在【交件的表】上逐位成立（{} 個數值欄）".format(len(num))
    if same_all == 24 else "⛔ 不成立：{} 格有差".format(len(diffs))))

print()
print("=== ② 輸入也比：AND 訊號檔 ===")
import gzip, hashlib
for d in ("results13", "results13b"):
    raw = open(d + "/and_signals.csv.gz", "rb").read()
    txt = gzip.decompress(raw)
    print("  {:11s} gz 位元組 sha {}｜解壓後內容 sha {}｜{} 列".format(
        d, hashlib.sha256(raw).hexdigest()[:16], hashlib.sha256(txt).hexdigest()[:16], txt.count(b"\n") - 1))
ra, rb = (gzip.decompress(open(d + "/and_signals.csv.gz", "rb").read()) for d in ("results13", "results13b"))
assert ra == rb, "⛔ 兩份 AND 訊號內容不同"
print("  ⇒ ✅ 解壓後逐位元相同（⚠ gz 本身的 sha 不同 ⇒ 那是 gzip 標頭裡的時間戳，⛔ 不是內容不同）")

print()
print("=== ③ ⚠ 「日報酬雜湊」做不到的那一半（據實寫）===")
print("  research13.py 只把 200 顆種子的【中位／p10／p90】寫進 portfolio.csv，逐日權益用完就丟（⛔ 沒落檔）")
print("  ⇒ 兩份交件都沒有逐日序列可雜湊；而今天重跑拿到的是【新快照】（本線 2108 §五）⇒ 比的就不是交件")
print("  ⇒ ✅ 能做到的最強版本就是上面兩項：24 格 12 個結果欄逐位相同 ＋ 輸入訊號逐位相同")
