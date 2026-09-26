#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""filing_dates.py — 財報【上傳日期】（doc.twse t57sb01）逐家逐年抓進 data/meta/filing_dates.csv。

    python3 filing_dates.py --start-year 2015 --end-year 2026 --sleep 3.5 --budget-min 300

## 為什麼要有（2026-09-27）

G（台股 seq4）與 PREREG大師三套（裁定 seq210）都把財報的【可用日】定成
「t57sb01 上傳日期的下一個交易日」⇒ 要全市場逐季的上傳時點。
本線 2026-09-25 1549 已實測：一發只能問「一家 × 一年」、不帶 co_id 回 0 列 ⇒ 沒有全市場一次拿的路。

## 一發回什麼（2026-09-27 實測 2330／1342 民國 113）

    2330 | 113 年 第一季 | 財務報告書 | | | IFRSs合併財報 | | 202401_2330_AI1.pdf | 8,048,457 | 113/05/15 14:25:29 | 無
    1342 | 113 年 第一季 | 財務報告書 | | | IFRSs個別財報 | | 202401_1342_AI2.pdf | 1,305,118 | 113/05/09 10:54:03 | 無
  檔名尾碼：AI1 合併｜AI2 個別（沒有子公司的公司只有這一份）｜AI3 個體（Q4）｜AIA／AIB／AIC 英文版
  ⚠ Q4（年報）列在【該會計年度】那一頁，上傳日在隔年（2330 113 Q4 ＝ 114/02/27）⇒ 一家一年一發就夠
  ⭐ 讀的人要的「中文主報表」＝ 有 AI1 取 AI1，否則 AI2（本支全部照收，⛔ 不在這裡挑）

## ⛔ 判準（照 filing_probe.py 那兩條）

  ① 擋阻頁（HTTP 200 但內容是「因為安全性考量」）⇒ 失敗，⛔ 不是「那年沒有財報」
  ② 回應要自己講出它是哪一家、哪一年：每一列的代號＝送出的 co_id、民國年＝送出的 year，
     任何一列對不上 ⇒ 整發不採用
  ③ 頁面沒有「上傳日期」表頭 ⇒ 不是正常頁 ⇒ 失敗；有表頭但 0 列 ⇒ status=empty（那年確實沒有檔）
"""
import argparse
import csv
import glob
import html
import io
import os
import re
import sys
import time

import runlog
from filing_probe import DOC, hit, looks_blocked

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "data", "meta", "filing_dates.csv")
ASKED = os.path.join(ROOT, "data", "meta", "_filing_dates_asked.csv")
FS_HIST = os.path.join(ROOT, "data", "mops", "fs_hist")
HEADER = ["stock_id", "year", "season", "doc_code", "doc_type", "file", "bytes", "uploaded_at", "corrected"]
ASKED_HEADER = ["stock_id", "roc_year", "status", "rows", "asked_at"]
SEASON = {"第一季": 1, "第二季": 2, "第三季": 3, "第四季": 4}


def parse(body, co_id, roc_year):
    """→ (rows, status, note)。status ∈ ok｜empty｜bad。⛔ 對不上就 bad，不猜。"""
    if not body:
        return [], "bad", "空回應"
    if looks_blocked(body):
        return [], "bad", "擋阻頁"
    txt = body.decode("big5", "replace")
    if "上傳日期" not in txt:
        return [], "bad", "沒有「上傳日期」表頭（不是正常頁）"
    out = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", txt, re.S | re.I):
        cells = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip()
                 for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S | re.I)]
        if len(cells) < 11 or not re.fullmatch(r"\d{2,3}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}", cells[9]):
            continue
        m = re.fullmatch(r"(\d{2,3})\s*年\s*(第.季)", cells[1])
        if cells[0] != str(co_id) or not m or m.group(1) != str(roc_year) or m.group(2) not in SEASON:
            return [], "bad", f"自述不符：{cells[:2]}（送 {co_id}／{roc_year}）"
        code = re.search(r"_([A-Z0-9]+)\.\w+$", cells[7])
        y, mo, d = cells[9][:cells[9].index(" ")].split("/")
        out.append([str(co_id), str(int(roc_year) + 1911), str(SEASON[m.group(2)]),
                    code.group(1) if code else "", cells[5], cells[7], cells[8].replace(",", ""),
                    "%04d-%s-%s %s" % (int(y) + 1911, mo, d, cells[9].split(" ")[1]), cells[10]])
    return out, ("ok" if out else "empty"), f"{len(out)} 列"


def universe(start, end):
    """→ {西元年: set(代號)}：該年 fs_hist 有報表的公司（含之後下市的，⛔ 不用今天的名冊＝存活者偏差）。"""
    u = {}
    for p in glob.glob(os.path.join(FS_HIST, "*.csv")):
        y = int(os.path.basename(p)[:4])
        if start <= y <= end:
            with io.open(p, encoding="utf-8") as f:
                u.setdefault(y, set()).update(r["stock_id"] for r in csv.DictReader(f))
    return u


def _read(path, header):
    if not os.path.exists(path):
        return []
    with io.open(path, encoding="utf-8") as f:
        r = csv.reader(f)
        h = next(r, None)
        if h != header:
            raise SystemExit(f"⛔ {path} 表頭不符：{h}")
        return list(r)


def _write(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start-year", type=int, default=2015)
    ap.add_argument("--end-year", type=int, default=2026)
    ap.add_argument("--sleep", type=float, default=3.5)
    ap.add_argument("--budget-min", type=float, default=300)
    ap.add_argument("--refresh-year", type=int, default=0, help="這一年已問過的也重問（當年還在出新季報）")
    ap.add_argument("--max", type=int, default=10 ** 9)
    a = ap.parse_args()
    t0 = time.time()
    rl = runlog.Run("filing_dates")
    uni = universe(a.start_year, a.end_year)
    if not uni:
        raise SystemExit("⛔ data/mops/fs_hist 是空的 ⇒ 沒有公司清單（⛔ 不退回今天的名冊）")
    asked = {(r[0], r[1]): r for r in _read(ASKED, ASKED_HEADER)}
    rows = {tuple(r[:4]): r for r in _read(OUT, HEADER)}
    todo = [(s, y) for y in sorted(uni) for s in sorted(uni[y])
            if (asked.get((s, str(y - 1911)), [None, None, ""])[2] not in ("ok", "empty")
                or y == a.refresh_year)]
    rl.info("母體", "｜".join(f"{y}:{len(uni[y])}" for y in sorted(uni)))
    rl.info("待問", f"{len(todo)} 發（已問過 {sum(len(v) for v in uni.values()) - len(todo)}）")
    n = ok = empty = bad = 0
    streak = 0
    bads = []
    for s, y in todo:
        if n >= a.max or (time.time() - t0) / 60 > a.budget_min:
            break
        roc = y - 1911
        url = f"{DOC}?step=1&colorchg=1&co_id={s}&year={roc}&mtype=A&"
        st, _, body, err = hit(url)
        got, status, note = parse(body, s, roc) if st == 200 else ([], "bad", f"HTTP {st} {err}")
        n += 1
        asked[(s, str(roc))] = [s, str(roc), status, str(len(got)), time.strftime("%Y-%m-%d %H:%M:%S")]
        if status == "bad":
            bad += 1
            streak += 1
            bads.append((s, roc, note))        # ⛔ 錯誤訊息不砍尾巴（CLAUDE.md 六點六）
        else:
            streak = 0
            ok += status == "ok"
            empty += status == "empty"
            for r in got:
                rows[tuple(r[:4])] = r
        if streak >= 8:
            print(f"[filing_dates] 連續 {streak} 發失敗，收手（最後：{bads[-1]}）", file=sys.stderr)
            break
        if n % 200 == 0:
            _write(OUT, HEADER, sorted(rows.values()))
            _write(ASKED, ASKED_HEADER, sorted(asked.values()))
            print(f"[filing_dates] {n}/{len(todo)}｜ok {ok} empty {empty} bad {bad}｜{(time.time() - t0) / 60:.0f} 分")
        time.sleep(a.sleep)
    _write(OUT, HEADER, sorted(rows.values()))
    _write(ASKED, ASKED_HEADER, sorted(asked.values()))
    left = len(todo) - n
    rl.info("本趟", f"問 {n} 發｜ok {ok}｜empty（那年沒有檔）{empty}｜失敗 {bad}｜剩 {left} 發｜{(time.time() - t0) / 60:.0f} 分")
    rl.info("累計", f"上傳紀錄 {len(rows)} 列｜已問 (家, 年) {sum(1 for v in asked.values() if v[2] in ('ok', 'empty'))}")
    if bads:
        rl.info("失敗的（前 10）", str(bads[:10]))
    rl.check("沒有連續失敗而收手", streak < 8, f"最後連續 {streak} 發失敗")
    rl.check("失敗 ≤ 本趟 2%", bad <= max(2, 0.02 * max(1, n)), f"{bad}／{n}")
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
