#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""crosscheck.py — 幫三份「只有自我一致」的資料找到第二個判準。**只讀 repo。**

2026-09-09 的稽核把三份資料標成 **C 級（只有自我一致）**：三大法人、融資融券、本益比。
C 級最危險的地方是它**最像 A 級**——報表一樣綠，差別只在「拿什麼來比」。

這一支找到並實作了三個判準。⛔ 每一個都要說得出**為什麼它算獨立**：

## ① 三大法人：Σ(逐檔股數 × 收盤) vs 大盤合計金額

逐檔來自 `T86`、大盤合計來自另一個彙總、收盤價來自日檔——**三個不同的檔**。
⚠ 但它只是近似：官方的買賣超金額用的是**成交價**，我方用收盤價。
⛔ **而且分母接近 0 時比值無意義**（2026-09-08 大盤只有 −125 億，比值就掉到 0.78）
⇒ 所以只在 **|大盤合計| ≥ 300 億**時判定，其餘只報不判。
   ⛔ 這不是為了讓它好看，是因為「比值」在分母趨近 0 時本來就不是有效的統計量。

## ② 融資融券：餘額的遞推恆等式

    餘額(t) ?= 餘額(t−1) + 融資買進 − 融資賣出

⚠ 不會完全相等——**現金償還**會減少餘額卻不出現在買賣裡。
實測正常日約 **75% 完全相等**，殘差多是小額負值，方向與「現償」一致。

⭐ **這個判準最有價值的地方不是那 75%，是它會自己抓到缺漏**：
2026-09-08 的相等率掉到 **18.7%**，原因是前一個檔是 09-04——**09-07 那天沒抓到**。
⇒ 一個跨日的恆等式，**同時驗數字也驗涵蓋率**。

## ③ 本益比：收盤 ÷ 近四季 EPS vs 端點的 `per`

EPS 來自 MOPS 財報（累計值相減還原單季，取最近四季），`per` 來自 `BWIBBU_d`
——**兩個不同的發布管道**。實測 855 檔可比、**中位誤差 0.21%**、89.1% 落在 5% 內。

## ⭐⭐ ④ 除權息：官方**自己寫出來的**恆等式

`TWT49U` 的 notes 有一句：**「權值+息值 ＝ 除權息前收盤價 − 除權息參考價」**。

⇒ ⭐ 這是**官方講的**，⛔ 不是我推的 ⇒ 它是這一族裡最硬的一個判準：
三個欄位任何一個被撿錯（`_pick` 那一族的錯法），這條**當場就不成立**。

⚠ 容差要 **0.011 不是 0.005**：兩個價各自捨入到「分」，誤差可以各 0.005
⇒ 差值的誤差上限是 0.01。⛔ 用 0.005 的話 16.6% 會誤報
（實測：±0.005 是 83.43%、±0.011 是 **11,751/11,751 ＝ 100.000%**）。

⭐ 而它同時是**涵蓋率**的判準：這三欄有一欄整批空掉，`n` 就會掉下來
——⛔ 而「0 列可比」跟「全部通過」在報表上長得一樣，所以下面會先釘母體。

⛔ 四個都**不是**「證明資料正確」，是「**多一個獨立的人在看**」。
   C 級升 B 級靠的是這個，不是通過率變高。
"""
import csv
import glob
import io
import os
import statistics
import sys

import runlog

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
EPS_KEY = "基本每股盈餘（元）"
INST_MIN = 30_000_000_000.0        # 300 億：低於此不判（見檔頭）


def _f(v):
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def inst_check(rl):
    p = os.path.join(_ROOT, "history", "market_inst.csv")
    if not os.path.exists(p):
        rl.info("① 三大法人", "⚠ 沒有 market_inst.csv，跳過")
        return
    with io.open(p, encoding="utf-8") as f:
        mk = {r["date"]: r for r in csv.DictReader(f)}
    rows, skipped = [], 0
    for d in sorted(mk):
        fi = os.path.join(_ROOT, "universe", "inst", d + ".csv")
        fd = os.path.join(_ROOT, "universe", "daily", d + ".csv")
        if not (os.path.exists(fi) and os.path.exists(fd)):
            continue
        px = {}
        with io.open(fd, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                v = _f(r.get("close"))
                if v:
                    px[r["stock_id"]] = v
        s = 0.0
        with io.open(fi, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                v = _f(r.get("total"))
                pp = px.get(r.get("stock_id"))
                if v is not None and pp:
                    s += v * pp
        t = _f(mk[d].get("total"))
        if not t:
            continue
        if abs(t) < INST_MIN:
            skipped += 1
            rl.info(f"   {d}", f"|大盤| {abs(t) / 1e8:,.0f} 億 < 300 億"
                               f"⇒ **只報不判**（比值 {s / t:.4f}）")
            continue
        rows.append((d, s / t))
    if not rows:
        rl.info("① 三大法人", f"可判定 0 天（只報不判 {skipped} 天）")
        return
    rs = [x[1] for x in rows]
    worst = max(rows, key=lambda x: abs(x[1] - 1))
    rl.info("① 三大法人 Σ(股數×收盤) vs 大盤合計",
            f"可判定 {len(rows)} 天（另有 {skipped} 天因分母太小只報不判）"
            f"｜比值 min {min(rs):.4f}／中位 {statistics.median(rs):.4f}／max {max(rs):.4f}"
            f"｜最偏 {worst[0]} {worst[1]:.4f}")
    bad = [x for x in rows if not 0.90 <= x[1] <= 1.10]
    # ⛔ 門檻要附「觸發幾次」與「最接近距離」（情報分析 2026-09-09 的規矩）
    near = min(abs(x[1] - 1) for x in rows) if rows else 0
    rl.check("三大法人逐檔加總與大盤合計相符（±10%，僅判 |大盤| ≥ 300 億的日子）",
             not bad,
             f"{len(bad)} 天不符：{[(d, round(r, 4)) for d, r in bad[:3]]}"
             f"｜⚠ 最偏 {max(abs(x[1] - 1) for x in rows):.4f}、最接近 {near:.4f}")


def margin_check(rl):
    ds = sorted(os.path.basename(x)[:-4]
                for x in glob.glob(os.path.join(_ROOT, "universe", "margin",
                                                "*.csv")))[-10:]
    prev, out = None, []
    for d in ds:
        cur = {}
        with io.open(os.path.join(_ROOT, "universe", "margin", d + ".csv"),
                     encoding="utf-8") as f:
            for r in csv.DictReader(f):
                b, bu, se = (_f(r.get("m_balance")), _f(r.get("m_buy")),
                             _f(r.get("m_sell")))
                if None not in (b, bu, se):
                    cur[r["stock_id"]] = (b, bu, se)
        if prev:
            tot = ok = 0
            for sid, (b, bu, se) in cur.items():
                p = prev.get(sid)
                if not p:
                    continue
                tot += 1
                if b == p[0] + bu - se:
                    ok += 1
            if tot:
                out.append((d, ok / tot * 100, tot))
        prev = cur
    if not out:
        rl.info("② 融資融券", "⚠ 資料不足")
        return
    rl.info("② 融資融券 餘額遞推恆等式",
            "｜".join(f"{d} {p:.1f}%" for d, p, _ in out[-5:])
            + "（完全相等的比例；殘差多為小額負值＝現金償還）")
    low = [x for x in out if x[1] < 50]
    # ⛔ 這一條**同時**在驗數字與涵蓋率：相等率崩掉最常見的原因是「前一天沒抓到」。
    rl.check("融資餘額遞推的相等率沒有崩掉（≥50%）", not low,
             f"{[(d, round(p, 1)) for d, p, _ in low]}"
             "｜⚠ 崩掉最常見的原因是**前一個交易日的檔案不存在**，先查涵蓋率")


def per_check(rl):
    eps = {}
    for f in (glob.glob(os.path.join(_ROOT, "mops", "fs_hist", "*.csv"))
              + glob.glob(os.path.join(_ROOT, "mops", "fs", "*.csv"))):
        q = os.path.basename(f).split("_")[0]
        try:
            with io.open(f, encoding="utf-8") as fh:
                rd = csv.DictReader(fh)
                if EPS_KEY not in (rd.fieldnames or []):
                    continue
                for r in rd:
                    s = (r.get("stock_id") or "").strip()
                    v = _f(r.get(EPS_KEY))
                    if s and v is not None:
                        eps[(s, q)] = v
        except OSError:
            continue
    pfs = sorted(glob.glob(os.path.join(_ROOT, "universe", "per", "*.csv")))
    if not pfs or not eps:
        rl.info("③ 本益比", "⚠ 資料不足")
        return
    d = os.path.basename(pfs[-1])[:-4]

    def single(sid, y, n):
        c = eps.get((sid, f"{y}Q{n}"))
        if c is None:
            return None
        if n == 1:
            return c
        p = eps.get((sid, f"{y}Q{n - 1}"))
        return None if p is None else c - p

    ok = bad = skip = 0
    diffs = []
    with io.open(pfs[-1], encoding="utf-8") as f:
        for r in csv.DictReader(f):
            per, close = _f(r.get("per")), _f(r.get("close"))
            fq = (r.get("fs_quarter") or "").strip()
            if not (per and close and per > 0 and "/" in fq):
                skip += 1
                continue
            try:
                y, n = fq.split("/")
                y, n = int(y) + 1911, int(n)
            except ValueError:
                skip += 1
                continue
            vals, yy, nn = [], y, n
            for _ in range(4):
                vals.append(single(r["stock_id"], yy, nn))
                nn -= 1
                if nn == 0:
                    yy, nn = yy - 1, 4
            if any(v is None for v in vals) or sum(vals) <= 0:
                skip += 1
                continue
            e = abs(close / sum(vals) - per) / per
            diffs.append(e)
            ok += e < 0.05
            bad += e >= 0.05
    if not diffs:
        rl.info("③ 本益比", "⚠ 沒有可比的檔")
        return
    diffs.sort()
    rl.info("③ 本益比 收盤÷近四季EPS vs 端點 per",
            f"{d}｜可比 {ok + bad} 檔｜誤差 <5% 的 {ok}（{ok / (ok + bad) * 100:.1f}%）"
            f"｜中位 {statistics.median(diffs) * 100:.2f}%"
            f"｜p90 {diffs[int(len(diffs) * 0.9)] * 100:.2f}%｜算不出來 {skip}")
    rl.check("本益比與 MOPS 的 EPS 對得起來（中位誤差 < 2%）",
             statistics.median(diffs) < 0.02,
             f"中位 {statistics.median(diffs) * 100:.2f}%"
             "｜⚠ 這是兩個發布管道的比對，⛔ 不是同一份資料自己比自己")


def exright_identity_check(rl, tol=0.011):
    """④ 除權息：`權值+息值 ＝ 前收 − 參考價`（**官方 notes 自己寫的**）。

    ⛔ `tol` 的預設 0.011 是**算出來的**，不是調出來的：兩個價各自捨入到分
    ⇒ 差值誤差上限 0.01。⚠ 調小它會讓這道閘門天天紅，然後被學會忽略。
    """
    d = os.path.join(_ROOT, "universe", "exright")
    if not os.path.isdir(d):
        rl.info("④ 除權息恆等式", "⚠ 沒有 data/universe/exright，跳過")
        return
    n = ok = 0
    worst = (0.0, "")
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".csv") or fn.startswith("_"):
            continue
        with io.open(os.path.join(d, fn), encoding="utf-8") as f:
            for r in csv.DictReader(f):
                pre, ref = _f(r.get("pre_close")), _f(r.get("ref_price"))
                val = _f(r.get("value"))
                if pre is None or ref is None or val is None:
                    continue
                n += 1
                dv = abs((pre - ref) - val)
                if dv <= tol:
                    ok += 1
                elif dv > worst[0]:
                    worst = (dv, f"{r.get('date')} {r.get('stock_id')}"
                                 f"｜前收 {pre}｜參考 {ref}｜權息值 {val}")
    if not n:
        rl.info("④ 除權息恆等式", "⚠ 一列都讀不到")
        return
    rl.info("④ 除權息 權值+息值 ＝ 前收 − 參考價（官方 notes 自己寫的）",
            f"可比 {n:,} 列｜相符 {ok:,}（{ok / n * 100:.3f}%）"
            + (f"｜⛔ 最差：{worst[1]}（差 {worst[0]:.4f}）" if worst[1] else ""))
    # ⭐ 先釘母體：⛔「0 列可比」跟「全部通過」在報表上長得一樣
    rl.check("④ 這道閘門真的有母體可掃（⛔ 0 列跟全部通過長得一樣）",
             n >= 5000, f"{n:,} 列")
    rl.check(f"④ 官方恆等式全數成立（容差 {tol}＝兩個價各自捨入到分）",
             ok == n, f"{ok:,}/{n:,}")


def dealer_identity(root=None):
    """自營商分項恆等式：`自行買賣 + 避險 == 自營商合計`。

    → (可驗列數, [(日期, 代號, self, hedge, dealer), ...] 不符的)。

    ## ⛔ 這一條的**適用範圍**要先講清楚

    三個欄**來自同一發回應**（T86／TPEx）⇒ ⚠ 它**不是**「獨立的第二個來源」，
    ⛔ 不可以拿它宣稱「官方那三個數字是對的」。
    ⭐ 它抓得到的是**我方這一端**的錯：欄位對錯位、解析抓錯欄、
      回補與每日兩條路寫出不同語意的欄（四點五那一族）。
    ⚠ 而那正是 CLAUDE.md 四點二③「**欄位有值 ≠ 值是對的**」要防的事
      ——`dealer_self` 整欄填成別的數字，**沒有任何現有閘門看得出來**。

    ## ⭐ 為什麼判準是「一列都不准不符」

    2026-09-14 上市那 2,851 天回補完之後**全庫實測**：

        可驗 4,811,538 列（上市＋上櫃、2015~2026）｜⛔ 不符 **0** 列

    ⇒ 它是一條**會回到 0** 的量（`lowwater.py` 檔頭那條）⇒ 絕對門檻是對的，
    ⛔ 不必也不應該用低水位——那會讓第一筆錯位被默默接受。
    """
    base = os.path.join(root or _ROOT, "universe")
    tot, bad = 0, []
    for d in ("inst", "otcinst"):
        for path in sorted(glob.glob(os.path.join(base, d, "*.csv"))):
            try:
                with io.open(path, encoding="utf-8") as f:
                    rd = csv.DictReader(f)
                    if not rd.fieldnames or "dealer_self" not in rd.fieldnames:
                        continue
                    day = os.path.basename(path)[:-4]
                    for r in rd:
                        try:
                            sv = int(r["dealer_self"])
                            hv = int(r["dealer_hedge"])
                            dv = int(r["dealer"])
                        except (ValueError, KeyError, TypeError):
                            continue        # ⚠ 空欄不算不符（舊檔還沒回補）
                        tot += 1
                        if sv + hv != dv:
                            bad.append((day, r.get("stock_id"), sv, hv, dv))
            except OSError:
                continue
    return tot, bad


def dealer_check(rl):
    tot, bad = dealer_identity()
    rl.info("⑤ 自營商分項恆等式　自行買賣 ＋ 避險 ＝ 自營商合計",
            f"可驗 {tot:,} 列（上市＋上櫃）｜不符 {len(bad):,}"
            + (f"｜⛔ 前 3：{bad[:3]}" if bad else "")
            + "　⚠ 三個欄來自**同一發回應** ⇒ ⛔ 它驗的是**我方有沒有對錯位**，"
              "不是官方的數字對不對")
    # ⭐ 先釘母體：⛔「0 列可驗」跟「全部通過」在報表上長得一樣
    rl.check("⑤ 這道閘門真的有母體可掃（⛔ 0 列跟全部通過長得一樣）",
             tot >= 1_000_000, f"{tot:,} 列")
    rl.check("⑤ 自營商分項恆等式全數成立（⛔ 一列都不准不符）",
             not bad,
             f"⛔ **{len(bad):,} 列不符**：{bad[:3]}" if bad
             else f"{tot:,} 列全過")


def tdcc_seam(root=None):
    """集保**兩層重疊的那幾週**要逐格相同。→ `(重疊週數, 可比格數, [不符…])`。

    ## ⛔ 這道閘門要擋的事：**兩層是重疊的，而重疊處沒有人在比**

    集保現在有兩層，⚠ 而它們**不是接續的，是重疊的**：

        data/tdcc/<資料日>.csv      `tdcc.py` 每週寫一份，**往後累積**
        data/tdcc_hist/<年>.parquet 2019-06-28 ~ 2026-09-11，**凍結不再改**

    ⇒ 2026-09-04 與 2026-09-11 **兩層都有**（實測 137,802 格逐格相同）。
    ⛔ 所以讀的人取聯集時一定要照 `date` 去重，⚠ 否則那兩週會被**算兩次**。

    ## ⭐ 而這道閘門比「去重」更前面一步

    重疊處若哪天**對不上**，代表兩件事之一：
    ① 那批封存有問題，或 ② `tdcc.py` 的解析改過而 parquet 沒跟上（四點五那一族）
    ⇒ 兩種都要人看，⛔ 不可以自動挑一邊。

    ⚠ 而母體是**結構性穩定**的（parquet 凍結、csv 只往後長）⇒ 重疊永遠是那幾週
    ⇒ 母體變 0 就代表有人動了不該動的東西 ⇒ 那也要紅。
    """
    base = root or _ROOT
    try:
        import pyarrow.parquet as pq
    except ImportError as ex:                                # noqa: BLE001
        return None, f"⚠ 這台沒有 {ex.name}"
    # ⛔ 第一版把 8 個年檔（2,061 萬列）整份讀進 dict ⇒ 120 秒還沒跑完。
    #   ⭐ 而要比的只有 `data/tdcc/` 那幾週 ⇒ **先看 csv 有哪幾天**，
    #     只讀那幾年、而且只留那幾天的列。
    csvs = sorted(glob.glob(os.path.join(base, "tdcc", "*.csv")))
    want = {os.path.basename(p)[:-4] for p in csvs}
    years = {d[:4] for d in want}
    par = {}
    for f in sorted(glob.glob(os.path.join(base, "tdcc_hist", "*.parquet"))):
        if os.path.basename(f)[:-8] not in years:
            continue
        t = pq.read_table(f).to_pydict()
        for i in range(len(t["date"])):
            if t["date"][i] not in want:
                continue
            par[(t["date"][i], t["stock_id"][i], int(t["level"][i]))] = (
                int(t["people"][i]), int(t["shares"][i]), round(float(t["pct"][i]), 4))
    if not par:
        return (0, 0, []), ("⛔ 沒有 tdcc_hist/*.parquet"
                            if not glob.glob(os.path.join(base, "tdcc_hist", "*"))
                            else "⚠ 兩層目前**沒有重疊的週**")
    weeks, cells, bad = set(), 0, []
    for p in csvs:
        for r in csv.DictReader(io.open(p, encoding="utf-8")):
            try:
                k = (r["date"], r["stock_id"], int(r["level"]))
                mine = (int(r["people"]), int(r["shares"]),
                        round(float(r["pct"]), 4))
            except (KeyError, ValueError, TypeError):
                continue
            if k not in par:
                continue                # ⚠ 不重疊的週不算不符（csv 往後長是正常的）
            weeks.add(r["date"])
            cells += 1
            if mine != par[k]:
                bad.append((k, mine, par[k]))
    return (len(weeks), cells, bad), ""


def tdcc_check(rl):
    got, note = tdcc_seam()
    if got is None:
        # ⭐ 寫成不會被讀成「驗過了」的樣子（六點五）
        rl.info("⚠⚠ **這一層沒跑**", f"⑥ 集保兩層重疊比對：{note}"
                                      "　⇒ ⛔ 不算失敗，⛔ **也不算驗過**")
        return
    weeks, cells, bad = got
    rl.info("⑥ 集保兩層**重疊**的週要逐格相同",
            f"重疊 {weeks} 週｜可比 {cells:,} 格｜不符 {len(bad):,}"
            + (f"｜⛔ 前 3：{bad[:3]}" if bad else "")
            + "　⚠ 兩層是**重疊**不是接續 ⇒ ⛔ 讀的人取聯集要照 `date` 去重")
    # ⭐ 先釘母體：⛔「0 格可比」跟「全部通過」在報表上長得一樣
    #   ⚠ 而這裡的母體是**結構性穩定**的（parquet 凍結、csv 只往後長）
    #   ⇒ 它變 0 就代表有人動了 `data/tdcc/` 或 `data/tdcc_hist/`，那也要紅。
    rl.check("⑥ 兩層真的還有重疊可比（⛔ 0 格跟全部通過長得一樣）",
             cells > 0, f"{weeks} 週／{cells:,} 格{note and '｜' + note}")
    rl.check("⑥ 重疊的那幾週**逐格相同**（⛔ 一格都不准不同）",
             not bad,
             f"⛔ **{len(bad):,} 格不同**：{bad[:3]}" if bad
             else f"{cells:,} 格全過")


def main():
    rl = runlog.Run("crosscheck")
    rl.info("這一支在做什麼", "幫原本只有自我一致（C 級）的資料找第二個判準；"
                            "⛔ 不是證明它們正確，是**多一個獨立的人在看**")
    inst_check(rl)
    margin_check(rl)
    per_check(rl)
    dealer_check(rl)
    tdcc_check(rl)
    exright_identity_check(rl)
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
