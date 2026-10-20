# -*- coding: utf-8 -*-
"""2015 年後已下市（停止交易）普通股的月營收 ⇒ revenue_delisted.csv（補 revenue_hist 的存活者偏差）

    python3 curated/revenue_delisted/build.py [--ref origin/main] [--sleep 3]

依據：裁定 seq406 §三、回測 1020-2209、台股 1020-2333：`data/mops/revenue_hist`（MOPS 靜態彙總頁）2015 後**一家已下市公司都沒有**
  ——那些頁是用「產生當下的公司清單」重繪的（_db_status D1；2026-10-20 再驗：無尾碼頁 t21sc03_<年>_<月>.html 也一樣），⛔ 官方路補不回來。
來源：FinMind `TaiwanStockMonthRevenue`（data_id＝代號，一檔一發；免費額度內）。⚠ 第三方，⛔ 不是官方。
母體：公開庫 `data/meta/stocks.csv` 的 kind=stock 且 last_seen 早於建置日前 20 天（＝真的停止交易；⭐ 市場轉換的代號 last_seen 會延續，不在內）。
輸出欄：stock_id, name, market, period(YYYY-MM), revenue_k（千元，與 MOPS 同單位；FinMind 原值是元 ÷1000）, finmind_date（FinMind 的 date 欄）, last_seen
⛔ 驗收（不過就不寫）：拿 12 檔仍上市、跨多年的公司，FinMind 與 revenue_hist 同期 當月營收 逐月比對，相符率 ≥ 99%（容許千元四捨五入 ±1）。
⚠ 可用日：FinMind 不給逐家申報時點 ⇒ 照全線口徑用「次月 10 日（2026-01 期起次月 15 日）之後」，⛔ 不可用期末日。
"""
import argparse, csv, datetime, io, json, os, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(HERE, "revenue_delisted.csv")
API = "https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockMonthRevenue&data_id={sid}&start_date=2014-01-01&end_date={end}"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
CHECK = ["1101", "2330", "2317", "1216", "2412", "3008", "6505", "2603", "8069", "6488", "3105", "5347"]


def git(ref, path):
    return subprocess.run(["git", "-C", REPO, "show", f"{ref}:{path}"], capture_output=True, text=True).stdout


def finmind(sid, sleep):
    time.sleep(sleep)
    u = API.format(sid=sid, end=datetime.date.today().isoformat())
    for i in range(3):
        try:
            d = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read())
            if d.get("msg") != "success":
                raise RuntimeError(d.get("msg"))
            return d.get("data") or []
        except Exception as e:  # noqa: BLE001
            print(f"  {sid} 重試 {i}：{e}")
            time.sleep(30)
    return None


def period_of(r):
    return "%04d-%02d" % (int(r["revenue_year"]), int(r["revenue_month"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="origin/main")
    ap.add_argument("--sleep", type=float, default=3)
    a = ap.parse_args()
    # ── 驗收：仍上市公司 FinMind vs revenue_hist
    hist = {}
    files = subprocess.run(["git", "-C", REPO, "ls-tree", "--name-only", a.ref, "data/mops/revenue_hist/"],
                           capture_output=True, text=True).stdout.split()
    for f in files:
        b = os.path.basename(f)
        if not (b.endswith("_twse.csv") or b.endswith("_tpex.csv")):
            continue
        for r in csv.DictReader(io.StringIO(git(a.ref, f))):
            if r["stock_id"] in CHECK:
                hist[(r["stock_id"], r["period"])] = r["當月營收"]
    n = ok = 0
    bad = []
    for sid in CHECK:
        rows = finmind(sid, a.sleep) or []
        for r in rows:
            k = (sid, period_of(r))
            if k in hist and hist[k] not in ("", None):
                n += 1
                mine = round(float(r["revenue"]) / 1000)
                if abs(mine - float(hist[k])) <= 1:
                    ok += 1
                elif len(bad) < 8:
                    bad.append((k, mine, hist[k]))
    rate = ok / n if n else 0
    print(f"⭐ 驗收：仍上市 {len(CHECK)} 檔、重疊 {n} 期，相符 {ok}（{rate:.2%}）｜例外 {bad}")
    if rate < 0.99:
        print("⛔ 相符率 < 99%，不寫檔"); return 1
    # ── 母體：停止交易的普通股
    cut = (datetime.date.today() - datetime.timedelta(days=20)).isoformat()
    st = [r for r in csv.DictReader(io.StringIO(git(a.ref, "data/meta/stocks.csv")))
          if r.get("kind") == "stock" and r.get("last_seen", "") < cut and r.get("last_seen", "") >= "2015-01-01"]
    print(f"母體：2015 後停止交易普通股 {len(st)} 家")
    out, none, fail = [], [], []
    for r in sorted(st, key=lambda x: x["stock_id"]):
        rows = finmind(r["stock_id"], a.sleep)
        if rows is None:
            fail.append(r["stock_id"]); continue
        if not rows:
            none.append(r["stock_id"]); continue
        for x in rows:
            p = period_of(x)
            if p < "2015-01" or p > r["last_seen"][:7]:
                continue
            out.append([r["stock_id"], r["name"], r["market"], p, round(float(x["revenue"]) / 1000), x["date"], r["last_seen"]])
    out.sort(key=lambda x: (x[3], x[0]))
    with io.open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["stock_id", "name", "market", "period", "revenue_k", "finmind_date", "last_seen"])
        w.writerows(out)
    got = len({x[0] for x in out})
    print(f"⭐ 寫入 {len(out)} 列、{got} 家｜FinMind 無資料 {len(none)} 家 {none}｜抓取失敗 {len(fail)} 家 {fail}")
    return 0 if not fail else 1


if __name__ == "__main__":
    sys.exit(main())
