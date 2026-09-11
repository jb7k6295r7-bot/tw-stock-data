#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_schema_audit.py — 釘住 `schema_audit.py` 的四個判準。

⛔ 這一支最重要的一節是 ⑤：**重現 `last_price` 那個誤判**。
2026-09-10 兩條線看到「全檔填值率 0.05%」就判它是空殼欄、建議刪掉，
⚠ 而它其實只有興櫃該有值。⇒ 這裡造一個同樣形狀的假檔，
斷言「**逐群那一列真的把它分得出來**」——⛔ 不是斷言「有算出百分比」。

⚠ 假檔照真檔的形狀做（`market` 三個值、無成交列的價格欄留空、
`volume` 是 `0` 而不是空）——⛔ 假的比真的簡單，等於那一段沒測。
"""
import io
import os
import shutil
import sys
import tempfile

import schema_audit as S

_ok = _bad = 0


def ck(name, cond, detail=""):
    global _ok, _bad
    if cond:
        _ok += 1
        print(f"  ok   {name}")
    else:
        _bad += 1
        print(f"  ✗    {name}　{detail}")


H16 = ("key,date,stock_id,name,market,open,high,low,close,volume,"
       "amount,change,limit,shares,transactions,price_basis")
H17 = H16 + ",last_price"


def w(path, text):
    io.open(path, "w", encoding="utf-8").write(text)


def main():
    sand = tempfile.mkdtemp(prefix="schaudit_")
    try:
        d = os.path.join(sand, "daily")
        os.makedirs(d)
        # ⚠ 刻意讓 v1 在 v2 之後**又出現一次**（回補跑一半的真實形狀）
        w(os.path.join(d, "2026-09-07.csv"), H16 + "\n")
        w(os.path.join(d, "2026-09-08.csv"), H17 + "\n")
        w(os.path.join(d, "2026-09-09.csv"), H16 + "\n")
        # ⛔ 一定要有**第三天**：只有兩天的話，「逐日清單」與「[頭, 尾] 區間」
        #   長得一模一樣 ⇒ ⚠ 那條斷言在「被改成回區間」時**照樣會綠**
        #   （突變 M3 實測：0 條紅）。⭐ 三天才分得出來。
        w(os.path.join(d, "2026-09-10.csv"), H16 + "\n")
        w(os.path.join(d, "notaday.csv"), H16 + "\n")

        print("── ① 表頭版本 ──")
        paths = S.day_paths(d)
        ck("⛔ 檔名不是日期的不算（`notaday.csv`）",
           [p[0] for p in paths] == ["2026-09-07", "2026-09-08",
                                     "2026-09-09", "2026-09-10"],
           str(paths))
        vers = S.schema_versions(paths)
        ck("兩個表頭 ⇒ 兩個版本", len(vers) == 2, str(len(vers)))
        ck("按**第一次出現的日期**排序（v1 是 16 欄那個）",
           len(vers[0][0]) == 16 and len(vers[1][0]) == 17,
           str([len(h) for h, _ in vers]))
        ck("⭐ 版本回的是**逐日清單**不是區間 ⇒ 不連續看得出來"
           "（v1 ＝ 09-07／09-09／09-10，中間跳過 09-08）",
           vers[0][1] == ["2026-09-07", "2026-09-09", "2026-09-10"],
           str(vers[0][1]))
        ck("　⛔ 而它**不是** [頭, 尾]（⚠ 兩天的樣本分不出這兩件事）",
           len(vers[0][1]) == 3, str(vers[0][1]))

        print("── ② 生效日 ──")
        first = S.col_first_seen(vers)
        ck("`last_price` 的生效日是它第一次出現那天（09-08）",
           first.get("last_price") == "2026-09-08", str(first.get("last_price")))
        ck("⛔ 舊欄的生效日不會被後來的版本蓋成較晚的日期",
           first.get("close") == "2026-09-07", str(first.get("close")))

        print("── ③ 「有值」的定義 ──")
        p = os.path.join(d, "2026-09-08.csv")
        w(p, H17 + "\n"
          # 有成交的興櫃：last_price 有值、volume 有值
          + "k1,2026-09-08,6740,甲,emerging,,,,57.18,28863,1650513,,,,,均價,58.00\n"
          # ⛔ 無成交的興櫃：價格欄空、volume 是 `0`（**不是空**）
          + "k2,2026-09-08,6741,乙,emerging,,,,,0,0,,,,,無成交,\n"
          # 上市：last_price 一律空（設計）
          + "k3,2026-09-08,2330,丙,twse,1000,1010,990,1005,10,10050,5,,,3,,\n"
          # ⚠ 只有空白字元的格不算有值（`name` 這一欄真實資料一定有值
          #   ⇒ 拿它當「唯一的差別就是空白」的那個對照）
          + "k4,2026-09-08,2317,   ,twse,20,21,19,20,5,100,1,,,2,   ,   \n")
        tot, hit, grp = S.fill_rates(p)
        ck("列數對（4 列）", tot == 4, str(tot))
        ck("⭐ `0` 算有值（`volume` 4／4，⛔ 無成交那列的 0 不可以被當成空）",
           hit.get("volume") == 4, f"{hit.get('volume')}／4")
        # ⭐ 用 `name` 隔離：四列裡只有第四列是空白字元，其餘都有值
        #   ⇒ 3／4 的唯一解釋就是「空白不算有值」。
        ck("⛔ 只有空白字元的格**不**算有值（`name` 3／4）",
           hit.get("name") == 3, f"{hit.get('name')}／4")
        # ⚠ 而上市的 `price_basis` 真實資料就是空的（留空＝收盤價）
        #   ⇒ 2／4 是對的，⛔ 不是缺值。
        ck("　⚠ `price_basis` 2／4（上市留空是設計，⛔ 不是缺值）",
           hit.get("price_basis") == 2, f"{hit.get('price_basis')}／4")

        print("── ④ 逐群分母 ──")
        ck("兩個 market 群，分母各 2", grp["emerging"][0] == 2
           and grp["twse"][0] == 2, str({g: v[0] for g, v in grp.items()}))

        print("── ⑤ ⭐⭐ 重現 `last_price` 那個誤判 ──")
        rate_all = hit.get("last_price", 0) / tot
        ck("　全檔填值率很低（1／4 ＝ 25%）⇒ ⛔ 光看這個會判它是空殼欄",
           rate_all < 0.5, f"{rate_all:.0%}")
        e_hit, e_n = grp["emerging"][1].get("last_price", 0), grp["emerging"][0]
        t_hit = grp["twse"][1].get("last_price", 0)
        ck("　⭐ 而逐群看得出來：emerging 1／2、twse 0／2 "
           "⇒ **「只有某一群該有值」自己顯形**",
           (e_hit, e_n, t_hit) == (1, 2, 0), f"{e_hit}／{e_n}, twse {t_hit}")

        print("── ⑥ 整欄空白 ──")
        blanks = S.empty_cols(tot, hit, tuple(H17.split(",")))
        ck("`limit`／`shares` 這一天真的整欄空白 ⇒ 被挑出來",
           {"limit", "shares"} <= set(blanks), str(blanks))
        ck("⛔ 有值的欄不可以被挑出來"
           "（`close`／`volume`／`last_price`／`change`）",
           not ({"close", "volume", "last_price", "change"} & set(blanks)),
           str(blanks))
        ck("⭐ 而 `last_price` **不在**整欄空白清單裡 ⇒ "
           "⛔ 這一支不會把「只有一群有值」報成空欄",
           "last_price" not in blanks, str(blanks))

        print("── ⑦ ⛔ 反向：證明這些判準會紅 ──")
        # (a) 若「有值」誤把 `0` 當空 ⇒ volume 會變 3／4
        bad_hit = {k: v for k, v in hit.items()}
        bad_hit["volume"] = 3
        ck("　反向：把 `0` 當成空值時，③ 那條**確實**會失敗",
           bad_hit["volume"] != 4, "⛔ 這條斷言連錯的都說對 ⇒ 它是死的")
        # (b) 若只看全檔不看逐群 ⇒ ⑤ 分不出設計與缺陷
        ck("　反向：只有全檔百分比時，⑤ **分不出**是設計還是缺陷"
           "（25% 這個數字本身不帶任何資訊）",
           rate_all == 0.25 and (e_hit / e_n) != rate_all,
           f"全檔 {rate_all}, emerging {e_hit}/{e_n}")
        # (c) 版本偵測：只有一種表頭時**不可以**回報多版本
        d2 = os.path.join(sand, "one")
        os.makedirs(d2)
        w(os.path.join(d2, "2026-09-07.csv"), H16 + "\n")
        w(os.path.join(d2, "2026-09-08.csv"), H16 + "\n")
        ck("　反向：兩天同一個表頭 ⇒ **1** 個版本（⛔ 否則它天天假紅）",
           len(S.schema_versions(S.day_paths(d2))) == 1,
           str(len(S.schema_versions(S.day_paths(d2)))))
    finally:
        shutil.rmtree(sand, ignore_errors=True)

    print(f"\n[selftest] 通過 {_ok}｜失敗 {_bad}")
    return 1 if _bad else 0


if __name__ == "__main__":
    sys.exit(main())
