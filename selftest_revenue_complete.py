#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`mops_history.revenue_complete` 的自測。**不連網、不碰真的 data/。**

## ⛔⛔ 它擋的是一個「永遠補不到」的洞

`--fill` 用 `has_output()` 決定跳不跳過，而 `revenue` 那一支**一直是
`os.path.exists`** ⇒ 檔案只要在（哪怕只有 12% 的列）就被跳過
⇒ ⚠ 那一趟印「0 期檔、0 個失敗」，**看起來像都做完了**。

⭐ 而 `has_output` 的說明**早就記著**這個教訓（2026-09-06 那次），
⛔ 只是當時只修了 `bs`——同一個檔案裡，同一個道理只做了一半（CLAUDE.md 四點六③）。
"""
import io
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mops_history as M                                       # noqa: E402
import runlog                                                  # noqa: E402

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


# ⛔⛔ 表頭要跟**真檔逐字一樣**（2026-09-15 修）：
#   第一版寫的是 `period,stock_id,name,market,…` ⇒ 名稱在第 **2** 欄，
#   ⚠ 而真檔是 `stock_id,name,period,market,…` ⇒ 名稱在第 **1** 欄。
#   ⇒ 那時只數列數，怎麼排都對；⛔ 而 `foreign_rows()` 是**讀名稱欄**的
#     ⇒ 錯的表頭會讓 ⑤ 那一節**永遠是 0**，然後看起來像「這條判準沒用」。
#   ⭐ 這就是第七點那句的實例：**假回應要照真回應的形狀做**，
#     ⚠ 而「欄的順序」也是形狀的一部分。
HEADER = ("stock_id,name,period,market,產業別,當月營收,上月營收,去年當月營收,"
          "上月比較增減(%),去年同月增減(%),當月累計營收,去年累計營收,前期比較增減(%)")


def write(d, per, market, rows, foreign=0):
    """照真檔的形狀寫（表頭＋rows 列，其中 `foreign` 列是 `-KY`）。

    ⛔ 假的比真的簡單＝那段沒測。
    """
    p = os.path.join(d, "revenue_hist", f"{per}_{market}.csv")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8") as f:
        f.write(HEADER + "\n")
        for i in range(rows):
            nm = f"外國{i}-KY" if i < foreign else "本國X"
            f.write(f"{1000+i},{nm},{per},{market},其他,1,1,1,0,0,1,1,0\n")


def main():
    print("=" * 64)
    print("revenue_complete：判的是**抓完了沒**，⛔ 不是「檔案在不在」")
    print("=" * 64)
    d = tempfile.mkdtemp(prefix="mrev_")
    old = M.OUT
    try:
        M.OUT = d
        # 12 期正常（800 列），中間塞一期只有 12% 的
        for i in range(1, 13):
            write(d, f"2022-{i:02d}", "tpex", 800)
        write(d, "2022-06", "tpex", 96)          # ⛔ 這一期沒抓完

        print("\n── ① 核心：檔在、但列數只有鄰期的 12% ──")
        ck("⛔ 判成**沒抓完**（⚠ 舊版 `os.path.exists` 會說「完整」）",
           M.revenue_complete("2022-06", "tpex") is False,
           f"列數 {M.revenue_rows('2022-06', 'tpex')}")
        ck("★ 反向驗：正常的那幾期判成完整（⛔ 不然是每期都紅）",
           all(M.revenue_complete(f"2022-{i:02d}", "tpex")
               for i in (1, 2, 3, 11, 12)))
        ck("⛔ 檔不存在 ⇒ 沒抓完", not M.revenue_complete("2023-01", "tpex"))
        ck("`revenue_rows` 扣掉表頭", M.revenue_rows("2022-01", "tpex") == 800,
           str(M.revenue_rows("2022-01", "tpex")))

        print("\n── ② 基準是**鄰近期別**，⛔ 不是全庫中位數 ──")
        # 家數會長期漂移：早期 400、晚期 900。中間那期 420 對鄰期是正常的
        d2 = tempfile.mkdtemp(prefix="mrev2_")
        M.OUT = d2
        for i in range(1, 13):
            write(d2, f"2015-{i:02d}", "tpex", 400)
        for i in range(1, 13):
            write(d2, f"2026-{i:02d}", "tpex", 900)
        ck("⭐ 早期 400 列在**鄰期也是 400** 的情況下判成完整"
           "（⛔ 用全庫中位數 650 × 0.9 會誤判成沒抓完）",
           M.revenue_complete("2015-06", "tpex"))
        ck("★ 反向驗：把它砍到 40 列就要判成沒抓完",
           (write(d2, "2015-06", "tpex", 40) or True)
           and not M.revenue_complete("2015-06", "tpex"))
        shutil.rmtree(d2, ignore_errors=True)

        print("\n── ③ 沒有可比的對象時**不判**（⛔ 不要用猜的門檻擋）──")
        d3 = tempfile.mkdtemp(prefix="mrev3_")
        M.OUT = d3
        write(d3, "2026-01", "tpex", 3)
        ck("只有一期、沒有鄰居 ⇒ 判成完整（⛔ 不硬擋）",
           M.revenue_complete("2026-01", "tpex"))
        shutil.rmtree(d3, ignore_errors=True)

        print("\n── ④ 呼叫點：`has_output('revenue', …)` 真的走這一支 ──")
        M.OUT = d
        # ⭐ 比行為，⛔ 不比字串
        ck("`has_output` 對那個殘缺期別回 False",
           M.has_output("revenue", "2022-06", "tpex") is False)
        ck("`has_output` 對正常期別回 True",
           M.has_output("revenue", "2022-01", "tpex") is True)
    finally:
        M.OUT = old
        shutil.rmtree(d, ignore_errors=True)

    # ── ⑤ ⭐⭐ 外國企業那一段（`-KY`／`-DR`）在不在 ──
    #
    # ⛔ ①～④ 那一道比的是「我 vs 鄰居的**列數**」
    # ⇒ 對「**所有鄰居一起缺同一段**」完全免疫（實測：KY 在 280 期同時缺，
    #   而 2015-01／2020-06／2026-07 六格全部 `complete=True`）。
    # ⭐ 所以這一節驗的是**另一件事**，而且它有兩個方向，⛔ 缺一個都不行。
    print("\n── ⑤ 外國企業那一段在不在（⛔ 而它不可以變成「每期都必須有 KY」）──")
    d5 = tempfile.mkdtemp(prefix="mrev5_")
    old5 = M.OUT
    try:
        M.OUT = d5
        for i in range(1, 8):                    # 七期鄰居，每期 100 列含 10 檔 KY
            write(d5, f"2024-{i:02d}", "twse", 100, foreign=10)
        write(d5, "2024-08", "twse", 100, foreign=0)      # ⭐ 只有這一期沒有
        ck("⭐ `foreign_rows` 讀得到（⚠ 名稱在第 1 欄，含 `-KY` 就算）",
           M.foreign_rows("2024-01", "twse") == 10,
           str(M.foreign_rows("2024-01", "twse")))
        ck("⛔ 沒有那個檔 ⇒ 回 None（⚠ 0 與「沒有檔」是兩件事）",
           M.foreign_rows("1999-01", "twse") is None)
        ck("⭐⭐ 列數正常、⛔ 而**少了外國企業那一段** ⇒ 判成**不完整**"
           "（⇒ `--fill` 會去補它）",
           M.revenue_complete("2024-08", "twse") is False)
        ck("  而鄰居那幾期照樣完整（⛔ 不可以把整批判紅）",
           M.revenue_complete("2024-03", "twse") is True)

        # ⛔⛔ 反向：**全部都沒有**的時候一律放行（absent ≠ zero，CLAUDE.md 五點三）
        d6 = tempfile.mkdtemp(prefix="mrev6_")
        M.OUT = d6
        for i in range(1, 9):
            write(d6, f"2024-{i:02d}", "tpex", 100, foreign=0)
        ck("⭐⭐ **所有期別都沒有**外國企業 ⇒ 一律放行"
           "（⛔ 否則真的沒有 KY 的期別會變成永遠補不完）",
           M.revenue_complete("2024-08", "tpex") is True)
        shutil.rmtree(d6, ignore_errors=True)

        # ⭐ 呼叫點：`has_output` 真的走這一支（第七點③：測了判準沒測呼叫點）
        M.OUT = d5
        ck("`has_output('revenue', …)` 對「少了 KY 那一段」的期別回 False",
           M.has_output("revenue", "2024-08", "twse") is False)
    finally:
        M.OUT = old5
        shutil.rmtree(d5, ignore_errors=True)

    # ── ⑦ ⭐ `foreign_summary()`：runlog 那一格的數字（⛔ 它本來住在 main() 裡，測不到）──
    print("\n── ⑦ runlog 要講得出外國企業那一段到底進來了沒 ──")
    d7 = tempfile.mkdtemp(prefix="mrev7_")
    old7, oldrl = M.OUT, runlog.PATH
    rlp = os.path.join(d7, "_last_run.md")
    repo_rl = os.path.join(HERE, "data", "meta", "_last_run.md")
    before = (io.open(repo_rl, "rb").read() if os.path.isfile(repo_rl) else None)
    try:
        M.OUT = d7
        runlog.PATH = rlp
        write(d7, "2024-01", "twse", 100, foreign=12)
        write(d7, "2024-02", "twse", 100, foreign=0)
        write(d7, "2024-01", "tpex", 80, foreign=3)
        n, zero, tot = M.foreign_summary()
        ck("⭐ 有值的期別檔數（2 個）", n == 2, str(n))
        ck("⭐ 0 列的那一個被列出來（⇒ 讀的人看得到是哪一期）",
           zero == ["2024-02_twse"], str(zero))
        ck("⭐ 合計列數 12+3=15", tot == 15, str(tot))
        # ⛔ 全 0 的那一種：判準是「**有沒有任何一期有**」，⛔ 不是「每一期都要有」
        d8 = tempfile.mkdtemp(prefix="mrev8_")
        M.OUT = d8
        write(d8, "2024-01", "twse", 100, foreign=0)
        n2, _z2, t2 = M.foreign_summary()
        ck("⛔ 全庫一列外國企業都沒有 ⇒ n=0（⇒ runlog 那一格會 ✗）",
           n2 == 0 and t2 == 0, f"n={n2} tot={t2}")
        shutil.rmtree(d8, ignore_errors=True)
    finally:
        M.OUT, runlog.PATH = old7, oldrl
        shutil.rmtree(d7, ignore_errors=True)
    # ★ 沒有動到 repo 真的 `_last_run.md`（CLAUDE.md 第七點第五個：沙箱導走漏一個的代價）
    after = (io.open(repo_rl, "rb").read() if os.path.isfile(repo_rl) else None)
    ck("★ 沒有動到 repo 真的 `data/meta/_last_run.md`（逐位元）", before == after)

    # ⭐ 呼叫點：`main()` 真的把它接到一條 runlog `check` 上
    #   ⚠ 比 **AST 且限定在 `main()` 裡**，⛔ 不是全檔 grep 字串
    #     （第七點第八個：那幾個字在上面的註解裡也有一份）
    import ast as _ast
    _src = io.open(os.path.join(HERE, "mops_history.py"), encoding="utf-8").read()
    _fmain = next((f for f in _ast.walk(_ast.parse(_src))
                   if isinstance(f, _ast.FunctionDef) and f.name == "main"), None)
    _calls = [n for n in _ast.walk(_fmain) if isinstance(n, _ast.Call)]
    ck("⭐ `main()` 裡真的叫了 `foreign_summary()`",
       any(getattr(c.func, "id", "") == "foreign_summary" for c in _calls))
    ck("⭐ 而且 `main()` 開了一個 runlog 區塊（⛔ 不是只印到 log——log 會捲掉）",
       any(getattr(getattr(c.func, "value", None), "id", "") == "runlog"
           and getattr(c.func, "attr", "") == "Run" for c in _calls))
    # ⛔⛔ 第一版寫「`main()` 裡有任何一個 `.check(`」⇒ 突變 K6（把**那一條**
    #   改成 `info`）**全綠**——因為 `main()` 本來就有別的 `.check(`。
    #   ⭐ 第七點那句的又一次：**斷言要釘住那一條**，⛔ 不是釘住那一族。
    def _mentions(node, name):
        return any(isinstance(x, _ast.Name) and x.id == name
                   for x in _ast.walk(node))
    _checks_pf = [c for c in _calls
                  if getattr(c.func, "attr", "") == "check"
                  and any(_mentions(a, "per_f") for a in c.args)]
    ck("⭐⭐ 而外國企業那個數字真的接到一條 `.check(` 上"
       "（⛔ 只有 `info` 的話它永遠不會紅）",
       len(_checks_pf) == 1, f"實得 {len(_checks_pf)} 條")

    # ── ⑥ ⭐ 而「第一次整批重抓」靠的是 workflow 那顆開關，⛔ 不是這道判準 ──
    #   ⚠ 這一條釘的是**呼叫點**：`feeds.yml` 真的有一條路會把 `--fill` 拿掉。
    #   ⛔ 不比原始碼裡有沒有 `mops_fill` 這幾個字（第七點第八個：註解裡也有一份）
    #   ⇒ 比 YAML 解析後的 inputs，並比那一段 shell 的**行為**。
    print("\n── ⑥ `feeds.yml` 有一顆按得到的開關可以拿掉 `--fill` ──")
    wf = os.path.join(HERE, ".github", "workflows", "feeds.yml")
    src = io.open(wf, encoding="utf-8").read()
    ck("⭐ `mops_fill` 是一個 workflow input（⇒ 派工按得到）",
       "\n      mops_fill:\n" in src)
    ck("⭐ 而 `--fill` 是**條件加上去**的（⛔ 不是寫死在那一行）",
       'ARGS="$ARGS --fill"' in src
       and "--kind both --start 2015-01 --sleep 3 --fill" not in src)
    # ⭐ 拿那段 shell 真的跑一次（⛔ 讀字串是「中間點」，跑一次才是終點）
    import re as _re
    import subprocess as _sp
    m = _re.search(r'ARGS="--run --kind .*?\n\s*python mops_history\.py \$ARGS',
                   src, _re.S)
    seg = m.group(0) if m else ""
    for want_fill, val in ((True, "true"), (False, "false")):
        sh = seg.replace("${{ inputs.mops_kind || 'both' }}", "both")
        sh = sh.replace("${{ inputs.mops_fill }}", val)
        sh = sh.replace("python mops_history.py $ARGS", 'echo "RAN $ARGS"')
        r = _sp.run(["bash", "-c", sh], capture_output=True, text=True)
        # ⛔⛔ 只能看 `RAN ` 那一行（2026-09-15 當場踩到）：
        #   `mops_fill=false` 那一支會印一句**警語**，而警語裡逐字寫著 `--fill`
        #   ⇒ 直接 `"--fill" in r.stdout` 兩種情況都是真 ⇒ 這條斷言永遠綠。
        #   ⭐ 第七點第八個的縮影：**那幾個字在說明文字裡也有一份。**
        ran = [ln for ln in r.stdout.splitlines() if ln.startswith("RAN ")]
        got = bool(ran) and ("--fill" in ran[0])
        ck(f"  mops_fill={val} ⇒ {'帶' if want_fill else '**不帶**'} `--fill`",
           got is want_fill, r.stdout.strip()[-160:])

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
