# -*- coding: utf-8 -*-
"""PREREGC17 重報：只算 BTC、幣本位全倉（裁定 seq333 讀法定 max；seq334 改照使用者實際做法重報，描述、N 不變）。

⭐ 讀法寫死：2026-10-11 01:03（台北；01:02:35 WSL 取時後寫，首跑 01:04:43）——在算出任何幣本位數字之前寫在這裡。【執行者補】一律標在此。
   已看過：C17 v1／v2 與 max 讀法對帳診斷結果（U 本位、每 1 單位名目口徑）；本件的幣本位錢包路徑、強平、逐年都還沒算。

依據：seq334 使用者逐字「我現在只算btc喔！然後開幣本位所以我在找穩定可以提升報酬的方法而已」；部位照加密 1009-1540 信：
   錢包 0.0715 BTC；現有 3 張；計畫上限 24 張（每張 100 USD）；幣安顯示 3 張強平 3,591、加密線估 24 張約 22,000（MMR 0.4%、未計資金費）。

⭐ 落地讀法
 B1 訊號與進出場：照 C17 v1 主臂、出場讀法 max（seq333）：收盤 ＜ max(訊號日最低, 前 10 日最低) ⇒ 次日開盤平；t＋1 開盤進場；持倉中不加碼不重設；
    價格一律用 Binance 現貨 BTCUSDT 日 K（登錄 §一；USDT≈USD），⚠ 幣本位永續成交價與現貨的價差不計【執行者補】。
 B2 部位：每次訊號開 n 張 BTCUSD 幣本位永續多單，n ∈ {3、24}，名目 N＝n×100 USD（固定張數，不隨錢包增減）【執行者補】；
    保證金＝合約錢包 W（BTC），起始 W0＝0.0715 BTC，兩窗各自從 W0 起算；全倉＝整個錢包都撐這一筆。
    ⚠ 使用者現有的 3 張常駐多單不併入（C17 是另開的訊號單）；若同錢包同時抱著常駐單，強平會更近——列為限制【執行者補】。
 B3 成本：每邊 0.1% × 名目（登錄 §二），以幣付＝0.001 × N ÷ 成交價。
 B4 資金費：data/meta/crypto_cm_funding_rest/BTCUSD_PERP.csv（2020-08-10 16:00 UTC 起）；歸日同 C17 K5（整點 h 屬 (h−1 秒) 的 UTC 日；D 08:00、16:00、D＋1 00:00 屬 D）；
    多方每天付 Σrate × N ÷ 參考價（進場日＝進場價，其他日＝前一日收盤；日 K 沒有逐筆標記價）【執行者補】；沒資料的日子以年化 10%（÷365.25）代入並報天數。
 B5 強平（幣安幣本位全倉，現行分級表第 1 級：部位價值 ≤ 5 BTC ⇒ MMR 0.4%、速算額 0；私有 cm_specs/cm_margin_tiers.csv，2026-05-11 生效；24 張在 BTC ≥ 480 USD 時都在第 1 級）：
    權益（BTC）＝W ＋ N×(1/Pe − 1/P)；權益 ≤ 0.004 × N／P ⇒ 強平 ⇒ Lp＝N×1.004 ÷ (W ＋ N/Pe)。
    每持有日：先扣當日資金費，再算 Lp；日低 ≤ Lp ⇒ 強平（錢包歸 0，之後都 0）；強平清算費 1.5% 不改觸發時點。主＝現貨日低；敏感度＝幣本位標記價日低（2020-08-11 起）。
    每筆報「最低點距強平」＝min(日低／Lp − 1)、有無觸及。
 B6 平倉：x 日開盤實現 W ＋＝ N×(1/Pe − 1/open_x) − 0.001×N/open_x；窗尾仍持有 ⇒ 以收盤估值、不扣平倉費。
 B7 衡量（seq334）：「囤幣＋訊號時開幣本位多」＝錢包權益（BTC）＝W＋未實現；「只囤幣」＝W0 不動。
    ① BTC 計：窗末權益 − W0（BTC 與 ÷W0 的 %）；② USD 計：權益×收盤，年化（365.25）、MDD（日收盤）、年化÷|MDD|，與只囤幣（W0×收盤）並列，並標合格／另列／不合格（同 C17 K10 定義）；
    ③ 逐年：每個 UTC 曆年（窗內段）年末權益 − 年初權益（BTC），＞0 加分、＜0 扣分、0 沒動。
 B8 旁證（⛔ 不進結果句）：8 幣合併（max 讀法 v2）＋0.165%／天、p 0.005——只照抄 diag_lowmax_v2.json。
 B9 --check：另一支寫法——強平用「權益 ≤ 維持保證金」不等式逐日直接判（不解 Lp）、每筆損益用收盤價閉式累加，重算窗末錢包、強平日、觸及筆數、逐年增減，逐位比。
 B10 【執行者補】敏感度「按今日比例」：固定張數在低價年代等於高倍數（24 張在 BTC 4,000 時＝錢包美元值的 8 倍、今日約 0.41 倍）⇒ 另報每筆名目＝k × W0 × 進場價，
     k＝n×100 ÷ (W0 × 2026-10-09 收盤)（3 張 k≈0.051、24 張 k≈0.41），不取整；只描述。
⛔ 不寫買賣建議、不寫「開幾張安全」。
"""
from __future__ import annotations
import os, sys, json
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import researchC17 as R

FROZEN_CM = "2026-10-11 01:03（台北；寫檔當下以 01:02:35 取時後估計，首跑 01:04:43）"
W0 = 0.0715
SIZES = (3, 24)
FACE = 100.0
MMR = 0.004
FEE = 0.001
RULE = ("lowmax", 10)
WINS = (("2018～2023", R.W1), ("2024～2026-10-09", R.W2))


def load():
    s = R.load_binance("BTC", drop30=False)
    R.attach_funding(s, R.fund_src("BTCUSD_CM"))
    mk = pd.read_csv(os.path.join(R.ROOT, "data", "crypto_cm_mark", "BTCUSD_PERP.csv"))
    mk["date"] = pd.to_datetime(mk["open_time"], unit="ms", utc=True).dt.strftime("%Y-%m-%d")
    s["mlow"] = mk.drop_duplicates("date").set_index("date")["low"].astype(float).reindex(s["dates"]).to_numpy()
    return s


def path(s, i0, i1, trades, n, low_kind="spot", ratio=None):
    """回 dict：每日權益（BTC）、每筆強平資訊、強平日。"""
    N = n * FACE
    o, c = s["open"], s["close"]
    low = s["low"] if low_kind == "spot" else np.where(np.isnan(s["mlow"]), s["low"], s["mlow"])
    W = W0
    eq = np.zeros(i1 - i0 + 1)
    by_e = {t["e"]: t for t in trades}
    cur = None; Pe = None; dead = False; liq_day = None; rows = []; rec = None; fund_paid = 0.0; fees = 0.0
    for d in range(i0, i1 + 1):
        if dead:
            eq[d - i0] = 0.0; continue
        if cur is not None and cur["x"] == d:          # 開盤平倉
            W += N * (1 / Pe - 1 / o[d]) - FEE * N / o[d]; fees += FEE * N / o[d]
            rows.append(rec); cur = None
        if d in by_e:                                   # 開盤進場
            cur = by_e[d]; Pe = o[d]; N = n * FACE if ratio is None else ratio * W0 * Pe; W -= FEE * N / Pe; fees += FEE * N / Pe
            rec = {"entry": s["dates"][d], "Pe": float(Pe), "days": cur["last"] - cur["e"] + 1,
                   "exit": s["dates"][cur["x"]] if cur["x"] is not None else "", "min_dist": np.inf, "touched": False, "touch_day": "",
                   "max_float": float(low[cur["e"]:cur["last"] + 1].min() / Pe - 1)}
        if cur is not None and cur["e"] <= d <= cur["last"]:
            pref = Pe if d == cur["e"] else c[d - 1]
            f = s["fund"][d] * N / pref
            W -= f; fund_paid += f
            Lp = N * (1 + MMR) / (W + N / Pe) if (W + N / Pe) > 0 else np.inf
            dist = low[d] / Lp - 1
            rec["min_dist"] = min(rec["min_dist"], float(dist))
            if low[d] <= Lp:
                rec["touched"] = True; rec["touch_day"] = s["dates"][d]
                dead = True; liq_day = s["dates"][d]; W = 0.0; eq[d - i0] = 0.0
                rows.append(rec); cur = None
                continue
            eq[d - i0] = W + N * (1 / Pe - 1 / c[d])
        else:
            eq[d - i0] = W
    if cur is not None and not dead:
        rows.append(rec)
    return {"eq": eq, "rows": rows, "liq_day": liq_day, "W_end": float(eq[-1]), "fund_paid": fund_paid, "fees": fees}


def measure(s, i0, i1, P):
    c = s["close"][i0:i1 + 1]
    prev = s["close"][i0 - 1]
    usd = np.r_[W0 * prev, P["eq"] * c]
    hold = np.r_[W0 * prev, W0 * c]
    T = i1 - i0 + 1

    def st(v):
        if v[-1] <= 0:
            ann = -1.0
        else:
            ann = (v[-1] / v[0]) ** (365.25 / T) - 1
        mdd = float((v / np.maximum.accumulate(v) - 1).min())
        return {"年化": float(ann), "MDD": mdd, "年化÷|MDD|": float(ann / abs(mdd)) if mdd < 0 else None, "期末USD": float(v[-1])}
    a, h = st(usd), st(hold)
    wr = a["年化"] > h["年化"]
    wc = (a["年化÷|MDD|"] is not None and h["年化÷|MDD|"] is not None and a["年化÷|MDD|"] >= h["年化÷|MDD|"])
    lab = "合格" if (wr and wc) else ("另列" if wr else "不合格")
    # 逐年
    dates = s["dates"][i0:i1 + 1]
    yrs = pd.Series(P["eq"], index=pd.Index([d[:4] for d in dates]))
    yr = []
    start = W0
    for y, g in yrs.groupby(level=0, sort=True):
        endv = float(g.iloc[-1])
        dlt = endv - start
        yr.append({"年": y, "年初BTC": start, "年末BTC": endv, "增減BTC": dlt, "增減÷W0": dlt / W0,
                   "判": "加分" if dlt > 1e-12 else ("扣分" if dlt < -1e-12 else "沒動")})
        start = endv
    return {"USD_囤幣加訊號": a, "USD_只囤幣": h, "使用者判準": lab, "逐年": yr}


def run():
    s = load()
    out = {"讀法寫死": FROZEN_CM, "資料commit": R.SHA, "出場讀法": "max（seq333）", "W0_BTC": W0, "MMR": MMR, "每張USD": FACE, "窗": {}}
    for lab, (a, b) in WINS:
        i0, i1 = R.window_idx(s, a, b)
        tr = R.unit_run(s, i0, i1, 2.0, 0.05, RULE, "open")
        trades = tr["trades"]
        w = {"筆數": len(trades), "窗內資金費代入天數": int(s["fmiss"][i0:i1 + 1].sum()),
             "持有日資金費代入天數": int((s["fmiss"] & tr["held"])[i0:i1 + 1].sum()),
             "每天多賺_幣本位資金費(1單位名目)": tr["excess"]}
        rng = np.random.default_rng(R.SEED + 7)
        p, _ = R.perm_test([(R.sub(s, i0, i1), tr["held"][i0:i1 + 1].copy(), tr["wmean"])], tr["excess"], rng)
        w["假訊號p"] = p
        for n in SIZES:
            P = path(s, i0, i1, trades, n)
            Pm = path(s, i0, i1, trades, n, "mark")
            m = measure(s, i0, i1, P)
            w[f"{n}張"] = {"窗末錢包權益BTC": P["W_end"], "對只囤幣增減BTC": P["W_end"] - W0, "增減÷W0": (P["W_end"] - W0) / W0,
                          "累計資金費BTC": P["fund_paid"], "累計手續費BTC": P["fees"], "強平日": P["liq_day"],
                          "觸及強平筆數": int(sum(r["touched"] for r in P["rows"])),
                          "最近距強平": float(min(r["min_dist"] for r in P["rows"])) if P["rows"] else None,
                          "標記價_觸及筆數": int(sum(r["touched"] for r in Pm["rows"])),
                          "標記價_最近距強平": float(min(r["min_dist"] for r in Pm["rows"])) if Pm["rows"] else None,
                          **m, "每筆": P["rows"]}
        for n in SIZES:
            k = n * FACE / (W0 * float(s["close"][-1]))
            for tagr, P in (("", path(s, i0, i1, trades, n)), ("_按今日比例", path(s, i0, i1, trades, n, ratio=k))):
                if tagr == "":
                    continue
                m = measure(s, i0, i1, P)
                md = float(min(r["min_dist"] for r in P["rows"])) if P["rows"] else None
                w[f"{n}張{tagr}"] = {"比例k(名目÷錢包美元值)": k, "窗末錢包權益BTC": P["W_end"], "對只囤幣增減BTC": P["W_end"] - W0, "增減÷W0": (P["W_end"] - W0) / W0,
                                    "強平日": P["liq_day"], "觸及強平筆數": int(sum(r["touched"] for r in P["rows"])), "最近距強平": md,
                                    "最低點還要再跌才強平": (md / (1 + md)) if (md is not None and md > 0) else None, **m}
            w[f"{n}張"]["最低點還要再跌才強平"] = (w[f"{n}張"]["最近距強平"] / (1 + w[f"{n}張"]["最近距強平"])) if (w[f"{n}張"]["最近距強平"] or -1) > 0 else None
        out["窗"][lab] = w
    # 參考：使用者現況兩個強平價（照本模型），對照幣安顯示 3,591、加密線估 22,000
    out["現況強平價_本模型"] = {"3張@84,500": FACE * 3 * (1 + MMR) / (W0 + 300 / 84500),
                            "24張(3@84,500+10@66,000+11@58,625)": FACE * 24 * (1 + MMR) / (W0 + 300 / 84500 + 1000 / 66000 + 1100 / 58625)}
    # 旁證（只照抄）
    D = json.load(open(os.path.join(R.OUT, "diag_lowmax_v2.json"), encoding="utf-8"))
    out["旁證_8幣合併_max_v2"] = {"每天多賺": D["主格"]["8幣合併"]["每天多賺"], "假訊號p": D["對照"]["8幣合併"]["假訊號p"], "註": "⛔ 不進給使用者的結果句"}
    # 資金費起訖
    ev = R.fund_src("BTCUSD_CM")
    out["CM資金費起訖"] = [pd.to_datetime(ev["h"].min(), unit="s", utc=True).strftime("%Y-%m-%d %H:%M UTC"),
                       pd.to_datetime(ev["h"].max(), unit="s", utc=True).strftime("%Y-%m-%d %H:%M UTC")]
    out["CM覆蓋日中筆數≠3"] = [str(d) for d in s["dates"][(s["fcnt"] != 3) & ~s["fmiss"]]]
    return out, s


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--stamp", default=""); ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        import researchC17_btccm_check as CK
        CK.main()
    else:
        J, _ = run()
        J["寫檔時間"] = a.stamp
        with open(os.path.join(R.OUT, "btc_coinm.json"), "w", encoding="utf-8") as f:
            json.dump(R.to_jsonable(J), f, ensure_ascii=False, indent=1)
        print("OK", a.stamp)
