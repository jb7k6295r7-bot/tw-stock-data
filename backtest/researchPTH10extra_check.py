# -*- coding: utf-8 -*-
"""PTH 10 檔版補件四件【獨立對帳】——回測線計算子代理。⛔ 只讀結果夾、不改任何檔（只寫 resultsPTH10extra/check.json、check.log）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTH10extra_check

C1 X1 滑價版：p1_slip.csv N＝10 各列 ＝ resultsPTHn/PTHn_main.csv（共同欄逐字）；年化／回落由 resultsPTHn eq_<世界>.npz N10[s]_eq 以自寫式（窗 [x, y]、年 ＝ 點數÷245）重算。
C2 X2 逐年：npz N10_eq、N10s_eq、Bc ＋ cal_<世界>.txt 自算年末÷前年末 ⇒ 對 p2_year.csv；並對 resultsPTHpf/by_year.csv S10。
C3 X1 漲停鎖死：只用 resultsPTHn trades_<世界>_N10（sid、PTH、買進日、賣出日）與 resultsPTH/freq events（入選、跳月_st、跳月_進場日）自算被擠掉筆數 ⇒ 對 J。
C4 X3：只用 resultsPTH10vsYL daily 檔，自寫月底、12 個月窗、各半③（窗首 ½／½、遇新年度首日收盤調回、扣搬動 0.585%）、比值 ⇒ 對 p3_roll.csv 旗標與 J 通過率。
C5 X4：0050 原始收盤 ＋ adj 因子（pre_close／ref_price）手算 36 個月含息報酬（不經 load_stock）⇒ 對 p4_gate.csv；2014 月底原始收盤對 origin/main data/extra/0050_2012_2014.csv。
C6 抽樣手算：p2_dd_hold 抽 8 列，市值 ＝ 讀 stocks csv 原始收盤×股數、產業 ＝ industry_pit 直讀 ⇒ 對檔。
C7 策略鎖 25 支相符；git 工作樹：本件只新增檔。
"""
from __future__ import annotations

import gzip
import io
import json
import os
import subprocess
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchAddOn as RA                    # noqa: E402

OUT = "backtest/resultsPTH10extra"
PNO = "backtest/resultsPTHn"
COST = 0.00585
H2D = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
EOTC = os.path.expanduser("~/earlydata/eotc_f65bb03e11/otc/data")
EARLY_TW = os.path.expanduser("~/earlydata/950ad26e12/main/data/stocks")
DATA = {"主": H2D, "早年": EOTC}


def rd(p, **k):
    return pd.read_csv(p, float_precision="round_trip", keep_default_na=False, na_values=[""], encoding="utf-8-sig", **k)


def main():
    T0 = time.time()
    log = RA.log_to(os.path.join(OUT, "check.log"))
    J = json.load(open(os.path.join(OUT, "PTH10extra.json"), encoding="utf-8"))
    C = {}; ok = True
    # C1
    P1 = rd(os.path.join(OUT, "p1_slip.csv"), dtype=str); PN = rd(os.path.join(PNO, "PTHn_main.csv"), dtype=str)
    bad = 0; nchk = 0; worst = 0.0
    for _, r in P1.iterrows():
        ref = PN[(PN["世界"] == r["世界"]) & (PN["N"] == "10") & (PN["滑價"] == r["滑價"]) & (PN["段"] == r["段"])].iloc[0]
        for k in P1.columns:
            if k in PN.columns and k not in ("N",):
                nchk += 1; bad += int(str(r[k]) != str(ref[k]))
        wn = r["世界"]; x, y = J["段"][wn][r["段"]][:2]
        e = np.load(os.path.join(PNO, f"eq_{wn}.npz"))["N10s_eq" if r["滑價"] == "True" else "N10_eq"][x:y + 1]
        cagr = (e[-1] / e[0]) ** (245.0 / len(e)) - 1; mdd = float((e / np.maximum.accumulate(e) - 1).min())
        worst = max(worst, abs(cagr - float(r["年化"])) / abs(cagr), abs(mdd - float(r["回落"])) / abs(mdd))
    C["C1"] = {"列": len(P1), "比對格": nchk, "不同": bad, "自算年化回落最大相對差(對%.6g)": worst}
    ok &= bad == 0 and worst < 5e-6; log(f"[C1] {C['C1']}")
    # C2
    PY = rd(os.path.join(OUT, "p2_year.csv")); BY = rd(os.path.join("backtest/resultsPTHpf", "by_year.csv"))
    w2 = 0.0; nb = 0
    for wn in ("主", "早年"):
        cal = open(os.path.join(OUT, f"cal_{wn}.txt")).read().split()
        Z = np.load(os.path.join(PNO, f"eq_{wn}.npz"))
        for sg, (x, y, *_) in J["段"][wn].items():
            yrs = sorted({d[:4] for d in cal[x:y + 1]})
            base = x
            for Y_ in yrs:
                e = max(i for i in range(x, y + 1) if cal[i][:4] == Y_)
                v = {"10格版": Z["N10_eq"][e] / Z["N10_eq"][base] - 1, "10格版滑價": Z["N10s_eq"][e] / Z["N10s_eq"][base] - 1, "0050": Z["Bc"][e] / Z["Bc"][base] - 1}
                r = PY[(PY["世界"] == wn) & (PY["段"] == sg) & (PY["年"] == int(Y_))].iloc[0]
                for k, val in v.items():
                    w2 = max(w2, abs(val - r[k]) / max(abs(val), 1e-9))
                b = BY[(BY["世界"] == wn) & (BY["臂"] == "S10") & (BY["段"] == sg) & (BY["年"] == int(Y_))].iloc[0]
                nb += int(abs(b["本件"] - v["10格版"]) > 5e-6 * max(abs(v["10格版"]), 1e-3) or abs(b["0050"] - v["0050"]) > 5e-6 * max(abs(v["0050"]), 1e-3))
                base = e
    C["C2"] = {"自算對 p2_year 最大相對差": w2, "對 resultsPTHpf by_year S10 超差年數": nb}
    ok &= w2 < 5e-6 and nb == 0; log(f"[C2] {C['C2']}")
    # C3
    res3 = {}
    for wn in ("主", "早年"):
        T = pd.read_csv(os.path.join(PNO, f"trades_{wn}_N10.csv.gz"), dtype={"sid": str, "買進日": str, "賣出日": str}, keep_default_na=False)
        F = pd.read_csv(f"backtest/resultsPTH/freq/events_{wn}.csv.gz", dtype={"sid": str, "跳月_進場日": str})
        F = F[F["入選"] & (F["跳月_st"] == "e開盤鎖漲停")]
        for sg, (x, y, dx, dy) in J["段"][wn].items():
            n_ahead = 0; n_tie = 0
            Tb = T[(T["買進日"] >= dx) & (T["買進日"] <= dy)]
            for e, g in F[(F["跳月_進場日"] >= dx) & (F["跳月_進場日"] <= dy)].groupby("跳月_進場日"):
                held = set(T.loc[(T["買進日"] < e) & ((T["賣出日"] == "") | (T["賣出日"] > e)), "sid"])
                sold = set(T.loc[T["賣出日"] == e, "sid"])
                bt = T[T["買進日"] == e]
                if 10 - len(held) <= 0:
                    continue
                L = g[~g["sid"].isin(held | sold)]
                if len(bt) == 0:
                    continue
                mn = bt["PTH"].min()
                n_ahead += min(int((L["PTH"] > mn).sum()), len(bt)); n_tie += int((L["PTH"] == mn).sum())
            ref = J["X1"][f"{wn}|漲停鎖死"][sg]
            res3[f"{wn}|{sg}"] = {"自算被擠掉": n_ahead, "檔": ref["被擠掉(遞補)筆"], "自算同分": n_tie, "檔同分": ref["同分可能筆"], "買進筆": int(len(Tb)), "檔買進筆": ref["10格版買進筆"]}
            ok &= n_ahead == ref["被擠掉(遞補)筆"] and n_tie == ref["同分可能筆"] and len(Tb) == ref["10格版買進筆"]
    C["C3"] = res3; log(f"[C3] {res3}")
    # C4
    R3 = rd(os.path.join(OUT, "p3_roll.csv"), dtype={"窗首": str, "窗尾": str})
    res4 = {}
    for wn in ("主", "早年"):
        DL = pd.read_csv(f"backtest/resultsPTH10vsYL/daily_{wn}.csv.gz", float_precision="round_trip", dtype={"日": str})
        d = DL["日"].tolist(); P = DL["10檔版淨值"].to_numpy(float); Y = DL["營量淨值"].to_numpy(float)
        ends = [k for k in range(len(d)) if k == len(d) - 1 or d[k + 1][:7] != d[k][:7]]
        pts = [0] + [k for k in ends if k != 0]
        R = R3[R3["世界"] == wn].reset_index(drop=True)
        badA = badB = 0; nA = nB = nAB = 0
        for w in range(len(pts) - 12):
            a_, z = pts[w], pts[w + 12]
            p, q = P[a_:z + 1], Y[a_:z + 1]
            A = (p[-1] / p[0]) - (q[-1] / q[0]) > 0
            # 各半③
            va, vb = 0.5, 0.5; V = [1.0]
            for k in range(1, len(p)):
                va *= p[k] / p[k - 1]; vb *= q[k] / q[k - 1]
                if d[a_ + k][:4] != d[a_ + k - 1][:4]:
                    tot = va + vb; tot -= abs(va - tot / 2) * COST; va = vb = tot / 2
                V.append(va + vb)
            V = np.array(V)

            def rat(e):
                m = (e / np.maximum.accumulate(e) - 1).min()
                return (e[-1] / e[0] - 1) / abs(m) if m < 0 else np.nan
            B = bool(np.isfinite(rat(V)) and np.isfinite(rat(q)) and rat(V) > rat(q))
            r = R.iloc[w]
            badA += int(bool(r["A_差>0"]) != bool(A) or r["窗尾"] != d[z]); badB += int(bool(r["B_各半③>營量"]) != B)
            nA += A; nB += B; nAB += (A or B)
        n = len(pts) - 12
        ref = J["X3"][wn]["全部窗"]
        res4[wn] = {"窗數": n, "檔窗數": len(R), "A不同": badA, "B不同": badB, "自算A率": nA / n, "自算B率": nB / n, "自算A或B率": nAB / n,
                    "檔A率": ref["A通過率"], "檔B率": ref["B通過率(各半③)"], "檔A或B率": ref["A或B通過率"]}
        ok &= badA == 0 and badB == 0 and n == len(R) and abs(nAB / n - ref["A或B通過率"]) < 1e-12
    C["C4"] = res4; log(f"[C4] {res4}")
    # C5
    G = rd(os.path.join(OUT, "p4_gate.csv"), dtype={"回看起(月底)": str, "回看迄(月底)": str})

    def raw(wn):
        s = pd.read_csv(os.path.join(DATA[wn], "stocks", "0050.csv"), dtype={"date": str}).set_index("date")["close"].astype(float)
        a = pd.read_csv(os.path.join(DATA[wn], "adj", "0050.csv"), dtype={"date": str})
        return s, a
    sE, aE = raw("早年"); sM, aM = raw("主")
    allc = pd.concat([sE, sM]); alla = pd.concat([aE, aM])

    def tret(a_, b_):
        f = alla[(alla["date"] > a_) & (alla["date"] <= b_)]
        return allc[b_] / allc[a_] * float(np.prod(f["pre_close"].astype(float) / f["ref_price"].astype(float))) - 1
    w5 = 0.0; s5 = 0
    for _, r in G.iterrows():
        v = tret(r["回看起(月底)"], r["回看迄(月底)"])
        w5 = max(w5, abs(v - r["36個月含息報酬"])); s5 += int((v < 0) != bool(r["<0(閘關)"]))
    ex = pd.read_csv(io.StringIO(subprocess.run(["git", "show", "origin/main:data/extra/0050_2012_2014.csv"], capture_output=True, text=True).stdout), dtype={"date": str}).set_index("date")["close"].astype(float)
    starts = sorted(set(G["回看起(月底)"]))
    xb = {d: (float(sE[d]), float(ex[d]) if d in ex.index else None) for d in starts}
    nx = sum(1 for d, (u, v) in xb.items() if v is None or abs(u - v) > 1e-9)
    C["C5"] = {"手算對 p4 最大絕對差": w5, "<0 判定不同": s5, "回看起月底原始收盤 早年 vs data/extra 不符": nx, "對照": xb,
               "註": "手算 ＝ 原始收盤比 × Π(pre_close÷ref_price)；不經 load_stock；容差 1e-6（load_stock 還原價有捨入，差在 1e-7 級，不影響正負）"}
    ok &= w5 < 1e-6 and s5 == 0 and nx == 0; log(f"[C5] {C['C5']}")
    # C6
    txt = subprocess.run(["git", "show", "origin/main:curated/industry_hist/industry_pit.csv"], capture_output=True, text=True).stdout
    IP = pd.read_csv(io.StringIO(txt), dtype=str, keep_default_na=False)
    H = rd(os.path.join(OUT, "p2_dd_hold.csv"), dtype={"sid": str, "形成月底": str})
    smp = H.sample(n=min(8, len(H)), random_state=20261021)
    res6 = []
    for _, r in smp.iterrows():
        wn = r["世界"]; s = r["sid"]; t = r["形成月底"]
        df = pd.read_csv(os.path.join(DATA[wn], "stocks", f"{s}.csv"), dtype={"date": str})
        row = df[df["date"] <= t].iloc[-1]
        sh = pd.to_numeric(df.loc[df["date"] <= t, "shares"], errors="coerce").dropna()
        if len(sh) == 0 and wn == "早年":
            d2 = pd.read_csv(os.path.join(EARLY_TW, f"{s}.csv"), dtype={"date": str})
            sh = pd.to_numeric(d2.loc[d2["date"] <= t, "shares"], errors="coerce").dropna()
        cap = float(row["close"]) * float(sh.iloc[-1]) / 1e8 if len(sh) else np.nan
        g = IP[IP["stock_id"] == s]
        ind = next((i for i, a_, b_ in zip(g["industry"], g["start"], g["end"]) if (a_ or "0") <= t <= (b_ or "9")), None)
        res6.append({"世界": wn, "sid": s, "形成月底": t, "手算市值(億)": cap, "檔市值(億)": r["市值(億)"], "手算產業": ind, "檔產業": r["產業"],
                     "符": bool((abs(cap - r["市值(億)"]) <= 1e-5 * cap if np.isfinite(cap) else not np.isfinite(r["市值(億)"])) and (ind or "未分類") == r["產業"])})
    C["C6"] = res6; ok &= all(z["符"] for z in res6); log(f"[C6] {res6}")
    # C7
    p = subprocess.run([sys.executable, "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True)
    gs = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines()
    C["C7"] = {"strategy_lock": p.stdout.strip().splitlines()[-1] if p.stdout.strip() else p.stderr.strip()[-200:], "rc": p.returncode,
               "既有追蹤檔有改動(工作樹，非本件)": [l for l in gs if not l.startswith("??")],
               "本件新增": [l for l in gs if l.startswith("??") and "PTH10extra" in l]}
    ok &= p.returncode == 0; log(f"[C7] {C['C7']}")
    C["全部通過"] = bool(ok); C["耗時秒"] = round(time.time() - T0)
    json.dump(C, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] 全部通過 {ok}｜{C['耗時秒']}s")


if __name__ == "__main__":
    main()
