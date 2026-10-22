# -*- coding: utf-8 -*-
"""pth10_daily（52 週新高 10 檔／高10 每日名單）對帳與 fixture——回測線開發子代理，2026-10-21。
⛔ 只對帳（與既有回測結果比相同）、⛔ 不算新的報酬。單一階段 ≤ 10 分鐘；大檔快取在 --work（預設 ~/pth10work）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.pth10_daily_check --stage world    # ① 世界（約 7 分）
    ... --stage rank      # ② 排序／進場狀態（約 5 分）      ... --stage replay    # ③ 事件、逐月回放、名單前一晚一致率（約 3 分）
    ... --stage fixture   # ④ 合成日曆 fixture（秒）          ... --stage dry       # ⑤ 2026-10-20 真實快照乾跑（寫暫存 md／暫存狀態夾）
    ... --stage e2e --day 0｜1｜2｜3   # ⑥ 端到端（起點假設 2026-04；9/29、9/30、10/01、10/20 四個真快照依序跑；day 0、1 各約 5 分）
輸出 backtest/resultsPTH10daily/check_<階段>.json

① 世界：pth10_daily.live_world 用 rerun17 快照（H2D，2026-09-24）全母體重建 ⇒ 名單、O／PV／TRD／UPL／DNL／C 與 ~/rluwork/world_main.pkl 逐位元相同；
   壞根 BADPOS 與 ~/crashwork/bad_main.pkl（load_bars 壞根 ∪ 減資／面額）相同。存 W 到 work/h2d_world.pkl。
② 排序：pth10_daily.rank_pass（單股世界 ⇒ researchPTH_freq.stock_job）全母體 ⇒ 每個形成月 排序母體、PTH、入選、跳月進場狀態 與已提交
   resultsPTH/freq/events_主.csv.gz 相同（PTH 容差 5e−7）；events/trades_主_跳月 的 PTH 與 pth10_daily.pth_keys(PTH) 逐位元相同；
   同時算「前一晚待定」進場狀態（EP 換成 e−1）。存 work/h2d_rank.pkl。
③ 回放：事件 ＝ pth10_daily.assemble（②的保留事件、代號序、R9 同值種子）⇒ 與 researchPTHpf.load_events（讀已提交事件檔）全欄逐位元相同、補位順序相同；
   pth10_daily.window_sim（t0＝0）⇒ researchPTHn.trades_df 全文 ＝ resultsPTHn/trades_主_N10.csv.gz、權益 ＝ eq_主.npz N10_eq（逐位元）；
   每批只取前 20 名（D4）⇒ 買賣與權益同全名單；逐月（2017-03～最近）月初持股名單 ＝ trades_主_N10 推出的持股、已出場筆 ＝ resultsPTH10path/path_trades.csv（主）；
   描述（⛔ 不判）：每批「前一晚名單」（待定事件、合成的明天）與實際補進名單相同的比例。
④ fixture：①月初前一晚出名單 ②非買賣日無【LINE】 ③第 6 個曆月最後交易日賣出（含月底遇平日休市；researchPTH.exit_positions 對照）
   ④空格放 0050 ⑤2 萬換算股數 ⑥put 只換第十節。
⑤ 乾跑：資料日 2026-10-20（main dbfb96cb81）⇒ 平日段落、--preview-buy（2026-11 名單用 2026-09 底排序）段落；寫到 work/dry（⛔ 不碰 resultsDaily）。
── D10 同分排序 F9（使用者 10/21；2026-10-21 加，既有各項不動）──
④ fixture 加 ⑨：同分群 F9 排序／F9 缺值排最後／F9 同分走抽籤／抽籤模式 ＝ batch_order／設定鍵缺省 ＝ 抽籤／LINE 行 F9 句與 NOTE_TIE／無同分群不算分數。
⑦ f9replay（約 5 分；要先有 ① ② 的 work 快取）：pth10_daily.f9_ctx／f9_members／tie_keys（researchPTH10tie_freq 同一批函式）逐月重算主世界同分群 F9
   ⇒ 與 resultsPTH10tie/freq/members_主.csv.gz（F9ok、F9、F6／F7／Q）及 resultsPTH10tie/main/keys_主.csv.gz（T1 算不出、T1 鍵、原 rk）逐列相同；
   (a) 引擎：次序 ＝ researchPTH10tie_freq.order_of（rk 位置化 ＝ researchPTH10tie.ev_with_order）⇒ pth10_daily.window_sim 交易檔全文 ＝ trades_主_T1.csv.gz、
       逐月（2016-03～最近）月初持股逐檔相同；
   (b) 使用者版：每批 pth10_daily.user_order（F9）＋ pick_user（跳過持有中）⇒ 前 k 檔 ＝ T1 交易檔當月買進（k ＝ 當月實買數）；抽籤模式同式 ＝ trades_主_N10。
⑧ f9dry --tie 抽籤｜F9（各約 1～6 分）：最新真快照（~/h2data/<main sha>，資料日 2026-10-20）--preview-buy --tie ⇒ 11/2 首批（2026-09-30 排序）10 檔與備位；
   F9 那次並列抽籤；寫到 work/f9dry（⛔ 不碰 resultsDaily）；策略鎖前後 --check。
── D11 第三本「F9 照規則」、D12 LINE 行移出五句（裁定 seq440 §二、使用者 10/21；2026-10-22 加）──
④ ① 與 ⑨c 改驗：LINE 行只留名單內容（含備位）、開頭不變；五句在下一行「  - 註：」（不帶【LINE】）。
⑦ 加 (c)：pth10_daily.f9_rows（同批 rk ＝ F9 次序位置、前 20 名依 F9）＋ assemble ＋ window_sim ⇒ 權益／持股數 ＝ resultsPTH10tie/main/raw_主.npz
   T1_eq／T1_nh（逐位元）、交易檔 ＝ trades_主_T1。
⑨ book3 --day 0｜1（各約 5 分；要先有 ⑥ 的 work/e2e 快取與 ⑧ 的財報籌碼資料夾）：起點假設 2026-04，9/30、10/01 兩個真快照連跑 ⇒
   positions.csv／positions_user.csv／positions_f9.csv 三本並存、equity_f9 與 equity 同日期、只追加（day0 列凍結）、LINE 行不含五句、註行有五句。
"""
from __future__ import annotations

import argparse
import gzip
import io
import json
import os
import pickle
import shutil
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
from backtest import pth10_daily as H                       # noqa: E402
from backtest import researchPTHpf as M                     # noqa: E402
from backtest import researchPTHn as PN                     # noqa: E402  trades_df
from backtest import researchPTH as PTH                     # noqa: E402
from backtest import researchPTH_freq as PT                 # noqa: E402
from backtest import rerun17 as RR                          # noqa: E402

OUT = "backtest/resultsPTH10daily"
DRY_SHA = "dbfb96cb81a7d3032e07fe47d1aeb5f0230545fa"
LOGS: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOGS.append(s)


def save(stage, J):
    os.makedirs(OUT, exist_ok=True)
    J["log"] = LOGS
    json.dump(J, open(os.path.join(OUT, f"check_{stage}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)


def eqa(a, b):
    a = np.asarray(a); b = np.asarray(b)
    if a.shape != b.shape:
        return False
    if a.dtype.kind == "f" or b.dtype.kind == "f":
        return bool(np.array_equal(a.astype(float), b.astype(float), equal_nan=True))
    return bool(np.array_equal(a, b))


# ═════════════ ① 世界 ═════════════
def st_world(a):
    J = {"階段": "world"}
    t0 = time.time()
    W = H.live_world(RR.H2D, log, None, a.procs, None)
    Z = pickle.load(open(os.path.expanduser("~/rluwork/world_main.pkl"), "rb"))
    n0 = W["n0"]
    res = {"名單": list(Z["sids"]) == W["sids"]}
    if res["名單"]:
        for k, zk, cut in (("O", "o", False), ("PV", "pv", False), ("TRD", "trd", True), ("UPL", "upl", True), ("DNL", "dnl", True), ("C", "c", False)):
            zz = np.asarray(Z[zk]); zz = zz[:, :n0] if cut else zz
            res[k] = eqa(W[k], zz.astype(W[k].dtype))
    else:
        res["名單差"] = {"只在重建": sorted(set(W["sids"]) - set(Z["sids"]))[:20], "只在快取": sorted(set(Z["sids"]) - set(W["sids"]))[:20]}
    B = pickle.load(open(os.path.expanduser("~/crashwork/bad_main.pkl"), "rb"))
    nb = [s for s in W["sids"] if s in B and W["BADPOS"][s] != (set(int(x) for x in B[s][0]) | set(int(x) for x in B[s][1]))]
    res["壞根(與crashwork不同檔數)"] = len(nb); res["壞根不同例"] = nb[:10]
    res["crashwork沒有的檔"] = [s for s in W["sids"] if s not in B][:10]
    J["結果"] = res
    ok = all(v for k, v in res.items() if isinstance(v, bool)) and not nb
    J["通過"] = bool(ok)
    log(f"[①世界] {res}｜{'✅' if ok else '⛔'}｜{time.time() - t0:.0f}s")
    os.makedirs(a.work, exist_ok=True)
    pickle.dump(W, open(os.path.join(a.work, "h2d_world.pkl"), "wb"), protocol=5)
    save("world", J)
    return ok


# ═════════════ ② 排序 ═════════════
def st_rank(a):
    J = {"階段": "rank"}
    t0 = time.time()
    D_ = RR.H2D
    H.D.DATA = D_; cal = H.D.load_calendar()
    ME, MK = H.month_ends_live(cal, None)
    EP2 = PT.entry_pos(cal, MK, 2)
    pend = {int(j): int(e) - 1 for j, e in enumerate(EP2) if e > 0}
    R = H.rank_pass(D_, cal, ME, MK, H.universe(D_)[0].keys(), a.procs, pend)
    log(f"[②排序] rank_pass {len(R)} 檔｜{time.time() - t0:.0f}s")
    dates = np.array([str(d.date()) for d in cal])
    jmap = {dates[p]: j for j, p in enumerate(ME)}
    ev = pd.read_csv("backtest/resultsPTH/freq/events_主.csv.gz", dtype={"sid": str})
    bad = {"列數": 0, "排序母體": 0, "PTH": 0, "入選": 0, "跳月_st": 0}
    rows = []
    for j in sorted(set(ev["形成月底"].map(jmap))):
        df, meta = H.rank_from(R, j)
        e_ = ev[ev["形成月底"] == dates[ME[j]]].sort_values("sid")
        df = df.sort_values("代號").reset_index(drop=True)
        if list(df["代號"]) != list(e_["sid"]):
            bad["列數"] += 1; continue
        if meta["排序母體"] != int(e_["排序母體"].iloc[0]):
            bad["排序母體"] += 1
        if (np.abs(df["PTH"].to_numpy() - e_["PTH"].to_numpy(float)) > 5e-7).any():
            bad["PTH"] += 1
        if (df["入選"].to_numpy(bool) != e_["入選"].to_numpy(bool)).any():
            bad["入選"] += 1
        st2 = np.array([PT.ENAME.get(int(R[s]["ENT2"][j]), "") for s in df["代號"]])
        if (st2 != e_["跳月_st"].to_numpy()).any():
            bad["跳月_st"] += 1
        rows.append(j)
    tr = pd.read_csv("backtest/resultsPTH/events/trades_主_跳月.csv.gz", dtype={"sid": str}, float_precision="round_trip")
    live = np.array([R[s]["PTH"][jmap[f]] for s, f in zip(tr["sid"], tr["形成月底"])])
    ulp = np.abs(live - tr["PTH"].to_numpy(float)) / np.spacing(np.abs(live))
    keyeq = H.pth_keys(live) == tr["PTH"].to_numpy(float)
    pbad = int((~keyeq).sum())
    J["結果"] = {"形成月數": len(set(ev["形成月底"])), "逐月不符": bad, "事件筆": int(len(tr)),
                 "trades_主_跳月 PTH：全精度逐位元相同筆": int((ulp == 0).sum()), "全精度差 1 ulp 筆": int((ulp == 1).sum()),
                 "pth_keys（pandas csv 存讀）後逐位元相同筆": int(keyeq.sum()),
                 "註": "事件檔的 PTH 是頻率表 csv 經 pandas 預設剖析器讀回的值（最後一位可差 1 ulp）⇒ pth10_daily.pth_keys 照同一存讀過程"}
    ok = not any(bad.values()) and pbad == 0
    J["通過"] = bool(ok)
    log(f"[②排序] {J['結果']}｜{'✅' if ok else '⛔'}｜{time.time() - t0:.0f}s")
    pickle.dump({"R": R, "pend": pend}, open(os.path.join(a.work, "h2d_rank.pkl"), "wb"), protocol=5)
    save("rank", J)
    return ok


# ═════════════ ③ 回放 ═════════════
def rows_from(R, W, js, pre_k=None, pend_j=None):
    """②的排序結果 ⇒ pth10_daily 事件列（每批代號序、R9 同值種子、前 pre_k 名算出場；None ＝ 全部）。"""
    EP2 = W["EP"][2]; rows = []
    for j in js:
        df, _ = H.rank_from(R, j)
        sel = df[df["入選"] == 1].sort_values("代號")
        fld = "ENT2p" if j == pend_j else "ENT2"
        if j == pend_j:
            keep = [(s, p) for s, p in zip(sel["代號"], sel["PTH"]) if int(R[s][fld][j]) not in (PT.E_BAD, PT.E_NA, PT.E_TAIL)]
        else:
            keep = [(s, p) for s, p in zip(sel["代號"], sel["PTH"]) if int(R[s][fld][j]) == PT.E_KEEP]
        rk, o_ = H.batch_order([s for s, _ in keep], [p for _, p in keep], j)
        pre = np.ones(len(keep), bool) if pre_k is None else np.zeros(len(keep), bool)
        if pre_k is not None:
            pre[o_[:pre_k]] = True
        for q, (s, p) in enumerate(keep):
            rows.append({"sid": s, "j": j, "e": int(EP2[j]), "pth": float(p), "rk": float(rk[q]), "pre": bool(pre[q]), "pend": j == pend_j})
    return rows


def st_replay(a):
    J = {"階段": "replay", "結果": {}}
    t0 = time.time()
    W = pickle.load(open(os.path.join(a.work, "h2d_world.pkl"), "rb"))
    Rk = pickle.load(open(os.path.join(a.work, "h2d_rank.pkl"), "rb")); R = Rk["R"]
    H.D.DATA = W["data"]; PT._G[H.WN] = W
    RES = H.pool_map(PTH.stock_job, [(H.WN, s) for s in W["sids"]], a.procs)
    RES = {k: v for k, v in RES.items() if v is not None}
    log(f"[③] PTH.stock_job {len(RES)} 檔｜{time.time() - t0:.0f}s")
    EP2 = W["EP"][2]; ME = W["ME"]; dates = W["dates"]
    js = [j for j in range(len(ME)) if EP2[j] >= 0]
    ok_all = True
    # 事件：pth10_daily.assemble vs researchPTHpf.load_events
    rows = rows_from(R, W, js)
    ev = H.assemble(W, rows, RES)
    ev["form"] = np.array([dates[ME[j]] for j in ev["jm"]], object)
    ref, info = M.load_events(W, "主", "跳月", RES)
    o_ = np.lexsort((ev["j"], ev["e"]))
    diff = {}
    for k in ("sid", "j", "jm", "e", "X", "typ", "R", "sd", "sale", "P", "px", "pth", "rk", "form"):
        mine = ev[k][o_]
        same = (list(mine) == list(ref[k])) if k in ("sid", "form") else eqa(mine, ref[k])
        if not same:
            diff[k] = True
    om = np.lexsort((ev["rk"][o_], -ev["pth"][o_], ev["e"][o_])); orf = np.lexsort((ref["rk"], -ref["pth"], ref["e"]))
    J["結果"]["事件 vs researchPTHpf.load_events"] = {"列": int(len(rows)), "參考列": info["列"], "不同欄": list(diff),
                                                    "PTH（pth_keys）逐位元相同列": int((ev['pth'][o_] == ref['pth']).sum()),
                                                    "補位順序 (e, −PTH, rk) 相同": bool((om == orf).all())}
    ok = not diff and len(rows) == info["列"] and bool((om == orf).all())
    ok_all &= ok
    log(f"[③事件] {J['結果']['事件 vs researchPTHpf.load_events']}｜{'✅' if ok else '⛔'}")
    # 全名單模擬 vs resultsPTHn N10
    S, n_win, n_real = H.window_sim(W, ev, 0, False)
    TD = PN.trades_df(W, ev, S)
    with gzip.open("backtest/resultsPTHn/trades_主_N10.csv.gz", "rt", encoding="utf-8") as fh:
        orig = fh.read()
    OD = pd.read_csv(io.StringIO(orig), dtype=str, keep_default_na=False)
    txt = PN.df_text(TD, "%.17g")
    Z = np.load("backtest/resultsPTHn/eq_主.npz")
    r1 = {"交易檔全文相同": txt == orig, "筆數": len(S["buys"]), "權益逐位元": eqa(S["eq"], Z["N10_eq"]), "持股數逐位元": eqa(S["nh"], Z["N10_nh"])}
    J["結果"]["全名單 vs resultsPTHn trades_主_N10／eq"] = r1
    ok = all(r1[k] for k in ("交易檔全文相同", "權益逐位元", "持股數逐位元")); ok_all &= ok
    log(f"[③全名單] {r1}｜{'✅' if ok else '⛔'}")
    # 前 20 名（D4）
    rows20 = rows_from(R, W, js, H.K_PRE)
    ev20 = H.assemble(W, rows20, RES)
    S20, _, _ = H.window_sim(W, ev20, 0, False)
    key = lambda S_, e_: [(t, e_["sid"][S_["q"][q]], amt) for t, q, amt in S_["buys"]]
    keys = lambda S_, e_: [(t, e_["sid"][S_["q"][q]], proc) for t, q, amt, proc in S_["sells"]]
    r2 = {"買進相同": key(S20, ev20) == key(S, ev), "賣出相同": keys(S20, ev20) == keys(S, ev), "權益逐位元": eqa(S20["eq"], S["eq"])}
    J["結果"]["前20名截斷 vs 全名單"] = r2
    ok = all(r2.values()); ok_all &= ok
    log(f"[③前20名] {r2}｜{'✅' if ok else '⛔'}")
    # 逐月持股
    T = pd.read_csv("backtest/resultsPTHn/trades_主_N10.csv.gz", dtype=str, keep_default_na=False)
    cal = W["cal"]
    firsts = [t for t in range(1, len(cal)) if cal[t].month != cal[t - 1].month and str(cal[t].date()) >= "2017-03-01"]
    sl = {q: t for t, q, amt, proc in S["sells"]}
    nmon = 0; nbad = 0; nsm = 0; badm = []
    for t in firsts:
        d = dates[t]
        ref_h = sorted(s for s, b, x in zip(T["sid"], T["買進日"], T["賣出日"]) if b <= d and (x == "" or x > d))
        mine_h = sorted(ev["sid"][S["q"][q]] for tb, q, amt in S["buys"] if tb <= t and (q not in sl or sl[q] > t))
        nmon += 1; nsm += len(ref_h)
        if ref_h != mine_h:
            nbad += 1; badm.append(d)
    P = pd.read_csv("backtest/resultsPTH10path/path_trades.csv", dtype=str)
    P = P[P["世界"] == "主"]
    pset = set(zip(P["sid"], P["買進日"], P["賣出日"]))
    mset = {(ev["sid"][S["q"][q]], dates[tb], dates[sl[q]]) for tb, q, amt in S["buys"] if q in sl and dates[tb] >= "2017-03-02"}
    r3 = {"月數": nmon, "期間": f"{dates[firsts[0]]}～{dates[firsts[-1]]}", "股月數": nsm, "不同月數": nbad, "不同月": badm[:10],
          "已出場筆 vs researchPTH10_path（主）": {"本模組": len(mset), "path_trades": len(pset), "相同": mset == pset}}
    J["結果"]["逐月持股（月初買進後）"] = r3
    ok = nbad == 0 and mset == pset; ok_all &= ok
    log(f"[③逐月] {r3}｜{'✅' if ok else '⛔'}")
    # 描述：前一晚名單 vs 實際補進
    buys_at = {}
    for tb, q, amt in S["buys"]:
        buys_at.setdefault(tb, []).append(ev["sid"][S["q"][q]])
    stat = []
    for jb in js:
        eb = int(EP2[jb])
        if dates[eb] < "2017-03-01":
            continue
        prior = [j for j in js if EP2[j] < eb]
        rws = rows_from(R, W, prior, H.K_PRE) + rows_from(R, W, [jb], H.K_PRE, pend_j=jb)
        evb = H.assemble(W, rws, RES)
        evb["sale"] = np.where(evb["sale"] >= eb, -1, evb["sale"])
        pm = evb["pend"]
        for q in np.flatnonzero(pm):
            evb["e"][q] = eb
            if evb["j"][q] >= 0:
                evb["P"][q] = W["CM"][evb["j"][q], eb - 1]
        Wb = {"n0": eb, "CM": W["CM"][:, :eb], "Bc": W["Bc"][:eb], "Bo": W["Bo"][:eb]}
        Sb, _, nr = H.window_sim(Wb, evb, 0, True)
        plan = sorted(evb["sid"][Sb["q"][q]] for t, q, amt in Sb["buys"] if t == nr)
        act = sorted(buys_at.get(eb, []))
        drop = int(sum(1 for r in rows_from(R, W, [jb], None, pend_j=jb)) - sum(1 for r in rows_from(R, W, [jb])))
        stat.append({"進場日": dates[eb], "名單": plan, "實際": act, "相同": plan == act, "名單外": len(set(act) - set(plan)), "待定比實際多": drop})
    sd = pd.DataFrame(stat)
    hb = sd["實際"].map(len) > 0
    r4 = {"批數": int(len(sd)), "名單＝實際 批數": int(sd["相同"].sum()), "有實際買進的批": int(hb.sum()), "有實際買進的批中 名單＝實際": int(sd.loc[hb, "相同"].sum()),
          "有買進且候選有人在 e 剔除的批": int((hb & (sd["待定比實際多"] > 0)).sum()),
          "其中 名單＝實際": int(sd.loc[hb & (sd["待定比實際多"] > 0), "相同"].sum()),
          "不同批的平均名單外檔數": float(sd.loc[~sd["相同"], "名單外"].mean()) if (~sd["相同"]).any() else 0.0,
          "待定＝實際事件數的批中 名單＝實際": f"{int(sd.loc[sd['待定比實際多'] == 0, '相同'].sum())}／{int((sd['待定比實際多'] == 0).sum())}",
          "不同批（前 12）": sd.loc[~sd["相同"], ["進場日", "名單外", "待定比實際多"]].head(12).to_dict("records")}
    J["結果"]["描述：前一晚名單 vs 實際補進（⛔ 不判）"] = r4
    log(f"[③描述] {r4}")
    J["通過"] = bool(ok_all)
    log(f"[③回放] {'✅ 全過' if ok_all else '⛔ 有不符'}｜{time.time() - t0:.0f}s")
    save("replay", J)
    return ok_all


# ═════════════ ④ fixture ═════════════
def synth_world(nS, n0, seed=3):
    rng = np.random.default_rng(seed)
    CM = 20 * np.exp(np.cumsum(rng.normal(0, 0.01, (nS, n0)), axis=1))
    Bc = 100 * np.exp(np.cumsum(rng.normal(0, 0.005, n0))); Bo = Bc * (1 + rng.normal(0, 0.001, n0))
    return {"n0": n0, "CM": CM, "Bc": Bc, "Bo": Bo}


def synth_ev(sids_j, e, pth, sale, P, R_, pend=False, pre=None):
    n = len(sids_j)
    return {"sid": np.array([f"S{j}" for j in sids_j], object), "j": np.array(sids_j, np.int64), "jm": np.zeros(n, np.int64),
            "e": np.full(n, e, np.int64), "pth": np.asarray(pth, float), "rk": np.linspace(0.1, 0.9, n), "sale": np.asarray(sale, np.int64),
            "P": np.asarray(P, float), "R": np.asarray(R_, float), "px": np.asarray(P, float) * (1 + np.asarray(R_, float)),
            "pre": np.ones(n, bool) if pre is None else np.asarray(pre, bool), "pend": np.full(n, pend), "typ": np.ones(n, np.int8),
            "X": np.asarray(sale, np.int64), "sd": np.asarray(sale, np.int64)}


def cat(*evs):
    return {k: np.concatenate([e[k] for e in evs]) for k in evs[0]}


def NS_free(uv):
    return H.NS - len(uv["held"])


def st_fixture(a):
    J = {"階段": "fixture", "結果": []}
    msgs = []
    # ⑧ 裁定 seq431：LINE 推送開關（設定檔「高10_LINE推送」）。暫停時買進行不帶【LINE】、其餘內容相同；之後各項以推送開啟測
    tag0 = H.LINE_TAG
    H.LINE_TAG = "- （LINE 暫停：高10 是否續推等使用者決定，裁定 seq431）"
    Lp = H.render({"asof": "2026-10-30", "nxt": "2026-11-02", "started": False, "e0": "2026-11-02", "form0": "2026-09-30", "held": [],
                   "buys": [("S01", "名", 50.0, H.shares(50.0))], "nfree": 10, "backup": [], "sells_tmr": [], "sold_today": []})
    assert not any("【LINE】" in x for x in Lp) and any(x.startswith("- （LINE 暫停") and "開盤買 1 檔" in x for x in Lp)
    H.LINE_TAG = "- 【LINE】⭐ "
    msgs.append("⑧ LINE 推送開關：暫停時買進行不帶【LINE】、內容照出（seq431）；其餘各項以推送開啟測（原設定 " + repr(tag0[:12]) + "）")
    # ⑤ 2 萬換算
    assert H.shares(2405) == 8 and H.shares(35.75) == 559 and H.shares(20000) == 1 and H.shares(20001) == 0
    assert H.shares(float("nan")) == 0 and H.shares(0) == 0 and H.shares(19.99) == 1000 and H.shares(0.5) == 40000
    msgs.append("⑤ 2 萬換算股數 ＝ floor(20000 ÷ 參考價)（2405→8、35.75→559、20000→1、20001→0、缺價→0）")
    # ① 月初前一晚：判定 ＋ 合成的明天 ＝ 真的明天（沒有人買不到時）
    T = pd.Timestamp
    assert H.is_buy_night(T("2026-10-30"), T("2026-11-02")) and not H.is_buy_night(T("2026-10-29"), T("2026-10-30"))
    assert not H.is_buy_night(T("2026-09-30"), T("2026-10-01")) and H.is_buy_night(T("2027-04-30"), T("2027-05-03"))
    W = synth_world(30, 41)
    CM = W["CM"]
    A = synth_ev(range(0, 12), 5, np.r_[np.ones(6), np.linspace(.99, .9, 6)], np.r_[np.full(12, 30)], CM[:12, 5], CM[:12, 30] / CM[:12, 5] - 1)
    B_ids = list(range(5, 25))
    Wt = {"n0": 40, "CM": CM[:, :40], "Bc": W["Bc"][:40], "Bo": W["Bo"][:40]}
    Bp = synth_ev(B_ids, 40, np.r_[np.ones(8), np.linspace(.98, .9, 12)], np.full(20, -1), CM[B_ids, 39], np.full(20, np.nan), pend=True)
    Sp, nw, nr = H.window_sim(Wt, cat(A, Bp), 0, True)
    ev_p = cat(A, Bp)
    plan = [ev_p["sid"][Sp["q"][q]] for t, q, amt in Sp["buys"] if t == nr]
    Br = synth_ev(B_ids, 40, np.r_[np.ones(8), np.linspace(.98, .9, 12)], np.full(20, -1), CM[B_ids, 40], np.full(20, np.nan))
    Sr, _, nr2 = H.window_sim(W, cat(A, Br), 0, False)
    ev_r = cat(A, Br)
    real = [ev_r["sid"][Sr["q"][q]] for t, q, amt in Sr["buys"] if t == 40]
    assert plan == real and len(plan) == 10, (plan, real)
    held = H.held_after(Sp, nr - 1)
    assert len(held) == 0                                         # A 批 30 日已到期賣出
    L = H.render({"asof": "2026-10-30", "nxt": "2026-11-02", "started": False, "e0": "2026-11-02", "form0": "2026-09-30", "held": [],
                  "buys": [(s, "名", 50.0, H.shares(50.0)) for s in plan], "nfree": 10, "backup": [("S99", "備")], "sells_tmr": [], "sold_today": []})
    line = [x for x in L if "【LINE】" in x]
    # D12（使用者 10/21「下面五句都不用寫」）：固定三句、同分句不在 LINE 行，改在下一行「  - 註：」；備位併入 LINE 行
    assert len(line) == 1 and line[0].startswith("- 【LINE】⭐ 52 週新高 10 檔（高10）：") and not any(s in line[0] for s in H.SENT3) and H.NOTE_TIE not in line[0]
    sub = L[L.index(line[0]) + 1]
    assert sub.startswith("  - 註：") and all(s in sub for s in H.SENT3) and H.NOTE_TIE in sub and "【LINE】" not in sub
    assert "明天 2026-11-02 開盤買 10 檔（每檔約 2 萬）" in line[0] and "400 股" in line[0] and "放 0050" not in line[0] and "S99 備" in line[0]
    assert all("【LINE】" not in x for x in L if x.startswith("  - "))
    msgs.append("① 月初前一晚：is_buy_night（跨月且 ≥ 2026-11）；合成的明天補進名單 ＝ 真的明天（無人買不到時）；LINE 行含買進日、2 萬換算股數與備位，"
                "不含固定三句與同分句（改在下一行「  - 註：」、不帶【LINE】）")
    # ② 非買賣日
    hd = [("S1", "甲", "2026-11-02", "2027-04-30"), ("S2", "乙", "2026-12-01", "2027-05-31")]
    for asof, nxt in (("2026-11-03", "2026-11-04"), ("2027-04-28", "2027-04-29")):
        assert H.sells_on(hd, nxt) == []
        L = H.render({"asof": asof, "nxt": nxt, "started": True, "e0": "2026-11-02", "form0": "2026-09-30", "held": hd, "buys": [], "nfree": 0,
                      "backup": [], "sells_tmr": H.sells_on(hd, nxt), "sold_today": []})
        assert not any("【LINE】" in x for x in L) and len([x for x in L if x.startswith("- ")]) == 1
    L = H.render({"asof": "2026-10-21", "nxt": "2026-10-22", "started": False, "e0": "2026-11-02", "form0": "2026-09-30", "held": [], "buys": [], "nfree": 0,
                  "backup": [], "sells_tmr": [], "sold_today": []})
    assert not any("【LINE】" in x for x in L) and "尚未開始" in L[2]
    msgs.append("② 非買賣日（含開始前）：只有一行持有狀態、無【LINE】")
    # ③ 第 6 個曆月最後交易日（月底遇平日休市）
    days = pd.bdate_range("2026-08-01", "2027-12-31")
    hol = {T("2027-04-30"), T("2026-12-31"), T("2027-01-01")}
    cal_ext = pd.DatetimeIndex([d for d in days if d not in hol])
    assert H.sched_sell(T("2026-11-02"), cal_ext) == T("2027-04-29")
    assert H.sched_sell(T("2026-08-03"), cal_ext) == T("2027-01-29") and H.sched_sell(T("2027-02-01"), cal_ext) == T("2027-07-30")
    cal_hist = cal_ext[cal_ext <= T("2027-06-30")]
    ME, MK = PT.month_ends(cal_hist)
    Wx = {"cal": cal_hist, "n0": len(cal_hist), "ME": ME, "EP": {L_: PT.entry_pos(cal_hist, MK, L_) for L_ in (1, 2)}}
    XP = PTH.exit_positions(Wx)
    j_sep = [j for j, (y, m) in enumerate(MK) if (y, m) == (2026, 10)][0]
    # 形成月 2026-10 ⇒ 跳月進場 2026-12、第 6 個曆月 2027-05
    xd = cal_hist[XP[(2, 6)][j_sep]]
    assert xd == H.sched_sell(cal_hist[Wx["EP"][2][j_sep]], cal_ext) == T("2027-05-31")
    j_nov = [j for j, (y, m) in enumerate(MK) if (y, m) == (2026, 11)][0]          # 進場 2027-01（1/01 休市 ⇒ 1/04）、第 6 個曆月 2027-06
    assert cal_hist[Wx["EP"][2][j_nov]] == T("2027-01-04") and cal_hist[XP[(2, 6)][j_nov]] == H.sched_sell(T("2027-01-04"), cal_ext)
    j_aug = [j for j, (y, m) in enumerate(MK) if (y, m) == (2026, 9)][0]           # 進場 2026-11、第 6 個曆月 2027-04（4/30 休市）
    assert cal_hist[XP[(2, 6)][j_aug]] == T("2027-04-29") == H.sched_sell(cal_hist[Wx["EP"][2][j_aug]], cal_ext)
    cut = cal_ext[cal_ext <= T("2027-04-29")]
    ME2, MK2 = PT.month_ends(cut)
    ME3, MK3 = H.month_ends_live(cut, T("2027-05-03"))
    assert MK2[-1] == (2027, 3) and MK3[-1] == (2027, 4) and ME3[-1] == len(cut) - 1
    ME4, MK4 = H.month_ends_live(cal_ext[cal_ext <= T("2027-04-28")], T("2027-04-29"))
    assert MK4[-1] == (2027, 3)
    hd = [("S1", "甲", "2026-11-02", str(H.sched_sell(T("2026-11-02"), cal_ext).date()))]
    assert H.sells_on(hd, "2027-04-29") == [("S1", "甲")]
    L = H.render({"asof": "2027-04-28", "nxt": "2027-04-29", "started": True, "e0": "2026-11-02", "form0": "2026-09-30", "held": hd, "buys": [], "nfree": 0,
                  "backup": [], "sells_tmr": H.sells_on(hd, "2027-04-29"), "sold_today": []})
    assert any(x.startswith("- 【LINE】⭐") and "明天 2027-04-29 收盤賣 1 檔（收盤賣）：S1 甲" in x and "續抱 0 檔" in x for x in L)
    L = H.render({"asof": "2027-04-29", "nxt": "2027-05-03", "started": True, "e0": "2026-11-02", "form0": "2026-09-30", "held": [], "buys": [("S7", "丙", 10.0, 2000)],
                  "nfree": 10, "backup": [], "sells_tmr": [], "sold_today": [("S1", "甲")]})
    assert any("今天 2027-04-29 收盤已到期賣出 1 檔：S1 甲" in x and "空 9 格放 0050" in x for x in L)
    msgs.append("③ 第 6 個曆月最後交易日：sched_sell ＝ researchPTH.exit_positions（4/30 休市 ⇒ 4/29、1/01 休市 ⇒ 1/04 進場）；資料日 4/29（月底遇平日休市）"
                "month_ends 判不完整、month_ends_live 補進；前一晚 LINE「收盤賣」、當晚「已到期賣出」")
    # ④ 空格放 0050
    W4 = synth_world(10, 20, 5)
    A4 = synth_ev(range(4), 3, np.ones(4), np.full(4, -1), W4["CM"][:4, 3], np.full(4, np.nan))
    S4, _, _ = H.window_sim(W4, A4, 0, False)
    assert len(S4["buys"]) == 4 and all(abs(amt - 0.1) < 1e-12 or abs(amt - S4["eq"][2] / 10) < 1e-12 for _, _, amt in S4["buys"])
    u_share = S4["u"][3] / S4["eq"][3]
    assert 0.55 < u_share < 0.65 and int(S4["nh"][10]) == 4, (u_share, S4["nh"][10])
    L = H.render({"asof": "x", "nxt": "y", "started": True, "e0": "", "form0": "", "held": [], "buys": [("S0", "a", 10.0, 2000)] * 4, "nfree": 10,
                  "backup": [], "sells_tmr": [], "sold_today": []})
    assert "空 6 格放 0050" in L[2]
    L = H.render({"asof": "x", "nxt": "y", "started": True, "e0": "", "form0": "", "held": [("S0", "a", "d", "2027-04-29")] * 4, "buys": [], "nfree": 0,
                  "backup": [], "sells_tmr": [], "sold_today": []})
    assert "其餘 0050" in L[2] and "空 6 格下個月初補" in L[2]
    msgs.append(f"④ 空格放 0050：候選 4 檔 ⇒ 只補 4 格（每格 前一日淨值 ÷ 10）、0050 占淨值 {u_share:.3f}；LINE「空 6 格放 0050」、平日「其餘 0050」")
    # ⑦ 照規則與使用者分岔：LINE 的賣出、續抱只列使用者（positions_user）持有的；選股跳過使用者已持有、空格照使用者
    def urow(sid, nm, st_, sched, sold="", rec=""):
        return {"批次": "2026-09-30", "代號": sid, "名稱": nm, "名單日": "2026-10-30", "參考價": "50", "股數": "400", "買進日": "2026-11-02",
                "買進價": "50", "狀態": st_, "排程賣出日": sched, "賣出日": sold, "賣出價": "", "備註": "", "出場記於": rec}
    U = pd.DataFrame([urow("A1", "甲", "持有中", "2027-04-29（外推）"), urow("B1", "乙", "持有中", "2027-05-31（外推）"),
                      urow("D1", "丁", "已出場", "2027-04-29（外推）", "2027-04-20", "2027-04-28"), urow("E1", "戊", "買不到", "2027-04-29（外推）")],
                     columns=H.USR_COLS)
    rule_held = [("C1", "丙", "2026-11-02", "2027-04-29"), ("A1", "甲", "2026-11-02", "2027-04-29")]
    assert H.sells_on(rule_held, "2027-04-29") == [("C1", "丙"), ("A1", "甲")]           # 照規則明天會賣 C1、A1
    uv = H.user_view(U, "2027-04-28", "2027-04-29")
    assert uv["sells_tmr"] == [("A1", "甲")] and [h[0] for h in uv["held"]] == ["A1", "B1"]
    assert uv["sold_today"] == [] and uv["sold_other"] == [("D1", "丁", "2027-04-20")]
    L = H.render({"asof": "2027-04-28", "nxt": "2027-04-29", "started": True, "e0": "2026-11-02", "form0": "2026-09-30", "held": uv["held"], "buys": [],
                  "nfree": 0, "backup": [], "sells_tmr": uv["sells_tmr"], "sold_today": uv["sold_today"], "sold_other": uv["sold_other"]})
    line = [x for x in L if "【LINE】" in x]
    assert len(line) == 1 and "明天 2027-04-29 收盤賣 1 檔（收盤賣）：A1 甲" in line[0] and "C1" not in line[0] and "E1" not in line[0]
    assert "續抱 1 檔：B1 乙" in line[0] and "D1 丁（2027-04-20）" in line[0]
    pk, bk = H.pick_user(["A1", "X1", "B1", "X2", "X3", "X4", "X5"], {"A1", "B1"}, 3)
    assert pk == ["X1", "X2", "X3"] and bk == ["X4", "X5"]
    uv2 = H.user_view(U.assign(狀態=np.where(U["代號"] == "A1", "已出場", U["狀態"]), 賣出日=np.where(U["代號"] == "A1", "2027-04-29", U["賣出日"]),
                               出場記於=np.where(U["代號"] == "A1", "2027-04-29", U["出場記於"])), "2027-04-29", "2027-05-03")
    assert uv2["sold_today"] == [("A1", "甲")] and NS_free(uv2) == 9
    msgs.append("⑦ 照規則與使用者分岔：照規則明天賣 C1、A1，使用者只持有 A1、B1 ⇒ LINE 只列賣 A1、續抱 B1（C1、買不到的 E1 不出現）；"
                "照規則提前出場的 D1 照列；選股跳過使用者已持有、空格 ＝ 10 − 使用者持有")
    # ⑥ put
    tmpd = os.path.join(a.work, "fx"); os.makedirs(tmpd, exist_ok=True)
    md = os.path.join(tmpd, "d.md")
    base = "# 每日名單 x\n\n## 一、甲\n\n- a\n\n## 八、（內部）乙\n\n- b\n\n## 九、VIX 狀態\n\n- c\n"
    open(md, "w", encoding="utf-8").write(base)
    H.put(md, ["## 十、52 週新高 10 檔（高10）", "", "- 舊", ""])
    H.put(md, ["## 十、52 週新高 10 檔（高10）", "", "- 新", ""])
    s = open(md, encoding="utf-8").read()
    assert s == base + "\n## 十、52 週新高 10 檔（高10）\n\n- 新\n", repr(s)
    open(md, "w", encoding="utf-8").write(base.replace("## 九、VIX 狀態", "## 十、52 週新高 10 檔（高10）\n\n- 舊\n\n## 九、VIX 狀態"))
    H.put(md, ["## 十、52 週新高 10 檔（高10）", "", "- 新", ""])
    assert open(md, encoding="utf-8").read() == base + "\n## 十、52 週新高 10 檔（高10）\n\n- 新\n"
    msgs.append("⑥ put：只拿掉舊第十節、接在檔尾；其他段逐字不變（含第十節夾在中間的情形）")
    msgs += f9_fixture(a)
    for m in msgs:
        log("✅ " + m)
    J["結果"] = msgs; J["通過"] = True
    save("fixture", J)
    return True


# ═════════════ ⑤ 乾跑 ═════════════
def st_dry(a):
    J = {"階段": "dry"}
    d = os.path.join(a.work, "dry"); os.makedirs(d, exist_ok=True)
    src = "backtest/resultsDaily/daily_2026-10-20.md"
    orig = open(src, encoding="utf-8").read()
    out = {}
    for tag, extra in (("平日", []), ("預覽買進前一晚", ["--preview-buy", "--nowrite"])):
        md = os.path.join(d, f"daily_2026-10-20_{tag}.md")
        shutil.copy(src, md)
        ap = argparse.Namespace(asof="2026-10-20", md=md, sha=DRY_SHA, fwd=os.path.join(d, "fwd"), nowrite="--nowrite" in extra,
                                preview_buy="--preview-buy" in extra, procs=a.procs)
        L, _ = H.run(ap, log)
        new = open(md, encoding="utf-8").read()
        assert new.startswith(orig.rstrip("\n")), "⛔ 其他段被改"
        out[tag] = L
    assert open(src, encoding="utf-8").read() == orig
    J["段落"] = out; J["通過"] = True
    log("[⑤乾跑] resultsDaily/daily_2026-10-20.md 未動；暫存 md 只多第十節 ✅")
    save("dry", J)
    return True


# ═════════════ ⑥ 端到端（把起點假設成 2026-04，用 9/29、9/30、10/01、10/20 四個真快照連跑；只驗流程，⛔ 不是前瞻紀錄）═════════════
E2E = [("2026-09-29", "~/h2data/full_9cc88ec902b6/data"), ("2026-09-30", "~/h2data/indrev_5d20a7edcf07/data"),
       ("2026-10-01", "~/h2data/indrev_f65bb03e114a/data"), ("2026-10-20", f"~/h2data/{DRY_SHA}/data")]


def st_e2e(a):
    day = int(a.day)
    asof, data = E2E[day]
    d = os.path.join(a.work, "e2e"); fwd = os.path.join(d, "fwd")
    if day == 0 and os.path.exists(d):
        shutil.rmtree(d)
    os.makedirs(d, exist_ok=True)
    H.START_YM = 2026 * 12 + 3                                     # 測試：第一批進場月 2026-04（形成月 2026-02）
    md = os.path.join(d, f"daily_{asof}.md")
    shutil.copy(f"backtest/resultsDaily/daily_{asof}.md", md)
    orig = open(md, encoding="utf-8").read()
    ap = argparse.Namespace(asof=asof, md=md, sha=None, fwd=fwd, nowrite=False, preview_buy=False, procs=a.procs, data=data)
    L, X = H.run(ap, log)
    chk = {}
    seed = os.path.join(d, "seed.json")
    if day == 0:
        # 使用者實際（positions_user）造一份「分岔」的：照規則持有中各列、去掉一檔 9/30 到期的、另加一檔照規則沒有的 2330（9/30 到期）⇒ 同一資料日重跑
        POS = pd.read_csv(os.path.join(fwd, "positions.csv"), dtype=str, keep_default_na=False)
        h = POS[POS["狀態"] == "持有中"]
        drop = h.loc[h["排程賣出日"].str.startswith("2026-09-30"), "代號"].iloc[0]
        rows = [{"批次": r["批次"], "代號": r["代號"], "名稱": r["名稱"], "名單日": "", "參考價": "", "股數": "1", "買進日": r["買進日"], "買進價": r["買進未還原開盤"],
                 "狀態": "持有中", "排程賣出日": r["排程賣出日"], "賣出日": "", "賣出價": "", "備註": "e2e 造", "出場記於": ""} for _, r in h.iterrows() if r["代號"] != drop]
        rows.append({"批次": "2026-02-26", "代號": "2330", "名稱": "台積電", "名單日": "", "參考價": "", "股數": "1", "買進日": "2026-04-01", "買進價": "",
                     "狀態": "持有中", "排程賣出日": "2026-09-30", "賣出日": "", "賣出價": "", "備註": "e2e 造（照規則沒有）", "出場記於": ""})
        H.write_csv(pd.DataFrame(rows, columns=H.USR_COLS), os.path.join(fwd, "positions_user.csv"))
        json.dump({"drop": drop}, open(seed, "w"))
        shutil.copy(f"backtest/resultsDaily/daily_{asof}.md", md)
        L, X = H.run(ap, log)
    drop = json.load(open(seed))["drop"]
    assert open(md, encoding="utf-8").read().startswith(orig.rstrip("\n"))
    POS = pd.read_csv(os.path.join(fwd, "positions.csv"), dtype=str, keep_default_na=False)
    line = [x for x in L if "【LINE】" in x]
    if day == 0:
        sell = line[0].split("明天 2026-09-30 收盤賣")[1].split("；")[0] if line and "明天 2026-09-30 收盤賣" in line[0] else ""
        chk["LINE：明天 9/30 收盤賣（照使用者持有）"] = "2330 台積電" in sell and drop not in sell
        chk["照規則持有 ≤ 10、且含被去掉的那檔"] = len(X["held"]) <= 10 and drop in [h_[0] for h_ in X["held"]]
        chk["md 有分岔說明行（不推）"] = any(x.startswith("  - LINE 名單持有") and "【LINE】" not in x for x in L)
    if day == 1:
        chk["LINE：今天已到期賣出 ＋ 明天 10/01 開盤買"] = bool(line) and "今天 2026-09-30 收盤已到期賣出" in line[0] and "明天 2026-10-01 開盤買" in line[0]
        sold = line[0].split("收盤已到期賣出")[1].split("；")[0] if line else ""
        chk["今天賣出只列使用者持有（含 2330、不含被去掉的）"] = "2330" in sold and drop not in sold
        p4 = POS[POS["買進日"].str.startswith("2026-04")]
        chk["4 月批全已出場、到期者賣出日 9/30"] = bool((p4["狀態"] == "已出場").all() and (p4.loc[p4["出場種類"] == "到期收盤", "賣出日"] == "2026-09-30").all())
        st = json.load(open(os.path.join(fwd, "state.json"), encoding="utf-8"))
        chk["名單存入 state（10/01）"] = "2026-10-01" in st["名單"] and len(st["名單"]["2026-10-01"]["rows"]) == len(X["buys"])
    if day == 2:
        b = POS[POS["買進日"] == "2026-10-01"]
        chk["10/01 照規則買進已記"] = len(b) > 0
        U = pd.read_csv(os.path.join(fwd, "positions_user.csv"), dtype=str, keep_default_na=False)
        chk["使用者實際（名單 2 萬）已記"] = int((U["名單日"] == "2026-09-30").sum()) > 0
        chk["10/01 無【LINE】"] = not line
    if day == 3:
        EQ = pd.read_csv(os.path.join(fwd, "equity.csv"), dtype=str)
        chk["權益記到 10/20"] = EQ["日期"].iloc[-1] == "2026-10-20" and EQ["日期"].is_unique
        chk["10/20 無【LINE】"] = not line
        chk["已出場列有出場種類"] = bool((POS.loc[POS["賣出日"] != "", "出場種類"] != "").all())
    ok = all(chk.values())
    log(f"[⑥端到端 day{day} {asof}] {chk}｜{'✅' if ok else '⛔'}")
    J = {"階段": f"e2e{day}", "段落": L, "檢查": chk, "通過": ok, "照規則持有": [h[0] for h in X["held"]], "名單": [b[0] for b in X["buys"]]}
    save(f"e2e{day}", J)
    return ok


# ═════════════ D10 同分排序 F9 ═════════════
def lock_check():
    import subprocess
    p = subprocess.run([os.path.expanduser("~/tw-p16/.venv/bin/python"), "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True,
                       env={**os.environ, "PYTHONPATH": os.path.expanduser("~/tw-p17")}, cwd=os.path.expanduser("~/tw-p17"))
    out = (p.stdout + p.stderr).strip().splitlines()
    return bool(p.returncode == 0 and "相符" in "".join(out[-3:])), out[-3:]


def f9_fixture(a):
    """④⑨：D10 同分排序（合成資料；⛔ 不讀真實分數）。"""
    msgs = []
    # 同分群
    g = H.tie_groups([1, 1, 1, .9, .9, .8])
    assert (g[:3] == g[0]).all() and (g[3:5] == g[3]).all() and g[0] != g[3] and g[0] >= 0 and g[3] >= 0 and g[5] == -1
    # F9 排序：同 PTH 內 F9 高→低、算不出排最後、F9 同分 ⇒ 原 rk；不跨 PTH
    sids = ["S0", "S1", "S2", "S3", "S4", "S5", "S6"]
    pth = np.array([1, 1, 1, 1, .95, .95, .9]); rk = np.array([.1, .2, .3, .4, .6, .5, .7])
    grp = H.tie_groups(pth)
    MB = pd.DataFrame({"q": [0, 1, 2, 3, 4, 5], "F9": [50.0, np.nan, 80.0, 50.0, 10.0, 20.0]})
    fl, sc = H.tie_keys(grp, MB)
    assert fl.tolist() == [False, True, False, False, False, False, False] and sc[6] == 0.0
    o = [sids[k] for k in H.user_order(rk, pth, fl, sc)]
    assert o == ["S2", "S0", "S3", "S1", "S5", "S4", "S6"], o
    # F9 同分（S0、S3 都 50）走抽籤：rk 對調 ⇒ 次序對調
    rk2 = rk.copy(); rk2[[0, 3]] = rk2[[3, 0]]
    o2 = [sids[k] for k in H.user_order(rk2, pth, fl, sc)]
    assert o2 == ["S2", "S3", "S0", "S1", "S5", "S4", "S6"], o2
    # 全部算不出 ＝ 全 0 ＝ 抽籤次序 ＝ batch_order
    for f_, s_ in ((np.ones(7, bool) & (grp >= 0), sc), (np.zeros(7, bool), np.zeros(7))):
        assert H.user_order(rk, pth, f_, s_).tolist() == H.user_order(rk, pth).tolist()
    rkb, ob = H.batch_order(sids, pth, 7)
    assert H.user_order(rkb, pth).tolist() == ob.tolist()
    # 跳過已持有、取空格
    pk_, bk_ = H.pick_user(o, {"S0", "S5"}, 3)
    assert pk_ == ["S2", "S3", "S1"] and bk_ == ["S4", "S6"]
    msgs.append("⑨a 同分排序 F9：同 PTH 內 F9 高→低、F9 缺值排最後（不跨 PTH）、F9 同分 ⇒ 原 rk（對調 rk ⇒ 次序對調）；全算不出／全 0 ＝ 抽籤 ＝ batch_order；pick_user 跳過持有")
    # 設定鍵
    tdir = os.path.join(a.work, "fx"); os.makedirs(tdir, exist_ok=True)
    cases = [({"高10": 20000}, "抽籤"), ({"高10_同分排序": "F9"}, "F9"), ({"高10_同分排序": " f9 "}, "F9"), ({"高10_同分排序": "抽籤"}, "抽籤"),
             ({"高10_同分排序": "xyz"}, "抽籤"), ({"高10_同分排序": None}, "抽籤")]
    for k, (d_, want) in enumerate(cases):
        p = os.path.join(tdir, f"set{k}.json"); json.dump(d_, open(p, "w", encoding="utf-8"), ensure_ascii=False)
        assert H._load_tie(p) == want, (d_, H._load_tie(p))
    p = os.path.join(tdir, "bad.json"); open(p, "w").write("{壞")
    assert H._load_tie(p) == "抽籤" and H._load_tie(os.path.join(tdir, "沒有這個檔.json")) == "抽籤"
    cur = json.load(open(H.SETTING, encoding="utf-8"))
    assert H.TIE == ("F9" if str(cur.get("高10_同分排序", "")).strip().upper() == "F9" else "抽籤")
    msgs.append(f"⑨b 設定鍵「高10_同分排序」：缺鍵／讀不到／壞檔／其他值 ⇒ 抽籤；\"F9\"（不分大小寫、去空白）⇒ F9；目前設定檔 ⇒ {H.TIE}")
    # LINE 行
    tag0 = H.LINE_TAG; H.LINE_TAG = "- 【LINE】⭐ "
    try:
        base = {"asof": "2026-10-30", "nxt": "2026-11-02", "started": False, "e0": "2026-11-02", "form0": "2026-09-30", "held": [],
                "buys": [("S01", "名", 50.0, H.shares(50.0))], "nfree": 10, "backup": [("S02", "備")], "sells_tmr": [], "sold_today": []}
        Lr = H.render(dict(base)); Lf = H.render(dict(base, tie="F9"))
    finally:
        H.LINE_TAG = tag0
    lr = [x for x in Lr if "【LINE】" in x][0]; lf = [x for x in Lf if "【LINE】" in x][0]
    nr_ = Lr[Lr.index(lr) + 1]; nf_ = Lf[Lf.index(lf) + 1]
    # D12：LINE 行不含五句（同分句、F9 句、固定三句）；下一行「  - 註：」依序列出（不帶【LINE】）；LINE 行開頭不變
    five = [H.NOTE_TIE_F9, H.F9_SENT, *H.SENT3]
    for x in (lr, lf):
        assert x.startswith("- 【LINE】⭐ 52 週新高 10 檔（高10）：") and not any(s in x for s in five + [H.NOTE_TIE])
    assert nf_ == "  - 註：" + "｜".join(five) and nr_ == "  - 註：" + "｜".join([H.NOTE_TIE, *H.SENT3])
    assert H.F9_SENT == "同分時依大跌 4 檔分數挑（你 10/21 選；回測：跟抽籤分不出，最多暫定）"
    assert all("【LINE】" not in x for x in Lf if x.startswith("  - ")) and any("依大跌 4 檔分數排序" in x for x in Lf if x.startswith("  - 名單依今晚資料"))
    assert lr == lf.replace("照同一排序", "照規則")                  # LINE 行只差備位的遞補說法
    msgs.append("⑨c LINE 行（D12）：只留名單內容（買、續抱、賣、備位）、開頭不變；五句（F9 版同分句、「" + H.F9_SENT + "」、固定三句）"
                "移到下一行「  - 註：」（不帶【LINE】）；抽籤模式註行 ＝ 原同分句＋固定三句")
    # 無同分群 ⇒ 不算分數、次序 ＝ 抽籤
    ns = argparse.Namespace(procs=1, nowrite=True, xd="/不存在")
    pl = [("A1", 1.0), ("A2", .99), ("A3", .98)]
    rk3, o3 = H.batch_order([s for s, _ in pl], [p for _, p in pl], 5)
    ordr, inf = H.f9_pend(ns, None, None, "x" * 10, tdir, "2026-09-30", "fx", pl, rk3, {}, {}, log)
    assert ordr == [pl[k][0] for k in o3] and inf["同分群"] == 0 and inf["來源"] == "無同分群"
    msgs.append("⑨d 當批沒有同分群 ⇒ 不讀分數資料、LINE 名單次序 ＝ 抽籤次序")
    return msgs


def _ev_world(a):
    W = pickle.load(open(os.path.join(a.work, "h2d_world.pkl"), "rb"))
    R = pickle.load(open(os.path.join(a.work, "h2d_rank.pkl"), "rb"))["R"]
    H.D.DATA = W["data"]; PT._G[H.WN] = W
    RES = H.pool_map(PTH.stock_job, [(H.WN, s) for s in W["sids"]], a.procs)
    RES = {k: v for k, v in RES.items() if v is not None}
    EP2 = W["EP"][2]; ME = W["ME"]; dates = W["dates"]
    js = [j for j in range(len(ME)) if EP2[j] >= 0]
    rows = rows_from(R, W, js)
    ev = H.assemble(W, rows, RES)
    ev["form"] = np.array([str(dates[ME[j]]) for j in ev["jm"]], object)
    _EVW.update(rows=rows, RES=RES)
    return W, ev


_EVW: dict = {}


def held_months(W, T):
    """交易檔（sid、買進日、賣出日）⇒ 各月第一個交易日（2016-03 起）月初買進後持股。"""
    cal = W["cal"]; dates = W["dates"]
    firsts = [t for t in range(1, len(cal)) if cal[t].month != cal[t - 1].month and dates[t] >= "2016-03-01"]
    return {dates[t]: sorted(s for s, b, x in zip(T["sid"], T["買進日"], T["賣出日"]) if b <= dates[t] and (x == "" or x > dates[t])) for t in firsts}


def pick_replay(ev, T, flag=None, score=None):
    """(b) 使用者版：每批 pth10_daily.user_order ＋ pick_user（跳過 ＝ 交易檔 買進日 ＜ e ≤ 賣出日；空格 ＝ 10 − 買進日 ＜ e ＜ 賣出日 的檔數，
    ＝ 引擎「同日先出後進」）⇒ 前 k 檔 ＝ 交易檔當日買進（k ＝ 實買數）。
    ⚠ 前瞻的 LINE 名單在前一晚出，看不到「買進日當天壞根強制賣出」⇒ 那種月份 LINE 名單會少補 1 格（次數另報）。"""
    bad, n, kfull, sameday = [], 0, 0, 0
    for e in np.unique(ev["e"]):
        idx = np.flatnonzero(ev["e"] == e)
        o = H.user_order(ev["rk"][idx], ev["pth"][idx], None if flag is None else flag[idx], None if score is None else score[idx])
        order = [str(ev["sid"][idx[k]]) for k in o]
        d = T.loc[T["sid"].isin(order) & (T["_e"] == int(e)), "sid"].tolist()
        dd = T["買進日"][T["_e"] == int(e)]
        if not len(dd):
            continue
        day = dd.iloc[0]
        blk = {s for s, b, x in zip(T["sid"], T["買進日"], T["賣出日"]) if b < day and (x == "" or x >= day)}       # 不可再買（含當天賣出者）
        nh = sum(1 for b, x in zip(T["買進日"], T["賣出日"]) if b < day and (x == "" or x > day))                     # 引擎「同日先出後進」：當天賣出的格可補
        sameday += int(nh < len(blk))
        pk_, _ = H.pick_user(order, blk, H.NS - nh)
        n += 1; kfull += int(len(d) == len(pk_))
        if d != pk_[:len(d)]:
            bad.append(day)
    return {"有買進批": n, "前 k 檔 ≠ 實買 批數": len(bad), "不同批": bad[:10], "實買數 ＝ 10 − 持有（未受 0050 可撥金額限制）批數": kfull,
            "買進日當天有持股賣出（壞根強制，引擎同日先出後進）批數": sameday}


def st_f9replay(a):
    J = {"階段": "f9replay", "結果": {}}
    t0 = time.time()
    from backtest import researchPTH10tie as TT                   # ev_with_order（rk 位置化）
    TF = H._tf()
    lk0 = lock_check(); J["策略鎖前"] = lk0[1]
    W, ev = _ev_world(a)
    nev = len(ev["e"]); dates = W["dates"]
    log(f"[⑦] 事件 {nev}｜{time.time() - t0:.0f}s")
    # 同分群（每批）
    grp = np.full(nev, -1, np.int64); off = 0
    for e in np.unique(ev["e"]):
        idx = np.flatnonzero(ev["e"] == e)
        g = H.tie_groups(ev["pth"][idx]); m = g >= 0
        grp[idx[m]] = g[m] + off; off += int(g.max()) + 1 if m.any() else 0
    forms = sorted({ev["form"][q] for q in np.flatnonzero(grp >= 0)})
    X, FIN, QFIN, info = H.f9_ctx(W["data"], W["cal"], forms, sorted({str(ev["sid"][q]) for q in np.flatnonzero(grp >= 0)}), a.procs, log, mk=W["mk"])
    J["資料"] = info
    parts = []
    for f_ in forms:
        qs = np.flatnonzero(ev["form"] == f_)
        d = H.f9_members(X, FIN, QFIN, f_, [str(s) for s in ev["sid"][qs]], grp[qs], qs)
        d["形成月底"] = f_
        parts.append(d)
    MB = pd.concat(parts, ignore_index=True)
    log(f"[⑦] 分數 {len(MB)} 列、同分群 {off} 組、{len(forms)} 排序日｜{time.time() - t0:.0f}s")
    ref = pd.read_csv("backtest/resultsPTH10tie/freq/members_主.csv.gz", dtype={"sid": str}, float_precision="round_trip")
    A = MB.set_index(["形成月底", "sid"]); B = ref.set_index(["形成月底", "sid"])
    r0 = {"本模組成員": len(A), "members_主 成員": len(B), "成員集合相同": set(A.index) == set(B.index)}
    if r0["成員集合相同"]:
        B = B.loc[A.index]
        for c in ("F9ok", "has6", "has7", "hasQ"):
            r0[f"{c} 不同列"] = int((A[c].astype(bool).to_numpy() != B[c].astype(bool).to_numpy()).sum())
        for c in ("F9", "F6_g6", "F7_g6", "Q_g6", "F6", "F7", "Q"):
            fa = ["%.10g" % x for x in A[c].to_numpy(float)]; fb = ["%.10g" % x for x in B[c].to_numpy(float)]
            r0[f"{c} 不同列（%.10g）"] = int(sum(x != y for x, y in zip(fa, fb)))
    J["結果"]["分數 vs resultsPTH10tie/freq/members_主"] = r0
    ok0 = r0["成員集合相同"] and all(v == 0 for k, v in r0.items() if "不同列" in k)
    log(f"[⑦分數] {r0}｜{'✅' if ok0 else '⛔'}")
    fl, sc = H.tie_keys(grp, MB)
    KD = pd.read_csv("backtest/resultsPTH10tie/main/keys_主.csv.gz", dtype={"sid": str}, float_precision="round_trip")
    km = KD.set_index(["形成月底", "sid"]).loc[list(zip(ev["form"], [str(s) for s in ev["sid"]]))]
    r1 = {"列": int(len(km)), "keys_主 列": int(len(KD)),
          "T1 算不出 不同": int((km["T1_算不出"].astype(str).str.lower().eq("true").to_numpy() != fl).sum()),
          "T1 鍵 不同（%.10g）": int(sum(("%.10g" % x) != ("%.10g" % y) for x, y in zip(km["T1_鍵"].to_numpy(float), sc))),
          "原 rk 不同（%.10g）": int(sum(("%.10g" % x) != ("%.10g" % y) for x, y in zip(km["rk原"].to_numpy(float), ev["rk"]))),
          "同分群成員 不同": int(((km["grp"].to_numpy() >= 0) != (grp >= 0)).sum())}
    J["結果"]["鍵 vs resultsPTH10tie/main/keys_主"] = r1
    ok1 = len(km) == len(KD) and all(v == 0 for k, v in r1.items() if "不同" in k)
    log(f"[⑦鍵] {r1}｜{'✅' if ok1 else '⛔'}")
    # (a) 引擎
    o = TF.order_of(ev, fl, sc)
    ev2 = TT.ev_with_order(ev, o)
    S, _, _ = H.window_sim(W, ev2, 0, False)
    with gzip.open("backtest/resultsPTH10tie/main/trades_主_T1.csv.gz", "rt", encoding="utf-8") as fh:
        t1 = fh.read()
    T1 = pd.read_csv(io.StringIO(t1), dtype=str, keep_default_na=False)
    mine = PN.trades_df(W, ev2, S)
    Tm = pd.read_csv(io.StringIO(PN.df_text(mine, "%.17g")), dtype=str, keep_default_na=False)
    hm, hr = held_months(W, Tm), held_months(W, T1)
    badm = [d for d in hr if hm.get(d) != hr[d]]
    r2 = {"交易檔全文 ＝ trades_主_T1": PN.df_text(mine, "%.17g") == t1, "筆數": len(S["buys"]), "T1 筆數": len(T1),
          "月數": len(hr), "期間": f"{min(hr)}～{max(hr)}", "股月數": int(sum(len(v) for v in hr.values())), "持股不同月數": len(badm), "不同月": badm[:10]}
    J["結果"]["(a) 引擎 F9 次序 vs trades_主_T1"] = r2
    ok2 = r2["交易檔全文 ＝ trades_主_T1"] and not badm
    log(f"[⑦引擎] {r2}｜{'✅' if ok2 else '⛔'}")
    # (b) 使用者版：user_order ＋ pick_user
    dpos = {d: i for i, d in enumerate(dates)}
    T1["_e"] = T1["買進日"].map(dpos)
    with gzip.open("backtest/resultsPTHn/trades_主_N10.csv.gz", "rt", encoding="utf-8") as fh:
        N10 = pd.read_csv(fh, dtype=str, keep_default_na=False)
    N10["_e"] = N10["買進日"].map(dpos)
    r3 = {"F9 vs trades_主_T1": pick_replay(ev, T1, fl, sc), "抽籤 vs trades_主_N10": pick_replay(ev, N10)}
    J["結果"]["(b) 使用者版 user_order＋pick_user 前 k 檔 ＝ 實買"] = r3
    ok3 = all(v["前 k 檔 ≠ 實買 批數"] == 0 and v["有買進批"] > 0 for v in r3.values())
    log(f"[⑦使用者版] {r3}｜{'✅' if ok3 else '⛔'}")
    # (c) D11 第三本「F9 照規則」：pth10_daily.f9_rows（同批 rk ＝ F9 次序位置、前 20 名依 F9）＋ assemble ＋ window_sim
    #     ⇒ 權益／持股數 ＝ resultsPTH10tie/main/raw_主.npz T1_eq／T1_nh（逐位元）、交易檔 ＝ trades_主_T1
    rows, RES = _EVW["rows"], _EVW["RES"]
    orders = {}
    for j in sorted({int(r["j"]) for r in rows}):
        idx = np.flatnonzero(ev["jm"] == j)
        if [str(s) for s in ev["sid"][idx]] != [r["sid"] for r in rows if r["j"] == j]:
            raise SystemExit("⛔ ev 與事件列順序不同")
        orders[j] = H.user_order(ev["rk"][idx], ev["pth"][idx], fl[idx], sc[idx])
    rows9 = H.f9_rows(rows, orders)
    ev9 = H.assemble(W, rows9, RES)
    ev9["form"] = ev["form"]
    S9, _, _ = H.window_sim(W, ev9, 0, False)
    Z = np.load("backtest/resultsPTH10tie/main/raw_主.npz")
    r4 = {"權益 ＝ raw_主 T1_eq（逐位元）": eqa(S9["eq"], Z["T1_eq"]), "持股數 ＝ T1_nh（逐位元）": eqa(S9["nh"], Z["T1_nh"]),
          "交易檔全文 ＝ trades_主_T1": PN.df_text(PN.trades_df(W, ev9, S9), "%.17g") == t1, "買進筆": len(S9["buys"]),
          "每批算出場列（前 20 名）": int(sum(r["pre"] for r in rows9)), "批數": len(orders)}
    J["結果"]["(c) F9 照規則本（f9_rows＋window_sim）vs resultsPTH10tie T1"] = r4
    ok4 = r4["權益 ＝ raw_主 T1_eq（逐位元）"] and r4["持股數 ＝ T1_nh（逐位元）"] and r4["交易檔全文 ＝ trades_主_T1"]
    log(f"[⑦F9照規則本] {r4}｜{'✅' if ok4 else '⛔'}")
    lk1 = lock_check(); J["策略鎖後"] = lk1[1]
    okl = lk0[0] and lk1[0]
    log(f"[⑦策略鎖] 前 {lk0[1]}／後 {lk1[1]}｜{'✅' if okl else '⛔'}")
    J["通過"] = bool(ok0 and ok1 and ok2 and ok3 and ok4 and okl)
    log(f"[⑦f9replay] {'✅ 全過' if J['通過'] else '⛔ 有不符'}｜{time.time() - t0:.0f}s")
    save("f9replay", J)
    return J["通過"]


def st_f9dry(a):
    """⑧：最新真快照 --preview-buy，11/2 首批（2026-09-30 排序）；--tie 抽籤｜F9；⛔ 不寫 md。"""
    tie = a.tie
    J = {"階段": f"f9dry_{tie}"}
    t0 = time.time()
    lk0 = lock_check(); J["策略鎖前"] = lk0[1]
    d = os.path.join(a.work, "f9dry"); fwd = os.path.join(d, f"fwd_{tie}")
    if os.path.exists(fwd):
        shutil.rmtree(fwd)
    os.makedirs(os.path.join(fwd, "ranks"), exist_ok=True)
    rc = os.path.join(a.work, "dry", "fwd", "ranks", "ranks_2026-09.csv")       # ⑤ 同快照（dbfb96）已算好的 2026-09 排序，省 3～5 分
    if os.path.exists(rc):
        shutil.copy(rc, os.path.join(fwd, "ranks", "ranks_2026-09.csv"))
    rs = sorted(os.listdir(os.path.join(a.work, "dry", "fwd", "ranks"))) if os.path.isdir(os.path.join(a.work, "dry", "fwd", "ranks")) else []
    ap = argparse.Namespace(asof="2026-10-20", md=None, sha=DRY_SHA, fwd=fwd, nowrite=False, preview_buy=True, procs=a.procs, tie=tie, xd=None)
    L, X = H.run(ap, log)
    nm = X["W"]["names"]
    J.update({"段落": L, "同分排序(實際)": X["tie"], "F9說明": X["f9"], "名單": [[s, nm.get(s, ""), p, k] for s, nm_, p, k in X["buys"]],
              "備位": X["backup"], "照規則明天會買": X["rule_picks"], "使用者版次序前20": X["user_order"][:20], "照規則次序前20": X["rule_order"][:20],
              "排序快取來源": rc if os.path.exists(rc) else "重算", "dry/fwd/ranks": rs})
    if tie == "F9":
        cp = H.f9_path(fwd, "2026-09")
        if os.path.exists(cp):
            C = pd.read_csv(cp, dtype={"sid": str})
            J["F9分數(同分群)"] = C.sort_values(["grp", "F9"], ascending=[True, False]).to_dict("records")
    lk1 = lock_check(); J["策略鎖後"] = lk1[1]
    ok = lk0[0] and lk1[0] and X["tie"] == tie and len(X["buys"]) == H.NS
    assert not any(os.path.abspath(p).startswith(os.path.abspath("backtest/resultsDaily")) for p in [fwd])
    other = os.path.join(OUT, f"check_f9dry_{'抽籤' if tie == 'F9' else 'F9'}.json")
    if os.path.exists(other):
        Oj = json.load(open(other, encoding="utf-8"))
        A_ = {"抽籤": Oj if tie == "F9" else J, "F9": J if tie == "F9" else Oj}
        rows = []
        for k in range(max(len(A_["抽籤"]["名單"]), len(A_["F9"]["名單"]))):
            r_ = A_["抽籤"]["名單"][k] if k < len(A_["抽籤"]["名單"]) else ["", "", "", ""]
            f_ = A_["F9"]["名單"][k] if k < len(A_["F9"]["名單"]) else ["", "", "", ""]
            rows.append(f"{k + 1:>2}｜抽籤 {r_[0]} {r_[1]}｜F9 {f_[0]} {f_[1]}")
        rows.append("備位｜抽籤 " + "、".join(f"{s} {n}" for s, n in A_["抽籤"]["備位"]) + "｜F9 " + "、".join(f"{s} {n}" for s, n in A_["F9"]["備位"]))
        s1 = {x[0] for x in A_["抽籤"]["名單"]}; s2 = {x[0] for x in A_["F9"]["名單"]}
        rows.append(f"兩邊相同 {len(s1 & s2)} 檔；只在抽籤 {sorted(s1 - s2)}；只在 F9 {sorted(s2 - s1)}")
        J["並列"] = rows
        for x in rows:
            log("[⑧並列] " + x)
    J["通過"] = bool(ok)
    log(f"[⑧f9dry {tie}] 名單 {[b[0] for b in X['buys']]}｜備位 {X['backup']}｜同分 {X['tie']}｜策略鎖 {lk0[1]}／{lk1[1]}｜{'✅' if ok else '⛔'}｜{time.time() - t0:.0f}s")
    save(f"f9dry_{tie}", J)
    return ok


# ═════════════ ⑨ 三本紀錄並存（D11）＋ LINE 行（D12）端到端：起點假設 2026-04，9/30、10/01 兩個真快照連跑；⛔ 不是前瞻紀錄 ═════════════
B3 = [("2026-09-30", "~/h2data/indrev_5d20a7edcf07/data"), ("2026-10-01", "~/h2data/indrev_f65bb03e114a/data")]
B3_XD = "~/mktdropwork/fwd/dbfb96cb81/data"                       # 財報籌碼（⑧ 已建；只用排序日以前的資料）


def st_book3(a):
    day = int(a.day)
    asof, data = B3[day]
    J = {"階段": f"book3_{day}"}
    t0 = time.time()
    lk0 = lock_check(); J["策略鎖前"] = lk0[1]
    d = os.path.join(a.work, "book3"); fwd = os.path.join(d, "fwd")
    if day == 0:
        if os.path.exists(d):
            shutil.rmtree(d)
        for sub, keys_ in (("ranks", None), ("events", ("2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07"))):
            src = os.path.join(a.work, "e2e", "fwd", sub); os.makedirs(os.path.join(fwd, sub), exist_ok=True)
            for f in sorted(os.listdir(src)) if os.path.isdir(src) else []:      # ⑥ 同一組真快照算好的排序／已進場批事件快取（省時；只驗流程）
                if keys_ is None or any(k in f for k in keys_):
                    shutil.copy(os.path.join(src, f), os.path.join(fwd, sub, f))
    H.START_YM = 2026 * 12 + 3                                     # 測試：第一批進場月 2026-04（形成月 2026-02）
    tag0 = H.LINE_TAG; H.LINE_TAG = "- 【LINE】⭐ "; push0 = H.PUSH; H.PUSH = True
    md = os.path.join(d, f"daily_{asof}.md")
    shutil.copy(f"backtest/resultsDaily/daily_{asof}.md", md)
    orig = open(md, encoding="utf-8").read()
    prev = {f: open(os.path.join(fwd, f), encoding="utf-8-sig").read() for f in ("positions_f9.csv", "equity_f9.csv", "equity.csv")
            if os.path.exists(os.path.join(fwd, f))}
    try:
        ap = argparse.Namespace(asof=asof, md=md, sha=None, fwd=fwd, nowrite=False, preview_buy=False, procs=a.procs, data=data, tie="F9",
                                xd=os.path.expanduser(B3_XD))
        L, X = H.run(ap, log)
    finally:
        H.LINE_TAG = tag0; H.PUSH = push0
    chk = {}
    rd = lambda f: pd.read_csv(os.path.join(fwd, f), dtype=str, keep_default_na=False, encoding="utf-8-sig") if os.path.exists(os.path.join(fwd, f)) else None
    P, P9, U, E, E9 = rd("positions.csv"), rd("positions_f9.csv"), rd("positions_user.csv"), rd("equity.csv"), rd("equity_f9.csv")
    chk["md 其他段不變"] = open(md, encoding="utf-8").read().startswith(orig.rstrip("\n"))
    chk["positions_f9.csv、equity_f9.csv 存在且與照規則同欄"] = P9 is not None and E9 is not None and list(P9.columns) == H.POS_COLS and list(E9.columns) == H.EQ_COLS
    chk["equity_f9 日期 ＝ equity 日期（到資料日）"] = E9 is not None and E9["日期"].tolist() == E["日期"].tolist() and E9["日期"].iloc[-1] == asof
    chk["沒有 ⚠（F9 算得出）"] = not any("⚠" in x for x in L)
    line = [x for x in L if "【LINE】" in x]
    five = H.note_sents("F9")
    if line:
        k_ = L.index(line[0])
        chk["LINE 行開頭不變"] = line[0].startswith("- 【LINE】⭐ 52 週新高 10 檔（高10）：")
        chk["LINE 行不含五句"] = not any(s in line[0] for s in five)
        chk["下一行「  - 註：」有五句、不帶【LINE】"] = L[k_ + 1] == "  - 註：" + "｜".join(five)
    if day == 0:
        chk["9/30 有 LINE（明天 10/01 買）"] = bool(line) and "明天 2026-10-01 開盤買" in line[0]
        st_ = json.load(open(os.path.join(fwd, "state.json"), encoding="utf-8"))
        chk["名單存入 state（10/01、同分 F9）"] = st_["名單"].get("2026-10-01", {}).get("同分排序") == "F9"
        chk["F9 照規則已有紀錄（4 月批補滿 10 格起）"] = P9 is not None and int((P9["買進日"] == "2026-04-01").sum()) == H.NS and bool((P9["買進日"] >= "2026-04-01").all())
    if day == 1:
        chk["三本並存：positions.csv／positions_user.csv／positions_f9.csv 都有 10/01 買進"] = all(
            x is not None and int((x["買進日"] == "2026-10-01").sum()) > 0 for x in (P, U, P9))
        for f in ("positions_f9.csv", "equity_f9.csv", "equity.csv"):
            if f in prev:
                old = pd.read_csv(io.StringIO(prev[f]), dtype=str, keep_default_na=False)
                new = rd(f)
                cols = [c for c in old.columns if c not in ("賣出日", "賣出未還原收盤", "出場種類", "R用", "淨報酬", "狀態")]
                chk[f"{f} 只追加（day0 的列與買進欄凍結）"] = len(new) >= len(old) and new.iloc[:len(old)][cols].equals(old[cols])
        chk["10/01 無【LINE】"] = not line
    J.update({"段落": L, "檢查": chk, "照規則持有": [h[0] for h in X["held"]], "F9照規則持有": [h[0] for h in X["held9"]],
              "使用者持有（positions_user 持有中）": sorted(U.loc[U["狀態"] == "持有中", "代號"].tolist()) if U is not None else [],
              "照規則 vs F9 照規則 買進不同筆": (len(set(zip(P["批次"], P["代號"])) ^ set(zip(P9["批次"], P9["代號"]))) if P9 is not None else None)})
    lk1 = lock_check(); J["策略鎖後"] = lk1[1]
    ok = all(chk.values()) and lk0[0] and lk1[0]
    J["通過"] = bool(ok)
    log(f"[⑨三本 day{day} {asof}] {chk}｜策略鎖 {lk0[1]}／{lk1[1]}｜{'✅' if ok else '⛔'}｜{time.time() - t0:.0f}s")
    save(f"book3_{day}", J)
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="fixture", choices=("world", "rank", "replay", "fixture", "dry", "e2e", "f9replay", "f9dry", "book3"))
    ap.add_argument("--day", default="0")
    ap.add_argument("--tie", default="F9", choices=H.TIES)
    ap.add_argument("--work", default=os.path.expanduser("~/pth10work")); ap.add_argument("--procs", type=int, default=4)
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    ok = {"world": st_world, "rank": st_rank, "replay": st_replay, "fixture": st_fixture, "dry": st_dry, "e2e": st_e2e,
          "f9replay": st_f9replay, "f9dry": st_f9dry, "book3": st_book3}[a.stage](a)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
