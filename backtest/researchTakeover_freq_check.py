# -*- coding: utf-8 -*-
"""公開收購／經營權變動／私募 seq2 頻率表【獨立對帳】——回測線計算子代理。⛔ 只讀結果夾、不改任何既有檔（只寫結果夾的 check.json、check.log）；⛔ 不算任何報酬。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTakeover_freq_check [--dry]

K1 登錄 sha 獨立重算（信箱根目錄＋_封存-*，去 pw1 行 sha256 前 16 碼）。
K2 事件表：(a) 同一 sha 的 build.py 不改規則重建 ⇒ 與 origin/main takeover_events.csv 逐位元相同（證明 v1b 重建法只差規則 A）；
   (b) v1b 重建 E2 76 列、v1c ⊂ v1b、差的 5 列 ＝ README 列名（3432、8455、3702×2、4729）；(c) 各組件數由事件表直接重數 ＝ events.csv。
K3 day0／判日：另一條路（逐列 pandas 日曆比較、收購方時戳以 news 主旨含「公開收購」＋簡稱另掃）重算 ⇒ 對 events.csv。
K4 可接價格原因、各窗狀態：不用 LV／CB，直接以 C、BAD 陣列切片重算（事件與配對公司）⇒ 全列相同。
K5 配對：逐事件另寫迴圈重建橫斷面（Python 迴圈、bisect 分位）⇒ 配對狀態、配對代號、池候選數全列相同。
K6 freq.csv 主要欄由 events.csv.gz 自算相同；輸出無報酬欄；策略鎖 25 支相符；git 工作樹相對開跑前只多 researchTakeover_freq*.py 與 resultsTakeover/。
"""
from __future__ import annotations

import argparse
import bisect
import glob
import hashlib
import io
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchTakeover_freq as TF            # noqa: E402
from backtest import researchRevTurn_freq as RT             # noqa: E402

MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
LOGL: list = []


def log(s):
    print(s, flush=True); LOGL.append(str(s))


def sha_of(f):
    b = open(f, "rb").read()
    return hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--dry", action="store_true"); ap.add_argument("--procs", type=int, default=2)
    a = ap.parse_args()
    out = os.path.join(TF.WORK, "dry") if a.dry else TF.OUT
    CK = {}
    # ── K1
    fs = [f for d in [MAILBOX] + sorted(glob.glob(os.path.join(MAILBOX, "_封存-*"))) for f in glob.glob(os.path.join(d, "*.md")) if f"sha{TF.REG_SHA}" in os.path.basename(f)]
    CK["K1_登錄sha"] = {"檔": [os.path.basename(f) for f in fs], "相符": bool(fs) and all(sha_of(f) == TF.REG_SHA for f in fs)}
    log(f"[K1] {CK['K1_登錄sha']}")
    J = json.load(open(os.path.join(out, "freq.json"), encoding="utf-8")); sha = J["origin/main"]
    E = pd.read_csv(os.path.join(out, "events.csv.gz"), dtype=str, keep_default_na=False)
    # ── K2
    main_b = subprocess.run(["git", "show", f"{sha}:{TF.EVP}"], capture_output=True, check=True).stdout
    cpc, _ = TF.load_build(sha, "v1c", False)
    same_bytes = open(cpc, "rb").read() == main_b
    cpb, _ = TF.load_build(sha, "v1b", True)
    ev = pd.read_csv(io.BytesIO(main_b), dtype=str, keep_default_na=False)
    vb = pd.read_csv(cpb, dtype=str, keep_default_na=False)
    e2c = ev[ev["class"] == "E2"]; e2b = vb[vb["class"] == "E2"]
    kc = set(zip(e2c["stock_id"], e2c["date"])); kb = set(zip(e2b["stock_id"], e2b["date"]))
    extra = sorted(s for s, _ in kb - kc)
    cnt_tab = {"E1": int(((ev["class"] == "E1") & (ev["followup"] == "0") & (ev["first12m"] == "1")).sum()),
               "E2(v1c主)": int(((ev["class"] == "E2") & (ev["first12m"] == "1") & (ev["overlap_e1"] == "0")).sum()),
               "E2含重疊(v1c)": int(((ev["class"] == "E2") & (ev["first12m"] == "1")).sum()),
               "E2(v1b敏感度)": int(((e2b["first12m"] == "1") & (e2b["overlap_e1"] == "0")).sum()),
               "E3": int(((ev["class"] == "E3") & (ev["first12m"] == "1")).sum()),
               "E3_有減資": int(((ev["class"] == "E3") & (ev["first12m"] == "1") & (ev["with_reduction"] == "1")).sum())}
    cnt_ev = {g: len(TF.GROUPS[g](E)) for g in cnt_tab}
    CK["K2_事件表"] = {"build原規則重建＝main表(逐位元)": same_bytes, "v1b E2列數": len(e2b), "v1c⊂v1b": kc <= kb, "v1b多出代號": extra,
                     "多出＝README": extra == sorted(["3432", "8455", "3702", "3702", "4729"]), "表重數": cnt_tab, "events": cnt_ev, "相同": cnt_tab == cnt_ev}
    log(f"[K2] {CK['K2_事件表']}")
    # ── 價格
    sha2, DN, MD = RT.ensure_data(sha)
    PX = TF.price_panel(sha, DN, a.procs)
    CAL = PX["CAL"]; NC = len(CAL); C = PX["C"]; BAD = PX["BAD"]; ix = PX["ix"]
    cal_dates = [d.strftime("%Y-%m-%d") for d in CAL]
    # ── K3 day0
    def d0_alt(date, tm):
        k = bisect.bisect_left(cal_dates, date)
        if k < NC and cal_dates[k] == date and tm != "" and tm >= "13:30:00":
            k += 1
        return k
    # 收購方時戳另掃
    e1 = ev[(ev["class"] == "E1") & (ev["followup"] == "0")]
    news = []
    for y in sorted({int(x[:4]) for x in e1["acq_date"] if x}):
        p = subprocess.run(["git", "show", f"{sha}:data/mops/news/{y}.csv"], capture_output=True)
        x = pd.read_csv(io.BytesIO(p.stdout), dtype=str, keep_default_na=False)
        x = x[x["market"].isin(["sii", "otc"]) & x["subject"].str.replace(r"\s+", "", regex=True).str.contains("公開收購")]
        news.append(x)
    NW = pd.concat(news, ignore_index=True); NW["s"] = NW["subject"].str.replace(r"\s+", "", regex=True)
    MB = TF.load_build(sha, "v1b", True)[1]
    bad3 = Counter(); n3 = 0
    for _, r in E.iterrows():
        n3 += 1
        if r["類"] == "E1" and r["臂"] == "最早日" and r["acq_date"]:
            nm = re.sub(r"[\*＊]|-KY|-創|KY$", "", ev.loc[(ev["stock_id"] == r["sid"]) & (ev["date"] == r["date"]) & (ev["class"] == "E1"), "name"].iloc[0]).strip()
            g = NW[(NW["date"] == r["acq_date"]) & (NW["stock_id"] != r["sid"])]
            g = g[[bool(re.search("公開收購.{0,12}" + re.escape(nm), s)) and not MB.E1_FU.search(s) for s in g["s"]]]
            at = g["time"].min() if len(g) else ""
            p0 = min(d0_alt(r["date"], r["time"]), d0_alt(r["acq_date"], at))
            if at != r["acq_time"]:
                bad3["acq_time"] += 1
        else:
            p0 = d0_alt(r["date"], r["time"])
        want = cal_dates[p0] if 0 < p0 < NC else ""
        if r["day0"] != "" and r["day0"] != want:
            bad3["day0"] += 1
        if r["T"] != "" and r["T"] != cal_dates[p0 - 1]:
            bad3["T"] += 1
    CK["K3_day0"] = {"列": n3, "不符": dict(bad3)}
    log(f"[K3] {CK['K3_day0']}")
    # ── K4
    def vpos(i):
        return np.flatnonzero(np.isfinite(C[i]))

    VPc = {}

    def lastv(i, p):
        if i not in VPc:
            VPc[i] = vpos(i)
        v = VPc[i]; k = int(np.searchsorted(v, p, "right"))
        return int(v[k - 1]) if k > 0 else -1

    def walk2(i, p0, a_, b_):
        base = p0 + a_ - 1; end = p0 + b_
        if end > NC - 1:
            return "超出資料尾"
        bv = lastv(i, base) if base >= 0 else -1
        if bv < 0:
            return "起點無K棒"
        last = lastv(i, NC - 1)
        if last <= base:
            return "下市長停截斷"
        if BAD[i, bv + 1:min(end, last) + 1].any():
            return "窗內壞根"
        return "下市長停截斷" if last < end else "走得完"
    bad4 = Counter(); okc = 0
    for _, r in E.iterrows():
        s = r["sid"]
        if r["st"] in ("保留", "首根K棒晚於判日", "判日後已無K棒", "pit_valid否"):
            i = ix[s]; p0 = cal_dates.index(r["day0"]); T = p0 - 1
            vp = vpos(i)
            st = "首根K棒晚於判日" if vp[0] > T else ("判日後已無K棒" if vp[-1] < T else ("pit_valid否" if not PX["PV"][i, T] else "保留"))
            if st != r["st"]:
                bad4["st"] += 1
            if st != "保留":
                continue
            okc += 1
            for w, (a_, b_) in TF.WINS.items():
                if walk2(i, p0, a_, b_) != r[f"窗{w}"]:
                    bad4[f"窗{w}"] += 1
                if r["配對sid"]:
                    if walk2(ix[r["配對sid"]], p0, a_, b_) != r[f"配窗{w}"]:
                        bad4[f"配窗{w}"] += 1
    CK["K4_可接與窗"] = {"保留列": okc, "不符": dict(bad4)}
    log(f"[K4] {CK['K4_可接與窗']}")
    # ── K5 配對
    cls_rows = {"E1": ev[ev["class"] == "E1"], "E2": ev[ev["class"] == "E2"], "E2b": e2b, "E3": ev[ev["class"] == "E3"]}
    cls_d = {k: defaultdict(list) for k in cls_rows}
    for k, df in cls_rows.items():
        for s, d in zip(df["stock_id"], df["date"]):
            cls_d[k][s].append(pd.Timestamp(d))
    SIDS = PX["SIDS"]; MC = PX["MC"]; PV = PX["PV"]
    memo = {}

    A12 = {}

    def r12(i, T, endpos):
        if T not in A12:
            A12[T] = bisect.bisect_right(cal_dates, (CAL[T] - pd.DateOffset(months=12)).strftime("%Y-%m-%d")) - 1
        a_ = A12[T]
        if a_ < 0:
            return np.nan
        pa = lastv(i, a_)
        if pa < 0 or BAD[i, pa + 1:endpos + 1].any():
            return np.nan
        return C[i, endpos] / C[i, pa] - 1.0
    bad5 = Counter(); n5 = 0
    for _, r in E[E["st"] == "保留"].iterrows():
        n5 += 1
        i = ix[r["sid"]]; p0 = cal_dates.index(r["day0"]); T = p0 - 1; d = pd.Timestamp(r["date"])
        if T not in memo:
            xs = []
            for j in range(len(SIDS)):
                if PV[j, T] and np.isfinite(C[j, T]) and np.isfinite(MC[j, T]) and MC[j, T] > 0:
                    rr = r12(j, T, T)
                    if np.isfinite(rr):
                        xs.append((j, float(MC[j, T]), rr))
            memo[T] = xs
        xs = memo[T]
        mc0 = MC[i, T]; bvi = lastv(i, T); r0 = r12(i, T, bvi) if bvi >= 0 else np.nan
        if len(xs) < 10 or not np.isfinite(r0) or not (np.isfinite(mc0) and mc0 > 0):
            st, js, nc = "配對不可算", "", ""
        else:
            qs = np.quantile([x[2] for x in xs], [0.2, 0.4, 0.6, 0.8])
            q0 = bisect.bisect_right(list(qs), r0)
            lo, hi = d - pd.DateOffset(months=12), d + pd.DateOffset(months=12)
            cand = [(abs(m - float(mc0)), SIDS[j]) for j, m, rr in xs if j != i and bisect.bisect_right(list(qs), rr) == q0
                    and not any(lo <= x <= hi for x in cls_d[r["類"]].get(SIDS[j], ()))]
            nc = str(len(cand))
            st, js = ("配對成功", min(cand)[1]) if cand else ("配對失敗", "")
        if st != r["配對"]:
            bad5["狀態"] += 1
        if js != r["配對sid"]:
            bad5["代號"] += 1
        if nc != "" and float(nc) != float(r["池候選數"] or "nan"):
            bad5["候選數"] += 1
    CK["K5_配對"] = {"列": n5, "不符": dict(bad5)}
    log(f"[K5] {CK['K5_配對']}")
    # ── K6
    F = pd.read_csv(os.path.join(out, "freq.csv"), encoding="utf-8-sig")
    E["date_dt"] = pd.to_datetime(E["date"])
    for c in ("已下市", "判日停牌", "後12月超表尾"):
        E[c] = E[c].map(lambda x: x == "True")
    E["池候選數"] = pd.to_numeric(E["池候選數"], errors="coerce")
    bad6 = []
    for _, fr in F.iterrows():
        if "_市值" in fr["組"]:
            continue
        sg = [s for s in TF.SEGS if s[0] == fr["段"]][0]
        sub = TF.GROUPS[fr["組"]](E); sub = sub[(sub["date_dt"] >= pd.Timestamp(sg[1])) & (sub["date_dt"] <= pd.Timestamp(sg[2]))]
        ok = sub[sub["st"] == "保留"]
        mine = {"表列數": len(sub), "可接價格": len(ok), "n_eff": min(len(ok), ok["date"].str[:7].nunique()),
                "配對成功": int((ok["配對"] == "配對成功").sum()),
                "後[+2,+250]_走得完": int((ok["窗後[+2,+250]"] == "走得完").sum()),
                "前[-30,-1]_走得完": int((ok["窗前[-30,-1]"] == "走得完").sum()),
                "後[+2,+250]_雙方走得完": int(((ok["窗後[+2,+250]"] == "走得完") & (ok["配窗後[+2,+250]"] == "走得完")).sum())}
        for k, v in mine.items():
            if int(fr[k]) != v:
                bad6.append((fr["段"], fr["組"], k, int(fr[k]), v))
    cols = list(E.columns) + [c for f in glob.glob(os.path.join(out, "*.csv")) for c in pd.read_csv(f, nrows=0, encoding="utf-8-sig").columns]
    badc = sorted({c for c in cols if any(w in str(c) for w in ("報酬", "年化", "淨值", "價格", "收盤", "開盤價", "d值", "CAR", "BHAR")) and c != "可接價格"
                   and not str(c).startswith("掉_") and c not in TF.DROP_ORDER})
    lk = subprocess.run([os.path.expanduser("~/tw-p16/.venv/bin/python"), "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True,
                        env={**os.environ, "PYTHONPATH": os.path.expanduser("~/tw-p17")})
    lock = (lk.stdout + lk.stderr).strip().splitlines()[-1:]
    before = set(open(os.path.join(TF.WORK, "git_before.txt")).read().splitlines())
    now = set(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines())
    extra_g = sorted(now - before)
    mine_g = [x for x in extra_g if ("researchTakeover_freq" in x) or ("resultsTakeover" in x)]
    other_g = [x for x in extra_g if x not in mine_g]
    CK["K6"] = {"freq重建不符": bad6[:20], "報酬類欄": badc, "策略鎖": lock, "git 本件新增": mine_g,
                "git 其他新增（同時段他件子代理的新檔，非本件）": other_g,
                # ★ 同一工作樹有他件子代理同時跑 ⇒ 判準：本件只新增未追蹤檔（??），且沒有任何既有檔被改（新出現的 M／D 列）
                "git 只多本件": all(x.startswith("??") for x in mine_g) and not any(x[:2].strip() in ("M", "D", "MM", "AM") for x in other_g)}
    log(f"[K6] {CK['K6']}")
    ok_all = (CK["K1_登錄sha"]["相符"] and same_bytes and len(e2b) == 76 and kc <= kb and CK["K2_事件表"]["多出＝README"] and CK["K2_事件表"]["相同"]
              and not bad3 and not bad4 and not bad5 and not bad6 and not badc and "相符" in "".join(lock) and CK["K6"]["git 只多本件"])
    CK["全部通過"] = bool(ok_all)
    log(f"[結論] 全部通過 {ok_all}")
    json.dump(CK, open(os.path.join(out, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    open(os.path.join(out, "check.log"), "w", encoding="utf-8").write("\n".join(LOGL) + "\n")


if __name__ == "__main__":
    main()
