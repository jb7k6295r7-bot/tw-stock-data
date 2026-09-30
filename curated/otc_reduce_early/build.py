# -*- coding: utf-8 -*-
"""上櫃早年減資偵測（合併缺口定義，裁定 seq280 §五）⇒ otc_reduce_detected_2007_2012.csv

    python3 curated/otc_reduce_early/build.py [--ref origin/main]

讀 git 物件（⛔ 不連網、不解壓）：data/early/daily ＋ data/universe/daily（上櫃列）、
data/meta/otc_reduce_history.csv（官方 revivt，驗收用）、data/meta/otc_exright_history.csv（扣除權息）。

定義（四碼普通股）：
  缺口     ＝ 上一個有成交日 與 本次有成交日 之間的上櫃交易日數（整列消失、有列無成交都算）
  候選     ＝ 缺口 ≥ 4 且 參考價（收盤−漲跌）÷ 前一有成交日收盤 偏離 > 0.1%（且 > 0.0101 元）
  股數變少 ＝ 本次有成交日的 shares ÷ 前一有成交日的 shares < 0.999
驗收結果與出處見同目錄 README.md。
"""
import argparse, bisect, collections, csv, io, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(HERE, "otc_reduce_detected_2007_2012.csv")
HEADER = ["stock_id", "name", "last_trade_day", "resume_day", "gap_days", "gap_absent_days", "last_close",
          "ref_price", "factor_est", "shares_ratio", "shares_down", "exright_in_gap"]


def git(*a):
    return subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, text=True, check=True).stdout


def fnum(x):
    try:
        return float(str(x).replace(",", ""))
    except ValueError:
        return None


def common(s):
    return len(s) == 4 and s[0] in "123456789"


def load(ref):
    files = {}
    for tree in ("data/early/daily", "data/universe/daily"):     # 同日兩邊都有 ⇒ 取主庫
        for ln in git("ls-tree", ref, tree + "/").splitlines():
            meta, path = ln.split("\t")
            b = path.rsplit("/", 1)[1]
            if b.endswith(".csv") and b[:4].isdigit():
                files[b[:-4]] = meta.split()[2]
    p = subprocess.Popen(["git", "-C", REPO, "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    ser, names, cal = collections.defaultdict(dict), {}, []
    for d in sorted(files):
        p.stdin.write((files[d] + "\n").encode()); p.stdin.flush()
        n = int(p.stdout.readline().split()[2])
        body = p.stdout.read(n); p.stdout.read(1)
        hit = False
        for r in csv.DictReader(io.StringIO(body.decode("utf-8"))):
            if r.get("market") == "tpex":
                hit = True
                ser[r["stock_id"]][d] = (r["close"], r["change"], r["shares"])
                names[r["stock_id"]] = r["name"]
        if hit:
            cal.append(d)
    p.stdin.close()
    return ser, names, cal


def detect(ser, cal):
    det = []
    for s, v in ser.items():
        if not common(s):
            continue
        prev, last_row = None, None
        for d in sorted(v):
            close, chg, shs = v[d]
            gap_abs = (bisect.bisect_left(cal, d) - bisect.bisect_right(cal, last_row)) if last_row else 0
            last_row = d
            cl = fnum(close)
            if not cl:
                continue
            c = fnum(chg)
            if prev and c is not None:
                gap = bisect.bisect_left(cal, d) - bisect.bisect_right(cal, prev[0])
                ref = cl - c
                if gap >= 4 and abs(ref - prev[1]) > 0.0101 and abs(ref / prev[1] - 1) > 0.001:
                    s0, s1 = fnum(v[prev[0]][2]), fnum(shs)
                    sr = s1 / s0 if s0 and s1 else None
                    det.append(dict(stock_id=s, last_trade_day=prev[0], resume_day=d, gap_days=gap,
                                    gap_absent_days=gap_abs, last_close=prev[1], ref_price=round(ref, 4),
                                    factor_est=round(ref / prev[1], 6),
                                    shares_ratio="" if sr is None else round(sr, 6),
                                    shares_down=int(sr is not None and sr < 0.999)))
            prev = (d, cl)
    return det


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="origin/main")
    a = ap.parse_args()
    ser, names, cal = load(a.ref)
    det = detect(ser, cal)
    off = list(csv.DictReader(io.StringIO(git("show", a.ref + ":data/meta/otc_reduce_history.csv"))))
    exr = collections.defaultdict(list)
    for r in csv.DictReader(io.StringIO(git("show", a.ref + ":data/meta/otc_exright_history.csv"))):
        exr[r["stock_id"]].append(r["date"])
    offk = collections.defaultdict(list)
    for r in off:
        offk[r["stock_id"]].append(r["date"])
    for x in det:
        x["exright_in_gap"] = int(any(x["last_trade_day"] < d <= x["resume_day"] for d in exr[x["stock_id"]]))
        x["name"] = names.get(x["stock_id"], "")
    print(f"上櫃交易日 {len(cal)}（{cal[0]}～{cal[-1]}）｜候選 {len(det)}")

    # ── 驗收：官方 revivt（2013-01-16 起）
    for nm, keep in (("純合併缺口", lambda x: True), ("＋股數變少", lambda x: x["shares_down"] == 1)):
        M = [x for x in det if keep(x)]
        hit = lambda r: any(x["stock_id"] == r["stock_id"] and x["last_trade_day"] < r["date"] <= x["resume_day"] for x in M)
        ov = [r for r in off if r["date"] <= "2014-12-31"]
        miss = [(r["stock_id"], r["date"], r["factor_official"]) for r in off if not hit(r)]
        fp = [x for x in M if x["resume_day"] >= "2013-01-16" and not x["exright_in_gap"]
              and not any(x["last_trade_day"] < d <= x["resume_day"] for d in offk[x["stock_id"]])]
        print(f"⭐ {nm}：G1 重疊期 {sum(1 for r in ov if hit(r))}/{len(ov)}｜全期 {len(off) - len(miss)}/{len(off)}"
              f"｜2013 起非官方候選（已扣除權息）{len(fp)}｜漏 {miss}")
        if nm == "＋股數變少":
            print("   非官方候選：", [(x["stock_id"], x["last_trade_day"], x["resume_day"], x["factor_est"], x["shares_ratio"]) for x in fp])

    rows = [x for x in det if "2007-07-01" <= x["resume_day"] <= "2012-12-31"]
    rows.sort(key=lambda x: (x["resume_day"], x["stock_id"]))
    with io.open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, HEADER, lineterminator="\n")
        w.writeheader()
        for x in rows:
            w.writerow({k: x[k] for k in HEADER})
    sd = [x for x in rows if x["shares_down"] and not x["exright_in_gap"]]
    print(f"⭐ 2007-07～2012-12：候選 {len(rows)}｜股數變少且缺口內無除權息 {len(sd)}"
          f"（逐年 {sorted(collections.Counter(x['resume_day'][:4] for x in sd).items())}）⇒ {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
