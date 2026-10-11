# -*- coding: utf-8 -*-
"""上市早年減資偵測＋參考價推估（2004-02～2010-12）⇒ twse_reduce_detected_2004_2010.csv

    python3 curated/twse_reduce_early/build.py [--ref origin/main]

依據：裁定 seq335 §一 (a)、回測 1011-0108（早年飆股 3.5% 假飆股來自減資沒還原）。
⛔ TWTAUU 官方表 2011-01-01 起才有：查 2004～2010 回「查詢開始日期小於100年1月1日，請重新查詢!」（2026-10-11 實測）
⇒ 2004～2010 只能偵測＋推估，⛔ 不是官方事實。

讀 git 物件（⛔ 不連網）：data/early/daily（上市列）、data/early/exright（扣除權息）、data/early/reduce（官方 TWTAUU 2011～2014，驗收用）。

偵測（四碼普通股；同上櫃 otc_reduce_early 的合併缺口定義）：
  缺口 ＝ 上一個有成交日與本次有成交日之間的上市交易日數（整列消失、有列無成交都算）
  候選 ＝ 缺口 ≥ 4 且 股數比 < 0.999 且 缺口內沒有除權息
  股數比 ＝ 恢復日起 6 個交易列（含恢復日）內最小的 shares ÷ 前次 shares
          （早年 shares 欄常晚 1～4 天才更新；shares_lag＝第幾列才看到變少，0＝恢復日當天）
另出 twse_jump_unexplained_2004_2010.csv：缺口 ≥ 4、恢復日最低價已超過前收 ÷ 0.93（漲停也到不了）、
  但股數沒變少 ⇒ 價格斷點未解釋（可能是減資同時增資、股數欄未更新），⛔ 不推因子，照實列出
參考價推估（⚠ 上市恢復日的 change 一律 0、早年無漲跌停價欄 ⇒ 不能像上櫃用 close−change 反推）：
  L（彌補虧損式）＝ 前收 ÷ 股數比
  C（現金減資退面額 10 元式）＝ (前收 − 10×(1−股數比)) ÷ 股數比
  可行區間 ＝ [當日最高 ÷ 1.07, 當日最低 ÷ 0.93]（早年漲跌幅 7%；放寬 0.6% 容捨入）
  只有一式在區間內 ⇒ 用它；兩式都在 ⇒ 用 C（2011～2014 驗收：兩式都可行的 12 筆全是現金減資）；
  都不在（多半是減資同時增資，股數比失真）⇒ 用區間中點（method＝M，誤差較大）
"""
import argparse, bisect, collections, csv, io, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(HERE, "twse_reduce_detected_2004_2010.csv")
OUT_U = os.path.join(HERE, "twse_jump_unexplained_2004_2010.csv")
LAG = 5
HEADER = ["date", "stock_id", "name", "pre_close", "ref_price", "factor_est", "method", "ref_lo", "ref_hi",
          "last_trade_day", "gap_days", "shares_ratio", "shares_lag", "resume_open", "resume_high", "resume_low", "resume_close"]
LIMIT, TOL = 0.07, 0.006
CUTOFF = "2011-01-01"   # TWTAUU 官方起點


def git(*a):
    return subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, text=True, check=True).stdout


def fnum(x):
    try:
        return float(str(x).replace(",", ""))
    except ValueError:
        return None


def tree_csv(ref, tree):
    out = []
    for ln in git("ls-tree", ref, tree + "/").splitlines():
        path = ln.split("\t")[1]
        if path.endswith(".csv") and path.rsplit("/", 1)[1][:4].isdigit():
            out += list(csv.DictReader(io.StringIO(git("show", ref + ":" + path))))
    return out


def load(ref):
    files = {}
    for ln in git("ls-tree", ref, "data/early/daily/").splitlines():
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
            if r.get("market") == "twse":
                hit = True
                ser[r["stock_id"]][d] = tuple(fnum(r[k]) for k in ("open", "high", "low", "close", "shares"))
                names[r["stock_id"]] = r["name"]
        if hit:
            cal.append(d)
    p.stdin.close()
    return ser, names, cal


def estimate(pre, r, h, l, c):
    lo = (h or c) / (1 + LIMIT) * (1 - TOL)
    hi = (l or c) / (1 - LIMIT) * (1 + TOL)
    cand = {"L": pre / r}
    cc = (pre - 10 * (1 - r)) / r
    if cc > 0:
        cand["C"] = cc
    feas = [k for k in ("C", "L") if k in cand and lo <= cand[k] <= hi]
    if feas:
        return feas[0], cand[feas[0]], lo, hi
    mid = ((h or c) / (1 + LIMIT) + (l or c) / (1 - LIMIT)) / 2
    return "M", mid, lo, hi


def detect(ser, cal, exr, unexplained):
    det = []
    for s, v in ser.items():
        if not (len(s) == 4 and s[0] in "123456789"):
            continue
        prev = None
        ds = sorted(v)
        for i, d in enumerate(ds):
            o, h, l, c, sh = v[d]
            if not c:
                continue
            if prev:
                gap = bisect.bisect_left(cal, d) - bisect.bisect_right(cal, prev[0])
                r, lag = None, None
                if prev[2]:
                    for k, x in enumerate(ds[i:i + LAG + 1]):
                        if v[x][4] and (r is None or v[x][4] / prev[2] < r):
                            r = v[x][4] / prev[2]
                            if r < 0.999 and lag is None:
                                lag = k
                if gap >= 4 and not any(prev[0] < x <= d for x in exr[s]):
                    if r is not None and r < 0.999:
                        m, ref, lo, hi = estimate(prev[1], r, h, l, c)
                        det.append(dict(date=d, stock_id=s, pre_close=prev[1], ref_price=round(ref, 4),
                                        factor_est=round(ref / prev[1], 6), method=m, ref_lo=round(lo, 4), ref_hi=round(hi, 4),
                                        last_trade_day=prev[0], gap_days=gap, shares_ratio=round(r, 6), shares_lag=lag,
                                        resume_open=o, resume_high=h, resume_low=l, resume_close=c))
                    elif (l or c) / prev[1] > 1 / (1 - LIMIT) * 1.01:
                        unexplained.append(dict(date=d, stock_id=s, pre_close=prev[1], last_trade_day=prev[0], gap_days=gap,
                                                shares_ratio="" if r is None else round(r, 6),
                                                resume_low=l, resume_close=c, jump=round((l or c) / prev[1], 4)))
            prev = (d, c, sh)
    return det


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="origin/main")
    a = ap.parse_args()
    ser, names, cal = load(a.ref)
    exr = collections.defaultdict(list)
    for r in tree_csv(a.ref, "data/early/exright"):
        exr[r["stock_id"]].append(r["date"])
    off = tree_csv(a.ref, "data/early/reduce")
    unexplained = []
    det = detect(ser, cal, exr, unexplained)
    print(f"上市交易日 {len(cal)}（{cal[0]}～{cal[-1]}）｜候選 {len(det)}")

    # ── 驗收：官方 TWTAUU（data/early/reduce，2011-01-25～2014-12-10）
    hit, errs, meth = 0, [], collections.Counter()
    for r in off:
        m = [x for x in det if x["stock_id"] == r["stock_id"] and x["last_trade_day"] < r["date"] <= x["date"]]
        if not m:
            continue
        hit += 1
        e = m[0]["ref_price"] / float(r["ref_price"]) - 1
        errs.append(abs(e)); meth[m[0]["method"]] += 1
    errs.sort()
    offk = collections.defaultdict(list)
    for r in off:
        offk[r["stock_id"]].append(r["date"])
    fp = [x for x in det if "2011-01-25" <= x["date"] <= "2014-12-31"
          and not any(x["last_trade_day"] < d <= x["date"] for d in offk[x["stock_id"]])]
    print(f"⭐ 驗收 G1：官方 {len(off)} 筆命中 {hit}（{hit / len(off):.1%}）｜非官方候選 {len(fp)} "
          f"{[(x['stock_id'], x['date'], x['factor_est']) for x in fp]}")
    print(f"⭐ 參考價誤差（命中者）：中位 {errs[len(errs) // 2]:.2%}｜p90 {errs[int(len(errs) * .9)]:.2%}｜最大 {errs[-1]:.2%}"
          f"｜≤1% {sum(1 for v in errs if v <= .01)}/{len(errs)}｜方法 {dict(meth)}")
    if hit / len(off) < 0.90:
        print("⛔ G1 < 90%，不寫檔"); return 1

    rows = [dict(x, name=names.get(x["stock_id"], "")) for x in det if x["date"] < CUTOFF]
    rows.sort(key=lambda x: (x["date"], x["stock_id"]))
    with io.open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, HEADER, lineterminator="\n")
        w.writeheader()
        for x in rows:
            w.writerow({k: x[k] for k in HEADER})
    U = sorted((dict(x, name=names.get(x["stock_id"], "")) for x in unexplained if x["date"] < CUTOFF), key=lambda x: (x["date"], x["stock_id"]))
    UH = ["date", "stock_id", "name", "pre_close", "last_trade_day", "gap_days", "shares_ratio", "resume_low", "resume_close", "jump"]
    with io.open(OUT_U, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, UH, lineterminator="\n")
        w.writeheader()
        for x in U:
            w.writerow({k: x[k] for k in UH})
    print(f"⚠ 未解釋（跳過漲停仍到不了、股數沒變少）2004～2010：{len(U)} 筆 ⇒ {OUT_U}")
    print(f"⭐ 2004～2010：{len(rows)} 筆（逐年 {sorted(collections.Counter(x['date'][:4] for x in rows).items())}"
          f"｜方法 {dict(collections.Counter(x['method'] for x in rows))}）⇒ {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
