# -*- coding: utf-8 -*-
"""逐日可交易旗標 —— 給 research11.simulate_mtm 的新參數 `tradable`（⇐ 裁定線 20260924-1714 §一）。

每檔回三條與日曆等長的布林序列：
   trd    當天有成交（未還原收盤非缺、> 0）
   up_o   當天【開盤 ＝ 漲停價】（⇒ 買不到）
   dn_o   當天【開盤 ＝ 跌停價】（⇒ 賣不掉）
   dn_c   當天【收盤 ＝ 跌停價】（⇒ 排程出場日收盤賣不掉；⇐ 裁定線 20260924-1744 裁 (乙)）
漲跌停價：⭐ 與 research11.limit_flags 同一套（research11.limit_price：tick 級距、2015-06-01 前 7%／後 10%），
   參考價 ＝ 前一個【有成交日】的未還原收盤；⛔ 差別只在拿【開盤】去比，而不是收盤（1714 §一④）
不判（旗標一律 False）：還原事件日（除權息日的參考價不是前收）、上市前 5 根（與 load_bars 同一條）
未還原價：與 research11.load_bars 同一條路 ⇒ 直接讀 data/stocks/{sid}.csv，⛔ 不從還原價反推
"""
from __future__ import annotations
import os
import numpy as np, pandas as pd
from backtest import data as D
from backtest import research11 as R

CUT = pd.Timestamp("2015-06-01")


def one(sid: str, cal: pd.DatetimeIndex) -> dict:
    n = len(cal)
    p = os.path.join(D.DATA, "stocks", f"{sid}.csv")
    none = {"trd": np.zeros(n, bool), "up_o": np.zeros(n, bool), "dn_o": np.zeros(n, bool), "dn_c": np.zeros(n, bool)}
    if not os.path.exists(p):
        return none
    raw = pd.read_csv(p, dtype={"date": str}, usecols=["date", "open", "close"])
    raw["date"] = pd.to_datetime(raw["date"]); raw = raw.drop_duplicates("date").set_index("date")
    ro = np.array(pd.to_numeric(raw["open"].reindex(cal), errors="coerce"), dtype=float)
    rc = np.array(pd.to_numeric(raw["close"].reindex(cal), errors="coerce"), dtype=float)
    ro[~(ro > 0)] = np.nan; rc[~(rc > 0)] = np.nan              # ⭐ 零價視為缺（與 load_stock 同）
    trd = np.isfinite(rc)
    idx = np.flatnonzero(trd)
    up = np.zeros(n, bool); dn = np.zeros(n, bool); dc = np.zeros(n, bool)
    if len(idx) < 2:
        return {"trd": trd, "up_o": up, "dn_o": dn, "dn_c": dc}
    skip = set()
    adj = D.load_adj(sid)
    if adj is not None and len(adj):
        dates = cal[idx]
        for d in adj["date"]:
            k = int(np.searchsorted(dates, pd.Timestamp(d)))
            if k < len(idx):
                skip.add(int(idx[k]))
    if cal[idx[0]] > pd.Timestamp("2015-01-12"):
        skip.update(int(x) for x in idx[:5])
    for a, b in zip(idx[:-1], idx[1:]):                         # b 的參考價 ＝ 前一個有成交日 a 的收盤
        if b in skip or not np.isfinite(ro[b]):
            continue
        lim = 0.07 if cal[b] < CUT else 0.10
        up[b] = abs(ro[b] - R.limit_price(rc[a], True, lim)) < 1e-6
        dn[b] = abs(ro[b] - R.limit_price(rc[a], False, lim)) < 1e-6
    for a, b in zip(idx[:-1], idx[1:]):                         # dn_c：同一個參考價，拿【收盤】比（⛔ 不受開盤缺值影響）
        if b in skip:
            continue
        lim = 0.07 if cal[b] < CUT else 0.10
        dc[b] = abs(rc[b] - R.limit_price(rc[a], False, lim)) < 1e-6
    return {"trd": trd, "up_o": up, "dn_o": dn, "dn_c": dc}


def build(sids, cal: pd.DatetimeIndex) -> dict:
    return {s: one(s, cal) for s in sids}


# ══ 裁定線 20260924-2319 seq98 §二：下市與停牌分開 ═══════════════════════════
DELIST_GAP = 60   # ⭐ 設計參數（在看任何新結果之前訂）；理由：本線 2013 量到的真停牌 gap 最長 49 天


def load_official(path=None) -> dict:
    """官方下市日（data/meta/delisted.csv：delist_date, stock_id, …）⇒ dict sid → Timestamp。"""
    import os as _os
    import pandas as _pd
    from . import data as _D
    p = path or _os.path.join(_D.DATA, "meta", "delisted.csv")
    d = _pd.read_csv(p, dtype={"stock_id": str})
    assert {"delist_date", "stock_id"} <= set(d.columns), "⛔ delisted.csv 欄位不對：{}".format(list(d.columns))
    return dict(zip(d["stock_id"], _pd.to_datetime(d["delist_date"])))


def delist_status(trad: dict, cal, official: dict | None = None, gap: int = DELIST_GAP) -> dict:
    """每檔：最後成交位置 last 與狀態（給 simulate_mtm 的 delist 參數）。
       ① 有官方下市日 ⇒ delisted_official
       ② 否則 最後成交之後全域日曆還有 ≥ gap 個交易日都沒成交 ⇒ delisted_gap
       ③ 最後成交就是日曆最後一根 ⇒ live
       ④ 其餘（< gap）⇒ ambig（⛔ 不猜；引擎照停牌處理並逐筆報數）
       ⭐「再也沒有成交」看的是【該檔自己】的最後成交，而 gap 量在【全域日曆】上（邊界要問是誰的）"""
    ncal = len(cal); out = {}
    official = official or {}
    for sid, f in trad.items():
        tt = np.flatnonzero(np.asarray(f["trd"], bool))
        if len(tt) == 0:
            continue
        last = int(tt[-1]); g = (ncal - 1) - last
        if sid in official:
            st = "delisted_official"
        elif g >= gap:
            st = "delisted_gap"
        elif g == 0:
            st = "live"
        else:
            st = "ambig"
        out[sid] = {"last": last, "status": st, "gap": g}
    return out
