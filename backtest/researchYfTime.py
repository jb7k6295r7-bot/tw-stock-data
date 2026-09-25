# -*- coding: utf-8 -*-
"""PREREG營飆時停（台股策略線登錄 seq1 sha 118f59657e8e0dde；裁定線 seq201：門檻 190／200、補進那檔同樣檢查、NH 起點）：
營飆 v1 買進後第 d 根（20／40／60）「沒反應」就次日開盤換下一檔。回測線，2026-09-26。

    PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYfTime [--procs 3] [--reps 200] [--out 目錄]

執行器、判準、閘、必報 ＝ researchYfStop.run_study（兩件共用）
判定 9 格（N_組合 ＋9）：R0／R10／NH × 20／40／60；線 ＝ yfstop_lines.time_lines、kw ＝ yfstop_lines.time_kw（stop_proceeds="next"）
  補進來那檔：同樣照自己的 (sid, entry_pos) 查線 ⇒ 同樣在它自己的第 d 根檢查（seq201）
  ⚠ 與登錄字面的兩處差別（原因）：
    NH「條件成立時 +∞」⇒ 用 float64 最大有限值 BIG：引擎只比 np.isfinite(線) 的線，字面 +∞ 永遠不觸發（LINES_REPORT §一 12）
    R10「進場價 × 1.10」⇒ 用 ep × 110 ÷ 100：ep × 1.10 在浮點上會偏大一個 ulp（例 50 × 1.10 ＝ 55.00000000000001），
      「收盤剛好漲 10%」會被誤判成沒反應（LINES_REPORT §一 10）；× 110 ÷ 100 在真值可表示時恰好
描述臂（⛔ 不判、不計 N）：ⓐ 整份（＝ 只給 stop_line、不給 stop_proceeds）、ⓑ 跌停賣不掉（stop_block）
  ⓒ「換掉的錢改放著不動」：⛔ 未跑（待引擎：引擎目前沒有「錢留到那檔原本出場日才釋放」）；
     ⚠ ⓐ 在引擎上 ＝「併回一般現金、任何槽空出來時一般新部位可用到」⇒ 與 ⓒ 字面「放著不動到那檔原本出場」不同
輸出 backtest/resultsYfTime/：cells.csv、seeds_arms.csv、summary.json、run.log、REPORT.md
"""
from __future__ import annotations

import argparse
import os

import pandas as pd

from . import researchYfStop as YS

HERE = YS.HERE
KINDS = ["R0", "R10", "NH"]
DS = [20, 40, 60]
CELLS = [f"{k}_{d}" for k in KINDS for d in DS]
KNAME = {"R0": "還在買進價以下", "R10": "漲不到 10%", "NH": "沒創新高"}
TNAME = {"base": "營飆 v1 原樣", **{f"{k}_{d}": f"{k}-{d}（第 {d} 天{KNAME[k]}）" for k in KINDS for d in DS}}


def time_arms(ctx):
    from . import tradability as T
    from . import yfstop_lines as Y
    sig, opens, closes = ctx["sig"], ctx["opens"], ctx["closes"]
    BLK = T.build(set(sig["sid"]), ctx["cal"])
    A = {"base": ({}, "base")}; build = {}
    for k in KINDS:
        for d in DS:
            lines, st = Y.time_lines(sig, opens, closes, YS.bars_of, k, d)
            A[f"{k}_{d}"] = (Y.time_kw(k, lines), "判定"); build[f"{k}_{d}"] = {"線": len(lines), "狀態": st, "sha": Y.lines_sha(lines)}
    for c in CELLS:
        A["a_" + c] = ({kk: vv for kk, vv in A[c][0].items() if kk != "stop_proceeds"}, "ⓐ整份")
    for c in CELLS:
        A["b_" + c] = ({**A[c][0], "stop_block": BLK}, "ⓑ跌停賣不掉")
    return A, build


def time_report(TB, S, OUT):
    T = TB.set_index("arm")
    good = [c for c in CELLS if T.loc[c, "vs_v1"] == "好"]
    Ls = ["# PREREG營飆時停：營飆 v1 買進後第 d 天沒反應就換下一檔（判定 9 格）", "",
          f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。登錄 seq1（sha 118f59657e8e0dde）；裁定 seq201。回測線。", "",
          f"閘：{S['閘']}", "", "## 結果句（⛔ 只照登錄 §五查表）", ""]
    for c in CELLS:
        q = T.loc[c]; k, d = c.split("_")
        s = f"- **{TNAME[c]}**：對 0050「{q['label']}」（年化中位 {YS._p(q['cagr_med'])}、回落中位 {YS._p(q['mdd_med'])}）；對營飆 v1「{q['vs_v1']}」"
        qb = T.loc["b_" + c]
        if qb["label"].replace("（描述）", "") != q["label"] or qb["vs_v1"].replace("（描述）", "") != q["vs_v1"]:
            s += f"；⚠ 開盤跌停／停牌賣不掉版：對 0050「{qb['label'].replace('（描述）', '')}」、對營飆 v1「{qb['vs_v1'].replace('（描述）', '')}」"
        if q["label"] == "合格" and q["vs_v1"] == "好":
            s += f"。營飆 v1 買進後第 {d} 天〔{KNAME[k]}〕就換下一檔，在 2017～2026 這段比原本好；⚠ 事後挑的，要升 v2 須裁定定、並進 2012～2014 驗收段＋前瞻紀錄"
        else:
            s += "。營飆 v1 照原本：抱滿 120 天"
        if good:
            s += f"。試了 9 種，{len(good)} 種好，可能是運氣"
        Ls.append(s + f"。（{YS.FOOT}）")
    Ls += YS.common_tables(T, CELLS, "換掉")
    Ls += YS.desc_table(T, [f"a_{c}" for c in CELLS] + [f"b_{c}" for c in CELLS])
    Ls += ["", "- ⓐ 整份 ＝ 只給 stop_line、不給 stop_proceeds：換掉的錢併回一般現金、空槽照 min(equity/10, 現金) 開一般新部位",
           "- ⓑ 跌停賣不掉 ＝ 加 stop_block（只擋換掉那筆賣出）",
           "- ⓒ「換掉的錢改放著不動」：**待引擎**（⛔ 未跑；引擎目前沒有「錢留到那檔原本出場日才釋放」）。⚠ ⓐ 在引擎上是「併回一般現金」，與 ⓒ 字面不同",
           "- ⚠ 與登錄字面的差別：NH「+∞」用 float64 最大有限值（引擎只比有限的線，+∞ 永遠不觸發）；R10「× 1.10」用 × 110 ÷ 100（× 1.10 浮點偏大一個 ulp，會把剛好漲 10% 誤判成沒反應）",
           "- 補進來那檔同樣照自己的第 d 根檢查（seq201）；「換掉時報酬」＝ 換掉那天開盤價 ÷ 進場價 − 1；「觸發根」＝ 引擎實際觸發日是進場後第幾根（應 ＝ d，停牌延後除外）", ""]
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(Ls) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--out", default=os.path.join(HERE, "resultsYfTime"))
    a = ap.parse_args()
    names = dict(TNAME); names.update({f"a_{c}": f"ⓐ整份 {TNAME[c]}" for c in CELLS}); names.update({f"b_{c}": f"ⓑ跌停 {TNAME[c]}" for c in CELLS})
    YS.run_study("PREREG營飆時停（登錄 seq1 sha 118f59657e8e0dde；裁定 seq201）", "time", time_arms, a.out, names, CELLS, "9", a.reps, a.procs,
                 {"ⓒ": "待引擎（⛔ 未跑）", "差別": {"NH": "BIG 代 +∞", "R10": "ep×110/100 代 ep×1.10"}, "N帳": {"N_組合": "+9", "不計": "ⓐⓑ、營飆 v1 原樣臂"}},
                 time_report)


if __name__ == "__main__":
    main()
