# -*- coding: utf-8 -*-
"""董監大股東質權設定／解除、轉讓持股（各 ≥100 萬股）月報 ⇒ insider_<種類>.csv

    python3 curated/insider_monthly/build.py [--from 95/01] [--to 115/09]

依據：情報 1013-2340（內部人轉讓、設質異常 ⇒ 之後 20 天）；裁定 seq348 §三；本線 1015 探針。
來源：MOPS 舊版 ajax_IRB190／IRB200／IRB140 回的是導向 ⇒ 證交所靜態月報
  https://siis.twse.com.tw/publish/<sii|otc>/<民國年>IRB<代號>_<MM>.HTM（cp950）
  IRB190 董事、監察人質權設定在 100 萬股以上者彙總表（不含金控子公司）
  IRB200 董事、監察人質權解除在 100 萬股以上者彙總表
  IRB140 董事、監察人、經理人及 10% 以上大股東轉讓持股達百萬股以上者彙總表
⭐ 每份檔頭有「日期」＝該月報的發布日（例 11303 那份 113/04/23）⇒ 存成 published，⭐ 這才是可用日，⛔ 不可用資料年月。
⛔ 只收 ≥100 萬股的事件（官方表的門檻），⛔ 不是全部內部人異動。
⛔ 不收個人姓名欄（研究用不到；只留公司、身分別、股數）。
判準：檔頭的資料年月必須＝請求的年月（防導到別月）；表頭必須是預期那幾欄，否則該月整份不收、記 _log。
每發間隔 2 秒、一般 UA。
"""
import argparse, csv, html, io, os, re, sys, time, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
URL = "https://siis.twse.com.tw/publish/{m}/{y}IRB{k}_{mm:02d}.HTM"
KINDS = {
    "190": ("pledge_set", ["公司名稱", "設定股數", "累計設定股數", "佔持股比例"],
            ["shares", "cumulative_pledged_shares", "pledged_pct_of_holding"]),
    "200": ("pledge_release", ["公司名稱", "解除股數", "累計設定股數", "佔持股比例"],
            ["shares", "cumulative_pledged_shares", "pledged_pct_of_holding"]),
    "140": ("transfer", ["公司名稱", "身份別", "姓名(或法人名稱)", "轉讓股數"],
            ["role", None, "shares"]),
}


def months(a, b):
    y, m = map(int, a.split("/")); y2, m2 = map(int, b.split("/"))
    while (y, m) <= (y2, m2):
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1


def get(u):
    time.sleep(2)
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60) as r:
            b = r.read()
            # ⚠ 上櫃 2011-10～2014-06 有 15 個月的檔是 UTF-16LE（有 BOM 或滿是 NUL 位元組），其餘 cp950
            if b[:2] in (b'\xff\xfe', b'\xfe\xff') or b[:400].count(b'\x00') > 50:
                return r.status, b.decode("utf-16", "replace")
            return r.status, b.decode("cp950", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:  # noqa: BLE001
        return None, str(e)


def clean(c):
    return re.sub(r"<[^>]+>|&nbsp;|\s+", "", c)


def parse(s, hdr):
    cells = [clean(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", s, re.S | re.I)]
    if hdr[0] not in cells:
        return None
    i = cells.index(hdr[0])
    if cells[i:i + len(hdr)] != hdr:
        return None
    body = [c for c in cells[i + len(hdr):]]
    rows = [body[k:k + len(hdr)] for k in range(0, len(body) - len(hdr) + 1, len(hdr))]
    return [r for r in rows if r and re.match(r"^\d{4}", r[0])]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="a", default="95/01")
    ap.add_argument("--to", dest="b", default="115/09")
    a = ap.parse_args()
    log = io.open(os.path.join(HERE, "_log.txt"), "a", encoding="utf-8")
    for k, (name, hdr, cols) in KINDS.items():
        out = os.path.join(HERE, "insider_%s.csv" % name)
        have = {}
        if os.path.exists(out):
            for r in csv.DictReader(io.open(out, encoding="utf-8")):
                have.setdefault((r["market"], r["data_ym"]), []).append(r)
        header = ["data_ym", "published", "market", "stock_id", "company"] + [c for c in cols if c]
        for mkt in ("sii", "otc"):
            n_ok = n_empty = n_bad = 0
            for y, m in months(a.a, a.b):
                ym = "%d-%02d" % (y + 1911, m)
                if (mkt, ym) in have:
                    continue
                st, s = get(URL.format(m=mkt, y=y, k=k, mm=m))
                s = html.unescape(s)   # ⚠ 上櫃 2011-10、2012-01、02 三份的中文是 HTML 數字實體（&#xxxxx;）
                if st != 200:
                    n_empty += 1
                    log.write("%s %s %s HTTP %s\n" % (name, mkt, ym, st)); continue
                mh = re.search(r"資\s*料\s*年\s*月\s*[:：]\s*(\d+)", re.sub(r"<[^>]+>", " ", s))
                ph = re.search(r"日\s*期\s*[:：]\s*(\d+)\s*/\s*(\d+)\s*/\s*(\d+)", re.sub(r"<[^>]+>", " ", s))
                if not mh or mh.group(1) != "%d%02d" % (y, m):
                    n_bad += 1
                    log.write("%s %s %s 資料年月不符：%s\n" % (name, mkt, ym, mh.group(1) if mh else None)); continue
                rows = parse(s, hdr)
                if rows is None:
                    n_bad += 1
                    log.write("%s %s %s 表頭不符\n" % (name, mkt, ym)); continue
                pub = "%d-%02d-%02d" % (int(ph.group(1)) + 1911, int(ph.group(2)), int(ph.group(3))) if ph else ""
                lst = have.setdefault((mkt, ym), [])
                for r in rows:
                    d = {"data_ym": ym, "published": pub, "market": mkt, "stock_id": r[0][:4], "company": r[0]}
                    for c, v in zip(cols, r[1:]):
                        if c:
                            d[c] = v.replace(",", "")
                    lst.append(d)
                if not rows:
                    lst.append({"data_ym": ym, "published": pub, "market": mkt, "stock_id": "", "company": "（本月無）"})
                n_ok += 1
            print("%s %s｜收 %d 月、無檔 %d、不符 %d" % (name, mkt, n_ok, n_empty, n_bad), flush=True)
            with io.open(out, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, header, lineterminator="\n", extrasaction="ignore")
                w.writeheader()
                for key in sorted(have):
                    for r in have[key]:
                        w.writerow({c: r.get(c, "") for c in header})
    return 0


if __name__ == "__main__":
    sys.exit(main())
