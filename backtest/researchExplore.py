# -*- coding: utf-8 -*-
"""PREREG探索批 seq2【探索段】——回測線落地（⛔ 探索段不下結論、⛔ 不計 N；只產「線索」與排名）。

登錄：台股策略線 PREREG探索批 seq2（sha 1697c62b04951f2f，2026-09-25 22:19）；裁定線 seq177 §二（編號、四處補）、seq181（核准開跑）。
⛔ 確認段（確認窗 A 2023-01～2026-08、確認窗 B 2012-06～2014-12、前瞻 C）本程式【一律不跑】。

    python3 backtest/researchExplore.py [--procs 1] [--out backtest/resultsExplore]
            [--stage sig|all] [--reps 200] [--s0 1000] [--perturb SEED] [--leak]

═══ 切點（登錄 §一；裁定 seq177 §二①）═══
  CUT ＝ 2022-12-30。⭐ 本程式在【讀進來的那一刻】就把資料切在 CUT：
   ① 交易日曆讀進來立刻截到 ≤ CUT ⇒ 之後所有 reindex(cal) 都自動丟掉 CUT 以後的列（D.load_stock、P4F.load_inst、
      tradability.one、面板 RP4.build_panel 全走這一份日曆）；引擎拿到的價格陣列長度 ＝ CUT 的日曆位置 ＋ 1
   ② 還原因子【as-of CUT】：只用事件日 ≤ CUT 的因子（有效因子 ＝ factor_official 有值用它、否則 factor），
      自己反向連乘重建 cum_factor（⚠ 資料檔的 cum_factor 已乘進 2023 以後的除權息 ⇒ 不直接用）；
      與全期還原價相比只差一個逐檔常數倍（比值不變；實測與檔內 cum_factor 相對差 ≤ 3e-7）
   ③ 月營收：期別的可得日（research34.rebalance_dates，次月 10 日後第一個交易日）落在截斷日曆之外 ⇒ 該期不存在
   ④ 官方下市日只收 ≤ CUT 的（之後的日期是 CUT 當時不知道的事）
   ⑤ 探索段在 CUT 收盤結算：排程出場日 ＞ CUT 的部位【不出場】、留在持股裡按 CUT 收盤計值（引擎 MTM 權益）；
      這些列的 xpos 照排程寫（＞ 陣列尾，只是一個位置數，⛔ 引擎到不了）；g 欄寫 CUT 收盤 ÷ 進場開盤 − 1
      （引擎只拿它算 wins 計數，⛔ 不進權益）
  ⭐ 切點 fixture（登錄要求）：backtest/selftest_explore.py
      --perturb SEED：把資料檔裡 CUT 以後的列（價、量、法人、融資、本益比、還原事件、月營收、日曆、上市／下市日期）
      全改成亂數或亂刪 ⇒ 探索段所有輸出要逐位元不變；--leak：故意讓 F05 在 2022-12-01 量測日讀 2023-01-03 的收盤
      ⇒ 同一個 perturb 要把它抓出來（鑑別力）

═══ 共同引擎（登錄 §二；⛔ 與 W1 同，一字不動）═══
  資料 edc6f8002f 快照（researchH2 把 D.DATA 指過去）；gate3；delist on；還原價；量測日＝每月第一個交易日；
  母體 ＝ W1 eligible（liq_ok ∧ bars_ok ∧ inst_ok；面板用 RP4.build_panel【同一支】在截斷日曆上重建）；⛔ 不用門檻B 任何條件
  候選母體 ＝ P7.build_sig_gate_b(…, signal="ALL")（＋⑤ 的尾段列）⇒ 再切條件前 10%
  引擎 research11.simulate_mtm：H120、n_slots 8、pick=None、cash_mode="zero"、成本 0.585%、tradable＋delist（同 researchAFC.sim）
  種子 102000＋r：每格 200 顆；S0 1,000 顆；判讀窗 [2017-03-02, 2022-12-30]（P12.win_read；訊號起點 P12.START＝2017-01-01，同 W1 窗頭帶倉）
  0050 錨：同窗自算（R13.window_stats，未捨入）

═══ 18 個條件（登錄 §三；分數越大越前面）═══
  量測日 T（每月第一個交易日，收盤後）；價格類在【還原收盤、交易日曆上 ffill】的序列上數（同 P4 面板 ret_20／ret_120／vol60 的慣例）
  F01 月營收年增率      ＝ 當月營收 ÷ 去年當月營收 − 1（同一筆申報的兩欄；去年 ≤ 0 或缺 ⇒ 缺）
  F02 近三月累計年增率  ＝ Σ當月營收(p−2..p) ÷ Σ去年當月營收(p−2..p) − 1（六個數缺一 ⇒ 缺；分母 ≤ 0 ⇒ 缺）
  F03 月增率            ＝ 營收(p) ÷ 營收(p−1) − 1（p−1 ≤ 0 或缺 ⇒ 缺）
  F04 營收距 24 月最高  ＝ 營收(p) ÷ max(營收 p−24..p−1)（⭐ 同 rev_hi24 的「當期之前 24 期」；有效 < 18 期或 max ≤ 0 ⇒ 缺）
      p ＝ T 當下【可得的最新期別】＝ rebalance_dates(pub_day=10) 的 entry_pos ≤ T 的最後一期（全市場同一期；該股該期缺 ⇒ 缺）
  F05 −(c[T]/c[T−20] − 1)   F06 c[T]/c[T−60] − 1   F07 c[T]/c[T−120] − 1   F08 c[T−20]/c[T−240] − 1
  F09 c[T] ÷ max(c[T−249..T])（250 根滿才算）      F10 c[T] ÷ MA60[T] − 1（60 根滿）
  F11 −std(日報酬 T−59..T，ddof=1)（60 個報酬滿）
  F12 mean(量 T−19..T) ÷ mean(量 T−79..T−20)（量＝成交股數；區間內無成交日 ＝ 0〈七十七〉；分母 0 ⇒ 缺）
  F13 Σ外資淨買超(T−19..T) ÷ Σ成交股數(T−19..T)   F14 投信同式（法人檔當天不在 ⇒ 缺值 seq106 ⇒ 20 日有一天缺就缺）
  F15 −(融資餘額[T] ÷ 融資餘額[T−20] − 1)（as-of、≤ 5 個交易日內的列；T−20 那端 ≤ 0 ⇒ 缺）
  F16 1 ÷ 本益比（本益比空白或 ≤ 0 ⇒ 缺，⛔ 不是 0）  F17 殖利率 yield_pct  F18 1 ÷ 股淨比（≤ 0 ⇒ 缺）
      per 檔 as-of：T 以前最後一列、且 ≤ 5 個交易日內；⭐ 該列欄位空白 ⇒ 缺（⛔ 不往前找上一個非空值）；⛔ per 檔的 close 欄不讀

═══ 候選（登錄 §二）═══
  逐量測日、在 eligible 母體內：單一條件 ⇒ 百分位 ＝ P4F.pct_strict_less（有限值為分母、同值同名次）；
  兩兩 ⇒ 兩條件各自的百分位平均；取前 k ＝ ceil(0.10 × 有效檔數)，依分數遞減、同分依代號遞增

═══ 探索段怎麼挑線索（登錄 §四，寫死）═══
  每格 A＝年化中位、D＝回落中位、比值＝A ÷ |D|；對 0050 同窗：標籤 Q 合格（A ＞ A50 ∧ 比值 ≥ 比值50）／
  R 另列（A ＞ A50 ∧ 比值 ＜ 比值50）／F 不合格（A ≤ A50）⇒ ⭐ 僅作排名參考，⛔ 探索段不是判定
  候選 ＝ A ＞ A50 的格，比值遞減（同比值依格序）；依序取、每個條件最多出現在 2 條線索 ⇒ 取滿 5 條
  運氣基準 S0（同母體每月隨機抽 8 檔 ＝ signal ALL＋pick=None，1,000 顆）⇒「隨機試 171 次最好那一次」的比值分佈
  ⇒ 每條線索的分位；＜ 95 分位 ⇒ 標「與試很多次的運氣分不開」（⛔ 不淘汰）

═══ ⭐ 登錄沒逐字寫、本線選的讀法（⛔ 看任何結果之前寫在這裡；交件逐條列出）═══
  X1 前 10% 的分母 ＝ 該量測日該條件【有效值】的檔數（⛔ 不是 eligible 總檔數）；k ＝ ceil(0.10 × n)
     另一讀法：k ＝ ceil(0.10 × eligible 檔數)、只在有效值裡取
  X2 兩兩組合：任一條件缺 ⇒ 該股該格缺（⛔ 不以單一條件的百分位代替）；百分位各自在自己的有效值內算
     另一讀法：缺的那一邊補 50（P4 面板慣例）
  X3 S0 的「比值分佈」＝ 1,000 顆【逐種子】比值 cagr_s ÷ |mdd_s|；「隨機試 171 次最好那次」＝ 從這 1,000 個裡
     獨立抽 171 個取最大 ⇒ CDF G(x) ＝ F̂(x)^171（精確式；另以 20,000 次抽樣複核）；線索分位 ＝ G(線索比值)
     另一讀法：一次「隨機試」＝ 200 顆 S0 種子的中位比值（與格的統計量同形）⇒ 分佈窄得多、線索分位會高得多
     （⭐ 本線取逐種子那一種：分佈較寬 ⇒ 較多線索被標「與運氣分不開」＝ 保守方向；另一讀法的數字只在 summary 當描述）
  X4 CUT 收盤結算 ＝ 按 CUT 收盤【計值】（MTM，未扣賣出成本；同 W1 在窗尾的讀法）；另一讀法：CUT 收盤強制賣出並扣成本
  X5 12−1 個月報酬 ＝ c[T−20] ÷ c[T−240] − 1（一個月 ＝ 20 根，同 P4 的 ret_20／ret_120）；另一讀法 12 個月 ＝ 250 根
  X6 F04 的 24 期 ＝ 當期之前 24 期（同 rev_hi24）；另一讀法：含當期的 24 期（⇒ 分數 ≤ 1、創新高者全同分）
  X7 F12「20 日前 60 日均量」＝ 最近 20 日之前的那 60 日（T−79..T−20）；另一讀法：截至 T 的 60 日均量
  X8 F01／F02 的去年同期用同一筆申報的「去年當月營收」欄；另一讀法：自己序列 12 期前的「當月營收」
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
import zlib
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchH2 as H2                               # ⭐ D.DATA ⇒ edc6f8002f 快照（唯讀）；os.chdir(~/tw-p17)
D = H2.D
from backtest import research11 as R
from backtest import research13 as R13
from backtest import research34 as R34
from backtest import researchp4 as RP4
from backtest import researchp7 as P7
from backtest import researchp12 as P12
from backtest import p4_features as P4F
from backtest import tradability as T

CUT = pd.Timestamp("2022-12-30")
W0_DATE = "2017-03-02"
START = P12.START                                     # "2017-01-01"（同 W1）
SEED0, REPS, N_S0 = 102000, 200, 1000
COST = 0.00585
TOP = 0.10
MAX_PER_COND, N_CLUES, LUCK_Q = 2, 5, 0.95
N_TRY = 171
LUCK_MC, LUCK_MC_SEED = 20000, 20260925
ASOF_LAG = 5                                          # per／融資 as-of 最多往前 5 個交易日
CONDS = [f"F{i:02d}" for i in range(1, 19)]
CELLS = [(a,) for a in CONDS] + [(a, b) for i, a in enumerate(CONDS) for b in CONDS[i + 1:]]
assert len(CELLS) == 171
LEAK_MEASURE, LEAK_READ = pd.Timestamp("2022-12-01"), "2023-01-03"
OUT_DEFAULT = "backtest/resultsExplore"


def cell_name(c) -> str:
    return "+".join(c)


# ═════════════ 切點：as-of 還原因子（②）═════════════
_ORIG_LOAD_ADJ = D.load_adj


def load_adj_asof(stock_id: str):
    """事件日 ≤ CUT 的還原事件，cum_factor 以有效因子（factor_official 有值用它、否則 factor）反向連乘重建。"""
    a = _ORIG_LOAD_ADJ(stock_id)
    if a is None:
        return None
    a = a[a["date"] <= CUT].copy()
    if a.empty:
        return a.reset_index(drop=True)
    fo = pd.to_numeric(a["factor_official"], errors="coerce") if "factor_official" in a.columns else pd.Series(np.nan, index=a.index)
    fe = fo.where(fo.notna(), pd.to_numeric(a["factor"], errors="coerce")).to_numpy(float)
    if not np.all(np.isfinite(fe)):
        raise SystemExit(f"⛔ {stock_id} 的還原事件有非有限因子（≤ CUT）⇒ 停")
    a["cum_factor"] = np.cumprod(fe[::-1])[::-1]
    return a.reset_index(drop=True)


# ═════════════ 切點 fixture：擾動 CUT 以後的資料（只在 --perturb 時裝上）═════════════
_POST = pd.date_range("2023-01-02", "2026-09-24", freq="B").strftime("%Y-%m-%d").to_numpy()


def install_perturb(seed: int, root: str) -> None:
    orig = pd.read_csv
    root = os.path.abspath(root)
    KEYS = {"date", "stock_id", "name", "market", "period", "產業別", "kind", "event", "note", "fs_quarter", "price_basis"}

    def _rand_col(df, m, col, rng):
        s = df[col]
        n = int(m.sum())
        if pd.api.types.is_integer_dtype(s):
            df.loc[m, col] = rng.integers(1, 10_000_000, n)
        elif pd.api.types.is_float_dtype(s):
            df.loc[m, col] = rng.uniform(0.3, 3000.0, n)
        else:
            num = pd.to_numeric(s[m], errors="coerce")
            if n and num.notna().mean() > 0.5:
                df.loc[m, col] = [f"{x:.2f}" for x in rng.uniform(0.3, 3000.0, n)]

    def wrapped(path, *a, **k):
        df = orig(path, *a, **k)
        p = os.path.abspath(str(path))
        if not p.startswith(root + os.sep):
            return df
        rel = os.path.relpath(p, root).split(os.sep)
        rng = np.random.default_rng([seed, zlib.crc32(p.encode())])
        top, base = rel[0], rel[-1]
        if top in ("stocks", "stocks_inst", "stocks_per", "stocks_margin", "adj") and "date" in df.columns:
            m = df["date"].astype(str).str[:10] > "2022-12-30"
            if m.any():
                df = df.copy()
                for col in df.columns:
                    if col not in KEYS:
                        _rand_col(df, m, col, rng)
                idx = df.index[m.to_numpy()]
                df = df.drop(index=rng.choice(idx, size=int(0.3 * len(idx)), replace=False))
        elif top == "mops" and "period" in df.columns:
            m = df["period"].astype(str) >= "2022-12"
            if m.any():
                df = df.copy()
                for col in df.columns:
                    if col not in KEYS:
                        _rand_col(df, m, col, rng)
        elif top == "meta" and base == "calendar_twse.csv":
            m = df["date"].astype(str).str[:10] > "2022-12-30"
            idx = df.index[m.to_numpy()]
            df = df.drop(index=rng.choice(idx, size=int(0.3 * len(idx)), replace=False))
        elif top == "meta" and base in ("stocks.csv", "delisted.csv"):
            df = df.copy()
            for col in ("first_seen", "last_seen", "delist_date"):
                if col in df.columns:
                    m = df[col].astype(str).str[:10] > "2022-12-30"
                    if m.any():
                        v = rng.choice(_POST, size=int(m.sum()))
                        df.loc[m, col] = v if not pd.api.types.is_datetime64_any_dtype(df[col]) else pd.to_datetime(v)
        return df

    pd.read_csv = wrapped


# ═════════════ 特徵（F05～F18，逐檔）═════════════
_G: dict = {}


def _asof(pos_rows: np.ndarray, vals: np.ndarray, t: int) -> float:
    j = int(np.searchsorted(pos_rows, t, side="right")) - 1
    if j < 0 or t - pos_rows[j] > ASOF_LAG:
        return np.nan
    return float(vals[j])


def _read_dated(path: str, cols: list, cal) -> tuple[np.ndarray, pd.DataFrame] | None:
    """讀 per／融資檔 ⇒ (列的日曆位置, 值)；⛔ 不在截斷日曆裡的列（CUT 以後）直接丟掉。"""
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path, dtype={"date": str}, usecols=["date"] + cols)
    df["date"] = pd.to_datetime(df["date"].str[:10])
    df = df.drop_duplicates("date", keep="last").sort_values("date")
    pos = cal.get_indexer(df["date"])
    keep = pos >= 0
    df = df[keep].copy()
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return pos[keep].astype(int), df.reset_index(drop=True)


def feat_worker(args):
    sid, market, tpos = args
    cal = _G["cal"]; n = len(cal)
    st = D.load_stock(sid, market, cal)
    out = []
    if st is None:
        return out
    df = st.df
    c = df["close"].ffill()
    cv = c.to_numpy(float)
    vol = pd.to_numeric(df["volume"], errors="coerce")
    tr = df["traded"].to_numpy(bool)
    if tr.any():                                     # 〈七十七〉區間內無成交日的量 ＝ 0（同 p4_features.stock_raw）
        i0, i1 = int(np.argmax(tr)), len(tr) - 1 - int(np.argmax(tr[::-1]))
        inside = np.zeros(len(tr), bool); inside[i0:i1 + 1] = True
        vol = vol.where(~(inside & ~tr), 0.0)
    ma60 = c.rolling(60, min_periods=60).mean().to_numpy()
    hi250 = c.rolling(250, min_periods=250).max().to_numpy()
    sd60 = c.pct_change().rolling(60, min_periods=60).std().to_numpy()
    v20 = vol.rolling(20, min_periods=20).mean().to_numpy()
    v60p = vol.rolling(60, min_periods=60).mean().shift(20).to_numpy()
    vs20 = vol.rolling(20, min_periods=20).sum().to_numpy()
    inst = P4F.load_inst(sid, cal)
    fs20 = inst["foreign"].rolling(20, min_periods=20).sum().to_numpy()
    ts20 = inst["trust"].rolling(20, min_periods=20).sum().to_numpy()
    per = _read_dated(os.path.join(D.DATA, "stocks_per", f"{sid}.csv"), ["yield_pct", "per", "pbr"], cal)
    mg = _read_dated(os.path.join(D.DATA, "stocks_margin", f"{sid}.csv"), ["m_balance"], cal)
    leak_c = None
    if _G.get("leak"):
        rp = os.path.join(D.DATA, "stocks", f"{sid}.csv")        # ⛔ 故意的前視（只給鑑別力 fixture 用）：直接讀原始檔、不經截斷日曆
        raw = pd.read_csv(rp, dtype={"date": str}, usecols=["date", "close"])
        hit = raw[raw["date"].str[:10] == LEAK_READ]
        leak_c = float(pd.to_numeric(hit["close"], errors="coerce").iloc[0]) if len(hit) else np.nan

    def at(a, t):
        return float(a[t]) if 0 <= t < n and np.isfinite(a[t]) else np.nan

    def ratio(x, y):
        return x / y if (np.isfinite(x) and np.isfinite(y) and y != 0) else np.nan

    for t in tpos:
        r = {"sid": sid, "pos": int(t)}
        c0 = at(cv, t)
        r["F05"] = -(ratio(c0, at(cv, t - 20)) - 1)
        r["F06"] = ratio(c0, at(cv, t - 60)) - 1
        r["F07"] = ratio(c0, at(cv, t - 120)) - 1
        r["F08"] = ratio(at(cv, t - 20), at(cv, t - 240)) - 1
        r["F09"] = ratio(c0, at(hi250, t))
        r["F10"] = ratio(c0, at(ma60, t)) - 1
        r["F11"] = -at(sd60, t)
        den = at(v60p, t)
        r["F12"] = ratio(at(v20, t), den) if den > 0 else np.nan
        vs = at(vs20, t)
        r["F13"] = ratio(at(fs20, t), vs) if vs > 0 else np.nan
        r["F14"] = ratio(at(ts20, t), vs) if vs > 0 else np.nan
        if mg is not None:
            b1 = _asof(mg[0], mg[1]["m_balance"].to_numpy(float), t)
            b0 = _asof(mg[0], mg[1]["m_balance"].to_numpy(float), t - 20)
            r["F15"] = -(b1 / b0 - 1) if (np.isfinite(b1) and np.isfinite(b0) and b0 > 0) else np.nan
        else:
            r["F15"] = np.nan
        if per is not None:
            pe = _asof(per[0], per[1]["per"].to_numpy(float), t)
            yd = _asof(per[0], per[1]["yield_pct"].to_numpy(float), t)
            pb = _asof(per[0], per[1]["pbr"].to_numpy(float), t)
            r["F16"] = 1.0 / pe if (np.isfinite(pe) and pe > 0) else np.nan
            r["F17"] = yd if np.isfinite(yd) else np.nan
            r["F18"] = 1.0 / pb if (np.isfinite(pb) and pb > 0) else np.nan
        else:
            r["F16"] = r["F17"] = r["F18"] = np.nan
        if leak_c is not None and cal[t] == LEAK_MEASURE:
            raw_t = pd.to_numeric(pd.read_csv(os.path.join(D.DATA, "stocks", f"{sid}.csv"), dtype={"date": str},
                                              usecols=["date", "close"]).set_index("date")["close"], errors="coerce").get(str(cal[t].date()), np.nan)
            r["F05"] = -(leak_c / raw_t - 1) if (np.isfinite(leak_c) and np.isfinite(raw_t) and raw_t > 0) else np.nan
        for k in list(r):
            if k.startswith("F") and not np.isfinite(r[k]):
                r[k] = np.nan
        out.append(r)
    return out


def revenue_feats(cal, keys: pd.DataFrame) -> pd.DataFrame:
    """F01～F04（可得日規則：rebalance_dates pub_day=10 的 entry_pos ≤ T 的最後一期）。keys：pos, sid。"""
    rev, rev_ly, _ = R34.load_revenue()
    per_all = pd.period_range(rev.index.min(), rev.index.max(), freq="M").strftime("%Y-%m")
    rev = rev.reindex(per_all); rev_ly = rev_ly.reindex(per_all)
    rd = R34.rebalance_dates(list(per_all), cal, 10)          # ⭐ 可得日落在截斷日曆外的期別不在 rd 裡（③）
    avail = sorted((e, p) for p, (_, e) in rd.items())
    e_arr = np.array([e for e, _ in avail]); p_arr = [p for _, p in avail]
    pidx = {p: i for i, p in enumerate(per_all)}
    RV = rev.to_numpy(float); RL = rev_ly.to_numpy(float); col = {s: j for j, s in enumerate(rev.columns)}
    rows = []
    for t, sid in zip(keys["pos"], keys["sid"]):
        f = {"pos": int(t), "sid": sid, "F01": np.nan, "F02": np.nan, "F03": np.nan, "F04": np.nan, "rev_period": ""}
        j = int(np.searchsorted(e_arr, t, side="right")) - 1
        if j >= 0 and sid in col:
            p = p_arr[j]; i = pidx[p]; k = col[sid]; f["rev_period"] = p
            x = RV[i, k]
            if np.isfinite(x):
                ly = RL[i, k]
                if np.isfinite(ly) and ly > 0:
                    f["F01"] = x / ly - 1
                if i >= 2:
                    a3, b3 = RV[i - 2:i + 1, k], RL[i - 2:i + 1, k]
                    if np.all(np.isfinite(a3)) and np.all(np.isfinite(b3)) and b3.sum() > 0:
                        f["F02"] = a3.sum() / b3.sum() - 1
                if i >= 1 and np.isfinite(RV[i - 1, k]) and RV[i - 1, k] > 0:
                    f["F03"] = x / RV[i - 1, k] - 1
                if i >= 24:
                    h = RV[i - 24:i, k]; h = h[np.isfinite(h)]
                    if len(h) >= 18 and h.max() > 0:
                        f["F04"] = x / h.max()
        rows.append(f)
    return pd.DataFrame(rows)


# ═════════════ 候選 ═════════════
def select_cells(feat: pd.DataFrame) -> dict:
    """回 {cell: DataFrame(pos, sid)}：逐量測日 top ceil(10% × 有效數)，分數遞減、同分代號遞增。"""
    sel = {c: [] for c in CELLS}
    stats = {c: [] for c in CELLS}
    for t, g in feat.groupby("pos", sort=True):
        g = g.sort_values("sid").reset_index(drop=True)
        pct = {f: P4F.pct_strict_less(g[f]).to_numpy(float) for f in CONDS}
        n_el = len(g)
        for c in CELLS:
            s = pct[c[0]] if len(c) == 1 else (pct[c[0]] + pct[c[1]]) / 2.0     # 任一缺 ⇒ NaN（X2）
            ok = np.isfinite(s)
            nv = int(ok.sum())
            if nv == 0:
                stats[c].append((t, n_el, 0, 0)); continue
            k = int(math.ceil(TOP * nv))
            idx = np.flatnonzero(ok)
            order = np.lexsort((idx, -s[idx]))              # 分數遞減、同分代號遞增（g 已依代號排序 ⇒ 列序 ＝ 代號序）
            take = idx[order[:k]]
            sel[c].append(pd.DataFrame({"pos": t, "sid": g["sid"].to_numpy()[take]}))
            stats[c].append((t, n_el, nv, k))
    out = {c: (pd.concat(v, ignore_index=True) if v else pd.DataFrame(columns=["pos", "sid"])) for c, v in sel.items()}
    return out, stats


def sig_explore(panel, cal, closes, opens, signal: str) -> pd.DataFrame:
    """P7.build_sig_gate_b（同一支）＋ 尾段列：排程出場 ＞ CUT 的進場（⑤ CUT 收盤計值）。"""
    ncal = len(cal)
    base = P7.build_sig_gate_b(panel, cal, closes, opens, start=START, signal=signal)
    pos = {d: i for i, d in enumerate(cal)}
    p = panel[panel["measure_date"] >= pd.Timestamp(START)]
    el = p[p["eligible"].astype(bool)]
    if signal == "ALL":
        m = pd.Series(True, index=el.index)
    else:
        m = (el["rev_hi24"] == 100) & (el["ma60_up"] == 100)
        if signal == "B":
            m &= el["ma_stack"] == 0
    tail = []
    for r in el[m].itertuples():
        e = pos[r.measure_date] + 1
        x = D.exit_pos(e, P7.HOLD_BARS_N)
        if x < ncal or e >= ncal or r.stock_id not in closes:
            continue                                      # x < ncal 的列 P7 已處理（⛔ 不重複）
        o = float(opens[r.stock_id][e])
        if not np.isfinite(o) or o <= 0:
            continue
        tail.append({"sid": r.stock_id, "entry_pos": e, f"xpos_{P7.RULE}": x,
                     f"g_{P7.RULE}": float(closes[r.stock_id][ncal - 1]) / o - 1.0,
                     "month": r.measure_date.strftime("%Y-%m"), "relvol": float(r.amt20), "vol": float(r.vol60)})
    sig = pd.concat([base, pd.DataFrame(tail)], ignore_index=True) if tail else base
    return sig.sort_values(["entry_pos", "sid"], kind="stable").reset_index(drop=True), len(base), len(tail)


# ═════════════ 引擎 ═════════════
_S: dict = {}


def run_one(args):
    key, seed = args
    R.COST = COST
    out = R.simulate_mtm(_S["sigs"][key], P12.RULE, P12.N_C1, np.random.default_rng(seed), _S["closes"], _S["opens"], _S["ncal"],
                         return_equity=True, pick=None, cap_fn=None, d_max=None, queue_days=0, cash_mode="zero",
                         tradable=_S["trad"], delist=_S["dl"])
    w0, w1 = _S["w0"], _S["w1"]
    r = P12.win_read(out, w0, w1, _S["marks"])
    eq = out["equity"][w0:w1 + 1]
    vol = float(np.std(eq[1:] / eq[:-1] - 1.0, ddof=1) * np.sqrt(245))
    return {"cell": key, "seed": seed, "cagr": r["cagr"], "mdd": r["mdd"], "tr": r["tr"], "expo": r["expo"], "vol": vol,
            "trades": r["trades"], "eq_sha": hashlib.sha1(np.ascontiguousarray(out["equity"]).tobytes()).hexdigest()[:16]}


def luck(s0: pd.DataFrame, x: float) -> float:
    r = (s0["cagr"] / s0["mdd"].abs()).to_numpy(float)
    return float((r <= x).mean() ** N_TRY)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=1)
    ap.add_argument("--out", default=OUT_DEFAULT)
    ap.add_argument("--stage", choices=("sig", "all"), default="all")
    ap.add_argument("--reps", type=int, default=REPS)
    ap.add_argument("--s0", type=int, default=N_S0)
    ap.add_argument("--perturb", type=int, default=None)
    ap.add_argument("--leak", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    os.makedirs(a.out, exist_ok=True)
    logf = open(os.path.join(a.out, "run.log"), "a", encoding="utf-8")

    def log(s):
        print(s, flush=True); logf.write(s + "\n"); logf.flush()
    log(f"=== researchExplore {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）out={a.out} stage={a.stage} reps={a.reps} s0={a.s0} perturb={a.perturb} leak={a.leak} procs={a.procs}")
    if a.perturb is not None:
        install_perturb(a.perturb, H2.H2D)
        log(f"⚠ 擾動模式：{H2.H2D} 內 CUT 以後的列全改亂數／亂刪（切點 fixture）")
    D.load_adj = load_adj_asof                          # ② as-of 還原因子（load_stock／tradability 都走 D.load_adj）
    _G["leak"] = a.leak
    # ① 日曆截斷
    cal_full = D.load_calendar()
    cal = cal_full[cal_full <= CUT]
    ncal = len(cal)
    assert cal[-1] == CUT, f"⛔ 日曆尾不是 {CUT.date()}：{cal[-1]}"
    w0 = int(cal.searchsorted(pd.Timestamp(W0_DATE))); w1 = ncal - 1
    assert str(cal[w0].date()) == W0_DATE
    marks = P12.month_marks(cal, w0, w1)
    _G["cal"] = cal
    log(f"[切點] 日曆 {cal[0].date()}～{cal[-1].date()}（{ncal} 根）；探索窗 [{w0}, {w1}] ＝ {cal[w0].date()}～{cal[w1].date()}（{w1 - w0 + 1} 根）")
    # 母體＋面板（同一支 RP4.build_panel，在截斷日曆上）
    stocks = pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str)
    U = H2.UG.gate3(stocks)
    U = D.load_universe().merge(U[["stock_id"]], on="stock_id")
    positions = P4F.measurement_days(cal, START, None)
    panel, _M = RP4.build_panel(cal, U, positions, procs=a.procs, mp_check=False, log=lambda s: None)
    el = panel[panel["eligible"].astype(bool)]
    log(f"[面板] gate3 {len(U)} 檔｜量測日 {len(positions)} 個（{cal[positions[0]].date()}～{cal[positions[-1]].date()}）｜{len(panel):,} 列、eligible {len(el):,}｜{time.time() - t0:.0f}s")
    uni = D.load_universe().set_index("stock_id")["market"]
    sids = sorted(set(panel["stock_id"]))
    closes, opens = {}, {}
    for s in sids + ["0050"]:
        st = D.load_stock(s, uni.get(s, "twse"), cal)
        if st is None:
            continue
        closes[s] = st.df["close"].ffill().to_numpy(float); opens[s] = st.df["open"].to_numpy(float)
    assert all(len(v) == ncal for v in closes.values())
    # 0050 同窗
    c50 = closes["0050"]
    a50, d50 = R13.window_stats(c50 / c50[w0], w0, w1 + 1, w0, w1 + 1)
    r50 = a50 / abs(d50)
    log(f"[0050 同窗] 年化 {a50:+.4%}｜回落 {d50:+.4%}｜比值 {r50:.4f}")
    # 特徵
    pos_of = {d: i for i, d in enumerate(cal)}
    el = el.assign(pos=el["measure_date"].map(pos_of).astype(int))
    jobs = [(s, uni.get(s, "twse"), g["pos"].to_numpy(int)) for s, g in el.groupby("stock_id", sort=True)]
    if a.procs > 1:
        with Pool(a.procs) as pool:
            fr = [r for rs in pool.map(feat_worker, jobs, chunksize=8) for r in rs]
    else:
        fr = [r for j in jobs for r in feat_worker(j)]
    F = pd.DataFrame(fr)
    RV = revenue_feats(cal, F[["pos", "sid"]])
    feat = F.merge(RV, on=["pos", "sid"], how="left", validate="1:1")
    feat["measure_date"] = [str(cal[p].date()) for p in feat["pos"]]
    feat = feat[["measure_date", "pos", "sid", "rev_period"] + CONDS].sort_values(["pos", "sid"]).reset_index(drop=True)
    assert len(feat) == len(el)
    feat.to_csv(os.path.join(a.out, "features.csv"), index=False)
    cov = {f: float(feat[f].notna().mean()) for f in CONDS}
    log("[特徵] {:,} 股-月｜覆蓋率 ".format(len(feat)) + " ".join(f"{f} {v:.1%}" for f, v in cov.items()) + f"｜{time.time() - t0:.0f}s")
    # 候選母體（signal ALL）與各格
    sigA, n_base, n_tail = sig_explore(panel, cal, closes, opens, "ALL")
    log(f"[S0 候選母體] P7 ALL {n_base:,} 列＋尾段（CUT 收盤計值）{n_tail:,} 列 ＝ {len(sigA):,}")
    sel, cstat = select_cells(feat)
    key = sigA.assign(pos=sigA["entry_pos"] - 1).set_index(["pos", "sid"])
    sigs, crow, cst = {}, [], []
    for c in CELLS:
        nm = cell_name(c)
        s = sel[c]
        ix = pd.MultiIndex.from_arrays([s["pos"].astype(int), s["sid"]])
        m = key.index.isin(ix)
        sigs[nm] = sigA[m].reset_index(drop=True)
        crow.append(pd.DataFrame({"cell": nm, "entry_pos": sigs[nm]["entry_pos"], "sid": sigs[nm]["sid"]}))
        st_ = np.array(cstat[c], float)
        cst.append({"cell": nm, "sig_rows": len(sigs[nm]), "months": int(sigs[nm]["month"].nunique()),
                    "selected": len(s), "dropped_entry_open": int(len(s) - m.sum()),
                    "avg_eligible": float(st_[:, 1].mean()), "avg_valid": float(st_[:, 2].mean()), "avg_k": float(st_[:, 3].mean()),
                    "min_valid": int(st_[:, 2].min())})
    pd.concat(crow, ignore_index=True).to_csv(os.path.join(a.out, "cands.csv"), index=False)
    CS = pd.DataFrame(cst); CS.to_csv(os.path.join(a.out, "cand_stats.csv"), index=False)
    log(f"[候選] 171 格｜每月平均 k {CS['avg_k'].min():.1f}～{CS['avg_k'].max():.1f}｜訊號列 {CS['sig_rows'].min():,}～{CS['sig_rows'].max():,}｜{time.time() - t0:.0f}s")
    sigB, nb_b, nt_b = sig_explore(panel, cal, closes, opens, "B")
    sigs["S0"] = sigA; sigs["W1ref"] = sigB
    log(f"[參照 W1ref 門檻B] {nb_b:,}＋尾段 {nt_b:,} ＝ {len(sigB):,} 列（⛔ 不排名、不計 N）")
    if a.stage == "sig":
        log(f"stage=sig 結束｜{time.time() - t0:.0f}s"); return
    # 引擎輸入
    allsid = set(sigA["sid"])
    trad = T.build(allsid, cal)
    off = {k: v for k, v in T.load_official().items() if v <= CUT}          # ④
    dl = T.delist_status(trad, cal, official=off)
    _S.update(sigs=sigs, closes=closes, opens=opens, ncal=ncal, trad=trad, dl=dl, w0=w0, w1=w1, marks=marks)
    log(f"[引擎輸入] tradable {len(trad):,} 檔｜官方下市日 ≤ CUT {len(off):,} 筆｜{time.time() - t0:.0f}s")
    seeds_p = os.path.join(a.out, "seeds.csv")
    done = set()
    if os.path.exists(seeds_p):
        old = pd.read_csv(seeds_p, dtype={"cell": str})
        cnt = old.groupby("cell")["seed"].nunique()
        done = set(cnt.index)
        need = {nm: (a.reps if nm not in ("S0",) else a.s0) for nm in cnt.index}
        bad = [nm for nm in done if cnt[nm] != need.get(nm, a.reps)]
        if bad:
            raise SystemExit(f"⛔ seeds.csv 有不完整的格 {bad[:5]} ⇒ 先刪掉再續跑")
    todo = [cell_name(c) for c in CELLS] + ["S0", "W1ref"]
    todo = [k for k in todo if k not in done]
    log(f"[引擎] 待跑 {len(todo)} 組（已完成 {len(done)}）")
    pool = Pool(a.procs) if a.procs > 1 else None
    try:
        for k in todo:
            n = a.s0 if k == "S0" else a.reps
            tasks = [(k, SEED0 + r) for r in range(n)]
            res = pool.map(run_one, tasks, chunksize=5) if pool else [run_one(x) for x in tasks]
            df = pd.DataFrame(res)
            df.to_csv(seeds_p, mode="a", header=not os.path.exists(seeds_p), index=False)
            log(f"  {k:<8} 年化中位 {df['cagr'].median():+.4%} 回落中位 {df['mdd'].median():+.4%}｜{time.time() - t0:.0f}s")
    finally:
        if pool:
            pool.close(); pool.join()
    aggregate(a.out, a50, d50, a.reps, a.s0, log)
    log(f"完成｜{time.time() - t0:.0f}s")


def aggregate(out, a50, d50, reps, n_s0, log=print):
    r50 = a50 / abs(d50)
    S = pd.read_csv(os.path.join(out, "seeds.csv"), dtype={"cell": str})
    s0 = S[S["cell"] == "S0"]; w1r = S[S["cell"] == "W1ref"]
    rows = []
    for i, c in enumerate(CELLS):
        nm = cell_name(c); g = S[S["cell"] == nm]
        if len(g) != reps:
            raise SystemExit(f"⛔ {nm} 只有 {len(g)} 顆")
        A, Dd = float(g["cagr"].median()), float(g["mdd"].median())
        ratio = A / abs(Dd)
        lab = ("Q" if ratio >= r50 else "R") if A > a50 else "F"
        rows.append({"idx": i, "cell": nm, "n_cond": len(c), "A": A, "D": Dd, "ratio": ratio,
                     "A_p10": float(g["cagr"].quantile(0.1)), "A_p90": float(g["cagr"].quantile(0.9)),
                     "vol_med": float(g["vol"].median()), "expo_med": float(g["expo"].median()),
                     "A_minus_0050": A - a50, "ratio_minus_0050": ratio - r50, "label": lab})
    C = pd.DataFrame(rows)
    C = C.sort_values(["ratio", "idx"], ascending=[False, True], kind="stable").reset_index(drop=True)
    C.insert(0, "rank", np.arange(1, len(C) + 1))
    cand = C[C["A"] > a50]
    C["cand_order"] = C["cell"].map({nm: j + 1 for j, nm in enumerate(cand["cell"])})
    C["luck_q"] = [luck(s0, x) for x in C["ratio"]]
    C["標記"] = "探索，非結論"
    C.to_csv(os.path.join(out, "ranking_171.csv"), index=False)
    # 線索
    used = {f: 0 for f in CONDS}; clues = []
    for r in cand.itertuples():
        cs = r.cell.split("+")
        if all(used[f] < MAX_PER_COND for f in cs):
            for f in cs:
                used[f] += 1
            clues.append(r.cell)
            if len(clues) == N_CLUES:
                break
    CL = C.set_index("cell").loc[clues].reset_index()
    CL.insert(0, "clue", np.arange(1, len(CL) + 1))
    CL["luck_tag"] = np.where(CL["luck_q"] < LUCK_Q, "與試很多次的運氣分不開", "")
    CL.to_csv(os.path.join(out, "clues.csv"), index=False)
    # 運氣分佈
    rs = (s0["cagr"] / s0["mdd"].abs()).to_numpy(float)
    rng = np.random.default_rng(LUCK_MC_SEED)
    mx = rs[rng.integers(0, len(rs), size=(LUCK_MC, N_TRY))].max(axis=1)
    qs = (0.05, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99)
    rs_sorted = np.sort(rs)
    exact_q = {f"p{int(q * 100)}": float(rs_sorted[min(len(rs) - 1, int(np.ceil(len(rs) * q ** (1 / N_TRY))) - 1)]) for q in qs}
    boot = []                                          # X3 另一讀法（描述）：一次試 ＝ 200 顆 S0 的中位比值
    for _ in range(2000):
        b = s0.iloc[rng.choice(len(s0), size=reps, replace=False)]
        boot.append(b["cagr"].median() / abs(b["mdd"].median()))
    boot = np.array(boot)
    bmx = boot[rng.integers(0, len(boot), size=(LUCK_MC, N_TRY))].max(axis=1)
    summ = {
        "登錄": "PREREG探索批 seq2 sha 1697c62b04951f2f【探索段】；⛔ 不下結論、不計 N",
        "切點": str(CUT.date()), "探索窗": [W0_DATE, str(CUT.date())],
        "0050同窗": {"年化": a50, "回落": d50, "比值": r50},
        "S0": {"n": int(len(s0)), "年化中位": float(s0["cagr"].median()), "回落中位": float(s0["mdd"].median()),
               "中位比值": float(s0["cagr"].median() / abs(s0["mdd"].median())),
               "逐種子比值分位": {f"p{int(q * 100)}": float(np.quantile(rs, q)) for q in qs},
               "逐種子年化>0050的比例": float((s0["cagr"] > a50).mean())},
        "運氣基準_最好一次（讀法 X3 甲：逐種子）": {"精確分位（F̂^171 的反函數）": exact_q,
                                          "抽樣複核分位": {f"p{int(q * 100)}": float(np.quantile(mx, q)) for q in qs},
                                          "抽樣次數": LUCK_MC},
        "運氣基準_描述（讀法 X3 乙：200 顆中位；⛔ 不用來標線索）": {f"p{int(q * 100)}": float(np.quantile(bmx, q)) for q in qs},
        "W1ref（門檻B 參照；⛔ 不排名）": {"n": int(len(w1r)), "年化中位": float(w1r["cagr"].median()) if len(w1r) else None,
                                   "回落中位": float(w1r["mdd"].median()) if len(w1r) else None},
        "標籤數（僅排名參考）": C["label"].value_counts().to_dict(),
        "年化>0050的格數": int(len(cand)),
        "比值分佈（171 格）": {f"p{int(q * 100)}": float(C["ratio"].quantile(q)) for q in (0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0)},
        "年化分佈（171 格）": {f"p{int(q * 100)}": float(C["A"].quantile(q)) for q in (0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0)},
        "線索": CL[["clue", "cell", "A", "D", "ratio", "label", "luck_q", "luck_tag"]].to_dict("records"),
        "線索不足5條": len(CL) < N_CLUES,
    }
    json.dump(summ, open(os.path.join(out, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[0050] {a50:+.4%}／{d50:+.4%}／{r50:.4f}｜年化>0050 {len(cand)} 格｜標籤 {summ['標籤數（僅排名參考）']}")
    log("[線索] " + "；".join(f"{r.clue}. {r.cell} {r.A:+.2%}／{r.D:+.2%}／{r.ratio:.3f} 運氣分位 {r.luck_q:.3f}" for r in CL.itertuples()))


if __name__ == "__main__":
    main()
