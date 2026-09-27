# -*- coding: utf-8 -*-
"""W1、F 確認段補跑 REPORT.md 產生器（只讀 resultsAFCext/；⛔ 不重算）。"""
from __future__ import annotations
import json, os
import numpy as np

OUT = os.path.expanduser("~/tw-p17/backtest/resultsAFCext")


def p(x, d=2):
    return "—" if x is None or not np.isfinite(float(x)) else f"{float(x) * 100:+.{d}f}%"


def main():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    CK = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else None
    V0, V1, V2, V3 = "V0 閘（截到 2026-03-02、stop_force 關）", "V1 補面板", "V2 補面板＋stop_force", "V3 補面板＋尾端截斷補回＋stop_force"
    z = S["0050"]; r0 = z["主窗"][0] / abs(z["主窗"][1])
    W, F = "W1（1,000 顆中位）", "F（200 顆中位）"
    o = S["原件"]
    labs = {k: (S[V3][k]["主窗判準"], S[V3][k]["確認段判準"]) for k in (W, F)}
    L = ["# W1、F 確認段補跑（面板改 panel_ext 到 2026-08；裁定 seq257 §三 順 3）", ""]
    L.append(f"**結論：補齊 2026-04～08 的面板並補回資料尾截斷的訊號後，W1 主窗【{labs[W][0]}】、F 主窗【{labs[F][0]}】（停止交易強制出場：開）；確認段 2022～2026 W1【{labs[W][1]}】、F【{labs[F][1]}】。"
             f"只換面板（V1、V2）數字與原件完全相同：H120 出場日要在資料尾 2026-09-24 以前，2026-05～08 進場的訊號被原函式整筆丟掉。**")
    L.append("")
    L.append("| 版 | W1 主窗 年化／回落（比值） | F 主窗 年化／回落（比值） | W1 判準 | F 判準 |")
    L.append("|---|---|---|---|---|")

    def lab(c, m):
        return "合格" if (c > z["主窗"][0] and c / abs(m) >= r0) else ("另列" if c > z["主窗"][0] else "不合格")
    L.append(f"| 原件（resultsAFC 面板到 2026-03-02） | {p(o[W][0])}／{p(o[W][1])}（{o[W][0] / abs(o[W][1]):.3f}） | {p(o[F][0])}／{p(o[F][1])}（{o[F][0] / abs(o[F][1]):.3f}） | {lab(*o[W])} | {lab(*o[F])} |")
    for vn, nm in ((V1, "補面板（stop_force 關）"), (V2, "補面板＋停止交易強制出場：開"), (V3, "補面板＋尾端截斷補回＋停止交易強制出場：開")):
        a, b = S[vn][W], S[vn][F]
        L.append(f"| {nm} | {p(a['主窗'][0])}／{p(a['主窗'][1])}（{a['主窗'][2]:.3f}） | {p(b['主窗'][0])}／{p(b['主窗'][1])}（{b['主窗'][2]:.3f}） | {a['主窗判準']} | {b['主窗判準']} |")
    L.append(f"| 0050 主窗 | {p(z['主窗'][0])}／{p(z['主窗'][1])}（{r0:.3f}） | 同左 | — | — |")
    L.append("")
    L.append("```")
    L.append("⚠ 標註")
    L.append("  ・停止交易強制出場：開（V2；research11.simulate_mtm stop_force，commit 51a3dc35f3）；V1 為關，用來分開「面板」與「強制出場」各自的影響")
    L.append("  ・除面板外與原件 researchAFC.py（4762a3809f）一字不動：門檻B、H120、N8、成本 0.585%、tradable＋delist、W1 1,000 顆、F 200 顆、F 假訊號臂 30×200")
    L.append("  ・K6 新判準：年化 ＞ 0050 同段 且 年化÷|MDD| ≥ 0050 ⇒ 合格；只過第一條 ⇒ 另列")
    L.append("  ・強制出場 0 筆：原件已開 tradable＋delist（下市以最後成交價了結）⇒ stop_force 在本件沒有額外作用")
    L.append("  ・⚠ 本線讀法（V3）：資料尾截斷補回照 researchYear1M T1（PREREGV 已用）；主窗到 2026-08-24 為止，補回列窗內照收盤計值、不賣不扣成本")
    L.append("  ・⚠ V3 的 W1 假訊號池沒有補回尾端截斷（2026-05～08 進場日假訊號候選較少）⇒ 那幾個月假訊號持股偏少；W1 p＝0 的方向不受影響")
    L.append("  ・F 主窗合格是邊緣（比值 0.715 對 0050 0.707）；確認段兩者都不合格（比值 0.60～0.61 對 0.868）")
    L.append("```")
    L.append("")
    L.append("## 一、三版細項")
    L.append("")
    L.append("| 版 | 訊號（筆／檔／月、最後進場） | 臂 | 主窗 年化／回落／比值 | 主窗判準 | 確認段 年化／回落／比值 | 確認段判準 | 強制出場（每顆） |")
    L.append("|---|---|---|---|---|---|---|---|")
    for vn in (V0, V1, V2, V3):
        v = S[vn]
        for k in (W, F):
            a = v[k]
            L.append(f"| {vn} | {v['S1筆']:,}／{v['S1檔']}／{v['S1月']}、{v['S1最後進場日']} | {k} | {p(a['主窗'][0])}／{p(a['主窗'][1])}／{a['主窗'][2]:.3f} | {a['主窗判準']} | "
                     f"{p(a['確認段'][0])}／{p(a['確認段'][1])}／{a['確認段'][2]:.3f} | {a['確認段判準']} | {a['強制出場筆_每顆']:.2f} |")
    L.append(f"\n0050：主窗 {p(z['主窗'][0])}／{p(z['主窗'][1])}；確認段 {p(z['確認段'][0])}／{p(z['確認段'][1])}（比值 {z['確認段'][0] / abs(z['確認段'][1]):.3f}）。")
    L.append("")
    L.append("## 二、差從哪來")
    L.append("")
    for k in (W, F):
        L.append(f"- {k}：原件 → 補面板 年化 {(S[V1][k]['主窗'][0] - o[k][0]) * 100:+.2f} 點；＋強制出場 {(S[V2][k]['主窗'][0] - S[V1][k]['主窗'][0]) * 100:+.2f} 點；"
                 f"＋尾端截斷補回 {(S[V3][k]['主窗'][0] - S[V2][k]['主窗'][0]) * 100:+.2f} 點（回落 {(S[V3][k]['主窗'][1] - S[V2][k]['主窗'][1]) * 100:+.2f} 點）")
    t1 = S.get("T1 尾端截斷補回", {})
    L.append(f"- 尾端截斷補回（⚠ 本線讀法，同 researchYear1M T1、PREREGV 已用）：原函式 {t1.get('原函式列數')} 列、補回 {t1.get('截斷補回')} 列（進場 {t1.get('補回進場日')}）；"
             "補回列的出場設在資料尾之後的墊檔日、窗內照收盤計值、⛔ 不賣不扣成本（窗到 2026-08-24 為止）")
    L.append("")
    L.append("## 三、假訊號（V3）")
    L.append("")
    fk = S[V3]["F 假訊號臂（30 次 × 200 顆）"]; wk = S[V3]["W1 假訊號臂（同進場日同筆數、閘門池隨機；200 次）"]
    L.append(f"- F（原件同一臂：每進場日隨機剔同數量，30 次 × 200 顆）：p（假訊號中位年化 ≥ F）＝ {fk['p（假訊號中位年化 ≥ F）']:.3f}、確認段 p ＝ {fk['確認段 p']:.3f}；"
             f"假訊號中位的中位 {p(fk['假訊號中位的中位'])}；30 次中合格 {fk['合格次數']} 次")
    L.append(f"- W1（⚠ 本線讀法：同進場日同筆數、從過閘門股隨機抽；200 次）：p ＝ {wk['p（假訊號年化 ≥ W1 中位）']:.3f}、確認段 p ＝ {wk['確認段 p']:.3f}；"
             f"假訊號年化中位 {p(wk['假訊號年化中位'])}、回落中位 {p(wk['假訊號回落中位'])}；假訊號合格比例 {wk['假訊號合格比例'] * 100:.1f}%")
    L.append("")
    L.append("## 四、閘")
    L.append("")
    g = S["閘 V0＝原件"]
    L.append(f"- 0050 錨 {S['0050錨']}；V0（panel_ext 截到 2026-03-02、stop_force 關）對原件 w1_1000.csv／f_and_fake.csv：W1 逐位元 {g['W1 1,000 顆逐位元']}、F 逐位元 {g['F 200 顆逐位元']}；"
             f"不逐位元 {g['不逐位元的顆數（W1＋F 共 1,200）']}／1,200、最大差 {g['最大差']:.1e}、中位數最大差 {g.get('中位數最大差', float('nan')):.1e}")
    L.append(f"- V0 ＝ 同一環境改用原件面板 resultsAFC/panel.csv.gz 重跑（逐位元）：{g['V0 ＝ 同環境用原件面板重跑（逐位元）']}")
    L.append(f"- ⚠ 逐位元做不到的原因：{g['說明']}")
    if CK:
        L.append(f"- 獨立查核 `researchAFCext_check.py`（⛔ 不 import 主程式與原件）：{'✅ 全過' if CK['全部過'] else '❌'}")
        for k, v in CK.items():
            if isinstance(v, dict):
                L.append(f"  - {k}：{'✅' if v['過'] is True else '❌'} " + "；".join(f"{a}={b}" for a, b in v.items() if a != "過"))
    L.append("")
    L.append("## 五、檔案")
    L.append("")
    L.append("`backtest/researchAFCext.py`、`researchAFCext_check.py`、`researchAFCext_report.py`；resultsAFCext/：summary.json、seeds.csv.gz（三版逐顆）、sig_ext.csv.gz、check.json、run.log、check.log")
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L[:14]))


if __name__ == "__main__":
    main()
