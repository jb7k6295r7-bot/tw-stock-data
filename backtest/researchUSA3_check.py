# -*- coding: utf-8 -*-
"""USREG-A3 獨立查核總表：呼叫各分檔的 check()（各自用獨立寫法抽樣重算，⛔ 不走主程式算報酬的函式）＋ 私有資料掃描。

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSA3_check [--only g1,g2,...]

私有資料掃描（resultsUSA34/A3/）：總量 < 10MB；CSV 不得有逐檔／逐日欄（sid、ticker、代號、date、T_date、日期、close、open、equity）；
JSON 不得有長度 > 400 的數列（逐日序列）；不得出現 ~/us_work 以外的逐筆檔。
"""
from __future__ import annotations

import gzip
import importlib
import io
import json
import os
import sys
import traceback

OUT = os.path.expanduser("~/tw-p17/backtest/resultsUSA34/A3")
MOD = {"g1": "backtest.researchUSA3_g1", "g2": "backtest.researchUSA3_g2", "g3": "backtest.researchUSA3_g3", "g4": "backtest.researchUSA3_g4",
       "surge": "backtest.researchUSA3_surge"}
BAD_COLS = {"sid", "ticker", "代號", "date", "t_date", "日期", "close", "open", "equity", "收盤", "開盤"}


def scan():
    tot = 0; bad = []
    for root, _, fs in os.walk(OUT):
        for f in fs:
            p = os.path.join(root, f); tot += os.path.getsize(p)
            if f.endswith(".csv") or f.endswith(".csv.gz"):
                raw = gzip.open(p, "rb").read() if f.endswith(".gz") else open(p, "rb").read()
                head = raw.decode("utf-8-sig", errors="replace").splitlines()[0] if raw else ""
                cols = {c.strip().strip('"').lower() for c in head.split(",")}
                hit = cols & BAD_COLS
                if hit:
                    bad.append((f, "逐檔／逐日欄 %s" % sorted(hit)))
            elif f.endswith(".json"):
                try:
                    J = json.load(open(p, encoding="utf-8"))
                except Exception as e:                      # noqa
                    bad.append((f, "JSON 讀不了 %s" % e)); continue
                stack = [J]
                while stack:
                    x = stack.pop()
                    if isinstance(x, dict):
                        stack.extend(x.values())
                    elif isinstance(x, list):
                        if len(x) > 400 and all(isinstance(v, (int, float)) for v in x[:50]):
                            bad.append((f, "長數列 %d" % len(x))); break
                        stack.extend(x)
    return {"總量MB": round(tot / 1e6, 3), "<10MB": tot < 10e6, "可疑": bad, "通過": (tot < 10e6) and not bad}


def main():
    only = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else list(MOD)
    res = {}
    for g in only:
        try:
            m = importlib.import_module(MOD[g])
            r = m.check()
            res[g] = r if isinstance(r, (list, dict)) else {"結果": str(r)}
        except Exception as e:                              # noqa
            res[g] = {"錯誤": repr(e), "trace": traceback.format_exc()[-800:]}
        print(g, json.dumps(res[g], ensure_ascii=False, default=str)[:600], flush=True)
    sc = scan()

    def diffs(x):
        if isinstance(x, list):
            return sum(diffs(v) for v in x)
        if isinstance(x, dict):
            if "錯誤" in x:
                return 10 ** 6
            if "不同" in x:
                return int(x["不同"])
            return sum(diffs(v) for v in x.values() if isinstance(v, (dict, list)))
        return 0
    nd = diffs(res)
    out = {"各組": res, "不同合計": nd, "私有資料掃描": sc, "全部通過": bool(nd == 0 and sc["通過"])}
    path = os.path.join(OUT, "check.json")
    old = json.load(open(path, encoding="utf-8")) if (os.path.exists(path) and "--only" in sys.argv) else None
    if old:
        old["各組"].update(res); old["不同合計"] = diffs(old["各組"]); old["私有資料掃描"] = sc
        old["全部通過"] = bool(old["不同合計"] == 0 and sc["通過"]); out = old
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("不同合計", out["不同合計"], "私有掃描", sc, "全部通過", out["全部通過"])


if __name__ == "__main__":
    main()
