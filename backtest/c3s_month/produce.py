# -*- coding: utf-8 -*-
"""月底 M 的正式產出（全部寫到 --stage，⛔ 不寫 repo；複製進 repo 由 run_c3s_month.sh 在驗算通過後做）。
程式 ＝ f56133f55a（~/c3s_f561），各支照原入口同一函式：
  ① 換股單（舊版、產單用）：researchUSC3s_ops.run_month(M, "main")        ＝ `researchUSC3s_ops --month M`
  ② 換股單（新版 e71b5bc77e，只多「全名」欄）：git show 取該版 researchUSC3s_ops.py 原文載入，同一 run_month（依賴模組 ＝ f56133f55a 同一份）
  ③ C3sF：forward_us_c3sf.update(M, root＝截到 M 的快照)                  ＝ `forward_us_c3sf --month M --root …`
  ④ C11：forward_us_c11.update(M, root＝同上)                              ＝ `forward_us_c11 --month M --root …`
  ⑤ 停用條件：前瞻 ② 簿 researchUSC3s_stop.month_level／level_line(M)       ＝ `researchUSC3s_stop --month M`
             主臂續抱簿（＝ 換股單同一簿）＝ b1030/finalize.py 同式（tables(virtual_e) → run_book → SR.path_stats → SR.levels，x、Dmax 寫死常數）
⇒ stage/summary.json（之後 inject.py、finalize.py 讀）。只印代號、排名、級別、濾網，⛔ 不印報酬。

    cd ~/c3s_f561 && US_DATA_ROOT_A2=<root> C3S_RUN_TS="YYYY-MM-DD HH:MM" python produce.py --month M --root <root> --world <dir> --stage <dir>
"""
import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c3sm_common as CM  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--month", required=True)
ap.add_argument("--root", required=True)
ap.add_argument("--world", required=True)
ap.add_argument("--stage", required=True)
a = ap.parse_args()
M = a.month; MD = M.replace("-", "")
os.makedirs(a.stage, exist_ok=True)
A4, K = CM.setup(a.world, a.root)
import numpy as np  # noqa: E402
from backtest import researchUSC3s_ops as OPS  # noqa: E402
from backtest import researchStopRule as SR  # noqa: E402
from backtest import researchUSC3s_stop as ST  # noqa: E402
from backtest import forward_us_c3sf as F  # noqa: E402
from backtest import forward_us_c11 as C11  # noqa: E402
CM.patch_forward_now(F, C11)

S = {"月底": M, "記錄時間": os.environ.get("C3S_RUN_TS"), "資料根": a.root, "資料commit": open(os.path.join(a.root, ".commit")).read().strip(),
     "world": {"路徑": os.path.join(a.world, "world.npz"), "sha256": CM.sha256f(os.path.join(a.world, "world.npz"))}}
R = K.rworld(); cal = R["cal"]
S["world"]["cal最後"] = str(cal[-1].date())
if S["world"]["cal最後"] != M:
    raise SystemExit(f"world cal 最後一日 {cal[-1].date()} ≠ 月底 {M}")
f561_head = subprocess.run(["git", "-C", CM.F561, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
dirty = subprocess.run(["git", "-C", CM.F561, "status", "--porcelain", "--", "backtest"], capture_output=True, text=True).stdout.strip()
if not f561_head.startswith(CM.OLD_REV) or dirty:
    raise SystemExit(f"~/c3s_f561 不是乾淨的 {CM.OLD_REV}（HEAD {f561_head[:10]}；改動 {dirty[:200]}）")
S["程式"] = {"舊版": f561_head, "ops檔": OPS.__file__}

# ① 舊版換股單
OPS.OPSD = os.path.join(a.stage, "ops_old")
v_old = OPS.run_month(M, "main")
p_old = os.path.join(OPS.OPSD, f"order_{MD}.csv")

# ② 新版（e71b5bc77e 原文；NAMES_CSV ＝ ~/tw-p17/backtest/forward/us_names.csv）
src = subprocess.run(["git", "-C", CM.REPO, "show", f"{CM.NEW_REV}:backtest/researchUSC3s_ops.py"], capture_output=True, text=True, check=True).stdout
head_blob = subprocess.run(["git", "-C", CM.REPO, "rev-parse", "HEAD:backtest/researchUSC3s_ops.py"], capture_output=True, text=True).stdout.strip()
new_blob = subprocess.run(["git", "-C", CM.REPO, "rev-parse", f"{CM.NEW_REV}:backtest/researchUSC3s_ops.py"], capture_output=True, text=True).stdout.strip()
NEW = types.ModuleType("backtest.researchUSC3s_ops_new")
NEW.__file__ = os.path.join(CM.REPO, "backtest", "researchUSC3s_ops.py")
NEW.__package__ = "backtest"
sys.modules[NEW.__name__] = NEW
exec(compile(src, NEW.__file__, "exec"), NEW.__dict__)
NEW.OPSD = os.path.join(a.stage, "ops_new")
v_new = NEW.run_month(M, "main")
p_new = os.path.join(NEW.OPSD, f"order_{MD}.csv")
S["程式"].update({"新版": CM.NEW_REV, "新版 blob": new_blob, "主工作樹 HEAD blob": head_blob, "HEAD 與新版同": head_blob == new_blob,
                 "us_names.csv": {"路徑": NEW.NAMES_CSV, "sha256": CM.sha256f(NEW.NAMES_CSV) if os.path.exists(NEW.NAMES_CSV) else None}})
S["換股單"] = {"舊版raw": {"路徑": p_old, "sha256": CM.sha256f(p_old)}, "新版raw": {"路徑": p_new, "sha256": CM.sha256f(p_new)},
             "view舊": v_old, "view新": v_new}

# ③ C3sF
fw = os.path.join(a.stage, "us_c3sf"); priv = os.path.join(a.stage, "priv")
if not os.path.exists(fw):
    shutil.copytree(os.path.join(CM.REPO, "backtest", "forward", "us_c3sf"), fw)
ft = F.spy_filter_table(a.root)
r = F.decide(ft, M)
if r is None:
    raise SystemExit(f"SPY {M} 無資料或 200 日線不可算")
st_f = F.update(M, root=a.root, fwd=fw, priv=priv)
rows = list(csv.DictReader(open(os.path.join(fw, "filter.csv"), encoding="utf-8-sig")))
led = next((x for x in rows if x["月底"] == M), None)
S["C3sF"] = {"現算": {"SPY還原收盤": repr(r[0]), "SPY200日線": repr(r[1]), "濾網": "擋" if r[2] else "不擋"}, "紀錄列": led,
             "state": {k: st_f.get(k) for k in ("濾網已記月底", "權益已記期數", "world 最後一日", "SPY／DTB3 資料commit", "狀態") if k in st_f}}

# ④ C11
fw11 = os.path.join(a.stage, "us_c11")
if not os.path.exists(fw11):
    shutil.copytree(os.path.join(CM.REPO, "backtest", "forward", "us_c11"), fw11)
st11 = C11.update(M, root=a.root, fwd=fw11, priv=priv)
S["C11"] = {k: st11.get(k) for k in ("狀態", "記到月底", "期數", "資料最後一日", "資料commit") if k in st11}

# ⑤ 停用條件
Mi, _v = OPS.month_end_index(M)
T = OPS.tables(virtual_e=True); t0 = T["t0"]; a0 = t0 - 1
eq = OPS.run_book(T, t0, Mi)[0]["eq"]
MEs = ST.month_ends(cal, a0, Mi) + [Mi]
st = SR.path_stats(eq, R["B"], a0, Mi, MEs); lv = SR.levels(st["RJ"], st["D"], ST.X_FIX, ST.DMAX_FIX)
L = lv[-1]["L"]; why = lv[-1]["why"] or "正常"
line = f"停用條件級別：{L}（{why}；{ST.ACT[L]}）" if L else "停用條件級別：0（正常）"
fwd = ST.month_level(M)
S["停用條件"] = {"主臂": {"月序": len(MEs), "R_類": str(st["kind"][-1]), "R12": float(st["R12"][-1]), "D": float(st["D"][-1]),
                        "T1": bool(lv[-1]["t1"]), "T2警戒": bool(lv[-1]["warn"]), "T2停用": bool(lv[-1]["stop"]),
                        "判前級": lv[-1]["prev"], "判後級": L, "原因": why, "一行": line},
               "前瞻②": {"級別": fwd["級別"], "原因": fwd["原因"], "R": fwd.get("R"), "D": fwd.get("D"), "一行": ST.level_line(M)},
               "x": ST.X_FIX, "Dmax": ST.DMAX_FIX, "ACT": ST.ACT}
json.dump(S, open(os.path.join(a.stage, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=K._jdef)
print("產出：換股單 舊", S["換股單"]["舊版raw"]["sha256"][:12], "新", S["換股單"]["新版raw"]["sha256"][:12],
      "｜C3sF", S["C3sF"]["現算"]["濾網"], "｜主臂", line, "｜前瞻②", S["停用條件"]["前瞻②"]["一行"])
