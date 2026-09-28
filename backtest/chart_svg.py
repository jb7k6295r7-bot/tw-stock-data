# -*- coding: utf-8 -*-
"""純 Python 日 K 線 SVG（⛔ 不需任何繪圖套件；只用 numpy）。回測線，2026-09-28。

    from backtest.chart_svg import kline_svg, MA_COLORS, legend_html
    svg = kline_svg(dates, o, h, l, c, v, ma={5: arr, 20: arr, 60: arr}, marks=[...], title="...")

台股慣例：紅漲綠跌（收 ≥ 開 ⇒ 紅；收 ＜ 開 ⇒ 綠）。
輸出 inline SVG（viewBox 自適應寬度，座標取到小數 1 位），可直接貼進 HTML。
  dates  字串序列（YYYY-MM-DD），長度 n
  o/h/l/c 價格（NaN ＝ 當天沒成交 ⇒ 不畫 K 棒）；v 成交量（任意單位，NaN 當 0）
  ma     {期數: 長度 n 的序列}（NaN 段不畫）
  marks  [{"i": 位置, "px": 價格, "kind": "entry"|"exit", "label": 字串[, "color": 色碼]}]（color 省略 ⇒ 進場藍、出場黑，原樣）
  shade  (i0, i1) ⇒ 持有期間淡色底
  hlines [{"px": 價格, "label": 字串, "color": 色碼}] ⇒ 水平虛線（基準線）；None（預設）⇒ 不畫，輸出與加參數前逐字相同
"""
from __future__ import annotations

import html

import numpy as np

UP, DOWN, FLAT = "#d62728", "#2ca02c", "#888888"
MA_COLORS = {5: "#ff9800", 20: "#1f6fd1", 60: "#9c27b0"}
W = 800
PL, PR = 6, 66                      # 左右留白（右邊放價格刻度）


def _f(x):
    return f"{x:.1f}".rstrip("0").rstrip(".") if abs(x - round(x)) > 1e-9 else str(int(round(x)))


def _nice_ticks(lo, hi, n=5):
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        return []
    raw = (hi - lo) / n
    mag = 10 ** np.floor(np.log10(raw))
    step = min((s * mag for s in (1, 2, 2.5, 5, 10) if s * mag >= raw), default=raw)
    t0 = np.ceil(lo / step) * step
    return [t0 + i * step for i in range(int((hi - t0) / step) + 1)]


def _fmt_px(p):
    return f"{p:,.2f}" if p < 100 else (f"{p:,.1f}" if p < 1000 else f"{p:,.0f}")


def kline_svg(dates, o, h, l, c, v, ma=None, marks=None, shade=None, title="", subtitle="", show_title=True, hlines=None):
    """show_title=False ⇒ 標題只放 aria-label（呼叫端用 HTML 文字顯示，手機上字比較大）。"""
    PT = 50 if show_title else 12
    PB_PRICE = PT + 300; VT = PB_PRICE + 18; VB = VT + 80; XLAB = VB + 20; H = XLAB + 8
    o, h, l, c = (np.asarray(a, float) for a in (o, h, l, c))
    v = np.nan_to_num(np.asarray(v, float), nan=0.0)
    n = len(c)
    ma = ma or {}
    marks = marks or []
    vals = [h[np.isfinite(h)], l[np.isfinite(l)]] + [np.asarray(m, float)[np.isfinite(m)] for m in ma.values()] + \
           [np.array([m["px"] for m in marks if np.isfinite(m["px"])])] +            ([np.array([z["px"] for z in hlines if np.isfinite(z["px"])])] if hlines else [])
    allv = np.concatenate([x for x in vals if len(x)])
    lo, hi = float(allv.min()), float(allv.max())
    pad = (hi - lo) * 0.08 or hi * 0.02 or 1.0
    lo -= pad; hi += pad * 1.6                          # 上方多留一點給出場標籤
    xw = (W - PL - PR) / max(n, 1)
    bw = max(xw * 0.7, 1.0)

    def X(i):
        return PL + (i + 0.5) * xw

    def Y(p):
        return PB_PRICE - (p - lo) / (hi - lo) * (PB_PRICE - PT)

    vmax = float(v.max()) or 1.0

    def YV(x):
        return VB - x / vmax * (VB - VT)

    out = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" '
           f'aria-label="{html.escape(title)}" style="width:100%;height:auto;display:block" font-family="sans-serif">',
           f'<rect x="0" y="0" width="{W}" height="{H}" fill="#fff"/>',
           ]
    if show_title:
        out.append(f'<text x="{PL}" y="22" font-size="19" font-weight="bold" fill="#222">{html.escape(title)}</text>')
    if subtitle and show_title:
        out.append(f'<text x="{PL}" y="42" font-size="14" fill="#555">{html.escape(subtitle)}</text>')
    if shade is not None:
        i0, i1 = shade
        x0 = X(i0) - xw / 2; x1 = X(i1) + xw / 2
        out.append(f'<rect x="{_f(x0)}" y="{PT}" width="{_f(x1 - x0)}" height="{VB - PT}" fill="#fff4cc" opacity="0.6"/>')
    # 格線與刻度
    g = []
    for t in _nice_ticks(lo, hi):
        y = Y(t)
        g.append(f'<line x1="{PL}" x2="{W - PR}" y1="{_f(y)}" y2="{_f(y)}" stroke="#e6e6e6"/>'
                 f'<text x="{W - PR + 4}" y="{_f(y + 5)}" font-size="14" fill="#666">{_fmt_px(t)}</text>')
    out.append("".join(g))
    out.append(f'<line x1="{PL}" x2="{W - PR}" y1="{VB}" y2="{VB}" stroke="#bbb"/>'
               f'<text x="{W - PR + 4}" y="{VT + 12}" font-size="13" fill="#666">量 {_fmt_px(vmax)}</text>')
    step = max(1, n // 4)
    lab = []
    for i in range(0, n, step):
        lab.append(f'<line x1="{_f(X(i))}" x2="{_f(X(i))}" y1="{VB}" y2="{VB + 4}" stroke="#999"/>'
                   f'<text x="{_f(X(i))}" y="{XLAB + 4}" font-size="14" fill="#666" '
                   f'text-anchor="{"start" if X(i) < 45 else ("end" if X(i) > W - PR - 45 else "middle")}">{dates[i]}</text>')
    out.append("".join(lab))
    # K 棒與量
    up, dn, fl, vu, vd = [], [], [], [], []
    for i in range(n):
        if not np.isfinite(c[i]) or not np.isfinite(o[i]):
            continue
        x = X(i)
        col = up if c[i] > o[i] else (dn if c[i] < o[i] else fl)
        hh = h[i] if np.isfinite(h[i]) else max(o[i], c[i]); ll = l[i] if np.isfinite(l[i]) else min(o[i], c[i])
        yt, yb = Y(max(o[i], c[i])), Y(min(o[i], c[i]))
        col.append(f'M{_f(x)} {_f(Y(hh))}V{_f(Y(ll))}')                               # 影線
        col.append(f'M{_f(x - bw / 2)} {_f(yt)}h{_f(bw)}v{_f(max(yb - yt, 0.8))}h{_f(-bw)}Z')  # 實體
        (vu if c[i] >= o[i] else vd).append(f'M{_f(x - bw / 2)} {_f(YV(v[i]))}h{_f(bw)}V{VB}h{_f(-bw)}Z')
    for d_, colr in ((up, UP), (dn, DOWN), (fl, FLAT)):
        if d_:
            out.append(f'<path d="{"".join(d_)}" stroke="{colr}" fill="{colr}" stroke-width="1"/>')
    for d_, colr in ((vu, UP), (vd, DOWN)):
        if d_:
            out.append(f'<path d="{"".join(d_)}" fill="{colr}" opacity="0.55"/>')
    # 均線
    for k_, arr in sorted(ma.items()):
        arr = np.asarray(arr, float)
        segs, cur = [], []
        for i in range(n):
            if np.isfinite(arr[i]):
                cur.append(f"{_f(X(i))},{_f(Y(arr[i]))}")
            elif cur:
                segs.append(cur); cur = []
        if cur:
            segs.append(cur)
        for s in segs:
            if len(s) > 1:
                out.append(f'<polyline points="{" ".join(s)}" fill="none" stroke="{MA_COLORS.get(k_, "#444")}" stroke-width="1.6"/>')
    for z in (hlines or []):                            # 基準線（hlines=None 時整段不輸出）
        if np.isfinite(z["px"]):
            zc = z.get("color", "#e65100")
            out.append(f'<line x1="{PL}" x2="{W - PR}" y1="{_f(Y(z["px"]))}" y2="{_f(Y(z["px"]))}" stroke="{zc}" stroke-width="1.6" stroke-dasharray="7 4"/>'
                       f'<text x="{PL + 4}" y="{_f(Y(z["px"]) - 5)}" font-size="14" fill="{zc}" stroke="#fff" stroke-width="3" paint-order="stroke">{html.escape(z.get("label", ""))}</text>')
    # 進出場標記
    for m in marks:
        i, p = m["i"], m["px"]
        if not (0 <= i < n) or not np.isfinite(p):
            continue
        x = X(i)
        if m["kind"] == "entry":
            mc = m.get("color", "#0b5fff")
            base = Y(l[i] if np.isfinite(l[i]) else p) + 6
            out.append(f'<path d="M{_f(x)} {_f(base)}l-8 15h16Z" fill="{mc}"/>'
                       f'<line x1="{_f(x - 18)}" x2="{_f(x + 18)}" y1="{_f(Y(p))}" y2="{_f(Y(p))}" stroke="{mc}" stroke-dasharray="3 2"/>'
                       + _label(x, base + 32 + 18 * m.get("row", 0), m["label"], mc))
        else:
            mc = m.get("color", "#111")
            base = Y(h[i] if np.isfinite(h[i]) else p) - 6
            out.append(f'<path d="M{_f(x)} {_f(base)}l-8 -15h16Z" fill="{mc}"/>'
                       f'<line x1="{_f(x - 18)}" x2="{_f(x + 18)}" y1="{_f(Y(p))}" y2="{_f(Y(p))}" stroke="{mc}" stroke-dasharray="3 2"/>'
                       + _label(x, base - 20 - 18 * m.get("row", 0), m["label"], mc))
    out.append("</svg>")
    return "".join(out)


def _label(x, y, text, colr):
    anchor = "end" if x > W - PR - 90 else ("start" if x < 90 else "middle")
    return (f'<text x="{_f(x)}" y="{_f(y)}" font-size="16" font-weight="bold" fill="{colr}" text-anchor="{anchor}" '
            f'stroke="#fff" stroke-width="3" paint-order="stroke">{html.escape(text)}</text>')


def legend_html():
    sw = lambda c_, t: (f'<span style="display:inline-flex;align-items:center;gap:4px;margin-right:12px">'
                        f'<span style="display:inline-block;width:18px;height:3px;background:{c_}"></span>{t}</span>')
    box = lambda c_, t: (f'<span style="display:inline-flex;align-items:center;gap:4px;margin-right:12px">'
                         f'<span style="display:inline-block;width:10px;height:12px;background:{c_}"></span>{t}</span>')
    return ('<div class="legend">' + sw(MA_COLORS[5], "MA5") + sw(MA_COLORS[20], "MA20") + sw(MA_COLORS[60], "MA60") +
            box(UP, "漲（收＞開）") + box(DOWN, "跌（收＜開）") +
            '<span style="margin-right:12px"><b style="color:#0b5fff">▲</b> 進場（開盤）</span>'
            '<span style="margin-right:12px"><b>▼</b> 出場</span>'
            '<span><span style="display:inline-block;width:14px;height:10px;background:#fff4cc;border:1px solid #eed"></span> 持有期間</span></div>')


def moving_avg(close, k):
    """k 日均線（close 已 ffill；前 k−1 根 NaN）。"""
    c = np.asarray(close, float)
    out = np.full(len(c), np.nan)
    if len(c) >= k:
        cs = np.cumsum(np.r_[0.0, np.nan_to_num(c)])
        m = (cs[k:] - cs[:-k]) / k
        ok = np.convolve(np.isfinite(c).astype(int), np.ones(k, int), "valid") == k
        out[k - 1:] = np.where(ok, m, np.nan)
    return out
