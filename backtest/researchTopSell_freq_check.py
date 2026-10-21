# -*- coding: utf-8 -*-
"""頂部樣子 seq1 頻率表【獨立對帳】——回測線計算子代理。⛔ 只讀結果夾、不改任何既有檔（只寫 resultsTopSell/freq/check.json、check.log）；⛔ 不算任何報酬。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTopSell_freq_check [--dry]

K1 登錄 sha 獨立重算（信箱根目錄＋_封存-*，去 pw1 行 sha256 前 16 碼）。
K2 資料同源：git diff 自跑（快照 A／B 對最新 origin/main 的 fin_hist、filing_dates、industry_hist、early/per、early/otcper、tdcc_hist 相同）；
   主 stocks_per：以最新 origin/main 逐檔重讀，母體列（主世界月底）面板 per 對新 per 逐格比 ⇒ 差異格數、T1a 會翻的列數照報。
K3 訊號自算（另一條路）：
   T1a ＝ 面板 per 60 個月底窗自算位置；T1b ＝ 最新 main fin_hist eps_ytd ＋ filing_dates（自寫：AI1 最早、否則全部最早；上傳日 ＜ t；2012Q1 起，同面板）；
   ROE ＝ fin_hist nip_ytd 單季 4 季和 ÷ equity_parent 自算 ⇒ 對 events ROE（面板 float32）；產業中位 ＝ pandas groupby 自算 ⇒ 對 events；
   另以同一 groupby、自算 EPS 對 resultsBigRun5/逐段 的「ROE產業中位@高點」「近4季EPS@高點」逐段比（證明本件與 BigRun5 同式）；
   集保 ＝ 最新 main tdcc_hist level 15 pct 自讀（月底前一交易日或更早、14 交易日內最近一週；與 12 個月底前之差）⇒ 對面板。
K4 母體自算：主世界月底 2018-01～2026-08（36 月窗不跨接縫）以 panel_主 自寫 pandas 版重算 閘、R36（壞根截）、距一年高點 ⇒ 符合集合與 events 完全相同；
   全期 去重 由 events 自算相同；合併日曆 距5年低點 對面板逐格（驗接縫與 BigRun3 同）。
K5 freq_段.csv 主要欄由 events.csv.gz 自算相同。
K6 輸出無報酬欄；策略鎖 25 支相符；git 工作樹相對開跑前只多 researchTopSell_freq*.py 與 resultsTopSell/。
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import io
import json
import os
import pickle
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchTopSell_freq as TS             # noqa: E402
from backtest import researchIndMom_freq as IMF             # noqa: E402
from backtest import researchAddOn as RA                    # noqa: E402

MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"


def sha_of(f):
    b = open(f, "rb").read()
    return hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]


def gshow(sha, path):
    p = subprocess.run(["git", "show", f"{sha}:{path}"], capture_output=True)
    return p.stdout if p.returncode == 0 else None


def b3(x):
    return None if (x is None or (isinstance(x, float) and np.isnan(x)) or x == "") else (str(x) == "True")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry", action="store_true"); a = ap.parse_args()
    out = os.path.join(TS.WORK, "dry") if a.dry else TS.OUT
    log = RA.log_to(os.path.join(out, "check.log"))
    CK = {}
    # ── K1
    fs = [f for d in [MAILBOX] + sorted(glob.glob(os.path.join(MAILBOX, "_封存-*"))) for f in glob.glob(os.path.join(d, "*.md")) if f"sha{TS.REG_SHA}" in os.path.basename(f)]
    CK["K1_登錄sha"] = {"檔": [os.path.basename(f) for f in fs], "相符": bool(fs) and all(sha_of(f) == TS.REG_SHA for f in fs)}
    log(f"[K1] {CK['K1_登錄sha']}")
    if not CK["K1_登錄sha"]["相符"]:
        raise SystemExit("⛔ K1")
    J = json.load(open(os.path.join(out, "freq.json"), encoding="utf-8")); sha = J["origin/main"]
    # ── K2
    same = {}
    for base, paths in ((TS.RB3.SHA_A, TS.SAME_A), (TS.RB3.SHA_B, TS.SAME_B)):
        for p in paths:
            same[p] = subprocess.run(["git", "diff", "--quiet", base, sha, "--", p]).returncode == 0
    CK["K2_快照同源"] = same
    if not all(same.values()):
        raise SystemExit(f"⛔ K2 {same}")
    EV = pd.read_csv(os.path.join(out, "events.csv.gz"), dtype={"sid": str, "產業": str}, keep_default_na=True)
    EV["產業"] = EV["產業"].fillna("")
    for c in ("T1a", "T1b", "T1", "T2", "T3", "S", "S12", "T1a′(面板每日)"):
        EV[c] = [b3(x) for x in EV[c]]
    PN = pickle.load(open(TS.PANEL, "rb")); P = PN["P"]; SIDS = PN["SIDS"]; MEp = np.asarray(PN["MEp"]); K = len(MEp); META = PN["META"]; INDM = PN["INDM"]
    Ze = IMF.build_panel("早年", 2, log); Zm = IMF.build_panel("主", 2, log)
    CAL = Ze["cal"].append(Zm["cal"]); NE = Ze["n0"]
    tpos = EV["_k"].map(lambda k: int(MEp[k]))
    # 主 stocks_per 逐格
    mm = EV[tpos >= NE]; diff = 0; flip = 0; ncell = 0
    for s, g in mm.groupby("sid"):
        raw = gshow(sha, f"data/stocks_per/{s}.csv")
        if raw is None:
            continue
        x = pd.read_csv(io.BytesIO(raw), dtype={"date": str}, usecols=["date", "per"]).drop_duplicates("date", keep="last")
        x["per"] = pd.to_numeric(x["per"], errors="coerce"); mp = dict(zip(pd.to_datetime(x["date"]), x["per"]))
        i = int(g["_i"].iloc[0])
        for k in range(K):
            if MEp[k] < NE:
                continue
            v_new = mp.get(CAL[MEp[k]], np.nan); v_new = v_new if (np.isfinite(v_new) and v_new > 0) else np.nan
            v_old = float(P["本益比"][i, k])
            ncell += 1
            if np.isfinite(v_new) != np.isfinite(v_old) or (np.isfinite(v_new) and abs(v_new - v_old) > 1e-3 * max(1, abs(v_new))):
                diff += 1
                if k in set(g["_k"]):
                    flip += 1
    CK["K2_stocks_per主表"] = {"比對格（母體股×主世界月底）": ncell, "與最新 main 不同格": diff, "其中母體列": flip}
    log(f"[K2] {CK['K2_stocks_per主表']}")
    # ── K3 T1a
    PE = P["本益比"].astype(float); bad = 0
    for i, k, pos in zip(EV["_i"], EV["_k"], EV["本益比5年月底位置"]):
        w = pd.Series(PE[i, max(0, k - 59):k + 1]).dropna(); v = PE[i, k]
        mine = (w.le(v).sum() / len(w)) if (np.isfinite(v) and len(w) >= 36) else np.nan
        if np.isfinite(mine) != np.isfinite(pos) or (np.isfinite(mine) and abs(mine - pos) > 1e-12):
            bad += 1
    t1a_chk = int(sum((b3(str(x >= 0.8)) if np.isfinite(x) else None) != y for x, y in zip(EV["本益比5年月底位置"], EV["T1a"])))
    CK["K3_T1a"] = {"位置不符": bad, "旗標不符": t1a_chk}
    # T1b 自算
    FD = os.path.join(TS.WORK, f"main_{sha[:12]}", "data")
    fd = pd.read_csv(io.BytesIO(gshow(sha, "data/meta/filing_dates.csv")), dtype=str)
    fd["d"] = pd.to_datetime(fd["uploaded_at"].str[:10], errors="coerce"); fd = fd.dropna(subset=["d"])
    fd["q"] = fd["year"].astype(int) * 4 + fd["season"].astype(int) - 1
    a1 = fd[fd["doc_code"] == "AI1"].groupby(["stock_id", "q"])["d"].min(); al = fd.groupby(["stock_id", "q"])["d"].min()
    AV = al.to_dict(); AV.update(a1.to_dict())
    AVS = {}
    for (s, q), d in AV.items():
        if q >= 2012 * 4:
            AVS.setdefault(s, []).append((d, q))
    L = []
    for f in sorted(glob.glob(os.path.join(FD, "mops", "fin_hist", "*.csv"))):
        b = os.path.basename(f)[:6]; q = int(b[:4]) * 4 + int(b[5]) - 1
        x = pd.read_csv(f, dtype={"stock_id": str}, usecols=["stock_id", "eps_ytd", "nip_ytd", "equity_parent"]); x["q"] = q; L.append(x)
    FN = pd.concat(L).drop_duplicates(["stock_id", "q"], keep="last")
    for c in ("eps_ytd", "nip_ytd", "equity_parent"):
        FN[c] = pd.to_numeric(FN[c], errors="coerce")
    FNd = {s: g.set_index("q") for s, g in FN.groupby("stock_id")}

    def sq(df, col, q):
        if q not in df.index:
            return np.nan
        v = df.at[q, col]
        if q % 4 == 0:
            return v
        if q - 1 not in df.index:
            return np.nan
        return v - df.at[q - 1, col]

    def selq(s, t):
        c = [q for d, q in AVS.get(s, []) if d < t]
        return max(c) if c else -1

    def eps_roe(s, t):
        q = selq(s, t); df = FNd.get(s)
        if q < 0 or df is None:
            return np.nan, np.nan, q
        e = [sq(df, "eps_ytd", j) for j in range(q - 3, q + 1)]; n = [sq(df, "nip_ytd", j) for j in range(q - 3, q + 1)]
        eq = df.at[q, "equity_parent"] if q in df.index else np.nan
        ev = float(sum(e)) if np.isfinite(e).all() else np.nan
        rv = float(sum(n) / eq) if (np.isfinite(n).all() and np.isfinite(eq) and eq > 0) else np.nan
        return ev, rv, q
    be = br = bq = 0; t1b_bad = 0
    for s, i, k, e0, r0 in zip(EV["sid"], EV["_i"], EV["_k"], EV["近4季EPS"], EV["ROE"]):
        t = CAL[MEp[k]]; ev, rv, q = eps_roe(s, t)
        if q != int(META["fs_qk"][i, k]):
            bq += 1
        if np.isfinite(ev) != np.isfinite(e0) or (np.isfinite(ev) and abs(ev - e0) > 1e-9):
            be += 1
        if np.isfinite(rv) != np.isfinite(r0) or (np.isfinite(rv) and abs(rv - r0) > 1e-5 * max(1, abs(rv))):
            br += 1
    for e0, y in zip(EV["近4季EPS"], EV["T1b"]):
        if ((e0 <= 0) if np.isfinite(e0) else None) != y:
            t1b_bad += 1
    CK["K3_EPS_ROE自算"] = {"列": len(EV), "選季不同": bq, "近4季EPS不同": be, "ROE不同(相對1e-5)": br, "T1b旗標不符": t1b_bad}
    log(f"[K3 T1] {CK['K3_T1a']}｜{CK['K3_EPS_ROE自算']}")
    # 產業中位 groupby
    ROE = P["ROE"].astype(float)
    df = pd.DataFrame({"i": np.repeat(np.arange(len(SIDS)), K), "k": np.tile(np.arange(K), len(SIDS)), "ind": INDM.ravel(), "roe": ROE.ravel()})
    df = df[(df["ind"] != "") & np.isfinite(df["roe"])]
    MD = df.groupby(["ind", "k"])["roe"].median().to_dict()
    mb = 0
    for ind, k, m0 in zip(EV["產業"], EV["_k"], EV["產業ROE中位"]):
        m = MD.get((ind, k), np.nan) if ind else np.nan
        if np.isfinite(m) != np.isfinite(m0) or (np.isfinite(m) and abs(m - m0) > 1e-12):
            mb += 1
    t2b = 0
    for r, m, y in zip(EV["ROE"], EV["產業ROE中位"], EV["T2"]):
        if ((r < m) if (np.isfinite(r) and np.isfinite(m)) else None) != y:
            t2b += 1
    B5 = pd.read_csv("backtest/resultsBigRun5/逐段.csv.gz", dtype={"代號": str}, usecols=["代號", "起點", "高點", "ROE產業中位@高點", "近4季EPS@高點", "月底產業@高點"])
    Y = pd.read_csv("backtest/resultsBigRun3/乙_全表.csv.gz", dtype={"代號": str}, usecols=["代號", "起點", "_i", "_k高點"])
    if len(B5) != len(Y) or not (B5["代號"].values == Y["代號"].values).all():
        raise SystemExit("⛔ BigRun5 逐段 與 乙_全表 列不對齊")
    b5m = b5e = n5 = 0
    for (_, r), i, k in zip(B5.iterrows(), Y["_i"], Y["_k高點"]):
        if not (0 <= k < K):
            continue
        n5 += 1; ind = INDM[i, k]
        m = MD.get((ind, k), np.nan) if ind else np.nan; m0 = r["ROE產業中位@高點"]
        if np.isfinite(m) != np.isfinite(m0) or (np.isfinite(m) and abs(m - m0) > 1e-9):
            b5m += 1
        ev, _, _ = eps_roe(r["代號"], CAL[MEp[k]]); e0 = r["近4季EPS@高點"]
        if np.isfinite(ev) != np.isfinite(e0) or (np.isfinite(ev) and abs(ev - e0) > 1e-6):
            b5e += 1
    CK["K3_產業中位"] = {"events 中位不同": mb, "T2旗標不符": t2b, "對 BigRun5 逐段（高點）比對段": n5, "ROE產業中位不同": b5m, "近4季EPS不同": b5e}
    log(f"[K3 T2] {CK['K3_產業中位']}")
    # 集保自讀
    L = []
    for y in range(2017, 2027):
        raw = gshow(sha, f"data/tdcc_hist/{y}.parquet")
        if raw is None:
            continue
        x = pd.read_parquet(io.BytesIO(raw), columns=["date", "stock_id", "level", "pct"])
        x = x[x["level"] == 15]; x = x.assign(date=pd.to_datetime(x["date"].astype(str)), stock_id=x["stock_id"].astype(str))
        L.append(x[["date", "stock_id", "pct"]])
    TD = pd.concat(L); TD = TD[np.isfinite(TD["pct"].astype(float))]
    TDs = {s: (g["date"].to_numpy(), g["pct"].to_numpy(float)) for s, g in TD.groupby("stock_id")}

    def tdv(s, k):
        p = int(MEp[k]) - 1; lo = p - 14
        if s not in TDs or k < 0:
            return np.nan
        d, v = TDs[s]
        # 資料日非交易日 ⇒ 記在其後第一個交易日（面板同）；取記帳位置在 [lo, p] 的最後一筆
        pos = CAL.searchsorted(d)
        m = (pos >= max(0, lo)) & (pos <= p)
        return float(v[m][np.argmax(pos[m])]) if m.any() else np.nan
    tb = tn = 0; alive_gap = []
    TD12 = P["集保千張大戶比12月變化"].astype(float); MCAP = P["市值(億)"].astype(float)
    for s, i, k, f_, sg in zip(EV["sid"], EV["_i"], EV["_k"], EV["入判"], EV["段"]):
        mine = tdv(s, k) - tdv(s, k - 12) if k >= 12 else np.nan
        v0 = TD12[i, k]; tn += 1
        if np.isfinite(mine) != np.isfinite(v0) or (np.isfinite(mine) and abs(mine - v0) > 1e-4):
            # 面板只在「該月底存活」（最後有效 K 棒距月底 ≤ 20 交易日，市值欄有值）時記集保值 ⇒ 12 個月前月底非存活 ⇒ 面板記缺（照面板）
            if not np.isfinite(v0) and (not np.isfinite(MCAP[i, k - 12]) or not np.isfinite(MCAP[i, k])):
                alive_gap.append({"sid": s, "月": EV.loc[(EV["sid"] == s) & (EV["_k"] == k), "月"].iloc[0], "入判": bool(f_), "段": sg,
                                  "自算12月變化": round(float(mine), 4)})
            else:
                tb += 1
    t3b = int(sum(((v < 0) if np.isfinite(v) else None) != y for v, y in zip([TD12[i, k] for i, k in zip(EV["_i"], EV["_k"])], EV["T3"])))
    CK["K3_集保"] = {"列": tn, "12月變化不同(無法解釋)": tb, "T3旗標不符": t3b, "面板非存活月記缺（照面板，T3 不可判）": alive_gap}

    log(f"[K3 T3] {CK['K3_集保']}")
    # S、S12 三值
    def k3(*xs):
        return True if all(x is True for x in xs) else (False if any(x is False for x in xs) else None)
    t1b2 = sum(k3x != y for k3x, y in zip([True if (p_ is True or q_ is True) else (False if (p_ is False and q_ is False) else None) for p_, q_ in zip(EV["T1a"], EV["T1b"])], EV["T1"]))
    sb = sum(k3(x, y_, z) != s_ for x, y_, z, s_ in zip(EV["T1"], EV["T2"], EV["T3"], EV["S"]))
    s12b = sum(k3(x, y_) != s_ for x, y_, s_ in zip(EV["T1"], EV["T2"], EV["S12"]))
    CK["K3_三值組合"] = {"T1不符": int(t1b2), "S不符": int(sb), "S12不符": int(s12b)}
    # ── K4 母體（主世界 2018-01～）
    Cm, Bm, Gm = Zm["C"], Zm["BAD"], Zm["G"]; calm = Zm["cal"]
    ks = [k for k in range(K) if MEp[k] >= NE and CAL[MEp[k]] >= pd.Timestamp("2018-01-01")]
    mine = set()
    for j, s in enumerate(Zm["sids"]):
        ser = pd.Series(Cm[j]); ok = ser.notna().to_numpy()
        if not ok.any():
            continue
        posv = np.flatnonzero(ok); badv = Bm[j][posv]
        for k in ks:
            p = int(MEp[k]) - NE
            if not (Gm[j, p] and ok[p]):
                continue
            # 距一年高點：日曆位置 [p−249, p] 有效 K 棒，最後一個壞根起
            def cut(idx):
                b_ = idx[1:][badv[idx[1:]]]
                return int(b_[-1]) if len(b_) else int(idx[0])
            idx = np.flatnonzero((posv >= p - 249) & (posv <= p)); st = cut(idx)
            hi = float(np.float32(Cm[j, p] / Cm[j, posv[st:idx[-1] + 1]].max() - 1))
            p36 = int(MEp[k - 36]) - NE
            idx = np.flatnonzero((posv > p36) & (posv <= p)); st = cut(idx)
            r36 = Cm[j, p] / Cm[j, posv[st:idx[-1] + 1]].min()
            if r36 >= 3 and hi >= -0.2:
                mine.add((s, k))
    theirs = set(zip(EV.loc[EV["_k"].isin(ks), "sid"], EV.loc[EV["_k"].isin(ks), "_k"]))
    if a.dry:
        sm = set(J["乾跑股"]); mine = {x for x in mine if x[0] in sm}
    CK["K4_母體主世界2018起"] = {"自算": len(mine), "events": len(theirs), "只在自算": sorted(mine - theirs)[:10], "只在events": sorted(theirs - mine)[:10],
                             "相同": mine == theirs}
    log(f"[K4] {CK['K4_母體主世界2018起']}")
    # 去重
    dd_bad = 0
    for s, g in EV.sort_values("_k").groupby("sid"):
        last = -999
        for k, f in zip(g["_k"], g["入判"]):
            take = k - last >= 6
            if take:
                last = k
            if take != bool(f):
                dd_bad += 1
    CK["K4_去重"] = {"不符": dd_bad}
    # 合併日曆 距5年低點 對面板
    CAL2, NE2, C, BAD, G, TRD, UPL, seam, ie, im = TS.merged_prices(Ze, Zm, SIDS)
    lo5 = P["距5年低點"].astype(float); mx = 0.0; n = 0
    for i in range(len(SIDS)):
        vp = np.flatnonzero(np.isfinite(C[i]))
        if not len(vp):
            continue
        vc = C[i, vp]; vb = BAD[i, vp]
        for k in np.flatnonzero(np.isfinite(lo5[i])):
            p = int(MEp[k]); kk = int(np.searchsorted(vp, p, "right")) - 1
            k5 = int(np.searchsorted(vp, p - 1249, "left")); bb = np.flatnonzero(vb[k5 + 1:kk + 1]); k5 = k5 + 1 + int(bb[-1]) if len(bb) else k5
            v = vc[kk] / vc[k5:kk + 1].min() - 1; mx = max(mx, abs(v - lo5[i, k]) / max(1.0, abs(v))); n += 1
    CK["K4_合併日曆距5年低點對面板"] = {"格": n, "最大相對差": mx, "接縫": seam}
    log(f"[K4 接縫] {CK['K4_合併日曆距5年低點對面板']}")
    # ── K5
    FR = pd.read_csv(os.path.join(out, "freq_段.csv"), encoding="utf-8-sig")
    EV["可用"] = EV["可用"].astype(str) == "True"; EV["入判"] = EV["入判"].astype(str) == "True"
    k5b = []
    for _, r in FR.iterrows():
        d = EV[(EV["段"] == r["段"]) & EV["入判"]]; col = r["判定訊號"]
        st = int((d[col] == True).sum()); sf = int((d[col] == False).sum())  # noqa: E712
        u = d[(d[col] == True) & d["可用"]]  # noqa: E712
        mine = [len(d), st, sf, len(u), u["月"].nunique(), min(len(u), u["月"].nunique())]
        theirs = [r["母體入判列"], r["S成立"], r["S不成立"], r["S成立可用事件"], r["S成立可用月數"], r["n_eff"]]
        if [int(x) for x in mine] != [int(x) for x in theirs]:
            k5b.append((r["段"], mine, theirs))
    CK["K5_段表自算"] = {"不符": k5b}
    # ── K6
    cols = list(EV.columns) + [c for f in glob.glob(os.path.join(out, "*.csv")) for c in pd.read_csv(f, nrows=0, encoding="utf-8-sig").columns]
    badc = [c for c in cols if any(w in c for w in ("報酬", "年化", "淨值", "回落", "價格", "收盤", "開盤價", "d值"))]
    lk = subprocess.run([os.path.expanduser("~/tw-p16/.venv/bin/python"), "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True,
                        env={**os.environ, "PYTHONPATH": os.path.expanduser("~/tw-p17")})
    lock = (lk.stdout + lk.stderr).strip().splitlines()[-1:]
    before = set(open(os.path.join(TS.WORK, "git_before.txt")).read().splitlines())
    now = set(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines())
    extra = sorted(now - before)
    CK["K6"] = {"報酬類欄": badc, "策略鎖": lock, "git 新增（相對開跑前）": extra,
                "git 只多本件": all("TopSell" in x for x in extra)}
    ok = (CK["K1_登錄sha"]["相符"] and all(same.values()) and CK["K3_T1a"] == {"位置不符": 0, "旗標不符": 0}
          and all(v == 0 for k_, v in CK["K3_EPS_ROE自算"].items() if k_ != "列") and CK["K3_產業中位"]["events 中位不同"] == 0 and CK["K3_產業中位"]["T2旗標不符"] == 0
          and CK["K3_產業中位"]["ROE產業中位不同"] == 0 and CK["K3_產業中位"]["近4季EPS不同"] == 0 and CK["K3_集保"]["12月變化不同(無法解釋)"] == 0 and CK["K3_集保"]["T3旗標不符"] == 0
          and all(v == 0 for v in CK["K3_三值組合"].values()) and CK["K4_母體主世界2018起"]["相同"] and CK["K4_去重"]["不符"] == 0
          and CK["K4_合併日曆距5年低點對面板"]["最大相對差"] < 1e-5 and not k5b and not badc and "相符" in "".join(lock) and CK["K6"]["git 只多本件"])
    CK["全過"] = bool(ok)
    log(f"[K5] {CK['K5_段表自算']}｜[K6] {CK['K6']}｜全過 {ok}")
    json.dump(CK, open(os.path.join(out, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)


if __name__ == "__main__":
    main()
