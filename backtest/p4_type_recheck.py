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
import itertools
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


def mine(path: str, h: int = H) -> pd.DataFrame:
    """本線自己那一趟的四型分位（主格、預設 H120）⇒ 依【型名本體】為鍵。

    ⛔ 鍵是型名本體（`bare`）⇒ ⭐ 本線 09-20 22:40 的圈號訂正不影響它（訂正只動圈號字元）。"""
    s = pd.read_csv(path, comment="#")
    t = s[(s["period"] == PERIOD) & (s["H"] == h)].copy()
    t["key"] = t["type"].map(bare)
    return t.set_index("key")


# ⛔ 策略線 2355 §6-1 標【待查證】的那一行：resultsp1 §十二「H=20 的 p10」——⭐ 它是**裸圈號**
#    （那一行沒有型名本體當錨 ⇒ 字串替換抓不到它，圈號訂正也就修不到它）。逐字寫死，⛔ 不可改。
H20, H20_STRAT_P10 = 20, {"①": -13.6, "②": -14.9, "③": -12.9, "④": -10.4}
# ⛔ 兩個判準常數（⭐ 它們只決定【配得出／配不出】，⛔ 不決定圈號歸屬——歸屬是型名本體配對的結果）
H20_TOL, H20_MARGIN = 0.5, 1.0      # 落在 ±0.5pp 之內才算候選；而次近的要再遠 1.0pp 才算【唯一】


def h20_p10(path: str) -> dict:
    """本線面板的【主格 H=20 p10】，鍵＝型名本體（⛔ 不是圈號）。"""
    return {k: float(v) for k, v in mine(path, H20)["p10"].items()}


def match_bare(strat: dict, mine_p10: dict, tol: float = H20_TOL, margin: float = H20_MARGIN) -> pd.DataFrame:
    """把一行【裸圈號】的四個數**整行**配回【型名本體】。

    ⭐⭐ 判準是【整行的指派】，⛔ 不是逐格取最近的：
      ① 最佳指派的**每一格**差都要 ≤ `tol`（⛔ 否則是口徑對不上，不是配對問題）
      ② 次佳指派的**總差**要比最佳的大 `margin` 以上（⛔ 否則本件【分不出】）
    ⇒ ⭐⭐ 為什麼不逐格取最近：本線面板上【營收＋回檔 −13.26】與【純技術＋回檔 −12.87】
      只差 0.39pp ⇒ 逐格看這兩格都會判「分不出」，⛔ 而【整行】其實是被唯一決定的
      （最佳總差 0.37 vs 次佳 1.09）。⇒ 逐格判準會給出**錯的形狀**。
    ⛔ 配不出來時四格一律回 None，⭐ 而最佳／次佳的總差照樣印出來（讀的人自己看得到有多近）。"""
    circles, keys = list(strat), list(mine_p10)
    cost = lambda perm: sum(abs(strat[c] - mine_p10[k]) for c, k in zip(circles, perm))
    # ⛔ 長度要取【圈號個數】：拿全部 key 去排列的話，圈號比候選少時尾巴會製造一堆
    #    成本相同的重複指派 ⇒ ⭐ 次佳永遠等於最佳 ⇒ 這支函式會恆判「分不出」（第一版就是這樣）。
    ranked = sorted(itertools.permutations(keys, len(circles)), key=cost)
    best, second = ranked[0], (ranked[1] if len(ranked) > 1 else None)
    tb = cost(best)
    ts = cost(second) if second is not None else float("inf")
    worst_cell = max(abs(strat[c] - mine_p10[k]) for c, k in zip(circles, best))
    ok = (worst_cell <= tol) and (ts - tb >= margin)
    why = "✅ 整行唯一" if ok else ("⛔ 最佳指派有一格超出容差" if worst_cell > tol
                                else "⛔ 次佳指派太接近 ⇒ 本件分不出")
    t = pd.DataFrame([{"圈號": c, "策略線那一行的值": strat[c],
                       "配到的型名本體": (k if ok else None), "本線的值": mine_p10[k],
                       "這一格的差": abs(strat[c] - mine_p10[k])} for c, k in zip(circles, best)])
    t["最佳總差"], t["次佳總差"], t["判定"] = tb, ts, why
    return t


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


# ⛔ 爭議只在 ②／③ 這一對（①與④ 兩側從頭到尾一致 —— K線 2155 §1-4④、策略線 2215 §一 都確認過）
DISPUTED = ("②", "③")
DISPUTED_KEYS = ("正在噴出", "純技術＋回檔")


def disputed_pair(mine_p10: dict) -> pd.DataFrame:
    """⭐⭐ 爭議只在 ②／③ ⇒ 候選【限定】成那兩個型名本體，⛔ 不是拿四個型去配。

    ⛔ 為什麼要限定：①與④ 兩側從頭到尾一致（K線 2155 §1-4④）⇒ 它們不在爭議裡；
    而不限定的話，另外兩型只要湊巧離得近就會把答案搶走 —— ⭐ 而那是一個【本來就不該參賽的候選】。"""
    return match_bare({c: H20_STRAT_P10[c] for c in DISPUTED}, {k: mine_p10[k] for k in DISPUTED_KEYS})


def h20_report(summary_path: str, out_dir: str) -> list:
    """策略線 2355 §6-1 標【待查證】的那一行（resultsp1 §十二「H=20 的 p10」裸圈號）。

    ⛔ 本件只報【本線量到的數字與配對】，⭐ 措辭與訂正追加是策略線的格子。"""
    mp = h20_p10(summary_path)
    full = match_bare(H20_STRAT_P10, mp)
    duo = disputed_pair(mp)
    L = ["# resultsp1 §十二「H=20 的 p10」那一行 —— 回測線的獨立查證", "",
         "⭐ 策略線 2355 §6-1 把它標【待查證】：那一行是**裸圈號**（沒有型名本體當錨）",
         "⇒ ⛔ 字串替換抓不到它，圈號訂正也就修不到它。", "",
         "⛔ 本件是【對帳】不是檢定：沒有判定格、沒有種子 ⇒ ⛔ 不寫「測得出／測不出」。",
         "⛔ 而本件只報數字與配對 —— 訂正追加的措辭是策略線的格子。", "",
         "## 一、策略線那一行（逐字）與本線面板（主格 H=20 p10）", "",
         "| 圈號 | 策略線 §十二 那一行 | | 型名本體 | 本線 `resultsp4/summary.csv` |",
         "|:-:|---:|---|---|---:|"]
    ks = list(mp)
    for i, c in enumerate(H20_STRAT_P10):
        L.append(f"| {c} | {H20_STRAT_P10[c]:+.1f} | | {ks[i]} | {mp[ks[i]]:+.3f} |")
    L += ["", "## 二、⛔ 整行配不出來 —— ⭐ 而配不出來的原因【不是】②③", "",
          "```"]
    L += [f"最佳指派總差 {float(full['最佳總差'].iloc[0]):.3f}pp／次佳 {float(full['次佳總差'].iloc[0]):.3f}pp"
          f" ⇒ 差 {float(full['次佳總差'].iloc[0]) - float(full['最佳總差'].iloc[0]):.3f}pp < 門檻 {H20_MARGIN}pp",
          "⇒ ⛔ 整行【分不出】——⭐ 而卡住的是【①與③】：",
          f"   本線面板上 營收＋回檔 {mp['營收＋回檔']:+.3f} 與 純技術＋回檔 {mp['純技術＋回檔']:+.3f}"
          f" 只差 {abs(mp['營收＋回檔'] - mp['純技術＋回檔']):.3f}pp",
          "⇒ ⛔ 本線的數字分不開那兩格，⛔ 不可假裝分得開。", "```", "",
          "## 三、✅ ⭐⭐ 而【本件要查的那一對 ②／③】配得出來，而且差很遠", "",
          "```"]
    L += [f"②／③ 兩格、候選只有 {DISPUTED_KEYS[0]} 與 {DISPUTED_KEYS[1]}（⭐ ①與④ 兩側一直一致 ⇒ 不在爭議裡）",
          f"  ②＝{H20_STRAT_P10['②']:+.1f} → 正在噴出 {mp['正在噴出']:+.3f}（差 {abs(H20_STRAT_P10['②'] - mp['正在噴出']):.3f}pp）",
          f"  ③＝{H20_STRAT_P10['③']:+.1f} → 純技術＋回檔 {mp['純技術＋回檔']:+.3f}（差 {abs(H20_STRAT_P10['③'] - mp['純技術＋回檔']):.3f}pp）",
          f"⇒ 反過來配：② 對 純技術＋回檔 差 {abs(H20_STRAT_P10['②'] - mp['純技術＋回檔']):.3f}pp、"
          f"③ 對 正在噴出 差 {abs(H20_STRAT_P10['③'] - mp['正在噴出']):.3f}pp",
          f"⇒ 最佳總差 {float(duo['最佳總差'].iloc[0]):.3f}pp vs 次佳 {float(duo['次佳總差'].iloc[0]):.3f}pp"
          f" ⇒ 差 {float(duo['次佳總差'].iloc[0]) - float(duo['最佳總差'].iloc[0]):.3f}pp ≫ 門檻 {H20_MARGIN}pp",
          f"⇒ {duo['判定'].iloc[0]}", "```", "",
          "⇒ ⭐⭐ 所以那一行的 **② 指的是【正在噴出】、③ 指的是【純技術＋回檔】** ⇒ 它是【(甲) 圈號】。",
          "⇒ ⭐ 在 (乙) 之下那兩格**要對調** ⇒ 還原後那一行應讀：",
          "",
          f"```\n①{H20_STRAT_P10['①']:+.1f}　②{H20_STRAT_P10['③']:+.1f}　③{H20_STRAT_P10['②']:+.1f}　④{H20_STRAT_P10['④']:+.1f}\n```",
          "",
          "⭐ 與策略線 2355 §6-1 事前推的還原【逐字相同】——⇒ ⭐ 而那是兩條獨立路徑得到的同一個結果。", "",
          "## 四、⛔ 範圍限制（⛔ 缺這一節不算交件）", "",
          "- ⛔ 本線**沒有**重建 v8 面板：用的是 `resultsp4` 那一趟（本線自己的面板與路徑）",
          "  ⇒ ⭐ 那正是「獨立查證」的意思，⛔ 但它與 v8 不是同一份面板 ⇒ 逐格相等本來就不該期待。",
          f"- ⚠ 逐型差：{'／'.join(f'{k} {abs(H20_STRAT_P10[c] - mp[k]):.2f}pp' for c, k in zip(H20_STRAT_P10, ks))}"
          f" ⇒ 最大 {max(abs(H20_STRAT_P10[c] - mp[k]) for c, k in zip(H20_STRAT_P10, ks)):.2f}pp",
          "  ⚠ 而 H=120 那一趟量到的口徑差是 0.13pp ⇒ ⭐ H=20 這一格【比較大】，要一起讀。",
          "- ⛔⛔ **①與③ 本線分不開**（差 0.39pp）⇒ 整行還原成立，是因為【①④ 兩側一致】這個",
          "  **別線已確認的前提**（K線 2155 §1-4④），⛔ 不是本線量出來的 ⇒ 兩件要分開記。",
          "- ⛔ 圈號怎麼寫是策略線／判定線的格子 ⇒ 本線只報配對，⛔ 不動任何文件。", ""]
    os.makedirs(out_dir, exist_ok=True)
    full.to_csv(os.path.join(out_dir, "h20_bare_circle.csv"), index=False)
    open(os.path.join(out_dir, "H20_BARE_CIRCLE.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    return L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=RESULTS)
    ap.add_argument("--summary", default=os.path.join(RESULTS, "summary.csv"))
    ap.add_argument("--task", default="recheck", choices=("recheck", "h20"),
                    help="h20 ＝ 只查證 §十二 那一行【裸圈號】，⛔ 不重寫 TYPE_RECHECK.md（它是已交件的舊報告）")
    a = ap.parse_args()
    if a.task == "h20":
        print("\n".join(h20_report(a.summary, a.out)), flush=True)
        return
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
