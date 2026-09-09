#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""industry_esb.py — 興櫃的產業別。**只讀 repo，不連外。**

## 為什麼興櫃一直沒有產業別

`industry.py` 的類股名單來自 TWSE `MI_INDEX`，**只涵蓋上市與上櫃**
⇒ 興櫃 364 檔在 `industry.csv` 裡根本沒有列。
先前把它記成「沒有來源」。

## ⭐ 2026-09-09：來源一直都在，而且就在 repo 裡

今天早上為了別的事做了一件小改動——`capital.py` 開始把端點回的**原始快照**
存進 `data/universe/capital/<tag>/<出表日期>.csv`（在那之前每天抓完就丟掉）。
其中 `tpex-mopsfin-R` 就是**興櫃**那份，而它的欄位裡有：

    SecuritiesIndustryCode

實測 `1150908.csv`：363 檔、產業別代碼**一個空值都沒有**。

⇒ 這是今天第四次「去某處找不到，就說它不存在」——
  前三次是集保、`_hist_status.csv`、上櫃股本。
  這一次的差別是：東西不但存在，**而且已經在我們自己的 repo 裡了**。

## ★ 代碼可以直接沿用上市上櫃那張表嗎——這件事**驗過才用**

⛔ 不可以假設兩邊的產業別代碼是同一套編碼。本檔每次跑都重驗一次：

    拿**上櫃**那份快照（`tpex-mopsfin-O`）的 `SecuritiesIndustryCode`
    去對 `industry.csv` 裡同一檔的 `industry_code`

2026-09-09 實測：**890 檔相同、0 檔不同、0 檔對不到**。
⇒ 同一套編碼，所以名稱表可以共用。
⛔ 這個檢查是 `rl.check`，**掉下 100% 就報 ✗**——
  編碼哪天改了要立刻知道，而不是安靜地掛上錯的產業名。

## ⛔ 為什麼另外寫一個檔，不併進 industry.csv

`industry.csv` 在多處被當成**母體**用：
`parvalue_scan.py` 的 `in_universe`、`feeds.py` 的 `known`、
「ETF 不在母體裡所以要全收」的邏輯。
併進去會**靜默改變**那些判斷（母體突然多 363 檔）。

⇒ 興櫃另存 `data/meta/industry_esb.csv`，要用的人明確地去讀它。
⚠ 這是**可逆**的選擇：日後要合併隨時可以合，
  但先合了再發現下游壞掉，壞掉的方式是安靜的。
  「是否併入」屬於語意決定 ⇒ 已去信請市場情報分析線裁定。

## ⚠ 32、33 這兩個代碼仍然沒有中文名

興櫃 363 檔裡有 11 檔落在 32、33——**正是上櫃那兩個一直沒有名稱的代碼**。
⇒ 兩個缺口其實是同一個缺口。這 11 檔的 `industry_name` 留空，
  ⛔ 不要填「其他」——那是編出來的。
"""
import csv
import io
import os
import sys

import runlog

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
IND = os.path.join(_ROOT, "meta", "industry.csv")
ARCH = os.path.join(_ROOT, "universe", "capital")
OUT = os.path.join(_ROOT, "meta", "industry_esb.csv")
HEADER = ["stock_id", "name", "market", "industry_code", "industry_name",
          "source", "asof"]
K_CODE = "SecuritiesCompanyCode"
K_IND = "SecuritiesIndustryCode"
K_ABBR = "CompanyAbbreviation"


def _latest(tag):
    """→ (路徑, 出表日期)。⛔ 沒有就回 (None, None)，不要自己造一個空的。"""
    d = os.path.join(ARCH, tag)
    if not os.path.isdir(d):
        return None, None
    fs = sorted(x for x in os.listdir(d) if x.endswith(".csv"))
    return (os.path.join(d, fs[-1]), fs[-1][:-4]) if fs else (None, None)


def _read(path):
    with io.open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    rl = runlog.Run("industry_esb")

    p_r, asof = _latest("tpex-mopsfin-R")
    if not p_r:
        rl.check("興櫃快照存在", False,
                 f"{ARCH}/tpex-mopsfin-R/ 沒有檔案——先跑 capital.py")
        return rl.finish()
    esb = _read(p_r)
    rl.info("興櫃快照", f"{os.path.basename(p_r)}｜{len(esb)} 檔")

    if not os.path.exists(IND):
        rl.check("industry.csv 存在", False, IND)
        return rl.finish()
    mine = {r["stock_id"]: r for r in _read(IND)}

    # ── ★ 編碼一致性：拿上櫃那份去對，⛔ 不是拿興櫃自己對自己
    p_o, _ = _latest("tpex-mopsfin-O")
    same = diff = nomatch = 0
    bad = []
    if p_o:
        for r in _read(p_o):
            sid = (r.get(K_CODE) or "").strip()
            code = (r.get(K_IND) or "").strip()
            m = mine.get(sid)
            if not m:
                nomatch += 1
                continue
            if (m.get("industry_code") or "").strip() == code:
                same += 1
            else:
                diff += 1
                if len(bad) < 5:
                    bad.append(f"{sid} 我方={m.get('industry_code')} 快照={code}")
    rl.info("編碼一致性（上櫃）", f"相同 {same}｜不同 {diff}｜對不到 {nomatch}")
    # ⛔ 這是**外部判準**：拿另一個市場的同一份欄位去驗，不是驗我自己算得對不對。
    rl.check("上櫃產業別代碼與 industry.csv 完全一致", diff == 0 and same > 0,
             f"不同 {diff} 檔"
             + ("：" + "；".join(bad) if bad else "")
             + "｜⛔ 不一致就代表兩邊不是同一套編碼，名稱表**不可以共用**")

    # ── 代碼 → 中文名（只從 industry.csv 既有的對應學，⛔ 不自己編）
    c2n = {}
    for r in mine.values():
        c = (r.get("industry_code") or "").strip()
        n = (r.get("industry_name") or "").strip()
        if c and n:
            c2n.setdefault(c, n)
    rl.info("代碼→名稱", f"{len(c2n)} 個代碼有中文名")

    rows, unnamed = [], {}
    for r in esb:
        sid = (r.get(K_CODE) or "").strip()
        if not sid:
            continue
        code = (r.get(K_IND) or "").strip()
        name = c2n.get(code, "")
        if code and not name:
            unnamed[code] = unnamed.get(code, 0) + 1
        rows.append([sid, (r.get(K_ABBR) or "").strip(), "esb", code, name,
                     f"tpex-mopsfin-R:{asof}", asof])
    rows.sort()

    named = sum(1 for x in rows if x[4])
    rl.info("興櫃產業別", f"{len(rows)} 檔｜有中文名 {named}｜"
                        f"只有代碼 {len(rows) - named}"
                        + (f"（代碼 {sorted(unnamed)}）" if unnamed else ""))
    # ⛔ 「有代碼沒名稱」不是錯，是 32/33 那兩個代碼本來就還沒有中文名。
    #   真正該擋的是**連代碼都沒有**——那才代表解析壞了。
    nocode = [x[0] for x in rows if not x[3]]
    rl.check("每一檔都有產業別代碼", not nocode,
             f"{len(nocode)} 檔沒有代碼：{nocode[:8]}")

    # ── ⚠ 我方認為是興櫃、但這份快照裡沒有的
    #   ⛔ **不要**用「多天快照聯集」去補。那招在 `capital.py` 的母體是對的
    #     （日檔只收當天有成交的，冷門股會缺席），但這裡不一樣：
    #     這份是**公司名冊**不是成交檔，缺席的正常解釋是
    #     「它已經轉上市櫃或終止興櫃」——聯集會讓退場的公司永遠留著。
    #   ⇒ 不補，但**要說出來**，否則差異會靜靜地掛在那裡沒人知道。
    cap_p = os.path.join(_ROOT, "meta", "capital.csv")
    if os.path.exists(cap_p):
        here = {x[0] for x in rows}
        gone = [(r["stock_id"], r.get("name", ""), r.get("asof", ""))
                for r in _read(cap_p)
                if r.get("market") == "emerging" and r["stock_id"] not in here]
        rl.info("我方有、名冊沒有",
                f"{len(gone)} 檔"
                + (f"：{gone}（多半是已轉上市櫃或終止興櫃，⛔ 不補）"
                   if gone else "（沒有）"))

    try:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with io.open(OUT, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(HEADER)
            w.writerows(rows)
        print(f"[industry_esb] 寫出 {OUT}（{len(rows)} 列）")
    except OSError as ex:                                        # noqa: BLE001
        rl.check("寫得出 industry_esb.csv", False, str(ex))
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
