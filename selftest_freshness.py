#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`freshness_check.py` 的自測。**造假的 data/ 再跑，⛔ 不連網、不碰 repo 的 data/。**

## ⛔⛔ 這一支為什麼今天才有（2026-09-11）

`freshness_check` 守的是**「不累積就永久失去」**的那幾份
（集保只留一年、上櫃日曆只給最近 7 個交易日、上市停止買賣中只給當下）。

⚠ 它們的共同點是**壞掉的時候整條管線是綠的**——沒有人會失敗，
只是每過一天就永久少一天。⇒ 這一支是那幾份**唯一**會吵的地方。

⛔ 而它自己**一支自測都沒有**。今天往 `TARGETS` 加東西時才發現。

## 要釘的四件

    ① 過期 ⇒ 真的變 ✗（⛔ 不是印一行 info 就算）
    ② 目錄不存在／是空的 ⇒ 也算壞（⛔ 讀不到 ≠ 沒問題）
    ⭐ ③ 認**檔名裡的日期**，⛔ 不認副檔名
       （`data/holiday/` 存的是 `.html`，只收 `.csv` 會報假的「目錄是空的」）
    ④ 民國檔名（`filename_roc`）換算得對
"""
import io
import os
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import freshness_check as F                                    # noqa: E402
import runlog                                                  # noqa: E402

OK = FAIL = 0
TPE = timezone(timedelta(hours=8))


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


def run_with(targets, root):
    """換掉 TARGETS 跑一趟 → (回傳碼, runlog 文字)。"""
    _ot, _op = F.TARGETS, runlog.PATH
    try:
        F.TARGETS = targets
        runlog.PATH = os.path.join(root, "_last_run.md")
        rc = F.main()
    finally:
        F.TARGETS, runlog.PATH = _ot, _op
    txt = ""
    if os.path.exists(os.path.join(root, "_last_run.md")):
        txt = io.open(os.path.join(root, "_last_run.md"), encoding="utf-8").read()
    return rc, txt


def main():
    print("=" * 60)
    print("freshness_check.py 自測（不連網）")
    print("=" * 60)
    today = datetime.now(TPE).date()

    d = tempfile.mkdtemp(prefix="fresh_")
    try:
        # ── ③ 認檔名裡的日期，⛔ 不認副檔名 ──
        html = os.path.join(d, "holiday")
        os.makedirs(html)
        for k in range(3):
            day = (today - timedelta(days=k)).isoformat()
            io.open(os.path.join(html, day + ".html"), "w").write("x")
        got, note = F._newest(html, "filename")
        ck("⭐ `.html` 也認得（⛔ 只收 `.csv` 會報假的「目錄是空的」）",
           got == today.isoformat(), f"{got} {note}")
        ck("  而且數得出有幾份", note == "3 份", note)

        # ⛔ 檔名不是日期的目錄
        junk = os.path.join(d, "junk")
        os.makedirs(junk)
        io.open(os.path.join(junk, "readme.txt"), "w").write("x")
        got2, note2 = F._newest(junk, "filename")
        ck("⛔ 有檔但檔名不是日期 ⇒ 取不到，⚠ 而且說得出差別"
           "（⛔ 不是回「目錄是空的」）",
           got2 is None and "沒有一個的檔名是日期" in note2, note2)

        empty = os.path.join(d, "empty")
        os.makedirs(empty)
        ck("  空目錄 ⇒ 說「目錄是空的」",
           F._newest(empty, "filename") == (None, "目錄是空的"))
        ck("  目錄不存在 ⇒ 說「目錄不存在」",
           F._newest(os.path.join(d, "nope"), "filename")
           == (None, "目錄不存在"))

        # ── ④ 民國檔名 ──
        roc = os.path.join(d, "roc")
        os.makedirs(roc)
        io.open(os.path.join(roc, "1150630.csv"), "w").write("x")
        ck("⭐ 民國 1150630 → 2026-06-30",
           F._newest(roc, "filename_roc")[0] == "2026-06-30",
           str(F._newest(roc, "filename_roc")))

        # ── ① 過期 ⇒ 真的變 ✗ ──
        old = os.path.join(d, "old")
        os.makedirs(old)
        io.open(os.path.join(old, (today - timedelta(days=30)).isoformat()
                             + ".csv"), "w").write("x")
        rc, txt = run_with([("測試用過期的", old, "filename", 5, "測試")], d)
        ck("⭐⭐ 過期 ⇒ 回非 0（⛔ 不是印一行 info 就算）", rc != 0, str(rc))
        ck("  而且是 ✗ 那一條",
           any(x.startswith("- **✗**") and "永久失去" in x
               for x in txt.splitlines()),
           [x for x in txt.splitlines() if "永久失去" in x])
        # ⚠ 要挑**那一項的資訊列**來比，⛔ 不是比整份文字：
        #   ✗ 那條的細節裡本來就有「30 天前 > 容忍 5」
        #   ⇒ 比整份的話，把資訊列拿掉的突變照樣過（M6 第一輪就是這樣沒紅）。
        _info = [x for x in txt.splitlines()
                 if x.startswith("- **測試用過期的**")]
        ck("  ⭐ **資訊列**本身就講得出差幾天與容忍幾天"
           "（⛔ 不是靠 ✗ 那條的細節）",
           bool(_info) and "30 天前" in _info[0] and "容忍 5" in _info[0],
           str(_info))

        # ── ⭐ 反向：沒過期 ⇒ 綠（⛔ 否則天天紅，然後被學會忽略）──
        rc2, txt2 = run_with([("測試用新鮮的", html, "filename", 5, "測試")], d)
        ck("⭐ 沒過期 ⇒ 回 0（⛔ 一個永遠紅的守門等於沒有守門）",
           rc2 == 0, str(rc2))
        ck("  而且那一條是 ok",
           any(x.startswith("- ok") and "永久失去" in x
               for x in txt2.splitlines()))

        # ── ② 目錄不存在也算壞 ──
        rc3, txt3 = run_with(
            [("測試用不存在的", os.path.join(d, "nope"), "filename", 5, "測試")], d)
        ck("⛔ 目錄不存在 ⇒ 也算壞（⛔ 讀不到 ≠ 沒問題）", rc3 != 0, str(rc3))

        # ── asof_column ──
        csvp = os.path.join(d, "cal.csv")
        io.open(csvp, "w", encoding="utf-8").write(
            "date,asof\n2026-09-01," + (today - timedelta(days=1)).isoformat()
            + "\n2026-09-02," + (today - timedelta(days=2)).isoformat() + "\n")
        got3, note3 = F._newest(csvp, "asof_column")
        ck("⭐ `asof_column` 取的是**最大值**，⛔ 不是最後一列",
           got3 == (today - timedelta(days=1)).isoformat(), f"{got3} {note3}")
        ck("  檔案不存在 ⇒ 說「檔案不存在」",
           F._newest(os.path.join(d, "nope.csv"), "asof_column")
           == (None, "檔案不存在"))

        # ── ⭐ 真的 TARGETS 也要驗：每一項都要有理由字串 ──
        ck("⭐ 真的 `TARGETS` 每一項都有非空的理由（⛔ 容忍天數不可以沒有出處）",
           all(str(t[4]).strip() for t in F.TARGETS),
           str([t[0] for t in F.TARGETS if not str(t[4]).strip()]))
        ck("  而且取法都是認得的那幾種之一",
           all(t[2] in ("filename", "filename_roc", "asof_column")
               or t[2].startswith("column:") for t in F.TARGETS),
           str([t[2] for t in F.TARGETS]))

        # ── ⭐ column:<欄名>（2026-09-24 加，給 market_inst 的 date 欄用）──
        csvp2 = os.path.join(d, "mi.csv")
        NL = chr(10)          # ⛔ 不寫轉義：這台機器的工具鏈會把它吃掉
        io.open(csvp2, "w", encoding="utf-8").write(NL.join([
            "date,foreign",
            (today - timedelta(days=1)).isoformat() + ",1",
            (today - timedelta(days=9)).isoformat() + ",2", ""]))
        g4, n4 = F._newest(csvp2, "column:date")
        ck("⭐ `column:date` 取 date 欄的**最大值**（⛔ 不是最後一列）",
           g4 == (today - timedelta(days=1)).isoformat(), f"{g4} {n4}")
        ck("  ⭐ `asof_column` 仍然等於 `column:asof`（⛔ 既有那幾項不可以壞掉）",
           F._newest(csvp, "asof_column") == F._newest(csvp, "column:asof"),
           str((F._newest(csvp, "asof_column"), F._newest(csvp, "column:asof"))))
        # ★ 反向樣本：欄名打錯時必須說「沒有那一欄」，
        #   ⛔ 不可以回「沒有值」——那會讓人去查資料，而病在設定
        g5, n5 = F._newest(csvp2, "column:asof")
        ck("★ 欄名不在表頭 ⇒ 說【沒有那一欄】並印出表頭（⛔ 不是「沒有值」）",
           g5 is None and "沒有 asof 這一欄" in n5, f"{g5} {n5}")
        # ══════════════════════════════════════════════════════════
        # ⑨ ⭐ 排程區塊有沒有死掉——⛔ 而「沒人按」要跟「壞掉」分開講
        #
        # ⚠ 這一節**全部用合成的 `_last_run.md`**，⛔ 不讀現場那一份。
        #   理由是第七點⑦：拿現場資料驗判準，等於把斷言的壽命綁在
        #   「那個 bug 還沒修好」上——⚠ 而現場那 60 個區塊**修好的那天**
        #   （格式都換過一輪）這一節就再也驗不到東西了。
        # ══════════════════════════════════════════════════════════
        print("\n[⑨ 排程區塊]")
        old_d = (today - timedelta(days=9)).isoformat() + "T08:00:00+08:00"
        new_d = today.isoformat() + "T08:00:00+08:00"
        lr = os.path.join(d, "lr9.md")
        io.open(lr, "w", encoding="utf-8").write(
            f"## 排程死了　✓ 正常\n\n最後執行：{old_d}（台北）"
            "｜觸發 schedule｜每日台股資料｜ref main｜run 1\n\n"
            f"## 排程還活著　✓ 正常\n\n最後執行：{new_d}（台北）"
            "｜觸發 schedule｜每日台股資料｜ref main｜run 2\n\n"
            f"## 手動沒人按　✓ 正常\n\n最後執行：{old_d}（台北）"
            "｜觸發 workflow_dispatch｜全市場 feed 回補（手動）｜ref main｜run 3\n\n"
            f"## 舊格式　✓ 正常\n\n最後執行：{old_d}（台北）\n\n"
            # ⭐ 月頻的那一支：9 天前**不算壞**（⛔ 用日頻那把尺會誤報）
            f"## 月頻沒過期　✓ 正常\n\n最後執行：{old_d}（台北）"
            "｜觸發 schedule｜股本／發行股數（每月）｜ref main｜run 4\n\n")
        # ⛔⛔ 容忍度要從**那一支的 cron** 推，⚠ 不是從名字猜
        #   ——我第一版寫「名字裡有『月』就用 40 天」⇒ `股本／發行股數（每月）`
        #   剛好中，⛔ 而那是運氣：改個名字就會被當成日頻 ⇒ **天天紅**。
        ck("⑨.0a 月頻（cron 指定了日期）⇒ 容忍 40 天",
           F._tol_for(["0 1 1 * *"])[0] == F.SCHED_TOL_MONTHLY,
           str(F._tol_for(["0 1 1 * *"])))
        ck("⑨.0b 日／週頻（日期欄是 `*`）⇒ 容忍 3 天",
           F._tol_for(["0 11 * * 1-5"])[0] == F.SCHED_TOL_DAYS,
           str(F._tol_for(["0 11 * * 1-5"])))
        ck("⑨.0c ⛔ 沒有 cron ⇒ **不判**（⚠ 亂判會變成一塊天天紅的閘門）",
           F._tol_for([])[0] is None, str(F._tol_for([])))
        ck("⑨.0d ⭐ 而 `_wf_crons()` 真的讀到東西（⛔ 0 支跟全部通過長得一樣）",
           len(F._wf_crons()) >= 8 and any(F._wf_crons().values()),
           str(sorted(F._wf_crons())[:3]))

        rl9 = runlog.Run("t9", os.path.join(d, "sink9.md"))
        n_dead = F.stale_scheduled(rl9, lr)
        txt9 = "\n".join(rl9.lines) + "｜" + "｜".join(
            f"{l}={o}:{dt}" for l, o, dt in rl9.checks)
        ck("⑨.1 ⛔ **排程 ＋ 過期 ⇒ 算壞掉**（那代表該天天跑的東西死了）",
           n_dead == 1 and "排程死了" in txt9, txt9[:300])
        ck("⑨.2 排程但沒過期 ⇒ 不算壞",
           "排程還活著" not in txt9.split("排程寫的區塊都還活著")[-1], txt9[:300])
        ck("⑨.3 ⚠ **手動 ＋ 過期 ⇒ 不算壞**，只說沒人按"
           "（⛔ 要不要排程是另一個決定）",
           "手動沒人按" in txt9 and "手動而久沒按 1" in txt9, txt9[:300])
        ck("⑨.4 ⛔ 舊格式要**明講它講不出自己是誰寫的**"
           "（⚠ 不可以當成手動的）",
           "舊格式" in txt9 and "講不出自己是誰寫的** 1" in txt9, txt9[:300])
        ck("⑨.4b ⭐⭐ **月頻**的那一支 9 天沒動 ⇒ **不算壞**"
           "（⛔ 用日頻那把尺量月頻 ⇒ 那一塊天天紅，然後被學會忽略）",
           n_dead == 1 and "月頻沒過期" not in txt9.split("排程寫的區塊都還活著")[-1],
           txt9[:400])
        ck("⑨.5 ⭐ 那一條 check 的紅綠**只由「排程 ＋ 過期」決定**",
           any(l == "排程寫的區塊都還活著" and o is False for l, o, _ in rl9.checks),
           str(rl9.checks))
        # ⭐ 而 `runlog.who()` 那一半要一起釘：它是這一節唯一的資料來源
        _env = {k: os.environ.get(k) for k in
                ("GITHUB_ACTIONS", "GITHUB_EVENT_NAME", "GITHUB_WORKFLOW",
                 "GITHUB_RUN_ID", "GITHUB_REF_NAME")}
        try:
            os.environ.update(GITHUB_ACTIONS="true", GITHUB_EVENT_NAME="schedule",
                              GITHUB_WORKFLOW="每日更新", GITHUB_RUN_ID="7",
                              GITHUB_REF_NAME="main")
            w = runlog.who()
            ck("⑨.6 `runlog.who()` 在 Actions 上講得出**觸發方式／workflow／ref／run**",
               all(x in w for x in ("觸發 schedule", "每日更新", "ref main", "run 7")), w)
            os.environ["GITHUB_ACTIONS"] = "false"
            ck("⑨.7 ⛔ 不是 Actions ⇒ **不寫**（⚠ 本機跑的那一塊本來就另有警語）",
               runlog.who() == "", repr(runlog.who()))
        finally:
            for k, v in _env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
    finally:
        shutil.rmtree(d, ignore_errors=True)

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
