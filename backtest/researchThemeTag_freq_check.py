# -*- coding: utf-8 -*-
"""researchThemeTag_freq 獨立查核（另一套寫法：csv 模組讀檔、逐代號買賣交替配對、手寫月份回推；⛔ 不 import 主檔）。⛔ 不讀報酬欄。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchThemeTag_freq_check
C1 進場重建：主世界 帳 YL／v1 的 buy／sell 依代號排序後必須 買、賣 交替；配對、持有狀態、期間篩選 ＝ entries.csv 逐列相同
C2 普查標籤重算（寬／嚴、對到的訊號）＝ entries.csv 逐列相同；甲／乙參考欄同
C3 彙總 ＝ freq.json、year.csv、month.csv、neff.csv、draw.csv
C4 邊界 fixture：月份回推（閏日、月底）、同日消息不算、恰 24 個月前算；突變：窗改成含進場日／改 23、25 個月 ⇒ 只報筆數變化
C5 entries.csv 不含任何報酬欄；前瞻第 1 期 sha16 與 42 家
輸出 backtest/resultsThemeTag/freq/check.json、check.log
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import os
import re
import sys
from collections import defaultdict

REPO = os.path.expanduser("~/tw-p17")
OUT = os.path.join(REPO, "backtest", "resultsThemeTag", "freq")
YFA = os.path.join(REPO, "backtest", "resultsYFallin")
MB = "/mnt/c/SynologyDrive/跨線信箱"
V4 = os.path.join(MB, "附件-近年燈號普查訊號清單v4_加判定把握_產業分析線-20261025-1830.csv")
V5 = os.path.join(MB, "附件-電子類燈號普查訊號清單v5_產業分析線-20261026-0130.csv")
FWD = os.path.join(MB, "附件-前沿研究前瞻紀錄第1期_產業分析線-20261026-0206.md")
LOG, BAD = [], []


def log(s):
    LOG.append(s); print(s, flush=True)


def ok(name, cond, extra=""):
    log(f"[{'過' if cond else '✖'}] {name} {extra}")
    if not cond:
        BAD.append(name)


def rgz(p):
    with gzip.open(p, "rt", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def back_months(d, n):
    y, m, dd = int(d[:4]), int(d[5:7]), int(d[8:10])
    tot = y * 12 + (m - 1) - n
    y2, m2 = divmod(tot, 12); m2 += 1
    mdays = [31, 29 if (y2 % 4 == 0 and (y2 % 100 != 0 or y2 % 400 == 0)) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m2 - 1]
    return f"{y2:04d}-{m2:02d}-{min(dd, mdays):02d}"


def in_win(d1, d, n=24, incl=False):
    return back_months(d, n) <= d1 and (d1 <= d if incl else d1 < d)


def main():
    # ── C4 fixture（先跑，與資料無關）
    ok("C4 回推 2024-02-29 −24 月 ＝ 2022-02-28", back_months("2024-02-29", 24) == "2022-02-28")
    ok("C4 回推 2026-03-31 −24 月 ＝ 2024-03-31", back_months("2026-03-31", 24) == "2024-03-31")
    ok("C4 回推 2025-05-31 −23 月 ＝ 2023-06-30", back_months("2025-05-31", 23) == "2023-06-30")
    ok("C4 同日消息不算", not in_win("2023-05-02", "2023-05-02"))
    ok("C4 恰 24 個月前算", in_win("2021-05-02", "2023-05-02"))
    ok("C4 24 個月前一天不算", not in_win("2021-05-01", "2023-05-02"))

    # ── C1 進場
    cal = {}
    for r in rgz(os.path.join(YFA, "daily_W.csv.gz")):
        if r["世界"] == "主" and r["帳"] == "YL":
            cal[int(r["t"])] = r["日期"] or ""
    last = max(t for t, d in cal.items() if d)
    tr = [r for r in rgz(os.path.join(YFA, "trades_W.csv.gz")) if r["世界"] == "主"]
    ents = []
    for st, acct in (("營量", "YL"), ("營飆", "v1")):
        ev = defaultdict(list)
        for r in tr:
            if r["帳"] == acct:
                ev[int(r["sid"])].append((int(r["t"]), 0 if r["side"] == "sell" else 1, r["side"], r["xpos"]))
        for sid, lst in ev.items():
            lst.sort()                                    # 同 t：先賣（舊部位）後買
            assert [x[2] for x in lst] == ["buy", "sell"] * (len(lst) // 2), (st, sid)
            for i in range(0, len(lst), 2):
                tb, _, _, xp = lst[i]; ts = lst[i + 1][0]; xp = int(float(xp))
                d = cal[tb]
                if not ("2021-01-01" <= d <= "2026-10-31"):
                    continue
                stt = "未滿" if (cal.get(ts, "") == "" or xp > last) else ("完整" if ts == xp else "提前")
                ents.append((st, f"{sid:04d}", tb, d, ts, stt))
    with open(os.path.join(OUT, "entries.csv"), encoding="utf-8") as f:
        E = list(csv.DictReader(f))
    mine = sorted(ents)
    theirs = sorted((r["策略"], r["代號"], int(r["進場t"]), r["進場日"], int(r["出場t"]), r["持有狀態"]) for r in E)
    ok("C1 進場重建逐列相同", mine == theirs, f"（本檔 {len(mine)}／主檔 {len(theirs)}）")

    # ── C2 普查標籤
    sigs = []
    for tag, p in (("v4", V4), ("v5", V5)):
        with open(p, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                know = (r.get("判燈者自評知道後來走勢") or "").strip()
                strict = r["判定把握"].strip() == "確定" and know != "知道"
                for c in ("公司1", "公司2", "公司3"):
                    m = re.match(r"^(\d{4})\s", (r[c] or "").strip())
                    if m:
                        sigs.append((m.group(1), r["燈1出處日期"].strip(), strict, tag, r["訊號編號"], r["產業"].strip(), r["主題"].strip(),
                                     r["版本(甲/乙/兩版)"].strip()))
    nbad = 0; nver = 0
    for r in E:
        for v in ("寬", "嚴"):
            hit = sorted({f"{s[3]}:{s[4]}|{s[5]}／{s[6]}" for s in sigs if s[0] == r["代號"] and (v == "寬" or s[2]) and in_win(s[1], r["進場日"])})
            if (r[f"標籤_{v}"] == "True") != bool(hit) or ";".join(hit) != (r[f"對到_{v}"] or ""):
                nbad += 1
            for ver, keep in (("甲", ("甲", "兩版")), ("乙", ("乙", "兩版"))):
                h2 = any(s[0] == r["代號"] and (v == "寬" or s[2]) and s[7] in keep and in_win(s[1], r["進場日"]) for s in sigs)
                if (r[f"參考_{ver}版_{v}"] == "True") != h2:
                    nver += 1
    ok("C2 寬／嚴標籤與對到訊號逐列相同", nbad == 0, f"（不符 {nbad}）")
    ok("C2 甲／乙參考欄逐列相同", nver == 0, f"（不符 {nver}）")

    # ── C3 彙總
    J = json.load(open(os.path.join(OUT, "freq.json"), encoding="utf-8"))
    YR = list(csv.DictReader(open(os.path.join(OUT, "year.csv"), encoding="utf-8")))
    MO = list(csv.DictReader(open(os.path.join(OUT, "month.csv"), encoding="utf-8")))
    NE = list(csv.DictReader(open(os.path.join(OUT, "neff.csv"), encoding="utf-8")))
    DR = list(csv.DictReader(open(os.path.join(OUT, "draw.csv"), encoding="utf-8")))
    tot = {}
    for st in ("營量", "營飆"):
        es = [r for r in E if r["策略"] == st]
        ei = [r for r in es if r["持有狀態"] != "未滿"]
        good = J["策略"][st]["進場筆數"] == len(es) and J["策略"][st]["未滿"] == len(es) - len(ei)
        for v in ("寬", "嚴"):
            th = [r for r in ei if r[f"標籤_{v}"] == "True"]
            ta = [r for r in es if r[f"標籤_{v}"] == "True"]
            x = J["策略"][st][v]
            months = {r["進場日"][:7] for r in th}
            themes = {z.split("|", 1)[1] for r in th for z in r[f"對到_{v}"].split(";") if z}
            good &= (x["主題組_全部"] == len(ta) and x["主題組_入統計"] == len(th) and x["月群"] == len(months) and x["主題群"] == len(themes)
                     and x["不同代號"] == len({r["代號"] for r in th}) and x["達30筆"] == (len(th) >= 30))
            ne = [r for r in NE if r["策略"] == st and r["版"] == v][0]
            good &= int(ne["主題組_入統計"]) == len(th) and int(ne["月群"]) == len(months)
            byy = defaultdict(lambda: [0, 0]); bym = defaultdict(lambda: [0, 0, 0, 0])
            for r in es:
                y = r["進場日"][:4]; m = r["進場日"][:7]; t_ = r[f"標籤_{v}"] == "True"; i_ = r["持有狀態"] != "未滿"
                byy[y][0] += 1; byy[y][1] += t_
                bym[m][0] += 1; bym[m][1] += t_; bym[m][2] += i_; bym[m][3] += (t_ and i_)
            for r in YR:
                if r["策略"] == st and r["版"] == v:
                    good &= [int(r["全部"]), int(r["主題組"])] == byy[r["年"]]
            mo = [r for r in MO if r["策略"] == st and r["版"] == v]
            good &= len(mo) == len(bym)
            for r in mo:
                good &= [int(r["全部"]), int(r["主題組"]), int(r["入統計_全部"]), int(r["入統計_主題組"])] == bym[r["月"]]
            deg = sum(1 for m, a in bym.items() if a[3] > 0 and a[3] == a[2])
            dr = [r for r in DR if r["策略"] == st and r["版"] == v][0]
            good &= int(dr["k＝n 月數（隨機組必＝主題組）"]) == deg and int(dr["主題組有筆月數"]) == sum(1 for a in bym.values() if a[3] > 0)
            tot[f"{st}_{v}"] = (len(th), len(ei))
        ok(f"C3 {st} 彙總（總表、年、月、n_eff、可抽性）", bool(good))

    # ── C4 突變：窗口徑改變 ⇒ 主題筆數（入統計）變化，只報
    for lab, n, incl in (("含進場日", 24, True), ("23 個月", 23, False), ("25 個月", 25, False)):
        s_ = []
        for st in ("營量", "營飆"):
            for v in ("寬", "嚴"):
                k = sum(1 for r in E if r["策略"] == st and r["持有狀態"] != "未滿" and
                        any(s[0] == r["代號"] and (v == "寬" or s[2]) and in_win(s[1], r["進場日"], n, incl) for s in sigs))
                s_.append(f"{st}{v} {k}（原 {tot[f'{st}_{v}'][0]}）")
        log(f"[突變・只報] {lab}：" + "、".join(s_))

    # ── C5
    cols = set(E[0].keys())
    ok("C5 entries.csv 無報酬欄", not (cols & {"amt", "amt_out", "cost", "px", "R", "超額", "報酬"}), f"欄 {sorted(cols)}")
    h = hashlib.sha256(open(FWD, "rb").read()).hexdigest()[:16]
    sec = open(FWD, encoding="utf-8").read().split("## 二、")[1].split("## 三、")[0]
    codes = set()
    for ln in sec.splitlines():
        if ln.startswith("| ") and "---" not in ln and "| 組 |" not in ln:
            comp = ln.split("|")[3]
            comp = re.sub(r"（.*?）", "", comp)
            codes.update(re.findall(r"\b(\d{4})\b", comp))
    ok("C5 前瞻第1期 sha16＝30e87e3eb701136f、42 家", h == "30e87e3eb701136f" and len(codes) == 42 and J["前瞻第1期代號數"] == 42, f"（{h}、{len(codes)}）")
    res = {"不過": BAD, "全過": not BAD}
    json.dump(res, open(os.path.join(OUT, "check.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(os.path.join(OUT, "check.log"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
    log(f"== 查核 {'全過' if not BAD else '有不過：' + '、'.join(BAD)}")
    return 1 if BAD else 0


if __name__ == "__main__":
    sys.exit(main())
