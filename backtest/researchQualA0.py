# -*- coding: utf-8 -*-
"""PREREG品質 seq1【A0 定案重跑】（台股策略線 登錄 sha 24e7fb594193b9c0；裁定 seq256 發號、seq245 §三「A2 暫定、A0 落地重跑定案」、
seq259 §四、0807（A0 落地後重跑定案）、seq275（全數補齊即排品質 A0 重跑））。回測線，2026-10-04。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchQualA0 [--procs 4] [--reps 1000]
    查核：同一支加 --check ⇒ 跑既有獨立查核 researchQual_check（⛔ 不 import 本體）並把它的路徑換成 A0 版（OUT、財報快照），再加 A2→A0 差異表

⭐ 讀法寫死時間：2026-10-04 11:50（台北）；寫死前 ⛔ 沒看 A0 版任何數字（A2 版 resultsQual 已交、已看過，登錄與裁定都已知）。

═══ 與 A2 版（researchQual.py，2026-09-28）唯一的差別 ═══
  財報快照：~/msdata/a2dadbca4a ⇒ ~/msdata/1fb8815e81（tw-stock-data main；fin_hist 兩版逐檔相同 diff 0；filing_dates.csv 由 FY2015 一部分 ⇒ 2019～2026 全部）
  ⇒ 程式一字不改（import researchQual、只換 FD／OUT／標籤），所以 Q1～Q4、挑格、假訊號種子、換股簿全同 A2 版；只有「可用日」因時戳變多而改變
═══ A0 可用日讀法（逐字沿用 researchQual B2 的程式；本件逐條核對）═══
  有 t57sb01 時戳 ⇒ 該季 uploaded_at 的日期取【最早】（groupby min，資料庫 10-04 ①：⛔ 不取最晚）⇒ 之後第一個交易日（盤中盤後不分；
    登錄大師三套 §一「上傳日期的下一個交易日」同口徑。資料庫信引「seq263」定時點，查無此內容，見 researchMaster4 說明）
  換股日 e 可用 ⇔ 可用日位置 ≤ e（e 開盤買、可用日當天開盤前已知）——A2 版原樣
  缺時戳 ⇒ 仍用 A2 的「法定期限之後第一個交易日 ＋5 個交易日」（執行者補：A0 只補到 2019～2026（使用者 09-29 指示），2019 以前的季與 2019～2020 少數 Q1／Q3 沒有時戳；
    登錄寫「A0 落地重跑」沒寫缺時戳怎麼辦 ⇒ 沿用 A2 的保守補位、⛔ 不改成法定期限當天（seq231 禁 A1）；計數必報）
  ⚠ 影響範圍：探索段 2017-03～2018 與早年段 2014～2016 幾乎全是補位（＝ A2 原樣）；A2→A0 的差主要落在 2019 起（探索段後段、確認段全段）
輸出 backtest/resultsQualA0/（cells.csv、picks.csv.gz、fake.csv.gz、summary.json、diff_A2_A0.json、check.json）
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchQual as RQ

MS_SHA = "1fb8815e81aa53edf91aacb8ebb4125c716ead3f"
OUT = "backtest/resultsQualA0"
OLD = "backtest/resultsQual"
TAG = "季財報可用日 A0 定案（t57sb01 該季最早上傳日之後第一個交易日；缺時戳沿用 A2 的法定期限＋5 交易日）"


def patch():
    RQ.FIN_SHA = MS_SHA
    RQ.FD = os.path.expanduser(f"~/msdata/{MS_SHA}/data")
    RQ.OUT = OUT
    RQ.A2TAG = TAG


def avail_counts():
    """A2 版與 A0 版各季的可用日來源與位移（主快照日曆）。"""
    out = {}
    cal = None
    for nm, sha in (("A2", "a2dadbca4ad165fc31f76edf67be34ee8ee7bc38"), ("A0", MS_SHA)):
        RQ.FD = os.path.expanduser(f"~/msdata/{sha}/data")
        Q = RQ.load_fin(lambda m: None)
        if cal is None:
            RQ.D.DATA = RQ.H2.H2D
            cal = RQ.D.load_calendar()
        pos, src = RQ.avail_pos(Q, cal)
        out[nm] = (Q[["sid", "y", "q"]].assign(pos=pos, src=src))
    patch()
    m = out["A2"].merge(out["A0"], on=["sid", "y", "q"], suffixes=("_a2", "_a0"))
    m["shift"] = m["pos_a0"] - m["pos_a2"]
    res = {}
    for lo, hi, nm in ((2013, 2018, "2013～2018"), (2019, 2026, "2019～2026")):
        x = m[(m["y"] >= lo) & (m["y"] <= hi)]
        res[nm] = {"季數": int(len(x)), "A2 有時戳": int((x["src_a2"] == "ts").sum()), "A0 有時戳": int((x["src_a0"] == "ts").sum()),
                   "可用日變動的季": int((x["shift"] != 0).sum()), "變早（交易日）中位": float(-x.loc[x["shift"] < 0, "shift"].median()) if (x["shift"] < 0).any() else 0.0,
                   "變晚的季": int((x["shift"] > 0).sum())}
    return res


def diff():
    old = pd.read_csv(os.path.join(OLD, "cells.csv")); new = pd.read_csv(os.path.join(OUT, "cells.csv"))
    so = json.load(open(os.path.join(OLD, "summary.json"), encoding="utf-8")); sn = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    k = ["格", "段"]
    m = old.merge(new, on=k, suffixes=("_A2", "_A0"))
    m["年化差（點）"] = (m["年化_A0"] - m["年化_A2"]) * 100
    flip = m[(m["標籤_A2"] != m["標籤_A0"]) & m["判定格_A2"]]
    po = pd.read_csv(os.path.join(OLD, "picks.csv.gz"), dtype={"sid": str}); pn = pd.read_csv(os.path.join(OUT, "picks.csv.gz"), dtype={"sid": str})
    res = {"挑中格": {fam: {"A2": so["挑格"][fam]["格"], "A0": sn["挑格"][fam]["格"],
                         "件標籤 A2": so["挑格"][fam]["件標籤"], "件標籤 A0": sn["挑格"][fam]["件標籤"],
                         "確認 A2": [so["挑格"][fam]["確認"]["年化"], so["挑格"][fam]["確認"]["回落"], so["挑格"][fam]["確認"]["標籤"]],
                         "確認 A0": [sn["挑格"][fam]["確認"]["年化"], sn["挑格"][fam]["確認"]["回落"], sn["挑格"][fam]["確認"]["標籤"]],
                         "早年 A2": [so["挑格"][fam]["早年"]["年化"], so["挑格"][fam]["早年"]["標籤"]], "早年 A0": [sn["挑格"][fam]["早年"]["年化"], sn["挑格"][fam]["早年"]["標籤"]],
                         "假訊號確認 p A2": so["挑格"][fam]["假訊號_確認"]["p（隨機年化 ≥ 本格）"], "假訊號確認 p A0": sn["挑格"][fam]["假訊號_確認"]["p（隨機年化 ≥ 本格）"]}
                   for fam in ("甲", "乙")},
           "判定格標籤翻轉（段 × 格）": flip[["格", "段", "標籤_A2", "標籤_A0", "年化_A2", "年化_A0"]].to_dict("records"),
           "全格年化差（點）": {seg: {"中位": float(g["年化差（點）"].median()), "最大絕對": float(g["年化差（點）"].abs().max())} for seg, g in m.groupby("段")}}
    for fam in ("甲", "乙"):
        kk = sn["挑格"][fam]["格"]
        a = po[(po["族"] == fam)]; b = pn[(pn["族"] == fam)]
        if so["挑格"][fam]["格"] == kk:
            sa = a.groupby(["世界", "換股日"])["sid"].apply(set); sb = b.groupby(["世界", "換股日"])["sid"].apply(set)
            j = sa.index.intersection(sb.index)
            res["挑中格" ][fam]["同格名單：換股日中有不同的比例"] = float(np.mean([sa[x] != sb[x] for x in j]))
            res["挑中格"][fam]["同格名單：平均每次不同檔數"] = float(np.mean([len(sa[x] ^ sb[x]) / 2 for x in j]))
    res["可用日來源"] = avail_counts()
    json.dump(res, open(os.path.join(OUT, "diff_A2_A0.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    print(json.dumps(res, ensure_ascii=False, indent=1, default=float))


def check():
    import importlib.util
    spec = importlib.util.spec_from_file_location("qcheck", os.path.expanduser("~/tw-p17/backtest/researchQual_check.py"))
    QC = importlib.util.module_from_spec(spec); spec.loader.exec_module(QC)
    QC.OUT = os.path.join(QC.B, "resultsQualA0")
    QC.FD = os.path.expanduser(f"~/msdata/{MS_SHA}/data")
    QC.main()


def main():
    if "--check" in sys.argv:
        return check()
    if "--diff" in sys.argv:
        patch(); return diff()
    patch()
    RQ.main()
    s = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    s["沿革"] = "A2 暫定版（resultsQual，2026-09-28）⇒ A0 定案重跑（本版）；程式一字不改、只換財報快照（filing_dates 補齊 2019～2026）"
    s["讀法寫死"] = "2026-10-04 11:50（台北）"
    json.dump(s, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    diff()


if __name__ == "__main__":
    main()
