# -*- coding: utf-8 -*-
"""MOPS IFRS XBRL 季度整包 ⇒ 財報細項（存貨、應收、合約負債、營業現金流…）fs_xbrl_<年>.csv

    python3 curated/fs_xbrl/build.py [--from 2013Q1] [--to 2026Q2] [--cache ~/xbrl_cache] [--keep-zip]

依據：情報 1013-2340（應計異常、營業現金流與淨利背離、存貨／應收增速）；裁定 seq348 §三；本線 1015-1851 探針。
  營業成本／毛利／營業利益三欄：裁定 seq412 §四 Q-G、台股 seq533 C（2026-10-21 加）。
來源：mopsov `server-java/FileDownLoad?step=9&fileName=tifrs-<YYYYQn>.zip&filePath=/home/html/nas/ifrs/<YYYY>/`
  一季一包、全市場（上市、上櫃、興櫃、公開發行），每家一檔。2013Q1 起（2012Q4 回 HTML ＝沒有）。
  ⚠ 兩種格式：早年是純 XBRL instance（.xml，前綴 `ifrs:`＝2010 版 taxonomy，值不帶 scale）；
    後來改 inline XBRL（.html，前綴 `ifrs-full:`、值要乘 scale、負號在 sign 屬性）⇒ 兩種都讀，前綴 `ifrs:` 一律視同 `ifrs-full:`。
  ⚠ 合約負債是 IFRS 15（2018 起）才有的科目 ⇒ 2017 以前空白是正常的。
  ⚠ 直接打 `/nas/ifrs/...zip` 回 403；要走 FileDownLoad。每包約 77 MB，每發間隔 5 秒、一般 UA。

抽法（⛔ 數值原樣，只乘 scale、套 sign，不推算）：
  只收 <ix:nonFraction>，name 在 ITEMS 裡、contextRef 是本期：
    存量科目 AsOf<期末日>；流量科目 From<會計年度起日>To<期末日>（⚠ 現金流量表是【年初至今累計】，Q2＝上半年）
  同一家同一季有合併（-cr-）與個體（-ir-）⇒ 取合併；有 fr1／fr0／fr2 ⇒ 依序取。
  一家一季一列；某科目該家沒有揭露 ⇒ 空白（⛔ 不是 0）。
⛔ 這不是公告日：可用日要另對 doc.twse t57sb01 上傳時戳（到秒），⛔ 不可用期末日（前視）。
"""
import argparse, collections, csv, io, os, re, subprocess, sys, time, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
URL = "https://mopsov.twse.com.tw/server-java/FileDownLoad?step=9&fileName=tifrs-{q}.zip&filePath=/home/html/nas/ifrs/{y}/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
# (欄名, 類型 S＝存量／F＝流量, 候選 XBRL 名稱（依序取第一個有值的）)
ITEMS = [
    ("inventories", "S", ["ifrs-full:Inventories"]),
    ("accounts_receivable", "S", ["tifrs-bsci-ci:AccountsReceivableNet", "ifrs-full:CurrentTradeReceivables"]),
    ("accounts_receivable_related", "S", ["tifrs-bsci-ci:AccountsReceivableDuefromRelatedPartiesNet"]),
    ("notes_receivable", "S", ["tifrs-bsci-ci:NotesReceivableNet"]),
    ("contract_liabilities_current", "S", ["ifrs-full:CurrentContractLiabilities"]),
    ("contract_liabilities_noncurrent", "S", ["ifrs-full:NoncurrentContractLiabilities"]),
    ("cash", "S", ["ifrs-full:CashAndCashEquivalents"]),
    ("total_assets", "S", ["ifrs-full:Assets"]),
    ("total_equity", "S", ["ifrs-full:Equity"]),
    ("revenue_ytd", "F", ["ifrs-full:Revenue", "tifrs-bsci-ci:OperatingRevenue",
                          "tifrs-bsci-bd:TotalRevenue"]),   # bd 證券 2017 以前的收益合計（2018 起 bd 改用 ifrs-full:Revenue）
    ("profit_before_tax_ytd", "F", ["ifrs-full:ProfitLossBeforeTax"]),
    ("net_income_ytd", "F", ["ifrs-full:ProfitLoss"]),
    ("operating_cash_flow_ytd", "F", ["ifrs-full:CashFlowsFromUsedInOperatingActivities"]),
    ("depreciation_ytd", "F", ["ifrs-full:AdjustmentsForDepreciationExpense", "tifrs-SCF:DepreciationExpense"]),
    ("capex_ytd", "F", ["ifrs-full:PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",
                        "tifrs-SCF:AcquisitionOfPropertyPlantAndEquipment"]),
    # 營業成本／營業毛利（毛損）淨額／營業利益（裁定 seq412 §四 Q-G、台股 seq533 C）
    #   ⚠ 毛利取【淨額】＝營業毛利 −未實現 ＋已實現銷貨損益（新版 ifrs-full:GrossProfit、舊版 …Net）；
    #     tifrs-bsci-ci:GrossProfitLossFromOperations 是未扣未實現前的毛利 ⇒ ⛔ 不收，免得兩種口徑混用。
    #   ⚠ 成本只收 OperatingCosts（營業成本合計）；ifrs-full:CostOfSales 在台灣範本是子項（銷貨成本）⇒ ⛔ 不當備援。
    ("cost_of_sales_ytd", "F", ["tifrs-bsci-ci:OperatingCosts"]),
    ("gross_profit_ytd", "F", ["ifrs-full:GrossProfit", "tifrs-bsci-ci:GrossProfitLossFromOperationsNet"]),
    ("operating_income_ytd", "F", ["ifrs-full:ProfitLossFromOperatingActivities", "tifrs-bsci-ci:NetOperatingIncomeLoss",
                                   "tifrs-bsci-bd:NetOperatingIncomeLoss"]),   # bd 證券 2017 以前（2018 起 bd 改用 ifrs-full）
]
HEADER = ["period", "stock_id", "industry_template", "report", "period_end"] + [c for c, _, _ in ITEMS] + ["source_file"]
QEND = {1: "0331", 2: "0630", 3: "0930", 4: "1231"}
TAG = re.compile(r"<ix:nonFraction\b([^>]*)>(.*?)</ix:nonFraction>", re.S)
ATTR = re.compile(r'(\w[\w:-]*)="([^"]*)"')
FNAME = re.compile(r"tifrs-(fr\d)-m\d-(\w+?)-(cr|ir)-([0-9A-Z]{4,6})-(\d{4})Q(\d)\.(html|xml)$")
XEL = re.compile(r"<([\w\-]+):(\w+)\b([^>]*)>([^<]*)</\1:\2>")


def quarters(a, b):
    y, q = int(a[:4]), int(a[-1])
    while (y, q) <= (int(b[:4]), int(b[-1])):
        yield "%dQ%d" % (y, q)
        q += 1
        if q == 5:
            y, q = y + 1, 1


def fetch(q, cache):
    os.makedirs(cache, exist_ok=True)
    p = os.path.join(cache, "tifrs-%s.zip" % q)
    if os.path.exists(p) and zipfile.is_zipfile(p):
        return p
    time.sleep(5)
    rc = subprocess.run(["curl", "-s", "-L", "-A", UA, "--max-time", "900", "-o", p + ".part",
                         URL.format(q=q, y=q[:4])]).returncode
    if rc != 0 or not zipfile.is_zipfile(p + ".part"):
        head = open(p + ".part", "rb").read(60) if os.path.exists(p + ".part") else b""
        print("  ⛔ %s 不是 zip（rc=%s，開頭 %r）⇒ 這季跳過" % (q, rc, head[:40]))
        return None
    os.replace(p + ".part", p)
    return p


def num(raw, attrs):
    s = re.sub(r"<[^>]+>", "", raw).replace(",", "").strip()
    if s in ("", "-"):
        return ""
    try:
        v = float(s) * (10 ** int(attrs.get("scale", "0") or 0))
    except ValueError:
        return ""
    if attrs.get("sign") == "-":
        v = -v
    return str(int(v)) if v == int(v) else repr(v)


def parse(html, y, qn):
    end = "%d%s" % (y, QEND[qn])
    ctx_s, ctx_f = "AsOf" + end, "From%d0101To%s" % (y, end)
    vals = {}
    if "<ix:nonFraction" in html:
        facts = ((dict(ATTR.findall(a_s)), raw) for a_s, raw in TAG.findall(html))
        facts = ((a.get("name", ""), a, raw) for a, raw in facts)
    else:   # 純 XBRL instance：<prefix:Name contextRef=.. decimals=..>值</prefix:Name>
        facts = (("%s:%s" % (p, n), dict(ATTR.findall(a_s)), raw) for p, n, a_s, raw in XEL.findall(html))
    for nm, a, raw in facts:
        if nm.startswith("ifrs:"):
            nm = "ifrs-full:" + nm[5:]
        cx = a.get("contextRef", "")
        if cx not in (ctx_s, ctx_f) or (nm, cx) in vals:
            continue
        vals[(nm, cx)] = num(raw, a)
    row = {}
    for col, kind, names in ITEMS:
        cx = ctx_s if kind == "S" else ctx_f
        row[col] = next((vals[(n, cx)] for n in names if vals.get((n, cx), "") != ""), "")
    return row, "%d-%s-%s" % (y, QEND[qn][:2], QEND[qn][2:])


def build_quarter(path, q):
    z = zipfile.ZipFile(path)
    pick = {}
    for n in z.namelist():
        m = FNAME.search(n)
        if not m:
            continue
        fr, tmpl, rep, sid, y, qn, _ext = m.groups()
        rank = (0 if rep == "cr" else 1, {"fr1": 0, "fr0": 1}.get(fr, 2))
        if sid not in pick or rank < pick[sid][0]:
            pick[sid] = (rank, n, tmpl, rep)
    out = []
    for sid, (_, n, tmpl, rep) in sorted(pick.items()):
        row, pe = parse(z.read(n).decode("utf-8", "replace"), int(q[:4]), int(q[-1]))
        row.update(period=q, stock_id=sid, industry_template=tmpl, report=rep, period_end=pe, source_file=n)
        out.append(row)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="a", default="2013Q1")
    ap.add_argument("--to", dest="b", default="2026Q2")
    ap.add_argument("--cache", default=os.path.expanduser("~/xbrl_cache"))
    ap.add_argument("--keep-zip", action="store_true")
    a = ap.parse_args()
    by_year = collections.defaultdict(list)
    for f in sorted(os.listdir(HERE)):          # 已建好的年份檔先讀回（可分批續跑）
        m = re.match(r"fs_xbrl_(\d{4})\.csv$", f)
        if m:
            by_year[m.group(1)] = list(csv.DictReader(io.open(os.path.join(HERE, f), encoding="utf-8")))
    for q in quarters(a.a, a.b):
        p = fetch(q, a.cache)
        if not p:
            continue
        rows = build_quarter(p, q)
        y = q[:4]
        by_year[y] = [r for r in by_year[y] if r["period"] != q] + rows
        cov = {c: sum(1 for r in rows if r[c] != "") for c, _, _ in ITEMS}
        print("%s｜%d 家｜存貨 %d、應收 %d、合約負債 %d、營業現金流 %d、稅前 %d、成本 %d、毛利 %d、營業利益 %d" % (
            q, len(rows), cov["inventories"], cov["accounts_receivable"], cov["contract_liabilities_current"],
            cov["operating_cash_flow_ytd"], cov["profit_before_tax_ytd"], cov["cost_of_sales_ytd"],
            cov["gross_profit_ytd"], cov["operating_income_ytd"]), flush=True)
        with io.open(os.path.join(HERE, "fs_xbrl_%s.csv" % y), "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, HEADER, lineterminator="\n")
            w.writeheader()
            for r in sorted(by_year[y], key=lambda r: (r["period"], r["stock_id"])):
                w.writerow({k: r.get(k, "") for k in HEADER})
        if not a.keep_zip:
            os.remove(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
