# -*- coding: utf-8 -*-
"""型態補條件 C 組 seq1【頻率表】（台股策略線 單筆層登錄 sha 8827942d8c296851，2026-10-17 09:38；裁定 seq360 §二 定 N_前段 ＋2、
seq361 發號）——回測線計算子代理。⛔ 只數事件日期與個數、剔除計數、n_eff；⛔ 不讀、不算、不存任何 T＋1 以後的價格或報酬。
⛔ 不 commit、不改既有程式與結果夾；patterns.py（研究二 cup_handle）、patterns_x.py（W 底 detect_turn）⛔ 只 import、不改。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPatC_freq [--procs 2]
輸出 backtest/resultsPatC/freq/：freq.json、freq.csv、freq_by_year.csv、cup_conditions.csv、w_shapes.csv、events_<格>.csv.gz、run.log

兩格（判定都只 H20；H60 只描述）：
  K1 杯柄＋柄四條：杯 ＝ 研究二 patterns.cup_handle 找杯流程原樣（本支 cups() 逐行抄錄；⭐ 每檔斷言與 patterns_x.cup_scan 的 (L, B, R) 逐筆相同）；
     柄 ＝ R＋1..t−1：① 長 ≥ 5 ② 柄期間最低收盤 ≥ cB ＋ 0.5(cR − cB)（跌破 ⇒ 型態失效、該杯結束）
     ③ 柄均量 ＜ 杯身右半（B..R）均量 ④ c[t] ＞ 柄最高價（還原 high）且 v[t] ＞ 1.4 × 前 50 日均量（Frame.vol_ma50，已 shift 1）⇒ T ＝ t。
     底版 K1b ＝ 研究二 patterns.cup_handle(frame_open(df), buy="handle") 原樣（閘門全開＝PREREGX 同；研究二自帶的柄規則與 20 日去重照舊）。
  K2 W 底＋左谷量 ＞ 右谷量：W 底 ＝ patterns_x.detect_turn("w", 有效 K 棒收盤) 原樣（補齊版 §二、PREREGX 同版：eq ≤ 5%、bounce ≥ 10%）；
     加 v[L1] ＞ v[L2]（當日成交量，有效 K 棒序號；任一缺值 ⇒ 不成立）。底版 K2b ＝ 不加量能。T ＝ 原版突破日。
  描述（⛔ 不判）：Adam／Eve（谷底收盤 ×1.03 以內、含谷底當天的連續有效 K 棒數 ≤ 3 ＝ Adam、≥ 4 ＝ Eve）四組合；量遞減 v[L1] ＞ v[A] ＞ v[L2]。

═══ 讀法（Q 標；登錄沒寫清楚、執行者補的都在這裡；⛔ 在看任何本件數字之前寫死；★＝兩種讀法擇一，〔 〕內為另一讀法）═══
 Q1 世界、母體、壞根 ＝ researchAscTri_freq.load_world 原樣（⛔ 不另寫資料層）：主 ＝ rerun17 快照 H2D edc6f8002f（2015-01-05～2026-09-24）；
    早年 ＝ ~/earlydata/eotc_f65bb03e11（2004-02-11～2014-12-31）；股票 ＝ ~/rluwork/world_{main,early}.pkl sids（UG.gate3 GATE_V2 開 ∩ 四碼、
    首碼 1～9、非 91xx、含已下市）；research11.load_bars ＜ 260 根的股票不進（同 AscTri／Dumb）。
    壞根 ＝ load_bars next_bad（缺口 ≥ 5 日、價格斷點、幽靈還原）∪ ~/crashwork/bad_*.pkl ∪ 早年 researchAddOn.early_extra_bad（reduce_v2，seq341 §六）。
 Q2 ★ 判定窗（PatAll seq3 同起點）：主全窗 ＝ T ∈ [2017-03-02, 資料尾 − H]；分報 探索 [2017-03-02, 2021-12-30]｜確認 [2022-01-03, 資料尾 − H]｜
    早年 [2005 第一個交易日, 2014-12-31 − H]（交易日曆）。⭐「依構造不可判定」以【主全窗 H20】的 n_eff 判（＝ PatAll seq3 單一判定窗）；
    探索／確認／早年只報〔另一讀法：分段各自判 ⇒ 三段 n_eff 並列在表上〕。
 Q3 先合併、再剔除（PatAll Q2 同）：同檔同格依 T 走，T ∈ (t0, t0＋20]（交易日曆、t0 ＝ 上一個未被合併者）⇒ 合併掉（主、早年各自一條序列，
    合併在 H20 窗內做、H60 沿用）；未合併者依序判剔除，只記第一個原因：
    pit 無效（UG.pit_valid[T]，GATE_V2 開）→ 硬斷點（[first, T＋H] 內有壞 K 棒；或 T＋H 前最後一根 K 棒到 T＋H 已缺 ≥ 5 日且之後還有成交）
    → T＋1 停牌（T＋1 無成交或還原開盤缺值）→ T＋1 開盤漲停 → T＋1 開盤跌停（PatAll Q3、Q4 同；⛔ 不看價差）。
    first：K1／K1b ＝ 左杯口 L；K2／K2b ＝ 左谷 L1。去重後 n ＝「保留」。
 Q4 n_eff（PatAll Q7）：H20 ＝ min(保留數, 有保留事件的曆月數)；H60 ＝ min(保留數, (T − 段起點)//60 區段數)（只描述）。
    n_eff ＜ 30 ⇒「依構造不可判定、不計 N」；否則「照判」（登錄 §二）。
 Q5 杯柄 柄的落地（登錄 §一 只寫四條）：
    ★ 柄上限 30 日（研究二 handle_len 上限，底版「原樣」的一部分）〔另一讀法：不設上限、到失效或突破為止 ⇒ 並列「K1_無上限」〕；
    ★ 研究二另兩條內部條件「柄長 ＜ 杯身長」「Frame.gate」⛔ 不加（登錄四條沒有；閘門全開同 PREREGX）；
    ② 用收盤、cR、≥（登錄逐字；研究二是盤中低點、cL、＞）；④ 用 ＞ 1.4（登錄逐字；研究二是 ≥）；
    ★ 帶量突破（④ 成立）但 ③ 不成立 ⇒ 該杯結束、無事件（研究二同：突破一次就結束這個 R）〔另一讀法：繼續等下一次突破〕；
    價格站上柄高但量不足 ⇒ 該日併入柄、繼續（研究二同）；柄內或 t 收盤缺值 ⇒ 該杯結束（研究二同）。
    同一個 T 由多個 R 產生 ⇒ 只算一筆（first 取 sorted 第一個）；⛔ 不套研究二的 20 日 last_sig（由 Q3 合併處理）。
    逐條保留比例 ＝ 四條全加的事件數 ÷ 拿掉該條（①→柄長 ≥ 1、②→不檢查、③→不檢查、④→只要收盤站上柄高）的事件數（同窗、同 Q3 流程）。
 Q6 W 底量能用 load_stock 的 volume（張數口徑同 Frame；有效 K 棒序號 L1、L2、A 對應日曆位置）。Adam／Eve 連續天數只往 T 之前數
    （右谷往右到 T−1 為止；左谷往左不限），門檻 ≤ c[谷]×1.03（含等號）。
"""
from __future__ import annotations

import argparse
import glob
import gzip
import hashlib
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchAscTri_freq as AT              # noqa: E402  load_world 原樣（⛔ 只 import）
from backtest import research11 as R                        # noqa: E402
from backtest import patterns as P                          # noqa: E402
from backtest import patterns_x as PX                       # noqa: E402
from backtest import universe_gate as UG                    # noqa: E402

UG.set_gate_v2(True)

REG_SHA = "8827942d8c296851"
MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
OUT = "backtest/resultsPatC/freq"
HS = (20, 60)
MERGE = 20
NEFF_MIN = 30
VOLX = 1.4
SEGS = {"主": {"主全窗": ("2017-03-02", None), "探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", None)},
        "早年": {"早年": ("2005-01-01", "2014-12-31")}}
CELLS = {"K1": "杯柄＋柄四條", "K1b": "底版 研究二杯柄", "K1_無上限": "杯柄＋柄四條（柄不設 30 日上限，另一讀法）",
         "K1_去①": "拿掉① 柄≥5日", "K1_去②": "拿掉② 不破杯深一半", "K1_去③": "拿掉③ 柄量縮", "K1_去④": "拿掉④ 突破量>1.4×50日均量",
         "K2": "W底＋左谷量>右谷量", "K2b": "底版 W底"}
JUDGE = {"K1": "K1b", "K2": "K2b"}
ST = ["保留", "合併掉", "剔除_pit無效", "剔除_硬斷點", "剔除_T+1停牌", "剔除_T+1開盤漲停", "剔除_T+1開盤跌停"]
_G: dict = {}
LOG: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def reg_check():
    fs = [f for f in glob.glob(os.path.join(MAILBOX, "*.md")) if f"sha{REG_SHA}" in os.path.basename(f)]
    if len(fs) != 1:
        raise SystemExit(f"⛔ 信箱找不到唯一一封登錄全文 sha{REG_SHA}：{fs}")
    b = open(fs[0], "rb").read()
    h = hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]
    if h != REG_SHA:
        raise SystemExit(f"⛔ 登錄 sha {h} ≠ {REG_SHA}")
    return os.path.basename(fs[0])


# ═════════════ 杯：研究二 cup_handle 找杯流程逐行抄錄（unit＝1） ═════════════
def cups(f):
    p = f.p; c, v = f.c, f.v
    k = max(1, p["pivot_k"]); cup_lo, cup_hi = p["cup_len"]; half_min = p["half_min"]
    prior_lb = p["prior_lookback"]; lookbacks = list(p["cup_lookbacks"]); u_frac = p["u_frac"]
    roll = pd.Series(c).rolling(2 * k + 1, center=True, min_periods=2 * k + 1).max().to_numpy(float)
    pivots = np.flatnonzero((c == roll) & ~np.isnan(roll))
    out = []
    for R_ in pivots:
        cR = c[R_]; found = None
        for lb in lookbacks:
            lo = max(0, R_ - lb)
            B = P._nanargmin(c[lo:R_ + 1], lo)
            if B is None or B == R_:
                continue
            L = P._nanargmax(c[lo:B + 1], lo)
            if L is None or not (L < B):
                continue
            cL, cB = c[L], c[B]
            if B - L < half_min or R_ - B < half_min or not (cup_lo <= R_ - L <= cup_hi):
                continue
            depth = (cL - cB) / cL
            if not (p["cup_depth"][0] <= depth <= p["cup_depth"][1]):
                continue
            if not (p["rim_ratio"][0] <= cR / cL <= p["rim_ratio"][1]):
                continue
            pre = c[max(0, L - prior_lb):L + 1]
            if np.isnan(pre).all() or cL / np.nanmin(pre) < p["cup_prior_rise"]:
                continue
            seg = c[L:R_ + 1]
            if np.isnan(seg).mean() > 0.05:
                continue
            u = np.nanmean(seg <= cB + p["u_zone"] * (cL - cB))
            if u < u_frac:
                continue
            found = (L, B, cL, cB)
            break
        if found is None:
            continue
        L, B, cL, cB = found
        out.append({"R": int(R_), "L": int(L), "B": int(B), "cL": float(cL), "cB": float(cB), "cR": float(cR),
                    "vr": float(np.nanmean(v[B:R_ + 1]))})
    return out


def handle_C(f, cup, minlen=5, c2=True, c3=True, c4=True, hmax=30):
    """Q5：回 (T 或 None, 結束原因)。柄 ＝ R+1..t−1；running 量（⛔ 只用 ≤ t 的資料）。"""
    c, h, v, vma, n = f.c, f.h, f.v, f.vol_ma50, f.n
    R_ = cup["R"]; floor = cup["cB"] + 0.5 * (cup["cR"] - cup["cB"])
    tmax = n - 1 if hmax is None else min(n - 1, R_ + hmax + 1)
    cmin = np.inf; hh = -np.inf; vs = 0.0; vn = 0
    for t in range(R_ + 1, tmax + 1):
        if t > R_ + 1:                                   # 把 t−1 併入柄
            j = t - 1
            if np.isnan(c[j]):
                return None, "缺值"
            cmin = min(cmin, c[j])
            if np.isfinite(h[j]):
                hh = max(hh, h[j])
            if np.isfinite(v[j]):
                vs += v[j]; vn += 1
            if c2 and cmin < floor:
                return None, "②破杯深一半"
        if t - R_ - 1 < minlen:
            continue
        if np.isnan(c[t]):
            return None, "缺值"
        if c[t] > hh and ((not c4) or (v[t] > VOLX * vma[t])):
            if (not c3) or (vn > 0 and vs / vn < cup["vr"]):
                return t, "突破"
            return None, "③柄量未縮（帶量突破時）"
    return None, "柄逾期／資料尾"


MODES = {"K1": {}, "K1_無上限": {"hmax": None}, "K1_去①": {"minlen": 1}, "K1_去②": {"c2": False},
         "K1_去③": {"c3": False}, "K1_去④": {"c4": False}}


def adam_eve(c, Lx, T):
    thr = c[Lx] * 1.03; n_ = 1; j = Lx - 1
    while j >= 0 and c[j] <= thr:
        n_ += 1; j -= 1
    j = Lx + 1
    while j < T and c[j] <= thr:
        n_ += 1; j += 1
    return n_


# ═════════════ 逐股 ═════════════
def stock_job(a):
    wn, sid = a
    W = _G[wn]; cal = W["cal"]; n0 = W["n0"]; i = W["ix"][sid]
    import backtest.data as D
    D.DATA = W["data"]
    B = R.load_bars(sid, W["mk"].get(sid, "twse"), cal)
    if B is None:
        return sid, None
    df = B["df"]; idx = B["idx"].astype(np.int64); nb = len(idx)
    if len(df) != n0:
        raise SystemExit(f"⛔ {wn} {sid} df 長 {len(df)} ≠ 日曆 {n0}")
    EV = {k: [] for k in CELLS}
    # ── 杯柄（日曆陣列，研究二同）
    f = PX.frame_open(df, set())
    cl = cups(f)
    _, cg = PX.cup_scan(f)
    if [(g["L"], g["B"], g["R"]) for g in cg] != [(x["L"], x["B"], x["R"]) for x in cl]:
        raise SystemExit(f"⛔ {wn} {sid}：cups() ≠ patterns_x.cup_scan（{len(cl)} vs {len(cg)}）")
    EV["K1b"] = [(int(s["signal_pos"]), int(s["L"]), {}) for s in P.cup_handle(f, buy="handle")]
    endr = {}
    for cup in cl:
        for m, kw in MODES.items():
            T, why = handle_C(f, cup, **kw)
            if m == "K1":
                endr[why] = endr.get(why, 0) + 1
            if T is not None:
                EV[m].append((int(T), cup["L"], {"R": cup["R"]}))
    # ── W 底（有效 K 棒序列，PREREGX 同）
    cf = df["close"].to_numpy(float); vf = df["volume"].to_numpy(float)
    bars = np.flatnonzero(np.isfinite(cf)); cb = cf[bars]; vb = vf[bars]
    for e in PX.detect_turn("w", cb)["events"]:
        L1, L2, A = e["pts"]["L1"], e["pts"]["L2"], e["pts"]["A"]; Tb = e["T"]
        v1, v2, vA = vb[L1], vb[L2], vb[A]
        volok = bool(np.isfinite(v1) and np.isfinite(v2) and v1 > v2)
        dec = bool(np.isfinite(v1) and np.isfinite(v2) and np.isfinite(vA) and v1 > vA > v2)
        s1 = "Adam" if adam_eve(cb, L1, Tb) <= 3 else "Eve"; s2 = "Adam" if adam_eve(cb, L2, Tb) <= 3 else "Eve"
        x = {"shape": f"{s1}&{s2}", "dec": dec}
        EV["K2b"].append((int(bars[Tb]), int(bars[e["first"]]), x))
        if volok:
            EV["K2"].append((int(bars[Tb]), int(bars[e["first"]]), x))
    # ── 母體／剔除材料
    bad = np.asarray(B["next_bad"][:nb] == np.arange(nb), bool)
    for p_ in W["BADPOS"].get(sid, ()):
        k = int(np.searchsorted(idx, p_, "left"))
        if k < nb:
            bad[k] = True
    CB = np.r_[0, np.cumsum(bad)]
    PV = W["PV"][i]; TRD = W["TRD"][i]; O = W["O"][i]; UPL = W["UPL"][i]; DNL = W["DNL"][i]

    def brk(fpos, endpos):
        kf = int(np.searchsorted(idx, fpos, "left")); kH = int(np.searchsorted(idx, endpos, "right")) - 1
        if kH >= kf and CB[kH + 1] - CB[kf] > 0:
            return True
        if 0 <= kH < nb - 1 and idx[kH + 1] - idx[kH] - 1 >= 5 and endpos - idx[kH] >= 5:
            return True
        return False

    out = {}
    for seg_w, (w0, wend) in W["win"].items():
        for cell, evs in EV.items():
            d = {}
            for e in sorted(set((t, fi) for t, fi, _ in evs)):
                d.setdefault(e[0], e[1])                    # 同一個 T 取第一個
            xs = {t: x for t, _, x in evs}
            Ts = [t for t in sorted(d) if w0 <= t <= n0 - 1 - HS[0] and t <= wend]
            rows = []; t0 = -10 ** 9
            for t in Ts:
                merged = t0 < t <= t0 + MERGE
                if not merged:
                    t0 = t
                st = {}
                for H in HS:
                    if t + H > n0 - 1:
                        st[H] = "窗外"; continue
                    if merged:
                        st[H] = "合併掉"; continue
                    e1 = t + 1
                    if not bool(PV[t]):
                        st[H] = "剔除_pit無效"
                    elif brk(d[t], t + H):
                        st[H] = "剔除_硬斷點"
                    elif not (bool(TRD[e1]) and np.isfinite(O[e1]) and O[e1] > 0):
                        st[H] = "剔除_T+1停牌"
                    elif bool(UPL[e1]):
                        st[H] = "剔除_T+1開盤漲停"
                    elif bool(DNL[e1]):
                        st[H] = "剔除_T+1開盤跌停"
                    else:
                        st[H] = "保留"
                rows.append({"sid": sid, "T": int(t), "first": int(d[t]), "st20": st[20], "st60": st[60], **xs.get(t, {})})
            out[(seg_w, cell)] = rows
    return sid, {"rows": out, "endr": endr, "ncup": len(cl)}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    t0 = time.time()
    out_dir = OUT if a.limit is None else os.path.join(OUT, "_try")
    os.makedirs(out_dir, exist_ok=True)
    reg = reg_check()
    log(f"[登錄] {reg}（sha {REG_SHA} 已驗）")
    J = {"性質": "型態補條件 C 組 seq1 頻率表（⛔ 未讀、未算任何報酬）", "登錄": f"台股策略線 seq1 sha {REG_SHA}",
         "裁定": "seq360 §二 N_前段 ＋2；seq361 發號；n_eff ＜ 30 ⇒ 依構造不可判定、不計 N", "世界": {}, "格": CELLS}
    FREQ = []; YR = []; COND = []; SHAPE = []; ENDR = {}
    for wn in ("主", "早年"):
        W = AT.load_world(wn); cal = W["cal"]; n0 = W["n0"]
        win = {}
        for sg, (x, y) in SEGS[wn].items():
            p0 = int(cal.searchsorted(pd.Timestamp(x)))
            p1 = n0 - 1 if y is None else int(cal.searchsorted(pd.Timestamp(y), side="right")) - 1
            win[sg] = (p0, p1)
        W["win"] = win; _G[wn] = W
        sids = W["sids"][:a.limit] if a.limit else W["sids"]
        res = {}
        with Pool(a.procs) as pool:
            for k_, (sid, r) in enumerate(pool.imap_unordered(stock_job, [(wn, s) for s in sids], chunksize=8)):
                res[sid] = r
                if (k_ + 1) % 300 == 0:
                    log(f"  {wn} … {k_ + 1}／{len(sids)}｜{time.time() - t0:.0f}s")
        ok = {s: r for s, r in res.items() if r is not None}
        n_skip = len(res) - len(ok)
        endr = {}
        for r in ok.values():
            for k, v in r["endr"].items():
                endr[k] = endr.get(k, 0) + v
        ENDR[wn] = {"杯數（全期）": int(sum(r["ncup"] for r in ok.values())), "K1 柄掃描結束原因（全期、每杯一次）": endr}
        log(f"[{wn}] 逐股完｜load_bars 不足 260 根 {n_skip} 檔｜cups() ＝ cup_scan 全部逐筆相同｜{ENDR[wn]}｜{time.time() - t0:.0f}s")
        Wj = {"資料": W["data"], "日曆": [str(cal[0].date()), str(cal[-1].date())], "閘": W["gate"], "壞根": W["bad_info"],
              "檔數": len(sids), "load_bars不足260根檔數": n_skip, "段": {}, "杯柄診斷": ENDR[wn]}
        for sg, (p0, p1) in win.items():
            ym = np.array([d.strftime("%Y-%m") for d in cal])
            segj = {}
            for cell in CELLS:
                rows = [x for r in ok.values() for x in r["rows"][(sg, cell)]]
                j = {}
                for H in HS:
                    key = f"st{H}"
                    inw = [x for x in rows if x[key] != "窗外"]
                    kept = [x for x in inw if x[key] == "保留"]
                    acc = {s_: sum(1 for x in inw if x[key] == s_) for s_ in ST}
                    if H == 20:
                        units = len({ym[x["T"]] for x in kept}); unit = "曆月"
                    else:
                        units = len({(x["T"] - p0) // 60 for x in kept}); unit = "60日區段"
                    ne = min(len(kept), units)
                    j[f"H{H}"] = {"原始": len(inw), "合併後": len(inw) - acc["合併掉"], **acc, "去重後n(保留)": len(kept),
                                  "相異檔數": len({x["sid"] for x in kept}), f"有事件{unit}": units, "n_eff": ne,
                                  "逐年原始": dict(sorted(pd.Series([cal[x["T"]].year for x in inw]).value_counts().to_dict().items())) if inw else {},
                                  "逐年保留": dict(sorted(pd.Series([cal[x["T"]].year for x in kept]).value_counts().to_dict().items())) if kept else {}}
                    if cell in ("K2", "K2b") and kept:
                        j[f"H{H}"]["Adam/Eve四組合(保留)"] = pd.Series([x["shape"] for x in kept]).value_counts().to_dict()
                        j[f"H{H}"]["量遞減L1>A>L2(保留)"] = int(sum(1 for x in kept if x["dec"]))
                segj[cell] = j
                if cell != "K1_無上限" or True:
                    yrs = (cal[min(p1, n0 - 1 - 20)] - cal[p0]).days / 365.25
                    row = {"世界": wn, "段": sg, "格": cell, "說明": CELLS[cell], "期間": f"{cal[p0].date()}～{cal[min(p1, n0 - 1 - 20)].date()}"}
                    for H in HS:
                        q = j[f"H{H}"]
                        for kk in ("原始", "合併後", "剔除_pit無效", "剔除_硬斷點", "剔除_T+1停牌", "剔除_T+1開盤漲停", "剔除_T+1開盤跌停",
                                   "去重後n(保留)", "相異檔數", "n_eff"):
                            row[f"{kk}_H{H}"] = q[kk]
                        row[f"有事件{'曆月' if H == 20 else '60日區段'}_H{H}"] = q[f"有事件{'曆月' if H == 20 else '60日區段'}"]
                    row["每年保留_H20"] = round(j["H20"]["去重後n(保留)"] / yrs, 2) if yrs > 0 else None
                    FREQ.append(row)
                    for y, nraw in j["H20"]["逐年原始"].items():
                        YR.append({"世界": wn, "段": sg, "格": cell, "年": int(y), "原始_H20": int(nraw), "保留_H20": int(j["H20"]["逐年保留"].get(y, 0))})
            # 比例（對底版）
            for cell, base in [("K1", "K1b"), ("K1_無上限", "K1b"), ("K2", "K2b")]:
                for H in HS:
                    a_, b_ = segj[cell][f"H{H}"], segj[base][f"H{H}"]
                    a_["對底版_原始比例"] = round(a_["原始"] / b_["原始"], 4) if b_["原始"] else None
                    a_["對底版_保留比例"] = round(a_["去重後n(保留)"] / b_["去重後n(保留)"], 4) if b_["去重後n(保留)"] else None
            # K1 與底版重疊（同檔同 T，保留）
            k1 = {(x["sid"], x["T"]) for r in ok.values() for x in r["rows"][(sg, "K1")] if x["st20"] == "保留"}
            kb = {(x["sid"], x["T"]) for r in ok.values() for x in r["rows"][(sg, "K1b")] if x["st20"] == "保留"}
            segj["K1"]["H20"]["與底版同檔同日(保留)"] = len(k1 & kb)
            # 逐條保留比例
            for m in ("K1_去①", "K1_去②", "K1_去③", "K1_去④", "K1_無上限"):
                for H in HS:
                    nA = segj["K1"][f"H{H}"]["去重後n(保留)"]; nM = segj[m][f"H{H}"]["去重後n(保留)"]
                    rA = segj["K1"][f"H{H}"]["原始"]; rM = segj[m][f"H{H}"]["原始"]
                    COND.append({"世界": wn, "段": sg, "H": H, "比較": f"K1 ÷ {m}", "說明": CELLS[m], "K1原始": rA, f"{m}原始": rM,
                                 "原始保留比例": round(rA / rM, 4) if rM else None, "K1保留": nA, f"對照保留": nM,
                                 "保留後保留比例": round(nA / nM, 4) if nM else None})
            for cell in ("K2", "K2b"):
                q = segj[cell]["H20"]
                for shp, cnt in sorted(q.get("Adam/Eve四組合(保留)", {}).items()):
                    SHAPE.append({"世界": wn, "段": sg, "格": cell, "形狀": shp, "保留_H20": int(cnt)})
                SHAPE.append({"世界": wn, "段": sg, "格": cell, "形狀": "量遞減L1>A>L2", "保留_H20": q.get("量遞減L1>A>L2(保留)", 0)})
            Wj["段"][sg] = segj
            log(f"[{wn}/{sg}] " + "｜".join(f"{c_} n={segj[c_]['H20']['去重後n(保留)']} n_eff={segj[c_]['H20']['n_eff']}" for c_ in CELLS))
            # 事件檔（⛔ 無報酬欄）
            for cell in CELLS:
                rows = sorted([x for r in ok.values() for x in r["rows"][(sg, cell)]], key=lambda x: (x["T"], x["sid"]))
                if not rows:
                    continue
                dfo = pd.DataFrame([{"sid": x["sid"], "T": str(cal[x["T"]].date()), "first": str(cal[x["first"]].date()),
                                     "狀態_H20": x["st20"], "狀態_H60": x["st60"], **({"Adam/Eve": x["shape"], "量遞減": x["dec"]} if "shape" in x else {})}
                                    for x in rows])
                with gzip.open(os.path.join(out_dir, f"events_{wn}_{sg}_{cell}.csv.gz"), "wt", encoding="utf-8") as fh:
                    dfo.to_csv(fh, index=False)
        J["世界"][wn] = Wj
    # ── 判斷（Q2：主全窗 H20）
    jd = {}
    for cell in JUDGE:
        ne = J["世界"]["主"]["段"]["主全窗"][cell]["H20"]["n_eff"]
        jd[cell] = {"格": CELLS[cell], "主全窗H20_n_eff": ne, "判斷": "依構造不可判定、不計 N" if ne < NEFF_MIN else "照判",
                    "分段n_eff(只報)": {sg: J["世界"][w]["段"][sg][cell]["H20"]["n_eff"] for w in ("主", "早年") for sg in SEGS[w] if sg != "主全窗"}}
    J["判斷"] = jd
    J["N"] = {"登錄記 N_前段": 2, "照判格數": sum(1 for v in jd.values() if v["判斷"] == "照判"),
              "依構造不可判定(不計N)格數": sum(1 for v in jd.values() if v["判斷"] != "照判")}
    J["讀法"] = __doc__.split("═══ 讀法")[1]
    J["時間"] = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")
    pd.DataFrame(FREQ).to_csv(os.path.join(out_dir, "freq.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(YR).to_csv(os.path.join(out_dir, "freq_by_year.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(COND).to_csv(os.path.join(out_dir, "cup_conditions.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(SHAPE).to_csv(os.path.join(out_dir, "w_shapes.csv"), index=False, encoding="utf-8-sig")
    json.dump(J, open(os.path.join(out_dir, "freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[判斷] {json.dumps(jd, ensure_ascii=False)}｜{time.time() - t0:.0f}s")
    open(os.path.join(out_dir, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
