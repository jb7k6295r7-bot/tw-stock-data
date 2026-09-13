#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reduce_shares_check.py — 用**我方自己的 `shares` 欄**重算官方減資參考價。
**只讀 repo，不連外。**

## ⭐⭐ 為什麼要有這一支：那個「沒有外部裁判」的結論是錯的

2026-09-13 我寫過一句：

> 上市那 303 筆減資的還原因子全是「官方參考價 ÷ 前收」回推的，
> **而它們沒有任何第二來源可以驗**。

⛔ **錯。** `data/stocks/<代號>.csv` 的 **`shares`（發行股數）**就是那個第二來源：
它來自日檔，**完全不從價格推**——⇒ 拿它算出換股比，就能**獨立**重算參考價。

```
換股比 keep = 減資日的 shares ÷ 前一個有值的交易日的 shares
減資比例 r  = 1 − keep
```

## ⛔ 而兩種減資的算式**不一樣**——這是本支最核心的一格

```
彌補虧損型   ref = 前收 ÷ keep                    ← 股東**沒有**拿到現金
現金型       ref = (前收 − 面額 10 × r) ÷ keep    ← 股東**拿回**每股 10×r 元
（現金型 ＝ `退還股款`／`現金減資`）
```

⚠ 用錯算式的後果是**系統性**的，不是隨機誤差：
2026-09-13 實測，把現金型套上彌補虧損型的算式 ⇒ 1563 差 3.34 元（3.9%）。

⭐ 而「總價值連續」這件事本身有外部佐證（TradingView 2026-09-13 實測）：

```
1563 2026-08-26  原始收盤 66.00
  TV【ADJ 開】 84.66645481   ⇒ ⭐ 跟我方 84.66 同一個量（總價值連續）
  TV【ADJ 關】 87.99978      ⇒ 66.00 × 4/3，**純股數比**、現金沒扣
```

⛔⛔ 2026-09-13 我一度把上面那第二個數字寫成「TradingView 不處理現金」——**那是錯的**。
⚠ TV **兩個量都算得出來**，差別只在圖表上那顆 `ADJ` 按鈕：

```
ADJ 關 ⇒ 股數連續（1/keep）        ⚠ 而它是**預設值會被人動到**的狀態
ADJ 開 ⇒ 總價值連續               ⇒ ⭐ 跟我方逐位相同
```

⇒ 所以「用 TV 算跨過現金型減資的報酬會多算跌幅（1563 多 3.80pp）」這句
**只在 ADJ 關閉時成立**，⛔ 不是 TV 的性質。
⚠ 而那顆按鈕的 `aria-label` 寫「調整股息數據」，實際上**連退還股款一起扣**
——⛔ 標籤會騙人，不要照名字推它管什麼。

⇒ ⭐ 我方的 `factor = ref ÷ 前收` 是總價值連續的那一個：
   `0.75 × 84.66 + 2.505 = 66.00` 逐位相符。

## 判準

`abs(算出來的 ref − 官方 ref) <= 0.05`（官方參考價印到分，容差放寬到 5 分）。
⚠ 在**價格空間**比，⛔ 不在比值空間——四捨五入在比值空間會被放大成假不符。

## ⛔ 回報「對不上 N 筆」時一定要附「對得上幾筆」（CLAUDE.md 第七點）

## ⭐⭐ `--exright`：同一套機制套到「權」族上，⛔ 而結論是「光靠 shares 不夠」

配股也改股數 ⇒ 看起來可以照抄。⛔ 而實測 72% 對不上，
⚠ **那不是 72% 的因子錯，是模型少了一式**——台灣的「除權」把兩件事綁在一起：

```
無償配股（盈餘／資本公積轉增資）  ref = 前收 ÷ (1 + 配股率)
   ⇒ 純稀釋，factor **等於**股數比
現金增資認股                      ref = (前收 + 認購價 × 認購率) ÷ (1 + 認購率)
   ⇒ 股東**要付錢** ⇒ factor **接近 1**，⛔ 而股數可以翻好幾倍
```

⭐ 跟上面減資那兩式是**同一族**：一邊拿錢、一邊付錢。
⇒ 判它是哪一種要「現增認購價與認購率」，⛔ 而我方目前沒有那兩欄
   ⇒ 本模式**只判得出**「這一筆是不是純無償配股」，⛔ 不判對錯。

⚠ ⛔ 而 `kind` 欄有**兩套詞彙**且按市場切開（上市 息/權/權息、上櫃 除息/除權/除權息）
⇒ 一律用**包含**比對（`"權" in kind`），⛔ 不可以寫 `kind == "權"`
   ——那會靜靜地只拿到上市，上櫃 2,570 筆整族掉光。
"""
import argparse
import bisect as _bisect
import collections
import csv
import io
import os
import sys

import runlog

_HERE = os.path.dirname(os.path.abspath(__file__))
ADJ = os.path.join(_HERE, "data", "adj")
STOCKS = os.path.join(_HERE, "data", "stocks")
OUT = os.path.join(_HERE, "data", "meta", "_reduce_shares_check.csv")
CASH_KINDS = ("退還股款", "現金減資")
PAR = 10.0          # 台股面額。⚠ 非 10 元面額的個股會落進「對不上」，那是刻意的
TOL = 0.05
OUT_EX = os.path.join(_HERE, "data", "meta", "_exright_shares_check.csv")
# ⭐⭐ 官方上櫃減資表的 `shares_per_1000` 是**換股比率**——⛔ 它不是從價格推的
#   ⇒ 它是繼 `shares` 之後的**第三個**來源，而且跟價格那一邊完全獨立。
#   ⚠ 這個檔由 `otc_reduce_history.py` 寫，daily.yml 裡排在本支**之前**。
OFFICIAL_TABLE = os.path.join(_HERE, "data", "meta", "otc_reduce_history.csv")
RATIO_TOL = 0.001
# ⛔⛔ 統計裡有兩種鍵：**分類**（每一筆事件剛好落一格）與**參考**（同一筆會再被數一次）。
#   混在一起 ⇒ 「對得上＋對不上＋算不了 ＝ 全部」那條不變式當場破掉
#   ——⭐ 而 2026-09-13 加第三個來源時它**當場就抓到了**（584 變成 1040）。
#   ⇒ 參考型的鍵一律加這個前綴，`tally()` 與那條不變式都把它們排除。
INFO = "（參考）"
EX_WIN = 40         # 事件日起往後找幾個交易日，等 shares 更新
EX_TOL = 0.005      # 「factor 等於股數比」的容差（比值空間，見 exright_scan）


def is_cash(kind):
    """→ 這一筆減資有沒有退還現金。⭐ 只有這一份實作。"""
    return (kind or "").strip() in CASH_KINDS


def expected_ref(pre_close, keep, cash):
    """→ 用換股比重算的官方參考價。⛔ 兩種算式不可以混用（見檔頭）。"""
    r = 1.0 - keep
    return ((pre_close - PAR * r) / keep) if cash else (pre_close / keep)


def implied_cash(pre_close, keep, ref_official):
    """→ 官方參考價**隱含**的「每股退還金額」。⛔ 只對現金型有意義。

    ⭐ 它存在的理由：`PAR * (1 - keep)` 是一個**假設**，⛔ 不是規則。
    2026-09-13 實測 248 筆現金減資，**232 筆（93.5%）**的隱含退還就是面額×比例
    （±0.02 元內），⚠ 而剩下 16 筆不是——最極端的 3356 差 2.90 元。
    ⇒ 那 16 筆的「對不上」**未必是我方 keep 錯**，可能只是公司退還的金額不同。
    ⛔ 而一條式子兩個未知數（退還金額、keep）分不開 ⇒ 這一欄是**線索，不是判決**。
    """
    return pre_close - keep * ref_official


def official_keep(pre_close, ref_official, cash):
    """→ 從官方參考價**反推**的換股比。

    ⭐ 彌補虧損型沒有現金項 ⇒ `keep = 前收 ÷ 參考價` 是**唯一解**
      ⇒ 它跟我方 shares 算出來的 keep 是**兩個來源的同一個量**，可以直接比。
    ⚠ 現金型多了「退還金額」這個未知數 ⇒ 這裡只能**沿用面額×比例的假設**反推，
      ⛔ 所以現金型的 `keep_official` 只是參考，不是第二來源。
    """
    if ref_official <= 0:
        return None
    if not cash:
        return pre_close / ref_official
    if abs(ref_official - PAR) < 1e-9:
        return None
    return (pre_close - PAR) / (ref_official - PAR)


def has_share_part(kind):
    """→ 這一筆事件有沒有「股數變動」那一半（配股／現增）。

    ⛔ **包含**比對，⛔ 不是整串相等——`kind` 有兩套詞彙且按市場切開：
      上市 `權`／`權息`　　上櫃 `除權`／`除權息`
    ⚠ 寫 `kind == "權"` 會靜靜地只拿到上市。⭐ 只有這一份實作。
    """
    return "權" in (kind or "")


def has_cash_part(kind):
    """→ 這一筆事件有沒有「現金」那一半（配息）。⭐ 只有這一份實作。"""
    return "息" in (kind or "")


def shares_series(code):
    """→ [(日期, shares)]，⭐ 只留**有值**的那些天，按日期升冪。

    ⚠ `shares` 欄上市留空、興櫃某些日子也可能空 ⇒ ⛔ 不可以拿「前一列」當「前一天」。
    ⭐ 只有這一份實作：`shares_around()` 與 `shares_after()` 都走它。
    """
    p = os.path.join(STOCKS, f"{code}.csv")
    if not os.path.exists(p):
        return []
    out = []
    for r in csv.DictReader(io.open(p, encoding="utf-8")):
        v = (r.get("shares") or "").strip()
        if not v:
            continue
        try:
            f = float(v)
        except ValueError:
            continue
        if f > 0:
            out.append((r["date"], f))
    out.sort()
    return out


def shares_after(code, day, window=EX_WIN):
    """→ (事件前的 shares, 事件後**變過**的 shares, 落後幾個交易日)；問不到回 (None, None, None)。

    ⛔ 這裡**不能**照抄 `shares_around()`：減資的股數在減資日當天就變，
    ⚠ 而配股的股數常常落後十幾個交易日才更新（實測 lag 眾數 0，但一大群落在 14~20）。
    ⇒ 所以要**往後找第一個跟事件前不同的值**，⛔ 不是讀事件日那一格。
    """
    ser = shares_series(code)
    if len(ser) < 2:
        return None, None, None
    days = [d for d, _ in ser]
    i = _bisect.bisect_left(days, day)
    if i == 0 or i >= len(ser):
        return None, None, None
    sb = ser[i - 1][1]
    for j in range(i, min(i + window, len(ser))):
        if abs(ser[j][1] - sb) / sb > 1e-9:
            return sb, ser[j][1], j - i
    return None, None, None


def exright_scan(window=EX_WIN):
    """→ (逐筆結果 list, 統計 Counter)。⛔ 只讀，不寫。

    比的是 `factor ÷ 股數比`：
      == 1  ⇒ 純無償配股（⭐ 這一筆的因子有第二來源了）
      >  1  ⇒ 股數漲得比價格掉得多 ⇒ **現增**（股東付了錢）
      <  1  ⇒ 還有現金流出（配息）⇒ 權息／除權息本來就該落在這一側
    """
    res, stat = [], collections.Counter()
    for code, r in load_events(event="exright"):
        kind = (r.get("kind") or "").strip()
        if not has_share_part(kind):
            continue
        day = r["date"]
        try:
            fac = float(r["factor"])
        except (ValueError, KeyError, TypeError):
            stat["算不了：factor 欄壞掉"] += 1
            continue
        if fac <= 0:
            stat["算不了：factor 欄壞掉"] += 1
            continue
        sb, sa, lag = shares_after(code, day, window)
        if sb is None:
            stat["算不了：問不到股數變動"] += 1
            continue
        share_f = sb / sa
        ratio = fac / share_f
        mixed = has_cash_part(kind)
        grp = "股數＋現金" if mixed else "純股數"
        if abs(ratio - 1.0) <= EX_TOL:
            tag = "＝股數比（純無償配股）"
        elif ratio > 1.0:
            tag = "＞股數比（有現增）"
        else:
            tag = "＜股數比（還有現金流出）"
        stat[f"{grp}｜{tag}"] += 1
        res.append({"stock_id": code, "date": day, "kind": kind,
                    "factor": f"{fac:.8f}", "share_factor": f"{share_f:.8f}",
                    "ratio": f"{ratio:.6f}", "lag": str(lag),
                    "shares_before": f"{sb:.0f}", "shares_after": f"{sa:.0f}"})
    return res, stat


def load_official_ratio():
    """→ {(代號, 日期): 官方換股比率}，讀不到就回空的 dict。

    ⛔ 讀不到**不可以靜靜放行**：`check_all()` 會把「有幾筆查得到官方比率」
    寫進統計 ⇒ 0 筆會直接顯示在 runlog 上（四點六：讀不到判準檔的表現是空值，不是錯誤）。
    """
    out = {}
    if not os.path.exists(OFFICIAL_TABLE):
        return out
    for r in csv.DictReader(io.open(OFFICIAL_TABLE, encoding="utf-8")):
        try:
            v = float(r.get("shares_per_1000") or "")
        except ValueError:
            continue
        if v > 0:
            out[(r.get("stock_id"), r.get("date"))] = v / 1000.0
    return out


def tally(stat):
    """→ (對得上, 對不上, 其中只差在分位, 算不了)。⭐ 只有這一份實作。

    ⛔ 「對不上（⚠ 只差在分位）」**仍然算對不上**——⛔ 不可以用 `endswith("對不上")`
    把它漏掉：那會讓「對得上 ＋ 對不上」**加不回可算的總數**，
    ⚠ 而少掉的那幾筆**不會有任何地方報**（＝把問題藏起來，四點二）。
    """
    cls = {k: v for k, v in stat.items() if not k.startswith(INFO)}
    good = sum(v for k, v in cls.items() if k.endswith("對得上"))
    bad = sum(v for k, v in cls.items() if "對不上" in k)
    near = sum(v for k, v in cls.items() if "只差在分位" in k)
    cant = sum(v for k, v in cls.items() if k.startswith("算不了"))
    return good, bad, near, cant


def load_events(event="reduce"):
    """→ [(代號, 那一列)]，只取指定的 `event`（`reduce`／`exright`）。"""
    out = []
    if not os.path.isdir(ADJ):
        return out
    for fn in sorted(os.listdir(ADJ)):
        if not fn.endswith(".csv") or fn.startswith("_"):
            continue
        for r in csv.DictReader(io.open(os.path.join(ADJ, fn), encoding="utf-8")):
            if (r.get("event") or "").strip() == event:
                out.append((fn[:-4], r))
    return out


def shares_around(code, day):
    """→ (減資日的 shares, 前一個有值交易日的 shares)；問不到就回 (None, None)。

    ⚠ 「前一個」要找**有值**的那一天，⛔ 不是前一列——`shares` 欄上市留空，
      而興櫃／某些日子也可能空。
    """
    ser = shares_series(code)          # ⭐ 讀 shares 只有這一份實作（四點五）
    days = [d for d, _ in ser]
    i = _bisect.bisect_left(days, day)
    if i == 0 or i >= len(ser) or days[i] != day:
        # ⚠ `days[i] != day` ＝ 減資日那一天**沒有** shares 值 ⇒ 算不了
        return None, None
    return ser[i][1], ser[i - 1][1]


def check_all():
    """→ (逐筆結果 list, 統計 Counter)。⛔ 只讀，不寫。"""
    res, stat = [], collections.Counter()
    ratios = load_official_ratio()
    for code, r in load_events():
        day, kind = r["date"], (r.get("kind") or "").strip()
        sa, sb = shares_around(code, day)
        try:
            pre, ref = float(r["pre_close"]), float(r["ref_price"])
        except (ValueError, KeyError, TypeError):
            stat["算不了：價格欄壞掉"] += 1
            continue
        via = "事件日"
        if sa is None or sb is None or sa >= sb or sb <= 0 or sa <= 0:
            # ⛔⛔ 讀事件日那一格會漏掉**三種**，而三種都不是資料壞掉（2026-09-13 實測）：
            #   ① 事件日**不是交易日**（5 筆：2016-09-28 ×2、2019-09-30 ×3）
            #      ⭐ 判準是「那天**全市場**沒有任何價格型 feed 的日檔」——⛔ 不是我記得
            #        那天放颱風假。⚠ 那兩天只有事件型 feed（exright／reduce）有檔，
            #        因為那一族是**按期間查**的，公告日期本來就可以落在非交易日。
            #   ② 事件日是交易日、但**該檔停牌**沒有列（1 筆：6222 2016-12-29）
            #   ③ 股數**更新落後**：實測 lag 1~19 個交易日都有（8 筆）
            # ⇒ 兩種都往後找第一個**變過**的股數。⭐ 跟除權那邊走同一支（四點五）。
            b2, a2, _lag = shares_after(code, day)
            # ⚠ 一定要**再驗一次是減少**：往後找可能撈到增資／可轉債轉換那種**增加**，
            #   ⛔ 而拿它算出來的 keep > 1 會生出一個看起來正常的假參考價。
            if b2 is None or a2 >= b2:
                stat["算不了：問不到變少的股數"] += 1
                continue
            sb, sa, via = b2, a2, "往後找"
        keep = sa / sb
        cash = is_cash(kind)
        calc = expected_ref(pre, keep, cash)
        diff = abs(calc - ref)
        tag = "現金型" if cash else "彌補虧損型"
        ok = diff <= TOL
        ko = official_keep(pre, ref, cash)
        # ⭐ 「對不上」要再分一刀：⛔ 價格空間的 5 分容差**對高價股太嚴**
        #   （6271 前收 139 元，keep 只差 0.03% 就被判成對不上）。
        #   ⇒ 換算到 **keep 空間**再看一次：差在 ±1% 內的是**印到分的差**，
        #     ⛔ 不是我方股數抓錯。⚠ 而它仍然算「對不上」，只是分開報。
        near = (not ok) and ko is not None and ko > 0 and abs(keep / ko - 1) <= 0.01
        # ⭐⭐ 第三個來源：官方公告的**換股比率**（⛔ 不是從價格推的）。
        #   它跟官方參考價是**兩欄分別公告**的 ⇒ 兩者一致就代表價格那一邊沒問題，
        #   ⇒ 這時候「對不上」的**異類是我方 `shares`**，⛔ 不是還原因子。
        kr = ratios.get((code, day))
        if kr:
            stat[INFO + "⭐ 查得到官方換股比率"] += 1
            if ko is not None and abs(kr - ko) <= RATIO_TOL:
                stat[INFO + "⭐ 官方換股比率與官方參考價一致（⇒ 價格那一邊沒問題）"] += 1
        blame_shares = (not ok and kr and ko is not None
                        and abs(kr - ko) <= RATIO_TOL
                        and abs(kr - keep) > RATIO_TOL)
        if blame_shares:
            lab = "對不上（⛔ 異類是我方 shares）"
        elif ok:
            lab = "對得上"
        elif near:
            lab = "對不上（⚠ 只差在分位）"
        else:
            lab = "對不上"
        stat[f"{tag}｜{lab}"] += 1
        res.append({"stock_id": code, "date": day, "kind": kind,
                    "keep": f"{keep:.6f}",
                    "keep_official": ("" if ko is None else f"{ko:.6f}"),
                    "pre_close": f"{pre:.2f}",
                    "ref_official": f"{ref:.2f}", "ref_calc": f"{calc:.2f}",
                    "diff": f"{diff:.4f}",
                    "cash_implied": (f"{implied_cash(pre, keep, ref):.4f}" if cash else ""),
                    "cash_par_based": (f"{PAR * (1 - keep):.4f}" if cash else ""),
                    "keep_ratio_official": (f"{kr:.6f}" if kr else ""),
                    "ok": "1" if ok else "0", "shares_via": via})
    return res, stat, ratios


def _write_csv(path, rows, fields):
    """寫完**重讀**並回傳讀回來的列數（四點二：斷言要驗終點，⛔ 不驗「寫檔成功」）。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    return len(list(csv.DictReader(io.open(path, encoding="utf-8"))))


def main_exright(write=False):
    """`--exright`：把同一套 shares 機制套到「權」族上。⛔ 它判不出對錯，見檔頭。"""
    res, stat = exright_scan()
    rl = runlog.Run("exright_shares_check")
    rl.info("⭐ 這一支在驗什麼",
            "用 `shares` 算股數比，看除權因子是不是**純無償配股**"
            "（⛔ 判不出對錯：現增那一式我方缺「認購價／認購率」兩欄）")
    for k in sorted(stat):
        rl.info(k, str(stat[k]))

    pure = stat.get("純股數｜＝股數比（純無償配股）", 0)
    over = stat.get("純股數｜＞股數比（有現增）", 0)
    under = stat.get("純股數｜＜股數比（還有現金流出）", 0)
    n_pure = pure + over + under
    rl.info("總計｜純股數族", f"可驗 {n_pure}｜＝ {pure}｜＞ {over}｜＜ {under}")

    # ⭐ 兩個方向都要有正例，⛔ 否則「某群 0 筆」讀不出意思（CLAUDE.md 第七點）
    rl.check("⭐ 純無償配股與帶現增兩群都各自抓到過（⛔ 有一群 0 筆 ＝ 那一群沒被測到）",
             pure > 0 and over > 0, f"純無償 {pure} 筆、帶現增 {over} 筆")

    # ⭐ 這條釘的是**單邊性**：現增只會把 factor 推到股數比**之上**。
    #   ⛔ 若兩邊差不多，代表那個偏差是雜訊，本節的解釋就不成立。
    rl.check("⭐ 偏差是單邊的（現增 ⇒ factor > 股數比），⛔ 不是隨機誤差",
             over > 0 and under * 5 < over, f"＞ {over} 筆　vs　＜ {under} 筆")

    # 權息／除權息：factor ÷ 股數比 = 1 − 配息÷前收 ⇒ 中位數就是隱含殖利率
    mixed = [float(x["ratio"]) for x in res if has_cash_part(x["kind"])]
    if mixed:
        mixed.sort()
        med = mixed[len(mixed) // 2]
        rl.check("⭐ 權息族的「factor ÷ 股數比」＝ 1 − 隱含殖利率，落在台股合理區間",
                 0.90 <= med <= 1.00,
                 f"{len(mixed)} 筆，中位 {med:.4f} ⇒ 隱含殖利率 {(1 - med) * 100:.2f}%")

    if write:
        fields = ["stock_id", "date", "kind", "factor", "share_factor",
                  "ratio", "lag", "shares_before", "shares_after"]
        back = _write_csv(OUT_EX, sorted(res, key=lambda x: x["date"]), fields)
        rl.check("逐筆結果寫得進去而且讀得回來",
                 back == len(res), f"寫 {len(res)} 列、讀回 {back} 列")
    return rl.finish()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="把逐筆結果寫成 CSV")
    ap.add_argument("--exright", action="store_true",
                    help="改跑「權」族（⛔ 判不出對錯，只判是不是純無償配股）")
    a = ap.parse_args()
    if a.exright:
        return main_exright(a.write)
    res, stat, ratios = check_all()
    rl = runlog.Run("reduce_shares_check")

    good, bad, near, cant = tally(stat)
    rl.info("⭐ 這一支在驗什麼",
            "用**我方自己的 `shares` 欄**算換股比，重算官方減資參考價"
            "（⛔ 不連外、不靠人工匯出的表）")
    for k in sorted(stat):
        rl.info(k, str(stat[k]))
    # ⛔ 「對不上 N 筆」一定要跟「對得上幾筆」放在一起（CLAUDE.md 第七點）
    rl.info("總計", f"對得上 {good}｜對不上 {bad}（其中 {near} 筆只差在分位）｜算不了 {cant}")
    # ⭐ 加不回去就是有一群掉在外面（⛔ 而那一群不會有任何地方報）
    # ⭐ 這一條**故意**用另一種數法（`sum(stat.values())`）當右邊：
    #   ⛔ 兩邊都用 `tally()` 的話它永遠成立，那就不是斷言而是恆等式。
    rl.check("⭐ 對得上 ＋ 對不上 ＋ 算不了 ＝ 全部（⛔ 沒有任何一筆掉在外面）",
             good + bad + cant == sum(v for k, v in stat.items()
                                      if not k.startswith(INFO)),
             f"{good} + {bad} + {cant} vs "
             f"{sum(v for k, v in stat.items() if not k.startswith(INFO))}")

    # ⭐ 兩種算式**都要有正例**。⛔ 只有一種有，代表另一種其實沒被測到
    #   ——而那正是「某群 0 筆」那個陷阱。
    cash_ok = stat.get("現金型｜對得上", 0)
    loss_ok = stat.get("彌補虧損型｜對得上", 0)
    rl.check("⭐ 兩種算式都各自對上過（⛔ 只有一種有正例 ＝ 另一種沒被測到）",
             cash_ok > 0 and loss_ok > 0,
             f"現金型 {cash_ok} 筆、彌補虧損型 {loss_ok} 筆")
    # ⭐ 第三個來源的兩條斷言。⛔ 第一條擋的是「判準檔讀不到 ⇒ 整欄空白」（四點六）
    have = stat.get(INFO + "⭐ 查得到官方換股比率", 0)
    agree = stat.get(INFO + "⭐ 官方換股比率與官方參考價一致（⇒ 價格那一邊沒問題）", 0)
    rl.check("⭐ 官方換股比率那張表**讀得到而且有內容**（⛔ 讀不到的表現是空值，不是錯誤）",
             have > 0, f"查得到 {have} 筆｜表 {len(ratios)} 列"
                       f"｜{os.path.relpath(OFFICIAL_TABLE, _HERE)}")
    rl.check("⭐ 官方的【換股比率】與【參考價】互相一致（⛔ 掉下來代表來源那張表變了）",
             have > 0 and agree / have >= 0.90, f"{agree}/{have}")
    rl.check("九成以上的減資參考價重算得出來",
             good + bad > 0 and good / (good + bad) >= 0.90,
             f"{good}/{good + bad}"
             + (f"　⚠ 對不上的逐筆在 {os.path.relpath(OUT, _HERE)}" if bad else ""))

    if a.write:
        back = _write_csv(OUT,
                          sorted((x for x in res if x["ok"] == "0"),
                                 key=lambda x: -float(x["diff"])),
                          list(res[0]) if res else
                          ["stock_id", "date", "kind", "keep", "keep_official",
                           "keep_ratio_official", "pre_close", "ref_official",
                           "ref_calc", "diff", "cash_implied", "cash_par_based",
                           "ok", "shares_via"])
        rl.check("對不上的清單寫得進去而且讀得回來",
                 back == bad, f"寫 {bad} 列、讀回 {back} 列")
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
