# -*- coding: utf-8 -*-
"""情報線 H4「大跌期出現的營量型訊號 vs 平常」——用回測線【正式】營量 v1 訊號跑同一格（⛔ 只描述、⛔ 不計 N、⛔ 不判定、⛔ 不是買賣建議）——回測線計算子代理，2026-11-08。
依據：情報線 2026-11-08 06:25 件（回 1107-2318；使用者 11/7「都做」；股癌借鏡第二批 H4）。情報線登錄 claude/prereg_gooaye_batch2_20261107.md H4 段
      （信中原文照抄；⚠ 本機找不到該檔 ⇒ 口徑照信件）；附件 附件-情報線-H4重建營量型訊號-20261108.csv（date, stock, ex, crash, m；2,843 筆）。
⛔ 只計算：不 commit、不 push、不寫跨線信箱（只讀）、不改既有檔（策略鎖內 rerun17／data 只 import；訊號表、世界快取、逐股快取只讀）；用語「假訊號」。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchMktDrop_h4

═══ 口徑（照信件＋委託；寫死於第一次跑之前，2026-11-08 07:20 台北）═══
 H0 正式訊號 ＝ 營量 v1 正式訊號表 backtest/resultsList/and_signals_ext.csv.gz（list_prereg10 build 輸出；list_yl13 營量 v1 名單同一管線，⛔ 不重算）：
    research11 主格 5 取 3 ∧ 同檔 20 根內只取第一個（去重在 5 取 3 層、AND 之前）∧ research13.and_flags（最新一期營收 rev_hi24、距訊號 ≤ 45 個交易日；
    營收面板列本身要求可得日 20 日均量 ≥ 500 張）；資料 edc6f 快照、日曆 2015-01-05～2026-09-24
    ⚠ 主世界營收 2015 起 ⇒ 24 月新高最早 2017-02 才可判 ⇒ 正式訊號實際從 2017-02-10 起（2015-08-24 事件窗內沒有正式訊號）
 H1 大跌事件 ＝ G2 的 19 次：backtest/resultsMktDrop/g2/events.csv 的 18 個事件日（2015 起）＋ 2026-10-15（在快照之後 ⇒ 窗內沒有可算訊號）
    大跌期 ＝ 訊號日在某事件 t0 的 [t0, t0＋20] 個交易日內（世界日曆位置；★ 執行者定：t0＋20 含；兩事件窗不會重疊）；平常 ＝ 其餘全部訊號
 H2 結果 ＝ 訊號隔天開盤進、第 60 根有效 K 棒收盤出（＝ 正式 g_H60／xpos_H60：research11.fixed_exit、進場根算第 1 根、窗內壞根 ⇒ 算不出）
    超額 ＝ g_H60 − 同期 R1 等權平均；R1 ＝ 訊號日 t 的 MktDrop／營量同一流動性母體（v1 逐股快取 mem：四碼普通股 ∧ pit_valid ∧ 含 t 的 20 日都有成交 ∧
    前 20 日均量 ≥ 500 張 ∧ 第 20 根起 ∧ [k−20,k] 無壞根），每檔 ＝ 還原收盤[x]（ffill；下市 ⇒ 最後收盤）÷ 還原開盤[e] − 1，e ＝ 訊號進場日、x ＝ 訊號出場日（同一組日曆位置）；
    ★ 執行者定：成員 e 日沒成交／開盤無效 ⇒ 剔除；成員 (e, x] 有壞根（crashwork bad_main）⇒ 剔除
 H3 期間 ＝ 訊號日 2015-01-05～資料末日、要算得出 60 天（g_H60 有值）；成本：情報版信中沒寫成本 ⇒ 兩邊都不扣（註明）
 H4 去重：照正式（5 取 3 層 20 根去重、AND 之前）；與情報版「同檔 20 日內只取第一次」（AND 之後）不同 ⇒ 註明差異（AND 後同檔間隔必 > 20 根）
 H5 判定格（★ 照情報版重現出來的算法）：主 ＝「月均等權」：大跌期訊號按月取平均、再對月等權平均 − 平常訊號按月取平均、再對月等權平均
    （⭐ 情報附件用此式重算 ＝ −0.2542%，與信中 −0.25% 相符；訊號等權直接相減 ＝ −2.07% 不符）；另報訊號等權差
    CI ＝ 按月分群 bootstrap（月有放回重抽、同月的大跌期／平常一起帶走）10,000 次、種子 default_rng(20261108)；百分位 2.5／97.5
    大跌期所在月數 ＜ 24 ⇒ 還沒測；≥24 時 CI 跨 0 ⇒ 測不出；不跨 0 也只當描述（負也寫「測不出」，⛔ 不寫劣於／反向）；另報中位數（訊號中位差、月均中位差）
 H6 名單重疊：情報（附件 2,843 筆）vs 正式（可算筆）：同 stock＋同 date；另報同 stock 且 |日曆位置差| ≤ 5 交易日；各占自己幾成；大跌期子集（各自的 crash 標）；
    另報共同窗（兩邊最早訊號日的較晚者～兩邊最後訊號日的較早者）
 H7 對帳：同 stock＋同 date 的重疊訊號，正式超額 vs 情報 ex；差 ≤ 0.5 個百分點 ⇒ 一致；不一致列原因：
    隱含情報 R1 ＝ 正式毛報酬 − 情報 ex（假設兩邊毛報酬相同）；(a) 停牌跨日（正式 60 根有效 K 棒 ≠ 60 個日曆交易日；另算日曆 60 日版看是否對上）、
    (b) 同一訊號日各筆的「正式 R1 − 隱含情報 R1」幾乎相同（同日標準差 ≤ 0.2pp）⇒ 差在 R1 母體／口徑；(c) 其他（毛報酬本身不同：價格還原／資料源）
 閘（不過 ⇒ 停）：正式 g_H60 ＝ 世界快取 c[x]/o[e]−1（相對差 ≤ 1e−9）；世界快取 shape ＝ 日曆長度；附件月均等權式重算 ＝ 信中 −0.25%（±0.005pp）
輸出 backtest/resultsMktDrop/h4/：結果.md（另寫）、summary.json、signals_formal.csv（逐筆）、recon_overlap.csv（重疊對帳逐筆）、run.log
"""
from __future__ import annotations

import json
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

REPO = os.path.expanduser("~/tw-p17")
sys.path.insert(0, REPO)
from backtest import rerun17 as RR  # noqa: E402

RR.use_snapshot()
from backtest import data as D  # noqa: E402

OUT = os.path.join(REPO, "backtest/resultsMktDrop/h4")
SIGF = os.path.join(REPO, "backtest/resultsList/and_signals_ext.csv.gz")
G2EV = os.path.join(REPO, "backtest/resultsMktDrop/g2/events.csv")
WORLD = os.path.expanduser("~/rluwork/world_main.pkl")
PACKS = os.path.expanduser("~/mktdropwork/v1/packs_主.pkl")
BAD = os.path.expanduser("~/crashwork/bad_main.pkl")
ADDON = os.path.expanduser("~/addonwork/world_主.pkl")
INTEL = "/mnt/c/SynologyDrive/跨線信箱/附件-情報線-H4重建營量型訊號-20261108.csv"
TIME = "2026-11-08 07:20（台北；口徑寫死、第一次跑之前）"
EXTRA_EVENTS = ["2026-10-15"]
WIN = 20
SEED = 20261108
NBOOT = 10000
TOL_REC = 0.005
TOL_SAMEDAY = 0.002
INTEL_REPORT = {"差": -0.0025, "CI": [-0.0655, 0.0604], "筆數": 2848, "大跌期筆數": 335, "大跌期月數": 27}
LOG = []


def log(s):
    s = f"[{time.strftime('%H:%M:%S')}] {s}"
    print(s, flush=True)
    LOG.append(s)


def crash_flag(pos, ev_pos):
    f = np.zeros(len(pos), bool)
    which = np.full(len(pos), "", object)
    for d, p0 in ev_pos.items():
        m = (pos >= p0) & (pos <= p0 + WIN)
        f |= m
        which[m] = d
    return f, which


def stats(df, rng_seed=SEED, nboot=NBOOT):
    """df: ex, crash, m。回傳主（月均等權差）、訊號等權差、中位、按月分群 bootstrap CI。"""
    g = df.groupby(["m", "crash"])["ex"].mean().unstack()
    for c in (True, False):
        if c not in g.columns:
            g[c] = np.nan
    Mc = g[True].to_numpy(float)
    Mn = g[False].to_numpy(float)
    months = g.index.to_numpy()
    mi = pd.Series(np.arange(len(months)), index=months)
    k = mi[df["m"]].to_numpy()
    cr = df["crash"].to_numpy(bool)
    ex = df["ex"].to_numpy(float)
    S = np.zeros((len(months), 2))
    C = np.zeros((len(months), 2))
    np.add.at(S, (k, cr.astype(int)), ex)
    np.add.at(C, (k, cr.astype(int)), 1)
    has_c = np.isfinite(Mc).any()
    main = (np.nanmean(Mc) - np.nanmean(Mn)) if has_c else np.nan
    sigw = ex[cr].mean() - ex[~cr].mean() if cr.any() else np.nan
    rng = np.random.default_rng(rng_seed)
    n = len(months)
    b1 = np.full(nboot, np.nan)
    b2 = np.full(nboot, np.nan)
    if has_c:
        for i in range(nboot):
            j = rng.integers(0, n, n)
            mc = Mc[j]
            mn = Mn[j]
            if np.isfinite(mc).any():
                b1[i] = np.nanmean(mc) - np.nanmean(mn)
            s = S[j].sum(0)
            c = C[j].sum(0)
            if c[1] > 0:
                b2[i] = s[1] / c[1] - s[0] / c[0]
    pc = lambda b, q: float(np.nanpercentile(b, q)) if np.isfinite(b).any() else None  # noqa: E731
    return {"大跌期筆數": int(cr.sum()), "平常筆數": int((~cr).sum()),
            "大跌期月數": int(np.isfinite(Mc).sum()), "平常月數": int(np.isfinite(Mn).sum()),
            "大跌期_月均等權平均": float(np.nanmean(Mc)) if has_c else None, "平常_月均等權平均": float(np.nanmean(Mn)),
            "主_月均等權差": float(main), "主_CI95": [pc(b1, 2.5), pc(b1, 97.5)],
            "大跌期_訊號平均": float(ex[cr].mean()) if cr.any() else None, "平常_訊號平均": float(ex[~cr].mean()),
            "訊號等權差": float(sigw), "訊號等權差_CI95": [pc(b2, 2.5), pc(b2, 97.5)],
            "大跌期_訊號中位": float(np.median(ex[cr])) if cr.any() else None, "平常_訊號中位": float(np.median(ex[~cr])),
            "訊號中位差": float(np.median(ex[cr]) - np.median(ex[~cr])) if cr.any() else None,
            "月均中位差": float(np.nanmedian(Mc) - np.nanmedian(Mn)) if has_c else None,
            "bootstrap 抽到沒有大跌月的次數": int(np.isnan(b1).sum())}


def verdict(s):
    if s["大跌期月數"] < 24:
        return f"還沒測（大跌期所在月數 {s['大跌期月數']} ＜ 24）"
    lo, hi = s["主_CI95"]
    return "測不出（CI 跨 0）" if lo <= 0 <= hi else "測不出（CI 不跨 0，但只當描述、不判定）"


def overlap(Fx, Ix, pos_of):
    fk = set(zip(Fx["sid"], Fx["date"]))
    ik = set(zip(Ix["stock"], Ix["date"]))
    ex_ = fk & ik
    fpos, ipos = {}, {}
    for s_, p_ in zip(Fx["sid"], Fx["pos"]):
        fpos.setdefault(s_, []).append(int(p_))
    ip = [(s_, pos_of.get(d_)) for s_, d_ in zip(Ix["stock"], Ix["date"])]
    for s_, p_ in ip:
        if p_ is not None:
            ipos.setdefault(s_, []).append(int(p_))

    def near(s_, p_, other):
        return any(abs(p_ - q) <= 5 for q in other.get(s_, ()))
    fn = sum(near(s_, int(p_), ipos) for s_, p_ in zip(Fx["sid"], Fx["pos"]))
    inn = sum(near(s_, p_, fpos) for s_, p_ in ip if p_ is not None)
    nf, ni = len(Fx), len(Ix)
    return {"正式筆": nf, "情報筆": ni, "同日同股": len(ex_),
            "同日同股_占正式": len(ex_) / nf if nf else None, "同日同股_占情報": len(ex_) / ni if ni else None,
            "±5日_正式有對到": int(fn), "±5日_占正式": fn / nf if nf else None,
            "±5日_情報有對到": int(inn), "±5日_占情報": inn / ni if ni else None}


def main():
    T0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    S = {"口徑寫死": TIME, "開跑（台北）": time.strftime("%Y-%m-%d %H:%M"), "依據": "情報線 2026-11-08 06:25 件 H4；口徑見程式檔頭 H0～H7", "閘": {}}
    cal = D.load_calendar()
    n = len(cal)
    dates = np.array([str(d.date()) for d in cal])
    pos_of = {d: i for i, d in enumerate(dates)}
    log(f"[日曆] {dates[0]}～{dates[-1]}｜{n}")
    # ── 世界快取 ──
    W = pickle.load(open(WORLD, "rb"))
    if W["c"].shape[1] != n:
        raise SystemExit("⛔ 世界快取日曆長度不同")
    sids = W["sids"]
    rix = {s: i for i, s in enumerate(sids)}
    Cm, Om, TRD = W["c"], W["o"], W["trd"]
    # ── 正式訊號 ──
    A = pd.read_csv(SIGF, dtype={"sid": str})
    A["date"] = dates[A["pos"].to_numpy()]
    S["正式訊號表"] = {"列": int(len(A)), "最早": A["date"].min(), "最晚": A["date"].max(), "g_H60 缺": int(A["g_H60"].isna().sum())}
    Wa = pickle.load(open(ADDON, "rb"))
    ref = Wa["SIG"][False]
    w0, w1 = Wa["w0"], Wa["w1"]
    sa = set(zip(ref["sid"], ref["pos"].astype(int)))
    mine = A[(A["entry_pos"] >= w0) & (A["entry_pos"] <= w1)]
    sb = set(zip(mine["sid"], mine["pos"].astype(int)))
    kk = "正式訊號表 vs addonwork 營量 AND（進場在窗內 2017-03-02～2026-08-24）"
    S["閘"][kk] = {"addonwork": len(sa), "本表": len(sb), "交集": len(sa & sb)}
    del Wa
    log(f"[正式] {S['正式訊號表']}｜{S['閘'][kk]}")
    # 去重差異：AND 後同檔間隔
    A2 = A.sort_values(["sid", "pos"])
    gap = A2.groupby("sid")["k"].diff()
    S["去重"] = {"AND 後同檔前後兩筆間隔（有效 K 棒）最小": float(gap.min()), "間隔 ≤ 20 根的筆數": int((gap <= 20).sum())}
    F = A[A["g_H60"].notna() & (A["date"] >= "2015-01-05")].copy()
    F["xpos"] = F["xpos_H60"].astype(int)
    F["e"] = F["entry_pos"].astype(int)
    rr_ = F["sid"].map(rix)
    inw = rr_.notna().to_numpy()
    S["閘"]["訊號股不在世界快取（四碼普通股閘外；g_H60 照正式表、不做價格閘）"] = {"筆": int((~inw).sum()), "股": sorted(F.loc[~inw, "sid"].unique())}
    r = rr_.fillna(0).astype(int).to_numpy()
    g = Cm[r, F["xpos"].to_numpy()] / Om[r, F["e"].to_numpy()] - 1
    dg = float(np.nanmax(np.abs(g[inw] / F["g_H60"].to_numpy()[inw] - 1))) if inw.any() else 0.0
    S["閘"]["g_H60 vs 世界快取 c[x]/o[e]−1 最大相對差"] = dg
    log(f"[閘] g_H60 vs 快取 最大相對差 {dg:.2e}｜不在快取 {int((~inw).sum())} 筆")
    if not dg <= 1e-9:
        raise SystemExit("⛔ g_H60 對不上世界快取")
    xc = F["e"].to_numpy() + 59
    F["g_cal60"] = np.where((xc < n) & inw, Cm[r, np.minimum(xc, n - 1)] / Om[r, F["e"].to_numpy()] - 1, np.nan)
    F["跨停牌"] = (F["xpos"] - F["e"]) != 59
    # ── R1 ──
    PK = pickle.load(open(PACKS, "rb"))
    MEM = np.zeros((len(sids), n), bool)
    miss = 0
    for s, pk in PK.items():
        if s not in rix:
            miss += 1
            continue
        MEM[rix[s], pk["idx"][pk["mem"]]] = True
    del PK
    BADD = pickle.load(open(BAD, "rb"))
    BADM = np.zeros((len(sids), n), bool)
    for s, v in BADD.items():
        if s in rix:
            for arr in v:
                arr = np.asarray(arr, int)
                arr = arr[(arr >= 0) & (arr < n)]
                BADM[rix[s], arr] = True
    CB = np.concatenate([np.zeros((len(sids), 1), np.int32), np.cumsum(BADM, 1, dtype=np.int32)], 1)
    S["閘"]["R1"] = {"逐股快取股不在世界快取": miss, "母體股日": int(MEM.sum()), "壞根股日": int(BADM.sum())}
    cache = {}
    r1 = np.full(len(F), np.nan)
    r1n = np.zeros(len(F), int)
    r1all = np.zeros(len(F), int)
    for i, (t, e, x) in enumerate(zip(F["pos"].to_numpy(), F["e"].to_numpy(), F["xpos"].to_numpy())):
        key = (int(t), int(e), int(x))
        if key not in cache:
            rows = np.flatnonzero(MEM[:, t])
            ok = TRD[rows, e] & np.isfinite(Om[rows, e]) & (Om[rows, e] > 0) & ((CB[rows, x + 1] - CB[rows, e + 1]) == 0) & np.isfinite(Cm[rows, x])
            rr = rows[ok]
            v = Cm[rr, x] / Om[rr, e] - 1
            cache[key] = (float(v.mean()) if len(v) else np.nan, len(v), int(len(rows)))
        r1[i], r1n[i], r1all[i] = cache[key]
    F["R1"] = r1
    F["R1_檔數"] = r1n
    F["R1_母體檔數"] = r1all
    S["R1"] = {"每筆 R1 檔數中位": float(np.median(r1n)), "最少": int(r1n.min()), "剔除比例中位（開盤無效／持有中壞根）": float(np.median(1 - r1n / np.maximum(r1all, 1)))}
    F = F[np.isfinite(F["R1"])].copy()
    F["ex"] = F["g_H60"] - F["R1"]
    F["m"] = F["date"].str[:7]
    # ── 事件 ──
    EV = pd.read_csv(G2EV)
    evd = list(EV["事件日"].astype(str)) + EXTRA_EVENTS
    ev_pos = {d: pos_of[d] for d in evd if d in pos_of}
    S["事件"] = {"G2 事件數": len(evd), "在快照日曆內": len(ev_pos), "快照日曆外（窗內無可算訊號）": [d for d in evd if d not in pos_of],
                 "窗": {d: f"{dates[p]}～{dates[min(p + WIN, n - 1)]}" for d, p in ev_pos.items()}}
    F["crash"], F["事件"] = crash_flag(F["pos"].to_numpy(), ev_pos)
    S["事件窗內正式訊號"] = {d: int((F["事件"] == d).sum()) for d in evd}
    # ── 判定格 ──
    st = stats(F[["ex", "crash", "m"]])
    st["判語"] = verdict(st)
    S["正式版"] = {"可算筆數": int(len(F)), "最早": F["date"].min(), "最晚": F["date"].max(), **st}
    log(f"[正式版] {S['正式版']}")
    # ── 情報版重現 ──
    I = pd.read_csv(INTEL, dtype={"stock": str})
    I["crash"] = I["crash"].astype(str).str.lower().eq("true")
    sti = stats(I[["ex", "crash", "m"]])
    sti["判語"] = verdict(sti)
    S["情報附件重算（同程式）"] = {"筆數": int(len(I)), "最早": I["date"].min(), "最晚": I["date"].max(), **sti}
    S["情報信中數字"] = INTEL_REPORT
    if abs(sti["主_月均等權差"] - INTEL_REPORT["差"]) > 0.00005:
        raise SystemExit(f"⛔ 附件重算 {sti['主_月均等權差']} ≠ 信中 −0.25%")
    ipos = I["date"].map(pos_of)
    S["閘"]["附件日期對不到快照日曆"] = int(ipos.isna().sum())
    Ii = I[ipos.notna()].copy()
    Ii["pos"] = ipos[ipos.notna()].astype(int)
    myc, _ = crash_flag(Ii["pos"].to_numpy(), ev_pos)
    icr = Ii["crash"].to_numpy()
    S["情報 crash 標 vs 本程式 [t0,t0+20]（附件日期在快照日曆內者）"] = {"筆": int(len(Ii)), "一致": int((myc == icr).sum()),
                                                                   "情報是本程式否": int((icr & ~myc).sum()), "本程式是情報否": int((~icr & myc).sum()),
                                                                   "不一致日期": sorted(set(Ii.loc[myc != icr, "date"]))[:30]}
    # ── 共同窗 ──
    c0 = max(F["date"].min(), I["date"].min())
    c1 = min(F["date"].max(), I["date"].max())
    Fc = F[(F["date"] >= c0) & (F["date"] <= c1)]
    Ic = I[(I["date"] >= c0) & (I["date"] <= c1)]
    S["共同窗"] = {"窗": f"{c0}～{c1}", "正式": stats(Fc[["ex", "crash", "m"]]), "情報": stats(Ic[["ex", "crash", "m"]])}
    for k in ("正式", "情報"):
        S["共同窗"][k]["判語"] = verdict(S["共同窗"][k])
    # ── 重疊 ──
    S["重疊"] = {"全部": overlap(F, I, pos_of), "大跌期（各自 crash 標）": overlap(F[F["crash"]], I[I["crash"]], pos_of),
                 "共同窗": overlap(Fc, Ic, pos_of), "共同窗大跌期": overlap(Fc[Fc["crash"]], Ic[Ic["crash"]], pos_of)}
    # ── 對帳 ──
    R = F.merge(I[["stock", "date", "ex", "crash"]].rename(columns={"stock": "sid", "ex": "ex_情報", "crash": "crash_情報"}), on=["sid", "date"])
    R["差"] = R["ex"] - R["ex_情報"]
    R["隱含情報R1"] = R["g_H60"] - R["ex_情報"]
    R["R1差"] = R["R1"] - R["隱含情報R1"]
    R["日曆60版超額"] = R["g_cal60"] - R["R1"]
    sd = R.groupby("date")["R1差"].transform(lambda s_: s_.std() if len(s_) > 1 else np.nan)
    R["同日R1差標準差"] = sd

    def reason(x):
        if abs(x["差"]) <= TOL_REC:
            return "一致"
        if x["跨停牌"]:
            return "(a) 停牌跨日（60 根有效 K 棒 ≠ 60 個日曆交易日）"
        if np.isfinite(x["同日R1差標準差"]) and x["同日R1差標準差"] <= TOL_SAMEDAY:
            return "(b) R1 母體／口徑差（同日各筆差相同）"
        return "(c) 其他（毛報酬不同或同日只 1 筆無法分辨）"
    R["原因"] = R.apply(reason, axis=1)
    S["對帳"] = {"重疊筆": int(len(R)), "一致（|差|≤0.5pp）": int((R["原因"] == "一致").sum()),
                 "差_平均": float(R["差"].mean()), "差_中位": float(R["差"].median()), "|差|_中位": float(R["差"].abs().median()),
                 "|差|≤1pp": int((R["差"].abs() <= 0.01).sum()), "|差|>5pp": int((R["差"].abs() > 0.05).sum()),
                 "相關係數": float(np.corrcoef(R["ex"], R["ex_情報"])[0, 1]) if len(R) > 2 else None,
                 "原因分布": R["原因"].value_counts().to_dict(),
                 "R1差（正式 R1 − 隱含情報 R1）_中位": float(R["R1差"].median()), "R1差_平均": float(R["R1差"].mean()),
                 "同日多筆者_同日R1差標準差中位": float(np.nanmedian(R["同日R1差標準差"])) if R["同日R1差標準差"].notna().any() else None,
                 "crash 標一致": int((R["crash"] == R["crash_情報"]).sum())}
    cs = R[R["跨停牌"]]
    S["對帳"]["跨停牌者"] = {"筆": int(len(cs)), "正式版一致": int((cs["差"].abs() <= TOL_REC).sum()),
                         "改日曆 60 日後一致": int(((cs["日曆60版超額"] - cs["ex_情報"]).abs() <= TOL_REC).sum())}
    # 判定格拆解（描述）：重疊子集（兩邊超額各自）、只在正式、只在情報（共同窗）
    rk = set(zip(R["sid"], R["date"]))
    fo = F[[(s_, d_) not in rk for s_, d_ in zip(F["sid"], F["date"])]]
    io = Ic[[(s_, d_) not in rk for s_, d_ in zip(Ic["stock"], Ic["date"])]]
    S["判定格拆解（描述）"] = {
        "重疊_正式超額": stats(R[["ex", "crash", "m"]]),
        "重疊_情報ex": stats(R[["ex_情報", "crash", "m"]].rename(columns={"ex_情報": "ex"})),
        "只在正式": stats(fo[["ex", "crash", "m"]]),
        "只在情報（共同窗）": stats(io[["ex", "crash", "m"]])}
    # 年別差
    R["年"] = R["date"].str[:4]
    S["對帳"]["年別_差中位"] = R.groupby("年")["差"].median().round(5).to_dict()
    S["對帳"]["年別_R1差中位"] = R.groupby("年")["R1差"].median().round(5).to_dict()
    # ── 輸出 ──
    cols = ["date", "sid", "pos", "e", "xpos", "g_H60", "R1", "R1_檔數", "ex", "crash", "事件", "m", "跨停牌", "relvol"]
    Fo = F[cols].copy()
    Fo["entry_date"] = dates[Fo["e"].to_numpy()]
    Fo["exit_date"] = dates[Fo["xpos"].to_numpy()]
    Fo.to_csv(os.path.join(OUT, "signals_formal.csv"), index=False, encoding="utf-8")
    R[["date", "sid", "g_H60", "R1", "ex", "ex_情報", "差", "隱含情報R1", "R1差", "同日R1差標準差", "跨停牌", "g_cal60", "日曆60版超額",
       "crash", "crash_情報", "原因"]].to_csv(os.path.join(OUT, "recon_overlap.csv"), index=False, encoding="utf-8")
    S["耗時秒"] = round(time.time() - T0, 1)
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(json.dumps({k: S[k] for k in ("去重", "R1", "事件窗內正式訊號", "共同窗", "重疊", "對帳",
                                       "情報 crash 標 vs 本程式 [t0,t0+20]（附件日期在快照日曆內者）")}, ensure_ascii=False, default=str))
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
