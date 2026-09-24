#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""大盤三大法人【金額】回補的交件驗收：裁定線 20260924-1941 §三 的五項。

⛔ 這一支【只讀】：不連網、不寫 `data/`。它是交件時附的那一份報告，
  ⚠ 不是每日閘門（每日的守門在 `freshness_check.py` 與 `crosscheck.py`）。

五項（逐字照裁定線 1941 §三）：
  ① 覆蓋　　逐日對 calendar，報應有／實有／缺哪幾天
  ② 對帳　　合計列 ＝ 成分列加總；與現有 `market_inst.csv` 重疊期逐位元比
  ③ 單位　　抽幾個年份再做一次量級夾（⛔ 不只九月）
  ④ 列名變化　印全期出現過的列名集合與各自起訖日
  ⑤ 新鮮度守門　補完後也要涵蓋（這一項只查「守門有沒有掛上」，⛔ 不代替它跑）

⭐⭐ 這一支最要緊的一件事，是【父列不一定叫「合計」】：

    上櫃 2017-01-03 ~ 2018-01-11 那一代的列名是
        投信／自營商／自營商(自行買賣)／自營商(避險)
    ⇒ `自營商` 是父列，⛔ 而它的名字裡【沒有「合計」兩個字】
      （本線 2026-09-24 用真回應驗過：2017-01-03 的 621,619,316
        ＝ 239,280,070 ＋ 382,339,246）
    ⇒ ⛔⛔ 所以「把不帶『合計』的列加起來」會【重複計算】，
      ⚠ 而它加得出一個看起來合理的數字 ⇒ 不會有人發現。
    ⇒ ⭐ 因此這一支用【明列的恆等式表】（`IDENTITIES`）：
      每一個父列都要在表上，⛔ 表上沒有的列名一律報 ✗，
      ⚠ 而不是「認不得就跳過」——認不得就跳過等於把新代靜靜漏掉。

⚠ 同一段還有兩件要一起講（都不是「抓取失敗」，⛔ 但長得像資料完整）：
  ・上櫃 2017-01-03 ~ 2018-01-11 **整段沒有外資**，也沒有總計列
    ⇒ 那一段的「三大法人」其實只有兩大法人。
  ・2018-01-12（TWSE 有開市）上櫃端點回 stat=ok ＋ **0 列**，
    重問三次都一樣 ⇒ 是【端點的洞】，⛔ 不是我方漏抓。
"""
import argparse
import csv
import io
import os
import sys

# ── 恆等式表 ────────────────────────────────────────────────────────────
#   (父列, [子列…])。⭐ 一天之內【父與所有子都在】才驗；少一個就記成「不適用」。
#   ⛔ 不要用「名字裡有沒有合計」去推——`自營商` 那一條就是反例。
IDENTITIES = {
    "instamt": [
        # 上市 BFI82U 是【平的】：只有一個總計列，成分就是其餘全部。
        # ⇒ 用「總計列 ＝ 其餘列加總」表示（見 TOTALS / 下面的 _flat_check）。
    ],
    "otcinstamt": [
        ("外資及陸資合計", ["外資及陸資(不含自營商)", "外資自營商"]),
        ("自營商合計", ["自營商(自行買賣)", "自營商(避險)"]),
        # ⭐ 舊代（2017-01-03 ~ 2018-01-11）的父列，名字裡沒有「合計」
        ("自營商", ["自營商(自行買賣)", "自營商(避險)"]),
        # ⛔⛔ 總計列【不含外資自營商】——官方附註逐字（上市、上櫃兩站相同）：
        #   「因外資自營商買賣金額已計入自營商買賣金額，故不納入三大法人買賣金額之合計數計算。」
        #   ⇒ 所以是「外資及陸資(不含自營商)」，⛔ 不是「外資及陸資合計」
        #   ⇒ ⚠ 外資自營商大多數日子是 0 ⇒ 兩種寫法絕大多數天一樣，只有它不為 0 的那幾天會露出來
        ("三大法人合計*", ["外資及陸資(不含自營商)", "投信", "自營商合計"]),
    ],
}

#   總計列的名字（⛔ 逐字，不做模糊比對：`三大法人合計*` 後面那個星號是官方寫的）
TOTALS = {"instamt": ["合計"], "otcinstamt": ["三大法人合計*"]}

#   ⭐ 上市是平的 ⇒ 總計列 ＝ 其餘列加總【扣掉 FLAT_EXCLUDE】（⛔ 上櫃不可以這樣算：它有巢狀子列）
FLAT = {"instamt": True, "otcinstamt": False}

#   ⛔⛔ 不納入總計的列（官方附註逐字，BFI82U 的 notes）：
#     「因外資自營商買賣金額已計入自營商買賣金額，故不納入三大法人買賣金額之合計數計算。」
#   ⇒ 2026-09-25 本線第一版把它加進去 ⇒ 全期驗收 ② 紅 4,623 條（從 2018-01-17 起）
#     ⇒ 2018-01-17 外資自營商賣出 73,970 元，差額剛好 −73,970 ⇒ ⭐ 錯的是驗收，⛔ 不是資料
#   ⚠ 而這一列大多數日子是 0 ⇒ 只驗 2026 年那幾天的自測【看不出】這個錯（第一版 12 格全綠）
FLAT_EXCLUDE = {"instamt": {"外資自營商"}, "otcinstamt": set()}

#   已知列名（⛔ 表上沒有的一律報出來：新代混進來要被看見，不是被忽略）
KNOWN = {
    "instamt": {"自營商", "自營商(自行買賣)", "自營商(避險)", "投信",
                "外資", "外資及陸資", "外資及陸資(不含外資自營商)", "外資自營商",
                "合計"},
    "otcinstamt": {"外資及陸資合計", "外資及陸資(不含自營商)", "外資自營商",
                   "投信", "自營商合計", "自營商", "自營商(自行買賣)",
                   "自營商(避險)", "三大法人合計*"},
}

#   ② 逐位元比對用：`latest/market_inst.csv` 的四欄各自對應哪一列。
#   ⚠ 它只有上市、只有 2026-09-01 起 ⇒ 只在重疊期比。
#   ⭐ `foreign` 對到【兩列相加】（與個股表同一個口徑，本線 20260924-2136 已答）。
MK_MAP = [
    ("foreign", ["外資及陸資(不含外資自營商)", "外資自營商"]),
    ("trust", ["投信"]),
    ("dealer", ["自營商(自行買賣)", "自營商(避險)"]),
    ("total", ["合計"]),
]


def _n(v):
    """'1,234' → 1234（int）。空白／'--' → None。⛔ 不回 0：0 是合法的值。"""
    s = str(v).replace(",", "").strip()
    if s in ("", "-", "--", "None"):
        return None
    try:
        return int(s)
    except ValueError:
        try:
            return int(round(float(s)))
        except ValueError:
            return None


def load_feed(root, feed):
    """→ {date: {investor: (buy, sell, net)}}。⛔ 只讀已經落地的檔。"""
    d = os.path.join(root, "universe", feed)
    out = {}
    if not os.path.isdir(d):
        return out
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".csv"):
            continue
        day = fn[:-4]
        with io.open(os.path.join(d, fn), encoding="utf-8") as f:
            rows = {}
            for r in csv.DictReader(f):
                rows[r["investor"]] = (_n(r["buy"]), _n(r["sell"]), _n(r["net"]))
        out[day] = rows
    return out


def load_calendar(root, which="twse"):
    p = os.path.join(root, "meta", "calendar_%s.csv" % which)
    if not os.path.exists(p):
        return []
    with io.open(p, encoding="utf-8") as f:
        return [r["date"] for r in csv.DictReader(f) if r.get("date")]


# ── ① 覆蓋 ──────────────────────────────────────────────────────────────
def sec_coverage(data, cal, feed, floor, note):
    print()
    print("① 覆蓋（逐日對 calendar_twse）")
    if not data:
        print("   ⛔ %s 一個檔都沒有 ⇒ 下面四項全部不適用" % feed)
        return False
    have = sorted(data)
    lo, hi = have[0], have[-1]
    want = [d for d in cal if max(lo, floor) <= d <= hi]
    miss = [d for d in want if d not in data]
    extra = [d for d in have if d not in set(cal)]
    print("   實有 %d 天：%s … %s" % (len(have), lo, hi))
    print("   應有 %d 天（calendar_twse ∩ [%s, %s]）" % (len(want), max(lo, floor), hi))
    print("   缺 %d 天%s" % (len(miss), ("：" + "、".join(miss[:40])
                                         + ("… 等" if len(miss) > 40 else "")) if miss else ""))
    if extra:
        # ⚠ 我方有、日曆沒有 ⇒ 不是「多抓」就是日曆自己缺 ⇒ 兩種都要看，⛔ 不可忽略
        print("   ⚠ 我方有而 calendar_twse 沒有的 %d 天：%s"
              % (len(extra), "、".join(extra[:20])))
    if note:
        print("   ⚠ %s" % note)
    return not miss


# ── ② 對帳 ──────────────────────────────────────────────────────────────
def sec_recon(data, feed, root):
    print()
    print("② 對帳（合計列 ＝ 成分列加總）")
    unknown = {}
    bad = []
    checked = 0
    na = 0
    for day in sorted(data):
        rows = data[day]
        for who in rows:
            if who not in KNOWN[feed]:
                unknown.setdefault(who, []).append(day)
        # 明列的恆等式
        for parent, kids in IDENTITIES[feed]:
            if parent not in rows or any(k not in rows for k in kids):
                continue
            for j, lab in enumerate(("buy", "sell", "net")):
                p = rows[parent][j]
                ks = [rows[k][j] for k in kids]
                if p is None or any(x is None for x in ks):
                    na += 1
                    continue
                checked += 1
                if p != sum(ks):
                    bad.append((day, parent, lab, p, sum(ks)))
        # 上市：總計 ＝ 其餘全部
        if FLAT[feed]:
            tot = [t for t in TOTALS[feed] if t in rows]
            if len(tot) == 1:
                t = tot[0]
                comp = [w for w in rows if w != t and w not in FLAT_EXCLUDE[feed]]
                for j, lab in enumerate(("buy", "sell", "net")):
                    p = rows[t][j]
                    ks = [rows[w][j] for w in comp]
                    if p is None or any(x is None for x in ks):
                        na += 1
                        continue
                    checked += 1
                    if p != sum(ks):
                        bad.append((day, t + "(平)", lab, p, sum(ks)))
    print("   驗了 %d 條恆等式（另有 %d 條因為缺值不適用）" % (checked, na))
    if bad:
        print("   ✗ 不成立 %d 條，前 10 條：" % len(bad))
        for x in bad[:10]:
            print("       %s %s %s：父 %d vs 子和 %d（差 %d）"
                  % (x[0], x[1], x[2], x[3], x[4], x[3] - x[4]))
    else:
        print("   ok 全部成立")
    if unknown:
        print("   ✗ 表上沒有的列名 %d 種（⛔ 不是跳過，是要有人去看）：" % len(unknown))
        for who in sorted(unknown):
            ds = unknown[who]
            print("       %r　%d 天　%s … %s" % (who, len(ds), ds[0], ds[-1]))
    else:
        print("   ok 沒有表外的列名")
    ok2 = _recon_market_inst(data, feed, root)
    return (not bad) and (not unknown) and ok2


def _recon_market_inst(data, feed, root):
    """與現有 `latest/market_inst.csv` 重疊期【逐位元】比。⛔ 只對上市。"""
    if feed != "instamt":
        print("   （與 market_inst.csv 的比對只對上市 ⇒ 這一支跳過）")
        return True
    p = os.path.join(root, "latest", "market_inst.csv")
    if not os.path.exists(p):
        print("   ⚠ 沒有 latest/market_inst.csv ⇒ 無法比對")
        return True
    with io.open(p, encoding="utf-8") as f:
        mk = {r["date"]: r for r in csv.DictReader(f)}
    ov = sorted(set(mk) & set(data))
    print("   重疊期 %d 天%s" % (len(ov), ("：%s … %s" % (ov[0], ov[-1])) if ov else ""))
    if not ov:
        return True
    diff = []
    for day in ov:
        rows = data[day]
        for col, srcs in MK_MAP:
            if any(s not in rows for s in srcs):
                diff.append((day, col, "缺列 " + "／".join(s for s in srcs if s not in rows), ""))
                continue
            mine = sum(rows[s][2] for s in srcs)       # net
            theirs = _n(mk[day].get(col))
            if theirs is None or mine != theirs:
                diff.append((day, col, mine, theirs))
    if diff:
        print("   ✗ 不同 %d 格，前 10 格：" % len(diff))
        for x in diff[:10]:
            print("       %s %s：本次回補 %s vs market_inst %s" % x)
    else:
        print("   ok %d 天 × %d 欄【逐格相同】" % (len(ov), len(MK_MAP)))
    return not diff


# ── ③ 單位（量級夾，抽年份）────────────────────────────────────────────
def sec_unit(data, feed, root, market):
    """法人買進＋賣出 ÷ 當日【該市場】成交金額（元）。

    ⭐ 這一夾量的是【量級】：若金額其實是「千元」，比值會掉到千分之一。
    ⛔ 它夾不出元 vs 角，⛔ 也不是逐位元對帳（那一項在 ② ）。
    """
    print()
    print("③ 單位（量級夾，逐年抽樣）")
    tot = TOTALS[feed][0]
    years = sorted({d[:4] for d in data})
    n_ok = n_all = 0
    for y in years:
        days = [d for d in sorted(data) if d.startswith(y) and tot in data[d]]
        picked = None
        for d in days:                      # 取該年【第一個算得出來】的交易日
            amt = _market_amount(root, d, market)
            if amt:
                picked = (d, amt)
                break
        if not picked:
            print("   %s　⚠ 該年沒有一天算得出全市場成交金額（daily 檔缺）" % y)
            continue
        d, amt = picked
        buy, sell, _net = data[d][tot]
        if buy is None or sell is None:
            print("   %s　⚠ %s 總計列缺值" % (y, d))
            continue
        r = (buy + sell) / float(amt)
        n_all += 1
        ok = 0.02 <= r <= 2.0
        n_ok += ok
        print("   %s　%s　法人買+賣 %s ÷ 全市場成交額 %s ＝ %.4f%s"
              % (y, d, "{:,}".format(buy + sell), "{:,}".format(amt), r,
                 "" if ok else "　✗ 落在 [0.02, 2.0] 之外"))
    print("   ⇒ %d／%d 個年份落在量級帶內（若單位是千元，比值會是千分之一）"
          % (n_ok, n_all))
    return n_all > 0 and n_ok == n_all


def _market_amount(root, day, market):
    p = os.path.join(root, "universe", "daily", day + ".csv")
    if not os.path.exists(p):
        return None
    s = 0
    with io.open(p, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if (r.get("market") or "").strip() != market:
                continue
            v = _n(r.get("amount"))
            if v:
                s += v
    return s or None


# ── ④ 列名變化 ─────────────────────────────────────────────────────────
def sec_names(data):
    print()
    print("④ 列名變化（全期出現過的列名與各自起訖日）")
    first, last, cnt = {}, {}, {}
    sig_runs = []
    prev = None
    for day in sorted(data):
        for who in data[day]:
            first.setdefault(who, day)
            last[who] = day
            cnt[who] = cnt.get(who, 0) + 1
        sig = tuple(sorted(data[day]))
        if sig != prev:
            sig_runs.append([day, day, sig])
            prev = sig
        else:
            sig_runs[-1][1] = day
    for who in sorted(first, key=lambda w: (first[w], w)):
        print("   %-26s %s … %s　（%d 天）" % (who, first[who], last[who], cnt[who]))
    print("   ⇒ 列名組合換過 %d 次：" % (len(sig_runs) - 1))
    for a, b, sig in sig_runs:
        print("       %s … %s　%d 列：%s" % (a, b, len(sig), "／".join(sig)))
    return True


# ── ⑤ 新鮮度守門 ────────────────────────────────────────────────────────
def sec_freshness(feed, here):
    print()
    print("⑤ 新鮮度守門（補完後也要涵蓋）")
    p = os.path.join(here, "freshness_check.py")
    if not os.path.exists(p):
        print("   ⚠ 找不到 freshness_check.py")
        return False
    src = io.open(p, encoding="utf-8").read()
    hit = ('"%s"' % feed) in src or ("'%s'" % feed) in src
    print("   freshness_check.py 有沒有掛 %s：%s" % (feed, "ok 有" if hit else "✗ 沒有"))
    print("   ⚠ 這一格只查【守門掛上了沒有】，⛔ 不代替它跑一次")
    return hit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None, help="data 目錄（預設：本檔旁的 data/）")
    ap.add_argument("--feed", default="instamt", choices=["instamt", "otcinstamt"])
    a = ap.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))
    root = a.root or os.path.join(here, "data")
    feed = a.feed

    # ⭐ 逐支的「已知下限」與必須一起講的那句話（⛔ 不是註解，是要印在報告上的）
    if feed == "instamt":
        floor, market = "2004-03-03", "twse"
        note = ("上市端點自己講的回溯下限是民國 093-03-03；"
                "本次回補的起日見下面的『實有』，⛔ 起日以前不算『缺』")
    else:
        floor, market = "2017-01-03", "tpex"
        note = ("上櫃回溯下限 2017-01-03（二分找出來）；"
                "⛔⛔ 而 2017-01-03 ~ 2018-01-11 那一段【沒有外資也沒有總計列】，"
                "2018-01-12 端點回 stat=ok ＋ 0 列（重問三次一樣）⇒ 那是端點的洞；"
                "⚠ calendar_tpex.csv 只有 2026-09 起 ⇒ 這裡拿 calendar_twse 當母體")

    data = load_feed(root, feed)
    cal = load_calendar(root, "twse")
    print("=" * 72)
    print("大盤三大法人金額　交件驗收（裁定線 20260924-1941 §三）｜feed=%s" % feed)
    print("root=%s｜calendar_twse %d 天" % (root, len(cal)))
    print("=" * 72)

    res = [("① 覆蓋", sec_coverage(data, cal, feed, floor, note))]
    if data:
        res.append(("② 對帳", sec_recon(data, feed, root)))
        res.append(("③ 單位", sec_unit(data, feed, root, market)))
        res.append(("④ 列名", sec_names(data)))
    res.append(("⑤ 守門", sec_freshness(feed, here)))

    print()
    print("=" * 72)
    for k, v in res:
        print("   %s　%s" % ("ok  " if v else "✗   ", k))
    bad = [k for k, v in res if not v]
    print("⇒ %d／%d 項通過%s" % (len(res) - len(bad), len(res),
                                 "" if not bad else "　⛔ 未過：" + "、".join(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
