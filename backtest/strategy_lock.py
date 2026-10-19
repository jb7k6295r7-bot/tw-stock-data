# -*- coding: utf-8 -*-
"""營量 v1／營飆 v1 策略鎖（使用者 10/18：「我要怎麼確保你不會又把兩個策略條件自己改到？」）——回測線，2026-10-18。

    python3 -m backtest.strategy_lock --check            # 比對鎖定版；不同 ⇒ 印出哪幾支、exit 1
    python3 -m backtest.strategy_lock --list             # 列出鎖定範圍與 sha
    python3 -m backtest.strategy_lock --relock --reason "裁定 seqNNN：…"   # ⛔ 只有裁定線發號核可的改動才可重鎖

鎖定範圍 ＝ 產生兩策略訊號、名單與照規則簿的程式，以及它們在 backtest/ 內 import 到的全部模組（遞迴，自動求閉包）：
  根：list_prereg10（營飆 v1 名單／AND 訊號管線）、list_yl13（營量 v1 名單）、forward_yl（照規則簿：N、H、挑法、大盤閘、種子）
  ⇒ 包含引擎 research11、rerun17、research13、data、patterns、universe_gate……（以實際 import 為準）。
  ⭐ 任何一支有改（即使是「預設關閉、逐位元相同」的加開關），--check 都會報；要經裁定核可後用 --relock 寫入原因才會消失。
  ⛔ daily_list.py（名單措辭／版面）不在鎖內：它只排版，不決定買哪幾檔；但它 import 的訊號模組在鎖內。
每日名單排程（run_daily_list.sh）每次跑都 --check；不同 ⇒ 名單最上方加一行 ⚠（會推到 LINE），並記 log。
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LOCK = os.path.join(HERE, "strategy_lock.json")
ROOTS = ["list_prereg10", "list_yl13", "forward_yl"]


def _imports(mod):
    """mod 在 backtest/ 內以相對匯入（from . import X／from .X import Y）用到的模組名。"""
    p = os.path.join(HERE, mod + ".py")
    tree = ast.parse(open(p, encoding="utf-8").read())
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and n.level == 1:
            if n.module:
                out.add(n.module.split(".")[0])
            else:
                out.update(a.name for a in n.names)
    return {m for m in out if os.path.exists(os.path.join(HERE, m + ".py"))}


def closure():
    seen, todo = set(), list(ROOTS)
    while todo:
        m = todo.pop()
        if m in seen:
            continue
        seen.add(m)
        todo.extend(_imports(m) - seen)
    return sorted(seen)


def digest():
    return {m: hashlib.sha256(open(os.path.join(HERE, m + ".py"), "rb").read()).hexdigest()[:16] for m in closure()}


def check():
    if not os.path.exists(LOCK):
        return ["（沒有鎖檔 strategy_lock.json）"]
    L = json.load(open(LOCK, encoding="utf-8"))
    old, new = L["files"], digest()
    diff = [f"{m}.py 已改" for m in sorted(set(old) & set(new)) if old[m] != new[m]]
    diff += [f"{m}.py 新加入鎖定範圍" for m in sorted(set(new) - set(old))]
    diff += [f"{m}.py 不再被 import" for m in sorted(set(old) - set(new))]
    return diff


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--relock", action="store_true")
    ap.add_argument("--reason", default="")
    a = ap.parse_args()
    if a.relock:
        if not a.reason.strip():
            sys.exit("⛔ --relock 要寫 --reason（裁定 seq 與改了什麼）")
        hist = json.load(open(LOCK, encoding="utf-8")).get("history", []) if os.path.exists(LOCK) else []
        hist.append({"時間": time.strftime("%Y-%m-%d %H:%M", time.localtime()), "原因": a.reason, "變動": check() if hist else ["初次上鎖"]})
        json.dump({"roots": ROOTS, "files": digest(), "history": hist}, open(LOCK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"已鎖 {len(digest())} 支：{a.reason}")
        return
    if a.list:
        for m, h in digest().items():
            print(f"{m}.py {h}")
        return
    if not os.path.exists(LOCK):                                        # 雲端 sparse checkout 沒帶鎖檔 ⇒ 無法檢查（exit 2），⛔ 不當成「不符」（情報 1020-0159）
        print("策略鎖：沒有鎖檔 strategy_lock.json，本次無法檢查")
        sys.exit(2)
    d = check()
    if d:
        print("⚠ 策略鎖不符：" + "；".join(d))
        sys.exit(1)
    print(f"策略鎖相符（{len(digest())} 支）")


if __name__ == "__main__":
    main()
