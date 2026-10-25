# -*- coding: utf-8 -*-
"""主題標籤能否替營量、營飆加分 seq1（台股策略線 0328，sha b2e6be286b41a9ad；裁定 seq478 §五 核）——【②普查標籤】正式描述程式。
回測線計算子代理，2026-10-26 03:45（台北）起草。前瞻＋描述、⛔ 不判、⛔ 不計 N；三種標籤分開報、⛔ 不合併（本檔只做②普查；①前瞻 2027-11-30、③盲判 seq2 另寫）。
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
    主題組 ＜ 30 ⇒ 寫「筆數不足」；否則「成立」／「不成立」。⛔ 不寫「有效」。
 F7 乾跑：⛔ 不讀 amt_out／cost、⛔ 不算任何價格比；R、大盤、0050 全設 0；只驗：配對鍵存在（buy 列＝(帳,代號,進場t)、sell 列＝(帳,代號,出場t)）、
    大盤與 0050 序列涵蓋所有需要的日期、抽樣與自助法流程跑通、F3 函式用合成數字 fixture 驗算。輸出到 resultsThemeTag/dry/（標「乾跑 R 全 0」）。
輸出（正式）backtest/resultsThemeTag/census/：rows.csv（每筆 R、大盤、0050、超額）、stats.csv、ci.csv、summary.md、run.json、run.log
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--ruling", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    if not a.dry and not re.fullmatch(r"seq\d+", a.ruling or ""):
        print("⛔ 正式跑須帶 --ruling seqNNN（裁定號）；只准 --dry 乾跑。拒跑。", file=sys.stderr)
        return 2
    out = a.out or os.path.join(B, "resultsThemeTag", "dry" if a.dry else "census")
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
                        sent[f"{st}_{v}"] = f"筆數不足（主題組 {th['筆數']} 筆 ＜ 30）"
                    else:
                        okk = (th["中位"] > no["中位"] and th["中位"] > rm["中位"] and th["去最大1筆平均"] > no["去最大1筆平均"]
                               and th["去最大1筆平均"] > rm["去最大1筆平均"])
                        sent[f"{st}_{v}"] = "成立" if okk else "不成立"
            log(f"[{st}·{v}] 主題 {int(Es[col].sum())}／全部 {len(Es)}；隨機抽樣月 {len(groups)}（k＝n {deg}）；描述句 {sent[f'{st}_{v}']}")
    S = pd.DataFrame(srows); C = pd.DataFrame(crows)
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
    L = [f"# 主題標籤 seq1 ②普查標籤｜{mode}", "", ("> ⚠ 乾跑：R、大盤、0050 全設 0，下表數字全部無意義，只驗流程。" if a.dry else
         "> 前瞻＋描述、⛔ 不判、⛔ 不計 N。普查有事後偏差、樣本本線看過 ⇒ 只描述。寬嚴照標、⛔ 不寫成保守～樂觀。"), "",
         "| 策略 | 版 | 描述句（大盤欄） |", "|---|---|---|"]
    for k, s in sent.items():
        st, v = k.split("_")
        L.append(f"| {st} | {'寬鬆' if v == '寬' else '嚴格'} | {s} |")
    L += ["", "stats.csv（主題／非主題／同月隨機／差 × 大盤、0050）、ci.csv（月群自助法，只描述）、rows.csv（每筆）。"]
    open(os.path.join(out, "summary.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    log(f"[完成] {time.time() - t0:.1f}s ⇒ {out}")
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
