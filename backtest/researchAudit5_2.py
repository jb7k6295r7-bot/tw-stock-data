# -*- coding: utf-8 -*-
"""稽核 §八（seq3；裁定 seq258 §二、seq257 順 7）第 2 件：回測 研究五（PREREG4 出場 11 種）、回測 研究六（PREREG5 等風險版）補「抱 20、120 天」逐筆配對。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchAudit5_2 [--procs 2]
    獨立查核：~/tw-p16/.venv/bin/python backtest/researchAudit5_2_check.py

原件：backtest/research5.py、PREREG4.md、results5/（進場 E1 G1 營收創高、E2 P1 箱型突破、E3 P4 錘子；11 種出場；只對 H60 配對）；
      backtest/research6.py、PREREG5.md（定案 w_max 20%、H 系代用停損距離 3×ATR14）、results6/
讀法（⭐ 看數字前寫定）：
  R1 進場集合 ＝ results5/exits.csv.gz 原列（set、stock_id、market、signal_pos、entry_pos），⛔ 不改；出場函式 ＝ research5._hold／_stop 原式（import 呼叫）
  R2 資料：原件跑在 2026-09-18 分支 data/；該份的還原因子之後有更新（抽 400 筆：H60 有 41 筆差 1e−8～3e−4）⇒ 本件全部出場腿在【釘住的快照 edc6f】重算，
     ⭐ 閘：快照上重算的「11 規則 − H60」配對判定 ＝ 原件判定（逐集合逐規則）；另報原件存檔數字上的「− H20」（H20 原件本來就有）
  R3 基準 H ∈ {20, 60, 120}：⭐ 主版 ＝「時間上限 ＝ H」配對（停損類規則的時間上限改成 H，與同長度固定持有比；H＝60 ＝ 原件）；
     另列字面版 ＝ 原件停損規則（上限 60）直接對 H20／H120
  R4 統計、判定用語 ＝ 原件（非重疊 n 間隔 60 日做 SE；期望值較好／只是保險／較差／分不出來；前段 ＜ 2021-01-04 ≤ 後段）
     H120 在資料尾算不出的列（進場後不足 120 根）⇒ 該配對只用兩腿都有的列（照報筆數）
  R5 研究六：部位 w ＝ min(2% ÷ d, 20%)；d ＝ 停損 p／追蹤 p／ATR k×ATR14 ÷ 進場價／固定持有 3×ATR14 ÷ 進場價（原件定案）；主指標 w × 淨報酬的配對差
  ⭐ 單筆層（逐筆淨報酬）⇒ 不涉組合層；stop_force、t1_censor 不適用（寫明）
輸出 backtest/resultsAudit5/2/：legs.csv.gz、pairs.csv、summary.json、REPORT.md
"""
from __future__ import annotations

import argparse
import json
import math
import os
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import data as D
from . import patterns as P
from . import rerun17 as RR
from . import research5 as R5
from . import evaluate as E

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsAudit5", "2")
HS = (20, 60, 120)
STOPS = [r for r in R5.RULES if r[1] != "hold"]
WMAX, RISK, HOLD_X = 0.20, 0.02, 3.0
_G: dict = {}


def legs_one(job):
    sid, market, ents = job
    cal = _G["cal"]
    st = D.load_stock(sid, market, cal)
    if st is None:
        return []
    f = P.Frame(st.df, st.event_dates)
    arr = {"o": f.o, "h": f.h, "l": f.l, "c": f.c, "prev_c": f.prev_c, "atr14": f.atr14}
    n = len(f.c); out = []
    for set_code, ep in ents:
        if ep >= n or np.isnan(arr["o"][ep]):
            out.append({"set": set_code, "stock_id": sid, "entry_pos": int(ep), "ok": False}); continue
        price = arr["o"][ep]
        row = {"set": set_code, "stock_id": sid, "entry_pos": int(ep), "ok": True,
               "atr_pct": float(arr["atr14"][ep] / price) if not np.isnan(arr["atr14"][ep]) else np.nan}
        for H in HS:
            r = R5._hold(arr, ep, H)
            row[f"ret_H{H}"] = (r[1] / price - 1 - E.COST) if r else np.nan
            row[f"days_H{H}"] = (r[0] - ep + 1) if r else np.nan
            for code, kind, p in STOPS:
                r = R5._stop(arr, ep, kind, p, cap=H)
                row[f"ret_{code}_c{H}"] = (r[1] / price - 1 - E.COST) if r else np.nan
                row[f"days_{code}_c{H}"] = (r[0] - ep + 1) if r else np.nan
                row[f"trig_{code}_c{H}"] = float(r[2]) if r else np.nan
        out.append(row)
    return out


def nonoverlap(df):
    return R5._nonoverlap(df)


def stats(d, col):
    m = d[col].notna()
    if m.sum() < 2:
        return None
    g = d[m]; x = g[col].to_numpy(float); n_no = nonoverlap(g)
    mean = x.mean(); se = x.std(ddof=1) / math.sqrt(max(1, n_no))
    return {"n": len(x), "n_no": n_no, "mean": mean, "lo": mean - 1.96 * se, "hi": mean + 1.96 * se, "p5": float(np.percentile(x, 5))}


def paired(d, col, base, split):
    m = d[col].notna() & d[base].notna()
    if m.sum() < 2:
        return None
    g = d[m]; x = (g[col] - g[base]).to_numpy(float); n_no = nonoverlap(g)
    mean = x.mean(); se = x.std(ddof=1) / math.sqrt(max(1, n_no))
    pre = g[g["entry_pos"] < split]; post = g[g["entry_pos"] >= split]
    return {"n": len(x), "n_no": n_no, "mean": mean, "lo": mean - 1.96 * se, "hi": mean + 1.96 * se,
            "pre": float((pre[col] - pre[base]).mean()) if len(pre) else np.nan, "post": float((post[col] - post[base]).mean()) if len(post) else np.nan,
            "p5_rule": float(np.percentile(g[col], 5)), "p5_base": float(np.percentile(g[base], 5))}


def verdict(pa, tail=True):
    """原件（research5._verdict＋樣本下限；research6 無「只是保險」）。"""
    if pa is None:
        return "—"
    same = np.isfinite(pa["pre"]) and np.isfinite(pa["post"]) and np.sign(pa["pre"]) == np.sign(pa["post"])
    if pa["lo"] > 0 and same:
        v = "期望值較好"
    elif pa["hi"] < 0:
        v = "較差"
    elif tail and (pa["p5_rule"] - pa["p5_base"]) >= 0.03:
        v = "只是保險"
    else:
        v = "分不出來"
    if pa["n_no"] < 30:
        v = "樣本不足（不報）"
    elif pa["n_no"] < 100:
        v += "（樣本不足）"
    return v


def w_of(d, code, kind, p):
    if kind in ("stop", "trail"):
        dist = pd.Series(p, index=d.index, dtype=float)
    elif kind == "atr":
        dist = p * d["atr_pct"]
    else:
        dist = HOLD_X * d["atr_pct"]
    return np.minimum(RISK / dist, WMAX)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    RR.use_snapshot()
    cal = D.load_calendar(); _G["cal"] = cal
    ex = pd.read_csv(os.path.join(HERE, "results5", "exits.csv.gz"), dtype={"stock_id": str})
    old_dates = pd.to_datetime(ex["entry_date"])
    if not (pd.DatetimeIndex(cal[ex["entry_pos"].to_numpy()]) == pd.DatetimeIndex(old_dates)).all():
        raise SystemExit("⛔ 快照日曆與原件 entry_pos 對不上")
    split = int(cal.searchsorted(pd.Timestamp(R5.SPLIT)))
    jobs = [(sid, g["market"].iloc[0], list(zip(g["set"], g["entry_pos"]))) for sid, g in ex.groupby("stock_id")]
    rows = []
    with Pool(a.procs) as pool:
        for i, r in enumerate(pool.imap_unordered(legs_one, jobs, chunksize=4)):
            rows += r
            if (i + 1) % 400 == 0:
                print(f"  {i + 1}/{len(jobs)} {time.time() - t0:.0f}s", flush=True)
    LG = pd.DataFrame(rows)
    LG = ex[["set", "stock_id", "entry_pos", "entry_date", "ret_H20", "ret_H60"] + [f"ret_{c}" for c, *_ in STOPS]].rename(
        columns=lambda c: c if c in ("set", "stock_id", "entry_pos", "entry_date") else "orig_" + c).merge(LG, on=["set", "stock_id", "entry_pos"], how="left")
    LG.to_csv(os.path.join(OUT, "legs.csv.gz"), index=False)
    PR = []; GATE = {}
    for s, nm in R5.SETS.items():
        d = LG[LG["set"] == s]
        # 閘：快照上重算的 −H60 判定 ＝ 原件存檔上的 −H60 判定
        for code, kind, p in [("H20", "hold", 20)] + STOPS:
            new = paired(d, f"ret_{code}_c60" if kind != "hold" else "ret_H20", "ret_H60", split)
            old = paired(d, f"orig_ret_{code}", "orig_ret_H60", split)
            GATE[f"{s}|{code}"] = [verdict(old), verdict(new), None if old is None else round(old["mean"] * 100, 3), None if new is None else round(new["mean"] * 100, 3)]
        # 主版（上限 ＝ H）與字面版（上限 60）
        for H in HS:
            base = f"ret_H{H}"
            for code, kind, p in STOPS:
                for ver, col in (("主版（上限＝H）", f"ret_{code}_c{H}"), ("字面（上限 60）", f"ret_{code}_c60")):
                    if ver.startswith("字面") and H == 60:
                        continue
                    pa = paired(d, col, base, split)
                    # 研究六：等風險
                    dd = d.copy()
                    dd["_pr"] = w_of(dd, code, kind, p) * dd[col]; dd["_pb"] = w_of(dd, "H", "hold", None) * dd[base]
                    pr6 = paired(dd, "_pr", "_pb", split)
                    PR.append({"集合": s, "基準": f"H{H}", "版本": ver, "規則": code,
                               **{f"五_{k}": v for k, v in (pa or {}).items()}, "五_判定": verdict(pa),
                               **{f"六_{k}": v for k, v in (pr6 or {}).items()}, "六_判定": verdict(pr6, tail=False)})
            for other in [h for h in HS if h != H]:
                pa = paired(d, f"ret_H{other}", base, split)
                PR.append({"集合": s, "基準": f"H{H}", "版本": "固定持有互比", "規則": f"H{other}", **{f"五_{k}": v for k, v in (pa or {}).items()},
                           "五_判定": verdict(pa)})
        # 原件存檔數字上的 −H20（H20 原件本來就有）
        for code, kind, p in STOPS:
            pa = paired(d, f"orig_ret_{code}", "orig_ret_H20", split)
            PR.append({"集合": s, "基準": "H20", "版本": "原件存檔（上限 60，原資料）", "規則": code, **{f"五_{k}": v for k, v in (pa or {}).items()}, "五_判定": verdict(pa)})
    T = pd.DataFrame(PR); T.to_csv(os.path.join(OUT, "pairs.csv"), index=False)
    gate_ok = all(v[0] == v[1] for v in GATE.values())
    S = {"閘_快照重算的−H60判定＝原件": gate_ok, "閘明細": GATE, "列數": int(len(LG)), "快照": RR.SHA,
         "H120 可算列": {s: int(LG[(LG["set"] == s)]["ret_H120"].notna().sum()) for s in R5.SETS}, "秒": round(time.time() - t0)}
    for H in HS:
        for ver in ("主版（上限＝H）", "字面（上限 60）"):
            sub = T[(T["基準"] == f"H{H}") & (T["版本"] == ver)]
            if len(sub):
                S[f"研究五_{ver}_vs_H{H}"] = sub["五_判定"].value_counts().to_dict()
                S[f"研究六_{ver}_vs_H{H}"] = sub["六_判定"].value_counts().to_dict()
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    report(T, S)
    print(json.dumps({k: v for k, v in S.items() if k != "閘明細"}, ensure_ascii=False))
    if not gate_ok:
        raise SystemExit("⛔ 閘不過：快照重算的 −H60 判定與原件不同")


def _pp(x):
    return "—" if x is None or not np.isfinite(x) else f"{x * 100:+.2f}"


def report(T, S):
    L = ["# 稽核 第 2 件：回測 研究五（PREREG4）、回測 研究六（PREREG5）補抱 20／120 天逐筆配對", "",
         f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。稽核 seq3 §八；裁定 seq258 §二、seq257 順 7。回測線。單筆層（stop_force、t1_censor 不適用）。", ""]
    k5 = {H: S.get(f"研究五_主版（上限＝H）_vs_H{H}", {}) for H in HS}
    k6 = {H: S.get(f"研究六_主版（上限＝H）_vs_H{H}", {}) for H in HS}
    fm = lambda d_: "、".join(f"{k} {v}" for k, v in sorted(d_.items(), key=lambda z: -z[1]))
    L.append(f"**結論：九種停損 × 三個進場集合（27 格；主版：停損的時間上限 ＝ H）對同長度固定持有逐筆配對——研究五（等權）"
             f"H20：{fm(k5[20])}｜H60：{fm(k5[60])}｜H120：{fm(k5[120])}；研究六（等風險 w_max 20%）H20：{fm(k6[20])}｜H60：{fm(k6[60])}｜H120：{fm(k6[120])}。"
             f"⇒ 原結論「停損比抱著差」在 60、120 天成立，20 天時差距縮小、等權版多格只是保險、等風險版 E1 S8／S10 反而較好。"
             f"閘（快照重算的 −H60 判定 ＝ 原件）：{'過' if S['閘_快照重算的−H60判定＝原件'] else '不過'}。**")
    L += ["", "## 研究五（等權）：配對差 pp（規則 − 固定持有 H；主版 上限＝H）", "", "| 集合 | 規則 | − H20 | 判定 | − H60 | 判定 | − H120 | 判定 |", "|---|---|---|---|---|---|---|---|"]
    for s in R5.SETS:
        for code, *_ in STOPS:
            cells = []
            for H in HS:
                r = T[(T["集合"] == s) & (T["基準"] == f"H{H}") & (T["版本"] == "主版（上限＝H）") & (T["規則"] == code)].iloc[0]
                cells += [f"{_pp(r['五_mean'])}〔{_pp(r['五_lo'])}～{_pp(r['五_hi'])}〕", r["五_判定"]]
            L.append(f"| {s} | {code} | " + " | ".join(cells) + " |")
    L += ["", "## 研究六（等風險）：配對差 pp（帳戶損益 w × 淨報酬；主版）", "", "| 集合 | 規則 | − H20 | 判定 | − H60 | 判定 | − H120 | 判定 |", "|---|---|---|---|---|---|---|---|"]
    for s in R5.SETS:
        for code, *_ in STOPS:
            cells = []
            for H in HS:
                r = T[(T["集合"] == s) & (T["基準"] == f"H{H}") & (T["版本"] == "主版（上限＝H）") & (T["規則"] == code)].iloc[0]
                cells += [f"{r['六_mean'] * 100:+.3f}〔{r['六_lo'] * 100:+.3f}～{r['六_hi'] * 100:+.3f}〕", r["六_判定"]]
            L.append(f"| {s} | {code} | " + " | ".join(cells) + " |")
    L += ["", "## 字面版（原件停損規則、上限 60）對 H20／H120；原件存檔數字上的 − H20", ""]
    for ver, H in (("字面（上限 60）", 20), ("字面（上限 60）", 120), ("原件存檔（上限 60，原資料）", 20)):
        sub = T[(T["版本"] == ver) & (T["基準"] == f"H{H}")]
        L.append(f"- {ver} − H{H}：研究五 " + json.dumps(sub["五_判定"].value_counts().to_dict(), ensure_ascii=False)
                 + (("；研究六 " + json.dumps(sub["六_判定"].value_counts().to_dict(), ensure_ascii=False)) if "六_判定" in sub and sub["六_判定"].notna().any() else ""))
    L += ["", "## 固定持有互比（研究五）", ""]
    for s in R5.SETS:
        r = T[(T["集合"] == s) & (T["版本"] == "固定持有互比")]
        L.append(f"- {s}：" + "；".join(f"{x['規則']} − {x['基準']} {_pp(x['五_mean'])}（{x['五_判定']}）" for _, x in r.iterrows()))
    L += ["", "## 讀法與閘", "",
          "- 進場集合 ＝ results5/exits.csv.gz 原列；出場函式 ＝ research5._hold／_stop 原式；成本 0.585%；判定用語、非重疊 n（60 日）、前後段（2021-01-04）照原件",
          f"- 資料：全部腿在釘住的快照 edc6f 重算（原件的 2026-09-18 分支 data/ 還原因子之後有更新；抽 400 筆 H60 有 41 筆差 1e−8～3e−4）；"
          f"閘：快照重算的「規則 − H60」判定 ＝ 原件存檔判定 {S['閘_快照重算的−H60判定＝原件']}（逐集合逐規則見 summary.json）",
          "- ★ 主版把停損規則的時間上限改成 H（與同長度固定持有比）；字面版（上限 60 對 H20／H120）另列",
          f"- H120 在資料尾算不出的列不進該配對：可算列 {S['H120 可算列']}",
          "- 研究六：w ＝ min(2% ÷ d, 20%)，固定持有的 d ＝ 3×ATR14 ÷ 進場價（原件定案）；研究六沒有「只是保險」這個用語（原件同）",
          "- ⚠ 字面版（停損上限 60 對 H20）的「期望值較好」主要是持有期長短差（H60 − H20 本身就 +3～+5 點），⛔ 不讀成停損有用", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
