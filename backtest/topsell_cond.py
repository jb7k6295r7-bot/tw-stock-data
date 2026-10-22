# -*- coding: utf-8 -*-
"""頂部樣子（PREREG 大漲後頂部樣子當賣出訊號 seq1，sha e30036415fbbce81；裁定 seq443 §三 轉前瞻）——條件與報酬的【唯一函式來源】。
⛔ 頻率表 researchTopSell_freq.py（已 commit 6ff3dc9f54）的條件寫在 main() 迴圈內、無法 import，且不得改既有檔
   ⇒ 把同一套式子抽成本模組；topsell_fwd（前瞻）、researchTopSell_desc（單段描述）、topsell_fwd_check（fixture）一律 import 本檔，⛔ 不另寫。
   ⭐ 等價證明：topsell_fwd_check F1 用本檔函式＋同一份月底面板重跑 1984～2026 全部月底，逐列重現 resultsTopSell/freq/events.csv.gz
     （母體集合、入判、R36 旗標、本益比位置、T1a、T1b、T1、T2、T3、S、S12、進場旗標全同）才算過。
式子出處（讀法 T 標見 researchTopSell_freq 檔頭）：
  距一年高點 ＝ researchBigRun3 D3⑦（250 交易日窗、最後一個壞根那根起）；R36 ＝ freq T2；本益比 5 年（月底）位置 ＝ freq T3 T1a；
  近四季 EPS ＝ researchBigRun5 G5；ROE ＝ researchBigRun3 D3④（近 4 季 nip 單季和 ÷ 最新季 equity_parent，＞0）；產業中位 ＝ BigRun5 G4；
  集保 ＝ BigRun3 D3⑧（level 15 pct；月底前一交易日或更早 14 交易日內最近一筆；該月底需存活）；三值 ＝ freq T3。
報酬（裁定 seq443 准描述與前瞻；登錄 §四）：R ＝ 出場還原收盤 ÷ e 還原開盤 − 1；出場（長線三問 L12／PTH R2 同式）：
  窗尾 x ＝ e＋N 個曆月當天或之前最後一個交易日；(e, x] 有壞根 ⇒ 第一個壞根前一根收盤（強制）；最後有效 K 棒 ＜ x 且距資料尾 ≥ 5 交易日 ⇒ 末根收盤（下市）；
  其餘 ⇒ x 當天或之前最後一根收盤（到期）。腰斬 ★ ＝ 路徑（e 開盤、e～出場根各收盤）最大回落 ≤ −50%。成本兩邊各 0.585%（d 內抵銷，R淨 另列）。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

R36_MIN, HI_MIN, PE_Q, PE_WIN, PE_MINN, DEDUP = 3.0, -0.20, 0.80, 60, 36, 6
ALIVE, TD_LAG, HI_WIN = 20, 14, 249
EXCL_IND = {"其他", "綜合", "存託憑證", "ETF", ""}
COST = 0.00585
HALF = -0.50


# ═════════════ 價格位置 ═════════════
def _cut_after_bad(vb, k0, kk):
    """有效 K 棒區間 [k0, kk]：(k0, kk] 內有壞根 ⇒ 從最後一個壞根那根起。"""
    bb = np.flatnonzero(vb[k0 + 1:kk + 1])
    return (k0 + 1 + int(bb[-1]), True) if len(bb) else (k0, False)


def hi1y(vp, vc, vb, p):
    """距一年高點（p 必須是有效 K 棒）。"""
    kk = int(np.searchsorted(vp, p))
    k1, _ = _cut_after_bad(vb, int(np.searchsorted(vp, p - HI_WIN, "left")), kk)
    return float(vc[kk] / vc[k1:kk + 1].max() - 1)


def r36(vp, vc, vb, p, p36):
    """R36 ＝ c[p] ÷ (p36, p] 窗內最低（壞根截）；p36 ＜ 0 ⇒ 自第一根。回 (R36, 36 月完整且無壞根)。"""
    kk = int(np.searchsorted(vp, p))
    ks = int(np.searchsorted(vp, p36, "right")) if p36 >= 0 else 0
    full36 = bool(p36 >= 0 and vp[0] <= p36)
    ks2, trunc = _cut_after_bad(vb, ks, kk)
    return float(vc[kk] / vc[ks2:kk + 1].min()), bool(full36 and not trunc)


def in_pop(r36v, hi):
    """母體價格條件；距一年高點以 float32 比（面板存 float32，freq 即以面板值判）。"""
    return bool(r36v >= R36_MIN and np.isfinite(hi) and float(np.float32(hi)) >= HI_MIN)


def dedupe_take(k, last_taken):
    return (k - last_taken) >= DEDUP


# ═════════════ 訊號 ═════════════
def pe_pos(win):
    """win ＝ 第 k−59～k 個月底的本益比（含當月；虧損或缺 ＝ NaN）。"""
    w = np.asarray(win)
    v = w[-1]; ww = w[np.isfinite(w)]
    return float((ww <= v).mean()) if (np.isfinite(v) and len(ww) >= PE_MINN) else np.nan


def single(ytd, k):
    """年初累計 → 單季（Q1 不減）；researchLongPool.single 同式（dict／Series 皆可）。"""
    v = ytd.get(k, np.nan)
    if k % 4 == 0:
        return v
    pv = ytd.get(k - 1, np.nan)
    return v - pv if (np.isfinite(v) and np.isfinite(pv)) else np.nan


def eps4(eps_ytd, qk):
    if qk < 0 or eps_ytd is None:
        return np.nan
    q = [single(eps_ytd, j) for j in range(qk - 3, qk + 1)]
    return float(sum(q)) if np.isfinite(q).all() else np.nan


def roe4(nip_ytd, eqp, qk):
    if qk < 0 or nip_ytd is None or eqp is None:
        return np.nan
    n4 = [single(nip_ytd, j) if j in nip_ytd else np.nan for j in range(qk - 3, qk + 1)]
    e = eqp.get(qk, np.nan)
    return float(sum(n4) / e) if (np.isfinite(n4).all() and np.isfinite(e) and e > 0) else np.nan


def ind_median(vals):
    v = np.asarray(vals, float); v = v[np.isfinite(v)]
    return (float(np.median(v)) if len(v) else np.nan), int(len(v))


def tri(x, f):
    return bool(f(x)) if np.isfinite(x) else None


def kleene(*xs):
    if all(x is True for x in xs):
        return True
    if any(x is False for x in xs):
        return False
    return None


def signals(pos, e4, roe, med, td12):
    t1a = tri(pos, lambda z: z >= PE_Q)
    t1b = tri(e4, lambda z: z <= 0)
    t1 = True if (t1a is True or t1b is True) else (False if (t1a is False and t1b is False) else None)
    t2 = bool(roe < med) if (np.isfinite(roe) and np.isfinite(med)) else None
    t3 = tri(td12, lambda z: z < 0)
    return {"T1a": t1a, "T1b": t1b, "T1": t1, "T2": t2, "T3": t3, "S": kleene(t1, t2, t3), "S12": kleene(t1, t2)}


def lastok(arr, p, lag):
    """researchBigRun3.lastok 同式。"""
    if p < 0:
        return -1
    lo = max(0, p - lag)
    w = np.flatnonzero(np.isfinite(arr[lo:p + 1]))
    return lo + int(w[-1]) if len(w) else -1


def alive(vp, p):
    kk = int(np.searchsorted(vp, p, "right")) - 1
    return kk >= 0 and p - vp[kk] <= ALIVE


# ═════════════ 進場旗標與報酬 ═════════════
def window_end(cal, e, months):
    """e＋months 個曆月當天或之前最後一個交易日的位置；回 (x, 到期日曆日, 日曆已走完)。"""
    xd = cal[e] + pd.DateOffset(months=months)
    x = int(cal.searchsorted(xd, side="right")) - 1
    return x, xd, bool(xd <= cal[-1])


def entry_flags(C_row, BAD_row, TRD_row, UPL_row, e, n):
    if e >= n:
        return {"壞根(t,e]": None, "e無成交": None, "e開盤鎖漲停": None}
    return {"壞根(t,e]": bool(BAD_row[e]), "e無成交": bool(not TRD_row[e] or not np.isfinite(C_row[e])), "e開盤鎖漲停": bool(UPL_row[e])}


def ret_window(vp, vc, vb, o_e, e, x, cend):
    """單筆持有報酬（⛔ 只在描述件與到期前瞻呼叫）。vp／vc／vb ＝ 有效 K 棒位置、還原收盤、壞根旗標；o_e ＝ e 還原開盤。"""
    if not (np.isfinite(o_e) and o_e > 0):
        return None
    ke = int(np.searchsorted(vp, e))
    if ke >= len(vp) or vp[ke] != e:
        return None
    kx = int(np.searchsorted(vp, x, "right")) - 1
    nb = np.flatnonzero(vb[ke + 1:kx + 1])
    if len(nb):
        kout = ke + int(nb[0]); typ = "壞根強制"
    else:
        kout = kx
        typ = "下市" if (vp[-1] < x and (cend - vp[-1]) >= 5 and kx == len(vp) - 1) else "到期"
    path = np.r_[o_e, vc[ke:kout + 1]]
    mdd = float((path / np.maximum.accumulate(path) - 1).min())
    return {"R": float(vc[kout] / o_e - 1), "出場": typ, "出場位置": int(vp[kout]), "最大回落": mdd, "腰斬": bool(mdd <= HALF)}
