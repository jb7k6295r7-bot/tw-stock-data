# -*- coding: utf-8 -*-
"""researchP9ext 報告（只讀 resultsP9ext/ 的檔）。  cd ~/tw-p17 && ~/tw-p16/.venv/bin/python -m backtest.researchP9ext_report"""
from __future__ import annotations
import json, os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsP9ext")


def p(x, d=2):
    return f"{x * 100:+.{d}f}%"


def main():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    FT = pd.read_csv(os.path.join(OUT, "flip_table.csv"))
    FAM = {"base": "", "A2": "2-A ", "A3": "2-A ", "Ba": "2-B ", "Bb": "2-B ", "Bc": "2-B ", "Ca": "2-C ", "Cc": "2-C ", "Cd": "2-C ", "Ce": "2-C ",
           "Cf": "2-C ", "Cg": "2-C ", "Ch": "2-C ", "Cb_ref": "參照 ", "By": ""}
    FT["格"] = [FAM.get(k, "") + g for k, g in zip(FT["arm"], FT["格"])]
    CK = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else None
    V = {k[:2]: k for k in S if k[:2] in ("V0", "V1", "V2", "V3") and isinstance(S[k], dict) and "格" in S[k]}
    c50, m50 = S["0050"]["主窗"]
    J = FT[FT["判定"]]
    P9 = J[J["arm"] != "By"]
    fl = P9[P9["翻"] != "不翻"]
    cnt = lambda df, col: {l: int((df[col] == l).sum()) for l in ("合格", "另列", "不合格")}
    c0, c3 = cnt(P9, "原件_標籤"), cnt(P9, "V3_標籤")
    by = FT[FT["arm"] == "By"].iloc[0]
    L = ["# P9run 12 格 K5 截斷補跑（裁定 seq260 §二；補法 ＝ AFCext V3：panel_ext＋尾端截斷補回＋停止交易強制出場）", ""]
    fl_txt = "、".join(f"{r['格'].split('⇒')[0].strip()}（{r['arm']}）{r['翻']}" for _, r in fl.iterrows()) or "沒有"
    fk3 = S[V["V3"]]["假訊號臂"]
    warn = [k for k in fk3 if fk3[k]["x_Q"] / fk3[k]["n"] >= 0.05]
    wflip = [k for k in warn if k in set(fl["arm"])]
    base = FT[FT["arm"] == "base"].iloc[0]
    warn_txt = ("⚠ " if wflip else "")
    L.append(warn_txt + f"**結論：補回尾端截斷後，P9run 12 格由 合格 {c0['合格']}／另列 {c0['另列']}／不合格 {c0['不合格']} 變成 合格 {c3['合格']}／另列 {c3['另列']}／不合格 {c3['不合格']}；"
             f"翻的有 {len(fl)} 格：{fl_txt}；年化差 {P9['差_年化點'].min():+.2f}～{P9['差_年化點'].max():+.2f} 點、回落差 {P9['差_回落點'].min():+.2f}～{P9['差_回落點'].max():+.2f} 點。"
             f"攤平停利 B 乙一 By：{by['原件_標籤']} → {by['V3_標籤']}（年化 {by['差_年化點']:+.2f} 點）。"
             f"翻的主因是共同的上移：不判的基準臂同樣 {base['差_年化點']:+.2f} 點（{p(base['原件_年化'])} → {p(base['V3_年化'])}，比值 {base['V3_比值']:.4f}，仍另列）。"
             + (f"⚠ 假訊號臂（均線狀態打亂）在 V3 也合格：" + "、".join(f"{FAM.get(k, '')}{k} {fk3[k]['x_Q']}／{fk3[k]['n']}" for k in warn)
                + "（≥ 5%）⇒ 其中翻合格的 " + "、".join(wflip) + " 跟隨機打亂的均線狀態分不開。" if warn else "")
             + "**")
    L.append("")
    L.append(f"0050 主窗 {p(c50)}／{p(m50)}（比值 {c50 / abs(m50):.4f}）；判準 seq141（年化 ＞ 0050 且 比值 ≥ 0050 ⇒ 合格；只過前者 ⇒ 另列）；判定值 ＝ 200 顆中位")
    L.append("")
    L.append("| 格 | 原件 年化／回落（比值） | 原件 | V3 年化／回落（比值） | V3 | 差 年化／回落（點） | 翻？ | 事前估計 |")
    L.append("|---|---|---|---|---|---|---|---|")
    for _, r in J.iterrows():
        L.append(f"| {r['格']} | {p(r['原件_年化'])}／{p(r['原件_回落'])}（{r['原件_比值']:.4f}） | {r['原件_標籤']} | {p(r['V3_年化'])}／{p(r['V3_回落'])}（{r['V3_比值']:.4f}） | "
                 f"{r['V3_標籤']} | {r['差_年化點']:+.2f}／{r['差_回落點']:+.2f} | {'**' + r['翻'] + '**' if r['翻'] != '不翻' else '不翻'} | {r['事前估計']} |")
    L.append("")
    L.append("```")
    L.append("⚠ 標註")
    L.append("  ・停止交易強制出場：開（V2、V3）")
    L.append("  ・尾端截斷補回（T1 讀法，researchYear1M.sig12／pad_px）：出場超過資料尾的訊號 ⇒ 墊檔日出場、報酬照最後收盤（2026-09-24）；墊檔日 opens NaN")
    L.append("  ・其餘照原件：tradable／delist 關（⚠ 與 AFC W1 不同）、H120、N8、種子 99000＋r、COST 0.585%、ⓑ 旗標 panel_ext（V3 墊 False）")
    L.append("  ・m̄／ē 對照臂、同現金比例×0050 沒有重跑（本件只問標籤翻不翻）")
    L.append("```")
    L.append("")
    L.append("## 一、分版（補面板／停止交易／尾端補回 各自的貢獻）")
    L.append("")
    L.append("| 格 | 原件 | V1 補面板 | V2 ＋stop_force | V3 ＋尾端補回 |")
    L.append("|---|---|---|---|---|")
    for _, r in FT.iterrows():
        L.append(f"| {r['格']}{'' if r['判定'] else '（⛔ 不判）'} | {p(r['原件_年化'])} {r['原件_標籤']} | {p(r['V1_年化'])} {r['V1_標籤']} | {p(r['V2_年化'])} {r['V2_標籤']} | "
                 f"{p(r['V3_年化'])} {r['V3_標籤']} |")
    L.append("")
    L.append("讀法：V1 ＝ V0 逐位元（14 臂＋By 共 3,000 顆 equity sha 全同）——補面板多出的 16 筆都在 2026-04-02 進場，"
             "而基準臂 200 顆在該日開盤的空槽全是 0（3 月 3 日那批已把 8 槽補滿，H120 固定出場、無停損）⇒ 一筆也買不到；"
             "V2 ＝ V1 逐位元：停止交易強制出場 0 筆（持有中的股沒有在主窗尾前停止交易）。⇒ 年化差全部來自 V3 的尾端截斷補回（294 筆，進場 2026-05-05～08-04）。")
    L.append("")
    L.append("訊號：" + "；".join(f"{k} {S[v]['訊號']['訊號筆']:,} 筆／{S[v]['訊號']['檔']} 檔、最後進場 {S[v]['訊號']['最後進場日']}、墊檔日出場 {S[v]['訊號']['墊檔日出場筆']}"
                             for k, v in sorted(V.items())))
    if "T1 尾端截斷補回" in S:
        L.append("")
        L.append(f"T1：{json.dumps(S['T1 尾端截斷補回'], ensure_ascii=False)}")
    L.append(f"；停止交易日（主窗尾前停止）{S['停止交易日（主窗尾前停止）']} 檔")
    L.append("")
    L.append("## 二、假訊號臂（ⓒ～ⓗ；線上／線下段打亂 30 次 × 50 顆，照原件）")
    L.append("")
    L.append("| 格 | V0（＝原件）假訊號合格 x／30 | 另列 | 真 50 顆年化名次（≤ 它的次數） | V3 假訊號合格 x／30 | 另列 | 真 50 顆年化名次 | V3 真 50 顆標籤 |")
    L.append("|---|---|---|---|---|---|---|---|")
    for k in S[V["V3"]]["假訊號臂"]:
        a, b = S[V["V0"]]["假訊號臂"][k], S[V["V3"]]["假訊號臂"][k]
        L.append(f"| {k} | {a['x_Q']}{' ⚠' if a['x_Q'] / a['n'] >= 0.05 else ''} | {a['x_R']} | {a['real_cagr_rank']} | {b['x_Q']}{' ⚠' if b['x_Q'] / b['n'] >= 0.05 else ''} | "
                 f"{b['x_R']} | {b['real_cagr_rank']} | {b['real50_label']} |")
    L.append("")
    L.append("（x／30 ≥ 5% ⇒ ⚠，同原件讀5）")
    L.append("")
    L.append("## 三、閘與查核")
    L.append("")
    g = S["閘"]["V0＝原件"]
    L.append("- ⚠ 開跑同一分鐘（01:05:40）另一條工作（researchT1fix）改了 backtest/rerun17.py（新增 T1 函式與 setup_and 的 t1 開關，預設關）；"
             "本件用到的 use_snapshot／load_prices／load_bench／win_bounds／win_metrics／bench_row 未動，V0 全部逐位元 ⇒ 不受影響")
    L.append(f"- 0050 錨逐位元 {S['閘']['0050錨']}；V0 訊號 ＝ 原件訊號（AFC 面板）{S['閘']['V0 訊號＝原件訊號（AFC 面板）']}")
    L.append(f"- V0 ＝ 原件：{json.dumps({k: v for k, v in g.items() if k != '說明'}, ensure_ascii=False, default=str)}")
    L.append(f"  - {g['說明']}")
    if CK:
        L.append(f"- 獨立查核 `researchP9ext_check.py`（⛔ 不 import 主程式、researchP9run、researchYear1M；訊號、墊檔、MA 狀態、停止交易日自寫）：{'✅ 全過' if CK['全部過'] else '❌'}")
        for k, v in CK.items():
            if isinstance(v, dict):
                L.append(f"  - {k}：{'✅' if v.get('過') is True else '❌'} " + "；".join(f"{a}={b}" for a, b in v.items() if a != "過"))
    L.append("")
    L.append("## 四、檔案")
    L.append("")
    L.append("`backtest/researchP9ext.py`、`researchP9ext_check.py`、`researchP9ext_report.py`；resultsP9ext/：summary.json、flip_table.csv、seeds_arms.csv.gz、"
             "seeds_fake.csv.gz、sig_v3.csv.gz、check.json、run.log")
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L[:22]))


if __name__ == "__main__":
    main()
