# -*- coding: utf-8 -*-
"""歷史產業別（point-in-time）回推 ⇒ industry_pit.csv

    python3 curated/industry_hist/build.py [--ref origin/main]

錨點：data/meta/industry.csv（現值，2026-09-05 快照；上櫃代號 32／33 名稱空白 ⇒ 補 文化創意業／農業科技業）
異動：同目錄 twse_changes.csv（2006 起）、tpex_changes.csv（2011 起）、twse_2007_split_inferred.csv（9 檔推定）
整批規則（官方只給規則、沒逐檔列）：
  ① 2023-07-03 觀光事業 整類改名 觀光餐旅（上市、上櫃）
  ② 2007-07-02 上市：電子工業 拆八子類、化學生技醫療 拆化學工業／生技醫療業
     ⇒ 那天當下屬子類、且當天沒有逐檔異動的 ⇒ 前一天是母類
做法：每檔從現值往回走，逐筆異動要求「新類別＝當下類別」（對不上記 chain_break，⛔ 不硬湊）。
輸出每檔每段：stock_id,market,industry,start,end,basis
  basis：anchor（現值段）｜change（逐檔公告）｜bulk_2007｜rename_2023｜inferred_2007｜pre_coverage（早於異動清單涵蓋起點，假設沒變）
⛔ 只含今天還在 industry.csv 的公司（已下市的沒有錨點）；另出 delisted_segments：已下市但在異動清單裡出現過的，只給有公告的那幾段。
"""
import argparse, collections, csv, io, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(HERE, "industry_pit.csv")
COVER = {"twse": "2006-01-01", "tpex": "2011-01-01"}
ELEC = {"半導體業", "電腦及週邊設備業", "光電業", "通信網路業", "電子零組件業", "電子通路業", "資訊服務業", "其他電子業"}
CHEM = {"化學工業", "生技醫療業"}
ALIAS = {"建材營造業": "建材營造", "其他業": "其他", "電器電纜業": "電器電纜", "生技醫療": "生技醫療業", "半導體": "半導體業",
         "電子商務業": "電子商務", "文化創意": "文化創意業", "貿易百貨業": "貿易百貨", "紡織纖維業": "紡織纖維",
         "電機機械業": "電機機械", "油電燃氣": "油電燃氣業", "電腦及週邊": "電腦及週邊設備業"}


def norm(x):
    x = (x or "").strip()
    if x.endswith("類") and x != "其他類":
        x = x[:-1]
    if x == "其他類":
        x = "其他"
    return ALIAS.get(x, x)


def git_show(ref, p):
    return subprocess.run(["git", "-C", REPO, "show", f"{ref}:{p}"], capture_output=True, text=True, check=True).stdout


def rows(name):
    return list(csv.DictReader(io.open(os.path.join(HERE, name), encoding="utf-8")))


def day_before(d):
    import datetime
    return (datetime.date.fromisoformat(d) - datetime.timedelta(days=1)).isoformat()


def first_seen(ref):
    """日 K（早年段＋主庫）裡每檔在各市場第一次出現的日子 ⇒ {market: {sid: date}}，以及各市場資料起點。
    ⚠ industry.csv 的 listed_date：上櫃全空；上市是【主板】上市日（創新板轉主板的比實際交易晚，例 6873）。"""
    files = {}
    for tree in ("data/early/daily", "data/universe/daily"):
        for ln in subprocess.run(["git", "-C", REPO, "ls-tree", ref, tree + "/"], capture_output=True, text=True).stdout.splitlines():
            meta, path = ln.split("\t")
            b = path.rsplit("/", 1)[1]
            if b.endswith(".csv") and b[:4].isdigit():
                files.setdefault(b[:-4], meta.split()[2])
    p = subprocess.Popen(["git", "-C", REPO, "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    first, lo = {"twse": {}, "tpex": {}}, {}
    for d in sorted(files):
        p.stdin.write((files[d] + "\n").encode()); p.stdin.flush()
        n = int(p.stdout.readline().split()[2])
        body = p.stdout.read(n); p.stdout.read(1)
        for r in csv.DictReader(io.StringIO(body.decode("utf-8"))):
            mk = r.get("market")
            if mk in first:
                lo.setdefault(mk, d)
                first[mk].setdefault(r["stock_id"], d)
    p.stdin.close()
    return first, lo


def walk(sid, name, mk, cur, end, basis, evs, lo_day, out, breaks, stats):
    """從 cur（end 那天的類別）往回走到 lo_day（不含）；回傳走完時的 (cur, end, basis)。"""
    cand = [(e[0], "x", e) for e in evs if (not lo_day or e[0] > lo_day) and (not end or e[0] <= end)]
    for d, k in (("2023-07-03", "r"),) + ((("2007-07-02", "b"),) if mk == "twse" else ()):
        if (not lo_day or d > lo_day) and (not end or d <= end):
            cand.append((d, k, None))
    cand.sort(key=lambda t: (t[0], t[1] == "x"), reverse=True)   # 同一天：逐檔先於整批
    done_day = set()
    for d, kind, e in cand:
        if kind == "x":
            eff, fr, to, emk, b, _ = e
            if to != cur and not (to == "觀光事業" and cur == "觀光餐旅"):
                breaks.append((sid, name, eff, f"公告新類別 {to} ≠ 當下 {cur}", emk))
            out.append((sid, mk, cur, eff, end, basis))
            cur, end, basis = fr, day_before(eff), b
            done_day.add(eff)
            stats[b] += 1
        elif kind == "r" and cur == "觀光餐旅" and d not in done_day:
            out.append((sid, mk, cur, d, end, basis))
            cur, end, basis = "觀光事業", day_before(d), "rename_2023"
            stats["rename_2023"] += 1
        elif kind == "b" and d not in done_day and (cur in ELEC or cur in CHEM):
            stats["bulk_2007_" + ("elec" if cur in ELEC else "chem")] += 1
            out.append((sid, mk, cur, d, end, basis))
            cur, end, basis = ("電子工業" if cur in ELEC else "化學生技醫療"), day_before(d), "bulk_2007"
    return cur, end, basis


def close(sid, mk, cur, end, basis, start, out):
    cov = COVER[mk]
    if start and start >= cov:
        out.append((sid, mk, cur, start, end, basis))
    elif not end or end >= cov:
        out.append((sid, mk, cur, cov, end, basis))
        out.append((sid, mk, cur, start, day_before(cov), "pre_coverage"))
    else:
        out.append((sid, mk, cur, start, end, "pre_coverage"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="origin/main")
    a = ap.parse_args()
    fs, lo = first_seen(a.ref)
    anchor = {}
    for r in csv.DictReader(io.StringIO(git_show(a.ref, "data/meta/industry.csv"))):
        mk = r["market"]
        if mk not in ("twse", "tpex"):
            continue
        nm = r["industry_name"] or {"32": "文化創意業", "33": "農業科技業"}.get(r["industry_code"], "")
        ld = r["listed_date"]
        ld = f"{ld[:4]}-{ld[4:6]}-{ld[6:8]}" if len(ld) == 8 and ld.isdigit() else ""
        f = fs[mk].get(r["stock_id"], "")
        if f and f > lo[mk]:                  # 日 K 第一天就在的 ⇒ 實際起點早於資料，照 listed_date
            ld = min(ld, f) if ld else f
        anchor[r["stock_id"]] = (mk, norm(nm), r["name"], ld)
    ch = collections.defaultdict(list)          # sid -> [(eff, from, to, market, basis, name)]
    for mk, fn in (("twse", "twse_changes.csv"), ("tpex", "tpex_changes.csv")):
        for r in rows(fn):
            if r["stock_id"]:
                ch[r["stock_id"]].append((r["effective_date"], norm(r["from_industry"]), norm(r["to_industry"]), mk, "change", r["name"]))
    for r in rows("twse_2007_split_inferred.csv"):
        ch[r["stock_id"]].append((r["effective_date"], norm(r["from_industry"]), norm(r["to_industry"]), "twse", "inferred_2007", r["name"]))
    no_id = sum(1 for fn in ("twse_changes.csv", "tpex_changes.csv") for r in rows(fn) if not r["stock_id"])

    out, breaks, stats = [], [], collections.Counter()
    for sid, (mk, cur, name, ld) in sorted(anchor.items()):
        evs = ch.get(sid, [])
        cur, end, basis = walk(sid, name, mk, cur, "", "anchor", [e for e in evs if e[3] == mk or not ld or e[0] > ld],
                               ld, out, breaks, stats)
        # 上櫃轉上市：上市日以前的上櫃期間另走一段（起點＝轉上市當下的類別，⚠ 假設轉市場時類別沒變，除非上櫃公告另有記載）
        ft = fs["tpex"].get(sid, "")
        if mk == "twse" and ld and ft and ft < ld:
            stats["otc_to_twse"] += 1
            t_lo = ft if ft > lo["tpex"] else ""
            c2, e2, b2 = walk(sid, name, "tpex", cur, day_before(ld), "transfer_assumed",
                              [e for e in evs if e[3] == "tpex" and e[0] < ld], t_lo, out, breaks, stats)
            close(sid, "tpex", c2, e2, b2, t_lo, out)
            close(sid, mk, cur, end, basis, ld, out)
        else:
            close(sid, mk, cur, end, basis, ld, out)
    stats["chain_break"] = len(breaks)
    # 已下市（不在錨點）但在異動清單出現過的：只給公告段
    dels = []
    for sid, evs in ch.items():
        if sid in anchor:
            continue
        evs = sorted(evs)
        for i, e in enumerate(evs):
            nxt = day_before(evs[i + 1][0]) if i + 1 < len(evs) else ""
            dels.append((sid, e[3], e[2], e[0], nxt, "delisted_" + e[4]))
            if i == 0:
                dels.append((sid, e[3], e[1], "", day_before(e[0]), "delisted_before_first_change"))
    out = sorted(set(out + dels), key=lambda t: (t[0], t[3]))
    with io.open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["stock_id", "market", "industry", "start", "end", "basis"])
        w.writerows(out)

    # ── 驗收
    print(f"錨點 {len(anchor)} 檔｜異動（有代號）{sum(len(v) for v in ch.values())} 筆、無代號 {no_id} 筆｜輸出 {len(out)} 段 ⇒ {OUT}")
    print("事件計數：", dict(stats))
    print(f"⭐ 鏈斷（公告新類別 ≠ 當下類別）{len(breaks)}：", breaks[:30])

    def members(day, mk, ind):
        return sum(1 for r in out if r[1] == mk and r[2] == ind and (r[3] or "0000") <= day and (not r[4] or day <= r[4])
                   and not r[5].startswith("delisted"))
    print("2007-07-01 上市 電子工業（官方 304，含之後下市者）：", members("2007-07-01", "twse", "電子工業"),
          "｜化學生技醫療（官方 32）：", members("2007-07-01", "twse", "化學生技醫療"))
    print("2007-07-02 上市 八子類合計：", sum(members("2007-07-02", "twse", x) for x in ELEC))
    for mk, cats in (("twse", ("綠能環保", "數位雲端", "運動休閒", "居家生活")), ("tpex", ("綠能環保", "數位雲端", "運動休閒", "居家生活"))):
        print(f"2023-07-03 {mk} 新類別成員（官方首批見 new_categories.csv）：",
              {c: members("2023-07-03", mk, c) for c in cats})
    ov = collections.Counter()
    for sid, (mk, cur, name, ld) in anchor.items():
        segs = sorted([r for r in out if r[0] == sid], key=lambda t: t[3])
        for x, y in zip(segs, segs[1:]):
            if x[4] and y[3] and x[4] >= y[3]:
                ov["overlap"] += 1
    print("同檔段落重疊：", ov["overlap"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
