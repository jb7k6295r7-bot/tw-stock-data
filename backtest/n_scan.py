# -*- coding: utf-8 -*-
"""N 盤點改成【掃 results* 目錄】（⇐ 台股策略線 2130 §一）＋ 逐項查證欄的語意。

⛔ 舊做法（本線 2026）照【指名欄】逐件打開 cells.csv 去數 ⇒ 漏掉沒被指名的件
   （2040 漏 22 格、2130 漏 P1）⇒ 成因是「表的件來自手列的清單」。
✅ 新做法：56 個 results* 目錄全掃；而**每一個命中都要查欄的語意**，⛔ 不可看欄名就算。

⭐⭐ 本支最重要的一件事：欄名 `win` 有三種完全不同的意思
   ① 布林的「贏過 0050 沒有」        ⇒ P1／P6／P7／P9ⓑ／P11／P13／研究十三(b)
   ② **窗名**（主格窗／全窗）          ⇒ resultsp12 的 cells／effects／attribution／cells_T1w
   ③ **勝率**（0.43 這種比例）        ⇒ resultsp8/a_deciles.csv、resultsp1/m_windows.csv(win_rate)
   ⇒ ⛔ 只看欄名會把 ② ③ 當成判準格 ⇒ 分母暴增而且是錯的
"""
from __future__ import annotations
import os
import io
import re
import glob
import pandas as pd

os.chdir(os.path.expanduser("~/tw-p17/backtest"))
COL = re.compile(r"^(win|win_[a-z0-9_]*|pass|pass_[a-z0-9_]*|通過|贏|過)$", re.I)
TRUEY = {"true", "1", "1.0", "是", "通過", "贏"}
FALSEY = {"false", "0", "0.0", "否", "沒通過", "沒贏"}

rows = []
for d in sorted(x for x in glob.glob("results*") if os.path.isdir(x)):
    for p in sorted(glob.glob(os.path.join(d, "*.csv"))):
        try:
            cols = list(pd.read_csv(p, nrows=0).columns)
        except Exception:
            continue
        hits = [c for c in cols if COL.match(str(c).strip())]
        if not hits:
            continue
        try:
            df = pd.read_csv(p, float_precision="round_trip")
        except Exception:
            continue
        for c in hits:
            v = df[c].astype(str).str.strip().str.lower()
            uniq = sorted(set(v))[:4]
            is_bool = set(v) <= (TRUEY | FALSEY)
            is_num = False
            try:
                pd.to_numeric(df[c])
                is_num = True
            except Exception:
                pass
            kind = ("① 布林判準" if is_bool else
                    "③ 數值（比例／量）" if is_num else
                    "② 文字標籤（⛔ 不是判準）")
            rows.append(dict(目錄=d, 檔=os.path.basename(p), 欄=c, 列數=len(df),
                             語意=kind, 取值樣本="／".join(uniq),
                             真值數=int(v.isin(TRUEY).sum()) if is_bool else -1))

T = pd.DataFrame(rows)
print("=== ① 全部命中，按【欄的語意】分開（⭐ 這一步是本支的重點）===")
for k, g in T.groupby("語意"):
    print()
    print("  ── {}（{} 個欄）".format(k, len(g)))
    print(g[["目錄", "檔", "欄", "列數", "真值數", "取值樣本"]].to_string(index=False))

print()
print("=== ② ⛔ 逐項剔除（⛔ 不是判準格的，逐條寫明理由）===")
EXCL = {
    "resultsp12": "⛔ `win` 欄是【窗名】（主格窗／全窗）⇒ 誤命中；P12 本來就是歸屬診斷、未比判準",
    "resultsp8": "⛔ `win`／`win50`／`lose20` 是【勝率】；P8 的判準是三條可偵測性，⛔ 不是對 0050",
    "results_step2": "⛔ 本線 2026-09-24 今晚自己的掃描輸出（假訊號臂通過率）⇒ ⛔ 不是交件",
    "resultsc3": "⛔ 加密（C3）⇒ 另建分母",
    "resultsc4": "⛔ 加密（C4）⇒ 另建分母",
}
for k, v in EXCL.items():
    print("  {:16s} {}".format(k, v))
print("  {:16s} {}".format("resultsp1/m_windows.csv", "⛔ `win_rate` 是比率 ⇒ 誤命中"))
print("  {:16s} {}".format("resultsp12/anchor_diag", "⛔ `win_mdd` 是窗內回落值 ⇒ 誤命中"))
print("  {:16s} {}".format("resultsp12/anchors.csv", "⛔ 「過」是【錨點閘門】（重現既有交件）⇒ 不是判準"))
print("  {:16s} {}".format("results13_*_0914", "⛔ 重跑版本（同一批格、不同資料快照）⇒ 不是新格"))
print("  {:16s} {}".format("resultsp13/judge.csv", "⭐ 只 1 列，覆蓋的是已計入的 2 格"))

print()
print("=== ③ ⭐⭐ 剩下的：真的印了「對 0050 過／不過」的布林判準格 ===")
KEEP = [
    ("P1 組合層槽數下探", "resultsp1/portfolio.csv", "win"),
    ("P6", "resultsp6/cells.csv", "win"),
    ("P7 停損四族（主表）", "resultsp7/cells.csv", "win"),
    ("P7 敏感度", "resultsp7/sensitivity.csv", "win"),
    ("P7 BASELINE", "resultsp7/baseline_gateB.csv", "win"),
    ("P9ⓑ 弱勢減碼", "resultsp9/cells.csv", "win_self"),
    ("P11 訊號集×選擇率", "resultsp11/cells.csv", "win"),
    #  ⛔ P13 的 arms.csv `win` 欄也是【窗名】（主格窗／全窗）⇒ ⛔ 不可放進來
    #     ⭐ P13 真正的判準在 judge.csv（pass_w1／pass_w0，1 列覆蓋已計入的 2 格）
    ("P13 只換權重（判準在 judge.csv）", "resultsp13/judge.csv", "pass_w1"),
    ("P14 0050 進組合", "resultsp14/w_summary.csv", "通過"),
    ("研究十三／PREREG10", "results13/portfolio.csv", "win"),
    ("研究十三b／PREREG11", "results13b/portfolio.csv", "win"),
]
tot = 0
out = []
for name, path, col in KEEP:
    df = pd.read_csv(path, float_precision="round_trip")
    v = df[col].astype(str).str.strip().str.lower()
    t = int(v.isin(TRUEY).sum())
    tot += len(df)
    out.append(dict(件=name, 檔=path, 欄=col, 判準格=len(df), 其中通過=t))
O = pd.DataFrame(out)
print(O.to_string(index=False))
print()
print("  ⇒ 這 {} 張表合計 **{} 格**（⛔ 而這只是「有布林判準欄的 csv」，⛔ 不是 N 的全部）".format(len(O), tot))
print("  ⛔ 本支第一版把 resultsp13/arms.csv 的 `win` 也算進來 ⇒ 它其實也是【窗名】")
print("     ⇒ ⭐ 被 §① 的『分語意』那一步抓到 ⇒ 已換成 judge.csv（P13 真正的判準表）")

print()
print("=== ④ ⭐ 對上現行的 N_組合 ＝ 160 ===")
print("""  160 ＝ 137（本線 2026 逐件）＋ 22（台股 2040：P7 敏感度4＋BASELINE6、PREREG9 12）＋ 1（W_fix）
  ⇒ ⭐ 本掃描查出【兩件】從來沒進過任何一版分母：
       ・P1  resultsp1/portfolio.csv ⇒ **44 格**（win 3 真：AND N30 null／N40 null／N40 relvol）
         ⚠ 台股策略線 2130 估「≥179」＝ 160＋19 ⇒ ⛔ 少估了：實際是 **44**
         ⭐ 結構（從檔案自己數）：2 set ×（8 N × 2 rule ＝ 16　＋　N=8 的 d∈{1,2,3} × 2 rule ＝ 6）＝ 44
       ・P6  resultsp6/cells.csv     ⇒ **8 格**（win 全 False）⇒ ⛔ 本線與台股策略線【兩邊都沒數到】
  ⇒ ⇒ N_組合 ≥ 160 ＋ 44 ＋ 8 ＝ **212**（⛔ 本線不裁，只報數）""")

print()
print("=== ⑤ ⏳ 一件請裁定線裁（本線不自取）===")
p3 = io.open("resultsp3/summary.md", encoding="utf-8").read()
n3 = sum(1 for l in p3.split("\n")
         if l.startswith("|") and re.search(r"仍沒贏|不再贏|仍贏|贏過|沒贏", l))
print("""  resultsp3/summary.md（PREREGP3 閒置資金放 0050 vs 空手）印了 {} 個表格列，
  逐格寫「H2 成立：乙下仍沒贏」「H1 成立：乙不再贏」「H1 否證：乙仍贏」
  ⇒ ⭐ 它確實印了【對 0050 的贏／沒贏】
  ⇒ ⏳ 但那些格是【P1 的同一批組態換成「閒置資金放 0050」這一臂】
     ⇒ 算新格（＋{}）還是算 P1 那 44 格的另一臂？⇒ **裁定線的格子**，⛔ 本線不自取""".format(n3, n3))

print()
print("=== ⑥ ⏳ 台股策略線 2130 §二 的 P1b：本線只報事實 ===")
p1b = io.open("resultsp1b/P1B_REPORT.md", encoding="utf-8").read()
n1b = sum(1 for l in p1b.split("\n") if l.startswith("|") and re.search(r"通過|沒通過", l))
print("  resultsp1b/P1B_REPORT.md 印了 {} 個表格列的「通過／沒通過」".format(n1b))
print("  ⚠ 而它判的是【CI 半寬能不能壓到 0.585pp】⇒ ⛔ 不是對 0050 的判準")
print("  ⇒ ⏳ 算不算 N ＝ 裁定線的格子（台股策略線 2130 §二 已請裁）")

os.makedirs("results_step2", exist_ok=True)
T.to_csv("results_step2/n_scan_columns.csv", index=False, encoding="utf-8")
O.to_csv("results_step2/n_scan_keep.csv", index=False, encoding="utf-8")
print()
print("⇒ 落檔 results_step2/n_scan_columns.csv（{} 列，含誤命中）、n_scan_keep.csv（{} 列）".format(len(T), len(O)))

# ⛔ 自測：三種語意都必須真的出現過 —— 否則「分語意」這一步是空轉的
ks = set(T["語意"])
assert "① 布林判準" in ks, "⛔ 沒有布林判準欄 ⇒ 掃描壞了"
assert "② 文字標籤（⛔ 不是判準）" in ks, "⛔ 沒抓到文字標籤型的 win ⇒ 分語意這步空轉"
assert "③ 數值（比例／量）" in ks, "⛔ 沒抓到數值型的 win ⇒ 分語意這步空轉"
assert len(pd.read_csv("resultsp1/portfolio.csv")) == 44, "⛔ P1 不是 44 列"
assert len(pd.read_csv("resultsp6/cells.csv")) == 8, "⛔ P6 不是 8 列"
print("✅ 自測四條：三種語意都真的出現過（⇒ 分語意不是空轉）｜P1 44 列｜P6 8 列")
