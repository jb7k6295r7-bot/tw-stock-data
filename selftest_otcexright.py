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
    if FAIL:
        print(f"⛔ {len(FAIL)} 項沒過：{FAIL}")
        return 1
    print("全過")
    return 0


if __name__ == "__main__":
    sys.exit(main())
