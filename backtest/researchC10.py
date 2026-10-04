# -*- coding: utf-8 -*-
"""PREREGC10「幣本位做多放大 v1」（sha 8902cc2e6b68bf17）——回測線執行端。裁定 seq289 §二：核准甲案（強平地圖＝主產出，確定性描述，N＝0）。

⭐ 讀法寫死：2026-10-04 11:18（台北）——⛔ 在算出任何數字之前寫在這裡；之後只准補「執行時發現」並標時間，不改讀法。
   登錄沒寫到、由回測線自己補的讀法一律標【執行者補】。

資料：main commit 1fb8815e81aa53edf91aacb8ebb4125c716ead3f（資料庫線 1004-1053 交件之後的 main）
   ⇒ git archive 取 data/crypto_cm_perp、data/crypto_cm_mark、data/meta/crypto_cm_funding_rest、data/crypto 到 ~/c10data/<sha>/（唯讀；同 C2 做法）
   資金費率：data/meta/crypto_cm_funding_rest/<SYM>USD_PERP.csv（REST 完整版；⛔ 不用封存 data/crypto_cm_funding）
   成交價日 K：data/crypto_cm_perp/；標記價日 K：data/crypto_cm_mark/；現貨日 K（對照組）：data/crypto/<SYM>.csv（C1／C2 同一份）
   每口面額 BTC 100 USD、其餘 10 USD（只描述；口數取整依登錄 §六 忽略）；保證金＝各幣本身

⭐ 落地讀法
 R1 窗：各幣第一根幣本位日 K ～ 三份（成交價、標記價、現貨）共同最後一天【執行者補：窗尾】
    〔執行時發現 2026-10-04 11:21 台北：寫死時誤記為 2026-10-02；幣本位日 K 實際最後一天是 2026-09-30（現貨到 10-02）⇒ 依同一條規則窗尾＝2026-09-30〕
    日 K 必須逐日無缺（同 C2 load_px 閘門）；三份日期必須一一對上，否則停
 R2 資金費歸屬（沿用 C2 K3）：funding_time（毫秒 UTC，先截到秒）的 UTC 日期＝d ⇒ 屬於「close(d−1) → close(d)」那一天的持有
    ⭐ 逐筆累加，⛔ 不假設一天 3 次（SOL 有 2、4 小時間隔）；當天 0 筆就是 0（列出 0 筆的日子；2026-06-30 少一筆是官方本來就沒有）
 R3 資金費以幣計（登錄 §三）：多方每筆 ΔW ＝ − rate_i × N ÷ 標記價_i；N＝合約美元名目
    標記價_i 用【前一日標記價收盤 mark_close(d−1)】近似（日 K 沒有逐筆標記價）【執行者補】
 R4 部位（登錄 §一、§三）：E＝1＋L，L∈{0.5、1、2}；窗首／起點當日收盤把 1 顆幣全當保證金，開 N＝L × 1 × close 的幣本位多單
    權益（幣）＝ W ＋ N ×（1/Pe − 1/P）；W＝錢包幣數（已實現＋資金費＋手續費），Pe＝持倉均價（再平衡時重設為當日收盤）
    估值與再平衡一律用【成交價收盤】；價格口徑（標記價／成交價）只換「強平用的日低」【執行者補】
 R5 強平（逐倉、標準幣本位公式）【執行者補：公式本身】：權益（幣）≤ m × N ÷ P 時強平
    ⇒ 實際強平價 Lp ＝ N ×（1＋m）÷（W ＋ N/Pe）；分母 ≤ 0 ⇒ Lp＝∞（已經爆）
    理想值（m＝0、無手續費、無資金費）退化成 Lp＝Pe × L/(1＋L)，即「從建倉／再平衡點跌 1/E」——⭐ 只是理想值，地圖一律用實際 Lp
    每日順序（沿用 C2 引擎）：① 先扣當日資金費 ② 用扣完的 W 重算 Lp ③ 當日低 ≤ Lp ⇒ 強平 ④ 否則到收盤，若是再平衡日就再平衡
    強平：保證金幣全失，權益 0、之後 0（C2 K5）；⛔ 不另計強平清算費（登錄沒寫；有的話強平只會更早，列為限制）
    〔補記 2026-10-04 18:45 台北（seq293、seq294 §三）〕強平清算費（BTC／ETH 1.5%、BNB／XRP 1.0%、DOGE 1.75%、SOL 2.5%；私有庫 cm_specs）
    在強平那一刻從剩餘保證金扣，不改觸發時點（觸發仍看維持保證金率）；強平期本來就記 −100% ⇒ 強平日與歸零結果都不變，不重跑
 R6 維持保證金率 m ∈ {0.5%、1%、2%} 三值全報；官方最低一級＝【待定】（分級表未交）；⛔ 不用 exchangeInfo 的 maintMarginPercent 2.5
    〔換標 2026-10-04 18:45 台北（seq294 §三，不重判、不重跑）〕主格標示改「官方分級表最低一級（現值口徑）」：私有庫 cm_specs/cm_margin_tiers.csv
    （2026-05-11／12 生效、單位＝幣）最低一級：BTC 0.4%（不等於三值，最接近 0.5% 欄）、ETH 0.5%（＝0.5% 欄）、BNB 2.5%（高於三值，最接近 2% 欄）、
    SOL 1.0%（＝1% 欄）、XRP 1.0%（＝1% 欄）、DOGE 1.2%（最接近 1% 欄）；最低一級只適用部位價值在第一級上限內；口徑為現值，早年實際分級可能不同
 R7 手續費：單邊 0.05% × |名目變動|（以幣付＝費率 × |ΔN| ÷ P）；建倉付一次；再平衡付差額；敏感度 ×0.5／×1／×2／×4
    再平衡的新名目 N′＝ L × 權益（幣，扣費前）× P，再扣手續費【執行者補：扣費前定 N′】
    窗尾不平倉、不付平倉費（長期持有；成長腿是以市價估的權益）【執行者補】
 R8 再平衡軸（seq241 三值全報）：不再平衡（口數固定）／每月（主格）／每日
    每月＝每個 UTC 月份第一天的收盤再平衡【執行者補：哪一天】；每日＝每天收盤
 R9 起點（seq289「每月滾動起點」）：每個 UTC 月份第一天的收盤建倉，從窗首後第一個月初到 2026-09-01【執行者補：最後一個起點】
    另跑「窗首」一條（登錄 §六：窗首當日收盤建倉）＝先驗 ①～③ 與成長腿的主窗
    每條路徑抱到窗尾；第一次強平就停（之後 0）
 R10 強平地圖（主格＝每月再平衡、標記價日低；成交價日低並報；m 三值全報）每格報：
    起點數、遇到強平的起點數與比例（到窗尾為止）；遇到者「從起點到第一次強平」的最快／中位／最慢天數；
    固定 1／2／4 年（月份加 12／24／48）內遇到強平的比例（只算抱得滿那段的起點）
    ⭐「最慢多久遇到第一次強平」＝遇到強平的起點裡，等最久的那一條的天數；沒遇到的起點只能說「到窗尾為止沒有」，⛔ 不外推【執行者補：讀法】
    每個 E 的總結：6 幣月初起點合併，報比例與最慢天數（m 三值）
 R11 現貨對照（登錄 §七）：同幣存著不動，同窗同起點，不扣成本；美元報酬用現貨收盤，C10 美元權益＝權益（幣）× 成交價收盤
 R12 成長腿（⛔ 只描述、不判、不計 N；⛔ 不寫放大比較好／不好）：窗首起、標記價口徑、m＝2%、成本 ×1【執行者補：取三值中最保守的 2%，同 C2 K9 退路】
    報：美元年化（365.25 日）、現貨年化、期末幣數÷期初幣數、年化平均日對數報酬差（強平後無定義）、最大回落、逐年、去掉最好一年後年化；
    滾動起點：抱 1／2／4 年與抱到窗尾，C10 美元權益高於現貨的起點比例（⛔ 不是勝率）
 R13 描述（登錄 §五 ②③）：從再平衡點起算的最深跌幅——一日內＝min(low(t)/close(t−1))−1；一月內＝每個月初收盤到下個月初之間最低 low ÷ 月初收盤 −1；兩種價各一
    資金費：逐年 Σrate（正＝多方付；年化＝× 365.25 ÷ 當年窗內天數）；對保證金近似＝ × L
 R14 --check：fixture（登錄 §十③ a／b／c ＋ seq289「實際強平價早於 1/E」d）各附會變紅的反例（突變引擎必須讓同一個測試失敗）；
    再用另一支逐筆、純迴圈的參考實作，抽樣重算真資料路徑（種子 20260923）＋逐日列出一段強平前後的 W、N、Pe、Lp、日低，和向量引擎逐位比
⛔ 結果不寫任何「開幾倍安全／可以開」（登錄 §八）。
"""
from __future__ import annotations
import os, sys, json, time, math, argparse, html, functools
import numpy as np
import pandas as pd

SHA = "1fb8815e81aa53edf91aacb8ebb4125c716ead3f"
ROOT = os.path.expanduser(f"~/c10data/{SHA}")
REPO = os.path.expanduser("~/tw-p17")
OUT = os.path.join(REPO, "backtest", "resultsC10")
COINS = ("BTC", "ETH", "BNB", "SOL", "XRP", "DOGE")
FACE = {"BTC": 100, "ETH": 10, "BNB": 10, "SOL": 10, "XRP": 10, "DOGE": 10}
ES = (1.5, 2.0, 3.0)
REBALS = ("none", "monthly", "daily")
REBAL_ZH = {"none": "不再平衡", "monthly": "每月", "daily": "每日"}
BASES = ("mark", "trade")
BASIS_ZH = {"mark": "標記價日低", "trade": "成交價日低"}
MMRS = (0.005, 0.01, 0.02)
CMULTS = (0.5, 1.0, 2.0, 4.0)
COST_SIDE = 0.0005
W_END = "2026-09-30"
LAST_START = "2026-09-01"
HORIZ = (12, 24, 48)
GROWTH_MMR = 0.02
SEED = 20260923
DAYS_YEAR = 365.25
FROZEN = "2026-10-04 11:18（台北）"
# seq294 §三：官方分級表最低一級（現值口徑；私有庫 cm_specs/cm_margin_tiers.csv，2026-05-11／12 生效）——(費率, 最接近的欄, 第一級上限〔幣〕)
TIER1 = {"BTC": (0.004, 0.005, 5), "ETH": (0.005, 0.005, 15), "BNB": (0.025, 0.02, 2000), "SOL": (0.01, 0.01, 400), "XRP": (0.01, 0.01, 33100), "DOGE": (0.012, 0.01, 500000)}
LIQ_FEE = {"BTC": 0.015, "ETH": 0.015, "BNB": 0.01, "SOL": 0.025, "XRP": 0.01, "DOGE": 0.0175}


def tier_note_html():
    parts = []
    for s, (r, col, cap) in TIER1.items():
        rel = "＝" if abs(r - col) < 1e-12 else ("高於三欄，最接近 " if r > max(MMRS) else ("低於三欄，最接近 " if r < min(MMRS) else "最接近 "))
        parts.append(f"{s} {r * 100:g}%（{rel}{col * 100:g}% 欄）")
    return ("<b>主格標示：官方分級表最低一級（現值口徑）</b>＝" + "、".join(parts)
            + "。資料來源：資料庫線交的官方分級表（2026-05 生效、單位＝幣）。最低一級只適用部位價值在第一級上限內；口徑是現值，早年實際分級可能不同；三欄照舊全報、不重判。")


LIQ_FEE_NOTE = ("強平清算費（BTC／ETH 1.5%、BNB／XRP 1%、DOGE 1.75%、SOL 2.5%）在強平那一刻從剩餘保證金扣，不改觸發時點；"
                "強平期本來就記 −100%（存的幣全部歸零），所以強平日與結果都不變。")


# ───────────────────────── 資料 ─────────────────────────
def _load_k(path):
    d = pd.read_csv(path)
    assert (d["open_time"] % 86_400_000 == 0).all(), path
    d["date"] = pd.to_datetime(d["open_time"], unit="ms", utc=True).dt.strftime("%Y-%m-%d")
    d = d.drop_duplicates("date").sort_values("date").reset_index(drop=True)
    gap = (pd.to_datetime(d["date"].iloc[-1]) - pd.to_datetime(d["date"].iloc[0])).days + 1
    assert gap == len(d), f"⛔ 日 K 有缺日：{path}"
    return d


def load(sym):
    p = _load_k(os.path.join(ROOT, "data", "crypto_cm_perp", f"{sym}USD_PERP.csv"))
    mk = _load_k(os.path.join(ROOT, "data", "crypto_cm_mark", f"{sym}USD_PERP.csv"))
    p = p[p["date"] <= W_END].reset_index(drop=True)
    assert p["date"].iloc[-1] == W_END, (sym, p["date"].iloc[-1])
    dates = p["date"].to_numpy()
    mm = mk.set_index("date").reindex(dates)
    assert mm["close"].notna().all() and mm["low"].notna().all(), f"⛔ {sym} 標記價對不上成交價日期"
    sp = pd.read_csv(os.path.join(ROOT, "data", "crypto", f"{sym}.csv"), dtype={"date": str}).drop_duplicates("date").set_index("date").reindex(dates)
    assert sp["close"].notna().all(), f"⛔ {sym} 現貨日 K 缺"
    f = pd.read_csv(os.path.join(ROOT, "data", "meta", "crypto_cm_funding_rest", f"{sym}USD_PERP.csv"))
    f["sec"] = f["funding_time"] // 1000
    f = f.drop_duplicates("sec").sort_values("sec")
    f["date"] = pd.to_datetime(f["sec"], unit="s", utc=True).dt.strftime("%Y-%m-%d")
    g = {k: v.to_numpy(float) for k, v in f.groupby("date")["funding_rate"]}
    fbd = [g.get(dt, np.array([])) for dt in dates]
    cnt = np.array([len(a) for a in fbd])
    return {"sym": sym, "dates": dates, "close": p["close"].to_numpy(float), "tlow": p["low"].to_numpy(float),
            "mclose": mm["close"].to_numpy(float), "mlow": mm["low"].to_numpy(float), "spot": sp["close"].to_numpy(float),
            "fbd": fbd, "fsum": np.array([a.sum() for a in fbd]), "fcnt": cnt,
            "fund_rows_total": int(len(f)), "fund_first": pd.to_datetime(f["sec"].iloc[0], unit="s", utc=True).strftime("%Y-%m-%d %H:%M"),
            "fund_last": pd.to_datetime(f["sec"].iloc[-1], unit="s", utc=True).strftime("%Y-%m-%d %H:%M")}


def rebal_mask(dates, rebal):
    n = len(dates)
    if rebal == "none":
        return np.zeros(n, bool)
    if rebal == "daily":
        return np.ones(n, bool)
    return np.array([x[8:10] == "01" for x in dates])


def start_indices(dates):
    """R9：index 0（窗首）＋ 每個月初（≤ LAST_START）。"""
    s = [0] + [i for i, x in enumerate(dates) if i > 0 and x[8:10] == "01" and x <= LAST_START]
    return np.array(s, int)


# ───────────────────────── 引擎（向量化：多條路徑同時跑）─────────────────────────
def engine(close, low, mclose, fsum, rmask, starts, L, m, cost, want_eq=False):
    """每條路徑 j：在 close(starts[j]) 建倉；L／m／cost 為長度 J 的陣列（cost＝單邊費率，已乘倍數）。
    回 (liq[j]＝強平那天的索引或 −1, eq[j,t]＝收盤權益（幣；未建倉 NaN、強平後 0）或 None, fund[j]＝累計資金費（幣，付出為負）, fee[j])。"""
    J, T = len(starts), len(close)
    W = np.zeros(J); N = np.zeros(J); Pe = np.ones(J); alive = np.zeros(J, bool); liq = np.full(J, -1)
    fund = np.zeros(J); fee = np.zeros(J)
    eq = np.full((J, T), np.nan) if want_eq else None
    for t in range(T):
        if t > 0 and alive.any():
            a = alive
            dW = np.where(a, -fsum[t] * N / mclose[t - 1], 0.0)
            W = W + dW; fund += dW
            den = W + N / Pe
            Lp = np.where(den > 0, N * (1.0 + m) / np.where(den > 0, den, 1.0), np.inf)
            hit = a & (low[t] <= Lp)
            if hit.any():
                liq[hit] = t; alive = alive & ~hit; W[hit] = 0.0; N[hit] = 0.0
            if rmask[t] and alive.any():
                a2 = alive
                e = W + N * (1.0 / Pe - 1.0 / close[t])
                Nn = L * e * close[t]
                fz = cost * np.abs(Nn - N) / close[t]
                W = np.where(a2, e - fz, W); N = np.where(a2, Nn, N); Pe = np.where(a2, close[t], Pe); fee += np.where(a2, fz, 0.0)
        o = starts == t
        if o.any():
            N[o] = L[o] * close[t]; f0 = cost[o] * L[o]; W[o] = 1.0 - f0; fee[o] += f0; Pe[o] = close[t]; alive[o] = True
        if want_eq:
            v = W + N * (1.0 / Pe - 1.0 / close[t])
            eq[:, t] = np.where(alive, v, np.where((liq >= 0) & (liq <= t), 0.0, np.nan))
    return liq, eq, fund, fee


# ───────────────────────── 參考實作（逐筆、純迴圈；也用來造突變反例）─────────────────────────
def ref_path(close, low, mclose, fbd, rmask, E, m, cost, mut=None, trace=False):
    """單一路徑，索引 0＝建倉日。mut：None｜usd_margin（保證金當美元）｜fund_sign（費率符號反）｜fund_3x（假設一天 3 次：平均×3）
    ｜no_relp（強平價建倉後不重算）｜ideal_lp（用理想值 Pe×L/(1+L)）。回 (liq, eq list, trace rows)。"""
    L = E - 1.0
    W = 1.0 - cost * L; N = L * close[0]; Pe = close[0]
    Lp0 = N * (1 + m) / (W + N / Pe)

    def val(P):
        if mut == "usd_margin":
            return (W * Pe + N * (P / Pe - 1.0)) / P
        return W + N * (1.0 / Pe - 1.0 / P)

    eqs = [val(close[0])]; rows = []; liq = -1
    for t in range(1, len(close)):
        rs = list(fbd[t])
        if mut == "fund_sign":
            dW = sum(r * N / mclose[t - 1] for r in rs)
        elif mut == "fund_3x":
            dW = -(float(np.mean(rs)) * 3.0 if rs else 0.0) * N / mclose[t - 1]
        else:
            dW = 0.0
            for r in rs:
                dW -= r * N / mclose[t - 1]
        W += dW
        if mut == "no_relp":
            Lp = Lp0
        elif mut == "ideal_lp":
            Lp = Pe * L / (1.0 + L)
        else:
            den = W + N / Pe
            Lp = N * (1 + m) / den if den > 0 else math.inf
        if trace:
            rows.append({"t": t, "W": W, "N": N, "Pe": Pe, "Lp": Lp, "low": float(low[t]), "close": float(close[t]), "強平": bool(low[t] <= Lp)})
        if low[t] <= Lp:
            liq = t
            eqs += [0.0] * (len(close) - t)
            break
        if rmask[t]:
            e = val(close[t]); Nn = L * e * close[t]
            W = e - cost * abs(Nn - N) / close[t]; N = Nn; Pe = close[t]
        eqs.append(val(close[t]))
    return liq, eqs, rows


def real_one(close, low, mclose, fbd, rmask, E, m, cost):
    """把向量引擎包成單一路徑（給 fixture 用）。"""
    fsum = np.array([float(np.sum(a)) for a in fbd])
    liq, eq, _, _ = engine(np.asarray(close, float), np.asarray(low, float), np.asarray(mclose, float), fsum, np.asarray(rmask, bool),
                           np.array([0]), np.array([E - 1.0]), np.array([m]), np.array([cost]), want_eq=True)
    return int(liq[0]), list(eq[0]), []


# ───────────────────────── fixture（登錄 §十③ ＋ seq289）─────────────────────────
def _z(n):
    return [np.array([]) for _ in range(n)]


def fx_a(run):
    """a. L＝1（E＝2）、同幣保證金：價格 ×0.5 ⇒ 理想權益歸零；×2 ⇒ 美元權益 ×3、幣權益 ×1.5（m＝0、無費用）。"""
    ok = True
    for k, want in ((2.0, 1.5), (0.6, 1 + 1 - 1 / 0.6), (0.51, 1 + 1 - 1 / 0.51)):
        c = [100.0, 100.0 * k]
        _, eq, _ = run(c, c, c, _z(2), [False, False], 2.0, 0.0, 0.0)
        ok &= abs(eq[1] - want) < 1e-12
    _, eq2, _ = run([100.0, 200.0], [100.0, 200.0], [100.0, 200.0], _z(2), [False, False], 2.0, 0.0, 0.0)
    ok &= abs(eq2[1] * 200.0 / (1.0 * 100.0) - 3.0) < 1e-12                       # 美元 ×3
    liq, eq3, _ = run([100.0, 50.0], [100.0, 50.0], [100.0, 50.0], _z(2), [False, False], 2.0, 0.0, 0.0)
    ok &= (liq == 1 and eq3[1] == 0.0)                                              # ×0.5 ⇒ 歸零（觸及理想強平價）
    return bool(ok)


def fx_b(run):
    """b. 正費率多方扣幣、負費率多方加幣；一天 6 筆（SOL 型）要逐筆累加。E＝2 ⇒ N＝100，價 100。"""
    c = [100.0, 100.0]; ok = True
    for rs, want in (([0.001], 1 - 0.001), ([-0.001], 1 + 0.001), ([0.0005] * 6, 1 - 0.003)):
        fb = _z(2); fb[1] = np.array(rs)
        _, eq, _ = run(c, c, c, fb, [False, False], 2.0, 0.01, 0.0)
        ok &= abs(eq[1] - want) < 1e-12
    return bool(ok)


def fx_c(run):
    """c. 每月再平衡後強平價重算：100 → 150（再平衡日）→ 日低 74。
    再平衡後 N＝200、Pe＝150、W＝4/3 ⇒ Lp＝202/(8/3)＝75.75 ⇒ 第 2 天強平；不再平衡 Lp＝50.5 ⇒ 不強平。"""
    c = [100.0, 150.0, 80.0]; lo = [100.0, 150.0, 74.0]
    l1, _, _ = run(c, lo, c, _z(3), [False, True, False], 2.0, 0.01, 0.0)
    l0, _, _ = run(c, lo, c, _z(3), [False, False, False], 2.0, 0.01, 0.0)
    return bool(l1 == 2 and l0 == -1)


def fx_d(run):
    """d. 含維持保證金、手續費、資金費 ⇒ 實際強平價早於理想 1/E：E＝2、m＝1%、費 0.05%、每天 3 筆 0.03%。
    第 11 天扣完當日資金費後 W＝1−0.0005−0.0099＝0.9896 ⇒ Lp＝101/1.9896＝50.764 ＞ 理想 50；第 11 天日低 50.6 ⇒ 實際強平（理想不會）。
    另驗：建倉當下（只含 m 與建倉費）每個 E×m 的實際 Lp／P0 都 ＞ 1 − 1/E。"""
    T = 12; c = [100.0] * T; lo = [100.0] * T; lo[11] = 50.6
    fb = _z(T)
    for t in range(1, T):
        fb[t] = np.array([0.0003] * 3)
    liq, _, _ = run(c, lo, c, fb, [False] * T, 2.0, 0.01, COST_SIDE)
    ok = liq == 11
    for E in ES:
        for m in MMRS:
            L = E - 1; lp = L * (1 + m) / (1 - COST_SIDE * L + L)
            ok &= lp > 1 - 1 / E
    return bool(ok)


FIXTURES = (("a", fx_a, "usd_margin", "保證金當成美元（不跟幣價動）"),
            ("b", fx_b, "fund_sign", "費率符號反過來"),
            ("b2", fx_b, "fund_3x", "假設一天 3 次（平均費率×3，不逐筆加）"),
            ("c", fx_c, "no_relp", "再平衡後強平價不重算"),
            ("d", fx_d, "ideal_lp", "用理想強平價 Pe×L/(1+L)（不含維持保證金、費用、資金費）"))


def run_fixtures():
    res = []
    real = real_one
    refn = lambda *a: ref_path(*a)
    for name, fx, mut, why in FIXTURES:
        g_real, g_ref = fx(real), fx(refn)
        mutant = (lambda mt: (lambda *a: ref_path(*a, mut=mt)))(mut)
        red = not fx(mutant)
        res.append({"案": name, "說明": fx.__doc__.strip().split("\n")[0], "向量引擎": "綠" if g_real else "紅",
                    "參考實作": "綠" if g_ref else "紅", "反例": why, "反例結果": "紅（測試抓得到）" if red else "⛔ 仍綠（測試抓不到）"})
    allok = all(r["向量引擎"] == "綠" and r["參考實作"] == "綠" and r["反例結果"].startswith("紅") for r in res)
    return allok, res


# ───────────────────────── 主計算 ─────────────────────────
@functools.lru_cache(maxsize=None)
def months_add(d, k):
    x = pd.Timestamp(d) + pd.DateOffset(months=k)
    return x.strftime("%Y-%m-%d")


def run_coin(d):
    dates = d["dates"]; starts = start_indices(dates); S = len(starts)
    combos = [(E, m, cm) for E in ES for m in MMRS for cm in CMULTS]
    rows, paths = [], []
    for rebal in REBALS:
        rm = rebal_mask(dates, rebal)
        for basis in BASES:
            low = d["mlow"] if basis == "mark" else d["tlow"]
            st = np.tile(starts, len(combos))
            Lv = np.repeat([c[0] - 1 for c in combos], S); mv = np.repeat([c[1] for c in combos], S); cv = np.repeat([COST_SIDE * c[2] for c in combos], S)
            liq, _, _, _ = engine(d["close"], low, d["mclose"], d["fsum"], rm, st, Lv, mv, cv)
            for ci, (E, m, cm) in enumerate(combos):
                lq = liq[ci * S:(ci + 1) * S]
                for j, s in enumerate(starts):
                    paths.append({"coin": d["sym"], "E": E, "rebal": rebal, "basis": basis, "MMR": m, "cost_mult": cm,
                                  "start": dates[s], "窗首起點": j == 0, "liq_date": dates[lq[j]] if lq[j] >= 0 else "",
                                  "days_to_liq": int((pd.Timestamp(dates[lq[j]]) - pd.Timestamp(dates[s])).days) if lq[j] >= 0 else np.nan})
    return paths


def summarize(P):
    """R10：每格摘要（只用月初起點；窗首另一欄）。"""
    out = []
    for key, g in P.groupby(["coin", "E", "rebal", "basis", "MMR", "cost_mult"], sort=False):
        ms = g[~g["窗首起點"]]; w0 = g[g["窗首起點"]].iloc[0]
        hit = ms[ms["liq_date"] != ""]
        r = dict(zip(["coin", "E", "rebal", "basis", "MMR", "cost_mult"], key))
        r.update({"月初起點數": len(ms), "遇到強平起點數": len(hit), "遇到比例": len(hit) / len(ms) if len(ms) else np.nan,
                  "最快天數": float(hit["days_to_liq"].min()) if len(hit) else np.nan, "中位天數": float(hit["days_to_liq"].median()) if len(hit) else np.nan,
                  "最慢天數": float(hit["days_to_liq"].max()) if len(hit) else np.nan,
                  "強平日（出現次數前三）": "；".join(f"{k}×{v}" for k, v in hit["liq_date"].value_counts().head(3).items()),
                  "窗首起點": w0["start"], "窗首強平日": w0["liq_date"]})
        for h in HORIZ:
            ends = ms["start"].map(lambda x: months_add(x, h))
            full = ms[ends <= W_END]; e2 = ends[ends <= W_END]
            n_hit = int(((full["liq_date"] != "") & (full["liq_date"] <= e2)).sum())
            r[f"{h // 12}年內_可算起點"] = len(full); r[f"{h // 12}年內_遇到比例"] = n_hit / len(full) if len(full) else np.nan
        out.append(r)
    return pd.DataFrame(out)


def cagr_of(v0, v1, days):
    if v1 <= 0:
        return -1.0
    return (v1 / v0) ** (DAYS_YEAR / days) - 1.0


def growth(d):
    """R12 成長腿描述＋R11 對照；R13 資金費、最深跌幅。"""
    dates = d["dates"]; starts = start_indices(dates); S = len(starts); T = len(dates)
    close, spot = d["close"], d["spot"]
    g_rows, roll_rows = [], []
    for rebal in REBALS:
        rm = rebal_mask(dates, rebal)
        st = np.tile(starts, len(ES)); Lv = np.repeat([E - 1 for E in ES], S)
        liq, eq, fund, fee = engine(close, d["mlow"], d["mclose"], d["fsum"], rm, st, Lv, np.full(len(st), GROWTH_MMR), np.full(len(st), COST_SIDE), want_eq=True)
        for ei, E in enumerate(ES):
            for j, s in enumerate(starts):
                k = ei * S + j
                usd = eq[k, s:] * close[s:]                     # 美元權益
                v0 = 1.0 * close[s]
                rec = {"coin": d["sym"], "E": E, "rebal": rebal, "start": dates[s]}
                for h in list(HORIZ) + ["end"]:
                    te = T - 1 if h == "end" else (np.searchsorted(dates, months_add(dates[s], h)) if months_add(dates[s], h) <= W_END else None)
                    if te is None:
                        rec[f"贏現貨_{h}"] = np.nan; continue
                    c10 = eq[k, te] * close[te] / v0; sp = spot[te] / spot[s]
                    rec[f"C10倍數_{h}"] = c10; rec[f"現貨倍數_{h}"] = sp; rec[f"贏現貨_{h}"] = float(c10 > sp); rec[f"幣數_{h}"] = eq[k, te]
                rec["強平日"] = dates[liq[k]] if liq[k] >= 0 else ""
                roll_rows.append(rec)
                if j == 0:                                       # 窗首主窗
                    days = (pd.Timestamp(dates[-1]) - pd.Timestamp(dates[s])).days
                    with np.errstate(divide="ignore", invalid="ignore"):
                        rc = usd[1:] / np.concatenate([[v0], usd[1:-1]]) - 1.0
                    rs = spot[s + 1:] / spot[s:-1] - 1.0
                    eqc = np.concatenate([[1.0], usd[1:] / v0])
                    with np.errstate(divide="ignore", invalid="ignore"):
                        mdd = float(np.nanmin(eqc / np.maximum.accumulate(eqc) - 1.0))
                        spc = spot[s:] / spot[s]; smdd = float(np.min(spc / np.maximum.accumulate(spc) - 1.0))
                        if liq[k] < 0:
                            ld = float(np.mean(np.log1p(rc) - np.log1p(rs)) * DAYS_YEAR)
                        else:
                            ld = np.nan
                    sv = pd.Series(eqc, index=pd.to_datetime(dates[s:])); ss = pd.Series(spc, index=pd.to_datetime(dates[s:]))
                    ye = sv.groupby(sv.index.year).last(); ye_s = ss.groupby(ss.index.year).last()
                    yr = ye / ye.shift(1).fillna(1.0) - 1.0; yr_s = ye_s / ye_s.shift(1).fillna(1.0) - 1.0
                    if liq[k] < 0 and len(yr) > 1:
                        best = int(yr.idxmax())
                        keep = np.asarray(sv.index.year[1:] != best)
                        rr = rc[keep]; ex_best = float(np.prod(1 + rr) ** (DAYS_YEAR / len(rr)) - 1.0)
                    else:
                        best, ex_best = None, np.nan
                    g_rows.append({"coin": d["sym"], "E": E, "rebal": rebal, "窗首": dates[s], "窗尾": dates[-1], "天數": days,
                                   "強平日": dates[liq[k]] if liq[k] >= 0 else "", "美元年化": cagr_of(v0, usd[-1], days),
                                   "現貨年化": cagr_of(spot[s], spot[-1], days), "期末幣數": float(eq[k, -1]),
                                   "年化日對數報酬差": ld, "最大回落": mdd, "現貨最大回落": smdd,
                                   "逐年": {int(a): round(float(b), 4) for a, b in yr.items()}, "現貨逐年": {int(a): round(float(b), 4) for a, b in yr_s.items()},
                                   "最好一年": best, "去掉最好一年後年化": ex_best,
                                   "累計資金費（幣）": float(fund[k]), "累計手續費（幣）": float(fee[k])})
    # R13
    desc = {"coin": d["sym"]}
    for basis in BASES:
        low = d["mlow"] if basis == "mark" else d["tlow"]
        dd1 = low[1:] / close[:-1] - 1.0; i = int(np.argmin(dd1))
        desc[f"一日內最深_{basis}"] = float(dd1[i]); desc[f"一日內最深日_{basis}"] = dates[i + 1]
        mf = [i for i, x in enumerate(dates) if x[8:10] == "01"]
        worst, wd = 0.0, ""
        for a, b in zip(mf, mf[1:] + [T - 1]):
            if b > a:
                v = float(low[a + 1:b + 1].min() / close[a] - 1.0)
                if v < worst:
                    worst, wd = v, dates[a][:7]
        desc[f"一月內最深_{basis}"] = worst; desc[f"一月內最深月_{basis}"] = wd
    yrs = pd.Series(d["fsum"][1:], index=pd.to_datetime(dates[1:]))
    fy = yrs.groupby(yrs.index.year).agg(["sum", "count"])
    desc["資金費逐年_年化Σrate"] = {int(y): round(float(r["sum"] * DAYS_YEAR / r["count"]), 5) for y, r in fy.iterrows()}
    desc["資金費全窗_年化Σrate"] = float(d["fsum"][1:].sum() * DAYS_YEAR / (T - 1))
    desc["資金費0筆的日子"] = [dates[i] for i in range(1, T) if d["fcnt"][i] == 0]
    desc["資金費非3筆的日子數"] = int(sum(1 for i in range(1, T) if d["fcnt"][i] != 3))
    desc["資金費每日筆數分布"] = {int(k): int(v) for k, v in pd.Series(d["fcnt"][1:]).value_counts().sort_index().items()}
    return g_rows, roll_rows, desc


# ───────────────────────── --check：抽樣逐日重算 ─────────────────────────
def sample_check(data, P):
    rng = np.random.default_rng(SEED)
    keys = P[P["cost_mult"] == 1.0][["coin", "E", "rebal", "basis", "MMR", "start"]].drop_duplicates().reset_index(drop=True)
    pick = list(rng.choice(len(keys), 8, replace=False))
    liqd = P[(P["cost_mult"] == 1.0) & (P["liq_date"] != "") & (P["rebal"] == "monthly") & (P["basis"] == "mark") & (P["MMR"] == 0.01)]
    out = []; trace = None
    rows = [keys.iloc[i].to_dict() for i in pick]
    if len(liqd):
        r0 = liqd.iloc[int(rng.integers(len(liqd)))]
        rows.append({k: r0[k] for k in ["coin", "E", "rebal", "basis", "MMR", "start"]})
    for r in rows:
        d = data[r["coin"]]; dates = d["dates"]; s = int(np.flatnonzero(dates == r["start"])[0])
        low = (d["mlow"] if r["basis"] == "mark" else d["tlow"])[s:]
        rm = rebal_mask(dates, r["rebal"])[s:]
        lq_ref, eq_ref, tr = ref_path(d["close"][s:], low, d["mclose"][s:], d["fbd"][s:], rm, r["E"], r["MMR"], COST_SIDE, trace=True)
        lq_v, eq_v, _, _ = engine(d["close"], (d["mlow"] if r["basis"] == "mark" else d["tlow"]), d["mclose"], d["fsum"], rebal_mask(dates, r["rebal"]),
                                  np.array([s]), np.array([r["E"] - 1]), np.array([r["MMR"]]), np.array([COST_SIDE]), want_eq=True)
        ev = eq_v[0, s:]; diff = float(np.max(np.abs(np.array(eq_ref) - ev)))
        prow = P[(P["coin"] == r["coin"]) & (P["E"] == r["E"]) & (P["rebal"] == r["rebal"]) & (P["basis"] == r["basis"]) & (P["MMR"] == r["MMR"]) & (P["cost_mult"] == 1.0) & (P["start"] == r["start"])].iloc[0]
        ld_ref = dates[s + lq_ref] if lq_ref >= 0 else ""; ld_v = dates[lq_v[0]] if lq_v[0] >= 0 else ""
        ok = (ld_ref == ld_v == prow["liq_date"]) and diff < 1e-9
        out.append({**{k: (float(v) if isinstance(v, (np.floating,)) else v) for k, v in r.items()}, "參考實作強平日": ld_ref, "向量引擎強平日": ld_v,
                    "地圖csv強平日": prow["liq_date"], "權益路徑最大差": diff, "一致": bool(ok)})
        if lq_ref >= 0 and trace is None:
            k = lq_ref
            trace = {"路徑": {k2: (float(v) if isinstance(v, (np.floating,)) else v) for k2, v in r.items()},
                     "逐日（強平前 5 天到強平日）": [{**x, "date": dates[s + x["t"]]} for x in tr[max(0, k - 6):k]]}
    return out, trace


# ───────────────────────── 網頁 ─────────────────────────
def pct(x, nd=0):
    return "—" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x * 100:.{nd}f}%"


def dayfmt(x):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    x = int(x)
    return f"{x} 天（約 {x / 30.44:.0f} 個月）" if x < 730 else f"{x} 天（約 {x / 365.25:.1f} 年）"


def rng_txt(vals, f):
    v = [x for x in vals if not (isinstance(x, float) and math.isnan(x))]
    if not v:
        return "—"
    a, b = f(min(v)), f(max(v))
    return a if a == b else f"{a}～{b}"


def build_html(meta, S, pooled, G, R, D, fx, chk):
    e = html.escape
    css = """
:root{--bg:#fbfaf7;--fg:#1d1d1b;--mut:#6b6a66;--card:#ffffff;--line:#e4e1da;--acc:#9a3412;--accbg:#fff1e8;--ok:#166534;--warn:#b45309}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#161615;--fg:#ecebe7;--mut:#a3a19b;--card:#1f1f1d;--line:#34332f;--acc:#fb923c;--accbg:#2a1d14;--ok:#4ade80;--warn:#fbbf24}}
:root[data-theme="dark"]{--bg:#161615;--fg:#ecebe7;--mut:#a3a19b;--card:#1f1f1d;--line:#34332f;--acc:#fb923c;--accbg:#2a1d14;--ok:#4ade80;--warn:#fbbf24}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.65 -apple-system,"PingFang TC","Noto Sans TC","Microsoft JhengHei",sans-serif}
main{max-width:860px;margin:0 auto;padding:20px 16px 60px}h1{font-size:1.45rem;margin:.2em 0 .3em}h2{font-size:1.15rem;margin:1.8em 0 .5em;border-top:1px solid var(--line);padding-top:1em}
h3{font-size:1rem;margin:1.2em 0 .3em}.sub{color:var(--mut);font-size:.88rem}.lead{background:var(--accbg);border-left:4px solid var(--acc);padding:12px 14px;border-radius:6px;margin:14px 0}
.lead b{color:var(--acc)}.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 14px;margin:10px 0}
.tw{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:8px 0}table{border-collapse:collapse;font-size:.86rem;min-width:100%}
th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:right;white-space:nowrap}th:first-child,td:first-child{text-align:left}
th{color:var(--mut);font-weight:600}.no{color:var(--warn);font-weight:600}.ok{color:var(--ok)}ul{padding-left:1.2em}li{margin:.25em 0}
.small{font-size:.84rem;color:var(--mut)}.tag{display:inline-block;font-size:.75rem;border:1px solid var(--line);border-radius:10px;padding:0 7px;color:var(--mut)}
"""
    h = [f"<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>幣本位強平地圖</title><style>{css}</style></head><body><main>"]
    h.append("<h1>幣本位做多放大：強平地圖</h1>")
    h.append(f"<div class='sub'>PREREGC10 v1（甲案：確定性描述，N＝0）｜回測線｜資料 main {SHA[:10]}｜窗尾 {W_END}｜讀法寫死 {FROZEN}｜產出 {e(meta['產出時間'])}</div>")
    # 結論
    lines = []
    for E in ES:
        p = pooled[E]
        lines.append(f"<li><b>E＝{E:g}</b>（合約名目＝保證金的 {E - 1:g} 倍）：從任一月初開始，<b>{p['比例']}</b> 的起點在窗尾前遇到強平；遇到的人，最慢 <b>{p['最慢']}</b> 就遇到第一次。</li>")
    h.append("<div class='lead'><b>結論（主格：每月再平衡、標記價日低；維持保證金率 0.5～2% 三值）</b><ul>" + "".join(lines) + "</ul>"
             "<div class='small'>6 幣月初起點合併。比例的範圍＝維持保證金率 0.5%～2%。⛔ 這是歷史描述，不是安全倍數；未來跌幅可以比窗內更深。</div></div>")
    h.append("<div class='card small'>" + tier_note_html() + "</div>")
    h.append("<div class='card'><b>這在算什麼</b><br>手上的幣全放進幣本位合約錢包當保證金，再開同一個幣的永續多單。用 <b>E</b>＝對美元的總曝險表示：合約介面上的「1 倍」加上同幣保證金，對美元其實是 <b>E＝2</b>。"
             "理想上 E＝2 跌 50% 歸零、E＝3 跌 33%；但算進維持保證金、手續費、資金費之後，<b>實際強平點會更早</b>，下面全部用實際強平價。</div>")
    # 每個 E 的逐幣表
    h.append("<h2>一、每個 E：逐幣強平地圖（主格）</h2><div class='small'>每月再平衡、標記價日低。「比例」＝月初起點中，窗尾前遇到強平的比例；三個數字＝維持保證金率 0.5%／1%／2%。天數＝從起點到第一次強平。</div>")
    for E in ES:
        h.append(f"<h3>E＝{E:g}</h3><div class='tw'><table><tr><th>幣</th><th>起點</th><th>遇到比例</th><th>最快</th><th>最慢</th><th>1 年內</th><th>4 年內</th><th>最常見強平日</th></tr>")
        for c in COINS:
            g = S[(S.coin == c) & (S.E == E) & (S.rebal == "monthly") & (S.basis == "mark") & (S.cost_mult == 1.0)].sort_values("MMR")
            h.append(f"<tr><td>{c}</td><td>{int(g['月初起點數'].iloc[0])}</td><td>{'／'.join(pct(x) for x in g['遇到比例'])}</td>"
                     f"<td>{rng_txt(list(g['最快天數']), lambda x: str(int(x)) + ' 天')}</td><td>{rng_txt(list(g['最慢天數']), lambda x: str(int(x)) + ' 天')}</td>"
                     f"<td>{'／'.join(pct(x) for x in g['1年內_遇到比例'])}</td><td>{'／'.join(pct(x) for x in g['4年內_遇到比例'])}</td>"
                     f"<td>{e(g[g.MMR == 0.01]['強平日（出現次數前三）'].iloc[0].split('；')[0] or '—')}</td></tr>")
        h.append("</table></div>")
    # 再平衡 × 價格口徑
    h.append("<h2>二、再平衡方式、價格口徑</h2><div class='small'>6 幣月初起點合併，遇到強平的比例（維持保證金率 1%；括號＝0.5%～2% 範圍）。</div>")
    h.append("<div class='tw'><table><tr><th>E</th><th>再平衡</th><th>標記價日低</th><th>成交價日低</th><th>最慢（標記價）</th></tr>")
    for E in ES:
        for rb in REBALS:
            cells = []
            for b in BASES:
                v = [pooled_ratio(S, E, rb, b, m) for m in MMRS]
                cells.append(f"{pct(v[1][0])}（{pct(min(x[0] for x in v))}～{pct(max(x[0] for x in v))}）")
            mx = pooled_ratio(S, E, rb, "mark", 0.01)[1]
            h.append(f"<tr><td>{E:g}</td><td>{REBAL_ZH[rb]}</td><td>{cells[0]}</td><td>{cells[1]}</td><td>{dayfmt(mx)}</td></tr>")
    h.append("</table></div><div class='small'>不再平衡＝口數固定，曝險隨價格漂移；它最依賴進場時點，單一起點的結果不能讀成一般結論。</div>")
    # 窗首
    h.append("<h2>三、窗首一條（各幣第一天建倉、抱到窗尾）</h2><div class='small'>維持保證金率 0.5%／1%／2% 下的第一次強平日（— ＝到窗尾沒有）。</div>")
    h.append("<div class='tw'><table><tr><th>幣（窗首）</th><th>E</th><th>不再平衡</th><th>每月</th><th>每日</th><th>每月・成交價</th></tr>")
    for c in COINS:
        for E in ES:
            cells = []
            for rb, b in (("none", "mark"), ("monthly", "mark"), ("daily", "mark"), ("monthly", "trade")):
                g = S[(S.coin == c) & (S.E == E) & (S.rebal == rb) & (S.basis == b) & (S.cost_mult == 1.0)].sort_values("MMR")
                ds = [x or "—" for x in g["窗首強平日"]]
                cells.append(ds[0] if len(set(ds)) == 1 else "／".join(ds))
            w0 = S[(S.coin == c)].iloc[0]["窗首起點"]
            h.append(f"<tr><td>{c}（{w0}）</td><td>{E:g}</td>" + "".join(f"<td>{x}</td>" for x in cells) + "</tr>")
    h.append("</table></div>")
    # 實際 vs 理想
    h.append("<h2>四、實際強平點比理想值早多少（建倉當下）</h2><div class='small'>只含維持保證金與建倉手續費；之後每付一次資金費，強平點還會再往上移（正費率時）。</div>")
    h.append("<div class='tw'><table><tr><th>E</th><th>理想：跌多少歸零</th><th>實際 m＝0.5%</th><th>m＝1%</th><th>m＝2%</th></tr>")
    for E in ES:
        L = E - 1
        cells = [pct(1 - L * (1 + m) / (1 - COST_SIDE * L + L), 2) for m in MMRS]
        h.append(f"<tr><td>{E:g}</td><td>{pct(1 / E, 2)}</td>" + "".join(f"<td>{x}</td>" for x in cells) + "</tr>")
    h.append("</table></div>")
    # 成長腿
    h.append("<h2>五、成長腿（只描述，不判）</h2><div class='small'>窗首起、每月再平衡、標記價、維持保證金率 2%、手續費 ×1。美元年化對現貨年化；期末幣數＝期初 1 顆變成幾顆。⛔ 不比較好壞；依登錄 §四，這一腿的差異遠小於可測門檻。</div>")
    h.append("<div class='tw'><table><tr><th>幣</th><th>E</th><th>美元年化</th><th>現貨年化</th><th>期末幣數</th><th>最大回落</th><th>現貨回落</th><th>強平</th></tr>")
    for c in COINS:
        for E in ES:
            g = G[(G.coin == c) & (G.E == E) & (G.rebal == "monthly")].iloc[0]
            h.append(f"<tr><td>{c}</td><td>{E:g}</td><td>{pct(g['美元年化'], 1)}</td><td>{pct(g['現貨年化'], 1)}</td><td>{g['期末幣數']:.2f}</td>"
                     f"<td>{pct(g['最大回落'], 1)}</td><td>{pct(g['現貨最大回落'], 1)}</td><td>{g['強平日'] or '—'}</td></tr>")
    h.append("</table></div>")
    h.append("<div class='small'>滾動起點（每月再平衡）：抱滿 1／2／4 年時，C10 美元權益高於現貨的起點比例（⛔ 這不是勝率）。</div>")
    h.append("<div class='tw'><table><tr><th>幣</th><th>E</th><th>1 年</th><th>2 年</th><th>4 年</th><th>抱到窗尾</th></tr>")
    for c in COINS:
        for E in ES:
            g = R[(R.coin == c) & (R.E == E) & (R.rebal == "monthly")]
            g = g.iloc[1:]  # 只用月初起點
            cells = [f"{pct(g[f'贏現貨_{hh}'].mean())}（{int(g[f'贏現貨_{hh}'].notna().sum())}）" for hh in list(HORIZ) + ["end"]]
            h.append(f"<tr><td>{c}</td><td>{E:g}</td>" + "".join(f"<td>{x}</td>" for x in cells) + "</tr>")
    h.append("</table></div><div class='small'>括號＝可算的起點數。</div>")
    # 描述：跌幅、資金費
    h.append("<h2>六、窗內最深跌幅與資金費</h2><div class='tw'><table><tr><th>幣</th><th>一日內（標記／成交）</th><th>一月內（標記／成交）</th><th>資金費年化Σ</th></tr>")
    for dd in D:
        h.append(f"<tr><td>{dd['coin']}</td><td>{pct(dd['一日內最深_mark'], 1)}／{pct(dd['一日內最深_trade'], 1)}<br><span class='small'>{dd['一日內最深日_mark']}／{dd['一日內最深日_trade']}</span></td>"
                 f"<td>{pct(dd['一月內最深_mark'], 1)}／{pct(dd['一月內最深_trade'], 1)}<br><span class='small'>{dd['一月內最深月_mark']}／{dd['一月內最深月_trade']}</span></td>"
                 f"<td>{pct(dd['資金費全窗_年化Σrate'], 2)}</td></tr>")
    h.append("</table></div><div class='small'>跌幅從再平衡點（前一日收盤／月初收盤）起算。資金費年化Σ＝對名目；正＝多方付。對保證金約再乘 L（E−1）。</div>")
    # 先驗
    h.append("<h2>七、先驗對答</h2><div class='card'><ul>" + "".join(f"<li>{e(x)}</li>" for x in meta["先驗對答"]) + "</ul></div>")
    # fixture、check
    h.append("<h2>八、驗證</h2><div class='tw'><table><tr><th>案</th><th>引擎</th><th>參考</th><th>反例</th><th>反例結果</th></tr>")
    for r in fx:
        h.append(f"<tr><td>{e(r['案'])}</td><td>{r['向量引擎']}</td><td>{r['參考實作']}</td><td style='white-space:normal'>{e(r['反例'])}</td><td>{e(r['反例結果'])}</td></tr>")
    h.append(f"</table></div><div class='small'>抽樣逐日重算（另一支逐筆迴圈）：{chk['一致數']}／{chk['抽樣數']} 條路徑強平日與權益完全一致。</div>")
    # 限制
    h.append("<h2>九、讀的時候要注意</h2><ul>"
             "<li>" + tier_note_html() + "</li>"
             "<li>強平只用日低判斷，日內先跌後漲也算；資金費用前一日標記價收盤近似；" + LIQ_FEE_NOTE + "</li>"
             "<li>口數取整忽略（BTC 一口 100 美元，小帳戶做不到精確 E）。</li>"
             "<li>模型外風險：交易所倒閉、自動減倉、插針、規格或分級變動、提幣限制。</li>"
             "<li>⛔ 歷史沒爆不等於未來不會；本頁不提供任何槓桿或開倉建議。</li></ul>")
    h.append("<h2>十、執行者補的讀法</h2><ul class='small'>" + "".join(f"<li>{e(x)}</li>" for x in meta["執行者補"]) + "</ul>")
    h.append("</main></body></html>")
    return "\n".join(h)


def pooled_ratio(S, E, rb, b, m):
    g = S[(S.E == E) & (S.rebal == rb) & (S.basis == b) & (S.MMR == m) & (S.cost_mult == 1.0)]
    n = g["月初起點數"].sum(); k = g["遇到強平起點數"].sum()
    return (k / n if n else np.nan, float(g["最慢天數"].max()) if g["最慢天數"].notna().any() else np.nan)


EXEC_SUPPLIED = [
    "R1 窗尾＝三份共同最後一天＝2026-09-30（寫死時誤記 10-02，執行時依同一規則更正）",
    "R3 資金費換幣的標記價＝前一日標記價收盤（日 K 沒有逐筆標記價）",
    "R4 估值與再平衡用成交價收盤；價格口徑只換強平用的日低",
    "R5 強平公式：逐倉幣本位標準式 Lp＝N(1+m)/(W+N/Pe)；強平清算費在強平那一刻從剩餘保證金扣、不改觸發時點，強平期本來就記 −100%，不影響（seq294 §三 補記）",
    "R7 再平衡新名目以扣費前權益定；窗尾不平倉、不付平倉費",
    "R8 每月再平衡＝每個 UTC 月份第一天收盤",
    "R9 月初起點到 2026-09-01 為止；另跑窗首一條",
    "R10「最慢多久遇到第一次強平」＝遇到強平的起點中等最久那條的天數；沒遇到的只說到窗尾為止沒有",
    "R12 成長腿用維持保證金率 2%（三值中最保守）",
]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    t0 = time.time()
    ok, fx = run_fixtures()
    for r in fx:
        print(f"[fixture {r['案']}] 引擎 {r['向量引擎']}｜參考 {r['參考實作']}｜反例「{r['反例']}」⇒ {r['反例結果']}")
    assert ok, "⛔ fixture 沒全過，停"
    os.makedirs(OUT, exist_ok=True)
    data = {s: load(s) for s in COINS}
    for s in COINS:
        d = data[s]
        print(f"[{s}] 窗 {d['dates'][0]}～{d['dates'][-1]}（{len(d['dates'])} 天）｜資金費 {d['fund_first']}～{d['fund_last']} UTC 共 {d['fund_rows_total']} 筆｜起點 {len(start_indices(d['dates']))}", flush=True)
    paths = []
    for s in COINS:
        paths += run_coin(data[s]); print(f"  地圖 {s} 完成 {time.time() - t0:.0f}s", flush=True)
    P = pd.DataFrame(paths)
    if a.check:
        okf, fx2 = ok, fx
        chk_rows, trace = sample_check(data, P)
        chk = {"讀法寫死": FROZEN, "fixture全過": okf, "fixture": fx2, "抽樣數": len(chk_rows), "一致數": int(sum(r["一致"] for r in chk_rows)),
               "抽樣": chk_rows, "逐日重算一段強平": trace, "種子": SEED}
        json.dump(chk, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
        print(f"[check] 抽樣 {chk['一致數']}／{chk['抽樣數']} 一致")
        if trace:
            for x in trace["逐日（強平前 5 天到強平日）"]:
                print("   ", x["date"], f"W={x['W']:.6f} N={x['N']:.4f} Pe={x['Pe']:.6g} Lp={x['Lp']:.6g} low={x['low']:.6g} 強平={x['強平']}")
        assert chk["一致數"] == chk["抽樣數"], "⛔ 抽樣重算不一致"
        return
    S = summarize(P)
    P[P["cost_mult"] == 1.0].to_csv(os.path.join(OUT, "map_starts.csv"), index=False)
    S.to_csv(os.path.join(OUT, "map_summary.csv"), index=False)
    G, Rr, D = [], [], []
    for s in COINS:
        g, r, dd = growth(data[s]); G += g; Rr += r; D.append(dd)
    G = pd.DataFrame(G); R = pd.DataFrame(Rr)
    G.to_csv(os.path.join(OUT, "growth_window.csv"), index=False); R.to_csv(os.path.join(OUT, "growth_rolling.csv"), index=False)
    pooled = {}
    for E in ES:
        v = [pooled_ratio(S, E, "monthly", "mark", m) for m in MMRS]
        pooled[E] = {"比例": rng_txt([x[0] for x in v], lambda x: pct(x)), "最慢": rng_txt([x[1] for x in v], lambda x: dayfmt(x)),
                     "逐MMR": {f"{m:.1%}": {"比例": x[0], "最慢天數": x[1]} for m, x in zip(MMRS, v)}}
    # 先驗對答（窗首一條，每月再平衡）
    def liq_coins(E, rb, b, m):
        g = S[(S.E == E) & (S.rebal == rb) & (S.basis == b) & (S.MMR == m) & (S.cost_mult == 1.0)]
        return [c for c, x in zip(g.coin, g["窗首強平日"]) if x]
    pri = []
    c1 = {m: liq_coins(3.0, "monthly", "mark", m) for m in MMRS}
    pri.append("① 押 E＝3 每月再平衡 ≥4 幣窗內強平：" + "；".join(f"m={m:.1%} {len(v)} 幣{('（' + '、'.join(v) + '）') if v else ''}" for m, v in c1.items()) + "（窗首一條、標記價）⇒ " + ("中" if all(len(v) >= 4 for v in c1.values()) else ("未中" if all(len(v) < 4 for v in c1.values()) else "依 m 而定")))
    c2t = {m: liq_coins(2.0, "monthly", "trade", m) for m in MMRS}; c2m = {m: liq_coins(2.0, "monthly", "mark", m) for m in MMRS}
    pri.append("② 押 E＝2 成交價 ≥2 幣強平、標記價較少：成交價 " + "；".join(f"m={m:.1%} {len(v)} 幣{('（' + '、'.join(v) + '）') if v else ''}" for m, v in c2t.items())
               + "｜標記價 " + "；".join(f"m={m:.1%} {len(v)} 幣" for m, v in c2m.items()) + "（窗首一條、每月再平衡）⇒ "
               + ("中" if all(len(c2t[m]) >= 2 and len(c2m[m]) < len(c2t[m]) for m in MMRS)
                  else ("部分中：成交價 ≥2 幣成立；「標記價較少」只在 " + ("、".join(f"m={m:.1%}" for m in MMRS if len(c2m[m]) < len(c2t[m])) or "無任何 m") + " 成立"
                        if all(len(c2t[m]) >= 2 for m in MMRS) else ("未中" if all(len(c2t[m]) < 2 for m in MMRS) else "部分中"))))
    c3 = {m: liq_coins(1.5, "none", "mark", m) for m in MMRS}
    pri.append("③ 押 E＝1.5 不再平衡至少 1 幣（SOL 或 DOGE）強平：" + "；".join(f"m={m:.1%} {len(v)} 幣{('（' + '、'.join(v) + '）') if v else ''}" for m, v in c3.items()) + "（窗首一條、標記價）⇒ "
               + ("中" if all(any(x in ("SOL", "DOGE") for x in v) for v in c3.values()) else ("未中" if all(not v for v in c3.values()) else "部分中")))
    pri.append("④ 押成長腿沒有任何一格出口②：甲案成長腿只描述、不判、不計 N ⇒ 沒有出口可對；與登錄 §四 構造算術一致（不判）")
    meta = {"登錄": "PREREGC10 幣本位做多放大 v1 sha8902cc2e6b68bf17", "裁定": "seq289 §二 甲案（N＝0）", "讀法寫死": FROZEN,
            "資料commit": SHA, "窗尾": W_END, "產出時間": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M（台北）"),
            "E": ES, "再平衡": REBALS, "價格口徑": BASES, "維持保證金率": MMRS, "官方最低一級": {k: v[0] for k, v in TIER1.items()}, "主格標示": "官方分級表最低一級（現值口徑）", "強平清算費": LIQ_FEE, "手續費單邊": COST_SIDE, "成本倍數": CMULTS,
            "每口面額": FACE, "各幣窗": {s: [data[s]["dates"][0], data[s]["dates"][-1], len(data[s]["dates"])] for s in COINS},
            "各幣資金費": {s: {"筆數": data[s]["fund_rows_total"], "起": data[s]["fund_first"], "迄": data[s]["fund_last"]} for s in COINS},
            "每個E總結（主格：每月、標記價、月初起點6幣合併）": {str(E): pooled[E] for E in ES},
            "先驗對答": pri, "描述": D, "fixture": fx, "執行者補": EXEC_SUPPLIED, "耗時秒": round(time.time() - t0, 1)}
    chk_path = os.path.join(OUT, "check.json")
    chk = json.load(open(chk_path, encoding="utf-8")) if os.path.exists(chk_path) else {"一致數": "—", "抽樣數": "—"}
    json.dump(meta, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(OUT, "幣本位做多放大_強平地圖.html"), "w", encoding="utf-8").write(build_html(meta, S, pooled, G, R, D, fx, chk))
    for E in ES:
        print(f"E={E}: 比例 {pooled[E]['比例']}｜最慢 {pooled[E]['最慢']}")
    for x in pri:
        print(x)
    print(f"完成 {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
