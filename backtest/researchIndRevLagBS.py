# -*- coding: utf-8 -*-
"""PREREG產業落後買賣點 seq2（台股策略線登錄 seq2 sha 86b8e1101848254a；seq1 作廢；裁定 seq317 發號，N_組合 ＋1，8 格整套一判）——回測線計算子代理。
⚠ 事後重切（買賣點是看過 PREREG產業營收落後 seq2 全部輸出後才改）⇒ 兩段都合格也最多「暫定」、只進前瞻紀錄。⛔ 不給買賣建議。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchIndRevLagBS [--procs 3] [--reps 1000] | --check | --page

═══ 讀法（寫死於 2026-10-07 07:35（台北），在算任何本件數字之前；「★」＝ 登錄沒寫清楚、執行者補）═══
 B0 沿用（⛔ 不改前件檔與其輸出）：backtest/researchIndRevLag_prereg.py（LAG）的 setup、A 表（讀 LAG 輸出的 A_table.csv.gz、⛔ 不重建）、
    段快取 ~/indrevlagwork/ctx_*.pkl、產業指數 IX（主段 W1 成員、早年 liq∧bars 成員；早年上市＋上櫃版面、挑股實際只有上市 ⇒ 照 seq2／seq315 標註）、
    排名 rank_tab、候選 cands、挑股 PRE.picks_at、成交與成本（開盤成交、開盤漲停買不到不遞補、開盤跌停／停牌延後賣、下市了結、停止交易強制出場、
    賣出扣進場金額 × 0.585%）、位置子帳戶；資料 sha ＝ LAG meta 的 main（同一份 git archive）；GATE_V2 開（LAG.setup 內）
    挑產業 ⛔ 不再挑：P2｜L250｜A2｜K1｜S1；檢查日 ＝ 營收可用日（2025-12 以前次月 10 日後、2026-01 起 15 日後；★ 窗首前一日視為檢查日，同 seq2）
    段：探索 2017-03-02～2021-12-30（挑）、確認 2022-01-03～2026-08-24（判；同 seq2 資料尾）、早年 2012-06-01～2014-12-30（判）
 B1 均線（★）：MA_n[d] ＝ 產業指數 I[d−n+1..d] 平均（n 個都有值才有，pandas rolling）；「站上」＝ I[d] ＞ MA_n[d]；「跌破」＝ I[d] ＜ MA_n[d]；相等兩者皆非；沒值 ⇒ 不成立
 B2 買點 B0 ＝ 檢查日 tc 收盤選出 ⇒ tc＋1 開盤買（＝ seq2）
    買點 B1 ＝ 檢查日 tc0 收盤選出後，第一個收盤 d ≥ tc0 站上 60 日線 ⇒ d＋1 開盤買（d ＝ tc0 即「當天已在上方」）；等待天數 ＝ d − tc0（交易日）
      ★ 每個收盤（含非檢查日）都看；★ 挑股名單 S1 ＝ 實際買進日 PRE.picks_at（進場時決定）
      放棄 ②（先判）：tc0 之後任一檢查日收盤，該產業 A ≤ 0（A 有值且公司數 ≥ 5）、或在可排名集合內且（A 百分位 ＜ 2/3 或 名次差 ≤ 0）；
         ★ 不在可排名集合且 A 不 ≤ 0 ⇒ 無法判定、不放棄（計數）；② 成立當天即使站上也不買
      放棄 ①：tc0 之後第 2 個檢查日收盤仍未站上（第 2 個檢查日當天站上 ⇒ 買）
      ★ 放棄當天照規則重新選：剛放棄的那個產業當天不再選（否則同一產業立刻再等，等於沒有上限）；下一個檢查日起可再選
      等待中該位置放現金、⛔ 不改等別的產業；窗尾仍在等 ⇒ 另計
 B3 賣點（三條任一先到）
    S-T：★ 買進日算第 1 個交易日（專案 H〈n〉＝ 進場日 ＋ (n−1) 慣例，D.exit_pos）⇒ 第 start＋T−1 個交易日收盤整個產業賣；
         該股當天停牌或收盤跌停（dn_c）⇒ 照引擎慣例延到之後第一個可開盤賣的日子；T ∈ {60, 120, 250, 無上限}
    S-Y：產業指數收盤跌破 240 日線 ⇒ 次一交易日開盤整個產業賣；★「上膛」＝ 買進前一收盤（start−1）或之後任一收盤曾站上 240 日線；
         上膛後第一個跌破的收盤即訊號（＝ 由上往下跌破）
    S-Z：持有中的成員股出現真頂 T1 ⇒ 次一交易日開盤賣該檔、款項留在該位置到整個產業出場；同一段持有內 ⛔ 不再買回
    同一收盤多條成立：先判 Y（整個產業），再判 Z（剩下的股）；T 是當天收盤賣 ⇒ 早於當天收盤才判的 Y、Z
    產業出場後：該位置現金到下一個檢查日照規則補位（被賣的產業若仍符合可再挑；出場決定日剛好是檢查日 ⇒ 當天就補，同 seq2 引擎）
    ★ 新名單裡的股票若正被同位置舊產業延後賣出 ⇒ 取消賣出、改掛新產業、真頂起算的買進日改成新段開始日（計數）；被他位置持有 ⇒ 跳過（同 seq2）
 B4 真頂 T1（裁定 seq317：回測 2026-10-06 定義 ＝ backtest/researchYL_truetopT.py U2、U3 主版；直接呼叫 TTT.anchor_pit、TTT.surge_world）
    起漲點 t(d)（point-in-time）：持有中每個收盤 d，只用 d 以前（含）的收盤 ＝ TTT.anchor_pit(c, d, e)（＝ surge_flow_daily.replay 的錨定規則逐字：
      d 往前 250 個交易日內最高收盤之前的最低收盤日；e ＜ t ⇒ 改用 e 往前 250 日；t 起的漲勢在 e 前已從最高回落 30% ⇒ 改用結束日～e 最低收盤日，重複最多 50 次）；
      e ＝ 該股本段買進日；c ＝ 引擎還原收盤（ffill；向後還原只在 d 之後的除權息會把 [d−249, d] 整段同乘一個係數 ⇒ 最高、最低、30% 比例都不變 ⇒ 與當時價格等價）
    W2a 再次進入處置 ＝ d 是處置起日 ∧ [t(d), d−1] 已有 ≥ 1 次處置起日；W2b 處置出關 ＝ d 是處置迄日的下一個交易日（不另加 t 條件，同 10/6）
    兩者都要 NEAR（收盤 ≥ 含當天 20 根有效 K 棒最高收盤 × 0.9）∧ 有效 K 棒；處置表、K 棒、NEAR ＝ TTT.surge_world（飆股資料處置表、stitch 價格），依日期對到本段日曆
    ⇒ 第一個 d ≥ e 成立 ⇒ d＋1 開盤賣；只看 W2b 不需起漲點，W2a 才用 t(d)（等價於 TTT.signals_row 的 w2a | w2b，--check 對過）
    ⚠ 飆股資料母體（2,203 檔）沒有的股票 ⇒ 沒有真頂訊號（計數）；處置表 2010-12 起（早年段夠用）
 B5 格 ＝ B 2 × T 4 ＝ 8；探索段先排除退化（平均持股 ＜ 3 或平均現金比例 ＞ 30%）；★ 8 格都退化 ⇒ 從 8 格挑並標出；
    過使用者判準（年化 ＞ 0050 ∧ 年化÷|回落| ≥ 0050，PRE.lab）者取比值最高，都沒過取比值最高；平手 ⇒ 年化高、B0 先、T 小先；
    判定 ＝ 確認、早年各自標籤取較嚴；事後重切 ⇒ 合格最多「暫定合格」、另列寫「另列（最多暫定）」
 B6 必報（§四）：各出場原因次數（產業層 T／Y；個股層 Z／T／Y／強制／下市）、持有天數分佈、窗尾仍持有（產業與檔數）、B1 等待天數、
    放棄 ①／② 分開、吃到起漲到頂幾成（＝ seq2 丙 ③ 口徑 LAG.eat_rows：產業指數，Is ＝ I[進場−1]、低 ＝ 前 250 日最低、頂 ＝ 進場起 500 日最高、
    實際 ＝ I[出場−1]；★ T 收盤賣 ⇒ 出場記成賣出日＋1，使 I[出場−1] ＝ 賣出日收盤；⚠ 個股層 Z 提早賣不反映在這個產業口徑）、各年報酬
    ★ 無上限格（兩個 B）必報＋窗尾仍持有檔數；挑中格若是有限 T ⇒ 同 B 無上限格並報（裁定 seq317）
 B7 對照：① seq2 挑中格原買賣點 ＝ LAG.sim_cond 同窗重跑（⭐ 閘：權益與 LAG eq.npz 逐位元相同）；② 營量 v1 ＝ 引 PRE meta（同 seq2）；③ 0050 ＝ RR.load_bench；
    ④ 假訊號臂（★）：挑中格同 B 機制（同檢查日、同 B1 等待與放棄），⛔ 不用 T／Y／Z，改成每段產業持有在進場時抽 h（從挑中格同一段資料的
       已出場產業持有天數 end − start 等機率抽）⇒ 第 start＋h−1 收盤決定、次一開盤整個產業賣；default_rng([20261007, 317, 段序, r])，1,000 次
 B8 先驗（§六）判法（★）：① 8 格兩段都合格 0 個 ⇒ 對；② 4 個 T 都是 B1 確認段年化 ＞ B0 ⇒ 對、0 個 ⇒ 錯、其餘 ⇒ 部分（報 x/4）；
    ③ 兩個 B 各自確認段年化隨 T（60→120→250→無上限）嚴格遞增：兩個都是 ⇒ 對、只一個 ⇒ 部分、都不是 ⇒ 錯（另報各 B 相鄰升幾次）；
    ④ 挑中格三段合計、個股層出場原因（Z／T／Y）以 Y 最多 ⇒ 對（另報產業層）
 B9 查核（--check；獨立寫法，0 不同才算過；抽樣 default_rng(20261007)）
    ① 起漲點：主段挑中格交易抽 4 筆，持有期間逐日直接呼叫 surge_flow_daily.replay（price_dir ＝ 本段價格）比 t(d)；早年段同法 2 筆
    ② 真頂第一天：挑中格用到的（代號, 買進日）全部，用另寫的純 Python（處置表 csv、stitch 收盤、bar.npy、起漲點迴圈）重算第一個 T1 日；
       另抽 30 筆與 TTT.signals_row 的 w2a｜w2b 第一天比
    ③ 整條重算：挑中格＋另抽 1 格、兩段，獨立位置簿（純 Python 均線、獨立挑股 ＝ 自讀面板、自讀市值、PRE.ck_ind；排名表與產業指數共用主程式 ⇒ 已由 LAG --check ②③ 全檢查日 0 不同）
       ⇒ 權益相對差 ≤ 1e−9、每筆交易 0 不同
輸出 backtest/resultsIndRevLag/buysell/：cells.csv、episodes.csv、waits.csv、sells.csv.gz、eat.csv、years.csv、fake.csv.gz、eq.npz、meta.json、check.json、產業落後買賣點改版.html
"""
from __future__ import annotations

import argparse
import bisect
import csv
import html
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

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D                              # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402
from backtest import research13 as R13                      # noqa: E402
from backtest import researchScore as SC                    # noqa: E402
from backtest import tradability as TR                      # noqa: E402
from backtest import researchIndRev_prereg as PRE           # noqa: E402
from backtest import researchIndRevLag_prereg as LAG        # noqa: E402
from backtest import researchYL_truetopT as TTT             # noqa: E402

TIME = "2026-10-07 07:35（台北）"
OUT = "backtest/resultsIndRevLag/buysell"
WORK = os.path.expanduser("~/indrevlagwork/bs")
CH = {"P": "P2", "L": 250, "A": "A2", "K": 1, "S": "S1"}
BS = ("B0", "B1"); TS = (60, 120, 250, None)
AI = {"A1": 1, "A2": 2, "A3": 3}
COST = LAG.COST
SEED = 20261007
BG: dict = {}
LOGF = None


def log(x):
    x = f"[{time.strftime('%H:%M:%S')}] {x}"
    print(x, flush=True)
    if LOGF:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(x + "\n")


def tname(T):
    return "無上限" if T is None else str(T)


def ckey(c):
    return f"{c['B']}|T{tname(c['T'])}"


def cells():
    return [{"B": b, "T": t} for b in BS for t in TS]


# ═════════════ 設定 ═════════════
def setup(a):
    lm = json.load(open(os.path.join(LAG.OUT, "meta.json"), encoding="utf-8"))
    sha = LAG.setup(a, lm["main"])
    AT = pd.read_csv(os.path.join(LAG.OUT, "A_table.csv.gz"), float_precision="round_trip")
    LAG.install_A(AT)
    Cm = LAG.prep_part("main", LAG.MAIN_W, LAG.SEG, a)
    Ce = LAG.prep_part("early", LAG.EARLY_A, {"早年": LAG.EARLY_A}, a)
    for C in (Cm, Ce):
        attach_bs(C)
        BG[C["name"]] = C
    return sha, lm


def attach_bs(C):
    MA = {}
    for ind, z in C["IX"]["pit"].items():
        x = pd.Series(z[0])
        MA[ind] = {60: x.rolling(60, min_periods=60).mean().to_numpy(), 240: x.rolling(240, min_periods=240).mean().to_numpy()}
    C["MA"] = MA
    os.makedirs(WORK, exist_ok=True)
    sp = os.path.join(WORK, f"sw_{C['name']}.pkl")
    if os.path.exists(sp):
        SW = pickle.load(open(sp, "rb"))
    else:
        SWD, gi, mstar, info = TTT.surge_world(sorted(C["P"]), C["cal"], log)
        SW = {"SW": {s: {"NB": v["NEAR"] & v["BAR"], "START": v["START"], "EXIT": v["EXIT"], "st": v["st"]} for s, v in SWD.items()}, "gi": gi, "info": info}
        pickle.dump(SW, open(sp, "wb"), protocol=5)
    D.DATA = C["data"]
    C["SW"] = SW["SW"]; C["gi"] = SW["gi"]; C["swinfo"] = SW["info"]
    C["T1"] = {}; C["DNC"] = {}; C["T1cnt"] = Counter()
    log(f"[{C['name']}] 均線 {len(MA)} 產業｜飆股資料 {len(C['SW'])}/{len(C['P'])} 檔｜{ {k: v for k, v in SW['info'].items() if k != '不在飆股母體的檔'} }")


def dnc(C, s):
    if s not in C["DNC"]:
        D.DATA = C["data"]
        C["DNC"][s] = np.asarray(TR.one(s, C["cal"])["dn_c"], bool)
    return C["DNC"][s]


def above(C, i, d, n):
    z = C["IX"]["pit"].get(i)
    if z is None or d < 0:
        return False
    x = z[0][d]; m = C["MA"][i][n][d]
    return bool(np.isfinite(x) and np.isfinite(m) and x > m)


def below(C, i, d, n):
    z = C["IX"]["pit"].get(i)
    if z is None or d < 0:
        return False
    x = z[0][d]; m = C["MA"][i][n][d]
    return bool(np.isfinite(x) and np.isfinite(m) and x < m)


def t1_first(C, s, e):
    """B4：第一個 d ≥ e 的真頂 T1 日（本段日曆位置）；沒有 ⇒ None。"""
    k = (s, e)
    if k in C["T1"]:
        return C["T1"][k]
    SW = C["SW"].get(s); res = None
    if SW is None:
        C["T1cnt"]["無飆股資料（代號×買進日）"] += 1
    else:
        c = C["P"][s]["c"]; gi = C["gi"]; st = SW["st"]
        m = SW["NB"][e:] & (SW["EXIT"][e:] | SW["START"][e:])
        for d in (np.flatnonzero(m) + e):
            d = int(d)
            if SW["EXIT"][d]:
                res = d; break
            t = TTT.anchor_pit(c, d, e)
            if not np.isfinite(c[max(d - 249, 0):d + 1]).all():
                C["T1cnt"]["起漲點視窗含空值收盤"] += 1
            if int(np.searchsorted(st, gi[d], "left") - np.searchsorted(st, gi[t], "left")) >= 1:
                res = d; break
    C["T1"][k] = res
    return res


def qualified(RK, i):
    """B2 ②：False ＝ 已不合格；None ＝ 無法判定；True ＝ 仍合格。"""
    A, L = CH["A"], CH["L"]
    v = RK["Aall"].get(i)
    if v is not None and v[0] >= 5 and np.isfinite(v[AI[A]]) and v[AI[A]] <= 0:
        return False
    k = RK["idx"].get(i)
    if k is None or RK["n"] < 2:
        return None
    pa = RK["pA"][A][k]; d = pa - RK["pL"][L][k]
    if pa < 2 / 3 - 1e-12 or d <= 0:
        return False
    return True


# ═════════════ 引擎 ═════════════
def sim_bs(C, t0, t1, cfg, rng=None, hpool=None):
    D.DATA = C["data"]
    P, dl, ncal = C["P"], C["dl"], C["ncal"]
    SF = LAG.sfdays(C, t1)
    P_, A, L, K, S = CH["P"], CH["A"], CH["L"], CH["K"], CH["S"]
    B, T = cfg["B"], cfg["T"]; fake = hpool is not None
    checks = set(c for c in C["checks"] if t0 - 1 <= c <= t1 - 1)
    eq = np.ones(ncal); scash = [1.0 / K] * K; sval = [1.0 / K] * K; slot = [None] * K
    pos = {}; pend = {}
    npos = np.zeros(ncal, np.int16); cashf = np.zeros(ncal); costd = np.zeros(ncal); buyd = np.zeros(ncal)
    cnt = Counter(); episodes = []; waits = []; trades = []; sells = []

    def close_slot(k, why, end):
        z = slot[k]
        for s, p_ in pos.items():
            if p_[2] == k and s not in pend:
                pend[s] = why
        e_ = {kk: v for kk, v in z.items() if kk not in ("mode", "armed")}
        e_.update(end=end, why=why); episodes.append(e_); slot[k] = None
        cnt[f"產業出場_{why}"] += 1

    def start_hold(k, i, t, sig, trig, info, newbuy):
        lst = PRE.picks_at(C, "pit", "W1", t).get(i, {}).get(S, [])
        if not lst:
            cnt["ind_empty"] += 1
        buy = []
        for s in lst:
            if s in pos:
                if pos[s][2] == k and s in pend:
                    pend.pop(s); pos[s][3] = t; cnt["取消賣出改掛"] += 1
                else:
                    cnt["他位置持有跳過"] += 1
                continue
            buy.append(s)
        h = int(hpool[rng.integers(len(hpool))]) if fake else None
        slot[k] = {"mode": "hold", "ind": i, "slot": k, "sig": sig, "trig": trig, "start": t, "wait": trig - sig, "armed": above(C, i, t - 1, 240),
                   "armed0": above(C, i, t - 1, 240), "h": h, "nz": 0, "n_list": len(lst), "list": "、".join(lst), **info}
        newbuy[k] = (buy, len(lst))
        if B == "B1":
            waits.append({"ind": i, "sig": sig, "end": trig, "結果": "買進", "等待天數": trig - sig})

    for t in range(t0, t1 + 1):
        for s in [s for s in pos if SF.get(s) is not None and t == SF[s] + 1]:
            u, amt, k, _ = pos.pop(s)
            px = P[s]["c"][t]
            scash[k] += u * px - amt * COST; costd[t] += amt * COST; cnt["stop_force"] += 1
            pend.pop(s, None); trades.append((t, s, "sf", float(px))); sells.append((t, s, "強制"))
        newbuy = {}
        tc = t - 1
        if tc >= t0 - 1:
            ischk = tc in checks
            RK = LAG.rank_tab(C, "pit", tc, tc) if ischk else None
            # (1) 產業層 Y（或假訊號 F）
            for k in range(K):
                z = slot[k]
                if z is None or z["mode"] != "hold":
                    continue
                i = z["ind"]
                if fake:
                    if tc == z["start"] + z["h"] - 1:
                        close_slot(k, "F", t)
                elif z["armed"] and below(C, i, tc, 240):
                    close_slot(k, "Y", t)
                elif above(C, i, tc, 240):
                    z["armed"] = True
            # (2) 個股層 Z
            if not fake:
                for s in sorted(pos):
                    if s in pend:
                        continue
                    k = pos[s][2]; z = slot[k]
                    if z is None or z["mode"] != "hold":
                        continue
                    f = t1_first(C, s, pos[s][3])
                    if f is not None and f == tc:
                        pend[s] = "Z"; z["nz"] += 1
            # (3) B1 等待
            excl = set()
            for k in range(K):
                z = slot[k]
                if z is None or z["mode"] != "wait":
                    continue
                i = z["ind"]
                if ischk and tc > z["sig"]:
                    z["nchk"] += 1
                    q = qualified(RK, i)
                    if q is False:
                        waits.append({"ind": i, "sig": z["sig"], "end": tc, "結果": "放棄②", "等待天數": tc - z["sig"]})
                        slot[k] = None; excl.add(i); cnt["放棄②"] += 1; continue
                    if q is None:
                        cnt["等待中②無法判定"] += 1
                if above(C, i, tc, 60):
                    start_hold(k, i, t, z["sig"], tc, z["info"], newbuy)
                elif ischk and z["nchk"] >= 2:
                    waits.append({"ind": i, "sig": z["sig"], "end": tc, "結果": "放棄①", "等待天數": tc - z["sig"]})
                    slot[k] = None; excl.add(i); cnt["放棄①"] += 1
            # (4) 檢查日補位
            if ischk:
                vac = [k for k in range(K) if slot[k] is None]
                if vac:
                    held = {z["ind"] for z in slot if z is not None} | excl
                    cl = LAG.cands(RK, P_, A, L, held, "rule")
                    if cl is None:
                        cnt["無法排名檢查日"] += 1; cl = []
                    for k in vac:
                        if not cl:
                            cnt["空位無候選"] += 1; continue
                        i = cl.pop(0)
                        info = {"M": RK["M"], **LAG.rk_info(RK, i, A, L)}
                        if B == "B0" or above(C, i, tc, 60):
                            start_hold(k, i, t, tc, tc, info, newbuy)
                        else:
                            slot[k] = {"mode": "wait", "ind": i, "sig": tc, "nchk": 0, "info": info}
        # ── 開盤賣
        for s in sorted(pend):
            x = P[s]; o_t = x["o"][t]
            if x["trd"][t] and not x["dn_o"][t] and np.isfinite(o_t) and o_t > 0:
                px = o_t; kd = "open"
            elif (not x["trd"][t]) and s in dl and t > dl[s]["last"] and dl[s]["status"].startswith("delisted"):
                px = x["c"][t]; kd = "delist"; cnt["delist_settled"] += 1
            else:
                cnt["sell_delayed_days"] += 1; continue
            u, amt, k, _ = pos.pop(s)
            scash[k] += u * px - amt * COST; costd[t] += amt * COST; cnt["sell"] += 1
            why = pend.pop(s); trades.append((t, s, kd, float(px))); sells.append((t, s, why if kd != "delist" else f"{why}（下市了結）"))
        # ── 開盤買
        for k in sorted(newbuy):
            buy, n_i = newbuy[k]
            for s in buy:
                x = P[s]; o_t = x["o"][t]
                if not x["trd"][t] or not (np.isfinite(o_t) and o_t > 0):
                    cnt["buy_blocked_halt"] += 1; continue
                if x["up_o"][t]:
                    cnt["buy_blocked_limit_up"] += 1; continue
                amt = min(sval[k] / n_i, scash[k])
                if amt <= 1e-12:
                    break
                scash[k] -= amt
                pos[s] = [amt / o_t, amt, k, t]
                cnt["buy"] += 1; buyd[t] += amt; trades.append((t, s, "buy", float(o_t)))
        # ── S-T 收盤
        if T is not None and not fake:
            for k in range(K):
                z = slot[k]
                if z is None or z["mode"] != "hold" or t != z["start"] + T - 1:
                    continue
                for s in sorted(s for s, p_ in pos.items() if p_[2] == k):
                    x = P[s]
                    if x["trd"][t] and not dnc(C, s)[t] and np.isfinite(x["c"][t]) and x["c"][t] > 0:
                        u, amt, _, _ = pos.pop(s); px = x["c"][t]
                        scash[k] += u * px - amt * COST; costd[t] += amt * COST; cnt["sell"] += 1
                        why = pend.pop(s, "T"); trades.append((t, s, "close", float(px))); sells.append((t, s, why))
                    else:
                        pend.setdefault(s, "T"); cnt["T收盤賣不掉延後"] += 1
                close_slot(k, "T", t + 1)
        # ── 計值
        hv = [0.0] * K
        for s, (u, _, k, _) in pos.items():
            hv[k] += u * P[s]["c"][t]
        sval = [scash[k] + hv[k] for k in range(K)]
        eq[t] = sum(sval)
        npos[t] = len(pos); cashf[t] = sum(scash) / eq[t] if eq[t] > 0 else np.nan
    eq[t1 + 1:] = eq[t1]
    tail_n = {}
    for k in range(K):
        z = slot[k]
        if z is None:
            continue
        if z["mode"] == "hold":
            e_ = {kk: v for kk, v in z.items() if kk not in ("mode", "armed")}
            e_.update(end=None, why="窗尾"); episodes.append(e_)
            tail_n[z["ind"]] = sum(1 for s, p_ in pos.items() if p_[2] == k and s not in pend)
        else:
            waits.append({"ind": z["ind"], "sig": z["sig"], "end": None, "結果": "窗尾仍在等", "等待天數": t1 - z["sig"]})
    return {"eq": eq, "npos": npos, "cashf": cashf, "costd": costd, "buyd": buyd, "cnt": dict(cnt), "episodes": episodes, "waits": waits,
            "trades": trades, "sells": sells, "tail_n": tail_n, "tail_pos": len(pos)}


# ═════════════ 指標 ═════════════
def stats_bs(res, a, b, t1):
    c, m, ratio = SC.seg_metrics(res["eq"], a, b)
    yrs = (b + 1 - a) / 245; meq = float(res["eq"][a:b + 1].mean())
    ep = [e for e in res["episodes"] if a <= e["start"] <= b]
    hd = [((e["end"] if e["end"] is not None else t1 + 1) - e["start"]) for e in ep]
    wt = [w for w in res["waits"] if a <= w["sig"] <= b]
    sl = Counter(w for t, _, w in res["sells"] if a <= t <= b)
    out = {"年化": c, "回落": m, "比值": ratio, "年化波動": RR.ann_vol(res["eq"][a:b + 1]),
           "平均持股": float(res["npos"][a:b + 1].mean()), "現金比例": float(np.nanmean(res["cashf"][a:b + 1])),
           "每年換手": float(res["buyd"][a:b + 1].sum()) / meq / yrs, "成本／年": float(res["costd"][a:b + 1].sum()) / meq / yrs,
           "產業持有段數": len(ep), "平均持有天數": float(np.mean(hd)) if hd else np.nan, "持有天數中位": float(np.median(hd)) if hd else np.nan,
           "產業出場T": sum(e["why"] == "T" for e in ep), "產業出場Y": sum(e["why"] == "Y" for e in ep), "產業出場F": sum(e["why"] == "F" for e in ep),
           "窗尾仍持有": sum(e["end"] is None for e in ep),
           "個股賣Z": sum(v for k, v in sl.items() if k.startswith("Z")), "個股賣T": sum(v for k, v in sl.items() if k.startswith("T")),
           "個股賣Y": sum(v for k, v in sl.items() if k.startswith("Y")), "個股賣F": sum(v for k, v in sl.items() if k.startswith("F")),
           "個股強制": sl.get("強制", 0), "個股下市了結": sum(v for k, v in sl.items() if "下市" in k),
           "等待次數": len(wt), "等待後買進": sum(w["結果"] == "買進" for w in wt), "放棄①": sum(w["結果"] == "放棄①" for w in wt),
           "放棄②": sum(w["結果"] == "放棄②" for w in wt), "窗尾仍在等": sum(w["結果"] == "窗尾仍在等" for w in wt),
           "等待天數中位（買進者）": float(np.median([w["等待天數"] for w in wt if w["結果"] == "買進"])) if any(w["結果"] == "買進" for w in wt) else np.nan,
           "等待0天（當天已站上）": sum(w["結果"] == "買進" and w["等待天數"] == 0 for w in wt)}
    return out


def hold_dist(hd):
    if not hd:
        return {"筆數": 0}
    return {"筆數": len(hd), **{f"p{q}": float(np.percentile(hd, q)) for q in (10, 25, 50, 75, 90)}, "最長": int(max(hd)),
            "≤21": sum(h <= 21 for h in hd), "22～63": sum(21 < h <= 63 for h in hd), "64～250": sum(63 < h <= 250 for h in hd), "＞250": sum(h > 250 for h in hd)}


def eat_summary(rows):
    g = pd.DataFrame(rows)
    if not len(g):
        return {"筆數": 0}
    return {"筆數": int(len(g)), "已漲250中位": float(g["已漲250"].median()), "還吃得到中位": float(g["吃到幾成"].median()),
            "實際持有吃到幾成中位": float(g["實際持有吃到幾成"].median()), "實際持有吃到幾成平均": float(g["實際持有吃到幾成"].mean()),
            "持有報酬中位": float(g["持有報酬"].median()), "持有報酬平均": float(g["持有報酬"].mean()), "窗尾仍持有": int(g["窗尾仍持有"].sum()),
            "未滿500日": int(g["未滿500日"].sum())}


def seg_of(C, t):
    return next((k for k, (a, b) in C["segp"].items() if a <= t <= b), "")


def _fake_job(args):
    part, cfg, r, hp = args
    C = BG[part]; t0, t1 = C["win"]
    res = sim_bs(C, t0, t1, cfg, rng=np.random.default_rng([SEED, 317, 0 if part == "main" else 1, r]), hpool=np.asarray(hp, np.int64))
    out = {"part": part, "r": r}
    for nm, (a, b) in C["segp"].items():
        c, m, ratio = SC.seg_metrics(res["eq"], a, b)
        out.update({f"{nm}_年化": c, f"{nm}_回落": m, f"{nm}_比值": ratio})
    return out


# ═════════════ 主程式 ═════════════
def run(a):
    T00 = time.time()
    os.makedirs(WORK, exist_ok=True)
    sha, lm = setup(a)
    Cm, Ce = BG["main"], BG["early"]
    META = {"讀法寫死": TIME, "main": sha, "成本": COST, "GATE_V2": True, "挑產業（沿用 seq2 挑中格）": CH, "飆股資料": {"main": Cm["swinfo"], "early": Ce["swinfo"]}}
    t0m, t1m = Cm["win"]
    RR.use_snapshot()
    cf, mf = R13.window_stats(Cm["bench"], 0, Cm["ncal"], t0m, t1m + 1)
    if not (repr(float(cf)) == repr(PRE.ANCHOR[0]) and repr(float(mf)) == repr(PRE.ANCHOR[1])):
        raise SystemExit("⛔ 0050 錨不過")
    D.DATA = Cm["data"]
    Z = {nm: SC.seg_metrics(Cm["bench"], x, y) for nm, (x, y) in Cm["segp"].items()}
    Z["早年"] = SC.seg_metrics(Ce["bench"], *Ce["segp"]["早年"])
    META["0050"] = {k: dict(zip(("年化", "回落", "比值"), v)) for k, v in Z.items()}
    log("[0050] " + "｜".join(f"{k} {v[0]:.2%}／{v[1]:.2%}／{v[2]:.3f}" for k, v in Z.items()))
    for C in (Cm, Ce):
        LAG.precompute(C)
    # ── 對照 ①：seq2 原買賣點重跑（閘：逐位元）
    leq = np.load(os.path.join(LAG.OUT, "eq.npz"))
    PREV = {}; CT = {"seq2挑中格（原買賣點）": {}}
    for part in ("main", "early"):
        C = BG[part]; t0, t1 = C["win"]
        rp = LAG.sim_cond(C, t0, t1, dict(CH, ver="pit", order="rule"))
        ok = bool(np.array_equal(rp["eq"], leq[part]))
        META.setdefault("閘", {})[f"seq2 挑中格重跑 ＝ LAG eq.npz（{part}，逐位元）"] = ok
        if not ok:
            raise SystemExit(f"⛔ seq2 重跑不等於 LAG eq.npz（{part}）")
        PREV[part] = rp
        for sg, (x, y) in C["segp"].items():
            CT["seq2挑中格（原買賣點）"][sg] = LAG.stats_c(rp, x, y, t1)
    log(f"[閘] {META['閘']}")
    pm = json.load(open("backtest/resultsIndRev/prereg/meta.json", encoding="utf-8"))
    CT["營量v1_T1"] = pm["對照"]["營量v1_T1"]
    # ── 8 格 × 兩段（主程序依序跑；快取留給假訊號臂）
    rows = []; RES = {}; t00 = time.time()
    for cfg in cells():
        key = ckey(cfg); row = {"key": key, "B": cfg["B"], "T": tname(cfg["T"])}
        for part in ("main", "early"):
            C = BG[part]; t0, t1 = C["win"]
            res = sim_bs(C, t0, t1, cfg); RES[(key, part)] = res
            for nm, (x, y) in C["segp"].items():
                row.update({f"{nm}_{k}": v for k, v in stats_bs(res, x, y, t1).items()})
                row[f"{nm}_吃到"] = json.dumps(eat_summary([r for r in LAG.eat_rows(C, C["IX"]["pit"], res["episodes"], t1, C["segp"]) if r["段"] == nm]), ensure_ascii=False)
            row[f"{part}_計數"] = json.dumps(res["cnt"], ensure_ascii=False)
            row[f"{part}_窗尾產業與檔數"] = json.dumps(res["tail_n"], ensure_ascii=False)
        rows.append(row)
        log(f"[格 {key}] 探索 {row['探索_年化']:+.2%}／{row['探索_回落']:+.2%}｜確認 {row['確認_年化']:+.2%}／{row['確認_回落']:+.2%}｜早年 {row['早年_年化']:+.2%}｜{time.time() - t00:.0f}s")
    TM = pd.DataFrame(rows)
    TM["退化"] = (TM["探索_平均持股"] < 3) | (TM["探索_現金比例"] > 0.30)
    for sg in ("探索", "確認", "早年"):
        TM[f"{sg}_標籤"] = [PRE.lab(c, m, Z[sg][0], Z[sg][1]) for c, m in zip(TM[f"{sg}_年化"], TM[f"{sg}_回落"])]
    alldeg = bool(TM["退化"].all())
    cand = (TM if alldeg else TM[~TM["退化"]]).copy(); cand["過"] = cand["探索_標籤"] == "合格"
    pool_ = cand[cand["過"]] if cand["過"].any() else cand
    pool_ = pool_.assign(_b=pool_["B"].map({b: i for i, b in enumerate(BS)}), _t=pool_["T"].map({tname(t): i for i, t in enumerate(TS)}))
    best = pool_.sort_values(["探索_比值", "探索_年化", "_b", "_t"], ascending=[False, False, True, True]).iloc[0]
    ck = best["key"]; CHB = {"B": best["B"], "T": None if best["T"] == "無上限" else int(best["T"])}
    lc, le = best["確認_標籤"], best["早年_標籤"]
    fin_ = min((lc, le), key=lambda z: PRE.RANKL.get(z, -1))
    final = {"合格": "暫定合格（事後重切；只進前瞻紀錄）", "另列": "另列（事後重切，最多暫定；只進前瞻紀錄）"}.get(fin_, fin_)
    TM.to_csv(os.path.join(OUT, "cells.csv"), index=False, float_format="%.10g")
    both = (TM["確認_標籤"] == "合格") & (TM["早年_標籤"] == "合格")
    META["挑格"] = {"格數": int(len(TM)), "退化格數": int(TM["退化"].sum()), "8格都退化": alldeg, "探索過判準格數": int(cand["過"].sum()), "挑中": ck, "挑中參數": {"B": CHB["B"], "T": tname(CHB["T"])},
                  **{sg: {k: float(best[f"{sg}_{k}"]) for k in ("年化", "回落", "比值")} for sg in ("探索", "確認", "早年")},
                  "確認標籤": lc, "早年標籤": le, "判定": final, "兩段都合格格數": int(both.sum()), "兩段都合格格數（非退化）": int((both & ~TM["退化"]).sum()),
                  "確認段合格格數": int((TM["確認_標籤"] == "合格").sum()), "早年段合格格數": int((TM["早年_標籤"] == "合格").sum())}
    log(f"[挑格] {json.dumps(META['挑格'], ensure_ascii=False)}")
    # ── 細項：全 8 格的段、等待、賣出原因
    EP, WT, SL, EAT = [], [], [], []
    for cfg in cells():
        key = ckey(cfg)
        for part in ("main", "early"):
            C = BG[part]; res = RES[(key, part)]; t1 = C["win"][1]
            for e in res["episodes"]:
                EP.append({"格": key, "part": part, "段": seg_of(C, e["start"]), "產業": e["ind"], "選出日": str(C["cal"][e["sig"]].date()), "站上日": str(C["cal"][e["trig"]].date()),
                           "進場日": str(C["cal"][e["start"]].date()), "出場日": str(C["cal"][e["end"]].date()) if e["end"] is not None and e["end"] < C["ncal"] else "",
                           "出場原因": e["why"], "持有天數": (e["end"] if e["end"] is not None else t1 + 1) - e["start"], "等待天數": e["wait"],
                           "買進時已在240線上": int(e["armed0"]), "真頂賣檔數": e["nz"], "名單檔數": e["n_list"], "名單": e["list"],
                           **{k: e.get(k) for k in ("M", "A值", "A百分位", "L報酬", "L百分位", "名次差")}})
            for w in res["waits"]:
                WT.append({"格": key, "part": part, "段": seg_of(C, w["sig"]), "產業": w["ind"], "選出日": str(C["cal"][w["sig"]].date()), "結果": w["結果"], "等待天數": w["等待天數"]})
            for t, s, why in res["sells"]:
                SL.append({"格": key, "part": part, "段": seg_of(C, t), "日": str(C["cal"][t].date()), "代號": s, "原因": why})
            for r in LAG.eat_rows(C, C["IX"]["pit"], res["episodes"], t1, C["segp"]):
                r.update({"格": key, "part": part}); EAT.append(r)
    for part in ("main", "early"):
        C = BG[part]; t1 = C["win"][1]
        for r in LAG.eat_rows(C, C["IX"]["pit"], PREV[part]["episodes"], t1, C["segp"]):
            r.update({"格": "seq2原買賣點", "part": part}); EAT.append(r)
    EPD, WTD, SLD, EATD = pd.DataFrame(EP), pd.DataFrame(WT), pd.DataFrame(SL), pd.DataFrame(EAT)
    EPD.to_csv(os.path.join(OUT, "episodes.csv"), index=False, float_format="%.8g")
    WTD.to_csv(os.path.join(OUT, "waits.csv"), index=False)
    SLD.to_csv(os.path.join(OUT, "sells.csv.gz"), index=False, compression={"method": "gzip", "mtime": 0})
    EATD.to_csv(os.path.join(OUT, "eat.csv"), index=False, float_format="%.8g")
    DET = {}
    for key in {ck, f"{CHB['B']}|T無上限", "B0|T無上限", "B1|T無上限"}:
        d_ = {}
        for part in ("main", "early"):
            C = BG[part]; res = RES[(key, part)]; t1 = C["win"][1]
            hd = [((e["end"] if e["end"] is not None else t1 + 1) - e["start"]) for e in res["episodes"]]
            d_[f"{part}_持有天數分佈"] = hold_dist(hd)
            tail = [{"產業": e["ind"], "進場日": str(C["cal"][e["start"]].date()), "已持有交易日": t1 + 1 - e["start"], "仍持有檔數": res["tail_n"].get(e["ind"])}
                    for e in res["episodes"] if e["end"] is None]
            d_[f"{part}_窗尾"] = {"窗尾": str(C["cal"][t1].date()), "產業": tail, "仍持有檔數（含延後賣）": res["tail_pos"],
                                 "仍在等": [w for w in res["waits"] if w["結果"] == "窗尾仍在等"]}
            wb = [w["等待天數"] for w in res["waits"] if w["結果"] == "買進"]
            d_[f"{part}_等待天數分佈（買進者）"] = hold_dist(wb)
            d_[f"{part}_計數"] = res["cnt"]
            d_[f"{part}_真頂計數"] = dict(C["T1cnt"])
        DET[key] = d_
    META["細項"] = DET
    # 先驗 ④ 原料：挑中格三段合計
    EATS = {}
    for (g_, part, sg), g in EATD.groupby(["格", "part", "段"]):
        EATS[f"{g_}|{sg}"] = eat_summary(g.to_dict("records"))
    META["吃到起漲到頂"] = EATS
    YR = []
    for part in ("main", "early"):
        C = BG[part]; t0, t1 = C["win"]
        yr = PRE.year_rets(RES[(ck, part)]["eq"], C["cal"], t0, t1); yb = PRE.year_rets(C["bench"] / C["bench"][t0], C["cal"], t0, t1)
        yp = PRE.year_rets(PREV[part]["eq"], C["cal"], t0, t1)
        for y in yr:
            YR.append({"段": part, "年": y, "挑中格": yr[y], "seq2原買賣點": yp[y], "0050": yb[y]})
    pd.DataFrame(YR).to_csv(os.path.join(OUT, "years.csv"), index=False, float_format="%.8g")
    # ── 假訊號臂
    jobs = []
    for part in ("main", "early"):
        C = BG[part]; t1 = C["win"][1]
        hp = [e["end"] - e["start"] for e in RES[(ck, part)]["episodes"] if e["end"] is not None]
        if not hp:
            hp = [e["end"] - e["start"] for e in RES[(ck, "main")]["episodes"] if e["end"] is not None]
        META.setdefault("假訊號臂", {})[f"{part}_持有天數池"] = {"筆數": len(hp), **hold_dist(hp)}
        jobs += [(part, CHB, r, hp) for r in range(a.reps)]
    t0_ = time.time()
    with Pool(a.procs) as pool:
        FK = pd.DataFrame(pool.map(_fake_job, jobs, chunksize=10))
    FK.to_csv(os.path.join(OUT, "fake.csv.gz"), index=False, compression={"method": "gzip", "mtime": 0}, float_format="%.10g")
    log(f"[假訊號] {len(jobs)} 次｜{time.time() - t0_:.0f}s")
    FS = {}
    for part in ("main", "early"):
        g = FK[FK["part"] == part]
        for sg in BG[part]["segp"]:
            xx = g[f"{sg}_年化"].to_numpy(float); rr_ = g[f"{sg}_比值"].to_numpy(float)
            FS[sg] = {"中位": float(np.nanmedian(xx)), "p10": float(np.nanquantile(xx, .1)), "p90": float(np.nanquantile(xx, .9)), "回落中位": float(g[f"{sg}_回落"].median()),
                      "p_年化（假訊號 ≥ 挑中格）": float(np.nanmean(xx >= META["挑格"][sg]["年化"])), "p_比值": float(np.nanmean(rr_ >= META["挑格"][sg]["比值"])),
                      "贏0050比例": float(np.nanmean(xx > Z[sg][0]))}
    CT["假訊號臂"] = FS
    META["對照"] = CT
    np.savez_compressed(os.path.join(OUT, "eq.npz"), **{f"{ckey(c).replace('|', '_')}_{p}": RES[(ckey(c), p)]["eq"] for c in cells() for p in ("main", "early")},
                        prev_main=PREV["main"]["eq"], prev_early=PREV["early"]["eq"], bench_main=Cm["bench"], bench_early=Ce["bench"])
    META["先驗"] = priors(META, TM, SLD, EPD, ck)
    META["耗時秒"] = round(time.time() - T00)
    json.dump(META, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] {time.time() - T00:.0f}s")


def priors(META, TM, SLD, EPD, ck):
    out = []
    n2 = META["挑格"]["兩段都合格格數"]
    out.append(("①", "兩段都合格的格 0 個", f"8 格兩段都合格 {n2} 格（確認段合格 {META['挑格']['確認段合格格數']}、早年段合格 {META['挑格']['早年段合格格數']}）", "對" if n2 == 0 else "錯"))
    tt = TM.set_index("key")
    win = [(tname(T), tt.loc[f"B1|T{tname(T)}", "確認_年化"], tt.loc[f"B0|T{tname(T)}", "確認_年化"]) for T in TS]
    nb = sum(b1 > b0 for _, b1, b0 in win)
    out.append(("②", "同 T 下 B1 轉強確認段年化高於 B0", "；".join(f"T{t}：B1 {b1:+.1%} vs B0 {b0:+.1%}" for t, b1, b0 in win) + f"（{nb}/4）",
                "對" if nb == 4 else ("錯" if nb == 0 else f"部分（{nb}/4）")))
    seqs = {}
    for b in BS:
        v = [tt.loc[f"{b}|T{tname(T)}", "確認_年化"] for T in TS]
        seqs[b] = (v, sum(v[j + 1] > v[j] for j in range(3)))
    allup = all(n == 3 for _, n in seqs.values()); anyup = any(n == 3 for _, n in seqs.values())
    out.append(("③", "T 越長年化越高（確認段）", "；".join(f"{b}：" + " → ".join(f"{x:+.1%}" for x in v) + f"（相鄰升 {n}/3）" for b, (v, n) in seqs.items()),
                "對" if allup else ("部分" if anyup else "錯")))
    g = SLD[SLD["格"] == ck]
    rc = Counter()
    for w in g["原因"]:
        for k in ("Z", "T", "Y"):
            if w.startswith(k):
                rc[k] += 1
    ge = EPD[EPD["格"] == ck]; ic = Counter(ge["出場原因"])
    top = max(("Z", "T", "Y"), key=lambda k: (rc[k], k == "Y"))
    out.append(("④", "出場原因以年線為最多", f"挑中格三段合計 個股層：真頂 Z {rc['Z']}、天數 T {rc['T']}、年線 Y {rc['Y']}；產業層：T {ic.get('T', 0)}、Y {ic.get('Y', 0)}、窗尾 {ic.get('窗尾', 0)}",
                "對" if (top == "Y" and rc["Y"] > max(rc["Z"], rc["T"])) else "錯"))
    return out


# ═════════════ 查核（獨立寫法） ═════════════
class _Got(Exception):
    pass


def ck_surge(C):
    """獨立讀：處置表 csv、stitch 原始收盤、bar.npy ⇒ 每檔（起日、迄日、近高判斷用陣列），以飆股日曆位置表示。"""
    from backtest import researchSurge5 as S5
    D.DATA = S5.ST; cal_s = D.load_calendar()
    uni = pd.read_csv(os.path.join(S5.WORK, "uni.csv"), dtype=str); s2i = {sd: i for i, sd in enumerate(uni["stock_id"])}
    bar_s = np.load(os.path.join(S5.WORK, "bar.npy"), mmap_mode="r")
    dsp = pd.read_csv(os.path.join(S5.MAIN, "meta", "disposal.csv"), dtype={"stock_id": str}, usecols=["stock_id", "start_date", "end_date"])
    D.DATA = C["data"]
    return {"cal_s": cal_s, "pos_s": {d: j for j, d in enumerate(cal_s)}, "uni": uni, "s2i": s2i, "bar": bar_s, "dsp": dsp, "cache": {}}


def ck_t1(C, KS_, s, e):
    """純 Python：第一個 d ≥ e 的 W2a／W2b（NEAR）日。"""
    from backtest import researchSurge5 as S5
    cal = C["cal"]; n = C["ncal"]
    if s not in KS_["s2i"]:
        return None
    if s not in KS_["cache"]:
        D.DATA = S5.ST
        si = KS_["s2i"][s]
        c0 = D.load_stock(s, KS_["uni"].loc[si, "market"], KS_["cal_s"]).df["close"].to_numpy(float)
        D.DATA = C["data"]
        bars = [d for d in range(len(KS_["cal_s"])) if np.isfinite(c0[d]) and KS_["bar"][si, d]]
        g = KS_["dsp"][KS_["dsp"]["stock_id"] == s]
        starts = sorted(int(KS_["cal_s"].searchsorted(pd.Timestamp(x))) for x in g["start_date"])
        ends = [int(KS_["cal_s"].searchsorted(pd.Timestamp(y), side="right")) - 1 for y in g["end_date"]]
        KS_["cache"][s] = (c0, {d: j for j, d in enumerate(bars)}, bars, starts, set(ends))
    c0, bpos, bars, starts, ends = KS_["cache"][s]
    c = [float(v) for v in C["P"][s]["c"]]
    stset = set(starts)

    def a_of(T_):
        lo = max(T_ - 249, 0); P0 = lo
        for d in range(lo, T_ + 1):
            if c[d] > c[P0] or (math.isnan(c[d]) and not math.isnan(c[P0])):
                P0 = d
            if math.isnan(c[P0]):
                break
        t_ = lo
        for d in range(lo, P0 + 1):
            if math.isnan(c[t_]):
                break
            if c[d] < c[t_] or math.isnan(c[d]):
                t_ = d
        return t_

    def anchor(T_, eb):
        t = a_of(T_)
        if eb < t:
            t = a_of(eb)
        for _ in range(50):
            rm = -math.inf; st_ = None
            for d in range(t, T_ + 1):
                rm = max(rm, c[d]) if not math.isnan(c[d]) and not math.isnan(rm) else math.nan
                if not math.isnan(rm) and c[d] <= rm * 0.7:
                    st_ = d; break
            if st_ is None or st_ >= eb:
                break
            m_ = st_
            for d in range(st_, eb + 1):
                if c[d] < c[m_]:
                    m_ = d
            t = m_
        return t
    for d in range(e, n):
        ds = KS_["pos_s"].get(cal[d])
        if ds is None or ds not in bpos:
            continue
        j = bpos[ds]
        if not (j >= 19 and c0[ds] >= 0.9 * max(c0[bars[j - 19:j + 1]])):
            continue
        if (ds - 1) in ends:
            return d
        if ds in stset:
            t = anchor(d, e); ts = KS_["pos_s"].get(cal[t])
            if ts is None:
                ts = int(KS_["cal_s"].searchsorted(cal[t]))
            if any(ts <= x <= ds - 1 for x in starts):
                return d
    return None


def ck_book(C, cfg, t0, t1, rkk, picks, t1fn):
    """B2～B3 照字面重寫（K＝1）；共用：價格與成交旗標、產業指數值、排名表。"""
    P, dl, n = C["P"], C["dl"], C["ncal"]
    I = {i: [float(v) for v in z[0]] for i, z in C["IX"]["pit"].items()}
    mac = {}

    def ma(i, d, w):
        if (i, w) not in mac:
            x = I[i]; out = [math.nan] * n
            for k in range(w - 1, n):
                seg = x[k - w + 1:k + 1]
                if all(v == v for v in seg):
                    out[k] = math.fsum(seg) / w
            mac[(i, w)] = out
        return mac[(i, w)][d]

    def up(i, d, w):
        return i in I and d >= 0 and I[i][d] == I[i][d] and ma(i, d, w) == ma(i, d, w) and I[i][d] > ma(i, d, w)

    def dn(i, d, w):
        return i in I and d >= 0 and I[i][d] == I[i][d] and ma(i, d, w) == ma(i, d, w) and I[i][d] < ma(i, d, w)

    def gone(R, i):
        A_ = CH["A"]; j = {"A1": 1, "A2": 2, "A3": 3}[A_]
        v = R["Aall"].get(i)
        if v is not None and v[0] >= 5 and v[j] == v[j] and v[j] <= 0:
            return True
        if i in R["names"] and len(R["names"]) >= 2:
            k = R["names"].index(i)
            if R["pA"][A_][k] < 2 / 3 - 1e-12 or R["pA"][A_][k] - R["pL"][CH["L"]][k] <= 0:
                return True
        return False
    stopd = {}
    for s, v in P.items():
        b = np.flatnonzero(v["valid"])
        if len(b) and b[-1] < t1:
            stopd[s] = int(b[-1])
    chk = set(t for t in C["checks"] if t0 - 1 <= t <= t1 - 1)
    T = cfg["T"]; B = cfg["B"]
    st = {"m": "空", "cash": 1.0, "val": 1.0}
    book = {}; q = {}; trades = []; eq = [1.0] * n
    for t in range(t0, t1 + 1):
        for s in sorted(book):
            if s in stopd and t == stopd[s] + 1:
                b = book.pop(s); st["cash"] += b["u"] * P[s]["c"][t] - b["amt"] * COST; q.pop(s, None); trades.append((t, s, "sf", float(P[s]["c"][t])))
        d = t - 1; go = None; plan = None
        if d >= t0 - 1:
            if st["m"] == "持":
                if st["armed"] and dn(st["i"], d, 240):
                    for s in book:
                        q.setdefault(s, "Y")
                    st = {"m": "空", "cash": st["cash"], "val": st["val"]}
                elif up(st["i"], d, 240):
                    st["armed"] = True
            if st["m"] == "持":
                for s in sorted(book):
                    if s not in q and t1fn(s, book[s]["e"]) == d:
                        q[s] = "Z"
            ban = set()
            if st["m"] == "等":
                i = st["i"]; drop = False
                if d in chk and d > st["c0"]:
                    st["k"] += 1
                    if gone(rkk[d], i):
                        drop = True
                if not drop:
                    if up(i, d, 60):
                        go = i
                    elif d in chk and st["k"] >= 2:
                        drop = True
                if drop:
                    st = {"m": "空", "cash": st["cash"], "val": st["val"]}; ban = {i}
            if go is None and d in chk and st["m"] == "空":
                lst = LAG.ck_cands(rkk[d], CH, ban) if len(rkk[d]["names"]) >= 2 else []
                if lst:
                    i = lst[0]
                    if B == "B0" or up(i, d, 60):
                        go = i
                    else:
                        st = {"m": "等", "i": i, "c0": d, "k": 0, "cash": st["cash"], "val": st["val"]}
            if go is not None:
                names = picks(t, go)
                tob = []
                for s in names:
                    if s in book:
                        if s in q:
                            q.pop(s); book[s]["e"] = t
                        continue
                    tob.append(s)
                st = {"m": "持", "i": go, "start": t, "armed": up(go, d, 240), "cash": st["cash"], "val": st["val"]}
                plan = (tob, len(names))
        for s in sorted(q):
            x = P[s]
            if x["trd"][t] and not x["dn_o"][t] and np.isfinite(x["o"][t]) and x["o"][t] > 0:
                px, kd = x["o"][t], "open"
            elif (not x["trd"][t]) and s in dl and t > dl[s]["last"] and dl[s]["status"].startswith("delisted"):
                px, kd = x["c"][t], "delist"
            else:
                continue
            b = book.pop(s); st["cash"] += b["u"] * px - b["amt"] * COST; q.pop(s); trades.append((t, s, kd, float(px)))
        if plan:
            tob, nn = plan
            for s in tob:
                x = P[s]; o = x["o"][t]
                if not x["trd"][t] or not (np.isfinite(o) and o > 0) or x["up_o"][t]:
                    continue
                amt = min(st["val"] / nn, st["cash"])
                if amt <= 1e-12:
                    break
                st["cash"] -= amt; book[s] = {"u": amt / o, "amt": amt, "e": t}; trades.append((t, s, "buy", float(o)))
        if T is not None and st["m"] == "持" and t == st["start"] + T - 1:
            for s in sorted(book):
                x = P[s]
                if x["trd"][t] and not dnc(C, s)[t] and np.isfinite(x["c"][t]) and x["c"][t] > 0:
                    b = book.pop(s); st["cash"] += b["u"] * x["c"][t] - b["amt"] * COST; q.pop(s, None); trades.append((t, s, "close", float(x["c"][t])))
                else:
                    q.setdefault(s, "T")
            st = {"m": "空", "cash": st["cash"], "val": st["val"]}
        st["val"] = st["cash"] + sum(b["u"] * P[s]["c"][t] for s, b in book.items())
        eq[t] = st["val"]
    return eq, trades


def check(a):
    T00 = time.time()
    META = json.load(open(os.path.join(OUT, "meta.json"), encoding="utf-8"))
    sha, lm = setup(a)
    RES = {"讀法寫死": TIME, "main": sha}; nd = 0
    rng = np.random.default_rng(SEED)
    chosen = META["挑格"]["挑中參數"]; cfg0 = {"B": chosen["B"], "T": None if chosen["T"] == "無上限" else int(chosen["T"])}
    others = [c for c in cells() if ckey(c) != ckey(cfg0)]
    other = others[int(rng.integers(len(others)))]
    RES["抽中格"] = ckey(other)
    from backtest import surge_flow_daily as SFL
    for part in ("main", "early"):
        C = BG[part]; t0, t1 = C["win"]; cal = C["cal"]; cal_s = [str(x.date()) for x in cal]
        res0 = sim_bs(C, t0, t1, cfg0)
        # ── ① replay 起漲點
        buys = sorted({(s, tt) for tt, s, k, _ in res0["trades"] if k == "buy"})
        exits = defaultdict(lambda: t1)
        for tt, s, k, _ in res0["trades"]:
            if k != "buy":
                for (s2, e2) in buys:
                    if s2 == s and e2 < tt and exits[(s2, e2)] == t1:
                        exits[(s2, e2)] = tt
        smp = [buys[int(j)] for j in rng.choice(len(buys), size=min(4 if part == "main" else 2, len(buys)), replace=False)]
        cache = {}; real_ctx = SFL.stock_ctx; real_sig = SFL.signals_for

        def ctx_cached(code, mk, cal_, n_, price_dir, aux_dir, DISP, disp_row):
            if code not in cache:
                cache[code] = real_ctx(code, mk, cal_, n_, price_dir, aux_dir, DISP, disp_row)
            return cache[code]

        def grab(*a_, **k_):
            f = sys._getframe(1); raise _Got(int(f.f_locals["t"]))
        SFL.stock_ctx = ctx_cached; SFL.signals_for = grab
        na = nda = 0; ex = []; err = None
        try:
            for s, e in smp:
                uni = pd.DataFrame({"stock_id": [s], "market": [C["mk"].get(s, "twse")]})
                for d in range(e, min(exits[(s, e)], C["ncal"] - 1) + 1):
                    Rr = {"cal": cal, "W": {"DISP": {}}, "uni": uni, "d0": 0, "d1": d}
                    try:
                        SFL.replay(Rr, s, cal_s[e], 1.0, C["data"], "/nonexistent_aux", names_bj=([], 0, {}))
                        raise RuntimeError("replay 沒走到 signals_for")
                    except _Got as g:
                        tr_ = int(g.args[0])
                    tm = TTT.anchor_pit(C["P"][s]["c"], d, e); na += 1
                    if tr_ != tm:
                        nda += 1; ex.append(f"{s} e{cal_s[e]} d{cal_s[d]}: replay {tr_} 本檔 {tm}")
        except Exception as x_:          # ★ 資料版面讀不到（例：早年版面缺欄）⇒ 照實標「做不到」，不算不同
            err = repr(x_)
        finally:
            SFL.stock_ctx = real_ctx; SFL.signals_for = real_sig; D.DATA = C["data"]
        RES.setdefault("① replay 起漲點", []).append({"段": part, "筆": smp and [f"{s}@{cal_s[e]}" for s, e in smp], "比對日數": na, "不同": nda, "例": ex[:5], "錯誤": err})
        nd += nda
        log(f"[查核 ① {part}] 比對 {na} 日 不同 {nda} {err or ''}")
        # ── ② 真頂第一天
        KS_ = ck_surge(C)
        pairs = sorted(k for k in C["T1"])
        bad2 = 0; ex2 = []
        for s, e in pairs:
            x1 = C["T1"][(s, e)]; x2 = ck_t1(C, KS_, s, e)
            if x1 != x2:
                bad2 += 1; ex2.append((s, cal_s[e], x1 and cal_s[x1], x2 and cal_s[x2]))
        sm = [pairs[int(j)] for j in rng.choice(len(pairs), size=min(30, len(pairs)), replace=False)] if pairs else []
        bad2b = 0; ex2b = []
        SWD, gi, mstar, _ = TTT.surge_world(sorted({s for s, _ in sm}), cal, log); D.DATA = C["data"]
        for s, e in sm:
            hi = min(C["ncal"], t1 + 1)
            if s in SWD:
                _, w2a, w2b, _, _ = TTT.signals_row({"c": C["P"][s]["c"]}, SWD[s], gi, mstar, e, hi)
                f = np.flatnonzero(w2a | w2b); x2 = e + int(f[0]) if len(f) else None
            else:
                x2 = None
            x1 = C["T1"][(s, e)]
            x1 = x1 if (x1 is not None and x1 < hi) else None
            if x1 != x2:
                bad2b += 1; ex2b.append((s, cal_s[e], x1, x2))
        RES.setdefault("② 真頂第一天", []).append({"段": part, "（代號,買進日）": len(pairs), "純 Python 不同": bad2, "例": ex2[:5], "對 TTT.signals_row 抽": len(sm), "不同": bad2b, "例2": ex2b[:5]})
        nd += bad2 + bad2b
        log(f"[查核 ② {part}] {len(pairs)} 對 純 Python 不同 {bad2}｜signals_row 抽 {len(sm)} 不同 {bad2b}")
        # ── ③ 整條
        rkk = {}
        for tc in C["checks"]:
            R_ = LAG.rank_tab(C, "pit", tc, tc)
            rkk[tc] = {"names": list(R_["names"]), "A": {k: list(map(float, v)) for k, v in R_["A"].items()}, "L": {k: list(map(float, v)) for k, v in R_["L"].items()},
                       "pA": {k: list(map(float, v)) for k, v in R_["pA"].items()}, "pL": {k: list(map(float, v)) for k, v in R_["pL"].items()}, "Aall": dict(R_["Aall"])}
        K_ = PRE.ck_load(PRE._C["DATA"])
        pnW = LAG.ck_panel(C["panel"], "W1"); uni_ = set(C["mk"]); mdl = sorted(pnW); rok = {}
        mcd = LAG.ck_mcap(C, cal_s)

        def picks(t, i):
            ym = cal_s[t][:7]; ds = [x for x in mdl if x[:7] == ym]
            if not ds:
                return []
            md = ds[-1]; out = []
            for s in sorted(pnW[md]):
                if s not in uni_ or s not in C["P"]:
                    continue
                if s not in rok:
                    rok[s] = LAG.ck_rowok(C["data"], s)
                if not LAG.ck_pitok(rok[s], md):
                    continue
                if PRE.ck_ind(K_, s, cal_s[t - 1]) != i:
                    continue
                v = mcd[s][t - 1]
                if v == v and v > 0:
                    out.append((-v, s))
            return [s for _, s in sorted(out)][:20]
        t1c = {}

        def t1fn(s, e):
            if (s, e) not in t1c:
                t1c[(s, e)] = ck_t1(C, KS_, s, e)
            return t1c[(s, e)]
        for cfg in (cfg0, other):
            res = sim_bs(C, t0, t1, cfg)
            eq2, tr2 = ck_book(C, cfg, t0, t1, rkk, picks, t1fn)
            rel = float(np.nanmax(np.abs(res["eq"][t0:t1 + 1] / np.asarray(eq2[t0:t1 + 1]) - 1)))
            tr1 = [(t, s, k, float(p)) for t, s, k, p in res["trades"]]
            bt = len(set(tr1) ^ set(tr2))
            ok = rel <= 1e-9 and bt == 0
            nd += 0 if ok else 1
            RES.setdefault("③ 整條重算", []).append({"段": part, "格": ckey(cfg), "交易筆數": len(tr1), "權益最大相對差": rel, "交易不同筆數": bt,
                                                    "例": sorted(set(tr1) ^ set(tr2))[:6], "通過": ok})
            log(f"[查核 ③] {RES['③ 整條重算'][-1]}")
    RES["不同項數"] = nd; RES["通過"] = nd == 0; RES["秒"] = round(time.time() - T00)
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[查核] 不同 {nd}｜通過 {nd == 0}")


def main():
    global LOGF
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=3); ap.add_argument("--reps", type=int, default=1000)
    ap.add_argument("--check", action="store_true"); ap.add_argument("--page", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    LOGF = os.path.join(OUT, "run_check.log" if a.check else ("run_page.log" if a.page else "run.log"))
    open(LOGF, "w").close()
    log(f"===== researchIndRevLagBS {'check' if a.check else ('page' if a.page else 'run')}｜讀法寫死 {TIME}｜GATE_V2 開 =====")
    if a.check:
        check(a)
    elif a.page:
        from backtest import researchIndRevLagBS_page as PG
        PG.page(OUT)
    else:
        run(a)
        from backtest import researchIndRevLagBS_page as PG
        PG.page(OUT)


if __name__ == "__main__":
    main()
