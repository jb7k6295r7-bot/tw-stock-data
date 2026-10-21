# -*- coding: utf-8 -*-
"""researchBigRun3 對帳（第二階段：十一類樣貌、對照 A～D）——回測線計算子代理。⛔ 不檢定。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBigRun3_check [--dir backtest/resultsBigRun3]
輸出 <dir>/check.json、check.log

 K1 面板抽格重算（另寫、直接讀原檔）：抽 120 個（股, 月底）格，重算 前3年報酬、距5年低點、60日周轉率、市值、股價淨值比5年位置、融資餘額÷股數、借券÷股數、
    集保千張大戶比、外資持股率、月營收年增與由負轉正、營業利益率、ROE、EPS由虧轉盈、合約負債年增、總資產年增；與面板比。
 K2 不前視（全部格）：月營收期別可用日（次月 10／15 日）＜ 月底日；財報上傳日 ＜ 月底日；另由 filing_dates 原檔重找 300 格的「已上傳最新季」。
 K3 區間欄：抽 60 段，由原檔（attention、disposal、seo_cb_events、insider_predeclare、stocks_inst）重算四個區間的次數／股數比，與 乙_全表 比。
 K4 對照 D：全部乙段由面板價格另接一條序列，重判 崩／下市／未崩／未定；對照 B 乙：逐筆重驗 5 欄 IQR、3 年窗（完整、無壞根、最高 ＜ 3 倍、報酬 ＜ 0050）、
    不在乙段內、同檔 36 個月內不重取；另抽 300 個「IQR 內但未入 B」的格，確認確實不合某條件或被去重。
    對照 C、B 甲：由第一件 甲_窗.csv.gz（R_vw、R_ew）與 ind_index、mkt_ew_index 月底值重做 併段／剔除／IQR／3 年報酬條件。
 K5 段形狀：抽 40 段（乙）重算 起點→高點月數、段中最大回檔、波數、高點後 12 月最大跌幅。
 K6 並排表重算：乙、B、D崩、乙非D 的 n、中位（旗標為比例）由明細重算，與 並排_乙 全部列比；甲、B、C 同。
 K7 策略鎖 --check；git status。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import pickle
import subprocess
import sys
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchIndMom_freq as IMF             # noqa: E402
import backtest.data as D                                   # noqa: E402
from backtest import research11 as R                        # noqa: E402

SHA_A = "dbfb96cb81a7d3032e07fe47d1aeb5f0230545fa"; SHA_B = "325a1ee753cfcb3b77a65fa270bb3120aad04fd2"
DA = os.path.expanduser(f"~/bgrwork/main_{SHA_A[:12]}/data"); DB = os.path.expanduser(f"~/bgrwork/mainB_{SHA_B[:12]}/data")
FLAGS = {"新上市(<2年)", "月營收年增由負轉正", "EPS由虧轉盈", "毛利率由降轉升", "營業利益率由降轉升"}
LOG = []; RES = {}


def log(s):
    print(s, flush=True); LOG.append(str(s))


def close(a, b, tol=1e-6):
    fa = a is not None and np.isfinite(a); fb = b is not None and np.isfinite(b)
    if not fa and not fb:
        return True
    return fa and fb and abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return np.nan


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dir", default="backtest/resultsBigRun3"); a = ap.parse_args()
    OD = a.dir; rng = np.random.default_rng(20261023)
    J = json.load(open(os.path.join(OD, "bigrun3.json"), encoding="utf-8")); dry = bool(J.get("乾跑limit"))
    PN = pickle.load(open(os.path.expanduser(f"~/bgrwork/bgr3_panel_{'dry' if dry else 'full'}.pkl"), "rb"))
    SIDS = PN["SIDS"]; MEp = PN["MEp"]; P = PN["P"]; CU = PN["CU"]; META = PN["META"]; SHK = PN["SHK"]; K = len(MEp); IX = {s: i for i, s in enumerate(SIDS)}
    Ze = IMF.build_panel("早年", 2, log); Zm = IMF.build_panel("主", 2, log)
    CAL = Ze["cal"].append(Zm["cal"]); NE = Ze["n0"]; NC = len(CAL)
    pos_le = lambda ts: int(CAL.searchsorted(pd.Timestamp(ts), side="right")) - 1
    ie = {s: k for k, s in enumerate(Ze["sids"])}; im = {s: k for k, s in enumerate(Zm["sids"])}
    YI = pd.read_csv(os.path.join(OD, "乙_全表.csv.gz"), dtype={"代號": str}); BI = pd.read_csv(os.path.join(OD, "對照B_乙.csv"), dtype={"代號": str})

    # 面板價格另接（原始收盤比接縫）
    MS = {}

    def merged(s):
        if s in MS:
            return MS[s]
        parts = []
        for Z, off, ix in ((Ze, 0, ie), (Zm, NE, im)):
            if s in ix:
                c = Z["C"][ix[s]]; v = np.flatnonzero(np.isfinite(c))
                if len(v):
                    parts.append((v + off, c[v].astype(float), np.asarray(Z["BAD"][ix[s]][v], bool).copy(), Z["data"], Z["cal"], off))
        if not parts:
            MS[s] = None; return None
        if len(parts) == 2:
            (pe, ce, be, de, cale, _), (pm, cm, bm, dm, calm, _) = parts

            def raw(data, cal, p, off):
                x = pd.read_csv(os.path.join(data, "stocks", f"{s}.csv"), dtype={"date": str}, usecols=["date", "close"])
                v = pd.to_numeric(x.loc[x["date"] == str(cal[p - off].date()), "close"], errors="coerce")
                return float(v.iloc[-1]) if len(v) else np.nan
            re_ = raw(de, cale, pe[-1], 0); rm_ = raw(dm, calm, pm[0], NE)
            Mf = ce[-1] * rm_ / (re_ * cm[0]) if (np.isfinite(re_) and np.isfinite(rm_) and re_ > 0) else np.nan
            if np.isfinite(Mf) and Mf > 0:
                cm = cm * Mf; bm[0] = (pm[0] - pe[-1] - 1) >= 5
            else:
                bm[0] = True
            MS[s] = (np.r_[pe, pm], np.r_[ce, cm], np.r_[be, bm])
        else:
            MS[s] = (parts[0][0], parts[0][1], parts[0][2])
        return MS[s]

    def rawcsv(s, fname, cols):
        L = []
        for Z, off in ((Ze, 0), (Zm, NE)):
            f = os.path.join(Z["data"], fname, f"{s}.csv")
            if os.path.exists(f):
                x = pd.read_csv(f, dtype={"date": str}, usecols=["date"] + cols).drop_duplicates("date", keep="last")
                x["pos"] = Z["cal"].get_indexer(pd.to_datetime(x["date"])) + off
                x.loc[Z["cal"].get_indexer(pd.to_datetime(x["date"])) < 0, "pos"] = -1
                L.append(x[x["pos"] >= 0])
        return pd.concat(L) if L else pd.DataFrame(columns=["date", "pos"] + cols)

    # ── K1 面板抽格
    alive = np.argwhere(np.isfinite(P["市值(億)"]))
    pick = alive[rng.choice(len(alive), min(120, len(alive)), replace=False)]
    revraw = {}
    for f in sorted(glob.glob(os.path.join(DA, "early", "revenue", "*.csv"))) + sorted(glob.glob(os.path.join(DA, "mops", "revenue_hist", "*.csv"))):
        x = pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收", "去年當月營收"])
        for s, p_, v, l in zip(x["stock_id"], x["period"], x["當月營收"], x["去年當月營收"]):
            if s in IX:
                revraw[(s, p_)] = (fnum(v), fnum(l))
    rd = pd.read_csv(os.path.join(DA, "meta", "revenue_delisted", "revenue_delisted.csv"), dtype=str)
    rdv = {(s_, p_): fnum(v_) for s_, p_, v_ in zip(rd["stock_id"], rd["period"], rd["revenue_k"])}
    for (s_, p_), v_ in rdv.items():                      # 只補 revenue_hist 沒有的格；去年當月 ＝ 補檔 12 期前，否則原表
        if s_ in IX and not np.isfinite(revraw.get((s_, p_), (np.nan, np.nan))[0]) and np.isfinite(v_):
            y_, m_ = int(p_[:4]), int(p_[5:]); p12 = f"{y_ - 1:04d}-{m_:02d}"
            l_ = rdv.get((s_, p12), np.nan)
            if not np.isfinite(l_):
                l_ = revraw.get((s_, p12), (np.nan, np.nan))[0]
            revraw[(s_, p_)] = (v_, l_)
    fd = pd.read_csv(os.path.join(DA, "meta", "filing_dates.csv"), dtype=str)
    fd["d"] = pd.to_datetime(fd["uploaded_at"], errors="coerce").dt.normalize(); fd = fd.dropna(subset=["d"])
    up = fd.groupby(["stock_id", "year", "season"])["d"].min()
    ai1 = fd[fd["doc_code"] == "AI1"].groupby(["stock_id", "year", "season"])["d"].min(); up.loc[ai1.index] = ai1
    UPS = defaultdict(list)
    for (s, y, q), d in up.items():
        UPS[s].append((d, int(y) * 4 + int(q) - 1))
    fin = {}
    for f in sorted(glob.glob(os.path.join(DA, "mops", "fin_hist", "*.csv"))):
        per = os.path.basename(f)[:6]; qk = int(per[:4]) * 4 + int(per[5]) - 1
        x = pd.read_csv(f, dtype={"stock_id": str}, usecols=["stock_id", "rev_ytd", "opi_ytd", "nip_ytd", "eps_ytd", "equity_parent"])
        for r in x.itertuples(index=False):
            if r.stock_id in IX:
                fin[(r.stock_id, qk)] = (fnum(r.rev_ytd), fnum(r.opi_ytd), fnum(r.nip_ytd), fnum(r.eps_ytd), fnum(r.equity_parent))
    xb = {}
    for f in sorted(glob.glob(os.path.join(DA, "meta", "fs_xbrl", "fs_xbrl_*.csv"))):
        x = pd.read_csv(f, dtype={"stock_id": str}, usecols=["period", "stock_id", "report", "contract_liabilities_current", "contract_liabilities_noncurrent", "total_assets"])
        x = x.assign(_r=(x["report"] != "cr").astype(int)).sort_values(["stock_id", "period", "_r"]).drop_duplicates(["stock_id", "period"])
        for r in x.itertuples(index=False):
            if r.stock_id in IX:
                qk = int(r.period[:4]) * 4 + int(r.period[-1]) - 1
                c1, c2 = fnum(r.contract_liabilities_current), fnum(r.contract_liabilities_noncurrent)
                xb[(r.stock_id, qk)] = (np.nansum([c1, c2]) if (np.isfinite(c1) or np.isfinite(c2)) else np.nan, fnum(r.total_assets))

    def single(key_fn, s, qk, idx):
        v = fin.get((s, qk), (np.nan,) * 5)[idx]
        if qk % 4 == 0:
            return v
        pv = fin.get((s, qk - 1), (np.nan,) * 5)[idx]
        return v - pv if np.isfinite(v) and np.isfinite(pv) else np.nan

    def ravail(p_):
        y, m = int(p_[:4]), int(p_[5:]); y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
        return pd.Timestamp(y2, m2, 15 if p_ >= "2026-01" else 10)
    pers = sorted({p_ for (_, p_) in revraw})
    tdcc = {}
    for f in sorted(glob.glob(os.path.join(DB, "tdcc_hist", "*.parquet"))):
        x = pd.read_parquet(f, columns=["date", "stock_id", "level", "pct"]); x = x[x["level"] == 15]
        x["stock_id"] = x["stock_id"].astype(str); x["date"] = pd.to_datetime(x["date"].astype(str))
        x["tp"] = CAL.searchsorted(x["date"])                # 非交易日 ⇒ 其後第一個交易日
        for s, g in x[x["stock_id"].isin({SIDS[i] for i, _ in pick})].groupby("stock_id"):
            tdcc.setdefault(s, []).append(g[["date", "tp", "pct"]])
    tdcc = {s: pd.concat(v).sort_values("date") for s, v in tdcc.items()}
    fhl = []
    for f in sorted(glob.glob(os.path.join(DB, "meta", "foreign_holding", "foreign_holding_*.csv"))):
        x = pd.read_csv(f, dtype={"stock_id": str, "date": str}, usecols=["date", "stock_id", "foreign_pct"]); fhl.append(x[x["stock_id"].isin({SIDS[i] for i, _ in pick})])
    fhd = pd.concat(fhl); fhd["date"] = pd.to_datetime(fhd["date"])
    k1 = defaultdict(lambda: [0, 0]); bad1 = []
    for i, k in pick:
        s = SIDS[i]; p = int(MEp[k]); d = CAL[p]
        mg = merged(s); pos, c, bad = mg
        kk = int(np.searchsorted(pos, p, "right")) - 1
        res = {}
        # 前3年報酬
        v = np.nan
        if k >= 36:
            p3 = int(MEp[k - 36]); k3 = int(np.searchsorted(pos, p3, "right")) - 1
            if k3 >= 0 and p3 - pos[k3] <= 20 and not bad[k3 + 1:kk + 1].any():
                v = c[kk] / c[k3] - 1
        res["前3年報酬"] = v
        lo = int(np.searchsorted(pos, p - 1249, "left"))
        for q_ in range(kk, lo, -1):
            if bad[q_]:
                lo = q_; break
        res["距5年低點"] = c[kk] / c[lo:kk + 1].min() - 1
        st = rawcsv(s, "stocks", ["close", "volume", "shares"])
        st["shares"] = pd.to_numeric(st["shares"], errors="coerce"); st = st.sort_values("pos")
        stp = st[st["pos"] <= p].copy()
        if stp["shares"].isna().any():                     # 股數缺 ⇒ 面板市值 ÷ 同日原始收盤（主程式同一補法）
            mcv = np.r_[Ze["MC"][ie[s]] if s in ie else np.full(NE, np.nan), Zm["MC"][im[s]] if s in im else np.full(NC - NE, np.nan)]
            cl_ = stp["close"].apply(fnum).to_numpy(); pp_ = stp["pos"].to_numpy(int)
            est = np.where(cl_ > 0, mcv[pp_] / cl_, np.nan)
            stp["shares"] = stp["shares"].where(stp["shares"].notna(), est)
        shs = stp["shares"].ffill()
        shp = float(shs.iloc[-1]) if len(shs) and np.isfinite(shs.iloc[-1]) else np.nan
        vol = st.set_index("pos")["volume"].apply(fnum).reindex(range(p - 59, p + 1)).fillna(0)
        res["60日周轉率"] = vol.mean() / shp if p >= 59 and np.isfinite(shp) else np.nan
        rcl = fnum(st.loc[st["pos"] == pos[kk], "close"].iloc[-1]) if (st["pos"] == pos[kk]).any() else np.nan
        res["市值(億)"] = rcl * shp / 1e8
        # 融資、借券、大戶、外資持股
        mx = rawcsv(s, "stocks_margin", ["m_balance"]); mx = mx[(mx["pos"] <= p) & (mx["pos"] >= p - 20)]
        mx = mx[pd.to_numeric(mx["m_balance"], errors="coerce").notna()]
        if p >= NE:                                   # 早年上櫃融資來自日檔夾，這裡只驗主世界 stocks_margin
            res["融資餘額÷股數"] = fnum(mx["m_balance"].iloc[-1]) * 1000 / shp if len(mx) else np.nan
        if s in tdcc:
            g = tdcc[s][(tdcc[s]["tp"] <= p - 1) & (tdcc[s]["tp"] >= p - 15)]
            res["集保千張大戶比"] = float(g["pct"].iloc[-1]) if len(g) else np.nan
        else:
            res["集保千張大戶比"] = np.nan
        g = fhd[(fhd["stock_id"] == s) & (fhd["date"] <= d) & (fhd["date"] >= CAL[max(0, p - 5)])]
        res["外資持股率(月表)"] = fnum(g["foreign_pct"].iloc[-1]) if len(g) else np.nan
        # 月營收
        av = [p_ for p_ in pers if ravail(p_) < d]
        got = []
        for p_ in reversed(av[-5:]):
            v_, l_ = revraw.get((s, p_), (np.nan, np.nan))
            if np.isfinite(v_):
                got.append((p_, v_ / l_ - 1 if np.isfinite(l_) and l_ > 0 else np.nan))
        res["月營收年增"] = got[0][1] if got and got[0][0] >= av[-3] else np.nan
        if len(got) >= 2 and got and got[0][0] >= av[-3] and pers.index(got[1][0]) == pers.index(got[0][0]) - 1 and np.isfinite(got[0][1]) and np.isfinite(got[1][1]):
            res["月營收年增由負轉正"] = float(got[0][1] > 0 and got[1][1] <= 0)
        else:
            res["月營收年增由負轉正"] = np.nan
        # 財報
        cand = [qk for dd, qk in UPS.get(s, []) if dd < d]
        if cand:
            j = max(cand)
            ro = lambda qk: (single(None, s, qk, 1) / single(None, s, qk, 0)) if single(None, s, qk, 0) > 0 else np.nan
            o0, o4, o1, o5 = ro(j), ro(j - 4), ro(j - 1), ro(j - 5)
            res["營業利益率"] = o0
            n4 = [single(None, s, q_, 2) for q_ in range(j - 3, j + 1)]; e = fin.get((s, j), (np.nan,) * 5)[4]
            res["ROE"] = sum(n4) / e if np.isfinite(n4).all() and np.isfinite(e) and e > 0 else np.nan
            e0, e1 = single(None, s, j, 3), single(None, s, j - 1, 3)
            res["EPS由虧轉盈"] = float(e0 > 0 and e1 <= 0) if np.isfinite(e0) and np.isfinite(e1) else np.nan
            cl0, cl4 = xb.get((s, j), (np.nan, np.nan))[0], xb.get((s, j - 4), (np.nan, np.nan))[0]
            res["合約負債年增"] = cl0 / cl4 - 1 if np.isfinite(cl0) and np.isfinite(cl4) and cl4 > 0 else np.nan
            t0, t4 = xb.get((s, j), (np.nan, np.nan))[1], xb.get((s, j - 4), (np.nan, np.nan))[1]
            res["總資產年增"] = t0 / t4 - 1 if np.isfinite(t0) and np.isfinite(t4) and t4 > 0 else np.nan
        for f_, v_ in res.items():
            if f_.startswith("_"):
                continue
            ok = close(v_, float(P[f_][i, k]), 2e-4 if f_ in ("60日周轉率",) else 1e-4)
            k1[f_][0] += 1; k1[f_][1] += int(ok)
            if not ok and len(bad1) < 15:
                bad1.append((s, str(d.date()), f_, v_, float(P[f_][i, k])))
    RES["K1"] = {f_: {"抽": v[0], "相符": v[1]} for f_, v in k1.items()}; RES["K1_不符例"] = bad1
    log("K1 面板抽格：" + "、".join(f"{f_} {v[1]}/{v[0]}" for f_, v in k1.items()))
    for b_ in bad1[:8]:
        log(f"   ✖ {b_}")

    # ── K2 不前視
    PER = PN["PERIODS"]
    rp = META["rev_per"]; nrev = int((rp >= 0).sum()); badrev = 0
    avd = np.array([np.datetime64(ravail(p_)) for p_ in PER])
    med = np.array([np.datetime64(CAL[int(p)]) for p in MEp])
    ii, kk_ = np.nonzero(rp >= 0)
    badrev = int((avd[rp[ii, kk_]] >= med[kk_]).sum())
    fa = META["fs_av"]; ii, kk_ = np.nonzero(fa >= 0)
    badfs = int((fa[ii, kk_] >= med[kk_].astype("datetime64[D]").astype(np.int64)).sum())
    ok2 = 0; n2 = 0
    cells = np.argwhere(META["fs_qk"] >= 0)
    for i, k in cells[rng.choice(len(cells), min(300, len(cells)), replace=False)]:
        s = SIDS[i]; d = CAL[int(MEp[k])]
        cand = [qk for dd, qk in UPS.get(s, []) if dd < d]
        n2 += 1; ok2 += int(cand and max(cand) == META["fs_qk"][i, k])
    RES["K2"] = {"月營收格": nrev, "可用日≥月底": badrev, "財報格": int(len(np.nonzero(fa >= 0)[0])), "上傳日≥月底": badfs, "最新季重找": n2, "相符": ok2}
    log(f"K2 不前視：月營收 {nrev} 格中可用日 ≥ 月底 {badrev}；財報上傳日 ≥ 月底 {badfs}；最新季重找 {ok2}/{n2}")

    # ── K3 區間欄
    at = pd.read_csv(os.path.join(DB, "meta", "attention.csv"), dtype={"stock_id": str}, usecols=["stock_id", "date"])
    di = pd.read_csv(os.path.join(DB, "meta", "disposal.csv"), dtype={"stock_id": str}, usecols=["stock_id", "announce_date"])
    se = pd.read_csv(os.path.join(DB, "meta", "seo_cb_events", "seo_cb_events.csv"), dtype={"stock_id": str}, usecols=["date", "stock_id", "ipo"])
    se = se[pd.to_numeric(se["ipo"], errors="coerce").fillna(0) == 0]
    ins = pd.concat([pd.read_csv(f, dtype={"stock_id": str}, usecols=["declare_date", "stock_id", "shares", "plan_own", "plan_trust"])
                     for f in sorted(glob.glob(os.path.join(DB, "meta", "insider_predeclare", "*.csv")))])
    sh_ = pd.to_numeric(ins["shares"], errors="coerce")
    ins["w"] = sh_.where(sh_.notna(), pd.to_numeric(ins["plan_own"], errors="coerce").fillna(0) + pd.to_numeric(ins["plan_trust"], errors="coerce").fillna(0)).fillna(0)
    WINS = {"前12月→起點": ("前12月", "起點"), "起點→高點": ("起點", "高點"), "高點前6月→高點": ("高點前6月", "高點"), "高點→高點後6月": ("高點", "高點後6月")}
    k3 = defaultdict(lambda: [0, 0]); bad3 = []
    sm = YI.sample(min(60, len(YI)), random_state=7)

    def tpos(dts):
        return CAL.searchsorted(pd.to_datetime(pd.Series(dts), errors="coerce").dropna())
    for _, r in sm.iterrows():
        s = r["代號"]; i = IX[s]
        A_ = tpos(at.loc[at["stock_id"] == s, "date"]); Dd = tpos(di.loc[di["stock_id"] == s, "announce_date"]); S_ = tpos(se.loc[se["stock_id"] == s, "date"])
        g = ins[ins["stock_id"] == s]; ip = CAL.searchsorted(pd.to_datetime(g["declare_date"], errors="coerce").fillna(pd.Timestamp("2100-01-01")))
        inst = rawcsv(s, "stocks_inst", ["foreign", "trust"]); inst["v"] = inst["foreign"].apply(fnum).fillna(0) + inst["trust"].apply(fnum).fillna(0)
        for wn, (x, y) in WINS.items():
            k1_, k2_ = int(r[f"_k{x}"]), int(r[f"_k{y}"])
            if not (0 <= k1_ < k2_ < K):
                continue
            p1, p2 = int(MEp[k1_]), int(MEp[k2_]); shp = SHK[i, k2_]
            pos_, _, _ = merged(s); q1 = int(np.searchsorted(pos_, p1, "right")) - 1; q2 = int(np.searchsorted(pos_, p2, "right")) - 1
            if q1 < 0 or p1 - pos_[q1] > 20 or q2 < 0 or p2 - pos_[q2] > 20:
                continue                                    # 面板只在「20 日內有成交」的月底記值
            mine = {"注意次數": float(((A_ > p1) & (A_ <= p2)).sum()) if CAL[p1] >= pd.Timestamp("2011-01-01") else np.nan,
                    "處置次數": float(((Dd > p1) & (Dd <= p2)).sum()) if CAL[p1] >= pd.Timestamp("2011-01-01") else np.nan,
                    "現增可轉債決議次數": float(((S_ > p1) & (S_ <= p2)).sum()),
                    "內部人申報轉讓÷股數": float(g["w"].to_numpy()[(ip > p1) & (ip <= p2)].sum()) / shp if np.isfinite(shp) and shp > 0 else np.nan}
            for f_, v_ in mine.items():
                ok = close(v_, r[f"{f_}@{wn}"], 1e-6)
                k3[f_][0] += 1; k3[f_][1] += int(ok)
                if not ok and len(bad3) < 10:
                    bad3.append((s, wn, f_, v_, r[f"{f_}@{wn}"]))
            fv = r[f"外資投信買賣超÷股數@{wn}"]
            if np.isfinite(fv):
                mine_i = inst.loc[(inst["pos"] > p1) & (inst["pos"] <= p2), "v"].sum() / shp
                k3["外資投信買賣超÷股數"][0] += 1; k3["外資投信買賣超÷股數"][1] += int(close(mine_i, fv, 1e-6))
    RES["K3"] = {f_: {"抽": v[0], "相符": v[1]} for f_, v in k3.items()}; RES["K3_不符例"] = bad3
    log("K3 區間欄：" + "、".join(f"{f_} {v[1]}/{v[0]}" for f_, v in k3.items()))

    # ── K4 對照 D、B 乙
    okd = 0; badd = []
    for _, r in YI.iterrows():
        pos, c, bad = merged(r["代號"]); ph = pos_le(r["高點"])
        b = int(np.searchsorted(pos, ph, "right")) - 1
        hend = CAL[ph] + pd.DateOffset(months=12); he = pos_le(hend)
        crashed = False; cutbad = False
        for q_ in range(b + 1, len(pos)):
            if pos[q_] > he:
                break
            if bad[q_]:
                cutbad = True; break
            if c[q_] <= 0.5 * c[b]:
                crashed = True; break
        delisted = pos[-1] < he and pos[-1] < NC - 6
        full = hend <= CAL[-1] and not cutbad and not delisted
        st_ = "崩" if crashed else ("下市" if delisted else ("未崩" if full else ("遇壞根截" if cutbad else "未定")))
        okd += int(st_ == r["對照D"])
        if st_ != r["對照D"] and len(badd) < 5:
            badd.append((r["代號"], r["起點"], r["高點"], st_, r["對照D"], str(CAL[pos[-1]].date()), str(CAL[he].date())))
    IQR = PN["IQR"]
    BF = {"前3年報酬": "前3年報酬@起點", "距一年高點": "距一年高點@起點", "月營收年增": "月營收年增@起點", "60日周轉率": "60日周轉率@起點"}
    SEG = defaultdict(list)
    for _, r in YI.iterrows():
        SEG[r["代號"]].append((pos_le(r["起點"]), pos_le(r["高點"])))
    P50 = None
    D.DATA = Ze["data"]; b0 = R.load_bars("0050", "twse", Ze["cal"]); D.DATA = Zm["data"]; b1 = R.load_bars("0050", "twse", Zm["cal"])
    p50 = np.r_[b0["idx"].astype(np.int64), b1["idx"].astype(np.int64) + NE]
    c50 = np.r_[np.asarray(b0["c"], float), np.asarray(b1["c"], float) * (b0["c"][-1] * b1["rc"][0] / (b0["rc"][-1] * b1["c"][0]))]
    v50 = lambda p: c50[int(np.searchsorted(p50, p, "right")) - 1]

    def bcheck(s, ps):
        """回 (合格, 原因)。"""
        pos, c, bad = merged(s); kk = int(np.searchsorted(pos, ps, "right")) - 1
        endt = CAL[ps] + pd.DateOffset(years=3)
        if endt > CAL[-1]:
            return False, "超出資料尾"
        ep_ = pos_le(endt); e = int(np.searchsorted(pos, ep_, "right")) - 1
        if pos[-1] < ep_ - 20 or e <= kk or bad[kk + 1:e + 1].any():
            return False, "窗不完整或壞根"
        if c[kk + 1:e + 1].max() >= 3 * c[kk]:
            return False, "是大漲段"
        if not c[e] / c[kk] - 1 < v50(ep_) / v50(ps) - 1:
            return False, "贏0050"
        if any(a_ <= ps <= b_ for a_, b_ in SEG.get(s, [])):
            return False, "在乙段內"
        return True, ""
    okb = 0; dup = 0; inbounds = 0
    for _, r in BI.iterrows():
        ok_iqr = all(IQR[f_][0] <= r[col] <= IQR[f_][1] for f_, col in BF.items()) and IQR["log市值"][0] <= np.log(r["市值(億)@起點"]) <= IQR["log市值"][1]
        inbounds += int(ok_iqr)
        okb += int(ok_iqr and bcheck(r["代號"], pos_le(r["起點"]))[0])
    for s, g in BI.groupby("代號"):
        ks = sorted(g["_k起點"].to_numpy(int)); dup += int(any(b_ - a_ < 36 for a_, b_ in zip(ks[:-1], ks[1:])))
    # 未入 B 抽查
    LMC = np.log(P["市值(億)"].astype(float))
    m_ = np.ones_like(LMC, bool)
    for f_ in ("前3年報酬", "距一年高點", "月營收年增", "60日周轉率"):
        x = P[f_].astype(float); m_ &= np.isfinite(x) & (x >= IQR[f_][0]) & (x <= IQR[f_][1])
    m_ &= np.isfinite(LMC) & (LMC >= IQR["log市值"][0]) & (LMC <= IQR["log市值"][1])
    inB = {(r["代號"], int(r["_k起點"])) for _, r in BI.iterrows()}
    cand = [(i, k) for i, k in np.argwhere(m_) if (SIDS[i], int(k)) not in inB]
    why = Counter(); nviol = 0
    for i, k in [cand[j] for j in rng.choice(len(cand), min(300, len(cand)), replace=False)] if cand else []:
        s = SIDS[i]; p = int(MEp[k]); pos, c, bad = merged(s); kk = int(np.searchsorted(pos, p, "right")) - 1
        prev = int(MEp[k - 1]) if k > 0 else -1
        if kk < 0 or pos[kk] <= prev:
            why["該月無成交"] += 1; continue
        okc, rs = bcheck(s, int(pos[kk]))
        if okc:
            near = [kb for (sb, kb) in inB if sb == s and 0 < k - kb < 36]
            if near:
                why["36個月內已取"] += 1
            else:
                why["應入B卻沒有"] += 1; nviol += 1
        else:
            why[rs] += 1
    log(f"  K4 D 不符例 {badd}")
    RES["K4"] = {"D不符例": badd, "D重判相符": okd, "D段數": len(YI), "B筆數": len(BI), "B的IQR成立": inbounds, "B全部條件重驗成立": okb, "B同檔36月內重取": dup,
                 "IQR內未入B抽查": dict(why), "應入B卻沒有": nviol}
    log(f"K4 對照D 重判 {okd}/{len(YI)}；B {okb}/{len(BI)} 全部條件成立（IQR {inbounds}）、同檔重取 {dup}；IQR 內未入 B 抽查 {dict(why)}")
    # C、B 甲（由第一件月底指數另算）
    II = pd.read_csv("backtest/resultsBigRun/ind_index.csv.gz"); MKI = pd.read_csv("backtest/resultsBigRun2/mkt_ew_index.csv.gz")
    mkt = dict(zip(MKI["日"], MKI["全市場等權"]))
    JA = pd.read_csv(os.path.join(OD, "甲_全表.csv")); JC = pd.read_csv(os.path.join(OD, "對照C.csv")); JB = pd.read_csv(os.path.join(OD, "對照B_甲.csv"))
    VK = {"原版市值": "vw", "原版等權": "ew", "補充市值": "vw", "補充等權": "ew"}
    c_ok = 0; c_n = 0; b_ok = 0
    for vn, kd in VK.items():
        segs = defaultdict(list)
        for _, r in JA[JA["版"] == vn].iterrows():
            segs[r["產業"]].append((pd.Timestamp(r["起點"]), pd.Timestamp(r["高點"])))
        mine = set()
        for ind, g in II.groupby("產業"):
            g = g.sort_values("日").reset_index(drop=True)
            ds = pd.to_datetime(g["日"]); I_ = g[f"I_{kd}"].to_numpy(float); ch = g[f"鏈_{kd}"].to_numpy()
            js = [j for j in range(36, len(g)) if ds[j - 36] >= pd.Timestamp("2004-12-31") and ch[j] == ch[j - 36] and ch[j] >= 0
                  and np.isfinite(I_[j]) and np.isfinite(I_[j - 36]) and 0.5 <= I_[j] / I_[j - 36] - 1 < 1.0
                  and (ds[j] - ds[j - 36]).days < 1110]
            grp = []
            for j in js:
                if grp and j - 36 <= grp[-1][-1]:
                    grp[-1].append(j)
                else:
                    grp.append([j])
            for gg in grp:
                S_, E_ = ds[gg[0] - 36], ds[gg[-1]]
                if any(a_ <= E_ and S_ <= b_ for a_, b_ in segs.get(ind, [])):
                    continue
                mine.add((ind, str(S_.date())))
        fil = {(r["產業"], r["起點"]) for _, r in JC[JC["版"] == vn].iterrows()}
        c_n += len(fil); c_ok += int(fil <= mine) * len(fil)
        RES.setdefault("K4_C", {})[vn] = {"檔內": len(fil), "另算候選(未套跌幅條件)": len(mine), "檔內都在候選內": bool(fil <= mine),
                                         "檔內跌幅都≤-20%": bool((JC[JC["版"] == vn]["⑩高點後12月最大跌幅"] <= -0.2).all())}
        for _, r in JB[JB["版"] == vn].iterrows():
            b_ok += int(r["3年報酬"] < r["基準同窗"] and not any(a_ <= pd.Timestamp(r["起點"]) <= b_ for a_, b_ in segs.get(r["產業"], [])))
    RES["K4_B甲"] = {"筆": len(JB), "條件成立": b_ok}
    log(f"K4 對照C：{RES['K4_C']}；B 甲 條件成立 {b_ok}/{len(JB)}")

    # ── K5 形狀
    k5 = 0; n5 = 0
    for _, r in YI.sample(min(40, len(YI)), random_state=9).iterrows():
        pos, c, bad = merged(r["代號"]); a_ = int(np.searchsorted(pos, pos_le(r["起點"]), "left")); b_ = int(np.searchsorted(pos, pos_le(r["高點"]), "right")) - 1
        v = c[a_:b_ + 1]; peak = v[0]; mdd = 0; waves = 1; inside = False
        for x in v:
            peak = max(peak, x); dd = x / peak - 1; mdd = min(mdd, dd)
            if not inside and dd <= -0.2:
                inside = True
            elif inside and dd >= 0:
                waves += 1; inside = False
        n5 += 1; k5 += int(close(mdd, r["⑩段中最大回檔"], 1e-9) and waves == r["⑩波數"])
    RES["K5"] = {"抽": n5, "相符": k5}
    log(f"K5 形狀 {k5}/{n5}")

    # ── K6 並排重算
    SI = pd.read_csv(os.path.join(OD, "並排_乙.csv")); SJ = pd.read_csv(os.path.join(OD, "並排_甲.csv"))
    ok6 = 0; n6 = 0
    yr = lambda df: pd.to_datetime(df["起點"]).dt.year
    for _, r in SI.iterrows():
        y0, y1 = {"全期": (2004, 2100), "2005～2014": (2004, 2014), "2015～": (2015, 2100)}[r["起點期"]]
        g1 = YI[(yr(YI) >= y0) & (yr(YI) <= y1)]; gb = BI[(yr(BI) >= y0) & (yr(BI) <= y1)]
        col = f"⑩{r['欄']}" if r["時點"] == "段" else f"{r['欄']}@{r['時點']}"
        for gname, df in (("乙", g1), ("B", gb), ("D崩", g1[g1["對照D"] == "崩"]), ("乙非D", g1[g1["對照D"] == "未崩"])):
            v = df[col].to_numpy(float); v = v[np.isfinite(v)]
            m = (v.mean() if r["欄"] in FLAGS else np.median(v)) if len(v) else np.nan
            n6 += 1; ok6 += int(len(v) == r[f"{gname}_n"] and close(m, r[f"{gname}_中位"], 1e-9))
    for _, r in SJ.iterrows():
        col = f"⑩{r['欄']}" if r["時點"] == "段" else f"{r['欄']}@{r['時點']}"
        for gname, df in (("甲", JA), ("B", JB), ("C", JC)):
            d_ = df[df["版"] == r["版"]]
            if col not in d_:
                continue
            v = d_[col].to_numpy(float); v = v[np.isfinite(v)]
            m = (v.mean() if r["欄"] in FLAGS else np.median(v)) if len(v) else np.nan
            n6 += 1; ok6 += int(len(v) == r[f"{gname}_n"] and close(m, r[f"{gname}_中位"], 1e-9))
    RES["K6"] = {"格": n6, "相符": ok6}
    log(f"K6 並排重算 {ok6}/{n6}")
    lk = subprocess.run([sys.executable, "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True)
    st = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines()
    RES["K7"] = {"策略鎖": (lk.stdout + lk.stderr).strip().splitlines()[-1:], "已追蹤檔改動": [x for x in st if not x.startswith("??")],
                 "本件新增": [x for x in st if "BigRun3" in x]}
    log(f"K7 策略鎖 {RES['K7']['策略鎖']}；已追蹤檔改動 {len(RES['K7']['已追蹤檔改動'])}")
    json.dump(RES, open(os.path.join(OD, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(OD, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
