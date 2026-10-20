# -*- coding: utf-8 -*-
"""PREREG接近52週新高組合層 seq1【獨立對帳】——回測線計算子代理。⛔ 只讀結果夾、不改任何檔（只寫 resultsPTHpf/check.json、check.log）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTHpf_check

C1 逐日重建持倉與淨值（份迴圈各臂 M、Mslip、NOSKIP、H3、H12，兩世界，全部日子）：只用 trades 表（份、買進日、金額、市值基準價、R用、排程賣出日、入帳）
   ＋ 0050 開收盤 ＋ 快取收盤，自寫逐份逐日迴圈（每份記 0050 單位與現金）⇒ 對 eq npz 逐日；並驗：
   ① 每批 Σ金額 ＝ 該份當天可用（前一日現金 ＋ 0050 單位 × 開盤 × (1 − 0.2425%)）、同批等權；② 入帳 ＝ 金額×(1＋R用−0.585%)；
   ③ 同份前一批出清後才進下一批；④ 印 6 個抽樣日的明細（持有筆數、相異檔數、各份 0050 單位、現金）。
C2 事件與滑價：M 的 R用 ＝ resultsPTH 事件層同一 (代號, 形成月底) 的 R；市值基準價 ＝ 快取還原開盤；Mslip 市值基準價 ＝ M×1.005、R用 ＝ 賣價×0.995÷(買價×1.005)−1；
   排程賣出日：到期／到期無成交 ⇒ 進場月起第 6 個曆月最後交易日；強制、末根 ⇒ 事件層出場日。
C3 10 檔版（S10）：自寫 10 槽迴圈（新部位 min(前一日淨值÷10, 0050 可撥)、T 開盤賣 0050 0.2425%、賣出當天留現金、隔天開盤買回 0.1425%）⇒ 對 eq；
   每個買進日：買到的 PTH ≥ 同日沒買到且未持有的候選（由高往下補）、持股 ≤ 10、同檔不重複；有空槽卻有未買候選的日子 ＝ 0。
C4 0050 價：npz 的 Bc／Bo ＝ data.load_stock("0050") 還原收盤（ffill）／開盤（缺 ⇒ 前一日收盤）。
C5 段指標：自寫年化（(末/首)^(245/點數)−1）與最大回落、0050 同窗 ⇒ 對主表；判準標籤重算（researchAscTri.label 字面另寫）。
C6 等效獨立檔數：主判每段抽 2 個買進日，researchDumb.eff_n（原函式、逐對迴圈）⇒ 對矩陣化值。
C7 隨機：200 列齊、有限；重跑第 0、137 次 ⇒ 與 random 檔逐欄相同。
C8 策略鎖：python -m backtest.strategy_lock --check ＝ 相符（25 支）；git 工作樹：本件只新增檔、既有追蹤檔無本件改動。
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
from backtest import researchPTHpf as M                     # noqa: E402  常數、build_world、rand_job、effn_vec（C6 對照）
from backtest import researchDumb as RD                     # noqa: E402
from backtest import data as D                              # noqa: E402
from backtest import researchAddOn as RA                    # noqa: E402

OUT = M.OUT
COST = 0.00585; BUY = 0.001425; SELL = 0.002425; SLIP = 0.005
TRARMS = {"M": 6, "Mslip": 6, "NOSKIP": 6, "H3": 3, "H12": 12}
STRC = ("sid", "形成月底", "買進日", "賣出日", "排程賣出日", "進場日", "出場種類", "季")


def rd(path):
    """數值欄照數值讀（缺 ⇒ NaN）、日期與代號欄讀字串（缺 ⇒ ""）。"""
    df = pd.read_csv(path, dtype={c: str for c in STRC}, float_precision="round_trip")
    for c in STRC:
        if c in df.columns:
            df[c] = df[c].fillna("").astype(object)
    return df


def rebuild_tranche(W, df, H, Bc, Bo, log, tag, sample):
    n0 = W["n0"]; CM = W["CM"]; ix = W["ix"]; dpos = {d: i for i, d in enumerate(W["dates"])}
    df = df.copy()
    df["t"] = df["買進日"].map(dpos); df["j"] = df["sid"].map(ix)
    df["s"] = [dpos[d] if d else -1 for d in df["賣出日"]]
    bad = {"批金額≠可用": 0, "非等權": 0, "入帳式": 0, "份重疊": 0, "賣出≠排程": 0}
    exp = df["金額"] * (1 + df["R用"] - COST)
    sold = df["s"] >= 0
    bad["入帳式"] = int((np.abs(df.loc[sold, "入帳"] - exp[sold]) > 1e-12 * np.abs(exp[sold])).sum())
    bad["賣出≠排程"] = int((df["賣出日"] != df["排程賣出日"]).sum())
    groups = {}
    for (k, t), g in df.groupby(["份", "t"]):
        groups.setdefault(int(k), {})[int(t)] = g
    eq = np.zeros(n0); nh = np.zeros(n0, int); detail = {}
    u = {k: (1.0 / H) / Bc[0] for k in range(H)}; c = {k: 0.0 for k in range(H)}
    inflow = {k: {} for k in range(H)}
    openpos = []                                      # (j, 金額, 基準價, 賣出日或 n0)
    busy = {k: -1 for k in range(H)}
    for t in range(n0):
        for k in range(H):
            g = groups.get(k, {}).get(t)
            if g is not None:
                cap = c[k] + u[k] * Bo[t] * (1 - SELL)
                if abs(g["金額"].sum() / cap - 1) > 1e-12:
                    bad["批金額≠可用"] += 1
                if g["金額"].max() - g["金額"].min() > 1e-15 * cap:
                    bad["非等權"] += 1
                if busy[k] >= t:
                    bad["份重疊"] += 1
                u[k] = 0.0; c[k] = 0.0
                for j, a_, ep, s_, pr in zip(g["j"], g["金額"], g["市值基準價"], g["s"], g["入帳"]):
                    openpos.append((int(j), float(a_), float(ep), int(s_) if s_ >= 0 else n0))
                    if s_ >= 0:
                        inflow[k][int(s_)] = inflow[k].get(int(s_), 0.0) + float(pr); busy[k] = max(busy[k], int(s_))
                    else:
                        busy[k] = n0
            elif c[k] > 0:
                u[k] += c[k] * (1 - BUY) / Bo[t]; c[k] = 0.0
            c[k] += inflow[k].pop(t, 0.0)
        openpos = [p for p in openpos if p[3] > t]
        hv = sum(a_ * CM[j, t] / ep for j, a_, ep, s_ in openpos)
        eq[t] = sum(u[k] * Bc[t] + c[k] for k in range(H)) + hv
        nh[t] = len(openpos)
        if t in sample:
            detail[W["dates"][t]] = {"持有筆數": len(openpos), "相異檔數": len({p[0] for p in openpos}), "淨值": eq[t],
                                    "0050市值": sum(u[k] * Bc[t] for k in range(H)), "現金": sum(c.values()), "個股市值": hv}
    return eq, nh, bad, detail


def rebuild_slot(W, df, Bc, Bo):
    """10 槽：只用 trades 表（買進日、金額、市值基準價、R用、賣出日）重建 ⇒ eq；並驗金額 ＝ min(前日淨值÷10, 可撥)。"""
    n0 = W["n0"]; CM = W["CM"]; ix = W["ix"]; dpos = {d: i for i, d in enumerate(W["dates"])}
    t_ = df["買進日"].map(dpos).to_numpy(); j_ = df["sid"].map(ix).to_numpy(); s_ = np.array([dpos[d] if d else -1 for d in df["賣出日"]])
    by = {}
    for q, t in enumerate(t_):
        by.setdefault(int(t), []).append(q)
    units = 1.0 / Bc[0]; pend = 0.0; openp = []; eq = np.zeros(n0); bad = {"金額≠min(槽,可撥)": 0, "持股>10": 0, "入帳式": 0}
    for t in range(n0):
        if pend > 0:
            units += pend * (1 - BUY) / Bo[t]; pend = 0.0
        still = []
        for q in openp:
            if 0 <= s_[q] <= t and not (s_[q] == t and t_[q] == t):
                pr = df["金額"].iat[q] * (1 + df["R用"].iat[q] - COST)
                if abs(pr - df["入帳"].iat[q]) > 1e-12 * abs(pr):
                    bad["入帳式"] += 1
                pend += pr
            else:
                still.append(q)
        openp = still
        for q in by.get(t, []):
            slot = (eq[t - 1] if t > 0 else 1.0) / 10; avail = units * Bo[t] * (1 - SELL)
            a_ = df["金額"].iat[q]
            if abs(a_ - min(slot, avail)) > 1e-12 * max(a_, 1.0):           # 0050 剩零頭時相對誤差放大 ⇒ 以淨值尺度比
                bad["金額≠min(槽,可撥)"] += 1
            units -= a_ / ((1 - SELL) * Bo[t]); openp.append(q)
        still = []
        for q in openp:
            if s_[q] == t and t_[q] == t:
                pend += df["金額"].iat[q] * (1 + df["R用"].iat[q] - COST)
            else:
                still.append(q)
        openp = still
        if len(openp) > 10:
            bad["持股>10"] += 1
        eq[t] = units * Bc[t] + pend + sum(df["金額"].iat[q] * CM[j_[q], t] / df["市值基準價"].iat[q] for q in openp)
    return eq, bad


def ev_light(W, wn):
    """事件（跳月）⇒ 隨機臂用陣列（自讀事件檔與快取開盤，⛔ 不呼叫主檔 load_events）。"""
    fr = pd.read_csv(os.path.join(M.EVD, f"trades_{wn}_跳月.csv.gz"), dtype=str, keep_default_na=False)
    dpos = {d: i for i, d in enumerate(W["dates"])}; jm_of = {W["dates"][p]: j for j, p in enumerate(W["ME"])}
    tinv = {v: k for k, v in M.TYPN.items()}
    j = np.array([W["ix"][s] for s in fr["sid"]]); e = np.array([dpos[d] for d in fr["進場日"]])
    jm = np.array([jm_of[d] for d in fr["形成月底"]]); typ = np.array([tinv[x] for x in fr["出場種類"]])
    R = np.array([float(x) if x else np.nan for x in fr["R"]]); sd = np.array([dpos[x] if x else -1 for x in fr["出場日"]])
    X = W["XP"][(2, 6)][jm]
    sale = np.where(np.isin(typ, (1, 2)), X, np.where(np.isin(typ, (3, 4)), sd, -1))
    P = np.asarray(W["O"], float)[j, e]
    return {"j": j, "e": e, "sale": sale, "P": P, "px": P * (1 + R), "R": R}


def seg_metrics(eq, x, y):
    seg = eq[x:y + 1]; yrs = len(seg) / 245
    cg = (seg[-1] / seg[0]) ** (1 / yrs) - 1
    pk = np.maximum.accumulate(seg); md = float(((seg - pk) / pk).min())
    return cg, md


def lab(c, m, bc, bm):
    if c > bc and c / abs(m) >= bc / abs(bm):
        return "合格"
    return "另列" if c > bc else "不合格"


def main():
    log = RA.log_to(os.path.join(OUT, "check.log"))
    T0 = time.time(); J = {"時間": M.now_tpe()}; ok = True
    TB = pd.read_csv(os.path.join(OUT, "PTHpf_main.csv"), encoding="utf-8-sig")
    PJ = json.load(open(os.path.join(OUT, "PTHpf.json"), encoding="utf-8"))
    for wn in ("主", "早年"):
        W = M.build_world(wn, log)
        Z = np.load(os.path.join(OUT, f"eq_{wn}.npz"))
        # C4
        D.DATA = W["data"]; st = D.load_stock("0050", "twse", W["cal"]).df
        bc = pd.Series(st["close"].to_numpy(float)).ffill().to_numpy(); bo = st["open"].to_numpy(float).copy()
        for t in range(len(bo)):
            if not (np.isfinite(bo[t]) and bo[t] > 0):
                bo[t] = bc[t - 1] if t > 0 else bc[0]
        c4 = {"Bc 最大差": float(np.max(np.abs(Z["Bc"] - bc))), "Bo 最大差": float(np.max(np.abs(Z["Bo"] - bo)))}
        J[f"C4_{wn}"] = c4; log(f"[C4 {wn}] {c4}"); ok &= c4["Bc 最大差"] == 0 and c4["Bo 最大差"] == 0
        Bc, Bo = Z["Bc"], Z["Bo"]
        rng = np.random.default_rng(20261020 + M.WID[wn])
        sample = set(int(t) for t in rng.choice(np.arange(300, W["n0"]), 6, replace=False))
        # C1
        TRD = {arm: rd(os.path.join(OUT, f"trades_{wn}_{arm}.csv.gz")) for arm in list(TRARMS) + ["S10"]}
        for arm, H in TRARMS.items():
            df = TRD[arm].copy()
            eq, nh, bad, det = rebuild_tranche(W, df, H, Bc, Bo, log, f"{wn}/{arm}", sample if arm == "M" else set())
            d = float(np.max(np.abs(eq / Z[f"{arm}_eq"] - 1)))
            dn = int(np.sum(nh != Z[f"{arm}_nh"]))
            c1 = {"逐日淨值最大相對差": d, "持股筆數不同日": dn, **bad}
            J[f"C1_{wn}_{arm}"] = c1
            if det:
                J[f"C1_{wn}_{arm}_抽樣日明細"] = det
                for k_, v_ in det.items():
                    log(f"  [C1 抽樣 {wn}/{arm} {k_}] {json.dumps(v_, ensure_ascii=False, default=float)}")
            log(f"[C1 {wn}/{arm}] {c1}")
            ok &= d <= 1e-9 and dn == 0 and not any(bad.values())
        # C2
        ev = pd.read_csv(os.path.join(M.EVD, f"trades_{wn}_跳月.csv.gz"), dtype={"sid": str}, keep_default_na=False, float_precision="round_trip")
        evk = {(s, f): (r, x, ty) for s, f, r, x, ty in zip(ev["sid"], ev["形成月底"], ev["R"], ev["出場日"], ev["出場種類"])}
        m_ = TRD["M"]; s_ = TRD["Mslip"]
        dpos = {d: i for i, d in enumerate(W["dates"])}
        nb = {"R用≠事件R": 0, "基準價≠快取開盤": 0, "滑價基準價": 0, "滑價R": 0, "排程賣出日": 0, "列數": int(len(m_))}
        mk = {(a_, b_): q for q, (a_, b_) in enumerate(zip(m_["sid"], m_["形成月底"]))}
        O = np.asarray(W["O"], float)
        for q in range(len(m_)):
            r_, xd, ty = evk[(m_["sid"].iat[q], m_["形成月底"].iat[q])]
            rr = float(r_) if r_ != "" else np.nan
            if not ((np.isnan(rr) and np.isnan(m_["R用"].iat[q])) or rr == m_["R用"].iat[q]):
                nb["R用≠事件R"] += 1
            P = O[W["ix"][m_["sid"].iat[q]], dpos[m_["買進日"].iat[q]]]
            if P != m_["市值基準價"].iat[q]:
                nb["基準價≠快取開盤"] += 1
            e = dpos[m_["買進日"].iat[q]]
            ym = W["cal"][e].year * 12 + W["cal"][e].month - 1 + 5
            lastd = W["cal"][(W["cal"].year == ym // 12) & (W["cal"].month == ym % 12 + 1)]
            want = (str(lastd[-1].date()) if len(lastd) else "") if ty in ("到期收盤", "到期日無成交、用前一根收盤") else (xd if ty != "資料尾未出場" else "")
            if want != m_["排程賣出日"].iat[q]:
                nb["排程賣出日"] += 1
        for q in range(len(s_)):
            p = mk[(s_["sid"].iat[q], s_["形成月底"].iat[q])]
            P = m_["市值基準價"].iat[p]; R_ = m_["R用"].iat[p]
            if abs(s_["市值基準價"].iat[q] - P * 1.005) > 1e-12 * P:
                nb["滑價基準價"] += 1
            want = P * (1 + R_) * 0.995 / (P * 1.005) - 1
            if not ((np.isnan(want) and np.isnan(s_["R用"].iat[q])) or abs(s_["R用"].iat[q] - want) <= 1e-12):
                nb["滑價R"] += 1
        J[f"C2_{wn}"] = nb; log(f"[C2 {wn}] {nb}"); ok &= not any(v for k, v in nb.items() if k != "列數")
        # C3
        df = TRD["S10"].copy()
        eq, bad = rebuild_slot(W, df, Bc, Bo)
        d = float(np.max(np.abs(eq / Z["S10_eq"] - 1)))
        # 由高往下：同日沒買到、未持有的候選 PTH ≤ 買到的最低 PTH（且槽滿或 0050 用盡）
        held_on = {}
        tb = df["買進日"].map(dpos).to_numpy(); ts = np.array([dpos[x] if x else W["n0"] + 1 for x in df["賣出日"]])
        viol = 0; nday = 0
        evd = ev.assign(t=ev["進場日"].map(dpos))
        for t, g in df.groupby(tb):
            nday += 1
            held = set(df["sid"][(tb < t) & (ts > t)])
            cand = evd[(evd["t"] == t) & ~evd["sid"].isin(held) & ~evd["sid"].isin(set(g["sid"]))]
            nheld = int(((tb < t) & (ts > t)).sum()) + len(g)
            if len(cand) and g["PTH"].min() < cand["PTH"].max() - 1e-15:
                viol += 1
            if len(cand) and nheld < 10 and Z["S10_u"][t] > 1e-9:
                viol += 1
        c3 = {"逐日淨值最大相對差": d, "買進日": nday, "由高往下違反日": viol, **bad}
        J[f"C3_{wn}"] = c3; log(f"[C3 {wn}] {c3}"); ok &= d <= 1e-9 and viol == 0 and not any(bad.values())
        # C5
        bad5 = []
        for r in [z for z in PJ["主表"] if z["世界"] == wn]:                 # JSON 為全精度（csv 為 6 位）
            x = int(W["cal"].searchsorted(pd.Timestamp(r["窗"].split("～")[0]))); y = int(W["cal"].searchsorted(pd.Timestamp(r["窗"].split("～")[1])))
            cg, md = seg_metrics(Z[f"{r['臂']}_eq"], x, y); bcg, bmd = seg_metrics(Bc, x, y)
            if abs(cg - r["年化"]) > 1e-9 or abs(md - r["回落"]) > 1e-9 or abs(bcg - r["0050年化"]) > 1e-9 or lab(cg, md, bcg, bmd) != r["標籤"]:
                bad5.append((r["臂"], r["段"], cg, r["年化"], md, r["回落"]))
        J[f"C5_{wn}"] = {"列": int((TB["世界"] == wn).sum()), "不同": len(bad5), "例": [str(b) for b in bad5[:3]]}
        log(f"[C5 {wn}] {J[f'C5_{wn}']}"); ok &= not bad5
        # C6
        dfm = TRD["M"]
        iv = np.stack([dfm["sid"].map(W["ix"]).to_numpy(), dfm["買進日"].map(dpos).to_numpy(),
                       np.array([dpos[x] if x else W["n0"] + 1 for x in dfm["賣出日"]])], 1).astype(np.int64)
        Wd = {"C": W["C"], "ix": W["ix"], "NP": W["n0"] + 1}
        c6 = []
        for sg, (x, y) in W["segp"].items():
            days = sorted({int(t) for t in iv[:, 1] if x <= t <= y})
            for t in [days[len(days) // 3], days[2 * len(days) // 3]]:
                m = (iv[:, 1] <= t) & (t < iv[:, 2])
                TRx = [{"r": {"sid": W["sids"][j]}, "tb": int(a_), "ts": int(b_) if b_ <= W["n0"] else None} for j, a_, b_ in iv[m]]
                ref = RD.eff_n(Wd, TRx, [t])[0]
                mine = M.effn_vec(W["C"], iv[m, 0], t)
                c6.append({"段": sg, "日": W["dates"][t], "N": ref[1], "eff_n(原)": ref[3], "矩陣化": mine[3], "相對差": abs(mine[3] / ref[3] - 1)})
                log(f"  [C6 {wn}] {c6[-1]}")
        J[f"C6_{wn}"] = c6; ok &= all(z["相對差"] < 1e-9 for z in c6)
        # C7
        RDF = pd.read_csv(os.path.join(OUT, f"random_{wn}.csv.gz"), float_precision="round_trip")
        evl = ev_light(W, wn)
        o_ = np.lexsort((W["srank"][evl["j"]], evl["e"]))
        M._G[wn] = {"tr": M.slot_tr(evl, False, o_), "n0": W["n0"], "CM": W["CM"], "Bc": Bc, "Bo": Bo, "segp": W["segp"]}
        diff = 0
        for i in (0, 137):
            r0 = M.rand_job((wn, i)); r1 = RDF[RDF["i"] == i].iloc[0]
            for k_, v_ in r0.items():
                if k_ in ("世界",):
                    continue
                if isinstance(v_, float) and abs(v_ - float(r1[k_])) > 1e-9 * max(1.0, abs(v_)):
                    diff += 1
                elif not isinstance(v_, float) and int(v_) != int(r1[k_]):
                    diff += 1
        c7 = {"列": int(len(RDF)), "有限": bool(np.isfinite(RDF.select_dtypes("number").to_numpy()).all()), "重跑第0、137次不同欄": diff}
        J[f"C7_{wn}"] = c7; log(f"[C7 {wn}] {c7}"); ok &= c7["列"] == M.NRAND and c7["有限"] and diff == 0
        del W, Z, TRD
    # C8
    p = subprocess.run([sys.executable, "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True)
    gs = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines()
    mod = [l for l in gs if not l.startswith("??")]
    new = [l for l in gs if l.startswith("??") and ("PTHpf" in l or "PEADpf" in l)]
    c8 = {"strategy_lock": p.stdout.strip().splitlines()[-1] if p.stdout.strip() else p.stderr.strip()[-200:], "rc": p.returncode,
          "既有追蹤檔有改動(工作樹)": mod, "本件新增": new}
    J["C8"] = c8; log(f"[C8] {c8}"); ok &= p.returncode == 0
    J["全部通過"] = bool(ok); J["耗時秒"] = round(time.time() - T0)
    json.dump(J, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] 全部通過 {ok}｜{J['耗時秒']}s")


if __name__ == "__main__":
    main()
