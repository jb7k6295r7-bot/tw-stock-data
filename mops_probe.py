#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mops_probe.py — 用 urllib 重測 MOPS 全市場端點，判斷「不可用」是不是誤判。

## 起因

2026-08-30 專案停用了 `t187ap06_L_ci`／`t187ap07_L_ci`，理由是
「大型全市場 JSON **靜默截斷**」；`t187ap03_L` 也被記成「查 7 個代號只回 1101」。

2026-09-05 複測 `t187ap03_L`：
- **WebFetch** → 50 筆，最後一筆 1432
- **urllib（管線）** → **1,094 筆，完整**

**所以那次是 WebFetch 的限制，不是端點的性質。**
`docs/READ_CONTRACT.md` 第四節本來就寫著「不要用 WebFetch 讀大 JSON，
會被截斷**而且被憑空補齊**，看起來像完整的」。

→ 月營收與財報那幾個端點**很可能是同一種誤判**。本檔就是來驗這件事。

## ★ 怎麼證明「沒有被截斷」

截斷是無聲的：HTTP 200、JSON 合法、每一筆都是真的，只是少了後面。
所以**不能只看「有沒有回東西」**，要有獨立的完整性判準：

1. **最後一筆的代號**。截斷保留的是前 N 筆，所以尾巴會停在很小的代號
   （WebFetch 那次停在 1432）。完整的應該一路到 9xxx。
2. **對照 `data/meta/industry.csv` 的上市公司清單**（1,094 檔，已交叉驗證過）。
   算涵蓋率，並**依代號分段**看——截斷的特徵是「前段 100%、後段 0%」，
   而不是均勻地少。**這一項是最有力的**：均勻缺少可能是端點本來就不含某類公司，
   前後段斷崖式差異則一定是截斷。
3. **抽固定幾檔高代號**（9xxx）確認在不在。

三項任一不過就標「疑似截斷」，**不要因為「有一千多筆」就當它完整**。
"""

import argparse
import csv
import json
import os
import sys

import backfill as B

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
IND = os.path.join(_ROOT, "meta", "industry.csv")

TWSE = "https://openapi.twse.com.tw/v1/opendata/"
TPEX = "https://www.tpex.org.tw/openapi/v1/"

TARGETS = [
    # (標籤, 網址)
    ("上市 公司基本資料（對照組，已知完整）", TWSE + "t187ap03_L"),
    ("上市 月營收",                          TWSE + "t187ap05_L"),
    ("上市 綜合損益表-一般業",                TWSE + "t187ap06_L_ci"),
    ("上市 資產負債表-一般業",                TWSE + "t187ap07_L_ci"),
    ("上市 綜合損益表-金控",                  TWSE + "t187ap06_L_basi"),
    ("上市 資產負債表-金控",                  TWSE + "t187ap07_L_basi"),
    ("上市 綜合損益表-證券",                  TWSE + "t187ap06_L_bd"),
    ("上市 綜合損益表-保險",                  TWSE + "t187ap06_L_ins"),
    ("上櫃 公司基本資料（對照組）",           TPEX + "mopsfin_t187ap03_O"),
    ("上櫃 月營收",                          TPEX + "mopsfin_t187ap05_O"),
    ("上櫃 綜合損益表-一般業",                TPEX + "mopsfin_t187ap06_O_ci"),
    ("上櫃 資產負債表-一般業",                TPEX + "mopsfin_t187ap07_O_ci"),
]

CODE_KEYS = ("公司代號", "SecuritiesCompanyCode", "Code", "股票代號")


def listed_codes():
    """→ ({上市代號}, {上櫃代號})，取自已交叉驗證過的 industry.csv。"""
    tw, tp = set(), set()
    if not os.path.exists(IND):
        return tw, tp
    with open(IND, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            (tw if r["market"] == "twse" else tp).add(r["stock_id"])
    return tw, tp


def _code(rec):
    for k in CODE_KEYS:
        v = rec.get(k)
        if v:
            return str(v).strip()
    return ""


def probe(tag, url, want):
    print(f"── {tag}")
    print(f"   {url}")
    raw, err = B.get(url, retries=2, timeout=60)
    if err:
        print(f"   ✗ {err[:140]}\n")
        return
    try:
        d = json.loads(raw.decode("utf-8"))
    except Exception as ex:                                   # noqa: BLE001
        head = raw[:120].decode("utf-8", "replace").replace("\n", " ")
        print(f"   ✗ 非 JSON（{len(raw):,}B）{type(ex).__name__}：{head}\n")
        return
    if not isinstance(d, list):
        print(f"   △ 不是 list，頂層是 {type(d).__name__}；鍵={list(d)[:8]}\n")
        return
    codes = [c for c in (_code(r) for r in d if isinstance(r, dict)) if c]
    if not codes:
        keys = list(d[0])[:12] if d else []
        print(f"   △ {len(d):,} 筆，但找不到代號欄。欄位={keys}\n")
        return

    got = set(codes)
    print(f"   ✓ {len(raw):,} bytes、{len(d):,} 筆")
    print(f"     欄位（前 12）={list(d[0])[:12]}")
    print(f"     代號 首={codes[0]} 末={codes[-1]} 最大={max(got)}")

    # ── 完整性三項 ──
    verdict = []
    # ① 尾巴代號
    if max(got) < "5000":
        verdict.append(f"最大代號只到 {max(got)}（**疑似截斷**）")
    # ② 依代號分段的涵蓋率
    if want:
        buckets = {}
        for c in sorted(want):
            b = c[0] if c and c[0].isdigit() else "?"
            buckets.setdefault(b, [0, 0])
            buckets[b][0] += 1
            if c in got:
                buckets[b][1] += 1
        line = "  ".join(f"{b}xxx {h}/{t}" for b, (t, h) in sorted(buckets.items()))
        cov = sum(v[1] for v in buckets.values()) / max(1, sum(v[0] for v in buckets.values()))
        print(f"     對照 industry.csv：涵蓋 {cov*100:.1f}%")
        print(f"     分段  {line}")
        rates = [h / t for t, h in buckets.values() if t >= 20]
        if rates and (max(rates) - min(rates)) > 0.5:
            verdict.append("**分段涵蓋率斷崖式差異 → 幾乎確定是截斷**")
        elif cov < 0.5:
            verdict.append(f"涵蓋率僅 {cov*100:.0f}%（可能是端點不含某類公司，也可能截斷）")
    # ③ 高代號抽樣
    hi = [c for c in sorted(want) if c >= "8000"][:6] if want else []
    if hi:
        miss = [c for c in hi if c not in got]
        print(f"     高代號抽樣 {hi}｜缺 {miss if miss else '無'}")
        if len(miss) == len(hi):
            verdict.append("高代號全缺（**疑似截斷**）")

    print(f"     → {'；'.join(verdict) if verdict else '**看起來完整**'}\n")


def main():
    ap = argparse.ArgumentParser(description="MOPS 全市場端點完整性探測")
    ap.add_argument("--sleep", type=float, default=2)
    a = ap.parse_args()
    B.SLEEP = a.sleep
    tw, tp = listed_codes()
    if not tw:
        print("[mops] 找不到 data/meta/industry.csv——**完整性判準會少一項**，"
              "先跑 industry 再來。", file=sys.stderr)
    print(f"[mops] 對照基準：上市 {len(tw):,} 檔、上櫃 {len(tp):,} 檔"
          f"（來自已交叉驗證的 industry.csv）\n")
    import time
    for tag, url in TARGETS:
        probe(tag, url, tw if "上市" in tag else tp)
        time.sleep(a.sleep)
    print("[mops] 判準提醒：**「有一千多筆」不等於完整**。"
          "分段涵蓋率出現斷崖，就是截斷。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
