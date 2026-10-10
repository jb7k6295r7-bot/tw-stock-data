# -*- coding: utf-8 -*-
"""PREREG好營收股價已認同 seq3（台股策略線登錄 sha dc28ff73dd09542c，2026-10-10 23:18；裁定 seq323 發號 N_組合 ＋1（#10 併入不另計）、seq324 措辭；
事後重切 ⇒ 最多暫定、只進前瞻紀錄）——回測線計算子代理。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchRevPriceOK run [--procs 2] [--reps 200] [--fake 200]
    ...                                                       -m backtest.researchRevPriceOK page
    抽樣查核（獨立寫法）：... -m backtest.researchRevPriceOK_check

⭐ 讀法寫死時間：2026-10-10 23:47（台北）；寫死前 ⛔ 沒算任何本件數字。共同讀法 ＝ backtest/researchPRE5core.py 檔頭（C1～C15）。

═══ 本件讀法（V 標）═══
 V1 t0 ＝ 營收月 M 的可用日（C14：M ≤ 2025-12 ⇒ M＋1 月 10 日之後第一個交易日；M ≥ 2026-01 ⇒ 15 日之後）；決策日 d ＝ t0 前一交易日；進場 ＝ t0 開盤
    母體 ＝ C3 在 d（5,000 萬＋四碼＋排除金融保險、生技醫療業；照事件層原定義）
 V2 內容（月營收檔欄位，%）：C1 好營收 ＝「上月比較增減(%)」≥ 0 且「去年同月增減(%)」≥ 15（#17 原定義）；
    C2 月增未創高 ＝ C1 條件 且 前 24 期（M−24～M−1）「當月營收」全部有值 且 當月營收 ≤ 前 24 期最大值（＝ 沒有「＞ 前 24 期最大值」的創新高；#10 原定義）
    欄位空白 ⇒ 不符
 V3 R ＝ c(d) ÷ c(M 月最後一個交易日) − 1（還原收盤 ffill；⛔ 不含 t0）− 同期母體平均（d 的母體內 R 有值者等權平均）
    已反應 ＝ 同月、同內容組（母體內、R 有值）依 R 由小到大排名（同值取平均名次）＞ 2n／3 者（上三分之一）
 V4 格 ＝ 內容 {C1, C2} × 選法 {S1 抽籤, S2 R 大者先（引擎 pick 遞減、不抽籤 ⇒ r＝0）} ＝ 4 格挑 1
 V5 出場：之後每個 t0′（之後每個營收月 M′ 的可用日）：該股 M′ 那期營收不再符合「該格的內容條件」（C2 格含「沒創新高」；M′ 沒有資料 ⇒ 不符）⇒ t0′ 開盤賣（R 不再看）；
    ⛔ 不設最長天數；賣出款等下一個 t0（同日新候選）
 V6 早年段：照既有月營收早年規則（自家彙總表 data/early/revenue；C14 覆蓋率 ≥ 90%（上市）的年份才判；IFRS 窗 2013 期別照標）
 V7 必報另加：與營量 v1 持股重疊率（先驗 ③；C13 overlap，逐日「本件持股中也在營量 v1 持股」的比例）；C1 對 C2 年化（先驗 ②）
 V8 措辭（seq324）：「營收與價格動能分不開」；⛔ 不寫「價格認同造成」
輸出 backtest/resultsRevPriceOK/；網頁 backtest/好營收股價已認同_回測.html
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
from backtest import researchPRE5core as C   # noqa: E402


class RevPriceOK:
    NAME = "PREREG好營收股價已認同 seq3"
    KEY = "RevPriceOK"
    REG_SHA = "dc28ff73dd09542c"
    TIME = "2026-10-10 23:47（台北）"
    OUT = os.path.expanduser("~/tw-p17/backtest/resultsRevPriceOK")
    PAGE = os.path.expanduser("~/tw-p17/backtest/好營收股價已認同_回測.html")
    cells = ["C1S1", "C1S2", "C2S1", "C2S2"]
    PICK = {"C1S1": False, "C1S2": True, "C2S1": False, "C2S2": True}
    excl_fb = True
    early_ok = True
    early_note = ""
    meta_extra = {"件說明": "營收好（月增且年增 ≥ 15%）、公布期間股價比母體多漲（同組上三分之一）的股票，t0 開盤買，營收轉差（不再符合內容條件）才賣"}
    LONG = "C1 已反應組 +2.27%、C2 月增未創高 +0.78%"

    def __init__(self):
        self.e2M = {}

    def result_sentence(self):
        return ("營收與價格動能分不開（⛔ 不寫「價格認同造成」：不分內容那格本身也有 +0.89%，兩者的差沒檢定）。"
                "做多那一腿對母體只有 C1 已反應組 +2.27%、C2 月增未創高 +0.78%，扣一趟成本 0.585% 後只剩約 0～0.2%；基準是 5,000 萬等權母體、不是 0050。")

    def notes(self):
        return ["t0 ＝ 月營收可用日（2025-12 以前次月 10 日後、2026-01 期起 15 日後第一個交易日）開盤買；母體 5,000 萬＋四碼、排除金融保險與生技醫療業。",
                "內容：C1 上月比較增減 ≥ 0 且去年同月增減 ≥ 15%；C2 再加「沒創 24 月新高（前 24 期全有值）」。已反應 ＝ 同組依公布期間超額報酬 R 排三等分取上三分之一。",
                "之後每個 t0：最新一期不再符合該格內容條件（缺值算不符）⇒ 當天開盤賣；⛔ 不設最長天數。",
                "早年段照自家彙總表月營收（覆蓋率 ≥ 90% 的年份）；2013 期別（IFRS 換軌）照標。",
                "事後重切（情報 #17、#10 已看過）⇒ 最多「暫定」。"]

    def _rev(self, W, log):
        k = ("rev",)
        if k not in W.ind_cache:
            REV = C.load_rev(log)
            P = list(REV["rev"].index)
            am = C.avail_map(W, P)
            rv = REV["rev"].reindex(columns=W.sids).to_numpy(float)
            mom = REV["mom"].reindex(columns=W.sids).to_numpy(float)
            yoy = REV["yoy"].reindex(columns=W.sids).to_numpy(float)
            with np.errstate(invalid="ignore"):
                c1 = (mom >= 0) & (yoy >= 15)
            df = pd.DataFrame(rv)
            mx = df.rolling(24, min_periods=24).max().shift(1).to_numpy()
            full = (df.notna().rolling(24).sum().shift(1) == 24).to_numpy()
            with np.errstate(invalid="ignore"):
                c2 = c1 & full & np.isfinite(rv) & (rv <= mx)
            W.ind_cache[k] = (P, am, {"C1": c1, "C2": c2})
        return W.ind_cache[k]

    def dec_days(self, W):
        P, am, _ = self._rev(W, print)
        return np.array(sorted(e - 1 for M, e in am.items() if 1 <= e < W.n), int)

    def rebal_days(self, W):
        return self.dec_days(W) + 1

    def extra_mask(self, W, d, log):
        return ~C.fb_mask(W, d, log)[0]

    def universe(self, W, log):
        U = W.UNI.copy()
        old = 0
        for d in self.dec_days(W):
            m, o = C.fb_mask(W, d, log); U[:, d] &= ~m; old += o
        self.n_old = old
        return U

    def build(self, W, U, log):
        P, am, CT = self._rev(W, log)
        cal = W.cal
        out = {c: [] for c in self.cells}
        Mi = [i for i, M in enumerate(P) if M in am and 1 <= am[M] < W.n]
        avail_e = np.array([am[P[i]] for i in Mi])
        for jj, i in enumerate(Mi):
            M = P[i]; e = am[M]; d = e - 1
            y, m = int(M[:4]), int(M[5:])
            nm = pd.Timestamp(y + (m == 12), m % 12 + 1, 1)
            me = int(cal.searchsorted(nm)) - 1
            if me < 0:
                continue
            u = U[:, d]
            with np.errstate(invalid="ignore", divide="ignore"):
                Rr = W.C[:, d] / W.C[:, me] - 1
            ok = u & np.isfinite(Rr)
            if not ok.any():
                continue
            Rx = Rr - Rr[ok].mean()
            self.e2M[(W.part, e)] = M
            for ct in ("C1", "C2"):
                g = np.flatnonzero(ok & CT[ct][i])
                if not len(g):
                    continue
                rk = pd.Series(Rx[g]).rank(method="average").to_numpy()
                top = g[rk > 2 * len(g) / 3]
                fail = ~CT[ct][:, :]
                for s in top:
                    # 之後第一個不符的營收月（有可用日者）
                    x = -1
                    for i2 in Mi[jj + 1:]:
                        if fail[i2, s]:
                            x = am[P[i2]]; break
                    for sel in ("S1", "S2"):
                        out[f"{ct}{sel}"].append((int(s), int(e), "open", int(x), "營收不再符合" if x > 0 else "未完", float(Rx[s])))
        return {c: pd.DataFrame(v, columns=["s", "e", "xk", "x", "why", "key"]) for c, v in out.items()}

    def early_window(self, W, log):
        REV = C.load_rev(log)
        T, Y = C.PRE.coverage(REV["rev"], REV["rev_ly"])
        y = Y[Y["市場"] == "twse"].set_index("年")["覆蓋率"]
        self.early_cov = {str(k): float(v) for k, v in y.items()}
        log(f"[早年覆蓋（上市）] {self.early_cov}")
        ok = [int(k) for k, v in y.items() if v >= 0.9]
        yrs = list(range(2005, 2015))
        start = None
        for yy in yrs:
            if all(z in ok for z in range(yy, 2015)):
                start = yy; break
        if start is None:
            self.early_note = "覆蓋率不足 ⇒ 不可判定"
            return None
        return (max(C.EARLY[0], f"{start}-01-01"), C.EARLY[1])

    def ifrs_share(self, W, F):
        Ms = [self.e2M.get((W.part, int(e)), "") for e in F["e"]]
        return float(np.mean([M.startswith("2013") for M in Ms])) if Ms else np.nan

    def extra_desc(self, W, U, chosen, log):
        return {}

    def extra_stats(self, W, U, FB, RES, chosen, seg, log):
        out = {"早年合併類「化學生技醫療」未剔（股-決策日）": int(getattr(self, "n_old", 0))}
        for c in self.cells:
            g = FB[c].groupby("e").size()
            out[f"{c} 每個 t0 候選數"] = C.q_(g.to_numpy())
        return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", nargs="?", default="run")
    ap.add_argument("--procs", type=int, default=2); ap.add_argument("--reps", type=int, default=200); ap.add_argument("--fake", type=int, default=200)
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    if a.cmd == "run":
        C.run_study(RevPriceOK(), a)
    elif a.cmd == "page":
        from backtest import researchPRE5page as PG
        PG.page(RevPriceOK())


if __name__ == "__main__":
    main()
