"""T1 §四 召回率：P5 換上新尺之後重量 —— 回測線執行端。

⛔⛔ 本支【不複製 t1_synth.py】——它是 2026-09-23 已交件的那一份，
    本支把它【原封不動 exec 兩次】，只在 exec 之前做兩件事：
      ① 讓 `from backtest import patterns` 拿到 ~/tw-p17 那份（含新尺）
      ② 設定 patterns.P5_CONFIRM_WINDOW（0 ＝ 舊尺／3 ＝ 型態線 2053 裁的新尺）
    ⇒ ⭐ 合成序列的產生器、雜訊校準、TRIALS、種子【一個字都沒動】
      ⇒ ⛔ 所以兩趟的差【只可能來自尺】。

⭐⭐ 錨點閘門：k=0 那一趟必須重現【已交件的】recall.csv 逐格相同。
   ⇒ 這一次錨得住，因為合成序列不碰 data/（⛔ 與 T3 那邊的快照問題無關）。
"""
from __future__ import annotations

import io
import os
import re
import sys
from contextlib import redirect_stdout

import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import backtest.patterns as P           # noqa: E402  ⭐ 先載入【本版】，t1_synth 之後 import 到的就是它

ORIG = ("/mnt/c/SynologyDrive/投資/回測用/交件/"
        "T1_偵測器召回率健檢_20260923/t1_synth.py")
OUT = os.path.expanduser("~/tw-p17/backtest/resultsp5win")
REF = ("/mnt/c/SynologyDrive/投資/回測用/交件/"
       "T1_偵測器召回率健檢_20260923/recall.csv")

os.makedirs(OUT, exist_ok=True)
src = open(ORIG, encoding="utf-8").read()
# ⭐ 只改輸出目錄（原檔寫的是一個已經不存在的 scratchpad）⇒ ⛔ 其餘一個字元都不動
src2 = re.sub(r'T1 = \(\s*"[^"]*"\s*"[^"]*"\s*\)', 'T1 = {!r}'.format(OUT), src, count=1)
assert src2 != src, "⛔ 輸出路徑沒有被替換到 ⇒ 停止（⛔ 不可以讓它寫到別的地方）"


def run(k: int) -> pd.DataFrame:
    P.P5_CONFIRM_WINDOW = k
    buf = io.StringIO()
    g = {"__name__": "__main__", "__file__": ORIG}
    with redirect_stdout(buf):
        try:
            exec(compile(src2, ORIG, "exec"), g)   # noqa: S102
        except SystemExit:
            pass
    txt = buf.getvalue()
    if "⛔⛔ 無雜訊版就抓不到" in txt:
        print(txt)
        raise SystemExit("⛔⛔ k={} 的無雜訊自我檢查沒過 ⇒ 停止".format(k))
    d = pd.read_csv(os.path.join(OUT, "recall.csv"))
    os.replace(os.path.join(OUT, "recall.csv"), os.path.join(OUT, "recall_k{}.csv".format(k)))
    print("── k={} ".format(k) + "─" * 56)
    print(txt.split("=== 一 ")[-1].rstrip())
    return d


old = run(0)
new = run(P.P5_CONFIRM_WINDOW if False else 3)

ref = pd.read_csv(REF)
m = ref.merge(old, on="pattern", suffixes=("_ref", "_k0"))
bad = m[(m["recall_top50_ref"] != m["recall_top50_k0"])
        | (m["recall_rest_ref"] != m["recall_rest_k0"])]
print()
print("=" * 70)
print("[錨點] k=0 對【已交件】recall.csv：{} / {} 格逐格相同"
      .format(len(m) - len(bad), len(m)))
if len(bad):
    print(bad.to_string(index=False))
    raise SystemExit("⛔⛔ 錨點不過 ⇒ 停止，⛔ 新尺的召回率不可引用")
print("       ✅ ⇒ ⭐ 產生器、雜訊、種子都沒被動到")

print()
print("=== ⭐⭐ P5 召回率：舊尺 vs 新尺 ===")
print()
print("  {:<10}{:>12}{:>12}{:>12}".format("尺", "市值前50", "其餘", "前50÷其餘"))
print("  " + "-" * 46)
for lab, d in (("舊尺(同日)", old), ("新尺(±3日)", new)):
    r = d[d["pattern"] == "P5_ma_cross_up"].iloc[0]
    print("  {:<10}{:>11.1%}{:>12.1%}{:>12.2f}x"
          .format(lab, r["recall_top50"], r["recall_rest"], r["ratio"]))
print()
print("=== ⛔ 確認其餘八型【沒有被動到】（型態線 2053 §五 只改 P5）===")
mm = old.merge(new, on="pattern", suffixes=("_k0", "_k3"))
for _, r in mm.iterrows():
    same = (r["recall_top50_k0"] == r["recall_top50_k3"]) and (r["recall_rest_k0"] == r["recall_rest_k3"])
    tag = "✅ 未變" if same else ("⭐ 本次要改的就是它" if r["pattern"] == "P5_ma_cross_up" else "⛔⛔ 不該變")
    print("  {:<22}{}".format(r["pattern"], tag))
    if not same and r["pattern"] != "P5_ma_cross_up":
        raise SystemExit("⛔⛔ {} 不該變卻變了 ⇒ 停止".format(r["pattern"]))
print()
print("[輸出] {}／recall_k0.csv、recall_k3.csv".format(OUT))
