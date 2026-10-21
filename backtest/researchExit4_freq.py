# -*- coding: utf-8 -*-
"""出場第四輪 seq1【頻率表・乾跑】（台股策略線 登錄 sha e86e45b37aaa66e2，2026-10-21 10:05；裁定 seq417 發號 N_前段 ＋3、最多暫定；
「先交頻率表，裁定線過目後開跑」）——回測線計算子代理。
⛔ 只數事件、n_eff、各出法觸發與觸發天數、評估點能否走完、構造與先後關係；⛔ 不算任何出法的 R、勝率、賣後走勢，⛔ 不存任何報酬或價格。
   r(t) 只用來決定事件日 T 與觸發日（登錄 §三、§四的條件本身），只存日期位置與布林。
⛔ 不 commit、不改既有程式與結果夾；researchExitGen（seq6：setup 母體、rev_turns、avail_map）、researchQuad（stock_data）、avgdown ⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchExit4_freq [--procs 3]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchExit4_freq_check
輸出 backtest/resultsExit4/freq/：freq.json、freq.csv（世界×段×狀態×終點×出法）、cells.csv（3 格能否判）、years.csv（分年）、market.csv（上市／上櫃）、
     equiv.csv（等價自查）、events.csv.gz（逐事件：T、各出法判斷日／賣出日位置，⛔ 無價格）、run.log

═══ 讀法（F 標；登錄沒寫清楚、執行者補的都在這裡；⛔ 在看任何本件數字之前寫死；★＝執行者定，〔 〕內為另一讀法）═══
 F1 母體（登錄 §二 ＝ seq6 §二 寫死）：researchExitGen.setup 原樣——主：resultsp4 面板＋panel_ext 的 W1 eligible ∩ gate3、資料 edc6f8002f 快照（日曆尾 2026-09-24）；
    早年：reduce_v2 版面＋sig_main 面板 liq_ok∧bars_ok（只上市；seq6 R1 同）。量測日 ＝ 每月第一個交易日、e ＝ 量測日＋1、進場價 P0 ＝ 還原開盤 o[e]；
    ★ e 範圍沿用 seq6 setup：主 e ≥ 2017-03-02、早年 e ≥ 2005-01-03（⇒ 所有 T ≥ e 都落在段內；探索段開頭幾個月事件較少，照報）。
    e 開盤漲停／停牌（ok_buy 假）⇒ 不建（seq6 同）。
 F2 seq412 exright（新件 open_base）：★ 上市 exright 表（~/b2fwork/exrtab_b5532121f8d8.pkl，researchIndMom.load_exr_table 的快取，universe＋early）
    有 open_base 的日子、且該日有成交 ⇒ 開盤漲停／跌停改用 limit_price(open_base, 7%／10%) 判（tradability.one 同式 |原始開盤 − 漲跌停價| ＜ 1e−6，
    只把參考價換成 open_base；舊口徑在除權息日一律不判）⇒ 重算 ok_buy、ok_sell。上櫃 otcexright 的 open_base 全空 ⇒ 上櫃維持舊口徑。
    壞 K：seq6 框架的硬斷點 ＝ D.breakpoints 價格規則（還原收盤跳 ≤0.55／≥1.8 且區間無還原事件）∪ 缺口 ≥5 日（seq335），⭐ 不用參考價
    ⇒ 沒有可換成 open_base 的地方；另描述：原始收盤 ÷ open_base 不在 [0.895, 1.105] 的「open_base 幽靈日」落在事件窗內的筆數（⛔ 不剔除，只報）。
 F3 硬斷點（seq335）：kb ＝ ≥ e 的第一個壞根（價格斷點 ≥ e，或缺口第 5 日 ≥ e＋4；avgdown.brk_vec 同式）；kb ＝ e ⇒ 該筆不建（seq6「硬斷點」）。
    狀態掃描窗 ＝ [e, min(e＋249, kb−1)]（登錄「進場後 250 個交易日內」，e 算第 1 日）。
 F4 狀態（登錄 §三；r(t) ＝ 還原收盤 ÷ P0 − 1，只在有效 K 棒上）：S+ ＝ 第一個 r ≥ +15% 的 T；S− ＝ 第一個 r ≤ −15% 的 T；
    S0_N ＝ T ＝ e＋N−1（日曆位置），且 [e, T] 每根有效 K 棒 −15% ＜ r ＜ +15%；N ＝ 40 判、30／60 並報。
    ★ S0 另要求 T ≤ 該股最後一根有效 K 棒（已下市不算盤整）。同一筆可依序產生多個狀態，各自一件（重疊照報）。
 F5 評估點（登錄 §四）：E_h ＝ T＋h（h ＝ 120 判、60／250 並報）。登錄「只收 E 落在資料內」⇒ T＋h ＞ 日曆尾 ⇒ 該 h 不收。
    ★ (T, T＋h] 有壞根（kb ≤ T＋h）⇒ E_h ＝ kb−1（壞根前一根強制結算，出場第三輪 Q8 同）、標「壞根截斷」〔另一讀法：整件剔除〕；
    ★ 下市（最後有效 K 棒 ＜ E_h、無壞根）⇒ seq6 同：以 E_h 以前最後一根收盤結算（照報筆數）。
    「評估點能走完」＝ E 在資料內 ∧ 沒有壞根截斷。
 F6 出法觸發（登錄 §四）：★ 判斷日 k ∈ [T, E−1]、只在有效 K 棒上判（「T 收盤判」⇒ T 當天收盤也判；出場第三輪是 [T＋1, E−1]）；
    ★ 賣出日 s ＝ k＋1 起第一個可賣開盤（有成交、開盤非跌停、還原開盤有效；F2 exright 版），s ≤ E 才算賣；否則 ＝ 不賣（E 收盤結算）。
    K0 不賣｜K1 k ＝ T｜S+ K2 ＝ 一半 K1（觸發 ＝ K1）｜S+ K3 c[k] ≤ 0.9 × max(c[T..k])｜K4 同 0.8｜K5 c[k] ＜ MA20[k]
    ★ MA20 ＝ 出場第三輪修正後寫法（日曆 ffill 收盤、最近 20 個有值平均、min_periods＝1、上市前缺值不計），平均改用 math.fsum（恰好相等不翻判）。
    S0 K2 c[k] ＜ 下緣（[e, T] 有效收盤最低）｜S0 K3 先突破（c[k] ＞ 上緣 ＝ [e, T] 最高）前 c[k] ＜ 下緣 ⇒ 賣；突破後 c[k] ＜ 上緣 ⇒ 賣（出場第三輪 Q9 同）。
    S− K2 c[k]/P0 − 1 ≥ −5% 或 c[k] ≥ MA20[k]（先到者；★ 同日兩條都成立 ⇒ 記「同日」）｜S− K3 c[k]/P0 − 1 ≤ −25%
    S− K4 ＝ seq6 X7 同式（researchExitGen.rev_turns、avail_map：可用日 ＝ 期別次月 10 日（≤2025-12）／15 日（≥2026-01）之後第一個交易日，seq304）：
       轉負可用日 A ∈ [T, E−1] 的第一個 ⇒ k ＝ A（★ A 不必是有效 K 棒）；沒有月營收 ⇒ 不觸發（比例照報）。
    同根兩出場價取較低（seq373）：每法每筆只有一個賣價（收盤判、隔日開盤賣）⇒ 不適用，照寫。
 F7 段（登錄 §六，依 T）：探索 2017-03-02～2021-12-30｜確認 2022-01-03～日曆尾｜早年 2005-01-03～2014-12-31（描述；reduce_v2 約 0.3% 註）。
    n_eff ＝ min(收件事件數, 有事件的 T 曆月數)；★ 能判 ＝ h＝120、S0 用 S0_40 時，探索、確認兩段 n_eff 都 ≥ 30（全專案出口①）。
 F8 觸發統計（⛔ 只計觸發、不算 R）：觸發率 ＝ 賣出（s ≤ E）÷ 該格收件事件；觸發天數 ＝ s − T（交易日）只計觸發者；另報 k ＝ T 就觸發的比例（≈ K1）。
 F9 等價自查（登錄 §七、seq377）：K2 ＝ ½K1＋½K0 構造上不可能唯一第一；S+ K4 觸發 ⇒ K3 已觸發（同日或更早）的比例（應 100%）與同日比例；
    S+ K5 與 K3 同日比例；S0 先突破比例（判斷窗 [T, E−1] 內第一次 c ＞ 上緣早於第一次 c ＜ 下緣）、K3 與 K2 賣出日不同的比例，＜10% ⇒「K3 近乎等於 K2」；
    S− K2 先後；S− K4 無月營收比例；全部出法兩兩「賣出日（含不賣）完全相同」比例，≥ 90% ⇒ 標近乎等價；觸發率 ＜ 10% ⇒ 標「近乎等於 K0」、
    k＝T 觸發 ≥ 90% ⇒ 標「近乎等於 K1」。
"""
from __future__ import annotations

import argparse
import glob
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

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchExitGen as G6                                # noqa: E402  seq6：setup、rev_turns、avail_map（⛔ 只 import）
Q, D = G6.Q, G6.D                                           # researchQuad（stock_data、_init）、data
from backtest import avgdown as AV                          # noqa: E402
from backtest import research11 as R11                      # noqa: E402  limit_price、regime_below
from backtest import tradability as TRD                     # noqa: E402  CUT

REG_SHA = "e86e45b37aaa66e2"
MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
OUT = os.environ.get("X4F_OUT", os.path.expanduser("~/tw-p17/backtest/resultsExit4/freq"))
EXR_PKL = os.path.expanduser("~/b2fwork/exrtab_b5532121f8d8.pkl")
THR, THR5, THR25 = 0.15, -0.05, -0.25
WIN = 250
S0N = (30, 40, 60)
HS = (60, 120, 250)
HJ = 120
NEFF_MIN = 30
SEGS = {"main": {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", None)}, "early": {"早年": ("2005-01-03", "2014-12-31")}}
WNAME = {"main": "主", "early": "早年"}
EXITS = {"S+": ["K0", "K1", "K2", "K3", "K4", "K5"], "S0": ["K0", "K1", "K2", "K3"], "S−": ["K0", "K1", "K2", "K3", "K4"]}
ENAME = {("S+", "K0"): "不賣", ("S+", "K1"): "立刻賣", ("S+", "K2"): "賣一半（＝½K1＋½K0）", ("S+", "K3"): "回落10%才賣", ("S+", "K4"): "回落20%才賣",
         ("S+", "K5"): "跌破20日線", ("S0", "K0"): "不賣", ("S0", "K1"): "立刻賣", ("S0", "K2"): "跌破整理區下緣", ("S0", "K3"): "Darvas（突破後跌回上緣）",
         ("S−", "K0"): "不賣", ("S−", "K1"): "立刻賣", ("S−", "K2"): "反彈−5%或站回20日線", ("S−", "K3"): "再跌到−25%", ("S−", "K4"): "營收年增轉負"}
STATES = ["S+", "S0_30", "S0_40", "S0_60", "S−"]
BIG = 10 ** 9
_W: dict = {}
LOG: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def grp(st):
    return "S0" if st.startswith("S0") else st


def reg_check():
    fs = [f for f in glob.glob(os.path.join(MAILBOX, "*.md")) if f"sha{REG_SHA}" in os.path.basename(f) and os.path.basename(f).startswith("登錄全文")]
    if not fs:
        raise SystemExit(f"⛔ 信箱找不到登錄全文 sha{REG_SHA}")
    for f in fs:
        b = open(f, "rb").read()
        h = hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]
        if h != REG_SHA:
            raise SystemExit(f"⛔ 登錄 sha {h} ≠ {REG_SHA}（{f}）")
    return os.path.basename(fs[0])


# ═════════════════════════════ 單檔：exright 修正（F2）
def exr_patch(sid, S, cal, tab):
    """回 (up_o, dn_o, ghost 布林, 計數)。只在上市 exright 有 open_base、該日有成交的根改判。"""
    up = np.array(S["up_o"], bool, copy=True); dn = np.array(S["dn_o"], bool, copy=True)
    n = len(cal); ghost = np.zeros(n, bool); cnt = {"exr列": 0, "up變": 0, "dn變": 0, "幽靈日": 0}
    rows = tab.get(sid)
    if not rows:
        return up, dn, ghost, cnt
    fp = os.path.join(D.DATA, "stocks", f"{sid}.csv")
    raw = pd.read_csv(fp, dtype={"date": str}, usecols=["date", "open", "close"])
    raw["date"] = pd.to_datetime(raw["date"]); raw = raw.drop_duplicates("date").set_index("date")
    ro = np.array(pd.to_numeric(raw["open"].reindex(cal), errors="coerce"), dtype=float)
    rc = np.array(pd.to_numeric(raw["close"].reindex(cal), errors="coerce"), dtype=float)
    ro[~(ro > 0)] = np.nan; rc[~(rc > 0)] = np.nan
    for d, ob in rows:
        p = int(cal.searchsorted(d))
        if p >= n or cal[p] != d or not np.isfinite(rc[p]):
            continue
        cnt["exr列"] += 1
        lim = 0.07 if cal[p] < TRD.CUT else 0.10
        if np.isfinite(ro[p]):
            u = abs(ro[p] - R11.limit_price(ob, True, lim)) < 1e-6
            w = abs(ro[p] - R11.limit_price(ob, False, lim)) < 1e-6
        else:
            u = w = False
        cnt["up變"] += int(u != up[p]); cnt["dn變"] += int(w != dn[p])
        up[p] = u; dn[p] = w
        if not (0.895 <= rc[p] / ob <= 1.105):
            ghost[p] = True; cnt["幽靈日"] += 1
    return up, dn, ghost, cnt


def ma20_exact(cf):
    """F6 MA20：日曆 ffill 收盤、最近 20 個有值（上市前缺值不計，min_periods＝1）的平均 ＝ math.fsum(窗)／個數。
    ⚠ 不用 pandas rolling：累加誤差約 1e−13 ⇒ 收盤恰好等於均線（連續平盤）時會翻判（對帳 C1 抓到 8 筆；researchQuad.ma_exact 同理由）。"""
    n = len(cf); out = np.full(n, np.nan)
    for i in range(n):
        w = cf[max(0, i - 19):i + 1]; w = w[np.isfinite(w)]
        if len(w):
            out[i] = math.fsum(w) / len(w)
    return out


def first_true(mask, a, b):
    """[a, b] 內第一個 True 的位置；沒有 ⇒ −1。"""
    if b < a:
        return -1
    w = np.flatnonzero(mask[a:b + 1])
    return int(a + w[0]) if len(w) else -1


def work(args):
    sid, market, es = args
    cal = Q._G["cal"]; n = len(cal); last = n - 1
    S = Q.stock_data(sid, market)
    base = {"sid": sid, "market": market}
    if S is None:
        return [], [{**base, "e": int(e), "status": "無資料"} for e in es], {}
    up_o, dn_o, ghost, xc = exr_patch(sid, S, cal, _W["tab"])
    o, c, valid = S["o"], S["c"], S["valid"]
    ok_buy = AV.trade_ok(S["trd"], up_o, o); ok_sell = AV.trade_ok(S["trd"], dn_o, o)
    nxt_sell = AV.next_true(ok_sell)
    xc["ok_buy變"] = int((ok_buy != S["ok_buy"]).sum()); xc["ok_sell變"] = int((ok_sell != S["ok_sell"]).sum())
    pbpos = np.flatnonzero(np.diff(np.r_[0, S["cs_pb"]]) > 0)
    g5pos = np.flatnonzero(np.diff(np.r_[0, S["cs_g5"]]) > 0)
    lastbar = int(S["bars"][-1])
    cf = pd.Series(c).ffill().to_numpy()
    ma20 = ma20_exact(cf)
    turns, nrev = G6.rev_turns(sid, _W["rev"], _W["rly"], _W["A"])
    cs_gh = np.cumsum(ghost)
    vc = np.where(valid, c, np.nan)
    ev = []; st = []

    def sell_at(k):
        if k < 0 or k + 1 > last:
            return -1
        return int(nxt_sell[k + 1])

    for e in es:
        e = int(e)
        r0 = {**base, "e": e}
        if e > last:
            st.append({**r0, "status": "超出日曆"}); continue
        if not ok_buy[e]:
            st.append({**r0, "status": "進場日漲停或停牌"}); continue
        a1 = pbpos[pbpos >= e]; a2 = g5pos[g5pos >= e + 4]
        kb = min(int(a1[0]) if len(a1) else BIG, int(a2[0]) if len(a2) else BIG)
        if kb == e:
            st.append({**r0, "status": "硬斷點"}); continue
        P0 = float(o[e])
        hi = min(e + WIN - 1, kb - 1, last)
        rr = vc[e:hi + 1] / P0 - 1.0
        with np.errstate(invalid="ignore"):
            iu = np.flatnonzero(rr >= THR); idn = np.flatnonzero(rr <= -THR)
        fu = int(iu[0]) if len(iu) else BIG; fd = int(idn[0]) if len(idn) else BIG
        st.append({**r0, "status": "保留", "壞根截斷狀態窗": int(kb - 1 < e + WIN - 1 and kb - 1 < last)})
        evs = []
        if fu < BIG:
            evs.append(("S+", e + fu))
        if fd < BIG:
            evs.append(("S−", e + fd))
        fo = min(fu, fd)
        for N in S0N:
            Tn = e + N - 1
            if Tn <= hi and fo > N - 1 and Tn <= lastbar:
                evs.append((f"S0_{N}", Tn))
        for stt, T in evs:
            W_ = min(T + WIN, kb - 1, last)              # 最長判斷窗的 E（h＝250）；判斷日 k ≤ W_−1
            kmax = W_ - 1
            row = {"sid": sid, "market": market, "e": e, "狀態": stt, "T": T, "kb": kb if kb < BIG else -1, "lastbar": lastbar, "nrev": nrev,
                   "幽靈日_e到T+250": int(cs_gh[min(T + WIN, last)] - (cs_gh[e - 1] if e > 0 else 0))}
            row["K1_d"] = T; row["K1_s"] = sell_at(T)
            g = grp(stt)
            if g == "S+":
                seg = vc[T:kmax + 1] if kmax >= T else np.zeros(0)
                if len(seg):
                    rm = np.fmax.accumulate(np.where(np.isfinite(seg), seg, -np.inf))
                    with np.errstate(invalid="ignore"):
                        h3 = np.isfinite(seg) & (seg <= 0.9 * rm); h4 = np.isfinite(seg) & (seg <= 0.8 * rm)
                        h5 = np.isfinite(seg) & (seg < ma20[T:kmax + 1])
                    for code, h_ in (("K3", h3), ("K4", h4), ("K5", h5)):
                        w = np.flatnonzero(h_); d = int(T + w[0]) if len(w) else -1
                        row[f"{code}_d"] = d; row[f"{code}_s"] = sell_at(d)
                else:
                    for code in ("K3", "K4", "K5"):
                        row[f"{code}_d"] = -1; row[f"{code}_s"] = -1
                row["K2_d"] = row["K1_d"]; row["K2_s"] = row["K1_s"]
            elif g == "S0":
                lo_, up_ = np.nanmin(vc[e:T + 1]), np.nanmax(vc[e:T + 1])
                seg = vc[T:kmax + 1] if kmax >= T else np.zeros(0)
                with np.errstate(invalid="ignore"):
                    bl = np.flatnonzero(np.isfinite(seg) & (seg < lo_)); bu = np.flatnonzero(np.isfinite(seg) & (seg > up_))
                dl = int(T + bl[0]) if len(bl) else -1; du = int(T + bu[0]) if len(bu) else -1
                row["K2_d"] = dl; row["K2_s"] = sell_at(dl)
                row["上緣突破_d"] = du; row["下緣跌破_d"] = dl
                if du >= 0 and (dl < 0 or du < dl):
                    with np.errstate(invalid="ignore"):
                        ba = np.flatnonzero(np.isfinite(seg) & (seg < up_) & (np.arange(len(seg)) > du - T))
                    d3 = int(T + ba[0]) if len(ba) else -1
                else:
                    d3 = dl
                row["K3_d"] = d3; row["K3_s"] = sell_at(d3)
            else:  # S−
                seg = vc[T:kmax + 1] if kmax >= T else np.zeros(0)
                with np.errstate(invalid="ignore"):
                    i5 = np.flatnonzero(np.isfinite(seg) & (seg / P0 - 1.0 >= THR5))
                    im = np.flatnonzero(np.isfinite(seg) & (seg >= ma20[T:kmax + 1]))
                    i25 = np.flatnonzero(np.isfinite(seg) & (seg / P0 - 1.0 <= THR25))
                f5 = int(T + i5[0]) if len(i5) else -1; fm = int(T + im[0]) if len(im) else -1
                d2 = min([x for x in (f5, fm) if x >= 0], default=-1)
                row["K2_d"] = d2; row["K2_s"] = sell_at(d2); row["K2_r5_d"] = f5; row["K2_ma_d"] = fm
                d3 = int(T + i25[0]) if len(i25) else -1
                row["K3_d"] = d3; row["K3_s"] = sell_at(d3)
                w = turns[(turns >= T) & (turns <= kmax)]
                d4 = int(w.min()) if len(w) else -1
                row["K4_d"] = d4; row["K4_s"] = sell_at(d4)
            evs_row = row
            ev.append(evs_row)
    return ev, st, xc


def _init(cal, off, b60, b200, tab, rev, rly, A):
    Q._init(cal, off, b60, b200)
    _W.update(tab=tab, rev=rev, rly=rly, A=A)


def run_world(world, procs, tab, limit=None):
    Wd = G6.setup(world, log)
    cal = Wd["cal"]; p = Wd["p"]
    if limit:
        p = p[p["stock_id"].isin(sorted(p["stock_id"].unique())[:limit])]
    off = Q.RA.TR.load_official()
    b60 = R11.regime_below(Wd["c50ff"], 60)
    tasks = [(sid, Wd["mk"].get(sid, "twse"), sorted(g["e"].astype(int))) for sid, g in p.groupby("stock_id")]
    EV = []; ST = []; XC = {}
    with Pool(procs, initializer=_init, initargs=(cal, off, b60, Wd["below200"], tab, Wd["rev"], Wd["rly"], Wd["A"])) as pool:
        for ev, st, xc in pool.imap_unordered(work, tasks, chunksize=8):
            EV += ev; ST += st
            for k, v in xc.items():
                XC[k] = XC.get(k, 0) + v
    E = pd.DataFrame(EV).sort_values(["sid", "e", "狀態"]).reset_index(drop=True)
    STt = pd.DataFrame(ST)
    return Wd, E, STt, XC


# ═════════════════════════════ 彙總
def seg_bounds(cal, world):
    out = {}
    for sg, (a, b) in SEGS[world].items():
        x = int(cal.searchsorted(pd.Timestamp(a)))
        y = len(cal) - 1 if b is None else int(cal.searchsorted(pd.Timestamp(b), side="right")) - 1
        out[sg] = (x, y)
    return out


def add_h(E, cal):
    last = len(cal) - 1
    E["T日"] = [str(cal[t].date()) for t in E["T"]]
    E["T月"] = E["T日"].str[:7]; E["T年"] = E["T日"].str[:4].astype(int)
    kb = np.where(E["kb"].to_numpy() < 0, BIG, E["kb"].to_numpy())
    for h in HS:
        Tn = E["T"].to_numpy() + h
        E[f"E在資料內_{h}"] = Tn <= last
        E[f"壞根截斷_{h}"] = (kb <= Tn) & (Tn <= last)
        E[f"E_{h}"] = np.where(kb <= Tn, kb - 1, Tn)
        E[f"下市末根<E_{h}"] = (E["lastbar"].to_numpy() < E[f"E_{h}"].to_numpy()) & ~E[f"壞根截斷_{h}"] & (Tn <= last)
    return E


def sold(E, code, h):
    d = E[f"{code}_d"].to_numpy(); s = E[f"{code}_s"].to_numpy(); Eh = E[f"E_{h}"].to_numpy()
    return (d >= 0) & (d <= Eh - 1) & (s >= 0) & (s <= Eh)


def freq_rows(E, world, cal):
    rows = []
    for sg, (x, y) in seg_bounds(cal, world).items():
        for stt in STATES:
            A0 = E[(E["狀態"] == stt) & (E["T"] >= x) & (E["T"] <= y)]
            for h in HS:
                sub = A0[A0[f"E在資料內_{h}"]]
                n = len(sub); mo = sub["T月"].nunique()
                base = {"世界": WNAME[world], "段": sg, "狀態": stt, "終點": f"T+{h}", "全部事件(T在段內)": len(A0), "收件(E在資料內)": n,
                        "有事件曆月": int(mo), "n_eff": int(min(n, mo)), "壞根截斷": int(sub[f"壞根截斷_{h}"].sum()),
                        "下市末根<E": int(sub[f"下市末根<E_{h}"].sum()),
                        "評估點能走完比例(÷全部)": round(float((sub[f"E在資料內_{h}"] & ~sub[f"壞根截斷_{h}"]).sum() / len(A0)), 4) if len(A0) else None,
                        "相異進場筆": int(sub[["sid", "e"]].drop_duplicates().shape[0]) if n else 0}
                for code in EXITS[grp(stt)]:
                    r = dict(base); r["出法"] = code; r["出法名"] = ENAME[(grp(stt), code)]
                    if code == "K0" or n == 0:
                        r.update({"觸發": 0, "觸發率": 0.0 if n else None, "觸發天數中位(s−T)": None, "觸發天數平均": None, "k=T觸發比例(÷事件)": 0.0 if n else None})
                    else:
                        m = sold(sub, code, h)
                        dd = (sub[f"{code}_s"].to_numpy() - sub["T"].to_numpy())[m]
                        kT = m & (sub[f"{code}_d"].to_numpy() == sub["T"].to_numpy())
                        r.update({"觸發": int(m.sum()), "觸發率": round(float(m.mean()), 4), "觸發天數中位(s−T)": float(np.median(dd)) if len(dd) else None,
                                  "觸發天數平均": round(float(dd.mean()), 2) if len(dd) else None, "k=T觸發比例(÷事件)": round(float(kT.mean()), 4),
                                  "判斷成立但E前賣不到": int(((sub[f"{code}_d"].to_numpy() >= 0) & (sub[f"{code}_d"].to_numpy() <= sub[f"E_{h}"].to_numpy() - 1) & ~m).sum())})
                    rows.append(r)
    return rows


def equiv_rows(E, world, cal):
    rows = []
    for sg, (x, y) in seg_bounds(cal, world).items():
        for stt in STATES:
            for h in HS:
                sub = E[(E["狀態"] == stt) & (E["T"] >= x) & (E["T"] <= y) & E[f"E在資料內_{h}"]]
                n = len(sub)
                if n == 0:
                    continue
                g = grp(stt)
                base = {"世界": WNAME[world], "段": sg, "狀態": stt, "終點": f"T+{h}", "事件": n}
                Eh = sub[f"E_{h}"].to_numpy()
                sd = {}
                for code in EXITS[g]:
                    if code == "K0":
                        sd[code] = np.full(n, -1)
                    else:
                        sd[code] = np.where(sold(sub, code, h), sub[f"{code}_s"].to_numpy(), -1)
                # 兩兩賣出日完全相同
                cs = EXITS[g]
                for i, a in enumerate(cs):
                    for b in cs[i + 1:]:
                        same = float((sd[a] == sd[b]).mean())
                        rows.append({**base, "項": f"{a}≡{b} 賣出日（含不賣）完全相同比例", "值": round(same, 4),
                                     "標記": ("⚠ 近乎等價（≥90%）" if same >= 0.9 else "") + ("（構造：K2 觸發＝K1，R＝½K1＋½K0）" if g == "S+" and {a, b} == {"K1", "K2"} else "")})
                for code in cs:
                    if code in ("K0", "K1") or (g == "S+" and code == "K2"):
                        continue
                    tr = float((sd[code] >= 0).mean())
                    kT = float(((sd[code] >= 0) & (sub[f"{code}_d"].to_numpy() == sub["T"].to_numpy())).mean())
                    rows.append({**base, "項": f"{code} 觸發率（退化檢查）", "值": round(tr, 4), "標記": "⚠ 近乎等於 K0（觸發 ＜10%）" if tr < 0.10 else ""})
                    rows.append({**base, "項": f"{code} k＝T 就觸發比例（退化檢查）", "值": round(kT, 4), "標記": "⚠ 近乎等於 K1（≥90%）" if kT >= 0.9 else ""})
                if g == "S+":
                    t3, t4, t5 = sd["K3"] >= 0, sd["K4"] >= 0, sd["K5"] >= 0
                    d3, d4 = sub["K3_d"].to_numpy(), sub["K4_d"].to_numpy()
                    rows.append({**base, "項": "K4 觸發 ⇒ K3 判斷日 ≤ K4 判斷日 的比例（應 100%）", "值": round(float(((d3 >= 0) & (d3 <= d4))[t4].mean()), 4) if t4.any() else None, "標記": ""})
                    rows.append({**base, "項": "K4 觸發者中 K3 同日比例", "值": round(float((sd["K3"] == sd["K4"])[t4].mean()), 4) if t4.any() else None, "標記": ""})
                    rows.append({**base, "項": "P(K4 觸發 | K3 觸發)", "值": round(float(t4[t3].mean()), 4) if t3.any() else None, "標記": ""})
                    both = t3 & t5
                    rows.append({**base, "項": "K3、K5 都觸發者中同日比例", "值": round(float((sd["K3"] == sd["K5"])[both].mean()), 4) if both.any() else None, "標記": ""})
                    rows.append({**base, "項": "K5 早於 K3（兩者都觸發）", "值": round(float((sd["K5"] < sd["K3"])[both].mean()), 4) if both.any() else None, "標記": ""})
                    rows.append({**base, "項": "K2＝½K1＋½K0：R(K2) 恆在 R(K1) 與 R(K0) 之間 ⇒ 平均也在兩者之間 ⇒ 不可能唯一第一（最多與 K1、K0 打平）", "值": None, "標記": "構造"})
                if g == "S0":
                    du = sub["上緣突破_d"].to_numpy(); dl = sub["下緣跌破_d"].to_numpy()
                    win = lambda d: (d >= 0) & (d <= Eh - 1)
                    fb = win(du) & (~win(dl) | (du < dl))
                    fl = win(dl) & (~win(du) | (dl < du))
                    rows.append({**base, "項": "先突破上緣比例（判斷窗 [T, E−1]）", "值": round(float(fb.mean()), 4),
                                 "標記": "K3 近乎等於 K2（先突破 ＜10%）" if fb.mean() < 0.10 else "K3 與 K2 不同（先突破 ≥10%）"})
                    rows.append({**base, "項": "先跌破下緣比例", "值": round(float(fl.mean()), 4), "標記": ""})
                    rows.append({**base, "項": "兩邊都沒碰", "值": round(float((~fb & ~fl).mean()), 4), "標記": ""})
                    rows.append({**base, "項": "K3 與 K2 賣出日不同比例", "值": round(float((sd["K3"] != sd["K2"]).mean()), 4), "標記": ""})
                if g == "S−":
                    f5, fm = sub["K2_r5_d"].to_numpy(), sub["K2_ma_d"].to_numpy()
                    w5 = (f5 >= 0) & (f5 <= Eh - 1); wm = (fm >= 0) & (fm <= Eh - 1)
                    a5 = w5 & (~wm | (f5 < fm)); am = wm & (~w5 | (fm < f5)); sm = w5 & wm & (f5 == fm)
                    for nm, v in (("K2 先由 r≥−5% 觸發", a5), ("K2 先由站回20日線觸發", am), ("K2 兩條同日", sm), ("K2 兩條都沒到", ~w5 & ~wm)):
                        rows.append({**base, "項": nm, "值": round(float(v.mean()), 4), "標記": ""})
                    rows.append({**base, "項": "K4 沒有月營收（nrev＝0 ⇒ 不觸發＝不賣）", "值": round(float((sub["nrev"] == 0).mean()), 4), "標記": ""})
    return rows


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    reg = reg_check()
    log(f"[登錄] {reg}（sha {REG_SHA} 已驗）")
    J = {"性質": "出場第四輪 seq1 頻率表乾跑（⛔ 未算任何出法的 R、勝率、賣後走勢；⛔ 不存價格）", "登錄": f"台股策略線 seq1 sha {REG_SHA}",
         "裁定": "seq417 發號 N_前段 ＋3、最多暫定；先交頻率表、裁定線過目後開跑"}
    X = pickle.load(open(EXR_PKL, "rb"))
    tab = X["tab"]
    J["exright表"] = {"檔": EXR_PKL, "sha": X.get("sha"), "info": X.get("info")}
    log(f"[exright] {J['exright表']}")
    FREQ = []; EQV = []; YRS = []; MKT = []; CELL = {}; EVALL = []; STAT = {}
    for world in ("main", "early"):
        Wd, E, STt, XC = run_world(world, a.procs, tab, a.limit)
        cal = Wd["cal"]
        E = add_h(E, cal); E["世界"] = WNAME[world]
        sb = seg_bounds(cal, world)
        E["段"] = ""
        for sg, (x, y) in sb.items():
            E.loc[(E["T"] >= x) & (E["T"] <= y), "段"] = sg
        stc = STt["status"].value_counts().to_dict()
        STAT[WNAME[world]] = {"進場列": int(len(STt)), "狀態": {k: int(v) for k, v in stc.items()},
                              "保留且狀態窗被壞根截斷": int(STt.get("壞根截斷狀態窗", pd.Series(dtype=float)).fillna(0).sum()),
                              "exright": XC, "日曆": [str(cal[0].date()), str(cal[-1].date())], "事件": E["狀態"].value_counts().to_dict(),
                              "段外事件(T不在任何段)": int((E["段"] == "").sum())}
        log(f"[{WNAME[world]}] {json.dumps(STAT[WNAME[world]], ensure_ascii=False)}｜{time.time() - t0:.0f}s")
        FREQ += freq_rows(E, world, cal)
        EQV += equiv_rows(E, world, cal)
        # 分年、上市上櫃（h＝120 收件）
        k = E[E[f"E在資料內_{HJ}"] & (E["段"] != "")]
        for (yr, stt), g in k.groupby(["T年", "狀態"]):
            YRS.append({"世界": WNAME[world], "T年": int(yr), "狀態": stt, "事件": len(g), "曆月": g["T月"].nunique()})
        for (sg, stt, mk), g in k.groupby(["段", "狀態", "market"]):
            r = {"世界": WNAME[world], "段": sg, "狀態": stt, "市場": mk, "事件": len(g), "n_eff": int(min(len(g), g["T月"].nunique()))}
            for code in EXITS[grp(stt)]:
                if code != "K0":
                    r[f"{code}觸發率"] = round(float(sold(g, code, HJ).mean()), 4)
            MKT.append(r)

        EVALL.append(E)
    F = pd.DataFrame(FREQ)
    # 3 格能否判（F7）
    CR = []
    for g, stt in (("S+", "S+"), ("S0", "S0_40"), ("S−", "S−")):
        row = {"格": g, "事件定義": stt}
        ok = True
        for sg in ("探索", "確認", "早年"):
            v = F[(F["段"] == sg) & (F["狀態"] == stt) & (F["終點"] == f"T+{HJ}") & (F["出法"] == "K0")]
            row[f"{sg}_收件"] = int(v["收件(E在資料內)"].iloc[0]) if len(v) else 0
            row[f"{sg}_n_eff"] = int(v["n_eff"].iloc[0]) if len(v) else 0
            if sg != "早年":
                ok &= row[f"{sg}_n_eff"] >= NEFF_MIN
        row["能判(探索確認n_eff都≥30)"] = bool(ok)
        CR.append(row)
    CR = pd.DataFrame(CR)
    log(f"[3 格] {CR.to_dict('records')}")
    EV = pd.concat(EVALL, ignore_index=True)
    # ⛔ 自檢：輸出不得含報酬欄
    bad = [c for c in EV.columns if any(w in c for w in ("R_", "ret", "報酬", "價", "V_"))]
    if bad:
        raise SystemExit(f"⛔ 事件檔含疑似報酬／價格欄 {bad}")
    J["進場與事件"] = STAT
    J["3格"] = CR.to_dict("records")
    J["讀法"] = __doc__.split("═══ 讀法")[1]
    J["時間"] = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")
    J["必附"] = ["隨便買的平均，不是對某一檔的預測", "只看這一筆，沒算賣掉的錢拿去做什麼", "看過相近結果後重切，最多暫定",
               "各出法持有時間不同，R 是到賣出或評估點為止的這一筆報酬，不是年化（seq417）",
               "早年 reduce_v2：含減資假飆股約 0.3%；早年只上市、母體 liq_ok∧bars_ok", "S− K4 用月營收：2015 後下市股部分補回（seq411）⇒ 附缺口句"]
    F.to_csv(os.path.join(OUT, "freq.csv"), index=False, encoding="utf-8-sig")
    CR.to_csv(os.path.join(OUT, "cells.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(YRS).to_csv(os.path.join(OUT, "years.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(MKT).to_csv(os.path.join(OUT, "market.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(EQV).to_csv(os.path.join(OUT, "equiv.csv"), index=False, encoding="utf-8-sig")
    EV.to_csv(os.path.join(OUT, "events.csv.gz"), index=False, compression="gzip")
    json.dump(J, open(os.path.join(OUT, "freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] {time.time() - t0:.0f}s")
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
