# -*- coding: utf-8 -*-
"""TradingView 流程指標（流程指標.pine）的門檻校準與近似吻合率——回測線計算子代理。只算、不交易、不計 N。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.tradingview.calib

═══ 讀法（寫死於 2026-09-30 16:05（台北），在算任何數字之前）═══
 T1 門檻（確認段 2024-01～2026-08 的每個交易日；上市櫃普通股母體 gate3、當天有 K 棒）：
    Q5 分界 ＝ 當天 Q 表碼 ＝ 5 的股票中 F 表原值的最小值；取所有日子的中位數當 Pine 預設門檻（r_5、lu_5、att_10）；另報 p10／p90 與整數欄的分佈
    disp_250 Q1 上界 ＝ 當天 Q 碼 ＝ 1 的最大原值（驗「Q1 ⇔ 0」）；bottomjudge 的「回落深度 Q5」「MA60下天數 Q2」直接用 bottomjudge meta 的探索段分界（⛔ 不重算）
 T2 Pine 的近似（Python 逐字同一套規則；K 棒序列 ＝ 研究的 bar 且有收盤；價格用【未還原】收盤，同 TradingView 預設）：
    漲停 ≈ 收盤 ÷ 前一根收盤 − 1 ≥ 9.5%｜5 日漲停天數 ＝ 最近 5 根內漲停根數｜5 日報酬 ＝ c ÷ c[5] − 1｜20 日新高 ＝ c ＞ 前 20 根最高收盤｜近 20 日高 10% 內 ＝ c ≥ 0.9 × 含當根 20 根最高
    注意（近似，依證交所「第四條異常標準之詳細數據」115.08.03 版；櫃買的門檻是用 2024～2026 公告理由裡各款出現過的最小值推的，標「近似」）：
      六日漲跌 r6 ＝ c ÷ c[k] − 1（k ∈ {5, 6} 哪個對第一款抓得準，在 T3 以 2024 年資料決定、照報；⚠ 這是校準）
      第一款：收盤 ≥ 5 元 ∧（|r6| ＞ 32%（櫃 30%）∨（|r6| ＞ 25%（櫃 23%）∧ 六日起迄價差 |c − c[5]| ≥ 50 元（櫃 40 元）））
      第二款：（30 日起迄漲 ＞ 100% ∨ 60 日 ＞ 130%（櫃 140%）∨ 90 日 ＞ 160%）∧ 收 ＞ 前收；起迄 ＝ c ÷ c[N−1] − 1（跌幅版本略過，不影響 W1）
      第三款：|r6| ＞ 25%（櫃 27%）∧ 當日量 ≥ 5 × 60 日均量（含當日）∧ 量 ≥ 500 張 ∧ 週轉率 ≥ 0.1%
      第四款：|r6| ＞ 25%（櫃 27%）∧ 當日週轉率 ≥ 10%（櫃 5%）
      第九款：6 日均量 ≥ 5 × 60 日均量 ∧ 當日量 ≥ 5 × 60 日均量 ∧ 週轉率 ＞ 0.1% ∧ 量 ＞ 500 張 ∧ 成交金額 ＞ 3000 萬
      第十款：6 日累積週轉率 ＞ 50%（櫃 80%）∧ 當日週轉率 ≥ 10%（櫃 5%）∧ 成交金額 ≥ 5 億（櫃不設）
      第十一款：收盤 ＞ 1000 元 ∧ 六日起迄價差 ≥ 300 ＋ 150 × floor((收盤 − 1000) ÷ 1000)（收盤 ≤ 2000 ⇒ 300）∧ 當日收盤為 6 日最高或最低
      ⛔ 略過（Pine 拿不到）：與全體、同類股平均的差幅、第五款（券商集中）、第六款（本益比、淨值比）、第七款（券資比）、第八款（TDR）、第十二款（借券）、第十三款（當沖）、監視督導會報決議；各款的「前幾日已公布不再公布」除外
      週轉率 ＝ 成交量 ÷ 發行股數（Python 用 stocks CSV 的 shares；Pine 用 syminfo.shares_outstanding_total）；成交金額 ＝ CSV amount（Pine 用 收盤 × 量 近似）
    處置（近似，依作業要點第六條）：觸發日 d ＝ 第一款連 3 日 ∨ 第一～四款（可算的價量款）連 5 日 ∨ 最近 10 日有 6 日 ∨ 最近 30 日有 12 日；
      2023-01 起才逐日模擬（暖身 1 年）；d 不在處置中才觸發；處置 ＝ d 的次一根起 10 根（2026-08-03 起 5 根，照新版要點；當沖加長到 7 根的情形不模擬）；
      計數重設：觸發後，計數只看觸發日之後的注意日（變體「不重設」另報，⚠ 兩者擇一是校準，在 T3 以 2024 年資料決定）
    由近似注意、處置推：近 10 日注意次數（含當日 10 根）、60 日內有處置（[d−59, d] 有處置中的根）、250 日處置天數、起漲以來處置次數、
      再次進入處置（d 是處置起日且前 60 根內另有起日）、出關（d 是處置最後一根的下一根）
    W1（Pine）＝ 20 日新高 ∧ 近 10 日注意次數 ≥ 門檻 ∧ 60 日內無處置 ∧（5 日漲停天數 ≥ 門檻 ∨ 5 日報酬 ≥ 門檻）；W2（Pine）＝ 近 20 日高 10% 內 ∧（再次進入處置 ∨ 出關）
 T3 吻合率（確認段 2024-01～2026-08 全部股票的 K 棒日）：
    k 與「重設／不重設」只用 2024 年決定（依第一款 F1、處置起日 F1），2025-01～2026-08 照報，兩段都列
    注意日：抓到率 ＝ 真注意日中近似也有的比例；誤報率 ＝ 近似注意日中真的沒有的比例；另報只看第一～四款的真注意日
    處置起日：同日、±2 根內；W1、W2：研究版（Q 表、真注意處置、還原價）對 Pine 近似版，逐日的抓到率、誤報率；另報「只換價格部分」（新高 × 急拉）的吻合
    B' 逐筆（w1better m＝7 的筆）：[e, stop] 內第一次 W1 同一天、±3 根內、兩邊都沒有的比例
 T4（2026-09-30 16:15（台北）補；⚠ 已看過第一次吻合率）：第一～四款近似誤報 45%，只用 2024 年診斷（diag_fp.py）⇒ 誤報主要來自第二款（2024 年 1,198／2,077），
    漏了官方第二款除外 3「最近 30 個營業日（含當日）內已依第一款公布，且最近 6 日累積漲跌未超過 25% ⇒ 不適用」⇒ 補上（用近似第一款代替真第一款），
    Python 與 Pine 同步；其他不變，整份重跑；第一次結果存 calib_v1.json 對照
輸出 backtest/tradingview/calib.json
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchSurge5 as S5
from backtest import researchSurge6_end_desc as ED

TIME = "2026-09-30 16:05（台北）"
OUT = "backtest/tradingview/calib.json"
D = S5.D
CON = (2024 * 12, 2026 * 12 + 7)
NEWRULE = pd.Timestamp("2026-08-03")
EXCL2 = True
PAR = {"twse": dict(c1=0.32, c1b=0.25, c1d=50.0, c2_60=1.30, c34=0.25, c4t=0.10, c10c=0.50, c10t=0.10, c10amt=5e8),
       "tpex": dict(c1=0.30, c1b=0.23, c1d=40.0, c2_60=1.40, c34=0.27, c4t=0.05, c10c=0.80, c10t=0.05, c10amt=0.0)}


def roll(x, w, fn):
    return getattr(pd.Series(x).rolling(w, min_periods=w), fn)().to_numpy()


def shift(x, k):
    return np.r_[np.full(k, np.nan), x[:-k]] if k else x


def attention_approx(c, v, amt, sh, mk, k6):
    """K 棒序列 ⇒ dict 各款 bool（Pine 同式）。"""
    p = PAR[mk]; cp = shift(c, 1)
    r6 = c / shift(c, k6) - 1; d6 = np.abs(c - shift(c, 5))                         # 價差 ＝ 六日（含當日）起迄 ⇒ c − c[5]
    turn = v / sh; v60 = roll(v, 60, "mean"); v6 = roll(v, 6, "mean")
    up = c > cp; dn = c < cp
    A = {}
    A[1] = (c >= 5) & ((np.abs(r6) > p["c1"]) | ((np.abs(r6) > p["c1b"]) & (d6 >= p["c1d"])))
    rr = {N: c / shift(c, N - 1) - 1 for N in (30, 60, 90)}
    big = (rr[30] > 1.0) | (rr[60] > p["c2_60"]) | (rr[90] > 1.6)
    A[2] = big & up                                                                  # 只算上漲版本（跌幅版本不影響 W1，略過）
    if EXCL2:                                                                        # T4：第二款除外 3（30 日內已有第一款且 6 日未超過 25%）
        a1_30 = roll(np.nan_to_num(A[1].astype(float)), 30, "sum")
        A[2] = A[2] & ~((np.nan_to_num(a1_30) > 0) & ~(r6 > 0.25))
    A[3] = (np.abs(r6) > p["c34"]) & (v >= 5 * v60) & (v >= 500_000) & (turn >= 0.001)
    A[4] = (np.abs(r6) > p["c34"]) & (turn >= p["c4t"])
    A[9] = (v6 >= 5 * v60) & (v >= 5 * v60) & (turn > 0.001) & (v > 500_000) & (amt > 3e7)
    A[10] = (roll(turn, 6, "sum") > p["c10c"]) & (turn >= p["c10t"]) & (amt >= p["c10amt"])
    hi6 = roll(c, 6, "max"); lo6 = roll(c, 6, "min")
    need = 300 + 150 * np.maximum(np.ceil((c - 2000) / 1000), 0)
    A[11] = (c > 1000) & (np.abs(c - shift(c, 5)) >= need) & ((c >= hi6) | (c <= lo6))
    for k in A:
        A[k] = np.nan_to_num(A[k].astype(float), nan=0).astype(bool)
    return A


def disposal_approx(A, dates, reset=True):
    """⇒ inD（處置中）、start（起日）、trig（觸發日）；位置 ＝ K 棒序列。"""
    m = len(dates); P = A[1] | A[2] | A[3] | A[4]; C1 = A[1]
    cP = np.r_[0, np.cumsum(P)]; cC = np.r_[0, np.cumsum(C1)]
    inD = np.zeros(m, bool); start = np.zeros(m, bool); trig = np.zeros(m, bool); endk = -1; base = 0
    i0 = int(np.searchsorted(dates, pd.Timestamp("2023-01-01")))                     # 暖身：2023 年起才逐日跑處置（之前的處置狀態不模擬）
    for i in range(i0, m):
        if i <= endk:
            continue
        lo = max(base, i0)

        def cnt(w, x):
            a = max(i - w + 1, lo); cs = cC if x is C1 else cP
            return int(cs[i + 1] - cs[a]) if a <= i else 0
        hit = (cnt(3, C1) == 3) or (cnt(5, P) == 5) or (cnt(10, P) >= 6) or (cnt(30, P) >= 12)
        if hit:
            trig[i] = True
            L = 5 if dates[min(i + 1, m - 1)] >= NEWRULE else 10
            if i + 1 < m:
                start[i + 1] = True; inD[i + 1:min(i + 1 + L, m)] = True; endk = min(i + L, m - 1)
            if reset:
                base = i + 1
    return inD, start, trig


def derived(inD, start, Aany):
    m = len(inD)
    att10 = roll(Aany.astype(float), 10, "sum")
    disp60 = roll(inD.astype(float), 60, "sum") > 0
    disp250 = roll(inD.astype(float), 250, "sum")
    st = np.flatnonzero(start)
    re = np.zeros(m, bool)
    for a in st:
        if ((st < a) & (st >= a - 60)).any():
            re[a] = True
    ex = np.zeros(m, bool)
    ex[1:] = inD[:-1] & ~inD[1:]
    return np.nan_to_num(att10, nan=0), disp60, disp250, re, ex


def thresholds(Qm, Fm, FX, bar, days, log):
    out = {}
    for col in ("r_5", "lu_5", "att_10"):
        q = np.asarray(Qm[FX[col]][:, days]); f = np.asarray(Fm[FX[col]][:, days]); b = bar[:, days]
        cut = np.array([np.nanmin(f[(q[:, j] == 5) & b[:, j], j]) if ((q[:, j] == 5) & b[:, j]).any() else np.nan for j in range(len(days))])
        r = {"中位": float(np.nanmedian(cut)), "p10": float(np.nanpercentile(cut, 10)), "p90": float(np.nanpercentile(cut, 90)), "日數": int(np.isfinite(cut).sum())}
        if col != "r_5":
            vc = pd.Series(cut[np.isfinite(cut)]).value_counts(normalize=True).sort_index()
            r["分佈"] = {str(int(k)): round(float(v), 4) for k, v in vc.items()}
        out[col] = r; log(f"[門檻] {col} {r}")
    q = np.asarray(Qm[FX["disp_250"]][:, days]); f = np.asarray(Fm[FX["disp_250"]][:, days]); b = bar[:, days]
    mx = np.array([np.nanmax(f[(q[:, j] == 1) & b[:, j], j]) if ((q[:, j] == 1) & b[:, j]).any() else np.nan for j in range(len(days))])
    out["disp_250 Q1"] = {"Q1 最大原值＝0 的日子比例": float(np.mean(mx == 0)), "Q1 最大原值 中位": float(np.nanmedian(mx))}
    meta = json.load(open("backtest/resultsSurge6/bottomjudge/meta.json", encoding="utf-8"))
    bd = meta["五等分分界（探索段低點）"]
    out["bottomjudge"] = {"m*（x20 K5）": int(meta["當下可用版 m*"]["20%_K5"]), "回落深度_x20 分界": bd["回落深度_x20"], "MA60下天數_x20 分界": bd["MA60下天數_x20"],
                          "回落深度 Q5 ⇔": f"≥ {bd['回落深度_x20'][3]}", "MA60下天數 Q2 ⇔": f"{bd['MA60下天數_x20'][0]} ≤ v ＜ {bd['MA60下天數_x20'][1]}"}
    return out


class Acc:
    def __init__(self):
        self.tp = self.fp = self.fn = 0

    def add(self, real, appr):
        self.tp += int((real & appr).sum()); self.fp += int((~real & appr).sum()); self.fn += int((real & ~appr).sum())

    def res(self):
        return {"真": self.tp + self.fn, "近似": self.tp + self.fp, "兩者": self.tp, "抓到率": self.tp / max(self.tp + self.fn, 1), "誤報率": self.fp / max(self.tp + self.fp, 1)}


def main():
    T0 = time.time()
    log = lambda m: print(f"[{time.time() - T0:6.0f}s] {m}", flush=True)
    uni, cal, n, inseg, bar, h6, E, cells, cnt = ED.load()
    Qm = np.load(os.path.join(S5.WORK, "Q.npy"), mmap_mode="r"); Fm = np.load(os.path.join(S5.WORK, "F.npy"), mmap_mode="r"); FX = S5.FIX
    mon = np.array([d.year * 12 + d.month - 1 for d in cal]); t1 = int(cal.searchsorted(pd.Timestamp("2026-08-31"), side="right")) - 1
    days = np.flatnonzero((mon >= CON[0]) & (mon <= CON[1]) & (np.arange(n) <= t1))
    TH = thresholds(Qm, Fm, FX, bar, days, log)
    thR5 = TH["r_5"]["中位"]; thLU = TH["lu_5"]["中位"]; thATT = TH["att_10"]["中位"]
    ATT, DISP = S5.SF.att_disp(S5.MAIN, cal)
    a_raw = pd.read_csv(os.path.join(S5.MAIN, "meta", "attention.csv"), dtype={"stock_id": str, "date": str}, usecols=["stock_id", "date", "reason"])
    a_raw = a_raw[a_raw["date"] >= "2023-06-01"]
    a_raw["p14"] = a_raw["reason"].fillna("").str.contains(r"第[一二三四]款")
    ATT14 = {s: np.unique(cal.searchsorted(pd.to_datetime(g.loc[g["p14"], "date"]))) for s, g in a_raw.groupby("stock_id")}
    Q = {c: np.asarray(Qm[FX[c]]) for c in ("att_10", "lu_5", "r_5")}; d60 = np.asarray(Fm[FX["disp_60"]])
    y24 = (mon >= 2024 * 12) & (mon <= 2024 * 12 + 11); y25 = (mon >= 2025 * 12) & (mon <= CON[1]) & (np.arange(n) <= t1)
    VAR = [(k6, rs) for k6 in (5, 6) for rs in (True, False)]
    acc = {(v, per, what): Acc() for v in VAR for per in ("2024", "2025-2026.08") for what in ("注意日", "注意日（只看一～四款）", "第一款", "處置起日", "W1", "W1 價格部分", "W2")}
    near = {(v, per): [0, 0, 0] for v in VAR for per in ("2024", "2025-2026.08")}     # 處置起日 ±2：真起日有近似 ±2 的數、真起日數、近似起日有真 ±2 的數
    nearA = {(v, per): 0 for v in VAR for per in ("2024", "2025-2026.08")}
    W1A = {v: np.zeros((len(uni), n), bool) for v in VAR}; W1R = np.zeros((len(uni), n), bool)
    D.DATA = S5.ST
    for s in range(len(uni)):
        sid, mk = uni.loc[s, "stock_id"], uni.loc[s, "market"]
        p_ = os.path.join(S5.ST, "stocks", sid + ".csv")
        if not os.path.exists(p_):
            continue
        raw = pd.read_csv(p_, dtype={"date": str}, usecols=["date", "close", "volume", "amount", "shares"]).drop_duplicates("date")
        raw.index = pd.to_datetime(raw["date"]); raw = raw.reindex(cal)
        rc = pd.to_numeric(raw["close"], errors="coerce").to_numpy(float).copy(); rc[~(rc > 0)] = np.nan
        idx = np.flatnonzero(np.isfinite(rc) & bar[s])
        if len(idx) < 100 or idx[-1] < days[0]:
            continue
        c = rc[idx]; v = pd.to_numeric(raw["volume"], errors="coerce").to_numpy(float)[idx]; amt = pd.to_numeric(raw["amount"], errors="coerce").to_numpy(float)[idx]
        sh = pd.to_numeric(raw["shares"], errors="coerce").ffill().to_numpy(float)[idx].copy(); sh[~(sh > 0)] = np.nan
        dates = cal[idx]
        ca = pd.Series(D.load_stock(sid, mk, cal).df["close"].to_numpy(float)).ffill().to_numpy()[idx]
        # 研究版（還原價）
        mx = roll(ca, 20, "max"); HIa = ca > shift(mx, 1); NEa = ca >= 0.9 * mx
        pr_res = HIa & ((Q["lu_5"][s, idx] == 5) | (Q["r_5"][s, idx] == 5))
        w1_res = pr_res & (Q["att_10"][s, idx] == 5) & (d60[s, idx] == 0)
        realA = np.zeros(n, bool); realA[ATT.get(sid, np.zeros(0, int))[ATT.get(sid, np.zeros(0, int)) < n]] = True; realA = realA[idx]
        realA14 = np.zeros(n, bool); a14 = ATT14.get(sid, np.zeros(0, int)); realA14[a14[a14 < n]] = True; realA14 = realA14[idx]
        rin = np.zeros(n, bool); rst = np.zeros(n, bool); rex = np.zeros(n, bool); starts = []
        for a_, b_ in DISP.get(sid, []):
            if 0 <= a_ < n:
                rst[a_] = True; starts.append(a_)
            rin[max(a_, 0):min(b_, n - 1) + 1] = True
            if 0 <= b_ + 1 < n:
                rex[b_ + 1] = True
        re_r = np.zeros(n, bool)
        for a_ in starts:
            if any(0 < a_ - x <= 60 for x in starts if x != a_):
                re_r[a_] = True
        w2_res = NEa & (re_r[idx] | rex[idx])
        # Pine 近似（未還原價）
        mxr = roll(c, 20, "max"); HIr = c > shift(mxr, 1); NEr = c >= 0.9 * mxr
        lu = (c / shift(c, 1) - 1 >= 0.095).astype(float); lu5 = roll(lu, 5, "sum"); r5 = c / shift(c, 5) - 1
        pr_apx = HIr & ((np.nan_to_num(lu5) >= thLU) | (np.nan_to_num(r5, nan=-9) >= thR5))
        W1R[s, idx] = w1_res
        for k6, rs in VAR:
            A = attention_approx(c, v, amt, sh, mk, k6); Aany = np.zeros(len(c), bool)
            for x in A.values():
                Aany |= x
            inD, st_, trig = disposal_approx(A, dates, rs)
            att10, disp60, disp250, re_a, ex_a = derived(inD, st_, Aany)
            w1_apx = pr_apx & (att10 >= thATT) & ~disp60
            w2_apx = NEr & (re_a | ex_a)
            W1A[(k6, rs)][s, idx] = w1_apx
            for per, msk in (("2024", y24[idx]), ("2025-2026.08", y25[idx])):
                g = lambda x: x[msk]
                acc[((k6, rs), per, "注意日")].add(g(realA), g(Aany)); acc[((k6, rs), per, "注意日（只看一～四款）")].add(g(realA14), g(A[1] | A[2] | A[3] | A[4]))
                acc[((k6, rs), per, "W1")].add(g(w1_res), g(w1_apx)); acc[((k6, rs), per, "W1 價格部分")].add(g(pr_res), g(pr_apx)); acc[((k6, rs), per, "W2")].add(g(w2_res), g(w2_apx))
                acc[((k6, rs), per, "處置起日")].add(g(rst[idx]), g(st_))
                ri = np.flatnonzero(g(rst[idx])); ai = np.flatnonzero(g(st_))
                near[((k6, rs), per)][0] += sum(1 for x in ri if (np.abs(ai - x) <= 2).any()); near[((k6, rs), per)][1] += len(ri)
                nearA[((k6, rs), per)] += sum(1 for x in ai if (np.abs(ri - x) <= 2).any()); near[((k6, rs), per)][2] += len(ai)
            # 第一款單獨（真第一款日 ＝ 理由含第一款）
        if s % 400 == 0:
            log(f"[股] {s}/{len(uni)}")
    # 第一款 F1 用「注意日（只看一～四款）」代替（真資料以理由判款）；依 2024 年 F1 選 k 與重設
    f1 = lambda r: 2 * r["兩者"] / max(r["真"] + r["近似"], 1)
    sc = {v: f1(acc[(v, "2024", "注意日（只看一～四款）")].res()) + f1(acc[(v, "2024", "處置起日")].res()) for v in VAR}
    best = max(VAR, key=lambda v: sc[v])
    log(f"[選] 依 2024 年 F1 和 ⇒ k6＝{best[0]}、重設＝{best[1]}｜{ {str(k): round(v, 4) for k, v in sc.items()} }")
    RES = {}
    for v in VAR:
        for per in ("2024", "2025-2026.08"):
            d_ = {w: acc[(v, per, w)].res() for w in ("注意日", "注意日（只看一～四款）", "處置起日", "W1", "W1 價格部分", "W2")}
            nr = near[(v, per)]
            d_["處置起日 ±2 根"] = {"真起日數": nr[1], "抓到率（±2）": nr[0] / max(nr[1], 1), "近似起日數": nr[2], "誤報率（±2）": 1 - nearA[(v, per)] / max(nr[2], 1)}
            RES[f"k6={v[0]}｜{'重設' if v[1] else '不重設'}｜{per}"] = d_
    # B' 逐筆：第一次 W1
    WT = pd.read_csv("backtest/resultsSurge6/w1better/trades.csv.gz"); WT = WT[WT["m"] == 7]
    BR = {}
    for per, lo, hi in (("2021-2023", 2021 * 12, 2023 * 12 + 11), ("2024-2026.08", CON[0], CON[1])):
        T = WT[(WT["進場月"] >= lo) & (WT["進場月"] <= hi)]; same = pm3 = none2 = only_r = only_a = 0
        for r in T.itertuples():
            s, e, stop = int(r.s), int(r.e), int(r.stop)
            fr = np.flatnonzero(W1R[s, e:stop + 1]); fa = np.flatnonzero(W1A[best][s, e:stop + 1])
            if not len(fr) and not len(fa):
                none2 += 1
            elif len(fr) and len(fa):
                same += int(fr[0] == fa[0]); pm3 += int(abs(fr[0] - fa[0]) <= 3)
            elif len(fr):
                only_r += 1
            else:
                only_a += 1
        N = len(T); BR[per] = {"筆數": N, "兩邊都沒有": none2 / N, "同一天": same / N, "±3 日曆位置內": pm3 / N, "只有研究版": only_r / N, "只有近似版": only_a / N,
                               "同一天或都沒有": (same + none2) / N}
        log(f"[B'] {per} {BR[per]}")
    out = {"讀法寫死": TIME, "門檻": TH, "Pine 預設門檻": {"5日報酬 ≥": thR5, "5日漲停天數 ≥": thLU, "近10日注意次數 ≥": thATT},
           "選定近似": {"六日漲跌用 c÷c[k]−1 的 k": best[0], "處置計數觸發後重設": best[1], "依據（2024 年 F1 和）": {f"k6={k[0]}｜{'重設' if k[1] else '不重設'}": v for k, v in sc.items()}},
           "吻合率": RES, "選定版吻合率": {per: RES[f"k6={best[0]}｜{'重設' if best[1] else '不重設'}｜{per}"] for per in ("2024", "2025-2026.08")},
           "B' m＝7 第一次 W1（選定版）": BR, "耗時秒": round(time.time() - T0)}
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log("[完]")


if __name__ == "__main__":
    main()
