# -*- coding: utf-8 -*-
"""researchBigRun4 對帳（A 外資／營業利益率重產、B 現在谷底清單、C 路徑／先後／自己漲）——回測線計算子代理。⛔ 不檢定。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBigRun4_check [--dry]
輸出 <結果夾>/check.json、check.log

 K1（A）抽 200 格：外資持股率由 foreign_holding 原檔重找（月底當天或之前 5 交易日內最近一筆），營業利益率三欄由 fs_xbrl 原檔另寫解析重算；兩版都有值的格逐格相同與否。
 K2（A）新舊對照表的 舊有值／新有值／兩版都有 由 *_新舊欄 明細重算。
 K3（B）抽 3 個產業（含半導體業）：價格由面板另接、逐日持有市值迴圈重算等權／市值指數的前 3 年報酬與距 5 年高點；
    財報與月營收欄由原檔（fs_xbrl、filing_dates、revenue_hist／early）另算加總口徑。
 K4（C①）路徑表抽 40 格（欄 × 對齊 × 月）由逐段查格重算中位；先後：抽 80 段由旗標序列另寫掃描重算兩種定義的月差。
 K5（C②）自己漲：由 甲_段＋甲補充_段＋族群_段 另判全部乙段，段數、每年段數相符；前 60 排序；抽 20 段由 news 原檔重數則數。
 K6 策略鎖 --check；git status。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import pickle
import subprocess
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchIndMom_freq as IMF             # noqa: E402
from backtest import researchIndRev_prereg as PRE           # noqa: E402

SHA = "c1db66ce973025613512c3a318411db17e842f2a"
WORK = os.path.expanduser("~/bgrwork")
DN = os.path.join(WORK, f"mainD_{SHA[:12]}", "data"); DA = os.path.join(WORK, "main_dbfb96cb81a7", "data")
EXCL = {"其他", "綜合", "存託憑證", "ETF", ""}
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
    ap = argparse.ArgumentParser(); ap.add_argument("--dry", action="store_true"); a = ap.parse_args()
    tag = "dry" if a.dry else "full"; OD = os.path.join(WORK, "dry4") if a.dry else "backtest/resultsBigRun4"
    SRC3 = os.path.join(WORK, "dry3") if a.dry else "backtest/resultsBigRun3"
    rng = np.random.default_rng(20261025)
    PN = pickle.load(open(os.path.join(WORK, f"bgr3_panel_{tag}.pkl"), "rb")); B4 = pickle.load(open(os.path.join(WORK, f"bgr4_{tag}.pkl"), "rb"))
    NP3 = pickle.load(open(os.path.join(WORK, f"bgr3b_np_{tag}.pkl"), "rb"))["NP"]
    SIDS = PN["SIDS"]; MEp = PN["MEp"]; META = PN["META"]; P = PN["P"]; INDM = PN["INDM"]; K = len(MEp); N = len(SIDS); IX = {s: i for i, s in enumerate(SIDS)}
    Ze = IMF.build_panel("早年", 2, log); Zm = IMF.build_panel("主", 2, log); CAL = Ze["cal"].append(Zm["cal"]); NE = Ze["n0"]; NC = len(CAL)
    pos_le = lambda ts: int(CAL.searchsorted(pd.Timestamp(ts), side="right")) - 1
    # ── K1
    fh = pd.concat([pd.read_csv(f, dtype={"stock_id": str, "date": str}, usecols=["date", "stock_id", "foreign_pct"])
                    for f in sorted(glob.glob(os.path.join(DN, "meta", "foreign_holding", "*.csv")))])
    fh["pos"] = CAL.get_indexer(pd.to_datetime(fh["date"])); fh = fh[fh["pos"] >= 0]
    FHG = {s: g.sort_values("pos") for s, g in fh[fh["stock_id"].isin(IX)].groupby("stock_id")}
    raw = {}
    for f in sorted(glob.glob(os.path.join(DN, "meta", "fs_xbrl", "fs_xbrl_*.csv"))):
        x = pd.read_csv(f, dtype=str, usecols=["period", "stock_id", "report", "revenue_ytd", "operating_income_ytd"])
        for r in x.itertuples(index=False):
            if r.stock_id not in IX:
                continue
            key = (r.stock_id, r.period)
            if key in raw and (raw[key][0] == "cr" or r.report != "cr"):
                continue
            raw[key] = (r.report, fnum(r.revenue_ytd), fnum(r.operating_income_ytd))
    per = lambda qk: f"{qk // 4}Q{qk % 4 + 1}"

    def sq(s, qk, idx):
        v = raw.get((s, per(qk)), (None, np.nan, np.nan))[idx]
        if qk % 4 == 0 or not np.isfinite(v):
            return v
        pv = raw.get((s, per(qk - 1)), (None, np.nan, np.nan))[idx]
        return v - pv if np.isfinite(pv) else np.nan
    om = lambda s, qk: (sq(s, qk, 2) / sq(s, qk, 1)) if sq(s, qk, 1) > 0 else np.nan
    k1 = defaultdict(lambda: [0, 0]); bad = []
    cells = np.argwhere(np.isfinite(P["市值(億)"]))
    for i, k in cells[rng.choice(len(cells), min(200, len(cells)), replace=False)]:
        s = SIDS[i]; p = int(MEp[k]); g = FHG.get(s)
        mine = np.nan
        if g is not None:
            gg = g[(g["pos"] <= p) & (g["pos"] >= p - 5)]
            v = pd.to_numeric(gg["foreign_pct"], errors="coerce").dropna()
            gg = gg.loc[v.index]
            mine = float(pd.to_numeric(gg["foreign_pct"]).iloc[-1]) if len(gg) else np.nan
        k1["外資持股率"][0] += 1; ok = close(mine, float(B4["FHn"][i, k]), 1e-6); k1["外資持股率"][1] += ok
        if not ok and len(bad) < 6:
            bad.append((s, str(CAL[p].date()), "外資", mine, float(B4["FHn"][i, k])))
        qk = int(META["fs_qk"][i, k])
        if qk >= 0:
            v0, v4, v1, v5 = om(s, qk), om(s, qk - 4), om(s, qk - 1), om(s, qk - 5)
            mm = {"營業利益率": v0, "營業利益率年變化": v0 - v4,
                  "營業利益率由降轉升": float(v0 - v4 > 0 and v1 - v5 <= 0) if np.isfinite(v0 - v4) and np.isfinite(v1 - v5) else np.nan}
            for f, v in mm.items():
                ok = close(v, float(B4["OPM"][f][i, k]), 1e-5); k1[f][0] += 1; k1[f][1] += ok
                if not ok and len(bad) < 6:
                    bad.append((s, per(qk), f, v, float(B4["OPM"][f][i, k])))
    o_, n_ = P["外資持股率(月表)"], B4["FHn"]; both = np.isfinite(o_) & np.isfinite(n_)
    RES["K1"] = {f: {"抽": v[0], "相符": v[1]} for f, v in k1.items()}; RES["K1_不符例"] = bad
    RES["K1_外資兩版都有格"] = {"格": int(both.sum()), "相同": int((np.abs(o_[both] - n_[both]) < 1e-6).sum())}
    log("K1 原檔重算：" + "、".join(f"{f} {v[1]}/{v[0]}" for f, v in k1.items()) + f"｜外資兩版都有 {RES['K1_外資兩版都有格']}")
    # ── K2
    CMP = pd.read_csv(os.path.join(OD, "A", "新舊對照.csv")); ok2 = n2 = 0
    for nm in ("乙", "B乙", "甲", "B甲", "C"):
        d = pd.read_csv(os.path.join(OD, "A", f"{nm}_新舊欄.csv.gz"), dtype={"代號": str})
        for _, r in CMP[CMP["單位"] == nm].iterrows():
            dd = d if r["分組"] == "全部" else d[d["版"] == r["分組"]]
            o = dd[f"{r['欄']}@{r['時點']}(舊)"].to_numpy(float); n = dd[f"{r['欄']}@{r['時點']}(新)"].to_numpy(float)
            n2 += 1; ok2 += int(np.isfinite(o).sum() == r["舊有值"] and np.isfinite(n).sum() == r["新有值"] and (np.isfinite(o) & np.isfinite(n)).sum() == r["兩版都有"])
    RES["K2"] = {"列": n2, "相符": ok2}; log(f"K2 新舊對照重算 {ok2}/{n2}")
    # ── K3（B）
    BIND = pd.read_csv(os.path.join(OD, "B", "谷底_產業.csv"))
    rev, rev_ly, cat, _, _, _ = PRE.load_rev(DA); PIT = PRE.PIT(DA, cat)
    ie = {s: k for k, s in enumerate(Ze["sids"])}; im = {s: k for k, s in enumerate(Zm["sids"])}

    def merged(s):
        parts = []
        for Z, off, ix in ((Ze, 0, ie), (Zm, NE, im)):
            if s in ix:
                c = Z["C"][ix[s]]; v = np.flatnonzero(np.isfinite(c))
                if len(v):
                    parts.append((v + off, c[v].astype(float), np.asarray(Z["BAD"][ix[s]][v], bool).copy(), Z["data"], Z["cal"], off))
        if len(parts) == 2:
            (pe, ce, be, de, cale, _), (pm, cm, bm, dm, calm, _) = parts

            def rawc(data, cal, p, off):
                x = pd.read_csv(os.path.join(data, "stocks", f"{s}.csv"), dtype={"date": str}, usecols=["date", "close"])
                v = pd.to_numeric(x.loc[x["date"] == str(cal[p - off].date()), "close"], errors="coerce")
                return float(v.iloc[-1]) if len(v) else np.nan
            re_, rm_ = rawc(de, cale, pe[-1], 0), rawc(dm, calm, pm[0], NE)
            Mf = ce[-1] * rm_ / (re_ * cm[0]) if np.isfinite(re_) and np.isfinite(rm_) and re_ > 0 else np.nan
            if np.isfinite(Mf) and Mf > 0:
                cm = cm * Mf; bm[0] = (pm[0] - pe[-1] - 1) >= 5
            else:
                bm[0] = True
            return np.r_[pe, pm], np.r_[ce, cm], np.r_[be, bm]
        return (parts[0][0], parts[0][1], parts[0][2]) if parts else None
    MCm = {}
    for s in SIDS:
        x = np.full(NC, np.nan)
        if s in ie:
            x[:NE] = Ze["MC"][ie[s]]
        if s in im:
            x[NE:] = Zm["MC"][im[s]]
        MCm[s] = x
    RAT = {}

    def ratio(s):
        if s not in RAT:
            x = np.ones(NC); m = merged(s)
            if m is not None:
                pos, c, bad_ = m
                for k_ in range(1, len(pos)):
                    if not bad_[k_]:
                        x[pos[k_]] = c[k_] / c[k_ - 1]
            RAT[s] = x
        return RAT[s]
    VAL = {s: np.flatnonzero(np.isfinite(ratio(s)) & (np.arange(NC) >= 0)) for s in []}
    ym = CAL.year * 12 + CAL.month; ms = np.flatnonzero(np.r_[True, ym[1:] != ym[:-1]]); me = np.r_[ms[1:] - 1, NC - 1]
    MON = [(int(ms[k] - 1), int(me[k])) for k in range(1, len(ms))]
    LASTV = {}

    def lastv(s, p):
        if s not in LASTV:
            m = merged(s); LASTV[s] = m[0] if m is not None else np.array([], int)
        v = LASTV[s]; k_ = int(np.searchsorted(v, p, "right")) - 1
        return v[k_] if k_ >= 0 else -10**9
    pnow = NC - 1
    pick = ["半導體業"] + [x for x in BIND.dropna(subset=["前3年報酬_等權"])["名稱"].sample(min(2, len(BIND)), random_state=3) if x != "半導體業"]
    k3 = []
    for ind in pick[:3]:
        r = BIND[BIND["名稱"] == ind].iloc[0]
        d3 = CAL[pnow] - pd.DateOffset(years=3); p3 = pos_le(d3); p5 = max(0, pnow - 1249)
        for kd in ("ew", "vw"):
            I = 1.0; vals = {}; okm = True
            for (b, e) in MON:
                if e < p5 or b >= pnow:
                    continue
                mem = [s for s in SIDS if b - lastv(s, b) <= 20 and np.isfinite(MCm[s][b]) and MCm[s][b] > 0 and PIT.at(s, CAL[b])[0] == ind]
                if len(mem) < 5:
                    okm = False; vals = {}; I = 1.0; continue
                W = np.array([MCm[s][b] if kd == "vw" else 1.0 for s in mem])
                G = np.cumprod(np.stack([ratio(s)[b + 1:min(e, pnow) + 1] for s in mem]), axis=1)
                if b not in vals:
                    vals[b] = I
                v = I * (W @ G) / W.sum()
                for j_, pp in enumerate(range(b + 1, min(e, pnow) + 1)):
                    vals[pp] = v[j_]
                I = float(v[-1])
            ser = pd.Series(vals).sort_index()
            mine3 = ser.iloc[-1] / ser[ser.index <= p3].iloc[-1] - 1 if (ser.index <= p3).any() and ser.index.min() <= p3 else np.nan
            mine5 = ser.iloc[-1] / ser[ser.index >= p5].max() - 1
            lab = "等權" if kd == "ew" else "市值"
            k3.append((ind, kd, close(mine3, r[f"前3年報酬_{lab}"], 1e-6), close(mine5, r[f"距5年高點_{lab}"], 1e-6), mine3, r[f"前3年報酬_{lab}"]))
            log(f"  K3 {ind} {lab}：前3年 {mine3:+.6f}/{r[f'前3年報酬_{lab}']:+.6f}｜距5年高 {mine5:+.6f}/{r[f'距5年高點_{lab}']:+.6f}")
    # 月營收近 3 月（加總）由原檔
    rr = {}
    for f in sorted(glob.glob(os.path.join(DA, "mops", "revenue_hist", "2026-*.csv"))) + sorted(glob.glob(os.path.join(DA, "mops", "revenue_hist", "2025-*.csv"))):
        x = pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收", "去年當月營收"])
        for s, p_, v, l in zip(x["stock_id"], x["period"], x["當月營收"], x["去年當月營收"]):
            rr[(s, p_)] = (fnum(v), fnum(l))
    k3r = []
    for ind in pick[:3]:
        r = BIND[BIND["名稱"] == ind].iloc[0]
        mem = [s for s in SIDS if pnow - lastv(s, pnow) <= 20 and np.isfinite(MCm[s][pnow]) and MCm[s][pnow] > 0 and PIT.at(s, CAL[pnow])[0] == ind]
        sv = sl = 0.0
        for s in mem:                                           # 2026-09-24 已公開 ⇒ 最新期 2026-08（可用 2026-09-15 之後）
            ends = ["2026-08", "2026-07", "2026-06"]; per3 = {"2026-08": ("2026-06", "2026-07", "2026-08"), "2026-07": ("2026-05", "2026-06", "2026-07"),
                                                             "2026-06": ("2026-04", "2026-05", "2026-06")}
            for e_ in ends:                                     # 最新期缺 ⇒ 往前最多 2 期（主程式同）
                if np.isfinite(rr.get((s, e_), (np.nan, np.nan))[0]):
                    got = [rr.get((s, p_), (np.nan, np.nan)) for p_ in per3[e_]]
                    if all(np.isfinite(g_[0]) and np.isfinite(g_[1]) for g_ in got) and sum(g_[1] for g_ in got) > 0:
                        sv += sum(g_[0] for g_ in got); sl += sum(g_[1] for g_ in got)
                    break
        mine = sv / sl - 1 if sl > 0 else np.nan
        k3r.append(close(mine, r["近3月營收年增(加總)"], 1e-3))
        log(f"  K3 {ind} 近3月營收年增(加總)：{mine:+.4f}/{r['近3月營收年增(加總)']:+.4f}（成員 {len(mem)}／檔 {r['成員數(當日在市)']}）")
    RES["K3"] = {"指數": [(x[0], x[1], bool(x[2]), bool(x[3])) for x in k3], "近3月營收": k3r}
    # ── K4（C①）
    PY = pd.read_csv(os.path.join(OD, "C", "路徑_乙.csv")); YI = pd.read_csv(os.path.join(SRC3, "乙_全表.csv.gz"), dtype={"代號": str})
    BI = pd.read_csv(os.path.join(SRC3, "對照B_乙.csv"), dtype={"代號": str})
    ARR = {"月營收年增": P["月營收年增"], "毛利率年變化(xbrl)": NP3["毛利率年變化"], "營業利益率年變化(xbrl新)": B4["OPM"]["營業利益率年變化"],
           "外資持股率(新月表)": B4["FHn"], "距一年高點": P["距一年高點"], "存貨天數年變化(天)": B4["IVDC"]}
    sub = PY[PY["欄"].isin(ARR)].sample(min(40, len(PY)), random_state=4); ok4 = 0
    for _, r in sub.iterrows():
        k0 = YI["_k起點" if r["對齊"] == "起點" else "_k高點"].to_numpy(int) + int(r["月"]); ii = YI["_i"].to_numpy(int)
        v = np.array([ARR[r["欄"]][i, k] if 0 <= k < K else np.nan for i, k in zip(ii, k0)], float); v = v[np.isfinite(v)]
        ok4 += int(len(v) == r["段_n"] and close(float(np.median(v)) if len(v) else np.nan, r["段_中位"], 1e-9))
    OR = pd.read_csv(os.path.join(OD, "C", "先後_逐段_乙.csv.gz"), dtype={"代號": str}); ORY = OR[OR["單位"] == "乙×3"].reset_index(drop=True)
    HI = B4["HI24"]; FHn = B4["FHn"].astype(float)
    okO = 0; nO = 0
    for j in rng.choice(len(YI), min(80, len(YI)), replace=False):
        r = YI.iloc[j]; i = int(r["_i"]); ks, kh = int(r["_k起點"]), int(r["_k高點"])
        rv = P["月營收年增由負轉正"][i] == 1
        gmv = NP3["毛利率由降轉升"][i]; gm = (gmv == 1) & ~np.r_[False, gmv[:-1] == 1]
        inc = [False] + [bool(np.isfinite(FHn[i, k]) and np.isfinite(FHn[i, k - 1]) and FHn[i, k] > FHn[i, k - 1]) for k in range(1, K)]
        fr = np.array([k >= 1 and k + 2 < K and inc[k] and inc[k + 1] and inc[k + 2] and not inc[k - 1] for k in range(K)])
        evs = {"營收年增由負轉正": rv, "毛利率由降轉升": gm, "外資持股率開始連3月增加": fr, "營收創24月新高首次": HI[i]}
        for e, m in evs.items():
            ks_ = [k for k in range(max(ks - 24, 0), min(kh, K - 1) + 1) if m[k]]
            first = (ks_[0] - ks) if ks_ else np.nan
            near = (sorted(ks_, key=lambda k: (abs(k - ks), k))[0] - ks) if ks_ else np.nan
            nO += 2
            okO += int(close(first, ORY.at[j, f"{e}_月差(窗內第一次)"], 1e-9)) + int(close(near, ORY.at[j, f"{e}_月差(最接近起點)"], 1e-9))
    RES["K4"] = {"路徑抽格": len(sub), "路徑相符": ok4, "先後抽算": nO, "先後相符": okO}
    log(f"K4 路徑 {ok4}/{len(sub)}；先後 {okO}/{nO}")
    # ── K5（C②）
    js = defaultdict(list)
    for f in ("backtest/resultsBigRun/甲_段.csv", "backtest/resultsBigRun2/甲補充_段.csv"):
        for _, r in pd.read_csv(f).iterrows():
            js[r["產業"]].append((r["起點"], r["高點"]))
    GS = pd.read_csv("backtest/resultsBigRun2/族群_段.csv", dtype={"代號": str})
    gkey = {(c, s0): g for c, s0, g in zip(GS["代號"], GS["起點"], GS["群_切0.7"])}
    self_ = [r for _, r in YI.iterrows() if not any(a_ <= r["高點"] and r["起點"] <= b_ for a_, b_ in js.get(r["產業(起點PIT)"], []))
             and gkey.get((r["代號"], r["起點"]), 0) == 0]
    SS = pd.read_csv(os.path.join(OD, "C", "自己漲_彙總.csv")); SY = pd.read_csv(os.path.join(OD, "C", "自己漲_年.csv"))
    myy = pd.Series([int(r["起點"][:4]) for r in self_]).value_counts()
    ok5 = int(len(self_) == SS["個股自己漲段數"].iloc[0]) + int(all(myy.get(int(y), 0) == n for y, n in zip(SY["起點年"], SY["段數"])))
    T60 = pd.read_csv(os.path.join(OD, "C", "自己漲_前60.csv"), dtype={"代號": str})
    exp60 = sorted([r for r in self_ if r["起點"] >= "2013"], key=lambda r: -r["倍數"])[:60]
    ok60 = [(r["代號"], r["起點"]) for r in exp60] == list(zip(T60["代號"], T60["起點"]))
    news = pd.concat([pd.read_csv(f, dtype={"stock_id": str}, usecols=["date", "stock_id"]) for f in sorted(glob.glob(os.path.join(DN, "mops", "news", "*.csv")))
                      if int(os.path.basename(f)[:4]) >= 2012])
    okn = 0; nn = 0
    for _, r in T60.head(20).iterrows():
        x = news[(news["stock_id"] == r["代號"]) & (news["date"] > r["起點"]) & (news["date"] <= r["高點"])]
        nn += 1; okn += int(len(x) == r["起點→高點重大訊息則數"])
    RES["K5"] = {"自己漲段數": len(self_), "彙總與每年相符項": ok5, "前60排序相符": bool(ok60), "news則數抽查": f"{okn}/{nn}"}
    log(f"K5 自己漲 {len(self_)} 段（彙總與每年 {ok5}/2）；前60 排序 {ok60}；news 則數 {okn}/{nn}")
    lk = subprocess.run([sys.executable, "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True)
    st = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines()
    RES["K6"] = {"策略鎖": (lk.stdout + lk.stderr).strip().splitlines()[-1:], "已追蹤檔改動": [x for x in st if not x.startswith("??")],
                 "本件新增": [x for x in st if "BigRun4" in x]}
    log(f"K6 策略鎖 {RES['K6']['策略鎖']}；已追蹤檔改動 {len(RES['K6']['已追蹤檔改動'])}；新增 {RES['K6']['本件新增']}")
    json.dump(RES, open(os.path.join(OD, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(OD, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
