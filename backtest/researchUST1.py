# -*- coding: utf-8 -*-
"""USREG-T1 台積電 ADR 溢價 seq1（美股策略線登錄 sha 818f735111234d1b，2026-10-16 23:30；裁定 seq353 §三.3 發號；
N 記台股帳：N_前段 ＋2、N_組合 ＋1；回測執行、台股會同 1017-0140 §二：2330 成本來回 0.585%、0050 用還原價、缺口 ≥5 日壞根 seq335、窗照台股探索／確認段）
——回測線計算子代理，2026-10-17。
⛔ 只計算：不 commit、不 push、不寫跨線信箱、不改既有檔（data／research11／rerun17／researchAddOn 只 import 呼叫）；用語「假訊號」；⛔ 不給買賣建議。
⛔ 私有庫 ~/us-stock-data 只讀；repo 內只放彙總（⛔ 不放 TSM 價格）；逐日明細（P、Z）放 ~/us_work/t1/。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUST1
    獨立重算：  PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUST1_check

⭐ 讀法寫死：2026-10-17 02:45（台北，WSL TZ=Asia/Taipei date）之後、第一次跑之前；寫死前 ⛔ 沒算任何本件數字（只看過資料檔頭尾與事件檔）

═══ 讀法（T 標；登錄沒寫死、執行者補的都在這裡）═══
 T1 資料：
    TSM ＝ ~/us-stock-data/data/macro/yahoo_TSM.csv（close ＝ Yahoo 配股〔記成 split〕調整後、adjclose 另含息）；
         未調整價 ＝ close × Π（事件日 ＞ 該日 的配股因子 num/den）＝ yahoo_events_TSM.csv type＝split 全部列（1998～2009 共 10 次）
    換股比 1 ADS ＝ 5 股普通股（資料庫線 1017-0226：SEC 20-F 2002～2026 逐份核過；⚠ 1997～2001 SEC 只有紙本、未核 —— 本件 P 從 2004-02 起算，用不到那段）
    匯率 ＝ ~/us-stock-data/data/macro/cbc_BP01D01_NTD.csv（央行 BP01D01，台北 16:00 收盤匯率，NTD/USD）；台股日 t 用 t 當日值，缺 ⇒ 用 ≤ t 最近一筆（筆數照報）
    2330／0050 ＝ 本庫兩個世界：早年 researchAddOn.EOTC（2004-02-11～2014-12-31）、主 rerun17.H2D（edc6f8002f；2015-01-05～2026-09-24）
         未還原收盤 ＝ stocks/2330.csv close（算 P）；還原價 ＝ data.load_stock（各世界檔內 adj 因子；算報酬）；0050 ＝ 還原價、停牌日開盤 ⇒ 前一日收盤（同 researchMktDrop_v1）
    ⚠ 本庫 2330 從 2004-02-11 才有 ⇒ P 從 2004-02-11 起（TSM 1997-10 起的資料 1997～2004 用不到）
 T2 時區（前視）：台股日 t 配「美東日期 ＜ t 的最後一個 TSM 收盤」（＝ 台北 t 清晨收完的那一盤）；美東 t 日那一盤要到台北 t＋1 清晨才收 ⇒ 不用
    匯率 16:00 晚於台股 13:30 收盤 ⇒ P_t 在 t 日 16:00 後才完整 ⇒ 一律 t＋1 開盤才動作（登錄本來就是），⛔ 無前視
    美股休市使配到的 TSM 收盤早於前一個美股平日 ⇒ 照用（陳舊日數照報）
 T3 溢價 P_t ＝ TSM未調整[美東 ＜ t 最後一盤] ÷ 5 × 匯率_t ÷ 2330未還原收盤_t − 1；2330 當日無成交 ⇒ 缺
 T4 排除（登錄 §一）：2330 除權息日（本庫 adj 全部事件：息、權、權息；兩世界合併）與 TSM 除息日（events type＝div）、TSM 配股日（type＝split）
    前後 3 個台股交易日 ⇒ P 設缺（不入 Z 的回看、不當事件日、不觸發乙的進出）
    ⚠ 登錄寫「除息日」；配股也會讓兩邊在不同日跳（理由同一條：兩邊日期不同 P 會跳）⇒ 配股併入排除（寫死）
    位置：2330 事件 ＝ 事件日當天或之後第一個台股交易日；TSM 事件 ＝ 第一個「配到的美東日期 ≥ 事件日」的台股交易日；排除 [位置−3, 位置＋3]
 T5 Z_t ＝ (P_t − 均值) ÷ 標準差（ddof＝1），均值與標準差取 t 之前（不含 t）最近 60 個有效 P（被排除與缺的不算）；不滿 60 個 ⇒ 缺；兩世界日曆連續接（P 是未還原、可跨接）
 T6 事件：Z ≥ ＋2（高）、Z ≤ −2（低）；同方向去重 ＝ 收下一筆後，同方向下一筆至少隔 20 個台股交易日（位置差 ≥ 20）
 T7 甲 事件層（登錄 §二）：進場 t＋1 開盤（還原）、持 H 根（data.exit_pos，進場那根算第 1 根）⇒ 出場根收盤；
    超額 ＝ 2330 (收[x] ÷ 開[t＋1] − 1) − 0050 (收[x] ÷ 開[t＋1] − 1)；H ＝ 20（主）、5
    t＋1 與出場根要在同一世界；2330 在 [t＋1, x] 有壞根（research11.load_bars：缺口 ≥5 日、幽靈還原、斷點；早年另查 reduce_v2／R8 名單）⇒ 不收（筆數照報）
    段內 ＝ t 與出場根都在段內（整筆落在段內）
    CI ＝ 月分群（事件日 t 的年月）SE ＝ sqrt(G/(G−1)·Σ_g(Σ殘差)²)/n；判定用 Bonferroni 0.05/2 ⇒ 97.5% 常態臨界 2.241403；95%（1.959964）並報
    統計層 ＝ 毛超額；可執行層（描述）＝ 毛超額 − 0.585%（2330 來回）、另報 − 0.97%（從 0050 換過去再換回：0.585%＋0.385%）
    判語（每方向一格，主 H20）：窗內 97.5% CI 不含 0 ⇒ 測得出（附號）；含 0 ⇒ 測不出（有效月 ＜ 24 加註「樣本少」）
    整格：⭐ 兩窗（早年、主窗）都測得出且同號 ⇒ 測得出；只一窗 ⇒「只在 X 窗測得出」⇒ 不算測得出；探索／確認只描述
    （登錄「兩窗都要過」寫在乙，甲沒寫 ⇒ 本件甲也用同一條；主窗單獨判語另列、⛔ 不換主判）
 T8 乙 組合層：段首收盤抱 0050（淨值 1）；收盤 Z ≥ ＋2 且抱 0050 ⇒ 次一交易日開盤全換 2330；抱 2330 期間收盤 Z ≤ 0（「回到 0 以下」含 0）⇒ 次一交易日開盤換回 0050；
    Z 缺（排除日、不滿 60）⇒ 當天不動作；段首那天收盤也可判；段尾仍抱 2330 ⇒ 段尾收盤結算（扣 2330 賣出＋0050 買進兩腿）⇒ 窗尾未出場照報
    成本分腿（合計 ＝ 2330 來回 0.585% ＋ 0050 來回 0.385%）：買 0.1425%；賣 2330 0.1425%＋稅 0.3%；賣 0050 0.1425%＋稅 0.1%
    2330 持有中遇壞根 ⇒ 壞根前一根收盤強制換回（同全線 Z3 慣例）；2330 開盤缺 ⇒ 延到下一個有開盤的日子
    年化、最大回落 ＝ rerun17.win_metrics（research13.window_stats，245 日／年）；0050 ＝ rerun17.bench_row 同窗；年化波動並報
    判定（使用者判準 seq141）：每窗 合格（年化 ＞ 0050 且 年化÷|回落| ≥ 0050）／另列（只年化贏）／不合格；
    整件：早年、主窗都合格 ⇒ 合格；兩窗都「合格或另列」⇒ 另列；其餘 ⇒ 不合格；探索、確認只描述（台股段，⛔ 不換主判）
    每段各自獨立起算（段首抱 0050），⛔ 不從前段帶部位進來
 T9 假訊號（登錄 §二）：
    甲：每窗每方向，候選日 ＝ 段內 Z 有效、該日事件結果可算（同 T7）、且 [d−20, d] 沒有同方向真事件 的台股日；抽與真事件同數、不放回；1,000 次；
        rng ＝ default_rng([20261017, 窗號, 方向號, H, i])；報隨機平均的分佈（中位、2.5／97.5 分位、半寬）、p（隨機 ≥ 真）、p（隨機 ≤ 真）
    乙：每窗，保持真實的進場次數與每筆持有長度（開盤進、開盤出；段尾結算那筆長度算到段尾＋1），隨機不重疊擺放（星條法均勻抽）；1,000 次；
        rng ＝ default_rng([20261017, 99, 窗號, i])；報隨機年化、回落、比值分佈、p（隨機比值 ≥ 真）、p（隨機年化 ≥ 真）、隨機版照判準的通過率
 T10 描述（⛔ 不判、⛔ 不計 N）：① Z ≤ −2 時把 0050 換現金（收盤 Z ≤ −2 ⇒ 次開盤賣 0050；收盤 Z ≥ 0 ⇒ 次開盤買回；段尾仍現金 ⇒ 扣買回腿）vs 一直抱 0050
    ② 門檻 ±1.5、±2.5（甲事件與乙進場門檻同改，乙出場仍 Z ≤ 0）③ 回看 60 改 120（門檻 ±2）
 T11 必報：每年事件數（原始、去重）、P 逐年中位（另 p10／p90、有效日數、排除日數）；甲 5／20 日超額分年；
    隔夜：每事件 2330 隔夜缺口（開[t＋1] ÷ 收[t] − 1）、扣 0050 同期隔夜後的超額缺口、t 收盤到出場收盤的總超額 ⇒ 隔夜佔總超額（平均之比）；
         另報 P 自身：(P_{t＋1} − P_t) ÷ (P_{t＋20} − P_t)（平均之比；t＋1、t＋20 為台股位置、P 缺 ⇒ 該筆不入）
    乙：年化、回落、比值、年化波動、換手（進場次數、每年次數）、平均持有天數（台股交易日，開盤進到開盤出）、窗尾未出場、2330 曝險日比例
    另描述：TSM 還原（adjclose）與 2330 還原逐年報酬
── 事後註（照實記）──
 ① 02:49 第一次全跑：TSM 1998～2003 六次配股（早於 P 起點）被對到合併位置 0 ⇒ 2004-02-11 起 4 天被誤排除；改成「事件日 ≤ 第一個配到的美東日 ⇒ 不收」後重跑
    （2330 adj 的 2003-07-07 同理只收落在世界資料期內的事件）；⛔ 定義、門檻、判準都沒改
 ② 第二次跑後看 P 序列：2004～2009 2330 配股年除權後 P 有約 1～3 點階梯上移（ADR 配股比例比 2330 小或 Yahoo 沒列）⇒ 加一張描述表（⛔ 不改 P 定義）
輸出 backtest/resultsUST1/：UST1.json、cells.csv、events.csv、event_yearly.csv、premium_yearly.csv、portfolio.csv、trades.csv、random_A.csv、random_B.csv、variants.csv、run.log
     ~/us_work/t1/premium_daily.csv（逐日 P、Z60、Z120、排除旗標；⛔ 不進 repo）
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
import time
import subprocess

import numpy as np
import pandas as pd

REPO = os.path.expanduser("~/tw-p17")
sys.path.insert(0, REPO)
OUT = os.path.join(REPO, "backtest/resultsUST1")
WORK = os.path.expanduser("~/us_work/t1")
USM = os.path.expanduser("~/us-stock-data/data/macro")
TSMF = os.path.join(USM, "yahoo_TSM.csv")
TSMEV = os.path.join(USM, "yahoo_events_TSM.csv")
FXF = os.path.join(USM, "cbc_BP01D01_NTD.csv")
REG = {"件": "USREG-T1 台積電ADR溢價 seq1", "登錄 sha": "818f735111234d1b", "裁定": "seq353 §三.3（N 記台股帳：N_前段 ＋2、N_組合 ＋1）",
       "會同": "台股策略線 1017-0140 §二", "資料": "資料庫線 1017-0226 §二（us-stock-data 070a4bcd7）"}
TIME = "2026-10-17 02:45（台北）寫死、第一次跑之前"
RATIO = 5.0
EXCL = 3
W_MAIN = 60
TH_MAIN = 2.0
DEDUP = 20
HS = (20, 5)
BUY = 0.001425
SELL_STK = 0.001425 + 0.003
SELL_ETF = 0.001425 + 0.001
C2330 = 0.00585
C0050 = 0.00385
Z95, ZBON = 1.959964, 2.241403
NREP = 1000
SEED = 20261017
WINS = {"早年": ("2005-02-01", "2014-12-31", "早年"), "主窗": ("2017-03-02", "2026-08-24", "主"),
        "探索": ("2017-03-02", "2021-12-30", "主"), "確認": ("2022-01-03", "2026-08-24", "主")}
JUDGE = ("早年", "主窗")
WNO = {"早年": 0, "主窗": 1, "探索": 2, "確認": 3}
DIRS = {"高": +1, "低": -1}
DNO = {"高": 0, "低": 1}
BENCH_MAIN = (0.2402, -0.3396)


def now_tpe():
    return subprocess.run(["bash", "-c", "TZ=Asia/Taipei date '+%Y-%m-%d %H:%M:%S'"], capture_output=True, text=True).stdout.strip()


# ═════════════ 資料 ═════════════
def load_tsm():
    t = pd.read_csv(TSMF, dtype={"date": str})
    t["date"] = pd.to_datetime(t["date"])
    t = t.sort_values("date").drop_duplicates("date").reset_index(drop=True)
    ev = pd.read_csv(TSMEV, dtype=str)
    ev["date"] = pd.to_datetime(ev["date"])
    sp = ev[ev["type"] == "split"].copy()
    sp["f"] = sp["value"].map(lambda v: float(v.split("/")[0]) / float(v.split("/")[1]))
    dv = ev[ev["type"] == "div"].copy()
    mult = np.ones(len(t))
    for d, f in zip(sp["date"], sp["f"]):
        mult[(t["date"] < d).to_numpy()] *= f            # 事件日 ＞ 該日 ⇒ 乘
    t["unadj"] = t["close"].astype(float) * mult
    return t, sp, dv


def load_fx():
    f = pd.read_csv(FXF, dtype={"date": str})
    f["date"] = pd.to_datetime(f["date"]); f["ntd_per_usd"] = pd.to_numeric(f["ntd_per_usd"], errors="coerce")
    return f.dropna().sort_values("date").drop_duplicates("date").reset_index(drop=True)


def load_world(wn, log):
    from backtest import data as D
    from backtest import research11 as R11
    from backtest import rerun17 as RR
    from backtest import researchAddOn as RA
    D.DATA = RA.EOTC if wn == "早年" else RR.H2D
    cal = D.load_calendar(); n = len(cal)
    B = R11.load_bars("2330", "twse", cal)
    O2 = np.full(n, np.nan); C2 = np.full(n, np.nan); RC = np.full(n, np.nan); BAD = np.zeros(n, bool)
    O2[B["idx"]] = B["o"]; C2[B["idx"]] = B["c"]; RC[B["idx"]] = B["rc"]
    bad_k = np.flatnonzero(B["next_bad"][:len(B["idx"])] == np.arange(len(B["idx"])))
    BAD[B["idx"][bad_k]] = True
    extra = {}
    if wn == "早年":                                     # reduce_v2＋R8 名單裡有沒有 2330
        for fn in ("twse_reduce_detected_2004_2010.csv", "otc_reduce_detected_2007_2012.csv", "twse_jump_unexplained_2004_2010.csv"):
            x = pd.read_csv(os.path.join(RA.V2EXT, fn), dtype=str, keep_default_na=False)
            extra[fn] = int((x["stock_id"].str.strip() == "2330").sum())
        wp = os.path.join(RA.WORK, "world_早年.pkl")
        if os.path.exists(wp):
            Wa = pickle.load(open(wp, "rb"))
            extra["R8 事件（addonwork world_早年 EV）"] = int((Wa["EV"]["stock_id"].astype(str).str.strip() == "2330").sum())
        if any(v > 0 for v in extra.values()):
            raise SystemExit(f"⛔ 早年另加壞根名單有 2330：{extra}（本檔未處理）")
    st = D.load_stock("0050", "twse", cal).df
    BC = pd.Series(st["close"].to_numpy(float)).ffill().to_numpy(float)
    BO = st["open"].to_numpy(float).copy()
    bo_fix = ~(np.isfinite(BO) & (BO > 0))
    BO[bo_fix] = np.r_[np.nan, BC[:-1]][bo_fix]
    bench = np.asarray(RR.load_bench(cal), float)
    adj = D.load_adj("2330")
    ev2330 = [] if adj is None else [(d, k) for d, k in zip(adj["date"], adj["kind"])]
    C2f = pd.Series(C2).ffill().to_numpy(float)
    gate = {"日曆": f"{cal[0].date()}～{cal[-1].date()}（{n}）", "2330 有效 K 棒": int(len(B["idx"])), "2330 缺 K 棒日": int(n - len(B["idx"])),
            "2330 壞根（load_bars）": [str(cal[i].date()) for i in np.flatnonzero(BAD)], "0050 開盤補前收": int(bo_fix.sum()),
            "0050 bench 與 BC 最大相對差": float(np.nanmax(np.abs(bench / BC - 1))), "早年另加壞根名單中的 2330": extra}
    log(f"[世界 {wn}] {gate}")
    return {"name": wn, "cal": cal, "n": n, "O2": O2, "C2": C2, "C2f": C2f, "RC": RC, "BAD": BAD, "BO": BO, "BC": BC, "bench": bench,
            "ev2330": ev2330, "gate": gate}


def build_premium(WD, log):
    """兩世界合併日曆上的 P、排除旗標、對應 TSM 美東日期。"""
    tsm, sp, dv = load_tsm(); fx = load_fx()
    cal = WD["早年"]["cal"].append(WD["主"]["cal"])
    if not cal.is_monotonic_increasing or cal.has_duplicates:
        raise SystemExit("⛔ 合併日曆不單調")
    world = np.r_[np.zeros(WD["早年"]["n"], int), np.ones(WD["主"]["n"], int)]
    wpos = np.r_[np.arange(WD["早年"]["n"]), np.arange(WD["主"]["n"])]
    RC = np.r_[WD["早年"]["RC"], WD["主"]["RC"]]
    N = len(cal)
    ud = tsm["date"].to_numpy("datetime64[ns]")
    j = np.searchsorted(ud, cal.values.astype("datetime64[ns]"), side="left") - 1     # 美東日期 ＜ t 的最後一盤
    if (j < 0).any():
        raise SystemExit("⛔ 有台股日找不到更早的 TSM")
    usd = tsm["unadj"].to_numpy(float)[j]; usdate = tsm["date"].to_numpy("datetime64[ns]")[j]
    fd = fx["date"].to_numpy("datetime64[ns]")
    k = np.searchsorted(fd, cal.values.astype("datetime64[ns]"), side="right") - 1
    fxv = fx["ntd_per_usd"].to_numpy(float)[k]
    fx_exact = fd[k] == cal.values.astype("datetime64[ns]")
    P = usd * fxv / (RATIO * RC) - 1.0
    # 陳舊：配到的美東日與 t 之間（不含兩端）有美股平日
    us_bd = pd.bdate_range(pd.Timestamp(usdate.min()), cal[-1])
    bdv = us_bd.values.astype("datetime64[ns]")
    cnt_between = np.searchsorted(bdv, cal.values.astype("datetime64[ns]"), "left") - np.searchsorted(bdv, usdate, "right")
    stale = cnt_between > 0
    # 排除
    ex = np.zeros(N, bool); exsrc = []
    evp = []
    for wn in ("早年", "主"):
        c0, c1 = WD[wn]["cal"][0], WD[wn]["cal"][-1]
        for d, kd in WD[wn]["ev2330"]:
            d = pd.Timestamp(d)
            if not (c0 < d <= c1):                       # 只收落在該世界資料期內的事件（早年 adj 有 2003-07-07，資料 2004-02-11 起）
                continue
            p = int(cal.searchsorted(d))
            evp.append(("2330" + str(kd), str(d.date()), p))
    evp = sorted(set(evp), key=lambda x: x[2])
    for typ, df_ in (("TSM除息", dv), ("TSM配股", sp)):
        for d in df_["date"]:
            if np.datetime64(pd.Timestamp(d)) <= usdate[0]:         # 事件早於 P 起點（1998～2003 配股）⇒ 不影響 P
                continue
            p = int(np.searchsorted(usdate, np.datetime64(pd.Timestamp(d)), "left"))   # 第一個配到美東日 ≥ d 的台股日
            if p < N:
                evp.append((typ, str(pd.Timestamp(d).date()), p))
    for typ, d, p in evp:
        lo, hi = max(0, p - EXCL), min(N - 1, p + EXCL)
        ex[lo:hi + 1] = True
        exsrc.append({"來源": typ, "事件日": d, "台股位置日": str(cal[p].date())})
    Pv = P.copy(); Pv[ex] = np.nan
    PR = {"cal": cal, "N": N, "world": world, "wpos": wpos, "P": P, "Pv": Pv, "ex": ex, "usdate": usdate, "fx_exact": fx_exact, "stale": stale,
          "exsrc": exsrc, "tsm": tsm, "sp": sp, "dv": dv}
    log(f"[P] {cal[0].date()}～{cal[-1].date()}｜{N} 日｜P 有值 {int(np.isfinite(P).sum())}｜排除日 {int(ex.sum())}｜有效 {int(np.isfinite(Pv).sum())}｜"
        f"匯率非當日 {int((~fx_exact).sum())}｜TSM 陳舊 {int(stale.sum())}｜排除事件 {len(exsrc)}")
    return PR


def zscore(Pv, W):
    """Z_t：t 之前（不含 t）最近 W 個有效 P 的均值、標準差（ddof=1）；t 本身要有效。"""
    N = len(Pv); Z = np.full(N, np.nan)
    vi = np.flatnonzero(np.isfinite(Pv)); vals = Pv[vi]
    s = pd.Series(vals)
    m = s.rolling(W, min_periods=W).mean().shift(1).to_numpy(); sd = s.rolling(W, min_periods=W).std(ddof=1).shift(1).to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        Z[vi] = (vals - m) / sd
    return Z


def events(Z, th, sgn):
    raw = (Z >= th) if sgn > 0 else (Z <= -th)
    raw = raw & np.isfinite(Z)
    acc = []; last = -10 ** 9
    for t in np.flatnonzero(raw):
        if t - last >= DEDUP:
            acc.append(int(t)); last = t
    return raw, np.array(acc, int)


def outcome(PR, WD, t, H):
    """事件 t（合併位置）⇒ dict 或 (None, 原因)。"""
    w = "早年" if PR["world"][t] == 0 else "主"; W = WD[w]; k = int(PR["wpos"][t]); n = W["n"]
    from backtest import data as D
    e = k + 1
    if e >= n:
        return None, "進場根超出世界"
    x = D.exit_pos(e, H)
    if x >= n:
        return None, "出場根超出世界"
    if not (np.isfinite(W["O2"][e]) and W["O2"][e] > 0):
        return None, "2330 t＋1 開盤缺"
    if W["BAD"][e:x + 1].any():
        return None, "持有中壞根"
    if not np.isfinite(W["C2"][k]):
        return None, "2330 t 收盤缺"
    r2 = W["C2f"][x] / W["O2"][e] - 1; r5 = W["BC"][x] / W["BO"][e] - 1
    g2 = W["O2"][e] / W["C2"][k] - 1; g5 = W["BO"][e] / W["BC"][k] - 1
    tot = (W["C2f"][x] / W["C2"][k] - 1) - (W["BC"][x] / W["BC"][k] - 1)
    return {"w": w, "k": k, "e": e, "x": x, "x_global": t + (x - k), "r2330": r2, "r0050": r5, "ex": r2 - r5,
            "gap2330": g2, "gap0050": g5, "gapex": g2 - g5, "totex": tot}, None


def clus(x, g):
    x = np.asarray(x, float); n = len(x)
    if n < 2:
        return {"n": n, "G": int(len(set(g))), "平均": float(x.mean()) if n else np.nan, "中位": float(np.median(x)) if n else np.nan,
                "se": np.nan, "lo95": np.nan, "hi95": np.nan, "lo975": np.nan, "hi975": np.nan}
    m = float(x.mean())
    s = pd.DataFrame({"r": x - m, "g": g}).groupby("g")["r"].sum().to_numpy(); G = len(s)
    se = float(np.sqrt(G / (G - 1) * (s ** 2).sum()) / n) if G > 1 else np.nan
    return {"n": n, "G": G, "平均": m, "中位": float(np.median(x)), "勝率（超額＞0）": float(np.mean(x > 0)), "se": se,
            "lo95": m - Z95 * se, "hi95": m + Z95 * se, "lo975": m - ZBON * se, "hi975": m + ZBON * se}


def win_pos(cal, a, b):
    x = int(cal.searchsorted(pd.Timestamp(a))); y = int(cal.searchsorted(pd.Timestamp(b), side="right")) - 1
    return x, y


# ═════════════ 乙 ═════════════
def schedule(Zw, W, x0, y0, th_in, th_out, mode):
    """收盤判、次開盤做。mode＝"2330"：Z ≥ th_in 進、Z ≤ th_out 出；mode＝"cash"：Z ≤ −th_in 進（賣 0050）、Z ≥ −th_out 出。
    ⇒ holds: list of (e, x, kind)；kind＝"open"（x 開盤出）／"close"（x 收盤出：壞根強制或段尾結算）"""
    holds = []; state = 0; e = None; pend_in = False; busy = -1
    for k in range(x0, y0 + 1):
        if state == 1 and mode == "2330" and k > e and W["BAD"][k]:
            holds.append((e, k - 1, "close")); state = 0; e = None
        if pend_in and state == 0:
            if mode == "cash" or (np.isfinite(W["O2"][k]) and W["O2"][k] > 0):
                e = k; state = 1; pend_in = False
        if k == y0:
            break
        if k < busy:                                     # 出場因開盤缺而順延中：不判
            continue
        z = Zw[k]
        if not np.isfinite(z):
            continue
        if state == 0:
            if (mode == "2330" and z >= th_in) or (mode == "cash" and z <= -th_in):
                pend_in = True
        else:
            if (mode == "2330" and z <= th_out) or (mode == "cash" and z >= -th_out):
                # 次開盤出（2330 開盤缺 ⇒ 延）
                q = k + 1
                while mode == "2330" and q <= y0 and not (np.isfinite(W["O2"][q]) and W["O2"][q] > 0):
                    q += 1
                if q <= y0:
                    if mode == "2330" and W["BAD"][e + 1:q + 1].any():
                        b = e + 1 + int(np.flatnonzero(W["BAD"][e + 1:q + 1])[0])
                        holds.append((e, b - 1, "close"))
                    else:
                        holds.append((e, q, "open"))
                    state = 0; e = None; busy = q                # q 當天收盤起才可再判
    if state == 1:
        holds.append((e, y0, "close"))
    # 開盤出的 x 若落在下一筆進場之後不可能（狀態機保證）
    return holds


def equity(W, x0, y0, holds, mode):
    n = W["n"]; BO, BC, O2, C2 = W["BO"], W["BC"], W["O2"], W["C2f"]
    m = np.ones(n)
    m[x0 + 1:y0 + 1] = BC[x0 + 1:y0 + 1] / BC[x0:y0]
    for e, x, kd in holds:
        if mode == "2330":
            m[e] = BO[e] / BC[e - 1] * (1 - SELL_ETF) * (1 - BUY) * C2[e] / O2[e]
            last = x - 1 if kd == "open" else x
            if last >= e + 1:
                m[e + 1:last + 1] = C2[e + 1:last + 1] / C2[e:last]
            if kd == "open":
                m[x] = O2[x] / C2[x - 1] * (1 - SELL_STK) * (1 - BUY) * BC[x] / BO[x]
            else:
                m[x] *= (1 - SELL_STK) * (1 - BUY)
        else:
            m[e] = BO[e] / BC[e - 1] * (1 - SELL_ETF)
            last = x - 1 if kd == "open" else x
            if last >= e + 1:
                m[e + 1:last + 1] = 1.0
            if kd == "open":
                m[x] = (1 - BUY) * BC[x] / BO[x]
            else:
                m[x] *= (1 - BUY)
    eq = np.full(n, np.nan)
    eq[x0] = 1.0
    eq[x0 + 1:y0 + 1] = np.cumprod(m[x0 + 1:y0 + 1])
    return eq


def pstats(W, eq, x0, y0, holds):
    from backtest import rerun17 as RR
    c, mdd, vol = RR.win_metrics(eq, x0, y0 + 1, x0, y0)
    yrs = (y0 + 1 - x0) / 245
    lens = [(x - e) if kd == "open" else (x + 1 - e) for e, x, kd in holds]
    held = sum(lens)
    return {"年化": c, "最大回落": mdd, "比值": c / abs(mdd) if mdd < 0 else np.nan, "年化波動": vol, "年化÷波動": c / vol if vol > 0 else np.nan,
            "進場次數": len(holds), "每年進場次數": len(holds) / yrs, "平均持有天數": float(np.mean(lens)) if lens else np.nan,
            "持有天數中位": float(np.median(lens)) if lens else np.nan, "曝險日比例": held / (y0 - x0), "窗尾未出場": int(any(kd == "close" and x == y0 for e, x, kd in holds)),
            "壞根強制": int(sum(1 for e, x, kd in holds if kd == "close" and x != y0))}


def label(s, b):
    c1 = s["年化"] > b["cagr"]; c2 = s["比值"] >= b["cagr"] / abs(b["mdd"])
    return "合格" if (c1 and c2) else ("另列" if c1 else "不合格")


def rand_holds(rng, x0, y0, lens):
    K = len(lens)
    if K == 0:
        return []
    L = list(rng.permutation(np.asarray(lens, int)))
    span = (y0 + 1) - (x0 + 1)
    free = span - int(sum(L))
    if free < 0:
        return None
    u = np.sort(rng.choice(free + K, size=K, replace=False))
    out = []; cum = 0
    for i in range(K):
        s = x0 + 1 + int(u[i]) - i + cum
        x = s + L[i]
        out.append((s, x, "open") if x <= y0 else (s, y0, "close"))
        cum += L[i]
    return out


# ═════════════ 主程式 ═════════════
def run(a, log):
    T0 = time.time(); os.makedirs(OUT, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    from backtest import rerun17 as RR
    S = {"件": REG, "讀法寫死": TIME, "開跑（台北）": now_tpe(), "讀法": "見程式檔頭 T1～T11"}
    WD = {wn: load_world(wn, log) for wn in ("早年", "主")}
    S["世界閘"] = {wn: WD[wn]["gate"] for wn in WD}
    PR = build_premium(WD, log)
    cal = PR["cal"]; N = PR["N"]
    Zs = {60: zscore(PR["Pv"], 60), 120: zscore(PR["Pv"], 120)}
    S["資料"] = {"P 起訖": f"{cal[0].date()}～{cal[-1].date()}", "合併台股日": N, "P 有值": int(np.isfinite(PR["P"]).sum()),
                "排除日": int(PR["ex"].sum()), "P 有效": int(np.isfinite(PR["Pv"]).sum()), "Z60 有值": int(np.isfinite(Zs[60]).sum()),
                "Z120 有值": int(np.isfinite(Zs[120]).sum()), "匯率非當日（用 ≤ t 最近一筆）": int((~PR["fx_exact"]).sum()),
                "TSM 陳舊日（中間隔美股平日休市）": int(PR["stale"].sum()), "排除事件數": len(PR["exsrc"]),
                "TSM 第一筆": str(PR["tsm"]["date"].iloc[0].date()), "TSM 最後一筆": str(PR["tsm"]["date"].iloc[-1].date()),
                "配股因子連乘（1997-10-09 起）": float(np.prod(PR["sp"]["f"].to_numpy())), "配股事件": [f"{d.date()} {v}" for d, v in zip(PR["sp"]["date"], PR["sp"]["value"])],
                "換股比": "1 ADS ＝ 5 股（2002～2026 SEC 核；1997～2001 未核、本件用不到）"}
    S["排除事件"] = PR["exsrc"]
    log(f"[資料] {S['資料']}")
    # 逐日明細 ⇒ us_work
    pd.DataFrame({"date": cal.strftime("%Y-%m-%d"), "tsm_us_date": pd.DatetimeIndex(PR["usdate"]).strftime("%Y-%m-%d"), "P": PR["P"], "excluded": PR["ex"].astype(int),
                  "Z60": Zs[60], "Z120": Zs[120], "fx_exact": PR["fx_exact"].astype(int), "stale": PR["stale"].astype(int)}).to_csv(
        os.path.join(WORK, "premium_daily.csv"), index=False, float_format="%.15g")
    # P 逐年
    yr = cal.year.to_numpy()
    PY = []
    for y in sorted(set(yr)):
        m = yr == y; v = PR["Pv"][m]; v = v[np.isfinite(v)]
        PY.append({"年": int(y), "台股日": int(m.sum()), "排除日": int(PR["ex"][m].sum()), "P 有效日": len(v), "P 中位": float(np.median(v)) if len(v) else np.nan,
                   "P p10": float(np.percentile(v, 10)) if len(v) else np.nan, "P p90": float(np.percentile(v, 90)) if len(v) else np.nan,
                   "P 平均": float(v.mean()) if len(v) else np.nan})
    # TSM 還原、2330 還原逐年（描述）
    tsm = PR["tsm"]; ty = tsm.groupby(tsm["date"].dt.year)["adjclose"].last()
    c2_all = np.r_[WD["早年"]["C2f"], WD["主"]["C2f"]]
    # 跨世界接：早年世界還原因子以 2014-12-31 為 1、主世界以 2026 為 1 ⇒ 年報酬只在世界內算；2015 年用主世界 2015 首日前一個交易日（2014-12-31）未還原 ÷ 2330 主世界因子
    for r in PY:
        y = r["年"]
        r["TSM 還原年報酬（美元）"] = float(ty.loc[y] / ty.loc[y - 1] - 1) if (y in ty.index and (y - 1) in ty.index) else np.nan
        m = np.flatnonzero(yr == y); mp = np.flatnonzero(yr == y - 1)
        if len(mp) and len(m) and PR["world"][m[-1]] == PR["world"][mp[-1]]:
            r["2330 還原年報酬（台幣）"] = float(c2_all[m[-1]] / c2_all[mp[-1]] - 1)
        else:
            r["2330 還原年報酬（台幣）"] = np.nan
    # ── 事件（主：Z60、±2）──
    def event_table(Z, th, tag):
        rows = []
        for dn, sg in DIRS.items():
            raw, acc = events(Z, th, sg)
            for t in acc:
                row = {"設定": tag, "方向": dn, "日期": str(cal[t].date()), "合併位置": int(t), "Z": float(Z[t]), "P": float(PR["P"][t])}
                for H in HS:
                    o, why = outcome(PR, WD, t, H)
                    if o is None:
                        row[f"H{H}_可算"] = False; row[f"H{H}_原因"] = why
                        continue
                    row.update({f"H{H}_可算": True, f"H{H}_出場日": str(WD[o['w']]["cal"][o["x"]].date()), f"H{H}_2330": o["r2330"], f"H{H}_0050": o["r0050"],
                                f"H{H}_超額": o["ex"], f"H{H}_總超額（t收盤起）": o["totex"]})
                    if H == 20:
                        row.update({"隔夜2330": o["gap2330"], "隔夜0050": o["gap0050"], "隔夜超額": o["gapex"]})
                p1 = t + 1; p20 = t + 20
                row["ΔP_t+1"] = float(PR["P"][p1] - PR["P"][t]) if p1 < N and np.isfinite(PR["P"][p1]) else np.nan
                row["ΔP_t+20"] = float(PR["P"][p20] - PR["P"][t]) if p20 < N and np.isfinite(PR["P"][p20]) else np.nan
                rows.append(row)
            S.setdefault("事件數", {}).setdefault(tag, {})[dn] = {"原始日": int(raw.sum()), "去重": int(len(acc))}
        return pd.DataFrame(rows)
    EV = event_table(Zs[60], TH_MAIN, "主 Z60±2")
    EV["年"] = EV["日期"].str[:4].astype(int)
    # 甲 每窗
    CELLS = []; EY = []
    def in_win(E, wname, H):
        a_, b_, wn = WINS[wname]
        m = (E["日期"] >= a_) & (E["日期"] <= b_) & E[f"H{H}_可算"].fillna(False).astype(bool)
        m &= E[f"H{H}_出場日"].fillna("9999") <= b_
        return E[m]
    def cells_of(E, tag):
        out = []
        for wname in WINS:
            for dn in DIRS:
                for H in HS:
                    sub = in_win(E[E["方向"] == dn], wname, H)
                    a_, b_, _ = WINS[wname]
                    allin = E[(E["方向"] == dn) & (E["日期"] >= a_) & (E["日期"] <= b_)]
                    c = clus(sub[f"H{H}_超額"].to_numpy(float), sub["日期"].str[:7].to_numpy())
                    r = {"設定": tag, "窗": wname, "方向": dn, "H": H, "段內去重事件": int(len(allin)), "可算且整筆在段內": int(len(sub)), **c}
                    r["測得出（97.5%）"] = bool(np.isfinite(r["lo975"]) and (r["lo975"] > 0 or r["hi975"] < 0))
                    r["測得出（95%）"] = bool(np.isfinite(r["lo95"]) and (r["lo95"] > 0 or r["hi95"] < 0))
                    r["扣2330來回0.585%"] = r["平均"] - C2330; r["扣換股0.97%"] = r["平均"] - C2330 - C0050
                    r["2330平均"] = float(sub[f"H{H}_2330"].mean()) if len(sub) else np.nan; r["0050平均"] = float(sub[f"H{H}_0050"].mean()) if len(sub) else np.nan
                    if H == 20 and len(sub):
                        r["隔夜超額平均"] = float(sub["隔夜超額"].mean()); r["隔夜超額中位"] = float(sub["隔夜超額"].median())
                        r["隔夜2330平均"] = float(sub["隔夜2330"].mean())
                        r["總超額（t收盤起）平均"] = float(sub["H20_總超額（t收盤起）"].mean())
                        r["隔夜佔總超額（平均之比）"] = r["隔夜超額平均"] / r["總超額（t收盤起）平均"] if r["總超額（t收盤起）平均"] != 0 else np.nan
                        q = sub[np.isfinite(sub["ΔP_t+1"]) & np.isfinite(sub["ΔP_t+20"])]
                        r["ΔP_t+1平均"] = float(q["ΔP_t+1"].mean()) if len(q) else np.nan; r["ΔP_t+20平均"] = float(q["ΔP_t+20"].mean()) if len(q) else np.nan
                        r["P 次日變化佔 20 日變化（平均之比）"] = r["ΔP_t+1平均"] / r["ΔP_t+20平均"] if len(q) and r["ΔP_t+20平均"] != 0 else np.nan
                        r["ΔP 可算筆數"] = int(len(q))
                    out.append(r)
        return out
    CELLS += cells_of(EV, "主 Z60±2")
    # 甲 判語
    J = {}
    for dn in DIRS:
        per = {}
        for wname in WINS:
            r = next(c for c in CELLS if c["設定"] == "主 Z60±2" and c["窗"] == wname and c["方向"] == dn and c["H"] == 20)
            if r["測得出（97.5%）"]:
                lab = f"測得出（{'＋' if r['平均'] > 0 else '－'}）"
            else:
                lab = "測不出" + ("（有效月 ＜ 24、樣本少）" if r["G"] < 24 else "")
            per[wname] = {"判語": lab, "平均": r["平均"], "97.5%CI": [r["lo975"], r["hi975"]], "n": r["n"], "有效月": r["G"]}
        j1, j2 = per["早年"], per["主窗"]
        if j1["判語"].startswith("測得出") and j2["判語"].startswith("測得出") and j1["判語"][:6] == j2["判語"][:6]:
            tot = f"測得出（兩窗同號 {j2['判語'][3:]}）"
        elif j1["判語"].startswith("測得出") or j2["判語"].startswith("測得出"):
            w_ = "早年" if j1["判語"].startswith("測得出") else "主窗"
            tot = f"只在{w_}測得出 ⇒ 不算測得出"
        else:
            tot = "測不出"
        J[dn] = {"整格（兩窗）": tot, "各窗": per}
    S["甲 判語（主 H20、Bonferroni 97.5%）"] = J
    log(f"[甲] {json.dumps(J, ensure_ascii=False, default=float)}")
    # 甲 分年
    for dn in DIRS:
        for y in sorted(EV["年"].unique()):
            sub = EV[(EV["方向"] == dn) & (EV["年"] == y)]
            r = {"方向": dn, "年": int(y), "去重事件": int(len(sub))}
            for H in HS:
                q = sub[sub[f"H{H}_可算"].fillna(False).astype(bool)]
                r[f"H{H} 可算"] = int(len(q)); r[f"H{H} 超額平均"] = float(q[f"H{H}_超額"].mean()) if len(q) else np.nan
                r[f"H{H} 超額中位"] = float(q[f"H{H}_超額"].median()) if len(q) else np.nan
            q = sub[sub["H20_可算"].fillna(False).astype(bool)]
            r["隔夜超額平均"] = float(q["隔夜超額"].mean()) if len(q) else np.nan
            EY.append(r)
    EYdf = pd.DataFrame(EY)
    # 每年原始事件日數（必報：每年事件數）
    for dn, sg in DIRS.items():
        raw, _ = events(Zs[60], TH_MAIN, sg)
        for r in PY:
            r[f"Z60 {dn} 原始日"] = int(raw[yr == r["年"]].sum())
            r[f"Z60 {dn} 去重事件"] = int((EV[(EV["方向"] == dn)]["年"] == r["年"]).sum())
    # ── 甲 假訊號 ──
    RA_ = []
    for wname in WINS:
        a_, b_, wn = WINS[wname]
        for dn, sg in DIRS.items():
            real = EV[EV["方向"] == dn]
            rp = real["合併位置"].to_numpy(int)
            for H in HS:
                sub = in_win(real, wname, H)
                nr = len(sub)
                if nr == 0:
                    continue
                xa, xb = int(cal.searchsorted(pd.Timestamp(a_))), int(cal.searchsorted(pd.Timestamp(b_), side="right")) - 1
                cand = []; vals = []
                for d in range(xa, xb + 1):
                    if not np.isfinite(Zs[60][d]):
                        continue
                    if ((rp >= d - DEDUP) & (rp <= d)).any():
                        continue
                    o, why = outcome(PR, WD, d, H)
                    if o is None or str(WD[o["w"]]["cal"][o["x"]].date()) > b_:
                        continue
                    cand.append(d); vals.append(o["ex"])
                vals = np.asarray(vals)
                means = np.empty(NREP)
                for i in range(NREP):
                    rng = np.random.default_rng([SEED, WNO[wname], DNO[dn], H, i])
                    means[i] = vals[rng.choice(len(vals), size=nr, replace=False)].mean()
                rm = float(sub[f"H{H}_超額"].mean())
                RA_.append({"窗": wname, "方向": dn, "H": H, "真事件數": nr, "候選日": len(vals), "真平均": rm, "隨機平均之中位": float(np.median(means)),
                            "隨機平均之平均": float(means.mean()), "隨機 2.5%": float(np.percentile(means, 2.5)), "隨機 97.5%": float(np.percentile(means, 97.5)),
                            "假訊號半寬": float((np.percentile(means, 97.5) - np.percentile(means, 2.5)) / 2),
                            "p（隨機≥真）": float(np.mean(means >= rm)), "p（隨機≤真）": float(np.mean(means <= rm)),
                            "真減隨機中位": rm - float(np.median(means))})
    RAdf = pd.DataFrame(RA_)
    log("[甲 假訊號]\n" + RAdf.to_string())
    # ── 乙 ──
    PORT = []; TR = []; RB = []
    def run_port(Z, th_in, th_out, mode, tag, wname, rand=False):
        a_, b_, wn = WINS[wname]; W = WD[wn]
        x0, y0 = win_pos(W["cal"], a_, b_)
        off = 0 if wn == "早年" else WD["早年"]["n"]
        Zw = Z[off:off + W["n"]]
        holds = schedule(Zw, W, x0, y0, th_in, th_out, mode)
        eq = equity(W, x0, y0, holds, mode)
        st = pstats(W, eq, x0, y0, holds)
        b = RR.bench_row(W["cal"], W["bench"], x0, y0 + 1)
        lab = label(st, b)
        row = {"設定": tag, "窗": wname, "起": str(W["cal"][x0].date()), "訖": str(W["cal"][y0].date()), **st,
               "0050年化": b["cagr"], "0050最大回落": b["mdd"], "0050比值": b["cagr"] / abs(b["mdd"]), "0050年化波動": b["vol"],
               "0050年化÷波動": b["cagr"] / b["vol"], "年化減0050": st["年化"] - b["cagr"], "比值減0050": st["比值"] - b["cagr"] / abs(b["mdd"]),
               "回落減0050": st["最大回落"] - b["mdd"], "判準標籤": lab}
        return row, holds, eq, (W, x0, y0, b)
    for wname in WINS:
        row, holds, eq, (W, x0, y0, b) = run_port(Zs[60], TH_MAIN, 0.0, "2330", "主 乙 Z60 ≥2 進、≤0 出", wname)
        PORT.append(row)
        for e, x, kd in holds:
            gr = (W["C2f"][x] / W["O2"][e] if kd == "close" else W["O2"][x] / W["O2"][e]) - 1
            br = (W["BC"][x] / W["BO"][e] if kd == "close" else W["BO"][x] / W["BO"][e]) - 1
            TR.append({"窗": wname, "進場日（開盤）": str(W["cal"][e].date()), "出場日": str(W["cal"][x].date()), "出場": "開盤" if kd == "open" else "收盤（段尾結算或壞根）",
                       "持有天數": (x - e) if kd == "open" else (x + 1 - e), "2330 毛報酬": gr, "0050 同期毛報酬": br, "超額": gr - br})
        # 假訊號（乙）
        lens = [(x - e) if kd == "open" else (x + 1 - e) for e, x, kd in holds]
        rr = []
        for i in range(NREP):
            rng = np.random.default_rng([SEED, 99, WNO[wname], i])
            hr = rand_holds(rng, x0, y0, lens)
            if hr is None:
                continue
            # 壞根：落在持有中的壞根 ⇒ 壞根前一根收盤強制（同真）
            h2 = []
            for e, x, kd in hr:
                bb = np.flatnonzero(W["BAD"][e + 1:x + 1]) if x > e else []
                if len(bb):
                    h2.append((e, e + int(bb[0]), "close"))
                else:
                    h2.append((e, x, kd))
            eqr = equity(W, x0, y0, h2, "2330")
            s = pstats(W, eqr, x0, y0, h2)
            rr.append({"年化": s["年化"], "最大回落": s["最大回落"], "比值": s["比值"], "標籤": label(s, b)})
        R_ = pd.DataFrame(rr)
        if len(R_):
            RB.append({"窗": wname, "真進場次數": len(holds), "真年化": row["年化"], "真比值": row["比值"], "隨機次數": len(R_),
                       "隨機年化中位": float(R_["年化"].median()), "隨機回落中位": float(R_["最大回落"].median()),
                       "隨機比值（年化中位÷|回落中位|）": float(R_["年化"].median() / abs(R_["最大回落"].median())),
                       "隨機年化 p10": float(R_["年化"].quantile(0.1)), "隨機年化 p90": float(R_["年化"].quantile(0.9)),
                       "p（隨機比值≥真）": float((R_["比值"] >= row["比值"]).mean()), "p（隨機年化≥真）": float((R_["年化"] >= row["年化"]).mean()),
                       "隨機合格率": float((R_["標籤"] == "合格").mean()), "隨機另列率": float((R_["標籤"] == "另列").mean())})
    RBdf = pd.DataFrame(RB)
    lab = {w: next(r["判準標籤"] for r in PORT if r["窗"] == w and r["設定"].startswith("主 乙")) for w in WINS}
    if lab["早年"] == "合格" and lab["主窗"] == "合格":
        tot = "合格"
    elif lab["早年"] in ("合格", "另列") and lab["主窗"] in ("合格", "另列"):
        tot = "另列"
    else:
        tot = "不合格"
    S["乙 判語"] = {"整件（早年、主窗）": tot, "各窗標籤": lab}
    log(f"[乙] {S['乙 判語']}")
    # 0050 主窗基準閘
    bm = next(r for r in PORT if r["窗"] == "主窗")
    S["0050 主窗基準閘"] = {"年化": bm["0050年化"], "最大回落": bm["0050最大回落"], "應為": BENCH_MAIN,
                         "相符（4 位）": bool(round(bm["0050年化"], 4) == BENCH_MAIN[0] and round(bm["0050最大回落"], 4) == BENCH_MAIN[1])}
    if not S["0050 主窗基準閘"]["相符（4 位）"]:
        raise SystemExit(f"⛔ 0050 主窗基準不符：{S['0050 主窗基準閘']}")
    # ── 資料揭露：2330 配股年（權、權息）除權前後 P 的階梯（描述）──
    STEP = []
    vpos = np.flatnonzero(np.isfinite(PR["Pv"]))
    hi_acc = EV[EV["方向"] == "高"]["合併位置"].to_numpy(int)
    for wn in ("早年", "主"):
        c0, c1 = WD[wn]["cal"][0], WD[wn]["cal"][-1]
        for d, kd in WD[wn]["ev2330"]:
            d = pd.Timestamp(d)
            if not (c0 < d <= c1) or "權" not in str(kd):
                continue
            p = int(cal.searchsorted(d))
            bef = vpos[vpos < p - EXCL][-30:]; aft = vpos[vpos > p + EXCL][:30]
            ys = PR["sp"][PR["sp"]["date"].dt.year == d.year]
            STEP.append({"2330 事件日": str(d.date()), "種類": str(kd), "Yahoo ADR 配股": (ys["value"].iloc[0] if len(ys) else "無"),
                         "前 30 有效日 P 中位": float(np.median(PR["Pv"][bef])), "後 30 有效日 P 中位": float(np.median(PR["Pv"][aft])),
                         "階梯": float(np.median(PR["Pv"][aft]) - np.median(PR["Pv"][bef])),
                         "之後 60 個台股日內的高事件數": int(((hi_acc > p) & (hi_acc <= p + 60)).sum())})
    S["資料揭露 配股年 P 階梯（描述）"] = STEP
    log(f"[配股年 P 階梯] {STEP}")
    # ── 描述變體 ──
    VAR = []
    for wname in WINS:
        r, *_ = run_port(Zs[60], TH_MAIN, 0.0, "cash", "描述① Z≤−2 換現金、Z≥0 買回", wname); VAR.append(r)
        for th in (1.5, 2.5):
            r, *_ = run_port(Zs[60], th, 0.0, "2330", f"描述② 乙 Z60 ≥{th} 進、≤0 出", wname); VAR.append(r)
        r, *_ = run_port(Zs[120], TH_MAIN, 0.0, "2330", "描述③ 乙 Z120 ≥2 進、≤0 出", wname); VAR.append(r)
    VARC = []
    for tag, Z, th in (("描述② Z60±1.5", Zs[60], 1.5), ("描述② Z60±2.5", Zs[60], 2.5), ("描述③ Z120±2", Zs[120], 2.0)):
        E2 = event_table(Z, th, tag)
        VARC += cells_of(E2, tag)
    Cdf = pd.DataFrame(CELLS + VARC)
    # ── 輸出 ──
    S["甲 主表（H20）"] = Cdf[(Cdf["設定"] == "主 Z60±2") & (Cdf["H"] == 20)][["窗", "方向", "n", "G", "平均", "中位", "lo975", "hi975", "lo95", "hi95",
                                                                           "扣2330來回0.585%", "隔夜超額平均", "總超額（t收盤起）平均", "隔夜佔總超額（平均之比）",
                                                                           "P 次日變化佔 20 日變化（平均之比）"]].to_dict("records")
    S["乙 主表"] = [{k: r[k] for k in ("窗", "年化", "最大回落", "比值", "年化波動", "進場次數", "每年進場次數", "平均持有天數", "曝險日比例", "窗尾未出場",
                                   "0050年化", "0050最大回落", "0050比值", "判準標籤")} for r in PORT]
    S["假訊號 乙"] = RBdf.to_dict("records")
    S["輸出"] = ["cells.csv", "events.csv", "event_yearly.csv", "premium_yearly.csv", "portfolio.csv", "trades.csv", "random_A.csv", "random_B.csv", "variants.csv", "run.log"]
    S["逐日明細（不進 repo）"] = os.path.join(WORK, "premium_daily.csv")
    S["耗時秒"] = round(time.time() - T0, 1); S["完成（台北）"] = now_tpe()
    Cdf.to_csv(os.path.join(OUT, "cells.csv"), index=False, float_format="%.15g")
    EV.drop(columns=["年"]).to_csv(os.path.join(OUT, "events.csv"), index=False, float_format="%.15g")
    EYdf.to_csv(os.path.join(OUT, "event_yearly.csv"), index=False, float_format="%.15g")
    pd.DataFrame(PY).to_csv(os.path.join(OUT, "premium_yearly.csv"), index=False, float_format="%.15g")
    pd.DataFrame(PORT).to_csv(os.path.join(OUT, "portfolio.csv"), index=False, float_format="%.15g")
    pd.DataFrame(TR).to_csv(os.path.join(OUT, "trades.csv"), index=False, float_format="%.15g")
    RAdf.to_csv(os.path.join(OUT, "random_A.csv"), index=False, float_format="%.15g")
    RBdf.to_csv(os.path.join(OUT, "random_B.csv"), index=False, float_format="%.15g")
    pd.DataFrame(VAR).to_csv(os.path.join(OUT, "variants.csv"), index=False, float_format="%.15g")
    json.dump(S, open(os.path.join(OUT, "UST1.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    log(f"[完成] {S['耗時秒']}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=1)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    lf = open(os.path.join(OUT, "run.log"), "a", encoding="utf-8")

    def log(x):
        print(x, flush=True); lf.write(x + "\n"); lf.flush()
    log(f"══ researchUST1 開跑 {now_tpe()} ══")
    run(a, log)


if __name__ == "__main__":
    main()
