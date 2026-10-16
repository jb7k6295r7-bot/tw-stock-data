# -*- coding: utf-8 -*-
"""USREG-C11（＝ USREG-B11 股債金搭配 seq1，sha c16dc89cba394b41；seq329 已判合格）——前瞻紙上紀錄（裁定 seq353 §三.7；⛔ 不計 N）。
回測線計算子代理建，2026-10-16 23:55（台北）。規則逐字照登錄判定格與 researchUSC_late.py 補讀法 L1、L2、L7（⛔ 不改規則、不挑格）：

  50% SSO＋30% IEF＋20% GLD；起點 2026-10-30 收盤（權益 1.0）→ 2026-11-02 開盤照目標權重建倉（付一次成本）；
  每年第一個交易日開盤再平衡回目標（2027-01-04 起；起點當天不算再平衡日，A1 reb_mask）；⛔ 不做偏離 ±5 點（那是描述格）；
  成交 ＝ researchUSA1_data.engine（t 開盤成交、換手 ½Σ|目標−現有|、成本 ＝ 換手 × 0.05%、一檔沒開盤 ⇒ 整筆延後）；
  現金 ＝ DTB3（前值補；t 日報酬 ＝ DTB3_{t−1}÷100÷252；本格權重和 1 ⇒ 只有成本後殘值）；還原價 ＝ 原始 × adjclose ÷ close。
  基準 ＝ ^SP500TR 收盤（adjclose），2026-10-30 收盤 ＝ 1.0。

    cd ~/tw-p17 && PYTHONPATH=$HOME/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.forward_us_c11                  # 補到資料裡最後一個「已結束」的月底
    ... -m backtest.forward_us_c11 --month 2026-11-30      # 資料最後一日就是月底時（當晚），指定它當月底
    ... -m backtest.forward_us_c11 --selftest              # 閘：同一套函式重算 C11 判定窗（b33bde6 快照）＝ researchUSC_late 判定格

資料：預設讀 ~/us-stock-data（私有庫本機 clone，⛔ 只讀、本檔不 pull）；紀錄每列寫 commit。
紀錄（backtest/forward/us_c11/，只追加、已寫入的列不重算）：monthly.csv（期、月底、實際權重、權益、基準、月報酬）、state.json、runlog.md。
⛔ 私有：逐日權益與價格只寫 ~/us_work/forward_us/c11_daily.csv（repo 外）；repo 只放月底彙總（權益指數、權重、報酬）。
判讀：C11 已合格（seq329）；前瞻只記、不另判、不計 N；與 C3s forward 合算的描述照裁定 seq353 §三.6（之後另做）。
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import subprocess
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
from backtest import researchUSA1_data as A      # noqa: E402  engine／reb_mask（只 import）
from backtest import researchUSC_late as L       # noqa: E402  engine_w（實際權重；閘 ＝ A.engine）

ASSETS = ("SSO", "IEF", "GLD")
WTS = np.array([0.5, 0.3, 0.2])
BASE = "2026-10-30"            # 起點收盤（權益 1.0）
START = "2026-11-02"           # 建倉開盤
COST = 0.0005
ROOT = os.path.expanduser("~/us-stock-data")
FWD = os.path.expanduser("~/tw-p17/backtest/forward/us_c11")
PRIV = os.path.expanduser("~/us_work/forward_us")
COLS = ["期", "月底", "SSO權重", "IEF權重", "GLD權重", "現金權重", "權益（10/30收盤=1）", "^SP500TR（10/30收盤=1）",
        "策略月報酬", "^SP500TR月報酬", "本月再平衡日", "資料commit", "記錄時間（台北）", "備註"]
TOL = 1e-9


def now_tpe():
    return pd.Timestamp.now(tz="Asia/Taipei").strftime("%Y-%m-%d %H:%M")


def commit_of(root):
    p = os.path.join(root, ".commit")
    if os.path.exists(p):
        return io.open(p, encoding="utf-8").read().strip()
    return subprocess.run(["git", "-C", root, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()


# ═════════════ 讀檔（＝ researchUSC_late.load_market 同式，只取需要的；root、end 可換）═════════════
def _yahoo(root, name):
    d = pd.read_csv(os.path.join(root, "data", "macro", f"yahoo_{name}.csv"), dtype={"date": str})
    d = d.drop_duplicates("date").set_index("date").sort_index()
    for c in ("open", "high", "low", "close", "volume", "adjclose"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    return d


def _on(s, cal):
    return np.array(s.reindex(cal).to_numpy(float), dtype=float, copy=True)


def load_mkt(root=ROOT, end=None, assets=ASSETS):
    d = pd.read_csv(os.path.join(root, "data", "macro", "yahoo_GSPC.csv"), usecols=["date"], dtype=str)["date"]
    cal = np.array(sorted(x for x in set(d) if end is None or x <= end))
    n = len(cal)
    M = {"cal": cal, "pos": {x: i for i, x in enumerate(cal)}, "O": {}, "C": {}, "commit": commit_of(root), "root": root}
    for k in assets:
        y = _yahoo(root, k)
        kf = y["adjclose"] / y["close"]
        o = _on(y["open"] * kf, cal); c = _on(y["close"] * kf, cal)
        bad = ~(np.isfinite(o) & np.isfinite(c) & (o > 0) & (c > 0))
        o[bad] = np.nan; c[bad] = np.nan
        M["O"][k], M["C"][k] = o, c
    tr = _yahoo(root, "SP500TR")
    M["C"]["TR"] = _on(tr["adjclose"], cal)
    r = pd.read_csv(os.path.join(root, "data", "macro", "fred_DTB3.csv"), dtype=str, keep_default_na=False)
    v = pd.Series(pd.to_numeric(r["value"].replace({"": None, ".": None}), errors="coerce").to_numpy(float), index=r["date"].to_numpy(str))
    if end is not None:
        v = v[v.index <= end]
    lv = v.dropna()
    dt = pd.Series(lv.to_numpy(), index=lv.index).reindex(sorted(set(lv.index) | set(cal))).ffill().reindex(cal).to_numpy(float)
    g = np.zeros(n); g[1:] = dt[:-1] / 100.0 / 252
    M["cash_g"] = g
    return M


def simulate(M, i0, i1):
    """[i0, i1]：i0 開盤建倉。⇒ eq（相對 i0−1 收盤 ＝ 1）、實際權重、再平衡日。A.run（官方權益）＋ L.engine_w（權重；閘同值）。"""
    cal = M["cal"]; n = i1 - i0 + 1
    W = np.tile(WTS, (n, 1))
    R = A.reb_mask(cal, i0, i1, "Y")
    r = A.run(M, ASSETS, W, i0, i1, R=R, cost=COST)
    O = np.stack([M["O"][a][i0:i1 + 1] for a in ASSETS], 1)
    C = np.stack([pd.Series(M["C"][a]).ffill().to_numpy()[i0:i1 + 1] for a in ASSETS], 1)
    eq2, aw, nreb = L.engine_w(O, C, W, R, M["cash_g"][i0:i1 + 1], cost=COST)
    gate = float(np.max(np.abs(eq2 - r["eq"])))
    if gate > 1e-10:
        raise SystemExit(f"engine_w 對 A.engine 差 {gate}")
    reb = [cal[i0 + t] for t in np.flatnonzero(r["exec"]) if t > 0]
    return r["eq"], aw, reb, gate


def month_ends(M, i0, force=None):
    cal = M["cal"]; out = []
    for p in range(i0, len(cal)):
        if p + 1 < len(cal) and cal[p + 1][:7] != cal[p][:7]:
            out.append(p)
    if force is not None:
        p = M["pos"].get(force)
        if p is None:
            raise SystemExit(f"{force} 不在資料日曆")
        if p != len(cal) - 1 and p not in out:
            raise SystemExit(f"{force} 不是月底")
        if p not in out:
            out.append(p)
    return out


def read_rows(fp):
    if not os.path.exists(fp):
        return []
    return list(csv.DictReader(open(fp, encoding="utf-8-sig")))


def write_rows(fp, rows):
    with open(fp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS); w.writeheader(); w.writerows(rows)


def update(month=None, root=ROOT, fwd=FWD, priv=PRIV, base=BASE, start=START):
    T0 = time.time(); os.makedirs(fwd, exist_ok=True); os.makedirs(priv, exist_ok=True)
    M = load_mkt(root); cal = M["cal"]; pos = M["pos"]
    fp = os.path.join(fwd, "monthly.csv"); old = read_rows(fp)
    log = []
    if base not in pos or start not in pos or pos[start] != pos[base] + 1:
        msg = f"資料未到起點（資料最後一日 {cal[-1]}；起點 {base} 收盤／{start} 開盤）"
        print(msg); return {"狀態": msg}
    i0 = pos[start]; b = pos[base]
    MEs = [p for p in month_ends(M, i0, month) if p >= i0]
    if not MEs:
        msg = f"尚無已結束的月底（資料最後一日 {cal[-1]}）"; print(msg); return {"狀態": msg}
    i1 = MEs[-1]
    eq, aw, reb, gate = simulate(M, i0, i1)
    B = M["C"]["TR"] / M["C"]["TR"][b]
    rows = [{"期": "0", "月底": base, "SSO權重": "", "IEF權重": "", "GLD權重": "", "現金權重": "", "權益（10/30收盤=1）": "1.0",
             "^SP500TR（10/30收盤=1）": "1.0", "策略月報酬": "", "^SP500TR月報酬": "", "本月再平衡日": "", "資料commit": M["commit"][:10],
             "記錄時間（台北）": now_tpe(), "備註": f"起點：{start} 開盤照目標 50/30/20 建倉（付一次成本 0.05%）"}]
    pe, pb_ = 1.0, 1.0
    for k, p in enumerate(MEs, 1):
        t = p - i0; e = float(eq[t]); bb = float(B[p])
        w = aw[t]; cashw = 1.0 - float(w.sum())
        mon = cal[p][:7]
        rows.append({"期": str(k), "月底": cal[p], "SSO權重": f"{w[0]:.6f}", "IEF權重": f"{w[1]:.6f}", "GLD權重": f"{w[2]:.6f}", "現金權重": f"{cashw:.6f}",
                     "權益（10/30收盤=1）": repr(e), "^SP500TR（10/30收盤=1）": repr(bb), "策略月報酬": f"{e / pe - 1:.6f}", "^SP500TR月報酬": f"{bb / pb_ - 1:.6f}",
                     "本月再平衡日": " ".join(x for x in reb if x[:7] == mon), "資料commit": M["commit"][:10], "記錄時間（台北）": now_tpe(),
                     "備註": ("⚠ 月底由 --month 指定（資料最後一日）" if month and cal[p] == month and p == len(cal) - 1 else "")})
        pe, pb_ = e, bb
    # 只追加：舊列保留；重算值與舊列不同 ⇒ 記 runlog
    have = {r["期"]: r for r in old}
    out = list(old)
    for r in rows:
        if r["期"] in have:
            o = have[r["期"]]
            if r["期"] != "0" and abs(float(o["權益（10/30收盤=1）"]) - float(r["權益（10/30收盤=1）"])) > TOL:
                log.append(f"期 {r['期']} 重算權益 {r['權益（10/30收盤=1）']} ≠ 已寫 {o['權益（10/30收盤=1）']}（保留已寫；資料 {M['commit'][:10]}）")
        else:
            out.append(r)
    write_rows(fp, out)
    pd.DataFrame({"日期": cal[b:i1 + 1], "權益": np.r_[1.0, eq], "^SP500TR": B[b:i1 + 1],
                  **{f"{a}權重": np.r_[np.nan, aw[:, i]] for i, a in enumerate(ASSETS)}}).to_csv(
        os.path.join(priv, "c11_daily.csv"), index=False, float_format="%.12g")
    st = {"件": "USREG-C11 前瞻紙上紀錄（50% SSO＋30% IEF＋20% GLD）", "起點": f"{base} 收盤 1.0／{start} 開盤建倉", "記到月底": cal[i1],
          "期數": len(MEs), "資料最後一日": cal[-1], "資料commit": M["commit"], "閘 engine_w 對 A.engine": gate, "寫入時間": now_tpe()}
    json.dump(st, open(os.path.join(fwd, "state.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(os.path.join(fwd, "runlog.md"), "a", encoding="utf-8") as f:
        f.write(f"- {now_tpe()}｜資料 {M['commit'][:10]}（最後一日 {cal[-1]}）｜記到 {cal[i1]}（{len(MEs)} 期）｜新增 {len(out) - len(old)} 列"
                + ("｜" + "；".join(log) if log else "") + f"｜{time.time() - T0:.0f}s\n")
    print(json.dumps(st, ensure_ascii=False, indent=1))
    return st


def selftest():
    """閘：本檔讀檔＋simulate 在 b33bde6 快照、C11 判定窗（SSO 上市 ＋200 日～2026-09-30）重算 ＝ researchUSC_late 判定格。"""
    snap = os.path.expanduser("~/usdata/b33bde6")
    M = load_mkt(snap, end=L.CAL_END)
    ML = L.load_market()
    g = {"日曆相同": bool(np.array_equal(M["cal"], ML["cal"]))}
    g["價格最大差（SSO/IEF/GLD/TR 開收）"] = float(max(np.nanmax(np.abs(np.nan_to_num(M[x][a]) - np.nan_to_num(ML[x][a]))) for x in ("O", "C") for a in ASSETS))
    g["TR 收盤最大差"] = float(np.nanmax(np.abs(M["C"]["TR"] - ML["C"]["TR"])))
    g["cash_g 最大差"] = float(np.max(np.abs(M["cash_g"] - ML["cash_g"])))
    i0 = M["pos"]["2006-06-21"] + 200; i1 = M["pos"][L.CAL_END]
    eq, aw, reb, gate = simulate(M, i0, i1)
    rJ = A.run(ML, ASSETS, np.tile(WTS, (i1 - i0 + 1, 1)), i0, i1, R=A.reb_mask(ML["cal"], i0, i1, "Y"))
    g["權益 對 researchUSC_late 判定格寫法（A.run on load_market）最大差"] = float(np.max(np.abs(eq - rJ["eq"])))
    c, m = A.perf(eq)
    S = json.load(open(os.path.join(L.OUT, "C11_summary.json"), encoding="utf-8"))
    g["年化 對 C11_summary 判定（6 位小數）差"] = abs(round(c, 6) - S["判定"]["年化"])
    g["回落 對 C11_summary 判定（6 位小數）差"] = abs(round(m, 6) - S["判定"]["回落"])
    g["窗"] = [M["cal"][i0], M["cal"][i1]]; g["C11_summary 窗"] = [S["判定"]["起"], S["判定"]["迄"]]
    g["engine_w 對 A.engine"] = gate
    g["再平衡日數（每年第一個交易日）"] = len(reb)
    ok = (g["日曆相同"] and g["價格最大差（SSO/IEF/GLD/TR 開收）"] == 0 and g["TR 收盤最大差"] == 0 and g["cash_g 最大差"] == 0
          and g["權益 對 researchUSC_late 判定格寫法（A.run on load_market）最大差"] <= 1e-12)
    g["全過"] = bool(ok and g["年化 對 C11_summary 判定（6 位小數）差"] <= 1e-6 and g["回落 對 C11_summary 判定（6 位小數）差"] <= 1e-6
                    and g["窗"] == g["C11_summary 窗"])
    g["算於"] = now_tpe()
    json.dump(g, open(os.path.join(FWD, "selftest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(g, ensure_ascii=False, indent=1, default=str))
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", help="把資料最後一日當月底（YYYY-MM-DD）")
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    os.makedirs(FWD, exist_ok=True)
    if a.selftest:
        selftest()
    else:
        update(a.month, a.root)


if __name__ == "__main__":
    main()
