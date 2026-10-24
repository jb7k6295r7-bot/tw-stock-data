# -*- coding: utf-8 -*-
"""「3 年內漲過 3 倍」候選篩選口徑重算 11 檔＋ETN（產業 seq10 §二、裁定 seq466 §三）——回測線計算子代理。
⚠ 候選篩選用的判斷，不是回測證據；⛔ 不計 N、不判定、不改任何規則。
⛔ 不 commit、不改既有檔；researchRevTurn_freq（ensure_data、prices、log）、researchTopSell_freq（raw_close）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTriple15y [--procs 3]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTriple15y_check
輸出 backtest/resultsTriple15y/：table.csv、summary.md、main.json、run.log（⛔ 不放美股逐日價格，只放倍數、日期、過／未過）

═══ 讀法（Y 標；★＝執行者定）═══
 Y0 口徑（使用者定）：含現金與股票股利還原價；判斷日 J ＝ 2026-10-22（台股最新資料日；美股 ＝ 2026-10-22 或之前最近 NYSE 交易日）；
    15 年窗 ＝ 2011-10-22 起（＝ 合併日曆第一個 ≥ 該日的交易日）～ J；任一日 t（有效 K 棒）起，(t, t＋750]（交易日位置）內最高收盤 ÷ t 收盤 ≥ 3 ⇒「有前例」。
    主口徑（嚴格）：t ≥ 窗首、t＋750 ≤ J 的位置（750 日窗完整落在 15 年窗內）。
    ★ 延伸欄（參考）：允許 t＋750 ＞ J，窗截到 J（＝ 近 3 年內起漲、還沒走滿 750 日的也算；倍數只會 ≥ 嚴格版）。
 Y1 台股價格 ＝ 本線共用合併面板（researchRevTurn_freq.prices 原式，同 researchLampTrade Q1：早年 eotc 2004-02～2014-12 ＋ 主 rerun17 H2D
    2015-01～2026-09-24，還原含息收盤 C；資料 sha ＝ PIN）。
    ★ 尾段 2026-09-25～J（面板沒有）：最新 origin/main 的 data/stocks/<代號>.csv 原始收盤，接在面板最後一根有效 K 棒後：
       尾段還原收盤[d] ＝ 原始收盤[d] × k × Π_{data/adj 事件 e ∈ (面板尾, d]} (1 ÷ factor_e)，k ＝ 面板 C[面板尾] ÷ 原始收盤[面板尾]（origin/main）；
       面板尾當天面板世界原始收盤須 ＝ origin/main 原始收盤（不符 ⇒ 中止）。尾段日曆 ＝ origin/main data/calendar.csv。
       尾段壞根 ＝ 有效 K 棒間隔 ≥ 5 交易日（seq335）或 原始收盤比 ≤0.55／≥1.8 且區間內無 data/adj 事件（照報）。
 Y2 壞根 BAD ＝ 面板原定義（缺口 ≥5 日 seq335 ∪ 價格斷點 ∪ 幽靈還原 ∪ crashwork ∪ 早年 reduce_v2 ∪ 接縫）＋ Y1 尾段壞根。
    BAD[b] ＝ b 與前一根有效 K 棒之間不可相連。
    ★ 主口徑 ＝「壞根處截斷」：t 的窗遇到 (t, t＋750] 內第一個壞根 b ⇒ 只看 (t, b−1]（本線 seq335 硬斷點：視窗不跨壞根）。
    參考欄 ＝「跨壞根照面板」：不截、照面板還原價跨過去；最大倍數所在窗若跨壞根 ⇒ 標 ⚠。
 Y3 未還原對照 ＝ 同法、但用原始收盤（早年 ＝ 面板早年世界 data/stocks，2015 起 ＝ 主世界，尾段 ＝ origin/main），
    ★ 不截壞根（＝ 產業線 10/23 原法的對照；原法細節未知，只換價格）；位置用同一合併日曆。
 Y4 每檔報：最大倍數（及 t、高點日）、≥3 過／未過、第一次 ≥3 的 t（及該窗第一個達 3 倍的日子）、窗內壞根日、15 年窗內第一根有效 K 棒。
 Y5 美股 ETN（Eaton）：私有庫 us-stock-data 最新 origin/main 的 data/prices_yahoo/ETN.csv（git show、只讀）；還原收盤 ＝ adjclose（Yahoo：含息、分割）；
    未還原對照 ＝ close（Yahoo close 已含分割調整、不含息；ETN 2011-10 之後無分割）；日曆 ＝ 該檔自己的列（NYSE 交易日）。
    ⚠ 該檔只從 2015-12-01 起（面板入指數前暖身起點）⇒ 15 年窗只能從 2015-12-01 算（照報）。
    硬斷點 ＝ 有效 K 棒間隔 ≥ 5 個 NYSE 交易日（us_data.long_gaps 同參數；日曆 ＝ data/macro/yahoo_GSPC.csv）。
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchRevTurn_freq as RT             # noqa: E402  ensure_data、prices、log
from backtest import researchTopSell_freq as TS             # noqa: E402  raw_close

OUT = "backtest/resultsTriple15y"
PIN = "9b0e9882572c"                                         # 同 researchLampTrade（rtfwork 已有快取）
J = pd.Timestamp("2026-10-22")
W0 = pd.Timestamp("2011-10-22")
H = 750
X = 3.0
STOCKS = [("1503", "士電"), ("1513", "中興電"), ("1305", "華夏"), ("1312", "國喬"), ("4510", "高鋒"), ("6609", "瀧澤科"),
          ("8936", "國統"), ("3376", "新日興"), ("2014", "中鴻"), ("1101", "台泥"), ("2002", "中鋼")]
US_REPO = os.path.expanduser("~/us-stock-data")
log = RT.log


def gshow(path, repo=None, ref="origin/main"):
    t = subprocess.run(["git"] + (["-C", repo] if repo else []) + ["show", f"{ref}:{path}"], capture_output=True)
    return t.stdout if t.returncode == 0 else None


def gsha(repo=None, ref="origin/main"):
    return subprocess.run(["git"] + (["-C", repo] if repo else []) + ["rev-parse", ref], capture_output=True, text=True, check=True).stdout.strip()


# ═════════════ 核心：滾動 750 日最大倍數 ═════════════
def scan(C, bad, w0, je, truncate, allow_tail, h=H, x=X):
    """C：位置序列（NaN ＝ 無有效 K 棒）；bad：BAD 旗標；窗首 w0、判斷日 je（位置）。
    回 dict：best（倍數、t、高點位置、是否跨壞根）、first（第一個 ≥x 的 t、該窗第一個達 x 倍位置）、n_t（可用起點數）。"""
    best = (np.nan, -1, -1, False); first = None; n_t = 0
    tmax = je - 1 if allow_tail else je - h
    badpos = np.flatnonzero(bad)
    for t in range(w0, tmax + 1):
        c0 = C[t]
        if not np.isfinite(c0) or c0 <= 0:
            continue
        end = min(t + h, je)
        k = int(np.searchsorted(badpos, t, "right"))
        b = int(badpos[k]) if k < len(badpos) and badpos[k] <= end else -1
        cross = b >= 0
        e2 = b - 1 if (truncate and cross) else end
        if e2 <= t:
            continue
        seg = C[t + 1:e2 + 1]
        if not np.isfinite(seg).any():
            continue
        n_t += 1
        j = int(np.nanargmax(seg)); m = seg[j] / c0
        if not (m <= best[0]):                      # NaN 起始 ⇒ 取
            best = (float(m), t, t + 1 + j, bool(cross and not truncate))
        if first is None and m >= x:
            hit = int(np.flatnonzero(seg >= x * c0)[0])
            first = (t, t + 1 + hit, bool(cross and not truncate))
    return {"best": best, "first": first, "n_t": n_t}


def fmt(res, D):
    m, t, hp, cr = res["best"]
    f = res["first"]
    return {"倍數": (round(m, 3) if np.isfinite(m) else np.nan), "起點t": (str(D[t].date()) if t >= 0 else ""),
            "高點日": (str(D[hp].date()) if hp >= 0 else ""), "過": ("過" if np.isfinite(m) and m >= X else "未過"),
            "第一次≥3起點": (str(D[f[0]].date()) if f else ""), "第一次達3倍日": (str(D[f[1]].date()) if f else ""),
            "⚠跨壞根": ("⚠" if cr else ""), "起點數": res["n_t"]}


# ═════════════ 台股：面板＋尾段 ═════════════
def tw_series(PX, sid, TCAL, CEND_D):
    """回 (C 還原, R 原始, BAD) 於 合併日曆＋尾段日曆 上；與尾段資訊。"""
    CAL, C, BAD, VP = PX["CAL"], PX["C"], PX["BAD"], PX["VP"]
    i = PX["ix"][sid]; NE = PX["NE"]
    n0 = len(CAL); nt = len(TCAL)
    Ca = np.full(n0 + nt, np.nan); Ra = np.full(n0 + nt, np.nan); Ba = np.zeros(n0 + nt, bool)
    Ca[:n0] = C[i]; Ba[:n0] = BAD[i]
    # 原始收盤（面板兩世界的 data/stocks）
    for p in VP[i]:
        p = int(p)
        Ra[p] = TS.raw_close(PX["main_data"] if p >= NE else PX["early_data"], sid, CAL[p])
    # 尾段
    S = pd.read_csv(io.BytesIO(gshow(f"data/stocks/{sid}.csv")), dtype={"date": str})
    S["date"] = pd.to_datetime(S["date"])
    S["close"] = pd.to_numeric(S["close"], errors="coerce")
    ok = S["close"].notna() & (S["close"] > 0)
    if "valid_bar" in S:
        ok &= pd.to_numeric(S["valid_bar"], errors="coerce").fillna(1).astype(int) == 1
    if "price_basis" in S:
        ok &= S["price_basis"].fillna("").astype(str) != "無成交"
    raw = dict(zip(S.loc[ok, "date"], S.loc[ok, "close"]))
    A = gshow(f"data/adj/{sid}.csv")
    ev = pd.read_csv(io.BytesIO(A), dtype=str) if A else pd.DataFrame(columns=["date", "factor", "event"])
    ev["date"] = pd.to_datetime(ev["date"])
    pl = int(VP[i][-1])
    info = {"面板最後有效": str(CAL[pl].date())}
    r_pl = raw.get(CAL[pl], np.nan); r_pl_panel = Ra[pl]
    info["面板尾原始收盤 origin/main／面板世界"] = [float(r_pl), float(r_pl_panel)]
    if not (np.isfinite(r_pl) and abs(r_pl - r_pl_panel) < 1e-9):
        raise SystemExit(f"⛔ {sid} 面板尾 {CAL[pl].date()} 原始收盤不符 {r_pl} vs {r_pl_panel}")
    if CEND_D - pl > 0:
        info["⚠ 面板最後有效不在面板尾"] = str(CAL[CEND_D].date())
    k = Ca[pl] / r_pl
    evs = ev[(ev["date"] > CAL[pl]) & (ev["date"] <= J)]
    info["尾段 adj 事件"] = [f"{r.date.date()} {r.event} f={r.factor}" for r in evs.itertuples()]
    prev_p, prev_r, prev_d = pl, r_pl, CAL[pl]
    tail_bad = []
    for q, d in enumerate(TCAL):
        p = n0 + q
        if d not in raw:
            continue
        r = raw[d]
        g = 1.0
        for e in evs.itertuples():
            if e.date <= d:
                g /= float(e.factor)
        Ca[p] = r * k * g; Ra[p] = r
        # 尾段壞根：間隔 ≥5 交易日 或 價比斷點且區間無事件
        gap = (p - prev_p - 1)
        inev = ((ev["date"] > prev_d) & (ev["date"] <= d)).any()
        ratio = r / prev_r
        if (gap >= 5 or ratio <= 0.55 or ratio >= 1.8) and not inev:
            Ba[p] = True; tail_bad.append(f"{d.date()}（間隔 {gap}、比 {ratio:.3f}）")
        prev_p, prev_r, prev_d = p, r, d
    info["尾段壞根"] = tail_bad
    info["尾段有效根數"] = int(np.isfinite(Ca[n0:]).sum())
    return Ca, Ra, Ba, info


def us_etn():
    sha = gsha(US_REPO)
    P = pd.read_csv(io.BytesIO(gshow("data/prices_yahoo/ETN.csv", US_REPO)), dtype={"date": str})
    P["date"] = pd.to_datetime(P["date"])
    for c in ("close", "adjclose"):
        P[c] = pd.to_numeric(P[c], errors="coerce")
    P = P[(P["close"] > 0) & (P["adjclose"] > 0)].drop_duplicates("date").sort_values("date")
    G = pd.read_csv(io.BytesIO(gshow("data/macro/yahoo_GSPC.csv", US_REPO)), dtype={"date": str})
    UCAL = pd.DatetimeIndex(pd.to_datetime(G["date"])).sort_values()
    UCAL = UCAL[(UCAL >= P["date"].iloc[0]) & (UCAL <= J)]
    jd = UCAL[-1]
    pos = {d: q for q, d in enumerate(UCAL)}
    n = len(UCAL)
    Ca = np.full(n, np.nan); Ra = np.full(n, np.nan); Ba = np.zeros(n, bool)
    miss = 0
    for r in P.itertuples():
        if r.date in pos:
            Ca[pos[r.date]] = r.adjclose; Ra[pos[r.date]] = r.close
        elif r.date <= J:
            miss += 1
    v = np.flatnonzero(np.isfinite(Ca))
    for a_, b_ in zip(v[:-1], v[1:]):
        if b_ - a_ - 1 >= 5:
            Ba[b_] = True
    w0 = int(np.searchsorted(UCAL.values, np.datetime64(max(W0, UCAL[0])), "left"))
    info = {"us_sha": sha, "資料起": str(P["date"].iloc[0].date()), "判斷日": str(jd.date()), "日曆外列": miss,
            "硬斷點(≥5日缺)": [str(UCAL[b].date()) for b in np.flatnonzero(Ba)]}
    return UCAL, Ca, Ra, Ba, w0, n - 1, info


def row_out(code, name, D, Ca, Ra, Ba, w0, je, extra):
    rM = scan(Ca, Ba, w0, je, truncate=True, allow_tail=False)
    rX = scan(Ca, Ba, w0, je, truncate=False, allow_tail=False)
    rT = scan(Ca, Ba, w0, je, truncate=True, allow_tail=True)
    rU = scan(Ra, Ba, w0, je, truncate=False, allow_tail=False)
    rUT = scan(Ra, Ba, w0, je, truncate=False, allow_tail=True)
    v = np.flatnonzero(np.isfinite(Ca[w0:je + 1]))
    bads = [str(D[b].date()) for b in np.flatnonzero(Ba[w0 + 1:je + 1]) + w0 + 1]
    o = {"代號": code, "名稱": name, "15年窗首": str(D[w0].date()), "判斷日": str(D[je].date()),
         "窗內第一根有效": (str(D[w0 + int(v[0])].date()) if len(v) else ""), "窗內壞根": "；".join(bads)}
    for tag, r in (("主_截斷", rM), ("跨壞根照面板", rX), ("延伸_窗尾截到判斷日", rT), ("未還原", rU), ("未還原_延伸", rUT)):
        for k, val in fmt(r, D).items():
            if tag != "跨壞根照面板" and k == "⚠跨壞根":
                continue
            o[f"{tag}_{k}"] = val
    o.update(extra)
    return o


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); a = ap.parse_args()
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    sha, DN, MD = RT.ensure_data(PIN)
    PX = RT.prices(sha, DN, a.procs)
    CAL = PX["CAL"]; CEND_D = len(CAL) - 1
    msha = gsha()
    TC = pd.read_csv(io.BytesIO(gshow("data/calendar.csv")), dtype=str)
    TC = pd.DatetimeIndex(pd.to_datetime(TC["date"]))
    TCAL = TC[(TC > CAL[-1]) & (TC <= J)]
    if J not in TC:
        raise SystemExit("⛔ 判斷日不在 origin/main 交易日曆")
    D = CAL.append(TCAL)
    je = len(D) - 1
    w0 = int(np.searchsorted(D.values, np.datetime64(W0), "left"))
    log(f"[Y1] 面板 sha {sha[:12]}｜日曆 {CAL[0].date()}～{CAL[-1].date()}｜尾段 origin/main {msha[:12]} {len(TCAL)} 日"
        f"（{TCAL[0].date()}～{TCAL[-1].date()}）｜窗首 {D[w0].date()}（pos {w0}）判斷日 {D[je].date()}（pos {je}）")
    rows = []; infos = {}
    for sid, nm in STOCKS:
        if sid not in PX["ix"]:
            log(f"⛔ {sid} 面板查無"); continue
        Ca, Ra, Ba, info = tw_series(PX, sid, TCAL, CEND_D)
        infos[sid] = info
        o = row_out(sid, nm, D, Ca, Ra, Ba, w0, je, {"市場": "台股", "價格來源": f"面板 {sha[:12]}＋尾段 origin/main {msha[:12]}"})
        rows.append(o)
        log(f"{sid} {nm}｜主 {o['主_截斷_倍數']} {o['主_截斷_過']} t {o['主_截斷_起點t']} 高 {o['主_截斷_高點日']}｜跨 {o['跨壞根照面板_倍數']}{o['跨壞根照面板_⚠跨壞根']}"
            f"｜延伸 {o['延伸_窗尾截到判斷日_倍數']}｜未還原 {o['未還原_倍數']}｜壞根 {o['窗內壞根']}｜{info}")
    UCAL, Ca, Ra, Ba, uw0, uje, uinfo = us_etn()
    infos["ETN"] = uinfo
    o = row_out("ETN", "Eaton", UCAL, Ca, Ra, Ba, uw0, uje, {"市場": "美股", "價格來源": f"us-stock-data {uinfo['us_sha'][:12]} prices_yahoo（私有，只出倍數）"})
    rows.append(o)
    log(f"ETN｜主 {o['主_截斷_倍數']} {o['主_截斷_過']} t {o['主_截斷_起點t']} 高 {o['主_截斷_高點日']}｜延伸 {o['延伸_窗尾截到判斷日_倍數']}｜未還原 {o['未還原_倍數']}｜{uinfo}")
    T = pd.DataFrame(rows)
    T.to_csv(os.path.join(OUT, "table.csv"), index=False, encoding="utf-8-sig")
    json.dump({"panel_sha": sha, "main_sha": msha, "J": str(J.date()), "W0": str(W0.date()), "H": H, "X": X, "info": infos},
              open(os.path.join(OUT, "main.json"), "w"), ensure_ascii=False, indent=1, default=str)
    # summary
    L = ["候選篩選用的判斷，不是回測證據；口徑：含息還原、判斷日前 15 年、從低點起算 750 交易日內 ≥3 倍",
         "",
         f"- 判斷日 {J.date()}（ETN 用 {uinfo['判斷日']}）；15 年窗 {D[w0].date()} 起；任一日 t 起 (t, t＋750 交易日] 最高收盤 ÷ t 收盤。",
         "- **主口徑**：含息還原、t＋750 ≤ 判斷日、**窗遇壞根截斷**（本線 seq335：視窗不跨壞根）。參考欄：跨壞根照面板（⚠ 標）、延伸（允許窗尾截到判斷日）、未還原價（產業線 10/23 原用口徑的對照）。",
         f"- 台股價格：本線合併還原面板（{sha[:12]}，到 {CAL[-1].date()}）＋尾段 {TCAL[0].date()}～{TCAL[-1].date()} 用 origin/main {msha[:12]} 原始收盤接上（含 data/adj 除權息）。",
         f"- ETN：私有庫 us-stock-data {uinfo['us_sha'][:12]} Yahoo adjclose（含息、分割）；⚠ 該檔只從 {uinfo['資料起']} 起 ⇒ ETN 的 15 年窗實際只有 {uinfo['資料起']}～{uinfo['判斷日']}。⛔ 不放逐日價格。",
         "",
         "| 代號 | 名稱 | 主口徑倍數 | 過？ | 起點 t | 高點日 | 第一次 ≥3 起點 | 跨壞根照面板 | 延伸（窗尾截到判斷日） | 未還原（倍數／過／t→高點） | 窗內壞根 |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for o in rows:
        L.append(f"| {o['代號']} | {o['名稱']} | {o['主_截斷_倍數']:.2f} | {o['主_截斷_過']} | {o['主_截斷_起點t']} | {o['主_截斷_高點日']} | {o['主_截斷_第一次≥3起點'] or '—'} |"
                 f" {o['跨壞根照面板_倍數']:.2f}{o['跨壞根照面板_⚠跨壞根']} | {o['延伸_窗尾截到判斷日_倍數']:.2f}（{o['延伸_窗尾截到判斷日_過']}，{o['延伸_窗尾截到判斷日_起點t']}→{o['延伸_窗尾截到判斷日_高點日']}） |"
                 f" {o['未還原_倍數']:.2f}／{o['未還原_過']}／{o['未還原_起點t']}→{o['未還原_高點日']} | {o['窗內壞根'] or '無'} |")
    L += ["", "- 「第一次 ≥3 起點」＝ 主口徑下最早一個達標的 t；table.csv 另有該窗第一個達 3 倍的日子、各欄起點數。",
          "- 壞根 ＝ 面板原定義（缺口 ≥5 日 ∪ 價格斷點 ∪ 幽靈還原 ∪ crashwork ∪ 早年 reduce_v2 ∪ 接縫）＋尾段同法；"
          "「跨壞根照面板」欄若最大倍數窗跨壞根則標 ⚠，該數字不可信（還原價在壞根處接不起來）。",
          "- 未還原欄不截壞根、也不還原除權息：只是換價格的對照，看差多少。",
          f"- 讀法全文見 backtest/researchTriple15y.py 檔頭（Y0～Y5）；對帳 researchTriple15y_check。耗時 {time.time() - t0:.0f}s。"]
    open(os.path.join(OUT, "summary.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(RT.LOG) + "\n")
    log(f"完成 {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
