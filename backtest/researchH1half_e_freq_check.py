# -*- coding: utf-8 -*-
"""H1 先賣一半 seq1 電子＋傳產普查頻率表對帳（獨立重算觸發）——回測線計算子代理。⛔ 不算報酬、不 commit、不改既有檔。
用 researchH1half_freq_check 同一套獨立重算（原始營收 csv、market_tri 日曆、逐月迴圈；⛔ 不 import 主程式），輸出夾改 freq_e；
另依類（電子／傳產）× 情境（照實／嚴格／剔自評知道）× 甲乙彙總：主觸發 vs 獨立重算觸發、緊接版、逐筆一致。

    cd ~/tw-p17 && PYTHONPATH=~/tw-p17 ~/tw-p16/.venv/bin/python -m backtest.researchH1half_e_freq_check
"""
import json
import os

import pandas as pd

from backtest import researchH1half_freq_check as K

K.OUT = "backtest/resultsH1half/freq_e"


def main():
    K.main()
    C = pd.read_csv(os.path.join(K.OUT, "check_rows.csv"), dtype={"代號": str})
    EV = pd.read_csv(os.path.join(K.OUT, "events.csv"), dtype={"代號": str})
    EV = EV[EV["入選"].astype(str) == "True"][["訊號", "代號", "類", "兩可", "自評知道", "緊接版觸發"]]
    M = C.merge(EV, on=["訊號", "代號"], how="left", validate="one_to_one")
    out = {}
    for sc in ("照實", "嚴格", "剔自評知道"):
        for cl in ("電子", "傳產", "合計"):
            for ver in ("甲", "乙"):
                d = M[M[ver].astype(str) == "True"]
                d = d if cl == "合計" else d[d["類"] == cl]
                if sc == "嚴格":
                    d = d[d["兩可"].astype(str) != "True"]
                elif sc == "剔自評知道":
                    d = d[d["自評知道"].astype(str) != "True"]
                out[f"{sc}|{cl}|{ver}"] = {"件": len(d), "主觸發": int(d["主_觸發"].sum()), "check觸發": int(d["chk_觸發"].sum()), "逐筆一致": int(d["一致"].sum()),
                                          "主緊接": int(d["緊接版觸發"].astype(str).eq("True").sum()), "check緊接": int(d["緊接_觸發"].sum())}
    ok = all(v["件"] == v["逐筆一致"] and v["主緊接"] == v["check緊接"] for v in out.values())
    out["CHECK_分組"] = "PASS" if ok else "FAIL"
    json.dump(out, open(os.path.join(K.OUT, "check_groups.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
