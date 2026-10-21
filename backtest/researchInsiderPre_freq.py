# -*- coding: utf-8 -*-
"""董監／大股東申報轉讓後偏弱 seq2【頻率表・乾跑】（台股策略線 登錄 sha 3e8056296f03d825，2026-10-21 00:20；裁定 seq407 第三題、seq408 發號、
seq412 §六 准開頻率表（贈與、信託另組；可用日＝申報日）；Seyhun 1986、Lakonishok & Lee 2001）——回測線計算子代理。
避開名單的事件層描述（N 不計，seq407）。
⛔ 只數事件、剔除計數、n_eff、配對可行性；⛔ 不讀、不算、不存任何進場後的價格、報酬、持有期結果。
   價格只用 ≤ 申報日 T 的還原收盤（前 12 個月報酬，只用來分五分位、⛔ 不存）、T 市值與已發行股數、500 張閘，與進場日 e 的成交／開盤／鎖漲停旗標。
⛔ 不 commit、不改既有程式與結果夾；researchIndMom_freq（共用面板）、researchSEO_freq（xsec）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchInsiderPre_freq
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchInsiderPre_freq_check
輸出 backtest/resultsInsiderPre/freq/：freq.json、freq.csv、by_year.csv、status.csv、match.csv、equiv.csv、events.csv.gz、run.log
（events 只有代號、日期、組、剔除原因、比例、配對候選數；⛔ 無姓名、無 holder_key）

═══ 讀法（Q 標；⛔ 在看任何本件數字之前寫死於 2026-10-21（台北）；★＝執行者定，〔 〕內為另一讀法）═══
 Q1 事件表 ＝ tw-stock-data 最新 origin/main 的 data/meta/insider_predeclare/insider_predeclare_*.csv（git archive 到 ~/b2fwork/ipf_main_<sha12>，唯讀）。
    市場 ＝ market 欄（申報當時市場）∈ {sii, otc}；rotc（興櫃）整列不納（登錄 §二）。可用日 ＝ declare_date（⛔ 不用 valid_start）。
 Q2 組（登錄 §二，method_raw 以「|」拆成各方式後逐一判）：含「一般交易」「盤後定價」「鉅額」「拍賣」⇒ 一般交易；含「贈與」⇒ 贈與；含「信託」⇒ 信託；
    其餘（洽特定人、轉讓私募股票、辦理過額配售…）⇒ 其他；一列跨兩組以上 ⇒ 混合。
    信託列受讓人含「限制員工」⇒ 其他：★ 受讓人原文不在公開庫，只能用 transferee_type＝employee_trust 或 transferee_org 含「限制員工」判
    （⚠ 資料庫的 transferee_type 先判「信託／銀行」，銀行受託的限制員工信託會落在 trust_bank ⇒ 這條規則本表判不出，照報）。
 Q3 列股數（資料庫使用規則）：一般交易組 ＝ shares（多種方式時 shares_split 加總；shares 空白 ⇒ plan_own＋plan_trust，計數）；
    其他各組 ＝ plan_own＋plan_trust。★ 同一發內完全相同的列（資料庫照官方保留）合併事件時照算，加總股數時只算一次。
 Q4 合併（登錄「同公司 30 個交易日內多筆申報合併為一事件（首筆日）」）：★ 逐組、逐公司（stock_id，不分 sii／otc）、依申報日排序；
    列的交易日位置 p ＝ 申報日當天或之前最後一個交易日；p − 錨點 p ≤ 30 ⇒ 併入該事件，否則開新事件（錨點 ＝ 新事件首筆）〔另一讀法：鏈式，與上一列比〕。
    ★ 交易日曆 ＝ 早年世界日曆 ∪ 主世界日曆；2004-02-11 以前（無價格資料）用週一～五補。
    ★ 一般交易組與贈與組等各自合併（主判只用一般交易）；同公司同期兩組都有 ⇒ 兩組都算、重疊照報（Q10）。
 Q5 事件日 d ＝ 首筆申報日。T ＝ d 當天或之前最後交易日（500 張閘在 T 判：Frame.gate[T]，t−20～t−1 均量 ≥ 500 張 ∧ 20 日有成交）；
    進場 e ＝ d 之後第一個交易日（登錄「事件日下一交易日開盤起算」）。世界 ＝ e 所在世界（e ≤ 2014-12-31 ⇒ 早年 eotc，否則主 H2D）；
    T 不在同一世界 ⇒「跨世界接縫」；d 早於 2004-02-11 ⇒「早於價格資料」；e 超出日曆 ⇒「超出資料尾」；
    ★ 早年世界上櫃 T ＜ 2007-07-02 ⇒「上櫃早於2007-07無股價」（登錄 §三「上櫃股價 2007-07 起」）。
 Q6 母體與進場剔除（SEO／PTH 頻率表同序）：四碼普通股（PRE.okcode）→ 世界 → 在面板（UG.gate3(GATE_V2) ∩ load_bars ≥ 260 根、含已下市）
    → 500 張閘 ∧ pit_valid ∧ T 有 K 棒 → 壞根(T,e]（缺口 ≥ 5 日 seq335；早年 reduce_v2）→ e 無成交 → e 開盤鎖漲停；保留 ＝ 事件。
 Q7 段（依 e）：探索 2017-03-01～2021-12-31｜確認 2022-01-01～資料尾｜早年 2003-05-01～2016-12-31（描述）。
    持有 h ＝ 20／60／250 交易日「走完」⇔ e 的合併日曆位置 ＋ h ≤ 主世界資料尾（★ 早年事件持有跨入 2015 主世界者另計「持有跨世界」）。
    n_eff ＝ min(事件數, 有事件的申報月數)（CI 申報月分群，登錄 §三）；★ 以 60 日走完者為判定用 n_eff；＜ 30 ⇒ 標「依構造不可判定」。
 Q8 身分（登錄 §二）：role 依序含「大股東」⇒ 大股東；含「董事」「監察人」⇒ 董監；含「經理人」⇒ 經理人；其餘（特定人）⇒ 其他身分。
    ★「子公司…」身分照字樣歸類（例 子公司經理人 ⇒ 經理人），另報子公司列數。分項：利用他人名義 → 未成年子女 → 配偶 → 本人（依序），
    「及由受託人持有者」另旗標。★ 事件層身分 ＝ 事件內任一列屬該類（一事件可屬多類）。
 Q9 股數占比（登錄 §二）＝ 事件內各列預定轉讓股數（Q3）加總 ÷ T 當天或之前最後一筆已發行股數（主 H2D stocks/<sid>.csv shares；早年 eotc daily_all.pkl
    shares）；★ 加總含 30 日內併入的後續列〔另一讀法：只算首筆申報日的列，另報 ≥1% 筆數〕。≥ 1% ／＜ 1%；股數不可得 ⇒「占比不可算」。
 Q10 配對可行性（登錄 §二；⛔ 只數候選、不取任何配對後價格）：橫斷面 ＝ T 當天母體（Q6 閘 ∧ 前 12 個月報酬可算 ∧ 市值 ＞ 0；SEO 頻率表 S8 同式，
    SQ.xsec 原樣）；前 12 個月報酬五分位切點含事件公司。★「同月」讀成同一 T 橫斷面。
    非申報 ＝ 事件表【全部列】（任何方式、任何市場）中 [p − 60, p ＋ 60] 交易日內沒有申報的公司（p ＝ T 的合併日曆位置）；
    ⚠ 此排除用到 T 之後 60 日的申報（控制組定義，登錄原文）；p ＋ 60 超過日曆尾者向後只看到表尾（照報）。
    主配對池 ＝ 非申報 ∧ 同前 12 個月報酬五分位，池內取市值最接近（|log 市值比| 最小）1 家；池空 ⇒ 配對失敗；事件公司自身不可算 ⇒「配對不可算」。
 Q11 已下市 ＝ 代號不在 origin/main stocks.csv 或其 last_seen 早於最晚 last_seen 10 天以上（SEO S7 同）。
 Q12 seq377 乾跑等價／退化：混合組、信託→其他（限制員工）筆數；一般交易 vs 贈與／信託／其他 同公司 0／30 日內重疊；
     ★ 與既有件（情報線用 insider_monthly IRB140 實際轉讓 ≥100 萬股）對照：一般交易保留事件中，同代號 IRB140 data_ym ∈ {申報月, 次月} 的比例
     （只描述，登錄未要求；IRB140 2006-01～2026-08）。
 Q13 假訊號臂：登錄未列 ⇒ 不做（照報）。
"""
from __future__ import annotations

import gzip
import json
import os
import subprocess
import sys
import time
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchIndMom_freq as IM              # noqa: E402  共用面板（⛔ 只 import）
from backtest import researchSEO_freq as SQ                 # noqa: E402  xsec（⛔ 只 import）
from backtest import researchIndRev_prereg as PRE           # noqa: E402  okcode

REG_SHA = "3e8056296f03d825"
OUT = "backtest/resultsInsiderPre/freq"
PARTS = ["data/meta/insider_predeclare", "data/meta/insider_monthly", "data/meta/stocks.csv"]
GROUPS = ("一般交易", "贈與", "信託", "其他", "混合")
GEN_KW = ("一般交易", "盤後定價", "鉅額", "拍賣")
SEGS = {"探索": ("2017-03-01", "2021-12-31"), "確認": ("2022-01-01", None), "早年": ("2003-05-01", "2016-12-31")}
HOLDS = (20, 60, 250)
MERGE_TD = 30
CTRL_TD = 60
NEFF_MIN = 30
OTC_EARLY = pd.Timestamp("2007-07-02")
EOTC_DAILY = IM.EOTC_DAILY
LOG = IM.LOG
log = IM.log


def ensure_data():
    sha = subprocess.run(["git", "rev-parse", "origin/main"], capture_output=True, text=True, check=True).stdout.strip()
    root = os.path.join(IM.WORK, f"ipf_main_{sha[:12]}")
    if not os.path.isfile(os.path.join(root, ".done")):
        os.makedirs(root, exist_ok=True)
        p = subprocess.run(["git", "archive", "--format=tar", sha] + PARTS, capture_output=True, check=True)
        subprocess.run(["tar", "-x", "-C", root], input=p.stdout, check=True)
        open(os.path.join(root, ".done"), "w").write(sha)
    return sha, os.path.join(root, "data")


def load_rows(DATA):
    d = os.path.join(DATA, "meta", "insider_predeclare")
    fs = sorted(f for f in os.listdir(d) if f.startswith("insider_predeclare_") and f.endswith(".csv"))
    X = pd.concat([pd.read_csv(os.path.join(d, f), dtype=str, keep_default_na=False) for f in fs], ignore_index=True)
    X["d"] = pd.to_datetime(X["declare_date"])
    return X


def norm_group(method_raw, ttype, torg):
    hit = set()
    for t in method_raw.split("|"):
        if any(k in t for k in GEN_KW):
            hit.add("一般交易")
        elif "贈與" in t:
            hit.add("贈與")
        elif "信託" in t:
            hit.add("信託")
        else:
            hit.add("其他")
    if len(hit) >= 2:
        return "混合", False
    g = hit.pop()
    if g == "信託" and (ttype == "employee_trust" or "限制員工" in torg):
        return "其他", True
    return g, False


def role_class(role):
    if "大股東" in role:
        return "大股東"
    if "董事" in role or "監察人" in role:
        return "董監"
    if "經理人" in role:
        return "經理人"
    return "其他身分"


def role_sub(role):
    for k in ("利用他人名義", "未成年子女", "配偶", "本人"):
        if k in role:
            return k
    return "未判"


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return np.nan


def plan_shares(r, g):
    """Q3：回 (股數, 是否改用 plan)。"""
    if g == "一般交易":
        if r["shares_split"]:
            v = sum(_num(x) for x in r["shares_split"].split("|"))
            if np.isfinite(v):
                return v, False
        v = _num(r["shares"])
        if np.isfinite(v):
            return v, False
    po, pt = _num(r["plan_own"]), _num(r["plan_trust"])
    v = (po if np.isfinite(po) else 0.0) + (pt if np.isfinite(pt) else 0.0)
    return (v if (np.isfinite(po) or np.isfinite(pt)) else np.nan), g == "一般交易"


def combined_cal(Zs):
    ce, cm = Zs["早年"]["cal"], Zs["主"]["cal"]
    pre = pd.bdate_range("2003-05-01", ce[0] - pd.Timedelta(days=1))
    return pd.DatetimeIndex(sorted(set(pre) | set(ce) | set(cm)))


class SharesOut:
    """Q9：T 當天或之前最後一筆已發行股數。"""
    def __init__(self, Zs, sids_early):
        self.main_data = Zs["主"]["data"]; self.m = {}
        da = pd.read_pickle(EOTC_DAILY)
        da = da[da["stock_id"].isin(sids_early)][["date", "stock_id", "shares"]].copy()
        da["shares"] = pd.to_numeric(da["shares"], errors="coerce"); da = da[da["shares"] > 0]
        da["date"] = pd.to_datetime(da["date"])
        self.e = {s: g.drop_duplicates("date", keep="last").set_index("date")["shares"].sort_index() for s, g in da.groupby("stock_id")}

    def get(self, wn, sid, T):
        if wn == "早年":
            s = self.e.get(sid)
        else:
            if sid not in self.m:
                f = os.path.join(self.main_data, "stocks", f"{sid}.csv")
                if os.path.exists(f):
                    x = pd.read_csv(f, usecols=["date", "shares"], dtype={"date": str})
                    x["date"] = pd.to_datetime(x["date"]); x["shares"] = pd.to_numeric(x["shares"], errors="coerce")
                    x = x[x["shares"] > 0].drop_duplicates("date", keep="last").set_index("date")["shares"].sort_index()
                    self.m[sid] = x
                else:
                    self.m[sid] = None
            s = self.m[sid]
        if s is None or len(s) == 0:
            return np.nan
        k = int(s.index.searchsorted(T, side="right")) - 1
        return float(s.iloc[k]) if k >= 0 else np.nan


def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    reg = IM.reg_check(REG_SHA)
    log(f"[登錄] {reg}（sha {REG_SHA} 已驗）")
    sha, DATA = ensure_data()
    log(f"[資料] origin/main {sha[:10]} ⇒ {DATA}")
    X = load_rows(DATA)
    tail_tab = X["d"].max()
    st = pd.read_csv(os.path.join(DATA, "meta", "stocks.csv"), dtype=str)
    ls = pd.to_datetime(st["last_seen"], errors="coerce"); alive = set(st.loc[ls >= ls.max() - pd.Timedelta(days=10), "stock_id"])
    Zs = {"早年": IM.panel_aux(IM.build_panel("早年", 2)), "主": IM.panel_aux(IM.build_panel("主", 2))}
    IX = {wn: {s: i for i, s in enumerate(Z["sids"])} for wn, Z in Zs.items()}
    CAL = combined_cal(Zs); NC = len(CAL)
    main_tail = Zs["主"]["cal"][-1]; main_tail_pos = int(CAL.searchsorted(main_tail))
    early_last_pos = int(CAL.searchsorted(Zs["早年"]["cal"][-1]))
    log(f"[事件表] {len(X)} 列 {X['d'].min().date()}～{tail_tab.date()}｜{dict(Counter(X['market']))}｜合併日曆 {NC} 日（主尾 {main_tail.date()}）")

    # ── 列層 ──
    ng = [norm_group(m, t, o) for m, t, o in zip(X["method_raw"], X["transferee_type"], X["transferee_org"])]
    X["組"] = [g for g, _ in ng]; X["信託轉其他"] = [f for _, f in ng]
    X["身分"] = X["role"].map(role_class); X["分項"] = X["role"].map(role_sub)
    X["受託旗標"] = X["role"].str.contains("由受託人持有"); X["子公司"] = X["role"].str.startswith("子公司")
    ps = [plan_shares(r, g) for r, g in zip(X.to_dict("records"), X["組"])]
    X["預定股數"] = [v for v, _ in ps]; X["改用plan"] = [f for _, f in ps]
    orig_cols = [c for c in X.columns if c not in ("d", "組", "信託轉其他", "身分", "分項", "受託旗標", "子公司", "預定股數", "改用plan")]
    X["完全重複"] = X.duplicated(subset=orig_cols, keep="first")
    X["p"] = CAL.searchsorted(X["d"], side="right") - 1
    X["組合字串"] = X["method_raw"].str.contains(r"\|", regex=True)
    J = {"性質": "董監大股東申報轉讓 seq2 頻率表乾跑（⛔ 未讀、未算任何進場後價格、報酬、持有期結果）", "登錄": f"台股策略線 seq2 sha {REG_SHA}",
         "裁定": "seq407 第三題、seq408 發號、seq412 §六（描述、N 不計；贈與、信託另組；可用日＝申報日）",
         "資料": {"origin/main": sha, "列數": int(len(X)), "期間": [str(X['d'].min().date()), str(tail_tab.date())], "市場": dict(Counter(X["market"]))},
         "列層": {"組(全市場)": dict(Counter(X["組"])), "信託轉其他(限制員工)": int(X["信託轉其他"].sum()),
                "transferee_type=employee_trust 列": int((X["transferee_type"] == "employee_trust").sum()),
                "employee_trust 列的方式": dict(Counter(X.loc[X["transferee_type"] == "employee_trust", "method_raw"])),
                "一般交易組 shares 空白改用 plan": int(X["改用plan"].sum()), "完全重複列": int(X["完全重複"].sum()),
                "預定股數不可得": int(X["預定股數"].isna().sum()), "unfinished=是": dict(Counter(X.loc[X["unfinished"] == "是", "組"])),
                "change_note 非空": int((X["change_note"] != "").sum()),
                "其他組方式": dict(Counter(X.loc[X["組"] == "其他", "method_raw"])), "組合字串": dict(Counter(X.loc[X["組合字串"], "method_raw"]))}}
    Y = X[X["market"].isin(["sii", "otc"])].copy()
    J["列層"]["上市櫃列數"] = int(len(Y)); J["列層"]["興櫃列數(不納)"] = int((X["market"] == "rotc").sum())
    J["列層"]["上市櫃 組"] = dict(Counter(Y["組"])); J["列層"]["上市櫃 身分"] = dict(Counter(Y["身分"]))
    J["列層"]["上市櫃 分項"] = dict(Counter(Y["分項"])); J["列層"]["上市櫃 受託旗標"] = int(Y["受託旗標"].sum())
    J["列層"]["上市櫃 子公司身分"] = int(Y["子公司"].sum())

    # ── Q4 合併 ──
    Y = Y.sort_values(["組", "stock_id", "d", "market"], kind="mergesort").reset_index()
    evs = []
    cur = None
    for k, r in enumerate(Y.itertuples(index=False)):
        key = (r.組, r.stock_id)
        if cur is None or cur["key"] != key or r.p - cur["p0"] > MERGE_TD:
            if cur is not None:
                evs.append(cur)
            cur = {"key": key, "p0": int(r.p), "d": r.d, "market": r.market, "rows": []}
        cur["rows"].append(k)
    if cur is not None:
        evs.append(cur)
    log(f"[合併] 上市櫃 {len(Y)} 列 ⇒ {len(evs)} 事件｜{dict(Counter(e['key'][0] for e in evs))}")

    # ── 申報公司日表（Q10 非申報；全部列）──
    allsid = sorted(set(X["stock_id"]) | set(Zs["早年"]["sids"]) | set(Zs["主"]["sids"]))
    SR = {s: k for k, s in enumerate(allsid)}
    DM = np.zeros((len(allsid), NC + 1), np.int32)
    for s, p in zip(X["stock_id"], X["p"]):
        if p >= 0:
            DM[SR[s], p + 1] += 1
    CS = np.cumsum(DM, axis=1)          # CS[r, q+1] − CS[r, a] ＝ 位置 [a, q] 申報列數

    sids_early = {Y.loc[e["rows"][0], "stock_id"] for e in evs if e["d"] <= pd.Timestamp("2015-01-31")}
    SO = SharesOut(Zs, sids_early)
    memo = {"早年": {}, "主": {}}; memo2 = {"早年": {}, "主": {}}

    def xs_arrays(wn, Z, T):
        if T not in memo2[wn]:
            out, qm, qr = SQ.xsec(Z, T, memo[wn])
            js = np.array(sorted(out), int)
            mc = np.array([out[j][0] for j in js]); rr = np.array([out[j][1] for j in js])
            qi = np.searchsorted(qr, rr, "right") if qr is not None else None
            rows = np.array([SR[Z["sids"][j]] for j in js], int)
            memo2[wn][T] = (out, qr, js, mc, qi, rows)
        return memo2[wn][T]

    recs = []
    for n_, ev in enumerate(evs):
        g, s = ev["key"]; d = ev["d"]
        R_ = Y.loc[ev["rows"]]
        nd = R_[~R_["完全重複"]]
        cls = set(R_["身分"])
        rec = {"sid": s, "date": str(d.date()), "組": g, "market": ev["market"], "已下市": s not in alive, "列數": len(R_),
               "申報日數": int(R_["d"].nunique()), "末筆": str(R_["d"].max().date()),
               "董監": "董監" in cls, "經理人": "經理人" in cls, "大股東": "大股東" in cls, "其他身分": "其他身分" in cls,
               "預定股數": float(nd["預定股數"].sum(min_count=1)) if nd["預定股數"].notna().any() else np.nan,
               "首日預定股數": float(nd.loc[nd["d"] == d, "預定股數"].sum(min_count=1)) if nd.loc[nd["d"] == d, "預定股數"].notna().any() else np.nan,
               "st": "", "世界": "", "T": "", "e": ""}
        recs.append(rec)
        if not PRE.okcode(s):
            rec["st"] = "非四碼普通股"; continue
        wn = None
        for w in ("早年", "主"):
            cal = Zs[w]["cal"]
            pe = int(cal.searchsorted(d, side="right"))
            if pe < len(cal) and (w == "主" or cal[pe] <= pd.Timestamp("2014-12-31")):
                wn = w; break
        if wn is None:
            rec["st"] = "超出資料尾"; continue
        Z = Zs[wn]; cal = Z["cal"]
        e = int(cal.searchsorted(d, side="right")); T = e - 1
        if T < 0:
            rec["st"] = "早於價格資料" if wn == "早年" else "跨世界接縫"; continue
        rec.update({"世界": wn, "T": str(cal[T].date()), "e": str(cal[e].date())})
        so = SO.get(wn, s, cal[T])
        rec["已發行股數"] = so
        rec["占比"] = rec["預定股數"] / so if (np.isfinite(so) and so > 0 and np.isfinite(rec["預定股數"])) else np.nan
        rec["首日占比"] = rec["首日預定股數"] / so if (np.isfinite(so) and so > 0 and np.isfinite(rec["首日預定股數"])) else np.nan
        if wn == "早年" and ev["market"] == "otc" and cal[T] < OTC_EARLY:
            rec["st"] = "上櫃早於2007-07無股價"; continue
        i = IX[wn].get(s)
        if i is None:
            rec["st"] = "不在面板(gate3／不足260根)"; continue
        if not (Z["G"][i, T] and np.isfinite(Z["C"][i, T])):
            rec["st"] = "閘外(500張/pit/T無K棒)"; continue
        rec["st"] = IM.entry_flag(Z, i, T, e)
        pe_c = int(CAL.searchsorted(cal[e])); pT_c = int(CAL.searchsorted(cal[T]))
        for h in HOLDS:
            rec[f"{h}日走完"] = bool(pe_c + h <= main_tail_pos)
            rec[f"{h}日跨世界"] = bool(wn == "早年" and pe_c + h > early_last_pos)
        if rec["st"] != "保留":
            continue
        # Q10 配對可行性
        out, qr, js, mc, qi, rows = xs_arrays(wn, Z, T)
        if int(i) not in out or qr is None:
            rec["配對"] = "配對不可算"; continue
        mc0, r0 = out[int(i)]; q0 = int(np.searchsorted(qr, r0, "right"))
        lo = max(pT_c - CTRL_TD, 0); hi = pT_c + CTRL_TD
        rec["±60窗截到表尾"] = bool(hi > NC - 1)
        hi = min(hi, NC - 1)
        decl = (CS[rows, hi + 1] - CS[rows, lo]) > 0
        ok = (~decl) & (qi == q0) & (js != int(i))
        rec["非申報檔數"] = int((~decl).sum()); rec["主池候選數"] = int(ok.sum())
        if ok.any():
            lr = np.abs(np.log(mc[ok] / mc0)); k = int(np.argmin(lr))
            rec["配對"] = "主配對"; rec["配對代號"] = Z["sids"][int(js[ok][k])]; rec["|log市值比|"] = float(lr[k])
        else:
            rec["配對"] = "配對失敗"
        if (n_ + 1) % 5000 == 0:
            log(f"  事件 … {n_ + 1}／{len(evs)}｜{time.time() - t0:.0f}s")
    E = pd.DataFrame(recs)
    E["e_dt"] = pd.to_datetime(E["e"], errors="coerce")
    E["申報月"] = E["date"].str[:7]
    J["合併後事件"] = dict(Counter(E["組"]))
    J["剔除總表"] = {g: dict(Counter(E.loc[E["組"] == g, "st"])) for g in GROUPS}

    # ── 段 × 組 ──
    FREQ = []; MATCH = []; J["段"] = {}
    kept = E[E["st"] == "保留"]

    def neff(sub):
        return min(len(sub), int(sub["申報月"].nunique()))

    for sg, (x, y) in SEGS.items():
        x_ = pd.Timestamp(x); y_ = main_tail if y is None else pd.Timestamp(y)
        segj = {"期間": f"{x}～{y_.date()}"}
        S0 = kept[(kept["e_dt"] >= x_) & (kept["e_dt"] <= y_)]
        for g in GROUPS:
            sub = S0[S0["組"] == g]; nev = len(sub)
            s60 = sub[sub["60日走完"].astype(bool)] if nev else sub
            gj = {"事件數(保留)": nev, "相異公司": int(sub["sid"].nunique()), "申報月數": int(sub["申報月"].nunique()), "n_eff": neff(sub),
                  "已下市比例": round(float(sub["已下市"].mean()), 4) if nev else None,
                  "上櫃比例": round(float((sub["market"] == "otc").mean()), 4) if nev else None}
            for h in HOLDS:
                s2 = sub[sub[f"{h}日走完"].astype(bool)] if nev else sub
                gj[f"{h}日走完_事件"] = len(s2); gj[f"{h}日走完_n_eff"] = neff(s2)
                gj[f"{h}日跨世界"] = int(sub[f"{h}日跨世界"].astype(bool).sum()) if nev else 0
            gj["判定n_eff(60日走完)"] = neff(s60); gj["n_eff<30"] = bool(gj["判定n_eff(60日走完)"] < NEFF_MIN)
            for c in ("董監", "經理人", "大股東", "其他身分"):
                s2 = s60[s60[c].astype(bool)] if len(s60) else s60
                gj[f"身分_{c}_事件(60走完)"] = len(s2); gj[f"身分_{c}_n_eff"] = neff(s2)
            pr = s60["占比"].to_numpy(float) if len(s60) else np.array([])
            big = s60[s60["占比"] >= 0.01] if len(s60) else s60; small = s60[s60["占比"] < 0.01] if len(s60) else s60
            gj["占比≥1%_事件(60走完)"] = len(big); gj["占比≥1%_n_eff"] = neff(big)
            gj["占比<1%_事件(60走完)"] = len(small); gj["占比<1%_n_eff"] = neff(small)
            gj["占比不可算"] = int((~np.isfinite(pr)).sum())
            gj["首日占比≥1%_事件(60走完)"] = int((s60["首日占比"] >= 0.01).sum()) if len(s60) else 0
            gj["占比分布"] = IM.qd(pr)
            mc_ = Counter(sub["配對"].fillna("配對不可算")) if nev else Counter()
            gj["配對"] = dict(mc_)
            gj["主配對成功率"] = round(mc_.get("主配對", 0) / nev, 4) if nev else None
            pc = sub["主池候選數"].dropna().to_numpy(float) if (nev and "主池候選數" in sub) else np.array([])
            gj["主池候選數分布"] = IM.qd(pc)
            gj["主池候選數_0／1～4／5～19／≥20"] = [int((pc == 0).sum()), int(((pc >= 1) & (pc <= 4)).sum()), int(((pc >= 5) & (pc <= 19)).sum()), int((pc >= 20).sum())]
            gj["|log市值比|分布"] = IM.qd(sub["|log市值比|"].dropna().to_numpy(float)) if (nev and "|log市值比|" in sub) else None
            gj["非申報檔數分布"] = IM.qd(sub["非申報檔數"].dropna().to_numpy(float)) if (nev and "非申報檔數" in sub) else None
            gj["±60窗截到表尾"] = int(sub["±60窗截到表尾"].fillna(False).astype(bool).sum()) if (nev and "±60窗截到表尾" in sub) else 0
            gj["每年"] = {int(k): int(v) for k, v in sub["e_dt"].dt.year.value_counts().sort_index().items()}
            segj[g] = gj
            FREQ.append({"段": sg, "組": g, "期間": segj["期間"], **{k: v for k, v in gj.items() if not isinstance(v, (dict, list))},
                         "占比中位": gj["占比分布"]["中位"] if gj["占比分布"] else None,
                         "候選數中位": gj["主池候選數分布"]["中位"] if gj["主池候選數分布"] else None})
            MATCH.append({"段": sg, "組": g, **gj["配對"], "主配對成功率": gj["主配對成功率"],
                          "候選0": gj["主池候選數_0／1～4／5～19／≥20"][0], "候選1～4": gj["主池候選數_0／1～4／5～19／≥20"][1],
                          "候選5～19": gj["主池候選數_0／1～4／5～19／≥20"][2], "候選≥20": gj["主池候選數_0／1～4／5～19／≥20"][3],
                          "|log市值比|中位": gj["|log市值比|分布"]["中位"] if gj["|log市值比|分布"] else None,
                          "±60窗截到表尾": gj["±60窗截到表尾"]})
        J["段"][sg] = segj
        log(f"[段 {sg}] " + "｜".join(f"{g} n={segj[g]['事件數(保留)']} n_eff60={segj[g]['判定n_eff(60日走完)']}" for g in GROUPS))
    seg_gap = kept[(kept["e_dt"] > pd.Timestamp("2016-12-31")) & (kept["e_dt"] < pd.Timestamp("2017-03-01"))]
    J["不入段(2017-01～02)"] = dict(Counter(seg_gap["組"]))

    # ── 每年（申報年）──
    BY = []
    X["年"] = X["d"].dt.year; E["年"] = E["date"].str[:4].astype(int)
    for yy in sorted(X["年"].unique()):
        xx = X[X["年"] == yy]; yy_ = xx[xx["market"].isin(["sii", "otc"])]; ee = E[E["年"] == yy]
        row = {"申報年": int(yy), "列數(全)": len(xx), "列數 sii": int((xx["market"] == "sii").sum()), "列數 otc": int((xx["market"] == "otc").sum()),
               "列數 rotc(不納)": int((xx["market"] == "rotc").sum()), "組合字串列(上市櫃)": int(yy_["組合字串"].sum()),
               "組合字串比例(上市櫃)": round(float(yy_["組合字串"].mean()), 4) if len(yy_) else None}
        for g in GROUPS:
            row[f"{g}_列"] = int((yy_["組"] == g).sum())
            row[f"{g}_事件"] = int((ee["組"] == g).sum())
            row[f"{g}_保留"] = int(((ee["組"] == g) & (ee["st"] == "保留")).sum())
        BY.append(row)
    STAT = [{"組": g, "剔除原因": k, "事件數": v} for g in GROUPS for k, v in J["剔除總表"][g].items()]

    # ── 覆蓋 ──
    J["覆蓋"] = {g: {"事件(全)": int((E["組"] == g).sum()), "已下市比例(全)": round(float(E.loc[E["組"] == g, "已下市"].mean()), 4) if (E["組"] == g).any() else None,
                    "上櫃比例(全)": round(float((E.loc[E["組"] == g, "market"] == "otc").mean()), 4) if (E["組"] == g).any() else None,
                    "保留": int(((E["組"] == g) & (E["st"] == "保留")).sum()),
                    "已下市比例(保留)": round(float(kept.loc[kept["組"] == g, "已下市"].mean()), 4) if (kept["組"] == g).any() else None}
                for g in GROUPS}

    # ── Q12 seq377 ──
    EQ = []

    def near(A, B, days):
        Bd = defaultdict(list)
        for s, d in zip(B["sid"], pd.to_datetime(B["date"])):
            Bd[s].append(d)
        return sum(any(abs((d - x).days) <= days for x in Bd.get(s, ())) for s, d in zip(A["sid"], pd.to_datetime(A["date"])))
    G0 = kept[kept["組"] == "一般交易"]
    for g in ("贈與", "信託", "其他"):
        B = kept[kept["組"] == g]
        for days in (0, 30):
            h = near(G0, B, days); h2 = near(B, G0, days)
            EQ.append({"比較": f"一般交易 vs {g}", "相隔≤曆日": days, "A筆數": len(G0), "B筆數": len(B), "A中B也有": h,
                       "比例_A": round(h / len(G0), 4) if len(G0) else None, "B中A也有": h2, "比例_B": round(h2 / len(B), 4) if len(B) else None})
    EQ.append({"比較": "混合組（一列跨兩組以上）", "上市櫃列數": int((Y["組"] == "混合").sum()), "事件": int((E["組"] == "混合").sum())})
    EQ.append({"比較": "信託→其他（受讓人限制員工）", "全市場列數": int(X["信託轉其他"].sum()),
               "註": "transferee_type 先判信託/銀行 ⇒ 銀行受託的限制員工信託判不出"})
    # 既有件對照：insider_monthly IRB140
    irb = pd.read_csv(os.path.join(DATA, "meta", "insider_monthly", "insider_transfer.csv"), dtype=str, keep_default_na=False)
    irb = irb[irb["stock_id"] != ""]
    iy = defaultdict(set)
    for s, ym in zip(irb["stock_id"], irb["data_ym"]):
        iy[s].add(ym)
    irb_tail = irb["data_ym"].max()
    gg = G0[(G0["date"] >= "2006-01-01") & ((pd.to_datetime(G0["date"]) + pd.DateOffset(months=1)).dt.strftime("%Y-%m") <= irb_tail)]

    def nxt(ym):
        return (pd.Period(ym, "M") + 1).strftime("%Y-%m")
    hit = [bool({m, nxt(m)} & iy.get(s, set())) for s, m in zip(gg["sid"], gg["申報月"])]
    gg = gg.assign(irb=hit)
    big = gg[gg["預定股數"] >= 1_000_000]
    EQ.append({"比較": "一般交易保留事件 vs IRB140（同代號 data_ym∈{申報月,次月}）", "A筆數(2006-01～IRB尾前一月)": len(gg), "A中IRB也有": int(gg["irb"].sum()),
               "比例_A": round(float(gg["irb"].mean()), 4) if len(gg) else None,
               "預定≥100萬股者": len(big), "其中IRB也有": int(big["irb"].sum()), "比例_≥100萬": round(float(big["irb"].mean()), 4) if len(big) else None,
               "IRB140 期間": f"{irb['data_ym'].min()}～{irb_tail}"})
    J["seq377等價"] = EQ
    J["假訊號臂"] = "登錄未列 ⇒ 不做"
    J["讀法"] = __doc__.split("═══ 讀法")[1]
    J["時間"] = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")
    pd.DataFrame(FREQ).to_csv(os.path.join(OUT, "freq.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(BY).to_csv(os.path.join(OUT, "by_year.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(STAT).to_csv(os.path.join(OUT, "status.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(MATCH).to_csv(os.path.join(OUT, "match.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(EQ).to_csv(os.path.join(OUT, "equiv.csv"), index=False, encoding="utf-8-sig")
    with gzip.open(os.path.join(OUT, "events.csv.gz"), "wt", encoding="utf-8") as fh:
        E.drop(columns=["e_dt"]).to_csv(fh, index=False)
    json.dump(J, open(os.path.join(OUT, "freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] {time.time() - t0:.0f}s")
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
