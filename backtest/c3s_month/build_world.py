# -*- coding: utf-8 -*-
"""建本期世界檔：＝ f56133f55a 的 `python -m backtest.researchUSA4 --stage world`（同一函式 stage_world），
只把輸出位置 A4.WORK 改到 --out（⛔ 不碰共用 ~/us_work/a4/world.npz；換共用檔由 run_c3s_month.sh 在全部通過後做）。

    cd ~/c3s_f561 && US_DATA_ROOT_A2=<截到 M 的快照> python build_world.py --root <同上> --out <資料夾> --month M [--procs 2]
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c3sm_common as CM  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--root", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--month", required=True)
ap.add_argument("--procs", type=int, default=2)
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
A4, K = CM.setup(a.out, a.root)
T0 = time.time()
A4.stage_world(argparse.Namespace(procs=a.procs, lim=0))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
p = os.path.join(a.out, "world.npz")
z = np.load(p, allow_pickle=False)
last = str(pd.Timestamp(z["cal"][-1]).date())
meta = {"world": p, "sha256": CM.sha256f(p), "cal最後": last, "檔數": int(z["tick"].shape[0]), "資料根": a.root,
        "資料commit": open(os.path.join(a.root, ".commit")).read().strip(), "程式": CM.OLD_REV, "秒": round(time.time() - T0)}
if last != a.month:
    raise SystemExit(f"世界 cal 最後一日 {last} ≠ 月底 {a.month}")
json.dump(meta, open(os.path.join(a.out, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(meta, ensure_ascii=False))
