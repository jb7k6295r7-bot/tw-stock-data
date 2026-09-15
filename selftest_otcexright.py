#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""驗 `otc_exright_check.main()`，⛔ 重點在**它擋不擋得下該擋的**。

盯三件：
1. 民國 7 碼沒轉西元 —— `1150909` 與 `2015-09-09` 都像日期，錯一個世紀沒人發現。
2. **「官方有、我方 adj 沒有」那條斷言真的會紅** —— 那是這一支存在的唯一理由，
   它若永遠綠，這支就是裝飾。
3. 累積檔**只增不減**（端點只給當日，寫短了就永久失去）。
"""
import io, json, os, sys, tempfile
import backfill as _B
import runlog as _RL
import otc_exright_check as C

FAIL = []


def ck(n, c, note=""):
    print(("  ok   " if c else "  ✗    ") + n + (f"　（{note}）" if note else ""))
    if not c:
        FAIL.append(n)


def row(code, name, pre, ref, kind="除權息", date="1150909"):
    return {C.F_DATE: date, C.F_CODE: code, C.F_NAME: name,
            C.F_PRE: pre, C.F_REF: ref, C.F_KIND: kind}


def run(payload, out, lr, adj):
    old = (C.OUT, C.ADJ_DIR, _RL.PATH, _B.get)
    C.OUT, C.ADJ_DIR, _RL.PATH = out, adj, lr
    _B.get = lambda *a, **k: (json.dumps(payload, ensure_ascii=False).encode(), None)
    try:
        sys.argv = ["otc_exright_check.py"]
        C.main()
        return io.open(lr, encoding="utf-8").read()
    finally:
        C.OUT, C.ADJ_DIR, _RL.PATH, _B.get = old


def main():
    print("[1] roc7()")
    ck("1150909 → 2026-09-09", C.roc7("1150909") == "2026-09-09", C.roc7("1150909"))
    ck("⛔ 認不出回 None", C.roc7("20260909") is None and C.roc7("") is None)

    d = tempfile.mkdtemp()
    adj = os.path.join(d, "adj")
    os.makedirs(adj)
    io.open(os.path.join(adj, "1815.csv"), "w").write("date,factor\n2026-09-09,0.949\n")
    out, lr = os.path.join(d, "o.csv"), os.path.join(d, "l.md")
    real_out, real_lr = C.OUT, _RL.PATH
    b4 = (os.path.exists(real_out),
          os.path.getmtime(real_lr) if os.path.exists(real_lr) else None)

    print("[2] ⭐ 一筆已落地、一筆沒有 ⇒ 斷言必須紅")
    t = run([row("1815", "富喬", "135.00", "128.10"),
             row("4160", "訊聯基因", "39.80", "37.92", "除權")], out, lr, adj)
    ck("★ 沒落地的那一筆讓斷言變 ✗", "**✗**　官方有、我方 data/adj 沒有" in t)
    ck("★ ✗ 的細節指得出是哪一檔", "4160" in t, [l for l in t.splitlines() if "沒落地" in l])
    csvtxt = io.open(out, encoding="utf-8").read()
    ck("民國已轉西元", "2026-09-09" in csvtxt and "1150909" not in csvtxt)
    ck("兩筆都累積進去", len(csvtxt.strip().splitlines()) == 3)

    print("[3] ⭐ 全部落地 ⇒ 斷言要變綠（否則它是永遠紅的裝飾）")
    io.open(os.path.join(adj, "4160.csv"), "w").write("date,factor\n2026-09-09,1.05\n")
    t2 = run([row("1815", "富喬", "135.00", "128.10"),
              row("4160", "訊聯基因", "39.80", "37.92", "除權")],
             os.path.join(d, "o2.csv"), os.path.join(d, "l2.md"), adj)
    ck("★ 全落地時斷言是 ok", "**✗**　官方有、我方 data/adj 沒有" not in t2)

    print("[4] 累積只增不減")
    t3 = run([row("1815", "富喬", "135.00", "128.10")], out, lr, adj)
    ck("★ 本趟只回一筆，累積檔仍是 2 筆（不覆蓋）",
       len(io.open(out, encoding="utf-8").read().strip().splitlines()) == 3)
    ck("只增不減那一項是 ok", "**✗**　累積檔只增不減" not in t3)

    print("[5] ⛔ 沒有動到 repo")
    ck("★ 沒動到真的 otc_exright_official.csv", os.path.exists(real_out) == b4[0])
    ck("★ 沒動到真的 _last_run.md",
       (os.path.getmtime(real_lr) if os.path.exists(real_lr) else None) == b4[1])

    print()
    # ───── ⭐ 反方向：「我方有、官方沒有」那一批各是什麼（三點①） ─────
    #  ⚠ 用**合成**資料（第七點第七個）：現場那 246 筆全部解釋得了
    #    ⇒ 拿現場資料驗，「轉板前 > 0」那一格**永遠走不到**。
    import bisect  # noqa: F401  （`_market_on` 用得到，這裡只是確認它 import 得進來）
    import otc_exright_history as H
    print("\n── 反方向：我方有、官方沒有 ──")
    _days = ["2020-01-02", "2020-01-03", "2020-06-01", "2020-06-02"]
    _out = {"AAA": "2019-12-31"}          # AAA 2019 年底就轉出上櫃了
    _only = [("AAA", "2020-06-01")]       # ⇒ 事件在轉板之後 ⇒ 正常
    a, b, v, u, bad = H.ours_only_verdict(_only, _out, _days)
    ck("⭐ 事件日在**轉出上櫃之後** ⇒ 歸到「轉板後」，⛔ 不算官方漏了",
       (a, b, v, u) == (1, 0, 0, 0), f"{(a, b, v, u)}｜{bad}")

    _only2 = [("AAA", "2019-06-01")]      # ⇒ 事件在轉板之前 ⇒ ⛔ 官方真的漏了
    a2, b2, v2, u2, bad2 = H.ours_only_verdict(_only2, _out, _days)
    ck("⭐⭐ 事件日在**轉板之前** ⇒ 那才是「官方漏了」，而且要講得出是哪一筆",
       (a2, b2) == (0, 1) and bad2 and bad2[0][0] == "AAA",
       f"{(a2, b2, v2, u2)}｜{bad2}")

    # ⭐ 第二條路：`delisted.csv` 查不到那一檔 ⇒ 改問**我方日檔**
    d9 = tempfile.mkdtemp(prefix="otcx_")
    _oldroot = H._ROOT
    try:
        H._ROOT = d9
        os.makedirs(os.path.join(d9, "universe", "daily"))
        for d, mk in (("2021-03-01", "twse"), ("2021-09-01", "tpex")):
            with io.open(os.path.join(d9, "universe", "daily", f"{d}.csv"),
                         "w", encoding="utf-8") as f:
                f.write("stock_id,market\n")
                f.write(f"BBB,{mk}\n")
        dd = ["2021-03-01", "2021-09-01"]
        a3, b3, v3, u3, _ = H.ours_only_verdict([("BBB", "2021-03-01")], {}, dd)
        ck("⭐ `delisted.csv` 查不到 ＋ 日檔說**上市** ⇒ 歸到「日檔判定」",
           (a3, b3, v3, u3) == (0, 0, 1, 0), str((a3, b3, v3, u3)))
        a4, b4, v4, u4, bad4 = H.ours_only_verdict([("BBB", "2021-09-01")], {}, dd)
        ck("⭐⭐ `delisted.csv` 查不到 ＋ 日檔說**還在上櫃** ⇒ ⛔ 算官方漏了",
           (a4, b4, v4, u4) == (0, 1, 0, 0) and bad4, f"{(a4, b4, v4, u4)}｜{bad4}")
        a5, b5, v5, u5, _ = H.ours_only_verdict([("ZZZ", "2021-03-01")], {}, dd)
        ck("⛔ 兩條路都查不到 ⇒ 歸到「仍未判定」，⛔ 不是塞進「官方漏了」"
           "（⚠ absent ≠ 證據，五點三）",
           (a5, b5, v5, u5) == (0, 0, 0, 1), str((a5, b5, v5, u5)))
        ck("★ 沒有動到 repo 真的 `data/universe/daily/`", H._ROOT == d9)
    finally:
        H._ROOT = _oldroot
        import shutil
        shutil.rmtree(d9, ignore_errors=True)

    # ⭐ 取「最後一筆」轉出日（一個代號可能有多列：轉板一筆＋真下市一筆）
    a6, b6, _, _, _ = H.ours_only_verdict(
        [("AAA", "2020-06-01")], {"AAA": "2019-12-31"}, _days)
    ck("  而基準是該檔轉出上櫃的日子（⛔ 不是今天）", (a6, b6) == (1, 0))

    # ⭐ 呼叫點（第七點第三個）
    import ast
    _src = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "otc_exright_history.py"), encoding="utf-8").read()
    _main = next(n for n in ast.parse(_src).body
                 if isinstance(n, ast.FunctionDef) and n.name == "main")
    _calls = {getattr(n.func, "id", "") for n in ast.walk(_main)
              if isinstance(n, ast.Call)}
    ck("⭐ `main()` 真的會叫反方向那一支（⛔ 不是函式在那裡沒人叫）",
       "ours_only_verdict" in _calls, str(sorted(x for x in _calls if x)))
    _cks = [n for n in ast.walk(_main) if isinstance(n, ast.Call)
            and getattr(n.func, "attr", "") == "check"]
    _rev = [c for c in _cks if isinstance(c.args[0], ast.Constant)
            and "反方向" in c.args[0].value]
    ck("⭐⭐ 而它接上了一道 `rl.check`（⛔ 只寫 info 的話沒有人在守）",
       len(_rev) == 1, str(len(_rev)))

    if FAIL:
        print(f"⛔ {len(FAIL)} 項沒過：{FAIL}")
        return 1
    print("全過")
    return 0


if __name__ == "__main__":
    sys.exit(main())
