# -*- coding: utf-8 -*-
"""USREG-A2（M／U／X／W1b 在 S&P 500＋400 新母體重跑）的資料轉接層：把 us_data（只認 S&P 500）擴成「兩個指數的聯集」。

⭐ 依據：美股登錄 USREG-A2 seq1（sha 8be74b36592db3f4，台北 2026-10-07 06:19）；裁定線 seq316（判定口徑：只 S&P 400 與合併都過才合格）；
        資料庫線 0245（S&P 400 名冊與七項限制）、1005-1321（體檢：整段缺價 S&P 500 18／S&P 400 48、代號重用已擋）。
⛔ 本檔只做讀檔：不算任何策略報酬。⛔ 不改 backtest/us_data.py（既有 M／U／X／W1b 的 --check 與結果不動）：
   install() 只在【本行程】把 us_data 模組的幾個函式換成聯集版（monkeypatch），既有程式另開行程時照舊讀 0043f97／60d2f99。
⛔⛔ 授權：us-stock-data 是私有 repo ⇒ 本檔只讀；逐日價格、財報原值一律不寫進 tw-p17。

資料：~/usdata/881c86a（git archive 881c86a9a756，唯讀；.commit 記完整 sha）＝ 開跑當下 us-stock-data main（含 3130a2e5、60d2f999、881c86a9）。
窗：2016-01-04 ～ 2026-09-30（登錄 A2 §一）。

讀法（登錄沒寫清楚 ⇒ 執行者先寫死，台北 2026-10-07）：
 D1 實體 ＝ 代號（兩個指數的聯集；⛔ 不分「500 的 AMD」「400 的 AMD」兩檔）：同一家公司 400↔500 升降級時是同一條價格、合併窗連續。
    資料庫 0245：同一天同時在兩個指數 0 天（本檔 fixture A2D1 全期再驗一次）。
 D2 每個指數各自的成分旗標 m500[d]／m400[d] ＝ 該指數 panel 那天有列 ⇒ 取該列 in_index；那天沒列 ⇒ 取該指數 universe.csv 的 spans（a ≤ d < b）
    （＝ us_data.in_index 同一規則，逐指數套）。母體 member ＝ m500 ∨ m400。
 D3 聯集 panel 的「那天用哪一列」：
    ① 那天在某指數成分內（m＝1）且該指數 panel 有列 ⇒ 用該列；
    ② 那天在某指數成分內、但該指數 panel 沒有列（資料庫刻意寧缺的段：代號重用 COR／WTW／DOC、COHR／CZR 前段、整段缺價…）
       ⇒ 那天【沒有列】（⛔ 不拿另一個指數同代號的列補，避免接到別家公司）；
    ③ 那天不在任何成分內（暖身、移出後）⇒ 兩邊有列且 src 相同 ⇒ 用它；只有一邊 ⇒ 用那一邊；兩邊都有但 src 不同 ⇒ 那天沒有列（計數；881c86a 只有 CHK 13 天）。
    ⇒ 價格一律照該列 src 讀 prices_yahoo／prices（兩個指數共用價格檔，資料庫 0245 ⑥），還原 OHLC 與硬斷點（seam／split_div）照 us_data.load_ohlc。
 D4 期初已在／期中加入（M B3、U W7）：T 所在的【聯集】指數區間起點（400→500 同日相接的區間併成一段）≤ 窗首 ⇒ 期初已在。
 D5 事件歸屬（三欄）：只 S&P 400 ＝ T（事件日／觸及日／S 日）當天 m400＝1；只 S&P 500 ＝ m500＝1；合併 ＝ 全部（D1 ⇒ 兩者互斥）。
 D6 |ret|＞50% 清單（裁定 seq316）：panel_sp400/_report.md〈在指數期間單日 |ret| > 50%〉23 列 ＝ 資料庫尚未逐筆確認 ⇒ 全部標「未確認」；
    主結果照用；敏感度 ＝「該列當硬斷點」（跨到那天的事件／訊號剔除，基準不收跨到那天的股票）。S&P 500 的同名清單是先前各件已照用的舊清單 ⇒ 只列數、不進敏感度。
 D7 整段缺價（存活者偏差）：每個指數「在指數股-日」中，聯集 panel 那天沒有列的比例逐指數報；資料庫 1005：整段缺 S&P 500 18、S&P 400 48 檔 ⇒ 結果偏向存活股、偏樂觀。
"""
from __future__ import annotations

import functools
import io
import os
import re

import numpy as np
import pandas as pd

from backtest import us_data as U

DATA_COMMIT = "881c86a"
DATA_COMMIT_FULL = "881c86a9a756d34cd41c9a2a0f8cfe8d8e3e311c"
ROOT = os.environ.get("US_DATA_ROOT_A2", os.path.expanduser("~/usdata/%s" % DATA_COMMIT))
WINDOW = (pd.Timestamp("2016-01-04"), pd.Timestamp("2026-09-30"))
IDX = ("sp500", "sp400")
DIRS = {"sp500": ("panel", "membership"), "sp400": ("panel_sp400", "membership_sp400")}
STATS = {"D3③_兩邊src不同而無列_天": 0, "D3②_成分內但該指數無列_天": 0}


def _p(*a):
    return os.path.join(ROOT, "data", *a)


def data_commit():
    return io.open(os.path.join(ROOT, ".commit"), encoding="utf-8").read().strip()


# ── 名冊 ──────────────────────────────────────────────────
@functools.lru_cache(maxsize=None)
def utab(idx):
    return pd.read_csv(_p(DIRS[idx][1], "universe.csv"), dtype=str, keep_default_na=False).set_index("ticker")


@functools.lru_cache(maxsize=None)
def tickers_all():
    return sorted(set(utab("sp500").index) | set(utab("sp400").index))


def spans_idx(t, idx):
    tb = utab(idx)
    if t not in tb.index:
        return []
    out = []
    for sp in tb.loc[t, "spans"].split(";"):
        a, b = sp.split("~")
        out.append((pd.Timestamp(a), pd.Timestamp(b) if b else None))
    return out


def union_spans(t, asof=None):
    """兩個指數的區間合併（相接 b＝a′ 併成一段）；asof 給定 ⇒ 右端晚於 asof 的當作還沒移出（同 us_data._spans）。"""
    sp = sorted(spans_idx(t, "sp500") + spans_idx(t, "sp400"), key=lambda x: x[0])
    out = []
    for a, b in sp:
        if out and (out[-1][1] is None or a <= out[-1][1]):
            pa, pb = out[-1]
            out[-1] = (pa, None if (pb is None or b is None) else max(pb, b))
        else:
            out.append((a, b))
    if asof is not None:
        asof = pd.Timestamp(asof)
        out = [(a, (None if (b is not None and b > asof) else b)) for a, b in out if a <= asof]
    return out


@functools.lru_cache(maxsize=None)
def segments_idx(idx):
    return pd.read_csv(_p(DIRS[idx][0], "_segments.csv"), dtype=str, keep_default_na=False)


@functools.lru_cache(maxsize=None)
def covered_tickers():
    out = set()
    for idx in IDX:
        s = segments_idx(idx)
        out |= set(s.loc[s["kind"] == "covered", "ticker"])
    return frozenset(out)


def no_ohlc_tickers():
    return sorted(set(tickers_all()) - covered_tickers())


# ── panel 聯集 ────────────────────────────────────────────
def _read_panel(idx, t):
    p = _p(DIRS[idx][0], t + ".csv")
    if not os.path.exists(p):
        return None
    d = pd.read_csv(p, dtype={"date": str, "src": str})
    d["date"] = pd.to_datetime(d["date"])
    d["star"] = d["src"].str.endswith("*")
    d["src"] = d["src"].str.rstrip("*")
    return d.set_index("date")


def _span_mask(idx_dates, spans):
    m = np.zeros(len(idx_dates), bool)
    v = idx_dates.values
    for a, b in spans:
        m |= (v >= np.datetime64(a)) & ((v < np.datetime64(b)) if b is not None else True)
    return m


@functools.lru_cache(maxsize=4096)
def panel_union(t):
    """→ DataFrame（index＝date）：ret, in_index（聯集成分，D2）, src, star, m500, m400, from（取自哪個指數的列）。D3 規則。"""
    P = {idx: _read_panel(idx, t) for idx in IDX}
    dates = sorted(set().union(*[set(x.index) for x in P.values() if x is not None]))
    cols = ["ret", "in_index", "src", "star", "m500", "m400", "from"]
    if not dates:
        return pd.DataFrame({c: [] for c in cols}, index=pd.DatetimeIndex([], name="date"))
    di = pd.DatetimeIndex(dates, name="date")
    M, H, X = {}, {}, {}
    for idx in IDX:
        sp = _span_mask(di, spans_idx(t, idx))
        x = P[idx]
        if x is not None:
            has = di.isin(x.index)
            xr = x.reindex(di)
            M[idx] = np.where(has, xr["in_index"].to_numpy() == 1, sp)
            H[idx] = has; X[idx] = xr
        else:
            M[idx] = sp; H[idx] = np.zeros(len(di), bool)
            X[idx] = pd.DataFrame({"ret": np.nan, "in_index": np.nan, "src": None, "star": False}, index=di)
    m5, m4, h5, h4 = M["sp500"], M["sp400"], H["sp500"], H["sp400"]
    same = (X["sp500"]["src"].to_numpy(object) == X["sp400"]["src"].to_numpy(object))
    mem = m5 | m4
    use5 = (m5 & h5) | (~mem & h5 & (~h4 | same))
    use4 = ~use5 & ((m4 & h4) | (~mem & ~h5 & h4))
    STATS["D3②_成分內但該指數無列_天"] += int((mem & ~use5 & ~use4).sum())
    STATS["D3③_兩邊src不同而無列_天"] += int((~mem & h5 & h4 & ~same).sum())
    keep = use5 | use4
    out = {}
    for c in ("ret", "src", "star"):
        a5 = X["sp500"][c].to_numpy(object); a4 = X["sp400"][c].to_numpy(object)
        out[c] = np.where(use5, a5, a4)[keep]
    df = pd.DataFrame({"ret": pd.to_numeric(pd.Series(out["ret"]), errors="coerce").to_numpy(float),
                       "in_index": mem[keep].astype(int), "src": out["src"].astype(str), "star": out["star"].astype(bool),
                       "m500": m5[keep], "m400": m4[keep], "from": np.where(use5, "sp500", "sp400")[keep]},
                      index=pd.DatetimeIndex(di[keep], name="date"))
    return df


def idx_member(t, cal):
    """→ (m500, m400)：對齊 cal 的逐指數成分旗標（D2）；cal 上 panel 沒列的日子取 spans。"""
    out = []
    for idx in IDX:
        x = _read_panel(idx, t)
        sp = _span_mask(cal, spans_idx(t, idx))
        if x is not None:
            has = cal.isin(x.index)
            rowm = np.zeros(len(cal), bool)
            rowm[has] = x.reindex(cal[has])["in_index"].to_numpy() == 1
            out.append(np.where(has, rowm, sp))
        else:
            out.append(sp)
    return out[0], out[1]


# ── us_data 換成聯集版 ───────────────────────────────────
def _u_spans(ticker, asof=None):
    return union_spans(ticker, asof)


def _u_universe_table():
    return pd.DataFrame({"ticker": tickers_all()})


@functools.lru_cache(maxsize=1)
def report_split_div_days():
    out = set()
    for idx in IDX:
        on = False
        for line in io.open(_p(DIRS[idx][0], "_report.md"), encoding="utf-8"):
            if line.startswith("## "):
                on = "同一天拆股" in line
                continue
            m = re.match(r"^- (\S+) (\d{4}-\d{2}-\d{2})：", line)
            if on and m:
                out.add((m.group(1), pd.Timestamp(m.group(2))))
    return frozenset(out)


@functools.lru_cache(maxsize=None)
def ret50_list(idx):
    """→ [(ticker, date, ret%, src)]：該指數 _report.md〈在指數期間單日 |ret| > 50%〉。"""
    out, on = [], False
    for line in io.open(_p(DIRS[idx][0], "_report.md"), encoding="utf-8"):
        if line.startswith("## "):
            on = "|ret| > 50%" in line
            continue
        m = re.match(r"^- (\S+) (\d{4}-\d{2}-\d{2}) ([+-][\d.]+)% （(\S+)）", line)
        if on and m:
            out.append((m.group(1), pd.Timestamp(m.group(2)), float(m.group(3)), m.group(4)))
    return out


def flag50_pos(t, cal):
    """D6：S&P 400 未確認 |ret|＞50% 列在 cal 上的位置（bool 陣列）。"""
    f = np.zeros(len(cal), bool)
    for tk, d, _, _ in ret50_list("sp400"):
        if tk == t and d in cal:
            f[cal.get_loc(d)] = True
    return f


def _u_no_assert():
    c = data_commit()
    if not c.startswith(DATA_COMMIT):
        raise RuntimeError("資料 commit %s ≠ A2 寫死的 %s" % (c, DATA_COMMIT))
    return c


_INSTALLED = [False]


def install():
    """把 backtest.us_data 換成聯集版（只在本行程）。⛔ 不寫回檔案。"""
    if _INSTALLED[0]:
        return
    U.ROOT = ROOT
    U.DATA_COMMIT = DATA_COMMIT
    U.WINDOW = WINDOW
    for f in (U.load_calendar, U.segments, U.universe_table, U.panel, U.report_split_div_days, U._read_src, U._membership,
              U.quarterly_revenue):
        try:
            f.cache_clear()
        except AttributeError:
            pass
    U.panel = panel_union
    U._spans = _u_spans
    U.universe_table = _u_universe_table
    U.no_ohlc_tickers = no_ohlc_tickers
    U.report_split_div_days = report_split_div_days
    U.data_commit = data_commit
    U.assert_pinned = _u_no_assert

    def _nope(*a, **k):
        raise RuntimeError("A2：此函式未改成聯集版，⛔ 不可用")
    U.universe = _nope
    U._membership = _nope
    U.segments = _nope
    U.quarterly_revenue = _nope
    U.revenue_asof = _nope
    U.revenue_not_applicable = _nope
    _INSTALLED[0] = True


# ── 存活者偏差、覆蓋（D7）────────────────────────────────
def coverage(cal, w0, w1):
    """→ 逐指數：窗內在指數股-日、其中聯集 panel 沒列的股-日與比例、整段缺價檔數。"""
    out = {}
    calw = cal[w0:w1 + 1]
    tot = {idx: 0 for idx in IDX}; miss = {idx: 0 for idx in IDX}; nohole = {idx: set() for idx in IDX}
    for t in tickers_all():
        m5, m4 = idx_member(t, calw)
        pu = panel_union(t)
        has = calw.isin(pu.index)
        for idx, m in (("sp500", m5), ("sp400", m4)):
            k = int(m.sum())
            if k == 0:
                continue
            tot[idx] += k; miss[idx] += int((m & ~has).sum())
            if not (m & has).any():
                nohole[idx].add(t)
    for idx in IDX:
        out[idx] = {"窗內在指數股日": tot[idx], "其中沒有價格列": miss[idx], "缺價股日比例": round(miss[idx] / max(1, tot[idx]), 5),
                    "窗內整段沒有價格的檔數": len(nohole[idx]), "窗內整段沒有價格名單": sorted(nohole[idx])}
    return out


def selftest():
    """A2D1 兩個指數同日都在 0 天（全期、名冊 spans）｜A2D2 聯集規則：寧缺段不借另一指數的列（COR／WTW／DOC）、CHK 兩邊 src 不同那 13 天無列｜
    A2D3 升降級股（AMD 2017-03-20 400→500）聯集區間相接成一段、成分連續｜A2D4 |ret|>50% 清單解析 23 列（S&P 400）。"""
    msg = []
    allp = []
    for t in tickers_all():
        for a, b in spans_idx(t, "sp500"):
            for c, d in spans_idx(t, "sp400"):
                lo = max(a, c); hi = min(b or pd.Timestamp("2100-01-01"), d or pd.Timestamp("2100-01-01"))
                if lo < hi:
                    allp.append((t, lo, hi))
    assert not allp, allp[:5]
    msg.append("A2D1 名冊 spans：同一代號同日在兩個指數 0 個重疊區間（%d 檔）" % len(tickers_all()))
    for t in ("COR", "WTW", "DOC"):
        pu = panel_union(t)
        m4only = pu["m400"] & ~pu["m500"]
        assert not m4only.any(), (t, int(m4only.sum()))
    pu = panel_union("CHK")
    gap = [d for d in pd.bdate_range("2021-02-10", "2021-03-01") if d in set(_read_panel("sp500", "CHK").index) & set(_read_panel("sp400", "CHK").index)]
    assert gap and not any(d in pu.index for d in gap), len(gap)
    msg.append("A2D2 寧缺段不借列：COR／WTW／DOC 在 S&P 400 成分內的日子聯集無列；CHK 兩邊 src 不同的 %d 天無列" % len(gap))
    sp = union_spans("AMD")
    assert len(sp) == 1 and sp[0][0] == pd.Timestamp("2016-01-01") and sp[0][1] is None, sp
    pu = panel_union("AMD")
    w = pu[(pu.index >= "2017-03-14") & (pu.index <= "2017-03-24")]
    assert w["in_index"].eq(1).all() and w.loc[w.index < "2017-03-20", "m400"].all() and w.loc[w.index >= "2017-03-20", "m500"].all(), w
    msg.append("A2D3 AMD 2017-03-20 400→500：聯集區間一段、成分逐日連續、歸屬日切換")
    r4 = ret50_list("sp400")
    assert len(r4) == 23, len(r4)
    msg.append("A2D4 S&P 400 |ret|>50%% 清單 23 列（全部未確認）；S&P 500 舊清單 %d 列（只列數）" % len(ret50_list("sp500")))
    for s in msg:
        print("✅", s, flush=True)
    return msg
