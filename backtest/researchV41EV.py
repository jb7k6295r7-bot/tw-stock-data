# -*- coding: utf-8 -*-
"""大漲主題框架 v4.1 新設定重算：期望值、兩平命中率、停用張數（產業分析線 seq30／seq34／seq37／seq38；描述、⛔ 不判定、不計 N）——回測線計算子代理。
⚠ 事後挑的贏家與失敗樣本 ⇒ 只描述，⛔ 不是期望值的證據。
⛔ 不 commit、不改既有檔；researchRevTurn_freq（ensure_data、prices、log）、researchShortageExit（seam_open）、researchTopSell_freq（raw_close）
   ⛔ 只 import；結算與接續的寫法照 researchLampTrade（Q1、Q5、Q5′、Q7）原式抄。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchV41EV
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchV41EV_check
輸入 backtest/resultsV41EV/：
  cases_input.csv     附件「進場候選K1至K4_56案與K1」複本，56 列；★ K21 依產業 seq37 §二更正為「AI 高階銅箔（HVLP）／金居 8358」（代號不變）
  peers_input_TW.csv  附件 peers_input_TW（產業 20261025-1328，31 案 55 列）複本
  peers_input_US.csv  附件 peers_input_US（同上，25 案 52 列）複本
輸出 backtest/resultsV41EV/：table.csv（每案×每檔×判決月）、members.csv（三版成員與剔除）、caps.csv（燈亮月月底市值；美股只放判定、⛔ 不放價格）、
  themes.csv（每版×每主題×判決月）、stats.csv、summary.md、main.json、run.log

═══ 讀法（★＝執行者定）═══
 V0 三版成員：
    代表股版 ＝ 案例表「公司」欄（燈 1 事件點名的公司）1 檔。
    同業等權版 ＝ peers_input 該案依名次前 3 列（實際幾家算幾家、⛔ 不硬湊；名稱標「備援」者＝燈 1 點名公司）；代表股不在名單 ⇒ 不加入。
    設下限版 ＝ 同業名單依名次，剔除燈亮月月底市值 台股 ＜ 新台幣 100 億、美股 ＜ 20 億美元者，名單內下一名遞補、取前 3（名單內沒有就少一家）；
               市值算不出 ⇒「查無、未剔除」。
    名單內查不到價格的代號 ⇒ 標「資料不足」、⛔ 不換代號；主題值只用有價格的成員；整個主題都沒有價格 ⇒ 該版該主題不進統計（件數照報）。
 V1 台股價格 ＝ researchLampTrade Q1 同一面板（PIN 9b0e9882572c；還原含息收盤 C、還原開盤 O 含接縫倍數；壞根 BAD 同定義）。
 V2 進場 ＝ 燈亮月下一個月第一個交易日的還原開盤（無成交 ⇒ 順延到下一個有成交開盤，日數照報）。美股同（還原開盤 ＝ open × adjclose ÷ close；
    data/prices/ 格式直接用 adjOpen／adjClose）。
 V3 判決日 ＝ 進場日 ＋ H 個日曆月（H＝60 主表、72 副欄；另附 24、36 月）當天或之前最後一個交易日的還原收盤；
    超出資料尾 ⇒ 結算到資料尾、標「未到判決日」。持有期間 ⛔ 不模擬 v4 出場 ①～⑤。
 V4 跨壞根 ⇒ 結算在第一個壞根前一根有效收盤、標「⚠壞根截斷」；接續版另欄（LampTrade Q5′）。下市 ⇒ 最後有效收盤、標「下市結算」。
    美股：連續 ≥5 交易日無 K 棒 ⇒ 壞根；最後一根距日曆尾 >10 日 ⇒ 下市結算。
 V5 R ＝ 判決價 ÷ 進場價 − 1 − 成本；台股 0.585% 來回、美股 0.05%／邊（0.1% 來回）。單位「份」＝每檔 1 份的損益倍數。
 V6 大盤 ＝ 台股 data/history/market_tri.csv；美股 ^SP500TR；進場前一交易日收盤 → 結算日收盤；超額 ＝ R − 大盤；大盤不扣成本。
 V7 主題值 ★ ＝ 同主題各檔 R（與超額）等權平均（1 個主題＝1 個獨立樣本）；合計 ＝ 各檔之和。另附「每檔各算 1 張」版。
 V8 兩平 p* ＝ −L ÷ (W − L)（L ≥ 0 ⇒ 不適用）；停用張數 n ＝ ⌈ln 0.1 ÷ ln(1 − p*)⌉；反例 μ、s（ddof=1）、門檻 μ − 1.28·s／√8。
 V9 市值（燈亮月月底＝該月該檔最後一個有收盤的交易日）：
    台股 ＝ 未還原收盤 × 當日發行股數；≤2014-12 讀 data/early/daily/<日>.csv 的 close、shares，≥2015 讀 data/stocks/<代號>.csv 的 close、shares
    （日檔 feed 的當日發行股數＝point-in-time）；shares 空 ⇒ 該月內最近一個有值的日子（註明），仍無 ⇒ 查無。
    美股 ＝ 未還原收盤 × SEC 申報股數：收盤 ＝ prices_yahoo close（已含拆股調整）× 該日之後所有 split 事件比率之積（events_yahoo；DELL 的
    spin-off 調整也照 Yahoo 列為 split 的倍數還原）；data/prices/ 格式用 close（未調整）。股數 ＝ fundamentals/shares_outstanding.csv
    as_of_date ≤ 月底的最後一個日期（同日多個 share_class 加總），距月底 >400 日或查無 ⇒ 查無。⛔ 美股市值只輸出判定，不輸出數值與價格。
"""
from __future__ import annotations

import io
import json
import math
import os
import re
import subprocess
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchRevTurn_freq as RT             # noqa: E402
from backtest import researchShortageExit as SE             # noqa: E402
from backtest import researchTopSell_freq as TS             # noqa: E402

OUT = "backtest/resultsV41EV"
INP = os.path.join(OUT, "cases_input.csv")
PEERS = {"TW": os.path.join(OUT, "peers_input_TW.csv"), "US": os.path.join(OUT, "peers_input_US.csv")}
PIN = "9b0e9882572c"
COST_TW = 0.00585
COST_US = 0.001
HS = (24, 36, 60, 72)
FLOOR = {"TW": 1e10, "US": 2e9}
US_REPO = os.path.expanduser("~/us-stock-data")
ORSTED = ("DNNGY", "ORSTED_CO")
ORSTED_CUT = pd.Timestamp("2025-09-05")
SPECIAL_BEFORE = [("CHPT", "2021-03-01", "SPAC 合併前價"), ("LCID", "2021-07-26", "SPAC 合併前價"), ("CGC", "2018-05-24", "可能是 OTC 價")]
VARS = ["代表股版", "同業等權版", "設下限版"]
WARN = "事後挑的贏家與失敗樣本 ⇒ 只描述，⛔ 不是期望值的證據"
QUAL = ("名單品質（產業 seq37 §二）：台股名次多半依「營收規模」而非「主題占比」排（只有 K45 照占比），排滿 3 家 6 案、只有 1 家 13 案 ⇒ "
        "台股同業版只能當近似；美股排滿 3 家 10 案，占比依 10-K／20-F 部門，部分以相近部門代替。")
K21NOTE = "K21 更正（產業 seq37 §二）：案例表誤標「T-glass／富喬 8358」，實為 AI 高階銅箔 HVLP 段、代表股 8358 金居（代號不變、R 不變）；cases_input.csv 已改產業與公司欄。"
LOG = RT.LOG
log = RT.log


def gshow(path, repo, ref="origin/main"):
    t = subprocess.run(["git", "-C", repo, "show", f"{ref}:{path}"], capture_output=True)
    return t.stdout if t.returncode == 0 else None


def tshow(sha, path):
    t = subprocess.run(["git", "show", f"{sha}:{path}"], capture_output=True)
    return t.stdout if t.returncode == 0 else None


def code_of(row):
    s = row["公司"].strip()
    if row["市場"] == "TW":
        m = re.search(r"(\d{4})\s*$", s)
        return m.group(1) if m else None
    if s.startswith("Ørsted"):
        return "DNNGY"          # ★ K39 代表股用美元 ADR DNNGY（同業名單備援列同碼；與 ^SP500TR 同幣別），丹麥 ORSTED_CO（DKK）不用
    m = re.match(r"^([A-Z][A-Z.\-]*)（", s)
    return m.group(1) if m else None


def load_cases():
    CS = pd.read_csv(INP, dtype=str, keep_default_na=False)
    if len(CS) != 56:
        raise SystemExit(f"⛔ 附件列數 {len(CS)} ≠ 56")
    k = CS["id"] == "K21"
    if "富喬" in CS.loc[k, "公司"].iloc[0]:
        raise SystemExit("⛔ cases_input.csv K21 尚未更正（應為金居 8358）")
    return CS


def load_peers():
    P = {}
    for mk, f in PEERS.items():
        d = pd.read_csv(f, dtype=str, keep_default_na=False)
        d["名次n"] = pd.to_numeric(d["名次"], errors="coerce")
        d = d.sort_values(["id", "名次n"], na_position="last")
        P[mk] = d
    return P


# ═════════════ 台股 ═════════════
def tw_engine():
    sha, DN, MD = RT.ensure_data(PIN)
    PX = RT.prices(sha, DN, 3)
    O, nseam = SE.seam_open(PX)
    T = pd.read_csv(io.BytesIO(tshow(sha, "data/history/market_tri.csv"))); T["date"] = pd.to_datetime(T["date"])
    T = T.dropna().drop_duplicates("date").sort_values("date").set_index("date")["close"]
    return sha, PX, O, nseam, T, z50(sha)


def z50(sha):
    """0050 含息還原收盤（副欄基準）：原始收盤 ≤2014 data/early/daily、≥2015 data/stocks/0050.csv；
    事件 ≤2014 data/early/exright（ref_price÷pre_close）、≥2015 data/adj/0050.csv factor（含 2025-06-18 分割）。
    還原價(d) ＝ 原始收盤(d) × Π_{事件日 > d} 因子。"""
    fs = [x for x in subprocess.run(["git", "ls-tree", "--name-only", sha, "data/early/daily/"], capture_output=True, text=True, check=True).stdout.split()
          if x.endswith(".csv")]
    ex = [x for x in subprocess.run(["git", "ls-tree", "--name-only", sha, "data/early/exright/"], capture_output=True, text=True, check=True).stdout.split()
          if x.endswith(".csv")]

    def batch(paths):
        inp = "".join(f"{sha}:{p}\n" for p in paths).encode()
        out = subprocess.run(["git", "cat-file", "--batch"], input=inp, capture_output=True, check=True).stdout
        res = []; k = 0
        while k < len(out):
            nl = out.index(b"\n", k); hdr = out[k:nl].split(); n = int(hdr[2]); res.append(out[nl + 1:nl + 1 + n]); k = nl + 1 + n + 1
        return res
    raw = {}
    for b in batch(fs):
        for line in b.decode("utf-8", "ignore").splitlines():
            if ",0050," in line:
                p = line.split(","); c = pd.to_numeric(p[8], errors="coerce")
                if c > 0:
                    raw[pd.Timestamp(p[1])] = c
    S = pd.read_csv(io.BytesIO(tshow(sha, "data/stocks/0050.csv")), dtype=str)
    for r in S.itertuples():
        c = pd.to_numeric(r.close, errors="coerce")
        if c > 0:
            raw[pd.Timestamp(r.date)] = c
    ev = []
    for b in batch(ex):
        for line in b.decode("utf-8", "ignore").splitlines():
            if ",0050," in line:
                p = line.split(","); ev.append((pd.Timestamp(p[0]), float(p[3]) / float(p[2])))
    A = pd.read_csv(io.BytesIO(tshow(sha, "data/adj/0050.csv")))
    ev += [(pd.Timestamp(d), float(f)) for d, f in zip(A["date"], A["factor"])]
    R = pd.Series(raw).sort_index()
    fac = pd.Series(1.0, index=R.index)
    for d, f in ev:
        fac[R.index < d] *= f
    Z = R * fac
    Z.attrs["info"] = f"0050 含息還原：{R.index[0].date()}～{R.index[-1].date()}，{len(R)} 日、事件 {len(ev)} 筆"
    return Z


def tri_at(T, d):
    k = int(T.index.searchsorted(pd.Timestamp(d), "right")) - 1
    return float(T.iloc[k])


def tw_cap(sha, sid, ym, early_days, cache):
    """燈亮月月底未還原收盤 × 當日發行股數（見 V9）。回 (市值, 日期, 收盤, 股數, 註)。"""
    p = pd.Period(ym, "M")
    if p.end_time < pd.Timestamp("2015-01-01"):
        days = [d for d in early_days if d.startswith(str(p))][::-1]
        last = None
        for d in days:
            if d not in cache:
                cache[d] = pd.read_csv(io.BytesIO(tshow(sha, f"data/early/daily/{d}.csv")), dtype=str).set_index("stock_id")
            E = cache[d]
            if sid in E.index:
                r = E.loc[sid]
                c = pd.to_numeric(r["close"], errors="coerce"); s = pd.to_numeric(r["shares"], errors="coerce")
                if np.isfinite(c) and c > 0:
                    if last is None:
                        last = (d, c, s)
                    if np.isfinite(s) and s > 0:
                        note = "" if d == last[0] else f"股數取 {d}"
                        return last[1] * s, last[0], last[1], s, "early/daily" + ("；" + note if note else "")
        return (np.nan, last[0], last[1], np.nan, "early/daily 股數空") if last else (np.nan, "", np.nan, np.nan, "early/daily 該月查無收盤")
    key = f"S{sid}"
    if key not in cache:
        raw = tshow(sha, f"data/stocks/{sid}.csv")
        cache[key] = pd.read_csv(io.BytesIO(raw), dtype=str) if raw else None
    S = cache[key]
    if S is None:
        return np.nan, "", np.nan, np.nan, "data/stocks 查無此檔"
    m = S[S["date"].str.startswith(str(p))].copy()
    m["c"] = pd.to_numeric(m["close"], errors="coerce"); m["s"] = pd.to_numeric(m["shares"], errors="coerce")
    m = m[m["c"] > 0]
    if not len(m):
        return np.nan, "", np.nan, np.nan, "data/stocks 該月查無收盤"
    r = m.iloc[-1]; ss = m[m["s"] > 0]
    if not len(ss):
        return np.nan, r["date"], r["c"], np.nan, "data/stocks 該月股數空"
    s = ss.iloc[-1]
    return r["c"] * s["s"], r["date"], r["c"], s["s"], "data/stocks" + ("" if s["date"] == r["date"] else f"；股數取 {s['date']}")


def tw_rows(pairs, eng):
    sha, PX, O, nseam, T, Z = eng
    CAL, ix, C, BAD, VP, LASTV, TRD = PX["CAL"], PX["ix"], PX["C"], PX["BAD"], PX["VP"], PX["LASTV"], PX["TRD"]
    CEND = len(CAL) - 1
    ADJ = {}

    def lastvalid_le(i, x):
        vp = VP[i]; k = int(np.searchsorted(vp, x, "right")) - 1
        return int(vp[k]) if k >= 0 else -1

    def opened(i, p):
        return bool(TRD[i, p] and np.isfinite(O[i, p]) and O[i, p] > 0 and np.isfinite(C[i, p]))

    def adj_events(sid):
        if sid not in ADJ:
            t = tshow(sha, f"data/adj/{sid}.csv")
            ADJ[sid] = {} if t is None else {pd.Timestamp(r["date"]): r for _, r in pd.read_csv(io.BytesIO(t), dtype=str).iterrows()
                                             if r["event"] in ("reduce", "parvalue")}
        return ADJ[sid]

    def bridge(i, sid, e, xe):
        k = 1.0; info = []
        for b in (e + 1 + np.flatnonzero(BAD[i, e + 1:xe + 1])):
            b = int(b); ev = adj_events(sid).get(CAL[b]); pb = lastvalid_le(i, b - 1)
            if ev is None or pb < e or not np.isfinite(C[i, b]):
                return None, f"壞根 {CAL[b].date()} 非減資／面額變更事件"
            rb = TS.raw_close(PX["main_data"] if b >= PX["NE"] else PX["early_data"], sid, CAL[b])
            rp = TS.raw_close(PX["main_data"] if pb >= PX["NE"] else PX["early_data"], sid, CAL[pb])
            g = rb / float(ev["ref_price"]) * float(ev["pre_close"]) / rp
            if not np.isfinite(g) or g <= 0:
                return None, f"壞根 {CAL[b].date()} 接續倍數不可算"
            k = k * (C[i, pb] * g) / C[i, b]
            info.append(f"{CAL[b].date()} {ev['event']}")
        return k, "；".join(info)

    rows = []
    for base in pairs:
        sid = base["代號"]
        if sid not in ix:
            for H in HS:
                rows.append({**base, "H月": H, "狀態": "資料不足(面板查無)"})
            continue
        i = ix[sid]
        p0 = int(CAL.searchsorted((pd.Period(base["燈亮月"], "M") + 1).to_timestamp()))
        e = p0
        while e <= CEND and not opened(i, e):
            e += 1
        if e > CEND:
            for H in HS:
                rows.append({**base, "H月": H, "狀態": "資料不足(進場後無成交)"})
            continue
        P0 = float(O[i, e]); tri0 = tri_at(T, CAL[e - 1]); z0 = tri_at(Z, CAL[e - 1])
        lastv = int(LASTV[i]); delist = (CEND - lastv) >= 5
        if lastv < e:
            for H in HS:
                rows.append({**base, "H月": H, "狀態": "資料不足(進場後無有效K棒)"})
            continue
        for H in HS:
            tgt = CAL[e] + pd.DateOffset(months=H)
            notyet = tgt > CAL[CEND]
            x = CEND if notyet else int(CAL.searchsorted(tgt, "right")) - 1
            bb = np.flatnonzero(BAD[i, e + 1:x + 1])
            st = "未到判決日" if notyet else "完整"; bad_d = ""
            if len(bb):
                b = e + 1 + int(bb[0]); bad_d = str(CAL[b].date()); xe = lastvalid_le(i, b - 1); st = "⚠壞根截斷" + ("＋未到判決日" if notyet else "")
            elif delist and lastv < x:
                xe = lastv; st = "下市結算"
            else:
                xe = lastvalid_le(i, x)
            R = float(C[i, xe] / P0 - 1 - COST_TW); M = tri_at(T, CAL[xe]) / tri0 - 1
            row = {**base, "H月": H, "進場日": str(CAL[e].date()), "進場順延日": e - p0, "判決目標日": str(tgt.date()), "結算日": str(CAL[xe].date()),
                   "狀態": st, "壞根日": bad_d, "R": R, "大盤": M, "超額": R - M}
            M5 = tri_at(Z, CAL[xe]) / z0 - 1
            row.update({"0050": M5, "超額0050": R - M5})
            if len(bb):
                xq = lastv if (delist and lastv < x) else lastvalid_le(i, x)
                k, note = bridge(i, sid, e, xq)
                row["接續註"] = note
                if k is not None:
                    Rb = float(C[i, xq] * k / P0 - 1 - COST_TW); Mb = tri_at(T, CAL[xq]) / tri0 - 1; Mb5 = tri_at(Z, CAL[xq]) / z0 - 1
                    row.update({"接續R": Rb, "接續大盤": Mb, "接續超額": Rb - Mb, "接續結算日": str(CAL[xq].date()), "接續超額0050": Rb - Mb5})
            rows.append(row)
    return rows


# ═════════════ 美股 ═════════════
class US:
    def __init__(self):
        self.sha = subprocess.run(["git", "-C", US_REPO, "rev-parse", "origin/main"], capture_output=True, text=True, check=True).stdout.strip()
        G = pd.read_csv(io.BytesIO(gshow("data/macro/yahoo_SP500TR.csv", US_REPO)), dtype={"date": str})
        G["date"] = pd.to_datetime(G["date"]); G["adjclose"] = pd.to_numeric(G["adjclose"], errors="coerce")
        self.G = G[G["adjclose"] > 0].drop_duplicates("date").sort_values("date").set_index("date")["adjclose"]
        GS = pd.read_csv(io.BytesIO(gshow("data/macro/yahoo_GSPC.csv", US_REPO)), dtype={"date": str})
        self.UCAL = pd.DatetimeIndex(pd.to_datetime(GS["date"])).sort_values().unique()
        SO = pd.read_csv(io.BytesIO(gshow("data/fundamentals/shares_outstanding.csv", US_REPO)), dtype=str)
        SO["as_of_date"] = pd.to_datetime(SO["as_of_date"], errors="coerce"); SO["shares"] = pd.to_numeric(SO["shares"], errors="coerce")
        self.SO = SO.dropna(subset=["as_of_date", "shares"])
        self.cache = {}

    def tr_at(self, d):
        k = int(self.G.index.searchsorted(pd.Timestamp(d), "right")) - 1
        return float(self.G.iloc[k])

    def load(self, tk, need=None):
        """回 (DataFrame[date, adjopen, adjclose, rawclose], 來源) 或 (None, 原因)。
        來源順序 prices_yahoo → prices → extra_yahoo；need（進場日）給定時取第一個起點 ≤ need 的來源（都不夠早 ⇒ 回第一個有的來源）。"""
        cands = [s for s in (self._load(tk, "prices_yahoo"), self._load(tk, "prices"), self._load(tk, "extra_yahoo")) if s[0] is not None]
        if not cands:
            return None, "私有庫查無此檔"
        if need is not None:
            for s in cands:
                if s[0]["date"].iloc[0] <= need:
                    return s
        return cands[0]

    def _load(self, tk, src):
        key = (tk, src)
        if key in self.cache:
            return self.cache[key]
        self.cache[key] = (None, "")
        if not tk:
            return self.cache[key]
        if src in ("prices_yahoo", "extra_yahoo"):
            raw = gshow(f"data/prices_yahoo/{tk}.csv" if src == "prices_yahoo" else f"data/extra_yahoo/yahoo_{tk}.csv", US_REPO)
            if raw is None:
                return self.cache[key]
            P = pd.read_csv(io.BytesIO(raw), dtype={"date": str}); P["date"] = pd.to_datetime(P["date"])
            for c in ("open", "close", "adjclose"):
                P[c] = pd.to_numeric(P[c], errors="coerce")
            P = P[(P["close"] > 0) & (P["adjclose"] > 0) & (P["open"] > 0)].drop_duplicates("date").sort_values("date").reset_index(drop=True)
            ev = gshow(f"data/events_yahoo/{tk}.csv" if src == "prices_yahoo" else f"data/extra_yahoo/yahoo_events_{tk}.csv", US_REPO)
            sp = []
            if ev is not None:
                E = pd.read_csv(io.BytesIO(ev), dtype=str).drop_duplicates()
                for r in E[E["type"] == "split"].itertuples():
                    a, b = r.value.split("/"); sp.append((pd.Timestamp(r.date), float(a) / float(b)))
            fac = np.ones(len(P))
            for d, rto in sp:
                fac[P["date"].to_numpy() < np.datetime64(d)] *= rto
            out = pd.DataFrame({"date": P["date"], "adjopen": P["open"] * P["adjclose"] / P["close"], "adjclose": P["adjclose"], "rawclose": P["close"] * fac})
            self.cache[key] = (out, src)
            return self.cache[key]
        raw = gshow(f"data/prices/{tk}.csv", US_REPO)
        if raw is not None:
            P = pd.read_csv(io.BytesIO(raw), dtype={"date": str}); P["date"] = pd.to_datetime(P["date"])
            for c in ("close", "adjOpen", "adjClose"):
                P[c] = pd.to_numeric(P[c], errors="coerce")
            P = P[(P["close"] > 0) & (P["adjClose"] > 0) & (P["adjOpen"] > 0)].drop_duplicates("date").sort_values("date").reset_index(drop=True)
            out = pd.DataFrame({"date": P["date"], "adjopen": P["adjOpen"], "adjclose": P["adjClose"], "rawclose": P["close"]})
            self.cache[key] = (out, "prices")
        return self.cache[key]

    def cap(self, tk, ym):
        P, src = self.load(tk, (pd.Period(ym, "M")).start_time)
        if P is None:
            return np.nan, "", "價格查無"
        p = pd.Period(ym, "M")
        m = P[(P["date"] >= p.start_time) & (P["date"] <= p.end_time)]
        if not len(m):
            return np.nan, "", "該月查無收盤"
        r = m.iloc[-1]
        s = self.SO[(self.SO["ticker"] == tk) & (self.SO["as_of_date"] <= r["date"])]
        if not len(s):
            return np.nan, str(r["date"].date()), "SEC 股數查無"
        d = s["as_of_date"].max()
        if (r["date"] - d).days > 400:
            return np.nan, str(r["date"].date()), f"SEC 股數最近 {d.date()}（>400 日）"
        sh = s[s["as_of_date"] == d].drop_duplicates(["share_class", "shares"])["shares"].sum()
        return float(r["rawclose"] * sh), str(r["date"].date()), f"{src}；股數 as_of {d.date()}"

    def rows(self, pairs):
        rows = []
        for base in pairs:
            tk = base["代號"]
            ent = (pd.Period(base["燈亮月"], "M") + 1).to_timestamp()
            P, src = self.load(tk, ent)
            if P is None:
                for H in HS:
                    rows.append({**base, "H月": H, "狀態": "資料不足(私有庫查無此檔)"})
                continue
            base = {**base, "價格來源": src}
            for t_, d_, why in SPECIAL_BEFORE:
                if tk == t_ and ent < pd.Timestamp(d_):
                    base["註"] = (base.get("註", "") + f"⚠進場在 {d_} 前（{why}）").strip()
            if ent < P["date"].iloc[0]:
                for H in HS:
                    rows.append({**base, "H月": H, "狀態": f"資料不足(燈亮早於資料起點 {P['date'].iloc[0].date()})"})
                continue
            if ent > P["date"].iloc[-1]:
                for H in HS:
                    rows.append({**base, "H月": H, "狀態": "資料不足(進場前已無資料)"})
                continue
            cal = self.UCAL[(self.UCAL >= P["date"].iloc[0])]
            pos = {d: q for q, d in enumerate(cal)}
            Pp = P[P["date"].isin(pos)].copy(); Pp["q"] = Pp["date"].map(pos)
            q = Pp["q"].to_numpy(); gapbad = set(q[1:][np.diff(q) - 1 >= 5])
            e_i = int(Pp["date"].searchsorted(ent))
            e_row = Pp.iloc[e_i]; P0 = float(e_row["adjopen"])
            e_d = e_row["date"]; prev = cal[pos[e_d] - 1] if pos[e_d] > 0 else e_d
            tr0 = self.tr_at(prev); last_d = Pp["date"].iloc[-1]
            delist = (self.UCAL[-1] - last_d).days > 10
            for H in HS:
                tgt = e_d + pd.DateOffset(months=H)
                notyet = tgt > last_d and not delist
                sub = Pp[(Pp["date"] > e_d) & (Pp["date"] <= tgt)]
                st = "未到判決日" if notyet else "完整"; bad_d = ""
                bq = [qq for qq in sub["q"] if qq in gapbad]
                if bq:
                    bad_d = str(cal[bq[0]].date()); sub = sub[sub["q"] < bq[0]]; st = "⚠壞根截斷" + ("＋未到判決日" if notyet else "")
                elif delist and last_d < tgt:
                    st = "下市結算"
                xr = sub.iloc[-1] if len(sub) else e_row
                extra = {}
                if tk in ORSTED and xr["date"] > ORSTED_CUT:
                    # Ørsted 2025-09 配權 Yahoo 未還原 ⇒ 主值截在 2025-09-05；未截值只當參考
                    Rraw = float(xr["adjclose"] / P0 - 1 - COST_US); Mraw = self.tr_at(xr["date"]) / tr0 - 1
                    extra = {"未截R(參考)": Rraw, "未截超額(參考)": Rraw - Mraw, "未截結算日": str(xr["date"].date())}
                    sub2 = sub[sub["date"] <= ORSTED_CUT]; xr = sub2.iloc[-1] if len(sub2) else e_row
                    st = st + "；⚠Ørsted配權未還原、截 2025-09-05"
                R = float(xr["adjclose"] / P0 - 1 - COST_US); M = self.tr_at(xr["date"]) / tr0 - 1
                big = [f"{d.date()} {v * 100:+.0f}%" for d, v in zip(Pp["date"], Pp["adjclose"].pct_change())
                       if e_d < d <= xr["date"] and np.isfinite(v) and abs(v) > 0.4]
                rows.append({**base, **extra, "H月": H, "進場日": str(e_d.date()), "進場順延日": int(pos[e_d] - int(np.searchsorted(cal, ent))),
                             "判決目標日": str(tgt.date()), "結算日": str(xr["date"].date()), "狀態": st, "壞根日": bad_d, "R": R, "大盤": M, "超額": R - M,
                             "單日>40%": "；".join(big)})
        return rows


# ═════════════ 成員 ═════════════
def build_members(CS, P, caps):
    M = []
    for _, r in CS.iterrows():
        mk = r["市場"]; cid = r["id"]
        M.append({"版": "代表股版", "id": cid, "市場": mk, "代號": code_of(r), "名稱": r["公司"], "名次": "", "角色": "代表股", "入選": True, "註": ""})
        d = P[mk][P[mk]["id"] == cid]
        d = d[d["代號"].str.strip() != ""]
        for k, (_, p) in enumerate(d.iterrows()):
            M.append({"版": "同業等權版", "id": cid, "市場": mk, "代號": p["代號"].strip(), "名稱": p["名稱"], "名次": p["名次"], "角色": f"名次{p['名次']}",
                      "入選": k < 3, "註": "" if k < 3 else "名次 4 以後"})
        n = 0
        for _, p in d.iterrows():
            c = caps.get((cid, p["代號"].strip()), {})
            v = c.get("市值", np.nan)
            if np.isfinite(v) and v < FLOOR[mk]:
                flag, inn = "市值不足、剔除", False
            elif np.isfinite(v):
                flag, inn = "過下限", n < 3
            else:
                flag, inn = "查無、未剔除", n < 3
            if inn:
                n += 1
            M.append({"版": "設下限版", "id": cid, "市場": mk, "代號": p["代號"].strip(), "名稱": p["名稱"], "名次": p["名次"], "角色": f"名次{p['名次']}",
                      "入選": inn, "註": flag if (inn or flag != "過下限") else "名額已滿"})
    return pd.DataFrame(M)


# ═════════════ 統計 ═════════════
def themes(TB, MB):
    ok = TB[TB["R"].notna()].copy()
    xb = ok["接續超額"].where(ok["狀態"].fillna("").str.contains("壞根") & ok["接續超額"].notna(), ok["超額"]) if "接續超額" in ok else ok["超額"]
    ok["xb"] = xb
    ok["xb5"] = ok["接續超額0050"].where(ok["狀態"].fillna("").str.contains("壞根") & ok["接續超額0050"].notna(), ok["超額0050"])
    out = []
    for v in VARS:
        mem = MB[(MB["版"] == v) & MB["入選"]][["id", "代號"]]
        d = ok.merge(mem, on=["id", "代號"])
        d["版"] = v
        g = d.groupby(["版", "市場", "id", "H月"])
        TH = g.agg(結果=("結果", "first"), 產業=("產業", "first"), 代表股=("代表股", "first"), 燈亮月=("燈亮月", "first"),
                   檔數=("代號", "size"), 各檔=("代號", lambda s: "／".join(s)), 等權R=("R", "mean"), 合計R=("R", "sum"), 等權大盤=("大盤", "mean"),
                   等權超額=("超額", "mean"), 合計超額=("超額", "sum"), 接續等權超額=("xb", "mean"),
                   等權0050=("0050", "mean"), 等權超額0050=("超額0050", "mean"), 接續等權超額0050=("xb5", "mean"),
                   未到=("狀態", lambda s: int(s.str.contains("未到").any())), 截斷=("狀態", lambda s: int(s.str.contains("壞根").any()))).reset_index()
        out.append(TH)
        # 每檔
    TH = pd.concat(out, ignore_index=True)
    each = []
    for v in VARS:
        mem = MB[(MB["版"] == v) & MB["入選"]][["id", "代號"]]
        d = ok.merge(mem, on=["id", "代號"]); d["版"] = v; each.append(d)
    return TH, pd.concat(each, ignore_index=True)


def be(W, L):
    if not (np.isfinite(W) and np.isfinite(L)):
        return np.nan, np.nan, "不可算"
    if L >= 0:
        return np.nan, np.nan, "反例平均為正、兩平不適用" if L > 0 else "反例為 0、兩平不適用"
    if W <= 0:
        return np.nan, np.nan, "贏家不為正、無兩平"
    p = -L / (W - L)
    return p, math.ceil(math.log(0.1) / math.log(1 - p)), ""


def stats(TH, EA):
    out = []
    for v in VARS:
        for mk in ("TW", "US"):
            for H in HS:
                for unit, D in (("主題", TH), ("每檔", EA)):
                    d = D[(D["版"] == v) & (D["市場"] == mk) & (D["H月"] == H)]
                    for met in ("超額", "R", "接續超額", "超額0050", "接續超額0050"):
                        if mk == "US" and met.endswith("0050"):
                            continue
                        c = ({"超額": "等權超額", "R": "等權R", "接續超額": "接續等權超額", "超額0050": "等權超額0050", "接續超額0050": "接續等權超額0050"}[met] if unit == "主題"
                             else {"超額": "超額", "R": "R", "接續超額": "xb", "超額0050": "超額0050", "接續超額0050": "xb5"}[met])
                        w = d[d["結果"] == "大漲"][c].astype(float); l = d[d["結果"] == "失敗"][c].astype(float)
                        rec = {"版": v, "市場": mk, "H月": H, "樣本單位": unit, "量": met, "贏家n": len(w), "反例n": len(l),
                               "贏家平均": w.mean(), "贏家中位": w.median(), "反例平均": l.mean(), "反例中位": l.median(),
                               "反例μ": l.mean(), "反例s": l.std(ddof=1) if len(l) > 1 else np.nan}
                        rec["門檻μ−1.28s/√8"] = rec["反例μ"] - 1.28 * rec["反例s"] / math.sqrt(8) if np.isfinite(rec["反例s"]) else np.nan
                        for k in ("平均", "中位"):
                            p, n, why = be(rec[f"贏家{k}"], rec[f"反例{k}"])
                            rec[f"p*_{k}"] = p; rec[f"n_{k}"] = n; rec[f"註_{k}"] = why
                        if unit == "主題":
                            rec["未到判決日主題數"] = int(d["未到"].sum()); rec["壞根截斷主題數"] = int(d["截斷"].sum())
                        else:
                            rec["未到判決日主題數"] = int(d["狀態"].str.contains("未到").sum()); rec["壞根截斷主題數"] = int(d["狀態"].str.contains("壞根").sum())
                        out.append(rec)
    return pd.DataFrame(out)


def main():
    t0 = time.time(); os.makedirs(OUT, exist_ok=True)
    CS = load_cases(); P = load_peers()
    # 要算的 (id, 代號) 對：代表股 ∪ 名單
    pairs = {}
    for _, r in CS.iterrows():
        base = {"id": r["id"], "市場": r["市場"], "結果": r["結果"], "型": r["型"], "產業": r["產業"], "代表股": r["公司"], "燈亮月": r["燈亮月"]}
        codes = [code_of(r)] + [c.strip() for c in P[r["市場"]][P[r["市場"]]["id"] == r["id"]]["代號"] if c.strip()]
        for c in codes:
            pairs.setdefault((r["id"], c), {**base, "代號": c})
    meta = {"K21": K21NOTE, "名單品質": QUAL}
    eng = tw_engine(); sha = eng[0]
    meta.update({"tw_sha": sha, "tw資料尾": str(eng[1]["CAL"][-1].date()), "接縫開盤倍數檔數": eng[3], "0050": eng[5].attrs["info"]})
    T = eng[4]; gp = pd.Series(T.index).diff().dt.days
    meta["大盤"] = (f"data/history/market_tri.csv（發行量加權股價報酬指數）{T.index[0].date()}～{T.index[-1].date()}，{len(T)} 日；"
                  f"最長日期間隔 {int(gp.max())} 日（{T.index[int(gp.idxmax())].date()} 前，春節），無缺段、未補值")
    us = US(); meta["us_sha"] = us.sha
    rows = tw_rows([b for k, b in pairs.items() if b["市場"] == "TW"], eng); log(f"[台股] {time.time() - t0:.0f}s")
    rows += us.rows([b for k, b in pairs.items() if b["市場"] == "US"]); log(f"[美股] {time.time() - t0:.0f}s")
    # 市值（只對名單成員）
    early_days = sorted(x.rsplit("/", 1)[1][:-4] for x in subprocess.run(["git", "ls-tree", "--name-only", sha, "data/early/daily/"],
                                                                              capture_output=True, text=True, check=True).stdout.split())
    cache = {}; caps = {}; CR = []
    for mk in ("TW", "US"):
        for _, p in P[mk].iterrows():
            c = p["代號"].strip()
            if not c:
                continue
            ym = CS.set_index("id").loc[p["id"], "燈亮月"]
            if mk == "TW":
                v, d, cl, sh, note = tw_cap(sha, c, ym, early_days, cache)
                CR.append({"id": p["id"], "市場": mk, "代號": c, "名稱": p["名稱"], "名次": p["名次"], "燈亮月": ym, "月底日": d, "未還原收盤": cl, "股數": sh,
                           "市值(億)": v / 1e8 if np.isfinite(v) else np.nan, "判定": ("查無" if not np.isfinite(v) else ("≥100億" if v >= FLOOR[mk] else "＜100億")), "來源註": note})
            else:
                v, d, note = us.cap(c, ym)
                CR.append({"id": p["id"], "市場": mk, "代號": c, "名稱": p["名稱"], "名次": p["名次"], "燈亮月": ym, "月底日": d,
                           "判定": ("查無" if not np.isfinite(v) else ("≥20億美元" if v >= FLOOR[mk] else "＜20億美元")), "來源註": note})
            caps[(p["id"], c)] = {"市值": v}
    CRd = pd.DataFrame(CR); CRd.to_csv(os.path.join(OUT, "caps.csv"), index=False, encoding="utf-8-sig")
    MB = build_members(CS, P, caps); MB.to_csv(os.path.join(OUT, "members.csv"), index=False, encoding="utf-8-sig")
    TB = pd.DataFrame(rows)
    cols = ["id", "市場", "結果", "型", "產業", "代表股", "代號", "燈亮月", "H月", "進場日", "進場順延日", "判決目標日", "結算日", "狀態", "壞根日",
            "R", "大盤", "超額", "接續R", "接續大盤", "接續超額", "接續結算日", "接續註", "0050", "超額0050", "接續超額0050",
            "價格來源", "註", "單日>40%", "未截R(參考)", "未截超額(參考)", "未截結算日"]
    TB = TB.reindex(columns=cols)
    TB.to_csv(os.path.join(OUT, "table.csv"), index=False, encoding="utf-8-sig")
    TH, EA = themes(TB, MB); TH.to_csv(os.path.join(OUT, "themes.csv"), index=False, encoding="utf-8-sig")
    ST = stats(TH, EA); ST.to_csv(os.path.join(OUT, "stats.csv"), index=False, encoding="utf-8-sig")
    write_md(TB, TH, ST, MB, CRd, meta)
    MJ = {"性質": "v4.1 新設定重算（描述、不判定、不計 N）", "警語": WARN, "請求": "產業分析線 seq30、seq34、seq37、seq38", **meta,
          "列數": len(TB), "可算列": int(TB["R"].notna().sum()), "stats": ST.to_dict("records"), "讀法": __doc__.split("═══ 讀法")[1], "秒": round(time.time() - t0)}
    json.dump(MJ, open(os.path.join(OUT, "main.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=lambda o: (None if not np.isfinite(o) else float(o)) if isinstance(o, (np.floating, np.integer, float)) else str(o))
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    log(f"[完成] {OUT}｜{time.time() - t0:.0f}s")


def f2(v):
    return "—" if v is None or not np.isfinite(v) else f"{v:+.2f}"


def pc(v):
    return "—" if v is None or not np.isfinite(v) else f"{v * 100:.1f}%"


def ni(v):
    return "—" if v is None or not np.isfinite(v) else str(int(v))


def sget(ST, v, mk, H, unit="主題", met="超額"):
    s = ST[(ST["版"] == v) & (ST["市場"] == mk) & (ST["H月"] == H) & (ST["樣本單位"] == unit) & (ST["量"] == met)]
    return s.iloc[0]


def write_md(TB, TH, ST, MB, CR, meta):
    md = [f"{WARN}", "", "# 大漲主題框架 v4.1 新設定重算：代表股版／同業等權版／設下限版（產業分析線 seq30／34／37／38）", "",
          f"> ⚠ **{QUAL}**", "", f"- {K21NOTE}",
          "- 描述、⛔ 不判定、不計 N、不改任何規則。單位「份」＝每檔 1 份的損益倍數（R＝判決還原價÷進場還原價−1，含息、扣成本：台股 0.585% 來回、美股 0.05%／邊）；"
          "表內數字為**對大盤含息超額**（括號為原始 R）。",
          f"- ⭐ 基準（產業 seq40、使用者 10/25 14:26「我們現在基礎的是大盤」）：**台股主數字＝對大盤（{meta.get('大盤', '')}）**；0050 含息版留作副欄（{meta.get('0050', '')}）。美股 ^SP500TR。",
          "- 進場＝燈亮月下一個月第一個交易日還原開盤；判決日＝進場日＋60 個月（主表）／72 個月（副欄）；資料不夠 ⇒ 結算到資料尾、標「未到判決日」。持有期間不模擬 v4 出場 ①～⑤。",
          "- 三版：**代表股版**＝燈 1 點名公司 1 檔；**同業等權版**＝名單前 3 名（實際幾家算幾家）等權；**設下限版**＝燈亮月月底市值 台股 ≥100 億元、美股 ≥20 億美元，"
          "不足剔除、名單內下一名遞補（名單都 ≤3 家 ⇒ 實際上只會少一家），市值算不出照標「查無、未剔除」。",
          "- 口徑（回測線定）：**同一主題的 3 檔算 1 個獨立樣本**（主題內等權平均＝該主題的值）；另附「每檔各算 1 張」版。名單內查不到價格的代號標「資料不足」、⛔ 不換代號，主題值只用有價格的成員。",
          "- 兩平 p*＝−L÷(W−L)；停用張數 n＝⌈ln0.1÷ln(1−p*)⌉；反例 μ、s（ddof=1）、門檻 μ−1.28·s／√8。",
          "- 市值：台股＝燈亮月最後一個有收盤日的未還原收盤 × 當日發行股數（≤2014 data/early/daily、≥2015 data/stocks 的 shares 欄＝日檔 feed 當日股數）；"
          "美股＝未還原收盤（Yahoo 拆股調整還原）× SEC 申報股數（as_of ≤ 月底最後一筆）。⛔ 美股不放價格與市值數值，只放判定。",
          f"- 資料：台股 sha {str(meta.get('tw_sha', ''))[:12]}（面板尾 {meta.get('tw資料尾', '')}）；美股 us-stock-data {str(meta.get('us_sha', ''))[:12]}。", ""]
    # 三欄對照
    md += ["## 三版對照（主題為 1 個樣本；台股對大盤＝發行量加權股價報酬指數、美股對 ^SP500TR，含息超額，單位份）", ""]
    for H in (60, 72):
        md += [f"### {H} 個月", "", "| 市場 | 項目 | 代表股版 | 同業等權版 | 設下限版 |", "|---|---|---|---|---|"]
        for mk in ("TW", "US"):
            S = [sget(ST, v, mk, H) for v in VARS]
            def pp(s, k):
                return pc(s[f"p*_{k}"]) + f"（n {ni(s[f'n_{k}'])}）" if np.isfinite(s[f"p*_{k}"]) else s[f"註_{k}"]
            md += [f"| {mk} | 贏家 平均／中位（主題數） | " + " | ".join(f"{f2(s['贏家平均'])}／{f2(s['贏家中位'])}（{s['贏家n']}）" for s in S) + " |",
                   f"| {mk} | 反例 平均／中位（主題數） | " + " | ".join(f"{f2(s['反例平均'])}／{f2(s['反例中位'])}（{s['反例n']}）" for s in S) + " |",
                   f"| {mk} | 兩平 p* 平均口徑（停用張數） | " + " | ".join(pp(s, "平均") for s in S) + " |",
                   f"| {mk} | 兩平 p* 中位口徑（停用張數） | " + " | ".join(pp(s, "中位") for s in S) + " |",
                   f"| {mk} | 反例 μ／s／門檻 | " + " | ".join(f"{f2(s['反例μ'])}／{f2(s['反例s'])}／{f2(s['門檻μ−1.28s/√8'])}" for s in S) + " |",
                   f"| {mk} | 未到判決日／壞根截斷 主題數 | " + " | ".join(f"{s['未到判決日主題數']}／{s['壞根截斷主題數']}" for s in S) + " |"]
        md.append("")
    md += ["## 副欄：台股對 0050 含息（主題為 1 個樣本）", "", "| 月 | 項目 | 代表股版 | 同業等權版 | 設下限版 |", "|---|---|---|---|---|"]
    for H in (60, 72, 36, 24):
        for met, lab in (("超額0050", ""), ("接續超額0050", "接續版 ")):
            S = [sget(ST, v, "TW", H, "主題", met) for v in VARS]

            def pp5(s, k):
                return pc(s[f"p*_{k}"]) + f"（n {ni(s[f'n_{k}'])}）" if np.isfinite(s[f"p*_{k}"]) else s[f"註_{k}"]
            md += [f"| {H} | {lab}贏家 平均／中位 | " + " | ".join(f"{f2(s['贏家平均'])}／{f2(s['贏家中位'])}" for s in S) + " |",
                   f"| {H} | {lab}反例 平均／中位 | " + " | ".join(f"{f2(s['反例平均'])}／{f2(s['反例中位'])}" for s in S) + " |",
                   f"| {H} | {lab}p* 平均（n）／中位（n） | " + " | ".join(f"{pp5(s, '平均')}／{pp5(s, '中位')}" for s in S) + " |",
                   f"| {H} | {lab}反例 μ／s／門檻 | " + " | ".join(f"{f2(s['反例μ'])}／{f2(s['反例s'])}／{f2(s['門檻μ−1.28s/√8'])}" for s in S) + " |"]
    # 差最多的格
    D = []
    for v in VARS:
        for H in HS:
            for unit in ("主題", "每檔"):
                for a_, b_, lab in (("超額", "超額0050", ""), ("接續超額", "接續超額0050", "接續版 ")):
                    s = sget(ST, v, "TW", H, unit, a_); t = sget(ST, v, "TW", H, unit, b_)
                    for f in ("贏家平均", "贏家中位", "反例平均", "反例中位", "反例s", "門檻μ−1.28s/√8", "p*_平均", "p*_中位"):
                        if np.isfinite(s[f]) and np.isfinite(t[f]):
                            D.append((abs(s[f] - t[f]), f"{v} {H} 月 {unit} {lab}{f}", s[f], t[f], f.startswith("p*")))
    D.sort(key=lambda z: -z[0])
    md += ["", "### 大盤版 vs 0050 版差最多的 12 格（份；p* 為百分點）", ""]
    md += [f"- {lab}：大盤 {pc(a) if isp else f2(a)}／0050 {pc(b) if isp else f2(b)}（差 {(a - b) * 100:+.1f} 個百分點）" if isp else
           f"- {lab}：大盤 {f2(a)}／0050 {f2(b)}（差 {a - b:+.2f}）" for _, lab, a, b, isp in D[:12]]
    md.append("")
    md += ["## 詳表（每版 × 市場 × 判決月；主題／每檔兩種單位；超額，括號原始 R）", "",
           "| 版 | 市場 | 月 | 單位 | 贏家 n | 贏家平均 | 贏家中位 | 反例 n | 反例平均 | 反例中位 | p* 平均（n） | p* 中位（n） | μ | s | 門檻 | 未到 |", "|" + "---|" * 16]
    for v in VARS:
        for mk in ("TW", "US"):
            for H in (60, 72, 36, 24):
                for unit in ("主題", "每檔"):
                    s = sget(ST, v, mk, H, unit); r_ = sget(ST, v, mk, H, unit, "R")
                    pa = f"{pc(s['p*_平均'])}（{ni(s['n_平均'])}）" if np.isfinite(s["p*_平均"]) else s["註_平均"]
                    pm = f"{pc(s['p*_中位'])}（{ni(s['n_中位'])}）" if np.isfinite(s["p*_中位"]) else s["註_中位"]
                    md.append(f"| {v} | {mk} | {H} | {unit} | {s['贏家n']} | {f2(s['贏家平均'])}（{f2(r_['贏家平均'])}） | {f2(s['贏家中位'])}（{f2(r_['贏家中位'])}） | {s['反例n']} | "
                              f"{f2(s['反例平均'])}（{f2(r_['反例平均'])}） | {f2(s['反例中位'])}（{f2(r_['反例中位'])}） | {pa} | {pm} | {f2(s['反例μ'])} | {f2(s['反例s'])} | "
                              f"{f2(s['門檻μ−1.28s/√8'])} | {s['未到判決日主題數']} |")
    md += ["", "## 台股接續版（壞根截斷格改用減資／面額變更接續值；參考）", ""]
    for v in VARS:
        for H in (60, 72):
            s = sget(ST, v, "TW", H, "主題", "接續超額")
            pa = f"{pc(s['p*_平均'])}（n {ni(s['n_平均'])}）" if np.isfinite(s["p*_平均"]) else s["註_平均"]
            pm = f"{pc(s['p*_中位'])}（n {ni(s['n_中位'])}）" if np.isfinite(s["p*_中位"]) else s["註_中位"]
            md.append(f"- {v} {H} 月：贏家 {f2(s['贏家平均'])}／{f2(s['贏家中位'])}、反例 {f2(s['反例平均'])}／{f2(s['反例中位'])}；p* 平均 {pa}、中位 {pm}；μ {f2(s['反例μ'])}、s {f2(s['反例s'])}、門檻 {f2(s['門檻μ−1.28s/√8'])}")
    # 美股補價
    U = TB[(TB["市場"] == "US") & (TB["價格來源"] == "extra_yahoo")]
    md += ["", "## 美股補價（資料庫 0253：us-stock-data data/extra_yahoo/，⛔ 不放價格）", "",
           f"- 用 extra_yahoo 的檔次：{'、'.join(sorted(set(U['id'] + ' ' + U['代號'])))}（prices_yahoo 起點晚於進場的 DDD、FSLR 改用 extra_yahoo）；LAZR 仍查無。",
           "- K39 Ørsted：代表股與名單都用美元 ADR DNNGY（丹麥 ORSTED_CO 為 DKK，不用）。2025-09 配權 Yahoo 未還原 ⇒ 跨過的格主值**截在 2025-09-05**、標 ⚠，未截值放 table.csv「未截R(參考)」。"]
    for _, r in TB[(TB["市場"] == "US") & (TB["H月"].isin([60, 72])) & TB["狀態"].fillna("").str.contains("Ørsted")].iterrows():
        md.append(f"  - {r['id']} {r['代號']} {r['H月']} 月：截值 R {f2(r['R'])}、超額 {f2(r['超額'])}（{r['結算日']}）；未截參考 R {f2(r['未截R(參考)'])}、超額 {f2(r['未截超額(參考)'])}（{r['未截結算日']}）")
    fl = TB[(TB["市場"] == "US") & TB["註"].fillna("").ne("")].drop_duplicates(["id", "代號"])
    md.append("- SPAC／OTC 前價：" + ("；".join(f"{r.id} {r.代號} {r.註}" for r in fl.itertuples()) or "本樣本進場都在 CHPT、LCID 合併與 CGC 轉主板之後，無格受影響"))
    bg = TB[(TB["市場"] == "US") & (TB["H月"] == 72) & TB["單日>40%"].fillna("").ne("")]
    md.append("- 持有期間單日漲跌 >40%（72 月窗內，還原價）：" + ("；".join(f"{r['id']} {r['代號']}：{r['單日>40%']}" for _, r in bg.iterrows()) or "無"))
    # 成員與剔除
    md += ["", "## 成員、資料不足與規模剔除", ""]
    nod = TB[(TB["H月"] == 60) & TB["R"].isna()]
    md.append(f"- 查不到價格（資料不足）：{len(nod)} 檔次——" + "；".join(f"{r.id} {r.代號}（{r.狀態}）" for r in nod.itertuples()))
    cut = MB[(MB["版"] == "設下限版") & (MB["註"] == "市值不足、剔除")]
    md.append(f"- 設下限剔除：{len(cut)} 檔——" + "；".join(f"{r.id} {r.代號}" for r in cut.itertuples()))
    unk = MB[(MB["版"] == "設下限版") & (MB["註"] == "查無、未剔除")]
    md.append(f"- 市值查無、未剔除：{len(unk)} 檔——" + "；".join(f"{r.id} {r.代號}" for r in unk.itertuples()))
    for v in VARS[1:]:
        for mk in ("TW", "US"):
            ids = set(TB[TB["市場"] == mk]["id"]); have = set(TH[(TH["版"] == v) & (TH["市場"] == mk) & (TH["H月"] == 60)]["id"])
            miss = sorted(ids - have)
            md.append(f"- {v} {mk}：可算主題 {len(have)}／{len(ids)}；不進統計：{('、'.join(miss)) or '無'}")
    dl = TB[TB["進場順延日"].fillna(0) > 0].drop_duplicates(["id", "代號"])
    md.append("- 進場順延：" + ("；".join(f"{r.id} {r.代號} 順延 {int(r.進場順延日)} 日到 {r.進場日}" for r in dl.itertuples()) or "無"))
    # 每主題一列
    md += ["", "## 每主題一列（60 月；括號 72 月；超額＝對大盤）", "",
           "| id | 市場 | 結果 | 產業 | 燈亮月 | 代表股 R | 同業各檔 R（60 月） | 同業等權 R | 同業合計 R | 同業等權超額 | 設下限成員 | 設下限等權超額 | 大盤同期 | 狀態 |", "|" + "---|" * 14]
    for cid in TB["id"].drop_duplicates():
        a = TB[(TB["id"] == cid)]
        r0 = a.iloc[0]

        def th(v, H, c):
            q = TH[(TH["版"] == v) & (TH["id"] == cid) & (TH["H月"] == H)]
            return q.iloc[0][c] if len(q) else np.nan

        def thm(v):
            q = TH[(TH["版"] == v) & (TH["id"] == cid) & (TH["H月"] == 60)]
            return q.iloc[0]["各檔"] if len(q) else "—"
        rep = MB[(MB["版"] == "代表股版") & (MB["id"] == cid)].iloc[0]["代號"]
        rr = a[(a["代號"] == rep)]
        r60 = rr[rr["H月"] == 60]["R"]; r72 = rr[rr["H月"] == 72]["R"]
        pm = MB[(MB["版"] == "同業等權版") & (MB["id"] == cid) & MB["入選"]]["代號"].tolist()
        each = "／".join(f"{c} " + (f2(a[(a['代號'] == c) & (a['H月'] == 60)]['R'].iloc[0]) if len(a[(a['代號'] == c) & (a['H月'] == 60)]) and np.isfinite(a[(a['代號'] == c) & (a['H月'] == 60)]['R'].iloc[0]) else "資料不足") for c in pm)
        stt = "；".join(sorted(set(a[(a["H月"] == 60) & a["代號"].isin(pm + [rep])]["狀態"].dropna())))
        md.append(f"| {cid} | {r0['市場']} | {r0['結果']} | {r0['產業']} | {r0['燈亮月']} | {f2(r60.iloc[0] if len(r60) else np.nan)}（{f2(r72.iloc[0] if len(r72) else np.nan)}） | {each} | "
                  f"{f2(th('同業等權版', 60, '等權R'))}（{f2(th('同業等權版', 72, '等權R'))}） | {f2(th('同業等權版', 60, '合計R'))}（{f2(th('同業等權版', 72, '合計R'))}） | "
                  f"{f2(th('同業等權版', 60, '等權超額'))}（{f2(th('同業等權版', 72, '等權超額'))}） | {thm('設下限版')} | "
                  f"{f2(th('設下限版', 60, '等權超額'))}（{f2(th('設下限版', 72, '等權超額'))}） | {f2(th('同業等權版', 60, '等權大盤'))} | {stt} |")
    md += ["", f"> ⚠ {QUAL}", "", f"{WARN}"]
    open(os.path.join(OUT, "summary.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")


if __name__ == "__main__":
    main()
