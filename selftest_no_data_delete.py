#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_no_data_delete.py — ⛔ **沒有任何程式會刪掉 `data/` 底下被 git 追蹤的檔**。

    python3 selftest_no_data_delete.py      # 零相依

## 為什麼要有這一道

2026-09-15 K線分析線 §5-3 指出 `otc_adj.py --fresh` 會 `os.remove` 一個
**被 git 追蹤**的台帳檔（`data/meta/_otcadj_done.csv`），並裁：

> 「請當成**已經觸發過**來修，不要當成還沒踩到。
>  理由：它沒觸發的唯一原因是『沒有人按過那個旗標』
>  ——⛔ 那是一個**時間問題**，不是一個**設計上的保護**。」

⚠ 傷害路徑是兩段的，而兩段都不會報錯：

```
① 程式刪掉工作區那個檔
② `push_data.sh` 看到一個刪除 ⇒ 把那個刪除**搬到 main**
⇒ ⛔ 那份累積台帳（1,996 列）從 main 上消失，
   ⚠ 而下一趟「已完成 0 個」⇒ 從頭重跑 ⇒ 免費額度撐不過 ⇒ 永遠跑不完
```

⭐ 而掃描範圍量過：自 2026-09-08 起 main 上 386 個資料 commit，
`data/` 底下**零個刪除** ⇒ 這條路確實沒被走過，⛔ 而它一直通著。

## 判準（⛔ 比 AST，不比字串）

第七點⑧：這個 repo 的**註解本來就會引用那段程式碼**
⇒ 比字串的話，上面那句「原本是 `os.remove(DONE)`」自己就會讓這一道紅。
⇒ ⭐ 走 AST：找 `os.remove(...)`／`os.unlink(...)`／`shutil.rmtree(...)` 的**呼叫**，
再看那個引數**指得到哪裡**。

⚠ 而「指得到哪裡」只解析得了兩種好解的形狀，⛔ 其餘一律當**可疑**報出來：

```
① 模組層的常數（`DONE = os.path.join(_ROOT, "meta", "_otcadj_done.csv")`）
② 字面字串
⛔ 其餘（區域變數、迴圈變數、函式回傳）⇒ 報出來讓人看，⚠ 不自動放行
```

## ⭐ 母體大小自己是一道斷言（第七點⑨）

「掃了 0 支程式」與「全部都乾淨」在紙上一模一樣
⇒ 底下釘 `n_files >= 150` 與 `n_tracked >= 100`。
"""
import ast
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

_n = [0, 0]


def ck(name, cond, detail=""):
    if cond:
        _n[0] += 1
        print(f"  ok   {name}")
    else:
        _n[1] += 1
        print(f"  ✗    {name}" + (f"｜{detail}" if detail else ""))


def tracked_data_files():
    """git 追蹤中、且在 `data/` 底下的檔（⛔ 不是磁碟上有什麼）。"""
    r = subprocess.run(["git", "ls-files", "data"], cwd=HERE,
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None
    return {ln.strip() for ln in r.stdout.splitlines() if ln.strip()}


DELETERS = {("os", "remove"), ("os", "unlink"), ("shutil", "rmtree"),
            ("pathlib", "Path")}


def _consts(tree):
    """模組層 `NAME = <運算式>` 的表，值只收解得出來的字串。"""
    out = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        t = node.targets[0]
        if not isinstance(t, ast.Name):
            continue
        out[t.id] = node.value
    return out


def _resolve(expr, consts, depth=0):
    """把運算式解成一段**路徑字串**，解不出來的片段寫成 `*`。

    ⛔⛔ 第一版寫成「任何一段解不出來 ⇒ 整個回 None」，⚠ 而那讓這一道
    **對真正要擋的那一筆完全無效**：

        _ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        DONE  = os.path.join(_ROOT, "meta", "_otcadj_done.csv")

    ⇒ 第一段（`os.path.dirname(...)`）永遠解不出來 ⇒ 整條回 None
    ⇒ `os.remove(DONE)` 被歸到「可疑、不判失敗」那一堆
    ⇒ ⛔ 突變 N1（把 `os.remove(DONE)` 放回去）**全綠**。

    ⭐ 而那正是第七點⑨：**母體被判準悄悄縮小**——
    「一個都沒中」與「解析器解不動」在紙上一模一樣。

    ⇒ ⭐ 改成：解不出來的片段變 `*`，**保留後面解得出來的尾巴**，
    由呼叫端拿那截尾巴去比對追蹤清單。
    """
    if depth > 8:
        return "*"
    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        return expr.value
    if isinstance(expr, ast.Name):
        v = consts.get(expr.id)
        return _resolve(v, consts, depth + 1) if v is not None else "*"
    if isinstance(expr, ast.JoinedStr):          # f-string
        return "".join(
            v.value if isinstance(v, ast.Constant) and isinstance(v.value, str)
            else "*" for v in expr.values)
    if isinstance(expr, ast.Call):
        f = expr.func
        if (isinstance(f, ast.Attribute) and f.attr == "join"
                and isinstance(f.value, ast.Attribute)
                and f.value.attr == "path"):
            return "/".join(_resolve(a, consts, depth + 1) for a in expr.args)
    return "*"


def scan(path, consts_cache):
    """回 [(行號, 呼叫的樣子, 解出來的路徑或 None)]。"""
    src = io.open(path, encoding="utf-8").read()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    consts = _consts(tree)
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        if not (isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name)):
            continue
        if (f.value.id, f.attr) not in DELETERS:
            continue
        if f.attr == "Path":                      # pathlib.Path 本身不刪東西
            continue
        arg = node.args[0] if node.args else None
        hits.append((node.lineno, f"{f.value.id}.{f.attr}",
                     _resolve(arg, consts) if arg is not None else None))
    return hits


def main():
    print("=== selftest_no_data_delete.py ===")
    tracked = tracked_data_files()
    if tracked is None:
        # ⚠ 不在 git 工作區裡（例如 tarball）⇒ **大聲說這一層沒跑**，
        #   ⛔ 不算失敗（六點五：一條在某個環境下必然不成立的斷言
        #   等於把那個環境的整條線關掉）。
        print("⚠⚠ **這一層沒跑**：`git ls-files` 不可用（不是 git 工作區？）")
        print("   ⇒ ⛔ 不算失敗，⛔ **也不算驗過**")
        return 0

    ck("⭐ 母體：被 git 追蹤的 `data/` 檔 ≥ 100 個"
       "（⛔ 0 個跟全部乾淨長得一樣）",
       len(tracked) >= 100, f"實得 {len(tracked)}")

    files = sorted(f for f in os.listdir(HERE) if f.endswith(".py"))
    ck("⭐ 母體：掃到的 .py ≥ 150 支", len(files) >= 150, f"實得 {len(files)}")

    # ⭐ 拿每個追蹤中檔案的**尾巴**建索引：`data/meta/_x.csv` ⇒ `meta/_x.csv`、
    #   `_x.csv`。⚠ 只收 ≥ 2 段的尾巴當判準（⛔ 光一個檔名太容易誤判）。
    tails = {}
    for t in tracked:
        segs = t.split("/")
        for i in range(max(0, len(segs) - 3), len(segs) - 1):
            tails.setdefault("/".join(segs[i:]), t)

    # ⭐ 追蹤中檔案的目錄集合（給「整個目錄清空型」用）
    tdirs = {t.rsplit("/", 1)[0] for t in tracked if "/" in t}

    bad, susp, sweeps, solved = [], [], [], 0
    for fn in files:
        for lineno, how, p in scan(os.path.join(HERE, fn), None):
            norm = (p or "*").replace("\\", "/")
            tail = norm.rsplit("*", 1)[-1].lstrip("/")
            if tail and "/" in tail:
                # ── ① 具名刪除：檔名解得出來 ⇒ 直接比追蹤清單
                solved += 1
                hit = tails.get(tail)
                if hit:
                    bad.append(f"{fn}:{lineno} {how}({norm}) ⇒ 追蹤中的 {hit}")
                continue
            # ── ② 整個目錄清空型：檔名來自 `os.listdir` ⇒ ⛔ 解不出來是**必然**的，
            #    ⚠ 而**目錄**常常解得出來 ⇒ 那就足以判斷它掃的是不是追蹤中的目錄。
            #    ⭐ 這一族不判失敗（`transpose` 全量重建本來就要清空），
            #    ⛔ 改成**棘輪**：已知的幾個列在下面，多一個就紅。
            d = norm.rstrip("/*").rsplit("*", 1)[-1].strip("/")
            if d and any(t == d or t.startswith(d + "/") for t in tdirs):
                sweeps.append((fn, d, lineno))
                continue
            susp.append(f"{fn}:{lineno} {how}({norm})")

    ck("⛔⛔ 沒有任何程式刪掉**被 git 追蹤**的 `data/` 檔",
       not bad,
       "｜".join(bad) + "　⇒ 刪掉之後 `push_data.sh` 會把那個刪除搬到 main")

    # ══════════════════════════════════════════════════════════════
    # ⭐ 整個目錄清空型的**棘輪**
    #
    # ⛔ 這一族**不可以**判失敗：`transpose.py` 全量重建本來就要先清空，
    #   `backfill.py --force` 重抓某一段也是。⚠ 判它失敗 ⇒ 天天紅 ⇒ 被學會忽略。
    # ⛔ 也**不可以**不管：它們掃的正是 main 上那些累積起來的日檔
    #   ⇒ 在錯的 ref 上跑一次，那個目錄就整批消失（四點六那個會刪資料的例外）。
    # ⇒ ⭐ 折衷是棘輪：**已知的列在這裡，多一個就紅**（新的要有人看過才進來），
    #   ⚠ 而**少一個也要紅**——⛔ 一筆過期的白名單會讓下一個人以為那條路還在。
    # ══════════════════════════════════════════════════════════════
    KNOWN_SWEEPS = {
        # 檔名 → 它清空的追蹤中目錄（⚠ 每一筆都要寫清楚**誰**在守它）
        ("backfill.py", "data/universe/daily"),
        # ⇒ 守它的是 `--force` 這個旗標本身 ＋ 四點六「讀 data/ 的只准在 main 上跑」
        ("selftest_missing_rows.py", "data/universe/otcper"),
        # ⛔⛔ 這一筆是**沙箱**：`os.path.join(root, "data", "universe", …)`
        #   而 `root` 是 `tempfile.mkdtemp()`。
        # ⚠ 而這一道**看不出**那件事——它只解得出字面那幾段
        #   ⇒ ⭐ 「沙箱裡的 data/universe/otcper」與「repo 真的那個」
        #     在這一道眼裡**一模一樣**。
        # ⇒ 守它的是 `selftest_missing_rows.py` 自己那條
        #   「★ 沒有動到 repo 真的 ___」的斷言（第七點第五個陷阱的對策），
        #   ⛔ 不是這一道。
    }
    got_sweeps = {(fn, d) for fn, d, _ in sweeps}
    ck("⭐ 整個目錄清空型：沒有**新**的（多一個就要有人看過才進白名單）",
       not (got_sweeps - KNOWN_SWEEPS),
       f"⛔ 新出現：{sorted(got_sweeps - KNOWN_SWEEPS)}"
       "　⇒ 它掃的是追蹤中的目錄 ⇒ 在錯的 ref 上跑一次就整批消失")
    ck("  而且白名單裡**沒有過期的**（⛔ 過期的會讓人以為那條路還在）",
       not (KNOWN_SWEEPS - got_sweeps),
       f"⛔ 白名單有而現況沒有：{sorted(KNOWN_SWEEPS - got_sweeps)}")

    # ⭐⭐ **涵蓋率自己要印出來**（第七點⑨）：這一道的綠燈只涵蓋
    #   「路徑的尾巴解得出來」的那些呼叫 ⇒ ⛔ 不可以讓人讀成「全 repo 乾淨」。
    tot = solved + len(sweeps) + len(susp)
    print(f"  ⇒ ⭐ 這一道掃到 {tot} 個刪除呼叫，分三堆（⛔ 綠燈不涵蓋第三堆）：")
    print(f"       ① 具名刪除（檔名解得出來）      {solved} 個 ⇒ ⭐ **判失敗**")
    print(f"       ② 整個目錄清空型（目錄解得出來）{len(sweeps)} 個 ⇒ ⭐ 棘輪")
    print(f"       ③ 兩者都解不出來                {len(susp)} 個 ⇒ ⛔ **只印，不判**")
    print(f"     ⚠ ③ 幾乎全是各支自測的 tempdir，⛔ 而「幾乎」不是「全部」"
          f"——這一道對它們是**瞎的**。")
    print("     ⛔⛔ 而②也有同一個盲點：`os.path.join(root, \"data\", …)` 這種，"
          "\n        `root` 是 tempdir 還是 repo 真的根，**這一道分辨不出來**"
          "\n        ⇒ ⭐ 那一層要由各支自測自己的「★ 沒有動到 repo 真的 ___」來守。")

    # ⚠ 解不出路徑的那些**只印出來**，⛔ 不判失敗——判失敗會天天紅然後被學會忽略
    #   （四點五那條：一道天天紅的閘門等於沒有閘門）。
    if susp:
        print(f"  ⚠ 另有 {len(susp)} 處刪除的引數解不出路徑（⇒ 人看一眼，不判失敗）：")
        for x in susp[:12]:
            print(f"     {x}")
        if len(susp) > 12:
            print(f"     …（另 {len(susp) - 12} 處未印）")

    # ⭐ 反向驗這一道**真的掃得到東西**：DELETERS 至少要在 repo 裡命中過幾次，
    #   ⛔ 否則「一個都沒中」跟「AST 走法寫錯」長得一模一樣（第七點第四個陷阱）。
    ck("★ 而這一道真的掃到了刪除呼叫（⛔ 0 次代表 AST 走法壞了）",
       len(susp) + len(bad) >= 3, f"實得 {len(susp) + len(bad)} 處")

    print(f"\n[selftest] 通過 {_n[0]}｜失敗 {_n[1]}")
    return 1 if _n[1] else 0


if __name__ == "__main__":
    sys.exit(main())
