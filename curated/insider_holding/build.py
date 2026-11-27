# -*- coding: utf-8 -*-
"""董監、經理人、10% 大股東【持股水準】與【質權設定】全市場月報 ⇒ irb110_<年>.csv、irb130_<年>.csv（2006-01 起）

    python3 curated/insider_holding/build.py [--start 2006-01] [--end 2026-10] [--outdir DIR]
    python3 curated/insider_holding/build.py --recent [--outdir data/meta/insider_holding]   # ⭐ 排程用：補近 3 個月裡還沒有的月份

依據：回測 1127-1457（單因子 S29 內部人持股增加、S87 董監持股比例水準、S30 內部人質押比上升）；
      資料庫 1127-1531（29 發探測）；裁定 seq526 §四（可用日用表頭「資料日期」）。
來源（官方、證交所 siis 靜態月報，與 curated/insider_monthly 同一個站）：
  https://siis.twse.com.tw/publish/<sii|otc>/<民國年>IRB<110|130>_<MM>.HTM
  IRB110 董事、監察人、經理人及百分之十以上大股東股權異動彙總表（不含金控子公司）
  IRB130 董事、監察人、經理人及百分之十以上大股東質權設定彙總表（不含金控子公司）
  ⭐ 這兩張是【每家公司一列的全名單】（不是 ≥100 萬股的事件表）。
⭐ 檔頭「資料日期」（例 11408 那份 114/09/17）＝發布日 ⇒ 存 published，⭐ 這才是可用日，⛔ 不可用 data_ym。
寫檔＝【合併、只准變多】：同一 (market, data_ym) 新列數 < 舊列數、或年檔總列數變少 ⇒ 整趟不寫（exit 1）。
守門（每發）：① 檔頭資料年月＝請求年月 ② 兩層表頭逐字＝預期 ③ 每列格數＝預期、數字欄可解析 ④ 0 列＝失敗
              ⑤ 內容指紋不得與其他月份相同（防導到別月）。
404：只有【當月與前 2 個月】視為「還沒發布」（記下、不算失敗）；更早的月份 404 ＝失敗。
快取：~/.cache/insider_holding/<market>_<kind>_<ym>.html，⭐ 只在全部守門過了才寫。
每發間隔 --sleep 秒（預設 2）、一般 UA；403／429 ⇒ 停，不繞過。
⛔ 不收個人姓名（這兩張表本來就沒有）。
"""
import argparse, csv, hashlib, html, io, os, re, sys, time, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.expanduser("~/.cache/insider_holding")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
URL = "https://siis.twse.com.tw/publish/{m}/{y}IRB{k}_{mm:02d}.HTM"
BASE = ["data_ym", "published", "market", "stock_id", "company"]
KINDS = {
    "110": dict(
        hdr=[["公司名稱", "實際發行股票總額", "董事、監察人本月份", "佔股份總額%", "經理人本月份實際持有股數", "百分之十以上大股東本月份實際持有股數"],
             ["增加股數", "減少股數", "實際持有股數"]],
        cols=["issued_shares", "ds_increase", "ds_decrease", "ds_shares", "ds_pct_of_issued", "mgr_shares", "major_shares"]),
    "130": dict(
        hdr=[["公司名稱", "董事、監察人本月份", "佔持股比例%", "經理人本月份實際持有股數", "百分之十以上大股東本月份實際持有股數",
              "經理人及百分之十以上大股東已設定股數", "佔持股比例%"],
             ["實際持有股數", "設定股數", "解除股數", "累計設定股數"]],
        cols=["ds_shares", "ds_pledge_set", "ds_pledge_release", "ds_pledged_cum", "ds_pledged_pct",
              "mgr_shares", "major_shares", "mgr_major_pledged", "mgr_major_pledged_pct"]),
}


def months(a, b):
    y, m = map(int, a.split("-")); y2, m2 = map(int, b.split("-"))
    while (y, m) <= (y2, m2):
        yield "%04d-%02d" % (y, m)
        m += 1
        if m == 13:
            y, m = y + 1, 1


def taipei_ym(back):
    t = time.gmtime(time.time() + 8 * 3600)
    y, m = t.tm_year, t.tm_mon - back
    while m < 1:
        y, m = y - 1, m + 12
    return "%04d-%02d" % (y, m)


def decode(b):
    # ⚠ 上櫃 2011-10～2014-06 有幾個月是 UTF-16（insider_monthly 實測），其餘 cp950
    if b[:2] in (b"\xff\xfe", b"\xfe\xff") or b[:400].count(b"\x00") > 50:
        return b.decode("utf-16", "replace")
    # ⛔ 官方公司欄把名稱截在雙位元組字中間（實測 1626 艾美特 2016-03～2017-11、4107 邦特 2009～2010）
    #   ⇒ 整份一起解碼時，半個字會把後面 </TD> 的「<」吃掉 ⇒ 少一格。
    #   ⭐ Big5 的第二位元組不會是 0x3C ⇒ 先用 b"<" 切段、逐段解碼，半個字只壞它自己那段
    return "<".join(seg.decode("cp950", "replace") for seg in b.split(b"<"))


def get(url, sleep):
    time.sleep(sleep)
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                return 200, r.read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                sys.exit(f"⛔ HTTP {e.code}：{url} ⇒ 被擋，停（不繞過）")
            if e.code == 404:
                return 404, b""
            print(f"  重試 {i}：HTTP {e.code}"); time.sleep(20)
        except Exception as e:  # noqa: BLE001
            print(f"  重試 {i}：{e}"); time.sleep(20)
    return None, b""


def clean(c):
    return re.sub(r"<[^>]+>|&nbsp;|\s+", "", c)


def num(s):
    return s.replace(",", "").strip()


def parse(s, ym, kind):
    """回 (published, rows)；不合格丟 RuntimeError。純函式，selftest 直接餵字串。"""
    s = html.unescape(s)
    # ⛔ 官方原檔本身就壞：截斷的公司名稱後面 `</TD>` 的「<」被寫成「?」（位元組層級實測：1626 艾美特 2016-03～2017-11、
    #   4107 邦特 2009-01～2010-01，上市上櫃 IRB110／130 都有）⇒ 「?/TD>」修回「</TD>」（正常 HTML 不會出現這串）
    s = re.sub(r"\?/(t[dh])>", r"</\1>", s, flags=re.I)
    flat =re.sub(r"<[^>]+>", " ", s)
    mh = re.search(r"資\s*料\s*年\s*月\s*[:：]\s*(\d+)", flat)
    want = "%d%02d" % (int(ym[:4]) - 1911, int(ym[5:7]))
    if not mh or mh.group(1) != want:
        raise RuntimeError(f"資料年月不符：{mh.group(1) if mh else None} ≠ {want}")
    ph = re.search(r"資\s*料\s*日\s*期\s*[:：]\s*(\d+)\s*/\s*(\d+)\s*/\s*(\d+)", flat)
    if not ph:
        raise RuntimeError("找不到資料日期")
    pub = "%d-%02d-%02d" % (int(ph.group(1)) + 1911, int(ph.group(2)), int(ph.group(3)))
    if pub[:7] <= ym:
        raise RuntimeError(f"資料日期 {pub} 不在資料年月 {ym} 之後")
    spec = KINDS[kind]
    trs = [[clean(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", t, re.S | re.I)]
           for t in re.findall(r"<tr[^>]*>(.*?)</tr>", s, re.S | re.I)]
    try:
        i = trs.index(spec["hdr"][0])
    except ValueError:
        raise RuntimeError("第一層表頭不符")
    if trs[i + 1] != spec["hdr"][1]:
        raise RuntimeError(f"第二層表頭不符：{trs[i + 1]}")
    n = 1 + len(spec["cols"])
    rows = []
    for c in trs[i + 2:]:
        if not c or not re.match(r"^\d{4}", c[0]):
            continue
        if len(c) != n:
            raise RuntimeError(f"格數 {len(c)} ≠ {n}：{c[:2]}")
        vals = [num(v) for v in c[1:]]
        for v in vals:
            if not re.fullmatch(r"-?\d+(\.\d+)?", v):
                raise RuntimeError(f"數字欄解析不了：{c[0]} {v!r}")
        rows.append([ym, pub, "", c[0][:4], c[0]] + vals)
    if not rows:
        raise RuntimeError("0 列")
    return pub, rows


def fingerprint(rows):
    return hashlib.md5("\n".join(",".join(r[3:]) for r in rows).encode("utf-8")).hexdigest()


def load_years(outdir, kind):
    have = {}
    hdr = BASE + KINDS[kind]["cols"]
    for f in sorted(os.listdir(outdir)) if os.path.isdir(outdir) else []:
        if re.fullmatch(r"irb%s_\d{4}\.csv" % kind, f):
            with io.open(os.path.join(outdir, f), encoding="utf-8") as fh:
                rd = csv.reader(fh)
                if next(rd, None) != hdr:
                    sys.exit(f"⛔ {f} 欄位與本程式不同 ⇒ 不寫")
                for r in rd:
                    if r:
                        have.setdefault((r[2], r[0]), []).append(r)
    return have


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2006-01")
    ap.add_argument("--end", default=taipei_ym(1))
    ap.add_argument("--outdir", default=HERE)
    ap.add_argument("--recent", action="store_true", help="排程用：只看近 3 個月（台北），已有的略過")
    ap.add_argument("--kinds", default="110,130")
    ap.add_argument("--sleep", type=float, default=2.0)
    a = ap.parse_args()
    if a.recent:
        a.start, a.end = taipei_ym(3), taipei_ym(1)
    recent_ok = {taipei_ym(0), taipei_ym(1), taipei_ym(2)}   # 當月與前 2 個月 404 ＝還沒發布
    os.makedirs(a.outdir, exist_ok=True)
    rc = 0
    for kind in a.kinds.split(","):
        have = load_years(a.outdir, kind)
        old_n = {k: len(v) for k, v in have.items()}
        prints = {fingerprint(v): k for k, v in have.items()}
        got, fails, unpub = {}, [], []
        for mkt in ("sii", "otc"):
            for ym in months(a.start, a.end):
                if (mkt, ym) in have:
                    continue
                y, m = int(ym[:4]) - 1911, int(ym[5:7])
                cp = os.path.join(CACHE, f"{mkt}_{kind}_{ym}.html")
                if os.path.exists(cp):
                    st, b = 200, open(cp, "rb").read()
                else:
                    st, b = get(URL.format(m=mkt, y=y, k=kind, mm=m), a.sleep)
                if st == 404 and ym in recent_ok:
                    unpub.append(f"{mkt} {ym}"); continue
                try:
                    if st != 200:
                        raise RuntimeError(f"HTTP {st}")
                    pub, rows = parse(decode(b), ym, kind)
                except RuntimeError as e:
                    fails.append((mkt, ym, str(e))); print(f"  ✗ IRB{kind} {mkt} {ym}：{e}", flush=True); continue
                for r in rows:
                    r[2] = mkt
                fp = fingerprint(rows)
                if fp in prints:
                    fails.append((mkt, ym, f"指紋與 {prints[fp]} 相同")); print(f"  ✗ IRB{kind} {mkt} {ym} 指紋重複 {prints[fp]}"); continue
                prints[fp] = (mkt, ym)
                got[(mkt, ym)] = rows
                if not os.path.exists(cp):
                    os.makedirs(CACHE, exist_ok=True); open(cp, "wb").write(b)
                print(f"  IRB{kind} {mkt} {ym}：{len(rows)} 列（發布 {pub}）", flush=True)
        if unpub:
            print(f"  IRB{kind} 還沒發布（近 2 個月 404，不算失敗）：{unpub}")
        if fails:
            print(f"⛔ IRB{kind} 失敗 {len(fails)}：{fails[:10]} ⇒ 本表不寫"); rc = 1; continue
        if not got:
            print(f"  IRB{kind}：沒有新月份"); continue
        have.update(got)
        years = {}
        for (mkt, ym), rs in have.items():
            years.setdefault(ym[:4], []).extend(rs)
        for y in sorted({ym[:4] for (_, ym) in got}):
            p = os.path.join(a.outdir, f"irb{kind}_{y}.csv")
            n_old = sum(v for (mk, ym), v in old_n.items() if ym[:4] == y)
            rs = sorted(years[y], key=lambda r: (r[0], r[2], r[3], r[4]))
            if len(rs) < n_old:
                print(f"⛔ {p} 列數 {n_old} → {len(rs)} 變少 ⇒ 不寫"); rc = 1; continue
            with io.open(p, "w", encoding="utf-8", newline="") as f:
                w = csv.writer(f, lineterminator="\n"); w.writerow(BASE + KINDS[kind]["cols"]); w.writerows(rs)
            print(f"  寫 {os.path.basename(p)}：{n_old} → {len(rs)} 列")
        print(f"⭐ IRB{kind}：本趟新收 {len(got)} 個（市場×月）、{sum(len(v) for v in got.values())} 列")
    return rc


if __name__ == "__main__":
    sys.exit(main())
