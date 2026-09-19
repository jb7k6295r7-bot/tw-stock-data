#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_longhalt.py — 驗 G2 每日累積的三個限定（0020）。

## ⛔ 假回應照**真回應的形狀**做，⛔ 不是照說明

每一份假回應的鍵名都是從 `data/meta/_suspend_probe.txt` 第六輪**逐字抄**的
（上市是中文鍵、上櫃是英文鍵，⛔ 兩家不一樣），⚠ 而**形狀**也照抄：

```
`t187ap26_L`  2026-09-17 那一發回**一列、每一欄都空的**（佔位列）
              ⇒ ⛔ 用列數判斷「有沒有資料」會數到 1
`tpex_cmode`  20 列、**沒有任何日期欄**（只有出表日期）
              ⇒ ⛔ 它講不出自己是哪一筆 ⇒ 去重鍵只能用旗標
```

## ⭐ 而這一支的主角是**第二趟**

這一族的錯法不在「抓得到嗎」，在**累積**：
⛔ 整份覆蓋（四點六）、⛔ 同一天跑兩趟數兩次、⛔ 今天沒回來就把舊列刪掉。
⇒ 每一條都拿**兩趟**驗，⛔ 不是驗一趟的輸出長什麼樣。
"""
import io
import json
import os
import shutil
import sys
import tempfile

import longhalt as L
import runlog

FAIL = []
N = [0]


def ck(label, cond, note=""):
    N[0] += 1
    print(f"  {'✓' if cond else '✗'} {label}" + (f"｜{note}" if note else ""))
    if not cond:
        FAIL.append(label)


# ── 假回應：鍵名與形狀逐字照 `_suspend_probe.txt` 第六輪 ──
TWSE_BLANK = json.dumps([{"停止買賣開始日": "", "公司代號": "", "公司名稱": "",
                          "出表日期": "1150917"}]).encode()
TWSE_ONE = json.dumps([{"停止買賣開始日": "1150910", "公司代號": "1234",
                        "公司名稱": "測試", "出表日期": "1150917"}]).encode()
TPEX_O = json.dumps([{"CompanyName": "大略-KY", "Date": "1150917",
                      "SecuritiesCompanyCode": "4804",
                      "停止買賣開始日": "1150903"}]).encode()
CMODE = json.dumps([
    {"SecuritiesCompanyCode": "2067", "CompanyName": "中湛", "Date": "1150917",
     "SuspensionOfTrading": "Ｙ", "AlteredTrading": "Ｙ", "PeriodicTrading": "",
     "MatchingFrequency": "", "ManagedStock": "", "FinancialAnnouncements": "Ｙ"},
    {"SecuritiesCompanyCode": "3064", "CompanyName": "佳總", "Date": "1150917",
     "SuspensionOfTrading": "", "AlteredTrading": "Ｙ", "PeriodicTrading": "Ｙ",
     "MatchingFrequency": "030", "ManagedStock": "", "FinancialAnnouncements": "Ｙ"},
]).encode()


def feeder(mapping):
    """→ 一個 `fetch(url)`；`mapping` 沒寫到的網址回 `(None, "沒有這一條")`。"""
    def _f(url):
        if url not in mapping:
            return None, "沒有這一條"
        v = mapping[url]
        return (None, v) if isinstance(v, str) else (v, None)
    return _f


def run_safe(**kw):
    """跑一趟，⭐ **自己接住例外**。→ `(rl, seen, add, upd)`；炸掉回 `(None, None, …)`。

    ⛔ 不接住的話，一個突變會讓整支自測**當場中斷** ⇒ 後面一條都不會跑，
    ⚠ 而「崩潰」跟「這條斷言沒用」在畫面上一模一樣（七點②）。
    """
    try:
        rl, seen, add, upd = L.run(**kw)
        return rl, seen, add, upd
    except Exception as ex:                                        # noqa: BLE001
        boom = f"{type(ex).__name__}: {ex}"
        print(f"    ⚠ 這一趟炸掉了：{boom}")
        return None, None, boom, boom


URLS = {s["src"]: s["url"] for s in L.SOURCES}
ALL_OK = {URLS["twse-t187ap26_L"]: TWSE_BLANK,
          URLS["tpex-t187ap26_O"]: TPEX_O,
          URLS["tpex-cmode"]: CMODE}


def main():
    print("== selftest_longhalt ==")
    tmp = tempfile.mkdtemp(prefix="longhalt_")
    out = os.path.join(tmp, "longhalt.csv")
    before_out = (io.open(L.OUT, "rb").read() if os.path.exists(L.OUT) else None)
    before_log = (io.open(runlog.PATH, "rb").read()
                  if os.path.exists(runlog.PATH) else None)
    saved = runlog.PATH
    runlog.PATH = os.path.join(tmp, "_last_run.md")
    try:
        # ── ① 解析：鍵名兩家不同，⛔ 不可以共用一份對照 ──
        rows, asof = L.parse(TPEX_O, L.SOURCES[1])
        ck("① 上櫃 event 解析得出來", len(rows) == 1 and rows[0]["stock_id"] == "4804")
        ck("① ⭐ 民國轉西元（開始日）", rows[0]["start_date"] == "2026-09-03",
           rows[0]["start_date"])
        ck("① ⭐ 官方自己的出表日也帶回來（⛔ 它跟我方抓取日是兩件事）",
           asof == "2026-09-17", asof)

        # ── ② ⛔ 佔位列：一列、每一欄都空 ⇒ 它**不是**資料 ──
        blank, _ = L.parse(TWSE_BLANK, L.SOURCES[0])
        ck("② ⭐⭐ 全空的佔位列被丟掉（⛔ 用列數判斷會數到 1）", blank == [], f"{blank}")
        real, _ = L.parse(TWSE_ONE, L.SOURCES[0])
        ck("② ⛔ 而真的有案件時**不可以**跟著被丟掉", len(real) == 1)

        # ── ③ state：沒有日期欄 ⇒ 鍵用旗標，⛔ 六個旗標全收 ──
        cm, _ = L.parse(CMODE, L.SOURCES[2])
        ck("③ cmode 兩列", len(cm) == 2)
        ck("③ ⭐ 六個旗標全收（⛔ 不是只收 SuspensionOfTrading）",
           "AlteredTrading=Ｙ" in cm[0]["flags"]
           and "FinancialAnnouncements=Ｙ" in cm[0]["flags"], cm[0]["flags"])
        ck("③ ⛔ 空的旗標不佔位", "ManagedStock" not in cm[0]["flags"])
        ck("③ ⭐ state 沒有開始日（⛔ 而那正是它講不出自己是哪一筆的原因）",
           cm[0]["start_date"] == "")
        ck("③ ⭐⭐ 兩種形狀用**兩種鍵**",
           L.key_of(rows[0])[2] == "2026-09-03"
           and L.key_of(cm[0])[2] == cm[0]["flags"])

        # ── ④ ⭐ 第一趟 ──
        _rl, seen, add, upd = run_safe(fetch=feeder(ALL_OK), today="2026-09-17",
                                       path=out)
        ck("④ 第一趟看到 3 列（上市那一列是佔位 ⇒ 不算）", seen == 3, f"{seen}")
        ck("④ 全部是新增", (add, upd) == (3, 0), f"{add}/{upd}")
        cur = L.load(out)
        ck("④ ⭐ 逐列帶抓取日（限定①）",
           all(r["first_asof"] == "2026-09-17" and r["n_obs"] == "1"
               for r in cur.values()))

        # ── ⑤ ⭐⭐ 同一天再跑一趟：**冪等**（daily 一天跑兩趟） ──
        _rl2, _seen2, add2, upd2 = run_safe(fetch=feeder(ALL_OK), today="2026-09-17",
                                            path=out)
        cur2 = L.load(out)
        ck("⑤ ⭐⭐ 同一天再跑：⛔ 不新增、⛔ 也不重複計數",
           (add2, upd2) == (0, 0) and all(r["n_obs"] == "1" for r in cur2.values()),
           f"{add2}/{upd2}｜{sorted(r['n_obs'] for r in cur2.values())}")

        # ── ⑥ 隔天：同一批 ⇒ 更新而不是新增 ──
        run_safe(fetch=feeder(ALL_OK), today="2026-09-18", path=out)
        cur3 = L.load(out)
        ck("⑥ 隔天同一批 ⇒ 更新（n_obs 2、first_asof 不動）",
           len(cur3) == 3 and all(r["n_obs"] == "2"
                                  and r["first_asof"] == "2026-09-17"
                                  for r in cur3.values()))

        # ── ⑦ ⭐⭐ 今天少回來一條 ⇒ 舊列**原封不動**（四點六） ──
        run_safe(fetch=feeder({URLS["tpex-cmode"]: CMODE}), today="2026-09-19",
                 path=out)
        cur4 = L.load(out)
        ck("⑦ ⭐⭐ 沒回來的那一條**一列都沒少**（⛔ 這一支絕不可以刪東西）",
           len(cur4) == 3, f"{len(cur4)}")
        ck("⑦ ⭐ 而它的 last_asof **停在上一次看到的那天**（⛔ 不是今天）",
           [r["last_asof"] for k, r in cur4.items()
            if k[0] == "tpex-t187ap26_O"] == ["2026-09-18"])
        ck("⑦ 有回來的那兩列才前進到今天",
           all(r["last_asof"] == "2026-09-19"
               for k, r in cur4.items() if k[0] == "tpex-cmode"))

        # ── ⑧ ⭐ 旗標變了 ＝ 新的一段（⛔ 不是把舊的改掉） ──
        cmode2 = json.dumps(json.loads(CMODE.decode())[:1]).encode()
        chg = json.loads(cmode2.decode())
        chg[0]["SuspensionOfTrading"] = ""          # 停止交易解除了
        run_safe(fetch=feeder({URLS["tpex-cmode"]: json.dumps(chg).encode()}),
                 today="2026-09-20", path=out)
        cur5 = L.load(out)
        ck("⑧ ⭐ 旗標變了 ⇒ 多一段（⛔ 舊那一段留著）", len(cur5) == 4, f"{len(cur5)}")

        # ── ⑨ ⛔ 三條全失敗 ⇒ 一個字都不寫 ──
        raw_before = io.open(out, "rb").read()
        rl9, seen9, _a9, _u9 = run_safe(fetch=feeder({}), today="2026-09-21",
                                        path=out)
        ck("⑨ ⛔ 三條全失敗 ⇒ 那個檔**逐位元沒有變**",
           io.open(out, "rb").read() == raw_before)
        ck("⑨ ⛔ 而它回報本趟看到 0 列", seen9 == 0, f"{seen9}")
        # ⛔⛔ 上面那一條**單獨不夠**：全部失敗時 `seen` 是空的 ⇒ 就算照樣走
        #   `merge` ＋ `save`，寫回去的內容也**一模一樣** ⇒ 那條斷言分不出來
        #   （實測：突變 G8「三條全失敗也照樣寫下去」回**全綠**）。
        # ⇒ ⭐ 要驗到它，得用**那個檔還不存在**的情境：照樣走下去會生出一份
        #   只有表頭的檔，⚠ 而那份空殼會讓下一趟以為「以前什麼都沒看到」。
        fresh = os.path.join(tmp, "fresh.csv")
        run_safe(fetch=feeder({}), today="2026-09-21", path=fresh)
        ck("⑨ ⭐⭐ 第一趟就三條全失敗 ⇒ **連檔都不要建**（⛔ 不是建一份空殼）",
           not os.path.exists(fresh))
        # ⭐ 而那一趟要**紅**：那條 check 是 False（⛔ 不是安靜地回 0 列）
        _bad = [c for c in (rl9.checks if rl9 else []) if not c[1]]
        ck("⑨ ⭐ 而那一趟的 check 是 ✗（⛔ 安靜地收工跟成功長得一樣）",
           any("至少有一條來源答得出來" in c[0] for c in _bad), f"{_bad}")

        # ── ⑩ ⭐ 保留期那一句只可以說「至少」（限定③） ──
        line = L.retention_line(cur5)
        ck("⑩ ⭐ 有「至少」也有「上限未知」", "至少" in line and "上限未知" in line, line)
        ck("⑩ ⛔ 而它講得出樣本有多大（⚠ 沒有樣本數的保留期是假的）",
           "觀測" in line and "天" in line)
        ck("⑩ ⭐ 還沒有觀測時**一個字都不說**",
           "一個字都還不能說" in L.retention_line({}))

        # ── ⑪ ⛔ 合併後列數變少 ⇒ 大聲失敗，⛔ 不是靜靜寫下去 ──
        try:
            L.save({}, out)
            loud = False
        except RuntimeError:
            loud = True
        ck("⑪ ⭐⭐ 列數變少 ⇒ **大聲失敗**（⛔ 這支絕不可以變成刪東西的那個人）", loud)
    finally:
        runlog.PATH = saved
        shutil.rmtree(tmp, ignore_errors=True)

    after_out = (io.open(L.OUT, "rb").read() if os.path.exists(L.OUT) else None)
    after_log = (io.open(runlog.PATH, "rb").read()
                 if os.path.exists(runlog.PATH) else None)
    ck("★ 沒有動到 repo 真的 longhalt.csv", before_out == after_out)
    ck("★ 沒有動到 repo 真的 _last_run.md", before_log == after_log)

    print(f"通過 {N[0] - len(FAIL)}｜失敗 {len(FAIL)}")
    for f in FAIL:
        print(f"  ✗ {f}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
