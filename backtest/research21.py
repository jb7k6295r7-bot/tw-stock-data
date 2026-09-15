"""研究二十一：詩魂變盤三部曲（單層日 K 落地版）＋敏感度 E／F／H。判準 backtest/PREREG21.md。

    python3 -m backtest.research21 [--procs 4] [--reps 200] [--limit N]

偵測 ＝ wsh.detect；閘門／母體／去重 ＝ research15；出場／CI／組合層 ＝ research11。
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import data as D
from . import research11 as R
from . import research15 as R15
from . import wsh as W

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results21")
R15DIR = os.path.join(HERE, "results15")
COST = R.COST
HOLDS = (20, 60, 120)
CAP_F = 120
VARIANTS = {"E0": dict(mode="E0", redraw_n=0, hthr=0.0), "E1": dict(mode="E1", redraw_n=0, hthr=0.0), "E2": dict(mode="E2", redraw_n=0, hthr=0.0),
            "E3": dict(mode="E3", redraw_n=0, hthr=0.0), "E4_3": dict(mode="E1", redraw_n=3, hthr=0.0), "E4_5": dict(mode="E1", redraw_n=5, hthr=0.0),
            "H2": dict(mode="E0", redraw_n=0, hthr=0.01), "H3": dict(mode="E0", redraw_n=0, hthr=0.04)}
_G: dict = {}


def _init(cal, disp, att, marg):
    R._init(cal); _G.update(cal=cal, disp=disp, att=att, marg=marg)


def f_exits(o, c, sw, k, sg, next_bad):
    """F0：收盤跌破末升低（進場後最近已確認 swing low；起始 ＝ HL）；F1：收盤跌破最近兩個已確認 swing low 的連線（起始 ＝ (L, HL)）。次根開盤出；上限 CAP_F。"""
    n = len(c); nb = next_bad[k + 1]; ep = o[k + 1]
    last = min(n - 1, k + CAP_F)
    if last >= nb or not (ep > 0):
        return {"F0": np.nan, "F0_bars": np.nan, "F1": np.nan, "F1_bars": np.nan}
    lows = [(sg["hl_idx"], sg["hl"])]
    if sg.get("L") is not None:
        lows = [(-1, sg["L"])] + lows
    lows_conf = [(cf, i, p) for cf, i, t, p in sw if t == "L" and i > k]
    out = {}
    for rule in ("F0", "F1"):
        cur = list(lows); ci = 0; hit = None
        for t in range(k + 1, last + 1):
            while ci < len(lows_conf) and lows_conf[ci][0] <= t:
                cur.append((lows_conf[ci][1], lows_conf[ci][2])); ci += 1
            if rule == "F0":
                thr = cur[-1][1]
            else:
                thr = W.line_value(cur[-2], cur[-1], t) if len(cur) >= 2 and cur[-2][0] >= 0 else cur[-1][1]
            if c[t] < thr:
                hit = t; break
        if hit is not None:
            if hit + 1 <= last and hit + 1 < n:
                out[rule] = o[hit + 1] / ep - 1; out[f"{rule}_bars"] = hit + 1 - k
            else:
                out[rule] = c[hit] / ep - 1; out[f"{rule}_bars"] = hit - k
        else:
            out[rule] = c[last] / ep - 1; out[f"{rule}_bars"] = last - k
    return out


def worker(args):
    sid, market = args
    cal, disp, att, marg = _G["cal"], _G["disp"], _G["att"], _G["marg"]
    B = R.load_bars(sid, market, cal)
    if B is None:
        return None
    idx, dates, o, c, h, l, amt, next_bad, ev_bar = (B[k] for k in ("idx", "dates", "o", "c", "h", "l", "amt", "next_bad", "ev_bar"))
    n = len(idx)
    liq_ok = pd.Series(amt).shift(1).rolling(20, min_periods=20).mean().to_numpy(float) >= R15.LIQ
    dmask = D.disposal_mask(sid, cal, disp)[idx]
    a_dates = att.get(sid, set()); m_dates = marg.get(sid, set())
    gate_ok = ~dmask & np.array([d not in a_dates and d not in m_dates for d in dates])
    nxt = np.minimum(np.arange(n) + 1, n - 1)
    valid_sig = (dates >= R15.SIG_START) & (np.arange(n) + 1 < n) & np.isfinite(o[nxt]) & (o[nxt] > 0)
    month = dates.strftime("%Y-%m")
    sw = W.swings(h, l)
    out = {"sid": sid, "rows": [], "noline": {}}
    for vname, vp in VARIANTS.items():
        try:
            sigs = W.detect(o, h, l, c, mode=vp["mode"], redraw_n=vp["redraw_n"], hthr=vp["hthr"], start=0)
        except Exception as e:
            out["rows"].append({"sid": sid, "variant": vname, "kind": "ERROR", "err": repr(e)}); continue
        out["noline"][vname] = (sum(1 for s in sigs if s["kind"] == "NOLINE"), sum(1 for s in sigs if s["kind"] == "S1"))
        for sg in sigs:
            if sg["kind"] == "NOLINE":
                continue
            k = int(sg["signal_raw"])
            if k < 1 or k >= n or not valid_sig[k]:
                continue
            row = {"sid": sid, "variant": vname, "kind": sg["kind"], "k": k, "pos": int(idx[k]), "entry_pos": int(idx[k + 1]), "month": month[k],
                   "liq_ok": bool(liq_ok[k]), "gate_ok": bool(gate_ok[k]), "t1": sg.get("t1"), "bars_since_t1": k - sg["t1"] if sg.get("t1") is not None else np.nan}
            nb = next_bad[k + 1]
            for H in HOLDS:
                r = R.fixed_exit(o, c, k, H, nb)
                row[f"g_H{H}"] = r[1] if r else np.nan; row[f"x_H{H}"] = int(idx[r[0]]) if r else -1
            if vname == "E0" and sg["kind"] == "S3":
                row.update(f_exits(o, c, sw, k, sg, next_bad))
            out["rows"].append(row)
    return out


def _p(x, d=2):
    return R._p(x, d)


def _ci(s):
    return f"{s['mean'] * 100:+.2f} pp（{s['lo'] * 100:+.2f} ~ {s['hi'] * 100:+.2f}）⇒ {'測不出' if s['lo'] <= 0 <= s['hi'] else '測得出'}"


def cell(L, title, d, base, cols=("H20", "H60", "H120")):
    L.append(f"#### {title}（n＝{len(d):,}）"); L.append("")
    L.append("| 規則 | n | 平均 | 中位 | 勝率 | p10 | 最壞 | 月分群 95% CI | 基準 | 超額 | 超額 月配對 CI | 統計層 |"); L.append("|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---|---|")
    res = {}
    for nm in cols:
        col = f"g_{nm}" if nm[0] == "H" else nm
        x = d[col].to_numpy(float) - COST; s = R.cl_stats(x, d["month"].to_numpy())
        if s["n"] == 0:
            L.append(f"| {nm} | 0 | | | | | | | | | | |"); continue
        if nm[0] == "H":
            bm = base[int(nm[1:])]; ex = d[col].to_numpy(float) - d["month"].map(bm).to_numpy(float); se = R.cl_stats(ex, d["month"].to_numpy())
            b = float(np.nanmean(d["month"].map(bm).to_numpy(float))) - COST
            v = "測不出" if se["lo"] <= 0 <= se["hi"] else ("測得出（＋）" if se["mean"] > 0 else "測得出（−）")
            exs, ci = f"{se['mean'] * 100:+.2f} pp", f"{se['lo'] * 100:+.2f} ~ {se['hi'] * 100:+.2f}"; res[nm] = se
        else:
            b, exs, ci = np.nan, "—", "—"; v = "測不出" if s["lo"] <= 0 <= s["hi"] else ("測得出（＋）" if s["mean"] > 0 else "測得出（−）"); res[nm] = s
        L.append(f"| {nm} | {s['n']:,} | {_p(s['mean'])} | **{_p(s['median'])}** | {s['win'] * 100:.1f}% | {_p(s['p10'])} | {_p(s['worst'])} | {_p(s['lo'])} ~ {_p(s['hi'])} | {_p(b)} | {exs} | {ci} | {v} |")
    L.append("")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4); ap.add_argument("--reps", type=int, default=200); ap.add_argument("--limit", type=int)
    a = ap.parse_args(); os.makedirs(RESULTS, exist_ok=True); t0 = time.time()
    cal = D.load_calendar(); uni = D.load_universe()
    ind = pd.read_csv(os.path.join(D.DATA, "meta", "industry.csv"), dtype=str).set_index("stock_id")["industry_code"]
    uni = uni[~uni["stock_id"].map(ind).isin(R15.EXCL_IND)]
    if a.limit:
        uni = uni.head(a.limit)
    disp = D.load_disposal_intervals(); att = D.load_attention_dates(); marg = R15.load_margin_o()
    rows = []; noline = {}
    with Pool(a.procs, initializer=_init, initargs=(cal, disp, att, marg)) as pool:
        for i, r in enumerate(pool.imap_unordered(worker, list(zip(uni["stock_id"], uni["market"])), chunksize=8)):
            if r is None:
                continue
            rows.extend(r["rows"])
            for v, (nl, s1) in r["noline"].items():
                a_, b_ = noline.get(v, (0, 0)); noline[v] = (a_ + nl, b_ + s1)
            if (i + 1) % 300 == 0:
                print(f"  {i + 1}/{len(uni)} {time.time() - t0:.0f}s", file=sys.stderr)
    E = pd.read_csv(os.path.join(R15DIR, "eligible.csv.gz"), dtype={"sid": str})
    base = {H: E[E["liq"]].groupby("month")[f"g{H}"].mean() for H in HOLDS}
    df = pd.DataFrame(rows); err = df[df["kind"] == "ERROR"] if "kind" in df else df.iloc[0:0]; df = df[df["kind"] != "ERROR"].copy()
    df["gate_all"] = df["gate_ok"] & df["liq_ok"]
    dd = R15.dedup(df)
    df.to_csv(os.path.join(RESULTS, "signals.csv.gz"), index=False)
    L = ["# 研究二十一：詩魂變盤三部曲——細表", "", f"產出：{pd.Timestamp.now(tz='Asia/Taipei').strftime('%Y-%m-%d %H:%M')}（台北）。判準 `backtest/PREREG21.md`。⛔ 這測的是本落地版，不是詩魂。", ""]
    if len(err):
        L.append(f"⚠ 偵測炸掉的檔：{len(err)}（{err['sid'].tolist()[:10]}）"); L.append("")
    L.append("## 〇、訊號數（過閘門＋流動性、去重 20）與 NOLINE"); L.append("")
    L.append("| 變體 | S3 | S1 | ABANDON | NOSTEP3 | NOLINE／S1 候選 | S3 每月中位 |"); L.append("|---|---:|---:|---:|---:|---|---:|")
    for v in VARIANTS:
        g = dd[(dd.variant == v) & dd.gate_all]
        cnt = {kd: int((g.kind == kd).sum()) for kd in ("S3", "S1", "ABANDON", "NOSTEP3")}
        nl = noline.get(v, (0, 0)); s3 = g[g.kind == "S3"]
        L.append(f"| {v} | {cnt['S3']:,} | {cnt['S1']:,} | {cnt['ABANDON']:,} | {cnt['NOSTEP3']:,} | {nl[0]:,}／{nl[0] + nl[1]:,}（{nl[0] / max(1, nl[0] + nl[1]) * 100:.0f}%） | {s3.groupby('month').size().median() if len(s3) else 0:.0f} |")
    L.append("")
    k_sig = 0
    main = dd[(dd.variant == "E0") & dd.gate_all]; M = main[main.kind == "S3"]
    L.append("## 一、主格 E0：S3（第三步訊號日次根開盤進）"); L.append("")
    res = cell(L, "主組 S3", M, base)
    k_sig += sum(int(not (res[h]["lo"] <= 0 <= res[h]["hi"])) for h in ("H20", "H60", "H120") if h in res)
    for per, lab in (("A", "A 段 2016–2020"), ("B", "B 段 2021–2026")):
        m = R.period_mask(M["month"], per); cell(L, f"主組 S3 {lab}", M[m], base)
    L.append(f"- 第三步距第一步：中位 {M['bars_since_t1'].median():.0f} 根、p90 {M['bars_since_t1'].quantile(.9):.0f}"); L.append("")
    L.append("## 二、對照與放棄（E0）"); L.append("")
    S1 = main[main.kind == "S1"]; AB = main[main.kind == "ABANDON"]; NS = main[main.kind == "NOSTEP3"]
    cell(L, "對照組 S1：第一步就進（收盤 > 末跌高 次根開盤）", S1, base)
    cell(L, "放棄組 ABANDON：HL 成立後收盤跌破 HL（從跌破日次根起算）", AB, base)
    cell(L, "放棄組 NOSTEP3：第一步後 60 根沒走到第三步（從第 60 根起算）", NS, base)
    L.append("### 主 − S1（同月配對，月分群 CI）"); L.append("")
    for H in HOLDS:
        s1m = S1.groupby("month")[f"g_H{H}"].mean(); x = (M[f"g_H{H}"] - M["month"].map(s1m)).to_numpy(float); s = R.cl_stats(x, M["month"].to_numpy())
        if s["n"]:
            L.append(f"- H{H}：{_ci(s)}（n {s['n']:,}）")
            if H == 20:
                k_sig += int(not (s["lo"] <= 0 <= s["hi"]))
    L.append("")
    L.append("## 三、敏感度 E（第一步的線型；S3、H20）與 H（第三步幅度）"); L.append("")
    L.append("| 變體 | n | NOLINE | H20 平均 | 中位 | 超額 | CI | 統計層 | H60 超額 | 主−S1 H20 |"); L.append("|---|---:|---:|---:|---:|---:|---|---|---:|---:|")
    signs = {}
    for v in VARIANTS:
        d = dd[(dd.variant == v) & (dd.kind == "S3") & dd.gate_all]; s1v = dd[(dd.variant == v) & (dd.kind == "S1") & dd.gate_all]
        if len(d) == 0:
            L.append(f"| {v} | 0 | | | | | | | | |"); continue
        ex = d["g_H20"].to_numpy(float) - d["month"].map(base[20]).to_numpy(float); se = R.cl_stats(ex, d["month"].to_numpy())
        ex60 = d["g_H60"].to_numpy(float) - d["month"].map(base[60]).to_numpy(float); se60 = R.cl_stats(ex60, d["month"].to_numpy())
        s1m = s1v.groupby("month")["g_H20"].mean(); dx = R.cl_stats((d["g_H20"] - d["month"].map(s1m)).to_numpy(float), d["month"].to_numpy())
        vv = "測不出" if se["lo"] <= 0 <= se["hi"] else ("測得出（＋）" if se["mean"] > 0 else "測得出（−）"); signs[v] = vv
        if v != "E0":
            k_sig += int(vv != "測不出")
        nl = noline.get(v, (0, 0))
        dxs = (f"{dx['mean'] * 100:+.2f} pp（{'測不出' if dx['lo'] <= 0 <= dx['hi'] else '測得出'}）" if dx.get('n') else '—')
        L.append(f"| {v} | {len(d):,} | {nl[0] / max(1, nl[0] + nl[1]) * 100:.0f}% | {_p(d['g_H20'].mean() - COST)} | {_p(d['g_H20'].median() - COST)} | {se['mean'] * 100:+.2f} pp | {se['lo'] * 100:+.2f} ~ {se['hi'] * 100:+.2f} | {vv} | {se60['mean'] * 100:+.2f} pp | {dxs} |")
    L.append("")
    L.append(f"- E 各格一致？ {'是' if len(set(signs[v] for v in signs if v.startswith('E'))) == 1 else '否'}（{ {v: signs[v] for v in signs if v.startswith('E')} }）"); L.append("")
    L.append("## 四、敏感度 F（出場兩版；主格 S3；上限 120 根）"); L.append("")
    resF = cell(L, "F0 跌破末升低／F1 跌破上升趨勢線（對照 H120 固定）", M, base, cols=("F0", "F1", "H120"))
    for r_ in ("F0", "F1"):
        if r_ in resF:
            k_sig += int(not (resF[r_]["lo"] <= 0 <= resF[r_]["hi"]))
    L.append(f"- 平均持有：F0 {M['F0_bars'].mean():.0f} 根、F1 {M['F1_bars'].mean():.0f} 根"); L.append("")
    L.append(f"## 五、格數：13 格、測得出 {k_sig} 格、雜訊期望 0.65"); L.append("")
    ok1 = bool(res.get("H20") and res["H20"]["lo"] > 0)
    if ok1 and a.reps > 0 and len(M):
        L.append("## 六、組合層（主組過統計層；N 5／10／20 × H20／H60、逐日市值；對 0050）"); L.append("")
        closes, opens = {}, {}; um = uni.set_index("stock_id")["market"]
        for sid in M["sid"].unique():
            st = D.load_stock(sid, um.get(sid, "twse"), cal)
            closes[sid] = pd.Series(st.df["close"].to_numpy()).ffill().to_numpy(np.float32); opens[sid] = st.df["open"].to_numpy(np.float32)
        bench = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy()).ffill().to_numpy(float)
        sig = M.rename(columns={"x_H20": "xpos_H20", "x_H60": "xpos_H60", "x_H120": "xpos_H120"})
        first = int(sig["entry_pos"].min()); end = len(cal)
        bc = (bench[end - 1] / bench[first]) ** (245 / (end - first)) - 1; pk = np.maximum.accumulate(bench[first:end]); bm_ = float(((bench[first:end] - pk) / pk).min())
        L.append(f"0050 同窗：年化 {bc * 100:+.1f}%、最大回落 {bm_ * 100:.1f}%"); L.append("")
        L.append("| N | 規則 | 年化 中位 | p10 ~ p90 | 最大回落 中位 | p10 ~ p90 | 槽位 | 對 0050 |"); L.append("|---:|---|---:|---|---:|---|---:|---|")
        for N in (5, 10, 20):
            for rule in ("H20", "H60"):
                s = pd.DataFrame([R.simulate_mtm(sig, rule, N, np.random.default_rng(1000 + r), closes, opens, len(cal)) for r in range(a.reps)])
                win = s["cagr"].median() >= bc and s["mdd"].median() > bm_
                L.append(f"| {N} | {rule} | {s['cagr'].median() * 100:+.1f}% | {s['cagr'].quantile(.1) * 100:+.1f} ~ {s['cagr'].quantile(.9) * 100:+.1f}% | {s['mdd'].median() * 100:.1f}% | {s['mdd'].quantile(.1) * 100:.1f} ~ {s['mdd'].quantile(.9) * 100:.1f}% | {s['slot_use'].median() * 100:.0f}% | {'贏' if win else '沒贏'} |")
        L.append("")
    else:
        L.append("## 六、組合層：主組未過統計層（H20 超額 CI 下緣 ≤ 0），依 PREREG21 六不做。"); L.append("")
    open(os.path.join(RESULTS, "summary.md"), "w").write("\n".join(L))
    print(f"完成 {time.time() - t0:.0f}s → {RESULTS}/summary.md；測得出 {k_sig}/13", file=sys.stderr)


if __name__ == "__main__":
    main()
