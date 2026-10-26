# -*- coding: utf-8 -*-
"""主題標籤能否替營量、營飆加分 seq1（台股策略線 0328，sha b2e6be286b41a9ad；裁定 seq478 §五 核）——【②普查標籤】正式描述程式。
回測線計算子代理，2026-10-26 03:45（台北）起草。前瞻＋描述、⛔ 不判、⛔ 不計 N；標籤分開報、⛔ 不合併。
⭐ 裁定 seq480 §三（2026-10-27 00:41）：③盲判標籤撤掉；正式跑範圍 ＝ ②普查標籤（描述，筆數不足照標）＋①前瞻標籤（主，2026-11 起每月記筆數）。
   本檔：②普查 正式描述（--ruling seq480）＋①前瞻 每月筆數骨架（⛔ 不讀報酬）。
⛔ 不 commit、不改既有檔（策略鎖內營量／營飆程式一字不動；resultsYFallin、resultsThemeTag/freq 只讀）。

    乾跑（R 全 0，seq459 §一；⛔ seq366 不准含報酬的試跑或子樣本）：
      cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchThemeTag --dry
    正式跑（須裁定號；沒帶 --ruling seqNNN 拒跑）：
      PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchThemeTag --ruling seqNNN

═══ 讀法（除 freq 檔頭 Q1～Q8 外，本檔另定；寫死於看任何報酬之前；★＝執行者定〔另一讀法〕）═══
 F0 前置：resultsThemeTag/freq/check.json 必須「全過」，否則停。進場與標籤一律讀 freq/entries.csv（不另算）。
 F1 母體 ＝ entries.csv 持有狀態「完整」「提前」；「未滿」記未到、⛔ 不入分母（件數照報，★freq Q2）。
 F2 每筆 R ＝ 賣出金額（毛）÷ 買進金額 − 1 − 0.585%（trades_W 的 amt_out ÷ amt；＝ 回測引擎同一筆的還原含息、進場日開盤→出場日收盤）。
    大盤 ＝ data/history/market_tri.csv（發行量加權股價報酬指數，PIN 9b0e9882572c）★ 進場前一交易日收盤 → 出場日收盤（＝ researchLampCensus L5）
       〔另一讀法：進場日開盤 → 出場日收盤；報酬指數無開盤價，故不採〕；日期 ＝ 主世界日曆 t−1、出場 t；大盤不扣成本。
    超額 ＝ R − 大盤（主）；0050 副欄 ＝ R − 0050（researchV41EV.z50 含息還原收盤，同期同式）。
    ★ 0050 某日無收盤（2025-06-11～06-17 分割停牌）⇒ 用該日以前最後一個收盤（＝ tri_at 同式）；大盤缺日一律停（不補）。用到補值的筆數照報。
 F3 每組報：筆數、中位、平均、去掉最大 1 筆的平均（n＜2 ⇒ 空）、勝率（超額 ＞ 0）。組 ＝ 主題、非主題、同月隨機；差 ＝ 主題 − 非主題、主題 − 隨機（逐統計量相減）。
 F4 同月隨機：每個 (策略, 版) 用 default_rng(20261026) 抽 1,000 次；每次對主題組有筆的每個月 m，從該月 F1 母體全部 n_m 筆（含主題組）不放回抽 k_m 筆；
    每次算 F3 統計量，取 1,000 次的中位。★ 同一組抽法同時套大盤與 0050 兩欄〔另一讀法：兩欄各自重抽〕。
 F5 CI（只描述）：按進場月分群自助法，default_rng(20261026)、2,000 次；每次對 F1 母體的全部進場月有放回抽同數量月，
    算 主題 − 非主題 的 中位差 與 去最大 1 筆平均差；取 2.5／97.5 百分位；某次主題或非主題為空（或去最大 1 筆後為空）⇒ 該次跳過、照報跳過次數。
 F6 描述句（登錄 §四）：「主題組筆數 ≥ 30，且主題組超額中位、平均（去掉最大 1 筆後）都高於非主題組與隨機組」——以大盤欄判
    ★ 「平均（去掉最大 1 筆後）」只修飾平均；中位用全部筆數；隨機組用 F4 的 1,000 次中位〔另一讀法：中位也去掉最大 1 筆〕。
    主題組 ＜ 30 ⇒ 寫「筆數不足、不下描述結論」（數字照列）；否則「成立」／「不成立」。⛔ 不寫「有效」。
 F7 乾跑：⛔ 不讀 amt_out／cost、⛔ 不算任何價格比；R、大盤、0050 全設 0；只驗：配對鍵存在（buy 列＝(帳,代號,進場t)、sell 列＝(帳,代號,出場t)）、
    大盤與 0050 序列涵蓋所有需要的日期、抽樣與自助法流程跑通、F3 函式用合成數字 fixture 驗算。輸出到 resultsThemeTag/dry/（標「乾跑 R 全 0」）。
 F8 ①前瞻標籤骨架（seq480 §三；只記筆數、⛔ 不讀任何價格或報酬欄）：
    名單 ＝ backtest/forward/frontier/period01_main.md（第 1 期，sha16 30e87e3eb701136f，§二表「公司」欄 4 碼、括號內不計分者不算，＝ 42 家）
         ＋ period01_supp.md（增補，sha16 db0aab7b8a76ef1f，§一表最後一欄 4 碼，＝ 7 家；6664 群翊兩期都有 ⇒ 聯集 48 家）；sha 不符即停。
    ★ 凍結日：第 1 期 2026-10-26（裁定 seq478 §四存證）、增補 2026-10-27（裁定 seq480 §四存證）；某期只用於 進場日 ＞ 凍結日 的進場〔另一讀法：用 README 起點 10/27 開盤〕。
    ★ 前瞻進場來源 ＝ backtest/forward/yl_rule/positions.csv（營量 v1／營飆 v1「照規則」欄，forward_yl.py；只讀 策略、代號、進場日 三欄）、進場日 ≥ 2026-11-01
       〔另一讀法：每日名單 resultsDaily 的 A 名單〕。每月一行：月、策略、可用期別、主題組筆數、全部筆數。目前 0 個月（照寫）。
輸出（正式）backtest/resultsThemeTag/main/：rows.csv（每筆 R、大盤、0050、超額）、stats.csv、ci.csv、forward.csv、summary.md、run.json、run.log
"""
from __future__ import annotations

import argparse
import warnings
import io
import json
import os
import re
import subprocess
import sys
import time

import numpy as np
import pandas as pd

REPO = os.path.expanduser("~/tw-p17")
os.chdir(REPO)
sys.path.insert(0, REPO)
B = "backtest"
YFA = os.path.join(B, "resultsYFallin")
FREQ = os.path.join(B, "resultsThemeTag", "freq")
TIME = "2026-10-26 03:45（台北）"
STRAT = {"營量": "YL", "營飆": "v1"}
COST = 0.00585
SEED, NDRAW, NBOOT = 20261026, 1000, 2000
PIN = "9b0e9882572c"
VERS = ("寬", "嚴")
BENCH = ("大盤", "0050")
LOG: list = []
warnings.filterwarnings("ignore", message="All-NaN slice encountered")


def log(s=""):
    LOG.append(str(s)); print(s, flush=True)


def stats(x):
    x = np.asarray(x, float)
    n = len(x)
    if n == 0:
        return {"筆數": 0, "中位": np.nan, "平均": np.nan, "去最大1筆平均": np.nan, "勝率": np.nan}
    xs = np.sort(x)
    return {"筆數": n, "中位": float(np.median(x)), "平均": float(x.mean()), "去最大1筆平均": float(xs[:-1].mean()) if n >= 2 else np.nan,
            "勝率": float((x > 0).mean())}


KEYS = ("中位", "平均", "去最大1筆平均", "勝率")


def fixture():
    s = stats([1.0, 2.0, 3.0, 10.0])
    assert s["筆數"] == 4 and s["中位"] == 2.5 and s["平均"] == 4.0 and s["去最大1筆平均"] == 2.0 and s["勝率"] == 1.0
    s = stats([-1.0, 0.0, 2.0])
    assert s["中位"] == 0.0 and abs(s["勝率"] - 1 / 3) < 1e-15 and s["去最大1筆平均"] == -0.5
    s = stats([5.0]); assert np.isnan(s["去最大1筆平均"])
    assert stats([])["筆數"] == 0
    # 合成數字的報酬式（非真實資料）
    amt, out, b0, b1 = 0.1, 0.13, 100.0, 110.0
    r = out / amt - 1 - COST; ex = r - (b1 / b0 - 1)
    assert abs(r - 0.29415) < 1e-12 and abs(ex - 0.19415) < 1e-12
    log("[fixture] stats／報酬式 合成數字驗算 過")


def tshow(path):
    t = subprocess.run(["git", "show", f"{PIN}:{path}"], capture_output=True)
    assert t.returncode == 0, path
    return t.stdout


def load_bench():
    T = pd.read_csv(io.BytesIO(tshow("data/history/market_tri.csv"))); T["date"] = pd.to_datetime(T["date"])
    T = T.dropna().drop_duplicates("date").sort_values("date").set_index("date")["close"]
    from backtest import researchV41EV as V
    sha = subprocess.run(["git", "rev-parse", PIN], capture_output=True, text=True, check=True).stdout.strip()
    Z = V.z50(sha)
    return T, Z


def calendar():
    d = pd.read_csv(os.path.join(YFA, "daily_W.csv.gz"), usecols=["世界", "帳", "t", "日期"])
    d = d[(d["世界"] == "主") & (d["帳"] == "YL")].sort_values("t")
    return d["日期"].fillna("").astype(str).to_numpy()


def attach(E, cal, dry):
    """配對鍵 → R；乾跑只驗鍵、⛔ 不讀 amt_out／cost。"""
    cols = ["世界", "帳", "side", "t", "sid"] + ([] if dry else ["amt", "amt_out", "cost"])
    T = pd.read_csv(os.path.join(YFA, "trades_W.csv.gz"), usecols=cols)
    T = T[T["世界"] == "主"]
    bu = T[T["side"] == "buy"].set_index(["帳", "sid", "t"]); se = T[T["side"] == "sell"].set_index(["帳", "sid", "t"])
    miss = 0; R = []
    for st, sid, tb, ts in zip(E["策略"], E["代號"].astype(int), E["進場t"].astype(int), E["出場t"].astype(int)):
        a = STRAT[st]
        if (a, sid, tb) not in bu.index or (a, sid, ts) not in se.index:
            miss += 1; R.append(np.nan); continue
        if dry:
            R.append(0.0)
        else:
            b = bu.loc[(a, sid, tb)]; s = se.loc[(a, sid, ts)]
            assert abs(float(s["amt"]) - float(b["amt"])) < 1e-12 and abs(float(s["cost"]) - float(b["amt"]) * COST) < 1e-12
            R.append(float(s["amt_out"]) / float(b["amt"]) - 1 - COST)
    assert miss == 0, f"配對鍵缺 {miss}"
    E = E.copy(); E["R"] = R
    E["基準起日"] = [cal[t - 1] for t in E["進場t"].astype(int)]
    return E


def bench_ret(E, T, Z, dry):
    need = sorted(set(E["基準起日"]) | set(E["出場日"]))
    ti, zi = set(T.index.strftime("%Y-%m-%d")), set(Z.index.strftime("%Y-%m-%d"))
    mt, mz = [d for d in need if d not in ti], [d for d in need if d not in zi]
    zfill = {d: str(Z.index[int(Z.index.searchsorted(pd.Timestamp(d), "right")) - 1].date()) for d in mz}
    nz = int(sum((b in zfill) or (e in zfill) for b, e in zip(E["基準起日"], E["出場日"])))
    log(f"[基準] 需要日期 {len(need)}；大盤缺 {len(mt)} {mt[:5]}；0050 缺 {len(mz)} ⇒ 用前一收盤 {zfill}（影響 {nz} 筆）")
    assert not mt and all(zfill[d] < d for d in mz)
    E = E.copy()
    if dry:
        E["大盤"] = 0.0; E["0050"] = 0.0
    else:
        ts = T.copy(); ts.index = ts.index.strftime("%Y-%m-%d")
        zs = Z.copy(); zs.index = zs.index.strftime("%Y-%m-%d")
        E["大盤"] = [ts[e] / ts[b] - 1 for b, e in zip(E["基準起日"], E["出場日"])]
        zv = lambda d: zs[zfill.get(d, d)]   # noqa: E731
        E["0050"] = [zv(e) / zv(b) - 1 for b, e in zip(E["基準起日"], E["出場日"])]
    E["超額_大盤"] = E["R"] - E["大盤"]; E["超額_0050"] = E["R"] - E["0050"]
    return E


def draws(Es, col):
    """F4：回 1,000 組索引（Es 的位置）。"""
    rng = np.random.default_rng(SEED)
    mon = Es["月"].to_numpy(); tag = Es[col].to_numpy(bool)
    groups = []
    for m in sorted(set(mon[tag])):
        ii = np.flatnonzero(mon == m); k = int(tag[ii].sum())
        groups.append((ii, k))
    out = []
    for _ in range(NDRAW):
        out.append(np.concatenate([rng.choice(ii, size=k, replace=False) for ii, k in groups]) if groups else np.array([], int))
    return out, groups


def boot(Es, col, ycol):
    rng = np.random.default_rng(SEED)
    months = np.array(sorted(Es["月"].unique()))
    by = {m: (Es.loc[Es["月"] == m, ycol].to_numpy(float), Es.loc[Es["月"] == m, col].to_numpy(bool)) for m in months}
    dm, dt, skip = [], [], 0
    for _ in range(NBOOT):
        pick = rng.choice(months, size=len(months), replace=True)
        y = np.concatenate([by[m][0] for m in pick]); g = np.concatenate([by[m][1] for m in pick])
        a, b = stats(y[g]), stats(y[~g])
        if a["筆數"] == 0 or b["筆數"] == 0 or np.isnan(a["去最大1筆平均"]) or np.isnan(b["去最大1筆平均"]):
            skip += 1; continue
        dm.append(a["中位"] - b["中位"]); dt.append(a["去最大1筆平均"] - b["去最大1筆平均"])
    q = lambda v: (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))) if v else (np.nan, np.nan)   # noqa: E731
    return {"中位差CI": q(dm), "去最大1筆平均差CI": q(dt), "有效次數": len(dm), "跳過": skip}


FRONT = os.path.join(B, "forward", "frontier")
PERIODS = [  # (期別, 檔, sha16, 家數, 凍結日)
    ("第1期", "period01_main.md", "30e87e3eb701136f", 42, "2026-10-26"),
    ("第1期增補", "period01_supp.md", "db0aab7b8a76ef1f", 7, "2026-10-27"),
]
FWD_SRC = os.path.join(B, "forward", "yl_rule", "positions.csv")
FWD_FROM = "2026-11-01"
FWD_STRAT = {"營量v1": "營量", "營飆v1": "營飆"}


def _codes_main(txt):
    sec = txt.split("## 二、", 1)[1].split("## 三、", 1)[0]
    c = set()
    for ln in sec.splitlines():
        if ln.startswith("|") and not ln.startswith("|---") and "| 組 |" not in ln:
            cells = [x.strip() for x in ln.strip().strip("|").split("|")]
            c |= set(re.findall(r"(?<!\d)(\d{4})(?!\d)", re.sub(r"（[^）]*）", "", cells[2])))
    return c


def _codes_supp(txt):
    sec = txt.split("## 一、", 1)[1].split("## 二、", 1)[0]
    c = set()
    for ln in sec.splitlines():
        if ln.startswith("|") and not ln.startswith("|---") and "| 名次 |" not in ln:
            cells = [x.strip() for x in ln.strip().strip("|").split("|")]
            c |= set(re.findall(r"(?<!\d)(\d{4})(?!\d)", cells[-1]))
    return c


def frontier_lists():
    import hashlib
    L = []
    for name, f, h16, n, fz in PERIODS:
        raw = open(os.path.join(FRONT, f), "rb").read()
        h = hashlib.sha256(raw).hexdigest()[:16]
        txt = raw.decode("utf-8")
        c = _codes_main(txt) if f.endswith("main.md") else _codes_supp(txt)
        log(f"[前瞻名單] {name} {f} sha16 {h}（應 {h16}）、{len(c)} 家（應 {n}）、凍結日 {fz}")
        assert h == h16 and len(c) == n, (name, h, len(c))
        L.append((name, fz, c))
    log(f"[前瞻名單] 聯集 {len(set().union(*[c for _, _, c in L]))} 家")
    return L


def forward_count(P, L, upto=None):
    """P：DataFrame(策略, 代號, 進場日)；回每月一行。只數筆數。"""
    P = P[P["進場日"] >= FWD_FROM]
    if upto:
        P = P[P["進場日"] <= upto]
    rows = []
    for (m, st), g in P.groupby([P["進場日"].str[:7], "策略"]):
        tagged, used = 0, set()
        for sid, d in zip(g["代號"], g["進場日"]):
            ok = [(nm, c) for nm, fz, c in L if fz < d]
            used |= {nm for nm, _ in ok}
            tagged += any(sid in c for _, c in ok)
        rows.append({"月": m, "策略": st, "可用期別": "＋".join(sorted(used)), "主題組": tagged, "全部": len(g)})
    return pd.DataFrame(rows, columns=["月", "策略", "可用期別", "主題組", "全部"])


def forward_fixture(L):
    fake = pd.DataFrame({"策略": ["營量", "營量", "營飆", "營量", "營量"], "代號": ["2330", "4722", "4722", "9999", "2330"],
                         "進場日": ["2026-11-03", "2026-11-04", "2026-12-01", "2026-11-05", "2026-10-28"]})
    F = forward_count(fake, L)
    a = F[(F["月"] == "2026-11") & (F["策略"] == "營量")].iloc[0]
    b = F[(F["月"] == "2026-12") & (F["策略"] == "營飆")].iloc[0]
    assert (a["主題組"], a["全部"], b["主題組"], b["全部"]) == (2, 3, 1, 1) and len(F) == 2
    L2 = [("X", "2026-11-04", {"4722"})]
    assert forward_count(fake.iloc[[1]], L2)["主題組"].tolist() == [0]          # 凍結日當天進場 ⇒ 不可用
    log("[fixture] 前瞻計數 合成資料驗算 過（10/28 進場不入；凍結日當天不可用）")


def forward_part(out):
    L = frontier_lists()
    forward_fixture(L)
    P = pd.read_csv(FWD_SRC, usecols=["策略", "代號", "進場日"], dtype=str, encoding="utf-8-sig")
    P["策略"] = P["策略"].map(FWD_STRAT)
    assert P["策略"].notna().all()
    F = forward_count(P, L)
    F.to_csv(os.path.join(out, "forward.csv"), index=False)
    log(f"[前瞻] 來源 {FWD_SRC}：{len(P)} 筆、進場日 {P['進場日'].min()}～{P['進場日'].max()}；≥{FWD_FROM} 的月數 {F['月'].nunique()}")
    return F, L


def _p(x):
    return "—" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x * 100:+.1f}%"


def summary(mode, dry, sent, S, C, FW, FL, nmiss, nE):
    V = {"寬": "寬鬆", "嚴": "嚴格"}
    L = [f"# 主題標籤能否替營量、營飆加分 seq1｜②普查標籤 描述＋①前瞻骨架｜{mode}", f"<p align=\"right\">{TIME} 起草・回測線計算子代理</p>", ""]
    if dry:
        L += ["> ⚠ 乾跑：R、大盤、0050 全設 0，下表數字全部無意義，只驗流程。", ""]
    else:
        L += ["> 前瞻＋描述、⛔ 不判、⛔ 不計 N（裁定 seq478 §五、seq480 §三）。③盲判標籤已撤（seq480）。",
              "> ⚠ 普查只涵蓋 11 個產業、蒐集有事後偏差；營量、營飆這段歷史本線看過 ⇒ 只描述。寬嚴照標，⛔ 不寫成「保守～樂觀」。", ""]
    L += ["## 一、描述句（登錄 §四；大盤欄）", "", "| 策略 | 版 | 結果 |", "|---|---|---|"]
    for k, x in sent.items():
        st, v = k.split("_")
        L.append(f"| {st} | {V[v]} | {x} |")
    L += ["", f"- 母體 2021-01～2026-09 進場、持有完整或停止交易強制出場 {nE} 筆；未滿（未到、不入分母）{nmiss} 筆。超額 ＝ 還原含息 R（扣 0.585%）− 同期基準。", ""]
    for bn, title in (("大盤", "二、超額對大盤報酬指數（主）"), ("0050", "三、超額對 0050（副欄）")):
        L += [f"## {title}", "", "| 策略 | 版 | 組 | 筆數 | 中位 | 平均 | 去最大 1 筆平均 | 勝率 |", "|---|---|---|---|---|---|---|---|"]
        for _, r in S[S["基準"] == bn].iterrows():
            n = "" if pd.isna(r["筆數"]) else f"{int(r['筆數'])}"
            w = "—" if pd.isna(r["勝率"]) else (f"{r['勝率'] * 100:.0f}%" if not r["組"].startswith("差") else f"{r['勝率'] * 100:+.0f} pp")
            L.append(f"| {r['策略']} | {V[r['版']]} | {r['組']} | {n} | {_p(r['中位'])} | {_p(r['平均'])} | {_p(r['去最大1筆平均'])} | {w} |")
        L.append("")
    L += ["## 四、主題 − 非主題 月群自助法區間（2,000 次，只描述）", "",
          "| 策略 | 版 | 基準 | 中位差 2.5～97.5% | 去最大 1 筆平均差 2.5～97.5% | 有效次數／跳過 | 主題組月群／全部月群 |", "|---|---|---|---|---|---|---|"]
    for _, r in C.iterrows():
        L.append(f"| {r['策略']} | {V[r['版']]} | {r['基準']} | {_p(r['中位差CI_下'])}～{_p(r['中位差CI_上'])} | "
                 f"{_p(r['去最大1筆平均差CI_下'])}～{_p(r['去最大1筆平均差CI_上'])} | {r['有效次數']}／{r['跳過']} | {r['主題組月群']}／{r['月群']} |")
    L += ["", "- 主題組月群遠小於 24（〈四十九〉）⇒ 區間只描述、⛔ 不當推論。", "", "## 五、①前瞻標籤（主）每月筆數", ""]
    L += [f"- 名單：{nm}（凍結日 {fz}，{len(c)} 家）" for nm, fz, c in FL]
    L += [f"- 聯集 {len(set().union(*[c for _, _, c in FL]))} 家；只用進場日前已凍結的期別；來源 backtest/forward/yl_rule/positions.csv（照規則欄），2026-11 起。"]
    if len(FW):
        L += ["", "| 月 | 策略 | 可用期別 | 主題組 | 全部 |", "|---|---|---|---|---|"] + [
            f"| {r['月']} | {r['策略']} | {r['可用期別']} | {r['主題組']} | {r['全部']} |" for _, r in FW.iterrows()]
    else:
        L += ["- **目前 0 個月**（照寫）。⛔ 不附報酬，2027-11-30 滿 12 個月才描述。"]
    L += ["", "## 六、必附", "",
          "- 營飆 ＝ 正式回測抽籤 r0 那一顆；營飆 2022 年 0 筆進場（大盤閘）。",
          "- 0050 在 2025-06-11、06-16 無收盤（分割停牌）⇒ 用 06-10 收盤（★F2）。",
          "- 普查燈 1 最晚 2024-09；8 季回看 ⇒ 2025 起進場被標到的機會逐年縮小。",
          "- ★ 讀法 Q1～Q8（researchThemeTag_freq.py）、F0～F8（researchThemeTag.py）寫於看任何報酬之前。",
          "- stats.csv、ci.csv、rows.csv（每筆）、forward.csv。"]
    return L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--ruling", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    if not a.dry and not re.fullmatch(r"seq\d+", a.ruling or ""):
        print("⛔ 正式跑須帶 --ruling seqNNN（裁定號）；只准 --dry 乾跑。拒跑。", file=sys.stderr)
        return 2
    out = a.out or os.path.join(B, "resultsThemeTag", "dry" if a.dry else "main")
    os.makedirs(out, exist_ok=True)
    t0 = time.time()
    mode = "乾跑（R 全 0）" if a.dry else f"正式（{a.ruling}）"
    log(f"# 主題標籤 seq1 ②普查標籤 描述｜{mode}｜{TIME}｜執行 {time.strftime('%Y-%m-%d %H:%M:%S')}（機器時鐘）")
    ck = json.load(open(os.path.join(FREQ, "check.json"), encoding="utf-8"))
    assert ck.get("全過") is True, "freq 查核未全過"
    fixture()
    cal = calendar()
    E0 = pd.read_csv(os.path.join(FREQ, "entries.csv"), dtype={"代號": str})
    for v in VERS:
        E0[f"標籤_{v}"] = E0[f"標籤_{v}"].astype(bool)
    nmiss = int((E0["持有狀態"] == "未滿").sum())
    E = E0[E0["持有狀態"] != "未滿"].reset_index(drop=True)
    log(f"[母體] entries {len(E0)}；入統計 {len(E)}；未滿（未到）{nmiss}")
    E = attach(E, cal, a.dry)
    T, Z = load_bench()
    E = bench_ret(E, T, Z, a.dry)
    keep = ["策略", "代號", "進場日", "出場日", "持有狀態", "月", "標籤_寬", "標籤_嚴", "R", "大盤", "0050", "超額_大盤", "超額_0050"]
    E[keep].to_csv(os.path.join(out, "rows.csv"), index=False)
    srows, crows, sent = [], [], {}
    for st in STRAT:
        Es = E[E["策略"] == st].reset_index(drop=True)
        for v in VERS:
            col = f"標籤_{v}"
            D, groups = draws(Es, col)
            assert all(len(d) == int(Es[col].sum()) for d in D)
            deg = sum(1 for ii, k in groups if k == len(ii))
            for bn in BENCH:
                y = Es[f"超額_{bn}"].to_numpy(float); g = Es[col].to_numpy(bool)
                th, no = stats(y[g]), stats(y[~g])
                rd = [stats(y[d]) for d in D]
                rm = {k: float(np.nanmedian([r[k] for r in rd])) if D and len(D[0]) else np.nan for k in KEYS}
                rm["筆數"] = int(g.sum())
                for grp, s in (("主題", th), ("非主題", no), ("同月隨機（1000 次中位）", rm)):
                    srows.append({"策略": st, "版": v, "基準": bn, "組": grp, **s})
                srows.append({"策略": st, "版": v, "基準": bn, "組": "差：主題−非主題", "筆數": np.nan, **{k: th[k] - no[k] for k in KEYS}})
                srows.append({"策略": st, "版": v, "基準": bn, "組": "差：主題−隨機", "筆數": np.nan, **{k: th[k] - rm[k] for k in KEYS}})
                ci = boot(Es, col, f"超額_{bn}")
                crows.append({"策略": st, "版": v, "基準": bn, "中位差CI_下": ci["中位差CI"][0], "中位差CI_上": ci["中位差CI"][1],
                              "去最大1筆平均差CI_下": ci["去最大1筆平均差CI"][0], "去最大1筆平均差CI_上": ci["去最大1筆平均差CI"][1],
                              "有效次數": ci["有效次數"], "跳過": ci["跳過"], "月群": int(Es["月"].nunique()), "主題組月群": int(Es.loc[g, "月"].nunique())})
                if bn == "大盤":
                    if th["筆數"] < 30:
                        sent[f"{st}_{v}"] = f"筆數不足、不下描述結論（主題組 {th['筆數']} 筆 ＜ 30）"
                    else:
                        okk = (th["中位"] > no["中位"] and th["中位"] > rm["中位"] and th["去最大1筆平均"] > no["去最大1筆平均"]
                               and th["去最大1筆平均"] > rm["去最大1筆平均"])
                        sent[f"{st}_{v}"] = "成立" if okk else "不成立"
            log(f"[{st}·{v}] 主題 {int(Es[col].sum())}／全部 {len(Es)}；隨機抽樣月 {len(groups)}（k＝n {deg}）；描述句 {sent[f'{st}_{v}']}")
    S = pd.DataFrame(srows); C = pd.DataFrame(crows)
    FW, FL = forward_part(out)
    S.to_csv(os.path.join(out, "stats.csv"), index=False); C.to_csv(os.path.join(out, "ci.csv"), index=False)
    if a.dry:
        num = S[list(KEYS)].to_numpy(float)
        allzero = bool(np.all((num == 0) | np.isnan(num)))
        wz = S.loc[S["組"].isin(["主題", "非主題"]), "勝率"].dropna()
        log(f"[乾跑] 統計量全為 0／空：{allzero}；勝率（＞0）全 0：{bool((wz == 0).all())}；CI 跳過次數 {C['跳過'].tolist()}")
        assert allzero
    meta = {"模式": mode, "時間": TIME, "母體": len(E), "未到": nmiss, "描述句": sent, "種子": SEED, "抽樣次數": NDRAW, "自助次數": NBOOT,
            "大盤": f"data/history/market_tri.csv @ {PIN}", "0050": "researchV41EV.z50 @ " + PIN}
    json.dump(meta, open(os.path.join(out, "run.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    L = summary(mode, a.dry, sent, S, C, FW, FL, nmiss, len(E))
    open(os.path.join(out, "summary.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    log(f"[完成] {time.time() - t0:.1f}s ⇒ {out}")
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
