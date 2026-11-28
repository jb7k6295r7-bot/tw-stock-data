# -*- coding: utf-8 -*-
"""月底 M 的美股資料到了沒（直接讀 us-stock-data 的 git 物件，⛔ 不改工作樹、不建快照；只數列數、不讀價格值）。

    python data_ready.py REPO COMMIT M OUT.json
    ⇒ stdout 三行：READY（1／0）、月底（資料日曆覆核後）、原因

判準（run_c3s_month.sh 第 3 點）：
  ① 月底覆核：^GSPC（＝ world 日曆來源 us_data.load_calendar）若已有 M 所在月之後的日期 ⇒ 該月最後一個 ^GSPC 日期才是月底（規則日曆算不到的臨時休市以資料為準）。
  ② SPY（C3sF 濾網）與 ^GSPC 都要有 M 那一列。
  ③ S&P 500 現役成分：前一交易日 P 在 panel 標 in_index＝1 且 ret 非空的代號中，M 那一列也有（ret 非空）的檔數 ≥ 98%。
"""
import json
import subprocess
import sys

REPO, COMMIT, M, OUT = sys.argv[1:5]
TH = 0.98


def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, check=True).stdout


def batch(paths):
    """git cat-file --batch：一次讀多個 blob ⇒ {path: bytes}。"""
    inp = "".join(f"{COMMIT}:{p}\n" for p in paths).encode()
    out = subprocess.run(["git", "-C", REPO, "cat-file", "--batch"], input=inp, capture_output=True, check=True).stdout
    res, i = {}, 0
    for p in paths:
        j = out.index(b"\n", i); hdr = out[i:j].split()
        if len(hdr) < 3 or hdr[1] != b"blob":
            res[p] = None; i = j + 1; continue
        n = int(hdr[2]); res[p] = out[j + 1:j + 1 + n]; i = j + 1 + n + 1
    return res


def dates(b):
    return sorted({ln[:10].decode() for ln in b.splitlines()[1:] if ln[:4].isdigit()}) if b else []


rep = {"commit": COMMIT, "M_規則": M}
mac = batch(["data/macro/yahoo_SPY.csv", "data/macro/yahoo_GSPC.csv"])
spy, gspc = dates(mac["data/macro/yahoo_SPY.csv"]), dates(mac["data/macro/yahoo_GSPC.csv"])
rep["SPY最後日"], rep["GSPC最後日"] = (spy[-1] if spy else None), (gspc[-1] if gspc else None)
mon = M[:7]
Ma = M
if gspc and gspc[-1][:7] > mon:
    inmon = [d for d in gspc if d[:7] == mon]
    if inmon:
        Ma = inmon[-1]
rep["M_資料"] = Ma
why = []
if Ma not in spy:
    why.append(f"SPY 沒有 {Ma} 那一列（SPY 最後一日 {rep['SPY最後日']}）")
if Ma not in gspc:
    why.append(f"^GSPC 沒有 {Ma} 那一列（最後一日 {rep['GSPC最後日']}）")
P = max((d for d in gspc if d < Ma), default=None)
rep["前一交易日"] = P
names = [f"data/panel/{x.decode()}" for x in git("ls-tree", "--name-only", f"{COMMIT}:data/panel").split()
         if x.endswith(b".csv") and not x.startswith(b"_")]
pan = batch(names)
nP = nM = 0
kP, kM = ("\n" + (P or "X")).encode(), ("\n" + Ma).encode()


def row(b, key):
    i = b.find(key + b",")
    if i < 0:
        return None
    j = b.find(b"\n", i + 1)
    return b[i + 1:(j if j > 0 else len(b))].rstrip(b"\r").split(b",")


for p, b in pan.items():
    if not b:
        continue
    rp = row(b, kP)
    if rp is None or len(rp) < 3 or rp[2].strip() != b"1" or not rp[1].strip():
        continue
    nP += 1
    rm = row(b, kM)
    if rm is not None and len(rm) >= 2 and rm[1].strip():
        nM += 1
rep.update({"panel檔數": len(names), "前一日現役有價檔數": nP, "M有價檔數": nM, "比例": (nM / nP if nP else None), "門檻": TH})
if not nP:
    why.append(f"panel 找不到前一交易日 {P} 的現役成分")
elif nM < TH * nP:
    why.append(f"S&P 500 現役成分 {Ma} 有價 {nM}／{nP} 檔（{nM / nP:.1%}）＜ 98%")
rep["READY"] = not why
rep["原因"] = "；".join(why) if why else f"齊：SPY、^GSPC 有 {Ma}；成分 {nM}／{nP}"
json.dump(rep, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(1 if rep["READY"] else 0); print(Ma); print(rep["原因"])
