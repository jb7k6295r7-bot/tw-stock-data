# -*- coding: utf-8 -*-
"""C5 描述（裁定線 seq125 ②、seq131；⛔ 不改判定、不計 N）：同窗美國 3 個月國庫券年化，與 C5 並排。

資料：裁定線 20260925-1122 放信箱的 FRED DTB3（2019-09 起），sha256 ＝ f93f5dc5628ad8d138119197eb6cc0dee454eb92f057404172e5fd09d1a35e8a（本支先驗）
取法（seq125 ② 逐字）：C5 同窗每個日曆日取最近一個公布值（前值延續；假日空值 ⛔ 不當 0）；日報酬 ＝ DTB3／100／360；累乘成同窗年化
   ⇒ 同窗＝ C5 的持有期：第 k 期 ＝ close(k) → close(k+1)，用第 k+1 日（期末那一天）的公布值（前值延續）
   ⇒ 年化照 researchc1.cagr（365.25 日曆日）
⚠ 標：折現基礎利率、未換算債券等值收益率；USDT 對美元偏離未處理
"""
import os, sys, json, hashlib
import numpy as np, pandas as pd
sys.path.insert(0, os.path.expanduser("~/tw-p17")); os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchc1 as C, researchc2 as C2, researchc5 as C5, funding as F

SRC = "/mnt/c/SynologyDrive/跨線信箱/資料-FRED_DTB3_2019-09起_裁定線取_shaf93f5dc5628ad8d1-20260925-1122.csv"
SHA = "f93f5dc5628ad8d138119197eb6cc0dee454eb92f057404172e5fd09d1a35e8a"
assert hashlib.sha256(open(SRC, "rb").read()).hexdigest() == SHA, "⛔ DTB3 檔 sha256 不符"
t = pd.read_csv(SRC)
assert list(t.columns) == ["observation_date", "DTB3"], list(t.columns)
t["observation_date"] = pd.to_datetime(t["observation_date"])
s = t.set_index("observation_date")["DTB3"]
cal = pd.date_range("2019-09-01", "2026-09-23", freq="D")
sf = s.reindex(cal).ffill()                                  # 前值延續（⛔ 假日不當 0）
man = F.load_manifest(path=os.path.join(C2.ROOT, "data", "meta", "crypto_funding_manifest.csv"))
R5 = {r["coin"]: r for r in json.load(open("backtest/resultsc5/summary.json", encoding="utf-8"))}
out = {"來源": "FRED DTB3（裁定線 20260925-1122 取）", "sha256": SHA, "標註": "折現基礎利率、未換算債券等值收益率；USDT 對美元偏離未處理"}
for sym in ("BTC", "ETH", "BNB", "SOL"):
    w0, w1 = R5[sym]["窗首（建倉日）"], R5[sym]["窗尾"]
    days = pd.date_range(w0, w1, freq="D")[1:]               # 每一期的期末日
    rate = sf.reindex(days)
    assert rate.notna().all(), f"⛔ {sym} 窗內有取不到的國庫券值"
    r = (rate / 100 / 360).to_numpy()
    tb = C.cagr(r)
    yr = pd.Series(np.cumprod(1 + r), index=days)
    ye = yr.groupby(yr.index.year).last(); prev = ye.shift(1); prev.iloc[0] = 1.0
    out[sym] = {"窗": [w0, w1], "國庫券同窗年化": tb, "C5 淨年化": R5[sym]["主格"]["年化"], "C5 − 國庫券（pp）": (R5[sym]["主格"]["年化"] - tb) * 100,
                "逐年國庫券": {int(k): float(v) for k, v in (ye / prev - 1).items()}, "逐年C5": R5[sym]["逐年"]}
    print("{}：國庫券同窗年化 {:+.2%}｜C5 {:+.2%}｜差 {:+.2f} pp".format(sym, tb, R5[sym]["主格"]["年化"], out[sym]["C5 − 國庫券（pp）"]))
    print("   逐年 國庫券／C5：", {k: "{:+.2%}／{:+.2%}".format(v, R5[sym]["逐年"][str(k)] if str(k) in R5[sym]["逐年"] else R5[sym]["逐年"].get(k, float("nan"))) for k, v in out[sym]["逐年國庫券"].items()})
json.dump(out, open("backtest/resultsc5/tbill_dtb3.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
