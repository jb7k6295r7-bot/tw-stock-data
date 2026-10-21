# -*- coding: utf-8 -*-
"""大漲後「頂部樣子」當賣出訊號 seq1【頻率表・乾跑】（台股策略線 登錄 sha e30036415fbbce81，2026-10-22 01:00；裁定 seq441 發號 N_前段 ＋1、最多暫定）
——回測線計算子代理。
⛔ 只數母體、訊號、可算比例、n_eff、窗能不能走完、重疊；⛔ 不讀、不算、不存任何進場後報酬（d、6 個月 d、腰斬比例一律留正式跑，seq366）。
   用到的價格只有 ≤ 月底 t 的還原收盤（36 個月低點比、距一年高點）與進場後窗的「有沒有有效 K 棒／壞根／下市」旗標（⛔ 不存價格數值）。
⛔ 不 commit、不改既有檔；researchBigRun3（月底面板 bgr3_panel_full.pkl：本益比、ROE、集保千張大戶比 12 月變化、產業 INDM、距一年高點）、
   researchBigRun5（近 4 季 EPS、同月同產業中位的算法；兩者寫在 main() 內無法 import ⇒ 同式重寫，_check 以 resultsBigRun5/逐段 對帳）、
   researchIndMom_freq（build_panel 兩世界價格面板、reg_check）、researchPTH_freq（month_ends）、researchLongPool（qkey、single）⛔ 只 import／只讀。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTopSell_freq [--limit N（乾跑，輸出到 ~/tpswork/dry）]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTopSell_freq_check [--dry]
輸出 backtest/resultsTopSell/freq/：freq.json、freq_段.csv、yearly.csv、monthly.csv、cond_段.csv、equiv.csv、overlap_D.csv、overlap_F7.csv、
     events.csv.gz（母體逐列旗標，無報酬）、run.log

═══ 讀法（T 標；登錄沒寫清楚、執行者補的都在這裡；⛔ 在看任何本件數字之前寫死於 2026-10-22（台北）；★＝執行者定，〔 〕內為另一讀法）═══
 T0 資料：月底面板 ＝ researchBigRun3 的 ~/bgrwork/bgr3_panel_full.pkl（快照 A dbfb96cb81a7：財報、上傳時戳、產業、早年 per；B 325a1ee753cf：集保；
    主 stocks_per）原值；★ 開跑時以 git diff 確認 A／B 的 fin_hist、filing_dates、industry_hist、early/per、early/otcper、tdcc_hist 與最新 origin/main 完全相同，
    不同即中止；stocks_per 主表有更新（逐日附加）⇒ _check 以最新 origin/main 重讀月底 per 逐格比（差異照報）。
    近 4 季 EPS ＝ 最新 origin/main 的 mops/fin_hist（git archive 到 ~/tpswork/main_<sha12>）。價格 ＝ researchIndMom_freq.build_panel 兩世界（快取
    ~/b2fwork/panel_<世界>.pkl：主 rerun17 H2D 2015-01-05～2026-09-24、早年 eotc 2004-02-11～2014-12-31；四碼普通股 UG.gate3(GATE_V2)、含已下市；
    壞根 ＝ load_bars next_bad ∪ crashwork ∪ 早年 reduce_v2）；兩世界接成合併日曆，接縫照 researchBigRun3 原式（主段乘 M ＝ c_e·rc_m ÷ (rc_e·c_m)，
    兩根相隔 ≥ 5 交易日或 M 不可算 ⇒ 接縫那根記壞根）。⭐ _check 以「重算 距一年高點／距5年低點 與面板逐格相同」驗接縫與價格同源。
 T1 月底 t ＝ researchPTH_freq.month_ends(合併日曆)（＝ 面板 MEp）；2004-02～2026-08。
 T2 母體（登錄 §二）：W1 eligible ＝ 上述四碼普通股（含已下市）；500 張閘 ＝ 面板 G[t]（patterns.Frame.gate：含 t 的 20 交易日都有成交 ∧ t−20～t−1 日均量 ≥ 500 張；
    ∧ UG.pit_valid）；t 當天有有效 K 棒。
    R36 ＝ c[t] ÷ 窗內最低還原收盤；★ 窗 ＝ 合併日曆 (第 k−36 個月底, t] 的有效 K 棒（k ＜ 36 ⇒ 自第一根）；★ 窗內有壞根 ⇒ 窗從最後一個壞根那根起算
    （面板 距一年高點／距5年低點 同式）；★ 上市不足 36 個月 ⇒ 用可得部分〔另一讀法：只取「36 月完整且無壞根」，另報件數〕。R36 ≥ 3。
    距一年高點 ＝ 面板「距一年高點」（250 交易日窗、同壞根截法）≥ −0.20（含 −20%）。
    去重 ★：同一檔逐月掃，符合月 k 取入判，之後 k＋1～k＋5 符合者標「照報(6月內)」不入判，k＋6 起再符合可再入判。
 T3 訊號（登錄 §三，寫死）：
    T1a ★ 本益比 ＝ 面板月底官方 per（虧損或缺 ⇒ 空白）；5 年（月底）分布 ＝ 第 k−59～k 個月底（含當月、60 個）有值者，有值 ≥ 36 個才可算；
        位置 ＝ 窗內 ≤ 當月值的比例；T1a ＝ 位置 ≥ 0.80。〔另一讀法 T1a′ ＝ 面板「本益比5年位置」（每日、1250 日窗、有值 ≥ 750）≥ 0.80，只報一致率〕
    T1b 近四季 EPS ≤ 0 ＝ researchBigRun5 G5 同式：選季 ＝ 面板 fs_qk（上傳時戳 ＜ t 的最新季；AI1 優先、否則最早文件，seq352），
        fin_hist eps_ytd 差分成單季、4 季齊全加總；★ 登錄字面「≤ 0」（BigRun5 虧損為 ＜ 0）。
    T1 ＝ T1a ∨ T1b，三值：任一為真 ⇒ 真；兩者皆可判且為假 ⇒ 假；其餘 ⇒ 不可判。
    T2 ＝ 面板 ROE ＜ 同月同產業中位；中位 ＝ researchBigRun5 G4 同式（面板 INDM 同產業、該月 ROE 有值者，含自己；INDM 已排除「其他」「綜合」
        「存託憑證」「ETF」與無類別）；ROE 缺、無產業 ⇒ 不可判。
    T3 ＝ 面板「集保千張大戶比12月變化」＜ 0（level 15 pct；月底前一交易日或更早 14 交易日內最近一週；與 12 個月底前之差）；缺 ⇒ 不可判。
    S ＝ T1 ∧ T2 ∧ T3（三值 Kleene：全真 ⇒ 成立；任一假 ⇒ 不成立；其餘 ⇒ 不可判）〔另一讀法：三條件全可算者才進判定母體，另報件數〕。
    早年描述 S12 ＝ T1 ∧ T2（同三值）。
 T4 段（登錄 §四）★ 依月底 t 歸段：早年(描述) 2005-01～2016-12（S12）｜2017（不入段，照報）｜探索 2018-01～2021-12｜確認 2022-01～2025-08（12 個月窗走得完）
    ｜確認(窗未滿) 2025-09～2026-08 另列。
    進場 e ＝ t 的下一個合併日曆交易日（開盤）；窗尾 ★ ＝ e 之後 12 個曆月當天或之前最後一個交易日；
    旗標（只數、⛔ 不算報酬）：日曆可走完（e＋12 月 ≤ 資料尾 2026-09-24）、壞根(t,e]、e無成交、e開盤鎖漲停、窗內遇壞根、窗內遇下市（最後有效 K 棒 ＜ 窗尾
    且距資料尾 ≥ 5 交易日）、接縫不明（早年獨有、活到 2014 年底前 5 日內、窗跨接縫）。
    「可用」★ ＝ 日曆可走完 ∧ e 有成交 ∧ (t,e] 無壞根（遇壞根、遇下市、開盤鎖漲停照數，處理留正式跑依 seq373 等規則）。
    n_eff ＝ min(S 成立可用事件數, 有 S 成立可用事件的月數)；任一段 n_eff ＜ 30 ⇒ 依構造不可判定、只描述（登錄 §五）。
 T5 等價／退化（seq377、登錄 §五）：各段、S 可判列中 S 成立比例（＞ 90% 或 ＜ 5% ⇒ 退化）；S 與單一條件、兩兩組合的一致率、|S|÷|T|；
    T1 兩分支（T1a、T1b）各自比例與各自與 T2 的重疊；一致率 ≥ 95% ★ ⇒「近乎等價」先報。
 T6 重疊（描述）：
    ① 對照 D（resultsBigRun3/乙_全表 的乙 ×3 段、對照D 標籤）★：同一檔有乙段的高點月底 k_h 滿足 k_h − 12 ≤ k ≤ k_h ＋ 6 ⇒ 該列「落在乙段頂部附近」，
       取最接近的一段的標籤（崩／未崩／未定／遇壞根截／下市）；報 S 成立、不成立、不可判 三組的分布；反向：高點月在各段內的 D 崩段、未崩段中，
       [k_h − 12, k_h] 內同檔有 S 成立入判列的比例。⚠ 對照 D 用了高點後價格（事後標籤），只描述重疊、⛔ 不當報酬。
    ② 長線三問丙 F7（resultsLong3/freq/events_丙.csv.gz 的 F7_首次，使用者版賣法）★：S 成立入判列中，同檔 F7 首次觸發日落在 [t − 3 個月, t ＋ 3 個月] 的比例，
       S 不成立同比例並列；反向：2018 起 F7 首次觸發中，觸發日所在月（含當月月底）同檔為本件母體（去重前）且 S 成立的比例。
       ⚠ F7 只存在於「營收創 24 月新高」事件的持有窗內（丙母體），重疊比例的分母照寫。
 T7 必附：「頻率表、未算任何報酬」「條件是看過對照 D 結果才挑的（最多暫定）」「集保 pct 2019-06-28 起才有值 ⇒ 12 月變化 2020-07 月底起」
    「本益比官方 per 主表 2015 起、早年 2012 起 ⇒ 5 年（月底）位置最早 2014-12」「虧損股官方 per 空白 ⇒ 由 T1b 接手」。
"""
from __future__ import annotations

import argparse
import glob
import gzip
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
from backtest import researchIndMom_freq as IMF             # noqa: E402  build_panel、reg_check
from backtest import researchPTH_freq as PF                 # noqa: E402  month_ends
from backtest import researchLongPool as LP                 # noqa: E402  qkey、single
from backtest import researchBigRun3 as RB3                 # noqa: E402  SHA_A、SHA_B、WORK（只讀常數）

REG_SHA = "e30036415fbbce81"
OUT = "backtest/resultsTopSell/freq"
WORK = os.path.expanduser("~/tpswork")
PANEL = os.path.join(RB3.WORK, "bgr3_panel_full.pkl")
SAME_A = ["data/mops/fin_hist", "data/meta/filing_dates.csv", "data/meta/industry_hist", "data/early/per", "data/early/otcper"]
SAME_B = ["data/tdcc_hist"]
PARTS = ["data/mops/fin_hist"]
R36_MIN, HI_MIN, PE_Q, PE_WIN, PE_MINN, DEDUP = 3.0, -0.20, 0.80, 60, 36, 6
NEFF_MIN = 30
EQ_HI = 0.95
SEGS = [("早年(描述)", "2005-01", "2016-12"), ("2017(不入段)", "2017-01", "2017-12"), ("探索", "2018-01", "2021-12"),
        ("確認", "2022-01", "2025-08"), ("確認(窗未滿)", "2025-09", "2026-08")]
NOTES = ["頻率表、未算任何報酬（seq366）", "條件是看過對照 D 結果才挑的 ⇒ 最多暫定、要靠往後紀錄確認", "只看單筆，沒算賣掉的錢去哪",
         "集保 level 15 pct 2019-06-28 起才有值（2017-07-21、2018-11～12 只有股數、pct 空白）⇒ 12 月變化 2020-07 月底起",
         "本益比官方 per：主 2015 起、早年 2012 起 ⇒ 5 年（月底）位置最早 2014-12", "虧損股官方 per 空白 ⇒ 由 T1b（近四季 EPS ≤ 0）接手",
         "對照 D 是事後標籤（用了高點後價格），重疊只描述"]
LOG: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def git(*a):
    return subprocess.run(["git"] + list(a), capture_output=True, text=True, check=True).stdout.strip()


def ensure_main():
    sha = git("rev-parse", "origin/main")
    root = os.path.join(WORK, f"main_{sha[:12]}")
    if not os.path.isfile(os.path.join(root, ".done")):
        os.makedirs(root, exist_ok=True)
        p = subprocess.run(["git", "archive", "--format=tar", sha] + PARTS, capture_output=True, check=True)
        subprocess.run(["tar", "-x", "-C", root], input=p.stdout, check=True)
        open(os.path.join(root, ".done"), "w").write(sha)
    return sha, os.path.join(root, "data")


def same_check(sha):
    out = {}
    for base, paths in ((RB3.SHA_A, SAME_A), (RB3.SHA_B, SAME_B)):
        for p in paths:
            r = subprocess.run(["git", "diff", "--quiet", base, sha, "--", p])
            out[f"{p}（{base[:12]}→{sha[:12]}）"] = "相同" if r.returncode == 0 else "不同"
    if any(v != "相同" for v in out.values()):
        raise SystemExit(f"⛔ 面板快照與最新 origin/main 不同：{out}")
    r = subprocess.run(["git", "diff", "--shortstat", RB3.SHA_A, sha, "--", "data/stocks_per"], capture_output=True, text=True)
    out["data/stocks_per（主表；_check 逐格比）"] = r.stdout.strip() or "相同"
    return out


# ═════════════ 合併日曆價格（researchBigRun3 main 的接縫原式）═════════════
def merged_prices(Ze, Zm, SIDS):
    CAL = Ze["cal"].append(Zm["cal"]); NE = Ze["n0"]; NC = len(CAL)
    ie = {s: k for k, s in enumerate(Ze["sids"])}; im = {s: k for k, s in enumerate(Zm["sids"])}
    N = len(SIDS)
    C = np.full((N, NC), np.nan); BAD = np.zeros((N, NC), bool); G = np.zeros((N, NC), bool)
    TRD = np.zeros((N, NC), bool); UPL = np.zeros((N, NC), bool)
    seam = Counter()
    for i, s in enumerate(SIDS):
        if s in ie:
            j = ie[s]; C[i, :NE] = Ze["C"][j]; BAD[i, :NE] = Ze["BAD"][j]; G[i, :NE] = Ze["G"][j]; TRD[i, :NE] = Ze["TRD"][j]; UPL[i, :NE] = Ze["UPL"][j]
        if s in im:
            j = im[s]; C[i, NE:] = Zm["C"][j]; BAD[i, NE:] = Zm["BAD"][j]; G[i, NE:] = Zm["G"][j]; TRD[i, NE:] = Zm["TRD"][j]; UPL[i, NE:] = Zm["UPL"][j]
        if s in ie and s in im:
            ve = np.flatnonzero(np.isfinite(C[i, :NE])); vm = np.flatnonzero(np.isfinite(C[i, NE:]))
            if not (len(ve) and len(vm)):
                continue
            pe, pm = int(ve[-1]), int(vm[0]) + NE
            re_ = raw_close(Ze["data"], s, CAL[pe]); rm_ = raw_close(Zm["data"], s, CAL[pm])
            Mf = C[i, pe] * rm_ / (re_ * C[i, pm]) if (np.isfinite(re_) and np.isfinite(rm_) and re_ > 0 and C[i, pm] > 0) else np.nan
            if np.isfinite(Mf) and Mf > 0:
                C[i, NE:] *= Mf; BAD[i, pm] = (pm - pe - 1) >= 5
            else:
                BAD[i, pm] = True
            seam["兩世界都有"] += 1; seam["接縫壞根"] += int(BAD[i, pm])
    return CAL, NE, C, BAD, G, TRD, UPL, dict(seam), ie, im


_RAW: dict = {}


def raw_close(data, sid, d):
    f = os.path.join(data, "stocks", f"{sid}.csv")
    if (data, sid) not in _RAW:
        if not os.path.exists(f):
            _RAW[(data, sid)] = None
        else:
            x = pd.read_csv(f, dtype={"date": str}, usecols=["date", "close"]).drop_duplicates("date", keep="last")
            _RAW[(data, sid)] = dict(zip(pd.to_datetime(x["date"]), pd.to_numeric(x["close"], errors="coerce")))
    m = _RAW[(data, sid)]
    return float(m.get(pd.Timestamp(d), np.nan)) if m is not None else np.nan


# ═════════════ 主程式 ═════════════
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--limit", type=int, default=None); a = ap.parse_args()
    t0 = time.time()
    out = os.path.join(WORK, "dry") if a.limit else OUT
    os.makedirs(out, exist_ok=True)
    reg = IMF.reg_check(REG_SHA); log(f"[登錄] {reg}（sha {REG_SHA} 已驗）")
    subprocess.run(["git", "fetch", "-q", "origin"], check=False)
    sha, DN = ensure_main(); SAME = same_check(sha)
    log(f"[資料] origin/main {sha[:12]}｜面板快照比對 {SAME}")
    PN = pickle.load(open(PANEL, "rb"))
    SIDS = PN["SIDS"]; P = PN["P"]; META = PN["META"]; INDM = PN["INDM"]; MEp = np.asarray(PN["MEp"], np.int64); K = len(MEp); N = len(SIDS)
    Ze = IMF.build_panel("早年", 2, log); Zm = IMF.build_panel("主", 2, log)
    if sorted(set(Ze["sids"]) | set(Zm["sids"])) != list(SIDS):
        raise SystemExit("⛔ 面板 SIDS ≠ 兩世界代號聯集")
    CAL, NE, C, BAD, G, TRD, UPL, seam, ie, im = merged_prices(Ze, Zm, SIDS)
    NC = len(CAL); CEND = NC - 1
    ME, MK = PF.month_ends(CAL)
    if not np.array_equal(np.asarray(ME, np.int64), MEp):
        raise SystemExit("⛔ 月底 ≠ 面板 MEp")
    del Ze, Zm
    log(f"[價格] 合併日曆 {CAL[0].date()}～{CAL[-1].date()}（{NC}）｜股 {N}｜接縫 {seam}｜月底 {K}（{CAL[MEp[0]].date()}～{CAL[MEp[-1]].date()}）｜{time.time() - t0:.0f}s")
    ym = [f"{CAL[p].year}-{CAL[p].month:02d}" for p in MEp]
    # 近 4 季 EPS（BigRun5 G5 同式）
    L = []
    for f in sorted(glob.glob(os.path.join(DN, "mops", "fin_hist", "*.csv"))):
        per = os.path.basename(f)[:6]; qk = LP.qkey(per[:4], per[5])
        x = pd.read_csv(f, dtype={"stock_id": str}, usecols=["stock_id", "eps_ytd"]); x["qk"] = qk; L.append(x)
    FN = pd.concat(L).drop_duplicates(["stock_id", "qk"], keep="last"); FN["eps_ytd"] = pd.to_numeric(FN["eps_ytd"], errors="coerce")
    EPSY = {s: g.set_index("qk")["eps_ytd"] for s, g in FN.groupby("stock_id")}

    def eps4(i, k):
        qk = int(META["fs_qk"][i, k]); y = EPSY.get(SIDS[i])
        if qk < 0 or y is None:
            return np.nan
        q = [LP.single(y, j) for j in range(qk - 3, qk + 1)]
        return float(sum(q)) if np.isfinite(q).all() else np.nan
    ROE = P["ROE"].astype(float); PE = P["本益比"].astype(float); PE5d = P["本益比5年位置"].astype(float)
    TD12 = P["集保千張大戶比12月變化"].astype(float); HI1 = P["距一年高點"].astype(float)
    MED = {}

    def imed(ind, k):
        key = (ind, k)
        if key not in MED:
            mem = np.flatnonzero(INDM[:, k] == ind)
            v = ROE[mem, k]; v = v[np.isfinite(v)]
            MED[key] = (float(np.median(v)) if len(v) else np.nan, int(len(v)))
        return MED[key]
    # 逐股掃月底
    rng = np.random.default_rng(20261022)
    idx_run = sorted(rng.choice(N, a.limit, replace=False)) if a.limit else range(N)
    rows = []; hi_diff = 0.0; hi_n = 0
    for i in idx_run:
        vp = np.flatnonzero(np.isfinite(C[i]))
        if not len(vp):
            continue
        vc = C[i, vp]; vb = BAD[i, vp]
        last_taken = -999
        for k in range(K):
            p = int(MEp[k])
            if not G[i, p] or not np.isfinite(C[i, p]):
                continue
            kk = int(np.searchsorted(vp, p))
            # 距一年高點（面板同式重算，順便核）
            k1 = int(np.searchsorted(vp, p - 249, "left")); bb = np.flatnonzero(vb[k1 + 1:kk + 1]); k1 = k1 + 1 + int(bb[-1]) if len(bb) else k1
            hi = vc[kk] / vc[k1:kk + 1].max() - 1
            hp = HI1[i, k]
            if np.isfinite(hp):
                hi_diff = max(hi_diff, abs(hi - hp) / max(1.0, abs(hi))); hi_n += 1
            # R36
            ks = int(np.searchsorted(vp, MEp[k - 36], "right")) if k >= 36 else 0
            full36 = bool(k >= 36 and vp[0] <= MEp[k - 36])
            bb = np.flatnonzero(vb[ks + 1:kk + 1]); trunc = bool(len(bb))
            ks2 = ks + 1 + int(bb[-1]) if len(bb) else ks
            r36 = vc[kk] / vc[ks2:kk + 1].min()
            if not (r36 >= R36_MIN and np.isfinite(hp) and hp >= HI_MIN):
                continue
            take = (k - last_taken) >= DEDUP
            if take:
                last_taken = k
            # 訊號
            w = PE[i, max(0, k - PE_WIN + 1):k + 1]; w = w[np.isfinite(w)]; v = PE[i, k]
            pos = float((w <= v).mean()) if (np.isfinite(v) and len(w) >= PE_MINN) else np.nan
            t1a = bool(pos >= PE_Q) if np.isfinite(pos) else None
            e4 = eps4(i, k); t1b = bool(e4 <= 0) if np.isfinite(e4) else None
            t1 = True if (t1a is True or t1b is True) else (False if (t1a is False and t1b is False) else None)
            ind = INDM[i, k]; roe = ROE[i, k]
            med, nmem = imed(ind, k) if ind else (np.nan, 0)
            t2 = bool(roe < med) if (np.isfinite(roe) and np.isfinite(med)) else None
            td = TD12[i, k]; t3 = bool(td < 0) if np.isfinite(td) else None

            def k3(*xs):
                if all(x is True for x in xs):
                    return True
                if any(x is False for x in xs):
                    return False
                return None
            S = k3(t1, t2, t3); S12 = k3(t1, t2)
            # 進場與窗旗標（⛔ 無價格數值）
            e = p + 1
            fl = {"e": "", "壞根(t,e]": None, "e無成交": None, "e開盤鎖漲停": None, "日曆可走完": False, "窗內遇壞根": None, "窗內遇下市": None, "接縫不明": None}
            if e <= CEND:
                fl["e"] = str(CAL[e].date())
                fl["壞根(t,e]"] = bool(BAD[i, e]); fl["e無成交"] = bool(not TRD[i, e] or not np.isfinite(C[i, e])); fl["e開盤鎖漲停"] = bool(UPL[i, e])
                xd = CAL[e] + pd.DateOffset(months=12)
                fl["日曆可走完"] = bool(xd <= CAL[CEND])
                x = int(CAL.searchsorted(xd, side="right")) - 1
                ke = int(np.searchsorted(vp, x, "right")) - 1
                k_e = int(np.searchsorted(vp, e, "right"))
                fl["窗內遇壞根"] = bool(vb[k_e:ke + 1].any())
                lastv = int(vp[-1])
                early_only = SIDS[i] not in im
                fl["接縫不明"] = bool(early_only and p < NE and x >= NE and lastv >= NE - 6)
                fl["窗內遇下市"] = bool(lastv < x and (CEND - lastv) >= 5 and not fl["接縫不明"])
            rows.append({"sid": SIDS[i], "_i": i, "_k": k, "月": ym[k], "t": str(CAL[p].date()), "入判": take, "R36≥3": True, "R36_36月完整無壞根": bool(full36 and not trunc),
                         "距一年高點≥-20%": True, "產業": ind, "產業ROE有值數": nmem, "產業ROE中位": med, "ROE": float(roe) if np.isfinite(roe) else np.nan,
                         "本益比有值": bool(np.isfinite(v)), "本益比5年月底位置": pos, "T1a": t1a, "T1a′(面板每日)": bool(PE5d[i, k] >= PE_Q) if np.isfinite(PE5d[i, k]) else None,
                         "近4季EPS": e4, "T1b": t1b, "T1": t1, "ROE有值": bool(np.isfinite(roe)), "產業中位有值": bool(np.isfinite(med)), "T2": t2,
                         "集保12月變化有值": bool(np.isfinite(td)), "T3": t3, "S": S, "S12": S12,
                         "融資÷股數有值": bool(np.isfinite(P["融資餘額÷股數"][i, k])), "60日周轉率有值": bool(np.isfinite(P["60日周轉率"][i, k])), **fl})
    if hi_diff > 1e-5:
        raise SystemExit(f"⛔ 距一年高點重算與面板不同 {hi_diff}")
    EV = pd.DataFrame(rows)
    log(f"[母體] 符合列 {len(EV)}、入判 {int(EV['入判'].sum())}｜距一年高點重算 vs 面板 {hi_n} 格最大相對差 {hi_diff:.1e}（float32 存檔）｜{time.time() - t0:.0f}s")

    def segof(m):
        for nm, a_, b_ in SEGS:
            if a_ <= m <= b_:
                return nm
        return "2004(不入段)"
    EV["段"] = [segof(m) for m in EV["月"]]
    EV["年"] = EV["月"].str[:4]
    EV["可用"] = EV["日曆可走完"] & (EV["e無成交"] == False) & (EV["壞根(t,e]"] == False)  # noqa: E712
    J = EV[EV["入判"]].copy()

    def cnt3(s):
        return int((s == True).sum()), int((s == False).sum()), int(s.isna().sum())  # noqa: E712

    def neff(df, col="S"):
        d = df[(df[col] == True) & df["可用"]]  # noqa: E712
        return int(len(d)), int(d["月"].nunique()), int(min(len(d), d["月"].nunique()))
    # 段表
    FR = []
    for nm, a_, b_ in SEGS:
        d = J[J["段"] == nm]; col = "S12" if nm.startswith("早年") else "S"
        st, sf, su = cnt3(d[col]); n_ev, n_m, ne = neff(d, col)
        months_all = sum(1 for m in ym if a_ <= m <= b_)
        r = {"段": nm, "月份": f"{a_}～{b_}", "判定訊號": col, "段內月數": months_all, "有母體的月數": int(d["月"].nunique()),
             "母體入判列": len(d), "照報(6月內)列": int(((EV["段"] == nm) & ~EV["入判"]).sum()),
             "S成立": st, "S不成立": sf, "S不可判": su, "S成立÷可判": st / (st + sf) if (st + sf) else np.nan, "S成立÷母體": st / len(d) if len(d) else np.nan,
             "S可判的月數": int(d.loc[d[col].notna(), "月"].nunique()), "有S成立的月數": int(d.loc[d[col] == True, "月"].nunique()),  # noqa: E712
             "S成立可用事件": n_ev, "S成立可用月數": n_m, "n_eff": ne, "n_eff≥30": ne >= NEFF_MIN,
             "對照(S不成立)可用": int(((d[col] == False) & d["可用"]).sum()),  # noqa: E712
             "三條件全可算列": int((d["T1"].notna() & d["T2"].notna() & (d["T3"].notna() if col == "S" else True)).sum()),
             "日曆可走完比例": float(d["日曆可走完"].mean()) if len(d) else np.nan, "可用比例": float(d["可用"].mean()) if len(d) else np.nan,
             "窗內遇壞根(可用中)": int((d["可用"] & (d["窗內遇壞根"] == True)).sum()), "窗內遇下市(可用中)": int((d["可用"] & (d["窗內遇下市"] == True)).sum()),  # noqa: E712
             "e開盤鎖漲停(可用中)": int((d["可用"] & (d["e開盤鎖漲停"] == True)).sum()), "接縫不明": int((d["接縫不明"] == True).sum()),  # noqa: E712
             "R36_36月完整無壞根比例": float(d["R36_36月完整無壞根"].mean()) if len(d) else np.nan}
        FR.append(r)
    FR = pd.DataFrame(FR)
    # 條件可算比例（段）
    CD = []
    for nm, _, _ in SEGS:
        d = J[J["段"] == nm]; n = len(d)
        if not n:
            continue
        r = {"段": nm, "母體入判列": n}
        for c in ("本益比有值", "ROE有值", "產業中位有值", "集保12月變化有值", "融資÷股數有值", "60日周轉率有值"):
            r[f"{c}比例"] = float(d[c].mean())
        r["產業空白(其他/綜合/無類別)比例"] = float((d["產業"] == "").mean())
        r["本益比空白比例"] = 1 - r["本益比有值比例"]
        r["本益比空白且EPS≤0比例"] = float(((~d["本益比有值"]) & (d["T1b"] == True)).mean())  # noqa: E712
        r["近4季EPS有值比例"] = float(d["近4季EPS"].notna().mean())
        for c in ("T1a", "T1b", "T1", "T2", "T3", "S12", "S"):
            a1, b1, c1 = cnt3(d[c]); r[f"{c}_成立"] = a1; r[f"{c}_不成立"] = b1; r[f"{c}_不可判"] = c1
            r[f"{c}_成立÷可判"] = a1 / (a1 + b1) if (a1 + b1) else np.nan
        CD.append(r)
    CD = pd.DataFrame(CD)
    # 年表、月表
    def tab(by):
        o = []
        for g, d in J.groupby(by):
            r = {by: g, "母體入判列": len(d), "母體檔數": int(d["sid"].nunique())}
            for c in ("T1", "T2", "T3", "S12", "S"):
                a1, b1, c1 = cnt3(d[c]); r[f"{c}成立"] = a1; r[f"{c}可判"] = a1 + b1; r[f"{c}成立÷可判"] = a1 / (a1 + b1) if (a1 + b1) else np.nan
            r["S成立÷母體"] = r["S成立"] / len(d)
            if by == "年":
                n_ev, n_m, ne = neff(d, "S"); r["S成立可用事件"] = n_ev; r["S成立可用月數"] = n_m; r["n_eff(S)"] = ne
                n_ev, n_m, ne = neff(d, "S12"); r["n_eff(S12)"] = ne
            o.append(r)
        return pd.DataFrame(o)
    YR = tab("年"); MO = tab("月")
    # 等價／退化
    EQ = []
    for nm in ("探索", "確認", "早年(描述)"):
        d = J[J["段"] == nm]; col = "S12" if nm.startswith("早年") else "S"
        conds = ["T1", "T2"] + (["T3"] if col == "S" else [])
        dd = d[d[col].notna()]
        if not len(dd):
            EQ.append({"段": nm, "項": f"{col} 可判列", "值": 0}); continue
        sv = dd[col] == True  # noqa: E712
        EQ.append({"段": nm, "項": f"{col} 成立比例（可判列 {len(dd)}）", "值": float(sv.mean()),
                   "旗": "退化（>90% 或 <5%）" if (sv.mean() > 0.9 or sv.mean() < 0.05) else ""})
        combos = [(c,) for c in conds] + [(a_, b_) for ii, a_ in enumerate(conds) for b_ in conds[ii + 1:]]
        for cb in combos:
            m = np.ones(len(dd), bool); tv = np.ones(len(dd), bool)
            for c in cb:
                m &= dd[c].notna().to_numpy(); tv &= (dd[c] == True).to_numpy()  # noqa: E712
            agree = float((tv[m] == sv.to_numpy()[m]).mean()) if m.any() else np.nan
            EQ.append({"段": nm, "項": f"{col} vs {'∧'.join(cb)}：一致率（兩者皆可判 {int(m.sum())}）", "值": agree,
                       "|S|÷|條件|": float(sv.to_numpy()[m].sum() / max(1, tv[m].sum())), "條件成立比例": float(tv[m].mean()) if m.any() else np.nan,
                       "旗": "近乎等價" if (np.isfinite(agree) and agree >= EQ_HI) else ""})
        # T1 兩分支
        t1d = d[d["T1"] == True]  # noqa: E712
        if len(t1d):
            only_a = (t1d["T1a"] == True) & (t1d["T1b"] != True); only_b = (t1d["T1b"] == True) & (t1d["T1a"] != True)  # noqa: E712
            both = (t1d["T1a"] == True) & (t1d["T1b"] == True)  # noqa: E712
            EQ.append({"段": nm, "項": f"T1 成立 {len(t1d)} 中：只 T1a 本益比高檔", "值": float(only_a.mean())})
            EQ.append({"段": nm, "項": "T1 成立中：只 T1b 虧損", "值": float(only_b.mean())})
            EQ.append({"段": nm, "項": "T1 成立中：兩者皆是", "值": float(both.mean())})
            for lab, mk in (("T1b 虧損", d["T1b"] == True), ("T1a 本益比高檔∧非虧損", (d["T1a"] == True) & (d["T1b"] != True))):  # noqa: E712
                x = d[mk & d["T2"].notna()]
                EQ.append({"段": nm, "項": f"{lab} 中 T2（ROE 低於產業中位）成立比例（T2 可判 {len(x)}）", "值": float((x["T2"] == True).mean()) if len(x) else np.nan})  # noqa: E712
            x = d[d["T2"].notna()]
            EQ.append({"段": nm, "項": f"基準：全部 T2 可判列 T2 成立比例（{len(x)}）", "值": float((x["T2"] == True).mean()) if len(x) else np.nan})  # noqa: E712
        x = d[d["T1a"].notna() & d["T1a′(面板每日)"].notna()]
        EQ.append({"段": nm, "項": f"T1a（月底 60 個）vs T1a′（每日 1250 日）一致率（兩者皆可判 {len(x)}）",
                   "值": float((x["T1a"] == x["T1a′(面板每日)"]).mean()) if len(x) else np.nan})
        x = d[d[col].notna()]
        if col == "S":
            allc = d["T1"].notna() & d["T2"].notna() & d["T3"].notna()
            EQ.append({"段": nm, "項": f"〔另一讀法〕三條件全可算列 {int(allc.sum())} 中 S 成立比例", "值": float((d.loc[allc, "S"] == True).mean()) if allc.any() else np.nan})  # noqa: E712
    EQ = pd.DataFrame(EQ)
    # 重疊 ① 對照 D
    Y = pd.read_csv("backtest/resultsBigRun3/乙_全表.csv.gz", dtype={"代號": str}, usecols=["代號", "_i", "_k高點", "對照D", "高點"])
    segs_by_i = defaultdict(list)
    for i_, kh_, lab_ in zip(Y["_i"], Y["_k高點"], Y["對照D"]):
        segs_by_i[int(i_)].append((int(kh_), lab_))

    def dlab(i, k):
        best = None
        for kh, lab in segs_by_i.get(i, []):
            if kh - 12 <= k <= kh + 6:
                if best is None or abs(k - kh) < abs(k - best[0]):
                    best = (kh, lab)
        return best[1] if best else "不在乙段頂部附近"
    J["對照D標籤"] = [dlab(i, k) for i, k in zip(J["_i"], J["_k"])]
    OD = []
    for nm in ("探索", "確認", "早年(描述)"):
        d = J[J["段"] == nm]; col = "S12" if nm.startswith("早年") else "S"
        for gl, gm in (("成立", d[col] == True), ("不成立", d[col] == False), ("不可判", d[col].isna())):  # noqa: E712
            g = d[gm]; vc_ = g["對照D標籤"].value_counts()
            r = {"段": nm, "訊號": col, "組": gl, "列數": len(g)}
            for lab in ("崩", "未崩", "未定", "遇壞根截", "下市", "不在乙段頂部附近"):
                r[f"{lab}比例"] = float(vc_.get(lab, 0) / len(g)) if len(g) else np.nan
            OD.append(r)
    seg_k = {nm: [k for k in range(K) if a_ <= ym[k] <= b_] for nm, a_, b_ in SEGS}
    sk = defaultdict(set)
    for i, k, s_, s12 in zip(J["_i"], J["_k"], J["S"], J["S12"]):
        if s_ == True:  # noqa: E712
            sk[("S", i)].add(k)
        if s12 == True:  # noqa: E712
            sk[("S12", i)].add(k)
    for nm in ("探索", "確認", "早年(描述)"):
        col = "S12" if nm.startswith("早年") else "S"; ks = set(seg_k[nm])
        for lab in ("崩", "未崩"):
            g = Y[(Y["對照D"] == lab) & Y["_k高點"].isin(ks)]
            hit = sum(1 for i_, kh_ in zip(g["_i"], g["_k高點"]) if any((kh_ - 12) <= kk <= kh_ for kk in sk.get((col, int(i_)), ())))
            OD.append({"段": nm, "訊號": col, "組": f"反向：高點月在段內的 D {lab}段", "列數": len(g), "高點前12月內有訊號成立比例": hit / len(g) if len(g) else np.nan})
    OD = pd.DataFrame(OD)
    # 重疊 ② 丙 F7
    F = pd.read_csv("backtest/resultsLong3/freq/events_丙.csv.gz", dtype={"sid": str}, usecols=["sid", "F7_首次"])
    F = F[F["F7_首次"].notna() & (F["F7_首次"] != "")]
    F["d"] = pd.to_datetime(F["F7_首次"])
    f7 = {s: g["d"].sort_values().to_numpy() for s, g in F.groupby("sid")}

    def f7near(s, t):
        a_ = f7.get(s)
        if a_ is None:
            return False
        t = pd.Timestamp(t); lo = np.datetime64(t - pd.DateOffset(months=3)); hi = np.datetime64(t + pd.DateOffset(months=3))
        return bool(((a_ >= lo) & (a_ <= hi)).any())
    J["F7±3月"] = [f7near(s, t) for s, t in zip(J["sid"], J["t"])]
    O7 = []
    for nm in ("探索", "確認", "早年(描述)"):
        d = J[J["段"] == nm]; col = "S12" if nm.startswith("早年") else "S"
        for gl, gm in (("成立", d[col] == True), ("不成立", d[col] == False), ("不可判", d[col].isna())):  # noqa: E712
            g = d[gm]
            O7.append({"段": nm, "訊號": col, "組": gl, "列數": len(g), "同檔F7首次在t±3月比例": float(g["F7±3月"].mean()) if len(g) else np.nan})
    EVk = {(s, m): (S, S12) for s, m, S, S12 in zip(EV["sid"], EV["月"], EV["S"], EV["S12"])}
    for nm, a_, b_ in SEGS[2:4]:
        g = F[(F["d"] >= pd.Timestamp(a_ + "-01")) & (F["d"] <= pd.Timestamp(b_ + "-01") + pd.offsets.MonthEnd(0))]
        inpop = [EVk.get((s, f"{d.year}-{d.month:02d}")) for s, d in zip(g["sid"], g["d"])]
        npop = sum(1 for x in inpop if x is not None); ns = sum(1 for x in inpop if x is not None and x[0] == True)  # noqa: E712
        O7.append({"段": nm, "訊號": "S", "組": "反向：F7 首次觸發（觸發月）", "列數": len(g), "當月同檔在本件母體(去重前)比例": npop / len(g) if len(g) else np.nan,
                   "當月同檔 S 成立比例": ns / len(g) if len(g) else np.nan})
    O7 = pd.DataFrame(O7)
    # 輸出
    w = lambda df, nm: df.to_csv(os.path.join(out, nm), index=False, encoding="utf-8-sig")
    w(FR, "freq_段.csv"); w(CD, "cond_段.csv"); w(YR, "yearly.csv"); w(MO, "monthly.csv"); w(EQ, "equiv.csv"); w(OD, "overlap_D.csv"); w(O7, "overlap_F7.csv")
    EVo = EV.merge(J[["sid", "_k", "對照D標籤", "F7±3月"]], on=["sid", "_k"], how="left")
    with gzip.open(os.path.join(out, "events.csv.gz"), "wt", encoding="utf-8") as fh:
        EVo.to_csv(fh, index=False)
    verdict = {}
    for nm in ("探索", "確認"):
        r = FR[FR["段"] == nm].iloc[0]
        verdict[nm] = {"n_eff": int(r["n_eff"]), "S可判的月數": int(r["S可判的月數"]), "能判": bool(r["n_eff"] >= NEFF_MIN)}
    JS = {"性質": "頂部樣子 seq1 頻率表乾跑（⛔ 未讀、未算任何進場後報酬）", "登錄": f"台股策略線 seq1 sha {REG_SHA}（{reg}）", "裁定": "seq441（N_前段 +1、最多暫定）",
          "origin/main": sha, "面板快照": {"A": RB3.SHA_A, "B": RB3.SHA_B, "比對": SAME}, "接縫": seam, "乾跑": bool(a.limit), "乾跑股": [SIDS[i] for i in idx_run] if a.limit else None,
          "母體符合列": len(EV), "入判列": int(len(J)), "能否判": verdict,
          "全段能判": all(v["能判"] for v in verdict.values()), "距一年高點重算對面板最大相對差": hi_diff, "必附": NOTES,
          "讀法": __doc__.split("═══ 讀法")[1], "時間": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M"), "耗時秒": round(time.time() - t0)}
    json.dump(JS, open(os.path.join(out, "freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[能否判] {verdict}")
    log(f"[完] {time.time() - t0:.0f}s ⇒ {out}")
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
