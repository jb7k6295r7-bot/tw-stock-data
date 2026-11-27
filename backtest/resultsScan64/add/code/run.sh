#!/bin/bash
# 補格 S29／S87／S30：共用 ../../code 的 snap、panel、factors（唯一實作），只用環境變數改快照與輸出根目錄。
cd ~/tw-p17
export SCAN_BASE=~/scanadd SCAN_SNAP=~/scanadd_data/data SCAN_SHA=~/scanadd_data/SHA.txt
export PYTHONPATH=~/tw-p17:~/tw-p17/backtest/resultsScan64/code:~/tw-p17/backtest/resultsScan64/add/code
exec ~/tw-p16/.venv/bin/python "$@"
