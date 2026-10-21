# -*- coding: utf-8 -*-
"""⚠ 修正後資料、非當時公布值 ⚠ —— 國發會景氣指標與景氣對策信號（月頻）⇒ ndc_signal.csv（只供描述）

    python3 curated/ndc_signal/build.py

依據：台股 seq533 §二 B（資料庫線子代理 2026-10-21）。
來源（官方）：政府資料開放平臺 data.gov.tw 資料集 6099「景氣指標及燈號」（國家發展委員會），
  metadata `https://data.gov.tw/api/v2/rest/dataset/6099` 的 distribution[0].resourceDownloadUrl
  ＝ `https://ws.ndc.gov.tw/Download.ashx?u=…&n=…`（ZIP，內含 景氣指標與燈號.csv 等 5 個 CSV＋schema）。
  ⭐ 每次執行先問 metadata 拿下載網址（網址內含檔案 GUID，換版可能會變）；ZIP 只在記憶體讀，⛔ 不解壓到磁碟。
⛔⛔ 口徑：資料集說明逐字「每月發布時回溯修正領先、同時及落後指標的歷史資料」
  ⇒ 本檔每一列都是【建置當下這一版】的值，⛔ 不是該月當時公布的燈號／分數；拿來做回測訊號會有前視。
  當時公布值只在國發會每月「景氣概況」新聞稿（PDF）裡，本檔⛔ 不抓。
輸出欄：period(YYYY-MM), leading_index, leading_detrended, coincident_index, coincident_detrended,
        lagging_index, lagging_detrended, signal_score, signal_light（紅／黃紅／綠／黃藍／藍，官方原字）, vintage
  vintage＝ZIP 內 景氣指標與燈號.csv 的檔案時間（＝這一版的修訂時點）。官方 '-' ⇒ 留空（⛔ 不填 0）。
自檢（只印不擋）：每種燈號的分數範圍（燈號門檻歷年改過，⛔ 不用現行門檻回推舊燈號）。
"""
import csv, datetime, io, json, os, sys, urllib.request, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "ndc_signal.csv")
META = "https://data.gov.tw/api/v2/rest/dataset/6099"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
SRC = ["Date", "領先指標綜合指數", "領先指標不含趨勢指數", "同時指標綜合指數", "同時指標不含趨勢指數",
       "落後指標綜合指數", "落後指標不含趨勢指數", "景氣對策信號綜合分數", "景氣對策信號"]
COLS = ["period", "leading_index", "leading_detrended", "coincident_index", "coincident_detrended",
        "lagging_index", "lagging_detrended", "signal_score", "signal_light", "vintage"]
TARGET = "景氣指標與燈號.csv"


def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=90).read()


def zname(i):
    try:
        return i.filename.encode("cp437").decode("cp950")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return i.filename


def main():
    m = json.loads(get(META)).get("result", {})
    dist = [d for d in m.get("distribution", []) if str(d.get("resourceFormat", "")).upper() == "ZIP"]
    if not dist:
        print(f"⛔ metadata 沒有 ZIP 分發：{m.get('distribution')}"); return 1
    print(f"資料集：{m.get('title')}｜說明：{dist[0].get('resourceDescription')}")
    b = get(dist[0]["resourceDownloadUrl"])
    if b[:2] != b"PK":
        print(f"⛔ 回的不是 ZIP（開頭 {b[:60]!r}）"); return 1
    z = zipfile.ZipFile(io.BytesIO(b))
    info = next((i for i in z.infolist() if zname(i) == TARGET), None)
    if info is None:
        print(f"⛔ ZIP 裡沒有 {TARGET}：{[zname(i) for i in z.infolist()]}"); return 1
    vintage = datetime.datetime(*info.date_time).strftime("%Y-%m-%d %H:%M")
    rows = list(csv.reader(io.StringIO(z.read(info).decode("utf-8-sig"))))
    if rows[0] != SRC:
        print(f"⛔ 欄位對不上：{rows[0]}"); return 1
    out, rng = [], {}
    for r in rows[1:]:
        if not r or not r[0].strip():
            continue
        p = r[0].strip()
        if len(p) != 6 or not p.isdigit():
            print(f"⛔ 期別格式怪：{r[:2]}"); return 1
        v = ["" if x.strip() in ("-", "") else x.strip() for x in r[1:]]
        out.append([f"{p[:4]}-{p[4:]}"] + v + [vintage])
        if v[6] and v[7]:
            rng.setdefault(v[7], []).append(int(float(v[6])))
    periods = [o[0] for o in out]
    if periods != sorted(set(periods)):
        print("⛔ 期別重複或未排序"); return 1
    with io.open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(COLS); w.writerows(out)
    sig = [o for o in out if o[8]]
    print(f"⭐ {len(out)} 期 {periods[0]} ~ {periods[-1]}｜有燈號 {len(sig)} 期 {sig[0][0]} ~ {sig[-1][0]}｜vintage {vintage}")
    for k in ("紅", "黃紅", "綠", "黃藍", "藍"):
        if k in rng:
            print(f"  {k}：{len(rng[k])} 期，分數 {min(rng[k])}～{max(rng[k])}")
    extra = set(rng) - {"紅", "黃紅", "綠", "黃藍", "藍"}
    if extra:
        print(f"  ⚠ 其他燈號字：{extra}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
