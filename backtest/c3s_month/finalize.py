# -*- coding: utf-8 -*-
"""驗算判定＋收尾（⛔ 不寫 repo、不寫信箱；只寫 --stage/final/，複製由 run_c3s_month.sh 做）。
（＝ ~/us_work/c/c3s/ops/b1030/finalize.py 的一般月版：停用條件級別寫 json、換股單備註加註；去掉 10/30 補記專用字樣。）

驗算（全過才出單）：
  V1 注入 ones、rand 兩次：換股單 proxy 模式除構造欄外逐欄相同、候補相同；C3sF 濾網（擋／不擋、SPY、200 日線）相同；
     停用條件主臂判後級、原因、R12、D 相同（差 ≤ 1e−12）；前瞻 ② 簿級別、原因相同。
  V2 新版 e71b5bc77e 換股單前 25 欄（表頭與值）＝ 舊版 f56133f55a。
  V3 C3sF 紀錄列（filter.csv 已凍結者以紀錄為準）濾網 ＝ 現算。
⇒ final/verify.json；通過 ⇒ final/repo/…（要進 repo 的檔）、final/mail.md、final/order_<M>_names.csv、final/commit_msg.txt、final/manifest.json；
   不過 ⇒ final/fail.md。退出碼：通過 0、驗算不過 3。

    python finalize.py --stage <dir> --ts YYYYMMDD-HHMM
"""
import argparse
import csv
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c3sm_common as CM  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--stage", required=True)
ap.add_argument("--ts", required=True)
a = ap.parse_args()
S = json.load(open(os.path.join(a.stage, "summary.json"), encoding="utf-8"))
M = S["月底"]; MD = M.replace("-", ""); C = S["資料commit"]
FIN = os.path.join(a.stage, "final")
shutil.rmtree(FIN, ignore_errors=True); os.makedirs(FIN)
TOL = 1e-12
chk, bad = [], []


def ok(name, cond, detail=""):
    chk.append({"項": name, "過": bool(cond), "說明": detail})
    if not cond:
        bad.append(f"{name}：{detail}")


# V1
fz = S["C3sF"]["現算"]; ma = S["停用條件"]["主臂"]; fw = S["停用條件"]["前瞻②"]
for kind in ("ones", "rand"):
    p = os.path.join(a.stage, f"inj_{kind}", "inject.json")
    if not os.path.exists(p):
        ok(f"注入 {kind}", False, "沒有 inject.json"); continue
    J = json.load(open(p, encoding="utf-8"))
    px = J["proxy"]
    ok(f"注入 {kind}：換股單（proxy）除構造欄外相同", px["除構造欄外相同"], json.dumps(px["不同欄"], ensure_ascii=False))
    vo = S["換股單"]["view舊"]
    cand0 = vo["空槽候補（前10% 未持有、依 MOM 序；現金不足或開盤無效所以沒買）"]
    ok(f"注入 {kind}：候補相同", px["候補"] == cand0, f"{px['候補']} vs {cand0}")
    ok(f"注入 {kind}：換股後持股相同", px["換股後持股"] == vo["換股後持股"], f"{px['換股後持股']} vs {vo['換股後持股']}")
    fr = J["C3sF filter 列"] or {}
    ok(f"注入 {kind}：C3sF 濾網相同", fr.get("濾網") == fz["濾網"] and fr.get("SPY還原收盤") == fz["SPY還原收盤"] and fr.get("SPY200日線") == fz["SPY200日線"],
       f"{fr.get('濾網')}／{fr.get('SPY還原收盤')}／{fr.get('SPY200日線')} vs {fz['濾網']}／{fz['SPY還原收盤']}／{fz['SPY200日線']}")
    jm = J["主臂"]
    ok(f"注入 {kind}：停用條件主臂相同", jm["判後級"] == ma["判後級"] and jm["原因"] == ma["原因"] and abs(jm["R12"] - ma["R12"]) <= TOL
       and abs(jm["D"] - ma["D"]) <= TOL and jm["月序"] == ma["月序"], f"級 {jm['判後級']}／{jm['原因']} vs {ma['判後級']}／{ma['原因']}")
    ok(f"注入 {kind}：停用條件前瞻②相同", J["前瞻②"]["級別"] == fw["級別"] and J["前瞻②"]["原因"] == fw["原因"], f"{J['前瞻②']} vs {fw['級別']}／{fw['原因']}")
    au = J["auto"]
    chk.append({"項": f"注入 {kind}：auto（{au['實際模式']}，假開盤價成交）", "過": None,
                "說明": "只記錄、不當判準；不同欄：" + json.dumps([c for c, _, _ in au["不同欄"]], ensure_ascii=False)})
# V2
ro = list(csv.reader(open(S["換股單"]["舊版raw"]["路徑"], encoding="utf-8-sig")))
rn = list(csv.reader(open(S["換股單"]["新版raw"]["路徑"], encoding="utf-8-sig")))
ok("新版前 25 欄表頭相同", ro[0][:25] == rn[0][:25], "")
ok("新版前 25 欄值相同", ro[1][:25] == rn[1][:25], json.dumps([(ro[0][i], ro[1][i], rn[1][i]) for i in range(25) if ro[1][i] != rn[1][i]], ensure_ascii=False))
ok("新版多一欄「全名」在備註前", rn[0][25:] == ["全名", ro[0][25]] and rn[1][26] == ro[1][25], str(rn[0][25:]))
# V3
led = S["C3sF"]["紀錄列"] or {}
ok("C3sF 紀錄列 ＝ 現算濾網", led.get("濾網") == fz["濾網"], f"紀錄 {led.get('濾網')} vs 現算 {fz['濾網']}")
PASS = not bad
ver = {"月底": M, "通過": PASS, "不過": bad, "檢查": chk, "資料commit": C, "記錄時間": S["記錄時間"], "ts": a.ts}
json.dump(ver, open(os.path.join(FIN, "verify.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
if not PASS:
    with open(os.path.join(FIN, "fail.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(f"- {b}" for b in bad) + "\n")
    print("驗算不過：" + "；".join(bad))
    sys.exit(3)

# ── 收尾：級別 json、換股單加註 ──
line = ma["一行"]; fline = fw["一行"]
note = (f"；程式 {CM.OLD_REV}；資料 us-stock-data {C[:10]} 截至 {M}（成分／價格欄的「881c86a」是舊程式寫死字樣）"
        f"；{line}（主臂續抱簿）；前瞻 ② 簿 {fline}；注入 M 之後假列驗算相同（run_c3s_month.sh）")
outs = {}
for tag, src, dst in (("舊版", S["換股單"]["舊版raw"]["路徑"], f"backtest/resultsUSC/C3s/ops/order_{MD}.csv"),
                      ("新版", S["換股單"]["新版raw"]["路徑"], f"backtest/resultsUSC/C3s/ops/order_{MD}_names.csv")):
    rows = list(csv.reader(open(src, encoding="utf-8-sig")))
    rows[1][-1] += note
    q = os.path.join(FIN, "repo", dst); os.makedirs(os.path.dirname(q), exist_ok=True)
    with open(q, "w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerows(rows)
    outs[tag] = q
lvj = {"件": f"USREG-C3s 停用條件 {M} 月底級別（監控規則、⛔ 不計 N）",
       "簿": "主臂續抱簿（＝ 換股單 order 同一簿；2016-12-30 收盤起，看過段 x、Dmax 寫死常數；狀態機 researchStopRule.levels 原樣）",
       "月底": M, "月序": ma["月序"], "R_類": ma["R_類"], "R12": ma["R12"], "R12_百分比": f"{ma['R12'] * 100:+.1f}%", "D": ma["D"], "D_百分比": f"{ma['D'] * 100:+.1f}%",
       "x": S["停用條件"]["x"], "Dmax": S["停用條件"]["Dmax"], "警戒線 0.8×Dmax": 0.8 * S["停用條件"]["Dmax"],
       "T1": ma["T1"], "T2警戒": ma["T2警戒"], "T2停用": ma["T2停用"], "判前級": ma["判前級"], "判後級": ma["判後級"], "原因": ma["原因"], "一行": line,
       "生效": f"{M} 的下一交易日開盤起", "前瞻 ② 簿（stop.py ③ 原定義）": {"級別": fw["級別"], "原因": fw["原因"], "R": fw["R"], "D": fw["D"], "一行": fline},
       "⚠ 資料": f"us-stock-data {C[:10]} 截到 {M}（快照 {S['資料根']}）；live 會刪離開指數代號的檔（倖存者偏差，見 10/30 期信）",
       "world": {"路徑": S["world"]["路徑"], "sha256": S["world"]["sha256"], "cal 最後": S["world"]["cal最後"]},
       "程式": f"{CM.OLD_REV}（worktree ~/c3s_f561）", "驗算": "注入 M 之後假列（全 1、亂數）：換股單 proxy、C3sF 濾網、停用條件級別相同", "算於": f"{S['記錄時間']}（台北）"}
lp = os.path.join(FIN, "repo", f"backtest/resultsUSC/C3s/stop/level_{MD}.json"); os.makedirs(os.path.dirname(lp), exist_ok=True)
json.dump(lvj, open(lp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for sub, names in (("us_c3sf", ("filter.csv", "monthly.csv", "state.json", "runlog.md")), ("us_c11", ("monthly.csv", "state.json", "runlog.md"))):
    for nm in names:
        s_ = os.path.join(a.stage, sub, nm)
        if os.path.exists(s_):
            d_ = os.path.join(FIN, "repo", "backtest", "forward", sub, nm); os.makedirs(os.path.dirname(d_), exist_ok=True)
            shutil.copy2(s_, d_)
shutil.copy2(outs["新版"], os.path.join(FIN, f"order_{MD}.csv"))      # 給信箱（含全名欄）
files = sorted(os.path.relpath(os.path.join(dp, f), os.path.join(FIN, "repo")) for dp, dn, fn in os.walk(os.path.join(FIN, "repo")) for f in fn)
open(os.path.join(FIN, "repo_files.txt"), "w", encoding="utf-8").write("\n".join(files) + "\n")
man = {"換股單 舊版 raw": S["換股單"]["舊版raw"]["sha256"], "換股單 新版 raw": S["換股單"]["新版raw"]["sha256"]}
man.update({f: CM.sha256f(os.path.join(FIN, "repo", f)) for f in files})
man["world.npz"] = S["world"]["sha256"]
json.dump(man, open(os.path.join(FIN, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ── 信 ──
vn = S["換股單"]["view新"]
sells = [f"{x['代號']}（{x['全名']}）：{x['原因']}，月底排名 {x['月底排名'] or '—'}" for x in vn["賣"]]
buys = [f"{x['代號']}（{x['全名']}）：月底排名 {x['月底排名']}" for x in vn["買（依序）"]]
cand = vn["空槽候補（前10% 未持有、依 MOM 序；現金不足或開盤無效所以沒買）"]
held = vn["換股後持股（代號（全名））"]
fzr = S["C3sF"]["紀錄列"]
sp = lambda s: f"{float(s):.2f}"
L = ["尚未驗證（看過段、集中度高），試單金額自行控制", "",
     f"# 件｜美股情報 ← 回測線：C3s 換股單 {M} 月底 → 下一交易日開盤", "",
     f"**寄件**：回測線（run_c3s_month.sh 自動）　**台北時戳**：{a.ts[:4]}-{a.ts[4:6]}-{a.ts[6:8]} {a.ts[9:11]}:{a.ts[11:13]}", "",
     "## 換股單（主臂續抱簿）",
     f"- **月底**：{M}（收盤量測）；**執行**：下一交易日開盤；成交價口徑：e 開盤 ≈ 月底收盤",
     "- **賣**：" + ("；".join(sells) if sells else "無"),
     "- **買（依序）**：" + ("；".join(buys) if buys else "無"),
     f"- **換股後持股**（{len(held)} 檔）：" + "、".join(held),
     f"- **空槽**：{vn['空槽']}" + (f"（候補 {'、'.join(cand)}：現金不足或開盤無效所以沒買）" if cand else ""),
     f"- 每筆新買金額：{vn['每筆新買金額']}",
     f"- ⚠ {vn['⚠ 全名']}", "",
     "## 停用條件",
     f"- **{line}**（主臂續抱簿，＝ 換股單同一簿）",
     f"- 前瞻 ② 簿：{fline}", "",
     "## C3sF 濾網",
     f"- **{fzr['濾網']}**：SPY 還原收盤 {sp(fzr['SPY還原收盤'])}、200 日線 {sp(fzr['SPY200日線'])}（{'被擋 ⇒ 下一換股日不新買' if fzr['濾網'] == '擋' else '不擋'}；C3sF 是前瞻紙上紀錄，不影響換股單）", "",
     "## 檔案與 sha256",
     f"- 換股單（含全名欄、已加註）：`_營量觀察/c3s_{M}_order.csv`　{man[f'backtest/resultsUSC/C3s/ops/order_{MD}_names.csv'][:16]}…",
     f"- 換股單舊版（repo `order_{MD}.csv`）：加註後 {man[f'backtest/resultsUSC/C3s/ops/order_{MD}.csv'][:16]}…（加註前 {man['換股單 舊版 raw'][:16]}…）",
     f"- 停用條件級別 `level_{MD}.json`：{man[f'backtest/resultsUSC/C3s/stop/level_{MD}.json'][:16]}…",
     f"- C3sF filter.csv：{man.get('backtest/forward/us_c3sf/filter.csv', '')[:16]}…",
     f"- world.npz：{man['world.npz'][:16]}…", "",
     "## 怎麼產的",
     f"- 程式 {CM.OLD_REV}（10/17 版，裁定指定）；新版 {CM.NEW_REV} 只多「全名」欄，前 25 欄逐字相同。",
     f"- 資料 us-stock-data {C[:10]}，全部截到 ≤ {M}；世界 cal 最後一天 {M}。",
     "- 注入驗算：尾端加 M 之後假列（全設 1、亂數各一次），換股名單、C3sF 濾網、停用條件級別都相同。", "",
     "描述，不是買賣建議", "", "— 回測線"]
open(os.path.join(FIN, "mail.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
nb = len(vn["買（依序）"]); ns = len(vn["賣"])
msg = (f"美股 C3s 月底換股單 {M}（run_c3s_month.sh）：賣 {ns}、買 {nb}、持股 {len(held)} 檔＋空 {vn['空槽']} 槽；C3sF 濾網{fzr['濾網']}；"
       f"停用條件主臂級 {ma['判後級']}（{ma['原因']}）；程式 {CM.OLD_REV}、us-stock-data {C[:10]} 截至 {M}、注入假列驗算相同\n\n"
       "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n")
open(os.path.join(FIN, "commit_msg.txt"), "w", encoding="utf-8").write(msg)
print(f"驗算通過｜賣 {ns} 買 {nb} 持股 {len(held)} 空 {vn['空槽']}｜濾網 {fzr['濾網']}｜{line}")
