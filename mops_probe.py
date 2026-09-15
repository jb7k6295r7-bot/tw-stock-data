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


#: ⭐ `one()` 這一趟**最後真的 GET 的那個網址**。
#  ⚠ 為什麼用模組屬性而不是多一個回傳值：`one()` 有五個呼叫點，
#    改簽章要改五處 ⇒ ⛔ 那是「改一邊、另一邊沒跟上」的完美條件（四點五）。
#  ⛔ 而它一定要有：外部 `.js` 的相對路徑要靠它才拼得出絕對網址，
#    ⚠ 而舊站的 host（mopsov）跟橋的 host（mops）**不同** ⇒ 拿橋的網址去拼會拼錯站。
LAST_URL = None


def one(api, year, out, **kw):
    """走一次完整的橋：POST 拿 URL → GET 那個 URL。→ (內容 bytes 或 None)

    ⚠ 同時把那個網址記在 `LAST_URL`（見上面那段的理由）。
    """
    global LAST_URL
    LAST_URL = None
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
    LAST_URL = url
    # ⚠ 2026-09-10 兩趟都斷在**這一段**（不是 POST）：
    #   `RemoteDisconnected: Remote end closed connection without response`。
    #   ⭐ 而同一段對 `ajax_t163sb04` 拿得回 **1,628,079 bytes** ⇒ 路是通的。
    #   ⇒ 差別可能是月營收那份更大／更慢，也可能是 mopsov 對那一支比較嚴。
    #   ⛔ 我不猜是哪一個：先把耐受度加大（3 次、120 秒），
    #     若還是斷，那就**不是暫時性的**，而那本身是有用的資訊。
    raw2, err2 = B.get(url, retries=3, timeout=120)
    if err2:
        out.append(f"    ⛔ 取舊站失敗：{_W(err2, 200)}")
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
    # ⛔⛔ 2026-09-15 付過代價：這一段本來**只比位元組、從來不說回來的是什麼**。
    #   ⚠ 而「兩期相同」有**兩種**成因，而且下一步完全相反：
    #
    #     ① 期別參數被忽略（回的是有資料的同一頁）⇒ ⛔ 這條路不可用
    #     ② 兩期回的都是**查無資料頁**　　　　　 ⇒ ⚠ 那多半是**別的參數**沒給對
    #        （`t05st01` 是逐檔查的重大訊息 ⇒ 沒給公司代號時本來就查無）
    #        ⇒ ⭐ 那是「我沒問對」，⛔ **不是**「它沒有歷史」
    #
    #   ⚠ CLAUDE.md 二③ 記過同一個坑：hist.tpex 的 4,449 bytes 查無資料頁
    #     讓 **32 個年份全部命中**。⇒ 所以這裡要把**內容自己**講出來。
    shell = {}
    for tag, raw in ((y1, a), (y2, b)):
        t = raw.decode("utf-8", "replace")
        # ⭐ 「是不是 js 空殼」走**唯一那一份**（`backfill.js_shell`，四點五）
        #   ——`suspend_probe` 早就有這個判準，而這一支沒有
        #   ⇒ 它把一個空殼判成「期別參數被忽略」（2026-09-15 實測）。
        han, n_tr, n_js, is_shell = B.js_shell(raw)
        shell[tag] = is_shell
        hits = [w for w in ("查無", "無資料", "沒有符合", "查詢無", "錯誤")
                if w in t]
        out.append(f"    [{tag}] 中文 {han:,} 字｜<tr> {n_tr} 個｜js {n_js} 支"
                   + ("　⛔ **js 空殼**" if is_shell else "")
                   + (f"｜⛔ 出現 {hits}" if hits else "｜（沒有查無字樣）"))
        # ⛔⛔ 2026-09-15 第二次付代價：上面那三個**數字**仍然分不出第三種形狀
        #   ——「它回的是**查詢表單**，不是結果」。表單頁一樣沒有「查無」字樣、
        #   一樣有幾個 `<tr>`、一樣每一期都相同。
        #   ⚠ 我已經為了這一格改過兩次判準，每次都又冒出一種形狀
        #   ⇒ ⭐ **不要再猜形狀了，把字印出來讓人讀。**
        #   （CLAUDE.md 第一點的同一句：先把回應自己講的話攤開，再開始比對。）
        #   ⇒ 去標籤那一半走**唯一那一份**（`backfill.visible_text`，四點五）
        out.append("      ⭐ 前 160 字："
                   + B.visible_text(t, " ")[:160])
    _t1 = a.decode("utf-8", "replace")
    _blank = any(w in _t1 for w in ("查無", "無資料", "沒有符合", "查詢無"))
    # ⛔⛔ js 空殼要**先**判：它同時滿足「兩期相同」與「沒有查無字樣」
    #   ⇒ 不先攔下來就會被判成「期別參數被忽略 ⇒ 這條路不可用」，
    #   ⚠ 而那兩句話的下一步**完全相反**（不可用 ⇒ 不再去試；取不到 ⇒ 還沒解決）。
    if all(shell.values()):
        out.append("  ⇒ ⚠⚠ **兩期都是 js 空殼**（框架回來了、資料是載入後由 js 取的）"
                   "　⇒ ⛔ **不可判定**它有沒有歷史——這是「**我方取不到**」，"
                   "跟 TDCC `qryStockAjax` 回 2 bytes、櫃買那三頁同一族，"
                   "⛔ **不是**「官方沒有」，⛔ 也不是「期別參數被忽略」。")
    elif same and _blank:
        out.append("  ⇒ ⚠⚠ **兩期相同，而且兩期都是「查無資料」頁**"
                   "　⇒ ⛔ **不可判定**它有沒有歷史——"
                   "這比較像是**別的參數沒給對**（例如逐檔查要給公司代號），"
                   "⛔ 不是「期別參數被忽略」。⇒ 要換參數再問一次。")
    elif same:
        out.append("  ⇒ ⛔⛔ **兩期內容逐位元組完全相同，而且不是查無資料頁**"
                   " ⇒ 期別參數被忽略，跟 `t164sb03` 同一種靜默失敗。**這條路不可用。**")
    else:
        out.append("  ⇒ ⭐ 兩期內容不同 ⇒ 期別參數**真的生效**。"
                   "⚠ 範圍：只驗了這兩個期別、這一個 TYPEK。")


def xhr_hunt(api, out, **kw):
    """⭐ 那一頁的 js **去打誰**——把線索從回應裡挖出來，⛔ 不是猜端點名。

    ## ⛔ 為什麼要有這一段

    2026-09-15 量 `t05st01` 的結論是「**js 空殼**：框架回來了、資料是載入後由
    js 取的」（`backfill.js_shell`）。⇒ 那句話講完之後，下一步**不是**放棄，
    ⚠ 也不是去猜端點名 —— ⭐ 是**把那個 js 要打的網址從頁面裡讀出來**。

    ⚠ 而我方到今天為止**只用過一個** MOPS api 路徑：`mops/api/redirectToOld`
    （全 repo grep 過，只有它）。⛔ 而那個名字本身就說明**還有別的**：
    「redirect **to old**」是相對於「新站自己的那一套」講的。

    ⇒ 這一段只做一件事：把回應裡**所有**像端點的東西逐條印出來
    （`/mops/api/…`、`fetch(`、`$.ajax`、`url:`、`getMsg` 的函式本體）。
    ⛔ 不下任何結論 —— ⭐ 人讀完那幾行才知道下一發要打哪裡。
    """
    out.append(f"── ⭐ `{api}` 的 js 去打誰（只挖線索，⛔ 不下結論）")
    raw = one(api, "114", out, **kw)
    if raw is None:
        out.append("  ⛔ 取不回來 ⇒ 這一段**沒跑**")
        return
    han, n_tr, n_js, shell = B.js_shell(raw)
    out.append(f"  [形狀] 中文 {han:,} 字｜<tr> {n_tr} 個｜js {n_js} 支"
               + ("　⛔ **js 空殼**" if shell else ""))
    # ⭐ 挖的那一半走**唯一那一份**（`backfill.xhr_clues`，四點五）
    #   ——櫃買公告區那幾頁是**同一個問題**，⛔ 不可以再抄一份。
    out += B.xhr_clues(raw, base=LAST_URL)
    # ⭐ ①~④ 全 0 的時候，答案在**外部 .js 裡** ⇒ 再挖一層（唯一那一份實作）
    out += B.js_followups(raw, base=LAST_URL)


def openapi_case(name, out):
    """⚠ 情報分析線標「一般認知只給最新一期，但那是印象不是實測」⇒ 這裡實測。

    ⭐ `name` 可以是短名（接在 TWSE 的 `opendata/` 後面），
    也可以是**整條網址**——⛔ 而那不是為了方便：櫃買那一族在別的網域
    （`www.tpex.org.tw/openapi/v1/`），⚠ 而這一支的判準（期別欄的相異值分佈）
    對兩邊**完全一樣** ⇒ ⛔ 不可以為了跨網域另寫一份（CLAUDE.md 四點五）。
    """
    url = name if "://" in name else OPENAPI + name
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
    # ⛔⛔ 2026-09-15 付過代價：這裡本來只認 `年月／出表／年度／月別／Date`
    #   ⇒ 量 `t187ap04`（每日重大訊息）時只看到 `出表日期`／`Date` 各 1 種
    #   ⇒ 我據此寫「只給最新一期，沒有歷史」。⛔ **那是量錯了欄。**
    # ⭐ 那兩欄是**快照時戳**（＝我方抓取那一天），⚠ 它必定只有 1 種——
    #   ⛔ 拿它問「有沒有歷史」，答案**永遠**是「沒有」，而那不是量出來的。
    # ⇒ 真正回答涵蓋期間的是**內容日期**（`發言日期`／`事實發生日`）。
    # ⚠ 而這正是 CLAUDE.md 二那條：**「這個端點可不可信」問錯了問題，
    #   要問的是「這個【欄】…」**——同一張表裡，有的欄是時戳、有的欄是內容。
    # ⛔⛔ 而我第一版的修法**過頭到另一邊**（同一天，2026-09-15）：
    #   我把「內容日期」當成一族，⚠ 而那一族裡其實有**兩種**，問的是不同的事：
    #
    #     ⭐ 批次日（`發言日期`／`年月`／`資料日期`）＝ **這一批是哪一天的**
    #        ⇒ ⭐ **只有它回答「涵蓋期間」**
    #        事件日（`事實發生日`）　　　　　　　＝ **這一列在講哪一天**
    #        ⇒ ⛔ 一批**單日**的公告裡，事件日本來就會散在好幾個月
    #
    #   ⇒ 實測的反證（⛔ 不是推理）：`t187ap04_L` 一批 82 筆，
    #     `發言日期` 只有 1 種（1150914），⚠ 而 `事實發生日` 有 11 種、
    #     ⭐ **最大值是 1151103——那是未來**。
    #     ⇒ 一個涵蓋期間的上界不可能落在未來 ⇒ ⛔ 事件日不是涵蓋期間。
    #
    # ⚠ 而 `發言時間` 是**時分秒**，⛔ 根本不是日期
    #   ——我上一版用 `"日期"`／`"發言"` 去比子字串就把它吃進來了，
    #   ⇒ 它有 80 個相異值 ⇒ 判準當場說「含多期」。⛔ 那是假的。
    TIMEY = ("時間", "Time", "time")                  # ⛔ 時分秒，不是日期
    STAMP = ("出表", "Date", "date", "asof")          # 快照時戳：必定 1 種
    EVENT = ("發生日", "事實發生")                     # 事件日：⛔ 不回答涵蓋期間
    BATCH = ("發言日", "年月", "年度", "月別",
             "資料日", "公告日", "申報日")              # ⭐ 批次日：只有它算數
    allk = [k for k in (d[0] if d else {})
            if not any(t in k for t in TIMEY)]
    stamp_k = [k for k in allk if any(t in k for t in STAMP)]
    event_k = [k for k in allk
               if k not in stamp_k and any(t in k for t in EVENT)]
    cont_k = [k for k in allk if k not in stamp_k and k not in event_k
              and any(t in k for t in BATCH)]
    for label, ks in (("快照時戳", stamp_k),
                      ("事件日｜⛔ 不回答涵蓋期間", event_k),
                      ("⭐ 批次日", cont_k)):
        for k in ks:
            vals = sorted({str(r.get(k, "")).strip() for r in d} - {""})
            out.append(f"  ── [{label}] `{k}` 有 {len(vals)} 個相異值："
                       + (f"{vals[:8]}…（最小 {vals[0]}｜最大 {vals[-1]}）"
                          if len(vals) > 8 else f"{vals}"))
    if not cont_k:
        out.append("  ⚠ 找不到**批次日**欄 ⇒ ⛔ **不可判定**它是不是只給最新一期"
                   + (f"（只有快照時戳 {stamp_k}，⛔ 那一族永遠只有 1 種）"
                      if stamp_k else "")
                   + (f"　⚠ 有事件日 {event_k}，⛔ **不可以拿它代打**"
                      if event_k else ""))
    elif all(len({str(r.get(k, "")).strip() for r in d} - {""}) <= 1
             for k in cont_k):
        out.append("  ⇒ ⛔ **批次日**只有一個值 ⇒ 只給最新一期，沒有歷史。"
                   + (f"　⚠ 而事件日 {event_k} 散在好幾期是**正常的**"
                      "（一批單日的公告在講過去甚至未來的事）⇒ ⛔ 那不是歷史"
                      if event_k else ""))
    else:
        _sp = max((len({str(r.get(k, "")).strip() for r in d} - {""}), k)
                  for k in cont_k)
        out.append(f"  ⇒ ⭐ **批次日**不只一個值（`{_sp[1]}` 有 {_sp[0]} 種）"
                   "⇒ **含多期**，值得當來源評估。"
                   "　⚠ 而「幾種」≠「涵蓋幾天」——要看上面那一行的最小與最大。")


def ezsearch_case(out):
    """⭐ 清單 D2 的新入口：「公開資訊觀測站**公告快易查**」（`ezsearch`）。

    ## ⛔ 它是怎麼冒出來的——而這正是三點④「先查自己家」

    2026-09-15 我替 `site_inventory.py` 加了關鍵詞「重大訊息／財報公告日」，
    ⇒ 櫃買官方選單回 **21 條**，其中一條是：

    ```
    關於櫃買 / 各項專區 / 公開資訊觀測站公告快易查
      → https://mopsov.twse.com.tw/mops/web/ezsearch
    ```

    ⚠ 而我整天都在打 `t05st01`（**每日**重大訊息）撞 js 空殼。
    ⭐ 「快易查」按名字是**查**（⇒ 有查詢條件 ⇒ 多半有日期區間），
    ⛔ 而**名字不是證據**（第二點⑤、TradingView 那顆按鈕）⇒ 所以這裡只量、不判。

    ## ⇒ 這一段做什麼

    只有三件：形狀（是不是 js 空殼）、inline 線索、外部 `.js` 再挖一層。
    ⛔ 不猜查詢參數、⛔ 不下「有沒有歷史」的結論——
    ⚠ 那個結論要靠「**這一批自己講出它是哪一期**」（第二點），而現在連資料都還沒拿到。
    """
    url = "https://mopsov.twse.com.tw/mops/web/ezsearch"
    out.append("── ⭐ 清單 D2 新入口：公開資訊觀測站**公告快易查** `ezsearch`")
    out.append(f"   {url}")
    out.append("   ⭐ 網址取自我方 `_site_inventory.txt`（櫃買官方選單），⛔ 不是我拼的")
    out.append("   ⚠ 只量形狀與線索，⛔ 不判它有沒有歷史（名字不是證據）")
    raw, err = B.get(url, retries=2, timeout=60)
    if err:
        out.append(f"   ⛔ 取不回來：{_W(err, 200)}　⇒ 這一段**沒跑**"
                   "（⛔ 不是「站上沒有」）")
        return
    han, n_tr, n_js, shell = B.js_shell(raw)
    out.append(f"   [形狀] {len(raw):,} bytes｜中文 {han:,} 字｜<tr> {n_tr} 個"
               f"｜js {n_js} 支" + ("　⛔ **js 空殼**" if shell else ""))
    out.append("   ⭐ 前 160 字：" + B.visible_text(raw, " ")[:160])
    out += B.xhr_clues(raw, base=url)
    out += B.js_followups(raw, base=url)
    # ══════════════════════════════════════════════════════════════
    # ⭐⭐ 端點名挖到了，**參數還是不知道**——⇒ 把那一段原始碼原樣印出來
    #
    # 2026-09-15 `mop_search.js` 裡挖到（在**被註解掉**的那幾行裡）：
    #     //var url = "/mops/web/ezsearch_query";
    #     //var keyValue = "step=" + step + "&lang=" + value + "&pg=ezsearch";
    # ⭐ 那是「公告快易查」真正的查詢端點，我方從來沒用過。
    # ⛔ 而參數**不可以猜**（第一點）⇒ 把 `ezsearch_query`／`AjaxCheck`
    #   前後的碼原樣印出來，⚠ 人讀完才知道下一發怎麼組。
    # ══════════════════════════════════════════════════════════════
    out.append("")
    out.append("── ⭐⭐ 那個查詢端點的**參數怎麼組**（⛔ 原始碼原樣印，不猜）")
    # ⛔⛔ 2026-09-15 讀完第一趟輸出之後的訂正——⚠ 我自己在 commit 訊息裡
    #   把 `/mops/web/ezsearch_query` 寫成「⭐⭐ D2 有進展：查詢端點」。
    #   ⭐ **那是過度解讀。** 逐字讀那幾段：
    #
    #     ① `ezsearch_query` 的每一處都在**被註解掉的行**裡
    #        （`//var url = "/mops/web/ezsearch_query";`）
    #     ② 而它們全部在 `getMsg()` ——⚠ 那個函式的註解寫著 **`/*跑馬燈*/`**
    #        （首頁那條捲動的最新消息），⛔ **不是查詢表單**
    #     ③ 活著的那一行是 `url = "/server-java/AjaxCheck"` ＋ `keyValue = "pg=ezsearch"`
    #        ⇒ 而 `mops2.js` 裡同一個端點是 `xhttp.send("step=0")` ＋ `eval(resp)`
    #        ＋ 一小時一次的 `setTimeout` ⇒ ⭐ 那更像**跑馬燈／連線檢查**
    #
    # ⇒ ⛔ 所以目前**還不知道**「公告快易查」的查詢表單送到哪裡。
    # ⚠ 而「註解掉的網址」與「現在還活著的網址」是**兩件事**
    #   ——⭐ 前者證明它**曾經**存在，⛔ 不證明它現在答得出來。
    # ⇒ 下一步是把 cap 放大、把**剩下那幾處**也印出來（`…（另 N 處未印）`）。
    out.append("   ⛔⛔ 這一格我**連錯兩次**，兩次的病根都是「只讀了印出來的那幾處」：")
    out.append("      ① 第一次：看到 `ezsearch_query` 就寫「查詢端點找到了」"
               "　⛔ 而當時印出來的三處**全是被註解掉的**")
    out.append("      ② 第二次：改寫成「每一處都在註解裡、都在 `/*跑馬燈*/` 內」"
               "　⛔ 而那只對**印出來的那三處**成立——輸出自己寫著「…（另 3 處未印）」")
    out.append("   ⇒ ⭐ cap 3 → 12 之後，那幾處裡**有沒被註解的**：")
    out.append("      `var url = \"/mops/web/ezsearch_query\";` 出現在 `/* 最新消息 */ proAN()`"
               "、在組長字串那一段、以及 `url_str` 那一段 ⇒ ⭐ **它是活的**")
    out.append("   ⇒ ⭐⭐ 而參數名**讀得到**（⛔ 不是猜的）：")
    out.append("      `step`／`CO_MARKET`／`CO_ID`／`PRO_ITEM`／`SUBJECT`"
               "／**`SDATE`**／**`EDATE`**／`lang`／`AN`")
    out.append("      ⚠ `SDATE`／`EDATE` 是**日期區間** ⇒ ⭐ 那正是 D2 缺的「歷史」那一半")
    out.append("      ⚠ `proAN()` 用 `step=\"01\"`；⛔ 主查詢的 `step` 值還沒讀到")
    out.append("")
    out.append("   ── ⭐⭐ 那就**真的打一發**（第一點：先把回應自己講的話攤開）")
    out.append("      ⛔ 這一段**不下結論**：只印形狀與前 300 字，"
               "⚠ 由人判斷它到底回了什麼")
    # ⛔ 參數是從上面那幾段**讀出來的**，⚠ 不是我拼的。
    #   `step` 主查詢的值還沒讀到 ⇒ ⭐ 那就**每個都試一次**並把結果並排，
    #   ⛔ 不要挑一個看起來對的填進去（第二點：靜默失敗都長成 stat:OK）。
    import twparse as _tw                                   # noqa: PLC0415
    from delist_probe import _spread as _sp                 # noqa: PLC0415
    EZ = "https://mopsov.twse.com.tw/mops/web/ezsearch_query"

    def _shot(label, form):
        """打一發並把回應攤開。→ (rows 或 None)。⛔ 這裡不下結論。"""
        out.append(f"      ── {label}")
        raw, err = _tw.post_form(EZ, form, timeout=60, retries=2)
        if err:
            out.append(f"         ⛔ 取不回來：{_W(err, 180)}"
                       "　⇒ 這一發**沒量到**（⛔ 不是「它不答」）")
            return None
        han, n_tr, n_js, shell = B.js_shell(raw)
        out.append(f"         [形狀] {len(raw):,} bytes｜中文 {han:,} 字"
                   f"｜<tr> {n_tr} 個｜js {n_js} 支"
                   + ("　⛔ **js 空殼**" if shell else ""))
        out.append("         ⭐ 前 300 字：" + B.visible_text(raw, " ")[:300])
        try:
            d = json.loads(raw.decode("utf-8-sig", "replace"))
        except ValueError:
            out.append("         ⚠ 不是 JSON ⇒ 這一發只量到形狀")
            return None
        rows = d.get("data") if isinstance(d, dict) else (
            d if isinstance(d, list) else None)
        if not isinstance(rows, list) or not rows:
            out.append(f"         ⚠ 沒有 `data` 陣列（頂層鍵 "
                       f"{sorted(d)[:8] if isinstance(d, dict) else type(d).__name__}）")
            return None
        out.append(f"         ⭐ `data` **{len(rows):,} 列**｜欄名 "
                   f"{sorted(rows[0])[:12]}")
        # ⛔ 第二點⑤：陣列型回應唯一問得出涵蓋期間的方式，是**每個鍵的相異值分佈**
        for _ln in _sp(rows):
            out.append("         " + _ln)
        return rows

    # ⭐ 主查詢是哪個 step ⇒ 四個都試一次並排（⛔ 不挑一個看起來對的）
    base = {"CO_MARKET": "", "CO_ID": "2330", "PRO_ITEM": "C00",
            "SUBJECT": "", "SDATE": "20260101", "EDATE": "20260915",
            "lang": "TW", "AN": ""}
    got = {}
    for step in ("00", "01", "02", "03"):
        got[step] = _shot(f"step={step}｜CO_ID=2330｜PRO_ITEM=C00"
                          "｜SDATE=20260101 EDATE=20260915",
                          dict(base, step=step))

    # ══════════════════════════════════════════════════════════════
    # ⛔⛔ 而「它回了資料」**不等於**「我送的參數有生效」（第二點①②）
    #
    # ⭐ 2026-09-15 第一發實測：我送 `CO_ID=2330`，⚠ 而回來的第一列是
    #   `COMPANY_ID: 6591`（動力-KY）、`CDATE: 115/09/15`（＝今天）
    #   ⇒ ⛔ 那看起來像「靜靜回今天的全部公告」，⚠ 而**看起來**不算數。
    #
    # ⇒ ⭐ 判準是 repo 到處在用的那一條：**換一個區間再打一次，比內容**。
    #   ⛔ 兩發逐位元組相同 ⇒ 那些參數是假的；不同 ⇒ 它們有生效。
    # ══════════════════════════════════════════════════════════════
    out.append("")
    out.append("      ── ⭐⭐ 參數到底有沒有生效：**換一個區間再打一次，比內容**")
    out.append("         ⛔ 「它回了資料」≠「我送的參數有生效」（第二點①②）")
    a = _shot("A｜step=00｜SDATE=20260301 EDATE=20260331（三月）",
              dict(base, step="00", SDATE="20260301", EDATE="20260331"))
    b = _shot("B｜step=00｜SDATE=20240301 EDATE=20240331（兩年前的三月）",
              dict(base, step="00", SDATE="20240301", EDATE="20240331"))
    if a is not None and b is not None:
        same = (a == b)
        out.append(f"         ⇒ ⭐ A 與 B **{'逐列相同' if same else '不同'}**"
                   + ("　⛔ **⇒ 日期參數是假的**（靜靜回同一批）"
                      if same else "　⇒ ⭐ 日期參數**有生效**"))
    else:
        out.append("         ⚠⚠ **這一格沒量到**（至少一發沒回來或不是 JSON）"
                   "　⇒ ⛔ 不算失敗，⛔ **也不算驗過**")
    for js in ("js/mop_search.js", "js/mops2.js"):
        jurl = "https://mopsov.twse.com.tw/mops/web/" + js
        out.append(f"  ── {jurl}")
        jraw, jerr = B.get(jurl, retries=2, timeout=60)
        if jerr:
            out.append(f"     ⛔ 取不回來：{_W(jerr, 160)}　⇒ 這一支**沒挖**")
            continue
        # ⚠ `SDATE` 是**日期區間**那一半的錨點——⭐ D2 要的「歷史」就掛在它上面。
        #   `CO_MARKET`／`PRO_ITEM` 是市場與公告項目（C00 財務資料／M00 重大訊息）。
        #   ⇒ 把組 keyValue 的那一段整串印出來，⛔ 參數名不可以猜。
        for needle in ("ezsearch_query", "AjaxCheck", "keyValue",
                       "SDATE", "CO_MARKET", "PRO_ITEM"):
            out.append(f"     ⭐ `{needle}` 前後：")
            out += ["  " + ln for ln in B.around(jraw, needle, span=420, cap=12)]


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
    # ⭐⭐ 清單 D2（財報**實際公告日**）2026-09-15 加。
    #
    # ⛔ 已知的否定要先講清楚範圍：官方 `t187ap06/07`（財報三表）裡的
    #   `報表日期`／`出表日期` 相異值都只有 **1 種**（＝我方抓取當天）
    #   ⇒ 那是**快照時戳**，不是公告日。⚠ 而那句話**只說得了那兩條端點**。
    #
    # ⭐ 而市場情報分析線 1846 §二指的路是「財報公告本身就是一則**重大訊息**」，
    #   並自承「上櫃那一半我完全沒碰」。
    # ⛔⛔ 而我方自己的 `_tpex_probe.txt` 第 67 行**早就寫著**：
    #       /mopsfin_t187ap04_O｜上櫃公司每日重大訊息｜參數 無
    #   ⇒ ⚠ 又是一次「外面的東西我知道要去查，而『我們自己有沒有』我以為我知道」
    #     （CLAUDE.md 三點 3.5 ④）。
    #
    # ⚠ 而「每日」這個名字**不是證據**（第二點⑤：名字叫 history 也可能只有今年）
    #   ⇒ 這裡問的是同一個判準：**期別欄有幾個相異值**。
    for n, why in (
        ("https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap04_O",
         "⭐ 上櫃每日重大訊息｜來源：我方 `_tpex_probe.txt` 第 67 行，⛔ 不是我拼的"),
        ("https://openapi.twse.com.tw/v1/opendata/t187ap04_L",
         "⚠ 上市的對應那條｜**這條是我依 `_O`／`_L` 慣例拼的** ⇒ 量得到才算"),
    ):
        out.append(f"── 清單 D2 候選：{why}")
        openapi_case(n, out)
        out.append("")
    # ⛔ 再驗橋接，而且**只驗那個唯一還沒排除的失敗模式**。
    bridge_case("ajax_t21sc03", "114", "110", out, month="01")
    out.append("")
    bridge_case("ajax_t163sb04", "114", "110", out, season="02")
    out.append("")
    # ⭐⭐ 清單 D2 的**最後一條**（市場情報分析線 1846 §二切入點①）。
    #
    # 已經量掉的：`t187ap04_L`／`mopsfin_t187ap04_O` 兩條 OpenAPI 都存在、
    # 欄位形狀正是公告日要的，⛔ 而 `發言日期` 相異值**各只有 1 種** ⇒ 只有當天。
    # ⇒ ⭐ 剩下唯一可能有歷史的就是 MOPS 的 `t05st01`（重大訊息）。
    #
    # ⚠ 而「它吃不吃日期參數」**不可以用讀的**——同一族已經騙過我們兩次
    #   （`t164sb03` 四種 year／season 組合回應完全相同；
    #     TDCC opendata 四個欄名逐位元相同）。
    # ⇒ ⭐ 判準走**同一份** `bridge_case`：兩個期別各抓一次，**比位元組**。
    #   ⛔ 相同就是期別參數被忽略，⚠ 而那跟「那一期真的沒有資料」長得一樣——
    #     所以底下取的兩個期別**都是一定有重大訊息的月份**。
    #
    # ⚠⚠ 參數名是**我依同族慣例拼的**（`year`／`month`／`day`），⛔ 不是查到的。
    #   ⭐ 而這不影響結論的可信度：`one()` 會把 `params` 的**回顯**印出來
    #     ⇒ 我送的參數有沒有生效，回應自己會講（CLAUDE.md 第一點）。
    #   ⇒ 若回應把我的參數換掉，那就是「這個參數是假的」，⛔ 不是「沒有歷史」。
    bridge_case("t05st01", "114", "110", out, month="09", day="01")
    out.append("")
    # ⭐⭐ 上面那一段的結論是「js 空殼 ⇒ 我方取不到」。
    #   ⇒ 而「取不到」是一個**還沒解決的工程問題**，⛔ 不是句點
    #   ⇒ 下一步是**把那個 js 要打的網址從頁面裡讀出來**（⛔ 不是猜端點名）。
    xhr_hunt("t05st01", out, month="09", day="01")
    out.append("")
    ezsearch_case(out)
    out.append("")
    revenue_hist_columns(out)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write(B.probe_stamp() + "\n".join(out) + "\n")
    print("\n".join(out))
    print(f"\n[mops_probe] 寫出 {OUT}")
    return 0

# ⛔ 這裡本來有一段**到不了**的寫檔碼（在 `return 0` 之後）。
#   ⚠ 它寫 OUT 的時候**沒有帶 `B.probe_stamp()`** ⇒ 若哪天有人動了上面那個
#     `return`，輸出會退回「講不出自己是哪一趟跑的」那個狀態，⛔ 而不會報錯。
#   ⇒ 照「已知會產生錯誤結論的工具要移走、不是標註別用」那條，刪掉，留這行說明。


if __name__ == "__main__":
    sys.exit(main())
