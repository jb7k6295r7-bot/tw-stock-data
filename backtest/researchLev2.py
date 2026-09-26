# -*- coding: utf-8 -*-
"""PREREG正2現金（台股策略線登錄 seq1 sha 9a0c5b353e90dd78；裁定 seq216 §一② 附則、seq217）—— pre 段：資料檢查與結構。

⛔ pre 段【不讀報酬】：不算任何組合、任何單檔的年化／回落／區間報酬。
   唯一例外 ＝ 0050 主窗錨（rerun17 既有釘死值）的逐位元重現 ⇒ 只報「逐位元 True／False」與錨值本身。
   跳動掃描只報【超出漲跌幅限制】的旗標列（資料錯誤），⛔ 不報任何分佈。
⛔ 不改任何既有 .py；資料一律讀 rerun17.use_snapshot()（edc6f8002f 快照），main 只用 git show 對照。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLev2 pre --official ~/lev2_official

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


def log(msg):
    print(msg, flush=True)
    with open(os.path.join(OUT, "pre_run.log"), "a", encoding="utf-8") as f:
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["pre"])
    ap.add_argument("--official", default="~/lev2_official")
    a = ap.parse_args()
    pre(a)


if __name__ == "__main__":
    main()
