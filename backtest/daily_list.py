# -*- coding: utf-8 -*-
"""每日名單檔 daily_<資料日>.md（營飆 v1 已達成＋營量 v1 已達成＋營量 v1 即將達成）——回測線，2026-09-28。
依據：市場情報分析線 2109、2130（使用者要每日名單）；裁定 seq270 §四（固定註）、§五（創新板加標）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.daily_list [--procs 2]
    包裝（fetch main ⇒ archive ⇒ 跑本支 ⇒ 複製到信箱 _營量觀察/）：bash ~/tw-p17/backtest/run_daily_list.sh

⛔ 不寫第二份實作：訊號、營收、5 取 3、去重、即將達成全部呼叫 list_yl13_watch.compute（其營收面板 ＝ list_prereg10.build_panel、AND ＝ research13.and_flags，
   閘：近 20 交易日 AND ＝ list_YL13_2026-09-24）；精簡列 ＝ list_yl13_watch.brief_rows；大盤閘 ＝ list_prereg10.regime_arrays（0050 還原收盤 vs 200 日均）
營飆 v1（PREREG10 #1：AND｜大盤閘｜N10｜H120）已達成 ＝ 資料日當天的 AND 訊號 ∧ 資料日（＝ 進場前一個交易日 t−1）大盤閘開（list_prereg10 L5）；出場 ＝ 第 120 個交易日
營量 v1（#13：AND｜無大盤閘｜N20｜relvol｜H60）已達成 ＝ 資料日當天的 AND 訊號（relvol 大者先）；出場 ＝ 第 60 個交易日（list_yl13 同：D.exit_pos(進場, 60)）
出場日超出資料日曆 ⇒ gate_b_status.future_trading_days 外推（未公告休市只扣週末 ⇒ 實際只會更晚）
創新板 ＝ 名稱含「-創」⇒ 加標「創新板（限合格投資人）」
輸出 backtest/resultsDaily/daily_<資料日>.md（包裝再複製到信箱 _營量觀察/）
"""
from __future__ import annotations

import argparse
import os
import time

from . import list_yl13_watch as W
from . import list_prereg10 as LP
from . import data as D
from . import gate_b_status as GB

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsDaily")
NOTE = "營量 v1 目前暫定（實際紀錄觀察中）；名單是看盤參考，照規則收盤成立、隔天開盤才買"
INNO = "創新板（限合格投資人）"


def tag(name):
    return f"｜{INNO}" if "-創" in str(name) else ""


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, "run.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:5.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    X = W.compute(a.procs, log)
    A, B, cal, asof, nxt, sha, S = (X[k] for k in ("A", "B", "cal", "asof", "nxt", "sha", "S"))
    n = len(cal)
    bench, ma, reg = LP.regime_arrays(cal)
    gate_on = bool(reg[n - 1])
    fut, basis = GB.future_trading_days(cal, 2 * 120 + 10)
    cal_ext = cal.append(fut)
    e = n                                                      # 進場 ＝ 下一交易日

    def exit_str(H):
        xp = D.exit_pos(e, H)
        b = basis[xp - n]
        return f"{cal_ext[xp].date()}" + ("（未公告休市只扣週末，實際只會更晚）" if "只扣週末" in b else "")
    reason = lambda r: f"營收 {r['營收期別']} 創 24 月新高、強勢 {int(r['分數'])}/5（{r['已達成']}）"
    L = [f"# 每日名單 {asof}（資料日）", "",
         f"- commit：tw-stock-data main {sha[:10]}｜資料日 {asof}｜下一交易日 {nxt[0].date()}（外推）",
         f"- 營飆大盤閘（前一天 0050 在 200 日線上）：{'開' if gate_on else '關'}（{asof} 0050 還原收盤 {bench[n - 1]:.2f}、200 日線 {ma[n - 1]:.2f}）", "",
         f"## 一、營飆 v1 已達成（{nxt[0].date()} 開盤照規則買；最多 10 檔、候選多於空槽時抽籤）", ""]
    if gate_on and len(A):
        L += [f"- {r['代號']} {r['名稱']}{tag(r['名稱'])}｜{reason(r)}｜出場 {exit_str(120)}（第 120 個交易日收盤）" for r in A.sort_values("代號").to_dict("records")]
    else:
        L.append("- 無" + ("（大盤閘關：今天的營收＋強勢訊號照規則不進場）" if (not gate_on and len(A)) else ""))
    L += ["", f"## 二、營量 v1 已達成（{nxt[0].date()} 開盤照規則買；20 檔、候選多於空槽時 relvol 大者先）", ""]
    if len(A):
        L += [f"- {r['代號']} {r['名稱']}{tag(r['名稱'])}｜{reason(r)}｜relvol 第 {int(r['relvol 排名'])}｜出場 {exit_str(60)}（第 60 個交易日收盤）" for r in A.to_dict("records")]
    else:
        L.append("- 無")
    ar, br = W.brief_rows(A, B)
    L += ["", "## 三、營量 v1 即將達成（最有可能的幾檔；兩天內可能、沒被去重擋住）", "",
          "張數 ＝ 3 倍量門檻金額 ÷（最新收盤 ×（1＋開高幅度））；「8 成」＝ 該張數 × 0.8。", "",
          "| 代號 名稱 | 門檻（億） | 平盤開 張（8 成） | 開高 3% 張（8 成） | 開高 5% 張（8 成） | 還差的價格條件 | 另一條路 |", "|---|---|---|---|---|---|---|"]
    for r in br:
        L.append(f"| {r['代號']} {r['名稱']}{tag(r['名稱'])} | {r['門檻（億）']:.1f} | {r['平盤開 張']:,}（{r['平盤開 8 成']:,}） | {r['開高 3% 張']:,}（{r['開高 3% 8 成']:,}） | "
                 f"{r['開高 5% 張']:,}（{r['開高 5% 8 成']:,}） | {r['還差的價格條件']} | {r['另一條路']} |")
    if not br:
        L.append("| 無 | | | | | | |")
    L += ["", NOTE, ""]
    fn = os.path.join(OUT, f"daily_{asof}.md")
    open(fn, "w", encoding="utf-8").write("\n".join(L))
    log(f"[完] {fn}｜大盤閘 {'開' if gate_on else '關'}｜營量已達成 {list(A['代號']) if len(A) else []}｜即將達成 {[r['代號'] for r in br]}｜閘 {S['閘（近 20 交易日 AND 訊號 ＝ list_YL13_2026-09-24）']['過']}")
    print(fn)


if __name__ == "__main__":
    main()
