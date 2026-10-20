# -*- coding: utf-8 -*-
"""出場第三輪 seq1 正式跑【對帳】——回測線計算子代理。⛔ 只讀 backtest/resultsExit3/（freq/ 外）與資料；輸出 resultsExit3/check.json、check.log。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchExit3_check

C1 抽 20 筆手算：另寫一份逐根迴圈（pandas rolling 20 日均、逐日走訪找觸發、DataFrame 篩候選與持有）重算帳戶值 V 與 ①，比 events_d。
C2 對照重建：exit3.json 的 trades_r0／events_r0 逐列相同旗標；候選數（Q4）與頻率表一致。
C3 不前視：判斷日 ∈ [T＋1, E−1]、賣日 ＞ 判斷日、賣日 ≤ E；立即換的賣日 ＞ T；營收轉負的判斷日 ＝ 該期可用日。
C4 彙總重算：判定表 7 格兩段（合併、T＋120）由逐事件檔重算 d 平均、CI、結果、整格；對照組改放 0050 比例重算。
C5 策略鎖。
"""
from __future__ import annotations

import json
import os
import pickle
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchExit3 as X3                    # noqa: E402
from backtest import researchExit3_freq as XF               # noqa: E402
from backtest import researchYL_integrate as IG             # noqa: E402
from backtest import researchAddOn as RA                    # noqa: E402
from backtest import research11 as R                        # noqa: E402
from backtest import research34 as R34                      # noqa: E402
from backtest import data as D                              # noqa: E402

OUT = X3.OUT
LOG = []
OK = {}


def log(s):
    print(s, flush=True); LOG.append(s)


def chk(name, cond, detail=""):
    OK[name] = bool(cond)
    log(f"{'✅' if cond else '❌'} {name} {detail}")


def main():
    J = json.load(open(os.path.join(OUT, "exit3.json"), encoding="utf-8"))
    DD = pd.read_csv(os.path.join(OUT, "events_d.csv.gz"), dtype={"sid": str, "事件月": str})
    VER = pd.read_csv(os.path.join(OUT, "判定表.csv"))
    WS = {}
    WS["主"], _ = IG.main_world(log)
    WS["早年"], _ = IG.early_world(log, 2)
    BAD = {}
    for wn, part in (("主", "main"), ("早年", "early")):
        B = pickle.load(open(os.path.join(RA.CRASH_WORK, f"bad_{part}.pkl"), "rb"))
        BAD[wn] = {s: set(int(x) for x in a_) | set(int(x) for x in b_) for s, (a_, b_) in B.items()}
    Wa = pickle.load(open(os.path.join(RA.WORK, "world_早年.pkl"), "rb"))
    EX, _ = RA.early_extra_bad(Wa, lambda *x: None)
    for s, ks in EX.items():
        BAD["早年"].setdefault(s, set()).update(int(k) for k in ks)
    TRD = {}
    for wn in ("主", "早年"):
        for sn, S in XF.STR.items():
            o, au = IG.eng(WS[wn], S["key"], 0, audit=True)
            TRD[(wn, sn)] = XF.trades_of(au, len(WS[wn]["cal"]))
    P50 = {}
    REV = {}
    for wn in ("主", "早年"):
        D.DATA = WS[wn]["data"]
        st = D.load_stock("0050", "twse", WS[wn]["cal"])
        P50[wn] = (st.df["open"].to_numpy(float), st.df["close"].ffill().to_numpy(float))
        REV[wn] = R34.load_revenue()[:2]

    def hand(wn, sn, s, e, x, st, T, h, mth):
        W = WS[wn]; last = len(W["cal"]) - 1
        c = np.asarray(W["closes"][s], float); o = np.asarray(W["opens"][s], float)
        bset = sorted(b for b in BAD[wn].get(s, ()) if b > T)
        E = min(T + h, last, (bset[0] - 1) if bset else 10 ** 9)
        Tr = TRD[(wn, sn)]
        bp = float(Tr[(Tr["sid"] == s) & (Tr["e"] == e)]["bp"].iloc[0])
        ma = pd.Series(c).rolling(20, min_periods=1).mean().to_numpy()

        def sell_after(d):
            q = d + 1
            while q <= E:
                if np.isfinite(o[q]) and o[q] > 0:
                    return q
                q += 1
            return None

        def reinv(sday):
            if sday >= E:
                return 1.0
            sig = W["SIG"][XF.STR[sn]["G"]]
            cand = sig[sig["entry_pos"] == sday]["sid"].tolist()
            held = set(Tr[(Tr["e"] <= sday) & (Tr["x"] > sday)]["sid"])
            vals = []
            for cd in cand:
                if cd == s or cd in held:
                    continue
                oc = np.asarray(W["opens"][cd], float); cc = np.asarray(W["closes"][cd], float)
                if not (np.isfinite(oc[sday]) and oc[sday] > 0):
                    continue
                bb = sorted(b for b in BAD[wn].get(cd, ()) if sday < b <= E)
                end = bb[0] - 1 if bb else E
                vals.append(cc[end] / oc[sday])
            if vals:
                return sum(vals) / len(vals) * (1 - X3.COST)
            o50, c50 = P50[wn]
            return c50[E] / o50[sday] * (1 - X3.COST50)

        def value(d):
            if d is None:
                return c[E] / c[T]
            sd = sell_after(d)
            if sd is None:
                return c[E] / c[T]
            return o[sd] / c[T] * reinv(sd)

        def walk(fn):
            for k in range(T + 1, E):
                if fn(k):
                    return k
            return None

        if mth == "imm":
            return value(T)
        if mth in ("trail10", "trail20"):
            p_ = 0.10 if mth == "trail10" else 0.20
            return value(walk(lambda k: c[k] <= (1 - p_) * max(c[e:k + 1])))
        if mth == "ma20dn":
            return value(walk(lambda k: c[k] < ma[k]))
        if mth == "half":
            return 0.5 * value(T) + 0.5 * value(walk(lambda k: c[k] < ma[k]))
        if mth == "box_lo":
            lo = min(c[e:T + 1]); return value(walk(lambda k: c[k] < lo))
        if mth == "darvas":
            lo, up = min(c[e:T + 1]), max(c[e:T + 1]); state = {"b": False}

            def f(k):
                if state["b"]:
                    return c[k] < up
                if c[k] < lo:
                    return True
                if c[k] > up:
                    state["b"] = True
                return False
            return value(walk(f))
        if mth == "rebound":
            return value(walk(lambda k: c[k] / bp - 1 >= -0.05 or c[k] >= ma[k]))
        if mth == "revneg":
            tt, _ = X3.rev_turns(s, REV[wn][0], REV[wn][1], X3.avail_map(list(REV[wn][0].index), W["cal"]))
            w = [t for t in tt if T + 1 <= t <= E - 1]
            return value(min(w) if w else None)
        if mth == "orig":
            if x <= E - 1:
                return c[x] / c[T] * reinv(x + 1)
            return c[E] / c[T]
        raise ValueError(mth)

    # ── C1
    rng = np.random.default_rng(20261021)
    pool = DD[(DD["終點h"] == 120) & (DD["出法"] != "imm")]
    smp = pool.iloc[rng.choice(len(pool), 20, replace=False)]
    errs = []
    for _, r in smp.iterrows():
        args = (r["世界"], r["策略"], r["sid"], int(r["e"]), int(r["x"]), r["狀態"], int(r["T"]), 120)
        v = hand(*args, r["出法"]); v1 = hand(*args, "imm")
        errs.append(max(abs(v - r["V"]), abs(v1 - r["V_立即換"]), abs((v - v1) - r["d"])))
        log(f"  {r['世界']}·{r['策略']} {r['sid']} {r['狀態']} T={r['事件日']} {r['出法']}：V {v:.6f}／檔 {r['V']:.6f}｜① {v1:.6f}／{r['V_立即換']:.6f}")
    chk("C1 抽 20 筆手算（另寫逐根迴圈）", max(errs) < 1e-9, f"最大誤差 {max(errs):.2e}")
    # ── C2
    chk("C2 引擎 r0 交易、事件、候選數與頻率表逐列相同", J["對照重建"]["events_r0 逐列相同"] and J["對照重建"]["trades_r0 相同"], json.dumps(J["對照重建"], ensure_ascii=False))
    # ── C3
    s_ = DD[DD["賣"] & DD["出法"].isin(["trail10", "trail20", "ma20dn", "box_lo", "darvas", "rebound", "revneg"])]
    v1 = int(((s_["判斷日"] < s_["T"] + 1) | (s_["判斷日"] > s_["E"] - 1) | (s_["賣日"] <= s_["判斷日"]) | (s_["賣日"] > s_["E"])).sum())
    im = DD[DD["賣"] & (DD["出法"] == "imm")]
    v2 = int(((im["賣日"] <= im["T"]) | (im["賣日"] > im["E"])).sum())
    rv = DD[DD["賣"] & (DD["出法"] == "revneg")]
    av = {wn: set(X3.avail_map(list(REV[wn][0].index), WS[wn]["cal"]).values()) for wn in ("主", "早年")}
    v3 = int(sum(1 for wn, d in zip(rv["世界"], rv["判斷日"]) if int(d) not in av[wn]))
    chk("C3 判斷日 ∈ [T＋1, E−1]、賣日 ∈ (判斷日, E]；立即換賣日 ＞ T；營收轉負判斷日 ＝ 可用日", v1 == 0 and v2 == 0 and v3 == 0, f"違反 {v1}／{v2}／{v3}")
    # ── C4
    mx = 0.0
    for _, v in VER.iterrows():
        cell = [c for c in X3.CELLS if c[1] == v["格"]][0]
        rs = []
        for sg in ("探索", "確認"):
            sub = DD[(DD["狀態"] == cell[2]) & (DD["出法"] == cell[3]) & (DD["終點h"] == 120) & (DD["段"] == sg)]
            cs = R.cl_stats(sub["d"].to_numpy(float), sub["事件月"].to_numpy())
            lo, hi = cs["mean"] - X3.Z7 * cs["se"], cs["mean"] + X3.Z7 * cs["se"]
            ne = min(len(sub), cs["months"])
            r_ = "依構造不可判定" if ne < 30 else ("分不出" if lo <= 0 <= hi else ("好" if cs["mean"] > 0 else "差"))
            rs.append(r_)
            mx = max(mx, abs(cs["mean"] - v[f"{sg}_d"]), abs(lo - v[f"{sg}_lo"]), abs(len(sub) - v[f"{sg}_n"]))
            if r_ != v[sg]:
                mx = 9.0
        whole = ("成立（比立即換" + rs[0] + "）") if (rs[0] == rs[1] and rs[0] in ("好", "差")) else "分不出"
        if whole != v["整格"]:
            mx = 9.0
    chk("C4 7 格兩段 d、CI、結果、整格由逐事件檔重算", mx < 1e-9, f"最大差 {mx:.2e}")
    imm = DD[(DD["出法"] == "imm") & (DD["終點h"] == 120) & DD["賣"]]
    z = {}
    for sg in ("探索", "確認", "早年"):
        u = imm[(imm["段"] == sg) & imm["狀態"].isin(["S+", "S0_40", "S−"])]
        z[sg] = float((u["去向"] == "0050").mean())
    d50 = max(abs(z[sg] - J["對照組改放0050比例(T+120)"][f"{sg}_三狀態合計"]) for sg in z)
    chk("C4 對照組改放 0050 比例重算", d50 < 1e-12, json.dumps(z, ensure_ascii=False))
    # ── C5
    out = subprocess.run([sys.executable, "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True)
    chk("C5 策略鎖相符", out.returncode == 0 and "相符" in out.stdout, out.stdout.strip().splitlines()[-1] if out.stdout.strip() else out.stderr[-200:])
    allok = all(OK.values())
    log(f"[結論] 全部通過 {allok}")
    json.dump({"全部通過": allok, "項": OK}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
