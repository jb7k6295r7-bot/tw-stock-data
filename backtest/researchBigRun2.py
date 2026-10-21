# -*- coding: utf-8 -*-
"""長線大漲段 補件第一階段（台股 seq532 §一①、seq534 §一①；裁定 seq421 核：描述、不判、不計 N；族群分群屬事後分群、只當描述、⛔ 不當母體）——回測線計算子代理。
⛔ 描述件：不做任何「之後報酬」檢定；不 commit、不改既有檔（researchBigRun／resultsBigRun 只讀）；私有資料 ⛔ 不讀。
   researchIndMom_freq（build_panel 快取）、researchPTH_freq（month_ends）、researchIndRev_prereg（load_rev、PIT）、research11（load_bars）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBigRun2 [--procs 2] [--limit N --out DIR（乾跑）]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchBigRun2_check
輸出 backtest/resultsBigRun2/：freq_甲補充.csv、甲補充_段.csv、甲補充_貢獻前5.csv、甲補充_窗.csv.gz、mkt_ew_index.csv.gz、
     族群_段.csv、族群_群.csv、族群_敏感度.csv、bigrun2.json、run.log

═══ 讀法（C 標；★＝執行者定；未寫者 ＝ researchBigRun B1～B5 原樣）═══
 C1 價格、合併日曆、接縫、壞根、產業別（PIT）、產業指數（市值加權／等權，每月初重設、月內買進持有，成員 ≥ 5）＝ researchBigRun B1～B3 原樣（本檔重寫同式，
    對帳 K1 與 resultsBigRun/甲_窗 的 R_vw、R_ew 逐列比）。月營收只用於 PIT 的「月營收彙總表當時類別」fallback，快照 ＝ tw-stock-data dbfb96cb81a7（同第一件）。
 C2 全市場等權指數 ★：每月初成員 ＝ 合併面板全部代號（UG.gate3∩四碼普通股、含已下市；load_bars ≥ 260 根）中，上月最後交易日 b 當天或之前 20 交易日內
    有有效 K 棒者（⛔ 不看產業別、不看市值；成員數照報）；月內等權買進持有（W0 ＝ 1、日報酬同 B3：壞根那根 r ＝ 0、無成交 r ＝ 0、下市後 r ＝ 0）。
 C3 甲補充版：同 B4，只把達標條件換成 R產業 ≥ +100% ∧ R產業 ≥ 2 × R全市場等權（同窗）；併段、起點、高點、漲幅、高點後 12 個月最大跌幅、段內貢獻同 B4。
    另並報同期 0050、同期全市場等權。原版（resultsBigRun）不動，頻率表兩版並列。
 C4 族群分群 ★（事後分群、只描述）：
    單位 ＝ resultsBigRun/乙_段_x3 的每一段（股 × 起點→高點）。
    週報酬 ＝ 合併日曆每週（ISO 週）最後交易日之間，該股日報酬（B3 同式）累乘；週內有壞根 ⇒ 該週缺。
    ★ 去掉大盤：殘差 ＝ 個股週對數報酬 − 全市場等權（C2）週對數報酬（避免「同一段時間大家都漲」被分成一群）。
    兩段相關 ＝ 兩段【起點→高點】期間重疊的週（週末日 ∈ (起點, 高點]）上殘差的 Pearson 相關；重疊 ＜ 52 週 ⇒ 不算（距離記 1）。距離 ＝ 1 − 相關。
    階層分群 ＝ 平均連結（average linkage，Lance–Williams 更新；numpy 自寫，本機無 scipy）；★ 主切點 距離 0.7（群間平均殘差相關 ≥ 0.3），
    另報敏感度切點 0.6、0.8。報 ≥ 3 段的群：段數、家數、期間、代表股（★ 群內與其他成員平均相關最高的 3 段）、官方產業（起點 PIT）分布、倍數中位、群內平均相關。
 C5 必附：「描述，不是選股規則」「族群分群是事後分群，只當描述與找原因用，⛔ 不當回測母體」「2015～2020 下市公司月營收約 80 家補不回」「上櫃 2007-07 前無價」
    「月營收為最新版、更正期間有輕微前視（本件月營收只用於產業別 fallback）」。
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import time
from collections import Counter, defaultdict
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchIndMom_freq as IMF             # noqa: E402
from backtest import researchPTH_freq as PF                 # noqa: E402
from backtest import researchIndRev_prereg as PRE           # noqa: E402
from backtest import research11 as R                        # noqa: E402
import backtest.data as D                                   # noqa: E402

SHA = "dbfb96cb81a7d3032e07fe47d1aeb5f0230545fa"
DATA = os.path.expanduser(f"~/bgrwork/main_{SHA[:12]}/data")
SRC1 = "backtest/resultsBigRun"
OUT = "backtest/resultsBigRun2"
EXCL_IND = {"其他", "綜合", "存託憑證", "ETF", ""}
MINMEM = 5
START = pd.Timestamp("2004-12-31")
WIN_M = 36
ALIVE = 20
MINWK = 52
CUTS = (0.6, 0.7, 0.8)
CUT_MAIN = 0.7
NOTES = ["描述，不是選股規則", "族群分群是事後分群，只當描述與找原因用，⛔ 不當回測母體", "2015～2020 下市公司月營收約 80 家補不回", "上櫃 2007-07 前無價",
         "月營收為最新版、更正期間有輕微前視（本件月營收只用於產業別 fallback；快照 dbfb96cb81a7）"]
LOG: list = []
_G: dict = {}


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def seam_job(sid):
    pe, pm = _G["SEAM"][sid]
    out = {"sid": sid, "rc_e": np.nan, "rc_m": np.nan}
    for wn, data, off, cal, p in (("早年", _G["ED"], 0, _G["ECAL"], pe), ("主", _G["MD"], _G["NE"], _G["MCAL"], pm)):
        x = pd.read_csv(os.path.join(data, "stocks", f"{sid}.csv"), dtype={"date": str}, usecols=["date", "close"]).drop_duplicates("date", keep="last")
        d = str(cal[p - off].date())
        v = pd.to_numeric(x.loc[x["date"] == d, "close"], errors="coerce")
        out["rc_e" if wn == "早年" else "rc_m"] = float(v.iloc[0]) if len(v) else np.nan
    return out


def avg_linkage(Dm, hmax):
    """平均連結（Lance–Williams）。Dm ＝ n×n 距離（會被改寫）。回 merges [(a, b, 高度)]，a、b 為當時群代表索引；高度 ＞ hmax 即停。"""
    n = len(Dm)
    np.fill_diagonal(Dm, np.inf)
    size = np.ones(n)
    merges = []
    for _ in range(n - 1):
        k = int(np.argmin(Dm)); i, j = divmod(k, n)
        h = float(Dm[i, j])
        if not np.isfinite(h) or h > hmax:
            break
        if i > j:
            i, j = j, i
        new = (size[i] * Dm[i] + size[j] * Dm[j]) / (size[i] + size[j])
        Dm[i, :] = new; Dm[:, i] = new
        Dm[i, i] = np.inf
        Dm[j, :] = np.inf; Dm[:, j] = np.inf
        size[i] += size[j]; size[j] = 0
        merges.append((i, j, h))
    return merges


def cut_labels(n, merges, cut):
    par = list(range(n))

    def f(x):
        while par[x] != x:
            par[x] = par[par[x]]; x = par[x]
        return x
    for a, b, h in merges:
        if h <= cut:
            par[f(b)] = f(a)
    return np.array([f(x) for x in range(n)])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    out_dir = a.out; os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    if not os.path.isfile(os.path.join(os.path.dirname(DATA), ".done")):
        raise SystemExit(f"⛔ 快照 {DATA} 不在（第一件 researchBigRun 建的）")
    Ze = IMF.build_panel("早年", a.procs, log); Zm = IMF.build_panel("主", a.procs, log)
    CAL = Ze["cal"].append(Zm["cal"]); NE = Ze["n0"]; NC = len(CAL)
    cpos_le = lambda ts: int(CAL.searchsorted(pd.Timestamp(ts), side="right")) - 1
    ie = {s: k for k, s in enumerate(Ze["sids"])}; im = {s: k for k, s in enumerate(Zm["sids"])}
    SIDS = sorted(set(ie) | set(im))
    B1 = pd.read_csv(os.path.join(SRC1, "乙_段_x3.csv.gz"), dtype={"代號": str})
    if a.limit:
        rng = np.random.default_rng(532)
        SIDS = sorted(set(rng.choice(SIDS, a.limit, replace=False)) | {"2330", "2454", "2303", "2603", "2609", "2615", "1513", "1519", "6669", "3017"})
        B1 = B1[B1["代號"].isin(SIDS)].reset_index(drop=True)
    N = len(SIDS); IX = {s: i for i, s in enumerate(SIDS)}
    C = np.full((N, NC), np.nan); BAD = np.zeros((N, NC), bool); MC = np.full((N, NC), np.nan); SEAM = {}
    for i, s in enumerate(SIDS):
        if s in ie:
            C[i, :NE] = Ze["C"][ie[s]]; BAD[i, :NE] = Ze["BAD"][ie[s]]; MC[i, :NE] = Ze["MC"][ie[s]]
        if s in im:
            C[i, NE:] = Zm["C"][im[s]]; BAD[i, NE:] = Zm["BAD"][im[s]]; MC[i, NE:] = Zm["MC"][im[s]]
        if s in ie and s in im:
            ve = np.flatnonzero(np.isfinite(C[i, :NE])); vm = np.flatnonzero(np.isfinite(C[i, NE:]))
            if len(ve) and len(vm):
                SEAM[s] = (int(ve[-1]), int(vm[0]) + NE)
    for Z in (Ze, Zm):
        for k in ("C", "BAD", "G", "MC", "TRD", "O", "UPL"):
            Z.pop(k, None)
    _G.update({"SEAM": SEAM, "ED": Ze["data"], "MD": Zm["data"], "ECAL": Ze["cal"], "MCAL": Zm["cal"], "NE": NE})
    with Pool(a.procs) as pool:
        SR = {r["sid"]: r for r in pool.imap_unordered(seam_job, sorted(SEAM), chunksize=16)}
    seam_info = Counter()
    for s, (pe, pm) in SEAM.items():
        i = IX[s]; seam_info["兩世界都有"] += 1
        re_, rm_ = SR[s]["rc_e"], SR[s]["rc_m"]
        Mf = C[i, pe] * rm_ / (re_ * C[i, pm]) if (np.isfinite(re_) and np.isfinite(rm_) and re_ > 0 and C[i, pm] > 0) else np.nan
        if np.isfinite(Mf) and Mf > 0:
            C[i, NE:] *= Mf
            BAD[i, pm] = (pm - pe - 1) >= 5
            if BAD[i, pm]:
                seam_info["接縫相隔≥5交易日⇒壞根"] += 1
        else:
            BAD[i, pm] = True; seam_info["接縫原始收盤缺⇒壞根"] += 1
    log(f"[接縫] {dict(seam_info)}")
    RR = np.zeros((N, NC)); LASTV = np.full((N, NC), -1, np.int32); RBAD = np.zeros((N, NC), bool)
    for i in range(N):
        vp = np.flatnonzero(np.isfinite(C[i]))
        if len(vp) > 1:
            vc = C[i, vp]; r = vc[1:] / vc[:-1] - 1.0; vb = BAD[i, vp[1:]]
            r[vb] = 0.0; RR[i, vp[1:]] = r; RBAD[i, vp[1:]] = vb
        ar = np.full(NC, -1, np.int32); ar[vp] = vp; LASTV[i] = np.maximum.accumulate(ar)
    log(f"[價格] {N} 檔｜{time.time() - t0:.0f}s")
    # 0050
    B50 = {}
    for wn, Z in (("早年", Ze), ("主", Zm)):
        D.DATA = Z["data"]; B50[wn] = R.load_bars("0050", "twse", Z["cal"])
    idx50 = np.concatenate([B50["早年"]["idx"].astype(np.int64), B50["主"]["idx"].astype(np.int64) + NE])
    c50 = np.concatenate([B50["早年"]["c"], B50["主"]["c"]]).astype(float); rc50 = np.concatenate([B50["早年"]["rc"], B50["主"]["rc"]]).astype(float)
    j50 = len(B50["早年"]["idx"]); c50[j50:] *= c50[j50 - 1] * rc50[j50] / (rc50[j50 - 1] * c50[j50])
    v50 = lambda p: c50[int(np.searchsorted(idx50, p, "right")) - 1]
    # PIT
    rev, rev_ly, cat, _, _, _ = PRE.load_rev(DATA)
    PIT = PRE.PIT(DATA, cat)
    del rev, rev_ly
    # 月份、成員、指數
    ym = CAL.year * 12 + CAL.month
    mstart = np.flatnonzero(np.r_[True, ym[1:] != ym[:-1]]); mend = np.r_[mstart[1:] - 1, NC - 1]
    MONTHS = [(int(mstart[k] - 1), int(mend[k])) for k in range(1, len(mstart))]
    MB = np.array([b for b, e in MONTHS]); MEND = np.array([e for b, e in MONTHS])
    mi_of = lambda p: (lambda k: k if k < len(MONTHS) and MB[k] < p <= MEND[k] else -1)(int(np.searchsorted(MEND, p, "left")))
    MEMB = []; MKT = []
    for (b, e) in MONTHS:
        lv = LASTV[:, b]
        alive = (lv >= 0) & (b - lv <= ALIVE)
        MKT.append(np.flatnonzero(alive))
        okmc = alive & np.isfinite(MC[:, b]) & (MC[:, b] > 0)
        mm = defaultdict(list)
        for i in np.flatnonzero(okmc):
            ind, _ = PIT.at(SIDS[i], CAL[b])
            if ind is None or ind in EXCL_IND:
                continue
            mm[ind].append(i)
        MEMB.append({k: np.array(v, np.int64) for k, v in mm.items()})
    INDS = sorted({k for m in MEMB for k in m})
    IDX = {kd: {ind: np.full(NC, np.nan) for ind in INDS} for kd in ("vw", "ew")}
    CH = {kd: {ind: np.full(NC, -1, np.int64) for ind in INDS} for kd in ("vw", "ew")}
    IM = np.full(NC, np.nan); NMK = np.zeros(len(MONTHS), np.int64)
    chain_no = 0
    for mi, (b, e) in enumerate(MONTHS):
        Gm = np.cumprod(1.0 + RR[:, b + 1:e + 1], axis=1)
        mk = MKT[mi]; NMK[mi] = len(mk)
        if len(mk):
            if not np.isfinite(IM[b]):
                IM[b] = 1.0
            IM[b + 1:e + 1] = IM[b] * Gm[mk].mean(0)
        for ind, idxs in MEMB[mi].items():
            if len(idxs) < MINMEM:
                continue
            for kd in ("vw", "ew"):
                W0 = MC[idxs, b] if kd == "vw" else np.ones(len(idxs))
                V = (W0[:, None] * Gm[idxs]).sum(0) / W0.sum()
                I_ = IDX[kd][ind]; H_ = CH[kd][ind]
                if not np.isfinite(I_[b]):
                    chain_no += 1; I_[b] = 1.0; H_[b] = chain_no
                I_[b + 1:e + 1] = I_[b] * V; H_[b + 1:e + 1] = H_[b]
    if not np.isfinite(IM[MONTHS[0][0] + 1:]).all():
        raise SystemExit("⛔ 全市場等權指數有缺")
    log(f"[指數] 產業 {len(INDS)}、鏈 {chain_no}；全市場等權 每月成員 {NMK.min()}～{NMK.max()}｜{time.time() - t0:.0f}s")
    ME, MK = PF.month_ends(CAL)
    jst = int(np.searchsorted(CAL[ME], START, "left"))
    WROWS = []; HITS = {kd: defaultdict(list) for kd in ("vw", "ew")}
    for j in range(jst + WIN_M, len(ME)):
        pa, pt = int(ME[j - WIN_M]), int(ME[j])
        rm = IM[pt] / IM[pa] - 1.0; r50 = v50(pt) / v50(pa) - 1.0
        for ind in INDS:
            row = None
            for kd in ("vw", "ew"):
                I_, H_ = IDX[kd][ind], CH[kd][ind]
                if H_[pa] < 0 or H_[pa] != H_[pt]:
                    continue
                rr = I_[pt] / I_[pa] - 1.0
                hit = bool(rr >= 1.0 and rr >= 2.0 * rm)
                if row is None:
                    row = {"產業": ind, "窗起": str(CAL[pa].date()), "窗終": str(CAL[pt].date()), "R全市場等權": rm, "R0050": r50}
                row[f"R_{kd}"] = rr; row[f"補充達標_{kd}"] = hit; row[f"原版達標_{kd}"] = bool(rr >= 1.0 and rr >= 2.0 * r50)
                if hit:
                    HITS[kd][ind].append(j)
            if row is not None:
                WROWS.append(row)
    log(f"[甲補充] 窗 {len(WROWS)}｜達標窗 市值 {sum(map(len, HITS['vw'].values()))}、等權 {sum(map(len, HITS['ew'].values()))}")

    def contrib(kd, ind, S, H):
        I_ = IDX[kd][ind]; acc = defaultdict(float)
        for mi in range(mi_of(S + 1), len(MONTHS)):
            b, e = MONTHS[mi]
            if b >= H:
                break
            end = min(e, H); idxs = MEMB[mi][ind]
            W0 = MC[idxs, b] if kd == "vw" else np.ones(len(idxs))
            g = np.prod(1.0 + RR[idxs, b + 1:end + 1], axis=1)
            for i, v in zip(idxs, I_[b] / I_[S] * W0 * (g - 1.0) / W0.sum()):
                acc[int(i)] += float(v)
        return acc

    NAME = {}
    for s in SIDS:
        for Z in (Zm, Ze):
            f = os.path.join(Z["data"], "stocks", f"{s}.csv")
            if s not in NAME and os.path.exists(f):
                with open(f, encoding="utf-8") as fh:
                    lines = fh.readlines()
                if len(lines) > 1:
                    NAME[s] = lines[-1].split(",")[2]
    SEGS = []; CONT = []
    for kd in ("vw", "ew"):
        for ind in INDS:
            js = HITS[kd][ind]
            if not js:
                continue
            groups = [[js[0]]]
            for j in js[1:]:
                if j - WIN_M <= groups[-1][-1]:
                    groups[-1].append(j)
                else:
                    groups.append([j])
            I_, H_ = IDX[kd][ind], CH[kd][ind]
            for g in groups:
                S = int(ME[g[0] - WIN_M]); E = int(ME[g[-1]])
                if not (H_[S:E + 1] == H_[S]).all():
                    raise SystemExit(f"⛔ {ind} 段內跨鏈")
                H = S + int(np.nanargmax(I_[S:E + 1]))
                gain = I_[H] / I_[S] - 1.0
                rm = IM[H] / IM[S] - 1.0; r50 = v50(H) / v50(S) - 1.0
                hend = CAL[H] + pd.DateOffset(months=12); he = cpos_le(hend)
                post = np.arange(H + 1, he + 1); post = post[H_[post] == H_[H]] if len(post) else post
                mdd = float(I_[post].min() / I_[H] - 1.0) if len(post) else np.nan
                full = bool(hend <= CAL[-1] and len(post) == he - H)
                acc = contrib(kd, ind, S, H); tot = sum(acc.values())
                if abs(tot - gain) > 1e-6 * max(1.0, abs(gain)):
                    raise SystemExit(f"⛔ {ind} 貢獻加總 {tot} ≠ 漲幅 {gain}")
                top = sorted(acc.items(), key=lambda z: -z[1])[:5]
                segid = f"補{kd}-{ind}-{CAL[S].strftime('%Y%m')}"
                # 與原版重疊：同產業、同加權的原版段區間相交
                SEGS.append({"段號": segid, "加權": "市值" if kd == "vw" else "等權", "產業": ind, "起點": str(CAL[S].date()), "高點": str(CAL[H].date()),
                             "最後達標窗終點": str(CAL[E].date()), "達標窗數": len(g), "起點左截斷": bool(g[0] - WIN_M == jst), "漲幅": gain,
                             "全市場等權同期": rm, "對全市場等權倍數": (1 + gain) / (1 + rm), "0050同期": r50, "對0050倍數": (1 + gain) / (1 + r50),
                             "起點到高點交易日": H - S, "高點後12月最大跌幅": mdd, "高點後12月": "滿" if full else "未滿12月",
                             "成員數@起點": int(len(MEMB[mi_of(S + 1)].get(ind, []))),
                             "前5貢獻": "｜".join(f"{SIDS[i]}{NAME.get(SIDS[i], '')} {v / gain:.0%}" for i, v in top)})
                for rk, (i, v) in enumerate(top):
                    CONT.append({"段號": segid, "名次": rk + 1, "代號": SIDS[i], "名稱": NAME.get(SIDS[i], ""), "貢獻(漲幅點)": v, "占漲幅": v / gain})
    SEG = pd.DataFrame(SEGS)
    O1 = pd.read_csv(os.path.join(SRC1, "甲_段.csv"))
    if len(SEG):
        for k_, r in SEG.iterrows():
            o = O1[(O1["加權"] == r["加權"]) & (O1["產業"] == r["產業"])]
            hit = [x for _, x in o.iterrows() if x["起點"] <= r["高點"] and r["起點"] <= x["高點"]]
            SEG.loc[k_, "原版同產業相交段"] = "｜".join(f"{x['起點']}→{x['高點']}" for x in hit)
    log(f"[甲補充] 段 市值 {int((SEG['加權'] == '市值').sum()) if len(SEG) else 0}、等權 {int((SEG['加權'] == '等權').sum()) if len(SEG) else 0}")
    F1o = pd.read_csv(os.path.join(SRC1, "freq_甲.csv"))
    FR = []
    for y in range(2004, CAL[-1].year + 1):
        r = {"起點年": y, "註": "起點 2004-12-31（左截斷）" if y == 2004 else ""}
        for kd in ("市值", "等權"):
            o = F1o[F1o["起點年"] == y]
            r[f"原版段數_{kd}"] = int(o[f"甲段數_{kd}"].iloc[0]) if len(o) else 0
            sub = SEG[(SEG["加權"] == kd) & (pd.to_datetime(SEG["起點"]).dt.year == y)] if len(SEG) else SEG
            r[f"補充段數_{kd}"] = len(sub); r[f"補充產業數_{kd}"] = int(sub["產業"].nunique()) if len(sub) else 0
            r[f"補充產業_{kd}"] = "、".join(sorted(sub["產業"].unique())) if len(sub) else ""
        FR.append(r)
    FR = pd.DataFrame(FR)

    # ═════════ 族群分群 ═════════
    wk = CAL.isocalendar() if hasattr(CAL, "isocalendar") else None
    iso = pd.DataFrame({"y": CAL.isocalendar().year.to_numpy(), "w": CAL.isocalendar().week.to_numpy()})
    wid = (iso["y"] * 100 + iso["w"]).to_numpy()
    WE = np.flatnonzero(np.r_[wid[1:] != wid[:-1], True])          # 每週最後交易日位置
    nW = len(WE)
    wkid = np.searchsorted(WE, np.arange(NC), "left")              # 日 → 週序
    LR = np.log1p(RR)
    nseg = len(B1)
    X = np.zeros((nseg, nW)); M = np.zeros((nseg, nW))
    mlr = np.log(IM[WE[1:]] / IM[WE[:-1]])                        # 第 w 週（w ≥ 1）全市場等權週對數報酬
    for k_, r in B1.iterrows():
        i = IX[r["代號"]]; ps, ph = cpos_le(r["起點"]), cpos_le(r["高點"])
        w0 = int(wkid[ps]) + 1; w1 = int(wkid[ph]) if WE[wkid[ph]] == ph else int(wkid[ph]) - 1
        if w1 < w0:
            continue
        s_ = np.add.reduceat(LR[i, :WE[-1] + 1], np.r_[0, WE[:-1] + 1])     # 每週日對數報酬和
        bad_w = np.add.reduceat(RBAD[i, :WE[-1] + 1].astype(int), np.r_[0, WE[:-1] + 1]) > 0
        ws = np.arange(max(w0, 1), w1 + 1)
        ok = ~bad_w[ws]
        X[k_, ws[ok]] = s_[ws[ok]] - mlr[ws[ok] - 1]; M[k_, ws[ok]] = 1.0
    log(f"[族群] 段 {nseg}｜週 {nW}｜每段有效週 中位 {np.median(M.sum(1)):.0f}｜{time.time() - t0:.0f}s")
    Nn = M @ M.T; Sx = X @ M.T; Sxx = (X * X) @ M.T; Sxy = X @ X.T
    with np.errstate(invalid="ignore", divide="ignore"):
        cov = Sxy - Sx * Sx.T / Nn
        vx = Sxx - Sx * Sx / Nn; vy = vx.T
        CR = cov / np.sqrt(vx * vy)
    del Sx, Sxx, Sxy, cov, vx, vy
    ok = (Nn >= MINWK) & np.isfinite(CR)
    DM = np.where(ok, 1.0 - CR, 1.0)
    np.fill_diagonal(DM, 0.0)
    CRm = np.where(ok, CR, np.nan)
    log(f"[族群] 可算相關的段對 {int(ok.sum() - nseg) // 2}｜{time.time() - t0:.0f}s")
    merges = avg_linkage(DM.copy(), max(CUTS))
    log(f"[族群] 合併 {len(merges)} 次｜{time.time() - t0:.0f}s")
    LAB = {c: cut_labels(nseg, merges, c) for c in CUTS}
    GR = []; SENS = []
    for c in CUTS:
        cnt = Counter(LAB[c])
        big = {g for g, n in cnt.items() if n >= 3}
        SENS.append({"切點(距離)": c, "群間平均殘差相關≥": round(1 - c, 2), "≥3段的群數": len(big), "在≥3段群內的段數": int(sum(cnt[g] for g in big)),
                     "2段群數": sum(1 for n in cnt.values() if n == 2), "單獨段數": sum(1 for n in cnt.values() if n == 1), "最大群段數": max(cnt.values())})
    lab = LAB[CUT_MAIN]
    cnt = Counter(lab)
    order = sorted([g for g, n in cnt.items() if n >= 3], key=lambda g: (-cnt[g], g))
    gname = {g: k + 1 for k, g in enumerate(order)}
    B1 = B1.copy()
    for c in CUTS:
        cc = Counter(LAB[c]); oo = sorted([g for g, n in cc.items() if n >= 3], key=lambda g: (-cc[g], g)); gm = {g: k + 1 for k, g in enumerate(oo)}
        B1[f"群_切{c}"] = [gm.get(x, 0) for x in LAB[c]]
    for g in order:
        mem = np.flatnonzero(lab == g)
        sub = CRm[np.ix_(mem, mem)]
        mc = np.nanmean(np.where(np.eye(len(mem), dtype=bool), np.nan, sub), axis=1)
        rep = mem[np.argsort(-np.nan_to_num(mc, nan=-9))[:3]]
        rows = B1.iloc[mem]
        ic = Counter(rows["產業(起點PIT)"])
        GR.append({"群號": gname[g], "段數": len(mem), "家數": rows["代號"].nunique(),
                   "期間": f"{rows['起點'].min()}～{rows['高點'].max()}", "起點中位": str(pd.to_datetime(rows["起點"]).median().date()),
                   "高點中位": str(pd.to_datetime(rows["高點"]).median().date()),
                   "代表股": "、".join(f"{B1.at[k, '代號']}{B1.at[k, '名稱']}" for k in rep),
                   "官方產業分布": "、".join(f"{k}{v}" for k, v in ic.most_common(4)), "最多官方產業占比": ic.most_common(1)[0][1] / len(mem),
                   "倍數中位": float(rows["倍數"].median()), "群內平均殘差相關": float(np.nanmean(sub[~np.eye(len(mem), dtype=bool)])),
                   "成員": "、".join(f"{c}{n}" for c, n in zip(rows["代號"], rows["名稱"]))})
    GR = pd.DataFrame(GR)
    log(f"[族群] 主切點 {CUT_MAIN}：≥3 段的群 {len(GR)}｜{time.time() - t0:.0f}s")
    # 存檔
    FR.to_csv(os.path.join(out_dir, "freq_甲補充.csv"), index=False, encoding="utf-8-sig")
    SEG.to_csv(os.path.join(out_dir, "甲補充_段.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(CONT).to_csv(os.path.join(out_dir, "甲補充_貢獻前5.csv"), index=False, encoding="utf-8-sig")
    with gzip.open(os.path.join(out_dir, "甲補充_窗.csv.gz"), "wt", encoding="utf-8") as fh:
        pd.DataFrame(WROWS).to_csv(fh, index=False)
    with gzip.open(os.path.join(out_dir, "mkt_ew_index.csv.gz"), "wt", encoding="utf-8") as fh:
        pd.DataFrame({"日": [str(d.date()) for d in CAL], "全市場等權": IM,
                      "當月成員數": [int(NMK[mi_of(p)]) if mi_of(p) >= 0 else None for p in range(NC)]}).to_csv(fh, index=False)
    B1[["代號", "名稱", "起點", "高點", "倍數", "產業(起點PIT)"] + [f"群_切{c}" for c in CUTS]].to_csv(os.path.join(out_dir, "族群_段.csv"), index=False, encoding="utf-8-sig")
    GR.to_csv(os.path.join(out_dir, "族群_群.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(SENS).to_csv(os.path.join(out_dir, "族群_敏感度.csv"), index=False, encoding="utf-8-sig")
    J = {"性質": "描述（⛔ 不判、不計 N、不當選股規則；族群為事後分群、⛔ 不當母體）",
         "依據": "台股 seq532 §一①、seq534 §一①；裁定 seq421", "資料": {"tw-stock-data 快照": SHA, "主世界": Zm["data"], "早年世界": Ze["data"], "乙段": SRC1},
         "檔數": N, "乾跑limit": a.limit, "乾跑代號": SIDS if a.limit else None, "接縫": dict(seam_info), "產業數": len(INDS),
         "全市場等權每月成員": [int(NMK.min()), int(NMK.max())],
         "甲補充段數": {"市值": int((SEG["加權"] == "市值").sum()) if len(SEG) else 0, "等權": int((SEG["加權"] == "等權").sum()) if len(SEG) else 0},
         "族群": {"段數": nseg, "週數": nW, "合併次數": len(merges), "敏感度": SENS}, "必附": NOTES, "讀法": __doc__.split("═══ 讀法")[1],
         "時間": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M"), "耗時秒": round(time.time() - t0)}
    json.dump(J, open(os.path.join(out_dir, "bigrun2.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    np.save(os.path.join(os.path.expanduser("~/bgrwork"), f"bgr2_corr_{'dry' if a.limit else 'full'}.npy"), CRm.astype(np.float32))
    log(f"[完] {time.time() - t0:.0f}s ⇒ {out_dir}")
    open(os.path.join(out_dir, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
