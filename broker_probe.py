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
import csv
import io
import json
import os
import re
import sys
import traceback

import backfill as B
from backfill import why as _W

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
        _p(lines, f"  ⛔ 失敗：{_W(err, 200)}")
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


def scale_lines():
    """⭐⭐ H1 分點：**這條路是對哪一種規模不可用**。→ list[str]。

    ## ⛔ 為什麼這一段要「算」而不是「寫」

    三點③：**沒有標規模的「不可用」，下一個人會拿它去擋一件它沒測過的事。**
    ⚠ 而擋住分點的三件事（驗證碼／逐檔查／只有當日）**全部是規模的函數**
    ⇒ 規模要是**量出來的數字**，⛔ 不是我記得的數字
    （2026-09-13 我寫「1,954 檔 × 245 日」，實測母體是 2,493／交易日 243）。
    """
    out = ["⭐⭐ H1 分點（券商買賣日報）：**這條路是對哪一種規模不可用**",
           "─" * 60,
           "⛔ 三點③：沒有標規模的「不可用」，下一個人會拿它去擋一件它沒測過的事。",
           "⚠ 而擋住分點的三件事——**驗證碼／逐檔查／只有當日**——全部是**規模的函數**。",
           ""]
    n_mkt, days = {}, 0
    try:
        with io.open(os.path.join(_ROOT, "meta", "stocks.csv"),
                     encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("kind") == "stock":
                    n_mkt[r.get("market") or "?"] = n_mkt.get(r.get("market") or "?", 0) + 1
    except OSError:
        pass
    d = os.path.join(_ROOT, "universe", "daily")
    if os.path.isdir(d):
        days = len([x for x in os.listdir(d) if x.startswith("2025") and x.endswith(".csv")])
    if not n_mkt or not days:
        # ⛔ 算不出來要**大聲說**，⚠ 不可以印一個看起來像量過的數字
        out += ["  ⛔⛔ **這一段沒跑**：這個 ref 上讀不到 `meta/stocks.csv` 或 "
                "`universe/daily/`",
                "     ⇒ ⚠ 規模是量出來的，量不到就**不寫數字**"
                "（⛔ 寫一個記得的數字比不寫更糟）"]
        return out
    listed = n_mkt.get("twse", 0) + n_mkt.get("tpex", 0)
    out += [f"  母體（`meta/stocks.csv` 的 `kind=stock`，⭐ 含已下市）："
            + "｜".join(f"{k} {v:,}" for k, v in sorted(n_mkt.items()))
            + f"｜上市＋上櫃 **{listed:,}**",
            f"  一年的交易日（`universe/daily/` 的 2025 檔名）：**{days}** 天",
            "",
            f"    全市場回補一年   {listed:,} 檔 × {days} 日 ≈ "
            f"**{listed * days:,}** 次請求",
            f"    追蹤一檔回補一年  1 檔 × {days} 日 = **{days}** 次",
            "    ⭐ 而 FinMind 那條 `?day=365` 一次請求就回整年 = **1** 次",
            "",
            "  逐項對照（同一個障礙，兩種規模的結論相反）",
            "    驗證碼    ⇒ 擋的是**自動化**。一檔一天輸一次，**人做得到**",
            "    逐檔查    ⇒ 追蹤單檔時**本來就只查一檔**，不是成本",
            "    只有當日  ⇒ 從今天開始一天記一次，一年後就有一年",
            "",
            "⇒ ⭐ **判死的不是「分點」這條路，是「全市場自動化」那一格。**",
            "",
            "⛔⛔ 而還有一個理由**跟規模無關**，不可以跟上面三個並排寫：",
            "     **條款禁「重製」。** 它在單檔也成立 ⇒ 任何規模都要先解決授權，",
            "     ⚠ 而我 2026-09-13 把它跟「請求量」並排寫成「兩個都獨立成立」，",
            "     ⛔ 看起來就像「到處都成立」——那正是使用者一句話戳破的地方。",
            "",
            "⇒ 本庫現況：**不落地任何分點資料**。⛔ 這不是「查不到」，"
            "是**授權沒有解決**。",
            "   ⚠ 而「技術上單檔做得到」要寫在這裡，⛔ 不可以被上面那句吃掉。"]
    return out


def probe_page(name, url, lines):
    _p(lines, "")
    _p(lines, "=" * 72)
    _p(lines, f"■ {name}")
    _p(lines, f"  {url}")
    raw, err = B.get(url, retries=2, timeout=40)
    if err:
        _p(lines, f"  ⛔ 頁面抓不到：{_W(err, 200)}")
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
                  "⚠ 它可能是**另外載入**的 JS 才組出來的。")
        # ⭐ 而「要人去開開發者工具看」**不是句點**——那一發寫在外部 `.js` 裡，
        #   而把它讀出來是程式做得到的事（`backfill.js_followups`，唯一那一份）。
        #   ⚠ 這跟 MOPS `t05st01`、櫃買 `announce/market/change*.html` 是同一族：
        #   inline 線索全 0 ⛔ 不是「站上沒有」。
        han, n_tr, n_js, shell = B.js_shell(raw)
        _p(lines, f"  [形狀] 中文 {han:,} 字｜<tr> {n_tr} 個｜js {n_js} 支"
                  + ("　⛔ **js 空殼**" if shell else ""))
        for ln in B.xhr_clues(raw, base=url):
            _p(lines, " " + ln)
        for ln in B.js_followups(raw, base=url):
            _p(lines, " " + ln)
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
    for ln in scale_lines():
        _p(lines, ln)
    rc = 0
    for name, url in PAGES:
        try:
            probe_page(name, url, lines)
        except Exception:                                      # noqa: BLE001
            rc = 1
            _p(lines, f"  ⛔ 這一條炸了：\n{traceback.format_exc()[:1200]}")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write(B.probe_stamp() + "\n".join(lines) + "\n")
    print(f"\n[broker_probe] 寫出 {OUT}（{len(lines)} 行）")
    return rc


if __name__ == "__main__":
    sys.exit(main())
