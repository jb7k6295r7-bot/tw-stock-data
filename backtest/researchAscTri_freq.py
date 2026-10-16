# -*- coding: utf-8 -*-
"""PREREG上升三角組合層 seq2 §六 步驟 1【頻率表】（台股策略線 登錄 sha 735a20737f9dd17c，2026-10-17 01:45；裁定 seq358：N_組合 ＋1，
先交頻率表；探索段預估平均持股 ＜ 3 ⇒ 改只描述、N 退回不計；≥ 3 照判）——回測線計算子代理。
⛔ 只數訊號、可買筆數、依主規則推算的持有天數與持股檔數；⛔ 不算、不存、不印任何報酬（出場時點只用價格路徑判，價格本身不輸出）。
⛔ 不 commit、不改既有程式與結果夾；偵測器 patterns_all.py ⛔ 只 import、不改；引擎 research11 ⛔ 不呼叫 simulate_mtm（會算權益）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchAscTri_freq [--procs 4]
輸出 backtest/resultsAscTri/freq/：freq.json、freq_by_year.csv、hold_by_segment.csv、signals_{主,早年}.csv.gz、run.log

═══ 讀法（Q 標；登錄沒寫清楚、執行者補的都在這裡；⛔ 在看任何本件數字之前寫死）═══
 Q0 型態（登錄 §一）：PREREG型態全量 seq3（sha b7b4a05af0341797）S06「上升三角_向上」＝ patterns_all.detect_lines 原樣（⛔ 不改參數）；
    逐檔在 D.load_stock 的有效 K 棒（還原收盤非缺值，＝ researchPatAll_freq.one_stock／detect_calendar 同一條）上跑；r60 ＝ PA._rN(c, 60)；
    去重 ＝ detect_all 同式（sorted(set)、同一 T 取第一個）。
    出場 a 要「三角下線在當日的延伸值」⇒ 本支另有 _lines_replica（detect_lines 逐行抄錄、只多記 S06 事件當時那一組的上下線），
    ⭐ 每一檔都斷言 replica 的 S06 (T, first) 與 PA.detect_lines 逐筆相同，任一檔不同 ⇒ 中止。
    ⭐ 主世界另與已提交的 resultsPatAll/events_S06_上升三角_向上.csv.gz（PatAll 頻率階段，同一快照 edc6f8002f）逐檔比 (T, first)
    （窗 [2017-03-02, 2026-08-24 往前 20 個交易日]、兩邊都有的股票）⇒ 照報差異數（PatAll 母體是 gate3 v1，名單差不算差異）。
 Q1 世界與母體（同 researchDumb Z1／Z4，⛔ 不另寫資料層）：主 ＝ rerun17 快照 H2D（edc6f8002f；2015-01-05～2026-09-24）；
    早年 ＝ ~/earlydata/eotc_f65bb03e11（上市＋上櫃，2004-02-11～2014-12-31）；股票 ＝ ~/rluwork/world_{main,early}.pkl 的 sids
    （UG.gate3 GATE_V2 開 ∩ 四碼、首碼 1～9、非 91xx ⇒ 排 -DR、ETF、創新板；含已下市）；research11.load_bars ＜ 260 根的股票不進（同 Dumb）。
    訊號日 T 的母體 ＝ patterns.Frame.gate[T]（含 T 的 20 個交易日都有成交 ∧ T−20～T−1 日均量 ≥ 500 張 ＝「T 前一日 20 日均量」）∧ UG.pit_valid[T]。
 Q2 壞根（seq335 缺口 ≥ 5 日即壞根；早年 reduce_v2 seq341 §六）：＝ researchDumb Z3 同一組來源（load_bars next_bad ∪ ~/crashwork/bad_*.pkl ∪
    早年 researchAddOn.early_extra_bad）。訊號要 [min(first, k−20), k＋1] 沒有壞 K 棒（k ＝ T 的有效 K 棒序號、first ＝ 型態第一個轉折；
    k−20 起是 ATR20 要用的前收）；持有中進場根之後第一個壞 K 棒 kb ⇒ kb−1 收盤強制賣（記在次一日曆日，Dumb 同式）。
 Q3 可買（登錄 §二）：e ＝ T＋1（日曆）是該股下一根有效 K 棒 ∧ 有成交 ∧ 開盤有效 ⇒ 否則「T＋1 無成交」；開盤鎖漲停（快取 upl）⇒「T＋1 鎖漲停買不到」。
    剔除順序（每筆只記第一個原因）：500 張閘／pit_valid → 壞根 → ATR20 不可算 → T＋1 無成交 → T＋1 鎖漲停。
 Q4 出場（登錄 §二 主臂，先到者；⛔ 不設天數）：ATR20 ＝ T 那根（＝ 買進前一日）往前 20 根真實區間簡單平均（還原；Dumb atr 同式）；
    從進場根 ke（含）起逐根收盤判：a ＝ 收盤 ＜ 下線(j)（下線 ＝ S06 事件那一組的最小平方下線，延伸到第 j 根有效 K 棒序號）；
    b ＝ 收盤 ≤ max(收盤[ke..j]) − 3 × ATR20；a、b 同一根都成立 ⇒ 記「a＆b 同日」；觸發根之後第一根可賣開盤（有成交 ∧ 開盤有效 ∧ 非開盤跌停鎖死）賣；
    可賣開盤在壞根之後或不存在 ⇒ Q2 強制／下市（最後收盤，記次一日曆日）／資料尾仍持有（窗尾照實報、持有天數設限）。
 Q5 組合（登錄 §二）：10 槽、同一檔同時只持一筆、賣後可再進、同日先出後進；候選多於空槽 ⇒ rng.permutation 抽籤（default_rng(1000)；
    只在「當天有候選 ∧ 有空槽」時抽一次 ＝ simulate_mtm 抽籤版同一條；候選依 (e, 代號) 排序）。
    ⚠ 本支只數槽、不算錢 ⇒ 不模擬「min(權益÷10, 現金)」的現金不足（10 槽等權下只影響金額、不影響檔數）；正式跑用引擎，抽籤結果應相同、照報差異。
    世界內一條線（主世界從第一筆訊號起，＝ Dumb「主窗一條權益」）；持有天數 ＝ 賣出日曆位置 − 買進日曆位置（Dumb Z16 同式）。
 Q6 段（登錄 §三）：探索 2017-03-02～2021-12-30｜確認 2022-01-03～資料尾 2026-09-24｜早年 2005 第一個交易日～2014-12-31。
    平均持股 ＝ 段內逐日收盤持股檔數平均（買進日算持有、賣出日不算）；另報空槽比例 ＝ 1 − 平均持股 ÷ 10（⚠ 只是檔數，⛔ 不是登錄的「現金比例」，
    現金比例要價格、留給正式跑）。逐年訊號表依 T 的曆年；實際買進依 e 的曆年。
 Q7 判斷（登錄 §六 步驟 2）：探索段預估平均持股 ＜ 3 ⇒「改只描述」；≥ 3 ⇒「照判」。⛔ 早年、確認段不進這個判斷（只報）。
 Q8 描述臂（月營收年增 ＞ 0）不在本步驟（任務只交主規則頻率表）。
"""
from __future__ import annotations

import argparse
import glob
import gzip
import hashlib
import json
import os
import pickle
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D                              # noqa: E402
from backtest import research11 as R                        # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402
from backtest import patterns as P                          # noqa: E402
from backtest import patterns_all as PA                     # noqa: E402
from backtest import universe_gate as UG                    # noqa: E402
from backtest import researchAddOn as RA                    # noqa: E402
from backtest import researchIndRev_prereg as PRE           # noqa: E402
from backtest import stop_fractal as SFR                    # noqa: E402

UG.set_gate_v2(True)

REG_SHA = "735a20737f9dd17c"
PAT_SHA = "b7b4a05af0341797"
MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
OUT = "backtest/resultsAscTri/freq"
PATALL_EV = "backtest/resultsPatAll/events_S06_上升三角_向上.csv.gz"
VID = "S06"
NS = 10
SEED_ENG = 1000
ATR_X = 3.0
DEG_HOLD = 3.0
WORLDS = {"主": {"data": RR.H2D, "part": "main"}, "早年": {"data": RA.EOTC, "part": "early"}}
SEGS = {"主": {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", None)}, "早年": {"早年": ("2005-01-01", "2014-12-31")}}
REASONS = ["閘外（500張／pit_valid）", "壞根", "ATR20不可算", "T+1無成交", "T+1鎖漲停"]
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


# ═════════════ Q0 偵測器抄錄（只多記上下線；⛔ 判斷逐行同 PA.detect_lines） ═════════════
def _lines_replica(h, l, c, r60):
    n = len(c); lag = PA.B_R
    ph = np.flatnonzero(SFR.swing_lows(-np.asarray(h, float), PA.B_R))
    pl = np.flatnonzero(SFR.swing_lows(np.asarray(l, float), PA.B_R))
    conf_at = {}
    for s in ph:
        conf_at.setdefault(int(s) + lag, []).append((int(s), "H", float(h[s])))
    for s in pl:
        conf_at.setdefault(int(s) + lag, []).append((int(s), "L", float(l[s])))
    piv = []
    out = []
    G = [None, None]
    for b in range(n):
        for gi in (0, 1):
            g = G[gi]
            if g is None:
                continue
            if b - g["conf"] > PA.LIFE:
                G[gi] = None; continue
            if b < g["conf"] + 1:
                continue
            lu = g["fu"]["a"] + g["fu"]["b"] * b; ll = g["fl"]["a"] + g["fl"]["b"] * b
            if g["conv"] and not lu > ll:
                G[gi] = None; continue
            lu1 = g["fu"]["a"] + g["fu"]["b"] * (b - 1); ll1 = g["fl"]["a"] + g["fl"]["b"] * (b - 1)
            if c[b] > lu and c[b - 1] <= lu1:
                if PA._LINE_VID[(g["typ"], 1)] == 6:
                    out.append((b, g["first"], g["fl"]["a"], g["fl"]["b"], g["fu"]["a"], g["fu"]["b"], g["conf"]))
                G[gi] = None
            elif c[b] < ll and c[b - 1] >= ll1:
                G[gi] = None
        new = conf_at.get(b)
        if new:
            piv.extend(new); piv.sort(key=lambda p: p[0])
            G[0] = PA._build_line(piv, b, r60)
            G[1] = PA._build_diamond(piv, b, r60)
    return out


def _dedup(ev):
    res, seen = [], set()
    for e in sorted(set(ev)):
        if e[0] not in seen:
            seen.add(e[0]); res.append(e)
    return res


# ═════════════ 世界 ═════════════
def load_world(wn):
    cfg = WORLDS[wn]; data = cfg["data"]; D.DATA = data
    cal = D.load_calendar(); n0 = len(cal)
    st = pd.read_csv(os.path.join(data, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(st); U = U[U["stock_id"].map(PRE.okcode)].reset_index(drop=True)
    mk = dict(zip(U["stock_id"], U["market"]))
    Z = pickle.load(open(os.path.expanduser(f"~/rluwork/world_{cfg['part']}.pkl"), "rb"))
    if Z["c"].shape[1] != n0:
        raise SystemExit(f"⛔ {wn} 快取日曆長 {Z['c'].shape[1]} ≠ {n0}")
    sids = list(Z["sids"]); ix = {s: i for i, s in enumerate(sids)}
    gate = {"UG.gate3(GATE_V2)∩四碼 檔數": int(len(U)), "快取檔數": len(sids),
            "名單差（本次有、快取沒有）": sorted(set(U["stock_id"]) - set(sids))[:20],
            "名單差（快取有、本次沒有）": sorted(set(sids) - set(U["stock_id"]))[:20]}
    BADPOS = {}; bad_info = {}
    B = pickle.load(open(os.path.expanduser(f"~/crashwork/bad_{cfg['part']}.pkl"), "rb"))
    nocache = []
    for s in sids:
        if s in B:
            a, b = B[s]; BADPOS[s] = set(int(x) for x in a) | set(int(x) for x in b)
        else:
            nocache.append(s)
            _, bad = RA.extra_stock(s, mk.get(s, "twse"), data, cal); BADPOS[s] = set(int(x) for x in np.flatnonzero(np.asarray(bad, bool)[:n0]))
    D.DATA = data
    bad_info["crashwork 沒有、現場補 檔數"] = len(nocache)
    if wn == "早年":
        Wa = pickle.load(open(os.path.join(RA.WORK, "world_早年.pkl"), "rb"))
        if not (len(Wa["cal"]) == n0 and (Wa["cal"] == cal).all()):
            raise SystemExit("⛔ 早年 addonwork 日曆 ≠ 版面日曆")
        EX, cnt = RA.early_extra_bad(Wa, log)
        n_ = int(sum(len(v) for v in BADPOS.values()))
        for s, ks in EX.items():
            if s in BADPOS:
                BADPOS[s] |= set(int(k) for k in ks)
        bad_info["早年另加（reduce_v2＋R8）來源"] = cnt
        bad_info["早年另加新增股日"] = int(sum(len(v) for v in BADPOS.values())) - n_
    D.DATA = data
    W = {"name": wn, "data": data, "cal": cal, "n0": n0, "sids": sids, "ix": ix, "mk": mk,
         "O": np.asarray(Z["o"], float), "PV": np.asarray(Z["pv"], bool), "TRD": np.asarray(Z["trd"], bool)[:, :n0],
         "UPL": np.asarray(Z["upl"], bool)[:, :n0], "DNL": np.asarray(Z["dnl"], bool)[:, :n0], "BADPOS": BADPOS, "gate": gate, "bad_info": bad_info}
    segp = {}
    for sg, (a, b) in SEGS[wn].items():
        x = int(cal.searchsorted(pd.Timestamp(a)))
        y = n0 - 1 if b is None else int(cal.searchsorted(pd.Timestamp(b), side="right")) - 1
        segp[sg] = (x, y)
    W["segp"] = segp
    log(f"[世界 {wn}] {cal[0].date()}～{cal[-1].date()}｜股 {len(sids)}｜段 {{{', '.join(f'{k}: {cal[x].date()}～{cal[y].date()}' for k, (x, y) in segp.items())}}}｜閘 {gate}｜壞根 {bad_info}")
    return W


# ═════════════ 逐股 ═════════════
def stock_job(a):
    wn, sid = a
    W = _G[wn]; D.DATA = W["data"]; cal = W["cal"]; n0 = W["n0"]; i = W["ix"][sid]
    B = R.load_bars(sid, W["mk"].get(sid, "twse"), cal)
    if B is None:
        return sid, None
    df = B["df"]; idx = B["idx"].astype(np.int64); nb = len(idx)
    o, h, l, c = (np.asarray(B[k], float) for k in ("o", "h", "l", "c"))
    # ── Q0 偵測（有效 K 棒 ＝ 還原收盤非缺值，同 detect_calendar）
    cf = df["close"].to_numpy(float)
    bars = np.flatnonzero(np.isfinite(cf))
    hd, ld, cd = df["high"].to_numpy(float)[bars], df["low"].to_numpy(float)[bars], cf[bars]
    r60 = PA._rN(cd, PA.R60)
    ref = _dedup(PA.detect_lines(hd, ld, cd, r60)[VID])
    rep = _lines_replica(hd, ld, cd, r60)
    rep_d = _dedup([(e[0], e[1]) for e in rep])
    if [(int(x), int(y)) for x, y in ref] != [(int(x), int(y)) for x, y in rep_d]:
        raise SystemExit(f"⛔ {wn} {sid}：replica S06 ≠ PA.detect_lines（{len(ref)} vs {len(rep_d)}）")
    line_of = {}
    for e in rep:
        if e[0] not in line_of:
            line_of[e[0]] = e
    det_of_pos = np.full(n0, -1, np.int64); det_of_pos[bars] = np.arange(len(bars))
    bars_eq = bool(len(bars) == nb and (bars == idx).all())
    # ── 母體、壞根、ATR
    f = P.Frame(df, set())
    gate_b = np.asarray(f.gate, bool)[idx]
    bad = np.asarray(B["next_bad"][:nb] == np.arange(nb), bool)
    for p in W["BADPOS"].get(sid, ()):
        k = int(np.searchsorted(idx, p, "left"))
        if k < nb:
            bad[k] = True
    CB = np.r_[0, np.cumsum(bad)]

    def nbad(a_, b_):
        a_ = max(a_, 0); b_ = min(b_, nb - 1)
        return int(CB[b_ + 1] - CB[a_]) if b_ >= a_ else 0
    tr = np.full(nb, np.nan); tr[1:] = np.maximum(h[1:], c[:-1]) - np.minimum(l[1:], c[:-1])
    atr = pd.Series(tr).rolling(20, min_periods=20).mean().to_numpy()
    pv_b = W["PV"][i, idx]
    TRD = W["TRD"][i]; O = W["O"][i]; UPL = W["UPL"][i]; DNL = W["DNL"][i]
    sell_ok = TRD[idx] & np.isfinite(O[idx]) & (O[idx] > 0) & ~DNL[idx]
    nxs = np.full(nb + 1, nb, np.int64)
    for k in range(nb - 1, -1, -1):
        nxs[k] = k if sell_ok[k] else nxs[k + 1]
    bb = np.flatnonzero(bad)
    end_ok = bool(idx[-1] == n0 - 1)
    rows = []
    for (Tb, fb) in ref:
        Tb, fb = int(Tb), int(fb)
        pos = int(bars[Tb]); fpos = int(bars[fb])
        k = int(np.searchsorted(idx, pos))
        if k >= nb or idx[k] != pos:
            rows.append({"sid": sid, "T": pos, "first": fpos, "why": "T不是有效K棒"}); continue
        kf = int(np.searchsorted(idx, fpos))
        rec = {"sid": sid, "T": pos, "first": fpos, "why": None}
        e = pos + 1
        if not (gate_b[k] and pv_b[k]):
            rec["why"] = REASONS[0]
        elif nbad(min(kf, k - 20), k + 1) > 0:
            rec["why"] = REASONS[1]
        elif k < 20 or not np.isfinite(atr[k]) or not atr[k] > 0:
            rec["why"] = REASONS[2]
        elif not (k + 1 < nb and idx[k + 1] == e and e < n0 and TRD[e] and np.isfinite(O[e]) and O[e] > 0):
            rec["why"] = REASONS[3]
        elif UPL[e]:
            rec["why"] = REASONS[4]
        if rec["why"] is not None:
            rows.append(rec); continue
        # ── Q4 出場時點（只用價格路徑；⛔ 不存價格、不算報酬）
        ke = k + 1; A = float(atr[k]); la, lb = line_of[Tb][2], line_of[Tb][3]
        j_ = int(np.searchsorted(bb, ke + 1)); kb = int(bb[j_]) if j_ < len(bb) else None
        lim = kb if kb is not None else nb
        hmax = -np.inf; d = None; typ = None; a_miss = 0
        for j in range(ke, lim):
            hmax = max(hmax, c[j])
            dj = det_of_pos[idx[j]]
            ca = bool(c[j] < la + lb * dj) if dj >= 0 else False
            a_miss += int(dj < 0)
            cb_ = bool(c[j] <= hmax - ATR_X * A)
            if ca or cb_:
                d = j; typ = "a＆b同日" if (ca and cb_) else ("a 型態失敗" if ca else "b 回落3ATR"); break
        S = None
        if d is not None:
            s_ = int(nxs[d + 1]) if d + 1 <= nb else nb
            S = s_ if s_ < lim else None
        if S is not None:
            xpos = int(idx[S]); fk = typ
        elif kb is not None:
            xpos = int(idx[kb - 1]) + 1; fk = "壞根前收盤強制"
        elif end_ok:
            xpos = n0; fk = "資料尾仍持有"
        else:
            xpos = int(idx[nb - 1]) + 1; fk = "下市／停止交易（最後收盤）"
        rec.update({"e": e, "xpos": xpos, "fk": fk, "trig": typ or "", "trig_pos": int(idx[d]) if d is not None else -1, "a_miss": a_miss})
        rows.append(rec)
    return sid, {"rows": rows, "bars_eq": bars_eq, "n_ev": len(ref)}


# ═════════════ Q5 組合：只數槽 ═════════════
def slot_sim(sigs, n0):
    sigs = sorted(sigs, key=lambda r: (r["e"], r["sid"]))
    by = {}
    for r in sigs:
        by.setdefault(r["e"], []).append(r)
    rng = np.random.default_rng(SEED_ENG)
    open_pos = []; held = set(); trades = []; skipped = {"槽滿": 0, "同檔已持有": 0}
    if not sigs:
        return trades, skipped
    for t in range(sigs[0]["e"], n0):
        still = []
        for p in open_pos:
            if p["xpos"] <= t:
                held.discard(p["sid"])
            else:
                still.append(p)
        open_pos = still
        g = by.get(t)
        if not g:
            continue
        cand = [r for r in g if r["sid"] not in held]
        skipped["同檔已持有"] += len(g) - len(cand)
        if len(open_pos) < NS and cand:
            avail = NS - len(open_pos)
            order = rng.permutation(len(cand))
            for q in order[:avail]:
                r = cand[q]; open_pos.append(r); held.add(r["sid"]); trades.append(r)
            skipped["槽滿"] += max(0, len(cand) - avail)
        else:
            skipped["槽滿"] += len(cand)
    return trades, skipped


def dist(x):
    x = np.asarray(x, float)
    if not len(x):
        return {"n": 0}
    return {"n": int(len(x)), "平均": round(float(x.mean()), 1), "中位": float(np.median(x)), "p10": float(np.percentile(x, 10)),
            "p25": float(np.percentile(x, 25)), "p75": float(np.percentile(x, 75)), "p90": float(np.percentile(x, 90)), "最大": int(x.max())}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=4); a = ap.parse_args()
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    reg = reg_check()
    log(f"[登錄] {reg}（sha {REG_SHA} 已驗）")
    J = {"性質": "PREREG上升三角組合層 seq2 §六 步驟 1 頻率表（⛔ 未算、未存任何報酬；出場時點只用價格路徑判）",
         "登錄": f"台股策略線 seq2 sha {REG_SHA}", "型態定義": f"PREREG型態全量 seq3 sha {PAT_SHA} S06 上升三角_向上（patterns_all.detect_lines 原樣）",
         "裁定": "seq358：N_組合 ＋1；探索段預估平均持股 ＜ 3 ⇒ 改只描述、N 退回不計；≥ 3 照判", "世界": {}}
    YR = []; HSEG = []; SIGOUT = {}
    for wn in ("主", "早年"):
        W = load_world(wn); _G[wn] = W
        cal = W["cal"]; n0 = W["n0"]
        jobs = [(wn, s) for s in W["sids"]]
        res = {}
        with Pool(a.procs) as pool:
            for k_, (sid, r) in enumerate(pool.imap_unordered(stock_job, jobs, chunksize=8)):
                res[sid] = r
                if (k_ + 1) % 300 == 0:
                    log(f"  {wn} … {k_ + 1}／{len(jobs)}｜{time.time() - t0:.0f}s")
        rows = [x for r in res.values() if r for x in r["rows"]]
        n_skip = sum(1 for r in res.values() if r is None)
        bars_neq = [s for s, r in res.items() if r and not r["bars_eq"]]
        log(f"[{wn}] 逐股完｜load_bars 不足 260 根 {n_skip} 檔｜偵測有效 K 棒 ≠ load_bars 有效 K 棒 {len(bars_neq)} 檔｜S06 事件 {len(rows)}｜{time.time() - t0:.0f}s")
        Wj = {"資料": W["data"], "日曆": [str(cal[0].date()), str(cal[-1].date())], "閘": W["gate"], "壞根": W["bad_info"],
              "load_bars不足260根檔數": n_skip, "偵測K棒≠load_bars K棒檔數": len(bars_neq), "replica＝PA.detect_lines": "全部逐筆相同（否則已中止）"}
        # ── PatAll 已提交事件檔比對（主）
        if wn == "主":
            pe = pd.read_csv(PATALL_EV, dtype={"sid": str})
            w0 = int(cal.searchsorted(pd.Timestamp("2017-03-02"))); w1 = int(cal.searchsorted(pd.Timestamp("2026-08-24")))
            mine = {(r["sid"], str(cal[r["T"]].date()), str(cal[r["first"]].date())) for r in rows if w0 <= r["T"] <= w1 - 20}
            common = set(pe["sid"]) & {s for s, r in res.items() if r is not None}
            theirs = {(s, t, f_) for s, t, f_ in zip(pe["sid"], pe["T"], pe["first"]) if s in common}
            mine_c = {x for x in mine if x[0] in common}
            Wj["與PatAll已提交S06事件檔比對"] = {"PatAll事件數": int(len(pe)), "兩邊都有的股票": len(common), "PatAll（共同股）": len(theirs),
                                          "本支（共同股、同窗）": len(mine_c), "只在PatAll": len(theirs - mine_c), "只在本支": len(mine_c - theirs),
                                          "只在PatAll例": sorted(theirs - mine_c)[:10], "只在本支例": sorted(mine_c - theirs)[:10],
                                          "本支有、PatAll母體沒有的股票事件數": len([x for x in mine if x[0] not in set(pe["sid"])])}
            log(f"[比對 PatAll] {Wj['與PatAll已提交S06事件檔比對']}")
        # ── 剔除與可買
        buy = [r for r in rows if r["why"] is None]
        trades, skipped = slot_sim(buy, n0)
        tk = {(r["sid"], r["e"]) for r in trades}
        # ── 逐年
        yrs = sorted({cal[r["T"]].year for r in rows})
        for y in yrs:
            ry = [r for r in rows if cal[r["T"]].year == y]
            d = {"世界": wn, "年": y, "S06訊號數": len(ry)}
            for rs in ["T不是有效K棒"] + REASONS:
                d["剔_" + rs] = sum(1 for r in ry if r["why"] == rs)
            d["可買筆數"] = sum(1 for r in ry if r["why"] is None)
            d["實際買進(依買進年)"] = sum(1 for r in trades if cal[min(r["e"], n0 - 1)].year == y)
            YR.append(d)
        # ── 逐日持股
        cnt = np.zeros(n0 + 2, np.int64)
        for r in trades:
            cnt[r["e"]] += 1; cnt[min(r["xpos"], n0 + 1)] -= 1
        hold = np.cumsum(cnt)[:n0]
        segj = {}
        for sg, (x, y) in W["segp"].items():
            hs = hold[x:y + 1]
            tr_s = [r for r in trades if x <= r["e"] <= y]
            bu_s = [r for r in buy if x <= r["e"] <= y]
            sig_s = [r for r in rows if x <= r["T"] <= y]
            hdt = [min(r["xpos"], n0) - r["e"] for r in tr_s]
            fk = pd.Series([r["fk"] for r in tr_s]).value_counts().to_dict() if tr_s else {}
            ndays = y - x + 1; yrs_ = (cal[y] - cal[x]).days / 365.25
            segj[sg] = {"期間": [str(cal[x].date()), str(cal[y].date())], "交易日": int(ndays),
                        "S06訊號數": len(sig_s), "可買筆數": len(bu_s), "實際買進筆數": len(tr_s),
                        "每年訊號": round(len(sig_s) / yrs_, 1), "每年可買": round(len(bu_s) / yrs_, 1), "每年實際買進": round(len(tr_s) / yrs_, 1),
                        "預估平均持股": round(float(hs.mean()), 2), "持股中位": float(np.median(hs)), "持股p10": float(np.percentile(hs, 10)),
                        "持股p90": float(np.percentile(hs, 90)), "0檔日比例": round(float((hs == 0).mean()), 3),
                        "≤2檔日比例": round(float((hs <= 2).mean()), 3), "滿10檔日比例": round(float((hs >= NS).mean()), 3),
                        "空槽比例(檔數，非現金比例)": round(1 - float(hs.mean()) / NS, 3),
                        "持有天數_實際買進": dist(hdt), "持有天數_全部可買(單筆路徑)": dist([min(r["xpos"], n0) - r["e"] for r in bu_s]),
                        "出場種類_實際買進": {k: int(v) for k, v in fk.items()}}
            row = {"世界": wn, "段": sg, **{k: v for k, v in segj[sg].items() if not isinstance(v, (dict, list))}}
            for kk in ("持有天數_實際買進", "持有天數_全部可買(單筆路徑)"):
                for q, v in segj[sg][kk].items():
                    row[f"{kk}_{q}"] = v
            HSEG.append(row)
        # 逐年平均持股（描述）
        yh = {}
        for y in sorted(set(cal.year)):
            m = (cal.year == y)
            if m.any() and np.flatnonzero(m)[-1] >= (trades[0]["e"] if trades else n0):
                yh[int(y)] = round(float(hold[m].mean()), 2)
        Wj.update({"段": segj, "逐年平均持股": yh, "可買未買": skipped, "可買筆數": len(buy), "實際買進筆數": len(trades),
                   "出場a判定時下線無對應K棒次數": int(sum(r.get("a_miss", 0) for r in buy))})
        J["世界"][wn] = Wj
        sg = pd.DataFrame([{"sid": r["sid"], "T": str(cal[r["T"]].date()), "first": str(cal[r["first"]].date()), "剔除": r["why"] or "",
                            "買進日": str(cal[r["e"]].date()) if r.get("e") is not None and r["e"] < n0 else "",
                            "賣出日": (str(cal[r["xpos"]].date()) if r["xpos"] < n0 else "窗尾") if r.get("xpos") is not None else "",
                            "持有天數": (min(r["xpos"], n0) - r["e"]) if r.get("xpos") is not None else "",
                            "出場": r.get("fk", ""), "實際買進": (r["sid"], r.get("e")) in tk} for r in sorted(rows, key=lambda r: (r["T"], r["sid"]))])
        SIGOUT[wn] = sg
        with gzip.open(os.path.join(OUT, f"signals_{wn}.csv.gz"), "wt", encoding="utf-8") as fh:
            sg.to_csv(fh, index=False)
        log(f"[{wn}] 段 {json.dumps({k: (v['預估平均持股'], v['可買筆數'], v['實際買進筆數']) for k, v in segj.items()}, ensure_ascii=False)}")
    exp = J["世界"]["主"]["段"]["探索"]["預估平均持股"]
    J["判斷"] = {"探索段預估平均持股": exp, "門檻": DEG_HOLD, "結果": "改只描述" if exp < DEG_HOLD else "照判",
                "依據": "登錄 seq2 §六 步驟 2（＝ seq325 退化門檻）；⛔ 只看探索段"}
    J["讀法"] = __doc__.split("═══ 讀法")[1]
    J["時間"] = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")
    pd.DataFrame(YR).to_csv(os.path.join(OUT, "freq_by_year.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(HSEG).to_csv(os.path.join(OUT, "hold_by_segment.csv"), index=False, encoding="utf-8-sig")
    json.dump(J, open(os.path.join(OUT, "freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[判斷] 探索段預估平均持股 {exp} ⇒ {J['判斷']['結果']}｜{time.time() - t0:.0f}s")
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
