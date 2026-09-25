# -*- coding: utf-8 -*-
"""PREREG型態全量 §六【頻率表】——只數事件的日期與個數、剔除計數、n_eff 上限；判準＝台股策略線 型態全量登錄 seq1（sha 4a90c43e04a0bef5）
§二、§六、§九；編號＝裁定線 seq173「PREREG型態全量」（§一：現在只寫偵測器＋fixture、交 §六 頻率表；§二④ 附方向與事前門檻對照表）。

⛔⛔ 本支不讀、不算、不存任何報酬：不讀 T＋1 以後的收盤、不算 R_e／X／基準／勝率。
   剔除只判「能不能成交／資料斷不斷」：硬斷點、T＋1 停牌、T＋1 開盤漲停／跌停（tradability.one，原始價）⇒ ⛔ 不看價差。
   事件檔只含 sid、T、first、方向、事前量（r10／r20／r60）、型態期間報酬（C_T ÷ 第 1 根前一日收盤 − 1：T 以前的形狀量，裁定 seq173 §二①）、狀態。

資料、母體、讀檔、硬斷點、下市：與 PREREGH2／PREREGM 同一份快照與同一套函式（import researchH2：main edc6f8002f、gate3、H2.brk；
   researchM_freq._g5：delist on ⇒ 最後成交之後的缺日不算連續缺日）。
偵測器：backtest/patterns_all.py；fixture：backtest/selftest_patterns_all.py（⭐ 本支開跑前先全跑；不過的變體在表上標「T1 不過」、照報）。

⭐ 登錄沒逐字寫、本支的落地讀法（⛔ 在看任何頻率之前寫在這裡；交件逐條列出；★ ＝ 兩種讀法擇一、另一讀法的數字並列）：
 Q1 事件須 T ∈ [2017-03-02, 窗尾 − H]（交易日曆；T＋1＋(H−1) ≤ 窗尾 ⇔ T＋H ≤ 窗尾）⇒ 三個 H 的原始事件數不同（H 越長、尾端越短）。
 Q2 ★ 處理順序：先合併、再剔除（登錄 §九「原始／合併後事件數、剔除數」的順序）：同檔同變體依時間走，T 落在「上一個未被合併的事件 t0」的
    (t0, t0＋20]（交易日曆）⇒ 合併掉（不看該 t0 後來有沒有被剔除）；未被合併者再判剔除（硬斷點 → T＋1 停牌 → T＋1 開盤漲停 → T＋1 開盤跌停，
    只記第一個原因）。〔另一讀法（H2 R5／PREREGM Q2）：被剔除者不開合併窗 ⇒ 並列「保留_另一順序」〕。
 Q3 T＋1 停牌 ＝ T＋1（交易日曆）無成交（tradability.one 的 trd 為假）或還原開盤缺值；開盤漲停／跌停 ＝ tradability.one 的 up_o／dn_o。
    ★ 登錄「T＋1 開盤漲停／跌停或停牌 ⇒ 剔除」⇒ 漲停與跌停都剔（不分 d 的正負）。
 Q4 硬斷點（同 H2 R3、PREREGM Q4）：① 價格：相鄰有效 K 棒 close 比 ≤ 0.55 或 ≥ 1.8 且其間無 data/adj 事件；② 時間：連續 ≥ 5 個交易日
    無有效 K 棒（5 個缺日全在範圍內）；範圍 ＝ [型態第一根（或第一個轉折）first, T＋H]（登錄 §二）。
 Q5 delist on（同 PREREGM Q5）：delisted_official／delisted_gap 的股票，最後成交之後的無成交日 ⛔ 不算 ② 的連續缺日。
 Q6 每檔每年：分子 ＝ 該檔該 H 保留事件數；分母 ＝ 該檔在 [窗起點, 窗尾−H] 內從首個到最後一個有效 K 棒所跨交易日數 ÷ 每年交易日數；
    分佈（平均／中位／p90）只取曝露 ≥ 1 年的股票（含零事件者）；另報合併母體比率（總事件 ÷ 總股票年）。上市／上櫃依快照 stocks.csv 的 market 欄。
 Q7 n_eff 上限（登錄 §六）：H20 ＝ min(保留事件數, 有事件的曆月數)（上限約 115）；H60 ＝ min(保留事件數, 有事件的 60 日區段數)
    （區段號 ＝ (T − 窗起點)//60，交易日曆，上限 38）；H120 ＝ 同式 120 日區段（上限 19，只描述）。
    依構造可能出口：n_eff 上限 ＜ 30 ⇒【依構造不可判定】；H20：30～99 ⇒ ①②、≥ 100 ⇒ ①②③；H60：≥ 30 ⇒ ①②（區段上限 38 ＜ 100）；
    H120 ⇒ 只描述（登錄 §六「全族只描述」）。判定格只算 H20、H60。
 Q8 重疊（登錄 §二、§九）：同一檔同一天（原始事件、H20 窗內、合併前）兩變體同時成立的件數 ÷ 兩者較少的那個。
"""
from __future__ import annotations
import os, sys, time, json, gzip, hashlib
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
import researchH2 as H2                             # ⭐ 同一份快照、同一套讀檔／斷點（D.DATA 已被指到快照）
import researchM_freq as MF                         # _g5（delist on）
D, TR, UG = H2.D, H2.TR, H2.UG
from backtest import patterns_all as PA
from backtest import selftest_patterns_all as SPA

OUT = "backtest/resultsPatAll"
W0, W1, WIN_DAYS, SHA = H2.W0, H2.W1, H2.WIN_DAYS, H2.SHA
HS = (20, 60, 120)
MERGE = 20
BLK = {20: None, 60: 60, 120: 120}
ATT = "/mnt/c/SynologyDrive/跨線信箱/附件-型態知識庫全量_型態線_20260925-1910"
HC_FILE, HC_SHA = "K棒型態方向可信度健檢總表.md", "12a43951a2f93c0e5d57f8289b6c4cb7a94f2b5e5f962b067e7919f408482209"
UT_FILE, UT_SHA = "還沒測的型態與飆股評分.md", "0b35119f28e204e01879b37184182ccecf232b24f10684eed5da8936f3578086"
ST_ORDER = ["保留", "合併掉", "剔除_硬斷點", "剔除_T+1停牌", "剔除_T+1開盤漲停", "剔除_T+1開盤跌停"]


# ═════════════ 方向與事前門檻對照表（裁定 seq173 §二④） ═════════════
def _read_att(fn, sha):
    b = open(os.path.join(ATT, fn), "rb").read()
    got = hashlib.sha256(b).hexdigest()
    assert got == sha, "⛔ {} sha256 {} ≠ manifest {}".format(fn, got, sha)
    return b.decode("utf-8")


def _table(txt, head):
    """取 `head` 段落（到下一個 ## 為止）的 markdown 表格列 ⇒ list[list[cell]]（去掉表頭與分隔列）。"""
    seg = txt.split(head, 1)[1].split("\n## ", 1)[0]
    rows = [ln.strip() for ln in seg.splitlines() if ln.strip().startswith("|")]
    return [[c.strip() for c in r.strip("|").split("|")] for r in rows[2:]]


def derive(name_dir, measured, verdict):
    """登錄 §三 的規則，機械套在健檢總表兩欄上 ⇒ (事前, d)。"""
    if "無明確方向" in name_dir:
        pre = "無"
    elif "看漲反轉" in name_dir or "看跌續勢" in name_dir:
        pre = "降"
    elif "看跌反轉" in name_dir or "看漲續勢" in name_dir:
        pre = "升"
    else:
        pre = "?"
    v = verdict.lstrip("⚠")
    sgn = 1 if pre == "升" else -1
    if "反轉當續勢" in v:
        d = sgn
    elif "續勢當反轉" in v:
        d = -sgn
    elif "定義上就是續勢" in v:
        d = sgn
    elif v.startswith("一致"):
        d = 1 if "看漲" in name_dir else -1
    elif "接近隨機" in v and pre == "無":
        d = "續" if "續勢" in measured else ("反" if "反轉" in measured else "?")
    else:
        d = "?"
    return pre, d


def direction_table():
    hc = _table(_read_att(HC_FILE, HC_SHA), "## 總表")
    ut = _table(_read_att(UT_FILE, UT_SHA), "## 十七個還沒回測過的型態")
    rows = []
    for v in PA.VARIANTS:
        if v["fam"] == "K":
            key = v["hc"]
            hit = [r for r in hc if r[0] == key or r[0].startswith(key + " ")]
            assert len(hit) == 1, (key, [r[0] for r in hit])
            r = hit[0]
            pre, d = derive(r[2], r[3], r[4])
            rows.append({"vid": v["vid"], "登錄#": int(v["vid"][1:]), "型態（登錄）": v["name"], "健檢總表列名": r[0], "型態性質": r[1],
                         "名稱隱含方向": r[2], "實測數字": r[3], "方向判定": r[4], "整體表現排名": r[5],
                         "推出_事前": pre, "推出_d": d, "登錄_事前": v["pre"], "登錄_d": v["d"],
                         "一致": (pre == v["pre"] and str(d) == str(v["d"]))})
        else:
            hit = [r for r in ut if r[0] == v["src"]]
            src = hit[0][1] if hit else "（表內無此列）"
            rows.append({"vid": v["vid"], "登錄#": v["vid"], "型態（登錄）": v["name"], "健檢總表列名": "（價格結構：出處 還沒測的型態 表）",
                         "型態性質": "", "名稱隱含方向": src, "實測數字": "", "方向判定": "", "整體表現排名": "",
                         "推出_事前": "r60 頂＞0／底＜0（登錄 §四）" if v["vid"] in ("S01", "S02", "S03", "S22", "S23", "S24", "S25", "S26") or "擴散" in v["name"] or "鑽石" in v["name"] else "—",
                         "推出_d": "突破方向（seq171 §三③）" if "向" in v["name"] else v["d"], "登錄_事前": "", "登錄_d": v["d"], "一致": ""})
    return pd.DataFrame(rows)


# ═════════════ 讀檔、逐檔 ═════════════
def load_raw(sid, cal):
    p = os.path.join(D.DATA, "stocks", f"{sid}.csv")
    raw = pd.read_csv(p, dtype={"date": str}, usecols=["date", "open", "high", "low", "close"])
    raw["date"] = pd.to_datetime(raw["date"]); raw = raw.drop_duplicates("date").set_index("date").sort_index()
    for c in ("open", "high", "low", "close"):
        raw[c] = pd.to_numeric(raw[c], errors="coerce")
    bad = (raw[["open", "high", "low", "close"]] <= 0).any(axis=1)
    raw.loc[bad, ["open", "high", "low", "close"]] = np.nan         # ⭐ 與 data.load_stock 同一條
    raw = raw.reindex(cal)
    return [raw[c].to_numpy(float) for c in ("open", "high", "low", "close")]


def one_stock(sid, market, cal, w0, w1, off):
    st = D.load_stock(sid, market, cal)
    if st is None:
        return None
    df = st.df
    o, h, l, c, v = (df[k].to_numpy(float) for k in ("open", "high", "low", "close", "volume"))
    valid = np.isfinite(c); bars = np.flatnonzero(valid)
    if len(bars) == 0:
        return None
    ro, rh, rl, rc = load_raw(sid, cal)
    ev = PA.detect_calendar(o, h, l, c, v, ro, rh, rl, rc)
    pb = np.zeros(len(cal), bool)
    for b_ in D.breakpoints(df, st.event_dates):
        if b_["rule"] in ("price", "price+gap"):
            pb[b_["pos"]] = True
    tb = TR.one(sid, cal)
    ds = TR.delist_status({sid: tb}, cal, official=off).get(sid)
    delisted = ds is not None and ds["status"].startswith("delisted")
    g5 = MF._g5(valid, upto=ds["last"]) if delisted else MF._g5(valid)
    S = {"cs_pb": np.cumsum(pb).astype(np.int32), "cs_g5": np.cumsum(g5).astype(np.int32)}
    expo = {H: max(0, min(int(bars[-1]), w1 - H) - max(int(bars[0]), w0) + 1) for H in HS}
    return {"sid": sid, "market": market, "ev": ev, "S": S, "tb": tb, "o": o, "expo": expo,
            "status": ds["status"] if ds else None, "nan_open": int(np.sum(valid & ~np.isfinite(o)))}


def classify(X, w0, w1):
    """單檔 ⇒ {vid: DataFrame 列（T、first、d、事前量、狀態_H…）}＋另一順序保留數。"""
    out = {}
    tb, S, o = X["tb"], X["S"], X["o"]
    for vid in PA.VID:
        e = X["ev"][vid]
        m = (e["T"] >= w0) & (e["T"] <= w1 - HS[0])
        if not m.any():
            continue
        T = e["T"][m]; first = e["first"][m]
        merged = np.zeros(len(T), bool); t0 = -10 ** 9
        for i, t in enumerate(T):                                  # Q2 先合併（純 20 日）
            if t0 < t <= t0 + MERGE:
                merged[i] = True
            else:
                t0 = t
        halt = np.array([(not bool(tb["trd"][t + 1])) or (not np.isfinite(o[t + 1])) for t in T])
        up = np.array([bool(tb["up_o"][t + 1]) for t in T]); dn = np.array([bool(tb["dn_o"][t + 1]) for t in T])
        st = {}; alt = {}
        for H in HS:
            s = []
            ta = -10 ** 9; na = 0
            for i, t in enumerate(T):
                if t + H > w1:
                    s.append("窗外"); continue
                brk = H2.brk(S, int(first[i]), int(t) + H)
                why = "剔除_硬斷點" if brk else ("剔除_T+1停牌" if halt[i] else ("剔除_T+1開盤漲停" if up[i] else ("剔除_T+1開盤跌停" if dn[i] else None)))
                s.append("合併掉" if merged[i] else (why or "保留"))
                if not (ta < t <= ta + MERGE) and why is None:          # 另一順序：被剔除者不開合併窗
                    na += 1; ta = t
            st[H] = s; alt[H] = na
        out[vid] = {"T": T, "first": first, "d": e["d"][m], "r10": e["r10"][m], "r20": e["r20"][m], "r60": e["r60"][m],
                    "prd": e["prd"][m], "st": st, "alt": alt, "merged": merged}
    return out


def qd(x):
    x = np.asarray(x, float)
    if len(x) == 0:
        return {"n": 0}
    return {"n": int(len(x)), "平均": round(float(x.mean()), 4), "中位": round(float(np.median(x)), 4),
            "p90": round(float(np.percentile(x, 90)), 4), "零事件佔比": round(float((x == 0).mean()), 4)}


def f6(x):
    return "" if not np.isfinite(x) else "{:.6g}".format(float(x))


def main():
    t0 = time.time()
    lim = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    out_dir = OUT if lim is None else os.path.join(OUT, "_try")
    os.makedirs(out_dir, exist_ok=True)
    # ── fixture（⭐ 先跑；不過的變體照報）
    fx = SPA.run_all(verbose=False)
    T1 = {r["vid"]: bool(r["T1"]) for r in fx["逐變體"]}
    print("[fixture] T1 過 {}／96｜全族 {}｜{:.0f}s".format(fx["T1過"], "過" if fx["全族過"] else "⛔ 不過", time.time() - t0), flush=True)
    # ── 方向表
    DT = direction_table()
    DT.to_csv(os.path.join(out_dir, "direction_table.csv"), index=False, encoding="utf-8-sig")
    nbad = int((DT["一致"] == False).sum())                                  # noqa: E712
    print("[方向表] K 棒 68 列：規則推出 vs 登錄 不一致 {} 列".format(nbad), flush=True)
    # ── 母體
    cal = D.load_calendar()
    w0 = int(cal.searchsorted(pd.Timestamp(W0))); w1 = int(cal.searchsorted(pd.Timestamp(W1)))
    assert str(cal[w0].date()) == W0 and str(cal[w1].date()) == W1 and w1 - w0 + 1 == WIN_DAYS
    DPY = {H: (w1 - H - w0 + 1) / ((cal[w1 - H] - cal[w0]).days / 365.25) for H in HS}
    stocks = pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str)
    U = UG.gate3(stocks)
    if lim:
        U = U.head(lim)
    off = TR.load_official()
    ym = np.array([str(d)[:7] for d in cal]); yr = np.array([d.year for d in cal])
    print("[資料] 快照 {}｜判定窗 [{}, {}] {} 日｜gate3 {:,} 檔｜每年交易日 {}".format(SHA[:10], W0, W1, WIN_DAYS, len(U),
          {H: round(v, 2) for H, v in DPY.items()}), flush=True)
    # ── 累加器
    ACC = {(vid, H): {"原始": 0, "純合併後": 0, **{k: 0 for k in ST_ORDER}, "保留_另一順序": 0, "月": set(), "區段": set(),
                      "年": {}, "市": {}, "檔": set(), "d+": 0, "d-": 0} for vid in PA.VID for H in HS}
    PER = []                                              # 每檔：sid, market, expo[H], 保留數[vid][H]
    OV = np.zeros((96, 96), np.int64)
    VI = {v: i for i, v in enumerate(PA.VID)}
    W = {}
    for vid in PA.VID:
        nm = PA.VMAP[vid]["name"].replace(" ", "_")
        f = gzip.open(os.path.join(out_dir, "events_{}_{}.csv.gz".format(vid, nm)), "wt", encoding="utf-8", compresslevel=6)
        f.write("sid,market,T,first,方向,r10,r20,r60,型態期間報酬,狀態_H20,狀態_H60,狀態_H120\n")
        W[vid] = f
    diag = {"可用檔數": 0, "有效K棒但還原open缺值": 0, "下市狀態": {}}
    for k, (sid, market) in enumerate(zip(U["stock_id"], U["market"])):
        X = one_stock(sid, market, cal, w0, w1, off)
        if X is None:
            continue
        diag["可用檔數"] += 1; diag["有效K棒但還原open缺值"] += X["nan_open"]
        diag["下市狀態"][str(X["status"])] = diag["下市狀態"].get(str(X["status"]), 0) + 1
        C = classify(X, w0, w1)
        kept = {}
        M = np.zeros((len(cal), 96), np.int8)
        for vid, R in C.items():
            T = R["T"]
            M[T, VI[vid]] = 1
            lines = []
            for i in range(len(T)):
                lines.append("{},{},{},{},{},{},{},{},{},{},{},{}\n".format(
                    sid, market, cal[T[i]].date(), cal[R["first"][i]].date(), int(R["d"][i]), f6(R["r10"][i]), f6(R["r20"][i]),
                    f6(R["r60"][i]), f6(R["prd"][i]), R["st"][20][i], R["st"][60][i], R["st"][120][i]))
            W[vid].write("".join(lines))
            for H in HS:
                A = ACC[(vid, H)]; s = np.array(R["st"][H])
                inw = s != "窗外"
                A["原始"] += int(inw.sum()); A["純合併後"] += int((inw & ~R["merged"]).sum()); A["保留_另一順序"] += R["alt"][H]
                for kk in ST_ORDER:
                    A[kk] += int((s == kk).sum())
                ks = T[s == "保留"]
                if len(ks):
                    A["檔"].add(sid)
                    A["月"].update(ym[ks].tolist())
                    A["區段"].update(((ks - w0) // (BLK[H] or 1)).tolist())
                    for y in yr[ks]:
                        A["年"][int(y)] = A["年"].get(int(y), 0) + 1
                    A["市"][market] = A["市"].get(market, 0) + len(ks)
                    dd = R["d"][s == "保留"]
                    A["d+"] += int((dd > 0).sum()); A["d-"] += int((dd < 0).sum())
                kept[(vid, H)] = len(ks)
        wm = (np.arange(len(cal)) >= w0) & (np.arange(len(cal)) <= w1 - 20)
        Mi = M[wm].astype(np.int32)
        OV += Mi.T @ Mi
        PER.append({"sid": sid, "market": market, **{"expo{}".format(H): X["expo"][H] for H in HS},
                    **{"{}_{}".format(v, H): kept.get((v, H), 0) for v in PA.VID for H in HS}})
        if (k + 1) % 200 == 0:
            print("  … {:,}／{:,} 檔｜{:.0f}s".format(k + 1, len(U), time.time() - t0), flush=True)
    for f in W.values():
        f.close()
    P = pd.DataFrame(PER)
    # ── 彙整
    rows = []; J = {}
    for vid in PA.VID:
        v = PA.VMAP[vid]
        row = {"vid": vid, "型態": v["name"], "族": v["fam"], "根數": v["k"] if v["k"] else "", "事前": v["pre"] or "",
               "d": v["d"], "T1": "過" if T1[vid] else "T1 不過"}
        jj = {}
        for H in HS:
            A = ACC[(vid, H)]
            n = A["保留"]
            nm_ = len(A["月"]); nb = len(A["區段"])
            if H == 20:
                ne = min(n, nm_); unit = "曆月"
                ex = "依構造不可判定" if ne < 30 else ("①②" if ne < 100 else "①②③")
            elif H == 60:
                ne = min(n, nb); unit = "60日區段"
                ex = "依構造不可判定" if ne < 30 else "①②"
            else:
                ne = min(n, nb); unit = "120日區段"
                ex = "只描述（H120 依構造只到①）"
            yrs = P["expo{}".format(H)] / DPY[H]
            rate = P["{}_{}".format(vid, H)] / yrs.where(yrs > 0)
            ok1 = yrs >= 1.0
            pooled = float(P["{}_{}".format(vid, H)].sum() / yrs.sum())
            row.update({"原始_H{}".format(H): A["原始"], "純合併後_H{}".format(H): A["純合併後"], "合併掉_H{}".format(H): A["合併掉"],
                        "剔除_硬斷點_H{}".format(H): A["剔除_硬斷點"], "剔除_停牌_H{}".format(H): A["剔除_T+1停牌"],
                        "剔除_開盤漲停_H{}".format(H): A["剔除_T+1開盤漲停"], "剔除_開盤跌停_H{}".format(H): A["剔除_T+1開盤跌停"],
                        "保留_H{}".format(H): n, "保留_另一順序_H{}".format(H): A["保留_另一順序"], "相異檔數_H{}".format(H): len(A["檔"]),
                        ("有事件曆月_H20" if H == 20 else "有事件區段_H{}".format(H)): (nm_ if H == 20 else nb),
                        "n_eff上限_H{}".format(H): ne, "可能出口_H{}".format(H): ex,
                        "每檔每年_H{}".format(H): round(pooled, 4),
                        "上市_H{}".format(H): A["市"].get("twse", 0), "上櫃_H{}".format(H): A["市"].get("tpex", 0)})
            jj["H{}".format(H)] = {"事件帳": {k_: A[k_] for k_ in ("原始", "純合併後", *ST_ORDER, "保留_另一順序")},
                                   "相異檔數": len(A["檔"]), "有事件曆月": nm_, "有事件區段({})".format(unit): nb if H != 20 else None,
                                   "n_eff上限": ne, "n_eff單位": unit, "可能出口": ex,
                                   "每檔每年": {"合併母體比率": round(pooled, 4), "曝露≥1年": qd(rate[ok1].fillna(0).to_numpy())},
                                   "逐年保留": dict(sorted(A["年"].items())), "市場別保留": {"上市": A["市"].get("twse", 0), "上櫃": A["市"].get("tpex", 0)},
                                   "保留中d": {"+1": A["d+"], "−1": A["d-"]}}
        for y in range(2017, 2027):
            row["H20_{}年".format(y)] = ACC[(vid, 20)]["年"].get(y, 0)
        row["可判定_H20"] = row["可能出口_H20"] != "依構造不可判定"
        row["可判定_H60"] = row["可能出口_H60"] != "依構造不可判定"
        rows.append(row); J[vid] = {"型態": v["name"], "T1": row["T1"], **jj}
    F = pd.DataFrame(rows)
    F.to_csv(os.path.join(out_dir, "freq.csv"), index=False, encoding="utf-8-sig")
    # ── 重疊
    diag_ = np.diag(OV)
    pairs = []
    for i in range(96):
        for j in range(i + 1, 96):
            if OV[i, j] > 0:
                pairs.append({"a": PA.VID[i], "b": PA.VID[j], "a名": PA.VMAP[PA.VID[i]]["name"], "b名": PA.VMAP[PA.VID[j]]["name"],
                              "同日件數": int(OV[i, j]), "a件數": int(diag_[i]), "b件數": int(diag_[j]),
                              "重疊率_對較少者": round(float(OV[i, j] / min(diag_[i], diag_[j])), 4)})
    pairs.sort(key=lambda p: -p["重疊率_對較少者"])
    named = [("K24", "K22"), ("K50", "K67"), ("K50", "K59"), ("K55", "K49"), ("K55", "K62"), ("K56", "K51"), ("K61", "K31"),
             ("K25", "K33"), ("K46", "K52"), ("K08", "K19"), ("K16", "K39"), ("K30", "K58"), ("K42", "K57"), ("K54", "K40")]
    ovn = {"{}×{}".format(a, b): next((p for p in pairs if {p["a"], p["b"]} == {a, b}), {"同日件數": 0}) for a, b in named}
    n20 = int(F["可判定_H20"].sum()); n60 = int(F["可判定_H60"].sum())
    R_ = {"性質": "PREREG型態全量 §六 頻率表（⛔ 未讀、未算任何報酬）", "登錄": "型態全量_單筆層登錄 台股策略線 seq1 sha 4a90c43e04a0bef5",
          "編號": "PREREG型態全量（裁定線 seq173）", "快照": SHA, "判定窗": [W0, W1], "gate3母體": int(len(U)), "每年交易日": {H: round(x, 3) for H, x in DPY.items()},
          "資料診斷": diag,
          "fixture": {"T1過": fx["T1過"], "全族過": fx["全族過"], "T1不過": [r["vid"] for r in fx["逐變體"] if not r["T1"]],
                      "全族": {k: v for k, v in fx["全族"].items() if k != "隨機序列事件數"},
                      "逐變體": [{k: r.get(k) for k in ("vid", "name", "T", "F1", "F2", "F3", "F4", "差一點", "差一點過", "T1")} for r in fx["逐變體"]]},
          "可判定格數": {"H20": n20, "H60": n60, "合計": n20 + n60},
          "依構造不可判定清單": {"H20": F.loc[~F["可判定_H20"], ["vid", "型態", "n_eff上限_H20"]].values.tolist(),
                           "H60": F.loc[~F["可判定_H60"], ["vid", "型態", "n_eff上限_H60"]].values.tolist()},
          "方向表_規則推出與登錄不一致": DT.loc[DT["一致"] == False, ["vid", "型態（登錄）", "推出_事前", "推出_d", "登錄_事前", "登錄_d"]].values.tolist(),  # noqa: E712
          "重疊_指名配對": ovn, "重疊_前40": pairs[:40], "變體": J}
    json.dump(R_, open(os.path.join(out_dir, "freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("[完成] 可判定格 H20 {}、H60 {}｜{:.0f}s".format(n20, n60, time.time() - t0), flush=True)
    cols = ["vid", "型態", "T1", "原始_H20", "純合併後_H20", "保留_H20", "每檔每年_H20", "n_eff上限_H20", "可能出口_H20", "保留_H60", "n_eff上限_H60", "可能出口_H60", "n_eff上限_H120"]
    print(F[cols].to_string(index=False))


if __name__ == "__main__":
    main()
