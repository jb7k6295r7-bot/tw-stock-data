# -*- coding: utf-8 -*-
"""現金增資決議／可轉換公司債發行決議 事件表（重大訊息主旨分類）⇒ seo_cb_events.csv

    python3 curated/seo_cb_events/build.py [--ref origin/main] [--sample 50]

依據：裁定 seq399 §四.1（核：用 news 主旨做事件表，現增決議／可轉債發行決議兩類、含已下市；濾雜訊規則先寫死再跑；交件附規則與隨機 50 則人工核對）。
來源：公開庫 `data/mops/news/<年>.csv`（MOPS 重大訊息主旨，1999 起全市場，含已下市）；只收 market ∈ {sii, otc}。
⛔ 事件層只用日期與代號；金額、價格等要讀內文（已下市公司讀不到）⇒ 用到內文欄位的分析要標存活者偏差。

## 規則（2026-10-20 寫死；主旨先去掉所有空白——原檔有斷行空格，如「現金 增資」）
共同排除（任一命中即不收）：
  代(重要)?子公司｜子公司｜孫公司｜轉投資｜被投資｜認購｜參與 ⇒ 不是本公司自己的
  更正｜補正｜補充｜變更｜不繼續｜撤銷｜取消｜停止｜延後｜終止｜修正 ⇒ 不是新的決議
現增（class=seo）：含「決議」且含「現金增資」或「現增」；排除 盈餘轉增資｜公積轉增資｜員工酬勞；
  只講基準日的排除（含「基準日」但不含「辦理」「發行新股」）。私募 ⇒ private=1。
可轉債（class=cb）：含「決議」且含「轉換公司債」且含 發行｜募集｜辦理；
  排除 轉換價格｜賣回｜贖回｜重設｜停止轉換｜資金運用｜資金用途｜發行條件。海外 ⇒ overseas=1；私募 ⇒ private=1。
⭐ v2（同日人工核對第一輪 50 則後加；第一輪誤收 4 則＋上市櫃前承銷 6 則）：共同排除再加 更新｜資金運用｜用途｜進度｜買回｜發行價格｜訂價｜定價；
  現增另標 ipo=1（初次上市／上櫃、上市櫃前、掛牌前、公開承銷）＝上市櫃前承銷用的現增，⛔ 不是已上市公司的現增，事件研究要排除。
⭐ v3（第二輪另抽 50 則：47 則對＝94%；誤收 6642「修訂現金增資案」、ipo 漏標 3169「股票上櫃辦理現金增資」）：
  共同排除加 修訂；ipo 再加 股票上市辦理｜股票上櫃辦理。⚠ 已知殘留：「決議訂定…私募現金增資…之事宜」（細節訂定、非新案）仍會收（例 2537 2008-03-12）。
同一代號、同一 class，30 個日曆天內只留第一則（後面的多半是同一案的重發）。
輸出欄：date, time, stock_id, name, market, class, private, overseas, subject（原文）, serial
"""
import argparse, csv, datetime, io, os, random, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(HERE, "seo_cb_events.csv")
SAMPLE = os.path.join(HERE, "sample50.csv")
EXC_ALL = re.compile(r"子公司|孫公司|轉投資|被投資|認購|參與|更正|補正|補充|變更|不繼續|撤銷|取消|停止|延後|終止|修正|修訂|更新|資金運用|用途|進度|買回|發行價格|訂價|定價")
IPO = re.compile(r"初次上市|初次上櫃|上市前|上櫃前|掛牌前|公開承銷|上市現金增資|上櫃現金增資|股票上市辦理|股票上櫃辦理")
EXC_SEO = re.compile(r"盈餘轉增資|公積轉增資|員工酬勞")
EXC_CB = re.compile(r"轉換價格|賣回|贖回|重設|停止轉換|資金運用|資金用途|發行條件")


def classify(subj):
    s = re.sub(r"\s+", "", subj)
    if "決議" not in s or EXC_ALL.search(s):
        return None
    if "轉換公司債" in s and re.search(r"發行|募集|辦理", s) and not EXC_CB.search(s):
        return "cb", int("私募" in s), int("海外" in s), 0
    if re.search(r"現金增資|現增", s) and not EXC_SEO.search(s):
        if "基準日" in s and not re.search(r"辦理|發行新股", s):
            return None
        return "seo", int("私募" in s), 0, int(bool(IPO.search(s)))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="origin/main")
    ap.add_argument("--sample", type=int, default=50)
    ap.add_argument("--seed", type=int, default=20261021)
    a = ap.parse_args()
    files = subprocess.run(["git", "-C", REPO, "ls-tree", "--name-only", a.ref, "data/mops/news/"],
                           capture_output=True, text=True).stdout.split()
    hits = []
    for f in sorted(x for x in files if re.search(r"/\d{4}\.csv$", x)):
        t = subprocess.run(["git", "-C", REPO, "show", f"{a.ref}:{f}"], capture_output=True, text=True).stdout
        for r in csv.DictReader(io.StringIO(t)):
            if r.get("market") not in ("sii", "otc"):
                continue
            c = classify(r.get("subject", ""))
            if c:
                hits.append(dict(r, cls=c[0], private=c[1], overseas=c[2], ipo=c[3]))
    hits.sort(key=lambda r: (r["stock_id"], r["cls"], r["date"], r.get("time", "")))
    out, last = [], {}
    for r in hits:
        k = (r["stock_id"], r["cls"])
        d = datetime.date.fromisoformat(r["date"])
        if k in last and (d - last[k]).days <= 30:
            continue
        last[k] = d
        out.append(r)
    out.sort(key=lambda r: (r["date"], r.get("time", ""), r["stock_id"]))
    hdr = ["date", "time", "stock_id", "name", "market", "class", "private", "overseas", "ipo", "subject", "serial"]
    with io.open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n"); w.writerow(hdr)
        for r in out:
            w.writerow([r["date"], r.get("time", ""), r["stock_id"], r.get("name", ""), r["market"], r["cls"],
                        r["private"], r["overseas"], r["ipo"], r["subject"], r.get("serial", "")])
    random.seed(a.seed)
    smp = random.sample(out, min(a.sample, len(out)))
    with io.open(SAMPLE, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n"); w.writerow(["date", "stock_id", "class", "private", "overseas", "ipo", "subject", "manual"])
        for r in sorted(smp, key=lambda r: r["date"]):
            w.writerow([r["date"], r["stock_id"], r["cls"], r["private"], r["overseas"], r["ipo"], r["subject"], ""])
    by = {}
    for r in out:
        by.setdefault((r["date"][:4], r["cls"]), 0)
        by[(r["date"][:4], r["cls"])] += 1
    print(f"命中 {len(hits)}｜去重後 {len(out)}（seo {sum(1 for r in out if r['cls']=='seo')}、cb {sum(1 for r in out if r['cls']=='cb')}）")
    print("逐年 seo/cb：" + " ".join(f"{y}:{by.get((y,'seo'),0)}/{by.get((y,'cb'),0)}" for y in sorted({k[0] for k in by})))
    return 0


if __name__ == "__main__":
    sys.exit(main())
