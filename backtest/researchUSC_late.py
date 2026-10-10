# -*- coding: utf-8 -*-
"""USREG-C 批後四件（等資料那四件）：C11 股債金 → C12 月線＋失業率 → C9 三倍 ETF → C2 內部人買進。回測線，台北 2026-10-10。

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSC_late c11|c12|c9|etf [--procs 3]
    C2：-m backtest.researchUSC_late_c2 ...｜獨立查核：-m backtest.researchUSC_late_check｜網頁：-m backtest.researchUSC_late_page

登錄（信箱全文；sha ＝ 整檔 sha256 前 16 碼，美股線已核）：
  C11 ＝ USREG-B11 股債金搭配 seq1（sha c16dc89cba394b41）｜C12 ＝ USREG-B12 趨勢加失業率擇時 seq1（sha cefe09aadd278f46）
  C9  ＝ USREG-B9 三倍 ETF seq1（sha 0a2da38ec570bcd3）｜C2 ＝ USREG-B2 內部人買進 seq1（sha f369f2c02f8e095b）
裁定：seq321 §三（發號、N：C2 6、C9 4、C12 2、C11 1；C2 合併母體當判定；C9 早年合成照 seq309；QQQ 1999-03 前不可判定）、§五（相對門檻、等效獨立檔數）；
      seq308（條件出場主臂、窗尾仍持有與持有天數必報、固定天數只描述）。
資料：資料庫線 1009-1604（ETF 含息日線）、1009-1659（費用率、ALFRED 首次公布值、Form 4）。
⛔⛔ 私有資料：us-stock-data 是私有庫 ⇒ 本檔只讀快照 ~/usdata/b33bde6（git archive b33bde68145e，唯讀）；
   resultsUSC/late/ 只放彙總（年化、回落、比值、次數、比例、判語、sha）；逐日價格、權益曲線一律不寫進 repo（中間檔放 ~/us_work/c_late/）。

══ 執行者補讀法（⭐ 台北 2026-10-10 23:16 寫死於看任何 C11／C12／C9 數字之前；登錄沒寫清楚處）══
 共通
 L1 資料 ＝ us-stock-data b33bde68（含 1604、1659 交件）；日曆 ＝ yahoo_GSPC 日期，截到 2026-09-30（⛔ 不用 10-01 之後）。
    還原價 ＝ 原始 × adjclose ÷ close（USREG-A1 D2 同法；含息、含分割）。^SP500TR 收盤 ＝ adjclose，開盤 ＝ ^GSPC 開盤 × (^SP500TR 收 ÷ ^GSPC 收)（A1 D2）。
 L2 現金 ＝ DTB3（%，前值補；t 日現金報酬 ＝ DTB3_{t−1}÷100÷252）；成本 ＝ 換手金額 × 0.05%；引擎 ＝ researchUSA1_data.engine（A1 D6，t 開盤成交、
    換手 ½Σ|目標−現有|、窗首建倉付一次成本、一檔沒開盤 ⇒ 整筆延後），⛔ 一行未改、只 import。
 L3 年化、回落、比值、判準 ＝ A1 D7（使用者判準：年化 ＞ ^SP500TR 同窗（嚴格）且 比值 ≥ 基準比值 ⇒ 合格；只前者 ⇒ 另列；否則不合格）。
    「100 萬最低剩」＝ 100 × 段內權益路徑（含 1.0 起點）最小值；「回本要幾年」＝ 最大回落那一段由高點到再創高點的交易日數 ÷ 252（段內沒回 ⇒ 未回本）。
 L4 條件出場（seq308）：C12、C9 的主規則本身就是條件出場（訊號轉弱才出、⛔ 無最長天數）；必報 每段「持有段」天數分佈（平均、中位、p10、p90、最長）與
    段尾是否仍持有；固定 {20, 60, 120, 240} 日 ＝ researchUSA1_data.fixed_hold_path（只描述）。C11 是常態持有（無進出場）⇒ 照實寫「全期持有」。
 L5 等效獨立檔數（seq321 §五，組合層加報）：C11 ＝ (Σ w_i σ_i)² ÷ (wᵀΣw)（日報酬、判定窗全段、目標權重）；C9、C12 單一資產 ⇒ 1。
 C11
 L6 窗 ＝ SSO 上市日（2006-06-21）在日曆的位置 ＋ 200（第 201 個交易日）～ 2026-09-30，一段判（登錄只寫一個窗）。
 L7 判定格 50% SSO＋30% IEF＋20% GLD，每年第一個交易日再平衡（窗首當天不算再平衡日，A1 reb_mask）。描述網格「債＝無」⇒ 其餘放國庫券。
    偏離 ±5 點才調 ＝ 每天收盤算實際權重（含現金），任一 |實際 − 目標| ＞ 5 點 ⇒ 次一交易日開盤調回（成本同）。
 L8 HFEA 對照 ＝ 55% UPRO＋45% TMF、每季第一個交易日再平衡，從 UPRO 上市日 2009-06-25 起（登錄寫 2009-05，UPRO 6 月才有）到 2026-09-30；
    同窗並列判定格與 ^SP500TR。60/40 ＝ 60% SPY＋40% IEF 每年再平衡。
 L9 危機窗：2008 ＝ 2007-10-01～2009-03-31｜2020 ＝ 2020-02-03～2020-03-31｜2022 ＝ 2022-01-03～2022-12-30；100 萬放在窗首前一交易日收盤，
    報 窗內最低剩、窗末剩、回本 ＝ 從窗首起到權益第一次回到 100 萬的交易日數（往後找到 2026-09-30；沒回 ⇒ 未回本）。
 L10 相關係數 ＝ 每個曆年日報酬（還原收盤）的 Pearson：SPY–IEF、SPY–TLT、SPY–GLD、IEF–GLD。
 L11 平均總股票曝險 ＝ 逐日收盤「股（SSO／QLD）實際市值 ÷ 總值 × 2」的平均（自寫引擎 engine_w，閘：每年再平衡時與 A1 engine 權益逐日差 ≤ 1e-10）。
     同曝險對照 ＝ SSO 權重 ＝ 平均曝險 ÷ 2、其餘國庫券、每年再平衡（＝ 單純股＋現金、同曝險）；另列 SPY min(曝險,1)＋國庫券（描述）。
 C12
 L12 月底 ＝ 日曆每月最後一個交易日。M ＝ 月底 ^SP500TR 收盤 ＞ 最近 10 個月底收盤平均（含當月，researchLowFreq M10 同式）。
 L13 E：只用 release_date ≤ 月底日 的首次公布值（alfred_UNRATE_first_release first_value；2025-10 空白 ＝ 未發布 ⇒ 跳過，不補）；依 ref_month 排序，
     最新一個 ＜ 最近 12 個（含最新）的平均 ⇒ E 成立（嚴格小於；相等的月份數另報）。
 L14 決策在月底收盤、下個月第一個交易日開盤換；1 倍 ＝ ^SP500TR 本身（開盤照 L1）；2 倍 ＝ 段一 合成 SSO（A1 seq3 公式：2r − (DTB3+0.25%)/252 − 0.89%/252，
     合成開盤 A1 D5）、段二三 真實 SSO。
 L15 段：段一 ＝ M 可算後第一個月初（1990-11-01）～ 2006-12-29｜段二 2007-01-03～2021-12-31｜段三 2022-01-03～2026-09-30；各段 1.0 重算、段首照前一月底決策建倉。
 L16 Sahm 版（描述）：a_k ＝ 最近 3 個已公布值平均；觸發 ＝ a_k − min(前 12 個 a) ≥ 0.5；狀態機：持有中「M 不成立且觸發」⇒ 出；出場中 M 成立 ⇒ 進；
     從可算的第一個月底以「持有」起跑、連續跑。修正後版（描述）＝ 同一組已公布月份，值改用 vintages 最新值（realtime_end 空白）。
 L17 逐筆出場：主規則與單用月線各自「持有→出場」的月底；出場日 ＝ 次一交易日開盤、回場日 ＝ 回場決策次一交易日開盤；期間漲跌 ＝ ^SP500TR 回場日開 ÷ 出場日開 − 1
     （＞ 0 ＝ 被洗）；窗尾仍在外 ⇒ 標「窗尾仍出場」用 2026-09-30 收盤。
 L18 四次大跌（高低點日寫死）：2000-03-24～2002-10-09（2001 衰退那次）、2007-10-09～2009-03-09、2020-02-19～2020-03-23、2022-01-03～2022-10-12；
     躲了幾成 ＝ 1 − 策略同期報酬 ÷ 指數同期報酬（前一交易日收盤到窗末收盤；2 倍對一直抱 2 倍）。2024 Sahm 假警報 ＝ 2024-06～2025-03 月底逐月狀態。
 C9
 L19 合成 3 倍（seq309）：r_L ＝ 3 r_idx − 2 (DTB3_{t−1}/100 ＋ 0.25%)/252 − f/252；開盤 L_o ＝ L_c,t−1 × (1 ＋ 3 (o_idx ÷ c_idx,t−1 − 1))；
     f ＝ etf_expense_ratios.csv SEC 497K 那一列的【淨】費用率（UPRO 0.88%、TQQQ 0.78%；毛費用率 0.88／0.94 另跑描述；利差 0、0.5% 描述）。
     UPRO 版指數 ＝ ^SP500TR；TQQQ 版 ＝ QQQ 含息價（1999-03-10 起，之前不可判定）。同規則 2 倍對照：早年合成 2 倍（f ＝ SEC 淨 SSO 0.84%、QLD 0.89%）、之後真實 SSO／QLD。
 L20 M ＝ 標的指數（^SP500TR 或 QQQ 還原收盤）＞ 自己 200 日均線 ⇒ 次一交易日開盤抱 3 倍，否則國庫券（W[t] ＝ 訊號[t−1]）。
     100、150 日與 ±3% 緩衝帶（站上 1.03 倍才進、跌破 0.97 倍才出，狀態機從均線可算日連續跑）只描述。V ＝ 每月底 w ＝ min(1, 30% ÷ σ̂20)，
     σ̂20 ＝ 合成 3 倍最近 20 日日報酬標準差 × √252，次月第一個交易日開盤調（描述）。
 L21 段：早年合成 ＝ 該件 200 日線可算後第一個月初 ～ 上市前最後一個月底（UPRO 1990-11-01～2009-05-29｜TQQQ 2000-01-03～2010-01-29），H 與 M 同起點；
     真實 ＝ 上市日 ～ 2021-12-31；2022-01-03 ～ 2026-09-30。判定 4 格各對 ^SP500TR 同窗；三段同標籤才下該標籤，否則「看段」。
 L22 三次大跌：2000-01-03～2002-12-31（合成）、2007-10-01～2009-03-31（UPRO 合成、TQQQ 合成）、2022-01-03～2022-12-30（真實）；
     100 萬放在窗首前一交易日收盤 ⇒ 最低剩、窗末剩、回本年數（從窗首起，往後找到 2026-09-30：早年用「合成接到 2026-09-30」的連續路徑）。
 L23 M 必報：每年換手 ＝ 段內持有狀態改變次數 ÷ 年數；錯過的反彈 ＝ 每次回場訊號日指數收盤 ÷ 出場期間指數最低收盤 − 1（平均、中位）；
     假突破 ＝ 持有段 ＜ 20 個交易日、且出場訊號日指數收盤 ≤ 進場訊號日指數收盤 的次數。
 L24 對帳：上市日～2026-09-30 合成 vs 真實（年化差、日報酬相關、日差絕對值平均）。
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import time
from itertools import product

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchUSA1_data as A          # noqa: E402  engine／perf／bench／label／reb_mask／fixed_hold_path（只 import、不改）

DATA_COMMIT = "b33bde68145eea96c6c4882f71b2a5352ba5c36e"
ROOT = os.environ.get("US_DATA_ROOT_CLATE", os.path.expanduser("~/usdata/b33bde6"))
OUT = os.path.expanduser("~/tw-p17/backtest/resultsUSC/late")
WORK = os.path.expanduser("~/us_work/c_late")
CAL_END = "2026-09-30"
ANN = 252
COST = 0.0005
SPREAD = 0.0025
READ_TS = "2026-10-10 23:16（台北）"
REG = {"C11": "USREG-B11 股債金搭配 seq1 sha c16dc89cba394b41", "C12": "USREG-B12 趨勢加失業率擇時 seq1 sha cefe09aadd278f46",
       "C9": "USREG-B9 三倍 ETF seq1 sha 0a2da38ec570bcd3", "C2": "USREG-B2 內部人買進 seq1 sha f369f2c02f8e095b",
       "裁定": "seq321 §三§五、seq308、seq309"}
NBOOK = {"C2": 6, "C9": 4, "C12": 2, "C11": 1}
ETFS = ("SPY", "QQQ", "SSO", "QLD", "UPRO", "TQQQ", "IEF", "TLT", "SHY", "GLD", "TMF")
SYN = "合成、非實際 ETF"
LOGF = None


def log(m):
    print(m, flush=True)
    if LOGF:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(m + "\n")


def p_(*a):
    return os.path.join(ROOT, "data", *a)


def data_commit():
    return io.open(os.path.join(ROOT, ".commit"), encoding="utf-8").read().strip()


def assert_pinned():
    c = data_commit()
    if c != DATA_COMMIT:
        raise RuntimeError(f"資料 commit {c} ≠ 寫死的 {DATA_COMMIT}")
    return c


def sha256f(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def jdump(obj, name):
    os.makedirs(OUT, exist_ok=True)
    json.dump(obj, open(os.path.join(OUT, name), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=_jd)


def _jd(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def rnd(x, k=6):
    if isinstance(x, dict):
        return {a: rnd(b, k) for a, b in x.items()}
    if isinstance(x, (list, tuple)):
        return [rnd(b, k) for b in x]
    if isinstance(x, (float, np.floating)):
        return None if not np.isfinite(x) else round(float(x), k)
    return x


# ═════════════ 讀檔（L1、L2）═════════════
def yahoo(name):
    d = pd.read_csv(p_("macro", f"yahoo_{name}.csv"), dtype={"date": str})
    d = d.drop_duplicates("date").set_index("date").sort_index()
    for c in ("open", "high", "low", "close", "volume", "adjclose"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    return d


def fred(name):
    d = pd.read_csv(p_("macro", f"fred_{name}.csv"), dtype=str, keep_default_na=False)
    v = pd.to_numeric(d["value"].replace({"": None, ".": None}), errors="coerce")
    return pd.Series(v.to_numpy(float), index=d["date"].to_numpy(str))


def _on(s, cal):
    return np.array(s.reindex(cal).to_numpy(float), dtype=float, copy=True)


def load_market():
    assert_pinned()
    d = pd.read_csv(p_("macro", "yahoo_GSPC.csv"), usecols=["date"], dtype=str)["date"]
    cal = np.array(sorted(x for x in set(d) if x <= CAL_END))
    n = len(cal)
    M = {"cal": cal, "pos": {x: i for i, x in enumerate(cal)}, "O": {}, "C": {}, "audit": {}}
    for k in ETFS:
        y = yahoo(k)
        kf = y["adjclose"] / y["close"]
        o = _on(y["open"] * kf, cal); c = _on(y["close"] * kf, cal)
        bad = ~(np.isfinite(o) & np.isfinite(c) & (o > 0) & (c > 0))
        o[bad] = np.nan; c[bad] = np.nan
        M["O"][k], M["C"][k] = o, c
        f = int(np.flatnonzero(np.isfinite(c))[0])
        M["audit"][k] = {"首日": cal[f], "首日後日曆內缺日": int((~np.isfinite(c[f:])).sum()),
                         "非日曆日列（≤2026-09-30）": int(len([x for x in y.index if x <= CAL_END and x not in M["pos"]]))}
    tr = yahoo("SP500TR"); gs = yahoo("GSPC")
    c_tr = _on(tr["adjclose"], cal); c_gs = _on(gs["close"], cal)
    M["C"]["TR"] = c_tr
    M["O"]["TR"] = _on(gs["open"], cal) * (c_tr / c_gs)
    M["audit"]["TR"] = {"首日": cal[0], "缺日": int((~np.isfinite(c_tr)).sum()), "GSPC缺日": int((~np.isfinite(c_gs)).sum())}
    r = fred("DTB3"); r = r[r.index <= CAL_END]
    lv = r.dropna()
    dt = pd.Series(lv.to_numpy(), index=lv.index).reindex(sorted(set(lv.index) | set(cal))).ffill().reindex(cal).to_numpy(float)
    M["dtb3"] = dt
    g = np.zeros(n); g[1:] = dt[:-1] / 100.0 / ANN
    M["cash_g"] = g
    M["audit"]["DTB3"] = {"日曆日無當日值（用前值）": int(sum(1 for x in cal if x not in set(lv.index))), "末筆": str(lv.index[-1])}
    er = pd.read_csv(p_("macro", "etf_expense_ratios.csv"), dtype=str)
    sec = er[er["source_type"].str.contains("SEC")].set_index("ticker")
    M["ER"] = {t: {"淨": float(sec.loc[t, "net_er"]) / 100, "毛": float(sec.loc[t, "gross_er"]) / 100, "asof": sec.loc[t, "asof"]} for t in sec.index}
    return M


def synth(M, idx, L, fee, s=SPREAD):
    """L 倍每日重設合成（L19／A1 D5 同式）⇒ (O, C)。"""
    o, c = M["O"][idx], M["C"][idx]
    n = len(c)
    Lc = np.full(n, np.nan); Lo = np.full(n, np.nan)
    st = int(np.flatnonzero(np.isfinite(c))[0])
    Lc[st] = 1.0
    dprev = np.r_[np.nan, M["dtb3"][:-1]]
    for t in range(st + 1, n):
        if not (np.isfinite(c[t]) and np.isfinite(c[t - 1])):
            Lc[t] = Lc[t - 1]
            continue
        r = c[t] / c[t - 1] - 1.0
        Lc[t] = Lc[t - 1] * (1.0 + L * r - (L - 1) * (dprev[t] / 100.0 + s) / ANN - fee / ANN)
        Lo[t] = Lc[t - 1] * (1.0 + L * (o[t] / c[t - 1] - 1.0)) if np.isfinite(o[t]) else np.nan
    return Lo, Lc


def run(M, assets, W, i0, i1, R=None, cost=COST):
    return A.run(M, tuple(assets), np.asarray(W, float), i0, i1, R=R, cost=cost)


def seg_stats(eq, cal, i0, bench_c):
    c, m = A.perf(eq)
    p = np.r_[1.0, eq]; pk = np.maximum.accumulate(p); dd = (p - pk) / pk
    it = int(np.argmin(dd)); ip = int(np.argmax(p[:it + 1]))
    back = np.flatnonzero(p[it:] >= p[ip])
    rec = (it + int(back[0]) - ip) / ANN if len(back) else None
    i1 = i0 + len(eq) - 1
    cb, mb = A.bench(bench_c, i0, i1)
    return {"年化": c, "回落": m, "比值": A.ratio(c, m), "100萬最低剩（萬）": float(p.min() * 100), "期末（萬）": float(eq[-1] * 100),
            "回本年數": rec if rec is not None else "段內未回本", "高點日": cal[i0 + ip - 1] if ip > 0 else "段首", "谷底日": cal[i0 + it - 1] if it > 0 else "段首",
            "基準年化": cb, "基準回落": mb, "基準比值": A.ratio(cb, mb), "標籤": A.label(c, m, cb, mb), "起": cal[i0], "迄": cal[i1]}


def crash(eq, cal, i0, a, b):
    """L9／L22：100 萬在 a 前一交易日收盤 ⇒ [a, b] 最低剩、窗末剩、回本（往後找到 eq 末）。eq 從 i0 起。"""
    ia, ib = a - i0, b - i0
    base = eq[ia - 1] if ia > 0 else 1.0
    seg = eq[ia:ib + 1] / base
    it = int(np.argmin(seg))
    after = eq[ia + it:] / base
    k = np.flatnonzero(after >= 1.0 - 1e-12)
    rec = (it + int(k[0])) / ANN if len(k) else None
    return {"窗內最低剩（萬）": float(min(1.0, seg.min()) * 100), "窗末剩（萬）": float(seg[-1] * 100), "谷底日": cal[a + it],
            "回本年數（從窗首）": rec if rec is not None else "未回本（至 2026-09-30）"}


def spells(on):
    """on（bool）⇒ [(起, 迄)] 連續 True 段（含端點，相對位置）。"""
    out = []; t = 0; n = len(on)
    while t < n:
        if on[t]:
            s = t
            while t < n and on[t]:
                t += 1
            out.append((s, t - 1))
        else:
            t += 1
    return out


def hold_dist(on, n_total=None):
    sp = spells(on)
    L = np.array([b - a + 1 for a, b in sp], float)
    if len(L) == 0:
        return {"持有段數": 0, "段尾仍持有": False}
    return {"持有段數": int(len(L)), "平均": float(L.mean()), "中位": float(np.median(L)), "p10": float(np.percentile(L, 10)),
            "p90": float(np.percentile(L, 90)), "最長": int(L.max()), "段尾仍持有": bool(on[-1]), "持有日占比": float(np.mean(on))}


def month_end_mask(cal):
    ym = np.array([s[:7] for s in cal])
    me = np.zeros(len(cal), bool); me[:-1] = ym[:-1] != ym[1:]; me[-1] = True
    return me


def month_start_after(cal, i):
    for t in range(i + 1, len(cal)):
        if cal[t][:7] != cal[t - 1][:7]:
            return t
    return -1


def ma(x, L):
    """有效值上的 L 日簡單平均，對回日曆（無值日 NaN）。"""
    ok = np.isfinite(x); out = np.full(len(x), np.nan)
    v = pd.Series(x[ok]).rolling(L, min_periods=L).mean().to_numpy()
    out[ok] = v
    return out


def engine_w(o, c, W, R, cash_g, cost=COST, band=None):
    """自寫引擎（L7、L11）：A1 engine 同一套成交規則，另回逐日實際權重；band ＝ 偏離門檻（小數）⇒ 收盤偏離超過 ⇒ 次一交易日開盤調回。
    閘：band=None 時權益與 A1 engine 逐日差 ≤ 1e-10（run_c11 會驗）。"""
    n, k = W.shape
    u = np.zeros(k); cash = 1.0; eq = np.empty(n); aw = np.zeros((n, k)); nreb = 0
    tgt_held = None; pending = True; flag = False
    for t in range(n):
        if t > 0 and ((R is not None and R[t]) or flag or not np.array_equal(W[t], tgt_held)):
            pending = True
        if pending:
            need = (u > 0) | (W[t] > 0)
            if np.all(np.isfinite(o[t][need])):
                px = o[t]
                hold = np.where(u > 0, u * px, 0.0); V = hold.sum() + cash
                tgt = W[t] * V; tc = (1.0 - W[t].sum()) * V
                tr = 0.5 * (np.abs(tgt - hold).sum() + abs(tc - cash))
                V2 = V - tr * cost
                u = np.where(W[t] > 0, W[t] * V2 / px, 0.0); cash = (1.0 - W[t].sum()) * V2
                tgt_held = W[t].copy(); pending = False; flag = False
                if t > 0:
                    nreb += 1
        if t > 0:
            cash *= 1.0 + cash_g[t]
        val = np.where(u > 0, u * c[t], 0.0)
        eq[t] = val.sum() + cash
        aw[t] = val / eq[t]
        if band is not None:
            dev = np.abs(aw[t] - W[t]).max()
            dc = abs(cash / eq[t] - (1.0 - W[t].sum()))
            flag = bool(max(dev, dc) > band)
    return eq, aw, nreb


def oc_seg(M, assets, i0, i1):
    O = np.stack([M["O"][a][i0:i1 + 1] for a in assets], 1)
    C = np.stack([pd.Series(M["C"][a]).ffill().to_numpy()[i0:i1 + 1] for a in assets], 1)
    return O, C


# ═════════════════════════════ C11 股債金 ═════════════════════════════
C11_CRISES = {"2008": ("2007-10-01", "2009-03-31"), "2020": ("2020-02-03", "2020-03-31"), "2022": ("2022-01-03", "2022-12-30")}


def c11(M):
    t0 = time.time(); cal = M["cal"]; pos = M["pos"]
    i0 = pos["2006-06-21"] + 200; i1 = pos[CAL_END]; n = i1 - i0 + 1
    log(f"[C11] 窗 {cal[i0]}～{cal[i1]}（{n} 日）")
    trc = M["C"]["TR"]
    B = {"年化": A.bench(trc, i0, i1)[0], "回落": A.bench(trc, i0, i1)[1]}
    B["比值"] = A.ratio(B["年化"], B["回落"])
    RY = A.reb_mask(cal, i0, i1, "Y"); RQ = A.reb_mask(cal, i0, i1, "Q")

    def cell(stock, sp, bond, gold, reb, a0=i0, a1=i1):
        assets = [stock]; w = [sp / 100]
        if bond != "無" and 100 - sp - gold > 0:
            assets.append(bond); w.append((100 - sp - gold) / 100)
        if gold > 0:
            assets.append("GLD"); w.append(gold / 100)
        nn = a1 - a0 + 1
        W = np.tile(np.array(w), (nn, 1))
        O, C = oc_seg(M, assets, a0, a1)
        if reb == "band":
            eq, aw, nreb = engine_w(O, C, W, None, M["cash_g"][a0:a1 + 1], band=0.05)
        else:
            R = A.reb_mask(cal, a0, a1, reb)
            eq, aw, nreb = engine_w(O, C, W, R, M["cash_g"][a0:a1 + 1])
        return eq, aw, assets, nreb

    # 判定格（A1 engine）＋ 閘（自寫引擎同值）
    asJ = ("SSO", "IEF", "GLD"); WJ = np.tile([0.5, 0.3, 0.2], (n, 1))
    rJ = run(M, asJ, WJ, i0, i1, R=RY)
    eqJ = rJ["eq"]
    eq2, awJ, _, _ = cell("SSO", 50, "IEF", 20, "Y")
    gate = float(np.max(np.abs(eq2 - eqJ)))
    assert gate <= 1e-10, gate
    sJ = seg_stats(eqJ, cal, i0, trc)
    expo = float(np.mean(awJ[:, 0] * 2))
    log(f"[C11] 判定格 {sJ['年化']:.4f}／{sJ['回落']:.4f} 標籤 {sJ['標籤']}｜基準 {B['年化']:.4f}／{B['回落']:.4f}｜閘 {gate:.1e}｜平均曝險 {expo:.3f}")
    # 網格（描述）
    rows = []
    for stock, sp, bond, gold, reb in product(("SSO", "QLD"), (40, 50, 60, 70), ("IEF", "TLT", "SHY", "無"), (0, 10, 20), ("Y", "Q", "band")):
        eq, aw, assets, nreb = cell(stock, sp, bond, gold, reb)
        s = seg_stats(eq, cal, i0, trc)
        row = {"股": stock, "股%": sp, "債": bond, "債%": (100 - sp - gold) if bond != "無" else 0, "金%": gold, "現金%": (100 - sp - gold) if bond == "無" else 0,
               "再平衡": {"Y": "每年", "Q": "每季", "band": "偏離±5點"}[reb], "年化": s["年化"], "回落": s["回落"], "比值": s["比值"],
               "標籤（描述）": s["標籤"], "100萬最低剩（萬）": s["100萬最低剩（萬）"], "平均總股票曝險": float(np.mean(aw[:, 0] * 2)), "調整次數": nreb}
        for k, (a, b) in C11_CRISES.items():
            cr = crash(eq, cal, i0, pos[a], pos[b])
            row[f"{k}最低剩（萬）"] = cr["窗內最低剩（萬）"]; row[f"{k}窗末（萬）"] = cr["窗末剩（萬）"]; row[f"{k}回本年數"] = cr["回本年數（從窗首）"]
        rows.append(row)
    grid = pd.DataFrame(rows)
    # 對照
    comp = {}

    def add(name, assets, w, reb, a0=i0, a1=i1):
        nn = a1 - a0 + 1; W = np.tile(np.array(w, float), (nn, 1))
        R = None if reb is None else A.reb_mask(cal, a0, a1, reb)
        r = run(M, assets, W, a0, a1, R=R)
        s = seg_stats(r["eq"], cal, a0, trc)
        s["危機"] = {k: crash(r["eq"], cal, a0, pos[a], pos[b]) for k, (a, b) in C11_CRISES.items() if pos[a] >= a0}
        comp[name] = s
        return r["eq"]
    s0 = dict(sJ); s0["危機"] = {k: crash(eqJ, cal, i0, pos[a], pos[b]) for k, (a, b) in C11_CRISES.items()}
    comp["判定格 50% SSO＋30% IEF＋20% GLD（每年）"] = s0
    add("一直抱 SPY", ("SPY",), [1.0], None)
    add("一直抱 SSO", ("SSO",), [1.0], None)
    add("60% SPY＋40% IEF（每年）", ("SPY", "IEF"), [0.6, 0.4], "Y")
    add("判定格但債換 TLT（50 SSO＋30 TLT＋20 GLD）", ("SSO", "TLT", "GLD"), [0.5, 0.3, 0.2], "Y")
    add(f"同曝險對照：SSO {expo / 2:.1%}＋國庫券（每年）", ("SSO",), [expo / 2], "Y")
    add(f"同曝險對照（描述）：SPY {min(expo, 1):.1%}＋國庫券（每年）", ("SPY",), [min(expo, 1.0)], "Y")
    h0 = pos["2009-06-25"]
    add("HFEA 55% UPRO＋45% TMF（每季，2009-06-25 起）", ("UPRO", "TMF"), [0.55, 0.45], "Q", a0=h0)
    add("判定格（同 HFEA 窗，2009-06-25 起）", asJ, [0.5, 0.3, 0.2], "Y", a0=h0)
    cbh, mbh = A.bench(trc, h0, i1)
    comp["^SP500TR（同 HFEA 窗）"] = {"年化": cbh, "回落": mbh, "比值": A.ratio(cbh, mbh)}
    comp["^SP500TR（判定窗）"] = {"年化": B["年化"], "回落": B["回落"], "比值": B["比值"],
                                  "危機": {k: crash(trc[i0:i1 + 1] / trc[i0 - 1], cal, i0, pos[a], pos[b]) for k, (a, b) in C11_CRISES.items()}}
    # 黃金 vs 股票（先驗：兩次都比股票少跌）
    gold_vs = {}
    for k in ("2008", "2022"):
        a, b = C11_CRISES[k]; ia, ib = pos[a], pos[b]
        g = {}
        for x in ("GLD", "SPY", "IEF", "TLT"):
            cc = pd.Series(M["C"][x]).ffill().to_numpy()
            g[x] = crash(cc[i0:i1 + 1] / cc[i0 - 1], cal, i0, ia, ib)
        gold_vs[k] = g
    # 相關係數（L10）
    corr = []
    rr = {x: pd.Series(M["C"][x]).ffill().pct_change().to_numpy() for x in ("SPY", "IEF", "TLT", "GLD")}
    yrs = np.array([s[:4] for s in cal])
    for y in sorted(set(yrs[i0:i1 + 1])):
        m = (yrs == y); m[:i0] = False; m[i1 + 1:] = False
        d = pd.DataFrame({k: v[m] for k, v in rr.items()}).dropna()
        corr.append({"年": y, "日數": len(d), "SPY–IEF": d["SPY"].corr(d["IEF"]), "SPY–TLT": d["SPY"].corr(d["TLT"]),
                     "SPY–GLD": d["SPY"].corr(d["GLD"]), "IEF–GLD": d["IEF"].corr(d["GLD"])})
    corr = pd.DataFrame(corr)
    # 等效獨立部位數（L5）
    rets = np.column_stack([pd.Series(M["C"][x]).ffill().pct_change().to_numpy()[i0 + 1:i1 + 1] for x in asJ])
    Sg = np.cov(rets.T); w = np.array([0.5, 0.3, 0.2]); sd = np.sqrt(np.diag(Sg))
    neff = float((w @ sd) ** 2 / (w @ Sg @ w))
    # 先驗對照
    sameexp = comp[[k for k in comp if k.startswith("同曝險對照：")][0]]
    pri = {"判定格標籤": sJ["標籤"],
           "2022 IEF 版跌幅比 TLT 版淺": comp["判定格 50% SSO＋30% IEF＋20% GLD（每年）"]["危機"]["2022"]["窗內最低剩（萬）"] > comp["判定格但債換 TLT（50 SSO＋30 TLT＋20 GLD）"]["危機"]["2022"]["窗內最低剩（萬）"],
           "黃金 2008、2022 都比 SPY 少跌": all(gold_vs[k]["GLD"]["窗內最低剩（萬）"] > gold_vs[k]["SPY"]["窗內最低剩（萬）"] for k in gold_vs),
           "同曝險對照：搭配版比值較好": sJ["比值"] > sameexp["比值"],
           "HFEA 最大回落 ≥ 60%": comp["HFEA 55% UPRO＋45% TMF（每季，2009-06-25 起）"]["回落"] <= -0.60}
    debt2022 = {"判定格 2022 最低剩": s0["危機"]["2022"]["窗內最低剩（萬）"], "同曝險 SSO＋國庫券 2022 最低剩": sameexp["危機"]["2022"]["窗內最低剩（萬）"],
                "IEF 本身 2022 最低剩": gold_vs["2022"]["IEF"]["窗內最低剩（萬）"],
                "讀法": "判定格 2022 最低剩 ＞ 同曝險 SSO＋國庫券 ⇒ 債＋金在 2022 有擋；反之 ⇒ 幫倒忙"}
    S = {"件": "USREG-C11 股債金搭配", "登錄": REG["C11"], "N": "N_組合 ＋1（美股帳）", "窗": [cal[i0], cal[i1]], "交易日": n,
         "判定格": "50% SSO＋30% IEF＋20% GLD，每年第一個交易日再平衡", "判定": sJ, "基準": B, "標籤": sJ["標籤"],
         "平均總股票曝險": expo, "等效獨立部位數（L5）": neff, "閘_自寫引擎對 A1 engine 最大差": gate,
         "對照": comp, "黃金與股票債券_危機": gold_vs, "債在2022": debt2022, "先驗對照": pri,
         "條件出場": "常態持有、無進出場訊號（靜態配置＋每年再平衡）⇒ 全期持有；窗尾仍持有＝是；持有天數＝全窗 %d 交易日；固定天數不適用" % n,
         "網格格數": len(grid), "網格年化>基準格數": int((grid["年化"] > B["年化"]).sum()), "網格合格格數（描述）": int((grid["標籤（描述）"] == "合格").sum()),
         "秒": round(time.time() - t0)}
    grid.to_csv(os.path.join(OUT, "C11_grid.csv"), index=False, encoding="utf-8")
    corr.to_csv(os.path.join(OUT, "C11_corr_by_year.csv"), index=False, encoding="utf-8")
    jdump(rnd(S), "C11_summary.json")
    log(f"[C11] 完成 {S['秒']}s｜先驗 {pri}")
    return S


# ═════════════════════════════ C12 月線＋失業率 ═════════════════════════════
C12_SEGS = (("段一（1990-11～2006，2 倍為合成）", None, "2006-12-29"), ("段二 2007～2021", "2007-01-03", "2021-12-31"), ("段三 2022～2026-09", "2022-01-03", CAL_END))
C12_CRISES = {"2000～2002（2001 衰退）": ("2000-03-24", "2002-10-09"), "2008": ("2007-10-09", "2009-03-09"), "2020": ("2020-02-19", "2020-03-23"),
              "2022": ("2022-01-03", "2022-10-12")}
SSO_FEE_A1 = 0.0089


def unrate_tables():
    fr = pd.read_csv(p_("macro", "alfred_UNRATE_first_release.csv"), dtype=str, keep_default_na=False)
    fr["v"] = pd.to_numeric(fr["first_value"].replace("", None), errors="coerce")
    vt = pd.read_csv(p_("macro", "alfred_UNRATE_vintages.csv"), dtype=str, keep_default_na=False)
    lv = vt[vt["realtime_end"] == ""].drop_duplicates("ref_month", keep="last")
    latest = pd.Series(pd.to_numeric(lv["value"].replace("", None), errors="coerce").to_numpy(float), index=lv["ref_month"].to_numpy())
    fr["v_rev"] = fr["ref_month"].map(latest)
    return fr.sort_values("ref_month").reset_index(drop=True)


def c12_signals(M):
    """→ 月底位置陣列 me_idx 與各月底的 M、E、E_rev、Sahm、主規則、單用月線、Sahm 版 決策。"""
    cal = M["cal"]; me = month_end_mask(cal); mei = np.flatnonzero(me)
    trc = M["C"]["TR"]; mc = trc[mei]
    M10 = np.full(len(mei), np.nan)
    for j in range(9, len(mei)):
        M10[j] = np.mean(mc[j - 9:j + 1])
    Ms = mc > M10
    fr = unrate_tables()
    rel = fr[fr["v"].notna()].reset_index(drop=True)
    E = np.zeros(len(mei), bool); Er = np.zeros(len(mei), bool); Sahm = np.zeros(len(mei), bool); tie = 0
    last_ref = []; nrel = np.zeros(len(mei), int)
    rd = rel["release_date"].to_numpy(str); v = rel["v"].to_numpy(float); vr = rel["v_rev"].to_numpy(float)
    for j, t in enumerate(mei):
        d = cal[t]
        k = np.flatnonzero(rd <= d)
        if len(k) < 15:
            E[j] = False; nrel[j] = len(k); last_ref.append(""); continue
        # 依 ref_month 排序（rel 已排序；只取已公布的）
        vv = v[k]; vvr = vr[k]
        E[j] = vv[-1] < vv[-12:].mean()
        tie += int(abs(vv[-1] - vv[-12:].mean()) < 1e-9)
        Er[j] = vvr[-1] < vvr[-12:].mean()
        a = np.array([vv[i - 2:i + 1].mean() for i in range(len(vv) - 13, len(vv))])
        Sahm[j] = (a[-1] - a[:-1].min()) >= 0.5 - 1e-12
        nrel[j] = len(k); last_ref.append(rel["ref_month"].iloc[k[-1]])
    ok = np.isfinite(M10)
    main = Ms | E; mon = Ms.copy(); rev = Ms | Er
    sv = np.zeros(len(mei), bool); state = True
    for j in range(len(mei)):
        if not ok[j]:
            sv[j] = True; continue
        if state and (not Ms[j]) and Sahm[j]:
            state = False
        elif (not state) and Ms[j]:
            state = True
        sv[j] = state
    return {"mei": mei, "ok": ok, "M": Ms, "E": E, "E_rev": Er, "Sahm": Sahm, "主規則": main, "單用月線": mon, "修正後失業率": rev, "Sahm版": sv,
            "tie": tie, "last_ref": np.array(last_ref), "M10": M10}


def daily_from_monthly(cal, mei, dec):
    """月底決策 ⇒ 日序列：t 日持有 ＝ 最近一個 ＜ t 的月底決策（L14）。第一個月底之前 NaN。"""
    n = len(cal); out = np.full(n, np.nan)
    for j, t in enumerate(mei):
        a = t + 1; b = mei[j + 1] if j + 1 < len(mei) else n - 1
        if a <= b:
            out[a:b + 1] = float(dec[j])
    return out


def c12(M):
    t0 = time.time(); cal = M["cal"]; pos = M["pos"]; trc = M["C"]["TR"]
    M["O"]["SYN_SSO_A1"], M["C"]["SYN_SSO_A1"] = synth(M, "TR", 2, SSO_FEE_A1)
    G = c12_signals(M)
    mei = G["mei"]
    first_ok = int(mei[np.flatnonzero(G["ok"])[0]])
    s1 = month_start_after(cal, first_ok)
    segs = []
    for nm, a, b in C12_SEGS:
        segs.append((nm, s1 if a is None else pos[a], pos[b]))
    log(f"[C12] 段 {[(x, cal[a], cal[b]) for x, a, b in segs]}｜tie {G['tie']}")
    rules = ("主規則", "單用月線", "Sahm版", "修正後失業率")
    D = {r: daily_from_monthly(cal, mei, G[r]) for r in rules}
    out = {"段": {}, "標籤": {}}
    rows = []
    for nm, i0, i1 in segs:
        cb, mb = A.bench(trc, i0, i1)
        seg = {"基準": {"年化": cb, "回落": mb, "比值": A.ratio(cb, mb)}, "起": cal[i0], "迄": cal[i1]}
        lev2 = "SYN_SSO_A1" if nm.startswith("段一") else "SSO"
        for tgt, asset in (("1 倍", "TR"), ("2 倍", lev2)):
            for r in rules:
                on = D[r][i0:i1 + 1] > 0.5
                W = on.astype(float)[:, None]
                rr = run(M, (asset,), W, i0, i1)
                s = seg_stats(rr["eq"], cal, i0, trc)
                sw = int(np.sum(on[1:] != on[:-1]))
                s.update({"換手次數（狀態改變）": sw, "持有": hold_dist(on), "成本合計": float(rr["cst"].sum())})
                seg[f"{tgt}×{r}"] = s
                rows.append({"段": nm, "標的": tgt, "規則": r, "年化": s["年化"], "回落": s["回落"], "比值": s["比值"], "標籤": s["標籤"],
                             "換手次數": sw, "持有日占比": s["持有"].get("持有日占比"), "段尾仍持有": s["持有"].get("段尾仍持有"),
                             "100萬最低剩（萬）": s["100萬最低剩（萬）"], "基準年化": cb, "基準回落": mb})
            hh = run(M, (asset,), np.ones((i1 - i0 + 1, 1)), i0, i1)
            seg[f"{tgt}×一直抱"] = seg_stats(hh["eq"], cal, i0, trc)
            # 固定天數描述（主規則）
            on = D["主規則"][i0:i1 + 1] > 0.5
            fx = {}
            for H in (20, 60, 120, 240):
                fon, ne = A.fixed_hold_path(on, H)
                r2 = run(M, (asset,), fon.astype(float)[:, None], i0, i1)
                c_, m_ = A.perf(r2["eq"]); fx[f"{H}日"] = {"年化": c_, "回落": m_, "進場次數": ne, "標籤（描述）": A.label(c_, m_, cb, mb)}
            seg[f"{tgt}×主規則_固定天數（描述）"] = fx
        out["段"][nm] = seg
    for tgt in ("1 倍", "2 倍"):
        labs = [out["段"][nm][f"{tgt}×主規則"]["標籤"] for nm, _, _ in segs]
        out["標籤"][f"{tgt}×主規則"] = labs[0] if len(set(labs)) == 1 else "看段（" + "／".join(f"{nm[:2]}{l}" for (nm, _, _), l in zip(segs, labs)) + "）"
    # 逐筆出場（L17）：連續、從 s1 起
    def exits(dec_key):
        dec = G[dec_key]; okj = G["ok"]; lst = []
        j = 0
        js = [j for j in range(len(mei)) if okj[j] and mei[j] >= s1 - 1]
        prev = None
        for j in js:
            cur = bool(dec[j])
            if prev is True and not cur:
                ex_t = mei[j] + 1
                back = [k for k in js if k > j and dec[k] and mei[k] + 1 < len(cal)]
                if ex_t >= len(cal):
                    continue
                if back:
                    re_t = mei[back[0]] + 1
                    chg = M["O"]["TR"][re_t] / M["O"]["TR"][ex_t] - 1 if re_t < len(cal) else np.nan
                    lst.append({"出場決策月底": cal[mei[j]], "出場日": cal[ex_t], "回場日": cal[re_t] if re_t < len(cal) else "—",
                                "出場月數": int(back[0] - j), "期間指數漲跌": chg, "被洗": bool(chg > 0)})
                else:
                    chg = trc[pos[CAL_END]] / M["O"]["TR"][ex_t] - 1 if ex_t < len(cal) else np.nan
                    lst.append({"出場決策月底": cal[mei[j]], "出場日": cal[ex_t] if ex_t < len(cal) else "—", "回場日": "窗尾仍出場",
                                "出場月數": None, "期間指數漲跌": chg, "被洗": bool(chg > 0)})
            prev = cur
        return lst
    EX = {r: exits(r) for r in rules}
    exdf = pd.concat([pd.DataFrame(v).assign(規則=k) for k, v in EX.items() if len(v)], ignore_index=True)
    exdf["段"] = [next((nm for nm, a, b in segs if cal[a] <= x <= cal[b]), "—") if x != "—" else "—" for x in exdf["出場日"]]
    exsum = {}
    for r in rules:
        d = exdf[exdf["規則"] == r]
        exsum[r] = {"出場次數": int(len(d)), "被洗次數": int(d["被洗"].sum()), "逐段": {nm: {"出場": int((d["段"] == nm).sum()), "被洗": int(((d["段"] == nm) & d["被洗"]).sum())} for nm, _, _ in segs}}
    # 大跌（L18）
    cr = []
    for k, (a, b) in C12_CRISES.items():
        ia, ib = pos[a], pos[b]
        nm, s0, s1_ = next((x for x in segs if x[1] <= ia <= x[2]))
        ridx = trc[ib] / trc[ia - 1] - 1
        lev2 = "SYN_SSO_A1" if nm.startswith("段一") else "SSO"
        row = {"大跌": k, "窗": f"{a}～{b}", "所在段": nm, "^SP500TR 同期": ridx}
        for tgt, asset in (("1 倍", "TR"), ("2 倍", lev2)):
            hh = run(M, (asset,), np.ones((s1_ - s0 + 1, 1)), s0, s1_)["eq"]
            base_h = hh[ia - 1 - s0] if ia - 1 >= s0 else 1.0
            rh = hh[ib - s0] / base_h - 1
            for r in ("主規則", "單用月線", "Sahm版"):
                on = D[r][s0:s1_ + 1] > 0.5
                e = run(M, (asset,), on.astype(float)[:, None], s0, s1_)["eq"]
                base = e[ia - 1 - s0] if ia - 1 >= s0 else 1.0
                rs = e[ib - s0] / base - 1
                row[f"{tgt}×{r} 同期"] = rs
                row[f"{tgt}×{r} 躲了幾成"] = (1 - rs / rh) if rh < 0 else None
            row[f"{tgt}×一直抱 同期"] = rh
        cr.append(row)
    # 2024 Sahm 假警報（L18）
    sh = []
    for j, t in enumerate(mei):
        if "2024-06" <= cal[t][:7] <= "2025-03":
            sh.append({"月底": cal[t], "最新已公布月": G["last_ref"][j], "M（站上10月線）": bool(G["M"][j]), "E（失業率低於12月平均）": bool(G["E"][j]),
                       "Sahm觸發": bool(G["Sahm"][j]), "主規則持有": bool(G["主規則"][j]), "Sahm版持有": bool(G["Sahm版"][j])})
    # 先驗對照
    pri = {"1 倍標籤": out["標籤"]["1 倍×主規則"], "2 倍標籤": out["標籤"]["2 倍×主規則"]}
    sw_main = sum(out["段"][nm]["1 倍×主規則"]["換手次數（狀態改變）"] for nm, _, _ in segs)
    sw_mon = sum(out["段"][nm]["1 倍×單用月線"]["換手次數（狀態改變）"] for nm, _, _ in segs)
    pri["換手次數 主規則 vs 單用月線"] = [sw_main, sw_mon]
    pri["換手少一半以上"] = sw_main <= sw_mon / 2
    pri["修正後失業率高估年化（1 倍，逐段：修正後 − 首次公布）"] = {nm: out["段"][nm]["1 倍×修正後失業率"]["年化"] - out["段"][nm]["1 倍×主規則"]["年化"] for nm, _, _ in segs}
    S = {"件": "USREG-C12 月線擇時＋失業率濾網", "登錄": REG["C12"], "N": "N_組合 ＋2（美股帳）", "段": out["段"], "標籤": out["標籤"],
         "逐筆出場彙總": exsum, "四次大跌": cr, "2024Sahm假警報": sh, "先驗對照": pri, "E 相等月份數": G["tie"],
         "失業率資料": {"首次公布列": int(len(unrate_tables())), "空白（未發布）": unrate_tables().loc[lambda d: d["v"].isna(), "ref_month"].tolist()},
         "條件出場": "主規則本身＝條件出場（M、E 都不成立才出、任一成立就回；⛔ 無最長天數）；持有段天數分佈與段尾仍持有見各段「持有」",
         "秒": round(time.time() - t0)}
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "C12_cells.csv"), index=False, encoding="utf-8")
    exdf.to_csv(os.path.join(OUT, "C12_exits.csv"), index=False, encoding="utf-8")
    pd.DataFrame(cr).to_csv(os.path.join(OUT, "C12_crises.csv"), index=False, encoding="utf-8")
    pd.DataFrame(sh).to_csv(os.path.join(OUT, "C12_sahm2024.csv"), index=False, encoding="utf-8")
    jdump(rnd(S), "C12_summary.json")
    log(f"[C12] 完成 {S['秒']}s｜標籤 {out['標籤']}｜先驗 {pri}")
    return S


# ═════════════════════════════ C9 三倍 ETF ═════════════════════════════
C9_CRASH = {"2000～2002": ("2000-01-03", "2002-12-31"), "2008": ("2007-10-01", "2009-03-31"), "2022": ("2022-01-03", "2022-12-30")}


def band_state(c, m, up=1.03, dn=0.97):
    n = len(c); st = np.zeros(n, bool); s = None
    for t in range(n):
        if not (np.isfinite(c[t]) and np.isfinite(m[t])):
            st[t] = bool(s) if s is not None else False
            continue
        if s is None:
            s = bool(c[t] > m[t])
        elif s and c[t] < dn * m[t]:
            s = False
        elif (not s) and c[t] > up * m[t]:
            s = True
        st[t] = s
    return st


def c9(M):
    t0 = time.time(); cal = M["cal"]; pos = M["pos"]; trc = M["C"]["TR"]; n = len(cal)
    ER = M["ER"]
    P = {"UPRO": {"idx": "TR", "real": "UPRO", "lev2": "SSO", "one_early": "TR", "one": "SPY", "list": "2009-06-25", "early_end": "2009-05-29"},
         "TQQQ": {"idx": "QQQ", "real": "TQQQ", "lev2": "QLD", "one_early": "QQQ", "one": "QQQ", "list": "2010-02-11", "early_end": "2010-01-29"}}
    for k, p in P.items():
        M["O"][f"SYN3_{k}"], M["C"][f"SYN3_{k}"] = synth(M, p["idx"], 3, ER[k]["淨"])
        M["O"][f"SYN3G_{k}"], M["C"][f"SYN3G_{k}"] = synth(M, p["idx"], 3, ER[k]["毛"])
        for s in (0.0, 0.005):
            M["O"][f"SYN3_{k}_s{s}"], M["C"][f"SYN3_{k}_s{s}"] = synth(M, p["idx"], 3, ER[k]["淨"], s)
        M["O"][f"SYN2_{k}"], M["C"][f"SYN2_{k}"] = synth(M, p["idx"], 2, ER[p["lev2"]]["淨"])
    S = {"件": "USREG-C9 三倍 ETF 長抱 vs 200 日線", "登錄": REG["C9"], "N": "N_組合 ＋4（美股帳）",
         "費用率（SEC 497K 淨／毛）": {k: ER[k] for k in ("UPRO", "TQQQ", "SSO", "QLD")}, "格": {}, "標籤": {}, "對帳": {}, "大跌": {}, "描述": {}}
    rows = []
    for k, p in P.items():
        ic = M["C"][p["idx"]]
        sig = {L: ic > ma(ic, L) for L in (100, 150, 200)}
        for L in sig:
            sig[L] = sig[L] & np.isfinite(ma(ic, L))
        sig["band3"] = band_state(ic, ma(ic, 200))
        ma_first = int(np.flatnonzero(np.isfinite(ma(ic, 200)))[0])
        E0 = month_start_after(cal, ma_first)
        segs = [("早年合成", E0, pos[p["early_end"]], f"SYN3_{k}", f"SYN2_{k}", p["one_early"]),
                ("真實（上市～2021）", pos[p["list"]], pos["2021-12-31"], p["real"], p["lev2"], p["one"]),
                ("2022～2026-09", pos["2022-01-03"], pos[CAL_END], p["real"], p["lev2"], p["one"])]
        for sgn, i0, i1, a3, a2, a1 in segs:
            nn = i1 - i0 + 1
            cb, mb = A.bench(trc, i0, i1)
            onM = np.zeros(nn, bool); onM[1:] = sig[200][i0:i1][:]  # W[t] ＝ 訊號[t−1]
            onM[0] = bool(sig[200][i0 - 1])
            arms = {"H": np.ones(nn, bool), "M": onM}
            for arm, on in arms.items():
                r = run(M, (a3,), on.astype(float)[:, None], i0, i1)
                s = seg_stats(r["eq"], cal, i0, trc)
                s["持有"] = hold_dist(on); s["換手次數"] = int(np.sum(on[1:] != on[:-1])); s["每年換手"] = s["換手次數"] / (nn / ANN)
                if arm == "M":
                    spl = spells(~on)
                    miss = []
                    for a, b in spl:
                        if b + 1 < nn:                       # 回場：on[b+1] 為 True ⇒ 訊號日 ＝ i0+b
                            lo = np.nanmin(ic[i0 + a - 1:i0 + b + 1])
                            miss.append(ic[i0 + b] / lo - 1)
                    fb = 0
                    for a, b in spells(on):
                        if b + 1 < nn and (b - a + 1) < 20 and ic[i0 + b] <= ic[i0 + a - 1]:
                            fb += 1
                    s["錯過的反彈_平均"] = float(np.mean(miss)) if miss else None
                    s["錯過的反彈_中位"] = float(np.median(miss)) if miss else None
                    s["假突破次數"] = fb
                    fx = {}
                    for H in (20, 60, 120, 240):
                        fon, ne = A.fixed_hold_path(on, H)
                        r2 = run(M, (a3,), fon.astype(float)[:, None], i0, i1)
                        c_, m_ = A.perf(r2["eq"]); fx[f"{H}日"] = {"年化": c_, "回落": m_, "進場次數": ne, "標籤（描述）": A.label(c_, m_, cb, mb)}
                    s["固定天數（描述）"] = fx
                r2x = run(M, (a2,), on.astype(float)[:, None], i0, i1)
                s2 = seg_stats(r2x["eq"], cal, i0, trc)
                s["同規則2倍"] = {"年化": s2["年化"], "回落": s2["回落"], "比值": s2["比值"], "標籤": s2["標籤"]}
                s["3倍減2倍"] = {"年化差": s["年化"] - s2["年化"], "回落差（負＝3倍跌更深）": s["回落"] - s2["回落"]}
                S["格"][f"{k}×{arm}｜{sgn}"] = s
                rows.append({"件": k, "臂": arm, "段": sgn, "起": cal[i0], "迄": cal[i1], "年化": s["年化"], "回落": s["回落"], "比值": s["比值"], "標籤": s["標籤"],
                             "100萬最低剩（萬）": s["100萬最低剩（萬）"], "回本年數": s["回本年數"], "每年換手": s["每年換手"], "基準年化": cb, "基準回落": mb,
                             "2倍年化": s2["年化"], "2倍回落": s2["回落"], "合成": a3.startswith("SYN")})
            # 描述臂
            dsc = {}
            for nm_, on in (("100日線", sig[100]), ("150日線", sig[150]), ("200日線±3%緩衝", sig["band3"])):
                w_ = np.zeros(nn, bool); w_[0] = bool(on[i0 - 1]); w_[1:] = on[i0:i1]
                r = run(M, (a3,), w_.astype(float)[:, None], i0, i1); c_, m_ = A.perf(r["eq"])
                dsc[nm_] = {"年化": c_, "回落": m_, "標籤（描述）": A.label(c_, m_, cb, mb), "每年換手": int(np.sum(w_[1:] != w_[:-1])) / (nn / ANN)}
            # V（波動目標，描述）
            sc = M["C"][f"SYN3_{k}"]; rr = pd.Series(sc).pct_change()
            sg = (rr.rolling(20, min_periods=20).std() * np.sqrt(ANN)).to_numpy()
            me = month_end_mask(cal)
            wv = np.full(n, np.nan); cur = np.nan
            for t in range(1, n):
                if me[t - 1] and np.isfinite(sg[t - 1]) and sg[t - 1] > 0:
                    cur = min(1.0, 0.30 / sg[t - 1])
                wv[t] = cur
            wseg = np.nan_to_num(wv[i0:i1 + 1], nan=0.0)
            r = run(M, (a3,), wseg[:, None], i0, i1); c_, m_ = A.perf(r["eq"])
            dsc["V 波動目標30%"] = {"年化": c_, "回落": m_, "標籤（描述）": A.label(c_, m_, cb, mb), "平均權重": float(np.mean(wseg))}
            for nm_, a_ in (("1倍一直抱", a1), ("2倍一直抱", a2)):
                r = run(M, (a_,), np.ones((nn, 1)), i0, i1); c_, m_ = A.perf(r["eq"])
                dsc[nm_] = {"年化": c_, "回落": m_, "標籤（描述）": A.label(c_, m_, cb, mb), "標的": a_}
            if sgn == "早年合成":
                for nm_, a_ in (("毛費用率", f"SYN3G_{k}"), ("利差0%", f"SYN3_{k}_s0.0"), ("利差0.5%", f"SYN3_{k}_s0.005")):
                    for arm, on in arms.items():
                        r = run(M, (a_,), on.astype(float)[:, None], i0, i1); c_, m_ = A.perf(r["eq"])
                        dsc[f"{arm}×{nm_}"] = {"年化": c_, "回落": m_, "標籤（描述）": A.label(c_, m_, cb, mb)}
            S["描述"][f"{k}｜{sgn}"] = dsc
        for arm in ("H", "M"):
            labs = [S["格"][f"{k}×{arm}｜{sg_[0]}"]["標籤"] for sg_ in segs]
            S["標籤"][f"{k}×{arm}"] = labs[0] if len(set(labs)) == 1 else "看段（" + "／".join(f"{sg_[0]}{l}" for sg_, l in zip(segs, labs)) + "）"
        # 大跌（L22）：連續路徑 E0 ～ 2026-09-30（早年合成接真實？⛔ 用合成一路到底，標合成）；2022 另用真實
        cr = {}
        iE = segs[0][1]; iZ = pos[CAL_END]; nn = iZ - iE + 1
        onF = np.zeros(nn, bool); onF[0] = bool(sig[200][iE - 1]); onF[1:] = sig[200][iE:iZ]
        for arm, on in (("H", np.ones(nn, bool)), ("M", onF)):
            e3 = run(M, (f"SYN3_{k}",), on.astype(float)[:, None], iE, iZ)["eq"]
            e2 = run(M, (f"SYN2_{k}",), on.astype(float)[:, None], iE, iZ)["eq"]
            for cn, (a, b) in C9_CRASH.items():
                cr[f"{arm}｜{cn}（合成連續路徑）"] = {"3倍": crash(e3, cal, iE, pos[a], pos[b]), "2倍": crash(e2, cal, iE, pos[a], pos[b])}
        i0r = pos["2022-01-03"]; nr = iZ - i0r + 1
        onR = np.zeros(nr, bool); onR[0] = bool(sig[200][i0r - 1]); onR[1:] = sig[200][i0r:iZ]
        for arm, on in (("H", np.ones(nr, bool)), ("M", onR)):
            e3 = run(M, (p["real"],), on.astype(float)[:, None], i0r, iZ)["eq"]
            cr[f"{arm}｜2022（真實 {p['real']}）"] = {"3倍": crash(e3, cal, i0r, pos["2022-01-03"], pos["2022-12-30"])}
        cr["^SP500TR 同窗"] = {cn: crash(trc[iE:iZ + 1] / trc[iE - 1], cal, iE, pos[a], pos[b]) for cn, (a, b) in C9_CRASH.items()}
        S["大跌"][k] = cr
        # 對帳（L24）
        il = pos[p["list"]]
        rc = M["C"][p["real"]][il:iZ + 1]; sc = M["C"][f"SYN3_{k}"][il:iZ + 1]
        rr_ = np.diff(rc) / rc[:-1]; sr_ = np.diff(sc) / sc[:-1]
        yrs = (iZ - il + 1) / ANN
        S["對帳"][k] = {"窗": [cal[il], CAL_END], "真實年化": (rc[-1] / rc[0]) ** (1 / yrs) - 1, "合成年化": (sc[-1] / sc[0]) ** (1 / yrs) - 1,
                       "年化差（合成−真實）": ((sc[-1] / sc[0]) ** (1 / yrs)) - ((rc[-1] / rc[0]) ** (1 / yrs)),
                       "日報酬相關": float(np.corrcoef(rr_, sr_)[0, 1]), "日差絕對值平均": float(np.mean(np.abs(rr_ - sr_)))}
    # 先驗對照
    def g(key, f):
        return S["格"][key][f]
    pri = {"TQQQ×H 早年段 100 萬最低剩 ＜ 1 萬": g("TQQQ×H｜早年合成", "100萬最低剩（萬）") < 1, "標籤": S["標籤"]}
    for k in P:
        pri[f"{k}：3倍+200日線比2倍+200日線年化高且回落深10點以上（逐段）"] = {sg_: (g(f"{k}×M｜{sg_}", "3倍減2倍")["年化差"] > 0 and g(f"{k}×M｜{sg_}", "3倍減2倍")["回落差（負＝3倍跌更深）"] <= -0.10)
                                                       for sg_ in ("早年合成", "真實（上市～2021）", "2022～2026-09")}
    S["先驗對照"] = pri
    S["條件出場"] = "M 主規則＝條件出場（指數跌破 200 日線才出、站回才進；⛔ 無最長天數）；各段持有段天數分佈與段尾仍持有見各格「持有」；固定天數只描述"
    S["秒"] = round(time.time() - t0)
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "C9_cells.csv"), index=False, encoding="utf-8")
    jdump(rnd(S), "C9_summary.json")
    log(f"[C9] 完成 {S['秒']}s｜標籤 {S['標籤']}")
    return S


def main():
    global LOGF
    ap = argparse.ArgumentParser(); ap.add_argument("what", choices=("c11", "c12", "c9", "etf")); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    LOGF = os.path.join(OUT, "run_etf.log")
    M = load_market()
    log(f"== researchUSC_late {a.what} 開跑 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜資料 {data_commit()[:12]}｜讀法寫死 {READ_TS}")
    jdump({"資料commit": data_commit(), "稽核": M["audit"], "費用率SEC": M["ER"],
           "檔案sha256": {f: sha256f(p_("macro", f)) for f in ("yahoo_UPRO.csv", "yahoo_TQQQ.csv", "yahoo_IEF.csv", "yahoo_TLT.csv", "yahoo_SHY.csv", "yahoo_GLD.csv",
                                                              "yahoo_TMF.csv", "yahoo_SSO.csv", "yahoo_QLD.csv", "yahoo_SPY.csv", "yahoo_QQQ.csv", "yahoo_SP500TR.csv",
                                                              "yahoo_GSPC.csv", "fred_DTB3.csv", "etf_expense_ratios.csv", "alfred_UNRATE_first_release.csv",
                                                              "alfred_UNRATE_vintages.csv")}}, "data_audit_etf.json")
    if a.what in ("c11", "etf"):
        c11(M)
    if a.what in ("c12", "etf"):
        c12(M)
    if a.what in ("c9", "etf"):
        c9(M)


if __name__ == "__main__":
    main()
