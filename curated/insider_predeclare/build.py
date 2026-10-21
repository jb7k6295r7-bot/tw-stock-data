# -*- coding: utf-8 -*-
"""內部人持股轉讓事前申報（全市場月彙總）⇒ insider_predeclare_<西元年>.csv

    python3 curated/insider_predeclare/build.py [--from 92/05] [--to 115/09] [--markets sii,otc,rotc]
                                               [--sleep 4] [--cache DIR] [--ref origin/main]

依據：裁定 seq407（內部人持股轉讓事前申報月彙總表，sii／otc／rotc 三市場，含已下市）。
來源：MOPS 舊站「內部人持股轉讓事前申報彙總表」
  POST https://mopsov.twse.com.tw/mops/web/ajax_t56sb21
  body：step=1&TYPEK=<sii|otc|rotc>&year=<民國年>&smonth=MM&emonth=MM&sstep=1&firstin=true
  回 UTF-8 HTML 表格（每列 18 格），頁尾「總計：N筆」，不分頁；無資料回「無持股轉讓之情形」。
  資料 91/08 起，但 91/08～92/04 的股數欄全是 0 ⇒ 不收，從 92/05 起。
  ⚠ mopsov robots.txt disallow ⇒ 只在自有排程小量取：每發間隔 ≥ --sleep 秒、失敗重試 3 次（間隔 30 秒）。
  ⛔ 遇到驗證碼／「因為安全性考量」擋阻頁就立刻停（exit 3），不繞過。
## 規則
  - 一發＝一市場×半年（同一民國年內）；頁尾總計 > 3000 筆或解析列數 ≠ 總計 ⇒ 改逐月重抓這半年。
  - 每發驗收：解析列數＝頁尾「總計：N筆」，不等就記錄（結尾列出），不中斷。
  - 一列＝一筆申報（官方一列）；同一申報若分多種轉讓方式，官方在同格用 <br> 分行：
    method_raw 以「|」連接原文、method 正規化後以「+」連接、shares＝各方式股數合計、shares_split＝各方式股數以「|」連接（單一方式時空白）。
  - 數字去千分位轉整數；空白留空。民國日期轉西元 YYYY-MM-DD。
  - 去重：不同發之間若出現完全相同的列（重疊的發）只留一次；同一發內完全相同的列照官方保留（都算在總計內）。
## 方式正規化（method）
  一般交易→general、贈與→gift、信託→trust、鉅額（逐筆／配對）交易→block、盤後定價交易→afterhours、
  洽特定人→specific、轉讓私募股票→private_placement、辦理過額配售→overallotment、拍賣或標購之委託競價→auction、其他→other。
## 隱私處理（⛔ 本表進公開 repo，不放自然人姓名）
  - holder（申報人姓名）不輸出 ⇒ holder_key＝sha1("<stock_id>|<姓名原文>").hexdigest()[:12]（同公司同一人可串，不直接露名）。
  - transferee（受讓人）不輸出 ⇒ transferee_type：含「信託／銀行／商銀」→trust_bank；否則含「限制員工／員工」→employee_trust；
    否則含法人字樣（股份有限／有限公司／公司／基金會／協會／投資／財團法人／大學／株式會社／LIMITED／LTD／INC…）→org；其餘非空→individual；空白留空。
    transferee_org：只有 org／trust_bank 才填，且只放「機構名稱片段」——原文先在 受託／託管／保管／受／括號／破折號／頓號／等… 處切段，
    每段只取到最後一個法人字尾（股份有限公司、有限公司、(股)公司、銀行、商銀、基金會、證券、大學、LTD…）為止；
    沒有法人字尾的段（多半是自然人姓名，例「某某受託信託財產專戶」）整段丟掉；
    含 公益信託／家族／紀念／律師／會計師／財團法人／社團法人／基金會／文教／基金 的段也丟掉（常以自然人命名）；
    含同列申報人姓名的段也丟掉（例「某某一號控股股份有限公司」）。individual 一律空白。
  - role 只留身分字樣；若原文夾帶「某某之配偶」這類姓名，去掉「之」以前的文字（本次 0 列）。
  - change_note、valid_period_raw 只有日期與固定字樣（已全量檢查）。
## 輸出欄
  market, declare_date, stock_id, name, role（原文身分）, holder_key, method_raw, method, shares, shares_split, daily_max, transferee_type, transferee_org,
  hold_own, hold_trust, plan_own, plan_trust, after_own, after_trust, valid_period_raw, valid_start, valid_end,
  unfinished（是／空白）, change_note（異動情形原文，<br> 直接接起）
⛔ 可用日＝申報日 declare_date，⛔ 不是有效轉讓期間起日 valid_start。
"""
import argparse, collections, csv, hashlib, html, io, os, re, subprocess, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
URL = "https://mopsov.twse.com.tw/mops/web/ajax_t56sb21"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Referer": "https://mopsov.twse.com.tw/mops/web/t56sb21"}
SPLIT_OVER = 3000
BLOCK = re.compile(r"因為安全性考量|驗證碼|CAPTCHA|captcha|請輸入圖形")
HDR = ["market", "declare_date", "stock_id", "name", "role", "holder_key", "method_raw", "method", "shares", "shares_split",
       "daily_max", "transferee_type", "transferee_org", "hold_own", "hold_trust", "plan_own", "plan_trust", "after_own", "after_trust",
       "valid_period_raw", "valid_start", "valid_end", "unfinished", "change_note"]
METHOD = [("一般交易", "general"), ("贈與", "gift"), ("信託", "trust"), ("鉅額", "block"), ("盤後定價", "afterhours"),
          ("洽特定人", "specific"), ("私募", "private_placement"), ("過額配售", "overallotment"), ("拍賣", "auction"),
          ("標購", "auction")]


TB = re.compile(r"信託|銀行|商銀")
EMP = re.compile(r"限制員工|員工")
ORG = re.compile(r"股份有限|有限公司|公司|基金會|協會|投資|銀行|財團法人|社團法人|合作社|學校|大學|醫院|基金|文教|教育|慈善|教會|農會|委員會|株式會社|會社|[國島州群灣港]商|\(股\)|（股）|﹝股﹞|事業|企業|實業|集團|控股|創投|證券|保險|工業|科技|電子|國際"
                 r"|LIMITED|LTD|\bINC\b|CORP|\bL\.?L\.?C\b|\bL\.P\.|\bFUND|\bTRUST|\bBANK|HOLDING|INVEST|CAPITAL|PARTNER|COMPANY|GMBH|\bPTE\b|\bS\.A\.|\bB\.V\.|\bAG\b|\bCO\.", re.I)
STOCKCO = re.compile(r"\(股\)|（股）|﹝股﹞|\[股\]")
SEP = re.compile(r"受託保管|受託經管|受託經營|受託|託管|保管|受|[-－—–/、，;；()（）〈〉\[\]﹝﹞<>]|\s及|及|與|等")
SUFFIX = re.compile(r"^(.*(?:股份有限公司|有限公司|\x02公司|\x02|公司|商業銀行|銀行|商銀|信託局|信託部|基金會|協會|證券|株式會社|會社|分行|分公司|大學|醫院|教會|校友會|學校|^中信銀|^中國信託$|^遠銀"
                    r"|LIMITED|LTD\.?|INC\.?|CORPORATION|CORP\.?|L\.?L\.?C\.?|L\.P\.|COMPANY|CO\.|GMBH|PTE\.?|B\.V\.|S\.A\.|\bAG|HOLDINGS?|INVESTMENTS?|FUND|BANK))", re.I)
DROP = re.compile(r"公益信託|家族|紀念|律師|會計師|財團法人|社團法人|基金會|文教|基金")


def transferee_type(t):
    if not t:
        return ""
    if TB.search(t):
        return "trust_bank"
    if EMP.search(t):
        return "employee_trust"
    if ORG.search(t):
        return "org"
    return "individual"


def org_part(t, person=""):
    """只取出法人／機構名稱片段；片段外的文字（可能是自然人姓名）一律丟掉。"""
    s = STOCKCO.sub("\x02", t)
    out = []
    for seg in SEP.split(s):
        seg = seg.strip()
        if seg.startswith(("財團法人", "社團法人")):
            m = re.match(r"^(.*?(?:基金會|協會|學會|文教|教育|醫院|學校))", seg)
        else:
            m = SUFFIX.match(seg)
        if not m:
            continue
        p = m.group(1).strip().replace("\x02", "(股)")
        if len(p) < 3 or DROP.search(p) or p in out or (len(person) >= 2 and person in p):
            continue
        out.append(p)
    return "；".join(out)
ROLE_NAME = re.compile(r"^.+?之(?=配偶|未成年子女|利用他人名義)")


def holder_key(sid, holder):
    return hashlib.sha1(f"{sid}|{holder}".encode("utf-8")).hexdigest()[:12]


class Blocked(Exception):
    pass


def windows(frm, to):
    """(民國年, 起月, 迄月) 半年一發，同一民國年內。"""
    fy, fm = map(int, frm.split("/"))
    ty, tm = map(int, to.split("/"))
    out = []
    for y in range(fy, ty + 1):
        for s, e in ((1, 6), (7, 12)):
            s2 = max(s, fm) if y == fy else s
            e2 = min(e, tm) if y == ty else e
            if s2 <= e2:
                out.append((y, s2, e2))
    return out


def fetch(mkt, y, s, e, sleep, cache):
    tag = f"{mkt}_{y}_{s:02d}_{e:02d}"
    cp = os.path.join(cache, tag + ".html") if cache else None
    if cp and os.path.exists(cp):
        return open(cp, encoding="utf-8").read(), True
    body = urllib.parse.urlencode({"step": "1", "TYPEK": mkt, "year": str(y), "smonth": f"{s:02d}", "emonth": f"{e:02d}",
                                   "sstep": "1", "firstin": "true"}).encode()
    last = None
    for i in range(3):
        time.sleep(sleep if i == 0 else 30)
        try:
            b = urllib.request.urlopen(urllib.request.Request(URL, data=body, headers=UA), timeout=120).read()
            t = b.decode("utf-8")
            if BLOCK.search(t):
                raise Blocked(f"{tag}：回應含擋阻字樣 {BLOCK.search(t).group(0)}")
            if "總計" not in t and "無持股轉讓之情形" not in t:
                raise RuntimeError(f"非預期回應 len={len(t)} 開頭={re.sub(r'<[^>]+>|\\s+', ' ', t)[:120]!r}")
            if cp:
                with open(cp, "w", encoding="utf-8") as f:
                    f.write(t)
            return t, False
        except Blocked:
            raise
        except Exception as ex:  # noqa: BLE001
            last = ex
            print(f"  {tag} 第 {i + 1} 次失敗：{ex}", flush=True)
    raise RuntimeError(f"{tag} 重試 3 次仍失敗：{last}")


def cell(x, br="|"):
    x = re.sub(r"<br\s*/?>", "\x01", x, flags=re.I)
    x = html.unescape(re.sub(r"<[^>]+>", "", x)).replace("\xa0", " ")
    parts = [re.sub(r"\s+", " ", p).strip() for p in x.split("\x01")]
    return br.join(p for p in parts if p)


def num(x):
    x = x.replace(",", "").replace(" ", "")
    if x == "":
        return ""
    if re.fullmatch(r"-?\d+", x):
        return int(x)
    raise ValueError(x)


def roc(d):
    m = re.fullmatch(r"(\d{2,3})/(\d{1,2})/(\d{1,2})", d.strip())
    if not m:
        return ""
    return "%04d-%02d-%02d" % (int(m.group(1)) + 1911, int(m.group(2)), int(m.group(3)))


def norm_method(raw, unk):
    out = []
    for p in raw.split("|"):
        k = next((v for w, v in METHOD if w in p), None)
        if k is None:
            k = "other"
            unk[p] += 1
        out.append(k)
    return "+".join(out)


def parse(t, mkt, anom, unk):
    m = re.search(r"總計：\s*([\d,]+)\s*筆", t)
    total = int(m.group(1).replace(",", "")) if m else (0 if "無持股轉讓之情形" in t else None)
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S):
        tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
        if not tds:
            continue
        if len(tds) != 18:
            anom.append(("格數≠18", mkt, len(tds), cell(tr)[:80]))
            continue
        c = [cell(x) for x in tds]
        meth = c[6]
        sh_parts = [p for p in c[7].split("|")]
        try:
            sh_nums = [num(p) for p in sh_parts if p != ""]
            shares = sum(sh_nums) if sh_nums else ""
            split = "|".join(str(v) for v in sh_nums) if len(sh_nums) > 1 else ""
            dm = [num(p) for p in c[8].split("|") if p != ""]
            daily = sum(dm) if dm else ""
            nums = [num(c[i]) for i in range(10, 16)]
        except ValueError as ex:
            anom.append(("數字無法解析", mkt, c[1], c[2], str(ex)))
            continue
        vp = cell(tds[16], br=" ").strip()
        ds = re.findall(r"\d{2,3}/\d{1,2}/\d{1,2}", vp)
        dd = roc(c[1])
        if not dd:
            anom.append(("申報日期無法解析", mkt, c[1], c[2]))
        role = cell(tds[4], br="")
        if ROLE_NAME.search(role):
            anom.append(("role 夾帶姓名（已去掉）", mkt, c[1], c[2]))
            role = ROLE_NAME.sub("", role)
        tf = c[9].replace("|", " ")
        tt = transferee_type(tf)
        hd = cell(tds[5], br=" ")
        person = re.sub(r"之(配偶|未成年子女).*$", "", hd)
        person = "" if transferee_type(person) in ("org", "trust_bank") else person
        rows.append([mkt, dd, c[2], c[3], role, holder_key(c[2], hd), meth, norm_method(meth, unk),
                     shares, split, daily, tt, org_part(tf, person) if tt in ("org", "trust_bank") else "", *nums, vp, roc(ds[0]) if ds else "",
                     roc(ds[1]) if len(ds) > 1 else "", "是" if "是" in c[17] else c[17], cell(tds[0], br="")])
    return total, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="frm", default="92/05")
    ap.add_argument("--to", default="115/09")
    ap.add_argument("--markets", default="sii,otc,rotc")
    ap.add_argument("--sleep", type=float, default=4)
    ap.add_argument("--cache", default="", help="原始回應快取資料夾（⛔ 不要放 repo 內）")
    ap.add_argument("--ref", default="origin/main")
    ap.add_argument("--outdir", default=HERE, help="年檔寫到哪裡（月排程寫 data/meta/insider_predeclare）")
    ap.add_argument("--recent", action="store_true",
                    help="月排程用：自動取「上個完整月所在那一年」的 1 月到上個月（年檔整檔覆寫，所以必須從 1 月起）")
    a = ap.parse_args()
    if a.recent:
        import datetime
        t = datetime.date.today().replace(day=1) - datetime.timedelta(days=1)
        a.frm, a.to = "%d/01" % (t.year - 1911), "%d/%02d" % (t.year - 1911, t.month)
        print(f"--recent ⇒ {a.frm}～{a.to}", flush=True)
    if a.cache:
        os.makedirs(a.cache, exist_ok=True)
    anom, unk, mismatch, outwin = [], collections.Counter(), [], collections.Counter()
    seen, allrows, nfetch, dup_x, dup_in = {}, [], 0, 0, 0
    try:
        for mkt in a.markets.split(","):
            for (y, s, e) in windows(a.frm, a.to):
                jobs = [(y, s, e)]
                t, hit = fetch(mkt, y, s, e, a.sleep, a.cache)
                nfetch += not hit
                total, rows = parse(t, mkt, anom, unk)
                if total is None or total > SPLIT_OVER or total != len(rows):
                    print(f"  {mkt} {y}/{s:02d}-{e:02d} 總計 {total} 解析 {len(rows)} ⇒ 改逐月", flush=True)
                    jobs = [(y, mm, mm) for mm in range(s, e + 1)]
                    got = []
                    for (yy, ss, ee) in jobs:
                        t2, hit = fetch(mkt, yy, ss, ee, a.sleep, a.cache)
                        nfetch += not hit
                        tt, rr = parse(t2, mkt, anom, unk)
                        if tt != len(rr):
                            mismatch.append((mkt, f"{yy}/{ss:02d}", tt, len(rr)))
                        got.append(((yy, ss, ee), rr))
                else:
                    got = [((y, s, e), rows)]
                for (yy, ss, ee), rr in got:
                    wid = (mkt, yy, ss, ee)
                    lo = "%04d-%02d-01" % (yy + 1911, ss)
                    hi = "%04d-%02d-31" % (yy + 1911, ee)
                    for r in rr:
                        if not (lo <= r[1] <= hi):
                            outwin[(mkt, yy)] += 1
                        k = tuple(r)
                        if k in seen and seen[k] != wid:
                            dup_x += 1
                            continue
                        if k in seen:
                            dup_in += 1
                        seen[k] = wid
                        allrows.append(r)
                print(f"{mkt} {y}/{s:02d}-{e:02d} 總計 {total} 解析 {len(rows)}{'（快取）' if hit else ''}", flush=True)
    except Blocked as ex:
        print(f"⛔ 擋阻，立刻停：{ex}", flush=True)
        return 3
    allrows.sort(key=lambda r: (r[1], r[0], r[2], r[5]))
    by = collections.defaultdict(list)
    for r in allrows:
        by[r[1][:4]].append(r)
    shrink = []
    for y, rr in sorted(by.items()):
        fp = os.path.join(a.outdir, f"insider_predeclare_{y}.csv")
        # ⛔ 只准變多：既有年檔列數比這一趟多 ⇒ 這一趟抓少了（官方暫時少回、或查詢窗沒從 1 月起）⇒ 不覆寫
        if os.path.exists(fp):
            old_n = sum(1 for _ in io.open(fp, encoding="utf-8")) - 1
            if old_n > len(rr):
                shrink.append((y, old_n, len(rr)))
                print(f"⛔ {y} 既有 {old_n} 列 > 這一趟 {len(rr)} 列 ⇒ 不覆寫", flush=True)
                continue
        with io.open(fp, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n"); w.writerow(HDR); w.writerows(rr)
    # ── 彙總
    print(f"\n實際發送 {nfetch} 發；總列數 {len(allrows)}；跨發重複去掉 {dup_x}；同發內完全相同列（保留）{dup_in}")
    cnt = collections.Counter((r[1][:4], r[0]) for r in allrows)
    mk = a.markets.split(",")
    print("逐年 " + "/".join(mk) + "：")
    for y in sorted(by):
        print(f"  {y}: " + " / ".join(str(cnt[(y, m)]) for m in mk) + f"  計 {len(by[y])}")
    print("總計比對不符：", mismatch or "無")
    print("申報日不在查詢窗內：", dict(outwin) or "無")
    print("異常列：", len(anom), anom[:10])
    print("未知方式（歸 other）：", unk.most_common(20) or "無")
    mc = collections.Counter()
    for r in allrows:
        for p in r[7].split("+"):
            mc[p] += 1
    print("方式分佈（組合拆開計）：", mc.most_common())
    print("組合方式列數：", sum(1 for r in allrows if "+" in r[7]))
    tc = collections.Counter(r[11] or "(空白)" for r in allrows)
    print("transferee_type 分佈：", tc.most_common())
    print("org／trust_bank 抽不出機構名稱（transferee_org 空白）：", sum(1 for r in allrows if r[11] in ("org", "trust_bank") and not r[12]))
    try:
        st = subprocess.run(["git", "-C", REPO, "show", f"{a.ref}:data/meta/stocks.csv"], capture_output=True, text=True).stdout
        codes = {r["stock_id"] for r in csv.DictReader(io.StringIO(st))}
        ids = {r[2] for r in allrows}
        gone = sorted(ids - codes)
        print(f"代號 {len(ids)} 個；不在 {a.ref}:data/meta/stocks.csv 的 {len(gone)} 個，例 {gone[:15]}")
    except Exception as ex:  # noqa: BLE001
        print("stocks.csv 比對失敗：", ex)
    if mismatch or shrink:
        print(f"⛔ 總計不符 {len(mismatch)}、年檔變少 {len(shrink)} ⇒ 結束碼 1")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
