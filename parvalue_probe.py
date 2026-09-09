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
import csv
import io
import json
import os
import sys
import traceback
from datetime import datetime, timedelta, timezone

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

    # ── ★ 順帶把同一族的另外兩支也量一次 ──
    #   三支是同一張形態（恢復買賣參考價表），但**是三種不同的公司行動**：
    #     reducation/TWTAUU  減資（多一欄「減資原因」）
    #     change/TWTB8U      變更股票面額            ← 本檔主角
    #     split/TWTCAU       ETF 分割／反分割
    #   ⛔ 三支不可以混用，混了會把不同性質的事件算成同一種。
    #   ⚠ `reducation` 是證交所自己拼錯的（不是 reduction），**照抄，不要「訂正」**。
    #
    #   ⛔⛔ 一條要避開的錯路（2026-09-09 使用者查證）：
    #     `www.twse.com.tw/zh/listed/violations/stop.html`（「停止買賣」）
    #     **不是**這一族。它頁面自己寫明只收「因財務業務發生異常」，
    #     **明文排除組織變更、重整、減資**。名字最像、內容完全不對。
    say("\n── ★ 同一族的另外兩支（順帶量欄位，三支不可混用）──")
    say("  ⚠ `reducation` 是證交所自己拼錯的，照抄不要訂正。")
    say("  ⛔ `zh/listed/violations/stop.html` 不是這一族——它只收財務業務異常，"
        "明文排除組織變更、重整、減資。名字最像、內容完全不對。")
    #   ⭐ 2026-09-09 使用者又提供了一支：`change/TWTB7U`。
    #     TWTB8U 是**恢復買賣參考價**（事後、換完之後的價）；
    #     TWTB7U 從頁名看是同一族的另一半（很可能是**停止買賣／預告**那一張）。
    #     ⛔ 但那是從頁名猜的——**量到欄位才算數**，所以放進來一起量，不先寫用途。
    #     若它帶得出「停止買賣日／換發比例」，上市那半就多一個獨立欄位可以交叉驗。
    for label, path, a2, b2 in (
            ("減資 reducation/TWTAUU", "reducation/TWTAUU", "20150101", "20151231"),
            ("ETF 分割 split/TWTCAU", "split/TWTCAU", "20250101", "20251231"),
            ("⭐ change/TWTB7U（使用者提供，用途待量）",
             "change/TWTB7U", "20250101", "20251231")):
        say(f"\n  ── {label}｜{a2}~{b2}")
        r3, e3 = B.get(f"https://www.twse.com.tw/rwd/zh/{path}"
                       f"?startDate={a2}&endDate={b2}&response=json",
                       retries=2, timeout=60)
        if e3:
            say(f"     ✗ {str(e3)[:120]}")
            continue
        try:
            d3 = json.loads(r3.decode("utf-8", "replace"))
        except Exception as ex:                                  # noqa: BLE001
            say(f"     ✗ 非 JSON：{type(ex).__name__}")
            continue
        t3 = (B._tables(d3) or [{}])[0]
        fl = [str(x) for x in (t3.get("fields") or [])]
        dt3 = t3.get("data") or []
        say(f"     stat={d3.get('stat')!r}｜title={d3.get('title')!r}")
        say(f"     欄位（{len(fl)}）：{fl}")
        say(f"     列數：{len(dt3)}")
        if dt3:
            say(f"     首列：{dt3[0]}")
        # TWTCAU 專屬：對方點名的 11 檔，這一年應該中到 5 檔
        if "TWTCAU" in path:
            want = {"00663L": "2025-06-11", "0050": "2025-06-18",
                    "00673R": "2025-10-22", "00706L": "2025-10-22",
                    "0052": "2025-11-26"}
            codes = {str(v).strip() for r in dt3 for v in (r or [])[:3]}
            for c, dd in sorted(want.items()):
                say(f"     {'✓' if c in codes else '✗'} {c}（掃描實測 {dd}）")
            say(f"     → 2025 這年命中 {len(set(want) & codes)}/{len(want)}"
                "（靶子取自 parvalue_scan.py，不是從回應反推）")

    # ─────────────────────────────────────────────────────────────────
    say("\n[T7] ★★ change/TWTB7U 把它問到底（使用者 2026-09-09 13:45 又給了一個形式）")
    # 上一趟已經量出來：stat=OK、title=**變更股票面額預告表**、10 欄，
    # 其中 `變更股票面額換股率`／`變更前面額`／`變更後面額` 是 TWTB8U **沒有**的。
    # ⇒ 若它吃得下長區間，上市那半就有**精確換股率**可用，
    #   跟上櫃用股數倍率同一個等級——而不是只能拿參考價比值。
    # ★ 使用者給的形式是 `?response=html`、**不帶日期**——那是我沒試過的第三種。
    #   ⛔ 三種都量，⛔ 不要因為「上一趟有回東西」就假設參數有生效
    #     （這個專案被靜默截斷騙過兩次）。
    T7 = "https://www.twse.com.tw/rwd/zh/change/TWTB7U"

    def _t7(label, url):
        r, e = B.get(url, retries=2, timeout=60)
        if e:
            say(f"     ✗ {label}：{str(e)[:110]}")
            return None
        txt = r.decode("utf-8", "replace")
        if "response=html" in url:
            # html 版只量形狀：有幾個 <tr>、抓不抓得到民國日期
            import re as _re
            tr = len(_re.findall(r"<tr[ >]", txt, _re.I))
            dts = sorted(set(_re.findall(r"\b1[0-9]{2}/[0-9]{2}/[0-9]{2}\b", txt)))
            say(f"     ✓ {label}：{len(r):,} bytes｜<tr> {tr} 個｜"
                f"民國日期 {len(dts)} 個{('｜' + dts[0] + ' ~ ' + dts[-1]) if dts else ''}")
            return None
        try:
            d = json.loads(txt)
        except Exception as ex:                                  # noqa: BLE001
            say(f"     ✗ {label}：不是 JSON（{type(ex).__name__}）｜{len(r):,} bytes")
            return None
        t = (B._tables(d) or [{}])[0]
        dt = t.get("data") or []
        say(f"     ✓ {label}：stat={d.get('stat')!r}｜title={d.get('title')!r}"
            f"｜列數 {len(dt)}")
        return dt

    say("  ── ① 使用者給的形式（不帶日期、response=html）")
    _t7("html 無日期", f"{T7}?response=html")
    say("  ── ② 同一個網址但要 json、仍然不帶日期")
    _t7("json 無日期", f"{T7}?response=json")
    say("  ── ③ 長區間：2015-01-01 ~ 今天（**這一項是重點**）")
    #   ⚠ 判準不是「有沒有回東西」，是**列數有沒有比一年那次多**。
    #     只回 1 列就代表區間沒生效，跟上一趟一樣——那要改成逐年迴圈。
    today = datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d")
    wide = _t7("2015~今天", f"{T7}?startDate=20150101&endDate={today}&response=json")
    if wide is not None:
        say(f"     ⇒ 長區間拿到 **{len(wide)} 列**。"
            + ("**區間有生效**（比 2025 那次的 1 列多）。"
               if len(wide) > 1 else
               "⛔ **和一年那次一樣少 ⇒ 區間多半沒生效**，下一步要逐年迴圈。"))
        # ★ 逐筆對我方 par_change.csv 的上市那 10 筆。
        #   ⛔ 這一段的價值在於：換股率是**官方寫出來的數字**，
        #     不是我方從價格或股數推的——是真正的第三個獨立來源。
        try:
            mine = {}
            with io.open(os.path.join(_ROOT, "meta", "par_change.csv"),
                         encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    mine[row["stock_id"]] = row
            hit = miss = 0
            def _cell(row, i):
                # ⛔ 不可以寫成 `(row or [""]*n)[i]`：row 非空但比 n 短時
                #   `or` 不會補齊，照樣 IndexError（2026-09-09 被 selftest 擋下）。
                row = row if isinstance(row, (list, tuple)) else []
                return str(row[i]).strip() if i < len(row) else ""

            for r in wide:
                sid = _cell(r, 1)
                rate = _cell(r, 4)
                q = mine.get(sid)
                if not q:
                    continue
                try:
                    ok = abs(float(rate) - float(q["share_mult"] or 0)) < 1e-6
                except ValueError:
                    ok = False
                hit += ok
                miss += (not ok)
                say(f"       {sid}｜官方換股率 {rate}｜我方 share_mult "
                    f"{q['share_mult'] or '（空）'}｜{'✓' if ok else '✗ 不符'}")
            say(f"     ⇒ 對上 {hit} 筆｜不符 {miss} 筆")
        except OSError as ex:                                    # noqa: BLE001
            say(f"     （對帳跳過：{ex}）")

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
    # ⚠ 探針炸掉時，traceback 只留在 Actions log 裡——而 log 要翻好幾百行才找得到，
    #   （2026-09-09 實測：tail 900 行都還沒回到那一步）。
    #   ⇒ **把 traceback 寫進輸出檔**，它會跟著 commit 進 repo。
    #   這樣「哪一節炸的」下一趟就是既成事實，不必再去考古。
    #   ⛔ 覆蓋掉上一次成功的內容是**故意的**：這一份的語意是「這一趟看到什麼」，
    #     上一次的內容在 git 歷史裡找得到，而「看起來是完整結果、其實是上一趟的」
    #     比缺一份更貴。開頭那個 ✗ 也讓下一趟的重跑條件自動成立。
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException:                                        # noqa: BLE001
        say("")
        say("✗ 這一趟在下面這裡炸掉了，以下是 traceback 原文（沒有整理）：")
        say(traceback.format_exc())
        _write(1)
        raise
