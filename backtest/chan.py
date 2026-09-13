"""纏論（日 K 單層簡化版）：包含處理 → 分型 → 筆 → 筆中樞 → 第三類買點與對照組②／放棄組③。K線分析 2026-09-13 08:30 派工（研究十五）。

⛔ 這不是纏論本身：以日 K 為最小級別、不做跨級別遞迴、不用背馳、線段不實作（用筆當次級別走勢）。
三個自由度做成開關（都要報）：A 序列起點（start）、B 老筆／新筆（pen_mode）、C 中樞 ZG／ZD 取前兩筆或三筆（zg_mode）。

所有輸出的「日」都是**確認日**（不是端點日）：
- 分型 j 的確認日 ＝ 第三根合併 K 棒的最後一根原始 K 棒。
- 筆的完成確認日 ＝ 下一個反向分型的確認日（該筆端點那一天還可能被更極端的同向分型取代）。
- 第三類買點（B3）訊號日 ＝ 回抽筆的確認日；對照組②（C2）訊號日 ＝ 中樞成立（第三筆確認）後第一根收盤 > ZG 的原始 K 棒；
  放棄組③（ABANDON）＝ 回抽筆低點 ≤ ZG（重回中樞）者，訊號日同樣取回抽筆確認日。
純函式，只吃 high／low／close 陣列（有效 K 棒序列），不讀資料庫。
"""
from __future__ import annotations

import numpy as np



def merge_bars(h, l, start=0):
    """包含處理。回傳 (mh, ml, m_end, m_start)：合併後的高、低、每根合併 K 棒的最後一根／第一根原始索引。
    方向：與前一根合併 K 棒比高點（高於 ⇒ 向上：取高高／高低；否則向下：取低高／低低）。第一根沒有方向時當向上。"""
    n = len(h)
    mh, ml, me, ms = [], [], [], []
    for i in range(start, n):
        if np.isnan(h[i]) or np.isnan(l[i]):
            continue
        if not mh:
            mh.append(float(h[i])); ml.append(float(l[i])); me.append(i); ms.append(i); continue
        H, L = mh[-1], ml[-1]
        if (h[i] <= H and l[i] >= L) or (h[i] >= H and l[i] <= L):
            up = True if len(mh) < 2 else mh[-1] > mh[-2]
            if up:
                mh[-1] = max(H, float(h[i])); ml[-1] = max(L, float(l[i]))
            else:
                mh[-1] = min(H, float(h[i])); ml[-1] = min(L, float(l[i]))
            me[-1] = i
        else:
            mh.append(float(h[i])); ml.append(float(l[i])); me.append(i); ms.append(i)
    return np.array(mh), np.array(ml), np.array(me, dtype=int), np.array(ms, dtype=int)


def fractals(mh, ml, me, ms=None):
    """分型：頂 ＝ 中間那根高點最高且低點最高；底 ＝ 低點最低且高點最低。回傳 list of (j, type, price, confirm_raw, mid_start_raw, mid_end_raw)。"""
    if ms is None:
        ms = me
    out = []
    for j in range(1, len(mh) - 1):
        if mh[j] > mh[j - 1] and mh[j] > mh[j + 1] and ml[j] > ml[j - 1] and ml[j] > ml[j + 1]:
            out.append((j, "top", float(mh[j]), int(me[j + 1]), int(ms[j]), int(me[j])))
        elif ml[j] < ml[j - 1] and ml[j] < ml[j + 1] and mh[j] < mh[j - 1] and mh[j] < mh[j + 1]:
            out.append((j, "bot", float(ml[j]), int(me[j + 1]), int(ms[j]), int(me[j])))
    return out


def pens(fr, mode="new"):
    """筆：頂底交替。
    新筆（PREREG15 主格）：① 兩分型經包含處理後不共用 K（中間根索引差 ≥ 3）；② 兩分型中間根之間（不含）的【原始】K 棒 ≥ 3（用合併 K 的原始邊界算）。
    老筆（敏感度 B）：頂底之間至少 1 根獨立合併 K（中間根索引差 ≥ 4）。
    同型分型更極端者取代端點。回傳 list of dict(j, type, price, confirm_raw, ...)——confirm_raw 是「到該端點那一筆」的完成確認日（＝下一個端點分型的確認日），最後一個端點為 None。"""
    ends = []
    for j, t, p, cr, rs, re_ in fr:
        if not ends:
            ends.append({"j": j, "type": t, "price": p, "fr_confirm": cr, "rs": rs, "re": re_, "confirm_raw": None}); continue
        cur = ends[-1]
        if t == cur["type"]:
            if (t == "top" and p > cur["price"]) or (t == "bot" and p < cur["price"]):
                cur.update(j=j, price=p, fr_confirm=cr, rs=rs, re=re_)
            continue
        if mode == "old":
            ok_dist = j - cur["j"] >= 4
        else:
            ok_dist = (j - cur["j"] >= 3) and (rs - cur["re"] - 1 >= 3)
        ok_price = (p < cur["price"]) if t == "bot" else (p > cur["price"])
        if ok_dist and ok_price:
            cur["confirm_raw"] = cr          # 上一筆到此確認
            ends.append({"j": j, "type": t, "price": p, "fr_confirm": cr, "rs": rs, "re": re_, "confirm_raw": None})
    return ends


def _pen_range(ends, k):
    a, b = ends[k]["price"], ends[k + 1]["price"]
    return min(a, b), max(a, b)


def centers_and_signals(ends, zg_mode=2, n_pens=5):
    """筆中樞與訊號。筆 k ＝ 端點 k → k+1（k 從 0 起）。
    中樞（PREREG15 1.4）：連續 n_pens 筆（主格 5、敏感度 D 3）全部與 [ZD,ZG] 有交集；zg_mode=2：ZG＝前兩筆最低高點、ZD＝前兩筆最高低點；zg_mode=3：前三筆。
    之後每筆與 [ZD,ZG] 有交集者延伸中樞（不設上限）。向上離開 ＝ 中樞之後的向上筆 A 終點 > ZG，緊接的向下筆 B：
      B 終點 ≥ ZG ⇒ 第三類買點（訊號日 ＝ B 的完成確認日）；B 終點 < ZG ⇒ 放棄組（訊號日同），中樞延伸。
    向下離開（A' 低點 < ZD 且 B' 高點 < ZD）⇒ 第三類賣點，中樞結束（本研究不做空，只用來結束中樞）。
    回傳 (centers, signals)：signals 為 dict(kind, signal_raw, zg, zd, center, pen)；kind ∈ {B3, ABANDON}。C2 由 detect() 用原始收盤補。"""
    total = len(ends) - 1
    centers, signals = [], []
    s = 0
    while s + n_pens - 1 < total:
        r = [_pen_range(ends, k) for k in range(s, s + n_pens)]
        if zg_mode == 2:
            zd, zg = max(r[0][0], r[1][0]), min(r[0][1], r[1][1])
        else:
            zd, zg = max(x[0] for x in r[:3]), min(x[1] for x in r[:3])
        ok = zd < zg and all(x[0] <= zg and x[1] >= zd for x in r)
        if not ok:
            s += 1; continue
        # 中樞確認日 ＝ 第 n_pens 筆的完成確認日（＝ 端點 s+n_pens−1 的 confirm_raw）
        formed_raw = ends[s + n_pens - 1]["confirm_raw"]
        if formed_raw is None:
            break
        c = {"start_pen": s, "zg": zg, "zd": zd, "formed_raw": int(formed_raw), "end_pen": s + n_pens - 1, "exit": None}
        k = s + n_pens
        while k < total:
            lo, hi = _pen_range(ends, k)
            up_pen = ends[k + 1]["type"] == "top"
            if up_pen and hi > zg and k + 1 < total:
                lo2, hi2 = _pen_range(ends, k + 1)       # 回抽筆 B
                cr = ends[k + 1]["confirm_raw"]           # B 的完成確認日 ＝ 端點 k+2 分型確認 ⇒ 存在 ends[k+1]["confirm_raw"]
                if cr is None:
                    break
                if lo2 >= zg:
                    signals.append({"kind": "B3", "signal_raw": int(cr), "zg": zg, "zd": zd, "center": len(centers), "pen": k + 1})
                    c["exit"] = ("up", k); c["end_pen"] = k + 1; k = None; break
                signals.append({"kind": "ABANDON", "signal_raw": int(cr), "zg": zg, "zd": zd, "center": len(centers), "pen": k + 1})
                c["end_pen"] = k + 1; k += 2; continue
            if (not up_pen) and lo < zd and k + 1 < total:
                lo2, hi2 = _pen_range(ends, k + 1)
                if hi2 < zd:
                    c["exit"] = ("down", k); c["end_pen"] = k + 1; k = None; break
                c["end_pen"] = k + 1; k += 2; continue
            if lo <= zg and hi >= zd:
                c["end_pen"] = k; k += 1; continue
            k += 1
        centers.append(c)
        s = c["end_pen"] + 1 if k is None else max(c["end_pen"], s + n_pens - 1) + 1
    return centers, signals


def detect(h, l, c, pen_mode="new", zg_mode=2, n_pens=5, start=0):
    """整條流程（預設 ＝ PREREG15 主格：新筆、ZG/ZD 前兩筆、五筆中樞、全歷史起算）。回傳 (centers, signals)，signals 含 B3／ABANDON／C2，signal_raw 是有效 K 棒序列上的索引。"""
    mh, ml, me, ms = merge_bars(h, l, start)
    fr = fractals(mh, ml, me, ms)
    ends = pens(fr, pen_mode)
    centers, signals = centers_and_signals(ends, zg_mode, n_pens)
    # 對照組②：中樞成立後第一根收盤 > ZG（且在中樞結束之前）
    n = len(c)
    for ci, ce in enumerate(centers):
        f = ce["formed_raw"]
        end_raw = ends[ce["end_pen"] + 1]["fr_confirm"] if ce["end_pen"] + 1 < len(ends) else n - 1
        for i in range(f + 1, min(n, end_raw + 1)):
            if not np.isnan(c[i]) and c[i] > ce["zg"]:
                signals.append({"kind": "C2", "signal_raw": int(i), "zg": ce["zg"], "zd": ce["zd"], "center": ci, "pen": -1}); break
    signals.sort(key=lambda s: (s["signal_raw"], s["kind"]))
    return centers, signals


# ── 合成序列自測 ──
def _seq(points, step=3):
    """由端點價位造 high／low／close 序列：每段線性走 step 根，每根高低各 ±0.3。"""
    xs = []
    for a, b in zip(points[:-1], points[1:]):
        xs.extend(np.linspace(a, b, step + 1)[:-1])
    xs.append(points[-1])
    x = np.array(xs, float)
    return x + 0.3, x - 0.3, x


def selftest():
    ok = True

    def check(name, cond, info=""):
        nonlocal ok
        print(("  ok   " if cond else "  ✗    ") + name + (f"  {info}" if info else ""))
        ok &= bool(cond)

    # 情境 1（主格：新筆、ZG/ZD 前兩筆、五筆中樞）：五筆全在 [ZD 9.7, ZG 12.3] 內，向上離開到 15，回抽到 13（≥ ZG）⇒ B3 一筆、無放棄；C2 在中樞成立後第一根收盤 > ZG
    pts = [8, 12, 10, 13, 10.5, 12.0, 11, 12.0, 10.8, 15, 13, 17, 14, 18]
    h, l, c = _seq(pts, 5)
    centers, sig = detect(h, l, c)
    kinds = [s["kind"] for s in sig]
    check("情境1 有五筆中樞", len(centers) >= 1 and centers[0]["end_pen"] - centers[0]["start_pen"] >= 4, f"{[(x['start_pen'], x['end_pen'], round(x['zd'],2), round(x['zg'],2)) for x in centers]}")
    check("情境1 ZG ＝ 前兩筆最低高點 12.3、ZD ＝ 前兩筆最高低點 9.7", bool(centers) and abs(centers[0]["zg"] - 12.3) < 1e-6 and abs(centers[0]["zd"] - 9.7) < 1e-6)
    check("情境1 B3 恰一筆", kinds.count("B3") == 1, str(kinds))
    check("情境1 無放棄", kinds.count("ABANDON") == 0)
    b3 = [s for s in sig if s["kind"] == "B3"]
    c2 = [s for s in sig if s["kind"] == "C2"]
    check("情境1 C2 早於 B3", bool(c2) and bool(b3) and c2[0]["signal_raw"] < b3[0]["signal_raw"], f"C2 {c2[0]['signal_raw'] if c2 else None} B3 {b3[0]['signal_raw'] if b3 else None}")
    check("情境1 B3 訊號日在回抽低點之後（確認日）", bool(b3) and c[b3[0]["signal_raw"]] > 13, f"close@sig={c[b3[0]['signal_raw']] if b3 else None}")
    check("情境1 C2 訊號日收盤 > ZG", bool(c2) and c[c2[0]["signal_raw"]] > centers[0]["zg"])
    check("情境1 C2 前一根收盤 ≤ ZG（第一根突破）", bool(c2) and c[c2[0]["signal_raw"] - 1] <= centers[0]["zg"])
    check("情境1 C2 在中樞成立（第五筆確認）之後", bool(c2) and c2[0]["signal_raw"] > centers[0]["formed_raw"], f"C2 {c2[0]['signal_raw'] if c2 else None} formed {centers[0]['formed_raw']}")
    check("情境1 離開筆在中樞之後（B3 的回抽筆索引 ≥ start+6）", bool(b3) and b3[0]["pen"] >= centers[0]["start_pen"] + 6, f"pen {b3[0]['pen'] if b3 else None}")
    # 情境 2：離開後回抽跌回中樞（11.5 < ZG 12.3）⇒ 放棄組一筆、第一次離開無 B3
    pts2 = [8, 12, 10, 13, 10.5, 12.0, 11, 12.0, 10.8, 15, 11.5, 16, 12.2, 17]
    h2, l2, c2_ = _seq(pts2, 5)
    cen2, sig2 = detect(h2, l2, c2_)
    k2 = [s["kind"] for s in sig2]
    check("情境2 放棄組 ≥ 1", k2.count("ABANDON") >= 1, str(k2))
    check("情境2 第一次離開沒有 B3", not any(s["kind"] == "B3" and s["pen"] == cen2[0]["start_pen"] + 6 for s in sig2) if cen2 else False)
    # 情境 3：單邊上漲之字 ⇒ 五筆中樞不成立（L2 > H1），無中樞、無訊號（三筆版才會恆真）
    pts3 = [8, 10, 9.5, 12, 11.5, 14, 13.5, 16, 15.5, 18]
    h3, l3, c3 = _seq(pts3, 5)
    cen3, sig3 = detect(h3, l3, c3)
    cen3b, _ = detect(h3, l3, c3, n_pens=3)
    check("情境3 單邊：五筆中樞 0 個、無訊號", len(cen3) == 0 and len(sig3) == 0, f"centers {len(cen3)} sig {len(sig3)}")
    check("情境3 單邊：三筆版反而有中樞（恆真，PREREG15 1.4）", len(cen3b) >= 1, f"{len(cen3b)}")
    # 情境 4：筆的距離——步長 3（分型中間原始 K 只有 2 根）新筆與老筆都不成筆；步長 5 都成
    h4, l4, c4 = _seq(pts, 3)
    _, so = detect(h4, l4, c4, pen_mode="old"); _, sn = detect(h4, l4, c4, pen_mode="new")
    check("情境4 步長 3：老筆新筆都 0 訊號", len(so) == 0 and len(sn) == 0, f"old {len(so)} new {len(sn)}")
    _, so5 = detect(h, l, c, pen_mode="old"); _, sn5 = detect(h, l, c, pen_mode="new")
    check("情境4 步長 5：老筆與新筆都有 B3", any(x["kind"] == "B3" for x in so5) and any(x["kind"] == "B3" for x in sn5))
    # 情境 5：ZG/ZD 二筆 vs 三筆——情境1 前三筆高點 12.3/13.3/13.3 ⇒ 三筆版 ZG 也是 12.3，B3 日相同
    _, s2 = detect(h, l, c, zg_mode=2); _, s3 = detect(h, l, c, zg_mode=3)
    check("情境5 zg_mode 2/3 在情境1 給同樣的 B3 日", [x["signal_raw"] for x in s2 if x["kind"] == "B3"] == [x["signal_raw"] for x in s3 if x["kind"] == "B3"])
    # 情境 6：序列起點（敏感度 A）——從第 3 根起算，包含處理路徑可能不同，但不可以炸、且仍找得到 B3
    _, sA = detect(h, l, c, start=3)
    check("情境6 起點平移仍有 B3", any(x["kind"] == "B3" for x in sA))
    # 情境 8：中樞第五筆（上升筆）自己探出 ZG，不算「離開」（離開筆必須在中樞之後）⇒ 不可以在它後面產生放棄組；B3 在後面真正的離開＋回抽
    pts8 = [10, 8, 12, 10, 13, 10.5, 12.2, 11.8, 15, 13, 17]
    h8, l8, c8 = _seq(pts8, 5)
    cen8, sig8 = detect(h8, l8, c8)
    k8 = [(x["kind"], x["pen"]) for x in sig8 if x["kind"] != "C2"]
    # 筆 0..4 是中樞（b5 ＝ 10.5→12.2 探出 ZG 12.3 但不算離開）、筆 5 回檔留在中樞、筆 6 離開、筆 7 回抽 ⇒ 唯一的非 C2 訊號是 B3@pen 7
    check("情境8 第五筆探出 ZG 不算離開：無放棄、B3 在中樞之後", bool(cen8) and k8 == [("B3", cen8[0]["start_pen"] + 7)], f"{k8} center {[(x['start_pen'], x['end_pen']) for x in cen8]}")
    # 情境 7：NaN 洞不炸
    h7 = h.copy(); l7 = l.copy(); c7 = c.copy(); h7[7] = l7[7] = c7[7] = np.nan
    detect(h7, l7, c7)
    check("情境7 NaN 不炸", True)
    print("[chan selftest]", "通過" if ok else "失敗")
    return ok


if __name__ == "__main__":
    import sys
    sys.exit(0 if selftest() else 1)
