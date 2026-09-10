#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""otc_reduce_history.py — 上櫃**減資**的官方歷史（櫃買公告區「減資恢復買賣」）。

## 為什麼今天才有

`sources/reduce_source.md` 記的是「形狀對，**但只回未來十天**」。
⛔ 那是**參數送錯**。市場情報分析線 2026-09-10 10:00 實測：

    POST https://www.tpex.org.tw/www/zh-tw/bulletin/revivt
    body: startDate=2015/01/01&endDate=2026/09/09&response=json
    → **234 筆，一次回完**（選擇器下限 data-start="20130101"，資料也真的從 2013 開始）

⭐ 而這一支是**必要的**，不是錦上添花：
`exDailyQ`（除權息）**不含減資**——59 檔的抽驗裡就少了 17 筆。
拿除權息表當上櫃 adj 的完整來源會**刪掉減資因子**，那幾檔的還原價整段錯。

    上櫃 adj ＝ exDailyQ（上櫃期間除權息）＋ **revivt（減資）** ＋ TWT49U（轉上市後）

## ⛔ 參數行為：同一個 `bulletin/` 家族，三支**並不相同**

情報分析線 10:06 自我更正過一次（他把 `exDailyQ` 的行為套到另兩支）：

    | | exDailyQ | revivt | pvChgRslt |
    | GET ＋斜線   | ⛔ 靜靜回今天 | ✅ 正常 | 未測 |
    | POST ＋無斜線 | ⛔ 靜靜回今天 | stat:參數錯誤（**大聲失敗**） | stat:參數錯誤 |
    | POST ＋斜線   | ✅ | ✅ | ✅ |

⇒ **最安全的寫法是 POST ＋ 斜線**（三支都過）。
⚠ 但錯誤處理不同：`exDailyQ` 必須自己檢查回應日期區間；
  這一支靠 `stat` 就擋得住——⛔ 儘管如此，本支**兩道都做**，
  因為「對方哪天改行為」不在我的控制範圍內。

## 這一支做什麼

1. 抓全期，寫 `data/meta/otc_reduce_history.csv`（判準檔）
2. ⭐ **逐筆掃「官方有、我方 `data/adj/` 沒有」**——這正是情報分析線
   10:00 說「那一掃你來做比較省」的那一掃（我手上就有全部 `data/adj/`）。
   他只驗過「我方已有的那些對得上」（12/12 逐位相符），**沒驗「我方缺哪些」**。
3. ⛔ 不寫 `data/adj/` 也不寫 `data/universe/otcreduce/`（單一寫入者）。
"""
import argparse
import csv
import io
import json
import os
import sys
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone

import runlog

TPE = timezone(timedelta(hours=8))
_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(_ROOT, "meta", "otc_reduce_history.csv")
ADJ = os.path.join(_ROOT, "adj")

URL = "https://www.tpex.org.tw/www/zh-tw/bulletin/revivt"
HEADER = ["date", "stock_id", "name", "last_close", "ref_price", "factor",
          "reason", "asof"]


def _post(url, form, timeout=120):
    body = urllib.parse.urlencode(form, encoding="utf-8").encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={"User-Agent": "Mozilla/5.0", "Referer": url,
                 "Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(), None
    except Exception as ex:                                      # noqa: BLE001
        return b"", f"{type(ex).__name__}: {str(ex)[:120]}"


def _iso(v):
    s = str(v).strip().replace("-", "/")
    p = s.split("/")
    if len(p) != 3 or not all(x.strip().isdigit() for x in p):
        return None
    y, m, d = (int(x) for x in p)
    if y < 1000:
        y += 1911
    if not (1990 < y < 2100 and 1 <= m <= 12 and 1 <= d <= 31):
        return None
    return f"{y:04d}-{m:02d}-{d:02d}"


def _num(v):
    s = str(v).replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def _pick(fields, *words):
    for i, f in enumerate(fields):
        if any(w in str(f) for w in words):
            return i
    return None


def parse(payload, want_from):
    """→ (rows, note)。⛔ 兩道守門都做：`stat` 與**回應涵蓋的日期範圍**。"""
    if isinstance(payload, dict):
        stat = str(payload.get("stat", "")).strip()
        # ⛔ 這一支參數錯會**大聲失敗**（stat:參數錯誤）——跟 exDailyQ 不同。
        #   但仍然不能只靠它，見檔頭：對方哪天改行為不在我的控制範圍內。
        if stat and stat.lower() not in ("ok", "success"):
            return [], f"⛔ 端點自己說失敗：stat={stat!r}"
    tabs = (payload.get("tables") if isinstance(payload, dict) else None) or []
    if not tabs and isinstance(payload, dict) and payload.get("data"):
        tabs = [payload]
    if not tabs:
        return [], f"回應裡沒有表（鍵={list(payload)[:8] if isinstance(payload, dict) else type(payload).__name__}）"
    t = tabs[0]
    fields = [str(x) for x in (t.get("fields") or [])]
    data = t.get("data") or []
    if not data:
        return [], "回了 0 列 ⛔ 當失敗，不是「這十一年沒有減資」"
    i_d = _pick(fields, "恢復買賣日期", "日期")
    i_c = _pick(fields, "股票代號", "證券代號", "代號")
    i_n = _pick(fields, "名稱")
    i_lc = _pick(fields, "最後交易日之收盤價", "最後交易日")
    i_rp = _pick(fields, "恢復買賣開始日參考價", "參考價格", "參考價")
    i_rs = _pick(fields, "減資原因", "原因")
    miss = [n for n, i in (("日期", i_d), ("代號", i_c),
                           ("最後收盤", i_lc), ("參考價", i_rp)) if i is None]
    if miss:
        return [], f"欄位對不上，缺 {miss}：{fields}"
    rows, bad = [], 0
    for r in data:
        if not isinstance(r, list) or len(r) <= max(i_d, i_c, i_lc, i_rp):
            bad += 1
            continue
        dt, code = _iso(r[i_d]), str(r[i_c]).strip()
        lc, rp = _num(r[i_lc]), _num(r[i_rp])
        if not dt or not code:
            bad += 1
            continue
        # ⭐ factor ＝ 參考價 ÷ 最後交易日收盤價（與 `data/adj` 同定義）
        f = f"{rp / lc:.8f}" if (lc and rp) else ""
        rows.append([dt, code, str(r[i_n]).strip() if i_n is not None else "",
                     str(r[i_lc]).replace(",", "").strip(),
                     str(r[i_rp]).replace(",", "").strip(), f,
                     str(r[i_rs]).strip() if i_rs is not None else ""])
    if not rows:
        return [], f"一列都認不出來（bad={bad}）：{fields}"
    ds = sorted(r[0] for r in rows)
    recent = (datetime.now(TPE) - timedelta(days=30)).strftime("%Y-%m-%d")
    if ds[0] > want_from and ds[0] >= recent:
        return [], (f"⛔ 回的只有最近的資料（{ds[0]} ~ {ds[-1]}，{len(rows)} 筆），"
                    f"我要的是 {want_from} 起　⚠ 參數多半沒生效")
    return rows, (f"{len(data)} 列｜認得出 {len(rows)}"
                  + (f"｜⚠ 認不出 {bad}" if bad else "")
                  + f"｜涵蓋 {ds[0]} ~ {ds[-1]}｜欄位 {fields}")


def adj_rows():
    """→ {(代號, 日期): factor 字串}，我方 `data/adj/` 的全部事件。"""
    out = {}
    if not os.path.isdir(ADJ):
        return out
    for n in os.listdir(ADJ):
        if not n.endswith(".csv") or n == "_index.csv":
            continue
        try:
            with io.open(os.path.join(ADJ, n), encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    if r.get("date"):
                        out[(n[:-4], r["date"])] = r.get("factor", "")
        except OSError:
            pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2013/01/01")
    ap.add_argument("--end", default="")
    ap.add_argument("--json", help="離線用：讀一個檔當回應")
    a = ap.parse_args()

    rl = runlog.Run("otc_reduce_history")
    today = datetime.now(TPE).strftime("%Y-%m-%d")
    end = a.end or today.replace("-", "/")
    rl.info("端點", f"POST {URL}｜{a.start} ~ {end}"
                    "　⛔ POST ＋日期帶斜線（無斜線這一支會 stat:參數錯誤，"
                    "⚠ 但 exDailyQ 是靜默的——同族三支行為不同）")

    if a.json:
        raw, err = io.open(a.json, "rb").read(), None
    else:
        raw, err = _post(URL, {"startDate": a.start, "endDate": end,
                               "response": "json"})
    if err or not raw:
        rl.check("抓得到 revivt", False, f"{str(err)[:100]}"
                 "｜⛔ 抓不到不等於沒有歷史（本機對 tpex 一律 403）")
        return rl.finish()
    try:
        payload = json.loads(raw.decode("utf-8", "replace"))
    except ValueError as ex:                                     # noqa: BLE001
        head = raw[:80].decode("utf-8", "replace").replace("\n", " ")
        rl.check("回應是 JSON", False, f"{str(ex)[:50]}｜開頭={head!r}")
        return rl.finish()

    rows, note = parse(payload, a.start.replace("/", "-"))
    rl.info("官方回的", note)
    rl.check("回應涵蓋我請求的整段期間", bool(rows), note)
    if not rows:
        return rl.finish()

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for r in sorted(rows):
            w.writerow(r + [today])
    rl.info("判準檔", f"data/meta/otc_reduce_history.csv｜{len(rows):,} 筆")
    rl.info("  原因分布", dict(Counter(r[6] for r in rows).most_common(6)))

    # ── ⭐ 情報分析線 10:00 指名要我做的那一掃 ──────────────────────
    #   他驗過的是「我方已有的那些對得上」（12/12 逐位相符），
    #   ⛔ **沒驗「我方缺哪些」**——而那要全部 `data/adj/` 才掃得動。
    have = adj_rows()
    miss = [r for r in rows if (r[1], r[0]) not in have]
    bad_f = []
    for r in rows:
        k = (r[1], r[0])
        if k in have and r[5] and have[k]:
            try:
                if abs(float(r[5]) - float(have[k])) > 1e-6:
                    bad_f.append((r[1], r[0], r[5], have[k]))
            except ValueError:
                pass
    rl.info("⭐ 官方有、我方 data/adj 沒有",
            f"**{len(miss)} 筆／{len({r[1] for r in miss})} 檔**"
            + (f"｜前 10：{[(r[1], r[0], r[6]) for r in miss[:10]]}" if miss else ""))
    rl.info("  分年", dict(Counter(r[0][:4] for r in miss).most_common()))
    rl.check("兩邊都有的那些 factor 逐位相符",
             not bad_f, f"{len(bad_f)} 筆不符：{bad_f[:6]}"
             if bad_f else f"{len(rows) - len(miss)} 筆全中")
    # ⛔ 「官方有我方沒有」不設 check：那是**歷史欠帳**，天天紅會被學會忽略。
    rl.info("⛔ 這一支不寫 data/adj/",
            "單一寫入者是 `adjust.py`／`otc_adj.py`。這裡只提供證據。")
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
