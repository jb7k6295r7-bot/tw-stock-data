# -*- coding: utf-8 -*-
"""財報品質三件 seq1【頻率表・乾跑】（台股策略線 登錄 sha fd142bbf73922770，2026-10-20 23:33；裁定 seq407 第二題、seq408 發號 N_前段 最多 ＋3、
seq411 §四「Q-A 可判、N 照 ＋3；三格一律用 fs_xbrl（含下市）、⛔ 不用 fs_hist」）——回測線計算子代理。
Q-A 應計低（Sloan 1996／Hribar & Collins 2002 現金流量表版）、Q-I 資產成長慢（Cooper, Gulen & Schill 2008）、Q-G 毛利對資產高（Novy-Marx 2013）。
⛔ 只數入選、事件個數、剔除計數、n_eff、重疊比例；⛔ 不讀、不算、不存任何進場後的價格、報酬、持有期結果。
   價格只用「排序日 t 在不在 500 張閘」與進場日 e 的成交／開盤／鎖漲停旗標、(t, e] 有無壞根。
⛔ 不 commit、不改既有程式與結果夾；researchIndMom_freq（共用面板）／researchQual（舊格定義，只為重疊比較）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchFinQ_freq [--procs 2]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchFinQ_freq_check
輸出 backtest/resultsFinQ/freq/：freq.json、freq.csv、by_year.csv、old_overlap.csv、equiv.csv、picks.csv.gz（只有代號、排序年、各格值與入選旗標）、run.log

═══ 讀法（F 標；⛔ 在看任何本件數字之前寫死於 2026-10-21（台北）；★＝執行者定，〔 〕內為另一讀法）═══
 F1 財報 ＝ tw-stock-data 最新 origin/main 的 data/meta/fs_xbrl（2013Q1 起、含已下市；年初至今累計；git archive 到 ~/b2fwork/main_<sha12>，唯讀）。
    年度值 ＝ period＝<FY>Q4 那列（Q4 YTD ＝ 全年）；★ 同 (代號, 期) 有合併 cr 與個體 ir 兩列 ⇒ 取 cr（README「同季兩種都有時取合併」）。
    ⛔ 不用 fs_hist／fin_hist（seq411 §四）。非曆年制公司累計欄空白 ⇒ 該格算不出（照計數）。
 F2 可用日（seq352／368）＝ data/meta/filing_dates.csv 該 (代號, FY, 4) 的 uploaded_at：★ 有 AI1 列 ⇒ AI1 中最早；沒有 AI1 ⇒ 全部 doc_code 中最早。
    ★ 可用 ⇔ uploaded_at 的日期 ≤ 排序日 t（t 收盤排序、下月第一個交易日開盤才買 ⇒ 當天上傳亦已知）。
    ★ 沒有時戳 ⇒ 剔除「無上傳時戳」〔另一讀法：法定期限 3/31＋5 交易日補位（PREREG品質 A2）〕；照計數。
 F3 排序日 t ＝ 每年 4 月最後一個交易日；進場 e ＝ 5 月第一個交易日開盤；持有到次年 5 月第一個交易日（12 個月）。
    世界：排序年 ≤ 2014 ⇒ 早年世界（eotc，上市＋上櫃）；≥ 2015 ⇒ 主世界（rerun17 H2D）；面板 ＝ researchIndMom_freq.build_panel（AscTri load_world 原樣、
    壞根含缺口 ≥ 5 日、早年 reduce_v2）。
    ★ 持有 12 個月走完 ⇔ 次年 5 月第一個交易日在主世界日曆內（資料尾 2026-09-24 ⇒ 排序年 ≤ 2025）。
 F4 母體 ＝ 面板股票（四碼普通股、含已下市）∧ 500 張閘在 t（Frame.gate ∧ pit_valid，登錄 §四「排序日判」）∧ t 有有效 K 棒
    ∧ 非金融保險：★ 兩條都要過 ①（t 的產業別，researchIndRev_prereg.PIT）≠ 金融保險 ② fs_xbrl industry_template ∉ {basi, bd, ins, fh}（銀行、證券、保險、金控）
    ∧ FY(Y−1) 年報可用（F2）。
 F5 三格（Y ＝ 排序年；TA ＝ total_assets 年底值；平均總資產 ＝ (TA_{Y−1} ＋ TA_{Y−2}) ÷ 2，兩者皆 ＞ 0）
    Q-A ＝（net_income_ytd − operating_cash_flow_ytd）÷ 平均總資產（FY Y−1）⇒ 最低十分位
    Q-I ＝ TA_{Y−1} ÷ TA_{Y−2} − 1 ⇒ 最低十分位
    Q-G ＝（營收 − 營業成本）÷ TA_{Y−1} ⇒ 最高十分位 ⚠ fs_xbrl 只有 revenue_ytd、沒有營業成本／毛利欄（build.py TAGS 無 CostOfSales／GrossProfit）
      ⇒ 本格在「一律用 fs_xbrl」之下【依構造算不出】；照報、⛔ 不改用 fs_hist；等裁定／資料庫補欄。
    ★ TA_{Y−2} 取 FY Y−2 年報（Q4 列；可用日早於 t 一年，照查）；2014 排序年需 FY2012 TA ⇒ fs_xbrl 2013Q1 起沒有 ⇒ Q-A、Q-I 依構造算不出（照報）。
    十分位：各格在母體內有值者 n 檔，k ＝ ⌈n ÷ 10⌉，第 k 名的值為切點，★ 同值併入（PTH 頻率表 P4 同法）。
 F6 進場剔除（PTH 頻率表 P5 同序）：壞根(t,e] → e無成交 → e開盤鎖漲停；保留 ＝ 事件。入選不因進場剔除而改、不遞補。
 F7 段（登錄 §三，依排序年）：探索 2017～2021｜確認 2022 起、整筆持有落在資料尾前（⇒ 2022～2025；2026 另列「持有未走完」）｜早年 2014～2016（描述）。
    n_eff（seq408：主 CI 用持有月分群、排序年分群並報）：
      持有月分群 n_eff ＝ min(事件數, 段內事件涵蓋的相異持有月數)（每排序年 5 月～次年 4 月 12 個月）；
      排序年分群 n_eff ＝ min(事件數, 有事件的排序年數)（每段 4～5 ⇒ 必 ＜ 30）。任一 ＜ 30 照標。
 F8 已下市（seq406）：★ 代號不在 origin/main stocks.csv，或其 last_seen 早於 stocks.csv 最晚 last_seen 10 天以上 ⇒ 已下市；報各排序年母體、入選中的家數。
 F9 與 PREREG品質 舊格重疊：舊 Q1 ROE、Q2 營業利益÷資產、Q3 ROA、Q4 研發 ＝ researchQual.load_fin（⛔ 只 import；fin_hist A0 快照 ~/msdata/1fb8815e81，
    舊件自己的資料源，只用來重現舊格名單）＋ avail_pos／q_at（A0 可用日、e 開盤前可用的最新一季 TTM）；
    ★ 舊格名單在【本件母體】（F4，不要求本件格有值）內取前十分位（同 F5 切法、高者佳）與前 20（舊格 N＝20）。
    報：本件各格入選中屬舊格前十分位的比例、舊格前 20 中屬本件格的比例、兩者共同有值股的 Spearman（平均名次 Pearson；Q-A、Q-I 取負號使「好」同向）。
 F10 seq377 乾跑等價：Q-A vs Q-I 每年 |A∩I|÷|A|、|A∩I|÷|I|、Jaccard；兩方向都 ≥ 0.8 ⇒ 近乎互蘊含、先報。
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
import math
import os
import sys
import time
from collections import Counter

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchIndMom_freq as IM              # noqa: E402  共用面板、登錄驗證、origin/main（新檔，⛔ 只 import）

REG_SHA = "fd142bbf73922770"
OUT = "backtest/resultsFinQ/freq"
OLDQ_FD = os.path.expanduser("~/msdata/1fb8815e81aa53edf91aacb8ebb4125c716ead3f/data")
FIN_TPL = {"basi", "bd", "ins", "fh"}
YEARS = list(range(2014, 2027))
SEGY = {"探索": list(range(2017, 2022)), "確認": list(range(2022, 2026)), "早年": [2014, 2015, 2016], "持有未走完(2026)": [2026]}
CELLS = ("Q-A", "Q-I", "Q-G")
NEFF_MIN = 30
LOG = IM.LOG
log = IM.log


def load_fs(DATA):
    fs = sorted(glob.glob(os.path.join(DATA, "meta", "fs_xbrl", "fs_xbrl_*.csv")))
    cols = ["period", "stock_id", "industry_template", "report", "period_end", "total_assets", "revenue_ytd", "net_income_ytd", "operating_cash_flow_ytd"]
    F = pd.concat([pd.read_csv(f, dtype={"stock_id": str, "period": str}, usecols=cols) for f in fs], ignore_index=True)
    hdr = pd.read_csv(fs[0], nrows=0).columns.tolist()
    F = F[F["period"].str.endswith("Q4")].copy()
    F["fy"] = F["period"].str[:4].astype(int)
    n_dup = int(F.duplicated(["stock_id", "fy"], keep=False).sum())
    F["_r"] = (F["report"] != "cr").astype(int)
    F = F.sort_values(["stock_id", "fy", "_r"]).drop_duplicates(["stock_id", "fy"], keep="first")
    K = {(s, y): r for s, y, r in zip(F["stock_id"], F["fy"], F.to_dict("records"))}
    return K, {"檔": [os.path.basename(f) for f in fs], "欄": hdr, "Q4列": int(len(F)), "同期cr與ir兩列(取cr)": n_dup}


def load_filing(DATA):
    fd = pd.read_csv(os.path.join(DATA, "meta", "filing_dates.csv"), dtype={"stock_id": str})
    fd = fd[fd["season"] == 4].copy()
    fd["ts"] = pd.to_datetime(fd["uploaded_at"], errors="coerce")
    fd = fd.dropna(subset=["ts"])
    fd["ai1"] = (fd["doc_code"] == "AI1").astype(int)
    g = fd.sort_values(["stock_id", "year", "ai1", "ts"], ascending=[True, True, False, True]).drop_duplicates(["stock_id", "year"], keep="first")
    return {(s, int(y)): (ts, dc) for s, y, ts, dc in zip(g["stock_id"], g["year"], g["ts"], g["doc_code"])}


def delisted_set(DATA):
    st = pd.read_csv(os.path.join(DATA, "meta", "stocks.csv"), dtype=str)
    ls = pd.to_datetime(st["last_seen"], errors="coerce"); mx = ls.max()
    alive = set(st.loc[ls >= mx - pd.Timedelta(days=10), "stock_id"])
    return alive, str(mx.date())


def dec_select(vals, low=True):
    """vals: {sid: v}（有限）⇒ 入選集合、n、k、切點（同值併入）。"""
    if not vals:
        return set(), 0, 0, np.nan
    v = np.array(list(vals.values()), float); n = len(v); k = int(math.ceil(n / 10))
    cut = np.sort(v)[k - 1] if low else np.sort(v)[::-1][k - 1]
    sel = {s for s, x in vals.items() if (x <= cut if low else x >= cut)}
    return sel, n, k, float(cut)


def topn(vals, N):
    return {s for s, _ in sorted(vals.items(), key=lambda t: (-t[1], t[0]))[:N]}


def spearman(a, b):
    ks = sorted(set(a) & set(b))
    if len(ks) < 10:
        return np.nan, len(ks)
    x = pd.Series([a[k] for k in ks]).rank().to_numpy(); y = pd.Series([b[k] for k in ks]).rank().to_numpy()
    return float(np.corrcoef(x, y)[0, 1]), len(ks)


def sort_points(Z, Y):
    cal = Z["cal"]
    apr = np.flatnonzero((cal.year == Y) & (cal.month == 4)); may = np.flatnonzero((cal.year == Y) & (cal.month == 5))
    if len(apr) == 0 or len(may) == 0:
        return None, None
    return int(apr[-1]), int(may[0])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2)
    a = ap.parse_args()
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    reg = IM.reg_check(REG_SHA)
    log(f"[登錄] {reg}（sha {REG_SHA} 已驗）")
    sha, DATA = IM.ensure_main()
    log(f"[資料] origin/main {sha[:10]} ⇒ {DATA}")
    K, finfo = load_fs(DATA)
    FD = load_filing(DATA)
    alive, mx_ls = delisted_set(DATA)
    PIT = IM.load_pit(DATA)
    has_gp = any(c in finfo["欄"] for c in ("gross_profit_ytd", "cost_of_revenue_ytd", "cost_of_sales_ytd", "gross_profit", "cost_of_sales"))
    log(f"[財報] fs_xbrl Q4 列 {finfo['Q4列']}｜同期 cr／ir 兩列 {finfo['同期cr與ir兩列(取cr)']}｜毛利／營業成本欄：{'有' if has_gp else '⛔ 沒有'}")
    # 舊格（PREREG品質）
    from backtest import researchQual as RQ                 # ⛔ 只 import；舊件自己的 fin_hist A0 快照（只用於重疊比較）
    RQ.FD = OLDQ_FD
    QOLD = RQ.load_fin(log)
    Zs = {"早年": IM.panel_aux(IM.build_panel("早年", a.procs)), "主": IM.panel_aux(IM.build_panel("主", a.procs))}
    main_tail = Zs["主"]["cal"][-1]
    OLDPOS = {wn: RQ.avail_pos(QOLD, Z["cal"])[0] for wn, Z in Zs.items()}
    BY = []; PICKS = []; OLDOV = []; EQ = []
    YD = {}
    for Y in YEARS:
        wn = "早年" if Y <= 2014 else "主"
        Z = Zs[wn]; cal = Z["cal"]
        t, e = sort_points(Z, Y)
        if t is None:
            log(f"[{Y}] 日曆內沒有 4／5 月 ⇒ 跳過"); continue
        hold_end = pd.Timestamp(Y + 1, 5, 1)
        mcal = Zs["主"]["cal"]; pe = int(mcal.searchsorted(hold_end))
        done = bool(pe < len(mcal) and mcal[pe].month == 5 and mcal[pe].year == Y + 1)
        rej = Counter(); univ = {}; vals = {c: {} for c in CELLS}; tpl_cnt = Counter()
        ts_lim = cal[t].normalize() + pd.Timedelta(days=1)                  # uploaded_at 日期 ≤ t
        for i in np.flatnonzero(Z["G"][:, t] & np.isfinite(Z["C"][:, t])):
            s = Z["sids"][i]
            ind, _ = PIT.at(s, cal[t])
            if ind == "金融保險":
                rej["金融保險(產業別)"] += 1; continue
            r1 = K.get((s, Y - 1))
            if r1 is not None and r1["industry_template"] in FIN_TPL:
                rej["金融保險(XBRL範本)"] += 1; continue
            if r1 is None:
                rej["fs_xbrl無FY(Y−1)年報"] += 1; continue
            tpl_cnt[r1["industry_template"]] += 1
            f1 = FD.get((s, Y - 1))
            if f1 is None:
                rej["無上傳時戳"] += 1; continue
            if not (f1[0] < ts_lim):
                rej["t時年報尚未上傳"] += 1; continue
            univ[s] = i
            r2 = K.get((s, Y - 2)); f2 = FD.get((s, Y - 2))
            ta1 = r1["total_assets"]; ta2 = r2["total_assets"] if (r2 is not None and f2 is not None and f2[0] < ts_lim) else np.nan
            ni, ocf = r1["net_income_ytd"], r1["operating_cash_flow_ytd"]
            if np.isfinite(ta1) and np.isfinite(ta2) and ta1 > 0 and ta2 > 0:
                vals["Q-I"][s] = ta1 / ta2 - 1.0
                if np.isfinite(ni) and np.isfinite(ocf):
                    vals["Q-A"][s] = (ni - ocf) / ((ta1 + ta2) / 2.0)
        sel = {}
        info = {}
        for c in CELLS:
            if c == "Q-G":
                sel[c] = set(); info[c] = {"n": 0, "k": 0, "切點": None, "註": "fs_xbrl 無營業成本／毛利欄 ⇒ 依構造算不出"}
                continue
            sel[c], n, k, cut = dec_select(vals[c], low=True)
            info[c] = {"n": n, "k": k, "切點": cut}
        # 母體內各格缺值原因
        miss = {}
        for s in univ:
            r2 = K.get((s, Y - 2)); r1 = K[(s, Y - 1)]
            if s not in vals["Q-I"]:
                miss.setdefault("Q-I", Counter())["FY(Y−2)年報缺" if r2 is None else "TA缺或≤0"] += 1
            if s not in vals["Q-A"]:
                why = "TA不可算" if s not in vals["Q-I"] else ("營業現金流缺" if not np.isfinite(r1["operating_cash_flow_ytd"]) else "淨利缺")
                miss.setdefault("Q-A", Counter())[why] += 1
        row = {"排序年": Y, "世界": wn, "排序日t": str(cal[t].date()), "進場日e": str(cal[e].date()), "持有12月走完": done,
               "閘內(500張∧t有K棒)": int((Z["G"][:, t] & np.isfinite(Z["C"][:, t])).sum()), **{f"剔除_{k}": v for k, v in rej.items()},
               "母體(非金融∧年報可用)": len(univ), "母體已下市家數": sum(1 for s in univ if s not in alive)}
        for c in CELLS:
            fl = Counter(IM.entry_flag(Z, univ[s], t, e) for s in sel[c])
            row[f"{c}_有值"] = info[c]["n"]; row[f"{c}_⌈n/10⌉"] = info[c]["k"]; row[f"{c}_入選"] = len(sel[c])
            row[f"{c}_切點"] = info[c]["切點"]
            for k_, v in fl.items():
                row[f"{c}_進場_{k_}"] = v
            row[f"{c}_事件(保留)"] = fl.get("保留", 0)
            row[f"{c}_入選已下市"] = sum(1 for s in sel[c] if s not in alive)
            if c in miss:
                row[f"{c}_母體內缺值"] = json.dumps(dict(miss[c]), ensure_ascii=False)
        row["XBRL範本(母體前)"] = json.dumps(dict(tpl_cnt), ensure_ascii=False)
        # F10
        A_, I_ = sel["Q-A"], sel["Q-I"]
        if A_ and I_:
            ia = len(A_ & I_)
            eq = {"排序年": Y, "Q-A入選": len(A_), "Q-I入選": len(I_), "交集": ia, "交集÷Q-A": round(ia / len(A_), 4), "交集÷Q-I": round(ia / len(I_), 4),
                  "Jaccard": round(ia / len(A_ | I_), 4), "Spearman(Q-A,Q-I)": round(spearman(vals["Q-A"], vals["Q-I"])[0], 4)}
            EQ.append(eq)
        # F9 舊格
        qa = RQ.q_at(QOLD, OLDPOS[wn], e)
        for k in ("Q1", "Q2", "Q3", "Q4"):
            ov = {s: v for s, v in qa[k].items() if s in univ}
            od, on, ok_, _ = dec_select(ov, low=False); o20 = topn(ov, 20)
            for c in ("Q-A", "Q-I"):
                if not sel[c]:
                    continue
                sp, nsp = spearman({s: -v for s, v in vals[c].items()}, ov)
                OLDOV.append({"排序年": Y, "本件格": c, "舊格": f"{k} {RQ.QN[k]}", "舊格母體內有值": on, "舊格前十分位": len(od),
                              "本件入選": len(sel[c]), "本件入選∩舊前十分位": len(sel[c] & od),
                              "比例_本件中屬舊前十分位": round(len(sel[c] & od) / len(sel[c]), 4),
                              "比例_舊前十分位中屬本件": round(len(sel[c] & od) / len(od), 4) if od else None,
                              "舊前20中屬本件": len(o20 & sel[c]), "Spearman(本件取負,舊)": round(sp, 4) if np.isfinite(sp) else None, "共同有值": nsp})
        for s, i in univ.items():
            PICKS.append({"排序年": Y, "sid": s, "已下市": s not in alive, "Q-A": vals["Q-A"].get(s, np.nan), "Q-I": vals["Q-I"].get(s, np.nan),
                          "Q-A入選": s in sel["Q-A"], "Q-I入選": s in sel["Q-I"],
                          "Q-A_st": IM.entry_flag(Z, i, t, e) if s in sel["Q-A"] else "", "Q-I_st": IM.entry_flag(Z, i, t, e) if s in sel["Q-I"] else ""})
        BY.append(row); YD[Y] = {"row": row, "sel": sel, "univ": univ, "done": done, "t": t, "e": e, "wn": wn}
        log(f"[{Y}] t {row['排序日t']}｜母體 {len(univ)}（已下市 {row['母體已下市家數']}）｜Q-A 有值 {info['Q-A']['n']} 入選 {len(sel['Q-A'])}｜"
            f"Q-I 有值 {info['Q-I']['n']} 入選 {len(sel['Q-I'])}｜走完 {done}")
    # 段
    J = {"性質": "財報品質三件 seq1 頻率表乾跑（⛔ 未讀、未算任何進場後價格、報酬、持有期結果）", "登錄": f"台股策略線 seq1 sha {REG_SHA}",
         "裁定": "seq407 第二題、seq408 發號、seq411 §四（fs_xbrl、⛔ fs_hist）", "資料": {"origin/main": sha, "fs_xbrl": finfo, "stocks.csv 最晚 last_seen": mx_ls,
                                                                              "毛利／營業成本欄": has_gp},
         "Q-G": "fs_xbrl 只有 revenue_ytd，無營業成本／毛利（build.py TAGS：Revenue、ProfitLossBeforeTax、ProfitLoss、CashFlowsFromUsedInOperatingActivities、"
                "Depreciation、PPE capex…）⇒ 一律用 fs_xbrl 之下【依構造算不出】；待裁定（資料庫補 ifrs-full:GrossProfit／CostOfSales 欄，或另准來源）",
         "段": {}}
    FREQ = []
    for sg, ys in SEGY.items():
        ys = [y for y in ys if y in YD]
        segj = {"排序年": ys}
        for c in CELLS:
            ev = [(y, s) for y in ys for s in YD[y]["sel"][c] if IM.entry_flag(Zs[YD[y]["wn"]], YD[y]["univ"][s], YD[y]["t"], YD[y]["e"]) == "保留"]
            nev = len(ev); yrs = sorted({y for y, _ in ev})
            hm = {(y + (m - 1) // 12, (m - 1) % 12 + 1) for y in yrs for m in range(5, 17)}
            ne_m = min(nev, len(hm)); ne_y = min(nev, len(yrs))
            cj = {"事件數(保留)": nev, "排序年數(有事件)": len(yrs), "相異持有月": len(hm), "n_eff_持有月分群": ne_m, "n_eff_排序年分群": ne_y,
                  "n_eff_持有月<30": bool(ne_m < NEFF_MIN), "n_eff_排序年<30": bool(ne_y < NEFF_MIN),
                  "每年入選": {y: YD[y]["row"][f"{c}_入選"] for y in ys}, "每年事件": {y: YD[y]["row"][f"{c}_事件(保留)"] for y in ys},
                  "相異檔數": len({s for _, s in ev}), "入選已下市": sum(YD[y]["row"][f"{c}_入選已下市"] for y in ys),
                  "判斷": ("依構造算不出（fs_xbrl 無毛利欄）" if c == "Q-G" else
                         ("依構造不可判定、不計 N" if ne_m < NEFF_MIN else "持有月分群可判；排序年分群 ＜ 30（照 seq408 並報、兩者不同照寫）"))}
            segj[c] = cj
            FREQ.append({"段": sg, "格": c, "排序年": f"{ys[0]}～{ys[-1]}" if ys else "", **{k: v for k, v in cj.items() if not isinstance(v, (dict, list))}})
        J["段"][sg] = segj
        log(f"[段 {sg}] " + "｜".join(f"{c} 事件 {segj[c]['事件數(保留)']} n_eff 持有月 {segj[c]['n_eff_持有月分群']}／排序年 {segj[c]['n_eff_排序年分群']}" for c in CELLS))
    # 重疊摘要（段）
    ov = pd.DataFrame(OLDOV)
    if len(ov):
        osum = []
        for sg, ys in SEGY.items():
            o = ov[ov["排序年"].isin(ys)]
            for (c, k), g in o.groupby(["本件格", "舊格"]):
                osum.append({"段": sg, "本件格": c, "舊格": k, "本件入選合計": int(g["本件入選"].sum()), "∩舊前十分位": int(g["本件入選∩舊前十分位"].sum()),
                             "比例_本件中屬舊前十分位": round(g["本件入選∩舊前十分位"].sum() / g["本件入選"].sum(), 4),
                             "Spearman_年中位": round(float(g["Spearman(本件取負,舊)"].median()), 4)})
        J["舊格重疊_段"] = osum
    eqd = pd.DataFrame(EQ)
    J["seq377等價_Q-A_vs_Q-I"] = {"每年": EQ, "交集÷Q-A_中位": float(eqd["交集÷Q-A"].median()) if len(eqd) else None,
                                 "交集÷Q-I_中位": float(eqd["交集÷Q-I"].median()) if len(eqd) else None,
                                 "互蘊含(兩方向≥0.8)年數": int(((eqd["交集÷Q-A"] >= 0.8) & (eqd["交集÷Q-I"] >= 0.8)).sum()) if len(eqd) else 0}
    J["讀法"] = __doc__.split("═══ 讀法")[1]
    J["時間"] = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")
    pd.DataFrame(FREQ).to_csv(os.path.join(OUT, "freq.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(BY).to_csv(os.path.join(OUT, "by_year.csv"), index=False, encoding="utf-8-sig")
    ov.to_csv(os.path.join(OUT, "old_overlap.csv"), index=False, encoding="utf-8-sig")
    eqd.to_csv(os.path.join(OUT, "equiv.csv"), index=False, encoding="utf-8-sig")
    with gzip.open(os.path.join(OUT, "picks.csv.gz"), "wt", encoding="utf-8") as fh:
        pd.DataFrame(PICKS).to_csv(fh, index=False)
    json.dump(J, open(os.path.join(OUT, "freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] {time.time() - t0:.0f}s")
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
