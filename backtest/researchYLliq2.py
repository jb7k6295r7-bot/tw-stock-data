# -*- coding: utf-8 -*-
"""營量／營飆 v1：營收可用日過 500 張閘、但「價格訊號日」已縮量的訊號，表現如何？（使用者看 6782 問：可用日 641 張、訊號日 327 張）
——回測線計算子代理。⭐ 描述、⛔ 不計 N、⛔ 不改規則；⛔ 不重算訊號（讀 resultsYLskip／resultsYFskip 的定版訊號表）；⛔ 不改任何既有 .py／結果夾；⛔ 不 commit。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLliq2 [--procs 3]
    查核：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLliq2_check

═══ 讀法（寫於 2026-10-19（台北），在算任何本件數字之前；⚠ 本線看過：resultsYLskip／resultsYFskip 各類淨報酬、營量／營飆 v1 各段年化與回落；
    ⛔ 沒看過任何「依訊號日均量分組」的數字）═══
 Q1 訊號母體與報酬 ＝ 定版訊號表原樣（不重算）：
      營量 ＝ backtest/resultsYLskip/signals.csv.gz（SIG[無閘]、H60、淨 ＝ 毛 − 0.585%、T+1 開盤買、停止交易強制出場同引擎）
      營飆 ＝ backtest/resultsYFskip/signals.csv.gz（SIG[閘]、H120、同上）
      超額 ＝ 表內「超額」＝ 淨 − 0050 同期淨（0050 扣 0.385%）；段 ＝ 營飆 v1 原報告段界（探索、確認＝主世界；早年＝早年世界）
    世界 ＝ researchYL_integrate.main_world／early_world（只用來取日曆、資料目錄與 AND 的 pos 欄；並驗訊號表 (sid, entry_pos, xpos) ＝ 世界 SIG 原樣）
 Q2 訊號日 ＝ AND 表 pos 欄（價格訊號那根的日曆位置；進場 ＝ entry_pos）；另報 pos ≠ entry_pos − 1 的筆數
    訊號日 20 日均量 ＝ patterns.Frame(D.load_stock(...).df).vol_ma20[pos]（＝ 500 張閘同一行程式：volume.rolling(20, min_periods=20).mean().shift(1)，
      即 T−20～T−1、不含訊號日；期間有未成交日 ⇒ NaN ⇒ 另列「無法算」）；另附 full20[pos]、gate[pos]
    訊號日 20 日均額 ＝ patterns.Frame 金額模式同式：amount.fillna(0).rolling(20, min_periods=20).mean().shift(1)（T−20～T−1、未成交記 0）
    分組：均量 ≥ 500 張／300～500 張／＜ 300 張／無法算；均額 ＞ 1 億／3,000 萬～1 億／＜ 3,000 萬（左閉右開：[3e7, 1e8)）
 Q3 每組（每段 × 每規則）：筆數、占段內比、淨中位／平均、勝率（淨 ＞ 0）、超額中位／平均、超額勝率、未滿／強制出場占比
    組間差 ＝ 各組 − 參考組（均量 ≥ 500 張；均額 ＞ 1 億），指標 淨平均、淨中位、勝率、超額平均、超額中位；
    95% CI ＝ 月分群 bootstrap（以訊號日所在月為群，2,000 次，rng 20261019，2.5／97.5 百分位）
 Q4 實務量：每份 2 萬元 ÷ 進場日（訊號日隔天 ＝ entry_pos）成交金額（D.load_stock 的 amount，名目元、未還原）；每段每規則報 中位、p90、p99、最大、
    ＞1%、＞5% 的筆數；進場日 amount 缺或 0 ⇒ 另計。⚠ 2 萬是今天的金額套在歷史名目成交額上（早年成交額較小，比例偏高）
 Q5 閘：K1 兩表 (sid, entry_pos, xpos) ＝ 世界 SIG（dropna、xpos ≥ 0）逐列相同；K2 每筆都有 pos；K3 分組筆數加總 ＝ 段內筆數
 必附：「描述，不當改規則依據」；早年附「早年含減資假飆股約 0.3%（reduce_v2；剩 22 筆未解釋）」與 NOTE3
輸出 backtest/resultsYLliq2/：signals.csv.gz（每筆訊號＋均量／均額／占比）、cells.csv、diffs.csv、practical.csv、cal.npz、summary.json、run.log
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D                              # noqa: E402
from backtest import patterns as P                          # noqa: E402
from backtest import researchYL_integrate as IG             # noqa: E402

TIME = "2026-10-19（台北）"
OUT = "backtest/resultsYLliq2"
NB = 2000
BOOT_SEED = 20261019
LOT = 1000.0
UNIT = 20_000.0
WORD = "描述，不當改規則依據"
NOTE_EARLY = ["早年含減資假飆股約 0.3%（reduce_v2；剩 22 筆未解釋）", IG.NOTE3]
SEGS = {"主": ("探索", "確認"), "早年": ("早年",)}
SRC = {"營量": ("backtest/resultsYLskip/signals.csv.gz", False, 60), "營飆": ("backtest/resultsYFskip/signals.csv.gz", True, 120)}
VG = ["≥500張", "300～500張", "<300張", "無法算"]
AG = [">1億", "3000萬～1億", "<3000萬"]
MET = [("淨", "mean"), ("淨", "med"), ("勝", "mean"), ("超額", "mean"), ("超額", "med")]


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


def log_to(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    f = open(path, "a", encoding="utf-8")

    def log(m):
        m = f"[{now_tpe()}] {m}"; print(m, flush=True); f.write(m + "\n"); f.flush()
    return log


def vgroup(v):
    if not np.isfinite(v):
        return "無法算"
    return "≥500張" if v >= 500_000 else ("300～500張" if v >= 300_000 else "<300張")


def agroup(a):
    return ">1億" if a > 1e8 else ("3000萬～1億" if a >= 3e7 else "<3000萬")


def liq_feats(W, sigs, log):
    """sigs：DataFrame(sid, pos, entry_pos) ⇒ 加 均量、均額、full20、gate、進場日成交金額（當下 D.DATA ＝ 該世界資料）。"""
    cal = W["cal"]; out = {}
    for s_ in sorted(sigs["sid"].unique()):
        st = D.load_stock(s_, W["uni"].get(s_, "twse"), cal)
        if st is None:
            out[s_] = None; continue
        f = P.Frame(st.df, st.event_dates)
        amt = st.df["amount"]
        am20 = amt.fillna(0.0).rolling(20, min_periods=20).mean().shift(1).to_numpy(float)
        out[s_] = (f.vol_ma20, am20, f.full20, f.gate, amt.to_numpy(float), st.df["volume"].to_numpy(float))
    rows = []
    for s_, p_, e_ in zip(sigs["sid"], sigs["pos"], sigs["entry_pos"]):
        z = out[s_]
        if z is None:
            rows.append((np.nan,) * 6); continue
        vm, am, f20, g, amt, vol = z
        rows.append((vm[p_], am[p_], float(f20[p_]), float(g[p_]), amt[e_] if e_ < len(amt) else np.nan, vol[e_] if e_ < len(vol) else np.nan))
    R_ = pd.DataFrame(rows, columns=["訊號日均量", "訊號日均額", "full20", "gate訊號日", "進場日成交金額", "進場日成交量"], index=sigs.index)
    log(f"[{W['name']} 均量] {len(sigs)} 筆｜{len(out)} 檔｜D.DATA ＝ {D.DATA}")
    return R_


def wmed(y, w):
    m = np.isfinite(y) & (w > 0)
    if not m.any():
        return np.nan
    o = np.argsort(y[m], kind="stable"); ys = y[m][o]; cw = np.cumsum(w[m][o])
    return float(ys[np.searchsorted(cw, 0.5 * cw[-1])])


def stat(y, w, how):
    m = np.isfinite(y) & (w > 0)
    if not m.any():
        return np.nan
    return float(np.sum(y[m] * w[m]) / np.sum(w[m])) if how == "mean" else wmed(y, w)


def boot(Ts, gcol, groups, ref, rng):
    """月分群 bootstrap：各組 − 參考組。回 list[dict]。"""
    um, mo = np.unique(Ts["月"].to_numpy(), return_inverse=True); M = len(um)
    draws = np.array([np.bincount(rng.integers(0, M, M), minlength=M) for _ in range(NB)], float)
    G = Ts[gcol].to_numpy(); out = []
    for col, how in MET:
        y = Ts[col].to_numpy(float)
        ind = {g: (G == g).astype(float) for g in groups}
        pt = {g: stat(y, ind[g], how) for g in groups}
        bs = {g: np.full(NB, np.nan) for g in groups}
        for g in groups:
            if ind[g].sum() == 0:
                continue
            if how == "mean":
                m = np.isfinite(y) & (ind[g] > 0)
                Sg = np.bincount(mo[m], weights=y[m], minlength=M); Cg = np.bincount(mo[m], minlength=M).astype(float)
                num, den = draws @ Sg, draws @ Cg
                bs[g] = np.where(den > 0, num / np.where(den > 0, den, 1), np.nan)
            else:
                m = np.isfinite(y) & (ind[g] > 0)
                o = np.argsort(y[m], kind="stable"); ys = y[m][o]; ms = mo[m][o]
                for b in range(NB):
                    cw = np.cumsum(draws[b][ms])
                    bs[g][b] = ys[np.searchsorted(cw, 0.5 * cw[-1])] if cw[-1] > 0 else np.nan
        for g in groups:
            if g == ref:
                continue
            dd = bs[g] - bs[ref]; dd = dd[np.isfinite(dd)]
            lo, hi = (float(np.percentile(dd, 2.5)), float(np.percentile(dd, 97.5))) if len(dd) >= 100 else (np.nan, np.nan)
            out.append({"比較": f"{g} − {ref}", "指標": f"{col}_{'平均' if how == 'mean' else '中位'}", "差": pt[g] - pt[ref], "CI下": lo, "CI上": hi,
                        "月群數": M, "有效抽數": len(dd), "組筆數": int(ind[g].sum()), "參考筆數": int(ind[ref].sum())})
    return out


def cells(Ts, gcol, groups):
    n = len(Ts); rows = []
    for g in groups:
        x = Ts[Ts[gcol] == g]
        net, exc = x["淨"].to_numpy(float), x["超額"].to_numpy(float)
        rows.append({"組": g, "筆數": len(x), "占比": len(x) / n if n else np.nan,
                     "淨_中位": float(np.median(net)) if len(x) else np.nan, "淨_平均": float(net.mean()) if len(x) else np.nan,
                     "勝率": float((net > 0).mean()) if len(x) else np.nan,
                     "超額_中位": float(np.median(exc)) if len(x) else np.nan, "超額_平均": float(exc.mean()) if len(x) else np.nan,
                     "超額勝率": float((exc > 0).mean()) if len(x) else np.nan,
                     "未滿占": float(x["未滿"].mean()) if len(x) else np.nan, "強制出場占": float(x["強制出場"].mean()) if len(x) else np.nan,
                     "均量中位(張)": float(np.nanmedian(x["訊號日均量"])) / LOT if x["訊號日均量"].notna().any() else np.nan,
                     "均額中位(億)": float(np.median(x["訊號日均額"])) / 1e8 if len(x) else np.nan})
    return rows


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    log = log_to(os.path.join(OUT, "run.log"))
    log(f"[開始] 讀法寫死 {TIME}")
    TAB = {k: pd.read_csv(p, dtype={"sid": str}, float_precision="round_trip") for k, (p, _, _) in SRC.items()}
    gate = {}; LQ = {}; CAL = {}; DATA = {}
    for wn in ("主", "早年"):
        W, gm = (IG.main_world(log) if wn == "主" else IG.early_world(log, a.procs))
        W["name"] = wn; CAL[wn] = W["cal"]; DATA[wn] = D.DATA
        gate.update({f"世界 {k}": v for k, v in gm.items()})
        for rn, (_, G, H) in SRC.items():
            s = W["SIG"][G]
            d = s.dropna(subset=["sid", "entry_pos", f"xpos_H{H}", f"g_H{H}"])
            d = d[d[f"xpos_H{H}"] >= 0].reset_index(drop=True)
            t = TAB[rn][TAB[rn]["世界"] == wn].reset_index(drop=True)
            same = (len(d) == len(t) and (d["sid"].astype(str).to_numpy() == t["sid"].to_numpy()).all()
                    and (d["entry_pos"].to_numpy(int) == t["entry_pos"].to_numpy(int)).all()
                    and (d[f"xpos_H{H}"].to_numpy(int) == t["xpos"].to_numpy(int)).all())
            gate[f"K1 {wn} {rn} 訊號表 ≠ 世界 SIG"] = int(not same)
            gate[f"K2 {wn} {rn} 缺 pos"] = int(d["pos"].isna().sum())
            t["pos"] = d["pos"].to_numpy(int)
            gate[f"附 {wn} {rn} pos ≠ entry_pos−1（筆）"] = int((t["pos"] != t["entry_pos"] - 1).sum())
            t = pd.concat([t, liq_feats(W, t[["sid", "pos", "entry_pos"]], log)], axis=1)
            t["規則"] = rn; t["日期"] = [W["cal"][p_].strftime("%Y-%m-%d") for p_ in t["pos"]]
            LQ[(wn, rn)] = t
    log(f"[閘] {gate}")
    hard = [k for k, v in gate.items() if k.startswith(("K1", "K2", "世界")) and v != 0]
    if hard:
        raise SystemExit(f"⛔ 閘不過 {hard}")
    ALL = []
    for (wn, rn), t in LQ.items():
        t = t.copy()
        t["未滿"] = t[f"未滿{SRC[rn][2]}"]
        t["勝"] = (t["淨"] > 0).astype(float)
        t["均量組"] = [vgroup(v) for v in t["訊號日均量"]]
        t["均額組"] = [agroup(v) for v in t["訊號日均額"]]
        t["2萬占進場日成交額"] = np.where(t["進場日成交金額"] > 0, UNIT / t["進場日成交金額"], np.nan)
        ALL.append(t)
    ALL = pd.concat(ALL, ignore_index=True)
    keep = ["世界", "規則", "段", "sid", "pos", "entry_pos", "xpos", "日期", "月", "淨", "0050淨", "超額", "勝", "未滿", "強制出場", "訊號日均量", "訊號日均額",
            "full20", "gate訊號日", "進場日成交金額", "進場日成交量", "均量組", "均額組", "2萬占進場日成交額"]
    ALL[keep].to_csv(os.path.join(OUT, "signals.csv.gz"), index=False, float_format="%.12g")
    np.savez_compressed(os.path.join(OUT, "cal.npz"), **{wn: np.array([d.strftime("%Y-%m-%d") for d in CAL[wn]]) for wn in CAL})
    rng = np.random.default_rng(BOOT_SEED)
    C, DF, PR = [], [], []
    for wn in ("主", "早年"):
        for sg in SEGS[wn]:
            for rn in SRC:
                Ts = ALL[(ALL["世界"] == wn) & (ALL["段"] == sg) & (ALL["規則"] == rn)].reset_index(drop=True)
                for kind, gcol, groups, ref in (("均量", "均量組", VG, "≥500張"), ("均額", "均額組", AG, ">1億")):
                    cr = cells(Ts, gcol, groups)
                    gate[f"K3 {wn} {sg} {rn} {kind} 分組加總 ≠ 段內"] = int(sum(r["筆數"] for r in cr) != len(Ts))
                    for r in cr:
                        C.append({"世界": wn, "段": sg, "規則": rn, "分組": kind, "段內筆數": len(Ts), **r})
                    for r in boot(Ts, gcol, groups, ref, rng):
                        DF.append({"世界": wn, "段": sg, "規則": rn, "分組": kind, **r})
                q = Ts["2萬占進場日成交額"].to_numpy(float); qf = q[np.isfinite(q)]
                PR.append({"世界": wn, "段": sg, "規則": rn, "筆數": len(Ts), "可算": len(qf), "進場日無成交額": int(len(Ts) - len(qf)),
                           "中位": float(np.median(qf)), "p90": float(np.percentile(qf, 90)), "p99": float(np.percentile(qf, 99)), "最大": float(qf.max()),
                           ">1%筆": int((qf > 0.01).sum()), ">5%筆": int((qf > 0.05).sum()),
                           "最大那筆": Ts.loc[int(np.nanargmax(q)), "sid"] + " " + Ts.loc[int(np.nanargmax(q)), "日期"],
                           "進場日成交額中位(萬)": float(np.nanmedian(Ts["進場日成交金額"])) / 1e4,
                           "進場日成交額最小(萬)": float(np.nanmin(Ts["進場日成交金額"].where(Ts["進場日成交金額"] > 0))) / 1e4})
    C, DF, PR = pd.DataFrame(C), pd.DataFrame(DF), pd.DataFrame(PR)
    C.to_csv(os.path.join(OUT, "cells.csv"), index=False, encoding="utf-8-sig", float_format="%.10g")
    DF.to_csv(os.path.join(OUT, "diffs.csv"), index=False, encoding="utf-8-sig", float_format="%.10g")
    PR.to_csv(os.path.join(OUT, "practical.csv"), index=False, encoding="utf-8-sig", float_format="%.10g")
    # 6782 型：可用日過閘但訊號日 ＜ 300 張 的占比彙總（全部訊號）
    S = {"讀法寫死": TIME, "性質": "描述、不計 N、不改規則、不重算訊號", "必附": WORD, "早年註": NOTE_EARLY, "資料目錄": DATA, "閘": gate,
         "訊號日 gate 未過占比": {f"{wn}·{rn}": float((1 - t["gate訊號日"]).mean()) for (wn, rn), t in LQ.items()},
         "表": C.to_dict("records"), "差": DF.to_dict("records"), "實務量": PR.to_dict("records"), "完成（台北）": now_tpe()}
    if any(v != 0 for k, v in gate.items() if k.startswith("K3")):
        json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
        raise SystemExit("⛔ K3 不過")
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    pd.set_option("display.width", 260); pd.set_option("display.max_columns", 40)
    log("\n" + C[["世界", "段", "規則", "分組", "組", "筆數", "占比", "淨_中位", "淨_平均", "勝率", "超額_中位", "超額_平均", "未滿占", "均量中位(張)", "均額中位(億)"]].to_string(index=False))
    log("\n" + DF[DF["指標"].isin(["淨_平均", "淨_中位", "超額_平均"])].to_string(index=False))
    log("\n" + PR.to_string(index=False))
    log(f"[完] {now_tpe()}")


if __name__ == "__main__":
    main()
