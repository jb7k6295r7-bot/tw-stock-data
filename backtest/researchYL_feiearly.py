# -*- coding: utf-8 -*-
"""營飆 v1 早年重判（裁定 seq285 §二；只跑一次、照原規則、⛔ 不調任何參數；不計 N）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYL_feiearly [--procs 3] | --check | --page

═══ 判讀（寫死於 2026-10-04 01:58（台北），在算任何本件數字之前；⚠ 本線看過：researchYL_integrate 36 格表裡這一格的早年中位 +15.2%／−56.1%（合格））═══
 J1 早年窗 2005-02-01～2014-12-31；上市＋上櫃版面 ~/earlydata/eotc_f65bb03e11（researchYL_integrate.early_world ＝ researchEarlyOTC_rerun.make_world("O", "W_B")）
    ⚠ 引用必附（裁定 seq283）：上櫃 2007-07～12 除權息未還原；上櫃減資 2007～2012 為偵測、非官方；2005-01～2007-06 只有上市
 J2 營飆 v1 規則（原規則一字不改）：AND 訊號（T1＋R8）、進場日前一日 0050 收盤 ＞ 200 日均才進、10 槽、抽籤 default_rng(1000＋r)、H120 收盤出、停止交易強制出場開
    ＝ researchYL_integrate 的格 H120·S10·閘·抽籤，直接呼叫同一支 eng／stats；r ＝ 0～199，報中位、p10～p90
    閘：200 顆的 eq_sha 與早年年化、回落 repr ＝ resultsYL_integrate/seeds.csv.gz（世界＝早年、格＝H120·S10·閘·抽籤）逐位元
 J3 判準：年化中位 ＞ 0050 同窗年化 且 年化中位 ÷ |回落中位| ≥ 0050 同窗比值 ⇒ 合格；只過第一條 ⇒ 另列；否則不合格
 J4 IFRS 敏感度（同 1004-0100 ＝ researchYL_integrate I8）：訊號的營收期別 ＝ 訊號日當下最新一列營收面板（sig_otc/panel_rev，signal_pos ≤ 訊號位置）；
    期別 ∈ [2013-01, 2014-12] ⇒ 剔除；剔除後同引擎 200 顆 ⇒ 標籤
 J5 判讀（⛔ 看數字後不改）：
    剔除 IFRS 訊號後標籤翻轉（合格 ↔ 非合格；另列與不合格之間的變動不算翻轉，兩者都不是「合格」）⇒「不可判定」
    否則：不剔除版合格 ⇒ 營飆 v1 改「暫定」；不合格（含另列）⇒ 維持「實驗」
    網頁主引不剔除版；敏感度只寫一句結論，⛔ 不並列剔除前後兩個年化數字
 J6 照實報：舊判定窗 2012-06～2014-12（只上市）的 +16.1%／−18.1% 不再引用（已改「不可判定（IFRS 換軌）」）
 J7 查核（--check）：① 閘逐日（0050 200 日均）重算全部窗內訊號；② IFRS 剔除逐列重找期別（全部窗內訊號）；③ 中位、p10～p90 與標籤從逐種子檔重算 ⇒ 0 不同才算過
輸出 backtest/resultsYL_feiearly/
"""
from __future__ import annotations

import argparse
import html
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchYL_integrate as IG
from backtest import rerun17 as RR

TIME = "2026-10-04 01:58（台北）"
OUT = "backtest/resultsYL_feiearly"
KEYF = IG.YF                                   # H120·S10·閘·抽籤
NSEED = 200
PANEL = os.path.expanduser(f"~/earlydata/eotc_{IG.MSHA[:10]}/sig_otc/panel_rev.csv.gz")
_W: dict = {}


def job(args):
    tag, r = args
    W = _W["W"]
    o, au = IG.eng(W, KEYF, r, sig=_W["SIG"][tag])
    row, eq = IG.stats(W, o, au, 10)
    row.update({"版": tag, "r": r, "eq_sha": IG.sha(eq)})
    return row


def periods(sig):
    pan = pd.read_csv(PANEL, dtype={"stock_id": str}, usecols=["stock_id", "period", "signal_pos"]).sort_values(["stock_id", "signal_pos"])
    PP = {s: (g["signal_pos"].to_numpy(int), g["period"].to_numpy()) for s, g in pan.groupby("stock_id")}
    out = []
    for s, p in zip(sig["sid"], sig["pos"].astype(int)):
        if s not in PP:
            out.append(None); continue
        sp, pr = PP[s]; j = int(np.searchsorted(sp, p, side="right")) - 1
        out.append(pr[j] if j >= 0 else None)
    return out


def run(a, log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    W, gate = IG.early_world(log, a.procs)
    sig = W["SIG"][True]
    pp = periods(sig)
    cross = np.array([p is not None and "2013-01" <= p <= "2014-12" for p in pp])
    _W.update(W=W, SIG={"原": sig, "剔IFRS": sig[~cross]})
    pd.DataFrame({"sid": sig["sid"].to_numpy(), "pos": sig["pos"].to_numpy(), "entry_pos": sig["entry_pos"].to_numpy(), "期別": pp, "剔除": cross}).to_csv(
        os.path.join(OUT, "signals.csv.gz"), index=False)
    with Pool(a.procs) as pool:
        rows = pool.map(job, [(t, r) for t in ("原", "剔IFRS") for r in range(NSEED)], chunksize=4)
    SE = pd.DataFrame(rows); SE.to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False, float_format="%.17g")
    ref = pd.read_csv("backtest/resultsYL_integrate/seeds.csv.gz", dtype={"eq_sha": str}, float_precision="round_trip")
    ref = ref[(ref["世界"] == "早年") & (ref["格"] == KEYF)].sort_values("r").reset_index(drop=True)
    m = SE[SE["版"] == "原"].sort_values("r").reset_index(drop=True)
    gate["本件原版 ＝ integrate 早年 H120·S10·閘·抽籤（eq_sha／年化／回落 repr 不同顆數）"] = int(sum(
        m.loc[i, "eq_sha"] != ref.loc[i, "eq_sha"] or repr(float(m.loc[i, "早年_年化"])) != repr(float(ref.loc[i, "早年_年化"]))
        or repr(float(m.loc[i, "早年_回落"])) != repr(float(ref.loc[i, "早年_回落"])) for i in range(min(len(m), len(ref)))))
    b = W["b50"]["早年"]
    res = {}
    for t, g in SE.groupby("版"):
        c_, m_ = float(g["早年_年化"].median()), float(g["早年_回落"].median())
        res[t] = {"年化中位": c_, "回落中位": m_, "年化p10": float(g["早年_年化"].quantile(.1)), "年化p90": float(g["早年_年化"].quantile(.9)),
                  "回落p10": float(g["早年_回落"].quantile(.1)), "回落p90": float(g["早年_回落"].quantile(.9)), "比值": c_ / abs(m_), "標籤": IG.label(c_, m_, b),
                  "持股中位": float(g["早年_持股"].median()), "現金中位": float(g["早年_現金"].median()), "買進每年中位": float(g["早年_買進每年"].median()),
                  "合格顆數比例": float(np.mean([IG.label(x, y, b) == "合格" for x, y in zip(g["早年_年化"], g["早年_回落"])]))}
    l0, l1 = res["原"]["標籤"], res["剔IFRS"]["標籤"]
    flip = (l0 == "合格") != (l1 == "合格")
    verdict = "不可判定" if flip else ("暫定" if l0 == "合格" else "實驗（維持）")
    S = {"讀法寫死": TIME, "早年標註": IG.NOTE3, "窗": [str(W["cal"][W["w0"]].date()), str(W["cal"][W["w1"]].date())], "0050": b, "閘": gate,
         "訊號": {"窗內（閘後）": int(len(sig)), "IFRS 剔除": int(cross.sum())}, "結果": res, "IFRS 標籤翻轉": bool(flip), "判定": verdict,
         "舊窗": "2012-06～2014-12（只上市）的 +16.1%／−18.1% 不再引用（已改「不可判定（IFRS 換軌）」）", "耗時秒": round(time.time() - T0)}
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] {json.dumps(S, ensure_ascii=False, default=str)}")
    if any(v for v in gate.values()):
        raise SystemExit(f"⛔ 閘不過 {gate}")


def check(a, log):
    from backtest import data as D
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    SG = pd.read_csv(os.path.join(OUT, "signals.csv.gz"), dtype={"sid": str})
    errs = []; info = {}
    D.DATA = os.path.expanduser(f"~/earlydata/eotc_{IG.MSHA[:10]}/otc/data")
    cal = D.load_calendar(); bench = RR.load_bench(cal)
    nd = 0
    for e in SG["entry_pos"].astype(int):
        t = e - 1
        ok = t >= 199 and bench[t] > sum(bench[t - 199:t + 1]) / 200.0
        if not ok:
            nd += 1
    info["① 閘逐日（窗內訊號都應在 200 日均之上；不成立列數）"] = nd
    if nd:
        errs.append(f"閘 {nd} 列不成立")
    pan = pd.read_csv(PANEL, dtype={"stock_id": str}, usecols=["stock_id", "period", "signal_pos"])
    by = {s: g for s, g in pan.groupby("stock_id")}
    nd = 0
    for r in SG.itertuples():
        g = by.get(r.sid)
        p = None
        if g is not None:
            best = -1
            for sp, pr in zip(g["signal_pos"], g["period"]):
                if sp <= r.pos and sp > best:
                    best, p = sp, pr
        x = p is not None and "2013-01" <= p <= "2014-12"
        if x != bool(r.剔除):
            nd += 1
    info["② IFRS 剔除逐列（不同列數）"] = nd
    if nd:
        errs.append(f"IFRS {nd}")
    SE = pd.read_csv(os.path.join(OUT, "seeds.csv.gz"), float_precision="round_trip")
    b = S["0050"]
    for t, g in SE.groupby("版"):
        xs = sorted(g["早年_年化"]); ys = sorted(g["早年_回落"])
        med = lambda v: (v[len(v) // 2 - 1] + v[len(v) // 2]) / 2
        c_, m_ = med(xs), med(ys)
        lab = "合格" if (c_ > b["cagr"] and c_ / abs(m_) >= b["cagr"] / abs(b["mdd"])) else ("另列" if c_ > b["cagr"] else "不合格")
        rr = S["結果"][t]
        if abs(c_ - rr["年化中位"]) > 1e-12 or abs(m_ - rr["回落中位"]) > 1e-12 or lab != rr["標籤"]:
            errs.append(f"{t} 中位／標籤 {c_} {m_} {lab} / {rr['年化中位']} {rr['回落中位']} {rr['標籤']}")
    info["③ 中位與標籤重算"] = "見不同的筆" if errs else "一致"
    out = {"讀法寫死": TIME, "比對": info, "不同的筆": errs, "主程式閘": S["閘"], "通過": not errs}
    json.dump(out, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[查核] {out}")


def page(log):
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    CKp = os.path.join(OUT, "check.json"); CK = json.load(open(CKp, encoding="utf-8")) if os.path.exists(CKp) else None
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0]
    CSS += ("\nsmall{color:#666}.warn{border-left:4px solid #d64045;padding:6px 10px;background:#fff4f4}"
            ".ok{border-left:4px solid #2b6cb0;padding:8px 12px;background:#eef4fb}.big{font-size:1.05rem}li{margin:.35em 0}")
    P1 = lambda v: f"{v * 100:+.1f}%"
    e = html.escape
    r = S["結果"]["原"]; b = S["0050"]
    sens = ("剔除用到 2013～2014 年營收（IFRS 換軌期）的訊號後，標籤" + ("翻轉 ⇒ 判「不可判定」。" if S["IFRS 標籤翻轉"] else "沒有翻轉。"))
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>營飆早年重判</title>", f"<style>{CSS}</style></head><body><main>",
         "<h1>營飆 v1 早年重判（2005-02～2014-12，上市＋上櫃）</h1>",
         f"<p class='warn'>⚠ {e(S['早年標註'])}。只跑一次、照原規則，沒有調任何參數。</p>",
         f"<div class='ok big'><b>判定：{e(S['判定'])}</b><br>營飆 v1 早年 年化 {P1(r['年化中位'])}、最大回落 {P1(r['回落中位'])}（200 顆種子中位；"
         f"年化 p10～p90 {P1(r['年化p10'])}～{P1(r['年化p90'])}）；0050 同窗 {P1(b['cagr'])}／{P1(b['mdd'])} ⇒ <b>{r['標籤']}</b>"
         f"（年化÷回落 {r['比值']:.2f} vs 0050 {b['cagr'] / abs(b['mdd']):.2f}）。<br>敏感度：{e(sens)}</div>",
         f"<p class='lead'>判讀寫死 {e(S['讀法寫死'])}：合格 ⇒ 改「暫定」；不合格 ⇒ 維持「實驗」；剔除 IFRS 訊號後標籤翻轉 ⇒「不可判定」。"
         f"規則：前一日 0050 在 200 日線上才進新倉、10 檔、候選多時抽籤、抱 120 個交易日收盤賣。"
         f"窗內訊號 {S['訊號']['窗內（閘後）']} 筆；平均持股 {r['持股中位']:.1f} 檔、現金 {r['現金中位'] * 100:.0f}%；200 顆中合格的 {r['合格顆數比例'] * 100:.0f}%。"
         + (f"查核：{'通過' if CK['通過'] else '有不同'}；與營收趨勢整合那一格逐位元相同。" if CK else "") + "</p>",
         f"<p class='note'>{e(S['舊窗'])}。</p></main></body></html>"]
    open(os.path.join(OUT, "營飆早年重判.html"), "w", encoding="utf-8").write("\n".join(H))
    log("[網頁] 完成")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--check", action="store_true"); ap.add_argument("--page", action="store_true"); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); T0 = time.time()
    logf = open(os.path.join(OUT, "run_check.log" if a.check else ("run_page.log" if a.page else "run.log")), "a", encoding="utf-8")

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(str(m) + "\n"); logf.flush()
    if a.check:
        check(a, log)
    elif a.page:
        page(log)
    else:
        run(a, log)
        page(log)


if __name__ == "__main__":
    main()
