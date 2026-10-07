# -*- coding: utf-8 -*-
"""USREG-A3 g3 組（組合層、條件出場四件）：A3-6 訊號對訊號交易系統、A3-7 訊號系統均線出場、A3-14 外部作者六顆、A3-15 外部作者追加三顆。

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSA3_g3 --run   [--procs 2] [--limit 60 --seeds 4 --fake 3]
    ...                                                                                         --check

判準：美股登錄 USREG-A3A4 seq1（sha 0dc16d3267725d7c）＋seq2（sha bc0927fed5996fd4）；裁定 seq318（發號）、seq319（Q1 早年段、Q12 A3-6 退化、Q13 外部作者）、
      seq316（只 S&P 400 與合併兩者都過才合格）、seq308（條件出場主臂）、seq242（組合層預設）。共同讀法 ＝ backtest/researchUSA3_core.py C1～C10（照用）。
開跑前清單（⛔ 照它、不改）：backtest/researchUSA34_prep.py（P1～P20、px_one 偵測寫法）、resultsUSA34/prep/PREP_REPORT.md、清單_29件.csv、退化格清單.csv。
台股原登錄（⭐ 判定規則照它移植）：
  A3-6  登錄全文-訊號對訊號交易系統_築底反轉進高檔出_登錄_台股策略線_seq1（sha 8e8595d3ce5f3c51）；原程式 researchSig.py
  A3-7  登錄全文-訊號系統均線出場_10與20與60日線_登錄_台股策略線_seq1（sha 39c29b1596b81dba）；原程式 researchSigMA.py
  A3-14 登錄全文-外部作者批七顆_波段醫生與楊爸_登錄_台股策略線_seq1（sha 62e4026f16879fed）；原程式 researchExtAuth.py（W2 年線戰法另立 A4-9，本檔只用它當出場顆基準的一員）
  A3-15 登錄全文-外部作者追加三顆_量縮補量跌與三線反紅與假跌破_登錄_台股策略線_seq1（sha 48cbe3c0f1fccd3e）；原程式 researchExtAuth2.py
既有程式只 import、⛔ 一行未改：researchUSA3_core、researchUSA34_prep（load_fund、yoy_of、q_last、spy_layer）、researchSig（sig_days、stop_days、E1／E2／XS）、
      researchExtAuth（detect、y4_day）、researchExtAuth2（detect_new）、research11.simulate_mtm、researchRev.ma_fsum。

⛔⛔ 私有資料：resultsUSA34/A3/A3-*.json 只放彙總；逐筆列、逐種子結果、訊號快取寫 ~/us_work/a3/g3/（repo 外），json 列 sha。

═══ g3 補讀法（執行者寫死於 2026-10-07 12:20（台北）；寫死前 ⛔ 沒看任何 A3 美股報酬）═══
 G1 段：探索 2016-01-04～2021-12-31（挑）｜確認 2022-01-03～2026-09-30（判）（core C1）；各段獨立起跑、期初全現金；進場 e＝t＋1 ∈ 段內（t 可為前一段最後一天）；
    段尾仍持有 ⇒ 段尾收盤結算（core C6），件數必報。台股原「早年段」美股沒有 ⇒ 不跑、結果句標「缺早年段」；A3-14／15 原「主窗全段另判、兩段都過才合格」
    ＝ 兩段取較嚴 ⇒ seq319 Q1：只看確認段（主窗全段 ⛔ 不跑）。
 G2 三欄（core C2、C3）：候選 ＝ 訊號日 t 當天在該欄指數（合併 member、只 S&P 400 m4、只 S&P 500 m5）且 t 有有效 K 棒；挑格只在【合併】欄探索段做，
    同一格在合併、只 400 兩欄判（只 500 描述）。判定格在只 400 欄依構造退化（事件不足）⇒ 該欄不可判定 ⇒ 依構造最多「事後擴母體」。
 G3 訊號（只 import、⛔ 不改）：A3-6／7 ＝ researchSig.sig_days；A3-14／15 ＝ researchExtAuth.detect、researchExtAuth2.detect_new（呼叫法照 prep px_one：
    還原 O、H、low_aligned L、C、拆股調整量 V；有效 K 棒空間偵測再對回日曆）。均線跌破 ＝ detect 的 MA{k}（researchRev.ma_fsum、由上往下穿越）。
    W2（只當 A3-14 出場顆／A3-15 S1 基準「五顆任一」的一員）＝ prep P20 與 stage_fund 同式：最新一季季營收 YoY ＞ 0 或 季淨利由 ≤0 轉 ＞0（prep.load_fund／yoy_of／q_last）。
 G4 進場列：A3-6、A3-7 ＝ researchSig.build_rows 規則（E 族任一、同日同檔有本格出場訊號 ⇒ 該進場訊號不進、已持有不加碼〔引擎 held〕、賣出可再進、不設冷卻）；
    A3-7 並列「收盤 ＜ MA 即賣」＝ researchSigMA 讀法（不套同日不進）。A3-14／15 進場顆 ＝ researchExtAuth.entry_rows 規則（訊號日同時跌破照進、只看持有期間）；
    O1 ＝ researchExtAuth2.o1_rows 規則（自帶出場 ＝ 持有期間收盤 ＜ 跌破日 k 最低）；出場顆基準 ＝ researchExtAuth.base_rows（W1、W2、Y1、Y2 進、Y3 任一，同檔同日一列）。
    T＋1（進場日）沒有有效開盤 ⇒ 剔除（P4）。
 G5 出場執行：出場條件 d（收盤判、d ≥ e）⇒ d＋1 開盤賣；d＋1 ＞ 段尾或沒有 ⇒ 段尾收盤結算（core exit_after／gross_exit）；⛔ 不設最長天數。
    多個出場條件「誰先到先出」，同日平手照台股原程式的先後（A3-6：訊號 → 停損 → 停利；均線基準 vs 疊加條件：均線先〔原程式 min((d, 名)) 的字串序〕）。
 G6 組合引擎 ＝ core C5（8 槽、等權、種子 102000＋r、200 顆、成本 0.05%、tradable＋delist、cash_mode zero）；台股原 10 檔、種子 1000＋r、成本 0.585% ⇒ 偏離照列。
    判準 ＝ ^SP500TR 同段（年化 ＞ 基準 且 年化÷|回落| ≥ 基準比值 ⇒ 合格；只前者 ⇒ 另列）；挑法照原登錄：過判準者取比值最高；都沒過取比值最高（同分取年化高）。
 G7 硬斷點：一列的 [t−60, 出場日] 碰到轉接層硬斷點（pb）⇒ 剔除（W1b W5 同精神；60 根 ≈ 訊號回看）；C8 敏感度臂再加 S&P 400 未確認 |ret|＞50% 列。
 G8 退化（照原登錄＋seq319）：
    A3-6：Q12 ⇒ 探索段（合併、事件為單位，P18 同式）段尾未出場 ＞ 50% 的出場格 ＝ 退化格，照報（照跑描述）、⛔ 不參與挑選（只用段尾門檻，＝ prep 退化格清單 3 格；本程式重算核對）。
    A3-7：seq246 ⇒ 每檔每股票年均線穿越 ＜ 1 或 探索段段尾未出場 ＞ 50%（事件為單位，P18）⇒ 不進挑選；某族 3 格全退化 ⇒ 該族依構造不可判定、不計 N。
    A3-14／15 進場顆：seq248 ④ 主窗（2016-01-04～2026-09-30）事件 ＜ 200 或年均（÷ 窗長／252）＜ 10 ⇒ 該顆該欄全部格退化（＝ prep 清單）；另探索段段尾未出場 ＞ 50% 的格剔除。
    出場顆（Y2 出、Y4 兩臂、Y5、S1）：主窗「有效觸發列」（基準列中本條先於基準出場觸發的列）＜ 200 或年均 ＜ 10 ⇒ 該格退化；探索段段尾未出場 ＞ 50% ⇒ 剔除。
    以上逐欄（合併、只 400）判；合併欄一顆全部格退化 ⇒ 該顆依構造不可判定（N 照計，seq248 ⑦／seq319 Q13）。
 G9 出場顆改造（⭐ seq308 條件出場主臂；brief「台股原文的固定天數臂也降描述」）：Y2 出／Y4（MA5、MA10 兩臂）／Y5 原「基準抱 H∈{20,60,120} 日＋本條」⇒
    主臂改「基準（五顆任一）跌破 MA10／20／60（無天數上限）＋本條，誰先到先出」，格數不變（3／6／3）＝ 與 A3-15 S1 原文的均線基準 3 格同構；
    原 H 基準格（含 S1 的 H 格）降描述（只在確認段合併欄跑）。Y2 一顆 ＝ Y2 進 3 格 ∪ Y2 出 3 格照同一挑法挑 1（台股原程式讀法 Q1）。
    Y4 觸發 ＝ researchExtAuth.y4_day（買價 ＝ 進場日開盤；以之前各根收盤最高報酬判段）。
 G10 A3-6 停損停利 16 組 ＝ researchSig.stop_days 原式（SL10／SL20 收盤 ≤ 進場價×0.9／0.8；AT2 Wilder 14 的 2×ATR 追蹤；TP30 收盤 ≥ ×1.3；TR20 收盤 ≤ 持有以來最高×0.8；
    TP50h ＝ 引擎 trim_rule gain 0.5 賣半）；觸發 d ⇒ d＋1 開盤；32 選 1（E1、E2 各 16，含「無」）；挑中「無」⇒ N 不另加。
 G11 SPY 層（0050 層 → SPY 層）：SPY 還原 OHLC（prep.spy_layer 同一份訊號）；SPY 自己的 E1∪E2 ⇒ 次日開盤全倉、X 任一 ⇒ 次日開盤全賣持現金（0 息）；
    researchSig.l0050_run 同式、成本 0.05%；判 ＝ 確認段年化 ＞ 一直抱 SPY（含息）。單一標的沒有只 S&P 400 欄 ⇒ seq316「全批一律」⇒ 贏了也依構造最多「事後擴母體」。
    A3-7 的 SPY 層（各均線）照台股原程式只描述。
 G12 假訊號臂（照原登錄；描述、不計 N）：判定格在合併、只 400 兩欄各 1,000 次；A ＝ 同進場（或同基準）＋隨機出場（持有天數抽自本格 200 顆已出場、非段尾結算的交易）；
    B（只 A3-6）＝ 同月同筆數從該欄母體隨機抽進場日（排除本格出場訊號日、T＋1 要有有效開盤、硬斷點照 G7）＋同出場規則。
    抽樣 rng ＝ default_rng([20261007, i])、引擎種子 102000＋(i mod 200)；p ＝ 隨機年化 ≥ 本格年化中位的比例；合併欄 p ≥ 0.05 ⇒ 結果句前加「隨機也做得到」。
 G13 描述臂（⛔ 不判）：固定持有 20／60／120／240 日（core fixed_rows，判定格、確認段、合併欄）；|ret|＞50% 剔除敏感度（判定格、兩欄）；
    合併欄「合格／另列」的判定格 ⇒ 成本 0.02／0.10%、槽數 4／16 敏感度（seq242 跟進）。「訊號出場 vs 固定抱 60 天」年化差只放描述欄、⛔ 不當評價（C6）。
 G14 單筆層、早年段、放棄組報酬（Y1／F1／O1）只描述的部分本檔不做（組合層主臂）；F1 確認率、與多頭吞噬 ±2 日重疊率、O1 站回率、S1 每檔每年觸發照報（事件數，不讀報酬）。
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import pickle
import sys
import time
from collections import Counter, defaultdict
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
from backtest import researchUSA3_core as C          # ⚠ 先 import（內含 A2.install()）
from backtest import researchUSA34_prep as PREP
import researchSig as RS
import researchExtAuth as EA
import researchExtAuth2 as EA2

R11, W, U, RV = C.R11, C.W, C.U, RS.RV
READ_TS = "2026-10-07 12:20（台北）"
WORK = os.path.join(C.WORK, "g3")
OUTD = C.OUT
N_FAKE = 1000
FAKE_SEED = 20261007
LOOKBACK = 60
BIGI = 10 ** 9
EXOPT = ("MA10", "MA20", "MA60")
ENT5 = ("W1", "W2", "Y1", "Y2in", "Y3")
REGTW = {"A3-6": ("登錄全文-訊號對訊號交易系統_築底反轉進高檔出_登錄_台股策略線_seq1_sha8e8595d3ce5f3c51-9449B-20260927-1710.md", "8e8595d3ce5f3c51"),
         "A3-7": ("登錄全文-訊號系統均線出場_10與20與60日線_登錄_台股策略線_seq1_sha39c29b1596b81dba-5446B-20260927-1910.md", "39c29b1596b81dba"),
         "A3-14": ("登錄全文-外部作者批七顆_波段醫生與楊爸_登錄_台股策略線_seq1_sha62e4026f16879fed-10494B-20260927-1910.md", "62e4026f16879fed"),
         "A3-15": ("登錄全文-外部作者追加三顆_量縮補量跌與三線反紅與假跌破_登錄_台股策略線_seq1_sha48cbe3c0f1fccd3e-4973B-20260927-1914.md", "48cbe3c0f1fccd3e")}
NAMES = {"A3-6": "訊號對訊號交易系統（E1／E2 進、X 出、可再進；停損停利 16 組；SPY 層）", "A3-7": "訊號系統均線出場（跌破 10／20／60 日線）",
         "A3-14": "外部作者七顆之六顆（W1、Y1～Y5；W2 另立 A4-9）", "A3-15": "外部作者追加三顆（S1、F1、O1）"}
XNAME = {"ANY": "X 任一", "VSc": "高檔爆量長上影（確認）", "TD": "TD 9 賣", "KD": "KD 頂背離", "MACD": "MACD 頂背離", "RSI": "RSI 70 跌回",
         "EVE": "黃昏之星", "ENG": "空頭吞噬", "TL": "上升趨勢線跌破"}
G = {}


def log(x):
    print(x, flush=True)
    try:
        with open(os.path.join(WORK, "run%s.log" % G.get("tag", "")), "a", encoding="utf-8") as f:
            f.write(time.strftime("%H:%M:%S ") + x + "\n")
    except OSError:
        pass


# ═════════════ 讀檔、訊號 ═════════════
def setup(lim=None):
    meta, ST = C.load_cache()
    if lim:
        ST = {k: ST[k] for k in sorted(ST)[:lim]}
    G.update(meta=meta, ST=ST, cal=meta["cal"], w0=meta["w0"], w1=meta["w1"], sp=meta["sp"], c0=meta["c0"], lim=lim, tag=("_lim%d" % lim) if lim else "")
    G["sids"] = sorted(ST)
    G["cspb"] = {s: np.cumsum(ST[s]["pb"].astype(np.int64)) for s in G["sids"]}
    G["csf50"] = {s: np.cumsum((ST[s]["pb"] | ST[s]["f50"]).astype(np.int64)) for s in G["sids"]}
    os.makedirs(WORK, exist_ok=True)


def _sig_one(t):
    d = G["ST"][t]; cal = G["cal"]; n = len(cal)
    O, H, L, Cc, V, valid, bars = d["O"], d["H"], d["L"], d["C"], d["V"], d["valid"], d["bars"]
    v0 = np.nan_to_num(V)
    fd = pd.DataFrame({"open": O, "high": H, "low": L, "close": Cc, "volume": v0, "traded": valid}, index=cal)
    SGd, _ = RS.sig_days(O, H, L, Cc, v0, O, H, L, Cc, fd, set(cal[d["pb"]]), n)
    out = {k: np.asarray(v, np.int64) for k, v in SGd.items()}
    ob, hb, lb, cb, vb = O[bars], H[bars], L[bars], Cc[bars], v0[bars]
    tc = lambda a: bars[np.asarray(a, int)].astype(np.int64) if len(a) else np.zeros(0, np.int64)
    ex, _ = EA.detect(ob, hb, lb, cb, vb)
    for k in ("W1", "Y1", "Y2in", "Y2out", "Y3", "Y5", "MA5", "MA10", "MA20", "MA60", "BL10", "BL20", "BL60"):
        out[k] = tc(ex[k])
    w2c = ex["W2c"]
    out["W2c"] = np.stack([bars[w2c[:, 0]], bars[w2c[:, 1]]], 1).astype(np.int64) if len(w2c) else np.zeros((0, 2), np.int64)
    ex2 = EA2.detect_new(ob, hb, lb, cb, vb)
    for k in ("S1", "F1", "F1c", "O1", "O1_k"):
        out[k] = tc(ex2[k])
    out["O1_low"] = np.asarray(ex2["O1_low"], float)
    oa = ex2["O1_all"]
    out["O1_all"] = (np.stack([bars[oa[:, 0]], np.where(oa[:, 1] >= 0, bars[np.maximum(oa[:, 1], 0)], -1)], 1).astype(np.int64)
                     if len(oa) else np.zeros((0, 2), np.int64))
    return t, out


def signals(procs=2):
    p = os.path.join(WORK, "sig%s.pkl" % G["tag"])
    if os.path.exists(p):
        SIG = pickle.load(open(p, "rb"))
    else:
        t0 = time.time(); SIG = {}
        with Pool(procs) as pool:
            for i, (t, out) in enumerate(pool.imap_unordered(_sig_one, G["sids"], chunksize=8)):
                SIG[t] = out
                if (i + 1) % 200 == 0:
                    log("[訊號] %d／%d %.0fs" % (i + 1, len(G["sids"]), time.time() - t0))
        # W2 基本面（prep P20 ＝ stage_fund 同式）
        F = PREP.load_fund(G["cal"])
        cal_days = G["cal"].values.astype("datetime64[D]").astype(np.int64)
        cnt = Counter()
        for t, S in SIG.items():
            keep = []
            for s_, j in S["W2c"]:
                sd_ = int(cal_days[s_])
                y = PREP.yoy_of(F, "revenue", t, int(s_), sd_)
                qn = PREP.q_last(F, "net_income", t, int(s_), 2, edays=sd_)
                turn = bool(qn[1][1] > 0 and qn[1][0] <= 0) if qn is not None else None
                ok = bool((np.isfinite(y) and y > 0) or turn)
                st = G["ST"][t]
                if G["w0"] <= j <= G["w1"] - 1 and st["member"][j] and st["valid"][j]:
                    cnt["候選（技術面成立）"] += 1; cnt["成立"] += int(ok)
                if ok:
                    keep.append(int(j))
            S["W2"] = np.array(sorted(set(keep)), np.int64)
        SIG["__W2__"] = dict(cnt)
        pickle.dump(SIG, open(p, "wb"), protocol=4)
        log("[訊號] %d 檔 %.0fs｜W2 %s" % (len(SIG) - 1, time.time() - t0, dict(cnt)))
    G["W2cnt"] = SIG.pop("__W2__", {})
    G["SIG"] = SIG
    G["sig_sha"] = C.sha256f(p)
    return SIG


def inwin_count(code, col):
    w0, w1 = G["w0"], G["w1"]; n = 0
    for s, S in G["SIG"].items():
        st = G["ST"][s]; M = colmask(st, col)
        a = S.get(code, np.zeros(0, int))
        a = a[(a >= w0) & (a <= w1)]
        n += int((M[a] & st["valid"][a]).sum())
    return n


def colmask(st, col):
    return st["member"] if col == "合併" else (st["m4"] if col == "只400" else st["m5"])


def stock_years(col="合併"):
    w0, w1 = G["w0"], G["w1"]
    return sum(int((G["ST"][s]["valid"] & colmask(G["ST"][s], col))[w0:w1 + 1].sum()) for s in G["sids"]) / 252.0


def verify_prep():
    """訊號重現核對：與 prep 的事件數（A3-6_訊號頻率、A3-14_A3-15 外部作者事件數、W2）逐列比。"""
    P = os.path.join(os.path.dirname(OUTD), "prep")
    out = {"比對列": 0, "不同": [], "W2": {"本程式": G["W2cnt"], "prep": {"候選（技術面成立）": 1205, "成立": 723}}}
    if G["lim"]:
        out["註"] = "小樣本試跑 ⇒ 不比"
        return out
    a = pd.read_csv(os.path.join(P, "A3-6_訊號頻率.csv"), encoding="utf-8-sig")
    for r in a.itertuples():
        for col, v in (("合併", r.窗內在母體事件), ("只400", r.只400)):
            m = inwin_count(r.訊號, col); out["比對列"] += 1
            if m != int(v):
                out["不同"].append((r.訊號, col, m, int(v)))
    b = pd.read_csv(os.path.join(P, "A3-14_A3-15_外部作者_事件數.csv"), encoding="utf-8-sig")
    for r in b.itertuples():
        for col, v in (("合併", r[3]), ("只400", r[5])):
            m = inwin_count(r.顆, col); out["比對列"] += 1
            if m != int(v):
                out["不同"].append((r.顆, col, m, int(v)))
    out["W2_同"] = (G["W2cnt"].get("候選（技術面成立）") == 1205 and G["W2cnt"].get("成立") == 723)
    return out


# ═════════════ 列（進場、出場觸發、結算）═════════════
def first_ge(arr, e, hi):
    i = int(np.searchsorted(arr, e))
    return int(arr[i]) if i < len(arr) and arr[i] <= hi else -1


def union_days(S, keys):
    arrs = [np.asarray(S.get(k, np.zeros(0, int)), np.int64) for k in keys]
    return np.unique(np.concatenate(arrs)) if arrs else np.zeros(0, np.int64)


def entry_rows(keys, s0, s1, xdrop=None):
    """訊號日 t（keys 任一）⇒ 列 (sid, t, e)；e＝t＋1 ∈ [s0, s1]、t 在母體（合併）且有效、e 有有效開盤。
    xdrop：callable(S) ⇒ 該檔的出場訊號日陣列；t ∈ 其中 ⇒ 不進（researchSig.build_rows 同日不進）。回 DataFrame 與同日不進數。"""
    rows = []; drop = 0
    for s in G["sids"]:
        S = G["SIG"][s]; st = G["ST"][s]
        ent = union_days(S, keys) if isinstance(keys, (list, tuple)) else keys(S)
        ent = ent[(ent + 1 >= s0) & (ent + 1 <= s1)]
        if not len(ent):
            continue
        ent = ent[st["member"][ent] & st["valid"][ent]]
        if xdrop is not None and len(ent):
            xd = xdrop(S); same = np.isin(ent, xd); drop += int(same.sum()); ent = ent[~same]
        for t in ent:
            e = int(t) + 1
            o = st["opens"][e]
            if not (np.isfinite(o) and o > 0):
                continue
            rows.append((s, int(t), e, bool(st["m4"][t]), bool(st["m5"][t])))
    return pd.DataFrame(rows, columns=["sid", "t", "e", "m4", "m5"]), drop


def trig_first(R, xfun, hi):
    """每列第一個 ≥ e 的出場訊號（≤ hi）；xfun(S) ⇒ 該檔出場日陣列。"""
    out = np.full(len(R), -1, np.int64); cache = {}
    for i, (s, e) in enumerate(zip(R["sid"].to_numpy(), R["e"].to_numpy())):
        if s not in cache:
            cache[s] = np.asarray(xfun(G["SIG"][s]), np.int64)
        out[i] = first_ge(cache[s], int(e), hi)
    return out


def finalize(R, s1, trig, names):
    """trig：{名: 觸發日陣列（−1 無）}，names 決定同日平手的先後（先列者勝）。⇒ xpos、g、endhold、why、pb、f50。"""
    n = len(R)
    if n == 0:
        return R.assign(xpos=[], g=[], endhold=[], why=[], pbx=[], f50x=[], d=[])
    M = np.column_stack([np.where(np.asarray(trig[k]) < 0, BIGI, np.asarray(trig[k])) for k in names])
    j = M.argmin(axis=1); d = M[np.arange(n), j]
    has = d < BIGI
    ok = has & (d + 1 <= s1)
    xpos = np.where(ok, d + 1, s1).astype(np.int64)
    why = np.where(ok, np.asarray(names, object)[j], "段尾")
    g = np.empty(n); pbx = np.zeros(n, bool); f5 = np.zeros(n, bool)
    sids = R["sid"].to_numpy(); ts = R["t"].to_numpy(); es = R["e"].to_numpy()
    for i in range(n):
        s = sids[i]; e = int(es[i]); x = int(xpos[i]); st = G["ST"][s]
        g[i] = C.gross_exit(st, e, x, not ok[i])
        lo = max(int(ts[i]) - LOOKBACK, 0)
        cs = G["cspb"][s]; pbx[i] = (cs[x] - (cs[lo - 1] if lo > 0 else 0)) > 0
        cf = G["csf50"][s]; f5[i] = (cf[x] - (cf[lo - 1] if lo > 0 else 0)) > 0
    return R.assign(xpos=xpos, g=g, endhold=~ok, why=why, pbx=pbx, f50x=f5, d=np.where(has, d, -1))


def pb_hit(s, t, x, f50=False):
    lo = max(int(t) - LOOKBACK, 0); cs = (G["csf50"] if f50 else G["cspb"])[s]
    return bool((cs[x] - (cs[lo - 1] if lo > 0 else 0)) > 0)


def col_sel(F, col, f50=False):
    m = np.ones(len(F), bool) if col == "合併" else np.array(F["m4" if col == "只400" else "m5"].to_numpy(bool), copy=True)
    m &= ~F["pbx"].to_numpy(bool)
    if f50:
        m &= ~F["f50x"].to_numpy(bool)
    return F[m]


def mk_arm(F, seg, cost=None, kw=None, slots=None, pool=False):
    F = F.sort_values(["e", "sid"])
    sig = pd.DataFrame({"sid": F["sid"].to_numpy(), "entry_pos": F["e"].to_numpy(np.int64),
                        f"xpos_{C.RULE}": F["xpos"].to_numpy(np.int64), f"g_{C.RULE}": F["g"].to_numpy(float)})
    keys = list(zip(F["sid"].to_numpy(), F["e"].to_numpy(np.int64).tolist()))
    a = {"sig": sig, "endhold": dict(zip(keys, F["endhold"].to_numpy(bool).tolist())), "why": dict(zip(keys, F["why"].tolist())),
         "seg": seg, "n_rows": int(len(F)), "pool": pool}
    if cost is not None:
        a["cost"] = cost
    if kw:
        a["kw"] = kw
    if slots:
        a["slots"] = slots
    return a


# ═════════════ 引擎（core C5 同一套；多記勝率、再進場、出場原因、現金比例）═════════════
def _one(args):
    seed, key = args
    a = G["arms"][key]; S = C._S
    R11.COST = a.get("cost", C.COST)
    aud = []
    try:
        out = R11.simulate_mtm(a["sig"], C.RULE, a.get("slots", C.N_SLOTS), np.random.default_rng(seed), S["closes"], S["opens"], S["ncal"],
                               return_equity=True, pick=None, d_max=None, queue_days=0, cash_mode="zero",
                               tradable=S["trad"], delist=S["dl"], audit=aud, **a.get("kw", {}))
    finally:
        R11.COST = C.COST
    return _stats(key, seed, a, out, aud)


def _stats(key, seed, a, out, aud):
    eq = np.asarray(out["equity"], float); s0, s1 = a["seg"]
    c, m = W.window_metrics(eq, s0, s1)
    cl = C._S["closes"]
    openb = {}; done = set(); tr = []
    for x in aud:
        s = x["sid"]; t = int(x["t"])
        if x["side"] == "buy":
            if x.get("kind") == "add":
                continue
            openb[s] = [t, float(x["amt"]), 0.0, 0.0, s in done]
        elif x["side"] == "sell":
            b = openb.get(s)
            if b is None:
                continue
            b[2] += float(x["amt"]); b[3] += float(x.get("cost", 0.0))
            if x.get("kind") == "trim":
                continue
            net = (b[2] - b[3]) / b[1] - 1.0
            endh = bool(a["endhold"].get((s, b[0]), False) and t >= s1)
            why = "段尾" if endh else a["why"].get((s, b[0]), "")
            seg_ = cl[s][b[0]:t + 1]; pk = np.nanmax(seg_) if len(seg_) else np.nan
            gap = float(x["px"]) / pk - 1.0 if (np.isfinite(pk) and pk > 0 and np.isfinite(x["px"])) else np.nan
            tr.append((b[0], t, net, b[4], why, endh, gap))
            done.add(s); del openb[s]
    hold = np.array([t - b for b, t, *_ in tr], float)
    gaps = np.array([z[6] for z in tr], float)
    cl_ = [z for z in tr if not z[5]]
    net = np.array([z[2] for z in cl_], float); re = np.array([z[3] for z in cl_], bool)
    hv = out.get("hold_val")
    seg = slice(s0, s1 + 1)
    with np.errstate(invalid="ignore", divide="ignore"):
        cash = float(np.nanmean(1.0 - np.asarray(hv, float)[seg] / eq[seg])) if hv is not None else np.nan
    cntd = np.zeros(len(eq) + 2)
    for b, t, *_ in tr:
        cntd[b] += 1; cntd[min(t, s1 + 1)] -= 1
    for s, b in openb.items():
        cntd[b[0]] += 1; cntd[s1 + 1] -= 1
    held = float(np.cumsum(cntd)[seg].mean())
    r = {"key": key, "seed": seed, "cagr": c, "mdd": m, "trades": out["trades"], "slot_use": out["slot_use"],
         "hold_mean": float(hold.mean()) if len(hold) else np.nan, "hold_med": float(np.median(hold)) if len(hold) else np.nan,
         "hold_p10": float(np.percentile(hold, 10)) if len(hold) else np.nan, "hold_p90": float(np.percentile(hold, 90)) if len(hold) else np.nan,
         "hold_max": float(hold.max()) if len(hold) else np.nan, "n_end_hold": int(sum(1 for z in tr if z[5]) + len(openb)),
         "peak_gap_med": float(np.nanmedian(gaps)) if np.isfinite(gaps).any() else np.nan,
         "n_closed": int(len(cl_)), "win": int((net > 0).sum()), "net_sum": float(net.sum()),
         "re_n": int(re.sum()), "re_win": int((net[re] > 0).sum()), "re_sum": float(net[re].sum()),
         "why": dict(Counter(z[4] for z in cl_)), "cash": cash, "held": held, "n_trades_all": int(len(tr) + len(openb))}
    if a.get("pool") and seed < C.SEED0 + C.NSEED:
        r["pool"] = np.array([t - b for b, t, *_ in cl_], np.int32)
    return r


def run_arms(arms, procs, nseed, tag=""):
    if not arms:
        return {}
    G["arms"] = arms
    jobs = [(C.SEED0 + r, k) for k in arms if arms[k]["n_rows"] > 0 for r in range(nseed)]
    res = {k: [] for k in arms}
    t0 = time.time()
    if procs <= 1:
        for j in jobs:
            x = _one(j); res[x["key"]].append(x)
    else:
        with Pool(procs) as pool:
            for x in pool.imap_unordered(_one, jobs, chunksize=4):
                res[x["key"]].append(x)
    for k in res:
        res[k].sort(key=lambda x: x["seed"])
    log("  [引擎 %s] %d 臂 × %d 顆 %.0fs" % (tag, len(arms), nseed, time.time() - t0))
    return res


def agg(rows, bref, seg):
    if not rows:
        return {"標籤": "不可判定", "註": "無訊號"}
    out = C.pf_agg(rows, bref)
    yrs = (seg[1] - seg[0] + 1) / 252.0
    nc = sum(x["n_closed"] for x in rows); rn = sum(x["re_n"] for x in rows)
    why = Counter()
    for x in rows:
        why.update(x["why"])
    out.update({"每年交易（每顆中位）": float(np.median([x["n_trades_all"] for x in rows])) / yrs,
                "勝率（已出場）": sum(x["win"] for x in rows) / nc if nc else np.nan,
                "平均淨報酬（已出場）": sum(x["net_sum"] for x in rows) / nc if nc else np.nan,
                "再進場_每顆筆數": rn / len(rows), "再進場_平均淨報酬": sum(x["re_sum"] for x in rows) / rn if rn else np.nan,
                "再進場_勝率": sum(x["re_win"] for x in rows) / rn if rn else np.nan,
                "首次進場_平均淨報酬": (sum(x["net_sum"] for x in rows) - sum(x["re_sum"] for x in rows)) / (nc - rn) if nc - rn else np.nan,
                "首次進場_勝率": (sum(x["win"] for x in rows) - sum(x["re_win"] for x in rows)) / (nc - rn) if nc - rn else np.nan,
                "出場原因占比": {k: round(v / nc, 4) for k, v in why.most_common()} if nc else {},
                "現金比例（平均）": float(np.nanmean([x["cash"] for x in rows])), "平均持股檔數": float(np.mean([x["held"] for x in rows])),
                "訊號列數": None})
    return out


def hold_pool(rows):
    ps = [x["pool"] for x in rows if "pool" in x]
    return np.concatenate(ps) if ps else np.zeros(0, np.int32)


def seeds_of(rows):
    return [(int(x["seed"]), float(x["cagr"]), float(x["mdd"])) for x in rows]


def pick(cands):
    """cands：[(名, agg)] ⇒ 原登錄挑法：過判準（合格）的裡取比值最高；都沒過取比值最高（同分取年化高）。"""
    cands = [(k, c) for k, c in cands if "比值" in c and np.isfinite(c["比值"])]
    if not cands:
        return None
    ok = [(k, c) for k, c in cands if c.get("標籤") == "合格"]
    pool = ok if ok else cands
    return sorted(pool, key=lambda kc: (-kc[1]["比值"], -kc[1]["年化中位"]))[0][0]


def brefs():
    cal = G["cal"]
    return {"探索": C.bench_row(cal, G["w0"], G["sp"]), "確認": C.bench_row(cal, G["c0"], G["w1"])}


def segs():
    return {"探索": (G["w0"], G["sp"]), "確認": (G["c0"], G["w1"])}


# ═════════════ 假訊號 ═════════════
def _fake_mats():
    if "OPN" not in G:
        G["sidx"] = {s: i for i, s in enumerate(G["sids"])}
        G["OPN"] = np.column_stack([G["ST"][s]["opens"] for s in G["sids"]])
        G["CLS"] = np.column_stack([G["ST"][s]["closes"] for s in G["sids"]])


def _engine_cagr(sid, e, x, g, seg, seed):
    o = np.argsort(e * 4096 + np.array([G["sidx"][s] for s in sid]), kind="stable")
    sig = pd.DataFrame({"sid": np.asarray(sid, object)[o], "entry_pos": np.asarray(e)[o], f"xpos_{C.RULE}": np.asarray(x)[o], f"g_{C.RULE}": np.asarray(g)[o]})
    S = C._S
    out = R11.simulate_mtm(sig, C.RULE, C.N_SLOTS, np.random.default_rng(seed), S["closes"], S["opens"], S["ncal"], return_equity=True,
                           pick=None, d_max=None, queue_days=0, cash_mode="zero", tradable=S["trad"], delist=S["dl"])
    return W.window_metrics(np.asarray(out["equity"], float), *seg)[0]


def _gross_vec(ci, e, x, endh):
    o = G["OPN"][e, ci]; ox = G["OPN"][x, ci]; cx = G["CLS"][x, ci]
    px = np.where(endh, cx, np.where(np.isfinite(ox) & (ox > 0), ox, cx))
    return px / o - 1.0


def _fakeA(i):
    J = G["FJ"]; rng = np.random.default_rng([FAKE_SEED, i]); s0, s1 = J["seg"]
    h = rng.choice(J["pool"], size=len(J["e"]), replace=True) if len(J["pool"]) else np.full(len(J["e"]), BIGI)
    x = J["e"] + h; endh = x > s1; x = np.where(endh, s1, x)
    g = _gross_vec(J["ci"], J["e"], x, endh)
    return _engine_cagr(J["sid"], J["e"], x, g, J["seg"], C.SEED0 + i % C.NSEED)


def _fakeB(i):
    J = G["FJ"]; rng = np.random.default_rng([FAKE_SEED, 10 ** 6 + i]); s0, s1 = J["seg"]
    sid = []; e = []
    for mo, nm in J["per_m"].items():
        cm = J["cand"].get(mo)
        if cm is None or not len(cm[0]):
            continue
        k = rng.choice(len(cm[0]), size=min(nm, len(cm[0])), replace=False)
        sid.extend(cm[0][k].tolist()); e.extend((cm[1][k] + 1).tolist())
    sid = np.asarray(sid, object); e = np.asarray(e, np.int64)
    xs = np.empty(len(e), np.int64); endh = np.zeros(len(e), bool); keep = np.ones(len(e), bool)
    for j in range(len(e)):
        s = sid[j]; d = first_ge(J["X"][s], int(e[j]), s1)
        if d >= 0 and d + 1 <= s1:
            xs[j] = d + 1
        else:
            xs[j] = s1; endh[j] = True
        cs = G["cspb"][s]; lo = max(int(e[j]) - 1 - LOOKBACK, 0)
        keep[j] = (cs[xs[j]] - (cs[lo - 1] if lo > 0 else 0)) == 0
    sid, e, xs, endh = sid[keep], e[keep], xs[keep], endh[keep]
    ci = np.array([G["sidx"][s] for s in sid], np.int64)
    g = _gross_vec(ci, e, xs, endh)
    return _engine_cagr(sid, e, xs, g, J["seg"], C.SEED0 + i % C.NSEED)


def fake_run(kind, J, nfake, procs):
    _fake_mats()
    J["ci"] = np.array([G["sidx"][s] for s in J["sid"]], np.int64) if "sid" in J else None
    G["FJ"] = J
    f = _fakeA if kind == "A" else _fakeB
    t0 = time.time()
    if procs <= 1:
        v = [f(i) for i in range(nfake)]
    else:
        with Pool(procs) as pool:
            v = pool.map(f, range(nfake), chunksize=8)
    log("  [假訊號 %s] %d 次 %.0fs" % (kind, nfake, time.time() - t0))
    return np.asarray(v, float)


def fake_summary(v, m, bref, nfake, pool_n=None):
    out = {"次數": nfake, "隨機年化中位": float(np.median(v)), "p10": float(np.percentile(v, 10)), "p90": float(np.percentile(v, 90)),
           "p（隨機 ≥ 本格）": float((v >= m).mean()), "隨機贏基準年化比例": float((v > bref["年化"]).mean())}
    if pool_n is not None:
        out["持有天數池"] = int(pool_n)
    return out


def fakeA_job(F, pool, seg):
    return {"sid": F["sid"].to_numpy(object), "e": F["e"].to_numpy(np.int64), "pool": np.asarray(pool, np.int64), "seg": seg}


def fakeB_job(F, xfun, col, seg):
    s0, s1 = seg
    per_m = Counter(G["cal"][F["t"].to_numpy()].strftime("%Y-%m"))
    mon = G["cal"].strftime("%Y-%m").to_numpy()
    cand = defaultdict(lambda: ([], []))
    X = {}
    for s in G["sids"]:
        st = G["ST"][s]; X[s] = np.asarray(xfun(G["SIG"][s]), np.int64)
        tt = np.arange(s0 - 1, s1)
        ok = st["valid"][tt] & colmask(st, col)[tt] & np.isfinite(st["opens"][tt + 1]) & (np.nan_to_num(st["opens"][tt + 1]) > 0)
        tt = tt[ok]
        tt = tt[~np.isin(tt, X[s])]
        for mo, grp in pd.Series(tt).groupby(mon[tt]):
            cand[mo][0].append(np.full(len(grp), s, object)); cand[mo][1].append(grp.to_numpy(np.int64))
    cand2 = {mo: (np.concatenate(a), np.concatenate(b)) for mo, (a, b) in cand.items()}
    return {"per_m": dict(per_m), "cand": cand2, "X": X, "seg": seg}


# ═════════════ 事件層段尾（P18 同式）═════════════
def ev_tail(entries_fun, exit_fun, lo, hi, drop_same):
    n = 0; tail = 0
    for s in G["sids"]:
        S = G["SIG"][s]; st = G["ST"][s]
        ent = entries_fun(S); ent = ent[(ent >= lo) & (ent <= hi - 1)]
        ent = ent[st["member"][ent] & st["valid"][ent]]
        xs = np.asarray(exit_fun(S), np.int64)
        if drop_same:
            ent = ent[~np.isin(ent, xs)]
        for t in ent:
            n += 1; tail += int(first_ge(xs, int(t) + 1, hi) < 0)
    return n, tail


# ═════════════ SPY 層 ═════════════
def spy_arrays():
    cal = G["cal"]
    d = pd.read_csv(U._p("macro", "yahoo_SPY.csv"), dtype={"date": str})
    d.index = pd.to_datetime(d["date"]); d = d.reindex(cal)
    k = d["adjclose"] / d["close"]
    return (d["open"] * k).to_numpy(float), (d["close"] * k).to_numpy(float)


def spy_run(o, c, ent, ex, s0, s1):
    """researchSig.l0050_run 同式（成本 0.05%、窗 [s0, s1]、年化 ÷252）。"""
    cff = pd.Series(c).ffill().to_numpy()
    eq = np.ones(len(c)); cash = 1.0; amt = 0.0; ep = np.nan; hold = False; pend = None; trades = []; tb = None
    if (s0 - 1) in ent and (s0 - 1) not in ex:
        pend = "buy"
    inpos = 0
    for t in range(s0, s1 + 1):
        if pend is not None and np.isfinite(o[t]) and o[t] > 0:
            if pend == "sell" and hold:
                g = o[t] / ep - 1.0
                cash = amt * (1 + g - C.COST); trades.append((tb, t, g - C.COST)); hold = False
            elif pend == "buy" and not hold:
                amt = cash; ep = float(o[t]); cash = 0.0; hold = True; tb = t
            pend = None
        eq[t] = amt * cff[t] / ep if hold else cash
        inpos += int(hold)
        if hold and t in ex:
            pend = "sell"
        elif (not hold) and t in ent and t not in ex and t + 1 <= s1:
            pend = "buy"
        elif pend == "sell" and not hold:
            pend = None
    c_, m_ = W.window_metrics(eq, s0, s1); bc, bm = W.window_metrics(cff, s0, s1)
    hd = [b - a for a, b, _ in trades]
    return {"年化": c_, "回落": m_, "比值": c_ / abs(m_) if m_ else np.nan, "一直抱SPY_年化": bc, "一直抱SPY_回落": bm,
            "年化高於一直抱": bool(c_ > bc), "交易筆": len(trades) + int(hold), "段尾未出場": int(hold),
            "勝率": float(np.mean([x[2] > 0 for x in trades])) if trades else np.nan, "平均持有天數": float(np.mean(hd)) if hd else np.nan,
            "持股時間比例": inpos / (s1 - s0 + 1)}


def ma_cross_days(c, k):
    b = np.flatnonzero(np.isfinite(c)); cb = c[b]
    ma = RV.ma_fsum(cb, k)
    with np.errstate(invalid="ignore"):
        x = np.isfinite(ma[1:]) & np.isfinite(ma[:-1]) & (cb[:-1] >= ma[:-1]) & (cb[1:] < ma[1:])
    return set(b[1:][x].tolist())


# ═════════════ 共用：判定格的確認段、描述、假訊號 ═════════════
def judge_block(name, Fc, nseed, procs, nfake, B, seg, deg400=False, fakeB_x=None, extra_label="", fixed=True):
    """Fc：確認段全部列（含 m4、m5、pbx…）。⇒ 三欄 agg、標籤、假訊號、ret50、固定持有、跟進敏感度。"""
    arms = {}
    for col in ("合併", "只400", "只500"):
        arms[(name, col)] = mk_arm(col_sel(Fc, col), seg, pool=(col != "只500"))
        if col != "只500":
            arms[(name, col, "ret50")] = mk_arm(col_sel(Fc, col, f50=True), seg)
    if fixed:
        Fm = col_sel(Fc, "合併").sort_values(["e", "sid"])
        rows_main = [{"sid": s, "entry_pos": int(e)} for s, e in zip(Fm["sid"], Fm["e"])]
        for H in C.FIXH:
            fr = C.fixed_rows(rows_main, H, seg[1], C._S["closes"], C._S["opens"])
            Ff = pd.DataFrame({"sid": [r["sid"] for r in fr], "e": [r["entry_pos"] for r in fr], "xpos": [r["xpos"] for r in fr],
                               "g": [r["g"] for r in fr], "endhold": [r["endhold"] for r in fr], "why": "H%d" % H})
            okp = [not pb_hit(s, int(e) - 1, int(x)) for s, e, x in zip(Ff["sid"], Ff["e"], Ff["xpos"])]
            arms[(name, "合併", "fix%d" % H)] = mk_arm(Ff[np.asarray(okp, bool)], seg)
    res = run_arms(arms, procs, nseed, "%s 確認段" % name)
    out = {"欄": {}, "描述": {}}
    for col in ("合併", "只400", "只500"):
        a = agg(res[(name, col)], B, seg); a["訊號列數"] = arms[(name, col)]["n_rows"]
        out["欄"][col] = a
    lc = out["欄"]["合併"]["標籤"]; l4 = out["欄"]["只400"]["標籤"]
    if deg400:
        out["標籤"] = C.label_pf(lc, "不合格")
        out["只400註"] = "只 S&P 400 欄依構造退化（事件不足）⇒ 不可判定 ⇒ 最多事後擴母體"
    else:
        out["標籤"] = C.label_pf(lc, l4)
    for col in ("合併", "只400"):
        r50 = agg(res[(name, col, "ret50")], B, seg)
        out["描述"]["ret50_" + col] = {k: r50[k] for k in ("年化中位", "回落中位", "比值", "標籤")}
        out["描述"]["ret50_" + col]["訊號列數"] = arms[(name, col, "ret50")]["n_rows"]
    if fixed:
        fx = {}
        for H in C.FIXH:
            a = agg(res[(name, "合併", "fix%d" % H)], B, seg)
            d_ = [x["cagr"] - y["cagr"] for x, y in zip(res[(name, "合併")], res[(name, "合併", "fix%d" % H)])]
            fx["固定%d日" % H] = {"年化中位": a["年化中位"], "回落中位": a["回落中位"], "比值": a["比值"], "窗尾仍持有（中位）": a["窗尾仍持有件數（逐種子中位）"],
                                "條件出場−固定_年化差中位（同種子）": float(np.median(d_))}
        out["描述"]["固定持有（合併；描述、⛔ 不當評價）"] = fx
    # 跟進敏感度（合併欄合格／另列）
    if lc in ("合格", "另列"):
        a2 = {}
        Fm_ = col_sel(Fc, "合併")
        for nm, kw in (("cost_0.02%", {"cost": C.COST_SENS[0]}), ("cost_0.10%", {"cost": C.COST_SENS[1]}), ("slots_4", {"slots": 4}), ("slots_16", {"slots": 16})):
            a2[(name, "合併", nm)] = mk_arm(Fm_, seg, **kw)
        r2 = run_arms(a2, procs, nseed, "%s 跟進敏感度" % name)
        out["描述"]["跟進敏感度（合併）"] = {k[2]: {kk: agg(v, B, seg)[kk] for kk in ("年化中位", "回落中位", "比值", "標籤")} for k, v in r2.items()}
    # 假訊號
    out["假訊號"] = {}
    for col in ("合併", "只400"):
        if "年化中位" not in out["欄"][col]:
            continue
        Fs = col_sel(Fc, col); m = out["欄"][col]["年化中位"]
        pool = hold_pool(res[(name, col)])
        vA = fake_run("A", fakeA_job(Fs, pool, seg), nfake, procs)
        out["假訊號"]["A_" + col] = fake_summary(vA, m, B, nfake, len(pool))
        if fakeB_x is not None:
            vB = fake_run("B", fakeB_job(Fs, fakeB_x, col, seg), nfake, procs)
            out["假訊號"]["B_" + col] = fake_summary(vB, m, B, nfake)
    pA = out["假訊號"].get("A_合併", {}).get("p（隨機 ≥ 本格）", 0.0); pB = out["假訊號"].get("B_合併", {}).get("p（隨機 ≥ 本格）", 0.0)
    out["隨機也做得到"] = bool(pA >= 0.05 or pB >= 0.05)
    out["_seeds"] = {col: seeds_of(res[(name, col)]) for col in ("合併", "只400", "只500")}
    return out


def card_line(a, B):
    if "年化中位" not in a:
        return "無訊號（不可判定）"
    return "年化 %+.2f%%／回落 %+.2f%%（比值 %.3f；^SP500TR %+.2f%%／%+.2f%%、%.3f）⇒ %s" % (
        a["年化中位"] * 100, a["回落中位"] * 100, a["比值"], B["年化"] * 100, B["回落"] * 100, B["比值"], a["標籤"])


def must_report(a):
    if "年化中位" not in a:
        return None
    return {"持有天數_平均": a["持有天數_平均（逐種子中位）"], "持有天數_中位": a["持有天數_中位（逐種子中位）"], "持有天數_p10": a["持有天數_p10"],
            "持有天數_p90": a["持有天數_p90"], "最長持有": a["最長持有（200 顆最大）"], "窗尾仍持有件數（逐種子中位）": a["窗尾仍持有件數（逐種子中位）"],
            "窗尾仍持有件數（範圍）": a["窗尾仍持有件數（範圍）"], "離頂距離中位": a["離頂距離中位（出場價÷持有期最高收盤−1）"]}


def slim(a):
    keep = ("年化中位", "回落中位", "比值", "標籤", "年化p10", "年化p90", "逐種子標籤比例", "交易數中位", "槽位使用率中位", "持有天數_平均（逐種子中位）",
            "持有天數_中位（逐種子中位）", "持有天數_p10", "持有天數_p90", "最長持有（200 顆最大）", "窗尾仍持有件數（逐種子中位）", "窗尾仍持有件數（範圍）",
            "離頂距離中位（出場價÷持有期最高收盤−1）", "每年交易（每顆中位）", "勝率（已出場）", "平均淨報酬（已出場）", "再進場_每顆筆數", "再進場_平均淨報酬",
            "再進場_勝率", "首次進場_平均淨報酬", "首次進場_勝率", "出場原因占比", "現金比例（平均）", "平均持股檔數", "訊號列數")
    return {k: a.get(k) for k in keep if k in a}


def save_work(item, obj):
    p = os.path.join(WORK, "%s%s.pkl" % (item, G["tag"]))
    pickle.dump(obj, open(p, "wb"), protocol=4)
    return os.path.basename(p), C.sha256f(p)


def write_item(item, J):
    if G["lim"]:
        p = os.path.join(WORK, "lim", "%s.json" % item)
    else:
        p = os.path.join(OUTD, "%s.json" % item)
    C.jdump(J, p)
    log("[寫出] %s（%d B）" % (p, os.path.getsize(p)))
    return p


def common_meta(item):
    return {"件": item, "名稱": NAMES[item], "台股原登錄": "%s（%s）" % REGTW[item], "依據": C.REG, "補讀法時戳": READ_TS, "程式": "backtest/researchUSA3_g3.py",
            "資料commit": G["meta"].get("data_commit"), "段": {"探索": [str(G["cal"][G["w0"]].date()), str(G["cal"][G["sp"]].date())],
                                                             "確認": [str(G["cal"][G["c0"]].date()), str(G["cal"][G["w1"]].date())]},
            "引擎": "core C5：8 槽、種子 102000＋r（%d 顆）、成本 0.05%%、tradable＋delist" % G["nseed"], "可用檔數": len(G["sids"]),
            "訊號快取sha256（repo 外）": G["sig_sha"]}


def surv_line():
    return C.SURV


# ═════════════ A3-6 ═════════════
def xfun_of(xo):
    if xo == "ANY":
        return lambda S: union_days(S, ["X:" + k for k in RS.XS])
    return lambda S: np.asarray(S.get("X:" + xo, np.zeros(0, int)), np.int64)


def efun_of(E):
    codes = RS.E1 if E == "E1" else RS.E2
    return lambda S: union_days(S, ["E:" + k for k in codes])


def sys_rows(E, xo, seg):
    s0, s1 = seg
    xf = xfun_of(xo)
    R, drop = entry_rows(efun_of(E), s0, s1, xdrop=xf)
    dX = trig_first(R, xf, s1)
    return R, dX, drop


def run_a36(procs, nseed, nfake):
    item = "A3-6"; SG_ = segs(); B = brefs(); s0, s1 = SG_["探索"]
    EX = ["ANY"] + list(RS.XS)
    # Q12 退化（事件為單位、P18）
    deg = {}; evt = {}
    for E in ("E1", "E2"):
        for xo in EX:
            n_, tl = ev_tail(efun_of(E), xfun_of(xo), G["w0"], G["sp"], True)
            evt["%s×%s" % (E, xo)] = {"進場訊號": n_, "段尾未出場": tl, "段尾未出場%": round(100.0 * tl / n_, 1) if n_ else np.nan}
            deg["%s×%s" % (E, xo)] = bool(n_ and tl / n_ > 0.5)
    prep_deg = {"E1×VSc", "E1×EVE", "E2×EVE"}
    mine = {k for k, v in deg.items() if v}
    if not G["lim"] and mine != prep_deg:
        log("⚠ A3-6 退化格重算 %s ≠ prep %s ⇒ 照 prep 清單" % (mine, prep_deg))
    use_deg = prep_deg if not G["lim"] else mine
    log("[A3-6] 退化格（Q12）%s" % sorted(use_deg))
    # 探索段 18 格（合併）
    ROWS = {}; arms = {}
    for E in ("E1", "E2"):
        for xo in EX:
            R, dX, drop = sys_rows(E, xo, SG_["探索"])
            F = finalize(R, s1, {"X": dX}, ["X"])
            ROWS[(E, xo)] = (R, dX)
            arms[("探索", E, xo)] = mk_arm(col_sel(F, "合併"), SG_["探索"])
    res = run_arms(arms, procs, nseed, "A3-6 探索 18 格")
    EXP = {k: agg(v, B["探索"], SG_["探索"]) for k, v in res.items()}
    for k in EXP:
        EXP[k]["訊號列數"] = arms[k]["n_rows"]
    chosen = {}
    for E in ("E1", "E2"):
        cands = [(xo, EXP[("探索", E, xo)]) for xo in EX if "%s×%s" % (E, xo) not in use_deg]
        chosen[E] = pick(cands)
    log("[A3-6] 挑出場 %s" % chosen)
    # 停損停利 16 組（探索段、E1、E2 各用挑中出場）
    cz, oz = C._S["closes"], C._S["opens"]
    bars_of = lambda s: {"idx": G["ST"][s]["bars"], "h": G["ST"][s]["H"][G["ST"][s]["bars"]], "l": G["ST"][s]["L"][G["ST"][s]["bars"]],
                         "c": G["ST"][s]["C"][G["ST"][s]["bars"]]}
    valid_of = lambda s: G["ST"][s]["valid"]
    SLS, TPS = RS.SLS, RS.TPS

    def stopdays(R, s1_):
        Rr = R.rename(columns={"e": "entry_pos"}).reset_index(drop=True)
        return RS.stop_days(Rr, cz, oz, bars_of, s1_, valid_of)

    def sltp_F(R, dX, sl, tp, s1_, SD):
        trig = {"X": dX}; names = ["X"]
        if sl != "無":
            trig[sl] = SD[sl].to_numpy(int); names.append(sl)
        if tp in ("TP30", "TR20"):
            trig[tp] = SD[tp].to_numpy(int); names.append(tp)
        F = finalize(R.reset_index(drop=True), s1_, trig, names)
        kw = {"trim_rule": {"kind": "gain", "x": 0.5, "frac": 0.5}} if tp == "TP50h" else None
        return F, kw, SD

    arms = {}
    for E in ("E1", "E2"):
        R, dX = ROWS[(E, chosen[E])]
        SD = stopdays(R, s1)
        for sl in SLS:
            for tp in TPS:
                if sl == "無" and tp == "無":
                    continue
                F, kw, _ = sltp_F(R, dX, sl, tp, s1, SD)
                arms[("探索", E, chosen[E], sl, tp)] = mk_arm(col_sel(F, "合併"), SG_["探索"], kw=kw)
    res = run_arms(arms, procs, nseed, "A3-6 探索 停損停利 30 組")
    for k, v in res.items():
        EXP[k] = agg(v, B["探索"], SG_["探索"]); EXP[k]["訊號列數"] = arms[k]["n_rows"]
    cands = [((E, chosen[E], "無", "無"), EXP[("探索", E, chosen[E])]) for E in ("E1", "E2")]
    cands += [((k[1], k[2], k[3], k[4]), EXP[k]) for k in res]
    ch_st = pick(cands)
    log("[A3-6] 挑停損停利 %s" % (ch_st,))
    # 確認段
    s0c, s1c = SG_["確認"]
    JUD = {}; CROWS = {}
    for E in ("E1", "E2"):
        R, dX, drop = sys_rows(E, chosen[E], SG_["確認"])
        F = finalize(R, s1c, {"X": dX}, ["X"]); CROWS[E] = F
        JUD[E] = judge_block("A3-6|%s|%s" % (E, chosen[E]), F, nseed, procs, nfake, B["確認"], SG_["確認"], fakeB_x=xfun_of(chosen[E]))
        JUD[E]["同日有出場而不進"] = drop
        # X 任一時各訊號占比（事件層）
        if chosen[E] == "ANY":
            cnt = Counter()
            for s, d in zip(F["sid"], F["d"]):
                if d >= 0:
                    S = G["SIG"][s]
                    for k in RS.XS:
                        if d in set(S.get("X:" + k, np.zeros(0, int)).tolist()):
                            cnt[k] += 1
            tot = sum(cnt.values())
            JUD[E]["X任一_各訊號占比（事件層）"] = {k: round(v / tot, 4) for k, v in cnt.most_common()} if tot else {}
    st_note = None
    if ch_st[2] == "無" and ch_st[3] == "無":
        st_note = "挑中「無」⇒ 停損停利沒有加分，該格與 %s 同格、N 不另加" % ch_st[0]
    else:
        E = ch_st[0]
        R, dX, _ = sys_rows(E, chosen[E], SG_["確認"])
        F, kw, SD = sltp_F(R, dX, ch_st[2], ch_st[3], s1c, stopdays(R, s1c))
        arms = {}
        for col in ("合併", "只400", "只500"):
            arms[("ST", col)] = mk_arm(col_sel(F, col), SG_["確認"], kw=kw)
            if col != "只500":
                arms[("ST", col, "ret50")] = mk_arm(col_sel(F, col, f50=True), SG_["確認"], kw=kw)
        res = run_arms(arms, procs, nseed, "A3-6 確認 停損停利格")
        J = {"欄": {col: agg(res[("ST", col)], B["確認"], SG_["確認"]) for col in ("合併", "只400", "只500")}, "描述": {}}
        for col in ("合併", "只400", "只500"):
            J["欄"][col]["訊號列數"] = arms[("ST", col)]["n_rows"]
        J["標籤"] = C.label_pf(J["欄"]["合併"]["標籤"], J["欄"]["只400"]["標籤"])
        for col in ("合併", "只400"):
            r50 = agg(res[("ST", col, "ret50")], B["確認"], SG_["確認"])
            J["描述"]["ret50_" + col] = {k: r50[k] for k in ("年化中位", "回落中位", "比值", "標籤")}
        # 放棄組（事件層）：被停損／停利出場的列 若只照訊號出場
        Fm = col_sel(F, "合併"); Fx = finalize(R, s1c, {"X": dX}, ["X"]).set_index(["sid", "e"])
        m = Fm["why"].isin(["SL10", "SL20", "AT2", "TP30", "TR20"]).to_numpy()
        if m.any():
            a_ = Fm[m]; b_ = Fx.loc[list(zip(a_["sid"], a_["e"])), "g"].to_numpy()
            J["描述"]["放棄組（事件層、合併）"] = {"筆數": int(m.sum()), "占列": float(m.mean()), "實際平均毛報酬": float(a_["g"].mean()),
                                         "若照訊號出場平均毛報酬": float(b_.mean()), "照訊號出場較好比例": float((b_ > a_["g"].to_numpy()).mean())}
        J["描述"]["出場原因（事件層、合併）"] = {k: int(v) for k, v in Fm["why"].value_counts().items()}
        J["_seeds"] = {col: seeds_of(res[("ST", col)]) for col in ("合併", "只400", "只500")}
        JUD["ST"] = J
    # SPY 層
    o, c = spy_arrays()
    SPYSG = PREP.spy_layer(G["cal"])
    ent = set(union_days(SPYSG, ["E:" + k for k in RS.E1 + RS.E2]).tolist())
    ex = set(union_days(SPYSG, ["X:" + k for k in RS.XS]).tolist())
    SPY = {seg: spy_run(o, c, ent, ex, *SG_[seg]) for seg in ("探索", "確認")}
    SPY["確認"]["^SP500TR（描述）"] = B["確認"]
    spy_lab = "事後擴母體（依構造：SPY 層沒有只 S&P 400 欄）" if SPY["確認"]["年化高於一直抱"] else "不合格"
    # ── 彙總
    cells = {"E1": JUD["E1"]["標籤"], "E2": JUD["E2"]["標籤"], "SPY層": spy_lab}
    N = 3 + (0 if st_note else 1)
    if not st_note:
        cells["停損停利挑中格"] = JUD["ST"]["標籤"]
    J = common_meta(item)
    J.update({"Q12退化（事件層、探索段、合併）": {"重算": evt, "退化格（照 prep 清單、照報不挑）": sorted(use_deg), "重算與 prep 一致": mine == prep_deg},
              "探索段（合併）": {"|".join(k[1:]): slim(v) for k, v in EXP.items()}, "探索段挑出場": chosen, "停損停利32選1": list(ch_st), "停損停利註": st_note,
              "確認段": {}, "SPY層": SPY, "基準": B})
    for E in ("E1", "E2"):
        J["確認段"][E] = {"格": "%s 進、%s 出" % (E, XNAME[chosen[E]]), "標籤": JUD[E]["標籤"], "欄": {c_: slim(v) for c_, v in JUD[E]["欄"].items()},
                          "描述": JUD[E]["描述"], "假訊號": JUD[E]["假訊號"], "隨機也做得到": JUD[E]["隨機也做得到"], "同日有出場而不進": JUD[E]["同日有出場而不進"],
                          "X任一_各訊號占比（事件層）": JUD[E].get("X任一_各訊號占比（事件層）")}
    if "ST" in JUD:
        J["確認段"]["停損停利挑中格"] = {"格": "%s＋%s／%s" % (ch_st[0], ch_st[2], ch_st[3]), "標籤": JUD["ST"]["標籤"],
                                     "欄": {c_: slim(v) for c_, v in JUD["ST"]["欄"].items()}, "描述": JUD["ST"]["描述"]}
    seeds = {E: JUD[E]["_seeds"] for E in ("E1", "E2")}
    if "ST" in JUD:
        seeds["ST"] = JUD["ST"]["_seeds"]
    wk = save_work(item, {"seeds": seeds, "chosen": chosen, "ch_st": ch_st,
                          "rows": {E: CROWS[E][["sid", "t", "e", "m4", "m5", "xpos", "g", "endhold", "why", "pbx", "f50x", "d"]] for E in CROWS}})
    J["逐筆檔sha（repo外）"] = {wk[0]: wk[1]}
    J["卡片"] = card_a36(J, JUD, chosen, ch_st, st_note, SPY, spy_lab, cells, N, B)
    write_item(item, J)
    return J


def lab_summary(cells):
    labs = list(cells.values())
    order = ["合格", "事後擴母體", "另列", "事後擴母體（另列）"]
    for o in order:
        hit = [k for k, v in cells.items() if v.startswith(o)]
        if hit:
            return "%s（%s）；其餘 %s" % (o, "、".join(hit), "、".join("%s %s" % (k, v) for k, v in cells.items() if k not in hit) or "—")
    if all(v.startswith("不可判定") for v in labs):
        return "不可判定（全部格依構造不可判定）"
    return "不合格（%s）" % "、".join("%s %s" % (k, v) for k, v in cells.items())


def ret50_line(JUD, keys):
    parts = []
    for k in keys:
        if k in JUD and "描述" in JUD[k] and "ret50_合併" in JUD[k]["描述"]:
            r = JUD[k]["描述"]["ret50_合併"]; r4 = JUD[k]["描述"].get("ret50_只400", {})
            parts.append("%s：合併 %+.2f%%（%s）、只400 %s" % (k, r["年化中位"] * 100, r["標籤"],
                                                     ("%+.2f%%（%s）" % (r4["年化中位"] * 100, r4["標籤"])) if r4 else "—"))
    return "剔除 S&P 400 未確認 |ret|＞50% 列後：" + "；".join(parts) if parts else "—"


def card_a36(J, JUD, chosen, ch_st, st_note, SPY, spy_lab, cells, N, B):
    Bc = B["確認"]
    three = {}
    for col, nm in (("合併", "合併"), ("只400", "只400"), ("只500", "只500")):
        parts = []
        for E in ("E1", "E2"):
            parts.append("%s（%s 出）%s" % (E, XNAME[chosen[E]], card_line(JUD[E]["欄"][col], Bc)))
        if "ST" in JUD:
            parts.append("停損停利格 %s" % card_line(JUD["ST"]["欄"][col], Bc))
        three[nm] = "；".join(parts) + ("（描述、⛔ 不判）" if col == "只500" else "")
    sent = []
    for E in ("E1", "E2"):
        q = JUD[E]["欄"]["合併"]; pre = "隨機也做得到：" if JUD[E]["隨機也做得到"] else ""
        lab = JUD[E]["標籤"]
        if lab == "合格":
            sent.append("%s%s 進、%s 出，2022～2026-09 年化 %+.1f%%／回落 %+.1f%%，贏 ^SP500TR（%+.1f%%）且風險調整後不輸（合併與只 S&P 400 都過）"
                        % (pre, E, XNAME[chosen[E]], q["年化中位"] * 100, q["回落中位"] * 100, Bc["年化"] * 100))
        elif lab.startswith("事後擴母體") or lab == "另列":
            sent.append("%s%s 進、%s 出：%s（合併年化 %+.1f%%／回落 %+.1f%%；只 S&P 400 %+.1f%%）" % (pre, E, XNAME[chosen[E]], lab, q["年化中位"] * 100,
                        q["回落中位"] * 100, JUD[E]["欄"]["只400"]["年化中位"] * 100))
        else:
            sent.append("%s%s 訊號進、訊號出沒有贏 ^SP500TR（合併年化 %+.1f%%／回落 %+.1f%%，基準 %+.1f%%／%+.1f%%）" % (pre, E, q["年化中位"] * 100, q["回落中位"] * 100,
                        Bc["年化"] * 100, Bc["回落"] * 100))
    sent.append(st_note or ("停損停利挑中 %s＋%s／%s：%s" % (ch_st[0], ch_st[2], ch_st[3], JUD["ST"]["標籤"])))
    sent.append("SPY 層（SPY 自己出現進場訊號就全買、出場訊號就全賣）年化 %+.1f%% vs 一直抱 SPY %+.1f%% ⇒ %s多賺" % (
        SPY["確認"]["年化"] * 100, SPY["確認"]["一直抱SPY_年化"] * 100, "有" if SPY["確認"]["年化高於一直抱"] else "沒有"))
    res_sent = "結論：%s。%s；%s；%s。" % ("；".join(sent[:2]), sent[2], sent[3], "%s、%s、%s" % (C.IDEA, C.NO_EARLY, C.SURV))
    E = "E1"
    return {"件": "A3-6", "名稱": NAMES["A3-6"], "台股原登錄": "%s（%s）" % REGTW["A3-6"], "出場型": "① 條件（X 訊號出場；⛔ 無最長天數；固定 20／60／120／240 只描述）",
            "N": N, "標籤": lab_summary(cells), "格標籤": cells,
            "判定格": {"E1": "E1 × %s" % XNAME[chosen["E1"]], "E2": "E2 × %s" % XNAME[chosen["E2"]],
                    "停損停利": ("無（%s）" % st_note) if st_note else "%s × %s × %s／%s" % (ch_st[0], XNAME[ch_st[1]], ch_st[2], ch_st[3]), "SPY層": "SPY 自己的 E1∪E2 進、X 任一出"},
            "三欄": three,
            "條件出場必報": {E_: must_report(JUD[E_]["欄"]["合併"]) for E_ in ("E1", "E2")},
            "結果句": res_sent,
            "敏感度_ret50": ret50_line(JUD, ["E1", "E2", "ST"]),
            "偏離": DEV_COMMON + ["0050 層 → SPY 層（含息、同規則）；判準 0050 → ^SP500TR（個股層）／一直抱 SPY（SPY 層）",
                               "SPY 層沒有只 S&P 400 欄 ⇒ 依構造最多事後擴母體（seq316 全批一律）",
                               "Q12：探索段段尾未出場 ＞50% 的出場格（E1×VSc、E1×EVE、E2×EVE）事前排除、照報（台股原登錄無此規則）",
                               "原「用訊號出場 vs 固定抱 60 天」一句移到描述欄（C6：⛔ 不拿抱幾天當評價）"],
            "補讀法": ["G1～G13（docstring）", "停損停利觸發照 researchSig.stop_days 原式；+50% 賣半用引擎 trim_rule gain"],
            "先驗紀錄": prior_a36(JUD, chosen, ch_st, st_note, SPY)}


DEV_COMMON = ["組合引擎改 core C5：8 槽、種子 102000＋r、成本 0.05%（台股 10 檔、種子 1000＋r、成本 0.585%、營飆骨架）",
              "母體 W1 eligible → 當天在 S&P 500／400（三欄：合併、只 S&P 400、只 S&P 500 描述）；判定 ＝ 合併與只 S&P 400 都過才合格（seq316）",
              "早年段美股沒有 ⇒ 不跑（結果句標「缺早年段」）；判定 ＝ 探索段挑、確認段判（seq319 Q1）",
              "持有期跨轉接層硬斷點（[t−60, 出場日]）的列剔除（G7）",
              "開盤漲停買不到等台股條件拿掉（P4）"]


def prior_a36(JUD, chosen, ch_st, st_note, SPY):
    p1 = all(JUD[E]["標籤"] == "不合格" for E in ("E1", "E2"))
    fx = [JUD[E]["描述"]["固定持有（合併；描述、⛔ 不當評價）"]["固定60日"]["條件出場−固定_年化差中位（同種子）"] for E in ("E1", "E2")]
    p3 = None
    if not st_note:
        p3 = JUD["ST"]["欄"]["合併"]["年化中位"] <= JUD[ch_st[0]]["欄"]["合併"]["年化中位"]
    return ("台股先驗（照實記，換成美股口徑）：① E1、E2 確認段都不合格（約七成）⇒ %s；② 訊號出場不比固定抱 60 天好（約七成）⇒ %s（年化差 E1 %+.2f、E2 %+.2f 點；只記錄）；"
            "③ 停損停利挑出組合確認段不贏「無」（約六成五）⇒ %s；④ 0050 層（SPY 層）年化低於一直抱（約八成）⇒ %s"
            % ("對" if p1 else "錯", "對" if all(x <= 0 for x in fx) else ("錯" if all(x > 0 for x in fx) else "一對一錯"), fx[0] * 100, fx[1] * 100,
               ("挑中「無」⇒ 對" if st_note else ("對" if p3 else "錯")), "對" if not SPY["確認"]["年化高於一直抱"] else "錯"))


# ═════════════ A3-7 ═════════════
def run_a37(procs, nseed, nfake):
    item = "A3-7"; SG_ = segs(); B = brefs(); s0, s1 = SG_["探索"]
    sy = stock_years("合併")
    deg = {}; info = {}
    for E in ("E1", "E2"):
        for xo in EXOPT:
            n_, tl = ev_tail(efun_of(E), lambda S, xo=xo: S[xo], G["w0"], G["sp"], False)
            per = inwin_count(xo, "合併") / sy
            info["%s×%s" % (E, xo)] = {"進場訊號": n_, "段尾未出場%": round(100.0 * tl / n_, 1) if n_ else np.nan, "均線穿越每股票年": round(per, 2)}
            deg["%s×%s" % (E, xo)] = bool((n_ and tl / n_ > 0.5) or per < 1.0)
    log("[A3-7] seq246 退化 %s" % {k: v for k, v in deg.items() if v})
    ROWS = {}; arms = {}
    for E in ("E1", "E2"):
        for xo in EXOPT:
            xf = (lambda S, xo=xo: S[xo])
            R, drop = entry_rows(efun_of(E), s0, s1, xdrop=xf)
            F = finalize(R, s1, {"X": trig_first(R, xf, s1)}, ["X"])
            arms[("探索", E, xo)] = mk_arm(col_sel(F, "合併"), SG_["探索"])
    res = run_arms(arms, procs, nseed, "A3-7 探索 6 格")
    EXP = {k: agg(v, B["探索"], SG_["探索"]) for k, v in res.items()}
    for k in EXP:
        EXP[k]["訊號列數"] = arms[k]["n_rows"]
    chosen = {}
    for E in ("E1", "E2"):
        cands = [(xo, EXP[("探索", E, xo)]) for xo in EXOPT if not deg["%s×%s" % (E, xo)]]
        chosen[E] = pick(cands) if cands else None
    log("[A3-7] 挑出場 %s" % chosen)
    s0c, s1c = SG_["確認"]
    JUD = {}; CROWS = {}; NS = {}
    for E in ("E1", "E2"):
        if chosen[E] is None:
            JUD[E] = {"標籤": "不可判定（該族 3 格全退化）"}; continue
        xo = chosen[E]; xf = (lambda S, xo=xo: S[xo])
        R, drop = entry_rows(efun_of(E), s0c, s1c, xdrop=xf)
        F = finalize(R, s1c, {"X": trig_first(R, xf, s1c)}, ["X"]); CROWS[E] = F
        JUD[E] = judge_block("A3-7|%s|%s" % (E, xo), F, nseed, procs, nfake, B["確認"], SG_["確認"])
        Fm = col_sel(F, "合併"); m = Fm["endhold"].to_numpy(bool)
        ur = Fm["g"].to_numpy()[m]; hd = (s1c - Fm["e"].to_numpy()[m])
        NS[E] = {"筆數（事件層、合併）": int(m.sum()), "占列": float(m.mean()) if len(m) else np.nan,
                 "段尾未實現毛報酬": {"中位": float(np.median(ur)), "p10": float(np.percentile(ur, 10)), "p90": float(np.percentile(ur, 90)),
                                "虧損比例": float((ur < 0).mean())} if m.any() else None, "最長持有（交易日）": int(hd.max()) if m.any() else 0}
    # 「收盤 ＜ MA 即賣」並列描述（確認段、合併；不套同日不進）
    arms = {}
    for E in ("E1", "E2"):
        for k in (10, 20, 60):
            xf = (lambda S, k=k: S["BL%d" % k])
            R, _ = entry_rows(efun_of(E), s0c, s1c)
            F = finalize(R, s1c, {"X": trig_first(R, xf, s1c)}, ["X"])
            arms[("MAs", E, k)] = mk_arm(col_sel(F, "合併"), SG_["確認"])
    res = run_arms(arms, procs, nseed, "A3-7 收盤＜MA 即賣（描述）")
    MAS = {"%s×收盤＜MA%d" % (k[1], k[2]): {kk: agg(v, B["確認"], SG_["確認"])[kk] for kk in ("年化中位", "回落中位", "比值", "標籤", "持有天數_中位（逐種子中位）")}
           for k, v in res.items()}
    # SPY 層（描述）
    o, c = spy_arrays(); SPYSG = PREP.spy_layer(G["cal"])
    ent = set(union_days(SPYSG, ["E:" + k for k in RS.E1 + RS.E2]).tolist())
    SPY = {}
    for k in (10, 20, 60):
        ex = ma_cross_days(c, k)
        for seg in ("探索", "確認"):
            SPY["MA%d|%s" % (k, seg)] = spy_run(o, c, ent, ex, *SG_[seg])
    cells = {E: JUD[E]["標籤"] for E in ("E1", "E2")}
    N = sum(1 for E in ("E1", "E2") if chosen[E] is not None)
    J = common_meta(item)
    J.update({"seq246退化（事件層、探索段）": {"重算": info, "排除": sorted(k for k, v in deg.items() if v), "股票年（合併）": round(sy, 1)},
              "探索段（合併）": {"|".join(k[1:]): slim(v) for k, v in EXP.items()}, "探索段挑出場": chosen, "確認段": {}, "描述": {"收盤＜MA即賣（確認、合併）": MAS,
              "SPY層（各均線；描述）": SPY, "一直沒站上就不賣（確認、事件層）": NS}, "基準": B})
    for E in ("E1", "E2"):
        if chosen[E] is None:
            J["確認段"][E] = {"標籤": JUD[E]["標籤"]}; continue
        J["確認段"][E] = {"格": "%s 進、跌破 %s 日線出" % (E, chosen[E][2:]), "標籤": JUD[E]["標籤"], "欄": {c_: slim(v) for c_, v in JUD[E]["欄"].items()},
                          "描述": JUD[E]["描述"], "假訊號": JUD[E]["假訊號"], "隨機也做得到": JUD[E]["隨機也做得到"]}
    wk = save_work(item, {"seeds": {E: JUD[E]["_seeds"] for E in CROWS}, "chosen": chosen,
                          "rows": {E: CROWS[E][["sid", "t", "e", "m4", "m5", "xpos", "g", "endhold", "why", "pbx", "f50x", "d"]] for E in CROWS}})
    J["逐筆檔sha（repo外）"] = {wk[0]: wk[1]}
    Bc = B["確認"]
    three = {}
    for col in ("合併", "只400", "只500"):
        three[col] = "；".join("%s（跌破 %s 日線）%s" % (E, chosen[E][2:], card_line(JUD[E]["欄"][col], Bc)) if chosen[E] else "%s 不可判定" % E
                               for E in ("E1", "E2")) + ("（描述、⛔ 不判）" if col == "只500" else "")
    sent = []
    for E in ("E1", "E2"):
        if chosen[E] is None:
            sent.append("%s 三格全退化 ⇒ 依構造不可判定" % E); continue
        q = JUD[E]["欄"]["合併"]; pre = "隨機出場也做得到：" if JUD[E]["隨機也做得到"] else ""; lab = JUD[E]["標籤"]
        if lab == "合格":
            sent.append("%s%s 進、跌破 %s 日線出，2022～2026-09 年化 %+.1f%%／回落 %+.1f%%，贏 ^SP500TR 且風險調整後不輸" % (pre, E, chosen[E][2:], q["年化中位"] * 100, q["回落中位"] * 100))
        elif lab != "不合格":
            sent.append("%s%s 進、跌破 %s 日線出：%s（合併年化 %+.1f%%、只 S&P 400 %+.1f%%）" % (pre, E, chosen[E][2:], lab, q["年化中位"] * 100, JUD[E]["欄"]["只400"]["年化中位"] * 100))
        else:
            sent.append("%s%s 訊號進、跌破 %s 日線出，沒有贏 ^SP500TR（合併年化 %+.1f%%／回落 %+.1f%%，基準 %+.1f%%／%+.1f%%）" % (pre, E, chosen[E][2:], q["年化中位"] * 100,
                        q["回落中位"] * 100, Bc["年化"] * 100, Bc["回落"] * 100))
    fx = {E: JUD[E]["描述"]["固定持有（合併；描述、⛔ 不當評價）"]["固定60日"]["條件出場−固定_年化差中位（同種子）"] for E in CROWS}
    J["卡片"] = {"件": item, "名稱": NAMES[item], "台股原登錄": "%s（%s）" % REGTW[item], "出場型": "① 條件（收盤由上往下穿越 MA ⇒ 次日開盤賣；⛔ 無最長天數）",
                "N": N, "標籤": lab_summary(cells), "格標籤": cells, "判定格": {E: ("%s × 跌破 %s 日線" % (E, chosen[E][2:])) if chosen[E] else "—" for E in ("E1", "E2")},
                "三欄": three, "條件出場必報": {E: must_report(JUD[E]["欄"]["合併"]) for E in CROWS},
                "結果句": "結論：%s。看過台股前一版結果才加測；%s、%s、%s。" % ("；".join(sent), C.IDEA, C.NO_EARLY, C.SURV),
                "敏感度_ret50": ret50_line(JUD, ["E1", "E2"]),
                "偏離": DEV_COMMON + ["seq246 退化判定用事件層（P18）：每檔每股票年均線穿越、探索段段尾未出場（台股原用 10 檔組合層統計）",
                                   "原「用均線出場 vs 固定抱 60 天」一句移到描述欄（C6）", "0050 層（各均線）→ SPY 層，只描述"],
                "補讀法": ["G1～G13（docstring）", "「跌破」＝ researchRev.ma_fsum 由上往下穿越；並列「收盤 ＜ MA 即賣」只在確認段合併欄描述"],
                "先驗紀錄": "台股先驗（照實記）：① E1、E2 確認段都不合格（約七成）⇒ %s；② 探索段挑中 MA60（約五成五）⇒ %s；③ 均線出場年化不比固定抱 60 天高（約六成）⇒ %s（只記錄）；④ 無退化格被排除（約七成）⇒ %s" % (
                    "對" if all(JUD[E]["標籤"] in ("不合格",) or JUD[E]["標籤"].startswith("不可判定") for E in ("E1", "E2")) else "錯",
                    "、".join("%s 挑 %s" % (E, chosen[E]) for E in ("E1", "E2")), "、".join("%s %s（%+.2f 點）" % (E, "對" if v <= 0 else "錯", v * 100) for E, v in fx.items()),
                    "對" if not any(deg.values()) else "錯")}
    write_item(item, J)
    return J


# ═════════════ A3-14／A3-15：外部作者 ═════════════
def ext_entry_rows(code, xo, seg):
    """researchExtAuth.entry_rows／researchExtAuth2.o1_rows 規則。"""
    s0, s1 = seg
    R, _ = entry_rows([code], s0, s1)
    if code == "O1" and xo == "OWN":
        out = np.full(len(R), -1, np.int64)
        for i, (s, t, e) in enumerate(zip(R["sid"], R["t"], R["e"])):
            S = G["SIG"][s]; st = G["ST"][s]
            j = np.flatnonzero(S["O1"] == t)
            lowk = S["O1_low"][j[0]]
            b = st["bars"]; bi = b[(b >= e) & (b <= s1)]
            w = bi[st["C"][bi] < lowk]
            out[i] = int(w[0]) if len(w) else -1
        dX = out
    else:
        dX = trig_first(R, lambda S: S[xo], s1)
    return finalize(R, s1, {"X": dX}, ["X"])


def base_rows(seg):
    s0, s1 = seg
    R, _ = entry_rows(list(ENT5), s0, s1)
    return R


def rule_trig(R, code, s1):
    """疊加條件第一次觸發（≥ e、≤ s1）。Y4 ＝ researchExtAuth.y4_day（買價 ＝ 進場日開盤）。"""
    if not code.startswith("Y4"):
        return trig_first(R, lambda S: S[code], s1)
    k = "MA5" if code == "Y4_MA5" else "MA10"
    out = np.full(len(R), -1, np.int64); cache = {}
    n = len(G["cal"])
    for i, (s, e) in enumerate(zip(R["sid"], R["e"])):
        st = G["ST"][s]
        if s not in cache:
            xb = np.zeros(n, bool); xb[G["SIG"][s][k]] = True; cache[s] = xb
        b = st["bars"]; bi = b[(b >= e) & (b <= s1)]
        out[i] = EA.y4_day(st["C"], bi, float(st["opens"][e]), cache[s])
    return out


def over_F(R, code, xo, s1, rt=None):
    """出場顆主臂：基準跌破 xo（無天數上限）＋本條（code；None ＝ 只基準）；平手均線先。"""
    dm = trig_first(R, lambda S: S[xo], s1)
    if code is None:
        return finalize(R, s1, {xo: dm}, [xo]), dm, None
    dr = rule_trig(R, code, s1) if rt is None else rt
    return finalize(R, s1, {xo: dm, code: dr}, [xo, code]), dm, dr


def over_H_F(R, code, H, s1, rt=None):
    """描述：原「基準抱 H 日（第 H 根收盤出）＋本條（觸發 d ≤ xpos−2 才有效 ⇒ d＋1 開盤）」。"""
    e = R["e"].to_numpy(np.int64); xp = e + H - 1
    endh = xp > s1; xpc = np.minimum(xp, s1)
    d = np.full(len(R), -1, np.int64)
    if code is not None:
        dr = rule_trig(R, code, s1) if rt is None else rt
        d = np.where((dr >= 0) & (dr <= xpc - 2) & (dr <= s1), dr, -1)
    x = np.where(d >= 0, d + 1, xpc)
    g = np.empty(len(R)); pbx = np.zeros(len(R), bool); f5 = np.zeros(len(R), bool)
    for i, (s, t, ee) in enumerate(zip(R["sid"], R["t"], e)):
        st = G["ST"][s]
        if d[i] >= 0:
            g[i] = C.gross_exit(st, int(ee), int(x[i]), False)
        else:
            g[i] = st["closes"][int(x[i])] / st["opens"][int(ee)] - 1.0
        lo = max(int(t) - LOOKBACK, 0); cs = G["cspb"][s]
        pbx[i] = (cs[x[i]] - (cs[lo - 1] if lo > 0 else 0)) > 0
    return R.assign(xpos=x, g=g, endhold=(d < 0) & endh, why=np.where(d >= 0, code or "", "H%d" % H), pbx=pbx, f50x=f5, d=d)


def ext_item(item, procs, nseed, nfake):
    """A3-14（W1、Y1、Y2、Y3、Y4、Y5）／A3-15（F1、O1、S1）。"""
    SG_ = segs(); B = brefs(); s0, s1 = SG_["探索"]; s0c, s1c = SG_["確認"]
    yrs_main = (G["w1"] - G["w0"] + 1) / 252.0
    if item == "A3-14":
        balls = {"W1": [("W1", x) for x in EXOPT], "Y1": [("Y1", x) for x in EXOPT],
                 "Y2": [("Y2in", x) for x in EXOPT] + [("Y2out", x) for x in EXOPT], "Y3": [("Y3", x) for x in EXOPT],
                 "Y4": [(c_, x) for c_ in ("Y4_MA5", "Y4_MA10") for x in EXOPT], "Y5": [("Y5", x) for x in EXOPT]}
        overs = ("Y2out", "Y4_MA5", "Y4_MA10", "Y5"); ents = ("W1", "Y1", "Y2in", "Y3")
    else:
        balls = {"F1": [(c_, x) for c_ in ("F1", "F1c") for x in EXOPT], "O1": [("O1", x) for x in ("OWN",) + EXOPT], "S1": [("S1", x) for x in EXOPT]}
        overs = ("S1",); ents = ("F1", "F1c", "O1")
    # ── 退化（逐欄）
    DEG = {}; DINFO = {}
    for code in ents:
        for col in ("合併", "只400"):
            nn = inwin_count(code, col)
            bad = nn < 200 or nn / yrs_main < 10
            DINFO["%s（%s）主窗事件" % (code, col)] = {"事件": nn, "年均": round(nn / yrs_main, 1), "退化": bad}
            for x in (("OWN",) + EXOPT if code == "O1" else EXOPT):
                DEG[(code, x, col)] = ["主窗事件 ＜200 或年均 ＜10"] if bad else []
        for x in (("OWN",) + EXOPT if code == "O1" else EXOPT):
            Fe0 = ext_entry_rows(code, x, SG_["探索"])
            for col in ("合併", "只400"):
                Fe = Fe0[(np.ones(len(Fe0), bool) if col == "合併" else Fe0["m4"].to_numpy(bool))]
                tl = float(Fe["endhold"].mean()) if len(Fe) else np.nan
                DINFO["%s×%s（%s）探索段段尾未出場" % (code, x, col)] = round(tl * 100, 1) if np.isfinite(tl) else None
                if np.isfinite(tl) and tl > 0.5:
                    DEG[(code, x, col)].append("探索段段尾未出場 ＞50%")
    Rm = base_rows((G["w0"], G["w1"])); Rx = base_rows(SG_["探索"])
    RT_main = {code: rule_trig(Rm, code, G["w1"]) for code in overs}
    RT_x = {code: rule_trig(Rx, code, s1) for code in overs}
    for code in overs:
        for x in EXOPT:
            dm = trig_first(Rm, lambda S, x=x: S[x], G["w1"]); dr = RT_main[code]
            win = (dr >= 0) & ((dm < 0) | (dr < dm))
            dmx = trig_first(Rx, lambda S, x=x: S[x], s1); drx = RT_x[code]
            tailx = (dmx < 0) & (drx < 0)
            for col in ("合併", "只400"):
                cm = np.ones(len(Rm), bool) if col == "合併" else Rm["m4"].to_numpy(bool)
                cx = np.ones(len(Rx), bool) if col == "合併" else Rx["m4"].to_numpy(bool)
                nn = int((win & cm).sum()); tl = float(tailx[cx].mean()) if cx.any() else np.nan
                bad = []
                if nn < 200 or nn / yrs_main < 10:
                    bad.append("主窗有效觸發 ＜200 或年均 ＜10")
                if np.isfinite(tl) and tl > 0.5:
                    bad.append("探索段段尾未出場 ＞50%")
                DEG[(code, x, col)] = bad
                DINFO["%s×%s（%s）" % (code, x, col)] = {"主窗基準列": int(cm.sum()), "有效觸發": nn, "年均": round(nn / yrs_main, 1),
                                                        "探索段段尾未出場%": round(tl * 100, 1) if np.isfinite(tl) else None, "退化": bad}
    log("[%s] 退化格 %s" % (item, sorted("%s×%s（%s）" % k for k, v in DEG.items() if v)))
    # ── 探索段全部格（合併）
    arms = {}
    BX = {}
    for g_, lst in balls.items():
        for code, x in lst:
            if code in overs:
                F, _, _ = over_F(Rx, code, x, s1, rt=RT_x[code])
            else:
                F = ext_entry_rows(code, x, SG_["探索"])
            arms[("探索", code, x)] = mk_arm(col_sel(F, "合併"), SG_["探索"])
    res = run_arms(arms, procs, nseed, "%s 探索 %d 格" % (item, len(arms)))
    EXP = {k: agg(v, B["探索"], SG_["探索"]) for k, v in res.items()}
    for k in EXP:
        EXP[k]["訊號列數"] = arms[k]["n_rows"]
    chosen = {}
    for g_, lst in balls.items():
        cands = [((code, x), EXP[("探索", code, x)]) for code, x in lst if not DEG.get((code, x, "合併"))]
        chosen[g_] = pick(cands) if cands else None
    log("[%s] 挑格 %s" % (item, chosen))
    # ── 確認段
    Rc = base_rows(SG_["確認"]); RT_c = {code: rule_trig(Rc, code, s1c) for code in overs}
    JUD = {}; CROWS = {}
    for g_, k in chosen.items():
        if k is None:
            JUD[g_] = {"標籤": "不可判定（全部格依構造退化）"}; continue
        code, x = k
        if code in overs:
            F, _, _ = over_F(Rc, code, x, s1c, rt=RT_c[code])
        else:
            F = ext_entry_rows(code, x, SG_["確認"])
        CROWS[g_] = F
        deg4 = bool(DEG.get((code, x, "只400")))
        JUD[g_] = judge_block("%s|%s|%s" % (item, code, x), F, nseed, procs, nfake, B["確認"], SG_["確認"], deg400=deg4)
        JUD[g_]["只400退化"] = DEG.get((code, x, "只400"))
    # ── 出場顆：加 vs 不加（同基準同均線；確認段兩欄）＋ 原 H 格描述（確認、合併）
    ADD = {}; arms = {}
    for g_, k in chosen.items():
        if k is None or k[0] not in overs:
            continue
        F0, _, _ = over_F(Rc, None, k[1], s1c)
        for col in ("合併", "只400"):
            arms[("BASE", k[1], col)] = mk_arm(col_sel(F0, col), SG_["確認"])
    Hdesc = {}
    for code in overs:
        for H in (20, 60, 120):
            arms[("H", code, H)] = mk_arm(col_sel(over_H_F(Rc, code, H, s1c, rt=RT_c[code]), "合併"), SG_["確認"])
    for H in (20, 60, 120):
        arms[("H", "BASE", H)] = mk_arm(col_sel(over_H_F(Rc, None, H, s1c), "合併"), SG_["確認"])
    res = run_arms(arms, procs, nseed, "%s 加減不加＋H 描述" % item)
    AG = {kk: agg(v, B["確認"], SG_["確認"]) for kk, v in res.items()}
    for g_, k in chosen.items():
        if k is None or k[0] not in overs:
            continue
        ADD[g_] = {}
        for col in ("合併", "只400"):
            b = AG[("BASE", k[1], col)]; o_ = JUD[g_]["欄"][col]
            ADD[g_][col] = {"年化差（點）": (o_["年化中位"] - b["年化中位"]) * 100, "回落差（點）": (o_["回落中位"] - b["回落中位"]) * 100,
                            "不加_年化": b["年化中位"], "不加_回落": b["回落中位"], "不加_標籤": b["標籤"]}
    for code in overs:
        for H in (20, 60, 120):
            a = AG[("H", code, H)]; b = AG[("H", "BASE", H)]
            Hdesc["%s|H%d" % (code, H)] = {"年化中位": a["年化中位"], "回落中位": a["回落中位"], "標籤（描述）": a["標籤"],
                                           "不加_年化": b["年化中位"], "加減不加_年化差（點）": (a["年化中位"] - b["年化中位"]) * 100}
    # ── A3-15 事件數描述
    EVD = {}
    if item == "A3-15":
        w0, w1 = G["w0"], G["w1"]
        f1 = []; f1c = 0; ov = 0; o1a = []; s1n = 0
        for s, S in G["SIG"].items():
            st = G["ST"][s]
            for t in S["F1"]:
                if w0 <= t <= w1 and st["member"][t]:
                    f1.append((s, t)); ov += int(np.any(np.abs(S.get("E:ENG", np.zeros(0, int)) - t) <= 2))
                    f1c += int(np.any((S["F1c"] > t) & (S["F1c"] <= t + 5)))
            for kk, jj in S["O1_all"]:
                if w0 <= kk <= w1 and st["member"][kk]:
                    o1a.append(jj >= 0)
            s1n += int(((S["S1"] >= w0) & (S["S1"] <= w1)).sum())
        EVD = {"F1 原版事件（主窗、在母體）": len(f1), "F1 確認率": f1c / max(1, len(f1)), "F1 與多頭吞噬 ±2 日重疊率": ov / max(1, len(f1)),
               "O1 跌破事件": len(o1a), "O1 3 日內站回率": float(np.mean(o1a)) if o1a else np.nan,
               "S1 每檔每年觸發（全訊號、主窗）": s1n / max(1, len(G["SIG"])) / yrs_main}
    # ── 一直沒出場的那批（確認段判定格、事件層、合併）
    NEV = {}
    for g_, F in CROWS.items():
        Fm = col_sel(F, "合併"); m = Fm["endhold"].to_numpy(bool)
        ur = Fm["g"].to_numpy()[m]; hd = s1c - Fm["e"].to_numpy()[m]
        NEV[g_] = {"筆數": int(m.sum()), "占列": float(m.mean()) if len(m) else np.nan,
                   "段尾未實現毛報酬中位": float(np.median(ur)) if m.any() else None, "p10": float(np.percentile(ur, 10)) if m.any() else None,
                   "p90": float(np.percentile(ur, 90)) if m.any() else None, "最長持有（交易日）": int(hd.max()) if m.any() else 0}
    # ── 彙總
    cells = {g_: JUD[g_]["標籤"] for g_ in balls}
    N = len(balls)
    J = common_meta(item)
    J.update({"退化（seq248 ④、逐欄）": {"明細": DINFO, "退化格": sorted("%s×%s（%s）" % k for k, v in DEG.items() if v)},
              "探索段（合併）": {"%s|%s" % (k[1], k[2]): slim(v) for k, v in EXP.items()},
              "探索段挑格": {g_: ("%s|%s" % k if k else "依構造不可判定（全部格退化）") for g_, k in chosen.items()},
              "確認段": {}, "出場顆_加減不加（確認段）": ADD, "描述": {"原 H 基準格（確認、合併）": Hdesc, "一直沒出場的那批（確認、事件層、合併）": NEV, "事件數": EVD},
              "W2（基準成員）": G["W2cnt"], "基準": B})
    for g_, k in chosen.items():
        if k is None:
            J["確認段"][g_] = {"標籤": JUD[g_]["標籤"]}; continue
        J["確認段"][g_] = {"格": "%s|%s" % k, "標籤": JUD[g_]["標籤"], "欄": {c_: slim(v) for c_, v in JUD[g_]["欄"].items()}, "描述": JUD[g_]["描述"],
                           "假訊號": JUD[g_]["假訊號"], "隨機也做得到": JUD[g_]["隨機也做得到"], "只400退化": JUD[g_]["只400退化"]}
    wk = save_work(item, {"seeds": {g_: JUD[g_]["_seeds"] for g_ in CROWS}, "chosen": chosen,
                          "rows": {g_: CROWS[g_][["sid", "t", "e", "m4", "m5", "xpos", "g", "endhold", "why", "pbx", "f50x", "d"]] for g_ in CROWS}})
    J["逐筆檔sha（repo外）"] = {wk[0]: wk[1]}
    Bc = B["確認"]
    three = {}
    for col in ("合併", "只400", "只500"):
        parts = []
        for g_, k in chosen.items():
            if k is None:
                parts.append("%s 依構造不可判定" % g_)
            else:
                parts.append("%s（%s）%s" % (g_, "|".join(k), card_line(JUD[g_]["欄"][col], Bc)))
        three[col] = "；".join(parts) + ("（描述、⛔ 不判）" if col == "只500" else "")
    sent = []
    for g_, k in chosen.items():
        if k is None:
            sent.append("%s 全部格事件不足 ⇒ 依構造不可判定" % g_); continue
        q = JUD[g_]["欄"]["合併"]; lab = JUD[g_]["標籤"]; pre = "隨機也做得到：" if JUD[g_]["隨機也做得到"] else ""
        s_ = "%s%s（%s）%s：合併年化 %+.1f%%／回落 %+.1f%%" % (pre, g_, "|".join(k), lab, q["年化中位"] * 100, q["回落中位"] * 100)
        if g_ in ADD:
            s_ += "；加這條 vs 不加（同均線基準）年化差 %+.1f 點、回落差 %+.1f 點" % (ADD[g_]["合併"]["年化差（點）"], ADD[g_]["合併"]["回落差（點）"])
        sent.append(s_)
    dev = DEV_COMMON + ["出場顆（%s）主臂改「基準跌破 MA10／20／60＋本條」，原「基準抱 H 日＋本條」降描述（G9；seq308／brief）" % "、".join(overs),
                        "原「主窗全段另判、兩段都過才合格」⇒ 只看確認段（seq319 Q1）", "單筆層、早年段、全市場基準描述未做（G14）"]
    if item == "A3-14":
        dev.append("W2 年線戰法另立 A4-9；本件只把季營收版 W2（P20）放進出場顆基準「五顆任一」")
    else:
        dev.append("S1 基準＝五顆進場任一（W2 用季營收版 P20）；F1 與多頭吞噬重疊率照報")
    prior = prior_ext(item, JUD, chosen, ADD)
    J["卡片"] = {"件": item, "名稱": NAMES[item], "台股原登錄": "%s（%s）" % REGTW[item],
                "出場型": "① 條件（進場顆：跌破 MA10／20／60 或作者自帶；出場顆：均線基準＋作者出場，誰先到先出；⛔ 無最長天數）",
                "N": N, "標籤": lab_summary(cells), "格標籤": cells, "判定格": {g_: ("%s|%s" % k if k else "—") for g_, k in chosen.items()},
                "三欄": three, "條件出場必報": {g_: must_report(JUD[g_]["欄"]["合併"]) for g_ in CROWS},
                "結果句": "結論：%s。⚠ 事後追加；%s、%s、%s。" % ("；".join(sent), C.IDEA, C.NO_EARLY, C.SURV),
                "敏感度_ret50": ret50_line(JUD, list(CROWS)), "偏離": dev,
                "補讀法": ["G1～G14（docstring）", "seq248 ④ 退化逐欄判；出場顆的事件 ＝ 主窗基準列中本條先於均線基準觸發的列（台股原程式「有效觸發」讀法）"],
                "先驗紀錄": prior}
    write_item(item, J)
    return J


def prior_ext(item, JUD, chosen, ADD):
    if item == "A3-14":
        ent = [g for g in ("W1", "Y1", "Y2", "Y3") if chosen.get(g) and chosen[g][0] not in ("Y2out",)]
        p1 = all(JUD[g]["標籤"] == "不合格" or JUD[g]["標籤"].startswith("不可判定") for g in ("W1", "Y1", "Y2", "Y3"))
        p1b = any(JUD[g]["標籤"].startswith("不可判定") for g in JUD)
        outs = [g for g in ADD]
        p2 = all(ADD[g]["合併"]["年化差（點）"] <= 0 for g in outs) if outs else None
        return ("台股先驗（照實記）：① 五顆進場確認段都不合格（約六成五）⇒ %s；至少一顆依構造不可判定（約六成）⇒ %s；② 出場顆「加 vs 不加」確認段年化都不比不加高（約七成）⇒ %s；"
                "③ 單筆層、④ 假訊號過半 ⇒ 單筆層本檔未做；假訊號 p ≥ 0.05 的格 %d／%d" % ("對" if p1 else "錯", "對" if p1b else "錯",
                                                                         "—" if p2 is None else ("對" if p2 else "錯"),
                                                                         sum(1 for g in JUD if JUD[g].get("隨機也做得到")), sum(1 for g in JUD if "假訊號" in JUD[g])))
    p1 = all(JUD[g]["標籤"] == "不合格" or JUD[g]["標籤"].startswith("不可判定") for g in ("F1", "O1"))
    p1b = JUD["F1"]["標籤"].startswith("不可判定")
    p3 = ADD["S1"]["合併"]["年化差（點）"] <= 0 if "S1" in ADD else None
    return ("台股先驗（照實記）：① F1、O1 確認段都不合格（約六成五）⇒ %s；F1 依構造不可判定（約四成）⇒ %s；② F1 與多頭吞噬重疊率 ≥ 五成（約六成）⇒ 見描述事件數；"
            "③ S1「加 vs 不加」確認段年化不比不加高（約七成）⇒ %s；④ O1 單筆層 ⇒ 本檔未做" % ("對" if p1 else "錯", "對" if p1b else "錯", "—" if p3 is None else ("對" if p3 else "錯")))


# ═════════════ 主流程 ═════════════
def run(procs=2, lim=None, nseed=C.NSEED, nfake=N_FAKE, items=("A3-7", "A3-6", "A3-15", "A3-14")):
    t0 = time.time()
    setup(lim)
    G["nseed"] = nseed
    log("===== researchUSA3_g3 run procs=%d lim=%s seeds=%d fake=%d %s =====" % (procs, lim, nseed, nfake, pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")))
    signals(procs)
    G["verify"] = verify_prep()
    log("[核對 prep] 比對 %d 列、不同 %d：%s｜W2 同 %s" % (G["verify"].get("比對列", 0), len(G["verify"].get("不同", [])), G["verify"].get("不同", [])[:5], G["verify"].get("W2_同")))
    C.pf_setup(G["ST"], G["sids"], G["cal"], G["w0"], G["w1"])
    G["coverage"] = C.coverage_cached(G["cal"], G["w0"], G["w1"]) if not lim else {}
    out = {}
    for it in items:
        t1 = time.time()
        if it == "A3-6":
            J = run_a36(procs, nseed, nfake)
        elif it == "A3-7":
            J = run_a37(procs, nseed, nfake)
        else:
            J = ext_item(it, procs, nseed, nfake)
        J_path = os.path.join(OUTD if not lim else os.path.join(WORK, "lim"), "%s.json" % it)
        Jd = json.load(open(J_path, encoding="utf-8"))
        Jd["訊號重現核對（對 prep）"] = G["verify"]; Jd["存活者偏差"] = {"句": C.SURV, "覆蓋": G["coverage"]}; Jd["耗時秒"] = round(time.time() - t1)
        C.jdump(Jd, J_path)
        out[it] = J["卡片"]["標籤"]
        log("[%s] 完成 %.0fs ⇒ %s" % (it, time.time() - t1, out[it]))
    log("[全部完成] %.0fs" % (time.time() - t0))
    return out


# ═════════════ check（獨立寫法：不呼叫本檔算報酬的函式）═════════════
def _fsum_ma(c, n):
    out = np.full(len(c), np.nan)
    for i in range(n - 1, len(c)):
        out[i] = math.fsum(c[i - n + 1:i + 1]) / n
    return out


def check(lim=None, n_seed_check=3):
    """① 抽樣檔：均線穿越日自己重算（math.fsum）對訊號快取；② 判定格：從快取訊號自己重建列（出場日、毛報酬）對逐筆檔；
    ③ 判定格抽 3 顆種子：自己用 research11.simulate_mtm 跑、自己算年化回落，對逐種子結果；④ SPY 層自己重寫一次對 json。"""
    meta, ST = C.load_cache()
    if lim:
        ST = {k: ST[k] for k in sorted(ST)[:lim]}
    tag = ("_lim%d" % lim) if lim else ""
    SIG = pickle.load(open(os.path.join(WORK, "sig%s.pkl" % tag), "rb")); SIG.pop("__W2__", None)
    cal = meta["cal"]; w0, w1, sp, c0 = meta["w0"], meta["w1"], meta["sp"], meta["c0"]
    rng = np.random.default_rng(7)
    out = {}
    # ① 均線穿越
    nd = 0; ns = 0
    for s in rng.choice(sorted(ST), size=min(25, len(ST)), replace=False):
        st = ST[s]; b = np.flatnonzero(st["valid"]); cb = st["C"][b]
        for k in (10, 20, 60):
            ma = _fsum_ma(cb, k)
            x = [int(b[i]) for i in range(1, len(b)) if np.isfinite(ma[i - 1]) and cb[i - 1] >= ma[i - 1] and cb[i] < ma[i]]
            ns += 1; nd += int(list(SIG[s]["MA%d" % k]) != x)
    out["均線穿越（抽 25 檔×3）"] = (ns, nd)
    # 引擎設定
    sids = sorted(ST)
    z = np.zeros(len(cal), bool)
    trad = {s: {"trd": ST[s]["valid"], "up_o": z, "dn_o": z, "dn_c": z} for s in sids}
    dl = C.TRD.delist_status(trad, cal)
    closes = {s: ST[s]["closes"] for s in sids}; opens = {s: ST[s]["opens"] for s in sids}
    R11.COST = U.COST_ROUNDTRIP                      # 美股成本 0.05%（引擎全域參數；台股預設 0.585% 不可沿用）
    res = {}
    for item in ("A3-6", "A3-7", "A3-14", "A3-15"):
        p = os.path.join(WORK, "%s%s.pkl" % (item, tag))
        jp = os.path.join(OUTD if not lim else os.path.join(WORK, "lim"), "%s.json" % item)
        if not os.path.exists(p) or not os.path.exists(jp):
            res[item] = {"件": item, "抽樣": 0, "不同": 0, "說明": "尚未產出"}
            continue
        Wd = pickle.load(open(p, "rb")); Jd = json.load(open(jp, encoding="utf-8"))
        n_ck = 0; n_bad = 0; notes = []
        for cell, F in Wd["rows"].items():
            F = F.reset_index(drop=True)
            # ② 抽 300 列自己重建出場日與毛報酬
            idx = rng.choice(len(F), size=min(300, len(F)), replace=False) if len(F) else []
            for i in idx:
                r = F.iloc[int(i)]; s = r["sid"]; st = ST[s]; e = int(r["e"]); t = int(r["t"])
                if e != t + 1 or not (np.isfinite(st["opens"][e]) and st["opens"][e] > 0):
                    n_bad += 1; notes.append("列進場錯 %s %d" % (s, e)); continue
                x = int(r["xpos"]); o = st["opens"][e]
                if bool(r["endhold"]):
                    gg = st["closes"][x] / o - 1.0
                else:
                    ox = st["opens"][x]; gg = (ox if np.isfinite(ox) and ox > 0 else st["closes"][x]) / o - 1.0
                n_ck += 1
                if not (abs(gg - float(r["g"])) < 1e-12):
                    n_bad += 1; notes.append("毛報酬不同 %s %d" % (s, e))
                if not bool(r["endhold"]) and int(r["d"]) + 1 != x:
                    n_bad += 1; notes.append("出場日不同 %s %d" % (s, e))
            # 出場條件重驗（只驗「均線跌破」與「X」單一訊號的格：d 必須是 ≥ e 的第一個該訊號日）
            ch = Wd["chosen"].get(cell) if isinstance(Wd["chosen"], dict) else None
            xo = None
            if item == "A3-7" and ch:
                xo = ch
            elif item in ("A3-14", "A3-15") and ch and ch[0] not in ("Y2out", "Y4_MA5", "Y4_MA10", "Y5", "S1") and ch[1] != "OWN":
                xo = ch[1]
            if xo is not None:
                for i in idx[:100]:
                    r = F.iloc[int(i)]; s = r["sid"]; e = int(r["e"]); seg_end = w1
                    arr = [int(v) for v in SIG[s][xo] if e <= v <= seg_end]
                    exp_d = arr[0] if arr else -1
                    n_ck += 1
                    if exp_d != int(r["d"]):
                        n_bad += 1; notes.append("觸發日不同 %s %d" % (s, e))
            # ③ 種子重跑
            seeds = Wd["seeds"].get(cell, {})
            for col, lst in seeds.items():
                if col == "只500" or not lst:
                    continue
                Fc = F[~F["pbx"].to_numpy(bool)]
                if col == "只400":
                    Fc = Fc[Fc["m4"].to_numpy(bool)]
                Fc = Fc.sort_values(["e", "sid"])
                sig = pd.DataFrame({"sid": Fc["sid"].to_numpy(), "entry_pos": Fc["e"].to_numpy(np.int64), "xpos_A3": Fc["xpos"].to_numpy(np.int64), "g_A3": Fc["g"].to_numpy()})
                kw = {}
                if item == "A3-6" and cell == "ST" and Wd["ch_st"][3] == "TP50h":
                    kw = {"trim_rule": {"kind": "gain", "x": 0.5, "frac": 0.5}}
                for j in rng.choice(len(lst), size=min(n_seed_check, len(lst)), replace=False):
                    seed, cg, mg = lst[int(j)]
                    o_ = R11.simulate_mtm(sig, "A3", 8, np.random.default_rng(seed), closes, opens, len(cal), return_equity=True, pick=None, d_max=None,
                                          queue_days=0, cash_mode="zero", tradable=trad, delist=dl, **kw)
                    eq = np.asarray(o_["equity"], float)[c0:w1 + 1]
                    cg2 = (eq[-1] / eq[0]) ** (252.0 / len(eq)) - 1.0
                    mg2 = float(((eq - np.maximum.accumulate(eq)) / np.maximum.accumulate(eq)).min())
                    n_ck += 1
                    if not (abs(cg2 - cg) < 1e-10 and abs(mg2 - mg) < 1e-10):
                        n_bad += 1; notes.append("種子 %d %s %s 年化 %.6g vs %.6g" % (seed, cell, col, cg2, cg))
        # ④ SPY 層
        if item == "A3-6" and "SPY層" in Jd:
            d = pd.read_csv(U._p("macro", "yahoo_SPY.csv"), dtype={"date": str}); d.index = pd.to_datetime(d["date"]); d = d.reindex(cal)
            k = d["adjclose"] / d["close"]; o = (d["open"] * k).to_numpy(float); c = (d["close"] * k).to_numpy(float)
            SG2 = PREP.spy_layer(cal)
            ent = set(np.concatenate([np.asarray(SG2.get("E:" + x, []), int) for x in RS.E1 + RS.E2]).tolist())
            ex = set(np.concatenate([np.asarray(SG2.get("X:" + x, []), int) for x in RS.XS]).tolist())
            cff = pd.Series(c).ffill().to_numpy()
            for segn, (a0, a1) in (("確認", (c0, w1)), ("探索", (w0, sp))):
                pos = False; pend = None; val = 1.0; units = 0.0; eqv = []; base_amt = 0.0
                if (a0 - 1) in ent and (a0 - 1) not in ex:
                    pend = "buy"
                for t in range(a0, a1 + 1):
                    if pend and np.isfinite(o[t]) and o[t] > 0:
                        if pend == "sell" and pos:
                            val = units * o[t] - base_amt * C.COST; pos = False      # 引擎慣例：成本 ＝ 買進金額 × 來回成本，出場一次扣
                        elif pend == "buy" and not pos:
                            units = val / o[t]; base_amt = val; pos = True
                        pend = None
                    eqv.append(units * cff[t] if pos else val)
                    if pos and t in ex:
                        pend = "sell"
                    elif (not pos) and t in ent and t not in ex and t + 1 <= a1:
                        pend = "buy"
                    elif pend == "sell" and not pos:
                        pend = None
                eqv = np.array(eqv); cg2 = (eqv[-1] / eqv[0]) ** (252.0 / len(eqv)) - 1.0
                n_ck += 1
                if abs(cg2 - Jd["SPY層"][segn]["年化"]) > 1e-10:
                    n_bad += 1; notes.append("SPY 層 %s 年化 %.8f vs %.8f" % (segn, cg2, Jd["SPY層"][segn]["年化"]))
        res[item] = {"件": item, "抽樣": n_ck, "不同": n_bad, "說明": ("；".join(notes[:8]) if notes else "逐列出場日／毛報酬、出場觸發日、引擎種子年化回落、SPY 層全同")}
    res["均線穿越（共用）"] = {"抽樣": out["均線穿越（抽 25 檔×3）"][0], "不同": out["均線穿越（抽 25 檔×3）"][1]}
    return res


if __name__ == "__main__":
    a = sys.argv
    procs = int(a[a.index("--procs") + 1]) if "--procs" in a else 2
    lim = int(a[a.index("--limit") + 1]) if "--limit" in a else None
    nseed = int(a[a.index("--seeds") + 1]) if "--seeds" in a else C.NSEED
    nfake = int(a[a.index("--fake") + 1]) if "--fake" in a else N_FAKE
    items = tuple(a[a.index("--items") + 1].split(",")) if "--items" in a else ("A3-7", "A3-6", "A3-15", "A3-14")
    if "--run" in a:
        print(json.dumps(run(procs, lim, nseed, nfake, items), ensure_ascii=False))
    if "--check" in a:
        print(json.dumps(check(lim), ensure_ascii=False, indent=1))
