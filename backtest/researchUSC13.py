# -*- coding: utf-8 -*-
"""USREG-C13 VIX 分層進場 seq1（美股策略線 2234，去 pw1 行 sha256 前 16 碼 d72fc2fdccf2c4c0，3535B；裁定 seq380 交辦、seq381 發號；美股 N_組合 ＋1）
＋ 台股描述臂 e（台股策略線 1019-2236 §一；裁定 seq381 核「回測可直接依兩信並跑」；⛔ 不另計 N、只描述方向）。回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSC13 pre    # 資料檢查＋觸發段（⛔ 不算任何報酬）
    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSC13 body   # 全部起點一次跑完
    獨立查核：cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSC13_check

⛔⛔ 私有資料：us-stock-data 是私有 repo ⇒ resultsUSC13/ 只放彙總（中位、比例、CI、判語、件數）與觸發日期清單（日期＋VIX 收盤，FRED 公開）；
   每段觸發後的「最深回落 %、回本交易日數」是事件彙總、不是逐日價；逐起點明細只放 ~/us_work/usc13/（repo 外）。

═══ C13 補讀法（⭐ 寫死於 2026-10-20 00:05（台北），寫死前 ⛔ 沒看任何 C13 報酬數字）═══
 C13-1 美股資料 ＝ USREG-A1／C7 同一份（researchUSA1_data.load_market，~/usdata/60d2f99，截到 2026-09-30）：
       ^SP500TR 收 ＝ adjclose、開 ＝ ^GSPC 開 × 同日 TR÷GSPC（A1 D2）；現金 ＝ DTB3（t 日報酬 ＝ DTB3_{t−1}÷100÷252，缺值用前值；A1 D4）。
       VIX ＝ 同快照 data/macro/fred_VIXCLS.csv（FRED VIXCLS 收盤；"." 缺值列丟掉），只用 ≤ 2026-09-30。
 C13-2 觸發（每個起點各自）：第 k 層 ＝ 起點【當日收盤】起（VIX 日期 d ≥ 起點日期），第一個 VIXCLS_d ≥ 門檻 k（30／50／75）的日子；
       美股 ⇒ 日曆上日期 ＞ d 的第一個交易日開盤買（^SP500TR 開盤無效 ⇒ 往後第一個有效開盤）。同一天跨兩層 ⇒ 兩層同日都買。
       每層一生只用一次（主臂）；⛔ 不設賣點，買了抱到量測日。
 C13-3 金額：起點 1.0（＝100 萬）分三份 20／30／50，各份等待時一起賺 DTB3 ⇒ 第 k 層買進額 ＝ 當時現金 × w_k ÷（尚未用掉各層 w 之和）；
       成本 0.05%（買進額）。量測期末 ＝ 持股 × 期末收盤 ＋ 現金（含息）。
 C13-4 起點：每月第一個交易日（^SP500TR 開盤有效），10 年窗 1990-02～2016-09（登錄）；期末 ＝ 起點月 ＋119 個月的最後一個交易日收盤；
       5 年窗（描述 d）1990-02～2021-09，期末 ＝ 起點月 ＋59 個月最後一個交易日。期末月須完整（下一個月在日曆內）。
 C13-5 對照：L ＝ 起點開盤全買抱到期末；D ＝ C7 定義（起點月起連 12 個月、每月第一個交易日開盤買「剩餘現金 ÷ 剩餘期數」，第 12 筆買完；
       未投入賺 DTB3）；成本同 0.05%。
 C13-6 判定（主比較 V 對 L；另比 V 對 D）：x ＝ 期末財富差（萬，100 萬本金）；中位 x 與「V 贏的起點比例」；
       CI ＝ 月分群（登錄字面：每個起點自成一群）Bonferroni：兩個比較 ⇒ z ＝ Φ⁻¹(1 − 0.05/2/2) ≈ 2.241；
       中位 ＞ 0 且 CI 下緣 ＞ 50% ⇒「方向一致（贏）」；中位 ＜ 0 且 CI 上緣 ＜ 50% ⇒「方向一致（輸）」；其餘「分不出」。⛔ 不給合格（登錄）。
       描述：年分群 CI（相鄰起點 10 年窗高度重疊、月分群偏窄）同式另列，⛔ 不改判語。
 C13-7 觸發「段」（必報次數與日期用）：某層 段起 ＝ 不在段內時 VIXCLS 收盤 ≥ 門檻的那天；段止 ＝ 之後第一個 VIX 收盤 ≤ 20 的日子
       （「20 以下」借登錄 §三 c 的重新武裝線）；資料末仍未 ≤ 20 ⇒ 照寫。另報：收盤 ≥ 門檻的日數、向上穿越（前日 ＜ 門檻 ≤ 當日）次數。
       美股段 ＝ 1990-01-02～2026-09-30；台股段 ＝ 2003-06-30 起。
 C13-8 每段觸發後「再往下最深、多久回本」：段起日 d ⇒ 照 C13-2 時差在 d 之後第一個交易日開盤買（成本不計）；
       ⚠ 修訂（2026-10-20 00:20 台北，只動這個必報描述項、判定格與起點表未動）：原寫「最深 ＝ 買進日起到第一次跌破後的回本日前」，
          實作後發現買進後先漲、數年後才首次跌破的段（例 1997-10、2007-08）會量到與該段無關的日後小回落、回本日數失真 ⇒ 改為：
       最深 ＝ min(0, 買進日起到「段止日（VIX ≤ 20）之後第一個交易日」為止的最低收盤 ÷ 買價 − 1)（收盤判，不看盤中）；
       回本 ＝ 該最低點之後第一個收盤 ≥ 買價的交易日，距買進日的交易日數（段內收盤從沒低於買價 ⇒ 0）；資料末沒回本 ⇒「未回本」。
 C13-9 閒置比例 ＝ 每個起點窗內每日「現金 ÷ 總值」的平均，再對起點平均（另報中位）；第 k 層「從沒觸發」＝ 窗內沒有第 k 層的買進成交。
 C13-10 描述臂（⛔ 不判）：a 比例 33⅓／33⅓／33⅓、10／30／60；b 盤中高 ⇒ 資料庫沒有 CBOE VIX 日高（us-stock-data 只有 FRED VIXCLS 收盤）⇒ 照寫「無資料」；
       c 重新武裝 ＝ 有層已用掉、且現金 ＞ 0（還有層沒用）時，某日 VIX 收盤 ≤ 20 ⇒ 已用掉的層全部補回（之後各層再等下一次收盤 ≥ 門檻；
          金額照 C13-3 用當時現金依權重分；三層都用完 ⇒ 現金 0、不補）；d 5 年窗（C13-4）。
 C13-11 台股描述臂 e（台股 2236 §一）：觸發與資金同主臂；VIX 日期 d 的收盤 ⇒ 台北日期 ＞ d（＝ d＋1 含之後）的第一個 0050 有 K 棒日【開盤】買；
       起點同樣只數 VIX 日期 d ≥ 起點日期（起點當晚美股收盤起）⇒ 買進日一定在起點之後，⛔ 不用台股 d 當日收盤。
       0050 ＝ researchRev.market_series 的接續還原序列（早年 data/early 3edc0e2206 ＋ 主快照 edc6f，含息、2025-06-18 一拆四已在 adj 還原）；
       台股交易日 ＝ 0050 有效 K 棒日（2025-06-11～17 分割停牌無 K 棒 ⇒ 順延）。
       ⚠ 資料只從 2004-02-11 起（資料庫早年日線首日）⇒ 規格的 2003-06-30～2004-02-10 沒有 0050 日線；起點從第一個完整月 2004-03 起（2003-07～2004-02 共 8 個起點無資料，照寫）。
       10 年窗起點 ～2016-09、5 年窗 ～2021-09（資料末 2026-09-24 ⇒ 期末月最晚 2026-08）；未投入 ＝ 台幣現金 0 報酬；買進手續費 0.1425%、不賣；
       對照 ① L 起點開盤全買 ② D（C7 定義，每月第一個 0050 交易日開盤，0 利率 ⇒ 每筆 1/12）；同 C13-6 統計，判語只寫方向（⛔ 不判、不計 N）。
 C13-12 條件出場（seq308）：不適用——登錄買了不賣、量測日固定；照寫。
"""
from __future__ import annotations

import argparse
import json
import os
import time
from collections import Counter
from statistics import NormalDist

import numpy as np
import pandas as pd

from backtest import researchUSA1_data as A

READ_TS = "2026-10-20 00:05（台北）"
REG = {"件": "USREG-C13 VIX 分層進場 seq1", "sha": "d72fc2fdccf2c4c0", "位元組": 3535, "裁定": "seq380 交辦、seq381 發號（美股 N_組合 ＋1）",
       "台股描述臂": "台股策略線 1019-2236 §一（pw1 seq=510 sha=12d9dc9f01adb67d）；裁定 seq381 核"}
OUT = os.path.expanduser("~/tw-p17/backtest/resultsUSC13")
WORK = os.path.expanduser("~/us_work/usc13")
THR = (30.0, 50.0, 75.0)
W_MAIN = (0.20, 0.30, 0.50)
W_DESC = {"a_33/33/33": (1 / 3, 1 / 3, 1 / 3), "a_10/30/60": (0.10, 0.30, 0.60)}
REARM = 20.0
COST_US = 0.0005
COST_TW = 0.001425
US_S0, US_S1, US_S1_5 = "1990-02", "2016-09", "2021-09"
TW_S0, TW_S1, TW_S1_5 = "2003-07", "2016-09", "2021-09"
TW_SEG0 = "2003-06-30"
ZB = NormalDist().inv_cdf(1 - 0.05 / 2 / 2)


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


def jdump(obj, name):
    os.makedirs(OUT, exist_ok=True)

    def cv(o):
        if isinstance(o, dict):
            return {str(k): cv(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [cv(v) for v in o]
        if isinstance(o, (np.floating, float)):
            return None if not np.isfinite(o) else float(o)
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, np.bool_):
            return bool(o)
        return o
    json.dump(cv(obj), open(os.path.join(OUT, name), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def clus_mean(x, grp, z):
    """群集穩健平均 CI（researchUSC.clus_mean 同式）：se ＝ sqrt(Σ_g (Σ_i∈g (x_i − x̄))²) ÷ n。"""
    x = np.asarray(x, float); grp = np.asarray(grp)
    n = len(x); mu = float(x.mean())
    s = pd.Series(x - mu).groupby(grp).sum().to_numpy()
    se = float(np.sqrt((s ** 2).sum()) / n)
    return {"平均": mu, "lo": mu - z * se, "hi": mu + z * se, "群數": int(len(s))}


# ═════════════ 資料 ═════════════
def load_vix():
    v = A.fred("VIXCLS")
    v = v[v.index <= A.CAL_END]
    raw_n = int(len(v)); nan_n = int(v.isna().sum())
    v = v.dropna()
    return v.index.to_numpy(str), v.to_numpy(float), {"列數": raw_n, "缺值列（丟）": nan_n, "首日": str(v.index[0]), "末日": str(v.index[-1])}


def load_us():
    A.assert_pinned()
    M = A.load_market()
    cal = M["cal"]
    o = M["O"]["TR"].astype(float); c = M["C"]["TR"].astype(float)
    ok = np.isfinite(o) & np.isfinite(c) & (o > 0) & (c > 0)
    cf = pd.Series(np.where(np.isfinite(c) & (c > 0), c, np.nan)).ffill().to_numpy()
    CI = np.cumprod(1.0 + M["cash_g"])
    return {"dates": np.asarray(cal, str), "o": o, "cf": cf, "ok": ok, "CI": CI, "M": M, "cost": COST_US}


def load_tw():
    from backtest import researchRev as RV        # ⭐ 匯入時 researchH2 把 D.DATA 指到快照 edc6f
    main, spl, info = RV.market_series()
    v = spl["valid"]
    dates = np.asarray(spl["dates"], str)[v]
    o = np.asarray(spl["o"], float)[v]; c = np.asarray(spl["c"], float)[v]
    ok = np.isfinite(o) & (o > 0) & np.isfinite(c) & (c > 0)
    info = dict(info); info["有效 K 棒開盤缺值"] = int((~ok).sum()); info["序列首日"] = str(dates[0]); info["序列末日"] = str(dates[-1])
    return {"dates": dates, "o": o, "cf": c, "ok": ok, "CI": np.ones(len(dates)), "cost": COST_TW, "info": info}


def next_valid(ok):
    n = len(ok); nv = np.full(n + 1, n, int)
    for i in range(n - 1, -1, -1):
        nv[i] = i if ok[i] else nv[i + 1]
    return nv


def buy_index(vd, mk_dates, nv):
    """VIX 日期 d ⇒ 市場日期 ＞ d 的第一個有效開盤位置（n ⇒ 無）。"""
    b = np.searchsorted(mk_dates, vd, side="right")
    return nv[b]


def month_tables(dates):
    ym = np.array([int(d[:4]) * 12 + int(d[5:7]) - 1 for d in dates])
    first, last = {}, {}
    for i, k in enumerate(ym):
        first.setdefault(int(k), i); last[int(k)] = i
    return ym, first, last


def ymk(s):
    return int(s[:4]) * 12 + int(s[5:7]) - 1


def kym(k):
    return f"{k // 12:04d}-{k % 12 + 1:02d}"


# ═════════════ 觸發段 ═════════════
def segments(vd, vv, thr, lo=None):
    rows = []; cur = None
    for j in range(len(vd)):
        if lo is not None and vd[j] < lo:
            continue
        if cur is None:
            if vv[j] >= thr:
                cur = {"門檻": thr, "段起日": vd[j], "段起VIX收盤": vv[j], "段內最高VIX收盤": vv[j], "最高日": vd[j], "段止日（VIX≤20）": None, "_j": j}
        else:
            if vv[j] > cur["段內最高VIX收盤"]:
                cur["段內最高VIX收盤"] = vv[j]; cur["最高日"] = vd[j]
            if vv[j] <= REARM:
                cur["段止日（VIX≤20）"] = vd[j]; cur["_je"] = j; rows.append(cur); cur = None
    if cur is not None:
        cur["段止日（VIX≤20）"] = "資料末仍 ＞ 20"; cur["_je"] = len(vd) - 1; rows.append(cur)
    return rows


def raw_counts(vd, vv, thr, lo=None):
    m = np.ones(len(vd), bool) if lo is None else (vd >= lo)
    x = vv[m]
    return {"收盤≥門檻日數": int((x >= thr).sum()), "向上穿越次數": int(((x[1:] >= thr) & (x[:-1] < thr)).sum() + int(x[0] >= thr))}


# ═════════════ 計畫與財富 ═════════════
def tier_buys(vd, vv, bidx, s_date, e, w, rearm=False):
    """→ buys [(位置, 用當時現金的比例)]、log [(層, VIX 日, 位置)]；只收位置 ≤ e 的買進。"""
    j0 = int(np.searchsorted(vd, s_date, side="left"))
    armed = [True, True, True]; buys = []; lg = []
    for j in range(j0, len(vd)):
        b = int(bidx[j])
        if b > e:
            break
        if rearm and vv[j] <= REARM and any(armed) and not all(armed):
            armed = [True, True, True]
        for k in range(3):
            if armed[k] and vv[j] >= THR[k]:
                rem = sum(w[i] for i in range(3) if armed[i])
                buys.append((b, w[k] / rem)); armed[k] = False; lg.append((k, vd[j], b))
        if not any(armed):
            break
    return buys, lg


def dca(first, mk, nv, n):
    out = []
    for i in range(12):
        if (mk + i) not in first:
            return None
        t = int(nv[first[mk + i]])
        if t >= n:
            return None
        out.append((t, 1.0 / (12 - i)))
    return out


def wealth(o, cf, CI, s, buys, e, cost):
    """C7 wealth 同式（researchUSC_c7.wealth），成本為參數。→ 期末財富、閒置現金比例平均。"""
    sh = 0.0; cash_at = 1.0; tc = s - 1
    bi = 0; csum = 0.0; m = e - s + 1
    for t in range(s, e + 1):
        while bi < len(buys) and buys[bi][0] == t:
            c_open = cash_at * CI[t - 1] / CI[tc]
            amt = c_open * buys[bi][1]
            sh += amt * (1 - cost) / o[t]
            cash_at = c_open - amt; tc = t - 1
            bi += 1
        cash_t = cash_at * CI[t] / CI[tc]
        V = sh * cf[t] + cash_t
        csum += cash_t / V
    assert bi == len(buys), "買進日不在窗內"
    return float(V), csum / m


def run_market(X, vd, vv, s0, s1, h, label, desc=True):
    dates, o, cf, ok, CI, cost = X["dates"], X["o"], X["cf"], X["ok"], X["CI"], X["cost"]
    n = len(dates); nv = next_valid(ok)
    bidx = buy_index(vd, dates, nv)
    ym, first, last = month_tables(dates)
    data_m0 = int(ym[0])
    rows = []; used = Counter()
    for mk in range(ymk(s0), ymk(s1) + 1):
        if mk not in first or mk == data_m0 and dates[0][8:10] != "01" and label.startswith("台股"):
            continue
        s = first[mk]
        if s < 1 or not ok[s]:
            continue
        e = last.get(mk + h - 1)
        if e is None or (mk + h) not in first:
            continue
        rec = {"起點": kym(mk), "年": mk // 12, "s": s, "e": e}
        pl = {"L": [(s, 1.0)], "D": dca(first, mk, nv, n)}
        if pl["D"] is None or pl["D"][-1][0] > e:
            continue
        b, lg = tier_buys(vd, vv, bidx, dates[s], e, W_MAIN)
        pl["V"] = b
        if desc:
            for nm, w in W_DESC.items():
                pl[nm] = tier_buys(vd, vv, bidx, dates[s], e, w)[0]
            pl["c_重新武裝"] = tier_buys(vd, vv, bidx, dates[s], e, W_MAIN, rearm=True)[0]
        for nm, bb in pl.items():
            rec[f"W_{nm}"], rec[f"閒置_{nm}"] = wealth(o, cf, CI, s, bb, e, cost)
        got = {k: None for k in range(3)}
        for k, d, bpos in lg:
            got[k] = (d, bpos)
            used[(k, d)] += 1
        for k in range(3):
            rec[f"層{k + 1}觸發"] = got[k] is not None
            rec[f"層{k + 1}等待交易日"] = (got[k][1] - s) if got[k] is not None else np.nan
        rec["期末仍有現金"] = not all(got[k] is not None for k in range(3))
        rows.append(rec)
    return pd.DataFrame(rows), used, bidx


def judge(df, a, b, desc_only=False):
    x = (df[f"W_{a}"] - df[f"W_{b}"]).to_numpy() * 100.0           # 萬（100 萬本金）
    r = (df[f"W_{a}"] / df[f"W_{b}"] - 1).to_numpy()
    win = (x > 0).astype(float)
    cm = clus_mean(win, df["起點"].to_numpy(), ZB)
    cy = clus_mean(win, df["年"].to_numpy(), ZB)
    med = float(np.median(x))

    def lab(c):
        return "方向一致（贏）" if (med > 0 and c["lo"] > 0.5) else ("方向一致（輸）" if (med < 0 and c["hi"] < 0.5) else "分不出")
    out = {"比較": f"{a} 對 {b}", "起點數": int(len(x)), "起點年數": int(df["年"].nunique()), "中位差（萬）": med, "平均差（萬）": float(x.mean()),
           "p10差（萬）": float(np.percentile(x, 10)), "p90差（萬）": float(np.percentile(x, 90)), "最差（萬）": float(x.min()), "最好（萬）": float(x.max()),
           "中位比值差": float(np.median(r)), f"{a}贏的起點比例": cm["平均"], "CI_月分群_Bonferroni": [cm["lo"], cm["hi"]],
           "判語（月分群）" if not desc_only else "方向（月分群，描述）": lab(cm),
           "描述_CI_年分群": [cy["lo"], cy["hi"]], "描述_方向（年分群）": lab(cy), "年群數": cy["群數"],
           f"{a}期末中位（萬）": float(np.median(df[f"W_{a}"]) * 100), f"{b}期末中位（萬）": float(np.median(df[f"W_{b}"]) * 100)}
    return out


def tier_stats(df):
    o = {}
    for k in range(3):
        o[f"層{k + 1}（≥{THR[k]:.0f}）從沒觸發的起點比例"] = float(1 - df[f"層{k + 1}觸發"].mean())
        w_ = df[f"層{k + 1}等待交易日"].dropna()
        o[f"層{k + 1}有觸發者等待交易日中位"] = float(w_.median()) if len(w_) else None
    o["V閒置比例_起點平均"] = float(df["閒置_V"].mean()); o["V閒置比例_起點中位"] = float(df["閒置_V"].median())
    o["D閒置比例_起點平均"] = float(df["閒置_D"].mean()); o["L閒置比例_起點平均"] = float(df["閒置_L"].mean())
    o["期末仍有現金的起點比例"] = float(df["期末仍有現金"].mean())
    for nm in list(W_DESC) + ["c_重新武裝"]:
        if f"閒置_{nm}" in df:
            o[f"{nm}閒置比例_起點平均"] = float(df[f"閒置_{nm}"].mean())
    return o


def dd_recover(o, cf, b, we):
    """C13-8（修訂）：最深 ＝ min(0, cf[b..we] 最低 ÷ 買價 − 1)；回本 ＝ 最低點之後第一個收盤 ≥ 買價、距 b 的交易日數。"""
    p = o[b]; we = min(we, len(cf) - 1)
    seg = cf[b:we + 1]; tr = int(np.argmin(seg))
    if seg[tr] >= p:
        return 0.0, 0, None, 0
    rec = np.flatnonzero(cf[b + tr:] >= p)
    if len(rec):
        return float(seg[tr] / p - 1), tr + int(rec[0]), True, tr
    return float(seg[tr] / p - 1), int(len(cf) - 1 - b), False, tr


def seg_table(segs, X, vd, bidx_mkt, mkt):
    rows = []
    for g in segs:
        j = g["_j"]; b = int(bidx_mkt[j]); we = int(bidx_mkt[g["_je"]])
        r = {k: v for k, v in g.items() if not k.startswith("_")}
        r["市場"] = mkt
        if b >= len(X["dates"]):
            r.update({"買進日": "無資料", "最深": None, "回本交易日": None, "回本": None})
        else:
            dd, days, okr, tr = dd_recover(X["o"], X["cf"], b, we)
            r.update({"買進日": X["dates"][b], "最深（收盤÷買價−1）": dd, "最低收盤日": X["dates"][b + tr], "到最低交易日": tr,
                      "回本交易日": days if okr is not False else None,
                      "回本": ("段內收盤從沒低於買價" if okr is None else ("是" if okr else f"未回本（至 {X['dates'][-1]}，{days} 交易日）"))})
        rows.append(r)
    return rows


# ═════════════ pre ═════════════
def pre(a):
    vd, vv, vinfo = load_vix()
    U = load_us(); T = load_tw()
    M = U["M"]; cal = U["dates"]
    early = cal < "1993-01-01"
    gs_o = A._on_cal(A.yahoo("GSPC")["open"], cal); gs_c = M["C"]["GSPC"]
    out = {"VIX": vinfo, "VIX 日期不在 ^GSPC 日曆": int(len(set(vd) - set(cal))), "^GSPC 日曆日無 VIX": int(len(set(cal) - set(vd))),
           "^SP500TR 開盤無效日數": int((~U["ok"]).sum()), "^GSPC 1990～1992 開＝收 日數": int(np.sum((gs_o == gs_c)[early])),
           "^GSPC 1990～1992 日數": int(early.sum()), "DTB3": M["audit"]["DTB3"], "0050": T["info"],
           "0050 2025-06-18 分割：原始收盤比（前後）與還原收盤比是否連續（|比−1|＜10%）": None}
    d = T["dates"]; i0 = int(np.searchsorted(d, "2025-06-18"))
    from backtest import researchRev as RV
    D = RV.D
    raw = pd.read_csv(os.path.join(D.DATA, "stocks", "0050.csv"), dtype={"date": str}, usecols=["date", "close"]).set_index("date")["close"].astype(float)
    rr = raw.get(d[i0]) / raw.get(d[i0 - 1]); ar = T["cf"][i0] / T["cf"][i0 - 1]
    out["0050 2025-06-18 分割：原始收盤比（前後）與還原收盤比是否連續（|比−1|＜10%）"] = {"前一 K 棒": d[i0 - 1], "原始比": float(rr), "還原連續": bool(abs(ar - 1) < 0.10)}
    out["觸發段"] = {}
    for thr in THR:
        out["觸發段"][f"美股≥{thr:.0f}"] = {"段數": len(segments(vd, vv, thr)), **raw_counts(vd, vv, thr),
                                          "段起日": [g["段起日"] for g in segments(vd, vv, thr)]}
        out["觸發段"][f"台股期≥{thr:.0f}"] = {"段數": len(segments(vd, vv, thr, TW_SEG0)), **raw_counts(vd, vv, thr, TW_SEG0),
                                           "段起日": [g["段起日"] for g in segments(vd, vv, thr, TW_SEG0)]}
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
    return out


# ═════════════ body ═════════════
def body(a):
    T0 = time.time()
    os.makedirs(WORK, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    vd, vv, vinfo = load_vix()
    U = load_us(); T = load_tw()
    R = {}
    R["US10"], usedU, bU = run_market(U, vd, vv, US_S0, US_S1, 120, "美股")
    R["US5"], _, _ = run_market(U, vd, vv, US_S0, US_S1_5, 60, "美股", desc=False)
    R["TW10"], usedT, bT = run_market(T, vd, vv, TW_S0, TW_S1, 120, "台股")
    R["TW5"], _, _ = run_market(T, vd, vv, TW_S0, TW_S1_5, 60, "台股", desc=False)
    for k, df in R.items():
        df.to_pickle(os.path.join(WORK, f"c13_starts_{k}.pkl"))
    res = {}
    # 主臂
    d = R["US10"]
    res["主臂_美股10年"] = {"起點範圍": [d["起點"].min(), d["起點"].max()], "對L（主比較，判定）": judge(d, "V", "L"), "對D（另比）": judge(d, "V", "D"),
                         "L對D（參考）": {k_: v_ for k_, v_ in judge(d, "L", "D").items() if k_ in ("中位差（萬）", "L贏的起點比例", "判語（月分群）")},
                         "必報": tier_stats(d)}
    res["描述臂"] = {}
    for nm in list(W_DESC) + ["c_重新武裝"]:
        res["描述臂"][nm] = {"對L": {k_: v_ for k_, v_ in judge(d, nm, "L", True).items()}, "對D": {k_: v_ for k_, v_ in judge(d, nm, "D", True).items()}}
    res["描述臂"]["b_盤中高"] = "無資料：資料庫（us-stock-data）只有 FRED VIXCLS 收盤，沒有 CBOE VIX 日高"
    d5 = R["US5"]
    res["描述臂"]["d_5年窗"] = {"起點範圍": [d5["起點"].min(), d5["起點"].max()], "對L": judge(d5, "V", "L", True), "對D": judge(d5, "V", "D", True), "必報": tier_stats(d5)}
    # 台股描述臂 e
    res["台股描述臂e"] = {}
    for key, nm in (("TW10", "10年"), ("TW5", "5年")):
        dt = R[key]
        res["台股描述臂e"][nm] = {"起點範圍": [dt["起點"].min(), dt["起點"].max()], "對①L（起點全買0050）": judge(dt, "V", "L", True),
                                 "對②D（12個月定額）": judge(dt, "V", "D", True), "必報": tier_stats(dt)}
    res["台股描述臂e"]["資料限制"] = ("0050 日線資料庫只從 2004-02-11 起 ⇒ 規格 2003-07～2004-02 的 8 個起點無資料、起點從 2004-03；"
                                  "2003-06-30～2004-02-10 期間 VIX 有無觸發見觸發段表")
    # 觸發段與每段回落
    seg_rows = []; summ = {}
    for thr in THR:
        su = segments(vd, vv, thr); st = segments(vd, vv, thr, TW_SEG0)
        seg_rows += seg_table(su, U, vd, bU, "美股（^SP500TR）")
        seg_rows += seg_table(st, T, vd, bT, "台股（0050）")
        summ[f"≥{thr:.0f}"] = {"美股段數（1990-01-02～2026-09-30）": len(su), **{f"美股_{k}": v for k, v in raw_counts(vd, vv, thr).items()},
                               "台股期段數（2003-06-30 起）": len(st), **{f"台股期_{k}": v for k, v in raw_counts(vd, vv, thr, TW_SEG0).items()}}
    S = pd.DataFrame(seg_rows)
    cols = ["市場", "門檻", "段起日", "段起VIX收盤", "段內最高VIX收盤", "最高日", "段止日（VIX≤20）", "買進日", "最深（收盤÷買價−1）", "最低收盤日", "到最低交易日", "回本交易日", "回本"]
    S = S[[c for c in cols if c in S.columns]]
    S.to_csv(os.path.join(OUT, "C13_segments.csv"), index=False, encoding="utf-8", float_format="%.4f")
    for mkt in ("美股（^SP500TR）", "台股（0050）"):
        for thr in THR:
            x = S[(S["市場"] == mkt) & (S["門檻"] == thr)]
            xx = pd.to_numeric(x["最深（收盤÷買價−1）"], errors="coerce").dropna()
            rc = pd.to_numeric(x["回本交易日"], errors="coerce").dropna()
            summ[f"≥{thr:.0f}"][f"{mkt}_每段最深_中位"] = float(xx.median()) if len(xx) else None
            summ[f"≥{thr:.0f}"][f"{mkt}_每段最深_最差"] = float(xx.min()) if len(xx) else None
            summ[f"≥{thr:.0f}"][f"{mkt}_回本交易日_中位（有回本者）"] = float(rc.median()) if len(rc) else None
            summ[f"≥{thr:.0f}"][f"{mkt}_未回本段數"] = int(x["回本"].astype(str).str.startswith("未回本").sum())
    res["觸發段摘要"] = summ
    # 起點實際用到的觸發日
    ur = []
    vmap = dict(zip(vd, vv))
    for mkt, used in (("美股10年", usedU), ("台股10年", usedT)):
        for (k, dd), cnt in sorted(used.items(), key=lambda z: (z[0][0], z[0][1])):
            ur.append({"窗": mkt, "層": k + 1, "VIX日期": dd, "VIX收盤": vmap[dd], "用到的起點數": cnt})
    pd.DataFrame(ur).to_csv(os.path.join(OUT, "C13_trigger_used.csv"), index=False, encoding="utf-8")
    # 先驗
    m = res["主臂_美股10年"]; segU = {thr: summ[f"≥{thr:.0f}"]["美股段數（1990-01-02～2026-09-30）"] for thr in THR}
    t3 = m["必報"]["層3（≥75）從沒觸發的起點比例"]
    res["先驗對錯"] = [
        {"先驗": "VIX 分層輸一開始全買（約八成五）", "結果": f"{m['對L（主比較，判定）']['判語（月分群）']}；中位 {m['對L（主比較，判定）']['中位差（萬）']:+.1f} 萬",
         "對": m["對L（主比較，判定）"]["判語（月分群）"] == "方向一致（輸）"},
        {"先驗": "VIX 分層贏定期定額（約四成）", "結果": f"{m['對D（另比）']['判語（月分群）']}；中位 {m['對D（另比）']['中位差（萬）']:+.1f} 萬",
         "對": m["對D（另比）"]["判語（月分群）"] == "方向一致（贏）"},
        {"先驗": "≥75 歷史只觸發 2 段（約八成）", "結果": f"{segU[75.0]} 段", "對": segU[75.0] == 2},
        {"先驗": "≥50 觸發 3～5 段（約七成）", "結果": f"{segU[50.0]} 段", "對": 3 <= segU[50.0] <= 5},
        {"先驗": "10 年內第三層從沒觸發的起點 ≥ 70%（約八成）", "結果": f"{t3:.0%}", "對": t3 >= 0.70}]
    jm = m["對L（主比較，判定）"]
    res["結果句"] = (f"VIX 30 買兩成、50 再買三成、75 買剩下五成（收盤判、閒錢放國庫券、買了不賣）：10 年後比一開始全買"
                  f"{'多' if jm['中位差（萬）'] > 0 else '少'}中位 {abs(jm['中位差（萬）']):.1f} 萬，贏的起點 {jm['V贏的起點比例']:.0%}"
                  f"（{jm['判語（月分群）']}；{jm['起點數']} 個起點、約 {jm['起點年數']} 年）；⚠ 1990 年以來 VIX 收盤 ≥ 50 只有 {segU[50.0]} 段、"
                  f"≥ 75 只有 {segU[75.0]} 段，樣本極少；比例 20／30／50 為本線所定，原文沒寫")
    res["卡片"] = {"N": "美股 N_組合 ＋1（主比較一格）；台股描述臂 e ⛔ 不另計 N", "判準": "樣本極少 ⇒ 只到方向，⛔ 不給合格",
                 "Bonferroni z（兩個比較）": ZB, "條件出場必報（seq308）": "不適用：登錄買了不賣、量測日固定",
                 "補讀法": f"C13-1～C13-12（researchUSC13.py docstring，{READ_TS} 寫死）", "登錄": REG}
    hol = sorted(set(vd) - set(U["dates"]))
    res["資料"] = {"美股快照": A.data_commit(), "VIX": vinfo, "0050": T["info"],
                 "VIX 在 ^GSPC 日曆外的列（多為 2022 起美股休市日，FRED 照列；照 C13-2 當一般觀測、次一交易日買）": len(hol),
                 "其中收盤 ≥ 30": [(x, float(dict(zip(vd, vv))[x])) for x in hol if dict(zip(vd, vv))[x] >= 30],
                 "修訂": "C13-8 每段最深／回本定義於 2026-10-20 00:20 修訂（見 docstring）；判定格、起點表、觸發日未動"}
    res["算於"] = now_tpe(); res["秒"] = round(time.time() - T0)
    jdump(res, "C13.json")
    print(json.dumps({k: res[k] for k in ("結果句", "先驗對錯")}, ensure_ascii=False, indent=1))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["pre", "body"])
    a = ap.parse_args()
    (pre if a.mode == "pre" else body)(a)


if __name__ == "__main__":
    main()
