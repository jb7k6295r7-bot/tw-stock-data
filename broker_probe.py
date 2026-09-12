#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""broker_probe.py — 上櫃「個股 × 券商進出」那兩條，照 `docs/NEW_ENDPOINT.md` 開一次。

## 為什麼只剩這兩條（範圍寫在前面，⛔ 不要讀成通則）

2026-09-12 拿**全站選單**問「券商／分公司／分點」：

    TWSE  選單 281 條 → 命中 7 條，**沒有一條**是個股 × 分點進出【實測】
    TPEx  選單 762 條 → 命中 34 條，其中 32 條是券商基本資料／月報／名單
          ⇒ 真正相關的只有這兩條【實測】

        /zh-tw/mainboard/trading/historical/broker-vol.html
        /zh-tw/mainboard/trading/historical/broker-amt.html

⚠ 而標題裡的「**熱門股**」與「**排行**」兩個詞都指向
  「不是全市場、不是全部分點」——⛔ 那是**推定**，這一支就是要把它變成實測。

TWSE 那邊的個股 × 分點是 `bsr.twse.com.tw/bshtm/`：
⛔ 有驗證碼、一次一檔、無日期選擇器 ⇒ **技術上不能自動化**（`bsr_probe.py` 實測）。
⚠ 那是「取不到」，⛔ 不是「官方沒有」——兩者不可互換。

## 這一支問什麼（⛔ 順序不可跳，CLAUDE.md 第一點）

    ① HTML 頁面本身：狀態／型別／位元組／`<title>`
    ② 頁面裡指向的**資料端點**（新站的頁面用 JS 打 `/www/zh-tw/...` 那一族）
    ③ ⭐ 打到資料端點之後，**先把全部頂層鍵印出來**，再談內容
       （`notes`／`hints`／`params`／`total` 每一個都對應一件我方手工做過的事）
    ④ `params` 有沒有把我送的日期**回顯**回來 ⇒ 參數是不是假的
    ⑤ 母體有多大：幾檔、幾家券商 ⇒ 回答「全市場還是熱門股」
    ⑥ 歷史到哪裡：拿一個**很舊**的日期去問，看它是大聲失敗還是靜靜回最新

⛔ 這一支**只測不寫資料**。輸出進 `data/meta/_broker_probe.txt`。
"""
import io
import json
import os
import re
import sys
import traceback

import backfill as B

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(_ROOT, "meta", "_broker_probe.txt")

PAGES = [
    ("上櫃 熱門股券商進出（量）", "https://www.tpex.org.tw/zh-tw/mainboard/trading/historical/broker-vol.html"),
    ("上櫃 熱門股券商進出（金額）", "https://www.tpex.org.tw/zh-tw/mainboard/trading/historical/broker-amt.html"),
]

# ⚠ 新站的資料端點長這樣：`/www/zh-tw/<區>/<名>`。⛔ 這是從頁面裡**掃出來**的，
#   不是我猜的——猜出來的路徑打不通時，分不出「路徑錯」與「端點沒了」。
_URL_RE = re.compile(r"""["'](/www/[a-zA-Z0-9/_\-]+)["']""")

RECENT = "2026-09-11"      # 一定有資料的近期交易日
ANCIENT = "2015-01-05"     # ⭐ 拿它問「歷史到哪裡」


def _p(lines, s=""):
    print(s, flush=True)
    lines.append(s)


def _spread(rows, lines, cap=6):
    """陣列型回應：印**每個鍵的相異值分佈**（CLAUDE.md 第二點⑤）。

    ⭐ 相異值只有一種的鍵，**當場就把涵蓋期間講出來了**
      （`tpex_spendi_history` 的 `Date` 只有民國 115 一種 ⇒ 它不是歷史）。
    ⛔ 相異值多的只印最小最大，不洗版。
    """
    if not rows or not isinstance(rows[0], (list, tuple)):
        _p(lines, "  ⚠ 不是二維陣列，跳過分佈")
        return
    n = max(len(r) for r in rows)
    for i in range(n):
        vals = {str(r[i]) for r in rows if i < len(r)}
        if len(vals) == 1:
            _p(lines, f"  欄{i}：相異值 **1 種** ⇒ {sorted(vals)[0]!r} × {len(rows)}")
        elif len(vals) <= cap:
            _p(lines, f"  欄{i}：相異值 {len(vals)} 種 ⇒ {sorted(vals)}")
        else:
            s = sorted(vals)
            _p(lines, f"  欄{i}：相異值 {len(vals)} 種｜min={s[0]!r} max={s[-1]!r}")


def _ask(url, lines, want=None):
    """打一發 → (doc 或 None)。⭐ 先印全部頂層鍵，再談內容。"""
    raw, err = B.get(url, retries=2, timeout=40)
    if err:
        _p(lines, f"  ⛔ 失敗：{err[:200]}")
        return None
    _p(lines, f"  {len(raw)} bytes")
    try:
        doc = json.loads(raw.decode("utf-8"))
    except Exception as ex:                                    # noqa: BLE001
        head = raw[:200].decode("utf-8", "replace").replace("\n", " ")
        _p(lines, f"  ⛔ 不是 JSON（{type(ex).__name__}）｜開頭：{head}")
        return None
    # ⭐⭐ CLAUDE.md 第一點：**第一件事**是把 notes／hints／title／params 印出來
    for ln in B.describe_response(doc, want=want):
        _p(lines, f"  {ln}")
    return doc


def probe_page(name, url, lines):
    _p(lines, "")
    _p(lines, "=" * 72)
    _p(lines, f"■ {name}")
    _p(lines, f"  {url}")
    raw, err = B.get(url, retries=2, timeout=40)
    if err:
        _p(lines, f"  ⛔ 頁面抓不到：{err[:200]}")
        _p(lines, "  ⚠ 這個容器對交易所一律 403（我方閘道）⇒ "
                  "⛔ 在這裡看到的失敗**不是事實**，要看 Actions 上那一份。")
        return
    html = raw.decode("utf-8", "replace")
    ttl = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    _p(lines, f"  {len(raw)} bytes｜<title> {ttl.group(1).strip() if ttl else '（無）'}")
    found = sorted(set(_URL_RE.findall(html)))
    _p(lines, f"  頁面裡掃到 {len(found)} 個 /www/ 路徑：")
    for f in found[:30]:
        _p(lines, f"      {f}")
    cands = [f for f in found if re.search(r"broker|deal|trad", f, re.I)]
    if not cands:
        _p(lines, "  ⛔ 沒掃到看起來像資料端點的路徑 ⇒ "
                  "⚠ 它可能是**另外載入**的 JS 才組出來的。"
                  "⇒ 這一條要人去開開發者工具看，⛔ 不要在這裡猜。")
        return
    _p(lines, f"  ⇒ 候選資料端點 {len(cands)} 條：{cands}")

    for path in cands[:3]:
        for day, why in ((RECENT, "近期（一定有資料）"), (ANCIENT, "⭐ 很舊（問歷史下限）")):
            q = f"https://www.tpex.org.tw{path}?date={day}&response=json"
            _p(lines, "")
            _p(lines, f"  ── {path}｜{why} date={day}")
            doc = _ask(q, lines, want={"date": day})
            if not isinstance(doc, dict):
                continue
            tabs = B._tables(doc)
            for ti, t in enumerate(tabs):
                data = t.get("data") or []
                _p(lines, f"  表{ti}：{t.get('title', '')!r}｜"
                          f"{len(t.get('fields') or [])} 欄 × {len(data)} 列")
                _p(lines, f"       欄名：{t.get('fields')}")
                _spread(data[:4000], lines)


def main():
    lines = []
    import runlog
    _p(lines, f"broker_probe.py　{runlog.now_tpe():%Y-%m-%d %H:%M} 台北")
    _p(lines, "⭐ 問的是：這兩條到底是**全市場 × 全部分點**，還是「熱門股排行」。")
    _p(lines, "⛔ 判準不是「有回列」——是**它自己講不講得出它是哪一天、涵蓋誰**。")
    rc = 0
    for name, url in PAGES:
        try:
            probe_page(name, url, lines)
        except Exception:                                      # noqa: BLE001
            rc = 1
            _p(lines, f"  ⛔ 這一條炸了：\n{traceback.format_exc()[:1200]}")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"\n[broker_probe] 寫出 {OUT}（{len(lines)} 行）")
    return rc


if __name__ == "__main__":
    sys.exit(main())
