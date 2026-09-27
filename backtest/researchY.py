# -*- coding: utf-8 -*-
"""PREREGY（大盤驅動因素加減碼，單筆層）pre 段：頻率與事件旗標（回測線，2026-09-27）。

⛔ 本段不讀、不印、不存任何報酬；⛔ 不印、不存任何因素值（主窗與早年都不存，只存事件旗標與事件日）。
   唯一例外是閘：主窗 0050 錨（已釘死、登錄聲明已看過的基準）逐位元比對；#9 prev 對 balance 的主庫樹相對差（資料庫 2312 同一組量）。

依據（逐字出處見 PRE_REPORT.md §〇）：
  登錄  PREREGY seq3（sha 60037805794e016c）§一 九項定義、§二 量法、§三 資料處理、§四 16 格、§九 #9 讀法
  裁定  seq154 §二（H 只輸出閘門狀態）、§四（門檻寫死法）；seq159 §二（編號、§三② 比照 H）；seq222 ①（再確認）；seq216 收下 #9 讀法
  出口  PREREGH1 seq2 §五（n_eff < 30 ⇒ 出口①；30～99 ⇒ 出口②；≥ 100 ⇒ 出口③）
  資料  資料庫線 1509、1542（附件 央行 54 次調整 sha18a7e036eb15f3c6）、1545、1639、0822、2312、0347

    python -m backtest.researchY pre
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import io
import json
import os
import subprocess
import tarfile
import time
from statistics import NormalDist

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsY")
DB_REPO = os.path.expanduser("~/tw-stock-data")
US_REPO = os.path.expanduser("~/us-stock-data")
DB_SHA = "3edc0e2206463bf7df0b47e87039db139f776bf3"     # data/early（M1～M5 到齊）＋ universe/instamt、marginmkt；⊇ 483792f6af、189c187cb5、c7a1b4b9c8
US_SHA = "591624c722486fd533359beac3a1583016d88756"     # us-stock-data main（data/macro）
YD = os.path.expanduser(f"~/ydata/{DB_SHA[:10]}")
EXTRACT = ["data/early/daily", "data/early/instamt", "data/early/marginmkt", "data/early/exright", "data/early/_structure.csv",
           "data/extra", "data/universe/instamt", "data/universe/marginmkt", "data/meta/calendar_twse.csv"]
CBC_ATTACH = "附件-央行重貼現率54次調整對決議公布日_資料庫線_sha18a7e036eb15f3c6-1398B-20260925-1542.csv"
MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"

W0, W1 = "2017-03-02", "2026-08-24"            # 登錄 §三③
WIN_DAYS = 2313
E0, E1 = "2008-01-01", "2014-12-31"            # 登錄 §五：驗收段 2008-01～2014-12（本段只報旗標）
ROLL, CHG, DEDUP, HOLD, HOLD_DESC = 756, 20, 20, 20, 60
N_CELLS = 16
ALPHA = 0.05
ETF757_FIRST = "2018-12-06"                     # edc6f 快照 stocks/00757.csv 首列（程式內再讀一次驗）
CBC_EXCLUDE = "2004-12-13"                      # 登錄 §一 #5：公布日不明 ⇒ 剔除

LOG: list[str] = []


def log(s: str):
    LOG.append(s)
    print(s, flush=True)


# ═════════════ 取資料（唯讀：git archive／git show）═════════════
def extract_db():
    done = os.path.join(YD, "done.json")
    if os.path.exists(done):
        m = json.load(open(done, encoding="utf-8"))
        if m.get("sha") == DB_SHA and m.get("paths") == EXTRACT:
            return m
    full = subprocess.run(["git", "-C", DB_REPO, "rev-parse", DB_SHA], capture_output=True, text=True, check=True).stdout.strip()
    assert full == DB_SHA
    os.makedirs(YD, exist_ok=True)
    p = subprocess.run(["git", "-C", DB_REPO, "archive", "--format=tar", DB_SHA] + EXTRACT, capture_output=True, check=True)
    with tarfile.open(fileobj=io.BytesIO(p.stdout)) as tf:
        tf.extractall(YD)
    m = {"sha": DB_SHA, "paths": EXTRACT, "tar_sha256": hashlib.sha256(p.stdout).hexdigest()}
    json.dump(m, open(done, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return m


def us_csv(name: str) -> pd.DataFrame:
    txt = subprocess.run(["git", "-C", US_REPO, "show", f"{US_SHA}:data/macro/{name}"], capture_output=True, check=True).stdout
    return pd.read_csv(io.BytesIO(txt), dtype=str, keep_default_na=False)


def us_manifest() -> dict:
    m = us_csv("_manifest.csv")
    return {r["series"]: {"rows": r["rows"], "first": r["first"], "last": r["last"], "sha256[:16]": r["sha256"][:16]} for _, r in m.iterrows()}


def fnum(s: pd.Series) -> np.ndarray:
    return pd.to_numeric(s.astype(str).str.replace(",", "", regex=False).replace({"": None, ".": None}), errors="coerce").to_numpy(float)


# ═════════════ 台北交易日曆 ═════════════
def tw_calendar():
    """早年（_structure twse rows>0，≤2014-12-31）＋ 主庫（edc6f 快照 calendar_twse）。"""
    st = pd.read_csv(os.path.join(YD, "data/early/_structure.csv"), dtype=str)
    early = sorted(st.loc[(st["market"] == "twse") & (pd.to_numeric(st["rows"]) > 0), "date"].tolist())
    from . import rerun17 as RR
    from . import data as D
    RR.use_snapshot()
    calm = [str(d.date()) for d in D.load_calendar()]
    cal3 = pd.read_csv(os.path.join(YD, "data/meta/calendar_twse.csv"), dtype=str)["date"].tolist()
    g = {"早年日曆天數": len(early), "早年起訖": [early[0], early[-1]], "主庫日曆(edc6f)天數": len(calm), "主庫起訖": [calm[0], calm[-1]],
         "edc6f 與 3edc0e2206 日曆在 ≤2026-08-24 相同": [d for d in calm if d <= W1] == [d for d in cal3 if d <= W1],
         "早年末日→主庫首日": [early[-1], calm[0]]}
    assert early[-1] <= "2014-12-31" < calm[0]
    cal = early + [d for d in cal3 if d > early[-1]] if len(cal3) >= len(calm) else early + calm
    pos = {d: i for i, d in enumerate(cal)}
    w0, w1 = pos[W0], pos[W1]
    g["合併日曆天數"] = len(cal)
    g["合併日曆末日"] = cal[-1]
    g["主窗天數"] = w1 - w0 + 1
    g["過"] = bool(g["edc6f 與 3edc0e2206 日曆在 ≤2026-08-24 相同"] and g["主窗天數"] == WIN_DAYS)
    return cal, pos, g


def next_tw(cal_arr: np.ndarray, dates: np.ndarray, strict: bool) -> np.ndarray:
    """每個日期之後（strict）／當日或之後的第一個台北交易日位置；超出 ⇒ −1。"""
    idx = np.searchsorted(cal_arr, dates, side="right" if strict else "left")
    idx[idx >= len(cal_arr)] = -1
    return idx


# ═════════════ 因素原始序列（⛔ 值只在記憶體；不印不存）═════════════
def load_instamt(cal):
    rows = []
    for tree in ("early", "universe"):
        for f in sorted(glob.glob(os.path.join(YD, f"data/{tree}/instamt/*.csv"))):
            rows.append(pd.read_csv(f, dtype=str, keep_default_na=False))
    df = pd.concat(rows, ignore_index=True)
    df["net"] = fnum(df["net"])
    names = df.groupby("investor")["date"].agg(["min", "max", "count"]).reset_index()
    piv = df.pivot_table(index="date", columns="investor", values="net", aggfunc="sum")
    dates = piv.index.tolist()
    single = piv["外資"].combine_first(piv["外資及陸資"])
    ex = piv["外資及陸資(不含外資自營商)"]
    fd = piv["外資自營商"]
    fa = single.combine_first(ex + fd)            # Fa：2017-12-18 起 兩列相加（READ_CONTRACT foreign；資料庫 1545）
    fb = single.combine_first(ex)                 # Fb：2017-12-18 起 只取「外資及陸資(不含外資自營商)」
    dset = set(dates)
    audit = {"investor 名稱與起訖（筆數）": {r["investor"]: [r["min"], r["max"], int(r["count"])] for _, r in names.iterrows()},
             "天數": len(dates), "起訖": [dates[0], dates[-1]],
             "每天恰有一個外資口徑（單列 xor 拆列）": int(((single.notna()) ^ (ex.notna())).sum()) == len(dates),
             "外資值缺（Fa）": int(fa.isna().sum()), "外資值缺（Fb）": int(fb.isna().sum()),
             "日期⊆台北日曆": all(d in set(cal) for d in dates),
             "台北日曆在起訖內但無檔天數": int(sum(1 for d in cal if dates[0] <= d <= dates[-1] and d not in dset)),
             "「外資自營商」列 net 非 0 天數": int((fd.fillna(0) != 0).sum()), "Fa ≠ Fb 天數": int((fa != fb).sum())}
    return {"a": pd.Series(fa.to_numpy(float), index=dates), "b": pd.Series(fb.to_numpy(float), index=dates)}, audit


def load_marginmkt(cal):
    rows = []
    bad = []
    for tree in ("early", "universe"):
        for f in sorted(glob.glob(os.path.join(YD, f"data/{tree}/marginmkt/*.csv"))):
            x = pd.read_csv(f, dtype=str, keep_default_na=False)
            if list(x.columns) != ["date", "item", "buy", "sell", "repay", "prev", "balance"] or len(x) != 3 or (x["item"] == "融資金額(仟元)").sum() != 1:
                bad.append(os.path.basename(f))
            rows.append(x[x["item"] == "融資金額(仟元)"])
    df = pd.concat(rows, ignore_index=True)
    dates = df["date"].tolist()
    prev = fnum(df["prev"]); bal = fnum(df["balance"])
    dset = set(dates)
    audit = {"item": "融資金額(仟元)", "天數": len(dates), "起訖": [dates[0], dates[-1]], "表頭／列數不符的檔": bad,
             "日期⊆台北日曆": all(d in set(cal) for d in dates),
             "台北日曆在起訖內但無檔天數": int(sum(1 for d in cal if dates[0] <= d <= dates[-1] and d not in dset)),
             "prev 缺值": int(np.isnan(prev).sum()), "balance 缺值": int(np.isnan(bal).sum())}
    return pd.Series(prev, index=dates), pd.Series(bal, index=dates), audit


def margin_prev_vs_balance(prev: pd.Series, bal: pd.Series):
    """閘：prev_T 對 balance_(T−1)（資料庫 2312 §三）。主庫樹報大小（相對差），早年樹只報天數（⛔ 不印早年因素值）。"""
    d = np.asarray(prev.index, dtype=str)
    p = prev.to_numpy(); b = bal.to_numpy()
    rel = p[1:] / b[:-1] - 1.0
    dd = d[1:]
    out = {}
    for tag, m in (("主庫樹（2015-01-06～2026-09-24）", dd >= "2015-01-06"), ("早年樹（2005-01-04～2014-12-31）", dd <= "2014-12-31")):
        r = rel[m]
        o = {"比較天數": int(m.sum()), "prev_T ≠ balance_(T−1) 天數": int((r != 0).sum()),
             "|相對差| > 0.1% 天數": int((np.abs(r) > 1e-3).sum()), "|相對差| > 1% 天數": int((np.abs(r) > 1e-2).sum())}
        if tag.startswith("主庫"):
            o.update({"|相對差| 中位": float(np.median(np.abs(r))), "|相對差| p99": float(np.quantile(np.abs(r), 0.99)),
                      "|相對差| 最大": float(np.abs(r).max()), "最大那天（T）": str(dd[m][int(np.argmax(np.abs(r)))])})
        out[tag] = o
    j = int(np.where(dd == "2015-01-05")[0][0])
    out["銜接：2014-12-31 balance ＝ 2015-01-05 prev"] = bool(rel[j] == 0)
    out["銜接：|相對差| < 0.1%"] = bool(abs(rel[j]) < 1e-3)
    out["銜接：|相對差|（2015-01-05 prev ÷ 2014-12-31 balance − 1）"] = float(abs(rel[j]))
    out["銜接：主庫樹同量 |相對差| 的百分位（該差在主庫樹 2,858 天中的排名）"] = float((np.abs(rel[dd >= "2015-01-06"]) < abs(rel[j])).mean())
    return out


def load_us():
    g = us_csv("yahoo_GSPC.csv")
    gc = fnum(g["close"])
    ok = np.isfinite(gc)
    gd, gcv = g["date"].to_numpy().astype(str)[ok], gc[ok]
    out = {"#2": pd.Series(gcv[1:] / gcv[:-1] - 1.0, index=gd[1:])}
    au = {"#2 yahoo_GSPC": {"列": int(len(g)), "close 缺": int((~ok).sum()), "日期重複": int(pd.Index(g["date"]).duplicated().sum()),
                            "讀法": "單日報酬＝close_d ÷ close_(前一美股交易日) − 1"}}
    for key, name in (("#7", "fred_DGS10.csv"), ("#8", "fred_VIXCLS.csv")):
        x = us_csv(name)
        v = fnum(x["value"])
        dx = x["date"].to_numpy().astype(str)
        au[f"{key} {name}"] = {"列": int(len(x)), "缺值列（FRED 假日 . 或空）": int(np.isnan(v).sum()),
                               "缺值列 2014-01～2026-08-24": int(np.isnan(v[(dx >= "2014-01-01") & (dx <= W1)]).sum()),
                               "缺值列 2004～2014": int(np.isnan(v[(dx >= "2004-01-01") & (dx <= E1)]).sum()),
                               "處理": "缺值列略過（不補值）"}
        m = np.isfinite(v)
        out[key] = pd.Series(v[m], index=dx[m])
    c = us_csv("cbc_BP01D01_NTD.csv")
    v = fnum(c["ntd_per_usd"])
    au["#6 cbc_BP01D01_NTD"] = {"列": int(len(c)), "缺值": int(np.isnan(v).sum()), "日期重複": int(pd.Index(c["date"]).duplicated().sum()),
                                "方向": "值＝新台幣/美元 ⇒ 20 日變化高端＝新台幣貶值、低端＝升值"}
    m = np.isfinite(v)
    out["#6"] = pd.Series(v[m], index=c["date"].to_numpy().astype(str)[m])
    fed = {}
    for name in ("fred_DFEDTAR.csv", "fred_DFEDTARU.csv"):
        x = us_csv(name)
        fed[name] = pd.Series(fnum(x["value"]), index=x["date"].to_numpy().astype(str))
        au[name] = {"列": int(len(x)), "缺值": int(np.isnan(fed[name].to_numpy()).sum())}
    return out, fed, au, gd


# ═════════════ 讀法（⛔ 本段不選；全部並列）═════════════
READINGS = {
    "W": {"題": "756 日滾動分布含不含事件日本身", "a": "含：[t−755, t] 共 756 個（「只用事件日（含）以前的資料」）",
          "b": "不含：[t−756, t−1] 共 756 個，拿 t 去比（「事件日以前 756 個交易日」）"},
    "Q": {"題": "第 5／95 百分位怎麼算", "a": "線性內插（numpy 預設）：x_t ≤ P5 或 ≥ P95",
          "b": "經驗排名：窗內 ≤ x_t 的比例 ≤ 5%（低端）；窗內 ≥ x_t 的比例 ≤ 5%（高端）"},
    "C": {"題": "#2 #6 #7 #8（美股／FRED／央行）的「756 個交易日」「20 日變化」「20 日內只取第一筆」數哪一套日",
          "a": "該序列自己的觀測日（美股交易日／FRED 有值日／央行有值日）；事件映射到下一個台北交易日開盤",
          "b": "台北交易日：每個台北日取當時已知的最新值（#2 取該台北日開盤前最近一場美股的報酬，與前一台北日同一場 ⇒ 空；#6 取當日 16:00 值；#7 #8 取前一美東日值），756／20 都數台北日"},
    "D": {"題": "「同一因素同一端，20 個交易日內只取第一筆」", "a": "從【被保留的】上一筆起算，相隔 ≥ 20 日才收",
          "b": "從被保留的上一筆起算，相隔 ≥ 21 日才收（「20 日內」含第 20 日）",
          "c": "連鎖：前 20 日內只要有同端尾端日（不論有沒有被保留）就不收"},
    "E": {"題": "窗怎麼收（主窗 2017-03-02～2026-08-24；早年 2008-01～2014-12）", "a": "只看事件日在窗內（登錄 §三③ 字面「事件日落在窗外的不收」）",
          "b": "起算日與「第 20 個交易日」開盤都在窗內（「主窗 0050 報酬只用 2017-03-02～2026-08-24」）"},
    "H": {"題": "「起算日開盤 → 第 20 個交易日開盤」（只影響 E=b 的窗尾）", "a": "s ⇒ s＋20 開盤（20 個日報酬）", "b": "起算日算第 1 日 ⇒ s＋19 開盤"},
    "F": {"題": "#3「外資單日淨買賣超金額」在 2017-12-18 官方拆列之後", "a": "「外資及陸資(不含外資自營商)」＋「外資自營商」（資料庫 1545 READ_CONTRACT 的 foreign）",
          "b": "只取「外資及陸資(不含外資自營商)」"},
    "S": {"題": "n_eff 的 20 日區段用哪一天定位", "a": "起算日（從窗首切，⌊(s−w0)/20⌋；PREREGH1 §五「區段從判定窗起點切」）",
          "b": "事件日"},
    "G": {"題": "去重在哪條時間軸上做", "a": "全時間軸去重、再篩窗（窗首可能被窗外前一筆壓掉；本段表列全用這個）", "b": "窗內重新起算（影響見 pre_coverage.json「G 影響」）"},
    "X1": {"題": "登錄 §二「事件 < 10 或 n_eff < 10 的格直接出口①」與「出口①②③ 照 PREREGH1 §五（n_eff < 30 ⇒ 出口①）」",
           "a": "兩句並存：< 10 連算都不算；10～29 仍是出口①", "b": "本件出口① 門檻改成 10（⇒ 10～29 變出口②）"},
    "P5a": {"題": "#5 聯準會「聲明美東日」怎麼從 FRED 取", "a": "FRED DFEDTAR(U) 值改變的那天當聲明日（FRED 是生效日，多數比聲明日晚 1 個美股交易日）",
            "b": "FRED 改變日的前一個美股交易日當聲明日（週日聲明、盤前臨時降息這類會錯）",
            "c": "另取 FOMC 聲明日表（⛔ 不在庫 ⇒ 需資料庫線）"},
    "P5b": {"題": "#5 是否也套「20 日內只取第一筆」", "a": "套（字面「同一因素同一端」）", "b": "不套（那句寫在連續量的門檻段）"},
    "P5c": {"題": "#5 台灣央行升／降方向", "a": "⛔ 資料庫附件（sha18a7e036eb15f3c6）只有生效日與公布日、沒有利率水準 ⇒ 方向需資料庫線補一欄；本段只報升＋降合計"},
}


def tail_flags(v: np.ndarray, W: str, Q: str):
    """v：時間序（可含 NaN）。回傳 (low, high, judgeable)；judgeable＝窗滿 756 個位置。"""
    n = len(v)
    low = np.zeros(n, bool); high = np.zeros(n, bool); judg = np.zeros(n, bool)
    L = ROLL
    if W == "a":
        if n < L:
            return low, high, judg
        win = sliding_window_view(v, L); t_idx = np.arange(L - 1, n)       # 含 t
    else:
        if n < L + 1:
            return low, high, judg
        win = sliding_window_view(v[:-1], L); t_idx = np.arange(L, n)     # 不含 t
    xt = v[t_idx]
    fin = np.isfinite(xt)
    judg[t_idx] = True
    if Q == "a":
        if np.isnan(win).any():
            p5 = np.nanpercentile(win, 5, axis=1); p95 = np.nanpercentile(win, 95, axis=1)
        else:
            p5 = np.percentile(win, 5, axis=1); p95 = np.percentile(win, 95, axis=1)
        lo = fin & (xt <= p5); hi = fin & (xt >= p95)
    else:
        cnt = np.sum(np.isfinite(win), axis=1)
        with np.errstate(invalid="ignore"):
            le = np.sum(win <= xt[:, None], axis=1); ge = np.sum(win >= xt[:, None], axis=1)
        lo = fin & (le / cnt <= 0.05); hi = fin & (ge / cnt <= 0.05)
    low[t_idx] = lo; high[t_idx] = hi
    return low, high, judg


def dedupe(flag_pos: np.ndarray, D: str) -> np.ndarray:
    """flag_pos：尾端日在「去重日曆」上的位置（遞增）。回傳保留者的索引。"""
    keep = []
    last_keep = None; last_raw = None
    for i, p in enumerate(flag_pos):
        if D == "c":
            if last_raw is None or p - last_raw > DEDUP:
                keep.append(i)
            last_raw = p
        else:
            gap = DEDUP if D == "a" else DEDUP + 1
            if last_keep is None or p - last_keep >= gap:
                keep.append(i); last_keep = p
    return np.asarray(keep, int)


# ═════════════ 連續量的三種軸 ═════════════
def build_native(key, raw, cal_arr):
    """讀法 C=a：序列自己的觀測日。回傳 (dates, v, ev_date, start_pos)。"""
    d = np.asarray(raw.index, dtype=str); v = raw.to_numpy(float)
    if key == "#6":
        c = np.full(len(v), np.nan); c[CHG:] = v[CHG:] / v[:-CHG] - 1.0; v = c
    elif key == "#7":
        c = np.full(len(v), np.nan); c[CHG:] = (v[CHG:] - v[:-CHG]) * 100.0; v = c
    sp = next_tw(cal_arr, d, strict=True)
    if key == "#2":          # 事件日＝台北 T（美股 d 之後第一個台北交易日），T 日開盤起算
        ev = np.where(sp >= 0, cal_arr[np.maximum(sp, 0)], "")
    else:                    # #6：台灣 16:00 值 ⇒ T＋1；#7 #8：美東 d ⇒ 下一個台北交易日
        ev = d
    return d, v, ev, sp


def build_tw(key, raw, cal_arr):
    """讀法 C=b：台北交易日軸。回傳 (v, ev_date, start_pos)。"""
    n = len(cal_arr)
    rd = np.asarray(raw.index, dtype=str); rv = raw.to_numpy(float)
    if key == "#2":
        j = np.searchsorted(rd, cal_arr, side="left") - 1         # 最近一場 d < T
        v = np.full(n, np.nan); ok = j >= 0; v[ok] = rv[j[ok]]
        dup = np.zeros(n, bool); dup[1:] = (j[1:] == j[:-1]); v[dup] = np.nan
        start = np.arange(n)
    elif key in ("#7", "#8"):
        j = np.searchsorted(rd, cal_arr, side="left") - 1         # 前一美東日（< T）
        lvl = np.full(n, np.nan); ok = j >= 0; lvl[ok] = rv[j[ok]]
        if key == "#7":
            v = np.full(n, np.nan); v[CHG:] = (lvl[CHG:] - lvl[:-CHG]) * 100.0
        else:
            v = lvl
        start = np.arange(n)
    elif key == "#6":
        j = np.searchsorted(rd, cal_arr, side="right") - 1        # 當日（≤ T）16:00 值
        lvl = np.full(n, np.nan); ok = j >= 0; lvl[ok] = rv[j[ok]]
        v = np.full(n, np.nan); v[CHG:] = lvl[CHG:] / lvl[:-CHG] - 1.0
        start = np.arange(n) + 1; start[start >= n] = -1
    else:
        raise ValueError(key)
    return v, cal_arr.copy(), start


def build_twfactor(key, series: pd.Series, cal_arr):
    """#3、#9：原生就是台北交易日。#9＝prev_T ÷ prev_(T−20) − 1（登錄 §九；T−20 數 marginmkt 的檔）。"""
    d = np.asarray(series.index, dtype=str); x = series.to_numpy(float)
    if key == "#9":
        v = np.full(len(x), np.nan); v[CHG:] = x[CHG:] / x[:-CHG] - 1.0
    else:
        v = x
    sp = next_tw(cal_arr, d, strict=True)
    return d, v, d, sp


def run_axis(key, tagC, F, dates, v, dpos, evd, sp):
    """一條軸上所有 W×Q×D 的事件（⛔ 不含值）。回傳 (rows, 可判日)。"""
    first = int(np.argmax(np.isfinite(v)))
    vv = v[first:]
    rows, fj = [], {}
    for W in "ab":
        for Q in "ab":
            lo, hi, jd = tail_flags(vv, W, Q)
            jp = np.where(jd)[0]
            fj[f"W{W}"] = str(dates[first + jp[0]]) if len(jp) else None
            for end, fl in (("低端", lo), ("高端", hi)):
                idx = np.where(fl)[0] + first
                for D in "abc":
                    k = dedupe(dpos[idx], D)
                    for i in idx[k]:
                        s = int(sp[i])
                        rows.append({"因素": key, "端": end, "C": tagC, "F": F, "W": W, "Q": Q, "D": D,
                                     "事件日": str(evd[i]), "起算日": str(cal_arr_g[s]) if s >= 0 else "", "起算位置": s, "去重位置": int(dpos[i])})
    return rows, fj


cal_arr_g: np.ndarray = np.array([])


# ═════════════ #5 離散事件 ═════════════
def fed_events(fed, gspc_dates):
    a = fed["fred_DFEDTAR.csv"].dropna(); b = fed["fred_DFEDTARU.csv"].dropna()
    s = pd.concat([a, b]).sort_index()
    ch = s.diff()
    us = np.asarray(sorted(gspc_dates))
    rows = []
    for d, dv in ch.items():
        if not np.isfinite(dv) or dv == 0:
            continue
        k = int(np.searchsorted(us, d, side="left")) - 1
        rows.append({"FRED改變日": d, "方向": "調升" if dv > 0 else "調降",
                     "來源": ("DFEDTAR" if d <= "2008-12-15" else "DFEDTARU") + ("（DFEDTAR 2008-12-15 → DFEDTARU 2008-12-16 銜接）" if d == "2008-12-16" else ""),
                     "前一美股交易日": str(us[k]) if k >= 0 else ""})
    return pd.DataFrame(rows)


def exit_of(n_eff: int, X1: str = "a") -> str:
    th1 = 30 if X1 == "a" else 10
    if n_eff < th1:
        return "出口①"
    return "出口②" if n_eff < 100 else "出口③"


def summarize(ev_all, cal_arr, w0, w1, e0p, e1p, e0d, e1d):
    out, years = [], []
    cols = ["因素", "端", "C", "F", "W", "Q", "D"]
    for keys, g in ev_all.groupby(cols, sort=False):
        base = dict(zip(cols, keys))
        sp = g["起算位置"].to_numpy(); ed = g["事件日"].to_numpy().astype(str)
        epos = np.searchsorted(cal_arr, ed, side="left")          # 事件日在台北日曆的位置（非台北日 ⇒ 下一個台北日）
        for E, H in (("a", "-"), ("b", "a"), ("b", "b")):
            h = HOLD if H in ("-", "a") else HOLD - 1
            if E == "a":
                mm = (ed >= W0) & (ed <= W1); me = (ed >= e0d) & (ed <= e1d)
            else:
                mm = (sp >= w0) & (sp + h <= w1); me = (sp >= e0p) & (sp + h <= e1p)
            for S in "ab":
                pm = sp[mm] if S == "a" else epos[mm]
                pe = sp[me] if S == "a" else epos[me]
                nm, ne = int(mm.sum()), int(me.sum())
                sm, se = len(set(((pm - w0) // HOLD).tolist())), len(set(((pe - e0p) // HOLD).tolist()))
                nfm, nfe = min(nm, sm), min(ne, se)
                out.append(dict(base, E=E, H=H, S=S, 主窗事件數=nm, 主窗區段數=sm, 主窗n_eff=nfm,
                                主窗出口上限_X1a=exit_of(nfm, "a"), 主窗出口上限_X1b=exit_of(nfm, "b"), 主窗每年=round(nm / (WIN_DAYS / 245.0), 2),
                                早年事件數=ne, 早年區段數=se, 早年n_eff=nfe, 早年出口上限_X1a=exit_of(nfe, "a"),
                                主窗60日可收=int(((sp[mm] >= w0) & (sp[mm] + HOLD_DESC <= w1)).sum()),
                                主窗00757可收=int((g["起算日"].to_numpy().astype(str)[mm] >= ETF757_FIRST).sum())))
            for tag, m in (("主窗", mm), ("早年", me)):
                for y, c in pd.Series(ed[m]).str[:4].value_counts().items():
                    years.append(dict(base, E=E, H=H, 段=tag, 年=y, 事件數=int(c)))
    return pd.DataFrame(out), pd.DataFrame(years)


def restart_effect(ev_all, cal_arr, w0):
    """讀法 G：窗內重新起算會多收幾筆（只數主窗首 20 日內被窗外前一筆壓掉的尾端日 ⇒ 上界 1 筆／格）。"""
    res = []
    for keys, g in ev_all.groupby(["因素", "端", "C", "F", "W", "Q", "D"], sort=False):
        before = g[g["事件日"] < W0]
        inside = g[g["事件日"] >= W0]
        if not len(before):
            continue
        lastd = before["事件日"].max()
        firstin = inside["事件日"].min() if len(inside) else None
        near = (pd.Timestamp(W0) - pd.Timestamp(lastd)).days <= 31      # 20 個交易日 ≤ 31 曆日 ⇒ 只有這種格窗首可能被壓
        res.append(dict(zip(["因素", "端", "C", "F", "W", "Q", "D"], keys), 窗外最後一筆=lastd, 窗內第一筆=firstin,
                        窗外最後一筆在W0前31曆日內=bool(near)))
    return pd.DataFrame(res)


# ═════════════ 閘：0050 錨 ═════════════
def gate_0050_main():
    from . import rerun17 as RR
    from . import data as D
    RR.use_snapshot()
    cal = D.load_calendar()
    w0, w1 = RR.win_bounds(cal)
    bench = RR.load_bench(cal)
    bw = RR.bench_row(cal, bench, w0, w1 + 1)
    same = repr(bw["cagr"]) == repr(RR.ANCHOR[0]) and repr(bw["mdd"]) == repr(RR.ANCHOR[1])
    s757 = pd.read_csv(os.path.join(D.DATA, "stocks", "00757.csv"), dtype=str, usecols=["date"])
    return {"年化": bw["cagr"], "回落": bw["mdd"], "錨": list(RR.ANCHOR), "逐位元": bool(same), "資料": RR.H2D,
            "00757 首列": s757["date"].iloc[0]}


def gate_0050_early(cal):
    """早年 0050 錨（early_data／researchV 閘 B 同法，⛔ 不算報酬）：兩來源逐欄互驗、官方除息 2005～2014 逐筆、data/extra 三筆 factor、早年窗無缺收盤。"""
    rows = []
    for f in sorted(glob.glob(os.path.join(YD, "data/early/daily/*.csv"))):
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                p = line.rstrip("\n").split(",")
                if len(p) > 4 and p[2] == "0050" and p[4] == "twse":
                    rows.append(p[:17])
    cols = ["key", "date", "stock_id", "name", "market", "open", "high", "low", "close", "volume", "amount", "change", "limit",
            "shares", "transactions", "price_basis", "last_price"]
    e50 = pd.DataFrame(rows, columns=cols).set_index("date")
    x50 = pd.read_csv(os.path.join(YD, "data/extra/0050_2012_2014.csv"), dtype=str, keep_default_na=False).set_index("date")
    com = sorted(set(e50.index) & set(x50.index))
    diffs = {}
    for c in ("open", "high", "low", "close", "volume", "amount", "transactions"):
        a_ = pd.to_numeric(e50.loc[com, c].str.replace(",", ""), errors="coerce").to_numpy(float)
        b_ = pd.to_numeric(x50.loc[com, c].str.replace(",", ""), errors="coerce").to_numpy(float)
        diffs[c] = int((~np.isclose(a_, b_, rtol=0, atol=1e-9, equal_nan=True)).sum())
    close = pd.to_numeric(e50["close"], errors="coerce")
    ecal = [d for d in cal if E0 <= d <= E1]
    miss = [d for d in ecal if d not in e50.index or not np.isfinite(close.get(d, np.nan))]
    ex = []
    for f in sorted(glob.glob(os.path.join(YD, "data/early/exright/*.csv"))):
        x = pd.read_csv(f, dtype=str, keep_default_na=False)
        ex.append(x[x["stock_id"] == "0050"])
    ex = pd.concat(ex, ignore_index=True)
    tr = [d for d in cal if d in e50.index and np.isfinite(close.get(d, np.nan))]
    evs = []
    for r in ex.itertuples():
        k = tr.index(r.date) if r.date in tr else -1
        pc = float(close[tr[k - 1]]) if k > 0 else np.nan
        pre, ref, val = float(r.pre_close), float(r.ref_price), float(r.value)
        evs.append({"除息日": r.date, "前收＝早年日K前一有成交日收盤": bool(abs(pc - pre) < 5e-3), "參考價＝前收−息": bool(abs(pre - val - ref) < 0.011)})
    adj = pd.read_csv(os.path.join(YD, "data/extra/0050_adj_2012_2014.csv"), dtype=str)
    fchk = []
    for r in adj.itertuples():
        m = ex[ex["date"] == r.date]
        f8 = round(float(m["ref_price"].iloc[0]) / float(m["pre_close"].iloc[0]), 8) if len(m) else np.nan
        fchk.append({"日": r.date, "early/exright 有同日": bool(len(m)), "ref/pre（8 位）＝extra factor": bool(abs(f8 - float(r.factor)) < 5e-9)})
    g = {"兩來源共同日": len(com), "extra 天數": int(len(x50)), "逐欄不同數": diffs,
         "早年窗（2008-01～2014-12）台北日": len(ecal), "0050 缺收盤天數": len(miss), "缺的日（前 10）": miss[:10],
         "early/exright 0050 除息筆數（2005～2014）": len(evs), "除息逐筆": evs, "extra 三筆": fchk,
         "對照（資料庫線 0404 §二，引用）": "官方 0050 除息 2005～2014 共 10 次"}
    g["過"] = bool(all(v == 0 for v in diffs.values()) and len(com) == len(x50) and len(miss) == 0 and len(evs) == 10
                  and all(e["前收＝早年日K前一有成交日收盤"] and e["參考價＝前收−息"] for e in evs)
                  and all(f["early/exright 有同日"] and f["ref/pre（8 位）＝extra factor"] for f in fchk))
    return g


# ═════════════ 主流程 ═════════════
def pre():
    global cal_arr_g
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    man = extract_db()
    log(f"[資料] tw-stock-data {DB_SHA[:10]}（git archive ⇒ {YD}，tar sha256 {man['tar_sha256'][:16]}）｜us-stock-data {US_SHA[:10]}（git show）｜0050／主窗日曆 edc6f8002f 快照")
    G = {}
    G["0050錨_主窗"] = gate_0050_main()
    log(f"[閘 0050 錨 主窗] 年化 {G['0050錨_主窗']['年化']!r}／回落 {G['0050錨_主窗']['回落']!r}｜逐位元 {G['0050錨_主窗']['逐位元']}")
    if not G["0050錨_主窗"]["逐位元"]:
        raise SystemExit("⛔ 主窗 0050 錨不過")
    assert G["0050錨_主窗"]["00757 首列"] == ETF757_FIRST
    cal, pos, gcal = tw_calendar()
    G["日曆"] = gcal
    log(f"[閘 日曆] {json.dumps(gcal, ensure_ascii=False)}")
    cal_arr = np.asarray(cal, dtype=str)
    cal_arr_g = cal_arr
    w0, w1 = pos[W0], pos[W1]
    e0p = int(np.searchsorted(cal_arr, E0)); e1p = int(np.searchsorted(cal_arr, E1, side="right")) - 1
    e0d, e1d = str(cal_arr[e0p]), str(cal_arr[e1p])
    G["0050錨_早年"] = gate_0050_early(cal)
    g5 = G["0050錨_早年"]
    log(f"[閘 0050 錨 早年] 過 {g5['過']}｜共同日 {g5['兩來源共同日']}｜逐欄不同 {g5['逐欄不同數']}｜除息 {g5['early/exright 0050 除息筆數（2005～2014）']} 筆｜"
        f"早年窗缺收盤 {g5['0050 缺收盤天數']}")

    inst, a_inst = load_instamt(cal)
    prev, bal, a_mg = load_marginmkt(cal)
    G["#9 prev 對 balance"] = margin_prev_vs_balance(prev, bal)
    log(f"[閘 #9 prev 對 balance] {json.dumps({k: v for k, v in G['#9 prev 對 balance'].items()}, ensure_ascii=False)}")
    us, fed, a_us, gspc_dates = load_us()
    COV = {"#3 instamt": a_inst, "#9 marginmkt": a_mg, "美股與總經（us-stock-data）": a_us, "us manifest": us_manifest()}
    bd = set(us["#6"].index)
    COV["#6 BP01D01 對台北日曆"] = {}
    for tag, lo, hi in (("主窗", W0, W1), ("756 回看（2014-01-01～2017-03-01）", "2014-01-01", "2017-03-01"), ("早年（2004～2014）", "2004-01-01", E1)):
        cc = [d for d in cal if lo <= d <= hi]
        ccs = set(cc)
        no_cbc = [d for d in cc if d not in bd]
        extra_ = sorted(d for d in bd if lo <= d <= hi and d not in ccs)
        COV["#6 BP01D01 對台北日曆"][tag] = {"台北日無央行值天數": len(no_cbc), "台北日無央行值（前 30）": no_cbc[:30],
                                          "央行有值但非台北交易日天數": len(extra_), "（前 30）": extra_[:30]}

    rows = []
    FJ = {}
    for key in ("#2", "#6", "#7", "#8"):
        dN, vN, evN, spN = build_native(key, us[key], cal_arr)
        r1, f1 = run_axis(key, "a", "-", dN, vN, np.arange(len(dN)), evN, spN)
        vB, evB, spB = build_tw(key, us[key], cal_arr)
        r2, f2 = run_axis(key, "b", "-", cal_arr, vB, np.arange(len(cal_arr)), evB, spB)
        rows += r1 + r2
        FJ[key] = {"資料首日": str(us[key].index[0]), **{f"Ca{k}": v for k, v in f1.items()}, **{f"Cb{k}": v for k, v in f2.items()}}
        log(f"[{key}] 事件列 Ca {len(r1)}｜Cb {len(r2)}｜可判首日 {FJ[key]}")
    for F, s in inst.items():
        d, v, evd, sp = build_twfactor("#3", s, cal_arr)
        r_, fj = run_axis("#3", "-", F, d, v, np.arange(len(d)), evd, sp)
        rows += r_
        m = d >= "2015-01-05"
        _, _, jd = tail_flags(v[m], "a", "a")
        FJ[f"#3 F{F}"] = {"資料首日": d[0], **fj, "只用主庫樹（2015 起）時 Wa": str(d[m][np.where(jd)[0][0]])}
        log(f"[#3 F{F}] 事件列 {len(r_)}｜{FJ[f'#3 F{F}']}")
    d9, v9, ev9, sp9 = build_twfactor("#9", prev, cal_arr)
    r_, fj = run_axis("#9", "-", "-", d9, v9, np.arange(len(d9)), ev9, sp9)
    rows += r_
    m = d9 >= "2015-01-05"
    x = prev.to_numpy(float)[m]; vm = np.full(len(x), np.nan); vm[CHG:] = x[CHG:] / x[:-CHG] - 1.0
    fin = np.where(np.isfinite(vm))[0]
    FJ["#9"] = {"資料首日": d9[0], **fj, "只用主庫樹（2015 起）時 Wa": str(d9[m][fin[ROLL - 1]])}
    log(f"[#9] 事件列 {len(r_)}｜{FJ['#9']}")
    # #9 balance 讀法（⛔ 判定不用；只當閘的描述）
    d9b, v9b, ev9b, sp9b = build_twfactor("#9", bal, cal_arr)
    rb, _ = run_axis("#9bal", "-", "-", d9b, v9b, np.arange(len(d9b)), ev9b, sp9b)
    ev = pd.DataFrame(rows)
    evb = pd.DataFrame(rb)
    cmp9 = {}
    e9 = ev[ev["因素"] == "#9"]
    for (W, Q, D), g in e9.groupby(["W", "Q", "D"]):
        gb = evb[(evb["W"] == W) & (evb["Q"] == Q) & (evb["D"] == D)]
        for tag, lo, hi in (("主窗", W0, W1), ("早年", e0d, e1d)):
            ga = g[(g["事件日"] >= lo) & (g["事件日"] <= hi)]; gbb = gb[(gb["事件日"] >= lo) & (gb["事件日"] <= hi)]
            A = set(zip(ga["端"], ga["事件日"]))
            # balance 讀法在 T−1 盤後就「看得到」同一段（prev_T 是 T−1 的最終餘額）⇒ 對齊：balance 事件日往後挪 1 個台北交易日再比
            B = set(zip(gbb["端"], [cal[pos[d] + 1] for d in gbb["事件日"]]))
            cmp9[f"W{W}Q{Q}D{D}｜{tag}"] = {"prev 讀法事件": len(A), "balance 讀法事件": len(B), "對齊 1 日後相同": len(A & B),
                                         "只在 prev": len(A - B), "只在 balance": len(B - A)}
    G["#9 prev 對 balance"]["事件旗標差異（描述；⛔ 判定只用 prev）"] = cmp9
    log("[#9 prev 對 balance 事件差異（balance 事件日＋1 對齊）相同/只在prev/只在balance] " + "｜".join(f"{k} {v['對齊 1 日後相同']}/{v['只在 prev']}/{v['只在 balance']}" for k, v in cmp9.items()))

    k3 = ["端", "W", "Q", "D", "事件日"]
    A3 = set(map(tuple, ev[(ev["因素"] == "#3") & (ev["F"] == "a")][k3].values)); B3 = set(map(tuple, ev[(ev["因素"] == "#3") & (ev["F"] == "b")][k3].values))
    COV["#3 instamt"]["F 讀法：事件日逐筆相同（全時間軸、全部 W×Q×D）"] = bool(A3 == B3)
    COV["#3 instamt"]["F 讀法：事件列數 Fa／Fb／只在 Fa／只在 Fb"] = [len(A3), len(B3), len(A3 - B3), len(B3 - A3)]
    log(f"[#3 F 讀法] 事件逐筆相同 {A3 == B3}｜{COV['#3 instamt']['F 讀法：事件列數 Fa／Fb／只在 Fa／只在 Fb']}")

    summ, years = summarize(ev, cal_arr, w0, w1, e0p, e1p, e0d, e1d)
    summ["格"] = summ["因素"] + " " + summ["端"] + summ["F"].map(lambda x: "" if x == "-" else " F" + x)
    cells = []
    for cell, g in summ.groupby("格", sort=False):
        r = {"格": cell, "主窗事件數 min": int(g["主窗事件數"].min()), "主窗事件數 max": int(g["主窗事件數"].max()),
             "主窗 n_eff min": int(g["主窗n_eff"].min()), "主窗 n_eff max": int(g["主窗n_eff"].max()),
             "主窗每年 min": float(g["主窗每年"].min()), "主窗每年 max": float(g["主窗每年"].max()),
             "主窗出口上限（X1=a）": "／".join(sorted(set(g["主窗出口上限_X1a"]))), "主窗出口上限（X1=b）": "／".join(sorted(set(g["主窗出口上限_X1b"]))),
             "早年事件數 min": int(g["早年事件數"].min()), "早年事件數 max": int(g["早年事件數"].max()),
             "早年出口上限（X1=a）": "／".join(sorted(set(g["早年出口上限_X1a"]))),
             "60日可收 min": int(g["主窗60日可收"].min()), "00757可收 min": int(g["主窗00757可收"].min()), "00757可收 max": int(g["主窗00757可收"].max())}
        for D in "abc":
            h = g[g["D"] == D]
            r[f"主窗 D={D}"] = f"{int(h['主窗n_eff'].min())}～{int(h['主窗n_eff'].max())}"
            r[f"早年 D={D}"] = f"{int(h['早年事件數'].min())}～{int(h['早年事件數'].max())}"
        cells.append(r)
    pd.DataFrame(cells).to_csv(os.path.join(OUT, "pre_cells.csv"), index=False, encoding="utf-8")
    yy = years[years["E"] == "a"].copy()
    yy["格"] = yy["因素"] + " " + yy["端"] + yy["F"].map(lambda x: "" if x == "-" else " F" + x)
    full = yy.pivot_table(index=["格", "C", "F", "W", "Q", "D", "段"], columns="年", values="事件數", fill_value=0)
    yr = full.groupby(level=["格", "段"]).agg(["min", "max"])
    yrs = pd.DataFrame({y: yr[(y, "min")].astype(int).astype(str) + "～" + yr[(y, "max")].astype(int).astype(str) for y in sorted(set(yy["年"]))})
    yrs.to_csv(os.path.join(OUT, "pre_year_range.csv"), encoding="utf-8")
    rst = restart_effect(ev, cal_arr, w0)

    # #5 聯準會
    fe = fed_events(fed, gspc_dates)
    fed_rows = []
    for P5a in "ab":
        d_stmt = (fe["FRED改變日"] if P5a == "a" else fe["前一美股交易日"]).to_numpy().astype(str)
        spf = next_tw(cal_arr, d_stmt, strict=True)
        for P5b in "ab":
            for end in ("調升", "調降"):
                mk = (fe["方向"] == end).to_numpy()
                sd = d_stmt[mk]; ss = spf[mk]
                if P5b == "a":
                    k = dedupe(ss, "a"); sd, ss = sd[k], ss[k]
                for tag, lo, hi, wl, wh in (("主窗", W0, W1, w0, w1), ("早年", e0d, e1d, e0p, e1p)):
                    mm = (sd >= lo) & (sd <= hi)
                    mb = (ss >= wl) & (ss + HOLD <= wh)
                    segs = len(set(((ss[mm] - wl) // HOLD).tolist()))
                    n = int(mm.sum())
                    fed_rows.append({"因素": "#5 聯準會", "端": end, "P5a": P5a, "P5b": P5b, "段": tag, "事件數_Ea": n, "事件數_Eb": int(mb.sum()),
                                     "區段數": segs, "n_eff": min(n, segs), "出口上限": exit_of(min(n, segs)),
                                     "00757可收": int((cal_arr[ss[mm]] >= ETF757_FIRST).sum()) if tag == "主窗" else "",
                                     "聲明日": ";".join(sd[mm]), "起算日": ";".join(cal_arr[ss[mm]])})
    fed_df = pd.DataFrame(fed_rows)
    fed_list = fe[(fe["FRED改變日"] >= "2007-12-01") & (fe["FRED改變日"] <= W1)]
    # #5 台灣央行
    p = os.path.join(MAILBOX, CBC_ATTACH)
    cbc = pd.read_csv(p, dtype=str)
    cbc_sha = hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
    n_all = len(cbc)
    cbc = cbc[cbc["effective_date"] != CBC_EXCLUDE]
    rel = cbc["decision_release_date"].to_numpy().astype(str)
    spc = next_tw(cal_arr, rel, strict=True)
    tw5 = {"附件": CBC_ATTACH, "sha256[:16]": cbc_sha, "列數": n_all, "剔除": CBC_EXCLUDE, "剔除後": int(len(cbc))}
    for tag, lo, hi, wl, wh in (("主窗", W0, W1, w0, w1), ("早年", e0d, e1d, e0p, e1p)):
        mm = (rel >= lo) & (rel <= hi)
        mb = (spc >= wl) & (spc + HOLD <= wh)
        n = int(mm.sum())
        tw5[tag] = {"升＋降 合計（Ea）": n, "合計（Eb）": int(mb.sum()), "公布日": rel[mm].tolist(), "起算日": [str(cal_arr[s]) for s in spc[mm]],
                    "兩格各自事件數上限": n, "出口上限（不論方向怎麼分、不論去重）": exit_of(n), "< 10（X1 兩讀法都直接出口①）": n < 10}
    # #4、#1
    p4 = pos.get("2023-09-25")
    n_have = len(cal_arr) - p4
    other = {"#4 外資期貨": {"資料": "⛔ 不在 tw-stock-data 3edc0e2206 樹；資料庫 1509：期交所只給 2023-09-25 起", "首日": "2023-09-25",
                           "到合併日曆末日（" + str(cal_arr[-1]) + "）已有台北日": int(n_have),
                           "20 日變化可算後尚缺（W=a，756＋20 日）": int(ROLL + CHG - n_have),
                           "處理": "登錄 §三①：⛔ 不計 N、前瞻紀錄（⛔ 本件不判）；主窗內依構造 0 事件"},
             "#1 景氣燈號": {"資料": "⛔ 不在庫（資料庫 1542：國發會網站在反機器人驗證後；data.gov.tw zip 為回溯修正版，未落地）",
                          "處理": "登錄 §一：改描述、⛔ 不計 N、⛔ 不判；本段無資料可報頻率"}}
    # 可判定性算術
    z = NormalDist().inv_cdf(1 - ALPHA / N_CELLS / 2)
    z80 = NormalDist().inv_cdf(0.8)
    arith = {"每格 α（Bonferroni 按 16 格，雙尾）": ALPHA / N_CELLS, "z*": z, "80% 檢定力另加 z": z80,
             "主窗交易日 W": WIN_DAYS, "20 日獨立區段上限 ⌊W/20⌋": WIN_DAYS // HOLD, "出口③ 依構造可達（⌊W/20⌋ ≥ 100）": WIN_DAYS // HOLD >= 100,
             "早年窗": [e0d, e1d], "早年窗交易日": e1p - e0p + 1, "早年 20 日區段上限": (e1p - e0p + 1) // HOLD,
             "最小可測差（σ20 為單位；⛔ σ 本段不讀）": {str(n): {"Bonferroni（z*/√n）": z / np.sqrt(n), "＋80% 檢定力（(z*+0.84)/√n）": (z + z80) / np.sqrt(n)}
                                                   for n in (10, 20, 30, 50, 100, 115)},
             "註": "月分群 SE 在事件同月叢聚時比 σ/√n 大 ⇒ 上表是下界"}

    # ── 輸出（⛔ 不含任何因素值）──
    ev_out = ev[(ev["事件日"] >= "2007-12-01") & (ev["事件日"] <= "2026-08-31")].drop(columns=["去重位置"])
    ev_out.to_csv(os.path.join(OUT, "pre_events.csv"), index=False, encoding="utf-8")
    summ.to_csv(os.path.join(OUT, "pre_freq.csv"), index=False, encoding="utf-8")
    years.to_csv(os.path.join(OUT, "pre_freq_year.csv"), index=False, encoding="utf-8")
    fed_df.to_csv(os.path.join(OUT, "pre_fed.csv"), index=False, encoding="utf-8")
    fed_list.to_csv(os.path.join(OUT, "pre_fed_changes.csv"), index=False, encoding="utf-8")
    rst.to_csv(os.path.join(OUT, "pre_restart.csv"), index=False, encoding="utf-8")
    json.dump({"讀法": READINGS, "可判首日": FJ, "覆蓋與缺值": COV, "#5 台灣": tw5, "#4 #1": other, "算術": arith,
               "窗": {"主窗": [W0, W1, int(w0), int(w1)], "早年": [e0d, e1d, e0p, e1p]}},
              open(os.path.join(OUT, "pre_coverage.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    json.dump(G, open(os.path.join(OUT, "pre_gates.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完成] 事件列 {len(ev)}（輸出 {len(ev_out)}）｜頻率列 {len(summ)}｜{time.time() - t0:.0f}s")
    open(os.path.join(OUT, "pre_run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["pre"])
    a = ap.parse_args()
    if a.stage == "pre":
        pre()


if __name__ == "__main__":
    main()
