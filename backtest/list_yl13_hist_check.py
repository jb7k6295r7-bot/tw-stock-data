# -*- coding: utf-8 -*-
"""list_yl13_hist 的簡短查核（回測線，2026-09-28）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.list_yl13_hist_check

① 抽 10 筆入選（等距抽樣），直接從價格檔（D.load_stock，快照）重算：進場開盤、第 60 根收盤、報酬（扣 0.585%），
  並數「進場到出場之間的有效 K 棒 ＝ 60」；原始價與 data/stocks 原檔比對
② 入選筆數 ＝ 引擎 audit（audit_seed0.csv.gz）在期間內的買進筆數，且（代號, 進場日）集合相同
③ HTML：SVG 張數 ＝ 入選筆數，每張 SVG 可被 XML 解析
輸出 resultsYLlist/check.json
"""
from __future__ import annotations

import glob
import json
import os
import re
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

from . import rerun17 as RR

RR.use_snapshot()
from . import data as D  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "resultsYLlist")
COST = 0.00585
D0, D1 = "2025-08-01", "2026-06-30"


def main():
    cal = D.load_calendar()
    uni = D.load_universe().set_index("stock_id")["market"]
    L = pd.read_csv(glob.glob(os.path.join(OUT, "營量v1名單_*.csv"))[0], dtype={"代號": str})
    res = {"①抽10筆重算": [], "②audit": {}, "③HTML": {}}
    ok = True
    for i in np.linspace(0, len(L) - 1, 10).round().astype(int):
        r = L.iloc[i]; s = r["代號"]
        st = D.load_stock(s, uni.get(s, "twse"), cal)
        ti, to = cal.get_loc(pd.Timestamp(r["進場日"])), cal.get_loc(pd.Timestamp(r["出場日"]))
        o = float(np.float32(st.df["open"].iloc[ti])); c = float(np.float32(st.df["close"].iloc[to]))
        ret = (c / o - 1 - COST) * 100
        nbar = int(st.df["traded"].iloc[ti:to + 1].sum())
        raw = pd.read_csv(os.path.join(D.DATA, "stocks", f"{s}.csv"), dtype={"date": str}).drop_duplicates("date").set_index("date")
        ro, rc = float(raw.at[r["進場日"], "open"]), float(raw.at[r["出場日"], "close"])
        good = (abs(ret - r["報酬_扣成本_pct"]) < 1e-3 and nbar == 60 and abs(ro - r["進場價_原始"]) < 1e-6 and abs(rc - r["出場價_原始"]) < 1e-6
                and r["出場說明"].startswith("H60"))
        ok &= good
        res["①抽10筆重算"].append({"進場日": r["進場日"], "代號": s, "名單報酬": round(float(r["報酬_扣成本_pct"]), 6), "重算": round(ret, 6),
                                "有效K棒": nbar, "原始進場": ro, "原始出場": rc, "相符": bool(good)})
    A = pd.read_csv(os.path.join(OUT, "audit_seed0.csv.gz"), dtype={"sid": str})
    B = A[A["side"] == "buy"].copy()
    B["d"] = [str(cal[int(t)].date()) for t in B["t"]]
    B = B[(B["d"] >= D0) & (B["d"] <= D1)]
    same = set(zip(B["sid"], B["d"])) == set(zip(L["代號"], L["進場日"]))
    res["②audit"] = {"audit 期間買進": int(len(B)), "名單筆數": int(len(L)), "筆數相同": len(B) == len(L), "集合相同": bool(same)}
    ok &= len(B) == len(L) and same
    h = open(glob.glob(os.path.join(OUT, "營量v1_K線圖_*.html"))[0], encoding="utf-8").read()
    svgs = re.findall(r"<svg .*?</svg>", h, flags=re.S)
    bad = 0
    for sv in svgs:
        try:
            ET.fromstring(sv)
        except ET.ParseError:
            bad += 1
    ext = re.findall(r'(?:src|href)=["\'](?:https?:)?//', h)
    res["③HTML"] = {"SVG 張數": len(svgs), "解析失敗": bad, "外部資源": len(ext), "大小_bytes": len(h.encode("utf-8"))}
    ok &= len(svgs) == len(L) and bad == 0 and not ext
    res["全過"] = bool(ok)
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    if not ok:
        raise SystemExit("⛔ 查核不過")


if __name__ == "__main__":
    main()
