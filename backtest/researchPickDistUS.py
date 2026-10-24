# -*- coding: utf-8 -*-
"""美股「產業線挑法」好壞比例分佈 seq2【三種分佈・正式跑程式；目前只准 --dry】（美股策略線 登錄 sha 3ce4e52205c08a14；裁定 seq464 核：描述、⛔ 不判、不計 N；
三種分佈與台股 seq1 同口徑）——回測線計算子代理。
⛔ 正式跑（不帶 --dry）須 --ruling <裁定號>，否則拒跑。⛔ seq366：乾跑時價格與報酬全寫常數（倍數 1、R 0、大盤 0），不用任何進場後價格值計算。
⛔⛔ 私有資料：repo 只放彙總；逐事件結果存 ~/pkdwork_us（repo 外）。
⛔ 不 commit、不改既有檔；researchPickDistUS_freq（world、rev_up、main、常數）、researchPickDist（bin1、bin2、annualize、cl_diff、boot_median_diff、stats）、
   researchUSA4（load_fund、key_at）、researchIndMom_freq（reg_check）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPickDistUS --dry          # 乾跑（輸出 ~/pkdwork_us/dry）
    ...                                                       -m backtest.researchPickDistUS --ruling seqNNN  # 正式跑（⛔ 等裁定）
輸出（正式）backtest/resultsPickDistUS/main/：main.json、cells.csv、diff.csv、yearly.csv、gics.csv、index.csv、run.log

═══ 讀法（W 標；頻率表 U0～U10 原樣沿用；⛔ 在看任何本件結果之前寫死於 2026-10-24（台北）；★＝執行者定）═══
 W1 事件 ＝ 頻率表：先以 researchPickDistUS_freq.main 原樣重建到 ~/pkdwork_us/rebuild，所有 csv 與 resultsPickDistUS/freq 逐字比；不同 ⇒ 中止。主格 ＝ 可進場 ∧ 750 走得完。
 W2 進場價 P0 ＝ e 還原開盤；路徑 ＝ 還原收盤 [e, x]、x ＝ e＋750；(e, x] 有斷點（U2）⇒ x 截在第一個斷點前一根；最後有效 K 棒 ＜ x 且距資料尾 ≥ 5 日
    ⇒ 下市（現行下市結算：以最後收盤計）。終值 ＝ x 當天或之前最後有效收盤。
 W3 ①② 與台股 Q3 同式（researchPickDist.bin1／bin2 同一函式）；② R2 扣 0.05% 來回。曾腰斬 ＝ 路徑最低收盤 ≤ 0.5 × P0。
 W4 ③ 美股小部位 seq2 規則：進場後「新季報」＝ 可用日（first_filed 次一交易日）＞ d 的季報，依可用日排序取前 4 份；第 k 份的判讀日 ＝ 其可用日所在月的最後一個交易日 me_k；
    me_k 用 rev_up（U5，看 ≤ me_k 可用的最新季報）判轉強 ⇒ 第一個為真者 me_k＋1 開盤加 2 份、抱到 x 收盤；4 份都沒轉強 ⇒ me_4＋1 開盤賣。
    ★ 兩份季報落在同一月 ⇒ 同一個 me 只判一次（仍算兩份）；進場時已轉強者同式（從第 1 份新季報起看）。
    ★ 判讀日或賣出日在 x 之後 ⇒ 不加碼／以 x 收盤結算（標「截斷先到」）；無有效開盤 ⇒ 順延到下一根有效開盤（不超過 x）。
    ★ x 之前湊不滿 4 份新季報、也沒轉強（含季營收不適用者）⇒ 抱到 x 收盤（標「季報不足」；件數照報）。
    R3、H、每筆年化、確認率 ＝ 台股 Q4 同式（成本 0.05%）。
 W5 大盤 ＝ ^SP500TR（researchUSA4.bench_series，日曆 ffill）；開盤進出用前一日收盤；①②③ 大盤與超額 ＝ 台股 Q5 同式。
 W6 描述比較（⛔ 不判定）：甲−丙、乙−丙 三項差（判斷窗單一段），CI ＝ 台股 Q6 同式（月分群穩健 SE；中位差月分群 bootstrap 1000 次，rng 20261024）；
    n_eff ＜ 24 ⇒ 樣本不足。分年、分 GICS sector、S&P 500／400 分開。
 W7 必附：頻率表 U10 全部。seq373 不適用（同台股 Q8）。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import pickle
import shutil
import sys
import time
from collections import Counter

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchPickDistUS_freq as PU          # noqa: E402  頻率表（⛔ 只 import）
from backtest import researchPickDist as PD                  # noqa: E402  分桶、年化、CI、統計（台美同一函式）
from backtest import researchUSA4 as A4                      # noqa: E402
from backtest import researchIndMom_freq as IMF              # noqa: E402

OUT = "backtest/resultsPickDistUS/main"
FREQ = PU.OUT
REB = os.path.join(PU.TW, "rebuild")
DRY = os.path.join(PU.TW, "dry")
COST = 0.0005
NQ = 4
FILES = ["events_甲.csv.gz", "events_乙.csv.gz", "events_丙.csv.gz", "events_丁.csv.gz", "freq.csv", "base.csv", "yearly.csv", "gics.csv",
         "index.csv", "equiv.csv", "noprice.csv"]
LOG = PU.LOG
log = PU.log
RCOLS = ["M", "R2", "曾腰斬", "M大盤", "R2大盤", "R3", "R3大盤", "確認", "截斷先到", "季報不足", "H", "狀態", "x", "年化"]


def outcome(ctx, t, j, d, idx, dry):
    Wx = ctx["Wx"]; tail = Wx["tail"]; BAD = Wx["BAD"]; C = Wx["C"]; O = Wx["O"]; BS = ctx["BS"]; F = ctx["F"]; cal = Wx["cal"]
    e = d + 1; x = e + PU.HJ; st = "完整"
    bb = np.flatnonzero(BAD[e + 1:x + 1, j])
    if len(bb):
        x = e + int(bb[0]); st = "斷點截斷"
    lv = int(Wx["LV"][j])
    if (tail - lv) >= 5 and lv < x:
        x = lv; st = "下市末根"
    key = A4.key_at(F["SEG"], t, cal[d])
    avs = []
    if key is not None and key in F["revenue"]:
        av = F["revenue"][key][2]
        avs = sorted(set(int(v) for v in av if d < v < 10 ** 8))[:NQ]
    mes = [ctx["ME"][v] for v in avs]

    def nextopen(p):
        if dry:
            return p if p <= x else None
        while p <= x:
            if Wx["V"][p, j] and np.isfinite(O[p, j]) and O[p, j] > 0:
                return p
            p += 1
        return None
    add = sell = None; cut = False; seen = set()
    for k, me in enumerate(mes):
        if me + 1 > x:
            cut = True; break
        if me not in seen:
            seen.add(me)
            ed = int(cal[me].value // 86400_000_000_000)
            u = PU.rev_up(F, key, me, ed)[3]                        # 乾跑也走一次真查表路徑（結果丟棄）
            if dry:
                u = (k == 0 and idx % 3 == 0)                        # 常數模式（非真資料）
            if u:
                add = nextopen(me + 1)
                if add is None:
                    cut = True
                break
        if k == NQ - 1:
            sell = nextopen(me + 1)
            if sell is None:
                cut = True
    short = (add is None and sell is None and not cut)
    H = (sell - e) if (sell is not None and add is None and not cut) else (x - e)
    res = {"x": x, "狀態": st, "確認": add is not None, "截斷先到": bool(cut), "季報不足": bool(short), "H": int(H)}
    if dry:
        res.update(M=1.0, R2=0.0, 曾腰斬=False, M大盤=1.0, R2大盤=0.0, R3=0.0, R3大盤=0.0)
        return res
    P0 = O[e, j]; seg = C[e:x + 1, j]; v = seg[np.isfinite(seg)]
    vx = np.flatnonzero(Wx["V"][e:x + 1, j])
    if not (np.isfinite(P0) and P0 > 0) or not len(v) or not len(vx):
        res.update(M=np.nan, R2=np.nan, 曾腰斬=np.nan, M大盤=np.nan, R2大盤=np.nan, R3=np.nan, R3大盤=np.nan, 狀態="無價")
        return res
    fin = float(C[e + int(vx[-1]), j]); tb = BS[e - 1]
    res["M"] = float(v.max() / P0); res["R2"] = fin / P0 - 1 - COST; res["曾腰斬"] = bool(v.min() <= 0.5 * P0)
    res["M大盤"] = float(np.nanmax(BS[e:x + 1]) / tb); res["R2大盤"] = float(BS[x] / tb - 1)
    if add is not None:
        res["R3"] = (fin / P0 + 2 * fin / O[add, j]) / 3 - 1 - COST
        res["R3大盤"] = float((BS[x] / tb + 2 * BS[x] / BS[add - 1]) / 3 - 1)
    elif sell is not None and not cut:
        res["R3"] = float(O[sell, j] / P0 - 1 - COST); res["R3大盤"] = float(BS[sell - 1] / tb - 1)
    else:
        res["R3"] = res["R2"]; res["R3大盤"] = res["R2大盤"]
    return res


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry", action="store_true"); ap.add_argument("--ruling", default=None)
    ap.add_argument("--no-rebuild", action="store_true")
    a = ap.parse_args()
    if not a.dry:
        if not a.ruling:
            raise SystemExit("⛔ 正式跑須 --ruling <裁定號>（裁定核頻率表後）；目前只准 --dry（seq366、seq458）")
        rf = [f for d in [IMF.MAILBOX] + sorted(glob.glob(os.path.join(IMF.MAILBOX, "_封存-*"))) for f in glob.glob(os.path.join(d, "*.md"))
              if a.ruling in os.path.basename(f) and "挑法" in os.path.basename(f)]
        if not rf:
            raise SystemExit(f"⛔ 信箱找不到裁定 {a.ruling}（檔名須含「挑法」）")
    PD.selftest()
    t0 = time.time()
    out = DRY if a.dry else OUT
    os.makedirs(out, exist_ok=True)
    reg = IMF.reg_check(PU.REG_SHA); log(f"[登錄] {reg}")
    same = {"略過": True}
    if not (a.no_rebuild and a.dry):
        if os.path.isdir(REB):
            shutil.rmtree(REB)
        argv = sys.argv; sys.argv = ["researchPickDistUS_freq", "--out", REB]
        try:
            PU.main()
        finally:
            sys.argv = argv
        same = {}
        for f in FILES:
            pa, pb = os.path.join(REB, f), os.path.join(FREQ, f)
            if not os.path.exists(pb):
                same[f] = "頻率表無此檔"; continue
            x_ = pd.read_csv(pa, dtype=str, keep_default_na=False); y_ = pd.read_csv(pb, dtype=str, keep_default_na=False)
            same[f] = bool(x_.shape == y_.shape and (x_.columns == y_.columns).all() and x_.equals(y_))
        log(f"[W1 重建] {same}")
        if not all(v is True for v in same.values()):
            if not a.dry:
                raise SystemExit(f"⛔ 頻率表重建不同：{same}")
            log("⚠ 乾跑：重建與 resultsPickDistUS/freq 不完全相同（照記，正式跑會中止）")
    Z = pickle.load(open(os.path.join(PU.TW, "events_us.pkl"), "rb"))
    Wx = PU.world(); cal = Wx["cal"]
    F = A4.load_fund(cal)
    BS = A4.bench_series(cal)
    s = pd.Series(np.arange(len(cal)), index=cal)
    mlast = s.groupby([s.index.year, s.index.month]).transform("last").to_numpy()
    ME = {int(p): int(mlast[p]) for p in range(len(cal))}
    ctx = {"Wx": Wx, "F": F, "BS": BS, "ME": ME}
    RES = {}
    for arm in PU.ARMS:
        E = Z["E"][arm]
        E = E[E["主格"]].reset_index(drop=True) if len(E) else E
        rows = [outcome(ctx, r.ticker, int(r.j), int(r.d), k, a.dry) for k, r in enumerate(E.itertuples(index=False))]
        X = pd.concat([E, pd.DataFrame(rows)], axis=1) if rows else pd.DataFrame(columns=list(E.columns) + RCOLS)
        X["年化"] = PD.annualize(X["R3"], X["H"]) if len(X) else []
        RES[arm] = X
        log(f"[結果] {arm} 主格 {len(X)}｜{time.time() - t0:.0f}s")
    CELL = pd.DataFrame([{"臂": PU.ARM_LABEL[arm], "段": "判斷窗", **PD.stats(RES[arm][RES[arm]["段"] == "判斷窗"] if len(RES[arm]) else RES[arm])}
                         for arm in PU.ARMS])
    rng = np.random.default_rng(PD.SEED)
    DF = []
    dc = RES["丙"][RES["丙"]["段"] == "判斷窗"] if len(RES["丙"]) else RES["丙"]
    for arm in ("甲", "乙"):
        da = RES[arm][RES[arm]["段"] == "判斷窗"] if len(RES[arm]) else RES[arm]
        ne_a, ne_c = int(da["月"].nunique()) if len(da) else 0, int(dc["月"].nunique()) if len(dc) else 0
        for item, fa, fc, kind in (("① ≥3 倍比例", (da["M"].astype(float) >= 3).astype(float), (dc["M"].astype(float) >= 3).astype(float), "mean"),
                                   ("② 腰斬比例(R2≤−50%)", (da["R2"].astype(float) <= -0.5).astype(float), (dc["R2"].astype(float) <= -0.5).astype(float), "mean"),
                                   ("② 中位", da["R2"].astype(float), dc["R2"].astype(float), "median")):
            c = PD.cl_diff(fa, da["月"], fc, dc["月"]) if kind == "mean" else PD.boot_median_diff(fa, da["月"], fc, dc["月"], rng)
            DF.append({"比較": f"{arm}−丙", "段": "判斷窗", "項": item, **c, "n_eff(臂)": ne_a, "n_eff(丙)": ne_c,
                       "樣本不足": ne_a < PD.PF.NEFF_MIN or ne_c < PD.PF.NEFF_MIN, "註": "描述、⛔ 不判定；750 日重疊、年代集中 ⇒ CI 偏窄"})
    DF = pd.DataFrame(DF)
    YR = []; GI = []; IX = []
    for arm in PU.ARMS:
        d = RES[arm]
        if not len(d):
            continue
        d = d[d["段"] == "判斷窗"]
        for y, x in d.groupby("年"):
            YR.append({"臂": PU.ARM_LABEL[arm], "年(判斷日)": int(y), **PD.stats(x)})
        for g_, x in d.groupby("GICS"):
            GI.append({"臂": PU.ARM_LABEL[arm], "GICS sector": g_, **PD.stats(x)})
        for g_, x in d.groupby("指數"):
            IX.append({"臂": PU.ARM_LABEL[arm], "指數": g_, **PD.stats(x)})
    YR, GI, IX = pd.DataFrame(YR), pd.DataFrame(GI), pd.DataFrame(IX)
    chk = {}
    for nm_, T in (("cells", CELL), ("yearly", YR), ("gics", GI), ("index", IX)):
        num = T.select_dtypes(include=[np.number]); nz = T["件數"] > 0
        chk[nm_] = {"列": len(T), "空組列": int((~nz).sum()), "有件數格中 NaN": int(num[nz].isna().sum().sum()) if len(T) else 0}
    chk["diff"] = {"列": len(DF), "差NaN": int(DF["差"].isna().sum()), "CI NaN": int(DF["下界"].isna().sum())}
    allr = pd.concat([RES[a_] for a_ in PU.ARMS], ignore_index=True)
    chk["年化非有限"] = int((~np.isfinite(allr["年化"].astype(float))).sum()); chk["H<1"] = int((allr["H"].astype(float) < 1).sum())
    chk["③狀態"] = {"確認": int(allr["確認"].sum()), "截斷先到": int(allr["截斷先到"].sum()), "季報不足": int(allr["季報不足"].sum()), "筆": len(allr)}
    chk["②狀態"] = dict(Counter(allr["狀態"]))
    log(f"[乾跑檢查] {chk}" if a.dry else f"[檢查] {chk}")
    CELL.to_csv(os.path.join(out, "cells.csv"), index=False, encoding="utf-8-sig")
    DF.to_csv(os.path.join(out, "diff.csv"), index=False, encoding="utf-8-sig")
    YR.to_csv(os.path.join(out, "yearly.csv"), index=False, encoding="utf-8-sig")
    GI.to_csv(os.path.join(out, "gics.csv"), index=False, encoding="utf-8-sig")
    IX.to_csv(os.path.join(out, "index.csv"), index=False, encoding="utf-8-sig")
    priv = os.path.join(PU.TW, "dry_events" if a.dry else "main_events"); os.makedirs(priv, exist_ok=True)
    for arm in PU.ARMS:
        RES[arm].to_csv(os.path.join(priv, f"events_R_{arm}.csv.gz"), index=False, encoding="utf-8-sig", compression="gzip")
    J = {"性質": ("乾跑（價格、報酬全寫常數；⛔ 不是結果）" if a.dry else "正式跑：描述、⛔ 不判、不計 N"), "登錄": reg, "頻率表重建": same, "檢查": chk,
         "必附": PU.NOTES[1:], "seq373": "不適用", "讀法": __doc__.split("═══ 讀法")[1], "秒": round(time.time() - t0)}
    json.dump(J, open(os.path.join(out, "main.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=lambda o: (o.item() if hasattr(o, "item") else str(o)))
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    log(f"[完成] {out}｜{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
