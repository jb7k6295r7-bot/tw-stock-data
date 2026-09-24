# -*- coding: utf-8 -*-
"""回覆資料庫線 20260924-2035 §五：本線讀到「9103 的 kind == 'stock'」的檔名、行號、ref。

⭐ 結論先寫：不是資料庫線那棵樹的 bug ——
   是【本線分支的 data/ 快照】比 main 舊（本線硬規矩⑤：分支的 data/ 永遠比 main 舊）。
⛔ 而後果不是零：本線的回測母體在這份快照上真的含 7 檔 -DR（main 上是 0 檔）。
"""
import os, subprocess, sys
import pandas as pd

ROOT = os.path.expanduser("~/tw-p17")
os.chdir(ROOT)
P = "data/meta/stocks.csv"
DRS = ["9103", "9105", "9106", "9110", "9136", "9157", "9188"]


def sh(*a):
    return subprocess.run(a, capture_output=True, text=True).stdout.strip()


print("=== ① 本線讀到的那一份是誰 ===")
branch = sh("git", "rev-parse", "--abbrev-ref", "HEAD")
head = sh("git", "rev-parse", "HEAD")
blob_ws = sh("git", "hash-object", P)
blob_head = sh("git", "rev-parse", "HEAD:" + P)
last = sh("git", "log", "-1", "--date=iso", "--format=%H|%ad|%s", "--", P)
print("  絕對路徑      {}/{}".format(ROOT, P))
print("  分支          {}".format(branch))
print("  HEAD          {}".format(head))
print("  檔案 blob sha {}".format(blob_ws))
print("  HEAD 記的 blob {}".format(blob_head))
assert blob_ws == blob_head, "⛔ 工作樹與 HEAD 不一致 ⇒ 要先查是誰改的"
print("  ⇒ ✅ 工作樹 ＝ HEAD（⛔ 不是本機未提交的手改）")
print("  最後動到它的 commit  {}".format(last))

print()
print("=== ② 那幾行的原文（逐字，含行號）===")
with open(P, encoding="utf-8") as f:
    lines = f.read().splitlines()
print("  第 1 行（表頭）: {}".format(lines[0]))
for i, ln in enumerate(lines, start=1):
    sid = ln.split(",", 1)[0]
    if sid in DRS:
        print("  第 {} 行: {}".format(i, ln))

print()
print("=== ③ 與 origin/main 對照 ===")
main = sh("git", "rev-parse", "origin/main")
mtxt = sh("git", "show", "origin/main:" + P)
print("  origin/main {}".format(main))
for ln in mtxt.splitlines():
    if ln.split(",", 1)[0] in DRS:
        print("    {}".format(ln))


def universe(txt):
    rows = [l.split(",") for l in txt.splitlines()[1:] if l]
    keep = [r for r in rows if r[3] == "stock" and r[2] in ("twse", "tpex")]
    dr = [r[0] for r in keep if "-DR" in r[1]]
    return len(keep), dr


n_b, dr_b = universe("\n".join(lines))
n_m, dr_m = universe(mtxt)
print()
print("=== ④ ⛔⛔ 後果不是零：兩棵樹的回測母體（kind=='stock' ∧ market∈{twse,tpex}）===")
print("  本線分支快照  {:,} 檔｜其中名稱含 -DR 的 {} 檔：{}".format(n_b, len(dr_b), "、".join(dr_b)))
print("  origin/main   {:,} 檔｜其中名稱含 -DR 的 {} 檔".format(n_m, len(dr_m)))
assert len(dr_m) == 0, "⛔ main 上竟然還有 -DR 落在 stock：{}".format(dr_m)
assert len(dr_b) == 7, "⛔ 本線快照的 -DR 檔數變了：{}".format(dr_b)
print("  ⇒ ⭐ 資料庫線 §一 的「母體零污染」對【今天的 main】成立 ✅")
print("  ⇒ ⛔ 但對【本線已交件所用的那棵樹】不成立：真的有 7 檔")

print()
print("=== ⑤ ⭐ 那 7 檔實際污染到多少：P4 面板的 eligible ===")
pan = pd.read_csv("backtest/resultsp4/panel.csv.gz", dtype={"stock_id": str},
                  usecols=["stock_id", "eligible"])
tot = 0
hit = []
for s in DRS:
    sub = pan[pan["stock_id"] == s]
    e = int(sub["eligible"].astype(bool).sum()) if len(sub) else 0
    tot += e
    if e:
        hit.append(s)
    print("  {}：面板列數 {:4d}｜eligible True {:4d}".format(s, len(sub), e))
print("  ⇒ 合計 {} 股-月，來自 {} 檔：{}".format(tot, len(hit), "、".join(hit)))
assert hit == ["9103", "9105"], "⛔ 進得了 eligible 的不只 9103／9105：{}".format(hit)
assert tot == 50, "⛔ 污染的股-月數變了：{}".format(tot)
print("  ⇒ ⭐⭐ 這正是 D4 seq17 §4-3 為什麼非要剔兩檔：")
print("     2,039 母體 ＝【窗內曾 eligible 的 1,586】∪【新增 453】")
print("     ⇒ 9103／9105 從「曾 eligible」那一半進來 ⇒ elig_d4 剔 2 檔 ⇒ 2,037 ✅")
print("     ⇒ 其餘 5 檔（9106／9110／9136／9157／9188）eligible 恆 0 ⇒ ⛔ 本來就沒進 2,039")

print()
print("=== ⑥ ⚠ 順手訂正資料庫線的日期：flip 不是 09-17 ===")
print("  main 上 data/meta/stocks.csv 逐版查 9103 的 kind：")
hist = sh("git", "log", "--date=short", "--format=%H|%ad", "origin/main", "--", P).splitlines()[:12]
prev = None
for h in hist:
    sha, dt = h.split("|")
    k = sh("git", "show", sha + ":" + P)
    kv = [l.split(",")[3] for l in k.splitlines() if l.startswith("9103,")]
    kv = kv[0] if kv else "?"
    print("    {} {}  kind={}".format(sha[:9], dt, kv))
    if prev and prev[2] != kv:
        print("       ⭐⭐ 變動點就在這兩版之間：{} {} (dr) ← {} {} (stock)".format(
            prev[0][:9], prev[1], sha[:9], dt))
    prev = (sha, dt, kv)
print("  ⇒ ⛔ 資料庫線 2035 §五 寫「2026-09-17 之前它真的是 stock」⇒ 日期要改")
print("  ⇒ ✅ 而他們的【假設】是對的：本線讀的就是 flip 之前的快照")
