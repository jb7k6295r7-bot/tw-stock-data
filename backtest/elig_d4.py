# -*- coding: utf-8 -*-
"""D4 新旗標 elig_d4（⇐ D4 seq=17 §4-2 逐字）＋ 必報欄① 的兩個數。

elig_d4(股,月) ＝ (a) 在 2,039 檔母體內（面板證券集合剔除 ETF/六位數/特別股/TDR/受益證券）
               ∧ (b) 該股-月有可成交的價格資料（＝面板判斷「這個月存不存在」的同一個欄）
⛔ liq_ok、inst_ok 一律不進；⛔ bars_ok 不當閘門（移到訊號層 ⇒ 依定義不成立）
"""
from __future__ import annotations
import os, sys, re
import numpy as np, pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D, p4_features as P4F, researchp12 as P12

cal = D.load_calendar()
panel = P4F.read_panel("backtest/resultsp4/panel.csv.gz")
panel["measure_date"] = pd.to_datetime(panel["measure_date"])
_pos = {d: i for i, d in enumerate(cal)}
panel["pos_"] = panel["measure_date"].map(_pos)
p = panel[panel["measure_date"] >= pd.Timestamp(P12.START)].copy()
print("面板（≥{}）{:,} 股-月／{:,} 檔".format(P12.START, len(p), p["stock_id"].nunique()))

uni = D.load_universe()
ind_p = "data/meta/industry.csv"
ind = pd.read_csv(ind_p, dtype=str) if os.path.exists(ind_p) else None
tdr = set(ind.loc[ind["industry_code"] == "91", "stock_id"]) if ind is not None else set()
print("industry_code==91（TDR）全庫 {} 檔".format(len(tdr)))

def not_common(s: str) -> bool:
    """(a) 的剔除類（⭐ 與本線 1511／d4_gate 同一套判準）。"""
    if s in tdr or s.startswith("91"):
        return True
    if re.fullmatch(r"00\d{2,3}[A-Z]?", s):        # ETF／受益憑證
        return True
    if re.fullmatch(r"0\d{4}[A-Z]?", s):           # 受益證券／REIT
        return True
    if re.fullmatch(r"\d{6}", s):                  # 權證／ETN
        return True
    if re.fullmatch(r"\d{4}[A-Z]\d?", s):          # 特別股
        return True
    return False

# ⛔⛔ (a) 的母體【不是】面板證券集合 —— 那樣會多 29 檔（第一版的錯，當場抓到）：
#   18 檔創新板（裁定線 1611 §二 已裁剔除）＋ 5 檔 TDR ＋ 6 檔窗內 eligible 恆 0 的一般股
#   ⚠ 另 2 檔創新板（2258、6949）從「窗內曾 eligible」那一半進了 2,039（elig_d4 共 51 股-月）
#     ⇒ 見 backtest/DR_SNAPSHOT_FOOTNOTE.md §七（裁定線 20260924-2229 §二：只加腳註、不重跑）
#   ⇒ ⭐ 2,039 的定義（本線 1511／commit 34b06b593）是：
#      【判定窗 [523,2835] 內曾 eligible 的 1,586 檔】∪【新增普通股 453 檔】
#   ⇒ ⛔ 所以 (a) 要用那一份清單，⛔ 不是「面板全體再剔非普通股」
_w = p[p["pos_"].notna() & (p["pos_"] >= 523) & (p["pos_"] <= 2835)] if "pos_" in p else None
_cur = set(_w.loc[_w["eligible"].astype(bool), "stock_id"].astype(str))
_g = pd.read_csv("backtest/resultsd4_gate.csv", dtype=str)
_n453 = set(_g.loc[(_g["direction"] == "新進來")
                   & (_g["fam2"].str.contains("沒過閘門", na=False)), "stock_id"])
pool2039 = _cur | _n453
allsid = sorted(set(p["stock_id"].astype(str)))
keep = [s for s in sorted(pool2039) if not not_common(s)]
drop = [s for s in allsid if s not in set(keep)]
print("\n=== (a) 證券圈選 ===")
print("  面板證券集合 {:,} 檔 ⇒ 剔除 {} 檔 ⇒ 留 **{:,} 檔**".format(len(allsid), len(drop), len(keep)))
print("  ⇒ 剔除 {} 檔（創新板／TDR／窗內 eligible 恆 0）".format(len(drop)))
_tdr_in = sorted(s_ for s_ in pool2039 if not_common(s_))
print("  ⚠ 本線 1511 的 2,039 含 {} 檔 TDR（{}）⇒ 依 seq17 §4-3，S1′／S0_pool 要剔掉它們"
      .format(len(_tdr_in), "、".join(_tdr_in)))
assert len(pool2039) == 2039, "⛔ 2,039 母體對不上：{}".format(len(pool2039))
assert len(keep) == 2039 - len(_tdr_in), "⛔ 剔 TDR 後檔數不對：{}".format(len(keep))
print("  ⭐ 閘門：2,039 母體 ✅｜剔 TDR 後 S1′／S0_pool 用 **{:,} 檔** ✅".format(len(keep)))

# (b) 該股-月有可成交價格資料 ＝ 面板裡有這一列（面板本來就是「這個月存在」才建列）
#     ⭐ 與 build_sig_gate_b 的剔除同口徑：進場開盤價與出場收盤價要可得 ⇒ 那一步在訊號層做
p["elig_d4"] = p["stock_id"].astype(str).isin(keep)
el_old = p[p["eligible"].astype(bool)]
el_new = p[p["elig_d4"]]
print("\n=== ⭐ 閘門：新旗標必須是舊 eligible 的【超集】 ===")
only_old = el_old.index.difference(el_new.index)
print("  舊 eligible {:,} 股-月／{:,} 檔".format(len(el_old), el_old["stock_id"].nunique()))
print("  新 elig_d4  {:,} 股-月／{:,} 檔".format(len(el_new), el_new["stock_id"].nunique()))
print("  ⛔ 舊有而新沒有 ＝ {:,} 股-月".format(len(only_old)))
if len(only_old):
    bad = p.loc[only_old, "stock_id"].astype(str).unique()
    print("     ⇒ 逐檔：" + "、".join(sorted(bad)[:10]))
    print("     ⭐ 預期只有 TDR（S0_mkt 保留它們、S1′ 剔除 ⇒ 兩池差這幾檔，seq17 §4-3 要逐格列）")

# ── 必報欄①：那 453 檔進池後貢獻多少
g = pd.read_csv("backtest/resultsd4_gate.csv", dtype=str)
n453 = set(g.loc[(g["direction"] == "新進來") & (g["fam2"].str.contains("沒過閘門", na=False)), "stock_id"])
sub = el_new[el_new["stock_id"].astype(str).isin(n453)]
print("\n=== ⭐ 必報欄①：453 檔進池後貢獻 ===")
print("  那 453 檔在 elig_d4 裡 ＝ **{:,} 股-月**／占 elig_d4 {:.2f}%（{:,} 檔實際有列）".format(
    len(sub), len(sub) / len(el_new) * 100, sub["stock_id"].nunique()))
for col, lab in (("rev_hi24", "rev_hi24"), ("ma60_up", "MA60")):
    na = sub[col].isna().sum()
    print("  其中 {} 為 NaN（K 棒不足 ⇒ 依定義不成立）＝ {:,} 股-月（{:.2f}%）".format(lab, na, na / len(sub) * 100))
print("\n=== ⭐ 必報欄②：逐月可買檔數（舊 S0 是 670 檔的那個量）===")
m_old = el_old.groupby("measure_date")["stock_id"].nunique()
m_new = el_new.groupby("measure_date")["stock_id"].nunique()
print("  舊 eligible  月中位 {:,.0f}｜min {:,}｜max {:,}".format(m_old.median(), m_old.min(), m_old.max()))
print("  新 elig_d4   月中位 {:,.0f}｜min {:,}｜max {:,}".format(m_new.median(), m_new.min(), m_new.max()))
print("  ⇒ 中位放大 {:.2f}×".format(m_new.median() / m_old.median()))
p[["stock_id", "measure_date", "eligible", "elig_d4"]].to_csv("backtest/results_d4/elig_d4.csv.gz", index=False, compression="gzip")
print("\n⇒ 落檔 backtest/results_d4/elig_d4.csv.gz")
