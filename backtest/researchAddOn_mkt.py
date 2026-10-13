# -*- coding: utf-8 -*-
"""漲多加碼：G3a「加權指數收盤 ＞ MA20 才加碼」是否只是參數巧合——大盤／廣度濾網的描述性穩健度初測——回測線計算子代理。
⛔ 只計算：不 commit、不改既有程式與結果夾；描述性「初測」、⛔ 不計 N、⛔ 不判定；用語「假訊號」；⛔ 不給買賣建議。
⛔ 加權指數讀私有庫 ~/us-stock-data（唯讀）；本結果夾只放布林與彙總，⛔ 不放任何指數值或均線值。
⚠ G3a 是在 researchAddOn_ext 看過結果後才挑出來追的；本件所有版本都在同一批已看過的 400 筆上試 ⇒ 多重比較，只當「要不要正式登錄」的參考。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchAddOn_mkt

═══ 讀法（M 標）═══
 M0 樣本 ＝ resultsAddOn/ext/ext_rows.csv.gz 的 400 筆（同 ext／cf／feat）；段 ＝ 探索 2017～2021、確認 2022～、早年 2005～2014；主窗 ＝ 探索＋確認
    每筆報酬 ＝ ext 的 A_ret（ta 開盤加 1 份、原持股同日同價出場、扣 COST）；金額 ＝ ext 金額；群集 ＝ ext clu（世界|A 加碼月）
    濾網版本只決定「加或不加」，加碼價同 A ⇒ 報：加碼比例、留下那批的 平均／中位／賺錢比例／賠＞15% 比例、總損益（Σ 金額 × r）、
      ① 總損益差 ＝ −Σ_被排除 金額 × r_A（月群集 bootstrap 總和 CI）、③ 留下平均 − 排除平均（兩組共用月群集重抽 CI）；bootstrap 5000 次
    決策日 t 的大盤狀態一律只用 t 收盤以前（含 t）的資料
 M1 加權指數 ＝ ~/us-stock-data/data/macro/twse_taiex.csv 收盤，依指數自己的交易日序列算 MA_L（含當日最近 L 日平均）；事件取 cal[t] 當日
    閘：MA20 版必須與 ext 的 G3a_多頭 逐筆相同；0050 版（世界 bench 還原收盤，世界日曆位置）MA20 必須與 ext 的 G3c_多頭 逐筆相同
 M2 版本（⛔ 不重切、⛔ 不調參；長度清單照派工）
    ①長度掃描：TX_MA{5,10,20,40,60,120,200}、E50_MA{同}（0050）：收盤 ＞ MA_L ⇒ 加
    ②趨勢：斜率正 ＝ MA20_t ＞ MA20_{t−5}；2×2 四格（站上／未站上 × 斜率正／非正）各自當「只加這格」；
       k ＝ 到 t 為止連續收盤 ＞ 當日 MA20 的天數；連5 ＝ k ≥ 5；剛站上 ＝ 1 ≤ k ≤ 5；已站上多日 ＝ k ≥ 6
    ③廣度：t 當日母體中 收盤 ＞ 自身 MA20（MA60）的比例 ＞ 50% ⇒ 加；股票 MA_L 用世界還原收盤、日曆位置 t−L＋1…t 皆有 K 棒有收盤、窗內無壞根（壞根 ＝ researchAddOn.market）
       母體兩版：R1（researchAddOn.market 的 R1 遮罩）、全檔（世界快取全部股票、t 有 K 棒）
 M3 逐年（A 加碼年）：G3a 站上／未站上兩組 筆數、平均、差、總損益；剔一年後主窗 ③ 的範圍；去掉 A_ret 最高 1%／5%（各段內、向上取整筆數）後 ③ 與 ①
 M4 群集：③ 在 月（預設）、月等權（先月內平均再跨月）、股票、年、大盤波段（加權 MA20 站上／未站上的連續段）五種群集下的差與 CI；各組不同股票數
 M5 假訊號（時間平移）：把 G3a 旗標換成 t−k 日的旗標（k ＝ 21…250 交易日），算各段 ③ 的分布，看真旗標排第幾（描述用）
 M6 早年：站上／未站上兩組的報酬、逐年、按策略
輸出 backtest/resultsAddOn/mkt/：mkt.json、mkt_table.csv、mkt_years.csv、mkt_rows.csv.gz（只有布林與彙總）
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchAddOn as AO                      # noqa: E402
from backtest import researchAddOn_ext as EXT                 # noqa: E402

OUT = "backtest/resultsAddOn/mkt"
TAIEX = os.path.expanduser("~/us-stock-data/data/macro/twse_taiex.csv")
SEED = 20261014
SEGN = ("探索", "確認", "主窗", "早年")
LENS = (5, 10, 20, 40, 60, 120, 200)


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


def evalf(s, flag, rng, clu="clu"):
    """flag：bool／NaN（缺）；回傳一列彙總。"""
    fl = s[flag] if isinstance(flag, str) else flag
    ok = fl.notna()
    ss = s[ok]; k = fl[ok].astype(bool).to_numpy()
    r = ss["A_ret"].to_numpy(float); amt = ss["金額"].to_numpy(float); c = ss[clu].to_numpy()
    o = {"事件數": int(len(ss)), "缺": int((~ok).sum()), "加碼筆數": int(k.sum()),
         "加碼比例": float(k.mean()) if len(k) else None}
    st = EXT.stats(r, amt * r * k, k)
    o.update({"留下_" + a: st.get(a) for a in ("平均", "中位", "賺錢比例", "賠超過15比例")})
    o["總損益"] = st["總損益"]; o["總損益A"] = float(np.sum(amt * r))
    o["排除筆數"] = int((~k).sum())
    if (~k).any():
        o["排除_平均"] = float(r[~k].mean()); o["排除_中位"] = float(np.median(r[~k])); o["排除_賺錢比例"] = float((r[~k] > 0).mean())
    b1 = EXT.boot(-(amt * r) * (~k), c, rng, "sum")
    o["總損益差"] = b1["值"]; o["總損益差_CI"] = b1["CI95"]
    if k.sum() > 1 and (~k).sum() > 1:
        b3 = EXT.boot_diff2(r[k], c[k], r[~k], c[~k], rng)
        o["留下減排除"] = b3["差"]; o["留下減排除_CI"] = b3["CI95"]
        o["中位差"] = float(np.median(r[k]) - np.median(r[~k]))
    else:
        o["留下減排除"] = None; o["留下減排除_CI"] = [None, None]; o["中位差"] = None
    o["留下_不同股票"] = int(ss.loc[k, "sid"].nunique()); o["排除_不同股票"] = int(ss.loc[~k, "sid"].nunique())
    return o


def boot_month_eq(r, keep, clu, rng, nb=5000):
    """月等權：每個（月, 組）先平均，再兩組各自跨月平均；按月重抽。"""
    df = pd.DataFrame({"r": r, "k": keep, "c": clu})
    g = df.groupby(["c", "k"])["r"].mean().unstack()
    months = g.index.to_numpy(); G = len(months)
    a = g.get(True, pd.Series(np.nan, index=g.index)).to_numpy(float)
    b = g.get(False, pd.Series(np.nan, index=g.index)).to_numpy(float)
    v = float(np.nanmean(a) - np.nanmean(b))
    bs = []
    for _ in range(nb):
        ix = rng.integers(G, size=G)
        aa, bb = a[ix], b[ix]
        if np.isfinite(aa).any() and np.isfinite(bb).any():
            bs.append(np.nanmean(aa) - np.nanmean(bb))
    return {"差": v, "CI95": [float(np.quantile(bs, .025)), float(np.quantile(bs, .975))], "月數": int(G),
            "有留下月": int(np.isfinite(a).sum()), "有排除月": int(np.isfinite(b).sum())}


def main():
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    R = pd.read_csv(os.path.join("backtest/resultsAddOn/ext", "ext_rows.csv.gz"), dtype={"sid": str},
                    usecols=["世界", "策略", "sid", "tb", "格", "t", "ta", "段", "金額", "市場", "加碼月", "A_ret", "G3a_多頭", "G3c_多頭", "clu"])
    assert len(R) == 400
    WS = AO.worlds(log, 1)
    from backtest import universe_gate as UG
    UG.set_gate_v2(True)
    MW = {}; X = None
    for wn in ("主", "早年"):
        M, HB, X, minfo = AO.market(wn, WS[wn], X, log, [])
        MW[wn] = M
    # ── 加權指數（私有庫，唯讀；只在記憶體）
    tx = pd.read_csv(TAIEX, dtype={"date": str}); tx["date"] = pd.to_datetime(tx["date"])
    tx = tx.drop_duplicates("date").set_index("date")["close"].astype(float).sort_index()
    tx = tx[np.isfinite(tx) & (tx > 0)]
    TXMA = {L: tx.rolling(L, min_periods=L).mean() for L in LENS}
    above20 = (tx > TXMA[20]) & TXMA[20].notna()
    slope = (TXMA[20] > TXMA[20].shift(5)) & TXMA[20].shift(5).notna()
    # 連續站上天數 k
    a = above20.to_numpy(); kk = np.zeros(len(a), int)
    for i in range(len(a)):
        kk[i] = (kk[i - 1] + 1 if i else 1) if a[i] else 0
    kser = pd.Series(kk, index=tx.index)
    epi = pd.Series(np.cumsum(np.r_[1, (a[1:] != a[:-1]).astype(int)]), index=tx.index)   # 大盤 MA20 波段編號
    info = {"加權指數 序列起訖": [str(tx.index[0].date()), str(tx.index[-1].date())], "加權指數 日數": int(len(tx))}
    # ── 每事件
    R["date"] = [WS[w]["cal"][int(t)] for w, t in zip(R["世界"], R["t"])]
    miss = (~R["date"].isin(tx.index)).sum(); info["事件日加權指數缺"] = int(miss)
    assert miss == 0
    for L in LENS:
        R[f"TX_MA{L}"] = [bool(tx[d] > TXMA[L][d]) if np.isfinite(TXMA[L][d]) else np.nan for d in R["date"]]
    R["TX_斜率正"] = [bool(slope[d]) for d in R["date"]]
    R["TX_k"] = [int(kser[d]) for d in R["date"]]
    R["TX_波段"] = [f"{w}|{int(epi[d])}" for w, d in zip(R["世界"], R["date"])]
    # 2×2、連續、剛站上
    st_ = R["TX_MA20"].astype(bool); sl = R["TX_斜率正"].astype(bool)
    R["Q_站上斜率正"] = st_ & sl; R["Q_站上斜率非正"] = st_ & ~sl; R["Q_未站上斜率正"] = ~st_ & sl; R["Q_未站上斜率非正"] = ~st_ & ~sl
    R["TX_斜率正_only"] = sl
    R["TX_站上或斜率正"] = st_ | sl
    R["TX_連5"] = R["TX_k"] >= 5
    R["TX_剛站上"] = (R["TX_k"] >= 1) & (R["TX_k"] <= 5)
    R["TX_已站上多日"] = R["TX_k"] >= 6
    R["TX_站上狀態"] = np.where(R["TX_k"] == 0, "未站上", np.where(R["TX_k"] <= 5, "剛站上(1~5日)", "已站上多日(≥6日)"))
    # 0050（世界 bench）
    for L in LENS:
        v = []
        for w, t in zip(R["世界"], R["t"]):
            b = np.asarray(WS[w]["bench"], float); t = int(t)
            if t - L + 1 < 0 or not np.isfinite(b[t - L + 1:t + 1]).all():
                v.append(np.nan)
            else:
                v.append(bool(b[t] > b[t - L + 1:t + 1].mean()))
        R[f"E50_MA{L}"] = v
    # 閘
    g1 = int((R["TX_MA20"].astype(bool) != R["G3a_多頭"].astype(bool)).sum())
    g2 = int((R["E50_MA20"].astype(bool) != R["G3c_多頭"].astype(bool)).sum())
    gates = {"TX_MA20 vs ext G3a_多頭 不同筆數": g1, "E50_MA20 vs ext G3c_多頭 不同筆數": g2}
    log(f"[閘] {gates}")
    if g1 or g2:
        raise SystemExit("⛔ 閘不過")
    # ── 廣度
    for wn in ("主", "早年"):
        M = MW[wn]; C, BAR, BAD, R1m = M["C"], M["BAR"], M["BAD"], M["R1"]
        CB = np.zeros((M["S"], M["n"] + 1), np.int32); CB[:, 1:] = np.cumsum(BAD, axis=1)
        okc = BAR & np.isfinite(C)
        OKC = np.zeros((M["S"], M["n"] + 1), np.int32); OKC[:, 1:] = np.cumsum(okc, axis=1)
        CS = np.zeros((M["S"], M["n"] + 1)); CS[:, 1:] = np.nancumsum(np.where(okc, C, 0.0), axis=1)
        ix = R.index[R["世界"] == wn]
        for L in (20, 60):
            for i in ix:
                t = int(R.at[i, "t"])
                el = ((OKC[:, t + 1] - OKC[:, t - L + 1]) == L) & ((CB[:, t + 1] - CB[:, t - L + 2]) == 0)
                ma = (CS[:, t + 1] - CS[:, t - L + 1]) / L
                up = el & (C[:, t] > ma)
                for pn, pm in (("R1", R1m[:, t] & el), ("全檔", BAR[:, t] & el)):
                    nn = int(pm.sum())
                    R.at[i, f"廣度_{pn}_MA{L}_比例"] = (float((up & pm).sum() / nn) if nn else np.nan)
                    R.at[i, f"廣度_{pn}_MA{L}_檔數"] = nn
        log(f"[廣度 {wn}] 完成")
    for pn in ("R1", "全檔"):
        for L in (20, 60):
            p = R[f"廣度_{pn}_MA{L}_比例"]
            R[f"BR_{pn}_MA{L}"] = np.where(p.isna(), np.nan, (p > 0.5).astype(float))
            R[f"BR_{pn}_MA{L}"] = R[f"BR_{pn}_MA{L}"].map(lambda v: np.nan if pd.isna(v) else bool(v))
    VERS = ([(f"TX_MA{L}", f"加權 ＞ MA{L}") for L in LENS] + [(f"E50_MA{L}", f"0050 ＞ MA{L}") for L in LENS] +
            [("TX_斜率正_only", "加權 MA20 斜率正（不看站上）"), ("Q_站上斜率正", "格：站上∧斜率正"), ("Q_站上斜率非正", "格：站上∧斜率非正"),
             ("Q_未站上斜率正", "格：未站上∧斜率正"), ("Q_未站上斜率非正", "格：未站上∧斜率非正"), ("TX_站上或斜率正", "站上 或 斜率正"),
             ("TX_連5", "連續 ≥5 日站上 MA20"), ("TX_剛站上", "剛站上（k＝1～5）"), ("TX_已站上多日", "已站上多日（k ≥ 6）")] +
            [(f"BR_{pn}_MA{L}", f"廣度 {pn} 收盤＞自身 MA{L} 比例 ＞ 50%") for pn in ("R1", "全檔") for L in (20, 60)])
    rng = np.random.default_rng(SEED)
    TB = []; J = {"時間": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M") + "（台北）",
                  "性質": "初測（描述性）；⛔ 不計 N、⛔ 不判定；G3a 是看過 ext 結果後挑出來追的 ⇒ 多重比較",
                  "讀法": __doc__.split("═══ 讀法（M 標）═══")[1].split("輸出")[0].strip(), "資訊": info, "閘": gates}
    for v, nm in VERS:
        for sg in SEGN:
            s = seg(R, sg)
            o = evalf(s, v, rng); rec = {"版本": v, "名稱": nm, "段": sg}
            for k_, x in o.items():
                if isinstance(x, list):
                    rec[k_ + "_低"], rec[k_ + "_高"] = x
                else:
                    rec[k_] = x
            TB.append(rec)
    TBd = pd.DataFrame(TB)
    TBd.to_csv(os.path.join(OUT, "mkt_table.csv"), index=False, float_format="%.6g")
    log("[表] 完成")
    # 剛站上／已站上／未站上 三組描述
    tri = {}
    for sg in SEGN:
        s = seg(R, sg); z = {}
        for g, q in s.groupby("TX_站上狀態"):
            r = q["A_ret"].to_numpy(float)
            z[g] = {"筆": int(len(q)), "平均": float(r.mean()), "中位": float(np.median(r)), "賺錢比例": float((r > 0).mean()),
                    "賠超過15比例": float((r < -0.15).mean()), "總損益": float((q["金額"] * q["A_ret"]).sum())}
        tri[sg] = z
    J["站上狀態三組"] = tri
    # 2×2 描述
    J["2x2"] = {sg: {c: {"筆": int(seg(R, sg)[c].sum()), "平均": float(seg(R, sg).loc[seg(R, sg)[c], "A_ret"].mean()) if seg(R, sg)[c].any() else None,
                         "賺錢比例": float((seg(R, sg).loc[seg(R, sg)[c], "A_ret"] > 0).mean()) if seg(R, sg)[c].any() else None}
                     for c in ("Q_站上斜率正", "Q_站上斜率非正", "Q_未站上斜率正", "Q_未站上斜率非正")} for sg in SEGN}
    # 廣度分布
    J["廣度分布（事件日，中位／站上 MA20 時中位／未站上時中位）"] = {
        sg: {f"{pn}_MA{L}": [float(seg(R, sg)[f"廣度_{pn}_MA{L}_比例"].median()),
                            float(seg(R, sg).loc[seg(R, sg)["TX_MA20"].astype(bool), f"廣度_{pn}_MA{L}_比例"].median()),
                            float(seg(R, sg).loc[~seg(R, sg)["TX_MA20"].astype(bool), f"廣度_{pn}_MA{L}_比例"].median())]
             for pn in ("R1", "全檔") for L in (20, 60)} for sg in SEGN}
    J["廣度 R1 檔數中位"] = float(R["廣度_R1_MA20_檔數"].median())
    # ── 逐年
    R["年"] = R["加碼月"].str[:4]
    txy = above20.groupby(above20.index.year).mean()
    YR = []
    for (y, sgn_), q in R.groupby(["年", "段"]):
        k = q["TX_MA20"].astype(bool); r = q["A_ret"]; amt = q["金額"]
        YR.append({"年": y, "段": sgn_, "筆": int(len(q)), "站上筆": int(k.sum()), "未站上筆": int((~k).sum()),
                   "站上平均": float(r[k].mean()) if k.any() else None, "未站上平均": float(r[~k].mean()) if (~k).any() else None,
                   "差": (float(r[k].mean() - r[~k].mean()) if (k.any() and (~k).any()) else None),
                   "站上賺錢比例": float((r[k] > 0).mean()) if k.any() else None, "未站上賺錢比例": float((r[~k] > 0).mean()) if (~k).any() else None,
                   "站上總損益": float((amt * r)[k].sum()), "未站上總損益": float((amt * r)[~k].sum()),
                   "全年A平均": float(r.mean()), "當年加權站上MA20交易日比例": float(txy.get(int(y), np.nan))})
    YRd = pd.DataFrame(YR); YRd.to_csv(os.path.join(OUT, "mkt_years.csv"), index=False, float_format="%.6g")
    # 剔一年
    LOO = {}
    for sg in SEGN:
        s = seg(R, sg); vals = {}
        for y in sorted(s["年"].unique()):
            q = s[s["年"] != y]; k = q["TX_MA20"].astype(bool); r = q["A_ret"]
            vals[y] = {"③": float(r[k].mean() - r[~k].mean()), "①": float(-(q["金額"] * r)[~k].sum())}
        LOO[sg] = {"逐年剔除": vals, "③ 最小／最大": [min(v["③"] for v in vals.values()), max(v["③"] for v in vals.values())],
                   "① 最小／最大": [min(v["①"] for v in vals.values()), max(v["①"] for v in vals.values())],
                   "③ 剔一年後仍 ＞0 的年數／年數": [int(sum(v["③"] > 0 for v in vals.values())), len(vals)]}
    J["剔一年"] = LOO
    # 去掉最賺
    TRIM = {}
    for sg in SEGN:
        s = seg(R, sg); z = {}
        for q_ in (0.0, 0.01, 0.05):
            for by in ("A_ret", "pnl"):
                if q_ == 0 and by == "pnl":
                    continue
                key = s["A_ret"] if by == "A_ret" else s["金額"] * s["A_ret"]
                m = int(math.ceil(q_ * len(s)))
                drop = key.sort_values(ascending=False).index[:m]
                t_ = s.drop(drop)
                o = evalf(t_, "TX_MA20", rng)
                z[f"去前{int(q_ * 100)}%（依{'報酬' if by == 'A_ret' else '金額損益'}，{m} 筆）"] = {
                    "③留下減排除": o["留下減排除"], "③CI": o["留下減排除_CI"], "①總損益差": o["總損益差"], "①CI": o["總損益差_CI"],
                    "中位差": o["中位差"], "被去掉的筆中站上的筆數": int(s.loc[drop, "TX_MA20"].astype(bool).sum())}
        TRIM[sg] = z
    J["去掉最賺"] = TRIM
    # ── 群集
    CL = {}
    for sg in SEGN:
        s = seg(R, sg); k = s["TX_MA20"].astype(bool).to_numpy(); r = s["A_ret"].to_numpy(float)
        z = {}
        for nmc, col in (("月（預設）", "clu"), ("股票", "sid"), ("年", "年"), ("大盤 MA20 波段", "TX_波段")):
            c = s[col].to_numpy()
            b = EXT.boot_diff2(r[k], c[k], r[~k], c[~k], rng)
            z[nmc] = {"差": b["差"], "CI95": b["CI95"], "群集數": int(len(np.unique(c))),
                      "留下群集數": int(len(np.unique(c[k]))), "排除群集數": int(len(np.unique(c[~k])))}
        z["月等權（先月內平均）"] = boot_month_eq(r, k, s["clu"].to_numpy(), rng)
        z["不同股票數 留下／排除"] = [int(s.loc[k, "sid"].nunique()), int(s.loc[~k, "sid"].nunique())]
        z["每月事件數 中位／最大"] = [float(s.groupby("clu").size().median()), int(s.groupby("clu").size().max())]
        z["同股同月重複事件筆數"] = int(s.duplicated(["sid", "clu"]).sum())
        CL[sg] = z
    J["群集"] = CL
    # ── 假訊號（時間平移）
    PL = {}
    txpos = {d: i for i, d in enumerate(tx.index)}
    ab = above20.to_numpy()
    for sg in SEGN:
        s = seg(R, sg); pos = np.array([txpos[d] for d in s["date"]]); r = s["A_ret"].to_numpy(float)
        real = float(r[ab[pos]].mean() - r[~ab[pos]].mean())
        vals = []
        for lag in range(21, 251):
            kf = ab[pos - lag]
            if kf.any() and (~kf).any():
                vals.append(float(r[kf].mean() - r[~kf].mean()))
        vals = np.array(vals)
        PL[sg] = {"真③": real, "平移③ 中位": float(np.median(vals)), "平移③ p5／p95": [float(np.quantile(vals, .05)), float(np.quantile(vals, .95))],
                  "真③ ≥ 平移③ 的比例": float((real >= vals).mean()), "平移次數": int(len(vals)), "平移③ ＞0 比例": float((vals > 0).mean())}
    J["假訊號（時間平移 k＝21～250）"] = PL
    # ── 早年
    s = seg(R, "早年"); k = s["TX_MA20"].astype(bool)
    J["早年"] = {"按策略": {st: {"站上": [int((k & (s["策略"] == st)).sum()), float(s.loc[k & (s["策略"] == st), "A_ret"].mean())],
                                 "未站上": [int((~k & (s["策略"] == st)).sum()), float(s.loc[~k & (s["策略"] == st), "A_ret"].mean())]}
                            for st in sorted(s["策略"].unique())},
                 "按市場": {mk: {"站上": [int((k & (s["市場"] == mk)).sum()), float(s.loc[k & (s["市場"] == mk), "A_ret"].mean()) if (k & (s["市場"] == mk)).any() else None],
                                 "未站上": [int((~k & (s["市場"] == mk)).sum()), float(s.loc[~k & (s["市場"] == mk), "A_ret"].mean()) if (~k & (s["市場"] == mk)).any() else None]}
                            for mk in sorted(s["市場"].unique())},
                 "未站上前 5 大報酬（年月、策略、站上狀態 k、報酬）": s.loc[~k].nlargest(5, "A_ret")[["加碼月", "策略", "TX_k", "A_ret"]].values.tolist(),
                 "站上前 5 大報酬": s.loc[k].nlargest(5, "A_ret")[["加碼月", "策略", "TX_k", "A_ret"]].values.tolist(),
                 "站上最差 5": s.loc[k].nsmallest(5, "A_ret")[["加碼月", "策略", "TX_k", "A_ret"]].values.tolist()}
    # ── 存
    keep = ["世界", "策略", "sid", "tb", "格", "t", "ta", "段", "加碼月", "clu", "TX_k", "TX_站上狀態", "TX_波段", "TX_斜率正"] + \
           [f"TX_MA{L}" for L in LENS] + [f"E50_MA{L}" for L in LENS] + \
           [c for c in R.columns if c.startswith("廣度_") or c.startswith("BR_")]
    R[keep].to_csv(os.path.join(OUT, "mkt_rows.csv.gz"), index=False, float_format="%.6g")
    json.dump(J, open(os.path.join(OUT, "mkt.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=jdef)
    log(f"[完成] {time.time() - T0:.0f}s ⇒ {OUT}")


if __name__ == "__main__":
    main()
