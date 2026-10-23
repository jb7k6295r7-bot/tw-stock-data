# -*- coding: utf-8 -*-
"""被公開收購／經營權變動／私募策略投資人 seq3【E3 私募分組・報酬描述，不計 N】（台股策略線 登錄 sha de337a91f8ae89c3；
裁定 seq457 §二、seq458 §四：頻率表到正式跑之間所有描述欄先乾跑）——回測線計算子代理。
⛔ 描述，不是選股規則；⛔ 不判、不計 N、不推 LINE。「策略性投資人」是董事會預定的應募人類別，⛔ 不等於實際認購人。
⛔ 不 commit、不改既有檔；researchTakeover3_freq（F3：母體、分組、重建）、researchTakeover（TM：ret_std、ret_red、Red、red_table、ensure_extra、stat）、
   researchTakeover_freq（TF）、researchRevTurn_freq（RT）、researchIndMom_freq（IMF）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTakeover3 [--dry（R 全寫 0，輸出 ~/tko3work/dry3_main）]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchTakeover3_check [--dry]
輸出 backtest/resultsTakeover3/main/：main.json、表.csv（段×組×窗）、追蹤.csv、events.csv.gz（逐筆 R、X）、recon.csv、recon_v4.csv、summary.md、run.log

═══ 讀法（Y 標；頻率表 W0～W5、seq2 U10～U12、U15 原樣沿用；⛔ 在讀任何 seq3 報酬之前寫死於 2026-10-23（台北）；★＝執行者定）═══
 Y0 事件、配對、分組 ＝ 頻率表 resultsTakeover3/freq/events.csv.gz：以 F3.build 同一批函式、同一 sha 逐列重建，全部欄逐字相同才往下算（recon.csv）。
 Y1 報酬 ＝ seq2 U10（收盤到收盤、還原收盤；窗 [−30,−1]、[0,+1]、[+2,+20]、[+2,+60]、[+2,+250]；下市長停截斷照「下市前最後收盤出場」收）；
    E3 有減資（with_reduction 1）的 [+2,+250] ＝ seq2 U11 主口徑「參考價接續」、敏感度「減資前最後收盤截斷」（配對公司同日出場）。
    X ＝ R事件 − R配對。同根兩出場價取較低（seq373）：每窗只有一個出場價 ⇒ 不適用。open_base 一律 exright 版（seq412；價格面板已是）。
    ⭐ 本件列全是 E3 v4 重跑（resultsTakeover/e3v4_main）的子集、口徑相同 ⇒ 逐列 R、X、追蹤須與它相同（recon_v4.csv；乾跑只比缺值型態）。
 Y2 統計 ＝ seq2 U12（平均、中位、勝率、公告月分群 CI 1.96；n_eff ＝ min(筆數, 公告月數)）；★ n_eff ＜ 24 標「還沒測」、＜ 30 標「事件少」。
    CI 結果 ①（含 0）／②（下界 ＞ 0）／③（上界 ＜ 0），⛔ 只是描述、不判。
 Y3 組 ＝ 頻率表 W2：基準（E3_2011起、配到、配到普通股、分組母體）、重疊組 甲／乙／丙 是／否、互斥 只策略／只內部人／兩者皆是／兩者皆否；
    各 × {全、有減資、無減資} × {全、市值≤10億、市值＞10億}。段 ＝ 頻率表 W4。
 Y4 追蹤 ＝ seq2 U15（注意、處置 [day0, +20]／[day0, +60]；後來減資、全額交割 +250；事件與配對公司都報）。
 Y5 乾跑（seq458、seq366）：--dry ⇒ 所有 R 寫 0（缺值照留）、全部描述欄照算，只抓除以 0、空組、欄位錯；⛔ 不准任何含報酬的小樣本試跑。
"""
from __future__ import annotations

import argparse
import glob
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
from backtest import researchTakeover3_freq as F3           # noqa: E402
from backtest import researchTakeover as TM                 # noqa: E402
from backtest import researchTakeover_freq as TF            # noqa: E402
from backtest import researchRevTurn_freq as RT             # noqa: E402
from backtest import researchIndMom_freq as IMF             # noqa: E402

REG_SHA = F3.REG_SHA
OUT = "backtest/resultsTakeover3/main"
FREQ_DIR = F3.OUT
V4_MAIN = "backtest/resultsTakeover/e3v4_main"
WINS = TF.WINS
W250 = "後[+2,+250]"
WT = f"截斷{W250}"
SEGS3 = F3.SEGS3
SENT = ["描述，不是選股規則", "事件少（多數交叉格 n_eff ＜ 24 還沒測）", "「策略性投資人」是董事會預定的應募人類別，⛔ 不等於實際認購人",
        "台灣文獻只讀到摘要", "只看單筆、沒算賣掉的錢", "E3 只用 2011 起；未配到、非普通股、三欄空白不入分組"]
FU_COLS = ("注意20", "注意60", "處置20", "處置60", "後來減資250", "全額交割250")
LOG: list = []


def log(s):
    s = f"[{pd.Timestamp.now(tz='Asia/Taipei').strftime('%H:%M:%S')}] {s}"
    print(s, flush=True); LOG.append(s)


def all_groups():
    out = []
    for g in F3.GROUPS3:
        out += F3.variants(g)
    return out


def stat(x, mon):
    s = TM.stat(x, mon)
    if s.get("n", 0):
        s["還沒測"] = bool(s["n_eff"] < F3.NEFF_TEST)
    return s


def build_table(E):
    TAB = []
    E = E.copy(); E["公告月"] = E["date"].str[:7]
    for sg, x, y in SEGS3:
        sub0 = E[(E["date"] >= x) & (E["date"] <= y) & (E["st"] == "保留")]
        for g in all_groups():
            sub = F3.gsel3(sub0, g)
            ws = list(WINS) + ([WT] if "有減資" in g else [])
            for w in ws:
                rw = {"段": sg, "組": g, "窗": w if w != WT else f"{W250}（減資前截斷，敏感度）"}
                Rc, Xc, stc = f"R{w}", f"X{w}", f"狀態{w}"
                se = stat(sub[Rc], sub["公告月"]); sx = stat(sub[Xc], sub["公告月"])
                stv = sub[stc].astype(str) if stc in sub else pd.Series([], dtype=str)
                rw.update({"可接": len(sub), "R_n": se.get("n", 0), "R平均": se.get("mean"), "R中位": se.get("median"), "R勝率": se.get("win"),
                           "X_n": sx.get("n", 0), "X平均": sx.get("mean"), "X中位": sx.get("median"), "X勝率": sx.get("win"), "X_lo": sx.get("lo"),
                           "X_hi": sx.get("hi"), "X月數": sx.get("months"), "X_n_eff": sx.get("n_eff"), "還沒測(n_eff<24)": sx.get("還沒測", True),
                           "事件少(n_eff<30)": sx.get("n_eff<30", True), "CI結果(描述)": sx.get("CI結果"),
                           "下市長停截斷筆數": int(stv.str.contains("下市長停截斷|・截斷").sum()),
                           "減資跨斷點筆數": int(stv.str.startswith("減資跨斷點").sum()),
                           "不收_壞根": int(stv.str.startswith("窗內壞根").sum()), "不收_超出資料尾": int((stv == "超出資料尾").sum()),
                           "配對不可算或配對R缺": int((sub[Rc].notna() & sub[Xc].isna()).sum())})
                TAB.append(rw)
    return pd.DataFrame(TAB)


def followup(E, DX, tab, CAL):
    """seq2 U15 原式（TM.main 段落照抄）。"""
    NC = len(CAL)
    att = pd.read_csv(os.path.join(DX, "meta", "attention.csv"), dtype=str); dis = pd.read_csv(os.path.join(DX, "meta", "disposal.csv"), dtype=str)
    fds = [f for f in sorted(glob.glob(os.path.join(DX, "universe", "fulldelivery", "*.csv"))) if not os.path.basename(f).startswith("_")]
    fd = pd.concat([pd.read_csv(f, dtype=str, usecols=["date", "stock_id"]) for f in fds], ignore_index=True)

    def dmap(df, dc):
        m = defaultdict(list)
        for s, d in zip(df["stock_id"].astype(str).str.strip(), pd.to_datetime(df[dc], errors="coerce")):
            if pd.notna(d):
                m[s].append(np.datetime64(d))
        return {s: np.array(sorted(v)) for s, v in m.items()}
    MA, MD_, MF = dmap(att, "date"), dmap(dis, "announce_date"), dmap(fd, "date")
    MR = {s: np.array(sorted({np.datetime64(x[0]) for x in v})) for s, v in tab.items()}
    A0, D0, F0 = np.datetime64(pd.Timestamp(att["date"].min())), np.datetime64(pd.Timestamp("2011-01-03")), np.datetime64(pd.Timestamp(fd["date"].min()))

    def hit(M, s, lo, hi, incl_lo=True):
        v = M.get(s)
        if v is None:
            return False
        k = np.searchsorted(v, lo, "left" if incl_lo else "right")
        return bool(k < len(v) and v[k] <= hi)
    fu = defaultdict(list)
    for _, r in E.iterrows():
        res = {}
        if r["st"] == "保留":
            p0 = int(CAL.searchsorted(pd.Timestamp(r["day0"]))); d0 = np.datetime64(CAL[p0])
            for who, s in (("", r["sid"]), ("配", r["配對sid"])):
                if not s:
                    continue
                for nm, M, H, start in (("注意", MA, 20, max(A0, D0)), ("注意", MA, 60, max(A0, D0)), ("處置", MD_, 20, D0), ("處置", MD_, 60, D0),
                                        ("後來減資", MR, 250, None), ("全額交割", MF, 250, F0)):
                    key = f"{who}{nm}{H}"
                    if p0 + H >= NC or (start is not None and d0 < start):
                        res[key] = ""; continue
                    hi = np.datetime64(CAL[p0 + H])
                    res[key] = str(hit(M, s, d0, hi, incl_lo=(nm != "後來減資")))
        for c in FU_COLS:
            for who in ("", "配"):
                fu[f"{who}{c}"].append(res.get(f"{who}{c}", ""))
    for c, v in fu.items():
        E[c] = v
    return E


def fu_table(E):
    FU = []
    for g in all_groups():
        sub = F3.gsel3(E[E["st"] == "保留"], g)
        rw = {"組": g, "可接(2011～)": len(sub)}
        for c in FU_COLS:
            for who in ("", "配"):
                v = sub[f"{who}{c}"]; den = int((v != "").sum()); num = int((v == "True").sum())
                rw[f"{who}{c}_分母"] = den; rw[f"{who}{c}_比例"] = round(num / den, 4) if den else None
        FU.append(rw)
    return pd.DataFrame(FU)


def pct(v, d=1):
    return "—" if v is None or (isinstance(v, float) and not np.isfinite(v)) else f"{v * 100:+.{d}f}%"


def summary_md(T, J, out):
    L = ["# 私募分組（seq3）事件層描述：結果摘要", "",
         f"- 登錄：台股策略線 seq3 sha {REG_SHA}（裁定 seq457 §二、seq458 §四）｜描述、⛔ 不判、不計 N",
         f"- 事件表、私募對照 sha {J['事件表sha'][:10]}｜價格等 sha {J['價格sha'][:10]}｜{'⚠ 乾跑：R 全 0' if J.get('乾跑') else '正式跑'}",
         f"- 母體：E3 first12m、2011 起 {J['件數']['E3_2011起(first12m)']} 件；配到 {J['件數']['配到']}；配到普通股 {J['件數']['配到普通股']}；"
         f"分組母體 {J['件數']['分組母體']}（三欄空白 {J['件數']['三欄空白']}）", "",
         "## 必附", ""] + [f"- {s}" for s in SENT] + ["", "## 全期（2011～）各組 X（事件 − 配對）：平均〔CI〕｜中位｜勝率｜n_eff", "",
                                                     "| 組 | 前[-30,-1] | 當[0,+1] | 後[+2,+20] | 後[+2,+60] | 後[+2,+250] |", "|---|---|---|---|---|---|"]
    q = T[T["段"] == "全期(2011～)"]
    for g in ["分組母體"] + F3.OVL + F3.EXCL + ["分組母體_有減資", "分組母體_無減資", "甲是_有減資", "甲否_有減資", "乙是_有減資", "乙否_有減資"]:
        cells = []
        for w in WINS:
            r = q[(q["組"] == g) & (q["窗"] == w)]
            if not len(r) or not r.iloc[0]["X_n"]:
                cells.append("—"); continue
            r = r.iloc[0]
            tag = "（還沒測）" if r["還沒測(n_eff<24)"] else ""
            cells.append(f"{pct(r['X平均'])}〔{pct(r['X_lo'])},{pct(r['X_hi'])}〕{r['CI結果(描述)']}｜{pct(r['X中位'])}｜{r['X勝率'] * 100:.0f}%｜{int(r['X_n_eff'])}{tag}")
        L.append(f"| {g} | " + " | ".join(cells) + " |")
    L += ["", "- 有減資組的 後[+2,+250] 為「參考價接續」主口徑；敏感度（減資前截斷）見 表.csv。",
          "- CI 結果 ①含 0／②下界＞0／③上界＜0，只是描述；n_eff ＜ 24 標還沒測。分段（早年 2011～2016／探索／確認）與市值交叉見 表.csv。",
          "- 追蹤（注意、處置、後來減資、全額交割）見 追蹤.csv。"]
    open(os.path.join(out, "summary.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2); ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    out = os.path.join(F3.WORK3, "dry3_main") if a.dry else OUT
    os.makedirs(out, exist_ok=True)
    reg = IMF.reg_check(REG_SHA)
    log(f"[登錄] {reg}（sha {REG_SHA} 已驗）｜{'乾跑：R 全寫 0' if a.dry else '正式跑'}")
    FJ = json.load(open(os.path.join(FREQ_DIR, "freq.json"), encoding="utf-8"))
    ev_full = F3.setup(); TM.WORK = F3.WORK3
    if FJ["事件表sha"] != ev_full:
        raise SystemExit("⛔ 頻率表事件表 sha 不同")
    sha, DN, MD = RT.ensure_data(None)
    if sha != FJ["價格sha"]:
        raise SystemExit("⛔ 價格 sha 不同")
    PX = TF.price_panel(sha, DN, a.procs); CAL = PX["CAL"]
    log(f"[價格] {CAL[0].date()}～{CAL[-1].date()}｜{time.time() - t0:.0f}s")
    # Y0
    _, Es, _ = F3.build(PX, sha, DN, ev_full)
    F = pd.read_csv(os.path.join(FREQ_DIR, "events.csv.gz"), dtype=str, keep_default_na=False)
    rec = {"列數": [len(Es), len(F)], "欄相同": list(Es.columns) == list(F.columns)}
    diff = []
    if rec["欄相同"] and len(Es) == len(F):
        Ex = Es.astype(str)
        for c in F.columns:
            m = Ex[c].to_numpy() != F[c].to_numpy()
            if m.any():
                diff.append({"欄": c, "不同列數": int(m.sum())})
    rec["不同欄"] = diff
    pd.DataFrame(diff or [{"欄": "（全部相同）", "不同列數": 0}]).to_csv(os.path.join(out, "recon.csv"), index=False, encoding="utf-8-sig")
    log(f"[Y0 重建] {rec}")
    if not (rec["欄相同"] and len(Es) == len(F) and not diff):
        raise SystemExit("⛔ 頻率表逐列重建不同 ⇒ 中止、不算報酬")
    E = F3.tags(F)
    # Y1
    DX = TM.ensure_extra(sha)
    tab, srcc = TM.red_table(DX)
    RD = TM.Red(PX, tab); ix = PX["ix"]
    log(f"[參考價表] 來源 {srcc}")
    recs = []
    for k, r in E.iterrows():
        row = {"_k": k}
        if r["st"] != "保留":
            recs.append(row); continue
        i = ix[r["sid"]]; p0 = int(CAL.searchsorted(pd.Timestamp(r["day0"])))
        j = ix[r["配對sid"]] if r["配對sid"] else None
        red = r["with_reduction"] == "1"
        for w, (a_, b_) in WINS.items():
            if red and w == W250:
                Re, se, ee, cut = TM.ret_red(PX, RD, i, p0, a_, b_, "接續")
                Rm, sm = (np.nan, "") if j is None else TM.ret_red(PX, RD, j, p0, a_, b_, "接續")[:2]
                Rt, stt, _, cutp = TM.ret_red(PX, RD, i, p0, a_, b_, "截斷")
                if j is not None and np.isfinite(Rt):
                    Rmt, smt = TM.ret_red(PX, RD, j, p0, a_, b_, "接續", exit_pos=(cutp if cutp >= 0 else None))[:2]
                else:
                    Rmt, smt = np.nan, ""
                row.update({f"R{WT}": Rt, f"狀態{WT}": stt, f"配R{WT}": Rmt, f"配狀態{WT}": smt})
            else:
                Re, se, _ = TM.ret_std(PX, i, p0, a_, b_)
                Rm, sm = (np.nan, "") if j is None else TM.ret_std(PX, j, p0, a_, b_)[:2]
            row.update({f"R{w}": Re, f"狀態{w}": se, f"配R{w}": Rm, f"配狀態{w}": sm})
        recs.append(row)
    RR = pd.DataFrame(recs).set_index("_k")
    for c in RR.columns:
        if c.startswith("R") or c.startswith("配R"):
            RR[c] = pd.to_numeric(RR[c], errors="coerce")
            if a.dry:
                RR[c] = RR[c].where(RR[c].isna(), 0.0)
    E = E.join(RR)
    for w in list(WINS) + [WT]:
        E[f"X{w}"] = E[f"R{w}"] - E[f"配R{w}"]
    log(f"[報酬] 逐列完成｜參考價查詢 {len(RD.memo)} 個壞根：{dict(Counter(v[1] for v in RD.memo.values()))}｜{time.time() - t0:.0f}s")
    E = followup(E, DX, tab, CAL)
    # Y1 對 e3v4_main
    V = pd.read_csv(os.path.join(V4_MAIN, "events.csv.gz"), dtype=str, keep_default_na=False)
    V = V[V["類"] == "E3"].set_index(["sid", "date"])
    rv = []
    keys = list(zip(E["sid"], E["date"]))
    miss = [k for k in keys if k not in V.index]
    Vs = V.reindex(keys)
    for c in [f"R{w}" for w in list(WINS) + [WT]] + [f"配R{w}" for w in list(WINS) + [WT]] + [f"狀態{w}" for w in list(WINS) + [WT]] + list(FU_COLS) + [f"配{c}" for c in FU_COLS]:
        mine = E[c].to_numpy(); theirs = Vs[c].to_numpy()
        if c.startswith(("R", "配R")):
            m1 = np.asarray(pd.to_numeric(pd.Series(mine), errors="coerce"), float); m2 = np.asarray(pd.to_numeric(pd.Series(theirs), errors="coerce"), float)
            nan_bad = int((np.isnan(m1) != np.isnan(m2)).sum())
            val_bad = 0 if a.dry else int((np.abs(np.nan_to_num(m1) - np.nan_to_num(m2)) > 1e-12).sum())
            rv.append({"欄": c, "缺值型態不同": nan_bad, "值不同": val_bad if not a.dry else "（乾跑不比值）"})
        else:
            s1 = pd.Series(mine).fillna("").astype(str).to_numpy(); s2 = pd.Series(theirs).fillna("").astype(str).to_numpy()
            rv.append({"欄": c, "字串不同": int((s1 != s2).sum())})
    RV = pd.DataFrame(rv)
    RV.to_csv(os.path.join(out, "recon_v4.csv"), index=False, encoding="utf-8-sig")
    nbad = int(RV.drop(columns=["欄"]).apply(pd.to_numeric, errors="coerce").fillna(0).to_numpy().sum())
    log(f"[Y1 對 e3v4_main] 缺列 {len(miss)}｜不同格合計 {nbad}")
    # Y2、Y3
    T = build_table(E)
    FU = fu_table(E)
    bad_cells = T[(T["X_n"] > 0) & T["X平均"].isna()]
    log(f"[表] {len(T)} 格｜X_n＝0 的格 {int((T['X_n'] == 0).sum())}｜X_n＞0 但平均缺 {len(bad_cells)}")
    J = {"性質": "公開收購／經營權／私募策略投資人 seq3 E3 分組事件層描述（不計 N、不判）" + ("【乾跑 R 全 0】" if a.dry else ""),
         "乾跑": bool(a.dry), "登錄": f"台股策略線 seq3 sha {REG_SHA}", "裁定": "seq457 §二、seq458 §四",
         "價格sha": sha, "事件表sha": ev_full, "重建": rec, "對e3v4": {"缺列": len(miss), "不同格": nbad}, "參考價表來源": srcc,
         "件數": FJ["件數"], "必附": SENT, "同根兩出場價": "每窗一個出場價 ⇒ seq373 不適用",
         "讀法": __doc__.split("═══ 讀法")[1], "時間": pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")}
    T.to_csv(os.path.join(out, "表.csv"), index=False, encoding="utf-8-sig")
    FU.to_csv(os.path.join(out, "追蹤.csv"), index=False, encoding="utf-8-sig")
    with gzip.open(os.path.join(out, "events.csv.gz"), "wt", encoding="utf-8") as fh:
        E.to_csv(fh, index=False)
    json.dump(J, open(os.path.join(out, "main.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    summary_md(T, J, out)
    log(f"[完] {time.time() - t0:.0f}s ⇒ {out}")
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
