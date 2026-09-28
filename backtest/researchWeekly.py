# -*- coding: utf-8 -*-
"""PREREG週線 seq1（台股策略線 登錄 sha 3c7ad365dc7a2f33；裁定 seq271 §三 發號；N：甲單筆 16 格、乙組合 ＋1）——回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchWeekly [--procs 2] [--fakes 30] [--xreps 100]
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchWeekly_check.py

使用者原話（逐字）：「我想問你如果改看周線會不會有新東西？」（⇒ 登錄 ⇒ 使用者：「好」）
⚠ 共用閘「-KY創」補丁（裁定 seq271 §二）另一子代理在做、預設關 ⇒ 本件照現行 universe_gate.gate3 跑（寫進報告）。
═══ 週 K（登錄 §一，寫死）═══
 W1 一週 ＝ 同一個「週一起算」的日曆週裡的交易日（接合日曆／各世界日曆）；週開 ＝ 該股該週第一根有效 K 棒開盤、週收 ＝ 最後一根收盤、
    週高低 ＝ 期間極值、週量 ＝ 成交股數和；還原價（同日線）；該股該週沒有有效 K 棒 ⇒ 沒有週 K（指標序列跳過那週）
    週的加減（「下週」、第 w＋k 週、前 4 週、8 週內、第 m／C 週）一律以「有交易日的日曆週」計（整週休市的週不算，例：農曆年）
 W2 硬斷點 ＝ research11.load_bars 的壞根（相位事件、斷點 applies、≥ 5 日缺口）；壞根所在週與前後各 1 週不產生訊號
 W3 判定點 ＝ 週收盤；執行 ＝ 下一個日曆週第一個交易日開盤
═══ 甲 週線訊號單測（登錄 §二）＋ 本線讀法（A 標，⭐ 看任何數字前寫死）═══
 S1 KD(9,3,3)：RSV ＝ (收 − 9 週最低) ÷ (9 週最高 − 9 週最低) × 100（區間 0 ⇒ 50）；K ＝ ⅔K前 ＋ ⅓RSV、D ＝ ⅔D前 ＋ ⅓K，起始 K ＝ D ＝ 50
    訊號：K前 ≤ D前 且 K ＞ D 且 K ≤ 30
 S2 MACD(12,26,9)：EMA α ＝ 2÷(n＋1)、以第一個週收起算；DIF ＝ EMA12 − EMA26、DEA ＝ EMA9(DIF)、柱 ＝ DIF − DEA；訊號：柱前 ≤ 0 ＜ 柱
 S3 RSI(14) Wilder：第 14 個差值起用前 14 個平均、之後 (前×13＋今)÷14；平均跌 0 ⇒ 100；訊號：RSI前 ＜ 30 ≤ RSI
 S4 週實體 收÷開 − 1 ≥ 8%、週收 ＞ 前 26 週最高週收、週量 ≥ 前 10 週平均 × 2
 A1 指標從該股第一根週 K 起算；訊號週在該股週序列的位置 ≥ 52（一年暖機；四個訊號同一條）
 A2 同一檔同一訊號：訊號週 − 上一個保留訊號週 ≤ 8 ⇒ 併掉（先 W2 排除、再合併、再做下面的剔除）
 A3 報酬 R_k ＝ c_ff[第 w＋k 週最後一個交易日] ÷ 開[第 w＋1 週第一個交易日] − 1（c_ff ＝ 收盤 ffill ⇒ 停止交易以最後收盤計＝強制出場）
    剔除：第 w＋k 週沒有完整落在資料內（登錄「持有期跨資料尾不進」）｜進場日不可買（無成交、開盤無效、開盤漲停）｜
          訊號週第一天到出場日之間有壞根（同 PREREG事件 E5 的讀法）｜load_bars 不足 260 根
 A4 母體 ＝ researchEvt.eligibility（W1 eligible、含已下市、panel_ext；2004～2012-05 早年 liq∧bars；2015 補定），取訊號週最後一個交易日；
    2015 以前只有上市（接合版面早年段）；另要求該股該週有週 K、進場可買、R_k 可算
 A5 基準① ＝ 同週母體其他股 R_k 等權；基準②（主）＝ 同週母體依前 4 週報酬（週收[w] ÷ 週收[w−4] − 1，c_ff）分十分位（avgdown.deciles）、同十分位其他股 R_k 等權
    X ＝ R_k − 基準；D ＝ 訊號 X 平均；CI ＝ 訊號週曆月分群 CR0（research11.cl_stats）
 A6 n_eff ＝ min(筆數, 段內 k 週區段數)；＜ 30 出口①（不可判定、不計入 Bonferroni k）、30～99 ②、≥ 100 ③；Bonferroni α ＝ 0.05／k（k ＝ 該段基準② 可判定格數）
 A7 成本帶（借券法人件修正後讀法）：Bonferroni CI 下緣 − 0.585% ＞ 0 ⇒ 測得出（＋）；上緣 ＋ 0.585% ＜ 0 ⇒ 測得出（−）；否則測不出（|D| ＜ 成本不翻成反向）
 A8 「穩」（seq253）：相鄰持有期（4–8–12–26）本身也過 Bonferroni＋成本帶、同方向才寫；否則「方向一致，但只有 k 週過門檻」
 A9 假訊號：同股隨機週 30 次——每個真訊號換成同一檔、同段、基準② X 可算的週（均勻、可重複）；rng default_rng([20260928, 訊號, k, 段, r])
    假訊號臂 ＝ 30 次合併（曆月分群 CR0、同一個 Bonferroni z、同成本帶）⇒「過」＝ 測得出（＋）；另報 p ＝ 30 次平均 ≥ 真 D 的比例
 A10 段（訊號週最後交易日所在月）：探索 2017-03～2021-12｜確認 2022-01～2026-08｜早年 2004～2014（只上市）
 A11 「可用」＝ 確認段基準② 測得出（＋）且 早年基準② D ＞ 0 且 確認段假訊號臂不過
═══ 乙 營量 v1 週收盤出場（登錄 §三）＋ 本線讀法（B 標）═══
 進場 ＝ 營量 v1 正式規則一字不動（T1、stop_force 開、relvol、20 檔；researchYLexit3_b.worlds 的 AND 表；只換每筆 xpos／g）
 B1 週序號：進場日所在日曆週 ＝ 第 1 週；「持有滿 m 週後」＝ 第 m 週（含）起每週收盤檢查
 B2 週收 ＝ 該股該週最後一根有效 K 棒收盤；週 MA(L) ＝ 該股最近 L 根週 K（含當週）週收平均；該週沒有週 K ⇒ 不檢查
 B3 觸發 ⇒ 下一個日曆週起第一根有效 K 棒開盤賣；未觸發 ⇒ 第 C 週最後一根有效 K 棒收盤賣
 B4 持有中碰到壞根 ⇒ 壞根前一根收盤出（計數必報）；早年 R8 截同 researchYLexit.exits_H；資料尾：股票活到日曆尾 ⇒ T1 補（xpos ＝ ncal、末日收盤）、
    停止交易 ⇒ 引擎 stop_force
 B5 格：L {5,10,20} × m {4,8} × C {26,52} ＝ 12；不停損；退化（探索段平均持股 ＜ 10 或現金 ＞ 30%）挑前排除
    挑：探索段 先合格、再比值（年化÷|回落|）⇒ 確認段、早年段判、取較嚴；主比較 ＝ 對營量 v1 同段每日報酬配對差（曆月 CR0）
    「比營量 v1 好」＝ 確認段 CI 不含 0（下緣 ＞ 0）且 早年差同向（＞ 0）；只一段 ⇒ 不穩
 B6 假訊號臂（出場週隨機、同次數）：挑中格裡「週收觸發」出場的每一筆，把觸發週換成 [m, C] 均勻隨機一週（照 B3 賣）；觸頂 C、壞根、截尾的不動；xreps 次
 B7 必報：平均持有交易日、超過 60 天比例、觸頂 C 比例、每年換手與成本（組合實際成交、種子 0）
 B8 新規矩 ③：挑中格確認或早年「合格／另列」⇒ 另跑 檔數 10／30（描述）；停損、停利類與本件「不停損、只換出場」衝突 ⇒ 不跑（寫明）
 ⛔ 結果句固定附：「使用者現行規則＝第 60 天收盤賣」；好也只進前瞻並列、⛔ 不改營量 v1
 閘：營量 v1 ＝ resultsT1fix c13 t1（主）／resultsYLexit3 營量v1 種子 0（主、早年）；登錄全文 sha（去 pw1 行）＝ 3c7ad365dc7a2f33
輸出 backtest/resultsWeekly/
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import sys
import time
from multiprocessing import Pool
from statistics import NormalDist

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import tradability as TR
from backtest import universe_gate as UG
from backtest import research11 as R11
from backtest import rerun17 as RR
from backtest import avgdown as AV
from backtest import researchEvt as EV
from backtest import researchYLexit as YX
from backtest import researchYLexit3_b as YB
from backtest import chart_svg as CS

ST = EV.ST
OUT = "backtest/resultsWeekly"
F_HTML = "週線兩件_20260928.html"
RAW = "我想問你如果改看周線會不會有新東西？"
PREREG_SHA = "3c7ad365dc7a2f33"
USER_RULE = "使用者現行規則＝第 60 天收盤賣"
COST = 0.00585
KS = (4, 8, 12, 26)
SIGS = ("S1", "S2", "S3", "S4")
SNAME = {"S1": "週 KD 低檔金叉", "S2": "週 MACD 翻正", "S3": "週 RSI 站回 30", "S4": "週長紅突破"}
SEGA = {"早年": ("2004-01", "2014-12"), "探索": ("2017-03", "2021-12"), "確認": ("2022-01", "2026-08")}
WARM = 52; DEDUP = 8
LS = (5, 10, 20); MS = (4, 8); CS_ = (26, 52)
ORDER = {"不合格": 0, "另列": 1, "合格": 2}
_G: dict = {}
_W: dict = {}


def weeks_of(cal):
    """日曆週（週一起算）：回 每日週號 wk、每週第一日 wf、最後一日 wl。"""
    mon = (cal - pd.to_timedelta(cal.weekday, unit="D")).normalize()
    wk = pd.factorize(mon)[0]
    nw = int(wk.max()) + 1
    wf = np.full(nw, -1); wl = np.full(nw, -1)
    for i, w in enumerate(wk):
        if wf[w] < 0:
            wf[w] = i
        wl[w] = i
    return wk, wf, wl


# ═════════════ 週線指標（甲、查核共用定義；查核另寫一份） ═════════════
def kd(C, H, L):
    n = len(C); K = np.full(n, np.nan); Dd = np.full(n, np.nan); k0 = d0 = 50.0
    for t in range(n):
        if t < 8:
            continue
        lo, hi = L[t - 8:t + 1].min(), H[t - 8:t + 1].max()
        rsv = 50.0 if hi - lo <= 0 else (C[t] - lo) / (hi - lo) * 100
        k0 = k0 * 2 / 3 + rsv / 3; d0 = d0 * 2 / 3 + k0 / 3
        K[t] = k0; Dd[t] = d0
    return K, Dd


def ema(x, n):
    a = 2.0 / (n + 1); out = np.empty(len(x)); out[0] = x[0]
    for t in range(1, len(x)):
        out[t] = a * x[t] + (1 - a) * out[t - 1]
    return out


def rsi(C, n=14):
    out = np.full(len(C), np.nan)
    if len(C) <= n:
        return out
    d = np.diff(C); g = np.maximum(d, 0); l_ = np.maximum(-d, 0)
    ag, al = g[:n].mean(), l_[:n].mean()
    for t in range(n, len(C)):
        if t > n:
            ag = (ag * (n - 1) + g[t - 1]) / n; al = (al * (n - 1) + l_[t - 1]) / n
        out[t] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def signals(O, H, L, C, V):
    """週序列 ⇒ 四個訊號布林（未含暖機、斷點、合併）。"""
    n = len(C); S = {s: np.zeros(n, bool) for s in SIGS}
    if n < 30:
        return S
    K, Dd = kd(C, H, L)
    S["S1"][1:] = (K[:-1] <= Dd[:-1]) & (K[1:] > Dd[1:]) & (K[1:] <= 30)
    dif = ema(C, 12) - ema(C, 26); osc = dif - ema(dif, 9)
    S["S2"][1:] = (osc[:-1] <= 0) & (osc[1:] > 0)
    R = rsi(C)
    S["S3"][1:] = (R[:-1] < 30) & (R[1:] >= 30)
    for t in range(26, n):
        if C[t] / O[t] - 1 >= 0.08 and C[t] > C[t - 26:t].max() and t >= 10 and V[t] >= 2 * V[t - 10:t].mean():
            S["S4"][t] = True
    return S


def weekly_bars(valid, o, h, l, c, v, wk):
    """有效 K 棒 ⇒ 週 K。回 週號陣列、O、H、L、C、V（只含有週 K 的週）。"""
    ix = np.flatnonzero(valid)
    if len(ix) == 0:
        return (np.zeros(0, int),) + tuple(np.zeros(0) for _ in range(5))
    w = wk[ix]; st = np.r_[0, np.flatnonzero(np.diff(w)) + 1]; en = np.r_[st[1:], len(ix)] - 1
    return (w[st], o[ix[st]], np.maximum.reduceat(h[ix], st), np.minimum.reduceat(l[ix], st), c[ix[en]], np.add.reduceat(np.nan_to_num(v[ix]), st))


# ═════════════ 甲：每檔 ═════════════
def _init(cal):
    D.DATA = ST
    wk, wf, wl = weeks_of(cal)
    _G.update(cal=cal, wk=wk, wf=wf, wl=wl)


def load_one(args):
    sid, mk = args
    cal, wk, wf, wl = _G["cal"], _G["wk"], _G["wf"], _G["wl"]; n = len(cal); nw = len(wf)
    st = D.load_stock(sid, mk, cal)
    if st is None:
        return sid, None
    df = st.df
    o, h, l, c = (df[k_].to_numpy(float) for k_ in ("open", "high", "low", "close"))
    vol = pd.to_numeric(df["volume"], errors="coerce").to_numpy(float)
    valid = np.isfinite(c); cff = pd.Series(c).ffill().to_numpy(float)
    raw = pd.read_csv(os.path.join(ST, "stocks", sid + ".csv"), dtype={"date": str}, usecols=["date", "market", "amount"]).drop_duplicates("date")
    raw.index = pd.to_datetime(raw["date"]); raw = raw.reindex(cal)
    twse = (raw["market"].ffill() == "twse").to_numpy(); amt = pd.to_numeric(raw["amount"], errors="coerce").to_numpy(float)
    tb = TR.one(sid, cal); trd, up = np.asarray(tb["trd"], bool), np.asarray(tb["up_o"], bool)
    out = {"valid": valid, "nbars": np.cumsum(valid), "amt": amt}
    B = R11.load_bars(sid, mk, cal)
    wks, WO, WH, WL, WC, WV = weekly_bars(valid, o, h, l, c, vol, wk)
    has = np.zeros(nw, bool); has[wks] = True
    bad_day = np.zeros(n, bool)
    if B is not None:
        idx = B["idx"]; nb = B["next_bad"]; bb = np.flatnonzero(nb[:len(idx)] == np.arange(len(idx)))
        bad_day[idx[bb]] = True
    badw = np.zeros(nw, bool); badw[wk[bad_day]] = True
    near = badw.copy(); near[1:] |= badw[:-1]; near[:-1] |= badw[1:]
    cb = np.r_[0, np.cumsum(bad_day)]                                          # 區間壞根數
    # 訊號（週序列位置）
    S = signals(WO, WH, WL, WC, WV)
    sig = {}
    for s in SIGS:
        pos = np.flatnonzero(S[s] & (np.arange(len(wks)) >= WARM))
        last = -10 ** 9; keep = []
        for p in pos:
            w = int(wks[p])
            if near[w]:
                continue
            if w - last <= DEDUP:
                continue
            keep.append(w); last = w
        sig[s] = np.array(keep, int)
    # 每週：進場可買、R_k、前 4 週報酬、twse
    ent = np.zeros(nw, bool); ent[:-1] = [bool(trd[d] and np.isfinite(o[d]) and o[d] > 0 and not up[d]) for d in wf[1:]]
    complete = wl <= n - 1
    complete[-1] = cal[wl[-1]].weekday() == 4                                   # 資料尾那週不完整（非週五）⇒ 不算完整週
    Rk = {}
    for k in KS:
        r = np.full(nw, np.nan)
        if B is not None:
            w = np.arange(nw - k)
            ok = has[w] & ent[w] & complete[w + k]
            ww = w[ok]
            d0 = wf[ww]; dx = wl[ww + k]
            clean = (cb[dx + 1] - cb[d0]) == 0
            ww, dx = ww[clean], dx[clean]
            r[ww] = cff[dx] / o[wf[ww + 1]] - 1.0
        Rk[k] = r.astype(np.float32)
    ce = cff[wl]
    r4 = np.full(nw, np.nan); r4[4:] = ce[4:] / ce[:-4] - 1.0
    r4[~has] = np.nan
    out.update({"has": has, "twse_w": twse[wl], "R": Rk, "r4": r4.astype(np.float32), "sig": sig, "bars_ok": B is not None,
                "nweeks": len(wks), "near_n": int(near.sum())})
    return sid, out


def cstats(x, mon, z):
    cs = R11.cl_stats(np.asarray(x, float), np.asarray(mon))
    if cs["n"] == 0:
        return {"n": 0}
    return {"n": cs["n"], "D": cs["mean"], "se": cs["se"], "勝率": cs["win"], "曆月": cs["months"], "lo": cs["mean"] - z * cs["se"], "hi": cs["mean"] + z * cs["se"],
            "lo95": cs["lo"], "hi95": cs["hi"]}


def band(lo, hi):
    return "測得出（＋）" if lo - COST > 0 else ("測得出（−）" if hi + COST < 0 else "測不出")


def exit_of(neff):
    return "出口①" if neff < 30 else ("出口②" if neff < 100 else "出口③")


def part_a(a, log, S):
    D.DATA = ST
    cal = D.load_calendar(); n = len(cal)
    wk, wf, wl = weeks_of(cal); nw = len(wf)
    roster = pd.read_csv(os.path.join(ST, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(roster); mk = dict(zip(roster["stock_id"], roster["market"]))
    sids = sorted(set(U["stock_id"]) & {f[:-4] for f in os.listdir(os.path.join(ST, "stocks"))})
    if a.limit:
        sids = sids[::max(1, len(sids) // a.limit)]                    # 煙霧測試用（正式跑不給）
    t0 = time.time()
    with Pool(a.procs, initializer=_init, initargs=(cal,)) as pool:
        P = {s: v for s, v in pool.imap_unordered(load_one, [(s, mk.get(s, "twse")) for s in sids], chunksize=16) if v is not None}
    sids = [s for s in sids if s in P]
    log(f"[甲] 接合日曆 {cal[0].date()}～{cal[-1].date()}（{n} 日、{nw} 週）｜gate3 有檔 {len(sids)}｜{time.time() - t0:.0f}s")
    E, rules = EV.eligibility(cal, P, sids, log)
    S["甲"] = {"母體規則數": len(rules), "檔數": len(sids), "斷點前後週（不產生訊號）合計": int(sum(P[s]["near_n"] for s in sids))}
    Ew = E[:, wl]; del E
    for s in sids:
        for k_ in ("valid", "nbars", "amt"):
            del P[s][k_]
    bi = int(cal.searchsorted(pd.Timestamp("2015-01-05")))
    pre15 = wl < bi
    HAS = np.array([P[s]["has"] for s in sids]); TW = np.array([P[s]["twse_w"] for s in sids]); BOK = np.array([P[s]["bars_ok"] for s in sids])
    POOL = Ew & HAS & (TW | ~pre15[None, :]) & BOK[:, None]
    R4 = np.array([P[s]["r4"] for s in sids])
    month = np.array([str(cal[d])[:7] for d in wl])
    segw = np.array([next((sg for sg, (x, y) in SEGA.items() if x <= m_ <= y), "") for m_ in month])
    X1 = {}; X2 = {}; RK = {}
    for k in KS:
        Rm = np.array([P[s]["R"][k] for s in sids]).astype(float); RK[k] = Rm
        x1 = np.full(Rm.shape, np.nan); x2 = np.full(Rm.shape, np.nan)
        for w in range(nw):
            ok = POOL[:, w] & np.isfinite(Rm[:, w])
            ii = np.flatnonzero(ok)
            if len(ii) < 20:
                continue
            y = Rm[ii, w]; x1[ii, w] = y - (y.sum() - y) / (len(ii) - 1)
            ok2 = ok & np.isfinite(R4[:, w]); j2 = np.flatnonzero(ok2)
            if len(j2) < 20:
                continue
            dcl = AV.deciles(np.where(ok2, R4[:, w], np.nan)); dd = dcl[j2]; y2 = Rm[j2, w]
            sm = np.bincount(dd, weights=y2, minlength=10); ct = np.bincount(dd, minlength=10); co = ct[dd] - 1
            x2[j2, w] = np.where(co > 0, y2 - (sm[dd] - y2) / np.maximum(co, 1), np.nan)
        X1[k] = x1; X2[k] = x2
        log(f"[甲] 基準 k{k}：①股週 {int(np.isfinite(x1).sum()):,}｜② {int(np.isfinite(x2).sum()):,}")
    # 訊號列
    rows = []; cnt = {s: {"原始（暖機、斷點、合併後）": 0} for s in SIGS}
    for i, s in enumerate(sids):
        for sg in SIGS:
            for w in P[s]["sig"][sg]:
                cnt[sg]["原始（暖機、斷點、合併後）"] += 1
                if not segw[w]:
                    continue
                r = {"sid": s, "訊號": sg, "w": int(w), "i": i, "段": segw[w], "月": month[w], "母體": bool(POOL[i, w])}
                for k in KS:
                    r[f"R{k}"] = RK[k][i, w]; r[f"X1_{k}"] = X1[k][i, w]; r[f"X2_{k}"] = X2[k][i, w]
                rows.append(r)
    SG = pd.DataFrame(rows)
    SG.to_csv(os.path.join(OUT, "甲_signals.csv.gz"), index=False, float_format="%.7g")
    S["甲"]["訊號計數"] = cnt
    # 格
    cells = []
    for sg in SIGS:
        for seg in SEGA:
            g = SG[(SG["訊號"] == sg) & (SG["段"] == seg)]
            seg_w0 = int(np.flatnonzero(segw == seg)[0])
            for k in KS:
                gg = g[np.isfinite(g[f"X2_{k}"])]
                blocks = len(set(((gg["w"].to_numpy() - seg_w0) // k).tolist()))
                neff = int(min(len(gg), blocks))
                cells.append({"訊號": sg, "段": seg, "k": k, "段內訊號": int(len(g)), "在母體": int(g["母體"].sum()), "n": int(len(gg)), "n_eff": neff, "出口": exit_of(neff)})
    C = pd.DataFrame(cells)
    kseg = C[C["出口"] != "出口①"].groupby("段").size().to_dict()
    S["甲"]["Bonferroni k（基準② 可判定格）"] = {sg: int(kseg.get(sg, 0)) for sg in SEGA}
    FK = {}
    for ci, r in C.iterrows():
        g = SG[(SG["訊號"] == r["訊號"]) & (SG["段"] == r["段"])]; k = r["k"]
        z = NormalDist().inv_cdf(1 - 0.025 / max(kseg.get(r["段"], 1), 1)); C.at[ci, "z"] = z
        g2 = g[np.isfinite(g[f"X2_{k}"])]
        if len(g2) < 2:
            continue
        c2 = cstats(g2[f"X2_{k}"], g2["月"], z); g1 = g[np.isfinite(g[f"X1_{k}"])]; c1 = cstats(g1[f"X1_{k}"], g1["月"], z)
        for kk, vv in c2.items():
            C.at[ci, f"②{kk}"] = vv
        for kk in ("D", "lo", "hi", "n"):
            C.at[ci, f"①{kk}"] = c1.get(kk, np.nan)
        C.at[ci, "②毛R"] = float(g2[f"R{k}"].mean())
        C.at[ci, "②結果"] = band(c2["lo"], c2["hi"]) if r["出口"] != "出口①" else "出口①（不可判定）"
        C.at[ci, "①結果"] = band(c1["lo"], c1["hi"]) if (r["出口"] != "出口①" and c1.get("n", 0) > 1) else "—"
        # 假訊號（同股隨機週 30 次）
        seg_ws = np.flatnonzero(segw == r["段"])
        pools = {}
        fx = []; fm = []; means = []
        rng = np.random.default_rng([20260928, SIGS.index(r["訊號"]), k, list(SEGA).index(r["段"])])
        for rep in range(a.fakes):
            xs = []; ms = []
            for i in g2["i"].to_numpy():
                if i not in pools:
                    pools[i] = seg_ws[np.isfinite(X2[k][i, seg_ws])]
                pw = pools[i]
                w_ = int(pw[rng.integers(len(pw))])
                xs.append(X2[k][i, w_]); ms.append(month[w_])
            xs = np.array(xs); means.append(float(xs.mean())); fx.append(xs); fm.extend(ms)
        cf = cstats(np.concatenate(fx), np.array(fm), z)
        C.at[ci, "假D"] = cf["D"]; C.at[ci, "假lo"] = cf["lo"]; C.at[ci, "假hi"] = cf["hi"]
        C.at[ci, "假結果"] = band(cf["lo"], cf["hi"]); C.at[ci, "假p"] = float(np.mean(np.array(means) >= c2["D"]))
        FK[(r["訊號"], r["段"], k)] = means
    # 穩
    for (sg, seg), g in C.groupby(["訊號", "段"]):
        g = g.set_index("k")
        for k in KS:
            res = str(g.at[k, "②結果"]) if "②結果" in g.columns else ""
            if not res.startswith("測得出"):
                continue
            j = KS.index(k); nbrs = [KS[x] for x in (j - 1, j + 1) if 0 <= x < len(KS)]
            same = [str(g.at[q, "②結果"]) == res for q in nbrs]
            ci = C[(C["訊號"] == sg) & (C["段"] == seg) & (C["k"] == k)].index[0]
            C.at[ci, "穩"] = "穩" if all(same) else f"方向一致，但只有 {k} 週過門檻" if not any(same) else "部分相鄰過（" + "、".join(f"{q}週" for q, s_ in zip(nbrs, same) if s_) + "）"
    # 可用
    for sg in SIGS:
        for k in KS:
            q = lambda seg, col: C[(C["訊號"] == sg) & (C["段"] == seg) & (C["k"] == k)][col].iloc[0] if col in C.columns else np.nan
            ok = str(q("確認", "②結果")) == "測得出（＋）" and np.isfinite(q("早年", "②D")) and q("早年", "②D") > 0 and str(q("確認", "假結果")) != "測得出（＋）"
            C.loc[(C["訊號"] == sg) & (C["k"] == k), "可用"] = bool(ok)
    C.to_csv(os.path.join(OUT, "甲_cells.csv"), index=False, float_format="%.6g")
    S["甲"]["可用格"] = [f"{r.訊號}_k{r.k}" for r in C[(C["段"] == "確認") & (C["可用"] == True)].itertuples()]
    log(f"[甲] 完成｜可用 {S['甲']['可用格']}｜k {S['甲']['Bonferroni k（基準② 可判定格）']}")
    _G["A"] = {"C": C, "SG": SG, "cal": cal, "wf": wf, "wl": wl, "wk": wk, "mk": mk}
    return C


# ═════════════ 乙：週收盤出場 ═════════════
def wk_info(W, s):
    """該股：有效 K 棒的週號、每週（日曆週）週收（無週 K ⇒ NaN）、各 L 的週 MA。快取在 W。"""
    C_ = W.setdefault("WKI", {})
    if s in C_:
        return C_[s]
    B = YX.bars_of(W, s)
    if B is None:
        C_[s] = None; return None
    idx, o, c, nb, of_, cf_ = B
    wk = W["WK"]; nw = len(W["WF"])
    bw = wk[idx]
    st = np.r_[0, np.flatnonzero(np.diff(bw)) + 1]; en = np.r_[st[1:], len(idx)] - 1
    ws = bw[st]; wc = c[en]
    WC = np.full(nw, np.nan); WC[ws] = wc
    MA = {}
    for L in LS:
        m_ = pd.Series(wc).rolling(L, min_periods=L).mean().to_numpy()
        a_ = np.full(nw, np.nan); a_[ws] = m_; MA[L] = a_
    C_[s] = (bw, WC, MA)
    return C_[s]


def exit_week(W, s, k, L, m, C, rng=None, fake_lo=None):
    """回 (xpos, g, 類別, 週收觸發週序號 or None)。"""
    B = YX.bars_of(W, s); idx, o, c, nb, of_, cf_ = B
    bw, WC, MA = wk_info(W, s)
    n = len(idx); n0 = len(W["cal"]); ke = k + 1; we = int(bw[ke]); nw = len(W["WF"])
    trig = None
    if rng is None:
        for j in range(m, C + 1):
            w = we + j - 1
            if w >= nw:
                break
            if np.isfinite(WC[w]) and np.isfinite(MA[L][w]) and WC[w] < MA[L][w]:
                trig = j; break
    else:
        trig = int(rng.integers(m, C + 1))
    if trig is not None:
        w = we + trig - 1
        xb = int(np.searchsorted(bw, w + 1, side="left"))          # 下一個日曆週起第一根有效 K 棒
        kind = "週收觸發"; use_open = True
    else:
        w = we + C - 1
        xb = int(np.searchsorted(bw, w, side="right")) - 1          # 第 C 週最後一根有效 K 棒
        kind = "觸頂C"; use_open = False
        if xb < ke:
            xb = ke
    nbk = int(nb[ke]) if ke < len(nb) else n + 10
    if xb >= nbk and nbk - 1 >= ke and nbk <= n - 1:
        xb = nbk - 1; kind = "壞根前出"; use_open = False
    if xb >= n or (kind == "觸頂C" and w >= nw):
        if int(idx[n - 1]) == n0 - 1:
            xpos, g, kind = n0, float(c[n - 1] / o[ke] - 1.0), "T1 補"
        else:
            xpos, g, kind = n0, float(c[n - 1] / o[ke] - 1.0), "停止交易（引擎 stop_force）"
    else:
        xpos = int(idx[xb]); g = float((o[xb] if use_open else c[xb]) / o[ke] - 1.0)
    ent = int(idx[ke])
    for pe, pL in W["EVD"].get(s, []):
        if ent <= pL and xpos >= pe:
            xpos = pL; g = float(cf_[pL] / of_[ent] - 1.0); kind = "R8 截"
    return xpos, g, kind, trig


def build_b(W, cell, fake_seed=None, base_kinds=None):
    L, m, C = cell
    sig = W["SIGH"][("營量", 60)]; sig = sig[sig["xpos_H60"] >= 0].copy()
    X = np.zeros(len(sig), np.int64); G = np.zeros(len(sig)); K_ = []; TG = []
    rng = np.random.default_rng(fake_seed) if fake_seed is not None else None
    for i, (s, k) in enumerate(zip(sig["sid"], sig["k"].astype(int))):
        use_rng = rng if (rng is not None and base_kinds is not None and base_kinds[i] == "週收觸發") else None
        x, g, kd_, tg = exit_week(W, s, k, L, m, C, rng=use_rng)
        X[i] = x; G[i] = g; K_.append(kd_); TG.append(tg)
    sig["xpos_W"] = X; sig["g_W"] = G
    return sig, K_, TG


def cname(cell):
    return f"L{cell[0]}_m{cell[1]}_C{cell[2]}"


def run_b(job):
    wk, cell, fseed, N = job
    W = _W[wk]
    if cell == "base":
        sig, rule = W["SIGH"][("營量", 60)], "H60"; kinds = None
    else:
        bk = W["BK"][cell] if fseed is not None else None
        sig, kinds, _ = build_b(W, cell, fseed, bk); rule = "W"
    o, aud = YX._eng(W, "營量", sig, rule, 7000, N=N)
    row, eq, _ = YX._stats(W, o, aud, W["SEGP"], N or 20)
    row.update({"世界": wk, "格": "營量v1" if cell == "base" else cname(cell), "假": fseed, "N": N or 20, "eq_sha": YX.sha(eq)})
    diffs = {}
    if W.get("V1EQ") is not None:
        V1 = W["V1EQ"]
        for sg, (x, y) in W["SEGP"].items():
            diffs[sg] = (eq[x + 1:y + 1] / eq[x:y] - 1.0) - (V1[x + 1:y + 1] / V1[x:y] - 1.0)
    if fseed is not None:
        aud = None
    return row, diffs, aud, kinds


def part_b(a, log, S):
    Wm, We, ctx = YB.worlds(log)
    _W["主"] = Wm; _W["早年"] = We
    for W in (Wm, We):
        wk, wf, wl = weeks_of(W["cal"]); W["WK"], W["WF"], W["WL"] = wk, wf, wl
    CELLS = [(L, m, C) for L in LS for m in MS for C in CS_]
    ref = pd.read_csv("backtest/resultsT1fix/seeds.csv.gz", dtype={"eq_sha": str})
    rf = ref[(ref["key"] == "c13") & (ref["var"] == "t1")].set_index("r")["eq_sha"]
    ref3 = pd.read_csv("backtest/resultsYLexit3/seeds.csv.gz", dtype={"eq_sha": str}, low_memory=False)
    ROWS = []; DIFF = {}; AUD = {}; KIND = {}
    for wk, W in (("主", Wm), ("早年", We)):
        W["V1EQ"] = None
        row, _, aud, _ = run_b((wk, "base", None, None))
        o, _ = YX._eng(W, "營量", W["SIGH"][("營量", 60)], "H60", 7000); W["V1EQ"] = np.asarray(o["equity"], float)
        ROWS.append(row); AUD[(wk, "營量v1")] = aud
        S["閘"][f"{wk}｜營量 v1 ＝ resultsYLexit3 種子 0"] = bool(row["eq_sha"] == ref3[(ref3["世界"] == wk) & (ref3["格"] == "營量v1") & (ref3["r"] == 0)]["eq_sha"].iloc[0])
        if wk == "主":
            S["閘"]["主｜營量 v1 ＝ resultsT1fix c13 t1 種子 0"] = bool(row["eq_sha"] == rf[0])
        # 預先建各格出場（在主行程，fork 帶進子行程）
        W["BK"] = {}
        for cell in CELLS:
            _, kinds, _ = build_b(W, cell); W["BK"][cell] = kinds
        with Pool(a.procs) as pool:
            res = pool.map(run_b, [(wk, c_, None, None) for c_ in CELLS])
        for c_, (row, diffs, aud, kinds) in zip(CELLS, res):
            ROWS.append(row); AUD[(wk, cname(c_))] = aud; KIND[(wk, cname(c_))] = kinds
            for sg, d in diffs.items():
                DIFF[(wk, cname(c_), sg)] = d
        log(f"[乙 {wk}] 12 格完成｜閘 {S['閘']}")
    Z = json.load(open("backtest/resultsYLexit3/summary.json", encoding="utf-8"))["0050"]
    cal, ecal = Wm["cal"], We["cal"]
    months = {sg: np.array([str(d)[:7] for d in cal[x + 1:y + 1]]) for sg, (x, y) in Wm["SEGP"].items()}
    months["早年"] = np.array([str(d)[:7] for d in ecal[We["w0"] + 1:We["w1"] + 1]])
    SEED = pd.DataFrame(ROWS)
    SEGW = (("探索", "主"), ("確認", "主"), ("早年", "早年"))
    TB = []
    for c_ in ["base"] + CELLS:
        nm = "營量v1" if c_ == "base" else cname(c_)
        row = {"格": nm}
        for sg, wk in SEGW:
            g = SEED[(SEED["世界"] == wk) & (SEED["格"] == nm)].iloc[0]
            cc, mm = float(g[f"{sg}_年化"]), float(g[f"{sg}_回落"])
            row.update({f"{sg}_年化": cc, f"{sg}_回落": mm, f"{sg}_比值": cc / abs(mm), f"{sg}_標籤": YX.label(cc, mm, Z[sg]), f"{sg}_持股": float(g[f"{sg}_持股"]),
                        f"{sg}_現金": float(g[f"{sg}_現金"]), f"{sg}_換手每年": float(g[f"{sg}_換手每年"]), f"{sg}_成本每年": float(g[f"{sg}_成本每年"])})
            if c_ != "base":
                m_, se_ = YX.cr0(DIFF[(wk, nm, sg)], months[sg])
                row[f"{sg}_差"] = m_ * 245; row[f"{sg}_差lo"] = (m_ - 1.96 * se_) * 245; row[f"{sg}_差hi"] = (m_ + 1.96 * se_) * 245
        for wk in ("主", "早年"):
            TRd = YX_trades(AUD[(wk, nm)]); W = _W[wk]
            TRd = TRd[(TRd["t_in"] >= W["w0"]) & (TRd["t_in"] <= W["w1"])]
            hd = (np.minimum(TRd["t_out"], len(W["cal"]) - 1) - TRd["t_in"]).to_numpy()
            row[f"{wk}_平均持有交易日"] = float(hd.mean()); row[f"{wk}_超過60天"] = float((hd > 60).mean())
            if c_ != "base":
                kinds = pd.Series(KIND[(wk, nm)]); sig = W["SIGH"][("營量", 60)]; sig = sig[sig["xpos_H60"] >= 0]
                inw = ((sig["entry_pos"] >= W["w0"]) & (sig["entry_pos"] <= W["w1"])).to_numpy()
                kv = kinds[inw].value_counts(normalize=True).to_dict()
                row[f"{wk}_觸頂C比例"] = float(kv.get("觸頂C", 0.0)); row[f"{wk}_出場類別"] = {k_: round(v, 4) for k_, v in kv.items()}
        row["退化"] = bool(c_ != "base" and (row["探索_持股"] < 10 or row["探索_現金"] > 0.30))
        TB.append(row)
    TB = pd.DataFrame(TB)
    cand = TB[(TB["格"] != "營量v1") & ~TB["退化"]].copy()
    cand["_q"] = cand["探索_標籤"].map(ORDER)
    pick = cand.sort_values(["_q", "探索_比值", "探索_年化"], ascending=False).iloc[0]["格"]
    TB["挑中"] = TB["格"] == pick
    pr = TB.set_index("格").loc[pick]
    lab = min(pr["確認_標籤"], pr["早年_標籤"], key=lambda z: ORDER[z])
    better = bool(pr["確認_差lo"] > 0 and pr["早年_差"] > 0)
    S["乙"] = {"挑中": pick, "件標籤（確認、早年較嚴）": lab, "比營量 v1 好（確認 CI 下緣 ＞ 0 且早年同向）": better,
              "確認差": [pr["確認_差"], pr["確認_差lo"], pr["確認_差hi"]], "早年差": [pr["早年_差"], pr["早年_差lo"], pr["早年_差hi"]],
              "退化格": TB[TB["退化"]]["格"].tolist(), "結果句附註": USER_RULE}
    log(f"[乙] 挑中 {pick}｜標籤 {lab}｜比 v1 好 {better}")
    # 假訊號臂（出場週隨機、同次數）
    pc = tuple(int(x[1:]) for x in pick.split("_"))
    FK = []
    for wk in ("主", "早年"):
        with Pool(a.procs) as pool:
            res = pool.map(run_b, [(wk, pc, [20260928, 2, r], None) for r in range(a.xreps)])
        for r, (row, diffs, _, _) in enumerate(res):
            d_ = {"世界": wk, "r": r}
            for sg in _W[wk]["SEGP"]:
                d_[f"{sg}_年化"] = row[f"{sg}_年化"]; d_[f"{sg}_差"] = float(diffs[sg].mean() * 245)
            FK.append(d_)
    FK = pd.DataFrame(FK); FK.to_csv(os.path.join(OUT, "乙_fake.csv"), index=False, float_format="%.6g")
    fk = {}
    for sg, wk in SEGW:
        f_ = FK[FK["世界"] == wk]
        fk[sg] = {"假年化中位": float(f_[f"{sg}_年化"].median()), "p（假 ≥ 挑中）": float((f_[f"{sg}_年化"] >= pr[f"{sg}_年化"]).mean()),
                  "假差中位": float(f_[f"{sg}_差"].median())}
    S["乙"]["假訊號臂（出場週隨機、同次數）"] = fk
    # 新規矩 ③
    sens = {}
    if pr["確認_標籤"] in ("合格", "另列") or pr["早年_標籤"] in ("合格", "另列"):
        for N in (10, 30):
            for wk in ("主", "早年"):
                row, _, _, _ = run_b((wk, pc, None, N))
                for sg, wk2 in SEGW:
                    if wk2 == wk:
                        sens[f"檔數{N}｜{sg}"] = [row[f"{sg}_年化"], row[f"{sg}_回落"], YX.label(row[f"{sg}_年化"], row[f"{sg}_回落"], Z[sg])]
        S["乙"]["新規矩③ 檔數敏感度（描述）"] = sens
    else:
        S["乙"]["新規矩③"] = "挑中格確認、早年都不合格／另列 ⇒ 不觸發"
    TB.to_csv(os.path.join(OUT, "乙_cells.csv"), index=False, float_format="%.6g")
    SEED.to_csv(os.path.join(OUT, "乙_seeds.csv"), index=False, float_format="%.17g")
    _G["B"] = {"TB": TB, "pick": pick, "pc": pc, "AUD": AUD, "Z": Z}
    return TB


def YX_trades(aud):
    op = {}; rows = []
    for a_ in sorted(aud, key=lambda z: (z["t"], z["side"] != "sell")):
        if a_["side"] == "buy":
            op[a_["sid"]] = a_
        else:
            b = op.pop(a_["sid"])
            rows.append({"sid": a_["sid"], "t_in": b["t"], "t_out": a_["t"], "淨": a_["amt"] / b["amt"] - 1 - a_["cost"] / b["amt"]})
    return pd.DataFrame(rows)


# ═════════════ 報告 ═════════════
def P(x, d=1):
    return "—" if x is None or not np.isfinite(x) else f"{x * 100:+.{d}f}%"


def report(S):
    C = _G["A"]["C"]; TB = _G["B"]["TB"]; pick = _G["B"]["pick"]; Z = _G["B"]["Z"]
    NL = chr(10)
    L = ["# PREREG週線 seq1：週線訊號單測（甲）＋ 營量 v1 週收盤出場（乙）" + NL, f"使用者原話（逐字）：「{RAW}」" + NL,
         f"> 登錄 sha {PREREG_SHA}（裁定 seq271 §三）｜N：甲單筆 16 格、乙組合 ＋1｜⚠ 共用閘「-KY創」補丁未套（預設關），照現行 gate3｜本線讀法 A1～A11、B1～B8 見程式開頭" + NL,
         "## 甲 週線訊號單測（基準② 主；Bonferroni＋成本帶 ±0.585%）" + NL,
         "| 訊號 | k 週 | 段 | n（n_eff） | D ② | Bonferroni CI | 結果 | D ① | 假訊號臂 | 假 p | 穩 | 可用 |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in C.to_dict("records"):
        L.append(f"| {SNAME[r['訊號']]} | {r['k']} | {r['段']} | {r['n']}（{r['n_eff']}） | {P(r.get('②D'), 2)} | 〔{P(r.get('②lo'), 2)}, {P(r.get('②hi'), 2)}〕 | {r.get('②結果', '—')} | "
                 f"{P(r.get('①D'), 2)} | {r.get('假結果', '—')} | {'—' if not np.isfinite(r.get('假p', np.nan)) else format(r['假p'], '.2f')} | {r.get('穩', '') if isinstance(r.get('穩'), str) else ''} | {'✅' if r.get('可用') is True else ''} |")
    L.append(NL + f"Bonferroni k：{S['甲']['Bonferroni k（基準② 可判定格）']}｜可用格：{S['甲']['可用格'] or '無'}｜訊號計數：{S['甲']['訊號計數']}" + NL)
    L.append("## 乙 營量 v1 週收盤出場（" + USER_RULE + "）" + NL)
    L.append("| 格 | 探索 | 確認 | 確認標籤 | 早年 | 早年標籤 | 確認 對 v1〔CI〕 | 早年 對 v1〔CI〕 | 平均持有日 | ＞60 天 | 觸頂 C | 換手／成本每年（確認） | 退化 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in TB.to_dict("records"):
        d_ = (lambda sg: "—" if r["格"] == "營量v1" else f"{P(r[sg + '_差'])}〔{P(r[sg + '_差lo'])}, {P(r[sg + '_差hi'])}〕")
        L.append(f"| {r['格']}{' ⭐挑中' if r['挑中'] else ''} | {P(r['探索_年化'])}／{P(r['探索_回落'])} | {P(r['確認_年化'])}／{P(r['確認_回落'])} | {r['確認_標籤']} | "
                 f"{P(r['早年_年化'])}／{P(r['早年_回落'])} | {r['早年_標籤']} | {d_('確認')} | {d_('早年')} | {r['主_平均持有交易日']:.0f} | {r['主_超過60天']:.0%} | "
                 f"{'—' if r['格'] == '營量v1' else format(r['主_觸頂C比例'], '.0%')} | {r['確認_換手每年']:.1f}×／{P(r['確認_成本每年'])} | {'是' if r['退化'] else ''} |")
    L.append(NL + f"挑中 {pick}｜件標籤 {S['乙']['件標籤（確認、早年較嚴）']}｜比營量 v1 好：{S['乙']['比營量 v1 好（確認 CI 下緣 ＞ 0 且早年同向）']}｜假訊號臂 {S['乙']['假訊號臂（出場週隨機、同次數）']}")
    L.append(f"新規矩 ③：{S['乙'].get('新規矩③ 檔數敏感度（描述）', S['乙'].get('新規矩③'))}｜停損、停利類敏感度與本件「不停損、只換出場」衝突 ⇒ 不跑")
    L.append(NL + f"⛔ 就算好也只進前瞻並列、不改營量 v1；{USER_RULE}。0050 確認 {P(Z['確認']['cagr'])}／{P(Z['確認']['mdd'])}、早年 {P(Z['早年']['cagr'])}。" + NL)
    L.append(f"閘：{S['閘']}")
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write(NL.join(L) + NL)


def page(S):
    A = _G["A"]; C = A["C"]; SG = A["SG"]; cal, wf, wl, mk = A["cal"], A["wf"], A["wl"], A["mk"]
    TB = _G["B"]["TB"]; pick = _G["B"]["pick"]; pc = _G["B"]["pc"]; Z = _G["B"]["Z"]
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0] + "\n.pick{background:#fff4cc}td.l,th.l{text-align:left}"
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>週線兩件</title>", f"<style>{CSS}</style></head><body><main>", "<h1>改看週線：訊號單測＋營量週收盤出場</h1>",
         f"<p class='lead'>使用者原話：「{html.escape(RAW)}」<br>登錄 PREREG週線 seq1（sha {PREREG_SHA}）。⚠ 共用閘「-KY創」補丁未套，照現行母體閘。</p>"]
    # 甲 表：確認段、基準②
    H.append("<h2>甲：週線訊號（確認段 2022–26，跟同週、同前 4 週漲幅的股票比）</h2><div class='wrap'><table><tr><th class='l'>訊號</th>" +
             "".join(f"<th>{k} 週</th>" for k in KS) + "</tr>")
    for sg in SIGS:
        cells = []
        for k in KS:
            r = C[(C["訊號"] == sg) & (C["段"] == "確認") & (C["k"] == k)].iloc[0]
            res = str(r.get("②結果", "—")); tag = "✅" if r.get("可用") is True else ("＋" if res == "測得出（＋）" else ("−" if res == "測得出（−）" else ""))
            e_ = C[(C["訊號"] == sg) & (C["段"] == "早年") & (C["k"] == k)].iloc[0]
            cells.append(f"<td>{P(r.get('②D'), 2)} {tag}<br><small>n {r['n']}｜早年 {P(e_.get('②D'), 2)}</small></td>")
        H.append(f"<tr><td class='l'>{SNAME[sg]}</td>{''.join(cells)}</tr>")
    H.append("</table></div><p class='note'>數字 ＝ 每筆比同類股多賺多少（還沒扣成本）；要超過來回成本 0.585% 而且過多重比較門檻才算「測得出」。"
             f"✅ ＝ 可用（確認段測得出、早年同向、假訊號不過）。可用格：{('、'.join(S['甲']['可用格']) or '無')}。</p>")
    # 乙 表
    H.append(f"<h2>乙：營量 v1 改成「跌破週均線才賣」（{USER_RULE}）</h2><div class='wrap'><table><tr><th class='l'>格</th><th>探索</th><th>確認</th><th>標籤</th><th>早年</th><th>標籤</th><th>確認：對 v1〔CI〕</th><th>平均持有</th></tr>")
    for r in TB.to_dict("records"):
        c_ = "pick" if r["挑中"] else ""
        dd = "—" if r["格"] == "營量v1" else f"{P(r['確認_差'])}〔{P(r['確認_差lo'])}, {P(r['確認_差hi'])}〕"
        nm = "營量 v1（第 60 天賣）" if r["格"] == "營量v1" else r["格"].replace("_", " ") + ("（退化）" if r["退化"] else "")
        H.append(f"<tr class='{c_}'><td class='l'>{nm}</td><td>{P(r['探索_年化'])}／{P(r['探索_回落'])}</td><td>{P(r['確認_年化'])}／{P(r['確認_回落'])}</td><td>{r['確認_標籤']}</td>"
                 f"<td>{P(r['早年_年化'])}／{P(r['早年_回落'])}</td><td>{r['早年_標籤']}</td><td>{dd}</td><td>{r['主_平均持有交易日']:.0f} 天</td></tr>")
    H.append(f"</table></div><p class='note'>L ＝ 週均線週數、m ＝ 至少抱幾週才開始看、C ＝ 最多抱幾週。黃底 ＝ 探索段挑中的格。0050 確認 {P(Z['確認']['cagr'])}。⛔ 就算好也不改營量 v1。</p>")
    # 例子：甲（確認段、最接近可用的格，取中位 X 兩筆）
    H.append("<h2>例子</h2>" + CS.legend_html())
    cc = C[(C["段"] == "確認") & np.isfinite(C.get("②lo", pd.Series(np.nan, index=C.index)))].sort_values("②lo", ascending=False).iloc[0]
    sg, k = cc["訊號"], int(cc["k"])
    g = SG[(SG["訊號"] == sg) & (SG["段"] == "確認") & np.isfinite(SG[f"X2_{k}"])].sort_values([f"X2_{k}", "w"])
    D.DATA = ST
    for q in (0.25, 0.75):
        r = g.iloc[int(q * (len(g) - 1))]; s = r["sid"]; w = int(r["w"])
        st = D.load_stock(s, mk.get(s, "twse"), cal).df
        valid = np.isfinite(st["close"].to_numpy(float))
        wks, WO, WH, WL, WC, WV = weekly_bars(valid, *(st[c_].to_numpy(float) for c_ in ("open", "high", "low", "close")), pd.to_numeric(st["volume"], errors="coerce").to_numpy(float), _G["A"]["wk"])
        p = int(np.searchsorted(wks, w)); i0 = max(0, p - 40); px = int(np.searchsorted(wks, w + k, side="right")) - 1; i1 = min(len(wks) - 1, px + 6)
        sl = slice(i0, i1 + 1); e1 = p + 1 if p + 1 < len(wks) else p
        marks = [{"i": e1 - i0, "px": float(WO[e1]), "kind": "entry", "label": f"下週開盤進 {WO[e1]:.2f}"}, {"i": px - i0, "px": float(WC[px]), "kind": "exit", "label": f"{k} 週後出 {WC[px]:.2f}"}]
        svg = CS.kline_svg([str(cal[wl[z]].date()) for z in wks[sl]], WO[sl], WH[sl], WL[sl], WC[sl], WV[sl] / 1000.0, marks=marks, shade=(e1 - i0, px - i0), title=SNAME[sg], show_title=False)
        H.append(f"<details class='card' open><summary><b>甲 {SNAME[sg]}、抱 {k} 週</b>｜{s}｜訊號週 {cal[wl[w]].date()}</summary>"
                 f"<div class='meta'>週 K 線｜這筆 {P(r[f'R{k}'])}、比同類股 {P(r[f'X2_{k}'])}（取{'中位偏下' if q < 0.5 else '中位偏上'}）｜這一格確認段 {len(g)} 筆、平均 {P(cc['②D'], 2)}（{cc['②結果']}）</div>{svg}</details>")
    # 乙：挑中格，主窗確認段、持有 > 60 天與 ≤ 60 天各一
    RR.use_snapshot()
    W = _W["主"]; t0c, t1c = W["SEGP"]["確認"]
    sig, kinds, tgs = build_b(W, pc)
    base = W["SIGH"][("營量", 60)]; base = base[base["xpos_H60"] >= 0]
    df_ = pd.DataFrame({"sid": sig["sid"].to_numpy(), "e": sig["entry_pos"].to_numpy(int), "x": sig["xpos_W"].to_numpy(int), "g": sig["g_W"].to_numpy(float),
                        "x60": base["xpos_H60"].to_numpy(int), "g60": base["g_H60"].to_numpy(float), "類": kinds})
    df_ = df_[(df_["e"] > t0c) & (df_["e"] <= t1c) & (df_["x"] < len(W["cal"]))]
    df_["hold"] = df_["x"] - df_["e"]
    for title, sub in (("乙 抱超過 60 天", df_[df_["hold"] > 60]), ("乙 60 天內就跌破週線賣", df_[(df_["hold"] <= 60) & (df_["類"] == "週收觸發")])):
        if not len(sub):
            H.append(f"<p class='note'>{title}：沒有例子。</p>"); continue
        sub = sub.assign(d=sub["g"] - sub["g60"]).sort_values(["d", "e"]); r = sub.iloc[(len(sub) - 1) // 2]; s = r["sid"]
        cal_ = W["cal"]; df = D.load_stock(s, W["mk"].get(s, "twse"), cal_).df; cf = pd.Series(df["close"].to_numpy(float)).ffill().to_numpy()
        e, x, x60 = int(r["e"]), int(r["x"]), int(r["x60"]); i0 = max(0, e - 30); i1 = min(len(cal_) - 1, max(x, x60) + 10); sl = slice(i0, i1 + 1)
        op = df["open"].to_numpy(float)
        marks = [{"i": e - i0, "px": float(op[e]), "kind": "entry", "label": f"進 {op[e]:.2f}"},
                 {"i": x - i0, "px": float(op[x] if r["類"] == "週收觸發" else cf[x]), "kind": "exit", "label": f"週線出 {(op[x] if r['類'] == '週收觸發' else cf[x]):.2f}"},
                 {"i": x60 - i0, "px": float(cf[x60]), "kind": "exit", "label": f"第 60 天 {cf[x60]:.2f}", "color": "#888888", "row": 1}]
        ma = {kk: CS.moving_avg(cf, kk)[sl] for kk in (5, 20, 60)}
        svg = CS.kline_svg([str(z.date()) for z in cal_[sl]], op[sl], df["high"].to_numpy(float)[sl], df["low"].to_numpy(float)[sl], df["close"].to_numpy(float)[sl],
                           df["volume"].to_numpy(float)[sl] / 1000.0, ma=ma, marks=marks, shade=(e - i0, x - i0), title=title, show_title=False)
        H.append(f"<details class='card' open><summary><b>{title}（{pick.replace('_', ' ')}）</b>｜{s}｜進場 {cal_[e].date()}</summary>"
                 f"<div class='meta'>這一類在確認段 {len(sub)} 筆；取「週線出 − 第 60 天賣」中位那筆｜週線出場 {P(r['g'] - COST)}（抱 {int(r['hold'])} 個交易日）；第 60 天賣 {P(r['g60'] - COST)}</div>{svg}</details>")
    H.append(f"<p class='note'>{USER_RULE}；結果好也只進前瞻並列。價格為還原價。</p></main></body></html>")
    open(os.path.join(OUT, F_HTML), "w", encoding="utf-8").write("\n".join(H))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); ap.add_argument("--fakes", type=int, default=30)
    ap.add_argument("--xreps", type=int, default=100); ap.add_argument("--limit", type=int, default=0); ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    log(f"===== researchWeekly {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜PREREG週線 seq1 sha {PREREG_SHA} =====")
    S = {"登錄": f"PREREG週線 seq1 sha {PREREG_SHA}（裁定 seq271 §三）", "使用者原話": RAW, "閘": {}, "共用閘": "「-KY創」補丁未套（預設關），照現行 gate3"}
    reg = [os.path.join("/mnt/c/SynologyDrive/跨線信箱", f) for f in os.listdir("/mnt/c/SynologyDrive/跨線信箱") if f.startswith("登錄全文-週線兩件")]
    if reg:
        txt = open(reg[0], "rb").read().decode("utf-8").splitlines(keepends=True)
        S["閘"]["登錄全文 sha（去 pw1 行）"] = hashlib.sha256("".join(x for x in txt if "pw1" not in x).encode("utf-8")).hexdigest()[:16] == PREREG_SHA
    part_a(a, log, S)
    if a.smoke:
        log("[煙霧] 甲完成、停"); return
    RR.use_snapshot()
    part_b(a, log, S)
    report(S); page(S)
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=lambda z: z.item() if hasattr(z, "item") else str(z))
    log(f"[完] 網頁 {os.path.getsize(os.path.join(OUT, F_HTML))} bytes｜{time.time() - T0:.0f}s")


if __name__ == "__main__":
    main()
