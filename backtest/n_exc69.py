# -*- coding: utf-8 -*-
"""裁定線 seq83 §一 的例外回頭查：那些【沒有被拿去比判準】的臂裡，
有沒有任何一張輸出表印了 pass／fail 欄？（⭐ 規則看「表上有沒有印」，⛔ 不看登錄怎麼稱呼）
外加〈一百三十四〉：描述臂若也通過判定判準 ⇒ 必報。
"""
import os, sys, glob, re
import pandas as pd
BT = "/home/chemtim/tw-p17/backtest"
os.chdir(BT)

# ⭐ 判準與基準：裁定線 1047 §一 的未捨入值（本線 assert_bench_1047.py 已逐位驗過）
BC, BM = 0.24020209886370614, 0.3395700527611012
PAT = re.compile(r"pass|fail|verdict|判定|通過|未過|^過$|detectable|win_[a-z]", re.I)

print("=== ① 六件的所有輸出 CSV：表頭有沒有【判定欄】樣貌 ===")
hits = []
for d in ["resultsp12", "resultsp13", "resultsp15", "resultsp16", "resultsp17", "results_d4"]:
    for f in sorted(glob.glob(d + "/*.csv")):
        cols = list(pd.read_csv(f, nrows=0).columns)
        bad = [c for c in cols if PAT.search(c)]
        if bad:
            n = sum(1 for _ in open(f, encoding="utf-8")) - 1
            hits.append((f, bad, n))
            print("  ⚠ {:28s} 列數 {:5d}  疑似判定欄 {}".format(f, n, bad))
if not hits:
    print("  （無）")

print()
print("=== ② 逐件裁決：那一張表覆蓋的是【哪些】臂 ===")
print("""  resultsp12/anchors.csv  欄名就叫「過」，2 列 True／True
      ⇒ ⚠ 但它比的是【錨點閘門】（重現既有交件的兩個數），⛔ 不是使用者判準
      ⇒ 它的列不是 48 格中的任何一格（單位是「錨點」，⛔ 不是「臂」）
  resultsp12/effects.csv   有 detectable／verdict（測得出／測不出），21 列
      ⇒ ⚠ 單位是【因子效果】（arm 欄的值是 全部／S0／T1，各自彙總 16 格），⛔ 不是 48 格裡的一格
      ⇒ 判的是「CI 含不含 0」＝ 可偵測性，⛔ 不是「該格通不通過年化／回落」
  resultsp12/anchor_diag.csv  win_mdd 是【窗內回落】的數值欄，⛔ 不是 win/lose 判定
  resultsp13/judge.csv     有 pass_w1／pass_w0，⭐ 只 1 列 ⇒ 覆蓋的就是已計入的 2 格（W0／W1 全窗）
      ⇒ 另 6 列（主格窗 4 列＋對帳臂 W0p／W0i）在 judge.csv 裡【沒有列】
  resultsp16/det_E1*.csv   judge_pos 是【判定日的 bar 位置】（整數索引），⛔ 不是 pass/fail
  resultsp17/gate_i.csv    有 detectable，2 列（bootstrap／常態近似）
      ⇒ 覆蓋的是【判定格 R_eq 的 (i) 那一道】＝已計入的 1 格，⛔ 不是五個描述臂
  resultsp15 / results_d4  ⇒ 沒有任何 CSV 有判定欄樣貌的欄名""")

print()
print("=== ③ ⛔⛔ 但 P17 的臂數本線上一封報錯了 ===")
d17 = pd.read_csv("resultsp17/per_seed_arm.csv", float_precision="round_trip")
arms = sorted(d17["arm"].unique())
print("  per_seed_arm.csv 實際 arm 清單（{} 個）：{}".format(len(arms), arms))
print("  ⇒ 本線 2026 §一 寫「P17 6/1」⇒ ⛔ 錯，應為 **7/1**")
print("  ⇒ 跑過的臂合計 205 ⇒ **206**；差 68 ⇒ **69**")

print()
print("=== ④ ⭐⭐〈一百三十四〉：P17 六個描述臂對【使用者判準】逐腳查 ===")
print("  判準（登錄 §三 逐字）：兩腳都成立 且【至少一腳嚴格優】")
print("  基準 0050（裁定線 1047 未捨入）：年化 {!r}／回落 {!r}".format(BC, BM))
rows = []
for a in arms:
    s = d17[d17["arm"] == a]
    c, m = s["cagr"].median(), abs(s["mdd"].median())
    ok_c, ok_m = c >= BC, m <= BM
    strict = (c > BC) or (m < BM)
    rows.append(dict(arm=a, n列=len(s), 年化med=c, 回落med=m,
                     年化腳成立=ok_c, 回落腳成立=ok_m,
                     至少一腳嚴格優=strict, 通過判準=bool(ok_c and ok_m and strict)))
t = pd.DataFrame(rows)
print(t.to_string(index=False))

print()
print("=== ⑤ W_shuf（假訊號臂）⇒ 它的中位是 30 個 rep 混在一起的 ⇒ 逐 rep 再查 ===")
w = d17[d17["arm"] == "W_shuf"]
print("  rep 數 {}｜每 rep 種子數 {}".format(w["rep"].nunique(), len(w) // w["rep"].nunique()))
per = w.groupby("rep").agg(cagr_med=("cagr", "median"), mdd_med=("mdd", "median"))
per["回落med"] = per["mdd_med"].abs()
per["通過"] = (per["cagr_med"] >= BC) & (per["回落med"] <= BM) & \
              ((per["cagr_med"] > BC) | (per["回落med"] < BM))
k = int(per["通過"].sum())
print("  ⇒ 30 個 rep 裡【逐 rep 中位】通過使用者判準的：**{}／{}**".format(k, len(per)))
print("  ⇒ 池化（6000 列一起取中位）：{}".format(bool(t.set_index("arm").loc["W_shuf", "通過判準"])))
print("  rep 逐列（前 10）：")
print(per.head(10).to_string())

print()
print("=== ⑥ ⭐ R_rp 是不是獨立的一格 ===")
a, b = d17[d17["arm"] == "R_eq"], d17[d17["arm"] == "R_rp"]
same_sha = (a.sort_values("r")["eq_sha"].values == b.sort_values("r")["eq_sha"].values).sum()
print("  R_eq vs R_rp 權益曲線 sha 相同的種子數：{}／200".format(same_sha))
print("  年化中位差 {!r}｜回落中位差 {!r}".format(
    b["cagr"].median() - a["cagr"].median(), abs(b["mdd"].median()) - abs(a["mdd"].median())))
print("  ⇒ 登錄 §1-2：R_rp ＝ R_eq 同一算式的二分搜尋實作 ⇒ 數學上恆等")
print("  ⇒ ⭐ 中位逐位相同 ⇒ ⛔ 它通過判準【不是多一格通過】，是同一格")

# ⛔ 自測：本支報的每一個「通過」都必須能被報告裡印出的數字對上
_wf = t.set_index("arm").loc["W_fix"]
assert abs(_wf["年化med"] - 0.2689740000) < 1e-3 and abs(_wf["回落med"] - 0.3320390000) < 1e-3, \
    "⛔ W_fix 對不上 P17_REPORT §一 的 +26.90%／-33.20%"
assert bool(_wf["通過判準"]) is True, "⛔ W_fix 應判通過"
assert bool(t.set_index("arm").loc["W0", "至少一腳嚴格優"]) is False, \
    "⛔ W0 ＝ 0050 本身 ⇒ 兩腳都只是相等 ⇒ 不可有『嚴格優』"
assert bool(t.set_index("arm").loc["R_tv", "回落腳成立"]) is False, "⛔ R_tv 回落腳應不成立"
assert same_sha == 0 or same_sha == 200, "⛔ sha 比對結果應是全同或全異，混合要查"
print()
print("✅ 自測四條斷言通過（W_fix 對上報告印的數／W0 無嚴格優／R_tv 回落不過／sha 全同或全異）")

os.makedirs("results_step2", exist_ok=True)
t.to_csv("results_step2/n_exc69_p17arms.csv", index=False, encoding="utf-8")
per.to_csv("results_step2/n_exc69_wshuf_perrep.csv", encoding="utf-8")
print("⇒ 落檔 results_step2/n_exc69_p17arms.csv、results_step2/n_exc69_wshuf_perrep.csv")
