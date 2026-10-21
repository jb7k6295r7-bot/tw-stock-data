# -*- coding: utf-8 -*-
"""出場第四輪 seq1 正式跑——獨立對帳（回測線計算子代理；⛔ 不 commit、不改既有檔）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchExit4_check [--n 120]

D1 抽樣逐股重算 R（主 n 檔、早年 n/2 檔，default_rng(20261022)，與頻率表對帳抽樣不同種子）：
   事件與觸發用頻率表對帳檔 researchExit4_freq_check 的逐日迴圈版（stock、recompute；⛔ 不經 researchExit4_freq.work），
   R 用本檔逐筆迴圈另寫（基準＝T 以前最後有效收盤、E＝T＋h 或壞根前一根、結算＝E 以前最後有效收盤、賣價＝o[s]、減 0.4425%），
   與 events_R.csv.gz 的 R_{出法}_{h} 逐筆比（容差 1e−6；檔內 7 位小數）。
D2 由 events_R.csv.gz 另寫彙總：ranks.csv 的 n、平均R、名次逐列比；verdict.csv 的第一、第二、d 與 98.33% CI（本檔另寫月分群 CR0）。
D3 構造：S+ R_K2 ＝ ½(R_K1＋R_K0)；R_K2 在兩者之間；E 不在資料內 ⇒ R 全空；results.json 的頻率表逐列對帳全過。
D4 不前視：抽樣事件的每個觸發，把 d 之後的收盤全刪掉重判 ⇒ 判斷日不變；賣出日 s ≥ d＋1；基準根 ≤ T；
   月營收可用日（seq6 avail_map）一律 ≥ 期別次月 10 日（≥2026-01 期 ≥ 次月 15 日）。
D5 策略鎖 --check 相符（25 支）。
D6 抽筆手算 3 筆（主確認段 S+／S0_40／S−各 1，T＋120）：列出日期、還原價與各出法 R（給交件書）。
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import subprocess
import sys
from statistics import NormalDist

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchExit4_freq_check as FC                       # noqa: E402  逐日迴圈版 stock、recompute（⛔ 只 import）
G6, D, TRD = FC.G6, FC.D, FC.TRD

OUT = os.path.expanduser("~/tw-p17/backtest/resultsExit4/main")
EXR_PKL = FC.EXR_PKL
COST1 = 0.004425
HS = (60, 120, 250)
EX = {"S+": ["K0", "K1", "K2", "K3", "K4", "K5"], "S0": ["K0", "K1", "K2", "K3"], "S−": ["K0", "K1", "K2", "K3", "K4"]}
ZB = NormalDist().inv_cdf(1 - 0.05 / 3 / 2)
RES: dict = {}


def log(s):
    print(s, flush=True)


def grp(s):
    return "S0" if s.startswith("S0") else s


def last_valid_le(v, i):
    while i >= 0 and not v[i]:
        i -= 1
    return i


def r_hand(S, r, last):
    """本檔另寫的 R（逐筆）。回 {f'R_{code}_{h}': 值}；h 不收 ⇒ 不給。"""
    o, c, v = S["o"], S["c"], S["valid"]
    T = r["T"]; kb = r["kb"] if r["kb"] >= 0 else 10 ** 9
    PT = c[last_valid_le(v, T)]
    out = {}
    for h in HS:
        if T + h > last:
            continue
        E = kb - 1 if kb <= T + h else T + h
        PE = c[last_valid_le(v, E)]
        vals = {}
        for code in EX[grp(r["狀態"])]:
            px = PE
            if code != "K0" and not (grp(r["狀態"]) == "S+" and code == "K2"):
                d, s = r[f"{code}_d"], r[f"{code}_s"]
                if d >= 0 and d <= E - 1 and s >= 0 and s <= E:
                    px = o[s]
            vals[code] = px / PT - 1 - COST1
        if grp(r["狀態"]) == "S+":
            vals["K2"] = 0.5 * vals["K1"] + 0.5 * vals["K0"]
        for k, x in vals.items():
            out[f"R_{k}_{h}"] = x
    return out


def cr0_own(x, g):
    x = np.asarray(x, float); n = len(x); m = x.mean()
    sums = {}
    for xi, gi in zip(x - m, g):
        sums[gi] = sums.get(gi, 0.0) + xi
    se = float(np.sqrt(sum(s * s for s in sums.values())) / n)
    return m, se


def trig_trunc(S, r, code, d, P0, kmax):
    """D4：把 d 之後收盤刪掉重判（只 S+ K3/K4/K5、S0 K2/K3、S− K2/K3；K1＝T、K4(S−) 用可用日另查）。"""
    c = S["c"].copy(); c[d + 1:] = np.nan
    v = np.isfinite(c); ma = S["ma"]; T = r["T"]
    ks = [k for k in range(T, min(kmax, d) + 1) if v[k]]
    st = grp(r["狀態"])
    if st == "S+":
        mx = -np.inf
        for k in ks:
            mx = max(mx, c[k])
            if (code == "K3" and c[k] <= 0.9 * mx) or (code == "K4" and c[k] <= 0.8 * mx) or (code == "K5" and c[k] < ma[k]):
                return k
        return -1
    if st == "S0":
        vals = [c[t] for t in range(r["e"], T + 1) if v[t]]
        lo, up = min(vals), max(vals); brk = False
        for k in ks:
            if code == "K2" and c[k] < lo:
                return k
            if code == "K3":
                if not brk:
                    if c[k] < lo:
                        return k
                    if c[k] > up:
                        brk = True
                elif c[k] < up:
                    return k
        return -1
    for k in ks:
        if code == "K2" and (c[k] / P0 - 1 >= -0.05 or c[k] >= ma[k]):
            return k
        if code == "K3" and c[k] / P0 - 1 <= -0.25:
            return k
    return -1


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=120)
    a = ap.parse_args()
    EV = pd.read_csv(os.path.join(OUT, "events_R.csv.gz"), dtype={"sid": str})
    RK = pd.read_csv(os.path.join(OUT, "ranks.csv"))
    V = pd.read_csv(os.path.join(OUT, "verdict.csv"))
    J = json.load(open(os.path.join(OUT, "results.json"), encoding="utf-8"))
    tab = pickle.load(open(EXR_PKL, "rb"))["tab"]
    rng = np.random.default_rng(20261022)
    d1 = {}; d4 = {"重判": 0, "不同": 0, "s<d+1": 0, "基準根>T": 0}; hand = []
    for world, wn, nn in (("main", "主", a.n), ("early", "早年", a.n // 2)):
        Wd = G6.setup(world, log)
        cal = Wd["cal"]; p = Wd["p"]; last = len(cal) - 1
        off = TRD.load_official()
        sids = sorted(p["stock_id"].unique())
        pick = sorted(rng.choice(sids, size=min(nn, len(sids)), replace=False))
        if world == "main":                                      # D4 月營收可用日
            bad = 0
            for per, pos in Wd["A"].items():
                y, m = int(per[:4]), int(per[5:7])
                ny, nm = (y + (m == 12), m % 12 + 1)
                lim = pd.Timestamp(ny, nm, 15 if per >= "2026-01" else 10)
                bad += int(cal[pos] < lim)
            d4["可用日早於次月10／15日"] = bad; d4["可用日期別數"] = len(Wd["A"])
        nrow = 0; nbad = 0; maxd = 0.0
        for sid in pick:
            es = sorted(p.loc[p["stock_id"] == sid, "e"].astype(int))
            mk = Wd["mk"].get(sid, "twse")
            turns, nrev = G6.rev_turns(sid, Wd["rev"], Wd["rly"], Wd["A"])
            rows = FC.recompute(sid, mk, es, cal, off, tab, list(turns), nrev)
            if not rows:
                continue
            S = FC.stock(sid, mk, cal, off, tab)
            mine = EV[(EV["世界"] == wn) & (EV["sid"] == sid)].set_index(["e", "狀態"])
            for r in rows:
                hv = r_hand(S, r, last)
                pr = mine.loc[(r["e"], r["狀態"])]
                for k, x in hv.items():
                    nrow += 1
                    dd = abs(x - float(pr[k]))
                    maxd = max(maxd, dd)
                    nbad += int(not (dd < 1e-6))
                # 該有空的要空
                for h in HS:
                    if r["T"] + h > last:
                        nbad += int(np.isfinite(float(pr[f"R_K0_{h}"])))
                if int(pr["T基準根"]) > r["T"]:
                    d4["基準根>T"] += 1
                # D4 截斷重判
                kb = r["kb"] if r["kb"] >= 0 else 10 ** 9
                kmax = min(r["T"] + 250, kb - 1, last) - 1
                P0 = S["o"][r["e"]]
                for code in EX[grp(r["狀態"])]:
                    if code in ("K0", "K1") or (grp(r["狀態"]) == "S+" and code == "K2") or (grp(r["狀態"]) == "S−" and code == "K4"):
                        continue
                    d = r.get(f"{code}_d", -1)
                    if d is None or d < 0:
                        continue
                    d4["重判"] += 1
                    d4["不同"] += int(trig_trunc(S, r, code, d, P0, kmax) != d)
                    s = r[f"{code}_s"]
                    d4["s<d+1"] += int(s >= 0 and s < d + 1)
                # D6 手算
                if world == "main" and len(hand) < 3 and r["T"] >= int(cal.searchsorted(pd.Timestamp("2022-01-03"))) and r["T"] + 120 <= last:
                    want = ["S+", "S0_40", "S−"][len(hand)]
                    if r["狀態"] == want:
                        T = r["T"]; kb_ = r["kb"] if r["kb"] >= 0 else 10 ** 9
                        E = kb_ - 1 if kb_ <= T + 120 else T + 120
                        jT = last_valid_le(S["valid"], T); jE = last_valid_le(S["valid"], E)
                        h_ = {"sid": sid, "狀態": want, "e": str(cal[r["e"]].date()), "P0(o[e])": float(S["o"][r["e"]]), "T": str(cal[T].date()),
                              "c[T]": float(S["c"][jT]), "E": str(cal[E].date()), "c[E]": float(S["c"][jE]), "出法": {}}
                        for code in EX[grp(want)]:
                            if code == "K0" or (want == "S+" and code == "K2"):
                                continue
                            d, s = r[f"{code}_d"], r[f"{code}_s"]
                            if d >= 0 and d <= E - 1 and 0 <= s <= E:
                                h_["出法"][code] = {"判斷日": str(cal[d].date()), "賣出日": str(cal[s].date()), "o[s]": float(S["o"][s]),
                                                  "手算R": float(S["o"][s] / S["c"][jT] - 1 - COST1), "程式R": float(pr[f"R_{code}_120"])}
                            else:
                                h_["出法"][code] = {"E前沒觸發⇒E收盤": True, "手算R": float(S["c"][jE] / S["c"][jT] - 1 - COST1), "程式R": float(pr[f"R_{code}_120"])}
                        h_["出法"]["K0"] = {"手算R": float(S["c"][jE] / S["c"][jT] - 1 - COST1), "程式R": float(pr["R_K0_120"])}
                        if want == "S+":
                            h_["出法"]["K2"] = {"手算R": 0.5 * (h_["出法"]["K1"]["手算R"] + h_["出法"]["K0"]["手算R"]), "程式R": float(pr["R_K2_120"])}
                        hand.append(h_)
        d1[wn] = {"抽樣股": len(pick), "比對R值": nrow, "不符": nbad, "最大差": maxd, "過": nbad == 0 and nrow > 0}
        log(f"[D1 {wn}] {d1[wn]}")
    RES["D1"] = d1
    d4["過"] = d4["不同"] == 0 and d4["s<d+1"] == 0 and d4["基準根>T"] == 0 and d4.get("可用日早於次月10／15日", 1) == 0
    RES["D4"] = d4; log(f"[D4] {d4}")
    RES["D6_手算"] = hand
    # D2
    bad = 0; n2 = 0
    for (wn, sg, st, end), t in RK.groupby(["世界", "段", "狀態", "終點"]):
        h = int(end.split("+")[1])
        sub = EV[(EV["世界"] == wn) & (EV["段"] == sg) & (EV["狀態"] == st) & EV[f"R_K0_{h}"].notna()]
        means = {c: sub[f"R_{c}_{h}"].mean() for c in EX[grp(st)]}
        order = sorted(means, key=lambda c: (-means[c], EX[grp(st)].index(c)))
        for _, r in t.iterrows():
            n2 += 1
            ok = int(r["n"]) == len(sub) and abs(r["平均R"] - means[r["出法"]]) < 1e-6 and int(r["名次"]) == order.index(r["出法"]) + 1
            bad += int(not ok)
    vbad = 0
    for _, v in V.iterrows():
        for sg in ("探索", "確認"):
            sub = EV[(EV["世界"] == "主") & (EV["段"] == sg) & (EV["狀態"] == v["事件"]) & EV["R_K0_120"].notna()]
            first = v[f"{sg}第一"]
            dd = sub[f"R_{first}_120"].to_numpy() - sub[f"R_{v[sg + '_第二']}_120"].to_numpy()
            m, se = cr0_own(dd, sub["T日"].str[:7].to_numpy())
            vbad += int(abs(m - v[f"{sg}_d(第一−第二)"]) > 1e-6 or abs(m - ZB * se - v[f"{sg}_lo98.33"]) > 1e-6)
    RES["D2"] = {"ranks列": n2, "ranks不同": bad, "verdict不同": vbad, "過": bad == 0 and vbad == 0}
    log(f"[D2] {RES['D2']}")
    # D3
    sp = EV[EV["狀態"] == "S+"]
    k2 = True; btw = True
    for h in HS:
        m = sp[f"R_K0_{h}"].notna()
        x = sp.loc[m]
        k2 &= bool((abs(x[f"R_K2_{h}"] - 0.5 * (x[f"R_K1_{h}"] + x[f"R_K0_{h}"])) < 2e-7).all())
        lo = np.minimum(x[f"R_K1_{h}"], x[f"R_K0_{h}"]) - 2e-7; hi = np.maximum(x[f"R_K1_{h}"], x[f"R_K0_{h}"]) + 2e-7
        btw &= bool(((x[f"R_K2_{h}"] >= lo) & (x[f"R_K2_{h}"] <= hi)).all())
    rec = J["對帳_頻率表events逐列"]
    RES["D3"] = {"S+ K2＝½K1＋½K0": k2, "K2 在兩者之間": btw, "頻率表events逐列相同": {k: v["逐列相同"] for k, v in rec.items()},
                 "過": k2 and btw and all(v["逐列相同"] for v in rec.values())}
    log(f"[D3] {RES['D3']}")
    p_ = subprocess.run(["python3", "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True, cwd=os.path.expanduser("~/tw-p17"))
    tail = (p_.stdout + p_.stderr).strip().splitlines()[-1:]
    RES["D5"] = {"輸出": tail, "過": bool(tail and "相符（25 支）" in tail[0])}
    log(f"[D5] {RES['D5']}")
    RES["全過"] = all(v["過"] for v in d1.values()) and all(RES[k]["過"] for k in ("D2", "D3", "D4", "D5"))
    json.dump(RES, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[全過] {RES['全過']}")


if __name__ == "__main__":
    main()
