# -*- coding: utf-8 -*-
"""researchAddOnMkt_v2 獨立查核（回測線計算子代理，2026-10-14）。⛔ 只讀、只寫 resultsAddOn/mkt_v2/check.json。
獨立寫法（⛔ 不 import researchAddOn／researchAddOnMkt_v2 的任何計算函式）：
 C1 歷史主數字：觸發 ＝ resultsAddOn/triggers.csv.gz（原跑）登錄格；出場 ＝ exit5/exits.csv.gz（S_出場日、S_價）；每條路徑持股與金額 ＝ exit5/paths.csv.gz；
    大盤旗標 ＝ 自己 git show 同一 main sha 的 market_index.csv、自己算 20 日平均；收盤 ＝ ~/addonwork 世界快取 closes（只讀 pickle）；
    子帳戶 ＝ 逐日迴圈（開盤先用子帳戶現金、不足再撥入；收盤出場入帳）⇒ 淨損益、年化、回落；比對 mkt_v2.json 的 營量、營飆中位、合計中位，與 events.csv 的 r0／旗標；③①點值
 C2 成交：自己讀原始 csv、自己的 tick 表與漲停價 ⇒ 鎖漲停旗標、跳空分位數，比對 events.csv 與 json
 C3 前瞻門檻：自己寫的月塊拔靴＋群集 z，另一個種子，N*−40、N*、N*＋40 三格檢定力與 power.csv 比（容差 0.03）；去右尾差、每年觸發頻率、年數重算
    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchAddOnMkt_v2_check
"""
from __future__ import annotations

import io
import json
import math
import os
import pickle
import subprocess

import numpy as np
import pandas as pd

os.chdir(os.path.expanduser("~/tw-p17"))
OUT = "backtest/resultsAddOn/mkt_v2"
AOD = "backtest/resultsAddOn"
COSTX = 0.001425 * 2 + 0.003
CELLX = {"營量": "A2", "營飆": "A1"}
SEGP = {"主": {"探索": (523, 1711), "確認": (1712, 2835), "主窗": (523, 2835)}, "早年": {"早年": (249, 2711)}}
SEGU = {"探索": (523, 1711), "確認": (1711, 2835), "主窗": (523, 2835), "早年": (249, 2711)}
WN = {"探索": "主", "確認": "主", "主窗": "主", "早年": "早年"}


def tick(p):
    for lim, t in ((10, .01), (50, .05), (100, .1), (500, .5), (1000, 1.0)):
        if p < lim:
            return t
    return 5.0


def lup(ref, lim):
    raw = ref * (1 + lim); t = tick(raw)
    return math.floor(raw / t + 1e-9) * t


def main():
    J = json.load(open(os.path.join(OUT, "mkt_v2.json"), encoding="utf-8"))
    EVm = pd.read_csv(os.path.join(OUT, "events.csv"), dtype={"sid": str})
    sha = J["指數"]["main sha"]
    txt = subprocess.run(["git", "show", f"{sha}:data/history/market_index.csv"], capture_output=True, text=True, check=True).stdout
    ix = pd.read_csv(io.StringIO(txt), parse_dates=["date"]).dropna(subset=["close"]).drop_duplicates("date", keep="last").sort_values("date")
    ix = ix[ix["close"] > 0].set_index("date")["close"]
    up = (ix > ix.rolling(20).mean()) & ix.rolling(20).mean().notna()
    W = {wn: pickle.load(open(os.path.expanduser(f"~/addonwork/world_{wn}.pkl"), "rb")) for wn in ("主", "早年")}
    ENG = pickle.load(open(os.path.expanduser("~/addonwork/engine_200.pkl"), "rb"))
    tr = pd.read_csv(os.path.join(AOD, "triggers.csv.gz"), dtype={"sid": str})
    tr = tr[(tr["結果"] == "加碼") & (tr["格"] == tr["策略"].map(CELLX))].copy()
    ex = pd.read_csv(os.path.join(AOD, "exit5", "exits.csv.gz"), dtype={"sid": str}, usecols=["世界", "策略", "sid", "tb", "格", "S_出場日", "S_價"])
    ev = tr.merge(ex, on=["世界", "策略", "sid", "tb", "格"], how="left", validate="1:1")
    ev["t"] = ev["t"].astype(int); ev["ta"] = ev["ta"].astype(int)
    ev["d"] = [W[w]["cal"][t] for w, t in zip(ev["世界"], ev["t"])]
    ev["flag"] = [bool(up[d]) for d in ev["d"]]
    ev["r0"] = ev["S_價"] / ev["ep_a"] - 1 - COSTX
    ev.loc[[sd >= len(W[w]["cal"]) for w, sd in zip(ev["世界"], ev["S_出場日"])], "r0"] = np.nan      # 墊根了結 ＝ 資料尾計值
    # C2：鎖漲停、跳空（自己讀原始）
    RAWC = {}
    lk = []; gp = []
    for w, sid, t, ta in zip(ev["世界"], ev["sid"], ev["t"], ev["ta"]):
        cal = W[w]["cal"]
        if (w, sid) not in RAWC:
            df = pd.read_csv(os.path.join(W[w]["data"], "stocks", f"{sid}.csv"), dtype={"date": str})
            df["date"] = pd.to_datetime(df["date"]); df = df.drop_duplicates("date").set_index("date").reindex(cal)
            RAWC[(w, sid)] = df
        df = RAWC[(w, sid)]
        cl = np.asarray(W[w]["closes"][sid], float); op = np.asarray(W[w]["opens"][sid], float)
        rct, rca = float(df["close"].iloc[t]), float(df["close"].iloc[ta])
        ref = rct * ((cl[t] / rct) / (cl[ta] / rca)) if (np.isfinite(rca) and rca > 0) else rct
        lim = 0.07 if cal[ta] < pd.Timestamp("2015-06-01") else 0.10
        o, h, l = float(df["open"].iloc[ta]), float(df["high"].iloc[ta]), float(df["low"].iloc[ta])
        lk.append(bool(abs(h - l) < 1e-9 and o >= lup(ref, lim) - 1e-6))
        gp.append(op[ta] / cl[t] - 1)
    ev["lock"] = lk; ev["gap"] = gp
    ev["段"] = "段外"
    for sg in ("探索", "確認", "早年"):
        x, y = SEGU[sg]; m = (ev["世界"] == WN[sg]) & (ev["ta"] > x) & (ev["ta"] <= y)
        ev.loc[m, "段"] = sg
    C = {}
    mm = ev.merge(EVm, on=["世界", "策略", "sid", "tb", "t", "ta"], how="outer", suffixes=("", "_m"), indicator=True)
    C["C1 事件 只在一邊"] = int((mm["_merge"] != "both").sum())
    C["C1 r0 最大差"] = float(np.nanmax(np.abs(mm["r0"] - mm["r0_m"])))
    C["C1 旗標 不同"] = int((mm["flag"] != mm["大盤旗標"]).sum())
    C["C1 段 不同"] = int((mm["段"] != mm["段_m"]).sum())
    C["C2 鎖漲停 不同"] = int((mm["lock"] != mm["鎖漲停"]).sum())
    C["C2 跳空 最大差"] = float(np.nanmax(np.abs(mm["gap"] - mm["跳空"])))
    for sg in ("主窗", "早年"):
        s = ev[ev["段"].isin(("探索", "確認"))] if sg == "主窗" else ev[ev["段"] == sg]
        jz = J["成交（t＋1 開盤、鎖漲停、跳空）"][sg]
        C[f"C2 {sg} 鎖漲停筆 自算／json"] = [int(s["lock"].sum()), jz["鎖漲停（買不到）"]]
        C[f"C2 {sg} 跳空中位 自算／json"] = [float(s["gap"].median()), jz["跳空分布（全部）"]["中位"]]
        q = s[~s["lock"] & s["r0"].notna()]
        k = q["flag"].to_numpy(); r = q["r0"].to_numpy()
        amt = q.merge(EVm[["世界", "策略", "sid", "tb", "金額"]], on=["世界", "策略", "sid", "tb"])["金額"].to_numpy()
        d = J["逐筆診斷（唯一事件，⛔ 不單獨判）"][sg]["滑價0"]
        C[f"C1 {sg} ③ 自算／json"] = [float(r[k].mean() - r[~k].mean()), d["③留下減被擋"]]
        C[f"C1 {sg} ① 自算／json"] = [float(-(amt * r)[~k].sum()), d["①濾網減無條件淨損益"]]
    # C1 子帳戶（逐日迴圈）
    pa = pd.read_csv(os.path.join(AOD, "exit5", "paths.csv.gz"), dtype={"sid": str})
    pa = pa[pa["格"] == pa["策略"].map(CELLX)]
    evk = ev.set_index(["世界", "策略", "sid", "tb"])

    def sub(wn, sn, r, sg, flt):
        E = ENG[(wn, sn, r)]; x, y = SEGP[wn][sg]; a = max(x, E["first"]); yy = min(y, E["end"] - 1)
        q = pa[(pa["世界"] == wn) & (pa["策略"] == sn) & (pa["r"] == r)]
        pos = []
        for sid, tb, A in zip(q["sid"], q["tb"], q["金額"]):
            e_ = evk.loc[(wn, sn, sid, tb)]
            if not (a < e_["ta"] <= yy) or e_["lock"] or (flt and not e_["flag"]):
                continue
            pos.append((int(e_["ta"]), float(A), float(e_["ep_a"]), int(e_["S_出場日"]), float(e_["S_價"]), np.asarray(W[wn]["closes"][sid], float)))
        L = y - x + 1; MV = np.zeros(L); adds = {}; outs = {}
        for ta, A, ep, sd, px, cl in pos:
            hi = min(sd, y + 1)
            MV[ta - x:hi - x] += A * cl[ta:hi] / ep
            adds.setdefault(ta, []).append(A)
            if sd <= y:
                outs[sd] = outs.get(sd, 0.0) + A * (px / ep - COSTX)
        cash = 0.0; inj = 0.0; injs = np.zeros(L); csh = np.zeros(L)
        for i, dd in enumerate(range(x, y + 1)):
            for A in adds.get(dd, ()):
                u = min(cash, A); cash -= u; inj += A - u
            cash += outs.get(dd, 0.0)
            injs[i] = inj; csh[i] = cash
        I = injs[-1]
        nav = (I - injs) + csh + MV
        return nav, I
    L_ = lambda sg: SEGP[WN[sg]][sg][1] - SEGP[WN[sg]][sg][0] + 1
    for sg in ("主窗", "探索", "確認", "早年"):
        wn = WN[sg]; L = L_(sg)
        nUy, iUy = sub(wn, "營量", 0, sg, False); nFy, iFy = sub(wn, "營量", 0, sg, True)
        jm = J["主判（加碼子帳戶，濾網版 vs 無條件版）"][f"{sg}·滑價0.0%"]
        C[f"C1 {sg} 營量 子帳戶淨損益 無條件 自算／json"] = [float(nUy[-1] - iUy), jm["營量"]["無條件_淨損益"]]
        C[f"C1 {sg} 營量 子帳戶淨損益 濾網 自算／json"] = [float(nFy[-1] - iFy), jm["營量"]["濾網_淨損益"]]
        C[f"C1 {sg} 營量 濾網年化 自算／json"] = [float((nFy[-1] / iFy) ** (245 / (L - 1)) - 1), jm["營量"]["濾網_年化"]]
        C[f"C1 {sg} 營量 濾網回落 自算／json"] = [float((nFy / np.maximum.accumulate(nFy) - 1).min()), jm["營量"]["濾網_回落"]]
        if sg in ("主窗", "早年"):
            dF = []; dC = []
            for r in range(200):
                nU, iU = sub(wn, "營飆", r, sg, False); nF, iF = sub(wn, "營飆", r, sg, True)
                dF.append((nF[-1] - iF) - (nU[-1] - iU))
                dC.append(((nF + nFy)[-1] - (iF + iFy)) - ((nU + nUy)[-1] - (iU + iUy)))
            C[f"C1 {sg} 營飆 濾網−無條件 中位 自算／json"] = [float(np.median(dF)), jm["營飆"]["濾網減無條件_淨損益（中位）"]]
            C[f"C1 {sg} 營飆 濾網較好顆數比例 自算／json"] = [float(np.mean(np.array(dF) > 0)), jm["營飆"]["濾網淨損益 ＞ 無條件 的顆數比例"]]
            jc = jm["合計（營量＋營飆第 r 顆，200 組）"]
            C[f"C1 {sg} 合計 濾網−無條件 中位 自算／json"] = [float(np.median(dC)), jc["濾網減無條件_淨損益（中位）"]]
            C[f"C1 {sg} 合計 濾網較好組數比例 自算／json"] = [float(np.mean(np.array(dC) > 0)), jc["濾網淨損益 ＞ 無條件 的組數比例"]]
            if sg == "主窗":
                # 頻率：每條路徑觸發（含鎖漲停）
                def cnt(sn, r):
                    E = ENG[("主", sn, r)]; x, y = SEGP["主"]["主窗"]; a = max(x, E["first"]); yy = min(y, E["end"] - 1)
                    q = pa[(pa["世界"] == "主") & (pa["策略"] == sn) & (pa["r"] == r)]
                    n_ = b_ = 0
                    for sid, tb in zip(q["sid"], q["tb"]):
                        e_ = evk.loc[("主", sn, sid, tb)]
                        if a < e_["ta"] <= yy:
                            n_ += 1; b_ += int((not e_["flag"]) and not e_["lock"])
                    return n_, b_
                n0, b0 = cnt("營量", 0); nf = [cnt("營飆", r) for r in range(200)]
                yrs = (SEGP["主"]["主窗"][1] - SEGP["主"]["主窗"][0]) / 245
                rt = (n0 + np.median([z[0] for z in nf])) / yrs; rb = (b0 + np.median([z[1] for z in nf])) / yrs
                jt = J["前瞻門檻（寫死）"]
                kk = "歷史頻率（主窗 2017-03～2026-08，每條路徑：營量＋營飆中位顆，含鎖漲停）"
                C["C3 觸發／年 自算／json"] = [float(rt), jt[kk]["觸發／年"]]
                C["C3 被擋／年 自算／json"] = [float(rb), jt[kk]["被擋／年"]]
                C["C3 年數 自算／json"] = [float(max(jt["觸發門檻"] / rt, jt["被擋門檻"] / rb)), jt[kk]["所需年數（期望值）"]]
    # C3 檢定力（獨立寫法、另一種子）
    jt = J["前瞻門檻（寫死）"]; Ns = jt["S1"]["N*"]
    s = ev[ev["段"].isin(("探索", "確認")) & ~ev["lock"] & ev["r0"].notna()].copy()
    s["clu"] = s["世界"] + "|" + [str(W[w]["cal"][ta])[:7] for w, ta in zip(s["世界"], s["ta"])]
    s = s.sort_values("r0", ascending=False).iloc[int(math.ceil(0.05 * len(s))):]
    r = s["r0"].to_numpy(); k = s["flag"].to_numpy()
    C["C3 去右尾差 自算／json"] = [float(r[k].mean() - r[~k].mean()), jt["S1"]["原始去右尾差"]]
    months = [np.flatnonzero(s["clu"].to_numpy() == c) for c in sorted(s["clu"].unique())]
    rng = np.random.default_rng(777)
    pw = pd.read_csv(os.path.join(OUT, "power.csv")); pw = pw[pw["情境"] == "S1"]
    for N in (Ns - 40, Ns, Ns + 40):
        hit = 0
        for _ in range(2000):
            idx = []; cid = []; j = 0
            while len(idx) < N:
                g = months[rng.integers(len(months))]; idx.extend(g); cid.extend([j] * len(g)); j += 1
            idx = np.array(idx); cid = np.array(cid); rr = r[idx]; kk = k[idx]
            if kk.sum() < 2 or (~kk).sum() < 2:
                continue
            m1, m0 = rr[kk].mean(), rr[~kk].mean()
            psi = np.where(kk, (rr - m1) / kk.sum(), -(rr - m0) / (~kk).sum())
            S = pd.Series(psi).groupby(cid).sum().to_numpy(); G = len(S)
            se = math.sqrt((S ** 2).sum() * G / (G - 1))
            hit += (m1 - m0) / se > 1.645
        C[f"C3 檢定力 N＝{N} 自算／power.csv"] = [hit / 2000, float(pw.loc[pw["N觸發"] == N, "檢定力（單尾5%）"].iloc[0])]
    # 判
    bad = []
    for k_, v in C.items():
        if isinstance(v, list):
            tol = 0.03 if "檢定力" in k_ else (0.02 if ("比例" in k_ or "/年" in k_ or "年數" in k_) else 1e-6)
            if "年數" in k_ or "／年" in k_:
                tol = 0.02 * abs(v[1])
            if v[1] is None or abs(v[0] - v[1]) > tol:
                bad.append(k_)
        elif ("不同" in k_ or "只在一邊" in k_) and v != 0:
            bad.append(k_)
        elif "最大差" in k_ and v > 1e-6:
            bad.append(k_)
    C["不一致項"] = bad; C["結論"] = "全部一致" if not bad else "⛔ 有不一致"
    json.dump(C, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    for k_, v in C.items():
        print(k_, v)


if __name__ == "__main__":
    main()
