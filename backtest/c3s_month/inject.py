# -*- coding: utf-8 -*-
"""注入驗算（⛔ 不寫 repo）：＝ ~/us_work/c/c3s/ops/b1030/inject.py 同一做法，月底改成參數。
世界尾端與 SPY 尾端加 M 之後 20 個交易日的假列（KIND＝ones：價格全 1；rand：亂數），f56133f55a 版函式重產 M 的換股單、C3sF 濾網列、停用條件級別，
與 produce.py 的正式產出（stage/summary.json、舊版 raw 換股單）比對。輸出只寫 --out。

判準（finalize.py 用）：
  換股單 proxy 模式（＝ 正式單的做法：e 開盤 ≈ 月底收盤，只用 ≤ M 的資料）除構造欄外逐欄相同；
  構造欄 ＝ 換股日、月底、記錄時間、備註（e 在不在資料內才不同）。
  auto 模式（e 在資料內 ⇒ exact，用假的 e 開盤價成交）只記錄差異、不當判準：有賣有買的月份，賣出所得 ＝ 股數 × 假開盤價，買得到幾檔本來就會跟著假價變。
  C3sF：M 的濾網（擋／不擋、SPY 還原收盤、200 日線）相同。停用條件：主臂判後級、原因、R12、D 相同；前瞻 ② 簿級別、原因相同。

    cd ~/c3s_f561 && US_DATA_ROOT_A2=<root> python inject.py --kind ones|rand --month M --root <root> --world <dir> --stage <produce 的 stage> --out <dir>
"""
import argparse
import csv
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c3sm_common as CM  # noqa: E402
import c3sm_cal as CAL  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--kind", choices=("ones", "rand"), required=True)
ap.add_argument("--month", required=True)
ap.add_argument("--root", required=True)
ap.add_argument("--world", required=True)
ap.add_argument("--stage", required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()
KIND, M = a.kind, a.month
OUT = a.out; shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT)
A4, K = CM.setup(a.world, a.root)
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

z = np.load(os.path.join(a.world, "world.npz"), allow_pickle=False)
Wd = {k: z[k] for k in z.files}
cal0 = pd.DatetimeIndex(Wd["cal"]); assert str(cal0[-1].date()) == M, (cal0[-1], M)
fake = pd.DatetimeIndex([pd.Timestamp(d) for d in CAL.next_days(CAL._d(M), 20)])
k = len(fake); S_ = Wd["tick"].shape[0]
rng = np.random.default_rng(int(M.replace("-", "")) + (0 if KIND == "ones" else 1))
for key in list(Wd):
    if key in ("tick", "cal"):
        continue
    arr = Wd[key]
    if key in ("valid",):
        add = np.repeat(arr[-1:], k, axis=0)     # M 有 K 棒者假列都有效；已下市者維持無效（⛔ 不讓死股復活）
    elif key in ("m5", "m4"):
        add = np.repeat(arr[-1:], k, axis=0)
    elif key in ("pb", "f50"):
        add = np.zeros((k, S_), bool)
    elif key == "DIV":
        add = np.zeros((k, S_), arr.dtype)
    else:
        add = (np.ones((k, S_)) if KIND == "ones" else rng.lognormal(0, 1, (k, S_))).astype(arr.dtype)
    Wd[key] = np.vstack([arr, add])
Wd["cal"] = pd.DatetimeIndex(np.concatenate([cal0.values, fake.values]))
# ＝ A4.load_world 後段同式
Wd["ix"] = {t: j for j, t in enumerate(Wd["tick"])}
Wd["CF"] = pd.DataFrame(Wd["C"]).ffill().to_numpy()
v = Wd["valid"]; n = v.shape[0]
last = np.full(v.shape[1], -1); first = np.full(v.shape[1], n); anyv = v.any(axis=0)
last[anyv] = n - 1 - np.argmax(v[::-1, :][:, anyv], axis=0); first[anyv] = np.argmax(v[:, anyv], axis=0)
Wd["last"] = last; Wd["first"] = first; Wd["mem"] = Wd["m5"] | Wd["m4"]
A4._WD[""] = Wd
# SPY 假列
root0 = a.root; iroot = os.path.join(OUT, "root")
os.makedirs(os.path.join(iroot, "data", "macro"))
shutil.copy(os.path.join(root0, ".commit"), iroot)
spy = open(os.path.join(root0, "data", "macro", "yahoo_SPY.csv"), encoding="utf-8").read()
hdr = spy.splitlines()[0].split(",")
rows = []
for d in fake:
    val = "1.0" if KIND == "ones" else repr(float(rng.lognormal(6, 1)))
    rows.append(",".join(d.strftime("%Y-%m-%d") if c == "date" else ("1" if c == "volume" else val) for c in hdr))
open(os.path.join(iroot, "data", "macro", "yahoo_SPY.csv"), "w", encoding="utf-8").write(spy.rstrip("\n") + "\n" + "\n".join(rows) + "\n")
shutil.copy(os.path.join(root0, "data", "macro", "fred_DTB3.csv"), os.path.join(iroot, "data", "macro"))

from backtest import researchUSC3s_ops as OPS  # noqa: E402
from backtest import researchStopRule as SR  # noqa: E402
from backtest import researchUSC3s_stop as ST  # noqa: E402
from backtest import forward_us_c3sf as F  # noqa: E402
from backtest import forward_us_c11 as C11  # noqa: E402
CM.patch_forward_now(F, C11)
R = K.rworld(); cal = R["cal"]
Mi = int(cal.searchsorted(pd.Timestamp(M)))
S = json.load(open(os.path.join(a.stage, "summary.json"), encoding="utf-8"))
real = list(csv.reader(open(S["換股單"]["舊版raw"]["路徑"], encoding="utf-8-sig")))
rc, rr = real[0], dict(zip(real[0], real[1]))
by_constr = {3, 4, 24, 25}       # 換股日（資料內 vs 資料外）、月底、記錄時間、備註（「e 在資料外」字樣）
rep = {"KIND": KIND, "假列": [str(fake[0].date()), str(fake[-1].date()), k], "注入後 cal 最後": str(cal[-1].date())}
tick = R["Wd"]["tick"]
for mode in ("auto", "proxy"):
    o, T = OPS.order_for(Mi, "main", mode)
    cols, row = OPS.order_row(o, T)
    assert cols == rc
    diff = [(c, rr[c], row[c]) for c in cols if rr[c] != row[c]]
    rep[mode] = {"實際模式": o["mode"], "不同欄": diff, "除構造欄外相同": all(rc.index(c) in by_constr for c, _, _ in diff),
                 "賣": [str(tick[j]) for j, _ in o["sells"]], "買": [str(tick[j]) for j in o["buys"]],
                 "換股後持股": [str(tick[j]) for j in o["after"]], "候補": [str(tick[j]) for j in o["cand"]]}
# C3sF：同一 update() 寫到 OUT（⛔ 不寫 repo）
F.update(M, root=iroot, fwd=os.path.join(OUT, "us_c3sf"), priv=os.path.join(OUT, "priv"))
fi = [x for x in csv.DictReader(open(os.path.join(OUT, "us_c3sf", "filter.csv"), encoding="utf-8-sig")) if x["月底"] == M]
rep["C3sF filter 列"] = fi[0] if fi else None
# 停用條件：主臂續抱簿至 M（M 已是「已結束月底」）
T = OPS.tables(); t0 = T["t0"]; a0 = t0 - 1
eq = OPS.run_book(T, t0, Mi)[0]["eq"]
MEs = ST.month_ends(cal, a0, Mi)
assert MEs[-1] == Mi, "注入後 M 應為已結束月底"
st = SR.path_stats(eq, R["B"], a0, Mi, MEs); lv = SR.levels(st["RJ"], st["D"], ST.X_FIX, ST.DMAX_FIX)
rep["主臂"] = {"R12": float(st["R12"][-1]), "D": float(st["D"][-1]), "判後級": lv[-1]["L"], "原因": lv[-1]["why"] or "正常", "月序": len(MEs)}
fw = ST.month_level(M)
rep["前瞻②"] = {"級別": fw["級別"], "原因": fw["原因"]}
json.dump(rep, open(os.path.join(OUT, "inject.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
print(f"注入 {KIND}：proxy 除構造欄外相同 {rep['proxy']['除構造欄外相同']}｜auto({rep['auto']['實際模式']}) {rep['auto']['除構造欄外相同']}"
      f"｜濾網 {fi[0]['濾網'] if fi else None}｜主臂級 {rep['主臂']['判後級']}｜前瞻② {rep['前瞻②']['級別']}")
