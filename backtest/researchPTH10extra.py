# -*- coding: utf-8 -*-
"""PTH 10 檔版補件四件（描述；⛔ 不判、不計 N、不改前瞻 seq3 df9aeefe5570816e）——回測線計算子代理（裁定 seq409 §二、seq410 §一§二、seq411 §二，2026-10-21）。
⛔ 只計算：不 commit、不改既有檔；researchPTHpf（build_world、load_events、pf_stats、metrics、yearly、TYPN）、researchPTHn（run_slot、trades_df、df_text、
   NOTE_EARLY）、researchPTH（stock_job）、researchPTH10vsYL（blend_annual、OUT）、researchPTH_freq（SEGS、OUT）、researchAscTri（label、ratio）、
   rerun17（win_metrics、bench_row）⛔ 只 import。結果句必附「看過結果的描述格，不改前瞻規則、不當升格依據」；早年附 researchPTHn.NOTE_EARLY。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTH10extra [--procs 4]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTH10extra_check
輸出 backtest/resultsPTH10extra/：PTH10extra.json、p1_slip.csv、p1_year.csv、p1_lock.csv、p2_year.csv、p2_dd_hold.csv、p2_month.csv、p2_seg.csv、
    p2_quality.csv、p3_roll.csv、p4_gate.csv、cal_<世界>.txt、run.log

讀法（★ 執行者定）：
 X1（seq410 §一）滑價版 ＝ researchPTHn.run_slot(ev, W, 10, True)（每邊 +0.5%、0050 不加）；閘：eq/hv/u/pend/nh ＝ resultsPTHn eq_<世界>.npz N10s_*，
    交易檔全文 ＝ trades_<世界>_N10s；統計列（%.6g）＝ resultsPTHn/PTHn_main.csv N＝10 兩列 ⇒ 直接引用。無滑價版同法對 N10_*。
    每年換手、成本 ＝ researchPTHpf.pf_stats 以日曆年切窗（段首年、段尾年為部分年）。
    漲停鎖死：事件定義（researchPTH_freq P5）「e 開盤鎖漲停 ⇒ 進場剔除、不遞補」⇒ 鎖死股不在候選名單 ⇒ 10 格版實際上【由 PTH 次高者遞補】（不是留空）。
    ★ 計數：每個批次日 e，鎖死股（入選 ∧ 跳月_st＝e開盤鎖漲停 ∧ 當天未持有 ∧ 當天未賣出）中 PTH ＞ 當批實際買進最低 PTH 者 ＝「若買得到會被選、被下一檔遞補」；
    PTH ＝ 當批最低 PTH ⇒「同分、可能」（同分隨機序未定義）；被擠掉檔數 ＝ min(前者, 當批買進數)。分母 ＝ 段內 10 格版買進筆數。
 X2（seq410 §二）逐年 ＝ researchPTHpf.yearly（年末 ÷ 前一年末，段首年用段首）；⇒ 對 resultsPTHpf/by_year.csv S10（%.6g）。
    最大回落區間：段內權益 峰 → 谷 → 回到峰值（未回 ⇒ 段尾仍未回）；回落深度對 rerun17.win_metrics 段回落。
    持股貢獻（峰～谷）：每筆持有部位 起值 ＝ 峰日市值（峰後買進 ⇒ 買進金額）、迄值 ＝ 谷日市值（谷前賣出 ⇒ 入帳 金額×(1＋R−0.585%)）；貢獻 ＝ (迄−起) ÷ 峰日淨值；
    其餘 ＝ 0050＋待買回現金。產業 ＝ origin/main curated/industry_hist/industry_pit.csv（形成月底當日 pit）；市值 ＝ 形成月底原始收盤 × 股數（stocks/<sid>.csv shares，
    只 ffill（不 bfill）；早年上市 shares 2012-05 前空 ⇒ 同日由 ~/earlydata/950ad26e12/main/data/stocks 補）、億元；市值百分位 ＝ 同月排序母體內百分位。
    每月入選（PTH 前 30%）與 10 格版買進：平均／中位市值、市值百分位、產業 HHI（細類；另報電子九類合併為一類的 HHI，因 2007-07 前上市電子只有「電子工業」一類）、
    最大產業占比、電子占比、上櫃占比；依排序日 t 歸段（同頻率表 P6）；10 格版依買進日歸段。切點 PTH、PTH＝1 檔數 ＝ resultsPTH/freq/monthly.csv。
    資料品質：照 researchPTHn.NOTE_EARLY 逐條列，另數早年 10 格版逐年上櫃占比、出場種類、資料尾未出場、上櫃 2007-07～12 持有中的筆數；⛔ 不據此剔除早年。
 X3（seq411 §二）滾動 12 個月 ＝ resultsPTH10vsYL/daily_<世界>.csv.gz 重建（窗 ＝ rolling12 同式：連續 12 個月底；主世界 探索＋確認 全共同窗，窗尾歸段）：
    A ＝ 12 個月報酬差（10 格版 − 營量）＞ 0（＝ rolling12「差>0」，逐列對帳）；
    B ＝「本件＋營量各半」的 12 個月 比值 ＞ 營量單獨 比值；★ 各半 ＝ seq411 收下的各半③口徑（窗首 ½／½、窗內遇每年第一個交易日收盤調回 ½／½、扣搬動×0.585%；
       researchPTH10vsYL.blend_annual 原樣）；★ 比值 ＝ 12 個月累積報酬 ÷ |窗內最大回落|（12 個月窗即一年；rerun17.win_metrics 要 ≥ 245 日、窗長 240～250 日會缺 ⇒ 不用）。
    另一讀法（只報）：年化以 窗日數÷245 年換算；各半① 每日再平衡、各半② 窗首各半不再平衡。回落 ＝ 0 ⇒ 比值缺、記 B 不成立並計數。
 X4（seq409 §二）CGH 原式：訊號月 M 的狀態 ＝ M 前一個完整月底往回 36 個完整月的 0050 含息還原報酬（PREREGH seq2 §一）；＜ 0 ⇒ DOWN（閘關）。
    0050 含息還原：早年世界（~/earlydata/eotc，2004-02-11～2014-12-31）與主世界（快照，2015-01-05 起）各自 load_bench；接點 ＝ 原始收盤 2014-12-31 → 2015-01-05
    （其間無除息，驗）。月底 ＝ 各世界日曆該月最後交易日。
"""
from __future__ import annotations

import argparse
import gzip
import io
import json
import math
import os
import subprocess
import sys
import time
from collections import Counter
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchPTHpf as M                     # noqa: E402  ⛔ 只 import
from backtest import researchPTHn as PN                     # noqa: E402
from backtest import researchPTH as PTH                     # noqa: E402
from backtest import researchPTH10vsYL as VY                # noqa: E402
from backtest import researchPTH_freq as PT                 # noqa: E402
from backtest import researchAscTri as AS                   # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402
from backtest import researchAddOn as RA                    # noqa: E402

OUT = "backtest/resultsPTH10extra"
COST = M.COST
NS = 10
SENT = "看過結果的描述格，不改前瞻規則、不當升格依據"
NOTE_EARLY = PN.NOTE_EARLY
EARLY_TW = os.path.expanduser("~/earlydata/950ad26e12/main/data/stocks")
ELEC = {"電子工業", "電子零組件業", "半導體業", "光電業", "電腦及週邊設備業", "其他電子業", "通信網路業", "資訊服務業", "電子通路業"}
LOCK = "e開盤鎖漲停"
GATE_MONTHS = [f"{y}-{m:02d}" for y, m in [(2017, m) for m in range(3, 13)] + [(2018, 1)]]


def f6(v):
    if isinstance(v, (bool, np.bool_)):
        return str(bool(v))
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    v = float(v)
    return "" if np.isnan(v) else "%.6g" % v


# ═════════════ 產業、市值 ═════════════
def load_industry():
    txt = subprocess.run(["git", "show", "origin/main:curated/industry_hist/industry_pit.csv"], capture_output=True, text=True, check=True).stdout
    p = pd.read_csv(io.StringIO(txt), dtype=str, keep_default_na=False)
    seg = {}
    for s, ind, a, b in zip(p["stock_id"], p["industry"], p["start"], p["end"]):
        seg.setdefault(s, []).append((a or "0000-00-00", b or "9999-99-99", ind))
    for s in seg:
        seg[s].sort()
    sha = subprocess.run(["git", "rev-parse", "origin/main:curated/industry_hist/industry_pit.csv"], capture_output=True, text=True).stdout.strip()

    def f(s, d):
        sg = seg.get(s)
        if not sg:
            return None
        for a, b, ind in sg:
            if a <= d <= b:
                return ind or None
        if d > sg[-1][1]:
            return sg[-1][2] or None
        return None
    return f, sha, len(p)


def load_caps(data, need, fallback=None):
    """need：{sid: [日期字串…]} ⇒ {(sid, 日): (市值元, 原始收盤, 股數, 股數來源)}。"""
    out = {}; src = Counter()
    for s, ds in need.items():
        fp = os.path.join(data, "stocks", f"{s}.csv")
        if not os.path.exists(fp):
            src["無檔"] += len(ds); continue
        df = pd.read_csv(fp, usecols=["date", "close", "shares"], dtype={"date": str})
        sh = pd.to_numeric(df["shares"], errors="coerce")
        tag = "本檔"
        if fallback and sh.isna().any():
            f2 = os.path.join(fallback, f"{s}.csv")
            if os.path.exists(f2):
                d2 = pd.read_csv(f2, usecols=["date", "shares"], dtype={"date": str})
                fb = df["date"].map(dict(zip(d2["date"], pd.to_numeric(d2["shares"], errors="coerce"))))
                if fb.notna().any():
                    sh = sh.where(sh.notna(), fb)
                    tag = "早年上市補檔"
        shf = sh.ffill().to_numpy(float)
        cl = pd.to_numeric(df["close"], errors="coerce").to_numpy(float)
        dd = df["date"].to_numpy()
        for d in ds:
            k = int(np.searchsorted(dd, d, side="right")) - 1
            if k < 0 or not np.isfinite(cl[k]) or not np.isfinite(shf[k]) or shf[k] <= 0:
                src["缺"] += 1; continue
            out[(s, d)] = (cl[k] * shf[k], float(cl[k]), float(shf[k]), tag + ("" if dd[k] == d else "(前一根)"))
            src[tag] += 1
    return out, dict(src)


def set_stats(sids, caps_pct, caps, ind, otc):
    n = len(sids)
    if n == 0:
        return None
    cs = [caps.get(s) for s in sids]
    cv = np.array([c for c in cs if c is not None], float) / 1e8
    pc = np.array([caps_pct[s] for s in sids if s in caps_pct], float)
    inds = [ind.get(s) or "未分類" for s in sids]
    cnt = Counter(inds); p = np.array(list(cnt.values()), float) / n
    ce = Counter("電子(合併)" if i in ELEC else i for i in inds); pe = np.array(list(ce.values()), float) / n
    return {"n": n, "市值平均(億)": float(cv.mean()) if len(cv) else np.nan, "市值中位(億)": float(np.median(cv)) if len(cv) else np.nan,
            "市值百分位平均": float(pc.mean()) if len(pc) else np.nan, "HHI細類": float((p ** 2).sum()), "HHI電子合併": float((pe ** 2).sum()),
            "最大產業占比": float(p.max()), "最大產業": cnt.most_common(1)[0][0], "電子占比": float(np.mean([i in ELEC for i in inds])),
            "上櫃占比": float(np.mean([bool(otc.get(s, False)) for s in sids])), "市值缺": int(n - len(cv))}


# ═════════════ 回落區間與持股貢獻 ═════════════
def dd_episode(eq, x, y):
    e = np.asarray(eq[x:y + 1], float)
    pk = np.maximum.accumulate(e); dd = e / pk - 1.0
    t = int(np.argmin(dd)); p = int(np.argmax(e[:t + 1]))
    rec = next((k for k in range(t, len(e)) if e[k] >= e[p]), None)
    return {"峰": x + p, "谷": x + t, "回到峰": (x + rec) if rec is not None else None, "深度": float(dd[t])}


def dd_hold(W, ev, S, P, T, ind_at, caps):
    CM = W["CM"]; n0 = W["n0"]; eq = S["eq"]
    sl = {q: (t, proc) for t, q, amt, proc in S["sells"]}
    rows = []
    for tb, q, amt in S["buys"]:
        s_ = sl[q][0] if q in sl else n0
        if tb > T or s_ <= P:
            continue
        j = int(S["j"][q]); ep = S["ep"][q]; qi = S["q"][q]
        v0 = amt if tb > P else amt * CM[j, P] / ep
        v1 = sl[q][1] if (q in sl and s_ <= T) else amt * CM[j, T] / ep
        sid = ev["sid"][qi]; fm = ev["form"][qi]
        c = caps.get((sid, fm))
        rows.append({"sid": sid, "名稱": W["names"].get(sid, ""), "形成月底": fm, "PTH": float(ev["pth"][qi]), "買進日": W["dates"][tb],
                     "賣出日": W["dates"][s_] if q in sl else "", "上櫃": bool(W["otc"][j]), "產業": ind_at(sid, fm) or "未分類",
                     "市值(億)": c[0] / 1e8 if c else np.nan, "R用": float(S["g"][q]), "貢獻(占峰日淨值)": float((v1 - v0) / eq[P])})
    return pd.DataFrame(rows)


# ═════════════ 漲停鎖死遞補 ═════════════
def lock_disp(W, ev, S, fev, segp):
    dates = W["dates"]; dpos = {d: i for i, d in enumerate(dates)}
    sl = {q: t for t, q, amt, proc in S["sells"]}
    pos = []
    for tb, q, amt in S["buys"]:
        qi = S["q"][q]
        pos.append((tb, sl.get(q), ev["sid"][qi], float(ev["pth"][qi])))
    sel = fev[fev["入選"]]
    lk = sel[sel["跳月_st"] == LOCK]
    lkd = {}
    for s, e, p in zip(lk["sid"], lk["跳月_進場日"], lk["PTH"]):
        if e in dpos:
            lkd.setdefault(dpos[e], []).append((s, float(p)))
    days = sorted(set(lkd) | {p[0] for p in pos})
    rows = []
    for e in days:
        held = {s for tb, ts, s, p in pos if tb < e and (ts is None or ts > e)}
        sold = {s for tb, ts, s, p in pos if ts == e}
        bought = [(s, p) for tb, ts, s, p in pos if tb == e]
        nopen = NS - len(held)
        L = [(s, p) for s, p in lkd.get(e, []) if s not in held and s not in sold]
        mn = min((p for s, p in bought), default=np.nan)
        ahead = [s for s, p in L if (not bought) or p > mn]
        tie = [s for s, p in L if bought and p == mn]
        rows.append({"批次日": dates[e], "空格(賣後)": nopen, "買進": len(bought), "當批最低PTH": mn, "鎖死入選": len(lkd.get(e, [])),
                     "鎖死且可買": len(L), "鎖死PTH高於當批最低": len(ahead), "鎖死同分": len(tie),
                     "被擠掉(遞補)": min(len(ahead), len(bought)) if nopen > 0 else 0, "滿格": nopen <= 0,
                     "鎖死名單": ";".join(s for s, p in lkd.get(e, []))})
    D_ = pd.DataFrame(rows)
    out = {}
    for sg, (x, y) in segp.items():
        d = D_[(D_["批次日"] >= dates[x]) & (D_["批次日"] <= dates[y])]
        nb = int(sum(1 for tb, *_ in pos if x <= tb <= y))
        selseg = sel[(sel["跳月_進場日"] >= dates[x]) & (sel["跳月_進場日"] <= dates[y])]
        out[sg] = {"10格版買進筆": nb, "被擠掉(遞補)筆": int(d["被擠掉(遞補)"].sum()), "比例(÷買進)": float(d["被擠掉(遞補)"].sum() / nb) if nb else np.nan,
                   "同分可能筆": int(d["鎖死同分"].sum()), "有遞補的批次數": int((d["被擠掉(遞補)"] > 0).sum()), "批次數(有買進)": int((d["買進"] > 0).sum()),
                   "入選(前30%)筆": int(len(selseg)), "入選中開盤鎖死筆": int((selseg["跳月_st"] == LOCK).sum()),
                   "入選中開盤鎖死比例": float((selseg["跳月_st"] == LOCK).mean()) if len(selseg) else np.nan,
                   "買進數≠空格數的批次(sanity)": int(((d["買進"] > 0) & (d["買進"] != d["空格(賣後)"])).sum())}
    return D_, out


# ═════════════ 滾動 12 個月（X3）═════════════
def r_ratio(e, ann=False):
    e = np.asarray(e, float)
    r = e[-1] / e[0] - 1.0
    if ann:
        r = (e[-1] / e[0]) ** (245.0 / len(e)) - 1.0
    m = float((e / np.maximum.accumulate(e) - 1.0).min())
    return (r / abs(m) if m < 0 else np.nan), r, m


def roll12(wn, segp_dates):
    DL = pd.read_csv(os.path.join(VY.OUT, f"daily_{wn}.csv.gz"), float_precision="round_trip", dtype={"日": str})
    RL = pd.read_csv(os.path.join(VY.OUT, "rolling12.csv"), encoding="utf-8-sig", dtype=str, keep_default_na=False)
    RL = RL[RL["世界"] == wn].reset_index(drop=True)
    d = DL["日"].to_numpy(); eP = DL["10檔版淨值"].to_numpy(float); eY = DL["營量淨值"].to_numpy(float)
    yrs = np.array([int(x[:4]) for x in d]); ym = np.array([x[:7] for x in d]); n = len(d)
    me = [0] + [k for k in range(1, n) if k == n - 1 or ym[k + 1] != ym[k]]
    mP = eP[me][1:] / eP[me][:-1] - 1.0; mY = eY[me][1:] / eY[me][:-1] - 1.0
    rows = []; bad = 0
    for k in range(11, len(mP)):
        a_, z = me[k - 11], me[k + 1]
        sP, sY = eP[a_:z + 1], eY[a_:z + 1]
        df = float(np.prod(1 + mP[k - 11:k + 1]) - np.prod(1 + mY[k - 11:k + 1]))
        V3, moved, cst = VY.blend_annual(sP, sY, yrs[a_:z + 1])
        rP = sP[1:] / sP[:-1] - 1.0; rY = sY[1:] / sY[:-1] - 1.0
        V1 = np.r_[1.0, np.cumprod(1.0 + 0.5 * rP + 0.5 * rY)]
        V2 = 0.5 * sP / sP[0] + 0.5 * sY / sY[0]
        q3, r3, m3 = r_ratio(V3); qy, ry, my = r_ratio(sY); qp, rp, mp_ = r_ratio(sP)
        q3a, _, _ = r_ratio(V3, True); qya, _, _ = r_ratio(sY, True)
        q1, _, _ = r_ratio(V1); q2, _, _ = r_ratio(V2)
        sg = next((s for s, (u, v) in segp_dates.items() if u <= d[z] <= v), "")
        A = df > 0
        row = {"世界": wn, "窗首": d[a_], "窗尾": d[z], "歸段(窗尾)": sg, "窗日數": int(z - a_ + 1), "12m報酬差": df, "A_差>0": A,
               "本件12m": rp, "本件回落": mp_, "本件比值": qp, "營量12m": ry, "營量回落": my, "營量比值": qy,
               "各半③12m": r3, "各半③回落": m3, "各半③比值": q3, "各半③窗內調回次數": len(moved), "B_各半③>營量": bool(np.isfinite(q3) and np.isfinite(qy) and q3 > qy),
               "B③_年化245": bool(np.isfinite(q3a) and np.isfinite(qya) and q3a > qya),
               "B①_每日再平衡": bool(np.isfinite(q1) and np.isfinite(qy) and q1 > qy), "B②_不再平衡": bool(np.isfinite(q2) and np.isfinite(qy) and q2 > qy),
               "比值缺(回落=0)": bool(not (np.isfinite(q3) and np.isfinite(qy)))}
        row["A或B"] = bool(A or row["B_各半③>營量"])
        rows.append(row)
        r0 = RL.iloc[k - 11]
        bad += int(not (r0["窗尾月底"] == d[z] and r0["差>0"] == str(A) and r0["12m報酬差(10檔版−營量)"] == "%.6g" % df))
    R = pd.DataFrame(rows)
    return R, {"窗數": int(len(R)), "rolling12列數": int(len(RL)), "A 與 rolling12「差>0」、窗尾、差(%.6g) 不同列數": bad}


def roll_sum(R):
    if not len(R):
        return {}
    return {"窗數": int(len(R)), "A通過率": float(R["A_差>0"].mean()), "B通過率(各半③)": float(R["B_各半③>營量"].mean()),
            "A或B通過率": float(R["A或B"].mean()), "A且B": float((R["A_差>0"] & R["B_各半③>營量"]).mean()),
            "B只靠B(非A)": float((~R["A_差>0"] & R["B_各半③>營量"]).mean()),
            "另讀_B③年化245": float(R["B③_年化245"].mean()), "另讀_B①每日再平衡": float(R["B①_每日再平衡"].mean()),
            "另讀_B②不再平衡": float(R["B②_不再平衡"].mean()), "另讀_A或B①": float((R["A_差>0"] | R["B①_每日再平衡"]).mean()),
            "另讀_A或B②": float((R["A_差>0"] | R["B②_不再平衡"]).mean()), "比值缺窗數": int(R["比值缺(回落=0)"].sum())}


# ═════════════ 0050 36 個月（X4）═════════════
def month_last(cal):
    ym = np.asarray(cal.year * 100 + cal.month)
    return {f"{v // 100}-{v % 100:02d}": int(k) for k, v in enumerate(ym) if k == len(ym) - 1 or ym[k + 1] != v}


def gate36(WE, WM):
    calE, calM = WE["cal"], WM["cal"]; aE, aM = np.asarray(WE["bench"], float), np.asarray(WM["bench"], float)
    rawE = pd.read_csv(os.path.join(WE["data"], "stocks", "0050.csv"), dtype={"date": str}).set_index("date")["close"].astype(float)
    rawM = pd.read_csv(os.path.join(WM["data"], "stocks", "0050.csv"), dtype={"date": str}).set_index("date")["close"].astype(float)
    adjM = pd.read_csv(os.path.join(WM["data"], "adj", "0050.csv"), dtype=str)
    adjE = pd.read_csv(os.path.join(WE["data"], "adj", "0050.csv"), dtype=str)
    dE, dM = str(calE[-1].date()), str(calM[0].date())
    between = [d for d in list(adjE["date"]) + list(adjM["date"]) if dE < d <= dM]
    if between:
        raise SystemExit(f"⛔ 接點 {dE}→{dM} 之間有除息 {between}")
    link = float(rawM[dM] / rawE[dE])
    mlE, mlM = month_last(calE), month_last(calM)

    def tr(ym):
        if ym in mlE and ym <= "2014-12":
            k = mlE[ym]; return aE[k] / aE[len(calE) - 1], str(calE[k].date()), "早年"
        k = mlM[ym]; return link * aM[k] / aM[0], str(calM[k].date()), "主"

    def shift(ym, k):
        y, m = int(ym[:4]), int(ym[5:])
        z = y * 12 + m - 1 + k
        return f"{z // 12}-{z % 12 + 1:02d}"
    rows = []
    for M_ in GATE_MONTHS:
        e_ym, s_ym = shift(M_, -1), shift(M_, -37)
        te, de, we = tr(e_ym); ts, ds, ws = tr(s_ym)
        r = te / ts - 1.0
        rows.append({"訊號月": M_, "回看起(月底)": ds, "回看迄(月底)": de, "起_世界": ws, "迄_世界": we, "36個月含息報酬": r, "<0(閘關)": bool(r < 0),
                     "狀態": "DOWN" if r < 0 else "UP"})
    return pd.DataFrame(rows), {"接點": f"{dE}→{dM}", "原始收盤": [float(rawE[dE]), float(rawM[dM])], "接點報酬": link - 1.0, "其間除息": "無"}


# ═════════════ 主程式 ═════════════
def run(a, log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    J = {"題": "PTH 10 檔版補件四件（seq410 §一§二、seq411 §二、seq409 §二）", "身分": "描述（⛔ 不判、不計 N、不改前瞻 seq3）", "結果句必附": SENT,
         "早年註": NOTE_EARLY, "開跑": M.now_tpe(), "對帳": {}, "X1": {}, "X2": {}, "X3": {}, "X4": {}}
    ind_at, ind_sha, ind_n = load_industry()
    J["產業來源"] = {"檔": "origin/main:curated/industry_hist/industry_pit.csv", "blob": ind_sha, "列": ind_n}
    PJN = pd.read_csv(os.path.join(PN.OUT, "PTHn_main.csv"), encoding="utf-8-sig", dtype=str, keep_default_na=False)
    BYR = pd.read_csv(os.path.join(M.OUT, "by_year.csv"), encoding="utf-8-sig", dtype=str, keep_default_na=False)
    MON = pd.read_csv(os.path.join(PT.OUT, "monthly.csv"), encoding="utf-8-sig", dtype={"形成月底": str})
    P1, P1Y, P1L, P2Y, P2H, P2M, P2S, P2Q = [], [], [], [], [], [], [], []
    WK = {}
    for wn in ("主", "早年"):
        W = M.build_world(wn, log)
        t0 = time.time(); RES = {}
        with Pool(a.procs) as pool:
            for sid, r in pool.imap_unordered(PTH.stock_job, [(wn, s) for s in W["sids"]], chunksize=8):
                if r is not None:
                    RES[sid] = r
        log(f"[{wn}] 逐股完 {len(RES)} 檔｜{time.time() - t0:.0f}s")
        ev, info = M.load_events(W, wn, "跳月", RES)
        del RES
        cal = W["cal"]; dates = W["dates"]; segp = W["segp"]
        with open(os.path.join(OUT, f"cal_{wn}.txt"), "w") as fh:
            fh.write("\n".join(dates) + "\n")
        J["段"] = J.get("段", {}); J["段"][wn] = {sg: [int(x), int(y), dates[x], dates[y]] for sg, (x, y) in segp.items()}
        # ── X1：滑價版（對帳 resultsPTHn）
        Z = np.load(os.path.join(PN.OUT, f"eq_{wn}.npz"))
        SIM = {False: PN.run_slot(ev, W, NS, False), True: PN.run_slot(ev, W, NS, True)}
        for sl, S in SIM.items():
            tag = "N10s" if sl else "N10"
            for k in ("eq", "hv", "u", "pend", "nh"):
                if not np.array_equal(S[k], Z[f"{tag}_{k}"]):
                    raise SystemExit(f"⛔ {wn} {tag} {k} ≠ resultsPTHn")
            with gzip.open(os.path.join(PN.OUT, f"trades_{wn}_{tag}.csv.gz"), "rt", encoding="utf-8") as fh:
                if PN.df_text(PN.trades_df(W, ev, S), "%.17g") != fh.read():
                    raise SystemExit(f"⛔ {wn} {tag} 交易檔 ≠ resultsPTHn")
            J["對帳"][f"{wn}|{tag} eq/hv/u/pend/nh ＝ resultsPTHn（逐位元）、交易檔全文（逐字）"] = f"相同（{len(S['buys'])} 筆）"
        same_buys = [(t, int(S_q)) for t, S_q, _ in SIM[False]["buys"]] == [(t, int(S_q)) for t, S_q, _ in SIM[True]["buys"]]
        J["對帳"][f"{wn}|滑價版與無滑價版買進（日、筆）相同"] = bool(same_buys)
        bench = {sg: RR.bench_row(cal, W["bench"], x, y + 1) for sg, (x, y) in segp.items()}
        for sl, S in SIM.items():
            typ_q = ev["typ"][S["q"]]
            for sg, (x, y) in segp.items():
                c_, m_, b = M.metrics(W, S["eq"], x, y)
                row = {"世界": wn, "N": 10, "滑價": sl, "段": sg, "窗": f"{cal[x].date()}～{cal[y].date()}", "年化": c_, "回落": m_, "比值": AS.ratio(c_, m_),
                       "0050年化": b["cagr"], "0050回落": b["mdd"], "0050比值": AS.ratio(b["cagr"], b["mdd"]), "標籤": AS.label(c_, m_, b),
                       **M.pf_stats(W, S, x, y, typ_q)}
                ref = PJN[(PJN["世界"] == wn) & (PJN["N"] == "10") & (PJN["滑價"] == str(sl)) & (PJN["段"] == sg)].iloc[0]
                bad = [k for k in row if k in ref.index and k not in ("世界", "N", "滑價", "段", "窗", "標籤") and f6(row[k]) != ref[k]]
                if bad or row["標籤"] != ref["標籤"] or row["窗"] != ref["窗"]:
                    raise SystemExit(f"⛔ {wn}/{sg}/滑價{sl} 統計 ≠ PTHn_main：{bad}")
                J["對帳"][f"{wn}|N10{'s' if sl else ''} {sg} 統計列 ＝ PTHn_main.csv（%.6g，{sum(1 for k in row if k in ref.index)} 欄）"] = "逐字相同"
                P1.append(row)
                # 每年換手、成本
                yrs = np.asarray(cal.year)
                for Y_ in sorted(set(yrs[x:y + 1].tolist())):
                    ii = np.flatnonzero((yrs == Y_) & (np.arange(len(yrs)) >= x) & (np.arange(len(yrs)) <= y))
                    xa, ya = int(ii[0]), int(ii[-1])
                    st = M.pf_stats(W, S, xa, ya, typ_q)
                    P1Y.append({"世界": wn, "滑價": sl, "段": sg, "年": int(Y_), "起": dates[xa], "迄": dates[ya], "交易日": int(ya - xa + 1),
                                **{k: st[k] for k in ("買進筆", "換手每年", "成本每年(換手×0.585%)", "個股成本每年(實付)", "0050成本每年(實付)", "成本合計每年(實付)",
                                                      "平均持股(筆)", "0050占淨值")}})
        # 漲停鎖死
        fev = pd.read_csv(os.path.join(PT.OUT, f"events_{wn}.csv.gz"), dtype={"sid": str, "形成月底": str, "跳月_進場日": str})
        LD, lo = lock_disp(W, ev, SIM[False], fev, segp)
        LD.insert(0, "世界", wn); P1L.append(LD)
        J["X1"][f"{wn}|漲停鎖死"] = lo
        log(f"[X1 {wn} 鎖死] {json.dumps(lo, ensure_ascii=False, default=float)}")
        # ── X2：逐年（對 resultsPTHpf/by_year S10）
        S0 = SIM[False]; S1 = SIM[True]
        for sg, (x, y) in segp.items():
            y0 = M.yearly(S0["eq"], W["Bc"], cal, x, y); y1 = M.yearly(S1["eq"], W["Bc"], cal, x, y)
            nb = 0
            for Y_, v in y0.items():
                ref = BYR[(BYR["世界"] == wn) & (BYR["臂"] == "S10") & (BYR["段"] == sg) & (BYR["年"] == Y_)].iloc[0]
                nb += int(not (f6(v["本件"]) == ref["本件"] and f6(v["0050"]) == ref["0050"] and v["起"] == ref["起"] and v["訖"] == ref["訖"]))
                bys = [(t, q) for t, q, _ in S0["buys"] if v["起"] < dates[t] <= v["訖"] or (dates[t] == v["起"] and v["起"] == dates[x])]
                qq = [S0["q"][q] for t, q in bys]
                P2Y.append({"世界": wn, "段": sg, "年": int(Y_), "起": v["起"], "訖": v["訖"], "10格版": v["本件"], "10格版滑價": y1[Y_]["本件"], "0050": v["0050"],
                            "差(10格−0050)": v["本件"] - v["0050"], "買進筆": len(bys),
                            "買進上櫃占比": float(np.mean([bool(W["otc"][ev["j"][q]]) for q in qq])) if qq else np.nan,
                            "買進電子占比": float(np.mean([(ind_at(ev["sid"][q], ev["form"][q]) in ELEC) for q in qq])) if qq else np.nan})
            if nb:
                raise SystemExit(f"⛔ {wn}/{sg} 逐年 ≠ resultsPTHpf/by_year S10（{nb} 年）")
            J["對帳"][f"{wn}|{sg} 逐年（10格版、0050）＝ resultsPTHpf/by_year.csv S10（%.6g）"] = f"逐字相同（{len(y0)} 年）"
        # 市值、產業（入選與 10 格版買進）
        segt = {sg: (u, v or "9999-12-31") for sg, (u, v) in PT.SEGS[wn].items() if sg != "主全窗"}
        fs = fev[fev["形成月底"].between(min(u for u, v in segt.values()), max(v for u, v in segt.values()))]
        need = {}
        for s, t in zip(fs["sid"], fs["形成月底"]):
            need.setdefault(s, []).append(t)
        for s in need:
            need[s] = sorted(set(need[s]))
        caps, csrc = load_caps(W["data"], need, EARLY_TW if wn == "早年" else None)
        J["X2"][f"{wn}|市值來源計數"] = csrc
        fs = fs.assign(cap=[caps[(s, t)][0] if (s, t) in caps else np.nan for s, t in zip(fs["sid"], fs["形成月底"])])
        fs["cap_pct"] = fs.groupby("形成月底")["cap"].rank(pct=True)
        otc = {s: bool(W["otc"][W["ix"][s]]) for s in W["sids"]}
        buysT = {}
        for t, q, _ in S0["buys"]:
            qi = S0["q"][q]; buysT.setdefault(ev["form"][qi], []).append(ev["sid"][qi])
        for t, g in fs.groupby("形成月底"):
            sg = next((s for s, (u, v) in segt.items() if u <= t <= v), "")
            capd = dict(zip(g["sid"], g["cap"])); pctd = {s: p for s, p in zip(g["sid"], g["cap_pct"]) if np.isfinite(p)}
            capd = {s: c for s, c in capd.items() if np.isfinite(c)}
            ind = {s: ind_at(s, t) for s in g["sid"]}
            s_sel = g.loc[g["入選"], "sid"].tolist()
            st = set_stats(s_sel, pctd, capd, ind, otc)
            mr = MON[(MON["世界"] == wn) & (MON["形成月底"] == t)]
            P2M.append({"世界": wn, "段": sg, "形成月底": t, "組": "入選(前30%)", **st, "排序母體": int(len(g)),
                        "切點PTH": float(mr["切點PTH"].iloc[0]) if len(mr) else np.nan, "PTH=1檔數": int(mr["PTH=1檔數"].iloc[0]) if len(mr) else -1,
                        "排序母體市值中位(億)": float(np.nanmedian(g["cap"])) / 1e8})
            bl = buysT.get(t, [])
            if bl:
                for s in bl:
                    if s not in ind:
                        ind[s] = ind_at(s, t)
                stb = set_stats(bl, pctd, capd, ind, otc)
                P2M.append({"世界": wn, "段": sg, "形成月底": t, "組": "10格版買進", **stb, "排序母體": int(len(g)),
                            "PTH平均": float(np.mean([float(g.loc[g["sid"] == s, "PTH"].iloc[0]) for s in bl if (g["sid"] == s).any()]))})
        # 回落區間與持股
        for sg, (x, y) in segp.items():
            epi = dd_episode(S0["eq"], x, y); be = dd_episode(W["Bc"], x, y)
            c_, m_, _ = M.metrics(W, S0["eq"], x, y)
            P_, T_ = epi["峰"], epi["谷"]
            H = dd_hold(W, ev, S0, P_, T_, ind_at, caps)
            H.insert(0, "段", sg); H.insert(0, "世界", wn); P2H.append(H)
            tot = float(S0["eq"][T_] / S0["eq"][P_] - 1.0)
            o = {"峰": dates[P_], "谷": dates[T_], "回到峰": dates[epi["回到峰"]] if epi["回到峰"] is not None else "段內未回", "深度": epi["深度"],
                 "win_metrics回落": m_, "深度與win_metrics差": abs(epi["深度"] - m_), "峰谷交易日": int(T_ - P_),
                 "0050同窗報酬": float(W["Bc"][T_] / W["Bc"][P_] - 1.0), "0050自身最大回落": {"峰": dates[be["峰"]], "谷": dates[be["谷"]], "深度": be["深度"]},
                 "峰日持股筆": int(S0["nh"][P_]), "谷日持股筆": int(S0["nh"][T_]), "峰谷間買進筆": int(sum(1 for t, *_ in S0["buys"] if P_ < t <= T_)),
                 "持股合計貢獻": float(H["貢獻(占峰日淨值)"].sum()) if len(H) else 0.0, "0050與現金貢獻(差額)": tot - (float(H["貢獻(占峰日淨值)"].sum()) if len(H) else 0.0),
                 "峰谷間平均0050占淨值": float(np.mean(S0["u"][P_:T_ + 1] / S0["eq"][P_:T_ + 1])),
                 "持股產業貢獻": H.groupby("產業")["貢獻(占峰日淨值)"].sum().sort_values().to_dict() if len(H) else {},
                 "持股筆數依產業": H["產業"].value_counts().to_dict() if len(H) else {},
                 "持股電子占比(筆)": float(H["產業"].isin(ELEC).mean()) if len(H) else np.nan, "持股上櫃占比(筆)": float(H["上櫃"].mean()) if len(H) else np.nan,
                 "持股市值中位(億)": float(H["市值(億)"].median()) if len(H) else np.nan}
            J["X2"][f"{wn}|{sg}|最大回落"] = o
            log(f"[X2 {wn}/{sg} 回落] {json.dumps({k: v for k, v in o.items() if not isinstance(v, dict)}, ensure_ascii=False, default=float)}")
        # 資料品質（早年）
        if wn == "早年":
            x, y = segp["早年"]
            sl_ = {q: t for t, q, amt, proc in S0["sells"]}
            q_rows = []
            for t, q, amt in S0["buys"]:
                if not (x <= t <= y):
                    continue
                qi = S0["q"][q]; j = int(ev["j"][qi]); ts = sl_.get(q)
                endd = dates[ts] if ts is not None else "9999"
                q_rows.append({"年": int(cal[t].year), "上櫃": bool(W["otc"][j]), "出場種類": M.TYPN[int(ev["typ"][qi])],
                               "上櫃且持有跨2007-07～12": bool(W["otc"][j] and dates[t] <= "2007-12-31" and endd >= "2007-07-01"),
                               "R用": float(S0["g"][q]), "sid": ev["sid"][qi], "買進日": dates[t]})
            QD = pd.DataFrame(q_rows)
            for Y_, g in QD.groupby("年"):
                P2Q.append({"年": int(Y_), "買進筆": int(len(g)), "上櫃筆": int(g["上櫃"].sum()), "上櫃占比": float(g["上櫃"].mean()),
                            **{f"出場_{k}": int((g["出場種類"] == k).sum()) for k in M.TYPN.values()},
                            "上櫃且持有跨2007-07～12": int(g["上櫃且持有跨2007-07～12"].sum()), "R用>100%筆": int((g["R用"] > 1.0).sum())})
            J["X2"]["早年|資料品質"] = {"早年註(照列)": NOTE_EARLY, "買進筆": int(len(QD)), "上櫃筆": int(QD["上櫃"].sum()),
                                     "2007-07前買進筆(只有上市)": int((QD["買進日"] < "2007-07-01").sum()),
                                     "出場種類": QD["出場種類"].value_counts().to_dict(), "上櫃且持有跨2007-07～12(除權息未還原期)": int(QD["上櫃且持有跨2007-07～12"].sum()),
                                     "R用>100%": QD.loc[QD["R用"] > 1.0, ["sid", "買進日", "R用"]].to_dict("records"),
                                     "⛔": "照實列，不據此剔除早年"}
        WK[wn] = {"cal": cal, "bench": W["bench"], "data": W["data"]}
        # ── X3 對帳：daily 檔 10 檔版淨值 ＝ 本支重跑 eq（逐位元）
        DL = pd.read_csv(os.path.join(VY.OUT, f"daily_{wn}.csv.gz"), float_precision="round_trip", dtype={"日": str})
        dpos = {d: i for i, d in enumerate(dates)}
        tp = np.array([dpos[d] for d in DL["日"]], np.int64)
        J["對帳"][f"{wn}|resultsPTH10vsYL daily「10檔版淨值」＝ 本支重跑 eq（逐位元，{len(tp)} 日）"] = bool(np.array_equal(DL["10檔版淨值"].to_numpy(float), S0["eq"][tp]))
        if not J["對帳"][f"{wn}|resultsPTH10vsYL daily「10檔版淨值」＝ 本支重跑 eq（逐位元，{len(tp)} 日）"]:
            raise SystemExit(f"⛔ {wn} daily 10檔版淨值 ≠ 重跑 eq")
        segd = {sg: (dates[x], dates[y]) for sg, (x, y) in segp.items()}
        R3, chk = roll12(wn, segd)
        J["對帳"][f"{wn}|X3 A 對 rolling12"] = chk
        if chk["A 與 rolling12「差>0」、窗尾、差(%.6g) 不同列數"] or chk["窗數"] != chk["rolling12列數"]:
            raise SystemExit(f"⛔ {wn} X3 A ≠ rolling12 {chk}")
        J["X3"][wn] = {"全部窗": roll_sum(R3), **{f"窗尾在{sg}": roll_sum(R3[R3["歸段(窗尾)"] == sg]) for sg in segd}}
        J["X3"].setdefault("_rows", []).append(R3)
        log(f"[X3 {wn}] {json.dumps(J['X3'][wn], ensure_ascii=False, default=float)}")
        del W, ev, SIM, S0, S1, Z
        M._G.pop(wn, None); PT._G.pop(wn, None)
    # ── X4
    G4, link = gate36(WK["早年"], WK["主"])
    J["X4"] = {"接點": link, "列": G4.to_dict("records"), "觸發(DOWN)月數": int(G4["<0(閘關)"].sum()), "月數": int(len(G4))}
    log(f"[X4] {json.dumps(J['X4'], ensure_ascii=False, default=float)}")
    # ── 段級彙總（X2 每月 ⇒ 段平均）
    MD = pd.DataFrame(P2M)
    for (wn, sg, grp), g in MD.groupby(["世界", "段", "組"]):
        o = {"世界": wn, "段": sg, "組": grp, "月數": int(len(g)), "每月檔數平均": float(g["n"].mean()),
             **{k: float(g[k].mean()) for k in ("市值平均(億)", "市值中位(億)", "市值百分位平均", "HHI細類", "HHI電子合併", "最大產業占比", "電子占比", "上櫃占比")}}
        if grp == "入選(前30%)":
            o.update({"排序母體平均": float(g["排序母體"].mean()), "排序母體市值中位(億)平均": float(g["排序母體市值中位(億)"].mean()),
                      "切點PTH中位": float(g["切點PTH"].median()), "切點PTH_p10": float(g["切點PTH"].quantile(.1)), "切點PTH_p90": float(g["切點PTH"].quantile(.9)),
                      "PTH=1檔數平均": float(g["PTH=1檔數"].mean()), "PTH=1≥10檔的月比例": float((g["PTH=1檔數"] >= 10).mean()),
                      "最大產業(月次最多)": g["最大產業"].value_counts().index[0]})
        else:
            o.update({"買進PTH平均": float(g["PTH平均"].mean())})
        P2S.append(o)
    # 早年再分 2005-01～2007-06（只有上市）與 2007-07～2014
    for grp in ("入選(前30%)", "10格版買進"):
        g = MD[(MD["世界"] == "早年") & (MD["組"] == grp)]
        for nm, msk in (("早年_2005-01～2007-06(只有上市)", g["形成月底"] < "2007-07-01"), ("早年_2007-07～2014", g["形成月底"] >= "2007-07-01")):
            h = g[msk]
            P2S.append({"世界": "早年", "段": nm, "組": grp, "月數": int(len(h)), "每月檔數平均": float(h["n"].mean()),
                        **{k: float(h[k].mean()) for k in ("市值平均(億)", "市值中位(億)", "市值百分位平均", "HHI細類", "HHI電子合併", "最大產業占比", "電子占比", "上櫃占比")},
                        **({"切點PTH中位": float(h["切點PTH"].median()), "PTH=1檔數平均": float(h["PTH=1檔數"].mean()), "排序母體平均": float(h["排序母體"].mean())}
                           if grp == "入選(前30%)" else {})})
    J["X2"]["段級"] = P2S
    J["X1"]["統計列"] = P1
    # ── 存檔
    R3all = pd.concat(J["X3"].pop("_rows"), ignore_index=True)
    pd.DataFrame(P1).to_csv(os.path.join(OUT, "p1_slip.csv"), index=False, float_format="%.6g", encoding="utf-8-sig")
    pd.DataFrame(P1Y).to_csv(os.path.join(OUT, "p1_year.csv"), index=False, float_format="%.6g", encoding="utf-8-sig")
    pd.concat(P1L, ignore_index=True).to_csv(os.path.join(OUT, "p1_lock.csv"), index=False, float_format="%.10g", encoding="utf-8-sig")
    pd.DataFrame(P2Y).to_csv(os.path.join(OUT, "p2_year.csv"), index=False, float_format="%.6g", encoding="utf-8-sig")
    pd.concat(P2H, ignore_index=True).to_csv(os.path.join(OUT, "p2_dd_hold.csv"), index=False, float_format="%.6g", encoding="utf-8-sig")
    MD.to_csv(os.path.join(OUT, "p2_month.csv"), index=False, float_format="%.6g", encoding="utf-8-sig")
    pd.DataFrame(P2S).to_csv(os.path.join(OUT, "p2_seg.csv"), index=False, float_format="%.6g", encoding="utf-8-sig")
    pd.DataFrame(P2Q).to_csv(os.path.join(OUT, "p2_quality.csv"), index=False, float_format="%.6g", encoding="utf-8-sig")
    R3all.to_csv(os.path.join(OUT, "p3_roll.csv"), index=False, float_format="%.10g", encoding="utf-8-sig")
    G4.to_csv(os.path.join(OUT, "p4_gate.csv"), index=False, float_format="%.10g", encoding="utf-8-sig")
    J["耗時秒"] = round(time.time() - T0); J["完成"] = M.now_tpe()
    json.dump(J, open(os.path.join(OUT, "PTH10extra.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 60)
    log("[X1 表]\n" + pd.DataFrame(P1)[["世界", "滑價", "段", "年化", "回落", "比值", "0050年化", "0050回落", "0050比值", "標籤", "換手每年", "成本合計每年(實付)"]].to_string())
    log("[X1 每年]\n" + pd.DataFrame(P1Y).to_string())
    log("[X2 逐年]\n" + pd.DataFrame(P2Y).to_string())
    log("[X2 段級]\n" + pd.DataFrame(P2S).T.to_string())
    log("[X2 品質]\n" + pd.DataFrame(P2Q).to_string())
    log("[X4]\n" + G4.to_string())
    log(f"[對帳] {json.dumps(J['對帳'], ensure_ascii=False, default=float)}")
    log(f"[完] {J['耗時秒']}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    run(a, RA.log_to(os.path.join(OUT, "run.log")))


if __name__ == "__main__":
    main()
