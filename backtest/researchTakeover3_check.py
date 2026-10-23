# -*- coding: utf-8 -*-
"""私募分組 seq3【獨立對帳】——回測線計算子代理。⛔ 只讀結果夾、不改任何既有檔（只寫結果夾 check.json、check.log）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTakeover3_check [--dry]

K1 登錄 sha 獨立重算（去 pw1 行 sha256 前 16 碼）。
K2 事件與配對 ＝ 頻率表：recon.csv 全同；main/events.csv.gz 的頻率表欄與 freq/events.csv.gz 逐字相同；recon_v4.csv 全 0。
K3 件數守恆（另寫，不用 F3.tags／gsel3）：事件表 2011 起 E3 first12m 列數 ＝ 母體；配到＋未配到、普通股＋非普通股、分組母體＋三欄空白；
   互斥四組加總 ＝ 分組母體 ＝ 配到普通股 − 三欄空白；三個重疊組 是＋否 ＝ 分組母體；重疊組 ＝ 對應互斥組之和（重疊組與互斥組一致）；
   freq.csv 表列數、表.csv 可接 全格 ＝ 另寫篩選的件數；有／無減資、市值兩組加總。
K4 三欄另一條路：私募專區 placement_detail.csv 普通股案（同代號、同決議日）重取三欄，對分組母體逐列比。
K5 報酬另一條路：不用 LV／CB／walk／TM 函式，直接以 C、BAD 陣列與有效 K 棒位置重算每列每窗 R事件、R配對、X（E3 有減資 [+2,+250] 除外，
   該格由 e3v4 重跑之 researchTakeover_check 路徑驗過 ⇒ 這裡比對 e3v4_main 逐列）⇒ 與 events.csv.gz 全列比（相對誤差 ≤ 1e-9）。乾跑 ⇒ 另一條路也寫 0。
K6 表.csv 全格由 events 另寫統計（平均、中位、勝率、月分群 se、n_eff、CI 結果）重算 ⇒ 全格相同。
K7 summary.md 含必附句；git 工作樹相對開跑前只多本件新檔與新結果夾。
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import io
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchTakeover3 as T3                # noqa: E402  只取常數與輸出夾
from backtest import researchTakeover3_freq as F3           # noqa: E402  只取常數、setup、price_panel 參數
from backtest import researchTakeover_freq as TF            # noqa: E402
from backtest import researchRevTurn_freq as RT             # noqa: E402

MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
LOGL: list = []


def log(s):
    print(s, flush=True); LOGL.append(str(s))


def sha_of(f):
    b = open(f, "rb").read()
    return hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]


def gshow(sha, p):
    return pd.read_csv(io.BytesIO(subprocess.run(["git", "show", f"{sha}:{p}"], capture_output=True, check=True).stdout), dtype=str, keep_default_na=False)


def close(a, b):
    a, b = float(a), float(b)
    if np.isnan(a) or np.isnan(b):
        return np.isnan(a) and np.isnan(b)
    return abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))


# ── 另寫的分組（K3、K6）
def mine_flags(E):
    md = E["match_decide_date"] != ""
    com = md & E["sec_kind"].apply(lambda s: any(p == "普通股" for p in s.split("+")))
    full = E["is_strategic"].isin(["0", "1"]) & E["is_insider"].isin(["0", "1"]) & E["control_change"].isin(["0", "1"])
    return md, com, com & full


def mine_sel(E, name):
    md, com, pop = mine_flags(E)
    toks = name.replace("E3_2011起", "ALL").split("_")
    g, rest = toks[0], toks[1:]
    S, I, C = E["is_strategic"], E["is_insider"], E["control_change"]
    m = {"ALL": pd.Series(True, index=E.index), "配到": md, "配到普通股": com, "分組母體": pop,
         "甲是": pop & (S == "1"), "甲否": pop & (S == "0"), "乙是": pop & (I == "1"), "乙否": pop & (I == "0"),
         "丙是": pop & (C == "1"), "丙否": pop & (C == "0"),
         "只策略": pop & (S == "1") & (I == "0"), "只內部人": pop & (S == "0") & (I == "1"),
         "兩者皆是": pop & (S == "1") & (I == "1"), "兩者皆否": pop & (S == "0") & (I == "0")}[g]
    for r in rest:
        if r == "有減資":
            m = m & (E["with_reduction"] == "1")
        elif r == "無減資":
            m = m & (E["with_reduction"] == "0")
        elif r == "市值≤10億":
            m = m & (E["st"] == "保留") & (E["市值組"] == "≤10億")
        elif r == "市值＞10億":
            m = m & (E["st"] == "保留") & (E["市值組"] == "＞10億")
    return E[m]


def my_stat(x, mon):
    x = np.asarray(x, float); mon = np.asarray(mon); ok = np.isfinite(x)
    x, mon = x[ok], mon[ok]; n = len(x)
    if n == 0:
        return {"n": 0}
    mu = x.mean()
    sums = {}
    for v, k in zip(x - mu, mon):
        sums[k] = sums.get(k, 0.0) + v
    se = np.sqrt(sum(s * s for s in sums.values())) / n
    lo, hi = mu - 1.96 * se, mu + 1.96 * se
    ne = min(n, len(sums))
    return {"n": n, "mean": mu, "median": float(np.median(x)), "win": float((x > 0).mean()), "lo": lo, "hi": hi, "months": len(sums), "n_eff": ne,
            "ci": "①" if lo <= 0 <= hi else ("②" if lo > 0 else "③")}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry", action="store_true"); ap.add_argument("--procs", type=int, default=2)
    a = ap.parse_args()
    out = os.path.join(F3.WORK3, "dry3_main") if a.dry else T3.OUT
    CK = {}
    # K1
    fs = [f for d in [MAILBOX] + sorted(glob.glob(os.path.join(MAILBOX, "_封存-*"))) for f in glob.glob(os.path.join(d, "*.md")) if f"sha{F3.REG_SHA}" in os.path.basename(f)]
    CK["K1"] = {"檔": [os.path.basename(f) for f in fs], "相符": bool(fs) and all(sha_of(f) == F3.REG_SHA for f in fs)}
    log(f"[K1] {CK['K1']}")
    # K2
    J = json.load(open(os.path.join(out, "main.json"), encoding="utf-8"))
    rc = pd.read_csv(os.path.join(out, "recon.csv"), encoding="utf-8-sig")
    rv = pd.read_csv(os.path.join(out, "recon_v4.csv"), encoding="utf-8-sig")
    E = pd.read_csv(os.path.join(out, "events.csv.gz"), dtype=str, keep_default_na=False)
    F = pd.read_csv(os.path.join(F3.OUT, "events.csv.gz"), dtype=str, keep_default_na=False)
    same = len(E) == len(F) and all((E[c] == F[c]).all() for c in F.columns)
    rvbad = int(rv.drop(columns=["欄"]).apply(pd.to_numeric, errors="coerce").fillna(0).to_numpy().sum())
    CK["K2"] = {"recon全同": bool(int(rc["不同列數"].sum()) == 0), "頻率表欄逐字相同": bool(same), "recon_v4不同格": rvbad,
                "通過": bool(int(rc["不同列數"].sum()) == 0 and same and rvbad == 0)}
    log(f"[K2] {CK['K2']}")
    # K3
    ev = gshow(J["事件表sha"], "data/meta/takeover_events/takeover_events.csv")
    e3 = ev[ev["class"] == "E3"]
    n_tab = int(((e3["first12m"] == "1") & (e3["date"] >= "2011-01-01")).sum())
    md, com, pop = mine_flags(E)
    blank = com & ~pop
    S, I, C = E["is_strategic"], E["is_insider"], E["control_change"]
    ex = {k: int(len(mine_sel(E, k))) for k in F3.EXCL}
    ov = {k: int(len(mine_sel(E, k))) for k in F3.OVL}
    k3 = {"E3列數": len(e3), "事件表2011起first12m": n_tab, "母體": len(E), "配到": int(md.sum()), "未配到": int((~md).sum()),
          "配到普通股": int(com.sum()), "非普通股": int((md & ~com).sum()), "分組母體": int(pop.sum()), "三欄空白": int(blank.sum()),
          "互斥": ex, "重疊": ov}
    eq = [len(e3) == 3012, n_tab == len(E), k3["配到"] + k3["未配到"] == len(E), k3["配到普通股"] + k3["非普通股"] == k3["配到"],
          k3["分組母體"] + k3["三欄空白"] == k3["配到普通股"], sum(ex.values()) == k3["分組母體"] == k3["配到普通股"] - k3["三欄空白"],
          all(ov[f"{x}是"] + ov[f"{x}否"] == k3["分組母體"] for x in "甲乙丙"),
          ov["甲是"] == ex["只策略"] + ex["兩者皆是"], ov["甲否"] == ex["只內部人"] + ex["兩者皆否"],
          ov["乙是"] == ex["只內部人"] + ex["兩者皆是"], ov["乙否"] == ex["只策略"] + ex["兩者皆否"]]
    # 重疊組與互斥組逐列一致
    G = E[pop]
    eq.append(bool(((G["is_strategic"] == "1") == G["互斥組"].isin(["只策略", "兩者皆是"])).all()))
    eq.append(bool(((G["is_insider"] == "1") == G["互斥組"].isin(["只內部人", "兩者皆是"])).all()))
    eq.append(bool((E.loc[~pop, "互斥組"] == "").all()))
    # 丙：互斥組內丙是之和 ＝ 丙是
    eq.append(sum(int(((G["互斥組"] == k) & (G["control_change"] == "1")).sum()) for k in F3.EXCL) == ov["丙是"])
    # freq.csv、表.csv 件數
    FQ = pd.read_csv(os.path.join(F3.OUT, "freq.csv"), encoding="utf-8-sig")
    TB = pd.read_csv(os.path.join(out, "表.csv"), encoding="utf-8-sig")
    bad_f = bad_t = bad_rd = 0
    for sg, x, y in F3.SEGS3:
        Es = E[(E["date"] >= x) & (E["date"] <= y)]
        for g in T3.all_groups():
            s = mine_sel(Es, g)
            fq = FQ[(FQ["段"] == sg) & (FQ["組"] == g)]
            if len(fq) != 1 or int(fq.iloc[0]["表列數"]) != len(s):
                bad_f += 1
            n_ok = int((s["st"] == "保留").sum())
            tb = TB[(TB["段"] == sg) & (TB["組"] == g)]
            if len(tb) == 0 or (tb["可接"] != n_ok).any():
                bad_t += 1
            if "減資" not in g and "市值" not in g:
                if len(mine_sel(Es, g + "_有減資")) + len(mine_sel(Es, g + "_無減資")) != len(s):
                    bad_rd += 1
                if len(mine_sel(Es, g + "_市值≤10億")) + len(mine_sel(Es, g + "_市值＞10億")) != n_ok:
                    bad_rd += 1
    eq += [bad_f == 0, bad_t == 0, bad_rd == 0]
    k3["freq表列數不符格"] = bad_f; k3["表可接不符格"] = bad_t; k3["減資或市值加總不符"] = bad_rd
    k3["守恆逐項"] = [bool(v) for v in eq]; k3["通過"] = all(eq)
    CK["K3"] = k3
    log(f"[K3] {k3}")
    # K4
    P = gshow(J["事件表sha"], "data/meta/placement_detail/placement_detail.csv")
    P = P[P["sec_kind"] == "普通股"]
    cnt = P.groupby(["stock_id", "decide_date"]).size()
    Pi = P.drop_duplicates(["stock_id", "decide_date"]).set_index(["stock_id", "decide_date"])
    bad4 = 0; multi = 0
    for _, r in G.iterrows():
        k = (r["sid"], r["match_decide_date"])
        if k not in Pi.index:
            bad4 += 1; continue
        multi += int(cnt[k] > 1)
        bad4 += int(any(Pi.loc[k, c] != r[c] for c in ("is_strategic", "is_insider", "control_change")))
    CK["K4"] = {"分組母體": len(G), "不符": bad4, "同日多普通股案": multi, "通過": bad4 == 0}
    log(f"[K4] {CK['K4']}")
    # K5
    F3.setup()
    sha, DN, MD = RT.ensure_data(None)
    PX = TF.price_panel(sha, DN, a.procs); CAL = PX["CAL"]; NC = len(CAL); Cm = PX["C"]; BAD = PX["BAD"]; ix = PX["ix"]
    VPc = {}

    def vp(i):
        if i not in VPc:
            VPc[i] = np.flatnonzero(np.isfinite(Cm[i]))
        return VPc[i]

    def R(i, p0, a_, b_):
        base, end = p0 + a_ - 1, p0 + b_
        if end >= NC:
            return np.nan
        v = vp(i)
        k = int(np.searchsorted(v, base, "right")) - 1
        if base < 0 or k < 0:
            return np.nan
        bv = int(v[k]); last = int(v[-1])
        if last <= base:
            return 0.0
        hi = min(end, last)
        if BAD[i, bv + 1:hi + 1].any():
            return np.nan
        ev_ = int(v[int(np.searchsorted(v, hi, "right")) - 1])
        return Cm[i, ev_] / Cm[i, bv] - 1.0
    V4 = pd.read_csv(os.path.join(T3.V4_MAIN, "events.csv.gz"), dtype=str, keep_default_na=False)
    V4 = V4[V4["類"] == "E3"].set_index(["sid", "date"])
    nbad = ncmp = 0; ex5 = []
    for _, r in E.iterrows():
        if r["st"] != "保留":
            continue
        i = ix[r["sid"]]; p0 = int(CAL.searchsorted(pd.Timestamp(r["day0"])))
        j = ix[r["配對sid"]] if r["配對sid"] else None
        for w, (a_, b_) in T3.WINS.items():
            if r["with_reduction"] == "1" and w == T3.W250:
                v = V4.loc[(r["sid"], r["date"])]
                for c in (f"R{w}", f"配R{w}", f"R{T3.WT}", f"配R{T3.WT}"):
                    x2 = float(v[c]) if v[c] != "" else np.nan
                    if a.dry and np.isfinite(x2):
                        x2 = 0.0
                    x1 = float(r[c]) if r[c] != "" else np.nan
                    ncmp += 1
                    if not close(x1, x2):
                        nbad += 1; ex5.append((r["sid"], r["date"], c))
                continue
            re_ = R(i, p0, a_, b_); rm_ = R(j, p0, a_, b_) if j is not None else np.nan
            if a.dry:
                re_ = 0.0 if np.isfinite(re_) else re_; rm_ = 0.0 if np.isfinite(rm_) else rm_
            for c, x2 in ((f"R{w}", re_), (f"配R{w}", rm_), (f"X{w}", re_ - rm_)):
                x1 = float(r[c]) if r[c] != "" else np.nan
                ncmp += 1
                if not close(x1, x2):
                    nbad += 1; ex5.append((r["sid"], r["date"], c, x1, x2))
    CK["K5"] = {"比對格": ncmp, "不同": nbad, "例": ex5[:5], "通過": nbad == 0}
    log(f"[K5] {CK['K5']}")
    # K6
    E["公告月"] = E["date"].str[:7]
    nb6 = 0; nc6 = 0; ex6 = []
    for _, t in TB.iterrows():
        sg = t["段"]; x, y = [(s[1], s[2]) for s in F3.SEGS3 if s[0] == sg][0]
        s = mine_sel(E[(E["date"] >= x) & (E["date"] <= y) & (E["st"] == "保留")], t["組"])
        w = T3.WT if "截斷" in t["窗"] else t["窗"]
        for pre, key in (("R", "R"), ("X", "X")):
            col = f"{pre}{w}"
            st = my_stat(pd.to_numeric(s[col], errors="coerce"), s["公告月"])
            nc6 += 1
            ok = int(t[f"{key}_n"]) == st["n"]
            if st["n"]:
                ok &= close(t[f"{key}平均"], st["mean"]) and close(t[f"{key}中位"], st["median"]) and close(t[f"{key}勝率"], st["win"])
                if key == "X":
                    ok &= close(t["X_lo"], st["lo"]) and close(t["X_hi"], st["hi"]) and int(t["X_n_eff"]) == st["n_eff"] and t["CI結果(描述)"] == st["ci"]
                    ok &= bool(t["還沒測(n_eff<24)"]) == (st["n_eff"] < 24)
            if not ok:
                nb6 += 1; ex6.append((sg, t["組"], t["窗"], key))
    CK["K6"] = {"比對格": nc6, "不同": nb6, "例": ex6[:5], "通過": nb6 == 0}
    log(f"[K6] {CK['K6']}")
    # K7
    md_txt = open(os.path.join(out, "summary.md"), encoding="utf-8").read()
    need = ["描述，不是選股規則", "事件少", "董事會預定的應募人類別", "不等於實際認購人", "台灣文獻只讀到摘要"]
    before = set(open(os.path.join(F3.WORK3, "git_before.txt")).read().splitlines())
    now = set(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines())
    new = sorted(now - before)
    allowed = ("?? backtest/researchTakeover_e3v4.py", "?? backtest/researchTakeover3_freq.py", "?? backtest/researchTakeover3.py",
               "?? backtest/researchTakeover3_check.py", "?? backtest/resultsTakeover/e3v4_freq/", "?? backtest/resultsTakeover/e3v4_main/",
               "?? backtest/resultsTakeover3/")
    unexpected = [x for x in new if x not in allowed]
    CK["K7"] = {"必附缺": [s for s in need if s not in md_txt], "工作樹新增": new, "非本件": unexpected,
                "通過": not [s for s in need if s not in md_txt] and not unexpected}
    log(f"[K7] {CK['K7']}")
    CK["全部通過"] = all(CK[k].get("通過", CK[k].get("相符")) for k in ("K1", "K2", "K3", "K4", "K5", "K6", "K7"))
    log(f"[全部通過] {CK['全部通過']}")
    json.dump(CK, open(os.path.join(out, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(out, "check.log"), "w", encoding="utf-8").write("\n".join(LOGL) + "\n")


if __name__ == "__main__":
    main()
