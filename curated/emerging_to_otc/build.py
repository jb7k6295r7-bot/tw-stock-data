#!/usr/bin/env python3
"""興櫃轉上櫃【推定】名單（單因子 S59；裁定 seq526 准用推定名單）⇒ emerging_to_otc.csv

    python3 curated/emerging_to_otc/build.py [--from 2006-01] [--to 2026-10] [--outdir DIR]

官方沒有「由興櫃轉」的逐檔標記，所以用兩張官方月表交叉推定（全文見 README「推定規則」）：
  ① siis IRB170「新公司彙總表」上櫃版  https://siis.twse.com.tw/publish/otc/<民國年>IRB170_<MM>.HTM
     ＝該資料年月新進上櫃的公司（不分來源：興櫃轉、上市轉、控股公司換股新設都會在）
  ② siis IRB110 興櫃版（rotc）        https://siis.twse.com.tw/publish/rotc/<民國年>IRB110_<MM>.HTM
     ＝該資料年月的興櫃公司全名冊（每家一列）
  規則：① 資料年月 M 的公司，若在 ② 的 M−3～M 任一月出現 ⇒ inferred=1（推定興櫃轉上櫃）。
  輔證（不影響 inferred）：事前申報 insider_predeclare 在上櫃前最後一次 market=rotc 的申報日。

輸出一列＝IRB170 上櫃新公司的一筆（inferred 0／1 都留，方便核對），欄位見 README。
⛔ 不碰任何價格、報酬；名單交付前凍結（sha256 寫進 README）。
"""
import argparse, csv, glob, html, os, re, sys, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
CACHE = os.path.expanduser("~/.cache/emerging_to_otc")
URL = "https://siis.twse.com.tw/publish/{m}/{y}IRB{k}_{mm:02d}.HTM"
LOOKBACK = 3          # ② 往前看幾個月（含 M 當月共 LOOKBACK+1 個月）
RULE = ("IRB170 上櫃新公司 資料年月 M 的公司，若在興櫃 IRB110（rotc）資料年月 M−3～M 任一月的名冊出現"
        " ⇒ inferred=1（推定興櫃轉上櫃）；否則 0。輔證欄不影響判定。")


def decode(b):
    # 官方有些月份是另存的 UTF-16 檔（開頭 FF FE，例：興櫃 IRB110 102/05）
    if b[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return b.decode("utf-16", "replace")
    # 官方 cp950 混雜壞位元組：逐段解，壞的那段換成 �，不讓整頁失敗（同 insider_holding）
    return "<".join(seg.decode("cp950", "replace") for seg in b.split(b"<"))


def fetch(m, k, y, mm, sleep):
    os.makedirs(CACHE, exist_ok=True)
    fp = os.path.join(CACHE, f"{m}_{y}IRB{k}_{mm:02d}.HTM")
    if os.path.exists(fp) and os.path.getsize(fp) > 0:
        return open(fp, "rb").read()
    u = URL.format(m=m, y=y, k=k, mm=mm)
    for i in range(4):
        try:
            b = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read()
            time.sleep(sleep)
            open(fp, "wb").write(b)
            return b
        except urllib.error.HTTPError as e:
            if e.code == 404:
                time.sleep(sleep)
                return None
            time.sleep(5 * (i + 1))
        except Exception:
            time.sleep(5 * (i + 1))
    raise RuntimeError(f"抓不到 {u}")


def text(s):
    s = re.sub(r"<script.*?</script>", " ", s, flags=re.S | re.I)
    # 官方有些月份整頁用 &#33891; 這種實體字元（例：興櫃 IRB110 100/10）⇒ 先還原
    s = html.unescape(s)
    s = re.sub(r"\?/(t[dh])>", r"</\1>", s, flags=re.I)
    return s


def head_ym(t):
    m = re.search(r"資\s*料\s*年\s*月\s*[:：]\s*(\d{4,5})", re.sub(r"<[^>]+>", " ", t))
    return m.group(1) if m else None


def head_pub(t):
    m = re.search(r"日\s*期\s*[:：]\s*(\d{2,3})/(\d{2})/(\d{2})", re.sub(r"<[^>]+>", " ", t))
    return f"{int(m.group(1)) + 1911:04d}-{m.group(2)}-{m.group(3)}" if m else None


def parse170(b, y, mm):
    """⇒ (published, [(stock_id, name)])；表頭年月不符或合計對不上 ⇒ raise"""
    t = text(decode(b))
    ym = head_ym(t)
    if ym != f"{y}{mm:02d}":
        raise ValueError(f"IRB170 {y}/{mm:02d} 表頭資料年月是 {ym}")
    cells = [re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", c)) for c in re.findall(r"<td[^>]*>(.*?)</td>", t, flags=re.S | re.I)]
    rows = []
    for i, c in enumerate(cells):
        if re.fullmatch(r"\d{4,6}[A-Z]?", c) and i + 1 < len(cells) and cells[i + 1] and not re.fullmatch(r"[\d,]+", cells[i + 1]):
            rows.append((c, cells[i + 1]))
    m = re.search(r"合\s*計\s*[:：]\s*(\d+)\s*家", re.sub(r"<[^>]+>", " ", t))
    if not m:
        raise ValueError(f"IRB170 {y}/{mm:02d} 沒有「合計：N 家」")
    if int(m.group(1)) != len(rows):
        raise ValueError(f"IRB170 {y}/{mm:02d} 合計 {m.group(1)} 家、解析 {len(rows)} 家")
    return head_pub(t), rows


def parse110_ids(b, y, mm):
    """興櫃 IRB110 名冊 ⇒ 代號集合（公司名稱格開頭 4～6 碼）；表頭年月不符 ⇒ raise"""
    t = text(decode(b))
    ym = head_ym(t)
    if ym != f"{y}{mm:02d}":
        raise ValueError(f"rotc IRB110 {y}/{mm:02d} 表頭資料年月是 {ym}")
    ids = set()
    for c in re.findall(r"<td[^>]*>(.*?)</td>", t, flags=re.S | re.I):
        c = re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", c))
        mt = re.match(r"^(\d{4,6}[A-Z]?)(?=\D)", c)
        if mt and not re.fullmatch(r"[\d,.\-]+", c):
            ids.add(mt.group(1))
    if not ids:
        raise ValueError(f"rotc IRB110 {y}/{mm:02d} 0 家")
    return ids


def months(a, b):
    y, m = a
    while (y, m) <= b:
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1


def back(y, m, k):
    m -= k
    while m < 1:
        y, m = y - 1, m + 12
    return y, m


def predeclare_rotc():
    """事前申報 market=rotc 的申報日（輔證）⇒ {stock_id: [日期...]}"""
    d = {}
    for f in sorted(glob.glob(os.path.join(REPO, "curated", "insider_predeclare", "insider_predeclare_*.csv"))):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            if r.get("market") == "rotc":
                d.setdefault(r["stock_id"], []).append(r["declare_date"])
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="a", default="2006-01")
    ap.add_argument("--to", dest="b", required=True, help="最後一個資料年月 YYYY-MM（已公布的）")
    ap.add_argument("--outdir", default=HERE)
    ap.add_argument("--sleep", type=float, default=2.0)
    a = ap.parse_args()
    A = tuple(int(x) for x in a.a.split("-")); B = tuple(int(x) for x in a.b.split("-"))

    rotc = {}
    for (y, m) in months(back(*A, LOOKBACK), B):
        b = fetch("rotc", 110, y - 1911, m, a.sleep)
        if b is None:
            raise SystemExit(f"⛔ rotc IRB110 {y}-{m:02d} 404（範圍內不該缺）")
        rotc[(y, m)] = parse110_ids(b, y - 1911, m)
    pre = predeclare_rotc()

    out = []
    for (y, m) in months(A, B):
        b = fetch("otc", 170, y - 1911, m, a.sleep)
        if b is None:
            raise SystemExit(f"⛔ otc IRB170 {y}-{m:02d} 404（範圍內不該缺）")
        pub, rows = parse170(b, y - 1911, m)
        win = [back(y, m, k) for k in range(LOOKBACK, -1, -1)]
        for sid, name in rows:
            hit = [w for w in win if sid in rotc[w]]
            first_rotc = next((w for w in sorted(rotc) if sid in rotc[w] and w <= (y, m)), None)
            ym = f"{y:04d}-{m:02d}"
            pd_ = [d for d in pre.get(sid, []) if d[:7] <= ym]
            out.append({
                "stock_id": sid, "name": name, "irb170_ym": ym, "irb170_published": pub or "",
                "inferred": 1 if hit else 0,
                "rotc_last_ym": f"{hit[-1][0]:04d}-{hit[-1][1]:02d}" if hit else "",
                "rotc_months_in_window": len(hit),
                "rotc_first_ym_seen": f"{first_rotc[0]:04d}-{first_rotc[1]:02d}" if first_rotc else "",
                "predeclare_rotc_last": max(pd_) if pd_ else "",
            })
    os.makedirs(a.outdir, exist_ok=True)
    fp = os.path.join(a.outdir, "emerging_to_otc.csv")
    cols = list(out[0].keys())
    with open(fp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(out)
    n1 = sum(r["inferred"] for r in out)
    print(f"✓ {fp}：IRB170 上櫃新公司 {len(out)} 筆，推定興櫃轉上櫃 {n1}、非 {len(out) - n1}（{a.a}～{a.b}）")
    print("規則：" + RULE)


if __name__ == "__main__":
    main()
