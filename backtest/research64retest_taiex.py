# -*- coding: utf-8 -*-
"""六四 v1 重測 ④：1990 起加權指數合成壓力（1990 崩盤、2000～2002 長空頭）。回測線，2026-09-28。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.research64retest_taiex --src ~/msdata/us_macro/<sha>
    獨立查核：~/tw-p16/.venv/bin/python backtest/research64retest_taiex_check.py --src …

資料（⛔ 原始資料不進 repo；只放 repo 外 ~/msdata/us_macro/<commit sha>/，本檔只寫彙總）：
  私有 repo jb7k6295r7-bot/us-stock-data 的 data/macro/twse_taiex.csv（加權指數日收盤，1990-01-04 起）、
  cbc_EG41M01_money_market_monthly.csv（商業本票等月資料）、cbc_EG37D01_interbank_daily.csv（拆款日資料，1991-10 起）；
  美國 DTB3 ＝ 跨線信箱 DTB3.csv（③ 同一份）
合成（⚠ 逐字標註）：
  ・0050 代理 ＝ 加權指數日報酬（⚠ 價格指數、不含息）；另報「加年 3% 股息近似」＝ 每日報酬＋3%／245（描述）
  ・正2 ＝ 2 × 日報酬 − 經理費 0.3%／年 ÷ 245 − 資金成本 年利率 ÷ 245 ×（2−1）
  ・⚠ 指數沒有開盤價 ⇒ 開盤以前一日收盤代（＝ 前一日收盤成交；隔夜跳空不計）
  ・⚠ 早年有週六交易日 ⇒ 交易日照指數檔；年化仍用 245 日／年（全專案口徑）
  ・資金成本：不扣｜DTB3（美國 3 個月國庫券；t−1 以前最近一筆）｜台灣商業本票初級市場 1-30 天（月資料；月內各日用【上個月】的值）｜
             台灣拆款隔夜加權平均（日資料 1991-10 起；t−1 以前最近一筆；1990 窗無資料 ⇒ 不適用）｜固定 1%／2%／3%
六四 v1 ＝ 0050 代理 60%＋合成正2 40%、每年 1 月第一個交易日調回、ETF 成本 0.385%（researchMix70.sim 同一支）
壓力窗（100 萬起）：
  ① 1990：1990-01-05～1990-12-31（指數檔首日 01-04 的次一日起：01-04 沒有「前一日收盤」可當開盤；1990-02 見頂、1990-10 見底都在窗內）
  ② 2000～2002：2000-01-04～2002-12-31
  各窗報：窗內最慘剩多少（100 萬在窗首）、窗內最大回落（高點到谷底）與是否超過使用者上限 −70%
並列：一直抱合成正2、一直抱 0050 代理、PREREG低頻擇時三格（甲 D200_a、乙 s40_L60_a、丙 B_x20_R2_M；researchLowFreq 同一套規則，
      指標改用加權指數算；⚠ 1990 窗在指數檔首日起算、長均線與 250 日高還算不出來 ⇒ 1990 窗低頻擇時【不適用】）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os

import numpy as np
import pandas as pd

from . import researchLev2 as L2
from . import researchMix70 as MX
from . import researchLowFreq as LF

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results64retest")
DTB3 = "/mnt/c/SynologyDrive/跨線信箱/DTB3.csv"
WINS = {"① 1990": ("1990-01-05", "1990-12-31"), "② 2000～2002": ("2000-01-04", "2002-12-31"),
        "③ 2008（2006-09-12～2014-12-31，同 researchMix70 壓力窗）": ("2006-09-12", "2014-12-31"), "③b 2008-01～2009-03": ("2008-01-02", "2009-03-31")}
LIMIT = -0.70
FEE = 0.003
DIV = 0.03
PK = {"甲": ("甲", "D200_a"), "乙": ("乙", "s40_L60_a"), "丙": ("丙", "B_x20_R2_M")}


def manifest(src):
    """us-stock-data data/macro/_manifest.csv 的對應列（由 ~/us-stock-data 的同一 commit 讀；只記 sha 與起訖）。"""
    import subprocess
    try:
        txt = subprocess.run(["git", "-C", os.path.expanduser("~/us-stock-data"), "show", f"{os.path.basename(os.path.normpath(src))}:data/macro/_manifest.csv"],
                             capture_output=True, text=True, check=True).stdout
        m = pd.read_csv(__import__("io").StringIO(txt))
        m = m[m["series"].isin(["twse_taiex.csv", "cbc_EG41M01_money_market_monthly.csv", "cbc_EG37D01_interbank_daily.csv"])]
        return {r["series"]: {"rows": int(r["rows"]), "first": r["first"], "last": r["last"], "sha256": r["sha256"], "fetched_at": r["fetched_at"],
                              "與取出檔一致": sha(os.path.join(src, r["series"])) == r["sha256"]} for _, r in m.iterrows()}
    except Exception as e:
        return {"讀取失敗": str(e)}


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def daily_lag(dates, s, cal):
    """s：Series（index 日期字串、值 年利率 %）⇒ 每個 cal 日用 < 該日 的最近一筆（小數）。"""
    ds = list(s.index); vs = s.to_numpy(float); out = np.full(len(cal), np.nan); j = -1; k = 0
    for t, d in enumerate(cal):
        while k < len(ds) and ds[k] < d:
            j = k; k += 1
        out[t] = vs[j] / 100.0 if j >= 0 else np.nan
    return out


def rates(src, cal):
    R = {"不扣資金成本": np.zeros(len(cal))}
    d = pd.read_csv(DTB3); d.columns = ["date", "v"]; d["v"] = pd.to_numeric(d["v"], errors="coerce"); d = d.dropna()
    R["DTB3（美國 3 個月國庫券，代）"] = daily_lag(None, d.set_index("date")["v"], cal)
    m = pd.read_csv(os.path.join(src, "cbc_EG41M01_money_market_monthly.csv"), dtype={"month": str})
    col = "商業本票-初級市場-1-30天"
    mm = m.set_index("month")[col].apply(pd.to_numeric, errors="coerce")
    cp = np.full(len(cal), np.nan)
    for t, dd in enumerate(cal):
        y, mo = int(dd[:4]), int(dd[5:7]); py, pm = (y - 1, 12) if mo == 1 else (y, mo - 1)
        v = mm.get(f"{py}-{pm:02d}", np.nan)
        cp[t] = v / 100.0 if np.isfinite(v) else np.nan
    R["台灣商業本票初級 1-30 天（上個月）"] = cp
    ib = pd.read_csv(os.path.join(src, "cbc_EG37D01_interbank_daily.csv"), dtype={"date": str})
    R["台灣拆款隔夜加權平均"] = daily_lag(None, ib.set_index("date")["隔夜-加權平均"].apply(pd.to_numeric, errors="coerce").dropna(), cal)
    for x in (0.01, 0.02, 0.03):
        R[f"固定 {int(x * 100)}%"] = np.full(len(cal), x)
    return R


def synth(c, rate, div=0.0):
    """回 (O0050, C0050, Olev, Clev)：0050 代理（含股息近似時為總報酬近似）與合成正2；開盤 ＝ 前一日收盤。"""
    n = len(c); r = np.r_[np.nan, c[1:] / c[:-1] - 1.0] + div / 245
    C0 = np.full(n, np.nan); C0[0] = 1.0
    CL = np.full(n, np.nan)
    rf = pd.Series(rate).ffill().to_numpy()            # 利率開始有值之後才起算正2（之前 NaN ⇒ 該窗不適用）
    k0 = int(np.flatnonzero(np.isfinite(rf))[0]) if np.isfinite(rf).any() else n
    if k0 < n:
        CL[k0] = 1.0
    for t in range(1, n):
        C0[t] = C0[t - 1] * (1 + r[t])
        if t > k0:
            CL[t] = CL[t - 1] * (1 + 2 * r[t] - FEE / 245 - rf[t] / 245 * (2 - 1))
    O0 = np.r_[np.nan, C0[:-1]]; OL = np.r_[np.nan, CL[:-1]]
    return O0, C0, OL, CL


def worst(eq):
    p = np.r_[1.0, eq]; pk = np.maximum.accumulate(p)
    return float(p.min() * 100), float(((p - pk) / pk).min())


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--src", required=True); a = ap.parse_args()
    src = os.path.expanduser(a.src)
    tx = pd.read_csv(os.path.join(src, "twse_taiex.csv"), dtype={"date": str})
    tx["close"] = pd.to_numeric(tx["close"], errors="coerce"); tx = tx.dropna(subset=["close"]).drop_duplicates("date").sort_values("date").reset_index(drop=True)
    cal = tx["date"].tolist(); c = tx["close"].to_numpy(float); n = len(cal); pos = {d: i for i, d in enumerate(cal)}
    RT = rates(src, cal)
    srcinfo = {"repo": "jb7k6295r7-bot/us-stock-data", "commit": os.path.basename(os.path.normpath(src)),
               "檔案 sha256": {f: sha(os.path.join(src, f)) for f in ("twse_taiex.csv", "cbc_EG41M01_money_market_monthly.csv", "cbc_EG37D01_interbank_daily.csv")},
               "DTB3 sha256": sha(DTB3), "manifest": manifest(src), "指數列數": n, "指數起訖": [cal[0], cal[-1]], "週六交易日數": int(sum(pd.Timestamp(d).dayofweek == 5 for d in cal))}
    rows = []; LFNA = {}
    for divn, dv in (("價格指數（不含息）", 0.0), ("加年 3% 股息近似（描述）", DIV)):
        for rn, rt in RT.items():
            O0, C0, OL, CL = synth(c, rt, dv)
            O = {"0050": O0, "LEV": OL}; C = {"0050": C0, "LEV": CL}
            G = {"cal": np.array(cal), "pos": pos, "O": {"0050": O0, "SYN": OL, "00631L": OL}, "C": {"0050": C0, "SYN": CL, "00631L": CL}}
            I = LF.indicators(G)
            try:
                _, WS, g0, _ = LF.build(G, I)
            except Exception as e:                    # 期間端點不在指數日曆（不影響本件兩窗）⇒ 自建權重
                raise
            for wn, (a0, a1) in WINS.items():
                i0 = int(np.searchsorted(cal, a0)); i1 = int(np.searchsorted(cal, a1, side="right")) - 1   # 窗端點取窗內第一／最後一個交易日
                if not np.isfinite(OL[i0]) or not np.isfinite(CL[i0:i1 + 1]).all():
                    for nm in ("六四 v1", "一直抱合成正2", "一直抱 0050 代理"):
                        rows.append({"股息": divn, "資金成本": rn, "窗": wn, "對象": nm, "狀態": "利率無資料 ⇒ 不適用"})
                    continue
                for nm, assets, w in (("六四 v1", ("0050", "LEV"), (0.6, 0.4)), ("一直抱合成正2", ("LEV",), (1.0,)), ("一直抱 0050 代理", ("0050",), (1.0,))):
                    eq, acts, crel, dl = MX.sim(assets, w, i0, i1, O, C, cal, "Y", 1)
                    lo, mdd = worst(eq); cagr = float(eq[-1] ** (245 / len(eq)) - 1)
                    rows.append({"股息": divn, "資金成本": rn, "窗": wn, "對象": nm, "狀態": "", "窗內最慘剩（萬，100 萬起）": lo, "窗內最大回落": mdd,
                                 "超過−70%": bool(mdd < LIMIT), "期末（萬）": float(eq[-1] * 100), "年化": cagr})
                for f, key in PK.values():
                    W = WS[(f, key)][0]
                    if not np.isfinite(W[i0:i1 + 1]).all():
                        rows.append({"股息": divn, "資金成本": rn, "窗": wn, "對象": f"低頻擇時 {f} {key}", "狀態": "指標還算不出來 ⇒ 不適用"}); LFNA[wn] = True
                        continue
                    r = LF.run_seg(G, W, i0, i1, "SYN")
                    lo, mdd = worst(r["eq"])
                    rows.append({"股息": divn, "資金成本": rn, "窗": wn, "對象": f"低頻擇時 {f} {key}", "狀態": "", "窗內最慘剩（萬，100 萬起）": lo, "窗內最大回落": mdd,
                                 "超過−70%": bool(mdd < LIMIT), "期末（萬）": float(r["eq"][-1] * 100), "年化": float(r["eq"][-1] ** (245 / len(r["eq"])) - 1)})
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "stress_taiex.csv"), index=False, encoding="utf-8")
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    S["④ 1990 起加權指數合成"] = {"狀態": "完成", "資料": srcinfo,
                            "標註": ["0050 代理 ＝ 加權指數日報酬（價格指數、不含息）；另報加年 3% 股息近似", "指數無開盤價 ⇒ 開盤以前一日收盤代",
                                   "早年有週六交易日；年化照 245 日／年", "正2 ＝ 2 × 日報酬 − 0.3%／年 − 資金成本（年利率÷245×(2−1)）",
                                   "1990 窗在指數檔首日起算、長均線與 250 日高還算不出來 ⇒ 1990 窗低頻擇時不適用",
                                   "台灣拆款隔夜 1991-10 起 ⇒ 1990 窗不適用；商業本票用上個月月值",
                                   "台灣利率最後兩個月（2026-08 起）尚未公布 ⇒ 延用 2026-07 的值（本件四個壓力窗都在 2014 以前，不受影響）",
                                   "③ 2008 窗與 0050×2 合成（researchMix70 壓力窗 −67.80%／固定 3% −68.04%）並列；加權指數與 0050 成分不同"],
                            "窗（實際交易日）": {k: [cal[int(np.searchsorted(cal, v[0]))], cal[int(np.searchsorted(cal, v[1], side="right")) - 1]] for k, v in WINS.items()}}
    json.dump(S, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    json.dump(srcinfo, open(os.path.join(OUT, "taiex_sources.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    x = df[(df["股息"] == "價格指數（不含息）") & (df["對象"] == "六四 v1") & (df["狀態"] == "")]
    print(x[["資金成本", "窗", "窗內最慘剩（萬，100 萬起）", "窗內最大回落", "超過−70%"]].to_string())


if __name__ == "__main__":
    main()
