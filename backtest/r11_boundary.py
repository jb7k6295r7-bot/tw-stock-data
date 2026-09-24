# -*- coding: utf-8 -*-
"""研究十一 主格的 cond_exit 邊界例外次數（A2／A3／M5／LD 四條規則）——研究十三 LD 那次的同族延伸。

cond_exit 逐字：「成立 → j+1 開盤出（無則 j 收盤）」⇒ 例外路 ＝ 同一根既判定又用收盤成交。
⚠ 研究十一的 A2／A3 是【有狀態】的條件（追蹤最高價與停損線）⇒ ⛔ 不能像 ld_boundary.py 那樣重放 cond
   （重放會把狀態再推一次，得到錯的 j）
✅ 改成【不重放】：只看引擎自己的回傳分類
   例外路回 (j, c[j]/ep−1, True)；正常路回 (j+1, o[j+1]/ep−1, True)
   ⇒ 報酬逐位等於「收盤版」而不等於「開盤版」⇒ 例外；反之 ⇒ 正常
   ⇒ o[idx] == c[idx] 時兩版相同 ⇒ 再用邊界條件判：該根不在任何邊界 ⇒ 只可能是正常；在邊界 ⇒ 記「無法區分」
⛔ 不改共用引擎：只在本行程把 research11.cond_exit 換成包裝；stock_features 在呼叫時才解析全域名 ⇒ 包裝生效。
用法：python r11_boundary.py [--limit N] [--fixture-only]
"""
from __future__ import annotations
import os
import sys
import time
import collections
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import research11 as R

CAP = R.CAP
_orig = R.cond_exit
CNT = collections.Counter()
EXC = []
_CTX = {"sid": None}


def rule_of(cond):
    d = cond.__defaults__
    if d and len(d) == 2 and isinstance(d[1], float):
        return "A2" if d[1] == 2.0 else ("A3" if d[1] == 3.0 else "A?")
    fv = cond.__code__.co_freevars
    if "ma5" in fv:
        return "M5"
    if "dn" in fv:
        return "LD"
    return "其他"


def classify(o, c, k, nb, r):
    n = len(c)
    last = min(n - 1, k + CAP)
    if r is None:
        assert last >= nb, "⛔ 引擎回 None 但 last < nb"
        return "none_窗不足", None
    idx, ret, hit = r
    if not hit:
        assert idx == last, "⛔ 未觸發但出場根 ≠ last"
        return "cap_抱到上限", None
    ep = o[k + 1]
    v_close = c[idx] / ep - 1
    v_open = o[idx] / ep - 1
    tail, badw = (idx + 1 > n - 1), (idx + 1 >= nb)
    why = ("資料尾" if tail and not badw else "壞根窗" if badw and not tail else "兩者同時")
    if ret == v_close and ret != v_open:
        assert tail or badw, "⛔ 報酬是收盤版，但 idx 不在任何邊界"
        return "exc_" + why, idx
    if ret == v_open and ret != v_close:
        return "normal_次日開盤", None
    assert ret == v_open == v_close, "⛔ 報酬既不是開盤版也不是收盤版"
    if not (tail or badw):
        return "normal_次日開盤", None           # 不在邊界 ⇒ 例外路不可能
    return "ambig_開收同價且在邊界", idx


def wrapper(o, c, k, nb, cond):
    r = _orig(o, c, k, nb, cond)
    lab, idx = classify(o, c, k, nb, r)
    rl = rule_of(cond)
    CNT[(rl, lab)] += 1
    if idx is not None:
        EXC.append(dict(sid=_CTX["sid"], rule=rl, k=k, idx=idx, n=len(c), nb=nb, 路徑=lab))
    return r


def fixture():
    """⭐ 先證明分類器會響（〈追六六〉）：五條路各造一次，含有狀態的條件。"""
    global CNT
    save = CNT; CNT = collections.Counter()
    n_exc0 = len(EXC)
    o = np.arange(1.0, 41.0); c = o + 0.5
    n = len(c)
    wrapper(o, c, 5, 999, lambda j: j == n - 1)                       # 資料尾例外（k+CAP ≥ n−1）
    wrapper(o, c, 5, 999, lambda j: j == 10)                          # 正常
    wrapper(o, c, 5, 999, lambda j: False)                            # 抱到上限
    o2 = np.arange(1.0, 401.0); c2 = o2 + 0.5
    k = 10; nb = k + CAP + 1; last = min(len(c2) - 1, k + CAP)
    wrapper(o2, c2, k, nb, lambda j: j == last)                       # 壞根窗例外
    wrapper(o2, c2, k, k + CAP, lambda j: True)                       # 窗不足 None
    st = {"hi": -np.inf}
    def cond(j, st_=st, kx=2.0):                                      # 有狀態、且只能被叫一次的條件
        st_["hi"] = max(st_["hi"], c[j]); return j == n - 1
    wrapper(o, c, 5, 999, cond)
    got = {lab for (_, lab) in CNT}
    need = {"exc_資料尾", "normal_次日開盤", "cap_抱到上限", "exc_壞根窗", "none_窗不足"}
    assert need <= got, "⛔ fixture 少了路：{}".format(need - got)
    assert CNT[("A2", "exc_資料尾")] == 1, "⛔ 有狀態條件的例外沒被正確分類"
    print("✅ fixture：五條路都被分到、有狀態的條件（A2）也分對 ⇒ 分類器會響")
    CNT = save
    del EXC[n_exc0:]   # ⛔ fixture 的例外不可混進真資料的清單


if __name__ == "__main__":
    fixture()
    if "--fixture-only" in sys.argv:
        sys.exit(0)
    lim = None
    if "--limit" in sys.argv:
        lim = int(sys.argv[sys.argv.index("--limit") + 1])
    cal = D.load_calendar(); uni = D.load_universe()
    R._init(cal)
    R.cond_exit = wrapper
    tasks = [(r.stock_id, r.market, r.first_seen) for r in uni.itertuples()]
    if lim:
        tasks = tasks[:lim]
    t0 = time.time(); nmain = 0
    for i, t in enumerate(tasks):
        _CTX["sid"] = t[0]
        out = R.stock_features(t)
        if out:
            nmain += len(out["main"])
        if (i + 1) % 200 == 0:
            print("  {}/{}  {:.0f}s".format(i + 1, len(tasks), time.time() - t0), file=sys.stderr, flush=True)
    R.cond_exit = _orig
    print("\n=== 快照：日曆 {} 根／尾 {}｜跑 {} 檔｜主格訊號 {:,} 筆｜{:.0f}s ===".format(
        len(cal), cal[-1].date(), len(tasks), nmain, time.time() - t0))
    rows = []
    for rl in ("A2", "A3", "M5", "LD"):
        d = {lab: CNT[(rl, lab)] for (r_, lab) in CNT if r_ == rl}
        tot = sum(d.values())
        exc = sum(v for k2, v in d.items() if k2.startswith("exc_"))
        amb = sum(v for k2, v in d.items() if k2.startswith("ambig"))
        rows.append(dict(規則=rl, 呼叫=tot, 例外=exc, 無法區分=amb,
                         正常=d.get("normal_次日開盤", 0), 抱到上限=d.get("cap_抱到上限", 0),
                         窗不足=d.get("none_窗不足", 0),
                         例外占有效出場=round(exc / max(1, tot - d.get("none_窗不足", 0)) * 100, 4)))
    T = pd.DataFrame(rows)
    print(T.to_string(index=False))
    if EXC:
        E = pd.DataFrame(EXC)
        print("\n例外逐類：")
        print(E.groupby(["rule", "路徑"]).size().to_string())
    others = {k2: v for k2, v in CNT.items() if k2[0] not in ("A2", "A3", "M5", "LD")}
    assert not others, "⛔ 有辨識不出規則的呼叫：{}".format(others)
    if not lim:
        os.makedirs("backtest/results_step2", exist_ok=True)
        T.to_csv("backtest/results_step2/r11_boundary_tally.csv", index=False, encoding="utf-8")
        if EXC:
            pd.DataFrame(EXC).to_csv("backtest/results_step2/r11_boundary_cases.csv", index=False, encoding="utf-8")
        print("⇒ 落檔 backtest/results_step2/r11_boundary_tally.csv")
