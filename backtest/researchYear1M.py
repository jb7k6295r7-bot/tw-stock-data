# -*- coding: utf-8 -*-
"""使用者問「100 萬放一年，單純買 0050 對上幾檔選股策略，最後會是多少？」（台股策略線 seq237＋seq239；回測線計算助手 2026-09-26）。

⭐ 描述、⛔ 不判、⛔ 不計 N；程式與參數一字不動，只換起訖。⛔ 本檔不改任何既有 .py，策略邏輯一律呼叫原程式：
   引擎 research11.simulate_mtm｜AND 訊號 resultsN17/sig_edc6f/and_signals.csv.gz（rerun17_build）｜
   大盤閘 rerun17.regime_mask（regime 格一律 t−1：reg_t1[t] ＝ reg[t−1]，＝ rerun17_regime_t1）｜
   門檻B 訊號 researchp7.build_sig_gate_b｜P14 researchp14.blend｜P17 researchp17.{rebal_days, sigma_at, w_paths, compose}｜
   P9 六格 researchP9run.engine_kw（commit 8694b4f173 起未改）＋ p9_flags.build_flags｜0050 rerun17.load_bench

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYear1M panel   # 補 2026-09-01 量測日面板列
    ... -m backtest.researchYear1M gate  [--procs 3]    # G1：新包裝跑主窗、逐位元對 rerun17／regime_t1／P9run 的逐種子檔
    ... -m backtest.researchYear1M run   [--procs 3]    # A 固定窗 ＋ B 滾動窗（G1 沒過就拒跑）
    ... -m backtest.researchYear1M table                # 彙總 ⇒ fixed_windows.csv／rolling_windows.csv／rolling_terciles.csv／summary.json

═══ 臂與種子（照各原件）═══
  ① 0050 買進持有：rerun17.load_bench（還原收盤＝含息再投入，ffill）；報酬 ＝ bench[w1] ÷ bench[w0] − 1（＝ 0050 錨 bench_row 同式、不扣成本）
     另列描述欄「扣 ETF 來回 0.385%」＝ (1＋報酬)×(1−0.00385)−1（avgdown.COST_ETF：手續費 0.1425%×2＋ETF 證交稅 0.1%）
  ② #1 PREREG10 AND regime=True N10 H120（t−1 閘）｜種子 1000＋r
  ③ 門檻B（W1）＝ rerun17 格 0（P12 策略側、H120、N8、cash zero、無 tradable）｜種子 102000＋r
  ④ #2～#17 照 rerun17.CELLS（#4 #7 #16 #17 用 t−1 閘）｜P10 1000＋r、P1／P3乙 7000＋r、P14／P17 與 ③ 同一條路徑 102000＋r
     #18～#23 ＝ P9 A2／Ba／Bb／Bc／Cc／Ce（researchP9run.engine_kw、N8、H120、report_maxw）｜種子 99000＋r
  r ∈ [0, 200)

═══ 窗讀法（⭐ 看結果前寫定）═══
  W1 訊號只留 entry_pos ∈ [w0, w1]（＝ rerun17 主窗讀法）⇒ 窗起點全現金、w0 開盤起才可能進場；特徵照全歷史算（只讀過去）
  W2 窗內報酬 ＝ eq[w1] ÷ eq[w0] − 1、窗內最大回落 ＝ eq[w0..w1] 對其累積高點的最深跌幅（＝ research13.window_stats 的算式，
     但 ⛔ 不用它本身：它在不足 245 日時回 NaN）；⭐ 起點取 eq[w0]（w0 收盤）＝ rerun17 主窗與 0050 錨的同一口徑
  W3 窗末仍持有 ⇒ 引擎本來就逐日收盤市值，eq[w1] 就是「照 w1 收盤計值、不扣賣出成本」（引擎的成本在出場那天一次扣）
  W4 P14／P17：E ＝ eq[w0..w1]、B ＝ bench[w0..w1]，再平衡日與 σ 都照原件的【窗內相對】位置（⇒ 窗首 120 日 burn-in w＝0.5）
  W5 期末金額 ＝ 1,000,000 ×（1＋窗內報酬）；有種子的報 200 顆中位與 p10／p25／p75／p90（numpy.percentile linear）
  W6 「贏 0050 的種子比例」＝ 該窗 200 顆裡期末金額 ＞ ① 期末金額的比例（嚴格大於）

═══ 資料尾（⭐ 主版的讀法；引擎原樣另列）═══
  T1 引擎把「出場日超出資料尾」的訊號整筆丟掉（H 規則的 xpos＝−1；門檻B 的 x ≥ ncal 被剔）⇒ 最近一年窗後段會變成空手，
     這不是規則、是資料尾截斷 ⇒ 主版把這些訊號留下：出場日設在資料尾之後的一個墊檔日（日曆位置 ncal），
     價格陣列在尾端墊一根（收盤＝最後收盤、開盤 NaN）、ncal 傳 ncal＋1 ⇒ 部位在窗內照收盤計值、⛔ 不賣、⛔ 不扣成本
     判「資料尾截斷」的條件（⛔ 下市、壞根造成的不算）：AND ＝ 該股 bar k＋H ≥ 該股 K 棒數、該股最後一根 ＝ 日曆最後一天、
     k−20 之後沒有壞根；LD ＝ t_LD 為假、出場根 ＝ 該股最後一根 ＝ 日曆最後一天、k＋CAP ＞ 最後一根；
     門檻B ＝ build_sig_gate_b 在延伸日曆上建出、x ≥ ncal 的列（進場日開盤要有限且 ＞ 0，同原件）
  T2 門檻B／P9 的訊號面板：resultsAFC/panel.csv.gz 只到量測日 2026-03-02 ⇒ 主版改用 resultsp9_engine/panel_ext.csv.gz
     （＝ AFC 全部列 ＋ 2026-04～08 五個量測日，同一支 build_panel、sha d75bf50b…）＋ 本檔 panel 階段用同一支 build_panel
     補 2026-09-01 量測日（重疊的 2026-08-03 列逐位元對 panel_ext 為 fixture）；P9 Bb 旗標同樣用補過的面板
  T3 AND 訊號的營收面板 SIG_END＝2026-07-31（research34 原常數）⇒ 2026-09-15 以後沒有 AND 訊號；⛔ 不改常數，照報
  T4 受 T1／T2 影響的窗（w1 ≥ 該格最早受影響的日曆位置）另跑「引擎原樣」版（AND 不補、門檻B 用 AFC 面板），兩版並列
  墊檔對原路徑逐位元無影響（引擎只在 t ≤ min(ncal′, last＋2) 迴圈；不補訊號時 last ≤ ncal−1）⇒ 由 G1 驗
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import rerun17 as RR

RR.use_snapshot()

from . import data as D                                    # noqa: E402
from . import research11 as R                              # noqa: E402
from . import research13 as R13                            # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsYear1M")
REPS = 200
CAPITAL = 1_000_000
COST_ETF = 0.00385                                          # avgdown.COST_ETF（描述欄用）
AND_PATH = os.path.join(RR.OUT, "sig_edc6f", "and_signals.csv.gz")
PANEL_AFC = os.path.join(HERE, "resultsAFC", "panel.csv.gz")
PANEL_EXT = os.path.join(HERE, "resultsp9_engine", "panel_ext.csv.gz")
PANEL_EXT_SHA = "d75bf50baae15ed0445219a6f8003f166d65a6ce93b930d729a789fc364e0788"
PANEL_0901 = os.path.join(OUT, "panel_md20260901.csv.gz")
MD_NEW, MD_OVERLAP = "2026-09-01", "2026-08-03"
P10_SEED0, P1_SEED0, P12_SEED0, P9_SEED0 = 1000, 7000, 102000, 99000
REG_T1 = {1, 4, 7, 16, 17}
P9_CELLS = {18: "A2", 19: "Ba", 20: "Bb", 21: "Bc", 22: "Cc", 23: "Ce"}
P9_NAME = {18: "P9 2-A k2", 19: "P9 2-B ⓐ（+15% 加碼）", 20: "P9 2-B ⓑ（三分位加碼）", 21: "P9 2-B ⓒ（滿 40 根仍為正加碼）",
           22: "P9 2-C ⓒ（0050 MA60 下新部位 1.5 slot）", 23: "P9 2-C ⓔ（0050 MA10 下新部位 0.5 slot）"}

FIXED = [  # (鍵, 標籤, 起, 迄, 型) 型：exact＝兩端必須是交易日；year＝曆年第一個～最後一個交易日
    ("F2017", "2017-03-02～2018-03-01", "2017-03-02", "2018-03-01", "exact"),
    *[(f"Y{y}", f"{y} 曆年", f"{y}-01-01", f"{y}-12-31", "year") for y in range(2018, 2026)],
    ("L1Y", "最近一年 2025-09-24～2026-09-24", "2025-09-24", "2026-09-24", "exact"),
    ("YTD26", "2026-01-02～2026-09-24（⚠ 不滿一年）", "2026-01-02", "2026-09-24", "exact"),
]
ROLL_FROM = "2017-03"

_G: dict = {}


# ═════════════ 小工具 ═════════════
def sha16(a) -> str:
    return hashlib.sha256(np.asarray(a, float).tobytes()).hexdigest()[:16]


def sha64(a) -> str:
    return hashlib.sha256(np.asarray(a, float).tobytes()).hexdigest()


def seg_stats(v):
    """W2：v ＝ 窗內序列（v[0] ＝ 起點）⇒ (報酬, 最大回落)。回落 ＝ research13.window_stats 同式。"""
    v = np.asarray(v, float)
    peak = np.maximum.accumulate(v)
    return float(v[-1] / v[0] - 1.0), float(((v - peak) / peak).min())


def fixed_windows(cal):
    out = []
    for key, lab, a, b, kind in FIXED:
        if kind == "exact":
            w0 = int(cal.searchsorted(pd.Timestamp(a))); w1 = int(cal.searchsorted(pd.Timestamp(b)))
            if str(cal[w0].date()) != a or w1 >= len(cal) or str(cal[w1].date()) != b:
                raise SystemExit(f"⛔ 窗 {lab} 的端點不是交易日")
        else:
            w0 = int(cal.searchsorted(pd.Timestamp(a))); w1 = int(cal.searchsorted(pd.Timestamp(b), side="right")) - 1
        out.append({"key": key, "label": lab, "w0": w0, "w1": w1, "d0": str(cal[w0].date()), "d1": str(cal[w1].date()),
                    "days": w1 - w0 + 1, "full_year": key != "YTD26"})
    return out


def rolling_windows(cal):
    """每月第一個交易日起跑；終點 ＝ 起點＋1 年（同月同日）之前的最後一個交易日；起點＋1 年 ≤ 資料尾＋1 日才收。"""
    per = cal.to_period("M")
    firsts = np.flatnonzero(np.r_[True, per[1:] != per[:-1]])
    limit = cal[-1] + pd.Timedelta(days=1)
    out = []
    for s in firsts:
        if cal[s] < pd.Timestamp(ROLL_FROM + "-01"):
            continue
        e_date = cal[s] + pd.DateOffset(years=1)
        if e_date > limit:
            break
        w1 = int(cal.searchsorted(e_date, side="left")) - 1
        out.append({"key": f"R{cal[s]:%Y%m}", "label": f"{cal[s]:%Y-%m} 起", "w0": int(s), "w1": w1,
                    "d0": str(cal[s].date()), "d1": str(cal[w1].date()), "days": w1 - int(s) + 1, "full_year": True})
    return out


# ═════════════ 設定 ═════════════
def pad_px(closes, opens):
    cp = {s: np.r_[c, np.float32(c[-1])].astype(c.dtype) for s, c in closes.items()}
    op = {s: np.r_[o, np.float32(np.nan)].astype(o.dtype) for s, o in opens.items()}
    return cp, op


def and_censor(AND, cal, uni, log):
    """T1：AND 訊號裡「資料尾截斷」的列 ⇒ 回 (補過的 AND, 計數)。"""
    ncal = len(cal)
    A = AND.copy()
    cnt = {}
    cand_h = {H: A.index[A[f"xpos_H{H}"] < 0] for H in (60, 120)}
    cand_ld = A.index[(~A["t_LD"].astype(bool)) & (A["xpos_LD"] >= 0)]
    sids = sorted(set(A.loc[cand_h[60].union(cand_h[120]).union(cand_ld), "sid"]))
    bars = {}
    for s in sids:
        B = R.load_bars(s, uni.get(s, "twse"), cal)
        bars[s] = (B["idx"], B["next_bad"], B["o"], B["c"]) if B is not None else None
    for H in (60, 120):
        ok = []; why = {"delist_or_halt_end": 0, "badbar": 0, "not_end": 0, "nobars": 0, "pos_mismatch": 0}
        for i in cand_h[H]:
            row = A.loc[i]; b = bars.get(row["sid"])
            if b is None:
                why["nobars"] += 1; continue
            idx, nb, o, c = b; k = int(row["k"]); n = len(idx)
            if int(idx[k]) != int(row["pos"]):
                why["pos_mismatch"] += 1; continue
            nbk = nb[max(0, k - 20)]
            if D.exit_pos(k + 1, H) < n:
                why["not_end"] += 1; continue
            if nbk <= n - 1:
                why["badbar"] += 1; continue
            if int(idx[n - 1]) != ncal - 1:
                why["delist_or_halt_end"] += 1; continue
            ok.append((i, float(c[n - 1] / o[k + 1] - 1.0)))
        for i, g in ok:
            A.at[i, f"xpos_H{H}"] = ncal; A.at[i, f"g_H{H}"] = g
        cnt[f"H{H}"] = {"xpos<0": len(cand_h[H]), "補": len(ok), **why,
                        "補的進場日": [str(cal[int(A.at[i, 'entry_pos'])].date()) for i, _ in ok[:1]] +
                                     ([str(cal[int(A.at[ok[-1][0], 'entry_pos'])].date())] if ok else [])}
    ok = []; why = {"triggered_or_cap": 0, "not_last": 0, "not_cal_end": 0}
    for i in cand_ld:
        row = A.loc[i]; b = bars.get(row["sid"])
        if b is None:
            continue
        idx, nb, o, c = b; k = int(row["k"]); n = len(idx)
        if int(row["xpos_LD"]) != int(idx[n - 1]):
            why["not_last"] += 1; continue
        if k + R.CAP <= n - 1:
            why["triggered_or_cap"] += 1; continue
        if int(idx[n - 1]) != ncal - 1:
            why["not_cal_end"] += 1; continue
        ok.append(i)
    for i in ok:
        A.at[i, "xpos_LD"] = ncal
    cnt["LD"] = {"t_LD 假": len(cand_ld), "補": len(ok), **why}
    log(f"[T1 AND 資料尾] {json.dumps(cnt, ensure_ascii=False)}")
    return A, cnt


def sig12(panel, cal, closes, opens, log, tag):
    """T1：門檻B 訊號在延伸日曆上建（build_sig_gate_b 原函式），x ≥ ncal 的列改成墊檔日出場。"""
    from . import researchp7 as P7
    ncal = len(cal); EXT = 300
    cal_x = cal.append(pd.bdate_range(cal[-1] + pd.Timedelta(days=1), periods=EXT))
    cx = {s: np.r_[c, np.full(EXT, c[-1], dtype=c.dtype)] for s, c in closes.items()}
    ox = {s: np.r_[o, np.full(EXT, np.nan, dtype=o.dtype)] for s, o in opens.items()}
    sx = P7.build_sig_gate_b(panel, cal_x, cx, ox, start="2017-01-01", signal="B")
    s0 = P7.build_sig_gate_b(panel, cal, closes, opens, start="2017-01-01", signal="B")
    keep = sx[sx["xpos_H120"] < ncal].reset_index(drop=True)
    same = keep.equals(s0.reset_index(drop=True))
    if not same:
        raise SystemExit(f"⛔ {tag}：延伸日曆建出的非截斷列 ≠ 原日曆建出的訊號")
    cen = sx[(sx["xpos_H120"] >= ncal) & (sx["entry_pos"] < ncal)].copy()
    cen["g_H120"] = [float(closes[s][ncal - 1]) / float(opens[s][e]) - 1.0 for s, e in zip(cen["sid"], cen["entry_pos"])]
    cen["xpos_H120"] = ncal
    out = pd.concat([s0, cen], ignore_index=True).sort_values(["entry_pos", "sid"], kind="stable").reset_index(drop=True)
    info = {"原函式列數": len(s0), "截斷補回": len(cen), "合計": len(out),
            "補回進場日": [str(cal[int(cen['entry_pos'].min())].date()), str(cal[int(cen['entry_pos'].max())].date())] if len(cen) else None,
            "量測月": [s0["month"].min(), out["month"].max()]}
    log(f"[T1 門檻B {tag}] {json.dumps(info, ensure_ascii=False)}")
    return s0, out, info


def setup(log, need_windows=True):
    from . import p4_features as P4F
    from . import p9_flags as F
    from . import researchP9run as P9R
    cal = D.load_calendar(); ncal = len(cal)
    uni = D.load_universe().set_index("stock_id")["market"]
    AND = pd.read_csv(AND_PATH, dtype={"sid": str})
    afc = P4F.read_panel(PANEL_AFC)
    h = hashlib.sha256(open(PANEL_EXT, "rb").read()).hexdigest()
    if h != PANEL_EXT_SHA:
        raise SystemExit(f"⛔ panel_ext sha256 {h} ≠ {PANEL_EXT_SHA}")
    ext = P4F.read_panel(PANEL_EXT)
    if not os.path.exists(PANEL_0901):
        raise SystemExit("⛔ 先跑 panel 階段")
    add = P4F.read_panel(PANEL_0901)
    plus = pd.concat([ext, add[list(ext.columns)]], ignore_index=True).sort_values(["measure_date", "stock_id"], kind="stable").reset_index(drop=True)
    sids = set(AND["sid"]) | set(plus["stock_id"])
    closes, opens = RR.load_prices(sids, cal, uni, "branch")
    miss = sorted(set(AND["sid"]) - set(closes))
    if miss:
        raise SystemExit(f"⛔ AND 有 {len(miss)} 檔讀不到價格")
    bench = RR.load_bench(cal)
    # 門檻B 訊號：引擎原樣（AFC）／主版（panel_ext＋09-01、補截斷）
    s12_eng, _, _ = sig12(afc, cal, closes, opens, log, "AFC")
    s12_plain_plus, s12_mtm, info12 = sig12(plus, cal, closes, opens, log, "ext＋0901")
    AND_mtm, cntA = and_censor(AND, cal, uni, log)
    closesP, opensP = pad_px(closes, opens)
    benchP = np.r_[bench, bench[-1]]
    reg = RR.regime_mask(benchP)
    reg_t1 = np.zeros_like(reg); reg_t1[1:] = reg[:-1]
    # P9：旗標（原＝panel_ext；主版＝panel_ext＋09-01），墊一格
    fl_sids = set(s12_mtm["sid"]) | set(s12_eng["sid"])
    fo = F.build_flags(ext, cal, sids=fl_sids)
    fp = F.build_flags(plus, cal, sids=fl_sids)
    p0901 = int(cal.searchsorted(pd.Timestamp(MD_NEW)))
    fl_same = all(np.array_equal(fo[s][:p0901], fp[s][:p0901]) for s in fl_sids)
    if not fl_same:
        raise SystemExit("⛔ 補 09-01 後，09-01 之前的 Bb 旗標變了")
    flags_orig = {s: np.r_[v, False] for s, v in fo.items()}
    flags_plus = {s: np.r_[v, False] for s, v in fp.items()}
    below = {n: R.regime_below(benchP, n) for n in (60, 20, 10)}
    P9R._G.update(below=below, flags=flags_plus)
    # 受影響的最早日曆位置（T4）
    ch_and = {}
    for H, col in ((60, "xpos_H60"), (120, "xpos_H120")):
        d = AND_mtm.index[(AND_mtm[col] == ncal) & (AND[col] < 0)]
        ch_and[f"H{H}"] = int(AND_mtm.loc[d, "entry_pos"].min()) if len(d) else ncal
    ch_and["LD"] = ncal - 1 if (AND_mtm["xpos_LD"] == ncal).any() else ncal
    new12 = s12_mtm.merge(s12_eng, how="left", indicator=True, on=list(s12_eng.columns))
    ch12 = int(new12.loc[new12["_merge"] == "left_only", "entry_pos"].min()) if (new12["_merge"] == "left_only").any() else ncal
    _G.update(cal=cal, ncal=ncal, NP=ncal + 1, uni=uni, AND_eng=AND, AND_mtm=AND_mtm, s12_eng=s12_eng, s12_mtm=s12_mtm,
              closes=closesP, opens=opensP, bench=bench, benchP=benchP, reg_t1=reg_t1, reg=reg,
              flags_orig=flags_orig, flags_plus=flags_plus, ch_and=ch_and, ch12=ch12)
    info = {"日曆": f"{ncal} 根 {cal[0].date()}～{cal[-1].date()}", "AND": len(AND), "AND_補": cntA,
            "門檻B_AFC": len(s12_eng), "門檻B_主版": info12, "門檻B_ext＋0901_原函式": len(s12_plain_plus),
            "Bb旗標_09-01前相同": fl_same, "panel_ext_sha": h,
            "最早受影響": {"AND_H60": str(cal[min(ch_and['H60'], ncal - 1)].date()) if ch_and['H60'] < ncal else None,
                        "AND_H120": str(cal[ch_and['H120']].date()) if ch_and['H120'] < ncal else None,
                        "AND_LD": str(cal[ch_and['LD']].date()) if ch_and['LD'] < ncal else None,
                        "門檻B": str(cal[ch12].date()) if ch12 < ncal else None}}
    log(f"[設定] {json.dumps(info, ensure_ascii=False, default=str)}")
    return info


# ═════════════ 格 ═════════════
def cell_list():
    """(編號, 臂, 族, 名稱, 參數)。編號 0 ＝ 門檻B（W1），5／8 由同一條 P12 路徑算。"""
    out = []
    for cid, tier, fam, cell, sp in RR.CELLS:
        sp = dict(sp)
        name = f"#{cid} {fam}｜{cell}" + ("（t−1 閘）" if cid in REG_T1 else "")
        out.append((cid, "②" if cid == 1 else "④", sp["fam"], name, sp))
    out.append((0, "③", "P12", "門檻B（W1）＝ P12 策略側 H120 N8", {"fam": "P12"}))
    for cid, key in P9_CELLS.items():
        out.append((cid, "④", "P9", f"#{cid} {P9_NAME[cid]}", {"fam": "P9", "key": key}))
    return out


CELLS = cell_list()
CELL = {c[0]: c for c in CELLS}


def engine_family(cid):
    f = CELL[cid][4]["fam"]
    return "P12" if f in ("P12", "P14", "P17") else f


def affected_from(cid):
    """T4：此格最早受資料尾讀法影響的日曆位置。"""
    sp = CELL[cid][4]; f = sp["fam"]
    if f in ("P12", "P14", "P17", "P9"):
        return _G["ch12"]
    rule = sp.get("rule", "H60")
    return _G["ch_and"]["LD" if rule == "LD" else rule]


def sig_of(cid, variant, w0, w1):
    sp = CELL[cid][4]; f = sp["fam"]
    if f in ("P12", "P14", "P17", "P9"):
        s = _G["s12_mtm"] if variant == "mtm" else _G["s12_eng"]
    else:
        s = _G["AND_mtm"] if variant == "mtm" else _G["AND_eng"]
        if f == "P10" and sp["reg"]:
            m = _G["reg_t1"] if cid in REG_T1 else _G["reg"]
            s = s[m[s["entry_pos"].to_numpy()]]
    e = s["entry_pos"].to_numpy()
    return s[(e >= w0) & (e <= w1)]


def run_engine(cid, sig, r, variant, audit=None):
    """⭐ 全檔只有這裡呼叫引擎；參數逐字照 rerun17._sim_engine／_one_p12、researchP9run.sim。audit＝None 時與原呼叫相同（引擎預設 None；list 只記錄成交、⛔ 不動數值路徑）。"""
    sp = CELL[cid][4]; f = sp["fam"]; G = _G
    cl, op, NP = G["closes"], G["opens"], G["NP"]
    if f == "P10":
        return R.simulate_mtm(sig, sp["rule"], sp["N"], np.random.default_rng(P10_SEED0 + r), cl, op, NP, return_equity=True, audit=audit)
    if f in ("P1", "P3B"):
        kw = dict(d_max=sp["d"], pick=sp["pick"], queue_days=RR.P1_QUEUE if sp["d"] is not None else 0, return_equity=True)
        if f == "P1":
            return R.simulate_mtm(sig, "H60", sp["N"], np.random.default_rng(P1_SEED0 + r), cl, op, NP, log=[], audit=audit, **kw)
        return R.simulate_mtm(sig, "H60", sp["N"], np.random.default_rng(P1_SEED0 + r), cl, op, NP,
                              cash_mode="bench", bench=G["benchP"], bench_cost=RR.COST_STD / 2, audit=audit, **kw)
    if f in ("P12", "P14", "P17"):
        R.COST = RR.COST_STD
        try:
            return R.simulate_mtm(sig, RR.P12_RULE, RR.P12_N, np.random.default_rng(P12_SEED0 + r), cl, op, NP,
                                  return_equity=True, pick=None, cap_fn=None, d_max=None, queue_days=0, cash_mode="zero",
                                  bench=None, log=None, audit=audit)
        finally:
            R.COST = RR.COST_STD
    if f == "P9":
        from . import researchP9run as P9R
        P9R._G["flags"] = G["flags_plus"] if variant == "mtm" else G["flags_orig"]
        kw = P9R.engine_kw(sp["key"])
        return R.simulate_mtm(sig, P9R.RULE, P9R.N_MAIN, np.random.default_rng(P9_SEED0 + r), cl, op, NP,
                              return_equity=True, report_maxw=True, audit=audit, **kw)
    raise ValueError(f)


def p12_derived(eq, w0, w1):
    """W4：③（W1）、#8 P14 w=0.50、#5 P17 R_eq 在窗內的三條序列（rerun17._one_p12 同式）。"""
    from . import researchp14 as P14
    from . import researchp17 as P17
    n = w1 - w0 + 1
    E = np.asarray(eq, float)[w0:w1 + 1]; B = _G["bench"][w0:w1 + 1]
    V14 = P14.blend(E, B, 0.50)
    rb = P17.rebal_days(_G["cal"], w0, w1)
    mask = np.zeros(n, bool); mask[[int(t) for t in rb]] = True
    sB = {int(t): P17.sigma_at(B, int(t)) for t in rb}
    wp = P17.w_paths(E, B, rb, n, sB)["R_eq"]
    V17, _, _ = P17.compose(E, B, wp, mask)
    return {0: E, 8: V14, 5: V17}


def _job(args):
    """一顆種子、一個引擎格、一組窗（同一個窗的 sig 過濾）⇒ 回列。cid＝0 時同時產 0／5／8（rolling 只要 0）。"""
    cid, variant, wins, r, want = args
    out = []
    for w in wins:
        sig = sig_of(cid, variant, w["w0"], w["w1"])
        s = run_engine(cid, sig, r, variant)
        eq = np.asarray(s["equity"], float)
        series = p12_derived(eq, w["w0"], w["w1"]) if cid == 0 else {cid: eq[w["w0"]:w["w1"] + 1]}
        for c, v in series.items():
            if c not in want:
                continue
            ret, mdd = seg_stats(v)
            out.append({"win": w["key"], "cell": c, "variant": variant, "r": r, "ret": ret, "mdd": mdd,
                        "end_value": CAPITAL * (1.0 + ret), "trades": int(s["trades"]), "first": int(s["first"]),
                        "n_sig": int(len(sig))})
    return out


# ═════════════ G1 ═════════════
def _g1(args):
    cid, r = args
    G = _G; cal = G["cal"]; w0, w1 = RR.win_bounds(cal)
    f = CELL[cid][4]["fam"]
    sig = sig_of(cid, "eng", w0, w1)
    s = run_engine(cid, sig, r, "eng")
    eq = np.asarray(s["equity"], float)
    ncal = G["ncal"]
    rows = []
    if cid == 0:
        V = p12_derived(eq, w0, w1); n = w1 - w0 + 1
        for c in (0, 8, 5):
            cg, mg = R13.window_stats(V[c], 0, n, 0, n)
            rows.append({"cell": c, "r": r, "cagr": float(cg), "mdd": float(mg), "vol": RR.ann_vol(V[c]), "first": int(s["first"]),
                         "end": int(min(s["end"], ncal)), "trades": int(s["trades"]), "eq_sha": sha16(eq[:ncal]) if c != 0 else "",
                         "eq_sha64": sha64(eq[:ncal]), "ret_mine": seg_stats(V[c])[0]})
        return rows
    c_, m_, v_ = RR.win_metrics(eq, s["first"], s["end"], w0, w1)
    return [{"cell": cid, "r": r, "cagr": float(c_), "mdd": float(m_), "vol": float(v_), "first": int(s["first"]),
             "end": int(min(s["end"], ncal)), "trades": int(s["trades"]), "eq_sha": sha16(eq[:ncal]), "eq_sha64": sha64(eq[:ncal]),
             "ret_mine": seg_stats(eq[w0:w1 + 1])[0]}]


def gate(procs, reps, log):
    cal = _G["cal"]; w0, w1 = RR.win_bounds(cal)
    RTP = dict(float_precision="round_trip")
    res = {}
    bw = RR.bench_row(cal, _G["bench"], w0, w1 + 1)
    c50, m50 = R13.window_stats(_G["bench"][w0:w1 + 1] / _G["bench"][w0], 0, w1 - w0 + 1, 0, w1 - w0 + 1)
    ok0 = repr(bw["cagr"]) == repr(RR.ANCHOR[0]) and repr(bw["mdd"]) == repr(RR.ANCHOR[1])
    mine = seg_stats(_G["bench"][w0:w1 + 1])
    res["0050錨"] = {"年化": bw["cagr"], "回落": bw["mdd"], "錨": list(RR.ANCHOR), "逐位元": ok0,
                    "本檔回落式": mine[1], "本檔回落式_逐位元": repr(mine[1]) == repr(RR.ANCHOR[1])}
    log(f"[G1 0050] {res['0050錨']}")
    cids = [c[0] for c in CELLS if c[0] not in (5, 8)]
    with Pool(procs) as pool:
        rows = [x for y in pool.map(_g1, [(c, r) for c in cids for r in range(reps)], chunksize=2) for x in y]
    M = pd.DataFrame(rows)
    M.to_csv(os.path.join(OUT, "g1_seeds.csv"), index=False)
    ref_main = pd.read_csv(os.path.join(RR.OUT, "seeds_main.csv"), dtype={"eq_sha": str}, **RTP)
    ref_t1 = pd.read_csv(os.path.join(RR.OUT, "regime_t1", "seeds.csv"), dtype={"eq_sha": str}, **RTP)
    ref_p9 = pd.read_csv(os.path.join(HERE, "resultsP9run", "seeds_arms.csv"), dtype={"eq_sha": str}, **RTP)
    allok = ok0
    for c in sorted(M["cell"].unique()):
        g = M[M["cell"] == c].set_index("r").sort_index()
        if c in P9_CELLS:
            ref = ref_p9[ref_p9["arm"] == P9_CELLS[c]].set_index("r"); src = "resultsP9run/seeds_arms.csv"
            cols = {"cagr": "cagr", "mdd": "mdd", "vol": "vol", "first": "first", "end": "end", "trades": "trades", "eq_sha64": "eq_sha"}
        elif c in REG_T1:
            ref = ref_t1[(ref_t1["stage"] == "t1") & (ref_t1["cell"] == c)].set_index("r"); src = "resultsN17/regime_t1/seeds.csv（t1）"
            cols = {k: k for k in ("cagr", "mdd", "vol", "first", "end", "trades", "eq_sha")}
        else:
            ref = ref_main[(ref_main["stage"] == "main") & (ref_main["cell"] == c)].set_index("r"); src = "resultsN17/seeds_main.csv（main）"
            cols = {k: k for k in ("cagr", "mdd", "vol", "first", "end", "trades")}
            if c not in (0, 5, 8):
                cols["eq_sha"] = "eq_sha"
        ref = ref.loc[g.index]
        bad = {}
        for mine_c, ref_c in cols.items():
            x, y = g[mine_c], ref[ref_c]
            if mine_c in ("cagr", "mdd", "vol"):
                ne = sum(repr(float(p)) != repr(float(q)) for p, q in zip(x, y))
            elif mine_c.startswith("eq_sha"):
                ne = sum(str(p) != str(q) for p, q in zip(x, y))
            else:
                ne = sum(int(p) != int(q) for p, q in zip(x, y))
            bad[ref_c] = int(ne)
        ok = len(g) == reps and all(v == 0 for v in bad.values())
        allok &= ok
        res[f"格{c}"] = {"對象": src, "顆數": len(g), "不同數": bad, "逐位元": ok,
                         "年化中位_本檔": float(g["cagr"].median()), "年化中位_參照": float(ref["cagr"].median())}
        log(f"[G1 格{c:>2}] {src}｜{len(g)} 顆｜不同數 {bad}｜{'✅' if ok else '⛔'}")
    res["全部過"] = bool(allok)
    json.dump(res, open(os.path.join(OUT, "g1.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    return allok


# ═════════════ 主跑 ═════════════
def run(procs, reps, log):
    cal = _G["cal"]; ncal = _G["ncal"]
    FW = fixed_windows(cal); RW = rolling_windows(cal)
    log(f"[窗] 固定 {len(FW)}：{[(w['key'], w['d0'], w['d1'], w['days']) for w in FW]}")
    log(f"[窗] 滾動 {len(RW)}：{RW[0]['d0']}～{RW[0]['d1']} … {RW[-1]['d0']}～{RW[-1]['d1']}；天數 {min(w['days'] for w in RW)}～{max(w['days'] for w in RW)}")
    json.dump({"fixed": FW, "rolling": RW}, open(os.path.join(OUT, "windows.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # 0050
    B = _G["bench"]; rows = []
    for kind, WS in (("fixed", FW), ("rolling", RW)):
        for w in WS:
            ret, mdd = seg_stats(B[w["w0"]:w["w1"] + 1])
            rows.append({"kind": kind, "win": w["key"], "d0": w["d0"], "d1": w["d1"], "days": w["days"], "ret": ret, "mdd": mdd,
                         "end_value": CAPITAL * (1 + ret), "end_value_net_etf": CAPITAL * (1 + ret) * (1 - COST_ETF)})
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "bench_windows.csv"), index=False)
    # 工作：(引擎格, 版本, 窗組, r, 要的格)
    engine_cells = [c[0] for c in CELLS if c[0] not in (5, 8)]
    jobs = []
    for cid in engine_cells:
        want = {0, 5, 8} if cid == 0 else {cid}
        af = affected_from(cid)
        jobs += [(cid, "mtm", FW, r, want) for r in range(reps)]
        aff = [w for w in FW if w["w1"] >= af]
        if aff:
            jobs += [(cid, "eng", aff, r, want) for r in range(reps)]
    for cid in (1, 0):
        af = affected_from(cid)
        jobs += [(cid, "mtm", RW, r, {cid}) for r in range(reps)]
        aff = [w for w in RW if w["w1"] >= af]
        if aff:
            jobs += [(cid, "eng", aff, r, {cid}) for r in range(reps)]
    # 滾動窗的工作拆小一點（每工作 ≤ 12 窗）
    J = []
    for cid, v, WS, r, want in jobs:
        for i in range(0, len(WS), 12):
            J.append((cid, v, WS[i:i + 12], r, want))
    kind_of = {w["key"]: "fixed" for w in FW} | {w["key"]: "rolling" for w in RW}
    log(f"[工作] {len(J):,} 件（{procs} 行程）")
    t0 = time.time(); out = []
    with Pool(procs) as pool:
        for i, rs in enumerate(pool.imap_unordered(_job, J, chunksize=4)):
            out += rs
            if (i + 1) % 500 == 0:
                log(f"  {i + 1:,}/{len(J):,}｜{time.time() - t0:.0f}s")
    S = pd.DataFrame(out)
    S.insert(0, "kind", S["win"].map(kind_of))
    S["seed"] = [{"P10": P10_SEED0, "P1": P1_SEED0, "P3B": P1_SEED0, "P12": P12_SEED0, "P14": P12_SEED0, "P17": P12_SEED0,
                  "P9": P9_SEED0}[CELL[c][4]["fam"]] + r for c, r in zip(S["cell"], S["r"])]
    S = S.sort_values(["kind", "win", "cell", "variant", "r"], kind="stable").reset_index(drop=True)
    S.to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False, compression={"method": "gzip", "mtime": 0})
    log(f"[完成] seeds.csv.gz {len(S):,} 列｜{time.time() - t0:.0f}s")
    aff = {c[0]: (str(cal[affected_from(c[0])].date()) if affected_from(c[0]) < ncal else None) for c in CELLS}
    json.dump({"affected_from": aff}, open(os.path.join(OUT, "affected.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


# ═════════════ 彙總 ═════════════
Q = (10, 25, 50, 75, 90)


def table(log):
    S = pd.read_csv(os.path.join(OUT, "seeds.csv.gz"), float_precision="round_trip")
    Bw = pd.read_csv(os.path.join(OUT, "bench_windows.csv"), float_precision="round_trip")
    W = json.load(open(os.path.join(OUT, "windows.json"), encoding="utf-8"))
    g1 = json.load(open(os.path.join(OUT, "g1.json"), encoding="utf-8"))
    setup_info = json.load(open(os.path.join(OUT, "setup.json"), encoding="utf-8"))
    aff = json.load(open(os.path.join(OUT, "affected.json"), encoding="utf-8"))["affected_from"]
    bmap = {(k, w): row for (k, w), row in zip(zip(Bw["kind"], Bw["win"]), Bw.to_dict("records"))}
    order = [c[0] for c in CELLS]
    arm_of = {c[0]: c[1] for c in CELLS}; name_of = {c[0]: c[3] for c in CELLS}
    arm_of[5] = arm_of[8] = "④"

    def agg(g, b):
        v = g["end_value"].to_numpy(float)
        p = np.percentile(v, Q)
        return {"種子數": len(v), "期末金額_p10": p[0], "期末金額_p25": p[1], "期末金額_中位": p[2], "期末金額_p75": p[3],
                "期末金額_p90": p[4], "窗內報酬_中位": float(np.median(g["ret"])), "最大回落_中位": float(np.median(g["mdd"])),
                "贏0050種子比例": float((v > b["end_value"]).mean()), "交易筆數_中位": float(np.median(g["trades"]))}

    rows = []
    for w in W["fixed"]:
        b = bmap[("fixed", w["key"])]
        rows.append({"窗鍵": w["key"], "窗": w["label"], "起": w["d0"], "迄": w["d1"], "交易日數": w["days"], "滿一年": w["full_year"],
                     "臂": "①", "格": "0050", "名稱": "0050 買進持有（還原含息、不扣成本＝錨點算法）", "版本": "—",
                     "種子數": 0, "期末金額_中位": b["end_value"], "窗內報酬_中位": b["ret"], "最大回落_中位": b["mdd"],
                     "0050扣ETF來回0.385%期末": b["end_value_net_etf"]})
        for c in [1, 0] + [x for x in order if x not in (0, 1)]:
            for v in ("mtm", "eng"):
                g = S[(S["kind"] == "fixed") & (S["win"] == w["key"]) & (S["cell"] == c) & (S["variant"] == v)]
                if not len(g):
                    continue
                rows.append({"窗鍵": w["key"], "窗": w["label"], "起": w["d0"], "迄": w["d1"], "交易日數": w["days"], "滿一年": w["full_year"],
                             "臂": arm_of[c], "格": f"#{c}" if c else "門檻B", "名稱": name_of[c],
                             "版本": "主版（資料尾補訊號、照收盤計值）" if v == "mtm" else "引擎原樣（資料尾截斷的訊號被丟）",
                             "此格受資料尾影響起": aff.get(str(c)), **agg(g, b)})
    F = pd.DataFrame(rows)
    F.to_csv(os.path.join(OUT, "fixed_windows.csv"), index=False)
    # 滾動
    rr = []
    for w in W["rolling"]:
        b = bmap[("rolling", w["key"])]
        row = {"窗鍵": w["key"], "起": w["d0"], "迄": w["d1"], "交易日數": w["days"], "0050一年報酬": b["ret"], "0050期末": b["end_value"]}
        for c, lab in ((1, "②#1"), (0, "③門檻B")):
            g = S[(S["kind"] == "rolling") & (S["win"] == w["key"]) & (S["cell"] == c) & (S["variant"] == "mtm")]
            v = g["end_value"].to_numpy(float)
            row[f"{lab}_期末中位"] = float(np.median(v)); row[f"{lab}_減0050"] = float(np.median(v)) - b["end_value"]
            row[f"{lab}_贏0050種子比例"] = float((v > b["end_value"]).mean())
            ge = S[(S["kind"] == "rolling") & (S["win"] == w["key"]) & (S["cell"] == c) & (S["variant"] == "eng")]
            row[f"{lab}_引擎原樣期末中位"] = float(np.median(ge["end_value"])) if len(ge) else np.nan
        rr.append(row)
    Rw = pd.DataFrame(rr)
    Rw.to_csv(os.path.join(OUT, "rolling_windows.csv"), index=False)
    # 三分位：依 0050 一年報酬排序（同值以窗起點先後），np.array_split 切三組（低／中／高）
    idx = Rw.sort_values(["0050一年報酬", "起"], kind="stable").index.to_numpy()
    grp = np.empty(len(Rw), object)
    for name, part in zip(("低", "中", "高"), np.array_split(idx, 3)):
        grp[part] = name
    Rw["組"] = grp
    tr = []
    for name in ("低", "中", "高"):
        g = Rw[Rw["組"] == name]
        row = {"組": name, "窗數": len(g), "0050一年報酬_最低": float(g["0050一年報酬"].min()), "0050一年報酬_最高": float(g["0050一年報酬"].max()),
               "0050一年報酬_平均": float(g["0050一年報酬"].mean())}
        for lab in ("②#1", "③門檻B"):
            d = g[f"{lab}_減0050"]
            k = int(d.idxmin())
            row[f"{lab}_贏0050窗數比例"] = float((d > 0).mean()); row[f"{lab}_贏窗數"] = int((d > 0).sum())
            row[f"{lab}_平均差（元）"] = float(d.mean()); row[f"{lab}_最差一窗差（元）"] = float(d.min())
            row[f"{lab}_最差一窗起"] = Rw.loc[k, "起"]
        tr.append(row)
    T = pd.DataFrame(tr)
    T.to_csv(os.path.join(OUT, "rolling_terciles.csv"), index=False)
    Rw[["窗鍵", "組"]].to_csv(os.path.join(OUT, "rolling_groups.csv"), index=False)
    summ = {"說明": "描述、⛔ 不判、⛔ 不計 N；程式與參數一字不動，只換起訖（讀法見 researchYear1M.py 檔頭）",
            "滾動窗表頭": f"相鄰窗重疊 11/12，{len(Rw)} 個窗實際獨立的年份只有約 9 個 ⇒ 只能叫「形狀」，⛔ 不叫證據",
            "G1": g1, "設定": setup_info, "固定窗數": len(W["fixed"]), "滾動窗數": len(Rw),
            "滾動窗範圍": [W["rolling"][0]["d0"], W["rolling"][-1]["d0"], W["rolling"][-1]["d1"]],
            "受資料尾影響起": aff, "種子檔列數": len(S)}
    json.dump(summ, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[table] fixed_windows.csv {len(F)} 列｜rolling_windows.csv {len(Rw)} 列｜rolling_terciles.csv {len(T)} 列")


# ═════════════ panel：補 2026-09-01 量測日 ═════════════
def build_panel_0901(procs, log):
    from . import p4_features as P4F
    from . import researchp4 as RP4
    import backtest.p9_panel_ext as PE            # 它 import researchH2（D.DATA 指快照、chdir ~/tw-p17）
    RR.use_snapshot()
    cal = D.load_calendar()
    U = PE.load_gate3()
    pos = np.array([int(cal.searchsorted(pd.Timestamp(MD_OVERLAP))), int(cal.searchsorted(pd.Timestamp(MD_NEW)))])
    mdays = P4F.measurement_days(cal, "2026-08-01", str(cal[-1].date()))
    if [str(cal[p].date()) for p in pos] != [MD_OVERLAP, MD_NEW] or list(mdays) != list(pos):
        raise SystemExit(f"⛔ 量測日對不上：{[str(cal[p].date()) for p in mdays]}")
    log(f"[panel] gate3 {len(U)} 檔｜量測日 {MD_OVERLAP}（重疊 fixture）＋ {MD_NEW}（新增）")
    panel, M = RP4.build_panel(cal, U, pos, procs=procs, log=log)
    if len(M):
        raise SystemExit(f"⛔ min_periods 常設斷言不成立（{len(M)} 列）")
    ext = P4F.read_panel(PANEL_EXT)
    panel = PE.mask_fwd(panel)[list(ext.columns)]
    ov = panel[panel["measure_date"] == pd.Timestamp(MD_OVERLAP)].reset_index(drop=True)
    buf = io.StringIO(); ov.to_csv(buf, index=False); buf.seek(0)
    ov_rt = pd.read_csv(buf, dtype={"stock_id": str}, parse_dates=["measure_date"], float_precision="round_trip")
    ref = ext[ext["measure_date"] == pd.Timestamp(MD_OVERLAP)].reset_index(drop=True)
    ok, bad = PE.frames_identical(ov_rt, ref)
    log(f"[panel] 重疊 {MD_OVERLAP}：本檔 {len(ov_rt)} 列 vs panel_ext {len(ref)} 列 ⇒ 逐位元 {ok} {bad}")
    if not ok:
        raise SystemExit("⛔ 重疊量測日不逐位元相同 ⇒ 不寫檔")
    new = panel[panel["measure_date"] == pd.Timestamp(MD_NEW)].reset_index(drop=True)
    new.to_csv(PANEL_0901, index=False, compression={"method": "gzip", "mtime": 0})
    info = {"重疊量測日": MD_OVERLAP, "重疊列": len(ov_rt), "重疊逐位元": ok, "新增量測日": MD_NEW, "新增列": len(new),
            "新增eligible": int(new["eligible"].astype(bool).sum()), "fwd欄": "新增列一律 NaN（p9_panel_ext.mask_fwd）",
            "sha256": hashlib.sha256(open(PANEL_0901, "rb").read()).hexdigest()}
    json.dump(info, open(os.path.join(OUT, "panel_0901.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[panel] {info}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["panel", "gate", "run", "table"])
    ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--reps", type=int, default=REPS)
    ap.add_argument("--g1reps", type=int, default=20)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "a", encoding="utf-8")
    T0 = time.time()

    def log(x):
        x = f"[{time.time() - T0:6.0f}s] {x}"
        print(x, flush=True); logf.write(x + "\n"); logf.flush()

    log(f"===== researchYear1M {a.stage} {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜D.DATA {D.DATA} =====")
    if abs(R.COST - 0.00585) > 1e-15:
        raise SystemExit(f"⛔ COST {R.COST}")
    if a.stage == "panel":
        build_panel_0901(a.procs, log); return
    if a.stage == "table":
        table(log); return
    info = setup(log)
    json.dump(info, open(os.path.join(OUT, "setup.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    if a.stage == "gate":
        ok = gate(a.procs, a.g1reps, log)
        log(f"[G1] {'✅ 全部逐位元' if ok else '⛔ 不過'}")
        if not ok:
            raise SystemExit("⛔ G1 不過，停")
        return
    g1 = json.load(open(os.path.join(OUT, "g1.json"), encoding="utf-8"))
    if not g1.get("全部過"):
        raise SystemExit("⛔ G1 沒過 ⇒ 拒跑")
    run(a.procs, a.reps, log)


if __name__ == "__main__":
    main()
