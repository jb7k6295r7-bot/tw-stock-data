#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""half_run.py — 在沙箱裡**真的跑一次** `otc_*_history.py` 的 `main()`，回 (rc, runlog 文字)。

⭐ 為什麼是一份共用的，⛔ 不是兩支自測各抄一份：
  `otc_exright_history` 與 `otc_reduce_history` 是姊妹，兩支的 `--no-scan`／
  `--scan-only` 是**同一件事的兩份實作**（四點五）⇒ 驗它們的沙箱若也抄兩份，
  ⚠ 下一個人只會修其中一份，而 `selftest_no_dup.py` 比的是**函式本體**
  ⇒ 兩份只要寫法不同就躲得過那道守門（四點五第八次那一條）。

⛔ 這一支要導走的旋鈕有**四個**，缺一個就會寫到 repo 真的檔：

    mod.OUT        判準檔          `data/meta/otc_*_history.csv`
    mod.LOW        低水位檔        `data/meta/_otc_*_low.txt`（⚠ 寫壞一次那道閘門永遠綠）
    runlog.PATH    runlog          `data/meta/_last_run.md`
    mod._post      **連外**        ⇒ 預設換成會**丟例外**的那一個

⛔⛔ **而拿掉任何一個旋鈕的突變，會當場寫壞 repo 真的那幾個檔**——
  那正是那四條 `★` 斷言存在的理由，⚠ 而它也意味著：
  **跑完 P1~P4 那一族的突變之後，一定要 `git checkout -- data/meta/…` 還原。**
  ⇒ 實測（2026-09-16）：P2／P3 一跑完，`otc_reduce_history.csv` 從 285 列剩 1 列、
    `_last_run.md` 多了兩塊假的——⭐ 而 `mutate.py` 只還原**原始碼**，它不管 `data/`。

⭐ 而 `_post` 換成丟例外的（⛔ 不是回空的）是有理由的：
  `--scan-only` 那一半的**判準就是「它沒有連外」**
  ⇒ 回空的話它會走進「抓不到」那條正當出口，⚠ 看起來跟沒連外一模一樣（七點第四個）。
"""
import io
import os
import sys

import runlog

# ⭐ 呼叫端要拿它來寫「★ 沒有動到 repo 真的 ___」那幾條斷言（七點第五個）。
KNOBS = ("OUT", "LOW", "_post")


def run_half(mod, args, tmpdir, payload=None):
    """跑一次 `mod.main()`；`payload` 是 None ⇒ ⛔ 連外就當場炸。

    回 `(rc, runlog 這一趟寫出來的整份文字)`；⛔ 受測程式丟例外時回
    `(None, "⛔ 例外：…")`，**⚠ 不讓例外逃出去**。

    ⭐ 為什麼在這裡接住（⛔ 而不是讓呼叫端各自 try）：
      例外逃出去 ⇒ 整支自測**當場中斷、後面一條都不會跑**，
      ⚠ 而畫面上是 traceback ⇒ **不會印 `✗`**（七點第二個）。
      ⇒ 實測：`--scan-only` 那一半被改成會連外的突變，
        接住之前是「紅 3 條 ＋ 崩潰」、接住之後是**紅 5 條**。

    ⚠ runlog 要在**還原 PATH 之前**讀回來——還原之後那個路徑就指到 repo 真的檔了。
    """
    saved = {k: getattr(mod, k) for k in KNOBS}
    saved_path, saved_argv = runlog.PATH, sys.argv
    mod.OUT = os.path.join(tmpdir, "out.csv")
    mod.LOW = os.path.join(tmpdir, "low.txt")
    runlog.PATH = os.path.join(tmpdir, "_last_run.md")

    def _boom(*_a, **_k):
        raise AssertionError("★ 這一半**不可以連外**，⛔ 而它打了一發")

    mod._post = _boom if payload is None else (lambda *_a, **_k: (payload, None))
    sys.argv = ["x"] + list(args)
    try:
        try:
            rc = mod.main()
        except SystemExit:
            # ⛔ `SystemExit` 要放它過去：那是「兩個旗標同時給」的**正當**出口，
            #   ⚠ 而呼叫端的判準就是接得到它。
            raise
        except Exception as ex:                                  # noqa: BLE001
            # ⛔ 一定要**另存一個名字**：`except ... as ex` 的 `ex` 在離開
            #   那個區塊時會被 Python **自動 del 掉** ⇒ 下面再用它是 `NameError`
            #   ⚠ 而 NameError 也是例外 ⇒ 它照樣逃出去、照樣中斷整支自測
            #   ⇒ ⭐ 實測：修之前兩個突變都回「⚠ **崩潰**」，看起來跟沒接住一樣。
            rc, boom = None, f"{type(ex).__name__}: {ex}"
        txt = (io.open(runlog.PATH, encoding="utf-8").read()
               if os.path.exists(runlog.PATH) else "")
        if rc is None:
            txt = f"⛔ 例外：{boom}\n" + txt
    finally:
        sys.argv = saved_argv
        runlog.PATH = saved_path
        for k, v in saved.items():
            setattr(mod, k, v)
    return rc, txt
