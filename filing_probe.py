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
⇒ ⭐ 對照組至少要有一組是**已知合法**的值（合法值寫在人類填的那張表單上：
`year` 要民國年、`dataType="2"` 才是歷史）。
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


def _mops_body(year, season, dtype, cid="2330"):
    return json.dumps({"companyId": cid, "dataType": dtype,
                       "season": season, "year": year}).encode()


def probe_mops(lines):
    lines.append("")
    lines.append("══ ① MOPS t164sb03（POST／JSON）══")
    lines.append(f"   端點：{MOPS}")
    lines.append("   ⛔ 判準：回應要自己講出 result.year／result.season，"
                 "⚠ 不是看 HTTP 200")
    hdr = {"Content-Type": "application/json", "Accept": "application/json"}
    # ⭐ 三發：合法歷史值／換一個季（只改一個參數）／dataType=1 的對照組
    cases = [("113", "1", "2", "合法歷史值（民國年＋dataType=2）"),
             ("113", "3", "2", "只改 season（⇒ 數字該跟著變）"),
             ("113", "1", "1", "對照組：dataType=1（⇒ 情報線量到它一律回最新季）")]
    for year, season, dtype, why in cases:
        st, ct, body, err = hit(MOPS, _mops_body(year, season, dtype), hdr)
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
        lines.append(tag)
        lines.append(f"      HTTP={st}｜{ct}｜{len(body):,} bytes")
        if blocked:
            lines.append("      ⛔⛔ **這是擋阻頁**（HTTP 200 也算），"
                         "⚠ 只驗狀態碼會把它當成資料")
        elif said is None:
            lines.append("      ⛔ 回應**講不出自己是哪一期**（沒有 result.year／season）"
                         f"⇒ 前 120 字：{body[:120]!r}")
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
