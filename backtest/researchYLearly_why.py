# -*- coding: utf-8 -*-
"""營量訊號前一天為什麼不在「即將達成」名單上（使用者追問「卡在那個條件？」的另一半；描述、不計 N、不改判定）。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLearly_why
    簡短查核：~/tw-p16/.venv/bin/python backtest/researchYLearly_why_check.py

對象：主窗營量 AND 訊號表（T1、entry_pos ∈ 主窗）每一筆訊號 T（訊號根 k），看 T−1（j ＝ k−1）的狀態。
名單 ＝ researchYLearly 可執行臂（T−1：AND 營收＋5 取 3 恰 2 分＋所需隔日漲幅 ≤ x＋名單 20 根去重），直接讀 resultsYLearly/rows_主.csv.gz 的 sel_x 欄。
分類（互斥、依序判；協調者 1～6，本線加 0 與把「其他」拆細）：
  0 前一天在名單上（x 選入）
  1 T−1 營收條件還沒成立（另拆：T 才進新一期營收列／其他）
  2 T−1 分數 ≤ 1（一天補齊 ≥ 2 條；另報 T 當天新達成的條件組合）
  3 T−1 分數 ＝ 2，但沒有任何價格條件補得到（所需漲幅 ＝ ∞：只剩量 c3，或 c2 前 19 根漲停不到 2 次）
  4 T−1 分數 ＝ 2，所需漲幅 ＞ x
  5 T−1 分數 ≥ 3（前一天已成立），被 20 根去重擋住，T 才出
  6 其他（拆：T−1 不是合格根〔前 20 根壞根／事件根等〕、名單去重擋住〔分數 2、漲幅 ≤ x 但 20 根內已選過〕、…）
  ⚠ 讀法：1 先判 ⇒ 分數 ≤ 1 且營收也沒成立的歸 1；2～5 都要求 T−1 營收已成立；3／4 要求 T−1 是合格根（名單本來就要求），不合格根歸 6
每類：筆數、占比、H60 平均淨（扣成本，只算出場算得出的）；另報 T 當天新達成的條件裡 c3（爆量）的比例
輸出 backtest/resultsYLearly/why/
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import rerun17 as RR
from backtest import research11 as R11
from backtest import researchYLearly as YE

OUT = "backtest/resultsYLearly/why"
COST = R11.COST
XS = (0.03, 0.05, 0.10)
CAT = {0: "0 前一天在名單上", 1: "1 T−1 營收還沒成立", 2: "2 T−1 分數 ≤ 1（一天補 ≥ 2 條）", 3: "3 T−1 分數 2、只剩量或補不到（漲幅 ∞）",
       4: "4 T−1 分數 2、所需漲幅 ＞ x", 5: "5 T−1 已成立、被 20 根去重擋", 6: "6 其他"}


def main():
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    from backtest import researchT1fix as T1
    ctx = T1.build_ctx(True)
    RR.use_snapshot()
    cal, mk, w0, w1 = ctx["cal"], ctx["mk"], ctx["w0"], ctx["w1"]
    SIG = ctx["sig13"].copy()
    PAN = YE.load_panel(os.path.join(RR.OUT, "sig_edc6f", "panel_rev.csv.gz"))
    ROWS = pd.read_csv("backtest/resultsYLearly/rows_主.csv.gz", dtype={"sid": str})
    RJ = {(s, int(j)): r for s, j, r in zip(ROWS["sid"], ROWS["j"], ROWS.to_dict("records"))}
    out = []
    for sid, g in SIG.groupby("sid"):
        B = R11.load_bars(sid, mk.get(sid, "twse"), cal)
        idx = B["idx"]; cond, score, elig, nb_sig, _ = YE.feats(B)
        sp, hi = PAN.get(sid, (np.zeros(0, int), np.zeros(0, bool)))

        def andf(pos):
            j_ = int(np.searchsorted(sp, pos, side="right")) - 1
            return bool(j_ >= 0 and pos - sp[j_] <= YE.STALE and hi[j_]), j_
        # 3/5 候選（含 AND 前）去重鏈：找 T−1 若為候選、被哪一根擋
        last = -10 ** 9; picked = []
        for k_ in np.flatnonzero(elig & (score >= 3)):
            if k_ - last > YE.DD:
                picked.append(int(k_)); last = k_
        pk = np.array(picked)
        for r in g.itertuples():
            k = int(r.k); j = k - 1; pj = int(idx[j]); pk_ = int(idx[k])
            assert pk_ == int(r.pos)
            a_j, rj = andf(pj); a_k, rk = andf(pk_)
            newc = [YE.CN[q] for q in range(5) if cond[q, k] and not cond[q, j]]
            lost = [YE.CN[q] for q in range(5) if cond[q, j] and not cond[q, k]]
            row = {"sid": sid, "k": k, "T": pk_, "entry_pos": int(r.entry_pos), "g_H60": float(r.g_H60) if r.xpos_H60 >= 0 else np.nan,
                   "T−1分數": int(score[j]), "T分數": int(score[k]), "T−1合格根": bool(elig[j]), "T−1營收": a_j, "T營收": a_k,
                   "T−1未達": "+".join(YE.CN[q] for q in range(5) if not cond[q, j]), "T新達成": "+".join(newc), "T失去": "+".join(lost),
                   "營收細": ("T 才進新一期營收列" if (not a_j and rk > rj) else ("T−1 沒有面板列" if rj < 0 else ("T−1 最新列過期（>45）" if pj - sp[rj] > YE.STALE else "T−1 最新列 rev_hi24 假"))) if not a_j else ""}
            rr = RJ.get((sid, j))
            row["名單列存在"] = rr is not None
            row["所需漲幅"] = float(rr["所需漲幅"]) if rr is not None else np.nan
            row["最容易"] = rr["最容易"] if rr is not None else ""
            # 5 類的擋路根
            prv = pk[pk < k]
            row["前一個選入候選"] = int(prv[-1]) if len(prv) else -1
            for x in YE.XS:
                xn = YE.xname(x)
                if rr is not None and bool(rr[f"sel_{xn}"]):
                    c, sub = 0, "在名單"
                elif not a_j:
                    c, sub = 1, row["營收細"]
                elif score[j] <= 1:
                    c, sub = 2, ""
                elif score[j] == 2 and not elig[j]:
                    c, sub = 6, "T−1 分數 2 但不是合格根"
                elif score[j] == 2 and not np.isfinite(row["所需漲幅"]):
                    c, sub = 3, ("只剩量 c3" if "c3" in row["T−1未達"] else "c2 補不到")
                elif score[j] == 2 and row["所需漲幅"] > x + 1e-12:
                    c, sub = 4, ""
                elif score[j] == 2:
                    c, sub = 6, "分數 2、漲幅 ≤ x，但名單 20 根去重擋"
                elif score[j] >= 3 and elig[j]:
                    c, sub = 5, ""
                else:
                    c, sub = 6, "T−1 分數 ≥ 3 但不是合格根"
                row[f"類_{xn}"] = c; row[f"細_{xn}"] = sub
            out.append(row)
    R = pd.DataFrame(out).sort_values(["T", "sid"]).reset_index(drop=True)
    R = R[(R["entry_pos"] >= w0) & (R["entry_pos"] <= w1)].reset_index(drop=True)
    R.to_csv(os.path.join(OUT, "signals_why.csv.gz"), index=False, float_format="%.9g")
    # 一致性：名單列存在 ⇔ T−1 合格根＋分數 2＋營收
    exp = R["T−1合格根"] & (R["T−1分數"] == 2) & R["T−1營收"]
    S = {"訊號筆數": int(len(R)), "H60 算得出": int(R["g_H60"].notna().sum()),
         "自檢：名單列存在 ⇔ T−1 合格根＋分數 2＋營收（不符筆數）": int((exp != R["名單列存在"]).sum()),
         "自檢：5 類的 T−1 都在 3/5 候選鏈之前一個選入的 20 根內（不符筆數）": 0}
    c5 = R[R["類_x5"] == 5]
    S["自檢：5 類的 T−1 都在 3/5 候選鏈之前一個選入的 20 根內（不符筆數）"] = int(((c5["k"] - 1) - c5["前一個選入候選"] > YE.DD).sum() + (c5["前一個選入候選"] < 0).sum())
    TB = {}
    for x in XS:
        xn = YE.xname(x); rows = []
        for c in range(7):
            m = R[f"類_{xn}"] == c; gg = R.loc[m, "g_H60"].dropna() - COST
            rows.append({"類": CAT[c], "筆數": int(m.sum()), "占比": float(m.mean()), "H60 平均淨": float(gg.mean()) if len(gg) else np.nan,
                         "H60 中位淨": float(gg.median()) if len(gg) else np.nan, "T 新達成含 c3 比例": float(R.loc[m, "T新達成"].str.contains("c3").mean()) if m.any() else np.nan,
                         "細": dict(Counter(R.loc[m, f"細_{xn}"]).most_common()) if c in (1, 3, 6) else {}})
        TB[xn] = rows
        pd.DataFrame(rows).to_csv(os.path.join(OUT, f"table_{xn}.csv"), index=False, float_format="%.6g")
    S["分類"] = TB
    m2 = R["類_x5"] == 2
    S["類 2：T 當天新達成的條件組合"] = dict(Counter(R.loc[m2, "T新達成"]).most_common())
    S["類 2：T−1 分數分佈"] = {int(k_): int(v) for k_, v in R.loc[m2, "T−1分數"].value_counts().sort_index().items()}
    S["全部訊號：T 當天新達成含 c3 比例"] = float(R["T新達成"].str.contains("c3").mean())
    S["全部訊號：T 當天新達成的條件（逐條出現比例）"] = {c: float(R["T新達成"].str.contains(c).mean()) for c in YE.CN}
    S["全部訊號：T 當天新達成的組合（前 10）"] = dict(Counter(R["T新達成"]).most_common(10))
    S["類 4（x5）：最容易那條"] = dict(Counter(R.loc[R["類_x5"] == 4, "最容易"]).most_common())
    S["類 4（x5）：所需漲幅分位"] = {q: float(R.loc[R["類_x5"] == 4, "所需漲幅"].quantile(q / 100)) for q in (10, 25, 50, 75, 90)}
    for c in (0, 4):
        mc = R["類_x5"] == c
        S[f"類 {c}（x5）：T 當天新達成的條件組合"] = dict(Counter(R.loc[mc, "T新達成"]).most_common(8))
        S[f"類 {c}（x5）：T 只靠量 c3 補上的比例"] = float((R.loc[mc, "T新達成"] == "c3").mean())
    S["類 3 為什麼是 0"] = "分數 2 ⇒ 未達 3 條；補不到（∞）的只有 c3（量）與 c2（前 19 根漲停 < 2 次）兩條 ⇒ 第三條必是 c1／c4／c5 之一、所需漲幅有限 ⇒ 結構上落不進 3；「其實是靠量補上的」看類 0／4 的「T 只靠量 c3 補上的比例」"
    S["全部訊號 H60 平均淨"] =float((R["g_H60"].dropna() - COST).mean())
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=lambda z: z.item() if hasattr(z, "item") else str(z))
    P = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:+.1f}%"
    NL = chr(10)
    L = ["# 營量訊號前一天為什麼不在名單上（描述、不計 N、不改判定）" + NL,
         "使用者追問（逐字）：「卡在那個條件？」——這份是另一半：真正出訊號的營量訊號，T−1 為什麼不在「即將達成」名單（researchYLearly 可執行臂）上。" + NL,
         f"> 主窗營量 AND 訊號 {S['訊號筆數']} 筆（H60 算得出 {S['H60 算得出']}；全部平均淨 {P(S['全部訊號 H60 平均淨'])}）。分類互斥、依序判；讀法見程式開頭。" + NL,
         "## x＝5%（主）" + NL, "| 類 | 筆數 | 占比 | H60 平均淨 | T 新達成含 c3 |", "|---|---|---|---|---|"]
    for r in TB["x5"]:
        L.append(f"| {r['類']} | {r['筆數']} | {r['占比']:.1%} | {P(r['H60 平均淨'])} | {'—' if not np.isfinite(r['T 新達成含 c3 比例']) else format(r['T 新達成含 c3 比例'], '.0%')} |")
    L.append(NL + "## x＝3%／10%（只有 0、4、6 會變）" + NL)
    L.append("| 類 | x3 筆數（占比） | x3 平均淨 | x10 筆數（占比） | x10 平均淨 |"); L.append("|---|---|---|---|---|")
    for a_, b_ in zip(TB["x3"], TB["x10"]):
        L.append(f"| {a_['類']} | {a_['筆數']}（{a_['占比']:.1%}） | {P(a_['H60 平均淨'])} | {b_['筆數']}（{b_['占比']:.1%}） | {P(b_['H60 平均淨'])} |")
    L.append(NL + "## 細項" + NL)
    for r in TB["x5"]:
        if r["細"]:
            L.append(f"- {r['類']}：" + "、".join(f"{k_} {v}" for k_, v in r["細"].items()))
    L.append(f"- 類 2 的 T−1 分數：{S['類 2：T−1 分數分佈']}；T 當天新達成組合：" + "、".join(f"{k_} {v}" for k_, v in list(S["類 2：T 當天新達成的條件組合"].items())[:12]))
    L.append(f"- 類 4（x5）最容易那條：{S['類 4（x5）：最容易那條']}；所需漲幅分位 " + "、".join(f"p{q} {P(v)}" for q, v in S["類 4（x5）：所需漲幅分位"].items()))
    for c in (0, 4):
        L.append(f"- 類 {c}（x5）T 當天新達成組合：{S[f'類 {c}（x5）：T 當天新達成的條件組合']}；只靠量 c3 補上 {S[f'類 {c}（x5）：T 只靠量 c3 補上的比例']:.0%}")
    L.append(f"- 類 3 為什麼是 0：{S['類 3 為什麼是 0']}")
    L.append(f"- 全部訊號 T 當天新達成含 c3（爆量）：{S['全部訊號：T 當天新達成含 c3 比例']:.1%}；逐條：" + "、".join(f"{k_} {v:.0%}" for k_, v in S["全部訊號：T 當天新達成的條件（逐條出現比例）"].items()))
    L.append(f"- 全部訊號 T 當天新達成組合前 10：{S['全部訊號：T 當天新達成的組合（前 10）']}")
    L.append(NL + f"自檢：{ {k_: v for k_, v in S.items() if k_.startswith('自檢')} }｜條件代號：c1 20 日漲 30%、c2 20 日漲停 3 次、c3 量 3 倍、c4 站上百日線、c5 創 250 日高")
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write(NL.join(L) + NL)
    log(f"[完] {S['訊號筆數']} 筆｜x5 " + "；".join(f"{r['類']} {r['筆數']}" for r in TB["x5"]) + f"｜c3 新達成 {S['全部訊號：T 當天新達成含 c3 比例']:.1%}｜自檢 { {k_: v for k_, v in S.items() if k_.startswith('自檢')} }")


if __name__ == "__main__":
    main()
