#!/usr/bin/env bash
# 每日名單（無人值守版）：抓最新 main ⇒ 唯讀 archive ⇒ 跑 backtest.daily_list ⇒ 把 daily_<資料日>.md 放到信箱 _營量觀察/
# 用法：bash ~/tw-p17/backtest/run_daily_list.sh [--final] [--force]
#   Windows 排程每天 20:00、00:45、06:30 各跑一次；06:30 那次帶 --final
# 規則（協調者 09-28 轉使用者同意的排程要求）：
#   1 重複跑安全：_營量觀察/daily_<資料日>.md 已存在且檔頭的 main sha 相同 ⇒ 略過；main 有新 sha、資料日不變 ⇒ 照新資料重產、覆蓋同一檔
#   2 鎖檔 backtest/resultsYLwatch/.daily.lock（flock）：已有一個在跑 ⇒ 記 log 後退出（0）
#   3 每次追加一段到 backtest/resultsYLwatch/daily_run.log：時間（台北）、sha、資料日、結果（產檔／略過／失敗＋原因）
#   4 --final：「預期資料日」＝ 從今天（台北）【往前】找（不含今天：06:30 還沒收盤）最近一個週一～五、不在休市表的日子
#      （休市表 ＝ main 的 data/meta/holiday_schedule.csv，讀法同 gate_b_status.future_trading_days：名稱含「開始交易／最後交易」者是交易日；
#       另：附註寫「市場無交易」者當休市）
#      該日 daily 檔不在 ⇒ 寫 _營量觀察/daily_<預期資料日>_未到.md（資料庫未更新：main 最新資料日＝…／程式錯誤：最後 20 行）；休市 ⇒ 只記 log
#      測試用：環境變數 DAILY_FAKE_TODAY＝YYYY-MM-DD 可假造「今天」；DAILY_MB 可把輸出資料夾指到暫存處
#   5 退出碼：產檔或略過 0、失敗 1
#   6 ⛔ 信箱只寫 _營量觀察/ 這一個資料夾
#   8 GATE_V2（裁定 seq296 §一）：daily_list 每次開／關各算一次；不一致 ⇒ 差異檔 gatev2_diff_<資料日>.md 複製到 _營量觀察/、一致 ⇒ 刪同資料日舊差異檔
#   7 same_state（情報 1219；持股歷史同狀態，backtest.same_state 查表）：daily 產檔或略過之後才跑；⛔ 失敗只記 log、不改退出碼、不影響 daily；
#      同一資料日、同一 sha（resultsYLwatch/.same_state_<資料日>.sha）且 _營量觀察/same_state_<資料日>.md 在 ⇒ 略過；--force 一起重產；
#      --final 不寫 same_state 的 _未到（情報：缺檔就不印那行）；測試用：SAME_STATE_FAKE_FAIL=1 讓 same_state 故意失敗
#   9 大盤大跌前瞻（PREREG大盤大跌後買什麼 seq1，2026-10-17 加）：daily_list 產檔成功之後、複製到 _營量觀察/ 之前跑 backtest.mktdrop_fwd daily
#      （＝ researchMktDrop_v1 --judge <資料日> --write ＋ 收復檢查 ＋ 名單檔尾加「## 八、（內部）大盤大跌前瞻」）；⛔ 失敗只記 log、不改退出碼、名單照常複製；
#      紀錄 backtest/forward/mktdrop/、輸出 backtest/resultsDaily/mktdrop.log；daily 略過（sha 相同）⇒ 本步也不跑
#  11 VIX 狀態（2026-10-20 加）：backtest.vix_daily 在名單尾加「## 九、VIX 狀態」（私有庫 fred_VIXCLS；首次 ≥40 ⇒ ⭐【LINE】行）；失敗只記 log
#  10 策略鎖（2026-10-18 加）：每次產檔都跑 backtest.strategy_lock --check；不符 ⇒ 名單標題下加 ⚠⚠ 一行、記 log；⛔ 不擋產出
#   磁碟：archive 依【資料內容】（相關 data 子樹的 git tree id）存 ~/h2data/daily_<key>，~/h2data/<sha> 只放 symlink ⇒ 只改了別的 feed 的新 commit 不會再多一份 800MB
set -uo pipefail
REPO=$HOME/tw-p17
MB="${DAILY_MB:-/mnt/c/SynologyDrive/跨線信箱/_營量觀察}"                     # DAILY_MB 只給測試用（指到暫存資料夾）
WD="$REPO/backtest/resultsYLwatch"
LOG="$WD/daily_run.log"
LOCK="$WD/.daily.lock"
PY="$HOME/tw-p16/.venv/bin/python"
FINAL=0; FORCE=0
for x in "$@"; do case "$x" in --final) FINAL=1;; --force) FORCE=1;; esac; done     # --force：資料日與 sha 都相同也重產（手動改措辭用；排程不帶）
mkdir -p "$WD" "$REPO/backtest/resultsDaily"
NOW=$(TZ=Asia/Taipei date '+%Y-%m-%d %H:%M:%S')
logline() { echo "[$NOW 台北]$([ $FINAL = 1 ] && echo ' --final')$([ $FORCE = 1 ] && echo ' --force') $*" >> "$LOG"; echo "$*"; }

exec 9>"$LOCK"
if ! flock -n 9; then logline "略過：已有一個在跑（鎖 $LOCK）"; exit 0; fi

if ! git -C "$REPO" fetch -q origin main 2>/tmp/daily_fetch.err; then
  logline "失敗：git fetch：$(tail -1 /tmp/daily_fetch.err)"; FAIL="git fetch 失敗：$(tail -3 /tmp/daily_fetch.err)"; SHA=""; ASOF=""
else
  SHA=$(git -C "$REPO" rev-parse origin/main)
  KEY=$(for p in data/adj data/meta data/mops/revenue_hist data/stocks data/stocks_per; do git -C "$REPO" rev-parse "$SHA:$p"; done | sha1sum | cut -c1-16)
  DK="$HOME/h2data/daily_$KEY"
  [ -d "$HOME/h2data/$SHA/data/stocks" ] && [ ! -L "$HOME/h2data/$SHA" ] && DK="$HOME/h2data/$SHA"      # 這個 sha 以前已整份 archive 過 ⇒ 直接用
  if [ ! -d "$DK/data/stocks" ]; then
    mkdir -p "$DK"
    git -C "$REPO" archive "$SHA" data/adj data/meta data/mops/revenue_hist data/stocks data/stocks_per | tar -x -C "$DK" && chmod -R a-w "$DK"
  fi
  [ -e "$HOME/h2data/$SHA" ] || ln -s "$DK" "$HOME/h2data/$SHA"
  ASOF=$(tail -1 "$DK/data/meta/calendar_twse.csv" | cut -d, -f1)
  FAIL=""
fi

RESULT=""
if [ -z "$FAIL" ]; then
  OUTF="$MB/daily_$ASOF.md"
  if [ $FORCE = 0 ] && [ -f "$OUTF" ] && grep -q "main ${SHA:0:10}" "$OUTF"; then
    RESULT="略過"; logline "略過：sha ${SHA:0:10}｜資料日 $ASOF｜$OUTF 已存在且 sha 相同"
  else
    WLOG="$REPO/backtest/resultsDaily/wrapper.log"
    if (cd "$REPO" && PYTHONPATH=$REPO "$PY" -m backtest.daily_list > "$WLOG" 2>&1) && [ -f "$REPO/backtest/resultsDaily/daily_$ASOF.md" ]; then
      # 規則 9：大盤大跌前瞻（失敗只記 log；md 只在成功時才加第八節）
      MLOG="$REPO/backtest/resultsDaily/mktdrop.log"
      if (cd "$REPO" && PYTHONPATH=$REPO "$PY" -m backtest.mktdrop_fwd daily --asof "$ASOF" --sha "$SHA" --md "$REPO/backtest/resultsDaily/daily_$ASOF.md" > "$MLOG" 2>&1); then
        logline "大盤大跌前瞻：$(tail -1 "$MLOG")"
      else
        logline "大盤大跌前瞻 失敗（不影響 daily）：$(tail -1 "$MLOG" 2>/dev/null)（見 $MLOG）"
      fi
      # 規則 11：VIX 狀態（使用者 10/20「好」）：名單檔尾加「## 九、VIX 狀態」；⛔ 失敗只記 log、不影響名單
      VLOG="$REPO/backtest/resultsDaily/vix.log"
      if (cd "$REPO" && PYTHONPATH=$REPO "$PY" -m backtest.vix_daily --md "$REPO/backtest/resultsDaily/daily_$ASOF.md" > "$VLOG" 2>&1); then
        logline "VIX：$(grep -m1 '^- ' "$VLOG")"
      else
        logline "VIX 失敗（不影響 daily）：$(tail -1 "$VLOG" 2>/dev/null)"
      fi
      # 規則 12：52 週新高 10 檔（高10；前瞻 seq4、裁定 seq414～416、使用者 10/21「跟營飆一樣 LINE 給我」）：名單檔尾加「## 十、52 週新高 10 檔（高10）」；LINE 續抱／要賣照 positions_user；⛔ 失敗只記 log、不影響名單
      HLOG="$REPO/backtest/resultsDaily/pth10.log"
      if (cd "$REPO" && PYTHONPATH=$REPO "$PY" -m backtest.pth10_daily --asof "$ASOF" --sha "$SHA" --md "$REPO/backtest/resultsDaily/daily_$ASOF.md" > "$HLOG" 2>&1); then
        logline "高10：$(tail -1 "$HLOG")"
      else
        logline "高10 失敗（不影響 daily）：$(tail -1 "$HLOG" 2>/dev/null)（見 $HLOG）"
      fi
      # 規則 13：大跌加碼提醒（第十一節，使用者 10/21「大跌除了4檔以外通知我加碼高10及64中的0050」）：mktdrop_fwd 已在規則 9 產生第十一節 ⇒ 這裡只把它搬到檔尾（排在第十節之後；不重算、不寫紀錄、冪等）；⛔ 失敗只記 log
      if ! (cd "$REPO" && PYTHONPATH=$REPO "$PY" -m backtest.mktdrop_fwd sec11 --md "$REPO/backtest/resultsDaily/daily_$ASOF.md" >> "$MLOG" 2>&1); then
        logline "第十一節搬移失敗（不影響 daily）：見 $MLOG"
      fi
      # 規則 14：大漲觀察月報／季加報＋前瞻小部位 seq1（台股 seq538／539／544、情報 0030／0035、裁定 seq441／442）；每晚 auto（到期才產月報，每晚更新小部位前瞻、處理第十二節）；⛔ 失敗只記 log、不影響名單
      BLOG="$REPO/backtest/resultsDaily/bigrun.log"
      if (cd "$REPO" && PYTHONPATH=$REPO "$PY" -m backtest.bigrun_monthly --kind auto --asof "$ASOF" --sha "$SHA" --md "$REPO/backtest/resultsDaily/daily_$ASOF.md" > "$BLOG" 2>&1); then
        logline "大漲觀察：$(grep -E '^(產出|未到期|名單第十二節|小部位前瞻)' "$BLOG" | tr '\n' ' ')"
      else
        logline "大漲觀察 失敗（不影響 daily）：$(tail -1 "$BLOG" 2>/dev/null)（見 $BLOG）"
      fi
      # 規則 15：頂部樣子前瞻（PREREG 頂部樣子 seq1 e30036415fbbce81、裁定 seq443 §三 轉前瞻）：每晚呼叫；判定夜（月底下一交易日）判上月底、到期填 12／6 個月報酬；名單尾第十三節只在判定或填報酬那晚寫一行（內部、⛔ 不推 LINE）；⛔ 失敗只記 log、不影響名單
      TLOG="$REPO/backtest/resultsDaily/topsell.log"
      if (cd "$REPO" && PYTHONPATH=$REPO "$PY" -m backtest.topsell_fwd --asof "$ASOF" --sha "$SHA" --md "$REPO/backtest/resultsDaily/daily_$ASOF.md" > "$TLOG" 2>&1); then
        logline "頂部樣子前瞻：$(tail -1 "$TLOG")"
      else
        logline "頂部樣子前瞻 失敗（不影響 daily）：$(tail -1 "$TLOG" 2>/dev/null)（見 $TLOG）"
      fi
      # 規則 16：美股確認前小部位（ETN；美股 seq2 定版 f15b918fa43f360f、裁定 seq461 §四／seq462 §一）：每晚呼叫（冪等）；有事件行 ⇒ 名單尾「## 十五、美股小部位（通知）」＋【LINE】行；⛔ 失敗只記 log、不影響名單
      ULOG="$REPO/backtest/resultsDaily/us_smallpos.log"; UEV="$REPO/backtest/resultsDaily/us_smallpos_events.txt"
      if (cd "$REPO" && PYTHONPATH=$REPO "$PY" -m backtest.forward_us_smallpos --line-out "$UEV" > "$ULOG" 2>&1); then
        logline "美股小部位前瞻：$(tail -1 "$ULOG")"
        if [ -s "$UEV" ]; then
          { echo; echo "## 十五、美股小部位（通知）"; echo; echo "- 【LINE】⭐ 美股小部位："; sed 's/^/  /' "$UEV"; } >> "$REPO/backtest/resultsDaily/daily_$ASOF.md"
        fi
      else
        logline "美股小部位前瞻 失敗（不影響 daily）：$(tail -1 "$ULOG" 2>/dev/null)（見 $ULOG）"
      fi
      # 規則 17：美股 v4 小部位（BE、LRCX；美股登錄 seq3＋seq4、產業 v4.1 雜湊 f63147396ffc4ee9）：每晚呼叫（冪等）；APPROVED=None 時只乾跑；不產 LINE 行（情報照產業信推）；⛔ 失敗只記 log、不影響名單
      W4LOG="$REPO/backtest/resultsDaily/us_v4.log"
      if (cd "$REPO" && PYTHONPATH=$REPO "$PY" -m backtest.forward_us_v4 > "$W4LOG" 2>&1); then
        logline "$(tail -1 "$W4LOG")"
      else
        logline "美股 v4 小部位 失敗（不影響 daily）：$(tail -1 "$W4LOG" 2>/dev/null)（見 $W4LOG）"
      fi
      # 規則 10：策略鎖（使用者 10/18「我要怎麼確保你不會又把兩個策略條件自己改到？」）：營量／營飆選股程式與鎖定版不同 ⇒ 名單標題下加 ⚠ 一行（推 LINE）；⛔ 不擋名單產出
      SLK=$(cd "$REPO" && PYTHONPATH=$REPO "$PY" -m backtest.strategy_lock --check 2>&1); SLRC=$?
      if [ $SLRC = 2 ]; then logline "策略鎖：$SLK（不加警示）"; fi
      if [ $SLRC = 1 ]; then
        DMD="$REPO/backtest/resultsDaily/daily_$ASOF.md"; { head -1 "$DMD"; echo; echo "⚠⚠ $SLK（營量／營飆的選股程式和鎖定版本不同；回測線未經裁定核可不得改，請回測線說明）"; tail -n +2 "$DMD"; } > "$DMD.tmp" && mv "$DMD.tmp" "$DMD"
        logline "策略鎖不符：$SLK"
      fi
      mkdir -p "$MB"
      cp "$REPO/backtest/resultsDaily/daily_$ASOF.md" "$OUTF"
      rm -f "$MB/daily_${ASOF}_未到.md"
      # 裁定 seq296 §一：GATE_V2 開關不一致 ⇒ daily_list 寫了差異檔 ⇒ 放進 _營量觀察/；一致 ⇒ 刪掉同資料日舊的差異檔（只動 _營量觀察/ 這一個資料夾）
      if [ -f "$REPO/backtest/resultsDaily/gatev2_diff_$ASOF.md" ]; then cp "$REPO/backtest/resultsDaily/gatev2_diff_$ASOF.md" "$MB/gatev2_diff_$ASOF.md"; else rm -f "$MB/gatev2_diff_$ASOF.md"; fi
      RESULT="產檔"; logline "產檔：sha ${SHA:0:10}｜資料日 $ASOF｜$OUTF"
    else
      FAIL="程式錯誤：$(tail -20 "$WLOG")"
      logline "失敗：sha ${SHA:0:10}｜資料日 $ASOF｜程式錯誤（見 $WLOG）"
    fi
  fi
fi

# ── same_state（規則 7）：只在 daily 產檔或略過之後；失敗只記 log
if [ -z "$FAIL" ] && [ -n "$RESULT" ]; then
  SOUT="$MB/same_state_$ASOF.md"; SSHA="$WD/.same_state_$ASOF.sha"
  if [ $FORCE = 0 ] && [ -f "$SOUT" ] && [ -f "$SSHA" ] && [ "$(cat "$SSHA")" = "$SHA" ]; then
    logline "same_state 略過：sha ${SHA:0:10}｜資料日 $ASOF｜$SOUT 已存在且 sha 相同"
  else
    SLOG="$REPO/backtest/resultsDaily/same_state.log"
    if (cd "$REPO" && PYTHONPATH=$REPO "$PY" -m backtest.same_state --data "$DK/data" --sha "$SHA" > "$SLOG" 2>&1) && [ -f "$REPO/backtest/resultsDaily/same_state_$ASOF.md" ]; then
      mkdir -p "$MB"
      cp "$REPO/backtest/resultsDaily/same_state_$ASOF.md" "$SOUT" && echo "$SHA" > "$SSHA"
      logline "same_state 產檔：sha ${SHA:0:10}｜資料日 $ASOF｜$SOUT"
    else
      logline "same_state 失敗（不影響 daily）：sha ${SHA:0:10}｜資料日 $ASOF｜$(tail -1 "$SLOG" 2>/dev/null)（見 $SLOG）"
    fi
  fi
fi

if [ $FINAL = 1 ]; then
  TODAY=${DAILY_FAKE_TODAY:-$(TZ=Asia/Taipei date '+%Y-%m-%d')}
  HS="$HOME/h2data/${SHA:-none}/data/meta/holiday_schedule.csv"
  EXP=$("$PY" - "$TODAY" "$HS" <<'PYEOF'
import sys, os, pandas as pd
today, hs = pd.Timestamp(sys.argv[1]), sys.argv[2]
hol, trade = set(), set()
if os.path.exists(hs):
    h = pd.read_csv(hs, dtype=str)
    h = h[h["date"].astype(str).str.match(r"^\d{4}-\d{2}-\d{2}$", na=False)]
    for d, nm, nt in zip(h["date"], h["name"].fillna(""), h["note"].fillna("")):
        # 名稱含「開始交易／最後交易」且附註沒寫「無交易」⇒ 交易日（gate_b_status 同讀法，另把「市場無交易，僅辦理結算交割」當休市）
        (trade if (any(k in nm for k in ("開始交易", "最後交易")) and "無交易" not in nt) else hol).add(d)
d = today - pd.Timedelta(days=1)
while (d.weekday() >= 5 and d.strftime("%Y-%m-%d") not in trade) or d.strftime("%Y-%m-%d") in hol:
    d -= pd.Timedelta(days=1)
print(d.strftime("%Y-%m-%d"))
PYEOF
)
  if [ -f "$MB/daily_$EXP.md" ]; then
    logline "檢查：預期資料日 $EXP 的檔已在"
  else
    if [ -n "$FAIL" ]; then
      WHY="$FAIL"
    elif [ -n "$ASOF" ] && [[ "$EXP" > "$ASOF" ]]; then
      WHY="資料庫未更新：main 最新資料日＝$ASOF（sha ${SHA:0:10}）"
    else
      WHY="程式錯誤：main 最新資料日＝$ASOF 已涵蓋 $EXP，但沒有產出 daily_$EXP.md"
    fi
    mkdir -p "$MB"
    printf '# 每日名單未到：預期資料日 %s\n\n- 檢查時間：%s（台北，--final）\n- 原因：\n\n```\n%s\n```\n' "$EXP" "$NOW" "$WHY" > "$MB/daily_${EXP}_未到.md"
    logline "檢查：預期資料日 $EXP 沒有檔 ⇒ 寫 $MB/daily_${EXP}_未到.md｜$(echo "$WHY" | head -1)"
    [ -z "$FAIL" ] && [ "$RESULT" != "" ] && exit 0
    exit 1
  fi
fi
[ -n "$FAIL" ] && exit 1
exit 0
