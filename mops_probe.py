#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mops_probe.py — 丁級 11（財報／月營收「能指定期別」）的**終點驗證**。

## 這一支在驗什麼

市場情報分析線 2026-09-10 10:51 找到一條橋，但**明講「路徑找到、終點未驗」**：

    POST https://mops.twse.com.tw/mops/api/redirectToOld
    {"apiName":"ajax_t21sc03","parameters":{"year":"114","month":"01","TYPEK":"sii", …}}
    → {"result":{"url":"https://mopsov.twse.com.tw/mops/web/ajax_t21sc03?parameters=<加密 blob>"}}

他們四條路全斷（CORS／站台授權／blob 綁 host），⇒ 由我方 Python 驗。

## ⛔⛔ 這一支唯一真正要回答的問題

**`year=114` 與 `year=110` 各抓一次，回傳內容是不是真的不同。**

⚠ **blob 不同 ≠ 資料不同。** `t164sb03` 就是「參數收下、`code:200 查詢成功`、
資料完全不變」——若 `redirectToOld` 也只是把參數收下、舊站那端再忽略掉，
我方會拿到 2,700 檔 × N 期**一模一樣**的資料，⛔ **而且完全不會報錯**。
⇒ 排除掉這一種，丁級 11 才算解決。

⭐ 順帶優先試一條更乾淨的：`openapi.twse.com.tw/v1/opendata/t187ap05_L`（月營收）。
⚠ 情報分析線標明「一般認知只給最新一期，**但這是印象不是實測**」⇒ 這裡實測。

## ⛔ 本支只讀不寫資料

輸出 `data/meta/_mops_probe.txt`。⛔ 在開發容器裡跑一定失敗（我方閘道對交易所 403），
**要在 Actions 上跑**。
"""
import io
import json
import os
import sys
import urllib.error
import urllib.request
# ⭐ 補上 TPEx 漏送的憑證鏈（⛔ 不降低驗證，見 `ca_chain.py`）。
#   import 就生效：它把 urllib 的預設 SSLContext 換成「系統預設＋補鏈」。
import ca_chain  # noqa: F401

import backfill as B
from backfill import why as _W

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(_ROOT, "meta", "_mops_probe.txt")

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
BRIDGE = "https://mops.twse.com.tw/mops/api/redirectToOld"
OPENAPI = "https://openapi.twse.com.tw/v1/opendata/"


def _post(url, payload, timeout=45, retries=3, sleep=None):
    """→ (bytes, err)。⛔ 自己寫是因為 `B.get()` 只有 GET。"""
    # ⭐ 2026-09-10：這一支連兩趟都斷在**暫時性**網路錯誤
    #   （`_ssl.c:993: handshake operation timed out`／`RemoteDisconnected`）。
    #   ⚠ 兩趟的結論都寫成「未驗」——⭐ 結論是對的（沒取到就是沒驗到），
    #     ⛔ 但代價是**要有人再按一次**。
    #   ⇒ 退避重試。⚠ 規則與 `twparse.post_form` 同一套：
    #     ⛔ 4xx 不重試（參數錯，重試只是多打對方幾發），408／429 例外。
    import time as _t
    _sleep = _t.sleep if sleep is None else sleep
    body = json.dumps(payload).encode("utf-8")
    last = None
    for i in range(max(1, retries)):
        req = urllib.request.Request(url, data=body, headers={
            "User-Agent": UA, "Content-Type": "application/json",
            "Accept": "application/json,text/plain,*/*"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(), None
        except urllib.error.HTTPError as e:
            try:
                last = f"HTTP {e.code} {e.reason} | {e.read()[:200]!r}"
            except Exception:  # noqa: BLE001
                last = f"HTTP {e.code} {e.reason}"
            if 400 <= e.code < 500 and e.code not in (408, 429):
                return None, last
        except Exception as e:  # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
        if i < retries - 1:
            _sleep(2 * (i + 1))
    return None, (last or "") + (f"（重試 {retries} 次都失敗）" if retries > 1 else "")


def _params(api, year, **kw):
    p = {"year": year, "TYPEK": "sii", "encodeURIComponent": 1,
         "firstin": 1, "off": 1, "step": 1, "isQuery": "Y"}
    p.update(kw)
    return {"apiName": api, "parameters": p}


def one(api, year, out, **kw):
    """走一次完整的橋：POST 拿 URL → GET 那個 URL。→ (內容 bytes 或 None)"""
    sent = _params(api, year, **kw)
    out.append(f"  POST {BRIDGE}  apiName={api} year={year} {kw}")
    raw, err = _post(BRIDGE, sent)
    if err:
        out.append(f"    ⛔ {err}")
        return None
    try:
        d = json.loads(raw.decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        out.append(f"    ⛔ 回應不是 JSON（{type(e).__name__}）；前 200 bytes："
                   f"{raw[:200]!r}")
        return None
    # ⭐ 規矩第一條：先把**全部頂層鍵**攤開，再看資料本身。
    out += ["    " + s for s in B.describe_response(d, want=sent["parameters"])]
    url = ((d.get("result") or {}).get("url") if isinstance(d.get("result"), dict)
           else None)
    if not url:
        out.append(f"    ⛔ 回應裡沒有 result.url ⇒ 這條橋在這個 apiName 上不成立")
        return None
    out.append(f"    → {url[:150]}…（blob 長 {len(url)}）")
    # ⚠ 2026-09-10 兩趟都斷在**這一段**（不是 POST）：
    #   `RemoteDisconnected: Remote end closed connection without response`。
    #   ⭐ 而同一段對 `ajax_t163sb04` 拿得回 **1,628,079 bytes** ⇒ 路是通的。
    #   ⇒ 差別可能是月營收那份更大／更慢，也可能是 mopsov 對那一支比較嚴。
    #   ⛔ 我不猜是哪一個：先把耐受度加大（3 次、120 秒），
    #     若還是斷，那就**不是暫時性的**，而那本身是有用的資訊。
    raw2, err2 = B.get(url, retries=3, timeout=120)
    if err2:
        out.append(f"    ⛔ 取舊站失敗：{err2[:200]}")
        return None
    out.append(f"    ✓ 取回 {len(raw2):,} bytes")
    return raw2


def bridge_case(api, y1, y2, out, **kw):
    """⭐ 這一支的核心：兩個期別各抓一次，**比內容**。"""
    out.append(f"── 橋接 {api}（{kw or '無額外參數'}）")
    a = one(api, y1, out, **kw)
    b = one(api, y2, out, **kw)
    if a is None or b is None:
        out.append(f"  ⇒ **未驗**：至少一邊沒取回來 ⇒ ⛔ 不可以說這條路通了")
        return
    same = a == b
    out.append(f"  ⇒ year={y1} 取回 {len(a):,} bytes；year={y2} 取回 {len(b):,} bytes")
    if same:
        out.append("  ⇒ ⛔⛔ **兩期內容逐位元組完全相同** ⇒ 期別參數被忽略，"
                   "跟 `t164sb03` 同一種靜默失敗。**這條路不可用。**")
    else:
        out.append("  ⇒ ⭐ 兩期內容不同 ⇒ 期別參數**真的生效**。"
                   "⚠ 範圍：只驗了這兩個期別、這一個 TYPEK。")


def openapi_case(name, out):
    """⚠ 情報分析線標「一般認知只給最新一期，但那是印象不是實測」⇒ 這裡實測。"""
    url = OPENAPI + name
    out.append(f"── OpenAPI {url}")
    raw, err = B.get(url, retries=2, timeout=60)
    if err:
        out.append(f"  ⛔ {_W(err, 200)}")
        return
    try:
        d = json.loads(raw.decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        out.append(f"  ⛔ 不是 JSON（{type(e).__name__}）；前 200 bytes：{raw[:200]!r}")
        return
    if not isinstance(d, list):
        out += ["  " + s for s in B.describe_response(d)]
        return
    out.append(f"  ✓ {len(d):,} 筆；第一筆的鍵 = {sorted(d[0]) if d else '（空）'}")
    # ⭐ 判準：**這一批要自己講出它是哪一期**。找出期別欄，看它有幾個相異值。
    keys = [k for k in (d[0] if d else {})
            if any(t in k for t in ("年月", "出表", "年度", "月別", "Date", "date"))]
    for k in keys:
        vals = sorted({str(r.get(k, "")) for r in d})
        out.append(f"  ── `{k}` 有 {len(vals)} 個相異值：{vals[:8]}"
                   + ("…" if len(vals) > 8 else ""))
    if not keys:
        out.append("  ⚠ 找不到期別欄 ⇒ ⛔ **不可判定它是不是只給最新一期**")
    elif all(len({str(r.get(k, "")) for r in d}) <= 1 for k in keys):
        out.append("  ⇒ ⛔ 期別欄只有一個值 ⇒ **只給最新一期**，沒有歷史。")
    else:
        out.append("  ⇒ ⭐ 期別欄不只一個值 ⇒ **含多期**，值得當來源評估。")


def revenue_hist_columns(out):
    """⭐⭐ 回測線 0722 ③要的那一格：`revenue_hist` 的來源**有沒有公告日**。

    ⛔ 起因（前視偏誤，而且不會報錯、只會讓結果變好看）：
      我方 `data/mops/revenue_hist/<期>_<市場>.csv` **一個日期欄都沒有**
      ⇒ 下游只能拿「期別」去對齊價格，而那是前視。

    ⚠ 而我 0920 給回測線的答案是【推論】不是實測：
      我方解析是「`header[2:]` 原樣保留來源欄名」⇒ 產出沒有日期欄
      ⇒ **推**得出「那張頁本身就沒有」。⛔ 而我沒去看過那張頁。

    ⇒ 這一節就是把那一格從【推論】升成【實測】：把 `t21sc03` 的欄名逐字印出來。
    ⭐ 判準只有一個：**欄名裡有沒有任何一個像日期的**
      （`日期`／`年月`／`公告`／`申報`／`出表`）。
    ⛔ 沒有 ⇒ 那就是真的沒有，前視這一格要靠規則擋（次月 10 日），不是靠資料。
    """
    import mops_history as MH
    out.append("── ⭐ `t21sc03`（revenue_hist 的來源）的欄名：有沒有公告日")
    url = MH.rev_url("sii", 114, 1)          # 民國 114 年 1 月，上市
    out.append(f"   {url}")
    raw, err = B.get(url, retries=2, timeout=60)
    if err or not raw:
        out.append(f"   ✗ 抓不到：{B.why(err)}")
        out.append("   ⛔ 抓不到**不等於沒有那一欄**——這一格仍然是【未驗】，下一輪再試。")
        return
    rows, header, note, _ = MH.parse_revenue(raw, 114, 1, "twse")
    if not header:
        out.append(f"   ⚠ 解析不出表頭：{note}")
        out.append("   ⛔ 這一格答不出來，⛔ 不可以寫成「沒有公告日」。")
        return
    out.append(f"   ⭐ 欄名（{len(header)} 欄，逐字）：")
    for i, c in enumerate(header):
        out.append(f"      [{i:>2}] {c}")
    hit = [c for c in header
           if any(w in str(c) for w in ("日期", "年月", "公告", "申報", "出表", "Date"))]
    if hit:
        out.append(f"   ⭐⭐ **有像日期的欄**：{hit}"
                   "　⇒ 可以收下來當公告日，前視那一格有救")
    else:
        out.append("   ⛔ **一個像日期的欄都沒有** ⇒ 來源本身就沒有公告日"
                   "　⇒ 前視只能靠規則擋（次月 10 日），⚠ 而規則擋不住提前／延後公告的")
    out.append(f"   （解析：{note}；⛔ 這裡只看欄名，不寫任何資料檔）")


def main():
    out = [f"# MOPS／OpenAPI 探針（丁級 11 終點驗證）",
           f"# ⛔ 在開發容器裡跑一定失敗（我方閘道對交易所 403）——要看 Actions 上的結果",
           ""]
    # ⭐ 先試乾淨的那條：不必經過 MOPS，也不必解 blob。
    for n in ("t187ap05_L", "t187ap05_O"):
        openapi_case(n, out)
        out.append("")
    # ⛔ 再驗橋接，而且**只驗那個唯一還沒排除的失敗模式**。
    bridge_case("ajax_t21sc03", "114", "110", out, month="01")
    out.append("")
    bridge_case("ajax_t163sb04", "114", "110", out, season="02")
    out.append("")
    revenue_hist_columns(out)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("\n".join(out))
    print(f"\n[mops_probe] 寫出 {OUT}")
    return 0


    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("\n".join(out))
    print(f"\n[mops_probe] 寫出 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
