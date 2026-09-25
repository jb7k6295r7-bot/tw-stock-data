# -*- coding: utf-8 -*-
"""裁定線 seq178 §二：PREREG10 #1（AND｜regime=True｜N10｜H120）的最新候選名單（⛔ 只列訊號與日期，不算、不報任何報酬）。

    python3 -m backtest.list_prereg10 build           # 延伸 AND 訊號 → 重疊回歸 → 名單
    python3 -m backtest.list_prereg10 check [代號]    # 查核：regime 歷史重算、引擎端對端（rerun17 main 格 1 逐位元）、手算一檔 AND 條件

⭐ 一律呼叫原程式的函式，⛔ 既有 .py 一行都沒改（同 rerun17_build 的四步）：
  ① 營收面板 ＝ research34.process_stock（liq_mode=shares、pub_day=10；窗頭 SIG_START 不變、窗尾由 R34.SIG_END 延到日曆最後一根）
  ② S（3/5 主格）＝ resultsN17/sig_edc6f/signals_S.csv.gz（rerun17_build ② 的原輸出，⛔ 不重算）
     ＋ 最後一根：research11.stock_features 在 k+1 ≥ n 不出列 ⇒ 在 repo 外暫存 data 目錄複製最後一列當次一預計交易日的佔位 K 棒再呼叫原函式
       （見 last_bar_signals；回歸 C 逐欄驗其餘列不變；佔位 K 棒的一切前瞻欄覆寫 NaN）
  ③ AND ＝ research13.and_flags(S, 延伸面板)（STALE_MAX=45）
  ④ relvol ＝ researchp1.attach_features（只為了讓重疊回歸逐欄比；#1 不用 relvol）
落地讀法（⛔ 看名單前寫定；L1、L5 依回測線 2026-09-25 補充指示）：
  L1 AND 的底是研究十一 3/5 訊號，【逐日】判（任何有成交日），同檔 20 根內只取第一個（dd＝20，原件）⇒ ⛔ 不是每月量測日。
     名單 ＝ 資料最後 20 個交易日內的 AND 訊號；另標「最後交易日當天」那批（＝次一交易日開盤可進）。
     營收那一半：research34.rebalance_dates 的 signal_pos（M+1 月 10 日之後第一個交易日的前一日）起可用；各列附決定 AND 的營收期別。
  L3 延伸新增的列（pos ≥ 第一個新營收量測日）⇒ 一切前瞻欄（g_*、xpos_*、t_LD、面板 ret/bench）落地前覆寫為 NaN，⛔ 不讀。
  L4 重疊回歸：舊面板列（signal_pos ≤ 原 SIG_END 窗尾）逐欄逐位元相同；AND 列 pos < 第一個新量測日者逐欄逐位元相同 ⇒ 不同就停。
  L5 regime：名單一律用【進場前一個交易日（t−1，通常＝訊號日）】的 0050 還原收盤 vs 200 根均線判閘。
     原件回測（research13 L163～177、rerun17.regime_mask）用的是 regime_ok[entry_pos]＝進場日當天收盤（進場成交在開盤 ⇒ 半天前視）
     ⇒ 另並列「照原件判」一欄；進場日在資料之後 ⇒ 寫「未知」。
  L6 第 120 根出場日 ＝ 日曆[D.exit_pos(entry_pos, 120)]（日曆位置；假設該股每個交易日都有成交，停牌只會更晚）；
     超出資料日曆 ⇒ gate_b_status.future_trading_days 外推（2027 休市表未公告 ⇒ 只扣週末 ⇒ 實際出場日只會更晚）。
  L7 名額：N＝10 槽；同一天（同 entry_pos）候選多於空槽 ⇒ 引擎 research11.simulate_mtm pick=None ⇒ rng.permutation 隨機抽
     （rerun17／research13 種子 1000＋r）；已持有的代號當天不再進（held）。⛔ 不改成排序。
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import io
import os
import subprocess
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import rerun17 as RR

RR.use_snapshot()

from . import data as D                 # noqa: E402
from . import patterns as PT            # noqa: E402
from . import research11 as R           # noqa: E402
from . import research13 as R13         # noqa: E402
from . import research34 as R34         # noqa: E402
from . import researchp1 as P1          # noqa: E402
from . import universe_gate as UG       # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsList")
SIG = os.path.join(RR.OUT, "sig_edc6f")
ASOF = "2026-09-24"
HOLD = 120
FWD_AND = ["g_H60", "g_H120", "g_LD", "xpos_H60", "xpos_H120", "xpos_LD", "t_LD", "g_H20", "xpos_H20"]
FWD_PANEL = ["ret20", "bench20", "ret60", "bench60"]


def _log_factory(name):
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, name), "a", encoding="utf-8")

    def log(x):
        print(x, flush=True); logf.write(x + "\n"); logf.flush()
    return log


def universe():
    stocks = pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(stocks)
    uni = D.load_universe().merge(U[["stock_id"]], on="stock_id")
    return stocks, uni


def _rt(df):
    """csv 來回一次（與 rerun17_build 存檔再讀的路徑同型）。"""
    b = io.StringIO(); df.to_csv(b, index=False); b.seek(0)
    return b


def build_panel(cal, uni, log):
    PT.PARAMS["liq_mode"] = "shares"
    bdf = D.load_benchmark(cal)
    bench = {"o": bdf["open"].to_numpy(float), "c": bdf["close"].to_numpy(float)}
    disp = D.load_disposal_intervals()
    rev, rev_ly, ind = R34.load_revenue()
    rdates = R34.rebalance_dates(list(rev.index), cal, 10)
    lo = int(cal.searchsorted(pd.Timestamp(R34.SIG_START)))
    hi_orig = int(cal.searchsorted(pd.Timestamp(R34.SIG_END), side="right") - 1)
    hi = len(cal) - 1                                        # ⭐ 唯一的改動：窗尾延到日曆最後一根
    jobs = list(zip(uni["stock_id"], uni["market"], uni["first_seen"], uni["last_seen"]))
    log(f"[①面板] 營收 {rev.shape[0]} 期（{rev.index.min()}～{rev.index.max()}）；窗 {cal[lo].date()}～{cal[hi].date()}（原窗尾 {cal[hi_orig].date()}）")
    rows = []
    t0 = time.time()
    with Pool(1, initializer=R34._init, initargs=(cal, bench, disp, rev, rev_ly, rdates, lo, hi)) as pool:
        for i, r in enumerate(pool.imap_unordered(R34.process_stock, jobs, chunksize=8)):
            if r:
                rows += r
            if (i + 1) % 500 == 0:
                log(f"  ① {i + 1}/{len(jobs)} {time.time() - t0:.0f}s")
    panel = pd.DataFrame(rows)
    for c in ("rev_hi12", "rev_hi24", "rev_hi36", "bull"):
        if c in panel:
            panel[c] = panel[c].astype("boolean")
    panel["signal_date"] = [cal[i].strftime("%Y-%m-%d") for i in panel["signal_pos"]]
    panel["entry_date"] = [cal[i].strftime("%Y-%m-%d") for i in panel["entry_pos"]]
    new = panel["signal_pos"] > hi_orig
    panel.loc[new, FWD_PANEL] = np.nan                       # L3
    return panel, rdates, hi_orig


def regime_arrays(cal):
    bench = RR.load_bench(cal)
    ma = pd.Series(bench).rolling(R13.MA_REGIME, min_periods=R13.MA_REGIME).mean().to_numpy()
    return bench, ma, RR.regime_mask(bench)


def cmd_build():
    log = _log_factory("build.log")
    t0 = time.time()
    assert D.DATA == RR.H2D, D.DATA
    cal = D.load_calendar()
    n = len(cal)
    head = subprocess.run(["git", "-C", os.path.dirname(HERE), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    log(f"===== list_prereg10 build {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜資料 main {RR.SHA}｜程式 HEAD {head[:10]}｜日曆 {n} 根 {cal[0].date()}～{cal[-1].date()}")
    stocks, uni = universe()
    log(f"[母體] gate3 ∩ load_universe ⇒ {len(uni):,} 檔")

    # ① 延伸面板 + 回歸 A
    panel, rdates, hi_orig = build_panel(cal, uni, log)
    ppath = os.path.join(OUT, "panel_rev_ext.csv.gz")
    panel.to_csv(ppath, index=False, compression="gzip")
    pnl = pd.read_csv(ppath, dtype={"stock_id": str})
    old_p = pd.read_csv(os.path.join(SIG, "panel_rev.csv.gz"), dtype={"stock_id": str})
    key = ["stock_id", "period"]
    a = old_p.sort_values(key).reset_index(drop=True)
    b = pnl[pnl["signal_pos"] <= hi_orig].sort_values(key).reset_index(drop=True)
    try:
        pd.testing.assert_frame_equal(a, b, check_exact=True)
        log(f"[回歸A 面板] 舊 {len(a):,} 列 vs 延伸版窗內 {len(b):,} 列 ⇒ 逐欄逐位元相同 ✅")
    except AssertionError as e:
        log(f"[回歸A 面板] ⛔ 不同 ⇒ 停：{str(e)[:800]}"); raise SystemExit(1)
    newp = pnl[pnl["signal_pos"] > hi_orig]
    log(f"[①延伸] 新增面板 {len(newp):,} 列：" + "；".join(
        f"{p} 量測日 {g['signal_date'].iloc[0]} {len(g):,} 列、rev_hi24=True {int((g['rev_hi24'] == True).sum())}" for p, g in newp.groupby("period")))

    # ② S（原輸出）＋ 最後一根（佔位 K 棒）＋ ③ AND
    pnl["rev_hi24"] = pnl["rev_hi24"].fillna(False).astype(bool)
    S_full = pd.read_csv(os.path.join(SIG, "signals_S.csv.gz"), dtype={"sid": str})
    log(f"[②S] 原輸出 {len(S_full):,} 筆；pos 最晚 {cal[S_full['pos'].max()].date()}（快照最後一根 {cal[-1].date()}：stock_features 要次一根才出訊號）")
    S_last, next_day = last_bar_signals(cal, uni, pnl, S_full, log)
    S_all = pd.concat([S_full, S_last], ignore_index=True)
    S = S_all[["sid", "k", "pos", "entry_pos", "month", "g_H60", "g_H120", "g_LD", "xpos_H60", "xpos_H120", "xpos_LD", "t_LD"]].copy()
    flags, _ = R13.and_flags(S, pnl)
    AND = S[flags].copy()
    # ④ relvol
    missing, mism = P1.attach_features(AND, S, cal, uni.set_index("stock_id")["market"], 1)
    if mism or missing:
        raise SystemExit(f"⛔ attach_features k↔pos 不符 {mism}／讀不到 {len(missing)} ⇒ 停")
    AND = pd.read_csv(_rt(AND), dtype={"sid": str})

    # 回歸 B
    first_new_sp = int(newp["signal_pos"].min())
    old_a = pd.read_csv(os.path.join(SIG, "and_signals.csv.gz"), dtype={"sid": str})
    ka = ["sid", "pos"]
    a = old_a[old_a["pos"] < first_new_sp].sort_values(ka).reset_index(drop=True)
    b = AND[AND["pos"] < first_new_sp].sort_values(ka).reset_index(drop=True)      # ⚠ 只來回一次 csv（兩次會在 relvol 末位漂 1 ulp）
    # 佔位列的前瞻欄是 NaN ⇒ 合併後 xpos_* 被升成 float；重疊段沒有 NaN ⇒ 轉回舊檔的 dtype（值不變，轉型本身會擋非整數）
    for c_, dt in a.dtypes.items():
        if c_ in b and b[c_].dtype != dt:
            if b[c_].isna().any() or not np.array_equal(b[c_].to_numpy(float), b[c_].to_numpy(float).round()):
                log(f"[回歸B AND] ⛔ {c_} 有 NaN 或非整數 ⇒ 停"); raise SystemExit(1)
            b[c_] = b[c_].astype(dt)
    try:
        pd.testing.assert_frame_equal(a, b, check_exact=True)
        log(f"[回歸B AND] pos < 第一個新量測日 {cal[first_new_sp].date()}：舊 {len(a):,} 列 vs 延伸 {len(b):,} 列 ⇒ 逐欄逐位元相同 ✅")
    except AssertionError as e:
        log(f"[回歸B AND] ⛔ 不同 ⇒ 停：{str(e)[:800]}"); raise SystemExit(1)
    oa = old_a[old_a["pos"] >= first_new_sp]; na = AND[AND["pos"] >= first_new_sp]
    so, sn = set(zip(oa["sid"], oa["pos"])), set(zip(na["sid"], na["pos"]))
    log(f"[新量測日以後] 舊檔 {len(so)} 筆（由較舊那期營收判）；延伸版 {len(sn)} 筆（改由最新可得那期判）：共有 {len(so & sn)}、只在舊 {sorted(so - sn)}、只在延伸 {len(sn - so)}")
    for c_ in FWD_AND:                                        # L3
        AND[c_] = AND[c_].astype(object)
        AND.loc[AND["pos"] >= first_new_sp, c_] = np.nan
    AND.to_csv(os.path.join(OUT, "and_signals_ext.csv.gz"), index=False)
    log(f"[③AND 延伸] {len(AND):,} 筆／{AND['sid'].nunique():,} 檔；pos 最晚 {cal[AND['pos'].max()].date()}")

    # ── 名單（⭐ 訊號是逐日的：3/5 任何有成交日都可能觸發 ⇒ 名單＝最近 20 個交易日內的 AND 訊號）──
    bench, ma, reg = regime_arrays(cal)
    from . import gate_b_status as GB
    fut, fut_basis = GB.future_trading_days(cal, 2 * HOLD + 10)
    cal_ext = cal.append(fut)
    assert cal_ext[n] == next_day, (cal_ext[n], next_day)
    per_of = {sp: p for p, (sp, ep) in rdates.items()}
    p_sorted = pnl.sort_values(["stock_id", "signal_pos"])
    by = {sid: (g["signal_pos"].to_numpy(), g["period"].to_numpy()) for sid, g in p_sorted.groupby("stock_id")}

    def gov(sid, pos):
        sp, per = by[sid]; j = int(np.searchsorted(sp, pos, side="right")) - 1
        return per[j], int(sp[j])

    meta = stocks.drop_duplicates("stock_id").set_index("stock_id")
    Sx = S_all.set_index(["sid", "pos"])

    def rows_of(d):
        rows = []
        for r in d.itertuples():
            per, gsp = gov(r.sid, r.pos)
            e = int(r.entry_pos)
            xp = D.exit_pos(e, HOLD)
            s = Sx.loc[(r.sid, r.pos)]
            basis = "資料日曆" if xp < n else fut_basis[xp - n]
            if "只扣週末" in basis:
                basis += " ⇒ 實際只會更晚"
            t1 = e - 1                                            # 進場前一個交易日（＝訊號日，若該股連續成交）
            rows.append({"stock_id": r.sid, "name": meta["name"].get(r.sid, ""), "market": meta["market"].get(r.sid, ""),
                         "signal_date": str(cal[int(r.pos)].date()),
                         "batch": "最後交易日當天" if int(r.pos) == n - 1 else "近20交易日",
                         "entry_date": str(cal_ext[e].date()), "entry_basis": "資料日曆" if e < n else fut_basis[e - n],
                         "exit_date_120": str(cal_ext[xp].date()), "exit_basis": basis,
                         "rev_period": per, "rev_measure_date": str(cal[gsp].date()),
                         "regime_list_t1": bool(reg[t1]), "regime_date_t1": str(cal[t1].date()),
                         "bench_t1": round(float(bench[t1]), 4), "ma200_t1": round(float(ma[t1]), 4),
                         "regime_orig_entryclose": ("T" if reg[e] else "F") if e < n else "未知",
                         "score": int(s["score"]), "c1_ret20": bool(s["c1"]), "c2_nup20": bool(s["c2"]), "c3_amt": bool(s["c3"]),
                         "c4_ma100": bool(s["c4"]), "c5_hi250": bool(s["c5"])})
        out = pd.DataFrame(rows)
        if len(out):
            out["status"] = np.where(out["regime_list_t1"], "候選", "不進場（0050 在 200 日線下，t−1 判）")
            out = out.sort_values(["signal_date", "stock_id"]).reset_index(drop=True)
        return out

    lo20 = n - 20
    L = rows_of(AND[AND["pos"] >= lo20])
    tag = str(cal[-1].date())
    L.to_csv(os.path.join(OUT, f"list_PREREG10_1_{tag}.csv"), index=False, encoding="utf-8-sig")
    log(f"[名單] 近 20 個交易日 {cal[lo20].date()}～{cal[-1].date()}：AND {len(L)} 筆／{L['stock_id'].nunique() if len(L) else 0} 檔；"
        f"其中最後交易日 {cal[-1].date()} 當天 {int((L['batch'] == '最後交易日當天').sum()) if len(L) else 0} 筆（假想進場 {next_day.date()}）")
    if len(L):
        ok = L[L["regime_list_t1"]]
        byday = ok.groupby("entry_date").size()
        log(f"   regime（t−1）開 {len(ok)}／關 {len(L) - len(ok)}；照原件（進場日收盤）T {int((L['regime_orig_entryclose'] == 'T').sum())}、F {int((L['regime_orig_entryclose'] == 'F').sum())}、未知 {int((L['regime_orig_entryclose'] == '未知').sum())}；"
            f"候選的進場日 {len(byday)} 天、單日最多 {int(byday.max()) if len(byday) else 0} 筆；決定 AND 的營收期別 {L['rev_period'].value_counts().to_dict()}")
    # 前兩個月（以訊號日所在月份分）：描述
    AND["sig_month"] = [cal[int(p)].strftime("%Y-%m") for p in AND["pos"]]
    P = rows_of(AND[AND["sig_month"].isin(["2026-07", "2026-08", "2026-09"])])
    P["sig_month"] = P["signal_date"].str[:7]
    P.to_csv(os.path.join(OUT, "months_PREREG10_1_2026-07_09.csv"), index=False, encoding="utf-8-sig")
    for m, d in P.groupby("sig_month"):
        ok = d[d["regime_list_t1"]]
        byday = ok.groupby("entry_date").size()
        log(f"[月 {m}] AND {len(d)} 筆／{d['stock_id'].nunique()} 檔；regime（t−1）開 {len(ok)}／關 {len(d) - len(ok)}；"
            f"照原件 T {int((d['regime_orig_entryclose'] == 'T').sum())}／F {int((d['regime_orig_entryclose'] == 'F').sum())}／未知 {int((d['regime_orig_entryclose'] == '未知').sum())}；"
            f"候選進場日 {len(byday)} 天、單日最多 {int(byday.max()) if len(byday) else 0}；營收期別 {d['rev_period'].value_counts().to_dict()}")
    mlist = sorted(sp for sp in per_of if sp >= n - 70)
    log("[營收量測日] " + "；".join(f"{per_of[sp]} 營收 ⇒ {cal[sp].date()}" for sp in mlist))
    log("[regime 近 25 日（0050 還原收盤 vs MA200）] " + "；".join(f"{cal[t].date()} {'開' if reg[t] else '關'}（{bench[t]:.2f} vs {ma[t]:.2f}）" for t in range(n - 25, n)))
    reg_m = pd.Series(reg[n - 70:n], index=cal[n - 70:n]).groupby(lambda d: d.strftime("%Y-%m")).agg(["sum", "count"])
    log(f"[regime 各月開的天數] {reg_m.to_dict('index')}")
    if len(L):
        with pd.option_context("display.width", 300, "display.max_columns", 30, "display.max_rows", 300):
            log(L[["stock_id", "name", "market", "signal_date", "batch", "entry_date", "exit_date_120", "exit_basis", "rev_period",
                   "regime_list_t1", "regime_orig_entryclose", "score", "status"]].to_string())
    log(f"[完成] {time.time() - t0:.0f}s")


TMP = os.path.expanduser(f"~/lst_tmpdata/{RR.SHA}/data")


def last_bar_signals(cal, uni, pnl, S_full, log):
    """最後一根的 3/5 訊號：stock_features 在 k+1 ≥ n 時不出列（要次一根的開盤當進場價）⇒ 在 repo 外的暫存 data 目錄
    給每一檔候選股【複製最後一列】當作下一個預計交易日的佔位 K 棒，再呼叫原函式。
    ⭐ 最後一根（含）以前的特徵全是回看量（rolling／roll 的迴繞位置本來就被遮掉；ATR 與 amt 的 np.roll 迴繞值＝最後一列本身，
       複製後數值不變）⇒ 佔位 K 棒只讓 k+1 < n 成立，不改變任何特徵；回歸 C 逐欄驗其餘各列。
    ⛔ 佔位 K 棒算出來的一切前瞻欄一律覆寫 NaN。"""
    from . import gate_b_status as GB
    n = len(cal)
    next_day = GB.future_trading_days(cal, 1)[0][0]
    # 只算可能 AND 的股票：最後一根時點的最新面板列（≤ 45 日）rev_hi24＝True
    last = pnl[pnl["signal_pos"] <= n - 1].sort_values("signal_pos").groupby("stock_id").tail(1)
    want = set(last[(last["rev_hi24"]) & (n - 1 - last["signal_pos"] <= R13.STALE_MAX)]["stock_id"])
    sub = uni[uni["stock_id"].isin(want)]
    src = RR.H2D
    if os.path.isdir(os.path.dirname(TMP)):
        import shutil
        shutil.rmtree(os.path.dirname(TMP))
    os.makedirs(os.path.join(TMP, "meta")); os.makedirs(os.path.join(TMP, "stocks"))
    for d in os.listdir(src):
        if d not in ("meta", "stocks"):
            os.symlink(os.path.join(src, d), os.path.join(TMP, d))
    for f in os.listdir(os.path.join(src, "meta")):
        if f != "calendar_twse.csv":
            os.symlink(os.path.join(src, "meta", f), os.path.join(TMP, "meta", f))
    with open(os.path.join(src, "meta", "calendar_twse.csv"), encoding="utf-8") as fh:
        txt = fh.read()
    with open(os.path.join(TMP, "meta", "calendar_twse.csv"), "w", encoding="utf-8") as fh:
        fh.write(txt.rstrip("\n") + f"\n{next_day.date()},LST_PLACEHOLDER\n")
    for f in os.listdir(os.path.join(src, "stocks")):
        sid = f[:-4]
        if sid in want:
            with open(os.path.join(src, "stocks", f), encoding="utf-8") as fh:
                lines = fh.read().rstrip("\n").split("\n")
            lastl = lines[-1]
            lines.append(f"{next_day.date()}" + lastl[lastl.index(","):])
            with open(os.path.join(TMP, "stocks", f), "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines) + "\n")
        else:
            os.symlink(os.path.join(src, "stocks", f), os.path.join(TMP, "stocks", f))
    D.DATA = TMP
    try:
        cal2 = D.load_calendar()
        assert len(cal2) == n + 1 and (cal2[:n] == cal).all() and cal2[n] == next_day
        R._init(cal2)
        rows = []
        for r in sub.itertuples():
            o = R.stock_features((r.stock_id, r.market, r.first_seen))
            if o is not None:
                rows.extend(o["main"])
    finally:
        D.DATA = RR.H2D
    Sn = pd.read_csv(_rt(pd.DataFrame(rows)), dtype={"sid": str})
    fwd = [c for c in Sn.columns if c.startswith(("g_", "x_", "xpos_", "bars_", "t_"))]
    base = [c for c in Sn.columns if c not in fwd]
    old = S_full[S_full["sid"].isin(want)]
    a = old[base].sort_values(["sid", "pos"]).reset_index(drop=True)
    b = Sn[Sn["entry_pos"] < n][base].sort_values(["sid", "pos"]).reset_index(drop=True)
    try:
        pd.testing.assert_frame_equal(a, b, check_exact=True)
        log(f"[回歸C 佔位K棒] {len(want)} 檔：既有 S 列 {len(a):,} vs 佔位版 {len(b):,} 列（非前瞻欄 {len(base)} 欄）⇒ 逐位元相同 ✅")
    except AssertionError as e:
        log(f"[回歸C 佔位K棒] ⛔ 不同 ⇒ 停：{str(e)[:800]}"); raise SystemExit(1)
    new = Sn[Sn["entry_pos"] >= n].copy()
    for c_ in fwd:
        new[c_] = new[c_].astype(object)
        new[c_] = np.nan
    log(f"[②S 最後一根] 佔位 K 棒 {next_day.date()}（休市表外推的次一交易日）⇒ 新增 {len(new)} 筆 3/5 訊號（訊號日 {sorted(set(cal[p].date().isoformat() for p in new['pos']))}）")
    return new[S_full.columns.intersection(new.columns)].reindex(columns=S_full.columns), next_day


def cmd_check(sid_arg=None):
    log = _log_factory("check.log")
    log(f"===== list_prereg10 check {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）")
    cal = D.load_calendar(); n = len(cal)
    bench, ma, reg = regime_arrays(cal)
    # ── 查核 1：regime 歷史某日，research13 原式（rolling）vs 獨立 numpy ──
    for d in ("2020-03-19", "2022-06-17", "2024-08-05", "2025-04-09"):
        t = int(cal.searchsorted(pd.Timestamp(d)))
        ind = float(np.mean(bench[t - 199:t + 1]))
        log(f"[regime 歷史] {cal[t].date()}：0050 還原收盤 {bench[t]:.4f}；MA200 原式 {ma[t]:.6f} vs 獨立 {ind:.6f}（差 {abs(ma[t] - ind):.2e}）；"
            f"原式 {bool(reg[t])} vs 獨立 {bool(bench[t] > ind)}")
    # ── 查核 2：端對端 —— 本檔的 regime ＋ sig_edc6f 的 AND ⇒ 重跑 rerun17 main 格 1，eq_sha／trades 對 seeds_main.csv ──
    AND = pd.read_csv(os.path.join(SIG, "and_signals.csv.gz"), dtype={"sid": str})
    uni_mk = D.load_universe().set_index("stock_id")["market"]
    closes, opens = RR.load_prices(set(AND["sid"]), cal, uni_mk, "branch")
    w0, w1 = RR.win_bounds(cal)
    sig = AND[reg[AND["entry_pos"].to_numpy()]]
    e = sig["entry_pos"].to_numpy(); sig = sig[(e >= w0) & (e <= w1)]
    ref = pd.read_csv(os.path.join(RR.OUT, "seeds_main.csv"))
    for r in (0, 1):
        s = R.simulate_mtm(sig, "H120", 10, np.random.default_rng(1000 + r), closes, opens, n, return_equity=True)
        sha = hashlib.sha256(np.asarray(s["equity"], float).tobytes()).hexdigest()[:16]
        rr = ref[(ref["cell"] == 1) & (ref["r"] == r)].iloc[0]
        same = sha == rr["eq_sha"] and int(s["trades"]) == int(rr["trades"])
        log(f"[端對端] 格1 seed {1000 + r}：eq_sha {sha} vs seeds_main {rr['eq_sha']}｜trades {s['trades']} vs {rr['trades']} ⇒ {'相同 ✅' if same else '⛔ 不同'}")
    # ── 查核 3：手算名單上一檔的 AND 條件 ──
    L = sorted(f for f in os.listdir(OUT) if f.startswith("list_PREREG10_1_"))[-1]
    lst = pd.read_csv(os.path.join(OUT, L), dtype={"stock_id": str})
    sid = sid_arg or lst["stock_id"].iloc[0]
    row = lst[lst["stock_id"] == sid].iloc[0]
    st = D.load_stock(sid, row["market"], cal)
    df = st.df; idx = np.flatnonzero(df["traded"].to_numpy())
    c = df["close"].to_numpy()[idx]; amt = df["amount"].to_numpy()[idx]
    raw = pd.read_csv(os.path.join(D.DATA, "stocks", f"{sid}.csv"), dtype={"date": str})
    raw["date"] = pd.to_datetime(raw["date"]); raw = raw.drop_duplicates("date").set_index("date")
    rc = pd.to_numeric(raw["close"].reindex(cal[idx]), errors="coerce").to_numpy(float)
    pos = int(cal.searchsorted(pd.Timestamp(row["signal_date"]))); k = int(np.searchsorted(idx, pos))
    ret20 = c[k] / c[k - 20] - 1
    amt_r = amt[k] / np.mean(amt[k - 20:k])
    ma100 = np.mean(c[k - 99:k + 1]); hi250 = np.max(c[k - 249:k + 1])
    chg = rc[k - 19:k + 1] / rc[k - 20:k] - 1
    nup_approx = int((chg >= 0.095).sum())
    log(f"[手算 {sid} {row['name']}] 3/5 訊號日 {cal[pos].date()}（第 {k} 根有效 K 棒；原始 score {row['score']}，c1..c5 {[row[x] for x in ('c1_ret20','c2_nup20','c3_amt','c4_ma100','c5_hi250')]}）")
    log(f"   c1 20 根報酬 {ret20:+.4f}（≥0.30？{ret20 >= 0.30}）｜c3 成交額 ÷ 前 20 根均額 {amt_r:.3f}（≥3？{amt_r >= 3}）｜"
        f"c4 收 {c[k]:.3f} vs MA100 {ma100:.3f}（>？{c[k] > ma100}）｜c5 收 vs 250 根最高 {hi250:.3f}（≥？{c[k] >= hi250}）｜"
        f"c2 近 20 根未還原收盤漲 ≥9.5% 的根數 {nup_approx}（≥3？{nup_approx >= 3}；近似，原式用 tick 精算漲停價）")
    hand = int(ret20 >= 0.30) + int(amt_r >= 3) + int(c[k] > ma100) + int(c[k] >= hi250) + int(nup_approx >= 3)
    log(f"   手算分數 {hand}（需 ≥ 3）vs 原始 score {row['score']}")
    fs = sorted(glob.glob(os.path.join(D.DATA, "mops", "revenue_hist", "*.csv")))
    rv = pd.concat([pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收"]) for f in fs])
    rv = rv[rv["stock_id"] == sid].drop_duplicates(["stock_id", "period"], keep="last")
    rv["v"] = pd.to_numeric(rv["當月營收"], errors="coerce"); rv = rv.set_index("period")["v"].sort_index()
    p = row["rev_period"]; i = list(rv.index).index(p)
    hist = rv.iloc[i - 24:i]
    ok24 = bool(len(hist) == 24 and hist.notna().all() and rv.iloc[i] >= hist.max())
    log(f"   營收 {p} ＝ {rv.iloc[i]:,.0f}；前 24 期（{hist.index[0]}～{hist.index[-1]}，{int(hist.notna().sum())} 期有值）最高 {hist.max():,.0f}（{hist.idxmax()}）⇒ 創 24 月新高 {ok24}")
    ms = int(cal.searchsorted(pd.Timestamp(row["rev_measure_date"])))
    log(f"   營收量測日 {row['rev_measure_date']} → 訊號日相距 {pos - ms} 個交易日（≤ {R13.STALE_MAX}？{pos - ms <= R13.STALE_MAX}）")
    t1 = int(cal.searchsorted(pd.Timestamp(row["regime_date_t1"])))
    ind = float(np.mean(bench[t1 - 199:t1 + 1]))
    log(f"   regime（名單用 t−1＝{cal[t1].date()}）：0050 還原收盤 {bench[t1]:.4f} vs 獨立 MA200 {ind:.4f} ⇒ {bench[t1] > ind}（名單 {row['regime_list_t1']}）")
    log(f"   假想進場 {row['entry_date']}（{row['entry_basis']}）；第 120 根出場 {row['exit_date_120']}（{row['exit_basis']}）")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("stage", choices=["build", "check"]); ap.add_argument("sid", nargs="?")
    a = ap.parse_args()
    if a.stage == "build":
        cmd_build()
    else:
        cmd_check(a.sid)
