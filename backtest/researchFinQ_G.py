# -*- coding: utf-8 -*-
"""財報品質 seq1 第 3 格【Q-G 毛利對資產高（Novy-Marx 2013）】頻率表對帳＋事件層正式跑（台股策略線 登錄 sha fd142bbf73922770，2026-10-20 23:33；
裁定 seq407 第二題、seq408 發號、seq411 §四（一律 fs_xbrl、⛔ fs_hist）、seq412 §四（Q-G 掛起、補後 N_前段 ＋1）、seq418（Q-G 解除掛起）；
資料庫 1829：fs_xbrl 新三欄 cost_of_sales_ytd、gross_profit_ytd、operating_income_ytd）——回測線計算子代理。
⛔ 不 commit、不改既有程式與結果夾（resultsFinQ/ 既有檔、freq/ 不動；Q-A、Q-I 不重跑）；researchFinQ_freq（F1～F10）、researchFinQ（F11～F19；hm_stats）、
   researchIndMom（exright 版、出場、路徑、統計）、researchQual（PREREG品質 舊格，只為重疊）⛔ 只 import。

    乾跑（頻率表對帳，⛔ 不算任何進場後報酬）：cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchFinQ_G --dry
    正式跑：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchFinQ_G
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchFinQ_G_check
輸出 backtest/resultsFinQ/G/freq/（乾跑：freq.json、freq.csv、by_year.csv、picks.csv.gz、overlap.csv、old_q2.csv、run.log）
     backtest/resultsFinQ/G/（正式：FinQ_G.json、FinQ_G_表.csv、by_year.csv、events.csv.gz、fake_reps.csv、recon_dry.csv、先驗.csv、run.log）

═══ 讀法（G 標；F1～F19 原樣沿用，以下為 Q-G 新增；⛔ 在讀任何 Q-G 報酬之前寫死於 2026-10-21（台北）；★＝執行者定，〔 〕內為另一讀法）═══
 G1 資料快照 ＝ 新 origin/main（git fetch 後；sha 寫進 json；~/b2fwork/main_<sha12>，唯讀）：fs_xbrl（含新三欄）、filing_dates、stocks.csv、產業別 全部取自新快照。
    價格面板、exright 表 ＝ Q-A／Q-I 正式跑同一份（~/b2fwork/panel_<世界>.pkl、exrx_<世界>_b5532121f8d8.pkl）。
 G2 Q-G ＝（revenue_ytd − cost_of_sales_ytd）÷ total_assets（FY Y−1 年報 Q4 列；Q4 YTD ＝ 全年，不必相減）⇒ 最高十分位（F5 同切法、同值併入）。
    ★ 照登錄字面「營收 − 營業成本」〔另一讀法：gross_profit_ytd（營業毛利淨額 ＝ 毛利 − 未實現 ＋ 已實現銷貨損益，資料庫 1829）÷ 總資產〕；
    淨額版只描述：報兩版入選重疊。cost_of_sales_ytd 或 revenue_ytd 空白、TA ≤ 0 ⇒ 該股 Q-G 算不出（計數；⛔ 不補 0）。
 G3 母體 ＝ F4 原樣（四碼普通股含已下市 ∧ 500 張閘在 t ∧ 非金融保險（產業別 ∧ XBRL 範本）∧ FY(Y−1) 年報 t 前已上傳），在新快照上重算。
    Q-G 只用 FY(Y−1) ⇒ 排序年 2014 也算得出（Q-A／Q-I 需 FY2012 而算不出）；★ 2014 排序年在早年世界、12 個月持有跨 2014→2015 接縫 ⇒ 正式跑不收（筆數照報）。
 G4 頻率表對帳（乾跑）：每排序年 母體、Q-G 有值（可算比例）、缺值原因、入選、進場剔除、已下市；段 n_eff（持有月分群、排序年分群）；
    與 Q-A、Q-I 入選重疊（新快照重算；另對已提交 resultsFinQ/freq/picks.csv.gz，並報新舊快照 Q-A／Q-I 名單差）；
    與 PREREG品質 舊格 Q2（TTM 營業利益 ÷ 期末總資產，researchQual、F9 同法：本件母體內前十分位、前 20）重疊與 Spearman；淨額版重疊。
    ⭐ 正式跑先用同一支程式重建入選與進場狀態，與乾跑 picks.csv.gz 逐列比，不同 ⇒ 中止、⛔ 不算報酬。
 G5 報酬、對照、持有月分群、排序年分群、假訊號臂、seq322 ＝ F12～F16 原樣（格標 Q-G ＝ 3；Bonferroni 族 N ＝ 3 照原定，z ＝ 2.394）。
 G6 先驗（登錄 §六）：① 三格中至少一格兩段② ⇒ 用已交件 Q-A、Q-I（皆否）＋本格；② ★「Q-G 與 PREREG品質 Q2 入選重疊」＝ 探索＋確認排序年（2017～2025）合計
    Q-G 入選中屬 Q2 前十分位的比例 ≥ 50% ⇒ 中；≥ 80% ⇒ 照寫「與 PREREG品質 Q2 近乎同一件」；③ 照前次（不中）。
 G7 結果句必附：「年頻，每段只有 4～5 個排序年」「原文為美股、多空組合」「單筆層通過 ≠ 組合會贏 0050」＋ Q-G 與 PREREG品質 Q2 的重疊；
    財報母體含下市 ⇒ 不附存活者句；seq373 不適用照寫。
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
import os
import subprocess
import sys
import time
import zlib
from collections import Counter

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchFinQ_freq as FQ                # noqa: E402
from backtest import researchFinQ as FX                     # noqa: E402
from backtest import researchIndMom_freq as IM              # noqa: E402
from backtest import researchIndMom as IMX                  # noqa: E402
from backtest import researchPTH_freq as PF                 # noqa: E402
from backtest import research11 as R                        # noqa: E402

REG_SHA = FQ.REG_SHA
OUT = "backtest/resultsFinQ/G"
DRY = os.path.join(OUT, "freq")
OLD_PICKS = os.path.join(FQ.OUT, "picks.csv.gz")
OLD_TAB = os.path.join(FX.OUT, "FinQ_表.csv")
CTAG = 3
NCTRL, NFAKE = FX.NCTRL, FX.NFAKE
HS = FX.HS
SEGY = FX.SEGY
COST = FX.COST
LOG = IM.LOG
log = IM.log
pct = IMX.pct
SENT = FX.SENT


def load_fs_g(DATA):
    fs = sorted(glob.glob(os.path.join(DATA, "meta", "fs_xbrl", "fs_xbrl_*.csv")))
    cols = ["period", "stock_id", "industry_template", "report", "period_end", "total_assets", "revenue_ytd", "net_income_ytd",
            "operating_cash_flow_ytd", "cost_of_sales_ytd", "gross_profit_ytd"]
    F = pd.concat([pd.read_csv(f, dtype={"stock_id": str, "period": str}, usecols=cols) for f in fs], ignore_index=True)
    F = F[F["period"].str.endswith("Q4")].copy()
    F["fy"] = F["period"].str[:4].astype(int)
    F["_r"] = (F["report"] != "cr").astype(int)
    F = F.sort_values(["stock_id", "fy", "_r"]).drop_duplicates(["stock_id", "fy"], keep="first")
    return {(s, y): r for s, y, r in zip(F["stock_id"], F["fy"], F.to_dict("records"))}


def jac(a, b):
    return round(len(a & b) / len(a | b), 4) if (a | b) else None


def build(DATA, Zs, PIT, alive, K, FD):
    """F4 母體 ＋ 三格值（新快照）＋ Q-G 淨額版 ⇒ YD。"""
    YD = {}
    for Y in FQ.YEARS:
        wn = "早年" if Y <= 2014 else "主"
        Zo = Zs[wn]["o"]; Zx = Zs[wn]["x"]; cal = Zo["cal"]
        t, e = FQ.sort_points(Zo, Y)
        if t is None:
            continue
        ts_lim = cal[t].normalize() + pd.Timedelta(days=1)
        univ = {}; vals = {c: {} for c in ("Q-A", "Q-I", "Q-G", "Q-G淨額")}; miss = Counter(); rej = Counter()
        for i in np.flatnonzero(Zo["G"][:, t] & np.isfinite(Zo["C"][:, t])):
            s = Zo["sids"][i]
            ind, _ = PIT.at(s, cal[t])
            if ind == "金融保險":
                rej["金融保險(產業別)"] += 1; continue
            r1 = K.get((s, Y - 1))
            if r1 is not None and r1["industry_template"] in FQ.FIN_TPL:
                rej["金融保險(XBRL範本)"] += 1; continue
            if r1 is None:
                rej["fs_xbrl無FY(Y−1)年報"] += 1; continue
            f1 = FD.get((s, Y - 1))
            if f1 is None:
                rej["無上傳時戳"] += 1; continue
            if not (f1[0] < ts_lim):
                rej["t時年報尚未上傳"] += 1; continue
            univ[s] = int(i)
            r2 = K.get((s, Y - 2)); f2 = FD.get((s, Y - 2))
            ta1 = r1["total_assets"]; ta2 = r2["total_assets"] if (r2 is not None and f2 is not None and f2[0] < ts_lim) else np.nan
            ni, ocf = r1["net_income_ytd"], r1["operating_cash_flow_ytd"]
            if np.isfinite(ta1) and np.isfinite(ta2) and ta1 > 0 and ta2 > 0:
                vals["Q-I"][s] = ta1 / ta2 - 1.0
                if np.isfinite(ni) and np.isfinite(ocf):
                    vals["Q-A"][s] = (ni - ocf) / ((ta1 + ta2) / 2.0)
            rev, cos, gp = r1["revenue_ytd"], r1["cost_of_sales_ytd"], r1["gross_profit_ytd"]
            if not (np.isfinite(ta1) and ta1 > 0):
                miss["TA缺或≤0"] += 1
            elif not np.isfinite(cos):
                miss["營業成本空白"] += 1
            elif not np.isfinite(rev):
                miss["營收空白"] += 1
            else:
                vals["Q-G"][s] = (rev - cos) / ta1
            if np.isfinite(ta1) and ta1 > 0 and np.isfinite(gp):
                vals["Q-G淨額"][s] = gp / ta1
        sel = {"Q-A": FQ.dec_select(vals["Q-A"], low=True)[0], "Q-I": FQ.dec_select(vals["Q-I"], low=True)[0],
               "Q-G": FQ.dec_select(vals["Q-G"], low=False)[0], "Q-G淨額": FQ.dec_select(vals["Q-G淨額"], low=False)[0]}
        sto = {s: IM.entry_flag(Zo, univ[s], t, e) for s in sel["Q-G"]}
        stx = {s: IM.entry_flag(Zx, i, t, e) for s, i in univ.items()}
        YD[Y] = {"wn": wn, "t": t, "e": e, "univ": univ, "vals": vals, "sel": sel, "sto": sto, "stx": stx, "miss": miss, "rej": rej}
    return YD


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    os.makedirs(DRY if a.dry else OUT, exist_ok=True)
    reg = IM.reg_check(REG_SHA)
    log(f"[登錄] {reg}（sha {REG_SHA} 已驗）｜{'乾跑（⛔ 不算報酬）' if a.dry else '正式跑'}")
    if a.dry:
        subprocess.run(["git", "fetch", "-q", "origin", "main"], check=True)
        sha, DATA = IM.ensure_main()
    else:
        sha = json.load(open(os.path.join(DRY, "freq.json"), encoding="utf-8"))["資料"]["origin/main"]
        DATA = IMX.pinned_data(sha)
    log(f"[資料] origin/main {sha[:12]} ⇒ {DATA}")
    hdr = pd.read_csv(sorted(glob.glob(os.path.join(DATA, "meta", "fs_xbrl", "fs_xbrl_*.csv")))[0], nrows=0).columns.tolist()
    if not {"cost_of_sales_ytd", "gross_profit_ytd"} <= set(hdr):
        raise SystemExit("⛔ fs_xbrl 沒有新欄 cost_of_sales_ytd／gross_profit_ytd")
    K = load_fs_g(DATA); FD = FQ.load_filing(DATA); alive, mx_ls = FQ.delisted_set(DATA); PIT = IM.load_pit(DATA)
    Zs = {}
    for wn in ("早年", "主"):
        Zo = IMX.aux2(IM.panel_aux(IM.build_panel(wn, a.procs)))
        Zs[wn] = {"o": Zo, "x": IMX.make_x(Zo, IMX.build_exr(Zo, a.procs))}
    YD = build(DATA, Zs, PIT, alive, K, FD)
    log(f"[母體] {len(YD)} 個排序年｜{time.time() - t0:.0f}s")
    if a.dry:
        dry(sha, DATA, YD, Zs, alive, K, mx_ls, t0)
    else:
        formal(sha, YD, Zs, alive, t0)


# ═════════════ 乾跑：頻率表對帳 ═════════════
def dry(sha, DATA, YD, Zs, alive, K, mx_ls, t0):
    from backtest import researchQual as RQ
    RQ.FD = FQ.OLDQ_FD
    QOLD = RQ.load_fin(log)
    OLDPOS = {wn: RQ.avail_pos(QOLD, Zs[wn]["o"]["cal"])[0] for wn in Zs}
    PK = pd.read_csv(OLD_PICKS, dtype={"sid": str})
    BY = []; PICKS = []; OV = []; OQ = []
    for Y, yd in YD.items():
        univ, vals, sel = yd["univ"], yd["vals"], yd["sel"]
        G = sel["Q-G"]
        fl = Counter(yd["sto"].values()); flx = Counter(yd["stx"][s] for s in G)
        row = {"排序年": Y, "世界": yd["wn"], "排序日t": str(Zs[yd["wn"]]["o"]["cal"][yd["t"]].date()), "進場日e": str(Zs[yd["wn"]]["o"]["cal"][yd["e"]].date()),
               **{f"剔除_{k}": v for k, v in yd["rej"].items()}, "母體": len(univ), "母體已下市": sum(1 for s in univ if s not in alive),
               "Q-G有值": len(vals["Q-G"]), "Q-G可算比例": round(len(vals["Q-G"]) / len(univ), 4) if univ else None,
               "Q-G缺值原因": json.dumps(dict(yd["miss"]), ensure_ascii=False), "Q-G入選": len(G), "Q-G入選已下市": sum(1 for s in G if s not in alive),
               **{f"Q-G進場_{k}(舊口徑)": v for k, v in fl.items()}, **{f"Q-G進場_{k}(exright)": v for k, v in flx.items()},
               "Q-G事件(exright保留)": flx.get("保留", 0), "Q-G淨額有值": len(vals["Q-G淨額"]), "Q-G淨額入選": len(sel["Q-G淨額"]),
               "Q-A入選(新快照)": len(sel["Q-A"]), "Q-I入選(新快照)": len(sel["Q-I"])}
        BY.append(row)
        # 重疊（新快照）
        ov = {"排序年": Y, "Q-G入選": len(G)}
        for c in ("Q-A", "Q-I", "Q-G淨額"):
            ov[f"∩{c}"] = len(G & sel[c]); ov[f"比例_Q-G中屬{c}"] = round(len(G & sel[c]) / len(G), 4) if G else None; ov[f"Jaccard_{c}"] = jac(G, sel[c])
        # 對已提交 picks（舊快照）
        old = PK[PK["排序年"] == Y]
        for c in ("Q-A", "Q-I"):
            os_ = set(old.loc[old[f"{c}入選"].astype(bool), "sid"])
            ov[f"∩{c}(已提交)"] = len(G & os_)
            ov[f"{c}新舊快照名單差"] = len(os_ ^ sel[c])
        ov["母體新舊快照差"] = len(set(old["sid"]) ^ set(univ))
        sp = FQ.spearman(vals["Q-G"], vals["Q-G淨額"])
        ov["Spearman(Q-G,淨額)"] = round(sp[0], 4) if np.isfinite(sp[0]) else None
        OV.append(ov)
        # PREREG品質 舊格
        qa = RQ.q_at(QOLD, OLDPOS[yd["wn"]], yd["e"])
        for k in ("Q1", "Q2", "Q3", "Q4"):
            o = {s: v for s, v in qa[k].items() if s in univ}
            od = FQ.dec_select(o, low=False)[0]; o20 = FQ.topn(o, 20)
            sp, nsp = FQ.spearman(vals["Q-G"], o)
            OQ.append({"排序年": Y, "舊格": f"{k} {RQ.QN[k]}", "舊格母體內有值": len(o), "舊前十分位": len(od), "Q-G入選": len(G),
                       "Q-G∩舊前十分位": len(G & od), "比例_Q-G中屬舊前十分位": round(len(G & od) / len(G), 4) if G else None,
                       "舊前20中屬Q-G": len(o20 & G), "Spearman(Q-G,舊)": round(sp, 4) if np.isfinite(sp) else None, "共同有值": nsp})
        for s, i in univ.items():
            PICKS.append({"排序年": Y, "sid": s, "已下市": s not in alive, "Q-G": vals["Q-G"].get(s, np.nan), "Q-G淨額": vals["Q-G淨額"].get(s, np.nan),
                          "Q-G入選": s in G, "Q-G_st": yd["sto"].get(s, ""), "Q-G_stx": yd["stx"][s] if s in G else ""})
        log(f"[{Y}] 母體 {len(univ)}｜Q-G 有值 {len(vals['Q-G'])}（{row['Q-G可算比例']}）入選 {len(G)} 事件 {row['Q-G事件(exright保留)']}｜∩Q-A {ov['∩Q-A']} ∩Q-I {ov['∩Q-I']}")
    # 段
    FREQ = []; J = {"性質": "財報品質 Q-G 頻率表對帳（乾跑；⛔ 未讀、未算任何進場後報酬）", "登錄": f"台股策略線 seq1 sha {REG_SHA}",
                    "資料": {"origin/main": sha, "stocks.csv 最晚 last_seen": mx_ls, "exright": IMX.EXR_SHA}, "段": {}}
    oq = pd.DataFrame(OQ)
    for sg, ys in list(SEGY.items()) + [("探索＋確認(先驗②)", list(range(2017, 2026)))]:
        ys = [y for y in ys if y in YD]
        ev = [(y, s) for y in ys for s in YD[y]["sel"]["Q-G"] if YD[y]["stx"][s] == "保留"]
        yrs = sorted({y for y, _ in ev}); nev = len(ev)
        hm = {(y + (m - 1) // 12, (m - 1) % 12 + 1) for y in yrs for m in range(5, 17)}
        q2 = oq[(oq["排序年"].isin(ys)) & (oq["舊格"].str.startswith("Q2"))]
        sj = {"段": sg, "排序年": f"{ys[0]}～{ys[-1]}" if ys else "", "事件數(exright保留)": nev, "排序年數": len(yrs), "相異持有月": len(hm),
              "n_eff_持有月分群": min(nev, len(hm)), "n_eff_排序年分群": min(nev, len(yrs)),
              "Q-G∩Q2前十分位合計": int(q2["Q-G∩舊前十分位"].sum()), "Q-G入選合計": int(q2["Q-G入選"].sum()),
              "比例_Q-G中屬Q2前十分位": round(q2["Q-G∩舊前十分位"].sum() / max(1, q2["Q-G入選"].sum()), 4),
              "Spearman(Q-G,Q2)年中位": float(q2["Spearman(Q-G,舊)"].median()) if len(q2) else None}
        sub = pd.DataFrame(OV)[lambda d: d["排序年"].isin(ys)]
        for c in ("Q-A", "Q-I", "Q-G淨額"):
            sj[f"比例_Q-G中屬{c}(合計)"] = round(sub[f"∩{c}"].sum() / max(1, sub["Q-G入選"].sum()), 4)
        FREQ.append(sj); J["段"][sg] = sj
        log(f"[段 {sg}] 事件 {nev}｜n_eff 持有月 {sj['n_eff_持有月分群']}／排序年 {sj['n_eff_排序年分群']}｜Q-G 中屬 Q2 前十分位 {sj['比例_Q-G中屬Q2前十分位']}")
    J["讀法"] = __doc__.split("═══ 讀法")[1]; J["時間"] = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")
    pd.DataFrame(FREQ).to_csv(os.path.join(DRY, "freq.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(BY).to_csv(os.path.join(DRY, "by_year.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(OV).to_csv(os.path.join(DRY, "overlap.csv"), index=False, encoding="utf-8-sig")
    oq.to_csv(os.path.join(DRY, "old_q2.csv"), index=False, encoding="utf-8-sig")
    with gzip.open(os.path.join(DRY, "picks.csv.gz"), "wt", encoding="utf-8") as fh:
        pd.DataFrame(PICKS).to_csv(fh, index=False)
    json.dump(J, open(os.path.join(DRY, "freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] {time.time() - t0:.0f}s")
    open(os.path.join(DRY, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


# ═════════════ 正式跑 ═════════════
def formal(sha, YD, Zs, alive, t0):
    # G4 對乾跑 picks 逐列
    PK = pd.read_csv(os.path.join(DRY, "picks.csv.gz"), dtype={"sid": str}, keep_default_na=False)
    RECON = []
    for Y, yd in YD.items():
        fm = PK[PK["排序年"] == Y].reset_index(drop=True)
        mine = [(s, s in yd["sel"]["Q-G"], yd["sto"].get(s, ""), yd["stx"][s] if s in yd["sel"]["Q-G"] else "", yd["vals"]["Q-G"].get(s, np.nan)) for s in yd["univ"]]
        bad = len(fm) != len(mine)
        if not bad:
            bad = not ((fm["sid"].tolist() == [m[0] for m in mine]) and (fm["Q-G入選"].astype(str).tolist() == [str(m[1]) for m in mine])
                       and (fm["Q-G_st"].astype(str).tolist() == [m[2] for m in mine]) and (fm["Q-G_stx"].astype(str).tolist() == [m[3] for m in mine]))
            fv = pd.to_numeric(fm["Q-G"], errors="coerce").to_numpy(float); mv = np.array([m[4] for m in mine], float)
            bad = bad or not ((np.isnan(fv) & np.isnan(mv)) | np.isclose(fv, mv, rtol=1e-12, atol=0)).all()
        RECON.append({"排序年": Y, "乾跑列": len(fm), "本檔列": len(mine), "相同": not bad})
        if bad:
            raise SystemExit(f"⛔ [{Y}] 正式跑重建 ≠ 乾跑 picks ⇒ 中止、不算報酬")
    log(f"[G4] 乾跑 picks 逐列重建：{len(RECON)} 年全同｜{time.time() - t0:.0f}s")
    mcal = Zs["主"]["o"]["cal"]; MEm, MKm = PF.month_ends(mcal)
    me_of = {(int(y), int(m)): int(p) for p, (y, m) in zip(MEm, MKm)}
    Zx = Zs["主"]["x"]
    POOL = {}
    for Y, yd in YD.items():
        if yd["wn"] != "主":
            continue
        t, e = yd["t"], yd["e"]
        for H in HS:
            mons = [((Y * 12 + 4 + k) // 12, (Y * 12 + 4 + k) % 12 + 1) for k in range(H)]
            if mons[-1] not in me_of:
                continue
            taus = np.array([me_of[m] for m in mons]); x = int(taus[-1]); mk = np.array([y * 12 + m - 1 for y, m in mons])
            pool_s = [s for s in yd["univ"] if yd["stx"][s] == "保留"]
            ii = np.array([yd["univ"][s] for s in pool_s], np.int64)
            ex, Rv, typ = IMX.exits_vec(Zx, ii, e, x)
            V = IMX.path_val(Zx, ii, e, ex, taus)
            okp = np.isfinite(Rv)
            P = {"sids": [s for s, o in zip(pool_s, okp) if o], "R": Rv[okp], "V": V[okp], "typ": typ[okp], "mk": mk}
            P["ix"] = {s: k for k, s in enumerate(P["sids"])}
            POOL[(Y, H)] = P

    def x_of(Y, H, sids, tag):
        P = POOL[(Y, H)]; out = []
        for s in sids:
            k = P["ix"].get(s)
            if k is None:
                out.append(None); continue
            cand = np.array([q for q in range(len(P["sids"])) if q != k])
            rng = np.random.default_rng([20261021, tag, Y, H, zlib.crc32(s.encode())])
            pick = cand if len(cand) <= NCTRL else rng.choice(cand, NCTRL, replace=False)
            Vc = P["V"][pick].mean(0); Ve = P["V"][k]
            d = np.diff(np.r_[1.0, Ve]) - np.diff(np.r_[1.0, Vc])
            out.append((d, float(P["R"][k]), float(P["R"][pick].mean()), int(P["typ"][k]), len(pick), "|".join(P["sids"][q] for q in pick)))
        return out

    EVROWS = []; DM = {}; SEAMN = 0
    for Y, yd in YD.items():
        ev = sorted(s for s in yd["sel"]["Q-G"] if yd["stx"][s] == "保留")
        if yd["wn"] != "主":
            SEAMN += len(ev); continue
        for H in HS:
            if (Y, H) not in POOL:
                continue
            rows_d = []
            for s, r in zip(ev, x_of(Y, H, ev, CTAG)):
                if r is None:
                    EVROWS.append({"格": "Q-G", "排序年": Y, "H": H, "sid": s, "R可算": False}); continue
                d, Re, Rc, ty, nc, cl = r
                EVROWS.append({"格": "Q-G", "排序年": Y, "H": H, "sid": s, "R可算": True, "R": Re, "對照R": Rc, "X": Re - Rc, "淨R": Re - COST,
                               "出場": IMX.TYPN[ty], "對照檔數": nc, "對照": cl, "池大小": len(POOL[(Y, H)]["sids"]), "已下市": s not in alive,
                               "Σd−X": float(d.sum() - (Re - Rc))})
                rows_d.append(d)
            if rows_d:
                DM[(H, Y)] = np.vstack(rows_d)
    EV = pd.DataFrame(EVROWS)
    log(f"[報酬] 事件列 {len(EV)}｜2014 接縫不收 {SEAMN}｜Σd−X 最大誤差 {EV['Σd−X'].abs().max():.2e}｜{time.time() - t0:.0f}s")

    def seg_stats(H, ys, src):
        mats = [(Y, src[(H, Y)]) for Y in ys if (H, Y) in src]
        if not mats:
            return None
        Dm = np.vstack([m for _, m in mats]); mk = np.vstack([np.broadcast_to(POOL[(Y, H)]["mk"], m.shape) for Y, m in mats])
        st = FX.hm_stats(Dm, H, mk)
        Xv = Dm.sum(1); yk = np.concatenate([[Y] * len(m) for Y, m in mats]); cy = R.cl_stats(Xv, yk)
        ney = int(min(len(Xv), cy["months"]))
        st.update({"年分群_n_eff": ney, "年分群_lo": cy["lo"], "年分群_hi": cy["hi"], "年分群_結果": IMX.res_of(cy["lo"], cy["hi"], ney),
                   "年分群_結果(忽略n_eff)": "結果①" if cy["lo"] <= 0 <= cy["hi"] else ("結果②" if cy["lo"] > 0 else "結果③"),
                   "排序年": f"{mats[0][0]}～{mats[-1][0]}", "每年X̄": json.dumps({int(Y): round(float(m.sum(1).mean()), 4) for Y, m in mats})})
        return st

    FAKE = []; FDM = {}
    for r in range(NFAKE):
        for Y in YD:
            if (Y, 12) not in POOL:
                continue
            nev = int(((EV["排序年"] == Y) & (EV["H"] == 12) & EV["R可算"]).sum())
            P = POOL[(Y, 12)]
            rng = np.random.default_rng([20261021 + r, CTAG, Y])
            ss = list(rng.choice(P["sids"], size=min(nev, len(P["sids"])), replace=False)) if nev else []
            res = x_of(Y, 12, [str(s) for s in ss], 100 + r)
            if res:
                FDM[(r, Y)] = np.vstack([q[0] for q in res if q is not None])
        for sg in ("探索", "確認"):
            st = seg_stats(12, SEGY[sg], {(12, Y): FDM[(r, Y)] for Y in SEGY[sg] if (r, Y) in FDM})
            FAKE.append({"格": "Q-G", "段": sg, "r": r, "n": st["n"], "n_eff": st["n_eff"], "X̄": st["X̄"], "lo": st["lo"], "hi": st["hi"], "結果": st["結果"]})
    FK = pd.DataFrame(FAKE)
    log(f"[假訊號] 完｜{time.time() - t0:.0f}s")
    TAB = []
    for H in HS:
        for sg, ys in SEGY.items():
            st = seg_stats(H, ys, DM)
            if st is None:
                continue
            cell = "判定" if (H == 12 and sg != "早年") else "描述"
            row = {"格": "Q-G", "H": H, "段": sg, "身分": cell, **{k: st.get(k) for k in (
                "排序年", "n", "群數(持有月)", "n_eff", "樣本", "X̄", "中位", "X勝率", "lo", "hi", "結果", "t", "結果_Bonf3", "結果_Bonf2", "bonf_lo",
                "年分群_n_eff", "年分群_lo", "年分群_hi", "年分群_結果", "年分群_結果(忽略n_eff)", "逐持有月平均增量之中位", "逐月中位與平均同號", "每年X̄")}}
            sub = EV[(EV["H"] == H) & EV["排序年"].isin(ys) & EV["R可算"]]
            row["R̄"] = float(sub["R"].mean()); row["對照R̄"] = float(sub["對照R"].mean()); row["入選中已下市"] = int(sub["已下市"].sum())
            row["出場占比"] = json.dumps({k: round(v / len(sub), 4) for k, v in Counter(sub["出場"]).items()}, ensure_ascii=False)
            row["年分群與持有月分群結論不同"] = bool(st["年分群_結果(忽略n_eff)"] != st["結果"])
            if cell == "判定":
                fk = FK[FK["段"] == sg]; xf = int((fk["結果"] == "結果②").sum())
                row["假訊號x(／30)"] = xf; row["假訊號X̄中位"] = float(fk["X̄"].median()); row["假訊號X̄p95"] = float(fk["X̄"].quantile(0.95))
                c322 = {"結果②": st["結果"] == "結果②", "Bonferroni下界>0(N=3)": bool(st["bonf_lo"] > 0), "假訊號x≤1": xf <= 1,
                        "X̄−0.585%>0": bool(st["X̄"] - COST > 0), "逐月中位與平均同號": bool(st["逐月中位與平均同號"])}
                row["過seq322"] = all(c322.values()); row["seq322各條"] = json.dumps(c322, ensure_ascii=False)
            TAB.append(row)
    TB = pd.DataFrame(TAB)
    BY = EV[EV["R可算"]].groupby(["H", "排序年"]).agg(n=("X", "size"), X̄=("X", "mean"), R̄=("R", "mean"), 對照R̄=("對照R", "mean"), 已下市=("已下市", "sum")).reset_index()
    jd = TB[TB["身分"] == "判定"].set_index("段")
    fj = json.load(open(os.path.join(DRY, "freq.json"), encoding="utf-8"))
    q2 = fj["段"]["探索＋確認(先驗②)"]["比例_Q-G中屬Q2前十分位"]

    def word(r):
        return {"結果②": "多", "結果③": "少", "結果①": "分不出"}.get(r, "依構造不可判定")
    sent = (f"每年 4 月底挑毛利對資產最高的一成、抱一年：探索段（{jd.loc['探索', '排序年']}）比隨便買{word(jd.loc['探索', '結果'])} {pct(jd.loc['探索', 'X̄'])}"
            f"（{jd.loc['探索', '樣本']}）、確認段（{jd.loc['確認', '排序年']}）{word(jd.loc['確認', '結果'])} {pct(jd.loc['確認', 'X̄'])}（{jd.loc['確認', '樣本']}）"
            + ("；⚠ 排序年分群結論不同" if jd["年分群與持有月分群結論不同"].any() else "")
            + f"；與 PREREG品質 Q2 入選重疊 {q2 * 100:.1f}%" + ("（≥ 80%：與 PREREG品質 Q2 近乎同一件）" if q2 >= 0.8 else ""))
    old = pd.read_csv(OLD_TAB)
    both2 = {c: bool((old[(old["格"] == c) & (old["身分"] == "判定")]["結果"] == "結果②").all()) for c in ("Q-A", "Q-I")}
    both2["Q-G"] = bool((jd["結果"] == "結果②").all())
    PRIOR = [{"先驗": "① 三格中至少一格兩段②（約三成）", "中": any(both2.values()), "實際": "｜".join(f"{c} 兩段②={v}" for c, v in both2.items())},
             {"先驗": "② Q-G 與 PREREG品質 Q2 入選重疊 ≥ 50%（約六成）", "中": bool(q2 >= 0.5), "實際": f"2017～2025 合計 Q-G 入選中屬 Q2 前十分位 {q2 * 100:.1f}%"},
             {"先驗": "③ Q-A 因缺現金流量表或年份不足而不可判（約四成）", "中": False, "實際": "前次已判：Q-A 可判 ⇒ 不中"}]
    J = {"性質": "財報品質 seq1 第 3 格 Q-G 事件層正式跑", "登錄": f"台股策略線 seq1 sha {REG_SHA}", "裁定": "seq412 §四、seq418（Q-G 解除掛起，N_前段 ＋1）",
         "資料": {"origin/main": sha, "exright": IMX.EXR_SHA}, "判定": TB[TB["身分"] == "判定"].to_dict("records"), "結果句": sent, "必附": SENT,
         "Q2重疊": q2, "先驗": PRIOR, "先驗中": sum(1 for p in PRIOR if p["中"]), "乾跑重建": RECON, "2014接縫不收": SEAMN,
         "seq373": "同根兩出場價取較低：每筆只有一種出場價 ⇒ 不適用，照寫", "讀法": __doc__.split("═══ 讀法")[1],
         "時間": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")}
    TB.to_csv(os.path.join(OUT, "FinQ_G_表.csv"), index=False, encoding="utf-8-sig")
    BY.to_csv(os.path.join(OUT, "by_year.csv"), index=False, encoding="utf-8-sig")
    with gzip.open(os.path.join(OUT, "events.csv.gz"), "wt", encoding="utf-8") as fh:
        EV.to_csv(fh, index=False)
    FK.to_csv(os.path.join(OUT, "fake_reps.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(RECON).to_csv(os.path.join(OUT, "recon_dry.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(PRIOR).to_csv(os.path.join(OUT, "先驗.csv"), index=False, encoding="utf-8-sig")
    json.dump(J, open(os.path.join(OUT, "FinQ_G.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[判定] {sent}")
    log(f"[完] {time.time() - t0:.0f}s")
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
