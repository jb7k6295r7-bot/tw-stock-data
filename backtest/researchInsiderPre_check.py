# -*- coding: utf-8 -*-
"""董監／大股東申報轉讓後偏弱 seq2 正式跑【對帳】——回測線計算子代理。⛔ 只讀 backtest/resultsInsiderPre/（freq/ 外）與資料，不寫任何既有檔；
輸出 resultsInsiderPre/check.json、check.log。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchInsiderPre_check

C1 策略鎖相符（25 支）。
C2 頻率表逐列重建：recon_freq.csv 35 欄全 0 不同；正式跑保留事件 ＝ 頻率表 st＝保留（exright 差異列另計）。
C3 抽 12 筆手算（一般交易 60 日：主 9、早年 3）：事件與配對公司 R 用 researchIndMom_check.Indep 逐根迴圈重算 ⇒ X（容差 1e−9）。
C4 配對合法（抽 200 筆主配對）：配對 ≠ 事件公司；csv 模組自讀事件表原檔，配對公司在 T 的合併日曆位置 ±60 交易日內沒有任何申報列；
   與事件公司同 T 前 12 個月報酬五分位（xsec，exright 版）；e 進場保留；是池中 e 可買者裡 |log 市值比| 最小者（同距離依代號）。
C5 不前視（全部保留事件）：日曆[T] ≤ 首筆申報日 ＜ 日曆[e]，T ＝ e − 1；出場目標 ＝ e ＋ H − 1 ≥ e。
C6 彙總：InsiderPre_表.csv 判定列與全部「全部」子組列 n、n_eff、X̄、lo、hi、結果由 events 重算（容差 1e−12）；prior3_diff.csv 兩段重算。
C7 隱私：輸出檔（本夾 freq/ 外）欄名無 holder／姓名；全文不含任何 holder_key 值。
C8 措辭：結果句、必附無「建議」「放空」；全部輸出無「安慰劑」；必附含六句。
"""
from __future__ import annotations

import bisect
import csv
import glob
import gzip
import json
import os
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchInsiderPre as IP               # noqa: E402
from backtest import researchInsiderPre_freq as Q           # noqa: E402
from backtest import researchSEO_freq as SQ                 # noqa: E402
from backtest import researchIndMom as IMX                  # noqa: E402
from backtest import researchIndMom_freq as IM              # noqa: E402
from backtest import researchIndMom_check as IC             # noqa: E402

OUT = IP.OUT
LOG = IC.LOG
OK = IC.OK
log = IC.log
chk = IC.chk


def main():
    IC.lock_check()
    EV = pd.read_csv(os.path.join(OUT, "events.csv.gz"), dtype={"sid": str, "配對公司": str})
    TB = pd.read_csv(os.path.join(OUT, "InsiderPre_表.csv"))
    P3 = pd.read_csv(os.path.join(OUT, "prior3_diff.csv"))
    RC = pd.read_csv(os.path.join(OUT, "recon_freq.csv"))
    EXD = pd.read_csv(os.path.join(OUT, "exright_diff.csv"), dtype=str)
    EF = pd.read_csv(os.path.join(IP.FREQ_DIR, "events.csv.gz"), dtype=str, keep_default_na=False)
    J = json.load(open(os.path.join(OUT, "InsiderPre.json"), encoding="utf-8"))
    # C2
    chk("C2a recon_freq 35 欄全同", len(RC) == len(IP.CMP) == 35 and int(RC["不同列數"].sum()) == 0)
    kf = set(zip(EF.loc[EF["st"] == "保留", "sid"], EF.loc[EF["st"] == "保留", "date"], EF.loc[EF["st"] == "保留", "組"]))
    km = set(zip(EV["sid"], EV["date"], EV["組"]))
    exs = set(zip(EXD.loc[EXD["欄"] == "st", "sid"], EXD.loc[EXD["欄"] == "st", "date"], EXD.loc[EXD["欄"] == "st", "組"])) if len(EXD) else set()
    chk("C2b 保留事件 ＝ 頻率表 st＝保留（exright st 差異另計）", len({k for k in kf ^ km if k not in exs}) == 0,
        f"頻率表 {len(kf)}、本檔 {len(km)}、exright st 差異 {len(exs)}")
    # 面板
    Zx = {}
    for wn in ("早年", "主"):
        Zo = IMX.aux2(IM.panel_aux(IM.build_panel(wn, 2)))
        Zx[wn] = IMX.make_x(Zo, IMX.build_exr(Zo))
    IXs = {wn: {s: i for i, s in enumerate(Z["sids"])} for wn, Z in Zx.items()}
    # C3
    rng = np.random.default_rng(20261021)
    errs = []
    g60 = EV[(EV["組"] == "一般交易") & (EV["H60"] == "ok")]
    for wn, k in (("主", 9), ("早年", 3)):
        IPd = IC.Indep(wn); cal = Zx[wn]["cal"]
        pool = g60[g60["世界"] == wn]
        for _, r in pool.iloc[rng.choice(len(pool), k, replace=False)].iterrows():
            e = int(cal.searchsorted(pd.Timestamp(r["e"]))); x = e + 59
            Re, te = IPd.ret(r["sid"], e, x); Rm, tm = IPd.ret(r["配對公司"], e, x)
            errs.append(max(abs(Re - r["R60"]), abs(Rm - r["R配對60"]), abs(Re - Rm - r["X60"])))
            log(f"   {wn} {r['date']} {r['sid']}↔{r['配對公司']}：R {Re:+.6f}／{r['R60']:+.6f}（{te}）配對 {Rm:+.6f}／{r['R配對60']:+.6f}（{tm}）X {Re - Rm:+.6f}／{r['X60']:+.6f}")
    chk("C3 抽 12 筆 事件／配對 R、X 手算", max(errs) < 1e-9, f"最大誤差 {max(errs):.2e}")
    # C4：自讀原檔
    DATA = IP.pinned_data()
    raw_d = defaultdict(list); hk = set()
    for f in sorted(glob.glob(os.path.join(DATA, "meta", "insider_predeclare", "insider_predeclare_*.csv"))):
        for row in csv.DictReader(open(f, encoding="utf-8")):
            raw_d[row["stock_id"]].append(pd.Timestamp(row["declare_date"])); hk.add(row["holder_key"])
    CAL = Q.combined_cal(Zx); NC = len(CAL)
    rawp = {s: sorted(int(CAL.searchsorted(d, side="right")) - 1 for d in v) for s, v in raw_d.items()}
    bad = defaultdict(int); memo = {"早年": {}, "主": {}}
    sub = EV[EV["配對實際"] == "主配對"]
    sub = sub.iloc[np.random.default_rng(20261022).choice(len(sub), 200, replace=False)]
    for _, r in sub.iterrows():
        wn = r["世界"]; Z = Zx[wn]; cal = Z["cal"]; ix = IXs[wn]
        e = int(cal.searchsorted(pd.Timestamp(r["e"]))); T = e - 1
        i, j, m = ix[r["sid"]], ix[r["配對公司"]], r["配對公司"]
        bad["≠自己"] += m == r["sid"]
        pT = int(CAL.searchsorted(cal[T])); lo, hi = max(pT - 60, 0), min(pT + 60, NC - 1)

        def declared(s):
            v = rawp.get(s, [])
            k = bisect.bisect_left(v, lo)
            return k < len(v) and v[k] <= hi
        bad["±60非申報"] += declared(m)
        out, qm, qr = SQ.xsec(Z, T, memo[wn])
        dr = lambda k: int(np.searchsorted(qr, out[k][1], "right"))
        bad["同報酬五分位"] += dr(i) != dr(j)
        bad["配對e保留"] += IM.entry_flag(Z, j, T, e) != "保留"
        cand = [k for k in out if k != i and not declared(Z["sids"][k]) and dr(k) == dr(i) and IM.entry_flag(Z, k, T, e) == "保留"]
        best = min(cand, key=lambda k: (abs(np.log(out[k][0] / out[i][0])), Z["sids"][k]))
        bad["最近可買"] += best != j
    for k, v in bad.items():
        log(f"   C4 {k}：違反 {v}／{len(sub)}")
    chk("C4 配對合法（≠自己、±60 交易日非申報、同五分位、可買、最近）", all(v == 0 for v in bad.values()), json.dumps(dict(bad), ensure_ascii=False))
    # C5
    nb = 0
    for _, r in EV.iterrows():
        cal = Zx[r["世界"]]["cal"]; e = int(cal.searchsorted(pd.Timestamp(r["e"]))); T = int(cal.searchsorted(pd.Timestamp(r["T"])))
        d = pd.Timestamp(r["date"])
        nb += not (T == e - 1 and cal[T] <= d < cal[e])
    chk("C5 不前視 日曆[T] ≤ 首筆申報日 ＜ 日曆[e]、T＝e−1", nb == 0, f"違反 {nb}／{len(EV)}")
    # C6
    worst = 0.0; nbad = 0; cnt = 0
    edt = pd.to_datetime(EV["e"]); tail = Zx["主"]["cal"][-1]
    SG = dict(list(IP.SEGS.items()) + [("主全窗(參考)", ("2017-03-01", None))])
    for _, r in TB[TB["子組"] == "全部"].iterrows():
        x_, y_ = SG[r["段"]]
        insg = (edt >= pd.Timestamp(x_)) & (edt <= (tail if y_ is None else pd.Timestamp(y_)))
        H = int(r["H"])
        g = EV[insg & (EV["組"] == r["組"]) & (EV[f"H{H}"] == "ok")]
        st = IMX.stats(g[f"X{H}"], g["申報月"])
        cnt += 1
        if st["n"] == 0:
            nbad += int(r["n"]) != 0; continue
        for k in ("X̄", "lo", "hi"):
            worst = max(worst, abs(st[k] - r[k]))
        nbad += (st["n"] != r["n"]) or (st["n_eff"] != r["n_eff"]) or (st["結果"] != r["結果"])
    for _, r in P3[P3["段"].isin(["探索", "確認"])].iterrows():
        x_, y_ = SG[r["段"]]
        insg = (edt >= pd.Timestamp(x_)) & (edt <= (tail if y_ is None else pd.Timestamp(y_)))
        g = EV[insg & (EV["組"] == "一般交易") & (EV["H60"] == "ok") & EV["占比"].notna()]
        b = g["占比"] >= 0.01; x = g["X60"].to_numpy(); m1, m0 = x[b].mean(), x[~b].mean()
        psi = np.where(b, (x - m1) / b.sum(), -(x - m0) / (~b).sum())
        se = np.sqrt((pd.Series(psi).groupby(g["申報月"].to_numpy()).sum() ** 2).sum())
        worst = max(worst, abs((m1 - m0) - r["差"]), abs(se - r["se"])); cnt += 1
    chk("C6 彙總重算（全部子組各列＋先驗③差）", worst < 1e-12 and nbad == 0, f"{cnt} 列、最大誤差 {worst:.2e}、不符 {nbad}")
    # C7
    fs = [f for f in glob.glob(os.path.join(OUT, "*")) if os.path.isfile(f) and not f.endswith(("check.json", "check.log"))]
    colbad = []; hit = []
    hk.discard("")
    for f in fs:
        txt = gzip.open(f, "rt", encoding="utf-8").read() if f.endswith(".gz") else open(f, encoding="utf-8", errors="ignore").read()
        head = txt.split("\n", 1)[0]
        if any(w in head for w in ("holder", "姓名")):
            colbad.append(os.path.basename(f))
        toks = set(t for t in __import__("re").findall(r"[0-9a-f]{12}", txt))
        if toks & hk:
            hit.append(os.path.basename(f))
    chk("C7 隱私（無 holder／姓名欄、無 holder_key 值）", not colbad and not hit, f"檔 {len(fs)}；欄 {colbad}；holder_key {hit}")
    # C8
    s_all = J["結果句"] + "".join(J["必附"])
    alltxt = "".join(open(f, encoding="utf-8", errors="ignore").read() for f in fs if not f.endswith(".gz"))
    need = ["描述，不是選股規則", "贈與、信託不算賣出、另組", "台股文獻只讀到摘要", "單筆層通過 ≠ 組合會贏 0050", "申報要賣近半最後沒賣完", "限制員工"]
    chk("C8 措辭（無建議／放空、無安慰劑、必附六句）", not any(w in s_all for w in ("建議", "放空")) and "安慰劑" not in alltxt and all(any(n in x for x in J["必附"]) for n in need))
    allok = all(OK.values())
    log(f"{'✅ 全部通過' if allok else '❌ 有不通過'}（{sum(OK.values())}／{len(OK)}）")
    json.dump({"全部通過": allok, "項": OK}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
