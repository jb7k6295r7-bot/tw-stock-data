#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""par_timeline.py — 面額的時間軸。**只讀 repo，不連外。**

## 為什麼需要它

`股數 ＝ 股本 ÷ 面額`。要從 MOPS 的季報股本回推歷史股數，就得知道
**每一季當時的面額**，而不是今天的面額。

## ⛔ 方向：從今天往回，不是從 10 往前

⚠ 2026-09-09 實測：三份官方名冊 2,347 檔裡，`資本額 ÷ 股數` 不是 10 的有 76 檔，
其中 **54 檔我方根本沒有面額變更事件**——它們**一上市就不是 10**
（DR 是外國原股面額、興櫃與 KY 有一票 IPO 就採彈性面額）。
⇒ 「從 10 往前推」有 54 個反例。

**6919 康霈* 就是活生生的一個**：官方今天的面額是 **0.5**，
而我方只有一筆 ×10 的事件 ⇒ 若假設起點是 10，會得到 1.0，**錯一倍**。
往回走則得到「2025-07-21 之前是 5」——它 IPO 時面額就是 5。
⚠ 我一度以為那是「漏抓一筆面額變更」，去翻它 2025-07-21 之後的價格：
**278 個交易日連續、沒有空窗、沒有跳價** ⇒ 沒有第二次變更，是起點不是 10。

⇒ 演算法：

    par(今天) ← 官方名冊的「普通股每股面額」欄（**觀測值**）
    par(事件之前) ＝ par(事件之後) × share_mult

## ★ 今天的面額從哪裡來——這一段本身也是今天才修好的

端點**一直都有給**面額，值長這樣：`'新台幣                  0.5000元'`。
我方的 `_num()` 對它 `float()` 會炸 ⇒ 回空字串 ⇒ 整欄被丟掉。
⇒ 已改用 `_num_par()`。⛔ 它只脫固定的字首字尾，**不從字串裡撈第一個數字**——
那種寫法會把「無面額」也讀出一個數來，而**錯的面額比沒有面額危險得多**。

## ⛔ 這份的限制，引用前要知道

1. **只回溯到 `par_change.csv` 有的事件**（2015 起；上櫃官方表只到 2019-09-09，
   更早那段是靠我方掃描器背書，殘餘風險見 `sources/README.md`）。
2. 事件清單漏一筆，該檔在那個事件**之前**的面額就全錯。
3. ⚠ 這份**不含**「IPO 當時的面額」——它只說「已知事件之間是多少」。
"""
import csv
import glob
import io
import os
import sys

import runlog

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
ARCH = os.path.join(_ROOT, "universe", "capital")
PC = os.path.join(_ROOT, "meta", "par_change.csv")
OUT = os.path.join(_ROOT, "meta", "par_timeline.csv")
HEADER = ["stock_id", "name", "market", "valid_from", "valid_to", "par",
          "source", "note"]

SRC = (("twse-opendata-L", "公司代號", "公司簡稱", "普通股每股面額", "twse"),
       ("tpex-mopsfin-O", "SecuritiesCompanyCode", "CompanyAbbreviation",
        "ParValueOfCommonStock", "tpex"),
       ("tpex-mopsfin-R", "SecuritiesCompanyCode", "CompanyAbbreviation",
        "ParValueOfCommonStock", "emerging"))


def today_par():
    """→ ({code: (面額, 簡稱, 市場, 出表日期)}, {code: (簡稱, 市場, 種類)})。

    第二個回傳是**沒有面額可言**的標的。⛔ 它們不是「缺資料」：
      `no_par`      無面額股（面額欄逐字寫「無面額」）⇒ 資本額÷股數是平均發行價
      `foreign_par` 外幣面額（美元／港幣…）⇒ 與新台幣資本額不可相除
    ⚠ 上一版直接把它們**跳過**，於是它們安靜地不在時間軸裡——
      「不在」與「沒有面額」在檔案上長得一樣，而那是兩件事。
    """
    import capital as C
    out, none_par = {}, {}
    for tag, ck, nk, pk, mkt in SRC:
        fs = sorted(glob.glob(os.path.join(ARCH, tag, "*.csv")))
        if not fs:
            continue
        asof = os.path.basename(fs[-1])[:-4]
        with io.open(fs[-1], encoding="utf-8") as f:
            for r in csv.DictReader(f):
                code = (r.get(ck) or "").strip()
                if not code:
                    continue
                raw = str(r.get(pk) or "")
                kind = C.par_kind(raw)
                if kind in ("no_par", "foreign"):
                    none_par[code] = ((r.get(nk) or "").strip(), mkt,
                                      "no_par" if kind == "no_par" else "foreign_par")
                    continue
                pv = C._num_par(raw)
                if pv:
                    out[code] = (float(pv), (r.get(nk) or "").strip(), mkt, asof)
    return out, none_par


def events():
    """→ {code: [(日期, 倍率)]}，由新到舊。"""
    out = {}
    if not os.path.exists(PC):
        return out
    with io.open(PC, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                m = float(r.get("share_mult") or 0)
            except ValueError:
                continue
            if m > 0:
                out.setdefault(r["stock_id"], []).append((r["event_date"], m))
    for k in out:
        out[k].sort(reverse=True)
    return out


def main():
    rl = runlog.Run("par_timeline")
    cur, none_par = today_par()
    ev = events()
    rl.info("今天的面額", f"{len(cur)} 檔（來自端點自己的面額欄）")
    rl.info("面額變更事件", f"{len(ev)} 檔／{sum(len(v) for v in ev.values())} 筆")

    rows, noev, noparr = [], 0, []
    for code, (pv, name, mkt, asof) in sorted(cur.items()):
        # 事件由新到舊。最後一段（到今天）的起日 ＝ 最近一次事件日；
        # 每往回跨一個事件，面額就 × 該事件的 share_mult。
        # ⛔ 第一版把 valid_from 錯位了一格（最後一段寫成 valid_from=""），
        #   而**自我檢查一當場抓到 22 檔對不上** ⇒ 這就是那個檢查存在的理由。
        evs = ev.get(code, [])
        segs = [(evs[0][0] if evs else "", pv)]      # (valid_from, par)
        p = pv
        for i, (_d, m) in enumerate(evs):
            p = p * m
            segs.append((evs[i + 1][0] if i + 1 < len(evs) else "", p))
        segs.sort(key=lambda x: x[0] or "0")
        for i, (vf, val) in enumerate(segs):
            vt = segs[i + 1][0] if i + 1 < len(segs) else ""
            rows.append([code, name, mkt, vf, vt, f"{val:g}",
                         "endpoint+par_change" if evs else "endpoint", ""])
        if not ev.get(code):
            noev += 1

    # ★ 沒有面額可言的，也要有一列——⛔ 不可以只是「不在檔案裡」。
    #   「不在」與「沒有面額」在檔案上長得一樣，而那是兩件事。
    for code, (name, mkt, kind) in sorted(none_par.items()):
        rows.append([code, name, mkt, "", "", "", "endpoint", kind])
    import collections as _c
    rl.info("沒有面額可言",
            f"{len(none_par)} 檔：{dict(_c.Counter(v[2] for v in none_par.values()))}"
            "（⛔ 這不是缺資料，是這個欄位對它們沒有意義）")

    # ★ 自我檢查一：最後一段的面額必須等於端點今天給的值（⛔ 不然是我算錯）
    bad = []
    for code, (pv, *_x) in cur.items():
        last = [r for r in rows if r[0] == code and r[4] == "" and r[5]]
        if last and abs(float(last[0][5]) - pv) > 1e-9:
            bad.append((code, last[0][5], pv))
    rl.check("最後一段面額＝端點今天的值", not bad, f"{len(bad)} 檔不符：{bad[:5]}")

    # ★ 自我檢查二：往回推出來的**起點**若不是 10，把它列出來
    #   ⛔ 這不是錯——54 檔一上市就不是 10。列出來是要讓人看見，不是要修它。
    first = {}
    for r in rows:
        # ⚠ `par` 是空的那幾列是「沒有面額可言」的標的，⛔ 不可以 float()。
        if r[3] == "" and r[5]:
            first[r[0]] = float(r[5])
    odd = sorted((k, v) for k, v in first.items()
                 if ev.get(k) and abs(v - 10) > 1e-9)
    rl.info("有事件、但回推起點不是 10 的",
            f"{len(odd)} 檔：{odd[:8]}"
            + "（⛔ 這不是錯：IPO 面額本來就不一定是 10，"
              "6919 康霈* 已逐檔查證過——事件後 278 個交易日無空窗無跳價）")

    try:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with io.open(OUT, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(HEADER)
            w.writerows(rows)
        print(f"[par_timeline] 寫出 {OUT}（{len(rows)} 列／{len(cur)} 檔）")
        rl.info("寫出", f"{len(rows)} 列／{len(cur)} 檔｜其中有事件的 {len(ev)} 檔")
    except OSError as ex:                                        # noqa: BLE001
        rl.check("寫得出 par_timeline.csv", False, str(ex))
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
