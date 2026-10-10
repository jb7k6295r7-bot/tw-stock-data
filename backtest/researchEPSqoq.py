# -*- coding: utf-8 -*-
"""PREREG單季EPS季增 seq3（台股策略線登錄 sha a8db73f1b6f76640，2026-10-10 23:18；裁定 seq323 發號 N_組合 ＋1、seq324 母體更正與描述臂；
事後重切 ⇒ 最多暫定、只進前瞻紀錄）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchEPSqoq run [--procs 2] [--reps 200] [--fake 200]
    ...                                                   -m backtest.researchEPSqoq page
    抽樣查核（獨立寫法）：... -m backtest.researchEPSqoq_check

⭐ 讀法寫死時間：2026-10-10 23:51（台北）；寫死前 ⛔ 沒算任何本件數字。共同讀法 ＝ backtest/researchPRE5core.py 檔頭（C1～C15）。

═══ 本件讀法（E 標）═══
 E1 資料：data/mops/fs_hist/<yyyy>Q<q>_<格式>_<市場>.csv（repo 工作樹；檔內容 sha 記在 meta）；一般業 ＝ ci 檔
    「基本每股盈餘（元）」年初累計；單季 ＝ 本期累計 − 同年前一季累計（Q1 不減）；前一季不在 ci 或空值 ⇒ 單季缺（登錄「前期缺 ⇒ 不算」）
    同一股同一期出現在兩個檔 ⇒ ci 優先、再依檔名排序取第一個（researchYLmargin M3 同法，筆數照報）
 E2 t0(q) ＝ 法定期限（Q1 5/15、Q2 8/14、Q3 11/14、Q4 隔年 3/31）之後第一個交易日；決策日 d ＝ t0 前一交易日；進場 ＝ t0 開盤
    母體 ＝ C3 在 d（5,000 萬＋四碼；⭐ seq324：一般業 ci、⛔ 不另排生技）∧ 該股第 q 季在 ci 檔
 E3 候選：單季 EPS(q) ＞ 單季 EPS(q−1)（兩者有值；相等不算）；格 G1 抽籤｜G2 鍵 ＝（EPS(q) − EPS(q−1)）÷ d 的原始收盤（每股盈餘是原始股數口徑 ⇒ 用未還原收盤；
    引擎 pick 遞減、不抽籤 ⇒ r＝0）
 E4 出場：下一季 t0(q＋1)：EPS(q＋1) 不再 ＞ EPS(q)（含缺值）⇒ 當天開盤賣；仍季增 ⇒ 續抱、再看下一季；⛔ 不設最長天數；空位用當季新候選補（引擎：只在 t0 有新列）
 E5 早年段：fs_hist 2015Q1 起 ⇒「不可判定」（裁定 seq323 照登錄）
 E6 描述臂（seq324，不計 N、不判）：單季 EPS(q) ≥ 去年同季 EPS(q−4)，同進出場（出場 ＝ 之後某季不再 ≥ 去年同季；G2 鍵改用 (EPS(q) − EPS(q−4)) ÷ 原始收盤）
 E7 限制：fs_hist 是之後回填的版本（重編季可能不是第一次公布值）；可用日用法定期限（逾期申報者在 t0 當時其實還沒有資料）⇒ 照報、不改
 E8 先驗 ③：平均持有天數（交易日，實際成交已出場的筆）＜ 150
輸出 backtest/resultsEPSqoq/；網頁 backtest/單季EPS季增_回測.html
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import os
import re
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
from backtest import researchPRE5core as C   # noqa: E402

FS = os.path.expanduser("~/tw-p17/data/mops/fs_hist")
DEAD = {1: (0, 5, 15), 2: (0, 8, 14), 3: (0, 11, 14), 4: (1, 3, 31)}


def load_eps():
    files = sorted(glob.glob(os.path.join(FS, "*.csv")))
    h = hashlib.sha256(); parts = []
    for f in files:
        b = os.path.basename(f)
        m = re.fullmatch(r"(\d{4})Q([1-4])_([a-z]+)_(twse|tpex)\.csv", b)
        if not m:
            continue
        h.update(b.encode()); h.update(open(f, "rb").read())
        df = pd.read_csv(f, dtype=str, keep_default_na=False)
        col = [c for c in df.columns if c.startswith("基本每股盈餘")]
        v = pd.to_numeric(df[col[0]].str.replace(",", "").str.strip(), errors="coerce") if col else pd.Series(np.nan, index=df.index)
        parts.append(pd.DataFrame({"sid": df["stock_id"].str.strip(), "qi": int(m[1]) * 4 + int(m[2]) - 1, "fmt": m[3], "file": b, "eps": v.to_numpy(float)}))
    F = pd.concat(parts, ignore_index=True)
    F["_o"] = (F["fmt"] != "ci").astype(int)
    F = F.sort_values(["sid", "qi", "_o", "file"], kind="mergesort")
    dup = int(F.duplicated(["sid", "qi"]).sum())
    F = F.drop_duplicates(["sid", "qi"], keep="first").drop(columns="_o").reset_index(drop=True)
    ci = F[F["fmt"] == "ci"][["sid", "qi", "eps"]]
    p = ci.copy(); p["qi"] += 1
    M = ci.merge(p, on=["sid", "qi"], how="left", suffixes=("", "_p"))
    q1 = (M["qi"] % 4 == 0).to_numpy()
    M["sq"] = np.where(q1, M["eps"], M["eps"] - M["eps_p"])
    info = {"檔數": len(files), "內容sha": h.hexdigest()[:16], "同股同期重複列": dup, "ci 股期": int(len(ci)), "單季 EPS 有值": int(np.isfinite(M["sq"]).sum()),
            "期別": [f"{F['qi'].min() // 4}Q{F['qi'].min() % 4 + 1}", f"{F['qi'].max() // 4}Q{F['qi'].max() % 4 + 1}"]}
    return M, info


class EPSqoq:
    NAME = "PREREG單季EPS季增 seq3"
    KEY = "EPSqoq"
    REG_SHA = "a8db73f1b6f76640"
    TIME = "2026-10-10 23:51（台北）"
    OUT = os.path.expanduser("~/tw-p17/backtest/resultsEPSqoq")
    PAGE = os.path.expanduser("~/tw-p17/backtest/單季EPS季增_回測.html")
    cells = ["G1", "G2"]
    PICK = {"G1": False, "G2": True}
    excl_fb = False
    early_ok = False
    early_note = "fs_hist 2015Q1 起 ⇒ 早年段不可判定（裁定 seq323 照登錄）"
    meta_extra = {"件說明": "財報法定期限後第一個交易日開盤，買單季 EPS 比上一季高的一般業股票（G1 抽籤／G2 增幅÷股價大者先），下一季不再季增才賣"}
    LONG = "EPS 季增組 +0.79%"

    def result_sentence(self):
        return "做多那一腿對母體只有 EPS 季增組 +0.79%，扣一趟成本 0.585% 後只剩約 0～0.2%；基準是 5,000 萬等權母體、不是 0050。"

    def notes(self):
        return ["財報法定期限後第一個交易日 t0 開盤，買單季 EPS（基本每股盈餘累計相減）比上一季高的一般業（ci）股票；母體 5,000 萬＋四碼、不另排生技（seq324）。",
                "下一季 t0：不再季增（含缺值）⇒ 開盤賣；⛔ 不設最長天數。主臂維持季對季（沿用已看過的事件層定義、不另挑）。",
                "描述臂：單季 EPS ≥ 去年同季（同進出場）。",
                "早年段：fs_hist 2015Q1 起 ⇒ 不可判定。fs_hist 是回填版本、可用日用法定期限（逾期申報者當時其實還沒資料）⇒ 照報。",
                "事後重切（情報 #15 已看過）⇒ 最多「暫定」。"]

    def _eps(self, W, log):
        k = ("eps",)
        if k not in W.ind_cache:
            M, info = load_eps()
            self.meta_extra["fs_hist"] = info
            log(f"[fs_hist] {info}")
            qis = sorted(M["qi"].unique())
            q0, q1 = min(qis), max(qis)
            nq = q1 - q0 + 1
            SQ = np.full((nq, W.S), np.nan); CI = np.zeros((nq, W.S), bool)
            for sid, qi, sq in zip(M["sid"], M["qi"], M["sq"]):
                j = W.ix.get(sid)
                if j is None:
                    continue
                CI[qi - q0, j] = True; SQ[qi - q0, j] = sq
            t0 = []
            for qi in range(q0, q1 + 1):
                y, q = qi // 4, qi % 4 + 1
                dy, mo, dd = DEAD[q]
                t0.append(int(W.cal.searchsorted(pd.Timestamp(y + dy, mo, dd), side="right")))
            W.ind_cache[k] = (q0, SQ, CI, np.array(t0))
        return W.ind_cache[k]

    def dec_days(self, W):
        q0, SQ, CI, T0 = self._eps(W, print)
        return np.array([t - 1 for t in T0 if 1 <= t < W.n], int)

    def rebal_days(self, W):
        return self.dec_days(W) + 1

    def universe(self, W, log):
        return W.UNI.copy()

    def _rows(self, W, U, log, lag=1, ge=False):
        q0, SQ, CI, T0 = self._eps(W, log)
        nq = len(T0)
        with np.errstate(invalid="ignore"):
            good = np.zeros_like(CI)
            good[lag:] = (SQ[lag:] >= SQ[:-lag]) if ge else (SQ[lag:] > SQ[:-lag])
            diff = np.full_like(SQ, np.nan); diff[lag:] = SQ[lag:] - SQ[:-lag]
        rows = {"G1": [], "G2": []}
        for j in range(nq):
            t = T0[j]
            if not (1 <= t < W.n):
                continue
            d = t - 1
            cand = np.flatnonzero(U[:, d] & CI[j] & good[j])
            for s in cand:
                x = -1
                for j2 in range(j + 1, nq):
                    if T0[j2] >= W.n:
                        break
                    if not good[j2, s]:
                        x = int(T0[j2]); break
                key = diff[j, s] / W.RC[s, d] if np.isfinite(W.RC[s, d]) and W.RC[s, d] > 0 else np.nan
                why = ("不再 ≥ 去年同季" if ge else "不再季增") if x > 0 else "未完"
                for c in ("G1", "G2"):
                    rows[c].append((int(s), int(t), "open", x, why, float(key)))
        return {c: pd.DataFrame(v, columns=["s", "e", "xk", "x", "why", "key"]) for c, v in rows.items()}

    def build(self, W, U, log):
        return self._rows(W, U, log)

    def early_window(self, W, log):
        return None

    def extra_desc(self, W, U, chosen, log):
        return {"單季EPS≥去年同季（描述臂）": self._rows(W, U, log, lag=4, ge=True)[chosen]}

    def extra_stats(self, W, U, FB, RES, chosen, seg, log):
        q0, SQ, CI, T0 = self._eps(W, log)
        a, b = seg["主窗"]
        out = {}
        for c in self.cells:
            g = FB[c].groupby("e").size()
            out[f"{c} 每季候選數"] = C.q_(g.to_numpy())
        return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", nargs="?", default="run")
    ap.add_argument("--procs", type=int, default=2); ap.add_argument("--reps", type=int, default=200); ap.add_argument("--fake", type=int, default=200)
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    if a.cmd == "run":
        C.run_study(EPSqoq(), a)
    elif a.cmd == "page":
        from backtest import researchPRE5page as PG
        PG.page(EPSqoq())


if __name__ == "__main__":
    main()
