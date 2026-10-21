# -*- coding: utf-8 -*-
"""researchBigRun 對帳（抽段手算、不前視、彙總重算、策略鎖）——回測線計算子代理。⛔ 不算任何之後報酬；只讀 resultsBigRun/ 與原始資料逐筆重算。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBigRun_check [--dir backtest/resultsBigRun]
輸出 <dir>/check.json、check.log

 K1 甲 抽窗手算：抽 25 個窗（達標 10、未達標 15）＋ 抽 4 段（市值 3、等權 1）整段；價格 ⛔ 不用面板，逐檔 research11.load_bars 重讀兩世界、自己接縫
    （原始收盤比），壞根 ＝ load_bars next_bad ∪ 面板 BAD（crashwork、reduce_v2 只在面板裡）；成員自己重判（PIT、20 日內有成交、市值 ＞ 0、排除類別）；
    指數用逐日「持有市值」迴圈（每月初 W0、每日乘 1＋r）⇒ 3 年報酬、0050 同窗、達標判定；整段另驗 起點、高點日、漲幅。
 K2 甲 併段邏輯：由 甲_窗.csv.gz 的達標旗標自己併段（j2 − 36 ≤ j1），與 甲_段.csv 的 起點、最後達標窗終點、達標窗數 逐段比。
 K3 乙 ×3／×5 判定：抽 40 檔有段＋20 檔無段，load_bars 重讀、自己接縫，逐月底暴力掃描（月底、該月最後一根、3／5 曆年、遇壞根截斷、下一段起點在上一段高點之後），
    段列表（起點、高點、倍數）與 乙_段 逐筆比。
 K4 不前視（全部列）：每個時點的 營收期別 可用日（次月 10／15 日）＜ 時點日；財報可用（上傳日）＜ 時點日；另抽 300 列從 filing_dates 原檔重找
    「時點日之前已上傳的最新季」與 AI1／最早上傳日；抽 300 列從原始 CSV 重算 營收年增（公告當時口徑）。
 K5 抽 60 列重算 本益比 5 年位置（stocks_per／early per 原檔）、距一年高點（load_bars）、外資＋投信持股變化（stocks_inst 原檔）、0050 乖離。
 K6 彙總重算：freq_甲、freq_乙、乙_重疊、丙_乙彙總（中位數）由段檔重算。
 K7 策略鎖 --check；本件新增檔以外 git 已追蹤檔沒有被本件改動（列出 git status）。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchIndMom_freq as IMF             # noqa: E402  build_panel 快取（只拿日曆、BAD、市值）
from backtest import researchIndRev_prereg as PRE           # noqa: E402  PIT
from backtest import research11 as R                        # noqa: E402  load_bars
import backtest.data as D                                   # noqa: E402

SHA = "dbfb96cb81a7d3032e07fe47d1aeb5f0230545fa"
DATA = os.path.expanduser(f"~/bgrwork/main_{SHA[:12]}/data")
EXCL = {"其他", "綜合", "存託憑證", "ETF", ""}
START = pd.Timestamp("2004-12-31")
LOG = []
RES = {}


def log(s):
    print(s, flush=True); LOG.append(str(s))


def close(a, b, tol=1e-6):
    if (a is None or not np.isfinite(a)) and (b is None or not np.isfinite(b)):
        return True
    return a is not None and b is not None and np.isfinite(a) and np.isfinite(b) and abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dir", default="backtest/resultsBigRun"); a = ap.parse_args()
    OD = a.dir
    rng = np.random.default_rng(20261021)
    Ze = IMF.build_panel("早年", 2, log); Zm = IMF.build_panel("主", 2, log)
    CAL = Ze["cal"].append(Zm["cal"]); NE = Ze["n0"]; NC = len(CAL)
    ie = {s: k for k, s in enumerate(Ze["sids"])}; im = {s: k for k, s in enumerate(Zm["sids"])}
    ALL = sorted(set(ie) | set(im))
    pos_le = lambda ts: int(CAL.searchsorted(pd.Timestamp(ts), side="right")) - 1
    J = json.load(open(os.path.join(OD, "bigrun.json"), encoding="utf-8"))
    if J.get("乾跑limit"):
        log(f"⚠ 結果夾是乾跑（limit {J['乾跑limit']}）⇒ K1 成員只取該次的股票集合")
    SEG = pd.read_csv(os.path.join(OD, "甲_段.csv"))
    WIN = pd.read_csv(os.path.join(OD, "甲_窗.csv.gz"))
    B3 = pd.read_csv(os.path.join(OD, "乙_段_x3.csv.gz"), dtype={"代號": str}); B5 = pd.read_csv(os.path.join(OD, "乙_段_x5.csv.gz"), dtype={"代號": str})
    USE = set(J["乾跑代號"]) if J.get("乾跑limit") else set(ALL)

    # ── 逐檔重讀（快取）
    CACHE = {}

    def series(s):
        """回 (pos, c, bad)：兩世界 load_bars 接起來，接縫用原始收盤比；壞根 ＝ next_bad ∪ 面板 BAD。"""
        if s in CACHE:
            return CACHE[s]
        parts = []
        for wn, Z, off, ix in (("早年", Ze, 0, ie), ("主", Zm, NE, im)):
            if s not in ix:
                continue
            D.DATA = Z["data"]
            B = R.load_bars(s, Z["mk"].get(s, "twse"), Z["cal"])
            if B is None:
                continue
            idx = B["idx"].astype(np.int64); nb = len(idx)
            bad = np.asarray(B["next_bad"][:nb] == np.arange(nb), bool) | np.asarray(Z["BAD"][ix[s]][idx], bool)
            parts.append((wn, idx + off, np.asarray(B["c"], float), np.asarray(B["rc"], float), bad))
        if not parts:
            CACHE[s] = None; return None
        if len(parts) == 2:
            (_, pe, ce, re_, be), (_, pm, cm, rm, bm) = parts
            M = ce[-1] * rm[0] / (re_[-1] * cm[0]) if (np.isfinite(rm[0]) and np.isfinite(re_[-1]) and re_[-1] > 0) else np.nan
            bm = bm.copy()
            if np.isfinite(M) and M > 0:
                cm = cm * M
                bm[0] = (pm[0] - pe[-1] - 1) >= 5
            else:
                bm[0] = True
            pos = np.r_[pe, pm]; c = np.r_[ce, cm]; bad = np.r_[be, bm]
        else:
            _, pos, c, _, bad = parts[0]
        CACHE[s] = (pos, c, bad)
        return CACHE[s]

    # ── 0050
    p50 = []; c50 = []; r50 = []
    for Z, off in ((Ze, 0), (Zm, NE)):
        D.DATA = Z["data"]; B = R.load_bars("0050", "twse", Z["cal"])
        p50.append(B["idx"].astype(np.int64) + off); c50.append(np.asarray(B["c"], float)); r50.append(np.asarray(B["rc"], float))
    M50 = c50[0][-1] * r50[1][0] / (r50[0][-1] * c50[1][0])
    P50 = np.r_[p50[0], p50[1]]; C50 = np.r_[c50[0], c50[1] * M50]

    def v50(p):
        return C50[int(np.searchsorted(P50, p, "right")) - 1]

    # ── K1 甲
    rev, rev_ly, cat, _, _, _ = PRE.load_rev(DATA)
    PIT = PRE.PIT(DATA, cat)
    MCm = {}
    for s in ALL:
        x = np.full(NC, np.nan)
        if s in ie:
            x[:NE] = Ze["MC"][ie[s]]
        if s in im:
            x[NE:] = Zm["MC"][im[s]]
        MCm[s] = x
    VALID = {}
    for s in ALL:
        v = np.zeros(NC, bool)
        if s in ie:
            v[:NE] = np.isfinite(Ze["C"][ie[s]])
        if s in im:
            v[NE:] = np.isfinite(Zm["C"][im[s]])
        VALID[s] = np.flatnonzero(v)
    ym = CAL.year * 12 + CAL.month
    mstart = np.flatnonzero(np.r_[True, ym[1:] != ym[:-1]]); mend = np.r_[mstart[1:] - 1, NC - 1]
    MON = [(int(mstart[k] - 1), int(mend[k])) for k in range(1, len(mstart))]

    def members(ind, b):
        out = []
        for s in USE:
            vp = VALID[s]
            k = int(np.searchsorted(vp, b, "right")) - 1
            if k < 0 or b - vp[k] > 20:
                continue
            w = MCm[s][b]
            if not (np.isfinite(w) and w > 0):
                continue
            g, _ = PIT.at(s, CAL[b])
            if g == ind:
                out.append(s)
        return sorted(out)

    RC = {}

    def ratio_arr(s):
        """每個日曆位置的「當日價格比」：有效 K 棒 c[k]/c[k−1]（壞根 ⇒ 1），其餘 1。"""
        if s in RC:
            return RC[s]
        x = np.ones(NC); sr = series(s)
        if sr is not None:
            pos, c, bad = sr
            for k in range(1, len(pos)):
                if not bad[k]:
                    x[pos[k]] = c[k] / c[k - 1]
        RC[s] = x
        return x

    def index_path(ind, kd, pa, pt):
        """每月初持有市值 W0、逐日乘價格比：回 (日曆位置陣列, 指數值) 於 [pa, pt]，pa 必須是月底。成員 < 5 ⇒ None。"""
        vals = [1.0]; poss = [pa]; I = 1.0
        for (b, e) in MON:
            if e <= pa or b >= pt:
                continue
            mem = members(ind, b)
            if len(mem) < 5:
                return None
            W = np.array([MCm[s][b] if kd == "vw" else 1.0 for s in mem], float)
            end = min(e, pt)
            Gm = np.cumprod(np.stack([ratio_arr(s)[b + 1:end + 1] for s in mem]), axis=1)
            v = I * (W @ Gm) / W.sum()
            vals += list(v); poss += list(range(b + 1, end + 1))
            I = float(v[-1])
        return np.array(poss), np.array(vals)

    k1 = []
    hitw = WIN[WIN.get("達標_vw", pd.Series(False, index=WIN.index)).fillna(False).astype(bool)]
    nonw = WIN[~WIN.index.isin(hitw.index) & WIN["R_vw"].notna()]
    pick = pd.concat([hitw.sample(min(10, len(hitw)), random_state=1), nonw.sample(min(15, len(nonw)), random_state=2)])
    for _, w in pick.iterrows():
        pa, pt = pos_le(w["窗起"]), pos_le(w["窗終"])
        ip = index_path(w["產業"], "vw", pa, pt)
        if ip is None:
            k1.append({"產業": w["產業"], "窗起": w["窗起"], "結果": "成員<5（與主程式不同）", "相符": False}); continue
        rr = ip[1][-1] - 1.0
        q50 = v50(pt) / v50(pa) - 1.0
        hit = bool(rr >= 1.0 and rr >= 2 * q50)
        ok = close(rr, w["R_vw"], 1e-6) and close(q50, w["R0050"], 1e-9) and hit == bool(w["達標_vw"])
        k1.append({"產業": w["產業"], "窗起": w["窗起"], "窗終": w["窗終"], "R手算": rr, "R檔": w["R_vw"], "R0050手算": q50, "R0050檔": w["R0050"],
                   "達標手算": hit, "達標檔": bool(w["達標_vw"]), "相符": bool(ok)})
        log(f"  K1 窗 {w['產業']} {w['窗起']}→{w['窗終']}：手算 {rr:+.6f} 檔 {w['R_vw']:+.6f}｜0050 {q50:+.6f}/{w['R0050']:+.6f}｜達標 {hit}/{w['達標_vw']} {'✔' if ok else '✖'}")
    # 整段
    segpick = []
    sv = SEG[SEG["加權"] == "市值"]; se = SEG[SEG["加權"] == "等權"]
    if len(sv):
        sv2 = sv.assign(_len=pd.to_datetime(sv["最後達標窗終點"]) - pd.to_datetime(sv["起點"])).sort_values("_len")
        segpick += [r for _, r in sv2.head(3).iterrows()]
    if len(se):
        segpick += [r for _, r in se.sort_values("達標窗數").head(1).iterrows()]
    for r in segpick:
        kd = "vw" if r["加權"] == "市值" else "ew"
        S, E = pos_le(r["起點"]), pos_le(r["最後達標窗終點"])
        ip = index_path(r["產業"], kd, S, E)
        if ip is None:
            k1.append({"段號": r["段號"], "結果": "成員<5", "相符": False}); continue
        poss, vals = ip
        H = int(poss[int(np.argmax(vals))])
        gain = vals.max() - 1.0
        ok = (str(CAL[H].date()) == r["高點"]) and close(gain, r["漲幅"], 1e-6)
        k1.append({"段號": r["段號"], "高點手算": str(CAL[H].date()), "高點檔": r["高點"], "漲幅手算": gain, "漲幅檔": r["漲幅"], "相符": bool(ok)})
        log(f"  K1 段 {r['段號']}：高點 {CAL[H].date()}/{r['高點']} 漲幅 {gain:+.6f}/{r['漲幅']:+.6f} {'✔' if ok else '✖'}")
    RES["K1"] = {"筆": len(k1), "相符": int(sum(x["相符"] for x in k1)), "明細": k1}

    # ── K2 併段
    k2 = []
    for kd, lab in (("vw", "市值"), ("ew", "等權")):
        col = f"達標_{kd}"
        if col not in WIN:
            continue
        W2 = WIN[WIN[col].fillna(False).astype(bool)].copy()
        W2["t"] = pd.to_datetime(W2["窗終"]); W2["s"] = pd.to_datetime(W2["窗起"])
        for ind, g in W2.groupby("產業"):
            g = g.sort_values("t")
            grp = []
            for _, w in g.iterrows():
                if grp and w["s"] <= grp[-1][-1]["t"]:
                    grp[-1].append(w)
                else:
                    grp.append([w])
            for gg in grp:
                st = str(gg[0]["s"].date()); en = str(gg[-1]["t"].date())
                m = SEG[(SEG["加權"] == lab) & (SEG["產業"] == ind) & (SEG["起點"] == st)]
                ok = len(m) == 1 and m.iloc[0]["最後達標窗終點"] == en and int(m.iloc[0]["達標窗數"]) == len(gg)
                k2.append(ok)
    n_seg = len(SEG)
    RES["K2"] = {"自己併出段數": len(k2), "檔內段數": n_seg, "逐段相符": int(sum(k2)), "全符": bool(all(k2) and len(k2) == n_seg)}
    log(f"K2 併段：自己 {len(k2)} 段、檔 {n_seg} 段、相符 {sum(k2)}")

    # ── K3 乙
    ME = []
    s_ = pd.Series(np.arange(NC), index=CAL)
    g_ = s_.groupby([CAL.year, CAL.month]).max().to_numpy()
    if CAL[g_[-1]] < CAL[g_[-1]] + pd.offsets.BMonthEnd(0):
        g_ = g_[:-1]
    MEall = [int(x) for x in g_]

    def scan(s, mult, yrs):
        sr = series(s)
        if sr is None:
            return []
        pos, c, bad = sr
        out = []; nxt = -1
        for jj, me in enumerate(MEall):
            if CAL[me] < START or me <= nxt:
                continue
            prev = MEall[jj - 1] if jj > 0 else -1
            k = int(np.searchsorted(pos, me, "right")) - 1
            if k < 0 or pos[k] <= prev or pos[k] <= nxt:
                continue
            lim = CAL[pos[k]] + pd.DateOffset(years=yrs)
            best = -1.0; hk = -1
            for kk in range(k + 1, len(pos)):
                if CAL[pos[kk]] > lim or bad[kk]:
                    break
                if c[kk] > best:
                    best = c[kk]; hk = kk
            if hk > 0 and best >= mult * c[k]:
                out.append((str(CAL[pos[k]].date()), str(CAL[pos[hk]].date()), best / c[k]))
                nxt = pos[hk]
        return out

    k3 = []
    for tag, B, mult, yrs in (("x3", B3, 3.0, 3), ("x5", B5, 5.0, 5)):
        have = sorted(set(B["代號"]))
        pk = list(rng.choice(have, min(20 if tag == "x3" else 20, len(have)), replace=False))
        none = sorted(USE - set(have))
        pk += list(rng.choice(none, min(10, len(none)), replace=False)) if none else []
        for s in pk:
            mine = scan(s, mult, yrs)
            fil = [(r["起點"], r["高點"], r["倍數"]) for _, r in B[B["代號"] == s].iterrows()]
            ok = len(mine) == len(fil) and all(x[0] == y[0] and x[1] == y[1] and close(x[2], y[2], 1e-9) for x, y in zip(mine, fil))
            k3.append({"版": tag, "代號": s, "手算段數": len(mine), "檔段數": len(fil), "相符": bool(ok)})
            if not ok:
                log(f"  K3 ✖ {tag} {s}：手算 {mine[:3]} 檔 {fil[:3]}")
    RES["K3"] = {"檔數": len(k3), "相符": int(sum(x["相符"] for x in k3)), "明細": k3}
    log(f"K3 乙 暴力重掃：{RES['K3']['相符']}／{len(k3)} 檔相符")

    # ── K4 不前視
    def ravail(p):
        y, m = int(p[:4]), int(p[5:]); y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
        return pd.Timestamp(y2, m2, 15 if p >= "2026-01" else 10)

    def pdates(r):
        ds = pd.Timestamp(r["起點"]); d12 = ds - pd.DateOffset(months=12); p12 = pos_le(d12)
        return {"前12月": d12 if p12 < 0 else CAL[p12], "起點": ds, "高點": pd.Timestamp(r["高點"])}

    bad_rev = bad_fs = n_rev = n_fs = 0
    for B in (B3, B5):
        for _, r in B.iterrows():
            dd = pdates(r)
            for p, d in dd.items():
                per = r.get(f"營收期別@{p}")
                if isinstance(per, str) and per:
                    n_rev += 1
                    if not ravail(per) < d:
                        bad_rev += 1
                fa = r.get(f"財報可用@{p}")
                if isinstance(fa, str) and fa:
                    n_fs += 1
                    if not pd.Timestamp(fa) < d:
                        bad_fs += 1
    for _, r in SEG.iterrows():
        dd = pdates(r)
        for p, d in dd.items():
            per = r.get(f"營收期別(最多)@{p}")
            if isinstance(per, str) and per:
                n_rev += 1
                if not ravail(per) < d:
                    bad_rev += 1
    # 原檔重找財報季、營收年增
    fd = pd.read_csv(os.path.join(DATA, "meta", "filing_dates.csv"), dtype=str)
    fd["d"] = pd.to_datetime(fd["uploaded_at"], errors="coerce").dt.normalize()
    fd = fd.dropna(subset=["d"])
    ai1 = fd[fd["doc_code"] == "AI1"].groupby(["stock_id", "year", "season"])["d"].min()
    anyd = fd.groupby(["stock_id", "year", "season"])["d"].min()
    up = anyd.copy(); up.loc[ai1.index] = ai1
    UPS = defaultdict(list)
    for (s, y, q), d in up.items():
        UPS[s].append((d, f"{y}Q{q}"))
    def fnum(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return np.nan
    rawrev = {}
    for f in sorted(glob.glob(os.path.join(DATA, "early", "revenue", "*.csv"))) + sorted(glob.glob(os.path.join(DATA, "mops", "revenue_hist", "*.csv"))):
        x = pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收", "去年當月營收"])
        for s, p, v, l in zip(x["stock_id"], x["period"], x["當月營收"], x["去年當月營收"]):
            rawrev[(s, p)] = (fnum(v), fnum(l))
    smp = B3.sample(min(300, len(B3)), random_state=3)
    fs_ok = fs_n = rv_ok = rv_n = 0; fs_bad = []; rv_bad = []
    for _, r in smp.iterrows():
        s = r["代號"]
        for p, d in pdates(r).items():
            cand = [(dd, q) for dd, q in UPS.get(s, []) if dd < d]
            mine = max(cand, key=lambda z: (int(z[1][:4]), int(z[1][-1])))[1] if cand else ""
            fil = r.get(f"財報季@{p}"); fil = fil if isinstance(fil, str) else ""
            fs_n += 1
            if mine == fil:
                fs_ok += 1
            else:
                fs_bad.append((s, p, str(d.date()), mine, fil))
            per = r.get(f"營收期別@{p}")
            if isinstance(per, str) and per and (s, per) in rawrev:
                v, l = rawrev[(s, per)]
                y = v / l - 1 if (np.isfinite(v) and np.isfinite(l) and l > 0) else np.nan
                rv_n += 1
                if close(y, r[f"營收年增@{p}"], 1e-9):
                    rv_ok += 1
                else:
                    rv_bad.append((s, per, y, r[f"營收年增@{p}"]))
    RES["K4"] = {"營收期別_檢查": n_rev, "營收可用日≥時點": bad_rev, "財報可用_檢查": n_fs, "財報上傳日≥時點": bad_fs,
                 "財報季重找_抽": fs_n, "財報季重找_相符": fs_ok, "財報季不符例": fs_bad[:10],
                 "營收年增重算_抽": rv_n, "營收年增重算_相符": rv_ok, "營收年增不符例(多為 revenue_delisted 補格)": rv_bad[:10]}
    log(f"K4 不前視：營收 {n_rev} 格中可用日 ≥ 時點 {bad_rev}；財報 {n_fs} 格中上傳日 ≥ 時點 {bad_fs}；財報季重找 {fs_ok}/{fs_n}；營收年增重算 {rv_ok}/{rv_n}")

    # ── K5 價格類、per、法人、0050
    smp = B3.sample(min(60, len(B3)), random_state=4)
    k5 = defaultdict(lambda: [0, 0])
    PERc = {}

    def per_ser(s):
        if s in PERc:
            return PERc[s]
        x = np.full(NC, np.nan)
        f = os.path.join(Zm["data"], "stocks_per", f"{s}.csv")
        if os.path.exists(f):
            z = pd.read_csv(f, dtype={"date": str}, usecols=["date", "per"])
            ix = Zm["cal"].get_indexer(pd.to_datetime(z["date"])); v = pd.to_numeric(z["per"], errors="coerce").to_numpy(float)
            ok = ix >= 0; x[ix[ok] + NE] = np.where(v[ok] > 0, v[ok], np.nan)
        PERc[s] = x
        return x
    EP = {}
    for sub in ("per", "otcper"):
        for f in sorted(glob.glob(os.path.join(DATA, "early", sub, "*.csv"))):
            z = pd.read_csv(f, dtype={"stock_id": str, "date": str}, usecols=["date", "stock_id", "per"])
            z = z[z["stock_id"].isin(set(smp["代號"]))]
            for s, d, v in zip(z["stock_id"], z["date"], pd.to_numeric(z["per"], errors="coerce")):
                EP[(s, d)] = v
    for _, r in smp.iterrows():
        s = r["代號"]; sr = series(s)
        x = per_ser(s).copy()
        for (ss, d), v in EP.items():
            if ss == s and v > 0:
                k = Ze["cal"].get_indexer([pd.Timestamp(d)])[0]
                if k >= 0:
                    x[k] = v
        inst = np.zeros(NC); cov = -1; sh = np.full(NC, np.nan)
        for Z, off, wn in ((Ze, 0, "早年"), (Zm, NE, "主")):
            f = os.path.join(Z["data"], "stocks_inst", f"{s}.csv")
            if os.path.exists(f):
                y = pd.read_csv(f, dtype={"date": str}, usecols=["date", "foreign", "trust"])
                ix = Z["cal"].get_indexer(pd.to_datetime(y["date"])); ok = ix >= 0
                inst[ix[ok] + off] = (pd.to_numeric(y["foreign"], errors="coerce").fillna(0) + pd.to_numeric(y["trust"], errors="coerce").fillna(0)).to_numpy(float)[ok]
                if wn == "早年" and Ze["mk"].get(s) == "twse" and ok.any() and cov < 0:
                    cov = max(int(ix[ok].min()), int(Ze["cal"].searchsorted(pd.Timestamp("2012-05-02"))))
            if wn == "主" and cov < 0:
                cov = NE
            f2 = os.path.join(Z["data"], "stocks", f"{s}.csv")
            if os.path.exists(f2):
                y = pd.read_csv(f2, dtype={"date": str}, usecols=["date", "shares"])
                ix = Z["cal"].get_indexer(pd.to_datetime(y["date"])); ok = ix >= 0
                sh[ix[ok] + off] = pd.to_numeric(y["shares"], errors="coerce").to_numpy(float)[ok]
        sh = pd.Series(sh).ffill().to_numpy()
        dd = pdates(r); pp = {k: (pos_le(v) if v >= CAL[0] else -1) for k, v in dd.items()}
        for p, q in pp.items():
            # per
            mine = np.nan
            if q >= 0 and np.isfinite(x[q]):
                w = x[max(0, q - 1249):q + 1]; w = w[np.isfinite(w)]
                mine = float((w <= x[q]).mean()) if len(w) >= 750 else np.nan
            k5["本益比5年位置"][0] += 1; k5["本益比5年位置"][1] += close(mine, r[f"本益比5年位置@{p}"], 1e-9)
            # 距一年高點
            mine = np.nan
            if q >= 0 and sr is not None:
                pos, c, bad = sr
                k1_ = int(np.searchsorted(pos, q, "right")) - 1
                if k1_ >= 0 and q - pos[k1_] <= 20:
                    k0 = int(np.searchsorted(pos, q - 249, "left"))
                    for kk in range(k1_, k0, -1):
                        if bad[kk]:
                            k0 = kk; break
                    mine = c[k1_] / c[k0:k1_ + 1].max() - 1
            k5["距一年高點"][0] += 1; k5["距一年高點"][1] += close(mine, r[f"距一年高點@{p}"], 1e-9)
            # 0050
            mine = np.nan
            if q >= 0:
                kk = int(np.searchsorted(P50, q, "right")) - 1
                if kk >= 199:
                    mine = C50[kk] / C50[kk - 199:kk + 1].mean() - 1
            k5["0050乖離200日"][0] += 1; k5["0050乖離200日"][1] += close(mine, r[f"0050乖離200日@{p}"], 1e-9)
        for nm, (p1, p2) in (("前12月→起點", (pp["前12月"], pp["起點"])), ("起點→高點", (pp["起點"], pp["高點"]))):
            mine = np.nan
            if p1 >= 0 and cov >= 0 and p1 >= cov and np.isfinite(sh[p2]) and sh[p2] > 0:
                mine = inst[p1 + 1:p2 + 1].sum() / sh[p2]
            k5["外資投信"][0] += 1; k5["外資投信"][1] += close(mine, r[f"外資投信持股變化@{nm}"], 1e-6)
    RES["K5"] = {k: {"抽": v[0], "相符": v[1]} for k, v in k5.items()}
    log(f"K5 {RES['K5']}")

    # ── K6 彙總重算
    F1 = pd.read_csv(os.path.join(OD, "freq_甲.csv")); F2 = pd.read_csv(os.path.join(OD, "freq_乙.csv"))
    ok6 = []
    for _, r in F1.iterrows():
        for lab in ("市值", "等權"):
            sub = SEG[(SEG["加權"] == lab) & (pd.to_datetime(SEG["起點"]).dt.year == r["起點年"])]
            ok6.append(len(sub) == r[f"甲段數_{lab}"] and sub["產業"].nunique() == r[f"甲涉及產業數_{lab}"])
    for _, r in F2.iterrows():
        for tag, B in (("x3", B3), ("x5", B5)):
            sub = B[pd.to_datetime(B["起點"]).dt.year == r["起點年"]]
            ok6.append(len(sub) == r[f"乙段數_{tag}"])
            if len(sub):
                ok6.append(close(sub["與甲相交_市值"].mean(), r[f"乙與甲相交比例_{tag}_市值"], 1e-9))
    for lab in ("市值", "等權"):
        ok6.append(int(F1[f"甲段數_{lab}"].sum()) == int((SEG["加權"] == lab).sum()))      # 頻率表列加總 ＝ 全部段（含 2004-12-31 左截斷）
    for tag, B in (("x3", B3), ("x5", B5)):
        ok6.append(int(F2[f"乙段數_{tag}"].sum()) == len(B))
    log(f"  K6 頻率表加總：甲市值 {int(F1['甲段數_市值'].sum())}／{int((SEG['加權'] == '市值').sum())}、乙x3 {int(F2['乙段數_x3'].sum())}／{len(B3)}")
    OV = pd.read_csv(os.path.join(OD, "乙_重疊.csv"))
    for _, r in OV[OV["起點期"] == "全期"].iterrows():
        B = B3 if r["版"] == "x3" else B5
        ok6.append(len(B) == r["段數"] and close(B["與甲相交_市值"].mean(), r["與甲相交_市值"], 1e-9) and close(B["起點在甲段內_等權"].mean(), r["起點在甲段內_等權"], 1e-9))
    CS = pd.read_csv(os.path.join(OD, "丙_乙彙總.csv"))
    for _, r in CS[CS["起點期"] == "全期"].iterrows():
        B = B3 if r["版"] == "x3" else B5
        v = B[r["欄"]].to_numpy(float); v = v[np.isfinite(v)]
        ok6.append(len(v) == r["有值"] and (len(v) == 0 or close(float(np.median(v)), r["中位"], 1e-9)))
    RES["K6"] = {"項": len(ok6), "相符": int(sum(ok6))}
    log(f"K6 彙總重算：{sum(ok6)}／{len(ok6)}")

    # ── K7
    lk = subprocess.run([sys.executable, "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True)
    st = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines()
    mod = [x for x in st if not x.startswith("??")]
    RES["K7"] = {"策略鎖": (lk.stdout + lk.stderr).strip().splitlines()[-1:] , "已追蹤檔有改動": mod,
                 "本件新增": [x for x in st if "BigRun" in x]}
    log(f"K7 策略鎖：{RES['K7']['策略鎖']}｜已追蹤檔改動 {len(mod)} 筆（應只有本件開工前就有的 forward/yl_rule）")
    json.dump(RES, open(os.path.join(OD, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(OD, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
