#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""otcparvalue.py — 上櫃面額變更的還原因子，用**股數倍率**推導。**只讀 repo，不連外。**

## 為什麼要有這一支

TWSE `change/TWTB8U` 只涵蓋上市（2026-09-09 實測：同一發請求上市 2/2、上櫃 0/5）。
TPEx 沒有對應端點（swagger 225 個端點裡沒有減資／面額／參考價）。
於是全庫 24 筆面額變更裡，**上櫃那 14 筆一直沒有還原因子**——
跨過那 14 個事件日的長期報酬、均線、扣抵值全部是錯的，而且不會報錯。

## 為什麼股數倍率算得出來，而且比價格比值準

面額變更時**資本額不變**：面額 10 元改 1 元 ＝ 股數 ×10、每股價值 ÷10。
所以 **還原因子 ＝ 股數前 ÷ 股數後**，是精確值不是估計。

上市那 10 筆給了獨立佐證（2026-09-09 官方回補完成，逐筆核對 10/10 相符）：
官方「恢復買賣參考價 ÷ 停止買賣前收盤」全部是乾淨的 1/k
（0.05／0.10／0.25／0.50），而復牌首日相對參考價是 −9.9% ~ +10.0%。
⇒ **真實因子是乾淨的 1/k，價格比值 ＝ 因子 × 復牌首日漲跌。**
   價格比值含復牌首日那一段漲跌，股數不含——所以股數比較準。

## 四道閘門（市場情報分析線 2026-09-09 核可，(c) 是 CODE 提的）

    (a) 倍率必須是**精確整數比**（分母 ≤ 4），不是就**不寫並報 ✗**
        ⛔ 不要四捨五入、不要「接近就當是」
    (b) 輸出標明**來源是 shares 推導，不是官方公告**
    (c) 日後 TPEx 官方端點出現時**官方值優先**；兩者不符要報 ✗，
        **不可靜默取一邊**
    (d) 回補後拿**復牌首日收盤 ÷ 推得參考價**驗，必須落在 **±10%** 內

★ (d) 是**外部判準**（漲跌幅限制），不是拿自己的產出驗自己——
  這一點是這四道裡最重要的：其餘三道都只在檢查我自己的算術一致，
  只有 (d) 拿了一個資料庫之外的事實來對。

## ⚠ 一個沒有樣本的風險

股數在停止買賣期間**理論上**也可能因增資而變動，那樣倍率就不會是乾淨整數。
實測 14/14 都乾淨，所以目前沒有這種案例——**閘門 (a) 就是為它設的**。
"""
import argparse
import csv
import io
import os
import sys
from fractions import Fraction

import runlog

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
SRC = os.path.join(_ROOT, "meta", "par_change.csv")
OFFICIAL_DIR = os.path.join(_ROOT, "universe", "parvalue")     # 上市官方，用來做閘門 (c)
OUT_DIR = os.path.join(_ROOT, "universe", "otcparvalue")
HEADER = ["date", "stock_id", "pre_close", "ref_price", "reason",
          "open_base", "ex_ref_price", "halt_date", "derived_from"]

MAX_DEN = 4          # 閘門 (a)：倍率的分母上限
BAND = 0.10          # 閘門 (d)：復牌首日相對參考價的容許帶（漲跌幅限制）


def fnum(v):
    s = "" if v is None else str(v).replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def load_official():
    """上市官方那批，閘門 (c) 用。→ {(sid, date): (pre, ref)}"""
    out = {}
    if not os.path.isdir(OFFICIAL_DIR):
        return out
    for fn in sorted(os.listdir(OFFICIAL_DIR)):
        if not fn.endswith(".csv"):
            continue
        with io.open(os.path.join(OFFICIAL_DIR, fn), encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                pre, ref = fnum(r.get("pre_close")), fnum(r.get("ref_price"))
                if pre and ref:
                    out[(r.get("stock_id", "").strip(),
                         r.get("date", "").strip())] = (pre, ref)
    return out


def main():
    ap = argparse.ArgumentParser(description="上櫃面額變更：用股數倍率推還原因子")
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if not a.run:
        ap.print_help()
        return 1

    rl = runlog.Run("otcparvalue")
    if not os.path.exists(SRC):
        rl.check("par_change.csv 存在", False, SRC)
        return rl.finish()

    rows = list(csv.DictReader(io.open(SRC, encoding="utf-8")))
    src = [r for r in rows if r.get("evidence") == "shares_int_mult"]
    rl.info("來源", f"{SRC} 共 {len(rows)} 列，其中 shares 推導 {len(src)} 列")

    official = load_official()
    bad_mult, bad_band, conflict, out = [], [], [], []
    for r in src:
        sid, day = r["stock_id"], r["event_date"]
        pre, close = fnum(r["prev_close"]), fnum(r["close"])
        mult = fnum(r["share_mult"])
        if not (pre and close and mult):
            bad_mult.append(f"{sid}/{day}(欄位缺)")
            continue

        # ── 閘門 (a) 倍率必須是精確整數比 ──
        fr = Fraction(mult).limit_denominator(MAX_DEN)
        if abs(float(fr) - mult) > 1e-9:
            bad_mult.append(f"{sid}/{day}(×{mult:g} 不是分母≤{MAX_DEN} 的整數比)")
            continue

        ref = pre / mult                       # 推得的恢復買賣參考價

        # ── 閘門 (d) 復牌首日相對參考價要落在 ±10% ──
        dev = close / ref - 1
        if abs(dev) > BAND + 1e-9:
            bad_band.append(f"{sid}/{day}({dev:+.1%})")
            continue

        # ── 閘門 (c) 官方值優先；不符報 ✗，不可靜默取一邊 ──
        off = official.get((sid, day))
        if off:
            if abs(off[1] / off[0] - 1 / mult) > 1e-6:
                conflict.append(f"{sid}/{day}(官方 {off[1] / off[0]:.4f} "
                                f"vs 推導 {1 / mult:.4f})")
                continue
            ref = off[1]                       # 官方有就用官方的

        out.append([day, sid, f"{pre:g}", f"{ref:g}", "面額變更（股數推導）",
                    "", "", "", "shares_ratio"])

    rl.check(f"(a) 倍率都是精確整數比（分母 ≤ {MAX_DEN}）", not bad_mult,
             "、".join(bad_mult) if bad_mult else f"{len(src)} 筆全過")
    rl.check(f"(d) 復牌首日相對推得參考價落在 ±{BAND:.0%}", not bad_band,
             "、".join(bad_band) if bad_band else f"{len(src)} 筆全過")
    rl.check("(c) 與官方值沒有衝突", not conflict,
             "、".join(conflict) if conflict else
             f"官方涵蓋 {len([1 for r in src if (r['stock_id'], r['event_date']) in official])} 筆")

    # ⛔ 任何一道沒過就**整批不寫**——與 tdcc 同一個規矩。
    #   寫一半會讓「有些檔還原了、有些沒有」，而那分不出來。
    if bad_mult or bad_band or conflict:
        print("[otcparvalue] ★ 閘門沒過，**整批不寫**", file=sys.stderr)
        return rl.finish()

    os.makedirs(OUT_DIR, exist_ok=True)
    byday = {}
    for r in out:
        byday.setdefault(r[0], []).append(r)
    for day, rs in byday.items():
        with io.open(os.path.join(OUT_DIR, f"{day}.csv"), "w",
                     encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(HEADER)
            w.writerows(rs)
    rl.info("寫出", f"{len(byday)} 個日檔、{len(out)} 筆")
    rl.check("寫出的筆數＝來源筆數", len(out) == len(src),
             f"{len(out)} / {len(src)}")
    print(f"[otcparvalue] 寫出 {len(byday)} 個日檔、{len(out)} 筆到 {OUT_DIR}")
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
