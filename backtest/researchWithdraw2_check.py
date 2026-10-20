# -*- coding: utf-8 -*-
"""researchWithdraw2 獨立查核（裁定 seq396 §一）。回測線，2026-10-20。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchWithdraw2_check.py

K1 A 帳戶：v2 重跑的 A 全部格 ＝ resultsWithdraw/grid.csv（逐格逐欄；由兩份 csv 直接比，不經 researchWithdraw2）
K2 B 原版：v2 重跑的 B 原版全部格 ＝ resultsWithdraw/grid.csv
K3 扣費合成獨立重算：直接讀央行 EG41M01 月檔（不經 research64retest_taiex.rates），自寫迴圈 ⇒ 與 synth_daily.csv 扣費主／高費敏感逐日一致；原版欄 ＝ 2r−0.3%/245
K4 接合：B 用 00685L 收盤（扣費）上市前 ＝ k × 扣費合成（k 為常數）；上市日報酬 ＝ 合成當日報酬；上市日起 ＝ 原版（真實 00685L）
K5 抽樣年手算：2008、2016 逐年印 0050 含息報酬、2× 每日重設不扣費、扣費主；ln(不扣費／扣費) ≈ Σ c_t／(1＋2r_t)（c_t ＝ 當日扣費）
K6 對帳獨立重算：真實 00685L 由 tw-stock-data 原始收盤＋data/adj 分割重建 ⇒ 逐年報酬 ＝ synth_recon_yearly.csv；扣費主逐年報酬由 synth_daily 重算一致
K7 累計領現表 ＝ grid（A、B 各版）與 highdiv_side.csv；① 累計領現 ＝ 月數 × 目標
K8 B 扣費格抽查：用 synth_daily.csv 的「B用00685L收盤_扣費」自建 X、呼叫原版 W.sim ⇒ 與 grid_B_compare 一致（2 格）
K9 措辭：run.log 不含「最好」；含兩句附註
K10 原版檔未改：researchWithdraw.py 與 resultsWithdraw/ 頂層檔 sha256 ＝ meta.json 記錄
K11 策略鎖：python -m backtest.strategy_lock --check
"""
import glob
import hashlib
import io
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import researchHighDiv as RH  # noqa: E402
from backtest import researchWithdraw as W  # noqa: E402

HERE = os.path.expanduser("~/tw-p17/backtest")
D0 = os.path.join(HERE, "resultsWithdraw"); D = os.path.join(D0, "v2")
ok_all = []


def chk(name, ok, extra=""):
    ok_all.append(bool(ok)); print(f"[{'OK' if ok else 'NG'}] {name} {extra}")


meta = json.load(open(os.path.join(D, "meta.json"), encoding="utf-8"))
G0 = pd.read_csv(os.path.join(D0, "grid.csv"))
GL = pd.read_csv(os.path.join(D, "grid_v2_long.csv"))
KEYS = ["起點", "帳戶", "每月目標", "稅版", "方法", "水庫利率"]


def same_rows(a, b):
    m = a.merge(b, on=KEYS, suffixes=("_a", "_b")); worst = 0.0; bad = []
    for c in a.columns:
        if c in KEYS or c not in b.columns:
            continue
        x = pd.to_numeric(m[f"{c}_a"], errors="coerce").to_numpy(float); y = pd.to_numeric(m[f"{c}_b"], errors="coerce").to_numpy(float)
        if np.isfinite(x).any() or np.isfinite(y).any():
            if not np.array_equal(np.isfinite(x), np.isfinite(y)):
                bad.append(c); continue
            f = np.isfinite(x)
            worst = max(worst, float(np.max(np.abs(x[f] - y[f]) / np.maximum(1, np.abs(x[f])))) if f.any() else 0.0)
        elif not (m[f"{c}_a"].fillna("").astype(str) == m[f"{c}_b"].fillna("").astype(str)).all():
            bad.append(c)
    return len(m), worst, bad


for acct, nm in (("A", "K1 A 帳戶"), ("B", "K2 B 原版")):
    a = G0[G0["帳戶"] == acct]; b = GL[(GL["合成版"] == "原版") & (GL["帳戶"] == acct)].drop(columns=["合成版"])
    n, w, bad = same_rows(a, b)
    chk(f"{nm} 全部格 ＝ resultsWithdraw/grid.csv", n == len(a) == len(b) == 96 and w < 1e-9 and not bad, f"{n} 格；最大相對差 {w:.1e}；不一致欄 {bad}")

# ── K3 ──
SD = pd.read_csv(os.path.join(D, "synth_daily.csv"), dtype={"date": str})
cal = SD["date"].tolist(); Ac = SD["0050含息還原"].to_numpy(float)
mf = sorted(glob.glob(os.path.expanduser("~/msdata/us_macro/*/cbc_EG41M01_money_market_monthly.csv")))[-1]
mm = pd.read_csv(mf, dtype={"month": str}).set_index("month")["商業本票-初級市場-1-30天"]
mm = pd.to_numeric(mm, errors="coerce")
cp = []
for d in cal:
    y, mo = int(d[:4]), int(d[5:7]); key = f"{y-1}-12" if mo == 1 else f"{y}-{mo-1:02d}"
    cp.append(mm.get(key, np.nan) / 100)
cp = pd.Series(cp).ffill().to_numpy()
days = pd.to_datetime(pd.Series(cal)).diff().dt.days.fillna(0).to_numpy()
for col, fee in (("扣費主（0.34%＋商業本票）", 0.0034), ("扣費高費敏感（1.0%＋商業本票）", 0.010)):
    L = [1.0]
    for t in range(1, len(cal)):
        L.append(L[-1] * (1 + 2 * (Ac[t] / Ac[t - 1] - 1) - (fee + cp[t]) * days[t] / 365))
    L = np.array(L); rel = np.max(np.abs(L / SD[col].to_numpy() - 1))
    chk(f"K3 {col} 獨立重算 ＝ synth_daily", rel < 1e-10, f"最大相對差 {rel:.1e}")
chk("K3 利率欄 ＝ 央行月檔上個月值", np.allclose(cp, SD["商業本票(上月,小數)"].to_numpy(), atol=1e-12))
L = [1.0]
for t in range(1, len(cal)):
    L.append(L[-1] * (1 + 2 * (Ac[t] / Ac[t - 1] - 1) - 0.003 / 245))
rel = np.max(np.abs(np.array(L) / SD["原版（0.3%／245、無資金成本）"].to_numpy() - 1))
chk("K3 原版欄 ＝ 2r − 0.3%／245（research64retest.synth rate＝0）", rel < 1e-10, f"最大相對差 {rel:.1e}")

# ── K4 ──
ts = cal.index(W.LIST685)
k = SD["B用00685L收盤_扣費"].to_numpy()[:ts] / SD["扣費主（0.34%＋商業本票）"].to_numpy()[:ts]
chk("K4 上市前 B 用收盤 ＝ k × 扣費合成（k 常數）", np.ptp(k) / k.mean() < 1e-12, f"k ＝ {k.mean():.6f}")
Cb = SD["B用00685L收盤_扣費"].to_numpy(); Ls = SD["扣費主（0.34%＋商業本票）"].to_numpy()
chk("K4 上市日報酬 ＝ 合成當日報酬", abs(Cb[ts] / Cb[ts - 1] - Ls[ts] / Ls[ts - 1]) < 1e-12, f"{Cb[ts]/Cb[ts-1]-1:.4%}")
chk("K4 上市日起 ＝ 原版（真實 00685L）", np.array_equal(Cb[ts:], SD["B用00685L收盤_原版"].to_numpy()[ts:]))

# ── K5 抽樣年手算 ──
for y in ("2008", "2016"):
    idx = [i for i, d in enumerate(cal) if d[:4] == y]; b = idx[0] - 1 if idx[0] > 0 else 0; e = idx[-1]
    r = Ac[b + 1:e + 1] / Ac[b:e] - 1; c = (0.0034 + cp[b + 1:e + 1]) * days[b + 1:e + 1] / 365
    g0 = np.prod(1 + 2 * r); gc = np.prod(1 + 2 * r - c); syn = Ls[e] / Ls[b]
    approx = np.sum(c / (1 + 2 * r))
    print(f"\n[K5 手算 {y}｜{cal[b]}～{cal[e]}] 0050 含息 {Ac[e]/Ac[b]-1:+.2%}｜2× 每日重設不扣費 {g0-1:+.2%}｜扣費主 {gc-1:+.2%}（synth_daily {syn-1:+.2%}）"
          f"｜當年扣費合計 Σc ＝ {c.sum():.3%}（內扣 0.34%＋商業本票年均 {np.mean(cp[b+1:e+1]):.3%}）")
    chk(f"K5 {y} 手算扣費版 ＝ synth_daily；ln(不扣費／扣費) ≈ Σc／(1＋2r)", abs(gc / syn - 1) < 1e-10 and abs(np.log(g0 / gc) - approx) < 2e-4,
        f"ln 比 {np.log(g0/gc):.5f} vs {approx:.5f}")

# ── K6 對帳 ──
msha = meta["main"]
px = RH.load_px("00685L", msha)["close"].reindex(cal).ffill().to_numpy()
adj = pd.read_csv(io.StringIO(RH.git("show", f"{msha}:data/adj/00685L.csv")), dtype={"date": str})
spl = np.ones(len(cal))
for _, rr in adj.iterrows():
    spl[cal.index(rr["date"])] = round(float(rr["pre_close"]) / float(rr["ref_price"]))
R = np.full(len(cal), np.nan); R[ts] = 1.0
for t in range(ts + 1, len(cal)):
    R[t] = R[t - 1] * px[t] * spl[t] / px[t - 1]
YR = pd.read_csv(os.path.join(D, "synth_recon_yearly.csv"), dtype={"年": str})
good = True
for _, z in YR.iterrows():
    b = cal.index(z["起"]); e = cal.index(z["迄"])
    good &= abs((R[e] / R[b] - 1) - z["真實00685L"]) < 1e-10
    good &= abs((Ls[e] / Ls[b] - 1) - z["扣費主（0.34%＋商業本票）"]) < 1e-10
chk("K6 真實 00685L（原始收盤＋分割重建）與扣費主 逐年報酬 ＝ synth_recon_yearly", good, f"{len(YR)} 年")
nyr = (pd.Timestamp(cal[-1]) - pd.Timestamp(cal[ts])).days / 365.25
bias = (Ls[-1] / Ls[ts]) ** (1 / nyr) - (R[-1]) ** (1 / nyr)
chk("K6 全段年化偏差（扣費主－真實）＝ meta", abs(bias - meta["對帳摘要"]["扣費主（0.34%＋商業本票） 年化偏差（合成－真實）"]) < 1e-12, f"{bias:+.2%}")

# ── K7 累計領現 ──
CC = pd.read_csv(os.path.join(D, "cash_cum.csv"))
HD = pd.read_csv(os.path.join(D0, "highdiv_side.csv"))
g = True
for _, z in CC.iterrows():
    if z["方案"].startswith("高股息"):
        h = HD[(HD["起點"] == z["起點"]) & (HD["稅版"] == z["稅版"]) & (HD["方案"] == z["方案"])]
        g &= len(h) == 1 and abs(h["累計領現（每100萬）"].iloc[0] - z["累計領現（每100萬）"]) < 1e-6
    else:
        tag = "原版" if z["方案"].startswith("A") else z["方案"][z["方案"].index("（") + 1:-1]
        acct = z["方案"][0]
        q = GL[(GL["合成版"] == tag) & (GL["帳戶"] == acct) & (GL["起點"] == z["起點"]) & (GL["稅版"] == z["稅版"]) &
               (GL["每月目標"] == z["每月目標"]) & (GL["方法"] == z["方法"]) & (GL["水庫利率"] == z["水庫利率"])]
        g &= len(q) == 1 and abs(q["累計領現（每100萬）"].iloc[0] - z["累計領現（每100萬）"]) < 1e-6
chk("K7 累計領現表 ＝ grid／highdiv_side", g, f"{len(CC)} 列（高股息 {CC['方案'].str.startswith('高股息').sum()} 列）")
one = CC[CC["方法"] == "①固定金額"].copy()
st = {"2007-12": "2007-12-26", "2015-01": "2015-01-05", "2021-12": "2021-12-01"}
one["月數"] = [(pd.Period(cal[-1][:7]) - pd.Period(st[s][:7])).n + 1 for s in one["起點"]]
chk("K7 ① 累計領現 ＝ 月數 × 目標（無歸零）", np.allclose(one["累計領現（每100萬）"], one["月數"] * one["每月目標"]) and (one["提領到歸零"] == "否").all())

# ── K8 B 扣費抽查 ──
RH.MAIN_REF = msha
calx, pos, X, c4, c5, regime, *_ = W.load_all()
assert list(calx) == cal
X2 = dict(X); x = dict(X["00685L"])
Lo_ratio = None
# 開盤：上市前 ＝ k × 合成開盤（開盤 ＝ L_c[t−1]×(1＋2×隔夜報酬)）
Ao = X["0050"]["Ao"]; kk = k.mean()
O2 = x["O"].copy()
for t in range(1, ts):
    O2[t] = kk * Ls[t - 1] * (1 + 2 * (Ao[t] / Ac[t - 1] - 1)) if np.isfinite(Ao[t]) else np.nan
O2[0] = kk * Ls[0] / (1 + 2 * (Ac[0] / Ao[0] - 1))
x["C"] = Cb.copy(); x["O"] = O2; X2["00685L"] = x
CMP = pd.read_csv(os.path.join(D, "grid_B_compare.csv"))
for sn, tgt, tn, m in (("2007-12", 3404, "淨3.5%", 1), ("2015-01", 4649, "淨11.5%", 4)):
    i0 = pos[st[sn]]
    r = W.sim("B", float(tgt), m, W.TAXV[tn], 0.0, i0, len(cal) - 1, cal, X2, c4, c5, regime)
    s = W.summarize(r, cal, i0, len(cal) - 1)
    z = CMP[(CMP["起點"] == sn) & (CMP["每月目標"] == tgt) & (CMP["稅版"] == tn) & (CMP["方法"] == W.METHODS[m]) & (CMP["水庫利率"] == 0.0)].iloc[0]
    chk(f"K8 B 扣費 {sn} {tgt} {tn} {W.METHODS[m]}（由 synth_daily 自建序列）＝ grid_B_compare",
        abs(s["期末總額（每100萬）"] / z["期末總額（每100萬）｜扣費"] - 1) < 1e-9 and abs(s["最大回落（市值＋水庫）"] - z["最大回落（市值＋水庫）｜扣費"]) < 1e-9,
        f"總額 {s['期末總額（每100萬）']/1e4:.2f} 萬")

# ── K9 措辭 ──
txt = open(os.path.join(D, "run.log"), encoding="utf-8").read()
chk("K9 run.log 不含「最好」、含兩句附註", "最好" not in txt and "00685L 上市前為扣費合成序列（假設：" in txt and "描述，不是買賣建議" in txt)

# ── K10 原版檔未改 ──
cur = {}
for f in [os.path.join(HERE, "researchWithdraw.py")] + sorted(glob.glob(os.path.join(D0, "*.*"))):
    cur[os.path.relpath(f, HERE)] = hashlib.sha256(open(f, "rb").read()).hexdigest()
chk("K10 researchWithdraw.py 與 resultsWithdraw/ 頂層檔未改", cur == meta["原版檔sha256"], f"{len(cur)} 檔")

# ── K11 策略鎖 ──
p = subprocess.run([sys.executable, "-m", "backtest.strategy_lock", "--check"], cwd=os.path.expanduser("~/tw-p17"), capture_output=True, text=True)
chk("K11 策略鎖", p.returncode == 0, (p.stdout + p.stderr).strip()[-200:])
print(f"\n查核結果：{sum(ok_all)}／{len(ok_all)} 通過")
