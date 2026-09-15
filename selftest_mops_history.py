#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mops_history.py 的 `ledger_from_disk` 自測。**不連網、不碰 repo 的 data/。**

★ 為什麼要有這一支
────────────────────────────────
`data/mops/_hist_status.csv` 是回補歷史的狀態帳本。寫它那一段的註解寫著
「**這是資料庫的狀態，不只是這一趟**」——但 `--fill`／`--resume` 會先跳過
已經有檔的期別，那些**永遠不會進這一趟的 state**。

2026-09-08 實測：資料庫 2015-01 起全數回補完成（revenue_hist 280 檔、
fs_hist 與 bs_hist 各 372 檔），帳本卻只有 **6 列而且全是 pending**。
讀的人會以為整批都還沒補。**註解說的是意圖，程式做的是另一件事**——
一份宣稱是整體、實際只有這一趟的帳本，比沒有帳本更糟。

所以收尾時要用「真的寫出來的檔」這個直接證據補齊。第 1 節就是釘這件事。

跑法：python3 selftest_mops_history.py（不連網、不需要資料）
"""
import io
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ok = fail = 0

REPO_LEDGER = os.path.join(HERE, "data", "mops", "_hist_status.csv")


def chk(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ✓ {label}" + (f"　（{detail}）" if detail else ""))
    else:
        fail += 1
        print(f"  ✗ {label}" + (f"　（{detail}）" if detail else ""))


def touch(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8").write("stock_id\n")


def main():
    import mops_history as H

    tmp = tempfile.mkdtemp(prefix="histtest_")
    led_before = (io.open(REPO_LEDGER, "rb").read()
                  if os.path.isfile(REPO_LEDGER) else None)
    real_out = H.OUT
    H.OUT = tmp
    try:
        # 造出跟真的一樣的檔名形狀
        touch(os.path.join(tmp, "revenue_hist", "2015-01_twse.csv"))
        touch(os.path.join(tmp, "revenue_hist", "2015-01_tpex.csv"))
        for tag in ("basi", "bd", "ci"):
            touch(os.path.join(tmp, "fs_hist", f"2015Q1_{tag}_twse.csv"))
        touch(os.path.join(tmp, "bs_hist", "2015Q1_ci_tpex.csv"))

        print("── 1. ★ 這一趟沒碰到、但檔案已經在的期別要補成 ok ──")
        st = {}
        n = H.ledger_from_disk(st)
        chk("★ 空帳本被補齊（--fill 跳過的期別不會消失）", n == 4, f"補進 {n} 筆")
        chk("revenue 兩個市場都補成 ok",
            st.get(("revenue", "2015-01", "sii"), ("",))[0] == "ok"
            and st.get(("revenue", "2015-01", "otc"), ("",))[0] == "ok")
        chk("★ 市場名有轉換（檔名 twse/tpex → 帳本 sii/otc）",
            ("revenue", "2015-01", "sii") in st and ("revenue", "2015-01", "otc") in st,
            str(sorted(k[2] for k in st)))
        chk("fs 三張業別表算成同一期的 3 張",
            st[("fs", "2015Q1", "sii")][1].startswith("3 張表"),
            st[("fs", "2015Q1", "sii")][1][:12])
        chk("bs 的三段檔名也解析得對", ("bs", "2015Q1", "otc") in st)
        chk("note 有講清楚證據等級",
            "不證明內容完整" in st[("bs", "2015Q1", "otc")][1])

        print("\n── 2. 有檔但這一趟失敗：狀態是 ok，失敗原文不可以丟掉 ──")
        st = {("revenue", "2015-01", "sii"): ("fail", "連線中斷")}
        H.ledger_from_disk(st)
        v = st[("revenue", "2015-01", "sii")]
        chk("★ 資料庫的狀態是「有」", v[0] == "ok", v[0])
        chk("★ 這一趟的失敗留在 note 裡，沒被藏起來", "連線中斷" in v[1], v[1][-24:])

        print("\n── 3. 沒有檔的期別維持原判，不可以憑空變成 ok ──")
        st = {("fs", "2099Q9", "sii"): ("pending", "0 張表")}
        H.ledger_from_disk(st)
        chk("★ 沒檔就不會被補成 ok", st[("fs", "2099Q9", "sii")][0] == "pending")
        chk("沒碰過又沒檔的期別不會憑空出現",
            ("fs", "2098Q1", "sii") not in st)

        print("\n── 4. 目錄不存在時不可以爆掉 ──")
        H.OUT = os.path.join(tmp, "空的")
        st = {}
        try:
            H.ledger_from_disk(st)
            chk("目錄不存在時安靜略過", st == {})
        except Exception as ex:                              # noqa: BLE001
            chk("目錄不存在時安靜略過", False, f"{type(ex).__name__}: {ex}")

        print("\n── 5. 沒有碰到 repo ──")
        led_after = (io.open(REPO_LEDGER, "rb").read()
                     if os.path.isfile(REPO_LEDGER) else None)
        chk("★ repo 的 _hist_status.csv 逐位元沒變", led_before == led_after)
    finally:
        H.OUT = real_out
        shutil.rmtree(tmp, ignore_errors=True)

    # ══════════════════════════════════════════════════════════════
    # 6. ⭐⭐⭐ 月營收有**兩段**：`_0` 國內 ＋ `_1` 外國企業（KY／DR）
    #
    # ⛔ 2015~2026 十一年的歷史面板只打了 `_0` ⇒ **整類外國發行不在**，
    #   而它不會報錯：欄位一樣、格式一樣、列數幾千。
    # ⭐ probe run 109 實測：sii `_1` 91 列含 KY 89 檔、otc `_1` 30 列含 KY 30 檔、
    #   `_2` 兩個市場都 404。
    # ══════════════════════════════════════════════════════════════
    print("\n── 6. 月營收的兩段（合成資料，⛔ 不連外）──")
    import ast as _ast
    import inspect as _insp
    sig = _insp.signature(H.rev_url)
    chk("⭐⭐ `rev_url` 的 `part` **沒有預設值**"
        "（⛔ 有預設值 ⇒ 忘了傳就默默只拿國內那一段，⚠ 那正是原本的 bug）",
        sig.parameters["part"].default is _insp.Parameter.empty, str(sig))
    chk("  兩段都拼得出網址，而且尾碼不同",
        H.rev_url("sii", 114, 1, "0").endswith("_114_1_0.html")
        and H.rev_url("sii", 114, 1, "1").endswith("_114_1_1.html"))
    try:
        H.rev_url("sii", 114, 1, "9")
        _blocked = False
    except AssertionError:
        _blocked = True
    chk("⛔ 不認得的 part 要**當場擋下來**（⚠ 靜靜拼一個 404 網址最糟）", _blocked)
    chk("⭐ `REV_PARTS` 兩段都還在（⛔ 只剩一段就是有人把它抄回去了）",
        tuple(H.REV_PARTS) == ("0", "1"), str(H.REV_PARTS))

    hdr = ["a", "b", "c", "d"]
    r, h, note = H.merge_parts({
        "0": ([["1101", "台泥", "水泥工業", "1"]], hdr, ""),
        "1": ([["1256", "鮮活果汁-KY", "食品工業", "2"]], hdr, ""),
    })
    chk("⭐ 兩段合起來 ⇒ 列數相加、KY 那一列進得來",
        len(r) == 2 and any("KY" in x[1] for x in r), str(r))
    chk("  表頭沿用（兩段欄位相同）", h == hdr, str(h))
    chk("⭐⭐ 說明要把**每一段各幾列**講出來"
        "（⛔ 否則「`_1` 抓不到」跟「那一期沒有外國企業」長得一模一樣）",
        "0／國內 1 列" in note and "1／外國企業" in note, note)

    r2, _h2, note2 = H.merge_parts({
        "0": ([["1101", "台泥", "水泥工業", "1"]], hdr, ""),
        "1": ([], None, "HTTP 404 Not Found"),
    })
    chk("⭐ `_1` 掛掉時**主段照樣留下來**（⛔ 不是整期丟掉）", len(r2) == 1)
    chk("⭐⭐ 而它**為什麼**空要寫在說明裡（⚠ 這一條是這一節的重點）",
        "404" in note2 and "0 列" in note2, note2)

    # ⭐ 呼叫點：回補主迴圈真的兩段都抓（第七點③：測了判準沒測呼叫點）
    _src = io.open(os.path.join(HERE, "mops_history.py"), encoding="utf-8").read()
    _tree = _ast.parse(_src)
    # ⚠ 只數 `main()` 裡那一個：`merge_parts` 自己也有一個 `for part in REV_PARTS`，
    #   ⛔ 那一個是**對的**（它就是在逐段合併）——第一版我掃全檔 ⇒ 數到 2 ⇒ 假紅。
    _fmain = next((f for f in _ast.walk(_tree)
                   if isinstance(f, _ast.FunctionDef) and f.name == "main"), None)
    _loops = [n for n in _ast.walk(_fmain or _tree) if isinstance(n, _ast.For)
              and getattr(n.iter, "id", "") == "REV_PARTS"]
    chk("⭐⭐ 回補迴圈（`main()` 裡）是 `for part in REV_PARTS`（⛔ 不是寫死一段）",
        len(_loops) == 1, f"實得 {len(_loops)} 個")
    chk("  而且合併走 `merge_parts`（⛔ 不是在迴圈裡自己 extend 一份）",
        sum(1 for n in _ast.walk(_tree) if isinstance(n, _ast.Call)
            and getattr(n.func, "id", "") == "merge_parts") == 1)

    # ── ⭐⭐ `parse_fs` 回的元組**幾個欄**（⛔ 不是問 docstring，是問回來的東西）
    #   2026-09-15 probe 112 付過代價：docstring 寫 4 個、實際回 5 個
    #   ⇒ `mops_probe.survivor_fs_case` 照說明拆 ⇒ ValueError ⇒ 整支探針 rc=1
    #   ⇒ 那一趟的 `_mops_probe.txt` 是**上一次**的內容（⚠ 而檔案看起來完全正常）。
    _fs_html = (
        "<html><body><table>"
        "<tr><td>公司代號</td><td>公司名稱</td><td>營業收入</td><td>營業成本</td></tr>"
        "<tr><td>2330</td><td>台積電</td><td>1,234,567</td><td>600,000</td></tr>"
        "<tr><td>2456</td><td>奇力新</td><td>7,654</td><td>3,210</td></tr>"
        "</table></body></html>").encode("utf-8")
    _got, _enc = H.parse_fs(_fs_html)
    chk("⭐ `parse_fs` 至少解出一張表（⛔ 假回應要照真的形狀做，否則下一條沒測到）",
        len(_got) >= 1, f"實得 {len(_got)} 張")
    chk("⭐⭐ 而它每一格是 **5 元組** `(kind, how, caption, 表頭, 列)`"
        "（⛔ docstring 曾經寫 4 個，而斷言要驗**回來的東西**）",
        bool(_got) and all(len(t) == 5 for t in _got),
        f"實得長度 {[len(t) for t in _got]}")
    chk("  而最後一格是**列**、第一欄是代號（⇒ 下游 `r[0]` 拿到的是代號）",
        bool(_got) and [r[0] for r in _got[0][4]] == ["2330", "2456"],
        str(_got[0][4] if _got else ""))

    # ───── [兩條路] ⭐ 五點二的閘門：一整類只在其中一條路上 ─────
    #  ⚠ 這一節用**合成**資料（⛔ 不是現場的 data/）：
    #    CLAUDE.md 第七點第七個——拿現場資料驗判準，等於把斷言的壽命
    #    綁在「這個 bug 還沒修好」上。⭐ KY 那個缺口**已經補好了**
    #    ⇒ 拿現場資料這一節今天就驗不到。
    d3 = tempfile.mkdtemp(prefix="mopsdiff_")
    _old_out = H.OUT
    try:
        H.OUT = d3
        os.makedirs(os.path.join(d3, "revenue"))
        os.makedirs(os.path.join(d3, "revenue_hist"))

        def _w(rel, rows):
            with io.open(os.path.join(d3, rel), "w", encoding="utf-8") as f:
                f.write("stock_id,name,period,market\n")
                for sid, nm in rows:
                    f.write(f"{sid},{nm},2026-08,twse\n")

        chk("⭐ `sec_kind` 用**含**、⛔ 不是 endswith（創新板 `-KY創`）",
            (H.sec_kind("錼創科技-KY創"), H.sec_kind("晨訊科-DR"),
             H.sec_kind("台積電")) == ("KY", "DR", "一般"))
        chk("  ⚠ 名稱裡有逗號時**不會**判到別欄去（⛔ 裸 split 會）",
            H.sec_kind('友達, Inc.-KY') == "KY")

        # ① 兩邊都齊 ⇒ 沒有缺口
        _w("revenue/2026-08.csv", [("2330", "台積電"), ("8登", "某某-KY")])
        _w("revenue_hist/2026-08_twse.csv",
           [("2330", "台積電"), ("8登", "某某-KY")])
        chk("① 兩條路都講得出 KY ⇒ **沒有**缺口",
            H.class_gaps(*H.two_path_kinds("2026-08")) == [],
            str(H.class_gaps(*H.two_path_kinds("2026-08"))))

        # ② 歷史那條路整類 KY 是 0（＝2026-09-15 之前的真實狀態）
        _w("revenue_hist/2026-08_twse.csv", [("2330", "台積電")])
        g = H.class_gaps(*H.two_path_kinds("2026-08"))
        chk("②⭐⭐ 歷史面板整類 KY ＝ 0 而當期有 ⇒ **紅**（KY 缺了一年多的那個形狀）",
            g == [("KY", 1, 0)], str(g))

        # ②b ⭐ **反方向**也要抓（三點①：只比一個方向不算一致）
        _w("revenue/2026-08.csv", [("2330", "台積電")])
        _w("revenue_hist/2026-08_twse.csv",
           [("2330", "台積電"), ("8登", "某某-KY")])
        g2 = H.class_gaps(*H.two_path_kinds("2026-08"))
        chk("②b⭐ **當期** feed 整類 KY ＝ 0 而歷史有 ⇒ 一樣紅"
            "（⛔ 只比一個方向不算一致，三點①）",
            g2 == [("KY", 0, 1)], str(g2))

        # ③ 兩邊都沒有 KY ⇒ ⛔ 不可以紅（五點三 absent ≠ zero）
        _w("revenue/2026-08.csv", [("2330", "台積電")])
        _w("revenue_hist/2026-08_twse.csv", [("2330", "台積電")])
        chk("③⛔ 兩邊都沒有 KY ⇒ **不回報**（⚠ 真的沒有外國企業的期別，五點三）",
            H.class_gaps(*H.two_path_kinds("2026-08")) == [],
            str(H.class_gaps(*H.two_path_kinds("2026-08"))))

        # ④ 總數差很多、但每一類兩邊都有 ⇒ ⛔ 不可以紅
        _w("revenue/2026-08.csv", [("2330", "台積電"), ("8登", "某某-KY")])
        _w("revenue_hist/2026-08_twse.csv",
           [("2330", "台積電"), ("8登", "某某-KY")]
           + [(str(9000 + i), f"其他{i}") for i in range(50)])
        chk("④⛔ 總數差 50 檔但每一類兩邊都有 ⇒ **不回報**"
            "（⚠ 倖存者偏誤／期別重分組都會讓總數差，那是正當的）",
            H.class_gaps(*H.two_path_kinds("2026-08")) == [],
            str(H.class_gaps(*H.two_path_kinds("2026-08"))))

        # ⑤ 少一邊的檔 ⇒ 這一期比不了，⛔ 不是「沒有缺口」也不是紅
        c5, h5 = H.two_path_kinds("2099-01")
        chk("⑤ 任一條路沒有那一期的檔 ⇒ `two_path_kinds` 給 None（⛔ 不是空集合）",
            c5 is None and h5 is None, f"{c5}｜{h5}")
        n_cmp, bad = H.two_path_summary()
        chk("  而 `two_path_summary` 只數**比得了**的期別",
            n_cmp == 1 and bad == [], f"{n_cmp}｜{bad}")

        # ⭐ 呼叫點（第七點第三個）
        import ast
        src = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "mops_history.py"), encoding="utf-8").read()
        fn = next(n for n in ast.parse(src).body
                  if isinstance(n, ast.FunctionDef) and n.name == "main")
        names = {getattr(n.func, "id", "") for n in ast.walk(fn)
                 if isinstance(n, ast.Call)}
        chk("⭐ main() 真的會叫 `two_path_summary`（⛔ 不是函式在那裡沒人叫）",
            "two_path_summary" in names)
        checks = [n for n in ast.walk(fn) if isinstance(n, ast.Call)
                  and getattr(n.func, "attr", "") == "check"]
        hit = [c for c in checks if isinstance(c.args[0], ast.Constant)
               and "一整類" in c.args[0].value]
        chk("⭐⭐ 而它接上了一道 `rl.check`（⛔ 只寫 info 的話沒有人在守）",
            len(hit) == 1, str(len(hit)))
        # ⛔ `hit` 空的時候不可以讓它 IndexError：崩潰會把後面每一條都掐掉，
        #   ⚠ 而「紅 1 條」與「紅 5 條」對突變驗是兩回事（第七點第二個）。
        vs = ({n.id for n in ast.walk(hit[0].args[1]) if isinstance(n, ast.Name)}
              if len(hit) == 1 else set())
        chk("  而那道閘門的判準裡有 `bad`", "bad" in vs, str(sorted(vs)))

        # ⭐ 沒有動到 repo 真的 data/mops/
        chk("★ 沒有動到 repo 真的 `data/mops/revenue/`",
            H.OUT == d3 and os.path.isdir(os.path.join(d3, "revenue")))
    finally:
        H.OUT = _old_out
        shutil.rmtree(d3, ignore_errors=True)

    print(f"\n[selftest] 通過 {ok}｜失敗 {fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
