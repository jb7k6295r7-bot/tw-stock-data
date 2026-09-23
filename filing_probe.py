#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""財報「期別參數」與「公告時點」兩條路的探針。⛔ 只讀不寫任何 data/ 真資料。

## 為什麼有這一支（2026-09-23）

市場情報分析線 20260923-1420 §三 點名請本線代驗兩件事，理由是**他們打不到**：

    device_bash（使用者電腦）  mops http=000   doc http=000
    雲端沙箱 Bash              mops http=000   doc http=000（agent proxy 明文回
                               connect_rejected: organization policy）
    瀏覽器                     兩個都通 —— 他們那封信的數字全是這條通道量的

⇒ ⭐ 而「他們的 curl 打不到」**不等於**「我們的 runner 打不到」：
  我方抓取跑在 GitHub Actions（`runs-on: ubuntu-latest`），沒有那層 egress 政策。
  ⚠ 而反過來也一樣：本線在**開發容器／本機**打得到或打不到，都不是 Actions 上的事實
  （CLAUDE.md 第六點：這個開發容器對交易所一律 403，而那是**我方閘道**擋的）。
⇒ ⛔ 所以這一支的結論只在 **Actions 上**算數。

## ⛔ 判準：不可以用 HTTP 200 當成功

本線 2026-09-23 在自己機器上實測 `t164sb03`：**HTTP 200、800 bytes**，
而內容是 TWSE 的擋阻頁（「因為安全性考量，您所執行的頁面無法呈現」）。
⇒ ⭐ 那正是 CLAUDE.md 第二點④那一種（被 CDN 擋回 HTML）。

⇒ 本支的判準一律是 **「這一批要自己講出它是哪一期／哪一檔」**：

    ① t164sb03  ⇒ 回應裡的 `result.year`／`result.season` 要跟我送的一樣
    ② t57sb01   ⇒ 解出來的列要帶得出【上傳日期】，而且換一個 year 會跟著變

## ⭐ 兩發都帶對照組，而且只改一個參數

情報線 1420 §一 自報過一個值得抄下來的錯：他們比了兩次回應「逐位元相同」就判
參數無效 ——⛔ 而「兩組都被忽略」與「兩組都是無效值」在回應上**完全同形**。
⇒ ⭐ 對照組至少要有一組是**已知合法**的值。

## ⛔⛔ 2026-09-23 22:07 訂正：合法值的成因是【鍵有沒有到齊】，⛔ 不是年制

本支第一版照「`year` 要民國年、`dataType="2"` 才是歷史」寫 body ⇒ 三發全部 `code:500`。
⇒ 情報線 2207 在頁面上攔下瀏覽器**實際送出**的那一份，並做了控制變因實測：

    A 五鍵完整、year=113（民國）      ✅ 200
    B 缺 subsidiaryCompanyId、year=113 ⛔ 500      ⇒ A vs B 只差一個鍵
    C 五鍵完整、year=2024（西元）     ✅ 200（回應自己說 year=113）
    F 缺 subsidiaryCompanyId、year=2024 ⛔ 500      ⇒ C vs F 年制相同

⇒ ⭐ **成因是少了 `subsidiaryCompanyId`**（空字串也算）；⛔ 年制**不是**成因，
  端點會把西元年自動換成民國年。
⇒ ⚠ 情報線自報：他們 1420 §一 把「民國年」當成因，是因為它與「欄位齊全」共變
  （瀏覽器表單永遠送五個鍵、也永遠送民國年）⇒ ⭐ 可執行形式：
  **能造測試樣本就造，而且一次只改一個地方。** 本支 §四 的四鍵對照組就是照這條加的。

## ⭐ 錯誤碼要分兩種（情報線 2207 §五）

    code 500「傳入參數異常」⇒ **我方 body 錯**
    code 406「查無相符資料」⇒ body 對、那一期沒有資料
⚠ 兩者都是 HTTP 200、都 77 B、`result` 都是 null
⇒ ⛔ 只看長度或 result 分不出來，**一定要讀 code**。
"""
import io
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ca_chain  # noqa: F401  ⭐ 補鏈：TPEx／TWSE 的中間憑證（見 CLAUDE.md 六點六）
import backfill as B

OUT = os.path.join("data", "meta", "_filing_probe.txt")

MOPS = "https://mops.twse.com.tw/mops/api/t164sb03"
DOC = "https://doc.twse.com.tw/server-java/t57sb01"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
TIMEOUT = 25

# ⛔ 這兩句是 TWSE 擋阻頁的逐字特徵（2026-09-23 本機實測抓到的那一份）。
#   ⚠ 它回的是 **HTTP 200**，所以只驗狀態碼會把它當成資料。
BLOCK_MARKS = ("因為安全性考量", "FOR SECURITY REASONS")


def looks_blocked(body):
    """→ 這一份回應是不是「擋阻頁」。⛔ 判準是內容，不是狀態碼。"""
    if not body:
        return False
    for enc in ("utf-8", "big5", "latin-1"):
        try:
            txt = body.decode(enc, "ignore")
        except (LookupError, UnicodeDecodeError):
            continue
        if any(m in txt for m in BLOCK_MARKS):
            return True
    return False


def self_declared_period(payload):
    """→ (year, season) 或 None。⛔ 認不出來回 None，⚠ 不猜。

    ⭐ 這一格就是「這一批要自己講出它是哪一期」那條判準的落地：
    `result.year` 是**回應自己**講的，⛔ 不是我送出去的那個值。
    """
    if not isinstance(payload, dict):
        return None
    r = payload.get("result")
    if not isinstance(r, dict):
        return None
    y, s = r.get("year"), r.get("season")
    if y in (None, "") or s in (None, ""):
        return None
    return (str(y), str(s))


def upload_dates(body):
    """→ HTML（big5）裡「上傳日期」那一欄的值。⛔ 解不出來回空 list，不猜。

    ⚠ 這一頁的 `Content-Type` 是 `text/html;charset=big5`
    ⇒ 用 UTF-8 解會整片亂碼（情報線 1420 §二 第一次就踩到）。
    ⭐ 而判準是**帶標籤的整串**（民國日期＋時分秒），⛔ 不是裸數字。
    """
    import re
    try:
        txt = body.decode("big5", "replace")
    except (LookupError, AttributeError):
        return []
    return re.findall(r"\b(1[0-9]{2}/[01][0-9]/[0-3][0-9] "
                      r"[0-2][0-9]:[0-5][0-9]:[0-5][0-9])", txt)


def short_text(body, limit=500):
    """→ 把回應**解碼成看得懂的字**。⛔ 不要印 bytes 的 repr。

    ⛔⛔ 2026-09-23 run 35860275837 當場付過代價：`t164sb03` 回
    `{"code":500,"message":"傳入…"}` 只有 89 bytes，⚠ 而本支把它印成
    `b'{"code":500,"message":"\xe5\x82\xb3…'` 又截在 120 字
    ⇒ ⭐ **對方其實有講原因，而我把它印成看不懂的樣子** ——
      那跟「沒印」的差別只有一點點：它讓人以為自己看過了。
    ⇒ ⚠ 而這一格正是 CLAUDE.md 六點六那條的同一族：
      **錯誤訊息不可以砍尾巴，可行動的部分往往在後面。**
    """
    if not body:
        return "（空回應）"
    for enc in ("utf-8", "big5"):
        try:
            txt = body.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
        txt = " ".join(txt.split())
        return txt if len(txt) <= limit else txt[:limit] + "…（截斷）"
    return f"（解不出編碼，{len(body)} bytes）"


def hit(url, data=None, headers=None):
    """→ (status, ctype, body, err)。⛔ 例外不吞：錯誤訊息**不砍尾巴**（六點六）。"""
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    req.add_header("User-Agent", UA)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.headers.get("Content-Type", ""), r.read(), ""
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type", ""), e.read(), ""
    except Exception as e:                       # noqa: BLE001
        return 0, "", b"", f"{type(e).__name__}: {e}"


def _mops_body(year, season, dtype, cid="2330", drop=None):
    """→ MOPS 五鍵 body。⛔ 五個鍵**全部必填**，少一個就回 code:500。

    ⭐ 逐字照抄情報線 2207 §一 從 devtools 攔下來的那一份：
      {"companyId":"2330","dataType":"2","season":"1","year":"113",
       "subsidiaryCompanyId":""}
    ⚠ `subsidiaryCompanyId` 給**空字串**就好，⛔ 但不可以不給。
    ⭐ 型別與補零都不挑（season="01"、數字型別都 ✅ 200）⇒ ⛔ 只挑鍵有沒有到齊。

    `drop` 是給**對照組**用的：刻意少送一個鍵，⇒ 該回 500。
    """
    b = {"companyId": cid, "dataType": dtype, "season": season,
         "year": year, "subsidiaryCompanyId": ""}
    if drop:
        b.pop(drop, None)
    return json.dumps(b).encode()


def mops_code(payload):
    """→ (code, message)；⛔ 認不出來回 (None, "")。

    ⚠ 500 與 406 都是 HTTP 200、都 77 B、`result` 都 null
    ⇒ ⛔ 分不出來的唯一原因是沒去讀 `code`（情報線 2207 §五）。
    """
    if not isinstance(payload, dict):
        return None, ""
    return payload.get("code"), str(payload.get("message", ""))


def probe_mops(lines):
    lines.append("")
    lines.append("══ ① MOPS t164sb03（POST／JSON）══")
    lines.append(f"   端點：{MOPS}")
    lines.append("   ⛔ 判準：回應要自己講出 result.year／result.season，"
                 "⚠ 不是看 HTTP 200")
    hdr = {"Content-Type": "application/json", "Accept": "application/json"}
    # ⭐ 三發：合法歷史值／換一個季（只改一個參數）／dataType=1 的對照組
    # ⭐ 五發，⛔ 每一發只改一個地方（情報線 2207 §二 的控制變因寫法）
    cases = [("113", "1", "2", None, "合法歷史值（五鍵齊、民國年、dataType=2）"),
             ("113", "3", "2", None, "只改 season（⇒ 數字該跟著變）"),
             ("2024", "1", "2", None,
              "只改年制成西元（⇒ 情報線量到端點會自己換成 113）"),
             ("113", "1", "1", None,
              "對照組：dataType=1（⇒ 情報線量到它一律回最新季，⛔ 而且不報錯）"),
             ("113", "1", "2", "subsidiaryCompanyId",
              "⛔ 反向對照組：刻意少送第五個鍵（⇒ 該回 code:500）")]
    for year, season, dtype, drop, why in cases:
        st, ct, body, err = hit(MOPS, _mops_body(year, season, dtype, drop=drop),
                                hdr)
        tag = f"   送 year={year} season={season} dataType={dtype}｜{why}"
        if err:
            lines.append(tag + f"\n      ⛔ 連不上：{err}")
            continue
        blocked = looks_blocked(body)
        try:
            payload = json.loads(body.decode("utf-8", "replace"))
        except (ValueError, UnicodeDecodeError):
            payload = None
        said = self_declared_period(payload)
        code, msg = mops_code(payload)
        lines.append(tag)
        lines.append(f"      HTTP={st}｜{ct}｜{len(body):,} bytes｜code={code}")
        if code == 500:
            lines.append(f"      ⛔ code 500【傳入參數異常】＝**我方 body 錯**"
                         f"：{msg}")
        elif code == 406:
            lines.append(f"      ⚠ code 406【查無相符資料】＝body 對、那一期沒資料"
                         f"：{msg}")
        if blocked:
            lines.append("      ⛔⛔ **這是擋阻頁**（HTTP 200 也算），"
                         "⚠ 只驗狀態碼會把它當成資料")
        elif said is None:
            lines.append("      ⛔ 回應**講不出自己是哪一期**（沒有 result.year／season）")
            lines.append(f"         對方說：{short_text(body)}")
        else:
            ok = "✅ 跟我送的一樣" if said == (year, season) else "⛔ 跟我送的不一樣"
            lines.append(f"      回應自己說：year={said[0]} season={said[1]}　{ok}")


def probe_doc(lines):
    lines.append("")
    lines.append("══ ② doc.twse t57sb01（GET／big5 HTML）══")
    lines.append(f"   端點：{DOC}")
    lines.append("   ⛔ 判準：解得出【上傳日期】那一欄，而且換一個 year 會跟著變")
    for year, why in [("113", "合法值"), ("102", "換一個年（⇒ 日期該跟著變）")]:
        url = (f"{DOC}?step=1&colorchg=1&co_id=2330&year={year}&mtype=A")
        st, ct, body, err = hit(url)
        lines.append(f"   送 year={year}｜{why}")
        if err:
            lines.append(f"      ⛔ 連不上：{err}")
            continue
        dates = upload_dates(body)
        lines.append(f"      HTTP={st}｜{ct}｜{len(body):,} bytes｜"
                     f"解出上傳日期 {len(dates)} 筆")
        if looks_blocked(body):
            lines.append("      ⛔⛔ **這是擋阻頁**")
        elif dates:
            lines.append(f"      最早：{dates[0]}｜最晚：{dates[-1]}")
        else:
            lines.append("      ⛔ 解不出上傳日期（⚠ 可能是 big5 沒解對，也可能是查無資料）")


def main():
    lines = [B.probe_stamp("財報期別參數與公告時點（情報線 20260923-1420 §三 代驗）")]
    lines.append("# ⛔ 這一支只讀不寫：不動 data/ 底下任何真資料")
    lines.append("# ⚠ 在開發容器／本機跑到的失敗**不是事實**（我方閘道對交易所 403）"
                 "⇒ 只有 Actions 上的結果算數")
    probe_mops(lines)
    probe_doc(lines)
    lines.append("")
    lines.append("⇒ ⭐ 怎麼讀這一份：兩節各自的判準寫在節首。"
                 "⛔ 任何一節只要出現「擋阻頁」或「講不出自己是哪一期」，")
    lines.append("   就**不可以**寫成「這條路可以自動化」——那正是情報線 1420 §三 要問的那件事。")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[probe] 寫出 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
