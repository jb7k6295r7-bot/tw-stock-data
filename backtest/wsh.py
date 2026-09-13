"""詩魂「變盤三部曲」單層日 K 落地版（PREREG21）。

    第一步  收盤 > 末跌高（下降趨勢裡最後一個較低高點；E 敏感度改成趨勢線）
    第二步  打底不再破底：第一步之後出現 swing low 且 > L（最近一次最低點）＝ HL
    第三步  收盤 > 前高 H（第一步到 HL 之間的最高點）⇒ 訊號日（進場 ＝ 次一根開盤，研究十五 P1 口徑）

swing（K線分析 0947 逐字）：swing high(i) ＝ high[i] > high[i−k..i−1] 且 > high[i+1..i+k]，k＝5，確認日 i+k；swing low 鏡像。
末跌高狀態機（0925 三①）：每一次新的更低低點 L 確認，末跌高 := L 之前最近的一個 swing high（反彈沒破 ⇒ 往下移；反彈破了又再破底 ⇒ 往上移，兩種情形同一條規則）。
下降趨勢的最低要求：L 低於前一個 swing low（LL）且末跌高低於它之前的 swing high（LH）。
⛔ 全部只用 t 之前（含）的資料：swing 用確認日、線用已確認的 swing。

    python3 -m backtest.wsh     # 自測（合成序列）
"""
from __future__ import annotations

import numpy as np

K_SWING = 5
ABANDON_WINDOW = 60      # 第一步之後 60 根內沒走到第三步 ⇒ 「沒完成」


def swings(h, l, k=K_SWING):
    """回傳 list of (confirm_idx, idx, type, price)，type ∈ {"H", "L"}，按確認日排序。"""
    n = len(h); out = []
    for i in range(k, n - k):
        if np.isnan(h[i]) or np.isnan(l[i]):
            continue
        w_h = h[i - k:i + k + 1]; w_l = l[i - k:i + k + 1]
        if np.all(np.isfinite(w_h)) and h[i] > np.max(np.delete(w_h, k)):
            out.append((i + k, i, "H", float(h[i])))
        if np.all(np.isfinite(w_l)) and l[i] < np.min(np.delete(w_l, k)):
            out.append((i + k, i, "L", float(l[i])))
    out.sort(key=lambda x: (x[0], x[1]))
    return out


def line_value(p1, p2, t):
    """通過 (i1, v1)、(i2, v2) 的直線在 t 的值。"""
    (i1, v1), (i2, v2) = p1, p2
    if i2 == i1:
        return v2
    return v1 + (v2 - v1) * (t - i1) / (i2 - i1)


def body_ok(o, c, p1, p2):
    """不可穿實體（1010 2.2）：兩錨點之間（不含端點）每一根 K，線值不落在實體 (min(o,c), max(o,c)) 之內。"""
    (i1, _), (i2, _) = p1, p2
    for t in range(i1 + 1, i2):
        v = line_value(p1, p2, t)
        lo, hi = min(o[t], c[t]), max(o[t], c[t])
        if lo < v < hi:
            return False
    return True


def touches(h, p1, p2, t_end, tol=0.01):
    """觸點數（1010 畫法 B）：錨點之後到 t_end 之間 |high − 線值| / 線值 ≤ tol 的根數。⚠ tol 是我方定的。"""
    (i1, _), (i2, _) = p1, p2
    cnt = 0
    for t in range(i1, t_end + 1):
        v = line_value(p1, p2, t)
        if v > 0 and abs(h[t] - v) / v <= tol:
            cnt += 1
    return cnt


def detect(o, h, l, c, mode="E0", redraw_n=0, hthr=0.0, start=0):
    """回傳 signals: list of dict(kind, t1, hl_idx, H, L, lh, signal_raw, line_ok)。kind ∈ {S3, S1, ABANDON, NOSTEP3}。
    mode：E0 水平末跌高；E1 畫法 A＋不可穿實體；E3 畫法 A 不加實體規則；E2 畫法 B（最多觸點）＋實體規則；
    redraw_n>0 ⇒ E4：第一步突破後 redraw_n 根內收盤回到線下 ⇒ 假突破、用之後新確認的 swing high 重畫。
    hthr：第三步收盤要超過前高 H 的幅度（敏感度 H）。"""
    n = len(c); sw = swings(h, l)
    sig = []
    # 逐根推進：維護已確認的 swing 清單
    sh, sl = [], []                  # [(idx, price)]，已確認
    si = 0
    L = None; L_prev = None; lh = None; lh_prev = None; lh_idx = None
    state = 0                        # 0 找第一步；1 第一步已成立（等 HL）；2 HL 已成立（等第三步）
    t1 = None; hl = None; hl_idx = None; H = None
    line = None                      # (p1, p2) 目前用的趨勢線（E1～E4）
    false_break_at = None; armed = False
    for t in range(start, n):
        # 吸收在 t 確認的 swing
        while si < len(sw) and sw[si][0] <= t:
            cf, i, typ, p = sw[si]; si += 1
            if typ == "H":
                sh.append((i, p))
                if false_break_at is not None and i > false_break_at and redraw_n > 0:
                    line = None; false_break_at = None        # 假突破之後出現新 swing high ⇒ 重畫
                continue
            # swing low
            if state >= 1 and p >= L and i > t1:
                if state == 1:                               # 第一步之後第一個 HL（打底不再破底）
                    hl = p; hl_idx = i; H = float(np.nanmax(h[t1:i + 1])); state = 2
                sl.append((i, p)); continue
            if L is not None and p >= L:                     # 狀態 0 的較高低點：結構不變（末跌高要等它被突破或被更低低點取代）
                sl.append((i, p)); continue
            if state == 2:
                sig.append({"kind": "ABANDON", "t1": t1, "hl_idx": hl_idx, "H": H, "L": L, "lh": lh, "signal_raw": t, "line_ok": True})
            if state >= 1:
                state = 0; t1 = None; hl = None; hl_idx = None; H = None
            # 新的更低低點：L ＝ 它，末跌高 ＝ 它之前最近的 swing high（0925 兩種情形同一條規則）；重新武裝
            L_prev = L; L = p
            prev = [x for x in sh if x[0] < i]
            if prev:
                lh = prev[-1][1]; lh_idx = prev[-1][0]; lh_prev = prev[-2][1] if len(prev) >= 2 else None
            else:
                lh = None; lh_idx = None; lh_prev = None
            armed = True; line = None
            sl.append((i, p))
        if L is None or lh is None:
            continue
        # 下降趨勢最低要求：LL 且 LH
        downtrend = (L_prev is not None and L < L_prev) and (lh_prev is not None and lh < lh_prev)
        if state == 0:
            if not (downtrend and armed):
                continue
            # 第一步的門檻
            if mode == "E0":
                thr = lh; ok = True
            else:
                if line is None:
                    cand = [x for x in sh if x[0] <= t and x[0] > (sl[-2][0] if len(sl) >= 2 else -1) - 400]
                    highs = [x for x in sh if x[0] < (lh_idx or 0) + 1]
                    if len(highs) < 2:
                        continue
                    if mode in ("E1", "E3") or redraw_n > 0:
                        p1, p2 = highs[-2], highs[-1]
                        if p2[1] >= p1[1]:
                            continue                         # 要兩個 lower high
                        if mode != "E3" and not body_ok(o, c, p1, p2):
                            sig.append({"kind": "NOLINE", "t1": t, "signal_raw": t}); line = ("bad",); continue
                        line = (p1, p2)
                    else:                                     # E2：最多觸點
                        best = None
                        for a_ in range(max(0, len(highs) - 6), len(highs) - 1):
                            for b_ in range(a_ + 1, len(highs)):
                                p1, p2 = highs[a_], highs[b_]
                                if p2[1] >= p1[1] or not body_ok(o, c, p1, p2):
                                    continue
                                tc = touches(h, p1, p2, t)
                                if best is None or tc > best[0]:
                                    best = (tc, p1, p2)
                        if best is None:
                            sig.append({"kind": "NOLINE", "t1": t, "signal_raw": t}); line = ("bad",); continue
                        line = (best[1], best[2])
                if line == ("bad",):
                    continue
                thr = line_value(line[0], line[1], t)
            if c[t] > thr:
                if redraw_n > 0:
                    # E4：接下來 redraw_n 根內收盤回到線下 ⇒ 假突破（因果安全：判定用的是 t 之後的根，但訊號在判定完成之後才成立）
                    fb = False
                    for u in range(t + 1, min(t + redraw_n, n - 1) + 1):
                        v = line_value(line[0], line[1], u)
                        if c[u] < v:
                            fb = True; break
                    if fb:
                        false_break_at = t; continue
                t1 = t; state = 1; armed = False
                sig.append({"kind": "S1", "t1": t, "signal_raw": t, "lh": lh, "L": L, "line_ok": True})
        elif state == 1:
            if t - t1 > ABANDON_WINDOW:
                sig.append({"kind": "NOSTEP3", "t1": t1, "signal_raw": t1 + ABANDON_WINDOW, "lh": lh, "L": L}); state = 0; t1 = None; line = None
        elif state == 2:
            if c[t] < hl:
                sig.append({"kind": "ABANDON", "t1": t1, "hl_idx": hl_idx, "H": H, "L": L, "lh": lh, "signal_raw": t, "line_ok": True})
                state = 0; t1 = None; hl = None; hl_idx = None; H = None; line = None
            elif c[t] > H * (1 + hthr):
                sig.append({"kind": "S3", "t1": t1, "hl_idx": hl_idx, "hl": hl, "H": H, "L": L, "lh": lh, "signal_raw": t, "line_ok": True})
                state = 0; t1 = None; hl = None; hl_idx = None; H = None; line = None
            elif t - t1 > ABANDON_WINDOW:
                sig.append({"kind": "NOSTEP3", "t1": t1, "signal_raw": t1 + ABANDON_WINDOW, "lh": lh, "L": L}); state = 0; t1 = None; line = None
    return sig


# ── 自測 ──
def _mk(path):
    """path：list of (close 目標, 根數)，線性走到目標；開高低由收盤加小幅度合成。"""
    cs = []
    cur = path[0][0]
    for tgt, nb in path[1:]:
        for j in range(1, nb + 1):
            cs.append(cur + (tgt - cur) * j / nb)
        cur = tgt
    c = np.array(cs, float); o = np.r_[c[0], c[:-1]]
    h = c * 1.005; l = c * 0.995            # 用收盤造高低，峰谷才會是唯一的
    return o, h, l, c


def _selftest():
    ok_all = True
    def check(name, cond, info=""):
        nonlocal ok_all
        print(f"  {'ok  ' if cond else '✗   '} {name}  {info}")
        ok_all &= bool(cond)
    # 情境 1：下降趨勢（100→90→95→80→88）→ 第一步破末跌高 88 → 回檔 HL 84 (> 80) → 第三步破 H
    o, h, l, c = _mk([(80, 0), (100, 10), (90, 10), (95, 8), (80, 12), (88, 8), (83, 8), (92, 8), (86, 8), (99, 10), (93, 8), (105, 10), (110, 6)])
    s = detect(o, h, l, c)
    kinds = [x["kind"] for x in s]
    check("情境1 出 S1 再出 S3", "S1" in kinds and "S3" in kinds, str(kinds))
    s3 = [x for x in s if x["kind"] == "S3"]
    check("情境1 S3 在 HL 之後、H 之上", bool(s3) and c[s3[0]["signal_raw"]] > s3[0]["H"] and s3[0]["signal_raw"] > s3[0]["hl_idx"], f"{s3[0] if s3 else None}")
    check("情境1 末跌高 ≈ 95（swing high 含影線）", bool(s3) and abs(s3[0]["lh"] - 95 * 1.005) < 1e-6, f"lh={s3[0]['lh'] if s3 else None}")
    # 情境 2：回檔破底 ⇒ ABANDON（HL 之後收盤 < HL）
    o, h, l, c = _mk([(80, 0), (100, 10), (90, 10), (95, 8), (80, 12), (88, 8), (83, 8), (92, 8), (86, 8), (99, 10), (93, 8), (96, 6), (90, 8), (84, 8)])
    s = detect(o, h, l, c); kinds = [x["kind"] for x in s]
    check("情境2 HL 被跌破 ⇒ ABANDON、無 S3", "ABANDON" in kinds and "S3" not in kinds, str(kinds))
    # 情境 3：上升趨勢沒有下降段 ⇒ 沒有第一步
    o, h, l, c = _mk([(100, 0), (110, 20), (105, 10), (120, 20), (115, 10), (130, 20)])
    s = detect(o, h, l, c); kinds = [x["kind"] for x in s]
    check("情境3 純上升 ⇒ 沒有 S1", "S1" not in kinds, str(kinds))
    # 情境 4：第一步之後 60 根沒走到第三步 ⇒ NOSTEP3
    o, h, l, c = _mk([(80, 0), (100, 10), (90, 10), (95, 8), (80, 12), (88, 8), (83, 8), (92, 8), (86, 8), (99, 10), (97, 80)])
    s = detect(o, h, l, c); kinds = [x["kind"] for x in s]
    check("情境4 第一步後橫盤 60 根 ⇒ NOSTEP3", "NOSTEP3" in kinds and "S3" not in kinds, str(kinds))
    # 情境 5：敏感度 H 4% ⇒ 情境 1 的第三步要更高才成立
    o, h, l, c = _mk([(80, 0), (100, 10), (90, 10), (95, 8), (80, 12), (88, 8), (83, 8), (92, 8), (86, 8), (99, 10), (93, 8), (105, 10), (110, 6)])
    s0 = [x for x in detect(o, h, l, c, hthr=0.0) if x["kind"] == "S3"]; s4 = [x for x in detect(o, h, l, c, hthr=0.04) if x["kind"] == "S3"]
    check("情境5 hthr 4% 的 S3 不早於 0%", bool(s0) and bool(s4) and s4[0]["signal_raw"] >= s0[0]["signal_raw"] and c[s4[0]["signal_raw"]] > s4[0]["H"] * 1.04, f"{s0[0]['signal_raw'] if s0 else None} vs {s4[0]['signal_raw'] if s4 else None}")
    # 情境 6：E1 趨勢線（兩個 lower high 連線）在情境 1 也出得來或報 NOLINE，不炸
    s = detect(o, h, l, c, mode="E1"); kinds = [x["kind"] for x in s]
    check("情境6 E1 不炸且只出合法種類", set(kinds) <= {"S1", "S3", "ABANDON", "NOSTEP3", "NOLINE"}, str(kinds))
    s = detect(o, h, l, c, mode="E2"); check("情境6 E2 不炸", set(x["kind"] for x in s) <= {"S1", "S3", "ABANDON", "NOSTEP3", "NOLINE"})
    s = detect(o, h, l, c, mode="E1", redraw_n=3); check("情境6 E4 不炸", set(x["kind"] for x in s) <= {"S1", "S3", "ABANDON", "NOSTEP3", "NOLINE"})
    # 情境 7：NaN 不炸
    c2 = c.copy(); c2[25] = np.nan; h2 = h.copy(); h2[25] = np.nan; l2 = l.copy(); l2[25] = np.nan
    try:
        detect(o, h2, l2, c2); check("情境7 NaN 不炸", True)
    except Exception as e:
        check("情境7 NaN 不炸", False, repr(e))
    # 情境 8：因果——截斷序列在 S3 訊號日，訊號仍在
    s = detect(o, h, l, c); s3 = [x for x in s if x["kind"] == "S3"]
    if s3:
        t = s3[0]["signal_raw"]; s_cut = [x for x in detect(o[:t + 1], h[:t + 1], l[:t + 1], c[:t + 1]) if x["kind"] == "S3"]
        check("情境8 截斷在訊號日仍出同一個 S3（無前視）", bool(s_cut) and s_cut[0]["signal_raw"] == t, f"{[x['signal_raw'] for x in s_cut]}")
    # 情境 9：第一步之後直接破底（沒有 HL）⇒ 結構作廢，之後突破前高也不算 S3
    o, h, l, c = _mk([(80, 0), (100, 10), (90, 10), (95, 8), (80, 12), (88, 8), (83, 8), (92, 8), (86, 8), (99, 10), (75, 12), (100, 12), (105, 8)])
    s = detect(o, h, l, c); kinds = [x["kind"] for x in s]
    check("情境9 第一步後破底 ⇒ 沒有 S3、沒有 ABANDON（HL 從未成立）", "S3" not in kinds and "ABANDON" not in kinds and "S1" in kinds, str(kinds))
    print("[wsh selftest]", "通過" if ok_all else "⛔ 失敗")
    return ok_all


if __name__ == "__main__":
    import sys
    sys.exit(0 if _selftest() else 1)
