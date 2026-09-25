# -*- coding: utf-8 -*-
"""PREREGP9 12 格交件報告（只讀 backtest/resultsP9run/ 的檔 ⇒ 寫 P9_REPORT.md）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchP9run_report

⛔ 不跑引擎、不改任何數；12 格全部照報、⛔ 不挑。判定句照登錄 seq9 §三 的形狀。
唯一另算的：0050 自己的 ≥20% 事件在 log 口徑（researchp9.dd_type scale="log"，＝策略線 ddtype.py 口徑）下的分型（只描述，讀8）。
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsP9run")
RT = dict(float_precision="round_trip")
ORDER = ["A2", "A3", "Ba", "Bb", "Bc", "Ca", "Cc", "Cd", "Ce", "Cf", "Cg", "Ch"]
SHORT = {"base": "基準臂", "A2": "2-A k＝2", "A3": "2-A k＝3", "Ba": "2-B ⓐ +15%", "Bb": "2-B ⓑ 三分位", "Bc": "2-B ⓒ 滿40根",
         "Ca": "2-C ⓐ 個股−10%賣半", "Cc": "2-C ⓒ MA60 下 1.5 slot", "Cd": "2-C ⓓ MA20 下 0.5 slot", "Ce": "2-C ⓔ MA10 下 0.5 slot",
         "Cf": "2-C ⓕ MA60 賣半補回", "Cg": "2-C ⓖ MA20 賣半補回", "Ch": "2-C ⓗ MA10 賣半補回", "Cb_ref": "ⓑ 參照 MA60 下 0.5 slot"}
MA_OF = {"Cc": 60, "Cd": 20, "Ce": 10, "Cf": 60, "Cg": 20, "Ch": 10, "Cb_ref": 60}


def p(x, d=2):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x * 100:+.{d}f}%"


def pp(x, d=2):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x * 100:+.{d}f}pp"


def f3(x):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.4f}"


def g(x, d=1):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.{d}f}".rstrip("0").rstrip(".") if d else f"{x:.0f}"


def main():
    global OUT
    if len(sys.argv) > 1:
        OUT = sys.argv[1]
    TB = pd.read_csv(os.path.join(OUT, "cells.csv"), **RT).set_index("arm")
    CT = pd.read_csv(os.path.join(OUT, "controls.csv"), **RT)
    FK = pd.read_csv(os.path.join(OUT, "fake.csv"), **RT).set_index("cell")
    EV = pd.read_csv(os.path.join(OUT, "events.csv"), **RT)
    A = pd.read_csv(os.path.join(OUT, "seeds_arms.csv"), **RT)
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    CK = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else None
    b50 = S["0050"]; c50 = b50["主窗"]["cagr"]; m50 = b50["主窗"]["mdd"]; r50 = b50["比值"]; v50 = b50["主窗"]["vol"]
    z = TB.loc["base"]
    L = []
    w = L.append

    # ── 判定句
    def verdict(k):
        r = TB.loc[k]
        lab = r["label"]
        if lab == "合格":
            s = "在主窗照新判準合格；⚠ 主窗只當候選（見 §七④），早年段驗收過才算找到"
            if isinstance(r["deep_note"], str) and r["deep_note"]:
                s += f"（{r['deep_note']}）"
        elif lab == "另列":
            s = f"賺得比 0050 多，但風險增加得比報酬多：年化 {p(r['cagr'])}、回落 {p(r['mdd'], 1)}、比值 {f3(r['ratio'])} ⇒ 另段報使用者"
        else:
            s = f"不合格：條件一沒過（年化 {p(r['cagr'])} ≤ 0050 {p(c50)}）"
            s += f"；條件二 比值 {f3(r['ratio'])} {'≥' if r['cond2'] else '＜'} 0050 {f3(r50)}（{'過' if r['cond2'] else '也沒過'}）"
        if k in FK.index and bool(FK.loc[k, "warn"]):
            s = f"⚠ 隨機切換也有 {int(FK.loc[k, 'x_Q'])}／{int(FK.loc[k, 'n'])} 合格｜" + s
        if k in ("Ba", "Bb", "Bc") and r["x_add_n_med"] <= 2:
            s += "｜【結構上近乎不可得】（加成次數中位 ≤ 2）"
        return s

    ratios_b = {k: TB.loc[k, "x_add_short_med"] / TB.loc[k, "x_add_n_med"] for k in ("Ba", "Bb", "Bc")}
    xs_lo, xs_hi = min(ratios_b.values()), max(ratios_b.values())
    labs = {k: TB.loc[k, "label"] for k in ORDER}
    nQ = sum(v == "合格" for v in labs.values()); nR = sum(v == "另列" for v in labs.values()); nF = sum(v == "不合格" for v in labs.values())

    w("# PREREGP9【分批進場與加減碼】12 格：主窗一次跑、一次交件（回測線）")
    w("")
    w(f"產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）；開跑 {S['開跑']}。程式 `backtest/researchP9run.py`（計算）、`researchP9run_report.py`（本報告）、"
      "`researchP9run_check.py`（獨立重算）。⛔ 沒有 commit。")
    w("")
    w("| 項 | 值 |")
    w("|---|---|")
    w("| 登錄 | 台股策略線 PREREGP9 **seq9**（sha 868f99aeeba2fef3，13,568 B，2026-09-25 17:53） |")
    w("| 裁定 | seq162 §四（2-B 現金不足【不加、記次數】；出場＝第 120 根收盤；12 格一次跑；2-D 不跑）｜seq167 §四（面板補 4～8 月；ē／m̄ 主版＝逐種子配對） |")
    w("| 判準 | seq141：主窗 2017-03-02～2026-08-24；條件一 年化 ＞ 0050（嚴格）；條件二 年化÷\\|回落\\| ≥ 0050 比值（未捨入） |")
    w(f"| 0050 同窗 | 年化 {c50!r}（{p(c50, 4)}）／回落 {m50!r}（{p(m50, 4)}）／比值 {r50!r}／年化波動 {p(v50)}／年化÷波動 {f3(b50['年化÷波動'])} |")
    st_ = S["設定"]
    w(f"| 資料 | `{st_['data']}`（edc6f8002f 快照）；日曆 {st_['calendar']} |")
    w(f"| 訊號 | 門檻B（resultsAFC/panel.csv.gz 建）{st_['sig']['窗內']:,} 筆／{st_['sig']['檔']} 檔／{st_['sig']['月']} 月，全在主窗內 |")
    w(f"| 引擎 | research11.simulate_mtm；H120（第 120 根收盤出）、N＝8、停損 none、cash zero、tradable／delist 關；成本 {st_['COST'] * 100:.3f}%（來回） |")
    w(f"| 種子 | default_rng(99000＋r)，r ∈ [0,200)（登錄 §一）；假訊號臂 r ∈ [0,50) × 30 次 |")
    w(f"| ⓑ 旗標 | panel_ext.csv.gz sha256 `{S['閘']['二_panel_ext']['sha256']}`（{S['閘']['二_panel_ext']['位元組']:,} B）；窗內旗標 {S['旗標']['flag_true']:,} 個／{S['旗標']['stocks']} 檔／{S['旗標']['days']} 個量測日（{S['旗標']['panel_ext 量測日']}） |")
    w("")
    w("---")
    w("")
    w("## 〇、結論（12 格全部照報、⛔ 不挑）")
    w("")
    w(f"**12 格：合格 {nQ}、另列 {nR}、不合格 {nF}。** 判定值＝200 顆種子的年化中位、回落中位（P9B_REPORT 取法）。")
    w("")
    w("| 格 | 判定句（登錄 §三 形狀） |")
    w("|---|---|")
    for k in ORDER:
        w(f"| {SHORT[k]} | **{TB.loc[k, 'label']}**｜{verdict(k)} |")
    w("")
    w(f"⭐ 2-B 三格：加成次數中位 {g(TB.loc['Ba', 'x_add_n_med'])}／{g(TB.loc['Bb', 'x_add_n_med'])}／{g(TB.loc['Bc', 'x_add_n_med'])}（ⓐ／ⓑ／ⓒ）"
      f"⇒ {'有格' if any(TB.loc[k, 'x_add_n_med'] <= 2 for k in ('Ba', 'Bb', 'Bc')) else '⛔ 沒有一格'}標「結構上近乎不可得」；"
      f"**現金不足次數是加成的 {xs_lo:.1f}～{xs_hi:.1f} 倍**（照登錄：現金不足【不加、記次數】；各格 現金不足中位 ÷ 加成中位：ⓐ {ratios_b['Ba']:.2f}、ⓑ {ratios_b['Bb']:.2f}、ⓒ {ratios_b['Bc']:.2f}；"
      f"裁定 seq167 引的「2.5～6 倍」是面板補齊前的數：ⓑ 用舊面板時加成中位 23、現金不足 56，補 2026-04～08 量測日後加成中位 {g(TB.loc['Bb', 'x_add_n_med'])}）。")
    w("")
    w(f"⭐ 主窗結果【一律只當候選】（登錄 §七④）；合格或另列的格 ⇒ 排進 PREREGV 同一批早年段（2008-01～2014-12）驗收。本件 ⛔ 不對使用者說「找到」（Bonferroni 按格只在說「找到」時用；本件不到那一步）。")
    w("")

    # ── 一、閘
    G1 = S["閘"]["一_0050錨"]; G3 = S["閘"]["三_rerun17"]
    w("## 一、開跑前閘（三道全過才開跑）")
    w("")
    w("| 閘 | 內容 | 結果 |")
    w("|---|---|---|")
    w(f"| 一 0050 錨 | 主窗年化、回落 repr 逐位元 ＝ 0.24020209886370614／−0.3395700527611012 | {'✅' if G1['逐位元'] else '⛔'} {G1['年化']!r}／{G1['回落']!r} |")
    w(f"| 二 panel_ext | sha256 ＝ d75bf50b…0788 | {'✅ 相同' if S['閘']['二_panel_ext']['相同'] else '⛔'} |")
    w(f"| 三 基準臂設定 | {G3['對象']}：同一支引擎設定換成它的種子 102000＋r（200 顆） | {'✅' if G3['過'] else '⛔'} 年化／回落／波動 200 顆 **逐位元相同**（最大差 {G3['最大絕對差']['cagr']:.0e}／{G3['最大絕對差']['mdd']:.0e}／{G3['最大絕對差']['vol']:.0e}） |")
    w("")
    w(f"⇒ 本件基準臂設定＝rerun17 main 格 0（W1 的策略側、無 tradable／delist）：它的 200 顆年化中位 {p(G3['本件年化中位'])}、回落中位 {p(G3['本件回落中位'])}。"
      f"⚠ **AFC W1**（同 102000 種子、開 tradable＋delist）200 顆是 {p(G3['AFC_W1_200顆（開 tradable＋delist）']['年化中位'])}／{p(G3['AFC_W1_200顆（開 tradable＋delist）']['回落中位'])}，"
      f"差 {pp(G3['與AFC差']['年化中位'])}／{pp(G3['與AFC差']['回落中位'])} ⇒ 那是 tradable＋delist 的差（本件照 researchp9 基準臂與 P9 引擎閘 2 的設定，⛔ 不開）。")
    w(f"⇒ P9 基準臂本身（種子 99000＋r）主窗：年化中位 {p(z['cagr'])}、回落中位 {p(z['mdd'])}（浮動窗舊值 +27.69%／−42.5%，⛔ 不沿用）。")
    w("")

    # ── 二、判定表
    w("## 二、判定表（12 格＋基準臂＋ⓑ 參照臂＋0050）")
    w("")
    w("| 格 | 年化中位 | 回落中位 | 比值 | 年化波動 | 年化÷波動 | 條件一 | 條件二 | 標籤 | 附註 |")
    w("|---|---:|---:|---:|---:|---:|:--:|:--:|:--:|---|")
    w(f"| 0050 同窗 | {p(c50)} | {p(m50)} | {f3(r50)} | {p(v50)} | {f3(b50['年化÷波動'])} | | | | 錨 |")
    for k in ["base"] + ORDER + ["Cb_ref"]:
        r = TB.loc[k]
        judged = k in ORDER
        labcell = f"**{r['label']}**" if judged else "—（不判）"
        note = (r["deep_note"] if isinstance(r["deep_note"], str) else "") if judged else ("不計 N" if k == "base" else "參照、⛔ 不判、不計 N")
        w(f"| {SHORT[k]} | {p(r['cagr'])} | {p(r['mdd'])} | {f3(r['ratio'])} | {p(r['vol'])} | {f3(r['cagr_per_vol'])} | "
          f"{'✅' if r['cond1'] else '✗'} | {'✅' if r['cond2'] else '✗'} | {labcell} | {note} |")
    w("")
    w("條件一＝年化中位 ＞ 0050（嚴格）；條件二＝比值 ≥ 0050 比值（未捨入）。基準臂與 ⓑ 參照臂的 ✅／✗ 只是位置描述、⛔ 不是判定。年化波動、年化÷波動只描述。")
    w("")

    # ── 三、配對差
    w("## 三、對基準臂的逐種子配對差（同顆種子 格 − 基準；p10～p90 是【種子帶】、⛔ 不是信心區間）")
    w("")
    w("| 格 | 年化差 中位 | p10～p90 | 年化變好的種子 | 回落差 中位（正＝變淺） | p10～p90 | 回落變淺的種子 | 年化 p10～p90 | 回落 p10～p90 | 種子合格比例 | 種子另列比例 |")
    w("|---|---:|---|---:|---:|---|---:|---|---|---:|---:|")
    for k in ORDER + ["Cb_ref"]:
        r = TB.loc[k]
        w(f"| {SHORT[k]} | {pp(r['d_cagr_med'])} | {pp(r['d_cagr_p10'])}～{pp(r['d_cagr_p90'])} | {r['d_cagr_pos'] * 100:.0f}% | "
          f"{pp(r['d_mdd_med'])} | {pp(r['d_mdd_p10'])}～{pp(r['d_mdd_p90'])} | {r['d_mdd_pos'] * 100:.0f}% | "
          f"{p(r['cagr_p10'], 1)}～{p(r['cagr_p90'], 1)} | {p(r['mdd_p10'], 1)}～{p(r['mdd_p90'], 1)} | {r['seed_Q_share'] * 100:.1f}% | {r['seed_R_share'] * 100:.1f}% |")
    w(f"| 基準臂 | | | | | | | {p(z['cagr_p10'], 1)}～{p(z['cagr_p90'], 1)} | {p(z['mdd_p10'], 1)}～{p(z['mdd_p90'], 1)} | {z['seed_Q_share'] * 100:.1f}% | {z['seed_R_share'] * 100:.1f}% |")
    w("")

    # ── 四、對照臂
    w("## 四、同平均部位對照（登錄 §四①；⛔ 不計 N）")
    w("")
    w("主版＝**逐種子配對**（每顆種子用自己的 m̄／ē；裁定 seq167 §四）；「中位」「合計」兩版只描述。"
      "類別：格的年化中位、比值兩項都不輸對照 ⇒ 甲'；只一項 ⇒ 乙'；都輸 ⇒ 丙'。")
    w("")
    w("| 格 | 對照 | 版本 | m̄／ē（中位） | 對照 年化中位 | 對照 回落中位 | 對照 比值 | 格 年化中位 | 格 比值 | 年化不輸 | 比值不輸 | **類** | 配對 年化差中位（格−對照） | 配對 回落差中位 |")
    w("|---|---|---|---:|---:|---:|---:|---:|---:|:--:|:--:|:--:|---:|---:|")
    vname = {"paired": "**逐種子配對（主版）**", "median": "中位（描述）", "pooled": "合計（描述）", "paired_p17": "逐種子・P17 兩向成本（描述）"}
    for _, r in CT.iterrows():
        w(f"| {SHORT[r['cell']]} | {r['kind']} | {vname[r['version']]} | {r['param_med']:.4f} | {p(r['cagr'])} | {p(r['mdd'])} | {f3(r['ratio'])} | "
          f"{p(r['cell_cagr'])} | {f3(r['cell_ratio'])} | {'✅' if r['cell_not_lose_cagr'] else '✗'} | {'✅' if r['cell_not_lose_ratio'] else '✗'} | "
          f"{'**' + r['class'] + '**' if r['version'] == 'paired' else r['class']} | {pp(r['pair_d_cagr_med'])} | {pp(r['pair_d_mdd_med'])} |")
    w("")
    w("m̄＝實際成交倍數（2-B：1＋0.5×加成數÷新部位數；ⓒ：現金不足只買 1 slot 的算 1）；m̄ ＞ 1 的對照走 ⓒ 的現金規則。"
      "ē＝該格 [w0, w1] 持股市值÷總資產日平均；ē 對照＝基準臂同顆種子的持股簿、總曝險固定 ē、每月第一個交易日收盤再平衡、現金 0 報酬、成本照引擎慣例（賣出付一次來回）。")
    w("")

    # ── 五、同現金比例 × 0050
    w("## 五、同現金比例 × 0050 對照臂（每一臂、每顆種子；只描述）")
    w("")
    w("日報酬 ＝ 前一日持股比例 × 0050 日報酬（researchAFC 同式）；年化／回落用同一支 window_stats（2,313 日）。")
    w("")
    w("| 格 | 平均持股比例 ē | 同現金比例×0050 年化 | 回落 | 比值 | 位置（描述） | 格 年化 − 它 | 格 回落 − 它 |")
    w("|---|---:|---:|---:|---:|:--:|---:|---:|")
    for k in ["base"] + ORDER + ["Cb_ref"]:
        r = TB.loc[k]
        w(f"| {SHORT[k]} | {r['expo'] * 100:.1f}% | {p(r['x50_cagr'])} | {p(r['x50_mdd'])} | {f3(r['x50_ratio'])} | {r['x50_label']} | "
          f"{pp(r['cagr'] - r['x50_cagr'])} | {pp(r['mdd'] - r['x50_mdd'])} |")
    w("")

    # ── 六、次數
    w("## 六、加成／減碼／賣半補回次數、現金不足、平均持股比例（每顆種子；報中位〔p10～p90〕）")
    w("")
    def q(k, col, d=0):
        r = TB.loc[k]
        if f"{col}_med" not in r or not np.isfinite(r[f"{col}_med"]):
            return "—"
        fmt = (lambda x: f"{x:.{d}f}")
        return f"{fmt(r[f'{col}_med'])}〔{fmt(r[f'{col}_p10'])}～{fmt(r[f'{col}_p90'])}〕"
    w("| 格 | 新部位（筆） | 加減碼動作 | 現金不足 | m̄／ē | 單一部位最大佔比 中位（最差） |")
    w("|---|---:|---|---|---:|---:|")
    for k in ["base"] + ORDER + ["Cb_ref"]:
        r = TB.loc[k]
        if k in ("A2", "A3"):
            act = f"分批加買份數 {q(k, 'x_tr_buys')}；期間已出場未買 {q(k, 'x_tr_unbought')}"
            sh = f"分批現金不足 {q(k, 'x_tr_short')}"
            mb = "—"
        elif k in ("Ba", "Bb", "Bc"):
            act = f"觸發 {q(k, 'x_add_trig')}；**加成 {q(k, 'x_add_n')}**（最少 {r['x_add_n_min']:.0f}、最多 {r['x_add_n_max']:.0f}）"
            sh = f"**想加卻現金不足 {q(k, 'x_add_short')}**"
            mb = f"m̄ {r['mbar_med']:.4f}"
        elif k == "Ca":
            act = f"賣半 {q(k, 'x_trim_n')}"
            sh = "—"; mb = "—"
        elif k in ("Cc", "Cd", "Ce", "Cb_ref"):
            act = f"線下新部位套倍數 {q(k, 'x_mult_n')}"
            sh = f"1.5 slot 現金不足只買 1 slot {q(k, 'x_mult_short')}" if k == "Cc" else "—（m ≤ 1）"
            mb = f"m̄ {r['mbar_med']:.4f}"
        elif k in ("Cf", "Cg", "Ch"):
            act = (f"賣半 {q(k, 'x_rt_sell_events')} 天／{q(k, 'x_rt_sell_n')} 檔次；補回 {q(k, 'x_rt_refill_events')} 天／{q(k, 'x_rt_refill_n')} 檔次")
            sh = f"補回現金不足 {q(k, 'x_rt_refill_short')} 天（最低補回比例 中位 {r['x_rt_refill_fill_min_med']:.3f}）"
            mb = "—"
        else:
            act = "—"; sh = "—"; mb = "—"
        w(f"| {SHORT[k]} | {r['trades']:.0f} | {act} | {sh} | {mb} | {r['maxw'] * 100:.1f}%（{r['maxw_worst'] * 100:.1f}%） |")
    w("")
    w("平均持股比例 ē 見 §五第一欄。平均持有天數：H120 固定第 120 根收盤出、無停損、tradable 關 ⇒ 依構造每筆 120 根（讀11）。")
    w("")
    w("### 6-1 2-B 每顆種子實際加成次數分佈（登錄 §四⑧；現金不足【不加、記次數】）")
    w("")
    w("| 格 | 最少 | p10 | p25 | 中位 | p75 | p90 | 最多 | 加成 ≤ 2 的種子 | 現金不足 中位 | 現金不足 ÷ 加成（中位比） | 標記 |")
    w("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for k in ("Ba", "Bb", "Bc"):
        x = A[A["arm"] == k]["x_add_n"].to_numpy(float)
        qs = np.percentile(x, [10, 25, 50, 75, 90])
        w(f"| {SHORT[k]} | {x.min():.0f} | {qs[0]:g} | {qs[1]:g} | **{np.median(x):g}** | {qs[3]:g} | {qs[4]:g} | {x.max():.0f} | {int((x <= 2).sum())}／{len(x)} | "
          f"{TB.loc[k, 'x_add_short_med']:g} | {ratios_b[k]:.2f} 倍 | {'【結構上近乎不可得】' if np.median(x) <= 2 else '（中位 ＞ 2，不標）'} |")
    w("")
    w("### 6-2 ⓕⓖⓗ 另報（登錄 §四⑦）")
    w("")
    w("| 格 | 賣半（天） | 賣半（檔次） | 補回（天） | 補回（檔次） | 每年多付成本：賣半當下 | 補回金額×COST | 合計（pp／年） | 平均持股比例 ē | 線下天數占比 |")
    w("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for k in ("Cf", "Cg", "Ch"):
        r = TB.loc[k]; n = MA_OF[k]
        w(f"| {SHORT[k]} | {q(k, 'x_rt_sell_events')} | {q(k, 'x_rt_sell_n')} | {q(k, 'x_rt_refill_events')} | {q(k, 'x_rt_refill_n')} | "
          f"{r['rt_cost_sell_pp_yr_med']:.3f} | {r['rt_cost_refill_pp_yr_med']:.3f} | **{r['rt_cost_pp_yr_med']:.3f}**〔{r['rt_cost_pp_yr_p10']:.3f}～{r['rt_cost_pp_yr_p90']:.3f}〕 | "
          f"{r['expo'] * 100:.1f}% | {S['§四④'][str(n)]['線下占比'] * 100:.1f}% |")
    w("")
    w("「每年多付成本」＝ Σ（賣半當天付的成本 ＋ 補回金額 × 0.585%（引擎於該部位出場時才扣））÷ 前一日權益，主窗合計 ÷ 9.44 年（讀9）。")
    w("")

    # ── 七、假訊號臂
    w("## 七、假訊號臂（登錄 §四②；ⓒ～ⓗ；⛔ 不計 N）")
    w("")
    w("線上／線下狀態以連續區段為單位打亂（線下段、線上段各自打亂順序後照原交替接回 ⇒ 段長分佈、段數、線下比例全保留；範圍 [w0−1, w1]），"
      "30 次 × r ∈ [0,50)，每次取 50 顆的年化中位、回落中位照同一判準。")
    w("")
    w("| 格 | 假訊號 合格 x／30 | 另列 | ≥ 5%？ | 30 次的年化中位之中位 | 回落中位之中位 | 真訊號（同 50 顆）年化中位 | 回落中位 | 標籤 | 真訊號年化在 30 次中的位置（≤ 它的次數） | 回落位置 |")
    w("|---|---:|---:|:--:|---:|---:|---:|---:|:--:|---:|---:|")
    for k in ("Cc", "Cd", "Ce", "Cf", "Cg", "Ch"):
        r = FK.loc[k]
        w(f"| {SHORT[k]} | **{int(r['x_Q'])}／{int(r['n'])}** | {int(r['x_R'])} | {'⚠ 是' if r['warn'] else '否'} | {p(r['fake_cagr_med'])} | {p(r['fake_mdd_med'])} | "
          f"{p(r['real50_cagr'])} | {p(r['real50_mdd'])} | {r['real50_label']} | {int(r['real_cagr_rank（≤它的次數）'])}／30 | {int(r['real_mdd_rank（≤它的次數）'])}／30 |")
    fi = S["假訊號序列"]
    w("")
    w("序列檢查：" + "；".join(f"MA{n} 線下 {v['線下天數（[w0−1,w1]）']} 天、打亂後線下天數都相同 {v['打亂後都相同']}、窗外不動 {v['窗外不動']}、與原序列不同 {v['與原序列不同的次數']}／30"
                          for n, v in fi.items()) + "。")
    w("")

    # ── 八、§四④
    w("## 八、§四④ 三條均線的狀態描述（主窗 [w0, w1]）")
    w("")
    w("| 均線 | 跌破段數 | 假警報（≤ 5 日翻回） | 段長 p25／p50／p75／p90 | 線下天數 | 線下占比 |")
    w("|---|---:|---:|---|---:|---:|")
    for n in ("60", "20", "10"):
        v = S["§四④"][n]
        w(f"| MA{n} | {v['跌破段數']} | {v['假警報（≤5日翻回）']}（{v['假警報（≤5日翻回）'] / v['跌破段數'] * 100:.0f}%） | {'／'.join(g(x, 0) for x in v['段長 p25/p50/p75/p90'])} | {v['線下天數']} | {v['線下占比'] * 100:.1f}% |")
    w("")
    w("**0050 自己的 ≥ 20% 回落事件**（主窗；分型照 seq5 §7-1）與各均線第一個跌破（訊號）：")
    w("")
    w("| 事件（高點→谷底） | 跌幅 | 分型 | MA60 訊號／落後／已跌／已跌占全段 | MA20 | MA10 |")
    w("|---|---:|---|---|---|---|")
    ev0 = S["§四④"]["60"]["0050事件"]
    for i, e in enumerate(ev0):
        cells = []
        for n in ("60", "20", "10"):
            x = S["§四④"][n]["0050事件"][i]
            cells.append(f"{x['訊號'] or '—'}／{x['落後'] if x['落後'] is not None else '—'} 日／{p(x['已跌'])}／{(x['已跌占全段'] * 100) if x['已跌占全段'] is not None else float('nan'):.0f}%")
        w(f"| {e['高點']} → {e['谷底']} | {p(e['跌幅'], 1)} | {e['分型']} | " + " | ".join(cells) + " |")
    w("")
    try:
        from . import rerun17 as RR
        from . import researchp9 as P9
        RR.use_snapshot()
        from . import data as D
        cal_ = D.load_calendar(); w0_, w1_ = RR.win_bounds(cal_); b_ = RR.load_bench(cal_); bq_ = b_ / b_[w0_]
        lg = []
        for e in P9.dd_events(bq_, w0_, w1_ + 1):
            k1, a2, _ = P9.dd_type(bq_, e["peak"], e["trough"]); k2, c2, _ = P9.dd_type(bq_, e["peak"], e["trough"], scale="log")
            lg.append(f"{cal_[e['peak']].date()}：本件 simple {k1}（最差2日占 {a2 * 100:.1f}%）／log {k2}（{c2 * 100:.1f}%）")
        w("⚠ 分型口徑（讀8）：本件用 researchp9.dd_type 預設的 simple 報酬（＝ P9B_REPORT 那一種）；策略線 seq5 §7-2 的 ddtype.py 是 log 報酬，"
          "兩者在邊界附近會給不同型：" + "；".join(lg) + "。⛔ 本件照 simple 報、不換口徑。")
        w("")
    except Exception as ex:                      # noqa: BLE001
        w(f"（log 口徑對照沒算出：{ex!r}）"); w("")
    w("**回落分兩型**（每一臂 200 顆種子在主窗內的全部 ≥ 20% 事件，按分型計數〔simple 口徑〕；事件數報每顆種子的中位、各型報 200 顆合計）：")
    w("")
    w("| 格 | 事件數 中位 | 單日暴跌型 | 延續下跌型 | 混合型 |")
    w("|---|---:|---:|---:|---:|")
    for k in ["base"] + ORDER + ["Cb_ref"]:
        gA = A[A["arm"] == k]
        w(f"| {SHORT[k]} | {gA['dd_n'].median():g} | 共 {int(gA['dd_單日暴跌型'].sum())} | 共 {int(gA['dd_延續下跌型'].sum())} | 共 {int(gA['dd_混合型'].sum())} |")
    w("")

    # ── 九、§四⑤ 事件逐筆
    w(f"## 九、§四⑤ 大回落事件逐筆（基準臂中位種子 seed＝{S['§四⑤']['中位種子']}；⭐ 在這 {len(EV)} 次事件上）")
    w("")
    w("| 事件（高點→谷底→回升） | 日數 | 基準回落 | 分型 | 最差2日占比 | MA60 首跌破／落後／0050已跌／組合已跌 | MA20 | MA10 |")
    w("|---|---:|---:|---|---:|---|---|---|")
    for _, e in EV.iterrows():
        cells = []
        for n in (60, 20, 10):
            fb = e[f"MA{n}_首跌破"]
            if isinstance(fb, str) and fb:
                cells.append(f"{fb}／{e[f'MA{n}_落後']:.0f} 日／{p(e[f'MA{n}_0050已跌'])}／{p(e[f'MA{n}_組合已跌'])}")
            else:
                cells.append("—")
        w(f"| {e['高點']} → {e['谷底']} → {e['回升']}{'' if e['回升了'] else '（未回升）'} | {e['日數']} | {p(e['基準回落'], 1)} | {e['分型']} | {e['最差2日占比'] * 100:.1f}% | " + " | ".join(cells) + " |")
    w("")
    w("**各格在同一顆種子、同一個事件窗內救到幾 pp**（窗內回落 格 − 基準；正＝救到）：")
    w("")
    w("| 事件高點 | " + " | ".join(SHORT[k] for k in ORDER + ["Cb_ref"]) + " |")
    w("|---|" + "---:|" * (len(ORDER) + 1))
    for _, e in EV.iterrows():
        w(f"| {e['高點']} | " + " | ".join(f"{e[f'救到pp_{k}']:+.2f}" for k in ORDER + ["Cb_ref"]) + " |")
    w("")
    w(f"⛔ 依〈九十八〉：有效樣本數＝事件數＝{len(EV)} ⇒ 一律寫「在這 {len(EV)} 次事件上」，⛔ 不寫「測得出／測不出」。")
    w("")

    # ── 十、§四⑥
    yrs = [y for y, *_ in S["years"]]
    w("## 十、§四⑥ 逐年報酬（每顆種子逐年、報中位）＋去掉最好一年＋三段區間")
    w("")
    w("| 格 | " + " | ".join(str(y) for y in yrs) + " | 去掉最好一年（年化） | 2020-03 | 2022 | 2025-04 |")
    w("|---|" + "---:|" * (len(yrs) + 4))
    y50 = b50["逐年"]
    best = max(y50, key=y50.get)
    w(f"| 0050 | " + " | ".join(p(y50[str(y)], 1) for y in yrs) + f" | （最好 {best}） | {p(b50['區間']['2020-03'], 1)} | {p(b50['區間']['2022'], 1)} | {p(b50['區間']['2025-04'], 1)} |")
    for k in ["base"] + ORDER + ["Cb_ref"]:
        r = TB.loc[k]
        w(f"| {SHORT[k]} | " + " | ".join(p(r[f'y{y}'], 1) for y in yrs) + f" | {p(r['drop_best_geo'])} | {p(r['p2020-03'], 1)} | {p(r['p2022'], 1)} | {p(r['p2025-04'], 1)} |")
    w("")
    w(f"年界：{'、'.join(f'{y}（{a}～{b}）' for y, _, _, a, b in S['years'])}。2017 從 2017-03-02 起、2026 到 2026-08-24。"
      "「去掉最好一年」＝ 每顆種子去掉自己最好的那一年、其餘年連乘，以其餘交易日數 ÷ 245 年化（讀7）。")
    w("")

    # ── 十一、§2-E
    w("## 十一、§四③ seq5 §2-E ①～⑤")
    w("")
    w("① 年化＋回落（含 p10～p90）見 §三；交易筆數見 §六；槽位使用率、平均持有天數如下。")
    w("")
    w("| 格 | 槽位使用率 中位 | 新部位筆數 中位 | 加減碼動作筆數 中位 |")
    w("|---|---:|---:|---:|")
    extra_cols = {"A2": ["x_tr_buys"], "A3": ["x_tr_buys"], "Ba": ["x_add_n"], "Bb": ["x_add_n"], "Bc": ["x_add_n"], "Ca": ["x_trim_n"],
                  "Cf": ["x_rt_sell_n", "x_rt_refill_n"], "Cg": ["x_rt_sell_n", "x_rt_refill_n"], "Ch": ["x_rt_sell_n", "x_rt_refill_n"]}
    for k in ["base"] + ORDER + ["Cb_ref"]:
        r = TB.loc[k]
        ex = sum(r[f"{c}_med"] for c in extra_cols.get(k, [])) if k in extra_cols else 0
        w(f"| {SHORT[k]} | {r['slot'] * 100:.1f}% | {r['trades']:.0f} | {ex:g} |")
    w("")
    w(f"② 全窗＋A 窗（2017-03-02～2020-12-31）＋B 窗（2021-01-04～2026-08-24）；只描述、⛔ 不判（讀10）。0050：A 窗 {p(b50['A窗']['cagr'])}／{p(b50['A窗']['mdd'], 1)}、B 窗 {p(b50['B窗']['cagr'])}／{p(b50['B窗']['mdd'], 1)}。")
    w("")
    w("| 格 | A 窗 年化 | A 窗 回落 | A 窗 位置 | B 窗 年化 | B 窗 回落 | B 窗 位置 |")
    w("|---|---:|---:|:--:|---:|---:|:--:|")

    def pos(c, m, bc, bm):
        k1 = c > bc; k2 = c / abs(m) >= bc / abs(bm)
        return "合格形" if (k1 and k2) else ("另列形" if k1 else "不合格形")
    for k in ["base"] + ORDER + ["Cb_ref"]:
        r = TB.loc[k]
        w(f"| {SHORT[k]} | {p(r['ca'])} | {p(r['ma'], 1)} | {pos(r['ca'], r['ma'], b50['A窗']['cagr'], b50['A窗']['mdd'])} | "
          f"{p(r['cb'])} | {p(r['mb'], 1)} | {pos(r['cb'], r['mb'], b50['B窗']['cagr'], b50['B窗']['mdd'])} |")
    w("")
    w("③ 單一部位最大佔比：見 §六最後一欄（**描述**，登錄 seq9 §四③ 已改為不再比 20%）。④ 想加碼但現金不足：見 §六、6-1。")
    w("")
    ov = S["§2-E⑤"]
    w(f"⑤ 狀態月（每月進場日前一天 0050 在均線下）與母體負報酬月的重疊率，⛔ 兩個方向都報（每月只有一個進場日：{ov['每月只有一個進場日']}）：")
    w("")
    w("| 均線 | 共同月 | 線下月 | 負報酬月 | 交集 | 精確率（交集÷線下月） | 涵蓋率（交集÷負報酬月） |")
    w("|---|---:|---:|---:|---:|---:|---:|")
    for n in (60, 20, 10):
        v = ov[f"MA{n}"]
        w(f"| MA{n} | {v['共同月']} | {v['線下月']} | {v['負報酬月']} | {v['交集']} | {v['精確率'] * 100:.1f}% | {v['涵蓋率'] * 100:.1f}% |")
    w("")

    # ── 十二、先驗對照
    w("## 十二、先驗對照（登錄 §五；先驗寫下就不改，本節只逐條對）")
    w("")
    rb = TB.loc["Cb_ref"]

    def dd(k):
        r = TB.loc[k]
        return f"年化差 {pp(r['d_cagr_med'])}、回落差 {pp(r['d_mdd_med'])}、標籤 {r['label']}"
    w("| 先驗 | 結果（配對差是逐種子中位） | 逐項對照 |")
    w("|---|---|---|")
    yn = lambda b: "對" if b else "不對"
    for k in ("A2", "A3"):
        r = TB.loc[k]
        w(f"| 2-A k＝{k[1]}：回落改善 1～3pp、年化降 0～2pp ⇒ 不合格或另列（約七成） | {dd(k)} | "
          f"回落改善 1～3pp：{yn(0.01 <= r['d_mdd_med'] <= 0.03)}；年化降 0～2pp：{yn(-0.02 <= r['d_cagr_med'] <= 0)}；標籤：{yn(r['label'] in ('不合格', '另列'))} |")
    bB = [TB.loc[k] for k in ("Ba", "Bb", "Bc")]
    w(f"| 2-B：年化小幅升、回落變深 ⇒ 多數另列或不合格；三格都不合格約五成 | " + "；".join(f"{SHORT[k]} {dd(k)}" for k in ("Ba", "Bb", "Bc"))
      + f" | 年化升：{sum(r['d_cagr_med'] > 0 for r in bB)}／3；回落變深：{sum(r['d_mdd_med'] < 0 for r in bB)}／3（回落差 ≥ 0，沒有變深）；"
        f"多數另列或不合格：{yn(sum(r['label'] in ('另列', '不合格') for r in bB) >= 2)}；三格都不合格：{'是' if all(r['label'] == '不合格' for r in bB) else '否（三格皆另列）' if all(r['label'] == '另列' for r in bB) else '否'} |")
    r = TB.loc["Ca"]
    w(f"| 2-C ⓐ：年化降、回落改善小 ⇒ 不合格（約七成） | {dd('Ca')} | 年化降：{yn(r['d_cagr_med'] < 0)}；回落改善 {pp(r['d_mdd_med'])}（「小」無數值門檻，不判）；標籤：{yn(r['label'] == '不合格')} |")
    r = TB.loc["Cc"]
    w(f"| 2-C ⓒ：年化比基準高 0～4pp、回落深 0～4pp ⇒ 另列（約五成） | {dd('Cc')}（回落差 {r['d_mdd_med'] * 100:+.6f}pp） | "
      f"年化高 0～4pp：{yn(0 <= r['d_cagr_med'] <= 0.04)}；回落深 0～4pp：{yn(-0.04 <= r['d_mdd_med'] <= 0)}（回落中位差近乎 0、沒有變深）；標籤另列：{yn(r['label'] == '另列')} |")
    for k in ("Cd", "Ce"):
        r = TB.loc[k]
        w(f"| {SHORT[k]}：回落改善不超過 ⓑ、年化代價不小於 ⓑ ⇒ 不合格（兩格約六成） | {dd(k)}（ⓑ 參照：年化差 {pp(rb['d_cagr_med'])}、回落差 {pp(rb['d_mdd_med'])}） | "
          f"回落改善不超過 ⓑ：{yn(r['d_mdd_med'] <= rb['d_mdd_med'])}；年化代價不小於 ⓑ：{yn(r['d_cagr_med'] <= rb['d_cagr_med'])}；標籤不合格：{yn(r['label'] == '不合格')} |")
    r = TB.loc["Cf"]
    w(f"| 2-C ⓕ：回落改善大於 ⓑ、年化代價也大於 ⓑ ⇒ 不合格或另列（約六成） | {dd('Cf')} | "
      f"回落改善大於 ⓑ：{yn(r['d_mdd_med'] > rb['d_mdd_med'])}；年化代價大於 ⓑ：{yn(r['d_cagr_med'] < rb['d_cagr_med'])}；標籤：{yn(r['label'] in ('不合格', '另列'))} |")
    w(f"| 2-C ⓖ／ⓗ：來回磨損 ⇒ 兩格都不合格（約七成） | {dd('Cg')}；{dd('Ch')} | 兩格都不合格：{yn(all(TB.loc[k, 'label'] == '不合格' for k in ('Cg', 'Ch')))}（每年多付成本見 §6-2） |")
    anyq = any(TB.loc[k, "label"] == "合格" for k in ("Cf", "Cg", "Ch"))
    w(f"| ⓕⓖⓗ 至少一格合格：約兩成 | {'有' if anyq else '沒有'}一格合格 | {'（押的兩成那一邊）' if anyq else '（押的八成那一邊）'} |")
    cp = CT[(CT["version"] == "paired") & (CT["cell"].isin(["Cc", "Cd", "Ce"]))]
    tied = [r["cell"] for _, r in cp.iterrows() if (r["cagr"] >= r["cell_cagr"] and r["ratio"] >= r["cell_ratio"])]
    w(f"| 同平均部位對照：ⓒⓓⓔ 至少一格被對照追平（約五成） | 主版類別 " + "、".join(f"{SHORT[r['cell']]} {r['class']}" for _, r in cp.iterrows())
      + f"；對照兩項都不輸格（＝追平）的格：{('、'.join(SHORT[c] for c in tied)) or '無'} | {'是' if tied else '否'} |")
    rc = TB.loc["Cc"]
    w(f"| 新的、可否證：「跌破 MA60 加碼比減碼好」 | ⓒ（1.5 slot）年化 {p(rc['cagr'])}、比值 {f3(rc['ratio'])} vs ⓑ 參照（0.5 slot）年化 {p(rb['cagr'])}、比值 {f3(rb['ratio'])} | "
      f"年化 {'ⓒ 較高' if rc['cagr'] > rb['cagr'] else 'ⓑ 較高'}、比值 {'ⓒ 較高' if rc['ratio'] > rb['ratio'] else 'ⓑ 較高'}（描述） |")
    w(f"| ⓑ 在主窗（本線依浮動窗推「不合格」） | ⓑ 參照臂主窗：年化 {p(rb['cagr'])}、回落 {p(rb['mdd'])}、比值 {f3(rb['ratio'])}（⛔ 參照、不判） | — |")
    w("")
    w("「2025-04 單日暴跌型：三條均線都來不及（約九成）」：見 §九事件表與 §十「2025-04」欄（只描述）。")
    w("")

    # ── 十三、讀法
    w("## 十三、兩種讀法處（本件選一種、寫在 researchP9run.py docstring；⛔ 沒改規則）")
    w("")
    for s in [
        "讀1 2-B ⓑ 旗標由 panel_ext（補 2026-04～08 量測日）產；訊號仍由 resultsAFC 面板建（回測 1919：panel_ext 只產 ⓑ 旗標）",
        "讀2 m̄＝實際成交倍數（現金不足沒加的不算；ⓒ 現金不足只買 1 slot 算 1）｜另一讀法：名目倍數（觸發即算）",
        "讀3 ē＝[w0, w1] 持股市值÷總資產日平均；ē 對照成本＝引擎慣例（只在賣出付一次來回）｜另一讀法：P17 兩向都付（已另列為描述版）",
        "讀4 中位版＝200 顆 m̄／ē 的中位；合計版＝m̄ 按新部位數加權、ē 取 200 顆平均（兩版都只描述；主版逐種子配對是裁定 seq167 定的）",
        "讀5 假訊號臂：打亂範圍 [w0−1, w1]（窗外不動）、線下段與線上段各自打亂後照原交替接回；rng＝default_rng(20260925＋j)；同 j 的 MA60 序列 ⓒ、ⓕ 共用｜另一讀法：整條序列打亂、或只打亂線下段位置",
        "讀6 同現金比例×0050 用 2,313 日／245 年化（與 0050 錨同一支 window_stats）｜researchAFC 用 (w1−w0)/245",
        "讀7 去掉最好一年＝其餘年連乘、以其餘交易日數 ÷ 245 年化｜researchAFC 把首尾殘年當整年",
        "讀8 假警報＝線下段長 ≤ 5 日；事件訊號＝事件 [高點, 回升] 內第一個跌破段；組合事件的「0050 已跌」沿用 researchp9（事件起點前 60 根內 0050 最高）；回落分型用 researchp9.dd_type 的 simple 報酬（P9B_REPORT 同）｜另一讀法：策略線 ddtype.py 的 log 報酬（0050 兩個事件會換型，見 §八）",
        "讀9 ⓕⓖⓗ 每年多付成本＝賣半當下成本＋補回金額×COST（後者引擎在出場時才扣）",
        "讀10 A／B 窗切點＝research13.SPLIT（2021-01）；只描述",
        "讀11 平均持有天數依構造 120 根；讀12 現金不足倍數＝現金不足中位÷加成中位",
        "引擎既有讀法（回測 1738 §四、ENGINE_REPORT §六，裁定 seq162 收下）：分批每份＝進場日 slot÷k、分批現金不足有多少買多少、加碼 0.5 slot 取加碼當天 slot、+15%／−10% 含等號、ⓒ 只在第 40 根判一次且嚴格為正、ⓒ 1.5 slot 現金不足只買 1 slot、ⓕⓖⓗ 狀態式（線下每天把整份賣成半份）、部分補回之後不再補足、同日先賣後買再開新部位、漲跌停停牌延到下一個可成交開盤（本件 tradable 關，只有開盤非有限時才延）",
    ]:
        w(f"- {s}")
    w("")

    # ── 十四、查核
    w("## 十四、硬性查核")
    w("")
    det = S["查核_決定性"]
    w(f"- **決定性**：基準臂 200 顆重跑第二次 ⇒ equity sha256 {'✅ 全同' if det['equity_sha'] else '⛔'}、年化／回落／波動 repr {'✅ 全同' if (det['cagr'] and det['mdd'] and det['vol']) else '⛔'}。")
    if CK is not None:
        w(f"- **獨立重算**（`researchP9run_check.py`，⛔ 不 import 主程式、純 Python statistics.median）：每格年化中位、回落中位、比值、波動中位 repr 與 cells.csv 比、標籤、配對差中位、種子合格比例、"
          f"對照臂各版本與甲'／乙'／丙'、假訊號 x／30 ⇒ **{'✅ 全部相同' if CK['通過'] else '⛔ 有不符：' + str(CK['mismatch'][:5])}**。")
    else:
        w("- 獨立重算：⏳ 尚未跑")
    w(f"- 開跑前閘三道：見 §一。")
    w("")

    # ── 十五、限制與 N
    w("## 十五、限制、污染與 N 帳（登錄 §七、§八逐條）")
    w("")
    for s in [
        "① ⓑⓓⓔ 的「減碼」只作用在新部位；ⓕⓖⓗ 賣手上持股一半；0050／正二本身的加減碼 ⇒ 大盤驅動因素件",
        "② MA 天數 60／20／10 不掃；若任一格合格 ⇒ 敏感度另開一件",
        f"③ 大回落事件只有 {len(EV)} 次（基準臂中位種子）⇒ 有效樣本是事件數",
        "④ ⚠ 污染：ⓒ～ⓗ 都是看過 P9ⓑ 結果後才提；另外 6 格起草 seq 時也已看過 ⓑ ⇒ 12 格主窗結果【一律只當候選】；合格或另列的格 ⇒ PREREGV 同一批早年段（2008-01～2014-12）驗收",
        "⑤ 成本 0.585%；加減碼增加交易次數（筆數見 §六、§十一）；滑價未計",
        "⑥ 倖存者偏誤仍在；本件 tradable／delist 關（與 researchp9 基準臂、P9 引擎閘 2 同；AFC W1 開著，差見 §一）",
        "⑦ 2-D 組合 ⛔ 沒跑（裁定 seq162 §四③：疊加規則沒訂）",
        "N 帳：N_組合 **+12**（登錄 §八）；基準臂、ⓑ 參照臂、m̄／ē 對照臂、同現金比例×0050、假訊號臂 ⛔ 不計",
    ]:
        w(f"- {s}")
    w("")
    w("## 十六、檔案")
    w("")
    w("`backtest/resultsP9run/`：seeds_arms.csv（14 臂 × 200 顆逐種子）、seeds_controls.csv（m̄／ē 對照逐種子）、seeds_fake.csv（假訊號 6 格 × 30 × 50）、"
      "cells.csv、controls.csv、fake.csv、events.csv、gate3_rerun17_seeds.csv、summary.json、check.json、run.log、P9_REPORT.md")
    w("")
    open(os.path.join(OUT, "P9_REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(f"寫入 {os.path.join(OUT, 'P9_REPORT.md')}（{len(L)} 行）")


if __name__ == "__main__":
    sys.exit(main())
