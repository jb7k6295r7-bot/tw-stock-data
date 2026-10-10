# -*- coding: utf-8 -*-
"""PREREG營量營飆同產業上限 seq1（台股策略線登錄 sha 6b2c4554fbf63b60，2026-10-11 00:09；裁定 seq329 §三發號、N_組合 ＋1（營量＋上限、營飆＋上限兩格）；
事後重切 ⇒ 最多暫定）——回測線計算子代理。⛔ 只計算：不 commit、不改既有程式與結果夾；用語「假訊號」；⛔ 不給買賣建議。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchYLindcap run [--procs 2] [--reps 200]
    ...                                                       -m backtest.researchYLindcap report    # 由 seeds_part 重算彙總
    ...                                                       -m backtest.researchYLindcap page      # 網頁 backtest/resultsYLindcap/營量營飆同產業上限.html
    抽樣查核（獨立寫法）：... -m backtest.researchYLindcap_check

⭐ 讀法寫死時間：見 TIME（台北）；寫死前 ⛔ 沒算任何「加上限」的數字（只看過登錄全文 seq1／seq2、裁定 seq328／seq329、回測 1011-0003 描述 ⑨、
   既有程式（researchYLmargin、researchT1fix、research11.simulate_mtm 的 cap_fn、researchYLdesc ⑨）與資料格式；營量 v1／營飆 v1 正式數字本來就看過 ⇒ 登錄已標事後重切）。

═══ 讀法（Q 標；登錄沒寫清楚、執行者補的都在這裡）═══
 Q1 sha：登錄全文去掉含「pw1 line」那一行後 sha256 前 16 碼核對才跑（信箱只讀）：seq1 ＝ 6b2c4554fbf63b60（裁定 seq329 發號那一版；00:35 起搬到
    _封存-台股策略線附件-舊seq/）、seq2 ＝ 49b5dbbc3b4f9cdb（台股 00:35：只加末段「裁定 seq329 §三（寫死）」、判定一字未動；本檔寫死前已 diff 核過）⇒ 兩封都核
 Q2 本體 ＝ researchT1fix.build_ctx(True)（T1 資料尾補回、edc6f 快照、主窗 2017-03-02～2026-08-24；母體 ＝ AND 表既有的「20 日均量 ≥ 500 張」）；停止交易強制出場：開
    （SF ＝ research11.stop_force_days(valid_from_data(全部股票), 主窗尾)，同 researchT1fix）
    營飆 v1 ＝ listexit_lines.sim（H120、N10、default_rng(1000＋r)、t−1 大盤閘）200 顆；營量 v1 ＝ simulate_mtm(sig13, "H60", 20, default_rng(7000＋r), log=[], d_max=None,
      pick="relvol", queue_days=0)；relvol 排序不抽籤 ⇒ r＝0（正式件同；假訊號臂才跑 200）
    ⭐ 出場照原策略（營飆 120 根、營量 60 根收盤）⇒ seq308 條件出場主臂不適用（本件只改選股，登錄 §一「其他一字不動」）
 Q3 上限的接法 ＝ research11.simulate_mtm 既有參數 cap_fn（PREREGP2 落地；⛔ 不改引擎）：候選照原策略順序（營飆 rng.permutation、營量 relvol 遞減）逐一問 cap_fn，
    不合格 ⇒ 跳過（不占名額）、往下問下一檔；名額滿就停；當天問完仍有空位 ⇒ 留空（引擎原規則，⛔ 不放寬）
    cap_fn(sid, t, 持股) ＝「持股（當下持有 ＋ 今天已買）裡與 sid 同產業的檔數 ＜ 3」；產業一律取決策日 t−1 的分類（持股與候選同一天）；sid 產業查無 ⇒ 不設限（筆數照報）
    ⭐ 閘 G1：cap_fn 恆真（不設上限）走同一條包裝 ⇒ 與不加 cap_fn 的原版逐位元相同（eq_sha、cagr、mdd、trades；營飆 200 顆、營量 r0、兩個現實版）
       閘 G2：不加 cap_fn ＝ resultsT1fix c1／c13／slip1_real／slip13_real t1 逐位元（同 researchYLmargin G1／G2）
 Q4 產業（裁定 seq329 §三、登錄 §一）：industry_pit（tw-stock-data origin/main 執行時 sha）在決策日的類別；industry_pit 是上市櫃官方產業別單層（2007-07 電子拆八子類之後
    即「子類那一層」；⚠ 沒有更細的子類，照報）；
    ① 該股在 industry_pit 有段：決策日落在段內 ⇒ 該段（pit）；晚於最後一段 ⇒ 最後已知類別（pit最後已知）；早於首段 ⇒ 首段（pit首段前）；兩段之間 ⇒ 前一段（pit空隙）
       （＝ researchIndRev_prereg.PIT._at；後三者是已下市股缺段，照實寫、報筆數）
    ② industry_pit 沒有該股 ⇒ 登錄「查不到 ⇒ 用現值」：industry.csv 現值（標「現值補・非當時」，⛔ 不當成當時分類）
    ③ 現值也沒有（已下市且沒有異動公告）⇒ 月營收彙總表該股「決策日已公告的最近一期」產業別欄（公告當時的類別；PRE.PIT 的 fallback）
    ④ 都沒有 ⇒ 查無 ⇒ 不設限
    ⑨ 口徑（回測 1011-0003「現值套回」）＝ research34.load_revenue 的 ind（H2D 快照月營收彙總表各檔最後一期的產業別）⇒ 只拿來報差異（Q8）
 Q5 段：主窗 2017-03-02～2026-08-24｜探索 2017-03-02～2021-12-30｜確認 2022-01-03～2026-08-24（同一條權益曲線切窗；rerun17.win_metrics）
    早年段：營飆 v1 沒有早年版面（researchYLmargin M7 同）、且 industry_pit 早年覆蓋不足（上市 2006、上櫃 2011 以前視為沒變；已下市股沒有錨點）⇒「不可判定」
 Q6 判（登錄 §二）：「比原策略好」＝ 探索、確認兩段都「年化中位 ≥ 原策略 且 比值 ≥ 原策略」，且這四個比較至少一個嚴格較大；同時報使用者判準標籤（對 0050 同段：
    年化 ＞ 0050 且 比值 ≥ 0050 ⇒ 合格；只過年化 ⇒ 另列）；出口：比原策略好 ⇒「同產業上限 3 檔在 <策略> 上有改善（暫定）」；否 ⇒「…沒有改善」；⛔ 不寫「分散沒用」
    判定以 0.585% 版為準；現實版（researchSlip「現實版（C1 0.3%＋C2 50 萬＋C3＋C4）」，接法照 researchT1fix.slip_setup）同表並報
    退化（共同規則）：平均持股 ＜ 3 或現金 ＞ 30%（段內逐日平均、種子中位）⇒ 該格照登錄排除並列出；⭐ 先寫 degeneracy.json（附台北時間）再彙總報酬
    現金比例（主窗、種子中位）比原策略高 ≥ 5 個百分點 ⇒ 結果句加「部分可由降曝險解釋」
 Q7 假訊號臂（登錄「同日、同數量、隨機跳過候選（不看產業）200 次」）：第 i 抽 ⇒ 取加上限臂（營飆：同顆種子 i；營量：r0）每天實際跳過的候選數 k_t；
    假訊號那條路徑上第 t 天：空位 a、當天未持有候選 n ⇒ 在照原順序的前 min(n, a＋k_t) 個位置裡隨機挑 min(k_t, 該數) 個跳過（其餘規則同 cap_fn 路徑）；
    抽樣 default_rng([20261011, 族, i])（族 1 ＝ 營飆、13 ＝ 營量）；引擎種子 營飆 1000＋i、營量 7000＋i（營量排序不抽籤 ⇒ 種子無作用）
    p ＝ 假訊號年化 ≥ 加上限臂（營飆 200 顆中位）的比例；比值另報
 Q8 必報（描述、不判）：
    被跳過的候選（cap_fn 回假）：逐年筆數、占「當天被問到的候選」與「訊號列」的比例；其中「原本會買」＝ 順位 ＜ 當天空位；補到 ＝ 順位 ≥ 空位而被買的；補到比例 ＝ 補到 ÷ 原本會買
      （營量 r0；營飆 200 顆合計 ÷ 200）
    被跳過那批（原本會買）的逐筆報酬 vs 補上那批：AND 表 g_H120（營飆）／g_H60（營量）＝ 固定出場毛報酬（未扣成本）；營量 r0、營飆 200 顆去重
    等效獨立檔數變化（r＝0；researchYLmargin.eff_n）；最大產業占幾檔、同產業 ＞3 檔的換股日占比：換股日 ＝ 有買進的日子，持股 ＝ 當天收盤持有；
      營量 r0、營飆 200 顆合計（＝ 回測 1011-0003 ⑨ 的算法）；兩種口徑（industry_pit 當時、⑨ 現值套回）都報（裁定 seq329 §三）
    現金比例變化；產業來源筆數（訊號列 × 決策日：pit／pit最後已知／pit首段前／pit空隙／現值補／營收彙總表／查無）；pit 與 ⑨ 口徑不同的訊號列占比
    描述臂：「⑨ 現值口徑上限」（同規則、產業換成 ⑨ 口徑）⇒ 報與 pit 版的差（⛔ 不判）
 Q9 ⚠ 減資價格斷點（裁定 seq329 §五）：正式引擎 hard_break 是否擋到現金減資／彌補虧損減資日另案查核中；本件照現行引擎跑，結果註記「減資斷點待查」
輸出 backtest/resultsYLindcap/：degeneracy.json（先寫）、seeds.csv.gz、cells.csv、skipped.csv.gz、summary.json、run.log、營量營飆同產業上限.html（seeds_part.csv ＝ 續跑用）
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import html
import json
import os
import pickle
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import listexit_lines as L
from . import rerun17 as RR
from . import research11 as R
from . import research34 as R34
from . import researchT1fix as T
from . import researchYLmargin as YM
from . import researchIndRev_prereg as PRE

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsYLindcap")
PAGE = os.path.join(OUT, "營量營飆同產業上限.html")
WORK = os.path.expanduser("~/yicwork")
MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
TIME = "2026-10-11 00:52（台北）"
REG_SHA, REG_SHA2 = "6b2c4554fbf63b60", "49b5dbbc3b4f9cdb"
SEGS = {"主窗": ("2017-03-02", "2026-08-24"), "探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")}
JUDGE = ("探索", "確認")
CAP = 3
FSEED = 20261011
FAM = {"fly": {"id": 1, "名": "營飆 v1", "g": "g_H120", "x": "xpos_H120", "N": 10}, "vol": {"id": 13, "名": "營量 v1", "g": "g_H60", "x": "xpos_H60", "N": 20}}
SLIP = {"slip_fly": (1, "fly"), "slip_vol": (13, "vol")}
RP = dict(float_precision="round_trip")
_G: dict = {}
LOGF = None


def log(x):
    x = f"[{pd.Timestamp.now(tz='Asia/Taipei'):%H:%M:%S}] {x}"
    print(x, flush=True)
    if LOGF:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(x + "\n")


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


def reg_check():
    out = []
    for sha in (REG_SHA, REG_SHA2):
        fs = [f for f in glob.glob(os.path.join(MAILBOX, "**", "*.md"), recursive=True) if f"sha{sha}" in os.path.basename(f)]
        if len(fs) != 1:
            raise SystemExit(f"⛔ 信箱找不到唯一一封登錄全文 sha{sha}：{fs}")
        b = open(fs[0], "rb").read()
        h = hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]
        if h != sha:
            raise SystemExit(f"⛔ 登錄 sha {h} ≠ {sha}")
        out.append(os.path.relpath(fs[0], MAILBOX))
    return out


# ═════════════ 產業（Q4）═════════════
class Ind:
    def __init__(self, P, ind9, cal):
        self.P = P; self.ind9 = ind9; self.cal = cal; self.c = {}

    def at(self, sid, t, ver="pit"):
        """日曆位置 t 的產業 ⇒ (類別或 None, 來源)。"""
        k = (sid, t, ver)
        if k in self.c:
            return self.c[k]
        if ver == "now9":
            v = self.ind9.get(sid)
            r = (v if isinstance(v, str) and v else None, "⑨現值套回" if isinstance(v, str) and v else "查無")
        else:
            P = self.P; d = self.cal[t]
            if sid in P.seg:
                r = P._at(sid, d, "pit")
            elif sid in P.cur:
                r = (P.cur[sid], "現值補・非當時")
            else:
                r = P._at(sid, d, "pit")
                if r[0] is None:
                    r = (None, "查無")
        self.c[k] = r
        return r


def cap_fn_factory(ver, N, rec, cap=CAP):
    IN = _G["IND"]; st = {"t": None}

    def fn(sid, t, hold):
        if st["t"] != t:
            st.update(t=t, i=0, a=N - len(hold))
        i = st["i"]; st["i"] += 1
        if cap is None:
            ok = True
        else:
            ind = IN.at(sid, t - 1, ver)[0]
            ok = True if ind is None else sum(1 for h in hold if IN.at(h, t - 1, ver)[0] == ind) < cap
        rec.append((t, sid, i, st["a"], ok))
        return ok
    return fn


def fake_fn_factory(K, rng, day_sids, N, rec):
    st = {"t": None}

    def fn(sid, t, hold):
        if st["t"] != t:
            a = N - len(hold); k = int(K.get(t, 0))
            n = sum(1 for s in day_sids.get(t, ()) if s not in hold)
            M = min(n, a + k); kk = min(k, M)
            st.update(t=t, i=0, a=a, rej=set(rng.choice(M, kk, replace=False).tolist()) if kk > 0 else set())
        i = st["i"]; st["i"] += 1
        ok = i not in st["rej"]
        rec.append((t, sid, i, st["a"], ok))
        return ok
    return fn


# ═════════════ 設定 ═════════════
def setup(procs):
    t0 = time.time()
    regs = reg_check(); log(f"[Q1 sha] ✔ {regs}")
    ctx = T.build_ctx(True)
    cal = ctx["cal"]; ncal = len(cal); w0, w1 = ctx["w0"], ctx["w1"]
    bench = RR.load_bench(cal)
    bw = RR.bench_row(cal, bench, w0, w1 + 1)
    g0 = repr(bw["cagr"]) == repr(T.ANCHOR[0]) and repr(bw["mdd"]) == repr(T.ANCHOR[1])
    log(f"[G0 0050 錨] 逐位元 {g0}")
    if not g0:
        raise SystemExit("⛔ G0 不過")
    segpos = {}
    for k, (x, y) in SEGS.items():
        a, bb = int(cal.searchsorted(pd.Timestamp(x))), int(cal.searchsorted(pd.Timestamp(y)))
        if str(cal[a].date()) != x or str(cal[bb].date()) != y:
            raise SystemExit(f"⛔ 段端點不對 {k}")
        segpos[k] = (a, bb)
    if segpos["主窗"] != (w0, w1):
        raise SystemExit("⛔ 主窗 ≠ ctx 窗")
    B50 = {k: RR.bench_row(cal, bench, a, bb + 1) for k, (a, bb) in segpos.items()}
    SF = R.stop_force_days(R.valid_from_data(sorted(ctx["closes"]), ctx["mk"], cal), w1)
    _, _, ind9 = R34.load_revenue()                         # D.DATA ＝ H2D 快照（build_ctx 已 use_snapshot）
    ind9 = {k: v for k, v in ind9.to_dict().items() if isinstance(v, str)}
    sha = __import__("subprocess").run(["git", "rev-parse", "origin/main"], capture_output=True, text=True, check=True, cwd=os.path.dirname(HERE)).stdout.strip()
    sha_, DATA = PRE.ensure_data(sha)
    cat = PRE.load_rev(DATA)[2]
    P = PRE.PIT(DATA, cat)
    IND = Ind(P, ind9, cal)
    T._G.update(cal=cal, NPX=ncal + 1)
    slip_sids = sorted(set(ctx["sig"]["sid"]) | set(ctx["sig13"]["sid"]))
    with Pool(procs) as pool:
        X_full = dict(pool.map(T._load_x, [(s, ctx["mk"].get(s, "twse")) for s in slip_sids], chunksize=8))
    SLG = T.slip_setup(ctx, X_full, SF, procs)
    DAY = {}
    for f, sig in (("fly", ctx["sig"]), ("vol", ctx["sig13"])):
        s = sig[sig[FAM[f]["x"]] >= 0]
        DAY[f] = {int(e): list(g["sid"]) for e, g in s.groupby("entry_pos")}
    _G.update(ctx=ctx, cal=cal, ncal=ncal, w0=w0, w1=w1, SF=SF, segpos=segpos, IND=IND, SLG=SLG, DAY=DAY, B50=B50)
    # 產業來源（Q8）
    src = {}
    for f, sig in (("fly", ctx["sig"]), ("vol", ctx["sig13"])):
        c = {}; diff = 0; n = 0
        for sid, e in zip(sig["sid"], sig["entry_pos"].astype(int)):
            a_, sa = IND.at(sid, e - 1, "pit"); b_, _ = IND.at(sid, e - 1, "now9")
            c[sa] = c.get(sa, 0) + 1; n += 1; diff += int(a_ != b_)
        src[FAM[f]["名"]] = {"訊號列": n, "來源": c, "pit 與 ⑨ 口徑不同": diff, "不同占比": diff / n if n else np.nan}
    log(f"[產業來源] {json.dumps(src, ensure_ascii=False)}")
    info = {"日曆": ncal, "日曆起訖": [str(cal[0].date()), str(cal[-1].date())], "段": {k: [str(cal[a].date()), str(cal[bb].date()), bb - a + 1] for k, (a, bb) in segpos.items()},
            "0050": B50, "停止交易股": len(SF), "tw-stock-data": sha, "產業資料": DATA, "產業來源": src, "登錄": regs, "現實版股數": len(slip_sids), "秒": round(time.time() - t0)}
    return info


# ═════════════ 一顆 ═════════════
def seg_metrics(eq, first, end):
    out = {}
    for k, (a, b) in _G["segpos"].items():
        c, m, v = RR.win_metrics(eq, first, end, a, b)
        out[f"{k}_cagr"] = float(c); out[f"{k}_mdd"] = float(m); out[f"{k}_vol"] = float(v)
    return out


def _one(args):
    key, r = args
    fam_k, arm = key.split("|")
    ctx = _G["ctx"]; rec = []
    base_f = SLIP[fam_k][1] if fam_k in SLIP else fam_k
    N = FAM[base_f]["N"]
    kw = {}
    if arm == "nocap":
        kw["cap_fn"] = cap_fn_factory("pit", N, rec, cap=None)
    elif arm == "cap":
        kw["cap_fn"] = cap_fn_factory("pit", N, rec)
    elif arm == "cap9":
        kw["cap_fn"] = cap_fn_factory("now9", N, rec)
    elif arm == "fake":
        K = _G["K"][(fam_k, r if fam_k == "fly" else 0)]
        kw["cap_fn"] = fake_fn_factory(K, np.random.default_rng([FSEED, FAM[fam_k]["id"], r]), _G["DAY"][fam_k], N, rec)
    au = []
    if fam_k in SLIP:
        from . import researchSlip as S
        S._G.clear(); S._G.update(_G["SLG"])
        cell = SLIP[fam_k][0]
        sig, op, cost, kw0 = S._G["INP"][(cell, T.SLIP_REAL)]
        o = S.run_engine(cell, sig, op, cost, dict(kw0, **kw), r, audit=au)
    elif fam_k == "fly":
        o = L.sim(ctx, {"stop_force": _G["SF"], **kw}, r, audit=au)
    else:
        o = R.simulate_mtm(ctx["sig13"], "H60", 20, np.random.default_rng(RR.P1_SEED0 + r), ctx["closes"], ctx["opens"], ctx["ncal"], log=[], d_max=None,
                           pick="relvol", queue_days=0, return_equity=True, stop_force=_G["SF"], audit=au, **kw)
    eq = np.asarray(o["equity"], float)
    iv, anom = YM.intervals(au, len(eq))
    row = {"key": key, "r": r, **seg_metrics(eq, o["first"], o["end"]), **YM.hold_stats(iv, ctx["closes"], eq, _G["segpos"]), "audit_anom": anom,
           "cagr": None, "first": int(o["first"]), "end": int(o["end"]), "trades": int(o["trades"]), "eq_sha": hashlib.sha256(eq.tobytes()).hexdigest()[:16],
           "sf_n": int(o.get("x_stop_force_n", -1)), "lu": int(o.get("tr_limit_up", 0))}
    row["cagr"] = row["主窗_cagr"]; row["mdd"] = row["主窗_mdd"]; row["vol"] = row["主窗_vol"]
    ex = {"iv": [(s, t0, t1) for s, t0, t1, sh in iv], "rec": rec}
    return row, ex


# ═════════════ 主程式 ═════════════
COLS = (["key", "r"] + [f"{s}_{m}" for s in SEGS for m in ("cagr", "mdd", "vol")] + [f"{s}_{m}" for s in SEGS for m in ("nh", "cash")]
        + ["cash_min", "audit_anom", "cagr", "mdd", "vol", "first", "end", "trades", "eq_sha", "sf_n", "lu"])


def plan1(reps):
    P = []
    for arm in ("base", "nocap", "cap", "cap9"):
        P.append((f"fly|{arm}", reps)); P.append((f"vol|{arm}", 1))
    for arm in ("base", "nocap", "cap"):
        P.append((f"slip_fly|{arm}", reps)); P.append((f"slip_vol|{arm}", 1))
    return P


def run_batch(pool, P, EX, rows):
    for k, n in P:
        t0 = time.time()
        res = pool.map(_one, [(k, r) for r in range(n)], chunksize=4)
        arm = k.split("|")[1]
        for x, e in res:
            rows.append(x)
            if k.startswith("slip") or arm == "nocap":
                continue                                   # 閘用臂、現實版：只留種子列
            if arm == "base":
                e = {"iv": e["iv"]}
            EX[(k, x["r"])] = e
        log(f"  [{k}] {n} 顆｜{time.time() - t0:.0f}s")


def run(a):
    global LOGF
    os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True); LOGF = os.path.join(OUT, "run.log")
    t00 = time.time()
    src = {f: hashlib.sha256(open(os.path.join(HERE, f), "rb").read()).hexdigest()[:16]
           for f in ("research11.py", "rerun17.py", "listexit_lines.py", "researchSlip.py", "researchT1fix.py", "researchYLmargin.py", "researchYLindcap.py")}
    log(f"===== researchYLindcap run procs={a.procs} reps={a.reps} {now_tpe()}（台北）｜讀法寫死 {TIME}｜{T.TAG}｜{src} =====")
    info = setup(a.procs)
    EX, rows = {}, []
    with Pool(a.procs) as pool:
        run_batch(pool, plan1(a.reps), EX, rows)
    SD = pd.DataFrame(rows).reindex(columns=COLS)
    # ── 退化（先寫；Q6）──
    DG = {}
    for k, g in SD.groupby("key", sort=False):
        d = {f"{s}_平均持股": float(g[f"{s}_nh"].median()) for s in SEGS}
        d.update({f"{s}_平均現金": float(g[f"{s}_cash"].median()) for s in SEGS})
        d.update({f"{s}_退化": bool(d[f"{s}_平均持股"] < 3 or d[f"{s}_平均現金"] > 0.30) for s in SEGS}); d["顆數"] = int(len(g))
        DG[k] = d
    DJ = {"寫入時間": now_tpe() + "（台北）", "說明": "⭐ 本檔在彙總任何報酬之前寫入（Q6）；退化 ＝ 平均持股 ＜ 3 或平均現金 ＞ 30%（段內逐日平均、種子中位）；退化格照登錄排除",
          "持股與現金": DG, "排除的格": sorted(k for k, v in DG.items() if k.split("|")[1] == "cap" and (v["探索_退化"] or v["確認_退化"]))}
    json.dump(DJ, open(os.path.join(OUT, "degeneracy.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log("[退化] 已寫 degeneracy.json：" + "；".join(f"{k} 探索 {v['探索_平均持股']:.2f} 檔／現金 {v['探索_平均現金']:.1%}、確認 {v['確認_平均持股']:.2f}／{v['確認_平均現金']:.1%}"
                                              for k, v in DG.items() if not k.endswith("nocap")))
    # ── 假訊號（Q7）：k_t 取自加上限臂 ──
    K = {}
    for (k, r), e in EX.items():
        f, arm = k.split("|")
        if arm == "cap" and f in FAM:
            c = {}
            for t, sid, i, av, ok in e["rec"]:
                if not ok:
                    c[t] = c.get(t, 0) + 1
            K[(f, r)] = c
    _G["K"] = K
    with Pool(a.procs) as pool:
        run_batch(pool, [("fly|fake", a.reps), ("vol|fake", a.reps)], EX, rows)
    SD = pd.DataFrame(rows).reindex(columns=COLS)
    SD.to_csv(os.path.join(OUT, "seeds_part.csv"), index=False)
    keep = {k: v for k, v in EX.items() if not k[0].endswith("fake")}
    pickle.dump({"EX": keep, "info": info, "DJ": DJ, "src": src, "Kfake": {k: v for k, v in EX.items() if k[0].endswith("fake") and k[1] < 3}},
                open(os.path.join(WORK, "ex.pkl"), "wb"), protocol=5)
    json.dump({"setup": info, "程式": src, "reps": a.reps, "秒_run": round(time.time() - t00)}, open(os.path.join(OUT, "setup.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1, default=str)
    report(a)


# ═════════════ 彙總 ═════════════
ORD = {"不合格": 0, "另列": 1, "合格": 2}


def gates(SD):
    ref = pd.read_csv(os.path.join(HERE, "resultsT1fix", "seeds.csv.gz"), dtype={"eq_sha": str}, **RP)
    out = {}
    for k, rk, full in (("fly|base", "c1", True), ("vol|base", "c13", True), ("slip_fly|base", "slip1_real", False), ("slip_vol|base", "slip13_real", False)):
        g = SD[SD["key"] == k].set_index("r").sort_index()
        rf = ref[(ref["key"] == rk) & (ref["var"] == "t1")].set_index("r").sort_index()
        bad = 0
        for r in g.index:
            ok = all(repr(float(g.at[r, c])) == repr(float(rf.at[r, c])) for c in (("cagr", "mdd", "vol") if full else ("cagr", "mdd"))) and str(g.at[r, "eq_sha"]) == str(rf.at[r, "eq_sha"])
            if full:
                ok = ok and all(int(g.at[r, c]) == int(rf.at[r, c]) for c in ("first", "end", "trades"))
            bad += not ok
        out[f"G2 {k} ＝ resultsT1fix {rk} t1"] = {"顆數": int(len(g)), "不同": int(bad)}
    for f in ("fly", "vol", "slip_fly", "slip_vol"):
        g = SD[SD["key"] == f"{f}|base"].set_index("r").sort_index(); h = SD[SD["key"] == f"{f}|nocap"].set_index("r").sort_index()
        bad = sum(not (str(g.at[r, "eq_sha"]) == str(h.at[r, "eq_sha"]) and repr(float(g.at[r, "cagr"])) == repr(float(h.at[r, "cagr"]))
                       and repr(float(g.at[r, "mdd"])) == repr(float(h.at[r, "mdd"])) and int(g.at[r, "trades"]) == int(h.at[r, "trades"])) for r in g.index)
        out[f"G1 {f} 不設上限 ＝ 原版"] = {"顆數": int(len(g)), "不同": int(bad)}
    return out


def lab(c, m, b):
    c50, r50 = b["cagr"], b["cagr"] / abs(b["mdd"])
    return "合格" if (c > c50 and c / abs(m) >= r50) else ("另列" if c > c50 else "不合格")


def conc(ivs, IN, days_of, ver, a, b):
    """⑨ 算法：換股日（有買進）收盤持股的最大產業檔數；ivs ＝ 多顆的 [(sid, t0, t1)]。"""
    mx = []; viol = 0
    for iv in ivs:
        for t in sorted({t0 for s, t0, t1 in iv if a <= t0 <= b}):
            held = [s for s, t0, t1 in iv if t0 <= t < t1]
            c = {}
            for s in held:
                k_ = IN.at(s, t - 1, ver)[0] or f"查無:{s}"
                c[k_] = c.get(k_, 0) + 1
            mx.append(max(c.values()))
    mx = np.array(mx)
    return {"換股日": int(len(mx)), "最大產業檔數中位": float(np.median(mx)) if len(mx) else np.nan, "最大產業檔數最大": int(mx.max()) if len(mx) else 0,
            "同產業＞3檔的換股日占比": float((mx > 3).mean()) if len(mx) else np.nan}


def report(a):
    global LOGF
    LOGF = os.path.join(OUT, "run.log")
    SD = pd.read_csv(os.path.join(OUT, "seeds_part.csv"), dtype={"eq_sha": str}, **RP).drop_duplicates(["key", "r"], keep="last").sort_values(["key", "r"]).reset_index(drop=True)
    SD.to_csv(os.path.join(OUT, "seeds.csv.gz"), index=False)
    X = pickle.load(open(os.path.join(WORK, "ex.pkl"), "rb")); EX = X["EX"]; info = X["info"]
    if "ctx" not in _G:
        _G["ctx"] = T.build_ctx(True)
        cal = _G["ctx"]["cal"]
        _, _, ind9 = R34.load_revenue()
        sha_, DATA = PRE.ensure_data(info["tw-stock-data"])
        _G["IND"] = Ind(PRE.PIT(DATA, PRE.load_rev(DATA)[2]), {k: v for k, v in ind9.to_dict().items() if isinstance(v, str)}, cal)
        _G["segpos"] = {k: (int(cal.searchsorted(pd.Timestamp(x))), int(cal.searchsorted(pd.Timestamp(y)))) for k, (x, y) in SEGS.items()}
    ctx = _G["ctx"]; cal = ctx["cal"]; IN = _G["IND"]; segpos = _G["segpos"]
    B50 = info["0050"]
    G = gates(SD); gok = all(v["不同"] == 0 for v in G.values())
    log(f"[閘 G1 不設上限＝原版／G2 原版＝resultsT1fix] {json.dumps(G, ensure_ascii=False)}")
    cells = []
    for k, g in SD.groupby("key", sort=False):
        for s in SEGS:
            c, m = float(g[f"{s}_cagr"].median()), float(g[f"{s}_mdd"].median())
            cells.append({"key": k, "段": s, "顆數": int(len(g)), "年化": c, "回落": m, "比值": c / abs(m), "標籤": lab(c, m, B50[s]),
                          "年化_p10": float(g[f"{s}_cagr"].quantile(0.1)), "年化_p90": float(g[f"{s}_cagr"].quantile(0.9)),
                          "平均持股": float(g[f"{s}_nh"].median()), "平均現金": float(g[f"{s}_cash"].median()), "交易筆數中位": float(g["trades"].median()),
                          "0050年化": B50[s]["cagr"], "0050回落": B50[s]["mdd"]})
    TB = pd.DataFrame(cells); TB.to_csv(os.path.join(OUT, "cells.csv"), index=False)
    C = {(r["key"], r["段"]): r for r in cells}
    DJ = json.load(open(os.path.join(OUT, "degeneracy.json"), encoding="utf-8"))
    V = {}; SK_rows = []
    for f in ("fly", "vol"):
        nm = FAM[f]["名"]; N = FAM[f]["N"]
        q, b = (lambda s: C[(f"{f}|cap", s)]), (lambda s: C[(f"{f}|base", s)])
        seg_lab = {s: q(s)["標籤"] for s in SEGS}
        strict = min((seg_lab[s] for s in JUDGE), key=lambda x: ORD[x])
        cmp4 = [(q(s)["年化"], b(s)["年化"]) for s in JUDGE] + [(q(s)["比值"], b(s)["比值"]) for s in JUDGE]
        better = all(x >= y for x, y in cmp4) and any(x > y for x, y in cmp4)
        deg = DJ["持股與現金"][f"{f}|cap"]
        excluded = bool(deg["探索_退化"] or deg["確認_退化"])
        dcash = {s: (q(s)["平均現金"] - b(s)["平均現金"]) * 100 for s in SEGS}
        cash_flag = dcash["主窗"] >= 5
        if excluded:
            concl = f"同產業上限 3 檔在 {nm} 上：加上限後退化（照登錄排除），沒有可判的格"
        else:
            concl = f"同產業上限 3 檔在 {nm} 上有改善（暫定）" if better else f"同產業上限 3 檔在 {nm} 上沒有改善"
        v = {"段標籤": seg_lab, "兩段取較嚴（對 0050）": strict, "原策略段標籤": {s: b(s)["標籤"] for s in SEGS}, "比原策略好": better, "退化排除": excluded,
             "結論": concl, "早年": "不可判定（營飆 v1 沒有早年版面；industry_pit 早年覆蓋不足）",
             "差": {s: {"年化pt": (q(s)["年化"] - b(s)["年化"]) * 100, "回落pt": (q(s)["回落"] - b(s)["回落"]) * 100, "比值": q(s)["比值"] - b(s)["比值"]} for s in SEGS},
             "現金比例變化pt": dcash, "現金升≥5點": cash_flag}
        # 假訊號
        fk = SD[SD["key"] == f"{f}|fake"]
        v["假訊號"] = {}
        for s in SEGS:
            fc = fk[f"{s}_cagr"].to_numpy(); fr = fc / np.abs(fk[f"{s}_mdd"].to_numpy())
            v["假訊號"][s] = {"次數": int(len(fk)), "年化中位": float(np.median(fc)), "回落中位": float(fk[f"{s}_mdd"].median()),
                            "年化p10": float(np.percentile(fc, 10)), "年化p90": float(np.percentile(fc, 90)),
                            "p_年化": float((fc >= q(s)["年化"]).mean()), "p_比值": float((fr >= q(s)["比值"]).mean()),
                            "平均現金中位": float(fk[f"{s}_cash"].median())}
        if f == "fly":
            qq = SD[SD["key"] == "fly|cap"].set_index("r").sort_index(); bb = SD[SD["key"] == "fly|base"].set_index("r").sort_index().loc[qq.index]
            v["同顆配對"] = {s: {"年化較高": int((qq[f"{s}_cagr"] > bb[f"{s}_cagr"]).sum()), "逐位元相同": int((qq["eq_sha"] == bb["eq_sha"]).sum()), "顆數": int(len(qq))} for s in SEGS}
        # 現實版、⑨ 口徑描述
        v["現實版"] = {s: {"原策略": {k_: C[(f"slip_{f}|base", s)][k_] for k_ in ("年化", "回落", "比值", "標籤", "平均現金")},
                          "加上限": {k_: C[(f"slip_{f}|cap", s)][k_] for k_ in ("年化", "回落", "比值", "標籤", "平均現金")}} for s in SEGS}
        cmpr = [(C[(f"slip_{f}|cap", s)]["年化"], C[(f"slip_{f}|base", s)]["年化"]) for s in JUDGE] + [(C[(f"slip_{f}|cap", s)]["比值"], C[(f"slip_{f}|base", s)]["比值"]) for s in JUDGE]
        v["現實版比原策略好"] = all(x >= y for x, y in cmpr) and any(x > y for x, y in cmpr)
        v["⑨口徑上限（描述）"] = {s: {k_: C[(f"{f}|cap9", s)][k_] for k_ in ("年化", "回落", "比值", "標籤", "平均現金")} for s in SEGS}
        # 跳過統計（Q8）
        sig = ctx["sig"] if f == "fly" else ctx["sig13"]
        gmap = {(s_, int(e)): float(g_) for s_, e, g_ in zip(sig["sid"], sig["entry_pos"], sig[FAM[f]["g"]])}
        sig_year = pd.Series([cal[int(e)].year for e in sig["entry_pos"]]).value_counts().to_dict()
        recs = [(r, EX[(f"{f}|cap", r)]["rec"]) for r in range(SD[SD["key"] == f"{f}|cap"]["r"].nunique())]
        nrun = len(recs)
        yr = {}; blocked, filled = set(), set(); nb = nf = 0
        for r, rec in recs:
            for t, sid, i, av, ok in rec:
                if not (_G["segpos"]["主窗"][0] <= t <= _G["segpos"]["主窗"][1]):
                    continue
                y = cal[t].year; d = yr.setdefault(y, {"被問到": 0, "跳過": 0, "原本會買被擋": 0, "補到": 0})
                d["被問到"] += 1
                if not ok:
                    d["跳過"] += 1
                    if i < av:
                        d["原本會買被擋"] += 1; nb += 1; blocked.add((sid, t))
                        if r == 0:
                            SK_rows.append({"策略": nm, "類": "被擋", "sid": sid, "日": str(cal[t].date()), "產業": IN.at(sid, t - 1)[0], "g": gmap.get((sid, t), np.nan)})
                elif i >= av:
                    d["補到"] += 1; nf += 1; filled.add((sid, t))
                    if r == 0:
                        SK_rows.append({"策略": nm, "類": "補上", "sid": sid, "日": str(cal[t].date()), "產業": IN.at(sid, t - 1)[0], "g": gmap.get((sid, t), np.nan)})
        v["跳過逐年（每顆平均）"] = [{"年": y, "訊號列": int(sig_year.get(y, 0)), **{k_: x / nrun for k_, x in d.items()},
                                  "跳過占被問到": d["跳過"] / d["被問到"] if d["被問到"] else np.nan, "跳過占訊號列": (d["跳過"] / nrun) / sig_year[y] if sig_year.get(y) else np.nan}
                                 for y, d in sorted(yr.items())]
        tot = {k_: sum(d[k_] for d in yr.values()) / nrun for k_ in ("被問到", "跳過", "原本會買被擋", "補到")}
        v["跳過合計（每顆平均）"] = {**tot, "補到比例": tot["補到"] / tot["原本會買被擋"] if tot["原本會買被擋"] else np.nan, "顆數": nrun}
        v["被擋 vs 補上逐筆（去重，固定出場毛報酬 " + FAM[f]["g"] + "）"] = {"被擋": YM.dist([gmap.get(x, np.nan) for x in blocked]), "補上": YM.dist([gmap.get(x, np.nan) for x in filled])}
        # 集中度（兩種口徑）與等效獨立
        a_, b_ = segpos["主窗"]
        v["集中度（⑨ 算法，主窗）"] = {}
        for arm in ("base", "cap", "cap9"):
            ivs = [EX[(f"{f}|{arm}", r)]["iv"] for r in range(SD[SD["key"] == f"{f}|{arm}"]["r"].nunique())]
            v["集中度（⑨ 算法，主窗）"][arm] = {"industry_pit 當時": conc(ivs, IN, None, "pit", a_, b_), "⑨ 現值套回": conc(ivs, IN, None, "now9", a_, b_), "顆數": len(ivs)}
        v["等效獨立檔數（r0）"] = {}
        for arm in ("base", "cap"):
            iv = [(s, t0, t1, 0.0) for s, t0, t1 in EX[(f"{f}|{arm}", 0)]["iv"]]
            days = sorted({t0 for s, t0, t1, _ in iv if a_ <= t0 <= b_})
            en = YM.eff_n(iv, ctx["closes"], days)
            v["等效獨立檔數（r0）"][arm] = {s: {"換股日": int(sum(1 for x in en if segpos[s][0] <= x[0] <= segpos[s][1])),
                                           "平均N": float(np.nanmean([x[1] for x in en if segpos[s][0] <= x[0] <= segpos[s][1]])),
                                           "平均ρ": float(np.nanmean([x[2] for x in en if segpos[s][0] <= x[0] <= segpos[s][1]])),
                                           "平均N_eff": float(np.nanmean([x[3] for x in en if segpos[s][0] <= x[0] <= segpos[s][1]]))} for s in SEGS}
            v.setdefault("窗尾仍持有（r0）", {})[arm] = sorted(s for s, t0, t1, _ in iv if t0 <= b_ < t1)
        V[f] = v
        log(f"[{nm}] {concl}｜段標籤 {seg_lab}｜比原策略好 {better}｜現金變化 {dcash['主窗']:+.1f} 點｜跳過每顆 {tot['跳過']:.0f}、補到比例 {v['跳過合計（每顆平均）']['補到比例']:.2f}")
    pd.DataFrame(SK_rows).to_csv(os.path.join(OUT, "skipped.csv.gz"), index=False)
    S = {"件": "PREREG營量營飆同產業上限 seq1／seq2", "登錄sha": [REG_SHA, REG_SHA2], "讀法寫死": TIME, "停止交易強制出場": "開", "閘": {"G0": True, **G, "全過": gok},
         "setup": info, "退化": DJ, "策略": V, "減資斷點": "待查（裁定 seq329 §五；本件照現行引擎跑）", "產出": now_tpe() + "（台北）"}
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=lambda o: float(o) if np.isscalar(o) else str(o))
    if not gok:
        raise SystemExit("⛔ 閘門不過")


# ═════════════ 網頁 ═════════════
def page(a=None):
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    TB = pd.read_csv(os.path.join(OUT, "cells.csv"), **RP)
    C = {(r["key"], r["段"]): r for _, r in TB.iterrows()}
    chk = {}
    cf = os.path.join(OUT, "check.json")
    if os.path.exists(cf):
        chk = json.load(open(cf, encoding="utf-8"))
    e = html.escape
    p = lambda x: "—" if x is None or not np.isfinite(x) else f"{x * 100:+.1f}%"
    pp = lambda x: "—" if x is None or not np.isfinite(x) else f"{x * 100:.1f}%"
    V = S["策略"]; B = S["setup"]["0050"]
    secs = []
    for f in ("vol", "fly"):
        v = V[f]; nm = FAM[f]["名"]
        rows = []
        for s in ("探索", "確認", "主窗"):
            b, q, q9 = C[(f"{f}|base", s)], C[(f"{f}|cap", s)], C[(f"{f}|cap9", s)]
            fk = v["假訊號"][s]
            rows.append(f"<tr><th>{s}</th><td>{p(b['年化'])}／{p(b['回落'])}<br><span class=m>{b['標籤']}・現金 {pp(b['平均現金'])}</span></td>"
                        f"<td><b>{p(q['年化'])}／{p(q['回落'])}</b><br><span class=m>{q['標籤']}・現金 {pp(q['平均現金'])}</span></td>"
                        f"<td>{p(fk['年化中位'])}／{p(fk['回落中位'])}<br><span class=m>p 年化 {fk['p_年化']:.2f}・p 比值 {fk['p_比值']:.2f}</span></td>"
                        f"<td>{p(q9['年化'])}／{p(q9['回落'])}</td><td>{p(B[s]['cagr'])}／{p(B[s]['mdd'])}</td></tr>")
        sl = "".join(f"<tr><th>{s}</th><td>{p(v['現實版'][s]['原策略']['年化'])}／{p(v['現實版'][s]['原策略']['回落'])}（{v['現實版'][s]['原策略']['標籤']}）</td>"
                     f"<td>{p(v['現實版'][s]['加上限']['年化'])}／{p(v['現實版'][s]['加上限']['回落'])}（{v['現實版'][s]['加上限']['標籤']}）</td></tr>" for s in ("探索", "確認", "主窗"))
        yr = "".join(f"<tr><td>{y['年']}</td><td>{y['訊號列']}</td><td>{y['被問到']:.1f}</td><td>{y['跳過']:.1f}</td><td>{pp(y['跳過占被問到'])}</td><td>{y['原本會買被擋']:.1f}</td><td>{y['補到']:.1f}</td></tr>"
                     for y in v["跳過逐年（每顆平均）"])
        tt = v["跳過合計（每顆平均）"]
        dd = v[[k for k in v if k.startswith("被擋 vs 補上")][0]]
        cc = v["集中度（⑨ 算法，主窗）"]
        conc_rows = "".join(f"<tr><th>{ {'base': '原策略', 'cap': '加上限（pit）', 'cap9': '加上限（⑨ 口徑，描述）'}[k] }</th>"
                            f"<td>{pp(x['industry_pit 當時']['同產業＞3檔的換股日占比'])}（最多 {x['industry_pit 當時']['最大產業檔數最大']}）</td>"
                            f"<td>{pp(x['⑨ 現值套回']['同產業＞3檔的換股日占比'])}（最多 {x['⑨ 現值套回']['最大產業檔數最大']}）</td></tr>" for k, x in cc.items())
        en = v["等效獨立檔數（r0）"]
        cash_note = "；⚠ 現金比例比原策略高 ≥ 5 點 ⇒ 部分可由降曝險解釋" if v["現金升≥5點"] else ""
        secs.append(f"<section><h2>{nm}：{e(v['結論'])}</h2>"
                    f"<p>加上限後：探索 {v['段標籤']['探索']}、確認 {v['段標籤']['確認']}（對 0050）；比原策略好：{'是' if v['比原策略好'] else '否'}；"
                    f"主窗現金比例變化 {v['現金比例變化pt']['主窗']:+.1f} 點{cash_note}；早年 {e(v['早年'])}。</p>"
                    "<table><thead><tr><th>段</th><th>原策略</th><th>加同產業上限 3 檔</th><th>假訊號臂（同日同數量隨機跳過）</th><th>⑨ 口徑上限（描述）</th><th>0050</th></tr></thead><tbody>"
                    + "".join(rows) + "</tbody></table><p class=m>年化中位／回落中位；p ＝ 假訊號 200 次裡不輸本件的比例。</p>"
                    + "<h3>現實版（並報）</h3><table><thead><tr><th>段</th><th>原策略</th><th>加上限</th></tr></thead><tbody>" + sl + "</tbody></table>"
                    + f"<h3>被跳過的候選（每顆平均）</h3><table><thead><tr><th>年</th><th>訊號列</th><th>被問到</th><th>跳過</th><th>跳過占被問到</th><th>原本會買被擋</th><th>補到</th></tr></thead><tbody>{yr}</tbody></table>"
                    + f"<p class=m>合計：跳過 {tt['跳過']:.1f}、原本會買被擋 {tt['原本會買被擋']:.1f}、補到 {tt['補到']:.1f} ⇒ 補到比例 {pp(tt['補到比例'])}（{tt['顆數']} 顆平均）。</p>"
                    + f"<p>被擋那批 vs 補上那批（固定出場毛報酬、去重，描述）：被擋 {dd['被擋'].get('筆數', 0)} 筆 平均 {p(dd['被擋'].get('平均'))}、中位 {p(dd['被擋'].get('中位'))}；"
                      f"補上 {dd['補上'].get('筆數', 0)} 筆 平均 {p(dd['補上'].get('平均'))}、中位 {p(dd['補上'].get('中位'))}。</p>"
                    + "<h3>集中度（換股日同產業 ＞3 檔的占比）</h3><table><thead><tr><th></th><th>industry_pit 當時分類</th><th>⑨ 現值套回</th></tr></thead><tbody>" + conc_rows + "</tbody></table>"
                    + f"<p class=m>等效獨立檔數（r0、主窗）：原策略 {en['base']['主窗']['平均N_eff']:.1f}（ρ {en['base']['主窗']['平均ρ']:.2f}）→ 加上限 {en['cap']['主窗']['平均N_eff']:.1f}（ρ {en['cap']['主窗']['平均ρ']:.2f}）。"
                      f"窗尾（2026-08-24）仍持有：原 {len(v['窗尾仍持有（r0）']['base'])} 檔、加上限 {len(v['窗尾仍持有（r0）']['cap'])} 檔。</p></section>")
    src = S["setup"]["產業來源"]
    srcs = "".join(f"<li>{e(k)}：訊號列 {x['訊號列']}；來源 {e(json.dumps(x['來源'], ensure_ascii=False))}；pit 與 ⑨ 口徑分類不同 {pp(x['不同占比'])}</li>" for k, x in src.items())
    gate = "、".join(f"{k} 不同 {v['不同']}" for k, v in S["閘"].items() if isinstance(v, dict))
    vv, vf = V["vol"], V["fly"]
    head = (f"<p class=lead><b>結論：{e(vv['結論'])}；{e(vf['結論'])}。</b></p><ul>"
            f"<li>營量 v1：加上限後確認段 {p(C[('vol|cap', '確認')]['年化'])}／{p(C[('vol|cap', '確認')]['回落'])}，原策略 {p(C[('vol|base', '確認')]['年化'])}／{p(C[('vol|base', '確認')]['回落'])}；"
            f"探索段 {p(C[('vol|cap', '探索')]['年化'])}／{p(C[('vol|cap', '探索')]['回落'])}（原 {p(C[('vol|base', '探索')]['年化'])}／{p(C[('vol|base', '探索')]['回落'])}）。</li>"
            f"<li>營飆 v1：加上限後確認段 {p(C[('fly|cap', '確認')]['年化'])}／{p(C[('fly|cap', '確認')]['回落'])}，原策略 {p(C[('fly|base', '確認')]['年化'])}／{p(C[('fly|base', '確認')]['回落'])}；"
            f"探索段 {p(C[('fly|cap', '探索')]['年化'])}／{p(C[('fly|cap', '探索')]['回落'])}（原 {p(C[('fly|base', '探索')]['年化'])}／{p(C[('fly|base', '探索')]['回落'])}）。</li>"
            + "".join(f"<li>{FAM[f]['名']} 在假訊號分佈（同日同數量隨機跳過、200 次）的位置：確認段 p ＝ {V[f]['假訊號']['確認']['p_年化']:.2f}、探索段 p ＝ {V[f]['假訊號']['探索']['p_年化']:.2f}"
                      f"（p ＝ 假訊號年化不輸本件的比例）；同產業 ＞3 檔的換股日（原策略）：industry_pit 當時 {pp(V[f]['集中度（⑨ 算法，主窗）']['base']['industry_pit 當時']['同產業＞3檔的換股日占比'])}、"
                      f"⑨ 現值套回 {pp(V[f]['集中度（⑨ 算法，主窗）']['base']['⑨ 現值套回']['同產業＞3檔的換股日占比'])}。</li>" for f in ("vol", "fly")) +
            "<li>規則：其他一字不動，只加「同一產業最多同時持有 3 檔」；會超過的候選跳過、往下看下一檔；看完還有空位就留空。產業用 industry_pit 當時分類。</li>"
            "<li>⚠ 營量、營飆的結果事前看過 ⇒ 事後重切，就算改善也最多「暫定」。⛔ 不能讀成「分散沒用」——只測了上限 3 檔這一種。⛔ 不是買賣建議。</li>"
            "<li>⚠ 減資價格斷點待查（裁定 seq329 §五另案）；本件照現行引擎跑。</li></ul>")
    notes = ("<section><h2>怎麼算的</h2><ul>"
             "<li>本體：營量 v1、營飆 v1 正式版（資料尾補回 T1、停止交易強制出場開、母體 20 日均量 ≥ 500 張、主窗 2017-03-02～2026-08-24）；出場照原策略（營量 60 根、營飆 120 根收盤）。</li>"
             "<li>上限接在引擎既有的 cap_fn（⛔ 沒改引擎）；不設上限時走同一條包裝與原版逐位元相同（閘 G1）。</li>"
             f"<li>產業分類來源：<ul>{srcs}</ul>pit最後已知／首段前／空隙 ＝ 已下市股缺段（用最近一段）；現值補 ＝ industry_pit 沒有、用現值（⛔ 不是當時分類）；營收彙總表 ＝ 公告當時的類別；查無 ⇒ 不設限。</li>"
             "<li>假訊號臂：每天跳過的檔數跟加上限臂一樣多，但隨機挑、不看產業（200 次）。</li>"
             "<li>判：兩段（探索、確認）都年化 ≥ 且 年化÷回落 ≥ 原策略、且至少一項嚴格較大 ⇒ 比原策略好；另報對 0050 的標籤。早年段不可判定。</li>"
             "<li>營飆 v1 的 0050 濾網（0050 在 200 日線上才進）是擋長空頭、不是急跌保護。</li>"
             f"<li>閘門：{e(gate)}。</li>"
             + (f"<li>獨立查核（--check）：{e(chk.get('結論', ''))}</li>" if chk else "")
             + f"<li>產出 {now_tpe()}（台北）；程式 backtest/researchYLindcap.py；結果 backtest/resultsYLindcap/；讀法在程式檔頭（Q1～Q9）。</li></ul></section>")
    RL_CSS = CSS
    doc = (f"<!doctype html><html lang=zh-Hant><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
           f"<title>營量營飆同產業上限</title><style>{RL_CSS}</style></head><body>"
           f"<h1>營量營飆同產業上限</h1><p class=m>PREREG營量營飆同產業上限 seq2（sha {REG_SHA2}；seq1 {REG_SHA} 判定一字未動；裁定 seq329 §三、N_組合 ＋1）｜回測線｜停止交易強制出場：開</p>"
           + head + "".join(secs) + notes + "</body></html>")
    open(PAGE, "w", encoding="utf-8").write(doc)
    print("寫出", PAGE)


CSS = """:root{--bg:#fbfaf7;--fg:#1d1d1b;--mut:#6b6a66;--line:#e2dfd8;--acc:#1f5f8b;--card:#ffffff}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#161615;--fg:#ecebe6;--mut:#a3a19a;--line:#33322f;--acc:#7cb6de;--card:#1e1e1c}}
:root[data-theme="dark"]{--bg:#161615;--fg:#ecebe6;--mut:#a3a19a;--line:#33322f;--acc:#7cb6de;--card:#1e1e1c}
body{background:var(--bg);color:var(--fg);font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif;line-height:1.6;margin:0;padding:24px 16px;max-width:980px;margin:auto}
h1{font-size:1.5rem;margin:.2em 0}h2{font-size:1.2rem;border-bottom:2px solid var(--acc);padding-bottom:.2em;margin-top:2em}h3{font-size:1rem;margin-top:1.4em}
.lead{font-size:1.08rem}.m{color:var(--mut);font-size:.88rem}
table{border-collapse:collapse;width:100%;margin:.4em 0;font-size:.9rem;display:block;overflow-x:auto;background:var(--card)}
th,td{border:1px solid var(--line);padding:5px 8px;text-align:right;white-space:nowrap}th{text-align:left}thead th{background:var(--line)}"""


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["run", "report", "page"])
    ap.add_argument("--procs", type=int, default=2); ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--smoke", action="store_true")              # 冒煙：輸出到 ~/yicwork/smoke（數字不是本件結果）
    a = ap.parse_args()
    if a.smoke:
        OUT = os.path.join(WORK, "smoke"); PAGE = os.path.join(OUT, "smoke.html")
    {"run": run, "report": report, "page": page}[a.mode](a)
