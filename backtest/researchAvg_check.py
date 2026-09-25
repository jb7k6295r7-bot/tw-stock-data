# -*- coding: utf-8 -*-
"""PREREG攤平停利 獨立重算（⛔ 不 import researchAvg／avgdown；只 import backtest.data 讀快照、backtest.tradability 讀漲跌停旗標）。
body 跑完後才用：

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchAvg_check.py [--dir backtest/resultsAvg] [--sample 80]

甲 重算（逐項與 A_summary.json 比，差 < 1e-12 ⇒ 相同）：
  C1 每格 n、X̄、中位、X＞0 比例、最差、p10／p90；CR0 SE（自己寫：Σ_g(Σ_{i∈g}(x_i − x̄))² 開根號 ÷ n）、CI、群數、n_eff、出口、結果
  C2 必附句：y ＝ ȳ_i 平均、d ＝ X − ȳ 的同分群 CI、含 0 與否；句子裡的數字（X̄、CI 下緣、y）與重算值同
  C3 假訊號臂：由 A_fake_acc.npz 的逐群 (n, ΣX) 重算 30 次 × 兩版的 E、SE、n_eff、出口、結果 ⇒ x2／30、x3／30、平均 E
  C4 H120 描述：X̄、中位、p10／p90
  C5 抽 --sample 筆保留事件（種子 20260929），從快照重讀股價與 0050，用逐日迴圈【獨立】重找：觸發日 T（自 e 起第一個 ≤0.90·P0／≥1.15·P0）、
     成交日 s（T＋1 起第一個該方向可成交且 0050 開盤有效）、終點 x、終點用的那根 j、R、R0、X、對現金 X ⇒ 逐筆比
乙（B_seeds_arms.csv 存在時）：C6 每格年化中位、回落中位、比值、標籤（條件一嚴格 ＞、條件二 ≥ 0050 未捨入比值）與 B_cells.csv 同
"""
from __future__ import annotations
import os, sys, json
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
SNAP = os.path.expanduser("~/h2data/edc6f8002fed8803795e3486ad57db513f7e9f65/data")
from backtest import data as D
D.DATA = SNAP
from backtest import tradability as TR

W0, W1 = "2017-03-02", "2026-08-24"
C50, M50 = 0.24020209886370614, -0.3395700527611012
CS, CE = 0.00585, 0.00385


def cr0(x, g):
    x = np.asarray(x, float); n = len(x); m = x.mean()
    s = pd.Series(x - m).groupby(np.asarray(g)).sum().to_numpy()
    return float(m), float(np.sqrt((s ** 2).sum()) / n), int(len(s))


def verdict(m, lo, hi, n_eff):
    if n_eff < 30:
        return "出口①", "—（樣本不足以分辨）"
    ex = "出口②" if n_eff < 100 else "出口③"
    if lo <= 0 <= hi:
        return ex, "結果①"
    return ex, ("結果③" if m < 0 else "結果②")


def same(a, b, tol=1e-12):
    if isinstance(a, str) or isinstance(b, str):
        return a == b
    return abs(float(a) - float(b)) <= tol


def main():
    argv = sys.argv
    DIR = argv[argv.index("--dir") + 1] if "--dir" in argv else "backtest/resultsAvg"
    NS = int(argv[argv.index("--sample") + 1]) if "--sample" in argv else 80
    os.chdir(os.path.expanduser("~/tw-p17"))
    cal = D.load_calendar()
    w0 = int(cal.searchsorted(pd.Timestamp(W0)))
    OUTC = {}
    bad = []
    if os.path.exists(os.path.join(DIR, "A_summary.json")):
        S = json.load(open(os.path.join(DIR, "A_summary.json"), encoding="utf-8"))
        K = pd.read_csv(os.path.join(DIR, "A_events_kept.csv.gz"), dtype={"sid": str})
        for kind, nm in (("跌", "攤平"), ("漲", "停利")):
            for H in (20, 60):
                key = "{}_H{}".format(nm, H)
                k = K[(K["kind"] == kind) & (K["H"] == H)]
                x = k["X"].to_numpy(float); T = k["T"].to_numpy(int)
                g = k["T_date"].str[:7].to_numpy() if H == 20 else np.maximum(T - w0, 0) // 60
                m, se, ng = cr0(x, g); ne = min(len(x), ng)
                ex, rs = verdict(m, m - 1.96 * se, m + 1.96 * se, ne)
                J = S["判定4格"][key]
                chk = {"n": len(x) == J["n"], "X̄": same(m, J["X̄"]), "中位": same(np.median(x), J["中位"]), "X＞0比例": same((x > 0).mean(), J["X＞0比例"]),
                       "最差": same(x.min(), J["最差"]), "p10": same(np.percentile(x, 10), J["p10"]), "p90": same(np.percentile(x, 90), J["p90"]),
                       "se": same(se, J["se"]), "群數": ng == J["群數"], "n_eff": ne == J["n_eff"], "出口": ex == J["出口"], "結果": rs == J["結果"]}
                km = k[np.isfinite(k["y_bar"])]
                y = float(km["y_bar"].mean())
                d = (km["X"] - km["y_bar"]).to_numpy(float); Td = km["T"].to_numpy(int)
                gd = km["T_date"].str[:7].to_numpy() if H == 20 else np.maximum(Td - w0, 0) // 60
                md, sed, _ = cr0(d, gd)
                lo, hi = md - 1.96 * sed, md + 1.96 * sed
                P = J["必附句_配對組"]
                chk.update({"y": same(y, P["y"]), "X−y 平均": same(md, P["X−y"]["X̄"]), "X−y CI": same(lo, P["X−y"]["lo"]) and same(hi, P["X−y"]["hi"]),
                            "X−y 含0": bool(lo <= 0 <= hi) == P["X−y的CI含0"],
                            "句子含 y": "{:+.2f}%".format(y * 100) in J["給使用者的句子"],
                            "句子含 X̄": ("{:+.2f}%".format(m * 100) in J["給使用者的句子"]) or ("{:+.2f}%".format(-m * 100) in J["給使用者的句子"])})
                # C3 假訊號
                npz = np.load(os.path.join(DIR, "A_fake_acc.npz"))
                ki = 0 if kind == "跌" else 1; hi_ = 0 if H == 20 else 1
                for vi, vn in enumerate(("新預設_只排除過去20日", "不排除（描述）")):
                    rs_ = []; Es = []
                    for r in range(npz["acc"].shape[0]):
                        a = npz["acc"][r, ki, hi_, vi]
                        nn, sm = a[:, 0], a[:, 1]; N = nn.sum()
                        if N == 0:
                            continue
                        mm = sm.sum() / N; ss = np.sqrt(((sm - nn * mm) ** 2).sum()) / N
                        rs_.append(verdict(mm, mm - 1.96 * ss, mm + 1.96 * ss, int(min(N, (nn > 0).sum())))[1]); Es.append(mm)
                    F = J["假訊號"][vn]
                    chk["假訊號_" + vn] = (rs_.count("結果②") == F["x2／30（結果②＝同樣過關）"] and rs_.count("結果③") == F["x3／30（結果③）"]
                                          and same(np.mean(Es), F["假訊號日平均X"]))
                OUTC[key] = chk
                bad += [key + ":" + c for c, v in chk.items() if not v]
        for kind, nm in (("跌", "攤平"), ("漲", "停利")):
            k = K[(K["kind"] == kind) & (K["H"] == 120)]; x = k["X"].to_numpy(float)
            J = S["必報"]["H120_描述（依構造不可判定）"][nm]
            c4 = same(x.mean(), J["X̄"]) and same(np.median(x), J["中位"]) and same(np.percentile(x, 10), J["p10"]) and same(np.percentile(x, 90), J["p90"])
            OUTC[nm + "_H120"] = c4
            if not c4:
                bad.append(nm + "_H120")
        # C5 逐筆從快照重算
        stocks = pd.read_csv(os.path.join(SNAP, "meta", "stocks.csv"), dtype=str).drop_duplicates("stock_id").set_index("stock_id")["market"]
        s50 = D.load_stock("0050", "twse", cal).df
        o50 = s50["open"].to_numpy(float); c50 = pd.Series(s50["close"].to_numpy(float)).ffill().to_numpy()
        rng = np.random.default_rng(20260929)
        pick = K.iloc[np.sort(rng.choice(len(K), size=min(NS, len(K)), replace=False))]
        n_ok = 0; det = []
        cache = {}
        for _, e in pick.iterrows():
            sid = e["sid"]
            if sid not in cache:
                st = D.load_stock(sid, stocks.get(sid, e["market"]), cal); tb = TR.one(sid, cal)
                cache[sid] = (st.df["open"].to_numpy(float), st.df["close"].to_numpy(float), tb)
            o, c, tb = cache[sid]
            ee, H = int(e["e"]), int(e["H"]); P0 = o[ee]
            T = -1
            for t in range(ee, min(ee + 120, len(cal))):
                if np.isfinite(c[t]) and ((c[t] <= 0.90 * P0) if e["kind"] == "跌" else (c[t] >= 1.15 * P0)):
                    T = t; break
            lim = tb["up_o"] if e["kind"] == "跌" else tb["dn_o"]
            s = -1
            for t in range(T + 1, len(cal)):
                if tb["trd"][t] and not lim[t] and np.isfinite(o[t]) and o[t] > 0 and np.isfinite(o50[t]) and o50[t] > 0:
                    s = t; break
            x = s + H - 1
            j = x
            while not np.isfinite(c[j]):
                j -= 1
            R = c[j] / o[s] - 1; R0 = c50[x] / o50[s] - 1
            X = (R - CS) - (R0 - CE) if e["kind"] == "跌" else (R0 - CE) - R
            XC = R - CS if e["kind"] == "跌" else -R
            ok = (T == e["T"] and s == e["s"] and x == e["x"] and j == e["j_end"] and same(R, e["R"], 1e-12) and same(R0, e["R0"], 1e-12)
                  and same(X, e["X"], 1e-12) and same(XC, e["Xcash"], 1e-12))
            n_ok += int(ok)
            if not ok:
                det.append({"sid": sid, "kind": e["kind"], "H": H, "T": [T, int(e["T"])], "s": [s, int(e["s"])], "X": [X, float(e["X"])]})
        OUTC["C5_逐筆重算"] = {"抽樣": len(pick), "相同": n_ok, "不同明細": det[:10]}
        if n_ok != len(pick):
            bad.append("C5")
    if os.path.exists(os.path.join(DIR, "B_seeds_arms.csv")):
        A = pd.read_csv(os.path.join(DIR, "B_seeds_arms.csv"), float_precision="round_trip")
        TB = pd.read_csv(os.path.join(DIR, "B_cells.csv"), float_precision="round_trip").set_index("arm")
        r50 = C50 / abs(M50)
        for k in ("By", "Ci"):
            g = A[A["arm"] == k]
            c, m = float(g["cagr"].median()), float(g["mdd"].median()); ratio = c / abs(m)
            lab = "合格" if (c > C50 and ratio >= r50) else ("另列" if c > C50 else "不合格")
            ok = same(c, TB.loc[k, "cagr"]) and same(m, TB.loc[k, "mdd"]) and same(ratio, TB.loc[k, "ratio"]) and lab == TB.loc[k, "label"]
            OUTC["C6_" + k] = ok
            if not ok:
                bad.append("C6_" + k)
    OUTC["不同"] = bad
    json.dump(OUTC, open(os.path.join(DIR, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(OUTC, ensure_ascii=False, indent=1, default=str))
    print("✅ 全部相同" if not bad else "⛔ 不同：{}".format(bad))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
