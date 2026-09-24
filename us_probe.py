#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""美股供料探針：**只讀、不寫任何資料檔**，回答「美股能不能做回測」。

## ⛔⛔ 本支只有一個阻斷項：**拿不拿得到已下市的股票**

使用者 2026-09-24 定的範圍是【價量＋全市場（含下市）】。
⇒ 而免費的美股價量來源幾乎都只回**現在還在交易**的代號
  ⇒ ⛔⛔ 拿它做回測，母體會自動只剩活下來的那些，
    ⚠ 而**它不會報錯，數字看起來完全正常**。

⭐ 這件事本庫在台股上已經量過一次代價：回測線 2026-09-16
「已下市組缺 95.8% vs 在市組 0.3%」（`delisted.csv` 437 檔救回來的）。
⇒ 美股若拿只有倖存者的來源做，那個 95.8% 會變成**靜悄悄的 100%**。

⇒ ⭐ 所以本支的設計是：**拿四檔【已經下市】的真代號去問**，
  下市年份刻意拉開成一條梯子 ⇒ 回應自己會講出這個來源的倖存者邊界在哪一年。

## ⛔ 判準：不可以用 HTTP 200，也不可以用「有回東西」

```
⛔ HTTP 200            ⇒ 空的 chart、擋機器人頁、錯誤 JSON 都可能是 200
⛔ 回應長度不是 0      ⇒ 「查無此代號」的回應也有長度
✅ 判準：回應要【自己講出它有幾列、第一天與最後一天是哪一天】
   ⇒ 而【已下市那四檔的最後一天，要落在它下市的那一年附近】
   ⇒ 對不上 ⇒ 這個來源給的是別的東西（例如同代號被別家公司重用）
```

## ⭐ 對照組：一定要有一組【已知合法】的值

`AAPL` 在市、資料一定有 ⇒ 它是「這個來源到底通不通」的對照組。
⛔ 少了它，「四檔下市股都查不到」分不出是**來源沒有下市股**還是**整個來源打不通**。
（這一條是情報線 1420 §一 自報過的坑：兩組都失敗而兩種成因不同。）

## ⚠ 本支【做不到】的事，先寫明（⛔ 不要把它讀成「已經驗完」）

```
⛔ 付費來源（Polygon／Tiingo／Alpha Vantage 的 LISTING_STATUS）本機沒有 API key
   ⇒ 本支只能證明「沒有 key 打不進去」，⛔ 證明不了它們的資料有多好
   ⇒ ⭐ 那一格是【要不要付錢】的決定，不是本支能量的東西
⛔ 本支不判斷哪個來源「比較好」，只報各來源【自己講出來的】涵蓋範圍
```
"""
import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ca_chain  # noqa: F401  ⭐ 補鏈（見 CLAUDE.md 六點六）
import backfill as B

# ⛔ `B._ROOT` 已經是 `<repo>/data`（backfill.py:63）⇒ ⚠ 不可以再接一個 "data"。
#   2026-09-24 第一趟就是這樣炸的：寫到 data/data/meta/_us_probe.txt ⇒ FileNotFoundError
#   ⭐ 而 probe_step.sh 留下了 ✗ 那一行 ⇒ 看得見；⛔ 若沒有它，run 是綠的而檔是空的。
OUT = os.path.join(B._ROOT, "meta", "_us_probe.txt")

# ⭐ 已下市的真代號 ＋ 下市年份。⛔ 年份是判準的一部分，不是註解。
#   ⚠ 選這四檔的理由是【年份拉開成梯子】：回應會自己講出倖存者邊界在哪一年。
DELISTED = [
    ("LEH",  2008, "Lehman Brothers（2008 破產）"),
    ("SHLD", 2018, "Sears Holdings（2018 下市）"),
    ("TWTR", 2022, "Twitter（2022 被收購下市）"),
    ("FRC",  2023, "First Republic Bank（2023 被接管）"),
]
LIVE = ("AAPL", "⭐ 對照組：在市，⛔ 少了它分不出「沒有下市股」與「整個來源不通」")

# ⭐ 拆股還原的測試點：AAPL 2020-08-31 四比一。
#   ⛔ 判準不是「有沒有 adjclose 欄」，是【拆股前的價格有沒有被改過】。
SPLIT_SYM, SPLIT_DATE, SPLIT_RATIO = "AAPL", "2020-08-31", 4


def _n(v):
    """→ 數字或 None。⛔ 認不出來回 None，⚠ 不猜、不填 0。"""
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def yahoo_span(body):
    """→ (列數, 第一天, 最後一天) 或 None。

    ⛔ 不用 HTTP 狀態判成功：Yahoo 對不存在的代號也可能回 200＋一個空 chart。
    ⇒ 判準是 `chart.result[0].timestamp` 真的有列。
    ⚠ 粒度另外用 `yahoo_granularity()` 問——⛔ 有幾列【不等於】粒度對。
    """
    try:
        d = json.loads(body.decode("utf-8", "replace"))
    except (ValueError, AttributeError):
        return None
    try:
        res = (d.get("chart") or {}).get("result")
        if not res:
            return None
        ts = res[0].get("timestamp")
        if not ts:
            return None
        f = time.strftime("%Y-%m-%d", time.gmtime(ts[0]))
        l = time.strftime("%Y-%m-%d", time.gmtime(ts[-1]))
        return len(ts), f, l
    except (KeyError, IndexError, TypeError):
        return None


def yahoo_granularity(body):
    """→ 回應**自己講**的資料粒度（`meta.dataGranularity`），認不出來回 None。

    ⛔⛔ 2026-09-24 第一趟實跑當場被咬：本支送 `interval=1d`，
      而回應的 `meta.dataGranularity` 是 **3mo**
      ⇒ ⚠ HTTP 200、JSON 格式完全正確、`timestamp` 也真的有 169 列
        ——⛔ 而那 169 列是**季線**，不是日線。
    ⇒ ⭐ 這是「參數被收下但被忽略」那一族（本庫在 TPEx 的
      `violation/change` 上也踩過：四組參數回應逐位元相同）。
    ⇒ ⭐⭐ 而它擋得住的唯一方法是**問回應自己講什麼**，
      ⛔ 不是數列數（列數多寡跟粒度對不對是兩件事）。
    """
    try:
        d = json.loads(body.decode("utf-8", "replace"))
        return ((d.get("chart") or {}).get("result") or [{}])[0] \
            .get("meta", {}).get("dataGranularity")
    except (ValueError, AttributeError, KeyError, IndexError, TypeError):
        return None


def granularity_verdict(want, got):
    """→ (結論, 一句話)：我要的粒度與它給的粒度對不對得上。"""
    if got is None:
        return "unknown", ("⚠ 回應沒講它的粒度 ⇒ ⛔ 這一格沒有結論"
                           "（⚠ 不可以用列數反推）")
    if got == want:
        return "ok", f"✅ 我要 {want}，它說它給 {got}"
    return "ignored", (f"⛔⛔ 我要 {want}，而它自己說給的是 **{got}**"
                       f" ⇒ ⚠ 參數被收下但被忽略"
                       f" ⇒ ⛔ 這一批不是我要的東西，"
                       f"而它 HTTP 200、格式正確、列數也不是 0")


def stooq_span(body):
    """→ (列數, 第一天, 最後一天) 或 None。

    ⚠ Stooq 查不到時回的是一行純文字（例如 `No data`）⇒ ⛔ 那也是 HTTP 200。
    ⇒ 判準是【第一欄真的是 YYYY-MM-DD】的資料列數 ≥ 1。
    """
    try:
        txt = body.decode("utf-8", "replace")
    except AttributeError:
        return None
    days = []
    for ln in txt.splitlines()[1:]:          # 第一行是表頭
        c = ln.split(",")
        if len(c) >= 5 and len(c[0]) == 10 and c[0][4] == "-" and c[0][7] == "-":
            days.append(c[0])
    if not days:
        return None
    return len(days), days[0], days[-1]


def delisted_verdict(sym, year, span):
    """→ (結論, 一句話)。⛔ 判準是【最後一天落在下市年份附近】，不是「有回東西」。

    ⚠ 容差給 ±1 年：下市程序常跨年，而停止報價的那一天不等於公告下市的那一天。
    ⇒ 而差很多的那一種**要單獨講**：同一個代號被別家公司重用過
      ⇒ ⛔ 那時候「查得到」是最危險的情形——它給的是另一家公司的價格。
    """
    if span is None:
        return "missing", "⛔ 查不到 ⇒ 這個來源【不含】這一檔（倖存者偏誤的直接證據）"
    n, first, last = span
    ly = int(last[:4])
    if abs(ly - year) <= 1:
        return "ok", f"✅ 有 {n:,} 列｜{first} ~ {last} ⇒ 最後一天對得上下市年 {year}"
    if ly > year + 1:
        return "reused", (f"⛔⛔ 有 {n:,} 列但最後一天 {last} **晚於下市年 {year} 兩年以上**"
                          f" ⇒ ⚠ 這個代號很可能【被別家公司重用】"
                          f" ⇒ ⛔ 查得到比查不到更危險")
    return "truncated", (f"⚠ 有 {n:,} 列但最後一天 {last} 早於下市年 {year}"
                         f" ⇒ ⛔ 資料被截斷，不是完整到下市那一天")


def split_verdict(pre_close, post_close, ratio):
    """→ (結論, 一句話)：拆股前的價格是【來源已還原】還是【原始價】。

    ⭐ 判準：拆股前一天的收盤 ÷ 拆股後一天的收盤
      ≈ 1      ⇒ 來源已經還原（拆股前的價格被改小了）
      ≈ ratio  ⇒ 來源給的是原始價，⛔ 我方要自己還原
    ⚠ 而這一格量錯的代價是【整條報酬率錯 4 倍】，⛔ 而且只錯在拆股那一天。
    """
    if pre_close is None or post_close is None or not post_close:
        return "unknown", "⛔ 取不到拆股前後的收盤 ⇒ 這一格【沒有答案】，⚠ 不猜"
    r = pre_close / post_close
    if abs(r - 1) < 0.25:
        return "adjusted", (f"✅ 拆股前/後 ＝ {r:.2f} ≈ 1 ⇒ **來源已還原**"
                            f"　⚠ 而「已還原」要問它【什麼時候重算歷史】"
                            f"（台股那個「raw 會靜默回舊的」是同一族）")
    if abs(r - ratio) < ratio * 0.25:
        return "raw", (f"⛔ 拆股前/後 ＝ {r:.2f} ≈ {ratio} ⇒ **來源給原始價**"
                       f"　⇒ 我方要自己算還原因子（台股那一套可以沿用）")
    return "unknown", (f"⚠ 拆股前/後 ＝ {r:.2f}，既不像 1 也不像 {ratio}"
                       f" ⇒ ⛔ 判不出來，這一格留空")


SOURCES = [
    # (名稱, 組 URL 的函式, 解析函式, 一句說明)
    # ⛔ 不用 `range=max`：2026-09-24 實測它會讓回應把粒度降成 3mo。
    #   ⭐ 改用 period1/period2（epoch 秒）⇒ 這一組不會被降級。
    ("Yahoo chart",
     lambda s: ("https://query1.finance.yahoo.com/v8/finance/chart/"
                f"{s}?period1=0&period2={int(time.time())}&interval=1d"),
     yahoo_span, "免費、不需 key、⚠ 非官方"),
    ("Stooq CSV",
     lambda s: f"https://stooq.com/q/d/l/?s={s.lower()}.us&i=d",
     stooq_span, "免費、不需 key、⚠ 非官方"),
]

# ⛔ 需要 key 才打得進去的（本支只證明「沒有 key 進不去」）
KEYED = [
    # ⭐⭐ 2026-09-24 實測（demo key）：
    #   不帶 state ⇒ 14,462 列，表頭 symbol,name,exchange,assetType,
    #     ipoDate,delistingDate,status ⇒ ⭐ 欄位【有】下市那一格
    #     ⛔ 但每一列的 status 都是 Active、delistingDate 全是 null
    #   state=delisted ⇒ 回 `{}`（空 JSON）
    #   ⇒ ⛔⛔ 而 `{}` 的意思是【這把 key 拿不到】，
    #     ⚠ **不是**「沒有這份資料」——兩件事不可以混（否定句要標成立範圍）。
    #   ⇒ ⭐ 這條路的入場費是【一把免費 key】，⛔ 不是錢。
    ("Alpha Vantage LISTING_STATUS（不帶 state）",
     "https://www.alphavantage.co/query?function=LISTING_STATUS&apikey=demo",
     "⭐ 欄位有 delistingDate／status ⇒ 這支端點【結構上】給得出下市清單"),
    ("Alpha Vantage LISTING_STATUS（state=delisted）",
     "https://www.alphavantage.co/query?function=LISTING_STATUS"
     "&state=delisted&apikey=demo",
     "⛔ demo key 回 {} ⇒ ⚠ 那是 key 的限制，不是資料不存在"),
    ("Polygon tickers(active=false)",
     "https://api.polygon.io/v3/reference/tickers?active=false&limit=1",
     "⭐ 文件說 active=false 回已下市代號"),
]


def main():
    # ⭐ 第一行一律是 probe_stamp()：這一趟是誰、什麼時候、在哪個 ref 上跑的。
    #   ⛔ 少了它，一份三天前的輸出跟今天剛跑的【長得一模一樣】
    #   ⇒ 而這幾份檔正是各線判斷「官方到底有沒有」的依據。
    #   （selftest_probes.py 會擋：24 支寫探針輸出的程式全部都要叫它。）
    L = [B.probe_stamp("美股供料：阻斷項＝拿不拿得到已下市的股票").strip()]
    L.append("")
    L.append("# 美股供料探針（⛔ 只讀，本支不寫任何資料檔）")
    L.append("範圍（使用者 2026-09-24 定）：價量 ＋ 全市場【含下市】")
    L.append("")
    L.append("⛔⛔ 阻斷項：拿不拿得到【已下市】的股票。")
    L.append("   ⇒ 拿不到 ⇒ 母體只剩倖存者，而它不會報錯 ⇒ ⛔ 回測不成立。")

    for name, mkurl, parse, note in SOURCES:
        L.append("")
        L.append(f"══ {name}（{note}）══")
        # 對照組先打 ⇒ ⛔ 它不過，下面四檔的「查不到」就沒有意義
        sym, why = LIVE
        t0 = time.time()
        body, err = B.get(mkurl(sym), retries=2, timeout=30)
        dt = time.time() - t0
        if err:
            L.append(f"   {sym}　{why}")
            L.append(f"      ⛔ 連不上：{err}")
            L.append("   ⇒ ⛔⛔ 對照組不通 ⇒ **本來源這一節整個沒有結論**，"
                     "⚠ 不可讀成「它沒有下市股」")
            continue
        span = parse(body)
        L.append(f"   {sym}　{why}")
        if span is None:
            L.append(f"      ⛔ 回了 {len(body):,} bytes 但**解不出價格列** ⇒ "
                     f"⚠ 可能是擋機器人頁或格式變了｜前 200 字："
                     f"{body[:200].decode('utf-8', 'replace')}")
            L.append("   ⇒ ⛔⛔ 對照組不通 ⇒ 本來源這一節整個沒有結論")
            continue
        L.append(f"      ✅ {span[0]:,} 列｜{span[1]} ~ {span[2]}｜{dt:.1f} 秒")
        if parse is yahoo_span:
            gk, gm = granularity_verdict("1d", yahoo_granularity(body))
            L.append(f"      粒度：{gm}")
            if gk == "ignored":
                L.append("   ⇒ ⛔⛔ 粒度不對 ⇒ **本來源這一節的數字全部不可信**，"
                         "⚠ 包含下面四檔與拆股那一格")
                continue

        n_ok = 0
        for s, yr, d in DELISTED:
            time.sleep(1)                      # ⚠ 禮貌節流，⛔ 不是壓力測試
            b2, e2 = B.get(mkurl(s), retries=2, timeout=30)
            sp = None if e2 else parse(b2)
            kind, msg = delisted_verdict(s, yr, sp)
            if kind == "ok":
                n_ok += 1
            L.append(f"   {s}（{d}）")
            L.append(f"      {msg}" if not e2 else f"      ⛔ 連不上：{e2}")
        L.append(f"   ⇒ ⭐ 四檔下市股【對得上的有 {n_ok}/4】")
        if n_ok == 0:
            L.append("     ⇒ ⛔⛔ 這個來源**不能用來做回測**（母體只剩倖存者）")
        elif n_ok < 4:
            L.append("     ⇒ ⚠ 部分涵蓋 ⇒ ⛔ 而「部分」對回測沒有用："
                     "缺哪幾檔會隨年份變，母體就不是事前釘得死的")
        else:
            L.append("     ⇒ ✅ 四檔全中 ⇒ ⭐ 值得往下驗【全市場清單】那一步")

        # 拆股還原
        u = mkurl(SPLIT_SYM)
        b3, e3 = B.get(u, retries=2, timeout=30)
        L.append(f"   拆股還原判準（{SPLIT_SYM} {SPLIT_DATE} {SPLIT_RATIO}:1）")
        if e3:
            L.append(f"      ⛔ 連不上：{e3}")
        else:
            pre, post = _closes_around(b3, parse, SPLIT_DATE)
            kind, msg = split_verdict(pre, post, SPLIT_RATIO)
            L.append(f"      {msg}")

    L.append("")
    L.append("══ ⛔ 需要 API key 才打得進去的（本支只證明【沒有 key 進不去】）══")
    for name, url, note in KEYED:
        body, err = B.get(url, retries=1, timeout=20)
        got = "⛔ 連不上：" + str(err) if err else f"回了 {len(body):,} bytes"
        L.append(f"   {name}")
        L.append(f"      {note}")
        L.append(f"      無 key 試打：{got}")
    L.append("   ⇒ ⭐ 這一節【不是】資料品質的證據，只是「這條路要不要付錢」的入口確認。")

    txt = "\n".join(L) + "\n"
    io.open(OUT, "w", encoding="utf-8").write(txt)
    print(txt)
    return 0


def _closes_around(body, parse, day):
    """→ (拆股前一交易日收盤, 拆股當日或之後第一個交易日收盤)。

    ⚠ 只有 Yahoo 的回應帶得出逐日收盤（Stooq 的 CSV 也帶）⇒ 兩種各自解。
    ⛔ 解不出來一律回 (None, None)，⚠ 不猜。
    """
    try:
        if parse is yahoo_span:
            d = json.loads(body.decode("utf-8", "replace"))
            r = d["chart"]["result"][0]
            ts, cl = r["timestamp"], r["indicators"]["quote"][0]["close"]
            pre = post = None
            for t, c in zip(ts, cl):
                ds = time.strftime("%Y-%m-%d", time.gmtime(t))
                if ds < day:
                    pre = _n(c)
                elif post is None:
                    post = _n(c)
            return pre, post
        txt = body.decode("utf-8", "replace")
        pre = post = None
        for ln in txt.splitlines()[1:]:
            c = ln.split(",")
            if len(c) < 5:
                continue
            if c[0] < day:
                pre = _n(c[4])
            elif post is None:
                post = _n(c[4])
        return pre, post
    except (KeyError, IndexError, TypeError, ValueError):
        return None, None


if __name__ == "__main__":
    sys.exit(main())
