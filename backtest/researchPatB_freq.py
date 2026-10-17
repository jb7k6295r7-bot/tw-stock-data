# -*- coding: utf-8 -*-
"""型態補條件 B 組 seq1【頻率表】（台股策略線 單筆層登錄 sha 15b61be1b85b426d，2026-10-17 09:38；裁定 seq360 §二 定 N_前段 ＋2：
只做做多兩格；向下兩格 ⛔ 不做）——回測線計算子代理。⛔ 只數事件日期與個數、剔除計數、n_eff、每檔每年次數、原版第 3 根確認比例；
⛔ 不讀、不算、不存任何 T＋1 以後的價格或報酬。⛔ 不 commit、不改既有程式與結果夾；patterns_all.py（PREREG型態全量偵測器）⛔ 只 import、不改。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPatB_freq [--procs 3]
輸出 backtest/resultsPatB/freq/：freq.json、freq.csv、freq_by_year.csv、confirm.csv、per_stock_year.csv、events_<世界>_<段>_<格>.csv.gz、run.log

四格：
  B1 三內向上（判定）：第 1、2 根 ＝ PA.detect_kbars 的 K25 多頭母子線原樣（長黑＋白、top2≤top1、bot2≥bot1、B2＜B1；r10＜0 在第 1 根前一日；
     B̄ 容忍參數、A2～A5、B13 全照 patterns_all，⛔ 不另寫偵測）；第 3 根 ＝ 第 2 根的下一根有效 K 棒：PA.kbar_feats 的 wh（白 K，還原 C＞O）
     且 還原收盤 C3 ＞ C1 ⇒ T ＝ 第 3 根、first ＝ 第 1 根。
  B2 三外向上（判定）：第 1、2 根 ＝ K56 多頭吞噬原樣；第 3 根：C3 ＞ C2 ⇒ T ＝ 第 3 根、first ＝ 第 1 根。
  K25、K56（描述對照，⛔ 不判）：原版兩根就成立、T ＝ 第 2 根、first ＝ 第 1 根。

═══ 讀法（Q 標；登錄沒寫清楚、執行者補的都在這裡；⛔ 在看任何本件數字之前寫死；★＝兩種讀法擇一，〔 〕內為另一讀法）═══
 Q1 世界、母體、壞根 ＝ C 組 researchPatC_freq 同（researchAscTri_freq.load_world 原樣、⛔ 不另寫資料層）：主 ＝ rerun17 快照 H2D edc6f8002f
    （2015-01-05～2026-09-24）；早年 ＝ ~/earlydata/eotc_f65bb03e11（2004-02-11～2014-12-31）；股票 ＝ ~/rluwork/world_{main,early}.pkl sids
    （UG.gate3 GATE_V2 開 ∩ 四碼、首碼 1～9、非 91xx、含已下市）；research11.load_bars ＜ 260 根的股票不進。
    壞根 ＝ load_bars next_bad（缺口 ≥ 5 日、價格斷點、幽靈還原）∪ ~/crashwork/bad_*.pkl ∪ 早年 researchAddOn.early_extra_bad（reduce_v2）。
 Q2 偵測輸入 ＝ researchPatAll_freq.one_stock／detect_calendar 同一條：還原 OHLCV ＝ D.load_stock df（＝ load_bars 的 df）；原始 OHLC ＝
    researchPatAll_freq.load_raw 原樣；有效 K 棒 ＝ 還原收盤非缺值；PA.detect_kbars 在有效 K 棒序列上跑，T、first 換回日曆位置。
    ★ 第 3 根 ＝ 第 2 根之後的下一根有效 K 棒（A1：幾何在有效 K 棒序列上數）；第 2 根是最後一根 ⇒ 不成立。
    ★ B1 白 K 用 PA.kbar_feats 的 wh（＝ 還原 C＞O 且當根還原與原始 OHLC 全非缺值，同偵測器 wh 的定義）；
    ★ B2 第 3 根只要求 C3 ＞ C2（登錄逐字；⛔ 不要求顏色、不要求 OHLC 全非缺值）。
 Q3 判定窗、合併、剔除、n_eff ＝ C 組 Q2～Q4 原樣：主全窗 ＝ T ∈ [2017-03-02, 資料尾 − 20]；探索 [2017-03-02, 2021-12-30]｜
    確認 [2022-01-03, 資料尾 − 20]｜早年 [2005 第一個交易日, 2014-12-31 − 20]（交易日曆）。⭐「依構造不可判定」以【主全窗 H20】n_eff 判；
    分段只報。同檔同格依 T 先合併（T ∈ (t0, t0＋20]）、再剔除（pit 無效 → 硬斷點［first, T＋H］→ T＋1 停牌 → T＋1 開盤漲停 → T＋1 開盤跌停）；
    first ＝ 型態第 1 根（四格同）。n_eff H20 ＝ min(保留數, 有保留事件的曆月數)；H60 ＝ min(保留數, (T − 段起點)//60 區段數)（只描述）。
 Q4 每檔每年（PatAll Q6 同式）：分子 ＝ 該檔該段 H20 保留數；分母 ＝ 該檔在 [段起點, 段尾有效端] 內首個到最後一個有效 K 棒所跨交易日數 ÷
    該段每年交易日數；報合併母體比率（總保留 ÷ 總股票年）與曝露 ≥ 1 年股票的平均／中位／p90（含零事件者）。⚠ 分母未扣 pit 無效日（描述）。
 Q5 原版第 3 根確認比例（先驗②）：K25（K56）事件中，下一根有效 K 棒滿足 B1（B2）第 3 根條件者的比例；分兩個口徑報：
    ① 原始（窗內、合併前，依原版 T 入窗）② H20 保留（原版自己的合併／剔除後）。另報「確認版保留 ÷ 原版保留」（＝ 先驗②要 ≤ 0.5）。
 Q6 對帳（researchPatB_freq_check.py）：主世界 K25、K56 的窗內原始 (sid, T, first) 與已提交 resultsPatAll/events_K25、K56（PatAll 頻率階段，
    同一快照；窗 [2017-03-02, 2026-08-24 往前 20 個交易日]）兩邊都有的股票逐筆比；PatAll 母體是 gate3 v1、無 260 根門檻 ⇒ 名單差另報、不算差異。
"""
from __future__ import annotations

import argparse
import glob
import gzip
import hashlib
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchAscTri_freq as AT              # noqa: E402  load_world 原樣（⛔ 只 import）
from backtest import research11 as R                        # noqa: E402
from backtest import patterns_all as PA                     # noqa: E402  偵測器（⛔ 只 import）
from backtest import universe_gate as UG                    # noqa: E402
import researchPatAll_freq as RPF                           # noqa: E402  load_raw 原樣（⛔ 只 import）

UG.set_gate_v2(True)

REG_SHA = "15b61be1b85b426d"
MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
OUT = "backtest/resultsPatB/freq"
HS = (20, 60)
MERGE = 20
NEFF_MIN = 30
SEGS = {"主": {"主全窗": ("2017-03-02", None), "探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", None)},
        "早年": {"早年": ("2005-01-01", "2014-12-31")}}
CELLS = {"B1": "三內向上（K25＋第3根白K且C3>C1）", "B2": "三外向上（K56＋第3根C3>C2）",
         "K25": "原版 多頭母子線（描述對照）", "K56": "原版 多頭吞噬（描述對照）"}
JUDGE = {"B1": "K25", "B2": "K56"}
ST = ["保留", "合併掉", "剔除_pit無效", "剔除_硬斷點", "剔除_T+1停牌", "剔除_T+1開盤漲停", "剔除_T+1開盤跌停"]
_G: dict = {}
LOG: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def reg_check():
    fs = [f for f in glob.glob(os.path.join(MAILBOX, "*.md")) if f"sha{REG_SHA}" in os.path.basename(f)]
    if len(fs) != 1:
        raise SystemExit(f"⛔ 信箱找不到唯一一封登錄全文 sha{REG_SHA}：{fs}")
    b = open(fs[0], "rb").read()
    h = hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]
    if h != REG_SHA:
        raise SystemExit(f"⛔ 登錄 sha {h} ≠ {REG_SHA}")
    return os.path.basename(fs[0])


def detect_b(o, h, l, c, ro, rh, rl, rc):
    """有效 K 棒序列 ⇒ {格: [(T_bar, first_bar, conf)]}；K25／K56 的 conf ＝ 下一根是否滿足 B1／B2 第 3 根條件。"""
    K = PA.detect_kbars(o, h, l, c, ro, rh, rl, rc)
    F = PA.kbar_feats(o, h, l, c, ro, rh, rl, rc)
    n = len(c); wh = F["wh"]
    out = {k: [] for k in CELLS}
    for base, cell in (("K25", "B1"), ("K56", "B2")):
        for T in K[base]["T"]:
            T = int(T); f1 = T - 1; t3 = T + 1
            if t3 < n:
                if cell == "B1":
                    conf = bool(wh[t3] and c[t3] > c[f1])
                else:
                    conf = bool(c[t3] > c[T])
            else:
                conf = False
            out[base].append((T, f1, conf))
            if conf:
                out[cell].append((t3, f1, True))
    return out


def stock_job(a):
    wn, sid = a
    W = _G[wn]; cal = W["cal"]; n0 = W["n0"]; i = W["ix"][sid]
    import backtest.data as D
    D.DATA = W["data"]
    B = R.load_bars(sid, W["mk"].get(sid, "twse"), cal)
    if B is None:
        return sid, None
    df = B["df"]; idx = B["idx"].astype(np.int64); nb = len(idx)
    if len(df) != n0:
        raise SystemExit(f"⛔ {wn} {sid} df 長 {len(df)} ≠ 日曆 {n0}")
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    ro, rh, rl, rc = RPF.load_raw(sid, cal)
    bars = np.flatnonzero(np.isfinite(c))
    if not (len(bars) == nb and (bars == idx).all()):
        raise SystemExit(f"⛔ {wn} {sid}：有效 K 棒（還原收盤非缺）≠ load_bars idx")
    sel = lambda x: x[bars]
    EVb = detect_b(sel(o), sel(h), sel(l), c[bars], sel(ro), sel(rh), sel(rl), sel(rc))
    EV = {k: [(int(bars[t]), int(bars[f]), cf) for t, f, cf in v] for k, v in EVb.items()}
    # ── 母體／剔除材料（C 組同）
    bad = np.asarray(B["next_bad"][:nb] == np.arange(nb), bool)
    for p_ in W["BADPOS"].get(sid, ()):
        k = int(np.searchsorted(idx, p_, "left"))
        if k < nb:
            bad[k] = True
    CB = np.r_[0, np.cumsum(bad)]
    PV = W["PV"][i]; TRD = W["TRD"][i]; O = W["O"][i]; UPL = W["UPL"][i]; DNL = W["DNL"][i]

    def brk(fpos, endpos):
        kf = int(np.searchsorted(idx, fpos, "left")); kH = int(np.searchsorted(idx, endpos, "right")) - 1
        if kH >= kf and CB[kH + 1] - CB[kf] > 0:
            return True
        if 0 <= kH < nb - 1 and idx[kH + 1] - idx[kH] - 1 >= 5 and endpos - idx[kH] >= 5:
            return True
        return False

    out = {}; expo = {}
    for seg_w, (w0, wend) in W["win"].items():
        we = min(wend, n0 - 1 - HS[0])
        expo[seg_w] = max(0, min(int(idx[-1]), we) - max(int(idx[0]), w0) + 1)
        for cell, evs in EV.items():
            d = {t: (fi, cf) for t, fi, cf in evs}
            Ts = [t for t in sorted(d) if w0 <= t <= n0 - 1 - HS[0] and t <= wend]
            rows = []; t0 = -10 ** 9
            for t in Ts:
                merged = t0 < t <= t0 + MERGE
                if not merged:
                    t0 = t
                st = {}
                for H in HS:
                    if t + H > n0 - 1:
                        st[H] = "窗外"; continue
                    if merged:
                        st[H] = "合併掉"; continue
                    e1 = t + 1
                    if not bool(PV[t]):
                        st[H] = "剔除_pit無效"
                    elif brk(d[t][0], t + H):
                        st[H] = "剔除_硬斷點"
                    elif not (bool(TRD[e1]) and np.isfinite(O[e1]) and O[e1] > 0):
                        st[H] = "剔除_T+1停牌"
                    elif bool(UPL[e1]):
                        st[H] = "剔除_T+1開盤漲停"
                    elif bool(DNL[e1]):
                        st[H] = "剔除_T+1開盤跌停"
                    else:
                        st[H] = "保留"
                rows.append({"sid": sid, "T": int(t), "first": int(d[t][0]), "conf": bool(d[t][1]), "st20": st[20], "st60": st[60]})
            out[(seg_w, cell)] = rows
    return sid, {"rows": out, "expo": expo}


def qd(x):
    x = np.asarray(x, float)
    if len(x) == 0:
        return {"n": 0}
    return {"n": int(len(x)), "平均": round(float(x.mean()), 4), "中位": round(float(np.median(x)), 4),
            "p90": round(float(np.percentile(x, 90)), 4), "零事件佔比": round(float((x == 0).mean()), 4)}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    t0 = time.time()
    out_dir = OUT if a.limit is None else os.path.join(OUT, "_try")
    os.makedirs(out_dir, exist_ok=True)
    reg = reg_check()
    log(f"[登錄] {reg}（sha {REG_SHA} 已驗）")
    J = {"性質": "型態補條件 B 組 seq1 頻率表（⛔ 未讀、未算任何報酬）", "登錄": f"台股策略線 seq1 sha {REG_SHA}",
         "裁定": "seq360 §二 只做做多兩格、N_前段 ＋2；n_eff ＜ 30 ⇒ 依構造不可判定、不計 N", "世界": {}, "格": CELLS}
    FREQ = []; YR = []; CONF = []; PSY = []
    for wn in ("主", "早年"):
        W = AT.load_world(wn); cal = W["cal"]; n0 = W["n0"]
        win = {}
        for sg, (x, y) in SEGS[wn].items():
            p0 = int(cal.searchsorted(pd.Timestamp(x)))
            p1 = n0 - 1 if y is None else int(cal.searchsorted(pd.Timestamp(y), side="right")) - 1
            win[sg] = (p0, p1)
        W["win"] = win; _G[wn] = W
        sids = W["sids"][:a.limit] if a.limit else W["sids"]
        res = {}
        with Pool(a.procs) as pool:
            for k_, (sid, r) in enumerate(pool.imap_unordered(stock_job, [(wn, s) for s in sids], chunksize=8)):
                res[sid] = r
                if (k_ + 1) % 300 == 0:
                    log(f"  {wn} … {k_ + 1}／{len(sids)}｜{time.time() - t0:.0f}s")
        ok = {s: r for s, r in res.items() if r is not None}
        n_skip = len(res) - len(ok)
        log(f"[{wn}] 逐股完｜load_bars 不足 260 根 {n_skip} 檔｜{time.time() - t0:.0f}s")
        Wj = {"資料": W["data"], "日曆": [str(cal[0].date()), str(cal[-1].date())], "閘": W["gate"], "壞根": W["bad_info"],
              "檔數": len(sids), "load_bars不足260根檔數": n_skip, "段": {}}
        ym = np.array([d.strftime("%Y-%m") for d in cal])
        for sg, (p0, p1) in win.items():
            pe = min(p1, n0 - 1 - 20)
            yrs_seg = (cal[pe] - cal[p0]).days / 365.25
            dpy = (pe - p0 + 1) / yrs_seg
            ex = pd.Series({s: r["expo"][sg] for s, r in ok.items()}, dtype=float)
            syr = ex / dpy
            segj = {}
            for cell in CELLS:
                rows = [x for r in ok.values() for x in r["rows"][(sg, cell)]]
                j = {}
                for H in HS:
                    key = f"st{H}"
                    inw = [x for x in rows if x[key] != "窗外"]
                    kept = [x for x in inw if x[key] == "保留"]
                    acc = {s_: sum(1 for x in inw if x[key] == s_) for s_ in ST}
                    if H == 20:
                        units = len({ym[x["T"]] for x in kept}); unit = "曆月"
                    else:
                        units = len({(x["T"] - p0) // 60 for x in kept}); unit = "60日區段"
                    ne = min(len(kept), units)
                    j[f"H{H}"] = {"原始": len(inw), "合併後": len(inw) - acc["合併掉"], **acc, "去重後n(保留)": len(kept),
                                  "相異檔數": len({x["sid"] for x in kept}), f"有事件{unit}": units, "n_eff": ne,
                                  "逐年原始": dict(sorted(pd.Series([cal[x["T"]].year for x in inw]).value_counts().to_dict().items())) if inw else {},
                                  "逐年保留": dict(sorted(pd.Series([cal[x["T"]].year for x in kept]).value_counts().to_dict().items())) if kept else {}}
                # 每檔每年（H20 保留）
                kc = pd.Series([x["sid"] for x in rows if x["st20"] == "保留"]).value_counts() if rows else pd.Series(dtype=float)
                kc = kc.reindex(ex.index).fillna(0)
                pooled = float(kc.sum() / syr.sum()) if syr.sum() > 0 else None
                rate = (kc / syr.where(syr > 0))[syr >= 1.0].fillna(0)
                j["每檔每年_H20"] = {"合併母體比率": round(pooled, 4) if pooled is not None else None, "曝露≥1年": qd(rate.to_numpy()),
                                  "總股票年": round(float(syr.sum()), 1)}
                PSY.append({"世界": wn, "段": sg, "格": cell, "合併母體比率": j["每檔每年_H20"]["合併母體比率"], **{f"曝露≥1年_{k}": v for k, v in j["每檔每年_H20"]["曝露≥1年"].items()},
                            "總股票年": j["每檔每年_H20"]["總股票年"]})
                segj[cell] = j
                row = {"世界": wn, "段": sg, "格": cell, "說明": CELLS[cell], "期間": f"{cal[p0].date()}～{cal[pe].date()}"}
                for H in HS:
                    q = j[f"H{H}"]
                    for kk in ("原始", "合併後", "剔除_pit無效", "剔除_硬斷點", "剔除_T+1停牌", "剔除_T+1開盤漲停", "剔除_T+1開盤跌停",
                               "去重後n(保留)", "相異檔數", "n_eff"):
                        row[f"{kk}_H{H}"] = q[kk]
                    row[f"有事件{'曆月' if H == 20 else '60日區段'}_H{H}"] = q[f"有事件{'曆月' if H == 20 else '60日區段'}"]
                row["每年保留_H20"] = round(j["H20"]["去重後n(保留)"] / yrs_seg, 2) if yrs_seg > 0 else None
                row["每檔每年_H20(合併母體)"] = j["每檔每年_H20"]["合併母體比率"]
                row["n_eff<30"] = j["H20"]["n_eff"] < NEFF_MIN
                FREQ.append(row)
                for y, nraw in j["H20"]["逐年原始"].items():
                    YR.append({"世界": wn, "段": sg, "格": cell, "年": int(y), "原始_H20": int(nraw), "保留_H20": int(j["H20"]["逐年保留"].get(y, 0))})
            # 原版第 3 根確認比例（Q5）
            for cell, base in JUDGE.items():
                rb = [x for r in ok.values() for x in r["rows"][(sg, base)]]
                raw_n = len(rb); raw_c = sum(1 for x in rb if x["conf"])
                kb = [x for x in rb if x["st20"] == "保留"]; k_c = sum(1 for x in kb if x["conf"])
                nB = segj[cell]["H20"]["去重後n(保留)"]; nK = segj[base]["H20"]["去重後n(保留)"]
                rB = segj[cell]["H20"]["原始"]; rK = segj[base]["H20"]["原始"]
                c_ = {"原版": base, "確認版": cell, "原版原始(窗內)": raw_n, "其中第3根確認": raw_c,
                      "確認比例_原始": round(raw_c / raw_n, 4) if raw_n else None,
                      "原版H20保留": len(kb), "其中第3根確認_保留": k_c, "確認比例_保留": round(k_c / len(kb), 4) if kb else None,
                      "確認版原始÷原版原始": round(rB / rK, 4) if rK else None, "確認版保留÷原版保留": round(nB / nK, 4) if nK else None}
                c_["先驗②(確認版保留比原版少50%以上)"] = (c_["確認版保留÷原版保留"] is not None and c_["確認版保留÷原版保留"] <= 0.5)
                segj[cell]["對原版"] = c_
                CONF.append({"世界": wn, "段": sg, **c_})
            Wj["段"][sg] = segj
            log(f"[{wn}/{sg}] " + "｜".join(f"{c_} 原始={segj[c_]['H20']['原始']} n={segj[c_]['H20']['去重後n(保留)']} n_eff={segj[c_]['H20']['n_eff']}" for c_ in CELLS)
                + "｜確認比例(原始) " + "、".join(f"{b}:{segj[c]['對原版']['確認比例_原始']}" for c, b in JUDGE.items()))
            for cell in CELLS:
                rows = sorted([x for r in ok.values() for x in r["rows"][(sg, cell)]], key=lambda x: (x["T"], x["sid"]))
                if not rows:
                    continue
                dfo = pd.DataFrame([{"sid": x["sid"], "T": str(cal[x["T"]].date()), "first": str(cal[x["first"]].date()),
                                     **({"第3根確認": x["conf"]} if cell in ("K25", "K56") else {}),
                                     "狀態_H20": x["st20"], "狀態_H60": x["st60"]} for x in rows])
                with gzip.open(os.path.join(out_dir, f"events_{wn}_{sg}_{cell}.csv.gz"), "wt", encoding="utf-8") as fh:
                    dfo.to_csv(fh, index=False)
        J["世界"][wn] = Wj
    jd = {}
    for cell in JUDGE:
        ne = J["世界"]["主"]["段"]["主全窗"][cell]["H20"]["n_eff"]
        jd[cell] = {"格": CELLS[cell], "主全窗H20_n_eff": ne, "判斷": "依構造不可判定、不計 N" if ne < NEFF_MIN else "照判",
                    "分段n_eff(只報)": {sg: J["世界"][w]["段"][sg][cell]["H20"]["n_eff"] for w in ("主", "早年") for sg in SEGS[w] if sg != "主全窗"}}
    J["判斷"] = jd
    J["N"] = {"登錄記 N_前段": 2, "照判格數": sum(1 for v in jd.values() if v["判斷"] == "照判"),
              "依構造不可判定(不計N)格數": sum(1 for v in jd.values() if v["判斷"] != "照判")}
    J["n_eff<30的格(含分段、描述格)"] = [f"{r['世界']}/{r['段']}/{r['格']} n_eff={r['n_eff_H20']}" for r in FREQ if r["n_eff<30"]]
    J["讀法"] = __doc__.split("═══ 讀法")[1]
    J["時間"] = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")
    pd.DataFrame(FREQ).to_csv(os.path.join(out_dir, "freq.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(YR).to_csv(os.path.join(out_dir, "freq_by_year.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(CONF).to_csv(os.path.join(out_dir, "confirm.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(PSY).to_csv(os.path.join(out_dir, "per_stock_year.csv"), index=False, encoding="utf-8-sig")
    json.dump(J, open(os.path.join(out_dir, "freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[判斷] {json.dumps(jd, ensure_ascii=False)}｜{time.time() - t0:.0f}s")
    open(os.path.join(out_dir, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
