# -*- coding: utf-8 -*-
"""PREREG重大訊息類別反應 seq1——探索段分類材料（裁定 seq298 §二：N＝36；一次修訂權；⭐ 這一步不算任何報酬）。回測線。

登錄：台股策略線「重大訊息類別反應」seq1（sha 04bdf199cf275665，2026-10-04 20:55）§一、§二；裁定 seq298 §二。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchNewsCat explore

⭐ 讀法寫死時間：2026-10-04 21:05（台北，寫檔前 date）；21:08 執行（README 的產出時間由腳本當場 date 寫入）；寫死前 ⛔ 沒看任何主旨文字樣本或各類則數。
⛔ 本支 explore 只讀 news 2015～2020 六個年檔（⛔ 不讀 2014 以前、⛔ 不讀 2021 以後）、名冊與逐日檔的 name／market 欄（GATE_V2 母體用）、交易日曆；
   ⛔ 不讀任何價格欄、⛔ 不算任何報酬。

═══ 資料 ═══
  news：tw-stock-data main c2e0bf24ae 的 data/mops/news/2015.csv～2020.csv（git archive 到 ~/msdata/<sha>，只取這六檔）
  名冊、逐日檔 name／market、交易日曆：edc6f8002f 快照（researchH2，同 W1）
═══ 母體（登錄 §一）═══
  market ∈ {sii, otc}；且 UG.set_gate_v2(True) 的母體：
    靜態 ＝ universe_gate.gate3（GATE_V2）：kind＝stock ∧ 名冊市場上市櫃 → 排除 -DR → 只剔整段在創新板者
    逐日 ＝ pit_valid 在「事件交易日」為真（當日名稱不在創新板、逐列市場上市櫃）
  代號不在名冊（多為 2015 前已下市或非普通股）⇒ 不在母體（計數照報）；處置、停牌閘只影響報酬那一步 ⇒ 本步不套（執行者補）
═══ 分類（登錄 §二 逐字；只看主旨字串；優先序由上往下、第一個命中即歸類）═══
  執行者補 N1：第 6 類「（得標｜訂單｜接單｜簽訂 且 （合約｜契約｜協議））」讀成 得標 ∨ 訂單 ∨ 接單 ∨ (簽訂 ∧ (合約∨契約∨協議))（「且」只綁「簽訂」）
  執行者補 N2：字串比對用原始主旨（不做全形半形轉換）；關鍵字皆中文、不受影響
  旗標：主旨含「更正」或「補充」⇒ 照表歸類、另記旗標
═══ 材料（裁定 seq298 §二）═══
  ① 各類則數，逐年（全部則數；另報「同股、同類、5 個交易日內只取第一則」去重版——事件交易日 ＝ 登錄 §三：發言時間 ≤ 13:30 且為交易日 ⇒ 當天，
     否則 ⇒ 次一交易日；去重 ＝ 與同股同類上一則保留事件相差 ≥ 5 個交易日才保留〔執行者補 N3〕）；更正／補充旗標則數
  ② 每類隨機 50 則主旨：numpy default_rng(20261004)，每類依 (date, time, stock_id, serial) 排序後不放回抽 50（不足全取）
  ③「其他」類最常見 200 種主旨樣式：正規化〔執行者補 N4〕＝ 去掉該則的公司簡稱與代號 → NFKC → 連續數字換成「#」→ 去空白；依次數排序（同數依字串）
輸出 backtest/resultsNewsCat/explore_material/：README.md、counts_by_year.csv、counts_by_year_dedup.csv、flags.csv、sample50.csv、other_top200.csv、other_top1000.csv、universe_log.json
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import unicodedata

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest")); sys.path.insert(0, os.path.expanduser("~/tw-p17"))
import researchH2 as H2                                 # D.DATA ⇒ edc6f8002f；chdir ⇒ repo
D = H2.D
from backtest import universe_gate as UG

OUT = "backtest/resultsNewsCat/explore_material"
NEWS_SHA = "c2e0bf24ae9a48b3ed0a989dca636de539c7c38d"
ND = os.path.expanduser(f"~/msdata/{NEWS_SHA}/data/mops/news")
YEARS = range(2015, 2021)
SEED = 20261004

ANY = lambda s, ws: any(w in s for w in ws)
CATS = [
    (1, "注意交易資訊公告", lambda s: ANY(s, ("注意交易資訊", "交易異常", "公布注意"))),
    (2, "澄清媒體報導", lambda s: ANY(s, ("澄清", "媒體報導", "報載", "新聞報導"))),
    (3, "減資", lambda s: "減資" in s),
    (4, "併購／合資", lambda s: ANY(s, ("合併", "併購", "收購", "公開收購", "股份轉換", "合資", "分割"))),
    (5, "增資／發債", lambda s: ANY(s, ("現金增資", "私募", "增資發行", "發行新股", "公司債", "可轉換", "海外存託憑證"))),
    (6, "得標／接單／合約", lambda s: ANY(s, ("得標", "訂單", "接單")) or ("簽訂" in s and ANY(s, ("合約", "契約", "協議")))),
    (7, "取得或處分資產", lambda s: ANY(s, ("取得", "處分")) and ANY(s, ("資產", "不動產", "使用權", "設備", "有價證券", "股權", "土地", "廠房"))),
    (8, "股利", lambda s: ANY(s, ("股利", "盈餘分配", "除息", "除權", "配息"))),
    (9, "自結財報／營收", lambda s: ANY(s, ("自結", "財務報告", "財報", "營業收入", "營收"))),
    (10, "經理人異動", lambda s: ANY(s, ("經理人", "總經理", "董事長", "財務主管", "會計主管", "發言人", "稽核主管"))
     and ANY(s, ("異動", "變動", "辭任", "解任", "新任", "更換", "退休"))),
    (11, "法說會", lambda s: ANY(s, ("法人說明會", "法說會", "業績說明會"))),
]
NAMES = {k: n for k, n, _ in CATS}; NAMES[12] = "其他"


def classify(s: str) -> int:
    for k, _, f in CATS:
        if f(s):
            return k
    return 12


def ensure_news():
    if all(os.path.exists(os.path.join(ND, f"{y}.csv")) for y in YEARS):
        return
    root = os.path.expanduser(f"~/msdata/{NEWS_SHA}")
    os.makedirs(root, exist_ok=True)
    paths = [f"data/mops/news/{y}.csv" for y in YEARS]                  # ⛔ 只取 2015～2020
    p = subprocess.run(["git", "archive", "--format=tar", NEWS_SHA] + paths, capture_output=True, check=True)
    subprocess.run(["tar", "-x", "-C", root], input=p.stdout, check=True)


def norm(subj: str, name: str, sid: str) -> str:
    s = str(subj)
    for t in (str(name), str(sid)):
        if t and t != "nan":
            s = s.replace(t, "")
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"\d+", "#", s)
    return re.sub(r"\s+", "", s)


def explore():
    ts = subprocess.run(["bash", "-c", "TZ=Asia/Taipei date '+%F %H:%M'"], capture_output=True, text=True).stdout.strip()
    ensure_news()
    os.makedirs(OUT, exist_ok=True)
    N = pd.concat([pd.read_csv(os.path.join(ND, f"{y}.csv"), dtype=str, keep_default_na=False) for y in YEARS], ignore_index=True)
    LOG = {"執行時間": f"{ts}（台北）", "news": f"main {NEWS_SHA}，只讀 {YEARS[0]}～{YEARS[-1]}", "原始則數": int(len(N))}
    N = N.drop_duplicates(["date", "time", "stock_id", "serial"])
    LOG["去鍵重複後"] = int(len(N)); LOG["market 分佈"] = N["market"].value_counts().to_dict()
    N = N[N["market"].isin(["sii", "otc"])].copy()
    LOG["market∈{sii,otc}"] = int(len(N))
    # GATE_V2 母體
    UG.set_gate_v2(True)
    stocks = pd.read_csv(os.path.join(H2.H2D, "meta", "stocks.csv"), dtype=str)
    G = set(UG.gate3(stocks)["stock_id"])
    cal = D.load_calendar(); calv = cal.values; n = len(cal)
    d = pd.to_datetime(N["date"]).values
    p0 = np.searchsorted(calv, d, side="left")                           # 當天或之後第一個交易日
    istd = (p0 < n) & (calv[np.minimum(p0, n - 1)] == d)
    late = N["time"].str.slice(0, 5).to_numpy() > "13:30"
    N["epos"] = np.where(istd & ~late, p0, np.where(istd, p0 + 1, p0))
    N["in_static"] = N["stock_id"].isin(G)
    pv = {}
    for s in sorted(set(N.loc[N["in_static"], "stock_id"])):
        pv[s] = UG.pit_valid(s, cal)
    N["in_pit"] = [bool(pv[s][min(int(e), n - 1)]) if s in pv else False for s, e in zip(N["stock_id"], N["epos"])]
    UG.set_gate_v2(False)
    LOG["不在 GATE_V2 靜態母體（代號不在名冊／非普通股／-DR／整段在板）"] = int((~N["in_static"]).sum())
    LOG["靜態母體內但事件日在板期或興櫃列"] = int((N["in_static"] & ~N["in_pit"]).sum())
    N = N[N["in_static"] & N["in_pit"]].copy()
    LOG["母體內則數"] = int(len(N)); LOG["母體內家數"] = int(N["stock_id"].nunique())
    N["year"] = N["date"].str[:4].astype(int)
    N["cat"] = [classify(s) for s in N["subject"]]
    N["類別"] = N["cat"].map(NAMES)
    N["更正補充"] = N["subject"].str.contains("更正|補充", regex=True)
    # ① 則數
    def tab(df):
        t = df.pivot_table(index=["cat", "類別"], columns="year", values="subject", aggfunc="count", fill_value=0)
        t["合計"] = t.sum(axis=1); t["占比"] = t["合計"] / t["合計"].sum()
        t.loc[(99, "合計"), :] = t.sum(); t.loc[(99, "合計"), "占比"] = 1.0
        return t.reset_index()
    T1 = tab(N); T1.to_csv(os.path.join(OUT, "counts_by_year.csv"), index=False, encoding="utf-8-sig")
    N = N.sort_values(["stock_id", "cat", "epos", "time", "serial"])
    keep = np.zeros(len(N), bool); last = {}
    for i, (s, c, e) in enumerate(zip(N["stock_id"], N["cat"], N["epos"])):
        k = (s, c)
        if k not in last or e - last[k] >= 5:
            keep[i] = True; last[k] = e
    T2 = tab(N[keep]); T2.to_csv(os.path.join(OUT, "counts_by_year_dedup.csv"), index=False, encoding="utf-8-sig")
    FL = N.groupby(["cat", "類別"])["更正補充"].agg(["sum", "count"]).reset_index().rename(columns={"sum": "含更正或補充", "count": "則數"})
    FL.to_csv(os.path.join(OUT, "flags.csv"), index=False, encoding="utf-8-sig")
    # ② 每類 50
    rng = np.random.default_rng(SEED); rows = []
    for c in range(1, 13):
        g = N[N["cat"] == c].sort_values(["date", "time", "stock_id", "serial"])
        idx = sorted(rng.choice(len(g), size=min(50, len(g)), replace=False)) if len(g) else []
        for j in idx:
            r = g.iloc[j]
            rows.append({"cat": c, "類別": NAMES[c], "date": r["date"], "time": r["time"], "stock_id": r["stock_id"], "name": r["name"], "subject": r["subject"]})
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "sample50.csv"), index=False, encoding="utf-8-sig")
    # ③ 其他 200
    O = N[N["cat"] == 12]
    pat = pd.Series([norm(s, nm, sid) for s, nm, sid in zip(O["subject"], O["name"], O["stock_id"])])
    vc = pat.value_counts()
    top = pd.DataFrame({"樣式": vc.index, "則數": vc.values}).sort_values(["則數", "樣式"], ascending=[False, True]).head(200).reset_index(drop=True)
    ex = dict(zip(pat, O["subject"]))
    top["例"] = top["樣式"].map(ex); top.insert(0, "名次", range(1, len(top) + 1))
    top["占其他比"] = top["則數"] / len(O)
    top.to_csv(os.path.join(OUT, "other_top200.csv"), index=False, encoding="utf-8-sig")
    # ③b 其他前 1,000 種（台股 1005-0321 要求：只要樣式與則數）
    t1k = pd.DataFrame({"樣式": vc.index, "則數": vc.values}).sort_values(["則數", "樣式"], ascending=[False, True]).head(1000).reset_index(drop=True)
    t1k.insert(0, "名次", range(1, len(t1k) + 1)); t1k["累計占其他比"] = t1k["則數"].cumsum() / len(O)
    t1k.to_csv(os.path.join(OUT, "other_top1000.csv"), index=False, encoding="utf-8-sig")
    LOG["前 1,000 種涵蓋其他類"] = float(t1k["則數"].sum() / len(O))
    LOG["其他類則數"] = int(len(O)); LOG["其他類樣式種數"] = int(len(vc)); LOG["前 200 種涵蓋其他類"] = float(top["則數"].sum() / len(O))
    json.dump(LOG, open(os.path.join(OUT, "universe_log.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # README
    L = [f"# PREREG重大訊息類別反應 seq1：探索段分類材料（2015～2020）", "",
         f"**產出**：{ts}（台北）｜⛔ 不含任何價格、報酬，也沒讀日 K｜給台股修一次關鍵字（seq2）用", "",
         f"- 資料：main {NEWS_SHA[:10]} 的 data/mops/news/2015～2020.csv（只讀這六檔）；母體 market∈{{sii, otc}} ∩ GATE_V2（edc6f8002f 名冊與逐日檔）",
         f"- 則數：原始 {LOG['原始則數']:,} → sii／otc {LOG['market∈{sii,otc}']:,} → 母體內 {LOG['母體內則數']:,} 則、{LOG['母體內家數']:,} 家"
         f"（不在靜態母體 {LOG['不在 GATE_V2 靜態母體（代號不在名冊／非普通股／-DR／整段在板）']:,}；事件日在板期／興櫃 {LOG['靜態母體內但事件日在板期或興櫃列']:,}）",
         f"- 「其他」{LOG['其他類則數']:,} 則、{LOG['其他類樣式種數']:,} 種樣式；前 200 種涵蓋 {LOG['前 200 種涵蓋其他類']:.1%}、前 1,000 種涵蓋 {LOG['前 1,000 種涵蓋其他類']:.1%}", "",
         "## 各類則數（全部；去重版見 counts_by_year_dedup.csv）", "",
         "| # | 類別 | " + " | ".join(str(y) for y in YEARS) + " | 合計 | 占比 | 去重後合計 | 含更正／補充 |",
         "|" + "---|" * (len(YEARS) + 6)]
    t2 = T2.set_index("cat"); fl = FL.set_index("cat")
    for r in T1.itertuples(index=False):
        c = r[0]
        vals = [int(getattr(r, f"_{i + 2}")) for i in range(len(YEARS))] if False else [int(T1.loc[T1["cat"] == c, y].iloc[0]) for y in YEARS]
        L.append(f"| {c if c != 99 else ''} | {r[1]} | " + " | ".join(f"{v:,}" for v in vals) +
                 f" | {int(T1.loc[T1['cat'] == c, '合計'].iloc[0]):,} | {float(T1.loc[T1['cat'] == c, '占比'].iloc[0]):.1%} | "
                 f"{int(t2.loc[c, '合計']):,} | {int(fl.loc[c, '含更正或補充']) if c in fl.index else int(fl['含更正或補充'].sum()):,} |")
    L += ["", "## 檔案", "- counts_by_year.csv、counts_by_year_dedup.csv（同股同類 5 個交易日內只取第一則）、flags.csv",
          f"- sample50.csv：每類隨機 50 則（numpy default_rng({SEED})；每類依 date、time、stock_id、serial 排序後不放回抽）",
          "- other_top200.csv：「其他」類最常見 200 種主旨樣式（去公司簡稱與代號 → NFKC → 數字換 # → 去空白；附一則原文例）",
          "- other_top1000.csv：同上樣式的前 1,000 種，只列樣式、則數、累計占比（無原文例）",
          "- universe_log.json：母體每一步的則數", "",
          "## 本步讀法（登錄沒寫清楚、執行者補）",
          "- N1 第 6 類讀成 得標 ∨ 訂單 ∨ 接單 ∨（簽訂 ∧（合約∨契約∨協議））",
          "- N2 比對用原始主旨（不轉全形半形）",
          "- N3 去重：同股同類與上一則保留事件相差 ≥ 5 個交易日才保留；事件交易日照登錄 §三（13:30 前且交易日 ⇒ 當天，否則次一交易日）",
          "- N4 樣式正規化如上；代號不在名冊者不在母體；處置、停牌閘只影響報酬那一步，本步不套"]
    open(os.path.join(OUT, "README.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L[:8])); print(json.dumps(LOG, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "explore":
        explore()
    else:
        raise SystemExit("用法：python -m backtest.researchNewsCat explore")
