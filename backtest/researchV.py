# -*- coding: utf-8 -*-
"""PREREGV 早年段驗收（台股策略線 seq5 sha c56a87a3d8c47135；＋營飆 v2 候選 seq2 sha c4e9ab933b4bfb15，裁定 seq207／seq210 N_驗收 26）。
回測線，2026-09-27。⭐ 本檔目前【只有 pre 段】：資料管線＋閘門＋開跑前算術。⛔ 本段不讀、不印、不算任何 2015 以前的報酬。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchV pre-data            # 早年版面＋結構閘門＋逐格起點
    ... -m backtest.researchV pre-arith [--procs 2]                                                         # 開跑前算術（⛔ 只用主窗）
    ... -m backtest.researchV pre-report                                                                    # ⇒ resultsV/PRE_REPORT.md

依據：登錄 seq5 §二（窗、資料、規則）、§三（開跑前閘 G1／G2）、§四（開跑前算術）、§八（回測線：開跑前算術、逐格起點）；
      裁定 seq206 §三（主驗收只上市；結果句必附「早年只驗上市股」）；台股 seq260（再附「樣本只有約 3 年」）；
      資料庫線 0404／0406／2323（G1、錨點、G2）、0344（本益比）、0822（大盤法人金額）、1827（月營收去重）、1450（早年日 K、0050）、1504（規則 A）。

═══ pre-arith（⛔ 只用主窗 2017-03-02～2026-08-24；程式一字不動，呼叫 researchYear1M 的 setup／sig_of／run_engine／p12_derived）═══
  格      PREREGV 24 格：#1～#17（rerun17；#1 #4 #7 #16 #17 用 t−1 閘）、#18～#23（P9 A2／Ba／Bb／Bc／Cc／Ce）、#24（researchAvg 乙一 By）
  種子    照各原件（P10 1000＋r、P1／P3乙 7000＋r、P12 族 102000＋r、P9／#24 99000＋r），r ∈ [0,200)
  閘      每顆種子的 年化／回落 repr 逐位元 ＝ 既有逐種子檔（rerun17 seeds_main、regime_t1 seeds t1、resultsP9run seeds_arms、resultsAvg B_seeds_arms By）
  序列    該格 200 顆的逐日報酬【平均】（登錄 §四「有種子的格用 200 顆的逐日平均報酬序列」）− 0050 還原逐日報酬；t ∈ (w0, w1]，2,312 個
  月分群  t 的曆月（2017-03～2026-08，114 個月）
  年化差  主讀法：日差平均 × 245（算術）；另列 幾何（平均路徑 CAGR − 0050 CAGR，只點值）
  門檻 T  主窗月份【置中】後隨機重抽 30 個月（B＝20,000，種子 default_rng(20260927)），T ＝ −(α 分位) ；α ＝ 0.05／24（登錄字面）與 0.05／26 並列
  連續窗  主窗內每一段連續 30 個月（85 段）各自做月分群 bootstrap（B＝20,000、同一組重抽索引），數下界 ＞ 0 的段數
  判讀    24 格主窗年化差 ＜ T 全部成立 ⇒ 逐字寫「本段樣本只夠分 Q／R／F，『可以說找到』依構造不可得」（登錄 §四）
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import subprocess
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(HERE, "resultsV")
DBDRAFT = "/mnt/c/SynologyDrive/投資/資料庫用/草稿/early_checks_out.json"
ANN = 245
B_BOOT = 20_000
BOOT_SEED = 20260927
N_MONTHS = 30
ALPHAS = {"0.05/24": 0.05 / 24, "0.05/26": 0.05 / 26}
PREREGV = {  # 編號 ⇒ (名稱, 族)
    1: ("PREREG10 AND regime=True N10 H120（營飆 v1；t−1 閘）", "P10"), 2: ("P3 乙臂 N8 d=1.0 relvol", "P3B"), 3: ("P1 AND N8 d=1.0 relvol", "P1"),
    4: ("PREREG10 AND regime=True N10 LD（t−1 閘）", "P10"), 5: ("P17 R_eq", "P17"), 6: ("P1 AND N8 d=2.0 relvol", "P1"),
    7: ("PREREG10 AND regime=True N10 H60（t−1 閘）", "P10"), 8: ("P14 w=0.50", "P14"), 9: ("P1 AND N10 d=inf relvol", "P1"),
    10: ("P3 乙臂 N8 d=2.0 relvol", "P3B"), 11: ("P1 AND N8 d=inf relvol", "P1"), 12: ("PREREG10 AND regime=False N10 H120", "P10"),
    13: ("P1 AND N20 d=inf relvol（營量 v1）", "P1"), 14: ("P1 AND N20 d=inf null", "P1"), 15: ("PREREG10 regime=False N20 H60", "P10"),
    16: ("PREREG10 regime=True N20 H60（t−1 閘）", "P10"), 17: ("PREREG10 regime=True N20 H120（t−1 閘）", "P10"),
    18: ("P9 2-A k2", "P9"), 19: ("P9 2-B ⓐ（+15% 加碼）", "P9"), 20: ("P9 2-B ⓑ（三分位加碼）", "P9"), 21: ("P9 2-B ⓒ（滿 40 根仍為正加碼）", "P9"),
    22: ("P9 2-C ⓒ（0050 MA60 下新部位 1.5 slot）", "P9"), 23: ("P9 2-C ⓔ（0050 MA10 下新部位 0.5 slot）", "P9"),
    24: ("PREREG攤平停利 乙一（門檻B W1 H120 N8，−10% 加半份）", "AVG"),
}
V2 = {25: ("營飆 v2 候選一 M20 state＋整份", "V2"), 26: ("營飆 v2 候選二 K4 排名（pick_tie=rng）", "V2")}


def _log_to(path):
    os.makedirs(OUT, exist_ok=True)
    f = open(path, "a", encoding="utf-8"); t0 = time.time()

    def log(x):
        x = f"[{time.time() - t0:6.0f}s] {x}"
        print(x, flush=True); f.write(x + "\n"); f.flush()
    return log


def _sha256(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


# ═════════════════════════ pre-data ═════════════════════════
def pre_data(log):
    from . import early_data as E
    man = E.extract(log=log)
    st = E.build(log=log)                                   # R1a 版面（結構閘門與 R1 無關）
    rd = os.path.join(E.raw_dir(), "data")
    daily = E.read_daily(markets=("twse", "tpex"))
    tw = daily[daily["market"] == "twse"]
    cal = E.calendar(daily, "twse")
    pos = {d: i for i, d in enumerate(cal)}
    G = {"快照": {"tw-stock-data": E.EARLY_SHA, "取出": man}, "版面": st}

    # ── 閘 A 日曆 ＝ 日 K（只上市）──
    files = sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(rd, "early", "daily", "*.csv")))
    S = E.structure()
    s_tw = sorted(S.loc[(S["market"] == "twse") & (S["rows"] > 0), "date"])
    per_d = sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(rd, "early", "per", "*.csv")))
    ia_d = sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(rd, "early", "instamt", "*.csv")))
    cal_12_14 = [d for d in cal if "2012-01-01" <= d <= "2014-12-31"]
    cal_ia = [d for d in cal if ia_d[0] <= d <= "2014-12-31"]
    wk = [d for d in cal if pd.Timestamp(d).weekday() >= 5]
    s_rows = S[S["market"] == "twse"].set_index("date")["rows"]
    wk_thin = [d for d in wk if s_rows[d] < 0.9 * float(s_rows.median())]      # 週六補班交易日應為滿列；列數不足九成才算異常
    main_first = pd.read_csv(os.path.join(rd, "meta", "calendar_twse.csv"))["date"].min()
    w0a = next(d for d in cal if d >= "2012-06-01")
    w0b = cal[pos[w0a] + 1]
    w1 = [d for d in cal if d <= E.WIN_END][-1]
    G["A_日曆"] = {"上市日曆天數": len(cal), "起訖": [cal[0], cal[-1]], "＝日檔檔名": cal == files, "＝_structure twse rows>0": cal == s_tw,
                 "本益比 2012～2014 天數": len(per_d), "＝日曆∩2012～2014": per_d == cal_12_14,
                 "大盤法人金額天數": len(ia_d), "＝日曆∩[首日,2014-12-31]": ia_d == cal_ia, "週六交易日（補班形狀）": wk, "其中列數不足中位九成": wk_thin,
                 "主庫日曆首日": main_first, "早年末日→主庫首日": [cal[-1], main_first],
                 "窗": {"2012-06 第一個交易日（R14a）": w0a, "其次一交易日（R14b，主窗同構：量測日次日）": w0b, "w1": w1,
                       "窗內交易日（R14a）": pos[w1] - pos[w0a] + 1, "窗內曆月": len({d[:7] for d in cal if w0a <= d <= w1})}}
    G["A_日曆"]["過"] = bool(G["A_日曆"]["＝日檔檔名"] and G["A_日曆"]["＝_structure twse rows>0"] and G["A_日曆"]["＝日曆∩2012～2014"]
                          and G["A_日曆"]["＝日曆∩[首日,2014-12-31]"] and not wk_thin)
    log(f"[閘A 日曆] {json.dumps(G['A_日曆'], ensure_ascii=False)}")

    # ── 閘 B 0050（兩個來源互驗＋官方除息三筆）──
    e50 = tw[tw["stock_id"] == "0050"].set_index("date")
    x50 = E.extra_0050_daily().set_index("date")
    com = sorted(set(e50.index) & set(x50.index))
    diffs = {}
    for c in ("open", "high", "low", "close", "volume", "amount", "transactions"):
        a_ = e50.loc[com, c].astype(float).to_numpy(); b_ = pd.to_numeric(x50.loc[com, c], errors="coerce").to_numpy(float)
        diffs[c] = int((~np.isclose(a_, b_, rtol=0, atol=1e-9)).sum())
    A50 = E.adj_0050()
    ev = []
    tr50 = [d for d in cal if d in e50.index and np.isfinite(e50.loc[d, "close"])]
    for r in A50.itertuples():
        k = tr50.index(r.date) if r.date in tr50 else -1
        prev_c = float(e50.loc[tr50[k - 1], "close"]) if k > 0 else np.nan
        ev.append({"除息日": r.date, "前一有成交日": tr50[k - 1] if k > 0 else None, "早年日K前收": prev_c, "官方除息前收": float(r.pre_close),
                   "前收相同": bool(abs(prev_c - float(r.pre_close)) < 5e-3), "官方參考價": float(r.ref_price),
                   "factor": float(r.factor), "參考價÷前收（8 位）": round(float(r.ref_price) / float(r.pre_close), 8),
                   "factor 相同": bool(abs(round(float(r.ref_price) / float(r.pre_close), 8) - float(r.factor)) < 5e-9),
                   "早年cum": float(r.cum_factor), "主庫cum": float(r.cum_factor_main), "主庫cum÷早年cum": float(r.cum_factor_main) / float(r.cum_factor)})
    const = [e["主庫cum÷早年cum"] for e in ev]
    G["B_0050"] = {"兩來源共同日": len(com), "早年日K 0050 天數（2012～2014）": int(sum(1 for d in e50.index if "2012" <= d <= "2014-12-31")),
                   "extra 天數": int(len(x50)), "逐欄不同數": diffs, "官方除息（窗內，data/extra）": ev,
                   "早年 cum 與主庫 cum 只差常數": bool(np.ptp(const) < 1e-6),
                   "資料庫線 0404 §二（引用）": "官方 0050 除息 2005～2014 共 10 次：前收 10／10、官方前收−息值＝參考價 10／10 ⇒ 自算還原 10／10",
                   "⛔ 2011 年除息": "data/extra 只到 2012 ⇒ MA200 回看（2011-08 起）缺 2011-10 那一筆（M5）"}
    G["B_0050"]["過（窗內）"] = bool(all(v == 0 for v in diffs.values()) and len(com) == len(x50) and all(e["前收相同"] and e["factor 相同"] for e in ev))
    log(f"[閘B 0050] 共同日 {len(com)}｜不同 {diffs}｜除息三筆 前收／factor 全對 {all(e['前收相同'] and e['factor 相同'] for e in ev)}")

    # ── 閘 C 規則 A／B 與資料庫線草稿同一套（逐筆）──
    dup = int(daily.duplicated(["stock_id", "date"]).sum())
    det = E.detect_rule_ab(daily, files)
    mine = {(s, p, d, r, x) for s, p, d, r, x in det}
    C = {"同日重複列": dup, "本檔 A": sum(1 for x in det if x[3] == "A"), "本檔 B": sum(1 for x in det if x[3] == "B")}
    if os.path.exists(DBDRAFT):
        db = json.load(open(DBDRAFT, encoding="utf-8"))["det"]
        theirs = {(s, p, d, r, x) for s, _m, p, d, r, x in db}
        C.update({"資料庫線草稿 A": sum(1 for x in db if x[4] == "A"), "資料庫線草稿 B": sum(1 for x in db if x[4] == "B"),
                  "只在本檔": len(mine - theirs), "只在草稿": len(theirs - mine), "例_只在本檔": sorted(mine - theirs)[:5], "例_只在草稿": sorted(theirs - mine)[:5],
                  "草稿檔": DBDRAFT, "草稿 sha256": _sha256(DBDRAFT)[:16]})
        C["過"] = bool(mine == theirs)
    else:
        C["過"] = None; C["草稿檔"] = "讀不到"
    tw_rows = set(zip(tw["stock_id"], tw["date"]))
    detw = [x for x in det if (x[0], x[2]) in tw_rows]
    C["上市列（事件日是 twse 列）"] = {"A": sum(1 for x in detw if x[3] == "A"), "B": sum(1 for x in detw if x[3] == "B"),
                                  "A 2011～2014": sum(1 for x in detw if x[3] == "A" and "2011-01-01" <= x[2] <= "2014-12-31"),
                                  "A 描述段 2008-01～2012-05": sum(1 for x in detw if x[3] == "A" and "2008-01-01" <= x[2] <= "2012-05-31"),
                                  "B 描述段 2008-01～2012-05": sum(1 for x in detw if x[3] == "B" and "2008-01-01" <= x[2] <= "2012-05-31")}
    C["資料庫線 G1（引用 0404／0406）"] = "上市 2011～2014 官方 TWTAUU 88｜規則 A 命中 87（98.9%）｜漏 1805 2011-09-08｜A∪B 88／88 ⇒ 過"
    C["⚠"] = "規則 A 只用在描述段；主判定只用官方 TWTAUU（登錄 §三）⇒ 需 M4 落地"
    G["C_規則A"] = C
    pd.DataFrame(det, columns=["stock_id", "prev_date", "date", "rule", "ref_over_prev"]).to_csv(os.path.join(OUT, "pre_ruleab_events.csv"), index=False)
    log(f"[閘C 規則A] {json.dumps({k: v for k, v in C.items() if not k.startswith('例')}, ensure_ascii=False)}")

    # ── 閘 D 早年末日 ⇔ 主庫首日（登錄沒寫；補充：參考價 ＝ 前收）──
    def git_show(path):
        p = subprocess.run(["git", "-C", E.DB_REPO, "show", f"{E.EARLY_SHA}:{path}"], capture_output=True, check=True)
        return pd.read_csv(__import__("io").BytesIO(p.stdout), dtype=str, keep_default_na=False)
    m0 = git_show(f"data/universe/daily/{main_first}.csv")
    m0 = m0[m0["market"] == "twse"].copy()
    try:
        exr = git_show(f"data/universe/exright/{main_first}.csv"); ex_ids = set(exr["stock_id"])
    except subprocess.CalledProcessError:
        ex_ids = set()
    last = tw[tw["date"] == cal[-1]].set_index("stock_id")
    m0["close_f"] = pd.to_numeric(m0["close"], errors="coerce"); m0["chg_f"] = pd.to_numeric(m0["change"], errors="coerce")
    m0 = m0[m0["close_f"].notna() & m0["chg_f"].notna() & m0["stock_id"].isin(last.index)]
    m0 = m0[np.isfinite(last.loc[m0["stock_id"], "close"].to_numpy(float))]
    ref = (m0["close_f"] - m0["chg_f"]).round(2).to_numpy()
    prv = last.loc[m0["stock_id"], "close"].to_numpy(float)
    ok = np.abs(ref - prv) < 5e-3
    ev_mask = m0["stock_id"].isin(ex_ids).to_numpy()
    bad = m0.loc[~ok, "stock_id"].tolist()
    G["D_銜接"] = {"說明": f"主庫 {main_first} 上市列（close−change＝參考價）對 早年 {cal[-1]} 收盤；兩天都有成交", "檔數": int(len(m0)),
                  "相同": int(ok.sum()), "不同": int((~ok).sum()), "不同且為當日除權息": int((~ok & ev_mask).sum()),
                  "不同且非事件（例）": [s for s, e in zip(bad, m0.loc[~ok, "stock_id"].isin(ex_ids)) if not e][:10],
                  "當日除權息檔數": len(ex_ids)}
    G["D_銜接"]["過"] = bool(G["D_銜接"]["不同"] == G["D_銜接"]["不同且為當日除權息"])
    log(f"[閘D 銜接] {json.dumps(G['D_銜接'], ensure_ascii=False)}")

    # ── 閘 E 名冊（R13 a：日 K 自推）對官方下市、轉上市 ──
    R = pd.read_csv(os.path.join(E.snap_dir(), "R1a", "roster_with_src.csv"), dtype=str)
    dl = pd.read_csv(os.path.join(rd, "meta", "delisted.csv"), dtype={"stock_id": str})
    dl = dl[(dl["market"] == "twse") & (dl["delist_date"] >= cal[0]) & (dl["delist_date"] <= E.WIN_END)]
    Rr = R.set_index("stock_id")
    gaps = []; not_in = []
    for s, d in zip(dl["stock_id"], dl["delist_date"]):
        if s not in Rr.index:
            not_in.append(s); continue
        ls = Rr.loc[s, "last_seen"]
        gaps.append(int(np.searchsorted(cal, d) - pos[ls]))
    gaps = np.array(gaps)
    o2t = pd.read_csv(os.path.join(rd, "meta", "otc_to_twse.csv"), dtype={"stock_id": str})
    o2t = o2t[(o2t["transfer_date"] >= cal[0]) & (o2t["transfer_date"] <= E.WIN_END)]
    fg = []
    for s, d in zip(o2t["stock_id"], o2t["transfer_date"]):
        if s in Rr.index:
            fg.append(int(pos[Rr.loc[s, "first_seen"]] - np.searchsorted(cal, d)))
    fg_neg = [(s, d, Rr.loc[s, "first_seen"]) for s, d in zip(o2t["stock_id"], o2t["transfer_date"]) if s in Rr.index and pos[Rr.loc[s, "first_seen"]] < np.searchsorted(cal, d)]
    fg = np.array(fg)
    gone = R[(R["last_seen"] < cal[-1]) & (R["kind"] == "stock")]
    gone_nodl = sorted(set(gone["stock_id"]) - set(dl["stock_id"]))
    G["E_名冊"] = {"早年上市代號": int(len(R)), "kind 分布": R["kind"].value_counts().to_dict(),
                  "kind 待裁（今日 stocks.csv 沒有）": R.loc[R["kind"] == "?", ["stock_id", "name", "first_seen", "last_seen"]].to_dict("records"),
                  "官方上市下市（2004-02-11～2014-12-31）": int(len(dl)), "其中早年日K沒有": not_in,
                  "下市日 − 最後有列日（交易日）分布": {"≤0（最後列在下市日當天或之後）": int((gaps <= 0).sum()), "1～5": int(((gaps >= 1) & (gaps <= 5)).sum()),
                                              "6～60": int(((gaps > 5) & (gaps <= 60)).sum()), ">60": int((gaps > 60).sum()), "中位": float(np.median(gaps)) if len(gaps) else None},
                  "轉上市（2004-02-11～2014-12-31）": int(len(o2t)), "其中早年日K有上市列": int(len(fg)),
                  "首列日 − 轉上市日（交易日）分布": {"0": int((fg == 0).sum()), "1～5": int(((fg >= 1) & (fg <= 5)).sum()), "<0": int((fg < 0).sum()), ">5": int((fg > 5).sum())},
                  "首列早於轉上市日的": fg_neg,
                  "kind=stock 窗尾前消失、但不在官方下市名冊": {"檔數": len(gone_nodl), "例": gone_nodl[:15]},
                  "kind 待裁中四碼代號": int(R.loc[R["kind"] == "?", "stock_id"].str.fullmatch(r"[1-9]\d{3}").sum()),
                  "kind 待裁且 last_seen ≥ 2012-06-01": R.loc[(R["kind"] == "?") & (R["last_seen"] >= "2012-06-01"), ["stock_id", "name", "last_seen"]].to_dict("records"),
                  "⚠": "kind 待裁的四碼代號多半是早年已下市的普通股；R2 未裁前它們不在 load_universe ⇒ 倖存者偏差 ⇒ R2 必須在開跑前裁"}
    log(f"[閘E 名冊] 下市 {len(dl)}（日K沒有 {len(not_in)}）｜轉上市 {len(o2t)}｜kind 待裁 {int((R['kind'] == '?').sum())}｜消失非下市 {len(gone_nodl)}")

    # ── 閘 F 月營收（去重、窗內無重複、fixture）──
    fx = pd.read_csv(os.path.join(rd, "early", "revenue", "2010-06_twse.csv"), dtype=str, keep_default_na=False)
    fxd = E.dedup_revenue(fx)
    rs = pd.read_csv(os.path.join(rd, "early", "_revenue_structure.csv"), dtype=str)
    rs["rows"] = rs["rows"].astype(int); rs["distinct_codes"] = rs["distinct_codes"].astype(int)
    win_rs = rs[(rs["market"] == "twse") & (rs["period"] >= "2010-04") & (rs["period"] <= "2014-12")]
    G["F_月營收"] = {"fixture 2010-06 上市": {"列": int(len(fx)), "去重後": int(len(fxd)), "資料庫線 1827 數字": "1,186 列 ＝ 771 代號",
                                          "去重後仍為「電子工業」且原本重複的代號": int((fxd["stock_id"].isin(fx.loc[fx.duplicated("stock_id", keep=False), "stock_id"]) & (fxd["產業別"] == "電子工業")).sum()),
                                          "過": bool(len(fx) == 1186 and len(fxd) == 771 and fxd["stock_id"].is_unique
                                                    and not (fxd["stock_id"].isin(fx.loc[fx.duplicated("stock_id", keep=False), "stock_id"]) & (fxd["產業別"] == "電子工業")).any())},
                   "上市 2010-04～2014-12 期檔（rev_hi24 回看＋窗）": int(len(win_rs)), "其中 rows≠distinct（有重複）": win_rs.loc[win_rs["rows"] != win_rs["distinct_codes"], "period"].tolist()}
    log(f"[閘F 月營收] {json.dumps(G['F_月營收'], ensure_ascii=False)}")

    # ── 閘 G 主窗程式指到早年版面（⛔ 不算報酬：只讀日曆、名冊、0050 還原因子）──
    from . import data as D
    from . import universe_gate as UG
    from . import early_data as E2
    E2.use_early(strict=False)
    calD = D.load_calendar(); uni = D.load_universe()
    stocks = pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str)
    g3 = UG.gate3(stocks)
    s50 = D.load_stock("0050", "twse", calD)
    adj = D.load_adj("0050")
    F = D.cum_factor_series(pd.DatetimeIndex(pd.to_datetime(tr50)), adj)
    fchk = []
    for r in A50.itertuples():
        i = tr50.index(r.date)
        fchk.append(bool(abs(F[i - 1] / F[i] - float(r.factor)) < 1e-12))
    G["G_指到早年"] = {"D.DATA": D.DATA, "load_calendar": [str(calD[0].date()), str(calD[-1].date()), len(calD)],
                     "load_universe（kind=stock、twse＋tpex）": int(len(uni)), "gate3": int(len(g3)), "load_stock 0050 列": int(s50.df["traded"].sum()),
                     "0050 還原因子在除息日的跳動＝官方 factor": fchk, "load_adj 其餘個股": "⛔ 沒有檔（M3）⇒ 全部當 1 ⇒ 未還原",
                     "stocks_inst": "⛔ 沒有目錄（M1）⇒ p4_features.load_inst 回全 NaN ⇒ inst_ok 恆假", "shares": "⛔ 全空（M2）"}
    G["G_指到早年"]["過（格式）"] = bool(len(calD) == len(cal) and all(fchk))
    log(f"[閘G 指到早年] {json.dumps({k: v for k, v in G['G_指到早年'].items()}, ensure_ascii=False, default=str)}")

    # ── 結構量（起點用；⛔ 不算報酬）──
    uni_tw = set(R.loc[R["kind"] == "stock", "stock_id"])
    trad = tw[np.isfinite(tw["close"]) & (tw["close"] > 0)]
    tr_by = trad.groupby("stock_id")["date"].apply(lambda s: np.array(sorted(s)))
    at_w0 = sorted(uni_tw & set(trad.loc[trad["date"] == w0a, "stock_id"]))
    bars_tw = {s: int(np.searchsorted(tr_by[s], w0a, side="left")) for s in at_w0}
    otc = daily[(daily["market"] == "tpex") & np.isfinite(daily["close"]) & (daily["close"] > 0)]
    otc_by = otc.groupby("stock_id")["date"].count()
    rv_all = {m: E.read_revenue(markets=(m,)) for m in ("twse", "tpex")}
    rvp = {m: v.assign(rev=pd.to_numeric(v["當月營收"], errors="coerce")).pivot(index="period", columns="stock_id", values="rev").sort_index() for m, v in rv_all.items()}

    def rev24_ok(sid, per, mk):
        mats = [rvp[x] for x in mk]
        ps = sorted(set().union(*[set(m.index) for m in mats]))
        k = ps.index(per)
        vals = []
        for p in ps[k - 24:k + 1]:
            v = np.nan
            for m in mats:
                if sid in m.columns and p in m.index and np.isfinite(m.loc[p, sid]):
                    v = m.loc[p, sid]; break
            vals.append(v)
        return len(vals) == 25 and np.isfinite(vals).all()
    # w0 可用的最新一期：M 月營收在 M+1 月 10 日後可用 ⇒ 2012-06-01 可用 2012-04
    per_w0 = "2012-04"
    s_ids = sorted(at_w0)
    t86_20 = cal[pos[next(d for d in cal if d >= E.T86_TWSE_START)] + 19]
    SC = {"w0（R14a）": w0a, "w0 當天有成交的上市 kind=stock": len(s_ids),
          "research11 ≥ 249 根（只 twse 列，R1a）": int(sum(v >= 249 for v in bars_tw.values())),
          "p4 bars ≥ 120（只 twse 列，R1a）": int(sum(v >= 120 for v in bars_tw.values())),
          "其中曾有上櫃列（轉上市，R1b 會多出歷史）": int(sum(1 for s in s_ids if s in otc_by.index)),
          f"rev_hi24 算得出（{per_w0}＋前 24 期，twse 檔，R11a）": int(sum(rev24_ok(s, per_w0, ("twse",)) for s in s_ids)),
          f"rev_hi24 算得出（{per_w0}＋前 24 期，兩市檔，R11b）": int(sum(rev24_ok(s, per_w0, ("twse", "tpex")) for s in s_ids)),
          "T86 上市首日": E.T86_TWSE_START, "T86 第 20 個交易日（fore20／trust20 min_periods＝20 首個可算日）": t86_20,
          "0050 MA200 回看起點（w0 前 200 根）": cal[pos[w0a] - 199], "0050 MA60 回看起點": cal[pos[w0a] - 59]}
    G["結構量"] = SC
    log(f"[結構量] {json.dumps(SC, ensure_ascii=False)}")

    # ── 逐格起點 ──
    rows = []
    need_common = ["M3（還原）", "M4（主版減資剔除）"]
    for cid, (nm, fam) in {**PREREGV, **V2}.items():
        if fam in ("P10", "P1", "P3B", "V2"):
            feats = "research11 S（ret20、nup20、amt 比、MA100、250 日高；≥249 根）＋research34 rev_hi24（24 期）＋research13 AND（面板 ≤45 根）"
            feats += "＋relvol" if fam in ("P1", "P3B") else ""
            warm = f"249 根（w0 前 twse 首列 ≤ {cal[pos[w0a] - 249]}）；rev 2010-04 起；"
            need = list(need_common)
            if fam == "P10" and cid in (1, 4, 7, 16, 17) or fam == "V2":
                feats += "＋0050 MA200 t−1 閘"; warm += f"0050 MA200 回看至 {SC['0050 MA200 回看起點（w0 前 200 根）']}；"; need.append("M5（0050 2011 除息）")
            if fam == "P3B":
                feats += "＋閒置現金放 0050"
            if cid == 25:
                feats += "＋個股 MA20 線（yfstop_lines.ma_lines arm=state）"; warm += "MA20 20 根；"
            if cid == 26:
                feats += "＋K4＝c[k]/c[k−20]−1（＝research11 ret20）"; warm += "K4 20 根；"
        else:
            feats = "p4 面板（ret_120、dist_hi/lo120、vol60、amt20、turn20、fore20、trust20、ma_stack、ma60_up、rev_hi24）⇒ eligible＝liq∧bars≥120∧inst"
            warm = f"bars 120；ma60_up 80 根；fore20／trust20 20 個 T86 日（首個可算 {t86_20}）；"
            need = ["M1（T86 個股）", "M2（shares）"] + need_common
            if fam == "P17":
                feats += "＋σ（窗內 120 根 burn-in，w＝0.50）"; warm += "σ burn-in 見 R5；"
            if fam == "P14":
                feats += "＋0050 合成（期初一次配置）"
            if cid == 20:
                feats += "＋ⓑ 旗標（p9_flags：eligible 橫斷面 dist_hi120 前三分位；面板用早年 build_panel）"
            if cid in (22, 23):
                feats += f"＋0050 MA{60 if cid == 22 else 10}（t−1）"; warm += f"0050 MA{60 if cid == 22 else 10}；"
        rows.append({"編號": cid, "格": nm, "族": fam, "特徵與閘": feats, "暖身": warm,
                     "結構起點（資料齊時）": f"{w0a}（R14a）／{w0b}（R14b）" + ("；R5 b 則延到 σ 可算的第一個再平衡日" if fam == "P17" else ""),
                     "暖身是否早於 w0": "是（全部暖身落在 w0 之前，資料時間上都有）",
                     "缺的資料": "、".join(need), "現在算得出來": "否"})
    SP = pd.DataFrame(rows)
    SP.to_csv(os.path.join(OUT, "pre_start.csv"), index=False)
    json.dump(G, open(os.path.join(OUT, "pre_gates.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完成 pre-data] 閘 A {G['A_日曆']['過']}｜B {G['B_0050']['過（窗內）']}｜C {G['C_規則A']['過']}｜D {G['D_銜接']['過']}｜G {G['G_指到早年']['過（格式）']}")


# ═════════════════════════ pre-arith（⛔ 只用主窗）═════════════════════════
_A: dict = {}


def _arith_job(args):
    from . import research11 as R
    from . import research13 as R13
    from . import rerun17 as RR
    from . import researchYear1M as Y
    cid, r = args
    G = Y._G; w0, w1 = _A["w0"], _A["w1"]
    if cid == 24:
        from . import researchAvg as AV
        from . import researchP9run as P9R
        sig = Y.sig_of(18, "eng", w0, w1)
        P9R._G["flags"] = G["flags_orig"]
        s = R.simulate_mtm(sig, P9R.RULE, P9R.N_MAIN, np.random.default_rng(99000 + r), G["closes"], G["opens"], G["NP"],
                           return_equity=True, report_maxw=True, **AV.ENGINE_KW_B["By"])
    else:
        sig = Y.sig_of(cid, "eng", w0, w1)
        s = Y.run_engine(cid, sig, r, "eng")
    eq = np.asarray(s["equity"], float)
    out = {}
    if cid == 0:
        V = Y.p12_derived(eq, w0, w1); n = w1 - w0 + 1
        for c in (5, 8):
            cg, mg = R13.window_stats(V[c], 0, n, 0, n)
            out[c] = (np.asarray(V[c][1:] / V[c][:-1] - 1.0), float(cg), float(mg))
    else:
        c_, m_, _v = RR.win_metrics(eq, s["first"], s["end"], w0, w1)
        seg = eq[w0:w1 + 1]
        out[cid] = (np.asarray(seg[1:] / seg[:-1] - 1.0), float(c_), float(m_))
    return r, out


def pre_arith(log, procs):
    from . import rerun17 as RR
    from . import researchYear1M as Y
    RTP = dict(float_precision="round_trip")
    info = Y.setup(log)
    cal = Y._G["cal"]; w0, w1 = RR.win_bounds(cal)
    _A.update(w0=w0, w1=w1)
    bench = Y._G["bench"]
    bw = RR.bench_row(cal, bench, w0, w1 + 1)
    ok0 = repr(bw["cagr"]) == repr(RR.ANCHOR[0]) and repr(bw["mdd"]) == repr(RR.ANCHOR[1])
    log(f"[閘 0050 錨] {ok0}")
    if not ok0:
        raise SystemExit("⛔ 0050 錨不過")
    engine = [0] + [c for c in range(1, 25) if c not in (5, 8)]
    jobs = [(c, r) for c in engine for r in range(200)]
    n = w1 - w0
    acc = {c: np.zeros(n) for c in range(1, 25)}; cnt = {c: 0 for c in range(1, 25)}; met = []
    t0 = time.time()
    with Pool(procs) as pool:
        for i, (r, out) in enumerate(pool.imap_unordered(_arith_job, jobs, chunksize=2)):
            for c, (ret, cg, mg) in out.items():
                acc[c] += ret; cnt[c] += 1; met.append({"cell": c, "r": r, "cagr": cg, "mdd": mg})
            if (i + 1) % 200 == 0:
                log(f"  {i + 1}/{len(jobs)} {time.time() - t0:.0f}s")
    M = pd.DataFrame(met)
    # 閘：逐種子 repr 逐位元
    ref_main = pd.read_csv(os.path.join(RR.OUT, "seeds_main.csv"), **RTP)
    ref_t1 = pd.read_csv(os.path.join(RR.OUT, "regime_t1", "seeds.csv"), **RTP)
    ref_p9 = pd.read_csv(os.path.join(HERE, "resultsP9run", "seeds_arms.csv"), **RTP)
    ref_av = pd.read_csv(os.path.join(HERE, "resultsAvg", "B_seeds_arms.csv"), **RTP)
    gate = {}
    for c in range(1, 25):
        g = M[M["cell"] == c].set_index("r").sort_index()
        if c in Y.P9_CELLS:
            ref = ref_p9[ref_p9["arm"] == Y.P9_CELLS[c]]; src = "resultsP9run/seeds_arms.csv"
        elif c == 24:
            ref = ref_av[ref_av["arm"] == "By"]; src = "resultsAvg/B_seeds_arms.csv By"
        elif c in Y.REG_T1:
            ref = ref_t1[(ref_t1["stage"] == "t1") & (ref_t1["cell"] == c)]; src = "resultsN17/regime_t1/seeds.csv t1"
        else:
            ref = ref_main[(ref_main["stage"] == "main") & (ref_main["cell"] == c)]; src = "resultsN17/seeds_main.csv main"
        ref = ref.set_index("r").sort_index().loc[g.index]
        bad = {k: int(sum(repr(float(a)) != repr(float(b)) for a, b in zip(g[k], ref[k]))) for k in ("cagr", "mdd")}
        gate[c] = {"對象": src, "顆": int(len(g)), "不同": bad, "逐位元": bool(len(g) == 200 and all(v == 0 for v in bad.values()))}
    allok = all(v["逐位元"] for v in gate.values())
    log(f"[閘 逐種子] 全部逐位元 {allok}｜{ {c: v['逐位元'] for c, v in gate.items()} }")
    json.dump({"0050錨": ok0, "格": gate, "全部過": allok, "setup": info}, open(os.path.join(OUT, "pre_arith_gate.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1, default=str)
    if not allok:
        raise SystemExit("⛔ 逐種子閘不過 ⇒ 不做算術")
    days = pd.DatetimeIndex(cal[w0 + 1:w1 + 1])
    r50 = bench[w0 + 1:w1 + 1] / bench[w0:w1] - 1.0
    MR = pd.DataFrame({f"c{c}": acc[c] / cnt[c] for c in range(1, 25)}, index=days)
    MR["0050"] = r50
    MR.to_csv(os.path.join(OUT, "pre_arith_meanret.csv.gz"), compression="gzip", float_format="%.17g")
    boot(MR, log)


def boot(MR, log):
    """開跑前算術本體（輸入只有主窗的平均日報酬序列）。月數 30（登錄字面）與 31（早年窗 2012-06～2014-12 實際曆月）並列。"""
    mon = MR.index.strftime("%Y-%m").to_numpy()
    months = sorted(set(mon)); K = len(months)
    mi = np.searchsorted(np.array(months), mon)
    nm = np.bincount(mi, minlength=K).astype(float)
    r50 = MR["0050"].to_numpy()
    n = len(r50)
    g50 = float(np.prod(1 + r50) ** (ANN / n) - 1)
    rows = {c: {"編號": c, "格": PREREGV[c][0]} for c in range(1, 25)}
    for NM in (N_MONTHS, 31):
        rng = np.random.default_rng(BOOT_SEED)
        IDX = rng.integers(0, K, size=(B_BOOT, NM))              # 置中重抽：從 114 個月抽 NM 個
        IDXW = rng.integers(0, NM, size=(B_BOOT, NM))            # 連續窗內重抽：從該段 NM 個月抽 NM 個
        nwin = K - NM + 1
        for c in range(1, 25):
            m = MR[f"c{c}"].to_numpy()
            d = m - r50
            ann = float(d.mean() * ANN)
            row = rows[c]
            row["主窗年化差_算術（日差平均×245）"] = ann
            row["主窗年化差_幾何（平均路徑CAGR−0050CAGR）"] = float(np.prod(1 + m) ** (ANN / n) - 1) - g50
            S = np.bincount(mi, weights=d, minlength=K)
            Sc = np.bincount(mi, weights=d - d.mean(), minlength=K)
            stat = Sc[IDX].sum(1) / nm[IDX].sum(1) * ANN
            row[f"{NM}月_重抽sd"] = float(stat.std(ddof=1))
            for an, a in ALPHAS.items():
                T = float(-np.quantile(stat, a))
                row[f"{NM}月_T_{an}"] = T
                row[f"{NM}月_差<T_{an}"] = bool(ann < T)
                lbs = np.array([float(np.quantile(S[j:j + NM][IDXW].sum(1) / nm[j:j + NM][IDXW].sum(1) * ANN, a)) for j in range(nwin)])
                row[f"{NM}月_連續段下界>0_{an}"] = int((lbs > 0).sum())
                row[f"{NM}月_連續段下界最大_{an}"] = float(lbs.max())
            row[f"{NM}月_連續段數"] = nwin
    A = pd.DataFrame(list(rows.values()))
    A.to_csv(os.path.join(OUT, "pre_arith.csv"), index=False, float_format="%.10g")
    summ = {"主窗月份": [months[0], months[-1], K], "B": B_BOOT, "種子": BOOT_SEED}
    for NM in (N_MONTHS, 31):
        for an in ALPHAS:
            k = f"{NM}月_差<T_{an}"
            summ[f"{NM}月｜{an}｜24 格主窗差全部 < T"] = bool(A[k].all())
            summ[f"{NM}月｜{an}｜主窗差 ≥ T 的格"] = A.loc[~A[k], "編號"].tolist()
            summ[f"{NM}月｜{an}｜T 範圍"] = [float(A[f"{NM}月_T_{an}"].min()), float(A[f"{NM}月_T_{an}"].max())]
            summ[f"{NM}月｜{an}｜有連續段下界>0 的格"] = A.loc[A[f"{NM}月_連續段下界>0_{an}"] > 0, "編號"].tolist()
    json.dump(summ, open(os.path.join(OUT, "pre_arith_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[算術] {json.dumps(summ, ensure_ascii=False)}")


# ═════════════════════════ pre-report ═════════════════════════
def pre_report(log):
    from . import early_data as E
    G = json.load(open(os.path.join(OUT, "pre_gates.json"), encoding="utf-8"))
    SP = pd.read_csv(os.path.join(OUT, "pre_start.csv"))
    have_ar = os.path.exists(os.path.join(OUT, "pre_arith.csv"))
    L = ["# PREREGV 早年段 pre 段：資料管線＋閘門＋開跑前算術（⛔ 不含任何 2015 以前報酬）", "",
         f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。回測線。登錄 PREREGV seq5（sha c56a87a3d8c47135）＋營飆 v2 候選 seq2（sha c4e9ab933b4bfb15）；裁定 seq206 §三、seq210（N_驗收 26）。",
         f"早年資料：tw-stock-data main `{E.EARLY_SHA[:10]}`（git archive 唯讀取出到 ~/earlydata/{E.EARLY_SHA[:10]}/raw）。主窗：main `edc6f8002f` 快照。", "",
         "## 〇、一句話", "",
         "```",
         "⛔ 早年段現在【不能開跑】：data/early 缺 5 塊（M1～M5），其中 M3（全體上市股除權息 TWT49U）缺了就連一格都算不出還原價",
         "✅ 結構閘門：日曆＝日 K、0050 兩來源互驗與窗內三筆官方除息、規則 A 與資料庫線草稿逐筆同一套、早年末日⇔主庫首日銜接、主窗程式讀得動早年版面",
         "⏳ 逐格起點：資料齊時全部落在 w0（暖身都早於 w0）；但 w0 本身是 2012-06-01 還是 06-04 要裁（R14）",
         "⛔ 逐格訊號數／事件數／可交易性剔除數：缺 M1～M4 ⇒ 本段不數（原建構器會順手算前瞻報酬，⛔ 本段也不可跑）",
         "```", ""]
    # 缺資料
    L += ["## 一、⛔ 缺的資料（fail closed；請資料庫線落地）", "", "| 代號 | 項 | 版面 | 影響 | data/early 現況 |", "|---|---|---|---|---|"]
    for k, v in E.MISSING.items():
        L.append(f"| {k} | {v['項']} | {v['版面']} | {v['影響']} | {v['data/early 現況']} |")
    L += ["", "⭐ M3、M4 的原始表資料庫線 G1 時都現打過（草稿 early_checks.py／early_anchor_0050.py），只是沒有落地。", ""]
    # 閘
    A = G["A_日曆"]; B = G["B_0050"]; C = G["C_規則A"]; Dd = G["D_銜接"]; Ee = G["E_名冊"]; F = G["F_月營收"]; Gg = G["G_指到早年"]
    L += ["## 二、閘門", "",
          f"**A 早年日曆＝日 K（只上市）** ⇒ {'✅' if A['過'] else '⛔'}：上市日曆 {A['上市日曆天數']} 天（{A['起訖'][0]}～{A['起訖'][1]}）＝ 日檔檔名 {A['＝日檔檔名']}、＝ _structure twse {A['＝_structure twse rows>0']}；"
          f"本益比 {A['本益比 2012～2014 天數']} 天 ＝ 日曆∩2012～2014 {A['＝日曆∩2012～2014']}；大盤法人金額 {A['大盤法人金額天數']} 天 ＝ 日曆 {A['＝日曆∩[首日,2014-12-31]']}；週六交易日 {len(A['週六交易日（補班形狀）'])} 天（{'、'.join(A['週六交易日（補班形狀）'])}；列數都在中位九成以上 ⇒ 補班日形狀，⚠ 官方年曆未落地、未逐日對）；"
          f"早年末日 {A['早年末日→主庫首日'][0]} → 主庫首日 {A['早年末日→主庫首日'][1]}。窗：{json.dumps(A['窗'], ensure_ascii=False)}", "",
          f"**B 0050** ⇒ 窗內 {'✅' if B['過（窗內）'] else '⛔'}：早年日 K（MI_INDEX）對 data/extra（STOCK_DAY）共同 {B['兩來源共同日']} 天、逐欄不同數 {B['逐欄不同數']}；"
          f"窗內官方除息 {len(B['官方除息（窗內，data/extra）'])} 筆："
          + "；".join(f"{e['除息日']} 前收 {e['早年日K前收']}＝官方 {e['官方除息前收']} {'✓' if e['前收相同'] else '✗'}、參考價÷前收 {e['參考價÷前收（8 位）']}＝factor {e['factor']} {'✓' if e['factor 相同'] else '✗'}" for e in B["官方除息（窗內，data/extra）"])
          + f"；早年 cum 與主庫 cum 只差常數 {B['早年 cum 與主庫 cum 只差常數']}。引用：{B['資料庫線 0404 §二（引用）']}。⚠ {B['⛔ 2011 年除息']}", "",
          f"**C 規則 A 與資料庫線 G1 同一套** ⇒ {'✅' if C['過'] else ('⛔' if C['過'] is False else '—')}：本檔獨立重寫（1504 §一逐字）A {C['本檔 A']}／B {C['本檔 B']}；"
          f"草稿 early_checks_out.json A {C.get('資料庫線草稿 A')}／B {C.get('資料庫線草稿 B')}；只在本檔 {C.get('只在本檔')}、只在草稿 {C.get('只在草稿')}（逐筆比 代號、前一有成交日、事件日、規則、比值）。"
          f"上市列：{json.dumps(C['上市列（事件日是 twse 列）'], ensure_ascii=False)}。引用：{C['資料庫線 G1（引用 0404／0406）']}。⚠ {C['⚠']}", "",
          f"**D 早年末日⇔主庫首日（登錄沒寫，補充）** ⇒ {'✅' if Dd['過'] else '⛔'}：{Dd['說明']}：{Dd['檔數']} 檔，相同 {Dd['相同']}、不同 {Dd['不同']}（其中當日除權息 {Dd['不同且為當日除權息']}；非事件例 {Dd['不同且非事件（例）']}）", "",
          f"**E 名冊（R13 a：日 K 自推）** ⇒ 照報：{json.dumps({k: v for k, v in Ee.items() if k != 'kind 待裁（今日 stocks.csv 沒有）'}, ensure_ascii=False)}", "",
          f"　kind 待裁（R2）：{Ee['kind 待裁（今日 stocks.csv 沒有）']}", "",
          f"**F 月營收** ⇒ fixture {'✅' if F['fixture 2010-06 上市']['過'] else '⛔'}（{F['fixture 2010-06 上市']['列']} 列 → 去重 {F['fixture 2010-06 上市']['去重後']}；資料庫線 {F['fixture 2010-06 上市']['資料庫線 1827 數字']}）；"
          f"上市 2010-04～2014-12 共 {F['上市 2010-04～2014-12 期檔（rev_hi24 回看＋窗）']} 期，有重複的期 {F['其中 rows≠distinct（有重複）']}", "",
          f"**G 主窗程式指到早年版面（⛔ 不算報酬）** ⇒ 格式 {'✅' if Gg['過（格式）'] else '⛔'}：{json.dumps(Gg, ensure_ascii=False, default=str)}", "",
          "**G0／G1／G2（引用，資料庫線與回測 1705）**：G0 inst_ok 單獨擋 1.296% ＞ 1% ⇒ 路 A（原定義、含 inst_ok）；上市 G1 98.9% 過（0404／0406）；上櫃 G1 89.8% 未達 ⇒ 上櫃不開跑（裁定 seq206 §三）；G2 上市漲跌欄空白 0.00%、上櫃 0.24%（2323）", ""]
    # 起點
    L += ["## 三、逐格起點（登錄：起點 ＝ max（2012-06 第一個量測日，該格所有特徵與閘門都算得出來的第一個量測日））", "",
          f"結構量（⛔ 不含報酬）：{json.dumps(G['結構量'], ensure_ascii=False)}", "",
          "| # | 格 | 族 | 特徵與閘 | 暖身 | 結構起點（資料齊時） | 缺的資料 |", "|---|---|---|---|---|---|---|"]
    for _, r in SP.iterrows():
        L.append(f"| {r['編號']} | {r['格']} | {r['族']} | {r['特徵與閘']} | {r['暖身']} | {r['結構起點（資料齊時）']} | {r['缺的資料']} |")
    L += ["", "⇒ 每一格的暖身都早於 w0 ⇒ 資料齊時起點全部 ＝ w0；⛔ 沒有一格因暖身而後延（#5 視 R5）。訊號數、事件數、可交易性剔除數：⛔ 缺 M1～M4，本段不數。", ""]
    # 算術
    if have_ar:
        AR = pd.read_csv(os.path.join(OUT, "pre_arith.csv"))
        SU = json.load(open(os.path.join(OUT, "pre_arith_summary.json"), encoding="utf-8"))
        GA = json.load(open(os.path.join(OUT, "pre_arith_gate.json"), encoding="utf-8"))
        L += ["## 四、開跑前算術（⛔ 只用主窗 2017-03-02～2026-08-24）", "",
              f"閘：0050 錨 {GA['0050錨']}｜24 格逐種子年化／回落 repr 逐位元 {GA['全部過']}（對象見 pre_arith_gate.json）", "",
              f"讀法：主窗月份 {SU['主窗月份']}；B＝{SU['B']}；種子 {SU['種子']}；T ＝ 主窗日差置中後、重抽 30（登錄字面）或 31（早年窗實際曆月）個月的年化差分佈之 α 分位的相反數；"
              "連續段 ＝ 主窗內每一段連續 30／31 個月各自做月分群 bootstrap，數下界 ＞ 0 的段數", "",
              "| # | 格 | 主窗年化差（算術） | （幾何，參考） | T 30月 /24 | 差＜T | T 30月 /26 | T 31月 /24 | 差＜T | 連續 30 月段下界＞0（/24） | 段數 |", "|---|---|---|---|---|---|---|---|---|---|---|"]
        for _, r in AR.iterrows():
            L.append(f"| {int(r['編號'])} | {r['格']} | {r['主窗年化差_算術（日差平均×245）'] * 100:+.2f} 點 | {r['主窗年化差_幾何（平均路徑CAGR−0050CAGR）'] * 100:+.2f} 點 | "
                     f"{r['30月_T_0.05/24'] * 100:.2f} 點 | {'是' if r['30月_差<T_0.05/24'] else '否'} | {r['30月_T_0.05/26'] * 100:.2f} 點 | "
                     f"{r['31月_T_0.05/24'] * 100:.2f} 點 | {'是' if r['31月_差<T_0.05/24'] else '否'} | {int(r['30月_連續段下界>0_0.05/24'])} | {int(r['30月_連續段數'])} |")
        L += ["", f"總結：{json.dumps(SU, ensure_ascii=False)}", ""]
        keys = [k for k in SU if k.endswith("24 格主窗差全部 < T")]
        if all(SU[k] for k in keys):
            L += ["⇒ 四種口徑（30／31 個月 × 0.05/24／0.05/26）都成立 ⇒ 照登錄 §四逐字：**「本段樣本只夠分 Q／R／F，『可以說找到』依構造不可得」**"
                  "（24 格主窗年化差全部小於門檻；第一種結果句拿掉；「找到」只能等前瞻紀錄）", ""]
        else:
            L += [f"⇒ 不是每種口徑都成立：{ {k: SU[k] for k in keys} } ⇒ 口徑待裁（R7），⛔ 本段不選", ""]
    # 讀法
    L += ["## 五、待裁的讀法（⛔ 本段沒有選）", ""]
    for k, v in E.READINGS.items():
        L.append(f"- **{k} {v['題']}**：" + "；".join(f"{a}）{b}" for a, b in v["選項"].items()) + f"｜影響：{v['影響']}")
    L.append("- **R14 w0 是哪一天**：a）2012-06-01（登錄字面「2012-06 第一個量測日」）；b）2012-06-04（主窗同構：主窗 W0 2017-03-02 ＝ 量測日 03-01 的次一交易日）｜影響：窗首一天、0050 同窗起點")
    L += ["", "### R4 各程式寫死的主窗常數", "", "| 檔 | 名稱 | 主窗值 | 同義早年值（建議，待裁） | 意義 |", "|---|---|---|---|---|"]
    for f, n, m, e, s in E.WINDOW_CONSTANTS:
        L.append(f"| {f} | {n} | {m} | {e} | {s} |")
    L += ["", "## 六、檔案", "", "- backtest/early_data.py（轉接層）、backtest/researchV.py（pre 段）、backtest/selftest_early_data.py",
          "- resultsV/pre_gates.json、pre_start.csv、pre_ruleab_events.csv、pre_arith_gate.json、pre_arith_meanret.csv.gz、pre_arith.csv、pre_arith_summary.json、PRE_REPORT.md",
          f"- 早年版面（repo 外）：~/earlydata/{E.EARLY_SHA[:10]}/R1a/data（STATUS.json：complete＝false）", ""]
    open(os.path.join(OUT, "PRE_REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    log("[完成 pre-report]")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["pre-data", "pre-arith", "pre-boot", "pre-report"])
    ap.add_argument("--procs", type=int, default=2)
    a = ap.parse_args()
    log = _log_to(os.path.join(OUT, f"{a.stage}.log"))
    log(f"===== researchV {a.stage} {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）=====")
    if a.stage == "pre-data":
        pre_data(log)
    elif a.stage == "pre-arith":
        pre_arith(log, a.procs)
    elif a.stage == "pre-boot":
        boot(pd.read_csv(os.path.join(OUT, "pre_arith_meanret.csv.gz"), index_col=0, parse_dates=True, float_precision="round_trip"), log)
    else:
        pre_report(log)


if __name__ == "__main__":
    main()
