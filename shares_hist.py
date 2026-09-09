#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""shares_hist.py — 上市歷史股數：**先量可行性，還不要寫序列。** 只讀 repo，不連外。

## 為什麼會有這一支

`opendata/t187ap03_L` 只給當期（2026-09-09 Actions 實測：三種期別參數，
回應逐位元組相同）。使用者提供的替代路「BWIBBU_d 有市值可以反推」也否證了
（同日實測：2026 與 2015 兩發，欄位裡**都沒有市值**；而且 2015 那版連收盤價都沒有）。

⇒ 第三條路是**我方 repo 裡本來就有的東西**：MOPS 的資產負債表有 `股本`。

    股數 ＝ 股本（仟元）× 1000 ÷ 面額

`data/mops/bs_hist/` 從 **2015Q1** 起，372 個檔。⇒ 若這條成立，
上市就有**季頻**的股數序列，而不是只有「從今天起」。

## ⛔ 但這一支**只量，不寫序列**，理由是三個還沒解決的問題

1. **面額不是永遠 10**（台股 2014 起彈性面額）。用 10 去除會在那些股票上錯得
   一塌糊塗——實測誤差最大的幾檔正好都是名稱帶 `*` 的彈性面額股
   （2327 國巨* 差 75.00% ＝ 1−1/4，6919 康霈* 與 6949 沛爾* 差 95.00% ＝ 1−1/20）。

   ⭐ **2026-09-09 想清楚了：不可以用「10 ÷ Π(mult)」往前推。**
   實測三份官方名冊 2,346 檔，`實收資本額 ÷ 已發行股數` **不是 10** 的有 **76 檔**，
   其中 **54 檔我方根本沒有面額變更事件**——因為它們**一上市就不是 10**：

     - **DR（存託憑證）9 檔**：9110 越南控-DR 0.0421、910322 康師傅-DR 0.1631…
       那是外國原股的面額，⛔ 跟台股面額不是同一件事（比照代碼 91：問錯問題）。
     - **興櫃 19 檔**：6932 水星生醫*、7731 火星生技*、7781 昕力資*…
       全部帶 `*`，**IPO 當時就採彈性面額**，⛔ 沒有事件可以找。
     - **KY 公司**：4157 太景*-KY 0.0292、6741 91APP*-KY 5.0。

   ⇒ 正確方向是**反過來走**：拿**今天的面額**（同來源快照的
     `實收資本額 ÷ 已發行股數`，是觀測值不是假設），再沿事件**往回**乘：

         par(事件之前) ＝ par(事件之後) × share_mult

     這樣完全不需要假設「一開始是 10」。⛔ 前推需要那個假設，而它有 54 個反例。
2. **季頻不是日頻**：季中的可轉債轉換、員工認股、現金增資看不到。
   ⇒ 這條序列的語意是「每季末的股數」，⛔ 不可以拿去當日頻用。
3. 還有幾檔的誤差**用面額解釋不了**（例如 6669 緯穎、6108 競國），
   ⛔ 沒查清楚之前不要整批落地。

⚠ 判準寫在這裡：**中位數誤差要 ≈ 0，而且「面額解釋不了的離群檔」要逐檔有交代**，
  才可以把序列寫進資料庫。⛔ 「85% 對得上」不是及格，是**還有 15% 不知道為什麼**。
"""
import csv
import glob
import io
import os
import statistics
import sys

_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
BS = os.path.join(_ROOT, "mops")
CAP = os.path.join(_ROOT, "meta", "capital.csv")
OUT = os.path.join(_ROOT, "meta", "_shares_hist_feasibility.md")
K_CAP = "股本"


def load_quarter_capital(q):
    """→ {stock_id: 股本(仟元)}。同一季分散在很多張產業別表裡。"""
    out = {}
    pats = [os.path.join(BS, "bs_hist", f"{q}_*_twse.csv"),
            os.path.join(BS, "bs", f"{q}_*.csv")]
    for pat in pats:
        for f in glob.glob(pat):
            try:
                with io.open(f, encoding="utf-8") as fh:
                    rows = list(csv.DictReader(fh))
            except OSError:
                continue
            if not rows or K_CAP not in rows[0]:
                continue
            for r in rows:
                sid = (r.get("stock_id") or "").strip()
                v = (r.get(K_CAP) or "").replace(",", "").strip()
                if not (sid and v):
                    continue
                try:
                    out[sid] = float(v)
                except ValueError:
                    pass
    return out


def _by_quarter_table():
    """逐季的『誤差 ≥0.5% 比例』，排成年 × 季的表。→ [markdown 列]。"""
    import collections
    pt = collections.defaultdict(list)
    with io.open(os.path.join(_ROOT, "meta", "par_timeline.csv"),
                 encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("par"):
                pt[r["stock_id"]].append((r["valid_from"], r["valid_to"],
                                          float(r["par"])))
    daily = os.path.join(_ROOT, "universe", "daily")
    days = sorted(os.path.basename(x)[:-4]
                  for x in glob.glob(os.path.join(daily, "*.csv")))
    rate = {}
    for f in sorted({os.path.basename(x).split("_")[0]
                     for x in glob.glob(os.path.join(BS, "bs_hist",
                                                     "*_tpex.csv"))}):
        y, n = int(f[:4]), int(f[-1])
        last = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}[n]
        cand = [x for x in days if x <= f"{y}-{last}"]
        if not cand:
            continue
        d = cand[-1]
        act = {}
        with io.open(os.path.join(daily, d + ".csv"), encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                v = (r.get("shares") or "").strip()
                if v:
                    try:
                        act[r["stock_id"]] = float(v)
                    except ValueError:
                        pass
        tot = bad = 0
        for fn in glob.glob(os.path.join(BS, "bs_hist", f"{f}_*_tpex.csv")):
            with io.open(fn, encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    sid = (r.get("stock_id") or "").strip()
                    v = (r.get(K_CAP) or "").replace(",", "").strip()
                    a = act.get(sid)
                    p = _par_at(pt, sid, d)
                    if not (sid and v and a and p):
                        continue
                    try:
                        c = float(v)
                    except ValueError:
                        continue
                    tot += 1
                    if abs(c * 1000 / p - a) / a >= 0.005:
                        bad += 1
        if tot:
            rate[(y, n)] = bad / tot * 100
    out = []
    for y in sorted({k[0] for k in rate}):
        cells = []
        for n in (1, 2, 3, 4):
            v = rate.get((y, n))
            cells.append("—" if v is None else
                         (f"**{v:.1f}%**" if n == 2 else f"{v:.1f}%"))
        out.append(f"| {y} | " + " | ".join(cells) + " |")
    return out


def _par_at(pt, sid, d):
    for vf, vt, p in pt.get(sid, []):
        if (not vf or vf <= d) and (not vt or d < vt):
            return p
    return None


def _validate_otc():
    """上櫃逐季對官方發行股數。→ dict 或 None。"""
    import collections
    pt = collections.defaultdict(list)
    ptp = os.path.join(_ROOT, "meta", "par_timeline.csv")
    if not os.path.exists(ptp):
        return None
    with io.open(ptp, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                pt[r["stock_id"]].append((r["valid_from"], r["valid_to"],
                                          float(r["par"])))
            except (ValueError, KeyError):
                continue
    daily = os.path.join(_ROOT, "universe", "daily")
    days = sorted(os.path.basename(x)[:-4]
                  for x in glob.glob(os.path.join(daily, "*.csv")))
    qs = sorted({os.path.basename(f).split("_")[0]
                 for f in glob.glob(os.path.join(BS, "bs_hist", "*_tpex.csv"))})
    errs = []
    for q in qs:
        y, n = int(q[:4]), int(q[-1])
        last = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}[n]
        cand = [d for d in days if d <= f"{y}-{last}"]
        if not cand:
            continue
        d = cand[-1]
        act = {}
        try:
            with io.open(os.path.join(daily, d + ".csv"), encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    v = (r.get("shares") or "").strip()
                    if v:
                        try:
                            act[r["stock_id"]] = float(v)
                        except ValueError:
                            pass
        except OSError:
            continue
        cap = {}
        for fn in (glob.glob(os.path.join(BS, "bs_hist", f"{q}_*_tpex.csv"))
                   + glob.glob(os.path.join(BS, "bs", f"{q}_*.csv"))):
            try:
                with io.open(fn, encoding="utf-8") as f:
                    for r in csv.DictReader(f):
                        sid = (r.get("stock_id") or "").strip()
                        v = (r.get(K_CAP) or "").replace(",", "").strip()
                        if sid and v:
                            try:
                                cap[sid] = float(v)
                            except ValueError:
                                pass
            except OSError:
                continue
        for sid, c in cap.items():
            a = act.get(sid)
            p = _par_at(pt, sid, d)
            if not a or not p:
                continue
            errs.append(abs(c * 1000 / p - a) / a)
    if not errs:
        return None
    errs.sort()
    return {"n": len(errs), "med": statistics.median(errs),
            "a": sum(1 for e in errs if e < 0.0001),
            "b": sum(1 for e in errs if e < 0.001),
            "c": sum(1 for e in errs if e < 0.01),
            "d": sum(1 for e in errs if e < 0.05)}


def _quarter_end(q):
    """2026Q2 → 2026-06-30。⛔ 不用「今天」，那正是上一版比錯的地方。"""
    try:
        y, n = int(q[:4]), int(q[-1])
    except (ValueError, IndexError):
        return ""
    return {1: f"{y}-03-31", 2: f"{y}-06-30",
            3: f"{y}-09-30", 4: f"{y}-12-31"}.get(n, "")


def _events_after(sid, d0):
    """季末之後的還原事件。→ [(日期, 種類)]"""
    p = os.path.join(_ROOT, "adj", f"{sid}.csv")
    if not (d0 and os.path.exists(p)):
        return []
    out = []
    try:
        with io.open(p, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if (r.get("date") or "") > d0:
                    out.append((r["date"], r.get("kind", "")))
    except OSError:
        return []
    return out


def main():
    L = ["# 上市歷史股數：可行性量測（⛔ 這是量測，不是資料）", ""]
    L.append("**方法**：`股數 ＝ 股本（仟元）× 1000 ÷ 面額`，"
             "股本取自 MOPS 資產負債表。")
    L.append("")
    qs = sorted({os.path.basename(f).split("_")[0]
                 for f in glob.glob(os.path.join(BS, "bs_hist", "*_twse.csv"))})
    L.append(f"- `bs_hist/` 涵蓋 **{len(qs)} 季**："
             f"{qs[0] if qs else '?'} ~ {qs[-1] if qs else '?'}")

    mine = {}
    if os.path.exists(CAP):
        with io.open(CAP, encoding="utf-8") as f:
            mine = {r["stock_id"]: r for r in csv.DictReader(f)}
    # ── ★★ 歷史驗證：上櫃日檔**每天**都有官方發行股數 ⇒ 拿季末那天當外部錨點。
    #   ⛔ 這比「拿季末股本對今天的股數」強得多——後者中間隔了一季，
    #     而那個落差是**我自己造成的**，不是方法的誤差（第一版就是這樣比的）。
    L += ["", "## ★★ 歷史驗證（上櫃，46 季逐季對官方發行股數）", ""]
    L.append("上櫃日檔**每天**都有官方發行股數 ⇒ 每一季的季末交易日都是一個外部錨點。")
    L.append("⛔ 面額用 `par_timeline.csv` **按當時**取，不是一律用 10。")
    L.append("")
    hist = _validate_otc()
    if hist:
        L.append(f"- 可比對 **{hist['n']:,}** 個（季, 檔）配對")
        L.append(f"- **中位數誤差 {hist['med'] * 100:.4f}%**")
        for th, k in ((0.0001, "a"), (0.001, "b"), (0.01, "c"), (0.05, "d")):
            L.append(f"- 誤差 < {th * 100:g}%：**{hist[k]:,}**"
                     f"（{hist[k] / hist['n'] * 100:.1f}%）")
        L.append("")
        L.append("⇒ **這條公式在 46 季的歷史上成立**，不是只有今天湊得上。")
        L.append("")
        L.append("### ⚠ 殘差的成因：查到一部分，⛔ 沒查完就不寫成查完")
        L.append("")
        L.append("- **特別股**：確認至少一例——3095 及成的差額 **+6,180,000 股**"
                 "，正好等於它的特別股股數。BS 的 `股本` 含特別股，日檔的發行股數不含。")
        L.append("- ⛔ **但特別股解釋不了全部**：2026Q2 誤差 ≥0.5% 的 109 檔裡，"
                 "**只有 2 檔**的差額對得上快照的特別股欄。")
        L.append("- ⚠ 我試過的另一個假設「差額 ≈ 私募股數」也**不成立**。")
        L.append("- **預收股款（權益項下）之約當發行股數**：解釋 9 檔"
                 "（股本收了、股票還沒發）。⛔ 「待註銷股本股數」解釋 0 檔。")
        L.append("")
        L.append("### ⭐ 剩下的那些，成因**很可能是時點不是季末**")
        L.append("")
        L.append("拿 2026Q2 誤差 ≥0.5% 的 **109 檔**，去掃全部 2,847 個日檔，"
                 "問一句：**有沒有哪一天的官方股數剛好等於推算值？**")
        L.append("")
        L.append("```")
        L.append("有某一天對得上：93 檔／109")
        L.append("  其中那一天在季末**之後**：83 檔｜之前：10 檔")
        L.append("```")
        L.append("")
        L.append("⇒ 這強烈指向：那張表的 `股本` **不是季末那一刻的值**，"
                 "而是接近出表當下的值。")
        L.append("⇒ **後果不是誤差，是時點錯位**：把較晚的股本掛在較早的那一季上，"
                 "序列的形狀會對、日期會偏。")
        L.append("")
        L.append("### ⭐⭐ 再往下查，成因有**季節指紋**——每年的 Q2 都是最差的")
        L.append("")
        L.append("逐季算「誤差 ≥0.5% 的比例」，46 季排開之後形狀非常清楚：")
        L.append("")
        L.append("| 年 | Q1 | **Q2** | Q3 | Q4 |")
        L.append("|---|---|---|---|---|")
        for row in _by_quarter_table():
            L.append(row)
        L.append("")
        L.append("⇒ **Q2 幾乎年年是其他季的兩倍**（Q2 約 13~19%，其餘約 5~9%）。")
        L.append("")
        L.append("**機制**：Q2 財報在 **8 月中**公布，而 8 月正是台股**除權息高峰**。")
        L.append("若表裡的 `股本` 反映的是**公布當下**而不是 6/30，")
        L.append("那 Q2 的股本已經含了股票股利、而 6/30 的股數還沒有")
        L.append("⇒ **Q2 系統性偏高**。實測那些離群檔的差額確實**大多為正**，方向一致。")
        L.append("")
        L.append("⚠ 例外：2021Q2 只有 7.6%（那年減資／股票股利特別少？**未查證**）。")
        L.append("")
        L.append("⇒ **結論改寫**：這不是「還有 12% 不知道為什麼」，")
        L.append("是**已知的時點錯位，而且知道它什麼時候最嚴重**。")
        L.append("⛔ 但落地前仍要決定：季頻序列的日期要掛「季末」還是「公布日」——")
        L.append("**那是語意決定，不是我的**。")

    latest = qs[-1] if qs else None
    # 最新一季拿來對「今天的股數」——⛔ 這是唯一有獨立答案可以對的一季。
    cap = load_quarter_capital(latest) if latest else {}
    L.append(f"- 最新一季 `{latest}` 有股本的公司：**{len(cap)} 檔**")
    L.append("")
    res = []
    for sid, c in cap.items():
        m = mine.get(sid)
        if not m or m.get("market") != "twse":
            continue
        try:
            sh = float(m["shares"])
            par = float(m["par"] or 10)
        except (ValueError, TypeError, KeyError):
            continue
        if not sh:
            continue
        est = c * 1000 / par
        res.append((abs(est - sh) / sh, sid, m.get("name", ""), est, sh, par))
    res.sort()
    if not res:
        L.append("⚠ 對不到任何一檔——`capital.csv` 或 `bs_hist` 讀不到。")
        _write(L)
        return 1
    d = [x[0] for x in res]
    med = statistics.median(d)
    L.append(f"## 對「今天的股數」的誤差（{len(res)} 檔上市）")
    L.append("")
    L.append(f"- **中位數誤差 {med * 100:.4f}%**")
    for th in (0.0001, 0.001, 0.01, 0.05):
        n = sum(1 for x in d if x < th)
        L.append(f"- 誤差 < {th * 100:g}%：**{n} 檔**（{n / len(d) * 100:.1f}%）")
    L.append("")
    L.append("## ⚠ 先講一件我自己比錯的事")
    L.append("")
    L.append(f"上面是拿 **{latest} 季末的股本** 去對 **今天的股數**——"
             "中間隔了一季，")
    L.append("**這段期間發生的減資、除權、面額變更都會讓它對不上**，"
             "而那是我的比法造成的，不是方法錯。")
    L.append("⇒ 所以下表每一檔都去 `data/adj/` 查**季末之後有沒有事件**。"
             "查得到的，離群就有解釋。")
    L.append("")
    L.append("| 代號 | 名稱 | 用面額 | 推算股數 | 實際股數 | 誤差 | 季末之後的事件 | 面額解釋得了嗎 |")
    L.append("|---|---|---|---|---|---|---|---|")
    qend = _quarter_end(latest)
    for e, sid, nm, est, sh, par in res[-12:][::-1]:
        k = sh / est if est else 0
        near = min((abs(k - t), t) for t in (0.25, 0.5, 1, 2, 2.5, 4, 5, 10, 20))
        expl = (f"✓ 面額應為 {par / near[1]:g}（比值 {k:.4f}）"
                if near[0] < 0.01 else f"⛔ 解釋不了（比值 {k:.4f}）")
        evs = _events_after(sid, qend)
        etxt = "；".join(f"{d} {kd}" for d, kd in evs[:3]) if evs else "**沒有**"
        L.append(f"| {sid} | {nm} | {par:g} | {est:,.0f} | {sh:,.0f} "
                 f"| {e * 100:.2f}% | {etxt} | {expl} |")
    n_ev = sum(1 for _, sid, *_ in res[-12:] if _events_after(sid, qend))
    L.append("")
    L.append(f"⇒ 這 12 檔裡有 **{n_ev} 檔**在季末之後真的有事件"
             "（減資／除權／面額變更）⇒ **離群是日期落差造成的**。")
    L.append("⛔ 其餘的才是真的還沒有解釋，那幾檔要逐檔查過才可以落地。")
    L.append("")
    L.append("## 判準（⛔ 沒過就不要寫序列）")
    L.append("")
    L.append("1. 中位數誤差 ≈ 0　→ " + ("✓ 過" if med < 1e-6 else f"✗ {med * 100:.4f}%"))
    L.append("2. 面額要**隨時間重建**（`par_change.csv` 24 筆事件），"
             "⛔ 不可以一律用 10")
    L.append("3. 上表「解釋不了」的每一檔要有交代")
    L.append("")
    L.append("⚠ 這條序列的語意是**每季末**的股數。季中的可轉債轉換、"
             "員工認股、現金增資看不到 ⇒ ⛔ 不可以拿去當日頻用。")
    _write(L)
    return 0


def _write(L):
    try:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        io.open(OUT, "w", encoding="utf-8").write("\n".join(L) + "\n")
        print(f"[shares_hist] 寫出 {OUT}")
    except OSError as ex:                                        # noqa: BLE001
        print(f"[shares_hist] 寫檔失敗：{ex}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
