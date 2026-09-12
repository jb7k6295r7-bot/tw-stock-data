#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""finmind_probe.py — FinMind 的**權限與涵蓋期間**探針。⛔ 只測、不寫資料。

## 為什麼要有這一支（K線分析線 2026-09-12 01:15）

他們在四個第三方站之間找「分點」與「集保大戶持股長歷史」，繞了遠路
⇒ 而 FinMind 兩個都有，而且它一直在 `tw-data-sources` 裡被引用。

他們指名一格「**決定一切**」：

    TaiwanStockTradingDailyReport（台股分點資料表）的**涵蓋起始年**
    ⭐ 若也是 2010 起 ⇒ 「每日累積」整件事不必做
    ⛔ 若只有近期 ⇒ 付費也解決不了回測，仍然要累積

## ⛔ 這一支要回答的是**兩種完全不同的失敗**

⚠ FinMind 沒有資料與沒有權限，**回應長得不一樣但都不是例外**：

    沒有權限   HTTP 400／402，或 200 但 `msg` 講權限
    沒有資料   HTTP 200、`msg=success`、而 `data` 是**空陣列**

⛔ 把兩者混成「取不到」，下一步會完全相反（一個是付費、一個是累積）。
⇒ 本支**逐條把 HTTP 狀態碼與 `msg` 原文印出來**，⛔ 不做歸納。

## ⭐ 而「涵蓋起始年」不可以用「有回列」當判準（CLAUDE.md 第二點）

⇒ 判準是**那一批自己講出它是哪一段**：把回應裡 `date` 欄的
**最小值、最大值、相異值個數**印出來。
⚠ 我要 2010 年，它回 2024 年的列 ⇒ 那是「靜靜回最新一期」，⛔ 不是涵蓋 2010。
"""
import io
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backfill as B                                           # noqa: E402

TPE = timezone(timedelta(hours=8))
API = "https://api.finmindtrade.com/api/v4/data"
LIST_API = "https://api.finmindtrade.com/api/v4/datalist"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "data", "meta", "_finmind_probe.txt")


def ask(url):
    """→ (dict 或 None, 說明)。⛔ 把**原始狀態**帶回來，不吞。"""
    raw, err = B.get(url, retries=2, timeout=45)
    if err:
        return None, f"⛔ {err}"
    try:
        d = json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        head = raw[:160].decode("utf-8", "replace").replace("\n", " ")
        return None, f"⛔ 非 JSON（{len(raw):,}B）：{head}"
    return d, f"{len(raw):,}B"


def describe(d, out):
    """⭐ CLAUDE.md 第一點：**先把頂層鍵與 `msg` 原文印出來**，再談別的。"""
    if not isinstance(d, dict):
        out.append(f"    ⛔ 回的不是物件，是 {type(d).__name__}")
        return []
    out.append(f"    頂層鍵：{sorted(d)}")
    for k in ("msg", "status"):
        if k in d:
            out.append(f"    {k} 原文：{d[k]!r}")
    rows = d.get("data")
    if not isinstance(rows, list):
        out.append(f"    ⛔ `data` 不是陣列，是 {type(rows).__name__}")
        return []
    out.append(f"    data 列數：{len(rows):,}")
    if rows:
        out.append(f"    第一列的鍵：{sorted(rows[0])}")
    return rows


def spread(rows, key, out, top=6):
    """⭐ 那一批**自己講出它是哪一段**（第二點）。⛔ 不用「有回列」當判準。"""
    vals = sorted({str(r.get(key, "")) for r in rows if r.get(key) is not None})
    vals = [v for v in vals if v]
    if not vals:
        out.append(f"    ⛔ `{key}` 一個值都沒有 ⇒ **講不出它是哪一段**")
        return
    out.append(f"    `{key}`：相異 {len(vals)} 種｜最小 {vals[0]}｜最大 {vals[-1]}"
               + (f"｜全部：{vals}" if len(vals) <= top else ""))


def probe(name, url, out, want=""):
    out.append(f"\n── {name} ──")
    out.append(f"  URL：{url.replace(TOKEN, '<TOKEN>') if TOKEN else url}")
    if want:
        out.append(f"  ⭐ 我請求的：{want}")
    d, note = ask(url)
    out.append(f"  回應：{note}")
    if d is None:
        return []
    return describe(d, out)


TOKEN = os.environ.get("FINMIND_TOKEN", "").strip()


def main():
    out = [f"# finmind_probe.py 的輸出。⛔ 這是探針結果，不是資料。",
           f"# 產生時間：{datetime.now(TPE).isoformat(timespec='seconds')}（台北）",
           ""]
    # ⭐ 第一件事：我方到底有沒有 token。⛔ 這決定了下面每一條怎麼讀。
    out.append(f"⭐ 我方 `FINMIND_TOKEN`：**{'有' if TOKEN else '無'}**"
               + (f"（長度 {len(TOKEN)}）" if TOKEN else
                  "　⇒ ⛔ 下面的權限結論只代表**免費層**"))
    tk = f"&token={TOKEN}" if TOKEN else ""

    # ── Q1 ⭐⭐ 分點資料表的涵蓋起始年（K線分析線說「這一格決定一切」）──
    out.append("\n" + "=" * 62)
    out.append("Q1 ⭐⭐ `TaiwanStockTradingDailyReport` 的**涵蓋起始年**")
    out.append("=" * 62)
    for lo, hi, why in (("2010-01-01", "2010-01-31", "⭐ 要 2010，看它回什麼"),
                        ("2015-01-05", "2015-01-09", "2015"),
                        ("2026-09-01", "2026-09-05", "近期（對照組）")):
        rows = probe(f"TradingDailyReport {lo}~{hi}",
                     f"{API}?dataset=TaiwanStockTradingDailyReport"
                     f"&data_id=2330&start_date={lo}&end_date={hi}{tk}",
                     out, want=f"{lo} ~ {hi}｜{why}")
        if rows:
            spread(rows, "date", out)
            # ⛔ 我要 2010、它回別年 ⇒ 那是靜默失敗，不是涵蓋
            ds = sorted({str(r.get("date", "")) for r in rows})
            if ds and not (ds[0] >= lo and ds[-1] <= hi):
                out.append("    ⛔⛔ **回的日期不在我請求的區間內**"
                           " ⇒ 這不是涵蓋，是靜默失敗（第二點）")

    # ── Q2 集保分級：⛔ 分清「沒權限」與「沒資料」──
    out.append("\n" + "=" * 62)
    out.append("Q2 `TaiwanStockHoldingSharesPer`（集保分級）："
               "⛔ 沒權限 vs 沒資料")
    out.append("=" * 62)
    out.append("⚠ 我方 `tdcc_probe.py` 檔頭記著它「回 HTTP 400」，"
               "⛔ 而那一句**沒寫當時有沒有帶 token** ⇒ 這裡兩種都問一次。")
    for lab, t in (("不帶 token", ""), ("帶 token", tk)):
        if lab == "帶 token" and not TOKEN:
            out.append("\n── 帶 token ── ⛔ 跳過：我方沒有 token")
            continue
        rows = probe(f"HoldingSharesPer（{lab}）",
                     f"{API}?dataset=TaiwanStockHoldingSharesPer"
                     f"&data_id=2330&start_date=2010-01-01&end_date=2010-12-31{t}",
                     out, want="2010 全年（K線分析線說它 2010-01-29 起）")
        if rows:
            spread(rows, "date", out)

    # ── Q3 資料集總表：籌碼面還有什麼 ──
    out.append("\n" + "=" * 62)
    out.append("Q3 資料集總表（⛔ 不猜端點名，照官方清單）")
    out.append("=" * 62)
    # ⛔⛔ 2026-09-12 訂正：我第一版拿 `/api/v4/datalist` **不帶參數**去要「資料集總表」，
    #   回了 84B、`msg=success`，我把它印成「共 6 個資料集、籌碼面 0 個」。
    #   ⚠ 而 K線分析線那份有 **94 個** ⇒ **我端點用錯了**
    #     （`datalist` 列的是某個 dataset 的 `data_id`，⛔ 不是列 dataset）。
    # ⇒ ⭐ 這一格**不猜端點**（CLAUDE.md：不要自己編路徑）：
    #   原樣把回應印出來並標明它**不是**資料集總表，總表以 K線分析線那份為準。
    out.append("⛔ **這一格我第一版問錯了端點**：`/api/v4/datalist` 不帶參數"
               "列的是某個 dataset 的 `data_id`，⛔ **不是資料集總表**。")
    out.append("⚠ 所以下面那個數字**不是**「FinMind 有幾個資料集」，"
               "⛔ 不可以拿它去反駁 K線分析線那份 94 條的清單。")
    d, note = ask(LIST_API + ("?token=" + TOKEN if TOKEN else ""))
    out.append(f"  回應：{note}")
    if isinstance(d, dict):
        out.append(f"    頂層鍵：{sorted(d)}")
        for k in ("msg", "status"):
            if k in d:
                out.append(f"    {k} 原文：{d[k]!r}")
        lst = d.get("data")
        if isinstance(lst, list):
            names = sorted(str(x) for x in lst) if lst and isinstance(lst[0], str) \
                else sorted(str(x.get("dataset", x)) for x in lst if x)
            out.append(f"    回了 {len(names)} 個項目"
                       "（⛔ 這是 `data_id`，不是資料集名稱）")
            hit = [n for n in names if any(w in n for w in
                   ("Holding", "Trading", "Shareholding", "Securities",
                    "Margin", "Government", "Disposition"))]
            out.append(f"    ⚠ 其中字面像籌碼面的 {len(hit)} 個"
                       "（⛔ 這個數字沒有意義，見上面那句）：")
            for n in hit:
                out.append(f"      {n}")

    txt = "\n".join(out)
    print(txt)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write(txt + "\n")
    print(f"\n[finmind_probe] 寫出 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
