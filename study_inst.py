#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""study_inst.py — 研究一：法人買賣超「多少算多」。離線、只讀。

⛔ **門檻全部來自 `sources/inst_study_prereg.md`（2026-09-03 寫定，在看到任何
數字之前）。這支只追加結果，不修改任何一條門檻。** 事後才定門檻等於沒有門檻。

判準逐字照抄（不是我訂的）：

  樣本    上市股票，2024-01-01 ~ 2026-09-03
  訊號    I5(s,t) = 個股 s 截至第 t 個交易日的近 5 個交易日三大法人合計買賣超（股）
  百分位  p(s,t) = I5 在**該檔自己**前 252 個交易日（含當日）之中的百分位
          只用 t 當日與之前的資料；窗口內不足 200 個交易日就跳過
  報酬    R20(s,t) = t 日收盤買進、t+20 個交易日收盤賣出
  分組    p≥95／90–95／75–90／25–75（基準）／10–25／≤10。**買超賣超兩尾都做**
  通過    三條全部成立才算找到門檻：
          1. p≥95 的 R20 **中位數** 比基準組高 ≥ 1.0 個百分點
          2. 切成 2024-01~2025-06 與 2025-07~2026-09 兩段，**兩段都要成立**
          3. p≥95 在**每一個子期間**至少 500 個觀察值
  穩健    R10 與 R60 各跑一次；三個視窗方向不一致就三組都揭露，不可挑好看的
          流動性：主要分析不設門檻，另跑一次排除 20 日均額最低五分之一的版本
  ⛔ 重疊樣本 → **只報描述統計，不報 p 值**
  ⛔ 不寫「全部」「沒有例外」，要寫成「N 組中 M 組」

★ 兩條「已經過期但不得就地改」的限制（交付附註寫明）：
  - **未還原價**。`data/adj/` 已經完成，但改用還原價是**開一份新的事前判準**，
    不是改這一份。本檔照原文用未還原價。
  - **只有上市**。`otcinst` 已上線、`stocks_inst/` 是上市＋上櫃合併，
    但納入上櫃同樣要開新判準。本檔照原文只取上市。
"""
import csv
import io
import os
import sys

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT = os.path.join(_ROOT, "meta", "_study_inst.md")

START, END = "2024-01-01", "2026-09-03"
SPLITS = [("2024-01~2025-06", "2024-01-01", "2025-06-30"),
          ("2025-07~2026-09", "2025-07-01", "2026-09-03")]
WIN = 252          # 百分位窗口（交易日）
MIN_WIN = 200      # 窗口內不足這麼多天就跳過
# ⚠ 判準寫的是 `p ≥ 95`／`90–95`／…／`≤10`，所以區間是**左閉右開**、
#   最高與最低兩組各自含端點。第一版寫成 (lo, hi] 讓 p 剛好等於 95 的落進
#   「90-95」——與判準不符。門檻不能改，但**把區間實作成判準說的樣子是修正，不是改門檻**。
BANDS = [("p>=95", 95, 100.0001), ("90-95", 90, 95), ("75-90", 75, 90),
         ("25-75", 25, 75), ("10-25", 10, 25), ("p<=10", 0, 10.0001)]
BASE = "25-75"
GAP = 1.0          # 通過門檻①：高於基準 ≥ 1.0 個百分點
MIN_N = 500        # 通過門檻③：每個子期間至少 500 個觀察值


def listed_twse():
    p = os.path.join(_ROOT, "meta", "industry.csv")
    with io.open(p, encoding="utf-8") as f:
        return {r["stock_id"] for r in csv.DictReader(f) if r["market"] == "twse"}


def load(code):
    """→ [(date, close, amount, inst_total)]，只保留兩邊都有的交易日。"""
    pp = os.path.join(_ROOT, "stocks", f"{code}.csv")
    pi = os.path.join(_ROOT, "stocks_inst", f"{code}.csv")
    if not (os.path.exists(pp) and os.path.exists(pi)):
        return []
    inst = {}
    with io.open(pi, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                inst[r["date"]] = int(float(r["total"]))
            except (ValueError, TypeError, KeyError):
                continue
    out = []
    with io.open(pp, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d = r["date"]
            if d not in inst:
                continue
            try:
                c = float(r["close"])
                a = float(r["amount"] or 0)
            except (ValueError, TypeError):
                continue
            if c <= 0:
                continue
            out.append((d, c, a, inst[d]))
    out.sort()
    return out


def pct_rank(window, v):
    """v 在 window 裡的百分位（0~100）。只吃當日與之前的值。"""
    n = len(window)
    return sum(1 for x in window if x <= v) / n * 100


def band_of(p):
    """左閉右開 [lo, hi)。`p>=95` 與 `p<=10` 兩組的外側端點含在內。"""
    for name, lo, hi in BANDS:
        if lo <= p < hi:
            return name
    return None


def median(xs):
    if not xs:
        return None
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def build(codes, horizons=(10, 20, 60)):
    """→ list of dict(date, code, band, r10, r20, r60, amt20)"""
    rows = []
    for i, code in enumerate(sorted(codes), 1):
        s = load(code)
        if len(s) < WIN + max(horizons) + 5:
            continue
        dates = [x[0] for x in s]
        close = [x[1] for x in s]
        amt = [x[2] for x in s]
        tot = [x[3] for x in s]
        # I5：近 5 個交易日合計（含當日）
        i5 = [None] * len(s)
        run = 0
        for k in range(len(s)):
            run += tot[k]
            if k >= 5:
                run -= tot[k - 5]
            if k >= 4:
                i5[k] = run
        for k in range(len(s)):
            d = dates[k]
            if not (START <= d <= END) or i5[k] is None:
                continue
            lo = max(0, k - WIN + 1)
            win = [x for x in i5[lo:k + 1] if x is not None]
            if len(win) < MIN_WIN:
                continue          # 窗口內不足 200 個交易日就跳過
            b = band_of(pct_rank(win, i5[k]))
            if not b:
                continue
            rec = {"date": d, "code": code, "band": b,
                   "amt20": sum(amt[max(0, k - 19):k + 1]) / min(20, k + 1)}
            ok = True
            for h in horizons:
                if k + h >= len(s):
                    ok = False
                    break
                rec[f"r{h}"] = (close[k + h] / close[k] - 1) * 100
            if ok:
                rows.append(rec)
        if i % 200 == 0:
            print(f"  [{i}/{len(codes)}] {code} 累計 {len(rows):,} 個觀察值",
                  flush=True)
    return rows


L = []


def say(s=""):
    print(s, flush=True)
    L.append(s)


def table(rows, key, label):
    """印一組分組中位數，回 (p>=95 中位數 − 基準中位數, n)。"""
    say(f"\n**{label}**（n={len(rows):,}）")
    say("")
    say("| 分組 | 觀察值 | 中位數 % | 平均 % |")
    say("|---|---:|---:|---:|")
    med = {}
    for name, _lo, _hi in BANDS:
        g = [r[key] for r in rows if r["band"] == name]
        med[name] = median(g)
        if g:
            say(f"| {name} | {len(g):,} | {med[name]:+.2f} | "
                f"{sum(g) / len(g):+.2f} |")
        else:
            say(f"| {name} | 0 | — | — |")
    top, base = med.get("p>=95"), med.get(BASE)
    n95 = sum(1 for r in rows if r["band"] == "p>=95")
    if top is None or base is None:
        return None, n95
    return top - base, n95


def main():
    codes = listed_twse()
    say("# 研究一：法人買賣超「多少算多」")
    say("")
    say("⛔ 門檻全部來自 `sources/inst_study_prereg.md`（2026-09-03 寫定，"
        "在看到任何數字之前）。**本檔只追加結果，一條門檻都沒有改。**")
    say("")
    say(f"- 樣本：上市 {len(codes):,} 檔，{START} ~ {END}")
    say(f"- 訊號：近 5 個交易日三大法人合計買賣超（股）")
    say(f"- 百分位：該檔自己前 {WIN} 個交易日；窗口不足 {MIN_WIN} 天跳過")
    say("- ⚠ **未還原價**、**只有上市**——兩條限制在交付附註裡標成已過期，"
        "但事前判準只追加不修改，改用還原價或納入上櫃是**開一份新的判準**。")
    say("- ⚠ 相鄰交易日的 R20 高度重疊，**只報描述統計，不報 p 值**。")

    print("[study] 掃描中……", flush=True)
    rows = build(codes)
    say(f"\n總觀察值 **{len(rows):,}**")

    say("\n---\n\n## 主要分析（R20，全期）")
    d20, n95 = table(rows, "r20", "R20 全期")

    say("\n---\n\n## 通過門檻（三條全部成立才算找到門檻）")
    res = []
    for lab, a, b in SPLITS:
        sub = [r for r in rows if a <= r["date"] <= b]
        d, n = table(sub, "r20", f"R20 {lab}")
        res.append((lab, d, n))
    say("")
    say("| 條件 | 判準 | 實際 | 過？ |")
    say("|---|---|---|---|")
    c1 = d20 is not None and d20 >= GAP
    say(f"| ① 效果 | p≥95 中位數 − 基準 ≥ {GAP} pp | "
        f"{'—' if d20 is None else f'{d20:+.2f} pp'} | {'✓' if c1 else '✗'} |")
    c2 = all(d is not None and d >= GAP for _, d, _ in res)
    for lab, d, _n in res:
        say(f"| ② 穩定（{lab}）| 同上，兩段都要成立 | "
            f"{'—' if d is None else f'{d:+.2f} pp'} | "
            f"{'✓' if d is not None and d >= GAP else '✗'} |")
    c3 = all(n >= MIN_N for _, _, n in res)
    for lab, _d, n in res:
        say(f"| ③ 樣本量（{lab}）| p≥95 ≥ {MIN_N} | {n:,} | "
            f"{'✓' if n >= MIN_N else '✗'} |")

    say("\n---\n\n## 穩健性檢查")
    say("\n### 三個視窗（方向不一致就三組都揭露，不可挑好看的）")
    dirs = {}
    for h in (10, 20, 60):
        d, _ = table(rows, f"r{h}", f"R{h} 全期")
        dirs[h] = d
    same = len({(d or 0) > 0 for d in dirs.values()}) == 1
    say(f"\n三個視窗的方向{'一致' if same else '**不一致**'}："
        + "、".join(f"R{h} {('—' if d is None else f'{d:+.2f} pp')}"
                    for h, d in dirs.items()))
    if not same:
        say("→ 判準寫明：**方向不一致一律三組數字都揭露**，上面三張表就是。")

    say("\n### 流動性（另跑一次排除 20 日均額最低五分之一）")
    amts = sorted(r["amt20"] for r in rows)
    cut = amts[len(amts) // 5] if amts else 0
    liq = [r for r in rows if r["amt20"] > cut]
    dliq, _ = table(liq, "r20", f"R20 排除最低五分之一（門檻 {cut:,.0f} 元）")
    say(f"\n主要分析 {'—' if d20 is None else f'{d20:+.2f} pp'}"
        f"｜排除低流動性 {'—' if dliq is None else f'{dliq:+.2f} pp'}")
    if d20 is not None and dliq is not None and (d20 > 0) != (dliq > 0):
        say("→ **兩者結論不同，代表訊號其實來自流動性而不是法人行為。**")

    say("\n---\n\n## 結論")
    n_pass = sum([c1, c2, c3])
    if n_pass == 3:
        say(f"三條門檻 **3 組中 3 組成立**。p≥95 這一組的 R20 中位數"
            f"比基準高 {d20:+.2f} 個百分點，兩個子期間都成立、樣本量也夠。")
    else:
        say(f"三條門檻 **3 組中 {n_pass} 組成立**。依事前判準，結論是：")
        say("")
        say("> **未找到可用門檻，法人買賣超的百分位不足以單獨作為判讀依據。**")
        say("")
        say("判準寫明「不會因為結果不好看就換參數重跑」——上面的數字照實列出，"
            "沒有換過任何一條門檻。")
    say("\n⚠ 本研究只回答「多少算多」。三大法人在 2026-08-30 的八檔三年回測"
        "已被降級為「事後理解籌碼結構」，**本研究不是要把它升回進場條件**。")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(f"\n[study] 寫出 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
