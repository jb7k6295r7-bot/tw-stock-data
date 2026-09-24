"""PREREGC3 開跑前置 §九①②：窗首精確日 ＋ 同步率描述（⛔ 純描述、⛔ 不設門檻、⛔ 未算任何報酬）。"""
import os, sys, hashlib
import numpy as np
sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchc3 as C3

os.makedirs(C3.OUT, exist_ok=True)
dates, close, sig, w0s = C3.load_panel()
assert dates[-1] == C3.LAST_FULL, dates[-1]
d = C3.sync_describe(sig)
L = []
A = L.append
A("# PREREGC3 開跑前置：窗首精確日 ＋ 同步率描述\n")
A("⛔ 純描述（登錄 v4 §九①②）；⛔ 不設門檻、⛔ 不進判準、⛔ 本檔產生時【沒有算任何報酬】\n")
A("## §九② 窗首精確日\n")
A("| 幣 | SMA200 首個有值日 |\n|---|---|")
for s in C3.COINS:
    A("| {} | {} |".format(s, w0s[s]))
A("\n⇒ **窗首 ＝ {}**（最晚那一幣）；窗尾 ＝ {}；共 **{} 個交易日**（{} 個報酬期）\n"
  .format(dates[0], dates[-1], len(dates), len(dates) - 1))
A("⭐ 六幣在窗內逐日齊全（交集列數 ＝ 窗首到窗尾日曆日數：{}）\n".format(
  (np.datetime64(dates[-1]) - np.datetime64(dates[0])).astype(int) + 1 == len(dates)))
A("## §九① 同步率（訊號(t)，即收盤 t 決定、t+1 生效的在場集合）\n")
A("| 在場幣數 k | 天數 | 比例 |\n|---|---|---|")
for k in range(7):
    A("| {} | {} | {:.2%} |".format(k, d["dist"][k], d["dist"][k] / d["T"]))
A("\n```")
A("六幣同時在場的天數比例     {:.2%}".format(d["all_in"]))
A("六幣同時空手的天數比例     {:.2%}".format(d["all_out"]))
A("六幣一致（全在或全空）     {:.2%}".format(d["unanimous"]))
A("平均在場幣數               {:.3f}".format(d["mean_n_in"]))
A("兩兩同狀態比例（15 對平均）{:.2%}".format(d["pair_same_mean"]))
A("兩兩 phi 相關（15 對）     平均 {:.3f}　最小 {:.3f}　最大 {:.3f}".format(d["phi_mean"], d["phi_min"], d["phi_max"]))
A("```\n")
A("兩兩同狀態比例：\n")
A("| | " + " | ".join(C3.COINS) + " |")
A("|" + "---|" * 7)
for i, s in enumerate(C3.COINS):
    A("| {} | ".format(s) + " | ".join("{:.1%}".format(d["pair_same"][i, j]) for j in range(6)) + " |")
A("\n⛔ 本檔的任何數字都【不是】通過／退化的判定；依 v4 §2-D 逐字寫進結案措辭，由讀者自行判斷。")
txt = "\n".join(L) + "\n"
p = os.path.join(C3.OUT, "PRE_DESCRIBE.md")
open(p, "w", encoding="utf-8").write(txt)
print(txt)
print("sha16", hashlib.sha256(txt.encode()).hexdigest()[:16])
