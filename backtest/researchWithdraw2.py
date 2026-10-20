# -*- coding: utf-8 -*-
"""賣 0050／六四 v1 提領 補件：B 帳戶用【扣費合成 00685L】重跑＋每格累計領現（裁定 seq396 §一）。回測線，2026-10-20。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchWithdraw2
    獨立查核：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python backtest/researchWithdraw2_check.py

⛔ 定位：描述，不判、不計 N、不改六四 v1、不改任何規則；這是描述，不是買賣建議。措辭照 seq393（不寫哪個最好、不寫不賣最好）。
   researchWithdraw.py 與 resultsWithdraw/ 既有檔一律不改：本檔 import 重用 W.sim／W.summarize／W.hd 結果，輸出另存 resultsWithdraw/v2/。
═══ 與原版（researchWithdraw）唯一的差別：00685L 上市（2017-03-30）前的合成序列 ═══
 原版   L_c[t] ＝ L_c[t−1] ×（1＋2 r_t − 0.3%／245）；r_t ＝ 0050 含息還原日報酬（research64retest.synth rate＝0）——只扣經理費、不扣資金成本
 扣費版 L_c[t] ＝ L_c[t−1] ×（1＋2 r_t −（內扣費率＋融資利率_t）× 曆日數／365）  （1 倍名目借款 × 利率；開盤 ＝ L_c[t−1]×(1＋2×隔夜報酬)、成本記在收盤）
        ・按曆日計：一年剛好扣足年率（若 ÷252 每交易日扣，台股一年約 245 交易日 ⇒ 只扣到約 97%）
        ・內扣費率 ＝ 經理費 0.3%（repo resultsMix70／research64retest 已記、公開報導同：4 檔正2 中最低）＋ 保管費 0.04%（⚠ 未查到 00685L 實際保管費率，用常見值假設）＝ 0.34%／年
        ・融資利率（主）＝ 台灣商業本票初級市場 1-30 天（央行 EG41M01 月資料；月內各日用【上個月】值；research64retest_taiex 同一支 rates()）
          ⚠ 資料庫沒有台灣 1 年期定存序列 ⇒ 用貨幣市場利率（商業本票 1-30 天）代
        ・敏感度（描述）：同利率、內扣費 1.0%／年（＝ 若費用率與 00631L 同級）；對帳另列「拆款隔夜」與「DTB3」兩種利率
 接合   上市日起用真的 00685L（同原版）；上市前合成 × k，使上市日當天報酬 ＝ 合成報酬（researchWithdraw.load_all 同式）
 對帳   上市後把各合成序列繼續算到最新日，與真實 00685L（分割調整）逐年比報酬、報全段年化偏差；另報子段（至 2023-12-29）年化偏差
        診斷（描述）：同扣費但標的改用加權指數價格日報酬×2 的逐年差 ⇒ 看偏差有多少來自「0050 ≠ 00685L 的標的（臺指日報酬兩倍指數）」
 重跑   B 帳戶全部格（①～⑤、3,404／4,649、三起點、淨 3.5%／11.5%、水庫 0%／1.5%）× {扣費主、扣費高費敏感}；
        A 帳戶與 B 原版也在同一份資料上重跑 ⇒ 與 resultsWithdraw/grid.csv 逐格一致（資料 main 釘在原版的 006adbd009）
 累計領現 每格「累計領現（每 100 萬本金）」：A、B 原版、B 扣費、高股息 70/30、50/50、0/100（resultsWithdraw/highdiv_side.csv）
輸出 backtest/resultsWithdraw/v2/
"""
from __future__ import annotations

import glob
import hashlib
import json
import os

import numpy as np
import pandas as pd

from . import researchHighDiv as RH
from . import researchWithdraw as W
from . import research64retest_taiex as TX

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsWithdraw", "v2")
ORIG = os.path.join(HERE, "resultsWithdraw")
MAIN_PIN = "006adbd009e7f6c461e1d904f0349f395e54a5f6"      # 原版 resultsWithdraw/meta.json 的 main
SRC = glob.glob(os.path.expanduser("~/msdata/us_macro/*/cbc_EG41M01_money_market_monthly.csv"))
SUB_END = "2023-12-29"                                      # 對帳子段終點（0050 與加權指數 2024 起大幅分岔之前；描述）
MGMT = 0.003; CUST = 0.0004; FEE_MAIN = MGMT + CUST; FEE_HI = 0.010
CP = "台灣商業本票初級 1-30 天（上個月）"; IB = "台灣拆款隔夜加權平均"; DT = "DTB3（美國 3 個月國庫券，代）"
VAR = {"扣費": (FEE_MAIN, CP), "扣費高費敏感": (FEE_HI, CP)}
RECON = {"原版（0.3%／245、無資金成本）": None, "扣費主（0.34%＋商業本票）": (FEE_MAIN, CP), "扣費高費敏感（1.0%＋商業本票）": (FEE_HI, CP),
         "扣費（0.34%＋拆款隔夜）": (FEE_MAIN, IB), "扣費（0.34%＋DTB3）": (FEE_MAIN, DT), "只扣 0.34%（無資金成本）": (FEE_MAIN, None)}
SENT_SYN = "00685L 上市前為扣費合成序列（假設：0050 含息日報酬×2 每日重設，扣內扣費 0.34%／年〔經理費 0.3%＋保管費 0.04% 假設〕與 1 倍名目融資成本〔台灣商業本票初級 1-30 天，上個月值〕，按曆日計）"
SENT_DESC = "描述，不是買賣建議"
LOGF = None


def log(m):
    print(m, flush=True)
    if LOGF:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(m + "\n")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def orig_hashes():
    fs = [os.path.join(HERE, "researchWithdraw.py")] + sorted(glob.glob(os.path.join(ORIG, "*.*")))
    return {os.path.relpath(f, HERE): sha(f) for f in fs}


def rate_table(cal):
    src = os.path.dirname(sorted(SRC)[-1])
    RT = TX.rates(src, list(cal))
    out = {k: pd.Series(RT[k]).ffill().to_numpy() for k in (CP, IB, DT)}   # 資料最新月之後沿用最後一筆（只影響上市後的對帳延伸）
    for k, v in out.items():
        assert np.isfinite(v).all(), f"利率 {k} 在日曆起點就缺"
    return out, src


def synth_cost(Ao, Ac, cal, fee, rf):
    n = len(Ac); dts = pd.to_datetime(pd.Index(cal))
    Lc = np.empty(n); Lo = np.empty(n); Lc[0] = 1.0; Lo[0] = Lc[0] / (1 + 2 * (Ac[0] / Ao[0] - 1))
    dd = np.r_[0, np.diff(dts.values).astype("timedelta64[D]").astype(int)]
    r = np.zeros(n) if rf is None else rf
    for t in range(1, n):
        Lo[t] = Lc[t - 1] * (1 + 2 * (Ao[t] / Ac[t - 1] - 1)) if np.isfinite(Ao[t]) else np.nan
        Lc[t] = Lc[t - 1] * (1 + 2 * (Ac[t] / Ac[t - 1] - 1) - (fee + r[t]) * dd[t] / 365.0)
    return Lo, Lc


def splice(X, pos, Lo, Lc):
    ts = pos[W.LIST685]; C = X["00685L"]["C"]; O = X["00685L"]["O"]
    k = (C[ts] / (Lc[ts] / Lc[ts - 1])) / Lc[ts - 1]
    x = dict(X["00685L"]); x["O"] = np.r_[k * Lo[:ts], O[ts:]]; x["C"] = np.r_[k * Lc[:ts], C[ts:]]; x["synth_k"] = float(k)
    x["Lo"], x["Lc"] = Lo, Lc
    X2 = dict(X); X2["00685L"] = x
    return X2


def recon(cal, pos, X, series):
    """上市日收盤為基：真實 00685L（分割調整）vs 各合成延伸，逐年報酬與全段年化。"""
    ts = pos[W.LIST685]; C = X["00685L"]["C"]; spl = X["00685L"]["split"]
    real = np.full(len(cal), np.nan); real[ts] = 1.0
    for t in range(ts + 1, len(cal)):
        real[t] = real[t - 1] * C[t] * spl[t] / C[t - 1]
    S = {"真實00685L": real, **{k: v / v[ts] for k, v in series.items()}}
    yrs = sorted({d[:4] for d in cal[ts:]}); rows = []
    for y in yrs:
        idx = [i for i in range(ts, len(cal)) if cal[i][:4] == y]
        b = max(ts, idx[0] - 1) if y != cal[ts][:4] else ts; e = idx[-1]
        row = {"年": y, "起": cal[b], "迄": cal[e], "交易日": e - b}
        for k, v in S.items():
            row[k] = v[e] / v[b] - 1
        for k in series:
            row[f"差：{k}－真實"] = row[k] - row["真實00685L"]
        rows.append(row)
    yr = pd.DataFrame(rows)
    i1 = len(cal) - 1; nyr = (pd.Timestamp(cal[i1]) - pd.Timestamp(cal[ts])).days / 365.25
    summ = {"段": f"{cal[ts]}～{cal[i1]}", "年數": nyr}
    ar = S["真實00685L"][i1] ** (1 / nyr) - 1; summ["真實00685L 年化"] = ar
    ie = pos[SUB_END]; nyr2 = (pd.Timestamp(cal[ie]) - pd.Timestamp(cal[ts])).days / 365.25
    ar2 = S["真實00685L"][ie] ** (1 / nyr2) - 1; summ[f"子段 {cal[ts]}～{cal[ie]} 真實00685L 年化"] = ar2
    for k in series:
        a = S[k][i1] ** (1 / nyr) - 1
        summ[f"{k} 年化"] = a; summ[f"{k} 年化偏差（合成－真實）"] = a - ar
        summ[f"{k} 子段年化偏差（至 {cal[ie]}）"] = S[k][ie] ** (1 / nyr2) - 1 - ar2
        d = yr[f"差：{k}－真實"].iloc[1:-1] if len(yr) > 2 else yr[f"差：{k}－真實"]
        summ[f"{k} 完整年逐年差 平均"] = float(d.mean()); summ[f"{k} 完整年逐年差 中位"] = float(d.median())
        summ[f"{k} 完整年逐年差 絕對值平均"] = float(d.abs().mean())
    return yr, summ


def taiex_diag(cal, pos, X, rf):
    """診斷（描述）：把合成標的從 0050 含息換成【加權指數價格日報酬】（同扣 0.34%＋商業本票），看逐年差有多少來自標的不同。
    ⚠ 加權指數是價格指數（不含息）；檔案只到 taiex_last ⇒ 2026 只算到該日。"""
    tf = sorted(glob.glob(W.TAIEX_GLOB))[-1]
    tx = pd.read_csv(tf, dtype={"date": str}).set_index("date")["close"].astype(float)
    last = str(tx.index.max()); txc = tx.reindex(cal).ffill().to_numpy()
    ts = pos[W.LIST685]; ie = max(i for i in range(len(cal)) if cal[i] <= last)
    dts = pd.to_datetime(pd.Index(cal)); dd = np.r_[0, np.diff(dts.values).astype("timedelta64[D]").astype(int)]
    C = X["00685L"]["C"]; spl = X["00685L"]["split"]
    L = np.full(len(cal), np.nan); R = np.full(len(cal), np.nan); L[ts] = 1.0; R[ts] = 1.0
    for t in range(ts + 1, ie + 1):
        L[t] = L[t - 1] * (1 + 2 * (txc[t] / txc[t - 1] - 1) - (FEE_MAIN + rf[t]) * dd[t] / 365.0)
        R[t] = R[t - 1] * C[t] * spl[t] / C[t - 1]
    rows = []
    for y in sorted({d[:4] for d in cal[ts:ie + 1]}):
        idx = [i for i in range(ts, ie + 1) if cal[i][:4] == y]
        b = ts if y == cal[ts][:4] else idx[0] - 1; e = idx[-1]
        rows.append({"年": y, "加權診斷迄": cal[e], "2×加權指數價格（扣 0.34%＋商業本票）": L[e] / L[b] - 1, "真實（同段）": R[e] / R[b] - 1,
                     "差：2×加權－真實": (L[e] / L[b]) - (R[e] / R[b])})
    return pd.DataFrame(rows), last


def run_grid(tag, acct_list, X, cal, pos, c4, c5, regime, starts, i1, keep=None):
    rows = []
    for sn, d0 in starts.items():
        i0 = pos[d0]
        for acct in acct_list:
            for tgt in W.TARGETS:
                for tn, ts in W.TAXV.items():
                    for m in W.METHODS:
                        for rr in ((0.0, 0.015) if m >= 3 else (0.0,)):
                            r = W.sim(acct, tgt, m, ts, rr, i0, i1, cal, X, c4, c5, regime)
                            s = W.summarize(r, cal, i0, i1)
                            rows.append({"合成版": tag, "起點": sn, "起": d0, "迄": cal[i1], "帳戶": acct, "每月目標": int(tgt), "稅版": tn,
                                         "方法": W.METHODS[m], "水庫利率": rr, **s})
                            if keep is not None and sn == "2007-12" and tn == "淨3.5%" and rr == 0.0 and acct == "B":
                                keep[(tag, int(tgt), m)] = r
    return rows


KEYS = ["起點", "帳戶", "每月目標", "稅版", "方法", "水庫利率"]
MET = ["期末總額（每100萬）", "換算年化", "最大回落（市值＋水庫）", "最低市值剩本金", "最低日", "累計領現（每100萬）", "提領到歸零",
       "最差年每月現金", "賣股次數", "賣在大跌期金額比例", "被迫賣次數", "被迫賣年份"]


def main():
    global LOGF
    os.makedirs(OUT, exist_ok=True); LOGF = os.path.join(OUT, "run.log"); open(LOGF, "w").close()
    h0 = orig_hashes()
    log(f"===== researchWithdraw2 {pd.Timestamp.now(tz='Asia/Taipei'):%Y-%m-%d %H:%M}（台北）｜裁定 seq396 §一｜描述，不判、不計 N、不改六四 v1 =====")
    RH.MAIN_REF = MAIN_PIN                                   # 釘在原版資料
    cal, pos, X, c4, c5, regime, ind, info, tdd, fdd = W.load_all()
    assert info["main"] == MAIN_PIN
    i1 = len(cal) - 1
    starts = {k: next(d for d in cal if d >= v) for k, v in W.START_REQ.items()}
    log(f"資料 main {info['main'][:10]}（原版同）；日曆 {cal[0]}～{cal[-1]}（{len(cal)} 日）；起點 {starts}")
    RT, src = rate_table(cal)
    Ao, Ac = X["0050"]["Ao"], X["0050"]["Ac"]
    ts = pos[W.LIST685]
    for k in (CP, IB, DT):
        v = RT[k][:ts]; log(f"  利率 {k}：上市前（{cal[0]}～{cal[ts-1]}）平均 {v.mean():.3%}、最低 {v.min():.3%}、最高 {v.max():.3%}")
    # ── 合成序列 ──
    SER = {"原版（0.3%／245、無資金成本）": X["00685L"]["Lc"]}
    SYN = {}
    for k, spec in RECON.items():
        if spec is None:
            continue
        fee, rk = spec
        Lo, Lc = synth_cost(Ao, Ac, cal, fee, RT[rk] if rk else None)
        SER[k] = Lc; SYN[k] = (Lo, Lc)
    XV = {"扣費": splice(X, pos, *SYN["扣費主（0.34%＋商業本票）"]), "扣費高費敏感": splice(X, pos, *SYN["扣費高費敏感（1.0%＋商業本票）"])}
    for k, x in XV.items():
        log(f"  接合 {k}：k ＝ {x['00685L']['synth_k']:.6g}（原版 {info['synth_k']:.6g}）")
    # 上市前段合成累積報酬（窗首 2007-12-26 → 上市前一日）
    pre = {k: v[ts - 1] / v[0] - 1 for k, v in SER.items()}
    for k, v in pre.items():
        nyr = (pd.Timestamp(cal[ts - 1]) - pd.Timestamp(cal[0])).days / 365.25
        log(f"  上市前段 {cal[0]}～{cal[ts-1]} 合成 {k}：累積 {v:+.2%}、年化 {(1+v)**(1/nyr)-1:+.2%}")
    # ── 對帳 ──
    yr, summ = recon(cal, pos, X, {k: v for k, v in SER.items()})
    td, tlast = taiex_diag(cal, pos, X, RT[CP])
    yr = yr.merge(td, on="年", how="left")
    yr.to_csv(os.path.join(OUT, "synth_recon_yearly.csv"), index=False, encoding="utf-8-sig")
    log(f"\n[對帳] 上市後 {summ['段']}（{summ['年數']:.2f} 年）：真實 00685L 年化 {summ['真實00685L 年化']:.2%}")
    for k in SER:
        log(f"  {k:<26} 年化 {summ[f'{k} 年化']:.2%}｜年化偏差 {summ[f'{k} 年化偏差（合成－真實）']:+.2%}｜完整年逐年差 平均 {summ[f'{k} 完整年逐年差 平均']:+.2%}、"
            f"中位 {summ[f'{k} 完整年逐年差 中位']:+.2%}、|差| 平均 {summ[f'{k} 完整年逐年差 絕對值平均']:.2%}｜子段（至 {SUB_END}）年化偏差 {summ[f'{k} 子段年化偏差（至 {SUB_END}）']:+.2%}")
    show = yr[["年", "真實00685L"] + [f"差：{k}－真實" for k in ("原版（0.3%／245、無資金成本）", "扣費主（0.34%＋商業本票）", "扣費高費敏感（1.0%＋商業本票）")]
              + ["差：2×加權－真實"]].copy()
    log(show.to_string(index=False, float_format=lambda v: f"{v:+.2%}"))
    log(f"  （最後一欄＝診斷：合成標的改用加權指數價格日報酬×2、同扣 0.34%＋商業本票；加權檔只到 {tlast}；⚠ 價格指數不含息）")
    # ── 重跑 ──
    KEEP = {}
    rows = run_grid("原版", ("A", "B"), X, cal, pos, c4, c5, regime, starts, i1)
    for tag, x in XV.items():
        rows += run_grid(tag, ("B",), x, cal, pos, c4, c5, regime, starts, i1, KEEP)
    g = pd.DataFrame(rows)
    g.to_csv(os.path.join(OUT, "grid_v2_long.csv"), index=False, encoding="utf-8-sig")
    # 原版逐格一致
    G0 = pd.read_csv(os.path.join(ORIG, "grid.csv"))
    mine = g[g["合成版"] == "原版"].drop(columns=["合成版"]).reset_index(drop=True)
    mm = G0.merge(mine, on=KEYS, suffixes=("_g", "_m"))
    worst = 0.0; strbad = []
    for c in G0.columns:
        if c in KEYS:
            continue
        a = pd.to_numeric(mm[f"{c}_g"], errors="coerce").to_numpy(float); b = pd.to_numeric(mm[f"{c}_m"], errors="coerce").to_numpy(float)
        if np.isfinite(a).any() or np.isfinite(b).any():
            if not np.array_equal(np.isfinite(a), np.isfinite(b)):
                strbad.append(c); continue
            f = np.isfinite(a)
            if f.any():
                worst = max(worst, float(np.max(np.abs(a[f] - b[f]) / np.maximum(1.0, np.abs(a[f])))))
        else:
            if not (mm[f"{c}_g"].fillna("").astype(str) == mm[f"{c}_m"].fillna("").astype(str)).all():
                strbad.append(c)
    okA = len(mm) == len(G0) == len(mine) and not strbad
    if strbad:
        log(f"⚠ 原版重跑不一致欄：{strbad}")
    log(f"\n[原版重跑 ＝ resultsWithdraw/grid.csv] 列數 {len(mm)}／{len(G0)}；數值欄最大相對差 {worst:.2e} ⇒ {'一致' if okA and worst < 1e-9 else '⚠ 不一致'}")
    # B 並列
    b0 = g[(g["合成版"] == "原版") & (g["帳戶"] == "B")].set_index(KEYS)
    cmp = b0[MET].add_suffix("｜原版")
    for tag in XV:
        bt = g[(g["合成版"] == tag)].set_index(KEYS)[MET].add_suffix(f"｜{tag}")
        cmp = cmp.join(bt)
        cmp[f"期末總額差（{tag}－原版，每100萬）"] = cmp[f"期末總額（每100萬）｜{tag}"] - cmp["期末總額（每100萬）｜原版"]
        cmp[f"年化差（{tag}－原版）"] = cmp[f"換算年化｜{tag}"] - cmp["換算年化｜原版"]
    cmp = cmp.reset_index()
    cmp.to_csv(os.path.join(OUT, "grid_B_compare.csv"), index=False, encoding="utf-8-sig")
    # 累計領現
    hd = pd.read_csv(os.path.join(ORIG, "highdiv_side.csv"))
    a0 = g[(g["合成版"] == "原版") & (g["帳戶"] == "A")]
    cc = []
    for _, z in a0.iterrows():
        cc.append({"起點": z["起點"], "稅版": z["稅版"], "每月目標": z["每月目標"], "方案": "A 100% 0050", "方法": z["方法"], "水庫利率": z["水庫利率"],
                   "累計領現（每100萬）": z["累計領現（每100萬）"], "期末總額（每100萬）": z["期末總額（每100萬）"], "提領到歸零": z["提領到歸零"]})
    for tag in ("原版", "扣費", "扣費高費敏感"):
        for _, z in g[(g["合成版"] == tag) & (g["帳戶"] == "B")].iterrows():
            cc.append({"起點": z["起點"], "稅版": z["稅版"], "每月目標": z["每月目標"], "方案": f"B 六四 v1（{tag}）", "方法": z["方法"], "水庫利率": z["水庫利率"],
                       "累計領現（每100萬）": z["累計領現（每100萬）"], "期末總額（每100萬）": z["期末總額（每100萬）"], "提領到歸零": z["提領到歸零"]})
    for _, z in hd.iterrows():
        cc.append({"起點": z["起點"], "稅版": z["稅版"], "每月目標": np.nan, "方案": z["方案"], "方法": "配息領現（不賣股）", "水庫利率": np.nan,
                   "累計領現（每100萬）": z["累計領現（每100萬）"], "期末總額（每100萬）": z["期末總額（每100萬）"], "提領到歸零": "否"})
    cc = pd.DataFrame(cc)
    cc.to_csv(os.path.join(OUT, "cash_cum.csv"), index=False, encoding="utf-8-sig")
    # 抽樣明細（扣費版 B ① 3,404、B ④ 3,404）
    for (tag, tgt, m), r in KEEP.items():
        if tgt == 3404 and m in (1, 4) and tag == "扣費":
            nm = f"B_{tgt}_m{m}"
            pd.DataFrame(r["sales"]).to_csv(os.path.join(OUT, f"sample_sales_full_3.5_{nm}_扣費.csv"), index=False, encoding="utf-8-sig")
            pd.DataFrame({"date": cal[pos[starts['2007-12']]:], "V": r["V"], "res": r["res"], "out": r["out"]}).to_csv(
                os.path.join(OUT, f"sample_daily_full_3.5_{nm}_扣費.csv"), index=False, encoding="utf-8-sig")
    # 合成序列（上市前段，日資料）
    pd.DataFrame({"date": cal, "0050含息還原": Ac, **{k: v for k, v in SER.items()},
                  "商業本票(上月,小數)": RT[CP], "拆款隔夜(小數)": RT[IB], "DTB3(小數)": RT[DT],
                  "B用00685L收盤_原版": X["00685L"]["C"], "B用00685L收盤_扣費": XV["扣費"]["00685L"]["C"]}).to_csv(
        os.path.join(OUT, "synth_daily.csv"), index=False, encoding="utf-8-sig")
    # ── 顯示 ──
    for tn in W.TAXV:
        for sn in starts:
            log(f"\n── B 原版 vs 扣費｜起點 {sn}｜{tn}｜水庫利率 0% ──")
            x = cmp[(cmp["起點"] == sn) & (cmp["稅版"] == tn) & (cmp["水庫利率"] == 0.0)]
            for _, z in x.iterrows():
                log(f"  {z['每月目標']} {z['方法']:<10} 總額 {z['期末總額（每100萬）｜原版']/1e4:7.1f}→{z['期末總額（每100萬）｜扣費']/1e4:7.1f} 萬（高費 {z['期末總額（每100萬）｜扣費高費敏感']/1e4:7.1f}）｜"
                    f"年化 {z['換算年化｜原版']:6.2%}→{z['換算年化｜扣費']:6.2%}｜回落 {z['最大回落（市值＋水庫）｜原版']:7.2%}→{z['最大回落（市值＋水庫）｜扣費']:7.2%}｜"
                    f"最低剩 {z['最低市值剩本金｜原版']:.2f}→{z['最低市值剩本金｜扣費']:.2f}｜累計領現 {z['累計領現（每100萬）｜原版']/1e4:.1f}→{z['累計領現（每100萬）｜扣費']/1e4:.1f} 萬｜"
                    f"歸零 {z['提領到歸零｜原版']}→{z['提領到歸零｜扣費']}")
    log(f"\n結果句附註：「{SENT_SYN}」「{SENT_DESC}」")
    h1 = orig_hashes()
    log(f"[原版檔未改] researchWithdraw.py 與 resultsWithdraw/ 頂層 {len(h0)} 檔 sha256 前後一致：{h0 == h1}")
    meta = {"定位": "描述，不判、不計 N、不改六四 v1；" + SENT_DESC, "裁定": "seq396 §一", "main": info["main"], "迄": cal[i1], "起點": starts,
            "合成公式": "L_c[t]＝L_c[t−1]×(1＋2r_t−(費率＋利率_t)×曆日/365)；開盤＝L_c[t−1]×(1＋2×隔夜報酬)",
            "內扣費率主": {"經理費": MGMT, "保管費（假設，未查到）": CUST, "合計": FEE_MAIN}, "內扣費率敏感": FEE_HI,
            "融資利率主": CP + "（央行 EG41M01；資料庫無台灣 1 年期定存序列）", "利率來源": src,
            "接合k": {"原版": info["synth_k"], **{k: x["00685L"]["synth_k"] for k, x in XV.items()}},
            "對帳摘要": summ, "原版重跑一致": bool(okA and worst < 1e-9), "原版重跑最大相對差": worst,
            "結果句": [SENT_SYN, SENT_DESC], "原版檔sha256": h0, "原版檔未改": h0 == h1}
    with open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1, default=str)
    log("完成。")


if __name__ == "__main__":
    main()
