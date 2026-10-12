# -*- coding: utf-8 -*-
"""漲多加碼：加碼那一份（跟原持股同日賣）會賺／會賠，加碼當下有沒有特徵分得出來——描述性特徵掃描（使用者 2026-10-13：「有什麼可能提高機率嗎？」）
——回測線計算子代理。⛔ 只計算：不 commit、不改既有程式與結果夾；描述性、⛔ 不計 N、⛔ 不判定；用語「假訊號」；⛔ 不給買賣建議。
⚠ 加碼已看過結果（researchAddOn、truetop、exit5）⇒ 本件全是事後描述，任何「看起來有差」都只是待驗的線索。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchAddOn_feat

═══ 讀法（F 標）═══
 F0 樣本 ＝ researchAddOn 主臂（加碼那份跟原持股同日同價賣）的唯一加碼：讀 resultsAddOn/exit5/exits.csv.gz（唯一 世界×策略×sid×tb×格；營飆已是 200 顆去重）
    淨報酬 ＝ S_價 ÷ 加碼價 − 1 − COST（0.585%）；賺 ＝ 淨報酬 ＞ 0；S 資料尾仍持有（S_出場日 空）⇒ 不算（照報筆數）
    同一筆持股（世界, 策略, sid, tb）A1、A2 都有 ⇒ 只算一次、取 A1（A1 觸發日 ≤ A2）；只有 A2 ⇒ 用 A2（g−q95 標缺）
    營量、營飆合併（同一檔同一 tb 兩策略都有 ⇒ 兩筆都留、出場不同；照報重疊筆數）
    段（依加碼日 ta）：主世界 探索 (523, 1711]、確認 (1712−1, 2835]（＝ researchAddOn segp，ta ∈ (x, y]）；早年世界 早年段；段外 ⇒ 不算（照報）
 F1 特徵（⛔ 只用決策日 t 收盤以前；t ＝ 加碼前一根）：
    h、g−q95（triggers.csv.gz 的 g、q；A1 列 q ＝ q95）、起漲點以來漲幅（researchYL_truetopT.anchor_pit(c, t, tb)；c ＝ 世界還原收盤）、
    近 5／20 日漲停天數（s5work F 表 lu_5、lu_20）、近 10 日注意次數 att_10、近 10 日處置天數 disp_10、t 當天處置中（s5work disp）：2011-01-03 前 ＝ 缺（s5work ATT_FIRST）、
    20 日均額倍數 ar_20（當日成交金額 ÷ 前 20 日均額；⚠ 用金額不用張數，除權息不失真）、ATR/價（exits ATR ÷ c[t]）、
    最近一期月營收年增與是否創 24 月新高（researchExit5.load_revenue／avail_pos／rev_events：可得日 A ≤ t 的最後一期；2026-01 期起次月 15 日後）、
    0050 在 60／200 日均之上、0050 近 20 日報酬（世界 bench ＝ 0050 還原收盤 ffill）、同一天同策略其他唯一持股觸發數（同世界同策略同 t 的其他加碼，含資料尾仍持有）、
    起漲特徵 N/14（surge_feat_daily 同一套 FEATS，直接讀 s5work Q 表〔建表與每日名單逐格相同，閘 G1〕）、產業大類（industry_pit pit 版＋營收彙總表後備，PRE.PIT，t 當天）、策略
    另列「執行時可見」：加碼日開盤跳空 ＝ 加碼價 ÷ c[t] − 1（⚠ t＋1 開盤，決策時看不到）
    s5work 的表（F、Q、disp）以日期對到接合日曆；該股 t 當天 s5work 沒有 K 棒 ⇒ 缺
 F2 分組：連續 ＝ 探索段三分位（⛔ 切點只用探索段；同值多 ⇒ 切點去重後組數變少）；二元 ＝ 兩組；產業 ＝ 大類（探索段 ＜ 10 筆的類併「其他」）
    每組報 筆數、賺錢比例、平均、中位（三段）；探索段「賺錢比例差」＝ 筆數 ≥ 10 的組中 最高 − 最低
    前 5 名 ＝ 探索段差最大的 5 個特徵；確認、早年 同方向 ＝ 探索段最高那組的賺錢比例 − 最低那組 在該段同號（⛔ 不重切）
    AUC（單變數，Mann-Whitney，同值算半）：值越大越會賺 ⇒ AUC ＞ 0.5；產業不算 AUC
 F3 多重比較（前 5 名另報確認、早年「同兩組」單邊打亂 p，方向 ＝ 探索段高組 ＞ 低組）：探索段把「賺／賠」標籤隨機打亂 2000 次（特徵、分組不變），每次算每個特徵的賺錢比例差與 |AUC−0.5| ⇒
    每個特徵的打亂 p、「光靠運氣預期有幾個特徵的差 ≥ 某值」、打亂下所有特徵中最大差的分佈（族系）
輸出 backtest/resultsAddOn/feat/：feat.json、feat_table.csv、feat_rows.csv.gz（逐筆特徵，供查核）
"""
from __future__ import annotations

import json
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import research11 as R                          # noqa: E402
from backtest import researchYL_truetopT as TTT               # noqa: E402
from backtest import researchExit5 as EX5                     # noqa: E402
from backtest import researchIndRev_prereg as PRE             # noqa: E402
from backtest.researchSurge6_overlap import FEATS             # noqa: E402

OUT = "backtest/resultsAddOn/feat"
AO_OUT = "backtest/resultsAddOn"
WORK = os.path.expanduser("~/addonwork")
S5 = os.path.expanduser("~/s5work")
ST_CAL = os.path.expanduser("~/evtdata/stitch_950ad26e12_b53f5540a8/data/meta/calendar_twse.csv")
IND_DATA = os.path.expanduser("~/crashwork/tw_283eec12b2bc/data")
COST = R.COST
NPERM = 2000
MINGRP = 10
SEED = 20261013
ELEC = {"半導體業", "光電業", "通信網路業", "資訊服務業", "電腦及週邊設備業", "數位雲端", "電子工業"}

# (欄, 名稱, 型)：c ＝ 連續（三分位）、b ＝ 二元、k ＝ 類別
FEAT = [("h", "已持有天數 h", "c"), ("gq", "g − q95（超過門檻幅度）", "c"), ("surge", "起漲點以來漲幅", "c"),
        ("lu5", "近 5 日漲停天數", "c"), ("lu20", "近 20 日漲停天數", "c"),
        ("att10", "近 10 日注意次數", "c"), ("disp10", "近 10 日處置天數", "c"), ("indisp", "t 當天處置中", "b"),
        ("ar20", "當日額 ÷ 前 20 日均額", "c"), ("atrp", "ATR20 ÷ 價", "c"),
        ("yoy", "最近一期月營收年增", "c"), ("hi24", "最近一期月營收創 24 月新高", "b"),
        ("m60", "0050 在 60 日均之上", "b"), ("m200", "0050 在 200 日均之上", "b"), ("m20r", "0050 近 20 日報酬", "c"),
        ("same", "同天同策略其他觸發數", "c"), ("n14", "起漲特徵 N/14", "c"), ("ind", "產業大類", "k"), ("strat", "策略（營飆＝1）", "b")]
EXEC = [("gap", "加碼日開盤跳空（t＋1 開盤，執行時才看得到）", "c")]
SEGN = ("探索", "確認", "早年")


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def big_cat(ind):
    if ind is None or ind == "":
        return None
    if "電子" in ind or ind in ELEC:
        return "電子"
    if "生技" in ind:
        return "生技醫療"
    if "金融" in ind:
        return "金融"
    return "傳產"


# ═════════════ 樣本 ═════════════
def sample(WS):
    ex = pd.read_csv(os.path.join(AO_OUT, "exit5", "exits.csv.gz"))
    tr = pd.read_csv(os.path.join(AO_OUT, "triggers.csv.gz"))
    tr = tr[tr["結果"] == "加碼"].copy()
    info = {"exits 列（唯一 加碼×格）": int(len(ex)), "triggers 加碼列": int(len(tr))}
    # 閘：exits 與 triggers 的 t、ta、h、加碼價一致
    m = ex.merge(tr, on=["世界", "策略", "sid", "tb", "格"], how="left", suffixes=("", "_tr"))
    bad = int(((m["t"] != m["t_tr"]) | (m["ta"] != m["ta_tr"]) | (m["h"] != m["h_tr"]) | (np.abs(m["加碼價"] / m["ep_a"] - 1) > 1e-9)).sum())
    info["閘 exits vs triggers 不一致列"] = bad
    if bad:
        raise SystemExit(f"⛔ exits vs triggers 不一致 {bad}")
    m["sid"] = m["sid"].astype(str)
    key = ["世界", "策略", "sid", "tb"]
    m["_c"] = (m["格"] != "A1").astype(int)
    both = m.groupby(key)["格"].nunique()
    info["A1、A2 都觸發（只算一次、取 A1）"] = int((both == 2).sum())
    d = m.sort_values(key + ["_c"]).drop_duplicates(key, keep="first").copy()
    info["只有 A2"] = int((d["格"] == "A2").sum())
    info["唯一持股（去重後）"] = int(len(d))
    # 段
    seg = []
    for w, ta in zip(d["世界"], d["ta"]):
        sp = WS[w]["segp"]; s_ = None
        for nm in (("探索", "確認") if w == "主" else ("早年",)):
            x, y = sp[nm]
            if x < ta <= y:
                s_ = nm
        seg.append(s_)
    d["段"] = seg
    info["段外（不算）"] = int(d["段"].isna().sum())
    d["淨報酬"] = d["S_價"] / d["加碼價"] - 1.0 - COST
    d["出場"] = d["S_出場日"].notna()
    info["資料尾仍持有（不算）"] = {s: int(((~d["出場"]) & (d["段"] == s)).sum()) for s in SEGN}
    ov = d.groupby(["世界", "sid", "tb"])["策略"].nunique()
    info["營量、營飆同一檔同一 tb 都加碼（兩筆都留）"] = int((ov == 2).sum())
    d["賺"] = (d["淨報酬"] > 0).astype(float)
    return d, tr, info


# ═════════════ 特徵 ═════════════
def features(d, tr, WS):
    n_ = len(d)
    F = {k: np.full(n_, np.nan) for k, _, _ in FEAT + EXEC}
    IND = [None] * n_
    # s5work
    uni = pd.read_csv(os.path.join(S5, "uni.csv"), dtype=str); six = {s: i for i, s in enumerate(uni["stock_id"])}
    bj = json.load(open(os.path.join(S5, "build.json"), encoding="utf-8")); FX = {c: i for i, c in enumerate(bj["特徵欄"])}
    scal = pd.to_datetime(pd.read_csv(ST_CAL)["date"]); sdix = {dd: k for k, dd in enumerate(scal)}
    S_, n5 = len(uni), len(scal)
    assert n5 == bj["日曆"][2]
    Fm = np.load(os.path.join(S5, "F.npy"), mmap_mode="r"); Qm = np.load(os.path.join(S5, "Q.npy"), mmap_mode="r")
    BARm = np.load(os.path.join(S5, "bar.npy"), mmap_mode="r"); DISPm = np.load(os.path.join(S5, "disp.npy"), mmap_mode="r")
    assert Fm.shape == (len(FX), S_, n5) and BARm.shape == (S_, n5), (Fm.shape, BARm.shape)
    ATT_FIRST = int(scal.searchsorted(pd.Timestamp("2011-01-03")))
    # 營收
    REVW = {}
    for wn, W in WS.items():
        rev, rly, rinf = EX5.load_revenue(W["data"]); AV = EX5.avail_pos(list(rev.index), W["cal"])
        REVW[wn] = (rev, rly, AV, rinf)
    rv_, rl_, cat, mk, nf, nr = PRE.load_rev(IND_DATA); PIT = PRE.PIT(IND_DATA, cat)
    # 同天觸發數（去重後的唯一加碼，含資料尾仍持有）
    t2 = tr.copy(); t2["sid"] = t2["sid"].astype(str); t2["_c"] = (t2["格"] != "A1").astype(int)
    t2 = t2.sort_values(["世界", "策略", "sid", "tb", "_c"]).drop_duplicates(["世界", "策略", "sid", "tb"])
    SAME = t2.groupby(["世界", "策略", "t"]).size().to_dict()
    miss5 = 0
    for i, r in enumerate(d.to_dict("records")):
        wn, sn, sid, tb, t = r["世界"], r["策略"], r["sid"], int(r["tb"]), int(r["t"])
        W = WS[wn]; cal = W["cal"]; n0 = len(cal)
        c = np.asarray(W["closes"][sid][:n0], float)
        ct = c[t]
        F["h"][i] = r["h"]
        F["gq"][i] = (r["g"] - r["q"]) if r["格"] == "A1" else np.nan
        a = TTT.anchor_pit(c, t, tb); F["surge"][i] = ct / c[a] - 1.0
        F["atrp"][i] = r["ATR"] / ct if np.isfinite(r["ATR"]) else np.nan
        F["gap"][i] = r["加碼價"] / ct - 1.0
        b = np.asarray(W["bench"], float)
        F["m60"][i] = float(b[t] > b[t - 59:t + 1].mean()) if t >= 59 else np.nan
        F["m200"][i] = float(b[t] > b[t - 199:t + 1].mean()) if t >= 199 else np.nan
        F["m20r"][i] = b[t] / b[t - 20] - 1.0 if t >= 20 else np.nan
        F["same"][i] = SAME.get((wn, sn, t), 1) - 1
        F["strat"][i] = float(sn == "營飆")
        # 營收（可得日 A ≤ t 的最後一期）
        rev, rly, AV, _ = REVW[wn]
        ev = EX5.rev_events(sid, rev, rly, AV, n0)
        last = [e for e in ev if e[0] <= t]
        if last:
            A_, yy, hi = last[-1]
            F["yoy"][i] = yy
            F["hi24"][i] = np.nan if hi is None else float(hi)
        # 產業
        IND[i] = big_cat(PIT.at(sid, cal[t], "pit")[0])
        # s5work
        si = six.get(sid); T = sdix.get(cal[t])
        if si is None or T is None or not bool(BARm[si, T]):
            miss5 += 1; continue
        F["lu5"][i] = Fm[FX["lu_5"], si, T]; F["lu20"][i] = Fm[FX["lu_20"], si, T]
        F["att10"][i] = Fm[FX["att_10"], si, T]; F["disp10"][i] = Fm[FX["disp_10"], si, T]
        F["indisp"][i] = float(DISPm[si, T]) if T >= ATT_FIRST else np.nan
        F["ar20"][i] = Fm[FX["ar_20"], si, T]
        F["n14"][i] = sum(int(Qm[FX[col], si, T] == code) for _, col, code in FEATS)
    for k in F:
        d[k] = F[k]
    d["ind"] = IND
    rinfo = {wn: v[3] for wn, v in REVW.items()}
    return d, {"s5work 沒有該股該日 K 棒（s5work 特徵缺）": miss5, "營收檔": rinfo, "產業資料": IND_DATA}


# ═════════════ 分組、AUC、打亂 ═════════════
def auc(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    n1 = int(y.sum()); n0 = int(len(y) - n1)
    if n1 == 0 or n0 == 0:
        return np.nan
    rk = pd.Series(x).rank(method="average").to_numpy()
    return float((rk[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def make_bins(k, typ, xe):
    """探索段值 ⇒ (標籤函式, 組名清單)。"""
    if typ == "b":
        return (lambda v: np.where(np.isfinite(v), v.astype(float), np.nan)), ["0（否）", "1（是）"], [0.0, 1.0]
    if typ == "k":
        return None, None, None
    xe = xe[np.isfinite(xe)]
    e = np.unique(np.quantile(xe, [1 / 3, 2 / 3], method="linear"))
    def lab(v, e=e):
        o = np.full(len(v), np.nan); ok = np.isfinite(v)
        o[ok] = np.searchsorted(e, v[ok], side="left")       # v ≤ e1 ⇒ 0；e1 < v ≤ e2 ⇒ 1；＞ e2 ⇒ 2
        return o
    names = []
    for j in range(len(e) + 1):
        lo = None if j == 0 else e[j - 1]; hi = None if j == len(e) else e[j]
        names.append(("≤ " + f"{hi:.4g}") if lo is None else (("＞ " + f"{lo:.4g}") if hi is None else f"{lo:.4g} ＜ x ≤ {hi:.4g}"))
    return lab, names, list(e)


def run():
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    WS = {wn: pickle.load(open(os.path.join(WORK, f"world_{wn}.pkl"), "rb")) for wn in ("主", "早年")}
    d, tr, sinfo = sample(WS)
    log(f"[樣本] {sinfo}")
    d, finfo = features(d, tr, WS)
    log(f"[特徵] {finfo}")
    d = d[d["段"].notna()].copy()
    U = d[d["出場"]].copy()                                       # 分析樣本
    rows_out = U[["世界", "策略", "sid", "tb", "格", "t", "ta", "段", "淨報酬", "賺"] + [k for k, _, _ in FEAT + EXEC]].copy()
    rows_out.to_csv(os.path.join(OUT, "feat_rows.csv.gz"), index=False, float_format="%.10g")
    NS = {s: {"筆": int((U["段"] == s).sum()), "營量": int(((U["段"] == s) & (U["策略"] == "營量")).sum()), "營飆": int(((U["段"] == s) & (U["策略"] == "營飆")).sum()),
              "賺錢比例": float(U.loc[U["段"] == s, "賺"].mean()), "淨報酬平均": float(U.loc[U["段"] == s, "淨報酬"].mean()),
              "淨報酬中位": float(U.loc[U["段"] == s, "淨報酬"].median())} for s in SEGN}
    log(f"[分析樣本] {NS}")
    # 閘：營量 A1 主世界主窗（不去重、不分段）賺錢比例 vs AddOn.json 必報
    AJ = json.load(open(os.path.join(AO_OUT, "AddOn.json"), encoding="utf-8"))
    ref = AJ["必報"]["營量·A1·主"]["淨報酬 ＞ 0 比例"]
    ex = pd.read_csv(os.path.join(AO_OUT, "exit5", "exits.csv.gz"))
    x0, y0 = WS["主"]["segp"]["主窗"]
    e_ = ex[(ex["世界"] == "主") & (ex["策略"] == "營量") & (ex["格"] == "A1") & ex["S_出場日"].notna() & (ex["tb"] >= x0) & (ex["tb"] <= y0)]
    mine = float(((e_["S_價"] / e_["加碼價"] - 1 - COST) > 0).mean())
    gate = {"營量 A1 主窗 淨報酬＞0 比例：本件": mine, "AddOn.json 必報": ref, "差": mine - ref}
    log(f"[閘] {gate}")
    E = U[U["段"] == "探索"]; yE = E["賺"].to_numpy()
    TAB = []; SUMM = {}; GIDX = {}; LABF = {}
    for k, nm, typ in FEAT + EXEC:
        if typ == "k":
            vc = E[k].value_counts(); keep = [c_ for c_ in vc.index if vc[c_] >= MINGRP]
            names = sorted(keep) + ["其他"]
            mp = {c_: j for j, c_ in enumerate(sorted(keep))}
            labf = lambda s, mp=mp, names=names: np.array([np.nan if v is None else mp.get(v, len(names) - 1) for v in s], float)
            edges = None
        else:
            lab, names, edges = make_bins(k, typ, E[k].to_numpy(float))
            labf = lambda s, lab=lab: lab(np.asarray(s, float))
        LABF[k] = (labf, names)
        sm = {"名稱": nm, "型": typ, "切點（探索段定）": edges, "組": names, "執行時才看得到": k in [z[0] for z in EXEC]}
        for s in SEGN:
            G = U[U["段"] == s]; g = labf(G[k].tolist() if typ == "k" else G[k])
            gr = {}
            for j, gn in enumerate(names):
                mm = g == j; z = G.loc[mm, "淨報酬"]
                rec = {"特徵": k, "名稱": nm, "段": s, "組序": j, "組": gn, "筆數": int(mm.sum()),
                       "賺錢比例": float(G.loc[mm, "賺"].mean()) if mm.any() else np.nan,
                       "淨報酬平均": float(z.mean()) if mm.any() else np.nan, "淨報酬中位": float(z.median()) if mm.any() else np.nan}
                TAB.append(rec); gr[gn] = {kk: rec[kk] for kk in ("筆數", "賺錢比例", "淨報酬平均", "淨報酬中位")}
            sm[s] = {"組": gr, "缺值筆": int(np.isnan(g).sum()),
                     "AUC": (auc(G[k].to_numpy(float), G["賺"].to_numpy()) if typ != "k" else None)}
            if s == "探索":
                GIDX[k] = g
        # 探索段 差、方向
        gr = sm["探索"]["組"]; ok = [gn for gn in names if gr[gn]["筆數"] >= MINGRP]
        if len(ok) >= 2:
            hi = max(ok, key=lambda gn: gr[gn]["賺錢比例"]); lo = min(ok, key=lambda gn: gr[gn]["賺錢比例"])
            sm["探索差"] = gr[hi]["賺錢比例"] - gr[lo]["賺錢比例"]; sm["高組"] = hi; sm["低組"] = lo
            for s in ("確認", "早年"):
                g2 = sm[s]["組"]
                if g2[hi]["筆數"] and g2[lo]["筆數"]:
                    df_ = g2[hi]["賺錢比例"] - g2[lo]["賺錢比例"]
                    sm[f"{s}差（同兩組）"] = df_; sm[f"{s}同方向"] = bool(df_ > 0)
                    sm[f"{s}兩組筆數"] = [g2[hi]["筆數"], g2[lo]["筆數"]]
                else:
                    sm[f"{s}差（同兩組）"] = None; sm[f"{s}同方向"] = None; sm[f"{s}兩組筆數"] = [g2[hi]["筆數"], g2[lo]["筆數"]]
        else:
            sm["探索差"] = None
        SUMM[k] = sm
    # 打亂（探索段；只用決策時可得的特徵進排名）
    rng = np.random.default_rng(SEED)
    keys = [k for k, _, _ in FEAT if SUMM[k]["探索差"] is not None]
    P = np.array([rng.permutation(yE) for _ in range(NPERM)]).T            # n × P
    NULLD = {}; NULLA = {}
    for k in keys:
        g = GIDX[k]; ng = len(SUMM[k]["組"]); rates = []
        for j in range(ng):
            mm = g == j
            if mm.sum() >= MINGRP:
                rates.append(P[mm].mean(0))
        R_ = np.vstack(rates); NULLD[k] = R_.max(0) - R_.min(0)
        if SUMM[k]["型"] != "k":
            x = E[k].to_numpy(float); okx = np.isfinite(x); xr = pd.Series(x[okx]).rank(method="average").to_numpy()
            Pk = P[okx]; n1 = Pk.sum(0); n0 = okx.sum() - n1
            A_ = ((xr[:, None] * Pk).sum(0) - n1 * (n1 + 1) / 2) / (n1 * n0)
            NULLA[k] = np.abs(A_ - 0.5)
    for k in keys:
        SUMM[k]["打亂p（差）"] = float((NULLD[k] >= SUMM[k]["探索差"] - 1e-12).mean())
        if k in NULLA and SUMM[k]["探索"]["AUC"] is not None and np.isfinite(SUMM[k]["探索"]["AUC"]):
            SUMM[k]["打亂p（|AUC−0.5|）"] = float((NULLA[k] >= abs(SUMM[k]["探索"]["AUC"] - 0.5) - 1e-12).mean())
    MX = np.vstack([NULLD[k] for k in keys])                                 # 特徵 × P
    obs = sorted(((SUMM[k]["探索差"], k) for k in keys), reverse=True)
    top5 = [k for _, k in obs[:5]]
    MC = {"特徵數（進排名）": len(keys), "切法": "每特徵一種（探索段三分位／二元／產業大類）", "打亂次數": NPERM,
          "打亂下 所有特徵中最大差：中位、p90、p95": [float(np.median(MX.max(0))), float(np.quantile(MX.max(0), .9)), float(np.quantile(MX.max(0), .95))],
          "打亂下 每特徵差的中位（各特徵平均）": float(np.mean(np.median(MX, 1)))}
    for th in (0.10, 0.15, 0.20, 0.25):
        MC[f"光靠運氣預期有幾個特徵差 ≥ {th:.0%}"] = float((MX >= th).sum(0).mean())
        MC[f"實際有幾個特徵差 ≥ {th:.0%}"] = int(sum(1 for v, _ in obs if v >= th))
    MC["前 5 名各自的族系 p（打亂下最大差 ≥ 該特徵差）"] = {k: float((MX.max(0) >= SUMM[k]["探索差"] - 1e-12).mean()) for k in top5}
    if NULLA:
        MA = np.vstack([NULLA[k] for k in NULLA])
        MC["打亂下 所有特徵中最大 |AUC−0.5|：中位、p95"] = [float(np.median(MA.max(0))), float(np.quantile(MA.max(0), .95))]
    log(f"[多重比較] {MC}")
    TOP = []
    for k in top5:
        sm = SUMM[k]
        labf, names = LABF[k]
        for s in ("確認", "早年"):                                    # 該段同兩組的單邊打亂 p（方向 ＝ 探索段高組 ＞ 低組；⛔ 不重切）
            G = U[U["段"] == s]; g = labf(G[k].tolist() if sm["型"] == "k" else G[k]); y = G["賺"].to_numpy()
            ih, il = names.index(sm["高組"]), names.index(sm["低組"]); mm = (g == ih) | (g == il)
            if (g == ih).sum() and (g == il).sum():
                yy = y[mm]; hh = (g[mm] == ih); obs_ = yy[hh].mean() - yy[~hh].mean()
                Pp = np.array([rng.permutation(yy) for _ in range(NPERM)])
                nul = Pp[:, hh].mean(1) - Pp[:, ~hh].mean(1)
                sm[f"{s}單邊打亂p"] = float((nul >= obs_ - 1e-12).mean())
            else:
                sm[f"{s}單邊打亂p"] = None
        TOP.append({"特徵": k, "名稱": sm["名稱"], "探索差": sm["探索差"], "高組": sm["高組"], "低組": sm["低組"],
                    "確認差": sm.get("確認差（同兩組）"), "確認同方向": sm.get("確認同方向"), "確認單邊打亂p": sm.get("確認單邊打亂p"),
                    "早年差": sm.get("早年差（同兩組）"), "早年同方向": sm.get("早年同方向"), "早年單邊打亂p": sm.get("早年單邊打亂p"),
                    "AUC 探索／確認／早年": [sm[s]["AUC"] for s in SEGN], "打亂p": sm.get("打亂p（差）"), "族系p": MC["前 5 名各自的族系 p（打亂下最大差 ≥ 該特徵差）"][k],
                    "各組賺錢比例": {s: {gn: [v["筆數"], v["賺錢比例"]] for gn, v in sm[s]["組"].items()} for s in SEGN}})
    pd.DataFrame(TAB).to_csv(os.path.join(OUT, "feat_table.csv"), index=False, float_format="%.6g")
    AUCT = {k: {s: SUMM[k][s]["AUC"] for s in SEGN} for k, _, typ in FEAT + EXEC if typ != "k"}
    OUTJ = {"時間": now_tpe() + "（台北）", "性質": "描述性特徵掃描；⛔ 不計 N、⛔ 不判定；加碼已看過結果 ⇒ 全是事後描述、只當線索",
            "讀法": __doc__.split("═══ 讀法（F 標）═══")[1].split("輸出")[0].strip(),
            "樣本": sinfo, "特徵資訊": finfo, "分析樣本（S 已出場）": NS, "閘": gate,
            "前5（探索段差最大）": TOP, "探索段差排名": [{"特徵": k, "名稱": SUMM[k]["名稱"], "差": v, "打亂p": SUMM[k].get("打亂p（差）"),
                                                   "確認同方向": SUMM[k].get("確認同方向"), "早年同方向": SUMM[k].get("早年同方向")} for v, k in obs],
            "執行時才看得到（另列、不進排名）": {k: SUMM[k] for k, _, _ in EXEC},
            "AUC": AUCT, "多重比較": MC, "全部特徵": SUMM, "耗時秒": round(time.time() - T0)}
    json.dump(OUTJ, open(os.path.join(OUT, "feat.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=lambda o: (None if (isinstance(o, float) and not np.isfinite(o)) else (o.item() if hasattr(o, "item") else str(o))))
    log(f"[完成] {time.time() - T0:.0f}s ⇒ {OUT}")


if __name__ == "__main__":
    run()
