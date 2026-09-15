"""研究十五：纏論第三類買點（單層日 K 簡化版）。判準 backtest/PREREG15.md（K線分析 v2 登錄、回測線落地版）。

    python3 -m backtest.research15 [--procs 4] [--reps 200] [--limit N] [--out DIR]

偵測 ＝ chan.detect；出場／CI／組合層 import research11（同一件事只有一份實作）。
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import chan as C
from . import data as D
from . import research11 as R

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results15")
COST = R.COST
SIG_START = pd.Timestamp("2016-01-04")
SPLIT = "2021-01"
HOLDS = (20, 60, 120)
LIQ = 5e7
SHIFT = 7                      # 安慰劑 A：進場平移 +7 個交易日
SEED_B = 20260913
EXCL_IND = {"17", "22"}        # 金融保險、生技醫療
VARIANTS = {"main": dict(pen_mode="new", zg_mode=2, n_pens=5, start=None),
            "A_2016": dict(pen_mode="new", zg_mode=2, n_pens=5, start="2016"),
            "B_old": dict(pen_mode="old", zg_mode=2, n_pens=5, start=None),
            "C_zg3": dict(pen_mode="new", zg_mode=3, n_pens=5, start=None),
            "D_3pens": dict(pen_mode="new", zg_mode=2, n_pens=3, start=None)}
_G: dict = {}


def _init(cal, disp, att, marg):
    R._init(cal); _G.update(cal=cal, disp=disp, att=att, marg=marg)


MARGIN_O_REPORT: dict = {}   # load_margin_o 最近一次的缺欄／讀不到清單（給呼叫端與 runlog 用）


def load_margin_o() -> dict[str, set]:
    """停止融資（官方註記 O）日期，鍵＝代號。⚠ X 是停券期（每年例行），不當閘門。"""
    # ⚠ 缺欄不可以靜靜跳過（市場情報分析 09-14 0546 §四：「跳過」跟「沒有 O」在結果上同形）
    #   ⇒ 缺 note 欄的檔要記下來並印出來；呼叫端看得到「這道閘門在哪些檔上是空轉的」。
    out = {}
    files = [f for f in glob.glob(os.path.join(D.DATA, "stocks_margin", "*.csv")) if not os.path.basename(f).startswith("_")]  # _index.csv 不是個股
    no_col, bad = [], []
    for f in files:
        sid = os.path.basename(f)[:-4]
        try:
            head = pd.read_csv(f, nrows=0).columns
        except Exception:
            bad.append(sid); continue
        if "note" not in head or "date" not in head:
            no_col.append(sid); continue
        try:
            d = pd.read_csv(f, usecols=["date", "note"], dtype=str)
        except Exception:
            bad.append(sid); continue
        m = d["note"].fillna("").str.contains("O")
        if m.any():
            out[sid] = set(pd.to_datetime(d.loc[m, "date"]))
    MARGIN_O_REPORT.update({"files": len(files), "with_O": len(out), "no_note_col": sorted(no_col), "unreadable": sorted(bad)})
    print(f"[margin O] 讀 {len(files)} 檔｜有 O 的 {len(out)} 檔｜⛔ 缺 note 欄 {len(no_col)} 檔"
          f"{'（' + ', '.join(no_col[:8]) + ('…' if len(no_col) > 8 else '') + '）' if no_col else ''}"
          f"｜讀不到 {len(bad)} 檔{'（' + ', '.join(bad[:8]) + '）' if bad else ''}", flush=True)
    return out



def worker(args):
    sid, market = args
    cal, disp, att, marg = _G["cal"], _G["disp"], _G["att"], _G["marg"]
    B = R.load_bars(sid, market, cal)
    if B is None:
        return None
    idx, dates, o, c, h, l, amt, next_bad, ev_bar = (B[k] for k in ("idx", "dates", "o", "c", "h", "l", "amt", "next_bad", "ev_bar"))
    n = len(idx)
    liq20 = pd.Series(amt).shift(1).rolling(20, min_periods=20).mean().to_numpy(float)
    liq_ok = liq20 >= LIQ
    dmask = D.disposal_mask(sid, cal, disp)[idx]
    a_dates = att.get(sid, set()); m_dates = marg.get(sid, set())
    gate_ok = ~dmask & np.array([d not in a_dates and d not in m_dates for d in dates])
    valid_sig = (dates >= SIG_START) & (np.arange(n) + 1 < n) & np.isfinite(o[np.minimum(np.arange(n) + 1, n - 1)]) & (o[np.minimum(np.arange(n) + 1, n - 1)] > 0)
    has_adj = bool(ev_bar.any()) or (D.load_adj(sid) is not None and len(D.load_adj(sid)) > 0)
    month = dates.strftime("%Y-%m")
    out = {"sid": sid, "rows": [], "base": {}, "elig": None}

    def exits(k, row, suffix=""):
        nb = next_bad[k + 1]                                     # 只查 [進場根, 出場根]
        for H in HOLDS:
            r = R.fixed_exit(o, c, k, H, nb)
            row[f"g_H{H}{suffix}"] = r[1] if r else np.nan
            if not suffix:
                row[f"x_H{H}"] = int(idx[r[0]]) if r else -1
                row[f"div_H{H}"] = bool(ev_bar[k + 1:k + H + 1].any()) if k + H < n else None
        if not suffix:
            atr = R.wilder_atr(h, l, c)
            for name, kx in (("A2", 2.0), ("A3", 3.0)):
                st_ = {"hi": -np.inf, "stop": -np.inf}
                def cond(j, st_=st_, kx=kx):
                    if c[j] > st_["hi"]:
                        st_["hi"] = c[j]
                        if not np.isnan(atr[j]):
                            st_["stop"] = max(st_["stop"], st_["hi"] - kx * atr[j])
                    return c[j] < st_["stop"]
                r = R.cond_exit(o, c, k, nb, cond) if not np.isnan(atr[k]) else None
                row[f"g_{name}"], row[f"x_{name}"], row[f"bars_{name}"] = (r[1], int(idx[r[0]]), r[0] - k) if r else (np.nan, -1, np.nan)

    for vname, vp in VARIANTS.items():
        start = 0 if vp["start"] is None else int(np.searchsorted(dates, SIG_START))
        try:
            centers, sigs = C.detect(h, l, c, pen_mode=vp["pen_mode"], zg_mode=vp["zg_mode"], n_pens=vp["n_pens"], start=start)
        except Exception as e:      # 一檔炸掉不拖全部，但要記
            out["rows"].append({"sid": sid, "variant": vname, "kind": "ERROR", "err": repr(e)}); continue
        for sg in sigs:
            k = int(sg["signal_raw"])
            if k < 1 or not valid_sig[k]:
                continue
            row = {"sid": sid, "variant": vname, "kind": sg["kind"], "k": k, "pos": int(idx[k]), "entry_pos": int(idx[k + 1]), "month": month[k],
                   "liq_ok": bool(liq_ok[k]), "gate_ok": bool(gate_ok[k]), "has_adj": has_adj, "zg": sg["zg"], "zd": sg["zd"], "center": sg["center"]}
            exits(k, row)
            if vname == "main" and sg["kind"] == "B3":
                # 安慰劑 A：訊號日平移 +7 個交易日，映到次一有效 K 棒
                k7 = int(np.searchsorted(idx, idx[k] + SHIFT))
                if k7 + 1 < n:
                    exits(k7, row, "_pA")
            out["rows"].append(row)
    # 母體基準（主格閘門兩版）＋ 安慰劑 B 的抽樣池（通過全套閘門＋流動性的有效 K 棒）
    if True:
        ks = np.flatnonzero(valid_sig & gate_ok)
        rec = []
        for k in ks:
            nb = next_bad[k + 1]
            g = [R.fixed_exit(o, c, k, H, nb) for H in HOLDS]
            rec.append((k, liq_ok[k], *[x[1] if x else np.nan for x in g]))
        if rec:
            arr = np.array(rec, dtype=float)
            out["elig"] = {"k": arr[:, 0].astype(int), "liq": arr[:, 1].astype(bool), "month": month[arr[:, 0].astype(int)],
                           "g20": arr[:, 2].astype(np.float32), "g60": arr[:, 3].astype(np.float32), "g120": arr[:, 4].astype(np.float32)}
    return out


# ── 統計 ──
def dedup(df: pd.DataFrame, gap: int = 20) -> pd.DataFrame:
    keep = []
    for (sid, v, kd), g in df.sort_values("k").groupby(["sid", "variant", "kind"], sort=False):
        last = -10 ** 9
        for i, k in zip(g.index, g["k"]):
            if k - last > gap:
                keep.append(i); last = k
    return df.loc[sorted(keep)]


def _p(x, d=2):
    return R._p(x, d)


def cell(L, title, d, base, hold_cols=("H20", "H60", "H120", "A2", "A3")):
    L.append(f"#### {title}（n＝{len(d):,}）"); L.append("")
    L.append("| 規則 | n | 平均 | 中位 | 勝率 | p10 | 最壞 | 月分群 95% CI | 基準 | 超額 | 超額 月配對 CI | 統計層 |")
    L.append("|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---|---|")
    res = {}
    for nm in hold_cols:
        x = d[f"g_{nm}"].to_numpy(float) - COST
        s = R.cl_stats(x, d["month"].to_numpy())
        if s["n"] == 0:
            L.append(f"| {nm} | 0 | | | | | | | | | | |"); continue
        if nm[0] == "H" and base is not None:
            H = int(nm[1:]); bm = base[H]
            ex = d[f"g_{nm}"].to_numpy(float) - d["month"].map(bm).to_numpy(float)
            se = R.cl_stats(ex, d["month"].to_numpy())
            b = float(np.nanmean(d["month"].map(bm).to_numpy(float))) - COST
            v = "測不出" if se["lo"] <= 0 <= se["hi"] else ("測得出（＋）" if se["mean"] > 0 else "測得出（−）")
            exs, ci = f"{se['mean'] * 100:+.2f} pp", f"{se['lo'] * 100:+.2f} ~ {se['hi'] * 100:+.2f}"
            res[nm] = se
        else:
            b, exs, ci, v = np.nan, "—", "—", "—"
        L.append(f"| {nm} | {s['n']:,} | {_p(s['mean'])} | **{_p(s['median'])}** | {s['win'] * 100:.1f}% | {_p(s['p10'])} | {_p(s['worst'])} | {_p(s['lo'])} ~ {_p(s['hi'])} | {_p(b)} | {exs} | {ci} | {v} |")
    L.append("")
    return res


def paired(L, title, d, a, b):
    x = (d[f"g_{a}"] - d[f"g_{b}"]).to_numpy(float)
    s = R.cl_stats(x, d["month"].to_numpy())
    if s["n"] == 0:
        L.append(f"- {title}：n 0"); return None
    v = "測不出" if s["lo"] <= 0 <= s["hi"] else "測得出"
    L.append(f"- {title}：n {s['n']:,}，{s['mean'] * 100:+.2f} pp（CI {s['lo'] * 100:+.2f} ~ {s['hi'] * 100:+.2f}）⇒ {v}")
    return s


def report(rows, base, elig, cal, out, reps, procs):
    df = pd.DataFrame(rows)
    err = df[df["kind"] == "ERROR"] if "kind" in df else df.iloc[0:0]
    df = df[df["kind"] != "ERROR"].copy()
    df["gate_all"] = df["gate_ok"] & df["liq_ok"]
    dd = dedup(df)
    L = ["# 研究十五：纏論第三類買點（單層日 K 簡化版）——細表", "",
         f"產出：{pd.Timestamp.now(tz='Asia/Taipei').strftime('%Y-%m-%d %H:%M')}（台北）。判準 `backtest/PREREG15.md`（K線分析 v2）。⛔ 這測的是「本簡化版的第三類買點」，不是纏論。", ""]
    if len(err):
        L.append(f"⚠ 偵測炸掉的檔：{len(err)}（{err['sid'].tolist()[:10]}）"); L.append("")
    # 訊號數總表
    L.append("## 〇、訊號數（去重前／去重 20 根後；主格閘門 ＝ 前置閘門＋流動性 5,000 萬）"); L.append("")
    L.append("| 變體 | 種類 | 全部 | 去重 | 過閘門 去重 | 每月中位（過閘門去重） |"); L.append("|---|---|---:|---:|---:|---:|")
    for v in VARIANTS:
        for kd in ("B3", "C2", "ABANDON"):
            a = df[(df.variant == v) & (df.kind == kd)]; b = dd[(dd.variant == v) & (dd.kind == kd)]; g = b[b.gate_all]
            L.append(f"| {v} | {kd} | {len(a):,} | {len(b):,} | {len(g):,} | {g.groupby('month').size().median() if len(g) else 0:.0f} |")
    L.append("")
    # 主格
    main = dd[(dd.variant == "main")]
    M = main[(main.kind == "B3") & main.gate_all]
    L.append("## 一、主格：B3、新筆、五筆中樞、閘門全套＋流動性、去重 20"); L.append("")
    res_main = cell(L, "主組 B3（過閘門、去重）", M, base["gate"])
    cell(L, "主組 B3（過閘門、不去重）", main[(main.kind == "B3") & main.gate_all] if False else df[(df.variant == "main") & (df.kind == "B3") & df["gate_ok"] & df["liq_ok"]], base["gate"])
    cell(L, "主組 B3（無流動性閘門、去重）", main[(main.kind == "B3") & main.gate_ok], base["nogate"])
    for per, lab in (("A", "A 段 2016–2020"), ("B", "B 段 2021–2026")):
        m = R.period_mask(M["month"], per)
        cell(L, f"主組 B3 {lab}", M[m], base["gate"])
    # 過濾統計
    L.append("### 乾淨窗砍掉幾 %（主組 B3 過閘門去重；只查 [進場, 出場]）"); L.append("")
    L.append("| 持有期 | 砍掉 | 砍掉那批 窗內有除權息 | 留下那批 窗內有除權息 | 砍掉那批 前三產業 | 留下那批 前三產業 |"); L.append("|---|---:|---:|---:|---|---|")
    ind = pd.read_csv(os.path.join(D.DATA, "meta", "industry.csv"), dtype=str).set_index("stock_id")["industry_name"]
    for H in HOLDS:
        drop = M[M[f"g_H{H}"].isna()]; keep = M[M[f"g_H{H}"].notna()]
        top = lambda d: "、".join(f"{k}{v:.0%}" for k, v in d["sid"].map(ind).value_counts(normalize=True).head(3).items()) if len(d) else "—"
        L.append(f"| H{H} | {len(drop) / max(1, len(M)) * 100:.1f}% | {drop[f'div_H{H}'].mean() * 100 if len(drop) else float('nan'):.0f}% | {keep[f'div_H{H}'].mean() * 100 if len(keep) else float('nan'):.0f}% | {top(drop)} | {top(keep)} |")
    L.append("")
    # 對照組
    L.append("## 二、對照組（主格、過閘門、去重）"); L.append("")
    C2 = main[(main.kind == "C2") & main.gate_all]; AB = main[(main.kind == "ABANDON") & main.gate_all]
    res_c2 = cell(L, "對照組② C2：向上離開中樞就進（第一根收盤 > ZG）", C2, base["gate"])
    cell(L, "放棄組③ ABANDON：回抽跌破 ZG", AB, base["gate"])
    L.append("### 主組 − 對照組②（同月配對：主組每筆減同月 C2 平均；月分群 CI）"); L.append("")
    diff = {}
    for H in HOLDS:
        c2m = C2.groupby("month")[f"g_H{H}"].mean()
        x = (M[f"g_H{H}"] - M["month"].map(c2m)).to_numpy(float)
        s = R.cl_stats(x, M["month"].to_numpy())
        if s["n"]:
            v = "測不出" if s["lo"] <= 0 <= s["hi"] else "測得出"
            L.append(f"- H{H}：{s['mean'] * 100:+.2f} pp（CI {s['lo'] * 100:+.2f} ~ {s['hi'] * 100:+.2f}，n {s['n']:,}）⇒ {v}"); diff[H] = s
    L.append("")
    # 安慰劑
    L.append("## 三、安慰劑（主組 B3 過閘門去重）"); L.append("")
    pa = {}
    for H in HOLDS:
        s = paired(L, f"主 − 安慰劑 A（平移 +{SHIFT} 交易日）H{H}", M[M[f"g_H{H}_pA"].notna()], f"H{H}", f"H{H}_pA"); pa[H] = s
    rng = np.random.default_rng(SEED_B)
    pool = elig
    L.append("")
    pb = {}
    for H in HOLDS:
        col = f"g{H}"
        vals = []
        for mth, g in M.groupby("month"):
            cand = pool[(pool["month"] == mth) & pool["liq"]]
            cand = cand[~np.isnan(cand[col])]
            if len(cand) == 0:
                continue
            pick = rng.choice(len(cand), size=min(len(g), len(cand)), replace=False)
            vals.append(pd.DataFrame({"month": mth, "g": cand[col].to_numpy()[pick]}))
        if not vals:
            continue
        Bv = pd.concat(vals); bm = Bv.groupby("month")["g"].mean()
        x = (M[f"g_H{H}"] - M["month"].map(bm)).to_numpy(float)
        s = R.cl_stats(x, M["month"].to_numpy())
        pb[H] = s
        L.append(f"- 主 − 安慰劑 B（同月同數量隨機股票日）H{H}：{s['mean'] * 100:+.2f} pp（CI {s['lo'] * 100:+.2f} ~ {s['hi'] * 100:+.2f}）⇒ {'測不出' if s['lo'] <= 0 <= s['hi'] else '測得出'}")
    for H in HOLDS:
        if H in pa and pa[H] and H in pb and pb[H]["mean"] > 0:
            L.append(f"- H{H} 時點佔比 ＝ (主−A) ÷ (主−B) ＝ {pa[H]['mean'] / pb[H]['mean'] * 100:.0f}%")
    L.append("")
    # 敏感度
    L.append("## 四、敏感度（各翻一個開關；B3 過閘門去重；H20 主判定）"); L.append("")
    L.append("| 變體 | n | H20 平均 | 中位 | 超額 月配對 | CI | 統計層 | H60 超額 | 主−② H20 |"); L.append("|---|---:|---:|---:|---:|---|---|---:|---:|")
    flips = {}
    for v in VARIANTS:
        d = dd[(dd.variant == v) & (dd.kind == "B3") & dd.gate_all]
        c2v = dd[(dd.variant == v) & (dd.kind == "C2") & dd.gate_all]
        if len(d) == 0:
            L.append(f"| {v} | 0 | | | | | | | |"); continue
        ex = d["g_H20"].to_numpy(float) - d["month"].map(base["gate"][20]).to_numpy(float); se = R.cl_stats(ex, d["month"].to_numpy())
        ex60 = d["g_H60"].to_numpy(float) - d["month"].map(base["gate"][60]).to_numpy(float); se60 = R.cl_stats(ex60, d["month"].to_numpy())
        c2m = c2v.groupby("month")["g_H20"].mean(); dx = R.cl_stats((d["g_H20"] - d["month"].map(c2m)).to_numpy(float), d["month"].to_numpy())
        vv = "測不出" if se["lo"] <= 0 <= se["hi"] else ("測得出（＋）" if se["mean"] > 0 else "測得出（−）")
        flips[v] = vv
        L.append(f"| {v} | {len(d):,} | {_p(d['g_H20'].mean() - COST)} | {_p(d['g_H20'].median() - COST)} | {se['mean'] * 100:+.2f} pp | {se['lo'] * 100:+.2f} ~ {se['hi'] * 100:+.2f} | {vv} | {se60['mean'] * 100:+.2f} pp | {dx['mean'] * 100:+.2f} pp（{'測不出' if dx['lo'] <= 0 <= dx['hi'] else '測得出'}） |")
    L.append("- ⚠ D_3pens ≡ 突破前高後回檔不破前高（研究二已測過的東西），PREREG15 1.4。"); L.append("")
    # 六關
    L.append("## 五、六關（H20 主判定）"); L.append("")
    r20 = res_main.get("H20"); ok1 = bool(r20 and r20["lo"] > 0)
    ok2 = bool(len(M) and (M["g_H20"].mean() - COST) > 0)
    ok3 = bool(20 in diff and diff[20]["lo"] > 0)
    mA = M[R.period_mask(M["month"], "A")]; mB = M[R.period_mask(M["month"], "B")]
    sA = R.cl_stats(mA["g_H20"].to_numpy(float) - mA["month"].map(base["gate"][20]).to_numpy(float), mA["month"].to_numpy()) if len(mA) else {"n": 0}
    sB = R.cl_stats(mB["g_H20"].to_numpy(float) - mB["month"].map(base["gate"][20]).to_numpy(float), mB["month"].to_numpy()) if len(mB) else {"n": 0}
    ok4 = bool(sA.get("n") and sB.get("n") and np.sign(sA["mean"]) == np.sign(sB["mean"]) == np.sign(r20["mean"] if r20 else 0))
    ok5 = all(flips.get(v) == flips.get("main") for v in VARIANTS)
    ok6 = bool(20 in pa and pa[20] and pa[20]["lo"] > 0 and 20 in pb and pb[20]["lo"] > 0)
    for i, (lab, v) in enumerate((("統計層測得出（超額月配對 CI 下緣 > 0）", ok1), ("扣成本後仍為正", ok2), ("對照組② 差得出來", ok3), ("兩段樣本外同號", ok4), ("四個敏感度沒有翻轉", ok5), ("安慰劑 A、B 都沒過（主 − A、主 − B 的 CI 下緣 > 0）", ok6)), 1):
        L.append(f"{i}. {lab}：{'✓' if v else '✗'}")
    verdict = all((ok1, ok2, ok3, ok4, ok5, ok6))
    L.append(""); L.append(f"**六關同過：{'是' if verdict else '否'} ⇒ {'進建議層' if verdict else '觀察，不建議'}**"); L.append("")
    # 組合層（主組過統計層才做）
    if ok1 and reps > 0:
        L.append("## 六、組合層（主組過統計層才做；N 5／10／20 × 200 種子、逐日市值；對 0050）"); L.append("")
        closes, opens = {}, {}
        uni = D.load_universe().set_index("stock_id")["market"]
        for sid in M["sid"].unique():
            st = D.load_stock(sid, uni.get(sid, "twse"), cal)
            closes[sid] = pd.Series(st.df["close"].to_numpy()).ffill().to_numpy(np.float32); opens[sid] = st.df["open"].to_numpy(np.float32)
        bench = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy()).ffill().to_numpy(float)
        sig = M.rename(columns={"x_H20": "xpos_H20", "x_H60": "xpos_H60", "x_H120": "xpos_H120"})
        first = int(sig["entry_pos"].min()); end = len(cal)
        bc = (bench[end - 1] / bench[first]) ** (245 / (end - first)) - 1; pk = np.maximum.accumulate(bench[first:end]); bm_ = float(((bench[first:end] - pk) / pk).min())
        L.append(f"0050 同窗（{cal[first].date()} ~ {cal[end - 1].date()}）：年化 {bc * 100:+.1f}%、最大回落 {bm_ * 100:.1f}%"); L.append("")
        L.append("| N | 規則 | 年化 中位 | p10 ~ p90 | 最大回落 中位 | p10 ~ p90 | 槽位 | 筆數 | 對 0050 |"); L.append("|---:|---|---:|---|---:|---|---:|---:|---|")
        for N in (5, 10, 20):
            for rule in ("H20", "H60"):
                st = [R.simulate_mtm(sig, rule, N, np.random.default_rng(1000 + r), closes, opens, len(cal)) for r in range(reps)]
                s = pd.DataFrame(st)
                win = s["cagr"].median() >= bc and s["mdd"].median() > bm_
                L.append(f"| {N} | {rule} | {s['cagr'].median() * 100:+.1f}% | {s['cagr'].quantile(.1) * 100:+.1f} ~ {s['cagr'].quantile(.9) * 100:+.1f}% | {s['mdd'].median() * 100:.1f}% | {s['mdd'].quantile(.1) * 100:.1f} ~ {s['mdd'].quantile(.9) * 100:.1f}% | {s['slot_use'].median() * 100:.0f}% | {s['trades'].median():.0f} | {'贏' if win else '沒贏'} |")
        L.append("")
    else:
        L.append("## 六、組合層：主組未過統計層，依 PREREG15 七不做。"); L.append("")
    with open(os.path.join(out, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    df.to_csv(os.path.join(out, "signals.csv.gz"), index=False)


def main():
    global RESULTS
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4); ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--limit", type=int); ap.add_argument("--stocks", nargs="*"); ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if a.out:
        RESULTS = a.out
    os.makedirs(RESULTS, exist_ok=True)
    t0 = time.time()
    cal = D.load_calendar(); uni = D.load_universe()
    ind = pd.read_csv(os.path.join(D.DATA, "meta", "industry.csv"), dtype=str).set_index("stock_id")["industry_code"]
    uni = uni[~uni["stock_id"].map(ind).isin(EXCL_IND)]
    if a.stocks:
        uni = uni[uni["stock_id"].isin(a.stocks)]
    if a.limit:
        uni = uni.head(a.limit)
    disp = D.load_disposal_intervals(); att = D.load_attention_dates(); marg = load_margin_o()
    print(f"母體 {len(uni)} 檔（排除產業 17／22）；停止融資 O 有紀錄 {len(marg)} 檔", file=sys.stderr)
    rows = []; elig_parts = []
    with Pool(a.procs, initializer=_init, initargs=(cal, disp, att, marg)) as pool:
        for i, r in enumerate(pool.imap_unordered(worker, list(zip(uni["stock_id"], uni["market"])), chunksize=8)):
            if r is None:
                continue
            rows.extend(r["rows"])
            if r["elig"] is not None:
                e = r["elig"]; elig_parts.append(pd.DataFrame({"sid": r["sid"], "k": e["k"], "liq": e["liq"], "month": e["month"], "g20": e["g20"], "g60": e["g60"], "g120": e["g120"]}))
            if (i + 1) % 300 == 0:
                print(f"  {i + 1}/{len(uni)} {time.time() - t0:.0f}s", file=sys.stderr)
    elig = pd.concat(elig_parts, ignore_index=True)
    base = {"gate": {}, "nogate": {}}
    for H in HOLDS:
        base["gate"][H] = elig[elig["liq"]].groupby("month")[f"g{H}"].mean()
        base["nogate"][H] = elig.groupby("month")[f"g{H}"].mean()
    elig.to_csv(os.path.join(RESULTS, "eligible.csv.gz"), index=False)
    print(f"訊號列 {len(rows):,}、合格股票日 {len(elig):,}，{time.time() - t0:.0f}s", file=sys.stderr)
    report(rows, base, elig, cal, RESULTS, a.reps, a.procs)
    print(f"完成 {time.time() - t0:.0f}s", file=sys.stderr)


if __name__ == "__main__":
    main()
