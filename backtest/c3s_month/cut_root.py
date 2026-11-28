# -*- coding: utf-8 -*-
"""從唯讀快照 SRC 複製一份 DST，凡第一欄是 date 的 CSV 只留 date <= CUT 的列（表頭保留）。
（＝ ~/us_work/c/c3s/ops/b1030/cut_root.py 同一做法；只把 CUT.txt 說明改成參數。）
只印計數、不印任何價格。另列：非 date 首欄的 CSV 中含 CUT 之後日期字串的檔（只報檔名與次數）。

    python cut_root.py SRC DST CUT [說明]
"""
import os, re, shutil, sys, json

SRC, DST, CUT = sys.argv[1], sys.argv[2], sys.argv[3]
NOTE = sys.argv[4] if len(sys.argv) > 4 else "回測線 C3s 月底換股單（run_c3s_month.sh）用"
assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", CUT), CUT
assert not os.path.exists(DST), DST
tmp = DST + ".tmp"
if os.path.exists(tmp):                     # 上次中斷留下的半成品
    for dp, dn, fn in os.walk(tmp):
        os.chmod(dp, 0o755)
    shutil.rmtree(tmp)
shutil.copytree(SRC, tmp, copy_function=shutil.copy2)
for dp, dn, fn in os.walk(tmp):
    os.chmod(dp, 0o755)
    for f in fn:
        os.chmod(os.path.join(dp, f), 0o644)
dre = re.compile(r"^\d{4}-\d{2}-\d{2}")
later = re.compile(r"(20\d{2})-(\d{2})-(\d{2})")
st = {"csv": 0, "date首欄": 0, "有截": 0, "刪列": 0, "剩最大日期": "", "非date首欄含CUT後日期": {}}
for dp, dn, fn in os.walk(os.path.join(tmp, "data")):
    for f in fn:
        if not f.endswith(".csv"):
            continue
        p = os.path.join(dp, f); st["csv"] += 1
        with open(p, encoding="utf-8", newline="") as fh:
            lines = fh.read().splitlines(keepends=True)
        if not lines:
            continue
        h = lines[0].lstrip("﻿").strip().split(",")[0].strip().lower()
        if h == "date":
            st["date首欄"] += 1
            keep = [lines[0]]; drop = 0
            for ln in lines[1:]:
                if dre.match(ln) and ln[:10] > CUT:
                    drop += 1; continue
                keep.append(ln)
                if dre.match(ln) and ln[:10] > st["剩最大日期"]:
                    st["剩最大日期"] = ln[:10]
            if drop:
                st["有截"] += 1; st["刪列"] += drop
                with open(p, "w", encoding="utf-8", newline="") as fh:
                    fh.writelines(keep)
        else:
            k = sum(1 for ln in lines[1:] for m in later.finditer(ln) if m.group(0) > CUT)
            if k:
                st["非date首欄含CUT後日期"][os.path.relpath(p, tmp)] = k
with open(os.path.join(tmp, "CUT.txt"), "w", encoding="utf-8") as fh:
    fh.write(f"由 {SRC} 複製；第一欄 date 的 CSV 只留 date <= {CUT}（{NOTE}）\n")
for dp, dn, fn in os.walk(tmp):
    for f in fn:
        os.chmod(os.path.join(dp, f), 0o444)
os.rename(tmp, DST)
for dp, dn, fn in os.walk(DST):
    os.chmod(dp, 0o555)
print(json.dumps(st, ensure_ascii=False, indent=1))
