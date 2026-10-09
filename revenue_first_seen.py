#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""月營收【首次出現時點】逐趟累積 ⇒ data/meta/revenue_seen/<期別>/<台北時戳>.csv

    python revenue_first_seen.py [--period YYYY-MM] [--sleep 3]
    python revenue_first_seen.py --summary [--period YYYY-MM]   ⇒ 印出 period,stock_id,market,part,first_seen_at,censored（不寫檔）

## 為什麼（2026-10-09，台股 1542 §五 ⑤）
MOPS 沒有任何端點給「逐家逐月營收申報日」（t05st10_ifrs、t146sb05、doc.twse t57sb01 都沒有；
t21sc03 彙總表只有整表出表日期）；git 歷史推也不行（OpenAPI 整批發佈）。
⇒ 唯一的路：每月 1～20 日，跟著 daily 兩班（台北 18:23、23:47）打 mopsov t21sc03（sii／otc × 國內／外國 4 發），
   記下每家公司【第一次出現在表上】的時點 ⇒ 申報日的上界（精度約半天；漏跑幾班就晚幾班）。
⛔ 只能從開始累積那天往後；過去的申報日補不回來。
⛔ first_seen 是「本庫第一次看到」，⛔ 不是公司的申報時刻。

## 檔案設計（⭐ 防合併覆蓋）
每一趟只寫【一個新檔】，只放「這一期既有檔都還沒出現過」的公司 ⇒ 檔名不重複、push_data 不會互蓋。
首次出現時點＝該公司所有檔的【最小】時戳（工作樹舊、重記了也沒關係，取最小就對）。
某期的第一趟（該期還沒有任何檔）檔名加 `_first` ⇒ 那一趟看到的公司 censored＝1（實際申報可能更早）。
欄位：stock_id, market（sii／otc）, part（0 國內／1 外國）, revenue（當時表上的當月營收，千元）
"""
import argparse, csv, datetime, glob, io, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mops_history as M      # noqa: E402  ⭐ 沿用 rev_url／_fetch／parse_revenue（同一份實作）

BASE = os.path.join(HERE, "data", "meta", "revenue_seen")
TPE = datetime.timezone(datetime.timedelta(hours=8))
HDR = ["stock_id", "market", "part", "revenue"]


def target_period(now):
    """每月 1～20 日 ⇒ 上個月；其他日子 ⇒ None（不打）。"""
    if now.day > 20:
        return None
    y, m = (now.year, now.month - 1) if now.month > 1 else (now.year - 1, 12)
    return "%04d-%02d" % (y, m)


def files_of(per):
    return sorted(glob.glob(os.path.join(BASE, per, "*.csv")))


def stamp_of(path):
    b = os.path.basename(path)[:-4]
    return b.replace("_first", ""), b.endswith("_first")


def summary(per):
    """→ {stock_id: (first_seen_at, censored, market, part)}；取各檔最小時戳。"""
    best = {}
    for p in files_of(per):
        st, first = stamp_of(p)
        with io.open(p, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                k = r["stock_id"]
                if k not in best or st < best[k][0]:
                    best[k] = (st, 1 if first else 0, r["market"], r["part"])
    return best


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--period")
    ap.add_argument("--sleep", type=float, default=3.0)
    ap.add_argument("--summary", action="store_true")
    a = ap.parse_args(argv)
    now = datetime.datetime.now(TPE)
    per = a.period or target_period(now)
    if a.summary:
        pers = [per] if per else sorted(os.listdir(BASE)) if os.path.isdir(BASE) else []
        w = csv.writer(sys.stdout, lineterminator="\n")
        w.writerow(["period", "stock_id", "market", "part", "first_seen_at", "censored"])
        for pp in pers:
            for k, (st, c, mk, pt) in sorted(summary(pp).items(), key=lambda x: (x[1][0], x[0])):
                w.writerow([pp, k, mk, pt, st, c])
        return 0
    if not per:
        print("[revenue_first_seen] 今天 %s 不在每月 1～20 日 ⇒ 不打" % now.date())
        return 0
    y, m = int(per[:4]), int(per[5:7])
    roc = y - 1911
    have = set(summary(per))
    first = not files_of(per)
    new, ok, fail = [], 0, 0
    seen_now = set()
    for market in ("sii", "otc"):
        for part in M.REV_PARTS:
            raw, err = M._fetch(M.rev_url(market, roc, m, part))
            time.sleep(a.sleep)
            if err or not raw:
                if err and "404" in err:          # 月初還沒有任何公司申報時整頁 404 ⇒ 不算失敗
                    ok += 1
                    continue
                fail += 1
                print("[revenue_first_seen] ⛔ %s %s part%s：%s" % (per, market, part, err))
                continue
            got, header, note, _skip = M.parse_revenue(raw, roc, m, market)
            ci = header.index("當月營收") if header and "當月營收" in header else None
            ok += 1
            for r in got:
                if r[0] in have or r[0] in seen_now:
                    continue
                seen_now.add(r[0])
                new.append([r[0], market, part, (r[ci + 1] if ci is not None and ci + 1 < len(r) else "")])
            print("[revenue_first_seen] %s %s part%s：%s" % (per, market, part, note))
    if new:
        os.makedirs(os.path.join(BASE, per), exist_ok=True)
        name = now.strftime("%Y-%m-%dT%H%M%S") + ("_first" if first else "") + ".csv"
        with io.open(os.path.join(BASE, per, name), "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(HDR)
            w.writerows(sorted(new))
    print("[revenue_first_seen] %s｜本趟新記 %d 家%s｜成功 %d／失敗 %d" % (per, len(new), "（該期首趟 ⇒ censored）" if first and new else "", ok, fail))
    return 1 if fail and not ok else 0


if __name__ == "__main__":
    sys.exit(main())
