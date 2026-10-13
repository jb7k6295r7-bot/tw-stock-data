# -*- coding: utf-8 -*-
"""漲多加碼：外部 AI 建議 8 項（G4、C5、G1、C1、C4、G2、G3、C2）初測——只改「加碼那一份」，原持股不動——回測線計算子代理。
⛔ 只計算：不 commit、不改既有程式與結果夾；描述性「初測」、⛔ 不計 N、⛔ 不判定；用語「假訊號」；⛔ 不給買賣建議。
⚠ 加碼已看過結果（researchAddOn、truetop、exit5、feat、cf）；8 項 × 版本都在同一批看過的 400 筆事件上試 ⇒ 多重比較；
  任何一項只有在兩段（2017～2021、2022～）方向一致才值得正式登錄，且登錄後仍要在新資料上驗。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchAddOn_ext

═══ 讀法（X 標）═══
 X0 樣本 ＝ resultsAddOn/feat/feat_rows.csv.gz 的 400 筆（同 cf）；段 ＝ feat「段」（探索 ＝ 2017～2021、確認 ＝ 2022～、早年 2005～2014）；主窗 ＝ 探索＋確認
    出場 ＝ exit5/exits.csv.gz 的 S（原持股同日同價：S_價、S_價根 sb）；決策日 t（收盤）、A 的加碼日 ta ＝ t 的次一交易日
    基準 A ＝ ta 開盤加 1 份、sb 收盤賣：r ＝ S_價 ÷ op[ta] − 1 − COST（0.585%）；閘 ＝ feat 淨報酬（≤ 1e−9）
    金額 ＝ 原買進金額 × 份數；原買進金額 ＝ exit5/paths.csv.gz「金額」（起始權益 ＝ 1 的單位；營飆 ＝ 持有該筆的種子平均）
    延後買進（G4 第二份、G1、C4）：買在 d 之後第一個有效開盤 db；db ＞ sb ⇒ 不加；(t, db] 有壞根 ⇒ 不加（壞根 ＝ researchAddOn.market 同一套）；同 sb 收盤賣
    有效 K 棒 ＝ researchAddOn 的 K 棒（bar）且收盤有值；「前 N 日」＝ 前 N 根有效 K 棒（不含當日）；均線 MA_N(d) ＝ 含 d 的最近 N 根有效收盤平均
    價量 ＝ 世界還原收盤／開盤；高低 ＝ 原始 csv（W["data"]/stocks）高低 × (世界收盤 ÷ 原始收盤)；量 ＝ 原始成交股數；發行股數 ＝ 原始 csv shares 欄（≤ 當日最後一個有值）
 X1 各項（⛔ 不重切、⛔ 不調參；寫在算任何本件數字之前）
    G4 分兩次：ta 開盤 0.5 份；從 ta 起第 3 根有效收盤 c3（ta 算第 1 根）收盤 ≥ op[ta] ⇒ c3 後第一個有效開盤再 0.5 份（規則同延後買進）；否則只有 0.5 份
    C5 份數 w ＝ clip(σref ÷ σ20, 0.25, 1)；σ20 ＝ t 收盤為止 20 個日報酬（位置 t−20…t 共 21 根皆有 K 棒有收盤、(t−20, t] 無壞根）標準差（ddof 1）；
       σref ＝ 同世界、決策日日期嚴格早於 t 的樣本事件 σ20 中位（擴張、不偷看）；先前事件 ＜ 20 筆 ⇒ 用 t 當天 R1 母體（同定義 σ20）中位代替；σ20 缺 ⇒ w ＝ 1（照報筆數）
    G1 回檔再加：d ∈ (t, t＋10]（交易日位置）且 d ＜ sb 的有效 K 棒中，第一個符合 ⇒ 延後買進；等不到 ⇒ 不加
       G1a：收盤 ≤ MA5(d) 且 量 ≤ 前 5 日均量 × 0.7；G1b：收盤 ≤ MA10(d) 且同量縮；
       G1c：[t, d] 最高收盤 − 收盤[d] ≥ ATR20(d)（含 d 最近 20 根有效 K 棒 TR 平均，TR 用前一根有效收盤；窗內有壞根 ⇒ 缺 ⇒ 不成立）且同量縮
    C1 突破確認：t 收盤 ＞ 前 20 日最高收盤 且 t 量 ＞ 前 20 日均量 × 1.2 ⇒ A；否則不加
    C4 整理後再突破：L5 ＝ 前 5 日（t 之前 5 根有效）最低收盤；hi ＝ 收盤[t]、停 ＝ 0；依序看 d ∈ (t, t＋10] 且 d ＜ sb 的有效 K 棒：
       收盤 ＜ L5 ⇒ 放棄（不加）；收盤 ＞ hi：停 ≥ 3 ⇒ d 為突破 ⇒ 延後買進；否則 hi ＝ 收盤、停 ＝ 0；收盤 ≤ hi ⇒ 停 ＋1；等不到 ⇒ 不加
       （整理期最高收盤 ＝ 從 t 起的最高收盤；「突破」＝ 停 ≥ 3 日後第一次收盤創新高）
    G2 過熱排除：週轉 ＝ t 量 ÷ 發行股數 ＞ 15%，或（t 量 ＞ 前 20 日均量 × 4 且 上影線 ＞ 實體 × 2；上影 ＝ 高 − max(開, 收)、實體 ＝ |收 − 開|，同日原始價）⇒ 不加；否則 A
       發行股數缺 ⇒ 只看第二條（照報「週轉缺」筆數；集保總股數：本快照沒有逐股集保總股數 ⇒ 未用）
    G3 大盤濾網：G3a 加權指數（us-stock-data/data/macro/twse_taiex.csv，DB 線抓的證交所 FMTQIK）t 收盤 ＞ 含 t 的 20 日均 ⇒ A；否則不加
       G3b 上市看加權、上櫃看櫃買指數 ⇒ 櫃買指數本機無資料 ⇒ 上櫃筆 ＝ 缺（不進該版統計，照報）；G3c（另列）0050 還原收盤（世界 bench）＞ 20 日均
    C2 波動調整動能（只描述、不改觸發）：z ＝ (C[t] ÷ C[t−20] − 1) ÷ (σ20 × √20)；在 t 當天 R1 母體（同定義、有值者）的百分位 p（＜ 的比例，同值算半）；
       分兩半 ＝ 以探索段事件 p 的中位為切點（⛔ 切點只用探索段），各段照切；另報 p ≥ 0.5 的筆數比例
 X2 每項每段報：事件數、加碼筆數、不加比例、加碼那份的 平均／中位／賺錢比例／賠的平均（＜0 者平均）／賠 ＞15% 比例（皆只算有加的筆、每筆報酬 ＝ 該筆總損益 ÷ 投入金額）、
    總損益 ＝ Σ 金額 × 份數 × 報酬（起始權益 ＝ 1 的單位）；與 A 的配對差：
      ① 總損益差 ＝ Σ 金額 × (Σ_j w_j r_j − r_A)（沒加 ⇒ 該筆 −r_A）；CI ＝ 按 A 加碼月（世界|年月）群集 bootstrap 5000 次（default_rng(20261013)）的總和百分位 95%
      ② 每筆損益差（份數單位，未乘金額）平均與 CI
      ③ 延後類（G4、G1、C4）：同批已加碼事件的報酬差（X 報酬 − A 報酬）平均與 CI；濾網類（C1、G2、G3）：加碼價同 A ⇒ 改報「留下那批 A 平均 − 被排除那批 A 平均」
         （兩組共用月群集重抽）；C5 不適用（只改份數）
      另列「平均差 vs A」＝ 本臂有加者平均 − 同批事件 A 平均（非配對）
    （事後註：③ 的濾網／C5 讀法是第一次跑完看到 ③ ＝ 0（濾網、C5 依定義必為 0）後補；其餘讀法沒改）
    兩段同向 ＝ ① 在探索、確認兩段同號（另列 ③ 同號）；⛔ 不判定
輸出 backtest/resultsAddOn/ext/：ext.json、ext_table.csv、ext_rows.csv.gz
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchAddOn as AO                      # noqa: E402
from backtest import universe_gate as UG                      # noqa: E402

OUT = "backtest/resultsAddOn/ext"
AO_OUT = "backtest/resultsAddOn"
TAIEX = os.path.expanduser("~/us-stock-data/data/macro/twse_taiex.csv")
COST = AO.COST
SEED = 20261013
NBOOT = 5000
SEGN = ("探索", "確認", "主窗", "早年")
ARMS = ["A", "G4", "C5", "G1a", "G1b", "G1c", "C1", "C4", "G2", "G3a", "G3b", "G3c"]
FILTERS = ("C1", "G2", "G3a", "G3b", "G3c")
ARM_NAME = {"A": "基準 A（隔天開盤 1 份）", "G4": "G4 分兩次（0.5＋條件 0.5）", "C5": "C5 波動調整份數",
            "G1a": "G1a 回檔 MA5＋量縮", "G1b": "G1b 回檔 MA10＋量縮", "G1c": "G1c 回落 1ATR＋量縮",
            "C1": "C1 突破確認（20 日新高＋量 1.2 倍）", "C4": "C4 整理後再突破", "G2": "G2 過熱排除",
            "G3a": "G3a 加權指數 ＞ MA20", "G3b": "G3b 上市加權／上櫃櫃買（櫃買缺）", "G3c": "G3c 0050 ＞ MA20（另列）"}


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def load_raw(data, sid, cal):
    p = os.path.join(data, "stocks", f"{sid}.csv")
    raw = pd.read_csv(p, dtype={"date": str}, usecols=["date", "open", "high", "low", "close", "volume", "shares"])
    raw["date"] = pd.to_datetime(raw["date"])
    raw = raw.drop_duplicates("date").set_index("date").sort_index()
    for c in ("open", "high", "low", "close", "volume", "shares"):
        raw[c] = pd.to_numeric(raw[c], errors="coerce")
    bad = (raw[["open", "high", "low", "close"]] <= 0).any(axis=1)
    raw.loc[bad, ["open", "high", "low", "close"]] = np.nan
    raw["shares"] = raw["shares"].where(raw["shares"] > 0).ffill()
    return raw.reindex(cal)


def sig20(cl, okb, BADC, t):
    """位置 t−20…t 共 21 根皆有效、(t−20, t] 無壞根 ⇒ 20 個日報酬標準差（ddof 1）。"""
    if t < 20:
        return np.nan
    if not okb[t - 20:t + 1].all() or BADC[t + 1] - BADC[t - 20 + 1] > 0:
        return np.nan
    c = cl[t - 20:t + 1]
    return float(np.std(c[1:] / c[:-1] - 1.0, ddof=1))


def boot(vals, clu, rng, stat="mean"):
    x = np.asarray(vals, float); ok = np.isfinite(x); x = x[ok]; cl_ = np.asarray(clu)[ok]
    if len(x) < 2:
        return {"n": int(len(x)), "值": (float(x.sum() if stat == "sum" else x.mean()) if len(x) else None), "CI95": [None, None]}
    u, inv = np.unique(cl_, return_inverse=True); G = len(u)
    s = np.bincount(inv, weights=x, minlength=G); c = np.bincount(inv, minlength=G).astype(float)
    bs = np.empty(NBOOT)
    for b in range(NBOOT):
        k = rng.integers(G, size=G)
        bs[b] = s[k].sum() if stat == "sum" else s[k].sum() / c[k].sum()
    v = float(x.sum() if stat == "sum" else x.mean())
    return {"n": int(len(x)), "群集月數": int(G), "值": v, "CI95": [float(np.quantile(bs, .025)), float(np.quantile(bs, .975))],
            "bootstrap ≤0 比例": float((bs <= 0).mean())}


def boot_diff2(xa, ca, xb, cb, rng):
    """兩組平均差（高 − 低），按月群集（兩組共用月集合重抽）。"""
    xa = np.asarray(xa, float); xb = np.asarray(xb, float)
    allc = np.unique(np.r_[np.asarray(ca), np.asarray(cb)]); ix = {c: i for i, c in enumerate(allc)}; G = len(allc)
    ia = np.array([ix[c] for c in ca]); ib = np.array([ix[c] for c in cb])
    sa = np.bincount(ia, weights=xa, minlength=G); na = np.bincount(ia, minlength=G).astype(float)
    sb = np.bincount(ib, weights=xb, minlength=G); nb = np.bincount(ib, minlength=G).astype(float)
    bs = []
    for _ in range(NBOOT):
        k = rng.integers(G, size=G)
        if na[k].sum() > 0 and nb[k].sum() > 0:
            bs.append(sa[k].sum() / na[k].sum() - sb[k].sum() / nb[k].sum())
    bs = np.array(bs)
    return {"差": float(xa.mean() - xb.mean()), "CI95": [float(np.quantile(bs, .025)), float(np.quantile(bs, .975))], "群集月數": int(G)}


def stats(ret, pnl_amt, added):
    r = np.asarray(ret, float)[np.asarray(added, bool)]
    o = {"加碼筆數": int(len(r))}
    if len(r):
        lo = r[r < 0]
        o.update(平均=float(r.mean()), 中位=float(np.median(r)), 賺錢比例=float((r > 0).mean()),
                 賠的平均=(float(lo.mean()) if len(lo) else None), 賠超過15比例=float((r < -0.15).mean()))
    o["總損益"] = float(np.nansum(pnl_amt))
    return o


def main():
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    f = pd.read_csv(os.path.join(AO_OUT, "feat", "feat_rows.csv.gz"), dtype={"sid": str},
                    usecols=["世界", "策略", "sid", "tb", "格", "t", "ta", "段", "淨報酬"])
    ex = pd.read_csv(os.path.join(AO_OUT, "exit5", "exits.csv.gz"), dtype={"sid": str},
                     usecols=["世界", "策略", "sid", "tb", "格", "加碼價", "S_價", "S_價根", "S_種類"])
    pa = pd.read_csv(os.path.join(AO_OUT, "exit5", "paths.csv.gz"), dtype={"sid": str})
    pa = pa.groupby(["世界", "策略", "sid", "tb", "格"])["金額"].agg(金額="mean", 種子數="count").reset_index()
    d = f.merge(ex, on=["世界", "策略", "sid", "tb", "格"], how="left", validate="1:1").merge(pa, on=["世界", "策略", "sid", "tb", "格"], how="left", validate="1:1")
    assert len(d) == 400 and d["S_價"].notna().all() and d["金額"].notna().all()
    assert (d["S_種類"] == "同原持股").all()
    info = {"樣本": int(len(d)), "各段": d["段"].value_counts().to_dict(),
            "金額來源": "exit5/paths.csv.gz 金額（起始權益 ＝ 1）；營飆 ＝ 持有該筆的種子平均（種子數中位 %d）" % int(d.loc[d["策略"] == "營飆", "種子數"].median())}
    WS = AO.worlds(log, 1)
    UG.set_gate_v2(True)
    HBW = {}; MW = {}; X = None
    for wn in ("主", "早年"):
        hs = sorted(set(d.loc[d["世界"] == wn, "sid"]))
        M, HB, X, minfo = AO.market(wn, WS[wn], X, log, hs)
        HBW[wn] = HB; MW[wn] = M
    # TAIEX
    tx = pd.read_csv(TAIEX, dtype={"date": str}); tx["date"] = pd.to_datetime(tx["date"]); tx = tx.drop_duplicates("date").set_index("date")["close"].astype(float)
    TXM = {}
    for wn, W in WS.items():
        s = tx.reindex(W["cal"]).to_numpy(float)
        TXM[wn] = s
        info[f"加權指數 {wn} 世界日曆缺值天數"] = int(np.isnan(s[W["w0"]:W["w1"] + 1]).sum())
    # 每世界每個需要的 t：R1 母體 σ20、z
    POP = {}
    for wn in ("主", "早年"):
        M = MW[wn]; C, BAR, BAD, R1m = M["C"], M["BAR"], M["BAD"], M["R1"]
        CB = np.zeros((M["S"], M["n"] + 1), np.int32); CB[:, 1:] = np.cumsum(BAD, axis=1)
        for t in sorted(set(d.loc[d["世界"] == wn, "t"].astype(int))):
            m = R1m[:, t].copy()
            m &= BAR[:, t - 20:t + 1].all(1) & np.isfinite(C[:, t - 20:t + 1]).all(1) & ((CB[:, t + 1] - CB[:, t - 19]) == 0)
            cc = C[m][:, t - 20:t + 1]
            sg = np.std(cc[:, 1:] / cc[:, :-1] - 1.0, axis=1, ddof=1)
            z = (cc[:, -1] / cc[:, 0] - 1.0) / (sg * np.sqrt(20))
            z = z[np.isfinite(z)]
            POP[(wn, t)] = (float(np.median(sg)) if len(sg) else np.nan, np.sort(z), int(m.sum()))
    rows = []; gate_a = 0.0; gate_px = 0.0; gate_cl = 0.0
    RAW = {}
    for r in d.to_dict("records"):
        wn, sid, tb, t, ta = r["世界"], r["sid"], int(r["tb"]), int(r["t"]), int(r["ta"])
        W = WS[wn]; cal = W["cal"]; n = len(cal)
        op = np.asarray(W["opens"][sid][:n], float); cl = np.asarray(W["closes"][sid][:n], float)
        bar, bad = HBW[wn][sid]; bar = np.asarray(bar[:n], bool); bad = np.asarray(bad[:n], bool)
        BADC = np.r_[0, np.cumsum(bad)]
        okb = bar & np.isfinite(cl)
        vopen = bar & np.isfinite(op) & (op > 0)
        key = (wn, sid)
        if key not in RAW:
            RAW[key] = load_raw(W["data"], sid, cal)
        rw = RAW[key]
        fac = cl / rw["close"].to_numpy(float)
        hi = rw["high"].to_numpy(float) * fac; lo = rw["low"].to_numpy(float) * fac
        vol = rw["volume"].to_numpy(float); shr = rw["shares"].to_numpy(float)
        ro, rh, rc = rw["open"].to_numpy(float), rw["high"].to_numpy(float), rw["close"].to_numpy(float)
        # 閘：原始開盤 × 因子 vs 世界開盤（t−30…sb 有效處）
        sb = int(r["S_價根"]); sp = float(r["S_價"])
        win = np.arange(max(t - 30, 0), min(sb, n - 1) + 1); win = win[okb[win] & vopen[win] & np.isfinite(fac[win])]
        if len(win):
            gate_cl = max(gate_cl, float(np.max(np.abs(ro[win] * fac[win] / op[win] - 1.0))))
        A = sp / op[ta] - 1.0 - COST
        gate_a = max(gate_a, abs(A - r["淨報酬"])); gate_px = max(gate_px, abs(op[ta] / r["加碼價"] - 1.0))
        vb = np.flatnonzero(okb[:n])                                   # 有效 K 棒位置
        vvb = vb[np.isfinite(vol[vb])]

        def prev_valid(arr_pos, d_, k):
            j = int(np.searchsorted(arr_pos, d_))                     # arr_pos[j-1] < d_
            return arr_pos[max(0, j - k):j] if j >= k else None

        def last_valid(arr_pos, d_, k):
            j = int(np.searchsorted(arr_pos, d_, side="right"))
            return arr_pos[j - k:j] if j >= k else None

        def buy_after(dd):
            fut = np.flatnonzero(vopen[dd + 1:n]) + dd + 1
            if not len(fut):
                return None, "資料尾"
            db = int(fut[0])
            if db > sb:
                return None, "超過出場"
            if BADC[db + 1] - BADC[t + 1] > 0:
                return None, "壞根"
            return db, ""

        def vshrink(dd):
            p5 = prev_valid(vvb, dd, 5)
            return p5 is not None and np.isfinite(vol[dd]) and vol[dd] <= 0.7 * vol[p5].mean()

        def atr20(dd):
            w = last_valid(vb, dd, 21)
            if w is None or BADC[w[-1] + 1] - BADC[w[0] + 1] > 0:
                return np.nan
            pc = cl[w[:-1]]; h_ = hi[w[1:]]; l_ = lo[w[1:]]
            tr = np.maximum.reduce([h_ - l_, np.abs(h_ - pc), np.abs(l_ - pc)])
            return float(np.mean(tr)) if np.isfinite(tr).all() else np.nan

        o = {k: r[k] for k in ("世界", "策略", "sid", "tb", "格", "t", "ta", "段", "金額")}
        o.update(sb=sb, 市場=W["uni"].get(sid, "twse"), 加碼月=str(cal[ta])[:7])
        LEG = {}                                                       # arm -> [(w, ret)] ；空 ⇒ 不加
        LEG["A"] = [(1.0, A)]
        # G4
        vt = vb[vb >= ta]; leg = [(0.5, A)]; o["G4_第二份"] = "否"
        if len(vt) >= 3:
            c3 = int(vt[2])
            if cl[c3] >= op[ta]:
                db, why = buy_after(c3)
                if db is not None:
                    leg.append((0.5, sp / op[db] - 1.0 - COST)); o["G4_第二份"] = "加"
                else:
                    o["G4_第二份"] = "條件成立但" + why
            else:
                o["G4_第二份"] = "第3收盤＜加碼價"
        LEG["G4"] = leg
        # C5
        s20 = sig20(cl, okb, BADC, t); o["σ20"] = s20
        LEG["C5"] = None                                               # 之後依 σref 填
        # G1
        for arm, kind in (("G1a", 5), ("G1b", 10), ("G1c", "atr")):
            LEG[arm] = []; o[f"{arm}_因"] = "等不到"
            for dd in vb[(vb > t) & (vb <= t + 10) & (vb < sb)]:
                dd = int(dd)
                if kind == "atr":
                    pk = np.nanmax(cl[t:dd + 1][okb[t:dd + 1]]); a_ = atr20(dd)
                    c1 = np.isfinite(a_) and (pk - cl[dd] >= a_)
                else:
                    lw = last_valid(vb, dd, kind)
                    c1 = lw is not None and cl[dd] <= cl[lw].mean()
                if c1 and vshrink(dd):
                    db, why = buy_after(dd)
                    if db is not None:
                        LEG[arm] = [(1.0, sp / op[db] - 1.0 - COST)]; o[f"{arm}_因"] = "加"; o[f"{arm}_延後根"] = db - ta
                    else:
                        o[f"{arm}_因"] = "成立但" + why
                    break
        # C1
        p20 = prev_valid(vb, t, 20); p20v = prev_valid(vvb, t, 20)
        c1ok = (p20 is not None and p20v is not None and cl[t] > np.max(cl[p20]) and np.isfinite(vol[t]) and vol[t] > 1.2 * vol[p20v].mean())
        o["C1_成立"] = bool(c1ok); LEG["C1"] = [(1.0, A)] if c1ok else []
        # C4
        LEG["C4"] = []; o["C4_因"] = "等不到"
        p5 = prev_valid(vb, t, 5)
        if p5 is None:
            o["C4_因"] = "缺前5日"
        else:
            L5 = float(np.min(cl[p5])); hh = cl[t]; pause = 0
            for dd in vb[(vb > t) & (vb <= t + 10) & (vb < sb)]:
                dd = int(dd)
                if cl[dd] < L5:
                    o["C4_因"] = "跌破前5日低"; break
                if cl[dd] > hh:
                    if pause >= 3:
                        db, why = buy_after(dd)
                        if db is not None:
                            LEG["C4"] = [(1.0, sp / op[db] - 1.0 - COST)]; o["C4_因"] = "加"; o["C4_延後根"] = db - ta
                        else:
                            o["C4_因"] = "成立但" + why
                        break
                    hh = cl[dd]; pause = 0
                else:
                    pause += 1
        # G2
        turn = vol[t] / shr[t] if (np.isfinite(shr[t]) and np.isfinite(vol[t])) else np.nan
        o["週轉"] = turn
        sh_up = rh[t] - max(ro[t], rc[t]); body = abs(rc[t] - ro[t])
        c2 = bool(p20v is not None and np.isfinite(vol[t]) and vol[t] > 4 * vol[p20v].mean() and np.isfinite(sh_up) and sh_up > 2 * body)
        o["G2_量4倍長上影"] = c2; o["G2_週轉缺"] = bool(not np.isfinite(turn))
        hot = (np.isfinite(turn) and turn > 0.15) or c2
        o["G2_過熱"] = bool(hot); LEG["G2"] = [] if hot else [(1.0, A)]
        # G3
        txs = TXM[wn]
        g3a = bool(t >= 19 and np.isfinite(txs[t - 19:t + 1]).all() and txs[t] > txs[t - 19:t + 1].mean())
        o["G3a_多頭"] = g3a; LEG["G3a"] = [(1.0, A)] if g3a else []
        if o["市場"] == "tpex":
            LEG["G3b"] = None; o["G3b_缺"] = True
        else:
            LEG["G3b"] = LEG["G3a"]; o["G3b_缺"] = False
        b = np.asarray(W["bench"], float)
        g3c = bool(t >= 19 and b[t] > b[t - 19:t + 1].mean()); o["G3c_多頭"] = g3c; LEG["G3c"] = [(1.0, A)] if g3c else []
        # C2
        sgp, zs, npop = POP[(wn, t)]
        z = ((cl[t] / cl[t - 20] - 1.0) / (s20 * np.sqrt(20))) if np.isfinite(s20) else np.nan
        o["C2_z"] = z; o["R1母體σ20中位"] = sgp; o["R1母體有效檔"] = npop
        o["C2_p"] = (float((np.searchsorted(zs, z, "left") + np.searchsorted(zs, z, "right")) / 2 / len(zs)) if (np.isfinite(z) and len(zs)) else np.nan)
        o["_LEG"] = LEG
        rows.append(o)
    gates = {"A 重現 vs feat 淨報酬 最大差": gate_a, "加碼價 vs 世界開盤 最大相對差": gate_px,
             "原始開盤 × (世界收盤÷原始收盤) vs 世界開盤 最大相對差（t−30…sb）": gate_cl}
    log(f"[閘] {gates}")
    if gate_a > 1e-9 or gate_px > 1e-9:
        raise SystemExit("⛔ A 重現閘不過")
    # C5 σref（每世界擴張）
    nfb = 0; nmiss = 0
    for wn in ("主", "早年"):
        idx = sorted([i for i, o in enumerate(rows) if o["世界"] == wn], key=lambda i: (rows[i]["t"], i))
        for i in idx:
            o = rows[i]; tt = o["t"]
            prev = [rows[j]["σ20"] for j in idx if rows[j]["t"] < tt and np.isfinite(rows[j]["σ20"])]
            if len(prev) >= 20:
                ref = float(np.median(prev)); o["σref來源"] = "先前事件"
            else:
                ref = o["R1母體σ20中位"]; o["σref來源"] = "R1母體當日"; nfb += 1
            o["σref"] = ref
            if np.isfinite(o["σ20"]) and o["σ20"] > 0 and np.isfinite(ref):
                w = float(np.clip(ref / o["σ20"], 0.25, 1.0))
            else:
                w = 1.0; nmiss += 1
            o["C5_w"] = w
            o["_LEG"]["C5"] = [(w, o["_LEG"]["A"][0][1])]
    info["C5"] = {"σref 用 R1 母體當日中位代替的筆數（各世界前 20 筆內）": nfb, "σ20 缺 ⇒ w＝1 筆數": nmiss}
    # 展開
    for o in rows:
        LEG = o.pop("_LEG")
        rA = LEG["A"][0][1]; o["A_ret"] = rA
        for arm in ARMS:
            lg = LEG[arm]
            if lg is None:
                o[f"{arm}_缺"] = True; o[f"{arm}_加"] = False; o[f"{arm}_份"] = np.nan; o[f"{arm}_ret"] = np.nan; o[f"{arm}_pnl"] = np.nan; continue
            o[f"{arm}_缺"] = False
            ws = sum(w for w, _ in lg); pn = sum(w * x for w, x in lg)
            o[f"{arm}_加"] = bool(ws > 0); o[f"{arm}_份"] = ws
            o[f"{arm}_ret"] = (pn / ws) if ws > 0 else np.nan
            o[f"{arm}_pnl"] = pn                                       # 份數單位（× 金額 ⇒ 起始權益單位）
    R_ = pd.DataFrame(rows)
    R_["clu"] = R_["世界"] + "|" + R_["加碼月"]
    R_.to_csv(os.path.join(OUT, "ext_rows.csv.gz"), index=False, float_format="%.10g")
    # C2 切點（探索段）
    cut = float(R_.loc[R_["段"] == "探索", "C2_p"].median())
    R_["C2_半"] = np.where(R_["C2_p"].isna(), "缺", np.where(R_["C2_p"] > cut, "高", "低"))

    def seg(sg):
        return R_[R_["段"].isin(("探索", "確認"))] if sg == "主窗" else R_[R_["段"] == sg]
    rng = np.random.default_rng(SEED)
    J = {"時間": now_tpe() + "（台北）", "性質": "初測（描述性）；⛔ 不計 N、⛔ 不判定；只當是否值得正式登錄的參考",
         "多重比較註": "8 項 × 版本（共 %d 臂＋C2 描述）都在同一批已看過的 400 筆事件上試 ⇒ 多重比較；任何一項只有在兩段（2017～2021、2022～）方向一致才值得登錄，登錄後仍須新資料驗" % (len(ARMS) - 1),
         "讀法": __doc__.split("═══ 讀法（X 標）═══")[1].split("輸出")[0].strip(), "資訊": info, "閘": gates, "段": {}}
    TB = []
    for sg in SEGN:
        s = seg(sg); z = {}
        for arm in ARMS:
            ss = s[~s[f"{arm}_缺"]]
            amt = ss["金額"].to_numpy(float)
            pnl_amt = amt * ss[f"{arm}_pnl"].to_numpy(float)
            st = stats(ss[f"{arm}_ret"], pnl_amt, ss[f"{arm}_加"])
            st["事件數"] = int(len(ss)); st["缺（不進統計）"] = int(s[f"{arm}_缺"].sum())
            st["不加比例"] = float(1 - st["加碼筆數"] / len(ss)) if len(ss) else None
            st["平均份數（有加者）"] = float(ss.loc[ss[f"{arm}_加"], f"{arm}_份"].mean()) if st["加碼筆數"] else None
            st["總損益 A（同批事件）"] = float(np.sum(amt * ss["A_ret"].to_numpy(float)))
            if arm != "A":
                dd = ss[f"{arm}_pnl"].to_numpy(float) - ss["A_ret"].to_numpy(float)
                st["①總損益差（金額）"] = boot(amt * dd, ss["clu"], rng, "sum")
                st["②每筆損益差（份數單位）"] = boot(dd, ss["clu"], rng, "mean")
                ad = ss[ss[f"{arm}_加"]]
                if arm in FILTERS:                                     # 濾網：加碼價同 A ⇒ 改報「留下 − 排除」的 A 平均差
                    ex_ = ss[~ss[f"{arm}_加"]]
                    if len(ad) > 1 and len(ex_) > 1:
                        bd = boot_diff2(ad["A_ret"], ad["clu"], ex_["A_ret"], ex_["clu"], rng)
                        st["③同批已加報酬差"] = {"n": [int(len(ad)), int(len(ex_))], "值": bd["差"], "CI95": bd["CI95"], "意義": "留下那批 A 平均 − 被排除那批 A 平均"}
                    else:
                        st["③同批已加報酬差"] = {"n": [int(len(ad)), int(len(ex_))], "值": None, "CI95": [None, None]}
                    st["被排除那批 A"] = stats(ex_["A_ret"], ex_["金額"] * ex_["A_ret"], np.ones(len(ex_), bool))
                elif arm == "C5":
                    st["③同批已加報酬差"] = {"n": int(len(ad)), "值": None, "CI95": [None, None], "意義": "不適用（只改份數，每筆報酬 ＝ A）"}
                else:
                    st["③同批已加報酬差"] = boot(ad[f"{arm}_ret"] - ad["A_ret"], ad["clu"], rng, "mean")
                st["平均差（本臂平均 − A 平均，非配對）"] = (st["平均"] - float(ss["A_ret"].mean())) if st["加碼筆數"] else None
            z[arm] = st
            rec = {"段": sg, "臂": arm, "名稱": ARM_NAME[arm], "事件數": st["事件數"], "缺": st["缺（不進統計）"], "加碼筆數": st["加碼筆數"],
                   "不加比例": st["不加比例"], "平均": st.get("平均"), "中位": st.get("中位"), "賺錢比例": st.get("賺錢比例"),
                   "賠的平均": st.get("賠的平均"), "賠超過15比例": st.get("賠超過15比例"), "總損益": st["總損益"], "總損益A同批": st["總損益 A（同批事件）"]}
            if arm != "A":
                rec["平均差vsA"] = st["平均差（本臂平均 − A 平均，非配對）"]
                for k_, lab in (("①總損益差（金額）", "總損益差"), ("②每筆損益差（份數單位）", "每筆損益差"), ("③同批已加報酬差", "報酬差")):
                    rec[lab] = st[k_]["值"]; rec[lab + "_CI低"] = st[k_]["CI95"][0]; rec[lab + "_CI高"] = st[k_]["CI95"][1]
            TB.append(rec)
        # 各臂細項
        z["細項"] = {"G4 第二份": s["G4_第二份"].value_counts().to_dict(),
                   "G1a": s["G1a_因"].value_counts().to_dict(), "G1b": s["G1b_因"].value_counts().to_dict(), "G1c": s["G1c_因"].value_counts().to_dict(),
                   "G1 延後根（中位 a/b/c）": [float(s[f"{a}_延後根"].median()) if f"{a}_延後根" in s else None for a in ("G1a", "G1b", "G1c")],
                   "C4": s["C4_因"].value_counts().to_dict(), "C4 延後根中位": float(s["C4_延後根"].median()) if "C4_延後根" in s else None,
                   "C5 w（平均／中位／=1 比例／=0.25 比例）": [float(s["C5_w"].mean()), float(s["C5_w"].median()), float((s["C5_w"] >= 1 - 1e-12).mean()), float((s["C5_w"] <= 0.25 + 1e-12).mean())],
                   "G2 週轉缺": int(s["G2_週轉缺"].sum()), "G2 週轉＞15%": int((s["週轉"] > 0.15).sum()), "G2 量4倍長上影": int(s["G2_量4倍長上影"].sum()),
                   "G2 週轉 中位／p90": [float(s["週轉"].median()), float(s["週轉"].quantile(.9))] if s["週轉"].notna().any() else None,
                   "G3b 上櫃缺": int(s["G3b_缺"].sum())}
        # C2
        c2 = {}
        for hf in ("高", "低"):
            q = s[s["C2_半"] == hf]
            c2[hf] = stats(q["A_ret"], q["金額"] * q["A_ret"], np.ones(len(q), bool)); c2[hf]["筆"] = int(len(q))
        qa = s[s["C2_半"] == "高"]; qb = s[s["C2_半"] == "低"]
        c2["高−低 平均差"] = boot_diff2(qa["A_ret"], qa["clu"], qb["A_ret"], qb["clu"], rng) if len(qa) > 1 and len(qb) > 1 else None
        c2["缺"] = int((s["C2_半"] == "缺").sum()); c2["p ≥ 0.5 比例"] = float((s["C2_p"] >= 0.5).mean()); c2["p 中位"] = float(s["C2_p"].median())
        z["C2"] = c2
        for hf in ("高", "低"):
            TB.append({"段": sg, "臂": f"C2{hf}", "名稱": f"C2 波動調整動能 {hf}半（切點＝探索段中位 p {cut:.4f}）", "事件數": c2[hf]["筆"], "加碼筆數": c2[hf]["加碼筆數"],
                       "平均": c2[hf].get("平均"), "中位": c2[hf].get("中位"), "賺錢比例": c2[hf].get("賺錢比例"), "賠的平均": c2[hf].get("賠的平均"),
                       "賠超過15比例": c2[hf].get("賠超過15比例"), "總損益": c2[hf]["總損益"],
                       "報酬差": (c2["高−低 平均差"]["差"] if (hf == "高" and c2["高−低 平均差"]) else None),
                       "報酬差_CI低": (c2["高−低 平均差"]["CI95"][0] if (hf == "高" and c2["高−低 平均差"]) else None),
                       "報酬差_CI高": (c2["高−低 平均差"]["CI95"][1] if (hf == "高" and c2["高−低 平均差"]) else None)})
        J["段"][sg] = z
    J["C2 切點（探索段事件 p 中位）"] = cut
    # 兩段同向
    SAME = {}
    for arm in ARMS[1:]:
        e = J["段"]["探索"][arm]; c = J["段"]["確認"][arm]; y = J["段"]["早年"][arm]
        a1, a2, a3 = e["①總損益差（金額）"]["值"], c["①總損益差（金額）"]["值"], y["①總損益差（金額）"]["值"]
        b1, b2, b3 = e["③同批已加報酬差"]["值"], c["③同批已加報酬差"]["值"], y["③同批已加報酬差"]["值"]
        sgn = lambda v: (None if v is None else int(np.sign(v)))
        SAME[arm] = {"總損益差 探索／確認／早年": [a1, a2, a3], "總損益差 兩段同號": (sgn(a1) == sgn(a2) and sgn(a1) != 0),
                     "總損益差 方向": ("正" if (a1 or 0) > 0 else "負") if sgn(a1) == sgn(a2) else "不一致",
                     "③ 探索／確認／早年（濾網 ＝ 留下−排除；延後 ＝ 配對報酬差）": [b1, b2, b3],
                     "③ 兩段同號": (b1 is not None and b2 is not None and sgn(b1) == sgn(b2) and sgn(b1) != 0),
                     "平均差vsA 探索／確認／早年": [e["平均差（本臂平均 − A 平均，非配對）"], c["平均差（本臂平均 − A 平均，非配對）"], y["平均差（本臂平均 − A 平均，非配對）"]],
                     "早年同號（總損益差）": (sgn(a3) == sgn(a1)) if sgn(a1) == sgn(a2) else None}
    hA = J["段"]["探索"]["C2"]["高−低 平均差"]["差"]; hB = J["段"]["確認"]["C2"]["高−低 平均差"]["差"]
    SAME["C2（高−低 A 平均差）"] = {"探索／確認／早年": [hA, hB, J["段"]["早年"]["C2"]["高−低 平均差"]["差"]], "兩段同號": bool(np.sign(hA) == np.sign(hB))}
    J["兩段同向"] = SAME
    log("[兩段同向] " + json.dumps(SAME, ensure_ascii=False, default=float))
    json.dump(J, open(os.path.join(OUT, "ext.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=lambda v: (None if (isinstance(v, float) and not np.isfinite(v)) else (v.item() if hasattr(v, "item") else str(v))))
    pd.DataFrame(TB).to_csv(os.path.join(OUT, "ext_table.csv"), index=False, float_format="%.6g")
    log(f"[完成] {time.time() - T0:.0f}s ⇒ {OUT}")


if __name__ == "__main__":
    main()
