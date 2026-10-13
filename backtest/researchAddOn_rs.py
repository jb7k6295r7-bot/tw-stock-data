# -*- coding: utf-8 -*-
"""漲多加碼：外部 AI 第二批建議 4 項（相對強度 RS、營收加速、h×漲幅九宮格、觸發日 K 棒）初測——只看「加碼那一份」（A）——回測線計算子代理。
⛔ 只計算：不 commit、不改既有程式與結果夾；描述性「初測」、⛔ 不計 N、⛔ 不判定；用語「假訊號」；⛔ 不給買賣建議。
⛔ 加權指數讀私有庫 ~/us-stock-data（唯讀）；本結果夾 ⛔ 不放任何指數值、指數報酬或「個股減指數」的逐筆數值（只放三分位標籤／布林）。
⚠ 這 400 筆加碼已看過多次結果（researchAddOn、truetop、exit5、feat、cf、ext、mkt）⇒ 本件全是事後描述；項目 × 版本多 ⇒ 多重比較，只當「要不要正式登錄」的參考。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchAddOn_rs

═══ 讀法（S 標）═══
 S0 樣本 ＝ resultsAddOn/ext/ext_rows.csv.gz 的 400 筆（同 ext／mkt／cf／feat）；段 ＝ 探索 2017～2021、確認 2022～、早年 2005～2014；主窗 ＝ 探索＋確認
    每筆報酬 ＝ ext A_ret（ta 開盤加 1 份、原持股同日同價出場、扣 COST）；金額 ＝ ext 金額；群集 ＝ ext clu（世界|A 加碼月）
    決策日 t（收盤）；所有特徵只用 t 收盤以前（含 t）的資料；h ＝ feat h；g ＝ triggers g（closes[t] ÷ 買進價 − 1）
 S1 價：個股 ＝ 世界還原收盤（自己）、researchAddOn.market 快取 C（同業）；L 日報酬 ＝ C[t] ÷ C[t−L] − 1，需 t、t−L 皆有 K 棒有收盤且 [t−L＋1, t] 無壞根
    加權指數 ＝ ~/us-stock-data/data/macro/twse_taiex.csv 收盤（價格指數、不含息）對到世界日曆；0050 ＝ 世界 bench（還原收盤，含息）
 S2 項目（⛔ 方向事前定：數值越大／條件成立 ＝ 「留下」較好；⛔ 切點只用探索段；⛔ 不調參）
   1a 對大盤：RSX_TX60／RSX_TX20 ＝ 個股 60／20 日報酬 − 加權同期報酬；RSX_E60／RSX_E20 ＝ 對 0050；
      RSNH_TX／RSNH_E ＝ RS 線（個股 ÷ 指數）在 t 是近 60 根（t−59…t，全有效、窗內無壞根）的最高（≥ 最大值 − 1e−12）
   1b 對同產業：產業 ＝ industry_pit（researchIndRev_prereg.PIT，t 當天，pit 版；無 pit ⇒ 營收彙總表後備）；同業 ＝ 快取全部股票中 t 當天同產業、L 日報酬有效者（不含自己）
      INDX20／INDX60 ＝ 個股 L 日報酬 − 同業等權平均；INDP20／INDP60 ＝ 個股在同業中的百分位（同業比自己低的比例，同值算半）；同業 ＜ 5 檔 ⇒ 缺
      INDRK20 ＝ 該產業本身 20 日報酬（成員等權，含自己）在全市場產業（成員 ≥ 5）中的百分位（0 最弱、1 最強）
      另：2×2 描述（產業強 ＝ INDRK20 ＞ 探索段中位 × 個股贏同業較多 ＝ INDX20 ＞ 探索段中位）
      （事後註：原寫 INDX20 ＞ 0，第一次跑完見「個股輸同業」格 0 筆〔觸發時幾乎每筆都贏同業〕⇒ 改用探索段中位；另報 INDX20 ＞ 0 比例）
   2  營收加速（可得日規則同 researchExit5.avail_pos：≤2025-12 期次月 10 日後、≥2026-01 期次月 15 日後；A ≤ t 的最後一期 p）：
      REVACC3 ＝ YoY_p ＞ YoY_{p−1} ＞ YoY_{p−2}（三期須連續月份、YoY 皆有值）；REVACCD ＝ YoY_p − mean(YoY_{p−1..p−3}) ＞ 0（四期連續）
      YoY ＝ 當月營收 ÷ 去年當月營收 − 1（同 researchExit5.rev_events）
   3  九宮格：h、g 各以探索段三分位切 ⇒ 9 格；探索段（格內 ≥ 10 筆）A 平均最高格 ＝ 最佳格、最低格 ＝ 最差格（⚠ 方向由探索段資料挑）
      GRID_去最差 ＝ 留下「非最差格」；GRID_只最佳 ＝ 留下「最佳格」；另報四角交互 DiD ＝ (h高,g高) − (h高,g低) − (h低,g高) ＋ (h低,g低)
   4  觸發日 K 棒 KBAR ＝ 原始收盤 ≥ 原始最高 × 0.97 且 收 ＞ 開 且 1 ≤ t 量 ÷ 前 20 根有效 K 棒均量 ≤ 3（同 ext：量 ＝ 原始成交股數）
   連續項：探索段三分位 ⇒ 「排除」＝ 最低三分位、「留下」＝ 中＋高；另報 高三分位 − 低三分位；二元項：留下 ＝ 成立
 S3 每項每段報：留下／排除 各組 筆數、平均、中位、賺錢比例、賠＞15% 比例、總損益（Σ 金額 × r）；
      ① 總損益差 ＝ −Σ_排除 金額 × r（月群集 bootstrap 總和 CI）；③ 留下平均 − 排除平均（兩組共用月群集重抽 CI）；bootstrap 5000 次
      單邊打亂 p ＝ 該段內（特徵有值者）把 r 打亂 5000 次，③ 打亂值 ≥ 實際值的比例（方向 ＝ 事前定的「留下 ＞ 排除」）
      族系 p（探索、確認各一）＝ 同一組打亂（全段事件一起打亂 r）下，所有事前定方向的項目（九宮格除外）③ 的最大值 ≥ 該項實際 ③ 的比例
    兩段同向 ＝ ③ 在探索、確認兩段皆 ＞ 0（另列 ① 皆 ＞ 0）；⛔ 不判定
 S4 疊加 MA20：只在 ext G3a_多頭（加權收盤 ＞ 含 t 的 20 日均）＝ True 的事件裡，用同一切點再做 S3（① 的基準改為「只用 MA20」）；
    另報各項「留下」比例在 MA20 站上／未站上兩組的差（看兩者重疊多少）
輸出 backtest/resultsAddOn/rs/：rs.json、rs_table.csv、rs_grid.csv、rs_rows.csv.gz（加權指數相關只有標籤／布林）、run.log
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
from backtest import researchAddOn_ext as EXT                 # noqa: E402
from backtest import researchExit5 as EX5                     # noqa: E402
from backtest import researchIndRev_prereg as PRE             # noqa: E402

OUT = "backtest/resultsAddOn/rs"
AO_OUT = "backtest/resultsAddOn"
TAIEX = os.path.expanduser("~/us-stock-data/data/macro/twse_taiex.csv")
IND_DATA = os.path.expanduser("~/crashwork/tw_283eec12b2bc/data")
SEED = 20261015
NPERM = 5000
MINPEER = 5
MINCELL = 10
SEGN = ("探索", "確認", "主窗", "早年")

# (欄, 名稱, 型, 組)：c ＝ 連續（三分位，排除最低）、b ＝ 二元（留下 ＝ 成立）
ITEMS = [("RSX_TX60", "1a 個股60日報酬 − 加權60日", "c", "1a"), ("RSX_TX20", "1a 個股20日報酬 − 加權20日", "c", "1a"),
         ("RSNH_TX", "1a RS線(÷加權)創60日新高", "b", "1a"),
         ("RSX_E60", "1a 個股60日報酬 − 0050 60日", "c", "1a"), ("RSX_E20", "1a 個股20日報酬 − 0050 20日", "c", "1a"),
         ("RSNH_E", "1a RS線(÷0050)創60日新高", "b", "1a"),
         ("INDX20", "1b 個股20日 − 同業等權", "c", "1b"), ("INDX60", "1b 個股60日 − 同業等權", "c", "1b"),
         ("INDP20", "1b 同業內20日報酬百分位", "c", "1b"), ("INDP60", "1b 同業內60日報酬百分位", "c", "1b"),
         ("INDRK20", "1b 產業本身20日報酬在全產業的百分位", "c", "1b"),
         ("REVACC3", "2 營收年增連3期遞增", "b", "2"), ("REVACCD", "2 最近年增 − 前3期平均 ＞ 0", "b", "2"),
         ("KBAR", "4 觸發日強K（收≥高×0.97、紅K、量1～3倍）", "b", "4")]
GRID_ITEMS = [("GRID_去最差", "3 九宮格：排除探索段最差格"), ("GRID_只最佳", "3 九宮格：只留探索段最佳格")]
TXCOLS = ("RSX_TX60", "RSX_TX20")      # 含加權指數報酬的數值 ⇒ 不寫逐筆數值


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def jdef(v):
    if isinstance(v, (float, np.floating)):
        return None if not np.isfinite(v) else float(v)
    if hasattr(v, "item"):
        return v.item()
    return str(v)


def seg(R, sg):
    return R[R["段"].isin(("探索", "確認"))] if sg == "主窗" else R[R["段"] == sg]


def tercile_cut(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return list(np.unique(np.quantile(x, [1 / 3, 2 / 3], method="linear")))


def tercile_lab(v, e):
    v = np.asarray(v, float); o = np.full(len(v), np.nan); ok = np.isfinite(v)
    o[ok] = np.searchsorted(np.asarray(e), v[ok], side="left")     # v ≤ e1 ⇒ 0；e1 < v ≤ e2 ⇒ 1；＞ e2 ⇒ 2
    return o


def grp(r, amt):
    r = np.asarray(r, float); amt = np.asarray(amt, float)
    if not len(r):
        return {"筆": 0}
    return {"筆": int(len(r)), "平均": float(r.mean()), "中位": float(np.median(r)), "賺錢比例": float((r > 0).mean()),
            "賠超過15比例": float((r < -0.15).mean()), "總損益": float(np.sum(amt * r))}


def perm_p(r, k, rng, n=NPERM):
    """單邊：留下平均 − 排除平均 的打亂分布 ≥ 實際值的比例。"""
    r = np.asarray(r, float); k = np.asarray(k, bool)
    if k.sum() < 2 or (~k).sum() < 2:
        return None
    obs = r[k].mean() - r[~k].mean()
    P = np.argsort(rng.random((n, len(r))), axis=1)
    rp = r[P]
    nul = rp[:, k].mean(1) - rp[:, ~k].mean(1)
    return float((nul >= obs - 1e-12).mean())


def evalk(s, keep, rng):
    """keep：與 s 對齊的 float（1／0／NaN）。"""
    keep = np.asarray(keep, float); ok = np.isfinite(keep)
    ss = s[ok]; k = keep[ok].astype(bool)
    r = ss["A_ret"].to_numpy(float); amt = ss["金額"].to_numpy(float); c = ss["clu"].to_numpy()
    o = {"事件數": int(len(ss)), "缺": int((~ok).sum()), "留下筆": int(k.sum()), "留下比例": float(k.mean()) if len(k) else None}
    o["留下"] = grp(r[k], amt[k]); o["排除"] = grp(r[~k], amt[~k])
    o["總損益A（有值事件）"] = float(np.sum(amt * r))
    if len(ss) >= 2:
        b1 = EXT.boot(-(amt * r) * (~k), c, rng, "sum"); o["①總損益差"] = b1["值"]; o["①CI"] = b1["CI95"]
    else:
        o["①總損益差"] = None; o["①CI"] = [None, None]
    if k.sum() > 1 and (~k).sum() > 1:
        b3 = EXT.boot_diff2(r[k], c[k], r[~k], c[~k], rng)
        o["③留下減排除"] = b3["差"]; o["③CI"] = b3["CI95"]
        o["中位差"] = float(np.median(r[k]) - np.median(r[~k]))
        o["賺錢比例差"] = float((r[k] > 0).mean() - (r[~k] > 0).mean())
        o["單邊打亂p"] = perm_p(r, k, rng)
    else:
        o["③留下減排除"] = None; o["③CI"] = [None, None]; o["中位差"] = None; o["賺錢比例差"] = None; o["單邊打亂p"] = None
    return o


def boot_did(r, cell, clu, rng, nb=5000):
    """四角 DiD ＝ m(2,2) − m(2,0) − m(0,2) ＋ m(0,0)；cell ＝ 'hi,gi' 字串；月群集重抽。"""
    corners = ("2,2", "2,0", "0,2", "0,0"); sg = (1, -1, -1, 1)
    df = pd.DataFrame({"r": r, "c": cell, "m": clu})
    df = df[df["c"].isin(corners)]
    if any((df["c"] == cc).sum() == 0 for cc in corners):
        return {"DiD": None, "CI95": [None, None], "四角筆數": [int((df["c"] == cc).sum()) for cc in corners]}
    months = df["m"].unique(); mix = {m: i for i, m in enumerate(months)}; G = len(months)
    S = np.zeros((4, G)); N = np.zeros((4, G))
    for j, cc in enumerate(corners):
        q = df[df["c"] == cc]
        ii = np.array([mix[m] for m in q["m"]])
        S[j] = np.bincount(ii, weights=q["r"].to_numpy(float), minlength=G); N[j] = np.bincount(ii, minlength=G)
    v = float(sum(s_ * S[j].sum() / N[j].sum() for j, s_ in enumerate(sg)))
    bs = []
    for _ in range(nb):
        ix = rng.integers(G, size=G)
        n_ = N[:, ix].sum(1)
        if (n_ > 0).all():
            bs.append(sum(s_ * S[j, ix].sum() / n_[j] for j, s_ in enumerate(sg)))
    return {"DiD": v, "CI95": [float(np.quantile(bs, .025)), float(np.quantile(bs, .975))],
            "四角筆數": [int((df["c"] == cc).sum()) for cc in corners]}


def main():
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    R = pd.read_csv(os.path.join(AO_OUT, "ext", "ext_rows.csv.gz"), dtype={"sid": str},
                    usecols=["世界", "策略", "sid", "tb", "格", "t", "ta", "段", "金額", "市場", "加碼月", "A_ret", "G3a_多頭", "clu", "sb"])
    assert len(R) == 400
    F = pd.read_csv(os.path.join(AO_OUT, "feat", "feat_rows.csv.gz"), dtype={"sid": str}, usecols=["世界", "策略", "sid", "tb", "格", "h", "淨報酬"])
    TR = pd.read_csv(os.path.join(AO_OUT, "triggers.csv.gz"), dtype={"sid": str})
    TR = TR[TR["結果"] == "加碼"][["世界", "策略", "sid", "tb", "格", "t", "h", "g"]].rename(columns={"t": "t_tr", "h": "h_tr"})
    K = ["世界", "策略", "sid", "tb", "格"]
    R = R.merge(F, on=K, how="left", validate="1:1").merge(TR, on=K, how="left", validate="1:1")
    gates = {"A_ret vs feat 淨報酬 最大差": float(np.max(np.abs(R["A_ret"] - R["淨報酬"]))),
             "t vs triggers t 不同筆": int((R["t"] != R["t_tr"]).sum()), "h vs triggers h 不同筆": int((R["h"] != R["h_tr"]).sum()),
             "g 缺": int(R["g"].isna().sum())}
    R["G3a_多頭"] = R["G3a_多頭"].astype(bool)
    WS = AO.worlds(log, 1)
    from backtest import universe_gate as UG
    UG.set_gate_v2(True)
    MW = {}; HBW = {}; X = None
    for wn in ("主", "早年"):
        hs = sorted(set(R.loc[R["世界"] == wn, "sid"]))
        M, HB, X, minfo = AO.market(wn, WS[wn], X, log, hs)
        MW[wn] = M; HBW[wn] = HB
    # 加權指數（私有庫、唯讀、只在記憶體）
    tx = pd.read_csv(TAIEX, dtype={"date": str}); tx["date"] = pd.to_datetime(tx["date"])
    tx = tx.drop_duplicates("date").set_index("date")["close"].astype(float).sort_index()
    TXW = {wn: tx.reindex(W["cal"]).to_numpy(float) for wn, W in WS.items()}
    # 閘：G3a 重算
    g3 = []
    for w, t in zip(R["世界"], R["t"]):
        s_ = TXW[w]; t = int(t)
        g3.append(bool(t >= 19 and np.isfinite(s_[t - 19:t + 1]).all() and s_[t] > s_[t - 19:t + 1].mean()))
    gates["G3a 重算 vs ext 不同筆"] = int((np.array(g3) != R["G3a_多頭"].to_numpy()).sum())
    log(f"[閘] {gates}")
    if gates["A_ret vs feat 淨報酬 最大差"] > 1e-9 or gates["t vs triggers t 不同筆"] or gates["h vs triggers h 不同筆"] or gates["g 缺"] or gates["G3a 重算 vs ext 不同筆"]:
        raise SystemExit("⛔ 閘不過")
    # 產業
    rv_, rl_, cat, mk_, nf_, nr_ = PRE.load_rev(IND_DATA); PIT = PRE.PIT(IND_DATA, cat)
    # 營收（同 feat：researchExit5.load_revenue(W["data"])）
    REVW = {}
    for wn, W in WS.items():
        rev, rly, rinf = EX5.load_revenue(W["data"]); AV = EX5.avail_pos(list(rev.index), W["cal"])
        REVW[wn] = (rev, rly, AV, rinf)
    info = {"營收檔": {wn: v[3] for wn, v in REVW.items()}, "加權指數 世界日曆缺值（事件 t−60…t 窗內）": 0}
    # 同業：每個 (世界, t) 一次
    POPIND = {}
    for wn in ("主", "早年"):
        M = MW[wn]; C, BAR, BAD = M["C"], M["BAR"], M["BAD"]; S_, n = M["S"], M["n"]
        Z = __import__("pickle").load(open(os.path.join(AO.RLU_WORK, f"world_{'main' if wn == '主' else 'early'}.pkl"), "rb"))
        sids = list(Z["sids"]); del Z
        CB = np.zeros((S_, n + 1), np.int32); CB[:, 1:] = np.cumsum(BAD, axis=1)
        okC = BAR & np.isfinite(C)
        cal = WS[wn]["cal"]
        for t in sorted(set(R.loc[R["世界"] == wn, "t"].astype(int))):
            d = cal[t]
            live = np.flatnonzero(okC[:, t])
            ind = {}
            for i in live:
                nm = PIT.at(sids[i], d, "pit")[0]
                if nm:
                    ind[i] = nm
            rets = {}
            for L in (20, 60):
                ii = np.array([i for i in ind if t - L >= 0 and okC[i, t - L] and CB[i, t + 1] - CB[i, t - L + 1] == 0], int)
                rets[L] = dict(zip([sids[i] for i in ii], C[ii, t] / C[ii, t - L] - 1.0))
            POPIND[(wn, t)] = ({sids[i]: nm for i, nm in ind.items()}, rets)
        log(f"[同業 {wn}] 完成 {len([k for k in POPIND if k[0] == wn])} 個決策日")
    # 逐筆
    rows = []; RAW = {}; srcc = {}
    nmiss_tx = 0
    for r in R.to_dict("records"):
        wn, sid, t = r["世界"], r["sid"], int(r["t"])
        W = WS[wn]; cal = W["cal"]; n = len(cal)
        cl = np.asarray(W["closes"][sid][:n], float)
        bar, bad = HBW[wn][sid]; bar = np.asarray(bar[:n], bool); bad = np.asarray(bad[:n], bool)
        BADC = np.r_[0, np.cumsum(bad)]; okb = bar & np.isfinite(cl)
        txs = TXW[wn]; b = np.asarray(W["bench"], float)
        o = {}

        def ret(L):
            if t - L < 0 or not (okb[t] and okb[t - L]) or BADC[t + 1] - BADC[t - L + 1] > 0:
                return np.nan
            return cl[t] / cl[t - L] - 1.0
        r20, r60 = ret(20), ret(60)
        for L, rr in ((20, r20), (60, r60)):
            tr_ = txs[t] / txs[t - L] - 1.0 if np.isfinite(txs[t]) and np.isfinite(txs[t - L]) else np.nan
            br_ = b[t] / b[t - L] - 1.0 if np.isfinite(b[t]) and np.isfinite(b[t - L]) else np.nan
            o[f"RSX_TX{L}"] = rr - tr_; o[f"RSX_E{L}"] = rr - br_
        # RS 線 60 日新高
        w_ = np.arange(t - 59, t + 1)
        okw = (t >= 59) and okb[w_].all() and (BADC[t + 1] - BADC[t - 59 + 1] == 0)
        for nm_, ix_ in (("TX", txs), ("E", b)):
            if okw and np.isfinite(ix_[w_]).all():
                rs = cl[w_] / ix_[w_]
                o[f"RSNH_{nm_}"] = float(rs[-1] >= rs.max() - 1e-12)
            else:
                o[f"RSNH_{nm_}"] = np.nan
                if nm_ == "TX" and okw:
                    nmiss_tx += 1
        # 同業
        indmap, rets = POPIND[(wn, t)]
        my, src = PIT.at(sid, cal[t], "pit"); srcc[src] = srcc.get(src, 0) + 1
        o["產業"] = my
        for L, rr in ((20, r20), (60, r60)):
            if my is None or not np.isfinite(rr):
                o[f"INDX{L}"] = np.nan; o[f"INDP{L}"] = np.nan; o[f"同業數{L}"] = 0; continue
            peers = np.array([v for s2, v in rets[L].items() if s2 != sid and indmap.get(s2) == my], float)
            o[f"同業數{L}"] = int(len(peers))
            if len(peers) < MINPEER:
                o[f"INDX{L}"] = np.nan; o[f"INDP{L}"] = np.nan; continue
            o[f"INDX{L}"] = rr - peers.mean()
            o[f"INDP{L}"] = float(((peers < rr).sum() + 0.5 * (peers == rr).sum()) / len(peers))
        # 產業本身 20 日在全產業的百分位
        byind = {}
        for s2, v in rets[20].items():
            nm2 = indmap.get(s2)
            if nm2:
                byind.setdefault(nm2, []).append(v)
        im = {k_: float(np.mean(v)) for k_, v in byind.items() if len(v) >= MINPEER}
        if my in im and len(im) >= 2:
            others = np.array([v for k_, v in im.items() if k_ != my]); x_ = im[my]
            o["INDRK20"] = float(((others < x_).sum() + 0.5 * (others == x_).sum()) / len(others)); o["產業數"] = len(im)
        else:
            o["INDRK20"] = np.nan; o["產業數"] = len(im)
        # 營收加速
        rev, rly, AV, _ = REVW[wn]
        o["REVACC3"] = np.nan; o["REVACCD"] = np.nan; o["營收最近期"] = None
        if sid in rev.columns:
            per = list(rev.index); rv = rev[sid].to_numpy(float); rl = rly[sid].to_numpy(float)
            av = [k_ for k_, p in enumerate(per) if AV[p] <= t and np.isfinite(rv[k_])]
            if av:
                k0 = av[-1]; o["營收最近期"] = per[k0]

                def yoy(k_):
                    return rv[k_] / rl[k_] - 1.0 if (k_ >= 0 and np.isfinite(rv[k_]) and np.isfinite(rl[k_]) and rl[k_] > 0) else np.nan

                def consec(k_, m):
                    if k_ - m + 1 < 0:
                        return False
                    ps = per[k_ - m + 1:k_ + 1]
                    return all(PRE.mshift(ps[j], 1) == ps[j + 1] for j in range(len(ps) - 1))
                y = [yoy(k0 - j) for j in range(4)]
                if consec(k0, 3) and np.isfinite(y[:3]).all():
                    o["REVACC3"] = float(y[0] > y[1] > y[2])
                if consec(k0, 4) and np.isfinite(y).all():
                    o["REVACCD"] = float(y[0] - np.mean(y[1:4]) > 0)
                    o["營收年增差"] = y[0] - np.mean(y[1:4])
        # K 棒
        key = (wn, sid)
        if key not in RAW:
            RAW[key] = EXT.load_raw(W["data"], sid, cal)
        rw = RAW[key]
        ro, rh, rc = rw["open"].to_numpy(float)[t], rw["high"].to_numpy(float)[t], rw["close"].to_numpy(float)[t]
        vol = rw["volume"].to_numpy(float)
        vb = np.flatnonzero(okb[:n]); vvb = vb[np.isfinite(vol[vb])]
        j = int(np.searchsorted(vvb, t))
        p20 = vvb[j - 20:j] if j >= 20 else None
        if p20 is None or not np.isfinite([ro, rh, rc, vol[t]]).all():
            o["KBAR"] = np.nan; o["KB_收近高"] = np.nan; o["KB_紅K"] = np.nan; o["KB_量1到3倍"] = np.nan; o["KB_量倍"] = np.nan
        else:
            vr = vol[t] / vol[p20].mean()
            a1 = rc >= 0.97 * rh; a2 = rc > ro; a3 = 1.0 <= vr <= 3.0
            o["KB_收近高"] = float(a1); o["KB_紅K"] = float(a2); o["KB_量1到3倍"] = float(a3); o["KB_量倍"] = vr
            o["KBAR"] = float(a1 and a2 and a3)
        rows.append(o)
    FE = pd.DataFrame(rows, index=R.index)
    R = pd.concat([R, FE], axis=1)
    info["產業來源（事件股）"] = srcc
    info["RS 線窗內個股有效但加權缺"] = nmiss_tx
    info["缺值筆數"] = {k: int(R[k].isna().sum()) for k, _, _, _ in ITEMS}
    info["同業數中位（20日）"] = float(R["同業數20"].median()); info["產業數中位"] = float(R["產業數"].median())
    # ── 切點（探索段）
    E = R[R["段"] == "探索"]
    CUT = {}
    for k, nm, typ, _ in ITEMS:
        if typ == "c":
            CUT[k] = tercile_cut(E[k])
            R[k + "_三分"] = tercile_lab(R[k], CUT[k])
            R[k + "_keep"] = np.where(R[k + "_三分"].isna(), np.nan, (R[k + "_三分"] > 0).astype(float))
        else:
            R[k + "_keep"] = R[k].astype(float)
    # 九宮格
    CUT["h"] = tercile_cut(E["h"]); CUT["g"] = tercile_cut(E["g"])
    R["h3"] = tercile_lab(R["h"], CUT["h"]); R["g3"] = tercile_lab(R["g"], CUT["g"])
    R["cell"] = R["h3"].astype(int).astype(str) + "," + R["g3"].astype(int).astype(str)
    E = R[R["段"] == "探索"]
    cm = E.groupby("cell")["A_ret"].agg(["mean", "size"])
    cm_ok = cm[cm["size"] >= MINCELL]
    best = cm_ok["mean"].idxmax(); worst = cm_ok["mean"].idxmin()
    R["GRID_去最差_keep"] = (R["cell"] != worst).astype(float)
    R["GRID_只最佳_keep"] = (R["cell"] == best).astype(float)
    J = {"時間": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M") + "（台北）",
         "性質": "初測（描述性）；⛔ 不計 N、⛔ 不判定；只當是否值得正式登錄的參考",
         "讀法": __doc__.split("═══ 讀法（S 標）═══")[1].split("輸出")[0].strip(), "閘": gates, "資訊": info,
         "切點（探索段）": {k: v for k, v in CUT.items() if k not in TXCOLS}, "九宮格 探索段最佳／最差格（h三分,g三分；0 低 2 高）": [best, worst]}
    J["切點（探索段）"]["RSX_TX60／RSX_TX20"] = "（含加權指數報酬，數值不寫出）"
    # ── 主表
    rng = np.random.default_rng(SEED)
    ALL = [(k, nm, typ, gp) for k, nm, typ, gp in ITEMS] + [(k, nm, "g", "3") for k, nm in GRID_ITEMS]
    TB = []; RES = {}
    for ov in ("全部", "疊加MA20"):
        for sg in SEGN:
            s = seg(R, sg)
            if ov == "疊加MA20":
                s = s[s["G3a_多頭"]]
            for k, nm, typ, gp in ALL:
                o = evalk(s, s[k + "_keep"], rng)
                if typ == "c":
                    lab = s[k + "_三分"].to_numpy(float); r_ = s["A_ret"].to_numpy(float)
                    hi_, lo_ = lab == 2, lab == 0
                    o["三分位"] = {str(j): grp(r_[lab == j], s["金額"].to_numpy(float)[lab == j]) for j in (0, 1, 2)}
                    if hi_.sum() > 1 and lo_.sum() > 1:
                        c_ = s["clu"].to_numpy()
                        b_ = EXT.boot_diff2(r_[hi_], c_[hi_], r_[lo_], c_[lo_], rng)
                        o["高三分減低三分"] = b_["差"]; o["高三分減低三分_CI"] = b_["CI95"]
                RES[(ov, sg, k)] = o
                TB.append({"疊加": ov, "段": sg, "項": k, "名稱": nm, "組": gp, "事件數": o["事件數"], "缺": o["缺"], "留下筆": o["留下筆"],
                           "留下比例": o["留下比例"],
                           "留下_平均": o["留下"].get("平均"), "留下_中位": o["留下"].get("中位"), "留下_賺錢比例": o["留下"].get("賺錢比例"),
                           "留下_賠超過15比例": o["留下"].get("賠超過15比例"), "留下_總損益": o["留下"].get("總損益"),
                           "排除_筆": o["排除"]["筆"], "排除_平均": o["排除"].get("平均"), "排除_中位": o["排除"].get("中位"),
                           "排除_賺錢比例": o["排除"].get("賺錢比例"), "排除_賠超過15比例": o["排除"].get("賠超過15比例"), "排除_總損益": o["排除"].get("總損益"),
                           "③留下減排除": o["③留下減排除"], "③CI低": o["③CI"][0], "③CI高": o["③CI"][1],
                           "①總損益差": o["①總損益差"], "①CI低": o["①CI"][0], "①CI高": o["①CI"][1],
                           "中位差": o["中位差"], "賺錢比例差": o["賺錢比例差"], "單邊打亂p": o["單邊打亂p"],
                           "高三分減低三分": o.get("高三分減低三分"), "高三分減低三分_CI低": (o.get("高三分減低三分_CI") or [None, None])[0],
                           "高三分減低三分_CI高": (o.get("高三分減低三分_CI") or [None, None])[1]})
        log(f"[主表 {ov}] 完成")
    # ── 族系 p（探索、確認；全部 與 疊加MA20；九宮格除外）
    FAM = {}
    keys = [k for k, _, _, _ in ITEMS]
    for ov in ("全部", "疊加MA20"):
        for sg in ("探索", "確認"):
            s = seg(R, sg)
            if ov == "疊加MA20":
                s = s[s["G3a_多頭"]]
            r_ = s["A_ret"].to_numpy(float)
            P = np.argsort(rng.random((NPERM, len(r_))), axis=1); rp = r_[P]
            MX = np.full(NPERM, -np.inf); obs = {}
            for k in keys:
                kp = s[k + "_keep"].to_numpy(float); ok = np.isfinite(kp); kk = kp[ok].astype(bool)
                if kk.sum() < 2 or (~kk).sum() < 2:
                    continue
                q = rp[:, ok]
                MX = np.maximum(MX, q[:, kk].mean(1) - q[:, ~kk].mean(1))
                obs[k] = float(r_[ok][kk].mean() - r_[ok][~kk].mean())
            FAM[f"{ov}|{sg}"] = {k: float((MX >= v - 1e-12).mean()) for k, v in obs.items()}
            FAM[f"{ov}|{sg}|打亂下最大③ 中位／p95"] = [float(np.median(MX)), float(np.quantile(MX, .95))]
    J["族系p"] = FAM
    # ── 兩段同向
    SAME = {}
    for k, nm, typ, gp in ALL:
        z = {}
        for ov in ("全部", "疊加MA20"):
            e, c, y = RES[(ov, "探索", k)], RES[(ov, "確認", k)], RES[(ov, "早年", k)]
            z[ov] = {"③ 探索／確認／早年": [e["③留下減排除"], c["③留下減排除"], y["③留下減排除"]],
                     "③ 兩段皆＞0": bool((e["③留下減排除"] or -1) > 0 and (c["③留下減排除"] or -1) > 0),
                     "① 探索／確認／早年": [e["①總損益差"], c["①總損益差"], y["①總損益差"]],
                     "① 兩段皆＞0": bool((e["①總損益差"] or -1) > 0 and (c["①總損益差"] or -1) > 0),
                     "單邊打亂p 探索／確認／早年": [e["單邊打亂p"], c["單邊打亂p"], y["單邊打亂p"]],
                     "族系p 探索／確認": [FAM.get(f"{ov}|探索", {}).get(k), FAM.get(f"{ov}|確認", {}).get(k)],
                     "留下比例 探索／確認／早年": [e["留下比例"], c["留下比例"], y["留下比例"]]}
        SAME[k] = {"名稱": nm, **z}
    J["兩段同向"] = SAME
    # ── 與 MA20 的重疊
    OVL = {}
    for k, nm, typ, gp in ALL:
        z = {}
        for sg in SEGN:
            s = seg(R, sg); kp = s[k + "_keep"]; m20 = s["G3a_多頭"]
            z[sg] = {"MA20 站上時留下比例": float(kp[m20].mean()) if m20.any() else None,
                     "MA20 未站上時留下比例": float(kp[~m20].mean()) if (~m20).any() else None}
        OVL[k] = z
    J["與MA20重疊（留下比例）"] = OVL
    # ── 九宮格
    GR = []
    for ov in ("全部", "疊加MA20"):
        for sg in SEGN:
            s = seg(R, sg)
            if ov == "疊加MA20":
                s = s[s["G3a_多頭"]]
            for c_ in sorted(R["cell"].unique()):
                q = s[s["cell"] == c_]
                g_ = grp(q["A_ret"], q["金額"])
                GR.append({"疊加": ov, "段": sg, "格(h三分,g三分)": c_, **g_})
            J.setdefault("九宮格四角DiD", {})[f"{ov}|{sg}"] = boot_did(s["A_ret"].to_numpy(float), s["cell"].to_numpy(), s["clu"].to_numpy(), rng)
    pd.DataFrame(GR).to_csv(os.path.join(OUT, "rs_grid.csv"), index=False, float_format="%.6g")
    # ── 產業強 × 個股贏同業 2×2
    medrk = float(E["INDRK20"].median()); J["2x2 產業強切點（探索段 INDRK20 中位）"] = medrk
    medx = float(E["INDX20"].median()); J["2x2 個股贏同業切點（探索段 INDX20 中位）"] = medx
    J["產業 vs 個股 描述"] = {sg: {"INDX20 ＞ 0 比例": float((seg(R, sg)["INDX20"] > 0).mean()), "INDX60 ＞ 0 比例": float((seg(R, sg)["INDX60"] > 0).mean()),
                                  "INDP20 中位": float(seg(R, sg)["INDP20"].median()), "INDRK20 中位": float(seg(R, sg)["INDRK20"].median()),
                                  "INDRK20 ＞ 0.5 比例": float((seg(R, sg)["INDRK20"] > 0.5).mean())} for sg in SEGN}
    T22 = {}
    for sg in SEGN:
        s = seg(R, sg); ok = s["INDRK20"].notna() & s["INDX20"].notna(); s = s[ok]
        z = {}
        for a_, an in ((True, "產業強"), (False, "產業弱")):
            for b_, bn in ((True, "個股贏同業較多"), (False, "個股贏同業較少")):
                q = s[((s["INDRK20"] > medrk) == a_) & ((s["INDX20"] > medx) == b_)]
                z[f"{an}×{bn}"] = grp(q["A_ret"], q["金額"])
        T22[sg] = z
    J["產業強×個股贏同業 2x2"] = T22
    # ── K 棒分項描述
    KB = {}
    for sg in SEGN:
        s = seg(R, sg)
        KB[sg] = {c_: {"成立": grp(s.loc[s[c_] == 1, "A_ret"], s.loc[s[c_] == 1, "金額"]),
                       "不成立": grp(s.loc[s[c_] == 0, "A_ret"], s.loc[s[c_] == 0, "金額"])} for c_ in ("KB_收近高", "KB_紅K", "KB_量1到3倍")}
    J["K棒分項（描述）"] = KB
    J["多重比較註"] = (f"{len(ITEMS)} 項事前定方向 ＋ 2 項九宮格（方向由探索段挑）× 2（全部／疊加 MA20）＝ {2 * (len(ITEMS) + 2)} 個比較，"
                      "全在同一批已看過多次的 400 筆上；確認段單邊 p＜0.05 光靠運氣預期約 %.1f 個；九宮格探索段 p 因挑格而偏低、不可讀"
                      % (0.05 * 2 * (len(ITEMS) + 2)))
    pd.DataFrame(TB).to_csv(os.path.join(OUT, "rs_table.csv"), index=False, float_format="%.6g")
    # ── 逐筆（加權相關只寫標籤／布林）
    keep = ["世界", "策略", "sid", "tb", "格", "t", "ta", "段", "加碼月", "clu", "A_ret", "金額", "G3a_多頭", "h", "g", "h3", "g3", "cell", "產業", "產業數",
            "同業數20", "同業數60", "營收最近期", "KB_收近高", "KB_紅K", "KB_量1到3倍", "KB_量倍"]
    for k, _, typ, _ in ITEMS:
        if k not in TXCOLS:
            keep.append(k)
        if typ == "c":
            keep.append(k + "_三分")
        keep.append(k + "_keep")
    keep += ["GRID_去最差_keep", "GRID_只最佳_keep"]
    R[keep].to_csv(os.path.join(OUT, "rs_rows.csv.gz"), index=False, float_format="%.6g")
    json.dump(J, open(os.path.join(OUT, "rs.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=jdef)
    log(f"[完成] {time.time() - T0:.0f}s ⇒ {OUT}")


if __name__ == "__main__":
    main()
