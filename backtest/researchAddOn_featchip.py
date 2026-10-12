# -*- coding: utf-8 -*-
"""漲多加碼：加碼那一份會賺／會賠，加碼當下的【籌碼】特徵分不分得出來——描述性特徵掃描（使用者 2026-10-13 追問：「大戶、外資籌碼呢？」）
——回測線計算子代理。⛔ 只計算：不 commit、不改既有程式與結果夾；描述性、⛔ 不計 N、⛔ 不判定；用語「假訊號」；⛔ 不給買賣建議。
⚠ 加碼已看過結果（researchAddOn、truetop、exit5、feat）⇒ 本件全是事後描述，任何「看起來有差」都只是待驗的線索。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchAddOn_featchip

═══ 讀法（C 標）═══
 C0 樣本 ＝ researchAddOn_feat 的逐筆檔 resultsAddOn/feat/feat_rows.csv.gz（去重 400 筆：探索 116、確認 102、早年 182；賺 ＝ 淨報酬 ＞ 0）——⛔ 不重抽樣本
    早年世界（2004～2014、早年版面）沒有法人、融資、集保 ⇒ 籌碼特徵全標缺，只做主世界（探索 2017～2021、確認 2022～）
 C1 資料（~/tw-p17/data，本機 repo 現況）與可得時點（⛔ 只用決策日 t 收盤時已公布者；t ＝ 加碼前一根，日期 ＝ 主世界日曆 cal[t]）：
    三大法人 stocks_inst/<代號>.csv（股；foreign ＝ 外資及陸資【含】外資自營商；dealer ＝ 自營商合計；total ＝ 三大合計）：當日盤後公布 ⇒ 用到 t 當天（含）
    成交量 stocks/<代號>.csv volume（股；未還原；同期法人買賣超也是股 ⇒ 比值口徑一致）；該股該日無列 ⇒ 量 0、法人 0
    融資融券 stocks_margin/<代號>.csv（張；m_balance 融資餘額、m_limit 融資限額、s_balance 融券餘額）：當日盤後公布 ⇒ 用到 t 當天（含）；t 當天無列 ⇒ 缺
    集保股權分散 tdcc_hist/<年>.parquet ＋ tdcc/<日期>.csv（週；資料日期 D ＝ 該週最後營業日，官方週六 09:00 後產生〔tdcc.py 文件〕）
      ⇒ 決策日 t 只用 D ＜ cal[t]（⛔ D ＝ t 當天那週不用）的最新一週（同 surge_features.tdcc_feature）；最新一週 D 距 cal[t] ＞ 17 天 ⇒ 缺（避免用過期週）
      ⚠ 歷史不連續：2017 只有 1 週（07-21）、2018 只有 11-02 起 9 週、2019 自 06-28 起連續 ⇒ 探索段集保特徵大多只有 2019 下半年起的加碼有值（照報有值筆數）
      比例自算 ＝ 該級距股數 ÷ 第 17 級（合計）股數 × 100（2017～2018 官方 pct 欄全空；2019 起與官方 pct 對帳，照報最大差）
      級距（data/meta/tdcc_level.csv 的 low_shares／high_shares）：＞400 張 ＝ 第 12～15 級；＞1000 張 ＝ 第 15 級；≤10 張 ＝ 第 1～3 級；≤50 張 ＝ 第 1～8 級；總股東 ＝ 第 17 級人數
      1 週變化 ＝ 最新週 − 前一筆（日期差 4～10 天，否則缺）；4 週變化 ＝ 最新週 − 日期落在 [D−35, D−21] 天、最接近 D−28 的那一週（沒有 ⇒ 缺）
    外資持股比例：⛔ 我方資料庫沒有（掃過 data/ 下 stocks_inst、universe/inst、otcinst、meta、docs/READ_CONTRACT.md：無 MI_QFIIS 類外資持股欄）
      ⇒ 改報代理「外資近 20 日買賣超 ÷ 集保總股數」（≈ 外資持股比例 20 日變化；分母 ＝ 上一條可得的最新週第 17 級股數）並標明是代理
 C2 特徵（各自報；窗 ＝ 主世界日曆的交易日，含 t）：見 CHIP；另並列上一份 lu20（近 20 日漲停天數）看重疊
 C3 方法同 researchAddOn_feat F2、F3：連續 ＝ 探索段三分位（⛔ 切點只用探索段）、二元 ＝ 兩組；探索段差 ＝ 筆數 ≥ 10 的組中 最高 − 最低賺錢比例；
    確認段同兩組同方向、確認段單邊打亂 p（方向 ＝ 探索段高組 ＞ 低組；⛔ 不重切；每個特徵都報）；單變數 AUC（值大 ⇒ 會賺 ⇒ ＞ 0.5）；
    族系多重比較：探索段賺／賠標籤打亂 2000 次（同一組打亂同時套到全部特徵）⇒ 每特徵打亂 p、族系 p（打亂下全部籌碼特徵最大差 ≥ 該特徵差）；
    另報「籌碼 ＋ 上一份 19 個」合併族系（上一份的分組用同法自 feat_rows 重建，並對帳 feat.json 的探索差）
 C4 重疊：每個籌碼特徵與 lu20 的 Spearman ρ（探索、確認）；前 5 名籌碼特徵在「lu20 ≤ 4」子樣本內的同兩組差（探索、確認）、高組中 lu20 ＞ 4 的占比
輸出 backtest/resultsAddOn/feat_chip/：featchip.json、featchip_table.csv、featchip_rows.csv.gz（逐筆籌碼特徵，供查核）
"""
from __future__ import annotations

import glob
import json
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchAddOn_feat as AF                # noqa: E402  （auc、make_bins、FEAT；只 import，不改）

OUT = "backtest/resultsAddOn/feat_chip"
FEAT_DIR = "backtest/resultsAddOn/feat"
WORK = os.path.expanduser("~/addonwork")
DATA = "data"
NPERM = 2000
MINGRP = 10
SEED = 20261013 + 1
SEGM = ("探索", "確認")
SEGN = ("探索", "確認", "早年")
STALE = 17

CHIP = [("f5", "外資 近 5 日買賣超 ÷ 同期成交量", "c"), ("f20", "外資 近 20 日買賣超 ÷ 同期成交量", "c"),
        ("fd20", "外資 近 20 日買超天數", "c"), ("fh20", "外資近 20 日買賣超 ÷ 集保總股數（外資持股比例 20 日變化的代理）", "c"),
        ("t5", "投信 近 5 日買賣超 ÷ 同期成交量", "c"), ("t20", "投信 近 20 日買賣超 ÷ 同期成交量", "c"),
        ("tfirst", "投信首買（近 5 日有買超、其前 20 日無買超）", "b"),
        ("d5", "自營商 近 5 日買賣超 ÷ 同期成交量", "c"), ("a5", "三大法人合計 近 5 日買賣超 ÷ 同期成交量", "c"),
        ("b400", "集保 ＞400 張持股比例（最新週）", "c"), ("b400w1", "集保 ＞400 張比例 1 週變化", "c"), ("b400w4", "集保 ＞400 張比例 4 週變化", "c"),
        ("b1000", "集保 ＞1000 張持股比例（最新週）", "c"), ("b1000w1", "集保 ＞1000 張比例 1 週變化", "c"), ("b1000w4", "集保 ＞1000 張比例 4 週變化", "c"),
        ("r10w4", "集保 ≤10 張持股比例 4 週變化", "c"), ("r50w4", "集保 ≤50 張持股比例 4 週變化", "c"),
        ("r50p4", "集保 ≤50 張人數 4 週變化率", "c"), ("hold4", "集保 總股東人數 4 週變化率", "c"),
        ("m5", "融資餘額 近 5 日變化率", "c"), ("m20", "融資餘額 近 20 日變化率", "c"), ("muse", "融資使用率（餘額 ÷ 限額）", "c"),
        ("s5", "融券餘額 近 5 日變化 ÷ 同期成交量（張）", "c"), ("s20", "融券餘額 近 20 日變化 ÷ 同期成交量（張）", "c"),
        ("sm", "券資比（融券餘額 ÷ 融資餘額）", "c")]
GROUPS = {"外資": ["f5", "f20", "fd20", "fh20"], "投信": ["t5", "t20", "tfirst"], "自營、合計": ["d5", "a5"],
          "集保大戶": ["b400", "b400w1", "b400w4", "b1000", "b1000w1", "b1000w4"], "集保散戶、股東數": ["r10w4", "r50w4", "r50p4", "hold4"],
          "融資券": ["m5", "m20", "muse", "s5", "s20", "sm"]}


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def jdump(o, p):
    json.dump(o, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=lambda z: (None if (isinstance(z, float) and not np.isfinite(z)) else (z.item() if hasattr(z, "item") else str(z))))


# ═════════════ 集保 ═════════════
def load_tdcc(sids):
    lv = pd.read_csv(os.path.join(DATA, "meta", "tdcc_level.csv"))
    lvd = {int(r.level): (int(r.low_shares) if pd.notna(r.low_shares) else None, int(r.high_shares) if pd.notna(r.high_shares) else None) for r in lv.itertuples()}
    # 級距對照（⛔ 不憑印象：從 tdcc_level.csv 讀下限／上限決定）
    L400 = [k for k, (lo, hi) in lvd.items() if k <= 15 and lo is not None and lo >= 400_001]
    L1000 = [k for k, (lo, hi) in lvd.items() if k <= 15 and lo is not None and lo >= 1_000_001]
    R10 = [k for k, (lo, hi) in lvd.items() if k <= 15 and hi is not None and hi <= 10_000]
    R50 = [k for k, (lo, hi) in lvd.items() if k <= 15 and hi is not None and hi <= 50_000]
    assert L400 == [12, 13, 14, 15] and L1000 == [15] and R10 == [1, 2, 3] and R50 == list(range(1, 9)), (L400, L1000, R10, R50)
    parts = []
    for f in sorted(glob.glob(os.path.join(DATA, "tdcc_hist", "*.parquet"))):
        x = pd.read_parquet(f, columns=["date", "stock_id", "level", "people", "shares", "pct"])
        x["stock_id"] = x["stock_id"].astype(str); x = x[x["stock_id"].isin(sids)]
        x["date"] = pd.to_datetime(x["date"].astype(str)); parts.append(x)
    for f in sorted(glob.glob(os.path.join(DATA, "tdcc", "*.csv"))):
        x = pd.read_csv(f, dtype={"stock_id": str}); x = x[x["stock_id"].isin(sids)]
        x["date"] = pd.to_datetime(x["date"]); parts.append(x[["date", "stock_id", "level", "people", "shares", "pct"]])
    A = pd.concat(parts, ignore_index=True); A["level"] = A["level"].astype(int)
    A = A.drop_duplicates(["date", "stock_id", "level"], keep="last")
    sh = A.pivot_table(index=["stock_id", "date"], columns="level", values="shares", aggfunc="first")
    pp = A.pivot_table(index=["stock_id", "date"], columns="level", values="people", aggfunc="first")
    pc = A.pivot_table(index=["stock_id", "date"], columns="level", values="pct", aggfunc="first")
    tot = sh[17].astype(float)
    Wk = pd.DataFrame(index=sh.index)
    Wk["tot_sh"] = tot
    Wk["b400"] = sh[L400].sum(1) / tot * 100; Wk["b1000"] = sh[L1000].sum(1) / tot * 100
    Wk["r10"] = sh[R10].sum(1) / tot * 100; Wk["r50"] = sh[R50].sum(1) / tot * 100
    Wk["r50p"] = pp[R50].sum(1).astype(float); Wk["hold"] = pp[17].astype(float)
    Wk = Wk[np.isfinite(Wk["tot_sh"]) & (Wk["tot_sh"] > 0)]
    # 對帳：自算 ＞400 張比例 vs 官方 pct 加總（2019 起官方有值）
    off = pc[L400].sum(1, min_count=len(L400)); j = off.index.intersection(Wk.index)
    dif = (Wk.loc[j, "b400"] - off.loc[j]).abs(); dif = dif[np.isfinite(dif)]
    info = {"級距": {"＞400 張": L400, "＞1000 張": L1000, "≤10 張": R10, "≤50 張": R50},
            "樣本股 週列": int(len(Wk)), "樣本股數": int(Wk.index.get_level_values(0).nunique()),
            "自算 ＞400 張比例 vs 官方 pct 加總：對到列、最大絕對差、p99": [int(len(dif)), float(dif.max()) if len(dif) else None, float(dif.quantile(.99)) if len(dif) else None]}
    by = {}
    for s, g in Wk.groupby(level=0):
        g = g.droplevel(0).sort_index()
        by[s] = (g.index.to_numpy(), {c: g[c].to_numpy(float) for c in g.columns})
    alld = sorted(set(A["date"]))
    info["週資料日期：全部週數、首、尾"] = [len(alld), str(alld[0].date()), str(alld[-1].date())]
    yc = pd.Series([d.year for d in alld]).value_counts().sort_index()
    info["每年週數"] = {int(k): int(v) for k, v in yc.items()}
    return by, info


def tdcc_at(by, sid, day):
    """day ＝ cal[t]；回 dict（缺 ⇒ 全 NaN）。"""
    o = {k: np.nan for k in ("b400", "b400w1", "b400w4", "b1000", "b1000w1", "b1000w4", "r10w4", "r50w4", "r50p4", "hold4", "tot_sh", "D")}
    if sid not in by:
        return o
    ds, V = by[sid]
    j = int(np.searchsorted(ds, np.datetime64(day), side="left")) - 1          # D ＜ day
    if j < 0:
        return o
    D = pd.Timestamp(ds[j])
    if (pd.Timestamp(day) - D).days > STALE:
        return o
    o["D"] = D; o["tot_sh"] = V["tot_sh"][j]; o["b400"] = V["b400"][j]; o["b1000"] = V["b1000"][j]
    if j >= 1 and 4 <= (D - pd.Timestamp(ds[j - 1])).days <= 10:
        o["b400w1"] = V["b400"][j] - V["b400"][j - 1]; o["b1000w1"] = V["b1000"][j] - V["b1000"][j - 1]
    cand = [k for k in range(max(0, j - 8), j) if 21 <= (D - pd.Timestamp(ds[k])).days <= 35]
    if cand:
        k = min(cand, key=lambda k: abs((D - pd.Timestamp(ds[k])).days - 28))
        o["b400w4"] = V["b400"][j] - V["b400"][k]; o["b1000w4"] = V["b1000"][j] - V["b1000"][k]
        o["r10w4"] = V["r10"][j] - V["r10"][k]; o["r50w4"] = V["r50"][j] - V["r50"][k]
        o["r50p4"] = V["r50p"][j] / V["r50p"][k] - 1 if V["r50p"][k] > 0 else np.nan
        o["hold4"] = V["hold"][j] / V["hold"][k] - 1 if V["hold"][k] > 0 else np.nan
    return o


# ═════════════ 逐筆特徵 ═════════════
def features(U, cal):
    sids = sorted(U.loc[U["世界"] == "主", "sid"].unique())
    by, tinfo = load_tdcc(set(sids))
    log(f"[集保] {tinfo}")
    cs = pd.DatetimeIndex(cal); cstr = cs.strftime("%Y-%m-%d")
    INST, VOL, MG = {}, {}, {}
    finfo = {"無法人檔": [], "無價量檔": [], "無融資券檔": []}
    for s in sids:
        p = os.path.join(DATA, "stocks_inst", s + ".csv")
        if os.path.exists(p):
            x = pd.read_csv(p, dtype={"date": str, "stock_id": str}).drop_duplicates("date", keep="last").set_index("date")
            INST[s] = {c: pd.to_numeric(x[c], errors="coerce").reindex(cstr).fillna(0.0).to_numpy() for c in ("foreign", "trust", "dealer", "total")}
        else:
            finfo["無法人檔"].append(s)
        p = os.path.join(DATA, "stocks", s + ".csv")
        if os.path.exists(p):
            x = pd.read_csv(p, dtype={"date": str, "stock_id": str}, usecols=["date", "volume"]).drop_duplicates("date", keep="last").set_index("date")
            VOL[s] = pd.to_numeric(x["volume"], errors="coerce").reindex(cstr).fillna(0.0).to_numpy()
        else:
            finfo["無價量檔"].append(s)
        p = os.path.join(DATA, "stocks_margin", s + ".csv")
        if os.path.exists(p):
            x = pd.read_csv(p, dtype={"date": str, "stock_id": str}, usecols=["date", "m_balance", "m_limit", "s_balance"]).drop_duplicates("date", keep="last").set_index("date")
            MG[s] = {c: pd.to_numeric(x[c], errors="coerce").reindex(cstr).to_numpy() for c in ("m_balance", "m_limit", "s_balance")}
        else:
            finfo["無融資券檔"].append(s)
    n_ = len(U); F = {k: np.full(n_, np.nan) for k, _, _ in CHIP}; DD = [None] * n_
    for i, r in enumerate(U.to_dict("records")):
        if r["世界"] != "主":
            continue
        s, t = r["sid"], int(r["t"])
        if s in INST and s in VOL and t >= 44:
            v = VOL[s]; I = INST[s]
            v5, v20 = v[t - 4:t + 1].sum(), v[t - 19:t + 1].sum()
            fo, tr, de, to = I["foreign"], I["trust"], I["dealer"], I["total"]
            if v5 > 0:
                F["f5"][i] = fo[t - 4:t + 1].sum() / v5; F["t5"][i] = tr[t - 4:t + 1].sum() / v5
                F["d5"][i] = de[t - 4:t + 1].sum() / v5; F["a5"][i] = to[t - 4:t + 1].sum() / v5
            if v20 > 0:
                F["f20"][i] = fo[t - 19:t + 1].sum() / v20; F["t20"][i] = tr[t - 19:t + 1].sum() / v20
            F["fd20"][i] = float((fo[t - 19:t + 1] > 0).sum())
            F["tfirst"][i] = float((tr[t - 4:t + 1] > 0).any() and not (tr[t - 24:t - 4] > 0).any())
        o = tdcc_at(by, s, cs[t])
        for k in ("b400", "b400w1", "b400w4", "b1000", "b1000w1", "b1000w4", "r10w4", "r50w4", "r50p4", "hold4"):
            F[k][i] = o[k]
        DD[i] = None if pd.isna(o["D"]) else str(pd.Timestamp(o["D"]).date())
        if s in INST and np.isfinite(o["tot_sh"]) and o["tot_sh"] > 0:
            F["fh20"][i] = INST[s]["foreign"][t - 19:t + 1].sum() / o["tot_sh"] * 100
        if s in MG and s in VOL:
            mb = pd.Series(MG[s]["m_balance"]).ffill().to_numpy(); sb = pd.Series(MG[s]["s_balance"]).ffill().to_numpy()
            mt, ml, st = MG[s]["m_balance"][t], MG[s]["m_limit"][t], MG[s]["s_balance"][t]
            v = VOL[s]; v5, v20 = v[t - 4:t + 1].sum() / 1000, v[t - 19:t + 1].sum() / 1000
            if np.isfinite(mt):
                if np.isfinite(mb[t - 5]) and mb[t - 5] > 0:
                    F["m5"][i] = mt / mb[t - 5] - 1
                if np.isfinite(mb[t - 20]) and mb[t - 20] > 0:
                    F["m20"][i] = mt / mb[t - 20] - 1
                if np.isfinite(ml) and ml > 0:
                    F["muse"][i] = mt / ml
                if np.isfinite(st):
                    if mt > 0:
                        F["sm"][i] = st / mt
                    if np.isfinite(sb[t - 5]) and v5 > 0:
                        F["s5"][i] = (st - sb[t - 5]) / v5
                    if np.isfinite(sb[t - 20]) and v20 > 0:
                        F["s20"][i] = (st - sb[t - 20]) / v20
    for k in F:
        U[k] = F[k]
    U["集保週D"] = DD
    finfo = {k: (len(v), v[:10]) for k, v in finfo.items()}
    return U, tinfo, finfo


# ═════════════ 分組、打亂 ═════════════
def group_stats(U, keyspec, rng_seed):
    """keyspec：[(欄, 名, 型)]；回 SUMM、GIDX、LABF。"""
    E = U[U["段"] == "探索"]
    SUMM, GIDX, LABF = {}, {}, {}
    TAB = []
    for k, nm, typ in keyspec:
        if typ == "k":
            vc = E[k].value_counts(); keep = [c_ for c_ in vc.index if vc[c_] >= MINGRP]
            names = sorted(keep) + ["其他"]; mp = {c_: j for j, c_ in enumerate(sorted(keep))}
            labf = lambda s, mp=mp, names=names: np.array([np.nan if (v is None or (isinstance(v, float) and np.isnan(v))) else mp.get(v, len(names) - 1) for v in s], float)
            edges = None
        else:
            lab, names, edges = AF.make_bins(k, typ, E[k].to_numpy(float))
            labf = lambda s, lab=lab: lab(np.asarray(s, float))
        LABF[k] = (labf, names)
        sm = {"名稱": nm, "型": typ, "切點（探索段定）": edges, "組": names}
        for s in SEGN:
            G = U[U["段"] == s]; g = labf(G[k].tolist() if typ == "k" else G[k])
            gr = {}
            for j, gn in enumerate(names):
                mm = g == j; z = G.loc[mm, "淨報酬"]
                rec = {"特徵": k, "名稱": nm, "段": s, "組序": j, "組": gn, "筆數": int(mm.sum()),
                       "賺錢比例": float(G.loc[mm, "賺"].mean()) if mm.any() else np.nan,
                       "淨報酬平均": float(z.mean()) if mm.any() else np.nan, "淨報酬中位": float(z.median()) if mm.any() else np.nan}
                TAB.append(rec); gr[gn] = {kk: rec[kk] for kk in ("筆數", "賺錢比例", "淨報酬平均", "淨報酬中位")}
            sm[s] = {"組": gr, "有值筆": int(np.isfinite(g).sum()), "缺值筆": int(np.isnan(g).sum()),
                     "AUC": (AF.auc(G[k].to_numpy(float), G["賺"].to_numpy()) if typ != "k" else None)}
            if s == "探索":
                GIDX[k] = g
        gr = sm["探索"]["組"]; ok = [gn for gn in names if gr[gn]["筆數"] >= MINGRP]
        if len(ok) >= 2:
            hi = max(ok, key=lambda gn: gr[gn]["賺錢比例"]); lo = min(ok, key=lambda gn: gr[gn]["賺錢比例"])
            sm["探索差"] = gr[hi]["賺錢比例"] - gr[lo]["賺錢比例"]; sm["高組"] = hi; sm["低組"] = lo
            g2 = sm["確認"]["組"]
            if g2[hi]["筆數"] and g2[lo]["筆數"]:
                sm["確認差（同兩組）"] = g2[hi]["賺錢比例"] - g2[lo]["賺錢比例"]; sm["確認同方向"] = bool(sm["確認差（同兩組）"] > 0)
            else:
                sm["確認差（同兩組）"] = None; sm["確認同方向"] = None
            sm["確認兩組筆數"] = [g2[hi]["筆數"], g2[lo]["筆數"]]
        else:
            sm["探索差"] = None
        SUMM[k] = sm
    return SUMM, GIDX, LABF, TAB


def null_diffs(SUMM, GIDX, keys, P):
    ND = {}
    for k in keys:
        g = GIDX[k]; rates = []
        for j in range(len(SUMM[k]["組"])):
            mm = g == j
            if mm.sum() >= MINGRP:
                rates.append(P[mm].mean(0))
        R_ = np.vstack(rates); ND[k] = R_.max(0) - R_.min(0)
    return ND


def run():
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    W = pickle.load(open(os.path.join(WORK, "world_主.pkl"), "rb")); cal = W["cal"]
    U = pd.read_csv(os.path.join(FEAT_DIR, "feat_rows.csv.gz"), dtype={"sid": str})
    FJ = json.load(open(os.path.join(FEAT_DIR, "feat.json"), encoding="utf-8"))
    NS = {s: int((U["段"] == s).sum()) for s in SEGN}
    gate = {"feat_rows 各段筆數": NS, "feat.json 分析樣本筆數": {s: FJ["分析樣本（S 已出場）"][s]["筆"] for s in SEGN}}
    assert all(NS[s] == FJ["分析樣本（S 已出場）"][s]["筆"] for s in SEGN), gate
    assert set(U.loc[U["段"].isin(SEGM), "世界"]) == {"主"} and set(U.loc[U["段"] == "早年", "世界"]) == {"早年"}
    U["決策日"] = [str(cal[int(t)].date()) if w == "主" else None for w, t in zip(U["世界"], U["t"])]
    log(f"[樣本] {NS}")
    U, tinfo, finfo = features(U, cal)
    # 有值筆數
    AV = {k: {s: int(np.isfinite(U.loc[U["段"] == s, k]).sum()) for s in SEGN} for k, _, _ in CHIP}
    # 集保有值的探索段日期範圍
    e_ = U[(U["段"] == "探索") & np.isfinite(U["b400"])]
    tdcc_rng = {"探索段 集保有值 決策日 首、尾": [e_["決策日"].min(), e_["決策日"].max()] if len(e_) else None,
                "探索段 集保有值 筆數、其中 2019-07 以前": [int(len(e_)), int((e_["決策日"] < "2019-07-01").sum())]}
    log(f"[有值] {AV}｜{tdcc_rng}")
    rows_out = U[["世界", "策略", "sid", "tb", "格", "t", "決策日", "段", "淨報酬", "賺", "lu20", "集保週D"] + [k for k, _, _ in CHIP]]
    rows_out.to_csv(os.path.join(OUT, "featchip_rows.csv.gz"), index=False, float_format="%.10g")

    SUMM, GIDX, LABF, TAB = group_stats(U, CHIP, SEED)
    # 上一份 19 個（同法重建，對帳 feat.json）
    PS, PG, PL, _ = group_stats(U, AF.FEAT, SEED)
    rec = {}
    for k, _, _ in AF.FEAT:
        a = PS[k]["探索差"]; b = FJ["全部特徵"][k]["探索差"]
        rec[k] = (a, b)
    bad = [k for k, (a, b) in rec.items() if (a is None) != (b is None) or (a is not None and abs(a - b) > 1e-9)]
    gate["上一份 19 特徵 探索差 重建 vs feat.json 不符"] = bad
    assert not bad, bad
    log(f"[閘] {gate}")

    rng = np.random.default_rng(SEED)
    E = U[U["段"] == "探索"]; yE = E["賺"].to_numpy()
    P = np.array([rng.permutation(yE) for _ in range(NPERM)]).T
    keys = [k for k, _, _ in CHIP if SUMM[k]["探索差"] is not None]
    ND = null_diffs(SUMM, GIDX, keys, P)
    pkeys = [k for k, _, _ in AF.FEAT if PS[k]["探索差"] is not None]
    PND = null_diffs(PS, PG, pkeys, P)
    for k in keys:
        SUMM[k]["打亂p（差）"] = float((ND[k] >= SUMM[k]["探索差"] - 1e-12).mean())
        x = E[k].to_numpy(float); okx = np.isfinite(x)
        if SUMM[k]["探索"]["AUC"] is not None and np.isfinite(SUMM[k]["探索"]["AUC"]):
            xr = pd.Series(x[okx]).rank(method="average").to_numpy(); Pk = P[okx]; n1 = Pk.sum(0); n0 = okx.sum() - n1
            A_ = ((xr[:, None] * Pk).sum(0) - n1 * (n1 + 1) / 2) / np.maximum(n1 * n0, 1)
            SUMM[k]["打亂p（|AUC−0.5|）"] = float((np.abs(A_ - 0.5) >= abs(SUMM[k]["探索"]["AUC"] - 0.5) - 1e-12).mean())
    MX = np.vstack([ND[k] for k in keys]); MXall = np.vstack([ND[k] for k in keys] + [PND[k] for k in pkeys])
    obs = sorted(((SUMM[k]["探索差"], k) for k in keys), reverse=True)
    MC = {"籌碼特徵數（進排名）": len(keys), "打亂次數": NPERM,
          "籌碼族系：打亂下最大差 中位、p90、p95": [float(np.median(MX.max(0))), float(np.quantile(MX.max(0), .9)), float(np.quantile(MX.max(0), .95))],
          "籌碼＋上一份 19 個（合併族系 %d 個）：打亂下最大差 中位、p95" % (len(keys) + len(pkeys)): [float(np.median(MXall.max(0))), float(np.quantile(MXall.max(0), .95))]}
    for th in (0.10, 0.15, 0.20, 0.25):
        MC[f"籌碼：光靠運氣預期有幾個特徵差 ≥ {th:.0%}"] = float((MX >= th).sum(0).mean())
        MC[f"籌碼：實際有幾個特徵差 ≥ {th:.0%}"] = int(sum(1 for v, _ in obs if v >= th))
    for k in keys:
        SUMM[k]["族系p（籌碼）"] = float((MX.max(0) >= SUMM[k]["探索差"] - 1e-12).mean())
        SUMM[k]["族系p（籌碼＋上一份）"] = float((MXall.max(0) >= SUMM[k]["探索差"] - 1e-12).mean())
    # 確認段單邊打亂 p（每個特徵）
    for k in keys:
        sm = SUMM[k]; labf, names = LABF[k]
        G = U[U["段"] == "確認"]; g = labf(G[k]); y = G["賺"].to_numpy()
        ih, il = names.index(sm["高組"]), names.index(sm["低組"]); mm = (g == ih) | (g == il)
        if (g == ih).sum() and (g == il).sum():
            yy = y[mm]; hh = (g[mm] == ih); o_ = yy[hh].mean() - yy[~hh].mean()
            Pp = np.array([rng.permutation(yy) for _ in range(NPERM)])
            nul = Pp[:, hh].mean(1) - Pp[:, ~hh].mean(1)
            sm["確認單邊打亂p"] = float((nul >= o_ - 1e-12).mean())
        else:
            sm["確認單邊打亂p"] = None
    # 重疊：與 lu20
    OV = {}
    for k, _, _ in CHIP:
        o = {}
        for s in SEGM:
            G = U[U["段"] == s]; x = G[k]; y = G["lu20"]; ok = np.isfinite(x) & np.isfinite(y)
            o[f"Spearman ρ（{s}，n）"] = [float(pd.Series(x[ok]).rank().corr(pd.Series(y[ok]).rank())) if ok.sum() > 5 else None, int(ok.sum())]
        OV[k] = o
    top5 = [k for _, k in obs[:5]]
    # 也把確認段同方向且確認單邊 p 最小的另列（不是挑選，只是並列）
    TOP = []
    for k in top5:
        sm = SUMM[k]; labf, names = LABF[k]; ih, il = names.index(sm["高組"]), names.index(sm["低組"])
        strat = {}
        for s in SEGM:
            G = U[U["段"] == s]; g = labf(G[k]); low = G["lu20"].to_numpy(float) <= 4
            mh, ml_ = (g == ih) & low, (g == il) & low
            strat[s] = {"lu20≤4 子樣本：高組（筆、賺錢比例）": [int(mh.sum()), float(G["賺"][mh].mean()) if mh.any() else None],
                        "lu20≤4 子樣本：低組（筆、賺錢比例）": [int(ml_.sum()), float(G["賺"][ml_].mean()) if ml_.any() else None],
                        "高組中 lu20＞4 占比": float((G["lu20"][g == ih] > 4).mean()) if (g == ih).any() else None,
                        "低組中 lu20＞4 占比": float((G["lu20"][g == il] > 4).mean()) if (g == il).any() else None}
        TOP.append({"特徵": k, "名稱": sm["名稱"], "探索差": sm["探索差"], "高組": sm["高組"], "低組": sm["低組"],
                    "確認差（同兩組）": sm.get("確認差（同兩組）"), "確認同方向": sm.get("確認同方向"), "確認單邊打亂p": sm.get("確認單邊打亂p"),
                    "AUC 探索／確認": [sm[s]["AUC"] for s in SEGM], "打亂p": sm.get("打亂p（差）"),
                    "族系p（籌碼）": sm["族系p（籌碼）"], "族系p（籌碼＋上一份）": sm["族系p（籌碼＋上一份）"],
                    "有值筆 探索／確認": [sm[s]["有值筆"] for s in SEGM],
                    "各組（筆數, 賺錢比例）": {s: {gn: [v["筆數"], v["賺錢比例"]] for gn, v in sm[s]["組"].items()} for s in SEGM},
                    "與 lu20 重疊": {**OV[k], **strat}})
    # lu20 本身同框（上一份的口徑）
    lu = PS["lu20"]
    LU = {"名稱": lu["名稱"], "探索差": lu["探索差"], "高組": lu["高組"], "低組": lu["低組"], "確認差（同兩組）": lu.get("確認差（同兩組）"),
          "各組（筆數, 賺錢比例）": {s: {gn: [v["筆數"], v["賺錢比例"]] for gn, v in lu[s]["組"].items()} for s in SEGM}}
    RANK = [{"特徵": k, "名稱": SUMM[k]["名稱"], "探索差": v, "高組": SUMM[k]["高組"], "低組": SUMM[k]["低組"],
             "確認差": SUMM[k].get("確認差（同兩組）"), "確認同方向": SUMM[k].get("確認同方向"), "確認單邊打亂p": SUMM[k].get("確認單邊打亂p"),
             "打亂p": SUMM[k].get("打亂p（差）"), "族系p（籌碼）": SUMM[k]["族系p（籌碼）"],
             "AUC 探索": SUMM[k]["探索"]["AUC"], "AUC 確認": SUMM[k]["確認"]["AUC"],
             "有值筆 探索／確認": [SUMM[k][s]["有值筆"] for s in SEGM], "ρ(lu20) 探索／確認": [OV[k][f"Spearman ρ（{s}，n）"][0] for s in SEGM]}
            for v, k in obs]
    noenter = [k for k, _, _ in CHIP if k not in keys]
    pd.DataFrame(TAB).to_csv(os.path.join(OUT, "featchip_table.csv"), index=False, float_format="%.6g")
    OUTJ = {"時間": now_tpe() + "（台北）", "性質": "描述性特徵掃描；⛔ 不計 N、⛔ 不判定；加碼已看過結果 ⇒ 全是事後描述、只當線索",
            "讀法": __doc__.split("═══ 讀法（C 標）═══")[1].split("輸出")[0].strip(),
            "閘": gate, "樣本筆數": NS, "集保資訊": tinfo, "集保有值範圍": tdcc_rng, "檔案缺": finfo, "各特徵有值筆數": AV,
            "籌碼探索段差排名": RANK, "前5（探索段差最大）": TOP, "未進排名（探索段可比組 ＜ 2）": noenter,
            "上一份 lu20 同框": LU, "多重比較": MC, "與 lu20 重疊（Spearman）": OV, "族群": GROUPS,
            "全部籌碼特徵": SUMM, "耗時秒": round(time.time() - T0)}
    jdump(OUTJ, os.path.join(OUT, "featchip.json"))
    log(f"[多重比較] {MC}")
    for r in RANK:
        log(f"  {r}")
    log(f"[完成] {time.time() - T0:.0f}s ⇒ {OUT}")


if __name__ == "__main__":
    run()
