#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`factor_limit_check` 的自測。**不連網、不碰真的 data/。**

⭐ 這一支要釘的兩件事，⛔ 缺一件這道閘門就沒有用：
① 排除事件日之後才判「有沒有硬性上限」——⚠ 不排除的話**每一檔都會被判成無限制**
② 無漲跌幅限制的證券**不可以**被套上這一條（那 3 檔 ETF 是真的大跌）
"""
import io
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import factor_limit_check as F                                 # noqa: E402

OK = FAIL = 0


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  ✗    {name}" + (f"｜{hint}" if hint else ""))


def mkser(n, start="2020-01-02", step=0.001, base=100.0):
    """→ 一段每天只動 ±0.1% 的價格序列（⇒ 一定會被判成有硬性上限）。"""
    import datetime as dt
    d = dt.date.fromisoformat(start)
    out = []
    for i in range(n):
        while d.weekday() >= 5:
            d += dt.timedelta(days=1)
        out.append((d.isoformat(), base * (1 + step * (i % 3 - 1))))
        d += dt.timedelta(days=1)
    return out


def main():
    print("=" * 64)
    print("factor_limit_check：用交易所的漲跌停證明因子錯（不連網）")
    print("=" * 64)

    print("\n── ① `has_hard_limit`：⛔ 一定要排除事件日 ──")
    ser = mkser(600)
    ck("每天只動 0.1% 的序列 ⇒ 判成有硬性上限", F.has_hard_limit(ser, set())[0])
    # ⭐ 插一根 −30% 的事件日跳空
    ser2 = list(ser)
    ser2[300] = (ser2[300][0], ser2[300][1] * 0.70)
    ck("⛔ 插一根 −30% 的跳空、而**不告訴它那是事件日** ⇒ 判成無限制",
       not F.has_hard_limit(ser2, set())[0])
    ck("⭐ 同一根跳空、**告訴它那是事件日** ⇒ 還是判成有硬性上限（＝排除生效）",
       F.has_hard_limit(ser2, {ser2[300][0], ser2[301][0]})[0],
       str(F.has_hard_limit(ser2, {ser2[300][0], ser2[301][0]})))
    ck("⛔ 天數不夠（< 500）⇒ 判不出來，不可以當成有上限",
       not F.has_hard_limit(mkser(100), set())[0])

    print("\n── ② `check_all`：⭐ 超出 ref×1.10 要抓到，⛔ 沒超出不可以叫 ──")
    d = tempfile.mkdtemp(prefix="flc_")
    da = os.path.join(d, "adj"); ds = os.path.join(d, "stocks")
    os.makedirs(da); os.makedirs(ds)
    oa, os_ = F.ADJ, F.STOCKS
    try:
        F.ADJ, F.STOCKS = da, ds

        def write(code, ser, evdate, ref, close_at_ev):
            rows = list(ser)
            i = next(j for j, (dd, _) in enumerate(rows) if dd == evdate)
            rows[i] = (evdate, close_at_ev)
            io.open(os.path.join(ds, f"{code}.csv"), "w", encoding="utf-8").write(
                "date,close\n" + "".join(f"{dd},{c:.4f}\n" for dd, c in rows))
            io.open(os.path.join(da, f"{code}.csv"), "w", encoding="utf-8").write(
                "date,factor,cum_factor,pre_close,ref_price,kind,event\n"
                f"{evdate},0.9,1,100,{ref},權,exright\n")

        ev = ser[300][0]
        # 參考價 90、收盤 98.9 ⇒ 98.9/90 = 1.099 ⇒ 在漲停內
        write("1111", ser, ev, 90.0, 98.9)
        bad, checked, nhard, _how = F.check_all()
        ck("收/參考 = 1.099（漲停內）⇒ ⛔ 不可以叫", not bad and checked == 1, str(bad))
        ck("　　而母體有算到（1 檔、1 筆）", nhard == 1 and checked == 1)
        # 參考價 90、收盤 100.0 ⇒ 1.111 ⇒ 超出
        write("1111", ser, ev, 90.0, 100.0)
        bad, checked, nhard, _how = F.check_all()
        ck("⭐ 收/參考 = 1.111（超出漲停）⇒ 一定要抓到",
           len(bad) == 1 and bad[0]["stock_id"] == "1111", str(bad))
        ck("　　而它記下收/參考", bad and bad[0]["close_over_ref"].startswith("1.11"),
           str(bad[0] if bad else None))
        # 跌破跌停側
        write("1111", ser, ev, 90.0, 79.0)
        bad, _c, _n, _how = F.check_all()
        ck("⭐ 跌破跌停側（收/參考 0.878）也要抓到", len(bad) == 1, str(bad))

        # ⭐⭐ 官方說「無漲跌幅限制」的那一筆 ⇒ **不進母體**，也不算超出
        #   ⛔ 把它算成「通過」等於把母體灌水（第七點：0 筆與沒掃到長得一樣）
        write("1111", ser, ev, 90.0, 500.0)     # 收 500、參考 90 ⇒ 推論一定判超出
        bad, checked, nhard, how = F.check_all()
        ck("　（先確認沒有官方數字時它**會**被判超出）", len(bad) == 1)
        ou2 = F.UNI
        du2 = os.path.join(d, "uni2")
        os.makedirs(os.path.join(du2, "exright"))
        io.open(os.path.join(du2, "exright", f"{ev}.csv"), "w",
                encoding="utf-8").write(
            "date,stock_id,limit_up,limit_down\n"
            f"{ev},1111,\"9,999.95\",0.01\n")
        try:
            F.UNI = du2
            bad, checked, nhard, how = F.check_all()
            ck("⭐ 官方說無限制 ⇒ **不算超出**", not bad, str(bad))
            ck("⛔⛔ 而且**不進母體**（checked 要是 0，⚠ 不是 1）",
               checked == 0, f"checked={checked}｜how={dict(how)}")
            ck("⭐ 而來源欄要講出它是被官方排除的",
               how.get("官方說無限制") == 1, str(dict(how)))
        finally:
            F.UNI = ou2

        # ⛔⛔ 反向：無漲跌幅限制的證券**不可以**被判
        wild = list(ser)
        for j in (50, 120, 200, 400, 500):
            wild[j] = (wild[j][0], wild[j][1] * 1.25)      # 平常就會 +25%
        write("2222", wild, ev, 90.0, 100.0)
        os.remove(os.path.join(ds, "1111.csv")); os.remove(os.path.join(da, "1111.csv"))
        bad, checked, nhard, _how = F.check_all()
        ck("⛔⛔ 無漲跌幅限制的證券 ⇒ 整檔不判（⚠ 那 3 檔 ETF 就是這樣被排除的）",
           not bad and checked == 0 and nhard == 0, f"bad={bad} checked={checked}")
    finally:
        F.ADJ, F.STOCKS = oa, os_
        shutil.rmtree(d, ignore_errors=True)

    print("\n── ②.5 ⭐ `judge()`：官方 > 推論，而「無限制」不是「通過」──")
    # ⭐ 有官方數字就用官方的（⛔ 不再推）
    src, over = F.judge(45.00, 41.28, "2015-01-23", ("44.15", "38.40"))
    ck("⭐ 官方漲停 44.15，收 45.00 ⇒ 判超出，來源是「官方」",
       src == "官方" and over, f"{src} {over}")
    src, over = F.judge(44.15, 41.28, "2015-01-23", ("44.15", "38.40"))
    ck("⭐ 收在官方漲停上 ⇒ 不超出", src == "官方" and not over)
    # ⛔⛔ 官方說無限制 ⇒ 這一筆**沒有判準**，不可以算成通過
    src, over = F.judge(999.0, 21.92, "2020-01-16", ("9,999.95", "0.01"))
    ck("⛔⛔ 官方說無限制 ⇒ 來源是「官方說無限制」且**不算超出**",
       src == "官方說無限制" and not over, f"{src} {over}")
    # ⭐ 沒有官方數字 ⇒ 退回推論
    src, over = F.judge(45.00, 41.28, "2015-01-23", None)
    ck("⭐ 沒有官方數字 ⇒ 退回推論（⚠ 舊日檔就是這條路）",
       src == "推論" and over, f"{src} {over}")
    # ⛔ 反向：官方那兩欄是空字串／壞值 ⇒ 也要退回推論，⛔ 不是崩潰
    src, _ = F.judge(45.00, 41.28, "2015-01-23", ("", ""))
    ck("⛔ 官方那兩欄是空的 ⇒ 退回推論，不崩潰", src == "推論")
    # ⭐ 有預設值的參數，一定要有一條不傳它的斷言（第七點③）
    #   ⚠ 而 44.20 **不夠**：預設 slack 0.5% ⇒ 門檻是 44.15×1.005 = 44.37
    #   ⛔ 拿 44.20 當斷言等於在測 slack 不存在——那條會紅，而且該紅。
    ck("⭐ `slack`／`etf` 不傳 ⇒ 走預設 0.5%（⛔ 這是 `check_all` 唯一會走的路）",
       F.judge(44.50, 41.28, "2015-01-23", None)[1]
       and not F.judge(44.20, 41.28, "2015-01-23", None)[1])
    # ⭐⭐ 而「官方說無限制」一定要被 `check_all` 排除在母體之外
    d = tempfile.mkdtemp()
    oa, os_, ou = F.ADJ, F.STOCKS, F.UNI
    try:
        da, ds, du = (os.path.join(d, "adj"), os.path.join(d, "stocks"),
                      os.path.join(d, "uni"))
        os.makedirs(da); os.makedirs(ds); os.makedirs(os.path.join(du, "exright"))
        F.ADJ, F.STOCKS, F.UNI = da, ds, du
        io.open(os.path.join(du, "exright", "2020-01-16.csv"), "w",
                encoding="utf-8").write(
            "date,stock_id,pre_close,ref_price,value,kind,open_base,"
            "limit_up,limit_down\n"
            "2020-01-16,00714,22.13,21.92,0.21,息,21.92,\"9,999.95\",0.01\n")
        off = F.official_limits()
        ck("⭐ `official_limits` 從日檔讀得到官方那兩欄",
           off.get(("00714", "2020-01-16")) == ("9,999.95", "0.01"), str(off))
        ck("⛔ 而沒有那兩欄的列不會進來（⚠ 舊日檔就是這樣）",
           len(off) == 1, str(off))
        # ⛔⛔ 反向：欄在、值是空的（⚠ 官方偶爾就是給空字串）⇒ 也不可以收
        #   收了的話 `judge` 會走進「官方」那條路、拿空字串去比 ⇒ 靜靜當成沒超出
        io.open(os.path.join(du, "exright", "2020-01-17.csv"), "w",
                encoding="utf-8").write(
            "date,stock_id,pre_close,ref_price,value,kind,open_base,"
            "limit_up,limit_down\n"
            "2020-01-17,1101,22.13,21.92,0.21,息,21.92,,\n")
        off2 = F.official_limits()
        ck("⛔⛔ 欄在但值是**空的** ⇒ 不收（⚠ 收了會靜靜當成「官方說沒超出」）",
           ("1101", "2020-01-17") not in off2, str(off2))
    finally:
        F.ADJ, F.STOCKS, F.UNI = oa, os_, ou
        shutil.rmtree(d, ignore_errors=True)

    print("\n── ③ 低水位：⛔ 不可以動到真的那個檔 ──")
    n, day = F.read_low()
    ck("讀得到低水位（筆數是整數、日期是 10 碼）",
       isinstance(n, int) and len(day) == 10, f"{n},{day}")
    ck("⭐ 低水位就是今天判定過的 7 筆（⛔ 改小它 = 假裝修好了）", n == 7, str(n))

    print(f"\n[selftest] 通過 {OK}｜失敗 {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
