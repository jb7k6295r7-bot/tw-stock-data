#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""上市「漲跌(+/-)」官方 X（不比價）旗標 ⇒ data/meta/twse_change_x.csv（date,stock_id）

    python3 twse_xflag.py --start 2004-02-11 --end 2026-10-02 [--sleep 3] [--budget-min 300]
    python3 twse_xflag.py --day 2026-10-05          # daily 用：只問一天

## 為什麼（2026-10-04，裁定 seq293 §二、seq297 §二核准）

日檔 change 欄只存「正負號 × 漲跌價差」⇒ 官方 X0.00 被存成 0.0、X 這個字丟了（2015 起 27,217 列）。
⛔ 日檔欄位不動（下游全部讀它）⇒ 另立旗標檔；⛔ 不用「收盤−前收」去猜（回測 1733：會丟 198 筆真減資）。

## 判準
  ・回應 stat 要 OK、自述 date 要等於問的那一天（⛔ 參數回音／回今天那一族）
  ・要找得到同時有「證券代號」與「漲跌(+/-)」欄的表
  ・旗標＝「漲跌(+/-)」那一格的可見文字是 X
台帳 data/meta/_twse_change_x_asked.csv：date,status,n_x（ok｜empty 休市｜bad）
上櫃不需要：TPEx 漲跌欄本身帶正負號、不比價時為空。
"""
import argparse, csv, datetime, io, json, os, re, sys, time, urllib.request

import runlog

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "data", "meta", "twse_change_x.csv")
ASKED = os.path.join(ROOT, "data", "meta", "_twse_change_x_asked.csv")
URL = "https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date={ymd}&type=ALLBUT0999&response=json"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
TAG = re.compile(r"<[^>]*>")


def parse(j, day):
    """→ (codes, status, note)。status ∈ ok｜empty｜bad。"""
    if not isinstance(j, dict):
        return [], "bad", "不是 JSON 物件"
    stat = str(j.get("stat", ""))
    if stat != "OK":
        if "沒有符合" in stat or "查詢日期" in stat or "休市" in stat:
            return [], "empty", stat
        return [], "bad", f"stat={stat}"
    said = str(j.get("date", ""))
    if said != day.replace("-", ""):
        return [], "bad", f"自述日期 {said} ≠ {day}"
    for t in j.get("tables") or []:
        f = [str(x) for x in (t.get("fields") or [])]
        if "證券代號" in f and any(x.startswith("漲跌(+/-)") for x in f):
            ic, isg = f.index("證券代號"), next(i for i, x in enumerate(f) if x.startswith("漲跌(+/-)"))
            codes = []
            for r in t.get("data") or []:
                if len(r) > max(ic, isg) and TAG.sub("", str(r[isg])).strip().upper() == "X":
                    codes.append(str(r[ic]).strip())
            return codes, "ok", f"{len(t.get('data') or [])} 列，X {len(codes)}"
    return [], "bad", "找不到同時有「證券代號」「漲跌(+/-)」的表"


def fetch(day):
    req = urllib.request.Request(URL.format(ymd=day.replace("-", "")), headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def trading_days(start, end):
    """上市交易日：calendar_twse（2015 起）∪ market_index 的日期（1990 起）；⛔ 不自己猜假日。"""
    s = set()
    for p, col in ((os.path.join(ROOT, "data", "meta", "calendar_twse.csv"), "date"),
                   (os.path.join(ROOT, "data", "history", "market_index.csv"), "date")):
        if os.path.exists(p):
            with io.open(p, encoding="utf-8") as f:
                s.update(r[col] for r in csv.DictReader(f) if r.get(col))
    return sorted(d for d in s if start <= d <= end)


def _read(p, header):
    if not os.path.exists(p):
        return []
    with io.open(p, encoding="utf-8") as f:
        r = csv.reader(f)
        h = next(r, None)
        if h != header:
            raise SystemExit(f"⛔ {p} 表頭不符：{h}")
        return [x for x in r if x]


def _write(p, header, rows):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2004-02-11")
    ap.add_argument("--end", default=datetime.date.today().isoformat())
    ap.add_argument("--day", help="只問這一天（daily 用；⭐ 已問過也重問）")
    ap.add_argument("--sleep", type=float, default=3)
    ap.add_argument("--budget-min", type=float, default=300)
    a = ap.parse_args()
    t0 = time.time()
    rl = runlog.Run("twse_xflag")
    flags = {(r[0], r[1]) for r in _read(OUT, ["date", "stock_id"])}
    asked = {r[0]: r for r in _read(ASKED, ["date", "status", "n_x"])}
    if a.day:
        todo = [a.day]
    else:
        todo = [d for d in trading_days(a.start, a.end) if asked.get(d, [None, ""])[1] not in ("ok", "empty")]
    rl.info("待問", f"{len(todo)} 天（台帳已有 {len(asked)}）")
    n = ok = empty = bad = added = 0
    bads = []
    for d in todo:
        if (time.time() - t0) / 60 > a.budget_min:
            break
        try:
            codes, st, note = parse(fetch(d), d)
        except Exception as e:                       # noqa: BLE001
            codes, st, note = [], "bad", f"{type(e).__name__}: {e}"
        n += 1
        asked[d] = [d, st, str(len(codes))]
        if st == "bad":
            bad += 1
            bads.append((d, note))
        else:
            ok += st == "ok"
            empty += st == "empty"
            # 同一天重問：先清掉那天舊的旗標再寫（官方若更正，以最新為準）
            flags = {k for k in flags if k[0] != d}
            for c in codes:
                flags.add((d, c))
                added += 1
        if n % 100 == 0:
            _write(OUT, ["date", "stock_id"], sorted(flags))
            _write(ASKED, ["date", "status", "n_x"], sorted(asked.values()))
            print(f"[xflag] {n}/{len(todo)}｜ok {ok} empty {empty} bad {bad}｜{(time.time() - t0) / 60:.0f} 分", flush=True)
        time.sleep(a.sleep)
    _write(OUT, ["date", "stock_id"], sorted(flags))
    _write(ASKED, ["date", "status", "n_x"], sorted(asked.values()))
    rl.info("本趟", f"問 {n} 天｜ok {ok}｜empty {empty}｜失敗 {bad}｜旗標 {added} 列｜剩 {len(todo) - n} 天｜{(time.time() - t0) / 60:.0f} 分")
    if bads:
        rl.info("失敗的（前 10）", str(bads[:10]))
    rl.check("失敗 ≤ 本趟 2%", bad <= max(2, 0.02 * max(1, n)), f"{bad}／{n}")
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
