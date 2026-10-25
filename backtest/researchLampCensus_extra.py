# -*- coding: utf-8 -*-
"""近年燈號普查加報（產業 seq50 §二；裁定 seq478 §二核：描述、⛔ 不判定、不計 N）——回測線計算子代理。
讀 researchLampCensus 主程式同一輸出夾（signals.csv、rows.csv、caps.csv、main.json 的來源清單），加算六項：
 X1 對照組（電子、傳產分開）：
    (a) 同股任意季 ＝ 訊號每一檔在 2021Q1～2024Q3 共 15 個季末各進場一次（季末後第一個交易日開盤，與主表同口徑），對大盤超額取平均（該 H 未到的季不算）；
        訊號值 ＝ 各檔平均。
    (b) 同產業隨機 ＝ 同一進場日（燈 1 季末後第一個交易日）、同一證交所產業別（data/meta/industry_hist/industry_pit.csv 在燈 1 季最後一日的產業別）、
        燈 1 季最後一個月市值 ≥100 億（同主表 tw_cap）的全部股票等權，含之後下市者（下市照主表「下市結算」）；★ 含訊號股本身。
        ⚠ industry_pit 已下市公司多半沒有產業段 ⇒ 當日查不到產業別的股票無法歸類（照列筆數與市值 ≥100 億者）。
    報：訊號 − 對照 的中位、訊號勝過對照（差 ＞0）的比例；★ 以燈 1 季為群的叢集自助法區間（季有放回抽 B=2000 次、種子 20261026、2.5～97.5 百分位）。
 X2 依燈 1 年份（2021～2024）分列：訊號超額（中位、平均）、股票毛報酬 R（還原、扣成本前？★ 照主表 R＝已扣 0.585%）與大盤毛報酬（market_tri）的中位、平均。
 X3 右尾拆解（套規模下限的訊號樣本）：平均、去掉最大 1 名的平均、去掉最大 3 名的平均、中位、前 5 名。
 X4 電子類規模剔除名單與燈 1 季末市值（整個訊號剔除與部分剔除分開）。
 X5 另一進場：燈 1 出處日期的次一交易日開盤（規模下限仍用燈 1 季末市值，照主表）；只報中位、≥+2 份比例、最好值。
 X6 命中代理：進場後 24 個月內（含）任一日 收盤÷進場開盤 ≥2（絕對 2 倍）、(收盤÷進場開盤)÷(大盤÷進場前一日大盤) ≥2（相對大盤 2 倍）；
    壞根 ⇒ 只看第一個壞根之前；下市 ⇒ 看到最後有效日；24 月窗未走完 ⇒ 不入分母（件數照報）。報每檔比例、訊號內任一檔命中比例；
    同產業隨機母體的同口徑比例當對照。
 情境：照實（＝寬鬆）為主；嚴格（燈 1 兩可不算）、剔自評知道 只在 X1 摘要表另列。
    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLampCensus_extra [--out 主程式輸出夾] [--dry]
輸出（同夾）：extra_control.csv、extra_universe.csv、extra_stats.csv、extra_hit2.csv、extra_alt_entry.csv、summary_extra.md、extra_main.json
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchLampCensus as LC               # noqa: E402
from backtest import researchV41EV as V                    # noqa: E402

QUARTERS = [f"{y}-{m:02d}" for y in (2021, 2022, 2023, 2024) for m in (3, 6, 9, 12)][:15]   # 2021Q1～2024Q3 季末月
HS = ("12", "24", "末")
B = 2000
SEED = 20261026
log = LC.log


def pit_table(sha):
    t = subprocess.run(["git", "show", f"{sha}:data/meta/industry_hist/industry_pit.csv"], capture_output=True, check=True).stdout
    P = pd.read_csv(io.BytesIO(t), dtype=str, keep_default_na=False)
    P["s"] = pd.to_datetime(P["start"].replace("", "1900-01-01")); P["e"] = pd.to_datetime(P["end"].replace("", "2262-01-01"))
    return P


def ind_at(P, sid, d):
    q = P[(P["stock_id"] == sid) & (P["s"] <= d) & (P["e"] >= d)]
    return q["industry"].iloc[0] if len(q) else None


def boot(diff, grp, rng):
    """以季為群：回 (中位 lo, hi, 勝過比例 lo, hi)。"""
    diff = np.asarray(diff, float); grp = np.asarray(grp)
    ok = np.isfinite(diff); diff, grp = diff[ok], grp[ok]
    if len(diff) < 2:
        return (np.nan,) * 4
    G = sorted(set(grp)); idx = {g: np.flatnonzero(grp == g) for g in G}
    med = []; win = []
    for _ in range(B):
        pick = rng.choice(len(G), len(G), replace=True)
        v = np.concatenate([diff[idx[G[k]]] for k in pick])
        med.append(np.median(v)); win.append((v > 0).mean())
    return (np.percentile(med, 2.5), np.percentile(med, 97.5), np.percentile(win, 2.5), np.percentile(win, 97.5))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=LC.OUT); ap.add_argument("--dry", action="store_true"); a = ap.parse_args()
    out = a.out; t0 = time.time()
    MJ = json.load(open(os.path.join(out, "main.json"), encoding="utf-8"))
    srcs = [x["檔"] for x in MJ["來源"]]
    S, info = LC.load_signals(srcs)
    SG = pd.read_csv(os.path.join(out, "signals.csv"), dtype={"訊號": str})
    RW = pd.read_csv(os.path.join(out, "rows.csv"), dtype={"代號": str, "H": str})
    CP = pd.read_csv(os.path.join(out, "caps.csv"), dtype={"代號": str})
    ok = RW[RW["入選"].astype(str).eq("True") & RW["R"].notna()].copy()
    mem = ok[(ok["段"] == "燈1") & (ok["H"] == "末")].groupby("訊號")["代號"].apply(list).to_dict()
    EN = LC.Engine(); sha = EN.sha; CAL = EN.CAL
    P = pit_table(sha); cache = {}

    def capv(sid, ym):
        return V.tw_cap(sha, sid, ym, [], cache)[0]

    def settle_all(sid, e):
        i = EN.ix[sid]; r = {}
        for H in HS:
            tgt = None if H == "末" else CAL[e] + pd.DateOffset(months=int(H))
            x = EN.settle(i, sid, e, tgt)
            r[H] = np.nan if x["未到"] else x["超額"]
            r["R" + H] = np.nan if x["未到"] else x["R"]; r["M" + H] = np.nan if x["未到"] else x["大盤"]
        return r

    def hit2(sid, e):
        i = EN.ix[sid]; tgt = CAL[e] + pd.DateOffset(months=24)
        complete = tgt <= CAL[EN.CEND]
        x = EN.CEND if not complete else int(CAL.searchsorted(tgt, "right")) - 1
        bb = np.flatnonzero(EN.BAD[i, e + 1:x + 1])
        xe = (e + int(bb[0])) if len(bb) else x
        lastv = int(EN.LASTV[i]); xe = min(xe, lastv)
        seg = np.arange(e, xe + 1); c = EN.C[i, seg]; okk = np.isfinite(c)
        g = c[okk] / EN.O[i, e]
        m0 = V.tri_at(EN.T, CAL[e - 1]); mk = np.array([V.tri_at(EN.T, CAL[p]) / m0 for p in seg[okk]])
        ab = bool((g >= 2).any()); rel = bool(((g / mk) >= 2).any())
        delist = (EN.CEND - lastv) >= 5 and lastv < x
        cut = bool(len(bb)) or delist
        return ab, rel, bool(complete or delist), cut      # 24 月窗走完、或已下市（結果已定）⇒ 入分母

    # ── X1 (a) 同股任意季
    stocks = sorted({c for v in mem.values() for c in v})
    A = {}
    for sid in stocks:
        acc = {H: [] for H in HS}
        for ym in QUARTERS:
            en = EN.entry(sid, ym)
            if en[0] is None:
                continue
            r = settle_all(sid, en[1])
            for H in HS:
                if np.isfinite(r[H]):
                    acc[H].append(r[H])
        A[sid] = {H: (np.mean(acc[H]) if acc[H] else np.nan) for H in HS}
        A[sid].update({f"n{H}": len(acc[H]) for H in HS})
    log(f"[對照 a] {len(stocks)} 檔｜{time.time() - t0:.0f}s")

    # ── X1 (b) 同產業隨機
    allids = sorted(EN.ix)
    UNI = {}; ULOG = []

    def universe(ind, ym):
        key = (ind, ym)
        if key in UNI:
            return UNI[key]
        d = pd.Period(ym, "M").end_time.normalize()
        cand = sorted(set(P[(P["industry"] == ind) & (P["s"] <= d) & (P["e"] >= d)]["stock_id"]) & set(allids))
        memb = [s for s in cand if (lambda v: np.isfinite(v) and v >= 1e10)(capv(s, ym))]
        res = {H: [] for H in HS}; h_ab = []; h_rel = []; dl = 0
        for s in memb:
            en = EN.entry(s, ym)
            if en[0] is None:
                continue
            r = settle_all(s, en[1])
            for H in HS:
                if np.isfinite(r[H]):
                    res[H].append(r[H])
            ab, rel, comp, cut = hit2(s, en[1])
            if comp:
                h_ab.append(ab); h_rel.append(rel)
            dl += int((EN.CEND - int(EN.LASTV[EN.ix[s]])) >= 5)
        UNI[key] = {**{H: (np.mean(res[H]) if res[H] else np.nan) for H in HS}, **{f"n{H}": len(res[H]) for H in HS},
                    "abs2": np.mean(h_ab) if h_ab else np.nan, "rel2": np.mean(h_rel) if h_rel else np.nan, "成員": len(memb), "候選": len(cand), "其中已下市": dl,
                    "成員代號": "／".join(memb)}
        ULOG.append({"產業別": ind, "季末月": ym, **{k: v for k, v in UNI[key].items()}})
        return UNI[key]

    # 查不到產業別、市值 ≥100 億者（每季）
    nopit = []
    for ym in sorted({LC.q_last_month(q) for q in SG["燈1季"]}):
        d = pd.Period(ym, "M").end_time.normalize()
        covered = set(P[(P["s"] <= d) & (P["e"] >= d)]["stock_id"])
        big = [s for s in allids if s not in covered and s.isdigit() and len(s) == 4 and not s.startswith("00") and (lambda v: np.isfinite(v) and v >= 1e10)(capv(s, ym))]
        nopit.append({"季末月": ym, "查無產業別且市值≥100億": len(big), "代號": "／".join(big)})
    log(f"[查無產業別] {time.time() - t0:.0f}s")

    # ── 每訊號
    srow = S.set_index("訊號")
    REC = []; ALT = []; HIT = []
    for _, r in SG.iterrows():
        k = r["訊號"]
        if r["無點名"] or k not in mem:
            continue
        ym = LC.q_last_month(r["燈1季"]); d = pd.Period(ym, "M").end_time.normalize()
        cs = mem[k]
        rec = {"訊號": k, "類": r["類"], "甲": r["甲"], "乙": r["乙"], "型": r["型"], "燈1季": r["燈1季"], "年": r["燈1季"][:4], "兩可": r["兩可"],
               "自評知道": r.get("自評知道", False), "各檔": "／".join(cs)}
        inds = []; ub = {H: [] for H in HS}; uab = []; urel = []
        for c in cs:
            ind = ind_at(P, c, d); inds.append(ind or "查無")
            if ind:
                u = universe(ind, ym)
                for H in HS:
                    ub[H].append(u[H])
                uab.append(u["abs2"]); urel.append(u["rel2"])
        rec["產業別"] = "／".join(inds)
        for H in HS:
            q = ok[(ok["訊號"] == k) & (ok["段"] == "燈1") & (ok["H"] == H)]
            sv = r[f"{H}_超額"]
            rec[f"訊號_{H}"] = sv
            rec[f"R_{H}"] = q["R"].mean() if np.isfinite(sv) else np.nan
            rec[f"大盤_{H}"] = q["大盤"].mean() if np.isfinite(sv) else np.nan
            av = [A[c][H] for c in cs]
            rec[f"對照a_{H}"] = np.mean(av) if all(np.isfinite(av)) else np.nan
            rec[f"對照b_{H}"] = np.mean(ub[H]) if len(ub[H]) == len(cs) and all(np.isfinite(ub[H])) else np.nan
            rec[f"差a_{H}"] = sv - rec[f"對照a_{H}"]; rec[f"差b_{H}"] = sv - rec[f"對照b_{H}"]
        # X6
        hs_ = []
        for c in cs:
            en = EN.entry(c, ym); ab, rel, comp, cut = hit2(c, en[1])
            hs_.append((ab, rel, comp))
            HIT.append({"訊號": k, "類": r["類"], "代號": c, "進場日": str(CAL[en[1]].date()), "絕對2倍": ab, "相對2倍": rel, "24月完整": comp, "截斷或下市": cut})
        comp_all = all(h[2] for h in hs_)
        rec["24月完整"] = comp_all
        rec["絕對2倍_比例"] = np.mean([h[0] for h in hs_]) if comp_all else np.nan
        rec["相對2倍_比例"] = np.mean([h[1] for h in hs_]) if comp_all else np.nan
        rec["絕對2倍_任一"] = float(any(h[0] for h in hs_)) if comp_all else np.nan
        rec["相對2倍_任一"] = float(any(h[1] for h in hs_)) if comp_all else np.nan
        rec["對照b_絕對2倍"] = np.mean(uab) if len(uab) == len(cs) and comp_all else np.nan
        rec["對照b_相對2倍"] = np.mean(urel) if len(urel) == len(cs) and comp_all else np.nan
        # X5 出處日次一交易日
        dd = pd.to_datetime(srow.loc[k, "燈1出處日期"], errors="coerce")
        if pd.isna(dd):
            rec.update({f"出處日_{H}": np.nan for H in HS}); rec["出處日進場"] = "日期讀不出"
        else:
            vals = {H: [] for H in HS}; ents = []
            for c in cs:
                i = EN.ix[c]; p = int(CAL.searchsorted(dd, "right"))
                while p <= EN.CEND and not EN.opened(i, p):
                    p += 1
                ents.append(str(CAL[p].date()))
                rr = settle_all(c, p)
                for H in HS:
                    vals[H].append(rr[H])
                    ALT.append({"訊號": k, "代號": c, "出處日期": str(dd.date()), "進場日": str(CAL[p].date()), "H": H, "超額": rr[H]})
            for H in HS:
                rec[f"出處日_{H}"] = np.mean(vals[H]) if all(np.isfinite(vals[H])) else np.nan
            rec["出處日進場"] = "／".join(sorted(set(ents)))
        REC.append(rec)
    XC = pd.DataFrame(REC)
    log(f"[每訊號] {len(XC)}｜{time.time() - t0:.0f}s")

    # ── 統計
    rng = np.random.default_rng(SEED)
    ST = []
    classes = [c for c in ("傳產", "電子") if (XC["類"] == c).any()]
    groups = classes + (["合計"] if len(classes) > 1 else [])

    def subset(gp, ver, sc):
        d = XC if gp == "合計" else XC[XC["類"] == gp]
        d = d[d[ver].astype(bool)]
        if sc == "嚴格":
            d = d[~d["兩可"].astype(bool)]
        if sc == "剔自評知道":
            d = d[~d["自評知道"].astype(bool)]
        return d

    scens = ["照實"] + (["嚴格"] if info["有判定把握欄"] else []) + (["剔自評知道"] if info["有自評欄"] else [])
    for sc in scens:
        for gp in groups:
            for ver in ("甲", "乙"):
                d = subset(gp, ver, sc)
                for H in HS:
                    for kind in ("a", "b"):
                        df = d[f"差{kind}_{H}"]; okm = df.notna()
                        lo, hi, wlo, whi = boot(df[okm], d.loc[okm, "燈1季"], rng)
                        ST.append({"表": "對照", "情境": sc, "類": gp, "版": ver, "H": H, "對照": {"a": "同股任意季", "b": "同產業隨機"}[kind], "n": int(okm.sum()),
                                   "季群數": d.loc[okm, "燈1季"].nunique(), "訊號中位": d.loc[okm, f"訊號_{H}"].median(), "對照中位": d.loc[okm, f"對照{kind}_{H}"].median(),
                                   "差中位": df[okm].median(), "勝過比例": (df[okm] > 0).mean() if okm.any() else np.nan,
                                   "差中位_lo": lo, "差中位_hi": hi, "勝過_lo": wlo, "勝過_hi": whi, "差平均": df[okm].mean()})
    for gp in groups:
        for ver in ("甲", "乙"):
            d = subset(gp, ver, "照實")
            for H in HS:
                for y in ("2021", "2022", "2023", "2024"):
                    q = d[(d["年"] == y) & d[f"訊號_{H}"].notna()]
                    ST.append({"表": "年份", "情境": "照實", "類": gp, "版": ver, "H": H, "年": y, "n": len(q), "未到": int(((d["年"] == y) & d[f"訊號_{H}"].isna()).sum()),
                               "超額中位": q[f"訊號_{H}"].median(), "超額平均": q[f"訊號_{H}"].mean(), "R中位": q[f"R_{H}"].median(), "R平均": q[f"R_{H}"].mean(),
                               "大盤中位": q[f"大盤_{H}"].median(), "大盤平均": q[f"大盤_{H}"].mean()})
                v = d[[f"訊號_{H}", "訊號"]].dropna().sort_values(f"訊號_{H}", ascending=False)
                x = v[f"訊號_{H}"].to_numpy()
                ST.append({"表": "右尾", "情境": "照實", "類": gp, "版": ver, "H": H, "n": len(x), "平均": x.mean() if len(x) else np.nan,
                           "去最大1平均": x[1:].mean() if len(x) > 1 else np.nan, "去最大3平均": x[3:].mean() if len(x) > 3 else np.nan,
                           "中位": np.median(x) if len(x) else np.nan, "前5名": "；".join(f"{s} {f:+.2f}" for s, f in zip(v["訊號"][:5], x[:5]))})
                a_ = d[f"出處日_{H}"].dropna(); m_ = d.loc[d[f"出處日_{H}"].notna(), f"訊號_{H}"]
                bi = d.loc[a_.idxmax(), "訊號"] if len(a_) else ""
                ST.append({"表": "出處日進場", "情境": "照實", "類": gp, "版": ver, "H": H, "n": len(a_), "中位": a_.median(), "≥+2比例": (a_ >= 2).mean() if len(a_) else np.nan,
                           "最好": a_.max() if len(a_) else np.nan, "最好訊號": bi, "同批季末中位": m_.median(), "同批季末≥+2比例": (m_ >= 2).mean() if len(m_) else np.nan,
                           "同批季末最好": m_.max() if len(m_) else np.nan})
            q = d[d["24月完整"].astype(bool)]
            hh = pd.DataFrame(HIT); hh = hh[hh["訊號"].isin(q["訊號"]) & hh["24月完整"]]
            ST.append({"表": "2倍", "情境": "照實", "類": gp, "版": ver, "H": "24", "n": len(q), "未滿24月": int((~d["24月完整"].astype(bool)).sum()),
                       "訊號任一檔_絕對2倍": q["絕對2倍_任一"].mean(), "訊號任一檔_相對2倍": q["相對2倍_任一"].mean(),
                       "訊號等權比例_絕對2倍": q["絕對2倍_比例"].mean(), "訊號等權比例_相對2倍": q["相對2倍_比例"].mean(),
                       "每檔_絕對2倍": hh["絕對2倍"].mean() if len(hh) else np.nan, "每檔_相對2倍": hh["相對2倍"].mean() if len(hh) else np.nan, "檔次": len(hh),
                       "對照b_絕對2倍": q["對照b_絕對2倍"].mean(), "對照b_相對2倍": q["對照b_相對2倍"].mean()})
    ST = pd.DataFrame(ST)
    XC.to_csv(os.path.join(out, "extra_control.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(ULOG).to_csv(os.path.join(out, "extra_universe.csv"), index=False, encoding="utf-8-sig")
    ST.to_csv(os.path.join(out, "extra_stats.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(HIT).to_csv(os.path.join(out, "extra_hit2.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(ALT).to_csv(os.path.join(out, "extra_alt_entry.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(nopit).to_csv(os.path.join(out, "extra_nopit.csv"), index=False, encoding="utf-8-sig")
    write_md(out, XC, ST, CP, SG, nopit, groups, scens, MJ, a.dry)
    json.dump({"性質": "普查加報（描述、不判定、不計 N）", "請求": "產業 seq50 §二；裁定 seq478 §二", "B": B, "種子": SEED, "秒": round(time.time() - t0),
               "讀法": __doc__}, open(os.path.join(out, "extra_main.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[完成] 加報｜{out}｜{time.time() - t0:.0f}s")


f2 = LC.f2
pc = LC.pc
HL = {"12": "12 月", "24": "24 月", "末": "到末日"}


def write_md(out, XC, ST, CP, SG, nopit, groups, scens, MJ, dry):
    md = [*[f"> ⭐ {x}" for x in LC.FINAL], "", LC.LIMIT.replace("，電子類還沒做", "（此句指傳產部分）") + "　" + LC.LIMIT_E, "",
          "# 普查加報：對照組、依年份、右尾拆解、規模剔除、出處日進場、相對 2 倍（產業 seq50 §二；裁定 seq478 §二）", "",
          f"- {'⚠ dry 試跑（不是正式數）' if dry else '正式輸出'}；主表同夾 summary.md。描述、⛔ 不判定、不計 N。單位份＝對大盤含息超額。",
          "- 清單：" + "；".join(os.path.basename(x["檔"]) for x in MJ["來源"]),
          f"- 區間＝以燈 1 季為群的叢集自助法（季有放回、B={B}、種子 {SEED}、2.5～97.5 百分位），不是精確信賴區間；樣本小、季群少時區間很寬。",
          "- 對照 (a) 同股任意季＝同一檔在 2021Q1～2024Q3 共 15 個季末各進場一次的平均；(b) 同產業隨機＝同進場日、同產業別（industry_pit 燈 1 季末當日）、"
          "燈 1 季末市值 ≥100 億的全部股票等權（含訊號股本身、含之後下市者）。", ""]
    nb = sum(x["查無產業別且市值≥100億"] for x in nopit)
    md += [f"- ⚠ industry_pit 對已下市公司多半沒有產業段 ⇒ 燈 1 季末當日查不到產業別、市值 ≥100 億的股票（無法放進 (b)）：各季合計 {nb} 檔次"
           + ("（" + "；".join(f"{x['季末月']}：{x['代號']}" for x in nopit if x["查無產業別且市值≥100億"]) + "）" if nb else "") + "。", ""]
    md += ["## 1. 對照組：訊號 − 對照（份；訊號＝1 個樣本）", "", "| 情境 | 類 | 版 | 段 | 對照 | n（季群） | 訊號中位 | 對照中位 | **差中位**［區間］ | 勝過比例［區間］ | 差平均 |",
           "|" + "---|" * 11]
    for sc in scens:
        for gp in groups:
            for ver in ("甲", "乙"):
                for H in HS:
                    for kind in ("同股任意季", "同產業隨機"):
                        s = ST[(ST["表"] == "對照") & (ST["情境"] == sc) & (ST["類"] == gp) & (ST["版"] == ver) & (ST["H"] == H) & (ST["對照"] == kind)]
                        if not len(s):
                            continue
                        s = s.iloc[0]
                        if sc != "照實" and ver == "乙":
                            continue
                        md.append(f"| {sc} | {gp} | {ver} | {HL[H]} | {kind} | {s['n']}（{int(s['季群數'])}） | {f2(s['訊號中位'])} | {f2(s['對照中位'])} | "
                                  f"**{f2(s['差中位'])}**［{f2(s['差中位_lo'])}～{f2(s['差中位_hi'])}］ | {pc(s['勝過比例'])}［{pc(s['勝過_lo'])}～{pc(s['勝過_hi'])}］ | {f2(s['差平均'])} |")
    md += ["", "（嚴格、剔自評知道只列甲版。）", "", "## 2. 依燈 1 年份（照實；訊號等權）", "",
           "| 類 | 版 | 段 | 年 | n（未到） | 超額中位 | 超額平均 | 股票 R 中位 | 股票 R 平均 | 大盤中位 | 大盤平均 |", "|" + "---|" * 11]
    for gp in groups:
        for ver in ("甲", "乙"):
            for H in HS:
                for y in ("2021", "2022", "2023", "2024"):
                    s = ST[(ST["表"] == "年份") & (ST["類"] == gp) & (ST["版"] == ver) & (ST["H"] == H) & (ST["年"] == y)].iloc[0]
                    if s["n"] == 0 and s["未到"] == 0:
                        continue
                    md.append(f"| {gp} | {ver} | {HL[H]} | {y} | {s['n']}（{int(s['未到'])}） | {f2(s['超額中位'])} | {f2(s['超額平均'])} | {f2(s['R中位'])} | {f2(s['R平均'])} | "
                              f"{f2(s['大盤中位'])} | {f2(s['大盤平均'])} |")
    md += ["", "- 股票 R＝還原含息、已扣 0.585% 來回（同主表）；大盤＝market_tri 同期報酬。", "", "## 3. 右尾拆解（照實、套規模下限的訊號；份）", "",
           "| 類 | 版 | 段 | n | 平均 | 去最大 1 名 | 去最大 3 名 | 中位 | 前 5 名 |", "|" + "---|" * 9]
    for gp in groups:
        for ver in ("甲", "乙"):
            for H in HS:
                s = ST[(ST["表"] == "右尾") & (ST["類"] == gp) & (ST["版"] == ver) & (ST["H"] == H)].iloc[0]
                md.append(f"| {gp} | {ver} | {HL[H]} | {s['n']} | {f2(s['平均'])} | {f2(s['去最大1平均'])} | {f2(s['去最大3平均'])} | {f2(s['中位'])} | {s['前5名']} |")
    md += ["", "## 4. 電子類規模剔除（燈 1 季最後一個交易日市值 ＜100 億）", ""]
    ce = CP[(CP["類"] == "電子") & (CP["判定"] == "市值不足、剔除")] if "類" in CP else CP.iloc[0:0]
    whole = set(SG[(SG["類"] == "電子") & ~SG["無點名"].astype(bool) & (SG["檔數"] == 0)]["訊號"])
    md += ["| 訊號 | 整個訊號剔除？ | 代號 名稱 | 燈1季 | 市值（億） |", "|---|---|---|---|---|"]
    for _, r in ce.iterrows():
        md.append(f"| {r['訊號']} | {'是' if r['訊號'] in whole else '否（同訊號另有過下限的檔）'} | {r['名稱']} | {r['燈1季']} | {r['市值(億)']:.0f} |")
    md.append(f"\n- 整個訊號剔除 {len(whole)} 個：{'、'.join(sorted(whole)) or '無'}；剔除檔次 {len(ce)}。")
    md += ["", "## 5. 另一進場：燈 1 出處日期次一交易日開盤（照實；只報中位、≥+2 份比例、最好；右欄為同批訊號的季末進場對照）", "",
           "| 類 | 版 | 段 | n | 中位 | ≥+2 比例 | 最好 | 季末進場 中位 | 季末 ≥+2 | 季末 最好 |", "|" + "---|" * 10]
    for gp in groups:
        for ver in ("甲", "乙"):
            for H in HS:
                s = ST[(ST["表"] == "出處日進場") & (ST["類"] == gp) & (ST["版"] == ver) & (ST["H"] == H)].iloc[0]
                md.append(f"| {gp} | {ver} | {HL[H]} | {s['n']} | {f2(s['中位'])} | {pc(s['≥+2比例'])} | {f2(s['最好'])}（{s['最好訊號']}） | {f2(s['同批季末中位'])} | "
                          f"{pc(s['同批季末≥+2比例'])} | {f2(s['同批季末最好'])} |")
    md += ["", "- 規模下限仍用燈 1 季末市值（照主表）；出處日早於季末者，下限用到進場後的資訊（照寫）。", "",
           "## 6. 命中代理：24 個月內 絕對 2 倍 vs 相對大盤 2 倍（照實）", "",
           "| 類 | 版 | 訊號 n（未滿 24 月） | 訊號任一檔 絕對／相對 | 訊號等權比例 絕對／相對 | 每檔 絕對／相對（檔次） | 同產業隨機母體 絕對／相對 |", "|" + "---|" * 7]
    for gp in groups:
        for ver in ("甲", "乙"):
            s = ST[(ST["表"] == "2倍") & (ST["類"] == gp) & (ST["版"] == ver)].iloc[0]
            md.append(f"| {gp} | {ver} | {s['n']}（{int(s['未滿24月'])}） | {pc(s['訊號任一檔_絕對2倍'])}／{pc(s['訊號任一檔_相對2倍'])} | "
                      f"{pc(s['訊號等權比例_絕對2倍'])}／{pc(s['訊號等權比例_相對2倍'])} | {pc(s['每檔_絕對2倍'])}／{pc(s['每檔_相對2倍'])}（{int(s['檔次'])}） | "
                      f"{pc(s['對照b_絕對2倍'])}／{pc(s['對照b_相對2倍'])} |")
    md += ["", "- 絕對 2 倍＝收盤÷進場開盤 ≥2；相對 2 倍＝(收盤÷進場開盤)÷(大盤÷進場前一日大盤) ≥2；24 月內任一交易日觸及即算；壞根只看之前、下市看到最後有效日；"
           "24 月窗未走完不入分母。多頭期大盤自己漲很多 ⇒ 絕對 2 倍比相對 2 倍容易，差距＝絕對口徑的退化程度。", "",
           *[f"> ⭐ {x}" for x in LC.FINAL]]
    open(os.path.join(out, "summary_extra.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")


if __name__ == "__main__":
    main()
