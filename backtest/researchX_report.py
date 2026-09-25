# -*- coding: utf-8 -*-
"""PREREGX 交件報告產生器：只讀 resultsX/*.json ⇒ resultsX/X_REPORT_tables.md（數字表；⛔ 不手抄數字）。
敘述段（讀法、判定句）寫在 X_REPORT.md，表格一律從本檔產出後貼入。"""
from __future__ import annotations
import json
import os

OUT = os.path.expanduser("~/tw-p17/backtest/resultsX")
NAME = {"box": "箱型", "cup": "杯柄", "w": "W 底", "hs": "頭肩底", "flag": "旗形", "trend": "趨勢線"}


def pc(x, d=1):
    return "—" if x is None else f"{x * 100:.{d}f}%"


def pp(x, d=2):
    return "—" if x is None else f"{x * 100:+.{d}f}"


def main():
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    F = json.load(open(os.path.join(OUT, "freq.json"), encoding="utf-8"))
    fk = S.get("假訊號臂", {})
    L = []
    L.append("### 頻率（每檔每年；保留事件；⛔ 此表產出時未看任何達成率或報酬）\n")
    L.append("| 臂 | 型 | 保留 | 每檔每年（合併母體） | 中位（曝露 ≥ 1 年） | 型態視窗剔除：價格或停牌／處置／注意 |")
    L.append("|---|---|---:|---:|---:|---|")
    for key, v in F.items():
        if key.startswith("_"):
            continue
        arm, typ = key.split("_")
        a = v["帳"]
        L.append(f"| {arm} | {NAME[typ]} | {v['保留']:,} | {v['每檔每年_合併母體']:.3f} | {v['每檔每年_中位_曝露≥1年']:.3f} | "
                 f"{a['剔除_型態視窗_價格或停牌']:,}／{a['剔除_型態視窗_處置']:,}／{a['剔除_型態視窗_注意']:,} |")
    L.append("\n### 甲：量幅目標達成率（D_A ＝ 事件達成率 − 對照達成率；CI＝月分群）\n")
    L.append("| 型 | n | H | 事件達成率 | 對照達成率 | D_A（pp） | 95% CI（pp） | n_eff | 出口 | 結果 | 假訊號臂 判過／30 |")
    L.append("|---|---:|---|---:|---:|---:|---|---:|---|---|---:|")
    for typ in ("box", "cup", "w", "hs", "flag"):
        r = S["甲"][typ]
        for H in (60, 120):
            j = r[f"H{H}"]
            fa = fk.get(f"甲_{typ}_H{H}", {})
            L.append(f"| {NAME[typ]} | {j['n']:,} | {H} | {pc(j.get('事件達成率'))} | {pc(j.get('對照達成率'))} | {pp(j.get('D'))} | "
                     f"[{pp(j.get('lo'))}, {pp(j.get('hi'))}] | {j.get('n_eff')} | {j['出口']} | {j['結果']} | {fa.get('判過', '—')} |")
    L.append("\n| 型 | 格的結果（兩個 H） | 目標距離％ 中位［p10, p90］ | 開盤即達成 | H60 達成天數中位 | H120 達成天數中位 | H60 先碰型態低點 | H120 先碰型態低點 |")
    L.append("|---|---|---|---:|---:|---:|---:|---:|")
    for typ in ("box", "cup", "w", "hs", "flag"):
        r = S["甲"][typ]; d = r["描述"]; q = d["目標距離％分佈"]
        L.append(f"| {NAME[typ]} | {r['格的結果']} | {pc(q.get('中位'))}［{pc(q.get('p10'))}, {pc(q.get('p90'))}］ | {pc(d['開盤即達成比例'], 2)} | "
                 f"{d['H60']['達成天數中位（事件）']} | {d['H120']['達成天數中位（事件）']} | {pc(d['H60']['先碰型態低點比例'])} | {pc(d['H120']['先碰型態低點比例'])} |")
    c = S["甲"]["cup"]["描述"]
    L.append(f"\n杯柄半杯深（描述）：H60 {pc(c['H60'].get('半杯深達成率（描述）'))}、H120 {pc(c['H120'].get('半杯深達成率（描述）'))}。")
    L.append("\n### 乙：成形前讀法（分母＝全部形成中時點 S；X ＝ 20 日報酬 − 0.585% − 同段 gate3 等權）\n")
    L.append("| 型 | n（S） | 成形率［CI］ | 破壞率［CI］ | 都沒發生 | 20 日超額 X（pp） | 95% CI（pp） | n_eff | 出口 | 結果 | 假訊號臂 判過／30 |")
    L.append("|---|---:|---|---|---:|---:|---|---:|---|---|---:|")
    for typ in ("box", "cup", "w", "hs", "flag", "trend"):
        r = S["乙"][typ]; j = r["判定"]; rt = r["率"]
        fa = fk.get(f"乙_{typ}", {})
        L.append(f"| {NAME[typ]} | {j['n']:,} | {pc(rt['成形']['率'])}［{pc(rt['成形']['lo'])}, {pc(rt['成形']['hi'])}］ | "
                 f"{pc(rt['破壞']['率'])}［{pc(rt['破壞']['lo'])}, {pc(rt['破壞']['hi'])}］ | {pc(rt['都沒發生']['率'])} | {pp(j.get('D'))} | "
                 f"[{pp(j.get('lo'))}, {pp(j.get('hi'))}] | {j.get('n_eff')} | {j['出口']} | {j['結果']} | {fa.get('判過', '—')} |")
    L.append("\n描述（⛔ 不進判定：分組用到 S 之後的資訊）——各結局組的 20 日超額 X（pp）：\n")
    L.append("| 型 | 成形組 | 破壞組 | 都沒發生組 |")
    L.append("|---|---:|---:|---:|")
    for typ in ("box", "cup", "w", "hs", "flag", "trend"):
        rt = S["乙"][typ]["率"]
        L.append(f"| {NAME[typ]} | {pp(rt['成形']['20日超額（描述）'])}（{rt['成形']['筆數']:,}） | {pp(rt['破壞']['20日超額（描述）'])}（{rt['破壞']['筆數']:,}） | "
                 f"{pp(rt['都沒發生']['20日超額（描述）'])}（{rt['都沒發生']['筆數']:,}） |")
    open(os.path.join(OUT, "X_REPORT_tables.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
