# -*- coding: utf-8 -*-
"""PREREG事件 seq2（台股策略線 登錄 sha 8eae2968c12438fc，取代 seq1；裁定 seq259 §四、seq262 §五 發號；N ＋2）——回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchEvt [--procs 2] [--seeds 200] [--reps 1000]
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchEvt_check.py

問①庫藏股：公司董事會決議買回自家股票後買進，抱 5～120 日，扣成本後有沒有比同條件股票好；組合層 10 檔對 0050。
問②臺灣50 剔除：被踢出 0050 成分的股票，生效日（或公告日）後買進會不會反彈（納入只描述）。

═══ 資料 ═══
  庫藏股：tw-stock-data main b21882c9ff data/meta/treasury_buyback.csv（sha256 0713236b794358ea…；資料庫線 0036）⇒ ~/evtdata/treasury_buyback.csv
  臺灣50：信箱附件 tw50_changes.csv（sha256 ad506ee5b82f3b6e…；資料庫線 0123；main 尚無）⇒ ~/evtdata/tw50_changes.csv
  價量：⭐ 接合版面 ＝ 早年版面 950ad26e12（2004-02-11～2014-12-31，只上市）＋ main 快照 edc6f8002f（2015-01-05～2026-09-24）
        stocks/：兩段逐列相接（早年列 ≤ 2014-12-31、main 列 ≥ 2015-01-05）；
        adj/：早年事件列的 cum_factor × main 第一個（> 2014-12-31）事件列的 cum_factor（＝ main 全部事件連乘）⇒ 全段一條還原尺度
              （data.cum_factor_series 的定義：F(d) ＝ 事件日 ＞ d 的因子連乘；main 列 ≤ 2014-12-31 者不收，避免重複）
        meta/calendar、stocks、delisted ＝ 兩段聯集 ⇒ ~/evtdata/stitch_950ad26e12_edc6f8002f/data
        ⭐ 以前各件「兩版面還原尺度未接 ⇒ 做不到」；本件事件窗跨 2014／2015，照上式接（本線讀法，看任何事件數字前寫死）
═══ 本線讀法（⭐ 看任何事件報酬前寫死）═══
 E1 事件日：庫藏股 T ＝ board_date 當日或之前最後一個交易日；進場 ＝ T＋1 開盤（＝ 決議日之後第一個交易日；保守）
          臺灣50 生效日臂 T ＝ effective_date 當日或之前最後一個交易日（進場 ＝ 生效日次一交易日開盤）；公告日臂 T ＝ announce_date 同法
 E2 類型：全部（含目的 2）／目的 1 轉讓員工／目的 3 維護信用及股東權益；目的 2 單獨只描述；⛔ 不用 *_now 九欄；鍵 (stock_id, board_date, seq)
 E3 合併：各類型內、同一檔依 T 排序，同 T 取 seq 最小；T 落在「上一個保留事件 T0」的 (T0, T0＋20] 交易日 ⇒ 併掉；先合併、再剔除
 E4 報酬 R_H ＝ c_ff[min(T＋H, 末日)] ÷ o[T＋1] − 1（還原價；c_ff ＝ 收盤 ffill ⇒ 停止交易／下市即以最後有效收盤計 ＝ 強制出場：開）；
    H ∈ {5, 10, 20, 60, 120}（協調者 09-28：5／10／20／60／120；登錄 §九 列 4 值 ⇒ 10 日一併判，另報 4 值 k 下判定有無不同）；
    ⭐ 資料尾：T＋H 超過資料末日（2026-09-24）⇒ 以末日收盤計（rerun17.t1_censor 同讀法：窗內以收盤計值），計數必報
 E5 剔除（依序、計數必報）：不在接合版面／gate3 外 → 當月不在母體 → 2015 以前該列市場非上市 → T 無有效 K 棒 →
    T＋1 不可買（無成交、開盤無效、開盤漲停）→ 硬斷點（research11.load_bars 的 next_bad：有效 K 棒 [k_T−19, k_x] 內有壞根；
    load_bars 不足 260 根 ⇒ 剔除）→ 前 20 日報酬不可算 → 同十分位無其他股
 E6 母體（當月，量測日 ＝ 該月面板量測日 ≤ T 的最後一個）：
    2012-06～2014-12：早年面板 sig_main/panel.csv.gz 的 W1 eligible；2015-08 起：panel_ext eligible（三道閘）
    2004～2012-05：早年沒有個股法人 ⇒ liq_ok ∧ bars_ok（researchMomX 早年 eligible_v 同）
    2015-02～07：panel_ext 的 bars_ok 因 main 只從 2015-01 起而全為假 ⇒ liq_ok ∧ inst_ok ∧ 接合版面有效 K 棒數 ≥ 120（P4 MIN_BARS）
    2015-01：panel_ext 尚無 amt20、法人 ⇒ 接合版面「最近 20 根有效 K 棒成交金額平均 ≥ 5,000 萬」∧ 有效 K 棒數 ≥ 120
    ⚠ 2015 以前只有上市（早年版面）⇒ 探索段 2012～2014 與早年段都只含上市；上櫃 2015 起才有
 E7 基準②：同一個 T、H，母體中所有通過 E5（不含最後一條）的股票依前 20 日報酬（avgdown.r20_cal）分十分位（avgdown.deciles，代號序）；
    ȳ ＝ 同十分位【其他】股票 R_H 平均；X ＝ R_H − ȳ；⭐ 判定量 ＝ X − 0.585%（事件那筆扣來回成本；基準不扣）
 E8 CI：基準日曆月分群 CR0（research11.cl_stats 同式）；Bonferroni α ＝ 0.05／k，k ＝ 該問該段可判定格數（n ≥ 100，K7）；
    判定：CI 下緣 ＞ 0 ⇒ 測得出（＋）；上緣 ＜ 0 ⇒ 測得出（−）；否則測不出；n ＜ 100 ⇒ 依構造不可判定、不計 N
    段：庫藏股 早年 2005～2011（判）｜探索 2012～2018（描述、組合層挑格）｜確認 2019-01～2026-08-24（判）
        臺灣50 探索 2009～2018（描述）｜確認 2019-01～2026-08-24（判）；2005～2008 缺漏照實寫、不用
    「穩」（seq253 收緊）：相鄰視窗本身也過 Bonferroni 門檻、同方向才寫；否則「方向一致，但只有 X 天過門檻」
 E9 假訊號（K4）：每格每段 1,000 次；每個真事件換成「同一曆月、同 H 的基準母體」中均勻抽一個股日（可重複）；
    p ＝ 假平均 ≥ 真平均 的比例；另報「假事件照同法也測得出」的次數；rng default_rng([20260928, 問, 類型, H, 段, r])
 E10 組合層（庫藏股）：類型 3 × H {20, 60, 120} ＝ 9 格；research11.simulate_mtm：10 槽、每槽 equity÷10、抽籤（pick=None）、
     空位現金、tradable＋delist、stop_force 開（最後有效收盤 ＜ 2026-08-24 ⇒ 次日以該收盤出場）；xpos ＝ T＋H（超過資料尾 ⇒ ncal、以末日收盤計，t1_censor 同）；
     候選 ＝ 通過 E5 前七條的事件（不要求前 20 日報酬）；一條權益 2005-01-03～2026-08-24，段內 research13.window_stats；
     200 顆種子（[20260928, 類型, H, r]），各段取年化中位、回落中位 ⇒ 使用者判準（seq141）對 0050 同段
     退化格（挑前排除）：探索段年均事件 ＜ 10（K7）或探索段持股市值恆為 0（完全退化，seq262 §二）
     挑格：探索段過判準者取比值最高；都沒過取比值最高 ⇒ 確認、早年判；件標籤 ＝ 兩段較嚴者
     臺灣50：先報年均事件數；≥ 10／年才跑，否則依構造不可判定
 E10b 組合層假訊號：挑中格每筆事件換成「同一進場日、同池（母體 ∧ 可買 ∧ 無斷點 ∧ R_H 可算）」隨機一檔，seeds 顆；p ＝ 隨機年化 ≥ 本格年化中位 的比例
 E11 新規矩 ③（seq242 ②）：挑中格若確認或早年「合格／另列」⇒ 另跑出場敏感度（描述、不判），同 seeds 顆：
     SL10／SL20 收盤 ≤ 進場價 ×0.9／×0.8 當日收盤出場（simulate_mtm stop fix）｜AT2 進場以來最高收盤 − 2×ATR14（Wilder、前一日值）⇒ 收盤 ≤ 線當日收盤出場｜
     TP30h／TP50h 收盤[t−1] ≥ 進場價 ×1.3／×1.5 ⇒ t 開盤賣半一次（trim_rule gain）｜R0-40 第 40 根有效 K 棒收盤 ≤ 進場價 ⇒ 當日收盤出場｜檔數 5／20
     ⚠ E10b、E11 的落地是在 4 顆種子除錯試跑之後補寫（試跑只為抓錯；定義照 seq242 ② 與慣例，未依結果調整）
 E12 閘：兩份事件檔 sha256；接合版面抽 20 檔 × 跨界日還原收盤比 ＝ 原始收盤比（面額與除權息不跨界）；
     挑中格種子 0 重跑一次權益逐位元相同
輸出 backtest/resultsEvt/
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from multiprocessing import Pool
from statistics import NormalDist

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import tradability as TR
from backtest import universe_gate as UG
from backtest import research11 as R11
from backtest import research13 as R13
from backtest import avgdown as AV

EARLY = os.path.expanduser("~/earlydata/950ad26e12/main/data")
MAIN = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
ST = os.path.expanduser("~/evtdata/stitch_950ad26e12_edc6f8002f/data")
TREAS = os.path.expanduser("~/evtdata/treasury_buyback.csv"); TREAS_SHA = "0713236b794358ea9fe6bee236e2acf70538e6ff93bc1aaf1928305599f9160f"
TW50 = os.path.expanduser("~/evtdata/tw50_changes.csv"); TW50_SHA = "ad506ee5b82f3b6e74dafd8a1d7d7a175487125f485d5a05eda4bc6a4842052e"
EPANEL = os.path.expanduser("~/earlydata/3edc0e2206/sig_main/panel.csv.gz")
MPANEL = "backtest/resultsp9_engine/panel_ext.csv.gz"
OUT = "backtest/resultsEvt"
HS = (5, 10, 20, 60, 120)
PH = (20, 60, 120)
COST = 0.00585
MERGE = 20
K7_N, K7_Y = 100, 10
NSLOT = 10
LIQ_MIN, MIN_BARS = 50_000_000, 120
BOUND = pd.Timestamp("2014-12-31")
SEG_T = {"早年": ("2005-01-01", "2011-12-31"), "探索": ("2012-01-01", "2018-12-31"), "確認": ("2019-01-01", "2026-08-24")}
SEG_W = {"探索": ("2009-01-01", "2018-12-31"), "確認": ("2019-01-01", "2026-08-24")}
TYPES = {"全部": None, "目的1": "1", "目的3": "3", "目的2（描述）": "2"}
_G: dict = {}


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ═════════════ 接合版面 ═════════════
def stitch(log):
    done = os.path.join(ST, "STITCH.json")
    if os.path.exists(done):
        log(f"[接合] 已有 {ST}"); return json.load(open(done, encoding="utf-8"))
    os.makedirs(os.path.join(ST, "stocks"), exist_ok=True); os.makedirs(os.path.join(ST, "adj"), exist_ok=True); os.makedirs(os.path.join(ST, "meta"), exist_ok=True)
    ec = pd.read_csv(os.path.join(EARLY, "meta", "calendar_twse.csv"))["date"]; mc = pd.read_csv(os.path.join(MAIN, "meta", "calendar_twse.csv"))["date"]
    assert ec.max() <= "2014-12-31" < mc.min(), "⛔ 兩段日曆重疊"
    pd.DataFrame({"date": list(ec) + list(mc)}).to_csv(os.path.join(ST, "meta", "calendar_twse.csv"), index=False)
    es = pd.read_csv(os.path.join(EARLY, "meta", "stocks.csv"), dtype=str); ms = pd.read_csv(os.path.join(MAIN, "meta", "stocks.csv"), dtype=str)
    fs = es.set_index("stock_id")["first_seen"].to_dict()
    ms2 = ms.copy(); ms2["first_seen"] = [min(fs.get(s, f), f) for s, f in zip(ms2["stock_id"], ms2["first_seen"])]
    roster = pd.concat([ms2, es[~es["stock_id"].isin(set(ms["stock_id"]))]], ignore_index=True)
    roster.to_csv(os.path.join(ST, "meta", "stocks.csv"), index=False)
    ed = pd.read_csv(os.path.join(EARLY, "meta", "delisted.csv"), dtype=str); md = pd.read_csv(os.path.join(MAIN, "meta", "delisted.csv"), dtype=str)
    pd.concat([md, ed[~ed["stock_id"].isin(set(md["stock_id"]))]], ignore_index=True).to_csv(os.path.join(ST, "meta", "delisted.csv"), index=False)
    keep = sorted(set(roster.loc[roster["kind"] == "stock", "stock_id"]) | {"0050"})
    cnt = {"檔": 0, "兩段都有": 0, "只早年": 0, "只main": 0, "adj 乘數≠1": 0, "main adj 2014 以前列（不收）": 0}
    for s in keep:
        pe, pm = os.path.join(EARLY, "stocks", s + ".csv"), os.path.join(MAIN, "stocks", s + ".csv")
        parts = []
        for p, lo, hi in ((pe, None, "2014-12-31"), (pm, "2015-01-05", None)):
            if os.path.exists(p):
                x = pd.read_csv(p, dtype=str, keep_default_na=False)
                if lo:
                    x = x[x["date"] >= lo]
                if hi:
                    x = x[x["date"] <= hi]
                parts.append(x)
        if not parts:
            continue
        if len(parts) == 2:
            assert list(parts[0].columns) == list(parts[1].columns), s
        pd.concat(parts, ignore_index=True).to_csv(os.path.join(ST, "stocks", s + ".csv"), index=False)
        cnt["檔"] += 1; cnt["兩段都有" if len(parts) == 2 and all(len(p_) for p_ in parts) else ("只早年" if os.path.exists(pe) and not os.path.exists(pm) else "只main")] += 1
        ae, am = os.path.join(EARLY, "adj", s + ".csv"), os.path.join(MAIN, "adj", s + ".csv")
        A = []
        mult = 1.0
        if os.path.exists(am):
            m = pd.read_csv(am, dtype=str, keep_default_na=False)
            cnt["main adj 2014 以前列（不收）"] += int((m["date"] <= "2014-12-31").sum())
            m = m[m["date"] > "2014-12-31"]
            if len(m):
                mult = float(m["cum_factor"].iloc[0])
        if os.path.exists(ae):
            e = pd.read_csv(ae, dtype=str, keep_default_na=False)
            assert (e["date"] <= "2014-12-31").all(), s
            if mult != 1.0:
                cnt["adj 乘數≠1"] += 1
            e["cum_factor"] = [repr(float(v) * mult) for v in e["cum_factor"]]
            A.append(e)
        if os.path.exists(am) and len(m):
            A.append(m)
        if A:
            pd.concat(A, ignore_index=True).to_csv(os.path.join(ST, "adj", s + ".csv"), index=False)
    info = {"早年": "950ad26e1293592457ec28194f0c5eaebfd3e53b", "main": "edc6f8002fed8803795e3486ad57db513f7e9f65", "日曆": [str(ec.iloc[0]), str(mc.iloc[-1]), int(len(ec) + len(mc))], **cnt}
    json.dump(info, open(done, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[接合] {info}")
    return info


# ═════════════ 每檔 ═════════════
def _init(cal, t0):
    D.DATA = ST
    _G.update(cal=cal, t0=t0)


def load_one(args):
    sid, mk = args
    cal = _G["cal"]; n = len(cal)
    st = D.load_stock(sid, mk, cal)
    if st is None:
        return sid, None
    df = st.df
    c = df["close"].to_numpy(float); o = df["open"].to_numpy(float); valid = np.isfinite(c)
    cff = pd.Series(c).ffill().to_numpy(float)
    raw = pd.read_csv(os.path.join(ST, "stocks", sid + ".csv"), dtype={"date": str}, usecols=["date", "market", "amount"]).drop_duplicates("date")
    raw.index = pd.to_datetime(raw["date"]); raw = raw.reindex(cal)
    twse = (raw["market"] == "twse").to_numpy()
    amt = pd.to_numeric(raw["amount"], errors="coerce").to_numpy(float)
    tb = TR.one(sid, cal)
    trd, up = np.asarray(tb["trd"], bool), np.asarray(tb["up_o"], bool)
    out = {"c": cff, "o": o, "valid": valid, "twse": twse, "trd": trd, "up_o": up, "dn_o": np.asarray(tb["dn_o"], bool), "dn_c": np.asarray(tb["dn_c"], bool),
           "nbars": np.cumsum(valid), "amt": amt}
    idx = np.flatnonzero(valid)
    out["r20"] = AV.r20_cal(c, idx)
    B = R11.load_bars(sid, mk, cal)
    R = {H: np.full(n, np.nan) for H in HS}
    if B is not None:
        assert np.array_equal(B["idx"], idx), sid
        nb = B["next_bad"]; k_of = np.full(n, -1); k_of[idx] = np.arange(len(idx))
        eok = np.zeros(n, bool)
        eok[:-1] = valid[:-1] & trd[1:] & np.isfinite(o[1:]) & (o[1:] > 0) & ~up[1:]
        Ts = np.flatnonzero(eok)
        for H in HS:
            x = np.minimum(Ts + H, n - 1)
            kx = np.searchsorted(idx, x, side="right") - 1
            kT = k_of[Ts]
            clean = nb[np.maximum(kT - 19, 0)] > kx
            t = Ts[clean]
            R[H][t] = cff[np.minimum(t + H, n - 1)] / o[t + 1] - 1.0
    out["R"] = R
    out["bars_ok260"] = B is not None
    return sid, out


# ═════════════ 母體 ═════════════
def eligibility(cal, P, sids, log):
    n = len(cal); ix = {s: i for i, s in enumerate(sids)}
    ep = pd.read_csv(EPANEL, dtype={"stock_id": str}, parse_dates=["measure_date"])
    mp = pd.read_csv(MPANEL, dtype={"stock_id": str}, parse_dates=["measure_date"])
    tf = lambda s: s.astype(str).isin(["True", "1", "1.0"])
    rules = {}
    M = []
    for md, g in ep.groupby("measure_date"):
        el = tf(g["eligible"]) if md >= pd.Timestamp("2012-06-01") else (tf(g["liq_ok"]) & tf(g["bars_ok"]))
        M.append((md, set(g.loc[el.to_numpy(), "stock_id"]), "早年 W1" if md >= pd.Timestamp("2012-06-01") else "早年 liq∧bars"))
    for md, g in mp.groupby("measure_date"):
        if md >= pd.Timestamp("2015-08-01"):
            M.append((md, set(g.loc[tf(g["eligible"]).to_numpy(), "stock_id"]), "panel_ext W1"))
            continue
        pos = int(cal.searchsorted(md))
        ok = set()
        for s in g["stock_id"]:
            p = P.get(s)
            if p is None or p["nbars"][pos] < MIN_BARS:
                continue
            ok.add(s)
        if md >= pd.Timestamp("2015-02-01"):
            el = tf(g["liq_ok"]) & tf(g["inst_ok"])
            M.append((md, set(g.loc[el.to_numpy(), "stock_id"]) & ok, "2015 liq∧inst∧接合 bars"))
        else:
            ok2 = set()
            for s in ok:
                p = P[s]; vv = np.flatnonzero(p["valid"][:pos + 1])[-20:]
                if len(vv) == 20 and np.nanmean(p["amt"][vv]) >= LIQ_MIN:
                    ok2.add(s)
            M.append((md, ok2, "2015-01 接合 amt20∧bars"))
    M.sort(key=lambda t: t[0])
    E = np.zeros((len(sids), n), bool)
    mpos = [int(cal.searchsorted(md)) for md, _, _ in M]
    for j, (md, S_, rule) in enumerate(M):
        a = mpos[j]; b = mpos[j + 1] if j + 1 < len(M) else n
        for s in S_:
            if s in ix:
                E[ix[s], a:b] = True
        rules[str(md.date())] = [rule, len(S_)]
    log(f"[母體] 量測日 {len(M)}（{M[0][0].date()}～{M[-1][0].date()}）；各段規則見 summary")
    return E, rules


# ═════════════ 事件 ═════════════
def treasury_events(cal):
    t = pd.read_csv(TREAS, dtype={"stock_id": str, "seq": int, "purpose": str})
    t = t[["market", "seq", "stock_id", "name", "board_date", "purpose"]].copy()
    t["bd"] = pd.to_datetime(t["board_date"])
    t["T"] = cal.searchsorted(t["bd"], side="right") - 1
    t = t[(t["T"] >= 0) & (t["T"] < len(cal) - 1)]
    return t


def merge(ev):
    """E3：同一檔依 (T, seq)；T 落在上一個保留事件的 (T0, T0＋20] ⇒ 併掉；同 T 只留第一件。"""
    ev = ev.sort_values(["stock_id", "T", "seq"]).reset_index(drop=True)
    keep = []; last = {}
    for i, (s, T) in enumerate(zip(ev["stock_id"], ev["T"])):
        T0 = last.get(s)
        if T0 is not None and T0 <= T <= T0 + MERGE:
            continue
        keep.append(i); last[s] = T
    return ev.loc[keep].reset_index(drop=True)


def tw50_events(cal):
    t = pd.read_csv(TW50, dtype={"stock_id": str}, encoding="utf-8-sig")
    t = t[t["action"].isin(["delete", "add"])].copy()
    rows = []
    for arm, col in (("生效日後進場", "effective_date"), ("公告日後進場", "announce_date")):
        x = t.copy(); x["arm"] = arm; x["T"] = cal.searchsorted(pd.to_datetime(x[col]), side="right") - 1
        rows.append(x)
    return pd.concat(rows, ignore_index=True)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); ap.add_argument("--seeds", type=int, default=200)
    ap.add_argument("--reps", type=int, default=1000); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    log(f"===== researchEvt {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜PREREG事件 seq2 sha 8eae2968c12438fc =====")
    S = {"登錄": "PREREG事件 seq2 sha 8eae2968c12438fc（取代 seq1）", "閘": {}}
    S["閘"]["事件檔 sha256"] = {"庫藏股": sha256(TREAS) == TREAS_SHA, "臺灣50": sha256(TW50) == TW50_SHA}
    assert all(S["閘"]["事件檔 sha256"].values()), S["閘"]
    S["接合"] = stitch(log)
    D.DATA = ST
    cal = D.load_calendar(); n = len(cal)
    roster = pd.read_csv(os.path.join(ST, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(roster)
    mk = dict(zip(roster["stock_id"], roster["market"]))
    sids = sorted(set(U["stock_id"]) & {f[:-4] for f in os.listdir(os.path.join(ST, "stocks"))})
    with Pool(a.procs, initializer=_init, initargs=(cal, 0)) as pool:
        P = {s: v for s, v in pool.map(load_one, [(s, mk.get(s, "twse")) for s in sids + ["0050"]], chunksize=16) if v is not None}
    bench = P.pop("0050")["c"]
    sids = [s for s in sids if s in P]
    log(f"[資料] 接合日曆 {cal[0].date()}～{cal[-1].date()}（{n}）｜gate3 有檔 {len(sids):,}｜load_bars ≥260 根 {sum(P[s]['bars_ok260'] for s in sids):,}")
    # 閘：跨界還原比 ＝ 原始比
    bi = int(cal.searchsorted(pd.Timestamp("2015-01-05"))); rng0 = np.random.default_rng(20260928)
    both = [s for s in sids if P[s]["valid"][bi - 1] and P[s]["valid"][bi]]
    chk = []
    for s in sorted(rng0.choice(both, size=min(20, len(both)), replace=False)):
        r = pd.read_csv(os.path.join(ST, "stocks", s + ".csv"), dtype={"date": str}, usecols=["date", "close"]).set_index("date")["close"]
        raw_ratio = float(r["2015-01-05"]) / float(r["2014-12-31"])
        chk.append(abs(P[s]["c"][bi] / P[s]["c"][bi - 1] - raw_ratio))
    S["閘"]["跨界還原比＝原始比（抽 20 檔）"] = {"最大差": float(max(chk)), "過": float(max(chk)) < 1e-9}
    log(f"[閘] 跨界 {S['閘']['跨界還原比＝原始比（抽 20 檔）']}")
    E, rules = eligibility(cal, P, sids, log); S["母體規則（量測日: 規則, 檔數）"] = rules
    ix = {s: i for i, s in enumerate(sids)}
    pre15 = np.arange(n) < bi
    TW = np.array([P[s]["twse"] for s in sids]); POOLOK = E & (TW | ~pre15[None, :])
    R20 = np.array([P[s]["r20"] for s in sids])
    # ── 基準②：逐 T、H
    t_lo = int(cal.searchsorted(pd.Timestamp("2005-01-01"))) - 0
    MON = {H: {} for H in HS}          # 曆月 → X list（假訊號池）
    RB = {H: np.array([P[s]["R"][H] for s in sids]) for H in HS}
    for s in sids:
        del P[s]["R"]
    XB = {H: np.full((len(sids), n), np.nan) for H in HS}
    last_T = int(cal.searchsorted(pd.Timestamp("2026-08-24"), side="right") - 1)
    for H in HS:
        Rm = RB[H]
        for T in range(int(cal.searchsorted(pd.Timestamp("2004-06-01"))), last_T + 1):
            ok = POOLOK[:, T] & np.isfinite(R20[:, T]) & np.isfinite(Rm[:, T])
            if ok.sum() < 20:
                continue
            r = np.where(ok, R20[:, T], np.nan)
            dcl = AV.deciles(r)
            ii = np.flatnonzero(ok); y = Rm[ii, T]; dd = dcl[ii]
            sm = np.bincount(dd, weights=y, minlength=10); ct = np.bincount(dd, minlength=10)
            cnt_o = ct[dd] - 1
            X = np.where(cnt_o > 0, y - (sm[dd] - y) / np.maximum(cnt_o, 1), np.nan)
            XB[H][ii, T] = X
            MON[H].setdefault(str(cal[T])[:7], []).extend(X[np.isfinite(X)].tolist())
        log(f"[基準②] H{H} 完成（股日 {int(np.isfinite(XB[H]).sum()):,}）")
    MON = {H: {k: np.array(v) for k, v in d.items()} for H, d in MON.items()}

    def status(ev, H, need_bench=True):
        """E5 依序；回 (保留列 DataFrame 含 R、X、ybar；各原因計數)。"""
        why = {"不在版面或 gate3": 0, "當月不在母體": 0, "2015 前非上市": 0, "T 無有效K棒": 0, "T+1 不可買": 0, "硬斷點或不足260根": 0,
               "前20日報酬不可算": 0, "同十分位無他股": 0}
        keep = []
        for r in ev.itertuples():
            i = ix.get(r.stock_id); T = int(r.T)
            if i is None:
                why["不在版面或 gate3"] += 1; continue
            if not E[i, T]:
                why["當月不在母體"] += 1; continue
            if T < bi and not TW[i, T]:
                why["2015 前非上市"] += 1; continue
            p = P[r.stock_id]
            if not p["valid"][T]:
                why["T 無有效K棒"] += 1; continue
            if not (p["trd"][T + 1] and np.isfinite(p["o"][T + 1]) and p["o"][T + 1] > 0 and not p["up_o"][T + 1]):
                why["T+1 不可買"] += 1; continue
            if not np.isfinite(RB[H][i, T]):
                why["硬斷點或不足260根"] += 1; continue
            x = np.nan
            if need_bench:
                if not np.isfinite(R20[i, T]):
                    why["前20日報酬不可算"] += 1; continue
                x = XB[H][i, T]
                if not np.isfinite(x):
                    why["同十分位無他股"] += 1; continue
            keep.append((r.Index, float(RB[H][i, T]), x, bool(T + H > n - 1)))
        k = pd.DataFrame(keep, columns=["_i", "R", "X", "尾截"]).set_index("_i")
        return ev.loc[k.index].join(k), why

    def cstats(x, T, k):
        x = np.asarray(x, float); mon = np.array([str(cal[t])[:7] for t in T])
        cs = R11.cl_stats(x, mon)
        if cs["n"] == 0:
            return {"n": 0}
        z = NormalDist().inv_cdf(1 - 0.05 / (2 * max(k, 1)))
        return {"n": cs["n"], "平均": cs["mean"], "中位": cs["median"], "勝率": cs["win"], "曆月數": cs["months"], "se": cs["se"],
                "lo95": cs["lo"], "hi95": cs["hi"], "z": z, "lo": cs["mean"] - z * cs["se"], "hi": cs["mean"] + z * cs["se"]}

    def seg_of(T, segs):
        d = cal[T]
        for nm, (x, y) in segs.items():
            if pd.Timestamp(x) <= d <= pd.Timestamp(y):
                return nm
        return None

    def fake(xs_months, H, key, reps):
        """同曆月、同 H 基準母體均勻抽。回 假平均陣列、假也測得出次數（用同一 z）。"""
        rng = np.random.default_rng(key)
        um, cnt = np.unique(np.asarray(xs_months), return_counts=True)       # 曆月排序
        if any(len(MON[H].get(m, ())) == 0 for m in um):
            return None
        V = np.empty((reps, int(cnt.sum())))
        st_ = np.r_[0, np.cumsum(cnt)[:-1]]
        for m, c_, b_ in zip(um, cnt, st_):
            pool_ = MON[H][m]
            V[:, b_:b_ + c_] = pool_[rng.integers(len(pool_), size=(reps, c_))]
        V -= COST
        mu = V.mean(axis=1)
        ms_ = np.add.reduceat(V - mu[:, None], st_, axis=1)
        return mu, np.sqrt((ms_ ** 2).sum(axis=1)) / V.shape[1]

    # ═════ 問①庫藏股 單筆 ═════
    TE = treasury_events(cal)
    S["庫藏股原始"] = {"件": int(len(TE)), "上市": int((TE["market"] == "sii").sum()), "上櫃": int((TE["market"] == "otc").sum()),
                    "目的": TE["purpose"].value_counts().to_dict(), "決議日": [str(TE["bd"].min().date()), str(TE["bd"].max().date())]}
    EV = {}
    for tn, pv in TYPES.items():
        e = TE if pv is None else TE[TE["purpose"] == pv]
        EV[tn] = merge(e)
    S["庫藏股合併後"] = {tn: int(len(v)) for tn, v in EV.items()}
    rows = []; KEEP = {}; WHY = {}
    for tn in TYPES:
        for H in HS:
            k_, w_ = status(EV[tn], H); KEEP[(tn, H)] = k_; WHY[f"{tn}_H{H}"] = w_
            k_["段"] = [seg_of(int(t), SEG_T) for t in k_["T"]]
    S["庫藏股剔除計數"] = WHY
    # 可判定格數
    kk = {}
    for sg in SEG_T:
        kk[sg] = sum(1 for tn in TYPES if "描述" not in tn for H in HS if int((KEEP[(tn, H)]["段"] == sg).sum()) >= K7_N)
        kk[sg + "（4 視窗）"] = sum(1 for tn in TYPES if "描述" not in tn for H in HS if H != 10 and int((KEEP[(tn, H)]["段"] == sg).sum()) >= K7_N)
    S["庫藏股可判定格數 k"] = kk
    FKROWS = []
    for tn in TYPES:
        for H in HS:
            k_ = KEEP[(tn, H)]
            for sg in SEG_T:
                g = k_[k_["段"] == sg]
                if not len(g):
                    rows.append({"問": "庫藏股", "類型": tn, "H": H, "段": sg, "n": 0}); continue
                st_ = cstats(g["X"].to_numpy() - COST, g["T"].to_numpy(), kk[sg])
                st4 = cstats(g["X"].to_numpy() - COST, g["T"].to_numpy(), kk[sg + "（4 視窗）"])
                judge = (sg != "探索") and ("描述" not in tn)
                if st_["n"] < K7_N:
                    v = "依構造不可判定（n＜100）"
                elif not judge:
                    v = "描述"
                else:
                    v = "測得出（＋）" if st_["lo"] > 0 else ("測得出（−）" if st_["hi"] < 0 else "測不出")
                v4 = None
                if judge and st_["n"] >= K7_N and H != 10:
                    v4 = "測得出（＋）" if st4["lo"] > 0 else ("測得出（−）" if st4["hi"] < 0 else "測不出")
                fk = fake([str(cal[int(t)])[:7] for t in g["T"]], H, [20260928, 1, list(TYPES).index(tn), H, list(SEG_T).index(sg)], a.reps)
                fp = fpass = None
                if fk is not None:
                    fm, fse = fk; fp = float(np.mean(fm >= st_["平均"])); fpass = int(np.sum(fm - st_["z"] * fse > 0))
                    FKROWS.append(pd.DataFrame({"問": "庫藏股", "類型": tn, "H": H, "段": sg, "r": np.arange(a.reps), "假平均": fm, "假se": fse}))
                rows.append({"問": "庫藏股", "類型": tn, "H": H, "段": sg, "判定": v, "判定（4 視窗 k）": v4, "R平均": float(g["R"].mean()), "X平均（未扣成本）": float(g["X"].mean()),
                             "尾截筆": int(g["尾截"].sum()), "上櫃筆": int((g["market"] == "otc").sum()), **st_, "假訊號 p": fp, "假也測得出次數": fpass})
    # ═════ 問②臺灣50 單筆 ═════
    TWE = tw50_events(cal)
    S["臺灣50原始"] = {"刪除": int((TWE["action"] == "delete").sum() // 2), "納入": int((TWE["action"] == "add").sum() // 2),
                    "生效日": [str(TWE["effective_date"].min()), str(TWE["effective_date"].max())]}
    WHY2 = {}
    k2 = {}
    tmp = {}
    for act in ("delete", "add"):
        for arm in ("生效日後進場", "公告日後進場"):
            for H in HS:
                ev = TWE[(TWE["action"] == act) & (TWE["arm"] == arm)].copy(); ev["seq"] = 0
                k_, w_ = status(ev, H); k_["段"] = [seg_of(int(t), SEG_W) for t in k_["T"]]
                tmp[(act, arm, H)] = k_; WHY2[f"{act}_{arm}_H{H}"] = w_
    for sg in SEG_W:
        k2[sg] = sum(1 for arm in ("生效日後進場", "公告日後進場") for H in HS if int((tmp[("delete", arm, H)]["段"] == sg).sum()) >= K7_N)
    S["臺灣50剔除計數"] = WHY2; S["臺灣50可判定格數 k"] = k2
    for (act, arm, H), k_ in tmp.items():
        for sg in SEG_W:
            g = k_[k_["段"] == sg]
            if not len(g):
                rows.append({"問": "臺灣50", "類型": f"{'剔除' if act == 'delete' else '納入（描述）'}｜{arm}", "H": H, "段": sg, "n": 0}); continue
            st_ = cstats(g["X"].to_numpy() - COST, g["T"].to_numpy(), k2[sg])
            if st_["n"] < K7_N:
                v = "依構造不可判定（n＜100）"
            elif act == "add" or sg == "探索":
                v = "描述"
            else:
                v = "測得出（＋）" if st_["lo"] > 0 else ("測得出（−）" if st_["hi"] < 0 else "測不出")
            fk = fake([str(cal[int(t)])[:7] for t in g["T"]], H, [20260928, 2, int(act == "add"), int(arm[0] == "公"), H, list(SEG_W).index(sg)], a.reps)
            fp = fpass = None
            if fk is not None:
                fm, fse = fk; fp = float(np.mean(fm >= st_["平均"])); fpass = int(np.sum(fm - st_["z"] * fse > 0))
            rows.append({"問": "臺灣50", "類型": f"{'剔除' if act == 'delete' else '納入（描述）'}｜{arm}", "H": H, "段": sg, "判定": v,
                         "R平均": float(g["R"].mean()), "X平均（未扣成本）": float(g["X"].mean()), "尾截筆": int(g["尾截"].sum()), "上櫃筆": int((g["market"] == "tpex").sum()) if "market" in g else 0,
                         **st_, "假訊號 p": fp, "假也測得出次數": fpass})
    SG = pd.DataFrame(rows)
    # 穩
    stab = []
    for r in SG.itertuples():
        if not isinstance(r.判定, str) or not r.判定.startswith("測得出"):
            stab.append(None); continue
        hi_ = HS.index(r.H); nb_ = [HS[j] for j in (hi_ - 1, hi_ + 1) if 0 <= j < len(HS)]
        sib = SG[(SG["問"] == r.問) & (SG["類型"] == r.類型) & (SG["段"] == r.段) & SG["H"].isin(nb_)]
        passH = sorted(SG[(SG["問"] == r.問) & (SG["類型"] == r.類型) & (SG["段"] == r.段) & (SG["判定"] == r.判定)]["H"].tolist())
        if len(sib) and (sib["判定"] == r.判定).all():
            stab.append("穩")
        elif len(sib) and (np.sign(sib["平均"]) == np.sign(r.平均)).all():
            stab.append(f"方向一致，但只有 {'、'.join(map(str, passH))} 日過門檻")
        else:
            stab.append(f"相鄰視窗方向不一致；只有 {'、'.join(map(str, passH))} 日過門檻")
    SG["穩"] = stab
    SG.to_csv(os.path.join(OUT, "single.csv"), index=False, float_format="%.17g")
    pd.concat([k_.assign(類型=tn, H=H) for (tn, H), k_ in KEEP.items()]).drop(columns=["bd"]).to_csv(os.path.join(OUT, "events_treasury.csv.gz"), index=False, float_format="%.17g")
    pd.concat([k_.assign(act=act, arm_=arm, H=H) for (act, arm, H), k_ in tmp.items()]).to_csv(os.path.join(OUT, "events_tw50.csv.gz"), index=False, float_format="%.17g")
    if FKROWS:
        pd.concat(FKROWS).to_csv(os.path.join(OUT, "fake_single.csv.gz"), index=False, float_format="%.17g")
    log("[單筆] 完成")
    for r in SG[SG["判定"].astype(str).str.startswith("測得出")].itertuples():
        log(f"  {r.問} {r.類型} H{r.H} {r.段}：{r.判定}｜{r.平均:+.3%}〔{r.lo:+.3%}, {r.hi:+.3%}〕n {r.n}｜{r.穩}")
    # ═════ 組合層 ═════
    yrs = {sg: (pd.Timestamp(y) - pd.Timestamp(x)).days / 365.25 for sg, (x, y) in SEG_T.items()}
    tw_year = {sg: float(((TWE["action"] == "delete") & (TWE["arm"] == "生效日後進場") & (pd.to_datetime(TWE["effective_date"]).between(*SEG_W[sg]))).sum()) /
               ((pd.Timestamp(SEG_W[sg][1]) - pd.Timestamp(SEG_W[sg][0])).days / 365.25) for sg in SEG_W}
    S["臺灣50 組合層"] = {"年均剔除事件": tw_year, "判定": "依構造不可判定（年均 ＜ 10）" if max(tw_year.values()) < K7_Y else "要跑"}
    w0 = int(cal.searchsorted(pd.Timestamp("2005-01-03"))); w1 = last_T
    SEGP = {sg: (int(cal.searchsorted(pd.Timestamp(x))), int(cal.searchsorted(pd.Timestamp(y), side="right") - 1)) for sg, (x, y) in SEG_T.items()}
    Z = {sg: R13.window_stats(bench, 0, n, x, y + 1) for sg, (x, y) in SEGP.items()}
    S["0050"] = {sg: {"年化": float(c_), "回落": float(m_), "比值": float(c_) / abs(float(m_))} for sg, (c_, m_) in Z.items()}
    closes = {s: P[s]["c"] for s in sids}; opens = {s: P[s]["o"] for s in sids}
    trad = {s: {"trd": P[s]["trd"], "up_o": P[s]["up_o"], "dn_o": P[s]["dn_o"], "dn_c": P[s]["dn_c"]} for s in sids}
    dl = TR.delist_status({s: trad[s] for s in sids}, cal, official=TR.load_official())
    SF = R11.stop_force_days({s: P[s]["valid"] for s in sids}, w1)
    SIG = {}
    for tn in ("全部", "目的1", "目的3"):
        for H in PH:
            k_, _ = status(EV[tn], H, need_bench=False)
            k_ = k_[(k_["T"] + 1 >= w0) & (k_["T"] + 1 <= w1)]
            T_ = k_["T"].to_numpy(int)
            xp = np.where(T_ + H <= n - 1, T_ + H, n)
            SIG[(tn, H)] = pd.DataFrame({"sid": k_["stock_id"].to_numpy(), "entry_pos": T_ + 1, f"xpos_H{H}": xp, f"g_H{H}": k_["R"].to_numpy(float)})
    _G.update(SIG=SIG, closes=closes, opens=opens, trad=trad, dl=dl, SF=SF, n=n, SEGP=SEGP)
    jobs = [(tn, H, r) for tn in ("全部", "目的1", "目的3") for H in PH for r in range(a.seeds)]
    with Pool(a.procs) as pool:
        PR = pool.map(_port, jobs, chunksize=4)
    PT = pd.DataFrame(PR); PT.to_csv(os.path.join(OUT, "port_seeds.csv.gz"), index=False, float_format="%.17g")
    rows = []
    for (tn, H), g in PT.groupby(["類型", "H"], sort=False):
        ev_ = SIG[(tn, H)]
        for sg in SEG_T:
            c_ = float(g[f"{sg}_年化"].median()); m_ = float(g[f"{sg}_回落"].median()); c0, m0 = Z[sg]
            lab = "合格" if (c_ > c0 and c_ / abs(m_) >= c0 / abs(m0)) else ("另列" if c_ > c0 else "不合格")
            ne = int(((ev_["entry_pos"] >= SEGP[sg][0]) & (ev_["entry_pos"] <= SEGP[sg][1])).sum())
            rows.append({"類型": tn, "H": H, "段": sg, "年化中位": c_, "回落中位": m_, "比值": c_ / abs(m_), "標籤": lab, "種子合格比例": float(np.mean((g[f"{sg}_年化"] > c0) & (g[f"{sg}_年化"] / g[f"{sg}_回落"].abs() >= c0 / abs(m0)))),
                         "事件": ne, "年均事件": ne / yrs[sg], "平均投入比例": float(g[f"{sg}_投入"].median()), "恆為0": bool((g[f"{sg}_投入"] == 0).all())})
    PC = pd.DataFrame(rows); PC.to_csv(os.path.join(OUT, "port_cells.csv"), index=False, float_format="%.17g")
    ex = PC[PC["段"] == "探索"].copy()
    ex["退化"] = (ex["年均事件"] < K7_Y) | ex["恆為0"]
    ok_ = ex[~ex["退化"]]
    c0, m0 = Z["探索"]
    ps = ok_[(ok_["年化中位"] > c0) & (ok_["比值"] >= c0 / abs(m0))]
    best = (ps if len(ps) else ok_).sort_values(["比值", "年化中位"], ascending=[False, False]).iloc[0]
    pk = (best["類型"], int(best["H"]))
    lab = {sg: PC[(PC["類型"] == pk[0]) & (PC["H"] == pk[1]) & (PC["段"] == sg)].iloc[0] for sg in ("確認", "早年")}
    order = {"合格": 2, "另列": 1, "不合格": 0}
    for sg in ("確認", "早年"):
        if lab[sg]["年均事件"] < K7_Y:
            lab[sg] = lab[sg].copy(); lab[sg]["標籤"] = "依構造不可判定（年均 ＜ 10）"
    lj = [lab[sg]["標籤"] for sg in ("確認", "早年") if lab[sg]["標籤"] in order]
    S["組合層挑格"] = {"格": f"{pk[0]}_H{pk[1]}", "探索過判準格數": int(len(ps)), "退化排除": ex.loc[ex["退化"], ["類型", "H"]].astype(str).agg("_H".join, axis=1).tolist(),
                    "探索": {k: float(best[k]) for k in ("年化中位", "回落中位", "比值")},
                    "確認": {k: (lab["確認"][k] if k == "標籤" else float(lab["確認"][k])) for k in ("年化中位", "回落中位", "比值", "種子合格比例", "年均事件", "標籤")},
                    "早年": {k: (lab["早年"][k] if k == "標籤" else float(lab["早年"][k])) for k in ("年化中位", "回落中位", "比值", "種子合格比例", "年均事件", "標籤")},
                    "件標籤（兩段較嚴）": (min(lj, key=lambda x: order[x]) if lj else "依構造不可判定")}
    log(f"[組合層] 挑 {S['組合層挑格']['格']}｜探索 {best['年化中位']:+.2%}／{best['回落中位']:+.2%}｜確認 {lab['確認']['年化中位']:+.2%}／{lab['確認']['回落中位']:+.2%} {lab['確認']['標籤']}｜早年 {lab['早年']['年化中位']:+.2%}／{lab['早年']['回落中位']:+.2%} {lab['早年']['標籤']}")
    # 閘：挑中格種子 0 重跑
    e1 = _port((pk[0], pk[1], 0), eq_only=True); e2 = _port((pk[0], pk[1], 0), eq_only=True)
    S["閘"]["挑中格種子0重跑權益逐位元相同"] = hashlib.sha256(e1.tobytes()).hexdigest() == hashlib.sha256(e2.tobytes()).hexdigest()
    np.save(os.path.join(OUT, "eq_pick_seed0.npy"), e1)
    # 假訊號（組合層，挑中格）：每筆事件換成同一進場日、同池（母體 ∧ 可買 ∧ 無斷點 ∧ R_H 可算）隨機一檔；同 seeds 顆
    tn, H = pk
    base = SIG[(tn, H)]
    Tb = base["entry_pos"].to_numpy(int) - 1
    fpool = {int(T): np.flatnonzero(POOLOK[:, T] & np.isfinite(RB[H][:, T])) for T in np.unique(Tb)}
    FS = []
    for r in range(a.seeds):
        rng = np.random.default_rng([20260928, 9, H, r])
        ii = np.array([fpool[int(T)][rng.integers(len(fpool[int(T)]))] if len(fpool[int(T)]) else -1 for T in Tb])
        m = ii >= 0; Tm = Tb[m]
        FS.append(pd.DataFrame({"sid": [sids[i] for i in ii[m]], "entry_pos": Tm + 1, f"xpos_H{H}": np.where(Tm + H <= n - 1, Tm + H, n), f"g_H{H}": RB[H][ii[m], Tm]}))
    _G["FS"] = FS
    with Pool(a.procs) as pool:
        FR = pd.DataFrame(pool.map(_port_fake, [(tn, H, r) for r in range(a.seeds)], chunksize=4))
    FR.to_csv(os.path.join(OUT, "port_fake.csv.gz"), index=False, float_format="%.17g")
    real = PT[(PT["類型"] == tn) & (PT["H"] == H)]
    S["組合層假訊號（挑中格；同進場日同池隨機換股）"] = {sg: {"p（隨機年化 ≥ 本格年化中位）": float(np.mean(FR[f"{sg}_年化"] >= real[f"{sg}_年化"].median())),
                                                  "隨機年化中位": float(FR[f"{sg}_年化"].median()), "隨機回落中位": float(FR[f"{sg}_回落"].median())} for sg in SEG_T}
    log(f"[組合層假訊號] {S['組合層假訊號（挑中格；同進場日同池隨機換股）']}")
    S["新規矩③"] = "要跑" if any(lab[sg]["標籤"] in ("合格", "另列") for sg in ("確認", "早年")) else "不適用（挑中格確認、早年皆非合格／另列）"
    if S["新規矩③"] == "要跑":
        SIGV, cntv = exit_variants(base, H, cal, log)
        VAR = {"SL10": {"stop": ("fix", 0.10)}, "SL20": {"stop": ("fix", 0.20)}, "AT2": {}, "TP30h": {"trim_rule": {"kind": "gain", "x": 0.30, "frac": 0.5}},
               "TP50h": {"trim_rule": {"kind": "gain", "x": 0.50, "frac": 0.5}}, "R0-40": {}, "N5": {"nslot": 5}, "N20": {"nslot": 20}}
        _G.update(SIGV=SIGV, VAR=VAR)
        with Pool(a.procs) as pool:
            SR = pd.DataFrame(pool.map(_port_sens, [(v, tn, H, r) for v in VAR for r in range(a.seeds)], chunksize=4))
        SR.to_csv(os.path.join(OUT, "sens_seeds.csv.gz"), index=False, float_format="%.17g")
        sens = {"原格": {sg: [float(real[f"{sg}_年化"].median()), float(real[f"{sg}_回落"].median())] for sg in SEG_T}}
        for v, g in SR.groupby("變體", sort=False):
            sens[v] = {sg: [float(g[f"{sg}_年化"].median()), float(g[f"{sg}_回落"].median())] for sg in SEG_T}
        S["新規矩③ 出場敏感度（描述、不判；各段 [年化中位, 回落中位]）"] = {"定義": "SL10／SL20 ＝ 收盤 ≤ 進場價 ×0.9／×0.8 當日收盤出場（simulate_mtm stop fix）；AT2 ＝ 進場以來最高收盤 − 2×ATR14（Wilder、前一日值）⇒ 收盤 ≤ 線當日收盤出場；"
                                                                   "TP30h／TP50h ＝ 收盤[t−1] ≥ 進場價 ×1.3／×1.5 ⇒ t 開盤賣半（一次；trim_rule gain）；R0-40 ＝ 第 40 根有效 K 棒收盤 ≤ 進場價 ⇒ 當日收盤出場；N5／N20 ＝ 檔數",
                                                                   "提前出場筆數": cntv, **sens}
        log(f"[新規矩③] {sens}")
    S["窗"] = {"庫藏股": SEG_T, "臺灣50": SEG_W, "組合層權益": [str(cal[w0].date()), str(cal[w1].date())]}
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[閘] {S['閘']}｜新規矩③ {S['新規矩③']}")
    log(f"[完] {time.time() - T0:.0f}s")


PTYPES = ("全部", "目的1", "目的3")


def _run(sig, H, seed, nslot=NSLOT, **kw):
    out = R11.simulate_mtm(sig, f"H{H}", nslot, np.random.default_rng(seed), _G["closes"], _G["opens"], _G["n"],
                           return_equity=True, pick=None, d_max=None, queue_days=0, cash_mode="zero", tradable=_G["trad"], delist=_G["dl"], stop_force=_G["SF"], **kw)
    return np.asarray(out["equity"], float), np.asarray(out["hold_val"], float)


def _stats(eq, hv, row):
    for sg, (x, y) in _G["SEGP"].items():
        c_, m_ = R13.window_stats(eq, 0, len(eq), x, y + 1)
        row[f"{sg}_年化"] = float(c_); row[f"{sg}_回落"] = float(m_)
        row[f"{sg}_投入"] = float(np.mean(hv[x:y + 1] / eq[x:y + 1]))
    return row


def _port(job, eq_only=False):
    tn, H, r = job
    eq, hv = _run(_G["SIG"][(tn, H)], H, [20260928, PTYPES.index(tn), H, r])
    return eq if eq_only else _stats(eq, hv, {"類型": tn, "H": H, "r": r})


def _port_fake(job):
    tn, H, r = job
    eq, hv = _run(_G["FS"][r], H, [20260928, 9, H, r])
    return _stats(eq, hv, {"r": r})


def _port_sens(job):
    name, tn, H, r = job
    v = dict(_G["VAR"][name]); sig = _G["SIGV"].get(name, _G["SIG"][(tn, H)])
    ns = v.pop("nslot", NSLOT)
    eq, hv = _run(sig, H, [20260928, PTYPES.index(tn), H, r], nslot=ns, **v)
    return _stats(eq, hv, {"變體": name, "r": r})


def exit_variants(base, H, cal, log):
    """AT2（進場以來最高收盤 − 2×ATR14，前一日值；收盤 ≤ 線 ⇒ 當日收盤出場）、R0-40（第 40 根有效 K 棒收盤 ≤ 進場價 ⇒ 當日收盤出場）⇒ 改 xpos、g。"""
    n = len(cal); cache = {}
    A2 = base.copy(); R4 = base.copy(); cA = cR = 0
    xs, gs = f"xpos_H{H}", f"g_H{H}"
    for i, (s, e, x) in enumerate(zip(base["sid"], base["entry_pos"], base[xs])):
        if s not in cache:
            st = D.load_stock(s, "twse", cal); df = st.df
            c = df["close"].to_numpy(float); idx = np.flatnonzero(np.isfinite(c))
            h = df["high"].to_numpy(float)[idx]; l_ = df["low"].to_numpy(float)[idx]; cc = c[idx]
            tr = np.r_[h[0] - l_[0], np.maximum.reduce([h[1:] - l_[1:], np.abs(h[1:] - cc[:-1]), np.abs(l_[1:] - cc[:-1])])]
            atr = np.full(len(idx), np.nan)
            if len(idx) >= 14:
                atr[13] = tr[:14].mean()
                for k in range(14, len(idx)):
                    atr[k] = (atr[k - 1] * 13 + tr[k]) / 14
            cache[s] = (idx, cc, atr, df["open"].to_numpy(float))
        idx, cc, atr, o = cache[s]
        ke = int(np.searchsorted(idx, e)); kx = int(np.searchsorted(idx, min(x, n - 1), side="right") - 1)
        if ke >= len(idx) or idx[ke] != e:
            continue
        oe = o[e]; mx = cc[ke]
        for k in range(ke + 1, kx + 1):
            if np.isfinite(atr[k - 1]) and cc[k] <= mx - 2 * atr[k - 1]:
                A2.iat[i, A2.columns.get_loc(xs)] = int(idx[k]); A2.iat[i, A2.columns.get_loc(gs)] = cc[k] / oe - 1.0; cA += 1
                break
            mx = max(mx, cc[k])
        k40 = ke + 39
        if k40 <= kx and k40 < len(idx) and idx[k40] < min(x, n):
            if cc[k40] <= oe:
                R4.iat[i, R4.columns.get_loc(xs)] = int(idx[k40]); R4.iat[i, R4.columns.get_loc(gs)] = cc[k40] / oe - 1.0; cR += 1
    log(f"[出場敏感度] AT2 提前出場 {cA} 筆、R0-40 {cR} 筆（共 {len(base)}）")
    return {"AT2": A2, "R0-40": R4}, {"AT2 提前": cA, "R0-40 提前": cR}


if __name__ == "__main__":
    main()
