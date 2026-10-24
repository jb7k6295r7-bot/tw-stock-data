# -*- coding: utf-8 -*-
"""產業挑法的好壞比例分佈 台股 seq1【三種分佈・正式跑程式；目前只准 --dry】（台股策略線 登錄 sha 0e149f0996373817；裁定 seq463 §二：描述、⛔ 不判定、不計 N；
頻率表先交、全部描述欄先乾跑（seq458／459））——回測線計算子代理。
⛔ 正式跑（不帶 --dry）須 --ruling <裁定號>（裁定核頻率表後），否則拒跑。⛔ seq366：乾跑時價格與報酬全寫常數（倍數 1、R 0、大盤 0），
   不用任何進場後價格值計算（價格面板與大盤只載入、不取值）；只用頻率表已有的結構旗標（日曆位置、壞根、下市位置）與營收期別結構。
⛔ 不 commit、不改既有檔；researchPickDist_freq（build、main、常數）、researchRevTurn_freq、researchShortageExit（seam_open、lastvalid_le）、
   researchIndMom_freq（reg_check、entry_flag）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPickDist --dry          # 乾跑（輸出 ~/pkdwork/dry）
    ...                                                       -m backtest.researchPickDist --selftest     # 合成資料自測（分桶、年化、CI）
    ...                                                       -m backtest.researchPickDist --ruling seqNNN  # 正式跑（⛔ 等裁定）
輸出（正式）backtest/resultsPickDist/main/：main.json、cells.csv、diff.csv、yearly.csv、industry.csv、market.csv、ungated.csv、run.log（⛔ 逐事件報酬不進 repo，存 ~/pkdwork）

═══ 讀法（Q 標；頻率表 P0～P11 原樣沿用；⛔ 在看任何本件結果之前寫死於 2026-10-24（台北）；★＝執行者定）═══
 Q1 事件 ＝ 頻率表：先以 researchPickDist_freq.main 原樣（同一 --sha）重建到 ~/pkdwork/rebuild，所有 csv 與 resultsPickDist/freq 逐字比；不同 ⇒ 中止。
    主格 ＝ e 可進場 ∧ e＋750 ≤ 資料尾。丁 ＝ 每月全部過閘可進場股（不去重）。無閘版（描述）＝ 頻率表無閘事件，進場與走得完同式重算。
 Q2 進場價 P0 ＝ e 還原開盤（主世界開盤乘接縫倍數，researchShortageExit.seam_open，＝ 3 倍命中率 M2）。
    路徑 ＝ 還原收盤 [e, x]、x ＝ e＋750；(e, x] 有壞根 ⇒ x 截在第一個壞根前一根（seq335）；最後有效 K 棒 ＜ x 且距資料尾 ≥ 5 日 ⇒ 下市，x ＝ 最後有效 K 棒（以最後收盤計）。
    終值 ＝ x 當天或之前最後有效收盤。
 Q3 ① 最高倍數 M ＝ max(路徑收盤) ÷ P0 ⇒ ≥3｜[2,3)｜[1.2,2)｜＜1.2（★ 左閉右開）。
    ② R2 ＝ 終值 ÷ P0 − 1 − 0.585% ⇒ ≥+200%｜[+100%,+200%)｜[+20%,+100%)｜(−20%,+20%)（持平）｜(−50%,−20%]｜≤−50%（腰斬）（★ 邊界：+20% 歸 +20～100、−20% 歸 −50～−20）；
    曾腰斬 ＝ 路徑最低收盤 ≤ 0.5 × P0。
 Q4 ③ 小部位規則（登錄 §三；小部位 seq8 原文）：進場 1 份；之後第 k ＝ 1..12 個判日（期別 P＋k 的可用日 A_k）：★ 第一個 up(P＋k) 為真者 ⇒ A_k＋1 開盤加 2 份
    （進場時已轉強者同式：進場當期不算，從 k＝1 起看；〔另一讀法：已轉強者只看 k＝1〕）；該期無營收列 ⇒ 不算轉強（小部位 seq3「該期不判」，★ 但仍占一個判日）。
    加碼者抱到 x 收盤：R3 ＝ (終值÷P0 ＋ 2 × 終值÷P_add) ÷ 3 − 1 − 0.585%；H ＝ x − e。
    12 個都沒轉強 ⇒ A_12＋1 開盤賣：R3 ＝ P_s ÷ P0 − 1 − 0.585%，H ＝ (A_12＋1) − e。
    ★ 加碼日或賣出日在截斷點 x 之後 ⇒ 不加碼／以 x 收盤結算（標「截斷先到」）；加碼日、賣出日無有效開盤 ⇒ 順延到下一根有效開盤（不超過 x，否則同上）。
    每筆年化（seq460）＝ max(1＋R3, 0)^(250 ÷ max(H, 60)) − 1，主報中位；確認率 ＝ 加碼筆數 ÷ 筆數。
 Q5 大盤 ＝ data/history/market_tri.csv（報酬指數，只有收盤；合併日曆 ffill）。開盤進場 ⇒ 用 e−1 收盤；收盤出 ⇒ x 收盤；開盤出 ⇒ 出場日前一日收盤（＝ 燈號交易 Q7）。
    ② 大盤 ＝ TRI[x]÷TRI[e−1]−1；① 大盤倍數 ＝ max(TRI[e..x])÷TRI[e−1]；③ 大盤 ＝ 同樣份數與日期投入大盤（加碼：(TRI[x]÷TRI[e−1] ＋ 2·TRI[x]÷TRI[a−1])÷3−1；未加碼：TRI[s−1]÷TRI[e−1]−1）。
    超額 ＝ 個股 − 大盤；報中位（另報平均）。大盤不扣成本。
 Q6 描述比較（⛔ 不判定）：甲−丙、乙−丙 的「① ≥3 比例」「② 腰斬比例（R2 ≤ −50%）」「② 中位」三項差（各段）；
    比例差 95% CI ＝ 月分群穩健標準誤（兩組差的 cluster-robust，G/(G−1) 修正；月 ＝ 判日月）；中位差 95% CI ＝ 月分群 bootstrap（1000 次，rng 20261024，百分位）。
    任一臂該段 n_eff ＜ 24 ⇒ 標「樣本不足」。⚠ 750 日重疊 ⇒ CI 偏窄，只描述。
 Q7 分年（判日年）、分產業（industry_pit，兩段合計）、上市／上櫃：同一套統計（件數、n_eff、①②③ 分桶、中位）。
 Q8 必附：頻率表 P11 三句。seq373（同根兩出場價取較低）：本件只用收盤與開盤單一價、無同根兩出場價 ⇒ 不適用（照註）。
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import pickle
import shutil
import subprocess
import sys
import time
from collections import Counter

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchPickDist_freq as PF            # noqa: E402  頻率表（⛔ 只 import）
from backtest import researchRevTurn_freq as RT             # noqa: E402
from backtest import researchShortageExit as SM             # noqa: E402  seam_open、lastvalid_le
from backtest import researchIndMom_freq as IMF             # noqa: E402

OUT = "backtest/resultsPickDist/main"
FREQ = PF.OUT
REB = os.path.join(PF.TW, "rebuild")
DRY = os.path.join(PF.TW, "dry")
COST = 0.00585
NK = 12
SEED = 20261024
NBOOT = 1000
FILES = ["events_甲.csv.gz", "events_乙.csv.gz", "events_丙.csv.gz", "events_丁.csv.gz", "freq_段.csv", "base_段.csv", "hist_days.csv",
         "industry.csv", "yearly.csv", "equiv.csv"]
B1 = [("≥3倍", 3.0, np.inf), ("2～3倍", 2.0, 3.0), ("1.2～2倍", 1.2, 2.0), ("<1.2倍", -np.inf, 1.2)]
B2N = ["≥+200%", "+100～+200%", "+20～+100%", "−20～+20%(持平)", "−50～−20%", "≤−50%(腰斬)"]
LOG = PF.LOG
log = PF.log


# ═════════════ 分桶、年化、CI（純函式；--selftest 驗）═════════════
def bin1(m):
    m = np.asarray(m, float)
    return {nm: (m >= lo) & (m < hi) for nm, lo, hi in B1}


def bin2(r):
    r = np.asarray(r, float)
    return {B2N[0]: r >= 2.0, B2N[1]: (r >= 1.0) & (r < 2.0), B2N[2]: (r >= 0.2) & (r < 1.0), B2N[3]: (r > -0.2) & (r < 0.2),
            B2N[4]: (r > -0.5) & (r <= -0.2), B2N[5]: r <= -0.5}


def annualize(r, h):
    r = np.asarray(r, float); h = np.asarray(h, float)
    base = np.maximum(1.0 + r, 0.0)
    return np.power(base, 250.0 / np.maximum(h, 60.0)) - 1.0


def cl_diff(ya, ma, yc, mc, z=1.96):
    """兩組平均差的月分群穩健 CI（Q6）。空組 ⇒ NaN。"""
    ya = np.asarray(ya, float); yc = np.asarray(yc, float)
    if not len(ya) or not len(yc):
        return {"差": np.nan, "下界": np.nan, "上界": np.nan, "G": 0}
    d = ya.mean() - yc.mean()
    ua = pd.Series((ya - ya.mean()) / len(ya)).groupby(np.asarray(ma)).sum()
    uc = pd.Series((yc - yc.mean()) / len(yc)).groupby(np.asarray(mc)).sum()
    u = ua.sub(uc, fill_value=0.0).to_numpy(float)
    G = len(u)
    if G < 2:
        return {"差": float(d), "下界": np.nan, "上界": np.nan, "G": G}
    se = float(np.sqrt(G / (G - 1) * np.sum(u ** 2)))
    return {"差": float(d), "下界": float(d - z * se), "上界": float(d + z * se), "G": G}


def boot_median_diff(ya, ma, yc, mc, rng, nb=NBOOT):
    ya = np.asarray(ya, float); yc = np.asarray(yc, float)
    if not len(ya) or not len(yc):
        return {"差": np.nan, "下界": np.nan, "上界": np.nan, "G": 0}
    d = float(np.median(ya) - np.median(yc))
    months = sorted(set(np.asarray(ma).tolist()) | set(np.asarray(mc).tolist()))
    ga = pd.Series(ya).groupby(np.asarray(ma)).apply(np.array).to_dict()
    gc = pd.Series(yc).groupby(np.asarray(mc)).apply(np.array).to_dict()
    G = len(months); out = []
    if G < 2:
        return {"差": d, "下界": np.nan, "上界": np.nan, "G": G}
    for _ in range(nb):
        s = rng.integers(0, G, G)
        xa = [ga[months[k]] for k in s if months[k] in ga]; xc = [gc[months[k]] for k in s if months[k] in gc]
        if not xa or not xc:
            continue
        out.append(np.median(np.concatenate(xa)) - np.median(np.concatenate(xc)))
    if not out:
        return {"差": d, "下界": np.nan, "上界": np.nan, "G": G}
    return {"差": d, "下界": float(np.percentile(out, 2.5)), "上界": float(np.percentile(out, 97.5)), "G": G}


def stats(d):
    """一組主格事件 ⇒ 一列統計（空組也回一列）。"""
    n = len(d)
    row = {"件數": n, "n_eff": int(d["月"].nunique()) if n else 0}
    row["樣本不足(n_eff<24)"] = row["n_eff"] < PF.NEFF_MIN
    if not n:
        return row
    for nm, m in bin1(d["M"]).items():
        row[f"①{nm}"] = float(m.mean())
    for nm, m in bin2(d["R2"]).items():
        row[f"②{nm}"] = float(m.mean())
    row["②曾腰斬"] = float(d["曾腰斬"].mean())
    row["②平均"] = float(d["R2"].mean()); row["②中位"] = float(d["R2"].median())
    row["①超額中位(倍數−大盤倍數)"] = float((d["M"] - d["M大盤"]).median())
    row["②超額中位"] = float((d["R2"] - d["R2大盤"]).median()); row["②超額平均"] = float((d["R2"] - d["R2大盤"]).mean())
    for nm, m in bin2(d["R3"]).items():
        row[f"③{nm}"] = float(m.mean())
    row["③平均"] = float(d["R3"].mean()); row["③中位"] = float(d["R3"].median())
    row["③每筆年化中位"] = float(d["年化"].median()); row["③每筆年化平均"] = float(d["年化"].mean())
    row["③確認率"] = float(d["確認"].mean()); row["③H中位"] = float(d["H"].median())
    row["③超額中位"] = float((d["R3"] - d["R3大盤"]).median()); row["③超額平均"] = float((d["R3"] - d["R3大盤"]).mean())
    row["截斷或下市"] = int((d["狀態"] != "完整").sum())
    return row


# ═════════════ 結果變數（Q2～Q5）═════════════
def pplus(P, k):
    y, m = int(P[:4]), int(P[5:7]) + k
    y += (m - 1) // 12; m = (m - 1) % 12 + 1
    return f"{y:04d}-{m:02d}"


def outcome(ctx, sid, i, A_, P, idx, dry):
    PX = ctx["PX"]; CEND = ctx["CEND"]; BAD = PX["BAD"]; LASTV = PX["LASTV"]; O = ctx["O"]; C = PX["C"]; TRI = ctx["TRI"]
    e = A_ + 1; x = e + PF.HJ; st = "完整"
    bb = np.flatnonzero(BAD[i, e + 1:x + 1])
    if len(bb):
        x = e + int(bb[0]); st = "壞根截斷"
    lv = int(LASTV[i])
    if (CEND - lv) >= 5 and lv < x:
        x = lv; st = "下市末根"
    # ③ 時程（結構：判日位置）
    akp = []
    for k in range(1, NK + 1):
        Pk = pplus(P, k)
        akp.append((Pk, ctx["APOS"](Pk)))
    if dry:
        upk = [(k == 1 and idx % 3 == 0) for k in range(1, NK + 1)]        # 常數模式（非真資料）：每 3 筆 1 筆第 1 判日確認
        _ = [ctx["UP"].get((sid, Pk), False) for Pk, _a in akp]            # 走一次真查表路徑（結果丟棄）
    else:
        upk = [ctx["UP"].get((sid, Pk), False) for Pk, _a in akp]

    def nextopen(p):
        if dry:
            return p if p <= x else None
        while p <= x:
            if np.isfinite(O[i, p]) and O[i, p] > 0:
                return p
            p += 1
        return None
    add = None; sell = None; cut_first = False
    for k, (Pk, Ak) in enumerate(akp):
        if Ak is None or Ak + 1 > x:
            cut_first = True; break
        if upk[k]:
            add = nextopen(Ak + 1)
            if add is None:
                cut_first = True
            break
        if k == NK - 1:
            sell = nextopen(Ak + 1)
            if sell is None:
                cut_first = True
    H = (x - e) if (add is not None or cut_first or sell is None) else (sell - e)
    res = {"x": x, "狀態": st, "確認": add is not None, "截斷先到": bool(cut_first), "H": int(H)}
    if dry:
        res.update(M=1.0, R2=0.0, 曾腰斬=False, M大盤=1.0, R2大盤=0.0, R3=0.0, R3大盤=0.0)
        return res
    P0 = O[i, e]
    seg = C[i, e:x + 1]; v = seg[np.isfinite(seg)]
    xv = SM.lastvalid_le(PX["VP"], i, x)
    if not (np.isfinite(P0) and P0 > 0) or not len(v) or xv < e:
        res.update(M=np.nan, R2=np.nan, 曾腰斬=np.nan, M大盤=np.nan, R2大盤=np.nan, R3=np.nan, R3大盤=np.nan, 狀態="無價")
        return res
    fin = float(C[i, xv])
    tb = TRI[e - 1]
    res["M"] = float(v.max() / P0); res["R2"] = fin / P0 - 1 - COST; res["曾腰斬"] = bool(v.min() <= 0.5 * P0)
    res["M大盤"] = float(np.nanmax(TRI[e:x + 1]) / tb); res["R2大盤"] = float(TRI[x] / tb - 1)
    if add is not None:
        Pa = O[i, add]
        res["R3"] = (fin / P0 + 2 * fin / Pa) / 3 - 1 - COST
        res["R3大盤"] = float((TRI[x] / tb + 2 * TRI[x] / TRI[add - 1]) / 3 - 1)
    elif sell is not None and not cut_first:
        res["R3"] = float(O[i, sell] / P0 - 1 - COST); res["R3大盤"] = float(TRI[sell - 1] / tb - 1)
    else:
        res["R3"] = res["R2"]; res["R3大盤"] = res["R2大盤"]
    return res


def load_tri(sha, CAL):
    tri = pd.read_csv(io.BytesIO(subprocess.run(["git", "show", f"{sha}:data/history/market_tri.csv"], capture_output=True, check=True).stdout))
    tri["date"] = pd.to_datetime(tri["date"]); tri = tri.set_index("date")["close"].astype(float)
    nfill = int((~CAL.isin(tri.index)).sum())
    return tri.reindex(tri.index.union(CAL)).ffill().reindex(CAL).to_numpy(float), nfill


# ═════════════ 自測 ═════════════
def selftest():
    m = np.array([3.0, 2.999, 2.0, 1.2, 1.1999, 0.5])
    b = bin1(m); assert [int(b[k].sum()) for k, *_ in B1] == [1, 2, 1, 2], b
    r = np.array([2.0, 1.0, 0.2, 0.19, -0.2, -0.5, -0.51, 0.0, -0.19])
    b = bin2(r); got = [int(b[k].sum()) for k in B2N]; assert got == [1, 1, 1, 3, 1, 2], got
    tot = sum(b[k].astype(int) for k in B2N); assert (tot == 1).all()
    a = annualize([0.0, 1.0, -1.2, 0.1], [750, 250, 30, 30])
    assert abs(a[0]) < 1e-12 and abs(a[1] - 1.0) < 1e-12 and a[2] == -1.0 and abs(a[3] - (1.1 ** (250 / 60) - 1)) < 1e-12, a
    c = cl_diff([1, 1, 0, 0], ["a", "a", "b", "b"], [0, 0], ["a", "b"]); assert abs(c["差"] - 0.5) < 1e-12 and c["G"] == 2, c
    c = cl_diff([], [], [1.0], ["a"]); assert np.isnan(c["差"])
    c = cl_diff([1.0], ["a"], [0.0], ["a"]); assert c["G"] == 1 and np.isnan(c["下界"])
    bm = boot_median_diff([0, 0, 0], ["a", "b", "c"], [0, 0], ["a", "c"], np.random.default_rng(1), nb=50); assert bm["差"] == 0 and bm["下界"] == 0
    assert pplus("2023-11", 2) == "2024-01" and pplus("2023-12", 12) == "2024-12"
    e = pd.DataFrame(columns=["月", "M", "R2", "曾腰斬", "M大盤", "R2大盤", "R3", "R3大盤", "年化", "確認", "H", "狀態"]); s = stats(e)
    assert s["件數"] == 0 and s["樣本不足(n_eff<24)"]
    log("[自測] 分桶、年化、CI、空組、期別加月 全過")


# ═════════════ 主程式 ═════════════
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); ap.add_argument("--dry", action="store_true")
    ap.add_argument("--ruling", default=None); ap.add_argument("--selftest", action="store_true"); ap.add_argument("--sha", default=PF.SHA_PIN)
    ap.add_argument("--no-rebuild", action="store_true", help="乾跑除錯用：不重建頻率表、直接讀既有逐事件位置檔")
    a = ap.parse_args()
    if a.selftest:
        selftest(); return
    if not a.dry:
        if not a.ruling:
            raise SystemExit("⛔ 正式跑須 --ruling <裁定號>（裁定核頻率表後）；目前只准 --dry（seq366、seq458）")
        rf = [f for d in [IMF.MAILBOX] + sorted(glob.glob(os.path.join(IMF.MAILBOX, "_封存-*"))) for f in glob.glob(os.path.join(d, "*.md"))
              if a.ruling in os.path.basename(f) and "挑法" in os.path.basename(f)]
        if not rf:
            raise SystemExit(f"⛔ 信箱找不到裁定 {a.ruling}（檔名須含「挑法」）")
        log(f"[裁定] {os.path.basename(rf[0])}")
    selftest()
    t0 = time.time()
    out = DRY if a.dry else OUT
    os.makedirs(out, exist_ok=True)
    reg = IMF.reg_check(PF.REG_SHA); log(f"[登錄] {reg}")
    if a.no_rebuild and a.dry:
        pk = os.path.join(PF.TW, f"events_{a.sha[:12]}.pkl")
        same = {"略過": True}
    else:
        if os.path.isdir(REB):
            shutil.rmtree(REB)
        argv = sys.argv; sys.argv = ["researchPickDist_freq", "--procs", str(a.procs), "--sha", a.sha, "--out", REB]
        try:
            PF.main()
        finally:
            sys.argv = argv
        same = {}
        for f in FILES:
            pa, pb = os.path.join(REB, f), os.path.join(FREQ, f)
            if not os.path.exists(pb):
                same[f] = "頻率表無此檔"; continue
            x_ = pd.read_csv(pa, dtype=str, keep_default_na=False); y_ = pd.read_csv(pb, dtype=str, keep_default_na=False)
            same[f] = bool(x_.shape == y_.shape and (x_.columns == y_.columns).all() and x_.equals(y_))
        log(f"[Q1 重建] {same}")
        if not all(v is True for v in same.values()):
            if not a.dry:
                raise SystemExit(f"⛔ 頻率表重建不同：{same}")
            log("⚠ 乾跑：重建與 resultsPickDist/freq 不完全相同（照記，正式跑會中止）")
        pk = os.path.join(PF.TW, f"events_{a.sha[:12]}.pkl")
    Z = pickle.load(open(pk, "rb"))
    sha, DN, MD = RT.ensure_data(a.sha)
    PX = RT.prices(sha, DN, a.procs)
    CAL = PX["CAL"]; CEND = len(CAL) - 1; ix = PX["ix"]
    O, nseam = SM.seam_open(PX)
    TRI, nfill = load_tri(sha, CAL)
    RV, _ = RT.rev_table(MD, PX["SIDS"], a.procs, tag=PF.TP.RV_TAG)
    UP = {(s, p): bool(u) for s, p, u in zip(RV["sid"], RV["period"], RV["up"])}
    apc = {}

    def APOS(P):
        if P not in apc:
            v = RT.avail_pos(CAL, [P])[P]
            apc[P] = v if v <= CEND else None
        return apc[P]
    ctx = {"PX": PX, "CEND": CEND, "O": O, "TRI": TRI, "UP": UP, "APOS": APOS}

    def run(E):
        rows = []
        for k, r in enumerate(E.itertuples(index=False)):
            rows.append(outcome(ctx, r.sid, int(r.i), int(r.Apos), r.期別, k, a.dry))
        R = pd.DataFrame(rows)
        X = pd.concat([E.reset_index(drop=True), R], axis=1)
        if len(X):
            X["年化"] = annualize(X["R3"], X["H"])
        else:
            X["年化"] = []
        return X
    RES = {}
    for arm in PF.ARMS:
        E = Z["E"][arm]
        E = E[E["主格"]].reset_index(drop=True) if len(E) else E
        RES[arm] = run(E) if len(E) else pd.DataFrame(columns=list(E.columns) + ["M", "R2", "曾腰斬", "M大盤", "R2大盤", "R3", "R3大盤", "確認", "H", "狀態", "年化"])
        log(f"[結果] {arm} 主格 {len(RES[arm])}｜{time.time() - t0:.0f}s")
    # 無閘版（Q1）：頻率表無閘事件 ⇒ 進場、走得完同式
    UNG = {}
    for arm in PF.ARMS:
        K = Z["EVng"][arm]
        rows = []
        for sid, i, A_, mk, P in K:
            e = A_ + 1
            if e + PF.HJ > CEND:
                continue
            if IMF.entry_flag(PX, i, A_ - 1, e) != "保留":
                continue
            rows.append({"sid": sid, "i": i, "Apos": A_, "期別": P, "段": PF.segname(CAL[A_]), "月": f"{CAL[A_].year}-{CAL[A_].month:02d}"})
        E = pd.DataFrame(rows, columns=["sid", "i", "Apos", "期別", "段", "月"])
        UNG[arm] = run(E) if len(E) else pd.DataFrame(columns=list(E.columns) + ["M", "R2", "曾腰斬", "M大盤", "R2大盤", "R3", "R3大盤", "確認", "H", "狀態", "年化"])
        log(f"[無閘] {arm} 主格 {len(UNG[arm])}｜{time.time() - t0:.0f}s")

    segs = [s[0] for s in PF.SEGS]
    CELL = []
    for arm in PF.ARMS:
        for nm in segs + ["兩段合計"]:
            d = RES[arm]; d = d[d["段"].isin(segs)] if nm == "兩段合計" else d[d["段"] == nm]
            CELL.append({"臂": arm, "段": nm, **stats(d)})
    CELL = pd.DataFrame(CELL)
    rng = np.random.default_rng(SEED)
    DF = []
    for arm in ("甲", "乙"):
        for nm in segs:
            da = RES[arm][RES[arm]["段"] == nm]; dc = RES["丙"][RES["丙"]["段"] == nm]
            ne_a, ne_c = int(da["月"].nunique()), int(dc["月"].nunique())
            insuf = ne_a < PF.NEFF_MIN or ne_c < PF.NEFF_MIN
            for item, fa, fc, kind in (("① ≥3 倍比例", (da["M"] >= 3).astype(float), (dc["M"] >= 3).astype(float), "mean"),
                                       ("② 腰斬比例(R2≤−50%)", (da["R2"] <= -0.5).astype(float), (dc["R2"] <= -0.5).astype(float), "mean"),
                                       ("② 中位", da["R2"].astype(float), dc["R2"].astype(float), "median")):
                c = (cl_diff(fa, da["月"], fc, dc["月"]) if kind == "mean" else boot_median_diff(fa, da["月"], fc, dc["月"], rng))
                DF.append({"比較": f"{arm}−丙", "段": nm, "項": item, **c, "n_eff(臂)": ne_a, "n_eff(丙)": ne_c,
                           "樣本不足": insuf, "註": "描述、⛔ 不判定；750 日重疊 ⇒ CI 偏窄"})
    DF = pd.DataFrame(DF)
    YR = []; IND = []; MK = []; UG = []
    for arm in PF.ARMS:
        d = RES[arm]
        d = d[d["段"].isin(segs)]
        for y, x in d.groupby("年"):
            YR.append({"臂": arm, "年(判日)": int(y), **stats(x)})
        for ind, x in d.groupby("產業"):
            IND.append({"臂": arm, "產業": ind, **stats(x)})
        for mk_, x in d.groupby("市場"):
            MK.append({"臂": arm, "市場": mk_, **stats(x)})
        for nm in segs:
            UG.append({"臂": arm, "段": nm, "版本": "無流動性閘", **stats(UNG[arm][UNG[arm]["段"] == nm])})
    YR, IND, MK, UG = (pd.DataFrame(x) for x in (YR, IND, MK, UG))

    # ── 乾跑檢查：無例外、統計格在 n>0 時無 NaN、空組照列
    chk = {}
    for nm_, T in (("cells", CELL), ("yearly", YR), ("industry", IND), ("market", MK), ("ungated", UG)):
        num = T.select_dtypes(include=[np.number])
        nz = T["件數"] > 0
        bad = int(num[nz].isna().sum().sum()) if len(T) else 0
        chk[nm_] = {"列": len(T), "空組列": int((~nz).sum()), "有件數格中 NaN": bad}
    chk["diff"] = {"列": len(DF), "差NaN": int(DF["差"].isna().sum()), "CI NaN": int(DF["下界"].isna().sum())}
    allres = pd.concat([RES[a_] for a_ in PF.ARMS] + [UNG[a_] for a_ in PF.ARMS], ignore_index=True)
    chk["年化非有限"] = int((~np.isfinite(allres["年化"].astype(float))).sum())
    chk["H<1"] = int((allres["H"].astype(float) < 1).sum())
    chk["③狀態"] = {"確認": int(allres["確認"].sum()), "截斷先到": int(allres["截斷先到"].sum()), "筆": len(allres)}
    chk["②狀態"] = dict(Counter(allres["狀態"]))
    log(f"[乾跑檢查] {chk}" if a.dry else f"[檢查] {chk}")

    CELL.to_csv(os.path.join(out, "cells.csv"), index=False, encoding="utf-8-sig")
    DF.to_csv(os.path.join(out, "diff.csv"), index=False, encoding="utf-8-sig")
    YR.to_csv(os.path.join(out, "yearly.csv"), index=False, encoding="utf-8-sig")
    IND.to_csv(os.path.join(out, "industry.csv"), index=False, encoding="utf-8-sig")
    MK.to_csv(os.path.join(out, "market.csv"), index=False, encoding="utf-8-sig")
    UG.to_csv(os.path.join(out, "ungated.csv"), index=False, encoding="utf-8-sig")
    priv = os.path.join(PF.TW, "dry_events" if a.dry else "main_events"); os.makedirs(priv, exist_ok=True)
    for arm in PF.ARMS:
        RES[arm].drop(columns=[c for c in ("i",) if c in RES[arm].columns]).to_csv(os.path.join(priv, f"events_R_{arm}.csv.gz"), index=False,
                                                                                   encoding="utf-8-sig", compression="gzip")
    J = {"性質": ("乾跑（價格、報酬全寫常數；⛔ 不是結果）" if a.dry else "正式跑：描述、⛔ 不判定、不計 N"), "登錄": reg, "origin/main": sha,
         "頻率表重建": same, "接縫開盤倍數檔數": nseam, "大盤補值日": nfill, "檢查": chk, "必附": PF.NOTES[1:4],
         "seq373": "只用收盤與開盤單一價、無同根兩出場價 ⇒ 不適用", "讀法": __doc__.split("═══ 讀法")[1], "秒": round(time.time() - t0)}
    json.dump(J, open(os.path.join(out, "main.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=RT.jdef)
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    log(f"[完成] {out}｜{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
