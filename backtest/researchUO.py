# -*- coding: utf-8 -*-
"""Ultimate Oscillator 底背離 seq1【事件層正式跑】（台股策略線 單筆層登錄 sha 5982a1082147efef，2026-10-17 21:09；裁定 seq364「試試看」、
seq365 發號；N_前段 ＋1）——回測線計算子代理。
⛔ 不 commit、不改既有程式與結果夾；researchUO_freq（事件偵測、剔除、UO、轉折）、researchAscTri_freq（世界）、research11 ⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUO [--procs 3]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUO_check
輸出 backtest/resultsUO/（⛔ 不碰 freq/）：UO.json、UO_main.csv（判定表＋分報）、UO_desc.csv（描述格）、by_year.csv、fake_reps.csv、
    events/trades_<世界>_<格>.csv.gz（逐筆進出、對照、X）、run.log

格：A ＝ 判定格（頻率表 A，登錄 §二 ①②③ ＋ 出場）；描述（⛔ 不判、不計 N）：D1（件數）、D2（UO 由 ＜30 回到 ≥30 就買、同出場）、
    D3（A 同進場、固定抱 20／60 日）、假訊號臂（30 次隨機日當 T）；另一讀法（只報）：A_含確認日、A_新低作廢（頻率表 Q5／Q6）、A_出場含T（E3）。

═══ 讀法（E 標；頻率表 Q1～Q11 原樣沿用（母體、壞根、UO、轉折、偵測、剔除、段），以下為正式跑新增；⛔ 在讀任何本件報酬之前寫死；
     ★＝兩種讀法擇一，〔 〕內為另一讀法）═══
 E1 事件 ＝ 逐股呼叫 researchUO_freq.stock_job 原樣；⭐ 依頻率表寫法排成表、與已提交的 resultsUO/freq/events_<世界>.csv.gz 逐列逐欄比
    （格 A、A_含確認日、A_新低作廢、D2），任一不同 ⇒ 中止、⛔ 不算報酬。進場候選 ＝ 狀態「保留」者；進場 ＝ T＋1 開盤（還原開盤）。
 E2 出場（登錄 §二；先到者，收盤判、隔天開盤賣；⛔ 無固定天數）：持有中第 j 根（j ≥ 進場那根，含進場當天收盤）
    ⓐ UO[j] ＞ 70 ⇒ 第 j＋1 根（下一根有效 K 棒）開盤賣；
    ⓑ UO 先 ＞ 50（第 m 根，m ≥ 進場那根）、之後第一個 j ＞ m 的 UO[j] ＜ 45 ⇒ 第 j＋1 根開盤賣（＞50 後第一次 ＜45 必為由 ≥45 跌破）。
    ★ ⓑ 的「先 ＞ 50」從進場當天收盤起算（持有中才算數）〔另一讀法 A_出場含T：T 當天 UO ＞ 50 也算已過 50，只報〕。
    「賣出訊號」措辭照 seq343：UO ＞ 70 稱「過熱賣出訊號」、過 50 後跌破 45 稱「轉弱賣出訊號」；⛔ 不稱最高點、頂部。
 E3 不跨壞根（比照 mktdrop_fwd「壞根前一根收盤強制賣」）：持有中下一根是壞 K 棒（頻率表 Q1／Q3 的 bad：缺口 ≥ 5 日、價格斷點、
    幽靈還原、crashwork、早年 reduce_v2）且它不晚於賣出那根 ⇒ 以壞 K 棒前一根的還原收盤強制出場（含：訊號在第 j 根、第 j＋1 根就是壞 K 棒）。
    ★ 之後再也沒有成交、且最後一根距資料尾 ≥ 5 個交易日（下市／長期停牌）⇒ 以最後一根還原收盤出場（「末根」；PatAll ffill 同義）；
    距資料尾 ＜ 5 日仍未出訊號（或訊號在最後一根、賣出日在資料外）⇒「資料尾未出場」：照實報件數與帳面（最後收盤）報酬，
    ⛔ 不進 X（R 不可算；PatB 的 T＋H 超出資料尾同處理）。賣出那根開盤缺值 ⇒ 改用該根收盤並計數。開盤跌停照賣（不另處理，計數）。
 E4 R ＝ 出場價 ÷ 進場還原開盤 − 1；淨報酬 ＝ R − 0.585%（evaluate.COST，登錄 §三）；X ＝ (R − 0.585%) − 對照平均(R − 0.585%) ＝ R − 對照平均 R。
    持有天數 ＝ 出場日 − 進場日（交易日曆位置差；開盤賣 ⇒ 賣出那天；強制 ⇒ 收盤那天）。
 E5 同一檔持有中不重複進場（登錄 §二）：同檔保留事件依 T 排序，前一筆的賣出日 ＝ S；★ 新事件需 T ≥ S（T＋1 開盤買在賣出日之後；
    T ＜ S 即賣出訊號後、賣出前又出事件 ⇒ 等同沒賣，略過）〔另一讀法：T ＞ S〕；前一筆資料尾未出場 ⇒ 之後全部略過。
    持有限制在整個世界時序上套（段外事件也會擋段內事件）；各格（A、D2、另一讀法）各自套。
 E6 對照（seq364）：同一天 T、同母體 ＝ T 當天 Frame.gate ∧ pit_valid（頻率表 Q1）∧ T＋1 可買（下一根有效 K 棒 ＝ 日曆 T＋1、非壞 K 棒、
    有成交、開盤非缺且 ＞ 0、非開盤鎖漲停 ＝ 頻率表 Q8 同旗標）∧ UO[T] 有值（出場要用該股自己的 UO）∧ R 可算（PatB 對照池「R 可算」同；
    只在資料尾附近有影響）；★ 扣掉事件股自己與 T 當天同格【原始】偵測到的股票（任何狀態；PatB 同）〔另一讀法：只扣自己〕。
    不放回抽 20 檔（不足 ⇒ 全取、計數）⇒ 各自照 E2～E4 出場 ⇒ 等權平均。種子 default_rng([20261017, 格標, T, crc32(sid)])；
    格標 A＝0、A_含確認日＝1、A_新低作廢＝2、D2＝3、A_出場含T＝4、D3_H20＝20、D3_H60＝60；假訊號 ＝ 1000＋r。
    ⛔ 對照不套持有限制（每筆獨立）。
 E7 判定量 X̄；CI ＝ T 所在曆月分群（research11.cl_stats，CR0）、1.96；n_eff ＝ min(可算筆數, 有事件曆月數)；
    n_eff ＜ 30 ⇒ 樣本不足以分辨（依構造不可判定、不計 N）、30～99 ⇒ 句首「樣本中等」、≥ 100 ⇒ 一般；結果② ＝ CI 不含 0 且 X̄ ＞ 0、
    結果③ ＝ X̄ ＜ 0 且 CI 不含 0、結果① ＝ 含 0（登錄 §三）。Bonferroni 族 ＝ 本登錄判定格 N ＝ 1 ⇒ z ＝ 1.96（與 95% 同）。
 E8 ★ 判定段：登錄 §三 寫「探索｜確認｜早年（描述）」、未寫主全窗 ⇒ 照頻率表 Q11：判定在【探索】、【確認】各自報（探索為判定、確認為確認），
    主全窗（2017-03-02～）同法並報【參考】、早年只描述（附 reduce_v2 約 0.3% 註）〔另一讀法：主全窗單一判定窗（PatB P6）〕。
 E9 seq322 門檻（PatB P10 同式＋seq322 原條「逐月中位與平均同號」）＝ 判定段結果② ∧ Bonferroni 下界 ＞ 0 ∧ 假訊號 x ≤ 1
    ∧ X̄ − 0.585% ＞ 0（seq324 做多腿扣成本）∧ 逐月 X 平均之中位數與 X̄ 同號；五條全過才另起組合層登錄（登錄 §六）。探索、確認、主全窗各報。
 E10 假訊號臂（PatB P7 同式）：r ＝ 0…29；每檔每段：n ＝ 該檔 A 可算筆數；可抽日 ＝ 該檔在段內且在 E6 對照池（母體、T＋1 可買、UO 有值、R 可算），
    排除「存在該檔 A 保留事件 T_r ∈ [T−20, T]」的日子；不放回抽 n 天（不足 ⇒ 全取、計數）；⛔ 不套持有限制；對照照 E6（扣自己與 T 當天 A 原始偵測）；
    種子 default_rng([20261018＋r, crc32(sid), 段序號])。x／30 ＝ 落結果② 的次數；結果② 且 x ≥ 2 ⇒ 句首「⚠ 隨機挑日子也有 x／30 次同樣過關。」
 E11 D2 ＝ 頻率表 D2 事件（UO[k−1] ＜ 30 ∧ UO[k] ≥ 30）、同 E2～E6；與判定格的差 ＝ X̄(D2) − X̄(A)，SE ＝ 曆月分群線性化（PatB diff_stats 同式），
    差的 CI 含 0 ⇒ 先驗③ 中。D3 ＝ A 的同一批進場（E5 後），R_H ＝ ffill 還原收盤(T＋H) ÷ 還原開盤(T＋1) − 1；(T＋1, T＋H] 有壞 K 棒或
    T＋H 落在 ≥ 5 日缺口中 ⇒ 不可算（PatB BRK 同式）；對照 ＝ E6 母體 ∧ R_H 可算、同法抽 20 檔。D1 ＝ A 可算筆中 T 為營量／營飆訊號日（同日／20 日內，
    頻率表 Q9 旗標）⇒ 只報件數（n_eff ＜ 30 依構造不可判定）。
 E12 勝率 ＝ 淨報酬 ＞ 0 的比例；平均賺賠比 ＝ 賺錢筆平均淨報酬 ÷ |賠錢筆平均淨報酬|（事件筆；對照同式另欄）。每年事件數 ＝ 可算筆數 ÷ 段長（年）。
 E13 結果句必附：「低點用左右各 5 根、P1 到 P2 ≤ 60 日、突破限 20 日內，三處由本線定」「單筆層通過 ≠ 組合會贏 0050」；
    早年另附「早年含減資假飆股約 0.3%（剩 22 筆未解釋）」＋ 上櫃版面註（PatB NOTE_EARLY 同）。
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
import zlib
from collections import Counter
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchUO_freq as UF                  # noqa: E402  事件偵測、剔除、UO（⛔ 只 import）
from backtest import researchAscTri_freq as AT              # noqa: E402  load_world 原樣
from backtest import research11 as R                        # noqa: E402  load_bars、cl_stats
from backtest import patterns as P                          # noqa: E402  Frame.gate
from backtest import evaluate as E                          # noqa: E402  COST
from backtest import universe_gate as UG                    # noqa: E402

UG.set_gate_v2(True)

REG_SHA = UF.REG_SHA
OUT = "backtest/resultsUO"
FREQ = UF.OUT
UO_HI, UO_ARM, UO_DN = 70.0, 50.0, 45.0
NCTRL = 20
SEED_CTRL, SEED_FAKE = 20261017, 20261018
REPS, EXCL = 30, 20
HD3 = (20, 60)
Z95 = 1.96
N_FAM = 1
COST = E.COST
GAP_END = 5
CELLS = ["A", "A_含確認日", "A_新低作廢", "D2"]
TAG = {"A": 0, "A_含確認日": 1, "A_新低作廢": 2, "D2": 3, "A_出場含T": 4, "D3_H20": 20, "D3_H60": 60}
SEGNUM = {"探索": 0, "確認": 1, "主全窗": 2, "早年": 3}
TYP = {1: "過熱賣出訊號(UO>70)", 2: "轉弱賣出訊號(過50後跌破45)", 3: "壞根前一根收盤強制", 4: "末根收盤(之後無成交)", 5: "資料尾未出場"}
NAME = {"A": "UO 底背離買點（判定格）", "A_含確認日": "另一讀法：突破窗含確認日（只報）", "A_新低作廢": "另一讀法：新低作廢（只報）",
        "A_出場含T": "另一讀法：過50從T算（只報）", "D2": "D2 不要背離：UO 由<30 回到≥30 就買（描述）"}
SENT_SELF = "低點用左右各 5 根、P1 到 P2 ≤ 60 日、突破限 20 日內，三處由本線定"
SENT_ALL = "單筆層通過 ≠ 組合會贏 0050"
NOTE_EARLY = ["早年含減資假飆股約 0.3%（剩 22 筆未解釋）",
              "上櫃 2007-07～12 除權息未還原；上櫃減資 2007～2012 為偵測、非官方；2005-01～2007-06 只有上市"]
LOG: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M:%S")


def pct(x, d=2):
    return "—" if x is None or not np.isfinite(x) else "{:+.{}f}%".format(x * 100, d)


# ═════════════ 出場（E2～E4；向量化，fixture 對逐根迴圈）═════════════
def _nxt(mask, nb, BIG):
    out = np.full(nb + 2, BIG, np.int64)
    pos = np.where(mask, np.arange(nb), BIG)
    if nb:
        out[:nb] = np.minimum.accumulate(pos[::-1])[::-1]
    return out


def sim_exits(U, bad, o, c, idx, n0, arm_prev=False):
    """進場第 s 根（s ＝ 1..nb−1，T ＝ 第 s−1 根）⇒ (eb, px, typ, sell_day, mtm)；長度 nb−1，第 q 個 ＝ s ＝ q＋1。"""
    nb = len(U); BIG = nb + 10
    with np.errstate(invalid="ignore"):
        n70 = _nxt(U > UO_HI, nb, BIG); n50 = _nxt(U > UO_ARM, nb, BIG); n45 = _nxt(U < UO_DN, nb, BIG)
    nbd = _nxt(np.asarray(bad, bool), nb, BIG)
    s = np.arange(1, nb, dtype=np.int64)
    a0 = s - 1 if arm_prev else s
    m = n50[a0]
    s45 = np.where(m < nb, n45[np.minimum(m + 1, nb + 1)], BIG)
    e70 = n70[s]
    sig = np.minimum(e70, s45)
    fb = nbd[np.minimum(s + 1, nb + 1)]
    delisted = bool((n0 - 1 - idx[-1]) >= GAP_END)
    eb = np.full(len(s), -1, np.int64); typ = np.zeros(len(s), np.int8); px = np.full(len(s), np.nan)
    forced = (fb < BIG) & (fb <= sig + 1)
    eb[forced] = fb[forced] - 1; typ[forced] = 3
    sg = ~forced & (sig < nb)
    opn = sg & (sig + 1 < nb)
    eb[opn] = sig[opn] + 1
    typ[opn] = np.where(e70[opn] <= s45[opn], 1, 2)
    last = sg & ~opn                                   # 訊號在最後一根
    nos = ~forced & ~sg                                # 無訊號
    if delisted:
        eb[last] = sig[last]; typ[last] = 4
        eb[nos] = nb - 1; typ[nos] = 4
    else:
        typ[last] = 5; typ[nos] = 5
    okx = eb >= 0
    useo = opn.copy()
    po = np.where(okx, o[np.maximum(eb, 0)], np.nan); pc = np.where(okx, c[np.maximum(eb, 0)], np.nan)
    bado = useo & ~(np.isfinite(po) & (po > 0))
    px = np.where(useo & ~bado, po, pc)
    px[~okx] = np.nan
    sell = np.where(okx, idx[np.maximum(eb, 0)], -1)
    mtm = np.where(typ == 5, c[nb - 1], np.nan)
    return eb, px, typ, sell, mtm, bado


def sim_loop(U, bad, o, c, idx, n0, s, arm_prev=False):
    """逐根迴圈版（fixture／對帳用）：進場第 s 根 ⇒ (eb, px, typ, sell_day)。"""
    nb = len(U)
    armed = bool(arm_prev and U[s - 1] > UO_ARM)
    j = s
    while True:
        if U[j] > UO_HI:
            sig, kind = j, 1
            break
        if armed and U[j] < UO_DN:
            sig, kind = j, 2
            break
        if U[j] > UO_ARM:
            armed = True
        if j + 1 < nb and bad[j + 1]:
            return j, c[j], 3, int(idx[j])
        if j + 1 >= nb:
            if n0 - 1 - idx[-1] >= GAP_END:
                return j, c[j], 4, int(idx[j])
            return -1, np.nan, 5, -1
        j += 1
    if sig + 1 < nb:
        if bad[sig + 1]:
            return sig, c[sig], 3, int(idx[sig])
        p = o[sig + 1] if (np.isfinite(o[sig + 1]) and o[sig + 1] > 0) else c[sig + 1]
        return sig + 1, p, kind, int(idx[sig + 1])
    if n0 - 1 - idx[-1] >= GAP_END:
        return sig, c[sig], 4, int(idx[sig])
    return -1, np.nan, 5, -1


# ═════════════ 統計 ═════════════
def verdict(m, se, n_eff):
    if n_eff < 30:
        return "出口①", "樣本不足以分辨"
    ex = "出口②" if n_eff < 100 else "出口③"
    lo, hi = m - Z95 * se, m + Z95 * se
    if lo <= 0 <= hi:
        return ex, "結果①"
    return ex, ("結果②" if m > 0 else "結果③")


def x_stats(x, key):
    x = np.asarray(x, float); key = np.asarray(key)
    n = len(x)
    if n == 0:
        return {"n": 0, "n_eff": 0, "出口": "出口①", "結果": "樣本不足以分辨"}
    cs = R.cl_stats(x, key)
    m = cs["mean"]; se = cs["se"]; ng = cs["months"]; ne = int(min(n, ng))
    ex, rs = verdict(m, se, ne)
    mm = pd.Series(x).groupby(key).mean()
    return {"n": int(n), "X̄": float(m), "中位": float(np.median(x)), "X勝率": float((x > 0).mean()), "se": float(se),
            "lo": float(m - Z95 * se), "hi": float(m + Z95 * se), "群數": int(ng), "n_eff": ne, "出口": ex, "結果": rs,
            "逐月平均之中位": float(mm.median()), "逐月中位與平均同號": bool(np.sign(mm.median()) == np.sign(m)),
            "X̄−成本": float(m - COST), "bonf_lo": float(m - Z95 * se), "bonf_hi": float(m + Z95 * se)}


def agg_eval(acc):
    nn = acc[:, 0]; S = acc[:, 1]; N = nn.sum()
    if N == 0:
        return None
    m = S.sum() / N
    se = float(np.sqrt(((S - nn * m) ** 2).sum()) / N)
    ne = int(min(N, (nn > 0).sum()))
    ex, rs = verdict(m, se, ne)
    return {"n": int(N), "平均": float(m), "lo": m - Z95 * se, "hi": m + Z95 * se, "n_eff": ne, "出口": ex, "結果": rs}


def diff_stats(x1, k1, x2, k2):
    x1 = np.asarray(x1, float); x2 = np.asarray(x2, float)
    n1, n2 = len(x1), len(x2)
    if n1 == 0 or n2 == 0:
        return {"n_D2": n2, "n_A": n1}
    m1, m2 = x1.mean(), x2.mean()
    a = pd.Series(x1 - m1).groupby(np.asarray(k1)).sum() / n1
    b = pd.Series(x2 - m2).groupby(np.asarray(k2)).sum() / n2
    d = b.sub(a, fill_value=0.0)
    se = float(np.sqrt((d ** 2).sum()))
    df_ = m2 - m1
    return {"n_A": n1, "n_D2": n2, "X̄_A": float(m1), "X̄_D2": float(m2), "差(D2−A)": float(df_), "se": se,
            "lo": float(df_ - Z95 * se), "hi": float(df_ + Z95 * se), "群數": int(len(d)),
            "差的CI含0": bool(df_ - Z95 * se <= 0 <= df_ + Z95 * se)}


def trade_stats(Rn, hold, typ):
    Rn = np.asarray(Rn, float)
    o = {}
    if len(Rn):
        w = Rn[Rn > 0]; l_ = Rn[Rn <= 0]
        o.update(淨報酬平均=float(Rn.mean()), 淨報酬中位=float(np.median(Rn)), 勝率=float((Rn > 0).mean()),
                 平均賺=float(w.mean()) if len(w) else None, 平均賠=float(l_.mean()) if len(l_) else None,
                 平均賺賠比=float(w.mean() / abs(l_.mean())) if len(w) and len(l_) and l_.mean() != 0 else None,
                 平均持有天數=float(np.mean(hold)), 持有天數中位=float(np.median(hold)), 持有天數p90=float(np.percentile(hold, 90)))
        cnt = Counter(np.asarray(typ).tolist())
        for k_, nm in TYP.items():
            if k_ == 5:
                continue
            o[f"出場占比_{nm}"] = float(cnt.get(k_, 0) / len(Rn))
    return o


# ═════════════ 逐股 ═════════════
def stock_job(a):
    wn, sid = a
    sid_, res = UF.stock_job(a)                           # ⭐ 頻率表同一支：事件、剔除狀態
    if res is None:
        return sid, None
    W = UF._G[wn]; cal = W["cal"]; n0 = W["n0"]; i = W["ix"][sid]
    import backtest.data as D
    D.DATA = W["data"]
    B = R.load_bars(sid, W["mk"].get(sid, "twse"), cal)
    df = B["df"]; idx = B["idx"].astype(np.int64); nb = len(idx)
    o, h, l, c = (np.asarray(B[k], float) for k in ("o", "h", "l", "c"))
    bad = np.asarray(B["next_bad"][:nb] == np.arange(nb), bool)
    for p_ in W["BADPOS"].get(sid, ()):
        k = int(np.searchsorted(idx, p_, "left"))
        if k < nb:
            bad[k] = True
    U = UF.uo(h, l, c, bad)
    gate = np.asarray(P.Frame(df, set()).gate, bool)
    PV = np.asarray(W["PV"][i][:n0], bool); TRD = W["TRD"][i]; O = W["O"][i]; UPL = W["UPL"][i]; DNL = W["DNL"][i]
    # 進場可行（日曆 T）
    ent = np.zeros(n0, bool)
    k = np.arange(nb - 1); T = idx[k]; s = k + 1; e = T + 1
    ok = (idx[s] == e) & ~bad[s] & (e < n0)
    e_ = np.minimum(e, n0 - 1)
    with np.errstate(invalid="ignore"):
        ok &= TRD[e_] & np.isfinite(O[e_]) & (np.nan_to_num(O[e_]) > 0) & ~UPL[e_] & np.isfinite(U[k])
        ok &= np.isfinite(o[s]) & (o[s] > 0)
    ent[T[ok]] = True
    out = {"ent": ent, "pop": gate & PV}
    for ver, arm in (("m", False), ("a", True)):
        eb, px, typ, sell, mtm, bado = sim_exits(U, bad, o, c, idx, n0, arm_prev=arm)
        Rr = np.full(n0, np.nan); Hh = np.full(n0, -1, np.int32); Ty = np.zeros(n0, np.int8); Sd = np.full(n0, -1, np.int32)
        Mt = np.full(n0, np.nan); Bo = np.zeros(n0, bool)
        with np.errstate(invalid="ignore", divide="ignore"):
            rr = px / o[s] - 1.0; mm = mtm / o[s] - 1.0
        Tq = T[ok]
        Rr[Tq] = rr[ok]; Ty[Tq] = typ[ok]; Sd[Tq] = sell[ok]
        Hh[Tq] = np.where(sell[ok] >= 0, sell[ok] - e[ok], -1); Mt[Tq] = mm[ok]; Bo[Tq] = bado[ok]
        dnx = np.zeros(n0, bool)
        q = ok & (typ == 1) | ok & (typ == 2)
        dnx[T[q]] = DNL[np.minimum(sell[q], n0 - 1)]
        out.update({f"R{ver}": Rr, f"H{ver}": Hh, f"T{ver}": Ty, f"S{ver}": Sd, f"M{ver}": Mt, f"B{ver}": Bo, f"DN{ver}": dnx})
    # D3：固定抱 H（PatB G／BRK 同式）
    cf = df["close"].to_numpy(float); of = df["open"].to_numpy(float)
    cff = pd.Series(cf).ffill().to_numpy()
    badcal = np.zeros(n0, bool); badcal[idx[bad]] = True
    csb = np.cumsum(badcal).astype(np.int64)
    kH = np.searchsorted(idx, np.arange(n0), "right") - 1
    gap = np.zeros(n0, bool)
    okk = (kH >= 0) & (kH < nb - 1)
    pp = np.arange(n0)[okk]; kk = kH[okk]
    gap[pp] = (idx[kk + 1] - idx[kk] - 1 >= 5) & (pp - idx[kk] >= 5)
    for H in HD3:
        g = np.full(n0, np.nan)
        t = np.arange(n0 - H)
        with np.errstate(invalid="ignore", divide="ignore"):
            g[t] = cff[t + H] / of[t + 1] - 1.0
        brk = np.ones(n0, bool)
        brk[t] = (csb[t + H] - csb[t + 1] > 0) | gap[t + H]
        g[brk] = np.nan
        g[~ent] = np.nan
        out[f"G{H}"] = g
    out["ev"] = res["ev"]
    out["nb"] = nb
    return sid, out


# ═════════════ fixture ═════════════
def selftest():
    msgs = []
    rng = np.random.default_rng(7)
    nchk = 0
    for rep in range(300):
        nb = int(rng.integers(40, 200)); n0 = nb + int(rng.integers(0, 12))
        U = np.clip(50 + np.cumsum(rng.normal(0, 6, nb)), 5, 95)
        bad = rng.random(nb) < 0.03
        o = rng.uniform(10, 20, nb); c = rng.uniform(10, 20, nb)
        o[rng.random(nb) < 0.02] = np.nan
        idx = np.sort(rng.choice(np.arange(n0), nb, replace=False))
        for arm in (False, True):
            eb, px, typ, sell, mtm, bado = sim_exits(U, bad, o, c, idx, n0, arm_prev=arm)
            for s in range(1, nb):
                if bad[s]:
                    continue
                e2, p2, t2, s2 = sim_loop(U, bad, o, c, idx, n0, s, arm_prev=arm)
                q = s - 1
                assert (eb[q], typ[q], sell[q]) == (e2, t2, s2), (rep, arm, s, eb[q], typ[q], sell[q], e2, t2, s2)
                assert (np.isnan(px[q]) and np.isnan(p2)) or px[q] == p2
                nchk += 1
    msgs.append(f"F1 向量化出場 ＝ 逐根迴圈（隨機 UO、壞根、缺開盤、下市／資料尾；{nchk} 筆）")
    x = rng.normal(0, 1, 500); key = rng.integers(0, 40, 500)
    acc = np.zeros((300, 2)); np.add.at(acc[:, 0], key, 1.0); np.add.at(acc[:, 1], key, x)
    a_ = agg_eval(acc); b_ = R.cl_stats(x, key)
    assert abs(a_["平均"] - b_["mean"]) < 1e-12 and abs(a_["lo"] - b_["lo"]) < 1e-12
    msgs.append("F2 假訊號分群彙總式 ＝ research11.cl_stats")
    d = diff_stats(x, key, x, key)
    assert abs(d["差(D2−A)"]) < 1e-15 and d["se"] < 1e-15
    msgs.append("F3 兩組相同 ⇒ 差 0、SE 0")
    for m in msgs:
        log("✅ " + m)
    return msgs


# ═════════════ 對照抽樣 ═════════════
class Sampler:
    def __init__(self, POOL, RAW):
        self.P = POOL; self.RAW = RAW; self.cache = {}

    def draw(self, T, i, seed):
        r = self.cache.get(T)
        if r is None:
            r = np.flatnonzero(self.P[T]); self.cache[T] = r
        keep = r != i
        if self.RAW is not None:
            keep &= ~self.RAW[T, r]
        cand = r[keep]
        if len(cand) == 0:
            return cand
        rng = np.random.default_rng(seed)
        return np.sort(rng.choice(cand, size=min(NCTRL, len(cand)), replace=False))


def freq_frame(EVR, cal):
    allrows = []
    for cell in ("A", "A_含確認日", "A_新低作廢", "D2"):
        rows = sorted([e for r in EVR for e in r[cell]], key=lambda x: (x["T"], x["sid"]))
        if not rows:
            continue
        dfo = pd.DataFrame(rows)
        for col in ("T", "P1", "P2", "conf"):
            if col in dfo:
                dfo[col] = [str(cal[x].date()) for x in dfo[col]]
        dfo.insert(0, "格", cell)
        allrows.append(dfo)
    buf = io.StringIO()
    pd.concat(allrows, ignore_index=True).to_csv(buf, index=False)
    buf.seek(0)
    return pd.read_csv(buf, dtype=str, keep_default_na=False)


def sentence(cell, st, early=False):
    tail = [SENT_SELF, SENT_ALL] + (NOTE_EARLY if early else [])
    rs = st["結果"]
    nm = "UO 底背離買點（照原文出場：過熱或轉弱賣出訊號）" if cell == "A" else NAME.get(cell, cell)
    if rs == "樣本不足以分辨":
        return f"{nm}：樣本不足以分辨（n_eff＝{st.get('n_eff', 0)}）｜" + "；".join(tail)
    pre = "樣本中等（n_eff＝{}，介於 30 與 100 之間）：".format(st["n_eff"]) if st.get("出口") == "出口②" else ""
    if rs == "結果①":
        s = "{}{}比同一天同母體隨機買、照同樣規則賣：測不出（X̄ {}，95% CI {} ～ {}）".format(pre, nm, pct(st["X̄"]), pct(st["lo"]), pct(st["hi"]))
    else:
        x2 = st.get("假訊號_x2", 0) or 0
        warn = "⚠ 隨機挑日子也有 {}／30 次同樣過關。".format(int(x2)) if (rs == "結果②" and x2 >= 2) else ""
        if rs == "結果②":
            s = "{}{}{}比同一天同母體隨機買、照同樣規則賣，每筆多賺 {}".format(warn, pre, nm, pct(abs(st["X̄"]))[1:])
        else:
            s = "{}{}比同一天同母體隨機買、照同樣規則賣，每筆少賺 {}".format(pre, nm, pct(abs(st["X̄"]))[1:])
        s += "（95% CI {} ～ {}）".format(pct(st["lo"]), pct(st["hi"]))
    return s + "｜" + "；".join(tail)


# ═════════════ 主程式 ═════════════
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    t0 = time.time()
    out = OUT if a.limit is None else "/tmp/uo_try"
    os.makedirs(os.path.join(out, "events"), exist_ok=True)
    reg = UF.reg_check()
    log(f"[登錄] {reg}（sha {REG_SHA} 已驗）｜本體開跑 {now_tpe()}")
    fx = selftest()
    J = {"性質": "UO 底背離 seq1 事件層正式跑（單筆層；判定格 A；探索判定、確認確認、主全窗參考、早年描述）",
         "登錄": f"台股策略線 seq1 sha {REG_SHA}", "裁定": "seq364 試試看、seq365 發號；N_前段 ＋1",
         "成本": COST, "種子": {"對照": SEED_CTRL, "假訊號": SEED_FAKE}, "Bonferroni": {"族N": N_FAM, "z": Z95},
         "fixture": fx, "讀法_頻率表": UF.__doc__.split("═══ 讀法")[1], "讀法": __doc__.split("═══ 讀法")[1], "世界": {}, "時點": {"本體開跑": now_tpe()}}
    MAIN = []; DESC = []; BY = []; FK = []
    for wn in ("主", "早年"):
        W = AT.load_world(wn); cal = W["cal"]; n0 = W["n0"]
        win = {}
        for sg, (x_, y_) in UF.SEGS[wn].items():
            p0 = int(cal.searchsorted(pd.Timestamp(x_)))
            p1 = n0 - 2 if y_ is None else min(n0 - 2, int(cal.searchsorted(pd.Timestamp(y_), side="right")) - 1)
            win[sg] = (p0, p1)
        W["win"] = win
        W["SIGPOS"], W["SIGPOS_YF"], cover, nsig = UF.load_sig(wn, cal)
        UF._G[wn] = W
        sids = W["sids"][:a.limit] if a.limit else W["sids"]
        S = len(W["sids"]); ix = W["ix"]
        ENT = np.zeros((n0, S), bool); POP = np.zeros((n0, S), bool)
        M = {k: np.full((n0, S), np.nan) for k in ("Rm", "Ra", "Mm", "Ma", "G20", "G60")}
        Mi = {k: np.full((n0, S), -1, np.int32) for k in ("Hm", "Ha", "Sm", "Sa")}
        Mt = {k: np.zeros((n0, S), np.int8) for k in ("Tm", "Ta")}
        Mb = {k: np.zeros((n0, S), bool) for k in ("Bm", "Ba", "DNm", "DNa")}
        EVS = {}
        with Pool(a.procs) as pool:
            for k_, (sid, r) in enumerate(pool.imap_unordered(stock_job, [(wn, s_) for s_ in sids], chunksize=8)):
                if r is not None:
                    j = ix[sid]
                    ENT[:, j] = r["ent"]; POP[:, j] = r["pop"]
                    for kk in M:
                        M[kk][:, j] = r[kk]
                    for kk in Mi:
                        Mi[kk][:, j] = r[kk]
                    for kk in Mt:
                        Mt[kk][:, j] = r[kk]
                    for kk in Mb:
                        Mb[kk][:, j] = r[kk]
                    EVS[sid] = r["ev"]
                if (k_ + 1) % 400 == 0:
                    log(f"  {wn} … {k_ + 1}／{len(sids)}｜{time.time() - t0:.0f}s")
        log(f"[{wn}] 逐股完 {len(EVS)} 檔｜{time.time() - t0:.0f}s")
        # ── 查核 1：事件 ＝ 已提交頻率表事件檔（逐列逐欄）
        mine = freq_frame(list(EVS.values()), cal)
        ref = pd.read_csv(os.path.join(FREQ, f"events_{wn}.csv.gz"), dtype=str, keep_default_na=False)
        if a.limit:
            ref = ref[ref["sid"].isin(set(sids))].reset_index(drop=True)
        same = list(ref.columns) == list(mine.columns) and ref.shape == mine.shape and (ref.values == mine.values).all()
        if not same:
            raise SystemExit(f"⛔ {wn} 重新偵測 ≠ 已提交頻率表事件檔（{mine.shape} vs {ref.shape}）⇒ 中止（未算任何報酬）")
        log(f"[查核1] {wn}：重新偵測與已提交頻率表事件檔逐列逐欄相同（{len(ref):,} 列）")
        # 保留事件 ⇒ 進場可行（逐筆）
        bad_st = Counter()
        for s_, ev in EVS.items():
            j = ix[s_]
            for cell in CELLS:
                for e in ev[cell]:
                    if e["st"] == "保留" and not (ENT[e["T"], j] and POP[e["T"], j]):
                        bad_st[cell] += 1
        assert not bad_st, f"⛔ 保留事件但本支判不可進場：{bad_st}"
        log("[查核2] 保留事件全部：母體內、T＋1 可買、UO[T] 有值（本支 ENT 矩陣）")
        RAW = {}
        for cell in CELLS:
            Mx = np.zeros((n0, S), bool)
            for s_, ev in EVS.items():
                for e in ev[cell]:
                    Mx[e["T"], ix[s_]] = True
            RAW[cell] = Mx
        BASE = POP & ENT
        POOLm = BASE & np.isfinite(M["Rm"]); POOLa = BASE & np.isfinite(M["Ra"])
        if "第一次讀報酬" not in J["時點"]:
            J["時點"]["第一次讀報酬"] = now_tpe()
        log(f"[對照池] 第一次讀報酬 {J['時點']['第一次讀報酬']}｜每日對照池中位 {int(np.median(POOLm.sum(axis=1)[POOLm.sum(axis=1) > 0]))} 檔｜{time.time() - t0:.0f}s")
        moni = np.asarray(cal.year * 12 + cal.month); years = np.asarray(cal.year); dates = np.array([str(d.date()) for d in cal])
        crc = {s_: zlib.crc32(s_.encode("utf-8")) for s_ in W["sids"]}
        Wj = {"資料": W["data"], "日曆": [str(cal[0].date()), str(cal[-1].date())], "檔數": len(sids), "可用檔數": len(EVS),
              "段": {sg: f"{cal[p].date()}～{cal[q].date()}" for sg, (p, q) in win.items()}, "格": {}}
        SMP = {"m": {c_: Sampler(POOLm, RAW[c_]) for c_ in CELLS}, "a": {"A": Sampler(POOLa, RAW["A"])}}
        SMP3 = {H: Sampler(BASE & np.isfinite(M[f"G{H}"]), RAW["A"]) for H in HD3}
        TR = {}
        runs = [(c_, c_, "m") for c_ in CELLS] + [("A_出場含T", "A", "a")]
        for cname, src, ver in runs:
            Rk, Hk, Tk, Sk, Mk = M[f"R{ver}"], Mi[f"H{ver}"], Mt[f"T{ver}"], Mi[f"S{ver}"], M[f"M{ver}"]
            rows = []; skip = Counter()
            for s_, ev in EVS.items():
                j = ix[s_]; last_sell = -10 ** 9; open_end = False
                for e in sorted([x for x in ev[src] if x["st"] == "保留"], key=lambda x: x["T"]):
                    T = e["T"]
                    if open_end:
                        skip["前筆資料尾未出場"] += 1; continue
                    if T < last_sell:
                        skip["持有中略過"] += 1; continue
                    ty = int(Tk[T, j])
                    rows.append((j, T, e))
                    if ty == 5:
                        open_end = True
                    else:
                        last_sell = int(Sk[T, j])
            rows.sort(key=lambda z: (z[1], W["sids"][z[0]]))
            ii = np.array([z[0] for z in rows], np.int64); TT = np.array([z[1] for z in rows], np.int64)
            Rr = Rk[TT, ii]; ty = Tk[TT, ii]
            smp = SMP[ver][src if ver == "m" else "A"]
            cm = np.full(len(rows), np.nan); cn = np.zeros(len(rows), np.int64); cids = []
            cty = []; chd = []
            for q, (j, T, e) in enumerate(rows):
                sid = W["sids"][j]
                cs = smp.draw(T, j, [SEED_CTRL, TAG[cname], T, crc[sid]])
                cn[q] = len(cs)
                if len(cs):
                    cm[q] = float(Rk[T, cs].mean()); cty.append(Tk[T, cs]); chd.append(Hk[T, cs])
                cids.append(";".join(W["sids"][x] for x in cs) if src == "A" and ver == "m" else "")
            Xv = Rr - cm
            fr = pd.DataFrame({"sid": [W["sids"][x] for x in ii], "market": [W["mk"].get(W["sids"][x], "twse") for x in ii],
                               "T": dates[TT] if len(rows) else [], "進場日": dates[np.minimum(TT + 1, n0 - 1)] if len(rows) else [],
                               "出場日": [dates[x] if x >= 0 else "" for x in Sk[TT, ii]], "出場種類": [TYP[int(x)] for x in ty],
                               "持有天數": Hk[TT, ii], "R": Rr, "R淨": Rr - COST, "帳面R(資料尾)": Mk[TT, ii],
                               "賣出開盤缺用收盤": M_bo(Mb, ver)[TT, ii], "賣出日開盤跌停": Mb[f"DN{ver}"][TT, ii],
                               "對照數": cn, "對照平均R": cm, "X": Xv, "種子格標": TAG[cname], "對照代號": cids})
            if src == "A" and ver == "m":
                fr["D1_同日"] = [bool(z[2]["D1_同日"]) for z in rows]; fr["D1_20日內"] = [bool(z[2]["D1_20日內"]) for z in rows]
                fr["D1_同日_營飆"] = [bool(z[2]["D1_同日_營飆"]) for z in rows]; fr["D1_20日內_營飆"] = [bool(z[2]["D1_20日內_營飆"]) for z in rows]
            TR[cname] = {"fr": fr, "i": ii, "T": TT, "X": Xv, "R": Rr, "ty": ty, "H": Hk[TT, ii], "cm": cm, "skip": dict(skip),
                         "cty": np.concatenate(cty) if cty else np.zeros(0), "chd": np.concatenate(chd) if chd else np.zeros(0)}
            log(f"  [{wn}] {cname}：進場 {len(rows)} 筆（{dict(skip)}）｜資料尾未出場 {int((ty == 5).sum())}｜無對照 {int((cn == 0).sum())}｜{time.time() - t0:.0f}s")
        # D3：同 A 進場、固定抱 H
        A0 = TR["A"]
        for H in HD3:
            g = M[f"G{H}"][A0["T"], A0["i"]]; cm = np.full(len(g), np.nan); cn = np.zeros(len(g), np.int64)
            for q, (j, T) in enumerate(zip(A0["i"], A0["T"])):
                cs = SMP3[H].draw(int(T), int(j), [SEED_CTRL, TAG[f"D3_H{H}"], int(T), crc[W["sids"][j]]])
                cn[q] = len(cs)
                if len(cs):
                    cm[q] = float(M[f"G{H}"][T, cs].mean())
            A0["fr"][f"D3_R{H}"] = g; A0["fr"][f"D3_對照{H}"] = cm; A0["fr"][f"D3_X{H}"] = g - cm; A0["fr"][f"D3_對照數{H}"] = cn
            A0[f"X{H}"] = g - cm
        for cname, d_ in TR.items():
            d_["fr"].to_csv(os.path.join(out, "events", f"trades_{wn}_{cname}.csv.gz"), index=False, compression={"method": "gzip", "compresslevel": 6})
        # ── 各段統計
        for sg, (p0, p1) in win.items():
            yrs = (cal[p1] - cal[p0]).days / 365.25
            segj = {}
            for cname, d_ in TR.items():
                inseg = (d_["T"] >= p0) & (d_["T"] <= p1)
                okx = inseg & np.isfinite(d_["X"])
                st = x_stats(d_["X"][okx], moni[d_["T"][okx]])
                fin = inseg & np.isfinite(d_["R"])
                st.update({"進場筆數(含未出場)": int(inseg.sum()), "資料尾未出場": int((inseg & (d_["ty"] == 5)).sum()),
                           "資料尾未出場_帳面R平均": float(np.nanmean(d_["fr"]["帳面R(資料尾)"].to_numpy()[inseg & (d_["ty"] == 5)])) if (inseg & (d_["ty"] == 5)).any() else None,
                           "無對照剔除": int((fin & ~np.isfinite(d_["X"])).sum()), "相異檔數": int(len(set(d_["i"][okx].tolist()))),
                           "每年事件數": round(int(okx.sum()) / yrs, 2), "R̄": float(d_["R"][okx].mean()) if okx.any() else None,
                           "對照R̄": float(d_["cm"][okx].mean()) if okx.any() else None})
                st.update(trade_stats(d_["R"][okx] - COST, d_["H"][okx], d_["ty"][okx]))
                yr = years[d_["T"][okx]]
                st["逐年"] = {str(y): {"n": int((yr == y).sum()), "X̄": float(d_["X"][okx][yr == y].mean())} for y in sorted(set(yr.tolist()))}
                for y, q in st["逐年"].items():
                    BY.append({"世界": wn, "段": sg, "格": cname, "年": y, **q})
                if cname == "A":
                    # 對照側交易描述（同期間、同抽樣的對照股出場）
                    fr = d_["fr"]
                    st["D1件數"] = {k: int(fr[k].to_numpy()[okx].sum()) for k in ("D1_同日", "D1_20日內", "D1_同日_營飆", "D1_20日內_營飆")}
                    st["D1件數_n_eff"] = {k: int(len(set(moni[d_["T"][okx & fr[k].to_numpy()]].tolist()))) for k in ("D1_同日", "D1_20日內")}
                    for H in HD3:
                        xh = d_[f"X{H}"]; okh = inseg & np.isfinite(xh)
                        q = x_stats(xh[okh], moni[d_["T"][okh]])
                        q.update({"R̄": float(M[f"G{H}"][d_["T"][okh], d_["i"][okh]].mean()) if okh.any() else None})
                        DESC.append({"世界": wn, "段": sg, "格": f"D3_固定抱{H}日", **{k: v for k, v in q.items() if not isinstance(v, dict)}, "身分": "描述（⛔ 不判）"})
                        st[f"D3_H{H}"] = q
                    # 假訊號臂
                    acc = np.zeros((REPS, 300, 2)); cntf = np.zeros((REPS, 3), np.int64)
                    mo0 = moni[p0]
                    tsel = d_["T"][okx]; isel = d_["i"][okx]
                    nper = Counter(isel.tolist())
                    keptA = {}
                    for s_, ev in EVS.items():
                        keptA[ix[s_]] = np.array(sorted(e["T"] for e in ev["A"] if e["st"] == "保留"), np.int64)
                    candc = {}
                    for jj in nper:
                        cand = np.flatnonzero(POOLm[p0:p1 + 1, jj]).astype(np.int64) + p0
                        Tk = keptA.get(jj, np.zeros(0, np.int64))
                        if len(Tk) and len(cand):
                            kq = np.searchsorted(Tk, cand, side="right") - 1
                            prev = np.where(kq >= 0, Tk[np.clip(kq, 0, len(Tk) - 1)], -10 ** 9)
                            cand = cand[~((kq >= 0) & (cand - prev <= EXCL))]
                        candc[jj] = cand
                    smpf = SMP["m"]["A"]
                    for r_ in range(REPS):
                        for jj, nn in nper.items():
                            cand = candc[jj]; mq = min(nn, len(cand)); cntf[r_, 2] += nn - mq
                            if mq == 0:
                                continue
                            sid = W["sids"][jj]
                            rng = np.random.default_rng([SEED_FAKE + r_, crc[sid], SEGNUM[sg]])
                            pick = np.sort(rng.choice(cand, size=mq, replace=False))
                            for T in pick:
                                T = int(T)
                                cs = smpf.draw(T, jj, [SEED_CTRL, 1000 + r_, T, crc[sid]])
                                cntf[r_, 0] += 1
                                if len(cs) == 0:
                                    cntf[r_, 1] += 1; continue
                                xv = M["Rm"][T, jj] - M["Rm"][T, cs].mean()
                                cl = moni[T] - mo0
                                acc[r_, cl, 0] += 1.0; acc[r_, cl, 1] += xv
                    res_ = [agg_eval(acc[r_]) for r_ in range(REPS)]
                    st["假訊號_x2"] = sum(1 for q in res_ if q and q["結果"] == "結果②")
                    st["假訊號_x3"] = sum(1 for q in res_ if q and q["結果"] == "結果③")
                    st["假訊號_平均X"] = float(np.mean([q["平均"] for q in res_ if q])) if any(res_) else None
                    c2 = cntf.sum(axis=0)
                    st["假訊號_帳"] = {"抽出": int(c2[0]), "無對照": int(c2[1]), "可抽日不足": int(c2[2])}
                    for r_, q in enumerate(res_):
                        FK.append({"世界": wn, "段": sg, "r": r_, **({kk: q[kk] for kk in ("n", "平均", "lo", "hi", "n_eff", "出口", "結果")} if q else {"n": 0})})

                    g322 = bool(st["結果"] == "結果②" and st.get("bonf_lo", -1) > 0 and st["假訊號_x2"] <= 1 and st.get("X̄−成本", -1) > 0
                                and st.get("逐月中位與平均同號", False))
                    st["過seq322門檻"] = g322
                if cname == "D2":
                    A_ = TR["A"]; okA = (A_["T"] >= p0) & (A_["T"] <= p1) & np.isfinite(A_["X"])
                    st["D2−A"] = diff_stats(A_["X"][okA], moni[A_["T"][okA]], d_["X"][okx], moni[d_["T"][okx]])
                    st["先驗③(差CI含0)"] = st["D2−A"].get("差的CI含0")
                role = ("判定格｜" + {"探索": "判定段", "確認": "確認段", "主全窗": "參考（另一讀法：主全窗單一判定）", "早年": "早年描述"}[sg]) if cname == "A" \
                    else ("描述（⛔ 不判、不計 N）" if cname == "D2" else "另一讀法（只報）")
                st["身分"] = role
                st["句子"] = sentence(cname, st, early=(wn == "早年"))
                segj[cname] = st
                MAIN.append({"世界": wn, "段": sg, "格": cname, "說明": NAME[cname], "身分": role, "期間": f"{cal[p0].date()}～{cal[p1].date()}",
                             **{k: v for k, v in st.items() if not isinstance(v, dict) and k not in ("身分", "句子")}, "句子": st["句子"]})
                log(f"  [{wn}/{sg}] {cname}：n={st['n']} n_eff={st.get('n_eff')} X̄={pct(st.get('X̄'))} CI {pct(st.get('lo'))}～{pct(st.get('hi'))} {st['結果']}"
                    + (f" 假 x={st.get('假訊號_x2')} seq322={st.get('過seq322門檻')}" if cname == "A" else "")
                    + (f" D2−A {pct(st['D2−A'].get('差(D2−A)'))}（{pct(st['D2−A'].get('lo'))}～{pct(st['D2−A'].get('hi'))}）" if cname == "D2" else "")
                    + f"｜{time.time() - t0:.0f}s")
            Wj["格"][sg] = segj
        Wj["持有限制略過"] = {c_: d_["skip"] for c_, d_ in TR.items()}
        Wj["賣出開盤缺用收盤"] = {c_: int(d_["fr"]["賣出開盤缺用收盤"].sum()) for c_, d_ in TR.items()}
        Wj["賣出日開盤跌停"] = {c_: int(d_["fr"]["賣出日開盤跌停"].sum()) for c_, d_ in TR.items()}
        J["世界"][wn] = Wj
        del ENT, POP, M, Mi, Mt, Mb, RAW, BASE, POOLm, POOLa, SMP, SMP3, TR
    # ── 判定表與先驗
    jd = {}
    for sg in ("探索", "確認", "主全窗"):
        st = J["世界"]["主"]["格"][sg]["A"]
        jd[sg] = {k: st.get(k) for k in ("身分", "結果", "出口", "n", "n_eff", "X̄", "lo", "hi", "中位", "X̄−成本", "逐月平均之中位", "假訊號_x2",
                                         "過seq322門檻", "勝率", "平均賺賠比", "平均持有天數", "句子")}
    J["判定"] = jd
    stE = J["世界"]["主"]["格"]["探索"]
    J["先驗"] = {"①判定格結果①": {"判定段": stE["A"]["結果"], "中": stE["A"]["結果"] == "結果①"},
                "②n_eff≥30": {"判定段 n_eff": stE["A"]["n_eff"], "中": stE["A"]["n_eff"] >= 30},
                "③D2−A差CI含0": {"判定段": stE["D2"]["D2−A"], "中": bool(stE["D2"]["先驗③(差CI含0)"])},
                "各段": {sg: {"①": J["世界"][w]["格"][sg]["A"]["結果"], "②": J["世界"][w]["格"][sg]["A"]["n_eff"],
                             "③差CI含0": J["世界"][w]["格"][sg]["D2"]["先驗③(差CI含0)"]}
                        for w, sgs in (("主", ("探索", "確認", "主全窗")), ("早年", ("早年",))) for sg in sgs}}
    J["N"] = {"本件判定格": 1, "描述格／另一讀法": "不計 N"}
    J["時點"]["完成"] = now_tpe()
    pd.DataFrame(MAIN).to_csv(os.path.join(out, "UO_main.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(DESC).to_csv(os.path.join(out, "UO_desc.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(BY).to_csv(os.path.join(out, "by_year.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(FK).to_csv(os.path.join(out, "fake_reps.csv"), index=False, encoding="utf-8-sig")
    json.dump(J, open(os.path.join(out, "UO.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[判定] {json.dumps({k: {kk: v[kk] for kk in ('結果', 'n_eff', 'X̄', '假訊號_x2', '過seq322門檻')} for k, v in jd.items()}, ensure_ascii=False, default=float)}")
    log(f"[先驗] ①{J['先驗']['①判定格結果①']['中']} ②{J['先驗']['②n_eff≥30']['中']} ③{J['先驗']['③D2−A差CI含0']['中']}")
    log(f"完成 {time.time() - t0:.0f}s")
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


def M_bo(Mb, ver):
    return Mb[f"B{ver}"]


if __name__ == "__main__":
    main()
