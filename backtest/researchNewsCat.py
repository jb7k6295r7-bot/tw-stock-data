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


# ═════════════════════════════════════════════════════════════════════════════════════════════
# seq2：公告後股價反應（run）、查核（--check）、網頁與報告（page）——回測線
# ═════════════════════════════════════════════════════════════════════════════════════════════
RUN_DOC = """PREREG重大訊息類別反應 seq2（台股策略線登錄 sha b48ee3f4f02bf049，2026-10-05 08:09；裁定 seq302 凍結核准、N＝36、含早年段）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchNewsCat run [--procs 4]
    查核：python -m backtest.researchNewsCat --check ｜ 網頁＋REPORT.md：python -m backtest.researchNewsCat page
⭐ 讀法寫死時間：2026-10-05 08:30（台北，Windows 時鐘）；寫死前 ⛔ 沒看任何公告後報酬（探索材料只有則數與主旨）。
⛔ explore 模式（seq1 材料）程式一字未動；--check 會重跑 explore 到暫存夾、與 explore_material/ 逐位元組比（README／universe_log 只略過「產出時間」那一行）。

═══ 讀法（登錄 §一～§四逐字；S＝執行者補）═══
 S1 分類：附件 _重大訊息分類_seq2.py 的 classify() 逐字（下方 SEQ2_SRC，sha256 e25bd78f…；登錄「有出入以程式為準」）；主旨原文比對；
    減資分項（裁定 seq302：只描述、不計 N）：含 現金減資／退還股款／彌補虧損 ⇒「現金減資／彌補虧損」；否則含 庫藏股／註銷／限制員工／限制型／員工權利 ⇒
    「註銷庫藏股／限制股」；其餘 ⇒「其他減資」（S）。旗標：主旨含「更正」或「補充」。
 S2 資料：news ＝ main 8425186bd2 的 data/mops/news/1999～2026（只取公告日 1999-01-01～2026-09-30；1998.csv 不在任何段）；
    價 ＝ 主快照 ~/h2data/8425186bd2（2015-01-05～2026-10-02）＋早年上市＋上櫃版面 ~/earlydata/eotc_f65bb03e11/otc/data（2004-02-11～2014-12-31）。
    ⚠ 1999-01～2004-02-10 本專案沒有日 K ⇒ 早年段實際只算得到 2004-02-11 起（則數照報）；早年版面：上櫃 2007-07 前未收、
    上櫃 2007-07～12 除權息未還原、上櫃減資 2007～2012 為偵測非官方（裁定 seq283 必附）。
 S3 母體：market ∈ {sii, otc} ∩ gate3（GATE_V2 開；各版面自己的 stocks.csv 與逐日檔）∩ pit_valid(e)；含已下市；
    處置：母體閘不剔處置 ⇒ 照留（S）；基準日該檔無成交（停牌）⇒ 沒有基準價、剔除計數（S）；⛔ 不剔開盤漲停／跌停（量反應、不是量買不買得到，S）。
 S4 事件交易日 e（＝ N3 的事件交易日、同探索材料）：公告日是交易日且 time[:5] ≤ "13:30"（分鐘級、含 13:30 整分）⇒ 型 C、e＝當天；否則型 O、e＝次一交易日。
 S5 報酬（S：「往後數 H 個交易日」從公告日數）：型 C R＝還原收(e＋H)÷還原收(e)−1；型 O R＝還原收(e＋H−1)÷還原開(e)−1
    （公告日之後第 H 個交易日收盤；H＝1 ＝ e 當天開→收）；收盤停牌沿用前收、下市＝最後價。
 S6 基準②：同日 e、母體內（gate3 ∩ pit_valid(e)）同型同式 R 可算的股票，依前 20 日報酬分十分位（avgdown.deciles：rank×10//n）；
    前 20 日報酬 ＝ 有效 K 棒 20 根（avgdown.r20_cal）；型 C 量到收(e)；型 O 量到 e−1 以前最後一根有效 K 棒（停牌最多沿用 20 個交易日，S）；
    基準 ＝ 同十分位「其他」股票的 R 等權平均（S：扣掉自己）；當日成員 ＜ 20 檔 ⇒ 不算。X ＝ R − 基準②。
 S7 壞根（tw-stock-price-breaks）：價格斷點（data.breakpoints rule＝price／price+gap）＋幽靈還原事件（原始收盤比÷因子 ∉ [0.895, 1.105]）；
    持有窗 (e, e＋H]（型 O (e, e＋H−1]）或 r20 窗內有壞根 ⇒ 該值不定義；基準成員同規則（S）。
 S8 去重 N3（登錄寫死）：同股同類、依 (e, time, serial)，與上一則【保留】事件 e 相差 ≥ 5 個交易日才保留；對母體內事件做、不論有沒有價（同探索材料，S）。
    不去重版 ＝ 只做 §三「同股同日同類去重」（S）。
 S9 段依公告日期：早年 1999-01～2014-12｜探索 2015-01～2020-12｜確認 2021-01～2026-09；月分群依 e 所在曆月（research11.cl_stats，CR0、1.96）。
    e＋H 超出版面最後一日 ⇒ 該 H 不定義（早年 2014-12 底、確認 2026-09 下旬，照報）。
 S10 判（登錄 §四，seq249／253）：有反應 ＝ 探索與確認點估計同號且兩段 95% CI 都不跨 0；穩 ＝ 有反應且早年點估計同號（S：早年只看方向）；
    兩段 CI 都不跨 0 但反號 ⇒「兩段相反」；其餘 ⇒「測不出」。不設最小樣本（n ＜ 30 只標樣本少，S）。另報 Bonferroni（z＝Φ⁻¹(1−0.025/36)）判定變不變（描述）。
    「其他」類照判、照實寫，⛔ 結果句不得推論「其他類沒反應」（裁定 seq302）；注意交易、澄清 ⇒ 標「反應在公告前」。
 S11 另報（描述）：對加權指數（價格指數、不含息；型 O 以前一日收盤代開盤；指數檔止於 2026-09-24）、對 0050（還原、同式）、對全體（同日母體等權）；
    公告前 5 日 ＝ 收(e−1)÷收(e−6)−1（沿用前收）對同式基準②（十分位量到 e−6）；型 C「當天開→收」對同式基準②（＝ 型 O、H＝1 的基準）。
 S12 假訊號（描述、不計 N，S）：每筆保留事件換成同股、同段、同型的隨機一天（default_rng([20261005, H])，最多抽 30 次）算同式 X；36 格同判法，數幾格「有反應」。
 S13 種子：登錄沒有抽樣步驟（CI 為解析式月分群）⇒ 只有 S12 一顆種子。
輸出 backtest/resultsNewsCat/：summary.json、cells.csv、desc.json、check.json、REPORT.md、重大訊息類別反應.html；逐筆檔在 ~/ncwork/（⛔ 不進 repo）
"""
import hashlib
import math
import time
from multiprocessing import Pool
from statistics import NormalDist

from backtest import avgdown as AV
from backtest import research11 as R11

TAG2 = "2026-10-05 08:30（台北）"
REG2 = "PREREG重大訊息類別反應 seq2（台股策略線 sha b48ee3f4f02bf049）｜裁定 seq298（N＝36）、seq302（凍結開算、含早年）"
SEQ2_REF = "/mnt/c/SynologyDrive/跨線信箱/附件-重大訊息分類_seq2_台股策略線-20261005-0809.py"
SEQ2_SHA256 = "e25bd78fe7a7f00b400158568aa9041a9f937b0b07bd57e2b0f0fbc1d9ec7e9e"
# ⭐ 逐字照搬（台股策略線 1005-0809 附件；一個位元組都沒改）；用 exec 載入，免得改名時動到內容
SEQ2_SRC = '''import re
def has(s,ws): return any(w in s for w in ws)
FIN0=["高流動","流動比率","速動比率","負債比率","短期借款","現金收支","融資額度","帳齡","背書保證","資金貸與","淨值低於"]
MERGE_OK=["併購","收購","股份轉換","合資","分割","吸收合併","簡易合併","合併案","合併基準日","合併契約","合併計畫","消滅公司","存續公司","進行合併","決議合併","擬合併","合併後"]
def merge_hit(s):
    return has(s,MERGE_OK)
def classify(s):
    if has(s,["注意交易資訊","交易異常","公布注意","公佈注意"]): return 1
    if has(s,["澄清","媒體報導","報載","新聞報導","報導"]): return 2
    if has(s,FIN0): return 12
    if "減資" in s: return 3
    if merge_hit(s): return 4
    if has(s,["股利","盈餘分配","除息","除權","配息","盈餘轉增資","資本公積轉增資","資本公積配發"]): return 8
    if has(s,["現金增資","增資發行","發行新股","公司債","可轉換","海外存託憑證"]) or ("私募" in s and has(s,["普通股","特別股","公司債","辦理私募","私募案","私募方式","私募發行"]) and "取得" not in s):
        if not has(s,["轉換價格","賣回權","停止轉換","代收價款","存儲專戶","更名"]): return 5
    if (has(s,["得標","訂單","接單"]) or ("簽訂" in s and has(s,["合約","契約","協議"]))) and not has(s,["授信","融資","借款","租賃"]): return 6
    if has(s,["取得","處分","訂購","購置"]) and has(s,["資產","不動產","使用權","設備","有價證券","股權","土地","廠房"]): return 7
    if has(s,["經理人","總經理","董事長","財務主管","會計主管","發言人","稽核主管","研發主管","營運主管","公司治理主管","執行長","副總經理"]) and has(s,["異動","變動","辭任","解任","新任","更換","退休","選任","推選","委任","接任","升任"]): return 10
    if has(s,["法人說明會","法說會","業績說明會","業績發表會","投資人說明會","座談會","投資人會議"]): return 11
    if has(s,["自結","財務報告","財報","營業收入","營收","財務報表","財務資訊","財務資料","業績","自行結算","損益","獲利","營業額","盈餘"]): return 9
    return 12
'''
_NS2: dict = {}
exec(compile(SEQ2_SRC, "附件-重大訊息分類_seq2", "exec"), _NS2)
classify_seq2 = _NS2["classify"]

NEWS2_SHA = "8425186bd20cdef4d39ac039ad2a6eda0903a8bb"          # 2026-10-05 origin/main（news 2015～2020 與探索材料用的 c2e0bf24ae 逐位元組相同）
ND2 = os.path.expanduser(f"~/msdata/{NEWS2_SHA}/data/mops/news")
WD2 = {"early": os.path.expanduser("~/earlydata/eotc_f65bb03e11/otc/data"), "main": os.path.expanduser(f"~/h2data/{NEWS2_SHA}/data")}
TAIEX2 = os.path.expanduser("~/msdata/us_macro/c10a1d00c358760fb8780b79863068eca9341dfc/twse_taiex.csv")
WORK2 = os.path.expanduser("~/ncwork")
OUT2 = "backtest/resultsNewsCat"
YEARS2 = range(1999, 2027)
SEG2 = {"早年": ("1999-01-01", "2014-12-31"), "探索": ("2015-01-01", "2020-12-31"), "確認": ("2021-01-01", "2026-09-30")}
SEGS2 = ("探索", "確認", "早年")
HS2 = (1, 5, 20)
NAMES2 = {1: "注意交易資訊公告", 2: "澄清媒體報導", 3: "減資", 4: "併購／合資", 5: "增資／發債", 6: "得標／接單／合約", 7: "取得或處分資產",
          8: "股利", 9: "自結財報／營收", 10: "經理人異動", 11: "法說會", 12: "其他"}
PRE_CATS = (1, 2)                                                 # 登錄 §三 必註：反應在公告前
SEED2 = 20261005
_G2: dict = {}


def sub3(s: str) -> str:
    if ANY(s, ("現金減資", "退還股款", "彌補虧損")):
        return "現金減資／彌補虧損"
    if ANY(s, ("庫藏股", "註銷", "限制員工", "限制型", "員工權利")):
        return "註銷庫藏股／限制股"
    return "其他減資"


def ensure_news2():
    if all(os.path.exists(os.path.join(ND2, f"{y}.csv")) for y in YEARS2):
        return
    root = os.path.expanduser(f"~/msdata/{NEWS2_SHA}")
    os.makedirs(root, exist_ok=True)
    p = subprocess.run(["git", "archive", "--format=tar", NEWS2_SHA] + [f"data/mops/news/{y}.csv" for y in YEARS2], capture_output=True, check=True)
    subprocess.run(["tar", "-x", "-C", root], input=p.stdout, check=True)


def load_news2():
    ensure_news2()
    N = pd.concat([pd.read_csv(os.path.join(ND2, f"{y}.csv"), dtype=str, keep_default_na=False) for y in YEARS2], ignore_index=True)
    lg = {"原始則數（1999～2026 檔）": int(len(N))}
    N = N.drop_duplicates(["date", "time", "stock_id", "serial"])
    N = N[(N["date"] >= SEG2["早年"][0]) & (N["date"] <= SEG2["確認"][1])]
    lg["公告日 1999-01-01～2026-09-30"] = int(len(N))
    N = N[N["market"].isin(["sii", "otc"])].reset_index(drop=True)
    lg["market∈{sii,otc}"] = int(len(N))
    return N, lg


# ───────────── 每檔載入（worker）─────────────
def _w2_init(data):
    D.DATA = data
    UG.set_gate_v2(True)
    _G2["data"] = data; _G2["cal"] = D.load_calendar()


def _w2_one(args):
    sid, mk = args
    data = _G2["data"]; cal = _G2["cal"]; n = len(cal)
    st = D.load_stock(sid, mk, cal)
    if st is None:
        return sid, None
    df = st.df
    c = df["close"].to_numpy(float); o = df["open"].to_numpy(float)
    idx = np.flatnonzero(np.isfinite(c))
    if len(idx) == 0:
        return sid, None
    bad = np.zeros(n, bool)
    for b in D.breakpoints(df, st.event_dates):
        if b["rule"] in ("price", "price+gap"):
            bad[b["pos"]] = True
    adj = D.load_adj(sid)
    if adj is not None and len(adj):
        raw = pd.read_csv(os.path.join(data, "stocks", sid + ".csv"), dtype={"date": str}, usecols=["date", "close"]).drop_duplicates("date")
        raw.index = pd.to_datetime(raw["date"])
        rc = pd.to_numeric(raw["close"], errors="coerce").reindex(cal).to_numpy(float)
        rcb = rc[idx]; dates = cal[idx]
        for d, f in zip(adj["date"], adj["factor"].astype(float)):
            k = int(dates.searchsorted(d))
            if 0 < k < len(idx) and f > 0 and rcb[k] > 0 and rcb[k - 1] > 0:
                r = rcb[k] / (rcb[k - 1] * f)
                if r < 0.895 or r > 1.105:
                    bad[idx[k]] = True
    pit = UG.pit_valid(sid, cal, data)
    return sid, {"c": c, "o": o, "bad": bad, "pit": pit, "first": int(idx[0]), "last": int(idx[-1])}


def world2(name, procs, log):
    data = WD2[name]
    D.DATA = data
    UG.set_gate_v2(True)
    cal = D.load_calendar(); n = len(cal)
    stocks = pd.read_csv(os.path.join(data, "meta", "stocks.csv"), dtype=str)
    G = UG.gate3(stocks)
    mk = G.set_index("stock_id")["market"].to_dict()
    sids = sorted(G["stock_id"])
    if os.environ.get("NC_SMOKE"):
        sids = sids[:150]
    with Pool(procs, initializer=_w2_init, initargs=(data,)) as pool:
        F = dict(pool.map(_w2_one, [(s, mk[s]) for s in sids], chunksize=16))
    have = sorted(s for s, v in F.items() if v is not None)
    S = len(have)
    C = np.full((n, S), np.nan); O = np.full((n, S), np.nan); BAD = np.zeros((n, S), bool); PIT = np.zeros((n, S), bool)
    FIRST = np.zeros(S, int); LAST = np.zeros(S, int)
    for j, s in enumerate(have):
        v = F[s]; C[:, j] = v["c"]; O[:, j] = v["o"]; BAD[:, j] = v["bad"]; PIT[:, j] = v["pit"]; FIRST[j] = v["first"]; LAST[j] = v["last"]
    del F
    BAR = np.isfinite(C)
    CFF = pd.DataFrame(C).ffill().to_numpy()
    CSB = np.vstack([np.zeros((1, S), np.int32), np.cumsum(BAD, axis=0, dtype=np.int32)])     # (a, b] 壞根數 ＝ CSB[b＋1] − CSB[a＋1]
    R20 = np.full((n, S), np.nan); R20F = np.full((n, S), np.nan); ar = np.arange(n)
    for j in range(S):
        bars = np.flatnonzero(BAR[:, j])
        r = AV.r20_cal(C[:, j], bars)
        if len(bars) > 20:
            a_, b_ = bars[:-20], bars[20:]
            r[b_[(CSB[b_ + 1, j] - CSB[a_ + 1, j]) > 0]] = np.nan
        R20[:, j] = r
        lb = np.maximum.accumulate(np.where(BAR[:, j], ar, -1))
        ok = (lb >= 0) & (ar - lb <= 20)
        R20F[ok, j] = r[lb[ok]]
    # 0050、加權指數（同式另報）
    b0 = D.load_stock("0050", "twse", cal).df
    B0C = np.array(pd.Series(b0["close"].to_numpy(float)).ffill().to_numpy(), dtype=float); B0O = np.array(b0["open"].to_numpy(float), dtype=float)
    tx = pd.read_csv(TAIEX2, dtype={"date": str}); tx.index = pd.to_datetime(tx["date"])
    txs = pd.to_numeric(tx["close"], errors="coerce")
    TX = np.array(txs.reindex(cal).ffill().to_numpy(float), dtype=float)
    TX[cal > txs.index.max()] = np.nan
    log(f"[世界 {name}] {data}｜日曆 {cal[0].date()}～{cal[-1].date()} {n} 日｜gate3 {len(sids):,} 檔、有 K 棒 {S:,} 檔｜壞根 {int(BAD.sum()):,}")
    return {"name": name, "cal": cal, "n": n, "sids": have, "ix": {s: j for j, s in enumerate(have)}, "G": set(sids), "C": C, "O": O, "CFF": CFF,
            "BAR": BAR, "PIT": PIT, "CSB": CSB, "R20": R20, "R20F": R20F, "FIRST": FIRST, "LAST": LAST, "B0C": B0C, "B0O": B0O, "TX": TX,
            "mon": np.array([str(x)[:7] for x in cal])}


def typeR(W, kind, H):
    """型別報酬矩陣與排序鍵：C＝收(t)→收(t＋H)｜O＝開(t)→收(t＋H−1)｜P＝收(t)→收(t＋5)（沿用前收，公告前 5 日用）。"""
    n = W["n"]; C, O, CFF, BAR, CSB = W["C"], W["O"], W["CFF"], W["BAR"], W["CSB"]
    R = np.full(C.shape, np.nan); key = np.full(C.shape, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        if kind == "C":
            t = np.arange(n - H)
            ok = BAR[t] & ((CSB[t + H + 1] - CSB[t + 1]) == 0)
            R[t] = np.where(ok, CFF[t + H] / C[t] - 1.0, np.nan); key = W["R20"]
        elif kind == "O":
            L_ = H - 1; t = np.arange(n - L_)
            ok = BAR[t] & (O[t] > 0) & ((CSB[t + L_ + 1] - CSB[t + 1]) == 0)
            R[t] = np.where(ok, CFF[t + L_] / O[t] - 1.0, np.nan); key[1:] = W["R20F"][:-1]
        else:
            t = np.arange(n - 5)
            ok = (t[:, None] >= W["FIRST"][None, :]) & (t[:, None] + 5 <= W["LAST"][None, :]) & ((CSB[t + 6] - CSB[t + 1]) == 0)
            R[t] = np.where(ok, CFF[t + 5] / CFF[t] - 1.0, np.nan); key = W["R20F"]
    R[~np.isfinite(R)] = np.nan
    return R, key


def base2(W, R, key):
    n, S = R.shape; PIT = W["PIT"]
    DEC = np.full((n, S), -1, np.int8); SS = np.full((n, 10), np.nan); NN = np.zeros((n, 10), np.int64); SA = np.full(n, np.nan); NA = np.zeros(n, np.int64)
    for t in range(n):
        m = PIT[t] & np.isfinite(R[t]) & np.isfinite(key[t])
        k = int(m.sum())
        if k < 20:
            continue
        d = AV.deciles(np.where(m, key[t], np.nan))
        DEC[t] = d
        rr = R[t, m]; dm = d[m]
        SS[t] = np.bincount(dm, weights=rr, minlength=10); NN[t] = np.bincount(dm, minlength=10)
        SA[t] = rr.sum(); NA[t] = k
    return DEC, SS, NN, SA, NA


def evx(R, B, rows, cols):
    """事件 ⇒ (R, 基準②, 對全體)；不是當日成員 ⇒ 基準 NaN。"""
    DEC, SS, NN, SA, NA = B
    r = R[rows, cols]; d = DEC[rows, cols].astype(int); dd = np.maximum(d, 0)
    s = SS[rows, dd]; nn = NN[rows, dd]
    ok = (d >= 0) & np.isfinite(r)
    with np.errstate(invalid="ignore", divide="ignore"):
        base = np.where(ok & (nn > 1), (s - r) / (nn - 1), np.nan)
        ew = np.where(ok & (NA[rows] > 1), (SA[rows] - r) / (NA[rows] - 1), np.nan)
    return r, base, ew


def stat2(x, m, z=1.96):
    x = np.asarray(x, float); ok = np.isfinite(x)
    if ok.sum() == 0:
        return {"n": 0}
    s = R11.cl_stats(x[ok], np.asarray(m)[ok])
    s["lo"] = s["mean"] - z * s["se"]; s["hi"] = s["mean"] + z * s["se"]
    return s


def label2(ex, cf, ea):
    pe = bool(ex.get("n", 0) > 0 and (ex["lo"] > 0 or ex["hi"] < 0))
    pc = bool(cf.get("n", 0) > 0 and (cf["lo"] > 0 or cf["hi"] < 0))
    if pe and pc:
        sg = float(np.sign(ex["mean"]))
        if sg == float(np.sign(cf["mean"])):
            lab = "有反應（" + ("正" if sg > 0 else "負") + "）"
            if ea.get("n", 0) == 0:
                return lab + "；早年無資料", True, False
            return (lab + "＋穩", True, True) if bool(np.sign(ea["mean"]) == sg) else (lab + "；早年反向", True, False)
        return "兩段相反", False, False
    return "測不出", False, False


def run2(a):
    T0 = time.time()
    os.makedirs(OUT2, exist_ok=True); os.makedirs(WORK2, exist_ok=True)
    logf = open(os.path.join(WORK2, "run.log"), "w", encoding="utf-8")

    def log(m):
        m = f"[{time.time() - T0:6.0f}s] {m}"; print(m, flush=True); logf.write(m + "\n"); logf.flush()
    ts = subprocess.run(["bash", "-c", "TZ=Asia/Taipei date '+%F %H:%M'"], capture_output=True, text=True).stdout.strip()
    log(f"===== researchNewsCat run（seq2）{ts}（WSL 時鐘）｜讀法寫死 {TAG2} =====")
    assert hashlib.sha256(SEQ2_SRC.encode("utf-8")).hexdigest() == SEQ2_SHA256, "SEQ2_SRC 不是逐字照搬"
    N, LG = load_news2()
    N["cat"] = [classify_seq2(s) for s in N["subject"]]
    N["flag"] = N["subject"].str.contains("更正|補充", regex=True)
    N["sub3"] = [sub3(s) if c == 3 else "" for s, c in zip(N["subject"], N["cat"])]
    N["seg"] = np.select([N["date"] <= SEG2["早年"][1], N["date"] <= SEG2["探索"][1]], ["早年", "探索"], "確認")
    log(f"[news] {json.dumps(LG, ensure_ascii=False)}")
    WE = world2("early", a.procs, log); WM = world2("main", a.procs, log)
    nE = WE["n"]; CAL = WE["cal"].append(WM["cal"])
    assert CAL.is_monotonic_increasing and CAL.is_unique
    d = pd.to_datetime(N["date"]).values
    p0 = CAL.searchsorted(d, side="left"); nC = len(CAL)
    istd = (p0 < nC) & (CAL[np.minimum(p0, nC - 1)].values == d)
    late = N["time"].str.slice(0, 5).to_numpy() > "13:30"
    N["type"] = np.where(istd & ~late, "C", "O")
    N["epos"] = np.where(istd & ~late, p0, np.where(istd, p0 + 1, p0))
    pre = d < CAL[0].to_datetime64()
    LG["time 不是 HH:MM:SS 的則數"] = int((~N["time"].str.match(r"^\d\d:\d\d:\d\d$")).sum())
    LG["早於日K（1999-01～2004-02-10，sii／otc 全部、未過母體閘）各類則數"] = {NAMES2[c]: int(((N["cat"] == c).to_numpy() & pre).sum()) for c in range(1, 13)}
    N["world"] = np.where(N["epos"].to_numpy() < nE, "early", "main")
    N["le"] = np.where(N["world"] == "early", N["epos"], N["epos"] - nE)
    status = np.array([""] * len(N), dtype=object)
    status[pre] = "早於日K（2004-02-11 前）"
    col = np.full(len(N), -1)
    pitok = np.ones(len(N), bool)
    for W in (WE, WM):
        m = (N["world"].to_numpy() == W["name"]) & ~pre
        sid = N["stock_id"].to_numpy(); le = N["le"].to_numpy()
        inG = np.array([s in W["G"] for s in sid]) & m
        status[m & ~inG] = "不在 GATE_V2 靜態母體"
        cj = np.array([W["ix"].get(s, -1) for s in sid])
        col[m] = cj[m]
        hasf = m & inG & (cj >= 0)
        status[m & inG & (cj < 0)] = "版面無該檔"
        ii = np.flatnonzero(hasf)
        pv = W["PIT"][np.minimum(le[ii], W["n"] - 1), cj[ii]]
        pitok[ii] = pv
        status[ii[~pv]] = "事件日在板期／興櫃列"
    N["status"] = status; N["col"] = col
    popu = (N["status"] == "").to_numpy() | (N["status"] == "版面無該檔").to_numpy()
    LG["早於日K"] = int(pre.sum()); LG["不在 GATE_V2 靜態母體"] = int((N["status"] == "不在 GATE_V2 靜態母體").sum())
    LG["事件日在板期／興櫃列"] = int((N["status"] == "事件日在板期／興櫃列").sum()); LG["母體內則數（2004-02-11 起）"] = int(popu.sum())
    # 去重（N3）與同日同類去重
    N = N[popu].copy()
    N = N.sort_values(["stock_id", "cat", "epos", "time", "serial"]).reset_index(drop=True)
    keep = np.zeros(len(N), bool); last = {}
    for i, (s, c, e) in enumerate(zip(N["stock_id"], N["cat"], N["epos"])):
        k = (s, c)
        if k not in last or e - last[k] >= 5:
            keep[i] = True; last[k] = e
    N["dd"] = keep
    N["nd"] = ~N.duplicated(["stock_id", "cat", "epos"], keep="first")
    # 價可用狀態
    for W in (WE, WM):
        m = (N["world"] == W["name"]).to_numpy() & (N["status"] == "").to_numpy()
        ii = np.flatnonzero(m); le = N["le"].to_numpy()[ii]; cj = N["col"].to_numpy()[ii]; ty = N["type"].to_numpy()[ii]
        st_ = np.array(["保留"] * len(ii), dtype=object)
        st_[le < W["FIRST"][cj]] = "事件日早於該檔第一根K棒"
        st_[le > W["LAST"][cj]] = "事件日晚於該檔最後一根K棒（已下市）"
        okr = st_ == "保留"
        nob = okr & ~W["BAR"][np.minimum(le, W["n"] - 1), cj]
        st_[nob] = "基準日停牌（無成交）"
        boo = (st_ == "保留") & (ty == "O") & ~(W["O"][np.minimum(le, W["n"] - 1), cj] > 0)
        st_[boo] = "基準日開盤無效"
        sv = N["status"].to_numpy(); sv[ii] = st_; N["status"] = sv
    N.loc[N["status"] == "", "status"] = "版面無該檔"
    log(f"[事件] 母體內 {len(N):,} 則；去重 {int(N['dd'].sum()):,}；狀態 {N['status'].value_counts().to_dict()}")
    # 報酬
    VCOLS = [f"{p}{H}" for H in HS2 for p in ("R", "X", "vsEW", "vsTX", "vs0050_", "F")] + ["OC", "PRE5"]
    for c_ in VCOLS:
        N[c_] = np.nan
    N["mon"] = ""
    rng = {H: np.random.default_rng([SEED2, H]) for H in HS2}
    for W in (WE, WM):
        m = (N["world"] == W["name"]).to_numpy() & (N["status"] == "保留").to_numpy()
        ii = np.flatnonzero(m); le = N["le"].to_numpy()[ii]; cj = N["col"].to_numpy()[ii]; ty = N["type"].to_numpy()[ii]
        segv = N["seg"].to_numpy()[ii]
        mon = N["mon"].to_numpy(); mon[ii] = W["mon"][le]; N["mon"] = mon
        n = W["n"]
        for H in HS2:
            for kind in ("C", "O"):
                R, key = typeR(W, kind, H); B = base2(W, R, key)
                sel = ty == kind; rows = le[sel]; cols = cj[sel]; gi = ii[sel]
                r, base, ew = evx(R, B, rows, cols)
                N.loc[gi, f"R{H}"] = r; N.loc[gi, f"X{H}"] = r - base; N.loc[gi, f"vsEW{H}"] = r - ew
                with np.errstate(invalid="ignore", divide="ignore"):
                    if kind == "C":
                        e2 = np.minimum(rows + H, n - 1); okh = rows + H < n
                        tx = np.where(okh, W["TX"][e2] / W["TX"][rows] - 1.0, np.nan); b5 = np.where(okh, W["B0C"][e2] / W["B0C"][rows] - 1.0, np.nan)
                    else:
                        e2 = np.minimum(rows + H - 1, n - 1); okh = rows + H - 1 < n
                        tx = np.where(okh & (rows >= 1), W["TX"][e2] / W["TX"][np.maximum(rows - 1, 0)] - 1.0, np.nan)
                        b5 = np.where(okh, W["B0C"][e2] / W["B0O"][rows] - 1.0, np.nan)
                N.loc[gi, f"vsTX{H}"] = r - tx; N.loc[gi, f"vs0050_{H}"] = r - b5
                if kind == "O" and H == 1:                      # 型 C 事件「當天開→收」＝ 型 O、H＝1 的同式基準
                    sc = ty == "C"
                    r1, b1, _ = evx(R, B, le[sc], cj[sc]); N.loc[ii[sc], "OC"] = r1 - b1
                # 假訊號：同股、同段、同型的隨機一天
                DEC = B[0]; NN = B[2]
                fx = np.full(len(rows), np.nan)
                xs = (r - base)
                for sg in ("早年", "探索", "確認"):
                    a0, a1 = W["cal"].searchsorted(pd.Timestamp(SEG2[sg][0])), W["cal"].searchsorted(pd.Timestamp(SEG2[sg][1]), side="right") - 1
                    q = np.flatnonzero((segv[sel] == sg) & np.isfinite(xs))
                    if len(q) == 0 or a1 < a0:
                        continue
                    cand = rng[H].integers(a0, a1 + 1, size=(len(q), 30))
                    cq = cols[q][:, None]
                    dv = DEC[cand, cq].astype(int)
                    good = (dv >= 0) & (NN[cand, np.maximum(dv, 0)] > 1) & np.isfinite(R[cand, cq])
                    first = np.where(good.any(axis=1), good.argmax(axis=1), -1)
                    ok = first >= 0
                    tt = cand[ok, first[ok]]
                    rr, bb, _ = evx(R, B, tt, cols[q][ok])
                    tmp = np.full(len(q), np.nan); tmp[ok] = rr - bb; fx[q] = tmp
                N.loc[gi, f"F{H}"] = fx
                del R, key, B
            log(f"[{W['name']}] H{H} 完")
        R, key = typeR(W, "P", 5); B = base2(W, R, key)
        okp = le >= 6
        rp, bp, _ = evx(R, B, np.maximum(le - 6, 0), cj)
        N.loc[ii, "PRE5"] = np.where(okp, rp - bp, np.nan)
        del R, key, B
        log(f"[{W['name']}] 公告前 5 日 完")
    keepcols = ["date", "time", "stock_id", "serial", "subject", "cat", "flag", "sub3", "seg", "type", "epos", "world", "le", "col", "status", "dd", "nd", "mon"] + VCOLS
    N[keepcols].to_pickle(os.path.join(WORK2, "events.pkl"))
    log("[存檔] ~/ncwork/events.pkl")
    S = summarize2(N, LG, ts)
    S["耗時s"] = round(time.time() - T0)
    json.dump(S, open(os.path.join(OUT2, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    log(f"[完] {time.time() - T0:.0f}s")


def cells2(N, ver):
    """ver ∈ 去重／不去重／假訊號 ⇒ 每段每類每 H 的統計列。"""
    K = N[(N["status"] == "保留") & (N["dd"] if ver != "不去重" else N["nd"])]
    rows = []
    z36 = NormalDist().inv_cdf(1 - 0.025 / 36)
    for sg in SEGS2:
        ks = K[K["seg"] == sg]
        for c in range(1, 13):
            g = ks[ks["cat"] == c]
            for H in HS2:
                col_ = f"F{H}" if ver == "假訊號" else f"X{H}"
                s = stat2(g[col_].to_numpy(float), g["mon"].to_numpy())
                r = {"版本": ver, "段": sg, "cat": c, "類別": NAMES2[c], "H": H, "n": s.get("n", 0), "月數": s.get("months", 0),
                     "X平均": s.get("mean"), "X中位": s.get("median"), "勝率": s.get("win"), "se": s.get("se"), "lo": s.get("lo"), "hi": s.get("hi")}
                if s.get("n", 0):
                    r["lo_bonf"] = s["mean"] - z36 * s["se"]; r["hi_bonf"] = s["mean"] + z36 * s["se"]
                if ver == "去重":
                    for p in ("R", "vsEW", "vsTX", "vs0050_"):
                        cc = f"{p}{H}"
                        r[cc.rstrip("_") if p != "vs0050_" else f"vs0050_{H}"] = float(np.nanmean(g[cc])) if len(g) and np.isfinite(g[cc]).any() else np.nan
                rows.append(r)
    return pd.DataFrame(rows)


def judge2(C):
    """36 格標籤（登錄 §四）＋ Bonferroni 版（描述）。"""
    J = {}
    for c in range(1, 13):
        for H in HS2:
            g = {sg: C[(C["段"] == sg) & (C["cat"] == c) & (C["H"] == H)].iloc[0].to_dict() for sg in SEGS2}
            st = {sg: ({"n": int(v["n"]), "mean": v["X平均"], "lo": v["lo"], "hi": v["hi"]} if v["n"] else {"n": 0}) for sg, v in g.items()}
            lab, react, stable = label2(st["探索"], st["確認"], st["早年"])
            sb = {sg: ({"n": int(v["n"]), "mean": v["X平均"], "lo": v.get("lo_bonf"), "hi": v.get("hi_bonf")} if v["n"] else {"n": 0}) for sg, v in g.items()}
            labb, reactb, _ = label2(sb["探索"], sb["確認"], sb["早年"])
            J[f"{c}_H{H}"] = {"cat": c, "類別": NAMES2[c], "H": H, "標籤": lab, "有反應": react, "穩": stable,
                              "反應在公告前": c in PRE_CATS, "Bonferroni 標籤": labb,
                              **{f"{sg}_n": st[sg]["n"] for sg in SEGS2},
                              **{f"{sg}_X": st[sg].get("mean") for sg in SEGS2}, **{f"{sg}_lo": st[sg].get("lo") for sg in SEGS2},
                              **{f"{sg}_hi": st[sg].get("hi") for sg in SEGS2},
                              "樣本少": "、".join(sg for sg in SEGS2 if st[sg]["n"] < 30)}
    return J


def summarize2(N, LG, ts):
    C = pd.concat([cells2(N, v) for v in ("去重", "不去重", "假訊號")], ignore_index=True)
    C.to_csv(os.path.join(OUT2, "cells.csv"), index=False, float_format="%.6g", encoding="utf-8-sig")
    J = judge2(C[C["版本"] == "去重"])
    JF = judge2(C[C["版本"] == "假訊號"].assign(版本="去重"))
    JN = judge2(C[C["版本"] == "不去重"].assign(版本="去重"))
    seg_pass = {}
    for sg in SEGS2:
        x = C[(C["版本"] == "去重") & (C["段"] == sg)]
        seg_pass[sg] = {"CI 不跨 0（正）": int((x["lo"] > 0).sum()), "CI 不跨 0（負）": int((x["hi"] < 0).sum()), "可算格": int((x["n"] > 1).sum())}
    react_cats = sorted({v["cat"] for v in J.values() if v["有反應"]})
    lab = lambda c, H: J[f"{c}_H{H}"]["標籤"]
    K = N[(N["status"] == "保留") & N["dd"]]
    pre1 = {sg: stat2(K[(K["seg"] == sg) & (K["cat"] == 1)]["PRE5"], K[(K["seg"] == sg) & (K["cat"] == 1)]["mon"]) for sg in ("探索", "確認")}
    pri = {
        "① 有反應的類 ≤ 3 類": {"中": len(react_cats) <= 3, "有反應的類": [NAMES2[c] for c in react_cats]},
        "② 注意交易：公告前 5 日大漲、公告後 5／20 日偏弱": {
            "中": bool(all(pre1[sg].get("n", 0) and pre1[sg]["lo"] > 0 for sg in pre1) and lab(1, 5).startswith("有反應（負）") and lab(1, 20).startswith("有反應（負）")),
            "公告前 5 日 X（探索／確認）": [pre1[sg].get("mean") for sg in pre1], "H5": lab(1, 5), "H20": lab(1, 20),
            "讀法（S）": "前 5 日兩段 CI 下緣 ＞ 0，且 H5、H20 都是「有反應（負）」才算中"},
        "③ 法說會、經理人異動：測不出": {"中": all(lab(c, H) == "測不出" for c in (10, 11) for H in HS2),
                                 "標籤": {f"{NAMES2[c]} H{H}": lab(c, H) for c in (10, 11) for H in HS2}},
        "④ 得標／接單／合約：H1 偏正、H20 測不出": {"中": lab(6, 1).startswith("有反應（正）") and lab(6, 20) == "測不出", "H1": lab(6, 1), "H20": lab(6, 20)},
        "⑤ 增資／發債：H20 偏負": {"中": lab(5, 20).startswith("有反應（負）"), "H20": lab(5, 20)},
    }
    for v in pri.values():
        v["中"] = bool(v["中"])
    desc = describe2(N, C)
    S = {"登錄": REG2, "讀法寫死": TAG2, "執行時間": f"{ts}（WSL 時鐘）", "GATE_V2": True, "N": 36,
         "資料": {"news": f"main {NEWS2_SHA}", "主快照": WD2["main"], "早年版面": WD2["early"], "加權指數": TAIEX2, "母體步驟": LG},
         "判定": J, "標籤彙總": {k: int(v) for k, v in pd.Series([v["標籤"] for v in J.values()]).value_counts().items()},
         "有反應格數": int(sum(v["有反應"] for v in J.values())), "穩格數": int(sum(v["穩"] for v in J.values())),
         "有反應的類": [NAMES2[c] for c in react_cats], "各段 CI 不跨 0 格數（去重主版、36 格中）": seg_pass,
         "Bonferroni 版有反應格數（描述）": int(sum(v["Bonferroni 標籤"].startswith("有反應") for v in J.values())),
         "不去重版有反應格數（描述）": int(sum(v["有反應"] for v in JN.values())),
         "不去重版標籤（描述）": {k: v["標籤"] for k, v in JN.items()},
         "假訊號有反應格數（描述，36 格中）": int(sum(v["有反應"] for v in JF.values())),
         "假訊號標籤（描述）": {k: v["標籤"] for k, v in JF.items() if v["標籤"] != "測不出"},
         "先驗（登錄 §五）": pri}
    json.dump(desc, open(os.path.join(OUT2, "desc.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    return S


def describe2(N, C):
    K = N[(N["status"] == "保留") & N["dd"]]
    out = {}
    cnt = {}
    for sg in SEGS2:
        a = N[N["seg"] == sg]
        cnt[sg] = {NAMES2[c]: {"母體內": int((a["cat"] == c).sum()), "去重後": int(((a["cat"] == c) & a["dd"]).sum()),
                               "去重且有價": int(((a["cat"] == c) & a["dd"] & (a["status"] == "保留")).sum()),
                               "去重有價且 X20 可算": int(((a["cat"] == c) & a["dd"] & np.isfinite(a["X20"])).sum())} for c in range(1, 13)}
        tot = int(a["dd"].sum()); oth = int((a["dd"] & (a["cat"] == 12)).sum())
        cnt[sg]["「其他」占去重後"] = oth / tot if tot else None
        cnt[sg]["「其他」占母體內（未去重）"] = float((a["cat"] == 12).mean()) if len(a) else None
    out["各段各類則數"] = cnt
    out["去重事件狀態（各段）"] = {sg: N[(N["seg"] == sg) & N["dd"]]["status"].value_counts().to_dict() for sg in SEGS2}
    out["基準日停牌占比（去重、各類、全期）"] = {NAMES2[c]: float((N[(N["cat"] == c) & N["dd"]]["status"] == "基準日停牌（無成交）").mean()) for c in range(1, 13)}
    out["型 O（13:30 後或非交易日）占比（去重有價）"] = {NAMES2[c]: float((K[K["cat"] == c]["type"] == "O").mean()) for c in range(1, 13)}
    out["更正／補充旗標占比（去重有價）"] = {NAMES2[c]: float(K[K["cat"] == c]["flag"].mean()) for c in range(1, 13)}
    pre = {}; oc = {}
    for sg in SEGS2:
        ks = K[K["seg"] == sg]
        for c in range(1, 13):
            g = ks[ks["cat"] == c]
            s = stat2(g["PRE5"], g["mon"]); pre[f"{sg}|{NAMES2[c]}"] = {k: s.get(k) for k in ("n", "mean", "lo", "hi", "win")}
            gc = g[g["type"] == "C"]
            s = stat2(gc["OC"], gc["mon"]); oc[f"{sg}|{NAMES2[c]}"] = {k: s.get(k) for k in ("n", "mean", "lo", "hi")}
    out["公告前 5 日 X（對同式基準②）"] = pre
    out["型 C 當天開→收 X（對同式基準②）"] = oc
    rd = {}
    for sg in SEGS2:
        g3 = K[(K["seg"] == sg) & (K["cat"] == 3)]
        for sb in ("現金減資／彌補虧損", "註銷庫藏股／限制股", "其他減資"):
            g = g3[g3["sub3"] == sb]
            for H in HS2:
                s = stat2(g[f"X{H}"], g["mon"]); rd[f"{sg}|{sb}|H{H}"] = {k: s.get(k) for k in ("n", "mean", "lo", "hi")}
    out["減資分項（描述、不計 N）"] = rd
    # 重疊率：同股同日（e）跨類
    g = K.groupby(["stock_id", "epos"])["cat"].nunique()
    multi = set(g[g >= 2].index)
    kk = list(zip(K["stock_id"], K["epos"]))
    inm = np.array([x in multi for x in kk])
    out["跨類重疊率"] = {"同股同日有 ≥2 類的股日占比": float((g >= 2).mean()),
                     "各類事件與他類同股同日的比例": {NAMES2[c]: float(inm[(K["cat"] == c).to_numpy()].mean()) for c in range(1, 13)}}
    Nd = N[N["dd"]]
    yr = Nd.groupby([Nd["date"].str[:4], "cat"]).size().unstack(fill_value=0)
    out["每年去重事件數（母體內、2004-02-11 起）"] = {y: {NAMES2[int(c)]: int(v) for c, v in r.items()} for y, r in yr.iterrows()}
    return out


# ═════════════ 網頁與 REPORT ═════════════
def _p2(x, d=2):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—"
    return "—" if not np.isfinite(x) else f"{x * 100:+.{d}f}%"


CSS2 = """<style>:root{--fg:#1f2328;--bg:#fff;--mut:#656d76;--line:#d0d7de;--box:#f3f6fa;--ok:#1a7f37;--bad:#cf222e;--warn:#9a6700}
@media(prefers-color-scheme:dark){:root{--fg:#e6edf3;--bg:#0d1117;--mut:#8d96a0;--line:#30363d;--box:#161b22;--ok:#3fb950;--bad:#f85149;--warn:#d29922}}
body{font-family:-apple-system,'Noto Sans TC','PingFang TC',sans-serif;margin:0 auto;max-width:820px;padding:0 16px 48px;line-height:1.65;color:var(--fg);background:var(--bg)}
h1{font-size:1.35em;margin:.8em 0 .3em}h2{font-size:1.1em;margin-top:1.8em;border-bottom:1px solid var(--line);padding-bottom:.2em}
.box{background:var(--box);border-left:4px solid var(--ok);padding:10px 14px;margin:14px 0}.box.w{border-left-color:var(--warn)}
.wrap{overflow-x:auto}table{border-collapse:collapse;font-size:.84em;min-width:100%}td,th{border:1px solid var(--line);padding:3px 6px;text-align:right;white-space:nowrap}
td.l,th.l{text-align:left}.pos{color:var(--ok);font-weight:600}.neg{color:var(--bad);font-weight:600}.note{color:var(--mut);font-size:.86em}</style>"""


def page2():
    S = json.load(open(os.path.join(OUT2, "summary.json"), encoding="utf-8"))
    Dd = json.load(open(os.path.join(OUT2, "desc.json"), encoding="utf-8"))
    C = pd.read_csv(os.path.join(OUT2, "cells.csv"))
    ck = json.load(open(os.path.join(OUT2, "check.json"), encoding="utf-8")) if os.path.exists(os.path.join(OUT2, "check.json")) else {}
    J = S["判定"]
    react = [v for v in J.values() if v["有反應"]]

    def lcls(lab):
        return "pos" if "（正）" in lab else ("neg" if "（負）" in lab else "")
    head = (f"36 格（12 類 × 1／5／20 天）中，<b>{S['有反應格數']} 格「有反應」</b>（探索、確認兩段同向且 95% 區間都不含 0），其中 {S['穩格數']} 格早年也同向（穩）；"
            f"涉及 {len(S['有反應的類'])} 類：{'、'.join(S['有反應的類']) if S['有反應的類'] else '無'}。其餘 {36 - S['有反應格數']} 格未達「有反應」"
            f"（{'、'.join(f'{k} {v} 格' for k, v in S['標籤彙總'].items() if not k.startswith('有反應'))}）。")
    H = ["<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
         "<title>重大訊息類別反應</title>", CSS2, "</head><body>", "<h1>重大訊息類別反應：公告後股價有沒有反應</h1>",
         f"<div class='box'><b>結論</b>：{head}<br>比較對象＝同一天、前 20 日漲跌幅同十分位的其他股票（基準②）。這是全部公告平均起來的結果，"
         "只用來校準 LINE「這類公告過去平均有／沒有反應」的寫法，⛔ 不是選股或買賣規則，也不是對某一檔的預測。</div>",
         "<div class='box w'>⚠ 讀之前：① 只有公告標題、沒有內文與金額，結果不能拿來說「大單／金額大才有效」。② 「注意交易資訊公告」「澄清媒體報導」是股價先動才發的公告，"
         f"反應在公告前，⛔ 不能讀成公告造成。③ 「其他」是最大一類（未去重占 {min(Dd['各段各類則數'][g]['「其他」占母體內（未去重）'] for g in SEGS2):.0%}～{max(Dd['各段各類則數'][g]['「其他」占母體內（未去重）'] for g in SEGS2):.0%}、"
         f"去重後 {min(Dd['各段各類則數'][g]['「其他」占去重後'] for g in SEGS2):.0%}～{max(Dd['各段各類則數'][g]['「其他」占去重後'] for g in SEGS2):.0%}），它是很多種公告混在一起，⛔ 不能從結果推論「其他類沒反應」。"
         "④ 早年段登錄寫 1999 起，但本專案日 K 從 2004-02-11 起，早年實際是 2004-02～2014-12；上櫃 2007-07 前沒收。</div>"]
    H.append("<h2>36 格判定（主版：同股同類 5 個交易日內只取第一則）</h2><div class='wrap'><table><tr><th class='l'>類別</th><th>H</th><th class='l'>標籤</th>"
             "<th>探索 X（95%）</th><th>確認 X（95%）</th><th>早年 X</th><th>事件數 探／確／早</th></tr>")
    for v in J.values():
        lab = v["標籤"] + ("｜反應在公告前" if v["反應在公告前"] else "")
        H.append(f"<tr><td class='l'>{v['類別']}</td><td>{v['H']}</td><td class='l {lcls(v['標籤'])}'>{lab}</td>"
                 f"<td>{_p2(v['探索_X'])}（{_p2(v['探索_lo'])}～{_p2(v['探索_hi'])}）</td><td>{_p2(v['確認_X'])}（{_p2(v['確認_lo'])}～{_p2(v['確認_hi'])}）</td>"
                 f"<td>{_p2(v['早年_X'])}</td><td>{v['探索_n']:,}／{v['確認_n']:,}／{v['早年_n']:,}</td></tr>")
    H.append("</table></div><p class='note'>X ＝ 該股報酬 − 同日同十分位其他股票平均報酬。13:30（含）前公告：當天收盤起算；13:30 後或假日：次一交易日開盤起算；"
             "H ＝ 從公告日往後數的交易日數。月分群 95% 區間。</p>")
    sp = S["各段 CI 不跨 0 格數（去重主版、36 格中）"]
    H.append("<h2>各段：36 格中 95% 區間不含 0 的格數</h2><div class='wrap'><table><tr><th class='l'>段</th><th>偏正</th><th>偏負</th><th>可算格</th></tr>"
             + "".join(f"<tr><td class='l'>{sg}</td><td>{v['CI 不跨 0（正）']}</td><td>{v['CI 不跨 0（負）']}</td><td>{v['可算格']}</td></tr>" for sg, v in sp.items())
             + "</table></div>")
    H.append(f"<p class='note'>對照（描述、不判）：同一批事件換成同股隨機一天（假訊號）⇒ {S['假訊號有反應格數（描述，36 格中）']} 格「有反應」；"
             f"多重檢定 Bonferroni（36 格）⇒ {S['Bonferroni 版有反應格數（描述）']} 格；不去重版 ⇒ {S['不去重版有反應格數（描述）']} 格。</p>")
    # 有反應格的另報
    if react:
        H.append("<h2>有反應的格：換別的比較對象（描述）</h2><div class='wrap'><table><tr><th class='l'>類別／H</th><th class='l'>段</th><th>X 中位</th><th>勝率</th><th>對加權</th><th>對 0050</th><th>對全體</th></tr>")
        for v in react:
            hh = v["H"]
            for sg in ("探索", "確認"):
                r = C[(C["版本"] == "去重") & (C["段"] == sg) & (C["cat"] == v["cat"]) & (C["H"] == hh)].iloc[0]
                H.append(f"<tr><td class='l'>{v['類別']} H{hh}</td><td class='l'>{sg}</td><td>{_p2(r['X中位'])}</td><td>{float(r['勝率']):.0%}</td>"
                         f"<td>{_p2(r['vsTX' + str(hh)])}</td><td>{_p2(r['vs0050_' + str(hh)])}</td><td>{_p2(r['vsEW' + str(hh)])}</td></tr>")
        H.append("</table></div>")
    pre = Dd["公告前 5 日 X（對同式基準②）"]
    H.append("<h2>公告前 5 個交易日（描述：是不是股價先動才公告）</h2><div class='wrap'><table><tr><th class='l'>類別</th><th>探索</th><th>確認</th><th>早年</th></tr>")
    for c in range(1, 13):
        nm = NAMES2[c]
        H.append(f"<tr><td class='l'>{nm}</td>" + "".join(f"<td>{_p2(pre[f'{sg}|{nm}']['mean'])}（{_p2(pre[f'{sg}|{nm}']['lo'])}～{_p2(pre[f'{sg}|{nm}']['hi'])}）</td>" for sg in SEGS2) + "</tr>")
    H.append("</table></div>")
    cnt = Dd["各段各類則數"]
    H.append("<h2>事件數（去重後；「其他」照實列）</h2><div class='wrap'><table><tr><th class='l'>類別</th><th>探索</th><th>確認</th><th>早年</th></tr>")
    for c in range(1, 13):
        nm = NAMES2[c]
        H.append(f"<tr><td class='l'>{nm}</td>" + "".join(f"<td>{cnt[sg][nm]['去重後']:,}</td>" for sg in SEGS2) + "</tr>")
    H.append("<tr><td class='l'>「其他」占比（去重後）</td>" + "".join(f"<td>{cnt[sg]['「其他」占去重後']:.1%}</td>" for sg in SEGS2) + "</tr>")
    H.append("<tr><td class='l'>「其他」占比（未去重）</td>" + "".join(f"<td>{cnt[sg]['「其他」占母體內（未去重）']:.1%}</td>" for sg in SEGS2) + "</tr></table></div>")
    H.append(f"<p class='note'>假訊號（同股隨機日）有反應的格：{json.dumps(S['假訊號標籤（描述）'], ensure_ascii=False)}——這些格的比較基準本身就有偏，讀那一類時要打折。</p>")
    rd = Dd["減資分項（描述、不計 N）"]
    H.append("<h2>減資類內分項（描述、不判、不計 N）</h2><div class='wrap'><table><tr><th class='l'>分項</th><th>H</th><th>探索</th><th>確認</th><th>早年</th></tr>")
    for sb in ("現金減資／彌補虧損", "註銷庫藏股／限制股", "其他減資"):
        for Hh in HS2:
            H.append(f"<tr><td class='l'>{sb}</td><td>{Hh}</td>" + "".join(
                f"<td>{_p2(rd[f'{sg}|{sb}|H{Hh}']['mean'])}（n {rd[f'{sg}|{sb}|H{Hh}']['n'] or 0:,}）</td>" for sg in SEGS2) + "</tr>")
    H.append("</table></div>")
    pri = S["先驗（登錄 §五）"]
    H.append("<h2>台股策略線事前押的先驗（登錄 §五）</h2><ul>" + "".join(f"<li>{k}：{'中' if v['中'] else '沒中'}</li>" for k, v in pri.items()) + "</ul>")
    ov = Dd["跨類重疊率"]
    H.append(f"<h2>做法與限制</h2><ul><li>資料：公開資訊觀測站重大訊息標題（資料庫 main {NEWS2_SHA[:10]}），上市＋上櫃，含已下市；母體閘新口徑（GATE_V2）；分類照台股策略線 seq2 程式逐字。</li>"
             "<li>同股同類 5 個交易日內只算第一則；同股同日不同類各算一次，跨類重疊（同股同日有 ≥2 類）的股日占 "
             f"{ov['同股同日有 ≥2 類的股日占比']:.1%}。</li><li>停牌中公告、找不到基準價的事件剔除；收盤停牌沿用前收；硬斷點落在持有期內剔除。</li>"
             "<li>早年段：2004-02-11 起才有日 K；上櫃 2007-07～12 除權息未還原、上櫃減資 2007～2012 為偵測非官方；2005～2007-06 只有上市。</li>"
             f"<li>查核：{ck.get('結論', '（未跑）')}</li><li>出處：backtest/researchNewsCat.py（run／--check／page）、resultsNewsCat/（summary.json、cells.csv、desc.json、check.json、REPORT.md）</li></ul></body></html>")
    open(os.path.join(OUT2, "重大訊息類別反應.html"), "w", encoding="utf-8").write("\n".join(H))
    report2(S, Dd, C, ck)
    print("ok")


def report2(S, Dd, C, ck):
    J = S["判定"]
    L = ["# PREREG重大訊息類別反應 seq2：公告後股價反應（含早年段）", "",
         f"**登錄**：{S['登錄']}｜**讀法寫死**：{S['讀法寫死']}｜**執行**：{S['執行時間']}｜GATE_V2 開｜N＝36", "",
         "## 結論", "",
         f"- 36 格中 **{S['有反應格數']} 格有反應**（探索、確認同向且兩段月分群 95% CI 都不跨 0），其中 **{S['穩格數']} 格穩**（早年同向）。",
         f"- 有反應的類：{'、'.join(S['有反應的類']) if S['有反應的類'] else '無'}。",
         f"- 標籤彙總：{json.dumps(S['標籤彙總'], ensure_ascii=False)}",
         f"- 描述對照：假訊號（同股隨機日）{S['假訊號有反應格數（描述，36 格中）']} 格 {json.dumps(S['假訊號標籤（描述）'], ensure_ascii=False)}｜Bonferroni {S['Bonferroni 版有反應格數（描述）']} 格｜不去重版 {S['不去重版有反應格數（描述）']} 格。",
         "- ⚠ 注意交易資訊公告、澄清媒體報導 ⇒ 反應在公告前，⛔ 不讀成公告造成；只有標題沒有金額；「其他」占多數，⛔ 不得推論「其他類沒反應」。", "",
         "## 36 格", "", "| 類別 | H | 標籤 | 探索 X（95%） | 確認 X（95%） | 早年 X | n 探／確／早 | Bonferroni |", "|---|---|---|---|---|---|---|---|"]
    for v in J.values():
        L.append(f"| {v['類別']} | {v['H']} | {v['標籤']}{'｜反應在公告前' if v['反應在公告前'] else ''} | {_p2(v['探索_X'])}（{_p2(v['探索_lo'])}～{_p2(v['探索_hi'])}） | "
                 f"{_p2(v['確認_X'])}（{_p2(v['確認_lo'])}～{_p2(v['確認_hi'])}） | {_p2(v['早年_X'])} | {v['探索_n']:,}／{v['確認_n']:,}／{v['早年_n']:,} | {v['Bonferroni 標籤']} |")
    L += ["", "## 各段 CI 不跨 0 格數（36 格中）", ""] + [f"- {sg}：偏正 {v['CI 不跨 0（正）']}、偏負 {v['CI 不跨 0（負）']}（可算 {v['可算格']}）" for sg, v in S["各段 CI 不跨 0 格數（去重主版、36 格中）"].items()]
    L += ["", "## 先驗（登錄 §五）", ""] + [f"- {k}：{'中' if v['中'] else '沒中'}　{json.dumps({kk: vv for kk, vv in v.items() if kk != '中'}, ensure_ascii=False, default=str)}" for k, v in S["先驗（登錄 §五）"].items()]
    L += ["", "## 偏離登錄與限制（照實寫）", "",
          "- 早年段登錄 1999-01～2014-12；本專案日 K 從 2004-02-11 起 ⇒ 1999-01～2004-02-10 的公告只計則數、不算報酬（各類則數見 summary.json 資料→母體步驟）；"
          "早年版面上櫃 2007-07 前未收（那段只有上市）、上櫃 2007-07～12 除權息未還原、上櫃減資 2007～2012 為偵測非官方。",
          "- 前 20 日報酬要 20 根有效 K 棒 ⇒ 各版面開頭約 20 個交易日（2004-02～03、2015-01～02）基準② 不可算、該段事件不定義；e＋H 超出版面最後一日 ⇒ 不定義（2014-12 底、2026-09 下旬）。",
          "- 對加權指數：價格指數不含息、沒有開盤價（型 O 以前一日收盤代）、指數檔止於 2026-09-24。",
          "- 基準日停牌（停牌中公告且基準日無成交）⇒ 沒有基準價、剔除（各類占比見 desc.json）。",
          "- 種子：登錄無抽樣；只有假訊號一顆種子（20261005＋H），未減。"]
    L += ["", "## 母體與資料", "", "```", json.dumps(S["資料"], ensure_ascii=False, indent=1), "```", "",
          "## 執行者補讀法（S1～S13，全文見 researchNewsCat.py 的 RUN_DOC）", "", "```", RUN_DOC.strip(), "```", "",
          f"## 查核", "", f"- {ck.get('結論', '（未跑）')}", f"- 指令：`python -m backtest.researchNewsCat --check`", "",
          "## 檔案", "", "- summary.json（36 格判定、先驗、各段格數）、cells.csv（去重／不去重／假訊號 × 3 段 × 12 類 × 3 H）、desc.json（公告前 5 日、當天開→收、減資分項、重疊率、狀態）、check.json、重大訊息類別反應.html",
          "- 逐筆檔 ~/ncwork/events.pkl（⛔ 不進 repo）"]
    open(os.path.join(OUT2, "REPORT.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


# ═════════════ 查核（⛔ 不呼叫 world2／typeR／base2／evx／cells2）═════════════
def _ck_stock(data, sid, cal):
    """原始 CSV ⇒ 還原收、開（自算因子連乘）、有成交、壞根（自寫）。"""
    p = os.path.join(data, "stocks", sid + ".csv")
    if not os.path.exists(p):
        return None
    raw = pd.read_csv(p, dtype={"date": str}, usecols=["date", "open", "high", "low", "close", "volume"]).drop_duplicates("date")
    raw.index = pd.to_datetime(raw["date"]); raw = raw.sort_index()
    for k in ("open", "high", "low", "close"):
        raw[k] = pd.to_numeric(raw[k], errors="coerce")
    badp = (raw[["open", "high", "low", "close"]] <= 0).any(axis=1)
    raw.loc[badp, ["open", "high", "low", "close"]] = np.nan
    ap = os.path.join(data, "adj", sid + ".csv")
    evd = []
    F = np.ones(len(raw))
    if os.path.exists(ap):
        ad = pd.read_csv(ap, dtype={"date": str}); ad["date"] = pd.to_datetime(ad["date"])
        for dd_, f in zip(ad["date"], ad["factor"].astype(float)):
            F[raw.index < dd_] *= f
            evd.append((dd_, f))
    rc = raw["close"].to_numpy(float)
    c = (raw["close"] * F).reindex(cal).to_numpy(float); o = (raw["open"] * F).reindex(cal).to_numpy(float)
    rcc = pd.Series(rc, index=raw.index).reindex(cal).to_numpy(float)
    bars = np.flatnonzero(np.isfinite(c)); bad = np.zeros(len(cal), bool)
    for k in range(1, len(bars)):
        p_, t_ = bars[k - 1], bars[k]
        q = c[t_] / c[p_]
        if (q <= 0.55 or q >= 1.8) and not any(cal[p_] < x <= cal[t_] for x, _ in evd):
            bad[t_] = True
    for x, f in evd:
        k = int(np.searchsorted(cal[bars], x))
        if 0 < k < len(bars) and f > 0 and rcc[bars[k]] > 0 and rcc[bars[k - 1]] > 0:
            r = rcc[bars[k]] / (rcc[bars[k - 1]] * f)
            if r < 0.895 or r > 1.105:
                bad[bars[k]] = True
    return c, o, bars, bad


def _ck_r20(c, bars, bad, t, asof):
    """t 的前 20 根有效 K 棒報酬；asof ⇒ 用 t 以前（含）最後一根、最多舊 20 日。"""
    k = int(np.searchsorted(bars, t, side="right")) - 1
    if k < 0 or (not asof and bars[k] != t) or (asof and t - bars[k] > 20) or k < 20:
        return np.nan
    a_, b_ = bars[k - 20], bars[k]
    if bad[a_ + 1:b_ + 1].any():
        return np.nan
    return c[b_] / c[a_] - 1.0


def check2(a):
    T0 = time.time()
    out = {"時間": subprocess.run(["bash", "-c", "TZ=Asia/Taipei date '+%F %H:%M'"], capture_output=True, text=True).stdout.strip() + "（WSL 時鐘）"}
    E = pd.read_pickle(os.path.join(WORK2, "events.pkl"))
    # ① 分類＝參考實作逐字
    ok_src = hashlib.sha256(SEQ2_SRC.encode("utf-8")).hexdigest() == SEQ2_SHA256
    ref = {}
    if os.path.exists(SEQ2_REF):
        b = open(SEQ2_REF, "rb").read(); ok_ref = hashlib.sha256(b).hexdigest() == SEQ2_SHA256
        ns = {}; exec(compile(b.decode("utf-8"), SEQ2_REF, "exec"), ns)
        N0, _ = load_news2()
        cr = np.array([ns["classify"](s) for s in N0["subject"]])
        mrg = E.merge(N0.assign(cref=cr)[["date", "time", "stock_id", "serial", "cref"]], on=["date", "time", "stock_id", "serial"], how="left")
        ref = {"參考檔 sha256 相符": ok_ref, "全部 news（sii／otc）則數": int(len(N0)), "events.pkl 分類 ≠ 參考實作": int((mrg["cref"] != mrg["cat"]).sum())}
    out["① 分類＝參考 classify() 逐字"] = {"內嵌原始碼 sha256 相符": ok_src, **ref}
    # ② explore 逐位元組不變
    import tempfile
    global OUT
    tmp = tempfile.mkdtemp(prefix="nc_explore_"); old = OUT; OUT = tmp
    D.DATA = H2.H2D; UG.set_gate_v2(False)
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()):
        explore()
    OUT = old
    diff = []
    for f in sorted(os.listdir(old)):
        A_ = open(os.path.join(old, f), "rb").read(); B_ = open(os.path.join(tmp, f), "rb").read()
        if f in ("README.md", "universe_log.json"):
            A_ = b"\n".join(x for x in A_.split(b"\n") if "產出".encode() not in x and "執行時間".encode() not in x)
            B_ = b"\n".join(x for x in B_.split(b"\n") if "產出".encode() not in x and "執行時間".encode() not in x)
        if A_ != B_:
            diff.append(f)
    out["② explore_material 重跑逐位元組比（README／universe_log 略過產出時間行）"] = {"檔數": len(os.listdir(old)), "不同": diff}
    # ③ 抽事件：原始檔自算 e、R
    UG.set_gate_v2(True)
    rng = np.random.default_rng(7)
    K = E[(E["status"] == "保留") & E["dd"] & np.isfinite(E["R20"])]
    bad = 0; tot = 0; ex = []
    cals = {}
    for w in ("early", "main"):
        cal = pd.DatetimeIndex(pd.to_datetime(pd.read_csv(os.path.join(WD2[w], "meta", "calendar_twse.csv"))["date"])).sort_values(); cals[w] = cal
        kw = K[K["world"] == w]
        for i in rng.choice(len(kw), size=min(20, len(kw)), replace=False):
            r = kw.iloc[i]
            x = _ck_stock(WD2[w], r["stock_id"], cal)
            c, o, bars, bd = x
            d_ = pd.Timestamp(r["date"]); p = int(cal.searchsorted(d_))
            trd = p < len(cal) and cal[p] == d_
            if trd and r["time"][:5] <= "13:30":
                e, ty = p, "C"
            else:
                e, ty = (p + 1 if trd else p), "O"
            cff = pd.Series(c).ffill().to_numpy()
            for H in HS2:
                tot += 1
                if ty == "C":
                    R = cff[e + H] / c[e] - 1.0 if e + H < len(cal) and not bd[e + 1:e + H + 1].any() else np.nan
                else:
                    R = cff[e + H - 1] / o[e] - 1.0 if e + H - 1 < len(cal) and not bd[e + 1:e + H].any() else np.nan
                if ty != r["type"] or e != int(r["le"]) or not np.isclose(1.0 + R, 1.0 + r[f"R{H}"], rtol=1e-6, atol=0, equal_nan=True):
                    bad += 1; ex.append((w, r["stock_id"], r["date"], r["time"], H, ty, r["type"], e, int(r["le"]), R, r[f"R{H}"]))
    out["③ 抽 40 事件（兩版面各 20）原始檔自算 e、型別、R1／5／20"] = {"比對": tot, "不同": bad, "例": [list(map(str, z)) for z in ex[:5]]}
    # ④ 基準② 兩天（每版面一天）× 型 C H5、型 O H5：原始檔自算十分位
    bad4 = 0; tot4 = 0; ex4 = []
    for w in ("early", "main"):
        cal = cals[w]
        stocks = pd.read_csv(os.path.join(WD2[w], "meta", "stocks.csv"), dtype=str)
        D.DATA = WD2[w]
        G = sorted(UG.gate3(stocks)["stock_id"])
        kw = K[(K["world"] == w) & np.isfinite(K["X5"])]
        days = kw["le"].value_counts()
        day = int(days.index[rng.integers(0, min(50, len(days)))])
        cols = {}
        for s in G:
            x = _ck_stock(WD2[w], s, cal)
            if x is None:
                continue
            pv = UG.pit_valid(s, cal, WD2[w])
            cols[s] = (x, pv)
        for ty, H in (("C", 5), ("O", 5)):
            vals = []
            for s in G:
                if s not in cols:
                    continue
                (c, o, bars, bd), pv = cols[s]
                if not pv[day] or not np.isfinite(c[day]):
                    continue
                cff = pd.Series(c).ffill().to_numpy()
                if ty == "C":
                    if day + H >= len(cal) or bd[day + 1:day + H + 1].any():
                        continue
                    R = cff[day + H] / c[day] - 1.0; k_ = _ck_r20(c, bars, bd, day, False)
                else:
                    if not (o[day] > 0) or day + H - 1 >= len(cal) or bd[day + 1:day + H].any() or day < 1:
                        continue
                    R = cff[day + H - 1] / o[day] - 1.0; k_ = _ck_r20(c, bars, bd, day - 1, True)
                if np.isfinite(R) and np.isfinite(k_):
                    vals.append((s, k_, R))
            V = pd.DataFrame(vals, columns=["s", "k", "R"])
            V = V.sort_values(["k", "s"], kind="mergesort").reset_index(drop=True)
            V["dec"] = (np.arange(len(V)) * 10) // len(V)
            ev = kw[(kw["le"] == day) & (kw["type"] == ty)]
            for _, r in ev.iterrows():
                tot4 += 1
                me = V[V["s"] == r["stock_id"]]
                if len(me) != 1:
                    bad4 += 1; ex4.append((w, r["stock_id"], ty, "不在自算成員")); continue
                q = V[(V["dec"] == int(me["dec"].iloc[0])) & (V["s"] != r["stock_id"])]
                X = float(me["R"].iloc[0]) - float(q["R"].mean())
                if not np.isclose(X, r[f"X{H}"], rtol=0, atol=1e-6):          # 容差：adj 檔 cum_factor 只存到小數 8 位、本查核用 factor 連乘
                    bad4 += 1; ex4.append((w, r["stock_id"], ty, X, r[f"X{H}"]))
        out[f"④ 基準② 自算（{w} 版面 {cal[day].date()}）"] = {"成員數（型 C、O 各自）": "見比對", "日": str(cal[day].date())}
    out["④ 基準② 兩天 × 型 C／O H5 自算十分位"] = {"比對": tot4, "不同": bad4, "例": [list(map(str, z)) for z in ex4[:5]]}
    # ⑤ cells 與標籤：events.pkl 以另一條路重算
    C = pd.read_csv(os.path.join(OUT2, "cells.csv")); S = json.load(open(os.path.join(OUT2, "summary.json"), encoding="utf-8"))
    mism = 0; nlab = 0
    Kd = E[(E["status"] == "保留") & E["dd"]]
    for c_ in range(1, 13):
        for H in HS2:
            st = {}
            for sg in SEGS2:
                g = Kd[(Kd["seg"] == sg) & (Kd["cat"] == c_)][[f"X{H}", "mon"]].dropna()
                x = g[f"X{H}"].to_numpy(float)
                if len(x) == 0:
                    st[sg] = None; continue
                mu = x.mean(); sm = g.assign(d=x - mu).groupby("mon")["d"].sum().to_numpy()
                se = math.sqrt((sm ** 2).sum()) / len(x)
                st[sg] = (mu, mu - 1.96 * se, mu + 1.96 * se, len(x))
                row = C[(C["版本"] == "去重") & (C["段"] == sg) & (C["cat"] == c_) & (C["H"] == H)].iloc[0]
                if not (np.isclose(mu, row["X平均"], rtol=1e-5) and np.isclose(mu - 1.96 * se, row["lo"], rtol=1e-5, atol=1e-9) and int(row["n"]) == len(x)):
                    mism += 1
            e_, f_, y_ = st["探索"], st["確認"], st["早年"]
            pe = e_ is not None and (e_[1] > 0 or e_[2] < 0); pf = f_ is not None and (f_[1] > 0 or f_[2] < 0)
            react = pe and pf and np.sign(e_[0]) == np.sign(f_[0])
            nlab += int(react != S["判定"][f"{c_}_H{H}"]["有反應"])
    out["⑤ cells（去重 108 列）與 36 格「有反應」由 events.pkl 另路重算"] = {"cells 不同": mism, "標籤不同": nlab}
    good = ok_src and (not ref or (ref["參考檔 sha256 相符"] and ref["events.pkl 分類 ≠ 參考實作"] == 0)) and not diff and bad == 0 and tot > 0 and bad4 == 0 and tot4 > 0 and mism == 0 and nlab == 0
    out["結論"] = "✅ 全過（0 不同）" if good else "⛔ 有不同"
    out["耗時s"] = round(time.time() - T0)
    UG.set_gate_v2(False)
    json.dump(out, open(os.path.join(OUT2, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))


def main2():
    import argparse
    global OUT2, WORK2
    if os.environ.get("NC_SMOKE"):                                   # 冒煙：只取前 150 檔、輸出到 ~/ncwork/smoke（⛔ 不是本件數字）
        OUT2 = WORK2 = os.path.expanduser("~/ncwork/smoke")
    ap = argparse.ArgumentParser(); ap.add_argument("mode", nargs="?", default=None, choices=["explore", "run", "page"])
    ap.add_argument("--procs", type=int, default=4); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if a.check:
        return check2(a)
    if a.mode is None:
        raise SystemExit("用法：python -m backtest.researchNewsCat explore｜run [--procs 4]｜page｜--check")
    if a.mode == "explore":
        return explore()
    if a.mode == "page":
        return page2()
    return run2(a)


if __name__ == "__main__":
    main2()
