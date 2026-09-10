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
CHANGED=$(git diff --name-only "$BASE" "$DC" -- data)
DELETED=$(git diff --diff-filter=D --name-only "$BASE" "$DC" -- data)
echo "[push_data] 本趟改到 $(printf '%s\n' "$CHANGED" | grep -cv '^$') 個 data 檔"

for i in 1 2 3; do
  git fetch origin main || { sleep $((i * 5)); continue; }
  git checkout -q -B _push origin/main || break
  printf '%s\n' "$CHANGED" | grep -v '^$' | grep -vx "$LASTRUN" \
    | xargs -r git checkout "$DC" --
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
