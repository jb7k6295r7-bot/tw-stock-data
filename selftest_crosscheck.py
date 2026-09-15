#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`crosscheck.exright_identity_check` 的自測。**不連網、不碰真的 data/。**

⭐ 這一條釘的是**容差**：`0.011` 不是調出來的，是算出來的
（兩個價各自捨入到「分」⇒ 差值誤差上限 0.01）。
⛔ 調成 0.005 的話全庫有 16.6% 會誤報 ⇒ 這道閘門天天紅、然後被學會忽略。
"""
import io
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import crosscheck as C                                          # noqa: E402

OK = FAIL = 0
HEAD = ("date,stock_id,pre_close,ref_price,value,kind,open_base,"
        "limit_up,limit_down,ex_div_ref\n")


class Rec:
    """⛔ 假的 runlog：要能把 check 的結果**收下來**再判，不是印一印就算。"""

    def __init__(self):
        self.checks = []
        self.infos = []

    def info(self, a, b=""):
        self.infos.append((a, b))

    def check(self, a, cond, hint=""):
        self.checks.append((a, bool(cond), hint))


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


def run(rows, n_needed=0):
    """把幾列寫成假日檔跑一次；`n_needed` 是母體那條的門檻（測試用調低）。"""
    d = tempfile.mkdtemp(prefix="cc_")
    old = C._ROOT
    try:
        ex = os.path.join(d, "universe", "exright")
        os.makedirs(ex)
        io.open(os.path.join(ex, "2015-01-05.csv"), "w",
                encoding="utf-8").write(HEAD + "".join(rows))
        C._ROOT = d
        rec = Rec()
        # ⛔ 第七點②：斷言那條路若會丟例外就**接住再判**——
        #   不接住的話整支測試當場中斷，後面一條都不會跑，
        #   ⚠ 而突變報告上只會寫「崩潰」，看不出是哪一條斷言在守。
        try:
            C.exright_identity_check(rec)
        except Exception as ex:                                  # noqa: BLE001
            rec.infos.append(("⛔ 崩潰", f"{type(ex).__name__}: {ex}"))
        return rec
    finally:
        C._ROOT = old
        shutil.rmtree(d, ignore_errors=True)


def verdict(rec, key):
    for name, cond, _h in rec.checks:
        if key in name:
            return cond
    return None


def main():
    print("=" * 64)
    print("crosscheck ④ 除權息官方恆等式（不連網）")
    print("=" * 64)

    print("\n── ① 判準本體 ──")
    # ⭐ 官方真的回過的那一列（2353 宏碁 2015-01-05）：21.35 − 21.02 = 0.33
    #   而官方的 `權值+息值` 是 0.325605 ⇒ 差 0.004395，在容差內。
    good = ["2015-01-05,2353,21.35,21.02,0.325605,權,21.35,22.80,19.55,21.35\n"]
    ck("⭐ 官方真的那一列通過（差 0.0044）", verdict(run(good), "官方恆等式") is True)
    # ⛔ 反向：把 value 換成一個差 0.05 的數字 ⇒ 一定要紅
    bad = ["2015-01-05,2353,21.35,21.02,0.38,權,21.35,22.80,19.55,21.35\n"]
    ck("⛔ `value` 差 0.05 ⇒ 判不通過", verdict(run(bad), "官方恆等式") is False)
    # ⛔⛔ 最重要的反向：**欄位撿錯**（把 open_base 當成 ref_price）
    swap = ["2015-01-05,2353,21.35,21.35,0.325605,權,21.35,22.80,19.55,21.35\n"]
    ck("⛔⛔ 參考價被撿成開盤競價基準（21.35）⇒ 恆等式當場不成立",
       verdict(run(swap), "官方恆等式") is False)

    print("\n── ② ⭐ 容差是**算出來的**：0.011 不是 0.005 ──")
    # 兩個價各自捨入到分 ⇒ 差值誤差上限 0.01。這一列差 0.0084（實測 8033 2015-01-29）
    edge = ["2015-01-29,8033,13.60,13.11,0.481632,權,13.11,14.40,11.80,13.11\n"]
    ck("⭐ 差 0.0084 的真實列要**通過**（⛔ 0.005 的容差會把它誤報）",
       verdict(run(edge), "官方恆等式") is True)
    r = Rec()
    d = tempfile.mkdtemp(prefix="cc_")
    old = C._ROOT
    try:
        ex = os.path.join(d, "universe", "exright")
        os.makedirs(ex)
        io.open(os.path.join(ex, "a.csv"), "w", encoding="utf-8").write(HEAD + edge[0])
        C._ROOT = d
        C.exright_identity_check(r, tol=0.005)
    finally:
        C._ROOT = old
        shutil.rmtree(d, ignore_errors=True)
    ck("⛔ 而把容差調成 0.005，同一列就紅 ⇒ 證明這個數字有意義",
       verdict(r, "官方恆等式") is False)
    # ⭐ 有預設值的參數，一定要有一條**不傳它**的斷言（第七點③）
    ck("⭐ `tol` 不傳 ⇒ 走預設 0.011（⛔ 這是 `main()` 唯一會走的路）",
       verdict(run(edge), "官方恆等式") is True)

    print("\n── ③ ⛔ 母體：0 列跟全部通過長得一樣 ──")
    rec = run(good)
    ck("⭐ 只有 1 列 ⇒ 母體那一條要**紅**（⛔ 不是靜靜通過）",
       verdict(rec, "母體") is False)
    # ⛔ 三欄有一欄整批空掉 ⇒ 那些列不進母體 ⇒ 母體那條會叫
    empty = ["2015-01-05,2353,21.35,,0.325605,權,21.35,22.80,19.55,21.35\n"] * 3
    rec = run(empty)
    # ⛔⛔ 而這一條要**同時**排除「崩潰」：接住例外之後，
    #   「因為缺欄所以沒有 check」跟「因為炸了所以沒有 check」長得一模一樣。
    ck("⛔ `ref_price` 整批空掉 ⇒ 一列都比不了（⚠ 而恆等式那條會**不存在**，"
       "不是通過），⭐ 而且不可以是因為崩潰",
       verdict(rec, "官方恆等式") is None and not rec.checks
       and not any("崩潰" in a for a, _b in rec.infos),
       str(rec.infos))

    print("\n── ④ 目錄不在時不炸 ──")
    old = C._ROOT
    try:
        C._ROOT = os.path.join(tempfile.mkdtemp(prefix="cc_"), "nope")
        rec = Rec()
        C.exright_identity_check(rec)
        ck("⛔ 沒有 data/universe/exright ⇒ 只留一則 info，不崩潰也不假裝通過",
           not rec.checks and len(rec.infos) == 1)
    finally:
        C._ROOT = old

    # ══════════════════════════════════════════════════════════════
    # ⑤ 自營商分項恆等式：自行買賣 ＋ 避險 ＝ 自營商合計
    #
    # ⭐ 它抓得到的是**我方這一端**的錯（欄位對錯位、解析抓錯欄），
    #   ⛔ 不是「官方的數字對不對」——三個欄來自**同一發回應**。
    #   ⚠ 而那正是 CLAUDE.md 四點二③：`dealer_self` 整欄填成別的數字，
    #     **沒有任何現有閘門看得出來**。
    # ══════════════════════════════════════════════════════════════
    print("\n[⑤] 自營商分項恆等式")
    d5 = tempfile.mkdtemp(prefix="cc5_")
    old5 = C._ROOT
    try:
        C._ROOT = os.path.join(d5, "data")
        base = os.path.join(C._ROOT, "universe", "inst")
        os.makedirs(base)
        hdr = "date,stock_id,foreign,trust,dealer,total,dealer_self,dealer_hedge\n"
        # 兩天全對
        io.open(os.path.join(base, "2026-09-01.csv"), "w", encoding="utf-8").write(
            hdr + "2026-09-01,2330,1,2,30,33,10,20\n"
                  "2026-09-01,2317,1,2,-5,-2,-8,3\n")
        io.open(os.path.join(base, "2026-09-02.csv"), "w", encoding="utf-8").write(
            hdr + "2026-09-02,2330,1,2,0,3,0,0\n")
        tot, bad = C.dealer_identity()
        ck("⑤ 三列都可驗、⛔ 一列都不不符", (tot, bad) == (3, []), f"{tot}｜{bad}")
        rec = Rec()
        C.dealer_check(rec)
        ck("  ⛔ 但母體太小 ⇒ 那條「有母體可掃」要紅"
           "（⚠ 0 列跟全部通過長得一樣）",
           verdict(rec, "母體") is False, str(rec.checks))
        ck("  ⭐ 而恆等式那一條是綠的", verdict(rec, "全數成立") is True,
           str(rec.checks))

        # ⛔ 一列對錯位 ⇒ 一定要紅，而且點名是誰
        io.open(os.path.join(base, "2026-09-03.csv"), "w", encoding="utf-8").write(
            hdr + "2026-09-03,1101,1,2,30,33,10,19\n")
        tot2, bad2 = C.dealer_identity()
        ck("⛔ 一列不符 ⇒ 抓到", len(bad2) == 1, str(bad2))
        ck("  ⭐ 而且講得出**哪一天、哪一檔、三個數字各是多少**",
           bad2[0][:2] == ("2026-09-03", "1101") and bad2[0][2:] == (10, 19, 30),
           str(bad2))
        rec = Rec()
        C.dealer_check(rec)
        ck("  ⭐ `rl.check` 也跟著紅", verdict(rec, "全數成立") is False,
           str(rec.checks))
        # ⛔ 光是「紅了」不夠：報表上要**點名是哪一列**
        #   ⚠ 否則下一個人只看到「1 列不符」，得自己去 4,811,538 列裡找。
        _hint = next((h for a, _c, h in rec.checks if "全數成立" in a), "")
        ck("  ⭐⭐ 而 ✗ 的細節要**點名**（哪一天、哪一檔）"
           "⛔ 只給個數 = 叫人去 480 萬列裡自己找",
           "2026-09-03" in _hint and "1101" in _hint, repr(_hint))

        # ⚠ 空欄（還沒回補的舊檔）**不算不符**——⛔ 否則回補到一半就天天紅
        io.open(os.path.join(base, "2026-09-04.csv"), "w", encoding="utf-8").write(
            "date,stock_id,foreign,trust,dealer,total\n2026-09-04,2330,1,2,30,33\n")
        tot3, bad3 = C.dealer_identity()
        ck("⚠ 沒有那兩欄的舊檔 ⇒ **整個跳過**，⛔ 不算不符"
           "（否則回補到一半天天紅）", len(bad3) == 1 and tot3 == tot2, f"{tot3}｜{bad3}")
        # ⚠ 有欄但值是空的也一樣
        io.open(os.path.join(base, "2026-09-07.csv"), "w", encoding="utf-8").write(
            hdr + "2026-09-07,2330,1,2,30,33,,\n")
        tot4, bad4 = C.dealer_identity()
        ck("  ⭐ 欄在但值是空的也跳過（⛔ 空字串 int() 會炸）",
           len(bad4) == 1 and tot4 == tot2, f"{tot4}｜{bad4}")

        # ⭐ 上櫃那一半也要掃到（⛔ 只掃 inst 會漏掉一半的庫）
        base2 = os.path.join(C._ROOT, "universe", "otcinst")
        os.makedirs(base2)
        io.open(os.path.join(base2, "2026-09-01.csv"), "w", encoding="utf-8").write(
            hdr + "2026-09-01,6488,1,2,30,33,10,21\n")
        tot5, bad5 = C.dealer_identity()
        ck("⭐⭐ `otcinst` 也掃（⛔ 只掃 inst 會漏掉一半的庫）",
           len(bad5) == 2 and any(b[1] == "6488" for b in bad5), str(bad5))
    finally:
        C._ROOT = old5
        shutil.rmtree(d5, ignore_errors=True)

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
