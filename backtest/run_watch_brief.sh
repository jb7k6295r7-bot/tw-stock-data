#!/usr/bin/env bash
# 營量 v1「即將達成」精簡名單：抓最新 main ⇒ 唯讀 archive 到 ~/h2data/<sha>/data ⇒ 跑 --brief ⇒ 印出 brief md 路徑
# 用法：bash ~/tw-p17/backtest/run_watch_brief.sh      （給市場情報分析線定時推 LINE 用；回測線維護）
set -euo pipefail
REPO=$HOME/tw-p17
git -C "$REPO" fetch -q origin main
SHA=$(git -C "$REPO" rev-parse origin/main)
DST=$HOME/h2data/$SHA
if [ ! -d "$DST/data/stocks" ]; then
  mkdir -p "$DST"
  git -C "$REPO" archive "$SHA" data/adj data/meta data/mops/revenue_hist data/stocks data/stocks_per | tar -x -C "$DST"
fi
cd "$REPO"
PYTHONPATH=$REPO "$HOME/tw-p16/.venv/bin/python" -m backtest.list_yl13_watch --brief > /dev/null
ls -t "$REPO"/backtest/resultsYLwatch/brief_*.md | head -1
