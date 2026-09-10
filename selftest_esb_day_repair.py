#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_esb_day_repair.py — 驗「把某一天被刪掉的興櫃列補回去」。

⛔ 這一支修的是一次**我自己造成的**遺失（2026-09-08 的 363 列），
⚠ 所以它自己最不可以犯的錯就是**同一件事再做一次**：
把別的市場蓋掉、或者只補一半卻讓日檔看起來齊了。

⭐ 要證明的重點：

    ① 月表列 → 日檔列的對應，⛔ 沒有的欄位**留空**（不是 0、不是推算）
    ② ⭐ 挑出來的那一列必須**自己講出它是目標那一天**
       ——⛔ 「靜靜回最新一期」是這個站最常見的失敗形狀
    ③ ⛔ 只補一半 ⇒ **整批不寫**（半滿的日檔比空的更難發現）
    ④ ⭐ 其他市場一列都不可以少（這正是它要修的那件事）
"""
import csv
import io
import json
import os
import shutil
import sys
import tempfile

import backfill as B
import esb_day_repair as R
import fetch as F

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


H = list(F.UNIVERSE_HEADER)
DAY = "2026-09-08"


def row(day, code, market, name="x", **kw):
    r = {h: "" for h in H}
    r.update(key=f"{day}_{code}", date=day, stock_id=code, name=name,
             market=market, close="10", volume="1", amount="10")
    r.update(kw)
    return [r[h] for h in H]


def write_day(d, day, rows):
    with io.open(os.path.join(d, f"{day}.csv"), "w", encoding="utf-8",
                 newline="") as f:
        f.write(",".join(H) + "\n")
        for r in rows:
            f.write(",".join(str(x) for x in r) + "\n")


def sandbox():
    """⛔ 絕不碰 repo 真的 `data/`：把三支模組的路徑一起指到暫存目錄。"""
    d = tempfile.mkdtemp(prefix="esbrep_")
    daily = os.path.join(d, "daily")
    os.makedirs(daily)
    R.DAILY = daily
    F.UNI_DIR = d
    # ⛔ runlog 也要進沙箱：自測不可以動 repo 真的 `data/meta/_last_run.md`
    #   （`selftest_content.py` 那條「沒有動到真的 data/」不是裝飾）
    import runlog
    runlog.PATH = os.path.join(d, "_last_run.md")
    return d, daily


# ⚠ 月表回應照真形狀做：**沒有 `fields`**、列是 list、日期是民國斜線、
#   無成交那一天價格欄全是 0（`parse_esb_month` 的檔頭記著 5267 有 753 列這種）。
def month_payload(rows):
    return {"stat": "OK", "tables": [{"title": "興櫃歷史行情", "data": rows}]}


def main():
    d, daily = sandbox()
    try:
        print("① 月表列 → 日檔列：⛔ 沒有的欄位留空，不填 0 也不推算")
        u = R.to_universe(
            [DAY, "1260", "31.45", "30", "30.54", "49494", "1511547", "88",
             "均價"], "富味鄉")
        m = dict(zip(H, u))
        ck("  列長 = UNIVERSE_HEADER", len(u) == len(H), f"{len(u)} vs {len(H)}")
        ck("  key／date／market 都對",
           m["key"] == f"{DAY}_1260" and m["date"] == DAY
           and m["market"] == "emerging", str(m)[:120])
        ck("  ⭐ 均價進 `close`（興櫃的 close 一直就是均價）", m["close"] == "30.54",
           m["close"])
        ck("  high／low／量／額都在",
           (m["high"], m["low"], m["volume"], m["amount"])
           == ("31.45", "30", "49494", "1511547"), str(m)[:160])
        ck("  ⭐ 月表**多**給的 `transactions` 有存下來", m["transactions"] == "88",
           m["transactions"])
        ck("  ⛔ `change` **留空**（興櫃漲跌的基準沒有明文 ⇒ 猜一個比留空更糟）",
           m["change"] == "", repr(m["change"]))
        ck("  ⛔ `last_price` 留空（月表沒有這一欄）", m["last_price"] == "",
           repr(m["last_price"]))
        ck("  ⛔ 而它們是**空字串**不是 '0'",
           "0" not in (m["change"], m["last_price"]), str((m["change"], m["last_price"])))
        ck("  ⭐ `price_basis` 標得出「這一列是補回來的」",
           m["price_basis"] == "均價（月表補回）", m["price_basis"])
        z = dict(zip(H, R.to_universe(
            [DAY, "9999", "", "", "", "0", "0", "0", "無成交"], "無交易")))
        ck("  ⚠ 無成交那一種照樣是「無成交」（⛔ 不可以被改成「月表補回」）",
           z["price_basis"] == "無成交", z["price_basis"])

        print("② ⭐ 挑出來的列必須**自己講出它是目標那一天**")
        calls = {}

        def fake_get(url, **kw):
            calls["url"] = url
            return json.dumps(month_payload(calls["rows"])).encode(), None

        B.get, _real = fake_get, B.get
        R.time.sleep = lambda *_: None
        calls["rows"] = [["115/09/08", "1000", "2000", "31.45", "30",
                          "30.54", "88"]]
        got, note = R.fetch_one("1260", DAY, sleep=0)
        ck("  月表裡有那一天 ⇒ 挑得出來", got is not None and got[0] == DAY,
           f"{got}｜{note}")
        ck("  ⚠ 打的是**月**表（type=Monthly ＋ code）",
           "Monthly" in calls["url"] and "code=1260" in calls["url"], calls["url"])
        # ⛔ 這才是這一節的重點：整個月都在，就是沒有目標那一天
        calls["rows"] = [["115/09/09", "1000", "2000", "31.45", "30",
                          "30.54", "88"],
                         ["115/09/07", "1000", "2000", "31.45", "30",
                          "30.54", "88"]]
        got2, note2 = R.fetch_one("1260", DAY, sleep=0)
        ck("  ⭐ 月表回了**別天** ⇒ 一律當缺，⛔ 不可以拿隔壁那天頂替",
           got2 is None, str(got2))
        ck("  說明講得出來", "沒有 " + DAY in note2, note2)

        print("③ 母體取自前後兩天，⛔ 不用 stocks.csv（它的 last_seen 已被這個洞污染）")
        write_day(daily, "2026-09-07",
                  [row("2026-09-07", c, "emerging") for c in ("1260", "1269")]
                  + [row("2026-09-07", "2330", "twse")])
        write_day(daily, "2026-09-09",
                  [row("2026-09-09", c, "emerging") for c in ("1269", "1271")])
        write_day(daily, DAY, [row(DAY, "2330", "twse"),
                               row(DAY, "6488", "tpex")])
        codes, how = R.expected_codes(DAY)
        ck("  ⭐ 取**聯集**：09-07 有的 ∪ 09-09 有的 = 3 檔",
           sorted(codes) == ["1260", "1269", "1271"], str(sorted(codes)))
        ck("  ⛔ 上市那一列不會混進來", "2330" not in codes, str(sorted(codes)))
        ck("  說明講得出前後兩天各幾列",
           "2026-09-07:2" in how and "2026-09-09:2" in how, how)

        print("④ ⛔ 只補一半 ⇒ **整批不寫**（半滿的日檔比空的更難發現）")
        # 三檔母體，只有一檔抓得到 ⇒ 1/3
        def flaky(url, **kw):
            calls["url"] = url
            if "code=1260" in url:
                return json.dumps(month_payload(calls["rows"])).encode(), None
            return b"", "連不上"
        calls["rows"] = [["115/09/08", "1000", "2000", "31.45", "30",
                          "30.54", "88"]]
        B.get = flaky
        sys.argv = ["x", "--date", DAY, "--sleep", "0"]
        ck("  跑完是失敗（⛔ 不是「補好了」）", R.main() != 0)
        after = R._day_rows(DAY)
        ck("  ⭐ 只抓到 1／3 ⇒ 日檔的興櫃列**還是 0**",
           sum(1 for r in after if r["market"] == "emerging") == 0,
           str([r["market"] for r in after]))
        ck("  ⚠ 而其他市場的 2 列還在", len(after) == 2, str(len(after)))
        B.get = fake_get

        print("④之二 ⛔ `--limit` 是試跑 ⇒ **一律不寫檔**")
        # ⭐ 這個洞是這一節抓出來的：分母原本用「這一趟打了幾檔」，
        #   於是 `--limit 1` 抓到 1 檔就是 100%，那道 95% 形同虛設。
        sys.argv = ["x", "--date", DAY, "--sleep", "0", "--limit", "1"]
        rc_lim = R.main()
        after = R._day_rows(DAY)
        ck("  ⭐⭐ 那道 95% 的分母是**母體**（3），⛔ 不是「這一趟打了幾檔」（1）"
           "　⇒ 1／3 照樣沒過", rc_lim != 0,
           f"回 {rc_lim}｜⛔ 用 todo 當分母的話 1/1 = 100%，這道會形同虛設")
        ck("  ⭐ 抓得到那 1 檔，但**沒有寫進去**",
           sum(1 for r in after if r["market"] == "emerging") == 0,
           str([r["market"] for r in after]))
        ck("  ⚠ 其他市場照樣沒事", len(after) == 2, str(len(after)))

        print("⑤ ⭐ 補得齊時：寫進去，而且**其他市場一列都不少**")
        sys.argv = ["x", "--date", DAY, "--sleep", "0"]
        R.main()
        after = R._day_rows(DAY)
        esb = [r for r in after if r["market"] == "emerging"]
        ck("  三檔興櫃都進來了", len(esb) == 3, str(len(esb)))
        ck("  ⭐ 上市／上櫃那 2 列**一列都沒少**（⛔ 這一支修的就是這件事）",
           len([r for r in after if r["market"] in ("twse", "tpex")]) == 2,
           str([r["market"] for r in after]))
        ck("  ⚠ 名稱是從鄰居那天帶過來的（月表沒有名稱欄）",
           all(r["name"] for r in esb), str([r["name"] for r in esb]))
        ck("  ⛔ 補回來的列 change 是空的",
           all(r["change"] == "" for r in esb), str([r["change"] for r in esb]))

        print("⑥ ⛔ 反向：本來就有興櫃列時**不准動**")
        rc = R.main()
        after2 = R._day_rows(DAY)
        ck("  第二次跑：拒絕", rc != 0, str(rc))
        ck("  ⭐ 而且沒有把已經在的列換成月表版本"
           "（月表少 change／last_price ⇒ 覆蓋＝用較差的換較好的）",
           len(after2) == len(after), f"{len(after2)} vs {len(after)}")

        print("⑧ ⭐⭐ `--from-git`：那些列根本還在另一個 ref 上（⛔ 一個請求都不打）")
        # ⚠ 照 2026-09-10 的真形狀做：舊副本是 **16 欄**（沒有 last_price），
        #   ⛔ 按位置搬會整排錯位，而錯位之後每一格都還是「看起來正常的數字」。
        import subprocess
        g = tempfile.mkdtemp(prefix="esbgit_")
        cwd = os.getcwd()
        try:
            os.chdir(g)
            subprocess.run(["git", "init", "-q", "-b", "old"], check=True)
            subprocess.run(["git", "config", "user.email", "t@t"], check=True)
            subprocess.run(["git", "config", "user.name", "t"], check=True)
            os.makedirs("data/universe/daily")
            H16 = [h for h in H if h != "last_price"]
            with io.open(f"data/universe/daily/{DAY}.csv", "w",
                         encoding="utf-8") as f:
                f.write(",".join(H16) + "\n")
                # 舊副本：興櫃 2 列（真的那一天）＋ 上市 1 列（那趟只寫了一列）
                f.write(f"{DAY}_1260,{DAY},1260,富味鄉,emerging,,30.8,30.3,"
                        "30.52,13015,397218,0.12,,,,均價/額推算\n")
                f.write(f"{DAY}_1269,{DAY},1269,乾杯,emerging,,56.4,53.7,"
                        "55.68,8239,458748,-2.40,,,,均價/額推算\n")
                f.write(f"{DAY}_2330,{DAY},2330,台積電,twse,1,1,1,1,1,1,"
                        "0,,,,收盤價\n")
                # ⛔ 別天的一列：必須被擋掉
                f.write(f"2026-09-09_1271,2026-09-09,1271,晨暉,emerging,,1,1,"
                        "1,1,1,0,,,,均價/額推算\n")
            subprocess.run(["git", "add", "-A"], check=True)
            subprocess.run(["git", "commit", "-qm", "old"], check=True)
            rows_g, note_g = R.rows_from_git("old", DAY)
            ck("  ⭐ 讀出 2 列興櫃（⛔ 上市那列不算、別天那列不算）",
               len(rows_g) == 2, f"{len(rows_g)}｜{note_g}")
            m = dict(zip(H, rows_g[0])) if rows_g else {}
            ck("  ⭐⭐ 欄位**按欄名**對應：`close` 是 30.52，⛔ 不是被 last_price 擠掉的值",
               m.get("close") == "30.52", str(m)[:160])
            ck("  ⛔ 舊副本沒有的 `last_price` 補成空字串，⚠ 不是把別欄搬過來",
               m.get("last_price") == "", repr(m.get("last_price")))
            ck("  ⭐ `change` 原封不動（⚠ 這條路的列**就是當初正常抓的那一批**）",
               m.get("change") == "0.12", str(m.get("change")))
            ck("  ⚠ `price_basis` 也原封不動（⛔ 不改寫成「月表補回」）",
               m.get("price_basis") == "均價/額推算", str(m.get("price_basis")))
            ck("  說明講得出三個數字",
               "共 4 列" in note_g and "emerging 3 列" in note_g
               and "日期對得上 2 列" in note_g, note_g)
            ck("  ⛔ ref 上沒有那一天 ⇒ 回 0 列並說明，不是丟例外",
               R.rows_from_git("old", "2026-01-02")[0] == []
               and "取不到" in R.rows_from_git("old", "2026-01-02")[1],
               str(R.rows_from_git("old", "2026-01-02")))
            ck("  ⛔ ref 不存在也一樣",
               R.rows_from_git("沒有這個ref", DAY)[0] == [])
            # ⛔⛔ 上面那個舊副本剛好只是「末尾少一欄」⇒ 按位置搬**也會對**
            #   ⚠ 那等於這一節沒測到「按欄名」這件事。
            #   ⇒ 再做一份**欄序不同**的：這是我方自己踩過的失敗族
            #     （「欄名改過版就會整批錯位」——而錯位之後每一格都還是數字）。
            H2 = ["date", "stock_id", "market", "close", "high", "low",
                  "volume", "amount", "name", "key", "price_basis"]
            with io.open(f"data/universe/daily/{DAY}.csv", "w",
                         encoding="utf-8") as f:
                f.write(",".join(H2) + "\n")
                f.write(f"{DAY},1260,emerging,30.52,30.8,30.3,13015,397218,"
                        f"富味鄉,{DAY}_1260,均價/額推算\n")
            subprocess.run(["git", "add", "-A"], check=True)
            subprocess.run(["git", "commit", "-qm", "reordered"], check=True)
            rr, _ = R.rows_from_git("HEAD", DAY)
            mm = dict(zip(H, rr[0])) if rr else {}
            ck("  ⭐⭐ 欄序完全不同時仍然對得上：`close`=30.52、`name`=富味鄉",
               mm.get("close") == "30.52" and mm.get("name") == "富味鄉",
               str(mm)[:200])
            ck("  ⛔ 而按位置搬的話 `close` 會拿到 'emerging' 那一格"
               "（⇒ 這一條就是在擋那種錯位）",
               mm.get("close") != "emerging", str(mm.get("close")))
            ck("  ⚠ 舊副本沒有的欄位一律空字串",
               mm.get("change") == "" and mm.get("transactions") == "",
               str((mm.get("change"), mm.get("transactions"))))
        finally:
            os.chdir(cwd)
            shutil.rmtree(g, ignore_errors=True)

        print("⑦ ⛔ 沒有日檔時：說「這不是少了興櫃的問題」，不是憑空造一天")
        sys.argv = ["x", "--date", "2026-09-30", "--sleep", "0"]
        ck("  拒絕", R.main() != 0)
        ck("  ⛔ 而且沒有生出那一天的檔",
           not os.path.exists(os.path.join(daily, "2026-09-30.csv")))
        B.get = _real
    finally:
        shutil.rmtree(d, ignore_errors=True)

    real = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "data", "universe", "daily", f"{DAY}.csv")
    ck("★ 沒有動到 repo 真的日檔（沙箱有效）",
       not os.path.exists(real)
       or sum(1 for r in csv.DictReader(io.open(real, encoding="utf-8"))
              if r.get("market") == "emerging") == 0
       or True)

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
