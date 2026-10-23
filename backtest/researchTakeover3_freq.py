# -*- coding: utf-8 -*-
"""被公開收購／經營權變動／私募策略投資人 seq3【E3 私募分組・頻率表】（台股策略線 登錄 sha de337a91f8ae89c3，2026-10-23 00:13；
裁定 seq457 §二 加 §七、seq458 §四 核；描述、不計 N）——回測線計算子代理。
⛔ 只數件數、配到率、普通股、各組件數、n_eff、減資交叉、配對成功率；⛔ 不讀、不算、不存任何報酬（seq366）。
⛔ 不 commit、不改既有檔；researchTakeover_freq（TF：事件、配對、窗狀態函式原樣）、researchRevTurn_freq（RT）、researchIndMom_freq（IMF.reg_check）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTakeover3_freq
輸出 backtest/resultsTakeover3/freq/：freq.json、freq.csv（組×段）、cross.csv（組×減資×市值）、by_year.csv、equiv.csv、events.csv.gz（逐事件旗標，⛔ 無報酬）、run.log

═══ 讀法（W 標；⛔ 在看任何 seq3 分組數字之前寫死於 2026-10-23（台北）；★＝執行者定，〔 〕內為另一讀法）═══
 W0 事件表 ＝ origin/main 99159a0de9 的 takeover_events.csv（E3 v4，3,012 列；登錄寫 3,013 ＝ 資料庫多剔 2891 2010-08-26，在 2011 前、不影響本件）；
    私募對照 ＝ 同 sha 的 data/meta/placement_detail/e3_placement_match.csv（以 date＋stock_id 對 E3 列，一對一）、placement_detail.csv（只做驗證）。
    價格、exright、stocks.csv、配對池以外的一切 ＝ seq2 頻率表同一 sha 443ee8ce96（＝ researchTakeover_e3v4 的 V2）；
    事件、配對、窗狀態以 TF.process 原樣重建，須與 resultsTakeover/e3v4_freq/events.csv.gz 對應列逐字相同（不同 ⇒ 中止）。
 W1 母體（登錄 §七、§六）：E3 ∧ first12m 1 ∧ 公告日 ≥ 2011-01-01。
    配到 ＝ match_decide_date 非空（決議日在 E3 當天或之前 365 天內最近一案）；否則「未配到」⛔ 不入分組（照報）。
    普通股案 ＝ 配到 ∧ 私募專區證券種類（sec_kind，以「+」分隔的同日各案）含「普通股」（登錄「證券種類以內文為準」；
    同日普通股＋可轉債／特別股 ⇒ 以普通股案為準；三欄取該普通股案，W3 驗證）。不含普通股（只特別股、只公司債）⇒「非普通股」不入分組。
    ★ 三欄任一空白（舊表或兩格都沒勾）⇒「三欄空白」不入分組（照報）。分組母體 ＝ 配到 ∧ 普通股案 ∧ 三欄皆有值。
 W2 組：重疊組 甲 is_strategic、乙 is_insider、丙 control_change 各 是／否；互斥 只策略（甲1乙0）、只內部人（甲0乙1）、兩者皆是、兩者皆否。
    交叉（登錄 §七「其餘同 §六」、§三）：有／無減資（with_reduction 1／0）× 市值 ≤10 億／＞10 億（判日 T 面板市值，同 seq2 U1）。
 W3 驗證：分組母體每列的三欄 ＝ placement_detail.csv 中同代號、同決議日、sec_kind＝普通股那一案（須恰一案）。
 W4 段 ★（依公告日；seq2 U6 去掉 2011 前）：早年(2011～2016) 2011-01-01～2016-12-31｜探索 2017-03-01～2021-12-31｜確認 2022-01-01～｜全期(2011～)。
    n_eff ＝ min(事件數, 公告月數)（＝ 公告月數）；★ ＜ 24 標「還沒測」（派工）；＜ 30 另標「事件少」（seq2 U6）。⭐ 各窗另報「雙方走得完」的 n_eff。
 W5 seq377 等價／退化：三欄兩兩交叉、組與組成員是否全同、gap_days 分布、普通股＋可轉債同日案數、配對公司重複、2011 前配到率（說明為何不用）。
"""
from __future__ import annotations

import gzip
import io
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
from backtest import researchIndMom_freq as IMF             # noqa: E402  reg_check（⛔ 只 import）
from backtest import researchTakeover_freq as TF            # noqa: E402  事件、配對、窗（⛔ 只 import）
from backtest import researchRevTurn_freq as RT             # noqa: E402  ensure_data（⛔ 只 import）

REG_SHA = "de337a91f8ae89c3"
EV_SHA = "99159a0de9"
OUT = "backtest/resultsTakeover3/freq"
V4_FREQ = "backtest/resultsTakeover/e3v4_freq"
WORK3 = os.path.expanduser("~/tko3work")
PRICE_SHA = json.load(open(os.path.join(TF.OUT, "freq.json"), encoding="utf-8"))["origin/main"]
MATCH = "data/meta/placement_detail/e3_placement_match.csv"
PDET = "data/meta/placement_detail/placement_detail.csv"
START = "2011-01-01"
SEGS3 = [("早年(2011～2016)", "2011-01-01", "2016-12-31"), ("探索", "2017-03-01", "2021-12-31"), ("確認", "2022-01-01", "2099-12-31"),
         ("全期(2011～)", "2011-01-01", "2099-12-31")]
NEFF_TEST = 24
NEFF_FEW = 30
MCG = ("≤10億", "＞10億")
FLAGS = {"甲": "is_strategic", "乙": "is_insider", "丙": "control_change"}
EXCL = ["只策略", "只內部人", "兩者皆是", "兩者皆否"]
BASE = ["E3_2011起", "配到", "配到普通股", "分組母體"]
OVL = [f"{k}{v}" for k in FLAGS for v in ("是", "否")]
GROUPS3 = BASE + OVL + EXCL
NOTES = ["描述，不是選股規則", "事件少", "「策略性投資人」是董事會預定的應募人類別，⛔ 不等於實際認購人", "台灣文獻只讀到摘要",
         "頻率表、未算任何報酬（seq366）", "E3 只用 2011 起（2010 前私募專區只有舊表、配到約 30%，依構造不可分組）",
         "價格面板資料尾 2026-09-24（rerun17 H2D）；價格等 ＝ seq2 頻率表 sha 443ee8ce96；事件表、私募對照 ＝ 99159a0de9"]
LOG: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def gshow(sha, p):
    return pd.read_csv(io.BytesIO(subprocess.run(["git", "show", f"{sha}:{p}"], capture_output=True, check=True).stdout), dtype=str, keep_default_na=False)


def full_sha(s):
    return subprocess.run(["git", "rev-parse", s], capture_output=True, text=True, check=True).stdout.strip()


def setup():
    ev_full = full_sha(EV_SHA)
    _load = TF.load_table
    TF.load_table = lambda sha: _load(ev_full)                  # W0 事件表固定 99159a0de9
    if not getattr(RT, "_tko3", False):
        _ens = RT.ensure_data
        RT.ensure_data = lambda sha=None: _ens(PRICE_SHA)       # W0 價格等固定 seq2 sha
        RT._tko3 = True
    os.makedirs(WORK3, exist_ok=True)
    return ev_full


def tags(E):
    """W1、W2：E（含 match 欄）⇒ 分組旗標欄。"""
    E = E.copy()
    E["配到"] = E["match_decide_date"] != ""
    E["普通股案"] = E["配到"] & E["sec_kind"].map(lambda s: "普通股" in s.split("+"))
    E["三欄有值"] = E[list(FLAGS.values())].isin(["0", "1"]).all(axis=1)
    E["分組母體"] = E["普通股案"] & E["三欄有值"]
    E["分組狀態"] = np.where(~E["配到"], "未配到", np.where(~E["普通股案"], "非普通股", np.where(~E["三欄有值"], "三欄空白", "分組母體")))
    s, i = E["is_strategic"], E["is_insider"]
    ex = np.select([(s == "1") & (i == "0"), (s == "0") & (i == "1"), (s == "1") & (i == "1"), (s == "0") & (i == "0")], EXCL, "")
    E["互斥組"] = np.where(E["分組母體"], ex, "")
    return E


def gsel3(E, name):
    """組名 ⇒ 子集。組名 ＝ 基本組［_有減資｜_無減資］［_市值≤10億｜_市值＞10億］。"""
    parts = name.split("_")
    g = parts[0] if not name.startswith("E3_2011起") else "E3_2011起"
    rest = name[len(g):].strip("_").split("_") if name != g else []
    if g == "E3_2011起":
        s = E
    elif g == "配到":
        s = E[E["配到"]]
    elif g == "配到普通股":
        s = E[E["普通股案"]]
    elif g == "分組母體":
        s = E[E["分組母體"]]
    elif g in EXCL:
        s = E[E["互斥組"] == g]
    elif g in OVL:
        col = FLAGS[g[0]]; v = "1" if g[1] == "是" else "0"
        s = E[E["分組母體"] & (E[col] == v)]
    else:
        raise KeyError(name)
    for r in rest:
        if r == "有減資":
            s = s[s["with_reduction"] == "1"]
        elif r == "無減資":
            s = s[s["with_reduction"] == "0"]
        elif r.startswith("市值"):
            s = s[(s["st"] == "保留") & (s["市值組"] == r[2:])]
        elif r:
            raise KeyError(name)
    return s


def variants(g):
    out = [g]
    for rd in ("有減資", "無減資"):
        out.append(f"{g}_{rd}")
    for mg in MCG:
        out.append(f"{g}_市值{mg}")
    for rd in ("有減資", "無減資"):
        for mg in MCG:
            out.append(f"{g}_{rd}_市值{mg}")
    return out


def build(PX, sha_price, DN, ev_full):
    """E3 ∧ first12m 1 ∧ ≥ 2011 ⇒ TF.process 原樣（事件、配對、窗狀態）＋ 私募對照欄。回 (E 原型別, E 字串版)。"""
    ev = TF.load_table(sha_price)
    tail_ev = pd.Timestamp(ev["date"].max())
    st = pd.read_csv(os.path.join(DN, "meta", "stocks.csv"), dtype=str)
    ls = pd.to_datetime(st["last_seen"], errors="coerce"); alive = set(st.loc[ls >= ls.max() - pd.Timedelta(days=10), "stock_id"])
    m = defaultdict(list)
    e3all = ev[ev["class"] == "E3"]
    for s, d in zip(e3all["stock_id"], e3all["date"]):
        m[s].append(np.datetime64(pd.Timestamp(d)))
    cls_dates = {"E3": {s: np.array(sorted(v)) for s, v in m.items()}}
    base_cols = ["first12m", "outcome", "acq_date", "with_reduction", "reduction_type", "overlap_e1", "market", "time"]
    sel = ev[(ev["class"] == "E3") & (ev["first12m"] == "1") & (ev["date"] >= START)]
    units = [{"類": "E3", "臂": "全體", "sid": r["stock_id"], "date": r["date"], "p0": TF.day0_of(PX["CAL"], r["date"], r["time"]),
              **{c: r[c] for c in base_cols}} for _, r in sel.iterrows()]
    rows = TF.process(units, PX, alive, cls_dates, tail_ev, {})
    E = pd.DataFrame(rows)
    buf = io.StringIO(); E.to_csv(buf, index=False); buf.seek(0)
    Es = pd.read_csv(buf, dtype=str, keep_default_na=False)
    M = gshow(ev_full, MATCH)
    if M.duplicated(["date", "stock_id"]).any():
        raise SystemExit("⛔ 私募對照 date＋stock_id 重複")
    mc = ["match_decide_date", "gap_days", "n_cases", "report_type", "sec_kind", "bond_flag", "is_insider", "is_strategic", "control_change", "e3_first12m"]
    M = M.rename(columns={"stock_id": "sid"})[["sid", "date"] + mc]
    out = []
    for X in (E, Es):
        Y = X.merge(M, on=["sid", "date"], how="left", validate="one_to_one", indicator=True)
        if (Y["_merge"] != "both").any():
            raise SystemExit(f"⛔ 私募對照缺列 {int((Y['_merge'] != 'both').sum())}")
        Y = Y.drop(columns="_merge")
        if (Y["e3_first12m"] != Y["first12m"]).any():
            raise SystemExit("⛔ 私募對照 e3_first12m ≠ 事件表 first12m")
        out.append(tags(Y))
    return out[0], out[1], ev


def neff_flags(n):
    return {"還沒測(n_eff<24)": bool(n < NEFF_TEST), "事件少(n_eff<30)": bool(n < NEFF_FEW)}


def summ3(sub):
    g = TF.summarize(sub)
    g.update(neff_flags(g["n_eff"]))
    g["配到"] = int(sub["配到"].sum()); g["配到普通股"] = int(sub["普通股案"].sum()); g["分組母體"] = int(sub["分組母體"].sum())
    g["有減資"] = int((sub["with_reduction"] == "1").sum()); g["無減資"] = int((sub["with_reduction"] == "0").sum())
    for w in TF.WINS:
        g[f"{w}_雙方還沒測"] = bool(g[f"{w}_雙方n_eff"] < NEFF_TEST)
    return g


def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    reg = IMF.reg_check(REG_SHA)
    log(f"[登錄] {reg}（sha {REG_SHA} 已驗）")
    ev_full = setup()
    sha, DN, MD = RT.ensure_data(None)
    log(f"[資料] 價格等 sha {sha}｜事件表、私募對照 sha {ev_full}")
    PX = TF.price_panel(sha, DN, 2)
    E, Es, ev = build(PX, sha, DN, ev_full)
    e3 = ev[ev["class"] == "E3"]
    log(f"[事件表] E3 {len(e3)} 列（應 3,012）｜first12m {int((e3['first12m'] == '1').sum())}｜2011 起 first12m {len(E)}")
    if len(e3) != 3012:
        raise SystemExit("⛔ E3 列數 ≠ 3,012")
    # W0 對 e3v4 頻率表
    V = pd.read_csv(os.path.join(V4_FREQ, "events.csv.gz"), dtype=str, keep_default_na=False)
    V = V[(V["類"] == "E3") & (V["date"] >= START)].reset_index(drop=True)
    cols = [c for c in V.columns if c in Es.columns]
    e1only = [c for c in V.columns if c not in Es.columns]               # E1 專用欄（E3 列應全空）
    Ec = Es[cols].reset_index(drop=True)
    ndiff = int((Ec != V[cols]).any(axis=1).sum()) if len(Ec) == len(V) else -1
    if any((V[c] != "").any() for c in e1only):
        ndiff = -2
    rec = {"列數": [len(Ec), len(V)], "比對欄數": len(cols), "E1專用欄(E3列全空)": e1only, "不同列": ndiff}
    log(f"[W0 對 e3v4 頻率表] {rec}")
    if ndiff != 0:
        raise SystemExit("⛔ 與 e3v4 頻率表不同 ⇒ 中止")
    # W3 驗證
    P = gshow(ev_full, PDET)
    pc = P[P["sec_kind"] == "普通股"].groupby(["stock_id", "decide_date"])
    cnt = pc.size()
    first = pc.first()
    bad = []; nmulti = 0
    for _, r in E[E["分組母體"]].iterrows():
        k = (r["sid"], r["match_decide_date"])
        if k not in cnt.index:
            bad.append((k, "查無普通股案")); continue
        if cnt[k] != 1:
            nmulti += 1
        for c in FLAGS.values():
            if first.loc[k, c] != r[c]:
                bad.append((k, c))
    log(f"[W3 三欄驗證] 分組母體 {int(E['分組母體'].sum())}｜不符 {len(bad)} {bad[:5]}｜同日多普通股案 {nmulti}")
    if bad:
        raise SystemExit("⛔ 三欄與私募專區普通股案不符")
    # 頻率表
    J = {"性質": "公開收購／經營權／私募策略投資人 seq3 E3 分組頻率表（⛔ 未讀、未算任何報酬；描述、不計 N）", "登錄": f"台股策略線 seq3 sha {REG_SHA}",
         "裁定": "seq457 §二、seq458 §四", "價格sha": sha, "事件表sha": ev_full, "W0對e3v4": rec,
         "W3": {"分組母體": int(E["分組母體"].sum()), "不符": len(bad), "同日多普通股案": nmulti}, "注意": NOTES, "段": {}}
    st = Counter(E["分組狀態"])
    J["件數"] = {"E3_2011起(first12m)": len(E), "配到": int(E["配到"].sum()), "配到率": round(float(E["配到"].mean()), 4),
                "未配到": st.get("未配到", 0), "非普通股": st.get("非普通股", 0), "三欄空白": st.get("三欄空白", 0), "分組母體": st.get("分組母體", 0),
                "配到普通股": int(E["普通股案"].sum()),
                "非普通股證券種類": dict(Counter(E.loc[E["分組狀態"] == "非普通股", "sec_kind"])),
                "三欄空白明細": list(zip(E.loc[E["分組狀態"] == "三欄空白", "sid"], E.loc[E["分組狀態"] == "三欄空白", "date"],
                                     E.loc[E["分組狀態"] == "三欄空白", "report_type"])),
                "未配到明細": list(zip(E.loc[~E["配到"], "sid"], E.loc[~E["配到"], "date"])),
                **{g: int(len(gsel3(E, g))) for g in OVL + EXCL}}
    log(f"[件數] {J['件數']}")
    FREQ = []
    for sg, x, y in SEGS3:
        J["段"][sg] = {}
        sub0 = E[(E["date"] >= x) & (E["date"] <= y)]
        for g in GROUPS3:
            for v in variants(g):
                s = gsel3(sub0, v)
                r = summ3(s)
                FREQ.append({"段": sg, "組": v, **r})
                if v == g:
                    J["段"][sg][g] = {k: r[k] for k in ("表列數", "可接價格", "n_eff", "還沒測(n_eff<24)", "配對成功率", "有減資", "無減資",
                                                       "後[+2,+250]_雙方走得完", "後[+2,+250]_雙方n_eff", "後[+2,+20]_雙方n_eff")}
        log(f"[段 {sg}] " + "｜".join(f"{g} 列 {J['段'][sg][g]['表列數']} n_eff {J['段'][sg][g]['n_eff']}" for g in GROUPS3))
    F = pd.DataFrame(FREQ)
    # 交叉（組×減資×市值，全期，可接價格）
    CR = []
    for g in GROUPS3:
        s = gsel3(E, g); ok = s[s["st"] == "保留"]
        rw = {"組": g, "表列數": len(s), "可接價格": len(ok)}
        for rd, rv in (("有減資", "1"), ("無減資", "0")):
            rw[f"{rd}(表列)"] = int((s["with_reduction"] == rv).sum())
            for mg in MCG:
                rw[f"{rd}_市值{mg}(可接)"] = int(((ok["with_reduction"] == rv) & (ok["市值組"] == mg)).sum())
        rw["市值空白(可接)"] = int((ok["市值組"] == "").sum())
        CR.append(rw)
    # 每年
    BY = []
    E["年"] = E["date"].str[:4].astype(int)
    for g in GROUPS3:
        for yy, s in gsel3(E, g).groupby("年"):
            ok = s[s["st"] == "保留"]
            BY.append({"組": g, "公告年": yy, "表列數": len(s), "可接價格": len(ok), "配對成功": int((ok["配對"] == "配對成功").sum()),
                       "有減資": int((s["with_reduction"] == "1").sum()),
                       "後[+2,+250]_雙方走得完": int(((ok["窗後[+2,+250]"] == "走得完") & (ok["配窗後[+2,+250]"] == "走得完")).sum())})
    # W5 等價／退化
    EQ = []
    G = E[E["分組母體"]]
    for a_, b_ in (("甲", "乙"), ("甲", "丙"), ("乙", "丙")):
        ct = pd.crosstab(G[FLAGS[a_]], G[FLAGS[b_]])
        EQ.append({"項": f"{a_}×{b_} 交叉（列 {a_}、欄 {b_}）", "值": json.dumps({f"{i}{j}": int(ct.loc[i, j]) if i in ct.index and j in ct.columns else 0
                                                                      for i in "01" for j in "01"}), "分母": len(G)})
    sets = {g: frozenset(zip(gsel3(E, g)["sid"], gsel3(E, g)["date"])) for g in OVL + EXCL}
    same = [(a_, b_) for a_ in sets for b_ in sets if a_ < b_ and sets[a_] == sets[b_]]
    EQ.append({"項": "成員全同的組對（退化）", "值": len(same), "註": str(same)})
    EQ.append({"項": "空組", "值": sum(1 for g in sets if not sets[g]), "註": str([g for g in sets if not sets[g]])})
    gd = pd.to_numeric(G["gap_days"], errors="coerce")
    EQ.append({"項": "gap_days（E3 日 − 決議日）", "值": json.dumps({"0～3": int((gd <= 3).sum()), "4～30": int(((gd > 3) & (gd <= 30)).sum()),
                                                            "31～365": int((gd > 30).sum())}), "分母": len(G)})
    EQ.append({"項": "分組母體中同日另有公司債案（普通股＋可轉債，以普通股案為準）", "值": int((G["bond_flag"] == "1").sum()), "分母": len(G)})
    EQ.append({"項": "分組母體中同日另有特別股案", "值": int(G["sec_kind"].str.contains("特別股").sum()), "分母": len(G)})
    inst = {(a_, b_): c_ for a_, b_, c_ in zip(e3["stock_id"], e3["date"], e3["instrument"])}
    gi = pd.Series([inst.get(k, "") for k in zip(G["sid"], G["date"])])
    EQ.append({"項": "分組母體 主旨證券種類（instrument）≠ common（以內文為準，主旨只對照）", "值": int((gi != "common").sum()), "分母": len(G),
               "註": str(dict(Counter(gi)))})
    for g in OVL + EXCL:
        s = gsel3(E, g); mm = s[s["配對"] == "配對成功"]
        EQ.append({"項": f"{g} 配對公司重複使用", "值": int(len(mm) - mm["配對sid"].nunique()), "分母": len(mm)})
    Mall = gshow(ev_full, MATCH)
    pre = Mall[(Mall["date"] < START) & (Mall["e3_first12m"] == "1")]
    EQ.append({"項": "2011 前 E3 first12m 配到率（說明為何不用）", "值": int((pre["match_decide_date"] != "").sum()), "分母": len(pre)})
    EQ.append({"項": "E3 v4 剔除列落在 2011 起 first12m", "值": 7, "註": "2891 2011-10-27、2002 2011-12-23、2882 2018-04-25、8415 2022-04-11、3085 2022-08-08、6443 2025-11-07、5531 2026-05-07（已查：同代號 365 天內沒有被它擋成 first12m 0 的後續 E3 ⇒ 剔除後不必重算 first12m）"})
    J["seq377等價"] = EQ
    J["讀法"] = __doc__.split("═══ 讀法")[1]
    J["時間"] = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")
    F.to_csv(os.path.join(OUT, "freq.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(CR).to_csv(os.path.join(OUT, "cross.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(BY).to_csv(os.path.join(OUT, "by_year.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(EQ).to_csv(os.path.join(OUT, "equiv.csv"), index=False, encoding="utf-8-sig")
    with gzip.open(os.path.join(OUT, "events.csv.gz"), "wt", encoding="utf-8") as fh:
        Es.to_csv(fh, index=False)
    json.dump(J, open(os.path.join(OUT, "freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    for r in EQ:
        log(f"[W5] {r}")
    log(f"[完] {time.time() - t0:.0f}s ⇒ {OUT}")
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
