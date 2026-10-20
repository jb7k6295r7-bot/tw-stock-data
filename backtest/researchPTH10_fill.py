# -*- coding: utf-8 -*-
"""PTH 最高 10 檔前瞻（裁定 seq402、seq403 §三）的歷史描述：每月平均補幾檔、幾成月份一檔都沒補——回測線計算子代理。
⛔ 只數既有交易檔的買進日；⛔ 不讀、不算任何報酬（交易檔只讀 sid、形成月底、買進日、賣出日四欄，R用／入帳／金額 ⛔ 不讀）。
⛔ 不 commit、不改既有程式與結果夾；backtest/resultsPTHpf/trades_<世界>_S10.csv.gz（＝ researchPTHpf 描述① 10 檔版：10 格、每格買進時投入淨值 1/10、
   每月初從當批 PTH 由高往下補空位、已持有跳過、每檔抱 6 個月、空位放 0050；逐字即 seq402 指定的前瞻做法）與 resultsPTH/freq/monthly.csv ⛔ 只讀。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTH10_fill
輸出 backtest/resultsPTH10fill/：fill.json、fill_by_seg.csv、fill_monthly.csv、run.log

讀法（★ 執行者定）：
 F1 批次月 ＝ resultsPTH/freq/monthly.csv 中「跳月_保留 ＞ 0」的形成月，其跳月進場日所在曆月（＝ 每月初補空位的那一天）；⛔ 不另算事件。
 F2 每月補幾檔 ＝ 10 檔版交易檔中買進日 ＝ 該批進場日的筆數（同檔多批各自一筆）；買進日不在任何批次進場日 ⇒ 中止（10 檔版只在批次日買）。
 F3 段 ＝ 依批次進場日：探索 2017-03-02～2021-12-30｜確認 2022-01-03～資料尾｜早年 2005-01-01～2014-12-31｜主世界段前 2016-03～2017-02（主世界第一批到探索前，只報）。
    另報「扣該世界第一批」（建倉月一次補 10 檔）的版本。
 F4 對帳：① 由交易檔直接按買進曆月計數（不經批次表）⇒ 與 F2 逐月相同；② 每月補的檔數 ＝ 當月初空位數上限 ≤ 10；③ 同一天同檔不重複。
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
os.chdir(os.path.expanduser("~/tw-p17"))

TR = "backtest/resultsPTHpf/trades_{}_S10.csv.gz"
MON = "backtest/resultsPTH/freq/monthly.csv"
OUT = "backtest/resultsPTH10fill"
SEGS = {"主": {"主世界段前": ("2016-01-01", "2017-03-01"), "探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2099-12-31")},
        "早年": {"早年": ("2005-01-01", "2014-12-31")}}
LOG = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def bins(v):
    v = np.asarray(v, int)
    return {"0": int((v == 0).sum()), "1～2": int(((v >= 1) & (v <= 2)).sum()), "3～5": int(((v >= 3) & (v <= 5)).sum()),
            "6～9": int(((v >= 6) & (v <= 9)).sum()), "10": int((v == 10).sum())}


def main():
    os.makedirs(OUT, exist_ok=True)
    M = pd.read_csv(MON, dtype={"跳月_進場日": str})
    J = {"性質": "PTH 最高 10 檔（10 格補空位）歷史每月補檔頻率（⛔ 未讀任何報酬欄）", "裁定": "seq402、seq403 §三", "世界": {}}
    SEGROWS = []; MROWS = []
    for wn in ("主", "早年"):
        T = pd.read_csv(TR.format(wn), dtype={"sid": str}, usecols=["sid", "形成月底", "買進日", "賣出日"])
        mw = M[(M["世界"] == wn) & (M["跳月_保留"] > 0) & M["跳月_進場日"].notna() & (M["跳月_進場日"] != "")]
        bdays = sorted(set(mw["跳月_進場日"]))
        first_batch = bdays[0]
        nb = T.groupby("買進日").size()
        off = sorted(set(nb.index) - set(bdays))
        if off:
            raise SystemExit(f"⛔ {wn} 買進日不在批次日：{off[:5]}")
        if T.duplicated(["sid", "買進日"]).any():
            raise SystemExit(f"⛔ {wn} 同日同檔重複")
        if (nb > 10).any():
            raise SystemExit(f"⛔ {wn} 單日買進 ＞ 10")
        per = pd.DataFrame({"批次進場日": bdays})
        per["補檔"] = per["批次進場日"].map(nb).fillna(0).astype(int)
        per["曆月"] = per["批次進場日"].str[:7]
        if per["曆月"].duplicated().any():
            raise SystemExit(f"⛔ {wn} 同一曆月兩個批次日")
        # 對帳 ①：直接按買進曆月
        alt = T.assign(m=T["買進日"].str[:7]).groupby("m").size()
        chk = per.set_index("曆月")["補檔"]
        bad = [(m, int(chk.get(m, 0)), int(alt.get(m, 0))) for m in sorted(set(chk.index) | set(alt.index)) if int(chk.get(m, 0)) != int(alt.get(m, 0))]
        if bad:
            raise SystemExit(f"⛔ {wn} 對帳①不同：{bad[:5]}")
        # 對帳 ②：月初空位上限（持有中筆數 ＝ 買進日 ≤ d 且 賣出日 ≥ d 的前一批……以「之前買進且賣出日 ≥ 本批日」計）
        held_before = []
        for d in per["批次進場日"]:
            held_before.append(int(((T["買進日"] < d) & (T["賣出日"] >= d)).sum()))
        per["批前仍持有"] = held_before
        per["空位上限"] = 10 - per["批前仍持有"]
        n_over = int((per["補檔"] > per["空位上限"]).sum())
        for _, r in per.iterrows():
            MROWS.append({"世界": wn, **r.to_dict()})
        Wj = {"批次月數": len(per), "第一批": first_batch, "最後一批": bdays[-1], "交易筆數": len(T), "對帳①按買進曆月逐月相同": True,
              "對帳②補檔超過空位上限的月數": n_over, "段": {}}
        for sg, (a, b) in SEGS[wn].items():
            for drop_first in (False, True):
                sub = per[(per["批次進場日"] >= a) & (per["批次進場日"] <= b)]
                if drop_first:
                    sub = sub[sub["批次進場日"] != first_batch]
                if not len(sub):
                    continue
                v = sub["補檔"].to_numpy()
                row = {"世界": wn, "段": sg, "扣第一批": drop_first, "批次月": int(len(sub)), "期間": f"{sub['批次進場日'].iloc[0]}～{sub['批次進場日'].iloc[-1]}",
                       "補檔合計": int(v.sum()), "每月平均補檔": round(float(v.mean()), 3), "每月補檔中位": float(np.median(v)),
                       "一檔都沒補的月數": int((v == 0).sum()), "一檔都沒補比例": round(float((v == 0).mean()), 4),
                       "有補的月平均補檔": round(float(v[v > 0].mean()), 3) if (v > 0).any() else None, **{f"分布_{k}": x for k, x in bins(v).items()}}
                SEGROWS.append(row)
                Wj["段"][f"{sg}{'_扣第一批' if drop_first else ''}"] = row
        J["世界"][wn] = Wj
        log(f"[{wn}] " + "｜".join(f"{r['段']}{'(扣首批)' if r['扣第一批'] else ''} 月{r['批次月']} 平均{r['每月平均補檔']} 零補{r['一檔都沒補比例']:.1%}" for r in SEGROWS if r["世界"] == wn))
    J["時間"] = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")
    pd.DataFrame(SEGROWS).to_csv(os.path.join(OUT, "fill_by_seg.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(MROWS).to_csv(os.path.join(OUT, "fill_monthly.csv"), index=False, encoding="utf-8-sig")
    json.dump(J, open(os.path.join(OUT, "fill.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
