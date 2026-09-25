# -*- coding: utf-8 -*-
"""PREREG出場訊號 硬性查核①：從逐筆檔獨立重算 6 格判定量與 CI（⛔ 不 import researchExit／exit_signal／research11 任何一行）。

只讀：backtest/resultsExit/events_kept.csv.gz（逐筆）、summary.json（被比的一方）、快照的交易日曆（算 60 日區段號）。
重算：R ＝ P_end ÷ P_s − 1（逐筆）、E、CR0 分群 SE（純 Python 字典累加）、95% CI、n_eff、出口、結果；與 summary.json 逐格比。
"""
import os, json, gzip, csv, math

SHA = "edc6f8002fed8803795e3486ad57db513f7e9f65"
CAL = os.path.expanduser("~/h2data/{}/data/meta/calendar_twse.csv".format(SHA))
OUT = os.path.expanduser("~/tw-p17/backtest/resultsExit")


def main():
    cal = [r["date"] for r in csv.DictReader(open(CAL, encoding="utf-8"))]
    cal = sorted(cal); pos = {d: i for i, d in enumerate(cal)}
    w0 = pos["2017-03-02"]
    rows = list(csv.DictReader(gzip.open(os.path.join(OUT, "events_kept.csv.gz"), "rt", encoding="utf-8")))
    S = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))["判定6格"]
    out = {}; worst_R = 0.0; bad = []
    for g in ("甲", "乙", "丙"):
        for H in (20, 60):
            xs = []; gs = []
            for r in rows:
                if r["rule"] != "close" or r["g"] != g or int(r["H"]) != H:
                    continue
                R = float(r["P_end"]) / float(r["P_s"]) - 1.0
                worst_R = max(worst_R, abs(R - float(r["R"])))
                xs.append(R)
                gs.append(r["T_date"][:7] if H == 20 else (pos[r["T_date"]] - w0) // 60)
            n = len(xs); m = sum(xs) / n
            acc = {}
            for x, k in zip(xs, gs):
                acc[k] = acc.get(k, 0.0) + (x - m)
            se = math.sqrt(sum(v * v for v in acc.values())) / n
            lo, hi = m - 1.96 * se, m + 1.96 * se
            ne = min(n, len(acc))
            if ne < 30:
                ex, rs = "出口①", "—（樣本不足以分辨）"
            else:
                ex = "出口②" if ne < 100 else "出口③"
                rs = "結果①" if lo <= 0 <= hi else ("結果③" if m < 0 else "結果②")
            J = S["{}_H{}".format(g, H)]
            d = {"n": n, "E": m, "lo": lo, "hi": hi, "n_eff": ne, "出口": ex, "結果": rs,
                 "E差": abs(m - J["E"]), "lo差": abs(lo - J["lo"]), "hi差": abs(hi - J["hi"]),
                 "n同": n == J["n"], "n_eff同": ne == J["n_eff"], "出口同": ex == J["出口"], "結果同": rs == J["結果"]}
            ok = d["n同"] and d["n_eff同"] and d["出口同"] and d["結果同"] and max(d["E差"], d["lo差"], d["hi差"]) < 1e-12
            d["判"] = "✅" if ok else "⛔"
            if not ok:
                bad.append("{}_H{}".format(g, H))
            out["{}_H{}".format(g, H)] = d
            print("{}_H{}：n {:,}｜E {:+.4f}%｜CI {:+.4f} ～ {:+.4f}%｜n_eff {}｜{} {}｜與本體差 E {:.1e} lo {:.1e} hi {:.1e}｜{}".format(
                g, H, n, m * 100, lo * 100, hi * 100, ne, ex, rs, d["E差"], d["lo差"], d["hi差"], d["判"]))
    res = {"逐筆R重算最大差": worst_R, "格": out, "不一致的格": bad, "判": "✅ 6 格全同" if not bad and worst_R < 1e-12 else "⛔"}
    json.dump(res, open(os.path.join(OUT, "check_recompute.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("逐筆 R 重算最大差 {:.1e}｜{}".format(worst_R, res["判"]))


if __name__ == "__main__":
    main()
