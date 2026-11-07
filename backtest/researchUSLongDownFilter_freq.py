# -*- coding: utf-8 -*-
"""美股合理價機械版「可買」裡剔除【長期下跌】（年線版／半年線版）——頻率表＋描述欄乾跑（只描述、不判定、不計 N；⛔ 不算任何報酬）。

登錄：產業 seq96（pw1 sha 2b9b3d9778382198）§五「美股：同規則在美股機械版（seq63 登錄的那份）各跑一次，只描述」。
發號：裁定 seq498 §一（台股 2 格 N_單筆 +2；美股只描述、不計 N）。
補登錄：產業 seq101（pw1 1d4094ab4250c703）① 主量只算剔除組 ≥ 3 檔的月份 ⇒ 彙總加 TWL.seq101_block（同台股）；
      ④ 美股只描述、要用另外登錄。第一次美股乾跑在 seq101 送達前已開跑 ⇒ 跑完後用 --resummarize 只重出彙總（逐筆不變）：
    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSLongDownFilter_freq --resummarize
原版：美股合理價機械版（產業 seq63 ab44c6850399ff57；backtest/researchUSFairValue_freq.py 的 classify()，★1～★22、裁定 seq480／seq481 照舊）。
資料：私有庫 us-stock-data 89d9f8550f6ea39b392087c22998cd298164a26c（~/usdata/89d9f8550 唯讀快照，.commit 開跑先驗）。
私有：repo 的 resultsLongDownFilter/freq/ 只放每月筆數與彙總；逐檔明細只寫 ~/us_work/longdown/（repo 外）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchUSLongDownFilter_freq

程式重用（⛔ 不改原版、不寫第二份合理價實作）：
  - 母體、四條品質門檻、E0、g、配息率、本益比中位數、分組：直接呼叫 researchUSFairValue_freq.run(eval_list＝每月評估日, write=False)
    （classify() 對任意日 d 都只用 first_filed < d 的申報＝PIT，不需改口徑）。
  - 還原價：researchUSCheapTrend.adj_series（★T1：panel ret 連乘；ret 空白記 0）。
  - 長期下跌判斷、放行／新低計數：researchTWLongDownFilter_freq 的純函式（台美同一份）。
  - 1 年／3 年算得出：researchUSFairValue.Holder.window 的同一判法（評估日後 H 個 yahoo_GSPC 交易日都在日曆內）。

══════════ ★ 執行者定（看任何數字前寫死；台股 ★ 未列者同台股檔）══════════
 ★U1 評估日＝yahoo_GSPC 日曆每月第一個交易日，2020-04～2025-10（67 個月；同台股「每月」規則；seq63 原版是季末前一交易日 27 個）。
 ★U2 母體＝classify stage＝pop（在指數、有價、市值 ≥ 100 億美元）；可買＝group＝可買（倍數 ≤ 1.00；E0 ≤ 0 歸偏貴）。
 ★U3 有效 K 棒＝該檔 panel 列（同 researchUSCheapTrend ★T2）；均線、20 根前、「均線天數＋20」都數 panel 列，含評估日當列。
     評估日沒有 panel 列 ⇒ 不判（照報，併入「K 棒不足不判」另列原因）。
 ★U4 硬斷點（seq335 的美股對應）：相鄰兩個 panel 列之間缺 ≥ 5 個 yahoo_GSPC 交易日 ⇒ 壞根；回看窗內有壞根 ⇒ 不判（同台股 ★5）。
     ret 空白（來源切換日）照 ★T1 記 0、不算壞根。
 ★U5 1 年／3 年算得出＝評估日日曆位置 +250／+750 在 yahoo_GSPC 日曆內（Holder.window 同判法；只看日期）。
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
sys.path.insert(0, os.path.join(os.path.expanduser("~/tw-p17"), "backtest"))
sys.dont_write_bytecode = True
from backtest import researchUSFairValue_freq as FQ          # noqa: E402
from backtest import researchUSCheapTrend as UCT             # noqa: E402
import researchTWLongDownFilter_freq as TWL                  # noqa: E402

DATA_PIN = "89d9f8550f6ea39b392087c22998cd298164a26c"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsLongDownFilter", "freq")
PRIV = os.path.expanduser("~/us_work/longdown")
VERS, SLOPE, H1, H3 = TWL.VERS, TWL.SLOPE, TWL.H1, TWL.H3
SHORT, BRK, NOROW = TWL.SHORT, TWL.BRK, -3
GAP_BAD = 5


def month_dates(cal):
    out, seen = [], set()
    for d in cal:
        ym = str(d.date())[:7]
        if TWL.M_START <= ym <= TWL.M_END and ym not in seen:
            seen.add(ym)
            out.append(d)
    return out


class USStock:
    """與台股 Stock 同介面（px、bad、cb、pos、ma()、nl）。"""
    def __init__(self, t, cal):
        s = UCT.adj_series(t)
        self.dates = s.index
        self.px = s.values.astype(float)
        self.pos = cal.searchsorted(self.dates, side="left")
        gap = np.diff(self.pos) - 1
        self.bad = np.zeros(len(self.px), bool)
        if len(self.px) > 1:
            self.bad[1:] = gap >= GAP_BAD
        self.cb = TWL.cumbad(self.bad)
        self.at = {d: i for i, d in enumerate(self.dates)}
        self._ma, self._nl = {}, None

    def ma(self, N):
        if N not in self._ma:
            self._ma[N] = TWL.ma_arr(self.px, N)
        return self._ma[N]

    @property
    def nl(self):
        if self._nl is None:
            self._nl = TWL.newlow_flags(self.px)
        return self._nl


def main():
    import time
    t0 = time.time()
    if FQ.DATA_COMMIT_FULL != DATA_PIN:
        raise RuntimeError("合理價程式的資料 commit 與本件寫死的不同")
    FQ.assert_pinned()
    vreg = TWL.verify_registration()
    cal = FQ.calendar()
    months = month_dates(cal)
    assert len(months) == 67, len(months)
    R, _ = FQ.run(eval_list=months, write=False)
    print("classify 完成", round(time.time() - t0), "秒", flush=True)
    R = R[R["stage"] == "pop"].copy()
    STK = {}
    rows = []
    for _, x in R.iterrows():
        d = pd.Timestamp(x["eval"])
        r = dict(eval=x["eval"], ticker=x["ticker"], buy=int(x.get("group") == "可買"))
        if r["buy"]:
            t = x["ticker"]
            if t not in STK:
                STK[t] = USStock(t, cal) if UCT.adj_series(t) is not None else None
            st = STK[t]
            if st is None or d not in st.at:
                for vn, N in VERS:
                    r[f"ld_{vn}"] = NOROW
                r["nl"] = NOROW
            else:
                k = st.at[d]
                r["n_bars"] = k + 1
                for vn, N in VERS:
                    ma = st.ma(N)
                    c = TWL.longdown_code(st.px, ma, st.cb, k, N)
                    r[f"ld_{vn}"] = c
                    r[f"ld_{vn}_nobrk"] = TWL.longdown_code_nobrk(st.px, ma, k, N)
                    r[f"below_{vn}"] = TWL.below_only(st.px, ma, k) if c in (0, 1) else np.nan
                    if c == 1:
                        for kk, vv in TWL.release_info(st, k, N).items():
                            r[f"{kk}_{vn}"] = vv
                r["nl"] = TWL.newlow_code(st.nl, st.cb, k, True)
                r["nl_alt"] = TWL.newlow_code(st.nl, st.cb, k, False)
                if r["nl"] == 1:
                    tt, why = TWL.delayed_entry(st, k)
                    r["delay_status"] = why
                    r["delay_1y_cal"] = int(tt is not None and st.pos[tt] + H1 < len(cal))
            i = cal.get_loc(d)
            r["cal_1y"] = int(i + H1 < len(cal))
            r["cal_3y"] = int(i + H3 < len(cal))
        rows.append(r)
    P = pd.DataFrame(rows)
    os.makedirs(PRIV, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    P[P.buy == 1].to_csv(os.path.join(PRIV, "us_buy_rows_noreturn.csv"), index=False)

    trows = []
    for d in months:
        e = str(d.date())
        x = P[P["eval"] == e]
        b = x[x.buy == 1]
        for vn, N in VERS:
            c = b[f"ld_{vn}"] if len(b) else pd.Series(dtype=float)
            trows.append(dict(month=e[:7], eval=e, year=int(e[:4]), segment="前段" if e[:7] <= TWL.FRONT_END else "後段",
                              版本=vn, 母體=len(x), 全部可買=len(b), 濾網組=int((c == 0).sum()), 剔除組=int((c == 1).sum()),
                              K棒不足不判=int(c.isin([SHORT, NOROW]).sum()), 其中評估日無panel列=int((c == NOROW).sum()),
                              回看缺口不判=int((c == BRK).sum()), 不判合計=int(c.isin([SHORT, BRK, NOROW]).sum()),
                              一年出場在日曆內=int(cal.get_loc(d) + H1 < len(cal)),
                              三年出場在日曆內=int(cal.get_loc(d) + H3 < len(cal)),
                              加碼_有新低=int((b.get("nl", pd.Series(dtype=float)) == 1).sum()),
                              加碼_沒新低=int((b.get("nl", pd.Series(dtype=float)) == 0).sum())))
    T = pd.DataFrame(trows)
    T.to_csv(os.path.join(OUT, "us_freq_by_month.csv"), index=False, encoding="utf-8-sig")
    S = summarize(P, T, months, cal)
    S.update({"登錄": TWL.REG + "＋補登錄 產業 seq101 pw1 1d4094ab4250c703", "登錄驗證": vreg,
              "發號": TWL.RULING + "（美股只描述、不計 N）", "資料commit": DATA_PIN, "用時秒": round(time.time() - t0)})
    with open(os.path.join(OUT, "us_freq_summary.json"), "w", encoding="utf-8") as f:
        json.dump(S, f, ensure_ascii=False, indent=1, default=lambda v: v.item() if hasattr(v, "item") else str(v))
    pd.set_option("display.width", 250)
    print(T.pivot_table(index="month", columns="版本", values=["全部可買", "濾網組", "剔除組", "不判合計"]).to_string())
    print(json.dumps(S, ensure_ascii=False, indent=1, default=str))


def mstat(x):
    x = pd.Series(x)
    return [float(x.median()), int(x.min()), int(x.max())]


def summarize(P, T, months, cal):
    S = {"月數": len(months), "評估日": [str(months[0].date()), str(months[-1].date())],
         "母體每月_中位_最少_最大": mstat(T[T["版本"] == "年線"]["母體"])}
    B = P[P.buy == 1]
    for vn, N in VERS:
        t = T[T["版本"] == vn]
        o = {}
        for g in ("全部可買", "濾網組", "剔除組", "不判合計"):
            o[f"{g}_每月_中位_最少_最大"] = mstat(t[g])
        for g in ("濾網組", "剔除組"):
            o[f"{g}_≥1檔月數"] = int((t[g] >= 1).sum())
            o[f"{g}_≥1檔月數_前段"] = int(((t[g] >= 1) & (t.segment == "前段")).sum())
            o[f"{g}_≥1檔月數_後段"] = int(((t[g] >= 1) & (t.segment == "後段")).sum())
            o[f"{g}_年分群數"] = int(t[t[g] >= 1].year.nunique())
            o[f"{g}_總筆數"] = int(t[g].sum())
        o["K棒不足不判_總筆數"] = int(t["K棒不足不判"].sum())
        o["其中評估日無panel列"] = int(t["其中評估日無panel列"].sum())
        o["回看缺口不判_總筆數"] = int(t["回看缺口不判"].sum())
        o["不判合計_總筆數"] = int(t["不判合計"].sum())
        o["24門檻（照台股口徑，只描述）"] = bool(o["濾網組_≥1檔月數"] < 24 or o["剔除組_≥1檔月數"] < 24)
        o["seq101①_剔除組≥3檔月份（主量口徑，只描述）"] = TWL.seq101_block(t)
        j = B[B[f"ld_{vn}"] >= 0]
        nb, nld = int((j[f"below_{vn}"] == 1).sum()), int((j[f"ld_{vn}"] == 1).sum())
        o["seq377_收盤<均線筆數"], o["seq377_長期下跌筆數"] = nb, nld
        o["seq377_長期下跌≡收盤<均線"] = bool(nb == nld)
        o["剔除組為0的月數"] = int((t["剔除組"] == 0).sum())
        x = B[B[f"ld_{vn}"] == 1]
        if len(x):
            rm, r6 = x[f"rel_main_{vn}"], x[f"rel_ma60_{vn}"]
            dm, d6 = x[f"rel_main_bars_{vn}"], x[f"rel_ma60_bars_{vn}"]
            both = (rm == "released") & (r6 == "released")
            o["放行對照（只筆數）"] = {"被擋": len(x), "主規則放行": int((rm == "released").sum()),
                               "主規則250根內": int(((rm == "released") & (dm <= H1)).sum()),
                               "季線放行": int((r6 == "released").sum()),
                               "季線250根內": int(((r6 == "released") & (d6 <= H1)).sum()),
                               "未放行": int((rm == "never").sum()), "截尾": int((rm == "censored").sum()),
                               "季線早於主規則": int((both & (d6 < dm)).sum()), "同一根": int((both & (d6 == dm)).sum()),
                               "季線晚於主規則": int((both & (d6 > dm)).sum())}
        for g, c in (("濾網組", 0), ("剔除組", 1)):
            y = B[B[f"ld_{vn}"] == c]
            o[f"{g}_1年可算筆數"] = int((y.cal_1y == 1).sum())
            o[f"{g}_3年可算筆數"] = int((y.cal_3y == 1).sum())
        S[vn] = o
    sy = set(zip(B["eval"][B["ld_年線"] == 1], B.ticker[B["ld_年線"] == 1]))
    sh = set(zip(B["eval"][B["ld_半年線"] == 1], B.ticker[B["ld_半年線"] == 1]))
    S["seq377_兩版剔除名單"] = {"年線": len(sy), "半年線": len(sh), "交集": len(sy & sh),
                          "Jaccard": (len(sy & sh) / len(sy | sh)) if (sy | sh) else None, "完全相同": bool(sy == sh)}
    S["描述欄乾跑"] = {
        "1年出場在日曆內的月數": int(sum(cal.get_loc(d) + H1 < len(cal) for d in months)),
        "2025-10進場+250在日曆內": bool(cal.get_loc(months[-1]) + H1 < len(cal)),
        "日曆最後一日": str(cal[-1].date()),
        "3年出場在日曆內的月數": int(sum(cal.get_loc(d) + H3 < len(cal) for d in months)),
        "全部可買_1年可算筆數": int((B.cal_1y == 1).sum()), "全部可買_3年可算筆數": int((B.cal_3y == 1).sum()),
        "加碼對照": {"有新低": int((B.get("nl") == 1).sum()), "沒新低": int((B.get("nl") == 0).sum()),
                 "不判": int(B.get("nl").isin([SHORT, BRK, NOROW]).sum()),
                 "另一讀法_有新低": int((B.get("nl_alt") == 1).sum()),
                 "延後版_找到": int((B.get("delay_status") == "found").sum()) if "delay_status" in B else 0,
                 "延後版_+250在日曆內": int((B.get("delay_1y_cal") == 1).sum()) if "delay_1y_cal" in B else 0},
        "說明": "只報筆數；⛔ 未讀任何持有期報酬"}
    return S


def resummarize():
    """--resummarize：不重跑 classify，讀上次乾跑存下的每月表（repo）與可買逐筆（~/us_work，無報酬欄）重出彙總。
    （產業 seq101 補登錄在第一次美股乾跑途中送達，只加彙總欄；逐筆判斷不變。）"""
    FQ.assert_pinned()
    vreg = TWL.verify_registration()
    cal = FQ.calendar()
    months = month_dates(cal)
    T = pd.read_csv(os.path.join(OUT, "us_freq_by_month.csv"), encoding="utf-8-sig")
    P = pd.read_csv(os.path.join(PRIV, "us_buy_rows_noreturn.csv"), dtype={"eval": str, "ticker": str})
    old = json.load(open(os.path.join(OUT, "us_freq_summary.json"), encoding="utf-8"))
    S = summarize(P, T, months, cal)
    S.update({"登錄": TWL.REG + "＋補登錄 產業 seq101 pw1 1d4094ab4250c703", "登錄驗證": vreg,
              "發號": TWL.RULING + "（美股只描述、不計 N）", "資料commit": DATA_PIN,
              "用時秒": old.get("用時秒"), "彙總重出": "--resummarize（seq101 加欄；逐筆未重算）"})
    with open(os.path.join(OUT, "us_freq_summary.json"), "w", encoding="utf-8") as f:
        json.dump(S, f, ensure_ascii=False, indent=1, default=lambda v: v.item() if hasattr(v, "item") else str(v))
    print(json.dumps(S, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    if "--resummarize" in sys.argv[1:]:
        resummarize()
    else:
        main()
