#!/usr/bin/env bash
# 美股 C3s 每月月底換股單（無人值守版）：上月最後一個美股交易日 M 收盤 ⇒ 下一交易日開盤的換股單＋C3sF 濾網＋C11 紀錄＋停用條件級別
#
# 誰可以叫：
#   - 由 run_daily_list.sh 在每日名單跑完後呼叫（Windows 排程「回測線_每日名單」每天 20:00、00:45、03:00）；本腳本失敗不影響每日名單
#   - 情報線可以用 `schtasks /run /tn "回測線_每日名單"` 叫（重複跑安全）；⛔ 不可以改本檔與 backtest/c3s_month/ 下的檔
#   - 手動：bash ~/tw-p17/backtest/run_c3s_month.sh [--month YYYY-MM-DD]
#
# 規則：
#   1 快速判斷：沒給 --month 時，M ＝ 上一個日曆月最後一個 NYSE 交易日（c3s_month/c3sm_cal.py 規則日曆）；
#     只在「M 的換股單還沒出、而且今天（台北）在 M 之後 1～5 個日曆日內」才進正式流程；其他日子幾秒內退出 0（不 fetch、不建快照）
#   2 鎖 ~/us_work/c3s_month/.lock（flock）；已有一個在跑 ⇒ 記 log 後退出 0。log 追加到 backtest/forward/us_c3s_month.log（台北時間）
#   3 重複跑安全：M 已出單（~/us_work/c3s_month/<M>/delivered.json，含驗算通過紀錄）⇒ 略過；repo 已有 order_<M>.csv（手動補記等）⇒ 也略過、不覆蓋
#     同一資料 commit 已驗算不過 ⇒ 略過（退出 1），等新資料或人工
#   4 資料到了沒：git -C ~/us-stock-data fetch（⛔ 不 pull、不改工作樹）後用 origin/main 最新 commit；c3s_month/data_ready.py：
#     M 那天 SPY、^GSPC 有列，且 S&P 500 現役成分有 M 那一列的檔數 ≥ 前一交易日的 98%；^GSPC 已有下月資料時以資料日曆覆核月底
#     未到 ⇒ 不出單；過了預期時間（M 的次日 13:00 台北）才寫「未到」信（同一原因只寫一次），之前只記 log
#   5 產出（M 之後的列全部截掉）：rebuild_usdata.sh 抽唯讀快照 ⇒ c3s_month/cut_root.py 截到 M ⇒ build_world.py 建本期世界 ⇒
#     produce.py（程式 f56133f55a：researchUSC3s_ops --month M、新版 e71b5bc77e 全名欄、forward_us_c3sf --month M、forward_us_c11 --month M、
#     researchUSC3s_stop --month M ＋主臂續抱簿級別）⇒ inject.py ones／rand ⇒ finalize.py（驗算判定、加註、sha）
#   6 驗算不過或程式錯誤 ⇒ 不出單，寫「未出」信；通過 ⇒ deliver()：md ＋ _交付-C3s換股單_<M>/order_<YYYYMMDD>.csv（新版、含全名欄）放信箱
#   7 repo（只正式模式）：產出檔複製到 ~/tw-p17 對應路徑，git add 指定檔、commit（只含那幾個檔）、push 到 claude/stock-analysis-backtest-iv9xji
#     共用世界檔 ~/us_work/a4/world.npz 換成本期版，舊檔備份成 world_<舊檔月底>.npz
#   8 退出碼：成功、略過、資料未到 0；失敗 1
#   ⛔ 不改任何選股、規則程式（c3s_month/*.py 只在行程內改讀寫位置與記錄時間）
#
# 測試用環境變數（C3S_OUT 有設 ⇒ 測試模式：信箱、log、工作夾、repo 複製全改到 C3S_OUT 底下；⛔ 不 commit、不 push、不換共用世界檔）：
#   C3S_OUT=<暫存資料夾>     C3S_FAKE_TODAY=YYYY-MM-DD[ HH:MM]（只能和 C3S_OUT 一起用；只給日期 ⇒ 當 20:00）
#   C3S_DATA_COMMIT=<commit>（不 fetch、改用這個 commit；回歸測試用）   C3S_FIXED_NOW="YYYY-MM-DD HH:MM"（記錄時間欄固定；只在測試模式有效）
#   C3S_PROCS=建世界的行程數（預設 2）
set -uo pipefail
REPO=$HOME/tw-p17
F561=$HOME/c3s_f561
H=$REPO/backtest/c3s_month
PY=$HOME/tw-p16/.venv/bin/python
USREPO=$HOME/us-stock-data
BRANCH=claude/stock-analysis-backtest-iv9xji
A4W=$HOME/us_work/a4/world.npz
export PYTHONDONTWRITEBYTECODE=1          # 不在 repo 的 c3s_month/ 留 __pycache__
M=""; MONTH=""
while [ $# -gt 0 ]; do
  case "$1" in
    --month) MONTH="${2:-}"; shift 2;;
    --month=*) MONTH="${1#*=}"; shift;;
    *) echo "未知參數：$1（用法：run_c3s_month.sh [--month YYYY-MM-DD]）"; exit 1;;
  esac
done
if [ -n "${C3S_OUT:-}" ]; then
  TEST=1; MB="$C3S_OUT/mailbox"; LOG="$C3S_OUT/us_c3s_month.log"; WROOT="$C3S_OUT/work"; RDST="$C3S_OUT/repo"
else
  TEST=0; MB="/mnt/c/SynologyDrive/跨線信箱"; LOG="$REPO/backtest/forward/us_c3s_month.log"; WROOT="$HOME/us_work/c3s_month"; RDST="$REPO"
fi
tpe() { TZ=Asia/Taipei date "$@"; }
logline() { echo "[$(tpe '+%Y-%m-%d %H:%M:%S') 台北]$([ $TEST = 1 ] && echo ' [測試]')${M:+ M=$M} $*" >> "$LOG"; echo "$*"; }
mkdir -p "$WROOT" "$(dirname "$LOG")" || exit 1
if [ -n "${C3S_FAKE_TODAY:-}" ] && [ $TEST = 0 ]; then logline "失敗：C3S_FAKE_TODAY 只能和 C3S_OUT 一起用"; exit 1; fi
if [ -n "${C3S_FAKE_TODAY:-}" ]; then
  case "$C3S_FAKE_TODAY" in *" "*) NOWX="$C3S_FAKE_TODAY";; *) NOWX="$C3S_FAKE_TODAY 20:00";; esac
else
  NOWX=$(tpe '+%Y-%m-%d %H:%M')
fi
TODAY=${NOWX:0:10}
if [ -n "${C3S_FIXED_NOW:-}" ] && [ $TEST = 1 ]; then RUN_TS="$C3S_FIXED_NOW"; else RUN_TS=$(tpe '+%Y-%m-%d %H:%M'); fi

exec 9>"$WROOT/.lock"
if ! flock -n 9; then logline "略過：已有一個在跑（鎖 $WROOT/.lock）"; exit 0; fi

# ── 1 決定月底 M ＋ 快速判斷 ──
if [ -n "$MONTH" ]; then
  [[ "$MONTH" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || { logline "失敗：--month 格式要 YYYY-MM-DD（$MONTH）"; exit 1; }
  M=$MONTH; GATE="手動 --month"
else
  M=$("$PY" "$H/c3sm_cal.py" prevme "$TODAY") || { logline "失敗：c3sm_cal.py"; exit 1; }
  DAYS=$(( ( $(date -ud "$TODAY" +%s) - $(date -ud "$M" +%s) ) / 86400 ))
  if [ "$DAYS" -lt 1 ] || [ "$DAYS" -gt 5 ]; then
    logline "不在換股窗：今天 $TODAY、上月底 $M（差 $DAYS 天，窗 1～5 天）⇒ 退出"; exit 0
  fi
  GATE="換股窗第 $DAYS 天"
fi

setm() { M="$1"; MD=${M//-/}; WD="$WROOT/$M"; ORD="$RDST/backtest/resultsUSC/C3s/ops/order_$MD.csv"; mkdir -p "$WD"; }
setm "$M"

# 未出信（同一原因只寫一次）：notice <原因短語> <內文>
notice() {
  local why="$1" body="$2" key ts f
  key="$WD/notice_$why.sent"
  if [ -f "$key" ]; then logline "（未出信「$why」已寫過：$(cat "$key")，不再寫）"; return 0; fi
  ts=$(tpe '+%Y%m%d-%H%M')
  mkdir -p "$MB" || return 1
  f="$MB/件-美股情報←回測線-$ts-C3s換股單_${M}_未出_$why.md"
  {
    echo "尚未驗證（看過段、集中度高），試單金額自行控制"; echo
    echo "# 件｜美股情報 ← 回測線：C3s 換股單 $M 月底【未出】——$why"; echo
    echo "**寄件**：回測線（run_c3s_month.sh 自動）　**台北時戳**：$(tpe '+%Y-%m-%d %H:%M')"; echo
    echo "- 這期換股單**還沒出**，請先不要照上月的單動作。"
    echo "- 原因：$why"; echo
    echo '```'; echo "$body"; echo '```'; echo
    echo "- 程式會在每日名單排程（20:00、00:45、03:00）重試到 M 之後第 5 天；出單後另寄一封。"
    echo "- 工作夾：$WD"; echo; echo "— 回測線"
  } > "$f.tmp" && mv "$f.tmp" "$f" && echo "$f" > "$key"
  logline "寫未出信：$f"
}

# 出單（測試模式 MB 在 C3S_OUT 底下）
deliver() {
  local ts="$1" f d
  mkdir -p "$MB" || return 1
  d="$MB/_交付-C3s換股單_$M"; mkdir -p "$d" || return 1
  cp "$WD/stage/final/order_$MD.csv" "$d/order_$MD.csv.tmp" && mv "$d/order_$MD.csv.tmp" "$d/order_$MD.csv" || return 1
  f="$MB/件-美股情報←回測線-$ts-C3s換股單_$M.md"
  cp "$WD/stage/final/mail.md" "$f.tmp" && mv "$f.tmp" "$f" || return 1
  DELIVERED="$f"
}

# repo：複製產出檔；正式模式才 commit／push
repo_step() {
  local files=() x
  mapfile -t files < "$WD/stage/final/repo_files.txt"
  for x in "${files[@]}"; do
    [ -n "$x" ] || continue
    mkdir -p "$(dirname "$RDST/$x")" && cp "$WD/stage/final/repo/$x" "$RDST/$x" || { logline "失敗：複製 $x"; return 1; }
  done
  if [ $TEST = 1 ]; then logline "測試模式：產出檔複製到 $RDST（${#files[@]} 檔），不 commit、不 push"; touch "$WD/repo_done"; return 0; fi
  local cur; cur=$(git -C "$REPO" branch --show-current)
  if [ "$cur" != "$BRANCH" ]; then logline "失敗：~/tw-p17 目前分支 $cur ≠ $BRANCH，不 commit（檔已複製）"; return 1; fi
  ( cd "$REPO" && git add -- "${files[@]}" ) > "$WD/git.log" 2>&1 || { logline "失敗：git add（見 $WD/git.log）"; return 1; }
  if git -C "$REPO" diff --cached --quiet -- "${files[@]}"; then
    logline "repo：這幾個檔與 HEAD 相同（已 commit 過），不再 commit"
  else
    ( cd "$REPO" && git commit -q -F "$WD/stage/final/commit_msg.txt" -- "${files[@]}" ) >> "$WD/git.log" 2>&1 \
      || { logline "失敗：git commit（見 $WD/git.log）"; return 1; }
    logline "commit $(git -C "$REPO" rev-parse --short=10 HEAD)：${#files[@]} 檔"
  fi
  if ! git -C "$REPO" push -q origin "HEAD:refs/heads/$BRANCH" >> "$WD/git.log" 2>&1; then
    logline "失敗：git push（commit 已在本機；見 $WD/git.log；下次執行會重推）"; touch "$WD/commit_done"; return 1
  fi
  touch "$WD/repo_done"; logline "push 完成：$BRANCH"
}

# 共用世界檔換成本期版（只正式模式）；舊檔備份 world_<舊檔月底>.npz
world_install() {
  [ $TEST = 1 ] && return 0
  local new="$WD/world/world.npz" oldlast newlast
  [ -f "$new" ] || { logline "（共用世界檔：本期世界檔已不在，略過）"; touch "$WD/world_done"; return 0; }
  newlast=$("$PY" -c "import numpy as np,pandas as pd,sys;print(pd.Timestamp(np.load(sys.argv[1])['cal'][-1]).strftime('%Y%m%d'))" "$new") || return 1
  if [ -f "$A4W" ]; then
    oldlast=$("$PY" -c "import numpy as np,pandas as pd,sys;print(pd.Timestamp(np.load(sys.argv[1])['cal'][-1]).strftime('%Y%m%d'))" "$A4W") || return 1
    if [[ ! "$oldlast" < "$newlast" ]]; then logline "共用世界檔已是 $oldlast（不比本期 $newlast 舊），不換"; touch "$WD/world_done"; return 0; fi
    [ -f "$HOME/us_work/a4/world_$oldlast.npz" ] || cp -p "$A4W" "$HOME/us_work/a4/world_$oldlast.npz" || return 1
  fi
  cp "$new" "$A4W.tmp" && mv "$A4W.tmp" "$A4W" || return 1
  touch "$WD/world_done"; logline "共用世界檔換成 $newlast 版（舊檔備份 world_${oldlast:-無}.npz）"
}

# ── 3 重複跑安全 ──
check_done() {
  if [ -f "$WD/delivered.json" ]; then
    local rc=0
    if [ $TEST = 0 ] && [ ! -f "$WD/repo_done" ]; then
      if [ -f "$WD/commit_done" ]; then
        git -C "$REPO" push -q origin "HEAD:refs/heads/$BRANCH" >> "$WD/git.log" 2>&1 && touch "$WD/repo_done" && logline "重推完成" || { logline "失敗：重推"; rc=1; }
      else
        repo_step || rc=1
      fi
    fi
    [ $TEST = 0 ] && [ ! -f "$WD/world_done" ] && { world_install || { logline "失敗：換共用世界檔"; rc=1; }; }
    logline "略過：$M 已出單（$(head -c 300 "$WD/delivered.json" | tr '\n' ' ')）"; exit $rc
  fi
  if [ -f "$ORD" ]; then logline "略過：$ORD 已存在（非本腳本產出或手動補記），不覆蓋"; exit 0; fi
}
check_done
logline "開始（$GATE；今天 $NOWX）"

# ── 4 資料到了沒 ──
if [ -n "${C3S_DATA_COMMIT:-}" ]; then
  C=$(git -C "$USREPO" rev-parse --verify "${C3S_DATA_COMMIT}^{commit}" 2>/dev/null) || { logline "失敗：C3S_DATA_COMMIT 找不到"; exit 1; }
  logline "資料 commit 由 C3S_DATA_COMMIT 指定：${C:0:10}（不 fetch）"
else
  if ! git -C "$USREPO" fetch -q origin 2> "$WD/fetch.err"; then
    logline "失敗：git fetch：$(tail -1 "$WD/fetch.err")"; notice 程式錯誤 "git -C ~/us-stock-data fetch 失敗：$(tail -3 "$WD/fetch.err")"; exit 1
  fi
  C=$(git -C "$USREPO" rev-parse origin/main)
fi
C9=${C:0:9}
if [ -f "$WD/verify_fail_$C9" ]; then logline "略過：資料 $C9 已驗算不過（$WD/verify_fail_$C9），等新資料或人工"; exit 1; fi
mapfile -t DR < <("$PY" "$H/data_ready.py" "$USREPO" "$C" "$M" "$WD/data_ready.json" 2> "$WD/data_ready.err")
if [ "${#DR[@]}" -lt 3 ]; then logline "失敗：data_ready.py（$(tail -1 "$WD/data_ready.err")）"; notice 程式錯誤 "data_ready.py：$(tail -5 "$WD/data_ready.err")"; exit 1; fi
if [ "${DR[1]}" != "$M" ]; then
  logline "⚠ 資料日曆（^GSPC）說上月最後交易日是 ${DR[1]}（規則日曆 $M）⇒ 改用 ${DR[1]}"
  setm "${DR[1]}"; check_done
  mapfile -t DR < <("$PY" "$H/data_ready.py" "$USREPO" "$C" "$M" "$WD/data_ready.json")
fi
if [ "${DR[0]}" != 1 ]; then
  EXPECT="$(date -ud "$M +1 day" +%F) 13:00"
  if [[ "$NOWX" < "$EXPECT" ]]; then logline "資料未到（還沒到預期時間 $EXPECT 台北）：${DR[2]}｜資料 $C9"; exit 0; fi
  logline "資料未到：${DR[2]}｜資料 $C9"
  notice 資料未到 "us-stock-data origin/main ${C:0:10}：${DR[2]}"
  exit 0
fi
logline "資料齊：${DR[2]}｜資料 $C9"

T0=$(date +%s)
fail() { logline "失敗：$1（見 $2）"; notice 程式錯誤 "$1：$(tail -15 "$2" 2>/dev/null)"; exit 1; }

# ── 5 快照、截到 M、世界 ──
SNAP=$HOME/usdata/$C9; MADE_SNAP=0
[ -e "$SNAP" ] || MADE_SNAP=1
bash "$REPO/backtest/rebuild_usdata.sh" "$C9" > "$WD/snap.log" 2>&1 || fail "rebuild_usdata.sh $C9" "$WD/snap.log"
if [ $TEST = 1 ]; then CUT="$WD/root"; else CUT="$HOME/usdata/${C9}_to$MD"; fi
if [ -d "$CUT" ] && [ "$(cat "$CUT/.commit" 2>/dev/null)" = "$C" ] && grep -q "<= $M" "$CUT/CUT.txt" 2>/dev/null; then
  logline "截到 $M 的快照已存在：$CUT"
else
  [ -e "$CUT" ] && { chmod -R u+w "$CUT" && rm -rf "$CUT"; }
  "$PY" "$H/cut_root.py" "$SNAP" "$CUT" "$M" > "$WD/cut.log" 2>&1 || fail "cut_root.py" "$WD/cut.log"
fi
if [ $MADE_SNAP = 1 ]; then chmod -R u+w "$SNAP" && rm -rf "$SNAP" && logline "清掉本次抽的完整快照 $SNAP（截後快照留著）"; fi
WORLDD="$WD/world"
if [ -f "$WORLDD/world.npz" ] && [ -f "$WORLDD/meta.json" ] && grep -q "\"資料commit\": \"$C\"" "$WORLDD/meta.json" && grep -q "\"資料根\": \"$CUT\"" "$WORLDD/meta.json"; then
  logline "本期世界檔已存在：$WORLDD/world.npz"
else
  rm -rf "$WORLDD"
  ( cd "$F561" && US_DATA_ROOT_A2="$CUT" "$PY" "$H/build_world.py" --root "$CUT" --out "$WORLDD" --month "$M" --procs "${C3S_PROCS:-2}" ) > "$WD/world.log" 2>&1 \
    || fail "build_world.py" "$WD/world.log"
fi

# ── 5 產出、驗算 ──
ST="$WD/stage"; rm -rf "$ST"; mkdir -p "$ST"
export US_DATA_ROOT_A2="$CUT" C3S_RUN_TS="$RUN_TS"
( cd "$F561" && "$PY" "$H/produce.py" --month "$M" --root "$CUT" --world "$WORLDD" --stage "$ST" ) > "$WD/produce.log" 2>&1 || fail "produce.py" "$WD/produce.log"
logline "$(tail -1 "$WD/produce.log")"
for K in ones rand; do
  ( cd "$F561" && "$PY" "$H/inject.py" --kind $K --month "$M" --root "$CUT" --world "$WORLDD" --stage "$ST" --out "$ST/inj_$K" ) > "$WD/inject_$K.log" 2>&1 \
    || fail "inject.py $K" "$WD/inject_$K.log"
  logline "$(tail -1 "$WD/inject_$K.log")"
done
TS=$(tpe '+%Y%m%d-%H%M')
"$PY" "$H/finalize.py" --stage "$ST" --ts "$TS" > "$WD/finalize.log" 2>&1; FRC=$?
if [ $FRC = 3 ]; then
  touch "$WD/verify_fail_$C9"
  logline "驗算不過 ⇒ 不出單：$(tail -1 "$WD/finalize.log")"
  notice 驗算失敗 "$(cat "$ST/final/fail.md")
資料 us-stock-data ${C:0:10}；詳見 $ST/final/verify.json"
  exit 1
elif [ $FRC != 0 ]; then
  fail "finalize.py" "$WD/finalize.log"
fi
logline "$(tail -1 "$WD/finalize.log")"

# ── 6 送出 ──
DELIVERED=""
deliver "$TS" || { logline "失敗：放信箱（$MB）"; exit 1; }
"$PY" -c "import json,sys;v=json.load(open(sys.argv[1],encoding='utf-8'));m=json.load(open(sys.argv[2],encoding='utf-8'));json.dump({'月底':v['月底'],'通過':v['通過'],'資料commit':v['資料commit'],'信':sys.argv[3],'sha':m},open(sys.argv[4],'w',encoding='utf-8'),ensure_ascii=False,indent=1)" \
  "$ST/final/verify.json" "$ST/final/manifest.json" "$DELIVERED" "$WD/delivered.json"
logline "出單：$DELIVERED｜$(( $(date +%s) - T0 )) 秒"

# ── 7 repo、共用世界檔 ──
RC=0
repo_step || RC=1
world_install || { logline "失敗：換共用世界檔"; RC=1; }
exit $RC
