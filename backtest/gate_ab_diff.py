# -*- coding: utf-8 -*-
"""⚠ 裁定線 seq85 §一③ 給的 (甲)(乙) 二選一 —— 本支發現它們【不等價】。

(乙) 在舊快照上依名稱排除 -DR ⇒ 2,124 檔
(甲) 同步到 main              ⇒ 2,126 檔
⇒ ⭐ 差 2 檔，而差的不是 DR ⇒ 本支把它找出來，並查清是【哪一欄】變了。

⛔ 本支第一版只比了 kind，印出「舊快照裡有（但 kind=stock）」這種自相矛盾的話
   ⇒ ⭐ 因為母體條件是 kind ∧ market 兩欄 ⇒ 只報一欄會得到矛盾的結論 ⇒ 本版兩欄都報。
"""
from __future__ import annotations
import os
import subprocess
import io
import pandas as pd

ROOT = os.path.expanduser("~/tw-p17")
os.chdir(ROOT)
P = "data/meta/stocks.csv"


def uni_from(txt: str) -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(txt), dtype=str)
    return df[(df["kind"] == "stock") & df["market"].isin(["twse", "tpex"])].reset_index(drop=True)


branch = io.open(P, encoding="utf-8").read()
main = subprocess.run(["git", "show", "origin/main:" + P], capture_output=True, text=True).stdout
nm_b = pd.read_csv(io.StringIO(branch), dtype=str).set_index("stock_id")
nm_m = pd.read_csv(io.StringIO(main), dtype=str).set_index("stock_id")

ub, um = uni_from(branch), uni_from(main)
b_nodr = ub[~ub["name"].str.contains("-DR", na=False)]
print("=== ① 三個母體 ===")
print("  (原) 分支快照 kind=='stock'      {:,} 檔（含 7 檔 -DR）".format(len(ub)))
print("  (乙) 分支快照 ＋ 排除 -DR        {:,} 檔".format(len(b_nodr)))
print("  (甲) origin/main kind=='stock'   {:,} 檔（-DR 0 檔）".format(len(um)))
print("  ⇒ ⚠ (甲) − (乙) ＝ {:+,} 檔 ⇒ ⛔ 兩個選項【不等價】".format(len(um) - len(b_nodr)))

sb, sm = set(b_nodr["stock_id"]), set(um["stock_id"])
only_m, only_b = sorted(sm - sb), sorted(sb - sm)
print()
print("=== ② 差在哪幾檔（⭐ kind 與 market 兩欄都報）===")


def show(s, side):
    inb = nm_b.loc[s] if s in nm_b.index else None
    inm = nm_m.loc[s] if s in nm_m.index else None
    f = lambda r: "缺" if r is None else "kind={} market={} last_seen={}".format(
        r["kind"], r["market"], str(r["last_seen"])[:10])
    nm = (inm if inm is not None else inb)["name"]
    print("    {}  {}".format(s, nm))
    print("       舊快照(乙)：{}".format(f(inb)))
    print("       main  (甲)：{}".format(f(inm)))
    if inb is not None and inm is not None:
        ch = [c for c in ("kind", "market") if inb[c] != inm[c]]
        print("       ⇒ ⭐ 變的欄：{}".format("、".join(ch) if ch else "（兩欄都沒變 ⇒ 要另查）"))


print("  只在 (甲) 有的 {} 檔：".format(len(only_m)))
for s in only_m:
    show(s, "m")
print("  只在 (乙) 有的 {} 檔：{}".format(len(only_b), "" if only_b else "—"))
for s in only_b:
    show(s, "b")

print()
print("=== ③ ⚠ 那幾檔裡有沒有【已被裁定排除】的類 ===")
for s in only_m:
    nm = nm_m.loc[s, "name"]
    flags = []
    if "創" in str(nm):
        flags.append("⚠ 創新板（裁定線 1611 §二 已裁：剔除）")
    if "-DR" in str(nm):
        flags.append("⚠ 存託憑證")
    print("    {} {} ⇒ {}".format(s, nm, "／".join(flags) if flags else "（無旗標）"))

print()
print("=== ④ ⭐ 要交代的三句 ===")
print("  ⇒ (乙) 只修掉 DR 那一項，⛔ 修不掉「舊快照的 market 欄還沒更新」那一項")
print("  ⇒ (甲) 兩項都修，⛔ 但 ① 交件無法逐位重現（本線 2108 §五 已量）")
print("     ② ⚠ 而它會把【創新板】那一檔帶進母體 —— 而裁定線 1611 §二 裁的是剔除")
print("     ⇒ ⭐ 所以 (甲) 不是「把資料弄新就好」，它還需要一道創新板排除")
print("  ⇒ ⏳ 二選一是裁定線的格子；本線只報【它們不等價】與【(甲) 會帶進什麼】")

assert len(um) - len(b_nodr) == len(only_m) - len(only_b), "⛔ 檔數差與名單差對不上"
print()
print("✅ 斷言：檔數差 {:+} ＝ 名單差（只在甲 {} − 只在乙 {}）".format(
    len(um) - len(b_nodr), len(only_m), len(only_b)))
