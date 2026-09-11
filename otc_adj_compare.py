#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""otc_adj_compare.py — 上櫃還原因子：**官方 vs 我方，雙向逐筆比對**。

    python3 otc_adj_compare.py        # 只讀本地檔、⛔ 一列都不寫進 data/adj

## ⛔ 這一支存在的理由：換供料的**第 1 步**，不是換供料本身

市場情報分析線 2026-09-10 20:00 裁定：

    第 1 步（現在做）：雙向逐筆比對，輸出差異清單，⛔ 不寫入 data/adj
    第 2 步（看完差異再做）：確認無誤後才換源

⚠ 而他們自己在同一天早上摔過一次：**只做單向比對**，宣告
「exDailyQ 可當上櫃 adj 的完整來源」；反方向一比少了 17 筆減資 ＋ 5 筆轉上市
⇒ **照那個結論做會刪掉既有的還原因子**。

## ⭐ 差異要分四類，⛔ 不可以合計成一個數字

    A 兩邊都有、factor 逐位相同        → 無事
    B 兩邊都有、factor **不同**        → ⛔ 換源的真正風險，要逐筆看
    C 官方有、我方沒有                 → 補（⚠ 先排除恢復買賣日在未來的預告列）
    D 我方有、官方沒有                 → ⛔⛔ 最危險：換源會**刪掉**它

⚠ **D 類一筆都不能自動處理。** `exDailyQ` **不含減資、不含轉上市之後**，
而那兩種在 FinMind 那邊是有的 ⇒ 換源等於把它們刪掉。
⇒ 最終形態不是「換掉 FinMind」，是**官方三支聯集 ＋ FinMind 退為備援**。

## ⛔ 比的是**同一個定義**

三邊一律用 `factor = 參考價 ÷ 前收盤價`。
⚠ 減資那邊另有一個 `factor_official`（官方換股比例，無捨入殘差），
K線線 20:20 裁定「還原用 `factor_official`、斷點門檻用 `factor`」
——⛔ 但那是**換算精度**的問題，跟「這個事件在不在」是兩件事。
把兩件事混在一起比，會讓 B 類塞滿一堆其實只是捨入殘差的列。
⇒ 這裡比 `factor`；精度那件由 `otc_reduce_history` 的上界斷言管。
"""
import argparse
import csv
import io
import os
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

import runlog
from otc_reduce_history import KNOWN_OFFICIAL_DUP as _KNOWN_DUP

TPE = timezone(timedelta(hours=8))
_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
ADJ = os.path.join(_ROOT, "adj")
DAILY = os.path.join(_ROOT, "universe", "daily")
EXH = os.path.join(_ROOT, "meta", "otc_exright_history.csv")
RDH = os.path.join(_ROOT, "meta", "otc_reduce_history.csv")
TWEX = os.path.join(_ROOT, "universe", "exright")
OUT = os.path.join(_ROOT, "meta", "_otc_adj_compare.csv")
TOL = 1e-6


def _f(v):
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _rows(path):
    if not os.path.exists(path):
        return []
    with io.open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def official(codes):
    """→ {(code, date): (factor, 來源, 前收, 參考價)}。官方三支的**聯集**。

    ⛔ 三支各補一塊，缺任何一塊都會讓 D 類假性變大：
      `exDailyQ` 不含減資、也不含該檔轉上市之後的除權息。

    ⛔⛔ `codes` 是必要參數，⚠ 第一版忘了它：`TWT49U` 是**全上市**的表，
      不濾就會把從來不是上櫃的一千多檔一起算進來
      ⇒ C 類（官方有我方沒有）從 2,998 膨脹到 **14,497**，
      ⚠ 而那看起來像是「我方漏抓了一萬多筆」——**方向剛好相反、而且很嚇人**。
      ⭐ 這一支是要拿來做換源決定的，⛔ 一個灌水的 C 類會直接誤導那個決定。
    """
    out, src = {}, Counter()
    for r in _rows(EXH):                       # ① 上櫃除權息
        pre, ref = _f(r.get("pre_close")), _f(r.get("ref_price"))
        if pre and ref and r["stock_id"] in codes:
            out[(r["stock_id"], r["date"])] = (ref / pre, "exDailyQ", pre, ref)
            src["exDailyQ"] += 1
    for r in _rows(RDH):                       # ② 上櫃減資
        pre, ref = _f(r.get("last_close")), _f(r.get("ref_price"))
        # ⛔⛔ 官方自己重複的列要**先扣掉**，否則它會永遠停在 C 類（官方有、
        #   我方沒有）——⚠ 而 C 類是拿來做換源決定的，一筆永遠補不掉的
        #   「缺口」會讓人以為我方漏抓，⛔ 方向剛好相反：漏的是官方打錯字。
        #   ⭐ 清單**只有一份**（`otc_reduce_history.KNOWN_OFFICIAL_DUP`），
        #   ⛔ 不在這裡抄（第四點五）。實例：6109 亞元 1070925 誤打成 1090925
        #   ——同一組數字（10.50→10.63）在表裡出現兩次，而 2020-09-25 那天
        #   我方日檔的價格是連續的（前收 14.45），⇒ 那天沒有減資。
        if (r["stock_id"], r["date"]) in _KNOWN_DUP:
            src["revivt(官方重複，已扣)"] += 1
            continue
        if pre and ref and r["stock_id"] in codes:
            out[(r["stock_id"], r["date"])] = (ref / pre, "revivt", pre, ref)
            src["revivt"] += 1
    if os.path.isdir(TWEX):                    # ③ 轉上市之後（TWT49U）
        for n in sorted(os.listdir(TWEX)):
            if not n.endswith(".csv"):
                continue
            for r in _rows(os.path.join(TWEX, n)):
                pre, ref = _f(r.get("pre_close")), _f(r.get("ref_price"))
                k = (r.get("stock_id", ""), r.get("date", ""))
                if pre and ref and k[0] in codes and k not in out:
                    out[k] = (ref / pre, "TWT49U", pre, ref)
                    src["TWT49U"] += 1
    return out, dict(src)


def otc_codes():
    """→ **曾經**在上櫃出現過的代號（判準取自日檔本身的 `market` 欄）。

    ⛔ 不用 `stocks.csv` 的 `market`：那是**當下**的市場，
    一檔轉上市之後就查不到它的上櫃時期——而那正是 D 類最容易出現的地方。
    """
    out = set()
    if not os.path.isdir(DAILY):
        return out
    for n in sorted(os.listdir(DAILY)):
        if not n.endswith(".csv"):
            continue
        try:
            with io.open(os.path.join(DAILY, n), encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    if (r.get("market") or "") == "tpex":
                        out.add(r.get("stock_id", ""))
        except OSError:
            pass
    out.discard("")
    return out


def ours(codes):
    """→ {(code, date): (factor, event, kind)}。只取 `codes` 裡那些檔。"""
    out = {}
    if not os.path.isdir(ADJ):
        return out
    for n in sorted(os.listdir(ADJ)):
        if not n.endswith(".csv") or n == "_index.csv":
            continue
        code = n[:-4]
        if code not in codes:
            continue
        for r in _rows(os.path.join(ADJ, n)):
            fac = _f(r.get("factor"))
            if r.get("date") and fac:
                out[(code, r["date"])] = (fac, r.get("event", ""),
                                          r.get("kind", ""))
    return out


def classify(off, mine, lo, hi, tol=TOL):
    """→ {A/B/C/D: [...]}。⛔ 四類分開，不合計。

    ⚠ 比對窗只取 `lo ~ hi`（我方涵蓋期起點 ~ 今天）：
    ⛔ 涵蓋期之前的「官方有我方沒有」不是缺陷（我方日檔還沒開始），
    ⛔ 而**今天之後**的是官方的**預告列**（`revivt` 會回未來的恢復買賣日）
      ——把預告當缺口會讓這份報告每天假紅。
    """
    res = {"A": [], "B": [], "C": [], "D": []}
    for k in set(off) | set(mine):
        if not (lo <= k[1] <= hi):
            continue
        o, m = off.get(k), mine.get(k)
        if o and m:
            (res["A"] if abs(o[0] - m[0]) <= tol else res["B"]).append(
                (k[0], k[1], round(o[0], 8), round(m[0], 8), o[1], m[1]))
        elif o:
            res["C"].append((k[0], k[1], round(o[0], 8), o[1]))
        else:
            res["D"].append((k[0], k[1], round(m[0], 8), m[1], m[2]))
    for v in res.values():
        v.sort(key=lambda x: (x[1], x[0]))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tol", type=float, default=TOL)
    a = ap.parse_args()

    rl = runlog.Run("otc_adj_compare")
    rl.info("⛔ 這一支只讀不寫",
            "換供料的**第 1 步**（情報分析線 2026-09-10 20:00 裁）："
            "先出差異清單，⛔ 確認無誤之前一列都不動 `data/adj/`")

    codes = otc_codes()
    off, src = official(codes)
    mine = ours(codes)
    days = sorted(n[:-4] for n in os.listdir(DAILY)) if os.path.isdir(DAILY) else []
    lo = days[0] if days else ""
    hi = datetime.now(TPE).strftime("%Y-%m-%d")
    rl.info("官方（三支聯集）", f"{len(off):,} 筆｜{src}")
    rl.info("我方 data/adj（只算曾經上櫃的 " + f"{len(codes):,} 檔）",
            f"{len(mine):,} 筆")
    rl.check("算得出比對窗（⛔ 沒有日檔就無從判斷涵蓋期）", bool(lo),
             f"{lo} ~ {hi}")
    if not lo:
        return rl.finish()
    rl.info("比對窗", f"{lo} ~ {hi}　⚠ 窗外不比："
                      "之前是我方還沒開始，之後是官方的**預告列**")

    res = classify(off, mine, lo, hi, a.tol)
    for k, why in (("A", "兩邊都有、factor 逐位相同 ⇒ 無事"),
                   ("B", "兩邊都有、**factor 不同** ⇒ ⛔ 換源的真正風險"),
                   ("C", "官方有、我方沒有 ⇒ 要補"),
                   ("D", "我方有、官方沒有 ⇒ ⛔⛔ 換源會**刪掉**它")):
        rl.info(f"  {k}：{why}", f"**{len(res[k]):,} 筆**")
    rl.info("  B 類前 10", str(res["B"][:10]) if res["B"] else "（沒有）")
    rl.info("  C 類的來源分布",
            str(dict(Counter(x[3] for x in res["C"]))) if res["C"] else "（沒有）")
    # ⭐ D 類要**分因**，⛔ 不是給一個數字：情報分析線點名的三種
    #   （減資／轉上市後／ETF 分割）各自的處置完全不同。
    dby = Counter(x[3] or "（沒有 event 欄）" for x in res["D"])
    rl.info("  ⛔ D 類的 event 分布（⚠ 這幾種 `exDailyQ` 都沒有）",
            str(dict(dby)) if res["D"] else "（沒有）")
    rl.info("  ⛔ D 類前 10", str(res["D"][:10]) if res["D"] else "（沒有）")

    # ⛔ 這一支**不設 check 判成敗**：它的產出是清單，不是「過或不過」。
    #   ⚠ 設成 check 會逼出一個「差異要小於幾筆」的門檻，
    #     而那個門檻沒有任何依據 ⇒ 只會變成每天紅然後被忽略。
    #   ⭐ 唯一該紅的是「三支官方來源少了一支」——那會讓 D 類假性變大，
    #     而**假性變大的 D 類會讓人以為官方來源不能用**，方向剛好相反。
    # ⛔ 判準是**三個名字都在**，⚠ 不是 `len(src) == 3`：
    #   `src` 現在還會多一個「官方重複，已扣」的計數鍵
    #   ⇒ 數個數會在「三支都在、但多了一個統計鍵」時假紅，
    #     也會在「少一支、卻多一個別的鍵」時**假綠**——⛔ 後者才是致命的那一種。
    _want = {"exDailyQ", "revivt", "TWT49U"}
    rl.check("⭐ 官方三支來源都讀到了（⛔ 少一支會讓 D 類假性變大）",
             _want <= set(src),
             f"讀到 {sorted(src)}｜⚠ 缺 {sorted(_want - set(src))}"
             if not _want <= set(src) else str(src))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["class", "stock_id", "date", "official_factor",
                    "our_factor", "official_src", "our_event", "our_kind"])
        for c, x in (("A", res["A"]), ("B", res["B"])):
            for r in x:
                w.writerow([c, r[0], r[1], r[2], r[3], r[4], r[5], ""])
        for r in res["C"]:
            w.writerow(["C", r[0], r[1], r[2], "", r[3], "", ""])
        for r in res["D"]:
            w.writerow(["D", r[0], r[1], "", r[2], "", r[3], r[4]])
    rl.info("差異清單", f"data/meta/_otc_adj_compare.csv｜"
                        f"{sum(len(v) for v in res.values()):,} 列")
    rl.info("⇒ 下一步", "⛔ 由市場情報分析線看完 B／D 兩類再決定換不換源。"
                        "⚠ D 類一筆都不能自動處理。")
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
