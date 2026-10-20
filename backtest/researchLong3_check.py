# -*- coding: utf-8 -*-
"""長線怎麼操作三問 seq1 正式跑【對帳】——回測線計算子代理。⛔ 只讀 backtest/resultsLong3/（freq/ 外）與資料，不寫任何既有檔；輸出 resultsLong3/check.json、check.log。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLong3_check

C1 抽 20 筆手算（甲）：逐根迴圈（逐日價格比連乘，接縫用原始收盤比）重算 R、出場型態、對照平均、X、對 0050；另抽 10 筆丙、10 筆乙。
C2 對照重建：long3.json 的 S1／S3 重建逐列相同旗標；對照名單每筆 ≠ 自己、無重複、數量 ＝ min(20, 池)；抽到的 20 筆其對照逐檔驗池條件。
C3 不前視：S1 進場日 ＝ 期別可用日（次月 10／15 日之後第一個交易日）且 sp ＜ e；PTH 類 進場 ＞ 形成月底；出場日 ≥ 進場日；丙 賣日 ＞ 觸發日 ≥ 進場日；乙 進場 ＞ 形成日。
C4 彙總重算：甲判定格與全表、丙表、乙表由逐筆檔重算，逐欄比（容差 1e−9）。
C5 策略鎖：python -m backtest.strategy_lock --check。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import zlib

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchLong3 as L3                    # noqa: E402
from backtest import researchLong3_freq as LF               # noqa: E402
from backtest import researchAscTri_freq as AT              # noqa: E402
from backtest import research11 as R                        # noqa: E402
import backtest.data as D                                   # noqa: E402

OUT = L3.OUT
LOG = []
OK = {}


def log(s):
    print(s, flush=True); LOG.append(s)


def chk(name, cond, detail=""):
    OK[name] = bool(cond)
    log(f"{'✅' if cond else '❌'} {name} {detail}")


def main():
    J = json.load(open(os.path.join(OUT, "long3.json"), encoding="utf-8"))
    EA = pd.read_csv(os.path.join(OUT, "events_甲.csv.gz"), dtype={"sid": str, "對照": str})
    TA = pd.read_csv(os.path.join(OUT, "甲_表.csv"))
    CR = pd.read_csv(os.path.join(OUT, "events_丙.csv.gz"), dtype={"sid": str, "期別": str})
    TC = pd.read_csv(os.path.join(OUT, "丙_表.csv"))
    BR = pd.read_csv(os.path.join(OUT, "events_乙.csv.gz"), dtype={"sid": str})
    BT = pd.read_csv(os.path.join(OUT, "乙_表.csv"))
    # ── 世界與逐股（獨立迴圈用）
    WS = {wn: AT.load_world(wn) for wn in ("早年", "主")}
    ne = WS["早年"]["n0"]
    CAL = WS["早年"]["cal"].append(WS["主"]["cal"]); NC = len(CAL); CEND = NC - 1
    CP = {d.strftime("%Y-%m-%d"): j for j, d in enumerate(CAL)}
    cache = {}

    def bars(s):
        if s in cache:
            return cache[s]
        out = []
        for wn, off in (("早年", 0), ("主", ne)):
            W = WS[wn]
            if s not in W["ix"]:
                continue
            D.DATA = W["data"]
            B = R.load_bars(s, W["mk"].get(s, "twse"), W["cal"])
            if B is None:
                continue
            idx = B["idx"].astype(np.int64); nb = len(idx)
            bad = np.asarray(B["next_bad"][:nb] == np.arange(nb), bool)
            for p_ in W["BADPOS"].get(s, ()):
                k = int(np.searchsorted(idx, p_, "left"))
                if k < nb:
                    bad[k] = True
            out.append((wn, idx + off, np.asarray(B["o"], float), np.asarray(B["c"], float), np.asarray(B["rc"], float), bad))
        cache[s] = out
        return out

    def series(s):
        P = bars(s)
        pos = np.concatenate([p[1] for p in P]); o = np.concatenate([p[2] for p in P]); c = np.concatenate([p[3] for p in P])
        rc = np.concatenate([p[4] for p in P]); bad = np.concatenate([p[5] for p in P]).copy(); wid = np.concatenate([np.full(len(p[1]), 0 if p[0] == "早年" else 1) for p in P])
        main = any(p[0] == "主" for p in P)
        if (wid == 0).any() and (wid == 1).any():
            bad[int(np.argmax(wid == 1))] = False
        return pos, o, c, rc, bad, wid, main

    def hand(s, e, x):
        """逐根迴圈：⇒ (R, typ, 出場位置)。價格比 ＝ 開盤→收盤再逐日收盤比連乘；接縫那一步用原始收盤比。"""
        pos, o, c, rc, bad, wid, main = series(s)
        ke = int(np.flatnonzero(pos == e)[0])
        if x > CEND:
            return np.nan, 5, -1
        k = ke; v = c[ke] / o[ke]
        while k + 1 < len(pos) and pos[k + 1] <= x:
            if bad[k + 1]:
                return v - 1.0, 3, int(pos[k])
            step = (rc[k + 1] / rc[k]) if wid[k + 1] != wid[k] else (c[k + 1] / c[k])
            v *= step; k += 1
        if k == len(pos) - 1 and pos[k] < x:
            L = int(pos[k])
            if (not main) and L >= ne - 5 and x >= ne:
                return np.nan, 6, -1
            if CEND - L >= 5:
                return v - 1.0, 4, L
        return v - 1.0, (1 if pos[k] == x else 2), int(pos[k])

    D.DATA = WS["早年"]["data"]; B0 = R.load_bars("0050", "twse", WS["早年"]["cal"])
    D.DATA = WS["主"]["data"]; B1 = R.load_bars("0050", "twse", WS["主"]["cal"])
    p50 = np.r_[B0["idx"], B1["idx"] + ne]; o50 = np.r_[B0["o"], B1["o"]]; c50 = np.r_[B0["c"], B1["c"]]; rc50 = np.r_[B0["rc"], B1["rc"]]; j50 = len(B0["idx"])

    def hand50(e, x):
        ke = int(np.searchsorted(p50, e, "left")); kx = int(np.searchsorted(p50, min(x, CEND), "right")) - 1
        v = c50[ke] / o50[ke]
        for k in range(ke + 1, kx + 1):
            v *= (rc50[k] / rc50[k - 1]) if k == j50 else (c50[k] / c50[k - 1])
        return v - 1.0

    # ── C1 甲 抽 20
    rng = np.random.default_rng(20261021)
    jud = EA[EA["集合"].isin(["S1", "S3"]) & (EA["H"] == 250) & np.isfinite(EA["X"])]
    oth = EA[~EA.index.isin(jud.index) & np.isfinite(EA["X"]) & (EA["H"] >= 750)]
    smp = pd.concat([jud.iloc[rng.choice(len(jud), 12, replace=False)], oth.iloc[rng.choice(len(oth), 8, replace=False)]])
    errs = []
    for _, r in smp.iterrows():
        Rh, th, xp = hand(r["sid"], int(r["e"]), int(r["x"]))
        picks = r["對照"].split("|") if isinstance(r["對照"], str) and r["對照"] else []
        cm = np.mean([hand(m, int(r["e"]), int(r["x"]))[0] for m in picks]) if picks else np.nan
        r5 = hand50(int(r["e"]), int(r["x"]))
        errs.append(max(abs(Rh - r["R"]), abs(cm - r["對照R平均"]), abs((Rh - cm) - r["X"]), abs(r5 - r["R0050"])))
        if th != int(r["typ"]):
            errs.append(9.0)
        log(f"  甲 {r['集合']} {r['sid']} {r['進場日']} H{r['H']}：R {Rh:+.6f}／檔 {r['R']:+.6f}｜型 {th}／{r['typ']}｜對照 {cm:+.6f}／{r['對照R平均']:+.6f}｜0050 {r5:+.6f}／{r['R0050']:+.6f}")
    chk("C1 甲 抽 20 筆手算（逐根連乘、接縫原始收盤比）", max(errs) < 1e-9, f"最大誤差 {max(errs):.2e}")
    # 丙 抽 10（有賣出者）
    cs = []
    full = CR[CR["窗完整"] & np.isfinite(CR["抱3年R"])]
    for F in ("F7", "F6", "F3", "F1", "F4"):
        sub = full[full[f"{F}_賣"] == True]  # noqa: E712
        for _, r in sub.iloc[rng.choice(len(sub), 2, replace=False)].iterrows():
            s = r["sid"]; e = int(r["e"])
            R3, t3, x3 = hand(s, e, e + 749)
            pos, o, c, rc, bad, wid, main = series(s)
            ks = int(np.flatnonzero(pos == CP[r[f"{F}_賣日"]])[0]); ke = int(np.flatnonzero(pos == e)[0])
            # 賣價比：同上迴圈到 ks 的開盤
            v = c[ke] / o[ke]
            for k in range(ke + 1, ks):
                v *= (rc[k] / rc[k - 1]) if wid[k] != wid[k - 1] else (c[k] / c[k - 1])
            # v ＝ 前一根收盤的價值；賣在 ks 開盤
            sv = v * (rc[ks] / rc[ks - 1]) * (o[ks] / c[ks]) if wid[ks] != wid[ks - 1] else v * (o[ks] / c[ks - 1])
            d_ = (sv - 1.0) - R3
            cs.append(abs(d_ - r[f"{F}_d"])); cs.append(abs(R3 - r["抱3年R"]))
            # 不前視：賣日 ＞ 觸發日
            cs.append(0.0 if pos[ks] > CP[_trig(r, F, s)] else 9.0)
            log(f"  丙 {F} {s} {r['進場日']}：d {d_:+.6f}／檔 {r[f'{F}_d']:+.6f}｜抱3年 {R3:+.6f}／{r['抱3年R']:+.6f}")
    chk("C1 丙 抽 10 筆手算（賣價、抱 3 年、d）", max(cs) < 1e-9, f"最大誤差 {max(cs):.2e}")
    # 乙 抽 10
    MEY = {}
    for Y in range(2004, 2027):
        p_ = int(CAL.searchsorted(pd.Timestamp(f"{Y}-12-31"), side="right")) - 1
        if CAL[p_].year == Y and CAL[p_].month == 12:
            MEY[Y] = p_
    bs = []
    bv = BR[np.isfinite(BR["R"])]
    for _, r in bv.iloc[rng.choice(len(bv), 10, replace=False)].iterrows():
        Y = int(r["形成年"]); e = MEY[Y] + 1; x = MEY[Y + int(r["月"]) // 12]
        Rh, th, _ = hand(r["sid"], e, x)
        bs.append(abs(Rh - r["R"]))
        log(f"  乙 {Y} {r['sid']} {r['月']}月：R {Rh:+.6f}／檔 {r['R']:+.6f}")
    chk("C1 乙 抽 10 筆手算", max(bs) < 1e-9, f"最大誤差 {max(bs):.2e}")
    # ── C2 對照重建
    chk("C2 S1／S3 重建與已提交逐列相同", J["對照重建"]["S1逐列相同"] and J["對照重建"]["S3逐列相同"], json.dumps(J["對照重建"], ensure_ascii=False))
    pk = EA[EA["對照"].notna()]
    bad_ = 0
    for s, pl, n_pool, n_c in zip(pk["sid"], pk["對照"], pk["池大小"], pk["對照數"]):
        p = pl.split("|")
        if s in p or len(set(p)) != len(p) or len(p) != min(20, n_pool) or len(p) != n_c:
            bad_ += 1
    chk("C2 對照名單：≠ 自己、無重複、數量 ＝ min(20, 池)", bad_ == 0, f"違反 {bad_}／{len(pk)}")
    # 抽到的 20 筆：對照逐檔驗池條件
    EVp = pd.concat([pd.read_csv(LF.PTHEV.format(wn), dtype={"sid": str}).assign(世界=wn) for wn in ("早年", "主")], ignore_index=True)
    vio = 0
    for _, r in smp.iterrows():
        e = int(r["e"]); wn = "早年" if e < ne else "主"; W = WS[wn]; off = 0 if wn == "早年" else ne
        for m in r["對照"].split("|"):
            if r["集合"].startswith("S1"):
                i = W["ix"][m]; ew = e - off
                pos, o, c, rc, bad, wid, main = series(m)
                okc = W["TRD"][i, ew] and W["O"][i, ew] > 0 and not W["UPL"][i, ew] and (pos == e).any()
                vio += int(not okc)
            else:
                g = EVp[(EVp["sid"] == m) & (EVp["跳月_進場日"] == r["進場日"]) & (EVp["跳月_st"] == "保留")]
                vio += int(len(g) != 1)
    chk("C2 抽 20 筆的對照逐檔符合池條件", vio == 0, f"違反 {vio}")
    # ── C3 不前視
    S1 = pd.read_csv(os.path.join(LF.OUT, "events_S1.csv.gz"), dtype={"sid": str, "期別": str})
    s1k = S1[S1["st"] == "保留"]
    av_ok = 0
    for p, e, sp in zip(s1k["期別"], s1k["e"], s1k["sp"]):
        y, m = int(p[:4]), int(p[5:]); y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
        cut = pd.Timestamp(y2, m2, 15 if p >= "2026-01" else 10)
        av_ok += int(CAL[e] > cut and CAL[e - 1] <= cut and sp < e)
    chk("C3 S1 進場日 ＝ 可用日（次月 10／15 日之後第一個交易日）且 sp ＜ e", av_ok == len(s1k), f"{av_ok}／{len(s1k)}")
    pth = EA[EA["集合"].isin(["S2", "S3", "M"])]
    mm = pth.merge(EVp[["sid", "跳月_進場日", "形成月底"]].drop_duplicates(), left_on=["sid", "進場日"], right_on=["sid", "跳月_進場日"], how="left")
    chk("C3 PTH 類 進場 ＞ 形成月底（跳 1 個月）", bool((mm["進場日"] > mm["形成月底"]).all()), f"{len(mm)} 列")
    ex = EA[EA["出場日"].notna() & (EA["出場日"] != "")]
    chk("C3 出場日 ≥ 進場日", bool((ex["出場日"] >= ex["進場日"]).all()))
    viol = 0
    for F in L3.FS:
        sub = CR[CR[f"{F}_賣"] == True]  # noqa: E712
        ev = pd.read_csv(os.path.join(LF.OUT, "events_丙.csv.gz"), dtype={"sid": str, "期別": str}).set_index(["sid", "期別"])
        tr = ev.loc[list(zip(sub["sid"], sub["期別"])), f"{F}_首次"].to_numpy()
        viol += int(((sub[f"{F}_賣日"].to_numpy() <= tr) | (tr < sub["進場日"].to_numpy())).sum())
    chk("C3 丙 賣日 ＞ 觸發日 ≥ 進場日", viol == 0, f"違反 {viol}")
    # ── C4 彙總重算
    p = lambda ts: int(CAL.searchsorted(pd.Timestamp(ts)))
    ple = lambda ts: int(CAL.searchsorted(pd.Timestamp(ts), side="right")) - 1
    SEG = {}
    for H in (120, 250):
        SEG[(H, "探索")] = (p("2017-03-02"), ple("2020-12-31") if H == 250 else ple("2021-12-30"), ple("2021-12-30"))
        SEG[(H, "確認")] = (p("2022-01-03"), CEND, CEND)
        SEG[(H, "早年(描述)")] = (p("2005-01-01"), ple("2014-12-31"), CEND)
    for H in (750, 1250):
        SEG[(H, "長窗2005～2021")] = (p("2005-01-01"), ple("2021-12-31"), CEND)
        SEG[(H, "長窗_2005～2014")] = (p("2005-01-01"), ple("2014-12-31"), CEND)
        SEG[(H, "長窗_2015～2021")] = (ple("2014-12-31") + 1, ple("2021-12-31"), CEND)
    mx = 0.0; nrow = 0
    for _, r in TA.iterrows():
        a0, a1, xb = SEG[(int(r["H"]), r["段"])]
        sub = EA[(EA["集合"] == r["集合"]) & (EA["H"] == r["H"]) & (EA["e"] >= a0) & (EA["e"] <= a1) & (EA["x"] <= xb) & np.isfinite(EA["R"]) & np.isfinite(EA["X"])]
        if len(sub) == 0:
            continue
        cs_ = R.cl_stats(sub["X"].to_numpy(float), sub["進場月"].to_numpy())
        z = L3.ZB2 if (r["集合"] in ("S1", "S3") and int(r["H"]) == 250 and r["段"] in ("探索", "確認")) else 1.96
        mx = max(mx, abs(cs_["mean"] - r["X_平均"]), abs(cs_["mean"] - z * cs_["se"] - r["X_lo"]), abs(len(sub) - r["X_n"]))
        ne_ = min(len(sub), cs_["months"])
        rs = "依構造不可判定" if ne_ < 30 else ("結果①" if cs_["mean"] - z * cs_["se"] <= 0 <= cs_["mean"] + z * cs_["se"] else ("結果②" if cs_["mean"] > 0 else "結果③"))
        if rs != r["X_結果"]:
            mx = 9.0
        nrow += 1
    chk("C4 甲 全表由逐筆重算（平均、下界、筆數、結果）", mx < 1e-9, f"{nrow} 列，最大差 {mx:.2e}")
    mx = 0.0
    for _, r in TC.iterrows():
        a0, a1 = {"全部窗完整": (0, CEND), "早年進場(～2014)": (0, ple("2014-12-31")), "2015～進場": (ple("2014-12-31") + 1, CEND),
                  "探索進場(2017-03～2021-12)": (p("2017-03-02"), ple("2021-12-30"))}[r["進場段"]]
        sub = CR[(CR["e"] >= a0) & (CR["e"] <= a1) & CR["窗完整"] & np.isfinite(CR["抱3年R"])]
        F = r["法"]
        mx = max(mx, abs(sub[f"{F}_d"].mean() - r["d平均(加賣法−抱3年)"]), abs(int((sub[f"{F}_賣"] == True).sum()) - r["觸發賣出"]))  # noqa: E712
    chk("C4 丙 表由逐筆重算（d 平均、觸發數）", mx < 1e-9, f"最大差 {mx:.2e}")
    mx = 0.0
    for _, r in BT[BT["量"] == "組−市場（等權）"].iterrows():
        sub = BR[(BR["月"] == r["月"]) & np.isfinite(BR["R"])]
        mk = sub.groupby("形成年")["R"].mean()
        col = {"個股贏家": "贏家", "個股輸家": "輸家", "產業贏家": "贏家產業", "產業輸家": "輸家產業"}[r["組"]]
        v = sub[sub[col]]
        x = v["R"].to_numpy() - mk.loc[v["形成年"]].to_numpy()
        mx = max(mx, abs(x.mean() - r["逐股平均"]), abs(pd.Series(x).groupby(v["形成年"].to_numpy()).mean().mean() - r["形成年等權平均"]))
    chk("C4 乙 表由逐筆重算（逐股、形成年等權）", mx < 1e-9, f"最大差 {mx:.2e}")
    # ── C5 策略鎖
    out = subprocess.run([sys.executable, "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True)
    chk("C5 策略鎖相符", out.returncode == 0 and "相符" in out.stdout, out.stdout.strip().splitlines()[-1] if out.stdout.strip() else out.stderr[-200:])
    allok = all(OK.values())
    log(f"[結論] 全部通過 {allok}")
    json.dump({"全部通過": allok, "項": OK}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


def _trig(r, F, s):
    ev = _trig.ev
    return ev.at[(s, r["期別"]), f"{F}_首次"]


_trig.ev = pd.read_csv(os.path.join(os.path.expanduser("~/tw-p17"), "backtest/resultsLong3/freq/events_丙.csv.gz"), dtype={"sid": str, "期別": str}).set_index(["sid", "期別"])

if __name__ == "__main__":
    main()
