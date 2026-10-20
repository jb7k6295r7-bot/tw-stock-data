# -*- coding: utf-8 -*-
"""出場第三輪 seq1【頻率表・乾跑】（台股策略線 登錄 sha 3180c03723d875e3，2026-10-20 20:08；裁定 seq403 發號 N_前段 ＋7（S+ 3、S0 2、S− 2），
「先交頻率表（三狀態 × 兩策略 × 三段事件數、n_eff、改放 0050 比例），裁定線過目後開跑」）——回測線計算子代理。
⛔ 只數事件、n_eff、候選有無、構造與先後關係；⛔ 不算任何出場法的報酬、d、帳戶報酬，⛔ 不存任何報酬數值。
   狀態本身由「持有中未實現報酬是否穿越 ±15%」定義（登錄 §二）⇒ 只用來決定事件日 T，只存布林與日期；S0 ②③ 先突破、S− ② 先後也只存日期先後。
⛔ 不 commit、不改既有程式與結果夾；引擎 research11.simulate_mtm ⛔ 不改，經 researchYL_integrate.main_world／early_world／eng 原樣呼叫（營量 v1 ＝ YL、營飆 v1 ＝ YF）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchExit3_freq [--procs 2]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchExit3_freq_check
輸出 backtest/resultsExit3/freq/：freq.json、freq.csv、cells.csv、seeds_dist.csv、equiv.csv、events_r0.csv.gz、trades_r0.csv.gz、run.log

═══ 讀法（Q 標；登錄沒寫清楚、執行者補的都在這裡；⛔ 在看任何本件數字之前寫死；★＝執行者定，〔 〕內為另一讀法）═══
 Q1 母體（登錄 §二）：營量 v1 ＝ IG.eng(W, YL, 0)（SIG[無閘]、H60、20 槽、relvol、default_rng(7000)）；營飆 v1 ＝ IG.eng(W, YF, r)（SIG[閘]、H120、10 槽、抽籤 default_rng(1000＋r)），
    主報 r ＝ 0、另報 r ＝ 0～199 的事件數分布；停止交易強制出場開（W["SF"]）。世界 ＝ main_world（主：進場 2017-03-02～2026-08-24）、early_world（早年：2005-02-01～2014-12-31）。
    交易清單 ＝ 引擎 audit 的 buy／sell 依代號時序配對：進場日 e ＝ buy 的 t、買價 bp ＝ buy 的 px（還原開盤）、出清日 x ＝ sell 的 t（排程出場 ＝ 第 H 日收盤賣，sell t ＝ xpos；
    停止交易 ＝ L＋1）；資料尾還沒賣 ⇒ x ＝ 日曆長度（＝ 資料尾之後）。
 Q2 未實現報酬 r(t) ＝ W["closes"][sid][t] ÷ bp − 1（引擎同一份還原收盤、ffill；停牌日 ＝ 前一收盤）；t 從 e（進場日收盤）起。
    事件日 T 必須 ＜ x（T 收盤判、T＋1 起執行；T ＝ x 當天原規則已收盤賣 ⇒ 不算，登錄「事件日若已過原策略的出場日 ⇒ 不算」）。
    ★ 壞根截斷（seq335）：(e, x] 內第一個壞根 kb（主 ~/crashwork/bad_main.pkl；早年 bad_early.pkl ∪ researchAddOn.early_extra_bad）⇒ T ≤ kb − 1（之後價格跨斷點不判；筆數照報）。
    S+ ＝ 第一個 r ≥ +15% 的 T；S− ＝ 第一個 r ≤ −15% 的 T；S0_N ＝ T ＝ e＋N−1（e 算第 1 日，日曆位置），且 [e, T] 每天 −15% ＜ r ＜ +15%；N ＝ 40 判、30／60 並報。
    同一筆可依序產生多個狀態，各自一個事件（重疊照報）。
 Q3 段 ＝ 依事件日 T（登錄 §四 CI 事件月分群）：探索 2017-03-02～2021-12-30｜確認 2022-01-03～資料尾｜早年 2005-02-01～2014-12-31（描述，附 reduce_v2 註）。
    n_eff ＝ min(事件數, 有事件的曆月數)；n_eff ＜ 30 ⇒ 依構造不可判定。合併 ＝ 營量 r0 ＋ 營飆 r0 的事件直接相加（兩個帳戶，同股同日兩邊都有照算兩件；重複數照報）。
    7 格（S+ ②③④、S0 ②③、S− ②③）的 n_eff ＝ 該狀態的 n_eff（同一批事件）；整格可判 ＝ 合併的探索、確認兩段 n_eff 都 ≥ 30。
 Q4 對照①「立即換下一檔」的候選（登錄 §三）：執行日 X ＝ T＋1（日曆位置；超出資料 ⇒ 另列）；候選 ＝ 同策略訊號表（營量 SIG[無閘]、營飆 SIG[閘]）中 entry_pos ＝ X 的列
    （＝ 每日名單「已達成」＝ 前一天 T 收盤的 AND 訊號，daily_list 同義）的代號，扣掉 ① 事件股自己、② X 當天該帳戶（同顆種子）仍持有者（e ≤ X ＜ x，含引擎當天已買進者）。
    候選 ≥ 1 ⇒「有候選」；0 ⇒「改放 0050」。
 Q5 S0 ②③ 等價（seq377）：整理區上緣 ＝ [e, T] 最高收盤、下緣 ＝ 最低收盤；看 (T, 終點]，終點 ＝ min(T＋120, 資料尾, 該股 T 之後第一個壞根前一根)：
    先突破 ＝ 有某天收盤 ＞ 上緣，且早於第一個收盤 ＜ 下緣的日子（或從未跌破）；先突破比例 ＜ 10% ⇒ 標「③ 近乎等於 ②」。N ＝ 30／40／60 都報。
    S+ ④ 與 ③：④ ＝ 一半立即換（＝①）＋ 一半照 ③ ⇒ d(④) ＝ ½ d(③) 為構造恆等（同一事件、同終點、成本同扣），⛔ 不當新證據（照報，不另算）。
    S− ②：(T, 終點] 內「r ≥ −5%」第一天與「收盤 ≥ 20 日均線」第一天的先後（★ 20 日均線 ＝ 日曆上最近 20 個交易日 ffill 收盤平均，停牌日以前收盤計入）。
 Q6 天數軸：終點 T＋120 判（60、250 描述）⇒ 頻率表另報 T＋60／120／250 超出資料尾的事件數。
"""
from __future__ import annotations

import argparse
import glob
import gzip
import hashlib
import json
import os
import pickle
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchYL_integrate as IG             # noqa: E402  main_world、early_world、eng、YL、YF（⛔ 只 import）
from backtest import researchAddOn as RA                    # noqa: E402  early_extra_bad、WORK、CRASH_WORK
from backtest import data as D                              # noqa: E402

REG_SHA = "3180c03723d875e3"
MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
OUT = "backtest/resultsExit3/freq"
THR = 0.15
S0N = (30, 40, 60)
ENDS = (60, 120, 250)
NSEED = 200
NEFF_MIN = 30
STR = {"營量": {"key": IG.YL, "G": False, "H": 60}, "營飆": {"key": IG.YF, "G": True, "H": 120}}
SEGS = {"主": {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", None)}, "早年": {"早年": ("2005-02-01", "2014-12-31")}}
STATES = ["S+", "S0_30", "S0_40", "S0_60", "S−"]
_G: dict = {}
LOG: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def reg_check():
    fs = [f for f in glob.glob(os.path.join(MAILBOX, "*.md")) if f"sha{REG_SHA}" in os.path.basename(f) and os.path.basename(f).startswith("登錄全文")]
    if not fs:
        raise SystemExit(f"⛔ 信箱找不到登錄全文 sha{REG_SHA}")
    for f in fs:
        b = open(f, "rb").read()
        h = hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]
        if h != REG_SHA:
            raise SystemExit(f"⛔ 登錄 sha {h} ≠ {REG_SHA}（{f}）")
    return os.path.basename(fs[0])


def trades_of(au, ncal):
    """audit ⇒ DataFrame(sid, e, bp, x)；依代號時序配對 buy／sell。"""
    buys = {}; rows = []
    for a in sorted(au, key=lambda z: (z["t"], 0 if z["side"] == "sell" else 1)):
        if a["side"] == "buy":
            if a["sid"] in buys:
                raise SystemExit(f"⛔ {a['sid']} 未賣先買")
            buys[a["sid"]] = (int(a["t"]), float(a["px"]))
        else:
            e, bp = buys.pop(a["sid"])
            rows.append((a["sid"], e, bp, int(a["t"])))
    for s, (e, bp) in buys.items():
        rows.append((s, e, bp, ncal))
    return pd.DataFrame(rows, columns=["sid", "e", "bp", "x"]).sort_values(["e", "sid"]).reset_index(drop=True)


def events_of(T, W, BAD, last, detail=False):
    """每筆交易 ⇒ 事件（狀態、T）。last ＝ 資料最後一個日曆位置。"""
    cl = W["closes"]; out = []; ntrunc = 0
    for s, e, bp, x in zip(T["sid"], T["e"], T["bp"], T["x"]):
        c = cl[s]
        hi = min(int(x) - 1, last)
        bb = BAD.get(s)
        if bb is not None:
            kk = bb[(bb > e) & (bb <= min(int(x), last))]
            if len(kk):
                ntrunc += 1; hi = min(hi, int(kk[0]) - 1)
        if hi < e:
            continue
        r = c[e:hi + 1] / bp - 1.0
        up = np.flatnonzero(r >= THR); dn = np.flatnonzero(r <= -THR)
        if len(up):
            out.append((s, e, int(x), "S+", e + int(up[0])))
        if len(dn):
            out.append((s, e, int(x), "S−", e + int(dn[0])))
        first_out = min(int(up[0]) if len(up) else 10 ** 9, int(dn[0]) if len(dn) else 10 ** 9)
        for N in S0N:
            Tn = e + N - 1
            if Tn <= hi and first_out > N - 1:
                out.append((s, e, int(x), f"S0_{N}", Tn))
    E = pd.DataFrame(out, columns=["sid", "e", "x", "狀態", "T"])
    return E, ntrunc


def seg_of(W, wn):
    cal = W["cal"]; out = {}
    for sg, (a, b) in SEGS[wn].items():
        x = int(cal.searchsorted(pd.Timestamp(a)))
        y = len(cal) - 1 if b is None else int(cal.searchsorted(pd.Timestamp(b), side="right")) - 1
        out[sg] = (x, y)
    return out


def summarize(E, W, wn, tag):
    rows = []
    cal = W["cal"]
    for sg, (x, y) in seg_of(W, wn).items():
        for st in STATES:
            sub = E[(E["狀態"] == st) & (E["T"] >= x) & (E["T"] <= y)]
            n = len(sub); mo = sub["T"].map(lambda t: cal[t].strftime("%Y-%m")).nunique() if n else 0
            rows.append({**tag, "世界": wn, "段": sg, "狀態": st, "事件": n, "有事件曆月": int(mo), "n_eff": int(min(n, mo)),
                         "相異交易": int(sub[["sid", "e"]].drop_duplicates().shape[0]) if n else 0})
    return rows


def cand_info(E, T, SIG, ncal_cal):
    """Q4：每個事件執行日 X ＝ T＋1 的候選數（扣自己、扣同帳戶持有）。"""
    by = SIG.groupby("entry_pos")["sid"].apply(list).to_dict()
    Ee = T["e"].to_numpy(); Ex = T["x"].to_numpy(); Es = T["sid"].to_numpy()
    nc = []
    for s, t in zip(E["sid"], E["T"]):
        X = int(t) + 1
        if X > ncal_cal - 1:
            nc.append(-1); continue
        cand = by.get(X, [])
        if not cand:
            nc.append(0); continue
        held = set(Es[(Ee <= X) & (Ex > X)])
        nc.append(sum(1 for c in cand if c != s and c not in held))
    return np.array(nc, int)


def seed_job(a):
    wn, r = a
    W = _G[wn]
    o, au = IG.eng(W, STR["營飆"]["key"], r, audit=True)
    return wn, r, trades_of(au, len(W["cal"])), IG.sha(o["equity"])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); ap.add_argument("--seeds", type=int, default=NSEED)
    a = ap.parse_args()
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    reg = reg_check()
    log(f"[登錄] {reg}（sha {REG_SHA} 已驗）")
    J = {"性質": "出場第三輪 seq1 頻率表乾跑（⛔ 未算任何出場法報酬、d、帳戶報酬）", "登錄": f"台股策略線 seq1 sha {REG_SHA}",
         "裁定": "seq403 發號 N_前段 ＋7（S+ 3、S0 2、S− 2；Bonferroni 7 格）；先交頻率表、裁定線過目後開跑"}
    WS = {}
    WS["主"], g1 = IG.main_world(log)
    WS["早年"], g2 = IG.early_world(log, a.procs)
    J["世界閘"] = {**g1, **g2}
    # 壞根
    BAD = {}
    for wn, part in (("主", "main"), ("早年", "early")):
        B = pickle.load(open(os.path.join(RA.CRASH_WORK, f"bad_{part}.pkl"), "rb"))
        BAD[wn] = {s: set(int(x) for x in a_) | set(int(x) for x in b_) for s, (a_, b_) in B.items()}
        D.DATA = WS[wn]["data"]
        cal_chk = D.load_calendar()
        if not (len(cal_chk) == len(WS[wn]["cal"]) and (cal_chk == WS[wn]["cal"]).all()):
            raise SystemExit(f"⛔ {wn} 壞根快取日曆 ≠ 引擎世界日曆")
    Wa = pickle.load(open(os.path.join(RA.WORK, "world_早年.pkl"), "rb"))
    if not (len(Wa["cal"]) == len(WS["早年"]["cal"]) and (Wa["cal"] == WS["早年"]["cal"]).all()):
        raise SystemExit("⛔ 早年 addonwork 日曆 ≠ 引擎世界日曆")
    EX, excnt = RA.early_extra_bad(Wa, lambda *x: None)
    for s, ks in EX.items():
        BAD["早年"].setdefault(s, set()).update(int(k) for k in ks)
    BAD = {wn: {s: np.array(sorted(v), np.int64) for s, v in d.items()} for wn, d in BAD.items()}
    log(f"[壞根] 主 {sum(len(v) for v in BAD['主'].values())}｜早年 {sum(len(v) for v in BAD['早年'].values())}（含 reduce_v2／R8 {excnt}）")
    # ── r0 兩策略
    FREQ = []; DET = []; TR0 = []; EQV = {}; CAND = []
    for wn in ("主", "早年"):
        W = WS[wn]; cal = W["cal"]; last = len(cal) - 1
        for sn, S in STR.items():
            o, au = IG.eng(W, S["key"], 0, audit=True)
            T = trades_of(au, len(cal))
            chk = W["SIG"][S["G"]].set_index(["sid", "entry_pos"])[f"xpos_H{S['H']}"]
            xs = np.array([chk.get((s, e), -9) for s, e in zip(T["sid"], T["e"])])
            nd = int(((xs != T["x"].to_numpy()) & (T["x"].to_numpy() < len(cal))).sum())
            log(f"[{wn}·{sn} r0] 交易 {len(T)}（引擎 trades {o['trades']}）｜eq_sha {IG.sha(o['equity'])}｜sell t ≠ 訊號表 xpos {nd} 筆（停止交易強制等）｜資料尾未賣 {int((T['x'] >= len(cal)).sum())}")
            E, ntr = events_of(T, W, BAD[wn], last)
            E["策略"] = sn; E["世界"] = wn
            # 段標
            segp = seg_of(W, wn)
            E["段"] = ""
            for sg, (x, y) in segp.items():
                E.loc[(E["T"] >= x) & (E["T"] <= y), "段"] = sg
            E["事件日"] = [str(cal[t].date()) for t in E["T"]]
            E["進場日"] = [str(cal[t].date()) for t in E["e"]]
            for h in ENDS:
                E[f"T+{h}超出資料尾"] = (E["T"] + h) > last
            # Q4 候選
            E["候選數"] = cand_info(E, T, W["SIG"][S["G"]], len(cal))
            # Q5 S0 ②③、S− ②
            cl = W["closes"]; brk = []; sm = []
            for s, e, st, t in zip(E["sid"], E["e"], E["狀態"], E["T"]):
                bb = BAD[wn].get(s)
                end = min(t + 120, last)
                if bb is not None:
                    kk = bb[bb > t]
                    if len(kk):
                        end = min(end, int(kk[0]) - 1)
                c = cl[s]
                if st.startswith("S0"):
                    up_, lo_ = c[e:t + 1].max(), c[e:t + 1].min()
                    seg_ = c[t + 1:end + 1]
                    iu = np.flatnonzero(seg_ > up_); il = np.flatnonzero(seg_ < lo_)
                    fu = int(iu[0]) if len(iu) else 10 ** 9; fl = int(il[0]) if len(il) else 10 ** 9
                    brk.append("先突破" if fu < fl else ("先跌破" if fl < fu else "都沒有"))
                else:
                    brk.append("")
                if st == "S−":
                    bp = float(T.loc[(T["sid"] == s) & (T["e"] == e), "bp"].iloc[0])
                    seg_ = c[t + 1:end + 1]
                    i5 = np.flatnonzero(seg_ / bp - 1.0 >= -0.05)
                    ma = np.array([c[max(0, j - 19):j + 1].mean() for j in range(t + 1, end + 1)])
                    im = np.flatnonzero(seg_ >= ma) if len(seg_) else np.zeros(0, int)
                    f5 = int(i5[0]) if len(i5) else 10 ** 9; fm = int(im[0]) if len(im) else 10 ** 9
                    sm.append("同日" if (f5 == fm and f5 < 10 ** 9) else ("r≥−5%先" if f5 < fm else ("20日線先" if fm < f5 else "都沒有")))
                else:
                    sm.append("")
            E["S0箱"] = brk; E["S−②先後"] = sm
            DET.append(E)
            T2 = T.copy(); T2["策略"] = sn; T2["世界"] = wn
            T2["進場日"] = [str(cal[t].date()) for t in T2["e"]]
            T2["出清日"] = [str(cal[t].date()) if t < len(cal) else "資料尾未賣" for t in T2["x"]]
            TR0.append(T2.drop(columns=["bp"]))
            FREQ += summarize(E, W, wn, {"策略": sn, "r": 0})
            log(f"[{wn}·{sn} r0] 事件 {E['狀態'].value_counts().to_dict()}｜壞根截斷交易 {ntr}")
    DE = pd.concat(DET, ignore_index=True)
    # 合併（營量 r0 ＋ 營飆 r0）
    for wn in ("主", "早年"):
        FREQ += summarize(DE[DE["世界"] == wn], WS[wn], wn, {"策略": "合併", "r": 0})
    dup = DE.groupby(["世界", "狀態", "sid", "T"]).size()
    J["合併重複(同股同狀態同日兩策略都有)"] = int((dup > 1).sum())
    # 7 格
    F = pd.DataFrame(FREQ)
    CELLS = [("S+", "②回落10%才賣", "S+"), ("S+", "③跌破20日線", "S+"), ("S+", "④半立即半③", "S+"),
             ("S0", "②跌破箱底", "S0_40"), ("S0", "③Darvas箱型", "S0_40"), ("S−", "②反彈或站回20日線", "S−"), ("S−", "③營收年增轉負", "S−")]
    CR = []
    for grp, nm, st in CELLS:
        row = {"狀態": grp, "格": nm, "事件定義": st}
        ok = True
        for sg in ("探索", "確認"):
            for sn in ("合併", "營量", "營飆"):
                v = F[(F["策略"] == sn) & (F["段"] == sg) & (F["狀態"] == st)]
                row[f"{sn}_{sg}_事件"] = int(v["事件"].iloc[0]); row[f"{sn}_{sg}_n_eff"] = int(v["n_eff"].iloc[0])
            ok &= row[f"合併_{sg}_n_eff"] >= NEFF_MIN
        v = F[(F["策略"] == "合併") & (F["段"] == "早年") & (F["狀態"] == st)]
        row["合併_早年_事件(描述)"] = int(v["事件"].iloc[0]); row["合併_早年_n_eff"] = int(v["n_eff"].iloc[0])
        row["可判(合併兩段n_eff≥30)"] = bool(ok)
        CR.append(row)
    CR = pd.DataFrame(CR)
    log(f"[7 格] 可判 {int(CR['可判(合併兩段n_eff≥30)'].sum())}／7")
    # 候選與 0050
    for (wn, sn, sg), sub in DE[DE["段"] != ""].groupby(["世界", "策略", "段"]):
        for st in STATES:
            x = sub[sub["狀態"] == st]
            v = x[x["候選數"] >= 0]
            CAND.append({"世界": wn, "策略": sn, "段": sg, "狀態": st, "事件": len(x), "T+1超出資料": int((x["候選數"] < 0).sum()),
                         "有候選": int((v["候選數"] > 0).sum()), "改放0050": int((v["候選數"] == 0).sum()),
                         "改放0050比例": round(float((v["候選數"] == 0).mean()), 4) if len(v) else None,
                         "候選數中位(有候選者)": float(v.loc[v["候選數"] > 0, "候選數"].median()) if (v["候選數"] > 0).any() else None})
    for (wn, sg), sub in DE[DE["段"] != ""].groupby(["世界", "段"]):
        v = sub[sub["候選數"] >= 0]
        CAND.append({"世界": wn, "策略": "合併", "段": sg, "狀態": "全部", "事件": len(sub), "T+1超出資料": int((sub["候選數"] < 0).sum()),
                     "有候選": int((v["候選數"] > 0).sum()), "改放0050": int((v["候選數"] == 0).sum()),
                     "改放0050比例": round(float((v["候選數"] == 0).mean()), 4) if len(v) else None,
                     "候選數中位(有候選者)": float(v.loc[v["候選數"] > 0, "候選數"].median()) if (v["候選數"] > 0).any() else None})
    # 等價
    for N in S0N:
        for (wn, sg), sub in DE[(DE["狀態"] == f"S0_{N}") & (DE["段"] != "")].groupby(["世界", "段"]):
            vc = sub["S0箱"].value_counts().to_dict(); n = len(sub)
            fb = vc.get("先突破", 0) / n if n else None
            EQV[f"S0_{N}②vs③_{wn}{sg}"] = {"事件": n, **vc, "先突破比例": round(fb, 4) if fb is not None else None,
                                         "標記": ("③ 近乎等於 ②（先突破 ＜ 10%）" if (fb is not None and fb < 0.10) else "③ 與 ② 不同（先突破 ≥ 10%）")}
        sub = DE[(DE["狀態"] == f"S0_{N}") & DE["段"].isin(["探索", "確認"])]
        n = len(sub); fb = (sub["S0箱"] == "先突破").sum() / n if n else None
        EQV[f"S0_{N}②vs③_主兩段合計"] = {"事件": n, "先突破": int((sub["S0箱"] == "先突破").sum()), "先突破比例": round(float(fb), 4) if fb is not None else None,
                                     "標記": ("③ 近乎等於 ②（先突破 ＜ 10%）" if (fb is not None and fb < 0.10) else "③ 與 ② 不同（先突破 ≥ 10%）")}
    EQV["S+④與③"] = {"關係": "④ ＝ 一半立即換（①）＋ 一半照 ③ ⇒ d(④) ＝ ½ d(③)（同一事件、同終點、成本同扣時恆等）；構造關係照報，⛔ 不當新證據"}
    for (wn, sg), sub in DE[(DE["狀態"] == "S−") & (DE["段"] != "")].groupby(["世界", "段"]):
        EQV[f"S−②先後_{wn}{sg}"] = {"事件": len(sub), **sub["S−②先後"].value_counts().to_dict()}
    # S0 退化（登錄 §五）：事件日固定在第 40 日 ⇒ 剩餘天數
    for sn, S in STR.items():
        for N in S0N:
            sub = DE[(DE["策略"] == sn) & (DE["狀態"] == f"S0_{N}")]
            EQV[f"S0退化_{sn}_N{N}"] = {"事件": len(sub), "原規則剩餘天數(H−N)": S["H"] - N,
                                     "占該策略 r0 交易比例": round(len(sub) / max(1, sum(len(t) for t in TR0 if t['策略'].iloc[0] == sn)), 4)}
    log(f"[等價] {json.dumps({k: v for k, v in EQV.items() if '主兩段' in k or 'S0退化' in k}, ensure_ascii=False)}")
    # ── 營飆 200 顆
    _G.update(WS)
    SD = []
    jobs = [(wn, r) for wn in ("主", "早年") for r in range(a.seeds)]
    ref = {}
    sp = "backtest/resultsYL_integrate/seeds.csv.gz"
    if os.path.exists(sp):
        z = pd.read_csv(sp, dtype=str)
        if {"世界", "格", "r", "eq_sha"} <= set(z.columns):
            z = z[z["格"] == IG.YF]
            ref = {(w, int(r)): h for w, r, h in zip(z["世界"], z["r"], z["eq_sha"])}
    nbad = 0; ncmp = 0
    with Pool(a.procs) as pool:
        for k_, (wn, r, T, h) in enumerate(pool.imap_unordered(seed_job, jobs, chunksize=4)):
            ncmp += int((wn, r) in ref)
            if (wn, r) in ref and ref[(wn, r)] != h:
                nbad += 1
            W = WS[wn]; cal = W["cal"]
            E, _ = events_of(T, W, BAD[wn], len(cal) - 1)
            nc = cand_info(E, T, W["SIG"][True], len(cal))
            for sg, (x, y) in seg_of(W, wn).items():
                for st in STATES:
                    m = (E["狀態"] == st).to_numpy() & (E["T"] >= x).to_numpy() & (E["T"] <= y).to_numpy()
                    n = int(m.sum()); mo = E.loc[m, "T"].map(lambda t: cal[t].strftime("%Y-%m")).nunique() if n else 0
                    v = nc[m]; v = v[v >= 0]
                    SD.append({"世界": wn, "r": r, "段": sg, "狀態": st, "事件": n, "n_eff": int(min(n, mo)), "交易": len(T),
                               "改放0050比例": float((v == 0).mean()) if len(v) else np.nan})
            if (k_ + 1) % 50 == 0:
                log(f"  營飆種子 {k_ + 1}／{len(jobs)}｜{time.time() - t0:.0f}s")
    SD = pd.DataFrame(SD)
    J["營飆種子權益對 resultsYL_integrate eq_sha 不同"] = {"比對顆數": ncmp, "不同": nbad}
    DIST = []
    for (wn, sg, st), g in SD.groupby(["世界", "段", "狀態"]):
        DIST.append({"世界": wn, "段": sg, "狀態": st, "顆數": len(g), "事件_min": int(g["事件"].min()), "事件_p25": float(g["事件"].quantile(0.25)),
                     "事件_中位": float(g["事件"].median()), "事件_p75": float(g["事件"].quantile(0.75)), "事件_max": int(g["事件"].max()),
                     "n_eff_中位": float(g["n_eff"].median()), "n_eff_min": int(g["n_eff"].min()),
                     "r0事件": int(g.loc[g["r"] == 0, "事件"].iloc[0]) if (g["r"] == 0).any() else None,
                     "改放0050比例_中位": round(float(g["改放0050比例"].median()), 4) if g["改放0050比例"].notna().any() else None})
    DIST = pd.DataFrame(DIST)
    log(f"[營飆 {a.seeds} 顆] eq_sha 對照 {J['營飆種子權益對 resultsYL_integrate eq_sha 不同']}")
    # ── 輸出
    J["讀法"] = __doc__.split("═══ 讀法")[1]
    J["等價"] = EQV
    J["時間"] = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")
    F.to_csv(os.path.join(OUT, "freq.csv"), index=False, encoding="utf-8-sig")
    CR.to_csv(os.path.join(OUT, "cells.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(CAND).to_csv(os.path.join(OUT, "cand_0050.csv"), index=False, encoding="utf-8-sig")
    DIST.to_csv(os.path.join(OUT, "seeds_dist.csv"), index=False, encoding="utf-8-sig")
    SD.to_csv(os.path.join(OUT, "seeds_all.csv.gz"), index=False, compression="gzip")
    pd.DataFrame([{"項": k, **v} for k, v in EQV.items()]).to_csv(os.path.join(OUT, "equiv.csv"), index=False, encoding="utf-8-sig")
    DE.to_csv(os.path.join(OUT, "events_r0.csv.gz"), index=False, compression="gzip")
    pd.concat(TR0, ignore_index=True).to_csv(os.path.join(OUT, "trades_r0.csv.gz"), index=False, compression="gzip")
    json.dump(J, open(os.path.join(OUT, "freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] {time.time() - t0:.0f}s")
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
