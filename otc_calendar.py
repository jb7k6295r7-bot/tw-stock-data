#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""otc_calendar.py — **上櫃交易日曆的外部判準**，每天抓、逐日累積。

## 為什麼要有這一支

`_data_audit.md` 裡，上櫃交易日曆一直是**唯一一列 C 級**：只有自我一致。
「自我一致」＝ 日曆就是 `data/universe/daily/` 裡有上櫃成交的日期集合，
**拿自己的產出當自己的判準**。當初若某天整批漏抓，那天就不在日曆裡，
於是每個 feed 一致地缺同一天，覆蓋率算出來還是 100%。
上市那邊有 `calendar_audit.py`（TWSE `FMTQIK` 大盤月報），⛔ 但 FMTQIK 只有上市。

`otccal_probe.py` 2026-09-09 在 Actions 上量到了缺的那一半：

    /openapi/v1/tpex_daily_trading_index｜上櫃日成交量值指數
    欄位 Date / TradeVolume / TradeAmount / NumberOfTransactions / TPExIndex / Change
    ⇒ 這是**櫃買自己的大盤層級統計**，跟我方上櫃日檔走的
      `www/zh-tw/afterTrading/otc`（逐檔行情）是不同端點、不同彙總層級。

## ⛔ 它只給**最近 7 個交易日**

swagger 的標題寫「歷史」，⛔ **那是誤導**：實測 8 個「歷史指數」端點
（tpex_index／tpex_reward_index／tpex50_index／tpcgi／tpci／tphd／emp88）
**每一個都只回 7 列**，一律是最近 7 個交易日。

⇒ 所以這一支跟集保、跟開休市行事曆是**同一族**：**不累積就永久失去**。
  今天不存，2026-09-01 那一天的外部判準明年就拿不到了。
  ⇒ 每天跑、往 `data/meta/calendar_tpex.csv` 累積，並排進 `freshness_check.py`。

## 這一支能證明什麼、不能證明什麼

✓ 能：**我方有沒有漏掉一整天的上櫃日檔**。對方有、我方無 ⇒ 幾乎確定是漏抓。
⛔ 不能：證明櫃買自己沒錯。同一個發行機構的兩條管線，
  錯在源頭的話兩邊會一起錯——這一點跟上市那邊的 FMTQIK 完全一樣，
  ⛔ **不要**因為有了這一支就說上櫃日曆「已驗證正確」。

## ⛔ 涵蓋範圍要講清楚，不可以整列寫成「已升 B」

- 2026-09-01 起（本支開始累積之後）：**B**（有外部判準）
- 2015-01-05 ~ 2026-08-31：**仍然是 C**——那段沒有人留下 7 天窗外的紀錄，
  ⛔ 而且**補不回來**。
"""
import argparse
import csv
import io
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

import backfill as B
import runlog

TPE = timezone(timedelta(hours=8))
_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DAILY_DIR = os.path.join(_ROOT, "universe", "daily")
OUT = os.path.join(_ROOT, "meta", "calendar_tpex.csv")

# ⛔ 端點逐字取自 `data/meta/_tpex_probe.txt`（swagger.json 實抓的目錄），
#   並由 `otccal_probe.py` 在 Actions 上實測過形狀。**不是拼的。**
URL = "https://www.tpex.org.tw/openapi/v1/tpex_daily_trading_index"

HEADER = ["date", "volume", "amount", "transactions", "index", "change", "asof"]


def _iso(v):
    """民國 1150901 / 西元 20260901 / 2026-09-01 → ISO。認不出回 None。

    ⛔ 民國 7 碼與西元 8 碼長得像同一種東西，錯一個世紀不會有人發現
      ⇒ 用長度分辨，⛔ 不用「看起來像日期就抓」。
    """
    s = str(v).strip()
    if re.fullmatch(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}", s):
        return s
    if re.fullmatch(r"1[0-9]{6}", s):        # 民國：1150901
        return f"{int(s[:3]) + 1911}-{s[3:5]}-{s[5:7]}"
    if re.fullmatch(r"20[0-9]{6}", s):       # 西元：20260901
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    return None


def _num(v):
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def our_days():
    """我方上櫃日曆：`data/universe/daily/` 裡**有上櫃列**的日期。

    ⛔ 這是被驗的對象，不是判準。
    """
    out = []
    if not os.path.isdir(DAILY_DIR):
        return out
    for fn in sorted(os.listdir(DAILY_DIR)):
        if fn.endswith(".csv"):
            try:
                with io.open(os.path.join(DAILY_DIR, fn), "rb") as f:
                    if b",tpex," in f.read():
                        out.append(fn[:-4])
            except OSError:
                pass
    return out


def _load():
    rows = {}
    if os.path.exists(OUT):
        with io.open(OUT, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("date"):
                    rows[r["date"]] = [r.get(k, "") for k in HEADER]
    return rows


def _save(rows):
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for k in sorted(rows):
            w.writerow(rows[k])


def _otc_totals(day):
    """我方那一天的上櫃合計，依證券種類分桶。回 dict[kind] = (列數, 金額, 股數)。"""
    p = os.path.join(DAILY_DIR, day + ".csv")
    out = {}
    if not os.path.exists(p):
        return out
    with io.open(p, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("market") != "tpex":
                continue
            k = B._kind(r.get("stock_id", ""))
            a = out.setdefault(k, [0, 0.0, 0.0])
            a[0] += 1
            a[1] += _num(r.get("amount")) or 0.0
            a[2] += _num(r.get("volume")) or 0.0
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="離線用：讀一個檔當回應（selftest 用）")
    args = ap.parse_args()

    rl = runlog.Run("otc_calendar")
    today = datetime.now(TPE).strftime("%Y-%m-%d")

    if args.json:
        raw = io.open(args.json, "rb").read()
    else:
        raw, err = B.get(URL, retries=3, timeout=60)
        if err or not raw:
            rl.info("端點", f"✗ 抓不到：{str(err)[:120]}")
            # ⛔ 抓不到**不是**「今天沒有交易日」。這一支唯一的失敗處置是報 ✗ 收手，
            #   ⛔ 絕不可以因此去動任何一天的日檔。
            rl.check("抓得到櫃買日成交量值指數", False,
                     f"{str(err)[:80]}｜⛔ 連續失敗 5 天以上就會被 freshness_check 抓到")
            return rl.finish()

    try:
        d = json.loads(raw.decode("utf-8", "replace"))
    except ValueError as ex:                                     # noqa: BLE001
        # ⛔ 只接 ValueError。我方自己的例外要炸出來，不要改名成別人的錯——
        #   2026-09-09 `holiday.py` 就是這樣把 NameError 印成「不是 JSON」的。
        rl.info("端點", f"✗ 對方回的不是 JSON：{ex}")
        rl.check("回應是 JSON", False, str(ex)[:80])
        return rl.finish()

    if not isinstance(d, list) or not d or not isinstance(d[0], dict):
        rl.info("端點", f"✗ 形狀不對：{type(d).__name__}")
        rl.check("回應是 list[dict]", False, str(d)[:120])
        return rl.finish()

    theirs, bad = {}, 0
    for r in d:
        iso = _iso(r.get("Date", ""))
        if not iso:
            bad += 1
            continue
        theirs[iso] = [iso, str(r.get("TradeVolume", "")).strip(),
                       str(r.get("TradeAmount", "")).strip(),
                       str(r.get("NumberOfTransactions", "")).strip(),
                       str(r.get("TPExIndex", "")).strip(),
                       str(r.get("Change", "")).strip(), today]
    td = sorted(theirs)
    rl.info("本趟端點回的", f"{len(d)} 列｜認得出日期 {len(td)} 天"
            + (f"｜⚠ 認不出 {bad} 列" if bad else "")
            + (f"｜{td[0]} ~ {td[-1]}" if td else ""))
    rl.check("端點的每一列都認得出日期", bad == 0, f"認不出 {bad} 列")
    if not td:
        return rl.finish()

    # ── 累積（⛔ 這一支的本體：端點只給 7 天，不存就永久失去） ──────────
    before = _load()
    n_before = len(before)
    rows = dict(before)
    rows.update(theirs)          # 同一天重抓覆蓋（asof 記得住是哪天抓的）
    _save(rows)
    ds = sorted(rows)
    rl.info("累積檔", f"{OUT.split('data/')[-1]}｜{len(rows)} 天"
            f"（本趟新增 {len(rows) - n_before}）｜{ds[0]} ~ {ds[-1]}")
    # ⛔ 只增不減。這一支若把累積檔寫短了，失去的那幾天**補不回來**。
    rl.check("累積檔只增不減", len(rows) >= n_before,
             f"{n_before} → {len(rows)}")

    # ── 雙向比對（⛔ 只在**重疊區間**內比） ──────────────────────────
    ours = our_days()
    if not ours:
        rl.info("比對", "✗ 讀不到 `data/universe/daily/` ⇒ 這一趟沒有比對")
        rl.check("讀得到我方日檔", False, DAILY_DIR)
        return rl.finish()
    lo, hi = max(td[0], ours[0]), min(td[-1], ours[-1])
    T = {x for x in td if lo <= x <= hi}
    O = {x for x in ours if lo <= x <= hi}
    only_t, only_o = sorted(T - O), sorted(O - T)
    rl.info("重疊區間", f"{lo} ~ {hi}｜櫃買 {len(T)} 天／我方 {len(O)} 天")
    # ⭐ 這一項就是「上櫃日曆的外部判準」本體。
    rl.check("櫃買有、我方沒有的交易日為 0（疑似整天漏抓）",
             not only_t, f"{len(only_t)} 天：{only_t[:10]}")
    # ⚠ 反方向也要看：我方有、櫃買沒有。在重疊區間內這一樣可疑。
    #   ⛔ 但**不可以自動刪**——那是把「我方多一天」跟「對方漏一天」當成同一件事。
    rl.check("我方有、櫃買沒有的交易日為 0（在重疊區間內）",
             not only_o, f"{len(only_o)} 天：{only_o[:10]}｜⛔ 要逐日看，不可以自動刪")

    # ── 大盤合計對帳：⛔ 這一輪**只量、不當判準** ─────────────────────
    #   2026-09-09 實測 2026-09-01：
    #     我方 stock+etf  Σamount −2.52%｜Σvolume +24.7%
    #     我方 只算 stock Σamount −4.48%｜Σvolume −2.18%
    #   ⇒ **沒有任何一種組合對得起來**（一邊金額少、一邊股數多）。
    #     還沒查出來的候選解釋：鉅額交易、盤後定價、ETF 計不計入。
    #   ⛔ 沒查清楚就設門檻＝憑感覺挑一個能過的數字。**先量，量到解釋為止。**
    last = td[-1]
    tot = _otc_totals(last)
    if tot:
        wa, wv = _num(theirs[last][2]), _num(theirs[last][1])
        se = tot.get("stock", [0, 0.0, 0.0])
        al = [sum(v[i] for v in tot.values()) for i in (1, 2)]
        def _pc(x, w):
            return f"{(x - w) / w * 100:+.2f}%" if w else "（對方 0）"
        rl.info(f"大盤合計對帳 {last}（⛔ 只量，還不是判準）",
                f"櫃買 金額 {wa:,.0f}／股數 {wv:,.0f}｜"
                f"我方全部 {_pc(al[0], wa)}／{_pc(al[1], wv)}｜"
                f"只算 stock {_pc(se[1], wa)}／{_pc(se[2], wv)}｜"
                f"分桶 {({k: v[0] for k, v in sorted(tot.items())})}")
        rl.note("⛔ 這一項**刻意沒有寫成 check**：金額與股數的誤差方向相反，"
                "代表還沒找到正確的比較口徑（鉅額／盤後定價／ETF）。"
                "在解釋出來之前設門檻，就是挑一個剛好能過的數字。")

    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
