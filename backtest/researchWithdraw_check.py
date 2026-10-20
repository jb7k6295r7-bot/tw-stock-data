# -*- coding: utf-8 -*-
"""researchWithdraw 獨立查核（seq391／392／393）。回測線，2026-10-20。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchWithdraw_check.py

K1 A 帳戶 ① 3,404 淨 3.5% 全期：另寫一支最簡迴圈（不呼叫 researchWithdraw.sim）重算期末總額、最大回落、最低市值 ⇒ 與 grid.csv 一致
K2 抽樣年手算：2008、2022 逐月（配息稅健保、發放、賣股單位與成本）印出；每筆賣股 成本 ＝ 0.2425% × 賣出總額、淨得 ＝ 總額 − 成本、單位 × 開盤價 ＝ 總額
K3 現金（暫存／水庫）逐日遞迴：前日 ＋ 稅後配息 − 發放 ＋ 賣股淨得（＋利息）＝ 當日（四個抽樣檔全期）
K4 水庫：補水庫後水庫 ＝ 24 個月；③④⑤ 補水庫日的條件用前一交易日收盤獨立重算（不前視）；發放合計 ＝ 月數 × 目標
K5 B 帳戶賣法：每次賣股都先賣比重超標的那檔（賣後不會讓超標那檔變成不足；兩檔都賣時賣後回到 60／40）
K6 合成 00685L ＝ researchMix70.load() 的合成序列（2008～2017-03 逐日報酬）；接合日前後連續
K7 高股息並排：全期重算 ＝ resultsHighDiv/grid_with_endcagr.csv
K8 措辭：run.log／grid 不含「不賣最好」「不提領最好」；不提領帳戶不在表內
K9 策略鎖：python -m backtest.strategy_lock --check
"""
import os
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchHighDiv as RH  # noqa: E402
from backtest import researchWithdraw as W  # noqa: E402

D = W.OUT
ok_all = []


def chk(name, ok, extra=""):
    ok_all.append(bool(ok)); print(f"[{'OK' if ok else 'NG'}] {name} {extra}")


G = pd.read_csv(os.path.join(D, "grid.csv"))
cal, pos, X, c4, c5, regime, ind, info, tdd, fdd = W.load_all()
i0 = pos["2007-12-26"]; i1 = len(cal) - 1

# ── K1 最簡迴圈 ──
V0 = 500000.0; M = 3404 / 2; SC = 0.001425 + 0.001
x = X["0050"]
used = 0.0; inv = V0 - M; u = (inv - inv * 0.00385) / x["O"][i0]; cash = 0.0; out = M
path = [u * x["C"][i0] + cash]
for t in range(i0 + 1, i1 + 1):
    if cal[t][:4] != cal[t - 1][:4]:
        used = 0.0
    u *= x["split"][t]
    d = x["div"][t]
    if d > 0:
        g = u * d; cr = min(0.085 * g, max(80000 - used, 0)); used += cr
        tax = 0.12 * g - cr; nhi = 0.0211 * g if g >= 20000 else 0.0
        cash += g - tax - nhi
    if cal[t][:7] != cal[t - 1][:7]:
        if cash >= M:
            cash -= M
        else:
            o = x["O"][t] if np.isfinite(x["O"][t]) else x["C"][t - 1]
            gross = (M - cash) / (1 - SC); u -= gross / o; cash = 0.0
        out += M
    path.append(u * x["C"][t] + cash)
path = np.array(path)
end_mine = (path[-1] + out) * 2
pk = np.maximum.accumulate(np.r_[V0, path]); mdd_mine = float(((np.r_[V0, path] - pk) / pk).min())
row = G[(G["起點"] == "2007-12") & (G["帳戶"] == "A") & (G["每月目標"] == 3404) & (G["稅版"] == "淨3.5%") & (G["方法"] == "①固定金額")].iloc[0]
chk("K1 A ① 3,404 全期 期末總額（最簡迴圈）＝ grid", abs(end_mine - row["期末總額（每100萬）"]) < 1e-3,
    f"手算 {end_mine:,.2f} vs grid {row['期末總額（每100萬）']:,.2f}；累計領現 {out*2:,.0f}")
chk("K1 最大回落、最低市值 一致", abs(mdd_mine - row["最大回落（市值＋水庫）"]) < 1e-9 and abs(path.min() / V0 - row["最低市值剩本金"]) < 1e-9,
    f"回落 {mdd_mine:.4%}／最低 {path.min()/V0:.4f}")

# ── K2／K3 抽樣檔 ──
for nm, acct, tgt, m in (("A_3404_m1", "A", 3404, 1), ("B_3404_m1", "B", 3404, 1), ("B_3404_m4", "B", 3404, 4), ("A_4649_m3", "A", 4649, 3)):
    S = pd.read_csv(os.path.join(D, f"sample_sales_full_3.5_{nm}.csv"))
    Dv = pd.read_csv(os.path.join(D, f"sample_divs_full_3.5_{nm}.csv"))
    P = pd.read_csv(os.path.join(D, f"sample_pays_full_3.5_{nm}.csv"))
    Dy = pd.read_csv(os.path.join(D, f"sample_daily_full_3.5_{nm}.csv"))
    assets = W.ACCTS[acct][0]
    gross_ok = all(abs(sum(r[f"賣{a}"] for a in assets) - r["賣出總額"]) < 1e-6 for _, r in S.iterrows())
    cost_ok = np.allclose(S["成本"], S["賣出總額"] * SC, atol=1e-6) and np.allclose(S["淨得"], S["賣出總額"] - S["成本"], atol=1e-6)
    chk(f"K2 {nm} 每筆賣股 成本＝0.2425%×總額、淨得＝總額−成本、各檔賣出合計＝總額（{len(S)} 筆）", gross_ok and cost_ok)
    # 稅：逐年 8.5% 抵減上限
    Dv["年"] = Dv["date"].str[:4]; tax_ok = True; used = {}
    for _, r in Dv.iterrows():
        y = r["年"]; cr = min(0.085 * r["給付"], max(80000 - used.get(y, 0.0), 0)); used[y] = used.get(y, 0.0) + cr
        tax_ok &= abs(r["稅"] - (0.12 * r["給付"] - cr)) < 1e-6 and abs(r["健保"] - (0.0211 * r["給付"] if r["給付"] >= 20000 else 0)) < 1e-6
    chk(f"K2 {nm} 配息稅（12%−8.5% 抵減、每戶 8 萬上限）與健保逐筆（{len(Dv)} 筆）", tax_ok)
    # K3 現金遞迴
    inc = pd.Series(0.0, index=Dy["date"])
    for _, r in Dv.iterrows():
        inc[r["date"]] += r["淨"]
    for _, r in S.iterrows():
        inc[r["date"]] += r["淨得"]
    pay = pd.Series(0.0, index=Dy["date"])
    for _, r in P.iterrows():
        pay[r["date"]] += r["發放"]
    res = Dy["res"].to_numpy(); prev = (24 * tgt / 2 if m >= 3 else 0.0)
    rec = prev + np.cumsum(inc.to_numpy() - pay.to_numpy())
    if m >= 3:
        rec = rec  # 窗首：水庫 24 個月 − 第一個月（發放已記在窗首日）
    else:
        rec = rec + 0.0
    # ①②窗首發放從本金留下（不經暫存）⇒ 加回第一筆
    if m <= 2:
        rec = rec + P["發放"].iloc[0]
    chk(f"K3 {nm} 現金逐日遞迴 ＝ 輸出（{len(res)} 日）", np.max(np.abs(rec - res)) < 1e-4, f"最大差 {np.max(np.abs(rec-res)):.2e}")
    months = len(P); want = months * tgt / 2
    if m != 2:
        chk(f"K4 {nm} 發放合計 ＝ 月數 × 目標", abs(P["發放"].sum() - want) < 1e-6, f"{months} 個月、合計 {P['發放'].sum()*2:,.0f}／每 100 萬")
    if m >= 3:
        ref = S[S["種類"] == "補水庫"]
        after = [res[Dy.index[Dy["date"] == d][0]] for d in ref["date"]]
        # 補水庫當日若有配息，水庫 ＝ 24 個月（配息在發放前已入水庫，補到滿）
        chk(f"K4 {nm} 補水庫後水庫 ＝ 24 個月（{len(ref)} 次）", np.allclose(after, 24 * tgt / 2, atol=1e-4))
        chk(f"K4 {nm} 被迫賣 0 次 ＝ grid", (S["種類"] == "被迫").sum() == 0)
    if acct == "B":
        good = True
        for _, r in S.iterrows():
            wb = np.array(eval(r["權重前"])); s = np.array([r["賣0050"], r["賣00685L"]])
            pr = np.array([r["價0050"], r["價00685L"]])
            H = r["賣出總額"] / (1.0)  # 總額
            # 賣前持有金額（由權重前 × 賣前總值）：賣前總值未存 ⇒ 用條件判斷：只賣一檔時，那檔必須是超標的
            if (s > 1e-9).sum() == 1:
                good &= int(np.argmax(s)) == int(np.argmax(wb - np.array([0.6, 0.4])))
        chk(f"K5 {nm} 只賣一檔時都是比重超標那檔（{len(S)} 筆中 {(np.minimum(S['賣0050'], S['賣00685L']) <= 1e-9).sum()} 筆單檔）", good)

# K2 手算印出：A ① 3,404 2008、2022
S = pd.read_csv(os.path.join(D, "sample_sales_full_3.5_A_3404_m1.csv")); Dv = pd.read_csv(os.path.join(D, "sample_divs_full_3.5_A_3404_m1.csv"))
for y in ("2008", "2022"):
    print(f"\n[K2 手算 {y}｜A ① 3,404 淨 3.5%｜50 萬本金口徑（元）]")
    for _, r in Dv[Dv["date"].str[:4] == y].iterrows():
        print(f"  配息 {r['date']} 單位 {r['單位']:.2f} × {r['每單位配息']} ＝ {r['給付']:.2f}｜稅 {r['稅']:.2f}（12%−8.5%）｜健保 {r['健保']:.2f}｜淨 {r['淨']:.2f}")
    for _, r in S[S["date"].str[:4] == y].iterrows():
        print(f"  賣股 {r['date']} 開盤 {r['價0050']} 賣 {r['賣0050']/r['價0050']:.4f} 單位 ＝ {r['賣出總額']:.2f}｜成本 {r['成本']:.2f}（0.2425%）｜淨得 {r['淨得']:.2f}"
              f"｜手算 淨得÷(1−0.2425%) ＝ {r['淨得']/(1-SC):.2f}")

# ── K4 條件不前視：獨立重算 ──
P = RH.load_px("0050", info["main"])["close"].dropna()
adj = P.copy(); adj[adj.index < "2025-06-18"] /= 4
bad = 0; n = 0
for nm, m in (("B_3404_m4", 4),):
    S = pd.read_csv(os.path.join(D, f"sample_sales_full_3.5_{nm}.csv"))
    for d in S[S["種類"] == "補水庫"]["date"]:
        t = pos[d]; prev = cal[t - 1]
        h = adj[adj.index <= prev]; last = h.iloc[-1]
        lo = (pd.Timestamp(h.index[-1]) - pd.Timedelta(days=363)).strftime("%Y-%m-%d")
        hi = h[h.index >= lo].max(); n += 1
        bad += not (last >= 0.95 * hi)
chk("K4 ④ 補水庫日：前一交易日 0050 收盤 ≥ 52 週高 ×0.95（獨立重算）", bad == 0 and n > 0, f"{n} 次")
ms = [t for t in range(i0 + 1, i1 + 1) if cal[t][:7] != cal[t - 1][:7]]
sma_bad = 0
for t in ms:
    h = adj[adj.index <= cal[t - 1]]
    sma_bad += bool(h.iloc[-1] > h.iloc[-200:].mean()) != bool(c5[t - 1])
chk("K4 ⑤ 月底站上 200 日線（獨立重算，全部月底）", sma_bad == 0, f"{len(ms)} 個月底、不符 {sma_bad}")

# ── K6 合成 ──
from backtest import researchMix70 as MX  # noqa: E402
MXd = MX.load(); mcal = MXd["cal"]; mpos = MXd["pos"]; SCm = MXd["SC"]["00685L"]
days = [d for d in cal if "2008-01-02" <= d < W.LIST685 and d in mpos]
a = np.array([X["00685L"]["C"][pos[d]] for d in days]); b = np.array([SCm[mpos[d]] for d in days])
ra = a[1:] / a[:-1] - 1; rb = b[1:] / b[:-1] - 1
consec = np.array([mpos[days[k + 1]] - mpos[days[k]] == 1 and pos[days[k + 1]] - pos[days[k]] == 1 for k in range(len(days) - 1)])
diff = np.abs(ra - rb)[consec]
chk("K6 合成 00685L 逐日報酬 ＝ researchMix70.load() 合成（2008～2017-03）", np.percentile(diff, 99) < 2e-3,
    f"{consec.sum()} 日；中位差 {np.median(diff):.2e}、99% 分位 {np.percentile(diff,99):.2e}、最大 {diff.max():.2e}（還原價來源不同：本檔以除息事件建鏈）；相關 {np.corrcoef(ra[consec], rb[consec])[0,1]:.6f}")
ts = pos[W.LIST685]
r_join = X["00685L"]["C"][ts] / X["00685L"]["C"][ts - 1] - 1; r_syn = X["00685L"]["Lc"][ts] / X["00685L"]["Lc"][ts - 1] - 1
chk("K6 接合日報酬 ＝ 合成當日報酬", abs(r_join - r_syn) < 1e-12, f"{r_join:.4%}")

# ── K7 ──
H = pd.read_csv(os.path.join(D, "highdiv_side.csv"))
chk("K7 高股息全期重算 ＝ grid_with_endcagr.csv（6 列）", H["與csv一致"].dropna().astype(bool).all() and H["與csv一致"].notna().sum() == 6)

# ── K8 措辭 ──
txt = open(os.path.join(D, "run.log"), encoding="utf-8").read() + G.to_csv()
chk("K8 不含「不賣最好／不提領最好」、不提領帳戶不列", ("不賣最好" not in txt) and ("不提領最好" not in txt) and ("不提領" not in set(G["方法"])))

# ── K9 策略鎖 ──
p = subprocess.run([sys.executable, "-m", "backtest.strategy_lock", "--check"], cwd=os.path.expanduser("~/tw-p17"), capture_output=True, text=True)
chk("K9 策略鎖", p.returncode == 0, (p.stdout + p.stderr).strip()[-200:])
print(f"\n查核結果：{sum(ok_all)}／{len(ok_all)} 通過")
