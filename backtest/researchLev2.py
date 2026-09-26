# -*- coding: utf-8 -*-
"""PREREG正2現金（台股策略線登錄 seq1 sha 9a0c5b353e90dd78；裁定 seq216 §一② 附則、seq217）—— pre 段：資料檢查與結構。

⛔ pre 段【不讀報酬】：不算任何組合、任何單檔的年化／回落／區間報酬。
   唯一例外 ＝ 0050 主窗錨（rerun17 既有釘死值）的逐位元重現 ⇒ 只報「逐位元 True／False」與錨值本身。
   跳動掃描只報【超出漲跌幅限制】的旗標列（資料錯誤），⛔ 不報任何分佈。
⛔ 不改任何既有 .py；資料一律讀 rerun17.use_snapshot()（edc6f8002f 快照），main 只用 git show 對照。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLev2 pre --official ~/lev2_official
    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLev2 body      # 本體（登錄 seq2；讀法寫在 body 段開頭）
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchLev2_check.py

--official 目錄（官方原檔，repo 外；sha256 記進 pre_official_src.csv）：
    twt49u_<年>.json      TWSE exRight/TWT49U（除權除息計算結果表）2015～2026-09-24，每年一檔
    twtcau.json           TWSE split/TWTCAU（ETF 分割（反分割）恢復買賣參考價格）2015-01-01～2026-09-24
    stockday_00631L_2014{10,11,12}.json、stockday_00685L_201703.json、stockday_00685L_2022{02..06}.json
                          TWSE afterTrading/STOCK_DAY（⛔ 只取日期、成交股數、收盤價是否為「--」，不讀價格數值）

登錄沒寫死的讀法 ⇒ 本支【只列選項】，⛔ 不選（見 PRE_REPORT.md §五）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from itertools import product

import numpy as np
import pandas as pd

from . import data as D
from . import rerun17 as RR
from . import research13 as R13

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsLev2")
SIDS = ("0050", "0052", "00631L", "00685L")
ETFS = ("0050", "0052")
LEVS = ("00631L", "00685L")
EXP_END = "2021-12-30"                    # 登錄 §四：探索段 共同起點～2021-12-30
CONF0, CONF1 = "2022-01-03", "2026-08-24"  # 登錄 §四：確認段
MA_N = 200                                # 登錄 §一「上市滿 200 個交易日」、C1／C4 的 200 日線
ANN = 245
DB_REPO = os.path.expanduser("~/tw-stock-data")
TRACK = {"0050": "臺灣50指數", "0052": "臺灣資訊科技指數（科技類股 ETF；⛔ 不是 0050 同類）",
         "00631L": "臺灣50指數 正向2倍（每日重設）", "00685L": "臺灣加權股價指數 正向2倍（每日重設；⛔ 不是台灣50）"}


LOGF = "pre_run.log"


def log(msg):
    print(msg, flush=True)
    with open(os.path.join(OUT, LOGF), "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def roc2iso(s: str) -> str:
    s = s.replace("年", "/").replace("月", "/").replace("日", "")
    y, m, d = s.split("/")
    return f"{int(y) + 1911:04d}-{int(m):02d}-{int(d):02d}"


def num(s: str) -> float:
    return float(str(s).replace(",", ""))


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


# ═════════════ 官方原檔 ═════════════
def read_official(odir):
    src, exr, spl, sday = [], [], [], {}
    for fn in sorted(os.listdir(odir)):
        p = os.path.join(odir, fn)
        if not fn.endswith(".json"):
            continue
        j = json.load(open(p, encoding="utf-8"))
        src.append({"檔": fn, "sha256": sha256(p), "stat": j.get("stat"), "title": j.get("title"), "列數": len(j.get("data", []))})
        if fn.startswith("twt49u_"):
            if j["fields"][1:7] != ["股票代號", "股票名稱", "除權息前收盤價", "除權息參考價", "權值+息值", "權/息"]:
                raise SystemExit(f"⛔ {fn} 欄位對不上：{j['fields']}")
            for r in j["data"]:
                if r[1].strip() in SIDS:
                    exr.append({"sid": r[1].strip(), "date": roc2iso(r[0]), "pre": num(r[3]), "ref": num(r[4]),
                                "value": num(r[5]), "kind": r[6].strip(), "src": fn})
        elif fn == "twtcau.json":
            if j["fields"][:6] != ["恢復買賣日期", "ETF代號", "名稱", "分割(反分割)", "停止買賣前收盤價格", "恢復買賣參考價"]:
                raise SystemExit(f"⛔ {fn} 欄位對不上：{j['fields']}")
            for r in j["data"]:
                spl.append({"sid": r[1].strip(), "date": roc2iso(r[0]), "type": r[3].strip(), "pre": num(r[4]), "ref": num(r[5]),
                            "limit_up": num(r[6]), "limit_down": num(r[7]), "src": fn})
        elif fn.startswith("stockday_"):
            if j["fields"][:2] != ["日期", "成交股數"] or j["fields"][6] != "收盤價":
                raise SystemExit(f"⛔ {fn} 欄位對不上：{j['fields']}")
            sid = fn.split("_")[1]
            # ⛔ 只取日期、成交股數、收盤價是否為「--」（有沒有成交），⛔ 不取價格數值
            sday.setdefault(sid, []).extend((roc2iso(r[0]), num(r[1]), r[6].strip() not in ("--", "")) for r in j["data"])
    return pd.DataFrame(src), pd.DataFrame(exr), pd.DataFrame(spl), sday


# ═════════════ 一、資料狀況 ═════════════
def raw_rows(sid):
    return pd.read_csv(os.path.join(D.DATA, "stocks", f"{sid}.csv"), dtype=str)


def data_status(cal, meta, uni, ind_ids, seg, sday):
    rows, miss_rows = [], []
    for sid in SIDS:
        r = raw_rows(sid)
        dates = pd.to_datetime(r["date"])
        cl = pd.to_numeric(r["close"], errors="coerce")
        ok = cl > 0
        d0, d1 = dates.min(), dates.max()
        i0, i1 = int(cal.searchsorted(d0)), int(cal.searchsorted(d1))
        span = cal[i0:i1 + 1]
        have = set(dates[ok])
        rowset = set(dates)
        nt = set(dates[r["price_basis"].fillna("") == "無成交"])
        miss = [d for d in span if d not in have]
        adj = D.load_adj(sid)
        sp = adj[adj["event"] == "etfsplit"]["date"].tolist() if adj is not None else []
        off = {x[0]: x for x in sday.get(sid, [])}
        for d in miss:
            why = ""
            if d in nt:
                why = "無成交（資料列在、price_basis＝無成交、價格空、valid_bar＝0）"
            elif d not in rowset:
                for e in sp:
                    j = int(cal.searchsorted(e))
                    if j - 10 <= int(cal.searchsorted(d)) < j:
                        why = f"分割停止買賣（無資料列；恢復買賣日 {e.date()}）"
            o = off.get(str(d.date()))
            miss_rows.append({"sid": sid, "date": d.date(), "段": seg_of(d, seg), "推定原因": why or "未知",
                              "官方STOCK_DAY": "" if o is None else f"成交股數 {int(o[1])}、{'有' if o[2] else '無'}收盤價"})
        amt = pd.Series(pd.to_numeric(r["amount"], errors="coerce").to_numpy(), index=dates)
        m = meta[meta["stock_id"] == sid].iloc[0]
        vb = r["valid_bar"].value_counts(dropna=False).to_dict()
        seg_days = {}
        for k, (a, b) in seg.items():
            if a is None:
                continue
            ia, ib = int(cal.searchsorted(pd.Timestamp(a))), int(cal.searchsorted(pd.Timestamp(b)))
            s = cal[ia:ib + 1]
            s = s[s >= d0]                                          # ⚠ 只數該檔 DB 首日之後（00685L 2017-03-30 上市）
            seg_days[f"{k}_日曆日"] = len(s)
            seg_days[f"{k}_有成交日"] = int(sum(d in have for d in s))
            am = amt.reindex(s).fillna(0.0)                          # 流動性（成交金額，元；⛔ 不是報酬）
            seg_days[f"{k}_日成交金額中位（元）"] = float(am.median())
            seg_days[f"{k}_日成交金額＜100萬的日數"] = int((am < 1_000_000).sum())
        rows.append({"sid": sid, "名稱": m["name"], "市場": m["market"], "kind": m["kind"], "追蹤": TRACK[sid],
                     "first_seen": m["first_seen"], "last_seen": m["last_seen"],
                     "資料首日": d0.date(), "資料末日": d1.date(), "日K列數": len(r), "有效收盤列數": int(ok.sum()),
                     "區間交易日（日曆）": len(span), "缺日": len(miss), "缺日_無成交列": int(sum(d in nt for d in miss)),
                     "缺日_無資料列": int(sum(d not in rowset for d in miss)),
                     "volume為0列": int((pd.to_numeric(r["volume"], errors="coerce") == 0).sum()),
                     "valid_bar分佈": json.dumps({str(k): int(v) for k, v in vb.items()}, ensure_ascii=False),
                     "price_basis非空": int(r["price_basis"].notna().sum()), "last_price非空": int(r["last_price"].notna().sum()),
                     "在load_universe": sid in set(uni["stock_id"]), "在industry.csv": sid in ind_ids,
                     "adj檔事件數": 0 if adj is None else len(adj), **seg_days})
    return pd.DataFrame(rows), pd.DataFrame(miss_rows)


def seg_of(d, seg):
    d = pd.Timestamp(d)
    if d < pd.Timestamp("2015-01-01"):
        return "2015 以前"
    if d <= pd.Timestamp(EXP_END):
        return "探索段（～2021-12-30）"
    if pd.Timestamp(CONF0) <= d <= pd.Timestamp(CONF1):
        return "確認段"
    return "確認段之後（窗外）"


# ═════════════ 還原事件 × 官方 ═════════════
def events_vs_official(exr, spl, cal):
    rows = []
    for sid in SIDS:
        adj = D.load_adj(sid)
        if adj is None:
            continue
        f = adj["factor"].to_numpy(float)
        cum_re = np.cumprod(f[::-1])[::-1]
        for i, a in adj.iterrows():
            d = a["date"].strftime("%Y-%m-%d")
            rec = {"sid": sid, "date": d, "段": seg_of(d, None), "event": a["event"], "kind_db": a["kind"] if isinstance(a["kind"], str) else "",
                   "pre_close_db": a["pre_close"], "ref_price_db": a["ref_price"], "factor_db": a["factor"], "cum_factor_db": a["cum_factor"],
                   "cum_factor_重算": float(cum_re[i]), "cum_差": float(cum_re[i] - a["cum_factor"])}
            if a["event"] == "exright":
                o = exr[(exr["sid"] == sid) & (exr["date"] == d)]
                if len(o) == 1:
                    o = o.iloc[0]
                    exp = (o["pre"] - o["value"]) / o["pre"]          # adjust.py EXACT_REF_SRC：TWSE 除權息用 pre − 權息值
                    rec.update(官方來源="TWT49U", 官方_pre=o["pre"], 官方_ref=o["ref"], 官方_權息值=o["value"], 官方_kind=o["kind"],
                               factor_官方重算=exp, factor_差=float(a["factor"] - exp),
                               pre相符=bool(o["pre"] == a["pre_close"]), ref相符=bool(o["ref"] == a["ref_price"]))
                else:
                    rec.update(官方來源=f"TWT49U 找到 {len(o)} 列")
            elif a["event"] == "etfsplit":
                o = spl[(spl["sid"] == sid) & (spl["date"] == d)]
                if len(o) == 1:
                    o = o.iloc[0]
                    exp = o["ref"] / o["pre"]
                    k = o["pre"] / o["ref"]
                    kk = round(k) if k >= 1 else 1 / round(1 / k)
                    exact = 1 / kk if k >= 1 else round(1 / k)
                    j = int(cal.searchsorted(pd.Timestamp(d)))
                    rec.update(官方來源="TWTCAU", 官方_pre=o["pre"], 官方_ref=o["ref"], 官方_kind=o["type"] or "（官方此欄空白）",
                               官方_漲停=o["limit_up"], 官方_跌停=o["limit_down"],
                               factor_官方重算=exp, factor_差=float(a["factor"] - exp),
                               pre相符=bool(o["pre"] == a["pre_close"]), ref相符=bool(o["ref"] == a["ref_price"]),
                               隱含比率_pre除ref=k, 名目比率=("1拆" + str(int(kk))) if k >= 1 else ("反分割 " + str(int(round(1 / k))) + "合1"),
                               factor_整數比=exact, factor_相對整數比=float(a["factor"] / exact - 1),
                               漲跌幅限制=round((o["limit_up"] / o["ref"] - 1) * 10) / 10)
                else:
                    rec.update(官方來源=f"TWTCAU 找到 {len(o)} 列")
            rows.append(rec)
    ev = pd.DataFrame(rows)
    # 官方有、資料庫沒有
    have = set(zip(ev["sid"], ev["date"]))
    extra = [dict(sid=r.sid, date=r.date, 表="TWT49U") for r in exr.itertuples() if (r.sid, r.date) not in have] + \
            [dict(sid=r.sid, date=r.date, 表="TWTCAU") for r in spl.itertuples() if r.sid in SIDS and (r.sid, r.date) not in have]
    return ev, pd.DataFrame(extra)


# ═════════════ 跳動掃描（只報超限旗標）═════════════
def jump_scan(cal, lim):
    rows, cnt = [], {}
    for sid in SIDS:
        st = D.load_stock(sid, "twse", cal)
        c = st.df["close"].to_numpy(float)
        idx = np.flatnonzero(np.isfinite(c))
        L = lim[sid]
        n = 0
        for a, b in zip(idx[:-1], idx[1:]):
            q = c[b] / c[a]
            n += 1
            if q > 1 + L + 0.01 or q < 1 - L - 0.01:
                rows.append({"sid": sid, "前一有成交日": cal[a].date(), "日": cal[b].date(), "間隔交易日": int(b - a),
                             "還原比": q, "當日有還原事件": cal[b] in st.event_dates or any(cal[a] < e <= cal[b] for e in st.event_dates)})
        cnt[sid] = {"比對對數": n, "漲跌幅限制": L, "超限": sum(r["sid"] == sid for r in rows)}
    return pd.DataFrame(rows, columns=["sid", "前一有成交日", "日", "間隔交易日", "還原比", "當日有還原事件"]), cnt


# ═════════════ main 對快照 ═════════════
def main_vs_snapshot():
    out = {}
    head = subprocess.run(["git", "-C", DB_REPO, "rev-parse", "origin/main"], capture_output=True, text=True).stdout.strip()
    out["main_sha"] = head
    for sid in SIDS:
        rec = {}
        for kind in ("stocks", "adj"):
            b = subprocess.run(["git", "-C", DB_REPO, "show", f"origin/main:data/{kind}/{sid}.csv"], capture_output=True).stdout
            snap = open(os.path.join(D.DATA, kind, f"{sid}.csv"), "rb").read()
            if kind == "adj":
                rec["adj_位元相同"] = b == snap
                continue
            from io import BytesIO
            m = pd.read_csv(BytesIO(b), dtype=str).set_index("date")
            s = pd.read_csv(BytesIO(snap), dtype=str).set_index("date")
            cols = ["open", "high", "low", "close", "volume"]
            m1, s1 = m[m.index <= CONF1][cols].fillna(""), s[s.index <= CONF1][cols].fillna("")   # ⚠ 無成交列價格空 ⇒ NaN≠NaN 會假報不同
            rec["窗內列數_main"], rec["窗內列數_快照"] = len(m1), len(s1)
            common = m1.index.intersection(s1.index)
            rec["窗內OHLCV不同列"] = int((m1.loc[common] != s1.loc[common]).any(axis=1).sum())
            rec["只在main"], rec["只在快照"] = int(len(m1.index.difference(s1.index))), int(len(s1.index.difference(m1.index)))
        out[sid] = rec
    return out


# ═════════════ 三、窗 ═════════════
def nth_bar_date(cal, sid, n, mode="own"):
    """第 n 天（1 起算；n ≤ 0 ⇒ 第 1 天）。mode＝"own"：sid 自己的有成交 K 棒；"cal"：從 sid 的 DB 首日起的 TWSE 交易日曆（不管當天有無成交）。"""
    st = D.load_stock(sid, "twse", cal)
    tr = st.df["traded"].to_numpy()
    idx = np.flatnonzero(tr) if mode == "own" else np.arange(int(np.flatnonzero(tr)[0]), len(cal))
    return cal[idx[max(n, 1) - 1]]


def windows(cal, sday):
    # 2015 以前的官方交易日數（STOCK_DAY 列數；⛔ 只數日期）。0050、0052 在 2014-01 已在交易（官方 2014-01 各 18 列）⇒ 到 2015-01-05 早已滿 200 個交易日
    pre2015 = {s: len([x for x in sday.get(s, []) if x[0] < "2015-01-01"]) for s in SIDS}
    for s in ETFS:
        if pre2015[s] > 0:
            pre2015[s] = 10 ** 6                          # 記號：DB 首日即已滿
    list_off = {s: (min(x[0] for x in sday[s] if x[2]) if s in sday else None) for s in SIDS}
    opts = {}
    for key, desc, need, mode in [
            ("b201", "DB 首日起、各檔自己的【有成交 K 棒】第 201 根（前面已有 200 根）", lambda s: MA_N + 1, "own"),
            ("b200", "DB 首日起、各檔自己的【有成交 K 棒】第 200 根", lambda s: MA_N, "own"),
            ("c201", "DB 首日起、TWSE【交易日曆】第 201 天（無成交日也算）", lambda s: MA_N + 1, "cal"),
            ("c200", "DB 首日起、TWSE【交易日曆】第 200 天", lambda s: MA_N, "cal"),
            ("a201", "官方上市日起、TWSE 交易日曆第 201 天（0050、0052 上市早於 2014 ⇒ DB 首日即滿；00631L 2015 以前有 45 個交易日；00685L 上市日＝DB 首日）", lambda s: MA_N + 1 - pre2015[s], "cal"),
            ("a200", "官方上市日起、TWSE 交易日曆第 200 天", lambda s: MA_N - pre2015[s], "cal")]:
        st = {s: nth_bar_date(cal, s, need(s), mode) for s in SIDS}
        opts[key] = {"說明": desc, "各檔": {s: str(st[s].date()) for s in SIDS},
                     "A組（0050、0052、00631L）": str(max(st[s] for s in ("0050", "0052", "00631L")).date()),
                     "B組（四檔含 00685L）": str(max(st.values()).date())}
    ma_first = nth_bar_date(cal, "0050", MA_N + 1)   # t−1 的 0050 200 日線可算的第一個 t（0050 早期無缺日）
    return opts, {s: (v if v < 10 ** 6 else "≥200（2014-01 已在交易）") for s, v in pre2015.items()}, list_off, ma_first


def seg_arith(cal, a, b):
    ia, ib = int(cal.searchsorted(pd.Timestamp(a))), int(cal.searchsorted(pd.Timestamp(b)))
    if str(cal[ia].date()) != a or str(cal[ib].date()) != b:
        raise SystemExit(f"⛔ 段端點不是交易日：{a}～{b} ⇒ {cal[ia].date()}～{cal[ib].date()}")
    s = cal[ia:ib + 1]
    ym = s.to_period("M")
    months = ym.unique()
    full = [p for p in months if s[ym == p][0] == cal[cal.to_period("M") == p][0] and s[ym == p][-1] == cal[cal.to_period("M") == p][-1]]
    yrs = sorted(set(s.year))
    yfirst = [s[s.year == y][0] for y in yrs]
    qfirst = [s[s.to_period("Q") == q][0] for q in s.to_period("Q").unique()]
    # 再平衡日 ＝ 每年／每季第一個交易日，且【不是窗首當天】、【是該年（季）日曆的第一個交易日】
    yreb = [d for d in yfirst if d != s[0] and d == cal[cal.year == d.year][0]]
    qreb = [d for d in qfirst if d != s[0] and d == cal[cal.to_period("Q") == d.to_period("Q")][0]]
    return {"起": a, "迄": b, "交易日": len(s), "年（÷245）": round(len(s) / ANN, 4), "月數（觸及）": len(months),
            "完整月數": len(full), "曆年數（觸及）": len(yrs), "年度再平衡日（不含窗首）": len(yreb),
            "季度再平衡日（不含窗首）": len(qreb), "window_stats≥245日": len(s) >= ANN,
            "年度再平衡日清單": [str(d.date()) for d in yreb]}


# ═════════════ 四、格數 ═════════════
def grid():
    W = [(e, l, 10 - e - l) for e in range(11) for l in range(11 - e)]
    assert len(W) == 66
    q1 = []
    for etf, lev, (e, l, c) in product(ETFS, LEVS, W):
        hold = frozenset((a, w) for a, w in ((etf, e), (lev, l), ("現金", c)) if w > 0)
        q1.append({"問": "問一", "ETF": etf, "正2": lev, "ETF%": e * 10, "正2%": l * 10, "現金%": c * 10, "持有": hold,
                   "窗": "B組起點（含 00685L）" if lev == "00685L" and l > 0 else ("A組起點" if lev == "00631L" or l == 0 else "")})
    q1 = pd.DataFrame(q1)
    q2 = []
    for cond, x, etf, lev in product(("C1 0050>MA200", "C2 0050>MA60", "C3 0050>MA20", "C4 MA50>MA200"), ("X1", "X2", "X3"), ETFS, LEVS):
        on = frozenset({(lev, 10)})
        off = frozenset({("現金", 10)}) if x == "X1" else (frozenset({(etf, 10)}) if x == "X2" else None)
        q2.append({"問": "問二", "條件": cond, "換法": x, "ETF": etf, "正2": lev,
                   "鍵": (cond, x, on, off) if x != "X3" else (cond, x, etf, lev)})
    q2 = pd.DataFrame(q2)
    s = {
        "問一_字面格數": len(q1),
        "問一_不同持有組合": int(q1["持有"].nunique()),
        "問一_重複說明": "ETF%=0 的 11 種在 0050／0052 兩邊相同；正2%=0 的 11 種在 00631L／00685L 兩邊相同；(0,0,100) 四邊相同",
        "問一_ETF%0格": int((q1["ETF%"] == 0).sum()), "問一_正2%0格": int((q1["正2%"] == 0).sum()),
        "問一_純0050格": int(((q1["ETF"] == "0050") & (q1["ETF%"] == 100)).sum()),
        "問一_含00685L持有（正2%>0）格": int(((q1["正2"] == "00685L") & (q1["正2%"] > 0)).sum()),
        "問一_00685L字面格": int((q1["正2"] == "00685L").sum()),
        "問一_季度描述臂字面格": len(q1),
        "問二_字面格數": len(q2),
        "問二_X1不同（ETF 不影響）": int(q2[q2["換法"] == "X1"]["鍵"].nunique()),
        "問二_X2不同": int(q2[q2["換法"] == "X2"]["鍵"].nunique()),
        "問二_X3字面": int((q2["換法"] == "X3").sum()),
        "問二_X3若只跟問一挑中的 ETF／正2": 4,
        "探索段字面總格（主，年度再平衡）": len(q1) + len(q2),
        "確認段判定格": 2, "N_組合": "+2（問一最好比例 1、問二最好轉換 1；探索段 ⛔ 不計 N）",
        "假訊號臂": "問一 1,000 次隨機挑比例、問二 1,000 次打亂轉換日（⛔ 不判、不計 N）",
    }
    s["問二_不同（X3 字面 16）"] = s["問二_X1不同（ETF 不影響）"] + s["問二_X2不同"] + 16
    s["問二_不同（X3 跟問一挑中）"] = s["問二_X1不同（ETF 不影響）"] + s["問二_X2不同"] + 4
    return q1.drop(columns=["持有"]), q2.drop(columns=["鍵"]), s


# ═════════════ main ═════════════
def pre(a):
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, "pre_run.log"), "w").close()
    log(f"===== researchLev2 pre {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）=====")
    RR.use_snapshot()
    log(f"[資料] D.DATA ＝ {D.DATA}（edc6f 快照）")
    cal = D.load_calendar()
    log(f"[日曆] {len(cal)} 根 {cal[0].date()}～{cal[-1].date()}")
    S = {"登錄": "台股策略線 seq1 sha 9a0c5b353e90dd78（PREREG正2現金；裁定 seq216 §一②、seq217）", "快照": RR.SHA}

    # 0050 主窗錨
    w0, w1 = RR.win_bounds(cal)
    bw = RR.bench_row(cal, RR.load_bench(cal), w0, w1 + 1)
    ok = repr(bw["cagr"]) == repr(RR.ANCHOR[0]) and repr(bw["mdd"]) == repr(RR.ANCHOR[1])
    S["閘_0050主窗錨"] = {"錨": list(RR.ANCHOR), "逐位元": ok}
    log(f"[閘] 0050 主窗錨 {RR.ANCHOR} 逐位元 {ok}")
    if not ok:
        raise SystemExit("⛔ 0050 主窗錨不符，停")

    # 官方
    src, exr, spl, sday = read_official(os.path.expanduser(a.official))
    src.to_csv(os.path.join(OUT, "pre_official_src.csv"), index=False, encoding="utf-8")
    pd.concat([exr.assign(表="TWT49U"), spl[spl["sid"].isin(SIDS)].assign(表="TWTCAU")], ignore_index=True) \
        .to_csv(os.path.join(OUT, "pre_official_rows.csv"), index=False, encoding="utf-8")
    S["官方_TWTCAU_全表列數"] = int(len(spl))
    S["官方_TWTCAU_全表"] = spl[["date", "sid", "type", "pre", "ref"]].to_dict("records")
    log(f"[官方] TWT49U 四檔列 {len(exr)}｜TWTCAU 全表 {len(spl)} 列（四檔 {int(spl['sid'].isin(SIDS).sum())}）")

    # 一、資料狀況
    meta = pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str)
    uni = D.load_universe()
    ind = pd.read_csv(os.path.join(D.DATA, "meta", "industry.csv"), dtype=str)
    ind_ids = set(ind.iloc[:, 0])
    seg = {"探索段": ("2015-01-05", EXP_END), "確認段": (CONF0, CONF1)}
    ds, miss = data_status(cal, meta, uni, ind_ids, seg, sday)
    ds.to_csv(os.path.join(OUT, "pre_data.csv"), index=False, encoding="utf-8")
    miss.to_csv(os.path.join(OUT, "pre_missing_days.csv"), index=False, encoding="utf-8")
    for r in ds.to_dict("records"):
        log(f"[資料] {r['sid']} {r['名稱']} {r['資料首日']}～{r['資料末日']} 列 {r['日K列數']}｜區間交易日 {r['區間交易日（日曆）']}｜缺 {r['缺日']}｜adj 事件 {r['adj檔事件數']}")

    ev, extra = events_vs_official(exr, spl, cal)
    ev.to_csv(os.path.join(OUT, "pre_events.csv"), index=False, encoding="utf-8")
    S["事件"] = {"總數": len(ev), "依檔": ev.groupby(["sid", "event"]).size().rename("n").reset_index().to_dict("records"),
               "官方找不到": int(ev["官方來源"].astype(str).str.contains("找到").sum()),
               "官方有資料庫沒有": extra.to_dict("records"),
               "pre不符": int((ev["pre相符"] == False).sum()), "ref不符": int((ev["ref相符"] == False).sum()),  # noqa: E712
               "factor最大絕對差": float(ev["factor_差"].abs().max()), "cum最大絕對差": float(ev["cum_差"].abs().max())}
    log(f"[事件] {S['事件']}")

    lim = {s: 0.1 for s in ETFS}
    lim.update({s: float(ev[(ev["sid"] == s) & (ev["event"] == "etfsplit")]["漲跌幅限制"].iloc[0]) for s in LEVS})
    for s in ETFS:
        v = ev[(ev["sid"] == s) & (ev["event"] == "etfsplit")]["漲跌幅限制"]
        if len(v):
            lim[s] = float(v.iloc[0])
    jumps, jcnt = jump_scan(cal, lim)
    jumps.to_csv(os.path.join(OUT, "pre_jumps.csv"), index=False, encoding="utf-8")
    S["跳動掃描"] = jcnt
    log(f"[跳動] {jcnt}")

    S["main對快照"] = main_vs_snapshot()
    log(f"[main] {S['main對快照']}")

    # 三、窗
    opts, pre2015, list_off, ma_first = windows(cal, sday)
    S["官方首個成交日"] = list_off
    S["2015以前官方成交日數"] = pre2015
    S["0050_t−1的200日線可算的第一個t"] = str(ma_first.date())
    S["起點選項"] = opts
    arith = []
    for key, o in opts.items():
        for grp in ("A組（0050、0052、00631L）", "B組（四檔含 00685L）"):
            st = o[grp]
            for nm, (x, y) in (("探索段", (st, EXP_END)), ("確認段", (CONF0, CONF1))):
                r = seg_arith(cal, x, y)
                arith.append({"起點讀法": key, "組": grp, "段": nm, **{k: v for k, v in r.items() if k != "年度再平衡日清單"},
                              "年度再平衡日清單": "、".join(r["年度再平衡日清單"])})
    ar = pd.DataFrame(arith)
    ar.to_csv(os.path.join(OUT, "pre_windows.csv"), index=False, encoding="utf-8")
    i_e, i_c = int(cal.searchsorted(pd.Timestamp(EXP_END))), int(cal.searchsorted(pd.Timestamp(CONF0)))
    S["探索段末與確認段首相鄰"] = {"探索末": EXP_END, "確認首": CONF0, "中間交易日": i_c - i_e - 1,
                            "2021-12-31是交易日": pd.Timestamp("2021-12-31") in set(cal)}
    log(f"[窗] {json.dumps(opts, ensure_ascii=False)}｜MA200 首日 {ma_first.date()}｜相鄰 {S['探索段末與確認段首相鄰']}")

    # 四、格數
    q1, q2, gs = grid()
    q1.to_csv(os.path.join(OUT, "pre_grid_q1.csv"), index=False, encoding="utf-8")
    q2.to_csv(os.path.join(OUT, "pre_grid_q2.csv"), index=False, encoding="utf-8")
    S["格數"] = gs
    log(f"[格數] {json.dumps(gs, ensure_ascii=False)}")

    with open(os.path.join(OUT, "pre_summary.json"), "w", encoding="utf-8") as f:
        json.dump(S, f, ensure_ascii=False, indent=1, default=str)
    log("[完] pre 段輸出 → resultsLev2/pre_*（⛔ 未讀任何報酬）")


# ═══════════════════════════════════════════════════════════════════════════
# 本體（body）：登錄 seq2（sha 7b67dfa0cc46c389）§七 讀法定案 ＋ 協調者轉達的 R1～R19 落地值
# ═══════════════════════════════════════════════════════════════════════════
"""
    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLev2 body

讀法（⭐ 看結果前寫定；對應 PRE_REPORT §五）：
  R1  共同起點 ＝ TWSE 交易日曆第 201 天：三檔組 2015-11-02；00685L 2018-01-15（描述）
  R2  (d) 00685L 的格只描述、不參加挑選 ⇒ 挑選池 ＝ 正2＝00631L 的 132 格（問一）／16 格（問二）
  R3  00685L 的格（含正2%＝0 那 11 格）一律用 00685L 起點（描述）
  R4  判斷用 t−1 收盤、t 開盤成交；再平衡日同樣在 t 開盤成交；窗首開盤建倉並付一次成本
  R5  成本 ＝ 換手 × 0.385%，換手 ＝ ½ Σ_{各檔＋現金} |目標 − 現有|（＝ 兩邊之間移動的金額，P17.compose 同義）
  R6  描述「現金年 1%」＝ 每個交易日收盤 × 1.01^(1/245)（窗首當天不計息）
  R7  分割因子用 DB 現值（官方參考價 ÷ 前收）
  R8  該成交的那天有任何一檔（現有持股或目標持股 ＞ 0）沒有開盤 ⇒ 整筆延到下一個【全部都有開盤】的日子、用當天的目標；
      0050 停牌期間條件判斷用 ffill 收盤（rerun17.load_bench）
  R9  均線 ＝ 0050 還原收盤（ffill）的簡單均線；C1～C3：bench[t−1] ＞ MA_n[t−1]；C4：MA50[t−1] ＞ MA200[t−1]；嚴格 ＞
  R10 X3 ＝ 問一挑中的 ETF／正2／權重（4 格：C1～C4）；問一照純 0050 ⇒ X3 無定義、不跑
  R11 X1、X2 的「抱正2」＝ 100% 正2；X3 條件成立 ＝ 問一權重、不成立 ＝ 正2 那一份轉現金；三種都在每年第一個交易日再平衡到當時目標
  R12 確認段 2022-01-03 以 1.0 重新起算（均線用之前的歷史）
  R13 0050 同窗基準 ＝ 還原收盤買入持有、不含成本 ＝ research13.window_stats(B/B[a])（主窗錨同式）
  年化／回落：策略權益 ＝ [1.0（窗首開盤前）, 各日收盤市值…]；年化 ＝ (末值)^(245／窗內交易日數) − 1（與 window_stats 同一年數口徑）；
      回落 ＝ 含 1.0 起點的路徑最大回落
  判定（seq141 同式）：條件一 年化 ＞ 0050（嚴格）；條件二 比值 ≥ 0050 比值 ⇒ 合格／另列（只條件一）／不合格
  探索挑法（登錄 §二）：年化 ＞ 同窗 0050 的格中比值最高；R15 同分取正2 比例較低者（問二用窗內平均正2 權重），再同分取表列順序（0050 先於 0052）
  R14 必報「2022」：00631L、00685L 單獨（2022-01-03 開盤買進、付成本）＋ 確認段 2 格；最大跌幅 ＝ 2022 年內路徑（含 1.0 起點）最大回落；
      100 萬剩多少 ＝ 2022-12-30 收盤市值（另報年內谷底）
  R16 假訊號：問一 ⇒ 221 種不同持有組合（pre 段）均勻抽 1,000 次（rng 20260927）；問二 ⇒ 挑中那一格在確認段的逐日狀態，
      保留「成立段」的段數與各段長度，隨機排列段長、再隨機重抽各段起點（段間至少隔 1 日；rng 20260928），1,000 次
  R18 00685L 只加流動性警語（確認段 28 日無成交、171 日成交額 ＜ 100 萬）
  R19 季度再平衡描述臂照跑
"""

COST = 0.00385
CASH_G = 1.01 ** (1 / ANN) - 1
A_START, L85_START = "2015-11-02", "2018-01-15"
SEED_Q1, SEED_Q2, NREP = 20260927, 20260928, 1000
CONDS = ("C1", "C2", "C3", "C4")
COND_TXT = {"C1": "0050＞200日線", "C2": "0050＞60日線", "C3": "0050＞20日線", "C4": "50日線＞200日線"}
X_TXT = {"X1": "不成立全轉現金", "X2": "不成立轉ETF", "X3": "問一比例、不成立時正2那份轉現金"}
WEIGHTS = [(e, l, 10 - e - l) for e in range(11) for l in range(11 - e)]


def load_px(cal):
    O, C = {}, {}
    for s in SIDS:
        st = D.load_stock(s, "twse", cal)
        C[s] = pd.Series(st.df["close"].to_numpy(float)).ffill().to_numpy()
        O[s] = st.df["open"].to_numpy(float)
    return O, C


def seg_idx(cal, a, b):
    i0, i1 = int(cal.searchsorted(pd.Timestamp(a))), int(cal.searchsorted(pd.Timestamp(b)))
    if str(cal[i0].date()) != a or str(cal[i1].date()) != b:
        raise SystemExit(f"⛔ 段端點不是交易日 {a}～{b}")
    return i0, i1


def reb_mask(cal, i0, i1, freq):
    """窗內每年（Y）／每季（Q）第一個交易日；⛔ 窗首當天不算。"""
    s = pd.DatetimeIndex(cal[i0:i1 + 1])
    key = s.year.to_numpy() if freq == "Y" else s.to_period("Q").astype(str).to_numpy()
    out = np.zeros(len(s), bool)
    out[1:] = key[1:] != key[:-1]
    return out


def cond_series(bench):
    """全日曆的 cond[t]（用 t−1 的收盤與均線）；t＝0 為 False。"""
    b = pd.Series(bench)
    ma = {n: b.rolling(n, min_periods=n).mean().to_numpy() for n in (20, 50, 60, 200)}
    out = {}
    for c, x in (("C1", bench > ma[200]), ("C2", bench > ma[60]), ("C3", bench > ma[20]), ("C4", ma[50] > ma[200])):
        x = np.where(np.isfinite(ma[200] if c in ("C1", "C4") else ma[{"C2": 60, "C3": 20}[c]]), x, False)
        y = np.zeros(len(bench), bool)
        y[1:] = x[:-1]
        out[c] = y
    return out


def engine(assets, W, R, i0, O, C, mode="open", init_cost=True, cash_g=0.0, cost=COST):
    """單位制逐日模擬。W：(n,k) 各檔目標權重（現金 ＝ 1 − 和）；R：(n,) 再平衡到期。
    mode＝"open"：t 開盤成交（R8 延後）；"close"：收盤成交、窗首不收成本（只給閘二對 P17.compose 用）。"""
    n, k = W.shape
    o = np.stack([O[a][i0:i0 + n] for a in assets], 1)
    c = np.stack([C[a][i0:i0 + n] for a in assets], 1)
    u = np.zeros(k); cash = 1.0
    eq = np.empty(n); turn = np.zeros(n); cst = np.zeros(n)
    held = np.full((n, k), np.nan); exec_day = np.zeros(n, bool)
    tgt_held = None; pending = True; delay = 0
    with np.errstate(invalid="ignore", divide="ignore"):
        for t in range(n):
            if mode == "open":
                if t > 0 and (R[t] or not np.array_equal(W[t], tgt_held)):
                    pending = True
                if pending:
                    need = (u > 0) | (W[t] > 0)
                    if np.all(np.isfinite(o[t][need])):
                        px = o[t]
                        hold = np.where(u > 0, u * px, 0.0)
                        V = hold.sum() + cash
                        tgt = W[t] * V; tc = (1.0 - W[t].sum()) * V
                        tr = 0.5 * (np.abs(tgt - hold).sum() + abs(tc - cash))
                        cc = tr * cost if (t > 0 or init_cost) else 0.0
                        V2 = V - cc
                        u = np.where(W[t] > 0, W[t] * V2 / px, 0.0)
                        cash = (1.0 - W[t].sum()) * V2
                        turn[t] = tr; cst[t] = cc; exec_day[t] = True
                        tgt_held = W[t].copy(); pending = False
                    else:
                        delay += 1                                # R8：有一檔沒開盤 ⇒ 延後
                if t > 0:
                    cash *= 1.0 + cash_g
                eq[t] = np.where(u > 0, u * c[t], 0.0).sum() + cash
            else:
                if t == 0:
                    u = W[0] / c[0]; cash = 1.0 - W[0].sum(); eq[0] = 1.0; tgt_held = W[0].copy(); exec_day[0] = True
                else:
                    cash *= 1.0 + cash_g
                    hold = u * c[t]
                    v = hold.sum() + cash
                    if R[t]:
                        tgt = W[t] * v; tc = (1.0 - W[t].sum()) * v
                        tr = 0.5 * (np.abs(tgt - hold).sum() + abs(tc - cash))
                        cc = tr * cost; v -= cc
                        u = W[t] * v / c[t]; cash = (1.0 - W[t].sum()) * v
                        turn[t] = tr; cst[t] = cc; exec_day[t] = True
                    eq[t] = v
            held[t] = tgt_held
    return {"eq": eq, "turn": turn, "cst": cst, "held": held, "exec": exec_day, "delay": delay}


def perf(eq):
    n = len(eq)
    cagr = (eq[-1] / 1.0) ** (1 / (n / ANN)) - 1
    path = np.concatenate([[1.0], eq])
    pk = np.maximum.accumulate(path)
    return float(cagr), float(((path - pk) / pk).min())


def bench_perf(bench, i0, i1):
    seg = bench[i0:i1 + 1]
    c, m = R13.window_stats(seg / seg[0], 0, len(seg), 0, len(seg))
    return float(c), float(m)


def ratio(c, m):
    """年化 ÷ |回落|；回落 ＝ 0（全現金）⇒ NaN（不可能 ＞ 0050）。"""
    return c / abs(m) if m < 0 else float("nan")


def label(c, m, c50, m50):
    k1 = c > c50; k2 = ratio(c, m) >= ratio(c50, m50)
    return "合格" if (k1 and k2) else ("另列" if k1 else "不合格")


def q1_W(e, l, n):
    return np.tile([e / 10, l / 10], (n, 1))


def q2_W(x, on, n, w13=None):
    """x∈X1/X2/X3；on：(n,) bool；assets：X1 (lev,)；X2 (etf, lev)；X3 (etf, lev)。"""
    if x == "X1":
        return on.astype(float)[:, None]
    if x == "X2":
        return np.stack([(~on).astype(float), on.astype(float)], 1)
    e, l = w13
    return np.stack([np.full(n, e / 10), np.where(on, l / 10, 0.0)], 1)


def q2_assets(x, etf, lev):
    return (lev,) if x == "X1" else (etf, lev)


def sel_pick(df, c50, key_lev):
    """登錄 §二 挑法：年化 ＞ 0050 的格中比值最高；同分取正2 比例較低者，再同分取表列順序。"""
    ok = df[df["年化"] > c50].copy()
    if ok.empty:
        return None, 0
    ok["_o"] = range(len(ok))
    ok = ok.sort_values(["比值", key_lev, "_o"], ascending=[False, True, True])
    return ok.iloc[0], len(ok)


def q2_desc(r, on_w, bench, i0):
    """每年換幾次、成本、錯過的漲幅（正2 那份不在場的日子，0050 收盤對收盤累積）。"""
    held = r["held"]; n = len(held)
    is_on = np.array([np.array_equal(h, on_w) for h in held])
    sw = int(sum(1 for t in range(1, n) if r["exec"][t] and is_on[t] != is_on[t - 1]))
    br = bench[i0 + 1:i0 + n] / bench[i0:i0 + n - 1]
    off = ~is_on[1:]
    return {"轉換次數": sw, "每年轉換": sw / (n / ANN), "成本合計": float(r["cst"].sum()),
            "正2不在場日數": int((~is_on).sum()), "不在場期間0050累積": float(np.prod(br[off]) - 1) if off.any() else 0.0}


def body(a):
    os.makedirs(OUT, exist_ok=True)
    global LOGF
    LOGF = "body_run.log"; open(os.path.join(OUT, LOGF), "w").close()
    log(f"===== researchLev2 body {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）=====")
    RR.use_snapshot()
    cal = D.load_calendar()
    bench = RR.load_bench(cal)
    O, C = load_px(cal)
    S = {"登錄": "PREREG正2現金 seq2 sha 7b67dfa0cc46c389", "快照": RR.SHA, "閘": {}}

    # ── 閘一 0050 錨
    w0, w1 = RR.win_bounds(cal)
    bw = RR.bench_row(cal, bench, w0, w1 + 1)
    g1 = repr(bw["cagr"]) == repr(RR.ANCHOR[0]) and repr(bw["mdd"]) == repr(RR.ANCHOR[1])
    S["閘"]["一_0050錨逐位元"] = g1
    log(f"[閘一] 0050 主窗錨逐位元 {g1}")
    if not g1:
        raise SystemExit("⛔ 閘一不過")

    A = {"探索": seg_idx(cal, A_START, EXP_END), "確認": seg_idx(cal, CONF0, CONF1)}
    L = {"探索": seg_idx(cal, L85_START, EXP_END), "確認": A["確認"]}
    B50 = {("A", k): bench_perf(bench, *v) for k, v in A.items()}
    B50[("L", "探索")] = bench_perf(bench, *L["探索"])
    B50[("L", "確認")] = B50[("A", "確認")]
    S["0050同窗"] = {f"{g}_{k}": {"年化": v[0], "回落": v[1], "比值": v[0] / abs(v[1])} for (g, k), v in B50.items()}
    log(f"[0050] {S['0050同窗']}")
    cond = cond_series(bench)

    # ── 閘二：收盤成交模式 ＝ P17.compose（兩格：ETF＋正2、正2＋現金）
    from . import researchp17 as P17
    g2 = {}
    i0, i1 = A["探索"]; n = i1 - i0 + 1; Ry = reb_mask(cal, i0, i1, "Y")
    for nm, (assets, w) in {"0050 50%＋00631L 50%": (("0050", "00631L"), (5, 5)), "00631L 30%＋現金 70%": (("00631L",), (3,))}.items():
        W = np.tile([x / 10 for x in w], (n, 1))
        r = engine(assets, W, Ry, i0, O, C, mode="close", init_cost=False)
        E = C["00631L"][i0:i1 + 1]
        Bm = C["0050"][i0:i1 + 1] if len(assets) == 2 else np.ones(n)
        wl = w[1] / 10 if len(assets) == 2 else w[0] / 10
        V, _, _ = P17.compose(E / E[0], Bm / Bm[0], np.full(n, wl), Ry, cost=COST)
        g2[nm] = float(np.max(np.abs(r["eq"] / V - 1)))
    S["閘"]["二_對P17compose最大相對差"] = g2
    log(f"[閘二] {g2}")
    if max(g2.values()) > 1e-12:
        raise SystemExit("⛔ 閘二不過")

    # ── 問一：全部格 × 兩段（00631L 用三檔組窗、00685L 用 00685L 窗）
    rows = []
    for etf, lev, (e, l, cc) in product(ETFS, LEVS, WEIGHTS):
        grp = "A" if lev == "00631L" else "L"
        for seg in ("探索", "確認"):
            i0, i1 = (A if grp == "A" else L)[seg]; n = i1 - i0 + 1
            r = engine((etf, lev), q1_W(e, l, n), reb_mask(cal, i0, i1, "Y"), i0, O, C)
            c_, m_ = perf(r["eq"]); c50, m50 = B50[(grp, seg)]
            rows.append({"段": seg, "組": "挑選池" if grp == "A" else "00685L描述", "ETF": etf, "正2": lev, "ETF%": e * 10, "正2%": l * 10,
                         "現金%": cc * 10, "年化": c_, "回落": m_, "比值": ratio(c_, m_), "成本合計": float(r["cst"].sum()), "R8延後日數": r["delay"],
                         "年化>0050": c_ > c50, "標籤": label(c_, m_, c50, m50)})
    q1 = pd.DataFrame(rows)
    q1.to_csv(os.path.join(OUT, "body_q1.csv"), index=False, encoding="utf-8")
    pool1 = q1[(q1["段"] == "探索") & (q1["組"] == "挑選池")].reset_index(drop=True)
    pick1, n_beat1 = sel_pick(pool1, B50[("A", "探索")][0], "正2%")
    S["問一_探索"] = {"挑選池格數": len(pool1), "年化>0050格數": n_beat1,
                    "挑中": None if pick1 is None else {k: pick1[k] for k in ("ETF", "正2", "ETF%", "正2%", "現金%", "年化", "回落", "比值")}}
    log(f"[問一探索] 池 {len(pool1)}｜年化＞0050 {n_beat1}｜挑中 {S['問一_探索']['挑中']}")

    # ── 問二
    w13 = None if pick1 is None or pick1["正2%"] == 0 else (int(pick1["ETF%"] // 10), int(pick1["正2%"] // 10))
    rows2, runs2 = [], {}
    for cd, x, etf, lev in product(CONDS, ("X1", "X2", "X3"), ETFS, LEVS):
        if x == "X1" and etf != "0050":
            continue                                             # X1 用不到 ETF ⇒ 只留一份
        if x == "X3":
            if w13 is None or etf != pick1["ETF"]:
                continue                                         # R10：只跟問一挑中的 ETF
            if lev != pick1["正2"] and lev != "00685L":
                continue
        grp = "A" if lev == "00631L" else "L"
        for seg in ("探索", "確認"):
            i0, i1 = (A if grp == "A" else L)[seg]; n = i1 - i0 + 1
            on = cond[cd][i0:i1 + 1]
            W = q2_W(x, on, n, w13)
            r = engine(q2_assets(x, etf, lev), W, reb_mask(cal, i0, i1, "Y"), i0, O, C)
            c_, m_ = perf(r["eq"]); c50, m50 = B50[(grp, seg)]
            on_w = W[on][0] if on.any() else q2_W(x, np.ones(1, bool), 1, w13)[0]
            lev_col = list(q2_assets(x, etf, lev)).index(lev)
            d = q2_desc(r, on_w, bench, i0)
            rows2.append({"段": seg, "組": "挑選池" if grp == "A" else "00685L描述", "條件": cd, "換法": x,
                          "ETF": "—" if x == "X1" else etf, "正2": lev, "年化": c_, "回落": m_, "比值": ratio(c_, m_),
                          "平均正2權重": float(np.nanmean(r["held"][:, lev_col])), "條件成立占比": float(on.mean()), "R8延後日數": r["delay"],
                          "年化>0050": c_ > c50, "標籤": label(c_, m_, c50, m50), **d})
            runs2[(seg, cd, x, etf, lev)] = (r, on)
    q2 = pd.DataFrame(rows2)
    q2.to_csv(os.path.join(OUT, "body_q2.csv"), index=False, encoding="utf-8")
    pool2 = q2[(q2["段"] == "探索") & (q2["組"] == "挑選池")].reset_index(drop=True)
    pick2, n_beat2 = sel_pick(pool2, B50[("A", "探索")][0], "平均正2權重")
    S["問二_探索"] = {"挑選池格數": len(pool2), "年化>0050格數": n_beat2,
                    "挑中": None if pick2 is None else {k: pick2[k] for k in ("條件", "換法", "ETF", "正2", "年化", "回落", "比值", "平均正2權重", "每年轉換")}}
    log(f"[問二探索] 池 {len(pool2)}｜年化＞0050 {n_beat2}｜挑中 {S['問二_探索']['挑中']}")

    # ── ⚠ 問一挑中的正2%＝0 ⇒ X3 無定義（主：不進池）；敏感度：X3 照字面跑（權重與問一相同、條件不影響）再挑一次
    if pick1 is not None and w13 is None:
        e3 = int(pick1["ETF%"] // 10); alt = []
        for cd in CONDS:
            for seg in ("探索", "確認"):
                i0, i1 = A[seg]; n = i1 - i0 + 1
                r = engine((pick1["ETF"], "00631L"), q2_W("X3", cond[cd][i0:i1 + 1], n, (e3, 0)), reb_mask(cal, i0, i1, "Y"), i0, O, C)
                c_, m_ = perf(r["eq"]); c50, m50 = B50[("A", seg)]
                alt.append({"段": seg, "組": "挑選池", "條件": cd, "換法": "X3", "ETF": pick1["ETF"], "正2": "00631L", "年化": c_, "回落": m_,
                            "比值": ratio(c_, m_), "平均正2權重": 0.0, "年化>0050": c_ > c50, "標籤": label(c_, m_, c50, m50)})
        alt = pd.DataFrame(alt)
        alt.to_csv(os.path.join(OUT, "body_q2_x3_sensitivity.csv"), index=False, encoding="utf-8")
        pa, nb = sel_pick(pd.concat([pool2, alt[alt["段"] == "探索"]], ignore_index=True), B50[("A", "探索")][0], "平均正2權重")
        ca = alt[(alt["段"] == "確認") & (alt["條件"] == pa["條件"])] if pa["換法"] == "X3" else q2[(q2["段"] == "確認") & (q2["條件"] == pa["條件"]) & (q2["換法"] == pa["換法"]) & (q2["ETF"] == pa["ETF"]) & (q2["正2"] == pa["正2"])]
        S["敏感度_X3照字面"] = {"說明": "問一挑中正2%＝0 ⇒ X3 四格＝問一格本身（條件不影響持有）；主讀法不進問二池",
                             "池": len(pool2) + 4, "挑中": {k: pa[k] for k in ("條件", "換法", "ETF", "年化", "回落", "比值")},
                             "確認段": {k: ca.iloc[0][k] for k in ("年化", "回落", "比值", "標籤")}}
        log(f"[敏感度 X3] {S['敏感度_X3照字面']}")
    # 描述：限「正2%＞0」的格照同一挑法（⛔ 不判）
    pl = pool1[pool1["正2%"] > 0].reset_index(drop=True)
    pp, npp = sel_pick(pl, B50[("A", "探索")][0], "正2%")
    if pp is not None:
        pc = q1[(q1["段"] == "確認") & (q1["ETF"] == pp["ETF"]) & (q1["正2"] == pp["正2"]) & (q1["ETF%"] == pp["ETF%"]) & (q1["正2%"] == pp["正2%"])].iloc[0]
        S["描述_限正2大於0"] = {"池": len(pl), "年化>0050": npp, "挑中": {k: pp[k] for k in ("ETF", "ETF%", "正2%", "現金%", "年化", "回落", "比值")},
                           "確認段（描述）": {k: pc[k] for k in ("年化", "回落", "比值", "標籤")}}
        log(f"[描述 限正2>0] {S['描述_限正2大於0']}")

    # ── 確認段 2 格判定
    c50c, m50c = B50[("A", "確認")]
    conf = {}
    if pick1 is not None:
        r1 = q1[(q1["段"] == "確認") & (q1["ETF"] == pick1["ETF"]) & (q1["正2"] == pick1["正2"]) & (q1["ETF%"] == pick1["ETF%"]) & (q1["正2%"] == pick1["正2%"])].iloc[0]
        conf["問一"] = {"格": f"{pick1['ETF']} {pick1['ETF%']}%＋{pick1['正2']} {pick1['正2%']}%＋現金 {pick1['現金%']}%（每年再平衡）",
                       "年化": r1["年化"], "回落": r1["回落"], "比值": r1["比值"], "標籤": r1["標籤"]}
    if pick2 is not None:
        etf2 = pick2["ETF"] if pick2["換法"] != "X1" else "0050"
        r2 = q2[(q2["段"] == "確認") & (q2["條件"] == pick2["條件"]) & (q2["換法"] == pick2["換法"]) & (q2["ETF"] == pick2["ETF"]) & (q2["正2"] == pick2["正2"])].iloc[0]
        conf["問二"] = {"格": f"{pick2['條件']}（{COND_TXT[pick2['條件']]}）× {pick2['換法']}（{X_TXT[pick2['換法']]}）× ETF {pick2['ETF']} × {pick2['正2']}",
                       "年化": r2["年化"], "回落": r2["回落"], "比值": r2["比值"], "標籤": r2["標籤"], "每年轉換": r2["每年轉換"]}
    S["確認段"] = {"0050": {"年化": c50c, "回落": m50c, "比值": c50c / abs(m50c)}, **conf}
    log(f"[確認] {S['確認段']}")

    # ── 假訊號臂
    q1c = q1[q1["段"] == "確認"].copy()
    q1c["持有"] = [tuple(sorted((a_, w_) for a_, w_ in ((r.ETF, r["ETF%"]), (r.正2, r["正2%"])) if w_ > 0)) for _, r in q1c.iterrows()]
    uniq = q1c.drop_duplicates("持有").reset_index(drop=True)
    if len(uniq) != 221:
        raise SystemExit(f"⛔ 不同持有組合 {len(uniq)} ≠ 221")
    # ⚠ 00685L 組合在確認段與 00631L 同窗（2022-01-03 起），可直接比
    rng = np.random.default_rng(SEED_Q1)
    draws = rng.integers(0, len(uniq), NREP)
    lab1 = uniq["標籤"].to_numpy()[draws]
    p1 = float(np.mean(lab1 == "合格"))
    pool121 = uniq[uniq["正2"].eq("00631L") | uniq["正2%"].eq(0)]
    S["假訊號_問一"] = {"抽樣母體": len(uniq), "p_合格": p1, "p_另列": float(np.mean(lab1 == "另列")),
                     "母體精確合格比例": float(np.mean(uniq["標籤"] == "合格")),
                     "參考_只含00631L或不含正2的組合": {"數": len(pool121), "合格比例": float(np.mean(pool121["標籤"] == "合格"))}}
    pd.DataFrame({"draw": range(NREP), "組合列": draws, "標籤": lab1}).to_csv(os.path.join(OUT, "body_null_q1.csv"), index=False, encoding="utf-8")
    log(f"[假訊號一] {S['假訊號_問一']}")

    if pick2 is not None:
        i0, i1 = A["確認"]; n = i1 - i0 + 1
        on0 = cond[pick2["條件"]][i0:i1 + 1]
        runs = []; t = 0
        while t < n:
            if on0[t]:
                s_ = t
                while t < n and on0[t]:
                    t += 1
                runs.append(t - s_)
            else:
                t += 1
        k = len(runs); F = n - sum(runs)
        rng2 = np.random.default_rng(SEED_Q2)
        states = np.zeros((NREP, n), bool); labs2 = []
        etf2 = pick2["ETF"] if pick2["換法"] != "X1" else "0050"
        for j in range(NREP):
            ln = rng2.permutation(runs)
            extra = F - max(k - 1, 0)
            cuts = np.sort(rng2.integers(0, extra + 1, k))          # k 個切點 ⇒ k+1 個間隔（含頭尾），內部間隔再 +1
            gaps = np.diff(np.concatenate([[0], cuts, [extra]]))
            st_ = np.zeros(n, bool); pos = gaps[0]
            for q in range(k):
                st_[pos:pos + ln[q]] = True
                pos += ln[q] + gaps[q + 1] + (1 if q < k - 1 else 0)
            if st_.sum() != sum(runs):
                raise SystemExit("⛔ 打亂後成立日數不等")
            states[j] = st_
            r = engine(q2_assets(pick2["換法"], etf2, pick2["正2"]), q2_W(pick2["換法"], st_, n, w13), reb_mask(cal, i0, i1, "Y"), i0, O, C)
            c_, m_ = perf(r["eq"]); labs2.append(label(c_, m_, c50c, m50c))
        labs2 = np.array(labs2)
        np.savez_compressed(os.path.join(OUT, "body_null_q2_states.npz"), states=np.packbits(states, axis=1), n=n)
        pd.DataFrame({"draw": range(NREP), "標籤": labs2}).to_csv(os.path.join(OUT, "body_null_q2.csv"), index=False, encoding="utf-8")
        S["假訊號_問二"] = {"成立段數": k, "成立日數": int(sum(runs)), "確認段日數": n, "p_合格": float(np.mean(labs2 == "合格")),
                         "p_另列": float(np.mean(labs2 == "另列"))}
        log(f"[假訊號二] {S['假訊號_問二']}")

    # ── 必報：2022
    i0, i1 = A["確認"]; y0, y1 = seg_idx(cal, "2022-01-03", "2022-12-30"); ny = y1 - y0 + 1
    rep = []

    def y22(nm, eq):
        path = np.concatenate([[1.0], eq[:ny]]); pk = np.maximum.accumulate(path)
        rep.append({"對象": nm, "2022年內最大回落": float(((path - pk) / pk).min()), "100萬到2022-12-30": float(eq[ny - 1] * 1e6),
                    "100萬年內谷底": float(path.min() * 1e6), "谷底日": str(cal[y0 + int(np.argmin(path)) - 1].date()) if np.argmin(path) > 0 else "起點"})
    for lev in LEVS:
        r = engine((lev,), np.ones((ny, 1)), np.zeros(ny, bool), y0, O, C)
        y22(f"{lev} 單獨（2022-01-03 開盤買進、付成本）", r["eq"])
    seg = bench[y0:y1 + 1] / bench[y0]
    y22("0050 參照（還原收盤買入持有、不含成本；以 2022-01-03 收盤為 1）", seg)
    if pick1 is not None:
        n = i1 - i0 + 1
        r = engine((pick1["ETF"], pick1["正2"]), q1_W(int(pick1["ETF%"] // 10), int(pick1["正2%"] // 10), n), reb_mask(cal, i0, i1, "Y"), i0, O, C)
        y22("確認段 問一格", r["eq"])
    if pick2 is not None:
        r, _ = runs2[("確認", pick2["條件"], pick2["換法"], pick2["ETF"] if pick2["換法"] != "X1" else "0050", pick2["正2"])]
        y22("確認段 問二格", r["eq"])
    pd.DataFrame(rep).to_csv(os.path.join(OUT, "body_2022.csv"), index=False, encoding="utf-8")
    S["必報_2022"] = rep
    log(f"[2022] {rep}")

    # ── 描述臂：現金 1%、季度再平衡、00685L 格
    desc = []
    for seg in ("探索", "確認"):
        i0, i1 = A[seg]; n = i1 - i0 + 1; c50, m50 = B50[("A", seg)]
        if pick1 is not None:
            e, l = int(pick1["ETF%"] // 10), int(pick1["正2%"] // 10)
            for nm, R_, cg in (("問一格｜現金年1%", reb_mask(cal, i0, i1, "Y"), CASH_G), ("問一格｜季度再平衡", reb_mask(cal, i0, i1, "Q"), 0.0)):
                r = engine((pick1["ETF"], pick1["正2"]), q1_W(e, l, n), R_, i0, O, C, cash_g=cg)
                c_, m_ = perf(r["eq"]); desc.append({"段": seg, "臂": nm, "年化": c_, "回落": m_, "比值": ratio(c_, m_), "對0050（描述）": label(c_, m_, c50, m50)})
        if pick2 is not None:
            etf2 = pick2["ETF"] if pick2["換法"] != "X1" else "0050"
            on = cond[pick2["條件"]][i0:i1 + 1]
            r = engine(q2_assets(pick2["換法"], etf2, pick2["正2"]), q2_W(pick2["換法"], on, n, w13), reb_mask(cal, i0, i1, "Y"), i0, O, C, cash_g=CASH_G)
            c_, m_ = perf(r["eq"]); desc.append({"段": seg, "臂": "問二格｜現金年1%", "年化": c_, "回落": m_, "比值": ratio(c_, m_), "對0050（描述）": label(c_, m_, c50, m50)})
    # 季度版全池挑選（描述）
    qq = []
    i0, i1 = A["探索"]; n = i1 - i0 + 1
    for etf, (e, l, cc) in product(ETFS, WEIGHTS):
        r = engine((etf, "00631L"), q1_W(e, l, n), reb_mask(cal, i0, i1, "Q"), i0, O, C)
        c_, m_ = perf(r["eq"]); qq.append({"ETF": etf, "正2": "00631L", "ETF%": e * 10, "正2%": l * 10, "現金%": cc * 10, "年化": c_, "回落": m_, "比值": ratio(c_, m_)})
    qq = pd.DataFrame(qq); qpick, _ = sel_pick(qq, B50[("A", "探索")][0], "正2%")
    S["描述_季度版探索挑中"] = None if qpick is None else {k: qpick[k] for k in ("ETF", "ETF%", "正2%", "現金%", "年化", "回落", "比值")}
    # 00685L（描述）：同一挑法在 00685L 窗會挑中什麼、確認段標籤
    l1 = q1[(q1["段"] == "探索") & (q1["組"] == "00685L描述")].reset_index(drop=True)
    lp1, lnb1 = sel_pick(l1, B50[("L", "探索")][0], "正2%")
    l2 = q2[(q2["段"] == "探索") & (q2["組"] == "00685L描述")].reset_index(drop=True)
    lp2, lnb2 = sel_pick(l2, B50[("L", "探索")][0], "平均正2權重")

    def conf_of(df, p, keys):
        if p is None:
            return None
        m = df["段"] == "確認"
        for k_ in keys:
            m &= df[k_] == p[k_]
        return df[m].iloc[0]
    lc1 = conf_of(q1, lp1, ["ETF", "正2", "ETF%", "正2%"]); lc2 = conf_of(q2, lp2, ["條件", "換法", "ETF", "正2"])
    S["描述_00685L"] = {"窗": f"{L85_START}～{EXP_END}（探索）", "0050同窗探索": S["0050同窗"]["L_探索"],
                       "問一挑中": None if lp1 is None else {k: lp1[k] for k in ("ETF", "ETF%", "正2%", "現金%", "年化", "回落", "比值")},
                       "問一確認段": None if lc1 is None else {k: lc1[k] for k in ("年化", "回落", "比值", "標籤")},
                       "問二挑中": None if lp2 is None else {k: lp2[k] for k in ("條件", "換法", "ETF", "年化", "回落", "比值")},
                       "問二確認段": None if lc2 is None else {k: lc2[k] for k in ("年化", "回落", "比值", "標籤")}}
    pd.DataFrame(desc).to_csv(os.path.join(OUT, "body_desc.csv"), index=False, encoding="utf-8")
    qq.to_csv(os.path.join(OUT, "body_q1_quarterly_explore.csv"), index=False, encoding="utf-8")
    S["描述"] = desc
    log(f"[描述] {desc}｜季度挑中 {S['描述_季度版探索挑中']}｜00685L {S['描述_00685L']}")

    with open(os.path.join(OUT, "body_summary.json"), "w", encoding="utf-8") as f:
        json.dump(S, f, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    log("[完] body")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["pre", "body"])
    ap.add_argument("--official", default="~/lev2_official")
    a = ap.parse_args()
    pre(a) if a.stage == "pre" else body(a)


if __name__ == "__main__":
    main()
