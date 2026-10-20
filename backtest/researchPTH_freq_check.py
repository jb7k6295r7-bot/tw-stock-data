# -*- coding: utf-8 -*-
"""researchPTH_freq 對帳（接近 52 週新高 PTH seq1 頻率表乾跑，登錄 sha e5d57b29ddb34ee7）——回測線計算子代理。
⛔ 不讀、不算任何進場後價格、報酬、持有期結果。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTH_freq_check
輸出 backtest/resultsPTH/freq/check.json、check.log

K1 抽 40 列（主 24、早年 16；入選 28、非入選 12；default_rng(20261020)），逐筆用【日曆 df 逐列手算】（⛔ 不呼叫 researchPTH_freq 的函式）：
   月底 ＝ 自己對日曆 groupby(年, 月) 取最後一天；窗 ＝ 日期在（前 12 個月底, t］且有成交的還原收盤 ⇒ PTH ＝ c[t] ÷ max；
   12−1 ＝ 前 1 個月底當天或之前最後成交日收盤 ÷ 前 12 個月底當天或之前最後成交日收盤 − 1；
   母體 ＝ 自算 t−20～t−1 日均量 ≥ 500,000 股 ∧ 含 t 的 20 日都有成交 ∧ UG.pit_valid[t]；窗內相鄰成交日的日曆間隔 ≥ 5 個交易日 ＝ 0（缺口壞根部分）。
K2 不前視：同 40 列，把 df 截在 t（只留 ≤ t 的列）重算 PTH、12−1 ⇒ 與全序列相同；進場日 e ＞ t、e ＝ 形成月 ＋1／＋2 個曆月的第一個交易日（自算）。
K3 排序：每世界抽 8 個形成月，從事件檔（排序母體列）重算 n、⌈0.3n⌉、切點、入選集合 ⇒ 與事件檔「入選」欄、monthly.csv 相同。
K4 seq377 等價：從事件檔重算主世界探索段「同一進場月 跳月 vs 不跳」合計交集÷跳月 ⇒ 與 freq.json 相同。
K5 策略鎖：python3 -m backtest.strategy_lock --check 必須相符。
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchAscTri_freq as AT              # noqa: E402  只用 WORLDS 路徑
from backtest import universe_gate as UG                    # noqa: E402
from backtest import data as D                              # noqa: E402

UG.set_gate_v2(True)
OUT = "backtest/resultsPTH/freq"
LOG = []


def log(s):
    print(s, flush=True); LOG.append(str(s))


def my_month_ends(cal):
    df = pd.DataFrame({"d": cal})
    df["ym"] = df["d"].dt.to_period("M")
    return df.groupby("ym")["d"].max()


def hand(sid, market, data, cal, t_date, mes):
    D.DATA = data
    st = D.load_stock(sid, market, cal)
    df = st.df.copy(); df["date"] = cal
    tr = df[df["traded"].astype(bool)]
    ym = pd.Timestamp(t_date).to_period("M")
    s0 = mes[ym - 12]; s1 = mes[ym - 1]
    w = tr[(tr["date"] > s0) & (tr["date"] <= t_date)]
    pth = float(w["close"].iloc[-1] / w["close"].max()) if len(w) and w["date"].iloc[-1] == t_date else np.nan
    a = tr[tr["date"] <= s1]; b = tr[tr["date"] <= s0]
    mom = float(a["close"].iloc[-1] / b["close"].iloc[-1] - 1) if len(a) and len(b) else np.nan
    # 缺口（日曆位置差 − 1 ≥ 5）窗內
    pos = np.flatnonzero(df["traded"].to_numpy(bool))
    wpos = pos[(cal[pos] > s0) & (cal[pos] <= t_date)]
    prev_ok = len(pos[cal[pos] <= s0]) > 0
    gaps = int((np.diff(wpos) - 1 >= 5).sum()) if len(wpos) > 1 else 0
    t = int(cal.searchsorted(t_date))
    v = df["volume"].to_numpy(float); trd = df["traded"].to_numpy(bool)
    gate = bool(t >= 20 and trd[t - 19:t + 1].all() and np.nanmean(v[t - 20:t]) >= 500_000)
    # 截斷
    dft = df.iloc[:t + 1]; trt = dft[dft["traded"].astype(bool)]
    wt = trt[(trt["date"] > s0)]
    pth_t = float(wt["close"].iloc[-1] / wt["close"].max()) if len(wt) else np.nan
    return {"pth": pth, "mom": mom, "gaps": gaps, "gate": gate, "prev_ok": prev_ok, "pth_trunc": pth_t}


def main():
    J = {}
    rng = np.random.default_rng(20261020)
    fj = json.load(open(os.path.join(OUT, "freq.json"), encoding="utf-8"))
    bad = 0
    rows_out = []
    for wn, nsel, nnon in (("主", 16, 8), ("早年", 12, 4)):
        data = AT.WORLDS[wn]["data"]; D.DATA = data
        cal = D.load_calendar()
        mes = my_month_ends(cal)
        st = pd.read_csv(os.path.join(data, "meta", "stocks.csv"), dtype=str)
        mk = dict(zip(st["stock_id"], st["market"]))
        ev = pd.read_csv(os.path.join(OUT, f"events_{wn}.csv.gz"), dtype={"sid": str})
        ev["t"] = pd.to_datetime(ev["形成月底"])
        pick = pd.concat([ev[ev["入選"]].sample(nsel, random_state=int(rng.integers(1e9))),
                          ev[~ev["入選"]].sample(nnon, random_state=int(rng.integers(1e9)))])
        for _, r in pick.iterrows():
            h = hand(r["sid"], mk.get(r["sid"], "twse"), data, cal, r["t"], mes)
            pv = UG.pit_valid(r["sid"], cal, data)
            t = int(cal.searchsorted(r["t"]))
            ok_pth = abs(h["pth"] - r["PTH"]) < 1e-9
            ok_mom = (np.isnan(h["mom"]) and np.isnan(r["mom12_1"])) or abs(h["mom"] - r["mom12_1"]) < 1e-9
            ok_gate = h["gate"] and bool(np.asarray(pv)[t])
            ok_trunc = abs(h["pth_trunc"] - r["PTH"]) < 1e-9
            # 進場日
            ym = r["t"].to_period("M")
            ok_e = True
            for arm, L in (("跳月", 2), ("不跳", 1)):
                ed = r[f"{arm}_進場日"]
                if isinstance(ed, str) and ed:
                    ed = pd.Timestamp(ed)
                    first = cal[(cal.to_period("M") == ym + L)].min()
                    ok_e &= bool(ed > r["t"] and ed == first)
            okall = ok_pth and ok_mom and ok_gate and ok_trunc and ok_e and h["gaps"] == 0 and h["prev_ok"]
            bad += 0 if okall else 1
            rows_out.append({"世界": wn, "sid": r["sid"], "t": str(r["t"].date()), "入選": bool(r["入選"]), "PTH檔": r["PTH"], "PTH手算": h["pth"],
                             "mom檔": r["mom12_1"], "mom手算": h["mom"], "閘手算": ok_gate, "窗內缺口≥5": h["gaps"], "上市滿12月": h["prev_ok"],
                             "截斷PTH相同": ok_trunc, "進場日正確且晚於t": ok_e, "OK": okall})
        log(f"[K1/K2 {wn}] {sum(1 for x in rows_out if x['世界'] == wn and x['OK'])}／{nsel + nnon} 相符")
        # K3
        mon = pd.read_csv(os.path.join(OUT, "monthly.csv"))
        mon = mon[mon["世界"] == wn]
        ms = rng.choice(sorted(ev["形成月底"].unique()), 8, replace=False)
        k3 = []
        for m in ms:
            g = ev[ev["形成月底"] == m]
            n = len(g); k = math.ceil(0.3 * n)
            cut = np.sort(g["PTH"].to_numpy())[::-1][k - 1]
            sel = g["PTH"] >= cut
            mr = mon[mon["形成月底"] == m].iloc[0]
            ok = bool((sel == g["入選"]).all() and n == mr["排序母體"] and int(sel.sum()) == mr["入選"] and abs(cut - mr["切點PTH"]) < 1e-12)
            k3.append({"月": m, "n": n, "k": k, "入選": int(sel.sum()), "OK": ok})
            bad += 0 if ok else 1
        J[f"K3_{wn}"] = k3
        log(f"[K3 {wn}] {sum(x['OK'] for x in k3)}／8 個月排序重算相符")
        # K4
        if wn == "主":
            A = ev[ev["入選"] & (ev["跳月_st"] == "保留")]; B = ev[ev["入選"] & (ev["不跳_st"] == "保留")]
            lo, hi = pd.Timestamp("2017-03-02"), pd.Timestamp("2021-12-30")
            A = A[pd.to_datetime(A["跳月_進場日"]).between(lo, hi)]; B = B[pd.to_datetime(B["不跳_進場日"]).between(lo, hi)]
            ka = set(zip(A["sid"], A["跳月_進場日"])); kb = set(zip(B["sid"], B["不跳_進場日"]))
            es = {e for _, e in ka} & {e for _, e in kb}
            ka2 = {x for x in ka if x[1] in es}; kb2 = {x for x in kb if x[1] in es}
            v = round(len(ka2 & kb2) / len(ka2), 4)
            ref = fj["世界"]["主"]["段"]["探索"]["seq377等價_跳月vs不跳"]["合計交集÷跳月"]
            J["K4"] = {"重算": v, "freq.json": ref, "OK": v == ref}
            bad += 0 if v == ref else 1
            log(f"[K4] 探索段 跳月vs不跳 合計交集÷跳月 重算 {v}｜freq.json {ref}")
    J["K1K2"] = rows_out
    # K5
    p = subprocess.run([sys.executable, "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True)
    J["K5_策略鎖"] = {"rc": p.returncode, "out": (p.stdout + p.stderr)[-800:]}
    log(f"[K5] strategy_lock --check rc={p.returncode}｜{(p.stdout + p.stderr).strip()[-300:]}")
    bad += 0 if p.returncode == 0 else 1
    J["不符項數"] = bad
    log(f"[總] 不符 {bad} 項")
    json.dump(J, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
