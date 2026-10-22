# -*- coding: utf-8 -*-
"""長線三問 丙 改抱大盤欄【對帳】——回測線計算子代理。⛔ 只讀；輸出 resultsLong3/alt/（或 alt/dry/）check.json、check.log。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLong3_alt_check [--dry]

K1 重建對帳：long3_alt.json 的 丙_表／events_丙 逐位元組相同旗標。
K2 新欄手算（全部被賣出者）：由【已提交】resultsLong3/events_丙.csv.gz 的 賣價 R、抱 3 年 R、抱 1 年 R、賣日、抱3年出場日，
   加上獨立讀入的 origin/main market_tri.csv（逐日比對日期），重算 d_alt、d1_alt、d1′_alt（乾跑：R ＝ 0、指數 ＝ 1）；誤差 ＜1e−12。
K3 抱 1 年出場日：typ1＝1 ⇒ ＝ 日曆[e＋249]；typ1∈{2,3,4} ⇒ ＜ 日曆[e＋249]；且 ≤ 抱 3 年出場日；另抽 20 筆逐根迴圈獨立重算抱 1 年出場日與 R。
K4 不前視：指數買進日 ＝ 賣日 ≥ 進場日；指數賣出日 ＝ 抱 3 年出場日 ≥ 賣日。
K5 表由逐筆重算：觸發數、d_alt／d1_alt／d1′_alt 平均（pandas 直接平均）與 CI（research11.cl_stats，1.96）。
K6 原欄不變：表內原 d、d1、d1′ 平均 ＝ 已提交 丙_表.csv；既有檔 md5 與跑前快照相同（/tmp/l3a_md5_before.txt）。
K7 策略鎖：python -m backtest.strategy_lock --check。
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchAscTri_freq as AT              # noqa: E402
from backtest import research11 as R                        # noqa: E402
import backtest.data as D                                   # noqa: E402

ORIG = "backtest/resultsLong3"
FS = ("F1", "F2", "F3", "F4", "F5", "F6", "F7")
C_ETF = 0.001425 * 2 + 0.001
LOG = []
OK = {}


def log(s):
    print(s, flush=True); LOG.append(s)


def chk(name, cond, detail=""):
    OK[name] = bool(cond)
    log(f"{'✅' if cond else '❌'} {name} {detail}")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    OUT = os.path.join(ORIG, "alt", "dry") if a.dry else os.path.join(ORIG, "alt")
    J = json.load(open(os.path.join(OUT, "long3_alt.json"), encoding="utf-8"))
    EV = pd.read_csv(os.path.join(OUT, "events_丙_alt.csv.gz"), dtype={"sid": str, "期別": str})
    TB = pd.read_csv(os.path.join(OUT, "丙_alt_表.csv"))
    CR = pd.read_csv(os.path.join(ORIG, "events_丙.csv.gz"), dtype={"sid": str, "期別": str})
    TCo = pd.read_csv(os.path.join(ORIG, "丙_表.csv"))
    # K1
    chk("K1 重建 丙_表／events_丙 與已提交逐位元組相同", J["重建"]["丙_表逐位元組相同"] and J["重建"]["events_丙逐位元組相同"])
    # 日曆（獨立讀）
    cals = []
    for wn in ("早年", "主"):
        D.DATA = AT.WORLDS[wn]["data"]; cals.append(D.load_calendar())
    CAL = cals[0].append(cals[1]); CP = {d.strftime("%Y-%m-%d"): j for j, d in enumerate(CAL)}
    ne = len(cals[0]); CEND = len(CAL) - 1
    # 指數（獨立讀）
    blob = subprocess.run(["git", "show", "origin/main:data/history/market_tri.csv"], capture_output=True, check=True).stdout
    chk("K2a 指數檔 sha 與主程式相同", hashlib.sha256(blob).hexdigest()[:16] == J["指數"]["sha256"])
    T = pd.read_csv(io.BytesIO(blob))
    tdict = dict(zip(T["date"], T["close"].astype(float)))
    tdates = sorted(tdict)

    def tri(dstr):
        if a.dry:
            return 1.0
        if dstr in tdict:
            return tdict[dstr]
        import bisect
        i = bisect.bisect_right(tdates, dstr) - 1
        return tdict[tdates[i]]

    M = CR.merge(EV, on=["sid", "期別"], suffixes=("", "_a"))
    chk("K2b 筆數相同", len(M) == len(CR) == len(EV), f"{len(M)}")
    err = []; n_sold = 0; viol4 = 0
    for _, r in M.iterrows():
        b3 = 0.0 if a.dry else r["抱3年R"]; b1 = 0.0 if a.dry else r["抱1年R"]
        for F in FS:
            if not r[f"{F}_賣"]:
                continue
            n_sold += 1
            sv = 0.0 if a.dry else r[f"{F}_R"]
            sd = r[f"{F}_賣日"]; x3 = r["抱3年出場日"]; x1 = r["抱1年出場日"]
            if not (r["進場日"] <= sd <= x3):
                viol4 += 1
            alt3 = (1 + sv) * (tri(x3) / tri(sd) - C_ETF) - 1
            err.append(abs((alt3 - b3) - r[f"{F}_d_alt"]))
            if np.isfinite(r["抱1年R"]):
                err.append(abs((alt3 - b1) - r[f"{F}_d1_alt"]))
                v = ((1 + sv) * (tri(x1) / tri(sd) - C_ETF) - 1 - b1) if sd <= x1 else 0.0
                err.append(abs(v - r[f"{F}_d1alt_alt"]))
    chk("K2c 被賣出者 d_alt／d1_alt／d1′_alt 手算", max(err) < 1e-12, f"{n_sold} 筆｜最大誤差 {max(err):.2e}")
    chk("K4 指數買進日＝賣日 ≥ 進場日、賣出日＝抱3年出場日 ≥ 賣日", viol4 == 0, f"違反 {viol4}")
    # K3 抱 1 年出場日
    v3 = 0
    for _, r in M[np.isfinite(M["抱1年R"])].iterrows():
        e = int(r["e"]); x1 = r["抱1年出場日"]; t1 = int(r["typ1"])
        ref = str(CAL[e + 249].date()) if e + 249 <= CEND else None
        x3 = r["抱3年出場日"]
        if ref is None or (t1 == 1 and x1 != ref) or (t1 in (2, 3, 4) and not x1 < ref) or (isinstance(x3, str) and not (x1 <= x3)):
            v3 += 1
    chk("K3a 抱 1 年出場日與型態相符、≤ 抱 3 年出場日", v3 == 0, f"違反 {v3}")
    # K3b 抽 20 筆逐根迴圈
    WS = {}
    rng = np.random.default_rng(20261023)
    pick = M[np.isfinite(M["抱1年R"]) & M["窗完整"]]
    pick = pick.iloc[rng.choice(len(pick), 20, replace=False)]
    e3 = []
    for _, r in pick.iterrows():
        s = r["sid"]; e = int(r["e"]); x = e + 249
        P = []
        for wn, off in (("早年", 0), ("主", ne)):
            if wn not in WS:
                WS[wn] = AT.load_world(wn)
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
            P.append((wn, idx + off, np.asarray(B["o"], float), np.asarray(B["c"], float), np.asarray(B["rc"], float), bad))
        pos = np.concatenate([p[1] for p in P]); o = np.concatenate([p[2] for p in P]); c = np.concatenate([p[3] for p in P])
        rc = np.concatenate([p[4] for p in P]); bad = np.concatenate([p[5] for p in P]).copy()
        wid = np.concatenate([np.full(len(p[1]), 0 if p[0] == "早年" else 1) for p in P])
        if (wid == 0).any() and (wid == 1).any():
            bad[int(np.argmax(wid == 1))] = False
        ke = int(np.flatnonzero(pos == e)[0]); k = ke; v = c[ke] / o[ke]
        while k + 1 < len(pos) and pos[k + 1] <= x:
            if bad[k + 1]:
                break
            v *= (rc[k + 1] / rc[k]) if wid[k + 1] != wid[k] else (c[k + 1] / c[k]); k += 1
        e3.append(abs((v - 1) - r["抱1年R"]) if str(CAL[pos[k]].date()) == r["抱1年出場日"] else 1.0)
    chk("K3b 抽 20 筆逐根迴圈重算抱 1 年出場日與 R", max(e3) < 1e-9, f"最大誤差 {max(e3):.2e}")
    # K5 表由逐筆重算
    p141231 = int(CAL.searchsorted(pd.Timestamp("2014-12-31"), side="right")) - 1
    p170302 = int(CAL.searchsorted(pd.Timestamp("2017-03-02"))); p211230 = int(CAL.searchsorted(pd.Timestamp("2021-12-30"), side="right")) - 1
    SEG = {"全部窗完整": (0, CEND), "早年進場(～2014)": (0, p141231), "2015～進場": (p141231 + 1, CEND), "探索進場(2017-03～2021-12)": (p170302, p211230)}
    mx = 0.0; nbad = 0
    for _, t in TB.iterrows():
        a0, a1 = SEG[t["進場段"]]; F = t["法"]
        sub = EV[(EV["e"] >= a0) & (EV["e"] <= a1) & EV["窗完整"] & np.isfinite(EV["抱3年R"])]
        nbad += int(len(sub) != t["事件(窗完整)"]) + int(int(sub[f"{F}_賣"].sum()) != t["觸發賣出"])
        for col, tc, lo, hi in ((f"{F}_d_alt", "d_alt平均(賣掉的錢改抱大盤)", "d_alt_lo", "d_alt_hi"), (f"{F}_d1_alt", "d1_alt平均", "d1_alt_lo", "d1_alt_hi"),
                                (f"{F}_d1alt_alt", "d1′_alt平均", "d1′_alt_lo", "d1′_alt_hi")):
            x = sub[col].to_numpy(float); km = sub["進場月"].to_numpy()
            ok = np.isfinite(x)
            cs = R.cl_stats(x[ok], km[ok])
            mx = max(mx, abs(float(np.mean(x[ok])) - t[tc]), abs(cs["mean"] - 1.96 * cs["se"] - t[lo]), abs(cs["mean"] + 1.96 * cs["se"] - t[hi]))
    chk("K5 表由逐筆重算（筆數、觸發數、平均、CI）", nbad == 0 and mx < 1e-9, f"筆數不符 {nbad}｜最大差 {mx:.2e}")
    # K6
    if not a.dry:
        o = TCo.set_index(["進場段", "法"])
        d6 = 0.0
        for _, t in TB.iterrows():
            q = o.loc[(t["進場段"], t["法"])]
            d6 = max(d6, abs(q["d平均(加賣法−抱3年)"] - t["d平均(原：賣掉的錢記0)"]), abs(q["d1平均(對抱1年)"] - t["d1平均(原，對抱1年)"]),
                     abs(q["d1′平均(1年窗另一讀法)"] - t["d1′平均(原，1年窗)"]), int(q["觸發賣出"] != t["觸發賣出"]))
        chk("K6a 表內原 d、d1、d1′、觸發數 ＝ 已提交 丙_表", d6 < 1e-12, f"最大差 {d6:.2e}")
    md = subprocess.run("md5sum -c /tmp/l3a_md5_before.txt", shell=True, capture_output=True, text=True)
    chk("K6b 既有檔（researchLong3*.py、resultsLong3 頂層）md5 與跑前相同", md.returncode == 0, md.stdout.strip().splitlines()[-1] if md.stdout.strip() else md.stderr[-200:])
    out = subprocess.run([sys.executable, "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True)
    chk("K7 策略鎖相符", out.returncode == 0 and "相符" in out.stdout, out.stdout.strip().splitlines()[-1] if out.stdout.strip() else out.stderr[-200:])
    allok = all(OK.values())
    log(f"{'✅ 全部通過' if allok else '❌ 有未通過'}（{sum(OK.values())}／{len(OK)}）")
    json.dump({"全部通過": allok, "項": OK}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
