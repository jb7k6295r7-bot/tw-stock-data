# -*- coding: utf-8 -*-
"""產業挑法的好壞比例分佈【有大漲前例＋還沒漲過（＋營收轉強），之後 3 年結果分幾段】事件層描述 seq1【頻率表・⛔ 不附報酬】
（台股策略線 登錄 sha 0e149f0996373817，2026-10-23 20:22；裁定 seq463 §二 核：描述、⛔ 不判定、不計 N；先交頻率表、全部描述欄先乾跑）——回測線計算子代理。
⛔ 只數事件、n_eff、重複窗、A／B／轉強成立率、走得完、壞根、下市、分產業；⛔ 不讀、不算、不存任何進場後報酬、倍數（seq366）。
   用到的價格只有 ≤ 判日（可用日前一交易日 A−1）的還原收盤（只用來判 A、B 布林，⛔ 不存數值）；進場日以後只用「有效 K 棒／壞根／下市」旗標。
⛔ 不 commit、不改既有檔；researchRevTurn_freq（ensure_data、prices、rev_table、avail_pos、mnum、qd、jdef）、researchTriple_freq（make_events、segof、market_map）、
   researchIndMom_freq（reg_check、entry_flag、load_pit）⛔ 只 import。轉強 ＝ bigrun_monthly.rev_metrics 的 up（經 researchRevTurn_freq.rev_table），⛔ 不寫第二份。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPickDist_freq [--procs 3] [--out DIR]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPickDist_freq_check
輸出 backtest/resultsPickDist/freq/：freq.json、freq_段.csv、base_段.csv、hist_days.csv、industry.csv、yearly.csv、equiv.csv、
      events_甲.csv.gz、events_乙.csv.gz、events_丙.csv.gz、events_丁.csv.gz（逐事件旗標，⛔ 無報酬、無價格、無倍數）、run.log；
      逐事件位置（正式跑用）另存 ~/pkdwork/events_<sha12>.pkl（repo 外）。

═══ 讀法（P 標；登錄沒寫清楚、執行者補的都在這裡；⛔ 在看任何本件數字之前寫死於 2026-10-24（台北）；★＝執行者定，〔 〕內為另一讀法）═══
 P0 資料：tw-stock-data origin/main ★ 釘 9b0e9882572c（＝「3 年 3 倍命中率」頻率表／正式跑同一版，重疊率同口徑；〔另一讀法：最新 main〕）；
    價格 ＝ researchRevTurn_freq.prices（rerun17 H2D edc6f 2015-01-05～2026-09-24 ＋ 早年 eotc 2004-02-11～2014-12-31 合併日曆；四碼普通股（已排 DR、ETF、
    權證；面板 UG.gate3）、含已下市；還原收盤；壞根 ＝ 缺口 ≥5 日（seq335）∪ 斷點 ∪ 幽靈還原 ∪ crashwork ∪ 早年 reduce_v2；exright open_base（seq412）上市＋上櫃）。
    月營收轉強 ＝ researchRevTurn_freq.rev_table（tag trp 快取，＝ 3 倍命中率同一份）的 up（＝ 甲 accel ≥ 0.05 ∨ 乙 首次創 24 月新高；bigrun_monthly.rev_metrics 原值）。
 P1 判日：每月月營收可用日 A ＝ researchRevTurn_freq.avail_pos（次月 10 日後第一個交易日；2026-01 期起 15 日）；期別 P ＝ A 對應的營收期。
    ★ 價格判日 p1 ＝ A−1（登錄 §一「判日＝可用日前一交易日」；A、B、500 張閘一律用 ≤ A−1 的還原收盤）〔另一讀法：A 收盤〕；轉強用期別 P（A 當天已可用）。
    進場 e ＝ A＋1 開盤（＝ 3 倍命中率 T1）。進場剔除 ＝ researchIndMom_freq.entry_flag(t＝A−1, e)（★ 檢查 (A−1, e] 壞根，因判日在 A−1）→ e 無成交 → e 開盤鎖漲停。
 P2 母體：判日 A−1 過 500 張閘（面板 G[A−1]：含判日 20 日都有成交 ∧ 20 日均量 ≥ 500 張 ∧ pit_valid）；無閘版（描述）★ ＝ A−1 有有效 K 棒。
 P3 A 有大漲前例：存在日曆位置 t0 ＜ t1 ≤ p1、t1 − t0 ≤ 750（合併日曆交易日），還原收盤(t1) ≥ 3 × 還原收盤(t0)，⛔ 只用 ≤ p1 的資料；
    ★ (t0, t1] 內有壞根 ⇒ 這一對不算（硬斷點兩側價格不可相比；t0 可以是壞根當根）；只看有效 K 棒。實作：每檔逐段（壞根切段）rolling 750 位置的最低收盤（不含當根），
    收盤 ≥ 3 × 該最低 ⇒ t1 為「命中日」；A(p1) ＝ 最早命中日 ≤ p1（一旦成立之後永遠成立：登錄「判日前任一」）。
    ★ A 可判（歷史夠長）＝ 第一根有效 K 棒 ≤ p1 − 750（至少有一個完整 750 日窗）；A 不可判者照式算（可能為真），⛔ 不剔除，件數照報。
    描述欄（⛔ 不入臂）：A近750 ＝ 只看 [p1−750, p1] 內的 t0、t1（＝ 美股版口徑），報與 A 的一致率。
    判日前可用歷史天數 ＝ p1 − 第一根有效 K 棒（日曆位置）；分年分佈照報（2008～2010 A 偏少）。
 P4 B 還沒漲過：c[p1] ＜ 2 × min(收盤[p1−499 … p1]) ∧ c[p1] ≤ 0.85 × max(收盤[p1−499 … p1])（★ 500 個日曆位置、含判日〔另一讀法：不含判日 [p1−500, p1−1]；
    兩式只在判日本身是窗內極值時才可能不同，且兩條結果相同〕）。★ B 可判 ＝ 第一根有效 K 棒 ≤ p1−499 且 (p1−499, p1] 無壞根（窗全在同一段）；不可判 ⇒ B 為假（件數照報）。
 P5 轉強：期別 P 的 up（rev_table 有該檔該期列）；無列 ⇒ 轉強不可判 ⇒ 為假（件數照報「轉強可判」）。
 P6 臂：甲 A∧B｜乙 A∧B∧轉強｜丙 B∧¬A｜丁 全母體（判日過閘且 e 可進場的全部股）。
    甲乙丙：★ 同檔同臂 36 個月內只取第一次 ＝ 過閘訊號依期別排序，與上一個「取用」期別相差 ＜ 36 個月 ⇒ 不取（researchTriple_freq.make_events 原式；
    取用不論 e 可不可進場）；★ 去重只從第一個入段判日（A ≥ 2008-01）起算、兩段連續不重設〔另一讀法：從 2005 起算〕。
    ★ 丁 不去重（登錄「判日當月全部可進場股」字面；每月一列）〔另一讀法：同 36 月去重，件數另報 equiv.csv〕。
 P7 段（依 A）：早段 2008-01～2014-12｜後段 2015-01～2023-08；2023-09 起 ＝ 段外（750 日走不完，只報件數）。
    走得完 ＝ e ＋ 750 ≤ 資料尾（2026-09-24，合併日曆位置）。主格 ＝ e 可進場 ∧ 750 走得完。n_eff ＝ 主格事件的判日月數（月分群有效月數）；＜ 24 ⇒ 標「樣本不足」。
    壞根截斷 ＝ (e, e＋750] 有壞根；下市 ＝ 最後有效 K 棒 ＜ e＋750 且距資料尾 ≥ 5 日（處理留正式跑：截在第一個壞根前一根／以最後收盤計）。
 P8 分產業 ＝ industry_pit 在 A（researchIndMom_freq.load_pit，含 fallback；無類別 ⇒「無類別」）；上市／上櫃 ＝ meta stocks／delisted 的 market。
 P9 與 3 倍命中率 S1 重疊：resultsTriple/freq/events_S1.csv.gz（36 月去重、過閘）以（代號, 期別）比；另報 ±12 個月內有 S1 事件的比例。
    ⭐ 本件 A 與 3 倍命中率的差別：3 倍命中率的訊號 S1 是【月營收】甲∧乙（加速 ≥5 點且首次創 24 月新高），「3 倍」是【進場後】750 日內最高收盤 ≥ 3 × 進場開盤（結果變數）；
       本件 A 是【判日前】價格條件：任一 750 日內某收盤 ≥ 3 × 更早某收盤（不錨定進場價、不錨定低點、不看營收），是條件不是結果。
 P10 等價／退化（seq377）：甲 ⊂ 丁（甲÷丁 列比）；B 成立率（是否幾乎總成立）；A 成立率；乙÷甲；轉強率；甲 ∩ 丙 ＝ 0（依構造）；A近750 vs A 一致率；
    丁去重版件數；甲 ∩ S1。
 P11 必附（結果句）：「C（主題燈）沒有回測，只測了『有大漲前例＋還沒漲過』」「事件重疊、CI 偏窄」「不是選股規則」。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import pickle
import sys
import time
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchRevTurn_freq as RT             # noqa: E402  價格面板、轉強（⛔ 只 import）
from backtest import researchTriple_freq as TP              # noqa: E402  make_events、segof、market_map
from backtest import researchIndMom_freq as IMF             # noqa: E402  reg_check、entry_flag、load_pit

REG_SHA = "0e149f0996373817"
RUL = "seq463"
SHA_PIN = "9b0e9882572c438ec25771031658ddc701ca6171"
OUT = "backtest/resultsPickDist/freq"
TW = os.path.expanduser("~/pkdwork")
DEDUP_M = 36
HJ = 750
WA = 750
WB = 500
NEFF_MIN = 24
SEGS = [("早段", "2008-01-01", "2014-12-31"), ("後段", "2015-01-01", "2023-08-31")]
FIRST_A = "2008-01-01"
ARMS = ["甲", "乙", "丙", "丁"]
S1_EV = "backtest/resultsTriple/freq/events_S1.csv.gz"
NOTES = ["頻率表、未算任何報酬、倍數（seq366）",
         "C（主題燈）沒有回測，只測了『有大漲前例＋還沒漲過』",
         "事件重疊（750 日窗互相重疊、同月多檔）⇒ 月分群 CI 偏窄，只描述",
         "不是選股規則；⛔ 不改小部位候選、⛔ 不當買進規則",
         "產業挑候選時用未還原價，本件一律還原（裁定 seq462 §二）",
         "早年可回看歷史短（2004-02 起；上櫃 2007-07 起）⇒ 2008～2010 A 偏少，見 hist_days.csv",
         "2015～2018 下市 58 家月營收補不回（存活者偏差，影響乙臂轉強）",
         "價格面板 ＝ rerun17 H2D（edc6f，資料尾 2026-09-24）；月營收、產業、exright ＝ tw-stock-data 9b0e9882572c（＝ 3 倍命中率同一版）"]
LOG: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


RT.log = log


# ═════════════ A、B（P3、P4）═════════════
def hit_first(PX):
    """每檔最早「命中日」（日曆位置；無 ⇒ 大數）與每個位置是否命中（稀疏：sid -> 命中位置陣列）。"""
    C, BAD = PX["C"], PX["BAD"]; N, NC = C.shape
    first = np.full(N, 10 ** 9, dtype=np.int64); hits = {}
    for i in range(N):
        vp = PX["VP"][i]
        if len(vp) < 2:
            continue
        starts = sorted(set([int(vp[0])] + [int(p) for p in np.flatnonzero(BAD[i]) if p >= vp[0]]))
        hp = []
        for k, s in enumerate(starts):
            e = starts[k + 1] if k + 1 < len(starts) else NC
            sub = C[i, s:e]
            if np.isfinite(sub).sum() < 2:
                continue
            lo = pd.Series(sub).rolling(WA, min_periods=1).min().shift(1).to_numpy(float)
            ok = np.isfinite(sub) & np.isfinite(lo) & (lo > 0)
            h = np.flatnonzero(ok & (sub >= 3.0 * np.where(ok, lo, np.inf)))
            if len(h):
                hp.append(h + s)
        if hp:
            hh = np.concatenate(hp); hits[i] = hh; first[i] = int(hh.min())
    return first, hits


def a_recent(PX, i, p1):
    """A近750（描述）：t0、t1 都在 [p1−750, p1]、(t0, t1] 無壞根。"""
    a = max(0, p1 - WA)
    sub = PX["C"][i, a:p1 + 1].copy(); bd = PX["BAD"][i, a:p1 + 1]
    seg = np.cumsum(bd)
    for k in np.unique(seg[np.isfinite(sub)]):
        m = (seg == k)
        s = sub[m]
        lo = pd.Series(s).cummin().shift(1).to_numpy(float)   # NaN 被 cummin 跳過
        ok = np.isfinite(s) & np.isfinite(lo) & (lo > 0)
        if (ok & (s >= 3.0 * np.where(ok, lo, np.inf))).any():
            return True
    return False


def b_at(PX, i, p1, fv):
    """(B可判, B)。"""
    a = p1 - (WB - 1)
    if a < 0 or fv > a:
        return False, False
    if PX["CB"][i, p1] - PX["CB"][i, a] > 0:
        return False, False
    c = PX["C"][i, p1]
    if not np.isfinite(c):
        return False, False
    w = PX["C"][i, a:p1 + 1]
    mn, mx = np.nanmin(w), np.nanmax(w)
    return True, bool(c < 2.0 * mn and c <= 0.85 * mx)


def segname(d):
    return TP.segof(d, SEGS + [("段外", "2023-09-01", "2099-12-31")])


# ═════════════ 主程式 ═════════════
def build(procs, sha_req=SHA_PIN):
    """回 dict：base（過閘、無閘股月表）、events（各臂）、PX 等。check 與正式跑共用。"""
    t0 = time.time()
    sha, DN, MD = RT.ensure_data(sha_req); log(f"[資料] origin/main {sha}｜{DN}")
    PX = RT.prices(sha, DN, procs)
    CAL, SIDS, ix = PX["CAL"], PX["SIDS"], PX["ix"]; CEND = len(CAL) - 1
    RV, rdiag = RT.rev_table(MD, SIDS, procs, tag=TP.RV_TAG)
    log(f"[月營收] {rdiag}")
    MKT = TP.market_map(DN)
    pit = IMF.load_pit(DN)
    periods = sorted(RV["period"].unique())
    APOS = RT.avail_pos(CAL, periods)
    UP = {(s, p): bool(u) for s, p, u in zip(RV["sid"], RV["period"], RV["up"])}
    FV = np.array([int(v[0]) if len(v) else 10 ** 9 for v in PX["VP"]])
    first, hits = hit_first(PX)
    log(f"[A] 命中檔 {int((first < 10 ** 9).sum())}／{len(SIDS)}｜{time.time() - t0:.0f}s")
    months = [(P, APOS[P]) for P in periods if 1 <= APOS[P] <= CEND and str(CAL[APOS[P]].date()) >= FIRST_A]
    G = PX["G"]; VALID = np.isfinite(PX["C"])
    rows = []
    for P, A_ in months:
        p1 = A_ - 1
        seg = segname(CAL[A_])
        for i in np.flatnonzero(VALID[:, p1]):
            i = int(i); sid = SIDS[i]
            bj, b = b_at(PX, i, p1, FV[i])
            up = UP.get((sid, P))
            rows.append((sid, i, P, A_, seg, bool(G[i, p1]), bool(first[i] <= p1), bool(FV[i] <= p1 - WA), bj, b,
                         up is not None, bool(up), int(p1 - FV[i])))
    B = pd.DataFrame(rows, columns=["sid", "i", "期別", "A", "段", "過閘", "A成立", "A可判", "B可判", "B", "轉強可判", "轉強", "歷史天數"])
    B["mk"] = [RT.mnum(p) for p in B["期別"]]
    log(f"[股月] 有效 {len(B)}｜過閘 {int(B['過閘'].sum())}｜月 {len(months)}｜{time.time() - t0:.0f}s")
    # A近750（描述；只過閘股月）
    g = B[B["過閘"]]
    B["A近750"] = False
    B.loc[g.index, "A近750"] = [a_recent(PX, int(i), int(A_) - 1) for i, A_ in zip(g["i"], g["A"])]
    log(f"[A近750] 完成｜{time.time() - t0:.0f}s")

    memo = {}

    def eflag(i, A_):
        k = (i, A_)
        if k not in memo:
            memo[k] = IMF.entry_flag(PX, i, A_ - 1, A_ + 1) if A_ + 1 <= CEND else "e超出資料尾"
        return memo[k]

    masks = {"甲": B["A成立"] & B["B"], "乙": B["A成立"] & B["B"] & B["轉強"], "丙": B["B"] & ~B["A成立"]}
    EV = {}; RS = {}; EVng = {}; RSng = {}
    for arm, m in masks.items():
        for tag, gm in (("g", B["過閘"]), ("ng", pd.Series(True, index=B.index))):
            d = B[m & gm]
            cands = [(s, int(i), int(A_), int(mk), P) for s, i, A_, mk, P in zip(d["sid"], d["i"], d["A"], d["mk"], d["期別"])]
            kept, rs = TP.make_events(cands, CEND, lambda i, A_: True)
            rs["訊號股月(去重前)"] = len(cands)
            (EV if tag == "g" else EVng)[arm] = kept; (RS if tag == "g" else RSng)[arm] = dict(rs)
    # 丁：過閘全部股月（不去重）
    d = B[B["過閘"]]
    EV["丁"] = [(s, int(i), int(A_), int(mk), P) for s, i, A_, mk, P in zip(d["sid"], d["i"], d["A"], d["mk"], d["期別"])]
    d = B
    EVng["丁"] = [(s, int(i), int(A_), int(mk), P) for s, i, A_, mk, P in zip(d["sid"], d["i"], d["A"], d["mk"], d["期別"])]
    Bi = B.set_index(["sid", "期別"])

    def ev_table(arm, K):
        out = []
        for sid, i, A_, mk, P in K:
            e = A_ + 1; fl = eflag(i, A_)
            x = e + HJ; walk = bool(x <= CEND)
            r = Bi.loc[(sid, P)]
            ind, _ = pit.at(sid, CAL[A_])
            out.append({"sid": sid, "i": i, "期別": P, "A": str(CAL[A_].date()), "Apos": A_, "e": (str(CAL[e].date()) if e <= CEND else ""),
                        "段": segname(CAL[A_]), "年": CAL[A_].year, "月": f"{CAL[A_].year}-{CAL[A_].month:02d}", "市場": MKT.get(sid, ""),
                        "產業": ind or "無類別", "A成立": bool(r["A成立"]), "A可判": bool(r["A可判"]), "A近750": bool(r["A近750"]), "B": bool(r["B"]),
                        "轉強可判": bool(r["轉強可判"]), "轉強": bool(r["轉強"]), "歷史天數": int(r["歷史天數"]),
                        "進場": fl, "H750走得完": walk,
                        "H750窗內遇壞根": (bool(PX["CB"][i, x] - PX["CB"][i, e] > 0) if walk else None),
                        "H750窗內遇下市": (bool(PX["LASTV"][i] < x and CEND - PX["LASTV"][i] >= 5) if walk else None)})
        E = pd.DataFrame(out)
        if len(E):
            E["主格"] = (E["進場"] == "保留") & E["H750走得完"]
        return E
    E = {arm: ev_table(arm, EV[arm]) for arm in ARMS}
    E["丁"] = E["丁"][E["丁"]["進場"] == "保留"].reset_index(drop=True)          # 丁 ＝ 可進場股
    log(f"[事件] " + "｜".join(f"{a} {len(E[a])}" for a in ARMS) + f"｜{time.time() - t0:.0f}s")
    return {"sha": sha, "DN": DN, "PX": PX, "B": B, "E": E, "EV": EV, "RS": RS, "EVng": EVng, "RSng": RSng, "eflag": eflag,
            "rdiag": rdiag, "months": months, "first": first, "FV": FV, "CEND": CEND}


def seg_rows(E, arm, extra=None):
    rows = []
    for nm in [s[0] for s in SEGS] + ["段外"]:
        d = E[E["段"] == nm] if len(E) else E
        if not len(d):
            rows.append({"臂": arm, "段": nm, "事件": 0, "n_eff": 0, "樣本不足(n_eff<24)": True}); continue
        m = d[d["主格"]]; ne = int(m["月"].nunique())
        rows.append({"臂": arm, "段": nm, "事件(重複窗後)": len(d), "上市": int((d["市場"] == "twse").sum()), "上櫃": int((d["市場"] == "tpex").sum()),
                     "e可進場": int((d["進場"] == "保留").sum()), "750走得完": int(d["H750走得完"].sum()),
                     "750走得完比例": float(d["H750走得完"].mean()), "主格事件": len(m), "n_eff": ne, "樣本不足(n_eff<24)": ne < NEFF_MIN,
                     "每月主格中位": (float(m.groupby("月").size().median()) if len(m) else np.nan), "主格年數": int(m["年"].nunique()),
                     "主格壞根截斷": int((m["H750窗內遇壞根"] == True).sum()), "主格下市": int((m["H750窗內遇下市"] == True).sum()),  # noqa: E712
                     "主格下市比例": (float((m["H750窗內遇下市"] == True).mean()) if len(m) else np.nan),  # noqa: E712
                     "A可判比例(主格)": (float(m["A可判"].mean()) if len(m) else np.nan),
                     "轉強可判比例(主格)": (float(m["轉強可判"].mean()) if len(m) else np.nan), "轉強比例(主格)": (float(m["轉強"].mean()) if len(m) else np.nan),
                     **(extra(d, m) if extra else {})})
    return rows


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); ap.add_argument("--out", default=OUT)
    ap.add_argument("--sha", default=SHA_PIN)
    a = ap.parse_args()
    t0 = time.time()
    out = a.out; os.makedirs(out, exist_ok=True); os.makedirs(TW, exist_ok=True)
    reg = IMF.reg_check(REG_SHA); log(f"[登錄] {reg}（sha {REG_SHA} 已驗）")
    rul = [f for d in [IMF.MAILBOX] + sorted(glob.glob(os.path.join(IMF.MAILBOX, "_封存-*"))) for f in glob.glob(os.path.join(d, "*.md")) if RUL in os.path.basename(f)]
    if not rul:
        raise SystemExit(f"⛔ 信箱找不到裁定 {RUL}")
    log(f"[裁定] {os.path.basename(rul[0])}")
    Z = build(a.procs, a.sha)
    PX, B, E, CEND = Z["PX"], Z["B"], Z["E"], Z["CEND"]
    CAL = PX["CAL"]

    # ── S1 重疊（P9）
    s1 = pd.read_csv(S1_EV, dtype={"sid": str, "期別": str}, usecols=["sid", "期別"])
    s1k = set(zip(s1["sid"], s1["期別"]))
    s1m = defaultdict(list)
    for s_, p_ in s1k:
        s1m[s_].append(RT.mnum(p_))
    for arm in ARMS:
        d = E[arm]
        if len(d):
            d["S1同期"] = [(s_, p_) in s1k for s_, p_ in zip(d["sid"], d["期別"])]
            d["S1±12月"] = [any(abs(RT.mnum(p_) - q) <= 12 for q in s1m.get(s_, [])) for s_, p_ in zip(d["sid"], d["期別"])]

    def extra(d, m):
        return {"S1同期重疊(事件)": float(d["S1同期"].mean()), "S1±12月重疊(事件)": float(d["S1±12月"].mean())}
    FR = []
    for arm in ARMS:
        FR += seg_rows(E[arm], arm, extra)
    FR = pd.DataFrame(FR)
    # 乙佔甲、去重前、無閘版件數
    for nm in [s[0] for s in SEGS] + ["段外"]:
        nj = int((E["甲"]["段"] == nm).sum()) if len(E["甲"]) else 0
        ny = int((E["乙"]["段"] == nm).sum()) if len(E["乙"]) else 0
        FR.loc[(FR["臂"] == "乙") & (FR["段"] == nm), "乙佔甲(事件)"] = (ny / nj if nj else np.nan)
        dj = E["甲"][E["甲"]["段"] == nm] if len(E["甲"]) else E["甲"]
        FR.loc[(FR["臂"] == "甲") & (FR["段"] == nm), "轉強配到率(甲事件有營收列)"] = (float(dj["轉強可判"].mean()) if len(dj) else np.nan)
        FR.loc[(FR["臂"] == "甲") & (FR["段"] == nm), "轉強率(甲事件)"] = (float(dj["轉強"].mean()) if len(dj) else np.nan)
        for arm in ARMS:
            bm = B[B["段"] == nm]
            if arm == "丁":
                raw = int(bm["過閘"].sum()); ng = int(len(bm))
            else:
                mk = {"甲": bm["A成立"] & bm["B"], "乙": bm["A成立"] & bm["B"] & bm["轉強"], "丙": bm["B"] & ~bm["A成立"]}[arm]
                raw = int((mk & bm["過閘"]).sum())
                ng = sum(1 for z in Z["EVng"][arm] if segname(CAL[z[2]]) == nm)
            FR.loc[(FR["臂"] == arm) & (FR["段"] == nm), "訊號股月(重複窗前,過閘)"] = raw
            FR.loc[(FR["臂"] == arm) & (FR["段"] == nm), "無閘版事件(重複窗後)"] = ng

    # ── 母體成立率（P2～P5）
    BS = []
    for nm in [s[0] for s in SEGS] + ["段外"]:
        for lab, bm in (("過閘", B[(B["段"] == nm) & B["過閘"]]), ("無閘", B[B["段"] == nm])):
            n = len(bm)
            if not n:
                continue
            BS.append({"段": nm, "母體": lab, "股月": n, "月": int(bm["期別"].nunique()), "A可判比例": float(bm["A可判"].mean()), "A成立率": float(bm["A成立"].mean()),
                       "A成立率(A可判中)": (float(bm.loc[bm["A可判"], "A成立"].mean()) if bm["A可判"].any() else np.nan),
                       "B可判比例": float(bm["B可判"].mean()), "B成立率": float(bm["B"].mean()),
                       "B成立率(B可判中)": (float(bm.loc[bm["B可判"], "B"].mean()) if bm["B可判"].any() else np.nan),
                       "轉強可判比例": float(bm["轉強可判"].mean()), "轉強率": float(bm["轉強"].mean()),
                       "A且B率": float((bm["A成立"] & bm["B"]).mean()), "B且非A率": float((bm["B"] & ~bm["A成立"]).mean()),
                       "A且B且轉強率": float((bm["A成立"] & bm["B"] & bm["轉強"]).mean()),
                       "A近750成立率": (float(bm["A近750"].mean()) if lab == "過閘" else np.nan)})
    BS = pd.DataFrame(BS)

    # ── 歷史天數（分年，過閘股月）
    g = B[B["過閘"]].copy(); g["年"] = [int(CAL[x].year) for x in g["A"]]
    HD = []
    for y, d in g.groupby("年"):
        HD.append({"年(判日)": y, "股月": len(d), "歷史天數p10": float(d["歷史天數"].quantile(0.1)), "中位": float(d["歷史天數"].median()),
                   "p90": float(d["歷史天數"].quantile(0.9)), "≥750比例(A可判)": float(d["A可判"].mean()), "≥499比例": float((d["歷史天數"] >= 499).mean()),
                   "A成立率": float(d["A成立"].mean()), "B成立率": float(d["B"].mean())})
    HD = pd.DataFrame(HD)

    # ── 分產業（主格；兩段分開）、分年
    IND = []; YR = []
    for arm in ARMS:
        d = E[arm]
        if not len(d):
            continue
        m = d[d["主格"]]
        for (nm, ind), x in m.groupby(["段", "產業"]):
            IND.append({"臂": arm, "段": nm, "產業": ind, "主格事件": len(x), "月數": int(x["月"].nunique())})
        for y, x in d.groupby("年"):
            YR.append({"臂": arm, "年(判日)": int(y), "事件": len(x), "e可進場": int((x["進場"] == "保留").sum()), "主格": int(x["主格"].sum()),
                       "上市": int((x["市場"] == "twse").sum()), "上櫃": int((x["市場"] == "tpex").sum()), "A可判比例": float(x["A可判"].mean())})
    IND = pd.DataFrame(IND); YR = pd.DataFrame(YR)

    # ── 等價／退化（P10）
    EQ = []
    gb = B[B["過閘"] & B["段"].isin([s[0] for s in SEGS])]
    EQ.append({"項": "A且B 股月 ÷ 全母體股月（過閘、兩段）", "值": round(float((gb["A成立"] & gb["B"]).mean()), 4), "註": "甲 ⊂ 丁；接近 1 ⇒ 甲≈丁"})
    EQ.append({"項": "B 成立率（過閘、兩段）", "值": round(float(gb["B"].mean()), 4), "註": "是否幾乎總成立（退化）"})
    EQ.append({"項": "B 成立率（B 可判中）", "值": round(float(gb.loc[gb["B可判"], "B"].mean()), 4), "註": "去掉不可判"})
    EQ.append({"項": "A 成立率（過閘、兩段）", "值": round(float(gb["A成立"].mean()), 4), "註": "A 幾乎總成立 ⇒ 甲≈B 全體、丙空"})
    EQ.append({"項": "B 的兩條：c＜2×最低 成立率／c≤0.85×最高 成立率", "值": "見下兩列", "註": "哪一條在擋"})
    # 兩條分開（只過閘、兩段、B 可判）
    c1 = []; c2 = []
    PXC = PX["C"]
    for i, A_ in zip(gb.loc[gb["B可判"], "i"], gb.loc[gb["B可判"], "A"]):
        p1 = int(A_) - 1; w = PXC[int(i), p1 - WB + 1:p1 + 1]; c = PXC[int(i), p1]
        c1.append(c < 2 * np.nanmin(w)); c2.append(c <= 0.85 * np.nanmax(w))
    c1 = np.array(c1, bool); c2 = np.array(c2, bool)
    EQ.append({"項": "B 條件一 c＜2×500日最低（B 可判中）", "值": round(float(c1.mean()), 4) if len(c1) else None, "註": ""})
    EQ.append({"項": "B 條件二 c≤0.85×500日最高（B 可判中）", "值": round(float(c2.mean()), 4) if len(c2) else None, "註": ""})
    EQ.append({"項": "B 兩條聯合（B 可判中）", "值": round(float((c1 & c2).mean()), 4) if len(c1) else None, "註": "若 ≈ 某一條 ⇒ 另一條幾乎不擋"})
    nj = len(E["甲"]); ny = len(E["乙"])
    EQ.append({"項": "乙 ÷ 甲（事件，全期）", "值": round(ny / nj, 4) if nj else None, "註": "乙臂轉強配到率"})
    EQ.append({"項": "甲事件轉強可判（有營收列）比例", "值": round(float(E["甲"]["轉強可判"].mean()), 4) if nj else None, "註": "無列 ⇒ 轉強為假"})
    ja = set(zip(E["甲"]["sid"], E["甲"]["期別"])) if nj else set(); ca = set(zip(E["丙"]["sid"], E["丙"]["期別"])) if len(E["丙"]) else set()
    EQ.append({"項": "甲 ∩ 丙（依構造應為 0）", "值": len(ja & ca), "註": "A 與 ¬A 互斥"})
    ya = set(zip(E["乙"]["sid"], E["乙"]["期別"])) if ny else set()
    EQ.append({"項": "乙事件中同期也是甲事件的比例", "值": round(len(ya & ja) / ny, 4) if ny else None, "註": "兩臂各自 36 月去重 ⇒ 乙不一定是甲的子集"})
    agree = float((gb["A近750"] == gb["A成立"]).mean())
    EQ.append({"項": "A近750（美股口徑）與 A（任一 750 日窗）一致率（過閘、兩段）", "值": round(agree, 4),
               "註": f"A成立但近750不成立 {int((gb['A成立'] & ~gb['A近750']).sum())}；近750成立必 A 成立（違反 {int((~gb['A成立'] & gb['A近750']).sum())}）"})
    d4 = E["丁"]
    kept, _ = TP.make_events([(s, int(i), int(A_), RT.mnum(P), P) for s, i, A_, P in zip(d4["sid"], d4["i"], d4["Apos"], d4["期別"])], CEND, lambda i, A_: True)
    kk = Counter(segname(CAL[z[2]]) for z in kept)
    EQ.append({"項": "丁 若同 36 月去重的件數（另一讀法）", "值": json.dumps(dict(kk), ensure_ascii=False), "註": "主讀法丁不去重"})
    for arm in ("甲", "乙", "丙"):
        d = E[arm]
        if len(d):
            EQ.append({"項": f"{arm} ∩ 3 倍命中率 S1 事件（同代號同期別）", "值": f"{int(d['S1同期'].sum())}／{len(d)}", "註": f"±12 月 {int(d['S1±12月'].sum())}"})
    EQ = pd.DataFrame(EQ)

    # ── 輸出
    cols_drop = ["i", "Apos"]
    for arm in ARMS:
        E[arm].drop(columns=[c for c in cols_drop if c in E[arm].columns]).to_csv(os.path.join(out, f"events_{arm}.csv.gz"), index=False,
                                                                                    encoding="utf-8-sig", compression="gzip")
    FR.to_csv(os.path.join(out, "freq_段.csv"), index=False, encoding="utf-8-sig")
    BS.to_csv(os.path.join(out, "base_段.csv"), index=False, encoding="utf-8-sig")
    HD.to_csv(os.path.join(out, "hist_days.csv"), index=False, encoding="utf-8-sig")
    IND.to_csv(os.path.join(out, "industry.csv"), index=False, encoding="utf-8-sig")
    YR.to_csv(os.path.join(out, "yearly.csv"), index=False, encoding="utf-8-sig")
    EQ.to_csv(os.path.join(out, "equiv.csv"), index=False, encoding="utf-8-sig")
    pk = os.path.join(TW, f"events_{Z['sha'][:12]}.pkl")
    pickle.dump({"E": {k: v for k, v in E.items()}, "EVng": Z["EVng"], "sha": Z["sha"], "out": out}, open(pk, "wb"), protocol=5)
    J = {"性質": "產業挑法好壞比例分佈 台股 seq1 頻率表（⛔ 未算任何報酬、倍數）", "登錄": f"台股策略線 seq1 sha {REG_SHA}（{reg}）", "裁定": os.path.basename(rul[0]),
         "origin/main": Z["sha"], "價格面板": {"主": PX["main_data"], "早年": PX["early_data"]}, "合併日曆": [str(CAL[0].date()), str(CAL[-1].date()), len(CAL)],
         "月營收": Z["rdiag"], "判日數": len(Z["months"]), "判日": [str(CAL[A_].date()) for _, A_ in Z["months"]],
         "重複窗剔除(過閘)": Z["RS"], "重複窗剔除(無閘)": Z["RSng"], "段": FR.to_dict("records"), "母體": BS.to_dict("records"),
         "必附": NOTES, "讀法": __doc__.split("═══ 讀法")[1], "逐事件位置檔": pk, "秒": round(time.time() - t0)}
    json.dump(J, open(os.path.join(out, "freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=RT.jdef)
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    log(f"[完成] {out}｜{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
