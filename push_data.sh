#!/usr/bin/env bash
# push_data.sh — 把「本趟改到的 data 路徑」搬到 main 的頭上，然後推。
#
# 用法：  bash push_data.sh "<commit 訊息>"
# 回傳：  0 = 推上去了（或本來就沒有差異）；非 0 = 真的失敗
#
# ⛔⛔ 為什麼要有這個檔：這段邏輯本來在**八支 workflow 各抄一份**。
#   而「同一段邏輯抄兩份」今晚已經害過一次——`limit` 那個 bug 在
#   `fetch.py` 與 `backfill.py` 各有一份，修好的那份天天跑、
#   沒修的那份只有回補才跑，所以一直沒被發現。
#   ⇒ 這裡只留一份，八支都呼叫它。
#
# ⭐ 做法（2026-09-10，付了 5 小時學費換來的）：
#   ① 程式 commit **一個都不重放** ⇒ workflow／程式檔永遠不會衝突
#   ② `data/` 裡只碰**本趟真的改到的檔** ⇒ 別的 workflow 剛寫的資料原封不動
#   ③ 完全沒有 rebase ⇒ 沒有「衝突要挑哪一邊」的問題
#   離線 git 模擬三項都驗過（scratchpad/gitsim3）。
set -u
MSG="${1:?用法: push_data.sh \"<commit 訊息>\"}"

git config user.name  "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

# ★ 用 -A：`git add <路徑>` 在舊版 git 不會把「檔案被刪掉」記進暫存區，
#   而 purge 模式產出的**就是刪除**。
git add -A data
if git diff --staged --quiet; then
  echo "[push_data] 沒有變動，不 commit"
  exit 0
fi
git commit -q -m "$MSG"

DC=$(git rev-parse HEAD)
BASE=$(git rev-parse HEAD~1)
LASTRUN="data/meta/_last_run.md"

# ⛔⛔ 累積型 CSV：**逐鍵合併，不可以整檔取本趟的**（2026-09-10 加）。
#
#   實際發生過的遺失：
#     07:15  一天實測（2026-09-09）推上 main ⇒ `_coverage_backfill.csv` 多一列
#     07:20  2015 那批開跑。它的 checkout 是**分支**，而分支上的 `data/`
#            **沒有**那一列（那一列是推到 main 的，不是推到分支）
#     07:22  它把整個檔搬到 main ⇒ ⛔ **五分鐘前那一列被刪掉**
#   ⚠ 而 `git diff` 看起來完全正常：一加一減，像是「這一趟重算過」。
#
# ⭐ 這跟下面 `_last_run.md` 那段是同一件事，只是它先被想到——
#   同一個道理原本只做了一半。
#
# ⚠ 這裡是**具名清單**，⛔ 不是「所有 CSV 都合併」：
#   `_missing_rows.csv`／`_notrade_days.csv` 那些是**每趟全量重算**的，
#   合併它們會把已經修好的舊列**復活**。
#   ⇒ 只有「這一趟只 append 自己那幾列」的檔才進這張清單。
LEDGERS="
data/universe/_coverage_backfill.csv:date
data/meta/calendar_tpex.csv:date
data/meta/holiday_schedule.csv:date
"
CHANGED=$(git diff --name-only "$BASE" "$DC" -- data)
DELETED=$(git diff --diff-filter=D --name-only "$BASE" "$DC" -- data)
echo "[push_data] 本趟改到 $(printf '%s\n' "$CHANGED" | grep -cv '^$') 個 data 檔"

for i in 1 2 3; do
  git fetch origin main || { sleep $((i * 5)); continue; }
  git checkout -q -B _push origin/main || break
  # 累積型的先排除，下面單獨逐鍵合併
  LEDGER_PATHS=$(printf '%s\n' "$LEDGERS" | grep -v '^$' | cut -d: -f1)
  KEEP=$(printf '%s\n' "$CHANGED" | grep -v '^$' | grep -vx "$LASTRUN")
  for lp in $LEDGER_PATHS; do
    KEEP=$(printf '%s\n' "$KEEP" | grep -vx "$lp" || true)
  done
  printf '%s\n' "$KEEP" | grep -v '^$' | xargs -r git checkout "$DC" --
  printf '%s\n' "$DELETED" | grep -v '^$' \
    | xargs -r git rm -q -f --ignore-unmatch
  # ⚠ `_last_run.md` 是**跨 workflow 累積**的（runlog 只覆蓋自己那一區塊）
  #   ⇒ ⛔ 不可以整份取本趟的，否則另一支剛報的 ✗ 會被安靜換回上一輪的 ✓。
  if printf '%s\n' "$CHANGED" | grep -qx "$LASTRUN"; then
    git show "$DC:$LASTRUN" > /tmp/lr_mine.md
    git show "origin/main:$LASTRUN" > /tmp/lr_main.md 2>/dev/null || : > /tmp/lr_main.md
    if python3 merge_last_run.py /tmp/lr_mine.md /tmp/lr_main.md > "$LASTRUN"; then
      git add -- "$LASTRUN"
    else
      echo "[push_data] ⛔ _last_run.md 逐區塊合併失敗，取本趟的（⚠ 另一支的區塊可能被回退）" >&2
      git checkout "$DC" -- "$LASTRUN" && git add -- "$LASTRUN"
    fi
  fi
  # ⭐ 累積型 CSV：逐鍵合併（本趟的鍵覆蓋、main 的其餘列原封不動保留）
  for ent in $(printf '%s\n' "$LEDGERS" | grep -v '^$'); do
    LP=${ent%%:*}; LK=${ent#*:}
    printf '%s\n' "$CHANGED" | grep -qx "$LP" || continue
    git show "$DC:$LP" > /tmp/lg_mine.csv 2>/dev/null || continue
    git show "origin/main:$LP" > /tmp/lg_main.csv 2>/dev/null || : > /tmp/lg_main.csv
    if python3 merge_ledger.py /tmp/lg_mine.csv /tmp/lg_main.csv "$LK" > /tmp/lg_out.csv; then
      cp /tmp/lg_out.csv "$LP"
      git add -- "$LP"
    else
      # ⛔ 合併不成就**整檔取本趟的**，⚠ 但一定要吼出來：
      #   那正是會靜靜刪掉別人剛寫的列的那條路。
      echo "[push_data] ⛔ $LP 逐鍵合併失敗，退回整檔取本趟的（⚠ main 上較新的列可能被回退）" >&2
      git checkout "$DC" -- "$LP" && git add -- "$LP"
    fi
  done
  git add -A data
  if git diff --staged --quiet; then
    echo "[push_data] 搬到 main 之後沒有差異（多半是別的 workflow 已推過同樣內容）"
    git checkout -q "${GITHUB_REF_NAME:-main}" 2>/dev/null || true
    exit 0
  fi
  git commit -q -m "$MSG"
  if git push origin HEAD:main; then
    echo "[push_data] ✓ 已推上 main"
    # ⛔ 一定要切回原本的分支：呼叫端後面可能還要繼續跑。
    git checkout -q "${GITHUB_REF_NAME:-main}" 2>/dev/null || true
    exit 0
  fi
  echo "[push_data] push 失敗（第 $i 次），多半是這幾秒又有人推了 main，重來" >&2
  sleep $((i * 5))
done
echo "[push_data] ⛔ 連續三次 push 失敗" >&2
exit 1
