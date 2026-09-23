"""PREREGP17 §四⑦(b)(c) 兩欄【補算】—— 回測線執行端。

⛔⛔ 本支【不改】已交件的 researchp17.py（sha256 152b93fd5bbe1bbf…）——
    它是 import 進來用的，⛔ 沒有複製它的任何一個函式。
    ⭐ 這是 2026-09-23「四點五」那次（重造市值實作）的教訓：⛔ 不維護拷貝。

⭐ 為什麼要補：登錄 PREREGP17 §四⑦ 的三條新必填欄在 **seq=1 就已經是必填**：
    (a) 區間長度的實際值         ⇒ ✅ 已交件（22 個交易日）
    (b) 區間內的換股筆數         ⇒ ⛔ 交件報告裡【沒有】⇒ 本支補
    (c) 第一個再平衡日當天的
        (持股清單, 買價, w) sha256 ⇒ ⛔ 交件報告裡【沒有】⇒ 本支補
        ⛔ 它與主欄【分母必須分開報】（登錄逐字；P16 那個 72/200 的教訓）

⭐ 順帶回答 seq=2 §四⑬（R_rp 對 R_eq 逐位元）——那一欄交件報告已經量到 0/200，
   本支只把它與 (b)(c) 放在同一張表上，⛔ 不重算、⛔ 不改結論。

⚠ 取得 log 的方式：researchp17._sim 是以 `log=None` 這個【關鍵字】呼叫引擎的
   ⇒ ⭐ 本支在 worker 裡把 `research11.simulate_mtm` 換成一層薄包裝，只把 log 換成 list，
     其餘參數原封不動轉交 ⇒ 走的仍然是 researchp17 自己那條呼叫路徑。
   ⇒ ⛔ 而「log 不影響數值」不是用文件宣稱的，是由 §零 的錨點閘門【實測】的。

⭐ 錨點（⛔ 不是自己比自己）：本支重新合成的 R_eq 逐日權益 sha256，
   必須與【已交件的】resultsp17/per_seed_arm.csv 的 R_eq eq_sha 200/200 逐位元相同。
   ⇒ 它同時證明兩件事：① 本支站在同一條資料與數值路徑上 ② log 沒有擾動數值。
"""

from __future__ import annotations

import hashlib
import os
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

from . import data as D
from . import p4_features as P4F
from . import research11 as R
from . import researchp1 as P1
from . import researchp7 as P7
from . import researchp12 as P12
from . import researchp17 as P17

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "resultsp17")          # ⛔ 唯讀：已交件
OUT = os.path.join(HERE, "resultsp17_bc")       # ⭐ 本支只寫這裡

ARMS7 = ("R_eq", "R_tv", "R_rp", "W_fix", "W_shuf", "W0", "W1")
ARMS5 = ("R_eq", "R_tv", "R_rp", "W_fix", "W_shuf")   # w 會動的五臂（⛔ 不含 W0／W1）


# ── worker：攔 log，算 (b)(c) 的原料 ───────────────────────────────────────
_ORIG = None
_CAP: dict = {}


def _patched(*a, **kw):
    lg = []
    kw = dict(kw)
    kw["log"] = lg
    out = _ORIG(*a, **kw)
    _CAP["log"] = lg
    return out


def _initw(sigs, closes, opens, ncal, w0, w1, marks, d_first):
    global _ORIG
    P17._init(sigs, closes, opens, ncal, w0, w1, marks)
    _CAP["d_first"] = int(d_first)
    if _ORIG is None:
        _ORIG = R.simulate_mtm
        R.simulate_mtm = _patched


def _one_bc(r: int):
    """一顆種子：走 researchp17._one 的原路，順手把 log 攔下來算 (b)(c) 的原料。"""
    row, eqw = P17._one(("BC", r))
    lg = _CAP["log"]
    D_reb = _CAP["d_first"]                       # 第一個再平衡日的【日曆索引】
    w0 = P17._S["w0"]
    closes, opens = P17._S["closes"], P17._S["opens"]

    ins = [x for x in lg if x["reason"] == "in"]

    # ── (b) 區間 ＝ [窗首, 第一個再平衡日 − 1]，日曆索引 [w0, D_reb − 1] ──
    lo, hi = w0, D_reb - 1
    n_in = sum(1 for x in ins if lo <= int(x["t"]) <= hi)
    n_out = sum(1 for x in ins if lo <= int(x["exit_pos"]) <= hi)

    # ── (c) 第一個再平衡日【當天收盤後】的持股 ──
    #   ⭐ 出場語意由引擎決定：research11 的迴圈是 `if ex <= t` 先出場、再進場
    #     ⇒ exit_pos ＝＝ D 的部位在 D 當天【已不在持股裡】⇒ 條件是 entry_t ≤ D < exit_pos
    hold = []
    dev = 0.0
    for x in ins:
        t, xp, sid = int(x["t"]), int(x["exit_pos"]), x["sid"]
        if t <= D_reb < xp:
            ep = float(opens[sid][t])             # ⭐ 逐字照 research11 L613 的兩行
            if not np.isfinite(ep) or ep <= 0:
                ep = float(closes[sid][t])
            # ⚠ 自檢：ep 也可以從 log 的 gross 反推（gross ＝ closes[sid][xp]/ep − 1）
            #   ⇒ 兩條路要一致，否則表示本支對「買價」的理解與引擎不同 ⇒ 要停
            g = float(x["gross"])
            if np.isfinite(g) and (1.0 + g) != 0.0:
                ep2 = float(closes[sid][xp]) / (1.0 + g)
                dev = max(dev, abs(ep2 - ep) / ep)
            hold.append((str(sid), ep))
    hold.sort(key=lambda z: z[0])
    return {"r": r, "eq_sha_raw": row["eq_sha"], "n_in": n_in, "n_out": n_out,
            "n_hold": len(hold), "ep_dev": dev}, hold, eqw


# ── (c) 的指紋 ─────────────────────────────────────────────────────────────
def fp(hold: list[tuple[str, float]], w: float) -> str:
    """(持股清單, 買價, w) 的 sha256。⭐ repr 保證浮點 round-trip。"""
    s = "\n".join("{}\t{!r}".format(sid, ep) for sid, ep in hold) + "\nw={!r}\n".format(float(w))
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--reps", type=int, default=P17.REPS)
    ap.add_argument("--panel", default=os.path.join(HERE, "resultsp4", "panel.csv.gz"))
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    log = lambda x: print(x, flush=True)
    t0 = time.time()

    # ① 設定（⭐ 與 researchp17.main 同一條路；常數全部從 P17 取，⛔ 本支不寫死任何一個）
    cal = D.load_calendar(); ncal = len(cal)
    uni = D.load_universe().set_index("stock_id")["market"]
    panel = P4F.read_panel(a.panel)
    closes, opens = P1.load_prices(set(panel["stock_id"]), cal, uni)
    w0, w1 = P12.win_bounds(cal, P17.WIN)
    marks = P12.month_marks(cal, w0, w1)
    n = w1 - w0 + 1
    sig = P7.build_sig_gate_b(panel, cal, closes, opens, start=P12.START, signal=P12.SIG_OF["S1"])
    got, want = P7.accept_sig_b(sig), P7.WANT_SIG_B
    if got != want:
        raise SystemExit("⛔ 門檻B sig 驗收數對不上 ⇒ 停跑")
    log("[sig] 門檻B ✅ 七個驗收數逐項相同：{:,} 筆／{:,} 檔".format(len(sig), sig["sid"].nunique()))

    bench = pd.Series(D.load_stock("0050", "twse", cal).df["close"].to_numpy()).ffill().to_numpy(float)
    B = bench[w0:w1 + 1]
    rb = P17.rebal_days(cal, w0, w1)
    rebal_mask = np.zeros(n, bool)
    rebal_mask[[int(t) for t in rb]] = True
    rb0 = int(rb[0])
    D_reb = w0 + rb0
    log("[窗] {} [{},{}] {} 日；第一個再平衡日 ＝ {}（窗內第 {} 日）"
        .format(P17.WIN, w0, w1, n, cal[D_reb].date(), rb0))
    log("[§四⑦a] 區間 ＝ [{}, {}] ＝ {} 個交易日（⭐ 已交件值，本支重現）"
        .format(cal[w0].date(), cal[D_reb - 1].date(), rb0))

    # ② 跑（⭐ 走 P17._one 的原路，攔 log）
    with Pool(a.procs, initializer=_initw,
              initargs=(sig, closes, opens, ncal, w0, w1, marks, D_reb)) as pool:
        res = pool.map(_one_bc, list(range(a.reps)))
    log("[跑] {} 顆（{:.0f}s）".format(len(res), time.time() - t0))

    rows = pd.DataFrame([x[0] for x in res])
    holds = {x[0]["r"]: x[1] for x in res}
    eqs = {x[0]["r"]: x[2] for x in res}

    # ③ ⭐⭐ 錨點閘門：重新合成的 R_eq 必須與【已交件的】 per_seed_arm.csv 逐位元相同
    sB = {int(t): P17.sigma_at(B, int(t)) for t in rb}
    mine = {}
    wfirst = {}
    for r in sorted(eqs):
        E = eqs[r]
        wp = P17.w_paths(E, B, rb, n, sB)
        V, _, _ = P17.compose(E, B, wp["R_eq"], rebal_mask)
        mine[r] = hashlib.sha256(V.tobytes()).hexdigest()
        wfirst[r] = {arm: float(wp[arm][rb0]) for arm in ("R_eq", "R_tv", "R_rp", "W_fix", "W0", "W1")}
        # W_shuf 的 w 在第一個再平衡日 ＝ 重排後的第一格；⭐ 用與交件同一個亂數源
        rng = np.random.default_rng(P17.SEED_SHUF + r)
        wsh = P17.shuffled_w(wp["R_eq"], rb, n, rng)
        wfirst[r]["W_shuf"] = float(wsh[rb0])

    ref = pd.read_csv(os.path.join(SRC, "per_seed_arm.csv"))
    ref_eq = ref[(ref["arm"] == "R_eq") & (ref["rep"] == -1)].set_index("r")["eq_sha"].to_dict()
    same = sum(1 for r in mine if mine[r] == ref_eq.get(r))
    if same != len(mine):
        raise SystemExit("⛔⛔ 錨點閘門不過：本支重新合成的 R_eq 與已交件的 per_seed_arm.csv "
                         "逐位元相同 {}/{} ⇒ 停止，⛔ 本支的 (b)(c) 不可引用".format(same, len(mine)))
    log("[錨點] ✅ 重新合成的 R_eq 對【已交件】per_seed_arm.csv【{}/{} 逐位元相同】"
        .format(same, len(mine)))
    log("       ⇒ ⭐ 同時證明：攔 log 沒有擾動數值路徑")

    dev = float(rows["ep_dev"].max())
    log("[自檢] 買價兩條路（opens 直讀 vs 由 log 的 gross 反推）最大相對差 ＝ {:.3e}".format(dev))
    if not (dev < 1e-9):
        raise SystemExit("⛔ 買價兩條路對不上 ⇒ 本支對「買價」的理解與引擎不同 ⇒ 停止")

    # ④ (b)
    rows["n_turn"] = rows["n_in"] + rows["n_out"]
    b_zero = int((rows["n_turn"] == 0).sum())
    log("")
    log("[§四⑦b] 區間內換股筆數：進場 {} ~ {}（中位 {}）／出場 {} ~ {}（中位 {}）"
        .format(int(rows["n_in"].min()), int(rows["n_in"].max()), float(rows["n_in"].median()),
                int(rows["n_out"].min()), int(rows["n_out"].max()), float(rows["n_out"].median())))
    log("         合計換股 {} ~ {}（中位 {}）；⭐ ＝ 0 的種子 {}/{} 顆"
        .format(int(rows["n_turn"].min()), int(rows["n_turn"].max()),
                float(rows["n_turn"].median()), b_zero, len(rows)))

    # ⑤ (c)：⛔ 分母與主欄分開報；⚠ 軸沒指定 ⇒ 兩種讀法都報（〈一百〇八〉）
    c_rows = []
    for r in sorted(holds):
        d = {"r": r, "n_hold": len(holds[r])}
        shas = {arm: fp(holds[r], wfirst[r][arm]) for arm in ARMS7}
        d["same7"] = len(set(shas.values())) == 1
        d["same5"] = len(set(shas[arm] for arm in ARMS5)) == 1
        d["sha_R_eq"] = shas["R_eq"]
        for arm in ARMS7:
            d["sha_" + arm] = shas[arm]
        c_rows.append(d)
    cdf = pd.DataFrame(c_rows)
    n7 = int(cdf["same7"].sum()); n5 = int(cdf["same5"].sum())
    uniq = cdf["sha_R_eq"].nunique()
    log("")
    log("[§四⑦c] 替代欄（持股清單, 買價, w）sha256 @ {}".format(cal[D_reb].date()))
    log("         (c-1) 跨臂一致：七臂 {}/{}　五臂 {}/{}　⛔ 分母與主欄分開".format(n7, len(cdf), n5, len(cdf)))
    log("         (c-2) 跨種子鑑別力：200 顆種子產生 {} 個相異指紋".format(uniq))
    log("         持股檔數 {} ~ {}（中位 {}）"
        .format(int(cdf["n_hold"].min()), int(cdf["n_hold"].max()), float(cdf["n_hold"].median())))

    rows.to_csv(os.path.join(OUT, "col_b.csv"), index=False)
    cdf.to_csv(os.path.join(OUT, "col_c.csv"), index=False)
    log("")
    log("[輸出] {}／col_b.csv、col_c.csv".format(OUT))
    log("[完成] {:.0f}s".format(time.time() - t0))


if __name__ == "__main__":
    main()
