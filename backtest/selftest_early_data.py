# -*- coding: utf-8 -*-
"""early_data.py 的自測（⛔ 不讀報酬；全部用合成資料，另有兩項在已取出的早年快照上做結構斷言）。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.selftest_early_data

每一項先證明「分得出來」（〈一百三十〉fixture 先證不假紅）：正例、反例、以及把條件拿掉就會翻的變異。
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile

import numpy as np
import pandas as pd

from . import early_data as E

RES = []


def check(name, cond, detail=""):
    RES.append((name, bool(cond), detail))
    print(("✅" if cond else "⛔"), name, detail, flush=True)


def _rows(sid, spec, cal, market="twse"):
    """spec：{日: (close, change)}；不在 spec 的日子 ⇒ 整列不在；close=None ⇒ 列在價空（無成交）。"""
    out = []
    for d in cal:
        if d not in spec:
            continue
        c, ch = spec[d]
        out.append({"date": d, "stock_id": sid, "market": market, "close": np.nan if c is None else c, "change": np.nan if ch is None else ch})
    return out


def t_rule_ab():
    cal = [f"2013-01-{i:02d}" for i in range(1, 31)]
    rows = []
    # A：第 3 日有成交 10.0；4、5、6、7 整列消失（4 日）；第 8 日 close 8.0、change 0 ⇒ ref 8.0 ≠ 10 ⇒ A
    rows += _rows("A1", {cal[2]: (10.0, 0.0), cal[7]: (8.0, 0.0), cal[8]: (8.1, 0.1)}, cal)
    # 只消失 3 日 ⇒ 不是 A；跳 20% ⇒ 也不滿足 B（無成交只 3 日）⇒ 無
    rows += _rows("A3", {cal[2]: (10.0, 0.0), cal[6]: (8.0, 0.0)}, cal)
    # B：列在價空 4 日、跳 6% ⇒ B
    rows += _rows("B1", {cal[2]: (10.0, 0.0), cal[3]: (None, None), cal[4]: (None, None), cal[5]: (None, None), cal[6]: (None, None),
                         cal[7]: (10.6, 0.0)}, cal)
    # 列在價空 4 日、跳 4% ⇒ 無
    rows += _rows("B4", {cal[2]: (10.0, 0.0), cal[3]: (None, None), cal[4]: (None, None), cal[5]: (None, None), cal[6]: (None, None),
                         cal[7]: (10.4, 0.0)}, cal)
    # 天天有成交、除息日 ref ≠ 前收（change 寫 0）⇒ 無（absent 0、無成交 0）
    rows += _rows("X1", {cal[i]: (10.0 if i < 10 else 9.5, 0.0) for i in range(2, 15)}, cal)
    # 消失 4 日、但恢復日 change 空白 ⇒ 算不出 ref ⇒ 無
    rows += _rows("N1", {cal[2]: (10.0, 0.0), cal[7]: (8.0, None)}, cal)
    # 消失 4 日、ref ＝ 前收（差 0.01 元以內）⇒ 無
    rows += _rows("Z1", {cal[2]: (10.0, 0.0), cal[7]: (10.01, 0.01)}, cal)
    df = pd.DataFrame(rows)
    det = E.detect_rule_ab(df, cal)
    got = {(s, r) for s, _p, _d, r, _x in det}
    check("規則A：消失 4 日＋基準跳 ⇒ A", ("A1", "A") in got, str(det))
    check("規則A：只消失 3 日 ⇒ 不是 A", not any(s == "A3" for s, _ in got))
    check("規則B：價空 4 日＋跳 6% ⇒ B", ("B1", "B") in got)
    check("規則B：價空 4 日＋跳 4% ⇒ 無", not any(s == "B4" for s, _ in got))
    check("除息（天天有列）⇒ 無", not any(s == "X1" for s, _ in got))
    check("恢復日 change 空白 ⇒ 無", not any(s == "N1" for s, _ in got))
    check("ref 與前收差 0.01 元 ⇒ 無", not any(s == "Z1" for s, _ in got))
    check("A1 只記一筆（恢復後第二日不重記）", sum(1 for s, _ in got if s == "A1") == 1)
    # 變異：把門檻改成 3 ⇒ A3 翻成 A（證明 fixture 分得出來）
    det3 = E.detect_rule_ab(df, cal, absent_min=3)
    check("變異 absent_min=3 ⇒ A3 被抓（fixture 會翻）", any(s == "A3" and r == "A" for s, _p, _d, r, _x in det3))


def t_dedup():
    base = {"stock_id": "2330", "name": "台積電", "period": "2010-06", "market": "twse", "當月營收": "100", "去年當月營收": "90"}
    df = pd.DataFrame([{**base, "產業別": "電子工業"}, {**base, "產業別": "半導體業"},
                       {**base, "stock_id": "1101", "name": "台泥", "產業別": "水泥工業"}])
    d = E.dedup_revenue(df)
    check("營收去重：列數 3 → 2", len(d) == 2)
    check("營收去重：取細類「半導體業」", d.loc[d["stock_id"] == "2330", "產業別"].tolist() == ["半導體業"])
    bad = df.copy(); bad.loc[1, "當月營收"] = "101"
    try:
        E.dedup_revenue(bad); ok = False
    except SystemExit:
        ok = True
    check("營收去重：重複列除產業別外不同 ⇒ 拒收", ok)
    same = pd.DataFrame([{**base, "產業別": "電子工業"}, {**base, "產業別": "電子工業"}])
    check("營收去重：兩列都是電子工業 ⇒ 留一列", len(E.dedup_revenue(same)) == 1)


def t_roster():
    tmp = tempfile.mkdtemp()
    try:
        old = E.ROOT; E.ROOT = tmp
        rd = os.path.join(E.raw_dir("f" * 40), "data", "meta"); os.makedirs(rd)
        pd.DataFrame([{"stock_id": "2330", "name": "台積電", "market": "twse", "kind": "stock", "first_seen": "2015-01-05", "last_seen": "2026-09-24"}]).to_csv(
            os.path.join(rd, "stocks.csv"), index=False)
        dm = pd.DataFrame({"stock_id": ["2330", "2330", "1107", "9104", "0015"], "name": ["台積電", "台積電", "建台", "某DR", "富邦"],
                           "market": ["twse"] * 5, "date": ["2012-06-01", "2012-06-04", "2012-06-01", "2012-06-01", "2012-06-01"]})
        r0 = E.roster(dm, "f" * 40, None).set_index("stock_id")
        check("名冊：今日有的照抄 kind", r0.loc["2330", "kind"] == "stock")
        check("名冊：今日沒有 ⇒ 待裁 '?'（R2 未裁不猜）", (r0.loc[["1107", "9104", "0015"], "kind"] == "?").all())
        check("名冊：first／last 由日 K 自推", (r0.loc["2330", "first_seen"], r0.loc["2330", "last_seen"]) == ("2012-06-01", "2012-06-04"))
        ra = E.roster(dm, "f" * 40, "a").set_index("stock_id")
        check("名冊 R2a：四碼非 91 ⇒ stock；91xx、0 開頭 ⇒ other", (ra.loc["1107", "kind"], ra.loc["9104", "kind"], ra.loc["0015", "kind"]) == ("stock", "other", "other"))
    finally:
        E.ROOT = old; shutil.rmtree(tmp)


def t_use_early_strict():
    tmp = tempfile.mkdtemp()
    try:
        old = E.ROOT; E.ROOT = tmp
        vd = os.path.join(E.snap_dir("e" * 40), "R1a"); os.makedirs(os.path.join(vd, "data"))
        json.dump({"complete": False, "missing": ["M1"], "data": os.path.join(vd, "data")}, open(os.path.join(vd, "STATUS.json"), "w"))
        try:
            E.use_early("e" * 40, "R1a", strict=True); ok = False
        except SystemExit:
            ok = True
        check("use_early：版面不完整 ⇒ strict 拒絕", ok)
        from . import data as D
        keep = D.DATA
        p = E.use_early("e" * 40, "R1a", strict=False)
        check("use_early：strict=False 才指過去（結構閘門用）", p == os.path.join(vd, "data") and D.DATA == p)
        D.DATA = keep
    finally:
        E.ROOT = old; shutil.rmtree(tmp)


def t_snapshot():
    """已取出的快照上：0050 早年 cum 重算 ＝ 事件日 ≥ 列的 factor 連乘，且與主庫 cum 只差常數。"""
    p = os.path.join(E.raw_dir(), "data", "extra", "0050_adj_2012_2014.csv")
    if not os.path.exists(p):
        print("（略）快照未取出", flush=True); return
    a = E.adj_0050()
    f = a["factor"].to_numpy(float)
    exp = [float(np.prod(f[i:])) for i in range(len(f))]
    check("0050 cum 重算 ＝ ∏_{j≥i} factor", np.allclose(a["cum_factor"].to_numpy(float), exp, rtol=0, atol=1e-15))
    ratio = a["cum_factor_main"].to_numpy(float) / a["cum_factor"].to_numpy(float)
    check("0050 早年 cum 與主庫 cum 只差常數", float(np.ptp(ratio)) < 1e-6, f"比 {ratio}")


def main():
    t_rule_ab(); t_dedup(); t_roster(); t_use_early_strict(); t_snapshot()
    bad = [r for r in RES if not r[1]]
    print(f"== selftest_early_data：{len(RES) - len(bad)}／{len(RES)} 過", flush=True)
    if bad:
        sys.exit(1)


if __name__ == "__main__":
    main()
