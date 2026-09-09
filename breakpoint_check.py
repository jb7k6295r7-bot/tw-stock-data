#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把回測線的 `backtest/breakpoint_scan.py` 接進每日管線，寫 `_last_run.md`。

    python3 breakpoint_check.py

## 為什麼是一層薄殼，不是把那支複製過來

`backtest/` 是**回測線**的，`breakpoint_scan.py` 的規則（比值 ≤ 0.55／≥ 1.8、
連續缺 ≥ 5 個交易日、流動性門檻）由 K線線裁定。⛔ 共用的引擎不可以在本地分岔——
複製一份過來，兩邊就會各自演化，而且**不會有人發現**，直到兩份的數字對不起來。
所以這一支只做三件本來就屬於施工這一邊的事：

  ① 呼叫他們的 `main()`，把 stdout 原封不動存成 `data/meta/_breakpoint_scan.md`
  ② 用他們的回傳碼寫進 `data/meta/_last_run.md`
  ③ pandas 缺席時**報 ✗，不是安靜跳過**

## 判定

市場情報分析線 2026-09-09 08:45 裁定：**要排、不擋整批、報 ✗ 吐差異清單**。
只有「漏抓」（`par_change.csv` 裡既無因子、規則也沒抓到）才是 ✗——
那代表規則寫錯了。規則另外抓到的長停牌**不算錯**，那是「洞算不算斷點」的
語意問題，歸情報分析裁；這裡只把數字列出來。
"""
import csv
import io
import os
import re
import sys

import runlog

_HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(_HERE, "data", "meta", "_breakpoint_scan.md")
# ★ 附表：**所有**缺 ≥ 5 日且區間內無事件的洞，不論流動性（回測線 2026-09-09 09:50 加）。
#   ⚠ 為什麼要另存一份到 data/meta/：`backtest/results/` 是回測線的產出目錄，
#     由他們的分支決定內容；資料庫這一側要引用的東西不可以指到別人的工作區——
#     那是「拿間接證據代替直接證據」的另一種形狀（我引的版本不一定是他們現在的版本）。
#   ⛔ 這一份**不設任何 ✗**：1,402 列是「拿去查的表」，不是閘門。
#     對它設門檻等於替情報分析裁「洞算不算斷點」，那不是我的權限。
HOLES_SRC = os.path.join(_HERE, "backtest", "results", "holes_scan.csv")
HOLES_OUT = os.path.join(_HERE, "data", "meta", "_holes_scan.csv")


def _coverage():
    """→ (N₁ 集合, 斷點掃描母體, 差集[(代號, kind, market)])。

    ⛔ N₁ 的定義照抄情報分析線的逐字版（金額、T−20~T−1、算術平均、
      無成交當 0、`>= 50_000_000` 含等於、不含當日），
      **不是我這邊另外訂一個**——兩邊算出不同的母體才是最糟的情況。
    """
    import collections
    import glob
    dayp = sorted(glob.glob(os.path.join(_HERE, "data", "universe", "daily", "*.csv")))
    days = [os.path.basename(x)[:-4] for x in dayp]
    win = days[-21:-1]
    amt = collections.defaultdict(float)
    seen = set()
    for d in win:
        with io.open(os.path.join(_HERE, "data", "universe", "daily", d + ".csv"),
                     encoding="utf-8") as f:
            for r in csv.DictReader(f):
                sid = (r.get("stock_id") or "").strip()
                if not sid:
                    continue
                seen.add(sid)
                try:
                    amt[sid] += float((r.get("amount") or "0").replace(",", ""))
                except ValueError:
                    pass
    n1 = {s for s in seen if win and amt[s] / len(win) >= 50_000_000}
    mk = {}
    with io.open(os.path.join(_HERE, "data", "meta", "stocks.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            mk[r["stock_id"]] = r
    # ⛔ 條件照抄 backtest/data.py 的 load_universe()：kind==stock 且 twse/tpex。
    #   興櫃與 ETF 被排除**是那邊刻意的**，不是漏掉。
    uni = {s for s, r in mk.items()
           if r.get("kind") == "stock" and r.get("market") in ("twse", "tpex")}
    dd = [(s, mk.get(s, {}).get("kind", "?"), mk.get(s, {}).get("market", "?"))
          for s in sorted(n1 - uni)]
    return n1, uni, dd


def main():
    rl = runlog.Run("breakpoint_scan")

    try:
        from backtest import breakpoint_scan as BS
    except Exception as ex:                                      # noqa: BLE001
        # ⚠ 不可以安靜跳過。這一支唯一的價值就是「規則有沒有寫錯」，
        #   跳過等於天天回報「沒問題」——那是最貴的失敗形狀。
        rl.info("狀態", f"載入失敗：{type(ex).__name__}: {ex}")
        rl.check("backtest.breakpoint_scan 載得起來（需要 pandas）", False,
                 "載不起來就沒有對帳，等於這道檢查不存在")
        return rl.finish()

    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        rc = BS.main()
    except Exception as ex:                                      # noqa: BLE001
        sys.stdout = old
        txt = buf.getvalue()
        rl.info("狀態", f"執行中丟例外：{type(ex).__name__}: {ex}")
        _write(txt + f"\n\n⛔ 例外：{type(ex).__name__}: {ex}\n")
        rl.check("掃描跑完", False, f"{type(ex).__name__}: {ex}")
        return rl.finish()
    finally:
        sys.stdout = old
    txt = buf.getvalue()
    print(txt, end="")
    _write(txt)

    # 從輸出裡把數字撈出來當摘要。⛔ 判定用的是 rc，不是這幾個數字——
    #   正則沒對到只會讓摘要少一行，不會讓判定失準。
    m = re.search(r"斷點 (\d+) 個、(\d+) 檔", txt)
    if m:
        rl.info("全母體斷點", f"{m.group(1)} 個／{m.group(2)} 檔")
    m = re.search(r"已有因子 (\d+)、仍為斷點 (\d+)、漏抓 (\d+)", txt)
    if m:
        rl.info("對帳 par_change.csv",
                f"已有因子 {m.group(1)}／仍為斷點 {m.group(2)}／漏抓 {m.group(3)}")
    m = re.search(r"規則另外抓到（不在 par_change.csv）：(\d+) 個、(\d+) 檔", txt)
    if m:
        rl.info("規則另外抓到（長停牌，成因未定）",
                f"{m.group(1)} 個／{m.group(2)} 檔——"
                "「洞算不算斷點」歸情報分析裁，這裡只列數")
    m = re.search(r"洞 (\d+) 個、(\d+) 檔；其中 liq_ok (\d+) 個", txt)
    if m:
        rl.info("附表：所有無事件的長洞（不論流動性）",
                f"{m.group(1)} 個／{m.group(2)} 檔，其中流動性夠的 {m.group(3)} 個"
                "——完整表在 data/meta/_holes_scan.csv，⛔ 不設 ✗")
    n_h = _copy_holes()
    if n_h is not None:
        rl.info("_holes_scan.csv", f"{n_h} 列")
    lh = _long_hole_impact()
    if lh:
        rl.info("long_hole 對推薦母體的影響（每日更新）", lh)
    # ★ 母體覆蓋率：掃描的母體有沒有蓋住情報分析線的 N₁ 母體
    #   （市場情報分析線 2026-09-09 16:25 的要求，理由是他們今天在同一個形狀上摔過：
    #    「以為閘門跑的是母體，實際跑的是 11 檔」）。
    #   ⛔ 差集是 0 也要印。**只有異常時才輸出的東西，沒有基準可以比。**
    try:
        n1, uni, dd = _coverage()
        rl.info("母體覆蓋（vs N₁）",
                f"斷點掃描母體 {len(uni)} 檔｜N₁ {len(n1)} 檔｜"
                f"**N₁ 有而掃描母體沒有：{len(dd)} 檔**")
        if dd:
            from collections import Counter
            c = Counter(f"{k}/{m}" for _, k, m in dd)
            rl.info("  差集組成", "｜".join(f"{k} {v}" for k, v in c.most_common()))
            other = [x[0] for x in dd if x[1] != "etf"]
            rl.info("  其中非 ETF", f"{len(other)} 檔：{other[:12]}")
        # ⛔ 不寫成 check：差集不為 0 **不是錯**（掃描母體本來就排除 ETF 與興櫃），
        #   它是「這些檔由誰在看」的分工問題，要人決定，不是程式判對錯。
    except Exception as ex:                                      # noqa: BLE001
        rl.info("母體覆蓋（vs N₁）", f"算不出來：{type(ex).__name__}: {ex}")

    rl.info("完整輸出", "data/meta/_breakpoint_scan.md")

    rl.check("par_change.csv 沒有一筆漏抓", rc == 0,
             "漏抓＝既無還原因子、規則也沒抓到 ⇒ 規則寫錯了，"
             "清單在 data/meta/_breakpoint_scan.md")
    return rl.finish()


def _long_hole_impact():
    """`long_hole` 裡有幾筆**近 240 個交易日內**、其中幾筆**近 20 日均額 ≥ 5,000 萬**。

    ★ 市場情報分析線 2026-09-09 12:35 問的兩個數字。
    ⛔ 但**不做成一次性的回答**——他們自己說「別把『我沒看到影響』當成『沒有影響』」，
      而一次性的答案明天就過期。⇒ 放進每日輸出，哪天從 0 變成 1 會被看到。
    ⚠ 這兩個數字**是快照**：今天不流動的股票明天可能變流動。
    """
    import csv as _csv
    try:
        cal_p = os.path.join(_HERE, "data", "meta", "calendar_twse.csv")
        with io.open(cal_p, encoding="utf-8") as f:
            cal = sorted(r.split(",")[0].strip()
                         for i, r in enumerate(f) if i and r.strip())
        pos = {d: i for i, d in enumerate(cal)}
        last = len(cal) - 1
        brk_p = os.path.join(_HERE, "data", "meta", "breakpoints_unexplained.csv")
        with io.open(brk_p, encoding="utf-8") as f:
            rows = [r for r in _csv.DictReader(f)
                    if (r.get("kind") or "") == "long_hole"]
        recent = [r for r in rows
                  if r.get("event_date") in pos
                  and last - pos[r["event_date"]] <= 240]
        liq = 0
        for r in recent:
            sp = os.path.join(_HERE, "data", "stocks", r["stock_id"] + ".csv")
            if not os.path.exists(sp):
                continue
            amt = {}
            with io.open(sp, encoding="utf-8") as f:
                for x in _csv.DictReader(f):
                    try:
                        amt[x["date"]] = float(
                            (x.get("amount") or "0").replace(",", "") or 0)
                    except ValueError:
                        pass
            # ⚠ 沒成交那天記 0（與情報分析的 N₁ 定義同一條），⛔ 不跳過
            if sum(amt.get(d, 0.0) for d in cal[last - 19:last + 1]) / 20 >= 5e7:
                liq += 1
        return (f"共 {len(rows)} 筆｜斷點日在**近 240 個交易日內** {len(recent)} 筆／"
                f"{len({r['stock_id'] for r in recent})} 檔｜"
                f"其中**近 20 日均額 ≥ 5,000 萬** **{liq} 筆**"
                "（⚠ 是今天的快照，不流動的明天可能變流動）")
    except (OSError, KeyError, ValueError) as ex:                # noqa: BLE001
        return f"算不出來（{type(ex).__name__}）"


def _copy_holes():
    """把附表從回測線的產出目錄複製到 data/meta/。回傳列數；來源不在就回 None。"""
    if not os.path.exists(HOLES_SRC):
        return None
    try:
        with io.open(HOLES_SRC, encoding="utf-8") as f:
            body = f.read()
        os.makedirs(os.path.dirname(HOLES_OUT), exist_ok=True)
        with io.open(HOLES_OUT, "w", encoding="utf-8") as f:
            f.write(body)
        return max(0, body.count("\n") - 1)          # 扣掉表頭
    except OSError as ex:                                        # noqa: BLE001
        print(f"[breakpoint] 附表複製失敗：{ex}", file=sys.stderr)
        return None


def _write(txt):
    try:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with io.open(OUT, "w", encoding="utf-8") as f:
            f.write("# breakpoint_scan 的輸出（全母體斷點掃描＋與 par_change.csv 對帳）\n")
            f.write("# 規則屬回測線／K線線，這裡只是把它接進每日管線。\n")
            f.write("# 產生方式：python3 breakpoint_check.py\n\n```\n")
            f.write(txt.rstrip("\n") + "\n```\n")
    except OSError as ex:                                        # noqa: BLE001
        print(f"[breakpoint] 寫檔失敗：{ex}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
