# -*- coding: utf-8 -*-
"""PREREG三重底 seq1【頻率表・乾跑】（台股策略線 單筆層登錄 sha 806f2cd9554b213d，2026-10-20 18:47；裁定 seq394 第 1 題、seq398 發號；
N_前段 ＋1；標籤上限「最多暫定」（主形狀已在型態全量 S2 測過））——回測線計算子代理。
⛔ 只數事件日期與個數、剔除計數、n_eff、曝險股日、條件成立比例、與已測項重疊；⛔ 不讀、不算、不存任何進場後的價格、報酬、持有天數、出場日
   （seq366 乾跑）。用到的價格只有 ≤ T 的日線開高低收量；T＋1 只判「有沒有成交、開盤是否鎖漲停」（快取 trd／o／upl）。
⛔ 不 commit、不改既有程式與結果夾；patterns_all（S2 偵測 detect_turns）、patterns_x（pivot_seq、W 底／頭肩底 detect_turn）、
   researchWR_freq（base、dedup_then_status、clean_window、run_freq）、researchAscTri_freq（load_world）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTripleBot_freq [--procs 2]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTripleBot_freq_check
輸出 backtest/resultsTripleBot/freq/：freq.json、freq.csv、freq_by_year.csv、events_<世界>.csv.gz、run.log

格（⭐ 判定只有 J；其餘只報、⛔ 不疊加）：
  M   主錨（描述）＝ 主要條件 ＝ PREREG型態全量 S2 三重底（patterns_all.detect_turns 原樣、⛔ 不另寫偵測）
  J   判定格 ＝ M ∧ 放量上攻（T 量 ÷ 前 20 日均量 ≥ 1.5 ∧ T 收紅）∧ 長期下跌（第一底收盤 ÷ 過去 250 日最高收盤 − 1 ≤ −20%）
  較嚴（各換掉 J 的一條、只報）：J_放量2倍、J_放量3倍、J_前5日均量1.5倍、J_跌30%、J_跌40%、J_120日線下>3月
  單條（只報）：M+放量、M+長期下跌
  量縮兩組（只報）：J_有量縮／J_沒量縮、M_有量縮／M_沒量縮（第三底量 ＜ 第一底量）

═══ 讀法（T 標；登錄沒寫清楚、執行者補的都在這裡；⛔ 在看任何本件數字之前寫死；★＝執行者定，〔 〕內為另一讀法）═══
 T1 世界、母體、壞根 ＝ researchAscTri_freq.load_world 原樣（UO／%R／海龜頻率表同）：主 ＝ rerun17 快照 edc6f8002f（2015-01-05～2026-09-24）；
    早年 ＝ ~/earlydata/eotc_f65bb03e11（2004-02-11～2014-12-31）；股票 ＝ ~/rluwork/world_{main,early}.pkl sids（UG.gate3 GATE_V2 ∩ 四碼、
    首碼 1～9、非 91xx、含已下市）；research11.load_bars ＜ 260 根不進。壞根 ＝ load_bars next_bad（缺口 ≥ 5 日 seq335、價格斷點、幽靈還原）
    ∪ ~/crashwork/bad_*.pkl ∪ 早年 researchAddOn.early_extra_bad（reduce_v2，seq341 §六）。
    T 的母體（登錄 §四「500 張閘在 T 判（T−20～T−1）」）＝ patterns.Frame.gate[T]（含 T 的 20 日都有成交 ∧ T−20～T−1 日均量 ≥ 500 張）∧ UG.pit_valid[T]。
 T2 偵測輸入 ＝ researchPatAll_freq.one_stock／detect_calendar 同一條：load_bars 的 df（＝ D.load_stock）還原收盤非缺值的有效 K 棒；
    r60 ＝ PA._rN(c, 60)；S2 ＝ PA.detect_turns(c, r60)["S02"]，去重 ＝ detect_all 同式（sorted(set)、同一 T 取第一個）；T、first 換回日曆位置。
    ⭐ 每檔斷言 偵測有效 K 棒 ＝ load_bars 有效 K 棒（不同 ⇒ 該檔記數、事件標「T不是有效K棒」）。
    三個底 L1、L2、L3 ＝ PX.pivot_seq(c, "L")（detect_turns 用的同一支）在事件組建立那根的 tail（T 當根或之前最近一次 tail 變動；
    T 當根先判舊組再換組 ⇒ T 當根有變動且 tail[0] ≠ first 時取前一次）；⭐ 斷言 tail[0] ＝ first 且 c[T] ＞ C_A（＝ 登錄 S2 突破式）。
 T3 剔除（每筆只記第一個原因；UO Q8／%R R7 同一套，加型態期間）：閘外(500張/pit) → 壞根(型態期間)（[first, T] 有效 K 棒之間有斷開：
    first 之後到 T 任一根是壞 K 棒；登錄「型態期間不跨壞根」）→ 壞根(T+1) → T+1無成交（下一根有效 K 棒不是日曆 T＋1、或無成交、或開盤缺值）
    → T+1開盤鎖漲停（快取 upl）。⛔ 不查 T＋1 以後的硬斷點（要出場日，正式跑再做）。
 T4 ★ 同檔 20 日內只算第一筆（同 C 組／PatAll Q2 的「先合併、再剔除」順序；researchWR_freq.dedup_then_status 原樣，間隔以有效 K 棒序號計）
    〔另一讀法：被剔除者不開合併窗 ⇒ 並列「保留_另一順序」〕；每格各自合併。
 T5 放量（seq394）：vr20 ＝ v[T] ÷ mean(v[T−20..T−1])（有效 K 棒、量 ＝ load_bars df volume；★ [T−20, T] 21 根需彼此相連（不跨壞根）、
    均量 ＞ 0、皆非缺值，否則不成立）；收紅 ＝ 還原 c[T] ＞ 還原 o[T]（同一還原因子 ⇒ ＝ 原始收 ＞ 開）。前 5 日均量版 vr5 同式（[T−5, T]）。
    判定：vr20 ≥ 1.5 ∧ 收紅；較嚴 vr20 ≥ 2、≥ 3；前 5 日均量版 vr5 ≥ 1.5 ∧ 收紅。
 T6 長期下跌：dd ＝ c[L1] ÷ max(c[s..L1]) − 1，s ＝ max(L1 − 249, L1 所在無壞根段的第一根)（★ 250 根含第一底當天；遇壞根只看壞根之後
    〔另一讀法：跨壞根照算〕；段內不足 60 根 ⇒ 不成立；不足 250 根照算並計數「250日窗被壞根或上市截短」）。判定 dd ≤ −20%；較嚴 −30%、−40%。
    ★「第一底前 120 日線下 ＞ 3 個月」＝ 截至 L1（含）連續收盤 ＜ MA120 的根數 ＞ 63（MA120 ＝ 含當根 120 根收盤平均，120 根需彼此相連）。
    ⭐ seq377 自查：主要條件已要求 r60[L1] ＜ 0 ⇒ 報「M 保留中 r60＜0 比例」（應 ＝ 100%）與「M 保留中 長期下跌 成立比例」（＝ 兩者同時成立比例）。
 T7 量縮（只描述）：v[L3] ＜ v[L1]（第三底當日量 ＜ 第一底當日量）；任一缺值 ⇒ 歸「沒量縮」並另計缺值筆數。
 T8 重疊（登錄 §四；件數 ÷ 本格保留數）：
    W 底 ＝ PX.detect_turn("w", c)（PREREGX 同版）事件 T；頭肩底 ＝ PX.detect_turn("hs", c)；型態 C 組 K2 ＝ W 底 ∧ v[L1] ＞ v[L2]（researchPatC_freq 同式）；
    同檔同日（T 相同）與同檔 ±20 根內（|ΔT| ≤ 20 有效 K 棒）兩種口徑；⛔ 對方不套剔除（偵測即算）。
    型態 C 組 K1 杯柄、型態 B 組 B1／B2 ＝ 讀已提交 resultsPatC/freq、resultsPatB/freq 同世界同段的事件檔（任何狀態，對方窗尾 ＝ 資料尾 − 20）同檔同日。
    頭肩底特查：「三底中間最深」（c[L2] ＜ c[L1] ∧ c[L2] ＜ c[L3]）筆數，其中同日也是頭肩底事件的筆數。
 T9 段（登錄 §三）：探索 [2017-03-02, 2021-12-30]｜確認 [2022-01-03, 資料尾前一日]｜主全窗 ＝ 探索＋確認｜早年 [2005 第一個交易日, 2014-12-31]
    （T 的日曆位置；researchWR_freq.run_freq 原樣）。n_eff ＝ min(保留數, 有保留事件的曆月數)；n_eff ＜ 30 ⇒「依構造不可判定、不計 N」。
    每年事件數、每檔每年次數（母體股年、有事件檔）＝ run_freq 原式。
 T10 S2 型態全量原標籤：讀 resultsPatAll/body/cells.csv（seq3 本體）S02 列的 原始／保留／n_eff／出口／結果（⛔ 不搬報酬欄）＋ resultsPatAll/freq.csv。
"""
from __future__ import annotations

import gzip
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchWR_freq as WR                  # noqa: E402  base、dedup_then_status、clean_window、run_freq（⛔ 只 import）
from backtest import patterns_all as PA                     # noqa: E402  S2 偵測（⛔ 只 import）
from backtest import patterns_x as PX                       # noqa: E402  pivot_seq、detect_turn（⛔ 只 import）

REG_SHA = "806f2cd9554b213d"
PAT_SHA = "b7b4a05af0341797"
OUT = "backtest/resultsTripleBot/freq"
VID = "S02"
DEDUP = 20
OVW = 20
DD_MINBARS = 60
ST_PAT = ["保留", "閘外(500張/pit)", "壞根(型態期間)", "壞根(T+1)", "T+1無成交", "T+1開盤鎖漲停", "T不是有效K棒", "合併掉"]
CELLS = {
    "M": "主錨（描述）：主要條件＝型態全量 S2 三重底",
    "J": "判定格：S2 ∧ 放量上攻(vr20≥1.5∧收紅) ∧ 長期下跌(距250日高≤−20%)",
    "J_放量2倍": "較嚴（只報）：放量改 vr20≥2",
    "J_放量3倍": "較嚴（只報）：放量改 vr20≥3",
    "J_前5日均量": "較嚴（只報）：放量改 前5日均量版 vr5≥1.5",
    "J_跌30%": "較嚴（只報）：長期下跌改 ≤−30%",
    "J_跌40%": "較嚴（只報）：長期下跌改 ≤−40%",
    "J_120日線下>3月": "較嚴（只報）：長期下跌改 第一底前連續收盤<MA120 >63根",
    "M+放量": "單條（只報）：S2 ∧ 放量上攻",
    "M+長期下跌": "單條（只報）：S2 ∧ 長期下跌−20%",
    "J_有量縮": "量縮組（只報）：J ∧ 第三底量<第一底量",
    "J_沒量縮": "量縮組（只報）：J ∧ 非（第三底量<第一底量）",
    "M_有量縮": "量縮組（只報）：S2 ∧ 第三底量<第一底量",
    "M_沒量縮": "量縮組（只報）：S2 ∧ 非（第三底量<第一底量）",
}
PRED = {
    "M": lambda f: True,
    "J": lambda f: f["vol15"] and f["dd20"],
    "J_放量2倍": lambda f: f["vol2"] and f["dd20"],
    "J_放量3倍": lambda f: f["vol3"] and f["dd20"],
    "J_前5日均量": lambda f: f["vol5"] and f["dd20"],
    "J_跌30%": lambda f: f["vol15"] and f["dd30"],
    "J_跌40%": lambda f: f["vol15"] and f["dd40"],
    "J_120日線下>3月": lambda f: f["vol15"] and f["below120"],
    "M+放量": lambda f: f["vol15"],
    "M+長期下跌": lambda f: f["dd20"],
    "J_有量縮": lambda f: f["vol15"] and f["dd20"] and f["shrink"],
    "J_沒量縮": lambda f: f["vol15"] and f["dd20"] and not f["shrink"],
    "M_有量縮": lambda f: f["shrink"],
    "M_沒量縮": lambda f: not f["shrink"],
}


# ═════════════ 共用小工具（圓弧底件 import） ═════════════
def seg_start(bad):
    """ss[k] ＝ k 所在無壞根段的第一根（段首 ＝ 第 0 根或壞 K 棒）。"""
    n = len(bad); a = np.where(np.asarray(bad, bool), np.arange(n), 0); a[0] = 0
    return np.maximum.accumulate(a)


def vol_ratio(v, bad, k, n):
    """T5：v[k] ÷ mean(v[k−n..k−1])；[k−n, k] 需相連、非缺值、均量 ＞ 0。"""
    if k < n or not _clean(bad, k - n, k):
        return np.nan
    w = v[k - n:k]
    if not (np.isfinite(w).all() and np.isfinite(v[k])):
        return np.nan
    m = float(w.mean())
    return float(v[k] / m) if m > 0 else np.nan


def _clean(bad, a, b):
    """[a, b] 有效 K 棒彼此相連（a 之後到 b 沒有壞 K 棒）。"""
    if a < 0:
        return False
    return not bool(np.asarray(bad[a + 1:b + 1], bool).any())


def longdown(c, ss, kb):
    """T6：回 (dd, 截短?)；不足 DD_MINBARS 根 ⇒ (nan, True)。"""
    s = max(kb - 249, int(ss[kb]))
    if kb - s + 1 < DD_MINBARS:
        return np.nan, True
    return float(c[kb] / np.max(c[s:kb + 1]) - 1.0), bool(kb - s + 1 < 250)


def below_run(c, bad, kb, n=120):
    """T6：截至 kb（含）連續收盤 ＜ MA_n 的根數（MA 窗需相連）。"""
    ma = pd.Series(c).rolling(n, min_periods=n).mean().to_numpy(float)
    okw = WR.clean_window(bad, n)
    r = 0; j = kb
    while j >= 0 and okw[j] and np.isfinite(ma[j]) and c[j] < ma[j]:
        r += 1; j -= 1
    return r


def st_pattern(X, k, kf):
    """T3：收盤判、T＋1 開盤進，加型態期間不跨壞根。"""
    idx, nb, bad, gate, PV, TRD, O, UPL, n0 = (X[z] for z in ("idx", "nb", "bad", "gate", "PV", "TRD", "O", "UPL", "n0"))
    T = int(idx[k]); e = T + 1
    if not (gate[T] and PV[T]):
        return "閘外(500張/pit)"
    if not _clean(bad, kf, k):
        return "壞根(型態期間)"
    if k + 1 < nb and bad[k + 1]:
        return "壞根(T+1)"
    if not (k + 1 < nb and idx[k + 1] == e and e < n0 and TRD[e] and np.isfinite(O[e]) and O[e] > 0):
        return "T+1無成交"
    if UPL[e]:
        return "T+1開盤鎖漲停"
    return "保留"


def cells_from_feats(X, feats, cells, pred, extra_keys):
    """每格各自 T4 合併再剔除。feats：{k: dict(kf, ...)}。"""
    sid = X["sid"]; idx = X["idx"]; cal = X["cal"]
    EV = {}
    for cell in cells:
        ks = sorted(k for k, f in feats.items() if pred[cell](f))
        st, alt = WR.dedup_then_status(ks, lambda k: (feats[k]["why0"] or st_pattern(X, k, feats[k]["kf"])), win=DEDUP)
        EV[cell] = [{"sid": sid, "T": int(idx[k]), "k": int(k), "first": str(cal[idx[feats[k]["kf"]]].date()),
                     **{z: feats[k][z] for z in extra_keys}, "st": st[k], "alt保留": bool(k in alt)} for k in ks]
    return EV


def turn_sets(c, v):
    """T8：W 底、頭肩底、C 組 K2 的事件 T（有效 K 棒序號）。"""
    w = PX.detect_turn("w", c)["events"]; hs = PX.detect_turn("hs", c)["events"]
    W = np.array(sorted({e["T"] for e in w}), np.int64)
    K2 = np.array(sorted({e["T"] for e in w if np.isfinite(v[e["pts"]["L1"]]) and np.isfinite(v[e["pts"]["L2"]])
                          and v[e["pts"]["L1"]] > v[e["pts"]["L2"]]}), np.int64)
    HS = np.array(sorted({e["T"] for e in hs}), np.int64)
    return {"W底": W, "頭肩底": HS, "C組K2": K2}


def ov_flags(k, sets):
    out = {}
    for nm, arr in sets.items():
        out[f"同日_{nm}"] = bool(np.isin(k, arr))
        out[f"±{OVW}_{nm}"] = bool(((arr >= k - OVW) & (arr <= k + OVW)).any())
    return out


def recover_tail(seq, bs, T, L1, c):
    """T2：事件組的 (L1, L2, L3)。"""
    j = int(np.searchsorted(bs, T, "right")) - 1
    for jj in (j, j - 1):
        if jj < 0:
            continue
        if jj == j - 1 and bs[j] != T:
            break
        tail = seq[int(bs[jj])]
        if len(tail) == 3 and tail[0] == L1:
            l1, l2, l3 = tail
            cA = max(float(np.max(c[l1:l2 + 1])), float(np.max(c[l2:l3 + 1])))
            if c[T] > cA:
                return l1, l2, l3
    raise SystemExit(f"⛔ 三重底 T={T} first={L1} 找不到對應 tail")


# ═════════════ 逐股 ═════════════
def stock_job(a):
    wn, sid = a
    X = WR.base(wn, sid)
    if X is None:
        return sid, None
    df = X["df"]; idx = X["idx"]; nb = X["nb"]; bad = X["bad"]; o = X["o"]; c = X["c"]
    v = pd.to_numeric(df["volume"], errors="coerce").to_numpy(float)[idx]
    cf = df["close"].to_numpy(float); bars = np.flatnonzero(np.isfinite(cf))
    bars_eq = bool(len(bars) == nb and (bars == idx).all())
    if not bars_eq:                                       # T2：偵測 K 棒 ≠ load_bars K 棒 ⇒ 該檔不偵測、記數
        return sid, {"ev": {cell: [] for cell in CELLS}, "expo": X["expo"], "nb": nb, "bars_eq": False, "nS2": 0, "n_trunc": 0}
    cd = cf[bars]
    r60 = PA._rN(cd, PA.R60)
    ev, seen = [], set()
    for e in sorted(set(PA.detect_turns(cd, r60)[VID])):
        if e[0] not in seen:
            seen.add(e[0]); ev.append(e)
    seq = PX.pivot_seq(cd, "L"); bs = np.array(sorted(seq), np.int64)
    ss = seg_start(bad)
    sets = turn_sets(c, v)
    feats = {}
    n_trunc = 0
    for (Tb, fb) in ev:
        L1, L2, L3 = recover_tail(seq, bs, int(Tb), int(fb), cd)
        k = int(Tb); kf = int(fb)
        if not (r60[L1] < 0):
            raise SystemExit(f"⛔ {sid} S2 r60[L1] 不 < 0")
        vr20 = vol_ratio(v, bad, k, 20); vr5 = vol_ratio(v, bad, k, 5)
        red = bool(c[k] > o[k])
        dd, trunc = longdown(c, ss, L1); n_trunc += int(trunc and np.isfinite(dd))
        b120 = below_run(c, bad, L1)
        sh_ok = np.isfinite(v[L3]) and np.isfinite(v[L1])
        f = {"kf": kf, "why0": None, "L1": str(X["cal"][idx[L1]].date()), "L2": str(X["cal"][idx[L2]].date()),
             "L3": str(X["cal"][idx[L3]].date()),
             "vr20": round(vr20, 4) if np.isfinite(vr20) else None, "vr5": round(vr5, 4) if np.isfinite(vr5) else None, "收紅": red,
             "dd250": round(dd, 4) if np.isfinite(dd) else None, "線下根數": int(b120), "r60_L1": round(float(r60[L1]), 4),
             "vol15": bool(np.isfinite(vr20) and vr20 >= 1.5 and red), "vol2": bool(np.isfinite(vr20) and vr20 >= 2 and red),
             "vol3": bool(np.isfinite(vr20) and vr20 >= 3 and red), "vol5": bool(np.isfinite(vr5) and vr5 >= 1.5 and red),
             "dd20": bool(np.isfinite(dd) and dd <= -0.20), "dd30": bool(np.isfinite(dd) and dd <= -0.30),
             "dd40": bool(np.isfinite(dd) and dd <= -0.40), "below120": bool(b120 > 63),
             "shrink": bool(sh_ok and v[L3] < v[L1]), "shrink缺值": bool(not sh_ok),
             "L2最深": bool(cd[L2] < cd[L1] and cd[L2] < cd[L3]), **ov_flags(k, sets)}
        feats[k] = f
    keys = ["L1", "L2", "L3", "vr20", "vr5", "收紅", "dd250", "線下根數", "r60_L1", "vol15", "dd20", "shrink", "shrink缺值", "L2最深",
            *[z for z in next(iter(feats.values())).keys() if z.startswith(("同日_", "±"))]] if feats else []
    EV = cells_from_feats(X, feats, CELLS, PRED, keys)
    return sid, {"ev": EV, "expo": X["expo"], "nb": nb, "bars_eq": bars_eq, "nS2": len(ev), "n_trunc": n_trunc}


# ═════════════ 段附加：條件比例、重疊 ═════════════
_EXT: dict = {}


def wn_sg(cal, p0, p1):
    wn = "早年" if cal[-1].year <= 2014 else "主"
    sg = next(s for s, w in WR._G[wn]["win"].items() if w == (p0, p1))
    return wn, sg


def ext_set(wn, sg, path):
    key = (wn, sg, path)
    if key not in _EXT:
        f = path.format(wn=wn, sg=sg)
        _EXT[key] = set(zip(*[pd.read_csv(f, dtype={"sid": str}, usecols=["sid", "T"])[z] for z in ("sid", "T")])) if os.path.exists(f) else None
    return _EXT[key]


EXT_FILES = {"C組K1杯柄": "backtest/resultsPatC/freq/events_{wn}_{sg}_K1.csv.gz",
             "B組B1三內向上": "backtest/resultsPatB/freq/events_{wn}_{sg}_B1.csv.gz",
             "B組B2三外向上": "backtest/resultsPatB/freq/events_{wn}_{sg}_B2.csv.gz"}


def overlap_block(kept, cal, wn, sg, names):
    n = len(kept); out = {"保留": n}
    if not n:
        return out
    for nm in names:
        for pre in ("同日_", f"±{OVW}_"):
            x = sum(1 for e in kept if e.get(pre + nm)); out[pre + nm] = x; out[pre + nm + "_比例"] = round(x / n, 4)
    for nm, path in EXT_FILES.items():
        S = ext_set(wn, sg, path)
        if S is None:
            out["同日_" + nm] = "（無事件檔）"; continue
        x = sum(1 for e in kept if (e["sid"], str(cal[e["T"]].date())) in S)
        out["同日_" + nm] = x; out["同日_" + nm + "_比例"] = round(x / n, 4)
    return out


def seg_extra(ok, p0, p1, cal):
    wn, sg = wn_sg(cal, p0, p1)
    kp = {cell: [e for r in ok.values() for e in r["ev"][cell] if p0 <= e["T"] <= p1 and e["st"] == "保留"] for cell in ("M", "J")}
    M, J = kp["M"], kp["J"]
    nM = len(M)
    r = lambda x: round(x / nM, 4) if nM else None
    out = {"seq377自查": {"M保留": nM, "r60<0(主要條件)": sum(1 for e in M if e["r60_L1"] < 0),
                       "長期下跌−20%成立(＝與r60<0同時成立)": sum(1 for e in M if e["dd20"]), "比例": r(sum(1 for e in M if e["dd20"])),
                       "放量1.5倍收紅成立": sum(1 for e in M if e["vol15"]), "放量比例": r(sum(1 for e in M if e["vol15"])),
                       "J÷M": r(len(J))},
           "量縮缺值筆數(M保留)": sum(1 for e in M if e["shrink缺值"]),
           "頭肩底特查(M保留)": {"三底中間最深": sum(1 for e in M if e["L2最深"]),
                            "其中同日也是頭肩底": sum(1 for e in M if e["L2最深"] and e.get("同日_頭肩底"))},
           "重疊_J": overlap_block(J, cal, wn, sg, ("W底", "頭肩底", "C組K2")),
           "重疊_M": overlap_block(M, cal, wn, sg, ("W底", "頭肩底", "C組K2"))}
    return out


def diag(ok):
    return {"有效K棒": int(sum(r["nb"] for r in ok.values())), "偵測K棒≠load_bars K棒檔數": int(sum(1 for r in ok.values() if not r["bars_eq"])),
            "S2偵測總數(全期)": int(sum(r["nS2"] for r in ok.values())),
            "長期下跌250日窗被壞根或上市截短(全期偵測)": int(sum(r["n_trunc"] for r in ok.values()))}


def patall_labels(vid):
    """T10：型態全量 seq3 原標籤與事件數（⛔ 不搬報酬欄）。"""
    cc = pd.read_csv("backtest/resultsPatAll/body/cells.csv", dtype={"vid": str})
    cols = ["H", "身分", "原始", "合併後", "剔除_硬斷點", "剔除_T+1停牌", "剔除_T+1開盤漲停", "剔除_T+1開盤跌停", "保留", "n_eff", "出口", "結果"]
    rows = cc.loc[cc["vid"] == vid, cols]
    fq = pd.read_csv("backtest/resultsPatAll/freq.csv", dtype={"vid": str})
    fr = fq.loc[fq["vid"] == vid].iloc[0]
    return {"出處": f"PREREG型態全量 seq3（sha {PAT_SHA}）resultsPatAll/body/cells.csv、resultsPatAll/freq.csv",
            "母體與口徑": "gate3 v1、無 500 張閘、硬斷點查到 T＋H、判定窗 2017-03-02～2026-08-24（與本件不同；只供對照）",
            "本體逐H": [{k: (None if (isinstance(v, float) and not np.isfinite(v)) else (v.item() if hasattr(v, "item") else v))
                        for k, v in r.items()} for _, r in rows.iterrows()],
            "頻率階段": {"保留_H20": int(fr["保留_H20"]), "相異檔數_H20": int(fr["相異檔數_H20"]), "n_eff上限_H20": int(fr["n_eff上限_H20"]),
                     "每檔每年_H20": float(fr["每檔每年_H20"]), "保留_H60": int(fr["保留_H60"]), "n_eff上限_H60": int(fr["n_eff上限_H60"])}}


def finalize(out_dir, vid, judge_cell, base_cell, extra=None):
    """run_freq 寫完後補：型態全量原標籤、判斷摘要。"""
    p = os.path.join(out_dir, "freq.json")
    J = json.load(open(p, encoding="utf-8"))
    J[f"{vid}型態全量原標籤"] = patall_labels(vid)
    jd = {}
    for wn, sgs in (("主", ("探索", "確認", "主全窗")), ("早年", ("早年",))):
        for sg in sgs:
            s = J["世界"][wn]["段"][sg]
            jd[f"{wn}/{sg}"] = {"判定格n": s[judge_cell]["事件數(保留)"], "判定格n_eff": s[judge_cell]["n_eff"],
                                "判斷": s[judge_cell]["判斷"], "主錨n": s[base_cell]["事件數(保留)"], "主錨n_eff": s[base_cell]["n_eff"]}
    J["判斷摘要"] = jd
    if extra:
        J.update(extra)
    json.dump(J, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)


def main():
    WR.run_freq({"sha": REG_SHA, "out": OUT, "cells": CELLS, "job": stock_job, "ev_cells": tuple(CELLS),
                 "title": "PREREG三重底 seq1 頻率表乾跑（⛔ 未讀、未算任何進場後價格、報酬、持有天數、出場日）",
                 "ruling": "seq394 第 1 題、seq398 發號；N_前段 ＋1；標籤最多暫定；n_eff ＜ 30 ⇒ 依構造不可判定、不計 N；乾跑",
                 "doc": __doc__, "seg_extra": seg_extra, "diag": diag, "st_all": ST_PAT})
    lim = "--limit" in sys.argv
    finalize(OUT if not lim else os.path.join(OUT, "_try"), VID, "J", "M")


if __name__ == "__main__":
    main()
