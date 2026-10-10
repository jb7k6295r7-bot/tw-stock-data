# -*- coding: utf-8 -*-
"""USREG-C2 內部人公開市場買進（Form 4）。回測線，台北 2026-10-10。

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSC_late_c2 [--procs 3] [--nseed 200]

登錄：USREG-B2 內部人買進 seq1（sha f369f2c02f8e095b）→ 裁定 seq321 §三發號 USREG-C2；N（美股帳）6 ＝ 甲 4（A、B、C、D）＋ 乙 2（B、C）。
裁定 seq321：美股原生新題 ⇒ 【合併母體】當判定（⛔ 不套 seq316）；只 S&P 500、只 S&P 400 照報，兩欄方向相反要寫。seq308：條件出場主臂、窗尾仍持有與持有天數必報。
⛔⛔ 私有資料：Form 4 逐筆、逐日價格、逐筆事件 ⛔ 不進 repo；逐筆中間檔放 ~/us_work/c_late/（repo 外）；resultsUSC/late/ 只放彙總（件數、比例、平均、CI、判語）。

資料：Form 4 ＝ ~/usdata/b33bde6/data/insider/form4_<年>.csv.gz（us-stock-data b33bde68；gzip.open(p,"rt",encoding="utf-8")）；
      價格、母體（S&P 500／400 聯集、硬斷點、有效 K 棒）＝ USREG-A3 的逐檔快取 ~/us_work/a3/stocks.pkl（us-stock-data 881c86a9，A3／A4 同一份，
      researchUSA3_core.load_cache；窗內價格與 b33bde68 只差 Yahoo 每日重算的 adjclose 比例，不影響報酬）；基準 ^SP500TR（researchUSA3_core.bench_tr）。

══ 執行者補讀法（⭐ 台北 2026-10-10 23:41 寫死於看任何 C2 報酬之前；登錄沒寫清楚處）══
 K1 取列：form ＝ "4"（4/A 全不用：登錄「以第一次申報為準、更正不回填」）；trans_code P（買）、S（賣）；交易資料讀 2013 起（分類要前 3 年）。
 K2 可用日：filing_accepted_at 的本地部分就是美東時間（資料庫 1659：標 Z 但不是 UTC、已換成美東帶偏移）⇒ 取日期 D 與時刻 h；
    可用日 ＝ 日曆（A3 快取日曆）中嚴格晚於 D 的第一個交易日；h ＞ 16:00:00 ⇒ 再往後一個交易日（照登錄字面；週末收件同法）；
    收件日早於日曆首日（2015-11-02）⇒ 不給可用日（這些列只用在 K5 分類歷史）。
 K3 人 ＝ owner_cik 的第一個 CIK（聯合申報以第一申報人為代表）；身分 ＝ 該列 is_director／is_officer（任一 ＝ 1 才算「董事或高階主管」；只有 10% 大股東、或三者皆 0 ⇒ 排除）。
 K4 合併：同一人、同一公司（issuer_cik）、同一 trans_date 的 P 列合成一筆；金額 ＝ Σ 股數 × 價格（價格空白的列不計金額）；全部價格空白 ⇒ 金額不明 ⇒ 排除（件數報）；
    合併後金額 ＜ 10,000 美元 ⇒ 排除（登錄寫明理由「象徵性」⇒ 固定值，seq321 §五 允許）；合併筆的可用日 ＝ 各列可用日最晚者（全部資訊都公開時）；10b5-1 ＝ 任一列勾 1。
 K5 分類（Cohen 等）：該筆的人（K3）在 trans_date 年 Y 的前 3 個曆年（Y−1、Y−2、Y−3）每年都有 P 或 S 交易（資料內任一公司、owner_cik 任一位置出現即算）才分類；
    3 年每年都有同一曆月（＝ 本筆 trans_date 的月）交易 ⇒ 例行型，否則 ⇒ 機會型；不足 ⇒ 不分類。trans_date ≥ 2023-04-01 且 10b5-1 勾 1 ⇒ 一律例行型。
    ⚠ 資料只含 S&P 500／400 名冊公司的申報 ⇒ 內部人在名冊外公司的交易看不到（分類偏向「不分類／機會型」，照標）。
 K6 訊號：A ＝ K4 後全部；B ＝ A ∩ 機會型（不分類者不算）；D ＝ officer_title（大寫）含 CEO、CHIEF EXECUTIVE、CFO、CHIEF FINANCIAL，或含 PRESIDENT 但不含
    VICE PRES／VP／EVP／SVP／V. P.（字面「含 President」會把所有副總裁算進執行長類，與題意不合 ⇒ 排除副總裁；字面版件數另報）；
    C ＝ 同一公司、A 的各筆依可用日排序，第 i 筆可用時「可用日 ≤ 它、且 |trans_date 差| ≤ 30 曆日」的不同人（含自己）≥ 3 ⇒ 事件日 ＝ 第 i 筆可用日。
 K7 母體與代號：事件日（可用日）d ∈ [2016-01-04, 2026-08-31]；公司的代號（Form 4 ticker 欄，可能用 ; 串多個）中，d 當天在 S&P 500 或 400 成分內、有效 K 棒、
    開盤 > 0 者；多個 ⇒ 字母序第一個（同一公司只算一筆）；沒有 ⇒ 不在母體（件數報）。三欄 ＝ d 當天歸屬（只 400 ＝ m400、只 500 ＝ m500、合併 ＝ 全部）。
 K8 去重：同一公司、同一訊號，依事件日排序，距上一個【保留】事件 ≤ 20 個交易日 ⇒ 丟（researchUSA3 keep_first 同序）；在母體篩完之後做。
 K9 甲 報酬：r_H ＝ PX(d＋H)／開盤(d) − 1（PX ＝ 有效開盤，否則前值收盤；A3 ew_bench 同式）；需 d＋H ≤ 2026-09-30、(d, d＋H] 無硬斷點，否則該 H 不收。
    前 20 日報酬 ＝ 收盤(d−1)／收盤(d−21) − 1（ffill 收盤；(d−21, d−1] 有硬斷點 ⇒ 缺）。
    十分位：d 日該欄母體（成分內 ∧ 有效開盤 ∧ 前 20 日報酬可算）依前 20 日報酬排名（同值依代號序）等分 10 組；
    對照（主）＝ 同日、同欄、同十分位、r_H 可算、且 d 日【沒有任何】P 申報可用（任何人、任何金額，Form 4 P 列可用日 ＝ d 的所有代號）的股票 r_H 等權平均；
    異常報酬 ＝ r_H − 對照。描述 ＝ 對同日該欄母體等權（r_H 可算者全部）。
 K10 甲 判：researchM.summ（曆月群集 SE、20 日區段 n_eff）；n ＜ 30 或 n_eff ＜ 30 ⇒ 出口①（樣本不足）；
     判定 ＝ 平均 ＞ 0 且 Bonferroni（0.05／4 ⇒ 雙尾 z ＝ 2.4977）群集 CI 不含 0 ⇒「之後比較會漲（測得出）」；95% CI 一併報。合併欄判、兩個單欄描述。
 K11 甲 假訊號（⛔ 不判）：合併欄、H20；每個保留事件（檔 s、季 q）在同檔、同曆季、窗內、異常報酬可算、且 [t−20, t] 內沒有該訊號真事件的交易日 t 中抽 1 天；
     1,000 次（rng 20261010）⇒ p ＝ 假訊號平均 ≥ 真平均 的比例；p ≥ 5% ⇒ 結果句前加「隨機也做得到 x%」。抽不到候選日的事件 ⇒ 該事件不進假訊號（件數報）。
 K12 乙 進場 ＝ 事件日 d 開盤（＝ 可用日開盤）；8 槽等權、同日超額抽籤（種子 102000＋r、200 顆）；引擎 ＝ researchUSA3_core.pf_run（research11.simulate_mtm，
     cash zero、tradable＝有效 K 棒、下市結算；USREG-A3 同一套）；成本 0.05%（合格或另列才跑 0.02、0.10% 敏感度）；窗 2016-01-04～2026-09-30；判準 ^SP500TR 同窗。
 K13 乙 出場（條件，⛔ 無最長天數）：取最早者 ——
     ① 同一公司任一董事或高階主管的機會型賣出（S；K3、K5 同法分類於賣方；10b5-1 勾 1 不算；金額不設門檻）：該賣出的可用日 x（＞ 進場日）開盤賣；
     ② 第 t 日（＞ 進場日、有效 K 棒）收盤 ＜ 自己 200 根有效 K 棒均線，且 (t 的日期 − 365 天, t 的日期] 內該公司沒有任何 A 級買進（K4 後，可用日計）
        ⇒ t＋1 開盤賣（「新的 P 訊號」讀成 A 級買進，含進場那一筆 ⇒ 進場後至少約 12 個月才可能觸發 ②）；均線不可算 ⇒ ② 不成立；
     都沒有、或出場日 ＞ 2026-09-30 ⇒ 窗尾收盤結算（件數必報）。毛報酬 researchUSA3_core.gross_exit。
     固定 {20, 60, 120, 240} 日只描述（researchUSA3_core.fixed_rows，同一批進場）。
 K14 乙 假訊號（⛔ 不判）：合併欄；每一筆進場保留同一檔，進場日改成窗內（≤ 2026-08-31）該檔在合併母體且有效開盤的隨機交易日，出場照 K13 重算；200 次（rng 20261011），
     每次 1 顆抽籤種子 102000 ⇒ p ＝ 假訊號年化 ≥ 真 200 顆年化中位 的比例。
 K15 等效獨立檔數（seq321 §五）：種子 102000 的持股，每月底 k 檔（k ≥ 2）⇒ k ÷ (1 ＋ (k−1) ρ̄)，ρ̄ ＝ 這 k 檔前 120 個交易日日報酬的平均兩兩相關；報月平均。
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import pickle
import re
import sys
import time
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
from backtest import researchUSA3_core as C3          # noqa: E402（import 時 A2.install()；價格快取 881c86a）
from backtest import research11 as R11                # noqa: E402
from backtest import researchUSC_late as L            # noqa: E402

INS = os.path.join(L.ROOT, "data", "insider")
READ_TS = "2026-10-10 23:41（台北）"
W0, AV_END, W1 = "2016-01-04", "2026-08-31", "2026-09-30"
HS = (20, 60, 120, 240)
CELLS = ("A", "B", "C", "D")
CELL_TXT = {"A": "任何董事或高階主管買進", "B": "機會型買進", "C": "多人一起買（30 天內 ≥3 人）", "D": "執行長或財務長買進"}
COLS = ("合併", "只400", "只500")
ZB = 2.497705                                          # 雙尾 0.05/4
MIN_AMT = 10000.0
WORK = L.WORK
LOGF = None


def log(m):
    print(m, flush=True)
    if LOGF:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(m + "\n")


# ═════════════ Form 4 讀檔（K1～K6）═════════════
def read_form4(y0=2013, y1=2026):
    fr = []
    for y in range(y0, y1 + 1):
        p = os.path.join(INS, f"form4_{y}.csv.gz")
        d = pd.read_csv(gzip.open(p, "rt", encoding="utf-8"), dtype=str, keep_default_na=False)
        fr.append(d)
    F = pd.concat(fr, ignore_index=True)
    n0 = len(F)
    F = F[(F["form"] == "4") & F["trans_code"].isin(["P", "S"])].copy()
    F["owner1"] = F["owner_cik"].str.split(";").str[0]
    F["dir_off"] = (F["is_director"] == "1") | (F["is_officer"] == "1")
    F["shares_f"] = pd.to_numeric(F["shares"].replace("", None), errors="coerce")
    F["price_f"] = pd.to_numeric(F["price"].replace("", None), errors="coerce")
    F["amt"] = F["shares_f"] * F["price_f"]
    F["acc_date"] = F["filing_accepted_at"].str[:10]
    F["acc_time"] = F["filing_accepted_at"].str[11:19]
    return F.reset_index(drop=True), n0


def avail_pos(acc_date, acc_time, cal_str):
    """K2：→ 日曆位置（int；超出 ⇒ -1）。"""
    i = np.searchsorted(cal_str, acc_date, side="right")
    i = i + (acc_time > "16:00:00").astype(int)
    i = np.where(acc_date < cal_str[0], -1, i)
    return np.where(i < len(cal_str), i, -1)


def hist_sets(F):
    """K5：owner（出現在 owner_cik 任一位置）× 年、× 年月 的集合。"""
    ys, yms = set(), set()
    for oc, td in zip(F["owner_cik"].to_numpy(), F["trans_date"].to_numpy()):
        y = td[:4]; m = td[5:7]
        for o in oc.split(";"):
            ys.add((o, y)); yms.add((o, y, m))
    return ys, yms


def classify(owner, tdate, aff, ys, yms):
    """→ '例行'／'機會'／'不分類'（K5）。"""
    if tdate >= "2023-04-01" and aff:
        return "例行"
    y = int(tdate[:4]); m = tdate[5:7]
    if not all((owner, str(y - k)) in ys for k in (1, 2, 3)):
        return "不分類"
    return "例行" if all((owner, str(y - k), m) in yms for k in (1, 2, 3)) else "機會"


CEO_RE = re.compile(r"\bCEO\b|CHIEF EXECUTIVE|\bCFO\b|CHIEF FINANCIAL")
VP_RE = re.compile(r"VICE[\s\-]*PRES|\bVP\b|\bEVP\b|\bSVP\b|V\.\s*P\.")


def is_ceo_cfo(title, literal=False):
    t = (title or "").upper()
    if CEO_RE.search(t):
        return True
    if "PRESIDENT" in t:
        return True if literal else not VP_RE.search(t)
    return False


def build_buys(F, cal_str, ys, yms):
    """K3～K6：A 級買進（合併後）表。"""
    P = F[(F["trans_code"] == "P") & F["dir_off"]].copy()
    st = {"P 列（form 4）": int((F["trans_code"] == "P").sum()), "P 列 董事或高階主管": int(len(P))}
    P["av"] = avail_pos(P["acc_date"].to_numpy(str), P["acc_time"].to_numpy(str), cal_str)
    g = P.groupby(["issuer_cik", "owner1", "trans_date"], sort=True)
    B = g.agg(ticker=("ticker", "first"), amt=("amt", lambda s: float(np.nansum(s.to_numpy(float))) if np.isfinite(s.to_numpy(float)).any() else np.nan),
              av=("av", "max"), av_min=("av", "min"), aff=("aff10b5one", lambda s: bool((s == "1").any())),
              aff_blank=("aff10b5one", lambda s: bool((s == "").all())),
              title=("officer_title", lambda s: next((x for x in s if x), "")), n_rows=("ticker", "size"),
              is_dir=("is_director", lambda s: bool((s == "1").any())), is_off=("is_officer", lambda s: bool((s == "1").any()))).reset_index()
    st["合併後筆數"] = int(len(B)); st["合併掉的列"] = int(len(P) - len(B))
    st["金額不明（價格全空白）"] = int(B["amt"].isna().sum())
    st["金額 < 1 萬美元"] = int((B["amt"] < MIN_AMT).sum())
    B = B[B["amt"] >= MIN_AMT].reset_index(drop=True)
    B["cls"] = [classify(o, t, a, ys, yms) for o, t, a in zip(B["owner1"], B["trans_date"], B["aff"])]
    B["ceo"] = [is_ceo_cfo(t) for t in B["title"]]
    B["ceo_lit"] = [is_ceo_cfo(t, True) for t in B["title"]]
    st["≥1 萬美元的 A 級買進"] = int(len(B))
    return B, st


def build_sales(F, cal_str, ys, yms):
    """K13 ①：機會型賣出（董事或高階主管、非 10b5-1）的 (issuer, 可用日位置)。"""
    S = F[(F["trans_code"] == "S") & F["dir_off"]].copy()
    S = S[S["trans_date"] >= "2015-01-01"]
    S["av"] = avail_pos(S["acc_date"].to_numpy(str), S["acc_time"].to_numpy(str), cal_str)
    S["aff1"] = S["aff10b5one"] == "1"
    S["cls"] = [classify(o, t, a, ys, yms) for o, t, a in zip(S["owner1"], S["trans_date"], S["aff1"])]
    keep = S[(S["cls"] == "機會") & ~S["aff1"] & (S["av"] >= 0)]
    out = defaultdict(list)
    for i, a in zip(keep["issuer_cik"], keep["av"]):
        out[i].append(int(a))
    st = {"S 列 董事或高階主管（2015 起）": int(len(S)), "其中機會型且非10b5-1": int(len(keep)),
          "分類分佈": {k: int(v) for k, v in S["cls"].value_counts().items()}}
    return {k: np.array(sorted(set(v)), int) for k, v in out.items()}, st


def cluster_events(B):
    """K6 C：→ B 的列索引（第 3 位使事件成立的那幾筆；每筆可用日都可能是事件）。"""
    idx = []
    for iss, g in B[B["av"] >= 0].groupby("issuer_cik"):
        g = g.sort_values(["av", "trans_date", "owner1"])
        av = g["av"].to_numpy(); td = pd.to_datetime(g["trans_date"]).to_numpy(); ow = g["owner1"].to_numpy()
        for k in range(len(g)):
            m = (av <= av[k]) & (np.abs((td - td[k]).astype("timedelta64[D]").astype(int)) <= 30)
            if len(set(ow[m])) >= 3:
                idx.append(g.index[k])
    return np.array(sorted(idx), int)


# ═════════════ 價格矩陣 ═════════════
def mats(ST, sids, n):
    O = np.column_stack([ST[s]["O"] for s in sids])
    valid = np.column_stack([ST[s]["valid"] for s in sids])
    okO = valid & (np.nan_to_num(O) > 0)
    Cf = np.column_stack([ST[s]["closes"] for s in sids])
    PX = np.where(okO, O, Cf)
    pb = np.column_stack([ST[s]["pb"] for s in sids])
    CS = np.cumsum(pb.astype(np.int64), axis=0)
    MM = {"合併": np.column_stack([ST[s]["member"] for s in sids]), "只400": np.column_stack([ST[s]["m4"] for s in sids]),
          "只500": np.column_stack([ST[s]["m5"] for s in sids])}
    return O, valid, okO, Cf, PX, CS, MM


def fwd_ret(O, okO, PX, CS, H, w1):
    n = O.shape[0]; r = np.full(O.shape, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        rr = PX[H:] / np.where(okO[:n - H], O[:n - H], np.nan) - 1.0
    rr[(CS[H:] - CS[:n - H]) > 0] = np.nan
    r[:n - H] = rr
    r[w1 - H + 1:] = np.nan                                   # d＋H ≤ 窗尾
    return r


def past20(Cf, valid, CS):
    n = Cf.shape[0]; p = np.full(Cf.shape, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        x = Cf[20:n - 1] / Cf[0:n - 21] - 1.0                # d ＝ 21..n−1：Cf[d−1]/Cf[d−21]
    brk = (CS[20:n - 1] - CS[0:n - 21]) > 0                  # (d−21, d−1]
    x[brk] = np.nan
    p[21:] = x
    return p


def deciles(p20, pop):
    """每日：pop 內依 p20 排名（同值依欄序）等分 10 ⇒ 0..9；不在 pop ⇒ -1。"""
    n, S = p20.shape; dec = np.full((n, S), -1, np.int8)
    for d in range(n):
        m = pop[d] & np.isfinite(p20[d])
        k = int(m.sum())
        if k < 10:
            continue
        j = np.flatnonzero(m)
        order = j[np.lexsort((j, p20[d, j]))]
        dec[d, order] = (np.arange(k) * 10 // k).astype(np.int8)
    return dec


def ctrl_mean(r, dec, excl):
    n, S = r.shape; out = np.full((n, 10), np.nan)
    ok = np.isfinite(r) & (dec >= 0) & ~excl
    for d in range(n):
        m = ok[d]
        if not m.any():
            continue
        s = np.bincount(dec[d, m], weights=r[d, m], minlength=10); c = np.bincount(dec[d, m], minlength=10)
        out[d] = np.where(c > 0, s / np.maximum(c, 1), np.nan)
    return out


def stat(x, T, cal, w0, wE):
    s = C3.ev_summ(np.asarray(x, float), np.asarray(T, int), cal, w0, wE)
    if s.get("n", 0) == 0:
        return {"n": 0, "判": "—（無事件）"}
    se = s["se_月"]; mu = s["平均"]
    s["lo_Bonf"] = mu - ZB * se; s["hi_Bonf"] = mu + ZB * se
    if s["n"] < 30 or s["n_eff"] < 30:
        s["判"] = "出口①（樣本不足以分辨）"
    elif s["lo_Bonf"] > 0:
        s["判"] = "測得出（＋）之後比較會漲"
    elif s["hi_Bonf"] < 0:
        s["判"] = "測得出（−）之後比較會跌"
    else:
        s["判"] = "測不出"
    return s


# ═════════════ 乙：出場 ═════════════
def ma200_below(d):
    c = d["C"]; v = d["valid"]
    m = L.ma(np.where(v, c, np.nan), 200)
    return v & np.isfinite(m) & (c < m)


def exit_for(e, iss, below, sales, abuy_dates, cal_dt, s1):
    """K13 ⇒ (x, endhold, reason)。"""
    x1 = None
    sa = sales.get(iss)
    if sa is not None:
        k = int(np.searchsorted(sa, e, side="right"))
        if k < len(sa):
            x1 = int(sa[k])
    x2 = None
    t = np.flatnonzero(below[e + 1:s1 + 1]) + e + 1
    if len(t):
        bd = abuy_dates.get(iss, np.array([], "datetime64[D]"))
        tdt = cal_dt[t]
        if len(bd):
            j = np.searchsorted(bd, tdt, side="right") - 1      # 最近一筆 ≤ t 的 A 級買進
            last = np.where(j >= 0, bd[np.maximum(j, 0)], np.datetime64("1900-01-01"))
        else:
            last = np.full(len(t), np.datetime64("1900-01-01"), "datetime64[D]")
        okk = (tdt - last).astype(int) >= 365
        if okk.any():
            x2 = int(t[np.flatnonzero(okk)[0]]) + 1
    cands = [(x, r) for x, r in ((x1, "機會型賣出"), (x2, "12個月無新買進且跌破200日線")) if x is not None]
    if cands:
        x, r = min(cands)
        if x <= s1:
            return x, False, r
    return s1, True, "窗尾"


def main():
    global LOGF
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); ap.add_argument("--nseed", type=int, default=200)
    ap.add_argument("--skip-pf", action="store_true"); a = ap.parse_args()
    os.makedirs(L.OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    LOGF = os.path.join(L.OUT, "run_c2.log")
    t0 = time.time()
    L.assert_pinned()
    meta, ST = C3.load_cache()
    cal = meta["cal"]; n = len(cal); cal_str = np.array([str(x.date()) for x in cal]); cal_dt = cal.values.astype("datetime64[D]")
    w0 = int(np.searchsorted(cal_str, W0)); wE = int(np.searchsorted(cal_str, AV_END, side="right")) - 1; w1 = int(np.searchsorted(cal_str, W1))
    assert cal_str[w0] == W0 and cal_str[w1] == W1, (cal_str[w0], cal_str[w1])
    log(f"== C2 開跑 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜價格快取 {meta['data_commit'][:12]}｜Form4 {L.data_commit()[:12]}｜讀法寫死 {READ_TS}"
        f"｜窗 {cal_str[w0]}～{cal_str[wE]}（可用日）／{cal_str[w1]}（結算）")
    sids = sorted(ST); sidx = {s: i for i, s in enumerate(sids)}; NS = len(sids)
    # Form 4
    F, n_all = read_form4()
    ys, yms = hist_sets(F)
    B, stB = build_buys(F, cal_str, ys, yms)
    sales, stS = build_sales(F, cal_str, ys, yms)
    log(f"[C2] Form4 {n_all} 列 ⇒ P/S form4 {len(F)}｜{stB}｜{stS}")
    # 母體與代號（K7）
    O, valid, okO, Cf, PX, CS, MM = mats(ST, sids, n)
    tick = []; col_in = []
    for tk, av in zip(B["ticker"], B["av"]):
        ch = None
        if 0 <= av < n:
            for t in sorted(tk.split(";")):
                j = sidx.get(t)
                if j is not None and MM["合併"][av, j] and okO[av, j]:
                    ch = t; break
        tick.append(ch)
    B["sid"] = tick
    B["in_win"] = (B["av"] >= w0) & (B["av"] <= wE)
    B["in_pop"] = B["in_win"] & B["sid"].notna()
    B["m4"] = [bool(MM["只400"][av, sidx[s]]) if isinstance(s, str) else False for s, av in zip(B["sid"], B["av"])]
    B["m5"] = [bool(MM["只500"][av, sidx[s]]) if isinstance(s, str) else False for s, av in zip(B["sid"], B["av"])]
    cl_idx = cluster_events(B)
    B["is_C"] = False; B.loc[cl_idx, "is_C"] = True
    B["is_B"] = B["cls"] == "機會"; B["is_D"] = B["ceo"]; B["is_A"] = True
    popst = {"窗內 A 級買進（可用日）": int(B["in_win"].sum()), "其中在母體": int(B["in_pop"].sum()), "窗內但不在母體或無有效開盤": int((B["in_win"] & ~B["in_pop"]).sum())}
    # 去重（K8）
    EV = {}
    for c in CELLS:
        d = B[B["in_pop"] & B[f"is_{c}"]].sort_values(["issuer_cik", "av", "sid", "owner1"])
        keep = []
        for iss, g in d.groupby("issuer_cik", sort=False):
            t0_ = -10 ** 9
            for ix, av in zip(g.index, g["av"]):
                if t0_ < av <= t0_ + 20:
                    continue
                keep.append(ix); t0_ = av
        EV[c] = B.loc[sorted(keep)].sort_values(["av", "sid"]).reset_index()
        log(f"[C2] {c} 原始 {len(d)} ⇒ 去重 {len(EV[c])}")
    pickle.dump({"B": B, "EV": EV}, open(os.path.join(WORK, "c2_events.pkl"), "wb"), protocol=4)
    # 事件層矩陣（K9）
    p20 = past20(Cf, valid, CS)
    insd = np.zeros((n, NS), bool)
    Pall = F[F["trans_code"] == "P"]
    avp = avail_pos(Pall["acc_date"].to_numpy(str), Pall["acc_time"].to_numpy(str), cal_str)
    for tk, av in zip(Pall["ticker"].to_numpy(), avp):
        if 0 <= av < n:
            for t in tk.split(";"):
                j = sidx.get(t)
                if j is not None:
                    insd[av, j] = True
    R = {H: fwd_ret(O, okO, PX, CS, H, w1) for H in HS}
    DEC = {}; CT = {}; EW = {}
    for col in COLS:
        pop = MM[col] & okO
        DEC[col] = deciles(p20, pop)
        for H in HS:
            CT[(col, H)] = ctrl_mean(R[H], DEC[col], insd)
            rr = np.where(pop & np.isfinite(R[H]), R[H], np.nan)
            cnt = np.isfinite(rr).sum(1)
            EW[(col, H)] = np.where(cnt > 0, np.nansum(rr, 1) / np.maximum(cnt, 1), np.nan)
    log(f"[C2] 矩陣完成 {time.time() - t0:.0f}s")

    def ar_of(ev, col, H, kind="ctrl"):
        T = ev["av"].to_numpy(int); J = np.array([sidx[s] for s in ev["sid"]], int)
        r = R[H][T, J]
        if kind == "ctrl":
            dc = DEC[col][T, J]
            base = np.where(dc >= 0, CT[(col, H)][T, np.maximum(dc, 0)], np.nan)
        else:
            base = EW[(col, H)][T]
        x = r - base
        return x, T, J

    def colmask(ev, col):
        return np.ones(len(ev), bool) if col == "合併" else (ev["m4"].to_numpy() if col == "只400" else ev["m5"].to_numpy())

    J_res = {}; rows = []
    for c in CELLS:
        ev = EV[c]
        for col in COLS:
            sub = ev[colmask(ev, col)].reset_index(drop=True)
            for H in HS:
                for kind in ("ctrl", "ew"):
                    x, T, J = ar_of(sub, col, H, kind)
                    ok = np.isfinite(x)
                    s = stat(x[ok], T[ok], cal, w0, wE)
                    key = f"{c}｜{col}｜H{H}｜{'對照同十分位' if kind == 'ctrl' else '對同日等權（描述）'}"
                    J_res[key] = s
                    rows.append({"訊號": c, "欄": col, "H": H, "對照": "同十分位無內部人買（主）" if kind == "ctrl" else "同日母體等權（描述）",
                                 "n": s.get("n", 0), "n_eff": s.get("n_eff"), "平均": s.get("平均"), "中位": s.get("中位"), "勝率": s.get("勝率"),
                                 "lo95": s.get("lo"), "hi95": s.get("hi"), "lo_Bonf": s.get("lo_Bonf"), "hi_Bonf": s.get("hi_Bonf"), "曆月數": s.get("曆月數"),
                                 "出口": s.get("出口"), "判": s.get("判"), "被剔除（硬斷點或超過窗尾）": int((~ok).sum())})
    evdf = pd.DataFrame(rows)
    # 判定（合併欄、H20、主對照）
    VERD = {c: J_res[f"{c}｜合併｜H20｜對照同十分位"]["判"] for c in CELLS}
    dirs = {}
    for c in CELLS:
        m5 = J_res[f"{c}｜只500｜H20｜對照同十分位"].get("平均"); m4 = J_res[f"{c}｜只400｜H20｜對照同十分位"].get("平均")
        dirs[c] = {"只500平均": m5, "只400平均": m4, "方向相反": bool(m5 is not None and m4 is not None and np.sign(m5) != np.sign(m4))}
    log(f"[C2 甲] 判 {VERD}")
    # 假訊號（K11）
    rng = np.random.default_rng(20261010)
    ARm = R[20] - np.where(DEC["合併"] >= 0, np.take_along_axis(CT[("合併", 20)], np.maximum(DEC["合併"], 0).astype(int), axis=1), np.nan)
    qtr = np.array([s[:4] + str((int(s[5:7]) - 1) // 3) for s in cal_str])
    PLAC = {}
    for c in CELLS:
        ev = EV[c]
        x, T, J = ar_of(ev, "合併", 20)
        ok = np.isfinite(x); T = T[ok]; J = J[ok]; real = float(np.mean(x[ok]))
        evd = defaultdict(list)
        for t_, j_ in zip(EV[c]["av"], [sidx[s] for s in EV[c]["sid"]]):
            evd[j_].append(t_)
        cands = []; nodraw = 0
        for t_, j_ in zip(T, J):
            q = qtr[t_]
            dd = np.flatnonzero((qtr == q))
            dd = dd[(dd >= w0) & (dd <= wE)]
            dd = dd[np.isfinite(ARm[dd, j_])]
            es = np.array(evd[j_], int)
            if len(es):
                bad = np.zeros(len(dd), bool)
                for e_ in es:
                    bad |= (dd >= e_) & (dd <= e_ + 20)
                dd = dd[~bad]
            if len(dd) == 0:
                nodraw += 1; continue
            cands.append((j_, dd))
        lens = np.array([len(dd) for _, dd in cands], int)
        off = np.r_[0, np.cumsum(lens)[:-1]]
        flat = np.concatenate([ARm[dd, j_] for j_, dd in cands])
        means = np.empty(1000)
        for r_ in range(1000):
            k = (rng.random(len(lens)) * lens).astype(int)
            means[r_] = float(np.mean(flat[off + k]))
        PLAC[c] = {"真平均": real, "假訊號平均的中位": float(np.median(means)), "假訊號p95": float(np.percentile(means, 95)),
                   "p（假訊號 ≥ 真）": float(np.mean(means >= real)), "抽不到候選日的事件": nodraw, "次數": 1000}
    log(f"[C2 甲] 假訊號 {PLAC}")
    # 必報（§五）
    yrs = B[B["in_pop"]].assign(年=lambda d: d["trans_date"].str[:4])
    by_year = []
    for y in sorted(set(cal_str[w0:wE + 1].astype("U4"))):
        r = {"年（事件日）": y}
        for c in CELLS:
            r[f"{c} 去重後事件"] = int(sum(1 for t_ in EV[c]["av"] if cal_str[t_][:4] == y))
        yy = B[B["in_pop"] & (pd.Series(cal_str[np.maximum(B["av"].to_numpy(int), 0)]).str[:4].to_numpy() == y)]
        r["A 級買進筆數（去重前）"] = int(len(yy))
        for k in ("機會", "例行", "不分類"):
            r[f"{k}型比例"] = float(np.mean(yy["cls"] == k)) if len(yy) else None
        r["平均買進金額（美元）"] = float(yy["amt"].mean()) if len(yy) else None
        r["中位買進金額（美元）"] = float(yy["amt"].median()) if len(yy) else None
        by_year.append(r)
    pa = B[B["in_pop"] & (B["trans_date"] >= "2023-04-01")]
    must = {"每年": by_year,
            "10b5-1 勾選比例（trans_date ≥ 2023-04-01 的 A 級買進）": float(pa["aff"].mean()) if len(pa) else None,
            "10b5-1 欄全空白比例（同上）": float(pa["aff_blank"].mean()) if len(pa) else None,
            "分類總計（母體內 A 級）": {k: int(v) for k, v in B[B["in_pop"]]["cls"].value_counts().items()},
            "D 字面版（含副總裁）事件數（去重前）": int((B["in_pop"] & B["ceo_lit"]).sum()), "D 本讀法（去重前）": int((B["in_pop"] & B["ceo"]).sum())}
    # 甲 分年、前 20 日跌幅、例行 vs 機會
    arsy = {}
    for c in CELLS:
        x, T, J = ar_of(EV[c], "合併", 20)
        dfy = pd.DataFrame({"y": cal_str[T].astype("U4"), "x": x}).dropna()
        arsy[c] = {y: {"n": int(len(g)), "平均": float(g["x"].mean())} for y, g in dfy.groupby("y")}
    pre = {}
    for c in CELLS:
        T = EV[c]["av"].to_numpy(int); J = np.array([sidx[s] for s in EV[c]["sid"]], int)
        v = p20[T, J]; dc = DEC["合併"][T, J]; v = v[np.isfinite(v)]
        pre[c] = {"n": int(len(v)), "p10": float(np.percentile(v, 10)), "p25": float(np.percentile(v, 25)), "中位": float(np.median(v)),
                  "p75": float(np.percentile(v, 75)), "p90": float(np.percentile(v, 90)), "落在最低十分位比例": float(np.mean(dc[dc >= 0] == 0)),
                  "落在最低三個十分位比例": float(np.mean(dc[dc >= 0] <= 2))}
    rvo = {}
    evA = EV["A"]
    for k in ("例行", "機會", "不分類"):
        sub = evA[evA["cls"] == k].reset_index(drop=True)
        x, T, J = ar_of(sub, "合併", 20); ok = np.isfinite(x)
        rvo[k] = stat(x[ok], T[ok], cal, w0, wE)
    rvo_diff = (rvo["機會"].get("平均") or np.nan) - (rvo["例行"].get("平均") or np.nan)
    S = {"件": "USREG-C2 內部人公開市場買進", "登錄": L.REG["C2"], "N": "N 6（美股帳）＝ 甲 4（Bonferroni 0.05／4）＋ 乙 2",
         "資料": {"價格快取": meta["data_commit"], "Form4": L.data_commit(), "Form4 檔 sha256": {f: L.sha256f(os.path.join(INS, f)) for f in sorted(os.listdir(INS)) if f.endswith(".gz") and f[6:10] >= "2013"}},
         "讀法寫死": READ_TS, "取列": stB, "賣出": stS, "母體": popst, "去重後事件": {c: int(len(EV[c])) for c in CELLS},
         "甲判定（合併欄、H20、對照同十分位）": VERD, "甲兩欄方向": dirs, "甲假訊號": PLAC, "甲": J_res, "甲分年（合併 H20）": arsy, "前20日報酬分佈": pre,
         "例行vs機會（A 內，合併 H20）": {"例行": rvo["例行"], "機會": rvo["機會"], "不分類": rvo["不分類"], "機會減例行": rvo_diff},
         "必報": must}
    evdf.to_csv(os.path.join(L.OUT, "C2_event_cells.csv"), index=False, encoding="utf-8")
    pd.DataFrame(by_year).to_csv(os.path.join(L.OUT, "C2_by_year.csv"), index=False, encoding="utf-8")
    L.jdump(L.rnd(S), "C2_summary.json")
    if a.skip_pf:
        return
    # ═════ 乙 ═════
    t1 = time.time()
    C3.pf_setup(ST, sids, cal, w0, w1)
    below = {s: ma200_below(ST[s]) for s in sids}
    abuy = defaultdict(list)
    for iss, av in zip(B["issuer_cik"], B["av"]):
        if 0 <= av < n:
            abuy[iss].append(cal_dt[av])
    abuy_dates = {k: np.array(sorted(v), "datetime64[D]") for k, v in abuy.items()}

    def mkrows(ev):
        rows_ = []
        for iss, s, e in zip(ev["issuer_cik"], ev["sid"], ev["av"]):
            e = int(e); d = ST[s]
            x, endh, why = exit_for(e, iss, below[s], sales, abuy_dates, cal_dt, w1)
            g = C3.gross_exit(d, e, x, endh)
            rows_.append({"sid": s, "entry_pos": e, "xpos": x, "g": g, "endhold": endh, "why": why})
        return rows_
    bref = C3.bench_row(cal, w0, w1)
    arms = {}; ROWS = {}
    for c in ("B", "C"):
        for col in COLS:
            ev = EV[c][colmask(EV[c], col)]
            rws = mkrows(ev); ROWS[(c, col)] = rws
            sig, endh, xp = C3.pf_sig(rws)
            arms[f"{c}｜{col}｜主"] = {"sig": sig, "endhold": endh, "xp": xp, "seg": (w0, w1)}
        for H in HS:
            fr_ = C3.fixed_rows(ROWS[(c, "合併")], H, w1, C3._S["closes"], C3._S["opens"])
            sig, endh, xp = C3.pf_sig(fr_)
            arms[f"{c}｜合併｜固定{H}日"] = {"sig": sig, "endhold": endh, "xp": xp, "seg": (w0, w1)}
    res = C3.pf_run(arms, procs=a.procs, nseed=a.nseed)
    PF = {k: C3.pf_agg(v, bref) for k, v in res.items()}
    log(f"[C2 乙] 主 {[(k, PF[k]['標籤'], round(PF[k]['年化中位'], 4)) for k in PF if k.endswith('主')]}｜{time.time() - t1:.0f}s")
    # 敏感度（合格或另列）
    sens = {}
    for c in ("B", "C"):
        if PF[f"{c}｜合併｜主"]["標籤"] in ("合格", "另列"):
            arm2 = {}
            for cost in (0.0002, 0.0010):
                a2 = dict(arms[f"{c}｜合併｜主"]); a2["cost"] = cost; arm2[f"{c}｜合併｜成本{cost}"] = a2
            r2 = C3.pf_run(arm2, procs=a.procs, nseed=a.nseed)
            sens.update({k: C3.pf_agg(v, bref) for k, v in r2.items()})
    # 出場原因、配對差
    reasons = {}
    for (c, col), rws in ROWS.items():
        cc = Counter(r["why"] for r in rws)
        reasons[f"{c}｜{col}"] = {k: v / max(1, len(rws)) for k, v in cc.items()} | {"訊號筆數": len(rws)}
    pair = {}
    for c in ("B", "C"):
        mc = np.array([x["cagr"] for x in res[f"{c}｜合併｜主"]])
        for H in HS:
            fc = np.array([x["cagr"] for x in res[f"{c}｜合併｜固定{H}日"]])
            pair[f"{c}｜主−固定{H}日（逐種子年化差中位）"] = float(np.median(mc - fc))
    yrsN = (w1 - w0 + 1) / L.ANN
    turn = {k: PF[k]["交易數中位"] / yrsN for k in PF if k.endswith("主")}
    # 假訊號（K14）
    rng2 = np.random.default_rng(20261011)
    PL2 = {}
    for c in ("B", "C"):
        base = ROWS[(c, "合併")]
        okday = {s: np.flatnonzero(MM["合併"][w0:wE + 1, sidx[s]] & okO[w0:wE + 1, sidx[s]]) + w0 for s in set(r["sid"] for r in base)}
        iss_of = dict(zip(EV[c]["sid"], EV[c]["issuer_cik"]))
        parms = {}
        for r_ in range(200):
            rws = []
            for r0 in base:
                s = r0["sid"]; dd = okday[s]
                e = int(dd[rng2.integers(0, len(dd))])
                x, endh, why = exit_for(e, iss_of[s], below[s], sales, abuy_dates, cal_dt, w1)
                rws.append({"sid": s, "entry_pos": e, "xpos": x, "g": C3.gross_exit(ST[s], e, x, endh), "endhold": endh})
            sig, endh, xp = C3.pf_sig(rws)
            parms[f"PL{c}{r_}"] = {"sig": sig, "endhold": endh, "xp": xp, "seg": (w0, w1)}
        rr = C3.pf_run(parms, procs=a.procs, nseed=1)
        cg = np.array([v[0]["cagr"] for v in rr.values()]); md = np.array([v[0]["mdd"] for v in rr.values()])
        real = PF[f"{c}｜合併｜主"]["年化中位"]
        labs = [C3.pf_label(x_, y_, bref)[0] for x_, y_ in zip(cg, md)]
        PL2[c] = {"真年化中位": real, "假訊號年化中位": float(np.median(cg)), "p（假訊號年化 ≥ 真）": float(np.mean(cg >= real)),
                  "假訊號合格比例": float(np.mean([l_ == "合格" for l_ in labs])), "假訊號另列比例": float(np.mean([l_ == "另列" for l_ in labs])), "次數": 200}
    log(f"[C2 乙] 假訊號 {PL2}")
    # 等效獨立檔數（K15）
    me = L.month_end_mask(cal_str)
    rets = np.vstack([np.full((1, NS), np.nan), Cf[1:] / Cf[:-1] - 1.0])
    rets[~valid] = np.nan
    NEFF = {}
    for c in ("B", "C"):
        a0 = arms[f"{c}｜合併｜主"]; aud = []
        R11.COST = C3.COST
        R11.simulate_mtm(a0["sig"], C3.RULE, C3.N_SLOTS, np.random.default_rng(C3.SEED0), C3._S["closes"], C3._S["opens"], C3._S["ncal"],
                         return_equity=True, pick=None, d_max=None, queue_days=0, cash_mode="zero", tradable=C3._S["trad"], delist=C3._S["dl"], audit=aud)
        held = np.zeros((n, NS), bool); buy = {}
        for x in aud:
            if x["side"] == "buy":
                buy[x["sid"]] = int(x["t"])
            elif x["side"] == "sell" and x["sid"] in buy:
                held[buy.pop(x["sid"]):int(x["t"]), sidx[x["sid"]]] = True
        for s_, b_ in buy.items():
            held[b_:w1 + 1, sidx[s_]] = True
        vals = []; ks = []
        for t in np.flatnonzero(me[w0:w1 + 1]) + w0:
            j = np.flatnonzero(held[t])
            if len(j) < 2 or t < 120:
                continue
            X = pd.DataFrame(rets[t - 119:t + 1][:, j]).corr().to_numpy()
            iu = np.triu_indices(len(j), 1); rho = np.nanmean(X[iu])
            if np.isfinite(rho):
                vals.append(len(j) / (1 + (len(j) - 1) * rho)); ks.append(len(j))
        NEFF[c] = {"月底數": len(vals), "平均持股檔數": float(np.mean(ks)) if ks else None, "等效獨立檔數（月平均）": float(np.mean(vals)) if vals else None,
                   "等效獨立檔數（月中位）": float(np.median(vals)) if vals else None}
    S2 = {"判準": bref, "主": {k: PF[k] for k in PF if k.endswith("主")}, "固定天數（描述）": {k: PF[k] for k in PF if "固定" in k},
          "成本敏感度": sens, "出場原因（訊號層）": reasons, "主減固定天數": pair, "每年交易筆數（中位÷年）": turn, "假訊號": PL2, "等效獨立檔數": NEFF,
          "標籤（合併欄判定）": {c: PF[f"{c}｜合併｜主"]["標籤"] for c in ("B", "C")},
          "兩欄方向": {c: {"只500年化中位": PF[f"{c}｜只500｜主"]["年化中位"], "只400年化中位": PF[f"{c}｜只400｜主"]["年化中位"],
                          "只500標籤": PF[f"{c}｜只500｜主"]["標籤"], "只400標籤": PF[f"{c}｜只400｜主"]["標籤"]} for c in ("B", "C")},
          "偏向存活股": C3.SURV, "秒": round(time.time() - t1)}
    S["乙"] = S2
    S["秒"] = round(time.time() - t0)
    pfrows = [{"臂": k, **{kk: vv for kk, vv in v.items() if not isinstance(vv, (dict, list))}} for k, v in PF.items()]
    pd.DataFrame(pfrows).to_csv(os.path.join(L.OUT, "C2_pf.csv"), index=False, encoding="utf-8")
    L.jdump(L.rnd(S), "C2_summary.json")
    log(f"[C2] 完成 {S['秒']}s")


if __name__ == "__main__":
    main()
