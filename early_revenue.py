#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""早年段（2015 以前）月營收 ⇒ data/early/revenue/<期別>_<市場>.csv（裁定線 seq149 §二 ③）。

⭐ 重用，⛔ 不另寫：抓取重試、解碼、解析、寫檔全走 mops_history 的 _fetch／parse_revenue／write_csv；
   輸出欄位與 data/mops/revenue_hist 相同（stock_id,name,period,market,產業別＋官方九欄）。
⛔⛔ 放 data/early/，⛔ 不併進 data/mops/revenue_hist（seq149：避免主窗程式讀到）。
⛔⛔ 驗收段守則：只做結構驗證（列數、頁面自述期別、表頭、產業別有無）⛔ 不讀營收數字、不算成長率。

⭐ 網址用【無尾碼】那一種：t21sc03_<民國年>_<月>.html（本線 2026-09-25 實測）
   民國 91/12～98 只有它（_0、_1 都 404，上櫃到 98/12 仍 404）
   民國 99～103 它與 _0、_1 並存，且列數 ＝ _0 ＋ _1（99/06、100/01、103/12 兩市場逐一相符）
   ⇒ 一發就涵蓋國內＋外國企業，⭐ 整個早年段只用同一種網址（⛔ 不在 99 年換口徑）
⭐ 頁面自述期別（「NN年M月」）必須等於請求的期別，⛔ 不符就不寫（參數回音那一族的防線）
"""
import argparse
import csv
import io
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mops_history as M
import runlog

OUT = os.path.join(HERE, "data", "early", "revenue")
LEDGER = os.path.join(HERE, "data", "early", "_revenue_structure.csv")
WANT = ["公司代號", "公司名稱", "當月營收", "上月營收", "去年當月營收", "上月比較增減(%)",
        "去年同月增減(%)", "當月累計營收", "去年累計營收", "前期比較增減(%)"]


def url(mkt, roc, m):
    return f"{M.MOPSOV}/nas/t21/{mkt}/t21sc03_{roc}_{m}.html"


def self_period(raw):
    txt, _enc = M._decode(raw)
    t = re.sub(r"<[^>]+>|\s", "", txt)
    me = re.search(r"(\d{2,3})年(\d{1,2})月", t)
    return (int(me.group(1)), int(me.group(2))) if me else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2003-01")
    ap.add_argument("--end", default="2014-12")
    ap.add_argument("--sleep", type=float, default=3.0)
    a = ap.parse_args()
    end = min(a.end[:7], "2014-12")
    rl = runlog.Run("early:revenue")
    led = {}
    if os.path.exists(LEDGER):
        with io.open(LEDGER, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                led[(r["period"], r["market"])] = r
    y, m = int(a.start[:4]), int(a.start[5:7])
    done = skipped = 0
    fails = []
    while (y, m) <= (int(end[:4]), int(end[5:7])):
        per = f"{y:04d}-{m:02d}"
        for mkt, market in M.MARKETS:
            path = os.path.join(OUT, f"{per}_{market}.csv")
            if os.path.exists(path) and (per, market) in led:
                skipped += 1
                continue
            roc = y - 1911
            raw, err = M._fetch(url(mkt, roc, m))
            time.sleep(a.sleep)
            if err:
                fails.append((per, market, M._W(err, 40)))
                continue
            sp = self_period(raw)
            rows, hd, note, _sk = M.parse_revenue(raw, roc, m, mkt)
            if (not rows or not hd) and sp == (roc, m):
                # 一次壞回應（主線 2026-03 中過）⇒ 重抓一次再判
                raw, err = M._fetch(url(mkt, roc, m))
                time.sleep(a.sleep)
                rows, hd, note, _sk = M.parse_revenue(raw, roc, m, mkt) if not err else ([], None, err, [])
            if sp != (roc, m):
                fails.append((per, market, f"頁面自述 {sp} ≠ 請求 {(roc, m)}"))
                continue
            if hd != WANT:
                fails.append((per, market, f"表頭不是預期的十欄：{hd}"))
                continue
            if not rows:
                fails.append((per, market, "0 列：" + M._W(note, 40)))
                continue
            nosec = sum(1 for r in rows if not r[2])
            full = ["stock_id", "name", "period", "market", "產業別"] + hd[2:]
            M.write_csv(path, full, [[r[0], r[1], per, market, r[2]] + r[3:] for r in rows])
            codes = [r[0] for r in rows]
            led[(per, market)] = {"period": per, "market": market, "url": url(mkt, roc, m).split("/")[-1],
                                  "self_period": "%d年%d月" % sp, "rows": len(rows),
                                  "distinct_codes": len(set(codes)), "no_sector": nosec}
            done += 1
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    cols = ["period", "market", "url", "self_period", "rows", "distinct_codes", "no_sector"]
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with io.open(LEDGER, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, cols, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        for k in sorted(led):
            w.writerow(led[k])
    dup = [k for k, r in led.items() if int(r["rows"]) != int(r["distinct_codes"])]
    rl.info("本趟", "寫 %d 期檔｜已有跳過 %d｜失敗 %d｜台帳共 %d 期檔" % (done, skipped, len(fails), len(led)))
    if fails:
        rl.info("失敗（前 10）", str(fails[:10]))
    if dup:
        rl.info("⚠ 同一期檔代號重複", str(sorted(dup)[:10]))
    rl.check("失敗 0 期（自述期別、表頭、列數都要過）", not fails, str(fails[:5]))
    rl.finish()
    print("revenue 寫 %d｜跳過 %d｜失敗 %d｜代號重複的期檔 %d" % (done, skipped, len(fails), len(dup)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
