# -*- coding: utf-8 -*-
"""營量 v1 創新板口徑（裁定 seq270 §五；描述、不計 N、不改營量 v1 定義）。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLinno
    簡短查核：~/tw-p16/.venv/bin/python backtest/researchYLinno_check.py

讀法（⭐ 看數字前寫定）：
  創新板 ＝ 該股在【訊號／進場那天】stocks/<代號>.csv 的 name 含「-創」或「-KY創」（例 6854 錼創科技-KY創；universe_gate 第三道閘只認「-創」⇒ 這 4 檔 6854、6924、7823、7827 在母體裡）（逐列名稱 ＝ 當時的名稱；轉板後改名者照當時算）；另報 meta/stocks.csv 最新名稱口徑
  ① 營量 v1 主窗實際成交 ＝ resultsYLlist/audit_seed0.csv.gz 的買進列（717 筆）⇒ 幾筆是創新板
  ② 剔除創新板【訊號】後重跑：營量 v1 T1 版（listexit_lines.setup_t1(t1=True)；researchT1fix #13 同）、stop_force 開、種子 0（營量 relvol 不抽籤）
     ⇒ 主窗 2017-03-02～2026-08-24、探索 2017-03-02～2021-12-30、確認 2022-01-03～2026-08-24 的年化／回落，對原版（同跑、閘 ＝ resultsT1fix c13 t1 r0）
  ③ 早年段（2012-06～2014-12，早年版面只上市）：創新板 2021 年才開板 ⇒ 依構造 0 筆、剔除後不變（照實寫；另核早年訊號名稱確實 0 筆含「-創」）
  差距 ≥ 0.5 個百分點（年化或回落）⇒ 標出
輸出 backtest/resultsYLinno/：summary.json、REPORT.md、innov_trades.csv
"""
from __future__ import annotations

import json
import re
import os

import numpy as np
import pandas as pd

from . import listexit_lines as L
from . import rerun17 as RR
from . import research11 as R
from . import data as D

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsYLinno")
INNO_RE = r"-(?:KY)?創"                # 創新板：名稱含「-創」或「-KY創」（⚠ universe_gate.exclude_innovation 只認「-創」、漏掉「-KY創」）
SEGS = {"主窗": ("2017-03-02", "2026-08-24"), "探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}


def names_on(sid, dates):
    x = pd.read_csv(os.path.join(D.DATA, "stocks", sid + ".csv"), dtype={"date": str}, usecols=["date", "name"]).drop_duplicates("date").set_index("date")["name"]
    x = x.reindex(sorted(set(x.index) | set(dates))).ffill()
    return [str(x.get(d, "")) for d in dates]


def main():
    os.makedirs(OUT, exist_ok=True)
    ctx = L.setup_t1(print, t1=True)
    G = RR._G; cal = ctx["cal"]; A = G["AND"]; e = A["entry_pos"].to_numpy()
    sig = A[(e >= G["w0"]) & (e <= G["w1"])].copy()
    SF = R.stop_force_days(R.valid_from_data(sorted(ctx["closes"]), ctx["mk"], cal), G["w1"])
    meta = pd.read_csv(os.path.join(D.DATA, "meta", "stocks.csv"), dtype=str).drop_duplicates("stock_id").set_index("stock_id")["name"]
    # 訊號當天名稱
    sig["date"] = [str(cal[p].date()) for p in sig["pos"]]
    nm = {}
    for s, g in sig.groupby("sid"):
        for d, n_ in zip(g["date"], names_on(s, list(g["date"]))):
            nm[(s, d)] = n_
    sig["name_then"] = [nm[(s, d)] for s, d in zip(sig["sid"], sig["date"])]
    sig["創新板"] = sig["name_then"].str.contains(INNO_RE, regex=True)
    sig["創新板_最新名"] = sig["sid"].map(meta).fillna("").str.contains(INNO_RE, regex=True)
    # ① 實際成交
    au = pd.read_csv(os.path.join(HERE, "resultsYLlist", "audit_seed0.csv.gz"), dtype={"sid": str})
    buys = au[au["side"] == "buy"].copy()
    buys["date"] = [str(cal[int(t)].date()) for t in buys["t"]]
    bn = {}
    for s, g in buys.groupby("sid"):
        for d, n_ in zip(g["date"], names_on(s, list(g["date"]))):
            bn[(s, d)] = n_
    buys["name_then"] = [bn[(s, d)] for s, d in zip(buys["sid"], buys["date"])]
    buys["創新板"] = buys["name_then"].str.contains(INNO_RE, regex=True)
    buys["創新板_最新名"] = buys["sid"].map(meta).fillna("").str.contains(INNO_RE, regex=True)
    buys[buys["創新板"] | buys["創新板_最新名"]].to_csv(os.path.join(OUT, "innov_trades.csv"), index=False, encoding="utf-8-sig")
    # ② 重跑
    def run(sg):
        o = R.simulate_mtm(sg, "H60", 20, np.random.default_rng(7000), ctx["closes"], ctx["opens"], ctx["ncal"], return_equity=True,
                           log=[], d_max=None, pick="relvol", queue_days=0, stop_force=SF)
        eq = np.asarray(o["equity"], float); out = {}
        for k, (x, y) in SEGS.items():
            a_, b_ = int(cal.searchsorted(pd.Timestamp(x))), int(cal.searchsorted(pd.Timestamp(y)))
            c_, m_, _ = RR.win_metrics(eq, o["first"], o["end"], a_, b_)
            out[k] = [float(c_), float(m_)]
        out["trades"] = int(o["trades"])
        return out
    base = run(sig.drop(columns=["date", "name_then", "創新板", "創新板_最新名"]))
    excl = run(sig[~sig["創新板"]].drop(columns=["date", "name_then", "創新板", "創新板_最新名"]))
    excl2 = run(sig[~sig["創新板_最新名"]].drop(columns=["date", "name_then", "創新板", "創新板_最新名"]))
    ref = pd.read_csv(os.path.join(HERE, "resultsT1fix", "seeds.csv.gz"), float_precision="round_trip")
    ref = ref[(ref["key"] == "c13") & (ref["var"] == "t1") & (ref["r"] == 0)].iloc[0]
    gate = repr(base["主窗"][0]) == repr(float(ref["cagr"])) and repr(base["主窗"][1]) == repr(float(ref["mdd"]))
    diff = {k: [excl[k][0] - base[k][0], excl[k][1] - base[k][1]] for k in SEGS}
    flag = {k: bool(abs(v[0]) >= 0.005 or abs(v[1]) >= 0.005) for k, v in diff.items()}
    # ③ 早年
    from . import researchV as V
    from . import researchYear1M as Y
    V.body_setup("main", print)
    ecal = V._B["cal"]; ET = Y.sig_of(13, "mtm", V._B["w0"], V._B["w1"])
    en = []
    for s, g in ET.groupby("sid"):
        ds = [str(ecal[p].date()) for p in g["pos"]]
        en += names_on(s, ds)
    early_n = int(sum(bool(re.search(INNO_RE, x)) for x in en))
    S = {"件": "營量 v1 創新板口徑（seq270 §五；描述）", "創新板定義": "訊號／進場當天名稱含「-創」或「-KY創」（另報最新名稱口徑）",
         "① 主窗實際成交（audit_seed0 買進）": {"筆": int(len(buys)), "創新板（當天名稱）": int(buys["創新板"].sum()), "創新板（最新名稱）": int(buys["創新板_最新名"].sum()),
                                           "檔": sorted(set(buys.loc[buys["創新板"] | buys["創新板_最新名"], "sid"]))},
         "主窗訊號": {"列": int(len(sig)), "創新板（當天名稱）": int(sig["創新板"].sum()), "創新板（最新名稱）": int(sig["創新板_最新名"].sum())},
         "閘（原版種子 0 主窗 ＝ resultsT1fix c13 t1 r0）": gate,
         "原版（種子 0）": base, "剔除創新板（當天名稱）": excl, "剔除創新板（最新名稱，描述）": excl2,
         "差（剔除 − 原版；[年化, 回落]）": diff, "差 ≥ 0.5 點": flag,
         "早年": {"早年訊號": int(len(ET)), "名稱含「-創」": early_n, "結論": "創新板 2021 年才開板 ⇒ 早年段 0 筆、剔除後不變（依構造，未重跑）"}}
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    P = lambda x: f"{x * 100:+.2f}%"
    Rp = ["# 營量 v1 創新板口徑（裁定 seq270 §五；描述、不改定義）", "",
          f"**結論：主窗實際成交 {len(buys)} 筆中創新板 {int(buys['創新板'].sum())} 筆（最新名稱口徑 {int(buys['創新板_最新名'].sum())} 筆）；"
          f"剔除創新板訊號後 主窗 {P(excl['主窗'][0])}／{P(excl['主窗'][1])}（原版 {P(base['主窗'][0])}／{P(base['主窗'][1])}）、"
          f"確認 {P(excl['確認'][0])}／{P(excl['確認'][1])}（原版 {P(base['確認'][0])}／{P(base['確認'][1])}）；早年 0 筆不變；"
          f"差 ≥ 0.5 點：{[k for k, v in flag.items() if v] or '無'}。**", "",
          "| 段 | 原版 年化／回落 | 剔除創新板 | 差（點） | ≥ 0.5 點 |", "|---|---|---|---|---|"]
    for k in SEGS:
        Rp.append(f"| {k} | {P(base[k][0])}／{P(base[k][1])} | {P(excl[k][0])}／{P(excl[k][1])} | {diff[k][0] * 100:+.2f}／{diff[k][1] * 100:+.2f} | {'⚠ 是' if flag[k] else ''} |")
    Rp.append(f"| 早年 | 不變 | 不變 | 0 | |")
    Rp += ["", f"- 閘：原版種子 0 主窗 ＝ resultsT1fix c13 t1 r0：{gate}", f"- 最新名稱口徑剔除（描述）：{json.dumps(excl2, ensure_ascii=False)}",
           "- 創新板股票明細：innov_trades.csv", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(Rp))
    print(Rp[2])
    if not gate:
        raise SystemExit("⛔ 閘不過")


if __name__ == "__main__":
    main()
