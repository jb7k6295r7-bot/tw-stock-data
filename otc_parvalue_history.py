#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""otc_parvalue_history.py — 上櫃**面額變更**的官方歷史（一次拿十一年半）。

## ⛔⛔ 這一支存在的理由：一句寫在四個地方的否定句是錯的

`otcparvalue.py` 的檔頭（與 `adjust.py`、`db_status.py`）寫著：

> 「TPEx 沒有對應端點（swagger 225 個端點裡沒有減資／面額／參考價）。
>   於是全庫 24 筆面額變更裡，**上櫃那 14 筆一直沒有還原因子**」

⭐ 2026-09-15（probe 117／118）實測推翻：

```
POST https://www.tpex.org.tw/www/zh-tw/bulletin/pvChgRslt
     startDate=2015/01/01&endDate=2026/09/15&response=json
⇒ "date":"20150101~20260915"   ← ⭐ 回顯我請求的那一段 ⇒ 期間參數真的生效
⇒ totalCount: **14**            ⭐ 跟那句話說的「14 筆」逐位吻合
```

⚠ 為什麼漏掉這麼久：那句否定句的**掃描範圍只有 swagger**，
⛔ 而它住在**公告區**——跟我方天天在用的 `exDailyQ`（上櫃除權息）、
`revivt`（上櫃減資）**同一族、同一個形狀**（三點①【掃描範圍】）。

## ⭐ 而它的用途不是「換掉」`otcparvalue.py`，是**當外部錨點**

兩條路**真正互相獨立**：

```
官方     價格：最後交易日之收盤價格 → 恢復買賣開始參考價（＋`詳細資料` 裡的**換股率**）
我方     股數：股數前 ÷ 股數後（`otcparvalue.py`，精確整數比）
```

⛔ 而 `adjust.py` 早就寫著「日後官方端點出現時**官方優先**，衝突要報 ✗
**不可靜默取一邊**」⇒ 這一支就是那句話的兌現。

### ⛔⛔ 而「官方優先」**不等於**「照抄官方每一個數字」

2026-09-15 離線對帳（官方 14 筆 vs 我方 14 筆）：

```
⭐⭐ 換股率              **14/14 逐位相同**
⭐  最後交易日收盤        **14/14 逐位相同**
⭐  恢復買賣參考價        **14/14 相同**（在**分**的尺度上）
⭐  事件集合             官方 14 vs 我方 14，⛔ 兩邊都沒有多餘或缺漏
```

⇒ ⭐⭐ `otcparvalue.py` 那條「股數倍率推導」**被官方完全證實**。

### ⛔⛔ 而我在這一格上**連錯兩次**，兩次都是**比較的方式**錯

```
① `abs(差) < 0.005`  ⇒ 把兩個實質相同的案例分到兩邊
   27.38−27.375 = 0.004999999999999893（過）
   36.38−36.375 = 0.005000000000002558（沒過）  ⛔ 門檻剛好切在它們中間
② 「2 筆差恰好半分」 ⇒ ⛔ 那是**浮點差**，不是真的差異
   27.375 與 27.38 在**分**的尺度上是**同一個數**（round(2737.5) == 2738）
```

⇒ ⭐ **價格要在它自己的最小單位（分）上比**，⛔ 不是拿浮點差比一個門檻。
⚠ 而 CLAUDE.md 三點6 記的是同一族的另一半（絕對誤差 vs 相對誤差）
——這一條是第三種：**比較的尺度選錯**。

### ⇒ 而「官方優先」**不等於**「照抄官方每一個數字」

官方裁定的是**事件與因子**。⚠ 而我方參考價多留一位（27.375 vs 27.38）
⇒ ⛔ 照抄官方會**失去精度**，⭐ 而兩者在分的尺度上本來就相同。
⇒ 閘門比的是**換股率**，⛔ 不是參考價的逐位相同。
"""
import argparse
import io
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import lowwater                                                # noqa: E402
import runlog                                                  # noqa: E402
from backfill import why as _W                                 # noqa: E402
from twparse import post_form as _post_form, roc_iso as _roc_iso  # noqa: E402

URL = "https://www.tpex.org.tw/www/zh-tw/bulletin/pvChgRslt"
_ROOT = os.path.join(_HERE, "data")


def out_path():
    """⭐ 呼叫當下才算（沙箱只要導 `_ROOT`，⛔ 不必記得導第二個旋鈕）。"""
    return os.path.join(_ROOT, "meta", "otc_parvalue_history.csv")


def low_path():
    return os.path.join(_ROOT, "meta", "_otc_parvalue_low.txt")


def mine_dir():
    return os.path.join(_ROOT, "universe", "otcparvalue")


HEADER = ["date", "stock_id", "name", "last_close", "ref_price",
          "limit_up", "limit_down", "open_base", "ratio",
          "par_before", "par_after", "halt_date"]

# ⚠ `詳細資料` 是一整段 HTML（`<th>標籤:</th><td>值</td>`），
#   ⛔ 而它的 `/` 是 `/` 逃脫過的 ⇒ 解析要在 **json.loads 之後**做。
_DETAIL = (r"<th>{}:<\s*/?\s*th>\s*<td>\s*(.*?)\s*<")


def _detail(html, label):
    """→ `詳細資料` 裡那個標籤的值，⛔ 找不到回 `""`（不猜）。"""
    m = re.search(_DETAIL.format(re.escape(label)), html or "")
    return m.group(1).strip() if m else ""


def _num(v):
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def parse(payload, want_range):
    """→ (rows, note)。⛔ 回應要**自己講出它是哪一段期間**（第二點）。

    ⚠ `want_range` 是我請求的那一段（`20150101~20260915` 這種形狀）。
    ⛔ 回顯的不是我請求的那一段 ⇒ **一列都不回**——那就是「參數被忽略」，
      而 `exDailyQ` 的檔頭記著 GET 會靜靜回「今天～明天」。
    """
    got = str((payload or {}).get("date") or "")
    if not got:
        return [], "⛔ 回應裡**沒有** `date` 鍵 ⇒ 判不出參數有沒有生效（⚠ 不是「有生效」）"
    if got.replace(" ", "") != want_range:
        return [], (f"⛔ 回顯的期間是 `{got}`，⚠ 而我請求的是 `{want_range}`"
                    "　⇒ **參數被忽略**（第二點①）")
    tabs = (payload or {}).get("tables") or []
    rows = []
    for t in tabs:
        for r in t.get("data") or []:
            if len(r) < 9:
                continue
            day = _roc_iso(r[0])
            if not day:
                continue
            html = r[8]
            rows.append([day, str(r[1]).strip(), str(r[2]).strip(),
                         _num(r[3]), _num(r[4]), _num(r[5]), _num(r[6]),
                         _num(r[7]), _num(_detail(html, "變更股票面額換股率")),
                         _num(_detail(html, "變更前股票面額")),
                         _num(_detail(html, "變更後股票面額")),
                         _roc_iso(_detail(html, "停止買賣日期")) or ""])
    rows.sort(key=lambda x: (x[0], x[1]))
    return rows, f"{len(rows)} 列｜回顯期間 {got}（⭐ 跟我請求的相同）"


def ratio_ok(row, cents=0.6):
    """官方那一列**自己內部**一致嗎：最後收盤 ÷ 參考價 ≟ 換股率。

    ⚠ 判準用**分**當單位（⛔ 不是拿浮點差比一個剛好等於它的門檻——
      2026-09-15 我第一版就是這樣把兩個實質相同的案例分到兩邊）。
    ⇒ 允許 `cents` 分的捨入（官方參考價四捨五入到分）。
    """
    last, ref, ratio = row[3], row[4], row[8]
    if not (last and ref and ratio):
        return None                      # ⛔ 缺值就是判不出，不是「過」
    want = last / ratio
    return abs(round(want * 100) - round(ref * 100)) <= cents


def load_mine(d=None):
    """→ {(日期, 代號): 我方那一列}（`otcparvalue.py` 推導出來的）。"""
    import csv
    d = d or mine_dir()
    out = {}
    if not os.path.isdir(d):
        return out
    for n in sorted(os.listdir(d)):
        if not n.endswith(".csv"):
            continue
        with io.open(os.path.join(d, n), encoding="utf-8") as f:
            for r in csv.DictReader(f):
                out[(r.get("date", ""), r.get("stock_id", ""))] = r
    return out


def reconcile(rows, mine):
    """官方 vs 我方的**雙向**比對 → dict。⛔ 只比一個方向不算一致（三點1）。

    ⭐ 閘門比的是**換股率**，⛔ 不是參考價逐位相同：
      官方四捨五入到分、我方留三位 ⇒ 參考價本來就會差半分，
      ⚠ 而那**不是**衝突（理由寫在本檔檔頭）。
    """
    off_keys = {(r[0], r[1]) for r in rows}
    res = {"same": [], "ratio_diff": [], "only_official": [], "only_mine": [],
           "ref_cents": []}
    for r in rows:
        m = mine.get((r[0], r[1]))
        if not m:
            res["only_official"].append((r[0], r[1], r[8]))
            continue
        pc, rp = _num(m.get("pre_close")), _num(m.get("ref_price"))
        mr = (pc / rp) if (pc and rp) else None
        if mr is None or r[8] is None or abs(mr - r[8]) > 1e-6:
            res["ratio_diff"].append((r[0], r[1], r[8], mr))
        else:
            res["same"].append((r[0], r[1]))
        if rp is not None and r[4] is not None and round(rp * 100) != round(r[4] * 100):
            res["ref_cents"].append((r[0], r[1], rp, r[4],
                                     round((rp - r[4]) * 100, 2)))
    for k in mine:
        if k not in off_keys:
            res["only_mine"].append(k)
    return res


def main():
    ap = argparse.ArgumentParser(description="上櫃面額變更的官方歷史")
    ap.add_argument("--start", default="2015/01/01")
    ap.add_argument("--end", default="")
    ap.add_argument("--json", help="離線用：讀一個檔當回應")
    ap.add_argument("--apply", action="store_true",
                    help="⭐ 真的寫判準檔；⛔ 不帶就只驗不寫")
    a = ap.parse_args()

    rl = runlog.Run("otc_parvalue_history")
    end = a.end or runlog.now_tpe().strftime("%Y/%m/%d")
    want = (a.start + "~" + end).replace("/", "")
    rl.info("端點", f"POST {URL}｜{a.start} ~ {end}"
                    "　⛔ POST ＋日期帶斜線（GET 會**靜默**回今天～明天，"
                    "那句話寫在 `otc_exright_history.py` 檔頭）")

    if a.json:
        raw, err = io.open(a.json, "rb").read(), None
    else:
        raw, err = _post_form(URL, {"startDate": a.start, "endDate": end,
                                    "response": "json"})
    if err or not raw:
        rl.check("抓得到 pvChgRslt", False,
                 f"{_W(err, 160)}｜⛔ 抓不到**不等於**沒有歷史"
                 "（本機對 tpex 一律 403，是我方閘道擋的）")
        return rl.finish()
    try:
        payload = json.loads(raw.decode("utf-8", "replace"))
    except ValueError as ex:                                    # noqa: BLE001
        head = raw[:120].decode("utf-8", "replace").replace("\n", " ")
        rl.check("回應是 JSON", False, f"{str(ex)[:60]}｜開頭={head!r}")
        return rl.finish()

    rows, note = parse(payload, want)
    rl.info("官方回的", note)
    rl.check("⭐ 回應**自己講出**它涵蓋哪一段（⛔ 不是我說了算）", bool(rows), note)
    if not rows:
        return rl.finish()

    bad_self = [r[:2] for r in rows if ratio_ok(r) is False]
    rl.check("⭐ 官方那一列**自己內部**一致（最後收盤 ÷ 參考價 ≟ 換股率）",
             not bad_self, f"⛔ {len(bad_self)} 筆對不上：{bad_self[:3]}"
             if bad_self else f"{len(rows)} 筆全過")

    mine = load_mine()
    res = reconcile(rows, mine)
    rl.info("⭐ 逐筆對帳（⛔ 雙向）",
            f"換股率相同 **{len(res['same'])}**｜⛔ 換股率不同 {len(res['ratio_diff'])}"
            f"｜⛔ 只有官方有 {len(res['only_official'])}"
            f"｜⚠ 只有我方有 {len(res['only_mine'])}")
    if res["ref_cents"]:
        rl.info("⚠ 參考價差（⛔ 不是衝突）",
                f"{len(res['ref_cents'])} 筆差 ≤ 半分"
                "　⇒ ⭐ 官方四捨五入到**分**、我方留**三位**"
                "　⛔ 照抄官方會**失去精度** ⇒ 這一格不當衝突"
                + f"：{res['ref_cents'][:3]}")
    # ⛔⛔ 這就是 `adjust.py` 那句「官方優先、衝突要報 ✗ 不可靜默取一邊」的兌現
    rl.check("⭐⭐ 官方與我方的**換股率**沒有衝突（⛔ 有衝突就報 ✗，不自己選一邊）",
             not res["ratio_diff"], f"⛔ {res['ratio_diff'][:3]}")
    rl.check("⭐ 事件集合**雙向**都對得上（⛔ 只比一個方向不算一致，三點1）",
             not res["only_official"] and not res["only_mine"],
             f"只有官方 {res['only_official'][:3]}｜只有我方 {res['only_mine'][:3]}")

    # ⭐ 低水位：官方筆數**只會長大** ⇒ UP（⛔ 不是 DOWN，那是「修得完」的量才用）
    lowwater.write(low_path(), len(rows), lowwater.UP)
    prev, prevday = lowwater.read(low_path(), lowwater.UP)
    rl.info("筆數水位", f"本趟 {len(rows)}｜歷史最高 "
            + (f"{prev}（{prevday}）" if prev is not None else "（第一趟）"))

    if not a.apply:
        rl.info("⚠ 這一趟沒有 `--apply`", "只驗不寫")
        return rl.finish()
    p = out_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    import csv as _csv
    with io.open(p, "w", encoding="utf-8", newline="") as f:
        w = _csv.writer(f, lineterminator="\n")
        w.writerow(HEADER)
        w.writerows(rows)
    # ⭐ 寫完**重讀**（四點二：⛔ 不要斷言「寫檔成功」）
    with io.open(p, encoding="utf-8") as f:
        back = list(_csv.DictReader(f))
    rl.check("⭐ 寫完重讀，列數與換股率對得回來（⛔ 不是斷言寫檔成功）",
             len(back) == len(rows)
             and all(_num(b["ratio"]) == r[8] for b, r in zip(back, rows)),
             f"寫 {len(rows)}｜讀回 {len(back)}")
    rl.info("寫出", p)
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
