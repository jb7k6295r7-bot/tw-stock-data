#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""parvalue_probe.py — 變更股票面額恢復買賣參考價的端點探針。**只測、不寫資料。**

## 為什麼要有這一支

`data/adj/` 實測只有 **exright（除權息）與 reduce（減資）** 兩種事件，
**變更股票面額一筆都沒有**。

台股 2014 年起開放彈性面額。面額 10 元改 5 元 → 股數加倍、股價腰斬。
`data/stocks/` 是未還原價，跨過那一天會看到約 **50% 的假跌**——
與 2026-09-06 之前的減資是**同一種病**：沒有錯誤、沒有缺檔，
只是還原因子少了一類，長期報酬、均線、扣抵值全部悄悄變錯。

⚠ 最糟的不是缺，是**缺得看不見**：`adjust.py` 對減資有「一筆都沒讀到就警告」，
對面額變更連警告都沒有，因為它根本不在 `EVENT_DIRS` 裡。

## 來源

`reduce_probe.py` 2026-09-06 就辨識出它了：

| 來源 | 當時的結論 |
|---|---|
| TWSE `reducation/TWTAUU` | ✓ 減資，已接成 `reduce` feed |
| TWSE `change/TWTB8U` | 「**變更股票面額**恢復買賣參考價，不同的公司行動，不要混用」|

**那句話寫對了，但只寫成註解——從來沒有人去抓它。** 這一支就是去補。

## 四項判準（照 `reduce_probe.py` 的規矩，缺一不可）

1. `stat` 與標題
2. **完整欄位**
3. 列數
4. **日期欄的最小與最大值** ← 最重要，它直接回答「有沒有歷史」

★ 只有第 4 項能分辨「端點可用」與「端點有我要的歷史」。
  前三項全對但日期全是未來十天，這條就不能用——那正是 TPEx `bulletin/revivt`
  的現況。

## ⚠ 參數回音

TWSE 踩過：`TWT49U` **不吃 `date` 卻把它原樣回傳**，於是日期核對被騙過，
把當天的四列寫進 2015 年的每一個日期檔。所以本檔**換兩個不同區間各打一發，
比對回應的標題與列數**——一樣就是參數被無視，不是有歷史。
"""
import io
import json
import os
import sys

import backfill as B

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(_ROOT, "meta", "_parvalue_probe.txt")

# 路徑取自 reduce_probe.py 2026-09-06 的實測紀錄，非自行生成。
# 參數沿用同站的 reducation/TWTAUU（startDate/endDate）——**這是待驗的假設**，
# 不是已知事實，所以下面用兩個區間對打來檢驗。
BASE = "https://www.twse.com.tw/rwd/zh/change/TWTB8U"
RANGES = [("20150101", "20151231"), ("20200101", "20201231"),
          ("20260101", "20260908")]

LINES = []


def say(s=""):
    print(s, flush=True)
    LINES.append(s)


def one(a, b):
    url = f"{BASE}?startDate={a}&endDate={b}&response=json"
    say(f"\n  ── {a} ~ {b}")
    say(f"     {url}")
    raw, err = B.get(url, retries=2, timeout=60)
    if err:
        say(f"     ✗ {err[:140]}")
        # ★ 「被限流擋下」與「端點沒有這個東西」是兩件事。
        #   backfill.get() 已經幫我們分好了：3xx 無 Location 或 429 → `LIMITED|`。
        #   2026-09-08 21:29 那趟三個區間全是 LIMITED——同一趟裡 feeds:reduce、
        #   mops 的 11 張 twse 表、suspend 的 2 個請求也一起被擋，
        #   **那是 IP 被限流，不是 TWTB8U 壞了**。混為一談就會去改根本沒錯的參數。
        if str(err).startswith("LIMITED"):
            return "LIMITED"
        return None
    try:
        d = json.loads(raw.decode("utf-8", "replace"))
    except Exception as ex:                                      # noqa: BLE001
        say(f"     ✗ 非 JSON：{type(ex).__name__}｜開頭 "
            f"{raw[:100].decode('utf-8', 'replace')}")
        return None
    stat = d.get("stat") if isinstance(d, dict) else None
    title = d.get("title") if isinstance(d, dict) else None
    say(f"     [1] stat={stat!r}｜title={title!r}")
    tabs = B._tables(d)
    if not tabs:
        say("     [2] 沒有 tables——**沒有事件的區間本來就會這樣**，不等於端點壞掉")
        return {"stat": stat, "title": title, "n": 0, "lo": "", "hi": ""}
    t = tabs[0]
    fields = [str(x) for x in (t.get("fields") or [])]
    data = t.get("data") or []
    say(f"     [2] 欄位（{len(fields)}）：{fields}")
    say(f"     [3] 列數：{len(data)}")
    if data:
        say(f"         首列：{data[0]}")
    # [4] 日期欄的最小與最大——唯一能回答「有沒有歷史」的那一項
    dates = []
    for r in data:
        for v in (r or [])[:3]:
            s = "".join(ch for ch in str(v) if ch.isdigit())
            if len(s) in (7, 8):          # 民國 1150907 或西元 20260907
                dates.append(str(v).strip())
                break
    if dates:
        say(f"     [4] ★ 日期欄 {min(dates)} ~ {max(dates)}（{len(dates)} 列有日期）")
    else:
        say("     [4] ⚠ 抽不到日期欄——**這一項沒答出來就不能說它有歷史**")
    return {"stat": stat, "title": title, "n": len(data),
            "lo": min(dates) if dates else "", "hi": max(dates) if dates else "",
            "fields": fields}


def main():
    say("── 變更股票面額恢復買賣參考價 探針 ──")
    say(f"端點（取自 reduce_probe.py 的實測紀錄）：{BASE}")
    say("⚠ 參數 startDate/endDate 是**沿用同站減資端點的假設**，本檔要驗它成不成立。")
    got = [one(a, b) for a, b in RANGES]

    say("\n── ★ 參數有沒有被無視 ──")
    say("TWSE 踩過：`TWT49U` 不吃 `date` 卻把它原樣回傳，日期核對被騙過，"
        "把當天的四列寫進 2015 年的每一個日期檔。")
    limited = [g for g in got if g == "LIMITED"]
    ok = [g for g in got if isinstance(g, dict)]
    if limited and not ok:
        say(f"  ⚠ **本趟 {len(limited)}/{len(RANGES)} 個區間全部被限流擋下（LIMITED），"
            "四項判準一項都沒答出。**")
        say("     這**不是**「端點不存在」，也**不是**「參數無效」——是這個時間點的 IP 被擋。")
        say("     限流要用分鐘級退避；同一趟裡 TWSE 其他抓取也一起失敗就是旁證。")
        say("     → 下一趟排程會自己再測一次（探針的重跑條件已含輸出含 ✗）。")
        say("     ⛔ 在真的答出四項之前，`adjust.py` 對面額變更仍然是**完全沒有還原**。")
    elif len(ok) < 2:
        say("  （成功的區間不足兩個，無法對打——先解決上面的失敗）")
    else:
        sig = {(g["title"], g["n"], g["lo"], g["hi"]) for g in ok}
        if len(sig) == 1:
            say("  ⛔ **三個區間回的標題、列數、日期範圍完全一樣**——"
                "參數被無視，這條路不能用來回補歷史。")
        else:
            say("  ✓ 不同區間回不同內容，參數有生效。")
            for (a, b), g in zip(RANGES, got):
                if isinstance(g, dict):
                    say(f"     {a}~{b}：{g['n']} 列｜日期 {g['lo']} ~ {g['hi']}")
                elif g == "LIMITED":
                    say(f"     {a}~{b}：被限流擋下，這一格沒有答案")

    # ── ★★ 涵蓋範圍：它到底收不收上櫃 ──
    #   2026-09-09 有人回報「主來源就是 TWTB8U」。TWTB8U 確實是對的來源，
    #   但**只對上市那一半**——這一節把它變成每趟都量的數字，不要再靠推論。
    #   靶子取自 `parvalue_scan.py` 的全庫掃描：同一個區間內已知存在的
    #   上市與上櫃事件各列一組，看回應裡有沒有。
    #   ⛔ 「回了東西」不算涵蓋，**要點名的那幾檔真的出現**才算。
    say("\n── ★★ 涵蓋範圍：TWTB8U 收不收上櫃 ──")
    EXPECT = ("20260101", "20260908", [
        ("7780", "大研生醫", "twse", "115/01/19"),
        ("6949", "沛爾生醫", "twse", "115/09/07"),
        ("8932", "智通", "tpex", "115/03/09"),
        ("8937", "合騏", "tpex", "115/04/13"),
        ("3086", "華義", "tpex", "115/04/20"),
        ("5904", "寶雅", "tpex", "115/08/10"),
        ("4747", "強生", "tpex", "115/08/31")])
    a, b, want = EXPECT
    g = next((x for x, (aa, bb) in zip(got, RANGES)
              if (aa, bb) == (a, b) and isinstance(x, dict)), None)
    if not g:
        say(f"  （{a}~{b} 那一發沒成功，這一節量不了）")
    else:
        url = f"{BASE}?startDate={a}&endDate={b}&response=json"
        raw, err = B.get(url, retries=2, timeout=60)
        codes = set()
        if not err:
            try:
                dd = json.loads(raw.decode("utf-8", "replace"))
                for t in (B._tables(dd) or []):
                    for r in (t.get("data") or []):
                        for v in (r or [])[:3]:
                            v = str(v).strip()
                            if v.isdigit() and len(v) == 4:
                                codes.add(v)
            except Exception:                                    # noqa: BLE001
                pass
        hit = {"twse": 0, "tpex": 0}
        tot = {"twse": 0, "tpex": 0}
        for sid, nm, mk, dt in want:
            tot[mk] += 1
            ok = sid in codes
            hit[mk] += 1 if ok else 0
            say(f"  {'✓' if ok else '✗'} {sid} {nm}（{mk}，{dt}）"
                f"{'' if ok else '  ← 沒有回來'}")
        say(f"  → 上市 {hit['twse']}/{tot['twse']}｜上櫃 {hit['tpex']}/{tot['tpex']}")
        if tot["tpex"] and hit["tpex"] == 0:
            say("  ⛔ **同一發請求裡上市全中、上櫃全不中——TWTB8U 不涵蓋上櫃。**")
            say("     上櫃那 14 筆面額變更仍然沒有來源，`data/adj/` 也就仍然沒有還原它們。")
            say("     要找的是 **TPEx 對應的「變更股票面額恢復買賣參考價」端點**，")
            say("     不是再確認一次 TWTB8U。")
        elif hit["tpex"]:
            say("  ★ 上櫃也回得出來——**那推翻了先前的結論**，"
                "去把 EVENT_DIRS 的 market 標記與 db_status 一起改掉。")

    say("\n── 下一步 ──")
    say("四項判準都答出來、而且參數確定有生效，才可以接成 feed 並加進")
    say("`adjust.py` 的 EVENT_DIRS 與 BOUNDS。")
    say("⚠ 面額變更的因子可能 <1（10→5，f≈0.5）也可能 >1（5→10，f≈2），")
    say("  **除權息那組 0.05~1.5 的界線套上來會把一半的真事件丟掉**——")
    say("  界線要按事件種類分開訂，這是減資那次已經學過的。")

    try:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        io.open(OUT, "w", encoding="utf-8").write(
            "# parvalue_probe.py 的輸出。這是探針結果，不是資料。\n"
            f"# 端點：{BASE}\n\n" + "\n".join(LINES) + "\n")
        print(f"\n[parvalue] 寫出 {OUT}")
    except OSError as ex:                                        # noqa: BLE001
        print(f"[parvalue] 寫檔失敗：{ex}", file=sys.stderr)
    return 0 if any(isinstance(g, dict) for g in got) else 1


if __name__ == "__main__":
    sys.exit(main())
