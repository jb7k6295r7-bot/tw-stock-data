"""K線分析線 1915 §六【逐字口徑】的描述性交件：**參考C 的候選裡，市值前 50 佔幾成**。

    python3 -m backtest.top50_share [--out backtest/results_top50]

⛔⛔ 這一件是【描述性交件】，⛔ 不是登錄、⛔ 不是檢定：
  ⚠ 用途是【第三條策略要不要開】的輸入，⛔ 不是參考C 的績效證據，
  ⛔ 也不可寫「測得出」（n ＝ 1 個窗，〈九十八〉）。

⭐ 口徑（K線分析線 1915 §六 逐字，⛔ 本線一個字都不自訂）：
```
母體　參考C 的逐月候選（⛔ 過與門檻B【同一組】閘門後的候選，不是訊號超集）
分子　該量測月的候選中，落在【當月全市場市值前 50】的檔數
分母　該量測月的候選數
市值　⭐ 口徑與 PREREGP13 的 W1 相同：量測日原始收盤 × 當日 shares
窗　　全窗 2017-03 ~ 2026-03（⛔ 與 P11 的判定窗相同）
必報　① 全窗合計比例（⭐ 與 B 的 7.6% ＝ 38/503【同一個口徑】）
　　　② 逐月比例的中位／p10／p90
　　　③ ⭐ 兩線的 B 值要各報一次 —— 若本線算出來的 B 不是 7.6% ⇒ ⛔ 先對帳再看 C
```

⛔⛔ 實作一律借用既有的那一份（四點五：同一件事只准一份實作）：
  sig  ＝ `researchp7.build_sig_gate_b(signal=...)`（⭐ B 與 C 走同一支，差別只有一個旗標）
  市值 ＝ `researchp13.load_mktcap`（原始收盤 × 當日 shares，⛔ 不走 load_stock）
  前 50 ＝ `researchp13.top50_by_month`（⭐ 逐月重算）
⇒ 本檔只新增【逐月分子/分母】與【對帳】這兩件事。

⚠ 兩個口徑差要【兩個都報，⛔ 不挑】：
  ① 前 50 的母體：1915 §六 的字面是「**全市場**市值前 50」，
     ⛔ 而策略線 1445 §一 的 38/503 用的是它的 0050 代理【**上市普通股**市值前 50】
     ⇒ 兩種都算、都報（〈七十〉：先確認同口徑；〈一百〇八〉：軸沒指定就都要交代）。
  ② 日期：本檔一律用【量測日】（＝ entry_pos − 1），因為 1915 §六 逐字寫「量測日原始收盤」。
     ⚠ PREREGP13 的重疊度用的是【進場日】⇒ 兩者差一個交易日，⛔ 不是同一個量。
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import pandas as pd

from . import data as D
from . import p4_features as P4F
from . import researchp1 as P1
from . import researchp7 as P7
from . import researchp13 as P13

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results_top50")
EVENT_WIN = ("2023-07", "2025-04")          # 策略線 1445 §三 的事件窗（22 個月／503 筆／323 檔）
WANT_EVENT_B = {"rows": 503, "stocks": 323, "months": 22}   # ⛔ 對帳目標，⛔ 不是本件的判準


def measure_pos(sig: pd.DataFrame) -> dict:
    """每個量測月的【量測日日曆位置】＝ entry_pos − 1（⛔ 不是進場日）。

    ⚠ 面板是逐月的 ⇒ 同一個月的所有候選共用同一個量測日；⛔ 不共用就停（那代表口徑假設錯了）。
    """
    out = {}
    for m, g in sig.groupby("month"):
        e = g["entry_pos"].unique()
        if len(e) != 1:
            raise SystemExit(f"⛔ {m} 的量測月有 {len(e)} 個 entry_pos ⇒ 「當月」沒有唯一的量測日 ⇒ 停")
        out[str(m)] = int(e[0]) - 1
    return out


def share_by_month(sig: pd.DataFrame, mpos: dict, top50: dict) -> pd.DataFrame:
    """逐月：分母＝該量測月的候選數、分子＝其中落在【當月市值前 50】的檔數。"""
    rows = []
    for m, g in sig.groupby("month"):
        t = mpos[str(m)]
        if t not in top50:
            raise SystemExit(f"⛔ {m}（量測日位置 {t}）沒有前 50 名單 ⇒ 停")
        top = top50[t]
        hit = int(sum(1 for s in g["sid"] if s in top))
        rows.append({"month": str(m), "mpos": t, "n": int(len(g)), "hit": hit, "share": hit / len(g)})
    return pd.DataFrame(rows).sort_values("month").reset_index(drop=True)


def summarize(tab: pd.DataFrame) -> dict:
    """必報①②：全窗合計（⭐ 合計分子÷合計分母，⛔ 不是逐月比例的平均）＋ 逐月比例的中位／p10／p90。"""
    n, hit = int(tab["n"].sum()), int(tab["hit"].sum())
    return {"months": int(len(tab)), "n": n, "hit": hit, "share": hit / n if n else float("nan"),
            "med": float(tab["share"].median()), "p10": float(tab["share"].quantile(0.10)),
            "p90": float(tab["share"].quantile(0.90)), "zero_months": int((tab["hit"] == 0).sum())}


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=RESULTS)
    ap.add_argument("--panel", default=os.path.join(HERE, "resultsp4", "panel.csv.gz"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    log = lambda s: print(s, flush=True)

    cal = D.load_calendar()
    uni = D.load_universe()
    panel = P4F.read_panel(a.panel)
    sids = set(panel["stock_id"])
    closes, opens = P1.load_prices(sids, cal, uni.set_index("stock_id")["market"])
    sig_b = P7.build_sig_gate_b(panel, cal, closes, opens, signal="B")
    got, want = P7.accept_sig_b(sig_b), P7.WANT_SIG_B
    if got != want:
        raise SystemExit(f"⛔ 門檻B sig 驗收數對不上 ⇒ 停跑\n  want {want}\n  got  {got}")
    sig_c = P7.build_sig_gate_b(panel, cal, closes, opens, signal="C")
    if not set(zip(sig_b["sid"], sig_b["month"])) <= set(zip(sig_c["sid"], sig_c["month"])):
        raise SystemExit("⛔ B ⊄ C ⇒ 兩者不是同一組閘門 ⇒ 停")
    log(f"[sig] B ✅ {len(sig_b):,} 筆／{sig_b['sid'].nunique():,} 檔；"
        f"C {len(sig_c):,} 筆／{sig_c['sid'].nunique():,} 檔（⭐ B ⊂ C 已驗）")

    allst = set(uni.loc[uni["kind"] == "stock", "stock_id"])
    twse = set(uni.loc[(uni["market"] == "twse") & (uni["kind"] == "stock"), "stock_id"])
    caps = P13.load_mktcap(sids | allst, cal)
    log(f"[市值] {len(caps):,} 檔（全市場普通股 {len(allst):,}／上市普通股 {len(twse):,}）")

    mp_b, mp_c = measure_pos(sig_b), measure_pos(sig_c)
    months = np.array(sorted({*mp_b.values(), *mp_c.values()}), int)
    tops = {"全市場": P13.top50_by_month(caps, allst, months, len(cal)),
            "上市普通股": P13.top50_by_month(caps, twse, months, len(cal))}

    L = ["# 參考C 的候選裡【市值前 50】佔幾成 —— 描述性交件（K線分析線 1915 §六 逐字口徑）", "",
         "⛔⛔ **這不是登錄、不是檢定、不是參考C 的績效證據**。",
         "⚠ 用途 ＝【第三條策略要不要開】的輸入；⛔ 不可寫「測得出」（n ＝ 1 個窗，〈九十八〉）。", "",
         "## 〇、⚠ 兩個口徑差：**兩個都報，⛔ 本線不挑**", "",
         "```",
         "① 前 50 的母體",
         "   1915 §六 的字面　　＝【全市場】市值前 50",
         f"   策略線 1445 §一 的 38/503 用的是它的 0050 代理 ＝【上市普通股】市值前 50",
         "   ⇒ ⛔ 兩者不是同一個名單 ⇒ 本件兩種都算（〈七十〉：先確認同口徑）",
         "② 日期",
         "   1915 §六 逐字寫【量測日】原始收盤 ⇒ 本件一律用量測日（＝ entry_pos − 1）",
         "   ⚠ PREREGP13 的重疊度用的是【進場日】⇒ 差一個交易日，⛔ 不是同一個量",
         "```", ""]

    # ── 必報③：先對帳 B ──
    L += ["## 一、⭐ 必報③：**兩線的 B 值各報一次**（⛔ 對不上就先對帳，〈七十〉）", ""]
    tabs = {}
    for uni_name, top in tops.items():
        tb = share_by_month(sig_b, mp_b, top)
        tabs[("B", uni_name)] = tb
        ev = tb[(tb["month"] >= EVENT_WIN[0]) & (tb["month"] <= EVENT_WIN[1])]
        sb, se = summarize(tb), summarize(ev)
        tabs[("B事件窗", uni_name)] = ev
        L += [f"### 前 50 母體 ＝ {uni_name}", "",
              f"- **全窗 2017-03 ~ 2026-03**：{sb['hit']} / {sb['n']} ＝ **{_pct(sb['share'])}**"
              f"（{sb['months']} 個月）",
              f"- **事件窗 {EVENT_WIN[0]} ~ {EVENT_WIN[1]}**（策略線 1445 §三／§四 的那一段）："
              f"{se['hit']} / {se['n']} ＝ **{_pct(se['share'])}**（{se['months']} 個月）", ""]
        ev_sids = sig_b[(sig_b["month"] >= EVENT_WIN[0]) & (sig_b["month"] <= EVENT_WIN[1])]
        L += [f"  ⇒ 事件窗內門檻B 訊號 **{len(ev_sids)} 筆／{ev_sids['sid'].nunique()} 檔／"
              f"{ev_sids['month'].nunique()} 個月**（策略線 1445 §三："
              f"{WANT_EVENT_B['rows']} 筆／{WANT_EVENT_B['stocks']} 檔／{WANT_EVENT_B['months']} 個月）", ""]
    ok_rows = {"rows": int(len(sig_b[(sig_b["month"] >= EVENT_WIN[0]) & (sig_b["month"] <= EVENT_WIN[1])])),
               "stocks": int(sig_b[(sig_b["month"] >= EVENT_WIN[0]) & (sig_b["month"] <= EVENT_WIN[1])]["sid"].nunique()),
               "months": int(sig_b[(sig_b["month"] >= EVENT_WIN[0]) & (sig_b["month"] <= EVENT_WIN[1])]["month"].nunique())}
    L += ["### ⇒ 對帳結論", "",
          f"- 分母（事件窗訊號筆數）：本線 {ok_rows} vs 策略線 {WANT_EVENT_B} ⇒ "
          f"{'✅ 逐項相同' if ok_rows == WANT_EVENT_B else '⛔ 對不上 ⇒ 下面的 C 只能當【本線口徑】讀'}", ""]

    # ── 必報①②：C ──
    L += ["## 二、⭐ 必報①②：**參考C**", ""]
    for uni_name, top in tops.items():
        tc = share_by_month(sig_c, mp_c, top)
        tabs[("C", uni_name)] = tc
        sc = summarize(tc)
        ev = tc[(tc["month"] >= EVENT_WIN[0]) & (tc["month"] <= EVENT_WIN[1])]
        L += [f"### 前 50 母體 ＝ {uni_name}", "",
              f"- **① 全窗合計比例**：{sc['hit']} / {sc['n']} ＝ **{_pct(sc['share'])}**（{sc['months']} 個月）",
              f"- **② 逐月比例**：中位 **{_pct(sc['med'])}**／p10 **{_pct(sc['p10'])}**／p90 **{_pct(sc['p90'])}**",
              f"  ⚠ 逐月分子為 0 的月份 **{sc['zero_months']} / {sc['months']}** ＝ {_pct(sc['zero_months'] / sc['months'])}"
              "（⭐ 中位要跟這個數一起讀，〈九十二〉）",
              f"- 參考：事件窗同口徑 {summarize(ev)['hit']} / {summarize(ev)['n']} ＝ **{_pct(summarize(ev)['share'])}**", ""]

    for (k, u), t in tabs.items():
        t.to_csv(os.path.join(a.out, f"bymonth_{k}_{u}.csv"), index=False)
    L += ["## 三、⛔ 範圍限制", "",
          "- ⛔ 本件是【描述】：沒有檢定、沒有種子、沒有判定 ⇒ ⛔ 不可寫「測得出／測不出」。",
          "- ⛔ 「前 50」是本線用【原始收盤 × 當日 shares】自己排的名單，⛔ 不是 0050 官方成分"
          "（PREREGP13 的代理驗證：2023-07~2025-01 代理 +58.25% vs 0050 實際 +63.2%）。",
          "- ⚠ 分母是【股-月】不是【檔】：同一檔在不同月會重複計入（〈七十〉：先寫下定義）。",
          "- ⚠ 候選＝過閘門後**且 H120 出場日在日曆內**的那些（與門檻B 同一支 `build_sig_gate_b`）。", ""]
    p = os.path.join(a.out, "C_TOP50_SHARE.md")
    open(p, "w", encoding="utf-8").write("\n".join(L) + "\n")
    log("\n".join(L))
    log(f"[out] {p}")


if __name__ == "__main__":
    main()
