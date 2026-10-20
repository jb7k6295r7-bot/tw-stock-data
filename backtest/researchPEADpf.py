# -*- coding: utf-8 -*-
"""PREREG財報公告後漂移PEAD組合層 seq1【正式跑】（台股策略線 登錄 sha bc4aa68308255d95，2026-10-20 18:47；裁定 seq396 准起草、seq398 發號 N_組合 ＋1、
組合規則與描述「過目照跑」；標籤上限：早年無上傳時戳 ⇒ 兩段合格也只寫暫定）——回測線計算子代理。
⛔ 只計算：不 commit、不改既有程式與結果夾；researchPEAD（stock_job 逐股報酬）、researchPEAD_freq（_G）、researchAscTri（load_world、label、ratio）、
researchTurtleS2PF（simulate、verdict、成本常數）、researchPTHpf（本線同批新檔：份迴圈以外的共用工具——世界收尾、等效獨立檔數、分年、最差 12 個月、
營量 v1 載入與比較、上限）、rerun17 ⛔ 只 import。用語「假訊號」；⛔ 不給買賣建議。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPEADpf [--procs 2] [--dry]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPEADpf_check
輸出 backtest/resultsPEADpf/：degeneracy.json（先寫）、PEADpf.json、PEADpf_main.csv、by_year.csv、yl.csv、weight_by_month.csv、
    trades_<臂>.csv.gz（逐筆買賣）、events_<臂>.csv.gz（入組合事件、去重）、eq.npz、run.log

⭐ 讀法寫死：2026-10-20 19:40～20:10（台北）寫檔；寫死前 ⛔ 沒看過任何本件組合層數字（看過的只有事件層結果與頻率表）。

═══ 讀法（Z 標；登錄沒寫清楚、執行者補的都在這裡；★＝執行者定，〔 〕內為另一讀法）═══
 Z0 事件與出場 ⛔ 不另寫：世界 ＝ researchAscTri.load_world「主」；逐股 R、出場種類、出場日 ＝ researchPEAD.stock_job 原樣（60 日 ＝ e＋59 收盤，壞根前強制、下市末根、資料尾）。
    事件 ＝ 已提交 resultsPEAD/events/trades_<格>.csv.gz 每一列（入選 ∧ 保留；上季切點 判定）；逐列比 R、出場種類、出場日 與本支重算，任一不同 ⇒ 中止。
    買價 P ＝ 快取還原開盤 O[e]；賣價 ＝ P×(1＋R)；價格閘：賣價 ÷ 賣出日快取收盤（ffill）− 1 ≤ 1e−9。
    賣出日：到期 ⇒ e＋59；★ 到期日無成交（用前一根收盤）也記在 e＋59；壞根前強制、下市末根 ⇒ 該根日曆日；資料尾未出場 ⇒ 持有到資料尾。
    同檔同時兩筆（後一筆 e ≤ 前一筆賣出日）⇒ 後一筆不入組合、照前一筆出場（登錄 §一）；件數照報。
 Z1 日曆時間組合（登錄 §一、Fama 1998）：窗首淨值 1 全抱 0050（⛔ 不扣建倉成本）。每天持股 ＝ 當天仍在持有期內的事件股。
    權重調整只在有事件進出的日子：
      進場日 e【開盤】：n ＝ 當天持有中事件數（含當天新進、含當天收盤才出場者）；每檔目標 ＝ 淨值 × 1/max(n, 10)；新事件以 P 買進，
        既有持股以當天還原開盤調到目標；其餘全放 0050（還原開盤）。
      出場日【收盤】：出場事件以賣價賣出；剩下 n′ 檔以當天收盤調到 1/max(n′, 10)；其餘放 0050（還原收盤）。
      ★ 開盤／收盤無成交的持股不能交易 ⇒ 該日不動（按前一日收盤／當天 ffill 收盤計值），其餘照目標；0050 不足（凍結持股過重）⇒ 可交易持股等比例縮小。
      其餘日子不動、自然漂移。淨值（開盤）＝ 0050 單位 × 0050 開盤 ＋ 持股 × 開盤（不能交易者用前一日收盤）＋ 零頭現金。
    成本（★ 部分加減碼無「買進金額」可對 ⇒ 改用單邊）：個股買 0.1425%、賣 0.4425%（手續費＋證交稅 0.3%；來回 ＝ 0.585%）；0050 買 0.1425%、賣 0.2425%；
      成本由同一次調整內扣（目標以「淨值 − 成本」計，定點疊代到成本變動 ≤ 1e−15×淨值；殘差留現金、下次調整併入）。0050 開盤缺值 ⇒ 前一日收盤。
 Z2 滑價版（seq369）：個股每筆買、賣（含加減碼、強制、末根）各再 +0.5%；0050 不加；其餘全同。
 Z3 段、判準 ⛔ 不另寫：段 ＝ researchAscTri_freq.SEGS「主」（探索 2017-03-02～2021-12-30｜確認 2022-01-03～資料尾）；早年段不做（無上傳時戳）。
    年化、回落 ＝ rerun17.win_metrics；0050 ＝ rerun17.bench_row；標籤 ＝ researchAscTri.label；整件 ＝ researchTurtleS2PF.verdict 原樣照報，
    再套 seq398 上限（researchPTHpf.capped：無早年 ⇒ 最多暫定；滑價版探索或確認不合格 ⇒ 最多另列）。退化（seq325）先寫 degeneracy.json。
 Z4 必報（＝ 海龜組合層 K10 同式，改單邊成本）：換手 ＝ 段內個股買進金額（新進＋加碼）÷ 段內平均淨值 ÷ 年（年 ＝ 交易日 ÷ 245）；成本／年 ＝ 換手 × 0.585%
    （另報實付個股、實付 0050、合計）；平均持股 ＝ 段內逐日收盤持股檔數平均；平均股票部位比例 ＝ 持股市值 ÷ 淨值 段內平均；0050 占淨值；
    等效獨立檔數 ＝ researchPTHpf.effn_vec（＝ researchDumb.eff_n 同式；段內每個進場日、持有中各筆）；事件逐筆（依進場日歸段；事件層 R − 0.585%）勝率、賺賠比、出場種類占比；
    分年、上市／上櫃（持股市值上櫃占比、事件逐筆淨報酬平均）、最差 12 個月 ＝ researchPTHpf 同一支。
 Z5 描述（⛔ 不判、不計 N）：
    ① 10 檔版 ＝ researchTurtleS2PF.simulate 主模式原樣（10 槽、新部位 min(前一日淨值÷10, 可撥 0050)、同檔不重複、同日先出後進）；
       候選依（e、SUE 由高到低、代號）排序、以「不洗牌」生成器傳入 ⇒ 同日事件多於空位 SUE 高者先；沒買到的件數照報。
    ② 與營量 v1 ＝ researchPTHpf.yl_load／yl_compare（月／日報酬相關、持股重疊、各半①②；確認段到營量資料尾 2026-08-24）。
    ③ 同季切點版組合（事件 ＝ trades_同季切點）；持有天數軸 20、120 日（trades_上季切點_20日／_120日）：皆同 Z1。
    ④ 股票部位比例時序：段內逐日股票部位比例的平均、中位、＜50%／＜20%／＝0 的日子比例、各曆月平均；
       報酬拆解（★ 近似）：0050 部分 ＝ Σ 前一日收盤 0050 權重 × 0050 當日報酬，個股部分 ＝ 組合日報酬 − 0050 部分（含成本），段內加總。
 Z6 結果句必附：登錄 §四 六句（「單筆層兩段都比隨便買好，但組合是另一回事」「每季實際入選 a%～b%」「台股有月營收先揭露」「早年無上傳時戳不做」
    「與單季 EPS 季增重疊 a～b%（該件不合格）」「沒事件時抱 0050」）＋ seq396「樣本中等、單筆通過不等於組合會贏」＋ seq398「早年無上傳時戳 ⇒ 兩段合格也只寫暫定」。
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import time
from collections import Counter
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchPEAD as PE                     # noqa: E402  stock_job（⛔ 只 import）
from backtest import researchPEAD_freq as PF                # noqa: E402  _G
from backtest import researchAscTri as AS                   # noqa: E402  load_world、label、ratio
from backtest import researchTurtleS2PF as TS               # noqa: E402  simulate、verdict
from backtest import researchPTHpf as PP                    # noqa: E402  共用工具（同批新檔）
from backtest import rerun17 as RR                          # noqa: E402
from backtest import researchAddOn as RA                    # noqa: E402
from backtest import universe_gate as UG                    # noqa: E402

UG.set_gate_v2(True)

TIME = "2026-10-20 19:40～20:10（台北）"
REG_SHA = "bc4aa68308255d95"
OUT = "backtest/resultsPEADpf"
EVD = "backtest/resultsPEAD/events"
PEJ = "backtest/resultsPEAD/PEAD.json"
COST = TS.COST
BC_BUY, BC_SELL, SLIP = TS.BC_BUY, TS.BC_SELL, TS.SLIP
SB, SS = 0.001425, 0.001425 + 0.003                 # 個股單邊：買、賣（來回 ＝ 0.585%）
NS = TS.NS
DEG_HOLD = 3.0
TYPN = PE.TYP
HS = (20, 60, 120)
CELLS = {"上季切點": 60, "同季切點": 60, "上季切點_20日": 20, "上季切點_120日": 120}
ARMS = {"M": {"名": "主判：SUE 最高十分位（上季切點）抱 60 日、日曆時間組合、每檔 1/max(n,10)、其餘 0050", "cell": "上季切點", "kind": "cal", "slip": False, "judge": True},
        "Mslip": {"名": "主判＋滑價每邊 0.5%（seq369 可執行性條款）", "cell": "上季切點", "kind": "cal", "slip": True, "judge": True},
        "S10": {"名": "描述①：10 檔版（SUE 高者先、空位 0050）", "cell": "上季切點", "kind": "slot", "slip": False, "judge": False},
        "SAMEQ": {"名": "描述③：同季切點版（日曆時間組合）", "cell": "同季切點", "kind": "cal", "slip": False, "judge": False},
        "H20": {"名": "描述：抱 20 日（日曆時間組合）", "cell": "上季切點_20日", "kind": "cal", "slip": False, "judge": False},
        "H120": {"名": "描述：抱 120 日（日曆時間組合）", "cell": "上季切點_120日", "kind": "cal", "slip": False, "judge": False}}
_G: dict = {}


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


pct = PP.pct


# ═════════════ 逐股（只取事件所在 e）═════════════
def stock_job(sid):
    s_, out = PE.stock_job(sid)
    if out is None:
        return sid, None
    req = np.asarray(_G["req"][sid], np.int64)
    return sid, {H: (out[f"R{H}"][req], out[f"T{H}"][req], out[f"S{H}"][req]) for H in HS}


def read_cell(cell):
    return pd.read_csv(os.path.join(EVD, f"trades_{cell}.csv.gz"), dtype=str, keep_default_na=False)


def load_events(W, cell, RES, FR):
    H = CELLS[cell]; fr = FR[cell]
    n0 = W["n0"]; ix = W["ix"]
    dpos = {d: i for i, d in enumerate(W["dates"])}
    tinv = {v: k for k, v in TYPN.items()}
    i_ = np.array([ix[s] for s in fr["sid"]], np.int64)
    e = np.array([dpos[d] for d in fr["進場日"]], np.int64)
    R = np.array([float(x) if x != "" else np.nan for x in fr["R"]])
    typ = np.array([tinv[x] for x in fr["出場種類"]], np.int8)
    sd = np.array([dpos[x] if x != "" else -1 for x in fr["出場日"]], np.int64)
    nd = Counter()
    for q, s in enumerate(fr["sid"]):
        rq = RES[s]; k = _G["reqpos"][(s, int(e[q]))]
        a_, t_, s2 = rq[H][0][k], int(rq[H][1][k]), int(rq[H][2][k])
        if not ((np.isnan(a_) and np.isnan(R[q])) or abs(a_ - R[q]) <= 1e-12):
            nd["R"] += 1
        if t_ != int(typ[q]):
            nd["出場種類"] += 1
        if s2 != int(sd[q]):
            nd["出場日"] += 1
    X = e + H - 1
    sale = np.where(np.isin(typ, (1, 2)), X, np.where(np.isin(typ, (3, 4)), sd, -1)).astype(np.int64)
    P = np.asarray(W["O"], float)[i_, e]
    px = P * (1.0 + R)
    nd["買價缺"] = int((~(np.isfinite(P) & (P > 0))).sum())
    nd["到期越界"] = int((np.isin(typ, (1, 2)) & (X > n0 - 1)).sum())
    sold = sale >= 0
    rel = np.abs(px[sold] / W["CM"][i_[sold], sale[sold]] - 1.0)
    nd["賣價≠賣出日收盤(>1e-9)"] = int((rel > 1e-9).sum())
    nd["出場早於進場"] = int((sold & (sale < e)).sum())
    bad = {k: v for k, v in nd.items() if v}
    if bad:
        raise SystemExit(f"⛔ {cell} 事件／價格閘不過 {bad}")
    sue = np.array([float(x) for x in fr["SUE"]])
    o_ = np.lexsort((W["srank"][i_], e))
    ev = {"sid": fr["sid"].to_numpy()[o_], "季": fr["季"].to_numpy()[o_], "j": i_[o_], "e": e[o_], "typ": typ[o_], "R": R[o_], "sale": sale[o_],
          "P": P[o_], "px": px[o_], "sue": sue[o_]}
    info = {"列": int(len(fr)), "最大相對差(賣價vs收盤)": float(rel.max()) if len(rel) else 0.0,
            "出場種類": {TYPN[int(k)]: int(v) for k, v in Counter(typ.tolist()).items()}}
    return ev, info


# ═════════════ 日曆時間組合（Z1、Z2）═════════════
def solve(E, cur, F, w, cur50, cb, cs, cb50, cs50):
    """目標 ＝ (E − 成本) × w（可交易各檔）；0050 ＝ 其餘；成本 ＝ 單邊成本合計（定點疊代）。⇒ T, T50, 個股成本, 0050 成本, 殘差。"""
    c = 0.0; T = np.zeros(len(cur)); T50 = 0.0; cst_s = 0.0; cst_5 = 0.0
    for _ in range(200):
        En = E - c
        T = np.full(len(cur), w * En)
        T50 = En - T.sum() - F
        if T50 < 0.0:
            if T.sum() > 0:
                T = T * max(En - F, 0.0) / T.sum()
            T50 = En - T.sum() - F
        d = T - cur; d50 = T50 - cur50
        cst_s = float(np.sum(np.where(d > 0, d * cb, -d * cs)))
        cst_5 = d50 * cb50 if d50 > 0 else -d50 * cs50
        cn = cst_s + cst_5
        if abs(cn - c) <= 1e-15 * max(abs(E), 1e-300):
            c_prev = c; c = cn
            break
        c = cn
    else:
        c_prev = c
    resid = E - (cst_s + cst_5) - T.sum() - F - T50
    return T, T50, cst_s, cst_5, resid


def dedup(ev, n0):
    m = len(ev["e"]); keep = np.ones(m, bool); last = {}
    for q in range(m):
        j = int(ev["j"][q]); end = int(ev["sale"][q]) if ev["sale"][q] >= 0 else n0 + 1
        if j in last and ev["e"][q] <= last[j]:
            keep[q] = False; continue
        last[j] = end
    return keep


def cal_sim(ev, W, slip, want_mv=False):
    n0 = W["n0"]; CM = W["CM"]; Bc = W["Bc"]; Bo = W["Bo"]
    O = np.asarray(W["O"], float)[:, :n0]; TRD = W["TRD"]
    cb = SB + (SLIP if slip else 0.0); cs = SS + (SLIP if slip else 0.0)
    keep = dedup(ev, n0)
    by_e, by_s = {}, {}
    for q in np.flatnonzero(keep):
        by_e.setdefault(int(ev["e"][q]), []).append(int(q))
        if ev["sale"][q] >= 0:
            by_s.setdefault(int(ev["sale"][q]), []).append(int(q))
    jq = ev["j"]; Pq = ev["P"]; pxq = ev["px"]
    pos = {}
    u = 1.0 / Bc[0]; cash = 0.0
    eq = np.zeros(n0); hv = np.zeros(n0); uv = np.zeros(n0); cv = np.zeros(n0); nh = np.zeros(n0, np.int32)
    MV = np.zeros((CM.shape[0], n0)) if want_mv else None
    buys, sells, etf, scost, reb = [], [], [], [], []
    froz_n = 0
    for t in range(n0):
        ents = by_e.get(t)
        if ents:
            held = list(pos.keys()); trad = []; Fv = 0.0
            for q in held:
                j = jq[q]
                if TRD[j, t] and np.isfinite(O[j, t]) and O[j, t] > 0:
                    trad.append((q, O[j, t]))
                else:
                    Fv += pos[q] * CM[j, t - 1]; froz_n += 1
            cur = np.array([pos[q] * p for q, p in trad] + [0.0] * len(ents))
            E = u * Bo[t] + cash + float(cur.sum()) + Fv
            n = len(held) + len(ents); w = 1.0 / max(n, NS)
            T, T50, c_s, c_5, resid = solve(E, cur, Fv, w, u * Bo[t], cb, cs, BC_BUY, BC_SELL)
            for k, (q, p) in enumerate(trad):
                d = T[k] - cur[k]
                if d > 0:
                    buys.append((t, q, d, 0))
                elif d < 0:
                    sells.append((t, q, -d, 0))
                pos[q] = T[k] / p
            for k, q in enumerate(ents):
                pos[q] = T[len(trad) + k] / Pq[q]; buys.append((t, q, T[len(trad) + k], 1))
            d50 = T50 - u * Bo[t]
            if d50 != 0.0:
                etf.append((t, 1 if d50 > 0 else -1, abs(d50), c_5))
            u = T50 / Bo[t]; cash = resid
            scost.append((t, c_s)); reb.append((t, 0, n, w, resid))
        exs = [q for q in by_s.get(t, []) if q in pos]
        if exs:
            proc = 0.0; c_x = 0.0
            for q in exs:
                V = pos.pop(q) * pxq[q]; cx = V * cs
                proc += V - cx; c_x += cx; sells.append((t, q, V, 1))
            held = list(pos.keys()); trad = []; Fv = 0.0
            for q in held:
                j = jq[q]
                if TRD[j, t]:
                    trad.append((q, CM[j, t]))
                else:
                    Fv += pos[q] * CM[j, t]; froz_n += 1
            cur = np.array([pos[q] * p for q, p in trad])
            E = u * Bc[t] + cash + proc + float(cur.sum()) + Fv
            n = len(held); w = 1.0 / max(n, NS)
            T, T50, c_s, c_5, resid = solve(E, cur, Fv, w, u * Bc[t], cb, cs, BC_BUY, BC_SELL)
            for k, (q, p) in enumerate(trad):
                d = T[k] - cur[k]
                if d > 0:
                    buys.append((t, q, d, 0))
                elif d < 0:
                    sells.append((t, q, -d, 0))
                pos[q] = T[k] / p
            d50 = T50 - u * Bc[t]
            if d50 != 0.0:
                etf.append((t, 1 if d50 > 0 else -1, abs(d50), c_5))
            u = T50 / Bc[t]; cash = resid
            scost.append((t, c_s + c_x)); reb.append((t, 1, n, w, resid))
        h = 0.0
        for q, sh in pos.items():
            v = sh * CM[jq[q], t]; h += v
            if MV is not None:
                MV[jq[q], t] += v
        hv[t] = h; uv[t] = u * Bc[t]; cv[t] = cash; nh[t] = len(pos)
        eq[t] = uv[t] + cash + h
    if not np.all(np.isfinite(eq)):
        raise SystemExit("⛔ 權益非有限值")
    return {"eq": eq, "hv": hv, "u": uv, "pend": cv, "nh": nh, "buys": buys, "sells": sells, "etf": etf, "scost": scost, "reb": reb,
            "MV": MV, "keep": keep, "froz": froz_n, "j": jq, "ext": ev["sale"], "g": ev["R"]}


def cal_intervals(ev, keep, n0):
    q = np.flatnonzero(keep)
    return np.stack([ev["j"][q], ev["e"][q], np.where(ev["sale"][q] >= 0, ev["sale"][q], n0 + 1)], 1).astype(np.int64)


def cal_stats(W, S, ev, x, y):
    eq, hv, u, nh = S["eq"], S["hv"], S["u"], S["nh"]
    yrs = (y - x + 1) / 245.0; meq = float(np.mean(eq[x:y + 1]))
    bs = [b for b in S["buys"] if x <= b[0] <= y]
    d = {"平均持股(筆)": float(np.mean(nh[x:y + 1])), "平均股票部位比例": float(np.mean(hv[x:y + 1] / eq[x:y + 1])),
         "0050占淨值": float(np.mean(u[x:y + 1] / eq[x:y + 1])), "零頭現金占淨值(最大絕對)": float(np.max(np.abs(S["pend"][x:y + 1] / eq[x:y + 1]))),
         "新進買進筆": int(sum(1 for b in bs if b[3] == 1)), "換手每年": float(sum(b[2] for b in bs) / meq / yrs),
         "換手每年_新進": float(sum(b[2] for b in bs if b[3] == 1) / meq / yrs), "調整日數": int(len({r[0] for r in S["reb"] if x <= r[0] <= y}))}
    d["成本每年(換手×0.585%)"] = d["換手每年"] * COST
    d["個股成本每年(實付)"] = float(sum(c for t, c in S["scost"] if x <= t <= y) / meq / yrs)
    d["0050成本每年(實付)"] = float(sum(e_[3] for e_ in S["etf"] if x <= e_[0] <= y) / meq / yrs)
    d["成本合計每年(實付)"] = d["個股成本每年(實付)"] + d["0050成本每年(實付)"]
    keep = S["keep"]
    qs = np.flatnonzero(keep & (ev["e"] >= x) & (ev["e"] <= y))
    fin = ev["sale"][qs] >= 0
    v = (ev["R"][qs] - COST)[fin]; w_ = v[v > 0]; l_ = v[v <= 0]
    d.update({"入組合事件": int(len(qs)), "同檔重疊不入": int(((~keep) & (ev["e"] >= x) & (ev["e"] <= y)).sum()),
              "事件勝率": float((v > 0).mean()) if len(v) else np.nan,
              "事件平均賺賠比": float(w_.mean() / abs(l_.mean())) if (len(w_) and len(l_) and l_.mean() != 0) else np.nan,
              "事件逐筆淨報酬平均(事件層R)": float(v.mean()) if len(v) else np.nan, "資料尾未出場": int((~fin).sum())})
    ty = ev["typ"][qs]
    for k_, nm in TYPN.items():
        d[f"出場占比_{nm}"] = float((ty == k_).mean()) if len(ty) else np.nan
    otc = W["otc"]
    oq = otc[ev["j"][qs]][fin]
    d["事件上櫃占比"] = float(otc[ev["j"][qs]].mean()) if len(qs) else np.nan
    d["事件逐筆淨報酬平均_上市"] = float(v[~oq].mean()) if (~oq).any() else np.nan
    d["事件逐筆淨報酬平均_上櫃"] = float(v[oq].mean()) if oq.any() else np.nan
    if S.get("MV") is not None:
        mv = S["MV"][:, x:y + 1]; tot = mv.sum(0)
        with np.errstate(invalid="ignore", divide="ignore"):
            d["持股市值上櫃占比"] = float(np.nanmean(np.where(tot > 0, mv[otc].sum(0) / tot, np.nan)))
    return d


def weight_desc(W, S, x, y):
    eq, hv, u = S["eq"], S["hv"], S["u"]
    ws = hv[x:y + 1] / eq[x:y + 1]
    cal = W["cal"]; mo = np.asarray(cal.month)[x:y + 1]
    r = eq[x + 1:y + 1] / eq[x:y] - 1.0
    b = W["Bc"]; rb = b[x + 1:y + 1] / b[x:y] - 1.0
    part50 = (u[x:y] / eq[x:y]) * rb
    return {"平均": float(ws.mean()), "中位": float(np.median(ws)), "＜50%日比例": float((ws < 0.5).mean()), "＜20%日比例": float((ws < 0.2).mean()),
            "＝0日比例": float((ws <= 1e-12).mean()), "≥99%日比例": float((ws >= 0.99).mean()),
            "各曆月平均": {int(m): float(ws[mo == m].mean()) for m in range(1, 13) if (mo == m).any()},
            "報酬拆解(近似,段內日報酬加總)": {"0050部分": float(part50.sum()), "個股部分(含成本)": float((r - part50).sum()), "合計": float(r.sum()),
                                     "0050部分占比": float(part50.sum() / r.sum()) if r.sum() != 0 else np.nan}}


# ═════════════ fixture ═════════════
def selftest(log):
    msgs = []
    # F1 單一事件手算（w ＝ 1/10）
    n0 = 5
    CM = np.array([[10.0, 10.5, 11.0, 11.5, 12.0]]); O = np.array([[10.0, 10.2, 10.8, 11.4, 11.9]])
    Bc = np.array([100.0, 101.0, 102.0, 103.0, 104.0]); Bo = np.array([99.5, 100.5, 101.5, 102.5, 103.5])
    W = {"n0": n0, "CM": CM, "Bc": Bc, "Bo": Bo, "O": O, "TRD": np.ones((1, n0), bool)}
    ev = {"j": np.array([0]), "e": np.array([1]), "sale": np.array([3]), "P": np.array([10.2]), "px": np.array([11.5]), "R": np.array([11.5 / 10.2 - 1])}
    r = cal_sim(ev, W, False)
    u0 = 1 / 100.0; E1 = u0 * Bo[1]
    # 解析解：c ＝ 0.1 cb (E−c) ＋ cs50 (E − 0.9 (E−c))  ⇒  c (1 ＋ 0.1 cb − 0.9 cs50) ＝ 0.1 E (cb ＋ cs50)
    c = 0.1 * E1 * (SB + BC_SELL) / (1 + 0.1 * SB - 0.9 * BC_SELL)
    T = 0.1 * (E1 - c); T50 = 0.9 * (E1 - c)
    sh = T / 10.2; u1 = T50 / Bo[1]
    e1 = u1 * Bc[1] + sh * CM[0, 1]; e2 = u1 * Bc[2] + sh * CM[0, 2]
    V = sh * 11.5; E3 = u1 * Bc[3] + V * (1 - SS)
    e3 = E3 - (V * (1 - SS)) * BC_BUY / (1 + BC_BUY)       # 收盤全買 0050（0 檔）：成本對買進額 ⇒ c ＝ 現金×cb÷(1＋cb)
    assert abs(r["eq"][0] - 1.0) < 1e-15 and abs(r["eq"][1] / e1 - 1) < 1e-13 and abs(r["eq"][2] / e2 - 1) < 1e-13 and abs(r["eq"][3] / e3 - 1) < 1e-13, (r["eq"], [e1, e2, e3])
    assert abs(r["eq"][4] / (r["u"][3] / Bc[3] * Bc[4]) - 1) < 1e-13
    msgs.append("F1 單一事件手算（開盤 1/10 買、0050 撥款、收盤賣出 0.4425%、收盤全回 0050 0.1425%、成本定點解析解）相對差 ≤ 1e−13")
    # F2 n ≥ 10 ⇒ 全押事件股、各 1/n；0050 ≈ 0
    n0 = 4; S_ = 12
    rng = np.random.default_rng(3)
    CM = 10 + rng.random((S_, n0)); O = CM * (1 + rng.normal(0, 0.01, (S_, n0)))
    W = {"n0": n0, "CM": CM, "Bc": np.full(n0, 100.0), "Bo": np.full(n0, 100.0), "O": O, "TRD": np.ones((S_, n0), bool)}
    ev = {"j": np.arange(S_), "e": np.full(S_, 1), "sale": np.full(S_, -1), "P": O[:, 1], "px": np.full(S_, np.nan), "R": np.full(S_, np.nan)}
    r = cal_sim(ev, W, False)
    assert r["u"][1] / r["eq"][1] < 1e-12 and r["nh"][1] == 12
    vals = np.array([r["MV"][j, 1] for j in range(S_)]) if r["MV"] is not None else None
    msgs.append("F2 n ＝ 12 ≥ 10 ⇒ 全押事件股、0050 ＝ 0")
    # F3 同檔重疊只算一筆
    ev = {"j": np.array([0, 0, 0]), "e": np.array([1, 3, 6]), "sale": np.array([4, 7, 9]), "P": np.ones(3), "px": np.ones(3), "R": np.zeros(3)}
    assert dedup(ev, 10).tolist() == [True, False, True]
    msgs.append("F3 同檔同時兩筆 ⇒ 後一筆不入（e ≤ 前一筆賣出日）")
    # F4 solve：無成本 ⇒ 目標精確；殘差 ≈ 0
    T, T50, a_, b_, res = solve(1.0, np.array([0.2, 0.0]), 0.0, 0.1, 0.8, 0.0, 0.0, 0.0, 0.0)
    assert np.allclose(T, [0.1, 0.1]) and abs(T50 - 0.8) < 1e-15 and abs(res) < 1e-15
    T, T50, a_, b_, res = solve(1.0, np.array([0.05] * 12), 0.0, 1 / 12, 0.4, SB, SS, BC_BUY, BC_SELL)
    assert abs(T50) < 1e-15 and abs(res) < 1e-14 and abs(T.sum() + a_ + b_ - 1.0) < 1e-14
    msgs.append("F4 定點：無成本精確；n ≥ 10 時 Σ目標 ＋ 成本 ＝ 淨值、殘差 ≤ 1e−14")
    for m_ in msgs:
        log("✅ " + m_)
    return msgs


# ═════════════ 主程式 ═════════════
def run(a, log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True)
    if abs(COST - 0.00585) > 1e-15 or abs(SB + SS - COST) > 1e-15:
        raise SystemExit("⛔ 成本常數不符")
    regf = PP.reg_check(REG_SHA)
    log(f"[登錄] sha {REG_SHA} ✓ {regf}｜讀法寫死 {TIME}｜開跑 {now_tpe()}")
    J = {"讀法寫死": TIME, "登錄": f"PREREG財報公告後漂移PEAD組合層 seq1 sha {REG_SHA}（裁定 seq396 准起草、seq398 發號 N_組合 ＋1、過目照跑）", "登錄檔": regf,
         "臂": {k: v["名"] for k, v in ARMS.items()},
         "成本": {"個股買": SB, "個股賣": SS, "0050買": BC_BUY, "0050賣": BC_SELL, "滑價每邊": SLIP, "10檔版個股來回(引擎口徑)": COST},
         "閘": {}, "時點": {"開跑": now_tpe()}}
    J["fixture"] = selftest(log)
    pj = json.load(open(PEJ, encoding="utf-8"))
    W = AS.load_world("主", log); PF._G["主"] = W
    PP.finish_world(W)
    J["閘"]["0050開盤缺值日(用前一日收盤)"] = W["nbo"]
    FR = {c: read_cell(c) for c in CELLS}
    dpos = {d: i for i, d in enumerate(W["dates"])}
    req = {}
    for c, fr in FR.items():
        for s, d in zip(fr["sid"], fr["進場日"]):
            req.setdefault(s, set()).add(dpos[d])
    _G["req"] = {s: sorted(v) for s, v in req.items()}
    _G["reqpos"] = {(s, e): k for s, v in _G["req"].items() for k, e in enumerate(v)}
    t0 = time.time(); RES = {}
    with Pool(a.procs) as pool:
        for k_, (sid, r) in enumerate(pool.imap_unordered(stock_job, sorted(_G["req"]), chunksize=8)):
            if r is not None:
                RES[sid] = r
            if (k_ + 1) % 300 == 0:
                log(f"  逐股 {k_ + 1}／{len(_G['req'])}｜{time.time() - t0:.0f}s")
    log(f"[主] 逐股完 {len(RES)} 檔（事件涉及 {len(_G['req'])} 檔）｜{time.time() - t0:.0f}s")
    EVS = {}
    for cell in CELLS:
        ev, info = load_events(W, cell, RES, FR)
        EVS[cell] = ev; J["閘"][f"事件 {cell}"] = info
        log(f"[查核 {cell}] 事件檔 {info['列']:,} 列 ＝ researchPEAD.stock_job 重算（R、出場種類、出場日）｜賣價 vs 收盤 最大相對差 {info['最大相對差(賣價vs收盤)']:.1e}")
    del RES
    if a.dry:
        log(f"[乾跑] 完（未算任何組合報酬）｜{time.time() - T0:.0f}s")
        json.dump(J, open(os.path.join(OUT, "dry.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
        return
    SIMS = {}
    for arm, cfg in ARMS.items():
        ev = EVS[cfg["cell"]]
        if cfg["kind"] == "cal":
            SIMS[arm] = cal_sim(ev, W, cfg["slip"], want_mv=(arm == "M"))
        else:
            o_ = np.lexsort((W["srank"][ev["j"]], -ev["sue"], ev["e"]))
            SIMS[arm] = PP.slot_sim(PP.slot_tr(ev, False, o_), W, PP.keep_order())
        log(f"[組合] {arm} 買進 {len(SIMS[arm]['buys']):,} 筆（⛔ 尚未讀報酬）｜{time.time() - T0:.0f}s")
    DEG = {"規則": "seq325：探索段平均持股 ＜ 3 ⇒ 退化、不判；空位抱 0050 ⇒「現金 ＞ 30%」不適用（seq360 §一）", "格": {}}
    for arm in ARMS:
        nh = SIMS[arm]["nh"]
        for sg, (x, y) in W["segp"].items():
            DEG["格"][f"主|{arm}|{sg}"] = {"平均持股": float(np.mean(nh[x:y + 1])), "退化": bool(np.mean(nh[x:y + 1]) < DEG_HOLD)}
    DEG["主判探索段退化"] = DEG["格"]["主|M|探索"]["退化"]
    DEG["寫入時間（台北）"] = now_tpe()
    json.dump(DEG, open(os.path.join(OUT, "degeneracy.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[退化] 已寫 degeneracy.json（{DEG['寫入時間（台北）']}）｜主判探索 {DEG['格']['主|M|探索']}")
    J["退化"] = DEG
    J["時點"]["第一次讀報酬"] = now_tpe()
    TAB = []; LAB = {}; BY = []; WD = {}
    cal = W["cal"]
    for arm, cfg in ARMS.items():
        S = SIMS[arm]; ev = EVS[cfg["cell"]]
        if cfg["kind"] == "cal":
            iv = cal_intervals(ev, S["keep"], W["n0"])
        else:
            iv = PP.intervals(S, W["n0"])
        for sg, (x, y) in W["segp"].items():
            c_, m_, b = PP.metrics(W, S["eq"], x, y)
            lab = AS.label(c_, m_, b); LAB[(arm, sg)] = lab
            row = {"世界": "主", "臂": arm, "臂名": cfg["名"], "身分": "判定" if cfg["judge"] else "描述（⛔ 不判）", "段": sg,
                   "窗": f"{cal[x].date()}～{cal[y].date()}", "年化": c_, "回落": m_, "比值": AS.ratio(c_, m_),
                   "0050年化": b["cagr"], "0050回落": b["mdd"], "0050比值": AS.ratio(b["cagr"], b["mdd"]), "標籤": lab}
            if cfg["kind"] == "cal":
                row.update(cal_stats(W, S, ev, x, y))
                if arm in ("M", "Mslip"):
                    row["平均股票部位比例"] = row["平均股票部位比例"]
                if arm == "M":
                    WD[sg] = weight_desc(W, S, x, y)
            else:
                st = PP.pf_stats(W, S, x, y, ev["typ"][S["q"]])
                cand = int(((ev["e"] >= x) & (ev["e"] <= y)).sum())
                st["候選事件"] = cand; st["沒買到"] = cand - st["買進筆"]
                st["平均股票部位比例"] = st.pop("個股占淨值")
                row.update(st)
            if arm in ("M", "S10"):
                row.update(PP.effn_seg(W, iv, x, y))
                w12 = PP.worst12(S["eq"], W["Bc"], cal, x, y)
                if w12:
                    row.update({"最差12個月": w12["最差12個月"], "最差12個月窗": w12["窗"], "最差12個月_0050同窗": w12["0050同窗"]})
            if arm in ("M", "Mslip", "S10"):
                for Y_, v_ in PP.yearly(S["eq"], W["Bc"], cal, x, y).items():
                    BY.append({"臂": arm, "段": sg, "年": Y_, **v_})
            TAB.append(row)
        log(f"  {arm} 統計完｜{time.time() - T0:.0f}s")
    TB = pd.DataFrame(TAB)
    TB.to_csv(os.path.join(OUT, "PEADpf_main.csv"), index=False, float_format="%.6g", encoding="utf-8-sig")
    pd.DataFrame(BY).to_csv(os.path.join(OUT, "by_year.csv"), index=False, float_format="%.6g", encoding="utf-8-sig")
    pd.DataFrame([{"段": sg, "曆月": m, "平均股票部位比例": v} for sg, d in WD.items() for m, v in d["各曆月平均"].items()]).to_csv(
        os.path.join(OUT, "weight_by_month.csv"), index=False, float_format="%.6g", encoding="utf-8-sig")
    J["主表"] = TAB; J["股票部位比例時序"] = WD
    log("[主表]\n" + TB[["臂", "段", "年化", "回落", "比值", "0050年化", "0050回落", "0050比值", "標籤", "平均持股(筆)", "平均股票部位比例", "換手每年",
                       "成本合計每年(實付)"]].to_string())
    L = {"主判探索": LAB[("M", "探索")], "主判確認": LAB[("M", "確認")], "滑價探索": LAB[("Mslip", "探索")], "滑價確認": LAB[("Mslip", "確認")],
         "主判早年": "—（無上傳時戳，不做）"}
    v0 = TS.verdict(L)
    v1, why = PP.capped(L, early_none=True)
    if DEG["主判探索段退化"]:
        v1 = f"退化、照 seq325 不判（標籤照報：{v1}）"
    J["判語"] = {**L, "researchTurtleS2PF.verdict 原樣": v0, "整件（套 seq398 上限）": v1, "上限理由": why}
    J["描述標籤"] = {f"{arm}|{sg}": LAB[(arm, sg)] for (arm, sg) in LAB if not ARMS[arm]["judge"]}
    log(f"[判語] {json.dumps(J['判語'], ensure_ascii=False)}")
    # ── 存檔
    dates = W["dates"]
    np.savez_compressed(os.path.join(OUT, "eq.npz"), Bc=W["Bc"], Bo=W["Bo"], **{f"{arm}_{k}": SIMS[arm][k] for arm in ARMS for k in ("eq", "hv", "u", "pend", "nh")})
    for arm, cfg in ARMS.items():
        S = SIMS[arm]; ev = EVS[cfg["cell"]]
        if cfg["kind"] == "cal":
            df = pd.DataFrame({"日": [dates[b[0]] for b in S["buys"]] + [dates[s[0]] for s in S["sells"]],
                               "pos": [b[0] for b in S["buys"]] + [s[0] for s in S["sells"]],
                               "sid": [ev["sid"][b[1]] for b in S["buys"]] + [ev["sid"][s[1]] for s in S["sells"]],
                               "季": [ev["季"][b[1]] for b in S["buys"]] + [ev["季"][s[1]] for s in S["sells"]],
                               "q": [b[1] for b in S["buys"]] + [s[1] for s in S["sells"]],
                               "方向": ["買"] * len(S["buys"]) + ["賣"] * len(S["sells"]),
                               "金額": [b[2] for b in S["buys"]] + [s[2] for s in S["sells"]],
                               "種類": [("新進" if b[3] else "加碼") for b in S["buys"]] + [("出場" if s[3] else "減碼") for s in S["sells"]]})
            df = df.sort_values(["pos", "方向", "q"], kind="mergesort")
            ek = pd.DataFrame({"q": np.arange(len(ev["e"])), "sid": ev["sid"], "季": ev["季"], "SUE": ev["sue"], "進場日": dates[ev["e"]],
                               "賣出日": [dates[s] if s >= 0 else "" for s in ev["sale"]], "出場種類": [TYPN[int(t)] for t in ev["typ"]],
                               "買價P": ev["P"], "賣價": ev["px"], "R": ev["R"], "入組合": S["keep"]})
            with gzip.open(os.path.join(OUT, f"events_{arm}.csv.gz"), "wt", encoding="utf-8") as fh:
                ek.to_csv(fh, index=False, float_format="%.17g")
        else:
            sl = {q: (t, proc) for t, q, amt, proc in S["sells"]}
            df = pd.DataFrame({"sid": [ev["sid"][S["q"][q]] for _, q, _ in S["buys"]], "季": [ev["季"][S["q"][q]] for _, q, _ in S["buys"]],
                               "SUE": [ev["sue"][S["q"][q]] for _, q, _ in S["buys"]], "買進日": [dates[t] for t, _, _ in S["buys"]],
                               "金額": [amt for _, _, amt in S["buys"]], "市值基準價": [S["ep"][q] for _, q, _ in S["buys"]], "R用": [S["g"][q] for _, q, _ in S["buys"]],
                               "排程賣出日": [dates[S["ext"][q]] if S["ext"][q] >= 0 else "" for _, q, _ in S["buys"]],
                               "賣出日": [dates[sl[q][0]] if q in sl else "" for _, q, _ in S["buys"]], "入帳": [sl[q][1] if q in sl else np.nan for _, q, _ in S["buys"]]})
        with gzip.open(os.path.join(OUT, f"trades_{arm}.csv.gz"), "wt", encoding="utf-8") as fh:
            df.to_csv(fh, index=False, float_format="%.17g")
    # ── 營量 v1
    Y = PP.yl_load("主", log, a.procs)
    J["營量v1"] = {"eq_sha": Y["sha"], "窗": Y["窗"]}; YLROW = []
    for sg, (x, y) in W["segp"].items():
        o = PP.yl_compare(W, SIMS["M"], Y, x, y)
        J["營量v1"][sg] = o
        if o:
            YLROW.append({"段": sg, **{k: v for k, v in o.items() if not isinstance(v, dict)},
                          **{f"{k}_{kk}": vv for k, v in o.items() if isinstance(v, dict) for kk, vv in v.items()}})
        log(f"[營量 {sg}] {json.dumps(o, ensure_ascii=False, default=float)}")
    pd.DataFrame(YLROW).to_csv(os.path.join(OUT, "yl.csv"), index=False, float_format="%.6g", encoding="utf-8-sig")

    def row(arm, sg):
        return TB[(TB["臂"] == arm) & (TB["段"] == sg)].iloc[0]
    J["先驗對照"] = {
        "① 兩段都合格（約三成）": {"探索": L["主判探索"], "確認": L["主判確認"], "成立": L["主判探索"] == "合格" and L["主判確認"] == "合格"},
        "② 平均股票部位比例 ＜ 60%（約六成五）": {sg: float(row("M", sg)["平均股票部位比例"]) for sg in W["segp"]},
        "③ 與營量 v1 月報酬相關 ＜ 0.6（約六成）": {sg: (J["營量v1"][sg] or {}).get("月報酬相關") for sg in W["segp"]},
        "④ 滑價版仍不低於另列（約五成）": {"探索": L["滑價探索"], "確認": L["滑價確認"],
                                  "成立": L["滑價探索"] in ("合格", "另列") and L["滑價確認"] in ("合格", "另列")}}
    J["先驗對照"]["② 平均股票部位比例 ＜ 60%（約六成五）"]["成立(兩段皆＜60%)"] = bool(all(row("M", sg)["平均股票部位比例"] < 0.6 for sg in W["segp"]))
    J["先驗對照"]["③ 與營量 v1 月報酬相關 ＜ 0.6（約六成）"]["成立(兩段皆＜0.6)"] = bool(all(
        ((J["營量v1"][sg] or {}).get("月報酬相關") or 1) < 0.6 for sg in W["segp"]))
    log(f"[先驗] {json.dumps(J['先驗對照'], ensure_ascii=False, default=float)}")
    rq = pj["引自頻率表"]["上季切點入選比例(每季)"]
    ovp = [pj["引自頻率表"]["與EPS季增重疊"][sg] for sg in ("探索", "確認")]
    tail = ["單筆層兩段都比隨便買好，但組合是另一回事", f"每季實際入選 {rq['最小'] * 100:.0f}%～{rq['最大'] * 100:.0f}%", "台股有月營收先揭露", "早年無上傳時戳不做",
            f"與單季 EPS 季增重疊 {min(ovp) * 100:.0f}～{max(ovp) * 100:.0f}%（該件不合格）", "沒事件時抱 0050", PP.SENT_396,
            "早年無上傳時戳 ⇒ 兩段合格也只寫暫定（seq398）"]
    sents = {}
    for sg in W["segp"]:
        z = row("M", sg); zs = row("Mslip", sg)
        sents[sg] = (f"PEAD 組合層（SUE 最高十分位上傳後抱 60 日、日曆時間組合、每檔 1/max(n,10)、其餘抱 0050）{sg}段：年化 {pct(z['年化'])}、最大回落 {pct(z['回落'])}、"
                     f"比值 {z['比值']:.2f}（0050 {pct(z['0050年化'])}、{pct(z['0050回落'])}、{z['0050比值']:.2f}）⇒ {z['標籤']}；平均股票部位 {z['平均股票部位比例'] * 100:.0f}%；"
                     f"滑價每邊 +0.5% 版：年化 {pct(zs['年化'])}、回落 {pct(zs['回落'])} ⇒ {zs['標籤']}｜" + "；".join(tail))
    sents["整件"] = f"PEAD 組合層整件：{v1}" + (f"（{'；'.join(why)}）" if why else "") + "｜" + "；".join(tail)
    J["結果句"] = sents
    for k, s in sents.items():
        log(f"[結果句 {k}] {s}")
    J["N"] = {"本件": "N_組合 ＋1（判定 1 件；滑價版為可執行性條款；10 檔版、同季切點、20／120 日、營量相關／重疊／各半、部位時序 皆描述不計）"}
    J["耗時秒"] = round(time.time() - T0); J["時點"]["完成"] = now_tpe()
    J["讀法"] = __doc__.split("═══ 讀法")[1]
    json.dump(J, open(os.path.join(OUT, "PEADpf.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] {J['耗時秒']}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=2)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    log = RA.log_to(os.path.join(OUT, "dry.log" if a.dry else "run.log"))
    run(a, log)


if __name__ == "__main__":
    main()
