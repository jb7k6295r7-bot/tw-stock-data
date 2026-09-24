# -*- coding: utf-8 -*-
"""D4 §2-3-2：套剔除規則 ⇒ 交【剔除後】母體檔數 ＋ 逐族剔除數。

⇐ 台股策略線 20260924-1518 §五②（⛔ 這一步之前不要算 13.25pp）
規則（seq=10 §2-3-1b 逐字）：**候選池的標的類別維持與現行池子相同 ＝【普通股】（上市＋上櫃）**

⛔⛔ 而本線在套的時候撞到一個【留白】⇒ 依角色邊界：留白 ＋ 寫信請裁，⛔ 本線不自己選：
   §2-3-1b 的規則寫的是「標的類別 ＝ 普通股」
   ⛔ 而 §二 的行文又把【創新板】與 TDR 並列，說「現行池子裡沒有這一類 ⇒ 一律不進」
   ⇒ ⇒ ⚠⚠ 兩句不一致：**創新板股票【就是普通股】**，只是掛在不同的板
     ・依「標的類別＝普通股」⇒ 創新板【應該留】
     ・依 §二 的行文　　　　⇒ 創新板【應該剔】
   ⇒ ⭐ 所以本支【兩種讀法都算、都報】，⛔ 本線不挑一個當答案。
"""
from __future__ import annotations
import os, sys, re
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D

g = pd.read_csv("backtest/resultsd4_gate.csv", dtype=str)
uni = D.load_universe(); ids = set(uni["stock_id"].astype(str))
nm = dict(zip(uni["stock_id"].astype(str), uni["name"].astype(str))) if "name" in uni.columns else {}

NEW_TOTAL, CUR_POOL = 2550, 1586      # ⇐ 本線 1422 的閘門結果
new_in = g[g["direction"] == "新進來"]["stock_id"].tolist()


def refine(s: str, fam: str) -> str:
    """把「⛔ 不在 universe」那 48 檔拆成本輪查出來的兩類（⭐ 證據見 §一）。"""
    if "不在 universe" not in fam:
        return fam
    m = re.fullmatch(r"(\d{4})([A-Z]\d?)", s)
    if m and m.group(1) in ids:
        return "特別股（母代號在現行池子裡）"
    if re.fullmatch(r"0\d{4}[A-Z]?", s):
        return "受益證券／REIT（0 開頭號段）"
    return "⛔ 仍未能歸類"


g["fam2"] = [refine(s, f) for s, f in zip(g["stock_id"], g["family"])]
fam_n = g[g["direction"] == "新進來"]["fam2"].value_counts()

# ⭐ 非普通股（兩種讀法都剔的）
NOT_COMMON = ["ETF／受益憑證（代號 00xx／00xxx）", "六位數代號（權證／ETN 等）",
              "TDR 存託憑證（91xxxx）", "特別股（母代號在現行池子裡）",
              "受益證券／REIT（0 開頭號段）"]
INNOV = "創新板（名稱帶 -創）"
COMMON_KEEP = "在 panel 內但【沒過閘門】（liq／bars／inst）"

print("=== ⭐ 新來源逐族（本線 1422 的 964 檔，⭐ 其中 48 檔已拆開）===")
for k, v in fam_n.items():
    tag = "⛔ 非普通股 ⇒ 剔" if k in NOT_COMMON else ("⚠ 留白（見檔頭）" if k == INNOV else "✅ 普通股 ⇒ 留")
    print("   {:<34} {:>5,} 檔   {}".format(k, v, tag))
print()

n_not_common = int(sum(fam_n.get(k, 0) for k in NOT_COMMON))
n_innov = int(fam_n.get(INNOV, 0))
n_keep_new = int(fam_n.get(COMMON_KEEP, 0))
print("=== ⭐⭐ 剔除後的候選池母體（⛔ 兩種讀法都報，本線不挑）===")
print("   新來源原始                        {:>6,} 檔".format(NEW_TOTAL))
print("   ⛔ 剔：非普通股（ETF/權證/TDR/特別股/受益證券）  −{:>5,} 檔".format(n_not_common))
print()
for lab, drop_innov in (("(甲) 依『標的類別＝普通股』⇒ **創新板留**", False),
                        ("(乙) 依 §二 行文『現行池子沒這一類』⇒ **創新板剔**", True)):
    tot = NEW_TOTAL - n_not_common - (n_innov if drop_innov else 0)
    print("   {}".format(lab))
    print("      ⛔ 另剔創新板 {:>3} 檔".format(n_innov) if drop_innov else "      ✅ 創新板 {} 檔留在池子裡".format(n_innov))
    print("      ⇒ **剔除後候選池 ＝ {:,} 檔**".format(tot))
    print("        其中：現行池子 {:,} ＋ 新進來的普通股 {:,}{}".format(
        CUR_POOL, n_keep_new, " ＋ 創新板 {}".format(n_innov) if not drop_innov else ""))
    print()
print("⇒ ⭐ 兩種讀法只差 **{} 檔**（{:.2f}%）⇒ ⛔ 而差別小【不是】不用裁的理由：".format(
    n_innov, n_innov / (NEW_TOTAL - n_not_common) * 100))
print("   ⭐ 創新板的流動性與一般上市櫃不同 ⇒ 它進不進池子會影響【選股病】那個量本身。")
print()
print("=== ⭐ 而這才是 D4 真正換到的東西（⛔ 本線只描述，不評價）===")
print("   換來源之後【真正新增的普通股】＝ **{:,} 檔**".format(n_keep_new))
print("   ⇒ 它們全部是【在 panel 內但沒過 liq／bars／inst 閘門】的普通股")
print("   ⇒ ⇒ ⭐⭐ 也就是說：扣掉非普通股之後，『換來源』的實質 ＝")
print("        **把現行池子的流動性／法人／K棒數閘門換掉**，⛔ 不是換到一批新標的")
print("   ⚠ 而那 {:,} 檔【正是被現行閘門明示排除的那一族】".format(n_keep_new))
print("   ⇒ ⏳ 這一句對 D4 的宣稱有沒有影響，⛔ 是台股策略線的格子，本線只報數。")

g.to_csv("backtest/resultsd4_gate.csv", index=False, encoding="utf-8")
print()
print("⇒ 落檔 backtest/resultsd4_gate.csv（已加 fam2 欄）")
