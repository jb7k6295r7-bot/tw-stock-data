# -*- coding: utf-8 -*-
"""NYSE 交易日（規則版，只用 datetime；給 run_c3s_month.sh 的快速判斷用，幾十毫秒內回）。

    python c3sm_cal.py prevme 2026-12-01     # ⇒ 上一個日曆月最後一個 NYSE 交易日（2026-11-30）
    python c3sm_cal.py next 2026-11-30 20    # ⇒ 之後 20 個交易日（一行一個；注入假列用）
    python c3sm_cal.py selftest <yahoo_GSPC.csv>   # 2016-01～該檔前一個完整月：規則月底 ＝ 資料月底

休市規則（NYSE 常規）：元旦（週日 ⇒ 週一；週六 ⇒ 不補休）、MLK（1 月第 3 個週一）、總統日（2 月第 3 個週一）、耶穌受難日（復活節前 2 天）、
陣亡將士（5 月最後週一）、六月節（2022 起，週六 ⇒ 週五、週日 ⇒ 週一）、獨立日、勞動節（9 月第 1 個週一）、感恩節（11 月第 4 個週四）、聖誕（週六 ⇒ 週五、週日 ⇒ 週一）。
⚠ 臨時休市（國喪、天災）規則算不到 ⇒ run_c3s_month.sh 在資料進來後再用 ^GSPC 日期覆核月底（有下月資料時以資料為準）。
"""
import sys
from datetime import date, timedelta


def _nth(y, m, wd, k):
    d = date(y, m, 1)
    d += timedelta((wd - d.weekday()) % 7)
    return d + timedelta(7 * (k - 1))


def _last(y, m, wd):
    d = date(y + (m == 12), m % 12 + 1, 1) - timedelta(1)
    return d - timedelta((d.weekday() - wd) % 7)


def _easter(y):
    a = y % 19; b = y // 100; c = y % 100; d = b // 4; e = b % 4; f = (b + 8) // 25; g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30; i = c // 4; k = c % 4; l_ = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_) // 451
    mo = (h + l_ - 7 * m + 114) // 31; da = (h + l_ - 7 * m + 114) % 31 + 1
    return date(y, mo, da)


def _obs(d):
    return d - timedelta(1) if d.weekday() == 5 else (d + timedelta(1) if d.weekday() == 6 else d)


def holidays(y):
    H = set()
    nd = date(y, 1, 1)
    if nd.weekday() == 6:
        H.add(nd + timedelta(1))
    elif nd.weekday() != 5:
        H.add(nd)
    H |= {_nth(y, 1, 0, 3), _nth(y, 2, 0, 3), _easter(y) - timedelta(2), _last(y, 5, 0), _obs(date(y, 7, 4)),
          _nth(y, 9, 0, 1), _nth(y, 11, 3, 4), _obs(date(y, 12, 25))}
    if y >= 2022:
        H.add(_obs(date(y, 6, 19)))
    return H


def is_trading(d):
    return d.weekday() < 5 and d not in holidays(d.year)


def month_end(y, m):
    d = date(y + (m == 12), m % 12 + 1, 1) - timedelta(1)
    while not is_trading(d):
        d -= timedelta(1)
    return d


def prev_month_end(today):
    y, m = (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)
    return month_end(y, m)


def next_days(d, k):
    out = []
    while len(out) < k:
        d += timedelta(1)
        if is_trading(d):
            out.append(d)
    return out


def _d(s):
    return date.fromisoformat(s[:10])


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "prevme":
        print(prev_month_end(_d(sys.argv[2])).isoformat())
    elif cmd == "next":
        print("\n".join(x.isoformat() for x in next_days(_d(sys.argv[2]), int(sys.argv[3]))))
    elif cmd == "selftest":
        ds = sorted({ln.split(",")[0] for ln in open(sys.argv[2], encoding="utf-8").read().splitlines()[1:] if ln[:4].isdigit()})
        last = {}
        for s in ds:
            last[s[:7]] = s
        months = sorted(k for k in last if k >= "2016-01")[:-1]
        bad = [(k, last[k], month_end(int(k[:4]), int(k[5:])).isoformat()) for k in months if last[k] != month_end(int(k[:4]), int(k[5:])).isoformat()]
        print(f"月數 {len(months)}；不同 {len(bad)}：{bad}")
        sys.exit(1 if bad else 0)
    else:
        raise SystemExit(f"未知指令 {cmd}")
