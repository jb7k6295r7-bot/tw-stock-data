#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""股本／發行股數（全市場）—— 補 `fetch.py` 拿不到的那一塊。

★ 為什麼要獨立一支：
  2026-09-03 稽核發現，`data/universe/daily/*.csv` 的 `shares` 欄**只有上櫃有值**
  （980/2,715）。上市 1,371 檔與興櫃 364 檔全空，因為 TWSE `MI_INDEX` 的欄位裡
  根本沒有發行股數（探針照抄的欄位清單可證），只有 TPEx 的 `otc` 端點有。

  沒有股本就算不出：**周轉率級距**、**三大法人佔股本比重**（`tw-technical-analysis`
  的驗證清單明文要求，不能只看張數）、**融資使用率**。
  等於上市股的籌碼面判讀少一條腿。

★ 為什麼不塞進每日流程：股本變動很慢（增資／減資才會動），**每天抓 1,700 次是浪費**。
  這支設計成每月跑一次，而且**可以分批續跑**。

用法
────
    python3 capital.py --probe
        對每一條候選端點各試一次，把 HTTP 狀態、位元組數、**實際欄位名**寫進
        data/meta/_capital_probe.txt。**先跑這個。**
        欄位名一律以探針照抄的為準，**不可照猜的寫死**——興櫃逐月端點連 `fields`
        鍵都沒有、只能靠 金額÷股數 反推欄位，就是前車之鑑。

    python3 capital.py --run
        ① 先從最新的 daily 檔把上櫃的發行股數**原地搬過來**（已經是官方值，不必再抓）
        ② 再試市場層端點補上市／興櫃
        ③ 還缺的寫進 data/meta/_capital_missing.txt，交給下一步

    python3 capital.py --finmind --limit 300
        用 FinMind 資產負債表的 OrdinaryShare 逐檔補齊剩下的。
        **已驗證可用**（追蹤股的 `_capital.csv` 就是這樣來的），代價是逐檔請求。
        有 --limit 與續跑，額度用完隔天再跑即可。

輸出：data/meta/capital.csv
    stock_id,name,market,capital,shares,par,source,asof
    capital ＝ 實收資本額（元）；shares ＝ 發行股數（股）
    par     ＝ 面額。端點有給就照抄，沒給又要推導股數時填 10 並在 note 標明
    source  ＝ 哪一條端點給的；asof ＝ 這一列是哪天寫的
    note    ＝ 驗算結果。`ok`＝ 股數×面額 與 實收資本額 對得起來；
              `mismatch:<比值>` ＝ **對不起來，這一檔的股數不要拿來算佔股本比重**；
              `derived:par=<面額>` ＝ 股數是用資本額推導的，不是官方股數
"""
import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

TPE = timezone(timedelta(hours=8))
UA = "Mozilla/5.0 (compatible; tw-stock-data-capital/1.0; +https://github.com/)"
_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
META_DIR = os.path.join(_ROOT, "meta")
UNI_DAILY = os.path.join(_ROOT, "universe", "daily")
OUT = os.path.join(META_DIR, "capital.csv")
PROBE = os.path.join(META_DIR, "_capital_probe.txt")
MISSING = os.path.join(META_DIR, "_capital_missing.txt")
STOCKS = os.path.join(META_DIR, "stocks.csv")

HEADER = ["stock_id", "name", "market", "capital", "shares", "par", "source", "asof",
          "note"]
FINMIND = "https://api.finmindtrade.com/api/v4/data"

# 面額。**台股 2014 年起開放彈性面額**，所以 capital/10 不是永遠對的。
# → 只有在「拿不到股數、只拿得到資本額」時才用，而且會把 par 寫進檔案裡，
#   讓下游看得出這一列是推導來的、不是官方股數。
PAR_DEFAULT = 10

# 只認這些 type（與 fetch.py 的 _CAPITAL_TYPES 同一份，改一邊記得改另一邊）
_CAPITAL_TYPES = ("OrdinaryShare", "CommonStock", "CommonStocks", "CapitalStock",
                  "ShareCapital", "Capital")

# 端點候選。**這裡列的是「要去試什麼」，不是「已知可用」**——通不通由 --probe 說了算。
CANDIDATES = [
    ("twse-opendata-L", "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"),
    ("twse-mopsfin-L", "https://openapi.twse.com.tw/v1/mopsfin_t187ap03_L"),
    ("tpex-mopsfin-O", "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O"),
    ("tpex-opendata-O", "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_basic_info"),
    ("tpex-mopsfin-R", "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_R"),
    ("tpex-esb-basic", "https://www.tpex.org.tw/openapi/v1/tpex_esb_basic_info"),
]

# 欄位名靠關鍵字比對，不寫死——各端點的中英文命名不一致。
_K_CODE = ("公司代號", "證券代號", "股票代號", "SecuritiesCompanyCode", "Code", "代號")
_K_NAME = ("公司名稱", "公司簡稱", "證券名稱", "CompanyName", "名稱")
_K_CAP = ("實收資本額", "資本額", "股本", "CapitalStock", "PaidInCapital", "Capital")
_K_SHR = ("發行股數", "已發行股數", "IssuedShares", "OutstandingShares", "Shares")
# ★ 面額一定要抓。2026-09-03 實測興櫃 364 檔：345 檔是面額 10，
#   但 2245／6473 是 5 元、6696／6912 是 1 元，還有 6876（比值 16.86）、
#   6932（0.25）兩檔**怎麼算都對不起來**。
#   假設面額一律 10 會讓這 19 檔的股本算錯，而錯的方向與幅度各不相同——
#   直接影響「三大法人佔股本比重」，那正是 skill 的必檢項。
_K_PAR = ("ParValueOfCommonStock", "普通股每股面額", "每股面額", "面額", "ParValue")
# ★ 特別股要一起抓。2026-09-03 實測 40 筆「對不起來」，其中金控股一整排
#   （富邦金 11.142、國泰金 11.045、凱基金 10.932、台新新光金 11.788…）比值都在
#   10～12 之間——因為**實收資本額含特別股，已發行普通股數不含**。
#   驗算：富邦金 156,073,549,520 −(14,007,364,952×10) = 15,999,900,000
#   ÷10 = 1,599,990,000 股，正是它的特別股股數。
#   不抓這一欄的話，這些公司會被誤標成資料異常，而它們其實完全正常。
_K_PREF = ("PreferredStock.shares", "特別股", "PreferredShares")


def now_tpe():
    return datetime.now(TPE)


def get(url, retries=2, timeout=40):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA, "Accept": "application/json,text/plain,*/*"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(), None
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read()[:200].decode("utf-8", "replace")
            except Exception:  # noqa: BLE001
                pass
            last = f"HTTP {e.code} {body}"
        except Exception as e:  # noqa: BLE001
            last = f"{type(e).__name__}: {e}"
        time.sleep(1.5 * (i + 1))
    return None, last


def _num(v):
    if v is None:
        return ""
    t = str(v).replace(",", "").replace("+", "").strip()
    if t in ("", "-", "--", "N/A", "null", "None"):
        return ""
    try:
        float(t)
    except ValueError:
        return ""
    return t


def _pick(keys, wanted):
    """回傳第一個「含有」關鍵字的 key。先試完全相等，再試包含。"""
    for w in wanted:
        for k in keys:
            if str(k).strip() == w:
                return k
    for w in wanted:
        for k in keys:
            if w in str(k):
                return k
    return None


def reconcile(capital, shares, par, pref=""):
    """股數 × 面額 應該等於實收資本額。→ (par_used, note)

    ★ 對不起來就要標出來，不要挑一個好看的用。2026-09-03 實測興櫃有兩檔
      （6876 比值 16.86、6932 比值 0.25）**用任何一種面額都湊不出來**——
      那代表官方那兩欄本身就不一致，這種列拿去算佔股本比重會靜默算錯。
    """
    try:
        cap = float(capital) if capital else 0.0
        shr = float(shares) if shares else 0.0
        pv = float(par) if par else 0.0
        pf = float(pref) if pref else 0.0
    except ValueError:
        return (par or ""), "unparsable"
    if shr <= 0:
        return (par or ""), "no-shares"
    if cap <= 0:
        return (par or ""), "no-capital"
    if pv > 0:
        if abs(shr * pv - cap) / cap <= 0.05:
            return par, "ok"
        # 加上特別股再試一次
        if pf > 0 and abs((shr + pf) * pv - cap) / cap <= 0.05:
            return par, "ok(含特別股)"
        # ★ 這裡本來還有一段「差額若是面額的整數倍就推測為特別股」——**已刪除**。
        #   數字一大，任何差額除以 10 都會接近整數，那個檢定等於恆真：
        #   實測連 6876 朗齊（比值 16.86、真的有問題的那一檔）都會被判成正常，
        #   還附上一個看起來很合理的「特別股 48,413,091 股」。
        #   **憑空生出一個聽起來合理的解釋，比直接說「對不起來」危險得多。**
        #   兩個端點本來就有特別股欄位，拿不到就老實標 mismatch。
        return par, f"mismatch:{cap / shr:.3f}"
    # 端點沒給面額 → 回推一個，看看像不像常見面額
    implied = cap / shr
    for cand in (10, 5, 1, 0.1):
        if abs(implied - cand) / cand <= 0.05:
            return str(cand), "ok"
    return "", f"mismatch:{implied:.3f}"


def _read_out():
    rows = {}
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            rd = csv.reader(f)
            head = next(rd, None)
            if head and head != HEADER:
                raise ValueError(f"{OUT} 欄位不符：{head}")
            for q in rd:
                if q and q[0]:
                    rows[q[0]] = (q + [""] * len(HEADER))[:len(HEADER)]
    return rows


def _write_out(rows):
    os.makedirs(META_DIR, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(",".join(HEADER) + "\n")
        for k in sorted(rows):
            f.write(",".join(str(x).replace(",", "") for x in rows[k]) + "\n")
    return len(rows)


def _latest_daily():
    """最新的 data/universe/daily/*.csv。沒有就回 None。"""
    if not os.path.isdir(UNI_DAILY):
        return None
    fs = sorted(x for x in os.listdir(UNI_DAILY) if x.endswith(".csv"))
    return os.path.join(UNI_DAILY, fs[-1]) if fs else None


def load_universe():
    """→ {code: (name, market, shares_from_feed)}。以最新 daily 檔為準。"""
    p = _latest_daily()
    out = {}
    if not p:
        return out, None
    with open(p, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[r["stock_id"]] = (r.get("name", ""), r.get("market", ""),
                                  (r.get("shares") or "").strip())
    return out, os.path.basename(p)[:-4]


# ────────────────────────────────────────────── 市場層端點

def parse_market(raw, tag):
    """→ (dict{code: (name, capital, shares, par, pref)}, note)。看不懂就回空並照抄欄位名。"""
    try:
        d = json.loads(raw.decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        return {}, f"JSON 解析失敗 {type(e).__name__}"
    if isinstance(d, dict):
        for k in ("data", "aaData", "result"):
            if isinstance(d.get(k), list):
                d = d[k]
                break
    if not isinstance(d, list) or not d or not isinstance(d[0], dict):
        return {}, f"回傳不是 list[dict]（{type(d).__name__}）"
    keys = list(d[0].keys())
    k_code = _pick(keys, _K_CODE)
    k_name = _pick(keys, _K_NAME)
    k_cap = _pick(keys, _K_CAP)
    k_shr = _pick(keys, _K_SHR)
    k_par = _pick(keys, _K_PAR)
    k_pref = _pick(keys, _K_PREF)
    note = (f"欄位={keys}\n    對應 code={k_code} name={k_name} "
            f"cap={k_cap} shares={k_shr} par={k_par} pref={k_pref}")
    if not k_code or not (k_cap or k_shr):
        # ★ 對不上不要靜默放棄：把真正的欄位名留下來，下次照著改 _K_* 就好
        return {}, note + "\n    ✗ 找不到代號或（資本額／股數），本條不採用"
    out = {}
    for r in d:
        code = str(r.get(k_code, "")).strip()
        if not code or not code[0].isdigit():
            continue
        out[code] = (str(r.get(k_name, "")).strip(),
                     _num(r.get(k_cap)) if k_cap else "",
                     _num(r.get(k_shr)) if k_shr else "",
                     _num(r.get(k_par)) if k_par else "",
                     _num(r.get(k_pref)) if k_pref else "")
    return out, note + f"\n    解析出 {len(out)} 檔"


def cmd_probe(_args):
    lines = [f"# 股本端點偵察 {now_tpe().isoformat(timespec='seconds')}"]
    for tag, url in CANDIDATES:
        raw, err = get(url, retries=1)
        if err:
            lines.append(f"\n== {tag} FAIL {url}\n    {err}")
            continue
        got, note = parse_market(raw, tag)
        lines.append(f"\n== {tag} OK   {url}\n    bytes={len(raw)}\n    {note}")
        if got:
            k = sorted(got)[0]
            lines.append(f"    首筆照抄：{k} {got[k]}")
    os.makedirs(META_DIR, exist_ok=True)
    with open(PROBE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


def cmd_run(_args):
    today = now_tpe().strftime("%Y-%m-%d")
    uni, day = load_universe()
    if not uni:
        print("[capital] 找不到 data/universe/daily/*.csv，先跑 fetch.py", file=sys.stderr)
        return 1
    rows = _read_out()
    print(f"[capital] universe={len(uni)} 檔（{day}）｜既有 capital.csv {len(rows)} 列")

    # ① 上櫃：daily 檔裡已經有官方發行股數，直接搬，不要再抓
    moved = 0
    for code, (name, market, shares) in uni.items():
        if shares:
            rows[code] = [code, name, market, "", shares, "",
                           f"universe:{day}", today, "feed-shares"]
            moved += 1
    print(f"  ① 從 daily 搬進來的官方發行股數：{moved} 檔")

    # ② 市場層端點
    filled, notes = 0, []
    for tag, url in CANDIDATES:
        need = [c for c in uni if not (rows.get(c, [""] * len(HEADER))[4])]
        if not need:
            break
        raw, err = get(url, retries=1)
        if err:
            notes.append(f"{tag} FAIL {err}")
            continue
        got, note = parse_market(raw, tag)
        notes.append(f"{tag} {note.splitlines()[0]}")
        hit, bad = 0, 0
        for code in need:
            if code not in got:
                continue
            _legal, cap, shr, par, pref = got[code]
            # 名稱一律用 universe 的簡稱，不用端點的公司全名——
            # 報告與其他檔案都是簡稱，混用會讓 join 對不上。
            name = uni[code][0] or _legal
            if shr:
                par_used, nt = reconcile(cap, shr, par, pref)
                rows[code] = [code, name, uni[code][1], cap, shr, par_used,
                              tag, today, nt]
            elif cap:
                # 只拿得到資本額 → 推導股數。**par 與 derived 標記一定要寫出來**
                pv = float(par) if par else PAR_DEFAULT
                rows[code] = [code, name, uni[code][1], cap,
                              str(int(float(cap) // pv)), str(pv), tag, today,
                              f"derived:par={pv:g}"]
            else:
                continue
            hit += 1
            if rows[code][8].startswith("mismatch"):
                bad += 1
        filled += hit
        print(f"  ② {tag}: 補到 {hit} 檔（其中 {bad} 檔股數與資本額對不起來）")

    total = _write_out(rows)
    miss = sorted(c for c in uni if not rows.get(c, [""] * len(HEADER))[4])
    os.makedirs(META_DIR, exist_ok=True)
    with open(MISSING, "w", encoding="utf-8") as f:
        f.write(f"# {today} 仍缺股數 {len(miss)} 檔（下一步：capital.py --finmind）\n")
        for c in miss:
            f.write(f"{c},{uni[c][0]},{uni[c][1]}\n")
    print(f"[capital] 落檔 {total} 列｜仍缺 {len(miss)} 檔 → {MISSING}")
    for n in notes:
        print("   ", n)
    return 0


# ────────────────────────────────────────────── FinMind 逐檔補

def finmind_shares(code):
    """→ (capital元, date, err)。用資產負債表的普通股股本。"""
    end = now_tpe().strftime("%Y-%m-%d")
    start = (now_tpe() - timedelta(days=800)).strftime("%Y-%m-%d")
    url = (f"{FINMIND}?dataset=TaiwanStockBalanceSheet&data_id={code}"
           f"&start_date={start}&end_date={end}")
    raw, err = get(url, retries=2)
    if err:
        return "", "", err
    try:
        d = json.loads(raw.decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        return "", "", f"JSON {type(e).__name__}"
    data = d.get("data") or []
    if not data:
        return "", "", "0 筆"
    # ★ 照抄 stock_id 核對——FinMind 實測會靜默回傳前一檔的資料（2026-08-30）
    got_id = str(data[0].get("stock_id", "")).strip()
    if got_id and got_id != str(code):
        return "", "", f"stock_id 不符（要 {code}、回 {got_id}）"
    by = {}
    for r in data:
        t, dt, v = str(r.get("type", "")), str(r.get("date", "")), _num(r.get("value"))
        if t and dt and v:
            by.setdefault(t, []).append((dt, v))
    pick = next((t for t in _CAPITAL_TYPES if t in by), None)
    if not pick:
        return "", "", f"科目對不上：{sorted(by)[:12]}"
    dt, v = sorted(by[pick])[-1]
    return v, dt, ""


def cmd_finmind(args):
    today = now_tpe().strftime("%Y-%m-%d")
    uni, _day = load_universe()
    rows = _read_out()
    need = [c for c in sorted(uni) if not rows.get(c, [""] * len(HEADER))[4]]
    if args.limit:
        need = need[:args.limit]
    print(f"[finmind] 這一趟處理 {len(need)} 檔（間隔 {args.sleep}s，"
          f"約 {len(need) * args.sleep / 60:.0f} 分鐘）")
    ok = fail = 0
    errs = {}
    for i, code in enumerate(need, 1):
        cap, dt, err = finmind_shares(code)
        if err:
            fail += 1
            errs[code] = err
            # ★ 連續失敗多半是額度用完，繼續打只是浪費——收手，下次續跑
            if fail >= 20 and ok == 0:
                print(f"  連續 {fail} 次失敗且無一成功，收手（最後：{err}）")
                break
        else:
            rows[code] = [code, uni[code][0], uni[code][1], cap,
                          str(int(float(cap) // PAR_DEFAULT)), str(PAR_DEFAULT),
                          f"finmind:{dt}", today,
                          f"derived:par={PAR_DEFAULT}"]
            ok += 1
        if i % 50 == 0:
            _write_out(rows)          # 中途落檔：跑一半被砍也不會全白做
            print(f"  {i}/{len(need)}　成功 {ok}／失敗 {fail}", flush=True)
        time.sleep(args.sleep)
    total = _write_out(rows)
    miss = sorted(c for c in uni if not rows.get(c, [""] * len(HEADER))[4])
    with open(MISSING, "w", encoding="utf-8") as f:
        f.write(f"# {today} 仍缺股數 {len(miss)} 檔\n")
        for c in miss:
            f.write(f"{c},{uni[c][0]},{uni[c][1]}\n")
    print(f"[finmind] 成功 {ok}｜失敗 {fail}｜capital.csv {total} 列｜仍缺 {len(miss)}")
    for c, e in list(errs.items())[:10]:
        print(f"    {c}: {e}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true", help="只測端點、照抄欄位名")
    ap.add_argument("--run", action="store_true", help="搬上櫃股數＋試市場層端點")
    ap.add_argument("--finmind", action="store_true", help="逐檔補剩下的")
    ap.add_argument("--limit", type=int, default=0, help="--finmind 這一趟最多幾檔")
    ap.add_argument("--sleep", type=float, default=6.0, help="--finmind 每檔間隔秒數")
    args = ap.parse_args()
    if args.probe:
        return cmd_probe(args)
    if args.run:
        return cmd_run(args)
    if args.finmind:
        return cmd_finmind(args)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
