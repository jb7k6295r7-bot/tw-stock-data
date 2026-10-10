# -*- coding: utf-8 -*-
"""PREREG財報前季營收前段 seq3（台股策略線登錄 sha 1f7e313014807dd1，2026-10-10 23:18；裁定 seq323 發號 N_組合 ＋1、seq324 加兩描述臂與措辭；
事後重切 ⇒ 最多暫定、只進前瞻紀錄）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchPreFinRev run [--procs 2] [--reps 200] [--fake 200]
    ...                                                       -m backtest.researchPreFinRev page
    抽樣查核（獨立寫法）：... -m backtest.researchPreFinRev_check

⭐ 讀法寫死時間：2026-10-10 23:49（台北）；寫死前 ⛔ 沒算任何本件數字。共同讀法 ＝ backtest/researchPRE5core.py 檔頭（C1～C15）。

═══ 本件讀法（P 標）═══
 P1 季 (y, q)：季底月 M ＝ y-03／06／09／12；t_rev ＝ M 的月營收可用日（C14）；決策日 d ＝ t_rev 前一交易日；進場 ＝ t_rev 開盤
    母體 ＝ C3 在 d（5,000 萬＋四碼＋排除金融保險、生技醫療業；照事件層原定義）
 P2 季營收年增 ＝ Σ 當月營收(M−2..M) ÷ Σ 去年當月營收(M−2..M) − 1（六個值都要有、去年合計 ＞ 0；⚠ 補讀法：去年同季用同一批月營收檔的「去年當月營收」欄，同口徑）
    前 10% ＝ d 的母體內有值者依年增由小到大排名（同值平均名次）＞ 0.9n
 P3 格：A1 ＝ 前 10% 裡年增最高 10 檔（引擎 pick 遞減、不抽籤 ⇒ r＝0）｜A2 ＝ 前 10% 裡抽籤 10 檔
 P4 出場：t0 ＝ 該季財報法定期限（Q1 5/15、Q2 8/14、Q3 11/14、Q4 隔年 3/31）之後第一個交易日 ⇒ t0 前一個交易日收盤全賣（C5 收盤賣型）
    空窗期（t0 → 下一季 t_rev）持現金
 P5 退化：本件依構造每年約四成時間持現金 ⇒ 現金 ＞ 30% 很可能成立；照登錄與裁定 seq325 排除並列出（全退化 ⇒ 沒有可挑的格，照報）
 P6 描述臂（不計 N、不判；挑中格的選法）：
    ① 單月排序：改用季底月單月年增（當月 ÷ 去年當月 − 1）排序，同進出場
    ② 非季底月同窗長：每個非季底月 M（1、2、4、5、7、8、10、11 月）的可用日進場，排序 ＝ 以 M 結尾的三個月合計年增（同 P2 式），
       持有 L 個交易日（進場那天算第 1 天，第 L 天收盤賣；L ＝ 主臂 Q1～Q3 窗長中位數）；但不超過本臂下一次進場日的前一交易日
    ③ 空窗期持 0050（⛔ 不判；P14 混 0050 已結案、⛔ 不可據此主張混合）：引擎 cash_mode="bench"（閒置資金持 0050、進出單邊 0.2925%）
 P7 先驗 ③「窗內報酬（不含空窗）贏 0050 同期」：各窗 eq[t0−1] ÷ eq[t_rev−1] 連乘（種子中位）vs 0050 同窗連乘
 P8 措辭（seq324）：⛔ 不寫「財報前效應」（窗內含下個月營收與提早公布的財報）；存活篩選由組合層 GATE_V2＋含下市處理
 P9 早年段：照既有月營收早年規則（自家彙總表；C14 覆蓋率 ≥ 90%（上市）的年份才判；IFRS 窗 2013 照標）
輸出 backtest/resultsPreFinRev/；網頁 backtest/財報前季營收前段_回測.html
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
from backtest import researchPRE5core as C   # noqa: E402
from backtest.researchRevPriceOK import RevPriceOK   # noqa: E402

DEAD = {1: (0, 5, 15), 2: (0, 8, 14), 3: (0, 11, 14), 4: (1, 3, 31)}


class PreFinRev:
    NAME = "PREREG財報前季營收前段 seq3"
    KEY = "PreFinRev"
    REG_SHA = "1f7e313014807dd1"
    TIME = "2026-10-10 23:49（台北）"
    OUT = os.path.expanduser("~/tw-p17/backtest/resultsPreFinRev")
    PAGE = os.path.expanduser("~/tw-p17/backtest/財報前季營收前段_回測.html")
    cells = ["A1", "A2"]
    PICK = {"A1": True, "A2": False}
    excl_fb = True
    early_ok = True
    early_note = ""
    meta_extra = {"件說明": "季底月營收出來後（t_rev 開盤）買季營收年增前 10% 的股票（A1 最高 10 檔／A2 抽籤 10 檔），財報法定期限前一天收盤全賣、空窗持現金"}
    LONG = "前 10% 組公布前窗 +1.52%（窗長 Q1～Q3 約 23 日、非 20 日）"

    def __init__(self):
        self.e2M = {}
        self._rp = RevPriceOK()

    def result_sentence(self):
        return ("（⛔ 本結果不稱「財報前效應」：窗內含下個月營收與提早公布的財報。）"
                "做多那一腿對母體只有 前 10% 組公布前窗 +1.52%（窗長 Q1～Q3 約 23 日、非 20 日），扣一趟成本 0.585% 後只剩約 0～0.2%；基準是 5,000 萬等權母體、不是 0050。")

    def notes(self):
        return ["季底月營收可用日（t_rev）開盤買季營收年增前 10%（A1 最高 10 檔、A2 抽籤 10 檔），財報法定期限前一交易日收盤全賣，空窗持現金。",
                "季營收年增 ＝ 三個月營收合計 ÷ 同檔「去年當月營收」三個月合計 − 1（六個值都要有）。",
                "依構造每年約四成時間持現金 ⇒ 現金比例 ＞ 30% 的退化格照登錄與裁定 seq325 排除。",
                "描述臂：單月營收排序、非季底月同窗長、空窗期持 0050（⛔ 不可據此主張混 0050）。",
                "早年段照自家彙總表月營收（覆蓋率 ≥ 90% 的年份）；事後重切 ⇒ 最多「暫定」。"]

    def _base(self, W, log):
        k = ("pfr",)
        if k not in W.ind_cache:
            REV = C.load_rev(log)
            P = list(REV["rev"].index); pi = {M: i for i, M in enumerate(P)}
            am = C.avail_map(W, P)
            rv = REV["rev"].reindex(columns=W.sids).to_numpy(float); rl = REV["rev_ly"].reindex(columns=W.sids).to_numpy(float)
            W.ind_cache[k] = (P, pi, am, rv, rl)
        return W.ind_cache[k]

    def yoy3(self, rv, rl, i):
        if i < 2:
            return np.full(rv.shape[1], np.nan)
        a = rv[i - 2:i + 1]; b = rl[i - 2:i + 1]
        ok = np.isfinite(a).all(0) & np.isfinite(b).all(0)
        sa, sb = a.sum(0), b.sum(0)
        with np.errstate(invalid="ignore", divide="ignore"):
            return np.where(ok & (sb > 0), sa / sb - 1, np.nan)

    def yoy1(self, rv, rl, i):
        with np.errstate(invalid="ignore", divide="ignore"):
            return np.where(np.isfinite(rv[i]) & np.isfinite(rl[i]) & (rl[i] > 0), rv[i] / rl[i] - 1, np.nan)

    def quarters(self, W, log, months=(3, 6, 9, 12)):
        P, pi, am, rv, rl = self._base(W, log)
        out = []
        for M in P:
            m = int(M[5:])
            if m not in months or M not in am or not (1 <= am[M] < W.n):
                continue
            out.append((M, pi[M], am[M]))
        return out

    def t0_of(self, W, M):
        y, m = int(M[:4]), int(M[5:]); q = m // 3
        dy, mo, dd = DEAD[q]
        return int(W.cal.searchsorted(pd.Timestamp(y + dy, mo, dd), side="right"))

    def dec_days(self, W):
        return np.array(sorted(e - 1 for M, i, e in self.quarters(W, print)), int)

    def rebal_days(self, W):
        return self.dec_days(W) + 1

    def extra_mask(self, W, d, log):
        return ~C.fb_mask(W, d, log)[0]

    def universe(self, W, log):
        U = W.UNI.copy(); old = 0
        days = set(self.dec_days(W).tolist()) | set((np.array([e for M, i, e in self.quarters(W, log, (1, 2, 4, 5, 7, 8, 10, 11))]) - 1).tolist())
        for d in sorted(days):
            m, o = C.fb_mask(W, d, log); U[:, d] &= ~m; old += o
        self.n_old = old
        return U

    def _rows(self, W, U, log, mode="q3", months=(3, 6, 9, 12), hold=None):
        P, pi, am, rv, rl = self._base(W, log)
        Q = self.quarters(W, log, months)
        rows = {"A1": [], "A2": []}
        for k, (M, i, e) in enumerate(Q):
            d = e - 1
            yy = self.yoy3(rv, rl, i) if mode == "q3" else self.yoy1(rv, rl, i)
            ok = U[:, d] & np.isfinite(yy)
            g = np.flatnonzero(ok)
            if not len(g):
                continue
            rk = pd.Series(yy[g]).rank(method="average").to_numpy()
            top = g[rk > 0.9 * len(g)]
            if hold is None:
                t0 = self.t0_of(W, M); y0 = t0 - 1 if t0 < W.n else -1
                why = "財報期限前一日收盤" if y0 >= 0 else "未完"
            else:
                nxt = Q[k + 1][2] if k + 1 < len(Q) else W.n
                y0 = min(e + hold - 1, nxt - 1)
                y0 = y0 if y0 < W.n else -1
                why = f"持有{hold}日" if y0 >= 0 else "未完"
            self.e2M[(W.part, e)] = M
            for s in top:
                for c in ("A1", "A2"):
                    rows[c].append((int(s), int(e), "close", int(y0), why, float(yy[s])))
        return {c: pd.DataFrame(v, columns=["s", "e", "xk", "x", "why", "key"]) for c, v in rows.items()}

    def build(self, W, U, log):
        return self._rows(W, U, log)

    def early_window(self, W, log):
        r = self._rp.early_window(W, log)
        self.early_cov = self._rp.early_cov; self.early_note = self._rp.early_note
        return r

    def ifrs_share(self, W, F):
        Ms = [self.e2M.get((W.part, int(e)), "") for e in F["e"]]
        return float(np.mean([M.startswith("2013") for M in Ms])) if Ms else np.nan

    def win_len(self, W, log):
        L = []
        for M, i, e in self.quarters(W, log):
            if int(M[5:]) == 12:
                continue
            t0 = self.t0_of(W, M)
            if t0 < W.n:
                L.append(t0 - e)      # 進場日到 t0 前一日（含兩端）的交易日數
        return int(np.median(L)), L

    def extra_desc(self, W, U, chosen, log):
        r1 = self._rows(W, U, log, mode="q1")[chosen]
        L, _ = self.win_len(W, log)
        r2 = self._rows(W, U, log, months=(1, 2, 4, 5, 7, 8, 10, 11), hold=L)[chosen]
        r3 = self._rows(W, U, log)[chosen].copy(); r3.attrs["cash_bench"] = True
        return {"①單月營收排序": r1, f"②非季底月同窗長（{L} 日）": r2, "③空窗期持0050（閒置資金持 0050）": r3}

    def extra_stats(self, W, U, FB, RES, chosen, seg, log):
        L, Ls = self.win_len(W, log)
        out = {"主臂窗長（Q1～Q3，交易日）": C.q_(Ls), "早年合併類「化學生技醫療」未剔（股-決策日）": int(getattr(self, "n_old", 0))}
        Q = [(M, e, self.t0_of(W, M)) for M, i, e in self.quarters(W, log)]
        ms = RES[f"{chosen}|b"]
        for sg, (a, b) in seg.items():
            ws = [(e, t0) for M, e, t0 in Q if a <= e and t0 - 1 <= b]
            if not ws:
                continue
            strat = [float(np.prod([m["eq"][t0 - 1] / m["eq"][e - 1] for e, t0 in ws])) - 1 for m in ms]
            b50 = float(np.prod([W.bench[t0 - 1] / W.bench[e - 1] for e, t0 in ws])) - 1
            days = sum(t0 - e for e, t0 in ws)
            out[f"{sg} 窗內報酬"] = {"窗數": len(ws), "窗內交易日": days, "策略窗內連乘（種子中位）": float(np.median(strat)), "0050 同窗連乘": b50,
                                  "策略窗內年化": float((1 + np.median(strat)) ** (245 / days) - 1), "0050 同窗年化": float((1 + b50) ** (245 / days) - 1),
                                  "贏 0050 同期": bool(np.median(strat) > b50)}
        return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", nargs="?", default="run")
    ap.add_argument("--procs", type=int, default=2); ap.add_argument("--reps", type=int, default=200); ap.add_argument("--fake", type=int, default=200)
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    if a.cmd == "run":
        C.run_study(PreFinRev(), a)
    elif a.cmd == "page":
        from backtest import researchPRE5page as PG
        PG.page(PreFinRev())


if __name__ == "__main__":
    main()
