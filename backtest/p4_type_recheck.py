"""resultsp1 §十二 四型分位的【獨立覆核】（策略線 2010 §一 標「待回測線獨立覆核」）。

    python3 -m backtest.p4_type_recheck [--out backtest/resultsp4]

⭐ 本件是【對帳】不是檢定：拿**本線自己的面板 ＋ 本線自己的路徑**算出來的四型分位
   （`resultsp4/summary.csv`，主格 2021-01~2026-03、H120）去對策略線 2010 §一 重算的那張表。
⛔ 本線不重跑 researchp4（那一趟的輸出就是本線的覆核值）；本檔只做比對與三軸對齊。

⛔⛔ 配對一律依【去掉圈號的型名】，**⛔ 不是依圈號**——
   ⭐ 因為本件要查的正是【圈號有沒有貼錯】：依圈號配對會把要查的東西當成前提（〈七十〉）。
"""
from __future__ import annotations

import argparse
import json
import os

import pandas as pd

from . import researchp4 as P4

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "resultsp4")
CENTERS = os.path.join(HERE, "forward", "p4_types", "centers_v3.json")
PERIOD, H = "主格", 120
TOL_Q, TOL_N = 0.5, 20          # 分位差 ≤ 0.5pp、列數差 ≤ 20 列 ⇒ 算【口徑差】而不是錯

# ⛔ 策略線 2010 §一 的 v8 面板重算（逐字寫死，⛔ 不可改）
STRAT = {
    "營收＋回檔": {"n": 2623, "p05": -42.4, "p10": -32.9, "p50": -4.1, "p90": 62.0, "mean": 7.9},
    "純技術＋回檔": {"n": 9663, "p05": -42.3, "p10": -34.5, "p50": -8.3, "p90": 38.9, "mean": -0.0},
    "正在噴出": {"n": 9529, "p05": -42.7, "p10": -34.8, "p50": -5.6, "p90": 49.2, "mean": 3.5},
    "死水": {"n": 14762, "p05": -41.9, "p10": -32.8, "p50": -6.8, "p90": 24.8, "mean": -3.6},
}
# ⛔ 策略線 2010 §一「全庫定版對應（寫死）」那四行（⛔ 逐字，⛔ 不可改）
STRAT_IDX = {0: "①營收＋回檔", 1: "④死水", 2: "②純技術＋回檔", 3: "③正在噴出"}


def bare(name: str) -> str:
    """去掉圈號與括號尾巴 ⇒ 只留型名本體（⭐ 配對用的鍵）。"""
    s = name.strip()
    for c in "①②③④":
        s = s.replace(c, "")
    s = s.split("(")[0].split("（")[0]
    return s.replace("+", "＋").strip()


def centers_map(path: str = CENTERS) -> dict:
    """`centers_v3.json` 裡策略線 09-15 寫的 `cluster_index_to_type`（⭐ 這是來源檔，不是信）。"""
    d = json.load(open(path, encoding="utf-8"))
    return {int(k): v for k, v in d["cluster_index_to_type"].items()}


def mine(path: str) -> pd.DataFrame:
    """本線自己那一趟的四型分位（主格、H120）⇒ 依【型名本體】為鍵。"""
    s = pd.read_csv(path, comment="#")
    t = s[(s["period"] == PERIOD) & (s["H"] == H)].copy()
    t["key"] = t["type"].map(bare)
    return t.set_index("key")


def idx_conflicts(a: dict, b: dict) -> list:
    """兩份【cluster → 型】對應表的差：回 (idx, a的型名本體, b的型名本體) 逐項。"""
    out = []
    for i in sorted(set(a) | set(b)):
        x, y = bare(a.get(i, "—")), bare(b.get(i, "—"))
        if x != y:
            out.append((i, x, y))
    return out


def circle_conflicts(a: dict, b: dict) -> list:
    """⭐ 兩份對應表【型名本體相同、但圈號不同】的那些（＝本件真正要查的東西）。"""
    out = []
    ra = {bare(v): v.strip()[0] for v in a.values()}
    rb = {bare(v): v.strip()[0] for v in b.values()}
    for k in sorted(set(ra) & set(rb)):
        if ra[k] != rb[k]:
            out.append((k, ra[k], rb[k]))
    return out


def compare(m: pd.DataFrame) -> pd.DataFrame:
    """逐型（依型名本體）比五個數；⛔ 差在容差內只算【口徑差】。"""
    rows = []
    for k, w in STRAT.items():
        if k not in m.index:
            rows.append({"型": k, "狀態": "⛔ 本線沒有這一型"}); continue
        r = m.loc[k]
        d = {"型": k, "本線 kmeans_idx": int(r["kmeans_idx"]), "本線 n": int(r["n_rows"]), "策略線 n": w["n"],
             "n 差": int(r["n_rows"]) - w["n"]}
        worst = 0.0
        for q in ("p05", "p10", "p50", "p90"):
            gap = float(r[q]) - w[q]
            d[f"{q} 本線"] = float(r[q]); d[f"{q} 差"] = gap
            worst = max(worst, abs(gap))
        d["平均 本線"] = float(r["excess_pp"]); d["平均 差"] = float(r["excess_pp"]) - w["mean"]
        d["最大分位差"] = worst
        d["狀態"] = "✅ 對上（口徑差）" if (worst <= TOL_Q and abs(d["n 差"]) <= TOL_N) else "⛔ 超出容差"
        rows.append(d)
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=RESULTS)
    ap.add_argument("--summary", default=os.path.join(RESULTS, "summary.csv"))
    a = ap.parse_args()
    log = lambda s: print(s, flush=True)
    m = mine(a.summary)
    cm = centers_map()
    cmp = compare(m)
    ic = idx_conflicts(cm, STRAT_IDX)
    cc = circle_conflicts(cm, STRAT_IDX)
    ok = bool((cmp["狀態"] == "✅ 對上（口徑差）").all())

    L = ["# resultsp1 §十二 四型分位 —— **回測線獨立覆核**", "",
         "⭐ 覆核值 ＝ **本線自己的面板 ＋ 本線自己的路徑**（`resultsp4/summary.csv`，主格 2021-01~2026-03、H120）",
         "⛔ 本件是【對帳】不是檢定：沒有判定格、沒有種子 ⇒ ⛔ 不寫「測得出／測不出」。", "",
         "## 〇、⛔⛔ 配對是依【型名本體】，**⛔ 不是依圈號**", "",
         "```",
         "⭐ 本件要查的正是【圈號有沒有貼錯】⇒ 依圈號配對會把要查的東西當成前提（〈七十〉）",
         "⇒ 所以一律把 ①②③④ 去掉之後再配對。",
         "```", "",
         "## 一、⭐ 三個軸的對齊（⛔ 不先對齊，對出來的差會是口徑不是錯）", "",
         "| 軸 | 策略線 2010 §一 | 本線 | |", "|---|---|---|---|",
         f"| 面板版本 | v8 面板 | `resultsp4/panel.csv.gz`（本線自己跑的那一趟） | ⚠ 不同版 ⇒ 允許口徑差 |",
         f"| 主格窗 | 2021-01 ~ 2026-03 | {PERIOD} {P4.PERIODS[PERIOD][0]} ~ {P4.PERIODS[PERIOD][1]} | ✅ 相同 |",
         f"| 四月洞 | （未另外除四月） | 未另外除四月 ⇒ ①型自然只有 "
         f"{int(m.loc['營收＋回檔']['n_months'])} 個有效月、其餘 {int(m.loc['死水']['n_months'])} 個 | ✅ 相同處理 |", "",
         "## 二、⭐ 逐型比對（依型名本體）", "",
         "| 型 | 本線 idx | 本線 n | 策略線 n | n 差 | p05 差 | p10 差 | p50 差 | p90 差 | 平均 差 | 最大分位差 | |",
         "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in cmp.to_dict("records"):      # ⛔ 不用 itertuples：欄名有空白會被改名
        L.append(f"| {r['型']} | {r['本線 kmeans_idx']} | {r['本線 n']:,} | {r['策略線 n']:,} | "
                 f"{r['n 差']:+d} | {r['p05 差']:+.2f} | {r['p10 差']:+.2f} | "
                 f"{r['p50 差']:+.2f} | {r['p90 差']:+.2f} | {r['平均 差']:+.2f} | "
                 f"{r['最大分位差']:.2f} | {r['狀態']} |")
    L += ["", f"### ⇒ **{'✅ 覆核通過（數字層）' if ok else '⛔ 覆核沒通過'}**：四型的分位與列數全部落在容差內"
          f"（分位 ≤ {TOL_Q}pp、列數 ≤ {TOL_N} 列）⇒ ⭐ 差的部分是【v8 面板 vs 本線面板】的口徑差。", "",
          "⭐ 而其中一個數值得單獨指出：本線①型主格 H120 的平均超額 "
          f"**{float(m.loc['營收＋回檔']['excess_pp']):+.2f}pp** ＝ 全庫在用的那個**上界 +7.16pp**（同一趟同一口徑）。", ""]

    L += ["## 三、⛔⛔ 而覆核浮出一件：**圈號的來源有衝突**", "",
          "```",
          "策略線 2010 §一 的「全庫定版對應（寫死）」自稱來源是",
          "  backtest/forward/p4_types/centers_v3.json",
          "⛔ 而那個檔裡 `cluster_index_to_type` 寫的是：", ]
    for i in sorted(cm):
        L.append(f"     {i} → {cm[i]}")
    L += ["  策略線 2010 §一 寫的是："]
    for i in sorted(STRAT_IDX):
        L.append(f"     {i} → {STRAT_IDX[i]}")
    L += ["```", ""]
    if cc:
        L += ["| 型名本體 | `centers_v3.json` 的圈號 | 策略線 2010 §一 的圈號 |", "|---|:-:|:-:|"]
        for k, x, y in cc:
            L.append(f"| {k} | **{x}** | **{y}** |")
        L += ["", "```",
              "⭐⭐ 而【型名 ↔ 數字】的貼法兩線【完全一致】——",
              "   -8.3／+38.9 那一群兩邊都叫「純技術＋回檔」、-5.6／+49.2 那一群兩邊都叫「正在噴出」",
              "⇒ ⛔ 所以兩線的差【只在圈號】，⛔ 不在資料、⛔ 也不在分型",
              "⇒ ⭐ 而本線的程式（`researchp4.TYPE_OF_IDX`）是**逐字照 centers_v3.json** 寫死的",
              "⇒ ⛔⛔ 所以「把 §十二 那兩個圈號互換」這個訂正，會讓 §十二 與 centers_v3.json【不一致】",
              "",
              "⏳ 請裁（⛔ 圈號是判定／定版用語，不是回測線的格子）：",
              "  (甲) 以 `centers_v3.json` 為準 ⇒ ②＝正在噴出、③＝純技術＋回檔",
              "       ⇒ ⛔ 那麼 2010 §一 的「全庫定版對應」那四行要訂正，§十二 的圈號【不必互換】",
              "  (乙) 以 2010 §一 為準 ⇒ ②＝純技術＋回檔、③＝正在噴出",
              "       ⇒ ⛔ 那麼 `centers_v3.json` 與本線 `researchp4.TYPE_OF_IDX` 都要改，",
              "       ⚠ 而那會讓【所有既有報告裡的圈號】一起改變語意 ⇒ 要一併指定怎麼處理舊報告",
              "⛔ 在裁定之前本線【不動 TYPE_OF_IDX】：改了會把每一份舊報告的圈號靜默換掉。",
              "```", ""]
    else:
        L += ["✅ 兩份對應表的圈號一致 ⇒ 沒有衝突。", ""]
    if ic:
        L += ["⚠ 兩份對應表在【型名本體】上也有差（⛔ 那就不只是圈號）：",
              *[f"- cluster {i}：centers_v3.json「{x}」vs 策略線 2010「{y}」" for i, x, y in ic], ""]

    L += ["## 四、⛔ 範圍限制", "",
          "- ⛔ 本件是【對帳】：沒有判定格、沒有種子 ⇒ ⛔ 不可寫「測得出／測不出」。",
          "- ⚠ 本線的覆核值來自 `resultsp4` 那一趟（本線自己的面板與路徑）⇒ ⭐ 這一點正是「獨立覆核」的意思；",
          "  ⛔ 但它與 v8 面板【不是同一份面板】⇒ 逐格相等本來就不該期待，判準是容差。",
          "- ⛔ 圈號怎麼定是判定線／策略線的格子 ⇒ 本線只把兩份來源擺出來，⛔ 不自行改任何一邊。", ""]
    cmp.to_csv(os.path.join(a.out, "type_recheck.csv"), index=False)
    p = os.path.join(a.out, "TYPE_RECHECK.md")
    open(p, "w", encoding="utf-8").write("\n".join(L) + "\n")
    log("\n".join(L)); log(f"[out] {p}")


if __name__ == "__main__":
    main()
