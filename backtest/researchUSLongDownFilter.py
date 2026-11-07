# -*- coding: utf-8 -*-
"""美股合理價機械版「可買」裡剔除【長期下跌】（年線版／半年線版）——正式跑（只描述、不判定、不計 N）。

登錄：產業 seq96 §五「美股同規則在美股機械版（seq63）各跑一次，只描述」＋產業 seq101 ④（美股只描述、要用另外登錄）。
發號：裁定 seq498 §一（美股只描述、不計 N）；正式跑：裁定 seq499（閘門同台股：`--formal --ruling seq499` 兩個都要）。
分組：直接呼叫頻率表 researchUSLongDownFilter_freq.build()（★U1～★U5 一字不改）；統計、放行／加碼對照呼叫台股正式檔的同一份函式
      （researchTWLongDownFilter：month_table、cell、boot_ci、version_block、release_block、addon_block）。
私有：repo 的 resultsLongDownFilter/formal/us_result.json 只放彙總；逐筆（含報酬、逐檔主導列表）只寫 ~/us_work/longdown/。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSLongDownFilter --formal --ruling seq499

══════════ ★UF 執行者定（看任何報酬前寫死）══════════
 ★UF1 1 年／3 年報酬＝美股機械版 seq63 原口徑：researchUSFairValue.Holder(dry=False).daily(t, 評估日, H) 連乘
       （評估日收盤後 H 個 yahoo_GSPC 交易日的 panel 日報酬；空白、缺口、出指數後記 0；整段無價格 −100%；窗不滿 ⇒ 不可算）。
 ★UF2 放行日／延後進場日起算同 ★UF1（起點換成放行／延後進場那一列的日期）。
 ★UF3 放行時（延後進場時）仍可買＝該日 researchUSFairValue_freq.classify(t, 該日) 的 group＝可買（PIT 同 seq63）。
 ★UF4 其餘（主量、剔除組 ≥ 3 檔月份、97.5% 月分群 CI、年分群、前後段、中位數差、拿掉 2022、少數股主導準則）同台股 ★F；
       只描述，⛔ 不寫通過／測不出。
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
sys.path.insert(0, os.path.join(os.path.expanduser("~/tw-p17"), "backtest"))
sys.dont_write_bytecode = True
from backtest import researchUSFairValue_freq as FQ          # noqa: E402
from backtest import researchUSFairValue as UFV              # noqa: E402
import researchUSLongDownFilter_freq as UL                   # noqa: E402
import researchTWLongDownFilter as F                         # noqa: E402

gate = F.gate
PRIV = UL.PRIV


class USAdapter:
    def __init__(self, STK, cal):
        self.STK, self.cal = STK, cal
        self.h = UFV.Holder(dry=False)

    def k(self, s, E):
        return self.STK[s].at[pd.Timestamp(E)]

    def _ret_from(self, s, d, H):
        try:
            r = self.h.daily(s, d, H)
        except KeyError:
            return np.nan, 'nocal'
        return (np.nan, 'cal') if r is None else (UFV.cum(r), 'ok')

    def ret(self, s, k, H):
        return self._ret_from(s, self.STK[s].dates[k], H)

    def still(self, s, k):
        r = FQ.classify(s, pd.Timestamp(self.STK[s].dates[k]), Counter())
        return int(r.get("stage") == "pop" and r.get("group") == "可買")

    def cal_ok(self, E, H):
        return self.cal.get_loc(pd.Timestamp(E)) + H < len(self.cal)


def compute_us():
    vreg = UL.preflight()
    v101 = F.verify_seq101()
    cal = FQ.calendar()
    months = UL.month_dates(cal)
    assert len(months) == 67, len(months)
    P, STK = UL.build(cal, months)
    ad = USAdapter(STK, cal)
    B = P[P.buy == 1].copy().rename(columns={"eval": "E", "ticker": "stock_id"}).reset_index(drop=True)
    B["year"] = B.E.str[:4].astype(int)
    B["segment"] = B.E.map(F.seg_of)
    r1, s1, r3, s3 = [], [], [], []
    for E, s in zip(B.E.values, B.stock_id.values):
        a, b = ad._ret_from(s, E, UL.H1); r1.append(a); s1.append(b)
        a, b = ad._ret_from(s, E, UL.H3); r3.append(a); s3.append(b)
    B["R1"], B["R1_status"], B["R3"], B["R3_status"] = r1, s1, r3, s3
    V, TT, addon = F.run_versions(B, None, ad, with_verdict=False)
    os.makedirs(PRIV, exist_ok=True)
    priv = {vn: {"少數股主導_前5檔": V[vn]["少數股主導"]["前5檔"], "逐筆列表": V[vn].pop("逐筆列表")} for vn, _ in UL.VERS}
    for vn, _ in UL.VERS:
        V[vn]["少數股主導"]["前5檔"] = [dict(拿掉後主量=r["拿掉後主量"], 變動=r["變動"], 觸發=r["觸發"])
                                  for r in V[vn]["少數股主導"]["前5檔"]]
    keep = ["E", "stock_id", "ld_年線", "ld_半年線", "nl", "R1", "R1_status", "R3", "R3_status"]
    B[keep].to_csv(os.path.join(PRIV, "us_formal_rows.csv"), index=False)
    pd.concat([TT[vn].assign(版本=vn) for vn, _ in UL.VERS]).to_csv(os.path.join(PRIV, "us_formal_month_table.csv"), index=False)
    json.dump(F._clean(priv), open(os.path.join(PRIV, "us_formal_dominance_rows.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1, default=F._js)
    out = dict(header=dict(登錄="產業 seq96 pw1 %s＋產業 seq101 pw1 %s（美股只描述、不計 N）" % (vreg["pw1"], v101["pw1"]),
                           正式跑="裁定 seq499（--formal --ruling seq499）", 資料commit=UL.DATA_PIN, SEED=F.SEED,
                           NBOOT=F.NBOOT, CI=F.CI_LEVEL),
               判語="只描述、不判定、不計 N（seq96 §五、seq498）",
               R1不可算=int(B.R1.isna().sum()), Holder計數=dict(ad.h.cnt),
               版本=V, 加碼對照=addon)
    return out


def main_formal():
    out = compute_us()
    od = F.OUTF
    os.makedirs(od, exist_ok=True)
    json.dump(F._clean(out), open(os.path.join(od, "us_result.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=F._js)
    if os.path.exists(os.path.join(od, "result.json")):
        F.write_md(od)
    print(json.dumps(F._clean({vn: out["版本"][vn]["主格"] for vn in ("年線", "半年線")}), ensure_ascii=False, indent=1,
                     default=F._js))


if __name__ == "__main__":
    m = gate(sys.argv[1:])
    if isinstance(m, tuple):
        sys.exit(m[1])
    main_formal()
