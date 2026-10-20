# -*- coding: utf-8 -*-
"""長線怎麼操作三問 seq1【頻率表・乾跑】（台股策略線 登錄 sha fe24579779402ee8，2026-10-20 19:58；§四b 附件 sha 1ac2310c08e8b759，20:08；
裁定 seq400 發號（甲 S1、S3 的 H250 判、S2 的 H250 只描述；乙方向判；丙描述）、seq403 核 §四b）——回測線計算子代理。
⛔ 只數事件、可用件數、n_eff、不重疊段數、剔除、觸發次數、重疊比例；⛔ 不讀、不算、不存任何進場後報酬（事件報酬、持有報酬、對照 X 一律不算）。
   用到的價格：① 進場前（≤ 訊號日／形成日）的還原收盤（PTH、36 個月報酬、200 日乖離的形成段）；
             ② 丙 F5、F6 的觸發條件（收盤 ÷ 200 日均、可用日起 5 日漲跌）本身要看持有中的價格 ⇒ 只存布林「有沒有觸發、哪天」，⛔ 不存數值、不算持有報酬。
⛔ 不 commit、不改既有程式與結果夾；researchAscTri_freq（load_world）、researchPTH_freq（month_ends、entry_pos 讀法）、research11（load_bars）、patterns（Frame.gate）、
   research34（load_revenue）、researchAddOn（early_extra_bad）、researchLongPool（load_filing、load_fs、load_fin、single、qkey、FW；⚠ 該檔 git 未追蹤）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLong3_freq [--procs 2]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLong3_freq_check
輸出 backtest/resultsLong3/freq/：freq.json、freq_甲.csv、freq_乙.csv、freq_乙_產業.csv、freq_丙.csv、equiv.csv、events_S1.csv.gz、events_丙.csv.gz、
     long_univ.csv.gz（乙每年母體與贏輸旗標，無報酬）、run.log

═══ 讀法（L 標；登錄沒寫清楚、執行者補的都在這裡；⛔ 在看任何本件數字之前寫死；★＝執行者定，〔 〕內為另一讀法）═══
 L1 世界、母體、壞根 ＝ researchAscTri_freq.load_world 原樣（＝ PTH 頻率表 P1）：主 2015-01-05～2026-09-24、早年 2004-02-11～2014-12-31（上市＋上櫃版面）；
    四碼普通股、含已下市；壞根 ＝ load_bars next_bad（缺口 ≥ 5 日 seq335 等）∪ ~/crashwork/bad_*.pkl ∪ 早年 reduce_v2（seq341）。
    ★ 長抱跨 2014／2015 接縫：兩世界日曆首尾相接成一條「合併日曆」（早年全部 ＋ 主全部）；同一代號兩世界的有效 K 棒接起來；⛔ 接縫本身不算壞根；
      跨接縫的價格比只在乙（36 個月形成報酬）用到：早年段還原比 × 接縫原始收盤比（主第一根 ÷ 早年最後一根）× 主段還原比。
 L2 500 張閘 ＝ patterns.Frame.gate ∧ pit_valid ∧ 當天有有效 K 棒，在「訊號可用日」判（S1：可用日前一個交易日 sp；S2、M：月底 t（PTH 頻率表原樣）；乙：形成日 12 月底）。
 L3 S1 營收創 24 個月新高 ＝ research34 rev_hi24 原式（當月 ≥ 前 24 期最高、前 24 期齊全）；營收面板 ＝ 早年版面 revenue_hist（2003-01～2014-12）∪ 主 revenue_hist
    （2015-01～）★ 接成一條（期別必須連續，否則中止）⇒ 2015、2016 年的新高也可判。
    可用日：期別 p 次月 10 日（p ≤ 2025-12）／15 日（p ≥ 2026-01）之後第一個交易日 ＝ 進場日 e（＝ research34.rebalance_dates、記憶 bt-line-revenue-avail-15th）；
    sp ＝ e 前一個交易日（合併日曆）；e 屬哪個世界，事件就屬哪個世界；sp 不在同一世界 ⇒ 剔除「sp跨世界」。
    進場剔除（每筆只記第一個原因，同 PTH P5）：閘外(sp) → 壞根(sp,e] → e無成交（含已下市）→ e開盤鎖漲停；保留 ＝ 事件。
 L4 S2 ＝ 已提交 resultsPTH/freq/events_<世界>.csv.gz 的「入選 ∧ 跳月_st ＝ 保留」原樣（⛔ 不重算）；進場 ＝ 跳月_進場日。
    M（12−1 動能前 30%，只描述）★ ＝ 同一份事件檔、每個形成月在「mom12_1 有值」的排序母體列內取前 ⌈30%⌉（同值併入）∧ 跳月_st ＝ 保留；進場 ＝ 跳月_進場日。
    S3 ★ ＝ S2 事件中，形成月 m 那一期月營收（期別 ＝ 形成月）rev_hi24 為真者（該期可用日 ＝ m＋1 月 10 日後，早於 S2 進場 m＋2 月第一個交易日 ⇒ 無前視）；
       進場、剔除沿用 S2〔另一讀法：S1 的時鐘——S1 保留事件中，期別 p 的月底 PTH 入選者，進場 ＝ S1 的 e；只報件數〕。
 L5 持有 H ∈ {120, 250, 750, 1250} 交易日：★ 出場日 x ＝ e ＋ H − 1（合併日曆位置；e 算第 1 天）。可用 ＝ x ≤ 段尾界線（下）。
    窗內（同 PTH R2）：（進場那根, x 當天或之前最後一根］有壞 K 棒 ⇒「遇壞根（強制賣）」；最後一根有效 K 棒 ＜ x 且距資料尾 ≥ 5 交易日 ⇒「遇下市」；兩者取先到；
    ★ 早年才有、主世界名單沒有、且活到 2014 年底前 5 日內的代號 ⇒ 接縫之後「不明」（另列，不算下市）。
    減資（只數件數）：主世界 adj/<sid>.csv event＝reduce 的日期、早年 researchAddOn.early_extra_bad（reduce_v2＋R8）位置，落在 (e, x] ⇒ 記「窗內有減資」。
 L6 段（登錄 §二）：H250 判定段 ── 探索 ＝ 進場 2017-03-02～2020-12-31 且 x ≤ 2021-12-30（整筆落在 2021 年底前）；確認 ＝ 進場 2022-01-03 起且 x ≤ 資料尾；
    H120（橋接）★ 同兩段的「整筆落在段內」：探索 進場 2017-03-02 起、x ≤ 2021-12-30；確認同上；早年（描述）＝ 進場 2005～2014、x ≤ 資料尾。
    H750、H1250（只描述）＝ 進場 2005-01-01～2021-12-31、x ≤ 資料尾，另拆 2005～2014／2015～2021。
    n_eff ＝ min(可用事件數, 有事件的進場月數)；n_eff ＜ 30 ⇒ 依構造不可判定。不重疊段數 ★ ＝ 依進場日排序貪婪取「上一段 x 之後才進場」的段數（H 長度不重疊區塊）。
    S2 的 H250 依 seq400 標「只描述（52 週新高件已看過抱 12 個月）」。
 L7 乙（De Bondt & Thaler）：形成日 t ＝ Y 年 12 月最後一個交易日，Y ＝ 2007～2022；母體 ＝ L2 閘 ∧ t−36 個月（Y−3 年 12 月最後交易日）當天或之前有有效 K 棒（上市滿 36 個月）
    ∧ 窗內無壞根（同 PTH P3 ★）；R36 ＝ 還原收盤比（跨接縫照 L1）。贏家 ＝ 前 ⌈10%⌉、輸家 ＝ 後 ⌈10%⌉（同值併入）。
    進場 ★ ＝ Y＋1 年第一個交易日開盤；剔除同 L3（壞根(t,e]、e無成交、e開盤鎖漲停）。持有 12／24／36 個月 ★ ＝ 到 Y＋1／Y＋2／Y＋3 年 12 月最後一個交易日；窗內壞根、下市照 L5 只數件數。
    產業層：產業 ＝ 月營收檔「產業別」在期別 Y-12（沒有 ⇒ 該代號 ≤ Y-12 最後一期）★；產業 R36 ＝ 母體內成員等權平均，★ 成員 ≥ 5 檔的產業才排名；前 3／後 3 產業。
    不重疊段 ＝ 形成年貪婪「隔 3 年」（2007、2010、…）。
 L8 丙（描述，F1～F7）：進場 ＝ S1 保留事件；基準窗 ＝ e 起 750 個交易日（x ＝ e＋749，超過資料尾 ⇒ 截到資料尾，另報「窗完整」子集）；
    ★ 有效窗尾 xe ＝ min(x, 遇壞根前一根、下市最後一根)；判斷日 d ∈ [e, xe−1]（d 收盤判、d＋1 開盤賣）；每法只記第一次觸發。
    F1 近 4 季營收合計年增 ＜ 0：季營收 ＝ researchLongPool.load_fin rev_ytd 差分成單季（無 ⇒ load_fs 營業收入）；需 8 季齊全、前 4 季合計 ＞ 0。
    F2 單季毛利率連 2 季年減：毛利率 ＝ 單季營業毛利（毛損）淨額（無 ⇒ 營業毛利（毛損）；fs_hist 沒有該公司 ⇒ fin_hist gp_ytd）÷ 單季營業收入（＞ 0）；
       q 與 q−1 兩季都 ＜ 去年同季；只有半年報（無 Q1／Q3 列）的公司數照報。
    F1、F2 判斷日 ＝ 該季財報上傳日（researchLongPool.load_filing：AI1 最早一筆，否則全部文件最早一筆）當天或之前最後一個交易日 ★；
       沒有上傳時戳 ⇒ 法定期限（Q1 5/15、Q2 8/14、Q3 11/14、Q4 次年 3/31）後第一個交易日再加 5 個交易日（researchExtAuth A2 同式）。
    F3 月營收年增連 3 個月 ＜ 0：期別 q 可用日 A(q)（L3 同式）當天判（q、q−1、q−2 年增都可算且 ＜ 0）；只看 e 之後新公布的期別。
    F4 本益比 ≥ 自身近 5 年第 90 百分位：stocks_per 官方 per（主 2015 起、早年 2012～2014 只有上市）接成合併日曆；★ per ≤ 0 或缺 ⇒ 缺；
       分位 ＝ 含當天的最近 1250 個合併日曆交易日、有值 ≥ 750 天才判（pandas rolling quantile 線性）；每個交易日判。
    F5 收盤 ÷ 200 日均線在當天全市場前 5%：比值 ＝ 還原收盤 ÷ 最近 200 根有效 K 棒收盤平均（200 根內有壞根 ⇒ 缺）；
       ★ 全市場 ＝ 該世界全部代號（不看 500 張閘）當天有比值者（≥ 20 檔）；門檻 ＝ 第 95 百分位（numpy 線性），比值 ≥ 門檻 ⇒ 觸發；每個交易日判。
    F6 利多反應完：e 之後新公布的期別 q 仍 rev_hi24，且 ★ 5 日報酬 ＝ 收盤(A＋4) ÷ 收盤(A−1) − 1 ≤ 0（各取當天或之前最後一根有效 K 棒；[A, A＋4] 沒有有效 K 棒、
       或 (A−1, A＋4] 有壞根 ⇒ 不判）；判斷日 ＝ A＋4。
    F7 ＝ F6 的判斷日當天 F4 或 F5 也成立。
    等價自查：F7 對 F6（F6 首次觸發中 F7 同日首次觸發的比例；F6 全部觸發日中 F4∨F5 成立的比例）、F4 對 F5（同一筆兩者都觸發、首次同日的比例）、F1 對 F3（兩者都觸發、首次相距 ≤ 63 交易日）。
 L9 S3 對 S1／S2 重疊（seq377）：|S3| ÷ |S2|、S1 保留事件中「同期別月底 PTH 入選」比例；F7 對 F6 見 L8。
"""
from __future__ import annotations

import argparse
import glob
import gzip
import hashlib
import json
import math
import os
import pickle
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchAscTri_freq as AT              # noqa: E402  load_world（⛔ 只 import）
from backtest import research11 as R                        # noqa: E402  load_bars
from backtest import patterns as P                          # noqa: E402  Frame.gate
from backtest import research34 as R34                      # noqa: E402  load_revenue
from backtest import researchAddOn as RA                    # noqa: E402  early_extra_bad、WORK
from backtest import researchLongPool as LP                 # noqa: E402  load_filing、load_fs、load_fin、single、qkey、FW
from backtest import universe_gate as UG                    # noqa: E402
import backtest.data as D                                   # noqa: E402

UG.set_gate_v2(True)

REGS = {"fe24579779402ee8": "主件", "1ac2310c08e8b759": "§四b 附件"}
MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
OUT = "backtest/resultsLong3/freq"
PTHEV = "backtest/resultsPTH/freq/events_{}.csv.gz"
HS = (120, 250, 750, 1250)
NEFF_MIN = 30
TOPQ = 0.30
DEC = 0.10
FD = os.path.join(LP.FW, "data")
_G: dict = {}
LOG: list = []
ST_GATE, ST_SPX, ST_BAD, ST_NOTRD, ST_UPL, ST_KEEP = "閘外(sp)", "sp跨世界", "壞根(sp,e]", "e無成交", "e開盤鎖漲停", "保留"


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def reg_check():
    out = {}
    for sha, nm in REGS.items():
        fs = [f for f in glob.glob(os.path.join(MAILBOX, "*.md")) if f"sha{sha}" in os.path.basename(f) and os.path.basename(f).startswith("登錄全文")]
        if not fs:
            raise SystemExit(f"⛔ 信箱找不到登錄全文 sha{sha}")
        for f in fs:
            b = open(f, "rb").read()
            h = hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]
            if h != sha:
                raise SystemExit(f"⛔ 登錄 sha {h} ≠ {sha}（{f}）")
        out[nm] = os.path.basename(fs[0])
    return out


# ═════════════ 逐股（各世界）═════════════
def stock_job(a):
    wn, sid = a
    W = _G[wn]; cal = W["cal"]; n0 = W["n0"]; i = W["ix"][sid]
    D.DATA = W["data"]
    B = R.load_bars(sid, W["mk"].get(sid, "twse"), cal)
    if B is None:
        return wn, sid, None
    df = B["df"]; idx = B["idx"].astype(np.int64); nb = len(idx)
    if len(df) != n0:
        raise SystemExit(f"⛔ {wn} {sid} df 長 {len(df)} ≠ 日曆 {n0}")
    c = np.asarray(B["c"], float)
    if not np.isfinite(c).all():
        raise SystemExit(f"⛔ {wn} {sid} 有效 K 棒收盤有缺值")
    raw = df["close"].to_numpy(float)[idx]
    bad = np.asarray(B["next_bad"][:nb] == np.arange(nb), bool)
    for p_ in W["BADPOS"].get(sid, ()):
        k = int(np.searchsorted(idx, p_, "left"))
        if k < nb:
            bad[k] = True
    f = P.Frame(df, set())
    has = np.zeros(n0, bool); has[idx] = True
    gate = np.asarray(f.gate, bool) & np.asarray(W["PV"][i], bool) & has
    # F5 比值：最近 200 根有效 K 棒（含當根）均線；200 根內（第 2 根起）有壞根 ⇒ 缺
    rat = np.full(nb, np.nan)
    if nb >= 200:
        cs = np.r_[0.0, np.cumsum(c)]; CB = np.r_[0, np.cumsum(bad)]
        k = np.arange(199, nb)
        ok = (CB[k + 1] - CB[k - 198]) == 0
        kk = k[ok]
        rat[kk] = c[kk] / ((cs[kk + 1] - cs[kk - 199]) / 200.0)
    return wn, sid, {"idx": idx.astype(np.int32), "bad": bad, "c": c, "raw": raw, "gate": np.packbits(gate), "rat": rat.astype(np.float32)}


def per_job(sid):
    """F4：合併日曆上的官方 per、近 1250 日第 90 百分位 ⇒ 觸發位置（合併日曆）。"""
    CP = _G["CPOS"]; NC = _G["NC"]
    arr = np.full(NC, np.nan)
    n_src = {}
    for nm, d in (("早年", _G["DATA_E"]), ("主", _G["DATA_M"])):
        p = os.path.join(d, "stocks_per", f"{sid}.csv")
        if not os.path.exists(p):
            continue
        x = pd.read_csv(p, usecols=["date", "per"])
        x["per"] = pd.to_numeric(x["per"], errors="coerce")
        x = x.drop_duplicates("date", keep="last")
        pos = x["date"].map(CP)
        m = pos.notna() & np.isfinite(x["per"]) & (x["per"] > 0)
        arr[pos[m].astype(int).to_numpy()] = x["per"][m].to_numpy(float)
        n_src[nm] = int(m.sum())
    if not n_src:
        return sid, None, n_src
    s = pd.Series(arr)
    q90 = s.rolling(1250, min_periods=750).quantile(0.9).to_numpy()
    with np.errstate(invalid="ignore"):
        trig = np.isfinite(arr) & np.isfinite(q90) & (arr >= q90)
    judg = np.isfinite(arr) & np.isfinite(q90)
    return sid, (np.flatnonzero(trig).astype(np.int32), np.flatnonzero(judg).astype(np.int32)), n_src


# ═════════════ 小工具 ═════════════
def qd(a):
    a = np.asarray([x for x in a if x is not None and np.isfinite(x)], float)
    if len(a) == 0:
        return None
    return {"n": int(len(a)), "中位": round(float(np.median(a)), 4), "p25": round(float(np.percentile(a, 25)), 4),
            "p75": round(float(np.percentile(a, 75)), 4), "min": round(float(a.min()), 4), "max": round(float(a.max()), 4)}


def greedy_segments(entries, H):
    n = 0; last = -10 ** 9
    for e in sorted(entries):
        if e > last:
            n += 1; last = e + H - 1
    return n


def topk_sel(v, q, top=True):
    """v：有值陣列；回布林（前／後 ⌈q·n⌉、同值併入）。"""
    n = len(v)
    if n == 0:
        return np.zeros(0, bool)
    k = int(math.ceil(q * n))
    srt = np.sort(v)[::-1] if top else np.sort(v)
    cut = srt[k - 1]
    return (v >= cut) if top else (v <= cut)


def load_rev_pit(datas):
    """月營收面板（早年 ∪ 主）：rev、rev_ly（期別 × 代號）、產業別（期別, 代號）。"""
    revs, lys, inds = [], [], []
    for d in datas:
        D.DATA = d
        rv, ly, _ = R34.load_revenue()
        revs.append(rv); lys.append(ly)
        fs = sorted(glob.glob(os.path.join(d, "mops", "revenue_hist", "*.csv")))
        x = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "產業別"]) for f in fs]).drop_duplicates(["stock_id", "period"], keep="last")
        inds.append(x)
    rev = pd.concat(revs); ly = pd.concat(lys)
    rev = rev[~rev.index.duplicated(keep="last")].sort_index(); ly = ly[~ly.index.duplicated(keep="last")].sort_index()
    ind = pd.concat(inds).drop_duplicates(["stock_id", "period"], keep="last")
    per = list(rev.index)
    pp = [int(p[:4]) * 12 + int(p[5:]) - 1 for p in per]
    if any(b - a != 1 for a, b in zip(pp[:-1], pp[1:])):
        raise SystemExit("⛔ 月營收期別不連續")
    return rev, ly.reindex(index=rev.index, columns=rev.columns), ind


# ═════════════ 主程式 ═════════════
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    t0 = time.time()
    out_dir = OUT if a.limit is None else os.path.join(OUT, "_try")
    os.makedirs(out_dir, exist_ok=True)
    regs = reg_check()
    log(f"[登錄] {regs}（sha 已驗）")
    J = {"性質": "長線怎麼操作三問 seq1 頻率表乾跑（⛔ 未讀、未算任何進場後報酬）", "登錄": regs,
         "裁定": "seq400 發號（N_前段 ＋4：甲 S1、S3 的 H250 ＋2、乙 ＋2；丙不計）；seq403 核 §四b F4～F7"}
    # ── 世界
    WS = {}
    for wn in ("早年", "主"):
        WS[wn] = AT.load_world(wn)
    We, Wm = WS["早年"], WS["主"]
    ne, nm_ = We["n0"], Wm["n0"]
    if not We["cal"][-1] < Wm["cal"][0]:
        raise SystemExit("⛔ 兩世界日曆重疊")
    CAL = We["cal"].append(Wm["cal"]); NC = len(CAL); CEND = NC - 1
    OFF = {"早年": 0, "主": ne}
    CP = {d.strftime("%Y-%m-%d"): j for j, d in enumerate(CAL)}
    cpos = lambda ts: int(CAL.searchsorted(pd.Timestamp(ts)))                 # 第一個 ≥ ts
    cpos_le = lambda ts: int(CAL.searchsorted(pd.Timestamp(ts), side="right")) - 1   # 最後一個 ≤ ts
    log(f"[合併日曆] {CAL[0].date()}～{CAL[-1].date()}｜{NC} 日（早年 {ne}＋主 {nm_}）")
    # ── 月營收
    rev, ly, IND = load_rev_pit([We["data"], Wm["data"]])
    PER = list(rev.index); KP = {p: k for k, p in enumerate(PER)}
    RV = rev.to_numpy(float); LY = ly.to_numpy(float); RSID = list(rev.columns); RIX = {s: j for j, s in enumerate(RSID)}
    HI = np.full(RV.shape, -1, np.int8)
    for k in range(24, len(PER)):
        h = RV[k - 24:k]; full = np.isfinite(h).all(axis=0)
        mx = np.where(full, np.nanmax(np.where(np.isfinite(h), h, -np.inf), axis=0), np.nan)
        r0 = RV[k]
        okk = full & np.isfinite(r0)
        HI[k, okk] = (r0[okk] >= mx[okk]).astype(np.int8)
    with np.errstate(divide="ignore", invalid="ignore"):
        YOY = np.where(np.isfinite(LY) & (LY > 0) & np.isfinite(RV), RV / LY - 1.0, np.nan)
    AV = np.full(len(PER), -1, np.int64)                                      # 可用日 e（合併日曆）
    for k, p in enumerate(PER):
        y, m = int(p[:4]), int(p[5:])
        y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
        cut = pd.Timestamp(y2, m2, 15 if p >= "2026-01" else 10)
        e = int(CAL.searchsorted(cut, side="right"))
        if 1 <= e <= CEND:
            AV[k] = e
    log(f"[月營收] 期別 {PER[0]}～{PER[-1]}（{len(PER)} 期連續）｜代號 {len(RSID)}｜可判 rev_hi24 股-月 {int((HI >= 0).sum()):,}｜新高 {int((HI == 1).sum()):,}")
    # ── 逐股
    _G.update(WS)
    jobs = []
    for wn in ("早年", "主"):
        sids = WS[wn]["sids"][:a.limit] if a.limit else WS[wn]["sids"]
        jobs += [(wn, s) for s in sids]
    RES = {"早年": {}, "主": {}}
    with Pool(a.procs) as pool:
        for k_, (wn, sid, r) in enumerate(pool.imap_unordered(stock_job, jobs, chunksize=8)):
            RES[wn][sid] = r
            if (k_ + 1) % 500 == 0:
                log(f"  逐股 {k_ + 1}／{len(jobs)}｜{time.time() - t0:.0f}s")
    nskip = {wn: sum(1 for r in RES[wn].values() if r is None) for wn in RES}
    log(f"[逐股完] load_bars 不足 260 根：{nskip}｜{time.time() - t0:.0f}s")
    # ── 合併每檔
    SS = {}
    main_sids = {s for s, r in RES["主"].items() if r is not None}
    for s in sorted(set(RES["早年"]) | set(RES["主"])):
        parts = [(wn, RES[wn].get(s)) for wn in ("早年", "主") if RES[wn].get(s) is not None]
        if not parts:
            continue
        pos = np.concatenate([r["idx"].astype(np.int64) + OFF[wn] for wn, r in parts])
        bad = np.concatenate([r["bad"] for wn, r in parts])
        c = np.concatenate([r["c"] for wn, r in parts]); raw = np.concatenate([r["raw"] for wn, r in parts])
        wid = np.concatenate([np.full(len(r["idx"]), 0 if wn == "早年" else 1, np.int8) for wn, r in parts])
        SS[s] = {"pos": pos, "bad": bad, "CB": np.r_[0, np.cumsum(bad)], "c": c, "raw": raw, "wid": wid, "main": s in main_sids,
                 "last": int(pos[-1])}
    # 接縫：主世界第一根不算壞根（L1）——上面對兩段相接處第一根主世界 K 棒強制 False；只有主世界者保留原旗標
    for s in SS:
        S = SS[s]
        if (S["wid"] == 0).any() and (S["wid"] == 1).any():
            j = int(np.argmax(S["wid"] == 1)); S["bad"][j] = False; S["CB"] = np.r_[0, np.cumsum(S["bad"])]
    log(f"[合併] 代號 {len(SS)}｜兩世界都有 {sum(1 for S in SS.values() if (S['wid'] == 0).any() and (S['wid'] == 1).any())}")
    # ── 減資日期
    RED = {}
    for s in SS:
        p_ = os.path.join(Wm["data"], "adj", f"{s}.csv")
        if os.path.exists(p_):
            x = pd.read_csv(p_, usecols=["date", "event"])
            for d in x.loc[x["event"] == "reduce", "date"]:
                if d in CP:
                    RED.setdefault(s, []).append(CP[d])
    Wa = pickle.load(open(os.path.join(RA.WORK, "world_早年.pkl"), "rb"))
    EX, excnt = RA.early_extra_bad(Wa, lambda *x: None)
    for s, ks in EX.items():
        for k in ks:
            RED.setdefault(s, []).append(int(k))
    RED = {s: np.array(sorted(set(v)), np.int64) for s, v in RED.items()}
    log(f"[減資] 主 adj reduce＋早年 reduce_v2/R8：{sum(len(v) for v in RED.values())} 股日｜早年來源 {excnt}")

    def window(s, e, x):
        """回 (狀態, 窗內有減資)。狀態：資料尾不足／完整／遇壞根／遇下市／接縫不明。"""
        if x > CEND:
            return "資料尾不足", False
        S = SS[s]; pos = S["pos"]
        ke = int(np.searchsorted(pos, e, "right")) - 1
        kx = int(np.searchsorted(pos, x, "right")) - 1
        ev = []
        if kx > ke and S["CB"][kx + 1] - S["CB"][ke + 1] > 0:
            kb = ke + 1 + int(np.argmax(S["bad"][ke + 1:kx + 1]))
            ev.append((int(pos[kb]), "遇壞根"))
        L = S["last"]
        if L < x:
            if (not S["main"]) and L >= ne - 5:
                if x >= ne:
                    ev.append((ne, "接縫不明"))
            elif CEND - L >= 5:
                ev.append((L + 1, "遇下市"))
        st = min(ev)[1] if ev else "完整"
        rd = RED.get(s)
        red = bool(rd is not None and ((rd > e) & (rd <= x)).any())
        return st, red

    def eff_end(s, e, x):
        """丙的有效窗尾：min(x, 遇壞根前一根、下市最後一根、資料尾)。"""
        x = min(x, CEND)
        S = SS[s]; pos = S["pos"]
        ke = int(np.searchsorted(pos, e, "right")) - 1
        kx = int(np.searchsorted(pos, x, "right")) - 1
        xe = x
        if kx > ke and S["CB"][kx + 1] - S["CB"][ke + 1] > 0:
            kb = ke + 1 + int(np.argmax(S["bad"][ke + 1:kx + 1]))
            xe = min(xe, int(pos[kb - 1]))
        if S["last"] < xe and CEND - S["last"] >= 5:
            xe = min(xe, S["last"])
        return xe

    # ═════════ S1 ═════════
    rows = []
    for wn in ("早年", "主"):
        W = WS[wn]; off = OFF[wn]; n0 = W["n0"]
        for s, r in RES[wn].items():
            if r is None or s not in RIX:
                continue
            j = RIX[s]; gate = np.unpackbits(r["gate"])[:n0].astype(bool)
            i = W["ix"][s]; idx = r["idx"].astype(np.int64); CBw = np.r_[0, np.cumsum(r["bad"])]
            for k in np.flatnonzero(HI[:, j] == 1):
                e = int(AV[k])
                if e < 0 or not (off <= e < off + n0):
                    continue
                ew = e - off; sp = e - 1
                rec = {"sid": s, "期別": PER[k], "世界": wn, "e": e, "sp": sp}
                if not (off <= sp < off + n0):
                    rec["st"] = ST_SPX
                else:
                    spw = sp - off
                    if not gate[spw]:
                        rec["st"] = ST_GATE
                    else:
                        ksp = int(np.searchsorted(idx, spw, "right")) - 1
                        kee = int(np.searchsorted(idx, ew, "right")) - 1
                        if kee > ksp and CBw[kee + 1] - CBw[ksp + 1] > 0:
                            rec["st"] = ST_BAD
                        elif not (W["TRD"][i, ew] and np.isfinite(W["O"][i, ew]) and W["O"][i, ew] > 0):
                            rec["st"] = ST_NOTRD
                        elif W["UPL"][i, ew]:
                            rec["st"] = ST_UPL
                        else:
                            rec["st"] = ST_KEEP
                rows.append(rec)
    S1 = pd.DataFrame(rows)
    S1["進場日"] = [str(CAL[e].date()) for e in S1["e"]]; S1["sp日"] = [str(CAL[p].date()) for p in S1["sp"]]
    log(f"[S1] 營收新高股-月（e 在世界內）{len(S1):,}｜狀態 {S1['st'].value_counts().to_dict()}")
    # ═════════ S2、M、S3 ═════════
    ev = []
    for wn in ("早年", "主"):
        x = pd.read_csv(PTHEV.format(wn), dtype={"sid": str})
        x["世界"] = wn
        ev.append(x)
    EV = pd.concat(ev, ignore_index=True)
    EV["e"] = EV["跳月_進場日"].map(lambda d: CP.get(d, -1) if isinstance(d, str) else -1)
    EV["期別"] = EV["形成月底"].str[:7]
    S2 = EV[EV["入選"] & (EV["跳月_st"] == "保留")].copy()
    mm = EV[np.isfinite(EV["mom12_1"])].copy()
    mm = mm.reset_index(drop=True)
    msel = np.zeros(len(mm), bool)
    for _, ii in mm.groupby(["世界", "形成月底"]).indices.items():
        msel[ii] = topk_sel(mm["mom12_1"].to_numpy(float)[ii], TOPQ, True)
    MM = mm[msel & (mm["跳月_st"] == "保留").to_numpy()].copy()
    hi_of = lambda s, p: int(HI[KP[p], RIX[s]]) if (p in KP and s in RIX) else -1
    S2["hi24"] = [hi_of(s, p) for s, p in zip(S2["sid"], S2["期別"])]
    S3 = S2[S2["hi24"] == 1].copy()
    pth_sel = set(zip(EV.loc[EV["入選"], "sid"], EV.loc[EV["入選"], "期別"]))
    S1k = S1[S1["st"] == ST_KEEP].copy()
    S1k["PTH入選同期"] = [(s, p) in pth_sel for s, p in zip(S1k["sid"], S1k["期別"])]
    S3alt = S1k[S1k["PTH入選同期"]]
    log(f"[S2] {len(S2):,}｜[M] {len(MM):,}｜[S3] {len(S3):,}（另一讀法 S1 時鐘 {len(S3alt):,}）｜S2 中 hi24 不可判 {int((S2['hi24'] < 0).sum())}")
    SETS = {"S1": S1k[["sid", "e"]], "S2": S2[["sid", "e"]], "S3": S3[["sid", "e"]], "M": MM[["sid", "e"]], "S3_另一讀法": S3alt[["sid", "e"]]}
    # ═════════ 甲：H × 段 ═════════
    p170302, p201231, p211230, p220103 = cpos("2017-03-02"), cpos_le("2020-12-31"), cpos_le("2021-12-30"), cpos("2022-01-03")
    p05, p141231, p211231 = cpos("2005-01-01"), cpos_le("2014-12-31"), cpos_le("2021-12-31")
    SEGDEF = {}
    for H in (120, 250):
        SEGDEF[(H, "探索")] = (p170302, p201231 if H == 250 else p211230, p211230)
        SEGDEF[(H, "確認")] = (p220103, CEND, CEND)
        SEGDEF[(H, "早年(描述)")] = (p05, p141231, CEND)
    for H in (750, 1250):
        SEGDEF[(H, "長窗2005～2021")] = (p05, p211231, CEND)
        SEGDEF[(H, "長窗_2005～2014")] = (p05, p141231, CEND)
        SEGDEF[(H, "長窗_2015～2021")] = (p141231 + 1, p211231, CEND)
    FA = []; WIN = {}
    for nm, T in SETS.items():
        nmiss = int((~T["sid"].isin(SS)).sum())
        if nmiss and a.limit is None:
            raise SystemExit(f"⛔ {nm} 有 {nmiss} 筆代號沒有合併 K 棒")
        T = T[(T["e"] >= 0) & T["sid"].isin(SS)]
        for (H, sg), (a0, a1, xb) in SEGDEF.items():
            sub = T[(T["e"] >= a0) & (T["e"] <= a1)]
            stc = {"完整": 0, "遇壞根": 0, "遇下市": 0, "接縫不明": 0}; red = 0; avail = []; navail_tail = 0
            for s, e in zip(sub["sid"], sub["e"]):
                x = int(e) + H - 1
                if x > xb:
                    navail_tail += 1; continue
                key = (s, int(e), H)
                if key not in WIN:
                    WIN[key] = window(s, int(e), x)
                st, rd = WIN[key]
                stc[st] += 1; red += int(rd); avail.append(int(e))
            months = len({CAL[e].strftime("%Y-%m") for e in avail})
            n = len(avail); ne_ = min(n, months)
            row = {"集合": nm, "H": H, "段": sg, "進場界": f"{CAL[a0].date()}～{CAL[a1].date()}", "x上限": str(CAL[min(xb, CEND)].date()),
                   "段內進場事件": int(len(sub)), "窗超出段尾(不可用)": navail_tail, "可用": n, "有事件進場月": months, "n_eff": ne_,
                   "n_eff<30": bool(ne_ < NEFF_MIN), "不重疊段數": greedy_segments(avail, H),
                   **{f"窗_{k}": v for k, v in stc.items()}, "窗內有減資": red,
                   "遇壞根比例": round(stc["遇壞根"] / n, 4) if n else None, "遇下市比例": round(stc["遇下市"] / n, 4) if n else None,
                   "減資比例": round(red / n, 4) if n else None}
            if nm in ("S1", "S3") and H == 250 and sg in ("探索", "確認"):
                row["性質"] = "判定格（seq400）" if ne_ >= NEFF_MIN else "判定格但依構造不可判定"
            elif nm == "S2" and H == 250 and sg in ("探索", "確認"):
                row["性質"] = "只描述（seq400：52 週新高件已看過抱 12 個月）"
            elif nm == "S3_另一讀法":
                row["性質"] = "另一讀法（只報件數）"
            else:
                row["性質"] = "描述"
            FA.append(row)
        log(f"[甲 {nm}] " + "｜".join(f"H{r['H']}{r['段']} 可用{r['可用']} n_eff{r['n_eff']} 段{r['不重疊段數']}" for r in FA if r["集合"] == nm and r["段"] in ("探索", "確認", "長窗2005～2021")))
    # S3 對 S1／S2 重疊（seq377）
    EQ = {}
    for sg, (a0, a1) in {"探索(進場)": (p170302, p211230), "確認(進場)": (p220103, CEND), "早年(進場)": (p05, p141231)}.items():
        n1 = int(((S1k["e"] >= a0) & (S1k["e"] <= a1)).sum()); n2 = int(((S2["e"] >= a0) & (S2["e"] <= a1)).sum())
        n3 = int(((S3["e"] >= a0) & (S3["e"] <= a1)).sum()); n3a = int(((S3alt["e"] >= a0) & (S3alt["e"] <= a1)).sum())
        EQ[f"S3對S1S2_{sg}"] = {"S1": n1, "S2": n2, "S3": n3, "S3÷S2": round(n3 / n2, 4) if n2 else None, "S3÷S1": round(n3 / n1, 4) if n1 else None,
                               "S1中同期PTH入選(S3另一讀法)": n3a, "S3另一讀法÷S1": round(n3a / n1, 4) if n1 else None}
    log(f"[等價 S3] {EQ}")
    # ═════════ 乙 ═════════
    MEY = {}
    for Y in range(2004, 2027):
        p_ = cpos_le(f"{Y}-12-31")
        if p_ >= 0 and CAL[p_].year == Y and CAL[p_].month == 12:
            MEY[Y] = p_
    gate_c = {}
    for wn in ("早年", "主"):
        n0 = WS[wn]["n0"]
        for s, r in RES[wn].items():
            if r is not None:
                gate_c[(wn, s)] = np.unpackbits(r["gate"])[:n0].astype(bool)

    def r_between(s, k0, k1):
        S = SS[s]; w0, w1 = S["wid"][k0], S["wid"][k1]
        if w0 == w1:
            return S["c"][k1] / S["c"][k0]
        j = int(np.argmax(S["wid"] == 1))
        return (S["c"][j - 1] / S["c"][k0]) * (S["raw"][j] / S["raw"][j - 1]) * (S["c"][k1] / S["c"][j])

    def ind_of(s, Y):
        g = IND_BY.get(s)
        if g is None:
            return ""
        ps, vs = g
        k = int(np.searchsorted(ps, f"{Y}-12", "right")) - 1
        return vs[k] if k >= 0 else ""

    IND_BY = {s: (g["period"].to_numpy(), g["產業別"].fillna("").to_numpy()) for s, g in IND.sort_values("period").groupby("stock_id")}
    FB = []; FBI = []; UNIV = []
    for Y in range(2007, 2023):
        t = MEY[Y]; t0_ = MEY[Y - 3]; wn = "早年" if t < ne else "主"; W = WS[wn]; off = OFF[wn]
        e = t + 1
        uni = []
        for s in SS:
            g = gate_c.get((wn, s))
            if g is None or not g[t - off]:
                continue
            S = SS[s]; pos = S["pos"]
            kt = int(np.searchsorted(pos, t, "right")) - 1
            k0 = int(np.searchsorted(pos, t0_, "right")) - 1
            if kt < 0 or pos[kt] != t:
                continue
            if k0 < 0:
                continue
            if S["CB"][kt + 1] - S["CB"][k0 + 1] > 0:
                continue
            uni.append((s, r_between(s, k0, kt) - 1.0))
        sids = [u[0] for u in uni]; R36 = np.array([u[1] for u in uni], float)
        win = topk_sel(R36, DEC, True); los = topk_sel(R36, DEC, False)
        # 進場狀態
        ew_wn = "早年" if e < ne else "主"; We_ = WS[ew_wn]; offe = OFF[ew_wn]
        ent = {}
        for s in sids:
            S = SS[s]; pos = S["pos"]
            kt = int(np.searchsorted(pos, t, "right")) - 1; ke = int(np.searchsorted(pos, e, "right")) - 1
            if ke > kt and S["CB"][ke + 1] - S["CB"][kt + 1] > 0:
                ent[s] = "壞根(t,e]"; continue
            if s not in We_["ix"]:
                ent[s] = "e無成交"; continue
            i = We_["ix"][s]; ew = e - offe
            if not (We_["TRD"][i, ew] and np.isfinite(We_["O"][i, ew]) and We_["O"][i, ew] > 0):
                ent[s] = "e無成交"
            elif We_["UPL"][i, ew]:
                ent[s] = "e開盤鎖漲停"
            else:
                ent[s] = "保留"
        row = {"形成年": Y, "形成日": str(CAL[t].date()), "世界": wn, "進場日": str(CAL[e].date()), "母體": len(sids), "⌈10%⌉": int(math.ceil(DEC * len(sids))),
               "贏家": int(win.sum()), "輸家": int(los.sum())}
        for grp, msk in (("贏家", win), ("輸家", los)):
            gs = [s for s, m in zip(sids, msk) if m]
            keep = [s for s in gs if ent[s] == "保留"]
            row[f"{grp}_保留"] = len(keep)
            for kk in ("壞根(t,e]", "e無成交", "e開盤鎖漲停"):
                row[f"{grp}_剔除_{kk}"] = sum(1 for s in gs if ent[s] == kk)
            for mo in (12, 24, 36):
                xp = MEY.get(Y + mo // 12, -1)
                if xp < 0:
                    row[f"{grp}_{mo}月_可用"] = 0; continue
                cnt = {"完整": 0, "遇壞根": 0, "遇下市": 0, "接縫不明": 0}; red = 0
                for s in keep:
                    st, rd = window(s, e, xp)
                    cnt[st] += 1; red += int(rd)
                row[f"{grp}_{mo}月_可用"] = len(keep)
                for kk, v in cnt.items():
                    row[f"{grp}_{mo}月_{kk}"] = v
                row[f"{grp}_{mo}月_窗內有減資"] = red
        # 產業
        inds = [ind_of(s, Y) for s in sids]
        df_ = pd.DataFrame({"sid": sids, "R": R36, "ind": inds})
        g = df_[df_["ind"] != ""].groupby("ind")["R"].agg(["mean", "size"])
        g5 = g[g["size"] >= 5].sort_values("mean", ascending=False)
        top3 = list(g5.index[:3]); bot3 = list(g5.index[::-1][:3])
        row.update({"無產業別": int((df_["ind"] == "").sum()), "產業數(全部)": int(len(g)), "產業數(≥5檔可排名)": int(len(g5)),
                    "贏家產業": "、".join(top3), "輸家產業": "、".join(bot3),
                    "贏家產業成員": int(df_["ind"].isin(top3).sum()), "輸家產業成員": int(df_["ind"].isin(bot3).sum()),
                    "贏家產業成員_保留": int(sum(1 for s, i_ in zip(sids, inds) if i_ in top3 and ent[s] == "保留")),
                    "輸家產業成員_保留": int(sum(1 for s, i_ in zip(sids, inds) if i_ in bot3 and ent[s] == "保留"))})
        for rk, i_ in enumerate(top3):
            FBI.append({"形成年": Y, "組": "贏家產業", "名次": rk + 1, "產業": i_, "成員數": int(g5.loc[i_, "size"])})
        for rk, i_ in enumerate(bot3):
            FBI.append({"形成年": Y, "組": "輸家產業", "名次": rk + 1, "產業": i_, "成員數": int(g5.loc[i_, "size"])})
        FB.append(row)
        for s, m1, m2, i_ in zip(sids, win, los, inds):
            UNIV.append({"形成年": Y, "sid": s, "贏家": bool(m1), "輸家": bool(m2), "產業": i_, "進場": ent[s]})
        log(f"[乙 {Y}] 母體 {len(sids)}｜贏 {int(win.sum())}／輸 {int(los.sum())}｜產業 ≥5 檔 {len(g5)}｜贏產業 {top3}｜輸產業 {bot3}")
    yrs = [r["形成年"] for r in FB]
    nonov = []; last = -99
    for Y in yrs:
        if Y >= last + 3:
            nonov.append(Y); last = Y
    J["乙"] = {"形成次數": len(FB), "形成年": [yrs[0], yrs[-1]], "36個月不重疊段(貪婪隔3年)": nonov, "不重疊段數": len(nonov),
              "36個月窗可用形成年": [r["形成年"] for r in FB if r.get("贏家_36月_可用", 0) > 0],
              "贏家筆數合計": int(sum(r["贏家"] for r in FB)), "輸家筆數合計": int(sum(r["輸家"] for r in FB)),
              "贏家36月遇下市": int(sum(r.get("贏家_36月_遇下市", 0) for r in FB)), "輸家36月遇下市": int(sum(r.get("輸家_36月_遇下市", 0) for r in FB)),
              "贏家36月遇壞根": int(sum(r.get("贏家_36月_遇壞根", 0) for r in FB)), "輸家36月遇壞根": int(sum(r.get("輸家_36月_遇壞根", 0) for r in FB)),
              "贏家36月窗內有減資": int(sum(r.get("贏家_36月_窗內有減資", 0) for r in FB)), "輸家36月窗內有減資": int(sum(r.get("輸家_36月_窗內有減資", 0) for r in FB)),
              "判斷": "只判方向、⛔ 不給合格；不重疊 3 年段 ＜ 30 ⇒ 結果句一律「樣本極少、只看方向」"}
    log(f"[乙] {J['乙']}")
    # ═════════ 丙 ═════════
    # F5 門檻
    F5POS = {}; F5J = {}
    for wn in ("早年", "主"):
        n0 = WS[wn]["n0"]; off = OFF[wn]
        ok = [s for s, r in RES[wn].items() if r is not None]
        M = np.full((len(ok), n0), np.nan, np.float32)
        for q, s in enumerate(ok):
            r = RES[wn][s]; M[q, r["idx"].astype(np.int64)] = r["rat"]
        cnt = np.isfinite(M).sum(axis=0)
        thr = np.full(n0, np.nan)
        for t in np.flatnonzero(cnt >= 20):
            thr[t] = np.percentile(M[np.isfinite(M[:, t]), t], 95)
        with np.errstate(invalid="ignore"):
            T5 = M >= thr[None, :]
        for q, s in enumerate(ok):
            F5POS.setdefault(s, []).append(np.flatnonzero(T5[q]).astype(np.int64) + off)
            F5J.setdefault(s, []).append(np.flatnonzero(np.isfinite(M[q]) & np.isfinite(thr)).astype(np.int64) + off)
        J.setdefault("F5門檻", {})[wn] = {"有門檻日數": int(np.isfinite(thr).sum()), "每日有比值檔數": qd(cnt[cnt > 0])}
        del M, T5
    F5POS = {s: np.concatenate(v) for s, v in F5POS.items()}; F5J = {s: np.concatenate(v) for s, v in F5J.items()}
    # F4
    _G.update({"CPOS": CP, "NC": NC, "DATA_E": We["data"], "DATA_M": Wm["data"]})
    s1sids = sorted(set(S1k["sid"]))
    F4POS = {}; F4J = {}; per_src = {"早年": 0, "主": 0, "無per檔": 0}
    with Pool(a.procs) as pool:
        for sid, rr, nsrc in pool.imap_unordered(per_job, s1sids, chunksize=8):
            if rr is None:
                per_src["無per檔"] += 1; continue
            F4POS[sid], F4J[sid] = rr
            for k in nsrc:
                per_src[k] += 1
    log(f"[F4] per 檔 {per_src}｜{time.time() - t0:.0f}s")
    # F6 5 日：每檔每期別
    def f6_flag(s, q):
        A = int(AV[q])
        if A < 1 or A + 4 > CEND:
            return None
        S = SS[s]; pos = S["pos"]
        ka = int(np.searchsorted(pos, A - 1, "right")) - 1
        kb = int(np.searchsorted(pos, A + 4, "right")) - 1
        if ka < 0 or kb <= ka:
            return None
        if S["CB"][kb + 1] - S["CB"][ka + 1] > 0:
            return None
        if S["wid"][ka] != S["wid"][kb]:
            return None
        return bool(S["c"][kb] / S["c"][ka] - 1.0 <= 0.0)

    # F1、F2、季可用日
    fq = LP.load_filing(FD)[0]
    fid = sorted(set(S1k["sid"]))
    qk0, qk1 = LP.qkey(2012, 1), LP.qkey(2026, 4)
    FIN = LP.load_fin(FD, fid, qk0, qk1); FS = LP.load_fs(FD, fid, qk0, qk1)
    dl = {1: (5, 15), 2: (8, 14), 3: (11, 14)}
    QINFO = {}; qsrc = {"時戳": 0, "期限＋5": 0}; halfyr = 0; nofin = 0
    for s in fid:
        fn = FIN.get(s); fs_ = FS.get(s)
        ks = sorted(set((fn.index if fn is not None else [])) | set((fs_.index if fs_ is not None else [])))
        if not ks:
            nofin += 1; QINFO[s] = None; continue
        revq, gm = {}, {}
        for k in ks:
            v = LP.single(fn["rev_ytd"], k) if (fn is not None and "rev_ytd" in fn) else np.nan
            if not np.isfinite(v) and fs_ is not None:
                v = LP.single(fs_["營業收入"], k)
            revq[k] = v
            gp = np.nan; rq = np.nan
            if fs_ is not None and k in fs_.index:
                col = "營業毛利（毛損）淨額" if np.isfinite(fs_["營業毛利（毛損）淨額"].get(k, np.nan)) else "營業毛利（毛損）"
                gp = LP.single(fs_[col], k); rq = LP.single(fs_["營業收入"], k)
            if not np.isfinite(gp) and fn is not None and "gp_ytd" in fn:
                gp = LP.single(fn["gp_ytd"], k); rq = LP.single(fn["rev_ytd"], k)
            gm[k] = gp / rq if (np.isfinite(gp) and np.isfinite(rq) and rq > 0) else np.nan
        has13 = any(k % 4 in (0, 2) for k in ks)
        halfyr += int(not has13)
        QA = {}
        for k in ks:
            y, q = k // 4, k % 4 + 1
            ts = fq.get((s, k))
            if ts is not None and not pd.isna(ts):
                QA[k] = cpos_le(ts.normalize()); qsrc["時戳"] += 1
            else:
                ddl = pd.Timestamp(y + 1, 3, 31) if q == 4 else pd.Timestamp(y, *dl[q])
                QA[k] = int(CAL.searchsorted(ddl, side="right")) + 5; qsrc["期限＋5"] += 1
        F1 = {}; F2 = {}
        for k in ks:
            a8 = [revq.get(k - j, np.nan) for j in range(8)]
            if all(np.isfinite(a8)) and sum(a8[4:]) > 0:
                F1[k] = bool(sum(a8[:4]) / sum(a8[4:]) - 1.0 < 0)
            g4 = [gm.get(k - j, np.nan) for j in (0, 1, 4, 5)]
            if all(np.isfinite(g4)):
                F2[k] = bool(g4[0] < g4[2] and g4[1] < g4[3])
        QINFO[s] = {"QA": QA, "F1": F1, "F2": F2, "has13": has13}
    log(f"[季報] 公司 {len(fid)}｜無季報 {nofin}｜只有半年報 {halfyr}｜季可用日來源 {qsrc}")
    # 逐事件
    CR = []
    for s, p, e in zip(S1k["sid"], S1k["期別"], S1k["e"]):
        e = int(e); kp = KP[p]; x = e + 749
        xe = eff_end(s, e, x)
        full = x <= CEND
        rec = {"sid": s, "期別": p, "e": e, "進場日": str(CAL[e].date()), "x": x, "窗完整": full, "有效窗尾": str(CAL[xe].date()), "有效窗天數": xe - e + 1}
        d_hi = xe - 1
        trig = {}; judg = {}
        # F3、F6
        j = RIX[s]; f6all = []; f6j = 0; f3j = 0
        for q in range(kp + 1, len(PER)):
            A = int(AV[q])
            if A < 0 or A > d_hi:
                if A > d_hi:
                    break
                continue
            yv = YOY[q - 2:q + 1, j] if q >= 2 else np.array([np.nan])
            if len(yv) == 3 and np.isfinite(yv).all():
                f3j += 1
                if "F3" not in trig and (yv < 0).all():
                    trig["F3"] = A
            if HI[q, j] == 1 and A + 4 <= d_hi:
                fl = f6_flag(s, q)
                if fl is not None:
                    f6j += 1
                    if fl:
                        f6all.append(A + 4)
        judg["F3"] = f3j; judg["F6"] = f6j
        if f6all:
            trig["F6"] = f6all[0]
        # F4、F5
        p4 = F4POS.get(s); p5 = F5POS.get(s)
        in_win = lambda arr: arr[(arr >= e) & (arr <= d_hi)] if arr is not None else np.zeros(0, np.int64)
        w4 = in_win(p4); w5 = in_win(p5)
        judg["F4"] = int(len(in_win(F4J.get(s)))) if s in F4J else 0
        judg["F5"] = int(len(in_win(F5J.get(s))))
        if len(w4):
            trig["F4"] = int(w4[0])
        if len(w5):
            trig["F5"] = int(w5[0])
        s4 = set(w4.tolist()); s5 = set(w5.tolist())
        f7 = [d for d in f6all if d in s4 or d in s5]
        if f7:
            trig["F7"] = f7[0]
        judg["F7"] = f6j
        rec["F6觸發日數"] = len(f6all); rec["F6觸發日中F4或F5"] = len(f7)
        rec["F4F5同日數"] = len(s4 & s5); rec["F4日數"] = len(s4); rec["F5日數"] = len(s5)
        # F1、F2
        qi = QINFO.get(s)
        j1 = j2 = 0
        if qi is not None:
            for k in sorted(qi["QA"]):
                d = qi["QA"][k]
                if d < e or d > d_hi:
                    continue
                if k in qi["F1"]:
                    j1 += 1
                    if "F1" not in trig and qi["F1"][k]:
                        trig["F1"] = d
                if k in qi["F2"]:
                    j2 += 1
                    if "F2" not in trig and qi["F2"][k]:
                        trig["F2"] = d
            rec["只有半年報"] = not qi["has13"]
        else:
            rec["只有半年報"] = None
        judg["F1"] = j1; judg["F2"] = j2
        for F in ("F1", "F2", "F3", "F4", "F5", "F6", "F7"):
            rec[f"{F}_可判次數"] = judg[F]
            rec[f"{F}_首次"] = str(CAL[trig[F]].date()) if F in trig else ""
            rec[f"{F}_天"] = (trig[F] - e + 1) if F in trig else np.nan
        CR.append(rec)
    CR = pd.DataFrame(CR)
    p150101 = cpos("2015-01-01")
    CSEG = {"全部(2007～)": (0, CEND), "早年進場(～2014)": (0, p141231), "2015-01～2017-02進場": (p150101, p170302 - 1),
            "探索進場(2017-03～2021-12)": (p170302, p211230), "確認進場(2022-01～)": (p220103, CEND)}
    FC = []
    for sg, (a0, a1) in CSEG.items():
        for only_full in (False, True):
            sub = CR[(CR["e"] >= a0) & (CR["e"] <= a1)]
            if only_full:
                sub = sub[sub["窗完整"]]
            n = len(sub)
            for F in ("F1", "F2", "F3", "F4", "F5", "F6", "F7"):
                ev_ = sub[f"{F}_首次"] != ""
                jd = sub[f"{F}_可判次數"] > 0
                days = sub.loc[ev_, f"{F}_天"].to_numpy(float)
                FC.append({"進場段": sg, "子集": "窗完整(750日)" if only_full else "全部(截到資料尾)", "法": F, "S1事件": n,
                           "可判(窗內至少一次可判)": int(jd.sum()), "觸發": int(ev_.sum()),
                           "觸發率(÷事件)": round(float(ev_.mean()), 4) if n else None,
                           "觸發率(÷可判)": round(float(ev_.sum() / jd.sum()), 4) if jd.sum() else None,
                           "250日內觸發率(÷事件)": round(float((sub[f"{F}_天"] <= 250).sum() / n), 4) if n else None,
                           "首次觸發天數中位": float(np.median(days)) if len(days) else None,
                           "首次觸發天數p25": float(np.percentile(days, 25)) if len(days) else None,
                           "首次觸發天數p75": float(np.percentile(days, 75)) if len(days) else None,
                           "n_eff(觸發，進場月)": int(min(int(ev_.sum()), sub.loc[ev_, "進場日"].str[:7].nunique())) if n else 0})
    # 等價
    def both(a_, b_):
        x = CR[(CR[f"{a_}_首次"] != "") & (CR[f"{b_}_首次"] != "")]
        return x
    b67 = CR[CR["F6_首次"] != ""]
    EQ["F7對F6"] = {"F6觸發事件": int(len(b67)), "F7觸發事件": int((CR["F7_首次"] != "").sum()),
                   "F7⊂F6(F7觸發者F6也觸發)": bool(((CR["F7_首次"] == "") | (CR["F6_首次"] != "")).all()),
                   "F6首次＝F7首次(同日)÷F6觸發事件": round(float((b67["F6_首次"] == b67["F7_首次"]).mean()), 4) if len(b67) else None,
                   "F6全部觸發日中F4或F5成立的比例": round(float(CR["F6觸發日中F4或F5"].sum() / CR["F6觸發日數"].sum()), 4) if CR["F6觸發日數"].sum() else None}
    x45 = both("F4", "F5")
    EQ["F4對F5"] = {"F4觸發事件": int((CR["F4_首次"] != "").sum()), "F5觸發事件": int((CR["F5_首次"] != "").sum()), "兩者都觸發": int(len(x45)),
                   "兩者都觸發÷任一觸發": round(len(x45) / int(((CR["F4_首次"] != "") | (CR["F5_首次"] != "")).sum()), 4) if ((CR["F4_首次"] != "") | (CR["F5_首次"] != "")).any() else None,
                   "首次同日÷兩者都觸發": round(float((x45["F4_首次"] == x45["F5_首次"]).mean()), 4) if len(x45) else None,
                   "窗內觸發日 Jaccard(合計)": round(float(CR["F4F5同日數"].sum() / (CR["F4日數"].sum() + CR["F5日數"].sum() - CR["F4F5同日數"].sum())), 4)
                   if (CR["F4日數"].sum() + CR["F5日數"].sum()) else None}
    x13 = both("F1", "F3")
    EQ["F1對F3"] = {"F1觸發事件": int((CR["F1_首次"] != "").sum()), "F3觸發事件": int((CR["F3_首次"] != "").sum()), "兩者都觸發": int(len(x13)),
                   "首次相距≤63交易日÷兩者都觸發": round(float((np.abs(x13["F1_天"] - x13["F3_天"]) <= 63).mean()), 4) if len(x13) else None,
                   "F3先到比例": round(float((x13["F3_天"] < x13["F1_天"]).mean()), 4) if len(x13) else None}
    EQ["F2剔除"] = {"S1事件中只有半年報公司": int((CR["只有半年報"] == True).sum()), "S1事件中無季報": int(CR["只有半年報"].isna().sum()),  # noqa: E712
                   "S1事件中F2全窗不可判": int((CR["F2_可判次數"] == 0).sum())}
    log(f"[等價 丙] {json.dumps({k: EQ[k] for k in ('F7對F6', 'F4對F5', 'F1對F3', 'F2剔除')}, ensure_ascii=False)}")
    # ═════════ 輸出 ═════════
    J["甲"] = {"S1狀態": {wn: S1[S1["世界"] == wn]["st"].value_counts().to_dict() for wn in ("早年", "主")},
              "S2事件": int(len(S2)), "M事件": int(len(MM)), "S3事件": int(len(S3)), "S3另一讀法": int(len(S3alt)),
              "S2中hi24不可判": int((S2["hi24"] < 0).sum()),
              "註": "主世界 PTH 需 12 個月 ⇒ 形成月 2015-01～2015-12 無 S2／M（進場 2015-03～2016-02 空白）；早年 PTH 從 2005-02 形成"}
    J["丙"] = {"S1保留事件": int(len(CR)), "窗完整": int(CR["窗完整"].sum()), "F4 per 檔來源": per_src, "季可用日來源": qsrc,
              "必附": "利多反應完是使用者的判斷，本件只是把它寫成數字，不代表抓得到真頂；數字門檻（第 90 百分位、前 5%、5 日）為台股策略線定"}
    J["等價"] = EQ
    J["減資來源"] = {"早年": excnt}
    J["讀法"] = __doc__.split("═══ 讀法")[1]
    J["時間"] = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")
    pd.DataFrame(FA).to_csv(os.path.join(out_dir, "freq_甲.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(FB).to_csv(os.path.join(out_dir, "freq_乙.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(FBI).to_csv(os.path.join(out_dir, "freq_乙_產業.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(FC).to_csv(os.path.join(out_dir, "freq_丙.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame([{"項": k, **v} for k, v in EQ.items()]).to_csv(os.path.join(out_dir, "equiv.csv"), index=False, encoding="utf-8-sig")
    S1.to_csv(os.path.join(out_dir, "events_S1.csv.gz"), index=False, compression="gzip")
    CR.to_csv(os.path.join(out_dir, "events_丙.csv.gz"), index=False, compression="gzip")
    pd.DataFrame(UNIV).to_csv(os.path.join(out_dir, "long_univ.csv.gz"), index=False, compression="gzip")
    S3.assign(進場日=[str(CAL[e].date()) for e in S3["e"]])[["sid", "世界", "形成月底", "期別", "進場日"]].to_csv(os.path.join(out_dir, "events_S3.csv.gz"), index=False, compression="gzip")
    MM[["sid", "世界", "形成月底", "mom12_1", "跳月_進場日"]].to_csv(os.path.join(out_dir, "events_M.csv.gz"), index=False, compression="gzip")
    json.dump(J, open(os.path.join(out_dir, "freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] {time.time() - t0:.0f}s")
    open(os.path.join(out_dir, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
