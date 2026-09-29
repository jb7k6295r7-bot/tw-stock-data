# -*- coding: utf-8 -*-
"""PREREG飆股回推 seq6（近年版）——回測線（子代理執行）。

    查核沿用：cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchSurge6 --stage prep
    建事件：   ... --stage events [--procs 2]                    （只重建 2021 起的起漲事件；不算任何提升倍數）
    分析：     ... --stage desc|feat|endtrade|report --sha <seq6 sha> [--start "YYYY-MM-DD HH:MM"]
               （⛔ 沒有 --sha 或 sha 對不上信箱登錄全文 ⇒ 拒跑）
    獨立查核： ~/tw-p16/.venv/bin/python backtest/researchSurge6_check.py

═══ 讀法（U 標；⭐ 寫死於 2026-09-29 18:45（台北），在收到 seq6 sha 之前、未跑任何會算出提升倍數的分析之前）═══
 U0 執行者：回測線子代理；執行者未看過 seq4、seq5 結果（resultsSurge5/、resultsSurge/_seq4_seen/、resultsSurge/ 的 REPORT／csv／html、
    /tmp 下 surge log、信箱「飆股回推seq5交件／第一批／第二批」與「飆股seq5收下」皆未開）。
    讀過的：seq5 登錄全文（sha 90ecf06e7f3d906a）、裁定 seq276／277／278、researchSurge5*.py 程式碼、surge_features.py、resultsSurge/HANDOFF.md；
    裁定 seq279 §三 規格由回測線 session 轉抄（原信未讀）。
 U1 規格：seq6 ＝ seq5（§十 ＋ 裁定 seq277 g 網格）只改資料期間（裁定 seq279 §三）：
    探索段 2021-01～2023-12、確認段 2024-01～2026-08；⛔ 不用 2017～2020、⛔ 不用早年段 2005～2014（⇒ seq5 S12 的「早年照驗」與早年欄一律不做）
 U2 其餘全部照 seq5 讀法 S1～S19（見 researchSurge5.py 開頭，逐條沿用、不改）：
    列＝觀察日×股（S1）；母體＝上市櫃普通股、含下市／注意／處置／停牌前後、⛔ 不用 W1 閘（S2）；壞根＝幽靈還原＋價格斷點（S3）；
    定義域（S4）；事件不重算（S5）；g ∈ {50,100,150,200,250,300,400,500,700,1000%}（1000% 即「≥1000%」）× H ∈ {10,…,250} ⇒ 250 格（S6）；
    P、P*（S7）；回落（S8）；特徵回看 5／10／20／60／120／250、門檻型改連續值五等分、原門檻版只描述（S9）；五等分（S10）；
    ①②（S11）；挑選：探索段 250 格中 ≥ 125 格「① 95% 下緣 ＞ 1 且 ② ≥ 5%」⇒ 全部進確認段；確認段 ≥ 125 格「① Bonferroni（k＝進確認段數）下緣 ＞ 1」⇒ 站得住（S12）；
    ③ 成本 0.585%、對全體與基準② 5～250 日（S13）；買不買得到（S14）；妖股（S15）；結束特徵（S16）；N（S17）；最短花幾天（S18）；結束可交易（S19）
 U3 特徵與 s5work 沿用：F／Q／R／bar／hdef／buy_ok／locked／disp／r20c 直接讀 ~/s5work（seq5 build＋cross 產物，全日曆算）；
    ⭐ 沿用前先過 --stage prep：抽樣重跑 researchSurge5.stock() 逐位元對 F（非橫斷面欄）／R／hdef／bar／buy_ok／locked／disp／r20c，
    抽日重算五等分對 Q，母體對 gate3 ⇒ 不過就不沿用（改重建）
    暖機：特徵回看窗可取 2021 以前價量（最長：bbw_L 需 L＋250 根、均線排列需 251 根、大盤時序五等分需前 750 日、集保 2019 起）——只是特徵定義，⛔ 不產生任何 2021 以前的起漲事件
 U4 事件（起漲日）只取 2021-01-01～2026-08-31 的觀察日 t；「同一檔同一格事件後 H 日內不重算」的鏈 ⭐ 從 2021 第一個交易日重新起算（2020 的事件不壓 2021 的事件；
    因為 seq5 的鏈是全日曆連續的，這裡不能直接篩 seq5 的 events.npz ⇒ 以 seq5 同一段程式邏輯重建，只加起點限制）；探索／確認交界不重起（同 seq5：鏈跨段連續）
    被跳過的日子仍在分母、標籤 0（S5 不變）；標籤窗 (t, t＋H] 照 S4 可延到資料尾 2026-09-24（同 seq5）；月分群依 t 的月份
 U5 分母：只取兩段內（2021-01～2026-08）有 K 棒的股-日；③ 的基準② 十分位、對全體平均都是同日橫斷面，只在段內日子算
 U6 Bonferroni：各族用自己的 k（飆股族 k＝進確認段級距數；妖股 30／50／70 各一族；結束 3×5 各一族；結束可交易 k＝站得住的不同結束級距數），另報總 N
 U7 ③ 曲線：淨報酬曲線 ＝ 超額 − 0.585%，「對全體」「對基準②」各一條（確認段 CI 用 Bonferroni z）；「買了賺」＝ 對基準② 下緣 − 0.585% ＞ 0 連續 ≥ 3 格（同 seq5）
 U8 揭露（逐字進報告）：「2022～2026 的整體結果已看過（seq5 站得住 0）⇒ 本件是事後重切」；挑選照規則機械化執行，不因已知結果而改。
    執行者自己沒看過任何 seq4／seq5 細部數字；上面那句是回測線轉達的揭露，不是執行者查到的
 U9 輸出 backtest/resultsSurge6/；工作檔 ~/s6work/（只有重建的 events.npz 與 events.json）
 U10 網格「樣本少」標記（裁定 seq277：照報、不併格）＝ 該段該格事件 ＜ 30；只標記，⛔ 不影響挑選與判定
 U11 sha 驗法同 seq5：登錄全文去掉含「pw1 line」那一行後 sha256 前 16 碼；分析階段（desc／feat／endtrade／report）沒有對上的 sha 一律拒跑

═══ 補寫（2026-09-29 18:53（台北）；收到 seq6 sha a5cbd8c8abb55a68 與協調者轉述之後、跑任何會算出提升倍數的分析之前）═══
 ⚠ seq6 登錄全文（sha a5cbd8c8abb55a68）沿革列寫「加 §十一」，但檔內正文只到 §十之七，沒有 §十一 ⇒ §十一 的內容以裁定 seq279 §三（協調者轉抄）與協調者轉述為準，照實記
 U4b 右截斷（協調者轉述登錄 §十一，⭐ 取代 U4 的「標籤窗可延到 2026-09-24」）：資料尾視為 2026-08-31（最後一個交易日）⇒
    定義域 hdef6 ＝ min(seq5 hdef, 2026-08-31 的索引 − t)；t＋H 超過 2026-08-31 的列不進該 H 格（分母、事件都不進）；
    同一條尾巴套到 ③ 報酬（R_h 要 t＋h ≤ 2026-08-31）、P 後回落觀察期、P*、250 日內最大漲幅、結束可交易；各段各格照實報「實際起漲日區間」與「定義域最後起漲日」
 U12 §九之一 量縮描述（⛔ 不判、不計 N；台股要求，協調者轉達）：
    量縮狀態 ＝ seq5 的 d_shrink 欄：20 日均額 ≤ 「該 20 日窗之前的 120 日均額」× 0.7（登錄「前 120 日均額」讀成緊接在 20 日窗之前的 120 日；本件的讀法），只在有 K 棒的日子有值
    D1：起漲日 t 前 60 個交易日（日曆交易日 t−59～t，含 t）內曾在量縮狀態的比例、t 當日在量縮的比例；
        對象 ＝ F1（H60 g100%）、F2（H20 g50%）、F3（H120 g200%）的事件、F1 的妖股（P 後回落 ≥ 50%）、全體母體股-日（t 當日量縮有值者）；分探索／確認／全期
    D2：F1 事件：往回最多 250 根 K 棒找最後一段量縮（連續有 K 棒日皆量縮）⇒ 持續根數、量縮最後一天到 t 隔幾根（t 當日仍量縮 ＝ 0）；中位、p25～p75；找不到的比例照報
    D3：進入量縮日 e ＝ 當根量縮、前一根 K 棒不量縮；只取 e 在 2021-01～2026-08 且 e＋250＋60 ≤ 2026-08-31（250 日內起漲的 F1 事件都要能完整判定）且 seq5 hdef[e] ≥ 250（窗內無壞根）；
        「變成飆股」＝ [e, e＋250] 內有 F1 事件的起漲日 ⇒ 比例、等幾天（第一個起漲日 − e，交易日；中位、p25～p75、平均）；
        沒變飆股者：e 收盤 → e＋250 收盤（還原、ffill）報酬 − 0050 同期報酬 ⇒ 平均、中位、月分群 95% CI（依 e 的月份）、落後 0050 的比例；分段依 e 的月份
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import html
import json
import os
import sys
import time
from multiprocessing import Pool
from statistics import NormalDist

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchSurge5 as S5              # 常數、特徵清單、stock()（只供 prep 查核）、qtie
from backtest import researchSurge5_feat as FT          # levels()、ratio_stats()
from backtest import researchSurge5_desc as DS          # defined_counts、qs、fastest、BUCK
from backtest import avgdown as AV

D = S5.D
READ_FIXED = "2026-09-29 18:45（台北）"
WORK5 = S5.WORK
WORK6 = os.environ.get("S6WORK", os.path.expanduser("~/s6work"))
OUT = "backtest/resultsSurge6"
MAILBOX = "/mnt/c/SynologyDrive/跨線信箱"
SEG = {"探索": ("2021-01", "2023-12"), "確認": ("2024-01", "2026-08")}
EV_FROM, EV_TO = "2021-01-01", "2026-08-31"
HS, GS, NC, HOLD, DD, KEND, COST = S5.HS, S5.GS, S5.NC, S5.HOLD, S5.DD, S5.KEND, S5.COST
HALF = NC // 2
Z95 = FT.Z95
CODES = 7
DISCLOSE = "2022～2026 的整體結果已看過（seq5 站得住 0）⇒ 本件是事後重切"
NOSEEN = "執行者未看過 seq4、seq5 結果"
_G: dict = {}


def pm(s):
    p = pd.Period(s)
    return p.year * 12 + p.month - 1


# ═════════════ sha 閘 ═════════════
def reg_sha(path):
    """同 seq5 的驗法：去掉含「pw1 line」的那一行，其餘逐行（每行補 \\n）sha256 取前 16。"""
    data = open(path, "rb").read()
    keep = [ln if ln.endswith(b"\n") else ln + b"\n" for ln in data.splitlines(keepends=True) if b"pw1 line" not in ln]
    return hashlib.sha256(b"".join(keep)).hexdigest()[:16]


def find_seq6(sha):
    fs = [f for f in glob.glob(os.path.join(MAILBOX, "**", "*.md"), recursive=True)
          if os.path.basename(f).startswith("登錄全文-") and "飆股" in os.path.basename(f) and "_seq6_" in os.path.basename(f) and "_封存" not in f]
    hit = [(f, reg_sha(f)) for f in fs]
    ok = [f for f, s in hit if s == sha]
    return ok, hit


def gate(a):
    if not a.sha:
        sys.exit("⛔ 沒有 --sha：分析階段要先收到 seq6 登錄 sha")
    ok, hit = find_seq6(a.sha)
    if not ok:
        sys.exit(f"⛔ 信箱找不到 sha＝{a.sha} 的 seq6 登錄全文（找到：{[(os.path.basename(f), s) for f, s in hit]}）")
    os.makedirs(OUT, exist_ok=True)
    fp = os.path.join(OUT, "START.json")
    if os.path.exists(fp):
        st = json.load(open(fp, encoding="utf-8"))
        if st["seq6_sha"] != a.sha:
            sys.exit(f"⛔ START.json 的 sha {st['seq6_sha']} ≠ {a.sha}")
    else:
        if not a.start:
            sys.exit("⛔ 第一個分析階段要給 --start（分析開始時間，台北）")
        st = {"分析開始": f"{a.start}（台北）", "seq6_sha": a.sha, "seq6_登錄檔": os.path.basename(ok[0]), "讀法寫死": READ_FIXED}
        json.dump(st, open(fp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return st


# ═════════════ 事件（U4）═════════════
def _init(W):
    D.DATA = S5.ST; _G.clear(); _G.update(W)


def ev_stock(args):
    """與 researchSurge5.stock() 的壞根、定義域、事件、事件屬性段落同一邏輯（逐行照抄），只加「t 在 [t0, t1]」與鏈的起點。"""
    si, sid, mk = args
    W = _G; cal = W["cal"]; n = len(cal); t0, t1 = W["t0"], W["t1"]
    st = D.load_stock(sid, mk, cal)
    if st is None:
        return si, None
    df = st.df
    cA = df["close"].to_numpy(float)
    idx = np.flatnonzero(np.isfinite(cA)); m = len(idx)
    if m < 2:
        return si, None
    raw = pd.read_csv(os.path.join(S5.ST, "stocks", sid + ".csv"), dtype={"date": str}, usecols=["date", "close"]).drop_duplicates("date")
    raw.index = pd.to_datetime(raw["date"]); raw = raw.reindex(cal)
    rcl = np.array(pd.to_numeric(raw["close"], errors="coerce"), dtype=float); rcl[~(rcl > 0)] = np.nan
    rc = rcl[idx]; c = cA[idx]; dates = cal[idx]
    adj = D.load_adj(sid)
    bad_k = np.zeros(m, bool)
    if adj is not None and len(adj):
        for d, f in zip(adj["date"], adj["factor"].astype(float)):
            k = int(np.searchsorted(dates, d))
            if k >= m:
                continue
            if k > 0 and np.isfinite(rc[k]) and np.isfinite(rc[k - 1]) and f > 0:
                r = rc[k] / (rc[k - 1] * f)
                if r < 0.895 or r > 1.105:
                    bad_k[k] = True
    for b in D.breakpoints(df, st.event_dates):
        if b["rule"] in ("price", "price+gap"):
            k = int(np.searchsorted(idx, b["pos"]))
            if k < m:
                bad_k[k] = True
    bad_day = np.zeros(n + 1, bool); bad_day[idx[bad_k]] = True
    nxt = np.full(n + 2, 10 ** 9)
    for p in range(n - 1, -1, -1):
        nxt[p] = p if bad_day[p] else nxt[p + 1]
    cff = pd.Series(cA).ffill().to_numpy()
    last = int(idx[-1])
    hdef = np.zeros(n, np.int16)
    pp = idx
    hd = np.minimum.reduce([np.full(m, 250), n - 1 - pp, nxt[np.minimum(pp + 1, n)] - 1 - pp, t1 - pp])     # ⭐ U4b 右截斷
    hdef[pp] = np.maximum(hd, 0)
    h5 = np.asarray(np.load(os.path.join(WORK5, "hdef.npy"), mmap_mode="r")[si])
    hmis = int((np.clip(np.minimum(h5.astype(np.int64), t1 - np.arange(n)), 0, None) != hdef).sum())
    sel = (pp >= t0) & (pp <= t1)
    ev = []; cP = {}; ends = {}
    for hi, H in enumerate(HS):
        rmx = pd.Series(cff[::-1]).rolling(H, min_periods=1).max().to_numpy()[::-1]
        fm = np.r_[rmx[1:], np.nan]
        okH = hdef[pp] >= H
        MH = np.where(okH, fm[pp] / c - 1, np.nan)
        for gi, g in enumerate(GS):
            q = pp[np.flatnonzero(sel & okH & (fm[pp] >= c * (1 + g) * (1 - 1e-9)))]
            if len(q) == 0:
                continue
            lastE = -10 ** 9; j = 0                                                  # ⭐ 鏈從 t0 起算（U4）
            while j < len(q):
                t = int(q[j])
                if t - lastE > H:
                    seg = cff[t + 1:t + H + 1]; P = t + 1 + int(np.argmax(seg)); ct = cff[t]
                    dg = int(np.argmax(seg >= ct * (1 + g) * (1 - 1e-9))) + 1
                    ev.append((S5.cell_of(hi, gi), t, float(MH[np.searchsorted(pp, t)]), P, dg))
                    lastE = t
                    j = int(np.searchsorted(q, t + H + 1))
                else:
                    j += 1
    E = {k_: [] for k_ in ("cell", "d", "M", "P", "dg", "M250", "obs", "maxdd", "rec", *[f"dd{int(x * 100)}" for x in DD], "ps_g", "ps_d", "ps_open")}
    for cc, t, M, P, dg in ev:
        if P not in cP:
            endobs = min(last, int(nxt[P + 1]) - 1 if P + 1 <= n else n - 1, n - 1, t1)                  # ⭐ U4b
            aft = cff[P + 1:endobs + 1]; pk = cff[P]
            hits = []
            for x in DD:
                w_ = np.flatnonzero(aft <= pk * (1 - x)); hits.append(int(w_[0]) + 1 if len(w_) else -1)
            rw = np.flatnonzero(aft > pk)
            sg_ = cff[P:endobs + 1]; rmax = np.maximum.accumulate(sg_); w_ = np.flatnonzero(sg_ / rmax - 1 <= -0.3)
            stop = int(w_[0]) if len(w_) else len(sg_); ps = int(np.argmax(sg_[:stop]))
            cP[P] = (endobs - P, float(aft.min() / pk - 1) if len(aft) else np.nan, int(rw[0]) + 1 if len(rw) else -1, hits, float(sg_[ps]), P + ps, int(len(w_) == 0))
        if t not in ends:
            m250 = cff[t + 1:t + 1 + min(250, int(hdef[t]))]
            ends[t] = float(m250.max() / cff[t] - 1) if len(m250) else np.nan
        ob, mdd, rec, hits, psv, psp, pso = cP[P]; m250 = ends[t]
        E["cell"].append(cc); E["d"].append(t); E["M"].append(M); E["P"].append(P); E["dg"].append(dg); E["M250"].append(m250)
        E["obs"].append(ob); E["maxdd"].append(mdd); E["rec"].append(rec)
        for x, hv in zip(DD, hits):
            E[f"dd{int(x * 100)}"].append(hv)
        E["ps_g"].append(psv / cff[t] - 1); E["ps_d"].append(psp - t); E["ps_open"].append(pso)
    E = {k_: np.asarray(v_, dtype=np.float32 if k_ in ("M", "M250", "maxdd", "ps_g") else np.int32) for k_, v_ in E.items()}
    E["s"] = np.full(len(ev), si, np.int32)
    return si, {"E": E, "hmis": hmis}


def cal_bounds(cal):
    return int(cal.searchsorted(pd.Timestamp(EV_FROM))), int(cal.searchsorted(pd.Timestamp(EV_TO), side="right")) - 1


def build_events(a, log):
    os.makedirs(WORK6, exist_ok=True)
    uni = pd.read_csv(os.path.join(WORK5, "uni.csv"), dtype=str)
    D.DATA = S5.ST; cal = D.load_calendar()
    t0, t1 = cal_bounds(cal)
    log(f"[事件] 起漲日範圍 {cal[t0].date()}～{cal[t1].date()}（索引 {t0}～{t1}）；鏈從 {cal[t0].date()} 起算")
    sids = list(zip(range(len(uni)), uni["stock_id"], uni["market"]))
    EV = []; hm = 0; done = 0
    with Pool(a.procs, initializer=_init, initargs=({"cal": cal, "t0": t0, "t1": t1},)) as pool:
        for si, o in pool.imap_unordered(ev_stock, sids, chunksize=8):
            done += 1
            if o is not None:
                EV.append(o["E"]); hm += o["hmis"]
            if done % 400 == 0:
                log(f"[事件] {done}/{len(sids)}")
    E = {k: np.concatenate([e[k] for e in EV]) for k in EV[0]}
    np.savez(os.path.join(WORK6, "events.npz"), **E)
    np.save(os.path.join(WORK6, "hdef6.npy"), hdef6(cal))
    e5 = np.load(os.path.join(WORK5, "events.npz"))
    d5 = e5["d"]; n5 = int(((d5 >= t0) & (d5 <= t1)).sum())
    info = {"起漲日範圍": [str(cal[t0].date()), str(cal[t1].date())], "事件列": int(len(E["d"])), "定義域與 s5work hdef 不同的股日": hm,
            "對照：seq5 全日曆鏈、不右截斷，直接篩同範圍的事件列": n5, "d 範圍檢查": [int(E["d"].min()), int(E["d"].max())]}
    json.dump(info, open(os.path.join(WORK6, "events.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"[事件] 完成 {json.dumps(info, ensure_ascii=False)}")
    assert hm == 0, "⛔ 定義域與 s5work（右截斷後）不同"
    assert E["d"].min() >= t0 and E["d"].max() <= t1


# ═════════════ prep：沿用 s5work 之前的查核（U3）═════════════
def prep(a, log):
    os.makedirs(OUT, exist_ok=True)
    W, uni = S5.world(log)
    u5 = pd.read_csv(os.path.join(WORK5, "uni.csv"), dtype=str)
    res = {"母體與 uni.csv 相同": bool(list(uni["stock_id"]) == list(u5["stock_id"]) and list(uni["market"]) == list(u5["market"]))}
    cal = W["cal"]; n = len(cal); t0, t1 = cal_bounds(cal)
    bar = np.load(os.path.join(WORK5, "bar.npy"), mmap_mode="r")
    rng = np.random.default_rng(20260930)
    act = np.asarray(bar[:, t0:t1 + 1]).sum(1)
    dl = set(pd.read_csv(os.path.join(S5.ST, "meta", "delisted.csv"), dtype=str)["stock_id"])
    cand = [i for i in range(len(uni)) if act[i] > 200]
    cdl = [i for i in cand if uni.loc[i, "stock_id"] in dl]
    smp = sorted(set(rng.choice(cand, 5, replace=False).tolist()) | set(rng.choice(cdl, 2, replace=False).tolist()))
    res["抽樣"] = [uni.loc[i, "stock_id"] for i in smp]
    S5._init(W)
    F = np.load(os.path.join(WORK5, "F.npy"), mmap_mode="r"); R = np.load(os.path.join(WORK5, "R.npy"), mmap_mode="r")
    AUX = {k: np.load(os.path.join(WORK5, k + ".npy"), mmap_mode="r") for k in ("bar", "hdef", "buy_ok", "locked", "disp", "r20c")}
    E5 = np.load(os.path.join(WORK5, "events.npz"))
    crosscols = {i for i, c in enumerate(S5.FCOL) if c.startswith("indrk_") or c.startswith("tdcc_") or c == "d_X1"}
    diffs = {}
    _init({"cal": cal, "t0": 0, "t1": n - 1})
    for si in smp:
        sid, mk = uni.loc[si, "stock_id"], uni.loc[si, "market"]
        _, o = S5.stock((si, sid, mk))
        S5._init(W)
        fo = o["F"]; fr = np.asarray(F[:, si, :])
        rows = [i for i in range(len(S5.FCOL)) if i not in crosscols]
        dF = int((~((fo[rows] == fr[rows]) | (np.isnan(fo[rows]) & np.isnan(fr[rows])))).sum())
        rr = np.asarray(R[:, si, :]); dR = int((~((o["R"] == rr) | (np.isnan(o["R"]) & np.isnan(rr)))).sum())
        dA = {}
        for k, arr in AUX.items():
            x = np.asarray(arr[si]); y = o[k]
            dA[k] = int((~((x == y) | (np.isnan(x.astype(float)) & np.isnan(np.asarray(y, float))))).sum())
        k5 = np.flatnonzero(E5["s"] == si)
        ref = sorted(zip(*(E5[c][k5].tolist() for c in ("cell", "d", "P", "dg", "dd30", "dd50"))))
        mine5 = sorted(zip(*(o["E"][c].tolist() for c in ("cell", "d", "P", "dg", "dd30", "dd50"))))
        # 本件事件函式關掉起點限制（t0＝0）⇒ 應與 seq5 stock() 事件完全相同（驗照抄無誤）
        _init({"cal": cal, "t0": 0, "t1": n - 1}); _, e6 = ev_stock((si, sid, mk)); S5._init(W)
        mine6 = sorted(zip(*(e6["E"][c].tolist() for c in ("cell", "d", "P", "dg", "dd30", "dd50"))))
        diffs[sid] = {"F 不同格": dF, "R 不同格": dR, **{f"{k} 不同": v for k, v in dA.items()},
                      "seq5 stock() 事件＝s5work events": ref == mine5, "本件事件函式（無起點）＝seq5 stock()": mine6 == mine5, "事件數": len(ref)}
        log(f"[prep] {sid} {diffs[sid]}")
    res["逐檔"] = diffs
    Q = np.load(os.path.join(WORK5, "Q.npy"), mmap_mode="r")
    nq = 0; tq = 0
    days = rng.choice(np.arange(t0, t1 + 1), 6, replace=False)
    for col in ("r_60", "amt_20", "turn_5", "yoy", "fnet_20", "bbw_250"):
        fi = S5.FIX[col]
        for t in days:
            b = np.asarray(bar[:, t]); x = np.asarray(F[fi, :, t], float)
            q = np.zeros(len(b), np.int8); q[b] = S5.qtie(x[b])
            tq += 1; nq += int(not np.array_equal(q, np.asarray(Q[fi, :, t])))
    res["五等分 抽 36 個 特徵×日 不同"] = nq
    ok = res["母體與 uni.csv 相同"] and nq == 0 and all(v["F 不同格"] == 0 and v["R 不同格"] == 0 and all(v[f"{k} 不同"] == 0 for k in AUX)
                                                     and v["本件事件函式（無起點）＝seq5 stock()"] for v in diffs.values())
    res["可沿用"] = bool(ok)
    json.dump(res, open(os.path.join(OUT, "check_prep.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[prep] 可沿用＝{ok}")


# ═════════════ 共用 ═════════════
def hdef6(cal):
    """U4b：seq5 hdef 再截到 2026-08-31。"""
    n = len(cal); _, t1 = cal_bounds(cal)
    h5 = np.load(os.path.join(WORK5, "hdef.npy"))
    return np.clip(np.minimum(h5.astype(np.int32), (t1 - np.arange(n))[None, :]), 0, 250).astype(np.int16)


def load_h6():
    return np.load(os.path.join(WORK6, "hdef6.npy"))


def load6():
    uni = pd.read_csv(os.path.join(WORK5, "uni.csv"), dtype=str)
    D.DATA = S5.ST; cal = D.load_calendar()
    mon = np.array([d.year * 12 + d.month - 1 for d in cal])
    segd = {k: (mon >= pm(x)) & (mon <= pm(y)) for k, (x, y) in SEG.items()}
    E = dict(np.load(os.path.join(WORK6, "events.npz")))
    return uni, cal, mon, segd, E


def lvname(lv):
    return f"{lv[4]}｜{lv[3]}"


# ═════════════ 描述層（seq5 第一批同式；只兩段）═════════════
def run_desc(st, log):
    uni, cal, mon, segd, E = load6()
    bar = np.load(os.path.join(WORK5, "bar.npy")); hdef = load_h6()
    locked = np.load(os.path.join(WORK5, "locked.npy")); disp = np.load(os.path.join(WORK5, "disp.npy"))
    qliq = np.asarray(np.load(os.path.join(WORK5, "Q.npy"), mmap_mode="r")[S5.FIX["amt_20"]])
    nxt_bar = np.zeros_like(bar); nxt_bar[:, :-1] = bar[:, 1:]
    nxt_lock = np.zeros_like(bar); nxt_lock[:, :-1] = locked[:, 1:]
    nxt_disp = np.zeros_like(bar); nxt_disp[:, :-1] = disp[:, 1:]
    excl = ~nxt_bar | nxt_lock | nxt_disp
    ec, es, ed = E["cell"].astype(int), E["s"].astype(int), E["d"].astype(int)
    SUM = {**st, "執行者": NOSEEN, "揭露": DISCLOSE, "段": {}}
    G = []; BAND = []; BUY = []
    for sg, dm in segd.items():
        rows = bar & dm[None, :]
        dc = DS.defined_counts(hdef, rows); dcx = DS.defined_counts(hdef, rows & ~excl)
        hmax = np.where(rows, hdef, 0).max(0)
        lastdef = {H: (int(np.flatnonzero(hmax >= H).max()) if (hmax >= H).any() else -1) for H in HS}
        ine = dm[ed]
        SUM["段"][sg] = {"股日": int(rows.sum()), "檔": int(rows.any(1).sum()), "月": f"{SEG[sg][0]}～{SEG[sg][1]}"}
        for c in range(NC):
            hi, gi = divmod(c, len(GS)); H, g = HS[hi], GS[gi]
            k = np.flatnonzero((ec == c) & ine)
            r = {"段": sg, "格": S5.cell_name(c), "H": H, "g": g, "事件": len(k), "定義域股日": dc[H], "比例": len(k) / dc[H] if dc[H] else np.nan,
                 "實際起漲日最早": str(cal[int(ed[k].min())].date()) if len(k) else "", "實際起漲日最晚": str(cal[int(ed[k].max())].date()) if len(k) else "",
                 "定義域最後起漲日": str(cal[int(lastdef[H])].date()) if lastdef[H] >= 0 else ""}
            if len(k):
                M = E["M"][k]; dg = E["dg"][k]; pt = E["P"][k] - ed[k]
                r.update({"最大漲幅中位（H內）": float(np.median(M)), "最大漲幅中位（不設H，到回落30%前）": float(np.median(E["ps_g"][k])),
                          "P*未完比例": float(np.mean(E["ps_open"][k])),
                          **{f"花幾天_{p}": v for p, v in DS.qs(dg).items()}, **{f"起漲到P_{p}": v for p, v in DS.qs(pt).items()}})
                ob = E["obs"][k]
                for x in DD:
                    hv = E[f"dd{int(x * 100)}"][k]; hit = hv > 0
                    r[f"回落{int(x * 100)}%_比例"] = float(hit.mean())
                    for w in (60, 120, 250):
                        den = hit & (hv <= w) | (ob >= w)
                        r[f"回落{int(x * 100)}%_{w}日內"] = float(((hv > 0) & (hv <= w))[den].mean()) if den.any() else np.nan
                    r[f"回落{int(x * 100)}%_P到觸及中位日"] = float(np.median(hv[hit])) if hit.any() else np.nan
                    r[f"回落{int(x * 100)}%_P到觸及p25日"] = float(np.percentile(hv[hit], 25)) if hit.any() else np.nan
                    r[f"回落{int(x * 100)}%_P到觸及p75日"] = float(np.percentile(hv[hit], 75)) if hit.any() else np.nan
                r["P後最大回落中位"] = float(np.nanmedian(E["maxdd"][k])); r["P後觀察天數中位"] = float(np.median(ob))
                yao = E["dd50"][k] > 0
                for nm, mk_ in (("妖股", yao), ("非妖股", ~yao)):
                    r[f"{nm}_事件"] = int(mk_.sum())
                    r[f"{nm}_起漲到P中位"] = float(np.median(pt[mk_])) if mk_.any() else np.nan
                    for x in (0.1, 0.2, 0.3):
                        hv = E[f"dd{int(x * 100)}"][k][mk_]
                        r[f"{nm}_P到回落{int(x * 100)}%中位"] = float(np.median(hv[hv > 0])) if (hv > 0).any() else np.nan
            r["樣本少"] = bool(len(k) < 30)
            G.append(r)
            if gi + 1 < len(GS):
                kb = k[E["M"][k] < GS[gi + 1]] if len(k) else k
                BAND.append({"段": sg, "H": H, "區間": f"{int(g * 100)}～{int(GS[gi + 1] * 100)}%", "事件": len(kb), "比例": len(kb) / dc[H] if dc[H] else np.nan})
            else:
                BAND.append({"段": sg, "H": H, "區間": "≥1000%", "事件": len(k), "比例": len(k) / dc[H] if dc[H] else np.nan})
            if len(k):
                s_, d_ = es[k], ed[k]
                b = {"段": sg, "格": S5.cell_name(c), "H": H, "g": g, "事件": len(k),
                     "t+1無成交": float((~nxt_bar[s_, d_]).mean()), "t+1漲停鎖死": float(nxt_lock[s_, d_].mean()), "t+1處置中": float(nxt_disp[s_, d_].mean())}
                ql = qliq[s_, d_]
                for q in range(1, 6):
                    b[f"20日均額Q{q}"] = float((ql == q).mean())
                keep = ~excl[s_, d_]
                b["剔除後事件"] = int(keep.sum()); b["剔除後比例"] = int(keep.sum()) / dcx[H] if dcx[H] else np.nan
                b["原比例"] = len(k) / dc[H] if dc[H] else np.nan
                BUY.append(b)
        log(f"[描述] {sg} 完成")
    G = pd.DataFrame(G); BAND = pd.DataFrame(BAND); BUY = pd.DataFrame(BUY)
    FAST = DS.fastest(E, uni, cal, log)
    for sg, dm in segd.items():
        for g in (0.5, 1.0, 2.0):
            c = S5.cell_of(len(HS) - 1, GS.index(g))
            k = np.flatnonzero((ec == c) & dm[ed])
            v = np.array([FAST.get((int(es[i]), int(ed[i]), c), np.nan) for i in k], float)
            ix = G.index[(G["段"] == sg) & (G["H"] == 250) & np.isclose(G["g"], g)][0]
            for p, val in DS.qs(v).items():
                G.loc[ix, f"最短花幾天_{p}"] = val
    G.to_csv(os.path.join(OUT, "grid.csv"), index=False, float_format="%.6g")
    BAND.to_csv(os.path.join(OUT, "grid_band.csv"), index=False, float_format="%.6g")
    BUY.to_csv(os.path.join(OUT, "buyable.csv"), index=False, float_format="%.6g")
    MG = []
    for sg, dm in segd.items():
        k = np.flatnonzero(dm[ed])
        key = es[k].astype(np.int64) * 100000 + ed[k]
        df = pd.DataFrame({"key": key, "M250": E["M250"][k], "ps": E["ps_g"][k], "open": E["ps_open"][k]}).groupby("key").agg(M250=("M250", "first"), ps=("ps", "max"), open=("open", "max"))
        for nm, col in (("250日內最大漲幅", "M250"), ("不設H最大漲幅（到回落30%前）", "ps")):
            x = df[col].to_numpy(float); x = x[np.isfinite(x)]
            h = np.histogram(x, bins=DS.BUCK)[0]
            MG.append({"段": sg, "口徑": nm, "起漲事件（聯集）": int(len(x)), **{b: int(v) for b, v in zip(DS.BUCKN, h)},
                       **{f"占比_{b}": float(v / len(x)) if len(x) else np.nan for b, v in zip(DS.BUCKN, h)}, **DS.qs(x), "未完比例": float(df["open"].mean()) if col == "ps" else np.nan})
    MG = pd.DataFrame(MG); MG.to_csv(os.path.join(OUT, "maxgain.csv"), index=False, float_format="%.6g")
    SUM["最大漲幅分佈"] = MG[["段", "口徑", "起漲事件（聯集）", "p50", "p90"]].to_dict("records")
    json.dump(SUM, open(os.path.join(OUT, "summary_desc.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log("[描述] 輸出 grid／grid_band／buyable／maxgain")


# ═════════════ 特徵層（seq5 第二批同式；只兩段）═════════════
def run_feat(st, log):
    T0 = time.time()
    uni, cal, mon, segd, E = load6()
    n = len(cal)
    mi = (mon - mon.min()).astype(np.int64); NM = int(mi.max()) + 1
    segm = {sg: np.zeros(NM, bool) for sg in SEG}
    inany = np.zeros(n, bool)
    for sg, dm in segd.items():
        segm[sg][np.unique(mi[dm])] = True; inany |= dm
    bar = np.load(os.path.join(WORK5, "bar.npy")); hdef = load_h6()
    locked = np.load(os.path.join(WORK5, "locked.npy")); disp = np.load(os.path.join(WORK5, "disp.npy"))
    nxt_bar = np.zeros_like(bar); nxt_bar[:, :-1] = bar[:, 1:]
    excl = ~nxt_bar; excl[:, :-1] |= locked[:, 1:] | disp[:, 1:]
    log("[特徵] 載入五等分表"); Q = np.load(os.path.join(WORK5, "Q.npy"))
    LV = FT.levels()
    log(f"[特徵] 級距 {len(LV)}（進挑選 {sum(1 for x in LV if x[8])}）")
    bidx = np.flatnonzero((bar & inany[None, :]).ravel())                           # ⭐ U5：分母只取兩段內
    b_day = bidx % n; b_mi = mi[b_day]; b_h = np.minimum(hdef.ravel()[bidx].astype(np.int64), 250)
    b_ex = excl.ravel()[bidx]
    ec, es, ed = E["cell"].astype(np.int64), E["s"].astype(np.int64), E["d"].astype(np.int64)
    e_mi = mi[ed]; e_ex = excl[es, ed]
    assert inany[ed].all()

    def base_counts(qf, rowmask=None):
        keep = qf > 0
        if rowmask is not None:
            keep &= rowmask
        key = (qf[keep].astype(np.int64) * NM + b_mi[keep]) * 251 + b_h[keep]
        c = np.bincount(key, minlength=CODES * NM * 251).reshape(CODES, NM, 251)
        ge = np.cumsum(c[:, :, ::-1], axis=2)[:, :, ::-1]
        return ge[:, :, list(HS)]

    def ev_counts(code_e, w=None, evmask=None):
        keep = code_e > 0
        if evmask is not None:
            keep &= evmask
        key = (code_e[keep].astype(np.int64) * NC + ec[keep]) * NM + e_mi[keep]
        return np.bincount(key, weights=None if w is None else w[keep], minlength=CODES * NC * NM).reshape(CODES, NC, NM)

    cellsA = {}
    for fi_ in sorted({x[0] for x in LV}):
        q = Q[fi_]; qf = q.ravel()[bidx]
        NC_ = base_counts(qf); code_e = q[es, ed]; EC_ = ev_counts(code_e)
        nrow = NC_[:, :, FT.HI_OF_CELL].transpose(0, 2, 1)
        eall = EC_[1:].sum(0); nall = nrow[1:].sum(0)
        for lv in [x for x in LV if x[0] == fi_]:
            code = lv[2]
            for sg in SEG:
                sm = segm[sg]
                e = EC_[code][:, sm].astype(float); nn = nrow[code][:, sm].astype(float)
                if nn.sum() == 0:
                    continue
                lift, lo, hi, cov = FT.ratio_stats(e, nn, eall[:, sm].astype(float), nall[:, sm].astype(float), e.sum(1), eall[:, sm].sum(1).astype(float), Z95)
                cellsA[(lv[1], code, sg)] = (lift, lo, hi, cov, e.sum(1), nn.sum(1))
    log(f"[①②] 完成 {time.time() - T0:.0f}s")
    PK = []
    for lv in LV:
        r = cellsA.get((lv[1], lv[2], "探索"))
        if r is None or not lv[8]:
            continue
        lift, lo, hi, cov, ev, nn = r
        if int(np.sum((lo > 1) & (cov >= 0.05))) >= HALF:
            PK.append(lv)
    k = len(PK); zB = NormalDist().inv_cdf(1 - 0.025 / max(k, 1))
    log(f"[挑選] 探索段進確認段 {k} 個級距｜Bonferroni z＝{zB:.3f}")
    for lv in PK:
        fi_ = lv[0]; q = Q[fi_]; qf = q.ravel()[bidx]
        NC_ = base_counts(qf); code_e = q[es, ed]; EC_ = ev_counts(code_e)
        nrow = NC_[:, :, FT.HI_OF_CELL].transpose(0, 2, 1); eall = EC_[1:].sum(0); nall = nrow[1:].sum(0)
        sm = segm["確認"]; code = lv[2]
        e = EC_[code][:, sm].astype(float); nn = nrow[code][:, sm].astype(float)
        cellsA[(lv[1], code, "確認B")] = FT.ratio_stats(e, nn, eall[:, sm].astype(float), nall[:, sm].astype(float), e.sum(1), eall[:, sm].sum(1).astype(float), zB) + (e.sum(1), nn.sum(1))
        NCx = base_counts(qf, ~b_ex); ECx = ev_counts(code_e, evmask=~e_ex)
        nrx = NCx[:, :, FT.HI_OF_CELL].transpose(0, 2, 1); eax = ECx[1:].sum(0); nax = nrx[1:].sum(0)
        for sg in SEG:
            sm = segm[sg]; e = ECx[code][:, sm].astype(float); nn = nrx[code][:, sm].astype(float)
            cellsA[(lv[1], code, sg + "_可買")] = FT.ratio_stats(e, nn, eax[:, sm].astype(float), nax[:, sm].astype(float), e.sum(1), eax[:, sm].sum(1).astype(float), zB if sg == "確認" else Z95) + (e.sum(1), nn.sum(1))
    recs = []
    for (col, code, sg), (lift, lo, hi, cov, ev, nn) in cellsA.items():
        for c in range(NC):
            recs.append((col, code, sg, S5.cell_name(c), float(lift[c]), float(lo[c]), float(hi[c]), float(cov[c]), int(ev[c]), int(nn[c])))
    A = pd.DataFrame(recs, columns=["欄", "碼", "段", "格", "提升", "下緣", "上緣", "涵蓋率", "事件", "定義域列"])
    A.to_csv(os.path.join(OUT, "feat_cells.csv.gz"), index=False, float_format="%.5g")
    del A, recs
    SUMR = []
    for lv in LV:
        r = {"欄": lv[1], "碼": lv[2], "特徵": lvname(lv), "類別": lv[5], "型態": lv[6], "進挑選": lv[8], "進確認段": lv in PK}
        for sg in ("探索", "確認", "確認B", "探索_可買", "確認_可買"):
            x = cellsA.get((lv[1], lv[2], sg))
            if x is None:
                continue
            lift, lo, hi, cov, ev, nn = x
            r[f"{sg}_提升中位"] = float(np.nanmedian(lift)); r[f"{sg}_涵蓋率中位"] = float(np.nanmedian(cov))
            r[f"{sg}_下緣>1格數"] = int(np.sum(lo > 1)); r[f"{sg}_提升>1格數"] = int(np.sum(lift > 1))
            r[f"{sg}_下緣>1且涵蓋≥5%格數"] = int(np.sum((lo > 1) & (cov >= 0.05)))
            r[f"{sg}_H60g100_提升"] = float(lift[S5.cell_of(5, 1)]); r[f"{sg}_H60g100_下緣"] = float(lo[S5.cell_of(5, 1)]); r[f"{sg}_H60g100_涵蓋率"] = float(cov[S5.cell_of(5, 1)])
        if lv in PK:
            r["站得住（確認，Bonferroni）"] = bool(r.get("確認B_下緣>1格數", 0) >= HALF)
        SUMR.append(r)
    SUMR = pd.DataFrame(SUMR)
    log(f"[確認] 站得住 {int(FT._flag(SUMR, '站得住（確認，Bonferroni）').sum())} 個")
    # ③
    Rm = np.load(os.path.join(WORK5, "R.npy"), mmap_mode="r"); r20 = np.load(os.path.join(WORK5, "r20c.npy"))
    b_h6 = hdef.ravel()[bidx].astype(np.int64)                                      # ⭐ U4b：R_h 要 t＋h ≤ 2026-08-31
    R5 = np.where(b_h6 >= HOLD[0], np.asarray(Rm[0]).ravel()[bidx], np.nan); r20f = r20.ravel()[bidx]
    ok10 = np.isfinite(R5) & np.isfinite(r20f)
    dec = np.full(len(bidx), -1, np.int64)
    order = np.argsort(b_day, kind="stable")
    bd_sorted = b_day[order]; starts = np.searchsorted(bd_sorted, np.arange(n)); ends = np.searchsorted(bd_sorted, np.arange(n), side="right")
    for t in np.flatnonzero(inany):
        ix = order[starts[t]:ends[t]]
        if len(ix) == 0:
            continue
        dec[ix] = AV.deciles(np.where(ok10[ix], r20f[ix], np.nan))
    log(f"[③] 基準② 十分位完成 {time.time() - T0:.0f}s")
    fis = sorted({x[0] for x in LV})
    ACC = {k_: np.zeros((len(fis), len(HOLD), CODES, NM)) for k_ in ("n1", "s1", "n2", "s2", "nr", "sr")}
    ALL = {k_: np.zeros((len(HOLD), NM)) for k_ in ("nr", "sr", "n1", "s1", "n2", "s2")}
    Qf = {fi_: Q[fi_].ravel()[bidx] for fi_ in fis}
    del Q
    for j, hh in enumerate(HOLD):
        r = np.asarray(Rm[j]).ravel()[bidx].astype(np.float64); r[b_h6 < hh] = np.nan; fin = np.isfinite(r)
        sd = np.bincount(b_day[fin], r[fin], minlength=n); cd = np.bincount(b_day[fin], minlength=n)
        x1 = np.full(len(r), np.nan); m1 = fin & (cd[b_day] > 1)
        x1[m1] = r[m1] - (sd[b_day[m1]] - r[m1]) / (cd[b_day[m1]] - 1)
        k2 = b_day * 10 + dec; m2 = fin & (dec >= 0)
        s2 = np.bincount(k2[m2], r[m2], minlength=n * 10); c2 = np.bincount(k2[m2], minlength=n * 10)
        x2 = np.full(len(r), np.nan); m2 &= c2[np.where(dec >= 0, k2, 0)] > 1
        x2[m2] = r[m2] - (s2[k2[m2]] - r[m2]) / (c2[k2[m2]] - 1)
        rn = r - COST
        ALL["nr"][j] = np.bincount(b_mi[fin], minlength=NM); ALL["sr"][j] = np.bincount(b_mi[fin], rn[fin], minlength=NM)
        ALL["n2"][j] = np.bincount(b_mi[m2], minlength=NM); ALL["s2"][j] = np.bincount(b_mi[m2], x2[m2], minlength=NM)
        ALL["n1"][j] = np.bincount(b_mi[m1], minlength=NM); ALL["s1"][j] = np.bincount(b_mi[m1], x1[m1], minlength=NM)
        for a_, fi_ in enumerate(fis):
            qf = Qf[fi_]
            for nk, sk, mk_, val in (("n1", "s1", m1, x1), ("n2", "s2", m2, x2), ("nr", "sr", fin, rn)):
                kk = mk_ & (qf > 0)
                key = qf[kk].astype(np.int64) * NM + b_mi[kk]
                ACC[nk][a_, j] = np.bincount(key, minlength=CODES * NM).reshape(CODES, NM)
                ACC[sk][a_, j] = np.bincount(key, val[kk], minlength=CODES * NM).reshape(CODES, NM)
        if j % 10 == 0:
            log(f"[③] h＝{hh} {time.time() - T0:.0f}s")
    del Qf
    fpos = {fi_: a_ for a_, fi_ in enumerate(fis)}
    CUR = []

    def cstat(nm_, sm_, z):
        nn = nm_[0][..., sm_]; ss = nm_[1][..., sm_]
        N = nn.sum(-1)
        with np.errstate(invalid="ignore", divide="ignore"):
            mu = ss.sum(-1) / N
            se = np.sqrt(((ss - mu[..., None] * nn) ** 2).sum(-1)) / N
        return mu, mu - z * se, mu + z * se, N
    for sg in SEG:
        sm = segm[sg]
        mu, lo, hi, N = cstat((ALL["nr"], ALL["sr"]), sm, Z95)
        mu2, lo2, hi2, N2 = cstat((ALL["n2"], ALL["s2"]), sm, Z95)
        for j, hh in enumerate(HOLD):
            CUR.append({"欄": "全體", "碼": 0, "特徵": "全體", "段": sg, "h": hh, "淨報酬": mu[j], "淨報酬_下": lo[j], "淨報酬_上": hi[j], "n": int(N[j]), "對基準②": mu2[j]})
    for lv in LV:
        a_ = fpos[lv[0]]; code = lv[2]
        for sg in SEG:
            z = zB if (sg == "確認" and lv in PK) else Z95
            sm = segm[sg]
            o1 = cstat((ACC["n1"][a_, :, code], ACC["s1"][a_, :, code]), sm, z)
            o2 = cstat((ACC["n2"][a_, :, code], ACC["s2"][a_, :, code]), sm, z)
            orr = cstat((ACC["nr"][a_, :, code], ACC["sr"][a_, :, code]), sm, z)
            for j, hh in enumerate(HOLD):
                CUR.append({"欄": lv[1], "碼": code, "特徵": lvname(lv), "段": sg, "h": hh, "對全體": o1[0][j], "對全體_下": o1[1][j], "對全體_上": o1[2][j],
                            "對基準②": o2[0][j], "對基準②_下": o2[1][j], "對基準②_上": o2[2][j], "淨報酬": orr[0][j], "淨報酬_下": orr[1][j], "淨報酬_上": orr[2][j], "n": int(o2[3][j])})
    CUR = pd.DataFrame(CUR); CUR.to_csv(os.path.join(OUT, "curves.csv.gz"), index=False, float_format="%.5g")

    def ranges(g):
        ok = (g["對基準②_下"].to_numpy() - COST > 0); hs = g["h"].to_numpy(); out = []; i = 0
        while i < len(ok):
            if ok[i]:
                j = i
                while j + 1 < len(ok) and ok[j + 1]:
                    j += 1
                if j - i + 1 >= 3:
                    out.append(f"{hs[i]}～{hs[j]} 日")
                i = j + 1
            else:
                i += 1
        neg = (g["對基準②_上"].to_numpy() + COST < 0)
        return "、".join(out) if out else "沒有", int(neg.sum())
    cg = CUR[CUR["欄"] != "全體"].groupby(["欄", "碼", "段"])
    RG = {kk: ranges(g.sort_values("h")) for kk, g in cg}
    for sg in SEG:
        SUMR[f"{sg}_③買了賺的持有區間"] = [RG.get((c_, q_, sg), ("—", 0))[0] for c_, q_ in zip(SUMR["欄"], SUMR["碼"])]
        SUMR[f"{sg}_③顯著輸的格數"] = [RG.get((c_, q_, sg), ("—", 0))[1] for c_, q_ in zip(SUMR["欄"], SUMR["碼"])]
        for hh in (20, 60, 120, 250):
            g = CUR[(CUR["段"] == sg) & (CUR["h"] == hh)].set_index(["欄", "碼"])
            SUMR[f"{sg}_③對基準②_{hh}日"] = [g["對基準②"].get((c_, q_), np.nan) for c_, q_ in zip(SUMR["欄"], SUMR["碼"])]
    log(f"[③] 完成 {time.time() - T0:.0f}s")
    Q = np.load(os.path.join(WORK5, "Q.npy"))

    def family(get_counts, tag):
        ST_ = {}; CF = {}
        for fi_ in fis:
            ea_, na_ = get_counts(fi_)
            eA = ea_[1:].sum(0); nA = na_[1:].sum(0)
            for lv in [v for v in LV if v[0] == fi_]:
                code = lv[2]
                for sg in SEG:
                    sm = segm[sg]
                    e = ea_[code][:, sm].astype(float); nn = na_[code][:, sm].astype(float)
                    if nn.sum() == 0:
                        continue
                    ea = eA[:, sm].astype(float); na = nA[:, sm].astype(float)
                    s_ = FT.ratio_stats(e, nn, ea, na, e.sum(1), ea.sum(1), Z95)
                    ST_[(lv, sg)] = (s_[0], s_[1], s_[3], e.sum(1))
                    if sg == "確認":
                        CF[lv] = (e.astype(np.float32), nn.astype(np.float32), ea.astype(np.float32), na.astype(np.float32))
        pk = [lv for lv in LV if lv[8] and (lv, "探索") in ST_ and int(np.sum((ST_[(lv, "探索")][1] > 1) & (ST_[(lv, "探索")][2] >= 0.05))) >= HALF]
        zb = NormalDist().inv_cdf(1 - 0.025 / max(len(pk), 1))
        out = []
        for lv in LV:
            r = {**tag, "欄": lv[1], "碼": lv[2], "特徵": lvname(lv), "進確認段": lv in pk}
            for sg in SEG:
                v = ST_.get((lv, sg))
                if v is None:
                    continue
                lift, lo, cov, es_ = v
                r[f"{sg}_提升中位"] = float(np.nanmedian(lift)); r[f"{sg}_涵蓋率中位"] = float(np.nanmedian(cov))
                r[f"{sg}_下緣>1且涵蓋≥5%格數"] = int(np.sum((lo > 1) & (cov >= 0.05))); r[f"{sg}_提升>1格數"] = int(np.sum(lift > 1))
                r[f"{sg}_陽性數"] = int(es_.sum())
            if lv in pk and lv in CF:
                e, nn, ea, na = (x.astype(float) for x in CF[lv])
                lift, lo, hi, cov = FT.ratio_stats(e, nn, ea, na, e.sum(1), ea.sum(1), zb)
                r["確認_Bonferroni下緣>1格數"] = int(np.sum(lo > 1)); r["站得住（確認）"] = bool(r["確認_Bonferroni下緣>1格數"] >= HALF)
            out.append(r)
        return out, pk
    YR = []; YPK = {}
    for x in (30, 50, 70):
        hit = (E[f"dd{x}"] > 0).astype(float)

        def gc(fi_, hit=hit):
            code_e = Q[fi_][es, ed]
            return ev_counts(code_e, w=hit), ev_counts(code_e)
        rr, pk = family(gc, {"回落": f"{x}%"}); YR += rr; YPK[x] = pk
        log(f"[妖股] 回落 {x}%：進確認段 {len(pk)}（{time.time() - T0:.0f}s）")
    YR = pd.DataFrame(YR); YR.to_csv(os.path.join(OUT, "yao_summary.csv"), index=False, float_format="%.5g")
    ER = []; EPK = {}
    Pv = E["P"].astype(np.int64)
    for x in (10, 20, 30):
        ended = E[f"dd{x}"] > 0
        for kk in KEND:
            pos = Pv - kk; mid = ed + (Pv - ed) // 2
            ii = np.flatnonzero(ended & (pos > ed) & (Pv - mid > 20) & (mid > ed))
            cc = ec[ii]; mm_ = e_mi[ii]; ss = es[ii]; pp_ = pos[ii]; md_ = mid[ii]

            def gc(fi_, cc=cc, mm_=mm_, ss=ss, pp_=pp_, md_=md_):
                q = Q[fi_]; cp = q[ss, pp_].astype(np.int64); cq = q[ss, md_].astype(np.int64)
                kp = cp > 0; kq = cq > 0
                npos = np.bincount((cp[kp] * NC + cc[kp]) * NM + mm_[kp], minlength=CODES * NC * NM).reshape(CODES, NC, NM)
                nctl = np.bincount((cq[kq] * NC + cc[kq]) * NM + mm_[kq], minlength=CODES * NC * NM).reshape(CODES, NC, NM)
                return npos, npos + nctl
            rr, pk = family(gc, {"結束套": f"回落{x}%", "k": kk}); ER += rr; EPK[(x, kk)] = pk
            log(f"[結束] 回落 {x}% k＝{kk}：事件 {len(ii)}｜進確認段 {len(pk)}（{time.time() - T0:.0f}s）")
    ER = pd.DataFrame(ER); ER.to_csv(os.path.join(OUT, "end_summary.csv"), index=False, float_format="%.5g")
    nY = {x: len(v) for x, v in YPK.items()}; nE = {f"{x}_{kk}": len(v) for (x, kk), v in EPK.items()}
    NS = k + sum(nY.values()) + sum(nE.values())
    SUMR.to_csv(os.path.join(OUT, "feat_summary.csv"), index=False, float_format="%.5g")
    SUM = {**st, "執行者": NOSEEN, "揭露": DISCLOSE, "g 網格": "照裁定 seq277（10 值 × H 25 ＝ 250 格）",
           "級距數": len(LV), "進挑選級距": sum(1 for x in LV if x[8]), "挑選門檻": f"探索段 250 格中 ≥ {HALF} 格「① 95% 下緣 ＞ 1 且 ② ≥ 5%」",
           "飆股特徵 進確認段": [lvname(lv) for lv in PK], "Bonferroni k（飆股）": k, "Bonferroni z（飆股）": zB,
           "站得住（飆股，確認）": SUMR.loc[FT._flag(SUMR, "站得住（確認，Bonferroni）"), "特徵"].tolist(),
           "妖股 進確認段": {f"{x}%": [lvname(lv) for lv in v] for x, v in YPK.items()},
           "妖股 站得住": {f"{x}%": YR[(YR["回落"] == f"{x}%") & FT._flag(YR, "站得住（確認）")]["特徵"].tolist() for x in (30, 50, 70)},
           "結束 進確認段": {f"回落{x}%_k{kk}": [lvname(lv) for lv in v] for (x, kk), v in EPK.items()},
           "結束 站得住": ER[FT._flag(ER, "站得住（確認）")][["結束套", "k", "特徵"]].to_dict("records"),
           "N_單筆": NS, "N 組成": {"飆股": k, "妖股": nY, "結束": nE}, "耗時秒": round(time.time() - T0)}
    json.dump(SUM, open(os.path.join(OUT, "summary_feat.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] N_單筆 {NS}｜{json.dumps(SUM['N 組成'], ensure_ascii=False)}")


# ═════════════ 結束可交易（S19）═════════════
def run_endtrade(st, log):
    T0 = time.time()
    uni, cal, mon, segd, E = load6()
    n = len(cal); mi = (mon - mon.min()).astype(np.int64); NM = int(mi.max()) + 1
    segm = {sg: np.zeros(NM, bool) for sg in SEG}
    for sg, dm in segd.items():
        segm[sg][np.unique(mi[dm])] = True
    ER = pd.read_csv(os.path.join(OUT, "end_summary.csv"))
    okc = FT._flag(ER, "站得住（確認）")
    LVS = sorted({(c, int(q)) for c, q in zip(ER.loc[okc, "欄"], ER.loc[okc, "碼"])})
    kB = len(LVS); zB = NormalDist().inv_cdf(1 - 0.025 / max(kB, 1))
    log(f"[結束可交易] 站得住的不同級距 {kB}｜Bonferroni z＝{zB:.3f}")
    json.dump({"站得住的不同結束級距": [f"{c} {q}" for c, q in LVS], "k": kB, "z": zB}, open(os.path.join(OUT, "end_trade_meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if not LVS:
        pd.DataFrame().to_csv(os.path.join(OUT, "end_trade_summary.csv"), index=False)
        return
    Qm = np.load(os.path.join(WORK5, "Q.npy"), mmap_mode="r")
    cols = sorted({c for c, _ in LVS}); QQ = {c: np.asarray(Qm[S5.FIX[c]]) for c in cols}
    Rm = np.load(os.path.join(WORK5, "R.npy"), mmap_mode="r"); h6 = load_h6()
    ed = E["d"].astype(np.int64); es = E["s"].astype(np.int64)
    inseg = np.zeros(len(ed), bool)
    for dm in segd.values():
        inseg |= dm[ed]
    key = np.unique(es[inseg] * 100000 + ed[inseg])
    SS, TT = key // 100000, key % 100000
    L = len(LVS); NH_ = len(HOLD)
    acc_n = np.zeros((L, NH_, NM)); acc_s = np.zeros((L, NH_, NM)); acc_hit = np.zeros((L, NH_, NM))
    D.DATA = S5.ST
    for s in np.unique(SS):
        T = TT[SS == s]
        stk = D.load_stock(uni.loc[int(s), "stock_id"], uni.loc[int(s), "market"], cal)
        o = stk.df["open"].to_numpy(float); okop = np.isfinite(o) & (o > 0)
        nxo = np.full(n + 2, n + 10, np.int64)
        for p in range(n - 1, -1, -1):
            nxo[p] = p if okop[p] else nxo[p + 1]
        Rb = np.asarray(Rm[:, int(s), :])[:, T].astype(np.float64)
        Rb[h6[int(s), T][None, :] < np.array(HOLD)[:, None]] = np.nan                  # ⭐ U4b
        ob = o[np.minimum(T + 1, n - 1)]
        m_ = mi[T]
        for li, (c, code) in enumerate(LVS):
            pos = np.flatnonzero(QQ[c][int(s)] == code)
            j = np.searchsorted(pos, T + 1)
            dsig = np.where(j < len(pos), pos[np.minimum(j, len(pos) - 1)] if len(pos) else n + 10, n + 10)
            ex = nxo[np.minimum(dsig + 1, n + 1)]
            for hj, hh in enumerate(HOLD):
                B = Rb[hj]; valid = np.isfinite(B)
                early = (dsig <= T + hh - 1) & (ex <= T + hh)
                A = np.where(early, o[np.minimum(ex, n - 1)] / ob - 1, B)
                Dd = A - B; v = valid & np.isfinite(Dd)
                acc_n[li, hj] += np.bincount(m_[v], minlength=NM)
                acc_s[li, hj] += np.bincount(m_[v], Dd[v], minlength=NM)
                acc_hit[li, hj] += np.bincount(m_[v], early[v].astype(float), minlength=NM)
    rows = []
    for li, (c, code) in enumerate(LVS):
        name = next(f"{sp[1]}｜Q{code}" if sp[3] in ("q", "qts", "x") else f"{sp[1]}｜{code}" for sp in S5.SPECS if sp[0] == c)
        for sg in SEG:
            sm = segm[sg]; z = zB if sg == "確認" else Z95
            nn = acc_n[li][:, sm]; ss = acc_s[li][:, sm]; N = nn.sum(1)
            with np.errstate(invalid="ignore", divide="ignore"):
                mu = ss.sum(1) / N; se = np.sqrt(((ss - mu[:, None] * nn) ** 2).sum(1)) / N
                hit = acc_hit[li][:, sm].sum(1) / N
            for hj, hh in enumerate(HOLD):
                rows.append({"欄": c, "碼": code, "特徵": name, "段": sg, "h": hh, "n": int(N[hj]), "A−B": mu[hj], "下": mu[hj] - z * se[hj], "上": mu[hj] + z * se[hj], "訊號已出現比例": hit[hj]})
    D_ = pd.DataFrame(rows); D_.to_csv(os.path.join(OUT, "end_trade.csv"), index=False, float_format="%.5g")

    def rng_(ok, hs):
        out = []; i = 0
        while i < len(ok):
            if ok[i]:
                j = i
                while j + 1 < len(ok) and ok[j + 1]:
                    j += 1
                if j - i + 1 >= 3:
                    out.append(f"{hs[i]}～{hs[j]} 日")
                i = j + 1
            else:
                i += 1
        return "、".join(out) if out else "沒有"
    SM = []
    for (c, code, name, sg), g in D_.groupby(["欄", "碼", "特徵", "段"]):
        g = g.sort_values("h"); hs = g["h"].to_numpy()
        SM.append({"欄": c, "碼": code, "特徵": name, "段": sg, "一出現就賣較好": rng_((g["下"] > 0).to_numpy(), hs), "續抱較好": rng_((g["上"] < 0).to_numpy(), hs),
                   **{f"A−B_{h}日": float(g.loc[g["h"] == h, "A−B"].iloc[0]) for h in (20, 60, 120, 250)}, "訊號在250日內出現比例": float(g.loc[g["h"] == 250, "訊號已出現比例"].iloc[0])})
    pd.DataFrame(SM).to_csv(os.path.join(OUT, "end_trade_summary.csv"), index=False, float_format="%.5g")
    log(f"[結束可交易] 完成 {time.time() - T0:.0f}s")


# ═════════════ §九之一 量縮描述（U12；只描述、不計 N）═════════════
def run_shrink(st, log):
    T0 = time.time()
    uni, cal, mon, segd, E = load6()
    n = len(cal); t0, t1 = cal_bounds(cal)
    bar = np.load(os.path.join(WORK5, "bar.npy")); h5 = np.load(os.path.join(WORK5, "hdef.npy"))
    x = np.asarray(np.load(os.path.join(WORK5, "F.npy"), mmap_mode="r")[S5.FIX["d_shrink"]])
    shr = (x == 1); defd = np.isfinite(x) & bar
    cs = np.cumsum(shr, axis=1, dtype=np.int32)
    any60 = cs.copy(); any60[:, 60:] -= cs[:, :-60]; any60 = any60 > 0                   # 日曆交易日 t−59～t
    SEGA = {**segd, "全期": segd["探索"] | segd["確認"]}
    ec, es, ed = E["cell"].astype(int), E["s"].astype(int), E["d"].astype(int)
    F1, F2, F3 = S5.cell_of(5, 1), S5.cell_of(1, 0), S5.cell_of(11, 3)
    GRP = {"F1（60日漲100%）": ec == F1, "F2（20日漲50%）": ec == F2, "F3（120日漲200%）": ec == F3, "F1 妖股（P後回落≥50%）": (ec == F1) & (E["dd50"] > 0)}
    D1 = []
    for sg, dm in SEGA.items():
        for nm, gm in GRP.items():
            k = np.flatnonzero(gm & dm[ed]); k = k[defd[es[k], ed[k]]]
            D1.append({"段": sg, "對象": nm, "n": int(len(k)), "前60日曾量縮": float(any60[es[k], ed[k]].mean()) if len(k) else np.nan,
                       "t當日量縮": float(shr[es[k], ed[k]].mean()) if len(k) else np.nan})
        rows = defd & dm[None, :]
        D1.append({"段": sg, "對象": "全體股-日", "n": int(rows.sum()), "前60日曾量縮": float(any60[rows].mean()), "t當日量縮": float(shr[rows].mean())})
    D1 = pd.DataFrame(D1)
    log(f"[量縮] D1 完成 {time.time() - T0:.0f}s")
    # D2
    k1 = np.flatnonzero(ec == F1)
    evs = {}
    for i in k1:
        evs.setdefault(int(es[i]), []).append(int(ed[i]))
    D2r = []
    for s, ts in evs.items():
        idx = np.flatnonzero(bar[s]); sb = shr[s, idx]
        rl = np.zeros(len(idx), np.int64); lp = np.full(len(idx), -1, np.int64)
        for i in range(len(idx)):
            rl[i] = rl[i - 1] + 1 if (sb[i] and i > 0) else int(sb[i])
            lp[i] = i if sb[i] else (lp[i - 1] if i > 0 else -1)
        for t in ts:
            i = int(np.searchsorted(idx, t)); j = lp[i]
            if j < 0 or i - j > 250:
                D2r.append((t, np.nan, np.nan))
            else:
                D2r.append((t, float(rl[j]), float(i - j)))
    D2r = np.array(D2r, float)
    D2 = []
    for sg, dm in SEGA.items():
        m_ = dm[D2r[:, 0].astype(int)]; v = D2r[m_]; ok = np.isfinite(v[:, 1])
        D2.append({"段": sg, "F1事件": int(m_.sum()), "往回250根找不到量縮的比例": float(1 - ok.mean()) if len(v) else np.nan,
                   **{f"量縮持續根數_{p}": q for p, q in DS.qs(v[ok, 1], (25, 50, 75)).items()},
                   **{f"量縮結束到起漲隔幾根_{p}": q for p, q in DS.qs(v[ok, 2], (25, 50, 75)).items()},
                   "起漲當日仍在量縮（隔0根）比例": float((v[ok, 2] == 0).mean()) if ok.any() else np.nan})
    D2 = pd.DataFrame(D2)
    log(f"[量縮] D2 完成 {time.time() - T0:.0f}s")
    # D3
    D.DATA = S5.ST
    m50 = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy(float)).ffill().to_numpy()
    emax = t1 - 310
    rec = []; base = []
    for s in range(len(uni)):
        idx = np.flatnonzero(bar[s] & (np.arange(n) >= t0) & (np.arange(n) <= emax))
        if len(idx) == 0:
            continue
        allidx = np.flatnonzero(bar[s]); pos = np.searchsorted(allidx, idx)
        prev = np.where(pos > 0, allidx[np.maximum(pos - 1, 0)], -1)
        ent = idx[shr[s, idx] & (prev >= 0) & defd[s, np.maximum(prev, 0)] & ~shr[s, np.maximum(prev, 0)] & (h5[s, idx] >= 250)]
        okb = idx[(h5[s, idx] >= 250) & defd[s, idx]]
        if len(okb) == 0:
            continue
        stk = D.load_stock(uni.loc[s, "stock_id"], uni.loc[s, "market"], cal)
        cff = pd.Series(stk.df["close"].to_numpy(float)).ffill().to_numpy()
        f1 = np.sort(ed[(es == s) & (ec == F1)])
        for arr, out in ((ent, rec), (okb, base)):
            if len(arr) == 0:
                continue
            j = np.searchsorted(f1, arr); nx = np.where(j < len(f1), f1[np.minimum(j, max(len(f1) - 1, 0))] if len(f1) else 10 ** 9, 10 ** 9)
            became = nx <= arr + 250
            rx = cff[arr + 250] / cff[arr] - 1 - (m50[arr + 250] / m50[arr] - 1)
            out.append(np.c_[arr, became, np.where(became, nx - arr, -1), rx])
    rec = np.vstack(rec); base = np.vstack(base)
    D3 = []
    for sg, dm in SEGA.items():
        for nm, R_ in (("進入量縮日", rec), ("對照：全體股-日", base)):
            v = R_[dm[R_[:, 0].astype(int)]]
            if not len(v):
                continue
            b = v[:, 1] > 0; w = v[b, 2]; nb = v[~b]
            xs = nb[:, 3]; ok = np.isfinite(xs); xs = xs[ok]; mm = mon[nb[ok, 0].astype(int)]
            mu = float(xs.mean()) if len(xs) else np.nan
            se = float(np.sqrt((pd.Series(xs - mu).groupby(mm).sum() ** 2).sum()) / len(xs)) if len(xs) else np.nan
            D3.append({"段": sg, "對象": nm, "n": int(len(v)), "250日內變F1飆股比例": float(b.mean()), "等幾天_平均": float(w.mean()) if len(w) else np.nan,
                       **{f"等幾天_{p}": q for p, q in DS.qs(w, (25, 50, 75)).items()}, "沒變飆股_n": int(len(xs)),
                       "沒變飆股_對0050_平均": mu, "沒變飆股_對0050_下": mu - Z95 * se, "沒變飆股_對0050_上": mu + Z95 * se,
                       "沒變飆股_對0050_中位": float(np.median(xs)) if len(xs) else np.nan, "沒變飆股_落後0050比例": float((xs < 0).mean()) if len(xs) else np.nan,
                       "進入日範圍": f"{cal[int(v[:, 0].min())].date()}～{cal[int(v[:, 0].max())].date()}"})
    D3 = pd.DataFrame(D3)
    D1.to_csv(os.path.join(OUT, "shrink_D1.csv"), index=False, float_format="%.5g"); D2.to_csv(os.path.join(OUT, "shrink_D2.csv"), index=False, float_format="%.5g")
    D3.to_csv(os.path.join(OUT, "shrink_D3.csv"), index=False, float_format="%.5g")
    log(f"[量縮] 完成 {time.time() - T0:.0f}s")


# ═════════════ 報告與手機網頁 ═════════════
R_ = FT.R_; C_ = FT.C_; I_ = FT.I_


def _rd(name):
    p = os.path.join(OUT, name)
    return pd.read_csv(p) if os.path.exists(p) and os.path.getsize(p) > 2 else pd.DataFrame()


def report(st, log):
    SD = json.load(open(os.path.join(OUT, "summary_desc.json"), encoding="utf-8"))
    SF_ = json.load(open(os.path.join(OUT, "summary_feat.json"), encoding="utf-8"))
    G = _rd("grid.csv"); BUY = _rd("buyable.csv"); MG = _rd("maxgain.csv")
    SUMR = _rd("feat_summary.csv"); YR = _rd("yao_summary.csv"); ER = _rd("end_summary.csv"); ETS = _rd("end_trade_summary.csv")
    CUR = pd.read_csv(os.path.join(OUT, "curves.csv.gz"))
    chk = json.load(open(os.path.join(OUT, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT, "check.json")) else None
    prep_ = json.load(open(os.path.join(OUT, "check_prep.json"), encoding="utf-8"))
    evj = json.load(open(os.path.join(WORK6, "events.json"), encoding="utf-8"))
    NL = "\n"
    L = ["# PREREG飆股回推 seq6（近年版）：2021～2023 找、2024～2026 驗", "",
         f"- 分析開始時間：{st['分析開始']}",
         f"- 所用 seq6 登錄 sha：{st['seq6_sha']}（{st['seq6_登錄檔']}；去 pw1 行後驗過）",
         f"- {NOSEEN}",
         f"- ⚠ {DISCLOSE}。挑選照規則機械化執行，不因已知結果而改。",
         f"- 讀法寫死：{st['讀法寫死']}＋補寫 2026-09-29 18:53（台北）（U0～U12、U4b，見 researchSurge6.py 開頭；其餘照 seq5 S1～S19）｜資料 main {S5.MAIN_SHA[:10]}＋早年 {S5.EARLY_SHA[:10]}（接合；本件只用 2021 起的起漲日）｜g 網格照裁定 seq277", "",
         f"- 右截斷（登錄 §十一，協調者轉述）：資料尾視為 2026-08-31；t＋H、t＋h 超過的列不進該格（U4b）。⚠ seq6 登錄全文正文只到 §十之七、沒有 §十一 那一節，§十一 內容以裁定 seq279 §三 與協調者轉述為準",
         f"- 母體：{json.dumps(SD['段'], ensure_ascii=False)}｜起漲事件列 {evj['事件列']:,}（鏈從 {evj['起漲日範圍'][0]} 起算）", ""]
    P = SUMR[SUMR["進確認段"] == True].copy()
    nstand = len(SF_["站得住（飆股，確認）"])
    L += ["## 結論", "",
          f"- 飆股特徵：探索段（2021～2023）進確認段 **{len(P)}** 個級距 ⇒ 確認段（2024～2026-08，Bonferroni k＝{SF_['Bonferroni k（飆股）']}）站得住 **{nstand}** 個。",
          f"- 妖股（高點後回落 30／50／70%）站得住：" + "；".join(f"{x}：{len(v)} 個" for x, v in SF_["妖股 站得住"].items()),
          f"- 結束特徵站得住：{len(SF_['結束 站得住'])} 個（級距×結束套×k）",
          f"- **N_單筆 ＝ {SF_['N_單筆']}**（{json.dumps(SF_['N 組成'], ensure_ascii=False)}）", ""]
    L.append("## 一、飆股特徵：進確認段與確認結果"); L.append("")
    if len(P):
        L.append("| 特徵 | 探索 過門檻格 | 探索 提升中位 | 探索 涵蓋中位 | 確認 Bonf 下緣>1 格 | 確認 提升中位 | 站得住 | 確認 ③ 買了賺的持有區間 | 確認 ③ 對基準② 20／60／120／250 日 | 可買版 確認 Bonf 下緣>1 格 |")
        L.append("|---" * 10 + "|")
        P["_c"] = P["確認B_下緣>1格數"].fillna(0)
        for r in P.sort_values(["_c", "探索_下緣>1且涵蓋≥5%格數"], ascending=False).to_dict("records"):
            L.append(f"| {r['特徵']} | {I_(r.get('探索_下緣>1且涵蓋≥5%格數'))} | {R_(r.get('探索_提升中位'))} | {C_(r.get('探索_涵蓋率中位'))} | {I_(r.get('確認B_下緣>1格數'))} | {R_(r.get('確認_提升中位'))} | "
                     f"{'✅' if r.get('站得住（確認，Bonferroni）') is True else '✘'} | {r.get('確認_③買了賺的持有區間', '—')} | {'／'.join(C_(r.get(f'確認_③對基準②_{h}日')) for h in (20, 60, 120, 250))} | {I_(r.get('確認_可買_下緣>1格數'))} |")
    else:
        L.append("探索段沒有任何級距過門檻 ⇒ 確認段無可驗。")
    L.append(""); L.append("## 二、使用者原門檻版本（只描述，⛔ 不進挑選）"); L.append("")
    L.append("| 特徵 | 探索 提升中位 | 探索 涵蓋中位 | 探索 下緣>1且涵蓋≥5% 格 | 確認 提升中位 | 確認 下緣>1 格 | 確認 ③ 對基準② 60 日 | 確認 ③ 買了賺區間 |"); L.append("|---" * 8 + "|")
    for r in SUMR[SUMR["進挑選"] == False].to_dict("records"):
        L.append(f"| {r['特徵']} | {R_(r.get('探索_提升中位'))} | {C_(r.get('探索_涵蓋率中位'))} | {I_(r.get('探索_下緣>1且涵蓋≥5%格數'))} | {R_(r.get('確認_提升中位'))} | {I_(r.get('確認_下緣>1格數'))} | "
                 f"{C_(r.get('確認_③對基準②_60日'))} | {r.get('確認_③買了賺的持有區間', '—')} |")
    L.append(""); L.append("## 三、③ 全體基準（隔天開盤買、抱 h 日、扣 0.585%）"); L.append("")
    L.append("| 段 | 20 日 | 60 日 | 120 日 | 250 日 |"); L.append("|---|---|---|---|---|")
    for sg in SEG:
        g = CUR[(CUR["欄"] == "全體") & (CUR["段"] == sg)].set_index("h")
        L.append(f"| {sg} | " + " | ".join(f"{C_(g.loc[h, '淨報酬'])}（{C_(g.loc[h, '淨報酬_下'])}～{C_(g.loc[h, '淨報酬_上'])}）" for h in (20, 60, 120, 250)) + " |")
    L.append(""); L.append("## 四、妖股特徵（飆股事件內，對「高點後回落 x%」）"); L.append("")
    for x in (30, 50, 70):
        g = YR[(YR["回落"] == f"{x}%") & (YR["進確認段"] == True)]; okk = g[FT._flag(g, "站得住（確認）")]
        L.append(f"- 回落 {x}%：進確認段 {len(g)} 個；站得住 {len(okk)} 個" + (f"：{'、'.join(okk['特徵'])}" if len(okk) else ""))
    L.append(""); L.append("## 五、結束特徵（高點前 k 日 對 同一段漲勢中段）"); L.append("")
    for (x, kk), g in ER.groupby(["結束套", "k"]):
        g2 = g[g["進確認段"] == True]; okk = g2[FT._flag(g2, "站得住（確認）")]
        L.append(f"- {x}、k＝{kk}：進確認段 {len(g2)} 個；站得住 {len(okk)} 個" + (f"：{'、'.join(okk['特徵'])}" if len(okk) else ""))
    L.append(""); L.append("## 六、結束特徵的可交易（S19；一出現就賣 vs 抱到 h）"); L.append("")
    if len(ETS):
        c = ETS[ETS["段"] == "確認"]
        L.append(f"- 確認段：「一出現就賣」較好 {int((c['一出現就賣較好'] != '沒有').sum())} 個；「續抱」較好 {int((c['續抱較好'] != '沒有').sum())} 個；其餘分不出"); L.append("")
        L.append("| 特徵 | 確認：賣較好 | 確認：抱較好 | A−B 20／60／120／250 日 |"); L.append("|---|---|---|---|")
        for r in c.to_dict("records"):
            L.append(f"| {r['特徵']} | {r['一出現就賣較好']} | {r['續抱較好']} | " + "／".join(C_(r[f'A−B_{h}日']) for h in (20, 60, 120, 250)) + " |")
    else:
        L.append("- 沒有站得住的結束特徵 ⇒ 不做。")
    L.append(""); L.append("## 七、描述層（網格、最大漲幅、花幾天、買不買得到）"); L.append("")
    L.append("| 段 | 格 | 事件 | 比例 | 最大漲幅中位（H內） | 回落 30%／50% 比例 | t+1 鎖死 | t+1 處置中 |"); L.append("|---|---|---|---|---|---|---|---|")
    for sg in SEG:
        for H, g in ((20, 0.5), (60, 1.0), (120, 2.0), (250, 5.0)):
            r = G[(G["段"] == sg) & (G["H"] == H) & np.isclose(G["g"], g)]
            b = BUY[(BUY["段"] == sg) & (BUY["H"] == H) & np.isclose(BUY["g"], g)] if len(BUY) else BUY
            if len(r) and r.iloc[0]["事件"] > 0:
                r = r.iloc[0]; bb = b.iloc[0] if len(b) else {}
                L.append(f"| {sg} | {r['格']} | {int(r['事件'])} | {DS.PP_(r['比例'])} | {DS.P_(r['最大漲幅中位（H內）'], 0)} | {DS.P_(r['回落30%_比例'], 0)}／{DS.P_(r['回落50%_比例'], 0)} | "
                         f"{DS.P_(bb.get('t+1漲停鎖死', np.nan))} | {DS.P_(bb.get('t+1處置中', np.nan))} |")
    L.append(""); L.append("| 段 | g | 事件 | 最短花幾天 p25／中位／p75 |"); L.append("|---|---|---|---|")
    for sg in SEG:
        for g in (0.5, 1.0, 2.0):
            r = G[(G["段"] == sg) & (G["H"] == 250) & np.isclose(G["g"], g)]
            if len(r) and r.iloc[0]["事件"] > 0:
                r = r.iloc[0]
                L.append(f"| {sg} | {int(g * 100)}% | {int(r['事件'])} | " + "／".join(DS.N_(r[f'最短花幾天_p{p}']) for p in (25, 50, 75)) + " |")
    L.append(""); L.append("各格實際起漲日區間與定義域最後起漲日見 grid.csv（欄「實際起漲日最早／最晚」「定義域最後起漲日」）；例：")
    for sg in SEG:
        for H in (10, 60, 250):
            r = G[(G["段"] == sg) & (G["H"] == H) & np.isclose(G["g"], 1.0)]
            if len(r):
                r = r.iloc[0]; L.append(f"- {sg} {r['格']}：實際起漲日 {r['實際起漲日最早']}～{r['實際起漲日最晚']}｜定義域最後起漲日 {r['定義域最後起漲日']}")
    S1, S2, S3 = _rd("shrink_D1.csv"), _rd("shrink_D2.csv"), _rd("shrink_D3.csv")
    if len(S1):
        L.append(""); L.append("## 八、§九之一 量縮描述（只描述、不計 N；量縮 ＝ 20 日均額 ≤ 其前 120 日均額 × 0.7）"); L.append("")
        L.append("D1 起漲前有幾成出現過量縮"); L.append(""); L.append("| 段 | 對象 | n | 前 60 日曾量縮 | 起漲當日在量縮 |"); L.append("|---|---|---|---|---|")
        for r in S1.to_dict("records"):
            L.append(f"| {r['段']} | {r['對象']} | {int(r['n']):,} | {C_(r['前60日曾量縮'])} | {C_(r['t當日量縮'])} |")
        L.append(""); L.append("D2 F1 飆股起漲前最後一段量縮（K 棒根數）"); L.append(""); L.append("| 段 | F1 事件 | 往回 250 根找不到量縮 | 量縮持續 p25／中位／p75 | 量縮結束到起漲 p25／中位／p75 | 起漲當日仍量縮 |"); L.append("|---|---|---|---|---|---|")
        for r in S2.to_dict("records"):
            L.append(f"| {r['段']} | {int(r['F1事件']):,} | {C_(r['往回250根找不到量縮的比例'])} | " + "／".join(DS.N_(r[f'量縮持續根數_p{q}']) for q in (25, 50, 75)) + " | "
                     + "／".join(DS.N_(r[f'量縮結束到起漲隔幾根_p{q}']) for q in (25, 50, 75)) + f" | {C_(r['起漲當日仍在量縮（隔0根）比例'])} |")
        L.append(""); L.append("D3 反過來看：進入量縮後 250 日內變 F1 飆股的比例、等幾天、沒變的對 0050"); L.append("")
        L.append("| 段 | 對象 | n | 變飆股 | 等幾天 平均（p25／中位／p75） | 沒變飆股：對 0050 平均（95% CI）｜中位｜落後比例 | 進入日範圍 |"); L.append("|---|---|---|---|---|---|---|")
        for r in S3.to_dict("records"):
            L.append(f"| {r['段']} | {r['對象']} | {int(r['n']):,} | {C_(r['250日內變F1飆股比例'])} | {DS.N_(r['等幾天_平均'])}（" + "／".join(DS.N_(r[f'等幾天_p{q}']) for q in (25, 50, 75)) + "） | "
                     f"{C_(r['沒變飆股_對0050_平均'])}（{C_(r['沒變飆股_對0050_下'])}～{C_(r['沒變飆股_對0050_上'])}）｜{C_(r['沒變飆股_對0050_中位'])}｜{C_(r['沒變飆股_落後0050比例'])} | {r['進入日範圍']} |")
        L.append(""); L.append("⚠ D3 要 e＋310 ≤ 2026-08-31 才能完整判定 ⇒ 確認段的進入日只到 2025 年中；對照列 ＝ 同條件的全部股-日（不論是否量縮）")
    L.append(""); L.append("## 九、查核"); L.append("")
    L.append(f"- 沿用 s5work 前查核（check_prep.json）：可沿用＝{prep_['可沿用']}；抽 {len(prep_['抽樣'])} 檔重跑 seq5 stock() 逐位元相同、五等分抽 36 個相同")
    L.append(f"- 事件重建：定義域與 s5work 不同的股日 {evj['定義域與 s5work hdef 不同的股日']}；對照 seq5 全日曆鏈、不右截斷直接篩同範圍 {evj['對照：seq5 全日曆鏈、不右截斷，直接篩同範圍的事件列']:,} 列（本件 {evj['事件列']:,}）")
    if chk:
        L.append(f"- 獨立查核（researchSurge6_check.py ⇒ check.json）：錯誤 {chk['info'].get('錯誤數')} ｜ " + "；".join(f"{k}：{v}" for k, v in chk["info"].items() if k not in ("錯誤數", "抽樣")))
    L.append(""); L.append("檔案：feat_summary.csv｜feat_cells.csv.gz｜curves.csv.gz｜yao_summary.csv｜end_summary.csv｜end_trade*.csv｜grid*.csv｜maxgain.csv｜buyable.csv｜summary_*.json｜check*.json")
    open(os.path.join(OUT, "REPORT.md"), "w", encoding="utf-8").write(NL.join(L) + NL)
    page(st, SD, SF_, SUMR, YR, ER, ETS, CUR, G)
    log("[報告] REPORT.md、網頁完成")


def svg_curve(lines, title):
    """lines：[(名稱, 顏色, hs, mu, lo, hi)]；單位 %。"""
    W, H, pl, pr, pt, pb = 340, 190, 40, 8, 22, 26
    vals = [v for ln in lines for arr in ln[3:] for v in arr if np.isfinite(v)] + [0.0]
    lo_, hi_ = min(vals), max(vals)
    if hi_ - lo_ < 1e-9:
        hi_ = lo_ + 0.01
    pad = (hi_ - lo_) * 0.06; lo_ -= pad; hi_ += pad
    X = lambda h: pl + (h - 5) / 245 * (W - pl - pr)
    Y = lambda v: pt + (hi_ - v) / (hi_ - lo_) * (H - pt - pb)
    o = [f"<svg viewBox='0 0 {W} {H}' width='100%' role='img' aria-label='{html.escape(title)}'>",
         f"<text x='{pl}' y='14' font-size='12' fill='currentColor'>{html.escape(title)}</text>",
         f"<line x1='{pl}' x2='{W - pr}' y1='{Y(0):.1f}' y2='{Y(0):.1f}' stroke='#999' stroke-dasharray='3 3'/>"]
    for v in np.linspace(lo_, hi_, 4):
        o.append(f"<text x='{pl - 4}' y='{Y(v) + 4:.1f}' font-size='10' text-anchor='end' fill='#888'>{v * 100:.0f}%</text>")
    for h in (5, 60, 120, 180, 250):
        o.append(f"<text x='{X(h):.1f}' y='{H - 8}' font-size='10' text-anchor='middle' fill='#888'>{h}</text>")
    for nm, col, hs, mu, lo, hi in lines:
        ok = np.isfinite(mu) & np.isfinite(lo) & np.isfinite(hi)
        if ok.sum() < 2:
            continue
        up = " ".join(f"{X(h):.1f},{Y(v):.1f}" for h, v in zip(hs[ok], hi[ok])); dn = " ".join(f"{X(h):.1f},{Y(v):.1f}" for h, v in zip(hs[ok][::-1], lo[ok][::-1]))
        o.append(f"<polygon points='{up} {dn}' fill='{col}' opacity='0.15'/>")
        o.append(f"<polyline points='{' '.join(f'{X(h):.1f},{Y(v):.1f}' for h, v in zip(hs[ok], mu[ok]))}' fill='none' stroke='{col}' stroke-width='2'/>")
    lx = pl + 4
    for nm, col, *_ in lines:
        o.append(f"<rect x='{lx}' y='{pt + 2}' width='10' height='3' fill='{col}'/><text x='{lx + 13}' y='{pt + 7}' font-size='10' fill='currentColor'>{html.escape(nm)}</text>")
        lx += 13 + 11 * len(nm)
    o.append("</svg>")
    return "".join(o)


def page(st, SD, SF_, SUMR, YR, ER, ETS, CUR, G):
    CSS = open("backtest/list_yl13_hist.py", encoding="utf-8").read().split('CSS = """')[1].split('"""')[0]
    CSS += "\n.ok{background:#e8f5e9}td.l,th.l{text-align:left}small{color:#666}.warn{border-left:4px solid #d64045;padding:6px 10px;background:#fff4f4}.chart{margin:8px 0 16px}"
    P = SUMR[SUMR["進確認段"] == True].copy()
    okf = FT._flag(P, "站得住（確認，Bonferroni）")
    Hh = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
          "<title>飆股回推 近年版</title>", f"<style>{CSS}</style></head><body><main>", "<h1>飆股回推 seq6（近年版）：2021–23 找、2024–26 驗</h1>",
          f"<p class='lead'>分析開始 {html.escape(st['分析開始'])}｜seq6 sha {st['seq6_sha']}｜{NOSEEN}。</p>",
          f"<p class='warn'>⚠ {html.escape(DISCLOSE)}。挑選照規則機械化執行，不因已知結果而改。資料尾截在 2026-08-31。</p>",
          f"<p class='note'>每個特徵分五組（或是／否），在 250 種飆股定義（10～250 天內漲 50%～10 倍以上）各算一次：<b>提升倍數</b>＝有這特徵的股票變飆股的機率是一般的幾倍；"
          f"<b>涵蓋率</b>＝飆股裡事先有這特徵的佔幾成。2021–23 至少一半定義裡「提升倍數確定 ＞ 1、涵蓋率 ≥ 5%」才挑出來，2024–26 再驗（一起比的校正版）。"
          f"<b>買了賺不賺</b>＝隔天開盤買、抱 5～250 天，扣來回成本 0.585% 後，比全體、比前 20 天漲跌差不多的股票多賺多少。檢定數 N＝{SF_['N_單筆']}。</p>",
          f"<h2>一、2021–23 挑出 {len(P)} 個，2024–26 站得住 {int(okf.sum())} 個</h2>"]
    if len(P):
        Hh.append("<div class='wrap'><table><tr><th class='l'>特徵</th><th>提升倍數（中位）<br>21–23／24–26</th><th>涵蓋率</th><th>站得住</th><th>買了賺（24–26）</th></tr>")
        P["_c"] = P["確認B_下緣>1格數"].fillna(0)
        for r in P.sort_values("_c", ascending=False).to_dict("records"):
            s_ = r.get("站得住（確認，Bonferroni）") is True
            Hh.append(f"<tr class='{'ok' if s_ else ''}'><td class='l'>{html.escape(r['特徵'])}</td><td>{R_(r.get('探索_提升中位'))}／{R_(r.get('確認_提升中位'))}</td><td>{C_(r.get('確認_涵蓋率中位'))}</td>"
                      f"<td>{'✅' if s_ else '✘'}<br><small>{I_(r.get('確認B_下緣>1格數'))}/250</small></td><td>{html.escape(str(r.get('確認_③買了賺的持有區間', '—')))}</td></tr>")
        Hh.append("</table></div>")
    else:
        Hh.append("<p>2021–23 沒有任何特徵過門檻。</p>")
    Hh.append("<h2>二、買了賺不賺：扣成本後的淨報酬曲線（2024–26）</h2><p class='note'>橫軸：持有交易日（5～250）；線＝平均、淡色帶＝信賴區間（挑出者用校正版）。"
              "紅＝比全體多賺（扣成本）；藍＝比前 20 天漲跌差不多的股票多賺（扣成本）。在 0 以上且帶子不碰 0 才算賺。</p>")
    g = CUR[(CUR["欄"] == "全體") & (CUR["段"] == "確認")].sort_values("h")
    Hh.append("<div class='chart'>" + svg_curve([("全體 隔天買 扣成本", "#555", g["h"].to_numpy(float), g["淨報酬"].to_numpy(float), g["淨報酬_下"].to_numpy(float), g["淨報酬_上"].to_numpy(float))], "全體（對照）") + "</div>")
    show = P.sort_values("_c", ascending=False).head(12) if len(P) else P
    for r in show.to_dict("records"):
        c = CUR[(CUR["欄"] == r["欄"]) & (CUR["碼"] == r["碼"]) & (CUR["段"] == "確認")].sort_values("h")
        hs = c["h"].to_numpy(float)
        Hh.append("<div class='chart'>" + svg_curve([("對全體", "#d64045", hs, c["對全體"].to_numpy(float) - COST, c["對全體_下"].to_numpy(float) - COST, c["對全體_上"].to_numpy(float) - COST),
                                                     ("對基準②", "#2b6cb0", hs, c["對基準②"].to_numpy(float) - COST, c["對基準②_下"].to_numpy(float) - COST, c["對基準②_上"].to_numpy(float) - COST)],
                                                    r["特徵"]) + "</div>")
    if len(P) > 12:
        Hh.append(f"<p class='note'>只畫確認段格數最多的 12 個；其餘 {len(P) - 12} 個在 curves.csv.gz。</p>")
    Hh.append("<h2>三、你給的原門檻（只描述）</h2><div class='wrap'><table><tr><th class='l'>特徵</th><th>提升倍數 21–23／24–26</th><th>涵蓋率</th><th>買了賺（24–26）</th></tr>")
    for r in SUMR[SUMR["進挑選"] == False].to_dict("records"):
        Hh.append(f"<tr><td class='l'>{html.escape(r['特徵'])}</td><td>{R_(r.get('探索_提升中位'))}／{R_(r.get('確認_提升中位'))}</td><td>{C_(r.get('確認_涵蓋率中位'))}</td><td>{html.escape(str(r.get('確認_③買了賺的持有區間', '—')))}</td></tr>")
    Hh.append("</table></div>")
    Hh.append("<h2>四、妖股與結束</h2><div class='wrap'><table><tr><th class='l'>族</th><th>挑出</th><th>站得住</th></tr>")
    for x in (30, 50, 70):
        g = YR[(YR["回落"] == f"{x}%") & (YR["進確認段"] == True)]; okk = g[FT._flag(g, "站得住（確認）")]
        Hh.append(f"<tr><td class='l'>高點後跌 {x}%</td><td>{len(g)}</td><td>{html.escape('、'.join(okk['特徵'])) or '沒有'}</td></tr>")
    for (x, kk), g in ER.groupby(["結束套", "k"]):
        g2 = g[g["進確認段"] == True]; okk = g2[FT._flag(g2, "站得住（確認）")]
        Hh.append(f"<tr><td class='l'>結束（{x}）高點前 {kk} 天</td><td>{len(g2)}</td><td>{html.escape('、'.join(okk['特徵'])) or '沒有'}</td></tr>")
    Hh.append("</table></div>")
    if len(ETS):
        c = ETS[ETS["段"] == "確認"]
        Hh.append("<h2>五、結束特徵一出現就賣，比抱著好嗎？（2024–26）</h2><div class='wrap'><table><tr><th class='l'>特徵</th><th>賣較好</th><th>抱較好</th><th>差 60／250 日</th></tr>")
        for r in c.to_dict("records"):
            Hh.append(f"<tr><td class='l'>{html.escape(r['特徵'])}</td><td>{html.escape(r['一出現就賣較好'])}</td><td>{html.escape(r['續抱較好'])}</td><td>{C_(r['A−B_60日'])}／{C_(r['A−B_250日'])}</td></tr>")
        Hh.append("</table></div>")
    S3 = _rd("shrink_D3.csv"); S1 = _rd("shrink_D1.csv")
    if len(S3):
        Hh.append("<h2>六、量縮之後（2021–26，只描述）</h2><p class='note'>量縮＝20 日均額 ≤ 前 120 日均額的 7 成。「進入量縮」那天起 250 個交易日內，有幾成變成 60 天漲一倍的飆股；沒變的，同期比 0050 多或少多少。</p>"
                  "<div class='wrap'><table><tr><th class='l'>段／對象</th><th>變飆股</th><th>等幾天（中位）</th><th>沒變的對 0050（平均）</th></tr>")
        for r in S3.to_dict("records"):
            Hh.append(f"<tr><td class='l'>{r['段']}<br><small>{html.escape(r['對象'])}</small></td><td>{C_(r['250日內變F1飆股比例'])}</td><td>{DS.N_(r['等幾天_p50'])}</td><td>{C_(r['沒變飆股_對0050_平均'])}</td></tr>")
        Hh.append("</table></div>")
        f1 = S1[(S1["段"] == "全期")]
        Hh.append("<div class='wrap'><table><tr><th class='l'>起漲前 60 日曾量縮</th><th>比例</th></tr>" + "".join(f"<tr><td class='l'>{html.escape(r['對象'])}</td><td>{C_(r['前60日曾量縮'])}</td></tr>" for r in f1.to_dict("records")) + "</table></div>")
    Hh.append("<h2>七、飆股有多少（每萬個股-日的起漲事件）</h2><div class='wrap'><table><tr><th>段</th><th>60 天漲 1 倍</th><th>120 天漲 2 倍</th><th>250 天漲 5 倍</th></tr>")
    for sg in SEG:
        cells = []
        for H_, g_ in ((60, 1.0), (120, 2.0), (250, 5.0)):
            r = G[(G["段"] == sg) & (G["H"] == H_) & np.isclose(G["g"], g_)]
            cells.append("—" if not len(r) else f"{r.iloc[0]['比例'] * 1e4:.1f}<br><small>{int(r.iloc[0]['事件'])} 件</small>")
        Hh.append(f"<tr><td>{sg}</td>" + "".join(f"<td>{x}</td>" for x in cells) + "</tr>")
    Hh.append("</table></div><p class='note'>完整 250 格、最大漲幅分佈、花幾天、買不買得到見 grid.csv、maxgain.csv、buyable.csv。</p></main></body></html>")
    open(os.path.join(OUT, "飆股回推seq6_近年版.html"), "w", encoding="utf-8").write("\n".join(Hh))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=("prep", "events", "desc", "shrink", "feat", "endtrade", "report"), required=True)
    ap.add_argument("--procs", type=int, default=2); ap.add_argument("--sha", default=""); ap.add_argument("--start", default="")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    logf = open(os.path.join(OUT, f"run_{a.stage}.log"), "w", encoding="utf-8"); T0 = time.time()

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    if a.stage in ("prep", "events"):
        log(f"===== researchSurge6 {a.stage}｜讀法寫死 {READ_FIXED}｜不算任何提升倍數 =====")
        (prep if a.stage == "prep" else build_events)(a, log)
    else:
        st = gate(a)
        log(f"===== researchSurge6 {a.stage}｜分析開始 {st['分析開始']}｜seq6 sha {st['seq6_sha']}｜{NOSEEN} =====")
        {"desc": run_desc, "shrink": run_shrink, "feat": run_feat, "endtrade": run_endtrade, "report": report}[a.stage](st, log)
    log(f"[完] {time.time() - T0:.0f}s")


if __name__ == "__main__":
    main()
