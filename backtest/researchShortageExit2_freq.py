# -*- coding: utf-8 -*-
"""缺貨型確認後怎麼賣・第二輪 seq1【頻率表】（台股策略線 登錄 sha 463e9d48aed0aa96，2026-10-23 00:41；裁定 seq458 §三 發號 N_單筆 ＋3、
Bonferroni 3 格、持有 1,000 日 ⇒ 最多暫定；判定口徑「賣掉的錢記 0」，「改抱大盤」只描述；「先交頻率表（⛔ 不附報酬）」）——回測線計算子代理。
⛔ 只數事件、n_eff、各賣法判到／賣出比例與天數、E 走得完比例、D1／D2 同期、首發值／修正值比例、等價／退化；⛔ 不讀、不算、不存任何 R、d、賣後走勢（seq366）。
⛔ 美國 PPI 是私有資料（us-stock-data）：本檔輸出 ⛔ 不放原始序列、⛔ 不放逐月 PPI 值；events.csv 只存觸發位置／日期／期別標籤／布林／值來源標籤。
⛔ 不 commit、不改既有檔；researchRevTurn_freq（ensure_data、rev_table、prices、avail_pos、mnum）、researchIndMom_freq（reg_check、entry_flag、load_pit）、
   researchShortageExit_freq（第一輪：RAW8、DEDUP_M 常數；events.csv.gz 只讀對帳）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchShortageExit2_freq [--procs 3] [--sha <tw-stock-data>] [--us-sha <us-stock-data>]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchShortageExit2_freq_check
輸出 backtest/resultsShortageExit2/freq/：freq.json、counts.csv、freq_段.csv、source.csv（首發值／修正值）、sync.csv（D1／D2 同期、D3 先後）、
     equiv.csv、industry.csv、group12.csv、events.csv.gz（逐事件，⛔ 無價格、無報酬、無 PPI 值）、run.log

═══ 讀法（T 標；登錄沒寫清楚、執行者補的都在這裡；⛔ 在看任何本件數字之前寫死於 2026-10-23 18:05（台北，系統時鐘）；★＝執行者定，〔 〕內為另一讀法）═══
 T0 資料、價格、exright（seq412 open_base 版）、轉強、可用日、母體、事件、24 個月只取第一次、進場剔除、壞根截斷、下市結算、可賣開盤
    ＝ 第一輪 researchShortageExit_freq 讀法 S0～S3 原樣（同一批函式）。★ tw-stock-data 預設用第一輪頻率表同一版 443ee8ce96ec（--sha 可改）⇒ 事件應與第一輪
    events.csv.gz 逐列相同（sid、期別、A、e、母體、進場；不同 ⇒ 照報）。產業 ★ 依 A（進場前一交易日）當天 industry_pit（第一輪 S1 原式）。
    ★ 本件只做缺貨型（八業）；一般股沒有報價代理 ⇒ 只報事件數。
 T1 段（登錄 §四，依進場日 e）：探索 2006-04-01～2014-12-31｜確認 2015-01-01～（E 落在資料內）｜e ＜ 2006-04 不入段（描述）。⚠ 與第一輪（2015-12／2016-01）不同，照新登錄。
    E ＝ e ＋ 1,000（合併日曆位置；「進場後第 1,000 個交易日收盤」，判）；750、1,250 只描述。走得完 ＝ e ＋ E ≤ 資料尾。
    E_eff ＝ 第一輪 S2：(e, E] 有壞根 ⇒ 第一個壞根前一根（壞根截斷）〔另一讀法：整筆剔除〕；下市（最後有效 K 棒 ＜ E、距資料尾 ≥ 5 日）⇒ 最後有效 K 棒。
    主格（頻率表口徑）＝ 缺貨型 ∧ e 可進場 ∧ E1000 走得完；n_eff ＝ 主格事件的進場月數；＜ 24 ⇒ 還沒測。第二欄 ＝ 段內進場月依（月序 mod 12）分 12 組件數
    （⚠ 持有 1,000 日 ≈ 4 年 ⇒ 同組相鄰起點仍重疊，只是件數描述）。
 T2 報價代理（資料庫線 2026-10-23 01:34 交件；us-stock-data origin/main，git show 讀，commit 記在 freq.json）：塑膠 WPU066、鋼鐵 WPU1017、化學 WPU061、
    水泥 WPU1322、玻璃陶瓷 WPU131（⚠ 只有玻璃）、造紙 WPU091、橡膠 WPU071、油電燃氣 PPIENG；八業都有代理 ⇒ 沒有「該業 D1、D2 不判」。
    月值 ★ ＝ 該月首發值（ppi_first_release.first_value）；首發值空白 ⇒ 現行修正後值（fred_<系列>.csv，有前視）。〔另一讀法：一律用修正後值／判日當時的
    最新版本（後者沒有資料，不可行）〕比較時各月各用自己的值（首發序列）；值來源標籤：判到時用到的月值全是首發 ⇒「首發值」、全是修正 ⇒「修正值」、其他 ⇒「混合」。
    可用日 ★ ＝ 合併日曆中第一個日期 ＞ first_release_date 的交易日（BLS 美東 8:30 發布 ＝ 台北當晚，故取「之後第一個」）；判到 k ＝ 該可用日、賣出 ＝ k＋1 起第一個可賣開盤。
 T3 賣法（登錄 §三；到 E_eff 都沒觸發 ⇒ 等於不賣）：判日窗 k ∈ [e, E_eff − 1]（第一輪 S3）；賣出 s ＝ 判到後第一個可賣開盤 s ≥ k＋1（有成交、開盤有效、非開盤鎖跌停
    exright 版）且 s ≤ E_eff；判到但 s ＞ E_eff ⇒ 等於不賣（照報「判到未賣出」）。
    ★ 判日（裁定方 2026-10-23 補讀法，主讀法）：D1／D2 只在「進場後才發布的月份」的可用日判（可用日 ≥ e 才算判日）；判到時的連跌／年增轉負計算可以用到進場前的月份
      （例：進場前已連跌 2 個月，進場後發布的第一個月又跌 ⇒ 第一個判日就觸發）。〔另一讀法 D1′／D2′：計算用到的「轉負月」全部是進場後發布的月份
      ＝ D1′ 連跌的 3 個月 P−2、P−1、P 可用日都 ≥ e；D2′ 的 P−1、P 可用日都 ≥ e〕兩讀法觸發比例都報；回測線前瞻提醒用主讀法。
    D0 不賣：E_eff 收盤。
    D1 報價代理連 3 個月月增 ＜ 0：月 P 判 ＝ v(P) ＜ v(P−1) ∧ v(P−1) ＜ v(P−2) ∧ v(P−2) ＜ v(P−3)（四個月值都要有）；狀態，第一次成立即判到。
    D2 報價代理年增由 ≥0 轉 ＜0：v(P) ＜ v(P−12) ∧ v(P−1) ≥ v(P−13)（四個月值都要有）。
    D3 進場後第 625 個交易日收盤賣：★ 判到 k ＝ e ＋ 625；賣在 k 收盤，k 不是可賣收盤（無成交或收盤無值）⇒ 往後第一個有成交且收盤有效的交易日收盤〔另一讀法：隔日開盤賣〕；
       ★ 收盤賣不檢查收盤鎖跌停（資料無收盤委賣量）；k ＞ E_eff（壞根截斷、下市）⇒ 等於不賣；賣出日 ＞ E_eff ⇒ 判到未賣出。
    同根兩出場價取較低（seq373）：每法每筆只有一個賣價 ⇒ 不適用，照寫。
 T4 統計（⛔ 不算 R）：判到率、賣出率 ＝ ÷ 主格事件；天數 ＝ k − e、s − e（交易日，只計賣出者）中位、p25、p75；首個判日即判到比例；進場時已成立（e 前最後一個可用月
    已成立）比例；值來源（判到者、全部判點）；D1／D2 同期 ＝ 兩者都判到者中同一 k 比例、|k1 − k2| 中位、≤ 21／63 日比例；D1 比 D2 早比例（兩者都判到者；
    另報「任一判到、沒判到當 ∞」口徑）；D3 早於 D1／D2（都依賣出日 s，沒賣當 ∞）。
 T5 等價／退化（seq377）：兩兩「結果相同」（同一個 s 且同價別，或都不賣）≥ 90% ⇒ 近乎等價；賣出率 ＜ 10% ⇒ 近乎等於 D0；D1／D2 首個判日即判到 ≥ 90% ⇒ 近乎立即賣；
    D1、D2 都判到者同一 k ≥ 90% ⇒ D1≈D2；D3 早於 D1（或 D2）＞ 50% ⇒「D3 大多數早於 Dk」。
 T6 必附：見 NOTES。
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
import time
from collections import Counter

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchRevTurn_freq as RT             # noqa: E402
from backtest import researchIndMom_freq as IMF             # noqa: E402
from backtest import researchShortageExit_freq as SX        # noqa: E402  第一輪（只讀常數與輸出）

REG_SHA = "463e9d48aed0aa96"
OUT = "backtest/resultsShortageExit2/freq"
PIN = "443ee8ce96ec3cbdb8e33be883a0e40c9a904336"            # 第一輪頻率表同一版
US_REPO = os.path.expanduser("~/us-stock-data")
WORK = RT.WORK
DEDUP_M = SX.DEDUP_M
ES = (750, 1000, 1250)
EJ = 1000
D3N = 625
NEFF_MIN = 24
SEGS = [("早於探索(不入段)", "2004-01-01", "2006-03-31"), ("探索", "2006-04-01", "2014-12-31"), ("確認", "2015-01-01", "2099-12-31")]
SEGJ = ["探索", "確認"]
RAW8 = SX.RAW8
PPI_MAP = {"塑膠工業": "WPU066", "鋼鐵工業": "WPU1017", "化學工業": "WPU061", "水泥工業": "WPU1322", "玻璃陶瓷": "WPU131",
           "造紙工業": "WPU091", "橡膠工業": "WPU071", "油電燃氣業": "PPIENG"}
RULES = ["D1", "D2", "D3"]
ALT = ["D1′", "D2′"]
RNAME = {"D0": "不賣", "D1": "報價代理連3個月月增<0", "D2": "報價代理年增由≥0轉<0", "D3": "進場後第625個交易日收盤賣",
         "D1′": "D1 另一讀法（連跌3個月全為進場後發布）", "D2′": "D2 另一讀法（P−1、P 全為進場後發布）"}
BIG = 10 ** 9
NOTES = ["頻率表、未算任何報酬（seq366）；判定口徑「賣掉的錢記 0」，「改抱大盤」只描述",
         "報價代理是美國生產者物價（FRED 商品別 PPI、未季調），不是亞洲報價、也不是個股產品價；玻璃陶瓷只有玻璃",
         "PPIENG 以外七支 2015-03 前沒有首發值 ⇒ 用現行修正後值（有前視）；探索段幾乎全是修正值，比例見 source.csv",
         "PPI 可用日 ＝ ALFRED 收錄日之後第一個交易日（≥ BLS 實際發布日，偏保守）；2015-03 前七支借 PPIACO 首發日",
         "缺貨型以產業別代理（八業），不是逐檔判定的缺貨；只看這一筆",
         "持有 1,000 日、月與月不獨立 ⇒ 月分群 CI 偏窄 ⇒ 結論最多「暫定」；任一段 n_eff ＜ 24 ⇒ 還沒測；第二欄 12 組仍重疊",
         "2015～2018 下市 58 家月營收補不回（存活者偏差，seq406／411）；早年上櫃 2007-07 前無價",
         "價格面板 ＝ rerun17 H2D（edc6f，資料尾 2026-09-24）；月營收、產業、exright ＝ tw-stock-data（版本見 origin/main 欄）",
         "同根兩出場價取較低（seq373）：每法每筆只有一個賣價 ⇒ 不適用"]
LOG = RT.LOG
log = RT.log


def segof(d):
    s = str(pd.Timestamp(d).date())
    for nm, a, b in SEGS:
        if a <= s <= b:
            return nm
    return "其他"


def us_git(*a):
    return subprocess.run(["git", "-C", US_REPO] + list(a), capture_output=True, check=True).stdout


def lab(srcs):
    s = set(srcs)
    return "首發值" if s == {"首"} else ("修正值" if s == {"修"} else "混合")


def load_ppi(us_sha, CAL):
    """T2：每業一條月序列（首發值優先、否則修正後值）、值來源、可用日位置；⛔ 值只留在記憶體。"""
    PF = pd.read_csv(io.BytesIO(us_git("show", f"{us_sha}:data/macro/ppi_first_release.csv")), dtype=str, keep_default_na=False)
    S = {}; info = {}
    for ind, ser in PPI_MAP.items():
        raw = pd.read_csv(io.BytesIO(us_git("show", f"{us_sha}:data/macro/fred_{ser}.csv")), dtype=str, keep_default_na=False)
        rv = dict(zip(raw["date"].str[:7], pd.to_numeric(raw["value"], errors="coerce")))
        g = PF[PF["series"] == ser].sort_values("period").reset_index(drop=True)
        m0 = RT.mnum(g["period"].iloc[0]); n = len(g)
        if [RT.mnum(p) for p in g["period"]] != list(range(m0, m0 + n)):
            raise SystemExit(f"⛔ {ser} 首發表期別不連續")
        frd = pd.to_datetime(g["first_release_date"])
        if frd.isna().any() or not frd.is_monotonic_increasing:
            raise SystemExit(f"⛔ {ser} 首發日缺或不遞增")
        fv = pd.to_numeric(g["first_value"].replace("", np.nan), errors="coerce").to_numpy(float)
        rvv = np.array([rv.get(p, np.nan) for p in g["period"]], float)
        v = np.where(np.isfinite(fv), fv, rvv)
        src = np.where(np.isfinite(fv), "首", np.where(np.isfinite(rvv), "修", "")).astype(object)
        av = CAL.searchsorted(frd.to_numpy(), side="right").astype(np.int64)      # 第一個日期 ＞ 首發日
        # 條件（狀態）與值來源
        c1 = np.zeros(n, bool); c2 = np.zeros(n, bool); l1 = np.empty(n, object); l2 = np.empty(n, object)
        for j in range(n):
            if j >= 3 and np.isfinite(v[j - 3:j + 1]).all():
                c1[j] = bool(v[j] < v[j - 1] and v[j - 1] < v[j - 2] and v[j - 2] < v[j - 3])
                l1[j] = lab(src[j - 3:j + 1])
            else:
                l1[j] = ""
            if j >= 13 and np.isfinite(v[[j, j - 1, j - 12, j - 13]]).all():
                c2[j] = bool(v[j] < v[j - 12] and v[j - 1] >= v[j - 13])
                l2[j] = lab(src[[j, j - 1, j - 12, j - 13]])
            else:
                l2[j] = ""
        S[ind] = {"ser": ser, "m0": m0, "per": list(g["period"]), "av": av, "c1": c1, "c2": c2, "l1": l1, "l2": l2,
                  "ok1": np.array([x != "" for x in l1]), "ok2": np.array([x != "" for x in l2])}
        fvp = g.loc[np.isfinite(fv), "period"]
        info[ind] = {"系列": ser, "期別": f"{g['period'].iloc[0]}～{g['period'].iloc[-1]}", "首發值起": (fvp.iloc[0] if len(fvp) else None),
                     "首發值月數": int(np.isfinite(fv).sum()), "修正值補月數": int(((~np.isfinite(fv)) & np.isfinite(rvv)).sum()),
                     "兩者皆無月數": int(((~np.isfinite(fv)) & ~np.isfinite(rvv)).sum()), "首發日來源": dict(Counter(g["date_source"]))}
    return S, info


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--sha", default=PIN, help="tw-stock-data 版本（預設第一輪頻率表同一版）"); ap.add_argument("--us-sha", default="origin/main")
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    t0 = time.time()
    out = a.out
    os.makedirs(out, exist_ok=True)
    reg = IMF.reg_check(REG_SHA); log(f"[登錄] {reg}（sha {REG_SHA} 已驗）")
    sha, DN, MD = RT.ensure_data(a.sha); log(f"[資料] tw-stock-data {sha}｜{DN}")
    us_sha = us_git("rev-parse", a.us_sha).decode().strip()
    if subprocess.run(["git", "-C", US_REPO, "merge-base", "--is-ancestor", "bcff4a31e", us_sha]).returncode != 0:
        raise SystemExit("⛔ us-stock-data 版本早於資料庫線交件 bcff4a31e")
    log(f"[PPI] us-stock-data {us_sha}")
    PX = RT.prices(sha, DN, a.procs)
    CAL, SIDS, ix = PX["CAL"], PX["SIDS"], PX["ix"]
    NC = len(CAL); CEND = NC - 1
    C, BAD, TRD, O, DNL, LASTV = PX["C"], PX["BAD"], PX["TRD"], PX["O"], PX["DNL"], PX["LASTV"]
    PP, pinfo = load_ppi(us_sha, CAL)
    log(f"[PPI] {pinfo}")
    RV, rdiag = RT.rev_table(MD, SIDS, a.procs, tag="all")
    pit = IMF.load_pit(DN)
    periods = sorted(RV["period"].unique())
    APOS = RT.avail_pos(CAL, periods)
    RV["i"] = RV["sid"].map(ix).fillna(-1).astype(int)
    RV["A"] = RV["period"].map(APOS).astype(int)
    RV["起點"] = RV["up"] & ~RV["up_prev"]
    G = PX["G"]
    # ── 事件（T0 ＝ 第一輪 S1）
    ST = RV[RV["起點"]].sort_values(["sid", "period"])
    reasons = Counter(); last_kept = {}; ev = []
    for r in ST.itertuples(index=False):
        if r.i < 0:
            reasons["非面板"] += 1; continue
        if r.A > CEND or r.A < 1:
            reasons["可用日超出日曆"] += 1; continue
        if not G[r.i, r.A - 1]:
            reasons["閘外（判日 A−1）"] += 1; continue
        lk = last_kept.get(r.sid)
        if lk is not None and RT.mnum(r.period) - RT.mnum(lk) < DEDUP_M:
            reasons["24個月內非第一次"] += 1; continue
        last_kept[r.sid] = r.period
        ev.append((r.sid, r.i, r.period, r.A))
    log(f"[事件] 起點 {len(ST)} ⇒ 過閘去重 {len(ev)}｜{dict(reasons)}")
    nxt_memo = {}; cls_memo = {}

    def nxt_sell(i):
        if i not in nxt_memo:
            ok = TRD[i] & np.isfinite(C[i]) & np.isfinite(O[i]) & ~DNL[i]
            idx = np.where(ok, np.arange(NC), BIG)
            nxt_memo[i] = np.minimum.accumulate(idx[::-1])[::-1]
        return nxt_memo[i]

    def nxt_close(i):
        if i not in cls_memo:
            ok = TRD[i] & np.isfinite(C[i])
            idx = np.where(ok, np.arange(NC), BIG)
            cls_memo[i] = np.minimum.accumulate(idx[::-1])[::-1]
        return cls_memo[i]
    rows = []
    for sid, i, P, A_ in ev:
        e = A_ + 1
        ind, isrc = pit.at(sid, CAL[A_]); ind = ind or ""
        pop = "缺貨型" if ind in RAW8 else ("一般股" if ind else "無類別")
        fl_ = IMF.entry_flag(PX, i, A_, e) if e <= CEND else "e超出資料尾"
        row = {"sid": sid, "期別": P, "A": str(CAL[A_].date()), "e": (str(CAL[e].date()) if e <= CEND else ""), "段": (segof(CAL[e]) if e <= CEND else "其他"),
               "進場月": (f"{CAL[e].year}-{CAL[e].month:02d}" if e <= CEND else ""), "產業": ind, "產業來源": isrc, "母體": pop, "進場": fl_,
               "代理序列": PPI_MAP.get(ind, "")}
        for E in ES:
            row[f"E{E}走得完"] = bool(e <= CEND and e + E <= CEND)
        if fl_ != "保留" or pop != "缺貨型":
            rows.append(row); continue
        W = min(e + max(ES), CEND)
        bb = np.flatnonzero(BAD[i, e + 1:W + 1]); kb = e + 1 + int(bb[0]) if len(bb) else BIG
        lastv = int(LASTV[i]); delist = (CEND - lastv) >= 5
        effs = {}
        for E in ES:
            x = e + E; st = "完整"
            if x > CEND:
                effs[E] = (None, "走不完"); continue
            if kb <= x:
                x = kb - 1; st = "壞根截斷"
            if delist and lastv < x:
                x = lastv; st = "下市結算"
            effs[E] = (x, st)
            row[f"E{E}狀態"] = st
            row[f"E{E}_eff偏移"] = x - e
        Wx = W
        if kb <= Wx:
            Wx = kb - 1
        if delist and lastv < Wx:
            Wx = lastv
        kmax = Wx - 1
        ns = nxt_sell(i); nc = nxt_close(i)
        S = PP[ind]; av = S["av"]
        j0 = int(np.searchsorted(av, e, "left")); j1 = int(np.searchsorted(av, kmax, "right"))   # 判點：e ≤ av ≤ kmax
        js = range(j0, j1)
        trig = {}; lab_ = {}; per_ = {}
        for c, cc, ll, okk in (("D1", S["c1"], S["l1"], S["ok1"]), ("D2", S["c2"], S["l2"], S["ok2"])):
            k = -1; lb = ""; pr = ""
            for j in js:
                if cc[j]:
                    k = int(av[j]); lb = ll[j]; pr = S["per"][j]; break
            trig[c] = k; lab_[c] = lb; per_[c] = pr
            row[f"{c}判點"] = len(js); row[f"{c}可判點"] = int(okk[j0:j1].sum())
            for nm in ("首發值", "修正值", "混合"):
                row[f"{c}判點_{nm}"] = int(sum(1 for j in js if ll[j] == nm))
            row[f"{c}進場時已成立"] = bool(j0 >= 1 and cc[j0 - 1])
            row[f"{c}首判即判到"] = bool(len(js) and cc[j0])
        # 另一讀法：轉負月全部是進場後發布
        for c, cc, back in (("D1′", S["c1"], 2), ("D2′", S["c2"], 1)):
            k = -1; pr = ""
            for j in js:
                if cc[j] and j - back >= 0 and av[j - back] >= e:
                    k = int(av[j]); pr = S["per"][j]; break
            trig[c] = k; per_[c] = pr; lab_[c] = (S["l1"] if c == "D1′" else S["l2"])[S["per"].index(pr)] if pr else ""
        row["首個判日偏移"] = (int(av[j0]) - e) if len(js) else None
        row["判點數"] = len(js)
        out_ = {}
        for c in RULES + ALT:
            if c == "D3":
                k = e + D3N
                s = int(nc[k]) if k <= CEND else BIG
                s = -1 if s >= BIG else s
                kind = "收"
            else:
                k = trig[c]
                s = int(ns[k + 1]) if (k >= 0 and k + 1 <= CEND) else -1
                s = -1 if s >= BIG else s
                kind = "開"
            row[f"{c}_k偏移"] = (k - e) if k >= 0 else None
            row[f"{c}_s偏移"] = (s - e) if s >= 0 else None
            row[f"{c}_價別"] = kind
            if c in ("D1", "D2", "D1′", "D2′"):
                row[f"{c}判到期"] = per_[c]; row[f"{c}值來源"] = lab_[c]
            for E in ES:
                x, st = effs[E]
                if x is None:
                    row[f"{c}_E{E}"] = None; continue
                lim = x if c == "D3" else x - 1                       # D3 收盤賣：k ≤ E_eff；D1／D2：k ≤ E_eff − 1
                if k >= 0 and k <= lim:
                    row[f"{c}_E{E}"] = "賣出" if (0 <= s <= x) else "判到未賣出"
                else:
                    row[f"{c}_E{E}"] = "不賣"
        rows.append(row)
    EV = pd.DataFrame(rows)
    log(f"[逐事件] {len(EV)}｜缺貨型可進場 {int(((EV['進場'] == '保留') & (EV['母體'] == '缺貨型')).sum())}｜{time.time() - t0:.0f}s")
    # ── 與第一輪事件對帳（同版才比）
    K0 = {"比對": False}
    if sha == PIN:
        E1 = pd.read_csv(os.path.join(SX.OUT, "events.csv.gz"), dtype={"sid": str, "期別": str}, keep_default_na=False)
        cols = ["sid", "期別", "A", "e", "母體", "進場", "產業"]
        a1 = set(map(tuple, E1[cols].astype(str).to_numpy())); a2 = set(map(tuple, EV[cols].astype(str).to_numpy()))
        K0 = {"比對": True, "第一輪": len(a1), "本件": len(a2), "只在第一輪": len(a1 - a2), "只在本件": len(a2 - a1), "相同": a1 == a2}
    log(f"[K0 對第一輪事件] {K0}")
    # ── 統計
    CNT = []; FR = []; SRC = []; SY = []; EQ = []; IND = []; G12 = []
    for sg in [s[0] for s in SEGS]:
        for pn in ("缺貨型", "一般股"):
            d = EV[(EV["段"] == sg) & (EV["母體"] == pn)]
            ok = d[d["進場"] == "保留"]
            row = {"段": sg, "母體": pn, "事件(過閘去重)": len(d), "e可進場": len(ok), "進場剔除": dict(Counter(d.loc[d["進場"] != "保留", "進場"]))}
            if pn == "一般股":
                row["備註"] = "沒有報價代理 ⇒ 只報事件數"; CNT.append(row); continue
            m = ok[ok[f"E{EJ}走得完"] == True]  # noqa: E712
            ne = int(m["進場月"].nunique())
            for E in ES:
                mm = ok[ok[f"E{E}走得完"] == True]  # noqa: E712
                row[f"E{E}走得完"] = len(mm); row[f"E{E}走得完比例"] = (len(mm) / len(ok) if len(ok) else np.nan)
                row[f"E{E}壞根截斷"] = int((mm.get(f"E{E}狀態") == "壞根截斷").sum()) if len(mm) else 0
                row[f"E{E}下市結算"] = int((mm.get(f"E{E}狀態") == "下市結算").sum()) if len(mm) else 0
            row.update({"主格(E1000走得完)": len(m), "n_eff(主格進場月數)": ne, "n_eff≥24": ne >= NEFF_MIN,
                        "主格進場日": (f"{m['e'].min()}～{m['e'].max()}" if len(m) else "")})
            CNT.append(row)
            if not len(m):
                continue
            for E in ES:
                mm = ok[ok[f"E{E}走得完"] == True]  # noqa: E712
                if not len(mm):
                    continue
                for c in RULES + ALT:
                    col = mm[f"{c}_E{E}"]
                    sold = mm[col == "賣出"]
                    kk = sold[f"{c}_k偏移"]; ss = sold[f"{c}_s偏移"]
                    FR.append({"段": sg, "E": E, "賣法": c, "名稱": RNAME[c], "身分": ("判定" if (E == EJ and c in RULES) else "描述"), "事件": len(mm),
                               "月數": int(mm["進場月"].nunique()), "判到": int((col != "不賣").sum()), "賣出": len(sold),
                               "判到未賣出": int((col == "判到未賣出").sum()), "判到率": float((col != "不賣").mean()), "賣出率": float((col == "賣出").mean()),
                               "判到天數中位(k−e)": (float(kk.median()) if len(sold) else np.nan), "判到天數p25": (float(kk.quantile(.25)) if len(sold) else np.nan),
                               "判到天數p75": (float(kk.quantile(.75)) if len(sold) else np.nan),
                               "賣出天數中位(s−e)": (float(ss.median()) if len(sold) else np.nan), "賣出天數p25": (float(ss.quantile(.25)) if len(sold) else np.nan),
                               "賣出天數p75": (float(ss.quantile(.75)) if len(sold) else np.nan),
                               "賣出天數≤250": (int((ss <= 250).sum()) if len(sold) else 0), "賣出天數251～625": (int(((ss > 250) & (ss <= 625)).sum()) if len(sold) else 0),
                               "賣出天數＞625": (int((ss > 625).sum()) if len(sold) else 0)})
            # 值來源（E1000 主格）
            for c in ("D1", "D2", "D1′", "D2′"):
                hit = m[m[f"{c}_E{EJ}"] != "不賣"]
                r_ = {"段": sg, "賣法": c, "判到": len(hit)}
                for nm in ("首發值", "修正值", "混合"):
                    r_[f"判到_{nm}"] = int((hit[f"{c}值來源"] == nm).sum())
                    r_[f"判到_{nm}比例"] = (float((hit[f"{c}值來源"] == nm).mean()) if len(hit) else np.nan)
                if c in ("D1", "D2"):
                    tot = int(m[f"{c}判點"].sum())
                    r_["全部判點"] = tot; r_["可判點"] = int(m[f"{c}可判點"].sum())
                    for nm in ("首發值", "修正值", "混合"):
                        r_[f"判點_{nm}比例"] = (float(m[f"{c}判點_{nm}"].sum() / tot) if tot else np.nan)
                    r_["進場時已成立比例"] = float(m[f"{c}進場時已成立"].mean())
                    r_["首個判日即判到比例"] = float(m[f"{c}首判即判到"].mean())
                SRC.append(r_)
            # 同期、先後（E1000 主格）
            def kk_(c, mm_=m):
                v = np.where(mm_[f"{c}_E{EJ}"] != "不賣", mm_[f"{c}_k偏移"].fillna(-1).to_numpy(float), np.inf)
                return v

            def ss_(c, mm_=m):
                return np.where(mm_[f"{c}_E{EJ}"] == "賣出", mm_[f"{c}_s偏移"].fillna(-1).to_numpy(float), np.inf)
            for a_, b_ in (("D1", "D2"), ("D1′", "D2′")):
                k1, k2 = kk_(a_), kk_(b_)
                both = np.isfinite(k1) & np.isfinite(k2); eith = np.isfinite(k1) | np.isfinite(k2)
                dk = np.abs(k1[both] - k2[both])
                SY.append({"段": sg, "項": f"{a_}、{b_}", "主格": len(m), f"{a_}判到": int(np.isfinite(k1).sum()), f"{b_}判到": int(np.isfinite(k2).sum()),
                           "兩者都判到": int(both.sum()), "兩者都判到比例(÷主格)": float(both.mean()), "只有一個判到": int((eith & ~both).sum()),
                           "都沒判到": int((~eith).sum()),
                           "都判到中同一k": (float((dk == 0).mean()) if both.any() else np.nan),
                           "都判到中|Δk|中位": (float(np.median(dk)) if both.any() else np.nan),
                           "都判到中|Δk|≤21": (float((dk <= 21).mean()) if both.any() else np.nan),
                           "都判到中|Δk|≤63": (float((dk <= 63).mean()) if both.any() else np.nan),
                           f"都判到中{a_}較早": (float((k1[both] < k2[both]).mean()) if both.any() else np.nan),
                           f"都判到中{b_}較早": (float((k2[both] < k1[both]).mean()) if both.any() else np.nan),
                           f"任一判到中{a_}較早(沒判到當∞)": (float((k1[eith] < k2[eith]).mean()) if eith.any() else np.nan),
                           f"任一判到中{b_}較早(沒判到當∞)": (float((k2[eith] < k1[eith]).mean()) if eith.any() else np.nan),
                           "任一判到中同日": (float((k1[eith] == k2[eith]).mean()) if eith.any() else np.nan)})
            s1, s2, s3 = ss_("D1"), ss_("D2"), ss_("D3")
            for nm, sx in (("D1", s1), ("D2", s2)):
                any_ = np.isfinite(s3) | np.isfinite(sx)
                SY.append({"段": sg, "項": f"D3 對 {nm}（依賣出日 s，沒賣當 ∞）", "主格": len(m),
                           "D3較早(÷主格)": float((s3 < sx).mean()), f"{nm}較早(÷主格)": float((sx < s3).mean()),
                           "同日或都不賣(÷主格)": float((sx == s3).mean()),
                           "任一賣出中D3較早": (float((s3[any_] < sx[any_]).mean()) if any_.any() else np.nan)})
            # 等價／退化（E1000 主格）
            outc = {"D0": np.full(len(m), "不賣", object)}
            for c in RULES + ALT:
                outc[c] = np.where(m[f"{c}_E{EJ}"] == "賣出", m[f"{c}_價別"].astype(str) + m[f"{c}_s偏移"].fillna(-1).astype(int).astype(str), "不賣")
            keys = ["D0"] + RULES + ALT
            for x_ in range(len(keys)):
                for y_ in range(x_ + 1, len(keys)):
                    same = float((outc[keys[x_]] == outc[keys[y_]]).mean())
                    EQ.append({"段": sg, "項": f"{keys[x_]} vs {keys[y_]} 結果相同", "值": same, "旗標": ("近乎等價" if same >= 0.90 else "")})
            for c in RULES + ALT:
                sr = float((m[f"{c}_E{EJ}"] == "賣出").mean())
                EQ.append({"段": sg, "項": f"{c} 賣出率", "值": sr, "旗標": ("近乎等於不賣(＜10%)" if sr < 0.10 else "")})
            for c in ("D1", "D2"):
                imm = float(m[f"{c}首判即判到"].mean())
                EQ.append({"段": sg, "項": f"{c} 首個判日即判到", "值": imm, "旗標": ("近乎立即賣(≥90%)" if imm >= 0.90 else "")})
            sy = [r for r in SY if r["段"] == sg and r["項"] == "D1、D2"][0]
            v12 = sy["都判到中同一k"]
            EQ.append({"段": sg, "項": "D1、D2 都判到中同一 k", "值": v12, "旗標": ("D1≈D2(≥90%)" if (np.isfinite(v12) and v12 >= 0.90) else "")})
            for nm, sx in (("D1", s1), ("D2", s2)):
                v3 = float((s3 < sx).mean())
                EQ.append({"段": sg, "項": f"D3 早於 {nm}（÷主格）", "值": v3, "旗標": ("D3 大多數早於" + nm if v3 > 0.5 else "")})
            # 分產業（E1000 主格；事件數另含全部可進場）
            for ind_, dd in ok.groupby("產業"):
                mm = dd[dd[f"E{EJ}走得完"] == True]  # noqa: E712
                r_ = {"段": sg, "產業": ind_, "代理序列": PPI_MAP.get(ind_, ""), "有報價代理": ind_ in PPI_MAP, "e可進場": len(dd), "主格": len(mm),
                      "主格月數": int(mm["進場月"].nunique())}
                for c in RULES + ALT:
                    r_[f"{c}判到率"] = (float((mm[f"{c}_E{EJ}"] != "不賣").mean()) if len(mm) else np.nan)
                    r_[f"{c}賣出率"] = (float((mm[f"{c}_E{EJ}"] == "賣出").mean()) if len(mm) else np.nan)
                IND.append(r_)
            # 第二欄（件數）
            if sg in SEGJ:
                lo, hi = [(s[1], s[2]) for s in SEGS if s[0] == sg][0]
                m0 = RT.mnum(lo[:7])
                for g_, dd in m.groupby(m["進場月"].map(lambda s: (RT.mnum(s) - m0) % 12)):
                    G12.append({"段": sg, "組(進場月序mod12)": int(g_), "件數": len(dd), "月數": int(dd["進場月"].nunique())})
    CNT = pd.DataFrame(CNT); FR = pd.DataFrame(FR); SRC = pd.DataFrame(SRC); SY = pd.DataFrame(SY); EQ = pd.DataFrame(EQ); IND = pd.DataFrame(IND)
    G12 = pd.DataFrame(G12)
    # ⛔ 私有資料檢查：輸出不得含 PPI 值欄
    bad_cols = [c for c in EV.columns if any(t in c for t in ("PPI", "ppi"))]
    for c in EV.columns:                                   # 數值欄只能是整數（位置、天數、件數）或布林
        if EV[c].dtype.kind == "f" and not np.all(np.isnan(EV[c]) | (EV[c] == np.round(EV[c]))):
            bad_cols.append(c)
    if bad_cols:
        raise SystemExit(f"⛔ events 有疑似 PPI 值欄 {bad_cols}")
    EV.to_csv(os.path.join(out, "events.csv.gz"), index=False, encoding="utf-8-sig", compression="gzip")
    CNT.to_csv(os.path.join(out, "counts.csv"), index=False, encoding="utf-8-sig")
    FR.to_csv(os.path.join(out, "freq_段.csv"), index=False, encoding="utf-8-sig")
    SRC.to_csv(os.path.join(out, "source.csv"), index=False, encoding="utf-8-sig")
    SY.to_csv(os.path.join(out, "sync.csv"), index=False, encoding="utf-8-sig")
    EQ.to_csv(os.path.join(out, "equiv.csv"), index=False, encoding="utf-8-sig")
    IND.to_csv(os.path.join(out, "industry.csv"), index=False, encoding="utf-8-sig")
    G12.to_csv(os.path.join(out, "group12.csv"), index=False, encoding="utf-8-sig")
    J = {"性質": "缺貨型確認後怎麼賣・第二輪 seq1 頻率表（⛔ 未算任何報酬）", "登錄": f"台股策略線 seq1 sha {REG_SHA}", "裁定": "seq458 §三（N_單筆 ＋3、Bonferroni 3 格）",
         "origin/main": sha, "us-stock-data": us_sha, "價格面板": {"主": PX["main_data"], "早年": PX["early_data"]}, "資料尾": str(CAL[-1].date()),
         "接縫": PX["seam"], "exright": PX["info"], "月營收": rdiag, "報價代理": pinfo,
         "起點": {"全部": int(len(ST)), "剔除": dict(reasons), "過閘去重事件": int(len(ev))}, "K0對第一輪事件": K0,
         "counts": CNT.to_dict("records"), "必附": NOTES, "讀法": __doc__.split("═══ 讀法")[1], "秒": round(time.time() - t0)}
    json.dump(J, open(os.path.join(out, "freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=RT.jdef)
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    log(f"[完成] {out}｜{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
