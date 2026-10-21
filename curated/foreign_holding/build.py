# -*- coding: utf-8 -*-
"""外資及陸資持股統計【月表】（每月最後一個交易日一發）⇒ foreign_holding_<年>.csv（補 2012 年前法人缺口）

    python3 curated/foreign_holding/build.py [--ref origin/main] [--start 2004-02] [--end 2012-12] [--check]

依據：台股 seq533 §二 A（資料庫線子代理 2026-10-21 探針後建檔）。
來源（皆官方）：
  上市 TWSE `https://www.twse.com.tw/rwd/zh/fund/MI_QFIIS?date=YYYYMMDD&selectType=ALLBUT0999&response=json`
       官方下限 2004-02-11（20040210 大聲回 stat「查詢日期小於93年02月11日」）。
       ⛔ selectType 一定要 ALLBUT0999（不帶回 8 列、ALL 回 0 列，都是 stat OK）。
  上櫃 TPEx `https://www.tpex.org.tw/www/zh-tw/insti/qfii?date=YYYY/MM/DD&response=json`（頁面「僑外資及陸資持股比例排行表」）
       實測最早 2007-05-02（2007-04-30 以前 stat ok＋0 列；頁面 data-start=20070101 不準）。
  ⚠ 上櫃 2004-08-04～2007-04 另有 MOPS `mopsov.twse.com.tw/server-java/t13sa150_otc`（POST years/months/days/bcode=/step=2），
     但它【不是全名單】（2008-05-30：429 檔 vs TPEx 546 檔，少的 117 檔有 106 檔外資持股 > 0），且同檔數值約 1.5% 與 TPEx 不同
     ⇒ ⛔ 本檔不收，只記在 README。
取日：每月最後一個交易日（上市日曆：origin/main `data/early/daily/` 檔名＋`data/meta/calendar_twse.csv`）；上櫃用同一天。
輸出欄：date, market, stock_id, name, isin, issued_shares, foreign_avail_shares, foreign_shares,
        foreign_avail_pct, foreign_pct, limit_pct, china_limit_pct, change_reason, last_report_date
  數字去千分位與 %；股數單位＝股、比率單位＝%。官方沒有的欄留空（上櫃無 isin／change_reason；2010 前無 china_limit_pct）。
守門（每發）：① 回應自己講的日期＝請求日（防參數回音／靜默回今天）② 欄位用名稱定位，對不上整批拒收 ③ 0 列＝失敗
  ④ 全部月份的資料指紋（md5）不得重複。
限制：
  - 月底快照，⛔ 不是逐日；月中異動看不到。
  - 欄名有年代差：2009 前「外資…」、之後「外資及陸資…」；2010 起多「陸資法令投資上限比率」。持股口徑隨法規改變，跨年比較自行注意。
  - limit_pct 早年上市大量是 0.00（官方原值，⛔ 不等於「不可投資」），原樣保留。
  - 母體含 ETF、受益憑證、TDR 等非普通股，使用時自行篩。
  - 可用日：官方當日盤後公布 ⇒ 該日收盤後可用。
"""
import argparse, csv, hashlib, io, json, os, re, subprocess, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
CACHE = os.path.expanduser("~/.cache/foreign_holding")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
TWSE = "https://www.twse.com.tw/rwd/zh/fund/MI_QFIIS?date={ymd}&selectType=ALLBUT0999&response=json"
TPEX = "https://www.tpex.org.tw/www/zh-tw/insti/qfii?date={slash}&response=json"
TPEX_FIRST = "2007-05"
FM = "https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockShareholding&data_id={sid}&start_date={d}&end_date={d}"
COLS = ["date", "market", "stock_id", "name", "isin", "issued_shares", "foreign_avail_shares", "foreign_shares",
        "foreign_avail_pct", "foreign_pct", "limit_pct", "china_limit_pct", "change_reason", "last_report_date"]


def git(ref, *a):
    return subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, text=True).stdout


def month_ends(ref, start, end):
    days = [os.path.basename(f)[:10] for f in git(ref, "ls-tree", "--name-only", ref, "data/early/daily/").split()
            if f.endswith(".csv")]
    days += [r["date"] for r in csv.DictReader(io.StringIO(git(ref, "show", f"{ref}:data/meta/calendar_twse.csv")))]
    last = {}
    for d in sorted(set(days)):
        last[d[:7]] = d
    return [last[m] for m in sorted(last) if start <= m <= end]


def fetch(url, key, sleep):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, key + ".json")
    if os.path.exists(p):
        return open(p, "rb").read()
    time.sleep(sleep)
    for i in range(3):
        try:
            b = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90).read()
            json.loads(b)            # ⛔ 不是 JSON（CDN 擋阻頁 HTML）⇒ 不快取、直接停
            open(p, "wb").write(b)
            return b
        except urllib.error.HTTPError as e:
            if e.code in (403, 428, 429):
                sys.exit(f"⛔ HTTP {e.code}：{url} ⇒ 被擋，停（不繞過）")
            print(f"  重試 {i}：{e}"); time.sleep(30)
        except ValueError:
            sys.exit(f"⛔ 回的不是 JSON（多半是擋阻頁）：{url}")
        except Exception as e:  # noqa: BLE001
            print(f"  重試 {i}：{e}"); time.sleep(30)
    return None


def num(s):
    s = str(s).replace(",", "").replace("%", "").replace("\xa0", "").strip()
    return s


def pick(fields, *pat, exclude=None):
    for i, f in enumerate(fields):
        if all(p in f for p in pat) and not (exclude and exclude in f):
            return i
    return None


def parse_twse(b, day):
    d = json.loads(b)
    if str(d.get("stat", "")).upper() != "OK":
        raise RuntimeError(f"stat={d.get('stat')!r}")
    ymd = day.replace("-", "")
    roc = "%d年%s月%s日" % (int(day[:4]) - 1911, day[5:7], day[8:10])
    if d.get("date") != ymd or roc not in str(d.get("title", "")):
        raise RuntimeError(f"⛔ 回應日期不符：date={d.get('date')!r} title={d.get('title')!r}")
    f = [str(x) for x in d.get("fields") or []]
    ix = dict(sid=pick(f, "代號"), name=pick(f, "名稱"), isin=pick(f, "國際證券編碼"), iss=pick(f, "發行股數"),
              avs=pick(f, "尚可投資股數"), fs=pick(f, "持有股數"), avp=pick(f, "尚可投資比率"), fp=pick(f, "持股比率"),
              lim=pick(f, "法令投資上限比率", exclude="陸資法令"), clim=pick(f, "陸資法令投資上限比率"),
              rsn=pick(f, "異動原因"), rpt=pick(f, "異動日期"))
    need = ["sid", "name", "iss", "fs", "fp", "lim"]
    if any(ix[k] is None for k in need):
        raise RuntimeError(f"⛔ 欄位對不上：{f}")
    out = []
    for r in d.get("data") or []:
        g = lambda k: (str(r[ix[k]]).strip() if ix[k] is not None else "")
        rpt = g("rpt")
        out.append([day, "twse", g("sid"), g("name"), g("isin"), num(g("iss")), num(g("avs")), num(g("fs")),
                    num(g("avp")), num(g("fp")), num(g("lim")), num(g("clim")), g("rsn"), "" if rpt in ("0", "") else rpt])
    return out, d.get("data")


def parse_tpex(b, day):
    d = json.loads(b)
    if str(d.get("stat", "")).upper() != "OK":
        raise RuntimeError(f"stat={d.get('stat')!r}")
    if d.get("date") != day.replace("-", ""):
        raise RuntimeError(f"⛔ 回應日期不符：date={d.get('date')!r}")
    t = (d.get("tables") or [{}])[0]
    f = [str(x) for x in t.get("fields") or []]
    ix = dict(sid=pick(f, "代號"), name=pick(f, "名稱"), iss=pick(f, "發行股數"), avs=pick(f, "尚可投資股數"),
              fs=pick(f, "持有股數"), avp=pick(f, "尚可投資比率"), fp=pick(f, "持股比率"), lim=pick(f, "法令投資上限比率"),
              note=pick(f, "備註"))
    if any(ix[k] is None for k in ("sid", "name", "iss", "fs", "fp", "lim")):
        raise RuntimeError(f"⛔ 欄位對不上：{f}")
    out = []
    for r in t.get("data") or []:
        g = lambda k: (str(r[ix[k]]).strip() if ix[k] is not None else "")
        out.append([day, "tpex", g("sid"), g("name"), "", num(g("iss")), num(g("avs")), num(g("fs")),
                    num(g("avp")), num(g("fp")), num(g("lim")), "", g("note"), ""])
    return out, t.get("data")


def check_finmind(rows, sleep):
    """抽 3 個月 × 上市 4 檔＋上櫃 2 檔＋已下市 4 檔（1204 津津、1520 復盛、2326 亞瑟、3069 寶晟科），比對 FinMind TaiwanStockShareholding（第三方）的持有股數與發行股數。"""
    by = {(r[0], r[2]): r for r in rows}
    dates = sorted({r[0] for r in rows})
    want = [d for d in dates if d[:7] in ("2005-06", "2009-12", "2012-12")]
    res = []
    for d in want:
        for sid in ("2330", "2317", "1101", "2603", "5347", "8069", "1204", "1520", "2326", "3069"):  # 後四檔已下市
            if (d, sid) not in by:
                continue
            time.sleep(sleep)
            try:
                j = json.loads(urllib.request.urlopen(urllib.request.Request(FM.format(sid=sid, d=d), headers=UA), timeout=60).read())
            except Exception as e:  # noqa: BLE001
                res.append((d, sid, "FinMind 失敗", str(e)[:60])); continue
            x = (j.get("data") or [None])[0]
            if not x:
                res.append((d, sid, "FinMind 無列", "")); continue
            me = by[(d, sid)]
            ok = str(x["ForeignInvestmentShares"]) == me[7] and str(x["NumberOfSharesIssued"]) == me[5]
            res.append((d, sid, me[1], me[3], "✓" if ok else f"✗ 我 {me[7]}/{me[5]} FM {x['ForeignInvestmentShares']}/{x['NumberOfSharesIssued']}"))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="origin/main")
    ap.add_argument("--start", default="2004-02")
    ap.add_argument("--end", default="2012-12")
    ap.add_argument("--sleep-twse", type=float, default=4.5)
    ap.add_argument("--sleep-tpex", type=float, default=3.5)
    ap.add_argument("--check", action="store_true", help="抽樣比對 FinMind")
    a = ap.parse_args()
    days = month_ends(a.ref, a.start, a.end)
    print(f"月底交易日 {len(days)} 天：{days[0]} ~ {days[-1]}")
    rows, prints, fails = [], {}, []
    for day in days:
        jobs = [("twse", TWSE.format(ymd=day.replace("-", "")), a.sleep_twse, parse_twse)]
        if day[:7] >= TPEX_FIRST:
            jobs.append(("tpex", TPEX.format(slash=day.replace("-", "/")), a.sleep_tpex, parse_tpex))
        for mk, url, sl, fn in jobs:
            b = fetch(url, f"{mk}_{day}", sl)
            try:
                if b is None:
                    raise RuntimeError("抓不到")
                out, raw = fn(b, day)
                if not out:
                    raise RuntimeError("0 列")
            except RuntimeError as e:
                fails.append((day, mk, str(e))); print(f"  ✗ {day} {mk}：{e}"); continue
            h = hashlib.md5(json.dumps(raw, ensure_ascii=False).encode()).hexdigest()
            if h in prints:
                fails.append((day, mk, f"⛔ 指紋與 {prints[h]} 相同")); print(f"  ✗ {day} {mk} 指紋重複 {prints[h]}"); continue
            prints[h] = f"{mk} {day}"
            rows.extend(out)
            print(f"  {day} {mk} {len(out)} 列")
    if fails:
        print(f"⛔ 失敗 {len(fails)}：{fails[:10]} ⇒ 不寫檔"); return 1
    years = {}
    for r in rows:
        years.setdefault(r[0][:4], []).append(r)
    for y, rs in sorted(years.items()):
        with io.open(os.path.join(HERE, f"foreign_holding_{y}.csv"), "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f); w.writerow(COLS); w.writerows(sorted(rs, key=lambda r: (r[0], r[1], r[2])))
    # 統計：家數、含下市幾家（不在現行 stocks.csv 的代號）
    known = {r["stock_id"] for r in csv.DictReader(io.StringIO(git(a.ref, "show", f"{a.ref}:data/meta/stocks.csv")))}
    for mk in ("twse", "tpex"):
        ids = {r[2] for r in rows if r[1] == mk}
        if not ids:
            continue
        gone = ids - known
        four = {i for i in gone if re.fullmatch(r"\d{4}", i)}
        print(f"⭐ {mk}：{sum(1 for r in rows if r[1] == mk)} 列、{len(ids)} 代號；不在現行 stocks.csv {len(gone)}（其中 4 碼數字 {len(four)}）")
    print(f"⭐ 總計 {len(rows)} 列、{len(prints)} 發、指紋全不重複")
    if a.check:
        for x in check_finmind(rows, 3):
            print("  FinMind 比對", x)
    return 0


if __name__ == "__main__":
    sys.exit(main())
