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




# ═════════════════════════════════════════════════════════════════════════════════════
# ═════════ 本體段（裁定 seq218 §四；登錄 PREREGV seq6 sha 445338e8a06bbac8＋營飆v2候選 seq3 sha d37771f84327dfb0）═════════
# ═════════════════════════════════════════════════════════════════════════════════════
"""
    ... -m backtest.researchV body-sig --layout main|restore [--procs 3]   # 早年訊號（AND 四步＋門檻B 面板）⇒ ~/earlydata/<sha10>/sig_<layout>/
    ... -m backtest.researchV body-gate [--procs 3]                        # #25／#26 包裝在主窗逐位元對 resultsYfV2（20 顆）
    ... -m backtest.researchV body-run [--procs 3]                         # 26 格 × 200 顆 × 5 版本＋假訊號臂＋控制臂（一次跑完）
    ... -m backtest.researchV body-table                                   # 彙總、判定、REPORT.md

版本（⭐ 看任何結果前寫死）：
  main     判定版：窗 2012-06-04～2014-12-31（R14）、只上市（R1）、原定義 eligible（含 inst_ok）、T1 補回（R3 主版）、官方減資 R8 截斷
  eng      描述：同 main，但 R3 引擎原樣（資料尾截斷的訊號整筆丟）
  noT      描述（R1 敏感度）：同 main，剔除 63 檔轉上市股（有上市前上櫃列者）的所有訊號
  restore  描述版（登錄 §三）：減資因子接進還原鏈、⛔ 不做 R8 剔除（另一份版面與訊號）
  desc     描述段：窗 2008-01-03～2012-05-31、只上市、eligible_v ＝ liq_ok ∧ bars_ok、事件 ＝ 官方 ∪ 規則 A ∪ 規則 B（扣除權息）；處置資料 2010-12-14 起
格與引擎：#1～#23 ＝ researchYear1M.run_engine（程式逐字＝rerun17／regime_t1／researchP9run；pre-arith 閘已逐種子驗 24 格）；
  #24 ＝ researchAvg.ENGINE_KW_B["By"]；#25 ＝ yfstop_lines.ma_lines(20, arm="state")＋stop_line_le=False（無 stop_proceeds）；
  #26 ＝ pick="K4"、pick_tie="rng"；#25、#26 的底 ＝ #1（AND、t−1 閘、10 槽、H120、種子 1000＋r）
判定（登錄 §四）：年化中位、回落中位（200 顆）⇒ 比值 ＝ 年化中位 ÷ |回落中位|；#5／#8 取 P12 路徑合成（rerun17 同式）；
  Q／R／F ＝ rerun17_table.label；下界 ＝ 26 格各自：200 顆逐日平均報酬 − 0050 逐日報酬，月分群 bootstrap B＝20,000，α＝0.05／26 分位（未置中）
  #25：對 0050 標籤 ＋ 對 #1 同種子（年化差、回落差）皆正 ≥ 190 ⇒ 好；皆負 ≥ 190 ⇒ 差；其餘分不出
  #26：先報退化量（0 ＜ 空槽 ＜ 候選的日數中位；＜ 20 ⇒ 依構造不可判定）；可判定 ⇒ 年化中位在 #1 200 顆逐顆年化的百分位、逐顆比值中位在 #1 逐顆比值的百分位，
       兩者 ≥ 98.75 好、≤ 1.25 差（中位秩；researchYfRank.pctl）；K0 落 10～90 以外 ⇒ 句前警語
假訊號臂（⛔ 不進判定，只決定措辭；x／次數 ≥ 5% ⇒「⚠ 隨機也有 x 合格」）：
  P10 族 #1 #4 #7 #12 #15 #16 #17（原件 research13）：S 內隨機抽 |AND| 筆（default_rng(13) 連抽 200 次），各配 1000＋j 一條路徑，照格的閘與規則跑
  P1 族 #3 #6 #9 #11 #13 #14（登錄）：每個訊號月從 S 同月列抽與 AND 同數（default_rng(20260925＋r)），引擎 7000＋r
  P3 乙 #2 #10（原件 researchp3 丙1）：同顆種子的甲（閒置 0 報酬）曝險序列環形平移 200 次（default_rng(9000＋k)），每次取 200 顆中位判
  #5（原件 P17 W_shuf）：R_eq 權重時序打亂 30 次（default_rng(108000＋r) 連抽），每次取 200 顆中位判
  #8：權重恆 0.50 ⇒ 打亂等於原樣 ⇒ 依構造退化，⛔ 不做（照報）
  #22 #23（原件 P9）：0050 均線狀態線上／線下段各自打亂 30 次（default_rng(20260925＋j)）× 50 顆，每次取 50 顆中位判
  #26：K0（代號尾數）；#25：控制臂 C1（隨機賣出＋整份；早年段 #25 的 p 與觸發根分佈，rng [1000＋r, 1]）、C2（M20＋stop_proceeds="next"）
"""
SIG_START, SIG_END = "2005-02-01", "2014-12-31"          # R4：research34 訊號位置（主窗 2016-01-04＝資料起點後約一年；早年同義）
PANEL_START, PANEL_END = "2004-01-01", "2014-12-31"      # R4：門檻B 面板量測日（主窗從資料起點）
B_START = "2004-01-01"                                   # R4：build_sig_gate_b start（主窗 2017-01-01 是主窗專用；早年由窗過濾）
W_MAIN = ("2012-06-04", "2014-12-31")
DESC_MONTHS = ("2008-01", "2012-05")
N_V = 26
ALPHA_V = 0.05 / N_V
VARIANTS = ["main", "eng", "noT", "restore", "desc"]
REG_T1 = {1, 4, 7, 16, 17}
P10_CELLS = [1, 4, 7, 12, 15, 16, 17]
P1_CELLS = [3, 6, 9, 11, 13, 14]
P3B_CELLS = [2, 10]
P9_KEYS = {18: "A2", 19: "Ba", 20: "Bb", 21: "Bc", 22: "Cc", 23: "Ce"}
CRASH = {"2008-05～2008-11": ("2008-04", "2008-11"), "2011-08～2011-12": ("2011-07", "2011-12")}
_B: dict = {}


def body_paths(layout):
    from . import early_data as E
    return os.path.join(E.snap_dir(E.BODY_SHA), layout, "data"), os.path.join(E.snap_dir(E.BODY_SHA), f"sig_{layout}")


def use_layout(layout):
    from . import data as D
    from . import early_data as E
    E.body_build(variant=layout)
    D.DATA = body_paths(layout)[0]
    return D.DATA


# ═════════════ body-sig：早年訊號（呼叫原程式的函式，逐步照 rerun17_build＋researchAFC_panel）═════════════
def body_sig(layout, procs, log):
    from multiprocessing import Pool
    from . import data as D
    from . import patterns as PT
    from . import research11 as R
    from . import research13 as R13
    from . import research34 as R34
    from . import researchp1 as P1
    from . import researchp4 as RP4
    from . import p4_features as P
    from . import universe_gate as UG
    use_layout(layout)
    out = body_paths(layout)[1]
    os.makedirs(out, exist_ok=True)
    t0 = time.time()
    cal = D.load_calendar()
    stocks = pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(stocks)
    uni = D.load_universe().merge(U[["stock_id"]], on="stock_id")
    log(f"[body-sig {layout}] D.DATA {D.DATA}｜日曆 {len(cal)}（{cal[0].date()}～{cal[-1].date()}）｜母體 {len(uni)}")
    PT.PARAMS["liq_mode"] = "shares"
    bdf = D.load_benchmark(cal)
    bench = {"o": bdf["open"].to_numpy(float), "c": bdf["close"].to_numpy(float)}
    disp = D.load_disposal_intervals()
    rev, rev_ly, ind = R34.load_revenue()
    rdates = R34.rebalance_dates(list(rev.index), cal, 10)
    lo = int(cal.searchsorted(pd.Timestamp(SIG_START))); hi = int(cal.searchsorted(pd.Timestamp(SIG_END), side="right") - 1)
    jobs = list(zip(uni["stock_id"], uni["market"], uni["first_seen"], uni["last_seen"]))
    rows = []
    with Pool(procs, initializer=R34._init, initargs=(cal, bench, disp, rev, rev_ly, rdates, lo, hi)) as pool:
        for r in pool.imap_unordered(R34.process_stock, jobs, chunksize=8):
            if r:
                rows += r
    panel = pd.DataFrame(rows)
    for c in ("rev_hi12", "rev_hi24", "rev_hi36", "bull"):
        if c in panel:
            panel[c] = panel[c].astype("boolean")
    panel["signal_date"] = [cal[i].strftime("%Y-%m-%d") for i in panel["signal_pos"]]
    panel["entry_date"] = [cal[i].strftime("%Y-%m-%d") for i in panel["entry_pos"]]
    panel.to_csv(os.path.join(out, "panel_rev.csv.gz"), index=False, compression="gzip")
    log(f"[①營收面板] {len(panel):,} 列｜營收 {rev.shape[0]} 期（{rev.index.min()}～{rev.index.max()}）｜訊號窗 {cal[lo].date()}～{cal[hi].date()}｜{time.time() - t0:.0f}s")
    tasks = [(r.stock_id, r.market, r.first_seen) for r in uni.itertuples()]
    main_rows = []
    with Pool(procs, initializer=R._init, initargs=(cal,)) as pool:
        for r in pool.imap_unordered(R.stock_features, tasks, chunksize=8):
            if r is not None:
                main_rows.extend(r["main"])
    S_full = pd.DataFrame(main_rows)
    S_full.to_csv(os.path.join(out, "signals_S_full.csv.gz"), index=False)
    pnl = pd.read_csv(os.path.join(out, "panel_rev.csv.gz"), dtype={"stock_id": str})
    pnl["rev_hi24"] = pnl["rev_hi24"].fillna(False).astype(bool)
    S = pd.read_csv(os.path.join(out, "signals_S_full.csv.gz"), dtype={"sid": str})
    S = S[["sid", "k", "pos", "entry_pos", "month", "g_H60", "g_H120", "g_LD", "xpos_H60", "xpos_H120", "xpos_LD", "t_LD"]].copy()
    flags, _ = R13.and_flags(S, pnl)
    AND = S[flags].copy()
    missing, mism = P1.attach_features(AND, S, cal, uni.set_index("stock_id")["market"], procs)
    if mism:
        raise SystemExit("⛔ k 與 pos 對不上")
    AND.to_csv(os.path.join(out, "and_signals.csv.gz"), index=False)
    S.to_csv(os.path.join(out, "signals_S.csv.gz"), index=False)
    log(f"[②③④] S {len(S):,}｜AND {len(AND):,}／{AND['sid'].nunique()} 檔｜relvol 缺 {int(AND['relvol'].isna().sum())}｜讀不到 {len(missing)}｜{time.time() - t0:.0f}s")
    positions = P.measurement_days(cal, PANEL_START, PANEL_END)
    pan, M = RP4.build_panel(cal, uni, positions, procs=procs, log=lambda s: None)
    if len(M):
        M.to_csv(os.path.join(out, "min_periods_mismatch.csv"), index=False)
        raise SystemExit("⛔ min_periods 常設斷言不成立")
    pan.to_csv(os.path.join(out, "panel.csv.gz"), index=False)
    info = {"layout": layout, "data": D.DATA, "母體": int(len(uni)), "營收面板列": int(len(panel)), "S": int(len(S)), "AND": int(len(AND)),
            "門檻B面板列": int(len(pan)), "eligible": int(pan["eligible"].sum()), "量測日": [str(cal[positions[0]].date()), str(cal[positions[-1]].date()), int(len(positions))],
            "SIG": [str(cal[lo].date()), str(cal[hi].date())], "秒": round(time.time() - t0)}
    json.dump(info, open(os.path.join(out, "INFO.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[⑤門檻B面板] {json.dumps(info, ensure_ascii=False)}")


# ═════════════ R8：減資事件的訊號剔除與持有截斷 ═════════════
def apply_events(tbl, E, cal, kind, px=None):
    """kind＝"AND"（訊號日＝pos；xpos／g 三組 H60／H120／LD，g 用 D.load_stock 還原價重算）或 "B"（訊號日＝entry_pos−1；xpos_H120／g_H120 用引擎價）。
    回 (新表, 計數)。E：stock_id, e, L（日期字串）。"""
    from . import data as D
    pos = {d.strftime("%Y-%m-%d"): i for i, d in enumerate(cal)}
    T = tbl.copy()
    sd = T["pos"].to_numpy() if kind == "AND" else T["entry_pos"].to_numpy() - 1
    drop = np.zeros(len(T), bool); n_short = {}
    ev = {}
    for s, e, L in zip(E["stock_id"], E["e"], E["L"]):
        if e in pos and L in pos:
            ev.setdefault(s, []).append((pos[e], pos[L]))
    sid = T["sid"].to_numpy()
    for s, lst in ev.items():
        m = sid == s
        if not m.any():
            continue
        for pe, pL in lst:
            drop |= m & (sd >= pe - 5) & (sd <= pe + 60)
    T = T[~drop].copy()
    cols = [("xpos_H60", "g_H60"), ("xpos_H120", "g_H120"), ("xpos_LD", "g_LD")] if kind == "AND" else [("xpos_H120", "g_H120")]
    cache = {}
    short_keys = set()
    for s, lst in ev.items():
        idx = np.flatnonzero(T["sid"].to_numpy() == s)
        if not len(idx):
            continue
        for pe, pL in lst:
            for i in idx:
                e_ = int(T.iloc[i]["entry_pos"])
                for xc, gc in cols:
                    x_ = int(T.iloc[i][xc])
                    if x_ < 0 or not (e_ <= pL and x_ >= pe):
                        continue
                    if kind == "AND":
                        if s not in cache:
                            st = D.load_stock(s, "twse", cal)
                            cache[s] = (st.df["open"].to_numpy(float), st.df["close"].to_numpy(float))
                        o_, c_ = cache[s]
                        g = c_[pL] / o_[e_] - 1.0
                    else:
                        g = float(px[0][s][pL]) / float(px[1][s][e_]) - 1.0
                    T.iat[i, T.columns.get_loc(xc)] = pL
                    T.iat[i, T.columns.get_loc(gc)] = g
                    n_short[xc] = n_short.get(xc, 0) + 1
                    short_keys.add((s, e_))
    return T, {"事件（在日曆內）": sum(len(v) for v in ev.values()), "訊號日落在 [e−5,e+60] 刪除": int(drop.sum()),
               "持有跨事件改在 L 了結": n_short, "_short_keys": sorted(short_keys)}


def sig12_ext(panel, cal, closes, opens, start):
    """researchYear1M.sig12 的同一式，只把 start 換成參數（原件寫死 2017-01-01）。"""
    from . import researchp7 as P7
    ncal = len(cal); EXT = 300
    cal_x = cal.append(pd.bdate_range(cal[-1] + pd.Timedelta(days=1), periods=EXT))
    cx = {s: np.r_[c, np.full(EXT, c[-1], dtype=c.dtype)] for s, c in closes.items()}
    ox = {s: np.r_[o, np.full(EXT, np.nan, dtype=o.dtype)] for s, o in opens.items()}
    sx = P7.build_sig_gate_b(panel, cal_x, cx, ox, start=start, signal="B")
    s0 = P7.build_sig_gate_b(panel, cal, closes, opens, start=start, signal="B")
    keep = sx[sx["xpos_H120"] < ncal].reset_index(drop=True)
    if not keep.equals(s0.reset_index(drop=True)):
        raise SystemExit("⛔ 延伸日曆建出的非截斷列 ≠ 原日曆建出的訊號")
    cen = sx[(sx["xpos_H120"] >= ncal) & (sx["entry_pos"] < ncal)].copy()
    cen["g_H120"] = [float(closes[s][ncal - 1]) / float(opens[s][e]) - 1.0 for s, e in zip(cen["sid"], cen["entry_pos"])]
    cen["xpos_H120"] = ncal
    out = pd.concat([s0, cen], ignore_index=True).sort_values(["entry_pos", "sid"], kind="stable").reset_index(drop=True)
    return s0, out, {"原函式列數": len(s0), "截斷補回": len(cen)}


def win_of(cal, variant):
    if variant == "desc":
        per = pd.DatetimeIndex(cal).strftime("%Y-%m")
        f = int(np.flatnonzero(per == DESC_MONTHS[0])[0]); w0 = f + 1
        w1 = int(np.flatnonzero(per == DESC_MONTHS[1])[-1])
        return w0, w1
    w0 = int(cal.searchsorted(pd.Timestamp(W_MAIN[0]))); w1 = int(cal.searchsorted(pd.Timestamp(W_MAIN[1])))
    assert str(cal[w0].date()) == W_MAIN[0] and str(cal[w1].date()) == W_MAIN[1] and w1 == len(cal) - 1
    return w0, w1


def body_setup(variant, log):
    """把 researchYear1M._G／researchP9run._G 填成早年版（fork 前做）。"""
    from . import data as D
    from . import early_data as E
    from . import p4_features as P4F
    from . import p9_flags as F
    from . import research11 as R
    from . import researchP9run as P9R
    from . import researchYear1M as Y
    from . import rerun17 as RR
    from . import yfstop_lines as YL
    layout = "restore" if variant == "restore" else "main"
    use_layout(layout)
    sdir = body_paths(layout)[1]
    cal = D.load_calendar(); ncal = len(cal)
    uni = D.load_universe().set_index("stock_id")["market"]
    AND = pd.read_csv(os.path.join(sdir, "and_signals.csv.gz"), dtype={"sid": str})
    S = pd.read_csv(os.path.join(sdir, "signals_S.csv.gz"), dtype={"sid": str})
    panel = P4F.read_panel(os.path.join(sdir, "panel.csv.gz"))
    if variant == "desc":
        panel["eligible"] = panel["liq_ok"].astype(bool) & panel["bars_ok"].astype(bool)      # eligible_v（登錄 §一）
    sids = set(AND["sid"]) | set(S["sid"]) | set(panel["stock_id"])
    closes, opens = RR.load_prices(sids, cal, uni, "branch")
    bench = RR.load_bench(cal)
    w0, w1 = win_of(cal, variant)
    info = {"variant": variant, "layout": layout, "D.DATA": D.DATA, "窗": [str(cal[w0].date()), str(cal[w1].date()), w1 - w0 + 1],
            "closes dtype": str(next(iter(closes.values())).dtype)}
    AND_m, cA = Y.and_censor(AND, cal, uni, lambda x: None)
    S_m, cS = Y.and_censor(S, cal, uni, lambda x: None)
    s12_eng, s12_mtm, i12 = sig12_ext(panel, cal, closes, opens, B_START)
    info["T1"] = {"AND": cA, "S": cS, "門檻B": i12}
    # R8
    if variant == "restore":
        EV = None
    else:
        EV = pd.read_csv(os.path.join(E.snap_dir(E.BODY_SHA), "reduce_events.csv"), dtype=str)
        if variant == "desc":
            X = pd.read_csv(os.path.join(E.snap_dir(E.BODY_SHA), "detected_events.csv"), dtype={"stock_id": str, "L": str, "e": str})
            X = X[~X["exright_in_gap"].astype(bool)]
            EV = pd.concat([EV[["stock_id", "e", "L"]], X[["stock_id", "e", "L"]]]).drop_duplicates(["stock_id", "e"])
    ev_info = {}
    if EV is not None:                                      # 被剔除的股-月（門檻B 面板 eligible、量測日次日進場在窗內）
        posd = {d.strftime("%Y-%m-%d"): i for i, d in enumerate(cal)}
        el = panel[panel["eligible"].astype(bool)].copy()
        el["mp"] = el["measure_date"].map(lambda d: posd.get(d.strftime("%Y-%m-%d"), -9))
        el = el[(el["mp"] + 1 >= w0) & (el["mp"] + 1 <= w1)]
        hit = np.zeros(len(el), bool)
        evd = {}
        for s_, e_, l_ in zip(EV["stock_id"], EV["e"], EV["L"]):
            if e_ in posd:
                evd.setdefault(s_, []).append(posd[e_])
        sidv = el["stock_id"].to_numpy(); mpv = el["mp"].to_numpy()
        for s_, lst in evd.items():
            mm = sidv == s_
            for pe in lst:
                hit |= mm & (mpv >= pe - 5) & (mpv <= pe + 60)
        info["R8_股月"] = {"窗內 eligible 股-月": int(len(el)), "落在 [e−5,e+60]": int(hit.sum()), "占比": float(hit.mean()) if len(el) else None,
                          "事件數（窗內恢復日）": int(sum(1 for s_, lst in evd.items() for pe in lst if w0 <= pe <= w1))}
    tabs = {"AND_eng": (AND, "AND"), "AND_mtm": (AND_m, "AND"), "S_mtm": (S_m, "AND"), "s12_eng": (s12_eng, "B"), "s12_mtm": (s12_mtm, "B")}
    T = {}
    short_all = set()
    for k, (t, kind) in tabs.items():
        if EV is None:
            T[k] = t; continue
        T[k], c = apply_events(t, EV, cal, kind, px=(closes, opens))
        short_all |= set(map(tuple, c.pop("_short_keys")))
        ev_info[k] = c
    info["R8"] = ev_info
    if variant == "noT":
        tr = set(json.load(open(os.path.join(E.snap_dir(E.BODY_SHA), "transferred.json"))))
        for k in T:
            T[k] = T[k][~T[k]["sid"].isin(tr)].copy()
        info["noT 剔除檔數"] = len(tr)
    closesP, opensP = Y.pad_px(closes, opens)
    benchP = np.r_[bench, bench[-1]]
    reg = RR.regime_mask(benchP)
    reg_t1 = np.zeros_like(reg); reg_t1[1:] = reg[:-1]
    fl_sids = set(T["s12_mtm"]["sid"]) | set(T["s12_eng"]["sid"])
    fo = F.build_flags(panel, cal, sids=fl_sids)
    flags = {s: np.r_[v, False] for s, v in fo.items()}
    below = {n: R.regime_below(benchP, n) for n in (60, 20, 10)}
    P9R._G.update(below=below, flags=flags)
    Y._G.update(cal=cal, ncal=ncal, NP=ncal + 1, uni=uni, AND_eng=T["AND_eng"], AND_mtm=T["AND_mtm"], s12_eng=T["s12_eng"], s12_mtm=T["s12_mtm"],
                closes=closesP, opens=opensP, bench=bench, benchP=benchP, reg_t1=reg_t1, reg=reg, flags_orig=flags, flags_plus=flags)
    vtag = "eng" if variant == "eng" else "mtm"
    # #25／#26 的訊號（＝ #1 同一組）＋ K4／K0 鍵、M20 線
    s1 = Y.sig_of(1, vtag, w0, w1).copy()
    bars = {}
    def bars_of(s):
        if s not in bars:
            bars[s] = R.load_bars(s, uni.get(s, "twse"), cal)
        return bars[s]
    k4 = []
    for s, k in zip(s1["sid"], s1["k"].astype(int)):
        c = bars_of(s)["c"]
        k4.append(float(c[k] / c[k - 20] - 1.0))
    s1["K4"] = k4
    s1["K0"] = s1["sid"].str[-1].astype(int)
    lines = YL.ma_lines(s1, closesP, bars_of, 20, arm="state")
    V = {}
    for s in set(s1["sid"]):
        v = np.zeros(ncal + 1, bool); v[bars_of(s)["idx"]] = True; V[s] = v
    ent = {}
    for s, e in zip(s1["sid"], s1["entry_pos"].astype(int)):
        ent.setdefault(e, []).append(s)
    _B.clear()
    _B.update(variant=variant, vtag=vtag, cal=cal, ncal=ncal, w0=w0, w1=w1, bench=bench, s1=s1, lines=lines, V=V, ent=ent,
              xmap={(s, int(e)): int(x) for s, e, x in zip(s1["sid"], s1["entry_pos"], s1["xpos_H120"])},
              short_keys=short_all, S_mtm=T["S_mtm"], AND_mtm=T["AND_mtm"])
    info["訊號數（窗內）"] = sig_counts(cal, w0, w1, vtag)
    info["#25 線數"] = len(lines); info["#1 訊號（=#25/#26 底）"] = int(len(s1))
    log(f"[setup {variant}] {json.dumps({k: v for k, v in info.items() if k not in ('R8',)}, ensure_ascii=False, default=str)}")
    return info


def sig_counts(cal, w0, w1, vtag):
    from . import researchYear1M as Y
    out = {}
    for cid in list(range(1, 24)) + [0]:
        if cid in (5, 8):
            continue
        s = Y.sig_of(cid, vtag, w0, w1)
        out[cid] = {"訊號": int(len(s)), "檔": int(s["sid"].nunique())}
    return out


# ── 一顆種子一格 ──
def _metrics(eq, first, end, hv=None, au=None):
    from . import rerun17 as RR
    from . import research13 as R13
    G = _B; w0, w1, cal = G["w0"], G["w1"], G["cal"]
    eq = np.asarray(eq, float)
    c, m, v = RR.win_metrics(eq, first, end, w0, w1)
    seg = eq[w0:w1 + 1]
    row = {"cagr": float(c), "mdd": float(m), "vol": float(v), "first": int(first), "end": int(end)}
    row.update(_path_desc(seg, None if hv is None else np.asarray(hv, float)[w0:w1 + 1]))
    if au is not None:
        yrs = (w1 + 1 - w0) / 245; meq = float(seg.mean())
        buy = sum(float(a["amt"]) for a in au if a["side"] == "buy" and w0 <= int(a["t"]) <= w1)
        cost = sum(float(a.get("cost", 0.0)) for a in au if a["side"] == "sell" and w0 <= int(a["t"]) <= w1)
        row["turnover_yr"] = buy / meq / yrs; row["cost_yr"] = cost / meq / yrs
        sk = G["short_keys"]
        row["short_settled"] = sum(1 for a in au if a["side"] == "buy" and (a["sid"], int(a["t"])) in sk)
    return row


def _path_desc(seg, hvseg):
    """逐年（P9 讀7：首年 ÷ eq[w0]）、去掉最好一年、描述段兩個大跌段的區間報酬與在場比例。seg ＝ eq[w0..w1]。"""
    G = _B; cal = G["cal"]; w0, w1 = G["w0"], G["w1"]
    d = pd.DatetimeIndex(cal[w0:w1 + 1])
    yy = d.year; ym = d.strftime("%Y-%m")
    out = {}; yr = {}; prev = 0
    for y in sorted(set(yy)):
        ix = np.flatnonzero(yy == y); last = int(ix[-1])
        yr[int(y)] = float(seg[last] / seg[prev] - 1.0); out[f"y{y}"] = yr[int(y)]; prev = last
    if len(yr) > 1:
        best = max(yr, key=yr.get)
        nb = int(np.sum(yy == best))
        rest = np.prod([1 + r for y, r in yr.items() if y != best])
        out["drop_best_year"] = best
        out["drop_best_geo"] = float(rest ** (245.0 / max(len(seg) - 1 - nb, 1)) - 1.0)
    if hvseg is not None:
        out["expo"] = float(np.mean(hvseg / seg))
    if G["variant"] == "desc":
        for k, (a, b) in CRASH.items():
            ia = np.flatnonzero(ym == a); ib = np.flatnonzero(ym == b)
            if len(ia) and len(ib):
                p0, p1 = int(ia[-1]), int(ib[-1])
                out[f"crash_{k}"] = float(seg[p1] / seg[p0] - 1.0)
                if hvseg is not None:
                    out[f"crash_expo_{k}"] = float(np.mean(hvseg[p0 + 1:p1 + 1] / seg[p0 + 1:p1 + 1]))
    return out


def _run_cell(cid, r, sig=None, kw_over=None, below=None, want_audit=True):
    """回 (eq, first, end, hold_val, audit)。cid：1～24、25、26、"C1"、"C2"、"K0"。"""
    from . import research11 as R
    from . import researchAvg as AV
    from . import researchP9run as P9R
    from . import researchYear1M as Y
    G = _B; YG = Y._G; w0, w1 = G["w0"], G["w1"]
    au = [] if want_audit else None
    cl, op, NP = YG["closes"], YG["opens"], YG["NP"]
    if cid in (25, 26, "C1", "C2", "K0"):
        s1 = G["s1"] if sig is None else sig
        kw = {25: {"stop_line": G["lines"], "stop_line_le": False}, 26: {"pick": "K4", "pick_tie": "rng"},
              "C2": {"stop_line": G["lines"], "stop_line_le": False, "stop_proceeds": "next"}, "K0": {"pick": "K0", "pick_tie": "rng"}}.get(cid, {})
        if kw_over is not None:
            kw = kw_over
        o = R.simulate_mtm(s1, "H120", 10, np.random.default_rng(1000 + r), cl, op, NP, return_equity=True, audit=au, **kw)
    elif cid == 24:
        s = Y.sig_of(18, G["vtag"], w0, w1) if sig is None else sig
        P9R._G["flags"] = YG["flags_plus"]
        o = R.simulate_mtm(s, P9R.RULE, P9R.N_MAIN, np.random.default_rng(99000 + r), cl, op, NP,
                           return_equity=True, report_maxw=True, audit=au, **AV.ENGINE_KW_B["By"])
    elif below is not None:
        s = Y.sig_of(cid, G["vtag"], w0, w1)
        P9R._G["flags"] = YG["flags_plus"]
        o = R.simulate_mtm(s, P9R.RULE, P9R.N_MAIN, np.random.default_rng(99000 + r), cl, op, NP,
                           return_equity=True, report_maxw=True, **P9R.engine_kw(P9_KEYS[cid], below=below))
    else:
        s = Y.sig_of(cid, G["vtag"], w0, w1) if sig is None else sig
        o = Y.run_engine(cid, s, r, G["vtag"], audit=au)
    return o, au


def _job(args):
    from . import rerun17 as RR
    from . import research13 as R13
    from . import researchp17 as P17
    from . import researchYear1M as Y
    cid, r = args
    G = _B; w0, w1 = G["w0"], G["w1"]
    o, au = _run_cell(cid, r)
    eq = np.asarray(o["equity"], float)
    rows = []
    if cid == 0:
        n = w1 - w0 + 1
        Vs = Y.p12_derived(eq, w0, w1)
        for c in (0, 8, 5):
            V = Vs[c]
            cg, mg = R13.window_stats(V, 0, n, 0, n)
            row = {"cell": c, "r": r, "cagr": float(cg), "mdd": float(mg), "vol": RR.ann_vol(V), "first": int(o["first"]), "end": int(o["end"])}
            row.update(_path_desc(V, None if c != 0 else np.asarray(o["hold_val"], float)[w0:w1 + 1]))
            if c == 0:
                row.update({k: v for k, v in _metrics(eq, o["first"], o["end"], o.get("hold_val"), au).items() if k in ("turnover_yr", "cost_yr", "short_settled")})
            rows.append((row, V))
        if G["variant"] == "main":                                    # #5 假訊號臂 W_shuf（原件 P17：每顆 30 次，default_rng(108000＋r)）
            E_ = eq[w0:w1 + 1]; B_ = G["bench"][w0:w1 + 1]
            rb = P17.rebal_days(G["cal"], w0, w1)
            mask = np.zeros(n, bool); mask[[int(t) for t in rb]] = True
            sB = {int(t): P17.sigma_at(B_, int(t)) for t in rb}
            wp = P17.w_paths(E_, B_, rb, n, sB)["R_eq"]
            rng = np.random.default_rng(P17.SEED_SHUF + r); sh = []
            for rep in range(P17.R_SHUF):
                Vw, _, _ = P17.compose(E_, B_, P17.shuffled_w(wp, rb, n, rng), mask)
                cg, mg = R13.window_stats(Vw, 0, n, 0, n); sh.append((rep, float(cg), float(mg)))
            rows[2][0]["_shuf"] = sh
    else:
        row = {"cell": cid, "r": r, "trades": int(o["trades"])}
        row.update(_metrics(eq, o["first"], o["end"], o.get("hold_val"), au))
        if cid == 1:
            row.update(_lottery_days(au))
        if cid == 25:
            row["_pos"] = _positions25(au)
        if cid == 26:
            _, al = _run_cell(1, r)
            bl = {(a["sid"], int(a["t"])) for a in al if a["side"] == "buy"}
            bb = [(a["sid"], int(a["t"])) for a in au if a["side"] == "buy"]
            row["buy_diff"] = len(bl - set(bb)); row["buys"] = len(bb)
            kv = dict(zip(zip(G["s1"]["sid"], G["s1"]["entry_pos"].astype(int)), G["s1"]["K4"]))
            row["buy_K4_mean"] = float(np.nanmean([kv.get(b, np.nan) for b in bb])) if bb else np.nan
            row["lot_K4_mean"] = float(np.nanmean([kv.get(b, np.nan) for b in bl])) if bl else np.nan
        rows.append((row, eq[w0:w1 + 1]))
    return [(row, np.asarray(V[1:] / V[:-1] - 1.0)) for row, V in rows]


def _lottery_days(au, N=10):
    G = _B; ent = G["ent"]; w0, w1 = G["w0"], G["w1"]
    by_t = {}
    for a in au:
        by_t.setdefault(int(a["t"]), []).append(a)
    held = set(); d_sig = d_over = d_act = 0; elim = 0
    for t in sorted(set(by_t) | set(ent)):
        for a in by_t.get(t, []):
            if a["side"] == "sell":
                held.discard(a["sid"])
        if t in ent and w0 <= t <= w1:
            cand = [s for s in ent[t] if s not in held]; free = N - len(held)
            d_sig += 1
            if len(cand) > free:
                d_over += 1
                if free > 0:
                    d_act += 1; elim += len(cand) - free
        for a in by_t.get(t, []):
            if a["side"] == "buy":
                held.add(a["sid"])
    return {"days_sig": d_sig, "days_over": d_over, "days_act": d_act, "elim_by_lottery": elim}


def _positions25(au):
    """#25 部位：(是否被 M20 賣、觸發根＝researchYfV2.positions 同式)。"""
    G = _B; xmap, V = G["xmap"], G["V"]
    pos = {}; out = []
    for a in au:
        t = int(a["t"])
        if a["side"] == "buy":
            pos[a["sid"]] = t
        elif "kind" not in a:
            s = a["sid"]; e = pos.pop(s); x = xmap[(s, e)]
            out.append((t < x, int(V[s][e:t].sum()) if t < x else 0))
    return out


# ── 假訊號臂與控制臂 ──
def _job_pl(args):
    from . import rerun17 as RR
    from . import research11 as R
    from . import research13 as R13
    from . import researchYear1M as Y
    from . import researchp1 as P1
    kind, cid, j = args
    G = _B; YG = Y._G; w0, w1 = G["w0"], G["w1"]
    if kind == "P10":
        s = G["pl_draw"][j]
        if cid in REG_T1:
            s = s[YG["reg_t1"][s["entry_pos"].to_numpy()]]
        o, _ = _run_cell(cid, j, sig=s, want_audit=False)
    elif kind == "P1":
        o, _ = _run_cell(cid, j, sig=G["p1_draw"][j], want_audit=False)
    elif kind == "P9":
        key_j, r = j
        o, _ = _run_cell(cid, r, below=G["fake"][(cid, key_j)], want_audit=False)
    elif kind in ("K0", "C2"):
        o, _ = _run_cell(kind, j, want_audit=False)
    elif kind == "C1":
        o, _ = _run_cell("C1", j, kw_over={"stop_line": G["c1_lines"][j], "stop_line_le": False}, want_audit=False)
    elif kind == "P3":
        sp = dict(Y.CELL[cid][4])
        s = Y.sig_of(cid, G["vtag"], w0, w1)
        kw = dict(d_max=sp["d"], pick=sp["pick"], queue_days=RR.P1_QUEUE if sp["d"] is not None else 0, return_equity=True)
        A = R.simulate_mtm(s, "H60", sp["N"], np.random.default_rng(RR.P1_SEED0 + j), YG["closes"], YG["opens"], YG["NP"], log=[], **kw)
        eq = np.asarray(A["equity"], float)[w0:w1 + 1]; hv = np.asarray(A["hold_val"], float)[w0:w1 + 1]
        e = np.where(eq > 0, hv / eq, 0.0)
        r_tot = np.r_[0.0, eq[1:] / eq[:-1] - 1]
        e_prev = np.r_[0.0, e[:-1]]
        r_inv = np.where(e_prev > 1e-12, r_tot / np.where(e_prev > 1e-12, e_prev, 1.0), 0.0)
        n = len(eq); res = []
        for k in range(200):
            kk = int(np.random.default_rng(9000 + k).integers(1, n))
            e2 = np.roll(e, -kk)
            eq2 = np.cumprod(1.0 + np.r_[0.0, e2[:-1]] * r_inv)
            cg, mg = R13.window_stats(eq2, 0, n, 0, n); res.append((k, float(cg), float(mg)))
        return {"kind": kind, "cell": cid, "j": j, "shifts": res}
    eq = np.asarray(o["equity"], float)
    c, m, v = RR.win_metrics(eq, o["first"], o["end"], w0, w1)
    out = {"kind": kind, "cell": cid, "j": j if not isinstance(j, tuple) else j[0], "r": j if not isinstance(j, tuple) else j[1],
           "cagr": float(c), "mdd": float(m), "vol": float(v)}
    if kind == "C1":
        out["c1_sold"] = G["c1_cnt"][j]
    return out


def _c1_lines(r, p, bars):
    from . import researchYfV2 as YV
    return YV.c1_lines(r, _B["s1"], _B["V"], p, bars)


def body_run(procs, log, only=None):
    from multiprocessing import Pool
    from . import researchP9run as P9R
    from . import researchYear1M as Y
    global OUT
    NREP = int(os.environ.get("PV_REPS", "200"))
    OUT = os.environ.get("PV_OUT", OUT)
    os.makedirs(OUT, exist_ok=True)
    t00 = time.time()
    vlist = VARIANTS if only is None else only
    allrows = []; meanret = {}; placebo = []; infos = {}
    infos["程式 sha256（組態）"] = {f: _sha256(os.path.join(HERE, f))[:16] for f in (
        "research11.py", "research13.py", "research34.py", "researchp1.py", "researchp4.py", "researchp7.py", "researchp14.py", "researchp17.py",
        "p4_features.py", "p9_flags.py", "researchP9run.py", "researchAvg.py", "researchYear1M.py", "rerun17.py", "yfstop_lines.py", "researchYfV2.py",
        "data.py", "early_data.py", "researchV.py")}
    for variant in vlist:
        info = body_setup(variant, log); infos[variant] = info
        w0, w1 = _B["w0"], _B["w1"]
        cells = [0] + [c for c in range(1, 27) if c not in (5, 8)]
        jobs = [(c, r) for c in cells for r in range(NREP)]
        acc = {}; cnt = {}; pos25 = []
        t0 = time.time()
        with Pool(procs) as pool:
            for res in pool.imap_unordered(_job, jobs, chunksize=4):
                for row, ret in res:
                    c = row["cell"]
                    acc[c] = acc.get(c, 0.0) + ret; cnt[c] = cnt.get(c, 0) + 1
                    if "_pos" in row:
                        pos25 += row.pop("_pos")
                    if "_shuf" in row:
                        for rep, cg, mg in row.pop("_shuf"):
                            placebo.append({"variant": variant, "kind": "W_shuf", "cell": 5, "j": rep, "r": row["r"], "cagr": cg, "mdd": mg})
                    row["variant"] = variant
                    allrows.append(row)
        log(f"  [{variant}] 26 格 × 200 顆 {time.time() - t0:.0f}s")
        mr = pd.DataFrame({f"c{c}": acc[c] / cnt[c] for c in sorted(acc)}, index=pd.DatetimeIndex(_B["cal"][w0 + 1:w1 + 1]))
        b = _B["bench"]; mr["0050"] = b[w0 + 1:w1 + 1] / b[w0:w1] - 1.0
        meanret[variant] = mr
        mr.to_csv(os.path.join(OUT, f"body_meanret_{variant}.csv.gz"), compression="gzip", float_format="%.17g")
        if variant != "main":
            continue
        # ── 假訊號臂＋控制臂（只在判定版）──
        n_sold = sum(1 for s, _ in pos25 if s); bars = np.asarray([b_ for s, b_ in pos25 if s], int)
        p = n_sold / max(len(pos25), 1)
        c1 = {"部位數（200 顆合併）": len(pos25), "被 M20 賣掉": n_sold, "p": p,
              "觸發根 p10／中位／p90": [float(np.quantile(bars, q)) for q in (.1, .5, .9)] if len(bars) else None}
        infos["C1經驗分佈"] = c1
        c1l = {}; c1c = {}
        for r in range(NREP):
            c1l[r], ns, nsh = _c1_lines(r, p, bars) if len(bars) else ({}, 0, 0)
            c1c[r] = (ns, nsh)
        rng13 = np.random.default_rng(13)
        S_w = _B["S_mtm"]; e_ = S_w["entry_pos"].to_numpy(); S_w = S_w[(e_ >= w0) & (e_ <= w1)].reset_index(drop=True)
        A_w = _B["AND_mtm"]; e2 = A_w["entry_pos"].to_numpy(); A_w = A_w[(e2 >= w0) & (e2 <= w1)]
        nA = len(A_w)
        pl_draw = [S_w.iloc[np.sort(rng13.choice(len(S_w), min(nA, len(S_w)), replace=False))].reset_index(drop=True) for _ in range(NREP)]
        p1_draw = []
        need = A_w.groupby("month").size().to_dict()
        by_m = {m: g for m, g in S_w.groupby("month")}
        for r in range(NREP):
            g = np.random.default_rng(20260925 + r); parts = []
            for m, k in sorted(need.items()):
                pool_ = by_m.get(m)
                if pool_ is None:
                    continue
                parts.append(pool_.iloc[np.sort(g.choice(len(pool_), min(k, len(pool_)), replace=False))])
            p1_draw.append(pd.concat(parts).sort_values(["entry_pos", "sid"], kind="stable").reset_index(drop=True))
        fake = {}
        for cid, n in ((22, 60), (23, 10)):
            orig = P9R._G["below"][n]
            for jj in range(1, 31):
                fake[(cid, jj)] = P9R.shuffle_state(orig, w0 - 1, w1, np.random.default_rng(20260925 + jj))
        _B.update(pl_draw=pl_draw, p1_draw=p1_draw, fake=fake, c1_lines=c1l, c1_cnt=c1c)
        infos["假訊號抽樣"] = {"S 窗內列": int(len(S_w)), "|AND| 窗內": nA, "P1 月數": len(need),
                           "P1 抽到的列數（中位）": float(np.median([len(x) for x in p1_draw])), "AND 列數": nA}
        pj = [("P10", c, j) for c in P10_CELLS for j in range(NREP)] + [("P1", c, r) for c in P1_CELLS for r in range(NREP)] + \
             [("P3", c, r) for c in P3B_CELLS for r in range(NREP)] + [("P9", c, (jj, r)) for c in (22, 23) for jj in range(1, 31) for r in range(min(50, NREP))] + \
             [("K0", 26, r) for r in range(NREP)] + [("C1", 25, r) for r in range(NREP)] + [("C2", 25, r) for r in range(NREP)]
        t0 = time.time()
        with Pool(procs) as pool:
            for res in pool.imap_unordered(_job_pl, pj, chunksize=8):
                if "shifts" in res:
                    for k, cg, mg in res["shifts"]:
                        placebo.append({"variant": "main", "kind": "P3shift", "cell": res["cell"], "j": k, "r": res["j"], "cagr": cg, "mdd": mg})
                else:
                    res["variant"] = "main"; placebo.append(res)
        log(f"  [main] 假訊號＋控制臂 {len(pj):,} 件 {time.time() - t0:.0f}s")
    SD = pd.DataFrame(allrows)
    SD.to_csv(os.path.join(OUT, "body_seeds.csv.gz"), index=False, compression={"method": "gzip", "mtime": 0}, float_format="%.17g")
    PL = pd.DataFrame(placebo)
    PL.to_csv(os.path.join(OUT, "body_placebo.csv.gz"), index=False, compression={"method": "gzip", "mtime": 0}, float_format="%.17g")
    json.dump(infos, open(os.path.join(OUT, "body_setup.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完成 body-run] seeds {len(SD):,}｜placebo {len(PL):,}｜{time.time() - t00:.0f}s（⛔ 本 log 不印任何報酬）")



# ═════════════ body-gate：#25／#26／C2／K0 的包裝在主窗逐位元對既有逐種子檔（⛔ 不碰早年）═════════════
def body_gate(log, reps=20):
    from . import listexit_lines as L
    from . import research11 as R
    from . import researchYfStop as YS
    from . import yfstop_lines as YL
    ctx = L.setup_t1(log)
    RR, w0, w1 = ctx["RR"], ctx["w0"], ctx["w1"]
    YS._G["ctx"] = ctx
    sig = ctx["sig"].copy()
    k4 = []
    for s, k in zip(sig["sid"], sig["k"].astype(int)):
        c = YS.bars_of(s)["c"]; k4.append(float(c[k] / c[k - 20] - 1.0))
    sig["K4"] = k4; sig["K0"] = sig["sid"].str[-1].astype(int)
    pk = pd.read_csv(os.path.join(HERE, "resultsYfRank", "pre_keys.csv"), dtype={"sid": str}, usecols=["sid", "entry_pos", "K0", "K4"], float_precision="round_trip")
    m = sig.merge(pk, on=["sid", "entry_pos"], suffixes=("", "_ref"), validate="1:1")
    keys_ok = len(m) == len(sig) and all(repr(a) == repr(b) for a, b in zip(m["K4"], m["K4_ref"])) and (m["K0"] == m["K0_ref"]).all()
    lines = YL.ma_lines(sig, ctx["closes"], YS.bars_of, 20, arm="state")
    arms = {"cand1": ({"stop_line": lines, "stop_line_le": False}, "resultsYfV2/main_seeds_arms.csv", "cand1"),
            "cand2": ({"pick": "K4", "pick_tie": "rng"}, "resultsYfV2/main_seeds_arms.csv", "cand2"),
            "C2": ({"stop_line": lines, "stop_line_le": False, "stop_proceeds": "next"}, "resultsYfStop/body_seeds_arms.csv", "M20"),
            "K0": ({"pick": "K0", "pick_tie": "rng"}, "resultsYfRank/seeds.csv", "K0")}
    res = {"鍵 K4／K0 ＝ resultsYfRank/pre_keys.csv（repr）": bool(keys_ok), "closes dtype": str(next(iter(ctx["closes"].values())).dtype)}
    for a, (kw, f, ref_arm) in arms.items():
        ref = pd.read_csv(os.path.join(HERE, f), float_precision="round_trip")
        ref = ref[ref["arm"] == ref_arm].set_index("r").sort_index()
        bad = 0
        for r in range(reps):
            o = R.simulate_mtm(sig, "H120", 10, np.random.default_rng(1000 + r), ctx["closes"], ctx["opens"], ctx["ncal"], return_equity=True, **kw)
            c, mm, v = RR.win_metrics(np.asarray(o["equity"], float), o["first"], o["end"], w0, w1)
            bad += int(repr(float(c)) != repr(float(ref.loc[r, "cagr"])) or repr(float(mm)) != repr(float(ref.loc[r, "mdd"])))
        res[f"{a} ＝ {f}:{ref_arm}（{reps} 顆 年化／回落 repr）"] = bad == 0
    res["全部過"] = all(v for k, v in res.items() if k != "closes dtype")
    json.dump(res, open(os.path.join(OUT, "body_gate.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[body-gate 主窗] {json.dumps(res, ensure_ascii=False)}")
    if not res["全部過"]:
        raise SystemExit("⛔ #25／#26 包裝閘不過")


# ═════════════ body-table：彙總、判定、REPORT.md ═════════════
def _pctl(x, dist):
    d = np.asarray(dist, float)
    return float(((d < x).sum() + 0.5 * (d == x).sum()) / len(d) * 100)


def _lab(c, m, bc, bm):
    from . import rerun17_table as RT
    lab, ratio, extra = RT.label(c, m, bc, bm)
    return {"合格": "Q", "另列": "R", "不合格": "F"}[lab], ratio, extra


def boot_lb(mr, col, alpha=ALPHA_V, B=B_BOOT, seed=BOOT_SEED):
    d = (mr[col] - mr["0050"]).to_numpy()
    mon = mr.index.strftime("%Y-%m").to_numpy()
    months = sorted(set(mon)); K = len(months)
    mi = np.searchsorted(np.array(months), mon)
    S = np.bincount(mi, weights=d, minlength=K); nm = np.bincount(mi, minlength=K).astype(float)
    IDX = np.random.default_rng(seed).integers(0, K, size=(B, K))
    stat = S[IDX].sum(1) / nm[IDX].sum(1) * ANN
    return float(d.mean() * ANN), float(np.quantile(stat, alpha)), K


def body_table(log):
    from . import rerun17 as RR
    from . import data as D
    SD = pd.read_csv(os.path.join(OUT, "body_seeds.csv.gz"), float_precision="round_trip")
    PL = pd.read_csv(os.path.join(OUT, "body_placebo.csv.gz"), float_precision="round_trip")
    ST = json.load(open(os.path.join(OUT, "body_setup.json"), encoding="utf-8"))
    NAME = {**{c: v[0] for c, v in PREREGV.items()}, **{c: v[0] for c, v in V2.items()}}
    rows = []; bench = {}
    for variant in [v for v in VARIANTS if v in set(SD["variant"])]:
        use_layout("restore" if variant == "restore" else "main")
        cal = D.load_calendar(); w0, w1 = win_of(cal, variant)
        b = RR.load_bench(cal)
        bw = RR.bench_row(cal, b, w0, w1 + 1)
        seg = b[w0:w1 + 1] / b[w0]
        _B.update(cal=cal, w0=w0, w1=w1, variant=variant)
        bd = _path_desc(seg, None)
        bench[variant] = {"window": [str(cal[w0].date()), str(cal[w1].date()), w1 - w0 + 1], **bw, "ratio": bw["cagr"] / abs(bw["mdd"]),
                          "ann_over_vol": bw["cagr"] / bw["vol"], **bd}
        mr = pd.read_csv(os.path.join(OUT, f"body_meanret_{variant}.csv.gz"), index_col=0, parse_dates=True, float_precision="round_trip")
        for cid in range(1, 27):
            g = SD[(SD["variant"] == variant) & (SD["cell"] == cid)]
            if not len(g):
                continue
            c, m, v = float(g["cagr"].median()), float(g["mdd"].median()), float(g["vol"].median())
            lab, ratio, extra = _lab(c, m, bw["cagr"], bw["mdd"])
            row = {"variant": variant, "編號": cid, "格": NAME[cid], "顆": len(g), "起點": str(cal[w0].date()),
                   "首筆進場（中位）": str(cal[int(g["first"].median())].date()) if "first" in g and g["first"].notna().all() and cid not in (5, 8) else "",
                   "年化": c, "回落": m, "比值": ratio, "年化波動": v, "年化÷波動": c / v, "標籤": lab, "深淺註": extra,
                   "0050年化": bw["cagr"], "0050回落": bw["mdd"], "0050比值": bw["cagr"] / abs(bw["mdd"]), "0050年化波動": bw["vol"],
                   "0050年化÷波動": bw["cagr"] / bw["vol"]}
            for k in [k for k in g.columns if (k.startswith("y") and k[1:].isdigit()) or k.startswith("crash") or k in
                      ("drop_best_geo", "turnover_yr", "cost_yr", "expo", "trades", "short_settled", "days_act", "days_over", "days_sig", "buy_diff")]:
                if g[k].notna().any():
                    row[k] = float(g[k].median())
            if f"c{cid}" in mr:
                ad, lb, K = boot_lb(mr, f"c{cid}")
                row.update({"年化差_算術": ad, "Bonferroni下界": lb, "月數": K})
            rows.append(row)
    C = pd.DataFrame(rows)
    # ── 判定版的措辭（登錄 §四查表＋v2 §二）──
    M = C[C["variant"] == "main"].set_index("編號")
    b0 = bench["main"]
    base1 = SD[(SD["variant"] == "main") & (SD["cell"] == 1)].set_index("r").sort_index()
    v2 = {}
    for cid in (25, 26):
        g = SD[(SD["variant"] == "main") & (SD["cell"] == cid)].set_index("r").sort_index()
        dc = g["cagr"] - base1.loc[g.index, "cagr"]; dm = g["mdd"] - base1.loc[g.index, "mdd"]
        v2[cid] = {"皆正": int(((dc > 0) & (dm > 0)).sum()), "皆負": int(((dc < 0) & (dm < 0)).sum()),
                   "年化差中位": float(dc.median()), "回落差中位": float(dm.median())}
    g26 = SD[(SD["variant"] == "main") & (SD["cell"] == 26)]
    lot_ratio = (base1["cagr"] / base1["mdd"].abs()).to_numpy()
    v2[26].update({"真由抽籤決定的日數（#1 200 顆中位）": float(base1["days_act"].median()), "候選＞空槽日（中位）": float(base1["days_over"].median()),
                   "有訊號日（中位）": float(base1["days_sig"].median()), "被改變的買進筆數（中位）": float(g26["buy_diff"].median()),
                   "年化百分位": _pctl(float(g26["cagr"].median()), base1["cagr"].to_numpy()),
                   "比值百分位": _pctl(float((g26["cagr"] / g26["mdd"].abs()).median()), lot_ratio)})
    k0 = PL[(PL["kind"] == "K0")]
    v2[26]["K0 年化百分位"] = _pctl(float(k0["cagr"].median()), base1["cagr"].to_numpy())
    v2[26]["K0 比值百分位"] = _pctl(float((k0["cagr"] / k0["mdd"].abs()).median()), lot_ratio)
    v2[26]["可判定"] = v2[26]["真由抽籤決定的日數（#1 200 顆中位）"] >= 20
    for kk in ("C1", "C2"):
        g = PL[PL["kind"] == kk].set_index("r").sort_index()
        c25 = SD[(SD["variant"] == "main") & (SD["cell"] == 25)].set_index("r").sort_index()
        lab, ratio, _ = _lab(float(g["cagr"].median()), float(g["mdd"].median()), b0["cagr"], b0["mdd"])
        v2[kk] = {"年化中位": float(g["cagr"].median()), "回落中位": float(g["mdd"].median()), "比值": ratio, "對0050": lab,
                  "對#1 皆正": int(((g["cagr"] - base1.loc[g.index, "cagr"] > 0) & (g["mdd"] - base1.loc[g.index, "mdd"] > 0)).sum()),
                  "對#1 皆負": int(((g["cagr"] - base1.loc[g.index, "cagr"] < 0) & (g["mdd"] - base1.loc[g.index, "mdd"] < 0)).sum()),
                  "對候選一 皆正": int(((g["cagr"] - c25.loc[g.index, "cagr"] > 0) & (g["mdd"] - c25.loc[g.index, "mdd"] > 0)).sum()),
                  "對候選一 皆負": int(((g["cagr"] - c25.loc[g.index, "cagr"] < 0) & (g["mdd"] - c25.loc[g.index, "mdd"] < 0)).sum())}
    # ── 假訊號臂 ──
    pl_rows = []
    def lab_of(c, m):
        return _lab(c, m, b0["cagr"], b0["mdd"])[0]
    for cid in P10_CELLS + P1_CELLS:
        g = PL[(PL["kind"].isin(["P10", "P1"])) & (PL["cell"] == cid)]
        labs = [lab_of(c, m) for c, m in zip(g["cagr"], g["mdd"])]
        pl_rows.append({"編號": cid, "臂": "P10 S 內抽 |AND|" if cid in P10_CELLS else "P1 每月同數抽 S", "次數": len(g), "x_Q": labs.count("Q"), "x_R": labs.count("R")})
    for cid in P3B_CELLS:
        g = PL[(PL["kind"] == "P3shift") & (PL["cell"] == cid)]
        md = g.groupby("j")[["cagr", "mdd"]].median()
        labs = [lab_of(c, m) for c, m in zip(md["cagr"], md["mdd"])]
        pl_rows.append({"編號": cid, "臂": "P3 丙1 環形平移（甲曝險）", "次數": len(md), "x_Q": labs.count("Q"), "x_R": labs.count("R")})
    g = PL[PL["kind"] == "W_shuf"]
    md = g.groupby("j")[["cagr", "mdd"]].median()
    labs = [lab_of(c, m) for c, m in zip(md["cagr"], md["mdd"])]
    pl_rows.append({"編號": 5, "臂": "P17 W_shuf", "次數": len(md), "x_Q": labs.count("Q"), "x_R": labs.count("R")})
    pl_rows.append({"編號": 8, "臂": "（權重恆 0.50 ⇒ 打亂＝原樣，依構造退化，不做）", "次數": 0, "x_Q": np.nan, "x_R": np.nan})
    for cid in (22, 23):
        g = PL[(PL["kind"] == "P9") & (PL["cell"] == cid)]
        md = g.groupby("j")[["cagr", "mdd"]].median()
        labs = [lab_of(c, m) for c, m in zip(md["cagr"], md["mdd"])]
        pl_rows.append({"編號": cid, "臂": "P9 線上／線下段打亂（50 顆中位）", "次數": len(md), "x_Q": labs.count("Q"), "x_R": labs.count("R")})
    PLT = pd.DataFrame(pl_rows)
    PLT["x／次數"] = PLT["x_Q"] / PLT["次數"].replace(0, np.nan)
    PLT["警語"] = PLT["x／次數"] >= 0.05
    PLT.to_csv(os.path.join(OUT, "body_placebo.csv"), index=False)
    warn = {int(r["編號"]): int(r["x_Q"]) for _, r in PLT.iterrows() if bool(r["警語"])}
    # ── 結果句 ──
    TAIL = "（早年只驗上市股；樣本只有約 3 年；本段樣本只夠分 Q／R／F，『可以說找到』依構造不可得）"
    sent = []
    for cid in range(1, 27):
        if cid not in M.index:
            continue
        q = M.loc[cid]; lab = q["標籤"]
        pre = f"⚠ 隨機也有 {warn[cid]} 合格：" if cid in warn else ""
        if cid in (25, 26):
            vv = v2[cid]
            if cid == 25:
                good = vv["皆正"] >= 190; bad = vv["皆負"] >= 190
            else:
                good = v2[26]["可判定"] and v2[26]["年化百分位"] >= 98.75 and v2[26]["比值百分位"] >= 98.75
                bad = v2[26]["可判定"] and v2[26]["年化百分位"] <= 1.25 and v2[26]["比值百分位"] <= 1.25
                if not (10 <= v2[26]["K0 年化百分位"] <= 90 and 10 <= v2[26]["K0 比值百分位"] <= 90):
                    pre = "連隨便排都偏離抽籤，抽籤分佈當對照要打折：" + pre
            nm = "候選一（M20＋整份）" if cid == 25 else "候選二（K4 排名）"
            if cid == 26 and not v2[26]["可判定"]:
                s_ = f"{nm}：早年段真由抽籤決定的日數 {v2[26]['真由抽籤決定的日數（#1 200 顆中位）']:.0f} ＜ 20 ⇒ 依構造不可判定 ⇒ 營飆 v1 不改"
            elif good:
                s_ = f"{nm}在 2012～2014 也比營飆 v1 好（樣本只有約 3 年）⇒ 仍須前瞻紀錄滿 12 個月才談升 v2（裁定定）"
            else:
                s_ = f"{nm}在沒看過的年份沒有比營飆 v1 好 ⇒ 營飆 v1 不改"
            s_ += f"；對 0050：{ {'Q': '合格', 'R': '另列', 'F': '不合格'}[lab] }｜早年只驗上市股｜這是全部選到的股票平均起來的結果，不是對某一檔的預測"
        elif lab == "Q":
            s_ = "驗收段也合格，但差距在誤差內" if q["Bonferroni下界"] <= 0 else "驗收段合格，而且下界 ＞ 0（⚠ 開跑前算術判定依構造不可得 ⇒ 第一種結果句已拿掉，不說「找到」）"
            if q["回落"] < q["0050回落"]:
                s_ += f"；回落比 0050 深 {(q['0050回落'] - q['回落']) * 100:.2f} 點、年化多 {(q['年化'] - q['0050年化']) * 100:.2f} 點"
        elif lab == "R":
            s_ = f"驗收段賺得比 0050 多，但風險增加得比報酬多：年化 {q['年化'] * 100:.2f}%、回落 {q['回落'] * 100:.2f}%、比值 {q['比值']:.4f}"
        else:
            s_ = f"早年段沒有撐住：年化 {q['年化'] * 100:.2f}% 對 0050 {q['0050年化'] * 100:.2f}%"
        if cid == 24:
            s_ += "；主窗對門檻B 基準臂分不出（34／200）"
        sent.append({"編號": cid, "格": NAME[cid], "標籤": lab, "結果句": pre + s_ + TAIL})
    SE = pd.DataFrame(sent)
    C.to_csv(os.path.join(OUT, "body_cells.csv"), index=False)
    SE.to_csv(os.path.join(OUT, "body_sentences.csv"), index=False)
    summ = {"0050": bench, "v2": v2, "setup": {k: ST[k] for k in ST if k in VARIANTS},
            "C1經驗分佈": ST.get("C1經驗分佈"), "假訊號抽樣": ST.get("假訊號抽樣"),
            "判定版 Q／R／F": M["標籤"].value_counts().to_dict(), "Q 格": M.index[M["標籤"] == "Q"].tolist(), "R 格": M.index[M["標籤"] == "R"].tolist()}
    json.dump(summ, open(os.path.join(OUT, "body_summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    body_report(C, SE, PLT, summ)
    log(f"[完成 body-table] body_cells.csv／body_sentences.csv／body_placebo.csv／body_summary.json／REPORT.md")


def _p(x, d=2):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x * 100:+.{d}f}%"


def body_report(C, SE, PLT, S):
    from . import early_data as E
    NAME = {**{c: v[0] for c, v in PREREGV.items()}, **{c: v[0] for c, v in V2.items()}}
    M = C[C["variant"] == "main"].set_index("編號")
    b = S["0050"]["main"]
    L = ["# PREREGV 早年段驗收（26 格，只上市）：本體", "",
         f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。回測線。登錄 PREREGV seq6（sha 445338e8a06bbac8）＋ 營飆 v2 候選 seq3（sha d37771f84327dfb0）；裁定 seq206 §三、seq210、seq215、seq218 §四。",
         f"資料：tw-stock-data main `{E.BODY_SHA[:10]}` 的 data/early（git archive 唯讀）；窗 {b['window'][0]}～{b['window'][1]}（{b['window'][2]} 個交易日）。",
         "⭐ 必附：**早年只驗上市股**｜**樣本只有約 3 年**｜**本段樣本只夠分 Q／R／F，『可以說找到』依構造不可得**｜成本 0.585% 來回（手續費照上限 0.1425%，實際可能更低）", "",
         "## 〇、表頭：營飆 v1（#1）、營量 v1（#13）", "", "| # | 格 | 年化 | 回落 | 比值 | 標籤 | 對 0050 |", "|---|---|---|---|---|---|---|"]
    for cid in (1, 13):
        q = M.loc[cid]
        L.append(f"| {cid} | {NAME[cid]} | {_p(q['年化'])} | {_p(q['回落'])} | {q['比值']:.4f} | {q['標籤']} | 0050 {_p(b['cagr'])}／{_p(b['mdd'])}／{b['ratio']:.4f} |")
    L += ["", "## 一、判定版 26 格（200 顆中位；⛔ 26 格一次跑完、一次交件）", "",
          f"0050 同窗：年化 {_p(b['cagr'])}、回落 {_p(b['mdd'])}、比值 {b['ratio']:.4f}、年化波動 {_p(b['vol'])}、年化÷波動 {b['ann_over_vol']:.4f}", "",
          "| # | 格 | 起點 | 年化 | 回落 | 比值 | 年化波動 | 年化÷波動 | 標籤 | 年化差（算術） | 下界 α=0.05/26 | 深淺註 |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for cid, q in M.iterrows():
        L.append(f"| {cid} | {NAME[cid]} | {q['起點']} | {_p(q['年化'])} | {_p(q['回落'])} | {q['比值']:.4f} | {_p(q['年化波動'])} | {q['年化÷波動']:.4f} | **{q['標籤']}** | "
                 f"{_p(q.get('年化差_算術'))} | {_p(q.get('Bonferroni下界'))} | {q['深淺註'] if isinstance(q['深淺註'], str) else ''} |")
    L += ["", f"Q／R／F：{S['判定版 Q／R／F']}", "", "## 二、結果句（登錄 §四查表；v2 照其登錄 §二）", ""]
    for _, r in SE.iterrows():
        L.append(f"- **#{r['編號']} {r['格']}**（{r['標籤']}）：{r['結果句']}")
    v2 = S["v2"]
    L += ["", "## 三、營飆 v2 候選（#25、#26）與控制臂 C1、C2、K0（⛔ 控制臂不計 N）", ""]
    L.append(f"```\n{json.dumps(v2, ensure_ascii=False, indent=1, default=str)}\n```")
    L += ["", "## 四、假訊號臂（⛔ 不進判定）", "", "| # | 臂 | 次數 | Q | R | x／次數 | 警語 |", "|---|---|---|---|---|---|---|"]
    for _, r in PLT.iterrows():
        L.append(f"| {r['編號']} | {r['臂']} | {r['次數']} | {r['x_Q']} | {r['x_R']} | {r['x／次數']} | {'⚠' if r['警語'] else ''} |")
    L += ["", "## 五、必報：逐年、去掉最好一年、換手與成本、在場", "", "| # | " + " | ".join(["2012", "2013", "2014", "去掉最好一年", "年換手", "年成本", "在場", "持有中遇減資了結（筆/顆）"]) + " |",
          "|---|" + "---|" * 8]
    L.append(f"| 0050 | {_p(b.get('y2012'))} | {_p(b.get('y2013'))} | {_p(b.get('y2014'))} | {_p(b.get('drop_best_geo'))} | — | — | — | — |")
    for cid, q in M.iterrows():
        L.append(f"| {cid} | {_p(q.get('y2012'))} | {_p(q.get('y2013'))} | {_p(q.get('y2014'))} | {_p(q.get('drop_best_geo'))} | "
                 f"{q.get('turnover_yr', np.nan):.2f} | {_p(q.get('cost_yr'))} | {q.get('expo', np.nan):.3f} | {q.get('short_settled', np.nan)} |")
    L += ["", "## 六、描述版與敏感度（⛔ 不判）", "", "| # | 判定版 年化／回落 | R3 引擎原樣 | R1 剔除轉上市 | 描述版（減資入鏈、不剔除） |", "|---|---|---|---|---|"]
    for cid in range(1, 27):
        cells = []
        for v in ("main", "eng", "noT", "restore"):
            g = C[(C["variant"] == v) & (C["編號"] == cid)]
            cells.append(f"{_p(g['年化'].iloc[0])}／{_p(g['回落'].iloc[0])}（{g['標籤'].iloc[0]}）" if len(g) else "—")
        L.append(f"| {cid} | " + " | ".join(cells) + " |")
    for v in ("eng", "noT", "restore"):
        bb = S["0050"].get(v)
        if bb:
            L.append(f"\n0050（{v}）：{_p(bb['cagr'])}／{_p(bb['mdd'])}")
    dd = S["0050"].get("desc")
    if dd:
        L += ["", f"## 七、描述段 {dd['window'][0]}～{dd['window'][1]}（eligible_v；G0 未過（1.30%）⇒ 定義與主窗不同；2008～2010 無處置資料；只上市；⛔ 不判）", "",
              f"0050：年化 {_p(dd['cagr'])}、回落 {_p(dd['mdd'])}；2008-05～11 {_p(dd.get('crash_2008-05～2008-11'))}；2011-08～12 {_p(dd.get('crash_2011-08～2011-12'))}", "",
              "| # | 年化 | 回落 | 比值 | 2008-05～11 報酬 | 在場 | 2011-08～12 報酬 | 在場 |", "|---|---|---|---|---|---|---|---|"]
        for _, q in C[C["variant"] == "desc"].iterrows():
            L.append(f"| {q['編號']} | {_p(q['年化'])} | {_p(q['回落'])} | {q['比值']:.4f} | {_p(q.get('crash_2008-05～2008-11'))} | {q.get('crash_expo_2008-05～2008-11', np.nan):.3f} | "
                     f"{_p(q.get('crash_2011-08～2011-12'))} | {q.get('crash_expo_2011-08～2011-12', np.nan):.3f} |")
    L += ["", "## 八、設定、事件、讀法", "", f"```\n{json.dumps(S['setup'], ensure_ascii=False, indent=1, default=str)[:20000]}\n```", "",
          f"讀法（R1～R14 照 seq215／seq6 §九；實作層）：\n```\n{json.dumps(E.BODY_READINGS, ensure_ascii=False, indent=1)}\n```", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["pre-data", "pre-arith", "pre-boot", "pre-report", "body-sig", "body-gate", "body-run", "body-table"])
    ap.add_argument("--procs", type=int, default=2)
    ap.add_argument("--layout", default="main")
    ap.add_argument("--only", nargs="*", default=None)
    a = ap.parse_args()
    log = _log_to(os.path.join(OUT, f"{a.stage}.log"))
    log(f"===== researchV {a.stage} {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）=====")
    if a.stage == "pre-data":
        pre_data(log)
    elif a.stage == "pre-arith":
        pre_arith(log, a.procs)
    elif a.stage == "pre-boot":
        boot(pd.read_csv(os.path.join(OUT, "pre_arith_meanret.csv.gz"), index_col=0, parse_dates=True, float_precision="round_trip"), log)
    elif a.stage == "pre-report":
        pre_report(log)
    elif a.stage == "body-sig":
        body_sig(a.layout, a.procs, log)
    elif a.stage == "body-gate":
        body_gate(log)
    elif a.stage == "body-run":
        body_run(a.procs, log, a.only)
    else:
        body_table(log)


if __name__ == "__main__":
    main()
