# -*- coding: utf-8 -*-
"""52 週新高 10 檔版加停損描述【獨立對帳】——回測線計算子代理。⛔ 只讀結果夾、不改任何檔（只寫 resultsPTH10stop/check.json、check.log）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTH10stop_check

C1 無停損：本件 eq npz（base、bases）五陣列 ＝ resultsPTHn N10、N10s 逐位元；交易檔全文 ＝ resultsPTHn trades_<世界>_N10[s] 逐字。
C2 每個停損組合：只用交易檔（買進日、金額、市值基準價、R用、賣出日）＋ 0050 開收盤 ＋ 快取收盤，researchPTHn_check.rebuild 重建 10 槽淨值 ⇒ 對 eq npz。
C3 全數重掃（收盤讀法、盤中讀法；主版與滑價版）：每列由快取收盤／開盤／load_bars 低價自算 是否停損、觸發日、賣出日、R用（含同根取較低）⇒ 對交易檔。
C4 手算 10 筆（收盤讀法、主版）：D.load_stock 原始還原日線（⛔ 不經快取）逐日列收盤 ÷ 買價 − 1，找第一個 ≤ 門檻日、隔天開盤 ⇒ 對 觸發日、賣出日、R用。
C5 段指標：自寫年化、回落、0050 同窗、標籤字面另寫 ⇒ 對 stop_main.csv 每一列。
C6 少賠／少賺拆解：由交易檔自算 ⇒ 對 decomp.csv。
C7 策略鎖 25 支相符；git 工作樹：本件只新增檔。
"""
from __future__ import annotations

import gzip
import json
import os
import subprocess
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchPTHpf as M                     # noqa: E402
from backtest import researchPTHpf_check as PC              # noqa: E402  rd、seg_metrics、lab
from backtest import researchPTHn_check as PNC              # noqa: E402  rebuild
from backtest import research11 as R11                      # noqa: E402
from backtest import researchAddOn as RA                    # noqa: E402
from backtest import data as D                              # noqa: E402

OUT = "backtest/resultsPTH10stop"
SRC = "backtest/resultsPTHn"
COST = 0.00585; SLIP = 0.005
VAR = ["base"] + [f"{m}{t}" for m in ("close", "intra") for t in (15, 20, 25, 30)]


def rdx(path):
    df = PC.rd(path)
    for c in ("觸發日", "原排程賣出日"):
        df[c] = df[c].fillna("").astype(str).replace("nan", "")
    df["sid"] = df["sid"].astype(str)
    return df


def rescan(W, df, mode, th, slip, LOWF):
    """回傳不符筆數與例。"""
    dpos = {d: i for i, d in enumerate(W["dates"])}; n0 = W["n0"]; C = W["C"]; O = W["O"]; ix = W["ix"]
    bad = 0; ex = []; nstop = 0
    PX = df["原排程賣價(未滑價)"].to_numpy(float)
    for r_, z in enumerate(df.itertuples(index=False)):
        j = ix[z.sid]; e = dpos[z.買進日]; s = dpos[z.原排程賣出日] if z.原排程賣出日 else -1
        P = float(O[j, e]); ep = P * (1 + SLIP) if slip else P
        last = s if s >= 0 else n0 - 1
        want = None
        if mode == "close":
            for d in range(e, (s if s >= 0 else n0)):
                if np.isfinite(C[j, d]) and C[j, d] / ep - 1.0 <= th + 1e-12:
                    for f in range(d + 1, last + 1):
                        if np.isfinite(O[j, f]) and O[j, f] > 0:
                            sp = O[j, f]
                            if f == s:
                                sp = min(sp, float(PX[r_]))
                            want = (d, f, sp)
                            break
                    break
        else:
            low = LOWF(z.sid)
            K = ep * (1 + th)
            for d in range(e, last + 1):
                if np.isfinite(low[d]) and low[d] <= K:
                    op = O[j, d]
                    sp = op if (np.isfinite(op) and op > 0 and op <= K) else K
                    if d == s:
                        sp = min(sp, float(PX[r_]))
                    want = (d, d, sp)
                    break
        got_stop = bool(z.停損)
        if want is None:
            ok = (not got_stop) and z.觸發日 == "" and z.賣出日 == z.原排程賣出日
        else:
            nstop += 1
            d, f, sp = want
            g = sp * (1 - SLIP) / ep - 1.0 if slip else sp / P - 1.0
            sell_ok = (z.賣出日 == W["dates"][f]) or (f >= n0)
            ok = got_stop and z.觸發日 == W["dates"][d] and sell_ok and abs(float(z.R用) - g) <= 1e-12 * max(1.0, abs(g))
        if not ok:
            bad += 1
            if len(ex) < 3:
                ex.append((z.sid, z.買進日, z.觸發日, z.賣出日, want))
    return bad, ex, nstop


def main():
    log = RA.log_to(os.path.join(OUT, "check.log"))
    T0 = time.time(); J = {"時間": M.now_tpe()}; ok = True
    TB = pd.read_csv(os.path.join(OUT, "stop_main.csv"), encoding="utf-8-sig")
    DC = pd.read_csv(os.path.join(OUT, "decomp.csv"), encoding="utf-8-sig")
    hand = []
    for wn in ("主", "早年"):
        W = M.build_world(wn, log)
        Z = np.load(os.path.join(OUT, f"eq_{wn}.npz")); Z0 = np.load(os.path.join(SRC, f"eq_{wn}.npz"))
        Bc, Bo = Z0["Bc"], Z0["Bo"]
        ok &= bool(np.array_equal(Z["Bc"], Bc) and np.array_equal(Z["Bo"], Bo))
        # C1
        c1 = {}
        for sx in ("", "s"):
            for k in ("eq", "hv", "u", "pend", "nh"):
                c1[f"{sx}{k}"] = bool(np.array_equal(Z[f"base{sx}_{k}"], Z0[f"N10{sx}_{k}"]))
            with gzip.open(os.path.join(OUT, f"trades_{wn}_base{sx}.csv.gz"), "rt", encoding="utf-8") as f1, \
                    gzip.open(os.path.join(SRC, f"trades_{wn}_N10{sx}.csv.gz"), "rt", encoding="utf-8") as f2:
                a_ = pd.read_csv(f1, dtype=str, keep_default_na=False); b_ = pd.read_csv(f2, dtype=str, keep_default_na=False)
            c1[f"交易檔{sx}"] = bool(a_[b_.columns].equals(b_))
        J[f"C1_{wn}"] = c1; log(f"[C1 {wn}] {c1}"); ok &= all(c1.values())
        # 低價（盤中讀法重掃用；load_bars 直讀）
        D.DATA = W["data"]; cache = {}

        def LOWF(sid):
            if sid not in cache:
                B = R11.load_bars(sid, W["mk"].get(sid, "twse"), W["cal"]); a = np.full(W["n0"], np.nan)
                a[np.asarray(B["idx"], int)] = np.asarray(B["l"], float); cache[sid] = a
            return cache[sid]
        for v in VAR:
            for sx in ("", "s"):
                df = rdx(os.path.join(OUT, f"trades_{wn}_{v}{sx}.csv.gz"))
                # C2
                eq, nh, bad = PNC.rebuild(W, df, 10, Bc, Bo)
                d = float(np.max(np.abs(eq / Z[f"{v}{sx}_eq"] - 1))); dn = int(np.sum(nh != Z[f"{v}{sx}_nh"]))
                c2 = {"逐日淨值最大相對差": d, "持股筆數不同日": dn, **bad, "買進筆": int(len(df))}
                ok &= d <= 1e-9 and dn == 0 and not any(bad.values())
                # C3
                if v != "base":
                    mode = v[:5]; th = -int(v[5:]) / 100
                    b3, ex, ns = rescan(W, df, mode, th, sx == "s", LOWF)
                    c2.update({"重掃不符": b3, "重掃停損筆": ns, "檔內停損筆": int(df["停損"].sum()), "例": str(ex)})
                    ok &= b3 == 0 and ns == int(df["停損"].sum())
                J[f"C2C3_{wn}_{v}{sx}"] = c2; log(f"[C2C3 {wn} {v}{sx}] {c2}")
        # C4 手算（D.load_stock 原始日線）
        rng = np.random.default_rng(20261020 + (0 if wn == "主" else 1))
        pool = []
        for v in ("close15", "close20", "close25", "close30"):
            df = rdx(os.path.join(OUT, f"trades_{wn}_{v}.csv.gz"))
            st = df[df["停損"].astype(bool)]
            for i in rng.choice(len(st), min(len(st), 2 if wn == "主" else 1), replace=False):
                pool.append((v, st.iloc[int(i)]))
        cal = W["cal"]
        for v, z in pool[: (6 if wn == "主" else 4)]:
            th = -int(v[5:]) / 100
            stk = D.load_stock(z["sid"], W["mk"].get(z["sid"], "twse"), cal).df
            dts = np.array([str(x.date()) for x in cal])
            e = int(np.flatnonzero(dts == z["買進日"])[0]); s = int(np.flatnonzero(dts == z["原排程賣出日"])[0]) if z["原排程賣出日"] else len(cal)
            o = stk["open"].to_numpy(float).copy(); c = stk["close"].to_numpy(float).copy()
            trd = stk["traded"].to_numpy(bool); o[~trd] = np.nan; c[~trd] = np.nan
            bp = o[e]; trig = None; sell = None; sp = None
            for d_ in range(e, s):
                if np.isfinite(c[d_]) and c[d_] / bp - 1 <= th + 1e-12:
                    trig = d_; break
            if trig is not None:
                for f in range(trig + 1, min(s, len(cal) - 1) + 1):
                    if np.isfinite(o[f]) and o[f] > 0:
                        sell = f; sp = o[f] if f != s else min(o[f], float(z["原排程賣價(未滑價)"])); break
            r = {"世界": wn, "門檻": v[5:], "sid": z["sid"], "買進日": z["買進日"], "買價(手算)": float(bp), "買價(檔)": float(z["市值基準價"]),
                 "觸發日(手算)": dts[trig] if trig is not None else "", "觸發日收盤報酬": float(c[trig] / bp - 1) if trig is not None else None,
                 "前一有收盤日報酬": float(c[[k for k in range(e, trig) if np.isfinite(c[k])][-1]] / bp - 1) if trig is not None and trig > e else None,
                 "觸發日(檔)": z["觸發日"], "賣出日(手算)": dts[sell] if sell is not None else "", "賣出日(檔)": z["賣出日"],
                 "賣價(手算)": float(sp) if sp is not None else None, "R(手算)": float(sp / bp - 1) if sp is not None else None, "R用(檔)": float(z["R用"]),
                 "原排程賣出日": z["原排程賣出日"], "若抱滿R": float(z["若抱滿g"])}
            r["相符"] = bool(r["觸發日(手算)"] == r["觸發日(檔)"] and r["賣出日(手算)"] == r["賣出日(檔)"] and r["R(手算)"] is not None
                           and abs(r["R(手算)"] - r["R用(檔)"]) <= 1e-12 and r["買價(手算)"] == r["買價(檔)"])
            hand.append(r); ok &= r["相符"]
            log(f"[C4 手算] {json.dumps(r, ensure_ascii=False)}")
        # C5
        bad5 = []; n5 = 0
        for _, r in TB[TB["世界"] == wn].iterrows():
            x = int(cal.searchsorted(pd.Timestamp(r["窗"].split("～")[0]))); y = int(cal.searchsorted(pd.Timestamp(r["窗"].split("～")[1])))
            bcg, bmd = PC.seg_metrics(Bc, x, y)
            if r["讀法"] == "0050":
                if abs(bcg - r["年化"]) > 1e-5 * max(1, abs(bcg)) or abs(bmd - r["回落"]) > 1e-5:
                    bad5.append(("0050", r["段"]))
                n5 += 1; continue
            th = r["門檻"]; sx = "s" if bool(r["滑價"]) else ""
            v = "base" if th == "無" else (("close" if r["讀法"].startswith("收盤") else "intra") + th.strip("-%"))
            cg, md = PC.seg_metrics(Z[f"{v}{sx}_eq"], x, y)
            if abs(cg - r["年化"]) > 1e-5 * max(1, abs(cg)) or abs(md - r["回落"]) > 1e-5 or PC.lab(cg, md, bcg, bmd) != r["標籤"]:
                bad5.append((v + sx, r["段"], cg, r["年化"]))
            n5 += 1
        J[f"C5_{wn}"] = {"列": n5, "不同": len(bad5), "例": [str(z) for z in bad5[:3]]}; log(f"[C5 {wn}] {J[f'C5_{wn}']}"); ok &= not bad5
        # C6
        bad6 = []
        for _, r in DC[DC["世界"] == wn].iterrows():
            v = ("close" if r["讀法"].startswith("收盤") else "intra") + r["門檻"].strip("-%")
            df = rdx(os.path.join(OUT, f"trades_{wn}_{v}.csv.gz"))
            x, y = W["segp"][r["段"]]
            dpos = {d: i for i, d in enumerate(W["dates"])}
            tb = df["買進日"].map(dpos).to_numpy(); m = (tb >= x) & (tb <= y)
            st = df[m & df["停損"].astype(bool).to_numpy()]
            now = st["R用"].to_numpy(float) - COST; hold = st["若抱滿g"].to_numpy(float) - COST; dif = now - hold
            mine = {"買進筆": int(m.sum()), "觸發筆": len(st), "少賠合計(等權)": float(dif[dif > 0].sum()), "少賺合計(等權)": float(-dif[dif < 0].sum()),
                    "被砍大賺(>+30%)筆": int((hold > 0.30).sum()), "躲掉大賠(≤−30%)筆": int((hold <= -0.30).sum()),
                    "若抱滿平均淨報酬": float(hold.mean()), "停損後平均淨報酬": float(now.mean())}
            for k, v_ in mine.items():
                if abs(v_ - float(r[k])) > 1e-5 * max(1.0, abs(v_)):
                    bad6.append((wn, v, r["段"], k, v_, r[k]))
        J[f"C6_{wn}"] = {"列": int((DC["世界"] == wn).sum()), "不同": len(bad6), "例": [str(z) for z in bad6[:3]]}
        log(f"[C6 {wn}] {J[f'C6_{wn}']}"); ok &= not bad6
        del W, Z, Z0
    J["C4_手算"] = hand
    # C7
    p = subprocess.run([sys.executable, "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True)
    gs = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines()
    mod = [l for l in gs if not l.startswith("??")]
    new = [l for l in gs if l.startswith("??") and "PTH10stop" in l]
    c7 = {"strategy_lock": p.stdout.strip().splitlines()[-1] if p.stdout.strip() else p.stderr.strip()[-200:], "rc": p.returncode,
          "既有追蹤檔有改動(工作樹，非本件)": mod, "本件新增": new}
    J["C7"] = c7; log(f"[C7] {c7}"); ok &= p.returncode == 0
    J["全部通過"] = bool(ok); J["耗時秒"] = round(time.time() - T0)
    json.dump(J, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] 全部通過 {ok}｜{J['耗時秒']}s")


if __name__ == "__main__":
    main()
