#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mops_news.py — 公開資訊觀測站【重大訊息】全市場逐日 ⇒ data/mops/news/<西元年>.csv

    python3 mops_news.py --start 1999-01-01 --end 2026-09-29 [--sleep 5] [--budget-min 300]

## 為什麼（2026-09-29）

台股 seq358／360（飆股回推比對 §九之三：題材／熱度代理）；使用者：「記錄一下個股報導什麼會有什麼反應」
⇒ 重大訊息＝「公司說了什麼、幾點說的」；反應用日 K 另算（本支只收訊息，⛔ 不算報酬）。
⚠ 證交所使用條款禁止未經同意的自動程式下載；使用者 2026-09-29 裁「照舊繼續」（量小、有間隔）⇒ 本支照這個做法。

## 端點（2026-09-29 實測）

    POST https://mops.twse.com.tw/mops/api/t05st02   content-type: application/json
    body {"year":"<民國年>","month":"<月>","day":"<日兩碼>"}
    ⇒ {"code":200,"message":"查詢成功","result":{"titles":[…],"data":[[發言日期,發言時間,公司代號,公司名稱,主旨,
        {"apiName":"t05st02_detail","parameters":{"marketKind":"sii|otc|rotc|pub","companyId":…,"serialNumber":…,"enterDate":…}}], …]}}
  最早：民國 88 年（1999-01）｜一天一發回全市場
  ⚠ 查某一天會連【前一個工作日 17:30 以後】的也一起回（例：查 115/09/25（中秋休市）回 60 筆全是 09/24 晚上）
    ⇒ 逐日接起來【一定會重複】⇒ 以 (date, time, stock_id, serial) 為鍵去重
  ⚠ code 不是 200 ⇒ 讀 message（MOPS 的 500／406 意思不同，見 tw-data-endpoints-mops-web）

## ⛔ 判準

  ・每一列的發言日期要落在【查詢日往前 7 天內】，否則整發不收（參數回音／回今天那一族）
  ・有 titles 且第一欄是「發言日期」才算正常頁
"""
import argparse
import csv
import datetime
import io
import json
import os
import sys
import time
import urllib.request

import runlog

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(ROOT, "data", "mops", "news")
ASKED = os.path.join(OUT_DIR, "_asked.json")
URL = "https://mops.twse.com.tw/mops/api/t05st02"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
HEADER = ["date", "time", "stock_id", "name", "market", "serial", "subject"]


def roc_date(s):
    y, m, d = str(s).strip().split("/")
    return "%04d-%02d-%02d" % (int(y) + 1911, int(m), int(d))


def parse(j, day):
    """→ (rows, status, note)。status ∈ ok｜empty｜bad。"""
    if not isinstance(j, dict):
        return [], "bad", "不是 JSON 物件"
    if j.get("code") != 200:
        msg = str(j.get("message", ""))
        if j.get("code") == 406 or "查無" in msg:
            return [], "empty", msg
        return [], "bad", f"code={j.get('code')} message={msg}"
    res = j.get("result") or {}
    titles = [t.get("main") for t in (res.get("titles") or []) if isinstance(t, dict)]
    if not titles or titles[0] != "發言日期":
        return [], "bad", f"表頭不對：{titles}"
    lo = (datetime.date.fromisoformat(day) - datetime.timedelta(days=7)).isoformat()
    rows = []
    for r in res.get("data") or []:
        if not isinstance(r, list) or len(r) < 6:
            continue
        d = roc_date(r[0])
        if not (lo <= d <= day):
            return [], "bad", f"自述日期 {d} 不在查詢日 {day} 往前 7 天內"
        p = (r[5] or {}).get("parameters", {}) if isinstance(r[5], dict) else {}
        subj = " ".join(str(r[4]).split())
        rows.append([d, str(r[1]).strip(), str(r[2]).strip(), str(r[3]).strip(), p.get("marketKind", ""),
                     str(p.get("serialNumber", "")), subj])
    return rows, ("ok" if rows else "empty"), f"{len(rows)} 則"


def fetch(day):
    y, m, d = day.split("-")
    body = json.dumps({"year": str(int(y) - 1911), "month": str(int(m)), "day": d}).encode()
    req = urllib.request.Request(URL, data=body, headers={"content-type": "application/json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def load_year(y):
    p = os.path.join(OUT_DIR, f"{y}.csv")
    if not os.path.exists(p):
        return {}
    with io.open(p, encoding="utf-8") as f:
        return {(r["date"], r["time"], r["stock_id"], r["serial"]): [r[h] for h in HEADER] for r in csv.DictReader(f)}


def save_year(y, rows):
    with io.open(os.path.join(OUT_DIR, f"{y}.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(HEADER)
        w.writerows(sorted(rows.values()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="1999-01-01")
    ap.add_argument("--end", default=datetime.date.today().isoformat())
    ap.add_argument("--sleep", type=float, default=5)
    ap.add_argument("--budget-min", type=float, default=300)
    a = ap.parse_args()
    t0 = time.time()
    os.makedirs(OUT_DIR, exist_ok=True)
    asked = json.load(io.open(ASKED, encoding="utf-8")) if os.path.exists(ASKED) else {}
    rl = runlog.Run("mops_news")
    d, end = datetime.date.fromisoformat(a.start), datetime.date.fromisoformat(a.end)
    today = datetime.date.today().isoformat()
    todo = []
    while d <= end:
        k = d.isoformat()
        if asked.get(k, "").split(":")[0] not in ("ok", "empty") or k >= today:
            todo.append(k)
        d += datetime.timedelta(days=1)
    rl.info("區間", f"{a.start} ~ {a.end}｜待問 {len(todo)} 天（已問過 {len(asked)}）")
    years, dirty = {}, set()
    n = ok = empty = bad = added = 0
    bads = []
    for day in todo:
        if (time.time() - t0) / 60 > a.budget_min:
            break
        try:
            rows, st, note = parse(fetch(day), day)
        except Exception as e:                      # noqa: BLE001
            rows, st, note = [], "bad", f"{type(e).__name__}: {e}"
        n += 1
        asked[day] = f"{st}:{len(rows)}"
        if st == "bad":
            bad += 1
            bads.append((day, note))
        else:
            ok += st == "ok"
            empty += st == "empty"
            for r in rows:
                y = r[0][:4]
                if y not in years:
                    years[y] = load_year(y)
                k = (r[0], r[1], r[2], r[5])
                if k not in years[y]:
                    added += 1
                years[y][k] = r
                dirty.add(y)
        if n % 100 == 0:
            for y in dirty:
                save_year(y, years[y])
            json.dump(asked, io.open(ASKED, "w", encoding="utf-8"), ensure_ascii=False, sort_keys=True, indent=0)
            print(f"[mops_news] {n}/{len(todo)}｜ok {ok} empty {empty} bad {bad}｜新增 {added}｜{(time.time() - t0) / 60:.0f} 分")
        time.sleep(a.sleep)
    for y in dirty:
        save_year(y, years[y])
    json.dump(asked, io.open(ASKED, "w", encoding="utf-8"), ensure_ascii=False, sort_keys=True, indent=0)
    rl.info("本趟", f"問 {n} 天｜ok {ok}｜empty {empty}｜失敗 {bad}｜新增 {added} 則｜剩 {len(todo) - n} 天｜{(time.time() - t0) / 60:.0f} 分")
    if bads:
        rl.info("失敗的（前 10）", str(bads[:10]))
    rl.check("失敗 ≤ 本趟 2%", bad <= max(2, 0.02 * max(1, n)), f"{bad}／{n}")
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
