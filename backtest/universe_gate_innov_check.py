# -*- coding: utf-8 -*-
"""universe_gate 補認「-KY創」開關（innov_ky，預設關）的 fixture 與閘門（裁定 seq271 §二；照共用引擎閘門）。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/universe_gate_innov_check.py

G0 fixture：名稱「測試創意公司」「某某KY創新」「測試-KY」留；「測試科技*-創」剔（開關關／開都剔）；「測試-KY創」關 ⇒ 留、開 ⇒ 剔；「測試存託-DR」第二道剔
G1 開關關 ＝ HEAD 版 universe_gate（git show HEAD:backtest/universe_gate.py）逐位元：
   五份 stocks 表（origin/main、edc6f 快照、0652e3e4f4 archive、早年 3edc0e2206、早年 950ad26e12）的 gate3 輸出 assert_frame_equal（exact）；
   全期每個量測日（resultsp9_engine/panel_ext、resultsAFC/panel、早年 sig_main/panel）：當日面板股票 ∩ gate3 名單 ⇒ HEAD 版 ＝ 新版（關）
G2 開關開：只多剔 4 檔（6854、6924、7823、7827）；列出各檔 first_seen～last_seen 與出現在各面板的量測日範圍（eligible 者另列）
G3 既有研究（開關關）：營量 v1 T1 種子 0（listexit_lines.setup_t1(t1=True)、stop_force 開）eq_sha ＝ resultsT1fix c13 t1 r0；
   另一件在執行當下呼叫 gate3 的：researchMomX 主世界 M1_F6_季_N20 三段年化 ＝ resultsMomX/cells.csv（repr）
⇒ backtest/resultsGateInnov/GATE.md、gate.json
"""
import hashlib
import io
import json
import os
import subprocess
import sys
import types

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import universe_gate as UG
from backtest import rerun17 as RR

OUT = "backtest/resultsGateInnov"
os.makedirs(OUT, exist_ok=True)
KY4 = ["6854", "6924", "7823", "7827"]
res = {}; errs = []

# HEAD 版
src = subprocess.run(["git", "show", "HEAD:backtest/universe_gate.py"], capture_output=True, text=True).stdout
assert "def gate3" in src
HM = types.ModuleType("ug_head"); HM.__dict__["__name__"] = "ug_head"
exec(compile(src.replace("from . import data as D", "from backtest import data as D"), "ug_head", "exec"), HM.__dict__)

# G0
fx = pd.DataFrame([dict(stock_id=s, name=n, market="twse", kind="stock", first_seen="2020-01-01", last_seen="2026-09-23") for s, n in (
    ("99991", "測試創意公司"), ("99992", "測試科技*-創"), ("99993", "測試存託-DR"), ("99994", "測試-KY創"), ("99995", "某某KY創新"), ("99996", "測試-KY"))])
off = list(UG.gate3(fx)["stock_id"]); on = list(UG.gate3(fx, innov_ky=True)["stock_id"]); hd = list(HM.gate3(fx)["stock_id"])
res["G0 fixture"] = {"關": off, "開": on, "HEAD": hd}
if not (off == hd == ["99991", "99994", "99995", "99996"] and on == ["99991", "99995", "99996"]):
    errs.append("G0")

# G1、G2
ms = UG.main_stocks()
tabs = {"origin/main": ms,
        "edc6f 快照": pd.read_csv(os.path.join(RR.H2D, "meta", "stocks.csv"), dtype=str),
        "0652e3e4f4 archive": pd.read_csv(os.path.expanduser("~/h2data/0652e3e4f419c78a6a9f6802095a2d97bfd22d9a/data/meta/stocks.csv"), dtype=str),
        "早年 3edc0e2206": pd.read_csv(os.path.expanduser("~/earlydata/3edc0e2206/main/data/meta/stocks.csv"), dtype=str),
        "早年 950ad26e12": pd.read_csv(os.path.expanduser("~/earlydata/950ad26e12/main/data/meta/stocks.csv"), dtype=str)}
g1 = {}; G_off = {}; G_on = {}
for k, t in tabs.items():
    a = HM.gate3(t); b = UG.gate3(t); c = UG.gate3(t, innov_ky=False)
    UG.set_innov_ky(False); d = UG.gate3(t)
    ok = True
    for x in (b, c, d):
        try:
            pd.testing.assert_frame_equal(a, x, check_exact=True)
        except AssertionError:
            ok = False
    e = UG.gate3(t, innov_ky=True)
    extra = sorted(set(a["stock_id"]) - set(e["stock_id"]))
    g1[k] = {"HEAD 檔數": len(a), "關 逐位元相同": ok, "開 檔數": len(e), "開 多剔": extra}
    if not ok:
        errs.append(f"G1 {k}")
    if k in ("origin/main", "edc6f 快照", "0652e3e4f4 archive") and extra != sorted(set(KY4) & set(a["stock_id"])):
        errs.append(f"G2 {k} 多剔 {extra}")
    if k.startswith("早年") and extra:
        errs.append(f"G2 {k} 早年不該有 {extra}")
    G_off[k] = set(a["stock_id"]); G_on[k] = set(e["stock_id"])
res["G1 五份 stocks 表"] = g1
# 每個量測日
panels = {"panel_ext（edc6f）": ("backtest/resultsp9_engine/panel_ext.csv.gz", "edc6f 快照"), "resultsAFC/panel（edc6f）": ("backtest/resultsAFC/panel.csv.gz", "edc6f 快照"),
          "早年 sig_main/panel（3edc0e2206）": (os.path.expanduser("~/earlydata/3edc0e2206/sig_main/panel.csv.gz"), "早年 3edc0e2206")}
pm = {}; rng = {}
for nm, (p, tk) in panels.items():
    P = pd.read_csv(p, dtype={"stock_id": str}, usecols=lambda c: c in ("measure_date", "stock_id", "eligible"))
    t = tabs[tk]; hs = set(HM.gate3(t)["stock_id"]); ns = set(UG.gate3(t)["stock_id"]); os_ = set(UG.gate3(t, innov_ky=True)["stock_id"])
    bad = 0; nd = 0
    for d, g in P.groupby("measure_date"):
        ids = set(g["stock_id"]); nd += 1
        if (ids & hs) != (ids & ns):
            bad += 1
    pm[nm] = {"量測日": nd, "HEAD vs 關 不同的量測日": bad}
    if bad:
        errs.append(f"G1 {nm}")
    for s in KY4:
        g = P[P["stock_id"] == s]
        if len(g):
            el = g[g["eligible"].astype(str).isin(["True", "1", "1.0"])] if "eligible" in g else g.iloc[0:0]
            rng.setdefault(s, {})[nm] = {"在面板": [str(g["measure_date"].min())[:10], str(g["measure_date"].max())[:10], int(len(g))],
                                         "eligible": ([str(el["measure_date"].min())[:10], str(el["measure_date"].max())[:10], int(len(el))] if len(el) else None)}
res["G1 每個量測日"] = pm
st = ms.set_index("stock_id")
res["G2 開 多剔的 4 檔"] = {s: {"名稱": st.loc[s, "name"], "市場": st.loc[s, "market"], "first_seen～last_seen": [st.loc[s, "first_seen"], st.loc[s, "last_seen"]],
                               "面板": rng.get(s, {})} for s in KY4}

# G3
from backtest import listexit_lines as L
from backtest import research11 as R
UG.set_innov_ky(False)
ctx = L.setup_t1(lambda x: None, t1=True)
G = RR._G; A = G["AND"]; e = A["entry_pos"].to_numpy(); sig = A[(e >= G["w0"]) & (e <= G["w1"])]
SF = R.stop_force_days(R.valid_from_data(sorted(ctx["closes"]), ctx["mk"], ctx["cal"]), G["w1"])
o = R.simulate_mtm(sig, "H60", 20, np.random.default_rng(7000), ctx["closes"], ctx["opens"], ctx["ncal"], return_equity=True, log=[], d_max=None,
                   pick="relvol", queue_days=0, stop_force=SF)
sh = hashlib.sha256(np.asarray(o["equity"], float).tobytes()).hexdigest()[:16]
ref = pd.read_csv("backtest/resultsT1fix/seeds.csv.gz", dtype={"eq_sha": str})
ref = ref[(ref["key"] == "c13") & (ref["var"] == "t1") & (ref["r"] == 0)]["eq_sha"].iloc[0]
res["G3 營量 v1 T1 種子 0 eq_sha（關）"] = [sh, ref, sh == ref]
if sh != ref:
    errs.append("G3 營量")
from backtest import researchMomX as MX
Wd = MX.load_world(MX.MAIN, 2, lambda x: None)
cal = Wd["cal"]
SEGP = {nm: (max(int(cal.searchsorted(pd.Timestamp(x))), Wd["w0"]), min(int(cal.searchsorted(pd.Timestamp(y), side="right") - 1), Wd["w1"])) for nm, (x, y) in MX.MAIN["segs"].items()}
TB = MX.rank_tables(Wd, 6); sel, _ = MX.select(Wd, TB, "M1", 6, "季", 20); rr = MX.sim_book(sel, Wd, 20)
cm = pd.read_csv("backtest/resultsMomX/cells.csv", float_precision="round_trip")
mo = {}
for nm, (x, y) in SEGP.items():
    stt = MX.seg_stats(Wd, rr, x, y, 20, [e_ for e_ in sorted(sel) if x <= e_ <= y])
    q = cm[(cm["世界"] == "主") & (cm["格"] == "M1_F6_季_N20") & (cm["段"] == nm)].iloc[0]
    mo[nm] = [float(stt["年化"]), float(q["年化"]), repr(float(stt["年化"])) == repr(float(q["年化"]))]
    if not mo[nm][2]:
        errs.append(f"G3 MomX {nm}")
res["G3 researchMomX M1_F6_季_N20（關；執行當下呼叫 gate3）"] = mo
res["母體影響（開）：MomX 主世界母體裡的 4 檔"] = sorted(set(KY4) & set(Wd["sids"]))
res["錯誤數"] = len(errs); res["錯誤"] = errs
json.dump(res, open(os.path.join(OUT, "gate.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
NL = "\n"
md = ["# 共用閘 exclude_innovation 補認「-KY創」（開關 innov_ky，預設關）", "",
      f"裁定 seq271 §二；照共用引擎閘門。產出 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）。回測線。", "",
      f"**結論：{'全過' if not errs else '⛔ 不過：' + '、'.join(errs)}。開關關 ⇒ 五份 stocks 表與全期每個量測日都與 HEAD 版逐位元相同；開 ⇒ 只多剔 4 檔（{'、'.join(KY4)}）；"
      f"營量 v1 T1 種子 0 eq_sha 不變；researchMomX M1 三段年化不變。**", "",
      "## 用法（新跑的件擇一；已判件不重跑）", "", "```", "from backtest import universe_gate as UG", "UG.set_innov_ky(True)          # 全域：之後所有 gate3／exclude_innovation 都剔「-創」＋「-KY創」",
      "uni = UG.gate3(stocks, innov_ky=True)   # 或單次", "```", "",
      "- 呼叫點：repo 裡 106 個 .py 經 gate3（第三道只在 universe_gate 內部呼叫 exclude_innovation）⇒ 全域開關一次涵蓋，⛔ 不必逐檔改。",
      "- ⚠ 用快取訊號／面板的件（resultsN17/sig_edc6f、resultsAFC/panel、resultsp9_engine/panel_ext 等）是舊閘建的 ⇒ 要重建快取，開關才會真的剔掉這 4 檔。", "",
      "## G0 fixture", "", "```", json.dumps(res["G0 fixture"], ensure_ascii=False), "```", "",
      "## G1 開關關 ＝ HEAD 版", "", "```", json.dumps(res["G1 五份 stocks 表"], ensure_ascii=False, indent=1), json.dumps(pm, ensure_ascii=False), "```", "",
      "## G2 開 多剔的 4 檔與日期範圍", "", "```", json.dumps(res["G2 開 多剔的 4 檔"], ensure_ascii=False, indent=1), "```", "",
      "## G3 既有研究（開關關）", "", f"- 營量 v1 T1 種子 0 eq_sha：{res['G3 營量 v1 T1 種子 0 eq_sha（關）']}",
      f"- researchMomX M1_F6_季_N20 三段年化（自跑／cells.csv／相同）：{json.dumps(mo, ensure_ascii=False)}", f"- MomX 主世界母體裡的 4 檔：{res['母體影響（開）：MomX 主世界母體裡的 4 檔']}", ""]
open(os.path.join(OUT, "GATE.md"), "w", encoding="utf-8").write(NL.join(md))
print(md[4]); [print("  ⛔", e) for e in errs]
