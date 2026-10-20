# -*- coding: utf-8 -*-
"""三重底 seq1 事件層 獨立對帳（⛔ 不 import researchTripleBot、researchTripleBot_freq、researchKDJ3、patterns_all、patterns_x、researchPatC
任何一行；只 import 資料層 researchAscTri_freq、research11.load_bars，與對帳共用小工具 researchKDJ3_check（同樣只用資料層）；
原始偵測／保留狀態取已提交的頻率表 resultsTripleBot/freq/events_<世界>.csv.gz）。本體跑完後：

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTripleBot_check [--sample 20]

C1 彙總重算（TripleBot_main.csv 每一列，從逐筆檔；同 KDJ3_check C1）。C2 假訊號 x／30 與 seq322 自判。
C3 差（J − M、J_有量縮 − J_沒量縮、M_有量縮 − M_沒量縮）自己寫曆月線性化 SE 重算。
C4 抽 --sample 筆（主：J 7、M 3；早年：J 7、M 3；探索／確認輪流；種子 20261021）逐根手算：
   三個底 L1／L2／L3（事件檔）：左右各 3 根的局部最低收盤、兩兩間隔 ≥ 5 根、三底差 ≤ 5%、較高反彈高點 ≥ 最低底 10%、r60[L1]＜0、
   確認日 L3＋3 ≤ T、[L3＋3, T) 收盤都 ≤ 反彈高點、T 收盤 ＞ 反彈高點、L1 到 T ≤ 60 根；判定格另驗 放量（T 量 ÷ 前 20 根均量 ≥ 1.5、收紅）、
   長期下跌（第一底收盤 ÷ 過去 250 根（不跨壞根）最高收盤 − 1 ≤ −20%）；母體（自算 500 張閘）、T＋1 可買；
   錨點 r60（第一底前一根 ÷ 前 61 根 − 1，窗內無壞 K 棒）、R（H20／60／120）；
   對照：全市場逐檔獨立重建——第一底那天 pit_valid ∧ 有效 K 棒 ∧ r60 可算 ⇒ pd.qcut(rank(first), 10)；T 當天母體、T＋1 可買、
   原始偵測取頻率表事件檔（該格任何狀態）、(first, T＋H] 硬斷點逐日掃、R 可算 ⇒ 對照平均、對照數，與逐筆檔比。
C5 不前視：同一批，把資料截在 T 重算 r60 錨點、放量、長期下跌與型態條件 ⇒ 相同；進場日 ＝ 日曆 T＋1、出場日 ＝ 日曆 T＋H。
結果寫 resultsTripleBot/check.json、check.log。
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchAscTri_freq as AT      # noqa: E402  資料層（世界）
from backtest import researchKDJ3_check as KC       # noqa: E402  對帳共用小工具（只用資料層）

OUT = "backtest/resultsTripleBot"
FREQ = "backtest/resultsTripleBot/freq"
TOL = KC.TOL
HS = KC.HS
LOG = KC.LOG
log = KC.log


def pattern_check(M, sid, T, L1, L2, L3, judge, cut_at=None):
    """⇒ dict（各條件 True／False）＋ 量。全部只用 ≤ T（cut_at）的 K 棒。"""
    s = M.ST[sid]
    idx = [int(p) for p in s["idx"] if cut_at is None or p <= cut_at]
    c = np.array([s["c"][p] for p in idx]); o = np.array([s["o"][p] for p in idx]); v = np.array([s["vol"][p] for p in idx])
    kT, k1, k2, k3 = idx.index(T), idx.index(L1), idx.index(L2), idx.index(L3)
    out = {}
    lm = True
    for kk in (k1, k2, k3):
        if kk - 3 < 0 or kk + 3 > kT:
            lm = False; continue
        lm &= bool(c[kk] <= c[kk - 3:kk + 4].min())
    out["三底皆為左右各3根局部最低"] = lm
    out["間隔≥5根"] = bool(k2 - k1 >= 5 and k3 - k2 >= 5)
    vv = c[[k1, k2, k3]]; mn = vv.min()
    out["三底差≤5%"] = bool((vv.max() - mn) / mn <= 0.05)
    cA = max(c[k1:k2 + 1].max(), c[k2:k3 + 1].max())
    out["反彈高點≥最低底10%"] = bool((cA - mn) / mn >= 0.10)
    r60 = c[k1 - 1] / c[k1 - 61] - 1 if k1 >= 61 else np.nan
    out["r60[L1]<0"] = bool(np.isfinite(r60) and r60 < 0)
    out["確認日L3+3≤T"] = bool(k3 + 3 <= kT)
    out["[L3+3,T)收盤≤反彈高點"] = bool(all(c[j] <= cA for j in range(k3 + 3, kT)))
    out["T收盤>反彈高點"] = bool(c[kT] > cA)
    out["L1到T≤60根"] = bool(kT - k1 + 1 <= 60)
    q = {"cA": float(cA), "r60L1": float(r60)}
    if judge:
        badk = s["badk"]
        w = list(range(kT - 20, kT))
        okw = kT >= 20 and not any(j in badk for j in range(kT - 19, kT + 1)) and np.isfinite(v[kT - 20:kT + 1]).all() and v[kT - 20:kT].mean() > 0
        vr = float(v[kT] / v[w].mean()) if okw else np.nan
        segst = max([j for j in range(1, k1 + 1) if j in badk], default=0)
        st = max(k1 - 249, segst)
        dd = float(c[k1] / c[st:k1 + 1].max() - 1) if k1 - st + 1 >= 60 else np.nan
        out["放量 vr20≥1.5 且收紅"] = bool(np.isfinite(vr) and vr >= 1.5 and c[kT] > o[kT])
        out["長期下跌 ≤−20%"] = bool(np.isfinite(dd) and dd <= -0.20)
        q.update({"vr20": vr, "dd250": dd})
    return out, q


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--sample", type=int, default=20); ap.add_argument("--out", default=None)
    ap.add_argument("--dry", action="store_true", help="對乾跑輸出驗流程：手算 R 一律寫 0（⛔ 不讀報酬）")
    a = ap.parse_args()
    out = a.out or OUT
    MAIN = pd.read_csv(os.path.join(out, "TripleBot_main.csv"), encoding="utf-8-sig")
    DIFF = pd.read_csv(os.path.join(out, "TripleBot_diff.csv"), encoding="utf-8-sig")
    FQ = pd.read_csv(os.path.join(FREQ, "freq.csv"), encoding="utf-8-sig")
    CHK = {}
    cals = {}
    import backtest.data as D
    for wn in ("主", "早年"):
        D.DATA = AT.WORLDS[wn]["data"]; cals[wn] = D.load_calendar()
    CHK["C1 彙總重算"], EVD, samesign = KC.check_main(MAIN, FQ, cals, out)
    log(f"C1 {CHK['C1 彙總重算']}")
    CHK["C2 假訊號 x／30 與 seq322"] = KC.check_fake(MAIN, out, samesign)
    log(f"C2 {CHK['C2 假訊號 x／30 與 seq322']}")
    nd = 0; w3 = 0.0; bad3 = []
    for new, old in (("J", "M"), ("J_有量縮", "J_沒量縮"), ("M_有量縮", "M_沒量縮")):
        n_, w_, b_ = KC.check_diff(DIFF, EVD, cals, new, old, f"{new} − {old}", {"差": "差"})
        nd += n_; w3 = max(w3, w_); bad3 += b_
    CHK["C3 差"] = {"列數": nd, "最大差": w3, "不同": bad3[:20], "過": not bad3}
    log(f"C3 {CHK['C3 差']}")
    rng = np.random.default_rng(20261021)
    res4 = []; w4 = 0.0
    nJ = max(1, round(a.sample * 0.35)); nM = max(1, a.sample // 2 - nJ)
    plan = {"主": [("J", nJ), ("M", nM)], "早年": [("J", nJ), ("M", nM)]}
    for wn in ("主", "早年"):
        M = KC.Mkt(wn); cal = M.cal; n0 = M.n0; W = M.W
        ev = pd.read_csv(os.path.join(FREQ, f"events_{wn}.csv.gz"), dtype=str)
        RAW = {c: set(zip(ev[ev["格"] == c]["sid"], ev[ev["格"] == c]["T"])) for c in ("J", "M")}
        picks = []
        for cell, m in plan[wn]:
            segs = ["探索", "確認"] if wn == "主" else ["早年"]
            for q in range(m):
                sg = segs[q % len(segs)]
                f = EVD[(wn, sg, cell, 20)]; f = f[f["配對"] == "有"]
                picks.append((sg, cell, f.iloc[int(rng.integers(len(f)))]))
        cache_dec = {}
        for sg, cell, e in picks:
            T = int(cal.searchsorted(pd.Timestamp(e["T"]))); sid0 = e["sid"]
            erow = ev[(ev["格"] == cell) & (ev["sid"] == sid0) & (ev["T"] == e["T"])].iloc[0]
            L1, L2, L3 = (int(cal.searchsorted(pd.Timestamp(erow[z]))) for z in ("L1", "L2", "L3"))
            f0 = int(cal.searchsorted(pd.Timestamp(e["first"])))
            chk = {"first＝L1": bool(f0 == L1)}
            pc, q = pattern_check(M, sid0, T, L1, L2, L3, judge=(cell == "J"))
            chk.update(pc)
            if cell == "J":
                chk["vr20 同事件檔"] = bool(abs(q["vr20"] - float(erow["vr20"])) <= 6e-5)
                chk["dd250 同事件檔"] = bool(abs(q["dd250"] - float(erow["dd250"])) <= 6e-5)
            pcc, qc = pattern_check(M, sid0, T, L1, L2, L3, judge=(cell == "J"), cut_at=T)
            chk["不前視：型態／放量／長期下跌 截在 T 相同"] = bool(pcc == pc and all((np.isnan(qc[k]) and np.isnan(q[k])) or qc[k] == q[k] for k in q))
            chk["母體"] = M.gate(sid0, T); chk["T+1可買"] = M.t1ok(sid0, T)
            chk["進場日＝日曆T+1"] = str(cal[T + 1].date()) == e["進場日"]
            rv = M.rN_pre(sid0, f0); rvc = M.rN_pre(sid0, f0, cut=T)
            chk["不前視：錨點 r60 截在 T 相同"] = bool(rv == rvc)
            chk["錨點 r60 同逐筆檔"] = bool(abs(rv - float(e["r60"])) <= TOL)
            if f0 not in cache_dec:
                vals = {}
                for sid in M.ST:
                    if f0 in M.ST[sid]["posset"] and W["PV"][M.ix[sid]][f0]:
                        v = M.rN_pre(sid, f0)
                        if np.isfinite(v):
                            vals[sid] = v
                cache_dec[f0] = pd.qcut(pd.Series(vals).rank(method="first"), 10, labels=False)
            dec = cache_dec[f0]
            d0_ = dec[sid0]
            for H in HS:
                fH = EVD[(wn, sg, cell, H)]; row = fH[(fH["sid"] == sid0) & (fH["T"] == e["T"])]
                if not len(row) or row.iloc[0]["配對"] != "有":
                    continue
                row = row.iloc[0]
                chk[f"H{H} 出場日＝日曆T+{H}"] = str(cal[T + H].date()) == row["出場日"]
                ctrl = []
                for sid in dec.index:
                    if sid == sid0 or dec[sid] != d0_ or (sid, e["T"]) in RAW[cell]:
                        continue
                    if not M.gate(sid, T) or not M.t1ok(sid, T) or M.brk(sid, f0, T + H):
                        continue
                    g = M.Rof(sid, T, H, a.dry)
                    if np.isfinite(g):
                        ctrl.append(g)
                r0 = M.Rof(sid0, T, H, a.dry); cm = float(np.mean(ctrl)) if ctrl else np.nan
                d1 = abs(r0 - float(row["R"])); d2 = abs(cm - float(row["對照平均"])); d3 = abs((r0 - cm) - float(row["X"]))
                w4 = max(w4, d1, d2, d3)
                chk[f"H{H} R同"] = bool(d1 <= TOL); chk[f"H{H} 對照平均同"] = bool(d2 <= TOL); chk[f"H{H} X同"] = bool(d3 <= TOL)
                chk[f"H{H} 對照數同"] = bool(len(ctrl) == int(row["對照數"])); chk[f"H{H} 十分位同"] = bool(int(d0_) == int(row["十分位"]))
                chk[f"H{H} 自身(first,T+H]無斷點"] = not M.brk(sid0, f0, T + H)
                chk[f"H{H} 手算"] = {"R": r0, "對照平均": cm, "對照數": len(ctrl)}
            okall = all(v for v in chk.values() if isinstance(v, bool))
            res4.append({"世界": wn, "段": sg, "格": cell, "sid": sid0, "T": e["T"], "first": e["first"], "全同": okall, **chk})
            log(f"C4 {res4[-1]}")
        del M
    CHK["C4／C5 抽樣逐根手算（含不前視）"] = {"筆數": len(res4), "最大差": w4, "全同": all(x["全同"] for x in res4), "明細": res4}
    CHK["全部過"] = bool(CHK["C1 彙總重算"]["過"] and CHK["C2 假訊號 x／30 與 seq322"]["過"] and CHK["C3 差"]["過"]
                     and CHK["C4／C5 抽樣逐根手算（含不前視）"]["全同"])
    json.dump(CHK, open(os.path.join(out, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log("全部過" if CHK["全部過"] else "⛔ 有不同")
    open(os.path.join(out, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
