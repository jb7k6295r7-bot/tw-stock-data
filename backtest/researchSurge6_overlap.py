# -*- coding: utf-8 -*-
"""PREREG飆股回推 seq6 追加：14 個特徵在飆股身上的重疊率（⛔ 只描述：不判定、不計 N、不挑格）——回測線子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchSurge6_overlap [--check]

═══ 讀法（寫死於 2026-09-29 19:42（台北），在算任何重疊數字之前）═══
 V1 資料：沿用 seq6（commit 8b8ac28230）的 events（~/s6work/events.npz，2021-01～2026-08、右截斷 2026-08-31）與 s5work 五等分表 Q；
    探索、確認兩段合併（2021-01～2026-08）
 V2 格：seq6 的 250 格（H 10～250 × g 50%～≥1000%）中，兩段合併事件 ≥ 30 的每一格都算；⛔ 不挑格
 V3 特徵（14 個，名稱照 feat_summary.csv「特徵」欄；有 ＝ Q 碼相等）：見 FEATS
 V4 缺值：某特徵在該列沒有值（Q＝0）⇒ 該特徵「沒有值」
    兩兩：P(B|A) ＝ #(A 且 B) ÷ #(A 且 B 有值)；Jaccard ＝ #(A 且 B) ÷ #(A 或 B)，都只在 A、B 兩個都有值的列算
    個數與組合：沒有值 ＝ 沒有（照實報各列平均有值的特徵數）
 V5 一般股-日（對照）：同一格的定義域 ＝ 兩段內有 K 棒、seq6 右截斷定義域 hdef6 ≥ H 的全部股-日（含飆股本身）；只和 H 有關 ⇒ 每個 H 算一次，對到該 H 的各格
 V6 彙總：先各格算，再取合格格的中位數，附 p10～p90；一般股-日也取同一批格的中位數
 V7 組合 ＝ 該列「有」的特徵集合（完全相同才算同一組合）；前 10 名 ＝ 非空組合依飆股比例的格中位數排序；空集合另見個數分佈的「0 個」
 V8 查核（--check）：抽 2 格，用 pandas 逐列自己重算 P(B|A)、Jaccard（2 對）與個數分佈 ⇒ 對 overlap_cells.csv.gz
輸出 backtest/resultsSurge6/overlap/
"""
from __future__ import annotations

import argparse
import html
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D

TIME = "2026-09-29 19:42（台北）"
ST = os.path.expanduser("~/evtdata/stitch_950ad26e12_b53f5540a8/data")
WORK5 = os.path.expanduser("~/s5work"); WORK6 = os.path.expanduser("~/s6work")
OUT = "backtest/resultsSurge6/overlap"
HS = list(range(10, 251, 10)); GS = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.0, 10.0]
FEATS = [("距5日最低｜Q1", "dlo_5", 1), ("距10日最低｜Q1", "dlo_10", 1), ("收盤÷MA5−1｜Q1", "ma_5", 1), ("5日報酬｜Q1", "r_5", 1),
         ("60日平均周轉率｜Q5", "turn_60", 5), ("120日報酬｜Q5", "r_120", 5), ("融資使用率｜Q5", "musage", 5),
         ("原：股價級距｜＜20 元", "d_px", 1), ("原：均線多頭排列5>20>60>100｜是", "d_bull", 2), ("原：注意股60日次數級距｜≥3 次", "d_att60", 3),
         ("原R2營收年增≥50%｜是", "d_R2a", 2), ("原：EPS轉正｜是", "d_eps", 2), ("原：營收創24月新高｜是", "d_revhi", 2), ("原：20日漲停天數級距｜≥3 次", "d_lu20", 4)]
K = len(FEATS)
SHORT = ["距5日低Q1", "距10日低Q1", "MA5乖離Q1", "5日報酬Q1", "60日周轉Q5", "120日報酬Q5", "融資使用Q5", "股價<20", "多頭排列", "注意≥3次",
         "營收年增≥50%", "EPS轉正", "營收24月新高", "20日漲停≥3"]
MINEV = 30


def cname(c):
    return f"H{HS[c // 10]}_g{int(round(GS[c % 10] * 100))}%"


def load():
    uni = pd.read_csv(os.path.join(WORK5, "uni.csv"), dtype=str)
    D.DATA = ST; cal = D.load_calendar(); n = len(cal)
    fcol = json.load(open(os.path.join(WORK5, "build.json"), encoding="utf-8"))["特徵欄"]; FX = {c: i for i, c in enumerate(fcol)}
    fs = pd.read_csv("backtest/resultsSurge6/feat_summary.csv")
    for nm, col, code in FEATS:                                                    # 名稱對 feat_summary
        r = fs[fs["特徵"] == nm]
        assert len(r) == 1 and r.iloc[0]["欄"] == col and int(r.iloc[0]["碼"]) == code, nm
    Qm = np.load(os.path.join(WORK5, "Q.npy"), mmap_mode="r")
    Qs = np.stack([np.asarray(Qm[FX[col]]) for _, col, _ in FEATS])               # (K, S, n) int8
    mon = np.array([d.year * 12 + d.month - 1 for d in cal])
    inseg = (mon >= 2021 * 12) & (mon <= 2026 * 12 + 7)
    bar = np.load(os.path.join(WORK5, "bar.npy")); h6 = np.load(os.path.join(WORK6, "hdef6.npy"))
    E = dict(np.load(os.path.join(WORK6, "events.npz")))
    return uni, cal, Qs, inseg, bar, h6, E


def stats(P, Dm):
    """P、Dm：(N, K) bool（有、有值）⇒ 兩兩計數與個數、組合。"""
    Pf = P.astype(np.float32); Df = Dm.astype(np.float32)
    both = Pf.T @ Pf                                  # #(A 且 B)
    a_bdef = Pf.T @ Df                                # #(A 且 B 有值)
    dd = Df.T @ Df                                    # #(A、B 都有值)
    # #(A 或 B，兩個都有值) ＝ #(A 且 B 有值) ＋ #(B 且 A 有值) − #(A 且 B)
    union = a_bdef + a_bdef.T - both
    with np.errstate(invalid="ignore", divide="ignore"):
        pba = both / a_bdef                           # [a, b] ＝ P(B|A)
        jac = both / union
    cnt = P.sum(1)
    dist = np.bincount(np.minimum(cnt, 5), minlength=6) / max(len(cnt), 1)
    mask = (P.astype(np.int64) * (1 << np.arange(K))).sum(1)
    u, c = np.unique(mask, return_counts=True)
    return {"pba": pba, "jac": jac, "dist": dist, "combo": dict(zip(u.tolist(), (c / len(mask)).tolist())), "N": len(cnt),
            "有值數平均": float(Dm.sum(1).mean()) if len(cnt) else np.nan}


def run(log):
    uni, cal, Qs, inseg, bar, h6, E = load()
    code = np.array([c for _, _, c in FEATS], np.int8)
    ec, es, ed = E["cell"].astype(int), E["s"].astype(int), E["d"].astype(int)
    assert inseg[ed].all()
    cnt = np.bincount(ec, minlength=250); cells = [c for c in range(250) if cnt[c] >= MINEV]
    log(f"[重疊] 合格格 {len(cells)}／250（事件 ≥ {MINEV}）")
    SUR = {}
    for c in cells:
        k = np.flatnonzero(ec == c)
        q = Qs[:, es[k], ed[k]].T                     # (n_ev, K)
        SUR[c] = stats(q == code[None, :], q > 0)
    log("[重疊] 飆股各格完成")
    GEN = {}
    rows = bar & inseg[None, :]
    for H in sorted({HS[c // 10] for c in cells}):
        ss, tt = np.nonzero(rows & (h6 >= H))
        q = Qs[:, ss, tt].T
        GEN[H] = stats(q == code[None, :], q > 0)
        log(f"[重疊] 一般股-日 H{H}：{len(ss):,} 列")
    # 各格長表
    L = []
    for c in cells:
        s_, g_ = SUR[c], GEN[HS[c // 10]]
        for a in range(K):
            for b in range(K):
                if a != b:
                    L.append({"格": cname(c), "事件": int(cnt[c]), "A": FEATS[a][0], "B": FEATS[b][0], "飆股 P(B|A)": s_["pba"][a, b], "飆股 Jaccard": s_["jac"][a, b],
                              "一般 P(B|A)": g_["pba"][a, b], "一般 Jaccard": g_["jac"][a, b]})
    CL = pd.DataFrame(L); CL.to_csv(os.path.join(OUT, "overlap_cells.csv.gz"), index=False, float_format="%.6g")
    q3 = lambda x: (np.nanmedian(x), np.nanpercentile(x, 10), np.nanpercentile(x, 90))
    PR = []
    for a in range(K):
        for b in range(K):
            if a == b:
                continue
            x1 = q3([SUR[c]["pba"][a, b] for c in cells]); x2 = q3([SUR[c]["jac"][a, b] for c in cells])
            x3 = q3([GEN[HS[c // 10]]["pba"][a, b] for c in cells]); x4 = q3([GEN[HS[c // 10]]["jac"][a, b] for c in cells])
            PR.append({"A": FEATS[a][0], "B": FEATS[b][0], "飆股 P(B|A) 中位": x1[0], "p10": x1[1], "p90": x1[2],
                       "飆股 Jaccard 中位": x2[0], "J p10": x2[1], "J p90": x2[2], "一般 P(B|A) 中位": x3[0], "一般 J 中位": x4[0],
                       "飆股÷一般（P(B|A) 中位比）": x1[0] / x3[0] if x3[0] > 0 else np.nan})
    PR = pd.DataFrame(PR); PR.to_csv(os.path.join(OUT, "pairs.csv"), index=False, float_format="%.5g")
    # 個數分佈
    DI = []
    lab = ["0 個", "1 個", "2 個", "3 個", "4 個", "5 個以上"]
    for i, lb in enumerate(lab):
        x = q3([SUR[c]["dist"][i] for c in cells]); y = q3([GEN[HS[c // 10]]["dist"][i] for c in cells])
        DI.append({"同時有幾個": lb, "飆股 中位": x[0], "飆股 p10": x[1], "飆股 p90": x[2], "一般 中位": y[0], "一般 p10": y[1], "一般 p90": y[2]})
    DI = pd.DataFrame(DI); DI.to_csv(os.path.join(OUT, "count_dist.csv"), index=False, float_format="%.5g")
    # 組合
    allm = set()
    for c in cells:
        allm |= {m for m, v in SUR[c]["combo"].items() if m != 0}
    CB = []
    for m in allm:
        xs = [SUR[c]["combo"].get(m, 0.0) for c in cells]; ys = [GEN[HS[c // 10]]["combo"].get(m, 0.0) for c in cells]
        CB.append({"組合": "＋".join(FEATS[i][0] for i in range(K) if m >> i & 1), "特徵數": bin(m).count("1"), "飆股 中位": float(np.median(xs)),
                   "飆股 p10": float(np.percentile(xs, 10)), "飆股 p90": float(np.percentile(xs, 90)), "一般 中位": float(np.median(ys)),
                   "飆股÷一般": float(np.median(xs)) / float(np.median(ys)) if np.median(ys) > 0 else np.nan, "_m": m})
    CB = pd.DataFrame(CB).sort_values(["飆股 中位", "飆股 p90"], ascending=False)
    CB.drop(columns="_m").head(50).to_csv(os.path.join(OUT, "combos_top50.csv"), index=False, float_format="%.5g")
    META = {"讀法寫死": TIME, "合格格數": len(cells), "合格格": [cname(c) for c in cells], "事件數（合格格加總，同一事件可跨格）": int(sum(cnt[c] for c in cells)),
            "飆股 各列平均有值特徵數（格中位）": float(np.median([SUR[c]["有值數平均"] for c in cells])),
            "一般 各列平均有值特徵數（格中位）": float(np.median([GEN[HS[c // 10]]["有值數平均"] for c in cells])),
            "特徵": [f[0] for f in FEATS]}
    json.dump(META, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    page(META, PR, DI, CB.head(10))
    log("[重疊] 輸出完成")


C_ = lambda x: "—" if not np.isfinite(x) else f"{x * 100:.1f}%"


def page(META, PR, DI, CB):
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0]
    CSS += "\ntd.l,th.l{text-align:left}small{color:#666}.hm td,.hm th{font-size:11px;padding:3px 4px;text-align:center}.hm th.r{writing-mode:vertical-rl;white-space:nowrap}"
    H = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
         "<title>飆股特徵重疊</title>", f"<style>{CSS}</style></head><body><main>", "<h1>飆股身上的特徵會一起出現嗎？（2021–2026-08）</h1>",
         f"<p class='lead'>只描述，不判定、不計檢定數、不挑格。{META['合格格數']} 種飆股定義（10～250 天內漲 50%～10 倍以上，事件 ≥ 30 的格）各算一次，取中位數。讀法寫死 {html.escape(META['讀法寫死'])}。</p>",
         "<h2>一、有 A 的飆股裡，也有 B 的比例</h2><p class='note'>格內大字 ＝ 飆股的 P(B|A)（格中位）；小字 ＝ 一般股-日同一對。底色越紅 ＝ 飆股比一般更常一起出現（比值 ＞ 1），越藍 ＝ 比一般少。列 ＝ A，欄 ＝ B。</p>",
         "<div class='wrap'><table class='hm'><tr><th></th>" + "".join(f"<th class='r'>{html.escape(s)}</th>" for s in SHORT) + "</tr>"]
    P = PR.set_index(["A", "B"])
    for a in range(K):
        H.append(f"<tr><th class='l'>{html.escape(SHORT[a])}</th>")
        for b in range(K):
            if a == b:
                H.append("<td style='background:#eee'>—</td>"); continue
            r = P.loc[(FEATS[a][0], FEATS[b][0])]
            v, g, ratio = r["飆股 P(B|A) 中位"], r["一般 P(B|A) 中位"], r["飆股÷一般（P(B|A) 中位比）"]
            lr = np.log2(ratio) if np.isfinite(ratio) and ratio > 0 else 0.0; al = min(1, abs(lr) / 2)
            col = f"rgba(214,64,69,{al:.2f})" if lr > 0 else f"rgba(43,108,176,{al:.2f})"
            H.append(f"<td style='background:{col}'>{v * 100:.0f}<br><small>{g * 100:.0f}</small></td>" if np.isfinite(v) else "<td>—</td>")
        H.append("</tr>")
    H.append("</table></div><p class='note'>單位 %。兩個都有值的列才算（財報、融資類在部分股票沒有值）。Jaccard 與 p10～p90 見 pairs.csv。</p>")
    H.append("<h2>二、每個飆股身上同時有幾個</h2><div class='wrap'><table><tr><th class='l'>同時有</th><th>飆股（中位；p10～p90）</th><th>一般股-日</th></tr>")
    for r in DI.to_dict("records"):
        H.append(f"<tr><td class='l'>{r['同時有幾個']}</td><td>{C_(r['飆股 中位'])}<br><small>{C_(r['飆股 p10'])}～{C_(r['飆股 p90'])}</small></td><td>{C_(r['一般 中位'])}</td></tr>")
    H.append(f"</table></div><p class='note'>沒有值算「沒有」。每列平均有值的特徵數：飆股 {META['飆股 各列平均有值特徵數（格中位）']:.1f}、一般 {META['一般 各列平均有值特徵數（格中位）']:.1f}（共 14 個）。</p>")
    H.append("<h2>三、最常見的組合（前 10）</h2><div class='wrap'><table><tr><th class='l'>組合（剛好就是這幾個）</th><th>飆股（中位；p10～p90）</th><th>一般股-日</th><th>飆股÷一般</th></tr>")
    for r in CB.to_dict("records"):
        rt = r["飆股÷一般"]; rts = "—" if not np.isfinite(rt) else f"{rt:.2f}"
        H.append(f"<tr><td class='l'>{html.escape(r['組合'])}</td><td>{C_(r['飆股 中位'])}<br><small>{C_(r['飆股 p10'])}～{C_(r['飆股 p90'])}</small></td><td>{C_(r['一般 中位'])}</td>"
                 f"<td>{rts}</td></tr>")
    H.append("</table></div><p class='note'>前 50 名見 combos_top50.csv。</p></main></body></html>")
    open(os.path.join(OUT, "飆股特徵重疊.html"), "w", encoding="utf-8").write("\n".join(H))


def check(log):
    uni, cal, Qs, inseg, bar, h6, E = load()
    CL = pd.read_csv(os.path.join(OUT, "overlap_cells.csv.gz"))
    ec = E["cell"].astype(int); cnt = np.bincount(ec, minlength=250)
    cells = [c for c in range(250) if cnt[c] >= MINEV]
    rng = np.random.default_rng(20260929); pick = rng.choice(cells, 2, replace=False)
    names = [f[0] for f in FEATS]; errs = []
    for c in pick:
        k = np.flatnonzero(ec == c)
        df = pd.DataFrame({nm: Qs[i, E["s"][k].astype(int), E["d"][k].astype(int)] for i, nm in enumerate(names)})
        for a, b in ((0, 7), (10, 12)):
            A_, B_ = names[a], names[b]; sub = df[(df[A_] > 0) & (df[B_] > 0)]
            ha = sub[A_] == FEATS[a][2]; hb = sub[B_] == FEATS[b][2]
            mine = ((ha & hb).sum() / ha.sum(), (ha & hb).sum() / (ha | hb).sum())
            r = CL[(CL["格"] == cname(c)) & (CL["A"] == A_) & (CL["B"] == B_)].iloc[0]
            if not np.allclose(mine, (r["飆股 P(B|A)"], r["飆股 Jaccard"]), rtol=1e-4, equal_nan=True):
                errs.append(f"{cname(c)} {A_}→{B_}：自算 {mine} 檔 {(r['飆股 P(B|A)'], r['飆股 Jaccard'])}")
        # 一般股-日（該格 H）同一對
        H = HS[c // 10]; ss, tt = np.nonzero(bar & inseg[None, :] & (h6 >= H))
        qa, qb = Qs[0, ss, tt], Qs[7, ss, tt]; ok = (qa > 0) & (qb > 0)
        mine_g = ((qa == 1) & (qb == 1) & ok).sum() / ((qa == 1) & ok).sum()
        r = CL[(CL["格"] == cname(c)) & (CL["A"] == names[0]) & (CL["B"] == names[7])].iloc[0]
        if not np.isclose(mine_g, r["一般 P(B|A)"], rtol=1e-4):
            errs.append(f"{cname(c)} 一般：自算 {mine_g} 檔 {r['一般 P(B|A)']}")
    out = {"抽格": [cname(c) for c in pick], "錯誤": errs}
    json.dump(out, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[查核] {out}")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); T0 = time.time()
    logf = open(os.path.join(OUT, "run_check.log" if a.check else "run.log"), "w", encoding="utf-8")

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    (check if a.check else run)(log)


if __name__ == "__main__":
    main()
