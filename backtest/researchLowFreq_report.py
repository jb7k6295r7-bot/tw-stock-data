# -*- coding: utf-8 -*-
"""PREREG低頻擇時 REPORT.md 產生器（只讀 resultsLowFreq/；⛔ 不重算）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchLowFreq_report.py
"""
from __future__ import annotations
import json, os
import numpy as np
import pandas as pd

HERE = os.path.expanduser("~/tw-p17/backtest")
OUT = os.path.join(HERE, "resultsLowFreq")
FAM = {"甲": "甲 月底看長均線", "乙": "乙 波動目標調正2比例", "丙": "丙 大盤停損"}


def p(x, d=2):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—"
    return "—" if not np.isfinite(x) else f"{x * 100:+.{d}f}%"


def pts(x):
    return f"{'多' if x >= 0 else '少'} {abs(x):.2f} 點"


def plain(fam, key):
    q = key.split("_")
    if fam == "甲":
        ma = {"M6": "6 個月線", "M10": "10 個月線", "M12": "12 個月線", "D200": "200 日線（月底看）"}[q[0]]
        return f"月底 0050 在{ma}上就抱正2，否則換{'0050' if q[1] == 'a' else '現金'}"
    if fam == "乙":
        return f"每月依正2 近 {q[1][1:]} 日波動調比例，目標波動 {q[0][1:]}%，其餘放{'0050' if q[2] == 'a' else '現金'}"
    return (f"抱{'0050' if q[0] == 'A' else '正2'}，0050 距一年高跌 {q[1][1:]}% 全換現金，"
            f"{'創 60 日新高' if q[2] == 'R1' else '站上 200 日線'}買回；{'每日' if q[3] == 'D' else '月底'}檢查")


def days(x):
    return f"{x} 個交易日" if isinstance(x, (int, float)) or str(x).isdigit() else str(x)


def main():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    C = pd.read_csv(os.path.join(OUT, "cells.csv"), encoding="utf-8")
    CK = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else None
    J, B, FK = S["判定"], S["基準"], S["假訊號"]
    reads = {f: J[f].get("讀法", J[f].get("判定")) for f in FAM}
    n_st = sum(v == "穩" for v in reads.values()); n_no = sum(v == "沒多賺" for v in reads.values())
    beat64 = [f for f in FAM if "確認" in J[f] and J[f]["確認"]["比六四v1（點）"] > 0 and J[f]["早年"]["比六四v1（點）"] > 0]
    ok70 = [f for f in FAM if "確認" in J[f] and not J[f]["2008型最慘（早年段最大回落、100萬在高點）"]["超過使用者上限 −70%"]]
    head = (f"三件裡 {n_st} 件兩段都比一直抱正2 多賺、{3 - n_st - n_no} 件只一段多賺、{n_no} 件兩段都沒多賺；"
            f"兩段都贏你現在的六四 v1 的：{'、'.join(beat64) if beat64 else '沒有'}；2008 型熊市沒超過 −70% 的：{'、'.join(ok70) if ok70 else '沒有'}")
    L = ["# PREREG低頻擇時 seq1（甲 長均線、乙 波動目標、丙 大盤停損；0050／00631L／現金）：本體＋獨立查核", ""]
    L.append(f"**結論：{head}。**（⚠ 事後追加、N ＋3；早年段是合成正2、非實際 ETF；六四 v1 的 00685L 用 00631L 代）")
    L.append("")
    L.append("| 件 | 挑中格 | 確認段 2022～2026 年化／回落 | 早年段 2005～2014（合成）年化／回落 | 對一直抱正2（確認／早年） | 對六四 v1（確認／早年） | 2008 型最慘（100 萬在高點） | 讀法 |")
    L.append("|---|---|---|---|---|---|---|---|")
    for f in FAM:
        j = J[f]
        if "確認" not in j:
            L.append(f"| {FAM[f]} | — | — | — | — | — | — | {j.get('判定')} |"); continue
        w = j["2008型最慘（早年段最大回落、100萬在高點）"]
        pf = FK.get(f, {}).get("確認", {}).get("p（隨機 ≥ 本格）")
        L.append(f"| {FAM[f]} | `{j['格']}` | {p(j['確認']['年化'])}／{p(j['確認']['回落'])} | {p(j['早年']['年化'])}／{p(j['早年']['回落'])} | "
                 f"{j['確認']['比一直抱正2（點）']:+.2f}／{j['早年']['比一直抱正2（點）']:+.2f} 點 | {j['確認']['比六四v1（點）']:+.2f}／{j['早年']['比六四v1（點）']:+.2f} 點 | "
                 f"剩 {w['剩（萬）']:.1f} 萬（{p(w['最大回落'])}{'，⚠ 超過 −70%' if w['超過使用者上限 −70%'] else '，未超過 −70%'}） | "
                 f"{j['讀法']}{'（隨機換也做得到）' if (pf is not None and pf >= 0.05) else ''} |")
    for nm, key in (("一直抱正2", "一直抱正2"), ("六四 v1（0050 60%＋00631L 40%）", "六四v1")):
        bc, be = B["確認"][key], B["早年"][key]
        L.append(f"| {nm} | — | {p(bc['年化'])}／{p(bc['回落'])} | {p(be['年化'])}／{p(be['回落'])} | — | — | 剩 {be['100萬在高點_谷底剩（萬）']:.1f} 萬（{p(be['最大回落'])}） | — |")
    L.append(f"| 0050 | — | {p(B['確認']['0050']['年化'])}／{p(B['確認']['0050']['回落'])} | {p(B['早年']['0050']['年化'])}／{p(B['早年']['0050']['回落'])} | — | — | — | — |")
    L.append("")
    L.append("結果句（登錄 §三＋裁定 seq254）：")
    L.append("")
    for f in FAM:
        j = J[f]
        if "確認" not in j:
            continue
        w = j["2008型最慘（早年段最大回落、100萬在高點）"]
        pf = FK.get(f, {}).get("確認", {}).get("p（隨機 ≥ 本格）")
        pre = "隨機換也做得到；" if (pf is not None and pf >= 0.05) else ""
        L.append(f"- {FAM[f]}：{pre}{plain(f, j['格'])}，2022～2026 年化 {p(j['確認']['年化'])}（一直抱正2 {p(B['確認']['一直抱正2']['年化'])}、0050 {p(B['確認']['0050']['年化'])}）；"
                 f"2005～2014（合成）年化 {p(j['早年']['年化'])}（一直抱合成正2 {p(B['早年']['一直抱正2']['年化'])}）；平均每年動手 {j['確認']['每年換手']:.1f} 次；"
                 f"2008 型最慘剩 {w['剩（萬）']:.1f} 萬{'（超過 −70%）' if w['超過使用者上限 −70%'] else '（未超過 −70%）'}。"
                 f"比一直抱正2 {pts(j['確認']['比一直抱正2（點）'])}（早年 {pts(j['早年']['比一直抱正2（點）'])}）；"
                 f"比你現在的六四 v1 {pts(j['確認']['比六四v1（點）'])}（早年 {pts(j['早年']['比六四v1（點）'])}）。讀法：{j['讀法']}；對 0050 判準：確認段 {j['確認']['對0050判準']}、早年段 {j['早年']['對0050判準']}")
    L.append("")
    L.append("```")
    L.append("⚠ 標註")
    L.append("  ・事後追加（看過國外結果才提；裁定 seq254）；N_組合 ＋3")
    L.append(f"  ・{S['六四v1']}")
    L.append(f"  ・早年段正2 ＝ {S['合成']}（0050 還原日報酬 ×2、每日重設、扣 1%／年）")
    L.append(f"  ・本線讀法 L1：早年段起點 {S['早年段起點 E0（讀法 L1）']}（登錄寫 2005-01；12 個月線與 250 日高要到 2005-01～02 才算得出來 ⇒ 下一個月初）")
    L.append("  ・本線讀法 L2：丙 M 版的「站上 200 日線（由下往上穿越）」＝ 上個月底在線下、本月底在線上（字面「月底當天剛好穿越」另報 §五）")
    L.append("  ・現金 0 息（登錄）；年 1% 另報 §五")
    L.append("```")
    L.append("")
    L.append("## 一、全部格（44 格；探索段挑、確認段與早年段判）")
    L.append("")
    L.append("| 件 | 格 | 探索 年化／回落 | 確認 年化／回落 | 早年 年化／回落 | 每年換手（確認） | 成本／年（確認） | 正2 平均比例（確認） | 退化 |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for (f, k), g in C.groupby(["件", "格"], sort=False):
        v = {r["段"]: r for _, r in g.iterrows()}
        mark = " ⭐" if S["挑格"].get(f) == k else ""
        L.append(f"| {f} | `{k}`{mark} | {p(v['探索']['年化'])}／{p(v['探索']['回落'])} | {p(v['確認']['年化'])}／{p(v['確認']['回落'])} | "
                 f"{p(v['早年']['年化'])}／{p(v['早年']['回落'])} | {v['確認']['每年換手']:.1f} | {p(v['確認']['成本／年'], 3)} | {v['確認']['正2平均比例']:.2f} | "
                 f"{v['探索']['退化'] if isinstance(v['探索']['退化'], str) and v['探索']['退化'] else '—'} |")
    L.append("")
    L.append("| 基準 | 探索 | 確認 | 早年 |")
    L.append("|---|---|---|---|")
    for nm, key in (("0050", "0050"), ("一直抱正2（早年合成）", "一直抱正2"), ("六四 v1", "六四v1")):
        L.append(f"| {nm} | " + " | ".join(f"{p(B[sg][key]['年化'])}／{p(B[sg][key]['回落'])}" for sg in ("探索", "確認", "早年")) + " |")
    L.append("")
    L.append("## 二、挑中格細項")
    L.append("")
    for f in FAM:
        j = J[f]
        if "確認" not in j:
            continue
        L.append(f"### {FAM[f]}：`{j['格']}`（{plain(f, j['格'])}）")
        L.append("")
        for sg in ("探索", "確認", "早年"):
            r = C[(C["件"] == f) & (C["格"] == j["格"]) & (C["段"] == sg)].iloc[0]
            extra = ""
            if f == "乙":
                extra = f"；正2 比例 平均 {r['正2平均比例']:.2f}、最低 {r['正2比例_最低']:.2f}、最高 {r['正2比例_最高']:.2f}"
            if f == "丙":
                extra = (f"；停出 {int(r['停出次數'])} 次、平均 {r['平均停出天數']:.0f} 個交易日、停出期間原持有標的漲跌平均 {p(r['停出期間持有標的漲跌（放棄組）_平均'])}"
                         f"（中位 {p(r['停出期間漲跌_中位'])}、上漲占 {r['停出期間上漲的比例'] * 100 if np.isfinite(r['停出期間上漲的比例']) else float('nan'):.0f}%）")
            L.append(f"- {sg}：年化 {p(r['年化'])}、回落 {p(r['回落'])}、比值 {r['比值']:.3f}、每年換手 {r['每年換手']:.1f}、成本／年 {p(r['成本／年'], 3)}、"
                     f"抱正2（或持有）時間占比 {r['狀態占比'] * 100:.0f}%、對 0050 {r['對0050判準']}；最大回落從 {r['高點日']} 到 {r['谷底日']}、"
                     f"回到高點 {days(r['回到高點的交易日數'])}{extra}")
        w8, w22 = j["2008窗"], j["2022窗"]
        L.append(f"- 2008 窗（100 萬在 2007-12-31）：谷底剩 {w8['谷底剩（萬）']:.1f} 萬（{w8['谷底日']}）、2009-03 底 {w8['期末（萬）']:.1f} 萬、谷底後回到 100 萬 {days(w8['谷底後回到100萬的交易日數'])}")
        L.append(f"- 2022 窗（100 萬在 2021-12-30）：谷底剩 {w22['谷底剩（萬）']:.1f} 萬（{w22['谷底日']}）、年底 {w22['期末（萬）']:.1f} 萬、谷底後回到 100 萬 {days(w22['谷底後回到100萬的交易日數'])}")
        L.append("")
    L.append("## 三、對照：假訊號（挑中格的權重序列保留、換手日改段內隨機；1,000 次）")
    L.append("")
    L.append("| 件 | 段 | 換手次數 | 隨機中位 | p10～p90 | p（隨機 ≥ 本格） | 隨機贏一直抱正2 | 隨機贏六四 v1 |")
    L.append("|---|---|---|---|---|---|---|---|")
    for f, v in FK.items():
        for sg, x in v.items():
            L.append(f"| {FAM[f]} | {sg} | {x['換手次數']} | {p(x['中位'])} | {p(x['p10'])}～{p(x['p90'])} | {x['p（隨機 ≥ 本格）']:.3f} | "
                     f"{x['隨機贏一直抱正2比例'] * 100:.1f}% | {x['隨機贏六四v1比例'] * 100:.1f}% |")
    L.append("")
    L.append("## 四、探索段前 5 名（描述）")
    L.append("")
    for f, rows in S["探索段前5"].items():
        L.append(f"- {FAM[f]}：" + "；".join(f"`{r['格']}` {p(r['年化'])}／{p(r['回落'])}" for r in rows))
    L.append("")
    L.append("## 五、描述（⛔ 不判）")
    L.append("")
    for k, v in S["描述"].items():
        if k.endswith("現金年1%"):
            L.append(f"- {k}：" + "；".join(f"{sg} {p(x['年化'])}／{p(x['回落'])}" for sg, x in v.items()))
    L.append("- 丙 M 版 R2 取字面（月底當天剛好由下往上穿越才買回）：")
    for k, v in S["描述"]["丙_M×R2_字面讀法"].items():
        L.append(f"  - {k}：" + "；".join(f"{sg} {p(x['年化'])}／{p(x['回落'])}（換手 {x['換手次數']}）" for sg, x in v.items()))
    L.append("")
    L.append("## 六、先驗（登錄 §五；只對事實）")
    L.append("")
    for f in FAM:
        j = J[f]
        if "確認" in j:
            L.append(f"- {FAM[f]}：確認段比一直抱正2 {j['確認']['比一直抱正2（點）']:+.2f} 點、回落 {p(j['確認']['回落'])}（正2 {p(B['確認']['一直抱正2']['回落'])}）；"
                     f"早年段比合成正2 {j['早年']['比一直抱正2（點）']:+.2f} 點；假訊號 p（確認）{FK[f]['確認']['p（隨機 ≥ 本格）']:.3f}")
    L.append("")
    L.append("## 七、出場敏感度（新規矩 ③）")
    L.append("")
    lab = [f for f in FAM if "確認" in J[f] and J[f]["確認"]["對0050判準"] in ("合格", "另列")]
    L.append(("確認段對 0050 為合格／另列的：" + "、".join(lab) + " ⇒ 見 sens 描述") if lab else "沒有合格或另列 ⇒ ⛔ 不跑")
    if "出場敏感度" in S:
        L.append("")
        L.append("| 件 | 出場 | 確認段 年化／回落 | 早年段 年化／回落 |")
        L.append("|---|---|---|---|")
        for f, v in S["出場敏感度"].items():
            for k, x in v.items():
                L.append(f"| {FAM[f]} | {k} | {p(x['確認'][0])}／{p(x['確認'][1])} | {p(x['早年'][0])}／{p(x['早年'][1])} |")
        L.append("")
        L.append(S.get("出場敏感度_註", ""))
        L.append("")
        L.append("⚠ 讀法提醒：出場後要等規則「下次換手」才買回；甲、丙一年只換 0.4～1.3 次 ⇒ AT2（2×ATR 約 6～8%，很快觸發）之後多半長期空手，所以 AT2 年化特別低；"
                 "SL10、R0-40 在確認段較高、早年段較低（方向兩段相反）⇒ 不穩")
    L.append("")
    L.append("## 八、閘與查核")
    L.append("")
    L.append("- 0050 主窗錨、合併序列主庫段 ＝ load_bench（pre 閘）；body 重算退化判定 ＝ pre 逐格")
    if CK:
        L.append(f"- 獨立查核 `researchLowFreq_check.py`（⛔ 不 import 主程式）：{'✅ 全過' if CK['全部過'] else '❌ 有不過'}")
        for k, v in CK.items():
            if isinstance(v, dict):
                L.append(f"  - {k}：{'✅' if v['過'] is True else '❌'} " + "；".join(f"{a}={b}" for a, b in v.items() if a != "過"))
    L.append("")
    L.append("## 九、檔案")
    L.append("")
    L.append("`backtest/researchLowFreq.py`（pre／body／sens）、`researchLowFreq_check.py`、`researchLowFreq_report.py`；resultsLowFreq/：pre_summary.json、pre_degenerate.csv、"
             "cells.csv（44 格 × 3 段）、summary.json、eq_picked.npz、check.json、pre_run.log、body_run.log、check.log")
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L[:22]))


if __name__ == "__main__":
    main()
