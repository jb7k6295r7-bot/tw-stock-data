# -*- coding: utf-8 -*-
"""52 週新高 10 檔版（resultsPTHn N＝10 ＝ resultsPTHpf 10 檔版，補空位、抱 6 個月）加停損——回測線計算子代理（2026-10-20）。
使用者看了 resultsPTH10path（持有路徑）後問：停損「設 25 呢？」
⛔ 描述、不計 N、不判；看過結果才問 ⇒ 結果句必附「看過結果的參數變體，只描述，不當改規則依據；前瞻照 seq402 不加停損」。
⛔ 只計算：不 commit、不改既有檔；researchPTHn（run_slot、trades_df、df_text、same、NOTE_EARLY）、researchPTHpf（build_world、load_events、
   metrics、pf_stats、COST、SLIP、TYPN）、researchPTH（stock_job）、research11（load_bars，只讀低價）、researchAscTri（label、ratio）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTH10stop [--procs 4]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPTH10stop_check
輸出 backtest/resultsPTH10stop/：stop.json、stop_main.csv、decomp.csv、trades_<世界>_<讀法>_<門檻>[s].csv.gz、eq_<世界>.npz、run.log

讀法（★ 執行者定）：
 T1 組合 ⛔ 不另寫：researchPTHn.run_slot(ev, W, 10, slip)（＝ researchTurtleS2PF.simulate 主模式 10 槽、PTH 由高往下、同日先出後進、
    空槽在下一批進場日從當批由高往下補、賣出入帳當天留現金隔天買回 0050）。停損只改「每筆候選事件」的出場日與出場價（ev 的 sale、R、px），
    其餘一字不動 ⇒ 被停損空出的格子由引擎原規則在下個批次進場日補。門檻「無」＝ 原 ev ⇒ 必須與 resultsPTHn N＝10（含滑價版）逐位元一致。
 T2 ★ 主讀法「收盤判、隔天開盤賣」：持有中 ＝ 買進日收盤 … 排程賣出日前一日收盤（資料尾未出場 ⇒ 到資料尾）；只看有成交日（快取收盤非缺值）；
    觸發 ＝ 收盤 ÷ 買價 − 1 ≤ 門檻（含等號，容差 1e−12）的第一個日 d；賣出日 f ＝ d 之後第一個有開盤價的日（≤ 排程賣出日；無 ⇒ 不停損、照原出場）；
    賣價 ＝ 還原開盤 O[f]；f ＝ 排程賣出日 ⇒ 同根兩出場價取較低（seq373）＝ min(O[f], 原排程賣價)。
    ★ 買價 ＝ 該版本的市值基準價（主版 ＝ O[買進日]；滑價版 ＝ O[買進日]×1.005，即該版本實際成交價）；滑價版賣價再 ×0.995（slot_tr 原式）。
 T3 另一讀法「當根盤中觸價」（只描述）：日 d ∈ 買進日 … 排程賣出日（含；資料尾未出場 ⇒ 到資料尾）、有成交日；停損價 K ＝ 買價 ×(1＋門檻)；
    觸發 ＝ 還原最低 ≤ K 的第一日；賣價 ＝ 開盤 ≤ K ⇒ 開盤（跳空），否則 K；d ＝ 排程賣出日 ⇒ min(賣價, 原排程賣價)（seq373）；當日入帳。
    低價 ＝ research11.load_bars 的還原最低（閘：同支 load_bars 的開、收 ＝ 快取 O、C 逐值，不符 ⇒ 中止）。
 T4 每門檻報：探索、確認、早年 年化、回落、比值、對 0050 標籤（researchAscTri.label）、滑價版、換手與成本（researchPTHpf.pf_stats）、
    觸發筆與比例（段內買進筆中被停損的比例，依買進日歸段）。
 T5 少賠 vs 少賺（主版、依買進日歸段、該組合實際被停損的筆）：若抱滿 ＝ 原排程出場淨報酬（R − 0.585%；資料尾未出場 ⇒ 末日收盤市值計，另報筆數）；
    停損後 ＝ 停損賣價淨報酬；少賠 ＝ Σ max(0, 停損後 − 若抱滿)、少賺 ＝ Σ max(0, 若抱滿 − 停損後)（等權，另報金額加權 ＝ 金額 × 差）；
    被砍掉的大賺 ＝ 若抱滿 ＞ ＋30% 的筆數、其若抱滿淨報酬和 ÷ 基準（無停損）組合同段獲利筆淨報酬和；躲掉的大賠 ＝ 若抱滿 ≤ −30% 的筆數。
 T6 結果句必附：SENT；早年附 researchPTHn.NOTE_EARLY（reduce_v2 約 0.3%）；背景對照 BG。
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchPTHn as PN                     # noqa: E402  ⛔ 只 import
from backtest import researchPTHpf as M                     # noqa: E402
from backtest import researchPTH as PTH                     # noqa: E402
from backtest import researchPTH_freq as PT                 # noqa: E402
from backtest import research11 as R11                      # noqa: E402
from backtest import researchAscTri as AS                   # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402
from backtest import researchAddOn as RA                    # noqa: E402
from backtest import data as D                              # noqa: E402

OUT = "backtest/resultsPTH10stop"
SRC = PN.OUT
N = 10
COST = M.COST
SLIP = M.SLIP
THS = (None, -0.15, -0.20, -0.25, -0.30)
MODES = {"close": "收盤判隔天開盤賣", "intra": "當根盤中觸價（另一讀法，只描述）"}
SENT = "看過結果的參數變體，只描述，不當改規則依據；前瞻照 seq402 不加停損"
BG = "背景對照：一般出場法 seq6 中 −10% 停損比抱著差（隨便買母體）"
NOTE_EARLY = PN.NOTE_EARLY


def thname(th):
    return "無" if th is None else f"{int(round(th * 100))}%"


def tag(mode, th, slip):
    return ("base" if th is None else f"{mode}{int(round(-th * 100))}") + ("s" if slip else "")


# ═════════════ 低價（T3）═════════════
def low_job(a):
    wn, sid = a
    W = PT._G[wn]; D.DATA = W["data"]
    B = R11.load_bars(sid, W["mk"].get(sid, "twse"), W["cal"])
    if B is None:
        return sid, None
    return sid, (np.asarray(B["idx"], np.int64), np.asarray(B["o"], float), np.asarray(B["c"], float), np.asarray(B["l"], float))


def low_matrix(W, wn, sids, procs, log):
    LOW = np.full(W["O"].shape, np.nan)
    bad = {"開≠快取O": 0, "收≠快取C": 0, "無K棒": 0}
    with Pool(procs) as pool:
        for sid, r in pool.imap_unordered(low_job, [(wn, s) for s in sids], chunksize=8):
            if r is None:
                bad["無K棒"] += 1; continue
            idx, o, c, l_ = r; j = W["ix"][sid]
            O_ = W["O"][j, idx]; C_ = W["C"][j, idx]
            bad["開≠快取O"] += int((~((o == O_) | (np.isnan(o) & np.isnan(O_)))).sum())
            bad["收≠快取C"] += int((~((c == C_) | (np.isnan(c) & np.isnan(C_)))).sum())
            LOW[j, idx] = l_
    if any(bad.values()):
        raise SystemExit(f"⛔ {wn} load_bars 與快取不符 {bad}")
    log(f"[低價 {wn}] {len(sids)} 檔：load_bars 開、收 ＝ 快取 O、C 逐值相同")
    return LOW


# ═════════════ 停損改寫事件（T2、T3）═════════════
def apply_stop(ev, W, th, slip, mode, LOW):
    """回傳 ev2（只換 sale、R、px）與 info（逐事件 觸發日、是否停損、原排程賣價…）。"""
    n0 = W["n0"]; C = W["C"]; O = W["O"]
    m = len(ev["e"])
    ev2 = dict(ev); sale = ev["sale"].copy(); R = ev["R"].copy(); px = ev["px"].copy()
    trig = np.full(m, -1, np.int64); stopped = np.zeros(m, bool); same_bar = np.zeros(m, bool); gap = np.zeros(m, bool)
    fac = (1 + SLIP) if slip else 1.0
    for q in range(m):
        j = int(ev["j"][q]); e = int(ev["e"][q]); s = int(ev["sale"][q]); P = float(ev["P"][q]); ep = P * fac
        last = s if s >= 0 else n0 - 1
        if mode == "close":
            hi = (s - 1) if s >= 0 else n0 - 1
            if hi < e:
                continue
            c = C[j, e:hi + 1]
            with np.errstate(invalid="ignore"):
                hit = np.isfinite(c) & (c / ep - 1.0 <= th + 1e-12)
            if not hit.any():
                continue
            d = e + int(np.argmax(hit))
            oo = O[j, d + 1:last + 1]
            ok = np.isfinite(oo) & (oo > 0)
            if not ok.any():
                continue
            f = d + 1 + int(np.argmax(ok)); sp = float(O[j, f])
        else:
            l_ = LOW[j, e:last + 1]
            K = ep * (1.0 + th)
            with np.errstate(invalid="ignore"):
                hit = np.isfinite(l_) & (l_ <= K)
            if not hit.any():
                continue
            d = e + int(np.argmax(hit)); f = d
            op = float(O[j, d])
            if np.isfinite(op) and op > 0 and op <= K:
                sp = op; gap[q] = True
            else:
                sp = K
        if f == s:
            same_bar[q] = True
            sp = min(sp, float(ev["px"][q]))
        trig[q] = d; stopped[q] = True
        sale[q] = f; px[q] = sp; R[q] = sp / P - 1.0
    ev2["sale"] = sale; ev2["R"] = R; ev2["px"] = px
    return ev2, {"trig": trig, "stopped": stopped, "same_bar": same_bar, "gap": gap}


def orig_g(ev, W, slip):
    """若抱滿：原排程出場的 g（slot_tr 同式）；資料尾未出場 ⇒ 末日快取收盤市值。"""
    ep = ev["P"] * (1 + SLIP) if slip else ev["P"]
    g = ev["px"] * (1 - SLIP) / ep - 1.0 if slip else ev["R"].copy()
    g = np.array(g, float); tail = ev["sale"] < 0
    g[tail] = W["CM"][ev["j"][tail], W["n0"] - 1] / ep[tail] - 1.0
    return g, tail


# ═════════════ 統計 ═════════════
def seg_buys(S, x, y):
    return [(t, q, amt) for t, q, amt in S["buys"] if x <= t <= y]


def decomp(S, info, g0, tail, x, y, base_pos):
    qm = S["q"]; sl = {q: (t, proc) for t, q, amt, proc in S["sells"]}
    bs = seg_buys(S, x, y)
    st = [(t, q, amt) for t, q, amt in bs if info["stopped"][qm[q]] and q in sl]
    o = {"買進筆": len(bs), "觸發筆": len(st), "觸發比例": len(st) / len(bs) if bs else np.nan}
    if not st:
        return o
    a_ = np.array([amt for _, _, amt in st]); now = np.array([S["g"][q] for _, q, _ in st]) - COST
    hold = np.array([g0[qm[q]] for _, q, _ in st]) - COST; tl = np.array([tail[qm[q]] for _, q, _ in st])
    dif = now - hold
    o.update({"其中資料尾未出場(若抱滿以末日收盤計)": int(tl.sum()), "同根取較低筆": int(sum(info["same_bar"][qm[q]] for _, q, _ in st)),
              "停損後平均淨報酬": float(now.mean()), "若抱滿平均淨報酬": float(hold.mean()), "若抱滿中位": float(np.median(hold)),
              "若抱滿最後賺(>0)比例": float((hold > 0).mean()),
              "少賠合計(等權)": float(dif[dif > 0].sum()), "少賺合計(等權)": float(-dif[dif < 0].sum()), "淨(少賠−少賺,等權)": float(dif.sum()),
              "少賠筆": int((dif > 0).sum()), "少賺筆": int((dif < 0).sum()),
              "少賠合計(金額加權)": float((a_ * dif)[dif > 0].sum()), "少賺合計(金額加權)": float(-(a_ * dif)[dif < 0].sum()),
              "淨(金額加權)": float((a_ * dif).sum()),
              "被砍大賺(>+30%)筆": int((hold > 0.30).sum()), "被砍大賺若抱滿淨報酬和": float(hold[hold > 0.30].sum()),
              "被砍大賺÷基準獲利筆淨報酬和": float(hold[hold > 0.30].sum() / base_pos) if base_pos else np.nan,
              "被砍大賺停損後淨報酬和": float(now[hold > 0.30].sum()),
              "躲掉大賠(≤−30%)筆": int((hold <= -0.30).sum()), "躲掉大賠若抱滿淨報酬和": float(hold[hold <= -0.30].sum()),
              "躲掉大賠停損後淨報酬和": float(now[hold <= -0.30].sum()), "基準獲利筆淨報酬和(等權)": float(base_pos)})
    return o


def base_pos_sum(S, x, y):
    sl = {q for _, q, _, _ in S["sells"]}
    v = np.array([S["g"][q] - COST for t, q, amt in seg_buys(S, x, y) if q in sl])
    return float(v[v > 0].sum()) if len(v) else 0.0


def trades_out(W, ev2, S, info, g0, ev0):
    df = PN.trades_df(W, ev2, S)
    qm = S["q"]; dates = W["dates"]
    df["停損"] = [bool(info["stopped"][qm[q]]) for _, q, _ in S["buys"]] if info is not None else False
    df["觸發日"] = [dates[info["trig"][qm[q]]] if (info is not None and info["trig"][qm[q]] >= 0) else "" for _, q, _ in S["buys"]]
    df["同根取較低"] = [bool(info["same_bar"][qm[q]]) for _, q, _ in S["buys"]] if info is not None else False
    df["若抱滿g"] = [g0[qm[q]] for _, q, _ in S["buys"]]
    df["原排程賣出日"] = [dates[ev0["sale"][qm[q]]] if ev0["sale"][qm[q]] >= 0 else "" for _, q, _ in S["buys"]]
    df["原排程賣價(未滑價)"] = [ev0["px"][qm[q]] for _, q, _ in S["buys"]]
    return df


def run(a, log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    PJ = json.load(open(os.path.join(SRC, "PTHn.json"), encoding="utf-8"))
    J = {"題": "使用者問停損「設 25 呢？」：52 週新高 10 檔版（補空位、抱 6 個月）加停損 −15／−20／−25／−30%", "身分": "描述（⛔ 不判、不計 N）",
         "結果句必附": SENT, "背景對照": BG, "早年註": NOTE_EARLY, "讀法": MODES, "開跑": M.now_tpe(), "對帳": {}, "閘": {}, "表": [], "拆解": []}
    TAB = []; DEC = []
    for wn in ("主", "早年"):
        W = M.build_world(wn, log)
        t0 = time.time(); RES = {}
        with Pool(a.procs) as pool:
            for sid, r in pool.imap_unordered(PTH.stock_job, [(wn, s) for s in W["sids"]], chunksize=8):
                if r is not None:
                    RES[sid] = r
        log(f"[{wn}] 逐股完 {len(RES)} 檔｜{time.time() - t0:.0f}s")
        ev, info0 = M.load_events(W, wn, "跳月", RES)
        del RES
        log(f"[查核 {wn}/跳月] 事件 {info0['列']:,} 列 ＝ stock_job 重算｜批次 {info0['批次數']}")
        LOW = low_matrix(W, wn, sorted(set(ev["sid"].tolist())), a.procs, log)
        J["閘"][f"{wn}|低價"] = f"事件股 {len(set(ev['sid'].tolist()))} 檔：research11.load_bars 開、收 ＝ 快取 O、C 逐值相同"
        cal = W["cal"]; segp = W["segp"]
        Z = np.load(os.path.join(SRC, f"eq_{wn}.npz"))
        SIM = {}; INF = {}; EV2 = {}; G0 = {}
        for slip in (False, True):
            G0[slip] = orig_g(ev, W, slip)
            SIM[("base", slip)] = PN.run_slot(ev, W, N, slip); INF[("base", slip)] = None; EV2[("base", slip)] = ev
            for mode in MODES:
                for th in THS[1:]:
                    ev2, inf = apply_stop(ev, W, th, slip, mode, LOW)
                    k = (tag(mode, th, False), slip)
                    SIM[k] = PN.run_slot(ev2, W, N, slip); INF[k] = inf; EV2[k] = ev2
        log(f"[組合 {wn}] {len(SIM)} 個組合｜{time.time() - T0:.0f}s")
        # ── 基準對帳（無停損 ＝ resultsPTHn N＝10）
        for slip in (False, True):
            S = SIM[("base", slip)]; sx = "s" if slip else ""
            for k in ("eq", "hv", "u", "pend", "nh"):
                if not np.array_equal(S[k], Z[f"N10{sx}_{k}"]):
                    raise SystemExit(f"⛔ 無停損 {wn}{sx} {k} ≠ resultsPTHn N10{sx}")
            with gzip.open(os.path.join(SRC, f"trades_{wn}_N10{sx}.csv.gz"), "rt", encoding="utf-8") as fh:
                orig = fh.read()
            if PN.df_text(PN.trades_df(W, ev, S), "%.17g") != orig:
                raise SystemExit(f"⛔ 無停損 {wn}{sx} 交易檔 ≠ resultsPTHn trades_{wn}_N10{sx}")
            J["對帳"][f"{wn}|無停損{'滑價' if slip else ''} 逐日 eq/hv/u/pend/nh、交易檔全文"] = f"逐位元相同（{len(S['buys'])} 筆）"
        # ── 統計
        for (k, slip), S in SIM.items():
            mode = "—" if k == "base" else ("close" if k.startswith("close") else "intra")
            th = None if k == "base" else -int(k[5:]) / 100.0
            typ_q = ev["typ"][S["q"]]
            for sg, (x, y) in segp.items():
                c_, m_, b = M.metrics(W, S["eq"], x, y)
                row = {"世界": wn, "讀法": MODES.get(mode, "無停損"), "門檻": thname(th), "滑價": slip, "段": sg, "窗": f"{cal[x].date()}～{cal[y].date()}",
                       "年化": c_, "回落": m_, "比值": AS.ratio(c_, m_), "0050年化": b["cagr"], "0050回落": b["mdd"],
                       "0050比值": AS.ratio(b["cagr"], b["mdd"]), "標籤": AS.label(c_, m_, b), **M.pf_stats(W, S, x, y, typ_q)}
                inf = INF[(k, slip)]
                if inf is None:
                    row.update({"觸發筆": 0, "觸發比例": 0.0})
                else:
                    bs = seg_buys(S, x, y)
                    nt = sum(1 for t, q, amt in bs if inf["stopped"][S["q"][q]])
                    row.update({"觸發筆": nt, "觸發比例": nt / len(bs) if bs else np.nan})
                TAB.append(row)
                if k == "base":
                    ref = [z for z in PJ["表"] if z["世界"] == wn and z["N"] == 10 and z["滑價"] == slip and z["段"] == sg][0]
                    bad = [kk for kk in row if kk in ref and kk not in ("世界", "段", "N") and not PN.same(row[kk], ref[kk])]
                    if bad:
                        raise SystemExit(f"⛔ 無停損 {wn}/{sg}/{slip} 統計 ≠ PTHn.json：{bad}")
                    J["對帳"][f"{wn}|無停損{'滑價' if slip else ''} {sg} 統計（{sum(1 for kk in row if kk in ref)} 欄）＝ PTHn.json"] = "逐位元相同"
                elif not slip:
                    bp = base_pos_sum(SIM[("base", False)], x, y)
                    DEC.append({"世界": wn, "讀法": MODES[mode], "門檻": thname(th), "段": sg, **decomp(S, inf, G0[False][0], G0[False][1], x, y, bp)})
        for sg, (x, y) in segp.items():
            b = RR.bench_row(cal, W["bench"], x, y + 1)
            TAB.append({"世界": wn, "讀法": "0050", "門檻": "—", "滑價": False, "段": sg, "窗": f"{cal[x].date()}～{cal[y].date()}",
                        "年化": b["cagr"], "回落": b["mdd"], "比值": AS.ratio(b["cagr"], b["mdd"])})
        # ── 存檔
        np.savez_compressed(os.path.join(OUT, f"eq_{wn}.npz"), Bc=W["Bc"], Bo=W["Bo"],
                            **{f"{k}{'s' if sl else ''}_{kk}": S[kk] for (k, sl), S in SIM.items() for kk in ("eq", "hv", "u", "pend", "nh")})
        for (k, sl), S in SIM.items():
            df = trades_out(W, EV2[(k, sl)], S, INF[(k, sl)], G0[sl][0], ev)
            with gzip.open(os.path.join(OUT, f"trades_{wn}_{k}{'s' if sl else ''}.csv.gz"), "wt", encoding="utf-8") as fh:
                df.to_csv(fh, index=False, float_format="%.17g")
        log(f"[存檔 {wn}] 完｜{time.time() - T0:.0f}s")
        del W, Z, SIM, ev, LOW, EV2
    TB = pd.DataFrame(TAB); DC = pd.DataFrame(DEC)
    TB.to_csv(os.path.join(OUT, "stop_main.csv"), index=False, float_format="%.6g", encoding="utf-8-sig")
    DC.to_csv(os.path.join(OUT, "decomp.csv"), index=False, float_format="%.6g", encoding="utf-8-sig")
    J["表"] = TAB; J["拆解"] = DEC
    pd.set_option("display.width", 260); pd.set_option("display.max_columns", 40); pd.set_option("display.max_rows", 500)
    log("[表]\n" + TB[["世界", "讀法", "門檻", "滑價", "段", "年化", "回落", "比值", "標籤", "換手每年", "成本合計每年(實付)", "平均持股(筆)",
                      "0050占淨值", "買進筆", "觸發筆", "觸發比例"]].to_string())
    log("[拆解]\n" + DC.to_string())
    log(f"[對帳] {json.dumps(J['對帳'], ensure_ascii=False)}")
    J["耗時秒"] = round(time.time() - T0); J["完成"] = M.now_tpe()
    json.dump(J, open(os.path.join(OUT, "stop.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] {J['耗時秒']}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=4)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    run(a, RA.log_to(os.path.join(OUT, "run.log")))


if __name__ == "__main__":
    main()
