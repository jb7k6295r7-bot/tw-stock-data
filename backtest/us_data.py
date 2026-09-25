# -*- coding: utf-8 -*-
"""美股資料轉接層（USREG-M／USREG-X／USREG-U／USREG-W1b 共用）。

⭐ 依據：美股登錄 seq2（正文）＋seq3＋seq4；裁定線 seq163、seq168、seq176；
        資料庫線 1550（面板）、1639（日曆／基準／成交規則）、1753（OHLC 切段）、2016（季營收）。
⛔ 本檔只做「把私有 repo us-stock-data 的資料讀成回測可用的形狀」：不算任何策略、不算任何策略報酬。
⛔ 不改台股共用引擎（research11.py、data.py、tradability.py…）；美股轉接另開（裁定）。
⛔⛔ 授權：us-stock-data 是私有 repo（Yahoo 等來源授權）⇒ 本檔只【讀】；
        ⛔ 永遠不可把它的價格／報酬寫進 tw-stock-data 或本線分支（resultsUS/ 只放計數、sha、查核結果）。

資料根目錄：環境變數 US_DATA_ROOT；預設 ~/usdata/<DATA_COMMIT>（git archive 出來的唯讀快照，
            裡面 .commit 記完整 sha）。⛔ 不直接讀 ~/us-stock-data 的工作目錄（它每天被 live.yml 更新）。

讀法總表（每個函式的 docstring 有細節）：
  load_calendar()        NYSE 交易日 ＝ data/macro/yahoo_GSPC.csv 的日期
  load_ohlc(t)           照 _segments.csv 的 covered 列取檔、只取該列 range、還原 OHLC；帶硬斷點
  hard_breaks(t)         資料層硬斷點：來源接縫（IR 2020-03-02）＋同日拆股配息（面板 src 帶 *、_report.md 那一節）
  long_gaps(t)           連續 ≥ 5 個交易日沒有 K 棒的空缺（登錄 seq2 §二④ 的參數；由策略決定當不當硬斷點）
  in_index(t)            逐交易日：member（在不在 S&P 500）、has_price（面板那天有沒有列）
  universe(d)            d 當天的成分股（預設只含面板有列的＝登錄的事件母體；include_unpriced=True 對名冊）
  benchmark_tr()         ^SP500TR 總報酬指數（SPY 還原價備援）；⛔ 不用 ^GSPC
  quarterly_revenue()    讀 value（第一次公布）、可用日 ＝ first_filed 的下一個交易日；⛔ 不讀 latest_value
  revenue_asof(d)        可用日 ≤ d 的季營收列
  no_ohlc_tickers()      整段沒有 OHLC 的 35 檔
  revenue_not_applicable()  季營收不適用的檔與原因
"""
import functools
import hashlib
import io
import os
import re
import subprocess

import numpy as np
import pandas as pd

# ── 版本與常數 ──────────────────────────────────────────────
DATA_COMMIT = "0043f97"                      # 登錄 seq4 §三 寫死
DATA_COMMIT_FULL = "0043f97d974df78ffe5626623aed2caecfd4a5b8"
ROOT = os.environ.get("US_DATA_ROOT", os.path.expanduser("~/usdata/%s" % DATA_COMMIT))
WINDOW = (pd.Timestamp("2016-01-04"), pd.Timestamp("2026-08-31"))   # 登錄 seq2 §一
EVENT_FWD = 21                               # 事件須 T+21 ≤ 窗尾（登錄 seq2 §一）

COST_ROUNDTRIP = 0.0005                      # 0.05% 來回（登錄 seq2 §一、seq3 §一②）
COST_PER_SIDE = COST_ROUNDTRIP / 2
COST_SENSITIVITY = (0.0002, 0.0010)          # 敏感度（來回）
PRICE_LIMIT = None                           # 美股沒有每日漲跌停（資料庫 1639 §四）⇒ ⛔ 不套台股漲跌停閘
HALT_RULE = "面板那天沒有列 ＝ 沒有 K 棒；⛔ 不補 0、⛔ 不補前值"   # 資料庫 1550 §二 1、1639 §三
GAP_BREAK_DAYS = 5                           # 連續 ≥ 5 交易日無有效 K 棒（登錄 seq2 §二④，取自台股 PREREGM ⑥）

# 資料庫線 1753 §一 逐字的 35 檔（selftest 拿來對 no_ohlc_tickers()）
NO_OHLC_35_LETTER = ("ADT ANSS APC BBBY CA CAM CBS CCE CCEP CSRA DNB DO EMC ENDP ESV FL FRC FTR HBI HFC "
                     "INFO MNK MON NFX PARA PCL POM SBNY SE SIVB SPLS STI TE VIAC WRK").split()
FAILED_BANKS = ("SIVB", "FRC", "SBNY")


def _p(*a):
    return os.path.join(ROOT, "data", *a)


def data_commit():
    """→ 完整 commit sha。快照目錄讀 .commit；若 ROOT 是 git 工作目錄則 rev-parse HEAD。"""
    f = os.path.join(ROOT, ".commit")
    if os.path.exists(f):
        return io.open(f, encoding="utf-8").read().strip()
    return subprocess.check_output(["git", "-C", ROOT, "rev-parse", "HEAD"], text=True).strip()


def assert_pinned():
    """開跑前呼叫：資料 commit 必須是登錄寫死的那一個。"""
    c = data_commit()
    if not c.startswith(DATA_COMMIT):
        raise RuntimeError("資料 commit %s ≠ 登錄寫死的 %s" % (c, DATA_COMMIT))
    return c


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def fingerprint():
    """→ {相對路徑: sha256}：本層會讀的檔；大目錄（panel、prices、prices_yahoo）給一個合併 sha
    （依檔名排序、逐行 "檔名 sha256\\n" 串接後再 sha256）。"""
    out = {}
    for rel in ("panel/_segments.csv", "panel/_month_end_roster.csv", "panel/_report.md",
                "membership/universe.csv", "macro/yahoo_GSPC.csv", "macro/yahoo_SP500TR.csv",
                "macro/yahoo_SPY.csv", "fundamentals/quarterly_revenue.csv",
                "fundamentals/quarterly_revenue_status.csv"):
        out[rel] = _sha256(_p(*rel.split("/")))
    for d in ("panel", "prices", "prices_yahoo"):
        names = sorted(n for n in os.listdir(_p(d)) if n.endswith(".csv") and not n.startswith("_"))
        h = hashlib.sha256()
        for n in names:
            h.update(("%s %s\n" % (n, _sha256(_p(d, n)))).encode())
        out["%s/*.csv（%d 檔）" % (d, len(names))] = h.hexdigest()
    return out


# ── 日曆 ──────────────────────────────────────────────────
@functools.lru_cache(maxsize=None)
def load_calendar():
    """→ pd.DatetimeIndex：紐約證交所開盤日 ＝ data/macro/yahoo_GSPC.csv 的 date 欄（資料庫 1639 §三）。
    ⚠ 0043f97：^GSPC（與 ^SP500TR）缺 2026-09-22（週二、正常開盤日；SPY 與 66 檔個股有那天）⇒ 在登錄窗
      （～2026-08-31）之外、不影響本件；窗內日曆與每年休市日數已查過（selftest A6、US_ADAPTER.md）。"""
    d = pd.read_csv(_p("macro", "yahoo_GSPC.csv"), usecols=["date"], dtype=str)
    return pd.DatetimeIndex(pd.to_datetime(d["date"]), name="date").sort_values()


def next_trading_day(d):
    """→ d 之後（嚴格晚於 d）的第一個交易日；超出日曆 ⇒ NaT。"""
    cal = load_calendar()
    i = cal.searchsorted(pd.Timestamp(d), side="right")
    return cal[i] if i < len(cal) else pd.NaT


# ── 面板、切段 ────────────────────────────────────────────
@functools.lru_cache(maxsize=None)
def segments():
    """→ _segments.csv（ticker,spans,kind,src,range,note）＋ r0／r1（range 起訖，Timestamp；gap 整段缺者為 NaT）。"""
    s = pd.read_csv(_p("panel", "_segments.csv"), dtype=str, keep_default_na=False)
    rr = s["range"].str.split("~", expand=True)
    s["r0"] = pd.to_datetime(rr[0].where(rr[0] != "", None))
    s["r1"] = pd.to_datetime(rr[1].where(rr[1] != "", None))
    return s


@functools.lru_cache(maxsize=None)
def universe_table():
    """→ membership/universe.csv（747 檔的在指數區間 spans；區間右端【不含】＝ build_panel.py 的 d < b）。"""
    return pd.read_csv(_p("membership", "universe.csv"), dtype=str, keep_default_na=False)


def _spans(ticker, asof=None):
    """→ [(a, b)]；asof 給定時把 b > asof 的右端改成 None（＝到 asof 為止還沒移出；selftest E1 用）。"""
    row = universe_table().set_index("ticker").loc[ticker]
    out = []
    for sp in row["spans"].split(";"):
        a, b = sp.split("~")
        a = pd.Timestamp(a)
        b = pd.Timestamp(b) if b else None
        if asof is not None:
            if a > asof:
                continue
            if b is not None and b > asof:
                b = None
        out.append((a, b))
    return out


def panel_path(ticker):
    return _p("panel", ticker + ".csv")


@functools.lru_cache(maxsize=1024)
def panel(ticker):
    """→ 面板 DataFrame（index＝date）：ret（空白 ⇒ NaN，⛔ 不補）、in_index（int）、src（去掉 *）、star（src 帶 *）。
    沒有面板檔（整段缺的 35 檔）⇒ 空 DataFrame。"""
    p = panel_path(ticker)
    if not os.path.exists(p):
        return pd.DataFrame({"ret": [], "in_index": [], "src": [], "star": []},
                            index=pd.DatetimeIndex([], name="date"))
    d = pd.read_csv(p, dtype={"date": str, "src": str})
    d["date"] = pd.to_datetime(d["date"])
    d["star"] = d["src"].str.endswith("*")
    d["src"] = d["src"].str.rstrip("*")
    return d.set_index("date")


@functools.lru_cache(maxsize=1)
def report_split_div_days():
    """→ frozenset{(ticker, Timestamp)}：_report.md〈同一天拆股＋配息〉那一節列的日子。"""
    out, on = set(), False
    for line in io.open(_p("panel", "_report.md"), encoding="utf-8"):
        if line.startswith("## "):
            on = "同一天拆股" in line
            continue
        m = re.match(r"^- (\S+) (\d{4}-\d{2}-\d{2})：", line)
        if on and m:
            out.add((m.group(1), pd.Timestamp(m.group(2))))
    return frozenset(out)


# ── 還原 OHLC ────────────────────────────────────────────
@functools.lru_cache(maxsize=256)
def _read_src(src):
    """src＝'yahoo:TT'／'tiingo:TWTR' ⇒ 還原 OHLC（index＝date）。
    Yahoo：還原 X ＝ 原始 X × adjclose ÷ close（登錄 seq2 §一）；Tiingo：直接用 adjOpen／adjHigh／adjLow／adjClose。
    無效列（任一欄空、或 ≤ 0）⇒ 丟掉（＝那天沒有 K 棒，⛔ 不補）；0043f97 實測 0 列。"""
    kind, f = src.split(":", 1)
    if kind == "yahoo":
        d = pd.read_csv(_p("prices_yahoo", f + ".csv"), dtype={"date": str})
        k = d["adjclose"] / d["close"]
        o = pd.DataFrame({"open": d["open"] * k, "high": d["high"] * k,
                          "low": d["low"] * k, "close": d["close"] * k})
        raw = d[["open", "high", "low", "close", "adjclose"]]
    elif kind == "tiingo":
        d = pd.read_csv(_p("prices", f + ".csv"), dtype={"date": str})
        o = pd.DataFrame({"open": d["adjOpen"], "high": d["adjHigh"],
                          "low": d["adjLow"], "close": d["adjClose"]})
        raw = o
    else:
        raise ValueError(src)
    o.index = pd.DatetimeIndex(pd.to_datetime(d["date"]), name="date")
    ok = raw.notna().all(axis=1).values & (raw > 0).all(axis=1).values
    return o[ok].astype(float)


def split_div_days(ticker):
    """→ 該檔同一天拆股＋配息的日子（面板 src 帶 * ∪ _report.md〈同一天拆股＋配息〉）。"""
    pn = panel(ticker)
    a = set(pn.index[pn["star"].astype(bool)]) if len(pn) else set()
    b = {d for t, d in report_split_div_days() if t == ticker}
    return sorted(a | b)


def load_ohlc(ticker, scope="covered"):
    """→ 還原 OHLC DataFrame（index＝date）：open,high,low,close,src,hard_break,break_reason,piece。

    scope="covered"（預設＝登錄 seq2 §一逐字）：只取 _segments.csv 裡 kind＝covered 的列，
        每列 src 前綴 yahoo: ⇒ data/prices_yahoo/<後綴>.csv、tiingo: ⇒ data/prices/<後綴>.csv，只取該列 range 內的日期。
        ⚠ covered 的 range ＝ 該來源在指數期間的第一天～最後一天 ⇒ 不含入指數前的暖身日。
    scope="panel"：照面板每一列的 src 取同一個檔（含 in_index＝0 的暖身日，面板從入指數前約 400 天起）。
        ⚠ 登錄沒寫要不要用暖身日 ⇒ 這個選項只供策略線／裁定線決定後使用；預設不用。
    hard_break＝True ⇒ 這一根與前一根【不可相連】（⛔ 不跨它畫線、認型態、算跨日報酬）：
        seam       來源接縫（同一代號換檔，例 IR 2020-03-02：yahoo:TT → yahoo:IR）
        split_div  同一天拆股＋配息（面板 src 帶 * 或 _report.md 那一節；DHR 2016-07-05、XRX 2017-01-03）
    piece＝硬斷點切出來的段號（0 起）。
    ⚠ 登錄 seq2 §二④ 的「連續 ≥ 5 交易日無 K 棒」空缺不在這裡標（見 long_gaps()），由策略程式決定怎麼切。
    沒有 covered 段（35 檔）⇒ 空 DataFrame。"""
    cols = ["open", "high", "low", "close", "src", "hard_break", "break_reason", "piece"]
    parts = []
    if scope == "covered":
        s = segments()
        s = s[(s["ticker"] == ticker) & (s["kind"] == "covered")].sort_values("r0")
        for _, r in s.iterrows():
            o = _read_src(r["src"])
            o = o.loc[(o.index >= r["r0"]) & (o.index <= r["r1"])].copy()
            o["src"] = r["src"]
            parts.append(o)
    elif scope == "panel":
        pn = panel(ticker)
        for src, g in pn.groupby("src", sort=False):
            o = _read_src(src)
            o = o.loc[o.index.isin(g.index)].copy()
            o["src"] = src
            parts.append(o)
    else:
        raise ValueError(scope)
    if not parts:
        return pd.DataFrame({c: [] for c in cols}, index=pd.DatetimeIndex([], name="date"))
    o = pd.concat(parts).sort_index()
    if o.index.duplicated().any():
        raise RuntimeError("%s：兩個來源段日期重疊 %s" % (ticker, o.index[o.index.duplicated()][:3].tolist()))
    reason = np.array([""] * len(o), dtype=object)
    srcs = o["src"].values
    seam = np.r_[False, srcs[1:] != srcs[:-1]]
    reason[seam] = "seam"
    hit = o.index.isin(split_div_days(ticker))
    reason[hit] = np.where(reason[hit] == "", "split_div", "seam+split_div")
    o["break_reason"] = reason
    o["hard_break"] = reason != ""
    o["piece"] = np.cumsum(o["hard_break"].values).astype(int)
    return o[cols]


def hard_breaks(ticker, scope="covered"):
    """→ DataFrame(date, reason)：資料層硬斷點（seam／split_div）。"""
    o = load_ohlc(ticker, scope)
    h = o[o["hard_break"].astype(bool)]
    return pd.DataFrame({"date": h.index, "reason": h["break_reason"].values})


def long_gaps(ticker, min_days=GAP_BREAK_DAYS, scope="covered"):
    """→ DataFrame(prev, next, missing)：相鄰兩根 K 棒之間缺了 ≥ min_days 個交易日的空缺（登錄 seq2 §二④）。
    ⚠ 只列事實；要不要當硬斷點由登錄決定（seq2 §二④ 寫的是要）。
    ⚠ 不在日曆上的 K 棒（0043f97：2026-09-22，^GSPC 缺那天；窗外）不參與計數。"""
    o = load_ohlc(ticker, scope)
    cal = load_calendar()
    pos = cal.get_indexer(o.index)
    o = o[pos >= 0]
    pos = pos[pos >= 0]
    if len(o) < 2:
        return pd.DataFrame({"prev": pd.DatetimeIndex([]), "next": pd.DatetimeIndex([]), "missing": np.array([], int)})
    miss = np.diff(pos) - 1
    k = np.where(miss >= min_days)[0]
    return pd.DataFrame({"prev": o.index[k], "next": o.index[k + 1], "missing": miss[k]})


# ── 母體 ─────────────────────────────────────────────────
def in_index(ticker, asof=None):
    """→ DataFrame（index＝NYSE 交易日，窗首 2016-01-04 ～ 日曆最後一天）：member、has_price。
    member：面板那天有列 ⇒ 取面板 in_index＝1；面板那天沒列 ⇒ 取 membership/universe.csv 的 spans（a ≤ d < b，
            與 build_panel.py 同一規則）。⇒ 整段缺價的 35 檔（含 SIVB、FRC、SBNY）照樣有 member＝True 的日子。
    has_price：面板那天有沒有列（⛔ 沒列 ＝ 沒有 K 棒，不補）。
    asof（selftest 用）：只用 asof 當天以前的面板列、spans 右端晚於 asof 的一律當「還沒移出」。"""
    cal = load_calendar()
    cal = cal[cal >= WINDOW[0]]
    if asof is not None:
        cal = cal[cal <= pd.Timestamp(asof)]
    m = np.zeros(len(cal), bool)
    for a, b in _spans(ticker, None if asof is None else pd.Timestamp(asof)):
        m |= np.asarray((cal >= a) & ((cal < b) if b is not None else True))
    out = pd.DataFrame({"member": m, "has_price": False}, index=cal)
    pn = panel(ticker)
    if len(pn):
        pn = pn[pn.index >= WINDOW[0]]
        if asof is not None:
            pn = pn[pn.index <= pd.Timestamp(asof)]
        idx = out.index.intersection(pn.index)
        out.loc[idx, "has_price"] = True
        out.loc[idx, "member"] = pn.loc[idx, "in_index"].values == 1
    return out


@functools.lru_cache(maxsize=1)
def _membership():
    """→ {date: (frozenset 有價, frozenset 無價)}，窗首起每個交易日。"""
    rows = {}
    for t in universe_table()["ticker"]:
        f = in_index(t)
        f = f[f["member"]]
        for d, hp in zip(f.index, f["has_price"].values):
            rows.setdefault(d, ([], []))[0 if hp else 1].append(t)
    return {d: (frozenset(a), frozenset(b)) for d, (a, b) in rows.items()}


def universe(date, include_unpriced=False):
    """→ date 當天的 S&P 500 成分股（排序過的 list）。
    預設 ＝ 面板 in_index＝1 且當天有列（登錄 seq2 §一「母體 panel 的 in_index＝1 當日；缺列 ⛔ 不補」）。
    include_unpriced=True ⇒ 另加當天在指數但沒有價格的（對 _month_end_roster.csv 的全部列用）。
    ⭐ 只用 date 當天的列與「到 date 為止還沒移出」⇒ 無前視（selftest E1 以截斷資料重建驗證）。
    date 不是交易日 ⇒ 回空 list。"""
    m = _membership().get(pd.Timestamp(date))
    if m is None:
        return []
    return sorted(m[0] | m[1]) if include_unpriced else sorted(m[0])


def no_ohlc_tickers():
    """→ 整段沒有 OHLC 的代號（母體裡沒有任何 covered 段）；0043f97 ＝ 35 檔。"""
    s = segments()
    cov = set(s.loc[s["kind"] == "covered", "ticker"])
    return sorted(set(universe_table()["ticker"]) - cov)


def partial_ohlc_tickers():
    """→ 有 covered 段、也有 gap 段的代號（在指數期間部分沒有價格）。"""
    s = segments()
    cov = set(s.loc[s["kind"] == "covered", "ticker"])
    gap = set(s.loc[s["kind"] == "gap", "ticker"])
    return sorted(cov & gap)


# ── 基準 ─────────────────────────────────────────────────
def benchmark_tr(source="SP500TR"):
    """→ pd.Series（index＝date）：總報酬水準。
    source="SP500TR"（主）＝ data/macro/yahoo_SP500TR.csv 的 adjclose；"SPY"（備援）＝ yahoo_SPY.csv 的 adjclose（含息）。
    ⛔ 不提供 ^GSPC（價格指數不含息，比含息面板每年多算約 1.5～2%；資料庫 1639）。"""
    f = {"SP500TR": "yahoo_SP500TR.csv", "SPY": "yahoo_SPY.csv"}[source]
    d = pd.read_csv(_p("macro", f), usecols=["date", "adjclose"], dtype={"date": str})
    s = pd.Series(d["adjclose"].values, index=pd.DatetimeIndex(pd.to_datetime(d["date"]), name="date"),
                  name=source).sort_index()
    return s[s.notna() & (s > 0)]


# ── 季營收 ───────────────────────────────────────────────
REV_COLS = ["ticker", "cik", "period_start", "period_end", "value", "first_filed", "first_form", "tag", "derived"]


@functools.lru_cache(maxsize=1)
def quarterly_revenue():
    """→ DataFrame：ticker,cik,period_start,period_end,value,first_filed,first_form,tag,derived,avail_date,cal_q。
    value＝第一次公布的數字；⛔ latest_value／latest_filed 根本不讀進來（usecols 排除）。
    avail_date ＝ first_filed 的下一個交易日（嚴格晚於；登錄 seq2 §五、seq4 §三）。
    cal_q ＝ period_end 所在的曆季（'2016Q1'；登錄 seq3 §四「用期間結束日」、seq4 §二「以期間結束日歸季」）。
    derived＝1（第四季 ＝ 全年 − 前三季，公布日取兩者晚者）照收（seq4 §三）。
    缺季 ⇒ 沒有列（⛔ 不補 0）。⚠ 來源本身有 value ≤ 0 的列（見 US_ADAPTER.md），本層不改、不刪。"""
    q = pd.read_csv(_p("fundamentals", "quarterly_revenue.csv"), usecols=REV_COLS,
                    dtype={"ticker": str, "cik": str, "first_form": str, "tag": str})
    for c in ("period_start", "period_end", "first_filed"):
        q[c] = pd.to_datetime(q[c])
    cal = load_calendar()
    i = cal.searchsorted(q["first_filed"].values, side="right")
    q["avail_date"] = pd.DatetimeIndex([cal[k] if k < len(cal) else pd.NaT for k in i])
    q["cal_q"] = q["period_end"].dt.to_period("Q").astype(str)
    return q[REV_COLS + ["avail_date", "cal_q"]].sort_values(["ticker", "period_end"]).reset_index(drop=True)


def revenue_asof(date):
    """→ 讀取日 date 當天已可用（avail_date ≤ date）的季營收列。"""
    q = quarterly_revenue()
    return q[q["avail_date"] <= pd.Timestamp(date)]


def revenue_not_applicable():
    """→ {ticker: 原因}：母體裡季營收一列都沒有的代號。
    原因取 quarterly_revenue_status.csv 的 status（no_revenue_tag／no_revenue_tag(bank)／no_companyfacts）；
    status 檔裡沒有的 ⇒ 'no_cik'（cik_map 沒對上）。"""
    q = quarterly_revenue()
    have = set(q["ticker"])
    st = pd.read_csv(_p("fundamentals", "quarterly_revenue_status.csv"), dtype=str).set_index("ticker")["status"]
    out = {}
    for t in universe_table()["ticker"]:
        if t not in have:
            out[t] = st.get(t, "no_cik")
    return dict(sorted(out.items()))
