#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""驗 mops_probe 的【內層預算】真的會停、而且會說它沒跑到什麼。⛔ 離線、不連網。

⛔⛔ 為什麼這一支值得存在（2026-09-24 量出來的）：
  probe.yml 的 MOPS 那一步【連六趟】耗時都是 780.0 秒 ＝ probe_step.sh 的預算
  ⇒ 每趟都被 timeout 砍，⚠ 而步驟顯示 success（continue-on-error）
  ⇒ 而 mops_probe 是最後才寫檔 ⇒ 被砍 ⇒ 一個字都沒寫
  ⇒ probe_step.sh 再從 origin/main 還原 ⇒ ⛔ 一趟 13 分鐘【零資訊】
  ⇒ main 上的 _mops_probe.txt 報頭從 09-24T08:42 起就凍住，而檔尾一路累積 ✗。

⭐ 修法是內層預算（step／budget_tail）。⚠ 而一個【沒被驗過的預算】跟沒有預算
  在報告上長得一樣 ⇒ 所以這一支釘三件：
  ① 預算用完 ⇒ 那個案例【真的沒被呼叫】（⛔ 不是呼叫了然後丟掉結果）
  ② 沒跑到的案例會【逐字列進輸出】（⇒ 「沒查」與「沒有」分得開）
  ③ 全部跑完時【不可以】謊報有跳過
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mops_probe as M

OK = FAIL = 0
BEFORE = None


def ck(name, cond, hint=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  ok     " + name)
    else:
        FAIL += 1
        print("  ✗      " + name + ("｜" + hint if hint else ""))


def reset(budget):
    M._BUDGET = float(budget)
    M._T0 = __import__("time").time()
    del M._TIMES[:]
    del M._SKIPPED[:]


def main():
    global BEFORE
    # ⭐ 一開始就把真的輸出檔讀起來（⛔ 不是在結尾才想起要比）
    BEFORE = io.open(M.OUT, "rb").read() if os.path.isfile(M.OUT) else None

    print("① ⭐ 預算還有 ⇒ 案例真的跑，而且耗時進得了輸出")
    reset(60)
    out = []
    called = []
    M.step(out, "案例甲", lambda: called.append(1))
    ck("  ⭐ 案例被呼叫了", called == [1])
    ck("  ⭐ 輸出多了一行耗時（⛔ 不是只印在 log）",
       any("案例甲" in l and "秒" in l for l in out), str(out))
    ck("  ⭐ _TIMES 記下了它", [n for n, _d in M._TIMES] == ["案例甲"], str(M._TIMES))
    ck("  ⛔ 沒有把它記成跳過", M._SKIPPED == [], str(M._SKIPPED))

    print("")
    print("② ⛔⛔ 預算用完 ⇒ 案例【真的沒被呼叫】（⛔ 不是跑了才丟）")
    reset(0)
    out2 = []
    called2 = []
    r = M.step(out2, "案例乙", lambda: called2.append(1))
    ck("  ★★ 案例函式【一次都沒被呼叫】", called2 == [], str(called2))
    ck("  ⭐ 回傳 None（⚠ 代表沒跑，⛔ 不是跑了沒結果）", r is None)
    ck("  ⭐ 記進 _SKIPPED", M._SKIPPED == ["案例乙"], str(M._SKIPPED))
    ck("  ⛔ 而輸出不可以出現它的耗時行（它沒跑）",
       not any("案例乙" in l for l in out2), str(out2))

    print("")
    print("③ ⭐ budget_tail：沒跑到的要【逐字列出來】")
    reset(0)
    out3 = []
    M.step(out3, "案例丙", lambda: None)
    M.step(out3, "案例丁", lambda: None)
    M.budget_tail(out3)
    txt3 = "\n".join(out3)
    ck("  ⭐ 說了幾個沒跑到", "沒跑到】2 個" in txt3, txt3[-300:])
    ck("  ⭐ 逐字列出案例名（⛔ 只報數字＝下游還是不知道缺哪一格）",
       "案例丙" in txt3 and "案例丁" in txt3)
    ck("  ⭐⭐ 講明那是【沒查】不是【沒有】",
       "不是「查了沒有」" in txt3, txt3[-300:])

    print("")
    print("④ ★ 全部跑完時⛔ 不可以謊報有跳過（⛔ 一句永遠出現的話等於沒有話）")
    reset(60)
    out4 = []
    M.step(out4, "案例戊", lambda: None)
    M.budget_tail(out4)
    txt4 = "\n".join(out4)
    ck("  ★ 沒有「沒跑到」那一段", "沒跑到】" not in txt4, txt4[-200:])
    ck("  ★ 而且明說預算夠用", "所有案例都在內層預算內跑完" in txt4, txt4[-200:])

    print("")
    print("⑤ ⭐ 例外要往外丟，⛔ 但耗時仍然要記（否則失敗的案例會從表上消失）")
    reset(60)
    out5 = []

    def boom():
        raise ValueError("測試用")

    try:
        M.step(out5, "案例己", boom)
        raised = False
    except ValueError:
        raised = True
    ck("  ⭐ 例外照樣往外丟（⛔ 不可以吞掉）", raised)
    ck("  ★ 而它仍然出現在耗時表上", [n for n, _d in M._TIMES] == ["案例己"],
       str(M._TIMES))

    print("")
    print("⑥ ★★ 內層預算一定要【小於】probe.yml 給的外層秒數")
    wf = io.open(os.path.join(HERE, ".github", "workflows", "probe.yml"),
                 encoding="utf-8").read()
    import re
    m = re.search(r"probe_step\.sh data/meta/_mops_probe\.txt (\d+) python mops_probe",
                  wf)
    ck("  ⭐ 找得到外層秒數", m is not None)
    if m:
        outer = int(m.group(1))
        inner = float(os.environ.get("MOPS_PROBE_BUDGET", "690"))
        ck("  ★★ 內層 %.0f < 外層 %d（⛔ 反過來的話內層等於沒有）" % (inner, outer),
           inner < outer, "內層 %.0f／外層 %d" % (inner, outer))
        mt = re.search(r"timeout-minutes: (\d+)\n\s+run: bash probe_step\.sh "
                       r"data/meta/_mops_probe\.txt", wf)
        ck("  ★ 而 step 的 timeout-minutes 要比外層秒數大",
           mt is not None and int(mt.group(1)) * 60 > outer,
           "timeout-minutes=%s／外層 %d" % (mt.group(1) if mt else "?", outer))

    print("")
    print("⑦ ★ 沒有動到 repo 真的輸出檔")
    # ⛔ 這一格原本寫成 `not os.path.exists(...) or True` ⇒ 永遠成立
    #   ⇒ 那是本庫最忌諱的形狀：一條永遠綠的斷言跟一條有效的長得一樣
    #   ⇒ 改成開頭讀一次 bytes、這裡再讀一次比對（比照 selftest_mops.py 第 8 節）
    after = io.open(M.OUT, "rb").read() if os.path.isfile(M.OUT) else None
    ck("  ★ data/meta/_mops_probe.txt 逐位元沒變（含「本來不存在就仍然不存在」）",
       after == BEFORE,
       "前 %s／後 %s" % (len(BEFORE) if BEFORE else None,
                        len(after) if after else None))

    print("\n[selftest] 通過 %d｜失敗 %d" % (OK, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
