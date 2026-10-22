# -*- coding: utf-8 -*-
"""mktdrop_fwd 大跌加碼高10／0050（2026-10-21 加）自測——回測線開發子代理。
⛔ 不算任何真實報酬：價格一律合成（monkeypatch mktdrop_fwd.one）、指數合成；只用真快照的交易日曆與 meta。
⛔ 不寫真紀錄：RM.FWD、positions_user、pth10 state、設定檔全部指到暫存夾。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.mktdrop_fwd_addon_check [--sha SHA] [--skip-regress]

F1 事件夜：高10 持股（每檔一份）＋ 0050 兩行「- 【LINE】⭐ 大跌加碼：」、待買列（權重等額）；買進日 ＞ t、賣出日 ≤ t 的不算；第十一節＝標題＋兩行
F2 無高10 紀錄 ⇒ 只 0050、「高10 尚未開始持有」；有紀錄但 0 檔 ⇒「高10 目前沒有持股」；無事件夜無紀錄 ⇒ 不產第十一節
F3 設定有金額 ⇒ 每檔等額、股數 ＝ floor(一份÷收盤)；缺鍵／null ⇒ 不換算、「金額照你決定」
F3c 今天月初買進、pth10 今晚才登（state.json 名單）⇒ 也算持股
F4 隔天：買進列（未還原開盤）；買不到 ⇒ 其餘等權；只有不推的前瞻紀錄行
F5 高10 明天到期 ⇒ 前一晚【LINE】；到期日收盤加碼那份同日出（報酬照式）
F6 收復夜【LINE】賣回（只列還在手上的加碼）；隔天開盤出場（報酬照式）；全出場後不產第十一節
F7 高10 非排程出場（positions_user 賣出日 ≠ 排程）⇒ 加碼那份同日出＋【LINE】
F10 第十一節 put11 冪等、沒要報且沒舊節 ⇒ 檔案不動；pth10_daily.put 不蓋掉；sec11 搬檔尾冪等；沒要報 ⇒ 拿掉舊節
F8 第八節回到改前：section()／put_section() 原始碼 ＝ 15c29eb178；真快照 2026-10-20 daily --nowrite 名單 ＝ 現有名單（第八節逐字、無第十一節）
F9 ADD_BT 數字 ＝ resultsDropAddSelf/split/table.csv 確認段 A 臂（高10 F9 版、0050；11 次）
F11 升降單位／限價（範例＋隨機 12,040 例）；F12～F14 第十四節（事件夜買、加碼線夜買、漲回夜賣；股數、限價、交割戶、處置股）
F15 ⚠⚠ 守門（缺節 ⇒ 標題下 ⚠⚠、exit 3、冪等；daily 整合）；F16 休市表缺 ⇒ 只扣週末＋⚠；F17 user-add；F18 reorder 再出；F19 sec11 搬十一、十四節
F20 T+2 交割日：買末列「｜T+2 扣款 M/D」、賣標頭「｜T+2 入帳 M/D」；跨週末、10/26 休市、春節結算交割日、跨年、休市表缺
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
    """真快照、真紀錄夾、--nowrite：新版第八節 ＝ 現有名單第八節（到「## 九」之前）、無第十一節；紀錄夾每檔位元組不變。"""
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
        P = M.ADD_LINE
        fwd = setup(tmp, cal, pt, idx, USR)
        ADD, info = M.add_daily(ds(0), a.sha, J, write=True)
        top = ADD.get("top", [])
        A = M.read_rows(M.ADD_FN)
        c0 = {s: F.px(s)[1][pt] for s in ("2330", "2454", "0050")}
        chk("F1 兩行都是「- 【LINE】⭐ 大跌加碼：」", len(top) == 2 and all(x.startswith("- 【LINE】⭐ 大跌加碼：") for x in top), top)
        chk("F1 高10 行：每檔加一份，列 2330、2454，不列 2317（買進日＞t）、2603（t 已賣）",
            top[0].startswith(P + "高10 明天開盤每檔加一份：") and "2330 台積電" in top[0] and "2454 聯發科" in top[0] and "2317" not in top[0] and "2603" not in top[0]
            and "%" not in top[0].split("｜")[0], top[0])
        chk("F1 0050 行", top[1].startswith(P + "0050 明天開盤加一份（金額照你決定）（六四中的 0050）"), top[1])
        chk("F1 兩行附回測句（含「回測為按持股市值比例」）", all(M.ADD_BT in x for x in top) and "回測為按持股市值比例" in M.ADD_BT)
        chk("F1 收復價 ＝ 大跌 4 檔同一（前一日收盤）", all("加權收盤 ≥ 100.00" in x for x in top))
        chk("F1 無金額 ⇒ 不換算股數、寫「金額照你決定」", all("金額照你決定" in x and not re.search(r"約 \d+ 股", x) for x in top), top)
        chk("F1 待買 3 列（序號 1）", len(A) == 3 and all(r["狀態"] == "待買" and r["序號"] == "1" for r in A), A)
        chk("F1 照規則紀錄每檔等額（權重 1/2、1/2；0050 1）", float(A[0]["權重"]) == 0.5 and float(A[1]["權重"]) == 0.5 and float(A[2]["權重"]) == 1.0
            and "回測 A 臂為市值比例" in A[0]["備註"], A)
        ADDr, _ = M.add_daily(ds(0), a.sha, J, write=True)
        chk("F1 重跑：不重寫列、行相同", len(M.read_rows(M.ADD_FN)) == 3 and ADDr.get("top") == top)
        L11 = M.add_run(ds(0), a.sha, J, write=False)[0]
        chk("F1 第十一節：標題＋空行＋兩行", L11[:2] == [M.SEC11_TITLE, ""] and L11[2:] == top, L11)
        # ── F2 無高10
        setup(tmp, cal, pt, idx, None)
        ADD2, _ = M.add_daily(ds(0), a.sha, J, write=False)
        t2 = ADD2.get("top", [])
        chk("F2 無高10 紀錄 ⇒ 只 0050 一行、寫「高10 尚未開始持有」", len(t2) == 1 and t2[0].startswith(P + "0050") and "高10 尚未開始持有" in t2[0], t2)
        chk("F2 nowrite ⇒ 沒寫 addon 檔", not os.path.exists(os.path.join(RM.FWD, M.ADD_FN)))
        setup(tmp, cal, pt, idx, [USR[3]])
        t2b = M.add_daily(ds(0), a.sha, J, write=False)[0].get("top", [])
        chk("F2b 有紀錄但 0 檔 ⇒「高10 目前沒有持股」", len(t2b) == 1 and "高10 目前沒有持股" in t2b[0], t2b)
        chk("F2c 無事件夜、無加碼紀錄 ⇒ 不產第十一節", M.add_run(ds(1), a.sha, {"狀態": "非事件"}, write=False)[0] == [])
        # ── F3 金額：每檔一份
        setup(tmp, cal, pt, idx, USR, setting={"說明": "x", "大跌加碼_高10": 20000, "大跌加碼_0050": 20000})
        t3 = M.add_daily(ds(0), a.sha, J, write=False)[0]["top"]
        s1 = int(np.floor(20000 / c0["2330"] + 1e-9)); s2 = int(np.floor(20000 / c0["2454"] + 1e-9)); s5 = int(np.floor(20000 / c0["0050"] + 1e-9))
        chk("F3 每檔等額：股數 ＝ floor(一份÷收盤)",
            t3[0].startswith(P + "高10 明天開盤每檔加一份 2 萬：") and f"2330 台積電（約 {s1} 股）" in t3[0] and f"2454 聯發科（約 {s2} 股）" in t3[0]
            and t3[1].startswith(P + f"0050 明天開盤加一份 2 萬（約 {s5} 股，") and s1 != s2, (s1, s2, s5, t3))
        chk("F3 有金額 ⇒ 不寫「金額照你決定」", all("金額照你決定" not in x for x in t3))
        setup(tmp, cal, pt, idx, USR, setting={"說明": "x", "大跌加碼_高10": None})
        t3b = M.add_daily(ds(0), a.sha, J, write=False)[0]["top"]
        chk("F3b null／缺鍵 ⇒ 只列代號不換算", all("金額照你決定" in x and not re.search(r"約 \d+ 股", x) for x in t3b), t3b)
        # ── F3c 今天月初買進、pth10 今晚才登
        st = {"名單": {ds(0): {"批次": "2026-08-31", "名單日": ds(-1), "rows": [["2317", "鴻海", 200.0, 100], ["3008", "大立光", 2000.0, 10]]}}}
        setup(tmp, cal, pt, idx, USR[:2], state=st)
        F.set("3008", 2000.0, 0.0, upl={pt})
        t3c = M.add_daily(ds(0), a.sha, J, write=False)[0]["top"]
        chk("F3c state 名單（今天買進）算持股、開盤鎖漲停買不到的不算", "2317 鴻海" in t3c[0] and "3008" not in t3c[0], t3c)
        F.set("3008", 2000.0, 0.0, upl={pt + 1})
        # ── F4 隔天：買進（加一檔 3008 隔天開盤鎖漲停 ⇒ 買不到）
        USR4 = USR + [{"批次": "2026-08-31", "代號": "3008", "名稱": "大立光", "股數": "5", "買進日": ds(-5), "買進價": "1", "狀態": "持有中", "排程賣出日": "2027-03-31"}]
        setup(tmp, cal, pt, idx, USR4, setting={"說明": "x", "大跌加碼_高10": 20000, "大跌加碼_0050": 20000})
        M.add_daily(ds(0), a.sha, J, write=True)
        ADD4, info4 = M.add_daily(ds(1), a.sha, {"狀態": "非事件"}, write=True)
        A = {r["代號"]: r for r in M.read_rows(M.ADD_FN)}
        o1 = {s: F.px(s)[0][pt + 1] for s in ("2330", "2454", "0050")}
        chk("F4 買進日／買進價 ＝ e 未還原開盤", all(A[s]["狀態"] == "持有中" and A[s]["買進日"] == ds(1) and abs(float(A[s]["買進價"]) - o1[s]) < 1e-9 for s in o1), A)
        chk("F4 開盤鎖漲停 ⇒ 買不到", A["3008"]["狀態"] == "買不到" and "開盤漲停鎖死" in A["3008"]["備註"], A["3008"])
        L4 = lines_of(ADD4)
        chk("F4 隔天沒有【LINE】（只有不推的前瞻紀錄行）", not any("【LINE】" in x for x in L4) and any(x.startswith("- 大跌加碼前瞻紀錄") and "買不到 1 檔" in x for x in L4), L4)
        # ── F5 高10 明天到期（2454 排程 ds(3)）
        L5 = lines_of(M.add_daily(ds(2), a.sha, {"狀態": "非事件"}, write=True)[0])
        chk("F5 前一晚【LINE】：高10 明天到期賣 2454 ⇒ 加碼那份同日一起賣",
            any(x.startswith(P + "高10 明天（") and "2454 聯發科" in x and "2330" not in x and f"那份 2454 聯發科（約 {A['2454']['參考股數']} 股）同日收盤一起賣" in x for x in L5), L5)
        L5b = lines_of(M.add_daily(ds(3), a.sha, {"狀態": "非事件"}, write=True)[0])
        A = {r["代號"]: r for r in M.read_rows(M.ADD_FN)}
        o, c = F.px("2454"); ex = (c[pt + 3] / o[pt + 1]) * (1 - RM.COST_STK) - 1
        chk("F5 到期日收盤出場（高10 規則）、報酬照式", A["2454"]["狀態"] == "已出場" and A["2454"]["出場日"] == ds(3) and A["2454"]["出場種類"] == M.K_RULE
            and abs(float(A["2454"]["報酬"]) - ex) < 1e-12 and abs(float(A["2454"]["出場價"]) - c[pt + 3]) < 1e-9, A["2454"])
        chk("F5 排程到期不再發非排程【LINE】、其他仍持有", not any("非排程" in x for x in L5b) and A["2330"]["狀態"] == "持有中" and A["0050"]["狀態"] == "持有中", L5b)
        # ── F6 收復夜（ds(5) 加權 100.2 ≥ 100）
        L6 = lines_of(M.add_daily(ds(5), a.sha, {"狀態": "非事件"}, write=True)[0])
        rec = [x for x in L6 if "賣回提醒" in x]
        chk("F6 收復夜【LINE】賣回：列 2330、0050（含股數），不列已出的 2454、買不到的 3008",
            len(rec) == 1 and rec[0].startswith(P + "賣回提醒：") and f"2330 台積電（約 {A['2330']['參考股數']} 股）（高10 原持股不動）" in rec[0] and f"0050（約 {A['0050']['參考股數']} 股）" in rec[0]
            and "2454" not in rec[0] and "3008" not in rec[0] and M.ADD_BT in rec[0] and "≥ 100.00" in rec[0], rec)
        M.add_daily(ds(6), a.sha, {"狀態": "非事件"}, write=True)
        A = {r["代號"]: r for r in M.read_rows(M.ADD_FN)}
        good = True
        for s, cost in (("2330", RM.COST_STK), ("0050", RM.COST_ETF)):
            o, c = F.px(s); ex = (o[pt + 6] / o[pt + 1]) * (1 - cost) - 1
            good &= A[s]["狀態"] == "已出場" and A[s]["出場日"] == ds(6) and A[s]["出場種類"] == M.K_REC and abs(float(A[s]["報酬"]) - ex) < 1e-12
        chk("F6 收復隔天開盤賣回、報酬照式（個股 0.585%、ETF 0.385%）", good, A)
        L6c = lines_of(M.add_daily(ds(7), a.sha, {"狀態": "非事件"}, write=False)[0])
        chk("F6 全出場後隔晚不再出行、不產第十一節", L6c == [] and M.add_run(ds(7), a.sha, {"狀態": "非事件"}, write=False)[0] == [], L6c)
        # ── F7 高10 非排程出場（positions_user 2330 賣出日 ds(2)，排程 2027-03-31）
        setup(tmp, cal, pt, idx, USR)
        M.add_daily(ds(0), a.sha, J, write=True); M.add_daily(ds(1), a.sha, {"狀態": "非事件"}, write=True)
        U7 = [dict(r) for r in USR]; U7[0].update({"狀態": "已出場", "賣出日": ds(2)})
        from backtest.pth10_daily import USR_COLS
        pd.DataFrame([{c_: r.get(c_, "") for c_ in USR_COLS} for r in U7], columns=USR_COLS).to_csv(M.PTH10_USR, index=False, encoding="utf-8-sig")
        L7 = lines_of(M.add_daily(ds(2), a.sha, {"狀態": "非事件"}, write=True)[0])
        A = {r["代號"]: r for r in M.read_rows(M.ADD_FN)}
        chk("F7 高10 非排程出場 ⇒ 加碼那份同日收盤出、【LINE】", A["2330"]["狀態"] == "已出場" and A["2330"]["出場日"] == ds(2) and "非排程" in A["2330"]["出場種類"]
            and any(x.startswith(P + "高10 2330 台積電") for x in L7), (A["2330"], L7))
        # ── F10 第十一節寫法：冪等、只換自己那節、pth10.put 不會蓋掉、sec11 搬到檔尾
        from backtest import pth10_daily as PH
        md = os.path.join(tmp, "sec.md")
        head = "# 名單\n\n## 一、營量\n\n- a\n"
        open(md, "w", encoding="utf-8").write(head)
        M.put_section(md, ["## 八、（內部）大盤大跌前瞻（研究紀錄、未驗證；不推 LINE）", "", "- x", ""])
        s8 = open(md, encoding="utf-8").read()
        M.put11(md, []); same0 = open(md, encoding="utf-8").read() == s8
        M.put11(md, L11); s1_ = open(md, encoding="utf-8").read()
        M.put11(md, L11); s2_ = open(md, encoding="utf-8").read()
        chk("F10 put11 冪等、L 空且沒舊節 ⇒ 逐位元不動、第八節以前不變", same0 and s1_ == s2_ and s1_.startswith(s8) and s1_.endswith("\n".join(L11) + "\n"), s1_[-300:])
        open(md, "a", encoding="utf-8").write("\n## 九、VIX 狀態（x）\n\n- v\n")
        PH.put(md, [PH.TITLE, "", "- h1"]); PH.put(md, [PH.TITLE, "", "- h2"])
        s3_ = open(md, encoding="utf-8").read()
        chk("F10 pth10.put（換第十節）不會蓋掉第十一節", "\n".join(L11) in s3_ and s3_.count(M.SEC11_TITLE) == 1 and "- h2" in s3_ and "- h1" not in s3_, s3_)
        M.move11(md); s4_ = open(md, encoding="utf-8").read()
        M.move11(md); s5_ = open(md, encoding="utf-8").read()
        chk("F10 sec11 搬到檔尾（冪等），其他節原文不變", s4_ == s5_ and s4_.endswith("\n".join(L11) + "\n")
            and re.sub(M.SEC11_RE, "", s4_, flags=re.S).rstrip("\n") == re.sub(M.SEC11_RE, "", s3_, flags=re.S).rstrip("\n")
            and s4_.index("## 十、") < s4_.index(M.SEC11_TITLE), s4_)
        M.put11(md, []); s6_ = open(md, encoding="utf-8").read()
        chk("F10 沒有要報 ⇒ 舊第十一節拿掉", M.SEC11_TITLE not in s6_ and s6_.rstrip("\n") == re.sub(M.SEC11_RE, "", s4_, flags=re.S).rstrip("\n"))
        # ── F11 升降單位與限價（買往下、賣往上；股票／ETF 級距）
        from decimal import Decimal as Dm
        LP = M.limit_px
        cases = [(46.13, "買", False, "49.35"), (46.8, "買", False, "50"), (47.0, "買", True, "50.25"), (52.6, "賣", False, "50"),
                 (105.2, "賣", False, "100"), (950.0, "買", False, "1015"), (1060.0, "賣", False, "1010"), (9.5, "買", False, "10.15"),
                 (108.15, "買", True, "115.7"), (30.0, "賣", True, "28.5"), (46.0, "賣", True, "43.7")]
        bad = [(c, s, e, w, M.fmt_px(LP(c, s, e))) for c, s, e, w in cases if M.fmt_px(LP(c, s, e)) != w]
        chk("F11 限價範例（含級距交界、ETF）", not bad, bad)
        rng = np.random.default_rng(7); bad = []
        for x in np.r_[rng.uniform(1, 2000, 3000), [9.99, 10, 49.99, 50, 99.9, 100, 499.5, 500, 999, 1000]]:
            for side, e in (("買", False), ("賣", False), ("買", True), ("賣", True)):
                p = LP(float(x), side, e); q = Dm(repr(float(x))) * Dm("1.07" if side == "買" else "0.95"); t = M.tick(p, e)
                ok = (p % t == 0) and ((p <= q and p + M.tick(p + t, e) > q) if side == "買" else (p >= q and p - M.tick(p - t, e) < q))
                if not ok:
                    bad.append((float(x), side, e, str(p)))
        chk("F11 隨機 12,040 例：合法升降單位、買＝≤ 收盤×1.07 的最大合法價、賣＝≥ 收盤×0.95 的最小合法價", not bad, bad[:5])
        # ── F12～F14 第十四節：事件夜／加碼線夜／漲回夜
        st20 = {"說明": "x", "大跌4檔": 20000, "大跌加碼_高10": 20000, "大跌加碼_0050": 20000}
        setup(tmp, cal, pt, idx, USR, setting=st20)
        pd.DataFrame({"候選": ["A", "F9top4", "F9top4", "F8top4"], "代號": ["0050", "3008", "2317", "2330"], "名稱": ["元大台灣50", "大立光", "鴻海", "台積電"],
                      "備註": ["", "", "", ""]}).to_csv(os.path.join(RM.FWD, f"candidates_{ds(0).replace('-', '')}.csv"), index=False, encoding="utf-8-sig")
        F.set("3008", 2000.0, 0.0)
        M.disp_set = lambda DATA, day: {"2317"}
        ADDe, _ = M.add_daily(ds(0), a.sha, J, write=True)
        erows = ADDe["_rows"]
        L12 = M.orders_daily(ds(0), a.sha, J, [], erows)
        cl = {s: F.px(s)[1][pt] for s in ("3008", "2317", "2330", "2454", "0050")}
        exp, gross = [], 0.0
        for s, g in (("3008", "大跌4檔"), ("2317", "大跌4檔"), ("2330", "高10 每檔加碼"), ("2454", "高10 每檔加碼"), ("0050", "0050 加碼（六四）")):
            sh = int(np.floor(20000 / cl[s] + 1e-9)); lp = LP(cl[s], "買", s.startswith("00")); gross += sh * float(lp)
            exp.append((s, sh, M.fmt_px(lp), g))
        rows12 = [x for x in L12 if x.startswith("- 【下單】買｜")]
        okrows = len(rows12) == 5 and all(f"買｜{s} " in r and f"｜{sh} 股｜限價 {lp}｜{g}" in r for (s, sh, lp, g), r in zip(exp, rows12))
        tot = int(np.ceil(gross * 1.001425 - 1e-9))
        chk("F12 事件夜清單：4 檔（候選 F9）＋高10 每檔＋0050，股數＝每份÷收盤、限價、順序", L12[0].startswith(f"- 【下單】⭐ {ds(1)} 開盤買") and okrows, L12)
        chk("F12 交割戶 ＝ ceil(Σ股數×限價×1.001425)、只有買清單有", L12[-1] == f"- 【下單】交割戶要有 {tot:,} 元（股數×限價 {gross:,.0f} ＋ 手續費 0.1425%）｜T+2 扣款 {cal[pt + 3].month}/{cal[pt + 3].day}", (tot, L12[-1]))
        chk("F12 處置股加註", "2317 鴻海" in rows12[1] and rows12[1].endswith(M.DISP_NOTE) and not rows12[0].endswith(M.DISP_NOTE))
        chk("F12 非事件夜不產第十四節", M.orders_daily(ds(1), a.sha, {"狀態": "非事件"}, [], []) == [] and M.sec14_lines([]) == [])
        # 加碼線夜：positions 有 F9 持有中 2 檔（一檔已出場不列）
        RM.fwd_append_positions([{"序號": 1, "事件日": ds(0), "候選": "F9top4", "代號": s, "名稱": n, "買進日": ds(1), "買進價": 1, "狀態": st_}
                                 for s, n, st_ in (("3008", "大立光", "持有中"), ("2317", "鴻海", "持有中"), ("1101", "台泥", "已出場"))])
        Radd = {"序號": "1", "事件日": ds(0), "狀態": "持有中", "加碼日": ds(2), "加碼線": 91.2, "收復日": None, "收復目標": 100.0}
        L13 = M.orders_daily(ds(2), a.sha, {"狀態": "非事件"}, [Radd], [])
        r13 = [x for x in L13 if x.startswith("- 【下單】買｜")]
        cl2 = {s: F.px(s)[1][pt + 2] for s in ("3008", "2317")}
        chk("F13 加碼線夜：F9 持有中每檔再一份（照加碼日收盤）、不列已出場", len(r13) == 2 and "1101" not in "".join(L13)
            and f"｜{int(np.floor(20000 / cl2['3008'] + 1e-9))} 股｜限價 {M.fmt_px(LP(cl2['3008'], '買', False))}｜大跌4檔 −5% 加碼" in r13[0]
            and L13[-1].startswith("- 【下單】交割戶要有"), L13)
        # 漲回夜：ds(5)；4 檔股數 ＝ 事件日 ＋ 加碼日 兩份；加碼列：2454 先照高10 到期賣掉 ⇒ 不列
        M.add_daily(ds(1), a.sha, {"狀態": "非事件"}, write=True); M.add_daily(ds(3), a.sha, {"狀態": "非事件"}, write=True)
        Rrec = {"序號": "1", "事件日": ds(0), "狀態": "持有中", "加碼日": ds(2), "加碼線": 91.2, "收復日": ds(5), "收復目標": 100.0}
        L14 = M.orders_daily(ds(5), a.sha, {"狀態": "非事件"}, [Rrec], [])
        r14 = [x for x in L14 if x.startswith("- 【下單】賣｜")]
        A14 = {r["代號"]: r for r in M.read_rows(M.ADD_FN)}
        sh3008 = int(np.floor(20000 / F.px("3008")[1][pt] + 1e-9)) + int(np.floor(20000 / F.px("3008")[1][pt + 2] + 1e-9))
        c5 = F.px("3008")[1][pt + 5]
        chk("F14 漲回夜賣清單：4 檔（含 −5% 加碼股數）＋高10 加碼（2330）＋0050 加碼；已到期賣的 2454 不列；限價＝收盤×0.95 往上",
            [x.split("｜")[1].split(" ")[0] for x in r14] == ["3008", "2317", "2330", "0050"]
            and f"｜{sh3008} 股｜限價 {M.fmt_px(LP(c5, '賣', False))}｜大跌4檔" in r14[0]
            and f"｜{A14['2330']['參考股數']} 股｜" in r14[2] and f"｜{A14['0050']['參考股數']} 股｜" in r14[3]
            and A14["2454"]["狀態"] == "已出場" and "含 −5% 加碼" in L14[0], L14)
        chk("F14 賣清單標頭行尾「｜T+2 入帳 M/D」（9/23 成交跨中秋、週末、教師節 ⇒ 9/29）", L14[0].endswith("｜T+2 入帳 9/29") and str(cal[pt + 8].date()) == "2026-09-29", L14[0])
        chk("F14 賣清單沒有交割戶列、處置股賣出註記", not any("交割戶" in x for x in L14) and r14[1].endswith(M.DISP_NOTE_SELL), L14)
        # ── F15 ⚠⚠ 守門
        md = os.path.join(tmp, "guard.md")
        base_md = "# 每日名單 2026-09-15\n\n## 一、營量\n\n- a\n"
        open(md, "w", encoding="utf-8").write(base_md)
        M.put_section(md, [M.SEC_TITLE, "", "- x", ""])
        fl = M.need_flags(ds(0), a.sha, J)
        rc1 = M.guard_md(md, fl); s1_ = open(md, encoding="utf-8").read()
        rc2 = M.guard_md(md, fl); s2_ = open(md, encoding="utf-8").read()
        chk("F15 事件夜缺第十一、十四節 ⇒ 標題下 ⚠⚠、exit 3、冪等", fl == {"大跌事件夜": ("八", "十一", "十四")} and rc1 == 3 and rc2 == 3 and s1_ == s2_
            and s1_.split("\n")[2].startswith("⚠⚠ 大盤大跌：今晚是大跌事件夜，但第十一、十四節沒產出") and s1_.count("⚠⚠") == 1, s1_[:400])
        open(md, "w", encoding="utf-8").write(base_md); M.put_section(md, [M.SEC_TITLE, "", "- x", ""])
        M.put11(md, M.sec11_lines(ADDe["top"])); M.put_sec(md, M.SEC14_TITLE, M.sec14_lines(L12))
        chk("F15 三節都在 ⇒ exit 0、檔案不動", M.guard_md(md, fl) == 0 and "⚠⚠" not in open(md, encoding="utf-8").read())
        M.put_sec(md, M.SEC14_TITLE, M.sec14_lines(["- ⚠ 下單清單產生失敗（見 log）：X"]))
        chk("F15 第十四節只剩 ⚠ 行（沒有【下單】⭐）也算沒產出", M.guard_md(md, fl) == 3 and "第十四節沒產出" in open(md, encoding="utf-8").read())
        chk("F15 平常夜（無事件／加碼線／漲回）⇒ 不需要任何節", M.need_flags(ds(1), a.sha, {"狀態": "非事件"}) == {})
        M.fwd_update("events.csv", RM.FWD_EV_COLS, {"序號": 1, "事件日": ds(0)}, {"買進日": ds(1), "狀態": "持有中"})
        flr = M.need_flags(ds(5), a.sha, {"狀態": "非事件"})
        _, df0 = RM.read_index(); df2 = df0.copy(); df2.loc[df2["date"] == cal[pt + 2], "close"] = 91.0
        RM.read_index = lambda sha=None: (sha, df2)
        fla = M.need_flags(ds(2), a.sha, {"狀態": "非事件"})
        RM.read_index = lambda sha=None: (sha, df0)
        chk("F15 漲回夜（有大跌加碼持有中）要八、十一、十四；加碼線夜要八、十四", list(flr.values()) == [("八", "十一", "十四")] and "漲回" in list(flr)[0]
            and list(fla.values()) == [("八", "十四")], (flr, fla))
        open(md, "w", encoding="utf-8").write(base_md)
        chk("F15 判不出（未知）⇒ ⚠⚠「判不出」", M.guard_md(md, {"未知": "X"}, crash="RuntimeError: y") == 3 and "判不出" in open(md, encoding="utf-8").read())
        # daily 整合：事件夜第十四節產生失敗 ⇒ ⚠⚠＋非 0；正常 ⇒ 0
        import types
        jr = RM.fwd_judge_and_record
        RM.fwd_judge_and_record = lambda d, w: dict(J)
        setup(tmp, cal, pt, idx, USR, setting=st20)
        pd.DataFrame({"候選": ["F9top4", "F9top4"], "代號": ["3008", "2317"], "名稱": ["大立光", "鴻海"], "備註": ["", ""]}).to_csv(
            os.path.join(RM.FWD, f"candidates_{ds(0).replace('-', '')}.csv"), index=False, encoding="utf-8-sig")
        ns = types.SimpleNamespace(fwd=RM.FWD, asof=ds(0), sha=a.sha, md=md, nowrite=False, preview_addon=False, preview_orders=None, preview_seq=None,
                                   preview_cands=None, fsha=None)
        open(md, "w", encoding="utf-8").write(base_md)
        rc_ok = M.daily(ns); s_ok = open(md, encoding="utf-8").read()
        od = M.orders_daily
        M.orders_daily = lambda *a_, **k_: (_ for _ in ()).throw(RuntimeError("模擬失敗"))
        setup(tmp, cal, pt, idx, USR, setting=st20)
        pd.DataFrame({"候選": ["F9top4"], "代號": ["3008"], "名稱": ["大立光"], "備註": [""]}).to_csv(
            os.path.join(RM.FWD, f"candidates_{ds(0).replace('-', '')}.csv"), index=False, encoding="utf-8-sig")
        open(md, "w", encoding="utf-8").write(base_md)
        ns.fwd = RM.FWD
        rc_bad = M.daily(ns); s_bad = open(md, encoding="utf-8").read()
        M.orders_daily = od; RM.fwd_judge_and_record = jr
        chk("F15 daily 整合：事件夜正常 ⇒ 0、第八／十一／十四節都在、無 ⚠⚠", rc_ok == 0 and M.SEC_TITLE in s_ok and M.SEC11_TITLE in s_ok and M.SEC14_TITLE in s_ok
            and "⚠⚠" not in s_ok and "- 【下單】買｜3008 大立光" in s_ok, s_ok[-800:])
        chk("F15 daily 整合：下單清單失敗 ⇒ ⚠⚠ 在標題下、exit 3", rc_bad == 3 and s_bad.split("\n")[2].startswith("⚠⚠") and "第十四節沒產出" in s_bad, s_bad[:300])
        # ── F16 休市表缺 ⇒ 只扣週末外推＋⚠（不中止）
        M.HOL_WARN.clear()
        nd_real = M._next_day(cal, len(cal) - 1, DATA)
        from backtest import gate_b_status as GB
        D.DATA = DATA
        chk("F16 休市表在 ⇒ 同 gate_b_status 外推", nd_real == GB.future_trading_days(cal, 1, fixed_holidays_uncovered=True)[0][0] and not M.HOL_WARN)
        nod = os.path.join(tmp, "nodata"); os.makedirs(os.path.join(nod, "meta"), exist_ok=True)
        nd_fb = M._next_day(cal, len(cal) - 1, nod)
        exp_fb = cal[-1] + pd.Timedelta(days=1)
        while exp_fb.weekday() >= 5:
            exp_fb += pd.Timedelta(days=1)
        chk("F16 休市表缺 ⇒ 只扣週末、HOL_WARN 一行、第十一／十四節帶 ⚠", nd_fb == exp_fb and len(M.HOL_WARN) == 1 and "休市表不在" in M.HOL_WARN[0]
            and M.sec14_lines(["x"])[-1].startswith("- ⚠ 休市表不在"), M.HOL_WARN)
        M.HOL_WARN.clear(); D.DATA = DATA
        # ── F17 user-add
        setup(tmp, cal, pt, idx, USR, setting=st20)
        r17 = M.user_add(1, "2330", ds(1), 1020.0, "19", "買", "大跌4檔", a.sha, note="t")
        o17 = F.px("2330")[0][pt + 1]
        R17 = M.read_rows(M.FILL_FN)
        dup = False
        try:
            M.user_add(1, "2330", ds(1), 1020.0, "19", "買", "大跌4檔", a.sha)
        except SystemExit:
            dup = True
        chk("F17 user-add：整股開盤價＝成交日未還原開盤、差＝零股÷整股開盤−1、重複拒絕",
            len(R17) == 1 and abs(float(R17[0]["整股開盤價"]) - o17) < 1e-9 and abs(float(R17[0]["零股÷整股開盤−1"]) - (1020.0 / o17 - 1)) < 1e-12 and dup, R17)
        # ── F18 reorder（再出）
        open(md, "w", encoding="utf-8").write(base_md); M.put_sec(md, M.SEC14_TITLE, M.sec14_lines(L12))
        b1 = M.reorder(ds(1), a.sha, "買", ["3008", "2317"], "大跌4檔", md=md); s18a = open(md, encoding="utf-8").read()
        M.reorder(ds(1), a.sha, "買", ["3008", "2317"], "大跌4檔", md=md); s18b = open(md, encoding="utf-8").read()
        cl18 = F.px("3008")[1][pt + 1]
        nerr = False
        try:
            M.reorder(ds(1), a.sha, "賣", ["3008"], "大跌4檔")
        except SystemExit:
            nerr = True
        chk("F18 reorder：照新收盤重算、標「再出」、併進第十四節且重跑冪等、原清單保留；賣沒給股數 ⇒ 拒絕",
            b1[0].endswith("再出：前一天沒成交") and f"3008 大立光｜{int(np.floor(20000 / cl18 + 1e-9))} 股｜限價 {M.fmt_px(LP(cl18, '買', False))}" in b1[1]
            and s18a == s18b and s18a.count("再出：前一天沒成交") == 1 and L12[0] in s18a and nerr, s18a[-600:])
        # ── F20 T+2（seq458 §五、情報 0041）：跨週末、跨 10/26 休市、春節前「僅辦理結算交割」日、休市表缺
        SD = lambda d_, n_=2, dd_=DATA: M.settle_day(cal, pd.Timestamp(d_), n_, dd_)   # noqa: E731
        TS = pd.Timestamp
        chk("F20 10/23 下單 ⇒ 10/27 成交（10/26 補假休市）⇒ T+2 ＝ 10/29", SD("2026-10-23", 1) == TS("2026-10-27") and SD("2026-10-27") == TS("2026-10-29"),
            (SD("2026-10-23", 1), SD("2026-10-27")))
        chk("F20 跨週末：9/17（四）成交 ⇒ T+2 ＝ 9/21（一）；9/23 成交跨中秋＋週末＋教師節 ⇒ 9/29",
            SD("2026-09-17") == TS("2026-09-21") and SD("2026-09-23") == TS("2026-09-29"))
        chk("F20 春節前「市場無交易，僅辦理結算交割作業」照算交割日：2/10 成交 ⇒ 2/12、2/11 成交 ⇒ 2/13",
            SD("2026-02-10") == TS("2026-02-12") and SD("2026-02-11") == TS("2026-02-13") and TS("2026-02-12") not in cal)
        chk("F20 跨年未公告年度：12/30 成交 ⇒ T+2 跳過 1/1（固定國定假日）", SD("2026-12-30") == TS("2027-01-04"), SD("2026-12-30"))
        M.HOL_WARN.clear()
        fb = SD("2026-10-23", 1, os.path.join(tmp, "nodata"))
        chk("F20 休市表缺 ⇒ 只扣週末（10/26 會算成交割日）＋ HOL_WARN（不中止）", fb == TS("2026-10-26") and any("T+2 只扣週末" in w for w in M.HOL_WARN), (fb, M.HOL_WARN))
        M.HOL_WARN.clear(); D.DATA = DATA
        # ── F19 sec11 子指令一併搬第十四節
        open(md, "w", encoding="utf-8").write(base_md)
        M.put11(md, M.sec11_lines(ADDe["top"])); M.put_sec(md, M.SEC14_TITLE, M.sec14_lines(L12))
        open(md, "a", encoding="utf-8").write("\n## 十、高10\n\n- h\n")
        M.move11(md); s19 = open(md, encoding="utf-8").read(); M.move11(md)
        chk("F19 sec11 子指令：第十一、十四節依序搬到檔尾（冪等）", s19 == open(md, encoding="utf-8").read()
            and s19.index("## 十、") < s19.index(M.SEC11_TITLE) < s19.index(M.SEC14_TITLE), s19[-300:])
        # ── F8 第八節回到改前逐字
        RM.FWD = os.path.join(REPO, "backtest", "forward", "mktdrop")
        RM.read_index = RM_read_index; M.one = M_one
        src_now = open(os.path.join(REPO, "backtest", "mktdrop_fwd.py"), encoding="utf-8").read()
        src_old = subprocess.run(["git", "-C", REPO, "show", "15c29eb178:backtest/mktdrop_fwd.py"], capture_output=True, text=True).stdout
        cut = lambda s_: s_[s_.index("def section("):s_.index("def put_section(")]   # noqa: E731
        chk("F8 section()／put_section() 原始碼與改前（15c29eb178）逐字相同", cut(src_now) == cut(src_old)
            and src_now[src_now.index("def put_section("):].split("\n\n\n")[0] == src_old[src_old.index("def put_section("):].split("\n\n\n")[0])
        if not a.skip_regress:
            chk(f"F8 真快照 {REG_ASOF} daily --nowrite：名單第八節與現有名單逐字相同、無第十一節、紀錄檔不變", *regress(a.sha, tmp))
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
