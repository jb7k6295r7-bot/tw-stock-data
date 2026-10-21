# -*- coding: utf-8 -*-
"""mktdrop_fwd 大跌加碼高10／0050（2026-10-21 加）自測——回測線開發子代理。
⛔ 不算任何真實報酬：價格一律合成（monkeypatch mktdrop_fwd.one）、指數合成；只用真快照的交易日曆與 meta。
⛔ 不寫真紀錄：RM.FWD、positions_user、pth10 state、設定檔全部指到暫存夾。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.mktdrop_fwd_addon_check [--sha SHA] [--skip-regress]

F1 事件夜：高10 持股（市值比例）＋ 0050 兩行【LINE】、待買列；買進日 ＞ t、賣出日 ≤ t 的不算；明天到期的註明
F2 無高10 紀錄 ⇒ 只 0050、「高10 尚未開始持有」；有紀錄但 0 檔 ⇒「高10 目前沒有持股」
F3 設定有金額 ⇒ 股數 ＝ floor(總額×權重÷收盤)；缺鍵／null ⇒ 不換算、「金額照你決定」
F3c 今天月初買進、pth10 今晚才登（state.json 名單）⇒ 也算持股
F4 隔天：買進列（未還原開盤）；買不到 ⇒ 其餘權重放大
F5 高10 明天到期 ⇒ 前一晚【LINE】；到期日收盤加碼那份同日出（報酬照式）
F6 收復夜【LINE】賣回（只列還在手上的加碼）；隔天開盤出場（報酬照式）
F7 高10 非排程出場（positions_user 賣出日 ≠ 排程）⇒ 加碼那份同日出＋【LINE】
F8 既有第八節行逐字不變（section 加 ADD 前後；真快照 2026-10-20 daily --nowrite 第八節 ＝ 現有名單）
F9 ADD_BT 數字 ＝ resultsDropAddSelf/split/table.csv 確認段 A 臂（高10 F9 版、0050；11 次）
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import numpy as np
import pandas as pd

REPO = os.path.expanduser("~/tw-p17")
sys.path.insert(0, REPO)
from backtest import data as D                              # noqa: E402
from backtest import mktdrop_fwd as M                       # noqa: E402
from backtest import researchMktDrop_v1 as RM               # noqa: E402

SHA0 = "c1db66ce973025613512c3a318411db17e842f2a"
OK = []


def chk(name, cond, msg=""):
    OK.append((name, bool(cond)))
    print(("✅ " if cond else "❌ ") + name + ("" if cond else f"｜{msg}"))


# ═════════════ 合成價格 ═════════════
class Fake:
    """每檔：還原＝未還原；開盤 o[k] ＝ base×(1＋a·(k−pt))、收盤 ＝ 開盤×1.01；可指定沒成交、鎖漲停根。"""
    def __init__(self, n, pt):
        self.n, self.pt, self.cfg = n, pt, {}

    def set(self, sid, base, a, notrd=(), upl=()):
        self.cfg[sid] = (base, a, set(notrd), set(upl))

    def px(self, sid):
        base, a, nt, up = self.cfg[sid]
        k = np.arange(self.n)
        o = base * (1 + a * (k - self.pt)); c = o * 1.01
        return o, c

    def one(self, sid, mk, cal, DATA):
        base, a, nt, up = self.cfg[sid]
        o, c = self.px(sid)
        trd = np.ones(self.n, bool); trd[list(nt)] = False
        o = o.copy(); c = c.copy(); o[list(nt)] = np.nan; c[list(nt)] = np.nan
        upl = np.zeros(self.n, bool); upl[list(up)] = True
        z = np.zeros(self.n, bool)
        return {"ro": o, "rh": c, "rl": o, "rc": c, "ao": o, "ac": c, "trd": trd, "upl": upl, "dnl": z, "bad": z.copy()}


def setup(tmp, cal, pt, idx_close, usr_rows=None, state=None, setting=None):
    """暫存夾：fwd／positions_user／state／設定；指數合成。"""
    fwd = os.path.join(tmp, "fwd")
    shutil.rmtree(fwd, ignore_errors=True); os.makedirs(fwd)
    RM.FWD = fwd
    M.PTH10_USR = os.path.join(tmp, "positions_user.csv")
    M.PTH10_ST = os.path.join(tmp, "state.json")
    M.SETTING = os.path.join(tmp, "設定.json")
    for p in (M.PTH10_USR, M.PTH10_ST, M.SETTING):
        if os.path.exists(p):
            os.remove(p)
    if usr_rows is not None:
        from backtest.pth10_daily import USR_COLS
        pd.DataFrame([{c: r.get(c, "") for c in USR_COLS} for r in usr_rows], columns=USR_COLS).to_csv(M.PTH10_USR, index=False, encoding="utf-8-sig")
    if state is not None:
        json.dump(state, open(M.PTH10_ST, "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(setting if setting is not None else {"說明": "x", "高10": 20000}, open(M.SETTING, "w", encoding="utf-8"), ensure_ascii=False)
    dates = cal[pt - 30: pt + 12]
    df = pd.DataFrame({"date": dates, "close": [idx_close(int(cal.get_loc(d)) - pt) for d in dates]})
    RM.read_index = lambda sha=None: (sha, df)
    RM.fwd_init()
    RM.fwd_append_event({"序號": 1, "事件日": str(cal[pt].date()), "入判": "是", "指數收盤": idx_close(0), "前一日收盤（收復目標）": idx_close(-1),
                         "指數報酬": idx_close(0) / idx_close(-1) - 1, "門檻q": -0.03, "判定": "事件", "狀態": "待買", "指數sha": "fixture", "寫入時間": "x"})
    return fwd


REG_ASOF = "2026-10-20"


def regress(sha, tmp):
    """真快照、真紀錄夾、--nowrite：新版第八節 ＝ 現有名單第八節（到「## 九」之前）；紀錄夾每檔位元組不變。"""
    import hashlib
    src = os.path.join(REPO, "backtest", "resultsDaily", f"daily_{REG_ASOF}.md")
    old = open(src, encoding="utf-8").read()
    k = old.find("\n" + M.SEC_TITLE)
    k9 = old.find("\n## 九、", k + 1)
    md = os.path.join(tmp, "reg.md")
    open(md, "w", encoding="utf-8").write(old[:k])
    fdir = os.path.join(REPO, "backtest", "forward", "mktdrop")
    h0 = {f: hashlib.md5(open(os.path.join(fdir, f), "rb").read()).hexdigest() for f in sorted(os.listdir(fdir))}
    r = subprocess.run([sys.executable, "-m", "backtest.mktdrop_fwd", "daily", "--asof", REG_ASOF, "--sha", sha, "--md", md, "--nowrite"],
                       cwd=REPO, env={**os.environ, "PYTHONPATH": REPO}, capture_output=True, text=True, timeout=540)
    h1 = {f: hashlib.md5(open(os.path.join(fdir, f), "rb").read()).hexdigest() for f in sorted(os.listdir(fdir))}
    new = open(md, encoding="utf-8").read()
    want = old[:k9] if k9 >= 0 else old
    return (r.returncode == 0 and new == want and h0 == h1), f"rc {r.returncode}｜{r.stderr[-500:]}｜紀錄不變 {h0 == h1}"


def J_of(cal, pt, idx_close):
    return {"狀態": "事件", "日期": str(cal[pt].date()), "收盤": idx_close(0), "前一日收盤": idx_close(-1), "指數報酬": idx_close(0) / idx_close(-1) - 1, "門檻": -0.03}


def lines_of(ADD):
    return [x for v in ADD.values() for x in v]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--sha", default=SHA0); ap.add_argument("--skip-regress", action="store_true")
    a = ap.parse_args()
    DATA = M.ddir(a.sha); D.DATA = DATA; cal = D.load_calendar()
    pt = int(cal.searchsorted(pd.Timestamp("2026-09-15")))
    ds = lambda k: str(cal[pt + k].date())                       # noqa: E731
    F = Fake(len(cal), pt)
    F.set("2330", 1000.0, 0.01); F.set("2454", 1500.0, -0.005); F.set("0050", 100.0, 0.004); F.set("3008", 2000.0, 0.0, upl={pt + 1})
    F.set("2317", 200.0, 0.002)
    M.one = F.one
    idx = lambda d: {-1: 100.0, 0: 96.0, 1: 97.0, 2: 97.5, 3: 98.0, 4: 99.0, 5: 100.2}.get(d, 100.0 if d < 0 else 101.0)   # noqa: E731
    J = J_of(cal, pt, idx)
    tmp = tempfile.mkdtemp(prefix="mda_addon_")
    sched_2454 = ds(3)
    USR = [{"批次": "2026-08-31", "代號": "2330", "名稱": "台積電", "股數": "20", "買進日": ds(-5), "買進價": "1", "狀態": "持有中", "排程賣出日": "2027-03-31"},
           {"批次": "2026-08-31", "代號": "2454", "名稱": "聯發科", "股數": "10", "買進日": ds(-5), "買進價": "1", "狀態": "持有中", "排程賣出日": sched_2454},
           {"批次": "2026-08-31", "代號": "2317", "名稱": "鴻海", "股數": "50", "買進日": ds(1), "買進價": "1", "狀態": "持有中", "排程賣出日": "2027-03-31"},
           {"批次": "2026-03-31", "代號": "2603", "名稱": "長榮", "股數": "50", "買進日": ds(-60), "買進價": "1", "狀態": "已出場", "排程賣出日": ds(0), "賣出日": ds(0)}]
    try:
        # ── F1 事件夜
        fwd = setup(tmp, cal, pt, idx, USR)
        ADD, info = M.add_daily(ds(0), a.sha, J, write=True)
        top = ADD.get("top", [])
        A = M.read_rows(M.ADD_FN)
        c0 = {s: F.px(s)[1][pt] for s in ("2330", "2454", "0050")}
        mv = np.array([20 * c0["2330"], 10 * c0["2454"]]); w = mv / mv.sum()
        chk("F1 兩行都是【LINE】⭐ 格式", len(top) == 2 and all(x.startswith("  - 【LINE】⭐ ") for x in top), top)
        chk("F1 高10 行列 2330、2454，不列 2317（買進日＞t）、2603（t 已賣）", "2330 台積電" in top[0] and "2454 聯發科" in top[0] and "2317" not in top[0] and "2603" not in top[0], top[0])
        chk("F1 權重 ＝ 事件日收盤市值比例", f"2330 台積電 {w[0]:.0%}" in top[0] and f"2454 聯發科 {w[1]:.0%}" in top[0], (w, top[0]))
        chk("F1 0050 行", "大跌加碼 0050（六四中的 0050）：明天開盤買 0050" in top[1], top[1])
        chk("F1 兩行附回測句", all(M.ADD_BT in x for x in top))
        chk("F1 收復價 ＝ 大跌 4 檔同一（前一日收盤）", all("加權收盤 ≥ 100.00" in x for x in top))
        chk("F1 無金額 ⇒ 不換算股數、寫「金額照你決定」", all("金額照你決定" in x and not re.search(r"約 \d+ 股", x) for x in top), top)
        chk("F1 待買 3 列（序號 1）", len(A) == 3 and all(r["狀態"] == "待買" and r["序號"] == "1" for r in A), A)
        chk("F1 權重欄", abs(float(A[0]["權重"]) - w[0]) < 1e-12 and float(A[2]["權重"]) == 1.0)
        ADDr, _ = M.add_daily(ds(0), a.sha, J, write=True)
        chk("F1 重跑：不重寫列、行相同", len(M.read_rows(M.ADD_FN)) == 3 and ADDr.get("top") == top)
        # ── F2 無高10
        setup(tmp, cal, pt, idx, None)
        ADD2, _ = M.add_daily(ds(0), a.sha, J, write=False)
        t2 = ADD2.get("top", [])
        chk("F2 無高10 紀錄 ⇒ 只 0050 一行、寫「高10 尚未開始持有」", len(t2) == 1 and "0050" in t2[0] and "高10 尚未開始持有" in t2[0], t2)
        chk("F2 nowrite ⇒ 沒寫 addon 檔", not os.path.exists(os.path.join(RM.FWD, M.ADD_FN)))
        setup(tmp, cal, pt, idx, [USR[3]])
        t2b = M.add_daily(ds(0), a.sha, J, write=False)[0].get("top", [])
        chk("F2b 有紀錄但 0 檔 ⇒「高10 目前沒有持股」", len(t2b) == 1 and "高10 目前沒有持股" in t2b[0], t2b)
        # ── F3 金額
        setup(tmp, cal, pt, idx, USR, setting={"說明": "x", "大跌加碼_高10": 100000, "大跌加碼_0050": 50000})
        t3 = M.add_daily(ds(0), a.sha, J, write=False)[0]["top"]
        s1 = int(np.floor(100000 * w[0] / c0["2330"] + 1e-9)); s2 = int(np.floor(100000 * w[1] / c0["2454"] + 1e-9)); s5 = int(np.floor(50000 / c0["0050"] + 1e-9))
        chk("F3 股數 ＝ floor(總額×權重÷收盤)", f"約 {s1} 股" in t3[0] and f"約 {s2} 股" in t3[0] and f"約 {s5} 股" in t3[1] and "共 10 萬" in t3[0], (s1, s2, s5, t3))
        chk("F3 有金額 ⇒ 不寫「金額照你決定」", all("金額照你決定" not in x for x in t3))
        setup(tmp, cal, pt, idx, USR, setting={"說明": "x", "大跌加碼_高10": None})
        t3b = M.add_daily(ds(0), a.sha, J, write=False)[0]["top"]
        chk("F3b null ⇒ 不換算", all("金額照你決定" in x and not re.search(r"約 \d+ 股", x) for x in t3b), t3b)
        # ── F3c 今天月初買進、pth10 今晚才登
        st = {"名單": {ds(0): {"批次": "2026-08-31", "名單日": ds(-1), "rows": [["2317", "鴻海", 200.0, 100], ["3008", "大立光", 2000.0, 10]]}}}
        setup(tmp, cal, pt, idx, USR[:2], state=st)
        F.set("3008", 2000.0, 0.0, upl={pt})
        t3c = M.add_daily(ds(0), a.sha, J, write=False)[0]["top"]
        chk("F3c state 名單（今天買進）算持股、開盤鎖漲停買不到的不算", "2317 鴻海" in t3c[0] and "3008" not in t3c[0], t3c)
        F.set("3008", 2000.0, 0.0, upl={pt + 1})
        # ── F4 隔天：買進（加一檔 3008 隔天開盤鎖漲停 ⇒ 買不到）
        USR4 = USR + [{"批次": "2026-08-31", "代號": "3008", "名稱": "大立光", "股數": "5", "買進日": ds(-5), "買進價": "1", "狀態": "持有中", "排程賣出日": "2027-03-31"}]
        setup(tmp, cal, pt, idx, USR4)
        M.add_daily(ds(0), a.sha, J, write=True)
        ADD4, info4 = M.add_daily(ds(1), a.sha, {"狀態": "非事件"}, write=True)
        A = {r["代號"]: r for r in M.read_rows(M.ADD_FN)}
        o1 = {s: F.px(s)[0][pt + 1] for s in ("2330", "2454", "0050")}
        chk("F4 買進日／買進價 ＝ e 未還原開盤", all(A[s]["狀態"] == "持有中" and A[s]["買進日"] == ds(1) and abs(float(A[s]["買進價"]) - o1[s]) < 1e-9 for s in o1), A)
        chk("F4 開盤鎖漲停 ⇒ 買不到", A["3008"]["狀態"] == "買不到" and "開盤漲停鎖死" in A["3008"]["備註"], A["3008"])
        L4 = lines_of(ADD4)
        chk("F4 隔天沒有【LINE】（只有內部帳面行）", not any("【LINE】" in x for x in L4) and any("買不到 1 檔" in x for x in L4), L4)
        # ── F5 高10 明天到期（2454 排程 ds(3)）
        L5 = lines_of(M.add_daily(ds(2), a.sha, {"狀態": "非事件"}, write=True)[0])
        chk("F5 前一晚【LINE】：明天高10 到期賣 2454 ⇒ 加碼那份同日一起賣", any(x.startswith("  - 【LINE】⭐ 大跌加碼高10：明天") and "2454 聯發科" in x and "2330" not in x for x in L5), L5)
        L5b = lines_of(M.add_daily(ds(3), a.sha, {"狀態": "非事件"}, write=True)[0])
        A = {r["代號"]: r for r in M.read_rows(M.ADD_FN)}
        o, c = F.px("2454"); ex = (c[pt + 3] / o[pt + 1]) * (1 - RM.COST_STK) - 1
        chk("F5 到期日收盤出場（高10 規則）、報酬照式", A["2454"]["狀態"] == "已出場" and A["2454"]["出場日"] == ds(3) and A["2454"]["出場種類"] == M.K_RULE
            and abs(float(A["2454"]["報酬"]) - ex) < 1e-12 and abs(float(A["2454"]["出場價"]) - c[pt + 3]) < 1e-9, A["2454"])
        chk("F5 排程到期不再發非排程【LINE】、其他仍持有", not any("非排程" in x for x in L5b) and A["2330"]["狀態"] == "持有中" and A["0050"]["狀態"] == "持有中", L5b)
        # ── F6 收復夜（ds(5) 加權 100.2 ≥ 100）
        L6 = lines_of(M.add_daily(ds(5), a.sha, {"狀態": "非事件"}, write=True)[0])
        rec = [x for x in L6 if "大跌加碼賣回提醒" in x]
        chk("F6 收復夜【LINE】賣回：列 2330、0050，不列已出的 2454、買不到的 3008",
            len(rec) == 1 and rec[0].startswith("  - 【LINE】⭐ ") and "2330 台積電" in rec[0] and "0050 加碼那份" in rec[0] and "2454" not in rec[0] and "3008" not in rec[0]
            and M.ADD_BT in rec[0] and "≥ 100.00" in rec[0], rec)
        M.add_daily(ds(6), a.sha, {"狀態": "非事件"}, write=True)
        A = {r["代號"]: r for r in M.read_rows(M.ADD_FN)}
        good = True
        for s, cost in (("2330", RM.COST_STK), ("0050", RM.COST_ETF)):
            o, c = F.px(s); ex = (o[pt + 6] / o[pt + 1]) * (1 - cost) - 1
            good &= A[s]["狀態"] == "已出場" and A[s]["出場日"] == ds(6) and A[s]["出場種類"] == M.K_REC and abs(float(A[s]["報酬"]) - ex) < 1e-12
        chk("F6 收復隔天開盤賣回、報酬照式（個股 0.585%、ETF 0.385%）", good, A)
        L6c = lines_of(M.add_daily(ds(7), a.sha, {"狀態": "非事件"}, write=False)[0])
        chk("F6 全出場後隔晚不再出行", L6c == [], L6c)
        # ── F7 高10 非排程出場（positions_user 2330 賣出日 ds(2)，排程 2027-03-31）
        setup(tmp, cal, pt, idx, USR)
        M.add_daily(ds(0), a.sha, J, write=True); M.add_daily(ds(1), a.sha, {"狀態": "非事件"}, write=True)
        U7 = [dict(r) for r in USR]; U7[0].update({"狀態": "已出場", "賣出日": ds(2)})
        from backtest.pth10_daily import USR_COLS
        pd.DataFrame([{c_: r.get(c_, "") for c_ in USR_COLS} for r in U7], columns=USR_COLS).to_csv(M.PTH10_USR, index=False, encoding="utf-8-sig")
        L7 = lines_of(M.add_daily(ds(2), a.sha, {"狀態": "非事件"}, write=True)[0])
        A = {r["代號"]: r for r in M.read_rows(M.ADD_FN)}
        chk("F7 高10 非排程出場 ⇒ 加碼那份同日收盤出、【LINE】", A["2330"]["狀態"] == "已出場" and A["2330"]["出場日"] == ds(2) and "非排程" in A["2330"]["出場種類"]
            and any(x.startswith("  - 【LINE】⭐ 大跌加碼高10：2330 台積電") for x in L7), (A["2330"], L7))
        # ── F8 既有行逐字不變
        RM.FWD = os.path.join(REPO, "backtest", "forward", "mktdrop")
        RM.read_index = RM_read_index; M.one = M_one
        RS = M.recovery("2026-10-20", a.sha, write=False)
        J8 = RM.judge_date("2026-10-20")
        base = M.section(J8, RS, RM.FWD)
        fake = {"top": ["  - 【LINE】⭐ X1"], "0": ["  - 【LINE】⭐ X2"], "tail": ["- X3"]}
        withA = M.section(J8, RS, RM.FWD, fake)
        chk("F8 section 加 ADD 後拿掉新增行 ＝ 舊版逐字", [x for x in withA if x not in ("  - 【LINE】⭐ X1", "  - 【LINE】⭐ X2", "- X3")] == base
            and M.section(J8, RS, RM.FWD, {}) == base and M.section(J8, RS, RM.FWD, None) == base)
        i2 = withA.index("  - 【LINE】⭐ X2")
        chk("F8 事件區塊內的行接在收復／加碼線行之後、帳面行之前", withA[i2 + 1].startswith("  - 帳面") and withA[i2 - 1].startswith("  - 【LINE】大跌加碼線"), withA[i2 - 2:i2 + 2])
        if not a.skip_regress:
            chk(f"F8 真快照 {REG_ASOF} daily --nowrite：第八節與現有名單逐字相同、紀錄檔不變", *regress(a.sha, tmp))
        # ── F9 回測句
        T = pd.read_csv(os.path.join(REPO, "backtest", "resultsDropAddSelf", "split", "table.csv"))
        T = T[(T["段"] == "確認") & (T["臂"] == "A")].set_index("策略")
        h, z = T.loc["高10（F9 同分排序，使用者版）"], T.loc["0050"]
        chk("F9 回測句 ＝ table.csv 確認段 A 臂（11 次、+4.2%、+3.8%）",
            int(h["事件數"]) == 11 and int(z["事件數"]) == 11 and f"{h['事件報酬平均']:+.1%}" == "+4.2%" and f"{z['事件報酬平均']:+.1%}" == "+3.8%"
            and "2022 起 11 次" in M.ADD_BT and "+4.2%" in M.ADD_BT and "+3.8%" in M.ADD_BT and h["窗"].startswith("2022"), (h["事件報酬平均"], z["事件報酬平均"]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    n_bad = sum(not x for _, x in OK)
    print(f"\n{'全部通過' if not n_bad else f'❌ {n_bad} 項沒過'}（{len(OK)} 項）")
    sys.exit(1 if n_bad else 0)


RM_read_index = RM.read_index
M_one = M.one

if __name__ == "__main__":
    main()
