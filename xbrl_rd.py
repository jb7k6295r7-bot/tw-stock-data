#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""xbrl_rd.py — 研究發展費用＋營收，從 MOPS「IFRSs 財務報告 XBRL 整批下載」逐季解出 ⇒ data/mops/rd_hist/<YYYYQn>.csv

    python3 xbrl_rd.py --start 2013Q1 --end 2026Q2 [--sleep 20] [--zip-dir 本機樣本目錄]

## 為什麼（2026-09-27，PREREG大師三套 裁定 seq210：墨菲「近 4 季研發費用 ÷ 營收 ＞ 5%」）

IFRS 季彙總表（data/mops/fs_hist）只有「營業費用」合計，t163sb01 簡明表也沒有研發費用。
⇒ 官方唯一整批的來源是 XBRL 整批下載：一季一個 zip、一家一個檔（本線 2026-09-27 子代理勘查＋本線抽驗 2330 2020Q4）。

## 端點與靜默失敗

    https://mopsov.twse.com.tw/server-java/FileDownLoad?step=9&filePath=/home/html/nas/ifrs/<年>/&fileName=tifrs-<年>Q<季>.zip
  ⚠ 只有 mopsov 舊版主機有（mops.twse／doc.twse 同路徑 404）
  ⛔ 季別不存在時回 HTTP 200＋text/html「伺服器忙碌中，請重試一次」⇒ 判定一律看 zip 檔頭 PK，⛔ 不看狀態碼
  ⚠ mopsov 的 robots.txt 是 disallow ⇒ 量小（一季一發）、每發之間長間隔

## 兩代格式（2019Q1 換）

  2013Q1～2018Q4：XBRL instance（.xml）｜元素 tifrs-bsci-ci:ResearchAndDevelopmentExpenses／OperatingRevenue｜單位元
  2019Q1～      ：inline XBRL（.html）  ｜元素 ifrs-full:ResearchAndDevelopmentExpense／Revenue｜scale="3" ⇒ ×1000｜sign="-"
  ⛔ 比對【完整的 local name】：檔內還有 WagesAndSalaries-ResearchAndDevelopmentExpenses 等性質別明細，子字串比對會抓錯
  context 名稱自帶期間（From20130401To20130630）⇒ 只取【本期】：迄日＝季底；起日＝季初 ⇒ 單季（*_q），起日＝1/1 ⇒ 累計（*_ytd）
  ⚠ Q4 只有全年 ⇒ rd_q／rev_q 空白；單季 Q4 ＝ 全年 − Q3 累計，由讀的人算（⛔ 本支不跨檔相減）

## 口徑（⛔ 本支只照收，不裁）

  ・一家可能同時有 cr（合併）與 ir（個別）等多個檔 ⇒ 取 cr，沒有才取其他；report 欄記取了哪一種、alt 記其餘
  ・損益表【沒有研發費用這一列】的公司（約 22%）⇒ rd 空白，⛔ 不填 0；要不要當 0 由登錄方定
  ・只解 ci（一般業）檔；金融保險等業別本來就沒有研發費用列
"""
import argparse
import csv
import io
import os
import re
import sys
import time
import urllib.request
import zipfile

import runlog

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(ROOT, "data", "mops", "rd_hist")
STATUS = os.path.join(ROOT, "data", "mops", "_rd_status.csv")
URL = "https://mopsov.twse.com.tw/server-java/FileDownLoad?step=9&filePath=/home/html/nas/ifrs/{y}/&fileName=tifrs-{y}Q{q}.zip"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
HEADER = ["stock_id", "period", "report", "alt", "taxonomy", "rd_q", "rd_ytd", "rev_q", "rev_ytd"]
STATUS_HEADER = ["period", "status", "zip_bytes", "files", "ci_files", "companies", "with_rd", "with_rev", "note", "asof"]
RD = {"ResearchAndDevelopmentExpenses", "ResearchAndDevelopmentExpense"}
REV = {"OperatingRevenue", "Revenue"}
QSTART = {1: "0101", 2: "0401", 3: "0701", 4: "1001"}
QEND = {1: "0331", 2: "0630", 3: "0930", 4: "1231"}
FNAME = re.compile(r"tifrs-(fr\d+)-(m\d+)-(\w+)-(\w+)-([0-9A-Z]+)-(\d{4})Q(\d)\.(xml|html?)$")


def periods(start, end):
    y, q = int(start[:4]), int(start[-1])
    while (y, q) <= (int(end[:4]), int(end[-1])):
        yield y, q
        y, q = (y + 1, 1) if q == 4 else (y, q + 1)


def _num(txt):
    t = "".join(str(txt).split()).replace(",", "")
    if t in ("", "-", "—"):
        return None
    try:
        return float(t)
    except ValueError:
        return None


def facts(text, y, q):
    """→ {"rd_q","rd_ytd","rev_q","rev_ytd"}（元；取不到的鍵不放）。只收本期 context。"""
    end, qs, ys = f"{y}{QEND[q]}", f"{y}{QSTART[q]}", f"{y}0101"
    out = {}

    def put(kind, ctx, val):
        m = re.search(r"From(\d{8})To(\d{8})", ctx or "")
        if val is None or not m or m.group(2) != end:
            return
        if m.group(1) == qs:
            out.setdefault(kind + "_q", val)
        if m.group(1) == ys:
            out.setdefault(kind + "_ytd", val)

    # inline XBRL：<ix:nonFraction name="ifrs-full:Revenue" contextRef=... scale="3" sign="-">1,234</ix:nonFraction>
    for m in re.finditer(r"<ix:nonFraction\b([^>]*)>(.*?)</ix:nonFraction>", text, re.S | re.I):
        attrs, inner = m.group(1), re.sub(r"<[^>]+>", "", m.group(2))
        nm = re.search(r'\bname="[\w\-]+:([\w\-]+)"', attrs)
        if not nm or (nm.group(1) not in RD and nm.group(1) not in REV):
            continue
        v = _num(inner)
        if v is not None:
            sc = re.search(r'\bscale="(-?\d+)"', attrs)
            v *= 10 ** int(sc.group(1)) if sc else 1
            if re.search(r'\bsign="-"', attrs):
                v = -v
        ctx = re.search(r'\bcontextRef="([^"]+)"', attrs)
        put("rd" if nm.group(1) in RD else "rev", ctx.group(1) if ctx else "", v)
    # XBRL instance：<tifrs-bsci-ci:OperatingRevenue contextRef="From..To.." decimals="-3" ...>288641316000</...>
    for m in re.finditer(r"<([\w\-]+):([\w\-]+)\b([^>]*)>([^<]*)</\1:\2>", text):
        if m.group(1) in ("ix", "xbrli", "link", "xbrldi"):
            continue
        if m.group(2) not in RD and m.group(2) not in REV:
            continue
        ctx = re.search(r'\bcontextRef="([^"]+)"', m.group(3))
        put("rd" if m.group(2) in RD else "rev", ctx.group(1) if ctx else "", _num(m.group(4)))
    return out


def parse_zip(zf, y, q):
    """→ (rows, stats)。一家一列：cr 優先。"""
    per = f"{y}Q{q}"
    by = {}
    files = ci = 0
    for name in zf.namelist():
        files += 1
        m = FNAME.search(os.path.basename(name))
        if not m or m.group(3) != "ci" or f"{m.group(6)}Q{m.group(7)}" != per:
            continue
        ci += 1
        by.setdefault(m.group(5), []).append((m.group(4), m.group(1), name))
    rows = []
    for sid in sorted(by):
        cands = sorted(by[sid], key=lambda c: (c[0] != "cr", c[0]))
        rep, tax, name = cands[0]
        f = facts(zf.read(name).decode("utf-8", "replace"), y, q)

        def g(k):
            return "" if k not in f else ("%.0f" % f[k])
        rows.append([sid, per, rep, "|".join(c[0] for c in cands[1:]), tax,
                     g("rd_q"), g("rd_ytd"), g("rev_q"), g("rev_ytd")])
    st = {"files": files, "ci_files": ci, "companies": len(rows),
          "with_rd": sum(1 for r in rows if r[6] or r[5]), "with_rev": sum(1 for r in rows if r[8] or r[7])}
    return rows, st


def download(y, q, dest, tries=3, wait=60):
    """→ (ok, note)。⛔ 判定看 zip 檔頭，不看狀態碼（不存在的季回 200＋忙碌頁）。"""
    last = ""
    for i in range(tries):
        req = urllib.request.Request(URL.format(y=y, q=q), headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=600) as r, open(dest, "wb") as f:
                ctype = r.headers.get("Content-Type", "")
                while True:
                    b = r.read(1 << 20)
                    if not b:
                        break
                    f.write(b)
            with open(dest, "rb") as f:
                head = f.read(4096)
            if head[:2] == b"PK":
                return True, f"{os.path.getsize(dest)} bytes"
            last = f"不是 zip（{ctype}）：{head.decode('big5', 'replace')[:200]}"
        except Exception as e:                       # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
        if i + 1 < tries:
            time.sleep(wait)
    return False, last


def _status():
    if not os.path.exists(STATUS):
        return {}
    with io.open(STATUS, encoding="utf-8") as f:
        return {r["period"]: r for r in csv.DictReader(f)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2013Q1")
    ap.add_argument("--end", default="2026Q2")
    ap.add_argument("--sleep", type=float, default=20)
    ap.add_argument("--zip-dir", default="", help="本機已下載的 zip（測試用，⛔ Actions 不用）")
    ap.add_argument("--redo", action="store_true", help="已完成的季也重做")
    a = ap.parse_args()
    rl = runlog.Run("xbrl_rd")
    stat = _status()
    os.makedirs(OUT_DIR, exist_ok=True)
    done = fail = 0
    fails, summary = [], []
    tmp = os.path.join(os.environ.get("RUNNER_TEMP", "/tmp"), "xbrl_rd.zip")
    for y, q in periods(a.start, a.end):
        per = f"{y}Q{q}"
        if not a.redo and stat.get(per, {}).get("status") == "ok":
            continue
        if a.zip_dir:
            src = os.path.join(a.zip_dir, f"tifrs-{per}.zip")
            ok, note = os.path.exists(src), "本機樣本"
        else:
            ok, note = download(y, q, tmp)
            src = tmp
            time.sleep(a.sleep)
        row = {"period": per, "asof": time.strftime("%Y-%m-%d %H:%M:%S")}
        if not ok:
            fail += 1
            fails.append((per, note))
            row.update(status="fail", note=note)
        else:
            with zipfile.ZipFile(src) as zf:
                rows, st = parse_zip(zf, y, q)
            with io.open(os.path.join(OUT_DIR, f"{per}.csv"), "w", encoding="utf-8", newline="") as f:
                w = csv.writer(f, lineterminator="\n")
                w.writerow(HEADER)
                w.writerows(rows)
            done += 1
            row.update(status="ok", zip_bytes=str(os.path.getsize(src)), note=note, **{k: str(v) for k, v in st.items()})
            summary.append(f"{per} 公司 {st['companies']}｜研發 {st['with_rd']}｜營收 {st['with_rev']}")
            print(f"[xbrl_rd] {summary[-1]}")
        stat[per] = {k: row.get(k, "") for k in STATUS_HEADER}
        with io.open(STATUS, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=STATUS_HEADER, lineterminator="\n")
            w.writeheader()
            for k in sorted(stat):
                w.writerow(stat[k])
    rl.info("本趟", f"完成 {done} 季｜失敗 {fail} 季")
    for s in summary:
        rl.info("季", s)
    if fails:
        rl.info("失敗的季", str(fails))
    rl.check("沒有失敗的季（⛔ 不存在的季也算失敗：請把 end 設在最新已公布季）", not fails, str(fails))
    rl.check("每一季都有公司列出研發費用（全季 0 ＝ 元素名稱換了）",
             all(int(r.get("with_rd") or 0) > 0 for r in stat.values() if r.get("status") == "ok"),
             str([p for p, r in stat.items() if r.get("status") == "ok" and int(r.get("with_rd") or 0) == 0]))
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
