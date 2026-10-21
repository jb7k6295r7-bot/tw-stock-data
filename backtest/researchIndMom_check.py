# -*- coding: utf-8 -*-
"""產業價格動能 seq1 正式跑【對帳】——回測線計算子代理。⛔ 只讀 backtest/resultsIndMom/（freq/ 外）與資料，不寫任何既有檔；
輸出 resultsIndMom/check.json、check.log。本檔另提供 Indep（逐根獨立重算報酬：research11.load_bars＋crashwork 壞根＋exright 差異），
財報品質、現增可轉債兩支對帳 import 重用。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchIndMom_check

C1 策略鎖：python -m backtest.strategy_lock --check（25 支相符）。
C2 頻率表逐列重建：recon_freq.csv 全同；判定格（市值加權 6 月）逐月入選產業 ＝ freq/monthly.csv「市值加權前3」（exright 差異列另計）。
C3 抽筆手算：主 6 筆＋早年 2 筆判定格事件，成員逐檔用 Indep 逐根迴圈重算 R、t 市值加權 ⇒ R產業（容差 1e−9）；主、早年各 1 個月全市場 R 同法重算。
C4 不前視：抽 6 個形成月，把面板 t 之後的價格、市值、閘全部抹掉重排 ⇒ 入選三產業不變；全部事件 進場日 ＞ 形成月底。
C5 彙總重算：IndMom_表.csv 全部列由 events 重算 n、n_eff、X̄、lo、hi（容差 1e−12）；假訊號 x 由 fake_reps.csv 重數。
C6 exright：2464 2026-09-02（資料庫 1021-0009 已知權息同日）在差異表為「幽靈壞根拿掉」，原始收盤 ÷ open_base 在 [0.895, 1.105] 內。
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
from backtest import researchIndMom as IMX                  # noqa: E402
from backtest import researchIndMom_freq as IM              # noqa: E402
from backtest import researchPTH_freq as PF                 # noqa: E402
from backtest import researchAscTri_freq as AT              # noqa: E402
from backtest import research11 as R                        # noqa: E402
import backtest.data as D                                   # noqa: E402

OUT = IMX.OUT
LOG: list = []
OK: dict = {}


def log(s):
    print(s, flush=True); LOG.append(s)


def chk(name, cond, detail=""):
    OK[name] = bool(cond)
    log(f"{'✅' if cond else '❌'} {name} {detail}")


class Indep:
    """逐根獨立重算：research11.load_bars（有效 K 棒、還原開收、next_bad）＋ AT.load_world 的 crashwork／早年壞根 ＋ exright 差異（新增／拿掉）。"""

    def __init__(self, wn):
        self.W = AT.load_world(wn); self.wn = wn
        self.cal = self.W["cal"]; self.n0 = self.W["n0"]
        X = pickle.load(open(os.path.join(IMX.WORK, f"exrx_{wn}_{IMX.EXR_SHA[:12]}.pkl"), "rb"))
        self.add, self.rem = set(), set()
        for d in X["diff"]:
            p = int(self.cal.searchsorted(pd.Timestamp(d["date"])))
            if d["項"] == "幽靈壞根新增":
                self.add.add((d["sid"], p))
            elif d["項"] == "幽靈壞根拿掉":
                self.rem.add((d["sid"], p))
        self.cache = {}

    def bars(self, sid):
        if sid not in self.cache:
            D.DATA = self.W["data"]
            B = R.load_bars(sid, self.W["mk"].get(sid, "twse"), self.cal)
            idx = B["idx"].astype(np.int64); nb = len(idx)
            bad = np.asarray(B["next_bad"][:nb] == np.arange(nb), bool)
            for p_ in self.W["BADPOS"].get(sid, ()):
                k = int(np.searchsorted(idx, p_, "left"))
                if k < nb:
                    bad[k] = True
            for k in range(nb):
                if (sid, int(idx[k])) in self.add:
                    bad[k] = True
                if (sid, int(idx[k])) in self.rem:
                    bad[k] = False
            self.cache[sid] = (idx, np.asarray(B["c"], float), np.asarray(B["o"], float), bad)
        return self.cache[sid]

    def ret(self, sid, e, x):
        """e 進場日曆位置（必須有 K 棒）、x 目標出場日曆位置（可超出）⇒ (R, 型態)。逐根往前走。"""
        idx, c, o, bad = self.bars(sid)
        ke = int(np.searchsorted(idx, e))
        assert idx[ke] == e, f"{sid} 進場日無 K 棒"
        xe = min(x, self.n0 - 1)
        k = ke
        while k + 1 < len(idx) and idx[k + 1] <= xe:
            if bad[k + 1]:
                return c[k] / o[ke] - 1.0, "壞根前一根強制"
            k += 1
        last = len(idx) - 1
        if idx[last] < x and self.n0 - 1 - idx[last] >= 5:
            return c[last] / o[ke] - 1.0, "下市末根"
        if x > self.n0 - 1:
            return np.nan, "超出資料尾不可算"
        return c[k] / o[ke] - 1.0, "到期收盤" if idx[k] == xe else "到期日無成交用前一根"


def lock_check():
    out = subprocess.run([sys.executable, "-m", "backtest.strategy_lock", "--check"], capture_output=True, text=True)
    chk("C1 策略鎖相符", out.returncode == 0 and "相符" in out.stdout, out.stdout.strip().splitlines()[-1] if out.stdout.strip() else out.stderr[-200:])


def main():
    lock_check()
    J = json.load(open(os.path.join(OUT, "IndMom.json"), encoding="utf-8"))
    EV = pd.concat([pd.read_csv(os.path.join(OUT, f"events_{w}.csv.gz")) for w in ("主", "早年")], ignore_index=True)
    TB = pd.read_csv(os.path.join(OUT, "IndMom_表.csv"))
    FK = pd.read_csv(os.path.join(OUT, "fake_reps.csv"))
    RC = pd.read_csv(os.path.join(OUT, "recon_freq.csv"))
    EXD = pd.read_csv(os.path.join(OUT, "exright_diff.csv"), dtype=str)
    MF = pd.read_csv(os.path.join(IMX.FREQ_DIR, "monthly.csv"), dtype=str, keep_default_na=False)
    # C2
    chk("C2a recon_freq 全同", bool(RC["相同"].all()) and len(RC) == 259, f"{int(RC['相同'].sum())}／{len(RC)} 列")
    jd = EV[(EV["臂"] == "市值加權6月(判定)") & (EV["H"] == 6)]
    exm = set(zip(EXD["世界"], EXD["date"])) if len(EXD) else set()
    mism = 0
    for (w, t), g in jd.groupby(["世界", "形成月底"]):
        f = MF[(MF["世界"] == w) & (MF["形成月底"] == t)]
        if f.empty or set(f.iloc[0]["市值加權前3"].split("｜")) != set(g["產業"]):
            if (w, t) not in exm:
                mism += 1
    chk("C2b 判定格逐月入選 ＝ 頻率表市值加權前3", mism == 0, f"不同 {mism} 月（exright 差異月除外）")
    # 面板（成員重建用）
    DATA = IMX.pinned_data(IMX.PIN_SHA)
    PIT = IM.load_pit(DATA)
    rng = np.random.default_rng(20261021)
    for wn, nsamp in (("主", 6), ("早年", 2)):
        Zo = IMX.aux2(IM.panel_aux(IM.build_panel(wn, 2)))
        Zx = IMX.make_x(Zo, IMX.build_exr(Zo))
        cal = Zx["cal"]; n0 = Zx["n0"]
        ME, MK = PF.month_ends(cal); EP = PF.entry_pos(cal, MK, 1)
        jix = {str(cal[int(ME[j])].date()): j for j in range(len(ME))}
        IP = Indep(wn)
        g = jd[jd["世界"] == wn]
        sub = g.iloc[rng.choice(len(g), nsamp, replace=False)]
        errs = []
        for _, r in sub.iterrows():
            j = jix[r["形成月底"]]; t = int(ME[j]); e = int(EP[j]); x = int(ME[j + 6])
            mem, _, univ = IM.month_table(Zx, PIT, ME, j, 6)
            num = den = 0.0
            for (i, _, _) in mem[r["產業"]]:
                if IM.entry_flag(Zx, i, t, e) != "保留":
                    continue
                Rv, _ = IP.ret(Zx["sids"][i], e, x)
                if np.isfinite(Rv):
                    w = Zx["MC"][i, t]; num += w * Rv; den += w
            errs.append(abs(num / den - r["R產業"]))
            log(f"   {wn} {r['形成月底']} {r['產業']}：手算 {num / den:+.6f} vs 檔 {r['R產業']:+.6f}")
        chk(f"C3a {wn} 抽 {nsamp} 筆 R產業 手算", max(errs) < 1e-9, f"最大誤差 {max(errs):.2e}")
        # 全市場 1 個月
        r = g.iloc[len(g) // 2]
        j = jix[r["形成月底"]]; t = int(ME[j]); e = int(EP[j]); x = int(ME[j + 6])
        _, _, univ = IM.month_table(Zx, PIT, ME, j, 6)
        num = den = 0.0
        for i in univ:
            if IM.entry_flag(Zx, i, t, e) != "保留":
                continue
            Rv, _ = IP.ret(Zx["sids"][i], e, x)
            if np.isfinite(Rv):
                w = Zx["MC"][i, t]; num += w * Rv; den += w
        chk(f"C3b {wn} {r['形成月底']} 全市場 R 手算（{len(univ)} 檔）", abs(num / den - r["R市場"]) < 1e-9, f"{num / den:+.6f} vs {r['R市場']:+.6f}")
        # C4 不前視
        bad = 0
        js = rng.choice([jj for jj in range(6, len(ME) - 1)], 3, replace=False)
        for jj in js:
            t = int(ME[jj])
            Zt = dict(Zx)
            for k in ("C", "MC"):
                A = np.array(Zx[k], copy=True); A[:, t + 1:] = np.nan; Zt[k] = A
            G = np.array(Zx["G"], copy=True); G[:, t + 1:] = False; Zt["G"] = G
            Bd = np.array(Zx["BAD"], copy=True); Bd[:, t + 1:] = True; Zt["BAD"] = Bd
            for k in ("CB", "VP"):
                Zt.pop(k, None)
            Zt = IM.panel_aux(Zt)
            a1 = IM.rank_inds(IM.month_table(Zx, PIT, ME, jj, 6)[0])["vw"][:3]
            a2 = IM.rank_inds(IM.month_table(Zt, PIT, ME, jj, 6)[0])["vw"][:3]
            bad += [k for k, _ in a1] != [k for k, _ in a2]
        chk(f"C4a {wn} 抹掉 t 之後資料重排入選不變（3 個月）", bad == 0)
    chk("C4b 全部事件 進場日 ＞ 形成月底", bool((pd.to_datetime(EV["進場日"]) > pd.to_datetime(EV["形成月底"])).all()))
    # C5
    worst = 0.0; nbad = 0
    for _, r in TB.iterrows():
        g = EV[(EV["世界"] == r["世界"]) & (EV["段"] == r["段"]) & (EV["臂"] == r["臂"]) & (EV["H"] == r["H"])]
        st = IMX.stats(g["X"], g["進場月"])
        for k in ("X̄", "lo", "hi"):
            worst = max(worst, abs(st[k] - r[k]))
        nbad += (st["n"] != r["n"]) or (st["n_eff"] != r["n_eff"]) or (st["結果"] != r["結果"])
        if r["臂"] == "市值加權6月(判定)" and r["H"] == 6:
            fk = FK[(FK["世界"] == r["世界"]) & (FK["段"] == r["段"])]
            nbad += int((fk["結果"] == "結果②").sum()) != int(r["假訊號x(／30)"]) or len(fk) != 30
    chk("C5 彙總重算（全表）", worst < 1e-12 and nbad == 0, f"最大誤差 {worst:.2e}、不符 {nbad}")
    # C6
    row = EXD[(EXD["sid"] == "2464") & (EXD["date"] == "2026-09-02")]
    T = IMX.load_exr_table()
    ob = dict((str(d.date()), v) for d, v in T["tab"].get("2464", []))["2026-09-02"]
    raw = pd.read_csv(os.path.join(AT.WORLDS["主"]["data"], "stocks", "2464.csv"), dtype={"date": str})
    rc = float(raw.loc[raw["date"] == "2026-09-02", "close"].iloc[0])
    chk("C6 2464 2026-09-02 權息同日：幽靈壞根拿掉、收盤÷open_base 在帶內", len(row) == 1 and row.iloc[0]["項"] == "幽靈壞根拿掉" and 0.895 <= rc / ob <= 1.105,
        f"收盤 {rc} ÷ open_base {ob} ＝ {rc / ob:.4f}")
    allok = all(OK.values())
    log(f"{'✅ 全部通過' if allok else '❌ 有不通過'}（{sum(OK.values())}／{len(OK)}）")
    json.dump({"全部通過": allok, "項": OK}, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
