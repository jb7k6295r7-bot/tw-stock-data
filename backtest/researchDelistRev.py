# -*- coding: utf-8 -*-
"""補下市公司月營收後重跑營量 v1、營飆 v1 主世界兩段（描述性對帳）——裁定 seq406 §三、seq411 §五.1；回測線計算子代理。
⭐ 描述、⛔ 不改標籤、⛔ 不計 N。⛔ 不改任何鎖內檔／既有檔（換資料只在本檔內注入）；⛔ 不 commit。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchDelistRev [--procs 2]
    獨立查核：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchDelistRev_check [--procs 2]

═══ 讀法（寫於 2026-10-21（台北），在算任何本件數字之前；⚠ 本線看過：營量 v1、營飆 v1 定版主世界各段年化／回落（resultsT1fix、resultsYF_N、resultsYLvsYF）；
    資料庫 1021-0009 的量級（72 家有、80 家缺；有資料的 69 家中 40 家下市前 24 月內曾創 24 月新高）；本件新數字一個都沒看過）═══
 資料
  ・快照 ＝ 定版同一份 ~/h2data/edc6f8002f…/data（rerun17.use_snapshot），只多注入 revenue_delisted 一批月營收
  ・revenue_delisted ＝ origin/main 1ab51f2820 的 data/meta/revenue_delisted/revenue_delisted.csv（原樣抽到 ~/dlrevdata/1ab51f2820/；sha256 寫死、不符即停）
    FinMind 第三方、千元；⚠ 可能為重編後值（2608 例），本件分不出 ⇒ 結果句照註
  ・注入規則：只填 revenue_hist 該格為空的 (代號, 期別)；revenue_hist 已有值的格一律不動（重疊格另報 ±1 千元相符率）；期別只收 revenue_hist 既有期別範圍（2015-01～2026-08）
  ・可用日：照全線口徑 ⇒ 注入格的期別 ＜ 2026-01 用「次月 10 日之後」（＝ 定版 research34.rebalance_dates pub_day＝10），≥ 2026-01 用「次月 15 日之後」；⛔ 不用 finmind_date
    （定版原有列一律不動：仍是 pub_day＝10）
 重建（＝ rerun17_build 四步，策略邏輯一律呼叫原函式，不改任何參數）
  ① 面板 research34.process_stock（liq_mode＝shares）；② S ＝ 定版 sig_edc6f/signals_S.csv.gz 原檔（純價格、與營收無關）；③ research13.and_flags；④ researchp1.attach_features
  ・空注入版（null）：①～④ 全量重建 ⇒ 面板與定版 panel_rev 排序後逐格相同、AND 檔解壓後逐位元組相同，否則停
  ・注入版（merged）：只重算注入到的股（其餘股的面板列取 null 版原列；process_stock 每股只讀自己那一欄、期別索引不變 ⇒ 等價，另以閘驗）
 引擎變體（兩者並列，⛔ 不擇優）
  ⓐ 定版引擎原式：AND 表 xpos＜0 的列由 simulate_mtm 丟掉（持有期內下市 ⇒ 該訊號整筆不進場）
  ⓑ 下市末根出場：AND 表中屬於「2015 後停止交易普通股 152 家」的列，若 xpos＜0 的原因是資料在出場根之前結束、期間無壞根、且最後一根不在日曆尾
    （＝ rerun17.t1_censor 的 delist_or_halt_end 類）⇒ xpos ＝ 最後一根、g ＝ 最後一根收盤 ÷ 進場開盤 − 1（照 t1_censor 同式）；null 與 merged 都套
 重跑 ＝ researchYL_integrate.main_world（T1fix 定版：營量 c13 t1 r0、營飆 c1 t1 r0～199），只把 AND 檔路徑換成本件的檔（monkeypatch rerun17.setup_and 的 and_path 參數）
  段 ＝ 探索 2017-03-02～2021-12-30、確認 2022-01-03～2026-08-24（另附主窗供對帳）；年化、回落 ＝ rerun17.win_metrics；比值 ＝ 年化 ÷ |回落|；對 0050 ＝ researchYL_integrate.label
  營飆報 200 顆中位〔p10～p90〕；另報同顆配對差中位
 新增訊號：merged AND − null AND（鍵 sid、k）；窗內筆數、有閘筆數、持有期內下市筆數；訊號層淨報酬（g − 0.585%）；
  交易層：模擬裡實際買進的新增列（營量 1 條、營飆 200 顆平均）筆數、淨報酬平均、以末根收盤出場的比例
 缺口（⛔ 不當正式訊號）：152 家中沒有月營收的 80 家 ⇒ fs_xbrl revenue_ytd 單季化、「單季營收 ≥ 前 8 季最大值（8 季都要有）」＝ 季旗標
  可用日 ＝ filing_dates（t57sb01）上傳日的下一個交易日（同季有 AI1 取 AI1 最早、否則最早文件；沒有 ⇒ 法定期限 Q1 5/15、Q2 8/14、Q3 11/14、Q4 次年 3/31 的下一交易日，另報筆數）
  S 列（純價格 3/5 訊號）訊號日當下最新一季（距可用日 ≤ 140 個交易日）季旗標為真 ⇒「可能入選」
  校準：有月營收的股，季旗標「可能」對實際 AND 的命中率（precision）與涵蓋率（recall）；估計受影響筆數 ＝ 80 家可能入選筆數 × precision
 結果句必附：「2015～2020 下市公司仍有約 80 家補不回，偏差只修正一部分」；FinMind 第三方、可能為重編後值
輸出 backtest/resultsDelistRev/：sig_null/、sig_merged/、seeds.csv.gz、cells.csv、new_signals.csv、gap_rows.csv、summary.json、REPORT.md、run.log
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import rerun17 as RR                           # noqa: E402

RR.use_snapshot()
from backtest import data as D                               # noqa: E402
from backtest import patterns as PT                          # noqa: E402
from backtest import research11 as R                         # noqa: E402
from backtest import research13 as R13                       # noqa: E402
from backtest import research34 as R34                       # noqa: E402
from backtest import researchp1 as P1                        # noqa: E402
from backtest import universe_gate as UG                     # noqa: E402
from backtest import researchYL_integrate as IG              # noqa: E402

TIME = "2026-10-21（台北）"
OUT = "backtest/resultsDelistRev"
NSEED = 200
if os.environ.get("DLREV_QUICK"):
    NSEED, OUT = 3, "/tmp/dlrev_quick"
DATA_COMMIT = "1ab51f2820df86eb41a17a1a403bf56eca4d9041"
DLD = os.path.expanduser("~/dlrevdata/1ab51f2820")
DL_SHA256 = "8a5f0681957720ff01ebd0f9deb3e1e1c69310f39bdc39313de7475366493f1b"
LOCK_DIR = os.path.join(RR.OUT, "sig_edc6f")
POP_LO, POP_CUT = "2015-01-01", "2026-09-30"                 # revenue_delisted build.py：last_seen ≥ 2015-01-01 且 ＜ 建置日（10-20）前 20 天
NEW15 = "2026-01"
COST = R.COST
SEGS = ("探索", "確認", "主窗")
REPSEG = ("探索", "確認")
WORD = "描述、不改標籤、不計 N"
STALE_Q = 140
LEGAL = {1: (0, 5, 15), 2: (0, 8, 14), 3: (0, 11, 14), 4: (1, 3, 31)}
SENT = "2015～2020 下市公司仍有約 80 家補不回，偏差只修正一部分"
NOTE_SRC = "下市公司月營收來自 FinMind（第三方、非官方；與官方重疊 1,692 期全符）；可能為重編後值，本件分不出"
VARS = (("null_a", "定版（重現）"), ("merged_a", "補下市營收｜定版引擎"), ("null_b", "定版＋下市末根出場"), ("merged_b", "補下市營收＋下市末根出場"))
_W: dict = {}
_AND_PATH = {"p": None}


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


def sha16(eq):
    return hashlib.sha256(np.asarray(eq, float).tobytes()).hexdigest()[:16]


def fsha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def log_to(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    f = open(path, "a", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); f.write(m + "\n"); f.flush()
    return log


# ═════════════ 資料 ═════════════
def load_pop():
    st = pd.read_csv(os.path.join(DLD, "stocks.csv"), dtype=str)
    pop = st[(st["kind"] == "stock") & (st["last_seen"] >= POP_LO) & (st["last_seen"] < POP_CUT)].copy()
    pop["下市年"] = pop["last_seen"].str[:4]
    return pop.reset_index(drop=True)


def load_dl():
    p = os.path.join(DLD, "revenue_delisted", "revenue_delisted.csv")
    if fsha(p) != DL_SHA256:
        raise SystemExit("⛔ revenue_delisted.csv sha256 不符")
    return pd.read_csv(p, dtype={"stock_id": str, "period": str})


def merge_rev(rev, rev_ly, DL):
    """只填空格；回 (rev_m, rev_ly_m, filled{(sid,p)}, 統計)。"""
    sids = sorted(set(DL["stock_id"]))
    cols = list(rev.columns) + [s for s in sids if s not in rev.columns]
    rev_m = rev.reindex(columns=cols); rly_m = rev_ly.reindex(columns=cols)
    filled, ov, ov_ok, outside, ovbad = set(), 0, 0, 0, []
    for s, p, v in zip(DL["stock_id"], DL["period"], DL["revenue_k"].astype(float)):
        if p not in rev_m.index:
            outside += 1; continue
        cur = rev_m.at[p, s]
        if pd.isna(cur):
            rev_m.at[p, s] = v; filled.add((s, p))
        else:
            ov += 1
            if abs(float(cur) - v) <= 1:
                ov_ok += 1
            elif len(ovbad) < 10:
                ovbad.append((s, p, float(cur), v))
    st = {"注入格": len(filled), "注入股": len({s for s, _ in filled}), "與 revenue_hist 重疊格": ov, "重疊格 ±1 千元相符": ov_ok,
          "重疊不符例": ovbad, "期別範圍外略過": outside, "原已在 revenue_hist 的代號": sorted(s for s in sids if s in rev.columns),
          "注入格 ≥2026-01（用 15 日）": sum(1 for _, p in filled if p >= NEW15)}
    return rev_m, rly_m, filled, st


def run_panel(cal, bench, disp, rev, rev_ly, rdates, lo, hi, jobs, procs):
    rows = []
    with Pool(procs, initializer=R34._init, initargs=(cal, bench, disp, rev, rev_ly, rdates, lo, hi)) as pool:
        for r in pool.imap_unordered(R34.process_stock, jobs, chunksize=8):
            if r:
                rows += r
    return rows


def finish_panel(rows, cal, path):
    panel = pd.DataFrame(rows)
    for c in ("rev_hi12", "rev_hi24", "rev_hi36", "bull"):
        if c in panel:
            panel[c] = panel[c].astype("boolean")
    panel["signal_date"] = [cal[i].strftime("%Y-%m-%d") for i in panel["signal_pos"]]
    panel["entry_date"] = [cal[i].strftime("%Y-%m-%d") for i in panel["entry_pos"]]
    panel.to_csv(path, index=False, compression="gzip")
    return pd.read_csv(path, dtype={"stock_id": str})


def norm_panel(p):
    p = p.sort_values(["stock_id", "period"]).reset_index(drop=True)
    return p[sorted(p.columns)]


def build_and(pnl_path, cal, uni_mk, procs, out_path):
    pnl = pd.read_csv(pnl_path, dtype={"stock_id": str})
    pnl["rev_hi24"] = pnl["rev_hi24"].fillna(False).astype(bool)
    S = pd.read_csv(os.path.join(LOCK_DIR, "signals_S.csv.gz"), dtype={"sid": str})
    S = S[["sid", "k", "pos", "entry_pos", "month", "g_H60", "g_H120", "g_LD", "xpos_H60", "xpos_H120", "xpos_LD", "t_LD"]].copy()
    flags, _ = R13.and_flags(S, pnl)
    AND = S[flags].copy()
    missing, mism = P1.attach_features(AND, S, cal, uni_mk, procs)
    if mism or missing:
        raise SystemExit(f"⛔ attach_features k↔pos 不符 {mism}／讀不到 {missing[:5]}")
    AND.to_csv(out_path, index=False)
    return AND


def gz_bytes(p):
    return gzip.open(p, "rb").read()


def delist_fill(AND, cal, mk, popset):
    """ⓑ：持有期內下市（資料在出場根前結束、無壞根、最後一根不在日曆尾）⇒ 末根收盤出場（t1_censor 同式，只是出場根 ＝ 最後一根）。"""
    A = AND.copy(); ncal = len(cal); filled = []
    bars = {}
    for H in (60, 120):
        for i in A.index[(A[f"xpos_H{H}"] < 0) & A["sid"].isin(popset)]:
            s = A.at[i, "sid"]
            if s not in bars:
                B = R.load_bars(s, mk.get(s, "twse"), cal)
                bars[s] = None if B is None else (B["idx"], B["next_bad"], B["o"], B["c"])
            b = bars[s]
            if b is None:
                continue
            idx, nb, o, c = b; k = int(A.at[i, "k"]); n = len(idx)
            if int(idx[k]) != int(A.at[i, "pos"]) or k + 1 > n - 1:
                continue
            if D.exit_pos(k + 1, H) < n or nb[max(0, k - 20)] <= n - 1 or int(idx[n - 1]) >= ncal - 1:
                continue
            A.at[i, f"xpos_H{H}"] = int(idx[n - 1]); A.at[i, f"g_H{H}"] = float(c[n - 1] / o[k + 1] - 1.0)
            filled.append({"sid": s, "k": k, "H": H, "entry_pos": int(A.at[i, "entry_pos"]), "xpos": int(idx[n - 1]),
                           "末根日": str(cal[int(idx[n - 1])].date()), "g": float(c[n - 1] / o[k + 1] - 1.0)})
    return A, pd.DataFrame(filled)


# ═════════════ 模擬 ═════════════
_ORIG_SETUP_AND = RR.setup_and


def _setup_and_patched(cal, and_path, px, log, t1=False):
    return _ORIG_SETUP_AND(cal, _AND_PATH["p"], px, log, t1=t1)


RR.setup_and = _setup_and_patched


def trades_of(au, n):
    op, T = {}, []
    for a in au:
        if a["side"] == "buy":
            if a["sid"] in op:
                raise SystemExit(f"⛔ {a['sid']} 重複買進")
            op[a["sid"]] = (a["t"], a["amt"], a["px"], a["equity_prev"])
        else:
            tb, amt, px, ep_ = op.pop(a["sid"])
            T.append((a["sid"], tb, a["t"], amt, px, a["px"], ep_))
    for s, (tb, amt, px, ep_) in op.items():
        T.append((s, tb, n, amt, px, np.nan, ep_))
    return T


def seed_stats(W, o, au):
    eq = np.asarray(o["equity"], float); n = len(eq)
    row = {"eq_sha": sha16(eq), "first": int(o["first"]), "end": int(o["end"]), "trades": int(o["trades"])}
    for sg in SEGS:
        x, y = W["segp"][sg]
        c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], x, y)
        row[f"{sg}_年化"] = float(c_); row[f"{sg}_回落"] = float(m_)
    NEW = W["NEW"]; FILL = W["FILLK"]; SF = W["SF"]
    nets, dl, cons, segc = [], 0, 0.0, {sg: 0 for sg in REPSEG}
    for s, tb, ts, amt, pin, pout, ep_ in trades_of(au, n):
        if (s, tb) not in NEW:
            continue
        if not np.isfinite(pout):
            pout = float(W["closes"][s][min(o["end"], W["NP"]) - 1])
        r_ = pout / pin - 1.0 - COST
        nets.append(r_); cons += amt * r_ / ep_
        if (s, tb) in FILL or (s in SF and ts >= SF[s]):
            dl += 1
        for sg in REPSEG:
            x, y = W["segp"][sg]
            if x <= tb <= y:
                segc[sg] += 1
    row["新增買進"] = len(nets); row["新增淨報酬和"] = float(np.sum(nets)) if nets else 0.0
    row["新增淨報酬平均"] = float(np.mean(nets)) if nets else np.nan; row["新增末根出場"] = dl; row["新增貢獻和"] = float(cons)
    row["新增勝"] = int(np.sum(np.array(nets) > 0)) if nets else 0
    for sg in REPSEG:
        row[f"新增買進_{sg}"] = segc[sg]
    return row


def job(args):
    vn, r = args
    W = _W[vn]
    o, au = IG.eng(W, IG.YF, r)
    return {"變體": vn, "策略": "營飆", "r": r, **seed_stats(W, o, au)}


def make_world(vn, path, newkeys, fillkeys, log):
    _AND_PATH["p"] = path
    W, gate = IG.main_world(log)
    W["NEW"] = newkeys; W["FILLK"] = fillkeys
    log(f"[{vn}] main_world 閘（ⓑ 補出場的列會與重算出場不同，屬預期）{gate}")
    return W, gate


# ═════════════ 缺口：季旗標 ═════════════
def qkey(y, q):
    return int(y) * 4 + int(q) - 1


def gap_stage(cal, S, AND_null, AND_merged, pop, have, uni_set, reg, w0, w1, segp, log):
    import glob
    fs = pd.concat([pd.read_csv(f, dtype={"stock_id": str, "period": str}, usecols=["period", "stock_id", "report", "revenue_ytd"])
                    for f in sorted(glob.glob(os.path.join(DLD, "fs_xbrl", "fs_xbrl_*.csv")))])
    fs = fs[fs["stock_id"].isin(uni_set)].copy()
    fs["qk"] = [qkey(p[:4], p[5]) for p in fs["period"]]
    fs = fs.sort_values(["stock_id", "qk", "report"]).drop_duplicates(["stock_id", "qk"], keep="first")   # cr 先於 ir
    ytd = fs.set_index(["stock_id", "qk"])["revenue_ytd"].astype(float)
    fd = pd.read_csv(os.path.join(DLD, "filing_dates.csv"), dtype=str)
    fd["d"] = pd.to_datetime(fd["uploaded_at"], errors="coerce"); fd = fd.dropna(subset=["d"])
    fd["qk"] = [qkey(a, b) for a, b in zip(fd["year"], fd["season"])]
    ai1 = fd[fd["doc_code"] == "AI1"].groupby(["stock_id", "qk"])["d"].min()
    anyd = fd.groupby(["stock_id", "qk"])["d"].min().to_dict(); anyd.update(ai1.to_dict())
    cal_d = cal.normalize()
    Q = {}; nfb = {"上傳時戳": 0, "法定期限": 0}
    for s, g in ytd.groupby(level=0):
        g = g.droplevel(0)
        single = {}
        for k, v in g.items():
            if not np.isfinite(v):
                continue
            if k % 4 == 0:
                single[k] = v
            elif (k - 1) in g.index and np.isfinite(g[k - 1]):
                single[k] = v - g[k - 1]
        ks = sorted(single); flag = {}; av = {}
        for k in ks:
            prev = [single.get(k - j) for j in range(1, 9)]
            flag[k] = bool(all(p is not None for p in prev) and single[k] >= max(prev))
            d = anyd.get((s, k))
            if d is not None:
                nfb["上傳時戳"] += 1
            else:
                y, q = k // 4, k % 4 + 1; dy, m, dd = LEGAL[q]; d = pd.Timestamp(year=y + dy, month=m, day=dd); nfb["法定期限"] += 1
            av[k] = int(cal_d.searchsorted(pd.Timestamp(d).normalize(), side="right"))   # 上傳日的下一個交易日
        Q[s] = (np.array(ks, int), np.array([av[k] for k in ks], int), np.array([flag[k] for k in ks], bool))

    def qflag(s, pos):
        if s not in Q:
            return None
        ks, av, fl = Q[s]
        ok = np.flatnonzero(av <= pos)
        if not len(ok):
            return None
        j = ok[np.argmax(ks[ok])]
        if pos - av[j] > STALE_Q:
            return None
        return bool(fl[j])

    e = S["entry_pos"].to_numpy(int)
    Sw = S[(e >= w0) & (e <= w1)].copy()
    Sw["閘開"] = reg[Sw["entry_pos"].to_numpy(int) - 1]
    Sw["季旗標"] = [qflag(s, int(p)) for s, p in zip(Sw["sid"], Sw["pos"])]
    kn = set(zip(AND_null["sid"], AND_null["k"])); km = set(zip(AND_merged["sid"], AND_merged["k"]))
    Sw["AND_null"] = [(s, k) in kn for s, k in zip(Sw["sid"], Sw["k"])]
    Sw["AND_merged"] = [(s, k) in km for s, k in zip(Sw["sid"], Sw["k"])]
    popset = set(pop["stock_id"]); miss = popset - have
    Sw["群"] = np.where(Sw["sid"].isin(miss), "缺80", np.where(Sw["sid"].isin(have), "補72", "其他"))
    out = {"季可用日來源（季數）": nfb}

    def conf(df, col):
        d = df[df["季旗標"].notna()]
        qt = d["季旗標"].astype(bool); a = d[col].astype(bool)
        tp = int((qt & a).sum())
        return {"S列": int(len(df)), "季旗標可判": int(len(d)), "季旗標真": int(qt.sum()), "AND": int(a.sum()), "兩者皆真": tp,
                "precision（季真中AND）": tp / int(qt.sum()) if qt.sum() else np.nan, "recall（AND中季真）": tp / int(a.sum()) if a.sum() else np.nan}
    out["校準_有月營收的其他股（AND_null）"] = conf(Sw[Sw["群"] == "其他"], "AND_null")
    out["驗證_補72（AND_merged）"] = conf(Sw[Sw["群"] == "補72"], "AND_merged")
    prec = out["校準_有月營收的其他股（AND_null）"]["precision（季真中AND）"]
    g80 = Sw[Sw["群"] == "缺80"]
    rec = {"缺80家數": len(miss), "缺80在母體閘內": len(miss & uni_set), "窗內有S列的家數": int(g80["sid"].nunique()), "窗內S列": int(len(g80)),
           "季旗標可判": int(g80["季旗標"].notna().sum()), "季旗標真（可能入選）": int((g80["季旗標"] == True).sum()),
           "其中閘開（營飆可進）": int(((g80["季旗標"] == True) & g80["閘開"]).sum()),
           "估計受影響AND筆數（×precision）": float((g80["季旗標"] == True).sum() * prec) if np.isfinite(prec) else np.nan}
    for sg in REPSEG:
        x, y = segp[sg]; m_ = (g80["entry_pos"] >= x) & (g80["entry_pos"] <= y)
        rec[f"{sg}_S列"] = int(m_.sum()); rec[f"{sg}_季旗標真"] = int((m_ & (g80["季旗標"] == True)).sum())
    yy = pop.set_index("stock_id")["下市年"]
    rec["可能入選_依下市年"] = g80[g80["季旗標"] == True]["sid"].map(yy).value_counts().sort_index().to_dict()
    rec["缺80_依下市年"] = pop[pop["stock_id"].isin(miss)]["下市年"].value_counts().sort_index().to_dict()
    rec["窗內S列_依下市年"] = g80["sid"].map(yy).value_counts().sort_index().to_dict()
    out["缺80"] = rec
    out["窗內AND筆數_null"] = int(Sw["AND_null"].sum())
    g80.assign(訊號日=[str(cal[int(p)].date()) for p in g80["pos"]]).to_csv(os.path.join(OUT, "gap_rows.csv"), index=False, encoding="utf-8-sig")
    log(f"[缺口] {json.dumps(out, ensure_ascii=False, default=float)}")
    return out


# ═════════════ 主流程 ═════════════
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    for d in ("sig_null", "sig_merged"):
        os.makedirs(os.path.join(OUT, d), exist_ok=True)
    log = log_to(os.path.join(OUT, "run.log"))
    log(f"[開始] {now_tpe()}（台北）｜讀法寫死 {TIME}｜快照 {RR.SHA[:10]}｜資料 {DATA_COMMIT[:10]}｜D.DATA {D.DATA}")
    S_ = {"讀法寫死": TIME, "性質": WORD, "快照": RR.SHA, "資料commit": DATA_COMMIT, "revenue_delisted_sha256": DL_SHA256,
          "signals_S_sha256": fsha(os.path.join(LOCK_DIR, "signals_S.csv.gz")), "結果句": SENT, "來源註": NOTE_SRC, "閘": {}}
    cal = D.load_calendar()
    stocks = pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str)
    uni = D.load_universe().merge(UG.gate3(stocks)[["stock_id"]], on="stock_id")
    uni_mk = uni.set_index("stock_id")["market"]; uni_set = set(uni["stock_id"])
    pop = load_pop(); DL = load_dl(); have = set(DL["stock_id"]); popset = set(pop["stock_id"])
    if not have <= popset or len(pop) != 152 or len(have) != 72:
        raise SystemExit(f"⛔ 母體 {len(pop)}／有資料 {len(have)} 與交件不符")
    S_["母體"] = {"152家": len(pop), "有月營收72": len(have), "缺80": len(popset - have), "72家在母體閘內": len(have & uni_set),
                "依下市年_有": pop[pop["stock_id"].isin(have)]["下市年"].value_counts().sort_index().to_dict(),
                "依下市年_缺": pop[~pop["stock_id"].isin(have)]["下市年"].value_counts().sort_index().to_dict(),
                "72家不在母體閘內": sorted(have - uni_set)}
    # ── ① 面板 ──
    PT.PARAMS["liq_mode"] = "shares"
    bdf = D.load_benchmark(cal); bench = {"o": bdf["open"].to_numpy(float), "c": bdf["close"].to_numpy(float)}
    disp = D.load_disposal_intervals()
    rev, rev_ly, _ind = R34.load_revenue()
    rd10 = R34.rebalance_dates(list(rev.index), cal, 10); rd15 = R34.rebalance_dates(list(rev.index), cal, 15)
    rdmix = {p: (rd10[p] if p < NEW15 else rd15[p]) for p in rev.index if p in rd10 and p in rd15}
    lo = int(cal.searchsorted(pd.Timestamp(R34.SIG_START))); hi = int(cal.searchsorted(pd.Timestamp(R34.SIG_END), side="right") - 1)
    jobs = list(zip(uni["stock_id"], uni["market"], uni["first_seen"], uni["last_seen"]))
    T0 = time.time()
    pn_path = os.path.join(OUT, "sig_null", "panel_rev.csv.gz")
    pnl_null = finish_panel(run_panel(cal, bench, disp, rev, rev_ly, rd10, lo, hi, jobs, a.procs), cal, pn_path)
    lock_pnl = pd.read_csv(os.path.join(LOCK_DIR, "panel_rev.csv.gz"), dtype={"stock_id": str})
    g0 = norm_panel(pnl_null).equals(norm_panel(lock_pnl))
    S_["閘"]["G0 null 面板 ＝ 定版 panel_rev（排序後逐格）"] = int(not g0)
    log(f"[①null] {len(pnl_null):,} 列｜＝定版 {g0}｜{time.time() - T0:.0f}s")
    if not g0:
        raise SystemExit("⛔ null 面板與定版不同")
    rev_m, rly_m, filled, mst = merge_rev(rev, rev_ly, DL)
    if not (rev_m.index.equals(rev.index) and rev_m[list(rev.columns)].equals(rev)):
        raise SystemExit("⛔ 注入改到既有格")
    S_["注入"] = mst
    aff = sorted(have & uni_set)
    jobs_aff = [j for j in jobs if j[0] in set(aff)]
    rowsA = run_panel(cal, bench, disp, rev_m, rly_m, rd10, lo, hi, jobs_aff, a.procs)
    rowsB = run_panel(cal, bench, disp, rev_m, rly_m, rdmix, lo, hi, jobs_aff, a.procs)

    def use15(s, p):
        return p >= NEW15 and (s not in rev.columns or (s, p) in filled)
    sel = [r for r in rowsA if not use15(r["stock_id"], r["period"])] + [r for r in rowsB if use15(r["stock_id"], r["period"])]
    keep = pnl_null[~pnl_null["stock_id"].isin(set(aff))]
    newp = pd.DataFrame(sel)
    for c in ("rev_hi12", "rev_hi24", "rev_hi36", "bull"):
        if c in newp:
            newp[c] = newp[c].astype("boolean")
    newp["signal_date"] = [cal[i].strftime("%Y-%m-%d") for i in newp["signal_pos"]]
    newp["entry_date"] = [cal[i].strftime("%Y-%m-%d") for i in newp["entry_pos"]]
    newp["rev_src"] = ["finmind" if (s, p) in filled else "revenue_hist" for s, p in zip(newp["stock_id"], newp["period"])]
    newp["pub_day"] = [15 if use15(s, p) else 10 for s, p in zip(newp["stock_id"], newp["period"])]
    newp.to_csv(os.path.join(OUT, "sig_merged", "panel_injected_rows.csv.gz"), index=False, compression="gzip")
    pm_path = os.path.join(OUT, "sig_merged", "panel_rev.csv.gz")
    pd.concat([keep, newp.drop(columns=["rev_src", "pub_day"])], ignore_index=True).to_csv(pm_path, index=False, compression="gzip")
    S_["注入面板"] = {"重算股": len(aff), "重算列": len(newp), "其中 15 日口徑列": int((newp["pub_day"] == 15).sum()),
                  "rev_hi24 真（重算股）": int((newp["rev_hi24"] == True).sum()),
                  "rev_hi24 真（同股 null）": int((pnl_null[pnl_null["stock_id"].isin(set(aff))]["rev_hi24"] == True).sum())}
    log(f"[①merged] {S_['注入']}｜{S_['注入面板']}")
    # ── ③④ AND ──
    an_path = os.path.join(OUT, "sig_null", "and_signals.csv.gz"); am_path = os.path.join(OUT, "sig_merged", "and_signals.csv.gz")
    AND_null = build_and(pn_path, cal, uni_mk, a.procs, an_path)
    g1 = gz_bytes(an_path) == gz_bytes(os.path.join(LOCK_DIR, "and_signals.csv.gz"))
    S_["閘"]["G1 null AND ＝ 定版 and_signals（解壓逐位元組）"] = int(not g1)
    if not g1:
        raise SystemExit("⛔ null AND 與定版不同")
    AND_m = build_and(pm_path, cal, uni_mk, a.procs, am_path)
    kn = set(zip(AND_null["sid"], AND_null["k"])); km = set(zip(AND_m["sid"], AND_m["k"]))
    oth = AND_m[~AND_m["sid"].isin(set(aff))].reset_index(drop=True); othn = AND_null[~AND_null["sid"].isin(set(aff))].reset_index(drop=True)
    S_["閘"]["G2 未注入股的 AND 列 merged ＝ null"] = int(not oth.equals(othn))
    log(f"[③④] null {len(AND_null):,}｜merged {len(AND_m):,}｜新增 {len(km - kn)}｜消失 {len(kn - km)}｜{time.time() - T0:.0f}s")
    # ── ⓑ 下市末根出場 ──
    paths = {"null_a": an_path, "merged_a": am_path}
    FILL = {}
    for vn, A0, d in (("null_b", AND_null, "sig_null"), ("merged_b", AND_m, "sig_merged")):
        Ab, fl = delist_fill(A0, cal, uni_mk, popset)
        p = os.path.join(OUT, d, "and_signals_delistexit.csv.gz"); Ab.to_csv(p, index=False)
        fl.to_csv(os.path.join(OUT, d, "delistexit_rows.csv"), index=False, encoding="utf-8-sig")
        paths[vn] = p; FILL[vn] = fl
        log(f"[ⓑ {vn}] 補出場 H60 {int((fl['H'] == 60).sum()) if len(fl) else 0}｜H120 {int((fl['H'] == 120).sum()) if len(fl) else 0}")
    S_["ⓑ補出場列"] = {vn: {"H60": int((f["H"] == 60).sum()) if len(f) else 0, "H120": int((f["H"] == 120).sum()) if len(f) else 0,
                       "其中新增列": int(sum((s, k) not in kn for s, k in zip(f["sid"], f["k"]))) if len(f) else 0} for vn, f in FILL.items()}
    # ── 新增訊號表 ──
    newk = km - kn
    NEWT = AND_m[[(s, k) in newk for s, k in zip(AND_m["sid"], AND_m["k"])]].copy()
    bench0 = RR.load_bench(cal); reg = RR.regime_mask(bench0); w0, w1 = RR.win_bounds(cal)
    segp = {"主窗": (w0, w1), **{sg: (int(cal.searchsorted(pd.Timestamp(x))), int(cal.searchsorted(pd.Timestamp(y)))) for sg, (x, y) in IG.SEG_M.items()}}
    e = NEWT["entry_pos"].to_numpy(int)
    NEWT["窗內"] = (e >= w0) & (e <= w1); NEWT["閘開"] = reg[e - 1]
    NEWT["段"] = np.where((e >= segp["探索"][0]) & (e <= segp["探索"][1]), "探索", np.where((e >= segp["確認"][0]) & (e <= segp["確認"][1]), "確認", "窗外"))
    NEWT["訊號日"] = [str(cal[int(p)].date()) for p in NEWT["pos"]]; NEWT["進場日"] = [str(cal[int(p)].date()) for p in NEWT["entry_pos"]]
    ls = pop.set_index("stock_id")["last_seen"]; NEWT["last_seen"] = NEWT["sid"].map(ls)
    fb = FILL["merged_b"]; fbk = {(s, k, H): g for s, k, H, g in zip(fb["sid"], fb["k"], fb["H"], fb["g"])} if len(fb) else {}
    for H in (60, 120):
        NEWT[f"持有期內下市_H{H}"] = [(s, int(k), H) in fbk for s, k in zip(NEWT["sid"], NEWT["k"])]
        NEWT[f"淨報酬_H{H}_定版引擎"] = np.where(NEWT[f"xpos_H{H}"] >= 0, NEWT[f"g_H{H}"] - COST, np.nan)
        NEWT[f"淨報酬_H{H}_末根出場"] = [((g - COST) if x >= 0 else (fbk[(s, int(k), H)] - COST if (s, int(k), H) in fbk else np.nan))
                                    for s, k, x, g in zip(NEWT["sid"], NEWT["k"], NEWT[f"xpos_H{H}"], NEWT[f"g_H{H}"])]
    NEWT.to_csv(os.path.join(OUT, "new_signals.csv"), index=False, encoding="utf-8-sig")
    gone = AND_null[[(s, k) in (kn - km) for s, k in zip(AND_null["sid"], AND_null["k"])]]
    gone.to_csv(os.path.join(OUT, "gone_signals.csv"), index=False, encoding="utf-8-sig")
    NS = {}
    for nm, m_ in (("窗內", NEWT["窗內"]), ("窗內且閘開", NEWT["窗內"] & NEWT["閘開"]), ("探索", NEWT["段"] == "探索"), ("確認", NEWT["段"] == "確認")):
        d = NEWT[m_]
        rec = {"筆數": int(len(d)), "家數": int(d["sid"].nunique())}
        for H in (60, 120):
            rec[f"持有期內下市_H{H}"] = int(d[f"持有期內下市_H{H}"].sum())
            for v in ("定版引擎", "末根出場"):
                x = d[f"淨報酬_H{H}_{v}"].dropna()
                rec[f"H{H}_{v}_可算"] = int(len(x)); rec[f"H{H}_{v}_淨報酬平均"] = float(x.mean()) if len(x) else np.nan
                rec[f"H{H}_{v}_淨報酬中位"] = float(x.median()) if len(x) else np.nan; rec[f"H{H}_{v}_勝率"] = float((x > 0).mean()) if len(x) else np.nan
        NS[nm] = rec
    S_["新增訊號"] = NS
    S_["消失訊號"] = {"筆數": int(len(gone)), "窗內": int(((gone["entry_pos"] >= w0) & (gone["entry_pos"] <= w1)).sum()), "代號": sorted(set(gone["sid"]))}
    S_["定版窗內訊號"] = int(((AND_null["entry_pos"] >= w0) & (AND_null["entry_pos"] <= w1)).sum())
    log(f"[新增訊號] {json.dumps(NS, ensure_ascii=False, default=float)}｜消失 {S_['消失訊號']}")
    # ── 模擬 ──
    ROWS = []; WG = {}
    for vn, _lab in VARS:
        fk = set()
        fl = FILL.get(vn)
        if fl is not None and len(fl):
            fk = {(s, int(ep)) for s, ep in zip(fl["sid"], fl["entry_pos"])}
        newkeys = {(s, int(ep)) for s, ep in zip(NEWT["sid"], NEWT["entry_pos"])} if vn.startswith("merged") else set()
        W, gate = make_world(vn, paths[vn], newkeys, fk, log)
        WG[vn] = gate
        _W.clear(); _W[vn] = W
        o, au = IG.eng(W, IG.YL, 0)
        ROWS.append({"變體": vn, "策略": "營量", "r": 0, **seed_stats(W, o, au)})
        with Pool(a.procs) as pool:
            ROWS += pool.map(job, [(vn, r) for r in range(NSEED)], chunksize=4)
        if vn == "null_a":
            B50 = W["b50"]
        log(f"[{vn}] 完成｜{time.time() - T0:.0f}s")
    S_["main_world閘"] = WG
    SE = pd.DataFrame(ROWS)
    SE.to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False, float_format="%.17g")
    # ── 定版閘 ──
    t1 = pd.read_csv("backtest/resultsT1fix/seeds.csv.gz", dtype={"eq_sha": str}, float_precision="round_trip")
    c13 = t1[(t1["key"] == "c13") & (t1["var"] == "t1") & (t1["r"] == 0)].iloc[0]
    yl0 = SE[(SE["變體"] == "null_a") & (SE["策略"] == "營量")].iloc[0]
    S_["閘"]["G3 營量 null ＝ T1fix c13 t1 r0（eq_sha、年化、回落 repr）"] = int(yl0["eq_sha"] != c13["eq_sha"] or repr(float(yl0["主窗_年化"])) != repr(float(c13["cagr"]))
                                                                   or repr(float(yl0["主窗_回落"])) != repr(float(c13["mdd"])))
    r1 = t1[(t1["key"] == "c1") & (t1["var"] == "t1")].set_index("r")
    m1 = SE[(SE["變體"] == "null_a") & (SE["策略"] == "營飆")].set_index("r")
    S_["閘"]["G4 營飆 null ＝ T1fix c1 t1（不同顆數）"] = int(sum(m1.loc[r, "eq_sha"] != r1.loc[r, "eq_sha"] or repr(float(m1.loc[r, "主窗_年化"])) != repr(float(r1.loc[r, "cagr"]))
                                                       or repr(float(m1.loc[r, "主窗_回落"])) != repr(float(r1.loc[r, "mdd"])) for r in m1.index))
    if NSEED == 200:
        yfn = [z for z in json.load(open("backtest/resultsYF_N/summary.json", encoding="utf-8"))["表"] if z["N"] == 10 and z["世界"] == "主"]
        S_["閘"]["G5 營飆 null 各段中位 ＝ resultsYF_N N10（不同項數）"] = int(sum(repr(float(m1[f"{z['段']}_{k}"].median())) != repr(float(z[f"{k}_中位"]))
                                                                for z in yfn for k in ("年化", "回落")))
    yv = json.load(open("backtest/resultsYLvsYF/summary.json", encoding="utf-8"))["營量"]["主"]
    S_["閘"]["G6 營量 null 各段 ＝ resultsYLvsYF（不同項數）"] = int(sum(repr(float(yl0[f"{sg}_{k}"])) != repr(float(yv[f"{sg}_{k}"])) for sg in SEGS for k in ("年化", "回落")))
    sm = json.load(open("backtest/resultsYL_integrate/summary.json", encoding="utf-8"))["0050"]["主"]
    S_["閘"]["G7 0050 各段 ＝ 整合件（不同項數）"] = int(sum(repr(float(B50[sg][k])) != repr(float(sm[sg][k])) for sg in SEGS for k in ("cagr", "mdd")))
    log(f"[閘] {S_['閘']}")
    bad = [k for k, v in S_["閘"].items() if v != 0]
    if bad:
        json.dump(S_, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
        raise SystemExit(f"⛔ 閘不過 {bad}")
    # ── 彙總表 ──
    C = []
    for vn, lab in VARS:
        for stg in ("營量", "營飆"):
            g = SE[(SE["變體"] == vn) & (SE["策略"] == stg)]
            g0_ = SE[(SE["變體"] == "null_a") & (SE["策略"] == stg)].set_index("r")
            for sg in SEGS:
                b = B50[sg]
                c_, m_ = float(g[f"{sg}_年化"].median()), float(g[f"{sg}_回落"].median())
                row = {"變體": vn, "變體名": lab, "策略": stg, "段": sg, "顆數": len(g), "年化": c_, "回落": m_, "比值": c_ / abs(m_), "對0050": IG.label(c_, m_, b),
                       "年化_p10": float(g[f"{sg}_年化"].quantile(.1)), "年化_p90": float(g[f"{sg}_年化"].quantile(.9)),
                       "回落_p10": float(g[f"{sg}_回落"].quantile(.1)), "回落_p90": float(g[f"{sg}_回落"].quantile(.9)),
                       "0050年化": b["cagr"], "0050回落": b["mdd"], "0050比值": b["cagr"] / abs(b["mdd"])}
                gi = g.set_index("r")
                row["配對差年化_中位"] = float((gi[f"{sg}_年化"] - g0_.loc[gi.index, f"{sg}_年化"]).median())
                row["配對差回落_中位"] = float((gi[f"{sg}_回落"] - g0_.loc[gi.index, f"{sg}_回落"]).median())
                row["新增買進_平均"] = float(g[f"新增買進_{sg}"].mean()) if sg in REPSEG else float(g["新增買進"].mean())
                C.append(row)
    C = pd.DataFrame(C)
    base = C[C["變體"] == "null_a"].set_index(["策略", "段"])
    for k in ("年化", "回落", "比值"):
        C[f"Δ{k}"] = [r[k] - base.loc[(r["策略"], r["段"]), k] for _, r in C.iterrows()]
    C["標籤變"] = [r["對0050"] != base.loc[(r["策略"], r["段"]), "對0050"] for _, r in C.iterrows()]
    C.to_csv(os.path.join(OUT, "cells.csv"), index=False, encoding="utf-8-sig", float_format="%.10g")
    S_["表"] = C.to_dict("records")
    TR = {}
    for vn in ("merged_a", "merged_b"):
        for stg in ("營量", "營飆"):
            g = SE[(SE["變體"] == vn) & (SE["策略"] == stg)]
            nb = g["新增買進"].sum()
            TR[f"{vn}_{stg}"] = {"每條新增買進（平均）": float(g["新增買進"].mean()), "探索": float(g["新增買進_探索"].mean()), "確認": float(g["新增買進_確認"].mean()),
                                "淨報酬平均（合併所有顆）": float(g["新增淨報酬和"].sum() / nb) if nb else np.nan,
                                "勝率": float(g["新增勝"].sum() / nb) if nb else np.nan,
                                "末根出場占比": float(g["新增末根出場"].sum() / nb) if nb else np.nan,
                                "對組合貢獻和（平均）": float(g["新增貢獻和"].mean())}
    S_["新增交易"] = TR
    # ── 缺口 ──
    S = pd.read_csv(os.path.join(LOCK_DIR, "signals_S.csv.gz"), dtype={"sid": str}, usecols=["sid", "k", "pos", "entry_pos"])
    S_["缺口"] = gap_stage(cal, S, AND_null, AND_m, pop, have, uni_set, reg, w0, w1, segp, log)
    S_["完成（台北）"] = now_tpe()
    json.dump(S_, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    report(S_, C)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    log("\n" + C[C["段"] != "主窗"][["變體", "策略", "段", "年化", "回落", "比值", "對0050", "Δ年化", "Δ回落", "配對差年化_中位", "新增買進_平均"]].to_string(index=False))
    log(f"[完] {now_tpe()}（台北）")


def pct(v, d=1):
    return "—" if v is None or not np.isfinite(v) else f"{v * 100:.{d}f}%"


def sgn(v, d=1):
    return "—" if v is None or not np.isfinite(v) else f"{v * 100:+.{d}f}%"


def report(S, C):
    L = ["# 補下市公司月營收：營量 v1、營飆 v1 主世界兩段對帳", "", f"產出 {S['完成（台北）']}（台北）。回測線計算子代理。⭐ {WORD}。", "",
         f"⚠ 結果句：「{SENT}」。{NOTE_SRC}。", "",
         f"資料：快照 {S['快照'][:10]}（定版同一份）＋ revenue_delisted（main {S['資料commit'][:10]}，sha256 {S['revenue_delisted_sha256'][:16]}…）；"
         f"注入 {S['注入']['注入格']:,} 格／{S['注入']['注入股']} 家（≥2026-01 用 15 日口徑 {S['注入']['注入格 ≥2026-01（用 15 日）']} 格）；"
         f"與 revenue_hist 重疊 {S['注入']['與 revenue_hist 重疊格']} 格、±1 千元相符 {S['注入']['重疊格 ±1 千元相符']}。", "",
         "## ① 兩策略：定版 vs 補下市（營飆 200 顆中位；比值 ＝ 年化 ÷ |回落|）", "",
         "| 策略 | 段 | 變體 | 年化 | 回落 | 比值 | 對 0050 | Δ年化 | Δ回落 | 同顆配對差中位（年化） |", "|---|---|---|---|---|---|---|---|---|---|"]
    for stg in ("營量", "營飆"):
        for sg in REPSEG:
            for vn, lab in VARS:
                r = C[(C["策略"] == stg) & (C["段"] == sg) & (C["變體"] == vn)].iloc[0]
                L.append(f"| {stg} | {sg} | {lab} | {sgn(r['年化'])} | {sgn(r['回落'])} | {r['比值']:.2f} | {r['對0050']} | {sgn(r['Δ年化'], 2)} | {sgn(r['Δ回落'], 2)} | "
                         f"{sgn(r['配對差年化_中位'], 2) if stg == '營飆' else '—'} |")
    b = C[(C["變體"] == "null_a") & (C["策略"] == "營量")].set_index("段")
    L += ["", "0050：" + "；".join(f"{sg} {sgn(b.loc[sg, '0050年化'])}／{sgn(b.loc[sg, '0050回落'])}／{b.loc[sg, '0050比值']:.2f}" for sg in REPSEG), "",
          "⚠ 定版引擎（ⓐ）會把「持有期內下市」的訊號整筆丟掉（xpos＜0 不進場）；ⓑ 改為以末根收盤出場（rerun17.t1_censor 同式）。兩者並列，⛔ 不擇優。", "",
          "## ② 新增訊號（merged AND − null AND）", "", "| 範圍 | 筆數／家數 | 持有期內下市 H60／H120 | H60 淨報酬平均 定版引擎／末根出場 | H120 淨報酬平均 定版引擎／末根出場 |", "|---|---|---|---|---|"]
    for nm, r in S["新增訊號"].items():
        L.append(f"| {nm} | {r['筆數']}／{r['家數']} | {r['持有期內下市_H60']}／{r['持有期內下市_H120']} | "
                 f"{sgn(r['H60_定版引擎_淨報酬平均'])}（{r['H60_定版引擎_可算']}）／{sgn(r['H60_末根出場_淨報酬平均'])}（{r['H60_末根出場_可算']}） | "
                 f"{sgn(r['H120_定版引擎_淨報酬平均'])}（{r['H120_定版引擎_可算']}）／{sgn(r['H120_末根出場_淨報酬平均'])}（{r['H120_末根出場_可算']}） |")
    L += ["", f"定版窗內訊號 {S['定版窗內訊號']:,} 筆；消失訊號 {S['消失訊號']['筆數']} 筆（窗內 {S['消失訊號']['窗內']}）。", "",
          "交易層（模擬中實際買進的新增列）：", "", "| 變體·策略 | 每條新增買進 | 探索／確認 | 淨報酬平均 | 勝率 | 末根出場占比 | 對組合貢獻和 |", "|---|---|---|---|---|---|---|"]
    for k, r in S["新增交易"].items():
        L.append(f"| {k} | {r['每條新增買進（平均）']:.1f} | {r['探索']:.1f}／{r['確認']:.1f} | {sgn(r['淨報酬平均（合併所有顆）'])} | {pct(r['勝率'], 0)} | {pct(r['末根出場占比'], 0)} | {sgn(r['對組合貢獻和（平均）'])} |")
    g = S["缺口"]; m = g["缺80"]; c1 = g["校準_有月營收的其他股（AND_null）"]; c2 = g["驗證_補72（AND_merged）"]
    L += ["", "## ③ 缺口：補不回的 80 家（⛔ 描述旗標、不當正式訊號）", "",
          f"- 缺 80 家（依下市年 {m['缺80_依下市年']}）；主窗內有價格訊號（S 列）的 {m['窗內有S列的家數']} 家、{m['窗內S列']} 筆（探索 {m['探索_S列']}、確認 {m['確認_S列']}）。",
          f"- 季旗標（fs_xbrl 單季營收 ≥ 前 8 季最大）可判 {m['季旗標可判']} 筆，**為真（可能入選）{m['季旗標真（可能入選）']} 筆**（探索 {m['探索_季旗標真']}、確認 {m['確認_季旗標真']}；閘開 {m['其中閘開（營飆可進）']}）。",
          f"- 校準（有月營收的其他股）：季旗標真 {c1['季旗標真']} 筆中實際 AND {c1['兩者皆真']}（precision {pct(c1['precision（季真中AND）'])}）；AND 中季旗標真 recall {pct(c1['recall（AND中季真）'])}。",
          f"  補 72 家驗證：precision {pct(c2['precision（季真中AND）'])}、recall {pct(c2['recall（AND中季真）'])}（S 列 {c2['S列']}）。",
          f"- ⇒ 估計受影響 AND 筆數量級 ≈ {m['估計受影響AND筆數（×precision）']:.0f} 筆（對照定版窗內 AND {g['窗內AND筆數_null']:,} 筆）。",
          f"- 季可用日：上傳時戳 {g['季可用日來源（季數）']['上傳時戳']:,} 季、法定期限替代 {g['季可用日來源（季數）']['法定期限']:,} 季。", "",
          "## 對帳", "", "```", json.dumps(S["閘"], ensure_ascii=False, indent=1), "```", "",
          f"⭐ {WORD}。結果句：「{SENT}」；{NOTE_SRC}。"]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
