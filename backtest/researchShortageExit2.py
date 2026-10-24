# -*- coding: utf-8 -*-
"""缺貨型確認後怎麼賣・第二輪 seq1【正式跑程式；目前只准 --dry】（台股策略線 登錄 sha 463e9d48aed0aa96；裁定 seq458 §三 發號 N_單筆 ＋3、Bonferroni 3 格
（雙尾 98.33%）、持有 1,000 日 ⇒ 最多暫定；判定口徑「賣掉的錢記 0」，「改抱大盤」只描述）——回測線計算子代理。
⛔ seq366：不准含報酬的試跑或子樣本；本檔在裁定核頻率表之前只准 --dry（價格全換成 1、成本 0 ⇒ R、d 全為 0），確認每一欄流程跑通、無除以 0、無空組錯。
⛔ 正式跑須另帶 --ruling <核准裁定 seq>（防誤跑）。⛔ 不 commit、不改既有檔；researchShortageExit2_freq（頻率表，⛔ 只 import）、researchShortageExit（第一輪：
   seam_open、lastvalid_le）、researchRevTurn_freq（prices 等）、research11（cl_stats）⛔ 只 import。
⛔ 美國 PPI 私有：本檔不讀 PPI（觸發位置全取自頻率表 events.csv.gz），輸出只有判定與彙總。

    乾跑：cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchShortageExit2 --dry [--procs 3]   （輸出 ~/rtfwork/dry_sx2）
    正式：PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchShortageExit2 --ruling seqNNN [--procs 3]   （輸出 backtest/resultsShortageExit2/main）
    （裁定 seq459 §四 核頻率表、開正式跑 ⇒ 本件用 --ruling seq459）
輸出：main.json、cells.csv（判定 3 格）、desc.csv（段×E×賣法：R、d、記 0 與改抱大盤兩口徑）、industry.csv、group12.csv（第二欄）、after.csv（賣後走勢）、
     yearly.csv、ann.csv（每筆年化描述欄，U9）、summary.md、events_R.csv.gz（逐事件，正式跑才有意義）、dry_checks.json（乾跑檢查）、run.log
2026-10-24 改動（同線後一個計算子代理；正式跑前、⛔ 未看任何本件報酬）：加 U9「每筆年化」描述欄（裁定 seq460／seq461、台股策略線 1843 §一 寫死）、ann.csv、
     summary.md、乾跑檢查加年化欄；判定、R、d 的算法一字未動。

═══ 讀法（U 標；頻率表讀法 T0～T6 原樣沿用；以下為正式跑新增；⛔ 在讀任何本件報酬之前寫死於 2026-10-23 18:08（台北，系統時鐘）；★＝執行者定，〔 〕內為另一讀法）═══
 U1 事件與觸發 ＝ 頻率表：先以 researchShortageExit2_freq.main 原樣（同一 --sha、--us-sha）重建到 ~/rtfwork/rebuild_sx2，events.csv.gz、counts.csv、freq_段.csv
    與頻率表輸出夾逐字比，任一不同 ⇒ 中止、⛔ 不算報酬。
 U2 價格（第一輪 M2 原式）：進場價 P0 ＝ e 的還原開盤（主世界開盤乘接縫倍數，researchShortageExit.seam_open）；D1／D2 賣出價 ＝ s 的還原開盤；
    D3 賣出價 ＝ s 的還原收盤（T3：收盤賣）；不賣（D0、或到 E_eff 沒賣出）＝ E_eff 當天或之前最後有效 K 棒的還原收盤（researchShortageExit.lastvalid_le）。
    E_eff 由頻率表 E{E}_eff偏移 取用，並以 BAD／LASTV 重算狀態，與頻率表不同 ⇒ 中止。
 U3 R ＝ 出場價 ÷ P0 − 1 − 0.4425%（賣出一次；各賣法同計 ⇒ d 中相消）；d_k ＝ R(Dk) − R(D0)，同一事件配對。另報滑價（每邊 0.5%）版 d（描述）。
    同根兩出場價取較低（seq373）：每法每筆只有一個賣價 ⇒ 不適用。
 U4 判定（登錄 §四）：缺貨型、E ＝ 1,000、判定 3 格 D1、D2、D3；段 ＝ 探索 2006-04～2014-12｜確認 2015-01～（依 e、E1000 走得完）。
    CI ＝ research11.cl_stats 同式按進場月分群；Bonferroni 3 格 ⇒ z ＝ Φ⁻¹(1 − 0.05/6) ＝ 2.394（雙尾 98.33%）。
    兩段平均 d 皆 ＞ 0 ∧ 確認段 Bonferroni 下界 ＞ 0 ⇒「Dk 比不賣有利（暫定）」；兩段皆 ＜ 0 ∧ 確認段上界 ＜ 0 ⇒「Dk 比不賣差（暫定）」；其他 ⇒「分不出」；
    任一段 n_eff ＜ 24 ⇒「還沒測」。
 U5 並列口徑「賣掉的錢改抱大盤」（描述、必報）：大盤 ＝ tw-stock-data data/history/market_tri.csv（同 --sha；★ 收盤 ffill 到合併日曆）；
    ★ R′ ＝ (1 ＋ R_k) × TRI(E_eff 日) ÷ TRI(賣出日 s) − 1（賣出日收盤才轉進大盤；開盤賣當天開→收不計〔另一讀法：TRI(s−1) 起算〕；大盤買進不另扣成本）；
    沒賣 ⇒ R′ ＝ R。d′ ＝ R′(Dk) − R(D0)。
 U6 描述（不判）：E ＝ 750、1,250；另一讀法 D1′、D2′；早於探索段；平均與中位並報；分產業；分年（進場年）；
    第二欄 ＝ 段內進場月依（月序 mod 12）分 12 組，每組 d 平均 ⇒ 12 組中位、最小、最大、＞0 組數（⚠ 1,000 日持有、同組仍重疊）；
    賣後走勢（每個 E、賣出者）：賣出後到 E_eff 最高還原收盤 ≥ 賣出價 × 1.2 比例（賣太早）、E_eff 收盤 ＜ 賣出價比例（賣對）。
 U7 先驗（登錄 §七，寫死不改）：① D3 記 0 比不賣差、改抱大盤分不出；② D1、D2 跟不賣分不出；③ D1 觸發比 D2 早（頻率表 sync.csv）；④ 3 格有利 0 格。
 U8 乾跑（--dry）：P0、出場價、TRI 全換成 1（只保留「有沒有值」的遮罩）、成本 0 ⇒ R、R′、d、d′ 全為 0；RuntimeWarning 一律當錯；檢查每張表無非預期空值、
    判定句可產出、各組不空；⛔ 不輸出到 repo。
 U9 每筆年化（描述、不判；裁定 seq460／seq461、台股策略線 1843 §一 寫死；本段寫於 2026-10-24 04:37（台北，date），⛔ 在看任何本件年化或報酬數字之前）：
    年化 ＝ (1 ＋ R)^(250 ÷ max(H, 60)) − 1；R 同 U3（含賣出成本）；H ＝ 該筆持有交易日數（合併日曆位置差，進場日 e 算第 1 日）：
      賣出者 H ＝ s − e ＋ 1（D1／D2 開盤賣、D3 收盤賣同式）；不賣（D0、或到 E_eff 沒賣）★ H ＝ xv − e ＋ 1，xv ＝ 實際取收盤那根（E_eff 當天或之前最後有效 K 棒）；
      ★ 1 ＋ R ≤ 0 ⇒ 年化記 −1。比法 ＝ 同一筆「賣法年化 − 抱到評估點（D0）年化」，沒賣 ⇒ 0。
    報（各段 × 各 E × D1～D3、D1′、D2′）：差的中位（主報）、平均、＞0 比例；賣法臂與 D0 臂各自年化中位；持有 ＜ 60 日件數比例（賣法臂，全部事件為分母）。
    結果句一句帶過：「若照每筆年化比：…」（判定 E1000、記 0 口徑；年化只描述）。乾跑 R ＝ 0 ⇒ 年化、差全為 0。
"""
from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import time
import warnings
from statistics import NormalDist

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/tw-p17")); sys.path.insert(0, os.path.expanduser("~/tw-p17/backtest"))
os.chdir(os.path.expanduser("~/tw-p17"))
from backtest import researchShortageExit2_freq as S2       # noqa: E402
from backtest import researchShortageExit as SXM            # noqa: E402  第一輪正式跑：seam_open、lastvalid_le
from backtest import researchRevTurn_freq as RT             # noqa: E402
from backtest import research11 as R                        # noqa: E402

OUT = "backtest/resultsShortageExit2/main"
FREQ = S2.OUT
REB = os.path.join(RT.WORK, "rebuild_sx2")
DRY_OUT = os.path.join(RT.WORK, "dry_sx2")
COST = 0.004425
SLIP = 0.005
CELLS = ["D1", "D2", "D3"]
DESC = ["D1′", "D2′"]
ALLR = CELLS + DESC
NB = 3
ZB = NormalDist().inv_cdf(1 - 0.05 / (2 * NB))
NEFF_MIN = 24
SEGJ = ["探索", "確認"]
SEGA = ["早於探索(不入段)"] + SEGJ
NOTES = ["只看這一筆；判定口徑「賣掉的錢記 0」，「改抱大盤」並列（描述）",
         "報價代理是美國生產者物價（FRED 商品別 PPI），不是亞洲報價、也不是個股產品價；玻璃陶瓷只有玻璃",
         "PPIENG 以外七支 2015-03 前用現行修正後值（有前視）",
         "缺貨型以產業別代理（八業），不是逐檔判定的缺貨",
         "持有 1,000 日、月與月不獨立 ⇒ 月分群 CI 偏窄 ⇒ 結論最多「暫定」",
         "2015～2018 下市 58 家月營收補不回（存活者偏差）；早年上櫃 2007-07 前無價",
         "同根兩出場價取較低（seq373）：每法每筆只有一個賣價 ⇒ 不適用"]
MUST = ["只看這一筆", "美國物價代理（FRED 商品別生產者物價，不是亞洲報價、也不是個股產品價）", "缺貨型以產業別代理（八業）",
        "1,000 日內幾乎每件都遇到報價轉跌，三格比的是賣的時點，不是賣或不賣", "探索段約 95% 用的是修正後物價（有前視）",
        "進場時 D1 已成立 11%／18%（探索／確認）", "玻璃陶瓷只有玻璃"]
HMIN = 60
LOG = RT.LOG
log = RT.log


def ann(R_, H):
    """U9：年化 ＝ (1＋R)^(250 ÷ max(H, 60)) − 1；1＋R ≤ 0 ⇒ −1。"""
    g = 1.0 + float(R_)
    return -1.0 if g <= 0 else g ** (250.0 / max(int(H), HMIN)) - 1.0


def rebuild(sha, us_sha, procs):
    """U1：頻率表原樣重建到 REB，與頻率表輸出逐字比。"""
    if os.path.isdir(REB):
        shutil.rmtree(REB)
    argv = sys.argv
    sys.argv = ["researchShortageExit2_freq", "--procs", str(procs), "--sha", sha, "--us-sha", us_sha, "--out", REB]
    try:
        S2.main()
    finally:
        sys.argv = argv
    res = {}
    for f in ("events.csv.gz", "counts.csv", "freq_段.csv", "source.csv", "sync.csv", "equiv.csv"):
        a = pd.read_csv(os.path.join(REB, f), dtype=str, keep_default_na=False)
        b = pd.read_csv(os.path.join(FREQ, f), dtype=str, keep_default_na=False)
        res[f] = bool(a.shape == b.shape and (a.columns == b.columns).all() and a.equals(b))
    return res


def cl(x, m, z=1.96):
    x = np.asarray(x, float); m = np.asarray(m)
    if not len(x):
        return {"n": 0, "months": 0, "mean": np.nan, "median": np.nan, "se": np.nan, "lo": np.nan, "hi": np.nan, "lo_b": np.nan, "hi_b": np.nan, "win": np.nan}
    s = R.cl_stats(x, m)
    s["lo_b"] = s["mean"] - z * s["se"]; s["hi_b"] = s["mean"] + z * s["se"]
    return s


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--procs", type=int, default=3); ap.add_argument("--dry", action="store_true")
    ap.add_argument("--ruling", default=None, help="正式跑：核准頻率表的裁定 seq（無 ⇒ 拒跑）")
    a = ap.parse_args()
    if not a.dry and not a.ruling:
        raise SystemExit("⛔ 正式跑要等裁定核頻率表：請帶 --ruling seqNNN；現在只准 --dry")
    if a.dry:
        warnings.simplefilter("error", RuntimeWarning)
        np.seterr(all="raise")
    t0 = time.time()
    out = DRY_OUT if a.dry else OUT
    os.makedirs(out, exist_ok=True)
    reg = S2.IMF.reg_check(S2.REG_SHA); log(f"[登錄] {reg}（sha {S2.REG_SHA} 已驗）")
    FJ = json.load(open(os.path.join(FREQ, "freq.json"), encoding="utf-8"))
    sha, us_sha = FJ["origin/main"], FJ["us-stock-data"]
    with np.errstate(all="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        same = rebuild(sha, us_sha, a.procs)
    log(f"[U1 重建] {same}")
    if not all(same.values()):
        raise SystemExit(f"⛔ 頻率表重建不同：{same}")
    _, DN, _ = RT.ensure_data(sha)
    with np.errstate(all="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        PX = RT.prices(sha, DN, a.procs)
        O, nseam = SXM.seam_open(PX)
    CAL, ix, C, BAD, VP, LASTV = PX["CAL"], PX["ix"], PX["C"], PX["BAD"], PX["VP"], PX["LASTV"]
    CEND = len(CAL) - 1
    log(f"[U2] 接縫倍數套到主世界開盤：{nseam} 檔")
    tri = pd.read_csv(io.BytesIO(subprocess.run(["git", "show", f"{sha}:data/history/market_tri.csv"], capture_output=True, check=True).stdout))
    tri["date"] = pd.to_datetime(tri["date"]); tri = tri.set_index("date")["close"].astype(float)
    TRI = tri.reindex(tri.index.union(CAL)).ffill().reindex(CAL).to_numpy(float)
    cost = COST
    if a.dry:                                                   # U8：只留遮罩
        O = np.where(np.isfinite(O), 1.0, np.nan); C = np.where(np.isfinite(C), 1.0, np.nan); TRI = np.where(np.isfinite(TRI), 1.0, np.nan); cost = 0.0
    EV = pd.read_csv(os.path.join(FREQ, "events.csv.gz"), dtype={"sid": str, "期別": str})
    EV = EV[(EV["進場"] == "保留") & (EV["母體"] == "缺貨型")].reset_index(drop=True)
    rows = []
    for rd in EV.to_dict("records"):                    # itertuples 會把含 ′ 的欄名改成位置名
        i = ix[rd["sid"]]; e = int(CAL.searchsorted(pd.Timestamp(rd["e"])))
        P0 = O[i, e]
        if not (np.isfinite(P0) and P0 > 0):
            raise SystemExit(f"⛔ 進場價缺 {rd['sid']} {rd['e']}")
        lastv = int(LASTV[i]); delist = (CEND - lastv) >= 5
        for E in S2.ES:
            if not rd[f"E{E}走得完"]:
                continue
            x = e + E; st = "完整"
            bb = np.flatnonzero(BAD[i, e + 1:x + 1])
            if len(bb):
                x = e + int(bb[0]); st = "壞根截斷"
            if delist and lastv < x:
                x = lastv; st = "下市結算"
            if st != rd[f"E{E}狀態"] or x - e != int(rd[f"E{E}_eff偏移"]):
                raise SystemExit(f"⛔ E_eff 與頻率表不同 {rd['sid']} {rd['e']} E{E}")
            xv = SXM.lastvalid_le(VP, i, x)
            PXE = C[i, xv]
            if not (np.isfinite(PXE) and PXE > 0):
                raise SystemExit(f"⛔ E_eff 收盤缺 {rd['sid']} {rd['e']} E{E}")
            R0 = PXE / P0 - 1 - cost
            R0s = PXE * (1 - SLIP) / (P0 * (1 + SLIP)) - 1 - cost if not a.dry else 0.0
            H0 = xv - e + 1; A0 = ann(R0, H0)
            row = {"sid": rd["sid"], "期別": rd["期別"], "e": rd["e"], "段": rd["段"], "產業": rd["產業"], "進場月": rd["進場月"], "進場年": int(rd["e"][:4]),
                   "E": E, "E狀態": st, "R_D0": R0, "R_D0_滑價": R0s, "H_D0": H0, "年化_D0": A0}
            for c in ALLR:
                oc = rd[f"{c}_E{E}"]
                if oc == "賣出":
                    s = e + int(rd[f"{c}_s偏移"])
                    ps = C[i, s] if c == "D3" else O[i, s]
                    if not (np.isfinite(ps) and ps > 0) or s > x:
                        raise SystemExit(f"⛔ 賣出價缺或晚於 E_eff {rd['sid']} {c}")
                    Rk = ps / P0 - 1 - cost
                    Rks = (ps * (1 - SLIP) / (P0 * (1 + SLIP)) - 1 - cost) if not a.dry else 0.0
                    t_s, t_x = TRI[s], TRI[x]
                    if not (np.isfinite(t_s) and np.isfinite(t_x) and t_s > 0):
                        raise SystemExit(f"⛔ 大盤指數缺 {CAL[s].date()}／{CAL[x].date()}")
                    Ralt = (1 + Rk) * t_x / t_s - 1
                    seg = C[i, s:x + 1]; seg = seg[np.isfinite(seg)]
                    row[f"{c}_賣太早"] = bool(len(seg) and seg.max() >= 1.2 * ps)
                    row[f"{c}_賣對"] = bool(PXE < ps)
                    Hk = s - e + 1; Ak = ann(Rk, Hk)
                else:
                    Rk, Rks, Ralt = R0, R0s, R0
                    Hk, Ak = H0, A0
                row[f"H_{c}"] = Hk; row[f"年化_{c}"] = Ak; row[f"年化差_{c}"] = Ak - A0
                row[f"R_{c}"] = Rk; row[f"d_{c}"] = Rk - R0; row[f"d_{c}_滑價"] = Rks - R0s
                row[f"R改抱大盤_{c}"] = Ralt; row[f"d改抱大盤_{c}"] = Ralt - R0; row[f"{c}_結果"] = oc
            rows.append(row)
    RR = pd.DataFrame(rows)
    log(f"[U3] 事件×E {len(RR)}｜{time.time() - t0:.0f}s")
    # ── 判定 3 格（U4）
    J = RR[RR["E"] == 1000]
    cells = []
    for c in CELLS + DESC:
        st = {}
        for sg in SEGJ:
            d = J[J["段"] == sg]
            st[sg] = cl(d[f"d_{c}"].to_numpy(float), d["進場月"].to_numpy(), ZB)
            st[sg]["n_eff"] = int(d["進場月"].nunique())
            st[sg]["alt"] = cl(d[f"d改抱大盤_{c}"].to_numpy(float), d["進場月"].to_numpy(), ZB)
        ex, cf = st["探索"], st["確認"]
        if min(ex["n_eff"], cf["n_eff"]) < NEFF_MIN:
            v = "還沒測（n_eff ＜ 24）"
        elif ex["mean"] > 0 and cf["mean"] > 0 and cf["lo_b"] > 0:
            v = f"{c} 比不賣有利（暫定）"
        elif ex["mean"] < 0 and cf["mean"] < 0 and cf["hi_b"] < 0:
            v = f"{c} 比不賣差（暫定）"
        else:
            v = f"{c} 跟不賣分不出"
        row = {"賣法": c, "名稱": S2.RNAME[c], "身分": ("判定" if c in CELLS else "描述（另一讀法）"), "判定(記0口徑)": v}
        for sg in SEGJ:
            s_ = st[sg]; al = s_["alt"]
            row.update({f"{sg}_n": s_["n"], f"{sg}_n_eff": s_["n_eff"], f"{sg}_d平均": s_["mean"], f"{sg}_d中位": s_["median"], f"{sg}_d>0比例": s_["win"],
                        f"{sg}_CI95": f"[{s_['lo']:+.4f}, {s_['hi']:+.4f}]", f"{sg}_CI98.33(Bonf3)": f"[{s_['lo_b']:+.4f}, {s_['hi_b']:+.4f}]",
                        f"{sg}_賣出率": float((J[J['段'] == sg][f"{c}_結果"] == "賣出").mean()),
                        f"{sg}_改抱大盤d平均": al["mean"], f"{sg}_改抱大盤d中位": al["median"], f"{sg}_改抱大盤CI98.33": f"[{al['lo_b']:+.4f}, {al['hi_b']:+.4f}]"})
        cells.append(row)
    CE = pd.DataFrame(cells)
    log("[U4 判定] " + "｜".join(f"{r['賣法']}：{r['判定(記0口徑)']}" for r in cells))
    # ── 描述（U6）
    DS = []
    for sg in SEGA:
        for E in S2.ES:
            d = RR[(RR["段"] == sg) & (RR["E"] == E)]
            if not len(d):
                continue
            s_ = cl(d["R_D0"].to_numpy(float), d["進場月"].to_numpy())
            DS.append({"段": sg, "E": E, "賣法": "D0(不賣)的R", "n": s_["n"], "n_eff": s_["months"], "平均": s_["mean"], "中位": s_["median"],
                       "CI95下": s_["lo"], "CI95上": s_["hi"], ">0比例": s_["win"], "滑價版平均": float(d["R_D0_滑價"].mean())})
            for c in ALLR:
                for lab_, col in (("記0", f"d_{c}"), ("改抱大盤", f"d改抱大盤_{c}")):
                    s_ = cl(d[col].to_numpy(float), d["進場月"].to_numpy())
                    DS.append({"段": sg, "E": E, "賣法": f"{c} d（{lab_}）", "n": s_["n"], "n_eff": s_["months"], "平均": s_["mean"], "中位": s_["median"],
                               "CI95下": s_["lo"], "CI95上": s_["hi"], ">0比例": s_["win"],
                               "滑價版平均": (float(d[f"d_{c}_滑價"].mean()) if lab_ == "記0" else np.nan),
                               "賣出率": float((d[f"{c}_結果"] == "賣出").mean()), "R平均": float(d[f"R_{c}"].mean() if lab_ == "記0" else d[f"R改抱大盤_{c}"].mean())})
    DS = pd.DataFrame(DS)
    # 分產業（E1000）
    IN = []
    for sg in SEGA:
        for ind, d in J[J["段"] == sg].groupby("產業"):
            r_ = {"段": sg, "產業": ind, "代理序列": S2.PPI_MAP.get(ind, ""), "n": len(d), "月數": int(d["進場月"].nunique()),
                  "D0的R平均": float(d["R_D0"].mean()), "D0的R中位": float(d["R_D0"].median())}
            for c in ALLR:
                r_[f"{c} d平均"] = float(d[f"d_{c}"].mean()); r_[f"{c} d中位"] = float(d[f"d_{c}"].median())
                r_[f"{c} 改抱大盤d平均"] = float(d[f"d改抱大盤_{c}"].mean())
            IN.append(r_)
    IN = pd.DataFrame(IN)
    # 第二欄（U6）
    G12 = []
    for sg in SEGJ:
        d = J[J["段"] == sg]
        lo = [s[1] for s in S2.SEGS if s[0] == sg][0]
        m0 = RT.mnum(lo[:7])
        g = d.groupby(d["進場月"].map(lambda s: (RT.mnum(s) - m0) % 12))
        for c in ALLR:
            for lab_, col in (("記0", f"d_{c}"), ("改抱大盤", f"d改抱大盤_{c}")):
                v = g[col].mean()
                G12.append({"段": sg, "賣法": c, "口徑": lab_, "組數": int(len(v)), "組d中位": float(v.median()), "組d最小": float(v.min()), "組d最大": float(v.max()),
                            "＞0組數": int((v > 0).sum()), "各組件數": " ".join(str(int(x)) for x in g.size().to_numpy())})
    G12 = pd.DataFrame(G12)
    # 分年、賣後走勢
    YR = J.groupby("進場年")[[f"d_{c}" for c in ALLR] + ["R_D0"]].mean().reset_index()
    YR["件數"] = J.groupby("進場年").size().to_numpy()
    AF = []
    for sg in SEGA:
        for E in S2.ES:
            d = RR[(RR["段"] == sg) & (RR["E"] == E)]
            for c in ALLR:
                s_ = d[d[f"{c}_結果"] == "賣出"]
                AF.append({"段": sg, "E": E, "賣法": c, "賣出": len(s_),
                           "賣太早(之後最高≥賣價×1.2)": (float(s_[f"{c}_賣太早"].astype(bool).mean()) if len(s_) else np.nan),
                           "賣對(E收盤＜賣價)": (float(s_[f"{c}_賣對"].astype(bool).mean()) if len(s_) else np.nan)})
    AF = pd.DataFrame(AF)
    # 每筆年化（U9，描述）
    AN = []
    for sg in SEGA:
        for E in S2.ES:
            d = RR[(RR["段"] == sg) & (RR["E"] == E)]
            if not len(d):
                continue
            for c in ALLR:
                x_ = d[f"年化差_{c}"].to_numpy(float); sold = d[f"{c}_結果"] == "賣出"
                AN.append({"段": sg, "E": E, "賣法": c, "身分": ("判定格的描述欄" if (c in CELLS and E == 1000) else "描述"), "n": len(d), "月數": int(d["進場月"].nunique()),
                           "賣出": int(sold.sum()), "年化差中位(賣法−D0)": float(np.median(x_)), "年化差平均": float(x_.mean()), "年化差>0比例": float((x_ > 0).mean()),
                           "賣出者年化差中位": (float(np.median(x_[sold.to_numpy()])) if sold.any() else np.nan),
                           "賣法年化中位": float(d[f"年化_{c}"].median()), "D0年化中位": float(d["年化_D0"].median()),
                           "持有<60日比例(賣法臂,÷全部)": float((d[f"H_{c}"] < HMIN).mean()),
                           "持有<60日件數(賣法臂)": int((d[f"H_{c}"] < HMIN).sum()), "D0臂持有<60日件數": int((d["H_D0"] < HMIN).sum()),
                           "賣法臂H中位": float(d[f"H_{c}"].median())})
    AN = pd.DataFrame(AN)
    # 先驗（U7）
    SY = pd.read_csv(os.path.join(FREQ, "sync.csv"), encoding="utf-8-sig")
    cd = {r["賣法"]: r for r in cells}
    p3 = SY[SY["項"] == "D1、D2"].set_index("段")["任一判到中D1較早(沒判到當∞)"].to_dict()
    PRI = [{"先驗": "① D3 記 0 比不賣差（約七成）；改抱大盤分不出（約五成五）", "實際": cd["D3"]["判定(記0口徑)"] + f"；改抱大盤確認段 CI98.33 {cd['D3']['確認_改抱大盤CI98.33']}"},
           {"先驗": "② D1、D2 跟不賣分不出（約六成）", "實際": "；".join(cd[c]["判定(記0口徑)"] for c in ("D1", "D2"))},
           {"先驗": "③ D1 觸發比 D2 早（約六成）", "實際": f"任一判到中 D1 較早：{p3}（頻率表 sync.csv）"},
           {"先驗": "④ 3 格「比不賣有利」0 格（約六成五）", "實際": f"有利 {sum(1 for c in CELLS if '有利' in cd[c]['判定(記0口徑)'])} 格"}]
    sent = [f"{r['名稱']}（{r['賣法']}）：{r['判定(記0口徑)']}；確認段 d 平均 {r['確認_d平均'] * 100:+.2f} 點 Bonf3 CI {r['確認_CI98.33(Bonf3)']}，探索段 {r['探索_d平均'] * 100:+.2f} 點；"
            f"改抱大盤（描述）確認段 {r['確認_改抱大盤d平均'] * 100:+.2f} 點" for r in cells if r["賣法"] in CELLS] + NOTES
    # 改抱大盤一句、年化一句（U5、U9；描述）
    alt1 = "若賣掉的錢改抱大盤報酬指數到 E1000（描述）：" + "；".join(
        f"{r['賣法']} 確認段 d′ 平均 {r['確認_改抱大盤d平均'] * 100:+.2f} 點（Bonf3 CI {r['確認_改抱大盤CI98.33']}）、探索段 {r['探索_改抱大盤d平均'] * 100:+.2f} 點"
        for r in cells if r["賣法"] in CELLS)
    A1 = AN[AN["E"] == 1000].set_index(["段", "賣法"])
    ann1 = "若照每筆年化比（賣法年化 − 抱到 E1000 年化，描述、不判）：" + "；".join(
        f"{c} 中位 確認 {A1.loc[('確認', c), '年化差中位(賣法−D0)'] * 100:+.2f} 點／探索 {A1.loc[('探索', c), '年化差中位(賣法−D0)'] * 100:+.2f} 點"
        f"（平均 {A1.loc[('確認', c), '年化差平均'] * 100:+.2f}／{A1.loc[('探索', c), '年化差平均'] * 100:+.2f} 點；持有＜60 日 "
        f"{A1.loc[('確認', c), '持有<60日比例(賣法臂,÷全部)'] * 100:.1f}%／{A1.loc[('探索', c), '持有<60日比例(賣法臂,÷全部)'] * 100:.1f}%）" for c in CELLS)
    sent = sent + [alt1, ann1] + ["必附：" + "；".join(MUST)]
    # summary.md
    f2 = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:+.2f}"   # noqa: E731
    p1 = lambda v: "—" if v is None or not np.isfinite(v) else f"{v * 100:.1f}%"   # noqa: E731
    md = [f"# 缺貨型確認後怎麼賣・第二輪 seq1 {'【乾跑：價格全換 1、⛔ 非報酬】' if a.dry else '正式跑'}（單筆層）", "",
          f"- 登錄：台股策略線 seq1 sha {S2.REG_SHA}｜裁定 seq458 §三（N_單筆 ＋3、Bonferroni 3 格 雙尾 98.33%）" + (f"、{a.ruling} §四 核頻率表開跑" if a.ruling else ""),
          f"- 資料：tw-stock-data {sha}｜美國 PPI us-stock-data {us_sha}（⛔ 本檔不含任何 PPI 值，只有判定與彙總）｜頻率表重建逐字相同 {all(same.values())}",
          "- 判定口徑「賣掉的錢記 0」；E ＝ 進場後第 1,000 個交易日收盤；CI 按進場月分群", "",
          "## 判定（E1000、記 0）", ""]
    md += [f"- **{r['名稱']}（{r['賣法']}）：{r['判定(記0口徑)']}**" for r in cells if r["賣法"] in CELLS]
    md += ["", "| 賣法 | 身分 | 段 | n | n_eff | 賣出率 | d 平均（點） | d 中位（點） | d>0 | CI95 | CI98.33（Bonf3） |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in cells:
        for sg in SEGJ:
            md.append(f"| {r['賣法']} | {r['身分']} | {sg} | {r[f'{sg}_n']} | {r[f'{sg}_n_eff']} | {p1(r[f'{sg}_賣出率'])} | {f2(r[f'{sg}_d平均'])} | {f2(r[f'{sg}_d中位'])} | "
                      f"{p1(r[f'{sg}_d>0比例'])} | {r[f'{sg}_CI95']} | {r[f'{sg}_CI98.33(Bonf3)']} |")
    md += ["", "## 賣後走勢（E1000、賣出者）", "", "| 段 | 賣法 | 賣出 | 賣後到 E 最高又漲 ≥20%（賣太早） | 到 E 收盤低於賣價（賣對） |", "|---|---|---|---|---|"]
    for _, r in AF[(AF["E"] == 1000) & AF["段"].isin(SEGJ)].iterrows():
        md.append(f"| {r['段']} | {r['賣法']} | {r['賣出']} | {p1(r['賣太早(之後最高≥賣價×1.2)'])} | {p1(r['賣對(E收盤＜賣價)'])} |")
    md += ["", "## 分產業（E1000，d 平均，點；描述）", "", "| 段 | 產業 | n | 月數 | D0 R 平均 | D1 | D2 | D3 |", "|---|---|---|---|---|---|---|---|"]
    for _, r in IN[IN["段"].isin(SEGJ)].iterrows():
        md.append(f"| {r['段']} | {r['產業']} | {r['n']} | {r['月數']} | {f2(r['D0的R平均'])} | {f2(r['D1 d平均'])} | {f2(r['D2 d平均'])} | {f2(r['D3 d平均'])} |")
    md += ["", "## 改抱大盤（描述，一句）", "", alt1, "", "## 每筆年化（描述，一句；裁定 seq460／seq461）", "", ann1, "",
           "| 段 | E | 賣法 | n | 年化差中位 | 年化差平均 | 年化差>0 | 持有<60日（賣法臂） |", "|---|---|---|---|---|---|---|---|"]
    for _, r in AN[AN["段"].isin(SEGJ)].iterrows():
        md.append(f"| {r['段']} | {r['E']} | {r['賣法']} | {r['n']} | {f2(r['年化差中位(賣法−D0)'])} | {f2(r['年化差平均'])} | {p1(r['年化差>0比例'])} | {p1(r['持有<60日比例(賣法臂,÷全部)'])} |")
    md += ["", "## 其他描述", "", "- D1′、D2′ 為另一讀法，只描述（見 cells.csv、desc.csv）；E750、E1250、早於探索段只描述（desc.csv）。",
           "", "## 先驗（登錄 §七，寫死）", ""] + [f"- {p['先驗']} ⇒ {p['實際']}" for p in PRI]
    md += ["", "## 必附", ""] + [f"- {s}" for s in MUST + NOTES]
    # ── 乾跑檢查（U8）
    DC = {}
    if a.dry:
        num = RR.select_dtypes("number")
        rc = [c for c in num.columns if c.startswith(("R_", "d_", "R改抱", "d改抱"))]
        DC["R與d全為0"] = bool(np.all(num[rc].to_numpy() == 0))
        DC["R與d無空值"] = bool(not num[rc].isna().any().any())
        DC["判定3格可產出"] = [r["判定(記0口徑)"] for r in cells]
        DC["cells空值欄"] = [c for c in CE.columns if CE[c].isna().any()]
        DC["desc空值欄"] = {c: int(DS[c].isna().sum()) for c in DS.columns if DS[c].isna().any()}
        DC["industry空值欄"] = [c for c in IN.columns if IN[c].isna().any()]
        DC["group12組數"] = G12.groupby("段")["組數"].min().to_dict()
        DC["after空組(賣出=0)"] = AF[AF["賣出"] == 0][["段", "E", "賣法"]].to_dict("records")
        DC["各段E事件數"] = RR.groupby(["段", "E"]).size().rename("n").reset_index().to_dict("records")
        DC["事件×E"] = len(RR)
        ac = [c for c in num.columns if c.startswith(("年化_", "年化差_"))]
        hc = [c for c in num.columns if c.startswith("H_")]
        DC["年化欄全為0"] = bool(len(ac) and np.all(num[ac].to_numpy() == 0))
        DC["年化欄無空值"] = bool(not num[ac].isna().any().any())
        DC["H欄≥1且無空值"] = bool(not num[hc].isna().any().any() and (num[hc].to_numpy() >= 1).all())
        DC["ann空值欄"] = {c: int(AN[c].isna().sum()) for c in AN.columns if AN[c].isna().any()}
        DC["ann列數"] = len(AN)
        DC["summary行數"] = len(md)
        log(f"[U8 乾跑檢查] {DC}")
    RR.to_csv(os.path.join(out, "events_R.csv.gz"), index=False, encoding="utf-8-sig", compression="gzip")
    CE.to_csv(os.path.join(out, "cells.csv"), index=False, encoding="utf-8-sig")
    DS.to_csv(os.path.join(out, "desc.csv"), index=False, encoding="utf-8-sig")
    IN.to_csv(os.path.join(out, "industry.csv"), index=False, encoding="utf-8-sig")
    G12.to_csv(os.path.join(out, "group12.csv"), index=False, encoding="utf-8-sig")
    YR.to_csv(os.path.join(out, "yearly.csv"), index=False, encoding="utf-8-sig")
    AF.to_csv(os.path.join(out, "after.csv"), index=False, encoding="utf-8-sig")
    AN.to_csv(os.path.join(out, "ann.csv"), index=False, encoding="utf-8-sig")
    open(os.path.join(out, "summary.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    MJ = {"性質": ("乾跑（價格全換 1、成本 0；⛔ 非報酬）" if a.dry else "缺貨型出場第二輪 seq1 正式跑（單筆層）"), "登錄": f"台股策略線 seq1 sha {S2.REG_SHA}",
          "裁定": "seq458 §三（N_單筆 ＋3、Bonferroni 3 格 98.33%）" + (f"；核頻率表 {a.ruling}" if a.ruling else ""), "origin/main": sha, "us-stock-data": us_sha,
          "頻率表重建": same, "接縫開盤倍數檔數": nseam, "z_Bonf3": ZB, "判定": cells, "先驗": PRI, "結果句": sent, "乾跑檢查": DC,
          "每筆年化(描述)": AN[AN["E"] == 1000].to_dict("records"), "必附": MUST,
          "讀法": __doc__.split("═══ 讀法")[1], "秒": round(time.time() - t0)}
    json.dump(MJ, open(os.path.join(out, "main.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=RT.jdef)
    if a.dry:
        json.dump(DC, open(os.path.join(out, "dry_checks.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=RT.jdef)
    open(os.path.join(out, "run.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    log(f"[完成] {out}｜{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
