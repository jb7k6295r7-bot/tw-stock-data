# -*- coding: utf-8 -*-
"""PREREGL §四② 合格數閘（seq3 d583251adfc2d594；⛔ 不看報酬、不跑引擎）。

登錄逐字：先報每月合格數分佈、合格數 < k_m 的月數與短缺檔數、R ＝ Σ實取檔數 ÷ Σk_m ⇒ R < 90% ⇒ 不開跑
本線寫死的落地讀法（看任何合格數之前定）：
  G1 面板 ＝ resultsAFC/panel.csv.gz（W1／A／F／C 同一份；gate3 內建）；資料 ＝ main edc6f8002f 快照
  G2 k_m ＝ S1 在量測日 m 的候選檔數 ＝ P7.build_sig_gate_b(panel, signal="B") 之後（含 entry／exit 剔除）每個 m 的列數
     ⇒ 只計判定窗內的量測日：entry_pos ∈ [w0, w1]（W1 的 marks 與 P12.win_bounds「全窗」＝ 2017-03-02～2026-08-24）
  G3 SL 合格 ＝ eligible 列上 甲 ∧ 乙；再當面板子集交 build_sig_gate_b(signal="ALL")（同一套剔除）⇒ 每個 m 的合格數 q_m
  G4 甲：c(m) ＝ 截至 m（含）往回、在該股【有效 K 棒日】（close 非缺）上連續 trust > 0 的天數；
         無有效 K 棒日 ⇒ 跳過（不算、不斷）；trust ≤ 0 ⇒ 斷；三大法人列 absent 或 trust NaN ⇒ 斷（計數）
         甲 ⇔ c ≥ 4 ∧ Σ(那 c 天 trust) ÷ 1,000 ＞ 1,000
  G5 乙：m_balance(m) < m_balance(cal[pos(m) − 20])（交易日曆往前第 20 個交易日）；
         不在信用表上 ⇒ 乙不成立，三類分別計數：① 無 stocks_margin 檔 ② m 或 m−20 無列（或 m_balance 缺） ③ [m−20, m] 內任一列 note 含 "O"
  G6 實取 ＝ min(q_m, k_m)；R ＝ Σ實取 ÷ Σk_m；短缺月 ＝ q_m < k_m 且 k_m > 0
"""
import os, sys, json
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchH2 as H2
from backtest import researchp7 as P7, researchp12 as P12, p4_features as P4F
D = H2.D
root = os.path.expanduser(f"~/h2data/{H2.SHA}/data")
OUT = "backtest/resultsL"

cal = D.load_calendar(); pos = {d: i for i, d in enumerate(cal)}
panel = P4F.read_panel("backtest/resultsAFC/panel.csv.gz")
uni = D.load_universe().set_index("stock_id")["market"]
w0, w1 = P12.win_bounds(cal, "全窗")
assert str(cal[w0].date()) == "2017-03-02" and str(cal[w1].date()) == "2026-08-24"
closes, opens, valid = {}, {}, {}
for s in sorted(set(panel["stock_id"])):
    st = D.load_stock(s, uni.get(s, "twse"), cal)
    if st is None:
        continue
    c = st.df["close"].to_numpy(float)
    closes[s] = pd.Series(c).ffill().to_numpy(); opens[s] = st.df["open"].to_numpy(float); valid[s] = np.isfinite(c)
S1 = P7.build_sig_gate_b(panel, cal, closes, opens, start=P12.START, signal="B")
S1 = S1[(S1["entry_pos"] >= w0) & (S1["entry_pos"] <= w1)]
k = S1.groupby("measure_date").size() if "measure_date" in S1.columns else S1.groupby("month").size()
key = "measure_date" if "measure_date" in S1.columns else "month"

el = panel[(panel["eligible"].astype(bool)) & (panel["measure_date"] >= pd.Timestamp(P12.START))].copy()
cnt = {"甲_斷_absent或NaN": 0, "乙①無融資檔": 0, "乙②m或m−20無列": 0, "乙③停止融資O": 0, "甲成立": 0, "乙成立": 0, "甲∧乙": 0, "eligible列": len(el)}
ok = np.zeros(len(el), bool)
for s, g in el.groupby("stock_id"):
    fi, fm = os.path.join(root, "stocks_inst", f"{s}.csv"), os.path.join(root, "stocks_margin", f"{s}.csv")
    tr = np.full(len(cal), np.nan); has_i = np.zeros(len(cal), bool)
    if os.path.exists(fi):
        a = pd.read_csv(fi, usecols=["date", "trust"]).drop_duplicates("date", keep="last")
        ip = a["date"].map(lambda d: pos.get(pd.Timestamp(d)))
        m_ = ip.notna(); ii = ip[m_].astype(int).to_numpy()
        tr[ii] = a.loc[m_, "trust"].to_numpy(float); has_i[ii] = True
    mb = np.full(len(cal), np.nan); has_m = np.zeros(len(cal), bool); noteO = np.zeros(len(cal), bool)
    mfile = os.path.exists(fm)
    if mfile:
        b = pd.read_csv(fm, usecols=["date", "m_balance", "note"], dtype={"note": str}).drop_duplicates("date", keep="last")
        mp = b["date"].map(lambda d: pos.get(pd.Timestamp(d)))
        m_ = mp.notna(); jj = mp[m_].astype(int).to_numpy()
        mb[jj] = b.loc[m_, "m_balance"].to_numpy(float); has_m[jj] = True
        noteO[jj] = b.loc[m_, "note"].fillna("").str.contains("O").to_numpy()
    v = valid.get(s, np.zeros(len(cal), bool))
    for idx, md in zip(g.index, g["measure_date"]):
        p = pos[md]
        # 甲
        cday, tot, t = 0, 0.0, p
        while t >= 0:
            if not v[t]:
                t -= 1; continue
            if not has_i[t] or not np.isfinite(tr[t]):
                cnt["甲_斷_absent或NaN"] += 1
                break
            if tr[t] > 0:
                cday += 1; tot += tr[t]; t -= 1
            else:
                break
        A = cday >= 4 and tot / 1000 > 1000
        # 乙
        if not mfile:
            B = False; cnt["乙①無融資檔"] += 1
        elif p - 20 < 0 or not (has_m[p] and has_m[p - 20]) or not (np.isfinite(mb[p]) and np.isfinite(mb[p - 20])):
            B = False; cnt["乙②m或m−20無列"] += 1
        elif noteO[p - 20:p + 1].any():
            B = False; cnt["乙③停止融資O"] += 1
        else:
            B = mb[p] < mb[p - 20]
        cnt["甲成立"] += int(A); cnt["乙成立"] += int(B); cnt["甲∧乙"] += int(A and B)
        ok[el.index.get_loc(idx)] = A and B
sub = panel.loc[el.index[ok]]
SL = P7.build_sig_gate_b(sub, cal, closes, opens, start=P12.START, signal="ALL")
SL = SL[(SL["entry_pos"] >= w0) & (SL["entry_pos"] <= w1)]
q = SL.groupby(key).size()
T = pd.DataFrame({"k_m": k}).join(pd.DataFrame({"q_m": q}), how="left").fillna(0).astype(int)
T["實取"] = np.minimum(T["q_m"], T["k_m"]); T["短缺"] = T["k_m"] - T["實取"]
R = T["實取"].sum() / T["k_m"].sum()
os.makedirs(OUT, exist_ok=True)
T.to_csv(os.path.join(OUT, "gate2_monthly.csv"))
res = {"R": float(R), "Σk_m": int(T["k_m"].sum()), "Σ實取": int(T["實取"].sum()), "量測日數": len(T), "k_m>0 月數": int((T["k_m"] > 0).sum()),
       "短缺月數（q<k 且 k>0）": int(((T["q_m"] < T["k_m"]) & (T["k_m"] > 0)).sum()), "短缺檔數": int(T["短缺"].sum()),
       "q_m 分佈": {"min": int(T["q_m"].min()), "p10": float(T["q_m"].quantile(.1)), "中位": float(T["q_m"].median()), "p90": float(T["q_m"].quantile(.9)), "max": int(T["q_m"].max())},
       "k_m 分佈": {"min": int(T["k_m"].min()), "中位": float(T["k_m"].median()), "max": int(T["k_m"].max())},
       "計數": cnt, "閘": "過（R ≥ 90%）" if R >= 0.9 else "不過（R < 90%）⇒ 不開跑"}
json.dump(res, open(os.path.join(OUT, "gate2.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))
print(T.to_string())
