# -*- coding: utf-8 -*-
"""PREREG飆股回推 seq5 描述層（第一批）：網格計數、分段版、最大漲幅分佈、漲 50／100／200% 花幾天、高點後回落、結束時點、買不買得到。
由 researchSurge5 --stage desc 呼叫；讀法見 researchSurge5 開頭 S1～S17。"""
from __future__ import annotations

import html
import json
import os

import numpy as np
import pandas as pd

from backtest import researchSurge5 as S5

BUCK = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.0, 10.0, np.inf]
BUCKN = ["50～100%", "100～150%", "150～200%", "200～250%", "250～300%", "300～400%", "400～500%", "500～700%", "700～1000%", "≥1000%"]


def qs(x, ps=(10, 25, 50, 75, 90)):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return {f"p{p}": (float(np.percentile(x, p)) if len(x) else np.nan) for p in ps}


def defined_counts(hdef, rows):
    """rows（S×n bool）內 hdef 的直方圖 ⇒ 每個 H 的「定義域列數」＝ #(hdef ≥ H)。"""
    h = np.bincount(hdef[rows].astype(np.int64), minlength=252)
    ge = np.cumsum(h[::-1])[::-1]
    return {H: int(ge[H]) for H in S5.HS}


def fastest(E, uni, cal, log):
    """S18：(股, t, 格) ⇒ 最短花幾天（只算 H＝250、g＝50／100／200% 三格）。"""
    S5.D.DATA = S5.ST
    cells = {S5.cell_of(len(S5.HS) - 1, S5.GS.index(g)): g for g in (0.5, 1.0, 2.0)}
    k = np.flatnonzero(np.isin(E["cell"].astype(int), list(cells)))
    out = {}
    df = pd.DataFrame({"i": k, "s": E["s"][k].astype(int), "d": E["d"][k].astype(int), "P": E["P"][k].astype(int), "c": E["cell"][k].astype(int)})
    for s, g_ in df.groupby("s"):
        st = S5.D.load_stock(uni.loc[s, "stock_id"], uni.loc[s, "market"], cal)
        cff = pd.Series(st.df["close"].to_numpy(float)).ffill().to_numpy()
        for r in g_.itertuples():
            g = cells[r.c]; best = 10 ** 9
            for s0 in range(r.d, r.P):
                w = np.flatnonzero(cff[s0 + 1:r.P + 1] >= cff[s0] * (1 + g) * (1 - 1e-9))
                if len(w):
                    best = min(best, int(w[0]) + 1)
            out[(s, r.d, r.c)] = best if best < 10 ** 9 else np.nan
    log(f"[描述] 最短花幾天 {len(out)} 個事件")
    return out


def run(log):
    os.makedirs(S5.OUT, exist_ok=True)
    uni, cal, mon, segd, E = S5.load_all()
    n = len(cal); S = len(uni)
    bar = np.load(os.path.join(S5.WORK, "bar.npy")); hdef = np.load(os.path.join(S5.WORK, "hdef.npy"))
    locked = np.load(os.path.join(S5.WORK, "locked.npy")); disp = np.load(os.path.join(S5.WORK, "disp.npy"))
    Q = np.load(os.path.join(S5.WORK, "Q.npy"), mmap_mode="r"); qliq = np.asarray(Q[S5.FIX["amt_20"]])
    bj = json.load(open(os.path.join(S5.WORK, "build.json"), encoding="utf-8"))
    # t＋1 旗標
    nxt_bar = np.zeros_like(bar); nxt_bar[:, :-1] = bar[:, 1:]
    nxt_lock = np.zeros_like(bar); nxt_lock[:, :-1] = locked[:, 1:]
    nxt_disp = np.zeros_like(bar); nxt_disp[:, :-1] = disp[:, 1:]
    disp_first = int(cal.searchsorted(pd.Timestamp("2011-01-03")))
    excl = ~nxt_bar | nxt_lock | nxt_disp
    ec, es, ed = E["cell"].astype(int), E["s"].astype(int), E["d"].astype(int)
    SUM = {"分析開始": S5.START, "所用登錄": S5.SEQ, "g 網格": "照裁定 seq277（seq278 §2）", "執行者": "未看過 seq4 結果", "建表": {k: v for k, v in bj.items() if k != "特徵欄"}, "段": {}}
    G = []; BAND = []; BUY = []
    for sg, dm in segd.items():
        rows = bar & dm[None, :]
        dc = defined_counts(hdef, rows)
        dcx = defined_counts(hdef, rows & ~excl)
        ine = dm[ed]
        SUM["段"][sg] = {"股日": int(rows.sum()), "檔": int(rows.any(1).sum()), "月": f"{S5.SEG[sg][0]}～{S5.SEG[sg][1]}"}
        for c in range(S5.NC):
            hi, gi = divmod(c, len(S5.GS)); H, g = S5.HS[hi], S5.GS[gi]
            k = np.flatnonzero((ec == c) & ine)
            r = {"段": sg, "格": S5.cell_name(c), "H": H, "g": g, "事件": len(k), "定義域股日": dc[H], "比例": len(k) / dc[H] if dc[H] else np.nan}
            if len(k):
                M = E["M"][k]; dg = E["dg"][k]; pt = E["P"][k] - ed[k]
                r.update({"最大漲幅中位（H內）": float(np.median(M)), "最大漲幅中位（不設H，到回落30%前）": float(np.median(E["ps_g"][k])),
                          "P*未完比例": float(np.mean(E["ps_open"][k])),
                          **{f"花幾天_{p}": v for p, v in qs(dg).items()}, **{f"起漲到P_{p}": v for p, v in qs(pt).items()}})
                ob = E["obs"][k]
                for x in S5.DD:
                    hv = E[f"dd{int(x * 100)}"][k]; hit = hv > 0
                    r[f"回落{int(x * 100)}%_比例"] = float(hit.mean())
                    for w in (60, 120, 250):
                        den = hit & (hv <= w) | (ob >= w)
                        r[f"回落{int(x * 100)}%_{w}日內"] = float(((hv > 0) & (hv <= w))[den].mean()) if den.any() else np.nan
                    r[f"回落{int(x * 100)}%_P到觸及中位日"] = float(np.median(hv[hit])) if hit.any() else np.nan
                    r[f"回落{int(x * 100)}%_P到觸及p25日"] = float(np.percentile(hv[hit], 25)) if hit.any() else np.nan
                    r[f"回落{int(x * 100)}%_P到觸及p75日"] = float(np.percentile(hv[hit], 75)) if hit.any() else np.nan
                r["P後最大回落中位"] = float(np.nanmedian(E["maxdd"][k])); r["P後觀察天數中位"] = float(np.median(ob))
                yao = E["dd50"][k] > 0
                for nm, mk_ in (("妖股", yao), ("非妖股", ~yao)):
                    r[f"{nm}_事件"] = int(mk_.sum())
                    r[f"{nm}_起漲到P中位"] = float(np.median(pt[mk_])) if mk_.any() else np.nan
                    for x in (0.1, 0.2, 0.3):
                        hv = E[f"dd{int(x * 100)}"][k][mk_]
                        r[f"{nm}_P到回落{int(x * 100)}%中位"] = float(np.median(hv[hv > 0])) if (hv > 0).any() else np.nan
            G.append(r)
            # 分段版
            if gi + 1 < len(S5.GS):
                kb = k[E["M"][k] < S5.GS[gi + 1]] if len(k) else k
                BAND.append({"段": sg, "H": H, "區間": f"{int(g * 100)}～{int(S5.GS[gi + 1] * 100)}%", "事件": len(kb), "比例": len(kb) / dc[H] if dc[H] else np.nan})
            else:
                BAND.append({"段": sg, "H": H, "區間": "≥1000%", "事件": len(k), "比例": len(k) / dc[H] if dc[H] else np.nan})
            # 買不買得到
            if len(k):
                s_, d_ = es[k], ed[k]
                b = {"段": sg, "格": S5.cell_name(c), "H": H, "g": g, "事件": len(k),
                     "t+1無成交": float((~nxt_bar[s_, d_]).mean()), "t+1漲停鎖死": float(nxt_lock[s_, d_].mean()),
                     "t+1處置中": float(nxt_disp[s_, d_].mean()) if sg != "早年" else np.nan}
                ql = qliq[s_, d_]
                for q in range(1, 6):
                    b[f"20日均額Q{q}"] = float((ql == q).mean())
                keep = ~excl[s_, d_]
                b["剔除後事件"] = int(keep.sum()); b["剔除後比例"] = int(keep.sum()) / dcx[H] if dcx[H] else np.nan
                b["原比例"] = len(k) / dc[H] if dc[H] else np.nan
                BUY.append(b)
        log(f"[描述] {sg} 完成")
    G = pd.DataFrame(G); BAND = pd.DataFrame(BAND); BUY = pd.DataFrame(BUY)
    # S18 最短花幾天：H＝250、g ∈ {50,100,200}% 的事件，在 [t, P] 內任選起點 s，第一次收盤 ≥ s 收盤 ×（1＋g）的天數取最小
    FAST = fastest(E, uni, cal, log)
    for sg, dm in segd.items():
        for g in (0.5, 1.0, 2.0):
            c = S5.cell_of(len(S5.HS) - 1, S5.GS.index(g))
            k = np.flatnonzero((ec == c) & dm[ed])
            v = np.array([FAST.get((int(es[i]), int(ed[i]), c), np.nan) for i in k], float)
            ix = G.index[(G["段"] == sg) & (G["H"] == 250) & np.isclose(G["g"], g)][0]
            for p, val in qs(v).items():
                G.loc[ix, f"最短花幾天_{p}"] = val
    G.to_csv(os.path.join(S5.OUT, "grid.csv"), index=False, float_format="%.6g")
    BAND.to_csv(os.path.join(S5.OUT, "grid_band.csv"), index=False, float_format="%.6g")
    BUY.to_csv(os.path.join(S5.OUT, "buyable.csv"), index=False, float_format="%.6g")
    # 最大漲幅分佈（不分格；(股, t) 聯集）
    MG = []
    for sg, dm in segd.items():
        k = np.flatnonzero(dm[ed])
        key = es[k].astype(np.int64) * 100000 + ed[k]
        df = pd.DataFrame({"key": key, "M250": E["M250"][k], "ps": E["ps_g"][k], "open": E["ps_open"][k]}).groupby("key").agg(M250=("M250", "first"), ps=("ps", "max"), open=("open", "max"))
        for nm, col in (("250日內最大漲幅", "M250"), ("不設H最大漲幅（到回落30%前）", "ps")):
            x = df[col].to_numpy(float); x = x[np.isfinite(x)]
            h = np.histogram(x, bins=BUCK)[0]
            MG.append({"段": sg, "口徑": nm, "起漲事件（聯集）": int(len(x)), **{b: int(v) for b, v in zip(BUCKN, h)},
                       **{f"占比_{b}": float(v / len(x)) if len(x) else np.nan for b, v in zip(BUCKN, h)}, **qs(x), "未完比例": float(df["open"].mean()) if col == "ps" else np.nan})
    MG = pd.DataFrame(MG); MG.to_csv(os.path.join(S5.OUT, "maxgain.csv"), index=False, float_format="%.6g")
    SUM["最大漲幅分佈"] = MG[["段", "口徑", "起漲事件（聯集）", "p50", "p90"]].to_dict("records")
    json.dump(SUM, open(os.path.join(S5.OUT, "summary_desc.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    report(SUM, G, BAND, BUY, MG)
    page(SUM, G, BAND, BUY, MG)
    log(f"[描述] 輸出 grid／grid_band／buyable／maxgain")


P_ = lambda x, d=1: "—" if x is None or not np.isfinite(x) else f"{x * 100:.{d}f}%"
N_ = lambda x: "—" if x is None or not np.isfinite(x) else f"{x:.0f}"
PP_ = lambda x: "—" if x is None or not np.isfinite(x) else (f"{x * 1e4:.2f}‱" if x < 0.001 else f"{x * 100:.2f}%")


def pick(G, sg, H, g):
    r = G[(G["段"] == sg) & (G["H"] == H) & (np.isclose(G["g"], g))]
    return r.iloc[0] if len(r) else None


def report(SUM, G, BAND, BUY, MG):
    NL = "\n"; L = ["# PREREG飆股回推 seq5 第一批：描述層（網格、最大漲幅、花幾天、高點後回落、買不買得到）", "",
                    f"> 分析開始 {SUM['分析開始']}｜所用登錄 {SUM['所用登錄']}｜g 網格照裁定 seq277｜執行者未看過 seq4 結果｜資料 main {S5.MAIN_SHA[:10]}＋早年 {S5.EARLY_SHA[:10]}（接合）｜讀法 S1～S17 見 researchSurge5.py 開頭", "",
                    f"母體：{json.dumps(SUM['段'], ensure_ascii=False)}", "",
                    "## 一、網格：之後 H 個交易日內收盤漲 ≥ g 的起漲事件，占全體股-日比例（每格事件數見 grid.csv）", ""]
    for sg in S5.SEG:
        L.append(f"### {sg}"); L.append("| H＼g | " + " | ".join(f"{int(g * 100)}%" for g in S5.GS) + " |"); L.append("|---" * (len(S5.GS) + 1) + "|")
        for H in S5.HS:
            row = []
            for g in S5.GS:
                r = pick(G, sg, H, g)
                row.append("—" if r is None else f"{PP_(r['比例'])}（{int(r['事件'])}）")
            L.append(f"| {H} | " + " | ".join(row) + " |")
        L.append("")
    L.append("## 二、每個起漲事件的最大漲幅（不分格；(股, t) 聯集）"); L.append("")
    L.append("| 段 | 口徑 | 事件 | " + " | ".join(BUCKN) + " | 中位 | p90 |"); L.append("|---" * (len(BUCKN) + 5) + "|")
    for r in MG.to_dict("records"):
        L.append(f"| {r['段']} | {r['口徑']} | {r['起漲事件（聯集）']} | " + " | ".join(P_(r[f'占比_{b}']) for b in BUCKN) + f" | {P_(r['p50'], 0)} | {P_(r['p90'], 0)} |")
    L.append(""); L.append("## 三、漲 50％／100％／200％ 實際花了幾天（H＝250 那一格；交易日）"); L.append("")
    L.append("⚠ 「從起漲日算」的起漲日是「250 日內會漲到的第一天」，天數天生貼近 250（構造使然），只當參考；主讀「最短花幾天」（S18：同一段漲勢內任選起點、最快漲到 g 的天數）。"); L.append("")
    L.append("| 段 | g | 事件 | 最短花幾天 p10／p25／中位／p75／p90 | 從起漲日算 中位（參考） |"); L.append("|---|---|---|---|---|")
    for sg in S5.SEG:
        for g in (0.5, 1.0, 2.0):
            r = pick(G, sg, 250, g)
            if r is not None and r["事件"] > 0:
                L.append(f"| {sg} | {int(g * 100)}% | {int(r['事件'])} | " + "／".join(N_(r[f'最短花幾天_p{p}']) for p in (10, 25, 50, 75, 90)) +
                         f" | {N_(r['花幾天_p50'])} |")
    L.append(""); L.append("## 四、高點 P 之後：回落 10／20／30／50／70% 的比例與花的天數（代表格 H＝60、120、250 × g＝100%、200%、500%）"); L.append("")
    L.append("| 段 | 格 | 事件 | 起漲到P中位 | " + " | ".join(f"回落{x}%（比例／中位日）" for x in (10, 20, 30, 50, 70)) + " | P後最大回落中位 |"); L.append("|---" * 10 + "|")
    for sg in S5.SEG:
        for H in (60, 120, 250):
            for g in (1.0, 2.0, 5.0):
                r = pick(G, sg, H, g)
                if r is None or r["事件"] == 0:
                    continue
                L.append(f"| {sg} | {r['格']} | {int(r['事件'])} | {N_(r['起漲到P_p50'])} | " + " | ".join(f"{P_(r[f'回落{x}%_比例'], 0)}／{N_(r[f'回落{x}%_P到觸及中位日'])}" for x in (10, 20, 30, 50, 70)) + f" | {P_(r['P後最大回落中位'], 0)} |")
    L.append(""); L.append("## 五、買不買得到（代表格；全部格見 buyable.csv）"); L.append("")
    L.append("| 段 | 格 | 事件 | t+1無成交 | t+1漲停鎖死 | t+1處置中 | 20日均額最低五分之一 | 原比例 | 剔除三者後比例 |"); L.append("|---" * 9 + "|")
    for sg in S5.SEG:
        for H in (20, 60, 250):
            for g in (0.5, 1.0, 3.0):
                r = BUY[(BUY["段"] == sg) & (BUY["H"] == H) & np.isclose(BUY["g"], g)]
                if not len(r):
                    continue
                r = r.iloc[0]
                L.append(f"| {sg} | {r['格']} | {int(r['事件'])} | {P_(r['t+1無成交'])} | {P_(r['t+1漲停鎖死'])} | {P_(r['t+1處置中'])} | {P_(r['20日均額Q1'])} | {PP_(r['原比例'])} | {PP_(r['剔除後比例'])} |")
    L.append(""); L.append("檔案：grid.csv（250 格 × 3 段全部欄）｜grid_band.csv（分段版）｜maxgain.csv｜buyable.csv｜summary_desc.json")
    open(os.path.join(S5.OUT, "REPORT_desc.md"), "w", encoding="utf-8").write(NL.join(L) + NL)


def page(SUM, G, BAND, BUY, MG):
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0]
    CSS += "\ntd.l,th.l{text-align:left}small{color:#666}.hm td{font-size:12px;padding:3px 4px}.tabs button{margin:2px;padding:6px 10px;border:1px solid #ccc;border-radius:6px;background:#fff}.tabs button.on{background:#333;color:#fff}"
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>飆股回推 第一批</title>", f"<style>{CSS}</style></head><body><main>", "<h1>飆股回推（seq5）第一批：飆股有多少、漲多少、多久、之後怎麼跌</h1>",
         f"<p class='lead'>分析開始 {SUM['分析開始']}，照登錄 {SUM['所用登錄']}；漲幅網格照裁定 seq277。執行者沒看過上一版結果。這一批只描述，還沒有看特徵。</p>",
         "<p class='note'>飆股 ＝ 某天收盤後，之後 H 個交易日內收盤曾經比那天高 g 以上。母體是全部上市櫃普通股（含已下市、注意、處置、停牌前後），2015 以前只有上市。</p>"]
    H.append("<h2>一、每一萬個股-日裡，有幾個是飆股起漲日</h2><div class='tabs'>" + "".join(f"<button onclick=\"sh('{sg}')\" id='b{sg}'>{sg}</button>" for sg in S5.SEG) + "</div>")
    for sg in S5.SEG:
        H.append(f"<div class='wrap seg' id='s{sg}'><table class='hm'><tr><th>H＼g</th>" + "".join(f"<th>{int(g * 100)}%</th>" for g in S5.GS) + "</tr>")
        mx = G[G["段"] == sg]["比例"].max()
        for Hh in S5.HS:
            H.append(f"<tr><th>{Hh}</th>")
            for g in S5.GS:
                r = pick(G, sg, Hh, g); v = r["比例"] if r is not None else np.nan
                a = 0 if not np.isfinite(v) or not mx else min(1, (v / mx) ** 0.35)
                H.append(f"<td style='background:rgba(214,64,69,{a:.2f})'>{'—' if not np.isfinite(v) else f'{v * 1e4:.1f}'}<br><small>{int(r['事件']) if r is not None else 0}</small></td>")
            H.append("</tr>")
        H.append(f"</table></div>")
    H.append("<p class='note'>格內上：每萬個股-日的起漲事件數；下：事件數。深色＝多。同一檔同一格事件後 H 日內不重算。</p>")
    H.append("<h2>二、每個起漲事件最後漲多少</h2><div class='wrap'><table><tr><th class='l'>段／口徑</th><th>事件</th>" + "".join(f"<th>{b}</th>" for b in BUCKN) + "</tr>")
    for r in MG.to_dict("records"):
        H.append(f"<tr><td class='l'>{r['段']}<br><small>{r['口徑']}</small></td><td>{r['起漲事件（聯集）']}</td>" + "".join(f"<td>{P_(r[f'占比_{b}'], 0)}</td>" for b in BUCKN) + "</tr>")
    H.append("</table></div>")
    H.append("<h2>三、漲 50%／100%／200% 花幾個交易日</h2><div class='wrap'><table><tr><th>段</th><th>漲幅</th><th>事件</th><th>一半的人在幾天內</th><th>中間一半</th></tr>")
    for sg in S5.SEG:
        for g in (0.5, 1.0, 2.0):
            r = pick(G, sg, 250, g)
            if r is not None and r["事件"] > 0:
                H.append(f"<tr><td>{sg}</td><td>{int(g * 100)}%</td><td>{int(r['事件'])}</td><td>{N_(r['最短花幾天_p50'])}</td><td>{N_(r['最短花幾天_p25'])}～{N_(r['最短花幾天_p75'])}</td></tr>")
    H.append("</table></div><p class='note'>以 250 日內漲到的事件為準；天數 ＝ 那一段漲勢裡最快漲到的交易日數；「一半的人」＝ 中位數。</p>")
    H.append("<h2>四、漲到高點之後</h2><div class='wrap'><table><tr><th class='l'>段／格</th><th>事件</th><th>回落 20%</th><th>回落 30%</th><th>回落 50%（妖股）</th><th>回落 70%</th></tr>")
    for sg in S5.SEG:
        for Hh, g in ((60, 1.0), (120, 2.0), (250, 5.0)):
            r = pick(G, sg, Hh, g)
            if r is None or r["事件"] == 0:
                continue
            H.append(f"<tr><td class='l'>{sg}<br><small>{Hh} 日內漲 {int(g * 100)}%</small></td><td>{int(r['事件'])}</td>" +
                     "".join(f"<td>{P_(r[f'回落{x}%_比例'], 0)}<br><small>高點後 {N_(r[f'回落{x}%_P到觸及中位日'])} 天</small></td>" for x in (20, 30, 50, 70)) + "</tr>")
    H.append("</table></div><p class='note'>比例 ＝ 高點之後（到資料尾為止）曾經跌到高點 ×（1−x）的事件占比；天數是中位數。</p>")
    H.append("<h2>五、買不買得到</h2><div class='wrap'><table><tr><th class='l'>段／格</th><th>隔天鎖漲停</th><th>隔天處置中</th><th>成交額最低五分之一</th></tr>")
    for sg in S5.SEG:
        for Hh, g in ((60, 1.0), (250, 3.0)):
            r = BUY[(BUY["段"] == sg) & (BUY["H"] == Hh) & np.isclose(BUY["g"], g)]
            if len(r):
                r = r.iloc[0]
                H.append(f"<tr><td class='l'>{sg}<br><small>{Hh} 日內漲 {int(g * 100)}%</small></td><td>{P_(r['t+1漲停鎖死'])}</td><td>{P_(r['t+1處置中'])}</td><td>{P_(r['20日均額Q1'])}</td></tr>")
    H.append("</table></div>")
    H.append("<p class='note'>第二批（特徵：起漲前長什麼樣、買了賺不賺、妖股與結束特徵）另交。</p>")
    H.append("<script>function sh(k){document.querySelectorAll('.seg').forEach(e=>e.style.display=e.id=='s'+k?'block':'none');document.querySelectorAll('.tabs button').forEach(b=>b.className=b.id=='b'+k?'on':'')}sh('探索')</script></main></body></html>")
    open(os.path.join(S5.OUT, "飆股回推seq5_第一批_20260929.html"), "w", encoding="utf-8").write("\n".join(H))
