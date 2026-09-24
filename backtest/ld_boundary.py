# -*- coding: utf-8 -*-
"""研究十三 LD 出場的【邊界例外】次數（本線 1722 §一 報過這個例外，⛔ 但從沒數過）。

`research11.cond_exit` 逐字：
    「從 k+1 起逐根看 cond(j)；成立 → j+1 開盤出（無則 j 收盤）；上限 k+CAP 收盤。」
⇒ 「無則」＝ j+1 超過資料尾（j+1 > n−1）或 j+1 落在壞根窗（j+1 ≥ nb）⇒ 退回 j 收盤
   ＝ ⭐ 同一根既判定又成交。

⛔ 不改共用引擎：本支用【包裝】數 —— 呼叫原函式取答案，另外重放一次只為了定位 j，
   ⭐ 而每一次呼叫都 assert「重放的分類」與「原函式的回傳」一致 ⇒ 引擎仍是唯一真相。

⚠⚠ 本支同時發現：這個次數是資料快照的函數，⛔ 不是常數（§二）。
"""
from __future__ import annotations
import os
import sys
import collections
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import data as D
from backtest import research11 as R
from backtest import research13 as R13

CAP = R.CAP
CNT = collections.Counter()
DET = []
_orig = R.cond_exit
_CTX = {"sid": None}


def counting_cond_exit(o, c, k, nb, cond):
    r = _orig(o, c, k, nb, cond)
    n = len(c)
    last = min(n - 1, k + CAP)
    if last >= nb:
        lab = "none_窗不足"
        assert r is None, "⛔ 重放說 None，引擎回 {!r}".format(r)
    else:
        j = None
        for jj in range(k + 1, last + 1):
            if cond(jj):
                j = jj
                break
        if j is None:
            lab = "cap_抱到上限"
            assert r is not None and r[0] == last and r[2] is False, \
                "⛔ 重放說抱到上限 last={}，引擎回 {!r}".format(last, r)
            DET.append(dict(sid=_CTX["sid"], k=k, j=-1, n=n, nb=nb, last=last, 路徑=lab,
                            上限是資料尾=bool(last == n - 1)))
        else:
            tail = (j + 1 > n - 1)
            badw = (j + 1 >= nb)
            if not tail and not badw:
                lab = "normal_次日開盤"
                assert r[0] == j + 1 and r[2] is True, \
                    "⛔ 重放說次日開盤 j+1={}，引擎回 {!r}".format(j + 1, r)
            else:
                lab = ("exc_資料尾" if tail and not badw else
                       "exc_壞根窗" if badw and not tail else "exc_兩者同時")
                assert r[0] == j and r[2] is True, \
                    "⛔ 重放說退回 j 收盤 j={}，引擎回 {!r}".format(j, r)
                DET.append(dict(sid=_CTX["sid"], k=k, j=j, n=n, nb=nb, last=last, 路徑=lab,
                                上限是資料尾=bool(last == n - 1)))
    CNT[lab] += 1
    return r


print("=== ① 前提 ===")
print("  引擎常數 CAP ＝ {} 根（cond_exit 的持有上限）".format(CAP))
cal = D.load_calendar()
uni = D.load_universe()
print("  ⭐ 本支跑的資料快照：日曆 {:,} 根，最後一日 {}".format(len(cal), cal[-1].date()))
panel = pd.read_csv("backtest/results3/panel.csv.gz", dtype={"stock_id": str})
panel["rev_hi24"] = panel["rev_hi24"].fillna(False).astype(bool)
gpos = {sid: g["signal_pos"].to_numpy() for sid, g in panel[panel["rev_hi24"]].groupby("stock_id")}
mk = uni.set_index("stock_id")["market"].to_dict()
tasks = [(s, mk[s]) for s in sorted(gpos) if s in mk]
print("  G1（月營收創 24 月新高）訊號涵蓋 {:,} 檔（都在母體內）".format(len(tasks)))

R.cond_exit = counting_cond_exit
R13._G["cal"] = cal
R13._G["gpos"] = gpos
rows = []
for t in tasks:
    _CTX["sid"] = t[0]
    out = R13.g_exits(t)
    if out:
        rows.extend(out["rows"])
R.cond_exit = _orig
G = pd.DataFrame(rows)

print()
print("=== ② ⛔⛔ 錨沒過 —— 而錨沒過本身就是答案的一半 ===")
old = pd.read_csv("backtest/results13/g1_signals.csv.gz", dtype={"sid": str})
print("  交件 results13/g1_signals.csv.gz  {:,} 筆／{:,} 檔".format(len(old), old["sid"].nunique()))
print("  本支重跑                          {:,} 筆／{:,} 檔".format(len(G), G["sid"].nunique()))
a = G.set_index(["sid", "g1_pos"]).sort_index()
b = old.set_index(["sid", "g1_pos"]).sort_index()
new_only = sorted(set(a.index) - set(b.index))
old_only = sorted(set(b.index) - set(a.index))
print("  只在重跑裡 {} 筆：{}".format(len(new_only), new_only))
print("  只在交件裡 {} 筆：{}".format(len(old_only), old_only))
assert old_only == [], "⛔ 交件有而重跑沒有 ⇒ 那是退步，要查"
assert [s for s, _ in new_only] == ["4166"], "⛔ 多出來的不只 4166：{}".format(new_only)
_b = R.load_bars("4166", mk["4166"], cal)
print("  ⇒ ⭐ 4166 友霖：現在有效 K 棒 {} 根、load_bars 門檻 260".format(len(_b["idx"])))
print("     ⇒ 交件那天不足 260 ⇒ 被 load_bars 回 None【整檔】排除")

com = a.index.intersection(b.index)
_nx = a.loc[com, "xpos_LD"].to_numpy()
_ox = b.loc[com, "xpos_LD"].to_numpy()
dx = _nx != _ox
dg = ~np.isclose(a.loc[com, "g_LD"].to_numpy(float), b.loc[com, "g_LD"].to_numpy(float),
                 equal_nan=True)
print("  共有 {:,} 筆｜xpos_LD 變了 {:,} 筆｜g_LD 變了 {:,} 筆".format(
    len(com), int(dx.sum()), int(dg.sum())))

TAIL = len(cal) - 1
nx = _nx[dx]
ox = _ox[dx]
c_tail = int((nx == TAIL).sum())
c_none = int((nx == -1).sum())
c_real = int(((nx != TAIL) & (nx != -1)).sum())
print("  ⇒ ⭐ 那 {} 筆逐類分（⛔ 本支第一版寫「全部貼在資料尾」，斷言當場擋下來）：".format(int(dx.sum())))
print("     (a) 新出場 ＝ 資料尾 {} ⇒ {:,} 筆".format(TAIL, c_tail))
print("         ⇒ 出場日是【資料尾決定的】，⛔ 不是規則決定的 ⇒ 資料長幾天就往後移幾天")
print("     (b) 新出場在尾之前、且與舊不同 ⇒ {:,} 筆".format(c_real))
print("         ⇒ ⭐ 在【新加進來的那幾根】上真的觸發了跌停 ⇒ 規則真的動了")
print("     (c) 新出場 ＝ −1（cond_exit 回 None、窗不足）⇒ {:,} 筆".format(c_none))
print("         ⇒ ⚠ 新資料裡出現壞根 ⇒ nb 前移 ⇒ 原本算得出的出場現在整筆不算")
assert c_tail + c_real + c_none == int(dx.sum()), "⛔ 三類加不回總數"
nt = pd.DataFrame({"sid": [c[0] for c in com[dx]], "g1_pos": [c[1] for c in com[dx]],
                   "新xpos": nx, "舊xpos": ox})
print()
print("  ⚠ (b)(c) 那 {} 筆逐筆列出（⛔ 不可只報 (a)）：".format(c_real + c_none))
print(nt[nt["新xpos"] != TAIL].to_string(index=False))
print()
print("  ⚠ g_LD 變了 {:,} 筆 > xpos 變了 {:,} 筆 ⇒ 差額 {:,} 筆是【還原價序列本身變了】".format(
    int(dg.sum()), int(dx.sum()), int(dg.sum()) - int(dx.sum())))
print("     （新的除權息事件改寫整條還原序列 ⇒ 出場日相同、報酬仍不同）")
print("  ⇒ ⛔ 所以交件的 results13 在今天這棵樹上【無法逐位重現】，")
print("     ⭐ 而那不是 bug，是資料新鮮度 ⇒ 下面的次數必須連【快照】一起報。")

print()
print("=== ③ ⭐⭐ LD 出場四條路各走幾次（快照：日曆 {} 根／尾 {}）===".format(len(cal), cal[-1].date()))
tot = sum(CNT.values())
for kk in ["normal_次日開盤", "exc_資料尾", "exc_壞根窗", "exc_兩者同時", "cap_抱到上限", "none_窗不足"]:
    v = CNT.get(kk, 0)
    print("  {:16s} {:7,}  ({:6.3f}%)".format(kk, v, v / tot * 100 if tot else 0))
print("  {:16s} {:7,}".format("合計呼叫", tot))
exc = sum(CNT.get(x, 0) for x in ("exc_資料尾", "exc_壞根窗", "exc_兩者同時"))
eff = tot - CNT.get("none_窗不足", 0)
print()
print("  ⇒ ⭐⭐ 邊界例外（無則 j 收盤 ＝ 同一根既判定又成交）{:,} 次".format(exc))
print("     占全部呼叫 {:.4f}%｜占有效出場（扣掉窗不足）{:.4f}%".format(
    exc / tot * 100 if tot else 0, exc / eff * 100 if eff else 0))
print("  ⇒ LD 實際算得出報酬的筆數（g_LD 非 NaN）＝ {:,}".format(int(G["g_LD"].notna().sum())))
print("     其中 t_LD True（條件成立才出，⛔ 非抱到上限）＝ {:,}".format(int(G["t_LD"].astype(bool).sum())))

dd = pd.DataFrame(DET)
cp = dd[dd["路徑"] == "cap_抱到上限"] if len(dd) else dd
if len(cp):
    print()
    print("=== ④ ⭐ 同族的另一件：抱到上限的筆，多少是【上限就是資料尾】 ===")
    k = int(cp["上限是資料尾"].sum())
    print("  抱到上限 {:,} 筆，其中 last ＝ n−1（資料尾）{:,} 筆（{:.2f}%）".format(
        len(cp), k, k / len(cp) * 100))
    print("  ⇒ ⭐ 這 {:,} 筆的「抱到上限」是【資料不夠】，⛔ 不是抱滿 {} 根".format(k, CAP))
    print("     ⇒ ⚠ 它們正是 §二 (a) 那 {} 筆位移的來源族".format(c_tail))
ex = dd[dd["路徑"] != "cap_抱到上限"] if len(dd) else dd
if len(ex):
    print()
    print("=== ⑤ 那 {} 次邊界例外的樣貌 ===".format(len(ex)))
    print(ex["路徑"].value_counts().to_string())
    print()
    print(ex.head(15).to_string(index=False))

os.makedirs("backtest/results_step2", exist_ok=True)
if len(dd):
    dd.to_csv("backtest/results_step2/ld_boundary_cases.csv", index=False, encoding="utf-8")
nt.to_csv("backtest/results_step2/ld_xpos_moved.csv", index=False, encoding="utf-8")
pd.Series(CNT, name="次數").rename_axis("路徑").to_csv(
    "backtest/results_step2/ld_boundary_tally.csv", encoding="utf-8")
print()
print("⇒ 落檔 results_step2/ld_boundary_tally.csv、ld_boundary_cases.csv、ld_xpos_moved.csv")
