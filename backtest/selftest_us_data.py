# -*- coding: utf-8 -*-
"""美股資料轉接層 backtest/us_data.py 的 fixture ＋ 查核。

⛔ 本檔不跑任何策略、不算任何策略報酬；輸出（backtest/resultsUS/）只含計數、sha、查核結果，
   ⛔ 不含任何美股價格或報酬數值（私有 repo 授權）。基準只報 ^SP500TR 與 SPY 的年化【差】。
⭐ 每條查核盡量附「會紅的反例」（fixture 先證明分得出來、不假紅）。

A 還原 OHLC　B 母體　C 季營收　D 基準　E 無前視
跑法：PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.selftest_us_data
"""
import csv
import datetime as dt
import io
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import us_data as U  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultsUS")
os.makedirs(OUT, exist_ok=True)
LOG = []
RES = []   # (id, status, summary)


T0 = dt.datetime.now()


def say(s=""):
    print(s, flush=True)
    if s.startswith("\n##"):
        sys.stderr.write("[%.0f 秒]\n" % (dt.datetime.now() - T0).total_seconds())
    LOG.append(s)


def check(cid, ok, summary, warn=False):
    st = "PASS" if ok else ("WARN" if warn else "FAIL")
    RES.append((cid, st, summary))
    say("%s %s｜%s" % ({"PASS": "✅", "WARN": "⚠", "FAIL": "❌"}[st], cid, summary))


# ════════════════════════════════════════════════════════
say("# selftest_us_data（%s）" % dt.datetime.now().strftime("%Y-%m-%d %H:%M"))
commit = U.data_commit()
say("資料根目錄 %s｜commit %s" % (U.ROOT, commit))
check("A0", commit.startswith(U.DATA_COMMIT), "資料 commit %s 對上登錄 seq4 §三 寫死的 %s" % (commit[:12], U.DATA_COMMIT))

seg = U.segments()
cov = seg[seg["kind"] == "covered"]
tickers_cov = sorted(cov["ticker"].unique())
uni = U.universe_table()
say("母體 %d 檔｜_segments %d 列（covered %d、gap %d）｜有 covered 段 %d 檔"
    % (len(uni), len(seg), len(cov), (seg["kind"] == "gap").sum(), len(tickers_cov)))

# ════════════════ A 還原 OHLC ════════════════
say("\n## A 還原 OHLC")

# A1 Yahoo：換算後 close ＝ adjclose
worst = 0.0
n_cmp = 0
for _, r in cov[cov["src"].str.startswith("yahoo:")].iterrows():
    f = r["src"].split(":", 1)[1]
    raw = pd.read_csv(U._p("prices_yahoo", f + ".csv"), dtype={"date": str})
    raw.index = pd.to_datetime(raw["date"])
    o = U.load_ohlc(r["ticker"])
    o = o[o["src"] == r["src"]]
    a = raw.loc[o.index, "adjclose"].values
    e = np.abs(o["close"].values / a - 1)
    worst = max(worst, e.max()) if len(e) else worst
    n_cmp += len(e)
check("A1", worst <= 1e-12, "Yahoo 換算後 close 與 adjclose：%d 根比對，最大相對誤差 %.1e（容差 1e-12）" % (n_cmp, worst))
# 反例：若誤用 adjclose/open 當係數 ⇒ close 就不等於 adjclose
raw = pd.read_csv(U._p("prices_yahoo", "AAPL.csv"))
bad = raw["close"] * raw["adjclose"] / raw["open"]
e_bad = np.abs(bad / raw["adjclose"] - 1).max()
check("A1-反例", e_bad > 1e-6, "反例（係數誤用 adjclose÷open）會紅：最大相對誤差 %.1e ≫ 1e-12" % e_bad)


def bar_viol(o, tol=1e-9):
    lo = o[["open", "close"]].min(axis=1)
    hi = o[["open", "close"]].max(axis=1)
    return (o["low"] > lo * (1 + tol)) | (hi > o["high"] * (1 + tol)) | (o["low"] > o["high"] * (1 + tol))


# A2 K 棒自洽：low ≤ open,close ≤ high
viol_rest, viol_raw, nbar = [], 0, 0
ohlc = {}
for t in tickers_cov:
    o = U.load_ohlc(t)
    ohlc[t] = o
    nbar += len(o)
    v = bar_viol(o)
    for d in o.index[v]:
        viol_rest.append((t, d.date().isoformat(), o.at[d, "src"]))
# 同樣的列在原始檔（未還原）是否本來就不自洽
raw_bad = 0
for t, d, src in viol_rest:
    kind, f = src.split(":", 1)
    if kind == "yahoo":
        rr = pd.read_csv(U._p("prices_yahoo", f + ".csv"), dtype={"date": str}).set_index("date").loc[d]
        rb = pd.DataFrame([{"open": rr["open"], "high": rr["high"], "low": rr["low"], "close": rr["close"]}])
    else:
        rr = pd.read_csv(U._p("prices", f + ".csv"), dtype={"date": str}).set_index("date").loc[d]
        rb = pd.DataFrame([{"open": rr["adjOpen"], "high": rr["adjHigh"], "low": rr["adjLow"], "close": rr["adjClose"]}])
    raw_bad += int(bar_viol(rb, tol=0).iloc[0])
say("   A2 違反列（代號 日期 來源）：%s%s" % (viol_rest[:20], " …" if len(viol_rest) > 20 else ""))
check("A2", len(viol_rest) == 0,
      "712 檔 %d 根還原 K 棒：low ≤ open,close ≤ high 違反 %d 根（相對容差 1e-9）；其中原始檔本來就違反 %d 根"
      % (nbar, len(viol_rest), raw_bad), warn=(len(viol_rest) > 0 and raw_bad == len(viol_rest)))
syn = pd.DataFrame([{"open": 10.0, "high": 9.5, "low": 9.0, "close": 9.2}])
check("A2-反例", bool(bar_viol(syn).iloc[0]), "反例（open＞high 的合成 K 棒）會紅")

# A3 面板 ret 與還原收盤日報酬一致（非硬斷點日）
TOL_RET = 1e-8   # 面板存 %.8f ⇒ 捨入誤差 ≤ 5e-9；浮點另計 < 1e-12


def ret_compare(t, scope, include_breaks=False):
    o = ohlc[t] if scope == "covered" else U.load_ohlc(t, "panel")
    pn = U.panel(t)
    prev_row = pd.Series(pn.index[:-1], index=pn.index[1:])   # 面板裡的前一列日期
    d = o.index[1:]
    p = o.index[:-1]
    same = prev_row.reindex(d).values == p.values               # 前一根 K 棒 ＝ 面板前一列
    keep = same & (include_breaks | ~o["hard_break"].values[1:].astype(bool))
    r_ohlc = o["close"].values[1:] / o["close"].values[:-1] - 1
    r_pan = pn["ret"].reindex(d).values
    k = keep & ~np.isnan(r_pan)
    diff = np.abs(r_ohlc[k] - r_pan[k])
    blank_in = int((keep & np.isnan(r_pan)).sum())
    return len(diff), int((diff > TOL_RET).sum()), (diff.max() if len(diff) else 0.0), blank_in, int((~same).sum())


for scope in ("covered", "panel"):
    n = bad = blank = skip = 0
    mx = 0.0
    worst_t = []
    for t in tickers_cov:
        a, b, m, bl, sk = ret_compare(t, scope)
        n += a
        bad += b
        blank += bl
        skip += sk
        mx = max(mx, m)
        if b:
            worst_t.append(t)
    check("A3-" + scope, bad == 0 and blank == 0,
          "scope=%s：面板 ret vs 還原收盤日報酬 %d 天比對，|差|>%.0e 的 %d 天（最大 %.1e）；非斷點日面板 ret 空白 %d 天；"
          "前一根 K 棒不是面板前一列而略過 %d 天%s" % (scope, n, TOL_RET, bad, mx, blank, skip,
                                          ("；不符代號 %s" % worst_t[:10]) if worst_t else ""))
# 反例：把硬斷點日也拿來比 ⇒ DHR、XRX 那兩天會紅
bad_with = sum(ret_compare(t, "covered", include_breaks=True)[1] for t in ("DHR", "XRX", "IR"))
check("A3-反例", bad_with >= 2, "反例（硬斷點日不排除）會紅：DHR／XRX／IR 不符 %d 天（≥2 ⇒ 比對分得出來）" % bad_with)

# A4 硬斷點
say("\n   A4 硬斷點")
all_breaks = []
for t in tickers_cov:
    h = ohlc[t]
    for d in h.index[h["hard_break"].astype(bool)]:
        all_breaks.append((t, d.date().isoformat(), h.at[d, "break_reason"]))
say("   covered 範圍內的全部硬斷點：%s" % all_breaks)
star = set()
for t in tickers_cov:
    pn = U.panel(t)
    for d in pn.index[pn["star"].astype(bool)]:
        star.add((t, d.date().isoformat()))
rep = {(t, d.date().isoformat()) for t, d in U.report_split_div_days()}
sd_flag = {(t, d) for t, d, r in all_breaks if "split_div" in r}
seam_flag = {(t, d) for t, d, r in all_breaks if "seam" in r}
exp_sd = {("DHR", "2016-07-05"), ("XRX", "2017-01-03")}
check("A4a", star == rep == sd_flag == exp_sd,
      "同日拆股＋配息：面板 src 帶 * %s ＝ _report.md %s ＝ 已標 split_div %s ＝ 登錄列的 DHR 2016-07-05、XRX 2017-01-03"
      % (sorted(star), sorted(rep), sorted(sd_flag)))
check("A4b", seam_flag == {("IR", "2020-03-02")},
      "來源接縫（covered 範圍）：已標 seam %s ＝ 登錄的 IR（yahoo:TT → yahoo:IR）" % sorted(seam_flag))
# 面板 ret 空白的日子（每檔第一列除外）⊆ 接縫
blank_not_seam = []
n_blank = 0
for t in tickers_cov:
    pn = U.panel(t)
    b = pn.index[1:][pn["ret"].isna().values[1:]]
    n_blank += len(b)
    srcs = pn["src"].values
    sw = {pn.index[i] for i in range(1, len(pn)) if srcs[i] != srcs[i - 1]}
    blank_not_seam += [(t, d.date().isoformat()) for d in b if d not in sw]
check("A4c", not blank_not_seam,
      "面板 ret 空白（各檔第一列除外）%d 天，全部落在來源切換日；不是切換日的 %d 天 %s"
      % (n_blank, len(blank_not_seam), blank_not_seam[:10]))
# 面板範圍的接縫（含暖身日）
pan_seams = []
for t in tickers_cov:
    h = U.hard_breaks(t, "panel")
    pan_seams += [(t, d.date().isoformat(), r) for d, r in zip(h["date"], h["reason"]) if "seam" in r]
say("   scope=panel 的接縫（含入指數前暖身日）：%s" % pan_seams)
# 跨斷點的假跳空確實存在（DHR）⇒ 斷點不是多餘的
o = ohlc["DHR"]
i = o.index.get_loc(pd.Timestamp("2016-07-05"))
jump = o["close"].iloc[i] / o["close"].iloc[i - 1] - 1
pr = U.panel("DHR").at[pd.Timestamp("2016-07-05"), "ret"]
check("A4d", abs(jump - pr) > 0.5 and o["piece"].iloc[i] == o["piece"].iloc[i - 1] + 1,
      "DHR 2016-07-05：跨日還原收盤比與面板 ret 差 > 50 個百分點（Yahoo 重複還原的假跳空）⇒ 已切成新段 piece")
# OHLC 與面板同源、同日
mism = []
for t in tickers_cov:
    o = ohlc[t]
    pn = U.panel(t)
    j = pn.reindex(o.index)
    if j["src"].isna().any() or (j["src"].values != o["src"].values).any():
        mism.append(t)
check("A4e", not mism, "每根 covered K 棒在面板都有同日、同 src 的列；不符 %d 檔 %s" % (len(mism), mism[:10]))

# A5 scope 一致
dif = []
for t in tickers_cov:
    a = ohlc[t]
    b = U.load_ohlc(t, "panel").reindex(a.index)
    if not np.array_equal(a[["open", "high", "low", "close"]].values, b[["open", "high", "low", "close"]].values):
        dif.append(t)
check("A5", not dif, "scope=panel 在 covered 日期上與 scope=covered 逐位元相同；不同 %d 檔 %s" % (len(dif), dif[:10]))

# A6 K 棒全在 NYSE 日曆上＋連續 ≥5 交易日無 K 棒的空缺（登錄 seq2 §二④，只報數）
cal = U.load_calendar()
w0, w1 = U.WINDOW
off_in, off_out = 0, {}
for t in tickers_cov:
    ix = ohlc[t].index
    bad_ix = ix[cal.get_indexer(ix) < 0]
    off_in += int(((bad_ix >= w0) & (bad_ix <= w1)).sum())
    for d in bad_ix[(bad_ix < w0) | (bad_ix > w1)]:
        off_out[d.date().isoformat()] = off_out.get(d.date().isoformat(), 0) + 1
# 窗內每年休市（非週末）日數
yrs = {}
d = w0
cs = set(cal)
while d <= w1:
    if d.dayofweek < 5 and d not in cs:
        yrs[d.year] = yrs.get(d.year, 0) + 1
    d += pd.Timedelta(days=1)
say("   窗內每年平日休市日數：%s（NYSE 正常 9～10 天；2018、2025 各多一天國喪）" % yrs)
gaps = []
g1 = []
for t in tickers_cov:
    g = U.long_gaps(t, min_days=1)
    g = g[(g["prev"] >= w0) & (g["next"] <= w1)]
    g1 += [int(m) for m in g["missing"]]
    g = g[g["missing"] >= U.GAP_BREAK_DAYS]
    gaps += [(t, a.date().isoformat(), b.date().isoformat(), int(m)) for a, b, m in
             zip(g["prev"], g["next"], g["missing"])]
check("A6", off_in == 0, "窗內 K 棒不在 NYSE 日曆上的 %d 根（窗外：%s）；窗內 covered K 棒之間缺 ≥1 交易日的空缺 %d 處（共缺 %d 天），"
      "其中 ≥%d 交易日 %d 處／%d 檔" % (off_in, off_out, len(g1), sum(g1), U.GAP_BREAK_DAYS, len(gaps),
                                   len({x[0] for x in gaps})))
say("   ≥5 交易日空缺明細（代號 前一根 後一根 缺幾天）：%s" % gaps)

# ════════════════ B 母體 ════════════════
say("\n## B 母體")
ros = pd.read_csv(U._p("panel", "_month_end_roster.csv"), dtype=str)
mis_all, mis_px, cnt = [], [], []
for d, g in ros.groupby("month_end"):
    ua = set(U.universe(d, include_unpriced=True))
    up = set(U.universe(d))
    ra = set(g["ticker"])
    rp = set(g.loc[g["has_price"] == "1", "ticker"])
    cnt.append(len(ua))
    if ua != ra:
        mis_all.append((d, sorted(ua - ra), sorted(ra - ua)))
    if up != rp:
        mis_px.append((d, sorted(up - rp), sorted(rp - up)))
say("   月底全名冊不符（日期, 本層多, 名冊多）：%s" % mis_all)
say("   月底有價名冊不符：%s" % mis_px)
# 不符的是否全是「名冊多、has_price＝0、且那天剛好 ＝ spans 右端（移出日）」
#   ⇒ build_panel.py 用 a ≤ d < b（移出日當天不在指數），roster.py 補無價列用 a ≤ d ≤ b（含移出日）
expl = []
for d, extra, more in mis_all:
    for t in more:
        hp = ros.loc[(ros["month_end"] == d) & (ros["ticker"] == t), "has_price"].iloc[0]
        ends = [b for a, b in U._spans(t) if b is not None]
        expl.append((d, t, hp, pd.Timestamp(d) in ends))
all_end = bool(expl) and all(hp == "0" and e for _, _, hp, e in expl) and not any(x[1] for x in mis_all)
say("   名冊多出的列（月底, 代號, has_price, 當天＝移出日）：%s" % expl)
check("B1", not mis_all and not mis_px,
      "_month_end_roster %d 個月底：universe(d) 與 has_price＝1 不符 %d 個月；universe(d, include_unpriced) 與名冊全列不符 %d 個月"
      "（%d 列，全部是名冊多出 has_price＝0、且月底 ＝ 該檔移出日：%s ⇒ roster.py 補列用 d ≤ b、面板用 d < b 的不一致，"
      "本層照面板）；每月檔數 %d～%d" % (ros["month_end"].nunique(), len(mis_px), len(mis_all), len(expl), all_end,
                               min(cnt), max(cnt)),
      warn=bool(mis_all and not mis_px and all_end))
# 反例：拿掉一檔 ⇒ 會紅
d0 = ros["month_end"].iloc[0]
check("B1-反例", set(U.universe(d0)[1:]) != set(ros.loc[(ros["month_end"] == d0) & (ros["has_price"] == "1"), "ticker"]),
      "反例（universe 少一檔）會紅")

# B2 倒閉銀行
w0, w1 = U.WINDOW
for t in U.FAILED_BANKS:
    f = U.in_index(t)
    f = f[(f.index >= w0) & (f.index <= w1)]
    nm = int(f["member"].sum())
    npx = int(f["has_price"].sum())
    no = len(U.load_ohlc(t))
    nr = int(((ros["ticker"] == t) & (ros["has_price"] == "0")).sum())
    nr1 = int(((ros["ticker"] == t) & (ros["has_price"] == "1")).sum())
    first = f.index[f["member"]].min().date() if nm else None
    last = f.index[f["member"]].max().date() if nm else None
    check("B2-" + t, nm > 0 and npx == 0 and no == 0 and nr > 0 and nr1 == 0,
          "%s：窗內在指數 %d 個交易日（%s～%s）、有價 %d 日、OHLC %d 根；名冊 has_price＝0 %d 個月、＝1 %d 個月"
          % (t, nm, first, last, npx, no, nr, nr1))

# B3 覆蓋數
no = U.no_ohlc_tickers()
check("B3", len(tickers_cov) == 712 and len(no) == 35 and set(no) == set(U.NO_OHLC_35_LETTER) and len(uni) == 747,
      "有 OHLC %d 檔、整段沒有 %d 檔（與資料庫 1753 名單相同：%s）；部分缺 %s"
      % (len(tickers_cov), len(no), set(no) == set(U.NO_OHLC_35_LETTER), U.partial_ohlc_tickers()))

# B4 股-日佔比（登錄 seq2 §一「檔數與它們在指數的股-日佔比必報」）
tot = no35 = nopx = 0
nopx_priced = 0
for t in uni["ticker"]:
    f = U.in_index(t)
    f = f[(f.index >= w0) & (f.index <= w1) & f["member"]]
    tot += len(f)
    k = int((~f["has_price"]).sum())
    nopx += k
    if t in no:
        no35 += len(f)
    else:
        nopx_priced += k
say("   窗 %s～%s：在指數股-日 %d；35 檔 %d（%.2f%%）；全部無價股-日 %d（%.2f%%），其中有 OHLC 的檔當天沒列 %d"
    % (w0.date(), w1.date(), tot, no35, no35 / tot * 100, nopx, nopx / tot * 100, nopx_priced))
check("B4", tot > 0, "35 檔佔在指數股-日 %.2f%%；含部分缺與零星缺列的全部無價佔 %.2f%%（資料庫 1550 說 1.58%%）"
      % (no35 / tot * 100, nopx / tot * 100))

# ════════════════ C 季營收 ════════════════
say("\n## C 季營收")
q = U.quarterly_revenue()
raw_q = pd.read_csv(U._p("fundamentals", "quarterly_revenue.csv"), dtype=str)
check("C0", len(q) == len(raw_q) and "latest_value" not in q.columns and "latest_filed" not in q.columns,
      "轉接後 %d 列 ＝ 原檔 %d 列（⛔ 不增列、不補季）；latest_value／latest_filed 不在輸出欄" % (len(q), len(raw_q)))
calset = set(cal)
cal_last = cal[-1]
na_rows = q[q["avail_date"].isna()]
na = len(na_rows)
na_ok = bool((na_rows["first_filed"] >= cal_last).all())    # 只允許：申報日在快照日曆最後一天或之後
qa = q[q["avail_date"].notna()]
gt_end = bool((qa["avail_date"] > qa["period_end"]).all())
gt_ff = bool((qa["avail_date"] > qa["first_filed"]).all())
on_cal = bool(qa["avail_date"].isin(cal).all())


# 下一個交易日：中間不可夾別的交易日（獨立寫法：逐日往後找；超過日曆尾 ⇒ NaT）
def nxt(d):
    d = d + pd.Timedelta(days=1)
    while d not in calset:
        if d > cal_last:
            return pd.NaT
        d = d + pd.Timedelta(days=1)
    return d


ff_u = q["first_filed"].drop_duplicates()
m = {d: nxt(d) for d in ff_u}
indep = q["first_filed"].map(m)
exact = bool(((indep == q["avail_date"]) | (indep.isna() & q["avail_date"].isna())).all())
lag = (qa["avail_date"] - qa["period_end"]).dt.days
w_in = qa[(qa["avail_date"] >= U.WINDOW[0]) & (qa["avail_date"] <= U.WINDOW[1])]
check("C1", na_ok and gt_end and gt_ff and on_cal and exact,
      "可用日：NaT %d 列（全是 first_filed ≥ 快照日曆最後一天 %s 的：%s）；其餘一律晚於期末 %s（落後最少 %d 天、中位 %d 天）；"
      "一律晚於 first_filed %s；都是交易日 %s；＝ first_filed 之後第一個交易日（逐日獨立重算）%s；可用日落在窗內 %d 列"
      % (na, cal_last.date(), na_ok, gt_end, lag.min(), lag.median(), gt_ff, on_cal, exact, len(w_in)))

# C2 抽查 5 家
pick = []
def add(t, cond, why):
    r = q[(q["ticker"] == t) & cond]
    if len(r):
        pick.append((why, r.iloc[0]))
add("AAPL", q["period_end"].between("2023-06-01", "2023-07-31"), "一般 10-Q")
add("MSFT", (q["derived"] == 1) & q["period_end"].between("2022-06-01", "2022-06-30"), "derived＝1 第四季（10-K）")
dis_cur = q.loc[(q["ticker"] == "DIS"), "cik"].iloc[-1]
add("DIS", (q["cik"] != dis_cur) & q["period_end"].between("2017-01-01", "2018-12-31"), "前身 CIK")
fri = q[q["first_filed"].dt.dayofweek == 4]
add("WAT", q["period_end"].between("2016-06-01", "2016-07-31"), "52／53 週會計年度")
t5 = fri[(fri["ticker"] == "NVDA")]
if len(t5):
    pick.append(("週五申報 ⇒ 可用日跨週末", t5.iloc[-1]))
else:
    pick.append(("週五申報 ⇒ 可用日跨週末", fri.iloc[0]))
ok5 = True
for why, r in pick:
    good = r["avail_date"] == nxt(r["first_filed"]) and r["avail_date"] > r["period_end"]
    ok5 &= bool(good)
    say("   %-6s %-22s 期末 %s｜%s｜first_filed %s（%s）⇒ 可用日 %s（%s）｜cal_q %s｜derived %d｜cik %s%s"
        % (r["ticker"], why, r["period_end"].date(), r["first_form"], r["first_filed"].date(),
           r["first_filed"].day_name()[:3], r["avail_date"].date(), r["avail_date"].day_name()[:3],
           r["cal_q"], r["derived"], r["cik"], "" if good else " ❌"))
check("C2", ok5 and len(pick) == 5, "抽查 %d 家 first_filed 與可用日（值不列出）：全部 ＝ 下一個交易日且晚於期末" % len(pick))

# C3 缺季不補 0
z0 = int((q["value"] == 0).sum())
zn = int((q["value"] < 0).sum())
zt = sorted(q.loc[q["value"] <= 0, "ticker"].unique())
xom = int(((q["ticker"] == "XOM") & (q["period_end"] < "2025-01-01")).sum())
# 曆季（期末歸季）的洞與撞：連續兩個會計季在時間上相接，但曆季跳 0 或跳 2
qq = q.sort_values(["ticker", "period_end"]).copy()
qq["pq"] = qq["period_end"].dt.year * 4 + (qq["period_end"].dt.quarter - 1)
same_t = qq["ticker"].eq(qq["ticker"].shift())
contig = same_t & ((qq["period_start"] - qq["period_end"].shift()).dt.days.between(0, 2))
step = qq["pq"] - qq["pq"].shift()
collide = contig & (step == 0)
skip2 = contig & (step == 2)
real_hole = same_t & ~contig
say("   value＝0 的列 %d、value＜0 的列 %d（來源本身的值，⛔ 非本層補的）；涉及 %d 檔：%s" % (z0, zn, len(zt), zt))
say("   XOM 2025 以前的季：%d 列（資料庫 2016 §三：Exxon 只從 2025 起）⇒ 缺季沒有列" % xom)
say("   曆季歸季（期末）：會計季相接但落在同一曆季（撞）%d 處／%d 檔；相接但跳過一個曆季（假洞）%d 處／%d 檔；"
    "時間上真的不相接（真缺）%d 處／%d 檔"
    % (int(collide.sum()), qq.loc[collide, "ticker"].nunique(), int(skip2.sum()), qq.loc[skip2, "ticker"].nunique(),
       int(real_hole.sum()), qq.loc[real_hole, "ticker"].nunique()))
say("   假洞最多的代號：%s" % qq.loc[skip2].groupby("ticker").size().sort_values(ascending=False).head(15).to_dict())
check("C3", xom == 0 and len(q) == len(raw_q),
      "缺季沒有列（XOM 2025 前 %d 列；總列數不變）；⚠ 來源有 value＝0 %d 列、＜0 %d 列（%d 檔）；"
      "⚠ 期末歸曆季會造成假洞 %d 處／%d 檔（52／53 週年度）" %
      (xom, z0, zn, len(zt), int(skip2.sum()), qq.loc[skip2, "ticker"].nunique()))

# C4 latest_value 沒被讀：重編過的季，轉接值 ＝ value ≠ latest_value
rq = raw_q.copy()
rq["value"] = rq["value"].astype("int64")
rq["latest_value"] = pd.to_numeric(rq["latest_value"], errors="coerce")
rq["period_end"] = pd.to_datetime(rq["period_end"])
mm = q.merge(rq[["ticker", "period_end", "value", "latest_value"]], on=["ticker", "period_end"], suffixes=("", "_raw"))
rest = mm[mm["value_raw"] != mm["latest_value"]]
check("C4", len(mm) == len(q) and (mm["value"] == mm["value_raw"]).all() and not (rest["value"] == rest["latest_value"]).any(),
      "重編過的季 %d 個：轉接值全部 ＝ value（第一次公布），沒有一個 ＝ latest_value" % len(rest))

# C5 不適用名單
na_ = U.revenue_not_applicable()
letter16 = set("ANDV CCEP CMA CVC DFS FDXF FITB HBAN MJN PBCT PCL POM RF SE SIVB SYF TFC".split())
say("   季營收一列都沒有的 %d 檔：%s" % (len(na_), na_))
say("   資料庫 2016 列的不適用名單（%d 個代號）與實際的差：名單有但實際有營收 %s；實際沒有但名單沒列 %s"
    % (len(letter16), sorted(letter16 - set(na_)), sorted(set(na_) - letter16 - {"FRC", "SBNY"})))
check("C5", False, "季營收整檔沒有的 %d 檔（no_revenue_tag 16、no_companyfacts 1、no_cik %d）；與登錄 seq4 §三「不適用 16 家與 FRC、SBNY」差 %s"
      % (len(na_), sum(v == "no_cik" for v in na_.values()), sorted(set(na_) ^ (letter16 | {"FRC", "SBNY"}))),
      warn=True)

# ════════════════ D 基準 ════════════════
say("\n## D 基準")
tr = U.benchmark_tr("SP500TR")
spy = U.benchmark_tr("SPY")
calw = cal[(cal >= w0) & (cal <= w1)]
mt = len(calw.difference(tr.index)), len(tr[(tr.index >= w0) & (tr.index <= w1)].index.difference(calw))
ms = len(calw.difference(spy.index)), len(spy[(spy.index >= w0) & (spy.index <= w1)].index.difference(calw))
base = cal[cal < w0][-1]


def ann(s):
    yrs = (w1 - base).days / 365.25
    return (s.loc[w1] / s.loc[base]) ** (1 / yrs) - 1


diff_bp = (ann(tr) - ann(spy)) * 1e4
raw_tr = pd.read_csv(U._p("macro", "yahoo_SP500TR.csv"))
same_cl = bool(np.allclose(raw_tr["close"], raw_tr["adjclose"], rtol=0, atol=0))
check("D1", mt == (0, 0) and ms == (0, 0),
      "窗內 NYSE 日 %d 天：^SP500TR 缺 %d、多 %d；SPY 缺 %d、多 %d" % (len(calw), mt[0], mt[1], ms[0], ms[1]))
check("D2", abs(diff_bp) < 50,
      "同窗年化差（^SP500TR − SPY 還原，%s 收盤 → %s 收盤，年＝日曆日÷365.25）＝ %+.1f 基點"
      "（SPY 含 0.09%% 費用率，預期正且小）；^SP500TR 的 adjclose ＝ close：%s" % (base.date(), w1.date(), diff_bp, same_cl))

# ════════════════ E 無前視 ════════════════
say("\n## E 無前視")
rng = np.random.default_rng(20260925)
alld = cal[(cal >= w0) & (cal <= w1)]
samp = sorted(set(rng.choice(alld, 12, replace=False)) |
              {pd.Timestamp(x) for x in ("2016-01-04", "2018-03-19", "2019-01-02", "2021-12-20", "2023-03-14",
                                         "2023-03-15", "2023-05-03", "2023-05-04", "2020-02-28", "2020-03-02")})
samp = [pd.Timestamp(d) for d in samp if pd.Timestamp(d) in calset]
bad = []
for d in samp:
    pa, pu = set(), set()
    for t in uni["ticker"]:
        f = U.in_index(t, asof=d)
        if len(f) and f.index[-1] == d and f["member"].iloc[-1]:
            (pa if f["has_price"].iloc[-1] else pu).add(t)
    if pa != set(U.universe(d)) or (pa | pu) != set(U.universe(d, include_unpriced=True)):
        bad.append(d.date().isoformat())
check("E1", not bad, "universe(d) ＝ 只用 d 以前的面板列、spans 右端晚於 d 當『尚未移出』重建的結果：%d 個日子不符 %d %s"
      % (len(samp), len(bad), bad))
# 反例：拿隔天的名冊 ⇒ 在成分變動日會不同
chg = [d for d, e in zip(alld[:-1], alld[1:]) if set(U.universe(d)) != set(U.universe(e))]
check("E1-反例", len(chg) > 0, "反例（用隔天名冊）在 %d 個變動日會與 universe(d) 不同 ⇒ E1 分得出前視" % len(chg))

# E2 季營收 asof
viol = 0
for d in samp:
    viol += int((U.revenue_asof(d)["avail_date"] > d).sum())
r0 = q.iloc[len(q) // 2]
A = r0["avail_date"]
prevd = cal[cal < A][-1]
key = (q["ticker"] == r0["ticker"]) & (q["period_end"] == r0["period_end"])
in_prev = bool(key.loc[U.revenue_asof(prevd).index].any())
in_A = bool(key.loc[U.revenue_asof(A).index].any())
ff_is_td = q["first_filed"].isin(cal)
leak = int((ff_is_td & (q["avail_date"] <= q["first_filed"])).sum())
check("E2", viol == 0 and not in_prev and in_A and leak == 0,
      "revenue_asof(d) 在 %d 個日子都只含可用日 ≤ d 的列（違反 %d）；抽一列：可用日前一交易日不在、可用日當天在；"
      "first_filed 是交易日的 %d 列沒有一列在申報當天就可用" % (len(samp), viol, int(ff_is_td.sum())))
naive = int((ff_is_td).sum())
check("E2-反例", naive > 0, "反例（可用日＝first_filed 當天）會在 %d 列提早一天 ⇒ E2 分得出來" % naive)

# ════════════════ 輸出 ════════════════
say("\n## 結果")
npass = sum(s == "PASS" for _, s, _ in RES)
nwarn = sum(s == "WARN" for _, s, _ in RES)
nfail = sum(s == "FAIL" for _, s, _ in RES)
say("PASS %d｜WARN %d｜FAIL %d" % (npass, nwarn, nfail))
fp = U.fingerprint()
with io.open(os.path.join(OUT, "fingerprint.csv"), "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["file", "sha256"])
    w.writerow(["commit", commit])
    for k, v in fp.items():
        w.writerow([k, v])
with io.open(os.path.join(OUT, "checks.csv"), "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["id", "status", "summary"])
    w.writerows(RES)
with io.open(os.path.join(OUT, "selftest_us_data.log"), "w", encoding="utf-8") as f:
    f.write("\n".join(LOG) + "\n")
sys.exit(1 if nfail else 0)
