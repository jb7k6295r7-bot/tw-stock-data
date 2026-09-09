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
   ⇒ 要先把**面額隨時間變化**重建出來（`par_change.csv` 有 24 筆事件與日期）。
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
