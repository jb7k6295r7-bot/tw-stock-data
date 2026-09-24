# -*- coding: utf-8 -*-
"""四型（PREREGP4v3）**純計數**：窗的實際交易日數、⌊W/120⌋、逐組有 ≥1 事件的區段數。

⇐ 台股策略線 20260924-1223 §三（裁定線 1235 §四 步驟② 確認要先做這個）
⛔⛔ 本支【不重跑策略】、⛔ 不動任何判定、⛔ 不算任何報酬、⛔ 不宣告四型判定失效。
   ⭐ 只把 1223 §二 的【粗估】換成實數，裁定線才有東西可裁。

⚠ 1223 §二 自己標了三件不能說的，本線照樣不碰：
   ⓑ 四型的判定是【同一量測日的四組橫斷面比較】，⛔ 不是單臂事件研究
      ⇒ 新條文是否直接適用 ⇒ ⛔ 本線不裁（裁定線 1235 §四 (丙) 留了證法，那是另一件）
   ⓒ 四型標著「回溯分析・不是前瞻登錄」⇒ 它的判定級別本來可能就有註記

口徑（⭐ 逐條指名）：
   窗　　 researchp4.PERIODS 逐字：主格 2021-01-01~2026-03-31／副格 2017-01-01~2024-12-31
   H　　 JUDGE_H = 120（researchp4 第 42 行：JUDGE_PERIOD, JUDGE_H = "主格", 120）
   事件　 classified.csv.gz 的合格列（⭐ 用 eligible，＝ researchp7 檔頭的 eligible 同一個）
   區段　 從【該窗第一個交易日】起切、長度 120 的不重疊區段（⛔ 不是從 523 —— 那是別件的窗）
   上限　 ⌊窗交易日數 / 120⌋；門檻 30／100 依裁定線 1235 §二 是【窗長的函數】
"""
# ⛔⛔ 圈號陷阱：本支第一版用【帶圈號的型名】比對 ⇒ ②③ 兩組量到 **0 事件**，⛔ 而它不報錯。
#   成因（⭐ 查證後，⛔ 不是憑印象）：
#     classified.csv.gz 最後被 commit 3137d36e9 寫出，⭐ 而它在圈號訂正 d96483bf0
#     （2026-09-20 14:30，K線分析線 2155 §一 裁 (乙)）【之前】
#     ⇒ ⇒ 所以那份 CSV 帶的是 (甲) 圈號：②＝正在噴出、③＝純技術＋回檔
#        而現行 researchp4.TYPE_OF_IDX 是 (乙)：③＝正在噴出、②＝純技術＋回檔 ⇒ 兩者相反
#   ⚠⚠ 危險在哪：不是報錯，是**那兩組安靜地變成 0**，而 0 在一張表裡看起來像一個結果。
#   ⭐⭐ 而這個陷阱【本專案已經登錄過】—— backtest/forward/p4_types/圈號沿革註記.md 逐字：
#      「引用那些來源的舊內容時，②／③ 要對調；⭐ 而【型名本體】全庫一直一致
#        ⇒ **依型名讀就不會錯**」
#      並且 §三 逐字寫「跨線比對一律依【去掉圈號的型名本體】…
#        backtest/p4_type_recheck.bare() 就是那一份實作，⛔ 不要再寫第二份」
#   ⇒ ✅ 所以本支改用 bare() 當比對鍵，⛔ 不自己寫去圈號的程式碼。

from __future__ import annotations
import os, sys
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import researchp4 as P4
from backtest.p4_type_recheck import bare   # ⭐ 去圈號的唯一實作（⛔ 不寫第二份）

H = P4.JUDGE_H
cal = D.load_calendar()
df = pd.read_csv("backtest/resultsp4/classified.csv.gz",
                 usecols=["stock_id", "measure_date", "eligible", "type"])
df["measure_date"] = pd.to_datetime(df["measure_date"])
df = df[df["eligible"].astype(bool)]
print("classified 合格列 {:,}｜H = {}（researchp4.JUDGE_H）".format(len(df), H))
print()

TYPES = [bare(t) for t in P4.TYPES]   # ⭐ 依【型名本體】比對，⛔ 不用圈號
rows = []
for name in ("主格", "副格", "擬合窗／追認格", "第二層"):
    if name not in P4.PERIODS:
        continue
    lo, hi = (pd.Timestamp(x) for x in P4.PERIODS[name])
    days = cal[(cal >= lo) & (cal <= hi)]
    n_days = len(days)
    cap = n_days // H
    first = days[0]
    e3, e2 = n_days // 100, n_days // 30      # 裁定線 1235 §二：出口③ ⇔ H ≤ ⌊W/100⌋ 等
    print("=== {} {} ~ {} ｜實際 **{:,}** 交易日（⛔ 1223 §二 粗估的是 ≈{:,}）"
          .format(name, lo.date(), hi.date(), n_days, {"主格": 1382, "副格": 1950}.get(name, 0)))
    print("    ② 不重疊 {} 日區段上限 ＝ ⌊{:,}/{}⌋ = **{}**".format(H, n_days, H, cap))
    print("    ⭐ 而門檻是窗長的函數：出口③ ⇔ H ≤ ⌊W/100⌋ = {}；出口② ⇔ H ≤ ⌊W/30⌋ = {}"
          .format(e3, e2))
    sub = df[(df["measure_date"] >= lo) & (df["measure_date"] <= hi)].copy()
    pos = {d: i for i, d in enumerate(days)}
    sub["seg"] = sub["measure_date"].map(pos)
    sub = sub[sub["seg"].notna()]
    sub["seg"] = (sub["seg"].astype(int) // H)
    sub = sub[sub["seg"] < cap]
    sub["type_bare"] = sub["type"].map(bare)
    print("    ③ 逐組有 ≥1 事件的區段數：")
    for t in TYPES:
        a = sub[sub["type_bare"] == t]
        hits = a["seg"].nunique()
        n = len(a)
        exit_no = "③" if min(n, hits) >= 100 else ("②" if min(n, hits) >= 30 else "①")
        print("        {:<12} 事件 {:>6,}｜有事件區段 **{:>2}** / 上限 {:<3}｜min = {:>2} ⇒ 出口 **{}**"
              .format(t, n, hits, cap, min(n, hits), exit_no))
        assert n > 0, "⛔ 組 {} 量到 0 事件 ⇒ 幾乎一定是【圈號／型名對不上】，⛔ 不是真的沒有事件".format(t)
        rows.append(dict(window=name, n_days=n_days, H=H, seg_cap=cap, type=t,
                         events=n, seg_hit=hits, conservative=min(n, hits), exit=exit_no,
                         exit3_max_H=e3, exit2_max_H=e2))
    print()

out = pd.DataFrame(rows)
out.to_csv("backtest/resultsp4/segs_h120.csv", index=False, encoding="utf-8")
print("⇒ 落檔 backtest/resultsp4/segs_h120.csv（{} 列）".format(len(out)))
print()
print("=== ⭐⭐ 給裁定線的一句（⛔ 本線不裁，只報數）===")
m = out[out.window == "主格"]
print("   主格實際 {:,} 交易日 ⇒ H=120 的區段上限 **{}**，四組實際各 {} 段"
      .format(int(m.n_days.iloc[0]), int(m.seg_cap.iloc[0]), sorted(set(m.seg_hit))))
print("   ⇒ ⛔ 四組全部 < 30 ⇒ 依裁定線 1235 §二② 的分流，H=120 那一格落【出口①】")
print("   ⚠ 而主格窗要讓 H=120 摸到出口② 需 ⌊W/120⌋ ≥ 30 ⇒ W ≥ 3,600 交易日"
      "（現有 {:,} ⇒ 還差 {:,} 日 ≈ {:.2f} 年）".format(
          int(m.n_days.iloc[0]), 3600 - int(m.n_days.iloc[0]), (3600 - int(m.n_days.iloc[0])) / 243.71))
print("   ⛔ 本線【不】據此宣告四型判定失效 —— 裁定線 1235 §四 明令：在步驟③ 之前不可那樣寫。")
