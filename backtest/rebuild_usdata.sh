#!/usr/bin/env bash
# 重抽美股唯讀快照 ~/usdata/<commit>（us_data.py 的資料根）。2026-11-24：舊快照已清掉以省空間，要重跑美股研究時用這支補回。
# 用法：bash backtest/rebuild_usdata.sh <commit短碼> [目的根，預設 ~/usdata]
# 內容＝git archive 該 commit 全樹＋.commit（完整 sha），與原快照逐檔相同（抽驗過）；已存在就不動。
set -euo pipefail
C="${1:?要給 commit}"; ROOTDIR="${2:-$HOME/usdata}"; R="${US_REPO:-$HOME/us-stock-data}"
FULL=$(git -C "$R" rev-parse --verify "$C^{commit}")
D="$ROOTDIR/$C"
if [ -e "$D" ]; then echo "已存在：$D"; exit 0; fi
mkdir -p "$D.tmp"
git -C "$R" archive "$FULL" | tar -x -C "$D.tmp"
echo "$FULL" > "$D.tmp/.commit"
chmod -R a-w "$D.tmp"
mv "$D.tmp" "$D"
echo "重抽完成：$D（$(find "$D" -type f | wc -l) 檔）"
