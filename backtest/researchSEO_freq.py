# -*- coding: utf-8 -*-
"""現金增資、可轉債公告後偏弱 seq2【頻率表・乾跑】（台股策略線 登錄 sha bdf021608239a93d，2026-10-21 00:20；裁定 seq385 第三題、seq388 發號、
seq411 §三 核 seq2（排除 ipo＝1、私募另組只描述、早年描述；先交頻率表）；Loughran & Ritter 1995、可轉債 Spiess & Affleck-Graves 1999）——回測線計算子代理。
避開名單的事件層描述（N 不計）。
⛔ 只數事件、剔除計數、n_eff、配對可行性；⛔ 不讀、不算、不存任何進場後的價格、報酬、持有期結果。
   價格只用 ≤ 公告日的還原收盤（前 12 個月報酬，只用來分五分位、⛔ 不存）、公告日市值、500 張閘，與進場日 e 的成交／開盤／鎖漲停旗標。
⛔ 不 commit、不改既有程式與結果夾；researchIndMom_freq（共用面板）⛔ 只 import。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchSEO_freq [--procs 2]
    對帳：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchSEO_freq_check
輸出 backtest/resultsSEO/freq/：freq.json、freq.csv、by_year.csv、match.csv、equiv.csv、events.csv.gz（只有代號、日期、組、剔除原因、配對候選數）、run.log

═══ 讀法（S 標；⛔ 在看任何本件數字之前寫死於 2026-10-21（台北）；★＝執行者定，〔 〕內為另一讀法）═══
 S1 事件表 ＝ tw-stock-data 最新 origin/main 的 data/meta/seo_cb_events/seo_cb_events.csv（git fetch 後 archive 到 ~/b2fwork/main_<sha12>，唯讀）。
    組（登錄 §二）：S ＝ seo ∧ private 0 ∧ ipo 0｜C ＝ cb ∧ private 0（overseas 0 標「國內」、1 標「海外」，併 C）｜S私 ＝ seo ∧ private 1 ∧ ipo 0｜
    C私 ＝ cb ∧ private 1（含海外私募）。⛔ ipo＝1 全部排除（計數）。S、C 主判；S私、C私 只描述。
 S2 同公司 12 個月內多次公告只取第一次：★ 逐組、依日期；與「上一筆保留事件」相隔 ＜ 12 個曆月（d < 上次 ＋ 12 個月）⇒ 略過（計數）；
    ★ 去重在事件表層做（先去重、再套價格母體）〔另一讀法：先套母體再去重〕。同日同公司 S、C 都有 ⇒ 兩組都算、重疊照報（S10）。
 S3 公告日 d ＝ date 欄（重訊發布日）。★ 判定日 T ＝ d 當天或之前最後一個交易日（世界日曆）；進場 e ＝ d 之後第一個交易日（登錄 §二「公告日下一交易日開盤」）。
    世界 ＝ e 所在世界（e ≤ 2014-12-31 ⇒ 早年 eotc；否則主 H2D）；★ T 不在同一世界（跨 2014→2015 接縫）⇒ 剔除「跨世界接縫」。
    d 早於世界日曆起點（2004-02-11）⇒「早於價格資料」；e 超出日曆 ⇒「超出資料尾」。
 S4 母體：四碼普通股（PRE.okcode）∧ 在面板（UG.gate3(GATE_V2) ∩ load_bars ≥ 260 根、含已下市）∧ 500 張閘在 T（Frame.gate[T]：t−20～t−1 均量 ≥ 500 張
    ∧ 含 T 的 20 交易日有成交；登錄 §四「公告日判（T−20～T−1）」）∧ pit_valid[T]。剔除依序計數。
 S5 進場剔除（PTH 頻率表 P5 同序）：壞根(T,e] → e無成交 → e開盤鎖漲停；保留 ＝ 事件。
 S6 段（依 e）：探索 2017-03-02～2021-12-30｜確認 2022-01-03～資料尾｜早年 2005-01-01～2016-12-31（描述；上櫃股價 2007-07 起）；2017-01～02 不入段（照報）。
    ★ 1 年持有走完 ⇔ e ＋ 12 個月 ≤ 主世界資料尾；3 年同理（只收整筆落在資料內，登錄 §三）；6 個月描述同理。
    n_eff ＝ min(事件數, 有事件的公告月數)（★ CI 依公告月分群）；＜ 30 照標。
 S7 已下市（★ 代號不在 origin/main stocks.csv 或其 last_seen 早於最晚 last_seen 10 天以上）比例。
 S8 配對可行性（登錄 §二；⛔ 只數候選、不取任何配對後價格）：橫斷面 ＝ T 當天母體（S4 的閘 ∧ 前 12 個月報酬可算 ∧ 市值 ＞ 0）；
      前 12 個月報酬 ＝ c[T] ÷ c[a] − 1，a ＝ T 往前 12 個曆月那天當天或之前最後一根有效 K 棒，(a, T] 無壞根（IndMom I3 同式）；市值 ＝ 原始收盤 × 股數（T 以前最後一筆）。
      ★ 五分位、十分位切點以該橫斷面（含發行公司）計算。
      非發行 ＝ 事件表【全部列】（任一 class、含私募、海外、ipo）中，[d − 3 年, d ＋ 3 年] 內沒有公告的公司；⚠ d ＋ 3 年超過事件表尾（2026-10-20）者向後只看到表尾（照報筆數）。
      主配對池 ＝ 非發行 ∧ 同市值十分位 ∧ 同前 12 個月報酬五分位（★「同規模」讀成同市值十分位，池內取市值最接近者）；
      放寬池 ＝ 非發行 ∧ 同市值十分位（不看報酬五分位）（登錄「放寬到同十分位市值」）；兩池都空 ⇒ 配對失敗。
      發行公司本身前 12 個月報酬或市值不可算 ⇒「配對不可算」（多為上市未滿 12 個月）。報：主池候選數分布、主配對成功率、放寬比例、失敗。
 S9 段內各組：事件數、相異公司、每年、n_eff、1 年／3 年走完的事件數與 n_eff、已下市比例、配對成功率。
 S10 seq377 乾跑等價：S vs C 同公司同日、同公司 ±30 天、±12 個月的重疊；C 國內 vs 海外；S vs S私（同公司 ±12 個月）。兩組幾乎同一批公司 ⇒ 先報。
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import time
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchIndMom_freq as IM              # noqa: E402  共用面板（新檔，⛔ 只 import）
from backtest import researchIndRev_prereg as PRE           # noqa: E402  okcode

REG_SHA = "bdf021608239a93d"
OUT = "backtest/resultsSEO/freq"
GROUPS = ("S", "C", "S私", "C私")
SEGS = {"探索": ("2017-03-02", "2021-12-30"), "確認": ("2022-01-03", None), "早年": ("2005-01-01", "2016-12-31")}
NEFF_MIN = 30
LOG = IM.LOG
log = IM.log


def load_events(DATA):
    ev = pd.read_csv(os.path.join(DATA, "meta", "seo_cb_events", "seo_cb_events.csv"), dtype={"stock_id": str, "serial": str})
    ev["d"] = pd.to_datetime(ev["date"])
    for c in ("private", "overseas", "ipo"):
        ev[c] = pd.to_numeric(ev[c], errors="coerce").fillna(0).astype(int)
    g = np.where(ev["class"] == "seo", np.where(ev["private"] == 1, "S私", "S"), np.where(ev["private"] == 1, "C私", "C"))
    ev["組"] = g
    ev["海外"] = (ev["class"] == "cb") & (ev["overseas"] == 1)
    return ev.sort_values(["d", "time", "stock_id"]).reset_index(drop=True)


def dedup12(ev):
    """S2：逐組、逐公司，與上一筆保留事件相隔 ＜ 12 個月 ⇒ 略過。回保留布林。"""
    keep = np.zeros(len(ev), bool)
    last = {}
    for k, (g, s, d) in enumerate(zip(ev["組"], ev["stock_id"], ev["d"])):
        key = (g, s)
        if key in last and d < last[key] + pd.DateOffset(months=12):
            continue
        keep[k] = True; last[key] = d
    return keep


def prior12(Z, i, T):
    cal = Z["cal"]
    a_pos = int(cal.searchsorted(cal[T] - pd.DateOffset(months=12), side="right")) - 1
    if a_pos < 0:
        return np.nan
    r, st, _ = IM.window_ret(Z, i, a_pos, T)
    return r if st == "ok" else np.nan


def xsec(Z, T, memo):
    """T 橫斷面：{i: (市值, 前12月報酬)}、市值十分位切點、報酬五分位切點。"""
    if T in memo:
        return memo[T]
    out = {}
    for i in np.flatnonzero(Z["G"][:, T] & np.isfinite(Z["C"][:, T])):
        mc = Z["MC"][i, T]
        if not (np.isfinite(mc) and mc > 0):
            continue
        r = prior12(Z, i, T)
        if np.isfinite(r):
            out[int(i)] = (float(mc), float(r))
    if len(out) >= 10:
        mcs = np.array([v[0] for v in out.values()]); rs = np.array([v[1] for v in out.values()])
        qm = np.quantile(mcs, np.linspace(0.1, 0.9, 9)); qr = np.quantile(rs, np.linspace(0.2, 0.8, 4))
    else:
        qm = qr = None
    memo[T] = (out, qm, qr)
    return memo[T]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=2)
    a = ap.parse_args()
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    reg = IM.reg_check(REG_SHA)
    log(f"[登錄] {reg}（sha {REG_SHA} 已驗）")
    sha, DATA = IM.ensure_main()
    log(f"[資料] origin/main {sha[:10]} ⇒ {DATA}")
    ev = load_events(DATA)
    tail_ev = ev["d"].max()
    st = pd.read_csv(os.path.join(DATA, "meta", "stocks.csv"), dtype=str)
    ls = pd.to_datetime(st["last_seen"], errors="coerce"); alive = set(st.loc[ls >= ls.max() - pd.Timedelta(days=10), "stock_id"])
    Zs = {"早年": IM.panel_aux(IM.build_panel("早年", a.procs)), "主": IM.panel_aux(IM.build_panel("主", a.procs))}
    IX = {wn: {s: i for i, s in enumerate(Z["sids"])} for wn, Z in Zs.items()}
    main_tail = Zs["主"]["cal"][-1]
    log(f"[事件表] {len(ev)} 筆 {ev['d'].min().date()}～{tail_ev.date()}｜{dict(Counter(ev['組']))}｜ipo {int(ev['ipo'].sum())}")
    # 發行公司日期表（S8 非發行判定用：全部列）
    iss = defaultdict(list)
    for s, d in zip(ev["stock_id"], ev["d"]):
        iss[s].append(d)
    iss = {s: np.array(sorted(v), dtype="datetime64[ns]") for s, v in iss.items()}

    def issued_near(s, lo, hi):
        v = iss.get(s)
        if v is None:
            return False
        k = np.searchsorted(v, lo, "left")
        return k < len(v) and v[k] <= hi

    rows = []
    memo = {"早年": {}, "主": {}}
    ev_ipo = ev[ev["ipo"] == 1]
    ev_ = ev[ev["ipo"] == 0].reset_index(drop=True)
    keep = dedup12(ev_)
    for k, r in ev_.iterrows():
        s, d, g = r["stock_id"], r["d"], r["組"]
        row = {"sid": s, "date": str(d.date()), "time": r["time"], "組": g, "海外": bool(r["海外"]), "market": r["market"], "已下市": s not in alive,
               "st": "", "世界": "", "T": "", "e": ""}
        if not keep[k]:
            row["st"] = "12個月內重複略過"; rows.append(row); continue
        if not PRE.okcode(s):
            row["st"] = "非四碼普通股"; rows.append(row); continue
        # 世界
        wn = None
        for w in ("早年", "主"):
            cal = Zs[w]["cal"]
            pe = int(cal.searchsorted(d, side="right"))
            if pe < len(cal) and (w == "主" or cal[pe] <= pd.Timestamp("2014-12-31")):
                wn = w; break
        if wn is None:
            row["st"] = "超出資料尾"; rows.append(row); continue
        Z = Zs[wn]; cal = Z["cal"]
        e = int(cal.searchsorted(d, side="right")); T = int(cal.searchsorted(d, side="right")) - 1
        if T < 0:
            row["st"] = "早於價格資料" if wn == "早年" else "跨世界接縫"; rows.append(row); continue
        row.update({"世界": wn, "T": str(cal[T].date()), "e": str(cal[e].date())})
        i = IX[wn].get(s)
        if i is None:
            row["st"] = "不在面板(gate3／不足260根)"; rows.append(row); continue
        if not (Z["G"][i, T] and np.isfinite(Z["C"][i, T])):
            row["st"] = "閘外(500張/pit/T無K棒)"; rows.append(row); continue
        row["st"] = IM.entry_flag(Z, i, T, e)
        # 持有走完
        ed = cal[e]
        for nmh, mo in (("6月走完", 6), ("1年走完", 12), ("3年走完", 36)):
            row[nmh] = bool(ed + pd.DateOffset(months=mo) <= main_tail)
        row["前後3年窗截到表尾"] = bool(d + pd.DateOffset(years=3) > tail_ev)
        # S8 配對可行性
        out, qm, qr = xsec(Z, T, memo[wn])
        if int(i) not in out or qm is None:
            row["配對"] = "配對不可算"
        else:
            mc0, r0 = out[int(i)]
            dm = int(np.searchsorted(qm, mc0, "right")); dr = int(np.searchsorted(qr, r0, "right"))
            lo = np.datetime64(d - pd.DateOffset(years=3)); hi = np.datetime64(d + pd.DateOffset(years=3))
            non = {j for j in out if not issued_near(Z["sids"][j], lo, hi)}
            same_d = [j for j in non if j != i and int(np.searchsorted(qm, out[j][0], "right")) == dm]
            prim = [j for j in same_d if int(np.searchsorted(qr, out[j][1], "right")) == dr]
            row["主池候選數"] = len(prim); row["放寬池候選數"] = len(same_d)
            row["配對"] = "主配對" if prim else ("放寬配對" if same_d else "配對失敗")
        rows.append(row)
        if (k + 1) % 1000 == 0:
            log(f"  事件 … {k + 1}／{len(ev_)}｜{time.time() - t0:.0f}s")
    E = pd.DataFrame(rows)
    E["e_dt"] = pd.to_datetime(E["e"], errors="coerce")
    J = {"性質": "現增／可轉債公告後 seq2 頻率表乾跑（⛔ 未讀、未算任何進場後價格、報酬、持有期結果）", "登錄": f"台股策略線 seq2 sha {REG_SHA}",
         "裁定": "seq385 第三題、seq388 發號、seq411 §三（描述、N 不計）", "資料": {"origin/main": sha, "事件表筆數": int(len(ev)),
                                                                        "事件表期間": [str(ev['d'].min().date()), str(tail_ev.date())]},
         "ipo排除": {g: int(v) for g, v in Counter(ev_ipo["組"]).items()},
         "去重前(非ipo)": {g: int(v) for g, v in Counter(ev_["組"]).items()},
         "剔除總表": {g: dict(Counter(E.loc[E["組"] == g, "st"])) for g in GROUPS}, "段": {}}
    FREQ = []; BY = []; MATCH = []
    kept = E[E["st"] == "保留"]
    for sg, (x, y) in SEGS.items():
        x_ = pd.Timestamp(x); y_ = main_tail if y is None else pd.Timestamp(y)
        segj = {"期間": f"{x}～{y_.date()}"}
        for g in GROUPS + ("C國內", "C海外"):
            if g == "C國內":
                sub = kept[(kept["組"] == "C") & ~kept["海外"]]
            elif g == "C海外":
                sub = kept[(kept["組"] == "C") & kept["海外"]]
            else:
                sub = kept[kept["組"] == g]
            sub = sub[(sub["e_dt"] >= x_) & (sub["e_dt"] <= y_)]
            mon = sub["date"].str[:7]
            nev = len(sub); nm_ = mon.nunique(); ne = min(nev, nm_)
            gj = {"事件數(保留)": nev, "相異公司": int(sub["sid"].nunique()), "公告月數": int(nm_), "n_eff": ne, "n_eff<30": bool(ne < NEFF_MIN),
                  "已下市比例": round(float(sub["已下市"].mean()), 4) if nev else None}
            for h in ("6月走完", "1年走完", "3年走完"):
                s2 = sub[sub[h].astype(bool)]
                gj[f"{h}_事件"] = len(s2); gj[f"{h}_n_eff"] = min(len(s2), int(s2["date"].str[:7].nunique()))
                gj[f"{h}_n_eff<30"] = bool(gj[f"{h}_n_eff"] < NEFF_MIN)
            mc = Counter(sub["配對"].fillna("配對不可算"))
            gj["配對"] = dict(mc)
            gj["主配對成功率"] = round(mc.get("主配對", 0) / nev, 4) if nev else None
            gj["放寬比例"] = round(mc.get("放寬配對", 0) / nev, 4) if nev else None
            pc = sub["主池候選數"].dropna().to_numpy(float) if "主池候選數" in sub else np.array([])
            gj["主池候選數分布"] = IM.qd(pc)
            gj["主池候選數_0／1～4／5～19／≥20"] = [int((pc == 0).sum()), int(((pc >= 1) & (pc <= 4)).sum()), int(((pc >= 5) & (pc <= 19)).sum()), int((pc >= 20).sum())]
            gj["前後3年窗截到表尾"] = int(sub["前後3年窗截到表尾"].astype(bool).sum()) if nev else 0
            gj["每年"] = {int(k): int(v) for k, v in sub["e_dt"].dt.year.value_counts().sort_index().items()}
            segj[g] = gj
            FREQ.append({"段": sg, "組": g, "期間": segj["期間"], **{k: v for k, v in gj.items() if not isinstance(v, (dict, list))},
                         "候選數中位": gj["主池候選數分布"]["中位"] if gj["主池候選數分布"] else None})
            MATCH.append({"段": sg, "組": g, **gj["配對"], "主配對成功率": gj["主配對成功率"], "放寬比例": gj["放寬比例"],
                          "候選0": gj["主池候選數_0／1～4／5～19／≥20"][0], "候選1～4": gj["主池候選數_0／1～4／5～19／≥20"][1],
                          "候選5～19": gj["主池候選數_0／1～4／5～19／≥20"][2], "候選≥20": gj["主池候選數_0／1～4／5～19／≥20"][3]})
        J["段"][sg] = segj
        log(f"[段 {sg}] " + "｜".join(f"{g} n={segj[g]['事件數(保留)']} n_eff={segj[g]['n_eff']}（1年走完 {segj[g]['1年走完_n_eff']}）" for g in GROUPS))
    # 每年（公告年）× 組 × 狀態
    E["年"] = E["date"].str[:4].astype(int)
    for (yy, g), sub in E.groupby(["年", "組"]):
        c = Counter(sub["st"])
        BY.append({"公告年": yy, "組": g, "列數(非ipo)": len(sub), **{f"st_{k}": v for k, v in c.items()},
                   "C海外(保留)": int(((sub["st"] == "保留") & sub["海外"]).sum()) if g == "C" else None})
    for (yy, g), n in Counter(zip(ev_ipo["d"].dt.year, ev_ipo["組"])).items():
        BY.append({"公告年": yy, "組": g, "ipo排除": n})
    # S10 等價
    EQ = []

    def near(A, B, days):
        Bd = defaultdict(list)
        for s, d in zip(B["sid"], pd.to_datetime(B["date"])):
            Bd[s].append(d)
        hit = 0
        for s, d in zip(A["sid"], pd.to_datetime(A["date"])):
            if any(abs((d - x).days) <= days for x in Bd.get(s, ())):
                hit += 1
        return hit
    Sx = kept[kept["組"] == "S"]; Cx = kept[kept["組"] == "C"]; SPx = kept[kept["組"] == "S私"]
    Cd = Cx[~Cx["海外"]]; Co = Cx[Cx["海外"]]
    for nm_, A, B in (("S vs C", Sx, Cx), ("C國內 vs C海外", Cd, Co), ("S vs S私", Sx, SPx)):
        for days in (0, 30, 365):
            h = near(A, B, days); h2 = near(B, A, days)
            EQ.append({"比較": nm_, "相隔≤天": days, "A筆數": len(A), "B筆數": len(B), "A中B也有": h, "比例_A": round(h / len(A), 4) if len(A) else None,
                       "B中A也有": h2, "比例_B": round(h2 / len(B), 4) if len(B) else None})
    J["seq377等價"] = EQ
    J["讀法"] = __doc__.split("═══ 讀法")[1]
    J["時間"] = pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")
    pd.DataFrame(FREQ).to_csv(os.path.join(OUT, "freq.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(BY).sort_values(["公告年", "組"]).to_csv(os.path.join(OUT, "by_year.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(MATCH).to_csv(os.path.join(OUT, "match.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(EQ).to_csv(os.path.join(OUT, "equiv.csv"), index=False, encoding="utf-8-sig")
    with gzip.open(os.path.join(OUT, "events.csv.gz"), "wt", encoding="utf-8") as fh:
        E.drop(columns=["e_dt"]).to_csv(fh, index=False)
    json.dump(J, open(os.path.join(OUT, "freq.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    log(f"[完] {time.time() - t0:.0f}s")
    open(os.path.join(OUT, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
