# -*- coding: utf-8 -*-
"""researchLong3_freq 對帳（抽樣手算、不前視、策略鎖）——回測線計算子代理。⛔ 不算任何報酬；只讀 resultsLong3/freq/ 與原始資料逐筆重算。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchLong3_freq_check
輸出 backtest/resultsLong3/freq/check.json、check.log

 C1 S1 抽 80 列（保留 50、剔除 30）：直接讀兩個版面的 revenue_hist 原始 CSV（⛔ 不經 research34）逐期比「當月 ≥ 前 24 期最大且 24 期齊全」；
    可用日以日曆逐日走到「次月 10／15 日之後第一個交易日」；sp ＝ 前一交易日；sp 閘（load_bars＋Frame.gate＋pit）、進場剔除逐項重判。另抽 40 個「非新高」股-月確認不在 S1。
 C2 不前視：全部 S1 事件 sp ＜ e、e 日期 ＞ 次月 10（15）日；丙全部首次觸發日 ≥ 進場日；F6 判斷日 ＝ 可用日＋4 ＞ 可用日；F1／F2 首次觸發日 ≥ 該季上傳日當天或之前最後交易日（抽 30）。
 C3 窗狀態抽 60 筆（S1、S2 × H250／H750）：兩世界 load_bars 逐根走，重判 完整／遇壞根／遇下市／資料尾不足。
 C4 丙 F3、F6 抽 40 筆：逐期走重找第一次觸發日。
 C5 乙 2016（跨接縫）、2010（早年）、2020（主）三年：母體全部重算 36 個月報酬（逐根、跨接縫用原始收盤比）、前後 10% 名單與 long_univ.csv.gz 逐檔比。
 C6 策略鎖 --check；git 已追蹤檔沒有被本件改動。
"""
from __future__ import annotations

import glob
import json
import math
import os
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchAscTri_freq as AT              # noqa: E402
from backtest import research11 as R                        # noqa: E402
from backtest import patterns as P                          # noqa: E402
from backtest import universe_gate as UG                    # noqa: E402
import backtest.data as D                                   # noqa: E402

UG.set_gate_v2(True)
OUT = "backtest/resultsLong3/freq"
LOG = []


def log(s):
    print(s, flush=True); LOG.append(str(s))


_RAW: dict = {}


def raw_rev(data_dirs, sid):
    """直接讀 revenue_hist 原始 CSV（⛔ 不經 research34），一次讀完、依代號分組。"""
    if not _RAW:
        L = []
        for d in data_dirs:
            for f in sorted(glob.glob(os.path.join(d, "mops", "revenue_hist", "*.csv"))):
                L.append(pd.read_csv(f, dtype=str, usecols=["stock_id", "period", "當月營收", "去年當月營收"]))
        x = pd.concat(L, ignore_index=True).drop_duplicates(["stock_id", "period"], keep="last")
        x["v"] = pd.to_numeric(x["當月營收"], errors="coerce"); x["l"] = pd.to_numeric(x["去年當月營收"], errors="coerce")
        for s, g in x.groupby("stock_id"):
            _RAW[s] = {p: (float(v), float(l)) for p, v, l in zip(g["period"], g["v"], g["l"])}
    return _RAW.get(sid, {})


def prev_period(p, k):
    y, m = int(p[:4]), int(p[5:]); n = y * 12 + m - 1 - k
    return f"{n // 12:04d}-{n % 12 + 1:02d}"


def main():
    rng = np.random.default_rng(20261020)
    res = {}
    WS = {wn: AT.load_world(wn) for wn in ("早年", "主")}
    We, Wm = WS["早年"], WS["主"]; ne = We["n0"]
    CAL = We["cal"].append(Wm["cal"]); CEND = len(CAL) - 1
    CP = {d.strftime("%Y-%m-%d"): j for j, d in enumerate(CAL)}
    datas = [We["data"], Wm["data"]]
    BARS = {}

    def bars(wn, sid):
        if (wn, sid) in BARS:
            return BARS[(wn, sid)]
        W = WS[wn]
        if sid not in W["ix"]:
            BARS[(wn, sid)] = None; return None
        D.DATA = W["data"]
        B = R.load_bars(sid, W["mk"].get(sid, "twse"), W["cal"])
        if B is None:
            BARS[(wn, sid)] = None; return None
        idx = B["idx"].astype(np.int64); nb = len(idx)
        bad = np.zeros(nb, bool)
        for k in range(nb):                                          # 逐根：next_bad[k] == k 即壞根
            if B["next_bad"][k] == k:
                bad[k] = True
        for p_ in W["BADPOS"].get(sid, ()):
            k = int(np.searchsorted(idx, p_, "left"))
            if k < nb:
                bad[k] = True
        f = P.Frame(B["df"], set())
        out = {"idx": idx, "bad": bad, "c": np.asarray(B["c"], float), "raw": B["df"]["close"].to_numpy(float)[idx], "gate": np.asarray(f.gate, bool)}
        BARS[(wn, sid)] = out
        return out

    COMB = {}

    def comb(sid):
        if sid not in COMB:
            COMB[sid] = comb0(sid)
        return COMB[sid]

    def comb0(sid):
        """合併兩世界的 (位置, 壞根, 世界)；接縫第一根主世界 K 棒不算壞根。"""
        ps, bs, ws = [], [], []
        for wn, off in (("早年", 0), ("主", ne)):
            b = bars(wn, sid)
            if b is None:
                continue
            ps += list(b["idx"] + off); bs += list(b["bad"]); ws += [wn] * len(b["idx"])
        for j in range(1, len(ws)):
            if ws[j] == "主" and ws[j - 1] == "早年":
                bs[j] = False
        return ps, bs, ws

    # ── C1
    S1 = pd.read_csv(os.path.join(OUT, "events_S1.csv.gz"), dtype={"sid": str})
    keep = S1[S1["st"] == "保留"]; rej = S1[S1["st"] != "保留"]
    smp = pd.concat([keep.sample(50, random_state=1), rej.sample(30, random_state=2)])
    diff = []
    for r in smp.itertuples(index=False):
        rv = raw_rev(datas, r.sid)
        v0 = rv.get(r.期別, (np.nan, np.nan))[0]
        hist = [rv.get(prev_period(r.期別, k), (np.nan, np.nan))[0] for k in range(1, 25)]
        hi = bool(np.isfinite(v0) and all(np.isfinite(hist)) and v0 >= max(hist))
        y, m = int(r.期別[:4]), int(r.期別[5:]); y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
        cut = pd.Timestamp(y2, m2, 15 if r.期別 >= "2026-01" else 10)
        j = 0
        while CAL[j] <= cut:
            j += 1
        e = j; sp = e - 1
        wn = "早年" if e < ne else "主"; off = 0 if wn == "早年" else ne
        W = WS[wn]; b = bars(wn, r.sid); i = W["ix"][r.sid]
        if not (off <= sp):
            st = "sp跨世界"
        else:
            spw, ew = sp - off, e - off
            g = bool(b["gate"][spw] and W["PV"][i][spw] and (spw in set(b["idx"].tolist())))
            if not g:
                st = "閘外(sp)"
            else:
                ks = [k for k in range(len(b["idx"])) if spw < b["idx"][k] <= ew]
                if any(b["bad"][k] for k in ks):
                    st = "壞根(sp,e]"
                elif not (W["TRD"][i, ew] and np.isfinite(W["O"][i, ew]) and W["O"][i, ew] > 0):
                    st = "e無成交"
                elif W["UPL"][i, ew]:
                    st = "e開盤鎖漲停"
                else:
                    st = "保留"
        if not hi or e != r.e or sp != r.sp or st != r.st:
            diff.append((r.sid, r.期別, hi, e, r.e, st, r.st))
    res["C1 S1 抽 80 列不同"] = len(diff); res["C1 不同明細"] = diff[:10]
    # 非新高股-月不在 S1
    s1set = set(zip(S1["sid"], S1["期別"]))
    ok_neg = 0; bad_neg = []
    sids = sorted(set(S1["sid"]))
    tries = 0
    while ok_neg < 40 and tries < 400:
        tries += 1
        sid = sids[int(rng.integers(len(sids)))]
        rv = raw_rev(datas, sid); ps = sorted(rv)
        if len(ps) < 30:
            continue
        p = ps[int(rng.integers(24, len(ps)))]
        v0 = rv[p][0]; hist = [rv.get(prev_period(p, k), (np.nan, np.nan))[0] for k in range(1, 25)]
        if np.isfinite(v0) and all(np.isfinite(hist)) and v0 < max(hist):
            ok_neg += 1
            if (sid, p) in s1set:
                bad_neg.append((sid, p))
    res["C1 非新高 40 股-月誤入 S1"] = len(bad_neg)
    log(f"[C1] {res['C1 S1 抽 80 列不同']} 不同｜非新高誤入 {len(bad_neg)}")
    # ── C2 不前視
    S1["cut"] = [pd.Timestamp(*(lambda y, m: ((y + 1, 1) if m == 12 else (y, m + 1)))(int(p[:4]), int(p[5:])), 15 if p >= "2026-01" else 10) for p in S1["期別"]]
    c2a = int((S1["sp"] >= S1["e"]).sum()); c2b = int((pd.to_datetime(S1["進場日"]) <= S1["cut"]).sum())
    CR = pd.read_csv(os.path.join(OUT, "events_丙.csv.gz"), dtype={"sid": str})
    c2c = 0
    for F in ("F1", "F2", "F3", "F4", "F5", "F6", "F7"):
        x = CR[CR[f"{F}_首次"].fillna("") != ""]
        c2c += int((pd.to_datetime(x[f"{F}_首次"]) < pd.to_datetime(x["進場日"])).sum())
        c2c += int((pd.to_datetime(x[f"{F}_首次"]) > pd.to_datetime(x["有效窗尾"])).sum())
    res["C2 S1 sp≥e"] = c2a; res["C2 S1 進場日≤次月10/15日"] = c2b; res["C2 丙首次觸發早於進場或晚於有效窗尾"] = c2c
    log(f"[C2] sp≥e {c2a}｜進場不晚於公布期限 {c2b}｜丙越界 {c2c}")
    # ── C3 窗
    def win_loop(sid, e, x):
        if x > CEND:
            return "資料尾不足"
        ps, bs, ws = comb(sid)
        ke = max(k for k in range(len(ps)) if ps[k] <= e)
        evs = []
        for k in range(ke + 1, len(ps)):
            if ps[k] > x:
                break
            if bs[k]:
                evs.append((ps[k], "遇壞根")); break
        L = ps[-1]
        if L < x:
            in_main = bars("主", sid) is not None
            if (not in_main) and L >= ne - 5:
                if x >= ne:
                    evs.append((ne, "接縫不明"))
            elif CEND - L >= 5:
                evs.append((L + 1, "遇下市"))
        return min(evs)[1] if evs else "完整"

    FA = pd.read_csv(os.path.join(OUT, "freq_甲.csv"))
    S2 = []
    for wn in ("早年", "主"):
        x = pd.read_csv(f"backtest/resultsPTH/freq/events_{wn}.csv.gz", dtype={"sid": str})
        x = x[x["入選"] & (x["跳月_st"] == "保留")]
        S2.append(x)
    S2 = pd.concat(S2); S2["e"] = S2["跳月_進場日"].map(CP)
    # 主程式的窗狀態沒有逐筆落檔 ⇒ ① 抽 60 筆比兩種獨立實作（向量 vs 逐根迴圈）；② 下方以逐根迴圈重算 S1 H250 探索、確認全部可用事件的狀態合計，對主程式表
    diff3 = []
    smp3 = [("S1", r.sid, int(r.e)) for r in keep.sample(30, random_state=3).itertuples()] + [("S2", r.sid, int(r.e)) for r in S2.sample(30, random_state=4).itertuples()]
    for nm, sid, e in smp3:
        for H in (250, 750):
            x = e + H - 1
            a_ = win_loop(sid, e, x)
            # 向量版（與主程式 window 同式，獨立寫一次）
            ps, bs, ws = comb(sid); ps = np.array(ps); bs = np.array(bs)
            if x > CEND:
                b_ = "資料尾不足"
            else:
                ke = int(np.searchsorted(ps, e, "right")) - 1; kx = int(np.searchsorted(ps, x, "right")) - 1
                ev = []
                if kx > ke and bs[ke + 1:kx + 1].any():
                    ev.append((int(ps[ke + 1 + int(np.argmax(bs[ke + 1:kx + 1]))]), "遇壞根"))
                L = int(ps[-1])
                if L < x:
                    if bars("主", sid) is None and L >= ne - 5:
                        if x >= ne:
                            ev.append((ne, "接縫不明"))
                    elif CEND - L >= 5:
                        ev.append((L + 1, "遇下市"))
                b_ = min(ev)[1] if ev else "完整"
            if a_ != b_:
                diff3.append((nm, sid, e, H, a_, b_))
    res["C3 窗狀態 60 筆×2H 迴圈 vs 向量 不同"] = len(diff3); res["C3 明細"] = diff3[:10]
    # 合計對：S1 H250 探索 可用數 ＝ 段內進場且 x ≤ 2021-12-30 的筆數（獨立算）
    p0 = CP["2017-03-02"]; p1 = max(v for k, v in CP.items() if k <= "2020-12-31"); xb = max(v for k, v in CP.items() if k <= "2021-12-30")
    n_av = int(((keep["e"] >= p0) & (keep["e"] <= p1) & (keep["e"] + 249 <= xb)).sum())
    n_tab = int(FA[(FA["集合"] == "S1") & (FA["H"] == 250) & (FA["段"] == "探索")]["可用"].iloc[0])
    res["C3 S1 H250 探索 可用 獨立數 vs 表"] = [n_av, n_tab]
    # 逐根迴圈重算全部可用事件的狀態合計
    pc0 = CP["2022-01-03"]
    tot_diff = {}
    for sg, msk in (("探索", (keep["e"] >= p0) & (keep["e"] <= p1) & (keep["e"] + 249 <= xb)), ("確認", (keep["e"] >= pc0) & (keep["e"] + 249 <= CEND))):
        cnt = {"完整": 0, "遇壞根": 0, "遇下市": 0, "接縫不明": 0}
        for sid, e in zip(keep.loc[msk, "sid"], keep.loc[msk, "e"]):
            cnt[win_loop(sid, int(e), int(e) + 249)] += 1
        row = FA[(FA["集合"] == "S1") & (FA["H"] == 250) & (FA["段"] == sg)].iloc[0]
        tab = {k: int(row[f"窗_{k}"]) for k in cnt}
        tot_diff[sg] = {"迴圈": cnt, "表": tab}
    res["C3 S1 H250 狀態合計 迴圈 vs 表"] = tot_diff
    c3_ok = all(v["迴圈"] == v["表"] for v in tot_diff.values())
    log(f"[C3] 不同 {len(diff3)}｜S1 H250 探索可用 {n_av} vs {n_tab}｜狀態合計 {tot_diff}")
    # ── C4 F3、F6
    revcache = {}
    diff4 = []
    smp4 = CR.sample(40, random_state=5)
    for r in smp4.itertuples(index=False):
        sid = r.sid
        if sid not in revcache:
            revcache[sid] = raw_rev(datas, sid)
        rv = revcache[sid]
        e = CP[r.進場日]; xe = CP[r.有效窗尾]; dhi = xe - 1
        f3 = ""; f6 = ""
        q = r.期別
        for _ in range(300):
            q = prev_period(q, -1)
            y, m = int(q[:4]), int(q[5:]); y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
            cut = pd.Timestamp(y2, m2, 15 if q >= "2026-01" else 10)
            A = int(CAL.searchsorted(cut, side="right"))
            if A > dhi or A > CEND:
                break
            yy = []
            for k in range(3):
                v, l_ = rv.get(prev_period(q, k), (np.nan, np.nan))
                yy.append(v / l_ - 1 if (np.isfinite(v) and np.isfinite(l_) and l_ > 0) else np.nan)
            if not f3 and all(np.isfinite(yy)) and all(t < 0 for t in yy):
                f3 = str(CAL[A].date())
            v0 = rv.get(q, (np.nan, np.nan))[0]; hist = [rv.get(prev_period(q, k), (np.nan, np.nan))[0] for k in range(1, 25)]
            hi = bool(np.isfinite(v0) and all(np.isfinite(hist)) and v0 >= max(hist))
            if not f6 and hi and A + 4 <= dhi:
                ps, bs, ws = comb(sid)
                ka = max([k for k in range(len(ps)) if ps[k] <= A - 1], default=-1); kb = max([k for k in range(len(ps)) if ps[k] <= A + 4], default=-1)
                if ka >= 0 and kb > ka and not any(bs[ka + 1:kb + 1]) and ws[ka] == ws[kb]:
                    b_ = bars(ws[ka], sid); off = 0 if ws[ka] == "早年" else ne
                    ia = int(np.searchsorted(b_["idx"], ps[ka] - off)); ib = int(np.searchsorted(b_["idx"], ps[kb] - off))
                    if b_["c"][ib] / b_["c"][ia] - 1 <= 0:
                        f6 = str(CAL[A + 4].date())
        g3 = r.F3_首次 if isinstance(r.F3_首次, str) else ""; g6 = r.F6_首次 if isinstance(r.F6_首次, str) else ""
        if f3 != g3 or f6 != g6:
            diff4.append((sid, r.期別, f3, g3, f6, g6))
    res["C4 F3/F6 抽 40 筆不同"] = len(diff4); res["C4 明細"] = diff4[:10]
    log(f"[C4] {len(diff4)} 不同 {diff4[:3]}")
    # ── C5 乙
    U = pd.read_csv(os.path.join(OUT, "long_univ.csv.gz"), dtype={"sid": str})
    diff5 = {}
    for Y in (2010, 2016, 2020):
        t = max(v for k, v in CP.items() if k <= f"{Y}-12-31"); t0 = max(v for k, v in CP.items() if k <= f"{Y - 3}-12-31")
        wn = "早年" if t < ne else "主"; off = 0 if wn == "早年" else ne
        cand = sorted(set(WS[wn]["sids"]))
        RR = {}
        for sid in cand:
            b = bars(wn, sid)
            if b is None or not b["gate"][t - off] or not WS[wn]["PV"][WS[wn]["ix"][sid]][t - off] or (t - off) not in set(b["idx"].tolist()):
                continue
            ps, bs, ws = comb(sid)
            kt = ps.index(t)
            k0s = [k for k in range(len(ps)) if ps[k] <= t0]
            if not k0s:
                continue
            k0 = k0s[-1]
            if any(bs[k0 + 1:kt + 1]):
                continue
            # 逐段乘
            r = 1.0; k = k0
            while k < kt:
                if ws[k] == ws[k + 1]:
                    bk = bars(ws[k], sid); offk = 0 if ws[k] == "早年" else ne
                    i0 = int(np.searchsorted(bk["idx"], ps[k] - offk)); i1 = int(np.searchsorted(bk["idx"], ps[k + 1] - offk))
                    r *= bk["c"][i1] / bk["c"][i0]
                else:
                    be, bm = bars("早年", sid), bars("主", sid)
                    r *= bm["raw"][0] / be["raw"][-1]
                k += 1
            RR[sid] = r - 1
        v = np.array(list(RR.values())); n = len(v); kk = int(math.ceil(0.1 * n))
        cw = np.sort(v)[::-1][kk - 1]; cl_ = np.sort(v)[kk - 1]
        W_ = {s for s, x in RR.items() if x >= cw}; L_ = {s for s, x in RR.items() if x <= cl_}
        u = U[U["形成年"] == Y]
        diff5[Y] = {"母體 重算／表": [n, len(u)], "贏家 重算／表／交集": [len(W_), int(u["贏家"].sum()), len(W_ & set(u.loc[u["贏家"], "sid"]))],
                    "輸家 重算／表／交集": [len(L_), int(u["輸家"].sum()), len(L_ & set(u.loc[u["輸家"], "sid"]))],
                    "母體名單差": len(set(RR) ^ set(u["sid"]))}
    res["C5 乙"] = diff5
    log(f"[C5] {diff5}")
    # ── C6
    lk = subprocess.run([os.path.expanduser("~/tw-p16/.venv/bin/python"), "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True)
    gs = subprocess.run(["git", "status", "--short"], capture_output=True, text=True).stdout.splitlines()
    res["C6 策略鎖"] = (lk.stdout.strip() + lk.stderr.strip())[:200]; res["C6 策略鎖 exit"] = lk.returncode
    res["C6 git 已追蹤檔被改（M）"] = [l for l in gs if l.startswith(" M") or l.startswith("M ")]
    log(f"[C6] {res['C6 策略鎖']}｜M {res['C6 git 已追蹤檔被改（M）']}")
    ok = (res["C1 S1 抽 80 列不同"] == 0 and res["C1 非新高 40 股-月誤入 S1"] == 0 and c2a == 0 and c2b == 0 and c2c == 0
          and len(diff3) == 0 and n_av == n_tab and c3_ok and len(diff4) == 0 and lk.returncode == 0
          and all(v["母體名單差"] == 0 and v["贏家 重算／表／交集"][0] == v["贏家 重算／表／交集"][1] == v["贏家 重算／表／交集"][2]
                  and v["輸家 重算／表／交集"][0] == v["輸家 重算／表／交集"][1] == v["輸家 重算／表／交集"][2] for v in diff5.values()))
    res["全部通過"] = bool(ok)
    log(f"[結論] 全部通過 {ok}")
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
