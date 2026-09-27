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
from backfill import visible_text

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


# ⭐ 2026-09-27（回測 1449、裁定 1457：fs_hist 幾乎沒有已下市公司 ⇒ 大師三套倖存者偏誤）
#   ⇒ 同一份 XBRL 另解財報主要欄位（全產業、含當時還在、之後下市的公司）⇒ data/mops/fin_hist
#   local name 兩代（2013Q2／2020Q4 實測 2330、2801、2882、2888、6005）：資產負債與淨利、EPS 名稱一致（前綴 ifrs → ifrs-full）；
#   營業利益 NetOperatingIncomeLoss（XML 世代）→ ProfitLossFromOperatingActivities；營收 OperatingRevenue → Revenue
KINDS = {"rd": RD, "rev": REV,
         "opi": {"NetOperatingIncomeLoss", "ProfitLossFromOperatingActivities", "OperatingIncomeLoss"},
         "ni": {"ProfitLoss"}, "nip": {"ProfitLossAttributableToOwnersOfParent"},
         "eps": {"BasicEarningsLossPerShare"},
         "assets": {"Assets"}, "liab": {"Liabilities"},
         "eqp": {"EquityAttributableToOwnersOfParent"}, "eq": {"Equity"}}
INSTANT = {"assets", "liab", "eqp", "eq"}          # 時點（AsOf<季底>）；其餘是期間（From..To..）
KIND_OF = {n: k for k, ns in KINDS.items() for n in ns}
FIN_DIR = os.path.join(ROOT, "data", "mops", "fin_hist")
FIN_HEADER = ["stock_id", "period", "industry", "report", "alt", "taxonomy",
              "rev_q", "rev_ytd", "opi_q", "opi_ytd", "ni_q", "ni_ytd", "nip_q", "nip_ytd", "eps_q", "eps_ytd",
              "assets", "liabilities", "equity_parent", "equity_total", "rd_q", "rd_ytd"]


def facts(text, y, q):
    """→ {"rd_q","rd_ytd","rev_q",…,"assets",…}（元；EPS 元／股；取不到的鍵不放）。只收本期 context。"""
    end, qs, ys = f"{y}{QEND[q]}", f"{y}{QSTART[q]}", f"{y}0101"
    out = {}

    def put(kind, ctx, val):
        if val is None:
            return
        if kind in INSTANT:
            if (ctx or "") == f"AsOf{end}":
                out.setdefault(kind, val)
            return
        m = re.search(r"From(\d{8})To(\d{8})", ctx or "")
        if not m or m.group(2) != end:
            return
        if m.group(1) == qs:
            out.setdefault(kind + "_q", val)
        if m.group(1) == ys:
            out.setdefault(kind + "_ytd", val)

    # inline XBRL：<ix:nonFraction name="ifrs-full:Revenue" contextRef=... scale="3" sign="-">1,234</ix:nonFraction>
    for m in re.finditer(r"<ix:nonFraction\b([^>]*)>(.*?)</ix:nonFraction>", text, re.S | re.I):
        attrs = m.group(1)
        nm = re.search(r'\bname="[\w\-]+:([\w\-]+)"', attrs)
        if not nm or nm.group(1) not in KIND_OF:
            continue
        v = _num(visible_text(m.group(2), ""))                     # 四點五：去標籤只有一份
        if v is not None:
            sc = re.search(r'\bscale="(-?\d+)"', attrs)
            v *= 10 ** int(sc.group(1)) if sc else 1
            if re.search(r'\bsign="-"', attrs):
                v = -v
        ctx = re.search(r'\bcontextRef="([^"]+)"', attrs)
        put(KIND_OF[nm.group(1)], ctx.group(1) if ctx else "", v)
    # XBRL instance：<tifrs-bsci-ci:OperatingRevenue contextRef="From..To.." decimals="-3" ...>288641316000</...>
    for m in re.finditer(r"<([\w\-]+):([\w\-]+)\b([^>]*)>([^<]*)</\1:\2>", text):
        if m.group(1) in ("ix", "xbrli", "link", "xbrldi") or m.group(2) not in KIND_OF:
            continue
        ctx = re.search(r'\bcontextRef="([^"]+)"', m.group(3))
        put(KIND_OF[m.group(2)], ctx.group(1) if ctx else "", _num(m.group(4)))
    return out


def _fmt(k, v):
    if v is None:
        return ""
    if k.startswith("eps"):
        return ("%.4f" % v).rstrip("0").rstrip(".")
    return "%.0f" % v


def parse_zip(zf, y, q):
    """→ (rd_rows, stats, fin_rows)。一家一列：cr 優先。
    rd_rows：只有 ci（一般業），格式與 2026-09-27 初版逐位元相同；fin_rows：全產業、財報主要欄位。"""
    per = f"{y}Q{q}"
    by, by_all = {}, {}
    files = ci = 0
    for name in zf.namelist():
        files += 1
        m = FNAME.search(os.path.basename(name))
        if not m or f"{m.group(6)}Q{m.group(7)}" != per:
            continue
        by_all.setdefault(m.group(5), []).append((m.group(4), m.group(1), name, m.group(3)))
        if m.group(3) != "ci":
            continue
        ci += 1
        by.setdefault(m.group(5), []).append((m.group(4), m.group(1), name))
    cache = {}

    def fx(name):
        if name not in cache:
            cache[name] = facts(zf.read(name).decode("utf-8", "replace"), y, q)
        return cache[name]
    rows = []
    for sid in sorted(by):
        cands = sorted(by[sid], key=lambda c: (c[0] != "cr", c[0]))
        rep, tax, name = cands[0]
        f = fx(name)

        def g(k):
            return "" if k not in f else ("%.0f" % f[k])
        rows.append([sid, per, rep, "|".join(c[0] for c in cands[1:]), tax,
                     g("rd_q"), g("rd_ytd"), g("rev_q"), g("rev_ytd")])
    fin = []
    for sid in sorted(by_all):
        cands = sorted(by_all[sid], key=lambda c: (c[0] != "cr", c[3] != "ci", c[0], c[3]))
        rep, tax, name, ind = cands[0]
        f = fx(name)
        fin.append([sid, per, ind, rep, "|".join(f"{c[3]}-{c[0]}" for c in cands[1:]), tax]
                   + [_fmt(k, f.get(k)) for k in ("rev_q", "rev_ytd", "opi_q", "opi_ytd", "ni_q", "ni_ytd",
                                                  "nip_q", "nip_ytd", "eps_q", "eps_ytd", "assets", "liab",
                                                  "eqp", "eq", "rd_q", "rd_ytd")])
    st = {"files": files, "ci_files": ci, "companies": len(rows),
          "with_rd": sum(1 for r in rows if r[6] or r[5]), "with_rev": sum(1 for r in rows if r[8] or r[7])}
    st["fin_companies"] = len(fin)
    st["fin_with_ni"] = sum(1 for r in fin if r[11] or r[10])
    st["fin_with_assets"] = sum(1 for r in fin if r[16])
    return rows, st, fin


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
            # ⛔ 2026-09-27 run 36255385807：2026Q1 檔頭是 PK、但【下載不完整】（沒有 Content-Length，斷線看不出來）
            #   ⇒ 解析時 BadZipFile 整支炸掉 ⇒ 驗到中央目錄（檔尾）才算數，不完整就重抓
            if head[:2] == b"PK" and zipfile.is_zipfile(dest):
                return True, f"{os.path.getsize(dest)} bytes"
            last = (f"zip 不完整（檔頭 PK、讀不到中央目錄，{os.path.getsize(dest)} bytes）" if head[:2] == b"PK"
                    else f"不是 zip（{ctype}）：{head.decode('big5', 'replace')}")
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
            try:
                with zipfile.ZipFile(src) as zf:
                    rows, st, fin = parse_zip(zf, y, q)
            except zipfile.BadZipFile as ex:        # 只記這一季失敗，⛔ 不讓整支炸掉（後面的季照做）
                ok, rows = False, None
                fail += 1
                fails.append((per, f"BadZipFile: {ex}"))
                row.update(status="fail", note=f"BadZipFile: {ex}")
        if ok:
            os.makedirs(FIN_DIR, exist_ok=True)
            for d_, h_, r_ in ((OUT_DIR, HEADER, rows), (FIN_DIR, FIN_HEADER, fin)):
                with io.open(os.path.join(d_, f"{per}.csv"), "w", encoding="utf-8", newline="") as f:
                    w = csv.writer(f, lineterminator="\n")
                    w.writerow(h_)
                    w.writerows(r_)
            done += 1
            finote = f"全產業 {st['fin_companies']} 家｜淨利 {st['fin_with_ni']}｜資產 {st['fin_with_assets']}"
            row.update(status="ok", zip_bytes=str(os.path.getsize(src)), note=f"{note}｜{finote}",
                       **{k: str(v) for k, v in st.items()})
            summary.append(f"{per} 公司 {st['companies']}｜研發 {st['with_rd']}｜營收 {st['with_rev']}｜{finote}")
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
