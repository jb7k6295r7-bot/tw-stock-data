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

MAX_PENS_IN_CENTER = 9


def merge_bars(h, l, start=0):
    """包含處理。回傳 (mh, ml, m_end)：合併後的高、低、每根合併 K 棒的最後一根原始索引。
    方向：與前一根合併 K 棒比高點（高於 ⇒ 向上：取高高／高低；否則向下：取低高／低低）。第一根沒有方向時當向上。"""
    n = len(h)
    mh, ml, me = [], [], []
    for i in range(start, n):
        if np.isnan(h[i]) or np.isnan(l[i]):
            continue
        if not mh:
            mh.append(float(h[i])); ml.append(float(l[i])); me.append(i); continue
        H, L = mh[-1], ml[-1]
        if (h[i] <= H and l[i] >= L) or (h[i] >= H and l[i] <= L):
            up = True if len(mh) < 2 else mh[-1] > mh[-2]
            if up:
                mh[-1] = max(H, float(h[i])); ml[-1] = max(L, float(l[i]))
            else:
                mh[-1] = min(H, float(h[i])); ml[-1] = min(L, float(l[i]))
            me[-1] = i
        else:
            mh.append(float(h[i])); ml.append(float(l[i])); me.append(i)
    return np.array(mh), np.array(ml), np.array(me, dtype=int)


def fractals(mh, ml, me):
    """分型：頂 ＝ 中間那根高點最高且低點最高；底 ＝ 低點最低且高點最低。回傳 list of (j, type, price, confirm_raw)。"""
    out = []
    for j in range(1, len(mh) - 1):
        if mh[j] > mh[j - 1] and mh[j] > mh[j + 1] and ml[j] > ml[j - 1] and ml[j] > ml[j + 1]:
            out.append((j, "top", float(mh[j]), int(me[j + 1])))
        elif ml[j] < ml[j - 1] and ml[j] < ml[j + 1] and mh[j] < mh[j - 1] and mh[j] < mh[j + 1]:
            out.append((j, "bot", float(ml[j]), int(me[j + 1])))
    return out


def pens(fr, mode="old"):
    """筆：頂底交替。老筆：兩個分型中間至少 1 根獨立合併 K 棒（j 差 ≥ 4）；新筆：分型不共用 K 棒即可（j 差 ≥ 3）。
    同型分型更極端者取代端點。回傳 list of dict(j, type, price, confirm_raw)——每個端點的 confirm_raw 是「該端點為止那一筆」的完成確認日（＝下一個端點分型的確認日），最後一個端點未確認為 None。"""
    gap = 4 if mode == "old" else 3
    ends = []
    for j, t, p, cr in fr:
        if not ends:
            ends.append({"j": j, "type": t, "price": p, "fr_confirm": cr, "confirm_raw": None}); continue
        cur = ends[-1]
        if t == cur["type"]:
            if (t == "top" and p > cur["price"]) or (t == "bot" and p < cur["price"]):
                cur.update(j=j, price=p, fr_confirm=cr)
            continue
        ok_dist = j - cur["j"] >= gap
        ok_price = (p < cur["price"]) if t == "bot" else (p > cur["price"])
        if ok_dist and ok_price:
            cur["confirm_raw"] = cr          # 上一筆到此確認
            ends.append({"j": j, "type": t, "price": p, "fr_confirm": cr, "confirm_raw": None})
    return ends


def _pen_range(ends, k):
    a, b = ends[k]["price"], ends[k + 1]["price"]
    return min(a, b), max(a, b)


def centers_and_signals(ends, zg_mode=3):
    """筆中樞與訊號。筆 k ＝ 端點 k → k+1（k 從 0 起）。
    中樞：筆 s、s+1、s+2 兩兩重疊（ZD < ZG）。zg_mode=3：ZG＝三筆高點最小、ZD＝三筆低點最大；zg_mode=2：只用前兩筆（仍要求第三筆與 [ZD,ZG] 重疊）。
    之後每筆與 [ZD,ZG] 重疊者延伸中樞（最多 9 筆）。向上離開 ＝ 向上筆 A 高點 > ZG 之後的向下筆 B：
      B 低點 > ZG ⇒ 第三類買點（訊號日 ＝ B 的確認日）；B 低點 ≤ ZG ⇒ 放棄組（訊號日同），中樞延伸。
    向下離開（A' 低點 < ZD 且 B' 高點 < ZD）⇒ 第三類賣點，中樞結束（本研究不做空，只用來結束中樞）。
    回傳 (centers, signals)：signals 為 dict(kind, signal_raw, zg, zd, center, pen)；kind ∈ {B3, ABANDON}。C2 由 detect() 用原始收盤補。"""
    n_pens = len(ends) - 1
    centers, signals = [], []
    s = 0
    while s + 2 < n_pens:
        r = [_pen_range(ends, k) for k in (s, s + 1, s + 2)]
        if zg_mode == 2:
            zd, zg = max(r[0][0], r[1][0]), min(r[0][1], r[1][1])
            ok = zd < zg and r[2][0] <= zg and r[2][1] >= zd
        else:
            zd, zg = max(x[0] for x in r), min(x[1] for x in r)
            ok = zd < zg
        if not ok:
            s += 1; continue
        # 中樞成立：第三筆確認日 ＝ 端點 s+2 的 confirm_raw（筆 s+2 到 s+3 確認）→ 用端點 s+3 的分型確認；保守取 ends[s+2]["confirm_raw"]
        formed_raw = ends[s + 2]["confirm_raw"]
        if formed_raw is None:
            break
        c = {"start_pen": s, "zg": zg, "zd": zd, "formed_raw": int(formed_raw), "end_pen": s + 2, "exit": None}
        k = s + 3
        while k < n_pens and k - s < MAX_PENS_IN_CENTER + 1:
            lo, hi = _pen_range(ends, k)
            up_pen = ends[k + 1]["type"] == "top"
            if up_pen and hi > zg and k + 1 < n_pens:
                lo2, hi2 = _pen_range(ends, k + 1)       # 回抽筆 B
                cr = ends[k + 1]["confirm_raw"]           # B 的完成確認日 ＝ 端點 k+2 分型確認 ⇒ 存在 ends[k+1]["confirm_raw"]
                if cr is None:
                    break
                if lo2 > zg:
                    signals.append({"kind": "B3", "signal_raw": int(cr), "zg": zg, "zd": zd, "center": len(centers), "pen": k + 1})
                    c["exit"] = ("up", k); c["end_pen"] = k + 1; k = None; break
                signals.append({"kind": "ABANDON", "signal_raw": int(cr), "zg": zg, "zd": zd, "center": len(centers), "pen": k + 1})
                c["end_pen"] = k + 1; k += 2; continue
            if (not up_pen) and lo < zd and k + 1 < n_pens:
                lo2, hi2 = _pen_range(ends, k + 1)
                if hi2 < zd:
                    c["exit"] = ("down", k); c["end_pen"] = k + 1; k = None; break
                c["end_pen"] = k + 1; k += 2; continue
            if lo <= zg and hi >= zd:
                c["end_pen"] = k; k += 1; continue
            k += 1
        centers.append(c)
        s = c["end_pen"] + 1 if k is None else max(c["end_pen"], s + 2) + 1
    return centers, signals


def detect(h, l, c, pen_mode="old", zg_mode=3, start=0):
    """整條流程。回傳 (centers, signals)，signals 含 B3／ABANDON／C2，signal_raw 是原始 K 棒索引（有效 K 棒序列上的位置）。"""
    mh, ml, me = merge_bars(h, l, start)
    fr = fractals(mh, ml, me)
    ends = pens(fr, pen_mode)
    centers, signals = centers_and_signals(ends, zg_mode)
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

    # 情境 1：三筆重疊成中樞 [ZD=10, ZG=12]，向上離開到 15，回抽到 13（> ZG）⇒ B3 一筆；C2 在第一根收盤 > 12
    pts = [8, 12, 10, 13, 10.5, 12.0, 11, 15, 13, 17, 14, 18]     # 延伸筆 12.0 留在 ZG（12.3）之內
    h, l, c = _seq(pts, 5)
    centers, sig = detect(h, l, c)
    kinds = [s["kind"] for s in sig]
    check("情境1 有中樞", len(centers) >= 1, f"{[(round(x['zd'],2), round(x['zg'],2)) for x in centers]}")
    check("情境1 B3 恰一筆", kinds.count("B3") == 1, str(kinds))
    check("情境1 無放棄", kinds.count("ABANDON") == 0)
    b3 = [s for s in sig if s["kind"] == "B3"]
    c2 = [s for s in sig if s["kind"] == "C2"]
    check("情境1 C2 早於 B3", bool(c2) and bool(b3) and c2[0]["signal_raw"] < b3[0]["signal_raw"], f"C2 {c2[0]['signal_raw'] if c2 else None} B3 {b3[0]['signal_raw'] if b3 else None}")
    check("情境1 B3 訊號日在回抽低點之後（確認日）", bool(b3) and c[b3[0]["signal_raw"]] > 13, f"close@sig={c[b3[0]['signal_raw']] if b3 else None}")
    # 情境 2：離開後回抽跌回中樞（11.5 ≤ ZG 12）⇒ 放棄組一筆、無 B3
    pts2 = [8, 12, 10, 13, 10.5, 12.5, 11, 15, 11.5, 16, 12.2, 17]
    h2, l2, c2_ = _seq(pts2, 5)
    _, sig2 = detect(h2, l2, c2_)
    k2 = [s["kind"] for s in sig2]
    check("情境2 放棄組 ≥ 1", k2.count("ABANDON") >= 1, str(k2))
    check("情境2 第一次離開沒有 B3", not any(s["kind"] == "B3" and s["pen"] == 8 for s in sig2))
    # 情境 3：單邊上漲的之字——⚠ 任三筆連續必重疊（筆 k 與 k+1 共端點），所以「筆中樞」在單邊裡也會成立（這是筆中樞簡化版的已知性質，PREREG 要寫）；
    #         但離開後沒有確認的回抽 ⇒ 不可以有 B3；放棄組也不可以有（回抽都在 ZG 之上）
    pts3 = [8, 10, 9.5, 12, 11.5, 14, 13.5, 16]
    h3, l3, c3 = _seq(pts3, 5)
    cen3, sig3 = detect(h3, l3, c3)
    k3 = [x["kind"] for x in sig3]
    check("情境3 單邊：無 B3、無放棄", k3.count("B3") == 0 and k3.count("ABANDON") == 0, f"centers {len(cen3)} {k3}")
    # 情境 4：老筆 vs 新筆——分型緊貼（間隔 3 根）時只有新筆成立
    pts4 = [8, 12, 10, 13, 10.5, 12.0, 11, 15, 13, 17, 14, 18]
    h4, l4, c4 = _seq(pts4, 2)
    _, so = detect(h4, l4, c4, pen_mode="old"); _, sn = detect(h4, l4, c4, pen_mode="new")
    check("情境4 步長 2：分型相距 2 根，老筆新筆都不成筆 ⇒ 0 訊號", len(so) == 0 and len(sn) == 0, f"old {len(so)} new {len(sn)}")
    h4b, l4b, c4b = _seq(pts4, 3)                                    # 步長 3：分型相距 3 根 ⇒ 只有新筆成立
    _, so3 = detect(h4b, l4b, c4b, pen_mode="old"); _, sn3 = detect(h4b, l4b, c4b, pen_mode="new")
    check("情境4 步長 3：老筆 0、新筆 ≥ 1", len(so3) == 0 and len(sn3) >= 1, f"old {len(so3)} new {len(sn3)}")
    check("情境1 C2 訊號日收盤 > ZG", bool(c2) and c[c2[0]["signal_raw"]] > centers[0]["zg"], f"close {c[c2[0]['signal_raw']] if c2 else None} zg {centers[0]['zg']}")
    check("情境1 C2 前一根收盤 ≤ ZG（第一根突破）", bool(c2) and c[c2[0]["signal_raw"] - 1] <= centers[0]["zg"])
    check("情境1 C2 在中樞成立（第三筆確認）之後", bool(c2) and c2[0]["signal_raw"] > centers[0]["formed_raw"], f"C2 {c2[0]['signal_raw'] if c2 else None} formed {centers[0]['formed_raw']}")
    # 情境 5：zg_mode 2 與 3 在三筆同幅時相同
    _, s2 = detect(h, l, c, zg_mode=2); _, s3 = detect(h, l, c, zg_mode=3)
    check("情境5 zg_mode 2/3 在情境1 給同樣的 B3 日", [x["signal_raw"] for x in s2 if x["kind"] == "B3"] == [x["signal_raw"] for x in s3 if x["kind"] == "B3"])
    # 情境 6：NaN 洞不炸
    h6 = h.copy(); l6 = l.copy(); c6 = c.copy(); h6[7] = l6[7] = c6[7] = np.nan
    detect(h6, l6, c6)
    check("情境6 NaN 不炸", True)
    print("[chan selftest]", "通過" if ok else "失敗")
    return ok


if __name__ == "__main__":
    import sys
    sys.exit(0 if selftest() else 1)
