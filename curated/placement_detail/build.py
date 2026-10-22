# -*- coding: utf-8 -*-
"""私募明細表（MOPS 私募專區 t116sb01）⇒ placement_detail.csv ＋ E3 對照 e3_placement_match.csv

    python3 curated/placement_detail/build.py [--fetch] [--build] [--ref origin/main] [--only 1795,2408]

依據：協調者 2026-10-22 派工（台股策略線 seq3 會用到）；前置探針見 curated/takeover_events/README.md（2026-10-22，21 發）。
來源：mopsov.twse.com.tw/mops/web/ajax_t116sb01（公開資訊觀測站「私募專區—辦理私募有價證券一覽表」）。
  一覽（step=1，每家一發）：POST step=1, firstin=true, off=1, queryName=co_id, inpuType=co_id, TYPEK=<sii|otc>, co_id=<代號>
     ⇒ 該公司全部私募案，一案一列；第 4 欄「董事會決議日起兩日內應申報相關資訊」的按鈕帶 report_type、decide_date（民國 YYYMMDD）、stock_kind。
  明細（step=2）：POST step=2, firstin=true, TYPEK, report_type, co_id, decide_date, stock_kind（year、seq_no、ys 給空字串）。
⚠ mopsov 的 robots.txt 是 disallow；本程式只在本機手動執行、每發間隔 ≥4.5 秒、一般瀏覽器 UA、快取在 repo 外（~/.cache/placement/），可中斷續跑（有快取就不再打）。
⛔ 遇擋阻頁／驗證碼／查詢過量訊息就停（exit 3），不繞過。

## 範圍（2026-10-22 寫死）
公司＝takeover_events.csv（--ref 版本）裡 class=E3、date ≥ 2011-01-01 的代號（612 家）；TYPEK 用該列的 market（news 的市場別＝現在或下市前）；
  一覽回 0 列時改用另一個市場（sii↔otc）再打一發。
明細只抓第 4 欄 report_type 不是 "1" 的案（"1"＝2010 年以前的舊表，只有文字、沒有是／否欄；"1_1" 普通股／特別股新式表、"2_1" 公司債新式表等照抓）。

## 防回音（每發都驗）
一覽：每一列第 1 欄代號、按鈕裡的 co_id 都要等於送出的 co_id，否則記 echo_bad。
明細：頁面「公司代號：」要等於送出的 co_id；「董事會決議日期」（或「股東會決議日期」）要等於送出的 decide_date，否則記 echo_bad。echo_bad 累計 >5 發就停。

## 欄位（placement_detail.csv，一案一列；⛔ 不收應募人姓名、法人名稱等）
stock_id, decide_date（ISO；明細的董事會決議日）, report_type, stock_kind, sec_kind（一覽的證券種類原文）, is_bond（證券種類含「公司債」＝1）,
form_title（明細抬頭括號內，例「私募普通股適用」）,
is_insider（應募人是否含有公司內部人或關係人：1／0／空＝兩個都沒勾或舊表）, is_strategic（應募人是否為策略性投資人）,
control_change（董事會決議辦理私募前一年內經營權是否發生重大變動或引進策略性投資人後是否將造成經營權重大變動）,
non_cash（應募人是否擬以非現金方式出資）, indep_objection（獨立董事反對或保留意見：1／0／na＝不適用／空）,
price_floor_pct（私募每股價格不得低於參考價格之成數 %）, fs_period（最近期財報年季，民國 YYY/Q）, nav_ps（最近期財報每股淨值）,
net_income_k, accum_pl_k（最近年度稅後損益、累計盈虧，千元）, close_prev（董事會決議日前一日收盤價）,
report_date, first_confirm_date（申報日期、第一次確認日期，ISO）, echo_ok, fetched（快取檔名）
⚠ 只有 report_type≠"1" 的案有明細欄；report_type="1" 的案也列出（明細欄空），供 E3 配對用。

## E3 對照（e3_placement_match.csv，takeover_events 每一列 E3）
規則（寫死）：同 stock_id 的私募案中，decide_date ≤ E3 date 且相差 ≤ 365 天的最近一案；沒有＝unmatched。
gap_days＝E3 date − decide_date；bond_flag＝配到的案是公司債（例 6558 2020-12-24 主旨沒寫、內文是私募無擔保轉換公司債）。
⚠ 舊表（report_type="1"）以股東會決議日當 decide_date，會晚於董事會公告 ⇒ 2010 年以前多半配不到或配到前一案；配對率分 2011 前後報。
"""
import argparse, csv, datetime, glob, io, os, random, re, subprocess, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
CACHE = os.path.expanduser("~/.cache/placement")
URL = "https://mopsov.twse.com.tw/mops/web/ajax_t116sb01"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
GAP = 4.5
BLOCK = re.compile(r"安全性考量|驗證碼|captcha|CAPTCHA|THE PAGE CANNOT BE ACCESSED|查詢過量|過於頻繁|請稍後再|Too Many|Forbidden")
_last = [0.0]
_echo_bad = [0]


def log(msg):
    os.makedirs(CACHE, exist_ok=True)
    line = time.strftime("%Y-%m-%d %H:%M:%S") + " " + msg
    print(line, flush=True)
    with open(os.path.join(CACHE, "log.txt"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def post(data):
    dt = time.time() - _last[0]
    if dt < GAP:
        time.sleep(GAP - dt)
    req = urllib.request.Request(URL, data=urllib.parse.urlencode(data).encode(),
                                 headers={"User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded",
                                          "Referer": "https://mopsov.twse.com.tw/mops/web/t116sb01"})
    err = None
    for k in range(3):
        try:
            r = urllib.request.urlopen(req, timeout=40)
            b = r.read(); _last[0] = time.time()
            t = b.decode("utf-8", "replace")
            mb = BLOCK.search(t)
            if mb and "公司代號" not in t:  # 正常頁（一覽、明細）都有「公司代號」；明細內文本身可能出現這些字（2408 101/10/24 實例）
                log("STOP 擋阻頁／驗證碼：" + re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))[:200])
                sys.exit(3)
            if mb:
                log(f"note 內文含「{mb.group(0)}」但頁面正常，續跑 {data.get('co_id')} {data.get('decide_date', '')}")
            return t
        except urllib.error.HTTPError as e:
            _last[0] = time.time()
            if e.code in (403, 429):
                log(f"STOP HTTP {e.code}"); sys.exit(3)
            err = e
        except Exception as e:
            _last[0] = time.time(); err = e
        time.sleep(30 * (k + 1))
    log(f"FAIL 連線 {err} {data.get('co_id')} {data.get('decide_date', '')}")
    return None


def text(h):
    x = re.sub(r"<[^>]+>", " ", h); x = x.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", x).split("try {")[0]


def parse_list(h):
    rows = []
    for tr in re.findall(r"<tr class='(?:odd|even)'>(.*?)</tr>", h, re.S):
        tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
        if len(tds) < 4:
            continue
        m = re.search(r"report_type\.value='([^']*)';document\.t116sb01_fm\.co_id\.value='([^']*)';"
                      r"document\.t116sb01_fm\.decide_date\.value='(\d+)'(?:;document\.t116sb01_fm\.stock_kind\.value='([^']*)')?", tds[3])
        rows.append(dict(sid=text(tds[0]).strip(), sec_kind=text(tds[2]).strip(),
                         report_type=m.group(1) if m else "", btn_co=m.group(2) if m else "",
                         decide=m.group(3) if m else "", stock_kind=(m.group(4) or "") if m else ""))
    return rows


def roc(s):
    s = s.replace("/", "")
    if not s or not s.isdigit():
        return ""
    y, m, d = int(s[:-4]) + 1911, int(s[-4:-2]), int(s[-2:])
    try:
        return datetime.date(y, m, d).isoformat()
    except ValueError:
        return ""


def radio(x, label):
    m = re.search(re.escape(label) + r"\s*([●○])\s*是\s*([●○])\s*否(?:\s*([●○])\s*不適用)?", x)
    if not m:
        return ""
    if m.group(1) == "●":
        return "1"
    if m.group(2) == "●":
        return "0"
    if m.group(3) == "●":
        return "na"
    return ""


def num(x, pat):
    m = re.search(pat + r"\s*(-?[\d,]+(?:\.\d+)?)", x)
    return m.group(1).replace(",", "") if m else ""


def parse_detail(h):
    x = text(h)
    g = lambda p: (re.search(p, x).group(1) if re.search(p, x) else "")
    fs = re.search(r"最近期財報年季\s*民國\s*(\d+)\s*年\s*0?(\d)\s*季", x)
    return dict(
        co=g(r"公司代號：\s*(\w+)"),
        decide_seen=g(r"(?:董事會|股東會)決議日期\s*(\d+/\d+/\d+)"),
        form_title=g(r"應申報(?:之[^()（）]*|相關資訊)[（(]([^)）]*)[)）]"),
        is_insider=radio(x, "應募人是否含有公司內部人或關係人"),
        is_strategic=radio(x, "應募人是否為策略性投資人"),
        control_change=(radio(x, "是否將造成經營權發生重大變動") or radio(x, "是否發生經營權重大變動情事")),  # 2025 前後新舊兩種問法
        non_cash=radio(x, "應募人是否擬以非現金方式出資"),
        indep_objection=radio(x, "獨立董事是否有反對或保留意見"),
        price_floor_pct=(num(x, r"不得低於參考價格之成數\(%\)") or num(x, r"不得低於理論價格之成數\(%\)")),
        fs_period=(f"{fs.group(1)}/{fs.group(2)}" if fs else ""),
        nav_ps=num(x, r"最近期財報每股淨值"),
        net_income_k=num(x, r"最近年度財報稅後損益 \(單位:新台幣千元\)"),
        accum_pl_k=num(x, r"最近年度財報累計盈虧 \(單位:新台幣千元\)"),
        close_prev=num(x, r"董事會決議日前一日收盤價"),
        report_date=roc(g(r"申報日期\s*(\d+/\d+/\d+)")),
        first_confirm_date=roc(g(r"第一次確認日期\s*(\d+/\d+/\d+)")))


def load_e3(ref):
    t = subprocess.run(["git", "-C", REPO, "show", f"{ref}:curated/takeover_events/takeover_events.csv"],
                       capture_output=True, text=True).stdout
    return [r for r in csv.DictReader(io.StringIO(t)) if r["class"] == "E3"]


def list_path(sid, mk):
    return os.path.join(CACHE, "list", f"{mk}_{sid}.html")


def det_path(sid, rt, dd, sk):
    return os.path.join(CACHE, "detail", f"{sid}_{dd}_{rt}_{sk}.html")


def fetch(e3, only):
    os.makedirs(os.path.join(CACHE, "list"), exist_ok=True); os.makedirs(os.path.join(CACHE, "detail"), exist_ok=True)
    firms = {}
    for r in e3:
        if r["date"] >= "2011-01-01":
            firms[r["stock_id"]] = r["market"]
    if only:
        firms = {k: v for k, v in firms.items() if k in only}
    log(f"fetch 開始：{len(firms)} 家")
    todo = []
    for i, (sid, mk) in enumerate(sorted(firms.items())):
        got = None
        for m2 in (mk, "otc" if mk == "sii" else "sii"):
            p = list_path(sid, m2)
            if os.path.exists(p):
                h = open(p, encoding="utf-8").read()
            else:
                h = post(dict(step="1", firstin="true", off="1", keyword4="", code1="", TYPEK2="", checkbtn="",
                              queryName="co_id", inpuType="co_id", TYPEK=m2, co_id=sid))
                if h is None:
                    break
                rows = parse_list(h)
                bad = [x for x in rows if x["sid"] != sid or (x["btn_co"] and x["btn_co"] != sid)]
                if bad:
                    _echo_bad[0] += 1; log(f"echo_bad list {sid} {m2}")
                    if _echo_bad[0] > 5:
                        log("STOP echo_bad >5"); sys.exit(4)
                    continue
                open(p + ".tmp", "w", encoding="utf-8").write(h); os.replace(p + ".tmp", p)
            rows = parse_list(h)
            if rows:
                got = (m2, rows); break
        if got:
            for x in got[1]:
                if x["report_type"] and x["report_type"] != "1":
                    todo.append((sid, got[0], x))
        if (i + 1) % 25 == 0:
            log(f"list {i + 1}/{len(firms)}")
    log(f"明細待抓 {len(todo)} 案（含已快取）")
    n = 0
    for sid, mk, x in todo:
        p = det_path(sid, x["report_type"], x["decide"], x["stock_kind"])
        if os.path.exists(p):
            continue
        h = post(dict(firstin="true", TYPEK=mk, step="2", report_type=x["report_type"], co_id=sid,
                      decide_date=x["decide"], stock_kind=x["stock_kind"], year="", seq_no="", ys=""))
        if h is None:
            continue
        d = parse_detail(h)
        if d["co"] != sid or d["decide_seen"].replace("/", "").lstrip("0") != x["decide"].lstrip("0"):
            _echo_bad[0] += 1; log(f"echo_bad detail {sid} {x['decide']} 看到 {d['co']} {d['decide_seen']}")
            if _echo_bad[0] > 5:
                log("STOP echo_bad >5"); sys.exit(4)
            p = p.replace(".html", ".echobad.html")
        open(p + ".tmp", "w", encoding="utf-8").write(h); os.replace(p + ".tmp", p)
        n += 1
        if n % 50 == 0:
            log(f"detail 新抓 {n}")
    log(f"fetch 結束：明細新抓 {n}，echo_bad {_echo_bad[0]}")


def build(e3, ref):
    rows = []
    for p in sorted(glob.glob(os.path.join(CACHE, "list", "*.html"))):
        mk, sid = os.path.basename(p)[:-5].split("_", 1)
        for x in parse_list(open(p, encoding="utf-8").read()):
            r = dict(stock_id=sid, market=mk, decide_date=roc(x["decide"]), report_type=x["report_type"],
                     stock_kind=x["stock_kind"], sec_kind=x["sec_kind"], is_bond=int("公司債" in x["sec_kind"]))
            dp = det_path(sid, x["report_type"], x["decide"], x["stock_kind"])
            if x["report_type"] and x["report_type"] != "1" and os.path.exists(dp):
                d = parse_detail(open(dp, encoding="utf-8").read())
                r.update({k: v for k, v in d.items() if k not in ("co", "decide_seen")})
                r["echo_ok"] = 1; r["fetched"] = os.path.basename(dp)
            elif x["report_type"] and x["report_type"] != "1" and os.path.exists(dp.replace(".html", ".echobad.html")):
                r["echo_ok"] = 0
            rows.append(r)
    seen, uniq = set(), []
    for r in sorted(rows, key=lambda r: (r["stock_id"], r["decide_date"], r["report_type"], r["stock_kind"])):
        k = (r["stock_id"], r["decide_date"], r["report_type"], r["stock_kind"], r["sec_kind"])
        if k in seen:
            continue
        seen.add(k); uniq.append(r)
    hdr = ["stock_id", "decide_date", "report_type", "stock_kind", "sec_kind", "is_bond", "form_title", "is_insider", "is_strategic",
           "control_change", "non_cash", "indep_objection", "price_floor_pct", "fs_period", "nav_ps", "net_income_k", "accum_pl_k",
           "close_prev", "report_date", "first_confirm_date", "echo_ok", "fetched"]
    with io.open(os.path.join(HERE, "placement_detail.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n"); w.writerow(hdr)
        for r in uniq:
            w.writerow([r.get(c, "") for c in hdr])
    by = {}
    for r in uniq:
        if r["decide_date"]:
            by.setdefault(r["stock_id"], []).append(r)
    mhdr = ["date", "stock_id", "name", "e3_first12m", "subject", "match_decide_date", "gap_days", "n_cases", "report_type", "sec_kind",
            "bond_flag", "is_insider", "is_strategic", "control_change"]
    out = []
    for e in e3:
        d0 = datetime.date.fromisoformat(e["date"]); best = None
        for c in by.get(e["stock_id"], []):
            g = (d0 - datetime.date.fromisoformat(c["decide_date"])).days
            if 0 <= g <= 365 and (best is None or g < best):
                best = g
        if best is None:
            out.append([e["date"], e["stock_id"], e.get("name", ""), e.get("first12m", ""), e["subject"], "", "", 0, "", "", "", "", "", ""])
            continue
        cs = [c for c in by[e["stock_id"]] if (d0 - datetime.date.fromisoformat(c["decide_date"])).days == best]
        # 同一決議日有多案（例 6558 109/10/05 普通股＋轉換公司債）：bond_flag＝任一案是公司債；三個是／否欄取股權案（非公司債），沒有才取公司債案
        eq = [c for c in cs if not c["is_bond"]] or cs
        c = eq[0]
        out.append([e["date"], e["stock_id"], e.get("name", ""), e.get("first12m", ""), e["subject"], c["decide_date"], best, len(cs),
                    "+".join(sorted({x["report_type"] for x in cs})), "+".join(sorted({x["sec_kind"] for x in cs})),
                    int(any(x["is_bond"] for x in cs)), c.get("is_insider", ""), c.get("is_strategic", ""), c.get("control_change", "")])
    with io.open(os.path.join(HERE, "e3_placement_match.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n"); w.writerow(mhdr); w.writerows(out)
    # summary
    new = [r for r in uniq if r.get("fetched")]
    print(f"私募案 {len(uniq)}（公司 {len({r['stock_id'] for r in uniq})}；舊表 report_type=1 {sum(r['report_type']=='1' for r in uniq)}；"
          f"無按鈕 {sum(not r['report_type'] for r in uniq)}；新式表已抓明細 {len(new)}；echo_bad {sum(r.get('echo_ok')==0 for r in uniq)}）")
    for k in ("is_insider", "is_strategic", "control_change"):
        cnt = {}
        for r in new:
            cnt[r.get(k, "")] = cnt.get(r.get(k, ""), 0) + 1
        print(f"  {k}: " + " ".join(f"{v or '空'}={n}" for v, n in sorted(cnt.items())))
    print("  report_type: " + " ".join(f"{t}={sum(r['report_type']==t for r in uniq)}" for t in sorted({r['report_type'] for r in uniq})))
    for lab, sel in (("2011 起", lambda e: e[0] >= "2011-01-01"), ("2010 前", lambda e: e[0] < "2011-01-01")):
        s = [o for o in out if sel(o)]
        m = [o for o in s if o[5]]
        print(f"  E3 {lab}：{len(s)} 列，配到 {len(m)}（{len(m)/max(len(s),1):.1%}）；gap≤3 天 {sum(1 for o in m if o[6]<=3)}；"
              f"配到新式表且有明細 {sum(1 for o in m if o[11]!='' or o[12]!='')}；bond {sum(1 for o in m if o[10]==1)}")
    return uniq, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="origin/main")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    if not a.fetch and not a.build:
        a.fetch = a.build = True
    e3 = load_e3(a.ref)
    if a.fetch:
        fetch(e3, set(x for x in a.only.split(",") if x))
    if a.build:
        build(e3, a.ref)
    return 0


if __name__ == "__main__":
    sys.exit(main())
