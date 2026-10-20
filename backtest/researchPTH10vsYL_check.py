# -*- coding: utf-8 -*-
"""52 週新高 10 檔版 對 營量 v1【獨立對帳】——回測線計算子代理。⛔ 只讀結果夾、不改任何檔（只寫 resultsPTH10vsYL/check.json、check.log）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTH10vsYL_check

C1 10 檔版權益：resultsPTHn N10_eq ＝ resultsPTHpf S10_eq（逐位元）；daily 檔「10檔版淨值」逐日 ＝ N10_eq 該日（逐位元）。
C2 營量 v1：researchYL_integrate.eng(W, YL, 0) 重跑（⛔ 不經 researchYLvsYF.book；自讀 audit 配對買賣）⇒ sha ＝ 整合件 seeds r0；
   daily 檔「營量淨值」逐日 ＝ equity 該日（逐位元）；yl_trades 檔逐列 ＝ 自配對結果。
C3 持股全日重算：只用 resultsPTHn trades_<世界>_N10（sid、買進日、賣出日）與自配對營量交易，日期字串比較 [買進日, 賣出日) ⇒
   每日 10 檔版持股數、營量持股數、同時持有、名單 ⇒ 對 daily 檔；抽樣日（主檔 J 閘）另列手算名單；抽樣日金額重疊 ＝ 自算市值 ÷ 淨值。
C4 進場：由兩份交易檔自算 ±0／5／20（營量日曆的交易日差）、買進日營量正持有、反向 ⇒ 對 entries 檔與 J。
C5 報酬：由 daily 檔自算 日報酬相關、月報酬相關（月底）、月差平均／CI、各半③（每年首日收盤調回、扣 0.585%）年化與回落、10 檔版／營量／0050 同窗 ⇒ 對 J。
C6 滾動 12 個月：由 daily 檔自算 ⇒ 對 rolling12.csv。
C7 策略鎖 25 支相符；git 工作樹：本件只新增檔。
"""
from __future__ import annotations

import gzip
import json
import math
import os
import subprocess
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchPTHpf as M                     # noqa: E402
from backtest import researchAddOn as RA                    # noqa: E402

OUT = "backtest/resultsPTH10vsYL"
COST = 0.00585


def rdcsv(p, **k):
    return pd.read_csv(p, float_precision="round_trip", keep_default_na=False, na_values=[""], **k)


def yrs_metrics(e):
    yrs = len(e) / 245
    cg = (e[-1] / e[0]) ** (1 / yrs) - 1
    pk = np.maximum.accumulate(e)
    return float(cg), float(((e - pk) / pk).min())


def close(a, b, tol=1e-9):
    if isinstance(a, str) or isinstance(b, str):
        return a == b
    a, b = float(a), float(b)
    return (np.isnan(a) and np.isnan(b)) or abs(a - b) <= tol * max(1.0, abs(b))


def main():
    log = RA.log_to(os.path.join(OUT, "check.log"))
    T0 = time.time(); ok = True
    J0 = json.load(open(os.path.join(OUT, "PTH10vsYL.json"), encoding="utf-8"))
    C = {"時間": M.now_tpe()}
    from backtest import researchYL_integrate as IG
    RL = rdcsv(os.path.join(OUT, "rolling12.csv"), encoding="utf-8-sig")
    for wn in ("主", "早年"):
        W = M.build_world(wn, log); dpos = {d: i for i, d in enumerate(W["dates"])}
        DL = rdcsv(os.path.join(OUT, f"daily_{wn}.csv.gz"), dtype={"10檔版名單": str, "營量名單": str})
        DL["10檔版名單"] = DL["10檔版名單"].fillna(""); DL["營量名單"] = DL["營量名單"].fillna("")
        EN = rdcsv(os.path.join(OUT, f"entries_{wn}.csv.gz"), dtype={"sid": str})
        YT = rdcsv(os.path.join(OUT, f"yl_trades_{wn}.csv.gz"), dtype={"sid": str, "買進日": str, "賣出日": str})
        YT["賣出日"] = YT["賣出日"].fillna("")
        # C1
        Zn = np.load(os.path.join("backtest/resultsPTHn", f"eq_{wn}.npz")); Zp = np.load(os.path.join(M.OUT, f"eq_{wn}.npz"))
        tP = DL["日"].map(dpos).to_numpy()
        c1 = {"N10_eq＝S10_eq": bool(np.array_equal(Zn["N10_eq"], Zp["S10_eq"])),
              "daily 10檔版淨值＝N10_eq": bool(np.array_equal(DL["10檔版淨值"].to_numpy(float), Zn["N10_eq"][tP])),
              "daily 0050＝Bc": bool(np.array_equal(DL["0050收盤"].to_numpy(float), Zn["Bc"][tP]))}
        C[f"C1_{wn}"] = c1; ok &= all(c1.values()); log(f"[C1 {wn}] {c1}")
        # C2
        Wy, _ = IG.main_world(log) if wn == "主" else IG.early_world(log, 4)
        o, au = IG.eng(Wy, IG.YL, 0)
        eq = np.asarray(o["equity"], float)
        import hashlib
        sha = hashlib.sha256(eq.tobytes()).hexdigest()[:16]
        ref = pd.read_csv("backtest/resultsYL_integrate/seeds.csv.gz", dtype={"eq_sha": str})
        rsha = ref[(ref["世界"] == wn) & (ref["格"] == IG.YL) & (ref["r"] == 0)].iloc[0]["eq_sha"]
        ydates = np.array([str(d.date()) for d in Wy["cal"]]); ypos = {d: i for i, d in enumerate(ydates)}
        tY = DL["日"].map(ypos).to_numpy()
        opn, mine = {}, []
        for a in sorted(au, key=lambda z: (z["t"], 0 if z["side"] == "sell" else 1)):
            if a["side"] == "buy":
                opn[a["sid"]] = (a["t"], a["amt"], a["px"])
            else:
                tb, amt, px = opn.pop(a["sid"])                 # 賣出 t ≥ 日曆長（資料尾）⇒ 視同持有到尾（＝ book 的 min(ts, n)）
                mine.append((a["sid"], ydates[tb], ydates[a["t"]] if a["t"] < len(ydates) else "", amt, px))
        for s, (tb, amt, px) in opn.items():
            mine.append((s, ydates[tb], "", amt, px))
        MY = pd.DataFrame(mine, columns=["sid", "買進日", "賣出日", "金額", "買價"]).sort_values(["sid", "買進日"]).reset_index(drop=True)
        YT2 = YT[["sid", "買進日", "賣出日", "金額", "買價"]].sort_values(["sid", "買進日"]).reset_index(drop=True)
        c2 = {"sha＝整合件 r0": sha == rsha, "daily 營量淨值＝equity": bool(np.array_equal(DL["營量淨值"].to_numpy(float), eq[tY])),
              "yl_trades＝自配對（列數）": [len(MY), len(YT2)],
              "yl_trades＝自配對（逐欄）": bool(len(MY) == len(YT2) and (MY["sid"] == YT2["sid"]).all() and (MY["買進日"] == YT2["買進日"]).all()
                                          and (MY["賣出日"] == YT2["賣出日"]).all() and np.array_equal(MY["金額"].to_numpy(float), YT2["金額"].to_numpy(float)))}
        C[f"C2_{wn}"] = c2; ok &= bool(c2["sha＝整合件 r0"] and c2["daily 營量淨值＝equity"] and c2["yl_trades＝自配對（逐欄）"]); log(f"[C2 {wn}] {c2}")
        # C3 全日持股
        PT = rdcsv(os.path.join("backtest/resultsPTHn", f"trades_{wn}_N10.csv.gz"), dtype={"sid": str, "買進日": str, "賣出日": str})
        PT["賣出日"] = PT["賣出日"].fillna("")
        pb, ps, psid = PT["買進日"].to_numpy(str), PT["賣出日"].to_numpy(str), PT["sid"].to_numpy(str)
        yb, ys_, ysid = MY["買進日"].to_numpy(str), MY["賣出日"].to_numpy(str), MY["sid"].to_numpy(str)
        bad3 = 0; ex3 = []
        for i, d in enumerate(DL["日"].to_numpy(str)):
            P = set(psid[(pb <= d) & ((ps == "") | (ps > d))]); Yh = set(ysid[(yb <= d) & ((ys_ == "") | (ys_ > d))])
            r = DL.iloc[i]
            if (len(P), len(Yh), len(P & Yh)) != (int(r["10檔版持股"]), int(r["營量持股"]), int(r["同時持有"])) or \
                    ";".join(sorted(P)) != r["10檔版名單"] or ";".join(sorted(Yh)) != r["營量名單"]:
                bad3 += 1
                if len(ex3) < 3:
                    ex3.append((d, len(P), len(Yh), len(P & Yh), r["10檔版持股"], r["營量持股"], r["同時持有"]))
        hand = {}
        CM = W["CM"]; ix = W["ix"]; eqP = Zn["N10_eq"]
        for d, s_ in J0["閘"][f"{wn}|抽樣日"].items():
            mP = (pb <= d) & ((ps == "") | (ps > d)); mY = (yb <= d) & ((ys_ == "") | (ys_ > d))
            wP = {psid[k]: PT["金額"].iat[k] * CM[ix[psid[k]], dpos[d]] / PT["市值基準價"].iat[k] / eqP[dpos[d]] for k in np.flatnonzero(mP)}
            wY = {}
            for k in np.flatnonzero(mY):
                s = ysid[k]
                wY[s] = wY.get(s, 0.0) + MY["金額"].iat[k] * float(Wy["closes"][s][ypos[d]]) / MY["買價"].iat[k] / eq[ypos[d]]
            amt = sum(min(wP[s], wY[s]) for s in set(wP) & set(wY))
            row = DL[DL["日"] == d].iloc[0]
            hand[d] = {"10檔版": sorted(wP), "營量同時持有": sorted(set(wP) & set(wY)), "營量檔數": len(wY), "主檔": s_,
                       "手算": f"{len(wP)}/{len(wY)}/{len(set(wP) & set(wY))}", "金額重疊手算": amt, "daily": float(row["金額重疊"]),
                       "相符": s_ == f"{len(wP)}/{len(wY)}/{len(set(wP) & set(wY))}" and abs(amt - float(row["金額重疊"])) <= 1e-12}
            ok &= hand[d]["相符"]
        C[f"C3_{wn}"] = {"全日數": len(DL), "不同日數": bad3, "例": [str(z) for z in ex3], "抽樣日手算": hand}
        ok &= bad3 == 0; log(f"[C3 {wn}] 不同 {bad3}／{len(DL)}｜抽樣 {[(d, v['手算'], v['相符']) for d, v in hand.items()]}")
        # C4 進場
        BYd = {}
        for s, d in zip(ysid, yb):
            BYd.setdefault(s, []).append(ypos[d])
        bad4 = 0
        for r in EN.itertuples(index=False):
            k = ypos[r.買進日]; v = np.array(BYd.get(r.sid, []))
            dm = int(np.min(np.abs(v - k))) if len(v) else -1
            held = bool(((yb <= r.買進日) & ((ys_ == "") | (ys_ > r.買進日)) & (ysid == r.sid)).any())
            want = (dm, len(v) > 0 and dm <= 0, len(v) > 0 and dm <= 5, len(v) > 0 and dm <= 20, held)
            got = (int(r[3]), bool(r[4]), bool(r[5]), bool(r[6]), bool(r[7]))
            bad4 += want != got
        c4 = {"列": len(EN), "不同": bad4}
        PBd = {}
        for s, d in zip(psid, pb):
            if d in ypos:
                PBd.setdefault(s, []).append(ypos[d])
        for sg in EN["段"].unique():
            e_ = EN[EN["段"] == sg]
            jj = J0["段"][f"{wn}|{sg}"]["進場"]
            ds = DL[DL["段"] == sg]["日"]; lo, hi = ds.iloc[0], ds.iloc[-1]
            yy = [(s, d) for s, d in zip(ysid, yb) if lo <= d <= hi]
            rv = np.mean([s in PBd and np.any(np.abs(np.array(PBd[s]) - ypos[d]) <= 20) for s, d in yy])
            mm = {"±20": (float(e_["營量±20"].mean()), jj["10檔版買進中營量±20也買"]), "±5": (float(e_["營量±5"].mean()), jj["10檔版買進中營量±5也買"]),
                  "持有": (float(e_["買進日營量正持有"].mean()), jj["10檔版買進日營量正持有"]), "反向±20": (float(rv), jj["營量買進中10檔版±20也買"])}
            c4[sg] = {k: [v[0], v[1], close(v[0], v[1], 1e-12)] for k, v in mm.items()}
            bad4 += sum(not v[2] for v in c4[sg].values())
        C[f"C4_{wn}"] = c4; ok &= bad4 == 0; log(f"[C4 {wn}] {c4}")
        # C5 報酬
        c5 = {}
        for sg in DL["段"].unique():
            g = DL[DL["段"] == sg].reset_index(drop=True); jr = J0["段"][f"{wn}|{sg}"]
            eP = g["10檔版淨值"].to_numpy(float); eY = g["營量淨值"].to_numpy(float); b = g["0050收盤"].to_numpy(float)
            dts = pd.to_datetime(g["日"])
            rP = np.diff(eP) / eP[:-1]; rY = np.diff(eY) / eY[:-1]
            ym = (dts.dt.year * 100 + dts.dt.month).to_numpy()
            idx = [0] + [k for k in range(1, len(g)) if k == len(g) - 1 or ym[k + 1] != ym[k]]
            mP = eP[idx][1:] / eP[idx][:-1] - 1; mY = eY[idx][1:] / eY[idx][:-1] - 1; dd = mP - mY
            n = len(dd); se = dd.std(ddof=1) / math.sqrt(n)
            A = B = 0.5; V = [1.0]; yr = dts.dt.year.to_numpy()
            for k in range(1, len(g)):
                A *= eP[k] / eP[k - 1]; B *= eY[k] / eY[k - 1]
                if yr[k] != yr[k - 1]:
                    T = A + B; T -= abs(A - T / 2) * COST; A = B = T / 2
                V.append(A + B)
            V = np.array(V)
            mine = {"日報酬相關": np.corrcoef(rP, rY)[0, 1], "月報酬相關": np.corrcoef(mP, mY)[0, 1], "月差平均": dd.mean(), "月差se": se,
                    "各半③": yrs_metrics(V), "10檔版": yrs_metrics(eP / eP[0]), "營量": yrs_metrics(eY / eY[0]), "0050": yrs_metrics(b / b[0])}
            rr = jr["報酬"]; pf = jr["績效(同窗)"]; md = rr["月報酬差(10檔版−營量)"]
            pairs = {"日報酬相關": (mine["日報酬相關"], rr["日報酬相關"]), "月報酬相關": (mine["月報酬相關"], rr["月報酬相關"]),
                     "月差平均": (mine["月差平均"], md["平均"]), "月差 sd": (dd.std(ddof=1), md["sd"]), "月數": (n, md["月數"]),
                     "各半③年化": (mine["各半③"][0], pf["各半③每年首日調回(扣0.585%)"]["年化"]), "各半③回落": (mine["各半③"][1], pf["各半③每年首日調回(扣0.585%)"]["回落"]),
                     "10檔版年化": (mine["10檔版"][0], pf["10檔版"]["年化"]), "10檔版回落": (mine["10檔版"][1], pf["10檔版"]["回落"]),
                     "營量年化": (mine["營量"][0], pf["營量v1"]["年化"]), "營量回落": (mine["營量"][1], pf["營量v1"]["回落"]),
                     "0050年化": (mine["0050"][0], pf["0050"]["年化"]), "0050回落": (mine["0050"][1], pf["0050"]["回落"]),
                     "各半③逐日 ＝ daily": (float(np.max(np.abs(V - g["各半③"].to_numpy(float)))), 0.0)}
            c5[sg] = {k: [float(v[0]), float(v[1]), close(v[0], v[1], 1e-10)] for k, v in pairs.items()}
            ok &= all(v[2] for v in c5[sg].values())
        C[f"C5_{wn}"] = c5; log(f"[C5 {wn}] {json.dumps(c5, ensure_ascii=False)}")
        # C6 滾動
        g = DL.reset_index(drop=True)
        eP = g["10檔版淨值"].to_numpy(float); eY = g["營量淨值"].to_numpy(float)
        dts = pd.to_datetime(g["日"]); ym = (dts.dt.year * 100 + dts.dt.month).to_numpy()
        idx = [0] + [k for k in range(1, len(g)) if k == len(g) - 1 or ym[k + 1] != ym[k]]
        mP = eP[idx][1:] / eP[idx][:-1] - 1; mY = eY[idx][1:] / eY[idx][:-1] - 1
        R0 = RL[RL["世界"] == wn].reset_index(drop=True)
        bad6 = 0
        for k in range(11, len(mP)):
            r = R0.iloc[k - 11]
            cr = np.corrcoef(mP[k - 11:k + 1], mY[k - 11:k + 1])[0, 1]; df = np.prod(1 + mP[k - 11:k + 1]) - np.prod(1 + mY[k - 11:k + 1])
            bad6 += not (abs(cr - r["月報酬相關12m"]) <= 1e-5 and abs(df - r["12m報酬差(10檔版−營量)"]) <= 1e-5 and r["窗尾月底"] == g["日"].iat[idx[k + 1]])
        C[f"C6_{wn}"] = {"窗數": len(mP) - 11, "檔列數": len(R0), "不同": bad6}
        ok &= bad6 == 0 and len(mP) - 11 == len(R0); log(f"[C6 {wn}] {C[f'C6_{wn}']}")
        del W, Wy, o, au, DL
    p = subprocess.run([sys.executable, "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True)
    gs = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines()
    C["C7"] = {"strategy_lock": p.stdout.strip().splitlines()[-1] if p.stdout.strip() else p.stderr.strip()[-200:], "rc": p.returncode,
               "既有追蹤檔有改動(工作樹，非本件)": [l for l in gs if not l.startswith("??")],
               "本件新增": [l for l in gs if l.startswith("??") and "PTH10vsYL" in l]}
    ok &= p.returncode == 0; log(f"[C7] {C['C7']}")
    C["全部通過"] = bool(ok); C["耗時秒"] = round(time.time() - T0)
    json.dump(C, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] 全部通過 {ok}｜{C['耗時秒']}s")


if __name__ == "__main__":
    main()
