#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`reduce_shares_check` 的自測。**不連網、不碰真的 data/。**

⭐ 這一支要釘的是那個**最貴的一格**：兩種減資的算式不一樣。
⛔ 用錯的後果是**系統性偏差**，不是隨機誤差——而它看起來完全正常。
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import reduce_shares_check as R                                # noqa: E402

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


def val(fn, *a, **k):
    """→ 呼叫結果；⭐ 丟例外就回一個絕不會相等的東西，**不讓它中斷整支測試**。

    ⛔ CLAUDE.md 第七點：斷言那條路崩掉的話，後面一條都不會跑，
    ⚠ 而突變驗只會看到「崩潰」而不是「紅 N 條」——那讀起來像工具壞了。
    """
    try:
        return fn(*a, **k)
    except Exception as e:                                    # noqa: BLE001
        return ("💥", f"{type(e).__name__}: {e}")


def main():
    print("=" * 64)
    print("reduce_shares_check：兩種減資的算式不一樣（不連網）")
    print("=" * 64)

    print("\n── ① 分類：哪一種有退還現金 ──")
    ck("`退還股款` 是現金型", R.is_cash("退還股款"))
    ck("`現金減資` 是現金型", R.is_cash("現金減資"))
    ck("⛔ `彌補虧損` **不是**現金型（股東沒拿到錢）", not R.is_cash("彌補虧損"))
    ck("空值不會爆，而且判成非現金型", not R.is_cash(None) and not R.is_cash(""))
    ck("前後空白照樣判得出來（⛔ CSV 讀進來常帶空白）", R.is_cash(" 退還股款 "))

    print("\n── ② 算式：拿**真實事件**驗（⛔ 不是我編的數字）──")
    # 1563 巧新 2026-09-07｜shares 225,608,140 → 169,206,105（＝ 0.75）
    #   官方參考價 84.66。⭐ 這三個數字都在 repo 裡查得到。
    got = R.expected_ref(66.00, 0.75, True)
    ck("1563 現金型：(66.00 − 10×0.25) ÷ 0.75 ⇒ 官方的 84.66",
       abs(got - 84.66) <= R.TOL, f"算出 {got:.4f}")
    # 6176 瑞儀 2026-08-24｜465,027,263 → 348,770,447（＝ 0.75）｜官方 105.06
    got = R.expected_ref(81.30, 0.75, True)
    ck("6176 現金型：(81.30 − 2.50) ÷ 0.75 ⇒ 官方的 105.06",
       abs(got - 105.06) <= R.TOL, f"算出 {got:.4f}")
    # 4174 浩鼎 2026-02-03｜彌補虧損｜前收 27.6 → 官方 55.2（換股比 0.5）
    got = R.expected_ref(27.60, 0.5, False)
    ck("4174 彌補虧損型：27.60 ÷ 0.5 ⇒ 官方的 55.20",
       abs(got - 55.20) <= R.TOL, f"算出 {got:.4f}")

    print("\n── ③ ⛔ 反向：用錯算式會差多少（這一節是本支存在的理由）──")
    wrong = R.expected_ref(66.00, 0.75, False)      # 現金型誤用彌補虧損式
    ck("⛔ 現金型誤套彌補虧損式 ⇒ 88.00，比官方的 84.66 高 3.34（3.9%）",
       abs(wrong - 88.00) < 0.01 and abs(wrong - 84.66) > 3.0,
       f"算出 {wrong:.4f}")
    ck("★ 反向驗：兩種算式**真的不同**（⛔ 一樣的話上面每一條都是假的）",
       R.expected_ref(66.00, 0.75, True) != R.expected_ref(66.00, 0.75, False))
    # ⭐ 而 88.00 正是 TradingView 2026-09-13 實測回的值（87.99978）
    ck("⭐ 88.00 就是 TradingView 量到的那個數（87.99978）"
       "⇒ ⛔ 它的還原只做股數、沒扣退還的現金",
       abs(wrong - 87.99978) < 0.01, f"算出 {wrong:.4f}")

    print("\n── ④ 總價值連續：⭐ 我方那個 factor 才是對報酬率對的那一個 ──")
    keep, ref, pre = 0.75, 84.66, 66.00
    cash_back = R.PAR * (1 - keep)
    ck("0.75 股 × 84.66 ＋ 退還 2.50 元 ＝ 前收 66.00（總價值連續）",
       abs(keep * ref + cash_back - pre) <= 0.01,
       f"{keep * ref + cash_back:.4f}")
    ck("⛔ 而純股數還原（88.00）**做不到**總價值連續",
       abs(keep * 88.00 + cash_back - pre) > 1.0,
       f"{keep * 88.00 + cash_back:.4f}")

    print("\n── ⑤ 面額是 10（⛔ 改了它，現金型整批會歪）──")
    ck("`PAR` 是 10.0", R.PAR == 10.0, str(R.PAR))

    print("\n── ⑥ `shares_around`：要找**前一個有值**的，⛔ 不是前一列 ──")
    import tempfile, shutil
    d = tempfile.mkdtemp(prefix="rsc_")
    old = R.STOCKS
    try:
        R.STOCKS = d
        io.open(os.path.join(d, "9999.csv"), "w", encoding="utf-8").write(
            "date,close,shares\n"
            "2026-01-05,10,1000000\n"
            "2026-01-06,10,\n"          # ⚠ 空的：上市的 shares 常常是空的
            "2026-01-07,10,\n"
            "2026-01-08,10,750000\n")
        a, b = R.shares_around("9999", "2026-01-08")
        ck("跳過中間兩天空值，抓到 2026-01-05 那筆 1,000,000",
           (a, b) == (750000.0, 1000000.0), f"{(a, b)}")
        ck("⛔ 問一個不存在的日期 ⇒ 回 (None, None)，不爆",
           R.shares_around("9999", "2026-02-02") == (None, None))
        ck("⛔ 問一個沒有個股檔的代號 ⇒ 回 (None, None)，不爆",
           R.shares_around("0000", "2026-01-08") == (None, None))
    finally:
        R.STOCKS = old
        shutil.rmtree(d, ignore_errors=True)

    print("\n── ⑦ ⛔⛔ `kind` 有兩套詞彙，⇒ 一律**包含**比對 ──")
    # 上市 息/權/權息　　上櫃 除息/除權/除權息（2026-09-13 全庫實測，見 READ_CONTRACT）
    for k in ("權", "權息", "除權", "除權息"):
        ck(f"`{k}` 有股數那一半", R.has_share_part(k))
    for k in ("息", "除息"):
        ck(f"⛔ `{k}` **沒有**股數那一半", not R.has_share_part(k))
    for k in ("息", "權息", "除息", "除權息"):
        ck(f"`{k}` 有現金那一半", R.has_cash_part(k))
    for k in ("權", "除權"):
        ck(f"⛔ `{k}` **沒有**現金那一半", not R.has_cash_part(k))
    ck("空值不會爆", not R.has_share_part(None) and not R.has_cash_part(None))
    # ⭐ 反向那一條才是主角：整串相等會靜靜地只拿到上市
    ck("⛔ `kind == '權'` 這種寫法會漏掉上櫃的 `除權`（本測就是在擋這個）",
       R.has_share_part("除權") and "除權" != "權")

    print("\n── ⑦b 全 repo 掃：有沒有人拿 `kind` 去做**整串相等**比對 ──")
    import ast
    LIT = {"權", "除權", "權息", "除權息", "息", "除息"}
    bad = []
    for fn in sorted(x for x in os.listdir(HERE) if x.endswith(".py")):
        if fn.startswith("selftest_"):
            continue
        try:
            tree = ast.parse(io.open(os.path.join(HERE, fn), encoding="utf-8").read())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare):
                continue
            for op, cmp_ in zip(node.ops, node.comparators):
                if isinstance(op, (ast.Eq, ast.NotEq)) and \
                        isinstance(cmp_, ast.Constant) and cmp_.value in LIT:
                    bad.append(f"{fn}:{node.lineno}")
    # ⛔ 比的是 **AST**，不是字串——那六個字在說明文字裡到處都有
    ck("⛔ 沒有任何一支拿 kind 的字面值做 ==／!=（⇒ 會靜靜地只拿到一個市場）",
       not bad, "、".join(bad))

    print("\n── ⑧ `shares_after`：往後找**第一個變過**的值（配股會落後十幾天）──")
    d = tempfile.mkdtemp(prefix="rsc2_")
    old = R.STOCKS
    try:
        R.STOCKS = d
        io.open(os.path.join(d, "8888.csv"), "w", encoding="utf-8").write(
            "date,close,shares\n"
            "2026-01-05,10,1000000\n"
            "2026-01-06,10,1000000\n"      # ← 事件日，股數還沒更新
            "2026-01-07,10,\n"             # ⚠ 空的一天不算一格
            "2026-01-08,10,1000000\n"
            "2026-01-09,10,1250000\n")     # ← 這一天才變
        # ⚠ lag 數的是「**有 shares 值**的那些天」，⛔ 不是日曆天也不是全部交易日
        #   ⇒ 01-07 空值那天不算一格 ⇒ 01-06 → 01-09 是 **2**，不是 3
        ck("⭐ 事件日股數還沒更新 ⇒ 往後找到 2026-01-09 那筆，lag=2（空值那天不算）",
           val(R.shares_after, "8888", "2026-01-06") == (1000000.0, 1250000.0, 2),
           str(val(R.shares_after, "8888", "2026-01-06")))
        ck("⛔ 視窗只給 2 天就找不到（⇒ 算不了，⛔ 不是硬湊一個值）",
           val(R.shares_after, "8888", "2026-01-06", window=2) == (None, None, None))
        io.open(os.path.join(d, "7777.csv"), "w", encoding="utf-8").write(
            "date,close,shares\n2026-01-05,10,1000000\n2026-01-06,10,1000000\n")
        ck("⛔ 股數從頭到尾沒變 ⇒ (None, None, None)，⛔ 不回一個比值 1",
           val(R.shares_after, "7777", "2026-01-06") == (None, None, None))
        ck("⛔ 事件日在序列最前面 ⇒ 沒有「事件前」可用 ⇒ 算不了",
           val(R.shares_after, "8888", "2026-01-05") == (None, None, None))
        # ⛔⛔ `shares` 欄出現 **0** 是這個庫已經有前例的壞法（興櫃 close=0 那一族）。
        #   ⚠ 0 混進來的表現**不是報錯**：它會變成除以 0，或一個天文數字的比值。
        io.open(os.path.join(d, "6666.csv"), "w", encoding="utf-8").write(
            "date,close,shares\n"
            "2026-01-05,10,0\n"            # ⛔ 0：要被當成「沒有值」丟掉
            "2026-01-06,10,1000000\n"
            "2026-01-07,10,1250000\n")
        ck("⛔ shares 是 0 的那一列要被丟掉（⛔ 不可以拿它當事件前的基準）",
           val(R.shares_after, "6666", "2026-01-07") == (1000000.0, 1250000.0, 0),
           str(val(R.shares_after, "6666", "2026-01-07")))
        ck("⛔ 而 0 那天本身問不出「事件前」（它前面只剩 0）⇒ 算不了",
           val(R.shares_after, "6666", "2026-01-06") == (None, None, None),
           str(val(R.shares_after, "6666", "2026-01-06")))
    finally:
        R.STOCKS = old
        shutil.rmtree(d, ignore_errors=True)

    print("\n── ⑤b `PAR × 比例` 是**假設**，⛔ 不是規則 ──")
    # 官方參考價隱含的每股退還 = 前收 − keep × 參考價
    ck("1563：隱含退還 ≈ 面額 10 × 25% = 2.50（⇒ 那一筆的假設成立）",
       abs(R.implied_cash(66.00, 0.75, 84.66) - 2.50) <= 0.01,
       f"{R.implied_cash(66.00, 0.75, 84.66):.4f}")
    # 6197 2017-10-02：keep 0.75 是乾淨的，⛔ 而隱含退還是 3.70，不是 2.50
    ck("⛔ 6197：keep 一樣是 0.75，隱含退還卻是 3.70 ⇒ **假設不成立的那 16 筆**",
       abs(R.implied_cash(31.25, 0.75, 36.73) - 3.70) <= 0.01,
       f"{R.implied_cash(31.25, 0.75, 36.73):.4f}")

    print("\n── ⑤c `official_keep`：⭐ 彌補虧損型才是真的第二來源 ──")
    ck("彌補虧損型：keep = 前收 ÷ 參考價（唯一解）",
       abs(R.official_keep(6.58, 13.33, False) - 6.58 / 13.33) < 1e-12)
    ck("現金型：沿用面額假設反推（6197 ⇒ 0.795，⛔ 跟真的 0.75 不同）",
       abs(R.official_keep(31.25, 36.73, True) - 0.79499) <= 1e-4,
       f"{R.official_keep(31.25, 36.73, True)}")
    ck("⛔ 參考價 ≤ 0 ⇒ 回 None，不爆", R.official_keep(10, 0, False) is None)
    ck("⛔ 現金型參考價剛好等於面額 ⇒ 分母 0 ⇒ 回 None，不爆",
       R.official_keep(10, R.PAR, True) is None)

    print("\n── ⑧b `check_all` 的往後找：兩種漏法，⛔ 而它不可以撈到「增加」──")
    d = tempfile.mkdtemp(prefix="rsc4_")
    da = tempfile.mkdtemp(prefix="rsc4a_")
    old, olda = R.STOCKS, R.ADJ
    try:
        R.STOCKS, R.ADJ = d, da
        # 減資 25%（現金型）：前收 66 ⇒ (66 − 2.5) ÷ 0.75 = 84.67
        adj = ("date,factor,cum_factor,pre_close,ref_price,kind,event\n"
               "2026-01-06,1,1,66,84.67,退還股款,reduce\n")
        io.open(os.path.join(da, "5555.csv"), "w", encoding="utf-8").write(adj)

        # ① 事件日**不是交易日**（颱風休市 ⇒ 全市場那天沒有日檔）
        io.open(os.path.join(d, "5555.csv"), "w", encoding="utf-8").write(
            "date,close,shares\n2026-01-05,66,1000000\n2026-01-07,84,750000\n")
        _r, st, _ra = val(R.check_all)
        ck("⭐ 事件日碰到休市（沒有那一列）⇒ 往後找，照樣算得出來",
           st.get("現金型｜對得上") == 1, str(dict(st)))
        ck("　　而它會記下用的是哪一條路（`shares_via`）",
           _r and _r[0].get("shares_via") == "往後找", str(_r))

        # ② 股數**更新落後**：事件日當天股數還沒變
        io.open(os.path.join(d, "5555.csv"), "w", encoding="utf-8").write(
            "date,close,shares\n2026-01-05,66,1000000\n"
            "2026-01-06,84,1000000\n2026-01-08,84,750000\n")
        _r, st, _ra = val(R.check_all)
        ck("⭐ 股數更新落後 ⇒ 往後找，照樣算得出來",
           st.get("現金型｜對得上") == 1, str(dict(st)))

        # ③ ⛔⛔ 反向那一條才是主角：往後找可能撈到**增加**（增資／可轉債轉換）
        #    ⇒ keep > 1 ⇒ 會生出一個「看起來正常」的假參考價。⛔ 一定要擋掉。
        io.open(os.path.join(d, "5555.csv"), "w", encoding="utf-8").write(
            "date,close,shares\n2026-01-05,66,1000000\n"
            "2026-01-06,84,1000000\n2026-01-08,84,1200000\n")
        _r, st, _ra = val(R.check_all)
        ck("⛔⛔ 往後找撈到的是**增加** ⇒ 算不了，⛔ 不可以拿它算出一個假參考價",
           st.get("算不了：問不到變少的股數") == 1 and not _r, str(dict(st)))

        # ④ 事件日那一格本來就讀得到 ⇒ ⛔ 不可以改走往後找
        io.open(os.path.join(d, "5555.csv"), "w", encoding="utf-8").write(
            "date,close,shares\n2026-01-05,66,1000000\n"
            "2026-01-06,84,750000\n2026-01-08,84,500000\n")
        _r, st, _ra = val(R.check_all)
        ck("⛔ 事件日讀得到就用事件日（⛔ 不可以被後面更小的股數蓋過去）",
           _r and _r[0].get("shares_via") == "事件日"
           and _r[0].get("keep") == "0.750000", str(_r))
    finally:
        R.STOCKS, R.ADJ = old, olda
        shutil.rmtree(d, ignore_errors=True)
        shutil.rmtree(da, ignore_errors=True)

    print("\n── ⑧c 「只差在分位」要分開報，⛔ 但仍然算對不上 ──")
    d = tempfile.mkdtemp(prefix="rsc5_")
    da = tempfile.mkdtemp(prefix="rsc5a_")
    old, olda = R.STOCKS, R.ADJ
    try:
        R.STOCKS, R.ADJ = d, da
        # 高價股：keep 只差 0.03%，⛔ 而在價格空間差 0.05 元以上
        #   6271 2020-11-30 實例：前收 139.00、官方 180.74、我方 keep 0.755760
        io.open(os.path.join(d, "4444.csv"), "w", encoding="utf-8").write(
            "date,close,shares\n2026-01-05,139,1000000\n2026-01-06,180,755760\n")
        io.open(os.path.join(da, "4444.csv"), "w", encoding="utf-8").write(
            "date,factor,cum_factor,pre_close,ref_price,kind,event\n"
            "2026-01-06,1,1,139,180.74,退還股款,reduce\n")
        _r, st, _ra = val(R.check_all)
        ck("⭐ 高價股：價格差 > 5 分、⛔ 而 keep 只差 0.03% ⇒ 進「只差在分位」那一格",
           st.get("現金型｜對不上（⚠ 只差在分位）") == 1, str(dict(st)))
        ck("　　⛔ 而它**仍然算對不上**（⛔ 不可以被算成對得上）",
           not st.get("現金型｜對得上"), str(dict(st)))
        # keep 真的不一樣（差 50%）⇒ ⛔ 不可以進「只差在分位」
        io.open(os.path.join(d, "4444.csv"), "w", encoding="utf-8").write(
            "date,close,shares\n2026-01-05,8.8,1000000\n2026-01-06,24,552630\n")
        io.open(os.path.join(da, "4444.csv"), "w", encoding="utf-8").write(
            "date,factor,cum_factor,pre_close,ref_price,kind,event\n"
            "2026-01-06,1,1,8.80,24.44,彌補虧損,reduce\n")
        _r, st, _ra = val(R.check_all)
        ck("⛔ keep 差 53%（4502 實例）⇒ 是真的對不上，⛔ 不是分位",
           st.get("彌補虧損型｜對不上") == 1, str(dict(st)))
    finally:
        R.STOCKS, R.ADJ = old, olda
        shutil.rmtree(d, ignore_errors=True)
        shutil.rmtree(da, ignore_errors=True)

    print("\n── ⑧d `tally`：⛔ 分位那一群不可以掉在外面 ──")
    st = {"現金型｜對得上": 5, "現金型｜對不上": 2,
          "現金型｜對不上（⚠ 只差在分位）": 3, "算不了：問不到變少的股數": 7}
    ck("⛔ 「只差在分位」算進**對不上**（⛔ endswith 會漏掉它）",
       R.tally(st) == (5, 5, 3, 7), str(R.tally(st)))
    ck("⭐ 對得上 ＋ 對不上 ＝ 可算的總數（⛔ 沒有一筆掉在外面）",
       sum(R.tally(st)[:2]) == 5 + 2 + 3, str(R.tally(st)))
    ck("空的統計不會爆", R.tally({}) == (0, 0, 0, 0))
    # ⭐ 第七點③：測完純函式，再掃原始碼確認**呼叫點**真的那樣叫
    import ast
    src = io.open(os.path.join(HERE, "reduce_shares_check.py"), encoding="utf-8").read()
    fn = next(n for n in ast.walk(ast.parse(src))
              if isinstance(n, ast.FunctionDef) and n.name == "main")
    calls = {n.func.id for n in ast.walk(fn)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    ck("⭐ `main()` 真的呼叫 `tally()`（⛔ 不是自己又數一份）", "tally" in calls,
       str(sorted(calls)))
    # ⛔ 而 `main()` 不可以自己**再數一次分類**——那就是第二份 `tally()`。
    #   ⚠ 那條不變式**故意**用另一種數法當右邊（濾掉「（參考）」前綴之後全加），
    #     ⛔ 兩邊都用 `tally()` 的話它永遠成立 ⇒ 那不是斷言是恆等式。
    #   ⇒ 判準寫成：`main()` 裡不可以有**提到分類字眼**的濾鍵加總。
    CLS_WORDS = ("對得上", "對不上", "算不了", "只差在分位")
    def _mentions_cls(node):
        return any(isinstance(x, ast.Constant) and isinstance(x.value, str)
                   and any(w in x.value for w in CLS_WORDS)
                   for x in ast.walk(node))
    ck("⛔ `main()` 裡沒有第二份「照分類濾鍵再數」的寫法",
       not [n for n in ast.walk(fn)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            and n.func.id == "sum"
            and any(isinstance(a, (ast.GeneratorExp, ast.ListComp))
                    and a.generators[0].ifs and _mentions_cls(a)
                    for a in n.args)])

    print("\n── ⑧e ⭐ 第三個來源：官方**換股比率**（⛔ 不是從價格推的）──")
    d = tempfile.mkdtemp(prefix="rsc6_")
    da = tempfile.mkdtemp(prefix="rsc6a_")
    old, olda, oldt = R.STOCKS, R.ADJ, R.OFFICIAL_TABLE
    try:
        R.STOCKS, R.ADJ = d, da
        R.OFFICIAL_TABLE = os.path.join(d, "otc_reduce_history.csv")
        # 6241 實例：官方換股比率 729.644150／1000、官方參考價 18.98、前收 13.85
        #   ⇒ 官方兩欄互相一致（0.729644 vs 0.729715）
        #   ⛔ 而我方 shares 算出 0.934983 ——**異類是我方 shares**
        io.open(R.OFFICIAL_TABLE, "w", encoding="utf-8").write(
            "date,stock_id,shares_per_1000\n2026-01-06,3333,729.644150\n")
        io.open(os.path.join(d, "3333.csv"), "w", encoding="utf-8").write(
            "date,close,shares\n2026-01-05,13.85,48700000\n"
            "2026-01-06,18.98,45533670\n")
        io.open(os.path.join(da, "3333.csv"), "w", encoding="utf-8").write(
            "date,factor,cum_factor,pre_close,ref_price,kind,event\n"
            "2026-01-06,1,1,13.85,18.98,彌補虧損,reduce\n")
        _r, st, _ra = val(R.check_all)
        ck("⭐ 官方換股比率站在參考價那邊 ⇒ 判成「異類是我方 shares」",
           st.get("彌補虧損型｜對不上（⛔ 異類是我方 shares）") == 1, str(dict(st)))
        ck("　　而逐筆結果留下那個比率（⛔ 不是空白）",
           _r and _r[0].get("keep_ratio_official", "").startswith("0.7296"), str(_r))
        # ⛔ 反向①：官方那張表**不見了** ⇒ 不可以還判成「異類是我方 shares」
        os.remove(R.OFFICIAL_TABLE)
        _r, st, _ra = val(R.check_all)
        ck("⛔ 官方表讀不到 ⇒ 退回普通的「對不上」，⛔ 不可以栽贓給 shares",
           st.get("彌補虧損型｜對不上") == 1
           and not st.get("彌補虧損型｜對不上（⛔ 異類是我方 shares）"), str(dict(st)))
        ck("⛔ 而「查得到官方換股比率」要是 0（⇒ runlog 上那條斷言會紅）",
           not st.get(R.INFO + "⭐ 查得到官方換股比率"), str(dict(st)))
        # ⛔ 反向②：官方兩欄**互相矛盾**時，⛔ 不可以說「異類是我方 shares」
        io.open(R.OFFICIAL_TABLE, "w", encoding="utf-8").write(
            "date,stock_id,shares_per_1000\n2026-01-06,3333,500.000000\n")
        _r, st, _ra = val(R.check_all)
        ck("⛔ 官方換股比率跟官方參考價**自己就對不上** ⇒ 退回普通的「對不上」",
           st.get("彌補虧損型｜對不上") == 1
           and not st.get("彌補虧損型｜對不上（⛔ 異類是我方 shares）"), str(dict(st)))
        # ⭐ 反向③：官方比率跟我方 shares **一致**時，⛔ 也不可以栽贓給 shares
        io.open(R.OFFICIAL_TABLE, "w", encoding="utf-8").write(
            "date,stock_id,shares_per_1000\n2026-01-06,3333,934.983000\n")
        _r, st, _ra = val(R.check_all)
        ck("⛔ 官方比率跟我方 shares 一致 ⇒ ⛔ 不是 shares 的問題",
           not st.get("彌補虧損型｜對不上（⛔ 異類是我方 shares）"), str(dict(st)))
        # ⭐ 反向③b：⚠ 上面那一格**隔離不了**那個條件——官方比率跟參考價差太多，
        #   前一個條件就先擋掉了。⇒ 要一格「三方都一致、只是價格差超過 5 分」的：
        #   高價股 pre 139.00／官方 ref 180.74 ⇒ ko = 0.768994
        #   我方 shares keep 0.768700（差 0.0003）⇒ 價格差 0.088 > 0.05
        io.open(R.OFFICIAL_TABLE, "w", encoding="utf-8").write(
            "date,stock_id,shares_per_1000\n2026-01-06,3333,768.700000\n")
        io.open(os.path.join(d, "3333.csv"), "w", encoding="utf-8").write(
            "date,close,shares\n2026-01-05,139,10000000\n"
            "2026-01-06,180,7687000\n")
        io.open(os.path.join(da, "3333.csv"), "w", encoding="utf-8").write(
            "date,factor,cum_factor,pre_close,ref_price,kind,event\n"
            "2026-01-06,1,1,139.00,180.74,彌補虧損,reduce\n")
        _r, st, _ra = val(R.check_all)
        ck("⭐ 三方都一致、只是價格差超過 5 分 ⇒ 要落在「只差在分位」",
           st.get("彌補虧損型｜對不上（⚠ 只差在分位）") == 1, str(dict(st)))
        ck("⛔ 而**不可以**被判成「異類是我方 shares」（官方比率跟我方 shares 一樣）",
           not st.get("彌補虧損型｜對不上（⛔ 異類是我方 shares）"), str(dict(st)))
    finally:
        R.STOCKS, R.ADJ, R.OFFICIAL_TABLE = old, olda, oldt
        shutil.rmtree(d, ignore_errors=True)
        shutil.rmtree(da, ignore_errors=True)

    print("\n── ⑧f ⛔ 參考型的鍵不可以混進分類的加總 ──")
    # ⚠ 參考型的鍵**故意寫成含有分類字眼**——⛔ 現在的鍵剛好沒撞到那幾個字，
    #   而「靠命名沒撞到」不是保護：判準必須是**前綴**，不是字眼。
    st = {"現金型｜對得上": 5, "現金型｜對不上": 2, "算不了：問不到變少的股數": 7,
          R.INFO + "官方兩欄對得上": 99, R.INFO + "算不了：沒查到": 88}
    ck("⛔ `tally()` 靠**前綴**排除參考型的鍵（⛔ 不是靠字眼剛好沒撞到）",
       R.tally(st) == (5, 2, 0, 7), str(R.tally(st)))

    print("\n── ⑨ `exright_scan`：三格分類，⛔ 而它判不出對錯 ──")
    d = tempfile.mkdtemp(prefix="rsc3_")
    da = tempfile.mkdtemp(prefix="rsc3a_")
    old, olda, oldwin = R.STOCKS, R.ADJ, R.EX_WIN
    try:
        R.STOCKS, R.ADJ = d, da
        io.open(os.path.join(d, "1111.csv"), "w", encoding="utf-8").write(
            "date,close,shares\n2026-01-05,10,1000000\n2026-01-06,10,1100000\n")
        io.open(os.path.join(da, "1111.csv"), "w", encoding="utf-8").write(
            "date,factor,cum_factor,pre_close,ref_price,kind,event\n"
            # 純無償配股 100 股/千股 ⇒ 股數比 = 1/1.1 = 0.909091，factor 相同
            "2026-01-06,0.90909091,1,11,10,權,exright\n")
        res, stat = val(R.exright_scan)
        if not isinstance(stat, dict) and not hasattr(stat, 'get'):
            res, stat = [], {}   # ⛔ 崩了 ⇒ 下面每一條都會判紅，⛔ 不中斷
        ck("純無償配股 ⇒ 落在「＝股數比」那一格",
           stat.get("純股數｜＝股數比（純無償配股）") == 1, str(dict(stat)))
        io.open(os.path.join(da, "1111.csv"), "w", encoding="utf-8").write(
            "date,factor,cum_factor,pre_close,ref_price,kind,event\n"
            # 現增：股數 ×1.1，⭐ 而股東付了錢 ⇒ 價格幾乎不動 ⇒ factor ≈ 1
            "2026-01-06,0.99500000,1,11,10.945,除權,exright\n")
        res, stat = val(R.exright_scan)
        if not isinstance(stat, dict) and not hasattr(stat, 'get'):
            res, stat = [], {}   # ⛔ 崩了 ⇒ 下面每一條都會判紅，⛔ 不中斷
        ck("⭐ 帶現增 ⇒ 落在「＞股數比」那一格（⛔ 上櫃詞彙 `除權` 也要吃得到）",
           stat.get("純股數｜＞股數比（有現增）") == 1, str(dict(stat)))
        io.open(os.path.join(da, "1111.csv"), "w", encoding="utf-8").write(
            "date,factor,cum_factor,pre_close,ref_price,kind,event\n"
            # 除權息：股數 ×1.1 ＋ 配息 ⇒ factor 比純股數比再低一截
            "2026-01-06,0.86363636,1,11,9.5,除權息,exright\n")
        res, stat = val(R.exright_scan)
        if not isinstance(stat, dict) and not hasattr(stat, 'get'):
            res, stat = [], {}   # ⛔ 崩了 ⇒ 下面每一條都會判紅，⛔ 不中斷
        ck("除權息 ⇒ 落在「股數＋現金｜＜股數比」那一格",
           stat.get("股數＋現金｜＜股數比（還有現金流出）") == 1, str(dict(stat)))
        io.open(os.path.join(da, "1111.csv"), "w", encoding="utf-8").write(
            "date,factor,cum_factor,pre_close,ref_price,kind,event\n"
            "2026-01-06,0.96000000,1,11,10.56,息,exright\n")
        res, stat = val(R.exright_scan)
        if not isinstance(stat, dict) and not hasattr(stat, 'get'):
            res, stat = [], {}   # ⛔ 崩了 ⇒ 下面每一條都會判紅，⛔ 不中斷
        ck("⛔ 純除息（沒有股數那一半）整筆跳過，⛔ 不算進任何一格",
           not res and not stat, str(dict(stat)))
    finally:
        R.STOCKS, R.ADJ, R.EX_WIN = old, olda, oldwin
        shutil.rmtree(d, ignore_errors=True)
        shutil.rmtree(da, ignore_errors=True)

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
