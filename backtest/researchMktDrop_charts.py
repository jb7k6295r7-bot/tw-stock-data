# -*- coding: utf-8 -*-
"""大跌 C+ 最好／最差走勢小圖（描述）——回測線計算子代理 2026-10-17。只讀、只寫新 HTML。"""
import io, os, subprocess, html, json
import numpy as np
import pandas as pd
from backtest import data as D
from backtest import research11 as R
from backtest import rerun17 as RR
from backtest import researchAddOn as RA

REPO = os.path.expanduser("~/tw-p17")
OUTD = os.path.join(REPO, "backtest/resultsMktDrop/charts")
OUT = os.path.join(OUTD, "大跌最好最差走勢.html")
FWDDATA = os.path.expanduser("~/h2data/740075ba40a8463c424cfa77b1f4b2b6096eb5ce/data")
PAD = 20
os.chdir(REPO)

# ── 指數 ──
sha = subprocess.run(["git", "rev-parse", "origin/main"], capture_output=True, text=True, check=True).stdout.strip()
raw = subprocess.run(["git", "show", f"{sha}:data/history/market_index.csv"], capture_output=True, check=True).stdout
IX = pd.read_csv(io.BytesIO(raw), dtype={"date": str})
IX["date"] = pd.to_datetime(IX["date"]); IX["close"] = pd.to_numeric(IX["close"], errors="coerce")
IX = IX.dropna(subset=["close"]).drop_duplicates("date").set_index("date")["close"].sort_index()

def names(data):
    s = pd.read_csv(os.path.join(data, "meta", "stocks.csv"), dtype=str).drop_duplicates("stock_id", keep="last").set_index("stock_id")
    return s["market"].to_dict(), s["name"].to_dict()

def series(sid, data, t_date, b_date, end_date, stop_at=None):
    """⇒ list of (日期, 還原收盤) 在 [t−20, end+20] 內、不跨壞根；cal；買進根還原開盤。"""
    D.DATA = data
    cal = D.load_calendar()
    mk, _ = names(data)
    B = R.load_bars(sid, mk.get(sid, "twse"), cal)
    if B is None:
        raise SystemExit(f"⛔ {sid} load_bars None")
    idx = np.asarray(B["idx"]); c = np.asarray(B["c"], float); o = np.asarray(B["o"], float)
    nb = len(idx); next_bad = np.asarray(B["next_bad"])
    bad = next_bad[:nb] == np.arange(nb)
    dates = pd.DatetimeIndex(cal[idx])
    kb = int(dates.searchsorted(b_date)); assert dates[kb] == b_date, (sid, b_date)
    kt = int(dates.searchsorted(t_date)); assert dates[kt] == t_date, (sid, t_date)
    pt = int(cal.searchsorted(t_date))
    lo_d = cal[max(pt - PAD, 0)]
    hi_d = cal[min(int(cal.searchsorted(end_date)) + PAD, len(cal) - 1)] if end_date is not None else cal[-1]
    k0 = int(dates.searchsorted(lo_d)); k1 = int(dates.searchsorted(hi_d, "right")) - 1
    # 不跨壞根：起點往後推到最後一個 ≤ kt 的壞根；終點截到 kb 之後第一個壞根之前
    cut_lo = k0; cut_hi = k1; notes = []
    for k in range(kt, k0 - 1, -1):
        if bad[k] and k <= kt:
            cut_lo = max(cut_lo, k); notes.append(f"事件前 {dates[k].date()} 有壞根，線從那天起畫"); break
    for k in range(kb + 1, k1 + 1):
        if bad[k]:
            cut_hi = k - 1; notes.append(f"{dates[k].date()} 是壞根（停牌缺口 ≥5 日或減資），線畫到之前最後一個成交日"); break
    if stop_at is not None:
        ks = int(dates.searchsorted(stop_at, "right")) - 1
        if ks < cut_hi:
            cut_hi = ks
            notes = [x for x in notes if "線畫到前一天" not in x] + ["壞根前強制賣，之後價格不可比，線只畫到出場日"]
    pts = [(dates[k], c[k]) for k in range(cut_lo, cut_hi + 1)]
    return pts, cal, o[kb], notes, (lo_d, hi_d)

def fmt_pct(x, d=1):
    return f"{x * 100:+.{d}f}%"

# ── SVG ──
W_, H_ = 320, 180
ML, MR, MT, MB = 34, 8, 10, 22

def svg(pts, ixpts, marks, lo_d, hi_d, kind):
    xs = [p[0] for p in pts]
    d0, d1 = lo_d, hi_d
    span = max((d1 - d0).days, 1)
    X = lambda d: ML + (W_ - ML - MR) * ((d - d0).days / span)
    vals = [v for _, v in pts] + [v for _, v in ixpts] + [100.0]
    ymin, ymax = min(vals), max(vals)
    pad = (ymax - ymin) * 0.06 or 5
    ymin -= pad; ymax += pad
    Y = lambda v: MT + (H_ - MT - MB) * (1 - (v - ymin) / (ymax - ymin))
    o = [f'<svg viewBox="0 0 {W_} {H_}" role="img" preserveAspectRatio="none" class="ch">']
    # 格線
    for v in nice_ticks(ymin, ymax):
        y = Y(v)
        o.append(f'<line x1="{ML}" x2="{W_ - MR}" y1="{y:.1f}" y2="{y:.1f}" class="{"base" if abs(v - 100) < 1e-9 else "grid"}"/>')
        o.append(f'<text x="{ML - 4}" y="{y + 3:.1f}" class="yl">{v:g}</text>')
    # 直線標記
    for lab, d, cls in marks:
        if d is None:
            continue
        x = X(d)
        o.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{MT}" y2="{H_ - MB}" class="{cls}"/>')
    # 指數、個股
    if ixpts:
        o.append('<polyline class="ix" points="' + " ".join(f"{X(d):.1f},{Y(v):.1f}" for d, v in ixpts) + '"/>')
    o.append(f'<polyline class="stk {kind}" points="' + " ".join(f"{X(d):.1f},{Y(v):.1f}" for d, v in pts) + '"/>')
    # x 軸標籤
    o.append(f'<text x="{ML}" y="{H_ - 6}" class="xl" text-anchor="start">{d0:%Y-%m-%d}</text>')
    o.append(f'<text x="{W_ - MR}" y="{H_ - 6}" class="xl" text-anchor="end">{d1:%Y-%m-%d}</text>')
    o.append("</svg>")
    return "".join(o)

def nice_ticks(a, b):
    rng = b - a
    for st in (5, 10, 20, 25, 50, 100):
        if rng / st <= 5:
            break
    t0 = np.ceil(a / st) * st
    return [float(v) for v in np.arange(t0, b + 1e-9, st)]

def card(title, sub, svgs, notes):
    n = "".join(f'<p class="nt">{html.escape(x)}</p>' for x in notes)
    return f'<figure class="card"><figcaption><b>{html.escape(title)}</b><span>{html.escape(sub)}</span></figcaption>{svgs}{n}</figure>'

def ix_pts(lo, hi, b_date):
    s = IX[(IX.index >= lo) & (IX.index <= hi)]
    if b_date not in IX.index:
        return []
    base = IX.loc[b_date]
    return [(d, v / base * 100) for d, v in s.items()]

# ── 一、歷史 C+ ──
C = pd.read_csv("backtest/resultsMktDrop/deep/c_rows.csv", dtype={"sid": str})
P = C[(C["yoy"] > 0) & (C["買得到"] == True)].copy()
P = P.sort_values(["淨報酬", "事件日", "sid"], kind="stable").reset_index(drop=True)
stat = {"C+ 買得到檔次": len(P), "逐筆平均": float(P["淨報酬"].mean()), "逐筆中位": float(P["淨報酬"].median()),
        "事件等權平均": float(P.groupby("事件日")["淨報酬"].mean().mean()), "事件數": int(P["事件日"].nunique())}
best = P.tail(6).iloc[::-1]; worst = P.head(6)
H_cards = {"best": [], "worst": []}; LIST = {"best": [], "worst": []}
_, NM_main = names(RR.H2D); _, NM_early = names(RA.EOTC); _, NM_fwd = names(FWDDATA)
for key, G in (("best", best), ("worst", worst)):
    for _, r in G.iterrows():
        t = pd.Timestamp(r["事件日"]); s_ = pd.Timestamp(r["賣出日"])
        data = RA.EOTC if t.year < 2015 else RR.H2D
        D.DATA = data; cal = D.load_calendar()
        b = cal[int(cal.searchsorted(t)) + 1]
        pts, cal, bo, notes, (lo, hi) = series(r["sid"], data, t, b, s_,
                                               stop_at=(None if r["出場種類"] == "規則賣（開盤）" else s_))
        # 賣價對帳：還原收盤（強制）或還原開盤（規則）
        sc = dict(pts).get(s_)
        if r["出場種類"] != "規則賣（開盤）" and sc is not None and abs(sc / r["賣價"] - 1) > 1e-4:
            raise SystemExit(f"⛔ {r['sid']} 強制賣價對不上 {sc} vs {r['賣價']}")
        if abs(bo / r["買價"] - 1) > 1e-4:
            raise SystemExit(f"⛔ {r['sid']} 買價對不上 {bo} vs {r['買價']}")
        # 賣價對帳（開盤賣 ⇒ 還原開盤；強制 ⇒ 還原收盤）
        pts = [(d, v / bo * 100) for d, v in pts]
        nm = NM_fwd.get(r["sid"]) or NM_main.get(r["sid"]) or NM_early.get(r["sid"]) or ""
        ix = ix_pts(lo, hi, b)
        kd = r["出場種類"]
        if kd != "規則賣（開盤）":
            notes = [f"出場種類：{kd}（之後停牌缺口 ≥5 日，線畫到出場日為止）"] + [x for x in notes if "線畫到之前" not in x]
        title = f"{r['sid']} {nm}"
        sub = (f"事件 {t:%Y-%m-%d}｜報酬 {fmt_pct(r['淨報酬'])}｜持有 {int(r['持有天數'])} 個交易日｜"
               f"當天 {fmt_pct(r['ret1'])}｜營收年增 {fmt_pct(r['yoy'], 2 if abs(r['yoy']) < 0.01 else 1)}")
        marks = [("大跌", t, "mk-ev"), ("買進", b, "mk-buy"), ("出場", s_, "mk-exit")]
        H_cards[key].append(card(title, sub, svg(pts, ix, marks, lo, hi, key), notes))
        LIST[key].append({"代號": r["sid"], "名稱": nm, "事件日": f"{t:%Y-%m-%d}", "報酬": float(r["淨報酬"]),
                          "持有天數": int(r["持有天數"]), "出場": kd, "賣出日": f"{s_:%Y-%m-%d}"})

# ── 二、前瞻 2026-10-15 ──
POS = pd.read_csv("backtest/forward/mktdrop/positions.csv", dtype={"代號": str}, encoding="utf-8-sig")
POS = POS[(POS["候選"] == "C+") & (POS["事件日"] == "2026-10-15")]
CAN = pd.read_csv("backtest/forward/mktdrop/candidates_20261015.csv", dtype={"代號": str}, encoding="utf-8-sig")
CAN = CAN[CAN["候選"] == "C+"].set_index("代號")
D.DATA = FWDDATA; calF = D.load_calendar()
tF = pd.Timestamp("2026-10-15"); bF = pd.Timestamp("2026-10-16")
from backtest import mktdrop_fwd as MF
mkF, _ = names(FWDDATA)
rows = []
for _, r in POS.iterrows():
    sid = r["代號"]
    A = MF.one(sid, mkF.get(sid, "twse"), calF, FWDDATA)
    e = int(calF.searchsorted(bF)); last = len(calF) - 1
    ac = A["ac"]; ao = A["ao"]
    j = last
    while j > e and not np.isfinite(ac[j]):
        j -= 1
    if not (np.isfinite(ao[e]) and ao[e] > 0) or abs(A["ro"][e] / float(r["買進價"]) - 1) > 1e-6:
        raise SystemExit(f"⛔ {sid} 買進價對不上")
    rows.append({"sid": sid, "name": r["名稱"], "bk": ac[j] / ao[e] - 1, "ao": ao[e], "asof": calF[j]})
F = pd.DataFrame(rows).sort_values(["bk", "sid"], kind="stable").reset_index(drop=True)
fstat = {"檔數": len(F), "帳面等權平均（未扣成本）": float(F["bk"].mean()), "帳面中位": float(F["bk"].median()), "資料日": f"{calF[-1]:%Y-%m-%d}"}
FB = F.tail(5).iloc[::-1]; FW = F.head(5)
F_cards = {"best": [], "worst": []}
for key, G in (("best", FB), ("worst", FW)):
    for _, r in G.iterrows():
        pts, cal, bo, notes, (lo, hi) = series(r["sid"], FWDDATA, tF, bF, None)
        pts = [(d, v / bo * 100) for d, v in pts]
        hi = calF[-1]
        ix = ix_pts(lo, hi, bF)
        cr = CAN.loc[r["sid"]]
        hold = int(calF.searchsorted(hi)) - int(calF.searchsorted(bF)) + 1
        sub = (f"事件 2026-10-15｜帳面 {fmt_pct(r['bk'])}（未扣成本）｜已持有 {hold} 個交易日｜"
               f"當天 {fmt_pct(cr['當日報酬'])}｜營收年增 {fmt_pct(cr['年增'])}（{cr['營收期別']}）")
        marks = [("大跌", tF, "mk-ev"), ("買進", bF, "mk-buy")]
        F_cards[key].append(card(f"{r['sid']} {r['name']}", sub, svg(pts, ix, marks, lo, hi, key), notes))
        LIST.setdefault("f" + key, []).append({"代號": r["sid"], "名稱": r["name"], "事件日": "2026-10-15", "帳面": float(r["bk"])})

# ── HTML ──
CSS = """
:root{--bg:#fbfaf7;--fg:#1f2328;--mut:#5d6470;--card:#ffffff;--bd:#e3e0d8;--grid:#ebe8e1;--base:#b9b4a8;
--best:#1f7a4d;--worst:#b4372f;--ix:#8f96a3;--ev:#c27c0e;--buy:#2f6fb5;--exit:#7a4fb0;}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#15171a;--fg:#e7e9ec;--mut:#a3a9b3;--card:#1d2024;--bd:#30343a;--grid:#2a2e33;--base:#565c66;
--best:#4cc38a;--worst:#f07167;--ix:#7b8494;--ev:#e8a33d;--buy:#6aa7ef;--exit:#b48ef0;}}
:root[data-theme="dark"]{--bg:#15171a;--fg:#e7e9ec;--mut:#a3a9b3;--card:#1d2024;--bd:#30343a;--grid:#2a2e33;--base:#565c66;
--best:#4cc38a;--worst:#f07167;--ix:#7b8494;--ev:#e8a33d;--buy:#6aa7ef;--exit:#b48ef0;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 -apple-system,"PingFang TC","Noto Sans TC","Microsoft JhengHei",sans-serif}
main{max-width:1060px;margin:0 auto;padding:16px}
h1{font-size:20px;margin:4px 0 8px}h2{font-size:17px;margin:28px 0 6px}h3{font-size:15px;margin:16px 0 8px;color:var(--mut)}
.lead{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:10px 12px;margin:8px 0}
.mut{color:var(--mut);font-size:13px}
.legend{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:13px;color:var(--mut);margin:8px 0}
.legend i{display:inline-block;width:18px;height:0;border-top:2px solid;vertical-align:middle;margin-right:4px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}
.card{margin:0;background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:8px 8px 6px}
figcaption{font-size:13px;margin-bottom:4px}figcaption b{display:block;font-size:14px}figcaption span{color:var(--mut)}
.ch{width:100%;height:auto;aspect-ratio:320/180;display:block}
.ch .grid{stroke:var(--grid);stroke-width:1}.ch .base{stroke:var(--base);stroke-width:1;stroke-dasharray:3 3}
.ch .yl{fill:var(--mut);font-size:9px;text-anchor:end}.ch .xl{fill:var(--mut);font-size:9px}
.ch .ix{fill:none;stroke:var(--ix);stroke-width:1.2;opacity:.7}
.ch .stk{fill:none;stroke-width:1.8;stroke-linejoin:round}.ch .stk.best{stroke:var(--best)}.ch .stk.worst{stroke:var(--worst)}
.ch .mk-ev{stroke:var(--ev);stroke-width:1.2;stroke-dasharray:4 3}.ch .mk-buy{stroke:var(--buy);stroke-width:1.2}.ch .mk-exit{stroke:var(--exit);stroke-width:1.2}
.nt{margin:4px 2px 0;font-size:12px;color:var(--mut)}
.tag{display:inline-block;font-size:12px;border:1px solid var(--bd);border-radius:6px;padding:1px 6px;margin-left:6px;color:var(--mut)}
footer{margin:28px 0 8px;font-size:12px;color:var(--mut)}
"""
LEG = ('<div class="legend"><span><i style="border-color:var(--best)"></i>最好</span><span><i style="border-color:var(--worst)"></i>最差</span>'
       '<span><i style="border-color:var(--ix)"></i>加權指數</span><span><i style="border-color:var(--ev);border-top-style:dashed"></i>大跌日</span>'
       '<span><i style="border-color:var(--buy)"></i>買進日</span><span><i style="border-color:var(--exit)"></i>出場日</span>'
       '<span>y 軸：買進價＝100</span></div>')
h = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
     '<title>大跌後最好最差走勢</title><style>' + CSS + '</style></head><body><main>',
     '<h1>大盤大跌後「跌最多＋營收年增＞0」（C+）：最好與最差的走勢</h1>',
     f'<div class="lead">這頁只是挑最極端的例子給你看形狀，<b>不代表平均</b>。歷史 {stat["事件數"]} 次大跌、C+ 共 {stat["C+ 買得到檔次"]} 檔次：'
     f'平均約 +8%（按事件等權 {fmt_pct(stat["事件等權平均"])}、逐筆 {fmt_pct(stat["逐筆平均"])}），逐筆中位約 {fmt_pct(stat["逐筆中位"])}。'
     '<br><span class="mut">描述紀錄，⛔ 不是買賣建議。</span></div>', LEG,
     '<h2>一、歷史 28 次大跌：C+ 全部檔次中報酬最好 6、最差 6</h2>',
     '<p class="mut">報酬＝隔天開盤買、加權收盤收復大跌前一日收盤後隔天開盤賣，扣來回成本 0.585%（未含滑價）；還原價。x 軸＝大跌日前 20 個交易日到出場後 20 個交易日；'
     '個股線以買進價＝100，加權指數以買進日收盤＝100。當天＝該股大跌日當天漲跌幅。</p>',
     '<h3>最好 6 檔次</h3><div class="grid">' + "".join(H_cards["best"]) + '</div>',
     '<h3>最差 6 檔次</h3><div class="grid">' + "".join(H_cards["worst"]) + '</div>',
     f'<h2>二、2026-10-15 事件（前瞻第 0 筆）<span class="tag">持有中、尚未出場、描述紀錄</span></h2>',
     f'<p class="mut">C+ {fstat["檔數"]} 檔，資料到 {fstat["資料日"]}（買進後只有 1 個交易日，形狀還很短）。帳面＝最新還原收盤 ÷ 買進日還原開盤 − 1，未扣成本；'
     f'75 檔等權帳面 {fmt_pct(fstat["帳面等權平均（未扣成本）"])}、中位 {fmt_pct(fstat["帳面中位"])}。第 0 筆不入判。x 軸＝大跌日前 20 個交易日到最新。</p>',
     '<h3>目前帳面最好 5 檔</h3><div class="grid">' + "".join(F_cards["best"]) + '</div>',
     '<h3>目前帳面最差 5 檔</h3><div class="grid">' + "".join(F_cards["worst"]) + '</div>',
     f'<footer>資料：backtest/resultsMktDrop/deep/c_rows.csv（C 逐筆，營收年增＞0 篩 C+）、backtest/forward/mktdrop/positions.csv、candidates_20261015.csv；'
     f'價格＝v1 世界還原價（research11.load_bars）；加權指數＝公開庫 market_index.csv（origin/main {sha[:10]}）。'
     '早年（2006～2014）含減資假飆股約 0.3%；線不跨壞根（缺口 ≥5 日或減資），遇到就截斷並在圖下註明。產生於 2026-10-17（台北）。</footer>',
     '</main></body></html>']
os.makedirs(OUTD, exist_ok=True)
open(OUT, "w", encoding="utf-8").write("".join(h))
J = json.dumps({"out": OUT, "stat": stat, "fstat": fstat, "list": LIST}, ensure_ascii=False, indent=1, default=str)
open("/mnt/c/Users/ChemTim/AppData/Local/Temp/claude/C--SynologyDrive---------/f4c14e25-a422-4a37-ab64-e11f2ead97b5/scratchpad/out.json", "w", encoding="utf-8").write(J)
print("ok")
