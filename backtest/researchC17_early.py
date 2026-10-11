# -*- coding: utf-8 -*-
"""PREREGC17 v2（sha 55523632897472ee，3949 B）早年 BTC 格重報——裁定 seq340 §四：量用 Coin Metrics、日高低准用 Bitstamp，兩個來源都標。

⭐ 讀法寫死：2026-10-11 20:35（台北；20:34:25 WSL `TZ=Asia/Taipei date` 取時後寫）——在算出任何早年新報酬之前寫在這裡；之後只准補「執行時發現」並標時間。
   【執行者補】一律標註。已看過：v1／v2 主格與 max 讀法對帳診斷（diag_lowmax_v2.json，含舊 Bitstamp 替代版早年 +0.257%／天、p 0.066）、
   幣本位重報（btc_coinm.json）、seq333／334／340；本件新資料（CM 量欄）只看過欄位覆蓋與分布，未碰任何報酬。

資料（⛔ 私有原始資料不進 repo；本檔只讀、結果只放彙總，交易清單只放日期與報酬、不放價）：
   私有 ~/us-stock-data（讀工作樹，並核對 blob 與 commit 相同）：
     data/crypto_private/coinmetrics/btc_daily.csv（commit e24d6a79）：PriceUSD、volume_reported_spot_usd_1d ——「資料來源：Coin Metrics Community Data」
     data/crypto_private/BTC.csv 的 bitstamp:btcusd 段（2012）＋ BTC_bitstamp_2013_2017.csv（2013-01-01～2017-08-16）：日高低 ——「資料來源：Bitstamp」
   公開 tw-stock-data main 69e257c882（~/c17data，同 researchC17）：Binance BTCUSDT 日 K（重疊期檢查、2017-08-17 起尾段日高低）。

⭐ 落地讀法
 E1 規則一律照 C17 v2 主臂、重用 researchC17 引擎（signals／simulate／net_series／summary／perm_test／rand_entry_test），出場＝("lowmax",10)
    ＝收盤 ＜ max(訊號日最低, 前 10 日最低) ⇒ 次日開盤平（seq333）；t＋1 開盤進場；持倉中不加碼不重設；成本每邊 0.1%；⛔ 不另寫訊號／出場邏輯。
 E2 早年序列（主）：收盤＝CM PriceUSD（登錄 §一）；量＝CM volume_reported_spot_usd_1d（USD，登錄 §一）；日高低＝Bitstamp（seq340）。
    開盤【執行者補】：CM PriceUSD 是 UTC 日界 00:00 的參考價、市場 24 小時連續 ⇒ open_d＝PriceUSD_{d−1}（＝前一日收盤）；
    因此「t＋1 開盤進場」與「t 收盤進場」價格相同，只差 t＋1 00:00 那筆資金費（皆為代入值）。
 E3 窗：登錄 2013-01-01～2017-12-31。Bitstamp 檔止於 2017-08-16 ⇒ 2017-08-17～12-31 日高低沒有 Bitstamp【執行者補】：
    主格＝登錄全窗，尾段 137 天日高低改用 Binance（登錄 §一 的 BTC 主資料源；接縫標明，等於第三個來源）；
    敏感度＝窗截到 2017-08-16（只有 CM＋Bitstamp 兩源）。兩者都報；出口 ① 以主格判，敏感度若異號加註。
    暖身：20 日均量與前 10 日低用 2012 年資料（CM 與 Bitstamp 2012 段，同來源），窗內第一天＝2013-01-01。
 E4 資金費：早年沒有永續 ⇒ 全部以年化 10%（÷365.25）代入（登錄 §一）；報天數。
 E5 對照：假訊號臂（持倉遮罩循環平移 2,000 次）、隨機進場臂（2,000 次），種子 20260923，各格獨立新 rng。
 E6 出口 ①（登錄 §三）四項：BTC 2018～2023、BTC 2024～、早年 BTC、8 幣合併「每天多賺」都 ＞ 0，且 8 幣合併假訊號 p ＜ 0.05，且方向與加密線 §五 一致。
    其他三項＝v2 max 讀法（researchC17 --fund2019、("lowmax",10)），本檔以同引擎、同 rng 順序重算，並與 diag_lowmax_v2.json 逐位比（不照抄）。
    早年格的方向對照：加密線 §五 對早年只給「固定 14 天之後比平常 +12.0%」⇒ 以同公式（researchC17.recon 的 f14 事件描述）在新序列重算比方向；主臂出場沒有作者數字 ⇒ 出口 ③ 對早年不適用。
    四項成立 ⇒「暫定成立（探索後）」，仍只前瞻（seq340）。
 E7 敏感度（描述）：Bitstamp 開高低收＋CM 量（價格同一所）；舊替代版（Bitstamp 自身量，窗到 2017-08-16）重現；t 收盤進場；鄰格（量倍數×漲幅×出場，前 N 日低一律 max 讀法）。
 E8 給使用者口徑（seq334）：BTC、幣本位全倉，重用 researchC17_btccm.path／measure：W0＝0.0715 BTC、3／24 張（每張 100 USD）固定張數，
    MMR 0.4%，強平以日低（早年沒有標記價 ⇒ 只用現貨日低）；另報「按今日比例」（名目＝k×W0×進場價，k＝n×100÷(W0×2026-10-09 Binance 收盤)）。
    衡量：BTC 計增減、USD 年化與年化÷|MDD| 對只囤幣、逐年加分扣分。⚠ 2013 年 BTC 13 美元時 24 張＝錢包美元值約 2,600 倍 ⇒ 固定張數必然強平，照實報；按今日比例才是可比口徑。
 E9 來源可信度（描述）：
    ⓐ Bitstamp ∩ Binance 日線重疊天數（檔案層面）；
    ⓑ CM ∩ Binance（2017-08-17～2026-10-09）：三版——B＝Binance 全部；C＝CM 收盤與量＋Binance 日高低（仿早年組法）；V＝Binance 價＋CM 量（隔離量源）；
       報訊號一致（兩版都有／只一版有／同日狀態一致率／Jaccard）、交易進場日相同筆數、每天多賺與差（窗 W1、W2、全段；資金費一律 BTCUSDT v2 實際值）；
    ⓒ CM ∩ Bitstamp（2013-01-01～2017-08-16）：PriceUSD 對 Bitstamp 收盤差、量對數相關、CM 量訊號對 Bitstamp 量訊號一致率。
 E10 --check：researchC17_early_check.py（獨立寫法：csv 模組讀檔、純迴圈），重算早年主格與敏感度格的交易清單、每天多賺、幣本位錢包（不解 Lp、直接判權益 ≤ 維持保證金）、
     重疊期訊號計數，逐位比；另兩個會變紅的反例（出場讀成 min、均量含 t）。
⛔ 不寫買賣建議、不寫「開幾張安全」；用語一律「假訊號」。
"""
from __future__ import annotations
import os, sys, json, subprocess, argparse
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import researchC17 as R
import researchC17_btccm as CMW

FROZEN_E = "2026-10-11 20:35（台北；20:34:25 WSL 取時後寫）"
PRIV_REPO = os.path.expanduser("~/us-stock-data")
PRIV = R.PRIV
CM_FILE = os.path.join(PRIV, "coinmetrics", "btc_daily.csv")
CM_COMMIT = "e24d6a79630402da31ea489cf97f1bf742a96e2f"
OUT_E = os.path.join(R.REPO, "backtest", "resultsC17", "early")
EARLY = ("2013-01-01", "2017-12-31")
BS_END = "2017-08-16"
WARM0 = "2012-01-01"
RULE = ("lowmax", 10)
SIG = (2.0, 0.05)
EXITS_E = [("lowmax", 5), ("lowmax", 10), ("lowmax", 20), ("ma", 10), ("ma", 20), ("trail", 0.08), ("trail", 0.12), ("trail", 0.15),
           ("fixed", 7), ("fixed", 14), ("fixed", 28)]
AUTHOR = {"BTC_W1": 0.0030, "BTC_W2": 0.0004, "8幣": {"SOL": .0042, "ADA": .0027, "XRP": .0025, "ETH": .0020, "LINK": .0018, "LTC": .0010, "DOGE": .0007, "BNB": .0006},
          "早年_固定14天之後比平常": 0.120}
SRC_CM = "資料來源：Coin Metrics Community Data（PriceUSD、volume_reported_spot_usd_1d；CC BY-NC 4.0）"
SRC_BS = "資料來源：Bitstamp BTC/USD 日 K（日高低；私有庫，條款禁止散布 ⇒ 只放彙總）"
SRC_BN = "資料來源：Binance BTCUSDT 日 K（公開 tw-stock-data，CC BY-NC-SA 4.0）"


# ───────────────────────── 資料 ─────────────────────────
def _git(*a):
    return subprocess.run(["git", "-C", PRIV_REPO, *a], capture_output=True, text=True).stdout.strip()


def provenance():
    rel = {"cm": "data/crypto_private/coinmetrics/btc_daily.csv", "bs2012": "data/crypto_private/BTC.csv",
           "bs": "data/crypto_private/BTC_bitstamp_2013_2017.csv"}
    out = {"私有庫HEAD": _git("rev-parse", "HEAD")}
    for k, p in rel.items():
        wt = _git("hash-object", p)
        head = _git("rev-parse", f"HEAD:{p}")
        out[k] = {"path": p, "最後改動commit": _git("log", "-1", "--format=%H", "--", p), "工作樹blob": wt, "HEAD_blob": head, "相同": wt == head}
    out["cm"]["CM加量欄commit_e24d6a79_blob"] = _git("rev-parse", f"{CM_COMMIT}:{rel['cm']}")
    assert all(out[k]["相同"] for k in rel), "⛔ 私有檔工作樹與 HEAD 不同"
    assert out["cm"]["工作樹blob"] == out["cm"]["CM加量欄commit_e24d6a79_blob"], "⛔ CM 檔不是 e24d6a79 版"
    return out


def load_cm():
    d = pd.read_csv(CM_FILE, dtype={"date_utc": str})
    d = d.rename(columns={"date_utc": "date"})[["date", "PriceUSD", "volume_reported_spot_usd_1d"]]
    return d.drop_duplicates("date").sort_values("date").reset_index(drop=True)


def load_bs_hl():
    a = pd.read_csv(os.path.join(PRIV, "BTC.csv"), dtype={"date": str})
    a = a[a["source"] == "bitstamp:btcusd"]
    b = pd.read_csv(os.path.join(PRIV, "BTC_bitstamp_2013_2017.csv"), dtype={"date": str})
    d = pd.concat([a[["date", "open", "high", "low", "close", "volume"]], b[["date", "open", "high", "low", "close", "volume"]]])
    d = d.drop_duplicates("date").sort_values("date").reset_index(drop=True)
    assert d["date"].iloc[0] == WARM0 and d["date"].iloc[-1] == BS_END and R._consec(d["date"]), "⛔ Bitstamp 段有缺日或起訖不符"
    d["src"] = "bitstamp"
    return d


def load_bn_raw():
    d = pd.read_csv(os.path.join(R.ROOT, "data", "crypto", "BTC.csv"), dtype={"date": str})
    d = d.drop_duplicates("date").sort_values("date")
    return d[d["date"] <= R.END].reset_index(drop=True)


def build_early(price="cm", hl_tail=True, end=EARLY[1]):
    """price＝cm：收盤 CM PriceUSD、開盤＝前一日 PriceUSD；price＝bs：Bitstamp（尾段 Binance）開高低收。量一律 CM。"""
    cm = load_cm()
    bs = load_bs_hl()
    hl = bs
    if hl_tail and end > BS_END:
        bn = load_bn_raw()
        bn = bn[(bn["date"] > BS_END) & (bn["date"] <= end)][["date", "open", "high", "low", "close", "volume"]].copy()
        bn["src"] = "binance"
        hl = pd.concat([bs, bn]).reset_index(drop=True)
    hl = hl[hl["date"] <= end]
    d = hl.merge(cm, on="date", how="left", validate="1:1")
    assert d["PriceUSD"].notna().all() and d["volume_reported_spot_usd_1d"].notna().all(), "⛔ CM 有缺"
    assert R._consec(d["date"]) and d["date"].iloc[0] == WARM0 and d["date"].iloc[-1] == end
    if price == "cm":
        px = d["PriceUSD"].astype(float).to_numpy()
        d = d.assign(close=px, open=np.r_[px[0], px[:-1]])
    s = R._pack(f"BTC_early_{price}", d, d["volume_reported_spot_usd_1d"].astype(float).to_numpy())
    s["hlsrc"] = d["src"].to_numpy(str)
    R.attach_funding(s, None)
    s["mlow"] = np.full(len(s["close"]), np.nan)
    return s


def build_old():
    s = R.attach_funding(R.load_bitstamp(), None)
    return s


# ───────────────────────── 單格 ─────────────────────────
def trade_rows_public(s, run):
    """只放日期、天數、報酬、最大浮虧（⛔ 不放價）。"""
    rows = R.trade_table(s, run["trades"], run["net"])
    return [{"signal": r["signal"], "entry": r["entry"], "exit": r["exit"], "days": r["days"], "ret": r["ret"], "maxdd": r["maxdd"],
             "open_at_end": r["open_at_end"]} for r in rows]


def cell(s, a, b, seed_off, mode="open", controls=True, vm=SIG[0], up=SIG[1], rule=RULE):
    i0, i1 = R.window_idx(s, a, b)
    r = R.unit_run(s, i0, i1, vm, up, rule, mode)
    out = {"摘要": R.summary(s, r, i0, i1, mode)}
    if controls:
        rng = np.random.default_rng(R.SEED + seed_off)
        p1, v1 = R.perm_test([(R.sub(s, i0, i1), r["held"][i0:i1 + 1].copy(), r["wmean"])], r["excess"], rng, mode)
        rows = R.trade_table(s, r["trades"], r["net"], mode)
        p2, v2 = R.rand_entry_test([(R.sub(s, i0, i1), [x["days"] for x in rows], [x["open_at_end"] for x in rows], r["wmean"])], r["excess"], rng)
        out["對照"] = {"假訊號p": p1, "假訊號中位": float(np.median(v1)), "假訊號95分位": float(np.quantile(v1, 0.95)),
                     "隨機進場p": p2, "隨機進場中位": float(np.median(v2)), "隨機進場95分位": float(np.quantile(v2, 0.95))}
    return out, (i0, i1, r)


def f14_event(s, a, b):
    """同 researchC17.recon：訊號後 14 天報酬 − 窗內全部日 14 天報酬（事件描述，訊號不管持倉）。"""
    i0, i1 = R.window_idx(s, a, b)
    sg = R.signals(s, *SIG)
    c = s["close"]
    f14 = np.r_[c[14:] / c[:-14] - 1.0, np.full(14, np.nan)]
    idx = [t for t in range(i0, i1 - 13) if sg[t]]
    return {"訊號後14天_減_全部日": float(np.nanmean(f14[idx]) - np.nanmean(f14[i0:i1 - 13])) if idx else None, "訊號天數": len(idx)}


# ───────────────────────── 其他三項（v2 max）同引擎重算 ─────────────────────────
def other_three():
    R.FUND2019 = True
    btc, early_old, coins = R.build_units("BTCUSDT")
    res = R.run_cell(btc, early_old, coins, *SIG, RULE, "open")
    rng = np.random.default_rng(R.SEED)          # 與 main_run 同 rng 消耗順序 ⇒ p 可逐位重現
    ctrl = {}
    for k in ("BTC_W1", "BTC_W2", "BTC_early_bitstamp"):
        s, i0, i1, r = res[k]
        p1, _ = R.perm_test([(R.sub(s, i0, i1), r["held"][i0:i1 + 1].copy(), r["wmean"])], r["excess"], rng)
        rows = R.trade_table(s, r["trades"], r["net"])
        p2, _ = R.rand_entry_test([(R.sub(s, i0, i1), [x["days"] for x in rows], [x["open_at_end"] for x in rows], r["wmean"])], r["excess"], rng)
        ctrl[k] = {"假訊號p": p1, "隨機進場p": p2}
    mg = R.merged(res)
    uc = [(R.sub(s, i0, i1), r["held"][i0:i1 + 1].copy(), r["wmean"]) for k, (s, i0, i1, r) in res.items() if k in R.COINS8]
    p1, _ = R.perm_test(uc, mg["每天多賺"], rng)
    ctrl["8幣合併"] = {"假訊號p": p1}
    out = {"BTC_W1": {"每天多賺": res["BTC_W1"][3]["excess"], **ctrl["BTC_W1"], "筆數": len(res["BTC_W1"][3]["trades"])},
           "BTC_W2": {"每天多賺": res["BTC_W2"][3]["excess"], **ctrl["BTC_W2"], "筆數": len(res["BTC_W2"][3]["trades"])},
           "8幣合併": {"每天多賺": mg["每天多賺"], "各幣等權": mg["各幣等權"], "筆數": mg["筆數"], **ctrl["8幣合併"]},
           "8幣各幣": {c: res[c][3]["excess"] for c in R.COINS8},
           "舊替代版早年_bitstamp量": {"每天多賺": res["BTC_early_bitstamp"][3]["excess"], **ctrl["BTC_early_bitstamp"]}}
    D = json.load(open(os.path.join(R.OUT, "diag_lowmax_v2.json"), encoding="utf-8"))
    cmp = []
    for k, dk in (("BTC_W1", "BTC_W1"), ("BTC_W2", "BTC_W2"), ("8幣合併", "8幣合併")):
        cmp.append({"項": k, "每天多賺差": abs(out[k]["每天多賺"] - D["主格"][dk]["每天多賺"]), "假訊號p差": abs(out[k]["假訊號p"] - D["對照"][dk]["假訊號p"])})
    cmp.append({"項": "舊替代版早年", "每天多賺差": abs(out["舊替代版早年_bitstamp量"]["每天多賺"] - D["主格"]["BTC_early_bitstamp"]["每天多賺"]),
                "假訊號p差": abs(out["舊替代版早年_bitstamp量"]["假訊號p"] - D["對照"]["BTC_early_bitstamp"]["假訊號p"])})
    out["與diag_lowmax_v2逐位比"] = cmp
    out["逐位相同"] = all(x["每天多賺差"] < 1e-15 and x["假訊號p差"] < 1e-15 for x in cmp)
    return out, btc


# ───────────────────────── 幣本位（seq334）─────────────────────────
def coinm_block(s, i0, i1, trades, close_today):
    out = {}
    for n in CMW.SIZES:
        for tag, ratio in (("固定", None), ("按今日比例", n * CMW.FACE / (CMW.W0 * close_today))):
            P = CMW.path(s, i0, i1, trades, n, "spot", ratio)
            m = CMW.measure(s, i0, i1, P)
            md = float(min(r["min_dist"] for r in P["rows"])) if P["rows"] else None
            out[f"{n}張_{tag}"] = {"比例k": ratio, "窗末錢包權益BTC": P["W_end"], "對只囤幣增減BTC": P["W_end"] - CMW.W0, "增減÷W0": (P["W_end"] - CMW.W0) / CMW.W0,
                                 "累計資金費BTC": P["fund_paid"], "累計手續費BTC": P["fees"], "強平日": P["liq_day"],
                                 "觸及強平筆數": int(sum(r["touched"] for r in P["rows"])), "實際走到的筆數": len(P["rows"]),
                                 "最近距強平": md, "最低點還要再跌才強平": (md / (1 + md)) if (md is not None and md > 0) else None,
                                 "USD_囤幣加訊號": m["USD_囤幣加訊號"], "USD_只囤幣": m["USD_只囤幣"], "使用者判準": m["使用者判準"],
                                 "逐年": [{k: v for k, v in y.items()} for y in m["逐年"]]}
    return out


# ───────────────────────── 來源可信度 ─────────────────────────
def sig_agree(sa, sb, i0, i1):
    a, b = sa[i0:i1 + 1], sb[i0:i1 + 1]
    both, oa, ob = int((a & b).sum()), int((a & ~b).sum()), int((~a & b).sum())
    return {"A訊號天數": int(a.sum()), "B訊號天數": int(b.sum()), "兩版都有": both, "只A": oa, "只B": ob,
            "同日狀態一致率": float((a == b).mean()), "Jaccard": (both / (both + oa + ob)) if (both + oa + ob) else None}


def overlap_cm_binance(btc_fund_src):
    bn = load_bn_raw()
    cm = load_cm()
    d = bn.merge(cm, on="date", how="left", validate="1:1")
    assert d["PriceUSD"].notna().all() and d["volume_reported_spot_usd_1d"].notna().all()
    B = R._pack("B_binance", d, d["quote_volume"].astype(float).to_numpy())
    px = d["PriceUSD"].astype(float).to_numpy()
    dc = d.assign(close=px, open=np.r_[px[0], px[:-1]])
    C = R._pack("C_cm_px_vol", dc, d["volume_reported_spot_usd_1d"].astype(float).to_numpy())
    V = R._pack("V_binance_px_cm_vol", d, d["volume_reported_spot_usd_1d"].astype(float).to_numpy())
    for s in (B, C, V):
        R.attach_funding(s, btc_fund_src)
    sg = {k: R.signals(s, *SIG) for k, s in (("B", B), ("C", C), ("V", V))}
    out = {"期間": f"{d['date'].iloc[0]}～{d['date'].iloc[-1]}", "版本": {"B": "Binance 收盤與量（C17 主）", "C": "CM 收盤與量＋Binance 日高低（仿早年組法）",
                                                                     "V": "Binance 開高低收＋CM 量（隔離量源）"},
           "收盤差_CM對Binance": {"中位|差|": float(np.median(np.abs(px / B["close"] - 1))), "最大|差|": float(np.max(np.abs(px / B["close"] - 1))),
                              "最大日": str(d["date"].iloc[int(np.argmax(np.abs(px / B["close"] - 1)))])},
           "量對數相關_CM對Binance": float(np.corrcoef(np.log(d["volume_reported_spot_usd_1d"].astype(float)), np.log(d["quote_volume"].astype(float)))[0, 1]),
           "CM收盤落在Binance高低外天數": int(((px > B["high"] * (1 + 1e-12)) | (px < B["low"] * (1 - 1e-12))).sum()),
           "窗": {}}
    for wk, (a, b) in (("全段", (d["date"].iloc[0], R.END)), ("BTC_W1", R.W1), ("BTC_W2", R.W2)):
        i0, i1 = R.window_idx(B, a, b)
        w = {"窗": f"{B['dates'][i0]}～{B['dates'][i1]}", "訊號_B對C": sig_agree(sg["B"], sg["C"], i0, i1), "訊號_B對V": sig_agree(sg["B"], sg["V"], i0, i1)}
        runs = {k: R.unit_run(s, i0, i1, *SIG, RULE, "open") for k, s in (("B", B), ("C", C), ("V", V))}
        for k in ("B", "C", "V"):
            w[f"每天多賺_{k}"] = runs[k]["excess"]; w[f"筆數_{k}"] = len(runs[k]["trades"])
        eb = set(B["dates"][t["e"]] for t in runs["B"]["trades"])
        for k in ("C", "V"):
            ek = set(B["dates"][t["e"]] for t in runs[k]["trades"])
            w[f"進場日相同筆數_B對{k}"] = len(eb & ek)
            w[f"每天多賺差_{k}減B"] = runs[k]["excess"] - runs["B"]["excess"]
            hb, hk = runs["B"]["held"][i0:i1 + 1], runs[k]["held"][i0:i1 + 1]
            w[f"持有日重疊率_B對{k}"] = float((hb & hk).sum() / max((hb | hk).sum(), 1))
        out["窗"][wk] = w
    return out


def overlap_cm_bitstamp(old):
    cm = load_cm()
    bs = load_bs_hl()
    d = bs.merge(cm, on="date", how="left", validate="1:1")
    d = d[(d["date"] >= "2013-01-01")].reset_index(drop=True)
    px = d["PriceUSD"].astype(float).to_numpy(); c = d["close"].astype(float).to_numpy()
    out = {"期間": f"{d['date'].iloc[0]}～{d['date'].iloc[-1]}",
           "收盤差_CM對Bitstamp": {"中位|差|": float(np.median(np.abs(px / c - 1))), "最大|差|": float(np.max(np.abs(px / c - 1))),
                               "最大日": str(d["date"].iloc[int(np.argmax(np.abs(px / c - 1)))]),
                               ">2%天數": int((np.abs(px / c - 1) > 0.02).sum()), ">5%天數": int((np.abs(px / c - 1) > 0.05).sum())},
           "量對數相關_CM對Bitstamp美元量_排除量0日": float(np.corrcoef(np.log(d.loc[d["volume"] > 0, "volume_reported_spot_usd_1d"].astype(float)),
                                                             np.log((d.loc[d["volume"] > 0, "volume"] * d.loc[d["volume"] > 0, "close"]).astype(float)))[0, 1]),
           "Bitstamp量為0天數": int((d["volume"] <= 0).sum()),
           "CM收盤落在Bitstamp高低外天數": int(((px > d["high"].to_numpy() * (1 + 1e-12)) | (px < d["low"].to_numpy() * (1 - 1e-12))).sum())}
    # 訊號：新版（CM 收盤＋量，窗到 08-16）對舊替代版（Bitstamp 收盤＋自身量）
    s_new = build_early("cm", False, BS_END)
    i0n, i1n = R.window_idx(s_new, "2013-01-21", BS_END)       # 舊替代版窗起點 2013-01-21（Bitstamp 檔第 21 天）
    i0o, i1o = R.window_idx(old, "2013-01-01", BS_END)
    assert s_new["dates"][i0n] == old["dates"][i0o] and s_new["dates"][i1n] == old["dates"][i1o]
    sn = R.signals(s_new, *SIG)[i0n:i1n + 1]; so = R.signals(old, *SIG)[i0o:i1o + 1]
    out["訊號_舊替代版(A)對CM新版(B)"] = sig_agree(so, sn, 0, len(so) - 1)
    out["訊號_舊替代版(A)對CM新版(B)"]["窗"] = f"{old['dates'][i0o]}～{old['dates'][i1o]}"
    s_v = build_early("bs", False, BS_END)                      # Bitstamp 價＋CM 量：只換量源
    sv = R.signals(s_v, *SIG)[i0n:i1n + 1]
    out["訊號_舊替代版(A)對Bitstamp價CM量(B)"] = sig_agree(so, sv, 0, len(so) - 1)
    return out


# ───────────────────────── 主流程 ─────────────────────────
def run(stamp):
    os.makedirs(OUT_E, exist_ok=True)
    J = {"性質": "PREREGC17 v2 早年格重報（裁定 seq340 §四）；探索後確認 ⇒ 結論最多「暫定成立（探索後）」，乾淨證據只有前瞻",
         "讀法寫死": FROZEN_E, "寫檔時間": stamp, "登錄": "PREREGC17 v2 sha55523632897472ee 3949B", "出場讀法": "max（seq333）",
         "資料來源": {"量與收盤": SRC_CM, "日高低": SRC_BS, "尾段日高低_2017-08-17起": SRC_BN, "BTC兩窗與8幣": SRC_BN},
         "私有資料出處": provenance(), "公開資料commit": R.SHA}
    # 早年主格與敏感度
    s_main = build_early("cm", True, EARLY[1])
    s_bs2 = build_early("cm", False, BS_END)
    s_px = build_early("bs", True, EARLY[1])
    s_px2 = build_early("bs", False, BS_END)
    i0, i1 = R.window_idx(s_main, *EARLY)
    J["早年覆蓋"] = {"窗": f"{s_main['dates'][i0]}～{s_main['dates'][i1]}", "窗天數": i1 - i0 + 1,
                 "日高低_Bitstamp天數": int((s_main["hlsrc"][i0:i1 + 1] == "bitstamp").sum()),
                 "日高低_Binance尾段天數": int((s_main["hlsrc"][i0:i1 + 1] == "binance").sum()),
                 "暖身起": WARM0, "CM缺": 0, "資金費代入天數": int(s_main["fmiss"][i0:i1 + 1].sum()),
                 "CM收盤落在日高低外天數": int(((s_main["close"] > s_main["high"] * (1 + 1e-12)) | (s_main["close"] < s_main["low"] * (1 - 1e-12)))[i0:i1 + 1].sum())}
    cells = {}
    cells["主格_CM價量_日高低Bitstamp接Binance_全窗"], (a0, a1, rmain) = cell(s_main, *EARLY, 101)
    cells["敏感度_CM價量_日高低Bitstamp_窗到0816"], (b0, b1, rbs2) = cell(s_bs2, EARLY[0], BS_END, 102)
    cells["敏感度_Bitstamp開高低收_CM量_全窗"], _ = cell(s_px, *EARLY, 103)
    cells["敏感度_Bitstamp開高低收_CM量_窗到0816"], _ = cell(s_px2, EARLY[0], BS_END, 104)
    cells["敏感度_t收盤進場_主序列"], _ = cell(s_main, *EARLY, 105, mode="close", controls=False)
    J["早年格"] = cells
    J["早年主格交易清單_只日期與報酬"] = trade_rows_public(s_main, rmain)
    J["早年敏感度0816交易清單_只日期與報酬"] = trade_rows_public(s_bs2, rbs2)
    J["早年_固定14天事件描述"] = {"主序列": f14_event(s_main, *EARLY), "窗到0816": f14_event(s_bs2, EARLY[0], BS_END), "作者§五": AUTHOR["早年_固定14天之後比平常"]}
    # 逐年（1 單位名目，描述）
    yr = {}
    for d in range(a0, a1 + 1):
        if rmain["held"][d]:
            yr.setdefault(s_main["dates"][d][:4], []).append(rmain["net"][d] - rmain["wmean"])
    J["早年主格_逐年每天多賺_描述"] = {y: {"持有日": len(v), "每天多賺(對全窗平均)": float(np.mean(v))} for y, v in sorted(yr.items())}
    # 鄰格（描述）
    nb = []
    for vm in (1.5, 2.0, 2.5):
        for up in (0.04, 0.05, 0.07):
            for rule in EXITS_E:
                if rule != RULE and (vm, up) != SIG:
                    continue
                c0, (_, _, rr) = cell(s_main, *EARLY, 0, controls=False, vm=vm, up=up, rule=rule)
                nb.append({"量倍數": vm, "漲幅": up, "出場": f"{rule[0]}{rule[1]}", "主格": (vm, up) == SIG and rule == RULE,
                           "每天多賺": c0["摘要"]["每天多賺"], "筆數": c0["摘要"]["筆數"]})
    J["早年鄰格_描述不判"] = nb
    # 其他三項重算
    o3, btc = other_three()
    J["其他三項_v2max同引擎重算"] = o3
    # 出口 ①
    e_main = cells["主格_CM價量_日高低Bitstamp接Binance_全窗"]["摘要"]["每天多賺"]
    e_bs2 = cells["敏感度_CM價量_日高低Bitstamp_窗到0816"]["摘要"]["每天多賺"]
    f14 = J["早年_固定14天事件描述"]["主序列"]["訊號後14天_減_全部日"]
    dir_ok = {"BTC_W1": o3["BTC_W1"]["每天多賺"] * AUTHOR["BTC_W1"] > 0, "BTC_W2": o3["BTC_W2"]["每天多賺"] * AUTHOR["BTC_W2"] > 0,
              "8幣各幣": all(o3["8幣各幣"][c] * v > 0 for c, v in AUTHOR["8幣"].items()),
              "早年(固定14天事件)": (f14 or 0) * AUTHOR["早年_固定14天之後比平常"] > 0}
    items = [("① BTC 2018～2023 每天多賺 > 0", o3["BTC_W1"]["每天多賺"]), ("② BTC 2024～2026-10-09 每天多賺 > 0", o3["BTC_W2"]["每天多賺"]),
             ("③ 早年 BTC 每天多賺 > 0（主格）", e_main), ("④ 8 幣合併每天多賺 > 0", o3["8幣合併"]["每天多賺"])]
    four = [{"項": k, "值": v, "成立": bool(v > 0)} for k, v in items]
    p_ok = o3["8幣合併"]["假訊號p"] < 0.05
    ok = all(x["成立"] for x in four) and p_ok and all(dir_ok.values())
    J["出口①"] = {"四項": four, "8幣合併假訊號p": o3["8幣合併"]["假訊號p"], "p<0.05": bool(p_ok), "方向與加密線§五一致": dir_ok,
                 "早年敏感度_窗到0816（只兩源）": {"值": e_bs2, "同號": bool(e_bs2 > 0) == bool(e_main > 0)},
                 "判": ("暫定成立（探索後）——仍只前瞻（seq340）" if ok else "未達出口 ①（見各項）"),
                 "註": ["BTC 2024～ 雖 > 0 但近 0（p 見其他三項）；seq334：照實寫「近兩年沒有提升」",
                       "早年格主臂出場無作者數字 ⇒ 出口 ③ 對早年不適用；方向以作者唯一早年數字（固定 14 天事件）比",
                       "N 不變（seq330／333／334）；鄰格描述不計"]}
    # 幣本位（seq334）
    bn = R.load_binance("BTC", drop30=False)
    close_today = float(bn["close"][-1])
    J["幣本位_seq334口徑_早年"] = {"說明": "BTC、幣本位全倉；W0 0.0715 BTC；MMR 0.4%；早年無永續 ⇒ 資金費年化 10% 代入；強平用日低（主序列＝Bitstamp，尾段 Binance）；無標記價",
                              "2026-10-09_Binance收盤": close_today,
                              "主格全窗": coinm_block(s_main, a0, a1, rmain["trades"], close_today),
                              "敏感度窗到0816": coinm_block(s_bs2, b0, b1, rbs2["trades"], close_today)}
    BC = json.load(open(os.path.join(R.OUT, "btc_coinm.json"), encoding="utf-8"))
    J["幣本位_兩窗_照抄btc_coinm.json"] = {lab: {n: {k: BC["窗"][lab][n].get(k) for k in ("窗末錢包權益BTC", "增減÷W0", "強平日", "觸及強平筆數", "使用者判準")}
                                             for n in ("3張", "24張", "3張_按今日比例", "24張_按今日比例")} for lab in BC["窗"]}
    # 來源可信度
    J["來源可信度"] = {
        "ⓐ_Bitstamp與Binance日線重疊": {"天數": int(len(set(load_bs_hl()["date"]) & set(load_bn_raw()["date"]))),
                                    "說明": "私有 Bitstamp 檔止於 2017-08-16、公開 Binance 起於 2017-08-17 ⇒ 檔案層面無重疊；以 ⓑ、ⓒ 代替"},
        "ⓑ_CM與Binance": overlap_cm_binance(R.fund_src("BTCUSDT")),
        "ⓒ_CM與Bitstamp": overlap_cm_bitstamp(build_old())}
    with open(os.path.join(OUT_E, "C17_early.json"), "w", encoding="utf-8") as f:
        json.dump(R.to_jsonable(J), f, ensure_ascii=False, indent=1)
    return J


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--stamp", default="")
    a = ap.parse_args()
    J = run(a.stamp)
    print("OK", a.stamp, J["出口①"]["判"])
