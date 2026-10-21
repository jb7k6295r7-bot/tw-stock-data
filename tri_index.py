# -*- coding: utf-8 -*-
"""臺灣發行量加權股價【報酬指數】（含息）日線 ⇒ data/history/market_tri.csv

    python3 tri_index.py                       # 每日：重抓上個月與本月
    python3 tri_index.py --start 2003-01       # 回補（官方最早 2003-01-02）
    python3 tri_index.py --start 2026-09 --end 2026-10 --dry

依據：裁定 seq425（2026-10-21，使用者指示台股判準基準由 0050 改為大盤；裁定定用含息的報酬指數）；回測 1021-1510 等件。
來源：TWSE `rwd/zh/TAIEX/MFI94U?date=YYYYMM01&response=json`（一發一個月，官方）。
  ⚠ 報酬指數 2003-01-02 才開始編（2026-10-21 實測 92/01 有、更早沒有）⇒ 2003 年以前只有價格指數（market_index.csv）。
欄：date, close（指數點數，去千分位）。
⛔ 合併寫入：既有列只會被同日新值取代，⛔ 不刪列；值有變動的印出來（官方極少回頭改）。
⛔ 驗收：抓到的每個月，交易日要與 `data/history/market_index.csv`（價格指數）同月的日期完全相同，不同就結束碼 1、不寫檔。
"""
import argparse, csv, datetime, io, json, os, sys, time, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "data", "history", "market_tri.csv")
PX = os.path.join(ROOT, "data", "history", "market_index.csv")
URL = "https://www.twse.com.tw/rwd/zh/TAIEX/MFI94U?date={ym}01&response=json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
FIRST = "2003-01"


def months(s, e):
    y, m = map(int, s.split("-"))
    ey, em = map(int, e.split("-"))
    while (y, m) <= (ey, em):
        yield "%04d-%02d" % (y, m)
        m += 1
        if m == 13:
            y, m = y + 1, 1


def fetch_month(ym, sleep):
    """→ [(YYYY-MM-DD, close)]；官方回「查無資料」⇒ []；其他錯誤重試 3 次後丟出。"""
    for i in range(3):
        try:
            time.sleep(sleep)
            raw = urllib.request.urlopen(urllib.request.Request(URL.format(ym=ym.replace("-", "")), headers=UA), timeout=60).read()
            d = json.loads(raw.decode("utf-8"))
            if d.get("stat") != "OK":
                if "沒有符合" in str(d.get("stat")) or "查無" in str(d.get("stat")):
                    return []
                raise RuntimeError(d.get("stat"))
            # ⛔ 參數回音防線：回應的 date 要是我送的那個月
            if str(d.get("date", ""))[:6] != ym.replace("-", ""):
                raise RuntimeError(f"回應月份 {d.get('date')} ≠ 要的 {ym}")
            out = []
            for r in d.get("data") or []:
                y, m, dd = r[0].strip().split("/")
                out.append(("%04d-%02d-%02d" % (int(y) + 1911, int(m), int(dd)), r[1].replace(",", "").strip()))
            return out
        except Exception as ex:  # noqa: BLE001
            print(f"  {ym} 重試 {i}：{ex}", flush=True)
            time.sleep(20)
    raise RuntimeError(f"{ym} 三次都失敗")


def main():
    ap = argparse.ArgumentParser()
    today = datetime.date.today()
    prev = (today.replace(day=1) - datetime.timedelta(days=1)).strftime("%Y-%m")
    ap.add_argument("--start", default=prev)
    ap.add_argument("--end", default=today.strftime("%Y-%m"))
    ap.add_argument("--sleep", type=float, default=4)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    start = max(a.start, FIRST)
    px = {}
    if os.path.exists(PX):
        for r in csv.DictReader(io.open(PX, encoding="utf-8")):
            px.setdefault(r["date"][:7], set()).add(r["date"])
    px_last = max((max(v) for v in px.values()), default="")
    old = {}
    if os.path.exists(OUT):
        for r in csv.DictReader(io.open(OUT, encoding="utf-8")):
            old[r["date"]] = r["close"]
    new, bad, changed = dict(old), [], []
    n = 0
    for ym in months(start, a.end):
        rows = fetch_month(ym, a.sleep)
        n += 1
        got = {d for d, _ in rows}
        want = px.get(ym, set())
        # 價格指數檔可能還沒更新到最近幾天 ⇒ 只比到它的最後一天
        got_cmp = {d for d in got if d <= px_last}
        if want and got_cmp != want:
            bad.append((ym, sorted(want - got_cmp)[:5], sorted(got_cmp - want)[:5]))
        for d, c in rows:
            if d in old and old[d] != c:
                changed.append((d, old[d], c))
            new[d] = c
        print(f"{ym} {len(rows)} 日" + ("" if not want or got_cmp == want else "  ⛔ 與價格指數交易日不同"), flush=True)
    print(f"抓 {n} 個月；既有 {len(old)} 列 ⇒ 合併後 {len(new)} 列；值有變動 {len(changed)} {changed[:5]}")
    if bad:
        print("⛔ 交易日與 market_index.csv 不同：", bad[:10])
        return 1
    if a.dry:
        print("（--dry，不寫檔）")
        return 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["date", "close"])
        for d in sorted(new):
            w.writerow([d, new[d]])
    print(f"⭐ 寫入 {OUT}：{min(new)}～{max(new)}，{len(new)} 列")
    return 0


if __name__ == "__main__":
    sys.exit(main())
