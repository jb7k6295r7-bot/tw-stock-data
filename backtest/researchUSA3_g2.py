# -*- coding: utf-8 -*-
"""USREG-A3 g2 組（事件層三件）：A3-5 型態全量 單筆層、A3-13 突破後過濾、A3-16 洗盤還是出貨。回測線計算子代理 g2。

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSA3_g2 --run [--procs 2] [--limit 60] [--only A3-5,A3-13,A3-16]
    ...                                                                                          --check

判準：美股登錄 USREG-A3A4 seq1（sha 0dc16d3267725d7c）＋seq2（sha bc0927fed5996fd4）；裁定 seq318（發號）、seq319（Q1、Q2、Q11）、seq316（兩母體）。
開跑前清單（⛔ 照它、不改）：researchUSA34_prep.py（px_one 的 A3-5／A3-13／A3-16 段落、merge_first、roll_mean）、resultsUSA34/prep/PREP_REPORT.md（P13、P15、P16）、
      清單_29件.csv（N：A3-5 174、A3-13 14、A3-16 9）、退化格清單.csv、A3-5_型態全量_頻率表.csv（判定格清單）。
共用底座：researchUSA3_core.py（C1～C10）。台股原登錄與原程式（判定規則照它移植）：
  A3-5  型態全量_單筆層登錄 seq3（sha b7b4a05af0341797）｜backtest/researchPatAll.py（C1～C12）、patterns_all.py（偵測器，只 import）
  A3-13 突破後過濾 seq4（sha d01e9d830657bb38）｜backtest/researchBF.py（body P1～P9；sha d01e… 沒有被 .py 引用，原程式引的是 seq2 245c89b4d6d49657，判定一字未動）
  A3-16 洗盤還是出貨 seq1（sha bed6ad77174957ec）｜backtest/researchWashDist.py（find_events、conds 只 import）

⛔⛔ 私有資料：resultsUSA34/A3/ 只放彙總（平均、CI、件數、比例、判語、sha）；逐筆事件寫 ~/us_work/a3/g2/（repo 外），json 列 sha。

═══ g2 補讀法（寫死於 2026-10-07 12:25（台北）；寫死前 ⛔ 沒看任何 A3-5／A3-13／A3-16 美股報酬）═══
共同
 G1 三欄 ＝ 事件日 T 當天 m4／m5（prep pack 同；只 S&P 500 欄描述、⛔ 不判）。對照／基準的母體 ＝ 合併母體（PREP「gate3 → 合併母體」），三欄共用同一套對照。
 G2 成本：台股 0.585% 來回 ⇒ 美股 U.COST_ROUNDTRIP 0.05%（seq242）。A3-5 是配對差、兩邊相同相減抵銷 ⇒ 不扣（台股 C1）。
 G3 統計照各台股原程式：A3-5 ＝ researchPatAll.cell_stats（H20 曆月、H60 (T−w0)//60 分群、n_eff ＝ min(n, 群數)）；
    A3-13 ＝ researchBF（(T−w0)//60 分群）；A3-16 ＝ researchWashDist（曆月）；皆 research11.cl_stats（CR0、1.96）。
    core ev_summ（20 日區段 n_eff）不用在這三件（三份台股原登錄各自寫明分群）。
 G4 每格「過」照原登錄：A3-5 ＝ 結果②（照 d 方向；CI 不含 0）；A3-13 ＝「加過濾比較好」（Δ＞0 且 Bonferroni 0.05／14 下界＞0）；
    A3-16 ＝ 該問該 H 探索、確認兩段都過半（W5／W6）。⇒ A3 標籤照 core C4（只400 與合併都過 ＝ 合格；只合併過 ＝ 事後擴母體；合併沒過 ＝ 不合格）。
 G5 件層標籤（多格件）：有任一格合格 ⇒「合格（x 格）」；否則有事後擴母體格 ⇒「事後擴母體（y 格）」；否則「不合格」；格標籤全表另給。
    ⚠ A3-5 合格格能不能單獨講，另看 Bonferroni（0.05／174）與族運氣（假訊號臂），寫在結果句（台股 §七，⛔ 不改標籤）。
 G6 C8 |ret|＞50% 敏感度：S&P 400 未確認列（A2 f50）當硬斷點：A3-5 事件與對照同時換（同一套斷點）；A3-13、A3-16 只剔事件
    （A3-16 基準② 台股原式本來就不剔斷點）；只重判、⛔ 不重跑假訊號臂。
 G7 窗：A3-5、A3-13 原登錄沒有探索／確認 ⇒ 全窗 2016-01-04～2026-09-30 判（T ∈ [w0, w1−H]）；不在 core EARLY_ITEMS ⇒ 不標「缺早年段」。
    A3-16 有兩段 ⇒ 探索 2016-01-04～2021-12-31、確認 2022-01-03～2026-09-30；原登錄「兩段都要過半」照留（兩段美股都有）；
    早年段拿掉 ⇒ 標「缺早年段」。seq319 Q1「兩段取較嚴 ⇒ 只看確認段」說的是確認＋早年段，本件的兩段是探索＋確認 ⇒ 不適用。
A3-5（台股 researchPatAll C1～C12 移植）
 F1 事件、合併、剔除 ＝ prep px_one 原式：PA.detect_all（無影用還原價，P13）、merge_first（先合併再剔除；[first, T＋H] S.brk；T＋1 有效），H ∈ {20, 60, 120}。
 F2 R ＝ ffill 收盤(T＋H) ÷ 開盤(T＋1) − 1（台股 C1）。
 F3 K 對照（台股 C2）：十分位橫斷面 ＝ T 當天在合併母體、有效 K 棒、r10_k 與期間報酬_k 可算（＜10 檔 ⇒ 無十分位）；對照股 ＝ 同兩十分位、同事前門檻、
    T 當天原始偵測沒有該變體、T＋1 有效且開盤＞0、自己 [first_k, T＋H] 無 S.brk、R 可算；扣自己。只配 r10 版並列描述。
 F4 S 對照（台股 C3）：錨點量在 first（r60；S25～S27 用 r20）。★ 錨點日十分位橫斷面 ＝ 面板中當天有效 K 棒且同式可算的全部股票（⛔ 不限當天在指數）：
    first 在 T 前最多約 250 日，限 first 當天在指數會把「之後才進指數」的事件整筆剔掉；台股 gate3 也是固定名單、不是當天名單。
    對照股另要求 T 當天在合併母體；其餘同台股 C3（無事前門檻；用事件同一段 [first, T＋H] 判對照股斷點）。
 F5 未配對描述 ＝ R − 同日 T 合併母體中 R 可算者等權（台股 C5 同式；只描述）。
 F6 判定（台股 C6）：結果②／③／①、出口①②③、勝率、最差；Bonferroni 雙側 α ＝ 0.05／174（美股 N）。三欄同式。
 F7 假訊號臂（台股 C8，30 次、新預設只排除過去 20 日、不排除版並列）：可抽日另要求當天在合併母體（K：十分位母體已含；S：有效∧在母體）；
    每檔抽的筆數 ＝ 該檔合併欄保留真事件數；假事件依抽到那天的 m4／m5 歸欄；種子同台股。每欄各自數 x／30 與每次全族過關格數。
 F8 族結論（台股 §七）每欄一句：N＝174、純運氣 174×2.5%、a（結果②）、b（結果③）、假訊號（新預設）30 次最大值 ⇒ a ≤ 最大 ⇒「與運氣分不開」。
 F9 H120 只描述（合併欄 d×X̄、中位；兩個 H 都依構造不可判定的變體 ⛔ 不讀）。「照名稱方向」讀法、包含關係 6 組、上市／上櫃 ⇒ 不做（只是描述）。
 F10 判定格 ＝ prep A3-5_型態全量_頻率表.csv「可判定(合併≥30)」174 格；本支重算的保留事件數（合併、只400）須與頻率表逐格相同，否則中止、⛔ 不算報酬。
A3-13（台股 researchBF body 移植）
 B1 事件、合併、買法 B～F 的成立日與進場日 ＝ prep px_one 逐行（日曆數；前 5 日曆日均量要全有值；吞噬看日曆前一日；F 窗 ＝ b＋1～T＋20，P15；
    同檔同型 20 日先合併再剔除，P15）。US 窗內 [first, T＋60] 任一天缺 K 棒即剔除 ⇒ 日曆數與 K 棒數在窗內相同。
 B2 每臂 r ＝ 買到：ffill 收盤(T＋60) ÷ 開盤(進場日) − 1 − 0.05%；沒買到 ＝ 0。Δ_e ＝ r(過濾) − r(A)；(T−w0)//60 分群；Bonferroni 0.05／14；結果句照台股 §三。
 B3 進場日開盤無效（缺或 ≤0）⇒ 沒買到（計數）。開跑前核：三型保留事件數與 prep 開跑前算術逐格相同、買到比例相同，否則中止。
 B4 描述：放棄組、E／F 回測分類（台股 P6；F 用 b＋1～T＋20）、H20（終點 T＋20、晚於 ⇒ 0）、H120 子集（T＋120 ≤ 窗尾且 (T＋60, T＋120] 無 S.brk）、
    分年、A 對 ^SP500TR（TR 只有收盤 ⇒ TR(T＋60) ÷ TR(T) − 1，以 T 收盤代 T＋1 開盤；A 用毛報酬）。假訊號臂 ＝ 台股 §五 不適用 ⇒ 不做。
A3-16（台股 researchWashDist 移植）
 W1 事件與四條 ＝ researchWashDist.find_events／conds 原式（prep px_one：有效 K 棒序列、量 ＝ Yahoo 拆股調整量、缺值當 0）。去重版判、不去重版描述。
 W2 事件：T 當天在合併母體且有效；T＋1 有效且開盤＞0；歸段 ＝ T＋1 在段內且 T＋H ≤ 段尾（台股原式）；[P−60, T＋H] S.brk ⇒ 該 H 剔除。
 W3 R ＝ ffill 收盤(T＋H) ÷ 開盤(T＋1) − 1；基準② ＝ T 當天合併母體（有效 K 棒）中 r20（ffill 收盤，20 個日曆位置）與 R 都可算者，≥20 檔才算，
    r20 十分位（整數式）等權（含事件自己，同台股）；X ＝ R − 基準②。
 W4 Q1 ＝ 洗盤 X − 0.05% 的 CI 下緣＞0；Q3 ＝ 出貨 X 的 CI 上緣＜0；Q2 ＝ 兩組平均差、SE ＝ √(SE洗²＋SE出²)、下緣＞0（台股原式）。
 W5 過半：各欄、各段：主版分母 ＝ 足樣本格（該組 ≥30；Q2 兩組都 ≥30），通過 ＞ 分母／2；另報 ≥9／16 全格版；成立 ＝ 探索、確認兩段主版都過半。
 W6 seq319 Q11：只400 欄某問某 H，任一段足樣本格 ＜ 9（湊不到 16 格的過半）⇒ 只400 欄依構造樣本不足 ⇒ 該格最多「事後擴母體」。合併欄照 W5 主版判。
 W7 描述：對全體（同日合併母體等權）、對 ^SP500TR（TR(T＋H) ÷ TR(T＋1) − 1）、混合組、四條逐條 X20 差、事後創前高（T 後 20 根）、
    不去重版 Q1 H20、現實版（(開＋高＋低＋收)÷4、每邊 0.3%）。開跑前核：照 prep 原式重數的事件數須與 prep A3-16_洗盤_事件數.csv 逐格相同，否則中止。
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import os
import pickle
import sys
import time
import zlib
from collections import Counter, defaultdict
import multiprocessing as mp
from statistics import NormalDist

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
from backtest import researchUSA3_core as CO      # noqa: E402
from backtest import researchUSA34_prep as PR     # noqa: E402  ⛔ 只 import（merge_first、roll_mean、偵測器）
PA, PX, RWD = PR.PA, PR.PX, PR.RWD
R11, MB = CO.R11, CO.MB

READ_TS = "2026-10-07 12:25（台北）"
OUT = CO.OUT
WORK = os.path.join(CO.WORK, "g2")
PREP = os.path.expanduser("~/tw-p17/backtest/resultsUSA34/prep")
COST = CO.COST
COLM = ("合併", "只400", "只500")
Z95 = 1.96
# A3-5
HA, HJ, KS = (20, 60, 120), (20, 60), (1, 2, 3, 5)
SEED_FAKE, REPS, EXCL = 20260927, 30, 20
N35 = 174
Z_B35 = NormalDist().inv_cdf(1 - 0.05 / N35 / 2)
ANCHOR20 = ("S25", "S26", "S27")
NCL = 140
# A3-13
H13, BLK13, N13 = 60, 60, 14
Z_B13 = NormalDist().inv_cdf(1 - 0.05 / N13 / 2)
TYPES = ("w", "hs", "box")
TNAME = {"w": "W 底", "hs": "頭肩底", "box": "箱型"}
ARMS = {"w": "BCDEF", "hs": "BCDEF", "box": "BDEF"}
ARM_NAME = {"A": "A 直接買", "B": "B 幅度 3%", "C": "C 站穩 3 天", "D": "D 放量 1.5 倍", "E": "E 等回測＋量縮＋止跌 K", "F": "F 三道全加"}
FNAME = {"B": "幅度 3% 過濾", "C": "站穩 3 天過濾", "D": "放量 1.5 倍過濾", "E": "等回測頸線＋量縮＋止跌 K", "F": "三道全加"}
# A3-16
HS16 = (5, 20, 60)
REG35 = "型態全量_單筆層登錄 台股策略線 seq3（sha b7b4a05af0341797）"
REG13 = "突破後過濾_直接買對加過濾 台股策略線 seq4（sha d01e9d830657bb38）"
REG16 = "洗盤還是出貨_圖卡四條合判 台股策略線 seq1（sha bed6ad77174957ec）"
_ST, _M = {}, {}
W = {}
EVT = {}


# ═════════════ 小工具 ═════════════
def decile_int(v):
    """十分位 0..9（rank(method="first") 後等分 10，整數式；researchPatAll 原式）。"""
    m = len(v)
    order = np.argsort(v, kind="stable")
    rank = np.empty(m, np.int64); rank[order] = np.arange(1, m + 1)
    lab = np.zeros(m, np.int8)
    for j in range(1, 10):
        lab += (10 * (rank - 1) > j * (m - 1)).astype(np.int8)
    return lab


def dec_matrix(M, base, rows):
    out = np.full(M.shape, -1, np.int8)
    for t in rows:
        idx = np.flatnonzero(base[t])
        if len(idx) < 10:
            continue
        out[t, idx] = decile_int(M[t, idx])
    return out


def brk_vec(css, a, H):
    """t ⇒ [a[t], t＋H] 內 css 任一累計有增（＝ MB.Stk.brk 的向量版）；a[t] ＜ 0 或 t＋H 超出 ⇒ True（不可用）。"""
    n = len(a); out = np.ones(n, bool)
    t = np.arange(n - H); b = t + H; aa = a[:n - H]; ok = aa >= 0
    t, b, aa = t[ok], b[ok], aa[ok]
    hit = np.zeros(len(t), bool)
    for cs in css:
        hit |= (cs[b] - np.where(aa > 0, cs[np.maximum(aa - 1, 0)], 0)) > 0
    out[t] = hit
    return out


def cnt(cs, a, b):
    b = min(b, len(cs) - 1)
    if b < a:
        return 0
    return int(cs[b] - (cs[a - 1] if a > 0 else 0))


def excl_past(cand, Tk, excl=EXCL):
    if len(Tk) == 0 or len(cand) == 0:
        return cand
    k = np.searchsorted(Tk, cand, side="right") - 1
    prev = np.where(k >= 0, Tk[np.clip(k, 0, len(Tk) - 1)], -10 ** 9)
    return cand[~((k >= 0) & (cand - prev <= excl))]


def verdict35(m, se, n_eff):
    if n_eff < 30:
        return "出口①", "樣本不足以分辨"
    ex = "出口②" if n_eff < 100 else "出口③"
    lo, hi = m - Z95 * se, m + Z95 * se
    if lo <= 0 <= hi:
        return ex, "結果①"
    return ex, ("結果②" if m > 0 else "結果③")


def agg_eval(acc):
    nn = acc[:, 0]; S = acc[:, 1]; N = nn.sum()
    if N == 0:
        return None
    m = S.sum() / N
    se = float(np.sqrt(((S - nn * m) ** 2).sum()) / N)
    ne = int(min(N, (nn > 0).sum()))
    ex, rs = verdict35(m, se, ne)
    return {"n": int(N), "平均": float(m), "lo": m - Z95 * se, "hi": m + Z95 * se, "n_eff": ne, "出口": ex, "結果": rs}


def clkey(T, H):
    T = np.asarray(T, np.int64)
    return W["MONI"][T] if H != 60 else (T - W["w0"]) // 60


def cell_stats(dx, T, H):
    dx = np.asarray(dx, float); T = np.asarray(T, np.int64)
    n = len(dx)
    if n == 0:
        return {"n": 0, "出口": "出口①", "結果": "樣本不足以分辨"}
    o = {"n": int(n), "dX̄": float(dx.mean()), "中位": float(np.median(dx)), "勝率": float((dx > 0).mean()),
         "最差": float(dx.min()), "p10": float(np.percentile(dx, 10)), "p90": float(np.percentile(dx, 90))}
    if H == 120:
        o["結果"] = "H120描述"
        return o
    cs = R11.cl_stats(dx, clkey(T, H))
    se = cs["se"]; ng = cs["months"]; ne = int(min(n, ng))
    ex, rs = verdict35(o["dX̄"], se, ne)
    m = o["dX̄"]
    o.update(se=se, lo=m - Z95 * se, hi=m + Z95 * se, 群數=int(ng), bonf_lo=m - Z_B35 * se, bonf_hi=m + Z_B35 * se,
             bonf不含0=bool(m - Z_B35 * se > 0 or m + Z_B35 * se < 0), n_eff=ne, 出口=ex, 結果=rs)
    return o


def desc_ci(x, T, H):
    x = np.asarray(x, float); T = np.asarray(T, np.int64); ok = np.isfinite(x); x, T = x[ok], T[ok]
    if len(x) == 0:
        return {"n": 0}
    o = {"n": int(len(x)), "平均": float(x.mean())}
    if H == 120 or len(x) < 2:
        return o
    cs = R11.cl_stats(x, clkey(T, H))
    ne = int(min(len(x), cs["months"]))
    o.update(lo=cs["lo"], hi=cs["hi"], n_eff=ne, 標籤=verdict35(cs["mean"], cs["se"], ne)[1])
    return o


def sha_file(p):
    return CO.sha256f(p)


def rnd(x, k=6):
    if x is None:
        return None
    if isinstance(x, (float, np.floating)):
        return None if not np.isfinite(x) else round(float(x), k)
    return x


def pct(x, d=2):
    return "—" if x is None or not np.isfinite(x) else "{:+.{}f}%".format(x * 100, d)


# ═════════════ pass 1：每檔偵測（fork 共用 _ST；⛔ 不算任何報酬）═════════════
def det_one(sid):
    d = _ST[sid]; cal = _M["cal"]; n = len(cal); w0, w1, sp = _M["w0"], _M["w1"], _M["sp"]; items = _M["items"]
    S = CO.stk(d, w0, w1)
    O, Hh, C, valid, bars, Lw, V = d["O"], d["H"], d["C"], d["valid"], d["bars"], d["L"], d["V"]
    m4, m5, member = d["m4"], d["m5"], d["member"]
    cs50 = np.cumsum(d["f50"]).astype(np.int32)
    ob, hb, lb, cb, vb = O[bars], Hh[bars], Lw[bars], C[bars], V[bars]
    out = {"sid": sid}
    # ── A3-5（prep px_one 原式）
    if "A3-5" in items:
        det = PA.detect_all(ob, hb, lb, cb, np.nan_to_num(vb), ob, hb, lb, cb)
        pat = {}
        for vid, e in det.items():
            Tb = np.asarray(e["T"], np.int64); Fb = np.asarray(e["first"], np.int64)
            Tc = bars[Tb] if len(Tb) else np.zeros(0, np.int64); Fc = bars[Fb] if len(Fb) else np.zeros(0, np.int64)
            info = {int(Tc[q]): (int(Fc[q]), int(e["d"][q]), int(Tb[q] - Fb[q]), float(e["r10"][q]), float(e["prd"][q]),
                                 float(e["r60"][q]), float(e["r20"][q])) for q in range(len(Tc))}
            rr = {"raw": Tc.astype(np.int32)}
            for H in HA:
                kp, acc = PR.merge_first(Tc, Fc, S, H, w0, w1 - H)
                kp = np.asarray(kp, np.int64)
                rr[H] = {"acc": dict(acc), "T": kp.astype(np.int32),
                         "first": np.array([info[t][0] for t in kp], np.int32), "d": np.array([info[t][1] for t in kp], np.int8),
                         "lag": np.array([info[t][2] for t in kp], np.int32),
                         "r10": np.array([info[t][3] for t in kp]), "prd": np.array([info[t][4] for t in kp]),
                         "r60": np.array([info[t][5] for t in kp]), "r20": np.array([info[t][6] for t in kp])}
            pat[vid] = rr
        out["PAT"] = pat
    # ── A3-13（prep px_one 原式；只記成立日與進場日）
    if "A3-13" in items:
        pbdays = set(cal[d["pb"]])
        fd = pd.DataFrame({"open": O, "high": Hh, "low": Lw, "close": C, "volume": np.nan_to_num(V), "traded": valid}, index=cal)
        fr = PX.frame_open(fd, pbdays)
        BRK = {}
        for kind in ("w", "hs"):
            r = PX.detect_turn(kind, cb)
            BRK[kind] = [(int(bars[e["T"]]), int(bars[e["first"]]), float(e["level"])) for e in r["events"]]
        BRK["box"] = [(int(e["T"]), int(e["first"]), float(e["level"])) for e in PX.box_events(fr)]
        rows = []; accs = {}
        for kind, evs in BRK.items():
            lv = {T_: (F_, L_) for T_, F_, L_ in evs}
            kp, acc = PR.merge_first([e[0] for e in evs], [e[1] for e in evs], S, H13, w0, w1 - H13)
            accs[kind] = dict(acc)
            for T_ in kp:
                F_, N_ = lv[T_]
                rows.append(bf_arms(d, S, kind, int(T_), int(F_), N_, n, w0, w1, cs50))
        out["BF"] = rows; out["BF_acc"] = accs
    # ── A3-16
    if "A3-16" in items:
        vb0 = np.nan_to_num(vb)
        ma60b = PR.roll_mean(cb, 60)
        c0 = sp + 1
        rows = []; prepc = Counter(); acc = {}
        for Uu in RWD.US:
            for Dd in RWD.DS:
                for dedup in (True, False):
                    E_, norb, short = RWD.find_events(cb, Uu, Dd, dedup)
                    acc[(Uu, Dd, dedup)] = (len(E_), norb, short)
                    for (P_, j_, L_, T_) in E_:
                        Tc = int(bars[T_])
                        a_ = int(bars[max(P_ - 60, 0)])
                        cds = {}
                        for Pthr in RWD.PS:
                            for sup in RWD.SUPS:
                                cd = RWD.conds(cb, vb0, P_, L_, T_, Pthr, sup, ma60b[T_])
                                nw = sum(x[0] for x in cd.values()); nd = sum(x[1] for x in cd.values())
                                grp = "洗盤" if nw == 4 else ("出貨" if nd >= 3 else "混合")
                                cds[(Pthr, sup)] = (grp, [int(cd[k][0]) - int(cd[k][1]) for k in ("位置", "量能", "走勢", "反彈")])
                        # prep 原式重數（核對用）
                        if dedup and (w0 <= Tc <= w1 - 5) and member[Tc] and valid[Tc] and Tc + 1 < n and valid[Tc + 1]:
                            seg_p = 0 if Tc <= sp else 1
                            for (Pthr, sup), (grp, _) in cds.items():
                                for H in HS16:
                                    if Tc + H > w1 or S.brk(a_, Tc + H):
                                        continue
                                    k_ = (Uu, Dd, Pthr, sup, H, grp, seg_p)
                                    prepc[k_ + ("合併",)] += 1; prepc[k_ + ("只400",)] += int(m4[Tc])
                        # 台股原式（判定用）
                        if not (w0 <= Tc <= w1) or not (member[Tc] and valid[Tc]):
                            continue
                        if Tc + 1 >= n or not valid[Tc + 1] or not (O[Tc + 1] > 0):
                            continue
                        if w0 <= Tc + 1 <= sp:
                            seg, s1 = "探索", sp
                        elif c0 <= Tc + 1 <= w1:
                            seg, s1 = "確認", w1
                        else:
                            continue
                        okH = [bool(Tc + H <= s1 and not S.brk(a_, Tc + H)) for H in HS16]
                        f50H = [bool(Tc + H <= s1 and cnt(cs50, a_, Tc + H) > 0) for H in HS16]
                        newhi = bool(np.any(cb[T_ + 1:T_ + 21] > cb[P_])) if T_ + 1 < len(cb) else False
                        for (Pthr, sup), (grp, cc) in cds.items():
                            rows.append((sid, Uu, Dd, dedup, Pthr, sup, int(bars[P_]), int(bars[L_]), Tc, seg, grp, *cc, newhi,
                                         *okH, *f50H, bool(m4[Tc]), bool(m5[Tc])))
        out["WASH"] = rows; out["WASH_prep"] = dict(prepc); out["WASH_acc"] = acc
    return out


def bf_arms(d, S, kind, T_, F_, N_, n, w0, w1, cs50):
    """prep px_one 的 B～F 逐行（加上沒買到的原因與 E／F 回測分類）；⛔ 不讀報酬。"""
    O, C, Lw, V, valid = d["O"], d["C"], d["L"], d["V"], d["valid"]
    r = {"type": kind, "T": T_, "first": F_, "N": N_, "m4": bool(d["m4"][T_]), "m5": bool(d["m5"][T_]),
         "in120": bool(T_ + 120 <= w1 and not S.brk(T_ + H13 + 1, T_ + 120)), "f50": bool(cnt(cs50, F_, T_ + H13) > 0)}
    ent = {"A": T_ + 1}; why = {"A": ""}
    # B
    bday = -1
    for dd in range(T_, T_ + 5):
        if dd < n and valid[dd] and C[dd] >= N_ * 1.03:
            bday = dd; break
    if bday >= 0 and bday + 1 < n and valid[bday + 1]:
        ent["B"] = bday + 1
    else:
        ent["B"] = None; why["B"] = "5 日內沒有收盤 ≥ 1.03N" if bday < 0 else "進場日不可成交"
    # C
    if kind != "box":
        if T_ + 3 < n and valid[T_:T_ + 3].all() and (C[T_:T_ + 3] > N_).all() and valid[T_ + 3]:
            ent["C"] = T_ + 3
        else:
            ent["C"] = None; why["C"] = "3 天沒有全部收盤 ＞ N"
    # D
    pv = V[T_ - 5:T_]
    dok = bool(np.isfinite(pv).all() and pv.mean() > 0 and np.isfinite(V[T_]) and V[T_] >= 1.5 * pv.mean())
    ent["D"] = T_ + 1 if dok else None
    if not dok:
        why["D"] = "量不到 1.5 倍"

    def e_search(d0, d1):
        for q in range(d0, min(d1, n - 2) + 1):
            if not valid[q]:
                continue
            if C[q] < N_ * 0.97:
                return -1, "跌破頸線"
            if not (Lw[q] <= N_ * 1.02 and C[q] >= N_):
                continue
            pv_ = V[q - 5:q]
            if not (np.isfinite(pv_).all() and np.isfinite(V[q]) and V[q] < pv_.mean()):
                continue
            o_, h_, l_, c_ = O[q], d["H"][q], Lw[q], C[q]
            B_ = abs(c_ - o_); Rg = h_ - l_
            Up = h_ - max(o_, c_); Dn = min(o_, c_) - l_
            ham = Rg > 0 and B_ > 0.1 * Rg and Dn >= 2 * B_ and Up <= 0.1 * Rg
            p_ = q - 1
            eng = (valid[p_] and C[p_] < O[p_] and c_ > o_ and max(o_, c_) >= max(O[p_], C[p_]) and min(o_, c_) <= min(O[p_], C[p_])
                   and B_ > abs(C[p_] - O[p_]))
            if ham or eng:
                return q, ""
        return -1, "窗內沒出現"

    def cls(x, w, d0, d1):
        if x is not None:
            return "買到"
        if w == "進場日不可成交":
            return "條件成立但進場日不可成交"
        if w in ("跌破頸線", "B 或 D 不成立"):
            return w
        for q in range(d0, min(d1, n - 2) + 1):
            if valid[q] and Lw[q] <= N_ * 1.02:
                return "回到頸線但量縮／止跌 K 沒湊齊"
        return "沒回測、直接走掉"
    ed, w_ = e_search(T_ + 1, T_ + 20)
    if ed >= 0 and valid[ed + 1]:
        ent["E"] = ed + 1
    else:
        ent["E"] = None; why["E"] = w_ if ed < 0 else "進場日不可成交"
    r["cls_E"] = cls(ent["E"], why.get("E", ""), T_ + 1, T_ + 20)
    if dok and bday >= 0:
        fdd, w_ = e_search(bday + 1, T_ + 20)
        if fdd >= 0 and valid[fdd + 1]:
            ent["F"] = fdd + 1
        else:
            ent["F"] = None; why["F"] = w_ if fdd < 0 else "進場日不可成交"
        r["cls_F"] = cls(ent["F"], why.get("F", ""), bday + 1, T_ + 20)
    else:
        ent["F"] = None; why["F"] = "B 或 D 不成立"; r["cls_F"] = "B 或 D 不成立"
    r["ent"] = ent; r["why"] = why
    return r


def pass1(sids, procs):
    ctx = mp.get_context("fork")
    res = {}
    t0 = time.time()
    with ctx.Pool(procs) as pool:
        for k, r in enumerate(pool.imap(det_one, sids, chunksize=4)):
            res[r["sid"]] = r
            if (k + 1) % 200 == 0:
                print("[偵測] %d／%d %.0fs" % (k + 1, len(sids), time.time() - t0), flush=True)
    print("[偵測] 完成 %d 檔 %.0fs" % (len(res), time.time() - t0), flush=True)
    return res


# ═════════════ A3-5：矩陣、對照、假訊號 ═════════════
def build_W35(ST, sids, meta, P1):
    cal = meta["cal"]; n = len(cal); w0, w1 = meta["w0"], meta["w1"]; S = len(sids)
    VALID = np.zeros((n, S), bool); MEM = np.zeros((n, S), bool); M4 = np.zeros((n, S), bool); M5 = np.zeros((n, S), bool)
    TRD1 = np.zeros((n, S), bool)
    G = {H: np.full((n, S), np.nan) for H in HA}
    R10 = {k: np.full((n, S), np.nan) for k in KS}; PRD = {k: np.full((n, S), np.nan) for k in KS}
    BRK = {(k, H): np.ones((n, S), bool) for k in KS for H in HA}
    BRK50 = {(k, H): np.ones((n, S), bool) for k in KS for H in HJ}
    A60 = np.full((n, S), np.nan); A20 = np.full((n, S), np.nan)
    CSPB = np.zeros((n, S), np.int32); CSMS = np.zeros((n, S), np.int32); CS50 = np.zeros((n, S), np.int32)
    BARS = []
    for j, s in enumerate(sids):
        d = ST[s]; valid = d["valid"]; O = d["O"]; cff = d["closes"]; bars = d["bars"]; cb = d["C"][bars]; nb = len(bars)
        VALID[:, j] = valid; MEM[:, j] = d["member"]; M4[:, j] = d["m4"]; M5[:, j] = d["m5"]; BARS.append(bars.astype(np.int64))
        okO1 = np.zeros(n, bool); okO1[:-1] = valid[1:] & (np.nan_to_num(O[1:]) > 0)
        TRD1[:, j] = okO1
        with np.errstate(invalid="ignore", divide="ignore"):
            for H in HA:
                G[H][:n - H, j] = np.where(okO1[:n - H], cff[H:] / O[1:n - H + 1] - 1.0, np.nan)
        miss = ~valid.copy(); miss[:bars[0]] = False; miss[bars[-1] + 1:] = False
        cpb = np.cumsum(d["pb"]).astype(np.int32); cms = np.cumsum(miss).astype(np.int32); c50 = np.cumsum(d["f50"]).astype(np.int32)
        CSPB[:, j] = cpb; CSMS[:, j] = cms; CS50[:, j] = c50
        jj_all = np.arange(nb)
        with np.errstate(invalid="ignore", divide="ignore"):
            for k in KS:
                jj = jj_all[jj_all - k - 10 >= 0]
                R10[k][bars[jj], j] = cb[jj - k] / cb[jj - k - 10] - 1.0
                PRD[k][bars[jj], j] = cb[jj] / cb[jj - k] - 1.0
                f = np.full(n, -1, np.int64); jf = jj_all[jj_all - k + 1 >= 0]; f[bars[jf]] = bars[jf - k + 1]
                for H in HA:
                    BRK[(k, H)][:, j] = brk_vec((cpb, cms), f, H)
                for H in HJ:
                    BRK50[(k, H)][:, j] = brk_vec((cpb, cms, c50), f, H)
            jj = jj_all[jj_all >= 61]; A60[bars[jj], j] = cb[jj - 1] / cb[jj - 61] - 1.0
            jj = jj_all[jj_all >= 21]; A20[bars[jj], j] = cb[jj - 1] / cb[jj - 21] - 1.0
    # 逐筆驗：事件的事前量 ＝ 本支矩陣（台股查核同式）
    mism = 0
    for j, s in enumerate(sids):
        for vid, rr in P1[s]["PAT"].items():
            v = PA.VMAP[vid]
            for H in HA:
                e = rr[H]
                if len(e["T"]) == 0:
                    continue
                if v["fam"] == "K":
                    k = v["k"]
                    mism += int(np.sum(R10[k][e["T"], j] != e["r10"])) + int(np.sum(PRD[k][e["T"], j] != e["prd"]))
                else:
                    A = A20 if vid in ANCHOR20 else A60
                    a = A[e["first"], j]; x = e["r20"] if vid in ANCHOR20 else e["r60"]
                    mism += int(np.sum(~((a == x) | (np.isnan(a) & np.isnan(x)))))
    rowsT = range(w0, w1 + 1)
    DECR, DECP, SGN = {}, {}, {}
    for k in KS:
        base = MEM & VALID & np.isfinite(R10[k]) & np.isfinite(PRD[k])
        DECR[k] = dec_matrix(R10[k], base, rowsT); DECP[k] = dec_matrix(PRD[k], base, rowsT)
        SGN[k] = np.sign(np.nan_to_num(R10[k])).astype(np.int8)
    DECA60 = dec_matrix(A60, VALID & np.isfinite(A60), range(0, w1 + 1))
    DECA20 = dec_matrix(A20, VALID & np.isfinite(A20), range(0, w1 + 1))
    EW = {}
    for H in HA:
        Gm = np.where(MEM, G[H], np.nan)
        with np.errstate(invalid="ignore"):
            c_ = np.isfinite(Gm).sum(axis=1); s_ = np.nansum(Gm, axis=1)
        EW[H] = np.where(c_ > 0, s_ / np.maximum(c_, 1), np.nan)
    MONI = np.array([(dd.year - 2016) * 12 + dd.month - 1 for dd in cal]); MONI[MONI < 0] = 0
    W.update(w0=w0, w1=w1, n=n, S=S, VALID=VALID, MEM=MEM, M4=M4, M5=M5, TRD1=TRD1, G=G, DECR=DECR, DECP=DECP, SGN=SGN,
             BRK=BRK, BRK50=BRK50, DECA60=DECA60, DECA20=DECA20, CSPB=CSPB, CSMS=CSMS, CS50=CS50, EW=EW, MONI=MONI,
             BARS=BARS, SIDS=sids, CRC=[zlib.crc32(s.encode("utf-8")) for s in sids], DATES=np.array([str(x.date()) for x in cal]))
    # 原始事件與保留事件
    RAWL = defaultdict(list); keptL = defaultdict(list)
    for j, s in enumerate(sids):
        for vid, rr in P1[s]["PAT"].items():
            if len(rr["raw"]):
                RAWL[vid].append((np.full(len(rr["raw"]), j, np.int32), rr["raw"].astype(np.int64)))
            for H in HA:
                e = rr[H]
                if len(e["T"]):
                    keptL[(vid, H)].append({"i": np.full(len(e["T"]), j, np.int32), "T": e["T"], "first": e["first"], "d": e["d"], "lag": e["lag"]})
    W["RAWL"] = {vid: ((np.concatenate([a for a, _ in RAWL[vid]]), np.concatenate([b for _, b in RAWL[vid]])) if RAWL[vid]
                       else (np.zeros(0, np.int32), np.zeros(0, np.int64))) for vid in PA.VID}
    EVT.clear()
    for key, L in keptL.items():
        EVT[key] = {c_: np.concatenate([e[c_] for e in L]) for c_ in ("i", "T", "first", "d", "lag")}
    return mism


def raw_dense(vid):
    M = np.zeros((W["n"], W["S"]), bool)
    j, t = W["RAWL"][vid]
    M[t, j] = True
    return M


def pre_mask(sg, pre):
    return (sg == 1) if pre == "升" else ((sg == -1) if pre == "降" else (sg != 0))


def k_tables(vid, H, RAWD, brk="BRK"):
    v = PA.VMAP[vid]; k = v["k"]
    r0, r1 = W["w0"], W["w1"] - H
    sl = slice(r0, r1 + 1); nr = r1 - r0 + 1
    DR = W["DECR"][k][sl]; DP = W["DECP"][k][sl]
    base = (DR >= 0) & (DP >= 0) & pre_mask(W["SGN"][k][sl], v["pre"])
    G = W["G"][H][sl]
    pool = base & W["TRD1"][sl] & ~W[brk][(k, H)][sl] & np.isfinite(G) & ~RAWD[sl]
    cell = DR.astype(np.int64) * 10 + DP.astype(np.int64)
    rr = np.arange(nr, dtype=np.int64)[:, None]
    key = (rr * 100 + cell)[pool]; gv = G[pool]
    CS = np.bincount(key, weights=gv, minlength=nr * 100).reshape(nr, 100)
    CC = np.bincount(key, minlength=nr * 100).reshape(nr, 100)
    key10 = (rr * 10 + DR.astype(np.int64))[pool]
    CS10 = np.bincount(key10, weights=gv, minlength=nr * 10).reshape(nr, 10)
    CC10 = np.bincount(key10, minlength=nr * 10).reshape(nr, 10)
    return {"r0": r0, "nr": nr, "k": k, "base": base, "pool": pool, "cell": cell, "DR": DR, "G": G,
            "CS": CS, "CC": CC, "CS10": CS10, "CC10": CC10}


def k_eval(tb, idx, T):
    r = np.asarray(T, np.int64) - tb["r0"]; idx = np.asarray(idx, np.int64)
    g = tb["G"][r, idx]; c = tb["cell"][r, idx]; c10 = tb["DR"][r, idx].astype(np.int64)
    s = tb["pool"][r, idx]
    gs = np.where(s, g, 0.0)
    cc = tb["CC"][r, c] - s; cs = tb["CS"][r, c] - gs
    cc10 = tb["CC10"][r, c10] - s; cs10 = tb["CS10"][r, c10] - gs
    with np.errstate(invalid="ignore", divide="ignore"):
        ctrl = np.where(cc > 0, cs / np.maximum(cc, 1), np.nan)
        ctrl10 = np.where(cc10 > 0, cs10 / np.maximum(cc10, 1), np.nan)
    return g, ctrl, cc, ctrl10, cc10, s


def s_pool(H, RAWD):
    r0, r1 = W["w0"], W["w1"] - H
    sl = slice(r0, r1 + 1)
    G = W["G"][H][sl]
    return {"r0": r0, "pool": W["VALID"][sl] & W["MEM"][sl] & W["TRD1"][sl] & np.isfinite(G) & ~RAWD[sl], "G": G}


def s_one(sp, A, H, i, T, f, use50=False):
    di = A[f, i]
    if di < 0:
        return np.nan, -1
    b = T + H
    nb = np.ones(W["S"], bool)
    for cs in (W["CSPB"], W["CSMS"]) + ((W["CS50"],) if use50 else ()):
        nb &= (cs[b] - (cs[f - 1] if f > 0 else 0)) == 0
    r = T - sp["r0"]
    m = sp["pool"][r] & (A[f] == di) & nb
    m[i] = False
    c_ = int(m.sum())
    return (float(sp["G"][r][m].mean()) if c_ else np.nan), c_


def own_brk(i, f, b, use50=False):
    for cs in (W["CSPB"], W["CSMS"]) + ((W["CS50"],) if use50 else ()):
        if cs[b, i] - (cs[f - 1, i] if f > 0 else 0) > 0:
            return True
    return False


def do_variant(vid):
    t0 = time.time()
    v = PA.VMAP[vid]; isK = v["fam"] == "K"; vnum = PA.VID.index(vid)
    J = W["JUDGE"][vid]
    Hs = [H for H in HJ if J[H]] + ([120] if (J[20] or J[60]) else [])
    out = {"vid": vid, "cells": {}, "sens": {}, "fake": {}, "desc": {}, "acct": {}, "sec": 0.0}
    if not Hs:
        return out
    RAWD = raw_dense(vid)
    A = None if isK else (W["DECA20"] if vid in ANCHOR20 else W["DECA60"])
    frames = []
    for H in Hs:
        E = EVT.get((vid, H))
        if E is None or len(E["i"]) == 0:
            out["cells"][H] = {c: {"n": 0, "結果": "樣本不足以分辨", "出口": "出口①"} for c in COLM}
            continue
        idx = E["i"].astype(np.int64); T = E["T"].astype(np.int64); fst = E["first"].astype(np.int64); d = E["d"].astype(float)
        tb = None
        if isK:
            tb = k_tables(vid, H, RAWD)
            inb = tb["base"][T - tb["r0"], idx]
            assert inb.all(), "⛔ 保留事件不在十分位母體：%s H%d %d 筆" % (vid, H, int((~inb).sum()))
            g, ctrl, cc, ctrl10, cc10, s = k_eval(tb, idx, T)
            assert not s.any(), "⛔ 事件自己在對照池"
            why = np.where(cc > 0, "", "配對格無對照股")
        else:
            sp = s_pool(H, RAWD)
            g = sp["G"][T - sp["r0"], idx]
            ctrl = np.full(len(T), np.nan); cc = np.zeros(len(T), np.int64)
            for q in range(len(T)):
                ctrl[q], cc[q] = s_one(sp, A, H, int(idx[q]), int(T[q]), int(fst[q]))
            ctrl10 = np.full(len(T), np.nan); cc10 = np.full(len(T), -1)
            why = np.where(cc > 0, "", np.where(cc < 0, "錨點量不可算", "配對格無對照股"))
        assert np.isfinite(g).all(), "⛔ 保留事件的 R 不可算 %s H%d" % (vid, H)
        X = g - ctrl; dX = d * X; Xu = g - W["EW"][H][T]
        ok = np.isfinite(X)
        c4 = W["M4"][T, idx]; c5 = W["M5"][T, idx]
        masks = {"合併": np.ones(len(T), bool), "只400": c4, "只500": c5}
        out["acct"][H] = {"保留": int(len(T)), "配對剔除": dict(Counter(why[~ok].tolist())),
                          "保留_只400": int(c4.sum()), "保留_只500": int(c5.sum())}
        cells = {}
        for col, cm in masks.items():
            st = cell_stats(dX[ok & cm], T[ok & cm], H)
            st["保留"] = int(cm.sum()); st["配對剔除數"] = int((~ok & cm).sum())
            cells[col] = st
        out["cells"][H] = cells
        dsc = {"未配對_dXu": desc_ci(d[ok] * Xu[ok], T[ok], H), "R̄": float(g[ok].mean()) if ok.any() else None,
               "對照R̄": float(ctrl[ok].mean()) if ok.any() else None, "對照數_中位": float(np.median(cc[ok])) if ok.any() else None}
        if isK:
            ok10 = np.isfinite(ctrl10)
            dsc["只配r10_dX"] = desc_ci(d[ok10] * (g[ok10] - ctrl10[ok10]), T[ok10], H)
        out["desc"][H] = dsc
        # ── C8 敏感度（f50 當斷點：事件與對照同換）
        if H in HJ:
            e50 = np.array([cnt(W["CS50"][:, int(i)], int(f), int(t) + H) > 0 for i, f, t in zip(idx, fst, T)], bool)
            if isK:
                tb50 = k_tables(vid, H, RAWD, brk="BRK50")
                _, ctrl50, cc50, _, _, _ = k_eval(tb50, idx, T)
            else:
                ctrl50 = np.full(len(T), np.nan)
                for q in range(len(T)):
                    if not e50[q]:
                        ctrl50[q], _ = s_one(sp, A, H, int(idx[q]), int(T[q]), int(fst[q]), use50=True)
            X50 = g - ctrl50; ok50 = np.isfinite(X50) & ~e50
            out["sens"][H] = {col: {k_: rnd(v_) for k_, v_ in cell_stats((d * X50)[ok50 & cm], T[ok50 & cm], H).items()
                                    if k_ in ("n", "dX̄", "lo", "hi", "n_eff", "結果")} for col, cm in masks.items()}
            out["sens"][H]["剔除事件數"] = int(e50.sum())
        frames.append(pd.DataFrame({"sid": np.array(W["SIDS"])[idx], "H": H, "T": W["DATES"][T], "first": W["DATES"][fst], "d": E["d"],
                                    "R": g, "對照平均": ctrl, "對照數": cc, "X": X, "dX": dX, "對照平均_r10": ctrl10, "X_未配對": Xu,
                                    "只400": c4, "只500": c5, "分群": clkey(T, H), "配對": np.where(ok, "有", why)}))
        if H in HJ:
            out["fake"][H] = fake_arm(vid, vnum, H, isK, E, RAWD, tb, A)
    if frames:
        os.makedirs(os.path.join(WORK, "a35_events"), exist_ok=True)
        pd.concat(frames, ignore_index=True).to_csv(os.path.join(WORK, "a35_events", "events_{}.csv.gz".format(vid)), index=False,
                                                    compression={"method": "gzip", "compresslevel": 6, "mtime": 0})
    out["sec"] = time.time() - t0
    return out


def fake_arm(vid, vnum, H, isK, E, RAWD, tb, A):
    w0, w1 = W["w0"], W["w1"]
    v = PA.VMAP[vid]
    r0, r1 = w0, w1 - H
    idx = E["i"].astype(np.int64); T = E["T"].astype(np.int64)
    order = np.lexsort((T, idx))
    idx_s, T_s, lag_s = idx[order], T[order], E["lag"][order].astype(np.int64)
    stocks, starts = np.unique(idx_s, return_index=True)
    ends = np.r_[starts[1:], len(idx_s)]
    sp = None
    if isK:
        CAND = tb["base"]
    else:
        CAND = W["VALID"][r0:r1 + 1] & W["MEM"][r0:r1 + 1]
        sp = s_pool(H, RAWD)
    cands = {int(i): np.flatnonzero(CAND[:, i]) + r0 for i in stocks}
    acc = np.zeros((REPS, 2, 3, NCL, 2)); cnts = np.zeros((REPS, 2, 5), np.int64)
    dfix = v["d"]
    for r in range(REPS):
        for ver in (0, 1):
            fi, fT, fl = [], [], []
            for i, a, b in zip(stocks, starts, ends):
                Tk = T_s[a:b]
                cand = cands[int(i)]
                if ver == 0:
                    cand = excl_past(cand, Tk)
                m = min(len(Tk), len(cand)); cnts[r, ver, 3] += len(Tk) - m
                if m == 0:
                    continue
                rng = np.random.default_rng([SEED_FAKE + r, W["CRC"][int(i)], vnum, H, ver])
                pick = np.sort(rng.choice(cand, size=m, replace=False))
                fi.append(np.full(m, i, np.int64)); fT.append(pick.astype(np.int64)); fl.append(lag_s[a:a + m])
            if not fi:
                continue
            fi = np.concatenate(fi); fT = np.concatenate(fT); fl = np.concatenate(fl)
            cnts[r, ver, 0] += len(fi)
            if isK:
                k = tb["k"]
                own = W["TRD1"][fT, fi] & ~W["BRK"][(k, H)][fT, fi] & np.isfinite(W["G"][H][fT, fi])
                cnts[r, ver, 1] += int((~own).sum())
                fi, fT = fi[own], fT[own]
                g, ctrl, cc, _, _, _ = k_eval(tb, fi, fT)
                okc = cc > 0
                cnts[r, ver, 2] += int((~okc).sum())
                sg = W["SGN"][k][fT, fi].astype(float)
                dd = np.full(len(fi), float(dfix)) if dfix in (1, -1) else (sg if dfix == "續" else -sg)
                dX = (dd * (g - ctrl))[okc]; TT = fT[okc]; FI = fi[okc]
            else:
                dX, TT, FI = [], [], []
                for i, t, lg in zip(fi, fT, fl):
                    bars = W["BARS"][int(i)]
                    bi = int(np.searchsorted(bars, t))
                    if bi - lg < 0:
                        cnts[r, ver, 4] += 1; continue
                    f = int(bars[bi - lg])
                    if not (W["TRD1"][t, i] and np.isfinite(W["G"][H][t, i])) or own_brk(int(i), f, int(t) + H):
                        cnts[r, ver, 1] += 1; continue
                    cm, c_ = s_one(sp, A, H, int(i), int(t), f)
                    if c_ < 0:
                        cnts[r, ver, 4] += 1; continue
                    if c_ == 0:
                        cnts[r, ver, 2] += 1; continue
                    dX.append(float(dfix) * (W["G"][H][t, i] - cm)); TT.append(int(t)); FI.append(int(i))
                dX = np.asarray(dX, float); TT = np.asarray(TT, np.int64); FI = np.asarray(FI, np.int64)
            if len(dX):
                cl = clkey(TT, H)
                for ci, cm_ in enumerate((np.ones(len(TT), bool), W["M4"][TT, FI], W["M5"][TT, FI])):
                    np.add.at(acc[r, ver, ci, :, 0], cl[cm_], 1.0)
                    np.add.at(acc[r, ver, ci, :, 1], cl[cm_], dX[cm_])
    return {"acc": acc, "cnt": cnts}


def run_a35(ST, sids, meta, P1, procs, lim):
    t0 = time.time()
    PT = pd.read_csv(os.path.join(PREP, "A3-5_型態全量_頻率表.csv"), encoding="utf-8-sig")
    JUDGE = {vid: {20: False, 60: False} for vid in PA.VID}
    for r in PT.itertuples(index=False):
        JUDGE[r.變體][int(r.H)] = bool(r._7)
    nJ = sum(J[20] + J[60] for J in JUDGE.values())
    assert nJ == N35, nJ
    # F10：保留事件數 ＝ 頻率表（⛔ 在讀任何報酬之前）
    chk = {}
    if lim is None:
        bad = []
        for r in PT.itertuples(index=False):
            vid, H = r.變體, int(r.H)
            nc = sum(len(P1[s]["PAT"][vid][H]["T"]) for s in sids)
            n4 = sum(int(ST[s]["m4"][P1[s]["PAT"][vid][H]["T"]].sum()) for s in sids)
            if nc != int(r.合併事件) or n4 != int(r.只400事件):
                bad.append((vid, H, nc, int(r.合併事件), n4, int(r.只400事件)))
        chk["保留事件數＝prep頻率表"] = "192／192 格相同" if not bad else bad[:10]
        assert not bad, "⛔ 保留事件數與 prep 頻率表不同 ⇒ 中止（未算報酬）：%s" % bad[:5]
    mism = build_W35(ST, sids, meta, P1)
    assert mism == 0, "⛔ 事件事前量 ≠ 本支矩陣 %d 筆" % mism
    chk["事前量逐位元相同"] = "差 0 筆"
    W["JUDGE"] = JUDGE
    print("[A3-5] 矩陣完成 %.0fs；開始讀報酬（變體迴圈）%s" % (time.time() - t0, time.strftime("%F %T")), flush=True)
    t_first = time.strftime("%F %T")
    order = sorted(PA.VID, key=lambda v_: -sum(len(EVT.get((v_, H), {"i": []})["i"]) for H in HJ))
    RES = {}
    ctx = mp.get_context("fork")
    with ctx.Pool(procs) as pool:
        for r in pool.imap_unordered(do_variant, order, chunksize=1):
            RES[r["vid"]] = r
            print("  [A3-5 %d/96] %s %.0fs（本變體 %.0fs）" % (len(RES), r["vid"], time.time() - t0, r["sec"]), flush=True)
    return summarize_a35(RES, JUDGE, PT, chk, t_first, meta)


def summarize_a35(RES, JUDGE, PT, chk, t_first, meta):
    cells = {}; lab = {}; lab50 = {}
    per_rep = {(c, ver): np.zeros(REPS, int) for c in range(3) for ver in (0, 1)}
    per_rep3 = {c: np.zeros(REPS, int) for c in range(3)}
    fx = {}
    lim400 = {}
    for r in PT.itertuples(index=False):
        lim400[(r.變體, int(r.H))] = not bool(r._8)
    for vid in PA.VID:
        v = PA.VMAP[vid]; R = RES[vid]
        for H in HJ:
            key = "%s_H%d" % (vid, H)
            pr = PT[(PT["變體"] == vid) & (PT["H"] == H)].iloc[0]
            if not JUDGE[vid][H]:
                cells[key] = {"型態": v["name"], "H": H, "身分": "依構造不可判定", "合併n_eff上限": int(pr["合併n_eff"])}
                lab[key] = "不可判定（合併 n_eff 上限 %d ＜ 30）" % int(pr["合併n_eff"])
                continue
            C = R["cells"][H]
            row = {"型態": v["name"], "H": H, "d": v["d"], "身分": "判定格", "只400_n_eff上限＜30（依構造最多事後擴母體）": lim400[(vid, H)]}
            for col in COLM:
                q = C[col]
                row[col] = {k_: rnd(q.get(k_)) for k_ in ("保留", "配對剔除數", "n", "n_eff", "出口", "dX̄", "lo", "hi", "bonf_lo", "bonf_hi",
                                                           "bonf不含0", "中位", "勝率", "p10", "p90", "最差", "結果") if k_ in q}
            fk = R["fake"].get(H) or {"acc": np.zeros((REPS, 2, 3, NCL, 2)), "cnt": np.zeros((REPS, 2, 5), np.int64)}; fx[key] = fk
            for ci, col in enumerate(COLM):
                for ver, vn in ((0, "新預設"), (1, "不排除")):
                    res_ = [agg_eval(fk["acc"][rr, ver, ci]) for rr in range(REPS)]
                    x2 = sum(1 for q in res_ if q and q["結果"] == "結果②")
                    row[col]["假訊號_%s_x2" % vn] = x2
                    for rr, q in enumerate(res_):
                        if q and q["結果"] == "結果②":
                            per_rep[(ci, ver)][rr] += 1
                        if ver == 0 and q and q["結果"] == "結果③":
                            per_rep3[ci][rr] += 1
            c_ = fk["cnt"][:, 0].sum(axis=0)
            row["假訊號帳_新預設"] = {"抽出": int(c_[0]), "剔除": int(c_[1]), "配對格無對照股": int(c_[2]), "可抽日不足": int(c_[3]), "錨點不可算": int(c_[4])}
            row["描述_合併"] = {k_: ({kk: rnd(vv) for kk, vv in v_.items()} if isinstance(v_, dict) else rnd(v_)) for k_, v_ in R["desc"].get(H, {}).items()}
            row["配對剔除_合併"] = R["acct"].get(H, {}).get("配對剔除")
            sens = R["sens"].get(H) or {c_: {"結果": "樣本不足以分辨"} for c_ in COLM}
            row["敏感度_ret50"] = sens
            cells[key] = row
            lab[key] = CO.label_ev(C["合併"]["結果"], C["只400"]["結果"])
            lab50[key] = CO.label_ev(sens["合併"]["結果"], sens["只400"]["結果"])
        if 120 in R["cells"]:
            q = R["cells"][120]["合併"]
            cells["%s_H120" % vid] = {"型態": v["name"], "H": 120, "身分": "H120 描述（⛔ 不判）", "n": q.get("n"), "dX̄": rnd(q.get("dX̄")), "中位": rnd(q.get("中位"))}
    judged = [k for k in lab if not lab[k].startswith("不可判定")]
    fam = {}
    for ci, col in enumerate(COLM):
        a_ = sum(1 for k in judged if cells[k][col]["結果"] == "結果②"); b_ = sum(1 for k in judged if cells[k][col]["結果"] == "結果③")
        M0 = int(per_rep[(ci, 0)].max()); M1 = int(per_rep[(ci, 1)].max())
        fam[col] = {"N": N35, "純運氣": N35 * 0.025, "a_d方向過關": a_, "b_反方向過關": b_,
                    "假訊號_新預設_30次全族過關格數": per_rep[(ci, 0)].tolist(), "假訊號_新預設_最大": M0,
                    "假訊號_不排除_最大": M1, "假訊號_新預設_30次反方向": per_rep3[ci].tolist(), "與運氣分不開": bool(a_ <= M0),
                    "Bonferroni也不含0且結果②格": [k for k in judged if cells[k][col]["結果"] == "結果②" and cells[k][col].get("bonf不含0")],
                    "族結論句": "本族可判定 N＝{} 格，純運氣約 {}×2.5%＝{:.1f} 格會單邊過關；實際 d 方向過關 {} 格、反方向 {} 格（假訊號臂 30 次各自數全族 d 方向過關格數：最大 {} 格）{}".format(
                        N35, N35, N35 * 0.025, a_, b_, M0, "" if a_ > M0 else "，與運氣分不開")}
    cnt_lab = Counter(("合格" if x == "合格" else ("事後擴母體" if x == "事後擴母體" else ("不合格" if x == "不合格" else "不可判定"))) for x in lab.values())
    cnt50 = Counter(lab50.values())
    return {"cells": cells, "lab": lab, "lab50": lab50, "fam": fam, "cnt": dict(cnt_lab), "cnt50": dict(cnt50), "chk": chk, "t_first": t_first}


# ═════════════ A3-13 ═════════════
def run_a313(ST, sids, meta, P1, lim):
    cal = meta["cal"]; w0, w1 = meta["w0"], meta["w1"]
    TR = CO.bench_tr(cal)
    rows = []
    for s in sids:
        for r in P1[s]["BF"]:
            rows.append(dict(r, sid=s))
    # 開跑前核（⛔ 未讀報酬）：事件數、買到比例 ＝ prep 開跑前算術
    chk = {}
    if lim is None:
        BF = pd.read_csv(os.path.join(PREP, "A3-13_突破過濾_開跑前算術.csv"), encoding="utf-8-sig")
        bad = []
        for b in BF.itertuples(index=False):
            typ = {v: k for k, v in TNAME.items()}[b.型]
            sub = [r for r in rows if r["type"] == typ]
            nb = sum(1 for r in sub if r["ent"][b.買法] is not None)
            same = sum(1 for r in sub if r["ent"][b.買法] is not None and r["ent"][b.買法] == r["ent"]["A"])
            okr = len(sub) == int(b.事件) and round(100.0 * nb / len(sub), 1) == float(b._3) and round(100.0 * same / len(sub), 1) == float(b._4)
            if not okr:
                bad.append((b.型, b.買法, len(sub), b.事件, nb, b._3))
        chk["事件數與買到比例＝prep開跑前算術"] = "14／14 格相同" if not bad else bad
        assert not bad, "⛔ A3-13 事件或買到比例與 prep 不同 ⇒ 中止：%s" % bad
    print("[A3-13] 開始讀報酬 %s" % time.strftime("%F %T"), flush=True)
    t_first = time.strftime("%F %T")
    nbad_open = 0
    recs = []
    for r in rows:
        d = ST[r["sid"]]; O, cff = d["O"], d["closes"]; T = r["T"]
        rec = {"sid": r["sid"], "type": r["type"], "T": T, "date": str(cal[T].date()), "year": int(cal[T].year), "blk": int((T - w0) // BLK13),
               "m4": r["m4"], "m5": r["m5"], "in120": r["in120"], "f50": r["f50"], "cls_E": r["cls_E"], "cls_F": r["cls_F"],
               "bench60": float(TR[T + H13] / TR[T] - 1.0)}
        for arm in "A" + ARMS[r["type"]]:
            x = r["ent"].get(arm)
            if x is not None and not (np.isfinite(O[x]) and O[x] > 0):
                nbad_open += 1; x = None
            rec["bought_" + arm] = int(x is not None)
            rec["wait_" + arm] = (x - T) if x is not None else np.nan
            for Hh, nm in ((H13, "r60_"), (20, "r20_"), (120, "r120_")):
                end = T + Hh
                if Hh == 120 and not r["in120"]:
                    rec[nm + arm] = np.nan; continue
                rec[nm + arm] = 0.0 if (x is None or x > end) else float(cff[end] / O[x] - 1.0 - COST)
            rec["late20_" + arm] = int(x is not None and x > T + 20)
        recs.append(rec)
    X = pd.DataFrame(recs)
    os.makedirs(WORK, exist_ok=True)
    pe = os.path.join(WORK, "a313_events.csv.gz")
    X.to_csv(pe, index=False, compression={"method": "gzip", "compresslevel": 6, "mtime": 0})
    chk["進場日開盤無效（記沒買到）"] = nbad_open
    cells = {}; lab = {}; lab50 = {}
    for typ in TYPES:
        for arm in ARMS[typ]:
            key = "%s×%s" % (TNAME[typ], arm)
            row = {"型態": TNAME[typ], "買法": ARM_NAME[arm]}
            res = {}
            for col in COLM:
                Y = X[X["type"] == typ]
                if col == "只400":
                    Y = Y[Y["m4"]]
                elif col == "只500":
                    Y = Y[Y["m5"]]
                row[col] = judge13(Y, arm); res[col] = row[col]["結果類"]
                Y50 = Y[~Y["f50"]]
                row[col]["敏感度_ret50"] = {k_: row_ for k_, row_ in judge13(Y50, arm).items() if k_ in ("事件數", "Δ", "結果類")}
            cells[key] = row
            ok = lambda c: c == "加過濾比較好"
            lab[key] = "合格" if (ok(res["合併"]) and ok(res["只400"])) else ("事後擴母體" if ok(res["合併"]) else "不合格")
            r50 = {c: row[c]["敏感度_ret50"]["結果類"] for c in COLM}
            lab50[key] = "合格" if (ok(r50["合併"]) and ok(r50["只400"])) else ("事後擴母體" if ok(r50["合併"]) else "不合格")
    desc = desc13(X)
    return {"cells": cells, "lab": lab, "lab50": lab50, "desc": desc, "chk": chk, "t_first": t_first, "events_file": pe,
            "acc": {typ: dict(sum((Counter(P1[s]["BF_acc"][typ]) for s in sids), Counter())) for typ in TYPES}}


def judge13(Y, arm):
    if len(Y) == 0:
        return {"事件數": 0, "結果類": "出口①", "結果句": "—（無事件）"}
    dd = (Y["r60_" + arm] - Y["r60_A"]).to_numpy(float)
    cs = R11.cl_stats(dd, Y["blk"].to_numpy())
    n_ = int(len(dd)); blk = int(cs["months"]); n_eff = min(n_, blk)
    ex = "出口①" if n_eff < 30 else ("出口②" if n_eff < 100 else "出口③")
    blo, bhi = cs["mean"] - Z_B13 * cs["se"], cs["mean"] + Z_B13 * cs["se"]
    s, cat = sent13(cs["mean"], cs["lo"], cs["hi"], blo, ex, FNAME[arm])
    return {"事件數": n_, "區段數": blk, "n_eff": n_eff, "出口": ex, "E_A": rnd(float(Y["r60_A"].mean())), "E_過濾": rnd(float(Y["r60_" + arm].mean())),
            "Δ": rnd(cs["mean"]), "CI95_lo": rnd(cs["lo"]), "CI95_hi": rnd(cs["hi"]), "Bonf_lo": rnd(blo), "Bonf_hi": rnd(bhi),
            "Δ中位": rnd(cs["median"]), "買到比例": rnd(float(Y["bought_" + arm].mean())), "結果類": cat, "結果句": s}


def sent13(m, lo, hi, blo, ex, fname):
    if ex == "出口①":
        return "—（出口①：樣本不足以分辨）", "出口①"
    pre = "樣本中等，" if ex == "出口②" else ""
    if lo <= 0 <= hi:
        return pre + "分不出來 ⇒ 直接買（突破隔天開盤）", "分不出來"
    if m > 0 and blo > 0:
        return pre + "突破後加{}再買，比直接買平均好 {:.2f}%（Bonferroni 下界 {:+.2f}%）".format(fname, m * 100, blo * 100), "加過濾比較好"
    if m > 0:
        return pre + "單格過關、與多次嘗試分不開 ⇒ 直接買", "單格過關"
    return pre + "加{}反而比較差：濾掉的比省下的多".format(fname), "加過濾較差"


def desc13(X):
    out = {"放棄組": {}, "A對SP500TR": {}, "回測分類": {}, "H20_H120": {}, "分年_Δ": {}}
    for typ in TYPES:
        Y = X[X["type"] == typ]
        for arm in "A" + ARMS[typ]:
            b = Y["bought_" + arm] == 1
            out["放棄組"]["%s×%s" % (TNAME[typ], arm)] = {
                "事件數": int(len(Y)), "買到比例": rnd(float(b.mean())), "平均等待天數": rnd(float(Y.loc[b, "wait_" + arm].mean())) if b.any() else None,
                "買到那批_平均報酬": rnd(float(Y.loc[b, "r60_" + arm].mean())) if b.any() else None,
                "買到那批_若照A": rnd(float(Y.loc[b, "r60_A"].mean())) if b.any() else None,
                "沒買到那批_若照A": rnd(float(Y.loc[~b, "r60_A"].mean())) if (~b).any() else None}
        x = (Y["r60_A"] + COST - Y["bench60"]).to_numpy(float)
        cs = R11.cl_stats(x, Y["blk"].to_numpy())
        out["A對SP500TR"][TNAME[typ]] = {"事件數": int(len(Y)), "A毛": rnd(float(Y["r60_A"].mean() + COST)), "SP500TR同段": rnd(float(Y["bench60"].mean())),
                                         "A毛−SP500TR": rnd(cs["mean"]), "CI95(描述)": [rnd(cs["lo"]), rnd(cs["hi"])]}
        for arm in ("E", "F"):
            for c_, g in Y.groupby("cls_" + arm):
                out["回測分類"]["%s×%s×%s" % (TNAME[typ], arm, c_)] = {"件數": int(len(g)), "比例": rnd(len(g) / len(Y)),
                                                                     "照A買的平均報酬": rnd(float(g["r60_A"].mean())), "該臂平均報酬": rnd(float(g["r60_" + arm].mean()))}
        Y120 = Y[Y["in120"]]
        for arm in ARMS[typ]:
            d20 = Y["r20_" + arm] - Y["r20_A"]; d120 = Y120["r120_" + arm] - Y120["r120_A"]
            out["H20_H120"]["%s×%s" % (TNAME[typ], arm)] = {"H20_Δ": rnd(float(d20.mean())), "H20_進場晚於T+20": int(Y["late20_" + arm].sum()),
                                                            "H120_事件數": int(len(Y120)), "H120_Δ": rnd(float(d120.mean())) if len(Y120) else None}
            out["分年_Δ"]["%s×%s" % (TNAME[typ], arm)] = {str(y): rnd(float((g["r60_" + arm] - g["r60_A"]).mean())) for y, g in Y.groupby("year")}
    return out


# ═════════════ A3-16 ═════════════
def run_a316(ST, sids, meta, P1, lim):
    cal = meta["cal"]; n = len(cal); w0, w1, sp = meta["w0"], meta["w1"], meta["sp"]
    chk = {}
    # 開跑前核：照 prep 原式重數 ＝ prep A3-16_洗盤_事件數.csv（⛔ 未讀報酬）
    if lim is None:
        PC = Counter()
        for s in sids:
            PC.update(P1[s]["WASH_prep"])
        WT = pd.read_csv(os.path.join(PREP, "A3-16_洗盤_事件數.csv"), encoding="utf-8-sig")
        bad = 0; tot = 0
        for r in WT.itertuples(index=False):
            for g in ("洗盤", "出貨", "混合"):
                for seg, sn in ((0, "探索"), (1, "確認")):
                    for col in ("合併", "只400"):
                        tot += 1
                        mine = PC.get((r.U, r.D, r.P, r.支撐, int(r.H), g, seg, col), 0)
                        if mine != int(getattr(r, "%s_%s_%s" % (g, sn, col))):
                            bad += 1
        chk["prep原式事件數＝prep事件數表"] = "%d／%d 格相同" % (tot - bad, tot)
        assert bad == 0, "⛔ A3-16 事件數與 prep 不同 %d 格 ⇒ 中止" % bad
    cols = ["sid", "U", "D", "去重", "P", "支撐", "Pc", "Lc", "T", "段", "組", "位置", "量能", "走勢", "反彈", "事後創前高",
            "ok5", "ok20", "ok60", "f505", "f5020", "f5060", "m4", "m5"]
    E = pd.DataFrame([x for s in sids for x in P1[s]["WASH"]], columns=cols)
    print("[A3-16] 事件列 %d；開始讀報酬 %s" % (len(E), time.strftime("%F %T")), flush=True)
    t_first = time.strftime("%F %T")
    S = len(sids); ix = {s: i for i, s in enumerate(sids)}
    CZ = np.column_stack([ST[s]["closes"] for s in sids]); O = np.column_stack([ST[s]["O"] for s in sids])
    VAL = np.column_stack([ST[s]["valid"] for s in sids]); MEM = np.column_stack([ST[s]["member"] for s in sids])
    AVG = np.column_stack([(ST[s]["O"] + ST[s]["H"] + ST[s]["L"] + ST[s]["C"]) / 4.0 for s in sids])
    EL = MEM & VAL
    OK1 = np.zeros((n, S), bool); OK1[:-1] = VAL[1:] & (np.nan_to_num(O[1:]) > 0)
    with np.errstate(invalid="ignore", divide="ignore"):
        r20 = np.full((n, S), np.nan); r20[20:] = CZ[20:] / CZ[:-20] - 1.0
    TR = CO.bench_tr(cal)
    BL = {}
    for H in HS16:
        Rh = np.full((n, S), np.nan)
        with np.errstate(invalid="ignore", divide="ignore"):
            Rh[:n - H] = np.where(OK1[:n - H], CZ[H:n] / O[1:n - H + 1] - 1.0, np.nan)
        base = np.full((n, S), np.nan); ew = np.full(n, np.nan)
        for t in range(w0, min(w1, n - H - 1) + 1):
            m = EL[t] & np.isfinite(r20[t]) & np.isfinite(Rh[t])
            if m.sum() < 20:
                continue
            x = r20[t, m]; dec = decile_int(x); rr = Rh[t, m]
            mu = np.array([rr[dec == q].mean() for q in range(10)])
            bt = np.full(S, np.nan); bt[np.flatnonzero(m)] = mu[dec]; base[t] = bt
            ew[t] = float(rr.mean())
        BL[H] = (Rh, base, ew)
    j = E["sid"].map(ix).to_numpy(); T = E["T"].to_numpy(int)
    E["月"] = [str(cal[t])[:7] for t in T]
    for H in HS16:
        Rh, base, ew = BL[H]
        ok = E["ok%d" % H].to_numpy(bool)
        Tc = np.minimum(T + H, n - 1)
        R = np.where(ok, Rh[T, j], np.nan)
        E["R%d" % H] = R
        E["X%d" % H] = R - np.where(ok, base[T, j], np.nan)
        E["vsEW%d" % H] = R - ew[T]
        E["vsTR%d" % H] = R - (TR[Tc] / TR[np.minimum(T + 1, n - 1)] - 1.0)
        with np.errstate(invalid="ignore", divide="ignore"):
            E["Xreal%d" % H] = np.where(ok, AVG[Tc, j] / AVG[np.minimum(T + 1, n - 1), j] - 1.0 - 2 * 0.003, np.nan) - np.where(ok, base[T, j], np.nan)
    nmiss = int((E["ok20"] & ~np.isfinite(E["X20"])).sum())
    chk["保留但基準②不可算（X 缺）"] = nmiss
    os.makedirs(WORK, exist_ok=True)
    pe = os.path.join(WORK, "a316_events.csv.gz")
    E.to_csv(pe, index=False, float_format="%.6g", compression={"method": "gzip", "compresslevel": 6, "mtime": 0})
    K = E[E["去重"]]
    res = judge16(K, False)
    res50 = judge16(K, True)
    # 描述（合併欄）
    dsc = {}
    for seg in ("探索", "確認"):
        k_ = K[K["段"] == seg]
        dsc[seg] = {"各組事件數（16 格合計，主列）": k_["組"].value_counts().to_dict(),
                    "逐條 像洗盤−像出貨 X20 差（16 格合計）": {c_: rnd(float(k_.loc[k_[c_] == 1, "X20"].mean() - k_.loc[k_[c_] == -1, "X20"].mean())) for c_ in ("位置", "量能", "走勢", "反彈")},
                    "事後創前高比例": {g: rnd(float(k_.loc[k_["組"] == g, "事後創前高"].mean())) if (k_["組"] == g).any() else None for g in ("洗盤", "出貨", "混合")},
                    "對全體_X20平均": {g: rnd(float(k_.loc[k_["組"] == g, "vsEW20"].mean())) for g in ("洗盤", "出貨", "混合") if (k_["組"] == g).any()},
                    "對SP500TR_X20平均": {g: rnd(float(k_.loc[k_["組"] == g, "vsTR20"].mean())) for g in ("洗盤", "出貨", "混合") if (k_["組"] == g).any()},
                    "現實版_X20平均": {g: rnd(float(k_.loc[k_["組"] == g, "Xreal20"].mean())) for g in ("洗盤", "出貨", "混合") if (k_["組"] == g).any()},
                    "混合組_X20平均": rnd(float(k_.loc[k_["組"] == "混合", "X20"].mean())) if (k_["組"] == "混合").any() else None}
        nd = E[(E["段"] == seg) & ~E["去重"]]
        dsc[seg]["不去重版 Q1 H20 洗盤 X−成本 平均"] = rnd(float(nd.loc[nd["組"] == "洗盤", "X20"].mean() - COST)) if (nd["組"] == "洗盤").any() else None
    acc = Counter()
    for s in sids:
        for k_, v_ in P1[s]["WASH_acc"].items():
            a0 = acc.get(k_, (0, 0, 0)); acc[k_] = (a0[0] + v_[0], a0[1] + v_[1], a0[2] + v_[2])
    dsc["30日內沒反彈比例（全史、去重）"] = {"U%.0f%%_D%.0f%%" % (k_[0] * 100, k_[1] * 100): rnd(v_[1] / max(1, v_[0] + v_[1]), 4) for k_, v_ in acc.items() if k_[2]}
    return {**res, "sens": res50, "desc": dsc, "chk": chk, "t_first": t_first, "events_file": pe}


def judge16(K, drop50):
    rows = []
    for seg in ("探索", "確認"):
        for U_ in RWD.US:
            for D_ in RWD.DS:
                for P_ in RWD.PS:
                    for sup in RWD.SUPS:
                        g0 = K[(K["段"] == seg) & (K["U"] == U_) & (K["D"] == D_) & (K["P"] == P_) & (K["支撐"] == sup)]
                        for H in HS16:
                            gH = g0[g0["ok%d" % H]]
                            if drop50:
                                gH = gH[~gH["f50%d" % H]]
                            for col in COLM:
                                g = gH if col == "合併" else (gH[gH["m4"]] if col == "只400" else gH[gH["m5"]])
                                w = g[g["組"] == "洗盤"]; d = g[g["組"] == "出貨"]
                                sw = R11.cl_stats(w["X%d" % H].to_numpy(float) - COST, w["月"].to_numpy()) if len(w) else {"n": 0}
                                sd = R11.cl_stats(d["X%d" % H].to_numpy(float), d["月"].to_numpy()) if len(d) else {"n": 0}
                                r = {"段": seg, "U": U_, "D": D_, "P": P_, "支撐": sup, "H": H, "欄": col,
                                     "洗盤_n": sw["n"], "洗盤_X−成本": sw.get("mean"), "洗盤_lo": sw.get("lo"), "洗盤_hi": sw.get("hi"),
                                     "出貨_n": sd["n"], "出貨_X": sd.get("mean"), "出貨_lo": sd.get("lo"), "出貨_hi": sd.get("hi")}
                                r["Q1過"] = bool(sw["n"] and sw["lo"] > 0); r["Q3過"] = bool(sd["n"] and sd["hi"] < 0)
                                if sw["n"] and sd["n"]:
                                    diff = (sw["mean"] + COST) - sd["mean"]; se = math.sqrt(sw["se"] ** 2 + sd["se"] ** 2)
                                    r.update({"Q2_差": diff, "Q2_lo": diff - 1.96 * se, "Q2_hi": diff + 1.96 * se}); r["Q2過"] = bool(diff - 1.96 * se > 0)
                                else:
                                    r["Q2過"] = False
                                rows.append(r)
    C = pd.DataFrame(rows)
    J = {}; lab = {}
    for H in HS16:
        for q, need in (("Q1", "洗盤"), ("Q2", "both"), ("Q3", "出貨")):
            key = "%s_H%d" % (q, H); J[key] = {}
            for col in COLM:
                per = {}
                for seg in ("探索", "確認"):
                    x = C[(C["段"] == seg) & (C["H"] == H) & (C["欄"] == col)]
                    suff = (x["洗盤_n"] >= 30) & (x["出貨_n"] >= 30) if need == "both" else (x["%s_n" % need] >= 30)
                    npass = int(x["%s過" % q].sum()); npass_s = int((x["%s過" % q] & suff).sum()); nsuff = int(suff.sum())
                    per[seg] = {"通過格（全）": npass, "足樣本格": nsuff, "足樣本中通過": npass_s,
                                "主版過半": bool(nsuff > 0 and npass_s > nsuff / 2), "全格版≥9／16": bool(npass >= 9)}
                main_ok = per["探索"]["主版過半"] and per["確認"]["主版過半"]
                alt_ok = per["探索"]["全格版≥9／16"] and per["確認"]["全格版≥9／16"]
                insuff = min(per["探索"]["足樣本格"], per["確認"]["足樣本格"]) < 9
                J[key][col] = {**per, "成立（主版）": main_ok, "成立（全格版≥9／16）": alt_ok, "足樣本格＜9（Q11 樣本不足）": insuff}
            ok_c = J[key]["合併"]["成立（主版）"]
            ok_4 = J[key]["只400"]["成立（主版）"] and not J[key]["只400"]["足樣本格＜9（Q11 樣本不足）"]
            lab[key] = "合格" if (ok_c and ok_4) else ("事後擴母體" if ok_c else "不合格")
            if J[key]["只400"]["足樣本格＜9（Q11 樣本不足）"]:
                J[key]["註"] = "只400 欄足樣本格 ＜9 ⇒ 依構造最多事後擴母體（seq319 Q11）"
    # 每問每 H 的平均（合併欄，跨 16 格事件合計；描述）
    return {"判定": J, "lab": lab, "cells_n": int(len(C)), "cells_tab": C}


# ═════════════ 結果檔 ═════════════
def items_label(lab):
    c = Counter(v if v in ("合格", "事後擴母體", "不合格") else "不可判定" for v in lab.values())
    if c.get("合格"):
        top = "合格（%d 格）" % c["合格"]
    elif c.get("事後擴母體"):
        top = "事後擴母體（%d 格）" % c["事後擴母體"]
    else:
        top = "不合格"
    return top, dict(c)


def warn_fake(cell):
    """台股 §八：結果② 且假訊號 x ≥ 2 ⇒ 句前加「隨機挑日子也有 x／30 次同樣過關」（兩欄各報）。"""
    w = ["%s %d／30" % (col, cell[col].get("假訊號_新預設_x2", 0)) for col in ("合併", "只400")
         if cell[col].get("結果") == "結果②" and cell[col].get("假訊號_新預設_x2", 0) >= 2]
    bz = all(cell[col].get("bonf不含0") for col in ("合併", "只400"))
    tail = "Bonferroni 兩欄都不含 0 ⇒ 可單獨引用" if bz else "Bonferroni 下界含 0 ⇒ 單格過關、全族與運氣分不開，⛔ 不單獨引用"
    return "（%s%s）" % ("⚠ 隨機挑日子也同樣過關：%s；" % "、".join(w) if w else "", tail)


def write_a35(R, meta, cov):
    lab = R["lab"]; top, c = items_label(lab)
    fam = R["fam"]
    judged = [k for k in lab if not lab[k].startswith("不可判定")]
    ok_cells = [k for k in judged if lab[k] == "合格"]
    exp_cells = [k for k in judged if lab[k] == "事後擴母體"]
    bonf_ok = [k for k in ok_cells if R["cells"][k]["合併"].get("bonf不含0") and R["cells"][k]["只400"].get("bonf不含0")]
    only4 = sum(1 for k in judged if R["cells"][k]["只400"]["結果"] == "結果②" and R["cells"][k]["合併"]["結果"] != "結果②")
    only_c = sum(1 for k in judged if R["cells"][k]["合併"]["結果"] == "結果②" and R["cells"][k]["只400"]["結果"] != "結果②")
    luck = fam["合併"]["與運氣分不開"]
    sent = ("型態全量 96 變體在美股（S&P 500＋400）：可判定 174 格中，合格（合併與只 S&P 400 都照文獻方向過關）{} 格、事後擴母體 {} 格、不合格 {} 格，"
            "另 18 格事件太少依構造不可判定。{}合併欄族結論：{}。只 S&P 400 欄：{}。單格合格且兩欄都過 Bonferroni（0.05／174）可單獨引用的：{}。"
            "⚠ 單筆層，任何一格過關也不等於照這個型態交易能贏大盤。{}；{}。").format(
        c.get("合格", 0), c.get("事後擴母體", 0), c.get("不合格", 0),
        "" if not ok_cells else "合格格：{}。".format("、".join("%s%s%s" % (k, R["cells"][k]["型態"], warn_fake(R["cells"][k])) for k in ok_cells)),
        fam["合併"]["族結論句"], fam["只400"]["族結論句"], ("、".join(bonf_ok) if bonf_ok else "沒有"),
        CO.IDEA, CO.SURV)
    card = {"件": "A3-5", "名稱": "型態全量 單筆層（96 變體 × H20、H60）", "台股原登錄": REG35, "出場型": "③ 事件（H20、H60 判；H120 描述）",
            "N": N35, "標籤": top, "格標籤彙總": c, "格標籤": lab,
            "註": "可判定 174 格中只 S&P 400 欄 n_eff 上限 ＜30 的 %d 格照計 N、依構造最多事後擴母體（seq319 Q2）；不可判定 18 格見 退化格清單.csv" % sum(
                1 for k in judged if R["cells"][k].get("只400_n_eff上限＜30（依構造最多事後擴母體）")),
            "判定格": "全族 174 格各自判（⛔ 不挑格）；判定量 d×(R − 同日同十分位對照)", "三欄": {
                "合併": "結果② {} 格、結果③ {} 格（174 格）；{}".format(fam["合併"]["a_d方向過關"], fam["合併"]["b_反方向過關"], "與運氣分不開" if luck else "超過假訊號臂最大值"),
                "只400": "結果② {} 格、結果③ {} 格；{}".format(fam["只400"]["a_d方向過關"], fam["只400"]["b_反方向過關"], "與運氣分不開" if fam["只400"]["與運氣分不開"] else "超過假訊號臂最大值"),
                "只500": "（描述、⛔ 不判）結果② {} 格、結果③ {} 格".format(fam["只500"]["a_d方向過關"], fam["只500"]["b_反方向過關"])},
            "條件出場必報": None, "結果句": sent,
            "敏感度_ret50": "f50 當斷點（事件與對照同換）後格標籤：{}；與主結果不同的格 {} 格".format(
                R["cnt50"], sum(1 for k in judged if R["lab50"][k] != lab[k])),
            "偏離": DEV35, "補讀法": [x.strip() for x in __doc__.split("A3-5（台股")[1].split("A3-13（台股")[0].splitlines()[1:] if x.strip()],
            "先驗紀錄": {"台股登錄先驗（價格結構多依構造不可判定，約七成）": "美股不可判定 18 格，其中價格結構 %d 格" % sum(1 for k in lab if lab[k].startswith("不可判定") and k.startswith("S")),
                      "台股先驗（可判定格 d 方向過關數不超過運氣兩倍）": "合併 a＝%d、純運氣 %.1f ⇒ %s" % (fam["合併"]["a_d方向過關"], N35 * 0.025, "對" if fam["合併"]["a_d方向過關"] <= 2 * N35 * 0.025 else "錯"),
                      "台股可否證（三隻烏鴉、昏星、晨星 H20 配對版照 d 方向過關，押不會）": {k: R["cells"]["%s_H20" % k]["合併"]["結果"] for k in ("K01", "K02", "K07") if "%s_H20" % k in R["cells"] and "合併" in R["cells"]["%s_H20" % k]},
                      "美股登錄先驗（只400 過合併不過 多於 反過來）": "只400 過合併不過 %d 格、合併過只400 不過 %d 格" % (only4, only_c)}}
    files = sorted(os.listdir(os.path.join(WORK, "a35_events")))
    man = {f: sha_file(os.path.join(WORK, "a35_events", f)) for f in files}
    mp_ = os.path.join(WORK, "a35_events_manifest.json"); json.dump(man, open(mp_, "w"), indent=0, sort_keys=True)
    obj = {"卡片": card, "共同": CO.REG, "讀法寫死": READ_TS, "第一次讀報酬": R["t_first"], "資料": meta.get("data_commit"),
           "Bonferroni_z": Z_B35, "族結論": fam, "格": R["cells"], "查核": R["chk"], "存活者偏差": cov,
           "逐筆中間檔": {"位置": "~/us_work/a3/g2/a35_events/（repo 外）", "檔數": len(files), "manifest_sha256": sha_file(mp_)},
           "格標籤_敏感度ret50": R["lab50"]}
    CO.jdump(obj, os.path.join(OUT, "A3-5.json"))
    return card


def write_a313(R, meta, cov):
    lab = R["lab"]; top, c = items_label(lab)
    cl = {k: R["cells"][k]["合併"]["結果類"] for k in R["cells"]}
    cnt_c = Counter(cl.values()); cnt_4 = Counter(R["cells"][k]["只400"]["結果類"] for k in R["cells"])
    vs = R["desc"]["A對SP500TR"]
    sent = ("突破後加過濾（美股 S&P 500＋400，W 底、頭肩底、箱型 × 5 種過濾，14 格）：{}。合併欄 {}；只 S&P 400 欄 {}。"
            "直接買本身對 ^SP500TR 同段（毛、描述）：{}。行動結論照台股登錄：分不出或較差 ⇒ 直接買（突破隔天開盤）。{}；{}。").format(
        top, dict(cnt_c), dict(cnt_4), "、".join("%s %s" % (k, pct(v["A毛−SP500TR"])) for k, v in vs.items()), CO.IDEA, CO.SURV)
    card = {"件": "A3-13", "名稱": "突破後過濾（直接買 vs 幅度／站穩／放量／等回測／三道全加）", "台股原登錄": REG13, "出場型": "③ 事件（終點＝A 的 H60）",
            "N": N13, "標籤": top, "格標籤彙總": c, "格標籤": lab, "判定格": "14 格各自判（Δ＝E(過濾)−E(A)；Bonferroni 0.05／14）",
            "三欄": {col: "；".join("%s %s" % (k, R["cells"][k][col]["結果類"] + "（Δ " + pct(R["cells"][k][col]["Δ"]) + "）") for k in R["cells"]) for col in COLM},
            "條件出場必報": None, "結果句": sent,
            "敏感度_ret50": "f50 剔除後格標籤：{}；與主結果不同 {} 格".format(dict(Counter(R["lab50"].values())), sum(1 for k in lab if R["lab50"][k] != lab[k])),
            "偏離": DEV13, "補讀法": [x.strip() for x in __doc__.split("A3-13（台股")[1].split("A3-16（台股")[0].splitlines()[1:] if x.strip()],
            "先驗紀錄": {"E、F Δ＜0（約六成五）": "E、F 共 6 格，合併欄 Δ＜0 的 %d 格" % sum(1 for k in R["cells"] if k[-1] in "EF" and (R["cells"][k]["合併"]["Δ"] or 0) < 0),
                      "B、C、D 多為分不出（約六成）": "B、C、D 共 8 格，合併欄分不出 %d 格" % sum(1 for k in R["cells"] if k[-1] in "BCD" and R["cells"][k]["合併"]["結果類"] == "分不出來"),
                      "沒有一格 Δ＞0 且 CI 不含 0（約七成）": "合併欄這樣的格 %d 格" % sum(1 for k in R["cells"] if R["cells"][k]["合併"]["結果類"] in ("加過濾比較好", "單格過關")),
                      "可否證：頭肩底 D 放量 Δ＞0": "合併欄 Δ %s、%s" % (pct(R["cells"]["頭肩底×D"]["合併"]["Δ"]), R["cells"]["頭肩底×D"]["合併"]["結果類"])}}
    obj = {"卡片": card, "共同": CO.REG, "讀法寫死": READ_TS, "第一次讀報酬": R["t_first"], "資料": meta.get("data_commit"), "Bonferroni_z": Z_B13,
           "格": R["cells"], "描述": R["desc"], "事件帳": R["acc"], "查核": R["chk"], "存活者偏差": cov,
           "逐筆中間檔": {"位置": "~/us_work/a3/g2/a313_events.csv.gz（repo 外）", "sha256": sha_file(R["events_file"])}}
    CO.jdump(obj, os.path.join(OUT, "A3-13.json"))
    return card


def write_a316(R, meta, cov):
    lab = R["lab"]; top, c = items_label(lab)
    J = R["判定"]
    s3 = {col: "；".join("%s %s" % (k, "成立" if J[k][col]["成立（主版）"] else "不成立") for k in J if k.startswith("Q")) for col in COLM}
    C = R["cells_tab"]
    tabs = []
    for r in C.to_dict("records"):
        tabs.append({k: rnd(v) if isinstance(v, (float, np.floating)) else (bool(v) if isinstance(v, (np.bool_,)) else (int(v) if isinstance(v, np.integer) else v))
                     for k, v in r.items()})
    sent = ("洗盤還是出貨（圖卡四條合判，美股 S&P 500＋400）：{}。合併欄 {}。只 S&P 400 欄 {}（洗盤組太少，Q1、Q2 只 400 欄依構造最多事後擴母體）。"
            "{}；{}；{}。").format(top, s3["合併"], s3["只400"], CO.IDEA, CO.NO_EARLY, CO.SURV)
    card = {"件": "A3-16", "名稱": "洗盤還是出貨（圖卡四條合判）", "台股原登錄": REG16, "出場型": "③ 事件（H{5,20,60} 各自判）",
            "N": 9, "標籤": top, "格標籤彙總": c, "格標籤": lab, "判定格": "3 問 × 3 H；每問每 H 16 格過半（探索、確認兩段都過）",
            "三欄": {"合併": s3["合併"], "只400": s3["只400"], "只500": "（描述、⛔ 不判）" + s3["只500"]},
            "條件出場必報": None, "結果句": sent,
            "敏感度_ret50": "f50 剔除後格標籤：{}；與主結果不同 {} 格".format(dict(Counter(R["sens"]["lab"].values())), sum(1 for k in lab if R["sens"]["lab"][k] != lab[k])),
            "偏離": DEV16, "補讀法": [x.strip() for x in __doc__.split("A3-16（台股")[1].splitlines()[1:] if x.strip()],
            "先驗紀錄": {"①Q1 洗盤組可買：否（約七成）": "對" if not any(J["Q1_H%d" % H]["合併"]["成立（主版）"] for H in HS16) else "錯",
                      "②Q2 分得出：測不出（約六成五）": "對" if not any(J["Q2_H%d" % H]["合併"]["成立（主版）"] for H in HS16) else "錯",
                      "③Q3 出貨組該賣：否（約六成五）": "對" if not any(J["Q3_H%d" % H]["合併"]["成立（主版）"] for H in HS16) else "錯",
                      "④四條合起來比單條多：看不出": "見 描述 逐條 X20 差（只描述）"}}
    obj = {"卡片": card, "共同": CO.REG, "讀法寫死": READ_TS, "第一次讀報酬": R["t_first"], "資料": meta.get("data_commit"),
           "判定": J, "格表（16 格 × 3 H × 2 段 × 3 欄；彙總）": tabs, "敏感度_ret50_判定": R["sens"]["判定"], "描述": R["desc"], "查核": R["chk"],
           "存活者偏差": cov, "逐筆中間檔": {"位置": "~/us_work/a3/g2/a316_events.csv.gz（repo 外）", "sha256": sha_file(R["events_file"])}}
    CO.jdump(obj, os.path.join(OUT, "A3-16.json"))
    return card


DEV35 = ["統計照台股 researchPatAll（H20 曆月、H60 60 日區段分群），不用 core ev_summ 的 20 日區段 n_eff（G3）",
         "S 對照的錨點十分位橫斷面不限錨點日在指數（F4，台股 gate3 是固定名單）",
         "Bonferroni 分母改美股 N＝174（台股 180）",
         "「照名稱方向」讀法、包含關係 6 組、上市／上櫃、逐年描述沒做（台股只描述、⛔ 不判）",
         "T＋1 開盤漲停／跌停剔除拿掉（美股無；P4）"]
DEV13 = ["買法細節照 prep px_one（日曆數、前 5 日曆日均量、吞噬看日曆前一日、F 窗 b＋1～T＋20、先合併再剔除）＝ PREP P15；台股 seq202 的 F 窗是 b＋1～b＋20、合併是被剔除者不開窗",
         "成本 0.585% → 0.05%（seq242）", "A 對大盤：0050 開盤(T＋1) → ^SP500TR 收盤(T)（TR 只有收盤）",
         "台股 Q2 型態視窗處置／注意斷點 → 美股 S.brk（P5）"]
DEV16 = ["基準② 母體 UG.set_gate_v2 → 合併母體（當天有效 K 棒）", "成本 0.585% → 0.05%（seq242）", "早年段拿掉（美股無資料）⇒ 早年同向無法報",
         "只400 欄樣本不足規則（W6）：任一段足樣本格 ＜9 ⇒ 最多事後擴母體（seq319 Q11 落地）", "量 原始成交股數 → Yahoo 拆股調整量（缺值當 0，prep 原式）"]


# ═════════════ 主程式 ═════════════
def run(procs=2, lim=None, items=("A3-5", "A3-13", "A3-16")):
    t0 = time.time()
    meta, ST = CO.load_cache(lim)
    sids = sorted(ST)
    _ST.clear(); _ST.update(ST)
    _M.update(cal=meta["cal"], w0=meta["w0"], w1=meta["w1"], sp=meta["sp"], items=tuple(items))
    print("[g2] %d 檔｜items %s｜讀法寫死 %s" % (len(sids), items, READ_TS), flush=True)
    P1 = pass1(sids, procs)
    cov = {"存活者偏差": CO.SURV}
    try:
        c = CO.coverage_cached(meta["cal"], meta["w0"], meta["w1"])
        cov.update({"S&P400 缺價股日比例": c["sp400"]["缺價股日比例"], "S&P500 缺價股日比例": c["sp500"]["缺價股日比例"],
                    "S&P400 整段缺價檔數": c["sp400"]["窗內整段沒有價格的檔數"], "S&P500 整段缺價檔數": c["sp500"]["窗內整段沒有價格的檔數"]})
    except Exception as e:  # noqa: BLE001
        cov["註"] = "coverage 讀不到：%s" % e
    global OUT
    if lim:
        OUT = os.path.join(WORK, "lim_out")
    cards = {}
    if "A3-13" in items:
        R = run_a313(ST, sids, meta, P1, lim); cards["A3-13"] = write_a313(R, meta, cov)
        print("[A3-13] 完成 %.0fs｜%s" % (time.time() - t0, cards["A3-13"]["標籤"]), flush=True)
    if "A3-16" in items:
        R = run_a316(ST, sids, meta, P1, lim); cards["A3-16"] = write_a316(R, meta, cov)
        print("[A3-16] 完成 %.0fs｜%s" % (time.time() - t0, cards["A3-16"]["標籤"]), flush=True)
    if "A3-5" in items:
        R = run_a35(ST, sids, meta, P1, procs, lim); cards["A3-5"] = write_a35(R, meta, cov)
        print("[A3-5] 完成 %.0fs｜%s" % (time.time() - t0, cards["A3-5"]["標籤"]), flush=True)
    print("[g2] 全部完成 %.0fs" % (time.time() - t0), flush=True)
    return cards


# ═════════════ check：⭐ 獨立寫法（不呼叫上面算報酬、對照、基準的函式）═════════════
def _ind_cl(x, g):
    """獨立的 CR0 群集 SE（pandas groupby 逐群殘差和）。"""
    x = np.asarray(x, float); df = pd.DataFrame({"x": x, "g": g}).dropna()
    m = df["x"].mean(); s = (df["x"] - m).groupby(df["g"]).sum()
    se = math.sqrt(float((s ** 2).sum())) / len(df)
    return m, se, len(s), len(df)


def check(n_ev=40, seed=7):
    meta, ST = CO.load_cache(None)
    cal = meta["cal"]; n = len(cal); w0, w1, sp = meta["w0"], meta["w1"], meta["sp"]
    sids = sorted(ST)
    rng = np.random.default_rng(seed)
    out = []

    def brk_ind(d, a, b):
        v = d["valid"]; bars = d["bars"]
        for q in range(max(a, 0), min(b, n - 1) + 1):
            if d["pb"][q]:
                return True
            if bars[0] <= q <= bars[-1] and not v[q]:
                return True
        return False

    def ret_ind(d, t, H):
        o = d["O"][t + 1]
        if not (d["valid"][t + 1] and np.isfinite(o) and o > 0):
            return np.nan
        q = t + H
        while q >= 0 and not np.isfinite(d["C"][q]):
            q -= 1
        return d["C"][q] / o - 1.0
    # ── A3-5：抽事件，逐檔迴圈重算 R 與對照平均
    J5 = json.load(open(os.path.join(OUT, "A3-5.json"), encoding="utf-8"))
    picks = [("K02", 20), ("K14", 60), ("K56", 20), ("S01", 20), ("S28", 60)]
    raw = {vid: {} for vid, _ in picks}          # 原始偵測（偵測器只 import；同 prep 原式；每檔偵測一次）
    for s in sids:
        d = ST[s]; b = d["bars"]
        dd = PA.detect_all(d["O"][b], d["H"][b], d["L"][b], d["C"][b], np.nan_to_num(d["V"][b]), d["O"][b], d["H"][b], d["L"][b], d["C"][b])
        for vid in raw:
            e = dd[vid]
            raw[vid][s] = set(int(x) for x in b[np.asarray(e["T"], np.int64)]) if len(e["T"]) else set()
    bad = 0; tot = 0; ex = []
    for vid, H in picks:
        v = PA.VMAP[vid]
        f = os.path.join(WORK, "a35_events", "events_%s.csv.gz" % vid)
        if not os.path.exists(f):
            continue
        Ev = pd.read_csv(f)
        Ev = Ev[(Ev["H"] == H) & (Ev["配對"] == "有")]
        if len(Ev) == 0:
            continue
        sub = Ev.iloc[rng.choice(len(Ev), size=min(8, len(Ev)), replace=False)]
        dpos = {str(x.date()): i for i, x in enumerate(cal)}
        for r in sub.itertuples(index=False):
            T = dpos[r.T]; fst = dpos[r.first]; me = ST[r.sid]
            R = ret_ind(me, T, H)
            k = v["k"]
            # 各檔的事前量
            vals = {}
            for s in sids:
                d = ST[s]; b = d["bars"]
                if not (d["valid"][T]):
                    continue
                jb = int(np.searchsorted(b, T))
                if v["fam"] == "K":
                    if not d["member"][T] or jb - k - 10 < 0:
                        continue
                    cb = d["C"][b]
                    a1 = cb[jb - k] / cb[jb - k - 10] - 1.0; a2 = cb[jb] / cb[jb - k] - 1.0
                    if np.isfinite(a1) and np.isfinite(a2):
                        vals[s] = (a1, a2, int(b[jb - k + 1]))
                else:
                    pass
            if v["fam"] == "K":
                ss = list(vals)
                q1 = pd.qcut(pd.Series([vals[s][0] for s in ss]).rank(method="first"), 10, labels=False).to_numpy()
                q2 = pd.qcut(pd.Series([vals[s][1] for s in ss]).rank(method="first"), 10, labels=False).to_numpy()
                D1 = dict(zip(ss, q1)); D2 = dict(zip(ss, q2))
                pre = v["pre"]
                xs = []
                for s in ss:
                    if s == r.sid or D1[s] != D1[r.sid] or D2[s] != D2[r.sid]:
                        continue
                    sg = np.sign(vals[s][0])
                    if (pre == "升" and sg != 1) or (pre == "降" and sg != -1) or (pre not in ("升", "降") and sg == 0):
                        continue
                    if T in raw[vid][s]:
                        continue
                    d = ST[s]
                    if brk_ind(d, vals[s][2], T + H):
                        continue
                    g = ret_ind(d, T, H)
                    if np.isfinite(g):
                        xs.append(g)
            else:
                A20 = vid in ANCHOR20; L_ = 21 if A20 else 61
                av = {}
                for s in sids:
                    d = ST[s]; b = d["bars"]
                    if not d["valid"][fst]:
                        continue
                    jb = int(np.searchsorted(b, fst))
                    if jb - L_ + 1 - 1 < 0 or jb < L_:
                        continue
                    cb = d["C"][b]; a = cb[jb - 1] / cb[jb - L_] - 1.0
                    if np.isfinite(a):
                        av[s] = a
                ss = list(av); qq = pd.qcut(pd.Series([av[s] for s in ss]).rank(method="first"), 10, labels=False).to_numpy(); DD = dict(zip(ss, qq))
                xs = []
                for s in ss:
                    if s == r.sid or DD[s] != DD.get(r.sid, -9):
                        continue
                    d = ST[s]
                    if not (d["member"][T] and d["valid"][T]) or T in raw[vid][s] or brk_ind(d, fst, T + H):
                        continue
                    g = ret_ind(d, T, H)
                    if np.isfinite(g):
                        xs.append(g)
            ctrl = float(np.mean(xs)) if xs else np.nan
            tot += 1
            if not (abs(R - r.R) < 1e-9 and abs(ctrl - r.對照平均) < 1e-9 and len(xs) == r.對照數):
                bad += 1; ex.append((vid, H, r.sid, r.T, R, r.R, ctrl, r.對照平均, len(xs), r.對照數))
    # 判定重算（從逐筆檔、獨立 SE）
    mm = 0
    for vid, H in picks:
        f = os.path.join(WORK, "a35_events", "events_%s.csv.gz" % vid)
        key = "%s_H%d" % (vid, H)
        if not os.path.exists(f) or key not in J5["格"] or "合併" not in J5["格"][key]:
            continue
        Ev = pd.read_csv(f); Ev = Ev[(Ev["H"] == H) & np.isfinite(Ev["X"])]
        for col, msk in (("合併", np.ones(len(Ev), bool)), ("只400", Ev["只400"].to_numpy(bool))):
            x = Ev["dX"].to_numpy(float)[msk]; g = Ev["分群"].to_numpy()[msk]
            m, se, ng, nn = _ind_cl(x, g); ne = min(nn, ng)
            rs = "樣本不足以分辨" if ne < 30 else ("結果①" if m - 1.96 * se <= 0 <= m + 1.96 * se else ("結果②" if m > 0 else "結果③"))
            tot += 1
            if rs != J5["格"][key][col]["結果"]:
                mm += 1; ex.append(("判定", key, col, rs, J5["格"][key][col]["結果"]))
    out.append({"件": "A3-5", "抽樣": tot, "不同": bad + mm, "說明": "抽 5 格各最多 8 筆事件：逐檔迴圈重算 R、十分位（pd.qcut rank first）、事前門檻、原始偵測、硬斷點、對照平均與對照數；"
                "另由逐筆檔用獨立 groupby SE 重算 10 個欄格的結果字樣", "例": ex[:5]})
    # ── A3-13：抽事件，逐日迴圈重算進場日與報酬
    X = pd.read_csv(os.path.join(WORK, "a313_events.csv.gz"))
    J13 = json.load(open(os.path.join(OUT, "A3-13.json"), encoding="utf-8"))
    sub = X.iloc[rng.choice(len(X), size=min(n_ev, len(X)), replace=False)]
    bad = 0; tot = 0; ex = []
    for r in sub.itertuples(index=False):
        d = ST[r.sid]; T = int(r.T)
        # 頸線：重新偵測（偵測器只 import）
        b = d["bars"]; N_ = None
        if r.type in ("w", "hs"):
            for e in PX.detect_turn(r.type, d["C"][b])["events"]:
                if int(b[e["T"]]) == T:
                    N_ = float(e["level"])
        else:
            fd = pd.DataFrame({"open": d["O"], "high": d["H"], "low": d["L"], "close": d["C"], "volume": np.nan_to_num(d["V"]), "traded": d["valid"]}, index=cal)
            for e in PX.box_events(PX.frame_open(fd, set(cal[d["pb"]]))):
                if int(e["T"]) == T:
                    N_ = float(e["level"])
        C, O, Hh, L, V, v = d["C"], d["O"], d["H"], d["L"], d["V"], d["valid"]

        def vm5(q):
            w = V[q - 5:q]
            return float(np.mean(w)) if np.all(np.isfinite(w)) else np.nan

        def stop_k(q):
            o_, h_, l_, c_ = O[q], Hh[q], L[q], C[q]
            body = abs(c_ - o_); rg = h_ - l_
            hammer = rg > 0 and body > 0.1 * rg and (min(o_, c_) - l_) >= 2 * body and (h_ - max(o_, c_)) <= 0.1 * rg
            p = q - 1
            engulf = bool(v[p]) and C[p] < O[p] and c_ > o_ and max(o_, c_) >= max(O[p], C[p]) and min(o_, c_) <= min(O[p], C[p]) and body > abs(C[p] - O[p])
            return hammer or engulf

        def retest(a, z):
            for q in range(a, min(z, n - 2) + 1):
                if not v[q]:
                    continue
                if C[q] < 0.97 * N_:
                    return None
                if L[q] <= 1.02 * N_ and C[q] >= N_ and np.isfinite(V[q]) and V[q] < vm5(q) and stop_k(q):
                    return q
            return None
        ent = {"A": T + 1}
        bb = next((q for q in range(T, T + 5) if q < n and v[q] and C[q] >= 1.03 * N_), None)
        ent["B"] = bb + 1 if (bb is not None and v[bb + 1]) else None
        if r.type != "box":
            ent["C"] = T + 3 if (all(v[q] and C[q] > N_ for q in (T, T + 1, T + 2)) and v[T + 3]) else None
        vt = vm5(T); dk = np.isfinite(vt) and vt > 0 and np.isfinite(V[T]) and V[T] >= 1.5 * vt
        ent["D"] = T + 1 if dk else None
        q = retest(T + 1, T + 20); ent["E"] = q + 1 if (q is not None and v[q + 1]) else None
        if dk and bb is not None:
            q = retest(bb + 1, T + 20); ent["F"] = q + 1 if (q is not None and v[q + 1]) else None
        else:
            ent["F"] = None
        cl = pd.Series(C).ffill().to_numpy()
        for arm, x in ent.items():
            rr = 0.0 if x is None else cl[T + 60] / O[x] - 1.0 - COST
            tot += 1
            if int(x is not None) != int(getattr(r, "bought_" + arm)) or abs(rr - getattr(r, "r60_" + arm)) > 1e-9:
                bad += 1; ex.append((r.sid, r.type, T, arm, x, rr, getattr(r, "r60_" + arm)))
    mm = 0
    for key in ("W 底×B", "頭肩底×E", "箱型×D"):
        typ = {v_: k_ for k_, v_ in TNAME.items()}[key.split("×")[0]]; arm = key.split("×")[1]
        Y = X[X["type"] == typ]
        m, se, ng, nn = _ind_cl((Y["r60_" + arm] - Y["r60_A"]).to_numpy(float), Y["blk"].to_numpy())
        tot += 1
        if abs(m - J13["格"][key]["合併"]["Δ"]) > 1e-6 or abs((m - 1.96 * se) - J13["格"][key]["合併"]["CI95_lo"]) > 1e-6:
            mm += 1; ex.append(("判定", key, m, J13["格"][key]["合併"]["Δ"]))
    out.append({"件": "A3-13", "抽樣": tot, "不同": bad + mm, "說明": "抽 %d 筆事件：重新偵測頸線、逐日迴圈重算 A～F 進場日與 H60 報酬（獨立的錘子／吞噬／均量寫法）；另 3 格 Δ 與 CI 由逐筆檔獨立重算" % len(sub), "例": ex[:5]})
    # ── A3-16：抽事件，逐檔迴圈重算 R、基準②、X 與分組
    E = pd.read_csv(os.path.join(WORK, "a316_events.csv.gz"))
    J16 = json.load(open(os.path.join(OUT, "A3-16.json"), encoding="utf-8"))
    E = E[E["去重"] & E["ok20"] & np.isfinite(E["X20"])]
    sub = E.iloc[rng.choice(len(E), size=min(n_ev, len(E)), replace=False)]
    bad = 0; tot = 0; ex = []
    cache_base = {}
    for r in sub.itertuples(index=False):
        T = int(r.T); H = 20
        if T not in cache_base:
            rows = []
            for s in sids:
                d = ST[s]
                if not (d["member"][T] and d["valid"][T]):
                    continue
                cz = d["closes"]
                a = cz[T] / cz[T - 20] - 1.0 if T >= 20 else np.nan
                g = ret_ind(d, T, H)
                if np.isfinite(a) and np.isfinite(g):
                    rows.append((s, a, g))
            df = pd.DataFrame(rows, columns=["s", "a", "g"])
            df["q"] = pd.qcut(df["a"].rank(method="first"), 10, labels=False)
            cache_base[T] = df
        df = cache_base[T]
        qq = df.loc[df["s"] == r.sid, "q"]
        base = float(df.loc[df["q"] == int(qq.iloc[0]), "g"].mean()) if len(qq) else np.nan
        R = ret_ind(ST[r.sid], T, H)
        tot += 1
        if not (abs(R - r.R20) < 1e-5 * max(1, abs(R)) and abs((R - base) - r.X20) < 1e-5):
            bad += 1; ex.append((r.sid, T, R, r.R20, R - base, r.X20))
        # 四條重算（獨立寫法）
        d = ST[r.sid]; b = d["bars"]; c = d["C"][b]; vv = np.nan_to_num(d["V"][b])
        P = int(np.searchsorted(b, r.Pc)); L = int(np.searchsorted(b, r.Lc)); Tb = int(np.searchsorted(b, T))
        pos = c[P] / c[P - 249:P + 1].min() - 1.0
        c1 = 1 if pos < r.P else -1
        vr, vp, vbb = vv[P - 59:P + 1].mean(), vv[P + 1:L + 1].mean(), vv[L + 1:Tb + 1].mean()
        w2 = vr > 0 and vp / vr < 0.8
        d2 = any(vv[q - 20:q].mean() > 0 and vv[q] >= 2 * vv[q - 20:q].mean() and c[q] / c[q - 1] - 1 <= 0.005 for q in range(max(P - 10, 20), min(P + 10, Tb) + 1))
        lvl = c[Tb - 59:Tb + 1].mean() if r.支撐 == "MA60" else c[P - 60] + 0.5 * (c[P] - c[P - 60])
        c3 = 1 if c[L] >= lvl else -1
        ww = [c1 == 1, w2, c3 == 1, vbb > vp]; dd = [c1 == -1, d2, c3 == -1, vbb < vp]
        grp = "洗盤" if all(ww) else ("出貨" if sum(dd) >= 3 else "混合")
        tot += 1
        if grp != r.組 or [c1, int(w2) - int(d2), c3, int(vbb > vp) - int(vbb < vp)] != [r.位置, r.量能, r.走勢, r.反彈]:
            bad += 1; ex.append(("四條", r.sid, T, grp, r.組))
    # 過半判定由格表重算
    mm = 0
    tab = pd.DataFrame(J16["格表（16 格 × 3 H × 2 段 × 3 欄；彙總）"])
    for H in HS16:
        for q_, need in (("Q1", "洗盤"), ("Q2", "both"), ("Q3", "出貨")):
            for col in COLM:
                for seg in ("探索", "確認"):
                    x = tab[(tab["段"] == seg) & (tab["H"] == H) & (tab["欄"] == col)]
                    suff = (x["洗盤_n"] >= 30) & (x["出貨_n"] >= 30) if need == "both" else (x["%s_n" % need] >= 30)
                    ns = int(suff.sum()); ps_ = int((x["%s過" % q_] & suff).sum())
                    tot += 1
                    mm += int((ns > 0 and ps_ > ns / 2) != J16["判定"]["%s_H%d" % (q_, H)][col][seg]["主版過半"])
    out.append({"件": "A3-16", "抽樣": tot, "不同": bad + mm, "說明": "抽 %d 筆事件：逐檔迴圈重算 R20、基準②（pd.qcut rank first）、X20 與四條分組；另 54 個「欄×段×問×H」的過半判定由格表重算" % len(sub), "例": ex[:5]})
    for o in out:
        print(json.dumps(o, ensure_ascii=False, default=str), flush=True)
    json.dump(out, open(os.path.join(WORK, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    return out


if __name__ == "__main__":
    procs = int(sys.argv[sys.argv.index("--procs") + 1]) if "--procs" in sys.argv else 2
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    only = tuple(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else ("A3-5", "A3-13", "A3-16")
    if "--run" in sys.argv:
        run(procs, lim, only)
    if "--check" in sys.argv:
        check()
