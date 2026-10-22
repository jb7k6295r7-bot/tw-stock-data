# -*- coding: utf-8 -*-
"""PREREG「產業營收加速改長抱」seq2【頻率表・退化檢查・乾跑】（台股策略線登錄 seq2 sha 800ad3a4bcacd7da，取代 seq1 sha 2f0f5925257a3260；
裁定 seq452 §二 發號、seq453 核 seq2：36 格挑 1、N_組合 ＋1；先交頻率表、⛔ 不附報酬）——回測線計算子代理。
⛔ 不算任何報酬：本檔不讀、不用任何收盤／還原價的數值（只用「有沒有成交」「開盤是否有限」、漲跌停旗標、壞根位置、市值排序），
   乾跑 ＝ 全部價格視為不變（R 全 0）：權益恆 1、每批金額只由份數與現金決定 ⇒ 持股檔數、現金比例是純構造量。
⛔ 不 commit；不改前件檔：researchIndRev_prereg（PRE，seq3 正式版：A 表 _a_month、ranked、a_val、elig_at、picks_at、attach_months）、
   researchIndRevLag_prereg（LAGP：setup ＝ GATE_V2＋15 日規則、part_ctx ＝ 主段 H2D edc6f／早年上市＋上櫃 eotc 版面與 W1 面板快取）只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchIndRevHold_freq --step A|flags_main|flags_early|freq|rand [--procs 4]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchIndRevHold_freq_check

═══ 讀法（寫死於 2026-10-22 23:29（台北），在算任何本件數字之前；★ ＝ 登錄沒寫清楚、執行者補；〔 〕＝ 另一讀法並報）═══
 F0 登錄：信箱根目錄＋_封存-* 檔名含 sha800ad3a4bcacd7da（seq2）去 pw1 行 sha256 前 16 碼相符才跑；seq1 同法核（只記錄）
    格 ＝ A {A1,A2,A3} × K {1,3} × H {250,500,750} × S {S1,S3} ＝ 36（seq453：性質欄「18 格」是筆誤，以 §二 為準）
 F1 資料：月營收、industry_pit ＝ tw-stock-data origin/main（執行時 sha，PRE.ensure_data git archive 唯讀）；
    價格旗標、W1 面板、市值 ＝ LAGP.part_ctx 快取（主：H2D edc6f8002f＋panel_ext（GATE_V2 pit_valid 剔）；
    早年：⭐ 上市＋上櫃版面 eotc_f65bb03e11（登錄「上市＋上櫃版面」；W1 面板 LAGP 重建；⚠ 上櫃無法人 ⇒ 早年 W1 實際只有上市，照實報））
    GATE_V2 開（LAGP.setup 第一行 UG.set_gate_v2(True)；登錄 §五 seq296）
 F2 可用日（登錄 §一）：M ≤ 2025-12 ⇒ M＋1 月 10 日之後第一個交易日；M ≥ 2026-01 ⇒ 15 日之後（LAGP.setup，R34.rebalance_dates 嚴格大於）
    A 表 ＝ PRE._a_month（compute_ind "new"，pit 版；判定日 ＝ 可用日前一交易日）以本次 origin/main 全部重算（M ≥ 2011-06）
 F3 批（登錄 §二「每月可用日收盤判、次一交易日開盤買」）：每個營收月 M 的可用日 p ⇒ ★ 批日 b ＝ p＋1（次一交易日）開盤買；營收月 ＝ M（＝ Mlast[b]）
    ⚠ 前件 seq3 是「可用日當天開盤買」；本件照登錄字面晚一天
    挑產業：PRE.ranked("pit", A, M, "top")（公司數 ≥ 5、A 有限、A 大到小、同值依名稱）中 ★ A ＞ 0 者取前 K（登錄「只有 A ＞ 0 才算加速；不足 K 缺額放現金」；
      ⚠ 前件 seq3 程式沒有 A ＞ 0 這道，照登錄字面加）
    挑股：成員 ＝ PRE.picks_at 同一套（b 同月最後量測日 W1 eligible ∩ ctx 有價格 ∩ ind_at(代號, b−1) ∩ 市值(b−1) 有限 ＞ 0，市值大到小、同值依代號）
      S1 ＝ 前 20（不足全買；⭐ 與 PRE.picks_at S1 逐批比對相同）｜S3 ＝ 全部成員（seq2 新軸；⚠ 與前件 seq3 的 S3「營收創 24 月新高前 10」不同義）
    金額：每批 ＝ min(1 ÷ n_H, 批日開盤可用現金)，★ n_H ＝ round(H ÷ 21) ＝ 12／24／36 份（登錄「H/21 份」非整數）；
      每產業 ＝ 批 ÷ K（★「各產業先等額」＋「缺額放現金」⇒ 除以 K、不是除以實際挑到的產業數）；產業內 ＝ ÷ 實際檔數
 F4 持有（登錄 §二）：買在 b 開盤；到期 mat ＝ b＋H−1（b 算第 1 日），mat 收盤賣；期間不賣不換
    買不到（★ 該部分放現金到該批到期）：b 無成交或開盤無效｜b 開盤漲停（⭐ seq412：上市 exright 有 open_base 的日子改用 limit_price(open_base) 判；
      上櫃 otcexright open_base 全空維持舊口徑）｜b 是硬斷點壞根（★）
    提前出場（★ 放現金到該批到期）：停止交易（R.stop_force_days，最後有效收盤 L ＜ 資料尾 ⇒ L＋1 收盤）｜
      ⭐ 硬斷點 seq335（research11.load_bars 壞根 ＝ D.breakpoints 價格規則 ∪ 缺口 ≥ 5 日）：(b, min(mat, 資料尾)] 第一個壞根 kb ⇒ kb 前一根有成交日收盤
      〔另一讀法：整筆剔除；本檔只計數〕；load_bars 回 None（＜ 260 根）⇒ 只用缺口規則（計數）
    到期日無成交或收盤跌停（dn_c，exright 同修）⇒ ★ 順延到下一個可賣收盤（計數）；份額在全部成員賣完後才回收
    持股計數 ＝ 收盤後：一筆在 [b, 出場日−1] 算持有；資料尾仍未出場 ⇒ 持有到尾
 F5 世界與段（登錄 §三）
    主（★ 主讀法：一條連續帳 2015-08-12 起第一批（W1 面板 2015-08-03 起才有，＝ researchScore EARLY_B 起點）～資料尾 2026-08-24）：
      早年B 2015-08-03～2016-12-30｜探索 2017-03-02～2021-12-30｜確認 2022-01-03～2026-08-24
      資料尾 ＝ 2026-08-24（＝ 前件 seq3／LAGP 確認段尾；panel_ext 最後量測日 2026-08-03 ⇒ 2026-09 起沒有 W1、不能成批）；另報以日曆尾 2026-09-24 計的走完批數
      〔讀法乙：主帳 2017-03-02 起第一批（＝ 前件 seq3 窗首）⇒ 探索段含建倉期〕
    早年（eotc 版面，W1 2012-06-01 起）：早年A 2012-06-01～2014-12-30（帳從 2012-06 第一批起；版面日曆尾 2014-12-31）
    ⚠ 登錄「早年 2012-06～2016-12（上市＋上櫃版面）」橫跨兩個版面（2015 起是主段 H2D）⇒ ★ 拆成早年A（eotc）＋早年B（主帳前段），各報
    ⚠ seq335「新件早年用 reduce_v2」：reduce_v2（950ad26e12）只有上市；登錄要上市＋上櫃 ⇒ 本頻率表早年用 eotc（壞根計數照 eotc），請裁定定正式跑版面
 F6 頻率表（每 世界×段×格）：批數（b 落在段內）、每批挑中產業數分佈（0／1／2／3）、A＞0 不足 K 的批數、每批成員檔數（計畫／實買）、
    每日平均同時持有檔數（不同代號）與持有筆數（代號×批）、持有 ＜ 5 檔的日數比例、平均現金比例（＋拆解：未投入份額／缺額產業／買不到／提前出場）、
    份數被現金卡住的批數、H 走得完批數（mat ≤ 資料尾；另 ≤ 日曆尾）、獨立期數 ＝ 段長 ÷ H、段內不同產業數、重複率（與上一批同產業的比例）、產業前 5 與次數、
    買不到／停止交易／硬斷點／到期順延次數；S3 另報：挑中產業平均成員數、小型股權重（★ 小型 ①＝產業內市值 20 名以外（＝ S3 比 S1 多出的部分）
    ②＝當日全體 W1 eligible 市值排名 ＞ 150（台灣 50＋中型 100 以外）③ ＞ 300）
 F7 退化（seq377、登錄 §二「平均持股 ＜ 5 檔或現金 ＞ 30%」，看探索段）：照兩讀法各標；另查 ① 某格永遠不挑（批全空）② 挑選相同：
    產業選擇只由 (A, K) 決定（S、H 只改買哪些股、抱多久）⇒ 6 條產業序列兩兩 Jaccard（批×產業）；S1 與 S3 的股票重疊（S3 權重落在 S1 名單內的比例）
    ③ 現金極端（任一段平均現金 ＞ 30% 或 ＜ 1%）
 F8 與前件挑中格（A2｜K1｜S1｜季，resultsIndRev/prereg/chosen_picks.csv）重疊：每批日 b 前件當時持有的產業 ∈ 本格挑中產業的比例（主：探索、確認；早年A 對前件早年）
    另報前件挑中產業在換股當月 A ≤ 0 的次數（前件無 A ＞ 0 道）
 F9 隨機 1,000 次框架（登錄 §四「同 K、同 H 隨機挑產業」；⛔ 本階段不算報酬）：rng ＝ default_rng([20261022, r])；每批把可排名產業（PRE.ranked "names"，
    ＝ 公司數 ≥ 5 且該 A 有限）依名稱排好後 permutation，取前 n_b 個，★ n_b ＝ 該格當批實際挑到的產業數（缺額現金一致）〔另一讀法：一律取 K〕；
    挑股、金額、持有、出場同該格。本階段報：每格 1,000 次的「與挑中格同產業比例」「段內不同產業數」，及前 RSTRUCT 次的構造量（持股、現金）分佈
 F10 全產業等權（登錄 §四對照）：每批 ＝ 全部可排名產業（★ 不論 A 正負；A 用 A1 的可排名集合）、每產業 ＝ 批 ÷ 產業數；S、H 同格；只報構造量
 F11 族群版（登錄 §二，只描述）：⚠ 族群表是事後分類；repo origin/main 只有 data/meta/sectors.csv（官方產業別），找不到族群表 ⇒ 本階段不做，報「待台股線提供族群表」
輸出 backtest/resultsIndRevHold/freq/：cells.csv、batches.csv.gz、similarity.csv、overlap_prev.csv、random_frame.csv.gz、allind.csv、daily.npz、
     A_table.csv.gz、meta.json、run.log
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import pickle
import sys
import time
from collections import Counter, defaultdict
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D                              # noqa: E402
from backtest import research11 as R                        # noqa: E402
from backtest import researchScore as SC                    # noqa: E402
from backtest import researchIndRev_prereg as PRE           # noqa: E402
from backtest import researchIndRevLag_prereg as LAGP       # noqa: E402
from backtest import researchIndMom as IMo                  # noqa: E402
from backtest import tradability as TR                      # noqa: E402

TIME = "2026-10-22 23:29（台北）"
OUT = "backtest/resultsIndRevHold/freq"
WORK = os.path.expanduser("~/indrevholdwork")
MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
REG = {"seq2": "800ad3a4bcacd7da", "seq1": "2f0f5925257a3260"}
AS = ("A1", "A2", "A3"); KS = (1, 3); HS = (250, 500, 750); SS = ("S1", "S3")
NSL = {H: int(round(H / 21)) for H in HS}
SEED = 20261022
RSTRUCT = 100
TAIL = {"main": "2026-08-24", "early": "2014-12-30"}
START = {"main": "2015-08-03", "early": "2012-06-01"}
ALT_START = "2017-03-02"
SEGS = {"main": {"早年B": ("2015-08-03", "2016-12-30"), "探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", "2026-08-24")},
        "early": {"早年A": ("2012-06-01", "2014-12-30")}}
EXCL = PRE.EXCL
INF = 10 ** 9
LOGF = None
W: dict = {}


def log(x):
    x = f"[{time.strftime('%H:%M:%S')}] {x}"
    print(x, flush=True)
    if LOGF:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(x + "\n")


def sha_of(f):
    b = open(f, "rb").read()
    return hashlib.sha256(b"\n".join(l for l in b.split(b"\n") if b"pw1 line" not in l)).hexdigest()[:16]


def reg_check():
    out = {}
    for k, sh in REG.items():
        fs = []
        for d in [MAILBOX] + sorted(glob.glob(os.path.join(MAILBOX, "_封存-*"))):
            fs += [f for f in glob.glob(os.path.join(d, "*.md")) if f"sha{sh}" in os.path.basename(f) and os.path.basename(f).startswith("登錄全文")]
        out[k] = {"sha": sh, "檔": [os.path.basename(f) for f in fs], "相符": bool(fs) and all(sha_of(f) == sh for f in fs)}
    if not out["seq2"]["相符"]:
        raise SystemExit(f"⛔ 登錄 seq2 sha 不符：{out}")
    return out


# ═════════════ A 表（F2） ═════════════
def step_A(a):
    sha = LAGP.setup(a, a.sha)
    Ms = [M for M in PRE._C["rev"].index if "2011-06" <= M and M in PRE._C["pitday"]]
    t0 = time.time()
    with Pool(a.procs) as pool:
        res = pool.map(PRE._a_month, [(M, "pit") for M in Ms], chunksize=2)
    AT = pd.concat([r[0] for r in res], ignore_index=True)
    src = Counter()
    for r in res:
        src.update(r[1])
    AT.to_csv(os.path.join(OUT, "A_table.csv.gz"), index=False, float_format="%.17g", compression={"method": "gzip", "mtime": 0})
    av = {M: str(PRE._C["avail_date"][M].date()) for M in Ms}
    json.dump({"main": sha, "月數": len(Ms), "期別": [Ms[0], Ms[-1]], "可用日": av, "PIT來源": dict(src), "秒": round(time.time() - t0)},
              open(os.path.join(OUT, "A_meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[A 表] main {sha[:10]}｜{len(Ms)} 月 {Ms[0]}～{Ms[-1]}｜{time.time() - t0:.0f}s｜2025-11 起可用日 { {M: v for M, v in av.items() if M >= '2025-11'} }")


def install_A(sha):
    AT = pd.read_csv(os.path.join(OUT, "A_table.csv.gz"), float_precision="round_trip")
    PRE._C["RANK"] = PRE.build_rank(AT)
    PRE._C["AV"] = {(v, M, i): {"A1": a1, "A2": a2, "A3": a3} for v, M, i, a1, a2, a3 in zip(AT["ver"], AT["M"], AT["產業"], AT["A1"], AT["A2"], AT["A3"])}
    am = json.load(open(os.path.join(OUT, "A_meta.json"), encoding="utf-8"))
    if am["main"] != sha:
        raise SystemExit(f"⛔ A 表 sha {am['main'][:10]} ≠ 本次 {sha[:10]}")
    return AT


# ═════════════ 逐檔旗標（F4；⛔ 無價格數值） ═════════════
_F: dict = {}


def _flag_job(args):
    sid, mk = args
    cal = _F["cal"]; n = len(cal)
    D.DATA = _F["data"]
    tb = TR.one(sid, cal)
    up = np.array(tb["up_o"], bool, copy=True); dc = np.array(tb["dn_c"], bool, copy=True)
    cnt = {"exr列": 0, "up變": 0, "dnc變": 0}
    rows = _F["tab"].get(sid)
    if rows:
        fp = os.path.join(D.DATA, "stocks", f"{sid}.csv")
        raw = pd.read_csv(fp, dtype={"date": str}, usecols=["date", "open", "close"])
        raw["date"] = pd.to_datetime(raw["date"]); raw = raw.drop_duplicates("date").set_index("date")
        ro = np.array(pd.to_numeric(raw["open"].reindex(cal), errors="coerce"), dtype=float)
        rc = np.array(pd.to_numeric(raw["close"].reindex(cal), errors="coerce"), dtype=float)
        ro[~(ro > 0)] = np.nan; rc[~(rc > 0)] = np.nan
        for d, ob in rows:
            p = int(cal.searchsorted(d))
            if p >= n or cal[p] != d or not np.isfinite(rc[p]):
                continue
            cnt["exr列"] += 1
            lim = 0.07 if cal[p] < TR.CUT else 0.10
            u = bool(np.isfinite(ro[p]) and abs(ro[p] - R.limit_price(ob, True, lim)) < 1e-6)
            w = bool(abs(rc[p] - R.limit_price(ob, False, lim)) < 1e-6)
            cnt["up變"] += int(u != up[p]); cnt["dnc變"] += int(w != dc[p])
            up[p] = u; dc[p] = w
    B = R.load_bars(sid, mk, cal)
    if B is None:
        idx = np.flatnonzero(tb["trd"])
        bad = idx[1:][(np.diff(idx) - 1) >= 5] if len(idx) > 1 else np.array([], int)
        src = "缺口規則（load_bars None）"
    else:
        nb = len(B["idx"])
        bad = np.asarray(B["idx"], int)[np.asarray(B["next_bad"][:nb]) == np.arange(nb)]
        src = "load_bars"
    return sid, {"trd": np.asarray(tb["trd"], bool), "up": up, "dc": dc, "bad": np.asarray(sorted(int(x) for x in bad), int), "src": src, "cnt": cnt}


def step_flags(a, world):
    C = LAGP.part_ctx(world, a)
    cal = C["cal"]
    lo = pd.Timestamp(START[world]) - pd.Timedelta(days=40)
    sids = sorted({s for d, v in C["memW"].items() if d >= lo for s in v if s in C["P"]})
    _F.update(cal=cal, data=C["data"], tab=IMo.load_exr_table()["tab"])
    t0 = time.time()
    with Pool(a.procs) as pool:
        FL = dict(pool.map(_flag_job, [(s, C["mk"].get(s, "twse")) for s in sids], chunksize=8))
    os.makedirs(WORK, exist_ok=True)
    pickle.dump(FL, open(os.path.join(WORK, f"flags_{world}.pkl"), "wb"), protocol=5)
    c = Counter(); src = Counter(v["src"] for v in FL.values())
    for v in FL.values():
        c.update(v["cnt"])
    log(f"[旗標 {world}] {len(FL)} 檔｜{dict(src)}｜exright {dict(c)}｜{time.time() - t0:.0f}s")


# ═════════════ 世界 ═════════════
def load_world(world, a):
    C = LAGP.part_ctx(world, a); PRE.attach_months(C)
    FL = pickle.load(open(os.path.join(WORK, f"flags_{world}.pkl"), "rb"))
    cal = C["cal"]; T = SC.pos_of(cal, TAIL[world])
    SFd = R.stop_force_days({s: v["valid"] for s, v in C["P"].items()}, T)
    ok_open = {s: (np.isfinite(v["o"]) & (v["o"] > 0)) for s, v in C["P"].items()}   # ⛔ 只取「開盤是否有效」布林
    return {"C": C, "FL": FL, "T": T, "SF": SFd, "okopen": ok_open, "cal": cal}


def batch_days(Wd, start):
    C = Wd["C"]; a0 = int(Wd["cal"].searchsorted(pd.Timestamp(start)))
    out = []
    for p, M in sorted(C["availday"].items()):
        b = p + 1
        if a0 <= b <= Wd["T"]:
            assert C["Mlast"][b] == M and PRE._C["avail_date"][M] < Wd["cal"][b], (b, M)
            out.append((b, M))
    return out


def members_full(Wd, b):
    """PRE.picks_at 同一套分組（F3），但回全部成員（S3 用）；S1 ＝ 前 20 逐批對 PRE.picks_at。"""
    C = Wd["C"]; d = C["cal"][b - 1]
    grp = defaultdict(list)
    for s in PRE.elig_at(C, b, "W1"):
        if s not in C["P"]:
            continue
        ind, _ = PRE._C["PIT"].at(s, d, "pit")
        if ind is None or ind in EXCL:
            continue
        mc = C["MC"][s][b - 1]
        if not (np.isfinite(mc) and mc > 0):
            continue
        grp[ind].append((-mc, s))
    out = {i: [s for _, s in sorted(v)] for i, v in grp.items()}
    pk = PRE.picks_at(C, "pit", "W1", b)
    assert set(pk) == set(out) and all(pk[i]["S1"] == out[i][:20] for i in out), b
    # 全體 W1 eligible 市值排名（小型股用；不分產業、含金融）
    allmc = sorted(((-C["MC"][s][b - 1], s) for s in PRE.elig_at(C, b, "W1") if s in C["P"] and np.isfinite(C["MC"][s][b - 1]) and C["MC"][s][b - 1] > 0))
    rank = {s: k + 1 for k, (_, s) in enumerate(allmc)}
    return out, rank


def pick_inds(A, K, M):
    rk = PRE.ranked("pit", A, M, "top")
    pos = [i for i in rk if PRE.a_val("pit", M, i, A) > 0]
    return pos[:K], len(rk), len(pos)


def lot_exit(Wd, s, b, mat):
    """⇒ (出場位置 或 None（未買）, 原因)。出場位置 e：持有 [b, e−1]；e ＝ T＋1 ⇒ 持有到資料尾未出場。"""
    T = Wd["T"]; f = Wd["FL"].get(s)
    if f is None:
        return None, "無旗標"
    trd, up, dc, bad = f["trd"], f["up"], f["dc"], f["bad"]
    if not trd[b] or not Wd["okopen"][s][b]:
        return None, "停牌買不到"
    if up[b]:
        return None, "漲停買不到"
    k = int(np.searchsorted(bad, b, "left"))
    if k < len(bad) and bad[k] == b:
        return None, "壞根日不買"
    end = min(mat, T)
    cand = []
    k = int(np.searchsorted(bad, b, "right"))
    if k < len(bad) and bad[k] <= end:
        kb = int(bad[k]); tt = np.flatnonzero(trd[b:kb]); q = b + int(tt[-1])
        cand.append((q, "硬斷點"))
    L = Wd["SF"].get(s)
    if L is not None and L >= b and L + 1 <= end:
        cand.append((L + 1, "停止交易"))
    if cand:
        return min(cand)
    if mat > T:
        return T + 1, "走不完"
    q = mat
    while q <= T and not (trd[q] and not dc[q]):
        q += 1
    if q > T:
        return T + 1, "到期賣不掉至資料尾"
    return q, ("到期" if q == mat else "到期順延")


def sim_cell(Wd, BL, picks, K, S, H, divK=None):
    """乾跑分批帳（F3、F4）。picks[j] ＝ 第 j 批挑中產業。divK ＝ 每產業份額除數（預設 K；全產業 ＝ 當批產業數）。"""
    T = Wd["T"]; n = len(Wd["cal"]); nsl = NSL[H]; sl = 1.0 / nsl
    sidx = Wd["sidx"]
    rel = []   # (回收位置, 金額)
    L_s, L_a, L_e, L_m = [], [], [], []
    cnt = Counter(); binfo = []
    dinv = np.zeros(n + 2); dslot = np.zeros(n + 2)
    for j, (b, M) in enumerate(BL):
        occ = sum(x for r, x in rel if r >= b)
        Aj = min(sl, max(1.0 - occ, 0.0))
        if Aj < sl - 1e-12:
            cnt["份數被現金卡住"] += 1
        mem, rank = Wd["MEM"][b]
        inds = picks[j]; dk = (divK[j] if divK is not None else K)
        mat = b + H - 1; release = mat if mat <= T else INF
        n_plan = n_buy = 0; w_out20 = w_r150 = w_r300 = 0.0; w_tot = 0.0; nmem = []
        for i in inds:
            lst = mem.get(i, [])
            nmem.append(len(lst))
            lst = lst[:20] if S == "S1" else lst
            if not lst:
                cnt["產業0檔"] += 1; continue
            per = Aj / dk / len(lst)
            for r_, s in enumerate(lst):
                n_plan += 1; w_tot += per
                w_out20 += per * (r_ >= 20); w_r150 += per * (rank.get(s, INF) > 150); w_r300 += per * (rank.get(s, INF) > 300)
                e, why = lot_exit(Wd, s, b, mat)
                cnt[why] += 1
                if e is None:
                    continue
                n_buy += 1
                L_s.append(sidx[s]); L_a.append(b); L_e.append(e); L_m.append(per)
                if e > mat:
                    release = INF if e > T else max(release, e)
        rel.append((release, Aj))
        # 份額占用（日）：[b, release]（release 收盤賣完 ⇒ 該日收盤後不再占用）
        r_end = min(release, T + 1) if release != INF else T + 1
        dslot[b] += Aj; dslot[r_end] -= Aj
        binfo.append({"b": b, "M": M, "n_ind": len(inds), "Aj": Aj, "n_plan": n_plan, "n_buy": n_buy, "成員數": nmem,
                      "w_out20": w_out20 / w_tot if w_tot else np.nan, "w_r150": w_r150 / w_tot if w_tot else np.nan,
                      "w_r300": w_r300 / w_tot if w_tot else np.nan, "mat": mat, "完": int(mat <= T)})
    L_s = np.asarray(L_s, int); L_a = np.asarray(L_a, int); L_e = np.asarray(L_e, int); L_m = np.asarray(L_m, float)
    np.add.at(dinv, L_a, L_m); np.add.at(dinv, L_e, -L_m)
    inv = np.cumsum(dinv)[:n]; slot = np.cumsum(dslot)[:n]
    dl_ = np.zeros(n + 2); np.add.at(dl_, L_a, 1); np.add.at(dl_, L_e, -1); lots = np.cumsum(dl_)[:n]
    M2 = np.zeros((len(sidx), n + 2), np.int32)
    np.add.at(M2, (L_s, L_a), 1); np.add.at(M2, (L_s, L_e), -1)
    distinct = (np.cumsum(M2, axis=1)[:, :n] > 0).sum(0)
    return {"inv": inv, "slot": slot, "lots": lots, "distinct": distinct, "cnt": cnt, "binfo": binfo}


def seg_stats(Wd, res, BL, picks, H, a_, z_):
    T = Wd["T"]; z_ = min(z_, T)
    cash = 1.0 - res["inv"][a_:z_ + 1]; idle = 1.0 - res["slot"][a_:z_ + 1]
    dist = res["distinct"][a_:z_ + 1]
    js = [j for j, (b, _) in enumerate(BL) if a_ <= b <= z_]
    bi = [res["binfo"][j] for j in js]
    ninds = Counter(x["n_ind"] for x in bi)
    seq = [picks[j] for j in js]
    rep = [len(set(seq[k]) & set(seq[k - 1])) / len(seq[k]) for k in range(1, len(seq)) if seq[k]]
    cnt_ind = Counter(i for p in seq for i in p)
    calT2 = len(Wd["cal"]) - 1
    return {"批數": len(js), "挑中產業數分佈": dict(sorted(ninds.items())), "空批（0 產業）": ninds.get(0, 0),
            "每批計畫檔數平均": float(np.mean([x["n_plan"] for x in bi])) if bi else np.nan,
            "每批實買檔數平均": float(np.mean([x["n_buy"] for x in bi])) if bi else np.nan,
            "每批實買檔數最少": int(min([x["n_buy"] for x in bi])) if bi else np.nan,
            "平均持股（不同代號）": float(dist.mean()), "持股最少": int(dist.min()), "持股<5日數比例": float((dist < 5).mean()),
            "平均持有筆數": float(res["lots"][a_:z_ + 1].mean()),
            "平均現金比例": float(cash.mean()), "現金_未投入份額": float(idle.mean()), "現金_份內（缺額產業、買不到、提前出場）": float((cash - idle).mean()),
            "現金最高": float(cash.max()),
            f"H走得完批數（≤{TAIL[Wd['name']]}）": int(sum(x["完"] for x in bi)),
            "H走得完批數（≤日曆尾）": int(sum(1 for x in bi if x["mat"] <= calT2)),
            "段內走得完批數（mat ≤ 段尾）": int(sum(1 for x in bi if x["mat"] <= z_)),
            "獨立期數（段長÷H）": round((z_ - a_ + 1) / H, 2),
            "段內不同產業數": len(cnt_ind), "重複率（與上一批同產業）": float(np.mean(rep)) if rep else np.nan,
            "產業前5": "｜".join(f"{k}{v}" for k, v in cnt_ind.most_common(5)),
            "挑中產業平均成員數": float(np.mean([m for x in bi for m in x["成員數"]])) if bi and any(x["成員數"] for x in bi) else np.nan,
            "小型權重_產業20名外": float(np.nanmean([x["w_out20"] for x in bi])) if bi else np.nan,
            "小型權重_全體排名>150": float(np.nanmean([x["w_r150"] for x in bi])) if bi else np.nan,
            "小型權重_全體排名>300": float(np.nanmean([x["w_r300"] for x in bi])) if bi else np.nan}


def segp(Wd):
    cal = Wd["cal"]
    return {k: (int(cal.searchsorted(pd.Timestamp(x))), int(cal.searchsorted(pd.Timestamp(y), "right") - 1)) for k, (x, y) in SEGS[Wd["name"]].items()}


def _cell_job(args):
    world, reading, A, K, S, H = args
    Wd = W[world]; BL = Wd["BL"][reading]; picks = Wd["PK"][reading][(A, K)]
    res = sim_cell(Wd, BL, picks, K, S, H)
    rows = []
    for sg, (a_, z_) in segp(Wd).items():
        if BL and z_ < BL[0][0]:
            continue
        rows.append({"世界": world, "讀法": reading, "段": sg, "A": A, "K": K, "S": S, "H": H, **seg_stats(Wd, res, BL, picks, H, a_, z_)})
    return rows, dict(res["cnt"]), (res["distinct"].astype(np.int16), (1.0 - res["inv"]).astype(np.float32)), [
        {"世界": world, "讀法": reading, "A": A, "K": K, "S": S, "H": H, "批日": str(Wd["cal"][x["b"]].date()), "營收月": x["M"], "產業": "｜".join(picks[j]),
         "產業數": x["n_ind"], "份額": x["Aj"], "計畫檔數": x["n_plan"], "實買檔數": x["n_buy"], "成員數": "/".join(map(str, x["成員數"])),
         "小型_20名外": x["w_out20"], "小型_>150": x["w_r150"], "到期": str(Wd["cal"][x["mat"]].date()) if x["mat"] < len(Wd["cal"]) else "曆外"}
        for j, x in enumerate(res["binfo"])]


def prep_world(world, a):
    Wd = load_world(world, a); Wd["name"] = world
    C = Wd["C"]
    allS = sorted(Wd["FL"]); Wd["sidx"] = {s: k for k, s in enumerate(allS)}
    starts = {"主讀法": START[world]} if world == "early" else {"主讀法": START[world], "讀法乙": ALT_START}
    Wd["BL"] = {r: batch_days(Wd, st) for r, st in starts.items()}
    Wd["MEM"] = {}
    for b, _ in Wd["BL"]["主讀法"]:
        Wd["MEM"][b] = members_full(Wd, b)
    Wd["PK"] = {}; Wd["PKinfo"] = []
    for r, BL in Wd["BL"].items():
        Wd["PK"][r] = {}
        for A in AS:
            for K in KS:
                ps = []
                for b, M in BL:
                    p, nr, npos = pick_inds(A, K, M); ps.append(p)
                    if r == "主讀法":
                        Wd["PKinfo"].append({"世界": world, "A": A, "K": K, "批日": str(C["cal"][b].date()), "營收月": M, "可排名產業數": nr, "A>0產業數": npos,
                                             "挑中": "｜".join(p), "A值": "｜".join(f"{PRE.a_val('pit', M, i, A):.4f}" for i in p)})
                Wd["PK"][r][(A, K)] = ps
    W[world] = Wd
    nmiss = sum(1 for b, _ in Wd["BL"]["主讀法"] for v in Wd["MEM"][b][0].values() for s in v if s not in Wd["FL"])
    log(f"[{world}] 批 主讀法 {len(Wd['BL']['主讀法'])}（{Wd['cal'][Wd['BL']['主讀法'][0][0]].date()}～{Wd['cal'][Wd['BL']['主讀法'][-1][0]].date()}）"
        + (f"｜讀法乙 {len(Wd['BL']['讀法乙'])}" if "讀法乙" in Wd["BL"] else "") + f"｜資料尾 {Wd['cal'][Wd['T']].date()}｜無旗標成員 {nmiss}")
    return Wd


def jacc(x, y):
    a_ = {(j, i) for j, p in enumerate(x) for i in p}; b_ = {(j, i) for j, p in enumerate(y) for i in p}
    return len(a_ & b_) / len(a_ | b_) if (a_ | b_) else np.nan


def prev_overlap(Wd):
    """F8：前件挑中格（A2|K1|S1|季）每批日當時持有的產業 ∈ 本格挑中產業的比例。"""
    cp = pd.read_csv(os.path.join(PRE.OUT, "chosen_picks.csv"), dtype=str)
    cp = cp[cp["段"].isin(["早年"] if Wd["name"] == "early" else ["探索", "確認"])]
    days = sorted(set(cp["換股日"])); ind_at = {d: g.sort_values("名次")["產業"].tolist() for d, g in cp.groupby("換股日")}
    Aneg = int(sum(1 for _, r in cp.iterrows() if not (float(r["A"]) > 0)))
    rows = []
    BL = Wd["BL"]["主讀法"]
    for (A, K), ps in Wd["PK"]["主讀法"].items():
        for sg, (a_, z_) in segp(Wd).items():
            hit = tot = emp = 0
            for (b, M), p in zip(BL, ps):
                if not (a_ <= b <= z_):
                    continue
                ds = str(Wd["cal"][b].date()); k = [d for d in days if d <= ds]
                if not k:
                    continue
                prev = ind_at[k[-1]]
                tot += 1; hit += int(any(i in p for i in prev)); emp += int(not p)
            if tot:
                rows.append({"世界": Wd["name"], "段": sg, "A": A, "K": K, "比對批數": tot, "前件產業∈本格挑中": hit / tot, "本格空批": emp})
    return rows, {"前件換股次數": len(days), "前件挑中產業當月A≤0次數": Aneg}


def step_freq(a):
    global LOGF
    LOGF = os.path.join(OUT, "run.log")
    REGI = reg_check()
    sha = LAGP.setup(a, a.sha or json.load(open(os.path.join(OUT, "A_meta.json"), encoding="utf-8"))["main"])
    install_A(sha)
    log(f"===== researchIndRevHold_freq｜讀法寫死 {TIME}｜main {sha[:10]}｜登錄 {json.dumps({k: v['相符'] for k, v in REGI.items()}, ensure_ascii=False)} =====")
    META = {"讀法寫死": TIME, "main": sha, "登錄": REGI, "份數": NSL, "資料尾": TAIL, "帳起點": START, "讀法乙主帳起點": ALT_START,
            "價格版面": {}, "⛔": "不含任何報酬；乾跑 R 全 0"}
    rows, cnts, daily, bat, sim, ovl, allind = [], {}, {}, [], [], [], []
    for world in ("main", "early"):
        Wd = prep_world(world, a)
        META["價格版面"][world] = {"data": Wd["C"]["data"], "info": Wd["C"]["info"]}
        jobs = [(world, r, A, K, S, H) for r in Wd["BL"] for A in AS for K in KS for S in SS for H in HS]
        t0 = time.time()
        with Pool(a.procs) as pool:
            res = pool.map(_cell_job, jobs, chunksize=1)
        for jb, (rr, cn, dd, bb) in zip(jobs, res):
            rows += rr; cnts["|".join(map(str, jb))] = cn
            daily["|".join(map(str, jb))] = dd
            if jb[1] == "主讀法":
                bat += bb
        log(f"[{world}] {len(jobs)} 格×讀法｜{time.time() - t0:.0f}s")
        # 相似度（F7 ②）
        PK = Wd["PK"]["主讀法"]; ks = list(PK)
        for x in range(len(ks)):
            for y in range(x + 1, len(ks)):
                if ks[x][1] == ks[y][1]:
                    sim.append({"世界": world, "格1": f"{ks[x][0]}|K{ks[x][1]}", "格2": f"{ks[y][0]}|K{ks[y][1]}", "Jaccard（批×產業）": jacc(PK[ks[x]], PK[ks[y]])})
        o, oi = prev_overlap(Wd); ovl += o; META[f"前件_{world}"] = oi
        # 全產業等權（F10）
        BL = Wd["BL"]["主讀法"]
        allp = [PRE.ranked("pit", "A1", M, "names") for b, M in BL]
        for S in SS:
            for H in HS:
                r_ = sim_cell(Wd, BL, allp, None, S, H, divK=[max(len(p), 1) for p in allp])
                for sg, (a_, z_) in segp(Wd).items():
                    allind.append({"世界": world, "段": sg, "S": S, "H": H, **seg_stats(Wd, r_, BL, allp, H, a_, z_)})
        pd.DataFrame(Wd["PKinfo"]).to_csv(os.path.join(OUT, f"picks_{world}.csv"), index=False)
        W.pop(world)
    T = pd.DataFrame(rows)
    # 退化（F7）
    ex = T[T["段"] == "探索"].set_index(["讀法", "A", "K", "S", "H"])
    T["退化（探索：持股<5 或 現金>30%）"] = [bool(ex.loc[(r, A, K, S, H), "平均持股（不同代號）"] < 5 or ex.loc[(r, A, K, S, H), "平均現金比例"] > 0.30)
                                       if (w == "main" and (r, A, K, S, H) in ex.index) else None
                                       for w, r, A, K, S, H in zip(T["世界"], T["讀法"], T["A"], T["K"], T["S"], T["H"])]
    T.to_csv(os.path.join(OUT, "cells.csv"), index=False, float_format="%.6g")
    pd.DataFrame(bat).to_csv(os.path.join(OUT, "batches.csv.gz"), index=False, float_format="%.6g", compression={"method": "gzip", "mtime": 0})
    pd.DataFrame(sim).to_csv(os.path.join(OUT, "similarity.csv"), index=False, float_format="%.6g")
    pd.DataFrame(ovl).to_csv(os.path.join(OUT, "overlap_prev.csv"), index=False, float_format="%.6g")
    pd.DataFrame(allind).to_csv(os.path.join(OUT, "allind.csv"), index=False, float_format="%.6g")
    np.savez_compressed(os.path.join(OUT, "daily.npz"), **{k.replace("|", "__"): np.vstack([v[0].astype(np.float32), v[1]]) for k, v in daily.items()})
    META["計數"] = cnts
    tot = Counter()
    for k, v in cnts.items():
        if "|主讀法|" in k:
            tot.update(v)
    META["計數合計（主讀法、全部格）"] = dict(tot)
    json.dump(META, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] 計數合計 {dict(tot)}")


# ═════════════ 隨機框架（F9；⛔ 無報酬） ═════════════
def _rand_job(args):
    world, A, K, S, H, r0, r1 = args
    Wd = W[world]; BL = Wd["BL"]["主讀法"]; mine = Wd["PK"]["主讀法"][(A, K)]
    names = Wd["NAMES"][A]
    out = []
    sp = segp(Wd)
    for r in range(r0, r1):
        rng = np.random.default_rng([SEED, r])
        ps = []
        for j, (b, M) in enumerate(BL):
            nm = names[j]; nb = len(mine[j])
            ps.append([nm[k] for k in rng.permutation(len(nm))][:nb] if nm else [])
        row = {"世界": world, "A": A, "K": K, "S": S, "H": H, "r": r}
        for sg, (a_, z_) in sp.items():
            js = [j for j, (b, _) in enumerate(BL) if a_ <= b <= z_]
            sl = [(j, i) for j in js for i in mine[j]]
            row[f"{sg}_同產業比例"] = (sum(1 for j, i in sl if i in ps[j]) / len(sl)) if sl else np.nan
            row[f"{sg}_不同產業數"] = len({i for j in js for i in ps[j]})
        if r < RSTRUCT:
            res = sim_cell(Wd, BL, ps, K, S, H)
            for sg, (a_, z_) in sp.items():
                z2 = min(z_, Wd["T"])
                row[f"{sg}_平均持股"] = float(res["distinct"][a_:z2 + 1].mean()); row[f"{sg}_平均現金"] = float((1 - res["inv"][a_:z2 + 1]).mean())
        out.append(row)
    return out


def step_rand(a):
    global LOGF
    LOGF = os.path.join(OUT, "run.log")
    sha = LAGP.setup(a, a.sha or json.load(open(os.path.join(OUT, "A_meta.json"), encoding="utf-8"))["main"]); install_A(sha)
    allrows = []
    for world in ("main", "early"):
        Wd = prep_world(world, a)
        Wd["BL"] = {"主讀法": Wd["BL"]["主讀法"]}
        Wd["NAMES"] = {A: [PRE.ranked("pit", A, M, "names") for b, M in Wd["BL"]["主讀法"]] for A in AS}
        W[world] = Wd
        t0 = time.time()
        jobs = [(world, A, K, S, H, r0, min(r0 + 250, a.reps)) for A in AS for K in KS for S in SS for H in HS for r0 in range(0, a.reps, 250)]
        with Pool(a.procs) as pool:
            for rr in pool.imap_unordered(_rand_job, jobs):
                allrows += rr
        log(f"[隨機 {world}] {len(jobs)} 工作｜{time.time() - t0:.0f}s")
        W.pop(world)
    RD = pd.DataFrame(allrows).sort_values(["世界", "A", "K", "S", "H", "r"])
    RD.to_csv(os.path.join(OUT, "random_frame.csv.gz"), index=False, float_format="%.6g", compression={"method": "gzip", "mtime": 0})
    log(f"[隨機] {len(RD)} 列｜seed [{SEED}, r]｜構造量前 {RSTRUCT} 次")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", required=True, choices=["A", "flags_main", "flags_early", "freq", "rand"])
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--reps", type=int, default=1000)
    ap.add_argument("--sha", default=None)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    if a.step == "A":
        reg_check(); step_A(a)
    elif a.step.startswith("flags_"):
        step_flags(a, a.step[6:])
    elif a.step == "freq":
        step_freq(a)
    else:
        step_rand(a)


if __name__ == "__main__":
    main()
