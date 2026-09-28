# -*- coding: utf-8 -*-
"""PREREG長線戰法 seq1 件 D：週線達華斯箱型（台股策略線 登錄 sha dce9829bd0736d4f；裁定 seq272 發號，全件 N ＋3）——回測線，2026-09-29。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLongD [--procs 2] [--seeds 200] [--reps 200]
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchLongD_check.py

⭐ 新件 ⇒ 共用閘開「-KY創」（裁定 seq271 §二）：UG.set_innov_ky(True)（本程式 import 後第一件事）；面板（panel_ext 等）是舊閘建的 ⇒ 母體再與 gate3（開）交集
═══ 週 K（登錄 §二「週 K 定義同 PREREG週線 §一」）═══
 直接 import researchWeekly：weeks_of（週一起算的日曆週）、weekly_bars（有效 K 棒 ⇒ 週開高低收量）；⛔ 不另寫週 K
 壞根週（research11.load_bars 的壞根所在週與前後各 1 週，同 researchWeekly W2）不產生買進訊號；持有中碰到壞根 ⇒ 壞根前一根收盤出（計數必報）
 資料：PREREG事件 seq2 的接合版面（researchEvt.ST：早年 950ad26e12 ≤ 2014 ＋ main edc6f ≥ 2015；還原價）；母體 ＝ researchEvt.eligibility（W1 eligible、含已下市；2015 以前只上市）
═══ 達華斯箱型（登錄 §二寫死；⭐ 本線落地讀法 D 標，看任何數字前寫死）═══
 D1 箱頂：某週週高 ＞ 前 52 週週高最大值（52 週新高；該股週序列第 52 週起）⇒ 候選箱頂；之後 3 週的週高都 ＜ 它 ⇒ 第 3 週收盤確認箱頂
    確認前任一週週高 ≥ 候選 ⇒ 候選作廢（若該週本身又是 52 週新高 ⇒ 成為新候選）
 D2 箱底：自候選箱頂週（含）起，第一組「連續 3 週週低嚴格墊高」的第一週週低 ＝ 箱底（第 3 週收盤確認）
 D3 箱成形 ＝ 箱頂、箱底都確認；買：箱成形之後某週週收 ＞ 箱頂 ⇒ 下一個日曆週第一根有效 K 棒開盤買（該週沒有 K 棒、或開盤無效／漲停 ⇒ 放棄這個訊號）
    成形後、突破前週收 ＜ 箱底 ⇒ 箱子作廢、重找（本線補：原文沒寫突破前跌破怎麼辦，照常見實作）；突破週落在壞根週 ⇒ 放棄
 D4 賣：持有中某週週收 ＜ 目前箱底 ⇒ 下一個有效 K 棒開盤賣（當週先用舊箱底判，再更新箱子）
    持有中週高 ＞ 持有以來最高（含原箱頂）⇒ 新候選箱頂，照 D1／D2 形成新箱；新箱成形 ⇒ 箱底改成新箱底（原文「新箱成形前原箱底有效」）
 D5 資料尾：持有到資料最後一根 ⇒ T1（xpos ＝ ncal、末日收盤計）；停止交易 ⇒ 引擎 stop_force；賣出後同一檔重新找箱（新候選要在賣出週之後）
 D6 訊號表與組合無關（每筆照「有買到」走完自己的路徑；組合沒買到的筆也照走，⇒ 同一檔的下一個訊號只在上一筆賣出後）
 D7 日線版（描述臂、不計 N）：同規則換成有效 K 棒：250 根新高、之後 3 根、3 根墊高、收盤 ＞ 箱頂 ⇒ 下一根開盤買、收盤 ＜ 箱底 ⇒ 下一根開盤賣；壞根前後 1 根不產生訊號
═══ 組合（登錄 §二）═══
 engine research11.simulate_mtm：N ∈ {10, 20}、等權、同日候選多於空槽 ⇒ RS 高者先（pick="relvol"，relvol 欄放 RS）；RS ＝ 2×r63 ＋ r126 ＋ r189 ＋ r252（訊號日、有效 K 棒還原收盤）
 母體：訊號日當時 eligible（2015 以前只上市）；成本 0.585%；stop_force 開；200 顆種子 default_rng(1000＋r)（RS 同分才抽籤）
 兩條權益：主 ＝ 進場 2017-03-02～2026-08-24 的訊號（探索 2017-03-02～2021-12-30、確認 2022-01-03～2026-08-24）；早年 ＝ 進場 2005-01-03～2014-12-31（只上市）
 退化（挑前排除）：探索段平均持股 ＜ N÷2 或現金 ＞ 30%；挑格：探索段先合格、再比值；判：確認、早年對 0050 同段、取較嚴
 假訊號臂（登錄 K4「同股隨機週進場同持有長度」）：挑中格每一筆換成同一檔、同一條權益窗內、eligible 且下週可買的隨機一週進場、持有同樣根數（收盤出）；
   RS 照原筆；reps 次、引擎種子 1000＋i、抽樣 default_rng([20260929, 4, i])；p ＝ 假年化 ≥ 本格年化中位 的比例
 另報：逐筆（全部 eligible 訊號）平均淨報酬（g − 0.585%）、勝率、平均持有根數（對照布考斯基：美股 2001～2010 週線 +6.9%／筆、日線 0.0%）
 新規矩 ③：挑中格確認或早年「合格／另列」⇒ 描述：檔數 5、停損 10%（simulate_mtm stop fix）
輸出 backtest/resultsLongD/
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import universe_gate as UG
UG.set_innov_ky(True)                                          # ⭐ 新件：共用閘開「-KY創」（裁定 seq271 §二）
from backtest import data as D
from backtest import tradability as TR
from backtest import research11 as R11
from backtest import rerun17 as RR
from backtest import researchEvt as EV
from backtest import researchWeekly as WK                      # ⭐ 週 K 只 import（weeks_of、weekly_bars）
from backtest import chart_svg as CS

ST = EV.ST
OUT = "backtest/resultsLongD"
F_HTML = "長線戰法_件D_週線達華斯_20260929.html"
COST = 0.00585
NS = (10, 20)
WINS = {"主": ("2017-03-02", "2026-08-24"), "早年": ("2005-01-03", "2014-12-31")}
SEGS = {"探索": ("主", "2017-03-02", "2021-12-30"), "確認": ("主", "2022-01-03", "2026-08-24"), "早年": ("早年", "2005-01-03", "2014-12-31")}
ORDER = {"不合格": 0, "另列": 1, "合格": 2}
_G: dict = {}
_W: dict = {}


def box_machine(H, L, C, near, look):
    """通用箱型狀態機（週 or 日）。H／L／C ＝ 該股 bar 序列；near ＝ 不產生買進訊號的 bar；look ＝ 新高回看（52 週／250 根）。
    回 [(買訊 bar, 賣訊 bar 或 None, 買時箱頂, 買時箱底, 賣時箱底)]；賣訊 bar ＝ 收盤 ＜ 箱底 的那根（下一根開盤賣）。"""
    n = len(C); out = []
    b = look
    mx = np.full(n, np.nan)
    for i in range(look, n):
        mx[i] = H[i - look:i].max()
    cand = None; top_ok = False; bot = None
    while b < n:
        # ── 空手：找箱 ──
        if cand is None or not (top_ok and bot is not None):
            pass
        ready = cand is not None and top_ok and bot is not None
        if ready and C[b] > cand[1]:
            if not near[b]:
                # 買；持有
                top, B_ = cand[1], bot; hi = max(top, H[b]); nc = None; ntop_ok = False; nbot = None
                s = None
                for j in range(b + 1, n):
                    if C[j] < B_:
                        s = j; break
                    # 新箱
                    if H[j] > hi:
                        hi = H[j]; nc = (j, H[j]); ntop_ok = False; nbot = None
                    elif nc is not None:
                        if not ntop_ok and j - nc[0] == 3 and H[nc[0] + 1:j + 1].max() < nc[1]:
                            ntop_ok = True
                    if nc is not None and nbot is None and j - 2 >= nc[0] and L[j - 2] < L[j - 1] < L[j]:
                        nbot = L[j - 2]
                    if nc is not None and ntop_ok and nbot is not None:
                        B_ = nbot; nc = None; ntop_ok = False; nbot = None
                out.append((b, s, top, bot, B_))
                if s is None:
                    return out
                b = s + 1; cand = None; top_ok = False; bot = None
                continue
            cand = None; top_ok = False; bot = None
            b += 1; continue
        if ready and C[b] < bot:
            cand = None; top_ok = False; bot = None
        if np.isfinite(mx[b]) and H[b] > mx[b]:
            cand = (b, H[b]); top_ok = False; bot = None
        elif cand is not None:
            if H[b] >= cand[1]:
                cand = None; top_ok = False; bot = None
            elif not top_ok and b - cand[0] == 3:
                top_ok = True
        if cand is not None and bot is None and b - 2 >= cand[0] and L[b - 2] < L[b - 1] < L[b]:
            bot = L[b - 2]
        b += 1
    return out


def _init(cal):
    D.DATA = ST
    wk, wf, wl = WK.weeks_of(cal)
    _G.update(cal=cal, wk=wk, wf=wf, wl=wl)


def load_one(args):
    sid, mk = args
    cal, wk = _G["cal"], _G["wk"]; n = len(cal)
    st = D.load_stock(sid, mk, cal)
    if st is None:
        return sid, None
    df = st.df
    o, h, l, c = (df[k_].to_numpy(float) for k_ in ("open", "high", "low", "close"))
    vol = pd.to_numeric(df["volume"], errors="coerce").to_numpy(float)
    valid = np.isfinite(c)
    raw = pd.read_csv(os.path.join(ST, "stocks", sid + ".csv"), dtype={"date": str}, usecols=["date", "market", "amount"]).drop_duplicates("date")
    raw.index = pd.to_datetime(raw["date"]); raw = raw.reindex(cal)
    twse = (raw["market"].ffill() == "twse").to_numpy(); amt = pd.to_numeric(raw["amount"], errors="coerce").to_numpy(float)
    tb = TR.one(sid, cal); trd, up = np.asarray(tb["trd"], bool), np.asarray(tb["up_o"], bool)
    out = {"valid": valid, "nbars": np.cumsum(valid), "amt": amt}
    B = R11.load_bars(sid, mk, cal)
    if B is None:
        out["trades"] = {"W": [], "D": []}; return sid, out
    idx = B["idx"]; nb = B["next_bad"]; bad_k = nb[:len(idx)] == np.arange(len(idx))
    bad_day = np.zeros(n, bool); bad_day[idx[bad_k]] = True
    cb = np.r_[0, np.cumsum(bad_day)]
    cv = c[idx]
    rs = np.full(len(idx), np.nan)
    if len(idx) > 252:
        k_ = np.arange(252, len(idx))
        rs[k_] = 2 * (cv[k_] / cv[k_ - 63] - 1) + (cv[k_] / cv[k_ - 126] - 1) + (cv[k_] / cv[k_ - 189] - 1) + (cv[k_] / cv[k_ - 252] - 1)
    rs_day = np.full(n, np.nan); rs_day[idx] = rs
    buy_ok = lambda d: bool(trd[d] and np.isfinite(o[d]) and o[d] > 0 and not up[d])
    last_day = int(idx[-1])

    def finish(sd, ed, xd, kind):
        """出場：xd ＝ 賣出那天（開盤賣）或 None（持有到尾）；中途壞根 ⇒ 壞根前一根收盤出。"""
        end = xd if xd is not None else last_day
        if cb[end + 1] - cb[ed + 1] > 0:                                   # (ed, end] 有壞根
            fb = ed + 1 + int(np.flatnonzero(bad_day[ed + 1:end + 1])[0])
            pv = idx[idx < fb]; xp = int(pv[-1]) if len(pv) and pv[-1] > ed else ed
            return xp, float(c[xp] / o[ed] - 1.0), "壞根前出"
        if xd is not None:
            return int(xd), float(o[xd] / o[ed] - 1.0), kind
        if last_day == n - 1:
            return n, float(c[last_day] / o[ed] - 1.0), "T1 補"
        return n, float(c[last_day] / o[ed] - 1.0), "停止交易（引擎 stop_force）"
    TRS = {"W": [], "D": []}
    # 週
    wks, WO, WH, WL, WC, WV = WK.weekly_bars(valid, o, h, l, c, vol, wk)
    if len(wks) > 60:
        ix = np.flatnonzero(valid); w_ = wk[ix]; stt = np.r_[0, np.flatnonzero(np.diff(w_)) + 1]; en = np.r_[stt[1:], len(ix)] - 1
        wfirst, wlast = ix[stt], ix[en]
        badw = np.zeros(int(wk.max()) + 2, bool); badw[wk[bad_day]] = True
        near = badw[wks] | badw[np.maximum(wks - 1, 0)] | badw[wks + 1]
        for bb, s_, top, bot, bfin in box_machine(WH, WL, WC, near, 52):
            if bb + 1 >= len(wks) or wks[bb + 1] != wks[bb] + 1:
                continue                                                  # 下一個日曆週沒有 K 棒 ⇒ 放棄
            ed = int(wfirst[bb + 1])
            if ed != int(_G["wf"][wks[bb + 1]]) or not buy_ok(ed):             # 下週第一個交易日要有 K 棒、可買
                continue
            xd = int(wfirst[s_ + 1]) if (s_ is not None and s_ + 1 < len(wks)) else None
            xp, g, kind = finish(int(wlast[bb]), ed, xd, "週收破箱底")
            TRS["W"].append({"sid": sid, "pos": int(wlast[bb]), "entry_pos": ed, "xpos_DB": xp, "g_DB": g, "kind": kind, "rs": float(rs_day[wlast[bb]]),
                             "top": float(top), "bot": float(bot), "bot_exit": float(bfin), "hold": int(((idx >= ed) & (idx <= min(xp, n - 1))).sum())})
    # 日（描述臂）
    Hh, Ll, Cc = h[idx], l[idx], cv
    nearD = bad_k.copy(); nearD[1:] |= bad_k[:-1]; nearD[:-1] |= bad_k[1:]
    for bb, s_, top, bot, bfin in box_machine(Hh, Ll, Cc, nearD, 250):
        if bb + 1 >= len(idx):
            continue
        ed = int(idx[bb + 1])
        if not buy_ok(ed):
            continue
        xd = int(idx[s_ + 1]) if (s_ is not None and s_ + 1 < len(idx)) else None
        xp, g, kind = finish(int(idx[bb]), ed, xd, "收盤破箱底")
        TRS["D"].append({"sid": sid, "pos": int(idx[bb]), "entry_pos": ed, "xpos_DB": xp, "g_DB": g, "kind": kind, "rs": float(rs_day[idx[bb]]),
                         "top": float(top), "bot": float(bot), "bot_exit": float(bfin), "hold": int(((idx >= ed) & (idx <= min(xp, n - 1))).sum())})
    out["trades"] = TRS
    out["twse"] = twse
    out["buyable_next_week"] = None
    return sid, out


def _stats(W, o, segs, N):
    eq = np.asarray(o["equity"], float); hv = np.asarray(o["hold_val"], float)
    row = {}
    for sg, (x, y) in segs.items():
        c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], x, y)
        row[f"{sg}_年化"] = float(c_); row[f"{sg}_回落"] = float(m_)
        row[f"{sg}_現金"] = float(1.0 - np.mean(hv[x:y + 1] / eq[x:y + 1]))
    return row, eq


def run_cell(job):
    mode, win, N, r, extra = job
    W = _W; sig = W["SIG"][(mode, win)]
    aud = []
    o = R11.simulate_mtm(sig, "DB", N, np.random.default_rng(1000 + r), W["closes"], W["opens"], W["NP"], return_equity=True,
                         log=[], d_max=None, pick="relvol", queue_days=0, stop_force=W["SF"], audit=aud, **(extra or {}))
    row, eq = _stats(W, o, W["SEGP"][win], N)
    cnt = np.zeros(len(eq) + 1)
    for a_ in aud:
        cnt[a_["t"]] += 1 if a_["side"] == "buy" else -1
    hold = np.cumsum(cnt)[:len(eq)]
    for sg, (x, y) in W["SEGP"][win].items():
        row[f"{sg}_持股"] = float(np.mean(hold[x:y + 1]))
    row.update({"mode": mode, "win": win, "N": N, "r": r, "trades": int(o["trades"]), "eq_sha": hashlib.sha256(eq.tobytes()).hexdigest()[:16]})
    return row


def run_fake(job):
    mode, win, N, i = job
    W = _W; base = W["SIG"][(mode, win)]
    rng = np.random.default_rng([20260929, 4, i])
    rows = []
    for r in base.itertuples(index=False):
        opts = W["FAKEPOS"].get((r.sid, win))
        if opts is None or not len(opts):
            continue
        ed = int(opts[rng.integers(0, len(opts))])
        P = W["PX"][r.sid]; idx = P["idx"]
        ke = int(np.searchsorted(idx, ed)); kx = min(ke + max(int(r.hold) - 1, 0), len(idx) - 1)
        xp = int(idx[kx]); g = float(P["c"][kx] / P["o"][ke] - 1.0)
        rows.append((r.sid, ed - 1, ed, xp, g, r.relvol))
    sig = pd.DataFrame(rows, columns=["sid", "pos", "entry_pos", "xpos_DB", "g_DB", "relvol"])
    o = R11.simulate_mtm(sig, "DB", N, np.random.default_rng(1000 + i), W["closes"], W["opens"], W["NP"], return_equity=True,
                         log=[], d_max=None, pick="relvol", queue_days=0, stop_force=W["SF"])
    row, _ = _stats(W, o, W["SEGP"][win], N)
    row.update({"i": i, "win": win, "筆": len(sig)})
    return row


def label(c, m, b):
    return "合格" if (c > b["cagr"] and c / abs(m) >= b["cagr"] / abs(b["mdd"])) else ("另列" if c > b["cagr"] else "不合格")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); ap.add_argument("--seeds", type=int, default=200)
    ap.add_argument("--reps", type=int, default=200); ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    log(f"===== researchLongD {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜seeds {a.seeds} reps {a.reps}｜UG.INNOV_KY＝{UG.INNOV_KY}｜stop_force 開 =====")
    S = {"件": "PREREG長線戰法 seq1 件 D 週線達華斯箱型（登錄 sha dce9829bd0736d4f；裁定 seq272）", "共用閘 -KY創": UG.INNOV_KY}
    D.DATA = ST
    cal = D.load_calendar(); n = len(cal)
    roster = pd.read_csv(os.path.join(ST, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(roster); mk = dict(zip(roster["stock_id"], roster["market"]))
    sids = sorted(set(U["stock_id"]) & {f[:-4] for f in os.listdir(os.path.join(ST, "stocks"))})
    if a.limit:
        sids = sids[::max(1, len(sids) // a.limit)]
    with Pool(a.procs, initializer=_init, initargs=(cal,)) as pool:
        P = {s: v for s, v in pool.imap_unordered(load_one, [(s, mk.get(s, "twse")) for s in sids], chunksize=16) if v is not None}
    sids = [s for s in sids if s in P]
    log(f"[讀檔] {len(sids)} 檔（gate3 innov_ky 開）｜{time.time() - T0:.0f}s")
    E, rules = EV.eligibility(cal, P, sids, log)
    ix = {s: i for i, s in enumerate(sids)}
    bi = int(cal.searchsorted(pd.Timestamp("2015-01-05")))
    WP = {k: (int(cal.searchsorted(pd.Timestamp(x))), int(cal.searchsorted(pd.Timestamp(y)))) for k, (x, y) in WINS.items()}
    SEGP = {"主": {}, "早年": {}}
    for sg, (w, x, y) in SEGS.items():
        SEGP[w][sg] = (int(cal.searchsorted(pd.Timestamp(x))), int(cal.searchsorted(pd.Timestamp(y))))
    ALL = {}
    for mode in ("W", "D"):
        rows = [dict(t) for s in sids for t in P[s]["trades"][mode]]
        T = pd.DataFrame(rows)
        T["elig"] = [bool(E[ix[s], p]) and (p >= bi or bool(P[s]["twse"][p])) for s, p in zip(T["sid"], T["pos"])]
        T["win"] = np.select([(T["entry_pos"] >= WP["主"][0]) & (T["entry_pos"] <= WP["主"][1]), (T["entry_pos"] >= WP["早年"][0]) & (T["entry_pos"] <= WP["早年"][1])], ["主", "早年"], "")
        T["seg"] = ""
        for sg, (w, x, y) in SEGS.items():
            px = SEGP[w][sg]
            T.loc[(T["entry_pos"] >= px[0]) & (T["entry_pos"] <= px[1]), "seg"] = sg
        T["relvol"] = T["rs"].fillna(-1e9)
        ALL[mode] = T
        T.to_csv(os.path.join(OUT, f"trades_{mode}.csv.gz"), index=False, float_format="%.17g")
    # 逐筆統計（全部 eligible 訊號）
    TS = {}
    for mode in ("W", "D"):
        T = ALL[mode]
        for sg in SEGS:
            g = T[T["elig"] & (T["seg"] == sg)]
            TS[f"{'週' if mode == 'W' else '日'}｜{sg}"] = {"筆": int(len(g)), "平均淨報酬": float((g["g_DB"] - COST).mean()) if len(g) else None,
                                                         "勝率": float(((g["g_DB"] - COST) > 0).mean()) if len(g) else None,
                                                         "平均持有根數": float(g["hold"].mean()) if len(g) else None, "出場方式": g["kind"].value_counts().to_dict()}
    S["逐筆（全部 eligible 訊號）"] = TS
    log(f"[逐筆] {json.dumps(TS, ensure_ascii=False)[:1500]}")
    # 引擎輸入
    need = sorted(set().union(*[set(ALL[m].loc[ALL[m]["elig"] & (ALL[m]["win"] != ""), "sid"]) for m in ("W", "D")]))
    closes, opens = RR.load_prices(need, cal, pd.Series(mk), "branch")
    closes, opens = RR.pad_px_t1(closes, opens)
    SF = R11.stop_force_days(R11.valid_from_data(need, pd.Series(mk), cal), WP["主"][1])
    SIG = {}
    for mode in ("W", "D"):
        for win in WINS:
            g = ALL[mode][ALL[mode]["elig"] & (ALL[mode]["win"] == win)]
            SIG[(mode, win)] = g[["sid", "pos", "entry_pos", "xpos_DB", "g_DB", "relvol", "hold"]].sort_values(["entry_pos", "sid"]).reset_index(drop=True)
    _W.update(SIG=SIG, closes=closes, opens=opens, NP=n + 1, SF=SF, SEGP=SEGP)
    bench = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy(float)).ffill().to_numpy(float)
    B50 = {sg: RR.bench_row(cal, bench, *SEGP[w][sg][:1], SEGP[w][sg][1] + 1) for sg, (w, x, y) in SEGS.items()}
    S["0050"] = B50
    S["訊號數（eligible、窗內）"] = {f"{m}｜{w}": int(len(SIG[(m, w)])) for m in ("W", "D") for w in WINS}
    jobs = [(m, w, N, r, None) for m in ("W", "D") for w in WINS for N in NS for r in range(a.seeds)]
    t0 = time.time()
    with Pool(a.procs) as pool:
        SEED = pd.DataFrame(pool.map(run_cell, jobs, chunksize=4))
    log(f"[組合] {len(jobs)} 次｜{time.time() - t0:.0f}s")
    SEED.to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False, float_format="%.17g")
    PT = []
    for m in ("W", "D"):
        for N in NS:
            row = {"格": f"{'週' if m == 'W' else '日'}_N{N}", "mode": m, "N": N}
            for sg, (w, x, y) in SEGS.items():
                g = SEED[(SEED["mode"] == m) & (SEED["win"] == w) & (SEED["N"] == N)]
                c, mm = float(g[f"{sg}_年化"].median()), float(g[f"{sg}_回落"].median())
                row.update({f"{sg}_年化": c, f"{sg}_回落": mm, f"{sg}_比值": c / abs(mm), f"{sg}_標籤": label(c, mm, B50[sg]),
                            f"{sg}_持股": float(g[f"{sg}_持股"].median()), f"{sg}_現金": float(g[f"{sg}_現金"].median())})
            PT.append(row)
    PT = pd.DataFrame(PT)
    PT["退化"] = (PT["探索_持股"] < PT["N"] / 2) | (PT["探索_現金"] > 0.30)
    cand = PT[(PT["mode"] == "W") & ~PT["退化"]]
    pk = None
    if len(cand):
        q = cand[cand["探索_標籤"] == "合格"] if (cand["探索_標籤"] == "合格").any() else cand
        pk = q.sort_values(["探索_比值", "探索_年化", "N"], ascending=[False, False, True]).iloc[0]["格"]
    S["退化（挑前排除；週線 2 格）"] = PT.loc[(PT["mode"] == "W") & PT["退化"], "格"].tolist()
    S["挑中格"] = pk
    J = {}
    if pk:
        pr = PT.set_index("格").loc[pk]
        J = {"確認": pr["確認_標籤"], "早年": pr["早年_標籤"], "件標籤": min((pr["確認_標籤"], pr["早年_標籤"]), key=lambda x: ORDER[x])}
    S["判定"] = J
    PT.to_csv(os.path.join(OUT, "cells.csv"), index=False, float_format="%.17g")
    log(f"[挑格] {pk}｜{J}｜退化 {S['退化（挑前排除；週線 2 格）']}")
    # 假訊號
    if pk:
        N = int(pk.split("_N")[1])
        PX = {}
        for s in need:
            st = D.load_stock(s, mk.get(s, "twse"), cal); cc = st.df["close"].to_numpy(float); oo = st.df["open"].to_numpy(float)
            ii = np.flatnonzero(np.isfinite(cc)); PX[s] = {"idx": ii, "c": cc[ii], "o": oo[ii], "oo": oo}
        tb_cache = {}
        FP = {}
        wk, wf, wl = WK.weeks_of(cal)
        for win in WINS:
            x0, x1 = WP[win]
            for s in set(SIG[("W", win)]["sid"]):
                if s not in tb_cache:
                    t_ = TR.one(s, cal); tb_cache[s] = (np.asarray(t_["trd"], bool), np.asarray(t_["up_o"], bool))
                trd, up = tb_cache[s]; oo = PX[s]["oo"]
                cands = [int(d) for d in wf[1:] if x0 <= d <= x1 and trd[d] and np.isfinite(oo[d]) and oo[d] > 0 and not up[d] and E[ix[s], d - 1]]
                FP[(s, win)] = np.array(cands, int)
        _W.update(FAKEPOS=FP, PX=PX)
        with Pool(a.procs) as pool:
            FR = pd.DataFrame(pool.map(run_fake, [("W", w, N, i) for w in WINS for i in range(a.reps)], chunksize=4))
        FR.to_csv(os.path.join(OUT, "fake.csv.gz"), index=False, float_format="%.17g")
        pr = PT.set_index("格").loc[pk]
        S["假訊號臂（同股隨機週、同持有根數）"] = {sg: {"p（假年化 ≥ 本格）": float(np.mean(FR[FR["win"] == w][f"{sg}_年化"] >= pr[f"{sg}_年化"])),
                                                 "假年化中位": float(FR[FR["win"] == w][f"{sg}_年化"].median())} for sg, (w, x, y) in SEGS.items()}
        log(f"[假訊號] {S['假訊號臂（同股隨機週、同持有根數）']}")
        trig = J["確認"] in ("合格", "另列") or J["早年"] in ("合格", "另列")
        S["新規矩③"] = "要跑" if trig else "不適用（挑中格確認、早年皆非合格／另列）"
        if trig:
            sens = {}
            for nm, NN, ex in (("檔數 5", 5, None), ("停損 10%", N, {"stop": ("fix", 0.10)})):
                with Pool(a.procs) as pool:
                    SR = pd.DataFrame(pool.map(run_cell, [("W", w, NN, r, ex) for w in WINS for r in range(a.seeds)], chunksize=4))
                sens[nm] = {sg: [float(SR[SR["win"] == w][f"{sg}_年化"].median()), float(SR[SR["win"] == w][f"{sg}_回落"].median())] for sg, (w, x, y) in SEGS.items()}
            S["新規矩③ 描述"] = sens
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    page(S, PT, ALL, cal, mk)
    report(S, PT)
    log(f"[完] {time.time() - T0:.0f}s")


def P_(x, d=2):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—"
    return "—" if not np.isfinite(x) else f"{x * 100:+.{d}f}%"


def report(S, PT):
    J = S["判定"]; pk = S["挑中格"]; B = S["0050"]
    L = ["# PREREG長線戰法 seq1 件 D：週線達華斯箱型", "",
         f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。登錄 sha dce9829bd0736d4f；裁定 seq272。回測線。⭐ stop_force 開；T1 開；共用閘「-KY創」開（新件）。引用請寫「回測 PREREG長線戰法 件D」。", ""]
    if pk:
        pr = PT.set_index("格").loc[pk]
        tw, td = S["逐筆（全部 eligible 訊號）"]["週｜確認"], S["逐筆（全部 eligible 訊號）"]["日｜確認"]
        L.append(f"**結論：挑中 {pk}：確認段 {P_(pr['確認_年化'])}／{P_(pr['確認_回落'])}（{pr['確認_標籤']}）、早年 {P_(pr['早年_年化'])}／{P_(pr['早年_回落'])}（{pr['早年_標籤']}）⇒ 件標籤 {J['件標籤']}；"
                 f"逐筆（確認段）週線平均淨 {P_(tw['平均淨報酬'])}、勝率 {tw['勝率'] * 100:.0f}%，日線 {P_(td['平均淨報酬'])}、勝率 {td['勝率'] * 100:.0f}%。**")
    L += ["", "| 格 | 探索 | 確認 | 早年 | 探索 持股／現金 | 退化 |", "|---|---|---|---|---|---|"]
    for _, r in PT.iterrows():
        L.append(f"| {r['格']}{'（描述）' if r['mode'] == 'D' else ''} | {P_(r['探索_年化'])}／{P_(r['探索_回落'])}（{r['探索_標籤']}） | {P_(r['確認_年化'])}／{P_(r['確認_回落'])}（{r['確認_標籤']}） | "
                 f"{P_(r['早年_年化'])}／{P_(r['早年_回落'])}（{r['早年_標籤']}） | {r['探索_持股']:.1f}／{r['探索_現金'] * 100:.0f}% | {'是' if r['退化'] else ''} |")
    L.append(f"| 0050 | {P_(B['探索']['cagr'])}／{P_(B['探索']['mdd'])} | {P_(B['確認']['cagr'])}／{P_(B['確認']['mdd'])} | {P_(B['早年']['cagr'])}／{P_(B['早年']['mdd'])} | | |")
    L += ["", "## 逐筆（全部 eligible 訊號；對照布考斯基 美股 2001～2010：週線 +6.9%／筆、日線 0.0%）", "", "```", json.dumps(S["逐筆（全部 eligible 訊號）"], ensure_ascii=False, indent=1), "```", "",
          f"- 訊號數：{json.dumps(S['訊號數（eligible、窗內）'], ensure_ascii=False)}", f"- 退化（挑前排除）：{S['退化（挑前排除；週線 2 格）']}；挑中：{pk}",
          f"- 假訊號臂：{json.dumps(S.get('假訊號臂（同股隨機週、同持有根數）'), ensure_ascii=False)}", f"- 新規矩 ③：{S.get('新規矩③')}｜{json.dumps(S.get('新規矩③ 描述'), ensure_ascii=False)}",
          "- 日線版只描述（不計 N）；「穩」照 seq253（組合層本件不寫「穩」）", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L))


def page(S, PT, ALL, cal, mk):
    pk = S["挑中格"]; B = S["0050"]
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0] + "\ntd.l,th.l{text-align:left}"
    names = pd.read_csv(os.path.join(ST, "meta", "stocks.csv"), dtype=str).drop_duplicates("stock_id").set_index("stock_id")["name"]
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>長線戰法 件D 週線達華斯</title>", f"<style>{CSS}</style></head><body><main>", "<h1>長線戰法 件 D：週線達華斯箱型</h1>",
         "<p class='lead'>箱頂＝創 52 週新高後 3 週都沒再過；箱底＝之後第一組連續 3 週墊高的低點；週收盤突破箱頂 ⇒ 下週第一天開盤買；週收盤跌破箱底 ⇒ 下週第一天開盤賣（創新高後會重畫新箱、箱底跟著上移）。"
         "日線版＝同一套規則換成日 K（只描述）。都扣成本 0.585%。</p>",
         "<h2>對照表（年化／回落；標籤對 0050 同段）</h2><div class='wrap'><table><tr><th class='l'>格</th><th>探索 17-21</th><th>確認 22-26</th><th>早年 05-14</th></tr>"]
    for _, r in PT.iterrows():
        H.append(f"<tr{' class=pick' if r['格'] == pk else ''}><td class='l'>{r['格']}{'（描述）' if r['mode'] == 'D' else ''}</td>"
                 + "".join(f"<td>{P_(r[f'{sg}_年化'])}／{P_(r[f'{sg}_回落'])}<br>{r[f'{sg}_標籤']}</td>" for sg in ("探索", "確認", "早年")) + "</tr>")
    H.append("<tr><td class='l'>0050</td>" + "".join(f"<td>{P_(B[sg]['cagr'])}／{P_(B[sg]['mdd'])}</td>" for sg in ("探索", "確認", "早年")) + "</tr></table></div>")
    TS = S["逐筆（全部 eligible 訊號）"]
    H.append("<h2>逐筆（每一筆訊號平均）</h2><div class='wrap'><table><tr><th class='l'>版本｜段</th><th>筆</th><th>平均淨報酬</th><th>勝率</th><th>平均持有（交易日）</th></tr>")
    for k, v in TS.items():
        H.append(f"<tr><td class='l'>{k}</td><td>{v['筆']}</td><td>{P_(v['平均淨報酬'])}</td><td>{(v['勝率'] or 0) * 100:.0f}%</td><td>{(v['平均持有根數'] or 0):.0f}</td></tr>")
    H.append("</table></div><p class='note'>對照：布考斯基（美股 2001～2010）週線 +6.9%／筆、日線 0.0%。</p>")
    # 例子：週線、確認段、eligible；淨報酬 最好／中位／最差
    T = ALL["W"]; g = T[T["elig"] & (T["seg"] == "確認")].sort_values("g_DB").reset_index(drop=True)
    picks = [] if not len(g) else [("最差", 0), ("中位", len(g) // 2), ("最好", len(g) - 1)]
    H.append("<h2>例子（週線、確認段）</h2>" + CS.legend_html())
    D.DATA = ST
    for lab, i in picks:
        r = g.iloc[i]; s = r["sid"]; e = int(r["entry_pos"]); x = min(int(r["xpos_DB"]), len(cal) - 1)
        df = D.load_stock(s, mk.get(s, "twse"), cal).df
        i0 = max(0, e - 120); i1 = min(len(cal) - 1, x + 20); sl = slice(i0, i1 + 1)
        cf = pd.Series(df["close"].to_numpy(float)).ffill().to_numpy()
        ma = {k: CS.moving_avg(cf, k)[sl] for k in (20, 60)}
        o = df["open"].to_numpy(float)
        marks = [{"i": e - i0, "px": float(o[e]), "kind": "entry", "label": f"買 {o[e]:.2f}"},
                 {"i": x - i0, "px": float(o[x] if r["kind"].endswith("箱底") else cf[x]), "kind": "exit", "label": f"賣（{r['kind']}）"}]
        hl = [{"px": r["top"], "label": f"箱頂 {r['top']:.2f}", "color": "#1565c0"}, {"px": r["bot"], "label": f"買時箱底 {r['bot']:.2f}", "color": "#e65100"}]
        if abs(r["bot_exit"] - r["bot"]) > 1e-9:
            hl.append({"px": r["bot_exit"], "label": f"最後箱底 {r['bot_exit']:.2f}", "color": "#c62828"})
        svg = CS.kline_svg([str(z.date()) for z in cal[sl]], df["open"].to_numpy(float)[sl], df["high"].to_numpy(float)[sl], df["low"].to_numpy(float)[sl],
                           df["close"].to_numpy(float)[sl], df["volume"].to_numpy(float)[sl] / 1000.0, ma=ma, marks=marks, title=s, show_title=False, hlines=hl)
        H.append(f"<details class='card' open><summary><b>{lab}</b>｜{s} {html.escape(str(names.get(s, '')))}｜進場 {cal[e].date()}｜報酬 {P_(r['g_DB'] - COST)}（扣成本）｜持有 {int(r['hold'])} 天</summary>{svg}</details>")
    H.append("</main></body></html>")
    open(os.path.join(OUT, F_HTML), "w", encoding="utf-8").write("\n".join(H))


if __name__ == "__main__":
    main()
