# -*- coding: utf-8 -*-
"""PREREG大師三套【仿 App 麥克墨菲／麥克喜偉／詹姆士歐沙那希 條件】——回測線落地。

登錄：台股策略線 PREREG大師三套 seq3（sha 5a5ca160c8d43d91，2026-09-27 00:52）；裁定 seq210 §五（編號＋附則①②③）、
      seq214 §二（資料閘三處讀法：分母＝上市滿 N 年、母公司欄空白改用本期淨利／權益總計、研發空白 ⇒ 不符）。
名稱一律「仿 App〔大師〕條件」；算法照本線定義，不保證與 App 相同。

    python -m backtest.researchMaster --part pre [--avail deadline] [--out backtest/resultsMaster]

⭐ 本版只有 --part pre（資料閘；⛔ 不讀任何報酬、⛔ 不建引擎輸入）。本體（判定 3 格、S0、描述臂）要等 pre 的停下條件解除才寫。

═══ 資料（釘版）═══
  財報：main 572b5993aa（⊇ 8b8f0dddbb：rd_hist 54 季）的 data/mops/fs_hist、bs_hist（IFRS 季彙總表，2015Q1～2026Q2，仟元）、
        data/mops/rd_hist（XBRL 研發費用＋營收，元）、data/meta/filing_dates.csv（t57sb01）⇒ git archive 到 ~/msdata/<sha>（唯讀）
  本益比：同一 commit 的 data/universe/per（上市）、data/universe/otcper（上櫃）；取量測日 t−1 那一天的檔
  日曆、股票名冊（first_seen）：edc6f8002f 快照（researchH2，同 W1）
  母體與量測日：W1 面板 resultsAFC/panel.csv.gz（gate3 內建；eligible ＝ liq_ok ∧ bars_ok ∧ inst_ok；量測日 ≥ 2017-01-01）

═══ 條件（登錄 §一，逐字機器化）═══
  單季 ＝ 累計相減（Q1 ＝ 累計；Q4 ＝ 全年 − Q3 累計）；資產負債表取期末
  年 ROE ＝ 全年母公司淨利 ÷ 年底母公司權益；年 ROA ＝ 全年母公司淨利 ÷ 年底總資產；年負債比 ＝ 年底總負債 ÷ 年底總資產
  年營收成長 ＝ 全年營收 ÷ 前一年 − 1；年 EPS 增率 ＝ 全年 EPS ÷ 前一年 − 1（前一年 ≤ 0 ⇒ 不符）
  母公司淨利／權益空白 ⇒ 本期淨利／權益總計（seq214 ②）
  M1 近 12 季單季營益率平均 ＞ 10%｜M2 ROE 5 年平均 ＞ 8%｜M3 營收成長 3 年平均 ＞ 10%｜M4 近 4 季研發 ÷ 營收 ＞ 5%（研發空白 ⇒ 不符）
  X1 ＝ M2｜X2 負債比 5 年平均 ＜ 30%｜X3 本益比 ＜ 15｜X4 ＝ M3
  O1 ROA 5 年平均 ＞ 8%｜O2 ＝ M2｜O3 EPS 增率 3 年平均 ＞ 30%｜O4 本益比 ＜ 15
  「不足」一律 ⇒ 不符；上市不滿該條件所需年數 ⇒ 依定義不符合、⛔ 不進可算比例的分母（seq214 ①）

═══ 可用日 ═══
  登錄：t57sb01 上傳日期的下一個交易日；缺時戳 ⇒ 法定期限（Q1 5/15、Q2 8/14、Q3 11/14、年報 次年 3/31）的下一個交易日
  ⚠ 2026-09-27 14:0x 查 main 572b5993aa：filing_dates.csv 只有 FY2015 的 525 家（2,651 列）⇒ t57sb01【沒有落地】
  ⇒ --avail deadline：一律用法定期限（＝ 登錄的缺時戳規則套到全部；⚠ 暫算，⛔ 未經裁定選用）

═══ pre 的「可算」定義（本線；交件列出）═══
  可算 ＝ 該條件依規則【判得出來】：所需各期財報列存在且所需欄位有值；研發空白、本益比空白（虧損）、前一年 EPS ≤ 0、
         分母 ≤ 0 屬「依定義不符」＝ 判得出來（⛔ 不算缺）
  分母 ＝ eligible ∧ 上市滿 5 年（三套都含 5 年條件）；上市滿 N 年 ＝ first_seen ≤ T − N 年，
         first_seen ＝ 2015-01-05（快照起點）視為上市早於快照起點（⭐ 本線讀法 L1）
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchH2 as H2                                # ⭐ D.DATA ⇒ edc6f8002f 快照（唯讀）；os.chdir(~/tw-p17)
D = H2.D
from backtest import p4_features as P4F

FIN_SHA = "572b5993aa87a48fd1f860a5bdc13cbbdf2e5964"
FD = os.path.expanduser(f"~/msdata/{FIN_SHA}/data")
PANEL = "backtest/resultsAFC/panel.csv.gz"
START = "2017-01-01"
W0_MAIN = "2017-03-02"
OUT_DEFAULT = "backtest/resultsMaster"
SNAP_FLOOR = pd.Timestamp("2015-01-05")
COV_TH = 0.90

REV = ["營業收入"]
REV_ALT = {"bd": ["收益"], "fh": ["淨收益"], "other": ["收入"]}          # 讀法 F1（金融業表的營收同義欄）；basi ＝ 利息淨收益＋利息以外淨損益
OI = ["營業利益（損失）", "營業利益"]
NIP = ["淨利（淨損）歸屬於母公司業主", "淨利（損）歸屬於母公司業主"]
NI = ["本期淨利（淨損）", "本期稅後淨利（淨損）"]
EPS = ["基本每股盈餘（元）", "基本每股盈餘"]
TA = ["資產總計", "資產總額", "資產合計"]
TL = ["負債總計", "負債總額", "負債合計"]
EQP = ["歸屬於母公司業主之權益合計", "歸屬於母公司業主權益合計", "歸屬於母公司業主之權益"]
EQ = ["權益總計", "權益總額", "權益合計"]

SETS = {"M": ["M1", "M2", "M3", "M4"], "X": ["M2", "X2", "PE", "M3"], "O": ["O1", "M2", "O3", "PE"]}
SET_NAME = {"M": "仿 App 麥克墨菲條件", "X": "仿 App 麥克喜偉條件", "O": "仿 App 詹姆士歐沙那希條件"}


def _pick(df, names):
    for n in names:
        if n in df.columns:
            return pd.to_numeric(df[n], errors="coerce")
    return pd.Series(np.nan, index=df.index, dtype=float)


def pidx(y, q):
    return int(y) * 4 + int(q) - 1


def load_fin(log=print):
    """(sid, p) ⇒ 累計損益＋期末資產負債；回 DataFrame 與重複列數。p ＝ 年×4＋季−1。"""
    fs, bs = [], []
    for sub, out in (("fs_hist", fs), ("bs_hist", bs)):
        for f in sorted(os.listdir(os.path.join(FD, "mops", sub))):
            if not f.endswith(".csv"):
                continue
            per, tab = f[:6], f[7:-4]
            df = pd.read_csv(os.path.join(FD, "mops", sub, f), dtype={"stock_id": str})
            if df.empty:
                continue
            r = pd.DataFrame({"sid": df["stock_id"].astype(str).str.strip(), "period": per, "table": tab})
            if sub == "fs_hist":
                r["rev"] = _pick(df, REV).to_numpy(float)
                kind = tab.split("_")[0]
                if kind == "basi":
                    ra = _pick(df, ["利息淨收益"]) + _pick(df, ["利息以外淨損益"])
                else:
                    ra = _pick(df, REV_ALT.get(kind, REV))
                r["rev_alt"] = np.where(np.isfinite(r["rev"].to_numpy(float)), r["rev"].to_numpy(float), ra.to_numpy(float))
                r["oi"] = _pick(df, OI).to_numpy(float)
                nip, ni = _pick(df, NIP).to_numpy(float), _pick(df, NI).to_numpy(float)
                r["ni"] = np.where(np.isfinite(nip), nip, ni); r["ni_fb"] = ~np.isfinite(nip) & np.isfinite(ni)
                r["eps"] = _pick(df, EPS).to_numpy(float)
            else:
                r["ta"] = _pick(df, TA).to_numpy(float); r["tl"] = _pick(df, TL).to_numpy(float)
                eqp, eq = _pick(df, EQP).to_numpy(float), _pick(df, EQ).to_numpy(float)
                r["eq"] = np.where(np.isfinite(eqp), eqp, eq); r["eq_fb"] = ~np.isfinite(eqp) & np.isfinite(eq)
            out.append(r)
    F = pd.concat(fs, ignore_index=True); B = pd.concat(bs, ignore_index=True)
    dupF = int(F.duplicated(["sid", "period"]).sum()); dupB = int(B.duplicated(["sid", "period"]).sum())
    F = F.drop_duplicates(["sid", "period"], keep="first"); B = B.drop_duplicates(["sid", "period"], keep="first")
    X = F.merge(B.drop(columns=["table"]), on=["sid", "period"], how="outer")
    X["y"] = X["period"].str[:4].astype(int); X["q"] = X["period"].str[5].astype(int)
    X["p"] = X["y"] * 4 + X["q"] - 1
    log(f"[財報] fs {len(F):,} 列（重複 {dupF}）｜bs {len(B):,} 列（重複 {dupB}）｜合併 {len(X):,}｜{X['sid'].nunique():,} 家｜"
        f"母公司淨利改用本期淨利 {int(X['ni_fb'].fillna(False).astype(bool).sum()):,} 列、權益改用權益總計 {int(X['eq_fb'].fillna(False).astype(bool).sum()):,} 列")
    return X, {"fs_dup": dupF, "bs_dup": dupB}


def load_rd(log=print):
    rows = []
    d = os.path.join(FD, "mops", "rd_hist")
    for f in sorted(os.listdir(d)):
        if f.endswith(".csv"):
            rows.append(pd.read_csv(os.path.join(d, f), dtype={"stock_id": str}))
    R = pd.concat(rows, ignore_index=True)
    R["sid"] = R["stock_id"].astype(str).str.strip()
    dup = int(R.duplicated(["sid", "period"]).sum())
    R = R.drop_duplicates(["sid", "period"], keep="first")
    R["p"] = [pidx(s[:4], s[5]) for s in R["period"]]
    for c in ("rd_ytd", "rev_ytd"):
        R[c] = pd.to_numeric(R[c], errors="coerce")
    log(f"[研發] rd_hist {len(R):,} 列（重複 {dup}）｜{R['period'].min()}～{R['period'].max()}｜研發有值 {R['rd_ytd'].notna().mean():.1%}")
    return R


def deadline(y: int, q: int) -> pd.Timestamp:
    return pd.Timestamp(f"{y + 1}-03-31") if q == 4 else pd.Timestamp(f"{y}-{('05-15', '08-14', '11-14')[q - 1]}")


class Fin:
    """每家公司：p ⇒ 列（累計損益、期末資產負債）；研發 p ⇒ (rd_ytd, rev_ytd)；可用日 pav[p]。"""

    def __init__(self, X: pd.DataFrame, R: pd.DataFrame, cal: pd.DatetimeIndex, avail: str):
        self.cal = cal
        X = X.sort_values(["sid", "p"])
        self.q = {sid: {r.p: r for r in g.itertuples(index=False)} for sid, g in X.groupby("sid", sort=False)}
        self.rd = {sid: {r.p: (r.rd_ytd, r.rev_ytd) for r in g.itertuples(index=False)} for sid, g in R.groupby("sid", sort=False)}
        self.avail_mode = avail
        self.pav = {}
        for p in sorted(set(X["p"]) | set(R["p"])):
            y, q0 = divmod(p, 4)
            j = int(cal.searchsorted(deadline(y, q0 + 1), side="right"))          # 法定期限的【下一個】交易日
            self.pav[p] = cal[j] if j < len(cal) else pd.Timestamp("2099-12-31")

    def latest(self, sid, T):
        d = self.q.get(sid)
        if not d:
            return None
        c = [p for p in d if self.pav[p] <= T]
        return max(c) if c else None

    def _v(self, sid, p, f):
        r = self.q.get(sid, {}).get(p)
        if r is None:
            return np.nan
        v = getattr(r, f)
        try:
            v = float(v)
        except (TypeError, ValueError):
            return np.nan
        return v if np.isfinite(v) else np.nan

    def single(self, sid, p, f):
        a = self._v(sid, p, f)
        return a if p % 4 == 0 else a - self._v(sid, p - 1, f)

    def annual(self, sid, y, f):
        return self._v(sid, y * 4 + 3, f)

    def rd4(self, sid, p, rev_src="rd"):
        """近 4 季研發 ÷ 營收 ⇒ (值, 狀態)。狀態：ok／no_row（XBRL 沒有這家或缺期）／rd_blank／rev_missing。
        近 4 季 ＝ 本季累計 ＋ 上年全年 − 上年同季累計（Q4 直接用全年；同資料庫線 0302 §三）。"""
        d = self.rd.get(sid)
        y, q0 = divmod(p, 4)
        need = [p] if q0 == 3 else [p, (y - 1) * 4 + 3, (y - 1) * 4 + q0]
        sgn = [1.0] if q0 == 3 else [1.0, 1.0, -1.0]
        if d is None or any(k not in d for k in need):
            return np.nan, "no_row"
        rd = [float(d[k][0]) for k in need]
        rv = [float(d[k][1]) for k in need] if rev_src == "rd" else [self._v(sid, k, "rev") * 1000.0 for k in need]
        if not all(np.isfinite(x) for x in rd):
            return np.nan, "rd_blank"
        if not all(np.isfinite(x) for x in rv):
            return np.nan, "rev_missing"
        num = sum(s * x for s, x in zip(sgn, rd)); den = sum(s * x for s, x in zip(sgn, rv))
        return (num / den if den > 0 else np.nan), "ok"


def eval_row(F: Fin, sid: str, T: pd.Timestamp, pe_val: dict, rev_f="rev", rd_rev="rd"):
    """回 ({cond: (可算, 符合)}, 附記)。pe_val：{讀法: 值／nan（空白）／None（當天檔裡沒有這檔）}。"""
    out, note = {}, {}
    L = F.latest(sid, T)
    note["L"] = L
    if L is None:
        for c in ("M1", "M2", "M3", "M4", "X2", "O1", "O3"):
            out[c] = (False, False)
    else:
        d = F.q[sid]
        ps = list(range(L - 11, L + 1))                   # M1：近 12 季（連續，讀法 Q1）
        if all(p in d for p in ps) and all((p - 1) in d for p in ps if p % 4 != 0):
            rv = [F.single(sid, p, rev_f) for p in ps]; oi = [F.single(sid, p, "oi") for p in ps]
            if all(np.isfinite(x) for x in rv + oi):
                mg = [o / r if r > 0 else np.nan for o, r in zip(oi, rv)]
                out["M1"] = (True, bool(all(np.isfinite(mg)) and np.mean(mg) > 0.10))
            else:
                out["M1"] = (False, False)
        else:
            out["M1"] = (False, False)
            note["M1_gap"] = sum(1 for p in ps if p not in d)
        Y = L // 4 if L % 4 == 3 else L // 4 - 1          # 已可用的最新年報
        ys = list(range(Y - 4, Y + 1))
        ni = [F.annual(sid, y, "ni") for y in ys]; eq = [F.annual(sid, y, "eq") for y in ys]
        ta = [F.annual(sid, y, "ta") for y in ys]; tl = [F.annual(sid, y, "tl") for y in ys]
        if all(np.isfinite(x) for x in ni + eq):
            v = [n / e if e > 0 else np.nan for n, e in zip(ni, eq)]
            out["M2"] = (True, bool(all(np.isfinite(v)) and np.mean(v) > 0.08))
        else:
            out["M2"] = (False, False)
        if all(np.isfinite(x) for x in ni + ta):
            v = [n / a if a > 0 else np.nan for n, a in zip(ni, ta)]
            out["O1"] = (True, bool(all(np.isfinite(v)) and np.mean(v) > 0.08))
        else:
            out["O1"] = (False, False)
        if all(np.isfinite(x) for x in tl + ta):
            v = [l / a if a > 0 else np.nan for l, a in zip(tl, ta)]
            out["X2"] = (True, bool(all(np.isfinite(v)) and np.mean(v) < 0.30))
        else:
            out["X2"] = (False, False)
        ys4 = list(range(Y - 3, Y + 1))
        rv = [F.annual(sid, y, rev_f) for y in ys4]
        if all(np.isfinite(x) for x in rv):
            g = [rv[i] / rv[i - 1] - 1 if rv[i - 1] > 0 else np.nan for i in range(1, 4)]
            out["M3"] = (True, bool(all(np.isfinite(g)) and np.mean(g) > 0.10))
        else:
            out["M3"] = (False, False)
        ep = [F.annual(sid, y, "eps") for y in ys4]
        if all(np.isfinite(x) for x in ep):
            g = [ep[i] / ep[i - 1] - 1 if ep[i - 1] > 0 else np.nan for i in range(1, 4)]
            out["O3"] = (True, bool(all(np.isfinite(g)) and np.mean(g) > 0.30))
        else:
            out["O3"] = (False, False)
        v, st = F.rd4(sid, L, rd_rev)
        note["rd"] = st
        if st in ("ok", "rd_blank", "no_row"):            # 研發空白／XBRL 沒有這家 ⇒ 依定義不符（判得出來）
            out["M4"] = (True, bool(st == "ok" and np.isfinite(v) and v > 0.05))
        else:
            out["M4"] = (False, False)
    for k, v in pe_val.items():
        out[f"PE_{k}"] = (False, False) if v is None else (True, bool(np.isfinite(v) and 0 < v < 15))
    return out, note


def load_pe(date: str, cache: dict):
    if date in cache:
        return cache[date]
    d = {}
    for sub, mk in (("per", "twse"), ("otcper", "tpex")):
        p = os.path.join(FD, "universe", sub, f"{date}.csv")
        if os.path.exists(p):
            df = pd.read_csv(p, dtype={"stock_id": str}, usecols=["stock_id", "per"])
            for s, v in zip(df["stock_id"].astype(str).str.strip(), pd.to_numeric(df["per"], errors="coerce")):
                d[(mk, s)] = float(v)
    cache[date] = d
    return d


def pe_lookup(cal, t, sid, cache):
    """{P0: 只讀 per（上市）恰 t−1｜P1: per＋otcper 恰 t−1｜P2: per＋otcper as-of t−1～t−6}；None ＝ 檔裡沒有這檔。"""
    d1 = load_pe(str(cal[t - 1].date()), cache)
    p0 = d1[("twse", sid)] if ("twse", sid) in d1 else None
    p1 = p0 if p0 is not None else (d1[("tpex", sid)] if ("tpex", sid) in d1 else None)
    p2 = None
    for k in range(1, 7):
        dk = load_pe(str(cal[t - k].date()), cache)
        for mk in ("twse", "tpex"):
            if (mk, sid) in dk:
                p2 = dk[(mk, sid)]
                break
        if p2 is not None:
            break
    return {"P0": p0, "P1": p1, "P2": p2}


def part_pre(a, log):
    t0 = time.time()
    cal = D.load_calendar()
    stocks = pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str)
    fseen = pd.to_datetime(stocks.set_index("stock_id")["first_seen"]).to_dict()
    panel = P4F.read_panel(PANEL)
    panel = panel[panel["measure_date"] >= pd.Timestamp(START)]
    el = panel[panel["eligible"].astype(bool)][["measure_date", "stock_id", "market"]].copy()
    pos_of = {d: i for i, d in enumerate(cal)}
    el["pos"] = el["measure_date"].map(pos_of).astype(int)
    log(f"[母體] W1 面板 {PANEL}｜量測日 {el['measure_date'].nunique()} 個（{el['measure_date'].min().date()}～{el['measure_date'].max().date()}）｜eligible 股-月 {len(el):,}")
    X, dup = load_fin(log)
    R = load_rd(log)
    F = Fin(X, R, cal, a.avail)
    fdd = pd.read_csv(os.path.join(FD, "meta", "filing_dates.csv"), dtype={"stock_id": str})
    t57 = fdd.groupby("year")["stock_id"].nunique().to_dict()
    log(f"[t57sb01] filing_dates.csv {len(fdd):,} 列｜逐年家數 {t57}｜⇒ 可用日一律 {a.avail}（法定期限下一交易日；暫算）")
    cache, rows = {}, []
    for (T, t), g in el.groupby(["measure_date", "pos"], sort=True):
        for r in g.itertuples(index=False):
            sid = r.stock_id
            fs_ = fseen.get(sid, pd.NaT)
            age = {n: bool(pd.notna(fs_) and (fs_ <= SNAP_FLOOR or fs_ <= T - pd.DateOffset(years=n))) for n in (3, 4, 5)}
            base, note = eval_row(F, sid, T, pe_lookup(cal, t, sid, cache))
            alt_rev, _ = eval_row(F, sid, T, {}, rev_f="rev_alt")
            alt_rd, _ = eval_row(F, sid, T, {}, rd_rev="fs")
            row = {"measure_date": T, "pos": t, "sid": sid, "market": r.market, "first_seen": fs_,
                   "age3": age[3], "age4": age[4], "age5": age[5], "L": note.get("L"), "rd_state": note.get("rd", ""),
                   "M1_gap": note.get("M1_gap", 0), "no_fs": sid not in F.q, "in_rd": sid in F.rd}
            for c, (dec, ok) in base.items():
                row[f"{c}_dec"] = dec; row[f"{c}_ok"] = ok
            for c in ("M1", "M3"):
                row[f"{c}_dec_F1"] = alt_rev[c][0]; row[f"{c}_ok_F1"] = alt_rev[c][1]
            row["M4_dec_R2"] = alt_rd["M4"][0]; row["M4_ok_R2"] = alt_rd["M4"][1]
            rows.append(row)
    E = pd.DataFrame(rows)
    E.to_csv(os.path.join(a.out, "pre_rows.csv.gz"), index=False)
    log(f"[逐列] {len(E):,} 股-月｜{time.time() - t0:.0f}s")
    summarize_pre(E, a, log, dup, t57)


def set_flags(E, s, pe="P1", rev="", rd="", age=True):
    dec = np.ones(len(E), bool); ok = np.ones(len(E), bool)
    for c in SETS[s]:
        cc = f"PE_{pe}" if c == "PE" else c
        suf = rev if (c in ("M1", "M3") and rev) else (rd if (c == "M4" and rd) else "")
        dec &= E[f"{cc}_dec{suf}"].to_numpy(bool); ok &= E[f"{cc}_ok{suf}"].to_numpy(bool)
    if age:
        ok &= E["age5"].to_numpy(bool)
    return dec, ok


def summarize_pre(E, a, log, dup, t57):
    per = []
    for T, g in E.groupby("measure_date", sort=True):
        d = {"measure_date": str(pd.Timestamp(T).date()), "eligible": len(g),
             "excl_lt3y": int((~g["age3"]).sum()), "excl_lt4y": int((~g["age4"]).sum()), "excl_lt5y": int((~g["age5"]).sum())}
        den = g["age5"].to_numpy(bool)
        d["denom_5y"] = int(den.sum())
        for tag, s, pe in (("M", "M", "P1"), ("X_P0", "X", "P0"), ("X_P1", "X", "P1"), ("O_P0", "O", "P0"), ("O_P1", "O", "P1")):
            dec, ok = set_flags(g, s, pe=pe)
            d[f"cov_{tag}"] = float(dec[den].mean()) if den.any() else np.nan
            d[f"cand_{tag}"] = int(ok.sum())
        g5 = g[g["age5"]]
        d["rd_blank_5y"] = int((g5["rd_state"] == "rd_blank").sum())
        d["rd_norow_5y"] = int((g5["rd_state"] == "no_row").sum())
        m123 = g5["M1_ok"] & g5["M2_ok"] & g5["M3_ok"]
        d["M123pass_5y"] = int(m123.sum())
        d["rd_block_M123pass"] = int((m123 & g5["rd_state"].isin(["rd_blank", "no_row"])).sum())
        for c, n in (("M1", 3), ("M2", 5), ("M3", 4), ("M4", 0), ("X2", 5), ("O1", 5), ("O3", 4), ("PE_P1", 0), ("PE_P0", 0)):
            m = g[f"age{n}"].to_numpy(bool) if n else np.ones(len(g), bool)
            d[f"covc_{c}"] = float(g.loc[m, f"{c}_dec"].mean()) if m.any() else np.nan
        d["cand_M_noage"] = int(set_flags(g, "M", age=False)[1].sum())
        d["cand_X_P1_noage"] = int(set_flags(g, "X", pe="P1", age=False)[1].sum())
        d["cand_O_P1_noage"] = int(set_flags(g, "O", pe="P1", age=False)[1].sum())
        d["cand_X_P2"] = int(set_flags(g, "X", pe="P2")[1].sum())
        d["cand_O_P2"] = int(set_flags(g, "O", pe="P2")[1].sum())
        d["cand_M_F1"] = int(set_flags(g, "M", rev="_F1")[1].sum())
        d["cand_X_P1_F1"] = int(set_flags(g, "X", pe="P1", rev="_F1")[1].sum())
        d["cand_M_R2"] = int(set_flags(g, "M", rd="_R2")[1].sum())
        d["M1_gap_rows"] = int((g["M1_gap"] > 0).sum())
        d["no_fs_rows"] = int(g["no_fs"].sum()); d["no_fs_5y"] = int((g["no_fs"] & g["age5"]).sum())
        per.append(d)
    P = pd.DataFrame(per)
    P.to_csv(os.path.join(a.out, "pre_coverage.csv"), index=False)
    res = {}
    for pe in ("P0", "P1"):
        cols = ["cov_M", f"cov_X_{pe}", f"cov_O_{pe}"]
        ok = (P[cols] >= COV_TH).all(axis=1)
        first = P.loc[ok, "measure_date"].iloc[0] if ok.any() else None
        each = {c: (P.loc[P[c] >= COV_TH, "measure_date"].iloc[0] if (P[c] >= COV_TH).any() else None) for c in cols}
        res[pe] = {"first_all_ge90": first, "each_first_ge90": each, "start": max(W0_MAIN, first) if first else None,
                   "later_below90": P.loc[(P["measure_date"] >= (first or "9999")) & ~ok, "measure_date"].tolist()}
    dist = []
    st = res["P1"]["start"]                             # ⚠ P0 的 X／O 永不 ≥ 90%（上櫃不在 per 檔）⇒ 分佈一律在 P1 起點之後的同窗描述
    W = P[P["measure_date"] >= st] if st else P.iloc[0:0]
    for tag in ("M", "X_P1", "O_P1", "X_P0", "O_P0"):
        if True:
            c = W[f"cand_{tag}"]
            dist.append({"window_from": st, "set": tag, "months": len(W), "median": float(c.median()), "p10": float(c.quantile(0.1)),
                         "p25": float(c.quantile(0.25)), "p75": float(c.quantile(0.75)), "p90": float(c.quantile(0.9)),
                         "min": float(c.min()), "max": float(c.max()), "share_lt10": float((c < 10).mean()), "share_eq0": float((c == 0).mean()),
                         "cov_min_after_start": float(W[f"cov_{tag}"].min())})
    DS = pd.DataFrame(dist)
    DS.to_csv(os.path.join(a.out, "pre_cand_dist.csv"), index=False)
    st = res["P1"]["start"]
    W = P[P["measure_date"] >= st]
    sens = []
    for lab, base, alt in (("L2 不看上市年數 vs L1（墨菲）", "cand_M", "cand_M_noage"),
                           ("L2 vs L1（喜偉 P1）", "cand_X_P1", "cand_X_P1_noage"),
                           ("L2 vs L1（歐沙那希 P1）", "cand_O_P1", "cand_O_P1_noage"),
                           ("本益比 P0 只讀 per（上市）vs P1 per＋otcper（喜偉）", "cand_X_P1", "cand_X_P0"),
                           ("本益比 P0 vs P1（歐沙那希）", "cand_O_P1", "cand_O_P0"),
                           ("本益比 P2 as-of≤6 交易日 vs P1 恰 t−1（喜偉）", "cand_X_P1", "cand_X_P2"),
                           ("本益比 P2 vs P1（歐沙那希）", "cand_O_P1", "cand_O_P2"),
                           ("營收 F1 金融業同義欄 vs F0 只認『營業收入』（墨菲）", "cand_M", "cand_M_F1"),
                           ("營收 F1 vs F0（喜偉 P1）", "cand_X_P1", "cand_X_P1_F1"),
                           ("M4 營收 R2 取 fs_hist vs R1 取 rd_hist（墨菲）", "cand_M", "cand_M_R2")):
        diff = W[alt] - W[base]
        sens.append({"reading": lab, "base_col": base, "alt_col": alt, "months": len(W), "base_median": float(W[base].median()),
                     "alt_median": float(W[alt].median()), "months_differ": int((diff != 0).sum()),
                     "sum_abs_diff": float(diff.abs().sum()), "max_abs_diff": float(diff.abs().max())})
    SE = pd.DataFrame(sens)
    SE.to_csv(os.path.join(a.out, "pre_readings.csv"), index=False)
    summ = {"登錄": "PREREG大師三套 seq3 sha 5a5ca160c8d43d91；裁定 seq210 §五、seq214 §二", "財報 commit": FIN_SHA,
            "可用日": f"{a.avail}（⚠ 暫算：t57sb01 未落地）", "t57sb01 逐年家數": {int(k): int(v) for k, v in t57.items()},
            "重複列": dup, "起點": res, "量測日數": int(len(P)), "⛔": "pre 不讀任何報酬"}
    json.dump(summ, open(os.path.join(a.out, "pre_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[起點] {json.dumps(res, ensure_ascii=False)}")
    log(DS.to_string(index=False))
    log(SE.to_string(index=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", choices=("pre",), required=True)
    ap.add_argument("--avail", choices=("deadline",), default="deadline")
    ap.add_argument("--out", default=OUT_DEFAULT)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    logf = open(os.path.join(a.out, "run.log"), "a", encoding="utf-8")

    def log(s):
        print(s, flush=True); logf.write(s + "\n"); logf.flush()
    log(f"=== researchMaster --part {a.part} avail={a.avail} {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）")
    if a.part == "pre":
        part_pre(a, log)


if __name__ == "__main__":
    main()
