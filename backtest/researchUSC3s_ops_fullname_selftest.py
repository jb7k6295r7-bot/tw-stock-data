# -*- coding: utf-8 -*-
"""C3s 換股單「全名」欄自測（只排版；⛔ 不動選股）。

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSC3s_ops_fullname_selftest

比對基準 ＝ 加欄前版本（commit 099aadd2c1 的 researchUSC3s_ops.py，以 git show 唯讀載入）：
  同一月底、同一 mode，order_row 的範本 26 欄逐字相同（記錄時間欄兩邊都固定成同一字串）；新 cols ＝ 舊 cols 在備註前插「全名」；
  order_view 舊鍵值全同；cols[-1] 仍是備註（researchUSC3s_stop.order_with_level 依此寫級別）；全名欄每個代號都查得到名稱。
⛔ 不寫任何檔。
"""
from __future__ import annotations

import os
import subprocess
import sys
import types

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchUSC as K               # noqa: E402
from backtest import researchUSC3s_ops as NEW       # noqa: E402

BASE = "099aadd2c1"
REPO = os.path.expanduser("~/tw-p17")


def load_old():
    src = subprocess.check_output(["git", "-C", REPO, "show", f"{BASE}:backtest/researchUSC3s_ops.py"], text=True)
    m = types.ModuleType("researchUSC3s_ops_base")
    m.__file__ = os.path.join(REPO, "backtest", "researchUSC3s_ops_base.py")
    exec(compile(src, m.__file__, "exec"), m.__dict__)
    return m


def main():
    OLD = load_old()
    K.now_tpe = lambda: "2026-01-01 00:00"          # 兩版同一字串（記錄時間欄只是當下時鐘）
    R = K.rworld(); w1 = R["w1"]; tick = R["Wd"]["tick"]
    T = NEW.tables()
    rebs = sorted(e for e in T["BUY"] if T["t0"] <= e <= w1 + 1)
    cases = [(e - 1, mode) for e in rebs[-4:] for mode in ("exact", "proxy")]
    fails, n = [], 0
    for M, mode in cases:
        o_old, T_old = OLD.order_for(M, "main", mode)
        o_new, T_new = NEW.order_for(M, "main", mode)
        c_old, r_old = OLD.order_row(o_old, T_old)
        c_new, r_new = NEW.order_row(o_new, T_new)
        tag = f"{R['cal'][M].date()} {mode}"
        n += 1
        if c_new != c_old[:-1] + [NEW.FULLNAME_COL] + c_old[-1:]:
            fails.append((tag, "cols"))
        for c in c_old:
            n += 1
            if r_old[c] != r_new[c]:
                fails.append((tag, c, r_old[c], r_new[c]))
        n += 1
        if c_new[-1] != c_old[-1]:
            fails.append((tag, "cols[-1] 不是備註"))
        v_old, v_new = OLD.order_view(o_old, T_old), NEW.order_view(o_new, T_new)
        for k, v in v_old.items():
            n += 1
            if k not in v_new:
                fails.append((tag, "view 缺鍵", k)); continue
            if isinstance(v, list) and v and isinstance(v[0], dict):
                vv = [{kk: d[kk] for kk in d0} for d, d0 in zip(v_new[k], v)]
                if vv != v or len(v_new[k]) != len(v):
                    fails.append((tag, "view", k))
            elif v_new[k] != v:
                fails.append((tag, "view", k))
        cell = r_new[NEW.FULLNAME_COL]
        for t in NEW.order_tickers(o_new, tick):
            n += 1
            if f"{t}（" not in cell or f"{t}（{NEW.NAME_UNKNOWN}）" in cell:
                fails.append((tag, "全名缺", t))
        n += 1
        if NEW.IB_NOTE not in cell:
            fails.append((tag, "缺 IB 提醒"))
        print(tag, "｜", cell)
    n += 2
    if NEW.label("ZZZZQ") != f"ZZZZQ（{NEW.NAME_UNKNOWN}）":
        fails.append(("fallback",))
    if NEW.full_name("SNDK") != "SANDISK CORP":
        fails.append(("對照表優先", NEW.full_name("SNDK")))
    print({"比對項數": n, "不同": len(fails), "不同明細": fails[:20], "基準": BASE, "月底×mode": len(cases)})
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
