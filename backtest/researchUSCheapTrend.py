# -*- coding: utf-8 -*-
"""美股「便宜＋趨勢轉強」【合理價機械版判為可買之後，再切季線年線趨勢四態】——正式程式（含頻率表／全部描述欄乾跑）。

登錄：登錄全文-美股便宜加趨勢轉強_合理價可買再切趨勢四態_美股策略線_seq1_sha68b7253a5f696d15-3718B-20261028-1452.md
      （整檔 3718 B、整檔 sha256 前 16 碼＝68b7253a5f696d15；回測線 2026-10-28 已驗，開跑再驗一次）
發號：裁定 seq482 §二（主格 N_單筆 +1；組合 N_組合 +1；3 年只描述）。
沿革：裁定 seq484 §一（2026-10-28）：★T8 群數下限適用全線〈四十九〉③（不算替登錄加規則）⇒ 主格 7 群 < 24 ⇒ 依構造還沒測；
      准正式跑（閘門 seq482 → seq484），判語事先固定「還沒測（依構造，7 群 < 24）」，報酬（含組合、對大盤）只當描述，
      ⛔ 不得寫成測不出或測到了。主格口徑＝可買∩T2 單獨、1 年；台股主格＝T1∪T2、60 日 ⇒ 台美主格口徑不同（結果必寫）。
      看報酬前只看過頻率表。
便宜：美股合理價機械版【原樣】（產業 seq63；★15、★16 照裁定 seq481）＝ backtest/researchUSFairValue_freq.py 的逐檔分類，
      經 backtest/researchUSFairValue.py 的 load_groups() 讀 ~/us_work/fairvalue/classify_by_eval_ticker.csv（⛔ 不改那兩支程式）。
資料：私有庫 us-stock-data 89d9f8550（唯讀快照 ~/usdata/89d9f8550；.commit 開跑先驗）。
私有：repo 的 resultsUSCheapTrend/ 只放筆數與彙總；逐檔趨勢明細只寫 ~/us_work/cheaptrend/（repo 外）。

用法（cd ~/tw-p17）：
    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSCheapTrend --dry
        ⇒ 頻率表＋全部描述欄乾跑（持有報酬與大盤全寫 0；⛔ 不讀出、不印任何報酬）→ backtest/resultsUSCheapTrend/freq/
    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSCheapTrend --formal --ruling seq484
        ⇒ 正式跑（⛔ 兩個旗標都要，否則拒跑）→ backtest/resultsUSCheapTrend/formal/

══════════ 登錄寫死的（照抄，不改）══════════
 便宜：seq63 的母體、評估日（每季末前一個交易日，2019-03-29～2025-09-29，27 個）、品質四門檻、合理價、分組
       （可買 ≤1.00／接近 1.00～1.15／偏貴 >1.15）、報酬（panel ret 連乘 250 日含息；下市照 seq63）全部照舊。
 趨勢：評估日收盤、還原價；MA60、MA250；上揚＝今日均線 ＞ 20 個交易日前均線，下彎＝其餘。依序判、先中先算：
       T1 多頭＝收盤＞MA60 且 MA60 上揚 且 收盤＞MA250｜T2 剛轉強＝收盤＞MA60 且（MA60 下彎 或 收盤≤MA250）｜
       T3 長多回檔＝收盤≤MA60 且 收盤＞MA250 且 MA250 上揚｜T4 空頭＝收盤≤MA60 且 收盤≤MA250 且 MA60、MA250 都下彎｜T0 其他。
       價格歷史不足 250＋20 日 ⇒ 趨勢不可判（照報筆數、不入任何趨勢組）。
 主格（1 年）：每評估日「可買∩T2 平均 − 可買∩其他四態 平均」取平均 ＞0、進場年分群 bootstrap 95% CI 下緣 ＞0、
       前段（2019–2021 進場）後段（2022–2025）各 ＞0 ⇒「趨勢轉強有加分」；其餘「測不出」（負也寫測不出）。
 組合：可買∩T2 每評估日開一袖、持 250 日、袖內同權，對 ^SP500TR：年化 ＞ 大盤 且 年化÷|最大回落| ≥ 大盤同比值；只過年化 ⇒ 另列。
 樣本不足：主格任一組在一半以上評估日 ＜3 檔 ⇒ 不下判定。3 年只描述。
 描述：可買∩T2｜可買∩T4｜偏貴∩T2｜母體全部；另 可買∩T1、可買∩T3、可買全部；每組每評估日檔數、1 年與 3 年平均與中位、對大盤超額；
       假訊號：每評估日從可買隨機抽與可買∩T2 同數 1,000 次 ⇒ 主格差的隨機分布、p 值。

══════════ ★ 執行者定（另一讀法寫在〔〕；看任何數字前寫死；皆取保守／字面）══════════
 ★T1 還原價＝該檔 panel 的 ret 連乘（＝seq63 報酬同一來源：含息、分割已處理、src 帶 * 的拆股＋配息同日已改收盤價），
     只用 date ≤ 評估日的列；第一列與 ret 空白列（來源切換日、ret_blank 壞列）記 0（同 seq63 正式程式「切換日記 0」）。
     〔另一讀法：評估日 panel src 那個價格檔的整段還原價（Yahoo adjclose／Tiingo adjClose）；兩讀法趨勢態不同的筆數照報（只報筆數）〕
 ★T2 交易日＝該檔 panel 的列（gap 段沒有列 ⇒ 不算一日；跨日列照算一列）。MA60／MA250＝含評估日在內最近 60／250 列的還原價平均；
     「20 個交易日前均線」＝往前第 20 列那天的均線。
     〔另一讀法：依 yahoo_GSPC 日曆，270 日窗內有缺列 ⇒ 不可判；窗內有缺列的筆數照報〕
 ★T3 可判＝評估日（含）以前 panel 列數 ≥ 270（MA250 在第 20 列前也要算得出）；評估日沒有 panel 列 ⇒ 不可判。
 ★T4 不等式照字面：線上＝收盤 ＞ 均線（相等算線下）；上揚＝均線 ＞ 20 列前均線（相等算下彎）。
 ★T5 主格對照組「可買∩其他四態」＝ 可買裡趨勢可判且不是 T2 的（T1＋T3＋T4＋T0 合併；五類去掉剛轉強剩四類）。
     〔另一讀法：只 T0「其他」；該讀法的樣本不足筆數照報（只報筆數）〕。趨勢不可判兩組都不進。
 ★T6 diff_d 只在兩組都非空的評估日才有（同 seq63 正式程式 ★R4）；空的報筆數。
 ★T7 樣本不足：主格兩組（可買∩T2、可買∩其他四態）任一組 ＜3 檔的評估日數 ≥ 27/2（＝≥14 日）⇒ 不下判定（優先於判定）。
     檔數＝該組 1 年窗走得完的筆數（27 個評估日 1 年窗都完整 ⇒ 等於集合大小）。
 ★T8 分群＝進場年（評估日的年），預期 7 群（前段 3、後段 4）；登錄沒寫群數下限 ⇒ 不設群數閘、照報群數。
     〔另一讀法：比照台股版「每段群數 ≥ 24」⇒ 依構造還沒測；這是改規則，⛔ 不採，交裁定〕
     〔沿革：裁定 seq484 §一 裁〈四十九〉適用 ⇒ 7 群 < 24 ⇒ 依構造還沒測；判語固定，見檔頭沿革〕
 ★T9 bootstrap：登錄沒寫次數與種子 ⇒ 照 seq63 正式程式 10,000 次、百分位法；種子 20261028（本登錄日）。
 ★T10 組合：空袖＝現金 0%；年化＝NAV^(252/日數)−1；最大回落 0 ⇒ 比值記 None（不除 0，判「不可比」）；
      區間＝第一個評估日次日到最後一袖結束；^SP500TR＝data/macro/yahoo_SP500TR.csv adjclose（同 seq63 ★R6～R8）。
      判定三態：兩條都過＝通過｜只過年化＝另列（只過年化）｜其餘＝不通過。
 ★T11 假訊號：每評估日從「可買且趨勢可判」不放回抽 k＝|可買∩T2| 檔，對照組＝同日可買可判的其餘檔，diff 照主格算法對評估日平均；
      1,000 次、種子 20261028；p＝(1＋#{假 ≥ 真})/(1＋1000)（單尾）。
      〔另一讀法：從全部可買（含趨勢不可判）抽、對照組固定為可買∩其他四態〕
 ★T12 描述「母體全部」＝ seq63 分類 stage＝pop（freq 表「母體」欄：在指數有價格、市值 ≥100 億）。〔另一讀法：過門檻全部〕
      「可買全部」＝ seq63 可買組（含趨勢不可判者）。
 ★T13 描述統計：每評估日 n、平均、中位、平均超額（每筆 − 同窗 ^SP500TR 累積）；彙總＝各評估日平均的平均、全部筆中位、
      各評估日超額的平均；3 年只收 750 日窗走得完的評估日（同 seq63 ★R3）。持有報酬全部用 seq63 正式程式的 Holder（同規則）。
 ★T14 對齊台股描述格（不判、不計 N）：可買∩轉強（T1∪T2）vs 可買∩沒轉強（T3∪T4∪T0），持有 60 個交易日，
      同評估日收盤進場、同 Holder；不加台股成本。注意 T1∪T2 恆等於「收盤 ＞ MA60」（seq377 等價，見 equivalence）。
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import io
import json
import os
import sys
from collections import Counter

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchUSFairValue_freq as FQ   # noqa: E402
from backtest import researchUSFairValue as FV         # noqa: E402

REG_NAME = ("登錄全文-美股便宜加趨勢轉強_合理價可買再切趨勢四態_美股策略線_seq1_sha68b7253a5f696d15-3718B-20261028-1452.md")
REG_DIR = os.environ.get("US_CT_REG_DIR", "/mnt/c/SynologyDrive/跨線信箱")
REG_SHA16, REG_BYTES = "68b7253a5f696d15", 3718
RULING = "seq484"                      # 正式跑閘門（沿革：seq482 → seq484）
FIXED_VERDICT = "還沒測（依構造，7 群 < 24）"   # 裁定 seq484 §一：事先固定，不看數字
RESULT_SENTENCES = [
    "台美主格口徑不同（台股 T1∪T2、60 日；美股 T2、1 年）",
    "依構造還沒測：進場年分群 7 群 < 24（〈四十九〉，裁定 seq484 §一）；報酬只當描述",
    "對齊台股描述格的『轉強』T1∪T2 恆等於收盤 > MA60（seq377 等價）；只描述、不判",
]
DATA_PIN = "89d9f8550f6ea39b392087c22998cd298164a26c"
HERE = os.path.dirname(os.path.abspath(__file__))
OUTD = os.path.join(HERE, "resultsUSCheapTrend", "freq")
FORMALD = os.path.join(HERE, "resultsUSCheapTrend", "formal")
PRIVD = os.path.expanduser("~/us_work/cheaptrend")

L60, L250, SLOPE = 60, 250, 20
NEED = L250 + SLOPE                    # ★T3 270 列
H1, H3, H60 = 250, 750, 60
SEED, NBOOT, NFAKE = 20261028, 10000, 1000
FRONT, BACK = (2019, 2021), (2022, 2025)
MIN_N = 3
NA = -1                                # 趨勢不可判
SNAME = {1: "T1多頭", 2: "T2剛轉強", 3: "T3長多回檔", 4: "T4空頭", 0: "T0其他", NA: "不可判"}


# ═════════════ 趨勢四態（純函式）═════════════
def classify_state(c, m60, m60p, m250, m250p):
    """單點：依序判、先中先算（照登錄 §二字面）。"""
    a60, a250 = c > m60, c > m250
    u60, u250 = m60 > m60p, m250 > m250p
    if a60 and u60 and a250:
        return 1
    if a60 and ((not u60) or (not a250)):
        return 2
    if (not a60) and a250 and u250:
        return 3
    if (not a60) and (not a250) and (not u60) and (not u250):
        return 4
    return 0


def _ma(px, L):
    px = np.asarray(px, float)
    out = np.full(len(px), np.nan)
    if len(px) >= L:
        out[L - 1:] = np.lib.stride_tricks.sliding_window_view(px, L).mean(axis=1)
    return out


def trend_states(px):
    """px：還原價（依列序）。→ dict：ma60、ma250、ma60p、ma250p、state（NA＝不可判）。
    第 k 列只用第 0..k 列（PIT）；k＋1 < 270 ⇒ 不可判。"""
    px = np.asarray(px, float)
    n = len(px)
    m60, m250 = _ma(px, L60), _ma(px, L250)
    m60p = np.full(n, np.nan)
    m250p = np.full(n, np.nan)
    m60p[SLOPE:] = m60[:-SLOPE] if n > SLOPE else m60p[SLOPE:]
    m250p[SLOPE:] = m250[:-SLOPE] if n > SLOPE else m250p[SLOPE:]
    a60, a250 = px > m60, px > m250
    u60, u250 = m60 > m60p, m250 > m250p
    c1 = a60 & u60 & a250
    c2 = a60 & ((~u60) | (~a250))
    c3 = (~a60) & a250 & u250
    c4 = (~a60) & (~a250) & (~u60) & (~u250)
    st = np.select([c1, c2, c3, c4], [1, 2, 3, 4], default=0)
    valid = (np.arange(n) + 1 >= NEED) & np.isfinite(m250p) & np.isfinite(m60p)
    st = np.where(valid, st, NA)
    return {"ma60": m60, "ma250": m250, "ma60p": m60p, "ma250p": m250p, "state": st,
            "a60": a60, "a250": a250, "u60": u60, "u250": u250}


# ═════════════ 價格（★T1／★T2）═════════════
@functools.lru_cache(maxsize=None)
def adj_series(t):
    """★T1：panel ret 連乘；ret 空白記 0。→ Series（index＝panel 列日期）或 None。"""
    pn = FQ.panel(t)
    if pn is None or len(pn) == 0:
        return None
    r = pd.to_numeric(pn["ret"], errors="coerce").values.astype(float)
    r[~np.isfinite(r)] = 0.0
    return pd.Series(np.cumprod(1.0 + r), index=pn.index)


@functools.lru_cache(maxsize=None)
def trend_table(t):
    s = adj_series(t)
    if s is None:
        return None
    tr = trend_states(s.values)
    df = pd.DataFrame({k: tr[k] for k in ("ma60", "ma250", "ma60p", "ma250p", "state", "a60", "a250", "u60", "u250")},
                      index=s.index)
    df["px"] = s.values
    df["nrow"] = np.arange(1, len(s) + 1)
    return df


@functools.lru_cache(maxsize=None)
def alt_table(src):
    """★T1 另一讀法：src 價格檔整段還原價（Yahoo adjclose／Tiingo adjClose）。"""
    kind, f = src.split(":", 1)
    if kind == "yahoo":
        d = pd.read_csv(FQ._p("prices_yahoo", f + ".csv"), usecols=["date", "adjclose"], dtype={"date": str})
        s = pd.Series(d["adjclose"].values, index=pd.to_datetime(d["date"])).astype(float)
    else:
        d = pd.read_csv(FQ._p("prices", f + ".csv"), usecols=["date", "adjClose"], dtype={"date": str})
        s = pd.Series(d["adjClose"].values, index=pd.to_datetime(d["date"])).astype(float)
    s = s[s.notna() & (s > 0)].sort_index()
    tr = trend_states(s.values)
    return pd.DataFrame({"state": tr["state"]}, index=s.index)


def state_at(t, d):
    """→ (state, info dict)。只看 date ≤ d 的列。"""
    d = pd.Timestamp(d)
    tb = trend_table(t)
    if tb is None or d not in tb.index:
        return NA, {"why": "no_row"}
    row = tb.loc[d]
    info = {"why": "ok" if row["state"] != NA else "short", "nrow": int(row["nrow"])}
    for k in ("px", "ma60", "ma250", "ma60p", "ma250p"):
        info[k] = float(row[k])
    for k in ("a60", "a250", "u60", "u250"):
        info[k] = bool(row[k])
    # ★T2 另一讀法：270 列窗內有沒有缺列（以 yahoo_GSPC 日曆計）
    if info["nrow"] >= NEED:
        i = tb.index.get_loc(d)
        first = tb.index[i - NEED + 1]
        cal = FQ.calendar()
        ncal = int(cal.searchsorted(d, side="right") - cal.searchsorted(first, side="left"))
        info["win_gap"] = bool(ncal != NEED)
    else:
        info["win_gap"] = None
    # ★T1 另一讀法
    pn = FQ.panel(t)
    src = pn.loc[d, "src"]
    try:
        at = alt_table(src)
        info["alt_state"] = int(at.loc[d, "state"]) if d in at.index else NA
    except FileNotFoundError:
        info["alt_state"] = NA
    return int(row["state"]), info


# ═════════════ 登錄驗證、閘門 ═════════════
def verify_registration():
    p = os.path.join(REG_DIR, REG_NAME)
    b = open(p, "rb").read()
    whole = hashlib.sha256(b).hexdigest()
    lines = b.decode("utf-8").splitlines(keepends=True)
    pw1 = hashlib.sha256("".join(lines[:-1]).encode("utf-8")).hexdigest()
    out = {"bytes": len(b), "整檔sha256": whole, "去末行sha256": pw1}
    if len(b) != REG_BYTES:
        raise RuntimeError("登錄檔大小 %d ≠ %d" % (len(b), REG_BYTES))
    if whole.startswith(REG_SHA16):
        out["相符"] = "整檔"
    elif pw1.startswith(REG_SHA16):
        out["相符"] = "去末行（pw1）"
    else:
        raise RuntimeError("登錄檔 sha 不符")
    return out


def gate(argv):
    """→ 'dry' | 'formal' | ('refuse', 訊息)。"""
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--formal", action="store_true")
    ap.add_argument("--ruling", default=None)
    try:
        a, rest = ap.parse_known_args(argv)
    except SystemExit:
        return ("refuse", "參數錯")
    if rest:
        return ("refuse", "不認得的參數 %s" % rest)
    if a.dry and a.formal:
        return ("refuse", "--dry 與 --formal 不可併用")
    if a.formal:
        if a.ruling != RULING:
            return ("refuse", "⛔ 拒跑正式：要 --formal --ruling %s" % RULING)
        return "formal"
    if a.dry:
        if a.ruling is not None:
            return ("refuse", "--dry 不帶 --ruling")
        return "dry"
    return ("refuse", "⛔ 沒給模式：乾跑 --dry；正式 --formal --ruling %s" % RULING)


# ═════════════ 分組與趨勢 ═════════════
def load_sets():
    if FQ.DATA_COMMIT_FULL != DATA_PIN or FV.DATA_PIN != DATA_PIN:
        raise RuntimeError("合理價程式的資料 commit 與本件寫死的不同")
    FQ.assert_pinned()
    G = FV.load_groups()                       # 驗 freq_summary 的資料 commit
    R = pd.read_csv(os.path.join(FQ.PRIVD, "classify_by_eval_ticker.csv"), dtype={"eval": str, "ticker": str},
                    usecols=["eval", "ticker", "stage"], low_memory=False)
    for d, x in R[R["stage"] == "pop"].groupby("eval"):
        G[d]["母體"] = sorted(x["ticker"])
    ev = [str(t.date()) for t in FQ.eval_dates()]
    if sorted(G) != ev:
        raise RuntimeError("分組檔的評估日與 eval_dates() 不同")
    # 與 freq 表逐日對帳
    T = pd.read_csv(os.path.join(FQ.OUTD, "freq_by_eval.csv"), encoding="utf-8-sig", dtype={"eval": str})
    for _, r in T.iterrows():
        for g in ("可買", "接近", "偏貴", "母體", "過門檻全部"):
            if int(r[g]) != len(G[r["eval"]][g]):
                raise RuntimeError("%s %s 筆數與 freq_by_eval.csv 不符" % (r["eval"], g))
    return G


def build_states(G):
    rows = []
    for d in sorted(G):
        grp = {}
        for g in ("可買", "接近", "偏貴"):
            for t in G[d][g]:
                grp[t] = g
        for t in G[d]["母體"]:
            s, info = state_at(t, d)
            rows.append(dict(eval=d, ticker=t, group=grp.get(t, "不在組"), state=s, **info))
    return pd.DataFrame(rows)


def arms(S, d):
    x = S[S["eval"] == d]
    buy = x[x["group"] == "可買"]
    ok = buy[buy["state"] != NA]
    A = {
        "可買全部": list(buy["ticker"]),
        "可買可判": list(ok["ticker"]),
        "可買∩T1": list(ok.loc[ok["state"] == 1, "ticker"]),
        "可買∩T2": list(ok.loc[ok["state"] == 2, "ticker"]),
        "可買∩T3": list(ok.loc[ok["state"] == 3, "ticker"]),
        "可買∩T4": list(ok.loc[ok["state"] == 4, "ticker"]),
        "可買∩T0": list(ok.loc[ok["state"] == 0, "ticker"]),
        "可買∩其他四態": list(ok.loc[ok["state"] != 2, "ticker"]),
        "可買∩轉強T1∪T2": list(ok.loc[ok["state"].isin([1, 2]), "ticker"]),
        "可買∩沒轉強T3∪T4∪T0": list(ok.loc[ok["state"].isin([3, 4, 0]), "ticker"]),
        "偏貴∩T2": list(x.loc[(x["group"] == "偏貴") & (x["state"] == 2), "ticker"]),
        "母體全部": list(x["ticker"]),
    }
    return A


DESC_GROUPS = ("可買∩T2", "可買∩T4", "偏貴∩T2", "母體全部", "可買∩T1", "可買∩T3", "可買全部")


# ═════════════ 頻率表（只筆數）═════════════
def freq(S, G):
    rows = []
    for d in sorted(G):
        x = S[S["eval"] == d]
        A = arms(S, d)
        buy = x[x["group"] == "可買"]
        okb = buy[buy["state"] != NA]
        t2 = okb[okb["state"] == 2]
        r = {"eval": d, "母體": len(x), "母體_不可判": int((x["state"] == NA).sum())}
        for k in (1, 2, 3, 4, 0):
            r["母體∩" + SNAME[k]] = int((x["state"] == k).sum())
        r["可買"] = len(buy)
        r["可買_不可判"] = int((buy["state"] == NA).sum())
        r["可買_不可判_無列"] = int((buy["why"] == "no_row").sum())
        for k in (1, 2, 3, 4, 0):
            r["可買∩" + SNAME[k]] = int((buy["state"] == k).sum())
        r["主格_可買∩T2"] = len(A["可買∩T2"])
        r["主格_可買∩其他四態"] = len(A["可買∩其他四態"])
        r["另讀_可買∩T0"] = len(A["可買∩T0"])
        r["對齊台股_可買∩轉強T1∪T2"] = len(A["可買∩轉強T1∪T2"])
        r["對齊台股_可買∩沒轉強"] = len(A["可買∩沒轉強T3∪T4∪T0"])
        r["偏貴"] = len(G[d]["偏貴"])
        r["偏貴∩T2"] = len(A["偏貴∩T2"])
        r["接近∩T2"] = int(((x["group"] == "接近") & (x["state"] == 2)).sum())
        # T2 的成因拆解（等價檢查用）
        r["T2a_MA60下彎且收盤>MA250"] = int(((~t2["u60"].astype(bool)) & t2["a250"].astype(bool)).sum())
        r["T2b_MA60上揚且收盤≤MA250"] = int((t2["u60"].astype(bool) & ~t2["a250"].astype(bool)).sum())
        r["T2c_MA60下彎且收盤≤MA250"] = int(((~t2["u60"].astype(bool)) & ~t2["a250"].astype(bool)).sum())
        # 另一讀法筆數
        r["可買可判_窗內缺列(★T2另讀)"] = int((okb["win_gap"] == True).sum())  # noqa: E712
        r["可買_價格另讀態不同(★T1另讀)"] = int((buy["state"] != buy["alt_state"]).sum())
        r["母體_價格另讀態不同(★T1另讀)"] = int((x["state"] != x["alt_state"]).sum())
        r["主格_T2<3"] = r["主格_可買∩T2"] < MIN_N
        r["主格_其他四態<3"] = r["主格_可買∩其他四態"] < MIN_N
        r["另讀_T0<3"] = r["另讀_可買∩T0"] < MIN_N
        r["描述_可買∩T4<3"] = r["可買∩T4空頭"] < MIN_N
        r["描述_偏貴∩T2<3"] = r["偏貴∩T2"] < MIN_N
        r["兩組都非空"] = (r["主格_可買∩T2"] > 0 and r["主格_可買∩其他四態"] > 0)
        rows.append(r)
    return pd.DataFrame(rows)


def insufficient(T, cols):
    half = len(T) / 2.0
    out = {}
    for c in cols:
        n = int((T[c] < MIN_N).sum())
        out[c] = {"<3的評估日數": n, "門檻(≥一半)": half, "觸發": bool(n >= half),
                  "<3的評估日": list(T.loc[T[c] < MIN_N, "eval"])}
    out["觸發"] = any(v["觸發"] for v in out.values() if isinstance(v, dict))
    return out


def armstats(T, c):
    v = T[c]
    return {"中位": float(v.median()), "最小": int(v.min()), "最大": int(v.max()), "平均": round(float(v.mean()), 2),
            "合計": int(v.sum()), "0檔評估日": int((v == 0).sum())}


# ═════════════ 報酬路徑（正式＝真值；乾跑＝0）═════════════
class Index:
    def __init__(self, dry):
        self.dry = dry
        self.cal = FQ.calendar()
        if not dry:
            b = pd.read_csv(FQ._p("macro", "yahoo_SP500TR.csv"), usecols=["date", "adjclose"], dtype={"date": str})
            self.b = pd.Series(b["adjclose"].values, index=pd.to_datetime(b["date"])).sort_index()

    def daily(self, d0_idx, n):
        """日曆位置 d0_idx 之後 n 日的日報酬。"""
        if self.dry:
            return np.zeros(n)
        b = self.b.reindex(self.cal[d0_idx:d0_idx + n + 1])
        if b.isna().any():
            raise RuntimeError("^SP500TR 有缺日")
        return b.values[1:] / b.values[:-1] - 1.0

    def cum(self, d, H):
        i = self.cal.get_loc(pd.Timestamp(d))
        if i + H >= len(self.cal):
            return None
        return float(np.prod(1.0 + self.daily(i, H)) - 1.0)


def compute(mode, S, G):
    dry = (mode == "dry")
    hd = FV.Holder(dry)
    ix = Index(dry)
    evals = sorted(G)
    A = {d: arms(S, d) for d in evals}
    res = {"mode": mode, "資料commit": FQ.data_commit(), "評估日數": len(evals)}

    # ── 每筆持有累積（cache）──
    cache = {}

    def cumr(t, d, H):
        k = (t, d, H)
        if k not in cache:
            x = hd.daily(t, d, H, count=False)
            cache[k] = None if x is None else FV.cum(x)
        return cache[k]

    def stats(names, d, H):
        v = [cumr(t, d, H) for t in names]
        v = [x for x in v if x is not None]
        ib = ix.cum(d, H)
        if not v:
            return {"n": 0, "平均": None, "中位": None, "超額平均": None}, v
        return {"n": len(v), "平均": float(np.mean(v)), "中位": float(np.median(v)),
                "超額平均": (float(np.mean(v)) - ib) if ib is not None else None}, v

    # ── 主格（1 年）＋ 3 年描述 ──
    per = {}
    for H, tag in ((H1, "1y"), (H3, "3y")):
        rows = []
        for d in evals:
            a, _ = stats(A[d]["可買∩T2"], d, H)
            b, _ = stats(A[d]["可買∩其他四態"], d, H)
            rows.append({"eval": d, "n_T2": a["n"], "n_其他四態": b["n"], "T2": a["平均"], "其他四態": b["平均"],
                         "diff": (a["平均"] - b["平均"]) if (a["平均"] is not None and b["平均"] is not None) else None})
        per[tag] = pd.DataFrame(rows)
    T1y = per["1y"].dropna(subset=["diff"])
    by_year = {}
    for d, x in zip(T1y["eval"], T1y["diff"]):
        by_year.setdefault(int(d[:4]), []).append(x)
    by_year = {y: np.array(v) for y, v in by_year.items()}
    if FV.NBOOT != NBOOT:
        raise RuntimeError("bootstrap 次數與 seq63 程式不同")
    lo, hi = FV.boot_ci(by_year, np.random.default_rng(SEED))
    avg = float(T1y["diff"].mean()) if len(T1y) else None
    yrs = T1y["eval"].str[:4].astype(int)
    fr = T1y.loc[yrs.between(*FRONT), "diff"]
    bk = T1y.loc[yrs.between(*BACK), "diff"]
    front = float(fr.mean()) if len(fr) else None
    back = float(bk.mean()) if len(bk) else None
    ins = insufficient(per["1y"], ["n_T2", "n_其他四態"])
    if ins["觸發"]:
        verdict = "樣本不足（不下判定）"
    elif None in (avg, lo, front, back):
        verdict = "測不出（有格不可算）"
    elif avg > 0 and lo > 0 and front > 0 and back > 0:
        verdict = "趨勢轉強有加分"
    else:
        verdict = "測不出"
    if mode == "formal":
        verdict = final_verdict()           # ⛔ 不看數字：裁定 seq484 §一
    res["主格_1年"] = {"diff平均": avg, "CI95": [lo, hi], "前段2019-2021": front, "後段2022-2025": back,
                     "有diff的評估日": int(len(T1y)), "兩組有空的評估日": int(len(per["1y"]) - len(T1y)),
                     "分群數": len(by_year), "前段群數": int(sum(1 for y in by_year if FRONT[0] <= y <= FRONT[1])),
                     "後段群數": int(sum(1 for y in by_year if BACK[0] <= y <= BACK[1])),
                     "樣本不足": ins, "判定": verdict}
    if mode == "formal":
        res["主格_1年"]["判定依據"] = ("裁定 seq484 §一：〈四十九〉適用，%d 群 < 24 ⇒ 依構造還沒測；判語事先固定，"
                                    "以上數字只當描述，⛔ 不得寫成測不出或測到了" % len(by_year))
    T3y = per["3y"].dropna(subset=["diff"])
    res["3年_只描述"] = {"diff平均": float(T3y["diff"].mean()) if len(T3y) else None, "評估日數": int(len(T3y))}

    # ── 假訊號 ──
    rng = np.random.default_rng(SEED)
    pools = {}
    for d in evals:
        names = A[d]["可買可判"]
        v = np.array([cumr(t, d, H1) for t in names if cumr(t, d, H1) is not None], float)
        pools[d] = (v, len(A[d]["可買∩T2"]))
    fake = np.empty(NFAKE)
    for b in range(NFAKE):
        ds = []
        for d in evals:
            v, k = pools[d]
            if k == 0 or k >= len(v):
                continue
            idx = rng.permutation(len(v))
            ds.append(v[idx[:k]].mean() - v[idx[k:]].mean())
        fake[b] = np.mean(ds) if ds else np.nan
    if avg is not None and np.isfinite(fake).all():
        pval = float((1 + int((fake >= avg).sum())) / (1 + NFAKE))
    else:
        pval = None
    fk = fake[np.isfinite(fake)]
    res["假訊號"] = {"次數": NFAKE, "種子": SEED, "平均": float(fk.mean()) if len(fk) else None,
                  "P2.5": float(np.percentile(fk, 2.5)) if len(fk) else None,
                  "P50": float(np.percentile(fk, 50)) if len(fk) else None,
                  "P97.5": float(np.percentile(fk, 97.5)) if len(fk) else None,
                  "真值": avg, "p值_單尾": pval}

    # ── 描述各組 ──
    desc = {}
    desc_by_eval = []
    for H, tag in ((H1, "1y"), (H3, "3y")):
        desc[tag] = {}
        for g in DESC_GROUPS:
            means, exs, allv, nd = [], [], [], []
            for d in evals:
                s, v = stats(A[d][g], d, H)
                nd.append(len(A[d][g]))
                if s["平均"] is not None:
                    means.append(s["平均"])
                    allv += v
                    if s["超額平均"] is not None:
                        exs.append(s["超額平均"])
                desc_by_eval.append({"eval": d, "期": tag, "組": g, "檔數": len(A[d][g]), "有報酬筆數": s["n"],
                                     "平均": s["平均"], "中位": s["中位"], "超額平均": s["超額平均"]})
            desc[tag][g] = {"有值評估日": len(means), "評估日平均之平均": float(np.mean(means)) if means else None,
                            "全部筆中位": float(np.median(allv)) if allv else None,
                            "對大盤超額平均": float(np.mean(exs)) if exs else None,
                            "每評估日檔數_中位": float(np.median(nd)), "每評估日檔數_最小": int(min(nd))}
    res["描述"] = desc

    # ── 對齊台股描述格（60 日；不判）──
    rows = []
    for d in evals:
        a, _ = stats(A[d]["可買∩轉強T1∪T2"], d, H60)
        b, _ = stats(A[d]["可買∩沒轉強T3∪T4∪T0"], d, H60)
        rows.append({"eval": d, "n_轉強": a["n"], "n_沒轉強": b["n"], "轉強": a["平均"], "沒轉強": b["平均"],
                     "diff": (a["平均"] - b["平均"]) if (a["平均"] is not None and b["平均"] is not None) else None,
                     "轉強_超額": a["超額平均"], "沒轉強_超額": b["超額平均"]})
    T60 = pd.DataFrame(rows)
    dv = T60.dropna(subset=["diff"])
    res["對齊台股_60日_描述"] = {"diff平均": float(dv["diff"].mean()) if len(dv) else None, "有diff評估日": int(len(dv)),
                           "轉強_平均": FV.mean_or_none(T60["轉強"].tolist()),
                           "沒轉強_平均": FV.mean_or_none(T60["沒轉強"].tolist()),
                           "轉強_超額": FV.mean_or_none(T60["轉強_超額"].tolist()),
                           "沒轉強_超額": FV.mean_or_none(T60["沒轉強_超額"].tolist())}

    # ── 組合：可買∩T2 袖 對 ^SP500TR ──
    cal = FQ.calendar()
    i0 = cal.get_loc(pd.Timestamp(evals[0])) + 1
    i1 = cal.get_loc(pd.Timestamp(evals[-1])) + H1
    days = cal[i0:i1 + 1]
    pos = {d: k for k, d in enumerate(days)}
    acc = np.zeros(len(days))
    cnt = np.zeros(len(days))
    empty = 0
    for d in evals:
        w = hd.window(d, H1)
        paths = [hd.daily(t, d, H1, count=False) for t in A[d]["可買∩T2"]]
        paths = [p for p in paths if p is not None]
        if not paths:
            empty += 1
            sr = np.zeros(H1)
        else:
            navs = np.cumprod(1.0 + np.vstack(paths), axis=1).mean(axis=0)
            prev = np.r_[1.0, navs[:-1]]
            sr = np.where(prev > 0, navs / prev - 1.0, 0.0)
        for k, day in enumerate(w):
            acc[pos[day]] += sr[k]
            cnt[pos[day]] += 1
    port = np.where(cnt > 0, acc / np.maximum(cnt, 1), 0.0)
    bm = ix.daily(i0 - 1, len(days))
    a1, m1, r1 = FV.nav_stats(port)
    a2, m2, r2 = FV.nav_stats(bm)
    c1 = bool(a1 is not None and a2 is not None and a1 > a2)
    c2 = None if (r1 is None or r2 is None) else bool(r1 >= r2)
    res["組合_可買∩T2袖"] = {"袖": {"年化": a1, "最大回落": m1, "年化÷|回落|": r1},
                        "大盤SP500TR": {"年化": a2, "最大回落": m2, "年化÷|回落|": r2},
                        "格1_年化勝": c1, "格2_比值不輸": c2 if c2 is not None else "不可比（回落為 0）",
                        "判定": (("只描述（主格依構造還沒測，裁定 seq484 §一；不判通過與否）") if mode == "formal" else
                               ("通過" if (c1 and c2) else ("另列（只過年化）" if c1 else "不通過"))),
                        "空袖數": empty, "區間": [str(days[0].date()), str(days[-1].date())],
                        "交易日數": int(len(days))}
    return res, per, pd.DataFrame(desc_by_eval), T60


def final_verdict(*_ignored, **__ignored):
    """正式跑判語：事先固定，與任何數字無關（裁定 seq484 §一）。"""
    return FIXED_VERDICT


def leaves(o, pre=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from leaves(v, pre + "/" + str(k))
    elif isinstance(o, (list, tuple)) and o and not isinstance(o[0], (str,)):
        for i, v in enumerate(o):
            yield from leaves(v, pre + "[%d]" % i)
    else:
        yield pre, o


def is_empty(v):
    return v is None or (isinstance(v, float) and not np.isfinite(v))


# ═════════════ seq377 等價檢查（邏輯）═════════════
EQUIV = {
    "互斥與依序": "T1、T2 都要求 收盤＞MA60；T3、T4 都要求 收盤≤MA60；T3 要 收盤＞MA250、T4 要 收盤≤MA250 ⇒ 四態依構造兩兩互斥，"
              "「依序判」不改變任何一筆的歸類（換順序結果相同）。",
    "T2": "T2 ⇔ 收盤＞MA60 ∧ ¬(MA60 上揚 ∧ 收盤＞MA250) ⇔ 收盤＞MA60 ∧ ¬T1；不等價於任何單一條件"
          "（含兩個成因：MA60 下彎、或 收盤≤MA250；兩者各有多少筆見頻率表 T2a/T2b/T2c）。",
    "主格對照組": "其他四態 ⇔ 可判 ∧ ¬T2 ⇔ 收盤≤MA60 ∨ T1；不等價於「收盤≤MA60」（差 T1 那一塊）。",
    "主格整體": "主格 ≠「收盤＞MA60 vs 收盤≤MA60」：T1（多頭）被放在對照組；故主格不是單一均線條件的換句話說。",
    "對齊台股轉強": "T1∪T2 ⇔ 收盤＞MA60（恆等，與台股版同一發現）⇒ 對齊台股的描述格其實就是「可買裡 收盤＞季線 vs ≤季線」；只描述、不判，不影響主格。",
    "與台股定義比對": "台股版 T1～T4、T0、20 日斜率、270 根暖身與本件文字相同 ⇒ 不需 seq2 對齊。",
}


def run_freq(S, G, reg):
    T = freq(S, G)
    os.makedirs(OUTD, exist_ok=True)
    T.to_csv(os.path.join(OUTD, "freq_by_eval.csv"), index=False, encoding="utf-8-sig")
    ins_main = insufficient(T, ["主格_可買∩T2", "主格_可買∩其他四態"])
    ins_alt = insufficient(T, ["主格_可買∩T2", "另讀_可買∩T0"])
    yrs = sorted({int(d[:4]) for d, ok_ in zip(T["eval"], T["兩組都非空"]) if ok_})
    tot = Counter()
    for c in T.columns:
        if c != "eval" and T[c].dtype != bool and np.issubdtype(T[c].dtype, np.number):
            tot[c] = int(T[c].sum())
    S_ = {
        "登錄": {"檔名": REG_NAME, **reg},
        "發號": "裁定 seq482 §二（主格 N_單筆 +1；組合 N_組合 +1）",
        "資料commit": FQ.data_commit(),
        "評估日數": len(T), "評估日": list(T["eval"]),
        "各組每評估日檔數": {c: armstats(T, c) for c in
                      ["母體", "可買", "可買_不可判", "主格_可買∩T2", "主格_可買∩其他四態", "另讀_可買∩T0",
                       "可買∩T1多頭", "可買∩T3長多回檔", "可買∩T4空頭", "可買∩T0其他", "偏貴∩T2",
                       "對齊台股_可買∩轉強T1∪T2", "對齊台股_可買∩沒轉強"]},
        "樣本不足_主格(★T5)": ins_main,
        "樣本不足_另讀只T0": ins_alt,
        "分群": {"兩組都非空的評估日": int(T["兩組都非空"].sum()), "進場年群": yrs, "群數": len(yrs),
               "前段群數": sum(1 for y in yrs if FRONT[0] <= y <= FRONT[1]),
               "後段群數": sum(1 for y in yrs if BACK[0] <= y <= BACK[1]),
               "登錄群數下限": "無（★T8 不設群數閘）"},
        "合計_(評估日,檔)": dict(tot),
        "等價檢查_seq377": EQUIV,
        "等價檢查_實測": {
            "可買∩T2合計": tot["主格_可買∩T2"],
            "T2a_MA60下彎且收盤>MA250": tot["T2a_MA60下彎且收盤>MA250"],
            "T2b_MA60上揚且收盤≤MA250": tot["T2b_MA60上揚且收盤≤MA250"],
            "T2c_MA60下彎且收盤≤MA250": tot["T2c_MA60下彎且收盤≤MA250"],
            "可買∩T1(對照組裡收盤>MA60的)": tot["可買∩T1多頭"],
            "可買∩轉強T1∪T2_合計": tot["對齊台股_可買∩轉強T1∪T2"],
            "轉強≡收盤>MA60_反例數": int(((S["group"] == "可買") & (S["state"] != NA) &
                                     (S["state"].isin([1, 2]) != (S["px"] > S["ma60"]))).sum()),
        },
        "另一讀法筆數": {"★T1_價格改src檔還原價_可買態不同": tot["可買_價格另讀態不同(★T1另讀)"],
                    "★T1_母體態不同": tot["母體_價格另讀態不同(★T1另讀)"],
                    "★T2_可買可判窗內缺列": tot["可買可判_窗內缺列(★T2另讀)"]},
    }
    return T, S_


def main(argv=None):
    m = gate(sys.argv[1:] if argv is None else argv)
    if isinstance(m, tuple):
        print(m[1])
        sys.exit(2)
    reg = verify_registration()
    G = load_sets()
    S = build_states(G)
    os.makedirs(PRIVD, exist_ok=True)
    S.to_csv(os.path.join(PRIVD, "state_by_eval_ticker.csv"), index=False)
    T, SUM = run_freq(S, G, reg)
    res, per, D, T60 = compute(m, S, G)
    if m == "dry":
        res["說明"] = "乾跑：持有報酬與大盤全寫 0（Holder dry）；只驗程式路徑與欄位齊全。⛔ 不含任何報酬。"
        lv = list(leaves(res))
        st = pd.DataFrame([{"欄": k, "空白": is_empty(v)} for k, v in lv])
        # 乾跑造成的空白（回落為 0 ⇒ 比值 None）另標
        st["乾跑佔位造成"] = st["欄"].str.contains("年化÷\\|回落\\|") & st["空白"]
        st.to_csv(os.path.join(OUTD, "desc_dryrun_status.csv"), index=False, encoding="utf-8-sig")
        dcols = D.drop(columns=["平均", "中位", "超額平均"])
        dcols.to_csv(os.path.join(OUTD, "desc_by_eval_counts.csv"), index=False, encoding="utf-8-sig")
        SUM["描述欄乾跑"] = {"欄數": int(len(st)), "空白": int(st["空白"].sum()),
                        "空白_乾跑佔位造成": int(st["乾跑佔位造成"].sum()),
                        "空白_其他": list(st.loc[st["空白"] & ~st["乾跑佔位造成"], "欄"]),
                        "逐評估日描述列": int(len(D)),
                        "逐評估日描述列_報酬欄空白(有檔卻無值)": int(((D["檔數"] > 0) & D["平均"].isna()).sum()),
                        "逐評估日描述列_0檔": int((D["檔數"] == 0).sum()),
                        "3年窗走不完的評估日": int(sum(1 for d in sorted(G) if FV.Holder(True).window(d, H3) is None))}
        FQ.jdump(res, os.path.join(OUTD, "dry_run.json"))
        FQ.jdump(SUM, os.path.join(OUTD, "freq_summary.json"))
        print(json.dumps(SUM, ensure_ascii=False, indent=1, default=str)[:12000])
    else:
        os.makedirs(FORMALD, exist_ok=True)
        res["登錄"] = reg
        res["判語"] = FIXED_VERDICT
        res["結果句"] = RESULT_SENTENCES
        res["沿革"] = ("裁定 seq484 §一：〈四十九〉適用 ⇒ 依構造還沒測；准正式跑（閘門 seq482 → seq484），"
                     "判語事先固定，報酬（主格、組合、對大盤、描述各組）只當描述")
        FQ.jdump(res, os.path.join(FORMALD, "result.json"))
        per["1y"].to_csv(os.path.join(FORMALD, "main_by_eval_1y.csv"), index=False, encoding="utf-8-sig")
        D.to_csv(os.path.join(FORMALD, "desc_by_eval.csv"), index=False, encoding="utf-8-sig")
        T60.to_csv(os.path.join(FORMALD, "tw_aligned_60d_by_eval.csv"), index=False, encoding="utf-8-sig")
        print("正式跑完成 →", FORMALD)


if __name__ == "__main__":
    main()
