#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""永續合約資金費率探針：**只讀、不寫資料檔**。答加密策略線 PREREGC2 的兩個開跑前置。

⏳ 加密策略線 20260924-1712 §三、裁定線 1715：
  §六① 資金費率歷史　§六③ 逐幣永續合約上市日 ⇒ 「目前是唯二開跑前置」
  母體：BTC／ETH／BNB／XRP／DOGE／SOL（加密策略線 20260923-1305 收斂的六幣）

## ⛔ 為什麼走 data.binance.vision，⛔ 不走 fapi

`crypto_probe.py` 2026-09-20 已經付過代價：`api.binance.com` 從 Actions 回
**451「restricted location」**（runner 的美國 IP 被法遵封鎖）。`fapi.binance.com`
（永續合約那一支，含 `exchangeInfo` 的 `onboardDate`）是同一個實體 ⇒ ⛔ 不指望它。
⇒ ⭐ `data.binance.vision`（CloudFront 大量歷史檔）從 Actions **驗過真的下載得到 zip**，
   ⭐ 而且我方現貨日線本來就走它 ⇒ 資金費率走同一條路，不多開一個依賴。

## ⭐⭐ 一個來源解兩件

```
① 資金費率歷史 ⇒ data/futures/um/monthly/fundingRate/<SYM>USDT/<SYM>USDT-fundingRate-YYYY-MM.zip
③ 上市日      ⇒ ⭐ 最早那一個月檔裡的【第一筆】時間戳
   ⚠ 它是上市日的【上界】，⛔ 不是上市日本身：
     資金費率在上市之後才第一次結算（間隔通常 8 小時）⇒ 真上市日 ≤ 第一筆
   ⇒ 報的時候一律寫「最早可得資金費率時間（≈ 上市日上界，差距 ≤ 一個結算間隔）」
```

## ⛔ 判準（照本庫已經付過代價的幾條）

```
⛔ 不看 HTTP 200：要【真的解壓、解得出列、第一欄解得出時間】才算
⛔ 不看目錄頁：crypto_probe 2026-09-20 踩過 —— ?prefix= 回的是 JS 空殼
⭐ 對照組：BTCUSDT 最近一個完整月（一定存在）⇒ 它不過，下面全部沒有結論
⭐ 表頭照印：⛔ 不假設欄名，把真的表頭印出來給下游用
⚠ 「查不到某個月」要分兩種：還沒上市（合法的 404）vs 我方打不通（連不上）
```
"""
import io
import os
import sys
import time
import zipfile
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ca_chain  # noqa: F401
import backfill as B

# ⛔ B._ROOT 已經是 <repo>/data（us_probe 2026-09-24 第一趟就是在這裡炸的）
OUT = os.path.join(B._ROOT, "meta", "_funding_probe.txt")
BASE = "https://data.binance.vision/data/futures/um/monthly/fundingRate"
COINS = ["BTC", "ETH", "BNB", "XRP", "DOGE", "SOL"]
# ⭐ USDT 本位永續 2019-09 才開 ⇒ 搜尋下界；⛔ 不是任何一檔的上市日
EARLIEST = (2019, 9)


def month_url(sym, y, m):
    s = sym + "USDT"
    return "%s/%s/%s-fundingRate-%04d-%02d.zip" % (BASE, s, s, y, m)


def fetch_rows(sym, y, m):
    """→ ('ok', 表頭, [列]) ／ ('absent', None, None) ／ ('error', 訊息, None)。

    ⭐ 三種要分開：absent＝對方明說沒有這個檔（404）、error＝我方沒打通。
    ⛔ 把兩種混在一起，「還沒上市」和「被擋」會長得一模一樣。
    """
    body, err = B.get(month_url(sym, y, m), retries=2, timeout=40)
    if err:
        # ⚠ S3／CloudFront 對【不存在的檔】常回 403（沒開 ListBucket 權限時）而不是 404
        #   ⇒ 403／404 都當「不存在」，⚠ 但把碼留下來印出來，⛔ 不藏
        #   ⇒ 而「整個來源被擋」由對照組（最近一個月必須 ok）排除，不靠這裡判
        if "HTTP 404" in err or "HTTP 403" in err:
            return "absent", err.split("|")[0].strip(), None
        return "error", err, None
    try:
        z = zipfile.ZipFile(io.BytesIO(body))
        name = z.namelist()[0]
        txt = z.read(name).decode("utf-8", "replace")
    except (zipfile.BadZipFile, IndexError, KeyError) as ex:
        return ("error", "不是可解的 zip（%s）｜前 80 bytes：%r"
                % (type(ex).__name__, body[:80]), None)
    lines = [l for l in txt.splitlines() if l.strip()]
    if not lines:
        return "error", "zip 裡是空檔", None
    head = lines[0]
    # ⚠ 有表頭就去掉；第一欄若是純數字就代表沒有表頭
    if head.split(",")[0].strip().isdigit():
        return "ok", "（無表頭）", lines
    return "ok", head, lines[1:]


def first_ts(rows):
    """→ 第一列的時間（UTC 字串）；⛔ 認不出來回 None，⚠ 不猜。"""
    if not rows:
        return None
    try:
        v = int(rows[0].split(",")[0])
        if v > 10 ** 12:          # 毫秒
            v //= 1000
        return datetime.datetime.fromtimestamp(
            v, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")
    except (ValueError, IndexError, OverflowError):
        return None


def months_between(a, b):
    out = []
    y, m = a
    while (y, m) <= b:
        out.append((y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def month_start_str(ym):
    """→ 該月第一瞬的字串，⭐ 與 first_ts 同格式（⛔ 不同格式就永遠比不相等）。"""
    return "%04d-%02d-01 00:00" % ym


def censor_verdict(ym, floor, ft):
    """→ '真' ／ '左截' ／ '不明'。⭐ 由機制推導，⛔ 不寫死任何日期。

    ⛔⛔ 這一支要擋的錯：把【封存下限】讀成【上市日】。

    ```
    左截的簽名：最早月【就是封存下限月】，而第一筆正好落在該月的【第一瞬】
      ⇒ 那個 00:00 不是一次結算 —— 資金費率是每隔數小時結算一次，
        真的第一次結算落在月中的機率遠大於落在 00:00:00
      ⇒ 只能說「上市日 ≤ 該月 1 日」，⛔ 給不出上市日
    真的簽名（兩種都算真）：
      ① 最早月【晚於】封存下限月 ⇒ 前一月確實有封存、只是這一幣沒有 ⇒ 真缺
      ② 最早月就是下限月，但第一筆在【月中】 ⇒ 看得到真正的第一次結算
    ```
    ⚠ 封存下限是【母體逐幣最早月取 min】推出來的，⛔ 不是常數：
      封存回溯一延伸，下限就會往前移，而這一支會自己跟著移。
    """
    if ft is None:
        return "不明"
    if ym != floor:
        return "真"
    return "左截" if ft == month_start_str(ym) else "真"


def intervals(rows):
    """→ {interval 值: 筆數}；⛔ 認不出來的列歸到 '?'，⚠ 不丟掉。

    ⭐ 為什麼要逐列看：Binance 把【部分】交易對的結算間隔從 8 小時改過
      ⇒ 若下游把 8 寫死成常數，那段期間的持有成本會【少算一半】。
    """
    out = {}
    for r in rows:
        c = r.split(",")
        k = c[1].strip() if len(c) > 1 and c[1].strip() else "?"
        out[k] = out.get(k, 0) + 1
    return out


def days_in_month(ym):
    y, m = ym
    ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
    return (datetime.date(ny, nm, 1) - datetime.date(y, m, 1)).days


def completeness(rows, ym):
    """→ (是否吻合, 說明)。⭐ 列數應該正好 ＝ 當月天數 × 每日結算次數。

    ⛔ 「下載到 zip」看不出缺口；⭐ 這個不變式看得出來，
       而它自己會算期望值（⛔ 不是寫死 90 或 93）。
    """
    iv = intervals(rows)
    if len(iv) != 1 or "?" in iv:
        return None, "interval 不是單一值（%s）⇒ ⛔ 不套這個不變式" % iv
    h = int(list(iv)[0])
    exp = days_in_month(ym) * 24 // h
    return (len(rows) == exp,
            "%d 列／期望 %d（%d 天 × 每 %d 小時）" % (len(rows), exp, days_in_month(ym), h))


def last_full_month():
    t = datetime.date.today().replace(day=1) - datetime.timedelta(days=1)
    return (t.year, t.month)


def main():
    L = [B.probe_stamp("永續合約資金費率（答加密策略線 PREREGC2 §六①③）").strip()]
    L.append("")
    L.append("# 永續合約資金費率探針（⛔ 只讀，本支不寫任何資料檔）")
    L.append("母體：%s（加密策略線 20260923-1305 收斂的六幣）" % "／".join(COINS))
    L.append("來源：%s" % BASE)
    L.append("")

    top = last_full_month()
    # ── 對照組 ─────────────────────────────────────────────
    st, info, rows = fetch_rows("BTC", *top)
    L.append("══ 對照組：BTCUSDT %04d-%02d（最近一個完整月，一定存在）══" % top)
    if st != "ok":
        L.append("   ⛔ %s｜%s" % (st, info))
        L.append("   ⇒ ⛔⛔ 對照組不通 ⇒ **下面全部沒有結論**，⚠ 不可讀成「沒有資料」")
        io.open(OUT, "w", encoding="utf-8").write("\n".join(L) + "\n")
        print("\n".join(L))
        return 0
    per_day = len(rows) / 30.0
    L.append("   ✅ 表頭（逐字，⛔ 不假設欄名）：%s" % info)
    L.append("   ✅ %d 列｜第一筆 %s UTC｜約每日 %.1f 筆" % (len(rows), first_ts(rows), per_day))
    L.append("   前兩列：%s ／ %s" % (rows[0], rows[1] if len(rows) > 1 else "-"))
    L.append("   ⭐ interval 逐列統計：%s"
             "（⛔ 下游要【逐列讀】這一欄，不可寫死 8：Binance 改過部分交易對的間隔）" % intervals(rows))
    okc, why = completeness(rows, top)
    L.append("   %s 完整性：%s"
             % ("✅" if okc else ("⚠" if okc is None else "⛔ 有缺口"), why))
    L.append("")

    # ── 逐幣：二分找最早可得的月 ──────────────────────────
    span = months_between(EARLIEST, top)
    L.append("══ 逐幣：最早可得資金費率（⭐ 上市日上界）══")
    L.append("   ⚠ 二分搜尋的前提是【一旦有、之後每月都有】⇒ 找到之後再往前驗一個月確認是 absent")
    summary = []
    for sym in COINS:
        lo, hi = 0, len(span) - 1
        # hi 一定要先驗是 ok（⛔ 不假設）
        st_hi = fetch_rows(sym, *span[hi])[0]
        if st_hi != "ok":
            L.append("   %-5s ⛔ 最近一個月就不是 ok（%s）⇒ 沒有結論" % (sym, st_hi))
            summary.append((sym, None, None, st_hi))
            continue
        errs = 0
        while lo < hi:
            mid = (lo + hi) // 2
            s = fetch_rows(sym, *span[mid])[0]
            time.sleep(0.3)
            if s == "ok":
                hi = mid
            elif s == "absent":
                lo = mid + 1
            else:
                errs += 1
                if errs > 3:
                    break
                continue
        ym = span[hi]
        st2, info2, rows2 = fetch_rows(sym, *ym)
        prev = span[hi - 1] if hi > 0 else None
        prev_st = fetch_rows(sym, *prev)[0] if prev else "（已是搜尋下界）"
        ft = first_ts(rows2) if st2 == "ok" else None
        good = (prev_st == "absent" or prev is None)
        L.append("   %-5s 最早 %04d-%02d｜第一筆 %s UTC｜前一月 %s %s"
                 % (sym, ym[0], ym[1], ft, prev_st,
                    "✅" if good else "⛔ 前一月不是 absent ⇒ 二分前提不成立，這一格不可信"))
        summary.append((sym, ym, ft, "ok" if good else "suspect"))

    # ── ⭐⭐ 封存下限：逐幣最早月取 min（⛔ 不是常數，⚠ 封存一延伸它就往前移）
    got = [ym for _, ym, _, _ in summary if ym]
    floor = min(got) if got else None

    L.append("")
    L.append("══ ⇒ 給加密策略線的一句（⭐ 可直接抄，⚠ 但要連限制一起抄）══")
    if floor:
        L.append("   ⭐ 本趟推出的【月檔封存下限】＝ %04d-%02d（逐幣最早月取 min）" % floor)
        L.append("   ⇒ ⛔⛔ 最早月落在下限月、而第一筆又正好是該月第一瞬 ⇒ 判【左截】：")
        L.append("     那個 00:00 是「檔案從這裡開始」，⛔ 不是一次結算 ⇒ 給不出上市日")
    for sym, ym, ft, st in summary:
        if not ft:
            L.append("   %-5s ⛔ 沒有結論（%s）" % (sym, st))
            continue
        v = censor_verdict(ym, floor, ft)
        if v == "左截":
            L.append("   %-5s ⛔ 左截：只能證明【永續上市日 ≤ %s】，⛔ 本線給不出上市日"
                     % (sym, month_start_str(ym).split()[0]))
        else:
            L.append("   %-5s ✅ 真：最早結算 %s UTC ⇒ 上市日在此【前 ≤ 一個結算間隔】內%s"
                     % (sym, ft, "" if st == "ok" else "　⛔ 可疑，見上"))
    L.append("   ⚠ 限制：①判【真】的是上界，真上市日 ≤ 第一筆，差距 ≤ 一個結算間隔")
    L.append("     ②判【左截】的⛔ 不可當上市日用：樣本期若早於下限月，母體不能靠它圈")
    L.append("     ③只驗到 USDT 本位永續（um）；幣本位與 USDC 本位【沒驗】")
    L.append("     ④費率是【小數】不是百分比（0.0001 ＝ 0.01%）")

    io.open(OUT, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
