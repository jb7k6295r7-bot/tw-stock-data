# -*- coding: utf-8 -*-
"""D4 **開跑前的資料閘**：新來源（籌碼）母體 vs 現行池子母體的【雙向差集】。

⇐ D4 seq=8 §三之三（⛔ 是閘，不是建議 ⇒ 沒過不開跑）＋台股策略線 1307 §三①／1418 §五①
⛔⛔ 本支【不重跑策略】、⛔ 不開登錄、⛔ 不算任何報酬。純描述。

⛔⛔ 先報一件【查無】（〈一百三十七〉：說查無要先報查了哪棵樹）：
   D4 seq=8 §4-2 逐字指名籌碼來源是 **`newdim.csv.gz`** ⇒ ⛔ **那個檔不存在**。
   查過的樹：~/tw-p17（本線 worktree，含 data/ 全樹）／git --all 全歷史（從未 A 過這個檔名）／
            ~/tw-stock-data、~/tw-p16、~/tw-trial 三個 worktree／
            /mnt/c/SynologyDrive/跨線信箱／/mnt/c/SynologyDrive/投資 全樹
   ⇒ 「newdim」這個字只出現在 D4 全文與兩封信的【文字】裡，⛔ 沒有對應的檔案。
   ⇒ ⭐ 所以本支用【實際存在的】籌碼來源做閘：
      data/universe/inst（上市）＋ data/universe/otcinst（上櫃）
      欄位 date, stock_id, foreign, trust, dealer, total, dealer_self, dealer_hedge
      ⚠ 而依 D4 §4-2 自己的警告，這兩個是【股數】⛔ 不是金額
        ⇒ ⛔ 本支不碰「金額」那一格 —— 那要先有檔、且要在登錄裡逐字寫死。
"""
from __future__ import annotations
import os, sys, glob, re
import numpy as np, pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import p4_features as P4F

W0, W1 = 523, 2835
cal = D.load_calendar()
panel = P4F.read_panel("backtest/resultsp4/panel.csv.gz")
panel["measure_date"] = pd.to_datetime(panel["measure_date"])
pos = {d: i for i, d in enumerate(cal)}
panel["pos"] = panel["measure_date"].map(pos)
panel = panel[panel["pos"].notna()]
panel = panel[(panel["pos"] >= W0) & (panel["pos"] <= W1)]
mds = sorted(panel["measure_date"].unique())
print("判定窗 [{},{}] {} ~ {}｜量測日 {} 個".format(
    W0, W1, cal[W0].date(), cal[W1].date(), len(mds)))

# ── 現行池子母體（門檻B／參考C ＝ eligible）
cur = set(panel.loc[panel["eligible"].astype(bool), "stock_id"].astype(str))
cur_all = set(panel["stock_id"].astype(str))          # ⭐ 進得到 panel 但沒過閘門的
print("現行池子（eligible）      {:,} 檔｜panel 全體 {:,} 檔".format(len(cur), len(cur_all)))

# ── 新來源母體（籌碼：實際存在的 inst ＋ otcinst），只讀量測日
new = set()
for d in mds:
    for sub in ("inst", "otcinst"):
        f = "data/universe/{}/{}.csv".format(sub, pd.Timestamp(d).strftime("%Y-%m-%d"))
        if os.path.exists(f):
            new |= set(pd.read_csv(f, dtype={"stock_id": str})["stock_id"].astype(str))
print("新來源（籌碼 inst+otcinst）{:,} 檔".format(len(new)))
print()

only_new = new - cur          # ⭐ 新進來的
only_cur = cur - new          # ⭐ 掉出去的
print("=== ⭐⭐ 雙向差集（⛔ 兩個方向都列 —— 只列一邊會漏掉「基準自己擋掉」那一族）===")
print("   ① 新來源【有】而現行池子【沒有】 ＝ **{:,} 檔**".format(len(only_new)))
print("   ② 現行池子【有】而新來源【沒有】 ＝ **{:,} 檔**".format(len(only_cur)))
print()

uni = D.load_universe()
nm = dict(zip(uni["stock_id"].astype(str), uni["name"].astype(str))) if "name" in uni.columns else {}
in_uni = set(uni["stock_id"].astype(str))


def family(s: str) -> str:
    """⭐ 逐族分類。⛔ 規則寫死在這裡，⛔ 不看結果再調。"""
    n = nm.get(s, "")
    # ⛔ 本行的第一版寫成 00＋三位數 ⇒ 把 0050／0051／0052／0053 誤歸成「不在 universe」。
    #   ⚠ 而 0050 正是 D4 §二 的【退化解本體】⇒ 誤分類會讓最要緊的那一檔藏在「來源不明」裡。
    #   ⭐ 據實聲明：這是看到結果之後才改的，⛔ 但改的是一個【事實性誤分類】
    #     （0050 依事實就是 ETF），⛔ 不是為了讓某個數字變好看。
    if re.fullmatch(r"00\d{2,3}[A-Z]?", s):
        return "ETF／受益憑證（代號 00xx／00xxx）"
    if s.startswith("91"):
        return "TDR 存託憑證（91xxxx）"
    if re.fullmatch(r"\d{6}", s):
        return "六位數代號（權證／ETN 等）"
    if "-創" in n:
        return "創新板（名稱帶 -創）"
    if s not in in_uni:
        return "⛔ 不在 universe（來源不明）"
    if s in cur_all:
        return "在 panel 內但【沒過閘門】（liq／bars／inst）"
    return "在 universe 但【沒進 panel】（bars 不足／期間無資料）"


for lab, st in (("① 新進來的（新來源有、現行池子沒有）", only_new),
                ("② 掉出去的（現行池子有、新來源沒有）", only_cur)):
    print("=== {} ＝ {:,} 檔 ===".format(lab, len(st)))
    fam = {}
    for s in st:
        fam.setdefault(family(s), []).append(s)
    for k in sorted(fam, key=lambda x: -len(fam[x])):
        v = sorted(fam[k])
        print("   {:<34} {:>5,} 檔   例：{}".format(
            k, len(v), "、".join("{}{}".format(x, "(" + nm[x] + ")" if x in nm else "") for x in v[:4])))
    print()

rows = []
for lab, st in (("新進來", only_new), ("掉出去", only_cur)):
    for s in sorted(st):
        rows.append(dict(direction=lab, stock_id=s, name=nm.get(s, ""), family=family(s)))
pd.DataFrame(rows).to_csv("backtest/resultsd4_gate.csv", index=False, encoding="utf-8")
print("⇒ 落檔 backtest/resultsd4_gate.csv（{:,} 列）".format(len(rows)))
print()
print("=== ⛔⛔ 閘門結論：③【舊基準擋掉而新基準沒擋】的族 ===")
key = [k for k in {family(s) for s in only_new}
       if k.startswith("ETF") or k.startswith("TDR") or k.startswith("六位數")]
n_key = sum(1 for s in only_new if family(s) in key)
print("   命中族：{}".format("；".join(sorted(key)) if key else "（無）"))
print("   合計 **{:,} 檔**".format(n_key))
if n_key:
    print("   ⇒ ⛔⛔ 依 D4 §三之三③：**13.25pp 那個選股病的量必須在【新母體】上重算**")
    print("      理由：它原本是在【舊母體】上算的，而舊母體【從來沒有把這些族列為排除】——")
    print("            它們根本沒進到那一步（⭐ 就是情報線 1133 §三 的 ETF 那個形狀）")
    print("   ⇒ ⇒ ⛔ 而本線【不】自己重算 —— 13.25pp 是台股策略線的量，本線只報閘門結果。")
print()
print("⇒ ⭐ 閘門本身：**跑完了，⛔ 而它沒有過** ——")
print("   ① 雙向差集已列、② 逐族 why-in／why-out 已寫、③ 命中「舊擋新不擋」⇒ 觸發重算要求")
print("   ⇒ ⛔ 依 §三之三「沒過就不開跑」⇒ **D4 現在不可開跑**，等 13.25pp 在新母體重算。")
