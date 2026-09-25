# -*- coding: utf-8 -*-
"""PREREGX（型態量幅目標＋成形前讀法）偵測器層。判準＝台股策略線 PREREGX seq2（sha 7de459d6a4578cf6）§一、§一之二。

⛔ 本支只產生事件日／形成中時點與型態價位；⛔ 不碰任何報酬。
⛔ 研究二的 patterns.py、PREREGM 的 trendline_m.py 只 import、不改；要改行為一律在本檔包一層。

五型（甲）＋六型（乙）：
   W 底、頭肩底、旗形 ⇒ 本檔新寫（補齊版 §零 轉折；登錄 §一之二 ②③④）
   箱型、杯柄         ⇒ 研究二 patterns.box_breakout／cup_handle 原樣（Frame.gate 由呼叫端決定：主跑一律全開＋gate3 母體）
   趨勢線（只用於乙）  ⇒ trendline_m.detect_pivot(「甲」, R＝5) 原樣

⭐ 登錄沒逐字寫、本檔的落地讀法（⛔ 在看任何頻率或結果之前寫在這裡；交件逐條列出；★ ＝ 有兩種讀法、此處擇一）：
 X1 幾何（轉折 k＝3、同類間隔 ≥ 5、W＝60、旗桿 20、旗面 5～25）一律在【該股有效 K 棒序列】上數（同 trendline_m M1、researchH2 R1）；
    起點 T+1、H、20 日、40 日一律用【交易日曆】（researchX.py）。
 X2 轉折（⓪）：局部低點 ＝ c[s] ≤ c[s−3..s+3] 每一根（含平手）；平手連續 ⇒ 若 s−1 也是局部低點且 c[s−1]＝c[s] ⇒ s 不算（取最早）；
    與前一個已確認同類轉折 p 的距離 s−p ＜ 5 ⇒ 較極端者留（低點較低、高點較高；平手留 p）；s 在 s＋3 收盤後才確認。
    高點對稱。p 被 s 取代 ＝「新轉折確認」⇒ 組換掉（⓪ 同時只追一組）。
 X3 同一根 b 的處理順序（同 trendline_m M3）：① 先用 b 開盤前就存在的組判 b（過期 → 觸發 → 形成中 S）；
    ② 再處理 b 收盤後剛確認的轉折 ⇒ 換組、舊組結束（舊組在 b 已判過）；③ 新組當根（＝其確認日）即判（登錄「確認日起」含確認日）。
 X4 ★ 60 日視窗「含頭尾」：b − 第一轉折 ＋ 1 ≤ 60（有效 K 棒）；超過 ⇒ 組作廢（該組最後被判的一根 ＝ 第一轉折＋59）。
 X5 W 底：A ＝ c[L1..L2] 最高收盤那天（端點是低點、不影響）；T ＝ b ≥ L2＋3 的第一個 c[b] ＞ c[A]；S ＝ 組內第一個 c[b] ＜ c[A] 的 b。
 X6 頭肩底：A1＝c[L..H] 最高、A2＝c[H..R] 最高；頸線＝(A1＋A2)/2；T ＝ b ≥ R＋3 的第一個 c[b] ＞ 頸線；S ＝ 第一個 c[b] ＜ 頸線。
 X7 旗形：組 ＝ 最近一個已確認局部高點 E（⓪「同時只追一組」逐字：旗面內若再確認一個較低的局部高點 E'，E' 成為新組 ★
    〔另一讀法：旗面內較低的高點不換組〕）；S0 ＝ c[E−20..E−1] 最低收盤那天（平手取最早）；E＜20 根 ⇒ 無旗桿。
    在第 b 根：旗面 F ＝ c[E+1..b−1]、長 m＝b−E−1：
      m ＞ 25 ⇒ 作廢（最後被判 ＝ E＋26）；
      m ≥ 5 且 F 全部條件成立（回檔 (c[E]−minF)/c[E] ∈ [0.05,0.20]、斜率 ≤ 0、收斂）且 c[b] ＞ maxF ⇒ T；
      m ≥ 5 且 F 條件成立且 c[b] ≤ maxF ⇒ S 候選（第一個）；
      沒觸發且 c[b] ＞ c[E] ⇒ 作廢（旗桿延長；b 成為旗面的一天）。
    收斂：F 前半 ＝ 前 ceil(m/2) 天（奇數中間那天歸前半），後半收盤高低幅 ≤ 前半 ⇒ 成立。斜率 ＝ F 對 0..m−1 的最小平方斜率。
    旗面低點（甲 描述）＝ minF(T)；乙 破壞位 ＝ min c[E+1..S]（★ 含 S 當天；S 當天收盤已屬旗面）。
 X8 乙 每組的追蹤終點 end ＝ 該組最後一根被判的 K 棒（觸發當根／過期前最後一根／被新組取代的那一根）；
    ★ 終點之後不再算成形或破壞（登錄 ⑦「過期 ⇒ 歸都沒發生」的類推：被取代與過期同樣處理）
    〔另一讀法：破壞在 40 日內一路追，不因組結束而停〕。
 X9 箱型 乙：研究二 box_ok（高度 ≤ 20%、3 天法則）且 box_bot ≤ c ≤ box_top ⇒ S；「一段」＝ 箱體起點 t−20（逐日滑動 ⇒ 每天一組，
    實際由「同檔同型 20 日只取第一個 S」收斂）；破壞位 ＝ box_bot[S]；
    ★ 成形 ＝ (S, S+40] 內任一研究二箱型事件日（站穩確認日）〔另一讀法：只認同一個箱體的突破——箱體逐日滑動、無法唯一認定〕。
 X10 杯柄 乙：研究二 cup_handle 的找杯流程原樣重寫在 cup_scan（⭐ 其突破清單須與 patterns.cup_handle 逐筆相同，researchX 每檔斷言）；
    柄 ＝ R+1..t−1（研究二程式的柄起點 ＝ 右杯口 R 的次日 ⇒ 與登錄「杯口 ＝ 右杯口 cR」一致）；
    S ＝ 柄長 5～30、柄低 ＞ 杯中點、柄均量 ＜ 右半杯均量、柄長 ＜ 杯身長 全部成立，且 柄低 ≤ c[t] ≤ c[R]、且 t 不是突破；
    「一段」＝ 左杯口 L；成形 ＝ 同一個 R 的研究二突破（不受研究二 20 日去重影響）；破壞位 ＝ 杯底 c[B]；
    組結束 ＝ 研究二迴圈 break 的那一根（柄破中點、柄逾 30 日、帶量突破但內部條件不符、缺值）。
 X11 趨勢線 乙：trendline_m 的 trace[b−1] ＝ b 開盤前的現行線；有效 ＝ b − conf ≤ 60；S ＝ 線有效、b 不是突破、
    0.97·ℓ(b) ≤ c[b] ≤ ℓ(b)（3% 用 ≤）；成形 ＝ 同一組取點的突破事件；破壞位 ＝ min c[P1..S]。
"""
from __future__ import annotations
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import patterns as P            # noqa: E402  研究二偵測器（只 import）
from backtest import trendline_m as TM        # noqa: E402  PREREGM 偵測器（只 import）

K = 3                 # 補齊版 §零②
GAP = 5               # 補齊版 §零③
WIN = 60              # 補齊版 §零④
W_EQ, W_BOUNCE = 0.05, 0.10
HS_SH, HS_DEPTH = 0.05, 0.10
FL_POLE, FL_POLE_N = 0.30, 20
FL_FACE_MIN, FL_FACE_MAX = 5, 25
FL_RET_MIN, FL_RET_MAX = 0.05, 0.20
TL_R, TL_NEAR = 5, 0.03
TYPES_A = ("box", "cup", "w", "hs", "flag")               # 甲 五型
TYPES_B = ("box", "cup", "w", "hs", "flag", "trend")      # 乙 六型


# ═════════════ 轉折（⓪，補齊版三型） ═════════════
def local_ext(c, k=K):
    """lo[s]／hi[s]：c[s] ≤／≥ 前後各 k 根每一根（含平手）；⚠ 用到 s+k ⇒ 只能在 s+k 收盤後使用。"""
    c = np.asarray(c, float); n = len(c)
    lo = np.zeros(n, bool); hi = np.zeros(n, bool)
    if n < 2 * k + 1:
        return lo, hi
    W = np.lib.stride_tricks.sliding_window_view(c, 2 * k + 1)
    mid = c[k:n - k]
    fin = np.isfinite(W).all(axis=1)
    with np.errstate(invalid="ignore"):
        lo[k:n - k] = fin & (mid <= W.min(axis=1))
        hi[k:n - k] = fin & (mid >= W.max(axis=1))
    return lo, hi


def pivot_seq(c, kind, k=K, gap=GAP, lag=None):
    """X2：回 {b: 該根收盤後已確認轉折序列的最後三個}（只在有變動的 b 出現）。
    lag：⛔ 正式一律＝k；lag≠k 只給 fixture 的「確認提早一根」鑑別力測試用。"""
    lag = k if lag is None else lag
    c = np.asarray(c, float); n = len(c)
    lo, hi = local_ext(c, k)
    flag = lo if kind == "L" else hi
    piv, out = [], {}
    for b in range(n):
        s = b - lag
        if s < 0 or s >= n or not flag[s]:
            continue
        if s >= 1 and flag[s - 1] and c[s - 1] == c[s]:
            continue                                  # 平手連續：取最早
        if piv and s - piv[-1] < gap:
            better = c[s] < c[piv[-1]] if kind == "L" else c[s] > c[piv[-1]]
            if better:
                piv[-1] = s; out[b] = tuple(piv[-3:])
        else:
            piv.append(s); out[b] = tuple(piv[-3:])
    return out


# ═════════════ W 底／頭肩底／旗形（補齊版三型） ═════════════
def _mk_w(c, tail, b, eq=W_EQ, bounce=W_BOUNCE):
    if len(tail) < 2:
        return None
    L1, L2 = tail[-2], tail[-1]
    A = L1 + int(np.argmax(c[L1:L2 + 1])); cA = c[A]
    m = min(c[L1], c[L2])
    if not (abs(c[L1] - c[L2]) / c[L1] <= eq):
        return None
    if not ((cA - m) / m >= bounce):
        return None
    return {"id": (L1, L2), "first": L1, "conf": b, "level": cA, "target": cA + (cA - m), "low": m,
            "pts": {"L1": L1, "L2": L2, "A": A}, "S": None, "trig": None, "end": None}


def _mk_hs(c, tail, b, sh=HS_SH, depth=HS_DEPTH):
    if len(tail) < 3:
        return None
    L, H, R = tail[-3], tail[-2], tail[-1]
    if not (c[H] < c[L] and c[H] < c[R]):
        return None
    if not (abs(c[L] - c[R]) / c[H] <= sh):
        return None
    a1 = L + int(np.argmax(c[L:H + 1])); a2 = H + int(np.argmax(c[H:R + 1]))
    neck = (c[a1] + c[a2]) / 2.0
    if not ((neck - c[H]) / neck >= depth):
        return None
    return {"id": (L, H, R), "first": L, "conf": b, "level": neck, "target": neck + (neck - c[H]), "low": c[H],
            "pts": {"L": L, "H": H, "R": R, "A1": a1, "A2": a2}, "S": None, "trig": None, "end": None}


def _mk_flag(c, tail, b, pole=FL_POLE, pole_n=FL_POLE_N):
    if len(tail) < 1:
        return None
    E = tail[-1]
    if E < pole_n:
        return None
    seg = c[E - pole_n:E]
    S0 = E - pole_n + int(np.argmin(seg))                # 平手取最早（argmin）
    if not (c[E] / c[S0] - 1.0 >= pole):
        return None
    return {"id": (E,), "first": S0, "conf": b, "E": E, "S0": S0, "pole": c[E] - c[S0],
            "pts": {"S0": S0, "E": E}, "S": None, "trig": None, "end": None, "low": None, "level": None, "target": None}


def face_ok(F, cE, rmin=FL_RET_MIN, rmax=FL_RET_MAX):
    """X7：旗面條件（回檔、斜率 ≤ 0、收斂）。F ＝ 旗面收盤（長 m ≥ 1）。"""
    m = len(F)
    ret = (cE - F.min()) / cE
    if not (rmin <= ret <= rmax):
        return False
    x = np.arange(m, dtype=float); x -= x.mean()
    sxx = float((x * x).sum())
    slope = float((x * (F - F.mean())).sum()) / sxx if sxx > 0 else 0.0
    if not slope <= 0:
        return False
    h1 = int(math.ceil(m / 2.0))
    a, b_ = F[:h1], F[h1:]
    if len(b_) == 0:
        return False
    return (b_.max() - b_.min()) <= (a.max() - a.min())


def _judge(kind, c, G, b, win, fmin=FL_FACE_MIN, fmax=FL_FACE_MAX):
    """X3 ①／③：判第 b 根。回 'expire'／'trig'／'void'／None。"""
    if b - G["first"] + 1 > win:
        return "expire"
    if kind in ("w", "hs"):
        if c[b] > G["level"]:
            G["trig"] = b
            return "trig"
        if G["S"] is None and c[b] < G["level"]:
            G["S"] = b
        return None
    # 旗形
    E = G["E"]; m = b - E - 1
    if m > fmax:
        return "expire"
    if m >= fmin:
        F = c[E + 1:b]
        if face_ok(F, c[E]):
            fh = F.max()
            if c[b] > fh:
                G["trig"] = b; G["level"] = fh; G["target"] = fh + G["pole"]; G["low"] = F.min()
                return "trig"
            if G["S"] is None:
                G["S"] = b; G["S_low"] = float(min(F.min(), c[b])); G["S_level"] = fh
    if c[b] > c[E]:
        return "void"
    return None


def detect_turn(kind, c, lag=None, trace=False, win=WIN, **kw):
    """W 底（kind='w'）、頭肩底（'hs'）、旗形（'flag'）：有效 K 棒序列上的線上掃描。
    回 {"events": 觸發（甲），"groups": 形狀成立的每一組（乙：S／trig／end），"trace": 每根收盤後 (組 id, 觸發數, S 數)}。"""
    c = np.asarray(c, float); n = len(c)
    ch = pivot_seq(c, "H" if kind == "flag" else "L", lag=lag)
    mk = {"w": _mk_w, "hs": _mk_hs, "flag": _mk_flag}[kind]
    G = None
    events, groups = [], []
    tr = [None] * n if trace else None
    nS = 0

    def finish(G, end):
        G["end"] = end; groups.append(G)

    def run(G, b):
        nonlocal nS
        s0 = G["S"]
        r = _judge(kind, c, G, b, win, **{k_: v for k_, v in kw.items() if k_ in ("fmin", "fmax")})
        if G["S"] is not None and s0 is None:
            nS += 1
        if r == "expire":
            finish(G, b - 1); return None
        if r == "trig":
            events.append({"T": b, "first": G["first"], "level": G["level"], "target": G["target"], "low": G["low"],
                           "id": G["id"], "pts": dict(G["pts"])})
            finish(G, b); return None
        if r == "void":
            finish(G, b); return None
        return G

    for b in range(n):
        if G is not None:                                   # X3 ①
            G = run(G, b)
        tail = ch.get(b)
        if tail is not None:                                # X3 ②
            if G is not None:
                finish(G, b); G = None
            G = mk(c, tail, b, **{k_: v for k_, v in kw.items() if k_ not in ("fmin", "fmax")})
            if G is not None:                               # X3 ③
                G = run(G, b)
        if trace:
            tr[b] = (None if G is None else G["id"], len(events), nS)
    if G is not None:
        finish(G, n - 1)
    return {"events": events, "groups": groups, "trace": tr}


# ═════════════ 箱型、杯柄（研究二原樣＋包裝） ═════════════
def frame_open(df, event_dates=frozenset()):
    """研究二 Frame，閘門全開（⛔ 不用 Frame.gate；主跑的母體是 gate3、硬斷點在 researchX 判）。"""
    f = P.Frame(df, set(event_dates))
    f.gate = np.ones(f.n, bool)
    return f


def box_events(f):
    """研究二 box_breakout 原樣；事件日 ＝ 站穩確認日（訊號日＋2）、起點 ＝ 次日開盤（＝研究二 entry_pos）。"""
    kd = f.p["confirm_days"]; W = f.p["box_window"]
    out = []
    for s in P.box_breakout(f):
        t = s["signal_pos"]; top, bot = float(f.box_top[t]), float(f.box_bot[t])
        out.append({"T": t + kd, "sig": t, "entry": s["entry_pos"], "first": t - W, "level": top,
                    "target": top + (top - bot), "low": bot})
    return out


def box_forming(f):
    """X9：S ＝ box_ok 且 box_bot ≤ c ≤ box_top；一段 ＝ 箱體起點 t−20（逐日一組）。"""
    W = f.p["box_window"]
    with np.errstate(invalid="ignore"):
        ok = f.box_ok() & np.isfinite(f.box_top) & np.isfinite(f.c) & (f.c >= f.box_bot) & (f.c <= f.box_top) & f.gate
    return [{"S": int(t), "first": int(t - W), "low": float(f.box_bot[t]), "id": int(t - W)} for t in np.flatnonzero(ok)]


def cup_events(f):
    """研究二 cup_handle(buy='handle') 原樣；起點 ＝ 次日開盤；目標在 researchX 以起點開盤＋杯深算（研究二原樣）。"""
    out = []
    for s in P.cup_handle(f, buy="handle"):
        out.append({"T": s["signal_pos"], "entry": s["entry_pos"], "first": s["L"], "depth_px": s["cup_L"] - s["cup_B"],
                    "low": s["cup_B"], "L": s["L"], "B": s["B"], "R": s["R"]})
    return out


def cup_scan(f, pivot_shift: int = 0):
    """X10：研究二 cup_handle 的找杯流程逐行照抄（buy='handle'、unit=1），另記每個 R 的 S／成形／終點。
    回 (signals, groups)；signals 必須與 patterns.cup_handle(f) 逐筆相同（呼叫端斷言）。
    pivot_shift：⛔ 正式＝0；≠0 只給 fixture 的前視鑑別力測試（故意讓樞紐多看未來幾根）。"""
    p = f.p
    c, h, l, v = f.c, f.h, f.l, f.v
    n = f.n
    u_frac = p["u_frac"]
    k = max(1, p["pivot_k"])
    cup_lo, cup_hi = p["cup_len"]
    half_min = p["half_min"]
    h_lo, h_hi = p["handle_len"]
    prior_lb = p["prior_lookback"]
    lookbacks = list(p["cup_lookbacks"])
    vol_ma = f.vol_ma50
    cs = pd.Series(c)
    kk = k + pivot_shift
    roll = cs.rolling(2 * kk + 1, center=True, min_periods=2 * kk + 1).max().to_numpy(float)
    pivots = np.flatnonzero((c == roll) & ~np.isnan(roll))
    out, groups = [], []
    last_sig = -10 ** 9
    for R in pivots:
        cR = c[R]
        found = None
        for lb in lookbacks:
            lo = max(0, R - lb)
            B = P._nanargmin(c[lo:R + 1], lo)
            if B is None or B == R:
                continue
            L = P._nanargmax(c[lo:B + 1], lo)
            if L is None or not (L < B):
                continue
            cL, cB = c[L], c[B]
            if B - L < half_min or R - B < half_min or not (cup_lo <= R - L <= cup_hi):
                continue
            depth = (cL - cB) / cL
            if not (p["cup_depth"][0] <= depth <= p["cup_depth"][1]):
                continue
            if not (p["rim_ratio"][0] <= cR / cL <= p["rim_ratio"][1]):
                continue
            pre = c[max(0, L - prior_lb):L + 1]
            if np.isnan(pre).all() or cL / np.nanmin(pre) < p["cup_prior_rise"]:
                continue
            seg = c[L:R + 1]
            if np.isnan(seg).mean() > 0.05:
                continue
            u = np.nanmean(seg <= cB + p["u_zone"] * (cL - cB))
            if u < u_frac:
                continue
            found = (L, B, cL, cB, depth, u)
            break
        if found is None:
            continue
        L, B, cL, cB, depth, u = found
        mid = cB + 0.5 * (cL - cB)
        vol_right = np.nanmean(v[B:R + 1])
        G = {"id": int(L), "R": int(R), "L": int(L), "B": int(B), "first": int(L), "low": float(cB),
             "S": None, "trig": None, "end": None}
        end = None
        for t in range(R + h_lo + 1, min(n, R + h_hi + 2)):
            hs = slice(R + 1, t)
            if np.isnan(c[hs]).any() or np.isnan(c[t]):
                end = t - 1
                break
            hl = np.nanmin(l[hs]); hh = np.nanmax(h[hs])
            if hl <= mid:
                end = t - 1
                break
            level = hh
            inner = bool(np.nanmean(v[hs]) < vol_right and (t - R - 1) < (R - L) and f.gate[t])
            if c[t] > level and v[t] >= p["handle_vol_x"] * vol_ma[t]:
                if inner:
                    G["trig"] = t
                    if t - last_sig >= 20:
                        out.append({"signal_pos": t, "entry_pos": t + 1, "L": L, "B": B, "R": R,
                                    "cup_L": cL, "cup_B": cB, "handle_high": hh, "handle_low": hl})
                        last_sig = t
                end = t
                break
            if G["S"] is None and inner and hl <= c[t] <= cR:
                G["S"] = t
        else:
            end = min(n, R + h_hi + 2) - 1
        G["end"] = end
        groups.append(G)
    return out, groups


# ═════════════ 趨勢線（只用於乙；PREREGM (甲) 原樣） ═════════════
def trend_forming(o, h, c, R=TL_R, near=TL_NEAR, lag=None):
    """X11：有效 K 棒序列 ⇒ 每條線一組 {id＝取點, first＝P1, conf, S, trig, end, low}。"""
    o = np.asarray(o, float); h = np.asarray(h, float); c = np.asarray(c, float); m = len(c)
    r = TM.detect_pivot(o, h, c, "甲", R=R, lag=lag, trace=True)
    tr = r["trace"]
    ev = {}
    for e in r["events"]:
        ev.setdefault(e["anchors"], e["T"])
    groups, cur = [], None

    def close(G):
        if G is not None:
            groups.append(G)

    for b in range(1, m):
        A = tr[b - 1]
        if A is None:
            continue
        if cur is None or cur["id"] != A:
            close(cur)
            p1, p2 = A
            cur = {"id": A, "first": int(p1), "conf": b - 1, "slope": (h[p2] - h[p1]) / (p2 - p1), "h1": h[p1],
                   "p1": int(p1), "S": None, "trig": ev.get(A), "end": None, "low": None}
        G = cur
        if b - G["conf"] > TM.LIFE:
            continue
        G["end"] = b
        lv = G["h1"] + G["slope"] * (b - G["p1"])
        lv1 = G["h1"] + G["slope"] * (b - 1 - G["p1"])
        if c[b] > lv and c[b - 1] <= lv1:
            continue                                      # 突破當根（＝ trendline_m 的事件）
        if G["S"] is None and (1.0 - near) * lv <= c[b] <= lv:
            G["S"] = b
            G["low"] = float(np.min(c[G["p1"]:b + 1]))
    close(cur)
    return {"groups": groups, "events": r["events"], "trace": tr}
