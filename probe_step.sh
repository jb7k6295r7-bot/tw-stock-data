#!/usr/bin/env bash
# probe_step.sh — 跑一支探針，而且**壞掉的時候要留得下痕跡**。
#
#   用法：bash probe_step.sh <輸出檔> <秒數預算> <指令…>
#   例：  bash probe_step.sh data/meta/_mops_probe.txt 420 python mops_probe.py
#
# ══════════════════════════════════════════════════════════════════
# ⛔ 這一段本來在 `probe.yml` 裡**抄三份**（迴圈那支、mops、suspend）。
#   四點五：同一件事只准有一份實作——而這三份已經開始走岔
#   （suspend 那份根本沒有還原那一行）。
#
# ⭐ 它做兩件事，而兩件都是 2026-09-16 probe run 131 付過代價的：
#
# ① ⛔⛔ **還原要從 `origin/main` 取，不是 `git checkout -- <檔>`**
#
#    run 131 在**分支**上跑，`keys_probe.py` 炸掉（NameError）
#    ⇒ 舊寫法 `git checkout -- "$F"` 還原的是**分支**那一份，
#    ⚠ 而分支的 `data/` 永遠比 main 舊（所有資料都是 workflow 推到 main 的，四點六）
#    ⇒ 那一趟把 main 上的 `_keys_probe.txt` **砍掉 533 行**，
#    ⛔ 而附加的那句「這一份是上一次成功的內容」**讓它看起來完全正常**。
#    ⇒ ⭐ 還原一律先試 `origin/main`；main 上沒有那個檔才退回本地 HEAD。
#
# ② ⛔⛔ **時間預算要在裡面，不是只靠 `timeout-minutes`**
#
#    run 131 的 `mops_probe` 撞到 step 的 `timeout-minutes: 8`
#    ⇒ **整個 shell 被砍** ⇒ 底下那段寫 ✗ 的程式**一行都沒跑**
#    ⇒ 輸出檔停在上一趟，⚠ 而 `continue-on-error: true` 讓那一步顯示 **success**
#    ⇒ ⛔ 「它被砍了」與「它跑完而且沒有新發現」在畫面上一模一樣。
#    ⇒ ⭐ 用 `timeout` 在**裡面**砍（rc=124），shell 活著 ⇒ 寫得下 ✗。
#    ⚠ 所以 workflow 的 `timeout-minutes` 要**比這裡的秒數大**，
#      ⛔ 否則外層先砍，這一層等於沒有。
#
# ⚠ 一律 `exit 0`：可見性由**資料**承擔（輸出檔裡那行 ✗ 會進 commit），
#   ⛔ 不是由 log——log 會捲掉，而捲掉的東西不算守門（四點二⑤）。
# ══════════════════════════════════════════════════════════════════
set -u

F="${1:?用法：probe_step.sh <輸出檔> <秒數> <指令…>}"
BUDGET="${2:?缺秒數預算}"
shift 2
[ "$#" -ge 1 ] || { echo "⛔ probe_step.sh 缺指令"; exit 0; }

RC=0
timeout -k 10 "$BUDGET" "$@" || RC=$?
[ "$RC" -eq 0 ] && exit 0

if [ "$RC" -eq 124 ] || [ "$RC" -eq 137 ]; then
  WHY="**撞到 ${BUDGET} 秒的時間預算被砍掉**（⛔ 不是跑完，也不是沒發現）"
else
  WHY="非 0 結束（rc=$RC）——traceback 在 Actions log"
fi
echo "⛔ $* $WHY"

# ① 還原：先 origin/main，再退回本地 HEAD。⛔ 兩個都失敗就不要假裝還原過。
BACK="（⛔ 還原不了，這一份可能是這一趟寫到一半的殘骸）"
if git checkout origin/main -- "$F" 2>/dev/null; then
  BACK="（⭐ 已從 **origin/main** 還原成上一次成功的內容）"
elif git checkout HEAD -- "$F" 2>/dev/null; then
  BACK="（⚠ main 上沒有這個檔 ⇒ 從**本地 HEAD** 還原）"
fi

{
  echo ""
  echo "✗ $(date -u '+%Y-%m-%dT%H:%M:%SZ') $* $WHY"
  echo "  $BACK"
} >> "$F"
exit 0
