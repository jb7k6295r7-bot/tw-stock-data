# -*- coding: utf-8 -*-
"""缺貨型持股「確認後」怎麼賣 seq1【頻率表・乾跑】（台股策略線 登錄 sha 2b3c853a8290be22，2026-10-22 16:41；裁定 seq447 §一 發號 N_單筆 ＋7、
Bonferroni 7 格、250 日重疊 ⇒ 最多暫定、n_eff ＜ 24 標還沒測；「先交頻率表（⛔ 不附報酬），我核過才跑報酬」）——回測線計算子代理。
⛔ 只數事件、n_eff、各賣法判到／賣出的比例與天數、評估點走得完比例、可判比例、等價／退化；⛔ 不讀、不算、不存任何 R、d、賣後走勢（seq366）。
   價格（還原收盤）只用來判 C4／C5 的條件本身（只存觸發位置與布林、⛔ 不存價格數值）；進場後其餘只用有效 K 棒／壞根／下市／可賣旗標。
⛔ 不 commit、不改既有檔；researchRevTurn_freq（本件同日新檔：ensure_data、rev_table、prices、gm_table、filing_pos、avail_pos ＝ 轉強與價格共用）、
   researchIndMom_freq（reg_check、entry_flag、load_pit）、researchBigRun3 面板（月底官方本益比，⛔ 只讀）、researchPTH_freq（month_ends）、researchLongPool ⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchShortageExit_freq [--procs 3] [--limit N（乾跑，輸出 ~/rtfwork/dry_sx）]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchShortageExit_freq_check [--dry]
輸出 backtest/resultsShortageExit/freq/：freq.json、counts.csv（段×母體 事件數、n_eff）、freq_段.csv（段×母體×E×賣法：判到率、賣出率、天數）、
     judge.csv（可判比例）、c1_month.csv（C1 分月）、equiv.csv（等價／退化）、group12.csv（第二欄分組件數）、events.csv.gz（逐事件，⛔ 無價格與報酬）、run.log

═══ 讀法（S 標；登錄沒寫清楚、執行者補的都在這裡；⛔ 在看任何本件數字之前寫死於 2026-10-22（台北）；★＝執行者定，〔 〕內為另一讀法）═══
 S0 資料、價格、exright、轉強、可用日 ＝ researchRevTurn_freq 讀法 V0～V3 原樣（同一批函式；轉強 ＝ 大漲觀察月報 bigrun_monthly.rev_metrics，⛔ 不寫第二份）。
 S1 母體（登錄 §二）：事件 ＝ 轉強起點 ∧ 面板四碼普通股 ∧ 判日 A−1 過 500 張閘（G[A−1]）；★ 同檔 24 個月內只取第一次（過閘起點依期別、與上一個取用期別相差 ＜ 24 個月不取）。
    進場 e ＝ A 下一交易日開盤；進場剔除 ＝ researchIndMom_freq.entry_flag 原式（壞根(A,e] → e無成交 → e開盤鎖漲停 exright 版）。
    母體別 ★ 依 A 當天 PRE.PIT industry_pit：缺貨型 ＝ 塑膠工業、化學工業、鋼鐵工業、水泥工業、玻璃陶瓷、造紙工業、橡膠工業、油電燃氣業（字面；2007 前舊類別
    「化學生技醫療」不算，件數照報）；一般股 ＝ 其他有類別者；無類別 ⇒ 兩邊都不算（照報）。
    族群（只描述）★ ＝ 台股策略線「十條供應鏈」（2026-10-20，_備份/十條供應鏈_含數字_20261020.md；現在的名單、不是當時的、事後名單）：
      被動元件 ＝ ⑨ ①～⑥（不含 ⑦ 通路）；記憶體 ＝ ② ① 原廠／利基型 ＋ ② 模組（不含控制 IC、封測、設備）；PCB 材料 ＝ ⑧ ① 玻纖紗布 ＋ ② 銅箔 ＋ ④ CCL；與產業無關。
 S2 段（登錄 §五，依進場日 e）：探索 2006-04-01～2015-12-31｜確認 2016-01-01～（E 落在資料內）｜e ＜ 2006-04 不入段。
    評估點 E ＝ e ＋ 250（合併日曆位置；★「進場後第 250 個交易日收盤」）；120、500 只描述。走得完 ＝ E ≤ 資料尾（2026-09-24）。
    ★ (e, E] 有壞根 ⇒ E_eff ＝ 第一個壞根前一根（標「壞根截斷」）〔另一讀法：整筆剔除〕；下市（最後有效 K 棒 ＜ E、距資料尾 ≥ 5 日）⇒ E_eff ＝ 最後有效 K 棒（標「下市結算」）。
    主格（頻率表口徑）＝ e 可進場 ∧ E 走得完；n_eff ＝ 主格事件的進場月數；＜ 24 ⇒ 還沒測。第二欄 ＝ 段內進場月依（月序 mod 12）分 12 組的件數。
 S3 賣法（登錄 §三；觸發 ＝ 判到；賣出 ＝ 判到後第一個可賣開盤 s ≥ k＋1（有成交、開盤有效、非開盤鎖跌停 exright 版）且 s ≤ E_eff；判到但 s ＞ E_eff ⇒ 等於不賣，照報）：
    判日窗 ★ ＝ k ∈ [e, E_eff − 1]。月營收判日 ＝ 期別 Q ＞ P（P ＝ 事件期別）的可用日 A_Q（V3 同式；★ A_Q 不必是有效 K 棒）；該檔該期沒值 ⇒ 該月不判。
    C1 營收月增 ≤ 0 連 2 個月 ＝ rev_metrics(Q).flag_mom2（＝ 月報 F①，同列上月營收）。
    C2 單月年增由 ≥0 轉 ＜0 ＝ yoy(Q) ＜ 0 ∧ yoy(Q−1) ≥ 0（兩期都要有值；yoy ＝ rev_metrics 同列去年當月）。
    C3 轉弱 ＝ accel(Q) ≤ −0.05（rev_metrics accel；狀態，第一次成立即判到）。
    C4 還原收盤距近一年最高 ≤ −30%：判日 ＝ {e} ∪ {A_Q}（★ 該日須為有效 K 棒，否則該次不判）；近一年 ＝ [d−249, d] 的有效 K 棒，★ 窗內有壞根 ⇒ 從最後一個壞根那根起算
       （researchTopSell_freq 距一年高點同式）；e 當天成立 ⇒ 記「進場時已成立」。
    C5 從進場日起最高收盤回落 30%：k 有效 K 棒、c[k] ≤ 0.70 × max(c[e..k])（★ 含 e 收盤）。
    C6 循環高峰：判日 ＝ 合併日曆月底（researchPTH_freq.month_ends ＝ BigRun3 面板 MEp）∈ 判日窗；
       ① 近 4 季 EPS ＝ 最新 main fin_hist eps_ytd 差分成單季（researchLongPool.single）4 季和；選季 ＝ 上傳日（AI1 優先、否則最早文件）＜ 月底日期的最新一季；
          ★「創 20 季新高」＝ 該季與前 19 季共 20 個近 4 季 EPS 全可算、且該季 ≥ 20 個中最大；
       ② 本益比 ＝ BigRun3 面板月底官方 per（快照 dbfb96；虧損 per 空白）；★ 自身 60 個月 ＝ 第 k−59～k 個月底有值者 ≥ 36 個才可算，第 20 百分位 ＝ np.percentile(…, 20)（線性內插）；
       成立 ＝ ① ∧ ② per ≤ 第 20 百分位 ∧ 近 4 季 EPS ＞ 0；虧損、本益比空白 ⇒ 不觸發。可判（照報）＝ per 有值 ∧ 60 月窗 ≥ 36 ∧ 20 季全可算。
    C7 最近一季毛利率年增由 ≥0 轉 ＜0：判日 ＝ 季 q 的可判位置（上傳日次一交易日；researchRevTurn_freq.filing_pos）∈ 判日窗；
       ΔGM(q) ＝ GM(q) − GM(q−4)（單季毛利率：fs_xbrl ⇒ 缺 ⇒ fin_hist，researchRevTurn_freq.gm_table）；成立 ＝ ΔGM(q) ＜ 0 ∧ ΔGM(q−1) ≥ 0（四季都要有值）。
    同根兩出場價取較低（seq373）：每法每筆只有一個賣價（判到隔日開盤）⇒ 不適用，照寫。
 S4 統計（⛔ 不算 R）：判到率、賣出率 ＝ ÷ 主格事件；天數 ＝ k − e、s − e（交易日，只計賣出者）中位；首個判日即判到比例；C4 進場時已成立比例；
    C1 分月 ＝ 判日窗內所有月營收判點依期別月份：條件成立率、第一次判到的月份分布（〈八十八〉）。
 S5 等價／退化（seq377、登錄 §七）：兩兩「結果相同」（同一個 s，或都不賣）比例 ≥ 90% ⇒ 近乎等價；賣出率 ＜ 10% ⇒ 近乎等於 C0（不賣）；
    首個判日即判到 ≥ 90% ⇒ 近乎立即賣；C4 與 C5 同日比例、C4 先於 C5 比例；C2 與 C3 同期判到比例；C6 可判（事件至少一個月底可判）＜ 30% ⇒「C6 多數事件判不了」。
 S6 必附：見 NOTES。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import pickle
import subprocess
import sys
import time
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchRevTurn_freq as RT             # noqa: E402  共用（同日新檔）
from backtest import researchIndMom_freq as IMF             # noqa: E402  reg_check、entry_flag、load_pit
from backtest import researchPTH_freq as PF                 # noqa: E402  month_ends
from backtest import researchLongPool as LP                 # noqa: E402  single、qkey
from backtest import researchBigRun3 as RB3                 # noqa: E402  WORK、SHA_A（只讀常數）

REG_SHA = "2b3c853a8290be22"
OUT = "backtest/resultsShortageExit/freq"
WORK = RT.WORK
PANEL = os.path.join(RB3.WORK, "bgr3_panel_full.pkl")
DEDUP_M = 24
ES = (120, 250, 500)
EJ = 250
DROP4, DROP5, ACC3 = -0.30, 0.70, -0.05
PE_WIN, PE_MINN, PE_Q, EPS_W = 60, 36, 20, 20
NEFF_MIN = 24
SEGS = [("早於探索(不入段)", "2004-01-01", "2006-03-31"), ("探索", "2006-04-01", "2015-12-31"), ("確認", "2016-01-01", "2099-12-31")]
RAW8 = RT.RAW8
GROUPS = {"被動元件": "6173 6175 2327 2492 3026 2478 3624 2375 2472 6449 6862 3357".split(),
          "記憶體": "2408 2344 2337 3006 3260 4967 5289".split(),
          "PCB材料": "1802 1815 5340 5475 1303 8358 4989 2383 6274 6213 6672".split()}
RULES = ["C1", "C2", "C3", "C4", "C5", "C6", "C7"]
RNAME = {"C1": "營收月增≤0連2月", "C2": "單月年增由≥0轉<0", "C3": "轉弱(近3月−近12月≤−5點)", "C4": "距一年高點≤−30%(營收可用日)",
         "C5": "進場後高點回落30%", "C6": "循環高峰(EPS創20季高∧本益比≤60月P20)", "C7": "毛利率年增由≥0轉<0"}
BIG = 10 ** 9
NOTES = ["頻率表、未算任何報酬（seq366）；只看這一筆，沒算賣掉的錢拿去做什麼",
         "缺貨型以產業別代理（塑膠、鋼鐵等八業），不是逐檔判定的缺貨",
         "持有 250 日、月與月不獨立 ⇒ 月分群 CI 偏窄 ⇒ 結論最多「暫定」；任一段 n_eff ＜ 24 ⇒ 該格還沒測",
         "財報（fin_hist、fs_xbrl、上傳時戳）2013Q1 起 ⇒ C6、C7 在 2014 年以前判不了；C6 要 20 季近 4 季 EPS ⇒ 約 2018 年底起才可能可判",
         "族群名單 ＝ 台股策略線十條供應鏈（2026-10-20 現在名單、事後挑的），只描述",
         "2015～2018 下市 58 家月營收補不回（存活者偏差，seq406／411）；早年上櫃 2007-07 前無價",
         "價格面板 ＝ rerun17 H2D（edc6f，資料尾 2026-09-24）；月營收、產業、財報、exright ＝ 最新 origin/main；本益比 ＝ BigRun3 面板（快照 dbfb96）",
         "同根兩出場價取較低（seq373）：每法每筆只有一個賣價（判到隔日開盤）⇒ 不適用"]
LOG = RT.LOG
log = RT.log


def segof(d):
    s = str(pd.Timestamp(d).date())
    for nm, a, b in SEGS:
        if a <= s <= b:
            return nm
    return "其他"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--sha", default=None, help="資料版本（預設最新 origin/main；兩件同跑時傳同一個）")
    a = ap.parse_args()
    t0 = time.time()
    out = os.path.join(WORK, "dry_sx") if a.limit else OUT
    os.makedirs(out, exist_ok=True)
    reg = IMF.reg_check(REG_SHA); log(f"[登錄] {reg}（sha {REG_SHA} 已驗）")
    sha, DN, MD = RT.ensure_data(a.sha); log(f"[資料] origin/main {sha}｜{DN}")
    PX = RT.prices(sha, DN, a.procs)
    CAL, SIDS, ix = PX["CAL"], PX["SIDS"], PX["ix"]
    NC = len(CAL); CEND = NC - 1
    C, BAD, TRD, O, DNL, LASTV, VP, CB = PX["C"], PX["BAD"], PX["TRD"], PX["O"], PX["DNL"], PX["LASTV"], PX["VP"], PX["CB"]
    codes = SIDS
    if a.limit:
        rng0 = np.random.default_rng(RT.SEED)
        codes = sorted(set(rng0.choice(SIDS, a.limit, replace=False).tolist()) | {s for g in GROUPS.values() for s in g if s in ix})
    RV, rdiag = RT.rev_table(MD, codes, a.procs, tag=("all" if not a.limit else f"drysx{a.limit}"))
    pit = IMF.load_pit(DN)
    GM, gsrc = RT.gm_table(DN); FP, fsrc = RT.filing_pos(DN, CAL)
    periods = sorted(RV["period"].unique())
    APOS = RT.avail_pos(CAL, periods)
    RV["i"] = RV["sid"].map(ix).fillna(-1).astype(int)
    RV["A"] = RV["period"].map(APOS).astype(int)
    RV["起點"] = RV["up"] & ~RV["up_prev"]
    G = PX["G"]
    REVD = {s: {p: (y, ac, fm) for p, y, ac, fm in zip(g["period"], g["yoy"], g["accel"], g["flag_mom2"])} for s, g in RV.groupby("sid")}
    # ── 本益比（BigRun3 面板）、近 4 季 EPS
    PN = pickle.load(open(PANEL, "rb"))
    if list(PN["SIDS"]) != list(SIDS):
        raise SystemExit("⛔ BigRun3 面板 SIDS ≠ 合併價格 SIDS")
    MEp = np.asarray(PN["MEp"], np.int64); K = len(MEp)
    ME, _ = PF.month_ends(CAL)
    if not np.array_equal(np.asarray(ME, np.int64), MEp):
        raise SystemExit("⛔ 月底 ≠ 面板 MEp")
    PE = np.asarray(PN["P"]["本益比"], float)
    METAq = np.asarray(PN["META"]["fs_qk"])
    del PN
    fl = []
    for f in sorted(glob.glob(os.path.join(DN, "mops", "fin_hist", "*.csv"))):
        b = os.path.basename(f)[:6]
        x = pd.read_csv(f, dtype={"stock_id": str}, usecols=["stock_id", "eps_ytd"]); x["qk"] = LP.qkey(b[:4], b[5]); fl.append(x)
    FN = pd.concat(fl).drop_duplicates(["stock_id", "qk"], keep="last"); FN["eps_ytd"] = pd.to_numeric(FN["eps_ytd"], errors="coerce")
    R4 = {}
    for s, g in FN.groupby("stock_id"):
        y = g.set_index("qk")["eps_ytd"]
        qs = sorted(y.index)
        sq = {q: LP.single(y, q) for q in range(qs[0], qs[-1] + 1)}
        R4[s] = {q: (float(sum(sq[j] for j in range(q - 3, q + 1))) if all(np.isfinite(sq.get(j, np.nan)) for j in range(q - 3, q + 1)) else np.nan)
                 for q in range(qs[0] + 3, qs[-1] + 1)}
    FPD = {s: (np.array([d for d, q, p in v], dtype="datetime64[ns]"), np.maximum.accumulate(np.array([q for d, q, p in v]))) for s, v in FP.items()}

    def selq(s, t):
        z = FPD.get(s)
        if z is None:
            return -1
        k = int(np.searchsorted(z[0], np.datetime64(t), "left")) - 1          # 上傳日 ＜ t
        return int(z[1][k]) if k >= 0 else -1
    # 選季與 BigRun3 面板 fs_qk 比（同式、不同快照 ⇒ 差異照報）
    qdiff = Counter()
    log(f"[財報] 毛利率來源 {gsrc}｜上傳時戳 {dict(fsrc)}｜近4季EPS 檔 {len(R4)}｜{time.time() - t0:.0f}s")
    # ── 事件（S1）
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
    nxt_memo = {}

    def nxt_sell(i):
        if i not in nxt_memo:
            ok = TRD[i] & np.isfinite(C[i]) & np.isfinite(O[i]) & ~DNL[i]
            idx = np.where(ok, np.arange(NC), BIG)
            nxt_memo[i] = np.minimum.accumulate(idx[::-1])[::-1]
        return nxt_memo[i]
    rows = []; c1m = []
    for sid, i, P, A_ in ev:
        e = A_ + 1
        ind, isrc = pit.at(sid, CAL[A_]); ind = ind or ""
        pop = "缺貨型" if ind in RAW8 else ("一般股" if ind else "無類別")
        grp = [g for g, L in GROUPS.items() if sid in L]
        fl_ = IMF.entry_flag(PX, i, A_, e) if e <= CEND else "e超出資料尾"
        row = {"sid": sid, "期別": P, "A": str(CAL[A_].date()), "e": (str(CAL[e].date()) if e <= CEND else ""), "段": (segof(CAL[e]) if e <= CEND else "其他"),
               "進場月": (f"{CAL[e].year}-{CAL[e].month:02d}" if e <= CEND else ""), "產業": ind, "產業來源": isrc, "母體": pop, "族群": "、".join(grp),
               "舊類別化學生技醫療": ind == "化學生技醫療", "進場": fl_}
        for E in ES:
            row[f"E{E}走得完"] = bool(e <= CEND and e + E <= CEND)
        if fl_ != "保留":
            rows.append(row); continue
        # E_eff（S2）
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
        Wx = W
        if kb <= Wx:
            Wx = kb - 1
        if delist and lastv < Wx:
            Wx = lastv
        kmax = Wx - 1                                     # 最長判日窗（E＝500 或資料尾）
        ns = nxt_sell(i)
        # 月營收判日
        rv = REVD.get(sid, {})
        Qs = []
        for Q in periods:
            if Q <= P:
                continue
            aq = APOS[Q]
            if aq > kmax:
                break
            if aq < e or Q not in rv:
                continue
            Qs.append((Q, aq))
        trig = {}
        # C1～C3
        k1 = k2 = k3 = -1; q2 = q3 = None
        n_j = Counter()
        for Q, aq in Qs:
            y, ac, fm = rv[Q]
            n_j["月營收判點"] += 1
            if np.isfinite(fm):
                n_j["C1可判"] += 1
                if row[f"E{EJ}走得完"]:
                    c1m.append((row["段"], pop, int(Q[5:7]), bool(fm == 1.0)))
                if fm == 1.0 and k1 < 0:
                    k1 = aq
            Qp = f"{int(Q[:4]) - (Q[5:7] == '01'):04d}-{(int(Q[5:7]) - 2) % 12 + 1:02d}"
            yp = rv.get(Qp, (np.nan,))[0]
            if np.isfinite(y) and np.isfinite(yp):
                n_j["C2可判"] += 1
                if y < 0 and yp >= 0 and k2 < 0:
                    k2 = aq; q2 = Q
            if np.isfinite(ac):
                n_j["C3可判"] += 1
                if ac <= ACC3 and k3 < 0:
                    k3 = aq; q3 = Q
        trig["C1"], trig["C2"], trig["C3"] = k1, k2, k3
        # C4
        vp = VP[i]; k4 = -1; c4e = None
        for d in [e] + [aq for _, aq in Qs]:
            if d > kmax or not np.isfinite(C[i, d]):
                continue
            n_j["C4判點"] += 1
            kk = int(np.searchsorted(vp, d)); k0 = int(np.searchsorted(vp, d - 249, "left"))
            vb = BAD[i, vp[k0 + 1:kk + 1]]; bq = np.flatnonzero(vb)
            if len(bq):
                k0 = k0 + 1 + int(bq[-1])
            hi = np.max(C[i, vp[k0:kk + 1]])
            hit = bool(C[i, d] / hi - 1.0 <= DROP4)
            if d == e:
                c4e = hit
            if hit and k4 < 0:
                k4 = d
        trig["C4"] = k4
        # C5
        k5 = -1
        if kmax >= e:
            seg = C[i, e:kmax + 1]
            fin = np.isfinite(seg)
            rm = np.fmax.accumulate(np.where(fin, seg, -np.inf))
            with np.errstate(invalid="ignore"):
                h = fin & (seg <= DROP5 * rm)
            w = np.flatnonzero(h)
            k5 = e + int(w[0]) if len(w) else -1
        trig["C5"] = k5
        # C6
        k6 = -1; n6 = n6ok = 0; qd6 = 0
        for k in np.flatnonzero((MEp >= e) & (MEp <= kmax)):
            m = int(MEp[k]); n6 += 1
            q = selq(sid, CAL[m])
            if q != int(METAq[i, k]):
                qd6 += 1
            pe = PE[i, k]
            w = PE[i, max(0, k - PE_WIN + 1):k + 1]; w = w[np.isfinite(w)]
            r4 = R4.get(sid, {})
            win = [r4.get(j, np.nan) for j in range(q - EPS_W + 1, q + 1)] if q >= 0 else []
            ok = bool(np.isfinite(pe) and len(w) >= PE_MINN and len(win) == EPS_W and np.isfinite(win).all())
            if not ok:
                continue
            n6ok += 1
            if win[-1] > 0 and win[-1] >= max(win) and pe <= np.percentile(w, PE_Q) and k6 < 0:
                k6 = m
        trig["C6"] = k6
        qdiff["月底判點"] += n6; qdiff["選季與面板fs_qk不同"] += qd6
        # C7
        k7 = -1; n7 = n7ok = 0
        g = GM.get(sid, {})
        for d, q, pq in FP.get(sid, []):
            if pq < e or pq > kmax:
                continue
            n7 += 1
            a0, a4, b0, b4 = g.get(q, np.nan), g.get(q - 4, np.nan), g.get(q - 1, np.nan), g.get(q - 5, np.nan)
            if not all(np.isfinite([a0, a4, b0, b4])):
                continue
            n7ok += 1
            if (a0 - a4) < 0 and (b0 - b4) >= 0 and k7 < 0:
                k7 = pq
        trig["C7"] = k7
        row.update({"月營收判點": n_j["月營收判點"], "C1可判點": n_j["C1可判"], "C2可判點": n_j["C2可判"], "C3可判點": n_j["C3可判"], "C4判點": n_j["C4判點"],
                    "C6月底判點": n6, "C6可判點": n6ok, "C7季判點": n7, "C7可判點": n7ok, "C4進場時已成立": c4e,
                    "C2判到期": q2 or "", "C3判到期": q3 or "", "首個月營收判日偏移": (Qs[0][1] - e if Qs else None)})
        for c in RULES:
            k = trig[c]
            s = int(ns[k + 1]) if (k >= 0 and k + 1 <= CEND) else -1
            s = -1 if s >= BIG else s
            row[f"{c}_k偏移"] = (k - e) if k >= 0 else None
            row[f"{c}_s偏移"] = (s - e) if s >= 0 else None
            for E in ES:
                x, st = effs[E]
                if x is None:
                    row[f"{c}_E{E}"] = None; continue
                if k >= 0 and k <= x - 1:
                    row[f"{c}_E{E}"] = "賣出" if (0 <= s <= x) else "判到未賣出"
                else:
                    row[f"{c}_E{E}"] = "不賣"
        rows.append(row)
    EV = pd.DataFrame(rows)
    log(f"[逐事件] {len(EV)}｜可進場 {int((EV['進場'] == '保留').sum())}｜選季比對 {dict(qdiff)}｜{time.time() - t0:.0f}s")
    # ── 統計
    POPS = [("缺貨型", EV["母體"] == "缺貨型"), ("一般股", EV["母體"] == "一般股")] + [(f"族群:{g}", EV["族群"].str.contains(g)) for g in GROUPS]
    CNT = []; FR = []; JD = []; EQ = []; G12 = []
    for sg in ("早於探索(不入段)", "探索", "確認"):
        for pn, pm in POPS:
            d = EV[(EV["段"] == sg) & pm]
            ok = d[d["進場"] == "保留"]
            m = ok[ok[f"E{EJ}走得完"] == True]  # noqa: E712
            ne = int(m["進場月"].nunique())
            CNT.append({"段": sg, "母體": pn, "事件(過閘去重)": len(d), "e可進場": len(ok), "進場剔除": dict(Counter(d.loc[d["進場"] != "保留", "進場"])),
                        "E120走得完": int((ok["E120走得完"] == True).sum()), "E250走得完(主格)": len(m), "E500走得完": int((ok["E500走得完"] == True).sum()),  # noqa: E712
                        "E250走得完比例": (len(m) / len(ok) if len(ok) else np.nan), "E250壞根截斷": int((m.get("E250狀態") == "壞根截斷").sum()) if len(m) else 0,
                        "E250下市結算": int((m.get("E250狀態") == "下市結算").sum()) if len(m) else 0,
                        "主格進場月數=n_eff": ne, "n_eff≥24": ne >= NEFF_MIN, "舊類別化學生技醫療(未計入)": int(d["舊類別化學生技醫療"].sum()),
                        "C4進場時已成立": int((m["C4進場時已成立"] == True).sum()) if len(m) else 0,  # noqa: E712
                        "C4進場時已成立比例": (float((m["C4進場時已成立"] == True).mean()) if len(m) else np.nan)})  # noqa: E712
            if not len(m):
                continue
            for E in ES:
                mm = ok[ok[f"E{E}走得完"] == True]  # noqa: E712
                if not len(mm):
                    continue
                for c in RULES:
                    col = mm[f"{c}_E{E}"]
                    sold = mm[col == "賣出"]
                    FR.append({"段": sg, "母體": pn, "E": E, "賣法": c, "名稱": RNAME[c], "事件": len(mm), "月數": int(mm["進場月"].nunique()),
                               "判到": int((col != "不賣").sum()), "賣出": len(sold), "判到未賣出": int((col == "判到未賣出").sum()),
                               "判到率": float((col != "不賣").mean()), "賣出率": float((col == "賣出").mean()),
                               "判到天數中位(k−e)": (float(sold[f"{c}_k偏移"].median()) if len(sold) else np.nan),
                               "賣出天數中位(s−e)": (float(sold[f"{c}_s偏移"].median()) if len(sold) else np.nan),
                               "賣出天數p25": (float(sold[f"{c}_s偏移"].quantile(0.25)) if len(sold) else np.nan),
                               "賣出天數p75": (float(sold[f"{c}_s偏移"].quantile(0.75)) if len(sold) else np.nan)})
            # 可判（E250 主格）
            JD.append({"段": sg, "母體": pn, "主格": len(m), "月營收判點(總)": int(m["月營收判點"].sum()),
                       "C1可判點÷判點": float(m["C1可判點"].sum() / max(1, m["月營收判點"].sum())), "C2可判點÷判點": float(m["C2可判點"].sum() / max(1, m["月營收判點"].sum())),
                       "C3可判點÷判點": float(m["C3可判點"].sum() / max(1, m["月營收判點"].sum())), "C4判點(總)": int(m["C4判點"].sum()),
                       "C6月底判點(總)": int(m["C6月底判點"].sum()), "C6可判點÷月底判點": float(m["C6可判點"].sum() / max(1, m["C6月底判點"].sum())),
                       "C6事件至少一點可判": float((m["C6可判點"] > 0).mean()), "C6事件全部月底可判": float(((m["C6可判點"] == m["C6月底判點"]) & (m["C6月底判點"] > 0)).mean()),
                       "C6多數事件判不了(＜30%)": bool((m["C6可判點"] > 0).mean() < 0.30),
                       "C7季判點(總)": int(m["C7季判點"].sum()), "C7可判點÷季判點": float(m["C7可判點"].sum() / max(1, m["C7季判點"].sum())),
                       "C7事件至少一點可判": float((m["C7可判點"] > 0).mean()), "無月營收判點事件": int((m["月營收判點"] == 0).sum())})
            # 等價／退化（E250 主格）
            outc = {}
            for c in RULES:
                outc[c] = np.where(m[f"{c}_E{EJ}"] == "賣出", m[f"{c}_s偏移"].fillna(-1).astype(int), -999)
            outc["C0"] = np.full(len(m), -999)
            keys = ["C0"] + RULES
            for x_ in range(len(keys)):
                for y_ in range(x_ + 1, len(keys)):
                    same = float((outc[keys[x_]] == outc[keys[y_]]).mean())
                    EQ.append({"段": sg, "母體": pn, "項": f"{keys[x_]} vs {keys[y_]} 結果相同", "值": same, "旗標": ("近乎等價" if same >= 0.90 else "")})
            for c in RULES:
                sr = float((m[f"{c}_E{EJ}"] == "賣出").mean())
                ko = m[f"{c}_k偏移"]
                if c in ("C1", "C2", "C3"):
                    first = m["首個月營收判日偏移"]
                    imm = float(((ko == first) & ko.notna()).mean())
                elif c in ("C4", "C5"):
                    imm = float((ko == 0).mean())
                else:
                    imm = np.nan
                EQ.append({"段": sg, "母體": pn, "項": f"{c} 賣出率", "值": sr, "旗標": ("近乎等於不賣(＜10%)" if sr < 0.10 else "")})
                if np.isfinite(imm):
                    EQ.append({"段": sg, "母體": pn, "項": f"{c} 首個判日即判到", "值": imm, "旗標": ("近乎立即賣(≥90%)" if imm >= 0.90 else "")})
            b45 = m["C4_k偏移"].notna() & m["C5_k偏移"].notna()
            EQ.append({"段": sg, "母體": pn, "項": "C4、C5 都判到中同日", "值": (float((m.loc[b45, "C4_k偏移"] == m.loc[b45, "C5_k偏移"]).mean()) if b45.any() else np.nan), "旗標": ""})
            EQ.append({"段": sg, "母體": pn, "項": "C4、C5 都判到中 C4 較早", "值": (float((m.loc[b45, "C4_k偏移"] < m.loc[b45, "C5_k偏移"]).mean()) if b45.any() else np.nan), "旗標": ""})
            b23 = m["C2_k偏移"].notna() & m["C3_k偏移"].notna()
            EQ.append({"段": sg, "母體": pn, "項": "C2、C3 都判到中同一期", "值": (float((m.loc[b23, "C2判到期"] == m.loc[b23, "C3判到期"]).mean()) if b23.any() else np.nan), "旗標": ""})
            EQ.append({"段": sg, "母體": pn, "項": "C2 判到中 C3 也判到", "值": (float(m.loc[m["C2_k偏移"].notna(), "C3_k偏移"].notna().mean()) if m["C2_k偏移"].notna().any() else np.nan), "旗標": ""})
            if pn in ("缺貨型", "一般股") and sg in ("探索", "確認"):
                months = sorted({f"{dd.year}-{dd.month:02d}" for dd in CAL if (SEGS[1][1] if sg == "探索" else SEGS[2][1]) <= str(dd.date()) <= (SEGS[1][2] if sg == "探索" else SEGS[2][2])})
                m0 = RT.mnum(months[0])
                for g_, dd in m.groupby(m["進場月"].map(lambda s: (RT.mnum(s) - m0) % 12)):
                    G12.append({"段": sg, "母體": pn, "組(進場月序mod12)": int(g_), "件數": len(dd), "月數": int(dd["進場月"].nunique())})
    CNT = pd.DataFrame(CNT); FR = pd.DataFrame(FR); JD = pd.DataFrame(JD); EQ = pd.DataFrame(EQ)
    # C1 分月
    C1 = pd.DataFrame(c1m, columns=["段", "母體", "期別月份", "成立"])
    C1M = []
    for (sg, pn), d in C1.groupby(["段", "母體"]):
        for mo, dd in d.groupby("期別月份"):
            C1M.append({"段": sg, "母體": pn, "期別月份": int(mo), "判點": len(dd), "條件成立": int(dd["成立"].sum()), "成立率": float(dd["成立"].mean())})
    first = EV[EV["C1_E250"] == "賣出"].copy() if "C1_E250" in EV else EV.iloc[0:0]
    C1M = pd.DataFrame(C1M)
    # 第一次判到的期別月份（E250 主格、賣出）：以判到日所在曆月往前推 1 個月 ≈ 期別月份 ⇒ 改用 A 日期月份照報
    if len(first):
        first["判到日"] = [CAL[CAL.searchsorted(pd.Timestamp(e_)) + int(k)] for e_, k in zip(first["e"], first["C1_k偏移"])]
        fm = first.groupby(["段", "母體", first["判到日"].map(lambda d: d.month)]).size().rename("第一次判到(依判日月份)").reset_index()
        fm = fm.rename(columns={"判到日": "判日月份"})
    else:
        fm = pd.DataFrame()
    # 輸出
    EV.to_csv(os.path.join(out, "events.csv.gz"), index=False, encoding="utf-8-sig", compression="gzip")
    CNT.to_csv(os.path.join(out, "counts.csv"), index=False, encoding="utf-8-sig")
    FR.to_csv(os.path.join(out, "freq_段.csv"), index=False, encoding="utf-8-sig")
    JD.to_csv(os.path.join(out, "judge.csv"), index=False, encoding="utf-8-sig")
    EQ.to_csv(os.path.join(out, "equiv.csv"), index=False, encoding="utf-8-sig")
    C1M.to_csv(os.path.join(out, "c1_month.csv"), index=False, encoding="utf-8-sig")
    fm.to_csv(os.path.join(out, "c1_first_month.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(G12).to_csv(os.path.join(out, "group12.csv"), index=False, encoding="utf-8-sig")
    per_diff = subprocess.run(["git", "diff", "--shortstat", RB3.SHA_A, sha, "--", "data/early/per", "data/early/otcper", "data/stocks_per"], capture_output=True, text=True).stdout.strip()
    J = {"性質": "缺貨型持股確認後怎麼賣 seq1 頻率表（⛔ 未算任何報酬）", "登錄": f"台股策略線 seq1 sha {REG_SHA}", "裁定": "seq447 §一",
         "origin/main": sha, "價格面板": {"主": PX["main_data"], "早年": PX["early_data"]}, "接縫": PX["seam"], "exright": PX["info"],
         "本益比面板": {"檔": PANEL, "快照": RB3.SHA_A, "per 路徑對最新 main 差異": per_diff or "相同"},
         "月營收": rdiag, "毛利率來源": gsrc, "上傳時戳來源": dict(fsrc), "選季對 BigRun3 fs_qk": dict(qdiff), "乾跑": bool(a.limit), "乾跑股數": a.limit,
         "起點": {"全部": int(len(ST)), "剔除": dict(reasons), "過閘去重事件": int(len(ev))}, "族群名單": GROUPS,
         "counts": CNT.to_dict("records"), "judge": JD.to_dict("records"), "必附": NOTES, "讀法": __doc__.split("═══ 讀法")[1], "秒": round(time.time() - t0)}
    json.dump(J, open(os.path.join(out, "freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=RT.jdef)
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    log(f"[完成] {out}｜{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
