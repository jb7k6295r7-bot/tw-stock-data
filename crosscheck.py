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


def main():
    rl = runlog.Run("crosscheck")
    rl.info("這一支在做什麼", "幫原本只有自我一致（C 級）的資料找第二個判準；"
                            "⛔ 不是證明它們正確，是**多一個獨立的人在看**")
    inst_check(rl)
    margin_check(rl)
    per_check(rl)
    exright_identity_check(rl)
    return rl.finish()


if __name__ == "__main__":
    sys.exit(main())
